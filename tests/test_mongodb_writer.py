"""Unit tests for MongoDBWriter (Saving final processed dataset to MongoDB)."""
import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import pandas as pd

from app.output.mongodb_writer import MongoDBWriter


class TestMongoDBWriter(unittest.TestCase):
    def test_sanitize_record(self):
        """Verify type sanitization converts numpy types and NaN values properly."""
        raw_record = {
            "student_id": np.int64(1001),
            "gpa": np.float64(3.85),
            "score": np.nan,
            "passed": np.bool_(True),
            "status": "Enrolled"
        }
        sanitized = MongoDBWriter.sanitize_record(raw_record)
        self.assertEqual(sanitized["student_id"], 1001)
        self.assertEqual(type(sanitized["student_id"]), int)
        self.assertEqual(sanitized["gpa"], 3.85)
        self.assertEqual(type(sanitized["gpa"]), float)
        self.assertIsNone(sanitized["score"])
        self.assertEqual(sanitized["passed"], True)
        self.assertEqual(type(sanitized["passed"]), bool)

    def test_save_empty_dataframe(self):
        """Verify empty DataFrame returns 0 saved records without error."""
        writer = MongoDBWriter()
        saved = writer.save(pd.DataFrame())
        self.assertEqual(saved, 0)

    @patch("app.output.mongodb_writer.MongoClient")
    def test_save_bulk_upsert(self, mock_client_cls):
        """Verify save performs bulk upserts using student_id key."""
        mock_client = MagicMock()
        mock_coll = MagicMock()
        mock_bulk_res = MagicMock()
        mock_bulk_res.upserted_count = 2
        mock_bulk_res.modified_count = 0
        mock_bulk_res.matched_count = 0
        mock_coll.bulk_write.return_value = mock_bulk_res
        mock_client.__getitem__.return_value.__getitem__.return_value = mock_coll
        mock_client_cls.return_value = mock_client

        df = pd.DataFrame([
            {"student_id": 1001, "student_name": "Ahmed", "gpa": 3.5},
            {"student_id": 1002, "student_name": "Fatima", "gpa": 3.9}
        ])

        writer = MongoDBWriter(collection="final_students")
        saved_count = writer.save(df, upsert_key="student_id")

        self.assertEqual(saved_count, 2)
        mock_coll.bulk_write.assert_called_once()


if __name__ == "__main__":
    unittest.main()
