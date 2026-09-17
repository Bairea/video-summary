# ASR 引擎：Apple Silicon 用 mlx-whisper，其他平台用 whisper.cpp CLI

原实现用 faster-whisper，实测速度慢于 mlx-whisper 和 whisper.cpp。决定改为：Apple Silicon（M1/M2/M3/M4）使用 mlx-whisper（原生 Metal 加速），其他平台使用 whisper.cpp CLI（跨平台 C++ 实现）。

- **Status**: accepted
- **Considered Options**: faster-whisper（CTranslate2，速度慢）；mlx-whisper 仅 macOS；whisper.cpp 仅 CLI；双引擎 Python binding
- **Decision**: Apple Silicon 检测 (`sys.platform == "darwin" and platform.machine() == "arm64"`) → mlx-whisper；其他 → whisper.cpp CLI（用户自行安装到 PATH）
- **Model Mapping**: 配置 `transcriptionModel` 统一用 `large-v3` 等名称，内部映射到各引擎模型 ID（mlx: `mlx-community/whisper-large-v3-mlx`；whisper.cpp: `ggml-large-v3.bin`）
- **Download Fallback**: HuggingFace 失败时降级到 ModelScope
- **Consequences**: macOS 用户获得最佳性能；非 macOS 用户需安装 whisper.cpp CLI；模型缓存目录保持 `~/.local/share/video-summary/models/`

> **Update（2026-09）**: 默认 `ai.transcriptionModel=large-v3-turbo`（速度与体积优先），未命中引擎映射时各引擎回退到 `large-v3`，见 README 默认配置。下载与缓存目录决策不变。
