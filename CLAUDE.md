# Video Summary (vsum)

本地优先的视频总结器。输入视频链接（YouTube / Bilibili），获取字幕，生成摘要、Markmap 导图与带引用的问答。

## 架构

```
src/video_summary/
├── api/              # FastAPI 路由
├── lib/              # 字幕解析、格式转换
├── repositories/     # SQLite 数据访问层
├── services/
│   ├── whisper_service.py   # ASR: mlx-whisper (Apple Silicon) / whisper.cpp CLI
│   ├── subtitle_service.py  # 平台字幕优先，本地 ASR 兜底
│   ├── ytdlp_service.py     # yt-dlp 封装
│   └── openai_compat.py     # OpenAI 兼容 API（摘要、问答）
├── cli.py            # vsum 命令入口
└── static/           # 前端构建产物
```

## Pipeline

Task 执行流水线：`parse → subtitles → summary → mindmap → qaIndex`

- **Parse**: 解析 URL，获取标题/元数据
- **Subtitles**: 平台字幕（yt-dlp）优先，无字幕时本地 ASR
- **Summary**: AI 生成摘要
- **Mindmap**: AI 生成 Markmap markdown
- **QA Index**: 构建问答索引

## ASR 引擎

| 平台 | 引擎 | 依赖 |
|------|------|------|
| Apple Silicon (M1/M2/M3/M4) | mlx-whisper | pip 依赖 |
| 其他 | whisper.cpp CLI | 用户自行安装到 PATH |

配置 `transcriptionModel` 统一用 `large-v3`，内部映射到各引擎模型 ID。

模型下载 fallback：HuggingFace → ModelScope。

## 数据目录

- SQLite + 任务产物：`~/.local/share/video-summary/`
- ASR 模型：`~/.local/share/video-summary/models/`
- 环境变量覆盖：`VIDEO_SUMMARY_DATA_DIR`

## 开发

```bash
uv sync            # Python 依赖
npm install        # 前端依赖
npm run build      # 构建前端到 src/video_summary/static/
uv run pytest      # 测试
uv run vsum serve  # 启动 Web UI
```

## 发布

```bash
uv build
uv publish
```
