# Video Summary

本地优先的视频总结器：输入 YouTube / Bilibili 视频链接，获取字幕（平台字幕或本地 faster-whisper 转写），生成摘要、Markmap 导图与带引用的问答。提供 CLI 与 Web UI 两种使用方式，并面向 Agent 生态以 skill 形式分发。

## 特性

- 平台字幕优先，本地 ASR 兜底（faster-whisper，跨平台 CPU/CUDA）
- 摘要 / Markmap 导图 / 引用式问答（支持 Anthropic Messages 与 OpenAI 兼容两种协议）
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
# 默认走 Anthropic Messages 协议（https://www.yydsapi.uno + grok-4.6），只需设置 API Key
vsum config set ai.apiKey sk-xxx
```

> 默认配置：`ai.provider=anthropic_compatible`、`ai.baseUrl=https://www.yydsapi.uno`、`ai.model=grok-4.6`、`ai.transcriptionModel=large-v3-turbo`。也可切换为 OpenAI 兼容协议（DeepSeek、DashScope 等）：
>
> ```bash
> vsum config set ai.provider openai_compatible
> vsum config set ai.baseUrl https://api.deepseek.com
> vsum config set ai.model deepseek-v4-flash
> ```
>
> API Key 也可用环境变量 `ANTHROPIC_API_KEY`（Anthropic Messages）或 `DEEPSEEK_API_KEY`（OpenAI 兼容）提供。

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

服务仅监听本机 127.0.0.1，且 CORS 只放行 localhost 来源；任务超出 `storage.maxTasks`（默认 200）时自动清理最旧的非活动任务。

### Agent skill

```bash
vsum skill install     # 安装到 ~/.claude/skills/video-summary
vsum skill uninstall   # 移除
```

### 卸载

```bash
vsum uninstall             # 移除已安装的 skill，保留数据与模型
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
