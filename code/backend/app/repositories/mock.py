from typing import Any

from .base import DataRepository
from ..mock_data import (
    get_summarized_video_info,
    get_video_index,
    get_watch_video_ids,
    load_daily_behavior,
    load_user_profile,
    normalize_user_id,
    normalize_video,
)


class MockRepository(DataRepository):
    async def authenticate(self, username: str, password: str) -> dict[str, Any] | None:
        if not username or not password:
            return None

        # Mock auth accepts any non-empty credential and maps to the sample user.
        # Real JWT + bcrypt auth will replace this in the PostgreSQL repository.
        return {
            "user_id": normalize_user_id(username),
            "username": username,
        }

    async def get_user_profile(self, user_id: str) -> dict[str, Any] | None:
        profile = load_user_profile()
        if user_id != profile["user_id"]:
            return None
        return profile

    async def get_user_behavior(self, user_id: str, date: str) -> dict[str, Any] | None:
        profile = await self.get_user_profile(user_id)
        if not profile:
            return None

        daily = load_daily_behavior()
        if daily["user_id"] != user_id:
            return None

        behavior = daily["daily_sfv_behavior"]
        return {
            "user_id": user_id,
            "date": date,
            "today_minutes": behavior["today_minutes"],
            "today_videos": behavior["today_videos"],
            "baseline_7d_minutes": behavior["baseline_7d_minutes"],
            "scroll_speed_vph": behavior["scroll_speed_vph"],
            "like_rate": behavior["like_rate"],
            "comment_rate": behavior["comment_rate"],
            "share_rate": behavior["share_rate"],
            "peak_hour": behavior["peak_hour"],
            "sessions": behavior["sessions"],
        }

    async def get_user_mental_state(self, user_id: str, date: str) -> dict[str, Any] | None:
        profile = await self.get_user_profile(user_id)
        if not profile:
            return None

        daily = load_daily_behavior()
        if daily["user_id"] != user_id:
            return None

        mental = daily["daily_mental_state"]
        return {
            "user_id": user_id,
            "date": date,
            "avg_stress_score_7d": mental["avg_stress_score_7d"],
            "avg_sleep_hours_7d": mental["avg_sleep_hours_7d"],
            "avg_mood_score_7d": mental["avg_mood_score_7d"],
            "today_self_reported_pressure": mental["today_self_reported_pressure"],
        }

    async def get_user_daily_behavior(self, user_id: str, date: str) -> dict[str, Any] | None:
        profile = await self.get_user_profile(user_id)
        if not profile:
            return None

        daily = load_daily_behavior()
        if daily["user_id"] != user_id:
            return None
        return daily | {"date": date}

    async def get_user_watch_history(self, user_id: str, date: str) -> dict[str, Any] | None:
        profile = await self.get_user_profile(user_id)
        if not profile:
            return None
        return {"user_id": user_id, "date": date, "video_ids": get_watch_video_ids()}

    async def get_videos_batch(self, ids: list[str]) -> dict[str, Any]:
        video_index = get_video_index()
        return {"videos": [normalize_video(video_index[vid]) for vid in ids if vid in video_index]}

    async def get_video_info(self, limit: int | None = None) -> dict[str, Any]:
        return get_summarized_video_info(limit=limit)
