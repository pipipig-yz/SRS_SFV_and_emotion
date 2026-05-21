from typing import Any

from .base import DataRepository
from ..mock_data import (
    get_video_index,
    get_watch_video_ids,
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

        baseline = profile["sfv_behavior_baseline"]
        return {
            "user_id": user_id,
            "date": date,
            "today_minutes": 68,
            "today_videos": 31,
            "baseline_7d_minutes": baseline["avg_daily_watch_minutes"],
            "scroll_speed_vph": baseline["avg_scroll_speed_vph"],
            "like_rate": baseline["avg_like_rate"],
            "comment_rate": baseline["avg_comment_rate"],
            "share_rate": baseline["avg_share_rate"],
            "peak_hour": "22:30",
            "sessions": [
                {"time": "14:00-14:20", "dur": 20, "note": "午休结束后"},
                {"time": "19:30-19:43", "dur": 13, "note": "晚饭后短暂刷"},
                {"time": "22:30-23:15", "dur": 45, "note": "睡前主要时段"},
            ],
        }

    async def get_user_mental_state(self, user_id: str, date: str) -> dict[str, Any] | None:
        profile = await self.get_user_profile(user_id)
        if not profile:
            return None

        baseline = profile["baseline_mental_state"]
        return {
            "user_id": user_id,
            "date": date,
            "avg_stress_score_7d": baseline["avg_stress_score_7d"],
            "avg_sleep_hours_7d": baseline["avg_sleep_hours_7d"],
            "avg_mood_score_7d": baseline["avg_mood_score_7d"],
            "today_self_reported_pressure": profile["stress_context"]["self_reported_academic_pressure"],
        }

    async def get_user_watch_history(self, user_id: str, date: str) -> dict[str, Any] | None:
        profile = await self.get_user_profile(user_id)
        if not profile:
            return None
        return {"user_id": user_id, "date": date, "video_ids": get_watch_video_ids()}

    async def get_videos_batch(self, ids: list[str]) -> dict[str, Any]:
        video_index = get_video_index()
        return {"videos": [normalize_video(video_index[vid]) for vid in ids if vid in video_index]}
