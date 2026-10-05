"""Unit tests for DatabaseSource (Test 3: SQLite Extraction)."""
import unittest
import sqlite3
import tempfile
from pathlib import Path
import pandas as pd

from app.sources.database_source import DatabaseSource


class TestDatabaseSource(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.test_dir.name) / "test_students.db"
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE courses (
            course_id INTEGER PRIMARY KEY,
            course_name TEXT,
            credit_hours INTEGER
        );
        """)
        cur.execute("""
        CREATE TABLE enrollments (
            enrollment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            course_id INTEGER,
            semester TEXT,
            score REAL
        );
        """)
        cur.execute("INSERT INTO courses VALUES (101, 'Python Programming', 3);")
        cur.execute("INSERT INTO enrollments VALUES (1, 1001, 101, 'Fall 2025', 92.0);")
        conn.commit()
        conn.close()

    def tearDown(self):
        import gc
        gc.collect()
        self.test_dir.cleanup()

    def test_database_extraction_success(self):
        """Test 3: Verify SQLite query extraction and join."""
        source = DatabaseSource(self.db_path)
        self.assertTrue(source.validate_connection())
        df = source.extract()

        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["student_id"], 1001)
        self.assertEqual(df.iloc[0]["course"], "Python Programming")
        self.assertEqual(df.iloc[0]["score"], 92.0)


if __name__ == "__main__":
    unittest.main()
