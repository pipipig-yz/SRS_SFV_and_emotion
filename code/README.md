# SRS 研究对话助手 — 开发说明

## 文件结构

```
interview/
├── index.html   # 登录页（入口）
├── chat.html    # 对话助手主界面
├── backend/     # FastAPI 后端
└── README.md    # 本文件
```

## 本地启动

```bash
cd interview
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env    # 如果本地还没有 .env
# 编辑 .env，至少填入 DEEPSEEK_API_KEY
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 3000
# 浏览器访问 http://localhost:3000
```

当前 FastAPI 已迁移：
- `GET /`、`GET /index.html`、`GET /chat.html`
- `GET /health`
- `POST /api/chat`（DeepSeek 流式代理）
- `POST /api/login`（阶段 2 mock 登录：任意非空账号密码映射到示例用户 `u_007`）
- `GET /api/user/{user_id}/profile`
- `GET /api/user/{user_id}/behavior?date=today`
- `GET /api/user/{user_id}/mental_state?date=today`
- `GET /api/user/{user_id}/watch_history?date=today`
- `POST /api/videos/batch`
- `POST /api/voice/transcribe`（火山引擎豆包 ASR 代理，支持页面麦克风 WAV base64，也支持公网 `audio_url` 轮询）

当前 FastAPI 数据层：
- API 路由通过 `backend/app/repositories` 访问数据
- `DATA_BACKEND=mock` 时读取 `database_example` 下的 JSON 示例数据
- `DATABASE_URL` 已预留给 PostgreSQL 迁移阶段，当前不会连接数据库

阶段 3 测试：

```bash
curl http://localhost:3000/health
curl -X POST http://localhost:3000/api/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"demo","password":"demo"}'
curl http://localhost:3000/api/user/u_007/profile
curl http://localhost:3000/api/user/u_007/watch_history?date=today
curl -X POST http://localhost:3000/api/videos/batch \
  -H 'Content-Type: application/json' \
  -d '{"ids":["7637444698836287146"]}'
```

浏览器测试：
- 打开 `http://localhost:3000`
- 任意输入非空账号和密码登录
- 进入 `chat.html` 后，页面会从 FastAPI 拉取用户档案、行为、心理状态和视频数据，再注入 System Prompt
- 发送一条消息，确认文本聊天仍然能流式回复

`.env` 文件格式：

```env
# Server
PORT=3000

# 数据源。当前阶段只支持 mock，后续 PostgreSQL 阶段会支持 postgres
DATA_BACKEND=mock

# PostgreSQL 连接串预留；当前 mock 阶段可留空
DATABASE_URL=

# DeepSeek chat proxy
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Volcengine Doubao ASR
VOLC_ASR_API_KEY=your_volc_asr_api_key_here
VOLC_ASR_UID=srs-chatbot
VOLC_ASR_FLASH_RESOURCE_ID=volc.bigasr.auc_turbo
VOLC_ASR_RESOURCE_ID=volc.seedasr.auc
```

说明：
- `.env.example` 是可提交的模板，不放真实密钥。
- `.env` 是本地真实配置文件，已被 `.gitignore` 忽略。
- 文本聊天至少需要 `DEEPSEEK_API_KEY`。
- 语音输入至少需要 `VOLC_ASR_API_KEY`；麦克风录音走极速版 `recognize/flash`，公网音频 URL 可走标准版 `submit/query`。

---

## 待完善事项

### 1. 完善用户登录流程

**目标**：用户输入账号和密码后，通过后端验证，获得对应的 `user_id`，再跳转到对话界面。

**当前状态**：`index.html` 中的登录为占位实现，任意账号密码均可通过，`user_id` 由账号名临时生成。

**需要做的事**：

- [ ] 搭建后端登录接口 `POST /api/login`，接收 `{ username, password }`，返回 `{ success, user_id, message }`
- [ ] 将 `index.html` 中的临时占位逻辑替换为真实 `fetch` 请求（代码注释中已提供示例）
- [ ] 登录成功后将 `user_id` 写入 `sessionStorage`，跳转到 `chat.html`
- [ ] `chat.html` 启动时读取 `sessionStorage.getItem('userId')`，用该 ID 查询数据库，拉取该用户的档案数据注入系统提示词

**关键代码位置**：
- 登录占位逻辑：`index.html` → `handleLogin()` 函数，约第 130 行
- 数据库注入逻辑：`chat.html` → `DB` 对象 和 `buildContext()` 函数

---

### 2. 接入真实数据库并构建 Chat 上下文

`chat.html` 启动时，需根据 `sessionStorage` 中的 `user_id` 完成以下两条并行查询链，将结果合并后注入 System Prompt。

#### 查询链 A — 用户数据

```
user_id
  ├─→ 查询 user_profile 表      → 用户基本档案（年龄、专业、学业阶段等）
  ├─→ 查询 sfv_behavior 表      → 用户今日短视频行为数据（时长、时段、滑动速度等）
  └─→ 查询 mental_state 表      → 用户今日心理状态（压力得分、睡眠、情绪等）
```

- [ ] 实现 `GET /api/user/{user_id}/profile`
- [ ] 实现 `GET /api/user/{user_id}/behavior?date=today`
- [ ] 实现 `GET /api/user/{user_id}/mental_state?date=today`

#### 查询链 B — 今日视频内容

```
user_id
  └─→ 查询 watch_history 表     → 获取该用户今日观看的视频 ID 列表
        └─→ 批量查询 videos 表  → 根据视频 ID 列表取回视频详情
```

- [ ] 实现 `GET /api/user/{user_id}/watch_history?date=today` → 返回 `video_id[]`
- [ ] 实现 `POST /api/videos/batch` 接收 `{ ids: video_id[] }` → 返回视频详情列表

#### System Prompt 中视频内容的格式

两条查询链完成后，将视频详情以**表格**形式注入 System Prompt，格式如下：

```
| 序号 | 视频ID | 标题 | 分类 | 时长 | 播放量 | 点赞数 | 评论数 | 评论摘要（前10条）|
|------|--------|------|------|------|--------|--------|--------|------------------|
| 1    | 763744 | 当我拿假鸡蛋逗爷爷玩 | 三农/搞笑 | 5:19 | 962万 | 10.8万 | 1.3万 | "爷爷太可爱了…" "笑死我了…" … |
| 2    | ...    | ...  | ...  | ...  | ...    | ...    | ...    | ...              |
```

**评论处理规则**：
- 每条视频只取前 **10** 条评论（`comments[0..9]`），拼接成一个字符串注入表格最后一列
- 评论数量上限（当前为 10）后续可根据 token 预算调整，调整位置在 `chat.html → buildContext()` 函数中的 `COMMENT_LIMIT` 常量

---

### 3. Chat System Prompt 最终构成

登录 → 查询完成后，注入 System Prompt 的完整内容为：

| 模块 | 来源 | 说明 |
|------|------|------|
| 用户档案 | `user_profile` 表 | 年龄、性别、专业、学业阶段、压力背景 |
| 行为数据 | `sfv_behavior` 表 | 今日观看时长、时段分布、滑动速度、互动率等 |
| 心理状态 | `mental_state` 表 | 今日及近 7 日压力/情绪/睡眠得分 |
| 今日视频内容 | `watch_history` + `videos` 表 | 表格形式，含视频 ID、标题、分类、统计数据、前 10 条评论 |
