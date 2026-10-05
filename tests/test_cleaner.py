"""Unit tests for DataCleaner (Test 4: Deduplication & Test 5: Missing Values)."""
import unittest
import pandas as pd
import numpy as np

from app.transformation.cleaner import DataCleaner


class TestDataCleaner(unittest.TestCase):
    def setUp(self):
        self.cleaner = DataCleaner({
            "gpa": "median",
            "attendance": "median",
            "score": "mean"
        })

    def test_deduplication(self):
        """Test 4: Verify duplicate student records are purged."""
        df = pd.DataFrame({
            "student_id": [1001, 1002, 1001, 1003],
            "name": ["Ahmed", "Sara", "Ahmed", "Omar"]
        })
        clean_df, removed = self.cleaner.remove_duplicates(df, subset_col="student_id")
        self.assertEqual(len(clean_df), 3)
        self.assertEqual(removed, 1)
        self.assertFalse(clean_df["student_id"].duplicated().any())

    def test_missing_values_imputation(self):
        """Test 5: Verify missing numeric values are imputed with median/mean."""
        df = pd.DataFrame({
            "student_id": [1001, 1002, 1003, 1004],
            "gpa": [3.0, 4.0, np.nan, 2.0],  # Median of 2.0, 3.0, 4.0 is 3.0
            "score": [80.0, 90.0, 100.0, np.nan]  # Mean of 80, 90, 100 is 90.0
        })
        imputed_df, count = self.cleaner.impute_missing_values(df)
        self.assertEqual(count, 2)
        self.assertFalse(imputed_df["gpa"].isna().any())
        self.assertFalse(imputed_df["score"].isna().any())
        self.assertEqual(imputed_df.loc[2, "gpa"], 3.0)
        self.assertEqual(imputed_df.loc[3, "score"], 90.0)

    def test_text_normalization(self):
        """Verify text trimming and title casing."""
        df = pd.DataFrame({
            "city": [" sanaa ", "SANAA", "Aden "],
            "student_name": ["  ahmed ali ", "SARA MOHAMMED", "omar"]
        })
        normalized = self.cleaner.clean_text_fields(df)
        self.assertEqual(list(normalized["city"]), ["Sanaa", "Sanaa", "Aden"])
        self.assertEqual(list(normalized["student_name"]), ["Ahmed Ali", "Sara Mohammed", "Omar"])


if __name__ == "__main__":
    unittest.main()
