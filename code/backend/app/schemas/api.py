from typing import Any

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = ""
    password: str = ""


class LoginResponse(BaseModel):
    success: bool
    user_id: str | None = None
    username: str | None = None
    message: str


class BehaviorSession(BaseModel):
    time: str
    dur: int
    note: str


class BehaviorResponse(BaseModel):
    user_id: str
    date: str
    today_minutes: int
    today_videos: int
    baseline_7d_minutes: int
    scroll_speed_vph: int
    like_rate: float
    comment_rate: float
    share_rate: float
    peak_hour: str
    sessions: list[BehaviorSession]


class MentalStateResponse(BaseModel):
    user_id: str
    date: str
    avg_stress_score_7d: float
    avg_sleep_hours_7d: float
    avg_mood_score_7d: float
    today_self_reported_pressure: float


class WatchHistoryResponse(BaseModel):
    user_id: str
    date: str
    video_ids: list[str]


class VideoBatchRequest(BaseModel):
    ids: list[str] = Field(default_factory=list)


class VideoResponse(BaseModel):
    video_id: str | None
    title: str
    author: str
    category: str
    duration: str
    share_url: str
    cover: str
    play_count: int
    digg_count: int
    comment_count: int
    share_count: int
    comments: list[str]


class VideoBatchResponse(BaseModel):
    videos: list[VideoResponse]


class VoiceTranscribeRequest(BaseModel):
    audio_data: str | None = None
    audio_url: str | None = None
    format: str = "wav"
    codec: str = "raw"
    rate: int = 16000
    bits: int = 16
    channel: int = 1


class VoiceTranscribeResponse(BaseModel):
    text: str
    request_id: str
    log_id: str | None = None


UserProfileResponse = dict[str, Any]
