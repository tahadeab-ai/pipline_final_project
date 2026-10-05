"""Data integration module: joins disparate sources on student_id and tracks data lineage."""
from typing import List
import logging
import pandas as pd

logger = logging.getLogger("student_pipeline")


class DataIntegrator:
    """
    Integrates multiple data sources into a unified dataset using a common join key (student_id).
    Tracks Data Lineage to record which sources contributed to each row (Excellence Requirement 21.3).
    """

    def __init__(self, join_key: str = "student_id"):
        self.join_key = join_key

    def integrate(
        self,
        csv_df: pd.DataFrame,
        api_df: pd.DataFrame,
        db_df: pd.DataFrame,
        *additional_dfs: pd.DataFrame,
        how: str = "outer"
    ) -> pd.DataFrame:
        """
        Merges CSV, API, SQLite, and optional additional DataFrames on student_id.
        Adds a 'data_lineage' column detailing which sources provided data for each record.
        """
        logger.info("Data integration started across multiple sources")

        source_dfs = [("CSV", csv_df), ("API", api_df), ("DATABASE", db_df)]
        for i, extra_df in enumerate(additional_dfs, start=1):
            name = getattr(extra_df, "_source_name", f"SOURCE_{i}")
            source_dfs.append((name, extra_df))

        # Normalize join key type across all dataframes
        normalized_dfs = []
        source_flags = []
        for name, df in source_dfs:
            df_copy = df.copy()
            flag_col = f"_has_{name.lower().replace(' ', '_')}"
            source_flags.append((name, flag_col))
            if self.join_key in df_copy.columns:
                df_copy[self.join_key] = pd.to_numeric(df_copy[self.join_key], errors="coerce")
                df_copy[flag_col] = df_copy[self.join_key].notna()
            else:
                df_copy[flag_col] = False
            normalized_dfs.append(df_copy)

        # Step 1: Merge base sources successively
        integrated = normalized_dfs[0]
        for idx, df_to_merge in enumerate(normalized_dfs[1:], start=1):
            suffix = f"_{source_flags[idx][0].lower()}"
            integrated = pd.merge(integrated, df_to_merge, on=self.join_key, how=how, suffixes=("", suffix))

        # Compute Data Lineage (e.g., 'CSV + API + DATABASE')
        def compute_lineage(row):
            sources = [src_name for src_name, flag_col in source_flags if row.get(flag_col) is True]
            return " + ".join(sources) if sources else "UNKNOWN"

        integrated["data_lineage"] = integrated.apply(compute_lineage, axis=1)

        # Drop internal helper columns
        drop_cols = [c for c in integrated.columns if c.startswith("_has_")]
        integrated.drop(columns=drop_cols, inplace=True)

        logger.info("Data integration completed. Integrated records: %d", len(integrated))
        return integrated
