"""CSV data extraction source."""
from pathlib import Path
from typing import Optional
import logging
import pandas as pd

from app.sources.base_source import BaseSource

logger = logging.getLogger("student_pipeline")


class CSVSource(BaseSource):
    """Extracts raw student demographic and basic enrollment data from a CSV file."""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)

    @property
    def source_name(self) -> str:
        return "CSV"

    def validate_connection(self) -> bool:
        """Verifies if the CSV file exists and is readable."""
        return self.file_path.exists() and self.file_path.is_file()

    def extract(self) -> pd.DataFrame:
        """
        Extracts student records from the CSV file.

        Returns:
            pd.DataFrame containing extracted records.
        """
        logger.info("CSV extraction started")
        if not self.validate_connection():
            error_msg = f"CSV source file not found at: {self.file_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        try:
            df = pd.read_csv(self.file_path, dtype=str)
            if df.empty:
                logger.warning("CSV file is empty: %s", self.file_path)
                return pd.DataFrame()

            # Clean leading/trailing spaces from column headers
            df.columns = [col.strip() for col in df.columns]

            logger.info("CSV records: %d", len(df))
            return df
        except Exception as ex:
            logger.error("Failed to read CSV file: %s", ex)
            raise RuntimeError(f"CSV extraction failed: {ex}") from ex
