"""Data transformation module: column standardizing, type conversion, and derived features."""
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger("student_pipeline")


class DataTransformer:
    """
    Handles schema standardization, type conversions, and derived feature engineering.
    """

    COLUMN_MAPPING = {
        "Student ID": "student_id",
        "StudentID": "student_id",
        "studentID": "student_id",
        "id": "student_id",
        "Student_Name": "student_name",
        "name": "student_name",
        "FullName": "student_name",
        "full_name": "student_name",
        "GPA": "gpa",
        "Attendance": "attendance",
        "Score": "score",
        "Age": "age",
        "Major": "major",
        "City": "city",
        "Status": "status",
        "Course": "course",
        "Course_Name": "course",
        "course_name": "course",
        "Semester": "semester"
    }

    def standardize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardizes arbitrary column naming conventions to snake_case standards."""
        df = df.copy()
        new_cols = {}
        for col in df.columns:
            cleaned = col.strip()
            new_cols[col] = self.COLUMN_MAPPING.get(cleaned, cleaned.lower().replace(" ", "_"))
        return df.rename(columns=new_cols)

    def cast_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Converts raw string fields to appropriate numeric and textual types."""
        df = df.copy()

        # Numeric conversions
        if "student_id" in df.columns:
            df["student_id"] = pd.to_numeric(df["student_id"], errors="coerce")

        if "age" in df.columns:
            df["age"] = pd.to_numeric(df["age"], errors="coerce")

        if "gpa" in df.columns:
            df["gpa"] = pd.to_numeric(df["gpa"], errors="coerce").round(2)

        if "attendance" in df.columns:
            df["attendance"] = pd.to_numeric(df["attendance"], errors="coerce").round(1)

        if "score" in df.columns:
            df["score"] = pd.to_numeric(df["score"], errors="coerce").round(2)

        return df

    def add_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates domain-specific derived indicators:
        1. performance_level:
           GPA >= 3.5 -> 'Excellent'
           GPA >= 3.0 -> 'Very Good'
           GPA >= 2.5 -> 'Good'
           GPA >= 2.0 -> 'Acceptable'
           GPA < 2.0  -> 'At Risk'

        2. attendance_status:
           attendance >= 75 -> 'Good'
           attendance < 75  -> 'Low'

        3. academic_standing:
           score >= 60 -> 'Passed'
           score < 60  -> 'Failed'
        """
        df = df.copy()

        # Feature 1: Performance Level from GPA
        if "gpa" in df.columns:
            conditions = [
                df["gpa"] >= 3.5,
                (df["gpa"] >= 3.0) & (df["gpa"] < 3.5),
                (df["gpa"] >= 2.5) & (df["gpa"] < 3.0),
                (df["gpa"] >= 2.0) & (df["gpa"] < 2.5),
                df["gpa"] < 2.0
            ]
            choices = ["Excellent", "Very Good", "Good", "Acceptable", "At Risk"]
            df["performance_level"] = np.select(conditions, choices, default="Unknown")

        # Feature 2: Attendance Status
        if "attendance" in df.columns:
            df["attendance_status"] = np.where(df["attendance"] >= 75.0, "Good", "Low")

        # Feature 3: Academic Standing based on course score
        if "score" in df.columns:
            df["academic_standing"] = np.where(df["score"] >= 60.0, "Passed", "Failed")

        logger.info("Generated derived columns: performance_level, attendance_status, academic_standing")
        return df
