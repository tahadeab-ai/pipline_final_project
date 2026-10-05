"""Data cleaning module: deduplication, text normalization, and imputation."""
from typing import Dict, Tuple
import logging
import pandas as pd

logger = logging.getLogger("student_pipeline")


class DataCleaner:
    """
    Handles data cleansing operations including:
    - Text whitespace stripping and casing harmonization
    - Deduplication on student_id
    - Strategic missing value imputation
    """

    def __init__(self, imputation_strategies: Dict[str, str] = None):
        raw_strategies = imputation_strategies or {
            "gpa": "median",
            "attendance": "median",
            "score": "mean",
            "major": "Unknown",
            "city": "Unknown"
        }
        # Normalize keys e.g. gpa_strategy -> gpa
        self.imputation_strategies = {
            k.replace("_strategy", ""): v for k, v in raw_strategies.items()
        }

    def clean_text_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """Strips leading/trailing whitespace and normalizes text casing."""
        df = df.copy()
        text_cols = df.select_dtypes(include=["object", "string"]).columns

        for col in text_cols:
            df[col] = df[col].astype("string").str.strip()
            # Title case cities and names for consistency
            if col in ["city", "student_name", "course", "major"]:
                df[col] = df[col].str.title()

        return df

    def remove_duplicates(self, df: pd.DataFrame, subset_col: str = "student_id") -> Tuple[pd.DataFrame, int]:
        """
        Removes duplicate entries based on a key column, preserving the first valid occurrence.
        Returns the deduplicated DataFrame and the count of dropped duplicates.
        """
        df = df.copy()
        initial_len = len(df)
        if subset_col in df.columns:
            # Filter out null student_id before deduplication so we don't accidentally drop valid rows
            non_null_mask = df[subset_col].notna()
            valid_subset = df[non_null_mask].drop_duplicates(subset=[subset_col], keep="first")
            null_subset = df[~non_null_mask]
            df = pd.concat([valid_subset, null_subset], ignore_index=True)

        duplicates_removed = initial_len - len(df)
        if duplicates_removed > 0:
            logger.info("Removed %d duplicate records based on %s", duplicates_removed, subset_col)
        return df, duplicates_removed

    def impute_missing_values(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        """
        Imputes missing values using domain-justified strategies:
        - GPA: Median (robust against extreme outliers)
        - Attendance: Median (reflects typical institutional attendance)
        - Score: Mean (standard assessment normalization)
        - Categorical: 'Unknown'
        """
        df = df.copy()
        total_imputed = 0

        for col, strategy in self.imputation_strategies.items():
            if col not in df.columns:
                continue

            missing_count = df[col].isna().sum()
            if missing_count == 0:
                continue

            total_imputed += int(missing_count)

            if strategy in ["median", "mean"]:
                # Ensure column is numeric before computing statistics
                df[col] = pd.to_numeric(df[col], errors="coerce")

            if strategy == "median":
                median_val = round(float(df[col].median()), 2)
                df[col] = df[col].fillna(median_val)
                logger.info("Imputed %d missing values in '%s' with median: %.2f", missing_count, col, median_val)
            elif strategy == "mean":
                mean_val = round(float(df[col].mean()), 2)
                df[col] = df[col].fillna(mean_val)
                logger.info("Imputed %d missing values in '%s' with mean: %.2f", missing_count, col, mean_val)
            else:
                df[col] = df[col].fillna(str(strategy))
                logger.info("Imputed %d missing values in '%s' with default: %s", missing_count, col, strategy)

        return df, total_imputed
