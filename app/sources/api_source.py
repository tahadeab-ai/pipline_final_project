"""REST API data extraction source with robust HTTP resilience."""
from pathlib import Path
from typing import Optional
import json
import logging
import pandas as pd
import requests

from app.sources.base_source import BaseSource

logger = logging.getLogger("student_pipeline")


class APISource(BaseSource):
    """
    Extracts student academic records from a REST API endpoint.
    Handles timeouts, connection errors, HTTP error codes, invalid JSON, and empty responses.
    """

    def __init__(
        self,
        endpoint_url: str,
        timeout: int = 5,
        mock_fallback_path: Optional[str | Path] = None,
        auto_fallback: bool = True
    ):
        self.endpoint_url = endpoint_url
        self.timeout = timeout
        self.mock_fallback_path = Path(mock_fallback_path) if mock_fallback_path else None
        self.auto_fallback = auto_fallback

    @property
    def source_name(self) -> str:
        return "API"

    def validate_connection(self) -> bool:
        """Pings the endpoint to verify network availability."""
        try:
            resp = requests.head(self.endpoint_url, timeout=self.timeout)
            return resp.status_code < 500
        except requests.RequestException:
            return False

    def _load_mock_fallback(self, reason: str) -> pd.DataFrame:
        """Loads fallback JSON mock file if available."""
        if self.auto_fallback and self.mock_fallback_path and self.mock_fallback_path.exists():
            logger.warning(
                "API call failed (%s). Falling back to local mock data at: %s",
                reason,
                self.mock_fallback_path
            )
            try:
                with open(self.mock_fallback_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                df = pd.DataFrame(data)
                logger.info("API records (fallback): %d", len(df))
                return df
            except Exception as ex:
                logger.error("Failed loading mock fallback file: %s", ex)
                raise RuntimeError(f"Fallback loading failed: {ex}") from ex
        raise RuntimeError(f"API request failed: {reason}")

    def extract(self) -> pd.DataFrame:
        """
        Executes HTTP GET request, validates response, parses JSON, and converts to DataFrame.

        Returns:
            pd.DataFrame containing academic metrics.
        """
        logger.info("API extraction started")

        try:
            response = requests.get(
                self.endpoint_url,
                timeout=self.timeout,
                headers={"Accept": "application/json"}
            )
            # Check HTTP Status Code
            response.raise_for_status()

            # Validate response body is not empty
            if not response.text or not response.text.strip():
                logger.warning("API returned an empty response")
                return self._load_mock_fallback("Empty Response")

            # Parse JSON
            try:
                data = response.json()
            except json.JSONDecodeError as json_err:
                logger.error("API returned invalid JSON: %s", json_err)
                return self._load_mock_fallback(f"Invalid JSON: {json_err}")

            if isinstance(data, dict):
                # If wrapped in a data key e.g. {"data": [...]}
                data = data.get("data", [data])

            df = pd.DataFrame(data)
            if df.empty:
                logger.warning("Parsed API dataset is empty")
                return pd.DataFrame()

            # Clean column names
            df.columns = [col.strip() for col in df.columns]

            logger.info("API records: %d", len(df))
            return df

        except requests.exceptions.Timeout as to_err:
            logger.error("API Request Timeout: %s", to_err)
            return self._load_mock_fallback(f"Timeout: {to_err}")
        except requests.exceptions.ConnectionError as conn_err:
            logger.warning("API Connection Error (Endpoint unreachable): %s", conn_err)
            return self._load_mock_fallback(f"Connection Error: {conn_err}")
        except requests.exceptions.HTTPError as http_err:
            logger.error("API HTTP Status Error (%s): %s", response.status_code, http_err)
            return self._load_mock_fallback(f"HTTP Error: {http_err}")
        except requests.exceptions.RequestException as req_err:
            logger.error("Unexpected Request Exception: %s", req_err)
            return self._load_mock_fallback(f"Request Exception: {req_err}")
