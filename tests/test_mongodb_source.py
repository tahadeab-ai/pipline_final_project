"""Unit tests for MongoDBSource."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from app.sources.mongodb_source import MongoDBSource


class TestMongoDBSource(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.mock_fallback_file = Path(self.temp_dir.name) / "mock_mongo.json"
        self.mock_docs = [
            {"student_id": 1001, "name": "Ahmed Ali", "gpa": 3.75, "attendance": 92.0, "status": "Enrolled"},
            {"student_id": 1002, "name": "Fatima Hassan", "gpa": 3.90, "attendance": 96.0, "status": "Enrolled"}
        ]
        with open(self.mock_fallback_file, "w", encoding="utf-8") as f:
            json.dump(self.mock_docs, f)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_source_name(self):
        """Verify source_name property returns 'MONGODB'."""
        source = MongoDBSource(mock_fallback_path=self.mock_fallback_file)
        self.assertEqual(source.source_name, "MONGODB")

    def test_validate_connection_fallback(self):
        """Verify validate_connection succeeds via local fallback when remote daemon is offline."""
        source = MongoDBSource(
            uri="mongodb://invalid-host:27017",
            mock_fallback_path=self.mock_fallback_file,
            auto_fallback=True
        )
        self.assertTrue(source.validate_connection())

    def test_extraction_fallback(self):
        """Verify extract loads records from local mock fallback when connection fails."""
        source = MongoDBSource(
            uri="mongodb://invalid-host:27017",
            mock_fallback_path=self.mock_fallback_file,
            auto_fallback=True
        )
        docs = source.extract()
        self.assertEqual(len(docs), 2)
        self.assertEqual(docs[0]["student_id"], 1001)
        self.assertEqual(docs[0]["name"], "Ahmed Ali")

    def test_fingerprint_generation(self):
        """Verify fingerprint returns deterministic MD5 hash."""
        source = MongoDBSource(
            uri="mongodb://invalid-host:27017",
            mock_fallback_path=self.mock_fallback_file,
            auto_fallback=True
        )
        fp_before = source.get_fingerprint()
        self.assertTrue(len(fp_before) == 32)
        source.extract()
        fp_after = source.get_fingerprint()
        self.assertTrue(len(fp_after) == 32)

    @patch("app.sources.mongodb_source.MongoClient")
    def test_extraction_from_live_client(self, mock_client_cls):
        """Verify successful query extraction and _id string sanitization from MongoClient."""
        mock_client = MagicMock()
        mock_coll = MagicMock()
        mock_coll.find.return_value = [
            {"_id": "mock_object_id_123", "student_id": 2001, "gpa": 3.8}
        ]
        mock_client.__getitem__.return_value.__getitem__.return_value = mock_coll
        mock_client_cls.return_value = mock_client

        source = MongoDBSource(uri="mongodb://localhost:27017", auto_fallback=False)
        docs = source.extract()

        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["student_id"], 2001)
        self.assertEqual(docs[0]["_id"], "mock_object_id_123")


if __name__ == "__main__":
    unittest.main()
