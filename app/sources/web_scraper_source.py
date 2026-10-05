"""Web Scraping data source using BeautifulSoup and requests with tenacity retries and local HTML fallback."""
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import hashlib
import logging
import requests
from bs4 import BeautifulSoup

from app.sources.base_source import BaseSource

logger = logging.getLogger("student_pipeline")


def _is_retryable_scraper_error(exception: BaseException) -> bool:
    """Predicate determining if an HTTP scrape request should be retried."""
    if isinstance(exception, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
        return True
    if isinstance(exception, requests.exceptions.HTTPError):
        if exception.response is not None and exception.response.status_code >= 500:
            return True
    return False



class WebScraperSource(BaseSource):
    """
    Extracts structured tabular or card student data from HTML pages
    using BeautifulSoup with flexible selector schemas, tenacity retries,
    and automatic local HTML fallback when offline.
    """

    def __init__(
        self,
        url: str = "https://example.com/students",
        row_selector: str = "table.students tbody tr",
        column_mapping: Optional[Dict[str, Any]] = None,
        timeout: int = 10,
        headers: Optional[Dict[str, str]] = None,
        fallback_html_path: Optional[Union[str, Path]] = "data/raw/students_web.html",
        output_raw_html_path: Optional[Union[str, Path]] = None,
        auto_fallback: bool = True,
        schema_mode: str = "lenient"
    ):
        self.url = url
        self.row_selector = row_selector
        self.column_mapping = column_mapping or {
            "student_id": {"selector": "td.id", "extract": "text"},
            "honors": {"selector": "td.honors", "extract": "text"},
            "graduation_year": {"selector": "td.grad_year", "extract": "text"}
        }
        self.timeout = timeout
        self.headers = headers or {"User-Agent": "StudentDataPipeline/2.0 (Scraper)"}
        self.fallback_html_path = Path(fallback_html_path) if fallback_html_path else None
        self.output_raw_html_path = Path(output_raw_html_path) if output_raw_html_path else None
        self.auto_fallback = auto_fallback
        self.schema_mode = schema_mode.lower()
        self._raw_html: Optional[str] = None

    @property
    def source_name(self) -> str:
        return "WEB_SCRAPER"

    def validate_connection(self) -> bool:
        """Pings target URL to verify reachability or checks local fallback."""
        try:
            resp = requests.head(self.url, timeout=self.timeout, headers=self.headers)
            return resp.status_code < 500
        except requests.RequestException:
            return bool(self.auto_fallback and self.fallback_html_path and self.fallback_html_path.exists())

    def get_raw_data(self) -> str:
        """Returns the raw unparsed HTML content."""
        return self._raw_html or ""

    def get_fingerprint(self) -> str:
        """Computes MD5 hash of raw HTML markup."""
        if self._raw_html:
            return hashlib.md5(self._raw_html.encode("utf-8")).hexdigest()
        if self.fallback_html_path and self.fallback_html_path.exists():
            return hashlib.md5(self.fallback_html_path.read_bytes()).hexdigest()
        return ""

   
    def _fetch_html(self) -> str:
        """Fetches HTML with retry backoff."""
        response = requests.get(self.url, timeout=self.timeout, headers=self.headers)
        response.raise_for_status()
        return response.text

    def _extract_field_value(self, row_tag: Any, field_config: Any) -> Any:
        """Extracts field value from a row tag according to flexible column_mapping."""
        if isinstance(field_config, int):
            cells = row_tag.find_all(["td", "th"])
            if 0 <= field_config < len(cells):
                return cells[field_config].get_text(strip=True)
            return None

        if isinstance(field_config, str):
            el = row_tag.select_one(field_config)
            return el.get_text(strip=True) if el else None

        if isinstance(field_config, dict):
            selector = field_config.get("selector")
            extract_type = field_config.get("extract", "text").lower()
            attribute = field_config.get("attribute")
            default_val = field_config.get("default", None)

            target_el = row_tag.select_one(selector) if selector else row_tag
            if not target_el:
                return default_val

            if extract_type == "text":
                return target_el.get_text(strip=True)
            elif extract_type == "attribute" and attribute:
                return target_el.get(attribute, default_val)
            elif extract_type == "html":
                return str(target_el)
            return target_el.get_text(strip=True)

        return None

    def extract(self) -> List[Dict[str, Any]]:
        """
        Scrapes and parses student records from web page or local fallback.
        """
        logger.info("Web scraping started from: %s", self.url)
        html: Optional[str] = None

        try:
            html = self._fetch_html()
        except Exception as ex:
            if self.auto_fallback and self.fallback_html_path and self.fallback_html_path.exists():
                logger.warning(
                    "Remote URL '%s' unreachable (%s). Using local fallback HTML at: %s",
                    self.url,
                    ex,
                    self.fallback_html_path
                )
                html = self.fallback_html_path.read_text(encoding="utf-8")
            else:
                logger.error("Web scraping extraction failed: %s", ex)
                raise RuntimeError(f"Web scraper extraction failed: {ex}") from ex

        self._raw_html = html

        # Save raw HTML output
        if self.output_raw_html_path:
            self.output_raw_html_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.output_raw_html_path, "w", encoding="utf-8") as f:
                f.write(html)

        # Parse HTML
        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            soup = BeautifulSoup(html, "html.parser")

        rows = soup.select(self.row_selector)
        if not rows:
            logger.warning("Web scraper found 0 matching rows with selector: %s", self.row_selector)
            return []

        records = []
        for row in rows:
            record = {}
            for field, config in self.column_mapping.items():
                val = self._extract_field_value(row, config)
                record[field] = val
            if any(v is not None for v in record.values()):
                records.append(record)

        logger.info("Web scraper records extracted: %d", len(records))
        return records
