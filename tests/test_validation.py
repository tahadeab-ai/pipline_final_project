"""Unit tests for DataQualityValidator (Test 6: Invalid Records Rejection)."""
import unittest
import pandas as pd
import numpy as np

from app.validation.quality import DataQualityValidator


class TestDataQualityValidator(unittest.TestCase):
    def setUp(self):
        self.validator = DataQualityValidator()

    def test_invalid_records_rejection(self):
        """Test 6: Verify out-of-bound age, GPA, attendance, and null IDs are rejected with reasons."""
        test_df = pd.DataFrame([
            {"student_id": 1001, "age": 21, "gpa": 3.5, "attendance": 90.0, "score": 85.0}, # Valid
            {"student_id": 1002, "age": -5, "gpa": 3.5, "attendance": 90.0, "score": 85.0}, # Invalid Age
            {"student_id": 1003, "age": 22, "gpa": 4.9, "attendance": 90.0, "score": 85.0}, # Invalid GPA
            {"student_id": 1004, "age": 20, "gpa": 3.0, "attendance": 120.0, "score": 85.0},# Invalid Attendance
            {"student_id": 1005, "age": 23, "gpa": 3.2, "attendance": 80.0, "score": 150.0},# Invalid Score
            {"student_id": np.nan, "age": 22, "gpa": 3.0, "attendance": 80.0, "score": 80.0} # Missing ID
        ])

        valid_df, rejected_df = self.validator.validate_dataset(test_df)

        self.assertEqual(len(valid_df), 1)
        self.assertEqual(len(rejected_df), 5)
        self.assertEqual(valid_df.iloc[0]["student_id"], 1001)

        # Verify error reasons exist
        error_reasons = list(rejected_df["error_reason"])
        self.assertTrue(any("Invalid Age" in r for r in error_reasons))
        self.assertTrue(any("Invalid GPA" in r for r in error_reasons))
        self.assertTrue(any("Invalid Attendance" in r for r in error_reasons))
        self.assertTrue(any("Invalid Score" in r for r in error_reasons))
        self.assertTrue(any("Missing student_id" in r for r in error_reasons))


if __name__ == "__main__":
    unittest.main()
