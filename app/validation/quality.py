"""Data quality validation module implementing Rules 1 through 7."""
from typing import Dict, List, Tuple
import logging
import pandas as pd

logger = logging.getLogger("student_pipeline")


class DataQualityValidator:
    """
    Validates dataset records against institutional business rules:
    - Rule 1: student_id cannot be NULL
    - Rule 2: student_id must be unique
    - Rule 3: age must be between 16 and 80
    - Rule 4: GPA must be between 0.0 and 4.0
    - Rule 5: attendance must be between 0% and 100%
    - Rule 6: score must be between 0 and 100
    - Rule 7: student_id integrity across sources

    Splits input DataFrame into:
    1. Valid DataFrame (Clean, compliant records)
    2. Rejected DataFrame (Flagged records with detailed rejection reasons)
    """

    def __init__(self, thresholds: Dict[str, float] = None):
        self.thresholds = thresholds or {
            "age_min": 16,
            "age_max": 80,
            "gpa_min": 0.0,
            "gpa_max": 4.0,
            "attendance_min": 0.0,
            "attendance_max": 100.0,
            "score_min": 0.0,
            "score_max": 100.0
        }

    def validate_dataset(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Validates all records in the DataFrame and partitions them into valid and rejected sets.

        Returns:
            Tuple[valid_df, rejected_df]
        """
        logger.info("Validation started against institutional quality rules")
        if df.empty:
            logger.warning("Dataset passed to validator is empty")
            return pd.DataFrame(), pd.DataFrame(columns=["student_id", "error_reason"])

        df = df.copy()
        errors_per_row: List[List[str]] = [[] for _ in range(len(df))]

        # Rule 1: student_id cannot be NULL
        if "student_id" in df.columns:
            null_mask = df["student_id"].isna()
            for idx in df[null_mask].index:
                errors_per_row[idx].append("Missing student_id (Rule 1)")

        # Rule 2: student_id must be unique (flag duplicates beyond first)
        if "student_id" in df.columns:
            dup_mask = df["student_id"].duplicated(keep="first") & df["student_id"].notna()
            for idx in df[dup_mask].index:
                errors_per_row[idx].append("Duplicate student_id (Rule 2)")

        # Rule 3: Age between 16 and 80
        if "age" in df.columns:
            age_s = pd.to_numeric(df["age"], errors="coerce")
            invalid_age_mask = age_s.notna() & (~age_s.between(self.thresholds["age_min"], self.thresholds["age_max"]))
            for idx in df[invalid_age_mask].index:
                errors_per_row[idx].append(f"Invalid Age: {df.loc[idx, 'age']} (Rule 3)")

        # Rule 4: GPA between 0.0 and 4.0
        if "gpa" in df.columns:
            gpa_s = pd.to_numeric(df["gpa"], errors="coerce")
            invalid_gpa_mask = gpa_s.notna() & (~gpa_s.between(self.thresholds["gpa_min"], self.thresholds["gpa_max"]))
            for idx in df[invalid_gpa_mask].index:
                errors_per_row[idx].append(f"Invalid GPA: {df.loc[idx, 'gpa']} (Rule 4)")

        # Rule 5: Attendance between 0% and 100%
        if "attendance" in df.columns:
            att_s = pd.to_numeric(df["attendance"], errors="coerce")
            invalid_att_mask = att_s.notna() & (~att_s.between(self.thresholds["attendance_min"], self.thresholds["attendance_max"]))
            for idx in df[invalid_att_mask].index:
                errors_per_row[idx].append(f"Invalid Attendance: {df.loc[idx, 'attendance']}% (Rule 5)")

        # Rule 6: Score between 0 and 100
        if "score" in df.columns:
            score_s = pd.to_numeric(df["score"], errors="coerce")
            invalid_score_mask = score_s.notna() & (~score_s.between(self.thresholds["score_min"], self.thresholds["score_max"]))
            for idx in df[invalid_score_mask].index:
                errors_per_row[idx].append(f"Invalid Score: {df.loc[idx, 'score']} (Rule 6)")

        # Compile valid and rejected records
        rejection_reasons = ["; ".join(errs) for errs in errors_per_row]
        has_errors = [len(errs) > 0 for errs in errors_per_row]

        rejected_mask = pd.Series(has_errors, index=df.index)
        valid_df = df[~rejected_mask].copy()

        rejected_df = df[rejected_mask].copy()
        rejected_df["error_reason"] = [reasons for reasons, is_err in zip(rejection_reasons, has_errors) if is_err]

        # Reorder rejected_df to feature student_id and error_reason prominently
        cols = ["student_id", "error_reason"] + [c for c in rejected_df.columns if c not in ["student_id", "error_reason"]]
        rejected_df = rejected_df[cols]

        logger.info(
            "Validation completed: %d valid records, %d rejected records",
            len(valid_df),
            len(rejected_df)
        )
        return valid_df, rejected_df
