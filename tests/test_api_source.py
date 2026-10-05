"""Unit tests for APISource (Test 2: API Connectivity & Error Handling)."""
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pandas as pd
import requests

from app.sources.api_source import APISource


class TestAPISource(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.mock_json = Path(self.test_dir.name) / "mock.json"
        with open(self.mock_json, "w", encoding="utf-8") as f:
            json.dump([
                {"student_id": 1001, "gpa": 3.8, "attendance": 90.0, "status": "Active"}
            ], f)

    def tearDown(self):
        self.test_dir.cleanup()

    @patch("requests.get")
    def test_api_extraction_success(self, mock_get):
        """Test 2a: Verify successful API HTTP request and parsing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps([
            {"student_id": 1001, "gpa": 3.8, "attendance": 90.0, "status": "Active"}
        ])
        mock_response.json.return_value = [
            {"student_id": 1001, "gpa": 3.8, "attendance": 90.0, "status": "Active"}
        ]
        mock_get.return_value = mock_response

        source = APISource("http://fake-api/students", auto_fallback=False)
        df = source.extract()

        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["student_id"], 1001)

    @patch("requests.get")
    def test_api_connection_error_fallback(self, mock_get):
        """Test 2b: Verify fallback when API endpoint is unreachable."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Failed connection")

        source = APISource(
            "http://unreachable-host/api",
            mock_fallback_path=self.mock_json,
            auto_fallback=True
        )
        df = source.extract()
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["student_id"], 1001)


if __name__ == "__main__":
    unittest.main()
