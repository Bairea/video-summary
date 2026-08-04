# 以 Python 包重构：FastAPI 后端 + 复用 React 前端，移除 Electron

原实现是 Electron 桌面应用（React + Express + SQLite）。Electron 常驻内存成本高（Chromium + Node 双进程），且无法被其他应用或 agent 通过命令行调用。决定重构为 Python 包：FastAPI 提供与原 Express 同名同形的 API 端点，现有 React 前端原样复用（仅改服务地址），通过浏览器访问；CLI 与 Web UI 共享同一流水线逻辑，CLI 同步编排（`vsum summarize`），Web 异步编排（任务队列）。

- **Status**: accepted
- **Considered Options**: 保留 Electron 仅做内存优化（无法满足"可被命令行调用"的定位）；前后端全部重写（现有前端已可用，重写无收益）
- **Consequences**: 数据目录迁移到 XDG 规范（`~/.local/share/video-summary/`），旧任务数据不迁移；旧仓库 `vedio_summary` 在新仓库建成后删除；Electron 相关代码（electron/、localWhisper、pythonRuntime）全部移除
