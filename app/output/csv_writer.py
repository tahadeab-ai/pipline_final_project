"""Output writer module for persistent file saving."""
from pathlib import Path
import logging
import pandas as pd

logger = logging.getLogger("student_pipeline")


class CSVWriter:
    """Handles persistent saving of processed and rejected records."""

    @staticmethod
    def save(df: pd.DataFrame, output_path: str | Path, file_description: str = "Dataset") -> Path:
        """
        Saves a DataFrame to a specified CSV path, ensuring parent directories exist.
        """
        dest = Path(output_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        try:
            df.to_csv(dest, index=False, encoding="utf-8")
            logger.info("Saved %d records to %s (%s)", len(df), dest, file_description)
            return dest
        except Exception as ex:
            logger.error("Failed writing %s to %s: %s", file_description, dest, ex)
            raise RuntimeError(f"Output writing failed: {ex}") from ex
