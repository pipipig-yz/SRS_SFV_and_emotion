from abc import ABC, abstractmethod
from typing import Any


class DataRepository(ABC):
    @abstractmethod
    async def authenticate(self, username: str, password: str) -> dict[str, Any] | None:
        """Return login data when credentials are accepted."""

    @abstractmethod
    async def get_user_profile(self, user_id: str) -> dict[str, Any] | None:
        """Return a user profile or None if the user does not exist."""

    @abstractmethod
    async def get_user_behavior(self, user_id: str, date: str) -> dict[str, Any] | None:
        """Return short-video behavior data for a user and date."""

    @abstractmethod
    async def get_user_mental_state(self, user_id: str, date: str) -> dict[str, Any] | None:
        """Return mental-state data for a user and date."""

    @abstractmethod
    async def get_user_watch_history(self, user_id: str, date: str) -> dict[str, Any] | None:
        """Return watched video ids for a user and date."""

    @abstractmethod
    async def get_videos_batch(self, ids: list[str]) -> dict[str, Any]:
        """Return normalized video details for ids."""
