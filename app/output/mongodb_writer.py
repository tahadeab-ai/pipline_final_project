"""MongoDB Output writer module for saving final processed dataset to MongoDB collection."""
from typing import Any, Dict, List, Optional, Union
import logging
import os
import numpy as np
import pandas as pd
from pymongo import MongoClient, ReplaceOne

logger = logging.getLogger("student_pipeline")


class MongoDBWriter:
    """
    Handles persistent saving of processed student records into a MongoDB collection.
    Supports atomic batch upserting based on student_id to prevent duplicates.
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        uri_env: str = "MONGODB_URI",
        database: Optional[str] = None,
        database_env: str = "MONGODB_DB",
        collection: str = "final_students"
    ):
        self.uri = uri or os.getenv(uri_env) or os.getenv("MONGO_URI") or "mongodb://localhost:27017"
        self.database_name = database or os.getenv(database_env) or os.getenv("MONGO_DB") or "university"
        self.collection_name = collection

    def _get_client(self) -> MongoClient:
        return MongoClient(self.uri, serverSelectionTimeoutMS=2000)

    @staticmethod
    def sanitize_record(record: Dict[str, Any]) -> Dict[str, Any]:
        """Cleans records to ensure strict BSON compatibility (handles NaN, int64, float64)."""
        sanitized = {}
        for k, v in record.items():
            if pd.isna(v) or v is None:
                sanitized[k] = None
            elif isinstance(v, (np.integer,)):
                sanitized[k] = int(v)
            elif isinstance(v, (np.floating,)):
                sanitized[k] = float(v)
            elif isinstance(v, (np.bool_,)):
                sanitized[k] = bool(v)
            elif isinstance(v, pd.Timestamp):
                sanitized[k] = v.to_pydatetime()
            else:
                sanitized[k] = v
        return sanitized

    def save(
        self,
        df: pd.DataFrame,
        upsert_key: str = "student_id",
        file_description: str = "Final Processed Dataset"
    ) -> int:
        """
        Saves DataFrame records into the target MongoDB collection via bulk upserts.
        Returns count of processed records.
        """
        if df.empty:
            logger.warning("MongoDBWriter: Empty DataFrame provided. No records saved.")
            return 0

        records = [self.sanitize_record(r) for r in df.to_dict(orient="records")]

        try:
            client = self._get_client()
            db = client[self.database_name]
            coll = db[self.collection_name]

            if upsert_key and upsert_key in df.columns:
                operations = [
                    ReplaceOne({upsert_key: r[upsert_key]}, r, upsert=True)
                    for r in records if r.get(upsert_key) is not None
                ]
                if operations:
                    res = coll.bulk_write(operations, ordered=False)
                    logger.info(
                        "Saved %d records to MongoDB collection '%s.%s' (%s)",
                        len(records),
                        self.database_name,
                        self.collection_name,
                        file_description
                    )
                    return len(records)
            else:
                coll.delete_many({})
                res = coll.insert_many(records)
                logger.info(
                    "Inserted %d records to MongoDB collection '%s.%s' (%s)",
                    len(res.inserted_ids),
                    self.database_name,
                    self.collection_name,
                    file_description
                )
                return len(res.inserted_ids)

            return len(records)

        except Exception as ex:
            logger.error(
                "Failed saving %s to MongoDB collection '%s.%s': %s",
                file_description,
                self.database_name,
                self.collection_name,
                ex
            )
            return 0

    @classmethod
    def save_dataset(
        cls,
        df: pd.DataFrame,
        uri: Optional[str] = None,
        database: Optional[str] = None,
        collection: str = "final_students",
        upsert_key: str = "student_id"
    ) -> int:
        """Convenience class method to instantiate and save dataset in a single call."""
        writer = cls(uri=uri, database=database, collection=collection)
        return writer.save(df, upsert_key=upsert_key)
