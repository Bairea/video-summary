---
name: video-summary
description: 本地视频总结工具：给定 YouTube / Bilibili 视频链接，获取字幕并生成摘要、导图，可查任务。所有操作通过 vsum 命令完成。适合"帮我总结这个视频/这篇文章的要点"类请求。
---

# video-summary

本地优先的视频总结器。所有能力通过 `vsum` CLI 暴露，输出为 Markdown 或 JSON。

## 准备

- 安装：`uv tool install video-summary`
- 首次本地转写前下载 ASR 模型：`vsum models --download`（约 1-2 GB）
- AI 配置（Base URL / API Key / Model）：`vsum config set ai.baseUrl ...`、`vsum config set ai.apiKey ...`、`vsum config set ai.model ...`

## 命令速查

| 命令 | 说明 |
|---|---|
| `vsum summarize <url> [-l zh] [--json]` | 单向总结：字幕 → 摘要 → 导图，默认输出摘要 Markdown |
| `vsum serve [-p 3001] [--open]` | 启动 Web UI（浏览器访问 http://127.0.0.1:3001） |
| `vsum tasks [-n 20]` / `vsum task <id>` | 查看任务列表 / 单个任务 JSON |
| `vsum config` / `vsum config set <path> <value>` | 查看 / 设置 AI 配置 |
| `vsum models [--download]` | 模型状态 / 下载 |
| `vsum skill install\|uninstall` | 安装 / 移除本 skill |

## 典型用法（agent）

1. 用户给了一个视频链接：
   ```
   vsum summarize "https://www.youtube.com/watch?v=..." --json
   ```
2. 输出结构（`--json` 时）：
   ```json
   {
     "task": { "id": "...", "status": "succeeded", "platform": "youtube", "title": "...", "error": null, ... },
     "summary": "# 一句话摘要 ...",
     "mindmap": "# 视频要点 ..."
   }
   ```
3. 处理规则：
   - `task.status == "succeeded"` 时，`summary` 是可直接呈现的 Markdown 摘要，`mindmap` 是 Markmap 导图 Markdown
   - `task.status == "failed"` 时，`task.error` 含失败原因（如"需要 cookies.txt"、"AI 未配置"）；按原因提示用户而非重试
   - 默认（不带 `--json`）输出为纯摘要 Markdown，适合直接转发给用户
4. 需要按视频内容追问细节时，使用 Web UI 的问答功能（`vsum serve` 后引导用户操作），或提示用户补充问题。

## 注意

- 转写长视频耗时较长（faster-whisper 本地推理），不要重复运行
- Bilibili 部分视频需要 cookies：`vsum config set download.cookiesPath ~/.local/share/video-summary/cookies.txt`
