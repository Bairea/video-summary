"""领域类型与默认配置。与旧 TS shared/types.ts 一一对应。"""

from typing import Literal, TypedDict

VideoPlatform = Literal["youtube", "bilibili", "unknown"]
TaskStatus = Literal["queued", "running", "succeeded", "failed", "canceled"]
TaskExecutionStage = Literal["parse", "download", "subtitles", "summary", "mindmap", "qaIndex"]
TaskStage = Literal[
    "created", "parsing", "downloading", "transcribing",
    "summarizing", "mindmap", "indexing", "ready", "failed", "canceled",
]
SubtitleFormat = Literal["srt", "vtt", "txt", "json"]
AppHealthStatus = Literal["ready", "needs_attention"]


class TranscriptSegment(TypedDict):
    startMs: int
    endMs: int
    text: str


class TaskArtifacts(TypedDict):
    transcriptReady: bool
    summaryReady: bool
    mindmapReady: bool
    qaReady: bool
    subtitleFormats: list[SubtitleFormat]


class CreateTaskRequest(TypedDict):
    url: str
    pipeline: dict
    download: dict
    language: str | None


class TaskDTO(TypedDict):
    id: str
    url: str
    platform: VideoPlatform
    title: str | None
    durationSec: int | None
    stage: TaskStage
    status: TaskStatus | None
    progress: int | None
    error: str | None
    currentStage: TaskExecutionStage | None
    lastCompletedStage: TaskExecutionStage | None
    failureStage: TaskExecutionStage | None
    failureCode: str | None
    retryable: bool | None
    artifacts: TaskArtifacts | None
    createdAt: str
    updatedAt: str


class AskResponse(TypedDict):
    answer: str
    insufficientEvidence: bool
    citations: list[TranscriptSegment]


class QAMessageDTO(TypedDict):
    id: str
    role: Literal["user", "assistant"]
    content: str
    createdAt: str
    citations: list[TranscriptSegment] | None
    insufficientEvidence: bool | None


def empty_artifacts() -> TaskArtifacts:
    return {
        "transcriptReady": False,
        "summaryReady": False,
        "mindmapReady": False,
        "qaReady": False,
        "subtitleFormats": [],
    }


def default_settings() -> dict:
    return {
        "ai": {
            "provider": "openai_compatible",
            "baseUrl": "https://api.deepseek.com",
            "model": "deepseek-v4-flash",
            "transcriptionModel": "large-v3-turbo",
            "asrEnabled": True,
        },
        "download": {},
        "storage": {
            "maxTasks": 200,
        },
    }
