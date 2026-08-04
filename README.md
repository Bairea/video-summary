# Video Summary

本地优先的视频总结器：输入 YouTube / Bilibili 视频链接，获取字幕（平台字幕或本地 faster-whisper 转写），生成摘要、Markmap 导图与带引用的问答。提供 CLI 与 Web UI 两种使用方式，并面向 Agent 生态以 skill 形式分发。

## 特性

- 平台字幕优先，本地 ASR 兜底（faster-whisper，跨平台 CPU/CUDA）
- 摘要 / Markmap 导图 / 引用式问答（OpenAI 兼容 API，支持 DashScope 等）
- 单向 CLI（`vsum summarize`）与 Web UI（`vsum serve`）共用同一流水线
- Agent skill 分发：`vsum skill install` 安装到 `~/.claude/skills/`
- 干净卸载：`vsum uninstall`（保守）与 `vsum uninstall --purge-all`

## 安装

```bash
uv tool install vsum
# 或 pip install vsum
```

首次使用前：

```bash
# 下载 ASR 模型（约 1-2 GB）
vsum models --download

# 配置 AI（Base URL / API Key / Model）
vsum config set ai.baseUrl https://dashscope.aliyuncs.com/compatible-mode
vsum config set ai.apiKey sk-xxx
vsum config set ai.model qwen-plus
```

## 使用

### CLI（单向总结）

```bash
vsum summarize "https://www.youtube.com/watch?v=..."          # 输出摘要 Markdown
vsum summarize "https://www.bilibili.com/video/BV1xx" --json   # 结构化输出（agent 友好）
```

### Web UI

```bash
vsum serve --open   # http://127.0.0.1:3001
```

### Agent skill

```bash
vsum skill install     # 安装到 ~/.claude/skills/video-summary
vsum skill uninstall   # 移除
```

### 卸载

```bash
vsum uninstall             # 移除 skill 与临时痕迹，保留数据/模型
vsum uninstall --purge-all # 同时删除数据目录与模型缓存
# CLI 本体：uv tool uninstall vsum
```

## 数据目录

- 数据（SQLite、任务产物）：`~/.local/share/video-summary/`（可用 `VIDEO_SUMMARY_DATA_DIR` 覆盖）
- Bilibili cookies：`~/.local/share/video-summary/cookies.txt`（`vsum config set download.cookiesPath` 可指向其他路径）

## 开发

```bash
uv sync            # Python 依赖
npm install        # 前端依赖
npm run build      # 构建前端到 src/video_summary/static/
uv run pytest      # 测试
npm run check      # 前端类型检查
uv run uvicorn video_summary.api.app:app --port 3001   # 仅后端
npm run dev        # 前端开发模式（vite，代理 /api 到 3001）
```

## License

MIT
