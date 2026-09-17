# ASR 引擎采用 faster-whisper，单一引擎不设 fallback

原实现用 mlx-whisper，仅支持 Apple Silicon，与"跨平台 Python 包"的定位冲突。决定采用 faster-whisper（CTranslate2，支持 CPU/CUDA/ROCm）作为唯一 ASR 引擎，不保留 mlx 分支。代价：开发机（M 芯片）上的转写速度低于 mlx，换来的是 Windows/Linux 与无 GPU 环境的可用性。

- **Status**: accepted
- **Considered Options**: mlx-whisper（macOS 专用、本机更快，但与包的分发定位矛盾）；双引擎（违反项目"不写 fallback 路径"规则）
- **Consequences**: 模型改为从 HuggingFace 下载（faster-whisper-large-v3），缓存目录置于数据目录内（`~/.local/share/video-summary/models/`），便于 `vsum uninstall --purge-all` 精确清理

> **Update（2026-09）**: 默认权重后续调整为 `large-v3-turbo`（速度与体积优先），可通过 `ai.transcriptionModel` 覆盖，见 README 默认配置。下载与缓存目录决策不变。
