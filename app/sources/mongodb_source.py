"""MongoDB data extraction source using pymongo with local fallback."""
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import hashlib
import json
import logging
import os
from pymongo import MongoClient
import pandas as pd
from app.sources.base_source import BaseSource

logger = logging.getLogger("student_pipeline")


class MongoDBSource(BaseSource):
    """
    Extracts student records from MongoDB database using pymongo.
    Sanitizes BSON types like ObjectId into JSON-safe representations,
    and supports local mock fallback when MongoDB daemon is offline.
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        uri_env: str = "MONGODB_URI",
        database: Optional[str] = None,
        database_env: str = "MONGODB_DB",
        collection: str = "students",
        query_filter: Optional[Dict[str, Any]] = None,
        mock_fallback_path: Optional[Union[str, Path]] = "data/raw/students_mongodb.json",
        auto_fallback: bool = True,
        schema_mode: str = "lenient"
    ):
        self.uri_env = uri_env
        self.uri = uri or os.getenv(uri_env, "mongodb://localhost:27017")
        self.database_env = database_env
        self.database_name = database or os.getenv(database_env, "university")
        self.collection_name = collection
        self.query_filter = query_filter or {}
        self.mock_fallback_path = Path(mock_fallback_path) if mock_fallback_path else None
        self.auto_fallback = auto_fallback
        self.schema_mode = schema_mode.lower()
        self._raw_docs: Optional[List[Dict[str, Any]]] = None

    @property
    def source_name(self) -> str:
        return "MONGODB"

    def _get_client(self) -> MongoClient:
        return MongoClient(self.uri, serverSelectionTimeoutMS=2000)

    def validate_connection(self) -> bool:
        """Pings MongoDB admin database to verify connectivity or checks fallback."""
        try:
            client = self._get_client()
            client.admin.command("ping")
            return True
        except Exception:
            return bool(self.auto_fallback and self.mock_fallback_path and self.mock_fallback_path.exists())

    def get_raw_data(self) -> str:
        """Returns JSON-serialized dump of extracted MongoDB documents."""
        if self._raw_docs is not None:
            return json.dumps(self._raw_docs, indent=2, default=str)
        return ""

    def get_fingerprint(self) -> str:
        """Computes hash based on extracted documents for incremental tracking."""
        if self._raw_docs is not None:
            serialized = json.dumps(self._raw_docs, sort_keys=True, default=str)
            return hashlib.md5(serialized.encode("utf-8")).hexdigest()
        if self.mock_fallback_path and self.mock_fallback_path.exists():
            return hashlib.md5(self.mock_fallback_path.read_bytes()).hexdigest()
        return ""

    def _load_mock_fallback(self, reason: str) -> List[Dict[str, Any]]:
        """Loads fallback JSON mock file if available."""
        if self.auto_fallback and self.mock_fallback_path and self.mock_fallback_path.exists():
            logger.warning(
                "MongoDB connection unavailable (%s). Falling back to local dataset at: %s",
                reason,
                self.mock_fallback_path
            )
            with open(self.mock_fallback_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._raw_docs = data
            logger.info("MongoDB documents (fallback): %d", len(data))
            return data
        raise RuntimeError(f"MongoDB extraction failed and no fallback available: {reason}")

    def extract(self) -> List[Dict[str, Any]]:
        """
        Queries collection or loads local fallback dataset.
        """
        logger.info(
            "MongoDB extraction started on database '%s', collection '%s'",
            self.database_name,
            self.collection_name
        )
        try:
            client = self._get_client()
            db = client[self.database_name]
            coll = db[self.collection_name]

            docs = list(coll.find(self.query_filter))

            # Sanitize documents (convert ObjectId to str)
            sanitized: List[Dict[str, Any]] = []
            for doc in docs:
                item = {}
                for k, v in doc.items():
                    if k == "_id":
                        item[k] = str(v)
                    else:
                        item[k] = v
                sanitized.append(item)

            self._raw_docs = sanitized
            logger.info("MongoDB documents extracted: %d", len(sanitized))
            return sanitized

        except Exception as ex:
            logger.warning("MongoDB query error: %s", ex)
            return self._load_mock_fallback(str(ex))
