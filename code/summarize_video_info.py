import argparse
import json
import os
import re
from pathlib import Path

import httpx


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_ROOT = PROJECT_ROOT.parent / "database_example"
INPUT_PATH = DATA_ROOT / "video_info.json"
OUTPUT_PATH = DATA_ROOT / "summarize_video_info.json"
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"


SYSTEM_PROMPT = """你是一个视频信息总结助手。

你的任务是通过读取每条视频的 title、category 和 comment 来总结视频内容，生成 summarize。
要求：
- 输出必须是合法 JSON，不要使用 Markdown 代码块。
- 输出 JSON 顶层必须是数组。
- 数组中每个对象必须包含：video_id, title, author, category, share_url, summarize。
- 必须覆盖输入中的每一条视频。
- summarize 用中文，简洁但信息完整。
- summarize 优先关注视频内容信息：主要人物、事件、场景、动作、物品、话题关键词和内容走向。
- summarize 可以补充情绪氛围和评论区主要反馈，但不要让评论反馈盖过视频本身内容。
- 不要编造输入中没有的信息。"""


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def trim_video(video: dict, comment_limit: int) -> dict:
    statistics = video.get("statistics") or {}
    comments = statistics.get("comments") or []
    return {
        "video_id": video.get("video_id", ""),
        "title": video.get("title", ""),
        "author": video.get("author", ""),
        "category": video.get("category", ""),
        "share_url": video.get("share_url", ""),
        "comments": comments[:comment_limit],
    }


def extract_json(content: str) -> list[dict]:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            raise
        data = json.loads(match.group(0))
    if not isinstance(data, list):
        raise ValueError("DeepSeek response must be a JSON array")
    return data


def summarize_videos(input_path: Path, output_path: Path, comment_limit: int, model: str) -> list[dict]:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set. Put it in code/.env or export it.")

    source = json.loads(input_path.read_text(encoding="utf-8"))
    videos = [trim_video(video, comment_limit) for video in source.get("videos", [])]
    payload = {
        "source_file": str(input_path),
        "comment_limit_per_video": comment_limit,
        "total_videos": len(videos),
        "videos": videos,
    }

    user_prompt = (
        "请总结下面 video_info 输入中的全部视频。"
        "每条视频只参考给出的 title、category 和 comments，同时保留 video_id、title、author、category、share_url。"
        "summarize 要更关注视频本身的具体内容信息和关键词。\n\n"
        + json.dumps(payload, ensure_ascii=False)
    )

    with httpx.Client(timeout=httpx.Timeout(120.0)) as client:
        response = client.post(
            DEEPSEEK_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 4000,
                "stream": False,
            },
        )
        response.raise_for_status()

    content = response.json()["choices"][0]["message"]["content"]
    summarized = extract_json(content)
    output_path.write_text(
        json.dumps(summarized, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summarized


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize database_example/video_info.json with DeepSeek.")
    parser.add_argument("--input", type=Path, default=INPUT_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--comment-limit", type=int, default=20)
    parser.add_argument("--model", default="deepseek-chat")
    args = parser.parse_args()

    load_env(PROJECT_ROOT / ".env")
    summarized = summarize_videos(args.input, args.output, args.comment_limit, args.model)
    print(f"Wrote {len(summarized)} summarized videos to {args.output}")


if __name__ == "__main__":
    main()
