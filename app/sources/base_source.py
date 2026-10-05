"""Abstract Base Class for all data extraction sources."""
from abc import ABC, abstractmethod
import pandas as pd


class BaseSource(ABC):
    """
    Abstract contract for pipeline data sources.
    Enables plug-and-play addition of new storage engines
    (e.g., PostgreSQL, MongoDB, Parquet, Excel) without altering the pipeline core.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Returns the canonical name of the source (e.g., 'CSV', 'API', 'DATABASE')."""
        pass

    @abstractmethod
    def extract(self) -> pd.DataFrame:
        """
        Extracts raw data from the underlying provider and returns a DataFrame.

        Raises:
            RuntimeError: If extraction fails or data cannot be reached.
        """
        pass

    @abstractmethod
    def validate_connection(self) -> bool:
        """Validates that the source target exists and is reachable."""
        pass
