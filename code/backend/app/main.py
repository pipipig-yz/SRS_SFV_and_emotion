from contextlib import asynccontextmanager
from pathlib import Path
import asyncio
import uuid

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse

from .config import settings
from .repositories import get_repository
from .schemas.api import (
    BehaviorResponse,
    LoginRequest,
    LoginResponse,
    MentalStateResponse,
    VideoBatchRequest,
    VideoBatchResponse,
    VoiceTranscribeRequest,
    VoiceTranscribeResponse,
    WatchHistoryResponse,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=None))
    try:
        yield
    finally:
        await app.state.http.aclose()


app = FastAPI(title="SRS Research Chatbot API", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"ok": True, "service": "srs-fastapi", "data_backend": settings.data_backend}


@app.get("/")
async def index():
    return FileResponse(PROJECT_ROOT / "index.html")


@app.get("/index.html")
async def index_html():
    return FileResponse(PROJECT_ROOT / "index.html")


@app.get("/chat.html")
async def chat_html():
    return FileResponse(PROJECT_ROOT / "chat.html")


@app.post("/api/chat")
async def chat_proxy(request: Request):
    if not settings.deepseek_api_key:
        return JSONResponse(
            {"error": "DEEPSEEK_API_KEY is not set in .env"},
            status_code=500,
        )

    body = await request.body()
    upstream_request = app.state.http.build_request(
        "POST",
        settings.deepseek_url,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.deepseek_api_key}",
        },
        content=body,
    )

    try:
        upstream = await app.state.http.send(upstream_request, stream=True)
    except httpx.HTTPError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)

    if upstream.status_code >= 400:
        err_text = (await upstream.aread()).decode("utf-8", errors="replace")
        await upstream.aclose()
        return Response(
            content=err_text,
            status_code=upstream.status_code,
            media_type=upstream.headers.get("content-type", "text/plain"),
        )

    async def iter_upstream():
        try:
            async for chunk in upstream.aiter_bytes():
                yield chunk
        finally:
            await upstream.aclose()

    return StreamingResponse(
        iter_upstream(),
        media_type=upstream.headers.get("content-type", "text/event-stream"),
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def extract_asr_text(data: dict) -> str:
    result = data.get("result") or {}
    if isinstance(result.get("text"), str):
        return result["text"].strip()

    utterances = result.get("utterances") or data.get("utterances") or []
    parts = [
        item.get("text", "").strip()
        for item in utterances
        if isinstance(item, dict) and item.get("text")
    ]
    return "".join(parts).strip()


def volc_asr_headers(resource_id: str, request_id: str, sequence: str | None = "-1"):
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": settings.volc_asr_api_key,
        "X-Api-Resource-Id": resource_id,
        "X-Api-Request-Id": request_id,
    }
    if sequence is not None:
        headers["X-Api-Sequence"] = sequence
    return headers


async def transcribe_uploaded_audio(payload: VoiceTranscribeRequest, request_id: str):
    body = {
        "user": {"uid": settings.volc_asr_uid},
        "audio": {
            "data": payload.audio_data,
            "format": payload.format,
            "codec": payload.codec,
            "rate": payload.rate,
            "bits": payload.bits,
            "channel": payload.channel,
        },
        "request": {
            "model_name": "bigmodel",
            "enable_itn": True,
            "enable_punc": True,
            "enable_ddc": False,
            "enable_speaker_info": False,
            "enable_channel_split": False,
            "show_utterances": False,
            "vad_segment": False,
        },
    }
    res = await app.state.http.post(
        settings.volc_asr_flash_url,
        headers=volc_asr_headers(settings.volc_asr_flash_resource_id, request_id),
        json=body,
    )
    status_code = res.headers.get("X-Api-Status-Code")
    if status_code != "20000000":
        return JSONResponse(
            {
                "error": res.headers.get("X-Api-Message", "ASR recognize failed"),
                "status_code": status_code,
                "log_id": res.headers.get("X-Tt-Logid"),
                "body": res.text,
            },
            status_code=502,
        )

    text = extract_asr_text(res.json())
    return {
        "text": text,
        "request_id": request_id,
        "log_id": res.headers.get("X-Tt-Logid"),
    }


async def transcribe_audio_url(payload: VoiceTranscribeRequest, request_id: str):
    submit_body = {
        "user": {"uid": settings.volc_asr_uid},
        "audio": {
            "url": payload.audio_url,
            "format": payload.format,
            "codec": payload.codec,
            "rate": payload.rate,
            "bits": payload.bits,
            "channel": payload.channel,
        },
        "request": {
            "model_name": "bigmodel",
            "enable_itn": True,
            "enable_punc": True,
            "enable_ddc": False,
            "enable_speaker_info": False,
            "enable_channel_split": False,
            "show_utterances": False,
            "vad_segment": False,
            "sensitive_words_filter": "",
        },
    }
    submit = await app.state.http.post(
        settings.volc_asr_submit_url,
        headers=volc_asr_headers(settings.volc_asr_resource_id, request_id),
        json=submit_body,
    )
    submit_status = submit.headers.get("X-Api-Status-Code")
    log_id = submit.headers.get("X-Tt-Logid")
    if submit_status != "20000000":
        return JSONResponse(
            {
                "error": submit.headers.get("X-Api-Message", "ASR submit failed"),
                "status_code": submit_status,
                "log_id": log_id,
                "body": submit.text,
            },
            status_code=502,
        )

    query_headers = volc_asr_headers(
        settings.volc_asr_resource_id,
        request_id,
        sequence=None,
    )
    if log_id:
        query_headers["X-Tt-Logid"] = log_id

    for _ in range(30):
        await asyncio.sleep(1)
        query = await app.state.http.post(
            settings.volc_asr_query_url,
            headers=query_headers,
            json={},
        )
        query_status = query.headers.get("X-Api-Status-Code")
        log_id = query.headers.get("X-Tt-Logid") or log_id
        if query_status == "20000000":
            text = extract_asr_text(query.json())
            return {"text": text, "request_id": request_id, "log_id": log_id}
        if query_status not in {"20000001", "20000002"}:
            return JSONResponse(
                {
                    "error": query.headers.get("X-Api-Message", "ASR query failed"),
                    "status_code": query_status,
                    "log_id": log_id,
                    "body": query.text,
                },
                status_code=502,
            )

    return JSONResponse(
        {"error": "ASR task timed out", "request_id": request_id, "log_id": log_id},
        status_code=504,
    )


@app.post("/api/voice/transcribe", response_model=VoiceTranscribeResponse)
async def voice_transcribe(payload: VoiceTranscribeRequest):
    if not settings.volc_asr_api_key:
        return JSONResponse(
            {"error": "VOLC_ASR_API_KEY is not set in .env"},
            status_code=500,
        )
    if bool(payload.audio_data) == bool(payload.audio_url):
        return JSONResponse(
            {"error": "Provide exactly one of audio_data or audio_url"},
            status_code=400,
        )

    request_id = str(uuid.uuid4())
    try:
        if payload.audio_data:
            return await transcribe_uploaded_audio(payload, request_id)
        return await transcribe_audio_url(payload, request_id)
    except httpx.HTTPError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)


@app.post("/api/login", response_model=LoginResponse)
async def login(payload: LoginRequest):
    username = payload.username.strip()
    password = payload.password.strip()

    if not username or not password:
        return JSONResponse(
            {"success": False, "message": "请输入账号和密码"},
            status_code=400,
        )

    auth = await get_repository().authenticate(username, password)
    if not auth:
        return JSONResponse(
            {"success": False, "message": "账号或密码错误"},
            status_code=401,
        )

    return {
        "success": True,
        "user_id": auth["user_id"],
        "username": auth.get("username", username),
        "message": "登录成功",
    }


@app.get("/api/user/{user_id}/profile")
async def user_profile(user_id: str):
    profile = await get_repository().get_user_profile(user_id)
    if not profile:
        return JSONResponse({"error": "User not found"}, status_code=404)
    return profile


@app.get("/api/user/{user_id}/behavior", response_model=BehaviorResponse)
async def user_behavior(user_id: str, date: str = "today"):
    behavior = await get_repository().get_user_behavior(user_id, date)
    if not behavior:
        return JSONResponse({"error": "User not found"}, status_code=404)
    return behavior


@app.get("/api/user/{user_id}/mental_state", response_model=MentalStateResponse)
async def user_mental_state(user_id: str, date: str = "today"):
    mental_state = await get_repository().get_user_mental_state(user_id, date)
    if not mental_state:
        return JSONResponse({"error": "User not found"}, status_code=404)
    return mental_state


@app.get("/api/user/{user_id}/daily_behavior")
async def user_daily_behavior(user_id: str, date: str = "today"):
    daily_behavior = await get_repository().get_user_daily_behavior(user_id, date)
    if not daily_behavior:
        return JSONResponse({"error": "User not found"}, status_code=404)
    return daily_behavior


@app.get("/api/user/{user_id}/watch_history", response_model=WatchHistoryResponse)
async def user_watch_history(user_id: str, date: str = "today"):
    watch_history = await get_repository().get_user_watch_history(user_id, date)
    if not watch_history:
        return JSONResponse({"error": "User not found"}, status_code=404)
    return watch_history


@app.post("/api/videos/batch", response_model=VideoBatchResponse)
async def videos_batch(payload: VideoBatchRequest):
    return await get_repository().get_videos_batch(payload.ids)


@app.get("/api/video_info")
async def video_info(limit: int | None = None):
    safe_limit = min(max(limit, 1), 100) if limit is not None else None
    return await get_repository().get_video_info(safe_limit)
