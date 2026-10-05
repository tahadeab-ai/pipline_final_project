"""Unit tests for WebScraperSource."""
from pathlib import Path
import tempfile
import unittest

from app.sources.web_scraper_source import WebScraperSource


SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Students</title></head>
<body>
    <table class="students">
        <tbody>
            <tr data-status="active">
                <td class="id">1001</td>
                <td class="honors">Dean's List</td>
                <td class="grad_year">2026</td>
            </tr>
            <tr data-status="graduated">
                <td class="id">1002</td>
                <td class="honors">Honors</td>
                <td class="grad_year">2025</td>
            </tr>
        </tbody>
    </table>
</body>
</html>
"""


class TestWebScraperSource(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.fallback_file = Path(self.temp_dir.name) / "test_students.html"
        self.fallback_file.write_text(SAMPLE_HTML, encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_source_name(self):
        """Verify source_name property returns 'WEB_SCRAPER'."""
        source = WebScraperSource(fallback_html_path=self.fallback_file)
        self.assertEqual(source.source_name, "WEB_SCRAPER")

    def test_validate_connection_with_fallback(self):
        """Verify connection validation succeeds when target URL fails but fallback HTML exists."""
        source = WebScraperSource(
            url="http://invalid-scraper-host.example",
            fallback_html_path=self.fallback_file,
            auto_fallback=True
        )
        self.assertTrue(source.validate_connection())

    def test_extraction_with_fallback_html(self):
        """Verify table scraping parses rows and columns correctly from fallback HTML."""
        source = WebScraperSource(
            url="http://invalid-scraper-host.example",
            row_selector="table.students tbody tr",
            column_mapping={
                "student_id": {"selector": "td.id", "extract": "text"},
                "honors": {"selector": "td.honors", "extract": "text"},
                "graduation_year": {"selector": "td.grad_year", "extract": "text"}
            },
            fallback_html_path=self.fallback_file,
            auto_fallback=True
        )
        records = source.extract()
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["student_id"], "1001")
        self.assertEqual(records[0]["honors"], "Dean's List")
        self.assertEqual(records[0]["graduation_year"], "2026")
        self.assertEqual(records[1]["student_id"], "1002")

    def test_extraction_with_attribute_and_default(self):
        """Verify extracting HTML attributes and applying default values."""
        source = WebScraperSource(
            url="http://invalid-scraper-host.example",
            row_selector="table.students tbody tr",
            column_mapping={
                "student_id": {"selector": "td.id", "extract": "text"},
                "status": {"selector": None, "extract": "attribute", "attribute": "data-status"},
                "missing_col": {"selector": "td.nonexistent", "extract": "text", "default": "N/A"}
            },
            fallback_html_path=self.fallback_file,
            auto_fallback=True
        )
        records = source.extract()
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["status"], "active")
        self.assertEqual(records[0]["missing_col"], "N/A")

    def test_fingerprint_generation(self):
        """Verify fingerprint returns deterministic MD5 hash of raw HTML."""
        source = WebScraperSource(
            url="http://invalid-scraper-host.example",
            fallback_html_path=self.fallback_file,
            auto_fallback=True
        )
        fp = source.get_fingerprint()
        self.assertTrue(len(fp) == 32)


if __name__ == "__main__":
    unittest.main()
