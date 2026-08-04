export type VideoPlatform = "youtube" | "bilibili" | "unknown";
export type TaskStatus = "queued" | "running" | "succeeded" | "failed" | "canceled";
export type TaskExecutionStage = "parse" | "download" | "subtitles" | "summary" | "mindmap" | "qaIndex";

export type TaskStage =
  | "created"
  | "parsing"
  | "downloading"
  | "transcribing"
  | "summarizing"
  | "mindmap"
  | "indexing"
  | "ready"
  | "failed"
  | "canceled";

export type SubtitleFormat = "srt" | "vtt" | "txt" | "json";
export type AppHealthStatus = "ready" | "needs_attention";

export interface TaskArtifactsDTO {
  transcriptReady: boolean;
  summaryReady: boolean;
  mindmapReady: boolean;
  qaReady: boolean;
  subtitleFormats: SubtitleFormat[];
}

export interface CreateTaskRequest {
  url: string;
  pipeline: {
    parse: boolean;
    download: boolean;
    subtitles: boolean;
    summary: boolean;
    mindmap: boolean;
    qaIndex: boolean;
  };
  download?: {
    audioOnly?: boolean;
    quality?: "best" | "1080p" | "720p" | "480p";
  };
  language?: string;
}

export interface TaskDTO {
  id: string;
  url: string;
  platform: VideoPlatform;
  title?: string;
  durationSec?: number;
  stage: TaskStage;
  status?: TaskStatus;
  progress?: number;
  error?: string;
  currentStage?: TaskExecutionStage;
  lastCompletedStage?: TaskExecutionStage;
  failureStage?: TaskExecutionStage;
  failureCode?: string;
  retryable?: boolean;
  artifacts?: TaskArtifactsDTO;
  createdAt: string;
  updatedAt: string;
}

export interface AskRequest {
  question: string;
  mode?: "concise" | "detailed";
}

export interface AskResponse {
  answer: string;
  insufficientEvidence: boolean;
  citations: Array<{
    startMs: number;
    endMs: number;
    text: string;
  }>;
}

export interface QAMessageDTO {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  citations?: AskResponse["citations"];
  insufficientEvidence?: boolean;
}

export interface MindmapDTO {
  format: "markmap";
  content: string;
}

export interface AppSettings {
  ai: {
    provider: "openai_compatible";
    baseUrl?: string;
    apiKey?: string;
    model?: string;
    transcriptionModel?: string;
    asrEnabled?: boolean;
  };
  download: {
    ytdlpPath?: string;
    proxy?: string;
    cookiesPath?: string;
    outputDir?: string;
  };
  storage: {
    dataDir?: string;
    maxTasks?: number;
  };
}

export interface AppHealthCheck {
  ok: boolean;
  label: string;
  required: boolean;
  detail: string;
  path?: string;
  source?: string;
  missing?: string[];
}

export interface AppHealthReport {
  ok: boolean;
  status: AppHealthStatus;
  summary: string;
  checkedAt: string;
  checks: {
    dataDir: AppHealthCheck;
    aiConfig: AppHealthCheck;
    ytDlp: AppHealthCheck;
    markmap: AppHealthCheck;
    localWhisper: AppHealthCheck;
    whisperWeights: AppHealthCheck;
    cookies: AppHealthCheck;
  };
}
