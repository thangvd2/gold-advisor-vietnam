"""USD/VND exchange rate fetcher interface."""

from abc import abstractmethod

from src.ingestion.fetchers.base import DataSource
from src.ingestion.models import FetchedPrice


class FxRateFetcher(DataSource):
    @abstractmethod
    async def fetch(self) -> list[FetchedPrice]: ...
