import json
from functools import lru_cache
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT.parent / "database_example"


@lru_cache
def load_user_profile() -> dict:
    with (DATA_ROOT / "user_profile.json").open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache
def load_daily_behavior() -> dict:
    with (DATA_ROOT / "daily_behavior.json").open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache
def load_douyin_sample() -> dict:
    sample_path = DATA_ROOT / "douyin_sample.json"
    if not sample_path.exists():
        return load_video_info()
    with sample_path.open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache
def load_video_info() -> dict:
    with (DATA_ROOT / "video_info.json").open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache
def load_summarized_video_info() -> list[dict]:
    with (DATA_ROOT / "summarize_video_info.json").open(encoding="utf-8") as f:
        return json.load(f)


def get_summarized_video_info(limit: int | None = None) -> dict:
    videos = load_summarized_video_info()
    included = videos[:limit] if limit else videos
    return {
        "source_file": "database_example/summarize_video_info.json",
        "total_videos": len(videos),
        "included_videos": len(included),
        "videos": included,
    }


def normalize_user_id(username: str) -> str:
    profile = load_user_profile()
    if username == profile["user_id"]:
        return profile["user_id"]
    return profile["user_id"]


def get_video_index() -> dict[str, dict]:
    return {v["video_id"]: v for v in load_douyin_sample().get("videos", [])}


def get_watch_video_ids(limit: int = 5) -> list[str]:
    videos = load_douyin_sample().get("videos", [])
    return [v["video_id"] for v in videos[:limit]]


def infer_category(video: dict) -> str:
    title = video.get("title", "")
    if "爷爷" in title or "万万想不到" in title:
        return "三农/搞笑"
    if "焦虑" in title or "学姐" in title or "经验" in title:
        return "知识/学习"
    if "宿舍" in title or "深夜" in title:
        return "情感/日常"
    return "短视频"


def normalize_video(video: dict) -> dict:
    statistics = video.get("statistics", {})
    duration = video.get("duration") or video.get("dur") or "未知"
    return {
        "video_id": video.get("video_id"),
        "title": video.get("title", ""),
        "author": video.get("author", ""),
        "category": video.get("category") or infer_category(video),
        "duration": str(duration),
        "share_url": video.get("share_url", ""),
        "cover": video.get("cover", ""),
        "play_count": statistics.get("play_count", 0),
        "digg_count": statistics.get("digg_count", 0),
        "comment_count": statistics.get("comment_count", 0),
        "share_count": statistics.get("share_count", 0),
        "comments": statistics.get("comments", []),
    }
