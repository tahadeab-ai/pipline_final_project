"""Unit tests for CSVSource (Test 1: CSV Extraction)."""
import unittest
from pathlib import Path
import tempfile
import pandas as pd

from app.sources.csv_source import CSVSource


class TestCSVSource(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.csv_path = Path(self.test_dir.name) / "test_students.csv"
        df = pd.DataFrame({
            "student_id": ["1001", "1002"],
            "student_name": ["Ahmed Ali", "Sara Mohammed"],
            "age": ["21", "22"],
            "major": ["CS", "AI"],
            "city": ["Sanaa", "Aden"]
        })
        df.to_csv(self.csv_path, index=False)

    def tearDown(self):
        self.test_dir.cleanup()

    def test_csv_extraction_success(self):
        """Test 1: Verify CSV loading and parsing into DataFrame."""
        source = CSVSource(self.csv_path)
        self.assertTrue(source.validate_connection())
        df = source.extract()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 2)
        self.assertIn("student_id", df.columns)
        self.assertIn("student_name", df.columns)

    def test_csv_file_not_found(self):
        """Verify exception when CSV file does not exist."""
        non_existent = Path(self.test_dir.name) / "missing.csv"
        source = CSVSource(non_existent)
        self.assertFalse(source.validate_connection())
        with self.assertRaises(FileNotFoundError):
            source.extract()


if __name__ == "__main__":
    unittest.main()
