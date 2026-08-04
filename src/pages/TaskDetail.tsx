import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Panel from "@/components/Panel";
import Button from "@/components/Button";
import StageBadge from "@/components/StageBadge";
import ProgressBar from "@/components/ProgressBar";
import MarkmapView from "@/components/MarkmapView";
import { apiFetch } from "@/utils/api";
import { type AskResponse, type MindmapDTO, type QAMessageDTO, type SubtitleFormat, type TaskDTO } from "../../shared/types";
import { ArrowLeft, Copy, Download, RefreshCcw, SendHorizontal } from "lucide-react";

type TabKey = "subtitles" | "summary" | "mindmap" | "qa";

function msToTime(ms: number): string {
  const sec = Math.max(0, Math.floor(ms / 1000));
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export default function TaskDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const taskId = id || "";

  const [task, setTask] = useState<TaskDTO | undefined>();
  const [tab, setTab] = useState<TabKey>("summary");
  const [subtitles, setSubtitles] = useState<string>("");
  const [summary, setSummary] = useState<string>("");
  const [mindmap, setMindmap] = useState<MindmapDTO | undefined>();
  const [mindmapSvg, setMindmapSvg] = useState("");
  const [question, setQuestion] = useState("");
  const [qaHistory, setQaHistory] = useState<QAMessageDTO[]>([]);
  const [busy, setBusy] = useState(false);

  const exportLinks = useMemo(() => {
    const fmts: SubtitleFormat[] = ["srt", "vtt", "txt", "json"];
    return fmts.map((f) => ({ f, href: `/api/tasks/${taskId}/subtitles?format=${f}` }));
  }, [taskId]);

  const loadTask = useCallback(async () => {
    const t = await apiFetch<TaskDTO>(`/api/tasks/${taskId}`);
    setTask(t);
  }, [taskId]);

  const loadSubtitles = useCallback(async () => {
    const resp = await fetch(`/api/tasks/${taskId}/subtitles?format=txt`);
    if (!resp.ok) {
      setSubtitles("");
      return;
    }
    setSubtitles(await resp.text());
  }, [taskId]);

  const loadSummary = useCallback(async () => {
    try {
      const resp = await apiFetch<{ markdown: string }>(`/api/tasks/${taskId}/summary`);
      setSummary(resp.markdown);
    } catch {
      setSummary("");
    }
  }, [taskId]);

  const loadMindmap = useCallback(async () => {
    try {
      const resp = await apiFetch<MindmapDTO>(`/api/tasks/${taskId}/mindmap`);
      setMindmap(resp);
    } catch {
      setMindmap(undefined);
      setMindmapSvg("");
    }
  }, [taskId]);

  const loadQaHistory = useCallback(async () => {
    try {
      const resp = await apiFetch<{ messages: QAMessageDTO[] }>(`/api/tasks/${taskId}/qa/messages`);
      setQaHistory(resp.messages);
    } catch {
      setQaHistory([]);
    }
  }, [taskId]);

  useEffect(() => {
    if (!taskId) return;
    loadTask();
    const t = setInterval(() => loadTask(), 1200);
    return () => clearInterval(t);
  }, [loadTask, taskId]);

  useEffect(() => {
    if (!taskId) return;
    if (tab === "subtitles") loadSubtitles();
    if (tab === "summary") loadSummary();
    if (tab === "mindmap") loadMindmap();
    if (tab === "qa") loadQaHistory();
  }, [loadMindmap, loadQaHistory, loadSubtitles, loadSummary, tab, taskId]);

  async function copyText(s: string) {
    await navigator.clipboard.writeText(s);
  }

  function downloadTextFile(fileName: string, content: string, contentType = "text/plain; charset=utf-8") {
    const blob = new Blob([content], { type: contentType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = fileName;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function ask() {
    if (!question.trim()) return;
    setBusy(true);
    try {
      await apiFetch<AskResponse>(`/api/tasks/${taskId}/ask`, {
        method: "POST",
        body: JSON.stringify({ question: question.trim(), mode: "detailed" }),
      });
      setQuestion("");
      await loadQaHistory();
    } finally {
      setBusy(false);
    }
  }

  if (!taskId) return null;

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto p-6 pb-10">
      <div className="flex flex-col gap-4 2xl:flex-row 2xl:items-start 2xl:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <Button size="sm" onClick={() => nav("/")} className="!rounded-xl">
              <ArrowLeft className="h-4 w-4" />
              返回
            </Button>
            <StageBadge stage={task?.stage ?? "created"} />
            <div className="text-[11px] text-white/45">
              <span className="font-mono">{task?.platform}</span>
              {task?.durationSec ? <span className="ml-2 font-mono">{Math.round(task.durationSec / 60)}min</span> : null}
            </div>
          </div>
          <div className="mt-3 truncate font-display text-2xl font-semibold tracking-wide">
            {task?.title || "任务详情"}
          </div>
          <div className="mt-2 max-w-5xl break-all text-sm leading-6 text-white/58">{task?.url}</div>
          <div className="mt-3 max-w-[740px]">
            <ProgressBar value={task?.progress ?? 0} />
          </div>
          {task?.error ? (
            <div className="mt-4 max-w-5xl rounded-2xl border border-red-300/15 bg-red-400/8 px-4 py-3">
              <div className="text-xs font-semibold uppercase tracking-wide text-red-100/90">错误详情</div>
              <pre className="mt-2 whitespace-pre-wrap break-words font-sans text-sm leading-7 text-red-50/92">{task.error}</pre>
            </div>
          ) : null}
        </div>

        <Panel className="flex w-full max-w-[360px] flex-col gap-3 p-4">
          <div className="text-sm font-semibold">导出</div>
          <div className="grid grid-cols-2 gap-2">
            {exportLinks.map((l) => (
              <a
                key={l.f}
                href={l.href}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-white/5 px-3 py-2 text-sm text-white/80 ring-1 ring-white/10 transition hover:bg-white/8"
              >
                <Download className="h-4 w-4" />
                {l.f.toUpperCase()}
              </a>
            ))}
          </div>
          <div className="text-[11px] text-white/45">字幕导出依赖任务已生成字幕文件。</div>
        </Panel>
      </div>

      <div className="grid grid-cols-1 items-start gap-6 xl:grid-cols-[300px_minmax(0,1fr)]">
        <Panel className="flex min-h-[220px] flex-col p-4">
          <div className="text-sm font-semibold">模块</div>
          <div className="mt-3 flex flex-col gap-2">
            {(
              [
                ["summary", "AI 摘要"],
                ["mindmap", "思维导图"],
                ["subtitles", "字幕"],
                ["qa", "AI 问答"],
              ] as const
            ).map(([k, label]) => (
              <button
                key={k}
                onClick={() => setTab(k)}
                className={`flex items-center justify-between rounded-2xl px-4 py-3 text-left text-sm transition ${
                  tab === k ? "bg-neon-500/10 text-white ring-1 ring-neon-500/20" : "bg-white/[0.02] text-white/75 hover:bg-white/[0.04]"
                }`}
              >
                <span className="font-medium">{label}</span>
                <span className="text-[11px] text-white/45">↵</span>
              </button>
            ))}
          </div>

          <div className="mt-4 rounded-2xl border border-white/10 bg-ink-900/35 p-4 text-xs text-white/55">
            <div className="font-mono text-neon-400/90">提示</div>
            <div className="mt-1">如果摘要/导图为空，通常是 AI 未配置或字幕不存在。</div>
          </div>
        </Panel>

        <Panel className="flex min-h-[520px] flex-col p-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="text-sm font-semibold">
              {tab === "subtitles" ? "字幕" : tab === "summary" ? "AI 摘要" : tab === "mindmap" ? "思维导图" : "AI 问答"}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                size="sm"
                onClick={() => {
                  if (tab === "subtitles") loadSubtitles();
                  if (tab === "summary") loadSummary();
                  if (tab === "mindmap") loadMindmap();
                }}
              >
                <RefreshCcw className="h-4 w-4" />
                刷新
              </Button>
              {tab === "summary" && summary ? (
                <Button size="sm" variant="primary" onClick={() => copyText(summary)}>
                  <Copy className="h-4 w-4" />
                  复制
                </Button>
              ) : null}
              {tab === "summary" && summary ? (
                <Button size="sm" onClick={() => downloadTextFile(`${taskId}-summary.md`, summary, "text/markdown; charset=utf-8")}>
                  <Download className="h-4 w-4" />
                  下载 MD
                </Button>
              ) : null}
              {tab === "subtitles" && subtitles ? (
                <Button size="sm" variant="primary" onClick={() => copyText(subtitles)}>
                  <Copy className="h-4 w-4" />
                  复制
                </Button>
              ) : null}
              {tab === "mindmap" && mindmap?.content ? (
                <Button size="sm" variant="primary" onClick={() => copyText(mindmap.content)}>
                  <Copy className="h-4 w-4" />
                  复制 MD
                </Button>
              ) : null}
              {tab === "mindmap" && mindmap?.content ? (
                <Button size="sm" onClick={() => downloadTextFile(`${taskId}-mindmap.md`, mindmap.content, "text/markdown; charset=utf-8")}>
                  <Download className="h-4 w-4" />
                  下载 MD
                </Button>
              ) : null}
              {tab === "mindmap" && mindmapSvg ? (
                <Button size="sm" onClick={() => downloadTextFile(`${taskId}-mindmap.svg`, mindmapSvg, "image/svg+xml; charset=utf-8")}>
                  <Download className="h-4 w-4" />
                  下载 SVG
                </Button>
              ) : null}
            </div>
          </div>

          <div className="mt-4 min-h-0 flex-1">
            {tab === "subtitles" ? (
              <div className="h-full overflow-auto rounded-2xl border border-white/10 bg-ink-900/35 p-4 font-mono text-sm leading-6 text-white/80">
                {subtitles ? subtitles : <div className="text-white/55">暂无字幕（或字幕尚未生成）</div>}
              </div>
            ) : null}

            {tab === "summary" ? (
              <div className="h-full overflow-auto rounded-2xl border border-white/10 bg-ink-900/35 p-4">
                {summary ? (
                  <pre className="whitespace-pre-wrap break-words font-sans text-sm leading-7 text-white/82">{summary}</pre>
                ) : (
                  <div className="text-sm text-white/55">暂无摘要（或摘要尚未生成）</div>
                )}
              </div>
            ) : null}

            {tab === "mindmap" ? (
              mindmap?.content ? (
                <MarkmapView markdown={mindmap.content} className="h-full" onSvgChange={setMindmapSvg} />
              ) : (
                <div className="h-full rounded-2xl border border-white/10 bg-ink-900/35 p-4 text-sm text-white/55">
                  暂无导图（或导图尚未生成）
                </div>
              )
            ) : null}

            {tab === "qa" ? (
              <div className="flex h-full flex-col gap-3 overflow-hidden">
                <div className="flex-1 overflow-auto rounded-2xl border border-white/10 bg-ink-900/35 p-4">
                  {qaHistory.length ? (
                    <div className="flex flex-col gap-3">
                      {qaHistory.map((item) => (
                        <div
                          key={item.id}
                          className={`rounded-2xl border p-3 ${
                            item.role === "assistant"
                              ? "border-neon-500/15 bg-neon-500/6"
                              : "border-white/10 bg-white/[0.03]"
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2 text-[11px] text-white/45">
                            <span>{item.role === "assistant" ? "AI 回答" : "我的问题"}</span>
                            <span>{new Date(item.createdAt).toLocaleTimeString()}</span>
                          </div>
                          <div className="mt-2 text-sm leading-6 text-white/85">{item.content}</div>
                          {item.role === "assistant" && item.insufficientEvidence ? (
                            <div className="mt-2 text-xs text-amber-200/85">证据不足：当前字幕片段不足以支持确定性回答。</div>
                          ) : null}
                          {item.citations?.length ? (
                            <div className="mt-3 flex flex-col gap-2">
                              {item.citations.map((c, idx) => (
                                <div
                                  key={`${item.id}-${idx}`}
                                  className="rounded-2xl border border-white/10 bg-black/15 p-3 text-xs text-white/70"
                                >
                                  <div className="font-mono text-[11px] text-neon-400/90">
                                    {msToTime(c.startMs)} - {msToTime(c.endMs)}
                                  </div>
                                  <div className="mt-1 leading-5">{c.text}</div>
                                </div>
                              ))}
                            </div>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-sm text-white/55">输入问题开始问答（需要字幕与 AI 配置）</div>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <input
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="例如：这个视频的核心观点是什么？"
                    className="flex-1 rounded-2xl border border-white/10 bg-ink-900/55 px-4 py-3 text-sm text-white/90 placeholder:text-white/30 outline-none focus:border-neon-500/30 focus:shadow-[0_0_0_4px_rgba(0,169,255,0.08)]"
                    onKeyDown={(e) => {
                      if (e.key === "Enter") ask();
                    }}
                  />
                  <Button variant="primary" disabled={busy || !question.trim()} onClick={ask}>
                    <SendHorizontal className="h-4 w-4" />
                    发送
                  </Button>
                </div>
              </div>
            ) : null}
          </div>
        </Panel>
      </div>
    </div>
  );
}
