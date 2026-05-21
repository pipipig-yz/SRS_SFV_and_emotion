# SRS Interview — 开发日志

## 2026-05-21

### 当前状态

- 后端已迁移到 FastAPI。
- Node.js 后端、`server.js`、`package.json`、`package-lock.json` 和 `node_modules` 已移除。
- 已重新接入语音 ASR：前端麦克风录音编码为 16k 单声道 WAV，后端通过火山引擎豆包 ASR 代理识别。
- PostgreSQL 暂未接入，当前数据层使用 `DATA_BACKEND=mock` 读取 `database_example` 示例数据。

### 已完成

#### FastAPI 后端
- 新增 `backend/app/main.py`，提供静态页面、聊天代理和数据接口。
- 新增 `backend/app/config.py`，通过 Pydantic Settings 读取 `.env`。
- 新增 `backend/requirements.txt`，管理 Python 依赖。
- `POST /api/chat` 迁移为 FastAPI DeepSeek 流式代理。
- `GET /`、`GET /index.html`、`GET /chat.html` 由 FastAPI 返回静态页面。
- `GET /health` 返回服务状态和当前数据源。

#### 登录与上下文接口
- `POST /api/login`：当前 mock 登录，任意非空账号密码映射到示例用户 `u_007`。
- `GET /api/user/{user_id}/profile`
- `GET /api/user/{user_id}/behavior?date=today`
- `GET /api/user/{user_id}/mental_state?date=today`
- `GET /api/user/{user_id}/watch_history?date=today`
- `POST /api/videos/batch`
- `POST /api/voice/transcribe`

#### 数据层
- 新增 `backend/app/repositories`，隔离 API 路由和数据来源。
- 新增 `MockRepository`，读取 `database_example` 下的 JSON 示例数据。
- 新增 `backend/app/schemas`，定义主要接口的 Pydantic request/response schema。
- `.env.example` 增加 `DATA_BACKEND=mock` 和 `DATABASE_URL=` 预留项。

#### 前端
- `index.html` 登录流程改为请求 `/api/login`。
- `chat.html` 启动时会从 FastAPI 拉取用户档案、行为、心理状态、观看历史和视频详情，再注入 System Prompt。
- 如果上下文接口失败，`chat.html` 会回退到本地 mock 数据。
- `DEFAULT_PROMPT` 已替换为 `system_prompt_ZH.md` 的正式中文版内容。
- `chat.html` 新增语音输入按钮；点击开始录音，再次点击停止并转写，识别文字会填入输入框。
- 后端新增火山引擎 ASR 代理，密钥只从 `.env` 读取，不暴露到前端。

### 暂未实现

| 项目 | 说明 |
|------|------|
| PostgreSQL | `DATABASE_URL` 已预留，尚未接 asyncpg 连接池和真实 SQL |
| JWT + bcrypt | 当前仍是 mock 登录，尚未做正式认证 |
| OSS | 暂未接入阿里云 OSS |

### 启动方式

```bash
cd /Users/zhuyucheng/Desktop/SRS/chatbot/code
source .venv/bin/activate
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 3000
```
