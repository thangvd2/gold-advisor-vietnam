"""Abstract DataSource adapter with retry/error handling."""

import asyncio
import functools
import logging
from abc import ABC, abstractmethod
from typing import Callable

from src.ingestion.models import FetchedPrice

logger = logging.getLogger(__name__)


def retry(max_retries: int = 3, backoff_factor: float = 1.0):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    last_exception = exc
                    if attempt < max_retries:
                        delay = backoff_factor * (2**attempt)
                        logger.warning(
                            "%s failed (attempt %d/%d), retrying in %.1fs: %s",
                            func.__qualname__,
                            attempt + 1,
                            max_retries + 1,
                            delay,
                            exc,
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "%s failed after %d attempts: %s",
                            func.__qualname__,
                            max_retries + 1,
                            exc,
                        )
            raise last_exception  # type: ignore[misc]

        return wrapper

    return decorator


class DataSource(ABC):
    @abstractmethod
    async def fetch(self) -> list[FetchedPrice]: ...
