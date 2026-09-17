# Video Summary

本地优先的视频总结器。输入视频链接（YouTube / Bilibili），获取字幕（平台字幕或本地转写），生成摘要、Markmap 导图与带引用的问答。以 Python 包形式分发，提供 CLI（`vsum`）与 Web UI 两种使用方式，并面向 Agent 生态以 skill 形式分发。

## Language

**Task（任务）**:
一次视频总结工作单元，承载视频 URL、执行状态与各阶段产物。
_Avoid_: job

**Pipeline（流水线）**:
Task 内按序执行的阶段序列：parse → download → subtitles → summary → mindmap → qaIndex。阶段可独立失败；重试会跳过已完成阶段（续跑），只补做失败部分。
_Avoid_: workflow

**Parse（解析）**:
流水线第一阶段：解析视频 URL，获取标题与元数据。

**Download（下载）**:
按需下载音视频媒体，供本地转写与导出使用。

**Subtitles（字幕）**:
视频的逐句文本，是摘要、导图与问答的共同原料。来源有二：平台字幕与本地转写，产物统一为 SRT/VTT/TXT/JSON。
_Avoid_: captions

**Transcript（转写稿）**:
平台字幕与本地转写统一后的逐句文本产物（含时间戳），是摘要/导图/问答的实际输入。代码、数据与 UI 均以 transcript 命名（transcriptRepo、transcriptReady 等）。

**Platform subtitles（平台字幕）**:
通过 yt-dlp 从视频平台直接提取的字幕。Bilibili 部分视频需要 cookies。

**Transcription（本地转写）**:
通过 faster-whisper 将音频转为文本；在平台字幕不可用时作为字幕内容的来源。

**Summary（摘要）**:
AI 生成的视频内容摘要。

**Mindmap（导图）**:
以 Markmap 渲染的结构化视频要点图，源为 AI 生成的 markdown。

**QA（问答）**:
针对视频内容的提问与回答，回答附引用指向字幕原文。
_Avoid_: chat

**Citation（引用）**:
问答回答中指向字幕片段的证据标注，供用户回看原文位置。
