import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import Panel from "@/components/Panel";
import Button from "@/components/Button";
import ProgressBar from "@/components/ProgressBar";
import StageBadge from "@/components/StageBadge";
import { useTasksStore } from "@/stores/tasksStore";
import { useTaskPolling } from "@/hooks/useTaskPolling";
import { cn } from "@/lib/utils";
import { ArrowRight, Link2, RefreshCcw, Trash2, XCircle } from "lucide-react";
import { type CreateTaskRequest, type TaskDTO } from "../../shared/types";

const defaultPipeline: CreateTaskRequest["pipeline"] = {
  parse: true,
  download: false,
  subtitles: true,
  summary: true,
  mindmap: true,
  qaIndex: true,
};

const subtitlesSummaryPipeline: CreateTaskRequest["pipeline"] = {
  parse: true,
  download: false,
  subtitles: true,
  summary: true,
  mindmap: false,
  qaIndex: false,
};

const parseOnlyPipeline: CreateTaskRequest["pipeline"] = {
  parse: true,
  download: false,
  subtitles: false,
  summary: false,
  mindmap: false,
  qaIndex: false,
};

const DOWNLOAD_QUALITIES = ["best", "1080p", "720p", "480p"] as const;

function shortUrl(u: string): string {
  try {
    const url = new URL(u);
    return `${url.hostname}${url.pathname}`.slice(0, 64);
  } catch {
    return u.slice(0, 64);
  }
}

function isRunning(stage: TaskDTO["stage"]): boolean {
  return ["parsing", "downloading", "transcribing", "summarizing", "mindmap", "indexing"].includes(stage);
}

function isSupportedVideoUrl(value: string): boolean {
  try {
    const host = new URL(value).hostname.toLowerCase();
    return host.includes("youtube.com") || host === "youtu.be" || host.includes("bilibili.com") || host === "b23.tv";
  } catch {
    return false;
  }
}

export default function Home() {
  useTaskPolling();
  const nav = useNavigate();
  const { tasks, loading, error, createTask, retryTask, cancelTask, deleteTask } = useTasksStore();

  const [url, setUrl] = useState("");
  const [pipeline, setPipeline] = useState(defaultPipeline);
  const [audioOnly, setAudioOnly] = useState(false);
  const [quality, setQuality] = useState<(typeof DOWNLOAD_QUALITIES)[number]>("best");
  const [language, setLanguage] = useState("zh-Hans,en");
  const [creating, setCreating] = useState(false);

  const canStart = useMemo(() => isSupportedVideoUrl(url.trim()) && !creating, [url, creating]);

  async function onStart() {
    setCreating(true);
    try {
      const task = await createTask({
        url: url.trim(),
        pipeline,
        download: pipeline.download ? { audioOnly, quality } : undefined,
        language,
      });
      setUrl("");
      nav(`/task/${task.id}`);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="flex h-full flex-col gap-6 overflow-hidden p-6">
      <div className="flex items-end justify-between gap-6">
        <div>
          <div className="font-display text-2xl font-semibold tracking-wide">工作台</div>
          <div className="mt-1 text-sm text-white/55">输入链接 → 字幕 → 摘要 → 思维导图 → 问答</div>
        </div>
        <div className="hidden items-center gap-2 rounded-2xl border border-white/10 bg-white/[0.035] px-4 py-3 text-xs text-white/65 md:flex">
          <span className="font-mono text-neon-400/90">/api/tasks</span>
          <span className="text-white/35">·</span>
          <span>本地任务队列</span>
        </div>
      </div>

      <div className="grid flex-none grid-cols-1 gap-6 xl:grid-cols-2">
        <Panel className="p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="text-sm font-semibold">新建任务</div>
              <div className="mt-1 text-xs text-white/55">支持 YouTube / Bilibili。部分视频可能需要 cookies 才能获取字幕。</div>
            </div>
            <div className="rounded-xl bg-white/5 px-3 py-2 text-[11px] text-white/65 ring-1 ring-white/10">
              <span className="font-mono text-neon-400/90">Pipeline</span>
            </div>
          </div>

          <div className="mt-4">
            <div className="relative">
              <Link2 className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-white/40" />
              <input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="粘贴视频链接…"
                className="w-full rounded-2xl border border-white/10 bg-ink-900/50 px-10 py-3 text-sm text-white/90 placeholder:text-white/30 outline-none ring-0 transition focus:border-neon-500/30 focus:shadow-[0_0_0_4px_rgba(0,169,255,0.08)]"
              />
            </div>
            <div className="mt-2 text-xs text-white/45">
              {url.trim()
                ? isSupportedVideoUrl(url.trim())
                  ? "已识别为支持的平台链接。"
                  : "请输入有效的 YouTube / Bilibili 链接。"
                : "推荐先使用“推荐流程”，它会生成字幕、摘要、导图和问答准备。"}
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            {[
              { label: "推荐流程", value: defaultPipeline },
              { label: "字幕+摘要", value: subtitlesSummaryPipeline },
              { label: "仅解析", value: parseOnlyPipeline },
            ].map((preset) => (
              <Button
                key={preset.label}
                size="sm"
                onClick={() => setPipeline(preset.value)}
                className="!rounded-xl"
              >
                {preset.label}
              </Button>
            ))}
          </div>

          <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-3">
            {(
              [
                ["parse", "解析"],
                ["download", "下载"],
                ["subtitles", "字幕"],
                ["summary", "摘要"],
                ["mindmap", "导图"],
                ["qaIndex", "问答索引"],
              ] as const
            ).map(([k, label]) => (
              <label
                key={k}
                className={cn(
                  "flex cursor-pointer items-center justify-between rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm transition hover:bg-white/[0.045]",
                  pipeline[k] && "border-neon-500/25 bg-neon-500/8",
                )}
              >
                <span className="text-white/80">{label}</span>
                <input
                  type="checkbox"
                  checked={pipeline[k]}
                  onChange={(e) => setPipeline((p) => ({ ...p, [k]: e.target.checked }))}
                  className="h-4 w-4 accent-neon-400"
                />
              </label>
            ))}
          </div>

          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
            <label className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm">
              <div className="text-[11px] text-white/55">字幕语言</div>
              <input
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                disabled={!pipeline.subtitles}
                className="mt-1 w-full bg-transparent text-sm text-white/85 outline-none disabled:opacity-40"
              />
            </label>

            <label className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm">
              <div className="text-[11px] text-white/55">下载清晰度</div>
              <select
                value={quality}
                onChange={(e) => setQuality(e.target.value as (typeof DOWNLOAD_QUALITIES)[number])}
                disabled={!pipeline.download || audioOnly}
                className="mt-1 w-full bg-transparent text-sm text-white/85 outline-none disabled:opacity-40"
              >
                {DOWNLOAD_QUALITIES.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>

            <label className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm">
              <div>
                <div className="text-[11px] text-white/55">仅音频</div>
                <div className="text-sm text-white/80">audio-only</div>
              </div>
              <input
                type="checkbox"
                checked={audioOnly}
                onChange={(e) => setAudioOnly(e.target.checked)}
                disabled={!pipeline.download}
                className="h-4 w-4 accent-neon-400 disabled:opacity-40"
              />
            </label>
          </div>

          <div className="mt-4 flex items-center justify-between gap-3">
            <div className="text-xs text-white/45">
              <span className="font-mono text-neon-400/90">提示</span>：首次使用先去“设置”配置 AI。
            </div>
            <Button variant="primary" onClick={onStart} disabled={!canStart}>
              开始 <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </Panel>

        <Panel className="p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="text-sm font-semibold">任务队列</div>
              <div className="mt-1 text-xs text-white/55">
                {loading ? "加载中…" : `${tasks.length} 个任务`} {error ? `· ${error}` : ""}
              </div>
            </div>
            <div className="rounded-xl bg-white/5 px-3 py-2 text-[11px] text-white/65 ring-1 ring-white/10">
              <span className="font-mono">{new Date().toLocaleTimeString()}</span>
            </div>
          </div>

          <div className="mt-4 h-[420px] overflow-auto pr-1">
            <div className="flex flex-col gap-3">
              {tasks.map((t) => (
                <div
                  key={t.id}
                  className="group rounded-2xl border border-white/10 bg-ink-900/30 px-4 py-4 transition hover:border-white/14 hover:bg-ink-900/45"
                >
                  <div className="flex items-start justify-between gap-3">
                    <button className="min-w-0 flex-1 text-left" onClick={() => nav(`/task/${t.id}`)}>
                      <div className="truncate text-sm font-semibold text-white/90">{t.title || shortUrl(t.url)}</div>
                      <div className="mt-1 flex items-center gap-2 text-[11px] text-white/45">
                        <span className="font-mono">{t.platform}</span>
                        <span className="text-white/25">·</span>
                        <span className="truncate">{shortUrl(t.url)}</span>
                      </div>
                    </button>
                    <StageBadge stage={t.stage} />
                  </div>

                  <button className="mt-3 block w-full text-left" onClick={() => nav(`/task/${t.id}`)}>
                    <ProgressBar value={t.progress ?? 0} />
                  </button>

                  {t.error ? <div className="mt-2 text-xs text-red-200/80">{t.error}</div> : null}

                  <div className="mt-3 flex items-center justify-between gap-3">
                    <div className="text-[11px] text-white/45">
                      <span className="font-mono">{new Date(t.createdAt).toLocaleString()}</span>
                    </div>
                    <div className="flex items-center gap-2 opacity-0 transition group-hover:opacity-100">
                      {t.retryable ? (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={async () => {
                            await retryTask(t.id);
                          }}
                        >
                          <RefreshCcw className="h-4 w-4" />
                          重试
                        </Button>
                      ) : null}
                      {isRunning(t.stage) ? (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => {
                            cancelTask(t.id);
                          }}
                        >
                          <XCircle className="h-4 w-4" />
                          取消
                        </Button>
                      ) : null}
                      <Button
                        size="sm"
                        variant="danger"
                        onClick={() => {
                          deleteTask(t.id);
                        }}
                      >
                        <Trash2 className="h-4 w-4" />
                        删除
                      </Button>
                    </div>
                  </div>
                </div>
              ))}

              {tasks.length === 0 ? (
                <div className="grid place-items-center rounded-2xl border border-dashed border-white/10 bg-white/[0.02] px-4 py-14 text-center">
                  <div className="text-sm text-white/70">暂无任务</div>
                  <div className="mt-1 text-xs text-white/45">从左侧粘贴链接，或直接选“推荐流程”开始</div>
                </div>
              ) : null}
            </div>
          </div>
        </Panel>
      </div>

      <div className="flex-1 overflow-hidden">
        <Panel className="h-full p-5">
          <div className="flex items-center justify-between gap-4">
            <div className="text-sm font-semibold">使用说明</div>
            <div className="text-[11px] text-white/45">
              <span className="font-mono">yt-dlp</span> 负责解析与字幕；<span className="font-mono">LLM</span>{" "}
              负责摘要/导图/问答
            </div>
          </div>
          <div className="mt-3 grid gap-3 text-sm text-white/70 md:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
              <div className="font-semibold text-white/85">1) 配置 AI</div>
              <div className="mt-1 text-xs text-white/55">设置 Base URL / API Key / Model，支持 OpenAI 兼容接口。</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
              <div className="font-semibold text-white/85">2) 获取字幕</div>
              <div className="mt-1 text-xs text-white/55">优先拉取平台字幕；没有字幕的内容需要额外 ASR（后续可扩展）。</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
              <div className="font-semibold text-white/85">3) 生成结构化知识</div>
              <div className="mt-1 text-xs text-white/55">摘要/思维导图/问答均可导出与复制到笔记工具。</div>
            </div>
          </div>
        </Panel>
      </div>
    </div>
  );
}
