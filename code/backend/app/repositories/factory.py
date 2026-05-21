from functools import lru_cache

from ..config import settings
from .base import DataRepository
from .mock import MockRepository


@lru_cache
def get_repository() -> DataRepository:
    if settings.data_backend == "mock":
        return MockRepository()
    raise RuntimeError(f"Unsupported DATA_BACKEND: {settings.data_backend}")
