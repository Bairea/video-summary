# Video Summary 开发指南

本地优先的视频总结器。输入 YouTube / Bilibili 视频链接，获取字幕（平台字幕或本地 ASR 转写），生成摘要、Markmap 导图与带引用的问答。以 Python 包 `vsum` 分发，提供 CLI 与 Web UI 两种使用方式，并面向 Agent 生态以 skill 形式分发。

## 技术栈

- **后端**：FastAPI + SQLite，Python >= 3.11，用 `uv` 管理。
- **前端**：React + TypeScript + Vite + Tailwind，构建后产物嵌入 `src/video_summary/static/`，由 Python 包一并分发。
- **ASR**：Apple Silicon 用 mlx-whisper，其他平台用 whisper.cpp CLI（用户自行安装到 PATH）。
- **字幕**：yt-dlp（平台字幕，Bilibili 部分需 cookies）。
- **AI**：支持 Anthropic Messages（`POST {base}/v1/messages`）与 OpenAI 兼容两种协议，由 `ai.provider` 切换；默认 Anthropic Messages 指向 yydsapi 网关（grok-4.6）。实现在 `services/openai_compat.py`（统一入口与分发）与 `services/anthropic_compat.py`。

## 模块结构（src/video_summary/）

- `cli.py` — `vsum` 命令入口（summarize / serve / tasks / task / config / models / skill / uninstall）。
- `api/` — FastAPI 路由（`app` 组装，`routes_tasks` / `routes_settings`）。
- `services/` — 领域逻辑：`task_service`（流水线编排）、`ytdlp_service`、`whisper_service`、`subtitle_service`、`summary_service`、`mindmap_service`、`qa_service`、`openai_compat`、`job_queue`、`file_store`、`health_service`。
- `repositories/` — SQLite 持久化（task / transcript / summary / mindmap / qa / settings）。
- `lib/` — 工具：cookies、retry、ai_http（AI 网关共用：Base URL 归一化/可取消等待）、errors（跨层错误类型）、字幕格式与解析。
- `paths.py` — 数据/任务/模型目录解析（XDG，可用环境变量覆盖）。
- `types.py` — 领域类型与默认配置（`default_settings`）。
- `skills/` — 随 `vsum skill install` 分发到 `~/.claude/skills/` 的 Agent skill。

## 流水线阶段

parse → download → subtitles → summary → mindmap → qaIndex。阶段可独立失败；重试会跳过已完成阶段续跑（依据持久化的 artifacts + 磁盘产物），只补做失败部分。qaIndex 为就绪标记：问答检索在提问时按相关度现场计算，无独立索引。任务数超出 `storage.maxTasks`（默认 200）时自动清理最旧的非活动任务。

## ASR 引擎

| 平台 | 引擎 | 依赖 |
|------|------|------|
| Apple Silicon (M1/M2/M3/M4) | mlx-whisper | pip 依赖 |
| 其他 | whisper.cpp CLI | 用户自行安装到 PATH |

配置 `transcriptionModel` 默认 `large-v3-turbo`，whisper_service 内部映射到各引擎模型 ID（未命中的尺寸回退到 `large-v3`）。模型下载 fallback：HuggingFace → ModelScope。

## 常用命令

```bash
uv sync                 # Python 依赖
npm install             # 前端依赖
npm run build           # 构建前端到 src/video_summary/static/
uv run pytest           # 测试
npm run check           # 前端类型检查
uv run uvicorn video_summary.api.app:app --port 3001   # 仅后端
npm run dev             # 前端开发模式（vite，代理 /api 到 3001）
```

CLI 使用：

```bash
uv run vsum summarize "https://...youtube..." --json
uv run vsum serve --open
uv run vsum config set ai.apiKey sk-xxx
uv run vsum models --download
uv run vsum skill install
```

## 关键约定

- 数据目录：`~/.local/share/video-summary/`，可用 `VIDEO_SUMMARY_DATA_DIR` 覆盖。
- Web 服务仅监听 `127.0.0.1`；CORS 只放行 localhost 来源（本机无鉴权 API 不对任意网页开放）。
- 模型目录：`resolve_models_dir()`，默认 `large-v3-turbo`。
- 前端静态目录：`resolve_static_dir()`，环境变量 `VIDEO_SUMMARY_STATIC_DIR` 优先，其次包内 `static/`。
- 平台字幕优先，本地转写兜底（由 `ai.asrEnabled` 控制）。
- 领域术语（Task / Pipeline / 阶段）见 `CONTEXT.md`。

## 发布

```bash
uv build
uv publish
```