"""
Main Pipeline Orchestrator for Student Data Integration & ETL System.
Conforms strictly to Sections 16, 21, and 23 of the comprehensive specification.
Extended with optional MongoDB source support.
"""
from pathlib import Path
import hashlib
import json
import logging
import time
from typing import Dict, Any, Optional
import pandas as pd 

from app.sources.mongodb_source import MongoDBSource
from app.sources.web_scraper_source import WebScraperSource
from app.utils.config import load_config
from app.utils.logger import setup_logger
from app.sources import CSVSource, APISource, DatabaseSource
from app.transformation import DataCleaner, DataTransformer, DataIntegrator
from app.validation import DataQualityValidator
from app.output import CSVWriter, MongoDBWriter
from mock_api import start_background_mock_server



def compute_file_hash(file_path: Path) -> Optional[str]:
    """Computes MD5 hash for a given file to support incremental processing."""
    if not file_path.exists():
        return None
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


class PipelineOrchestrator:
    """End-to-end coordinator for extraction, integration, cleaning, transformation, and output."""

    def __init__(self, config_path: str = "config.yaml"):
        self.config = load_config(config_path)
        self.log_file = Path(self.config["paths"]["log_file"])
        self.logger = setup_logger(self.log_file)
        self._mock_server = None

    def _ensure_api_availability(self):
        """Starts a local mock server if enabled and the remote endpoint is unreachable."""
        api_cfg = self.config["api"]
        if api_cfg.get("auto_start_mock", True):
            api_source = APISource(
                endpoint_url=api_cfg["base_url"],
                timeout=1,
                mock_fallback_path=api_cfg.get("mock_data_fallback"),
                auto_fallback=True
            )
            if not api_source.validate_connection():
                self.logger.info("Local API server not detected. Launching background mock API server...")
                self._mock_server = start_background_mock_server(port=8000)

    def _build_mongodb_source(self) -> Optional[MongoDBSource]:
        """Instantiates MongoDB source if enabled in config; otherwise returns None."""
        mongo_cfg = self.config.get("mongodb", {})
        if not mongo_cfg.get("enabled", False):
            return None
        return MongoDBSource(
            uri=mongo_cfg.get("uri"),
            uri_env=mongo_cfg.get("uri_env"),
            database=mongo_cfg.get("database"),
            database_env=mongo_cfg.get("database_env"),
            collection=mongo_cfg.get("collection"),
            query_filter=mongo_cfg.get("query_filter"),
            mock_fallback_path=mongo_cfg.get("mock_data_fallback", "data/raw/students_mongodb.json"),
            auto_fallback=mongo_cfg.get("auto_fallback", True),
        )

    def _build_web_scraper_source(self) -> Optional[WebScraperSource]:
        """Instantiates Web Scraper source if enabled in config; otherwise returns None."""
        scraper_cfg = self.config.get("web_scraper", {})
        if not scraper_cfg.get("enabled", False):
            return None
        return WebScraperSource(
            url=scraper_cfg.get("url", "https://example.com/students"),
            row_selector=scraper_cfg.get("row_selector", "table.students tbody tr"),
            column_mapping=scraper_cfg.get("column_mapping"),
            fallback_html_path=scraper_cfg.get("fallback_html_path", "data/raw/students_web.html"),
            auto_fallback=scraper_cfg.get("auto_fallback", True),
            schema_mode=scraper_cfg.get("schema_mode", "lenient")
        )

    def is_incremental_unchanged(
        self,
        csv_path: Path,
        db_path: Path,
        state_file: Path,
        mongo_fingerprint: Optional[str] = None,
    ) -> bool:
        """Checks if input data sources have changed since last successful execution."""
        csv_hash = compute_file_hash(csv_path)
        db_hash = compute_file_hash(db_path)

        if not state_file.exists():
            return False

        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            if state.get("csv_hash") != csv_hash or state.get("db_hash") != db_hash:
                return False
            # Validate MongoDB fingerprint if a MongoDB source is active
            if mongo_fingerprint is not None:
                if state.get("mongodb_fingerprint") != mongo_fingerprint:
                    return False
            return True
        except Exception:
            return False

    def update_incremental_state(
        self,
        csv_path: Path,
        db_path: Path,
        state_file: Path,
        mongo_fingerprint: Optional[str] = None,
    ):
        """Saves hashes of current sources to state file."""
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "last_run": time.strftime("%Y-%m-%d %H:%M:%S"),
            "csv_hash": compute_file_hash(csv_path),
            "db_hash": compute_file_hash(db_path),
        }
        if mongo_fingerprint is not None:
            state["mongodb_fingerprint"] = mongo_fingerprint
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def run(self, force_recompute: bool = False) -> Dict[str, Any]:
        """
        Executes the full pipeline workflow.
        Returns execution metrics summary.
        """
        start_time = time.time()
        self.logger.info("=" * 60)
        self.logger.info("PIPELINE EXECUTION STARTED")
        self.logger.info("=" * 60)

        paths = self.config["paths"]
        csv_path = Path(paths["csv_raw"])
        db_path = Path(paths["database_path"])
        processed_path = Path(paths["processed_output"])
        rejected_path = Path(paths["rejected_output"])
        state_path = Path(paths.get("state_file", "logs/pipeline_state.json"))

        # Instantiate MongoDB source (if enabled) up-front so we can fingerprint it
        mongo_extractor = self._build_mongodb_source()
        mongo_fingerprint: Optional[str] = None
        if mongo_extractor is not None and hasattr(mongo_extractor, "get_fingerprint"):
            try:
                mongo_fingerprint = mongo_extractor.get_fingerprint()
            except Exception as ex:
                self.logger.warning("Could not compute MongoDB fingerprint: %s", ex)

        # Incremental Processing Check (Section 21.2)
        if not force_recompute and self.is_incremental_unchanged(
            csv_path, db_path, state_path, mongo_fingerprint
        ):
            self.logger.info("Incremental check: Raw data sources unchanged since last execution. Using cached output.")
            print("\n[Incremental Processing] No changes detected in raw sources. Pipeline up to date.")
            return {"status": "skipped", "reason": "unchanged"}

        self._ensure_api_availability()

        # Phase 1: Extraction
        csv_extractor = CSVSource(csv_path)
        api_extractor = APISource(
            endpoint_url=self.config["api"]["base_url"],
            timeout=self.config["api"]["timeout_seconds"],
            mock_fallback_path=self.config["api"].get("mock_data_fallback"),
            auto_fallback=True
        )
        db_extractor = DatabaseSource(db_path)

        csv_df = csv_extractor.extract()
        api_df = api_extractor.extract()
        db_df = db_extractor.extract()

        raw_csv_count = len(csv_df)
        raw_api_count = len(api_df)
        raw_db_count = len(db_df)

        # Optional MongoDB extraction
        mongo_df = None
        raw_mongo_count = 0
        if mongo_extractor is not None:
            self.logger.info("Extracting data from MongoDB source...")
            mongo_docs = mongo_extractor.extract()
            raw_mongo_count = len(mongo_docs)
            if mongo_docs:
                mongo_df = pd.DataFrame(mongo_docs)
                if "_id" in mongo_df.columns:
                    mongo_df.drop(columns=["_id"], inplace=True)
                mongo_df._source_name = "MONGODB"

        # Optional Web Scraper extraction
        web_extractor = self._build_web_scraper_source()
        web_df = None
        raw_web_count = 0
        if web_extractor is not None:
            self.logger.info("Extracting data from Web Scraper source...")
            try:
                web_records = web_extractor.extract()
                raw_web_count = len(web_records)
                if web_records:
                    web_df = pd.DataFrame(web_records)
                    web_df._source_name = "WEB_SCRAPER"
            except Exception as ex:
                self.logger.warning("Web Scraper extraction skipped: %s", ex)

        # Standardize source schemas before integration
        transformer = DataTransformer()
        csv_df = transformer.standardize_column_names(csv_df)
        api_df = transformer.standardize_column_names(api_df)
        db_df = transformer.standardize_column_names(db_df)
        if mongo_df is not None:
            mongo_df = transformer.standardize_column_names(mongo_df)
        if web_df is not None:
            web_df = transformer.standardize_column_names(web_df)

        # Phase 2: Deduplication and Initial Cleaning
        cleaner = DataCleaner(self.config.get("imputation"))
        csv_df = cleaner.clean_text_fields(csv_df)
        csv_df, duplicate_count = cleaner.remove_duplicates(csv_df, subset_col="student_id")

        # Phase 3: Integration (with Data Lineage)
        integrator = DataIntegrator(join_key="student_id")
        dfs_to_integrate = [csv_df, api_df, db_df]
        if mongo_df is not None:
            dfs_to_integrate.append(mongo_df)
        if web_df is not None:
            dfs_to_integrate.append(web_df)
        integrated_df = integrator.integrate(*dfs_to_integrate, how="outer")
        integrated_count = len(integrated_df)

        # Phase 4: Type Conversion & Standardization
        self.logger.info("Transformation started")
        typed_df = transformer.cast_data_types(integrated_df)

        # Phase 5: Missing Value Imputation
        imputed_df, imputed_count = cleaner.impute_missing_values(typed_df)

        # Phase 6: Derived Features
        transformed_df = transformer.add_derived_features(imputed_df)
        self.logger.info("Transformation completed")

        # Phase 6: Quality Validation & Partitioning
        validator = DataQualityValidator(self.config.get("validation"))
        valid_df, rejected_df = validator.validate_dataset(transformed_df)

        # Phase 7 & 8: Output Loading
        CSVWriter.save(valid_df, processed_path, file_description="Final Processed Dataset")
        CSVWriter.save(rejected_df, rejected_path, file_description="Rejected Records")

        # Save to MongoDB destination collection
        mongo_saved_count = 0
        mongo_cfg = self.config.get("mongodb", {})
        if mongo_cfg.get("enabled", False):
            mongo_dest_collection = mongo_cfg.get("output_collection", "final_students")
            self.logger.info("Saving final dataset to MongoDB collection '%s'...", mongo_dest_collection)
            mongo_saved_count = MongoDBWriter.save_dataset(
                valid_df,
                uri=mongo_cfg.get("uri"),
                database=mongo_cfg.get("database"),
                collection=mongo_dest_collection,
                upsert_key="student_id"
            )

        self.logger.info("Final dataset created")

        # Update incremental state
        self.update_incremental_state(csv_path, db_path, state_path, mongo_fingerprint)

        elapsed_time = round(time.time() - start_time, 3)

        # Metrics Compilation (Section 21.4)
        metrics = {
            "csv_records": raw_csv_count,
            "api_records": raw_api_count,
            "database_records": raw_db_count,
            "mongodb_records": raw_mongo_count,
            "web_records": raw_web_count,
            "integrated_records": integrated_count,
            "valid_records": len(valid_df),
            "rejected_records": len(rejected_df),
            "duplicate_records": duplicate_count,
            "missing_values_imputed": imputed_count,
            "mongodb_saved_records": mongo_saved_count,
            "processing_time": elapsed_time
        }

        self._print_execution_summary(metrics)
        return metrics

    def _print_execution_summary(self, metrics: Dict[str, Any]):
        """Prints formatted execution metrics summary table."""
        summary = f"""
-----------------------------------
PIPELINE EXECUTION SUMMARY
-----------------------------------
CSV Records        : {metrics['csv_records']}
API Records        : {metrics['api_records']}
Database Records   : {metrics['database_records']}
MongoDB Records    : {metrics['mongodb_records']}
Web Scraper Records: {metrics.get('web_records', 0)}
Integrated Records : {metrics['integrated_records']}
Valid Records      : {metrics['valid_records']}
Rejected Records   : {metrics['rejected_records']}
Duplicate Records  : {metrics['duplicate_records']}
Missing Values     : {metrics['missing_values_imputed']}
MongoDB Saved      : {metrics.get('mongodb_saved_records', 0)}
Processing Time    : {metrics['processing_time']} seconds
-----------------------------------"""
        print(summary)
        self.logger.info(summary)


def run_pipeline(force_recompute: bool = False) -> Dict[str, Any]:
    """Top-level pipeline execution function."""
    orchestrator = PipelineOrchestrator()
    return orchestrator.run(force_recompute=force_recompute)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Student Data Integration Pipeline")
    parser.add_argument("--force", action="store_true", help="Force recomputation ignoring incremental cache")
    args = parser.parse_args()
    run_pipeline(force_recompute=args.force)