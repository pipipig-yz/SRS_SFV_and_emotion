# SRS 研究对话助手 — 开发说明

## 文件结构

```text
chatbot/
├── code/
│   ├── index.html                  # 登录页
│   ├── chat.html                   # 对话助手主界面
│   ├── summarize_video_info.py     # DeepSeek 视频总结脚本
│   ├── backend/                    # FastAPI 后端
│   └── README.md                   # 本文件
└── database_example/
    ├── user_profile.json           # 用户档案与 baseline
    ├── daily_behavior.json         # 今日行为与今日心理状态
    ├── video_info.json             # 今日原始视频内容数据
    ├── summarize_video_info.json   # 视频总结 agent 输出
    └── douyin_full.json            # 原始抖音全量样例数据
```

## 本地启动

```bash
cd /Users/zhuyucheng/Desktop/SRS/chatbot/code
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env    # 如果本地还没有 .env
# 编辑 .env，至少填入 DEEPSEEK_API_KEY
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 3001
# 浏览器访问 http://localhost:3001
```

如果 3001 被占用，可以换成其他端口；页面和接口都由同一个 FastAPI 服务提供。

## 当前 API

- `GET /`、`GET /index.html`、`GET /chat.html`
- `GET /health`
- `POST /api/login`：mock 登录，任意非空账号密码都会映射到示例用户 `u_007`
- `POST /api/chat`：DeepSeek 流式代理
- `GET /api/user/{user_id}/profile`
- `GET /api/user/{user_id}/behavior?date=today`
- `GET /api/user/{user_id}/mental_state?date=today`
- `GET /api/user/{user_id}/daily_behavior?date=today`
- `GET /api/user/{user_id}/watch_history?date=today`
- `POST /api/videos/batch`
- `GET /api/video_info`
- `POST /api/voice/transcribe`

## 数据流

### 1. User ID 查询用户数据

登录成功后，前端把 `user_id` 写入 `sessionStorage`。进入 `chat.html` 后，前端用这个 `user_id` 拉取用户相关数据。

```text
user_id
  ├─→ GET /api/user/{user_id}/profile
  │     └─→ database_example/user_profile.json
  │
  ├─→ GET /api/user/{user_id}/behavior?date=today
  │     └─→ database_example/daily_behavior.json
  │
  ├─→ GET /api/user/{user_id}/mental_state?date=today
  │     └─→ database_example/daily_behavior.json
  │
  └─→ GET /api/user/{user_id}/daily_behavior?date=today
        └─→ database_example/daily_behavior.json
```

`user_profile.json` 放用户相对稳定的信息：

- 基本档案：年龄、性别、专业、学业阶段、学校匿名信息
- 压力背景：当前是否期末周、考试数量、距下次考试天数、自评学业压力
- 心理 baseline：近 7 日压力、睡眠、情绪均值
- 短视频行为 baseline：日均观看时长、滑动速度、互动率、峰值使用时间
- 内容偏好：偏好类别、回避类别、不同类别平均停留时间
- 对话画像：回答风格、敏感话题、容易展开的话题

`daily_behavior.json` 放当天状态和当天行为：

- `daily_sfv_behavior`：今日观看时长、视频数量、观看时段、滑动速度、点赞率、评论率、转发率
- `daily_mental_state`：今日自评压力，以及近 7 日压力/睡眠/情绪均值
- 同时保留 `stress_context`、`baseline_mental_state`、`sfv_behavior_baseline`，方便单独检查这一天的完整输入

### 2. 视频数据查询与总结

当前视频链路分两步：先准备原始视频 JSON，再用一个单独的 DeepSeek summarizer 生成总结文件。

```text
原始今日视频数据
  └─→ database_example/video_info.json
        └─→ code/summarize_video_info.py
              └─→ DeepSeek 总结
                    └─→ database_example/summarize_video_info.json
```

`video_info.json` 是今日刷到的视频原始内容数据，包含：

- `video_id`
- `title`
- `author`
- `category`
- `share_url`
- 播放/点赞/评论/转发等统计
- 评论列表

`summarize_video_info.py` 会读取完整 `video_info.json`，但每条视频只传前 20 条评论给 DeepSeek，避免评论过多。它的输出是 `summarize_video_info.json`，每条视频格式为：

```json
{
  "video_id": "7637444698836287146",
  "title": "当我拿假鸡蛋逗爷爷玩，看爷爷是什么反应#我的乡村生活 #万万想不到",
  "author": "世豪在农村",
  "category": "三农",
  "share_url": "https://www.douyin.com/video/7637444698836287146",
  "summarize": "视频中，孙子用假鸡蛋逗爷爷..."
}
```

重新生成视频总结：

```bash
cd /Users/zhuyucheng/Desktop/SRS/chatbot/code
source .venv/bin/activate
python summarize_video_info.py
```

前端 `Video Info` 默认读取：

```text
GET /api/video_info
  └─→ database_example/summarize_video_info.json
```

## 最终 System Prompt 构成

`chat.html` 左侧是测试版输入区，包含四块可编辑内容：

- `System Prompt`
- `User Context`
- `Daily Behavior`
- `Video Info`

提交时，前端把四块内容组装成第一条 `system` message，再调用 `/api/chat` 转发给 DeepSeek。

默认模板中有三个占位符：

```text
【背景数据】
{USER_CONTEXT}

【Daily Behavior】
{DAILY_BEHAVIOR}

【Video Info】
{VIDEO_INFO}
```

提交逻辑：

- `User Context` 默认来自 `user_profile.json`
- `Daily Behavior` 默认来自 `daily_behavior.json`
- `Video Info` 默认来自 `summarize_video_info.json`
- 如果 `System Prompt` 里有 `{USER_CONTEXT}`，前端用左侧 `User Context` 替换
- 如果 `System Prompt` 里有 `{DAILY_BEHAVIOR}`，前端用左侧 `Daily Behavior` 替换
- 如果 `System Prompt` 里有 `{VIDEO_INFO}`，前端用左侧 `Video Info` 替换
- 如果用户删掉占位符，前端会把对应内容追加到 prompt 末尾
- 最终发送给 DeepSeek 的第一条消息是：

```js
{ role: "system", content: composedSystemPrompt }
```

后续用户消息和模型回复会继续追加到 `history` 中。

## database_example 文件说明

| 文件 | 用途 |
|------|------|
| `user_profile.json` | 用户基本档案、压力背景、心理 baseline、短视频行为 baseline、内容偏好、对话画像 |
| `daily_behavior.json` | 今日短视频行为和今日心理状态，替代原先写在 `mock.py` 里的硬编码 daily 数据 |
| `video_info.json` | 今日视频原始数据，包含标题、作者、分类、链接、统计数据和评论 |
| `summarize_video_info.json` | DeepSeek summarizer 对 `video_info.json` 的总结结果，前端实际注入 System Prompt 的视频信息 |
| `douyin_full.json` | 更大的原始抖音样例数据，目前主要作为原始数据备份/参考 |

## 快速测试

```bash
curl http://localhost:3001/health
curl -X POST http://localhost:3001/api/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"demo","password":"demo"}'
curl http://localhost:3001/api/user/u_007/profile
curl 'http://localhost:3001/api/user/u_007/behavior?date=today'
curl 'http://localhost:3001/api/user/u_007/mental_state?date=today'
curl 'http://localhost:3001/api/user/u_007/daily_behavior?date=today'
curl http://localhost:3001/api/video_info
```

浏览器测试：

- 打开 `http://localhost:3001`
- 任意输入非空账号和密码登录
- 进入 `chat.html`
- 左侧确认 `User Context`、`Daily Behavior` 和 `Video Info`
- 修改后点击“提交并开始对话”

## 环境变量

```env
# Server
PORT=3000

# 数据源。当前阶段只支持 mock，后续 PostgreSQL 阶段会支持 postgres
DATA_BACKEND=mock

# PostgreSQL 连接串预留；当前 mock 阶段可留空
DATABASE_URL=

# DeepSeek chat proxy / video summarizer
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Volcengine Doubao ASR
VOLC_ASR_API_KEY=your_volc_asr_api_key_here
VOLC_ASR_UID=srs-chatbot
VOLC_ASR_FLASH_RESOURCE_ID=volc.bigasr.auc_turbo
VOLC_ASR_RESOURCE_ID=volc.seedasr.auc
```

说明：

- `.env.example` 是可提交模板，不放真实密钥。
- `.env` 是本地真实配置文件，已被 `.gitignore` 忽略。
- 文本聊天和 `summarize_video_info.py` 至少需要 `DEEPSEEK_API_KEY`。
- 语音输入至少需要 `VOLC_ASR_API_KEY`。
