"""SQLite Database extraction source."""
from pathlib import Path
from typing import Optional
import logging
import sqlite3
import pandas as pd

from app.sources.base_source import BaseSource

logger = logging.getLogger("student_pipeline")


class DatabaseSource(BaseSource):
    """
    Extracts course enrollment and academic score records from SQLite database
    using relational SQL queries and joins.
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    @property
    def source_name(self) -> str:
        return "DATABASE"

    def validate_connection(self) -> bool:
        """Verifies database file existence and connectivity."""
        if not self.db_path.exists() or not self.db_path.is_file():
            return False
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT 1;")
            return True
        except sqlite3.Error:
            return False
        finally:
            if conn:
                conn.close()

    def extract(self) -> pd.DataFrame:
        """
        Executes SQL query joining enrollments and courses tables.
        Aggregates average score per student to maintain 1:1 student integrity.

        Returns:
            pd.DataFrame with columns: student_id, course, semester, score.
        """
        logger.info("Database extraction started")
        if not self.validate_connection():
            error_msg = f"Database file not accessible at: {self.db_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        query = """
        SELECT 
            e.student_id,
            c.course_name AS course,
            e.semester,
            ROUND(AVG(e.score), 2) AS score
        FROM enrollments e
        JOIN courses c ON e.course_id = c.course_id
        GROUP BY e.student_id;
        """

        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(query, conn)

            if df.empty:
                logger.warning("Database query returned 0 rows.")
                return pd.DataFrame()

            # Clean column headers
            df.columns = [col.strip() for col in df.columns]

            logger.info("Database records: %d", len(df))
            return df

        except sqlite3.Error as sql_err:
            logger.error("SQLite query execution failed: %s", sql_err)
            raise RuntimeError(f"Database extraction failed: {sql_err}") from sql_err
        finally:
            if conn:
                conn.close()
