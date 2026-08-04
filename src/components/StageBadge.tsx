import { cn } from "@/lib/utils";
import { type TaskStage } from "../../shared/types";

const map: Record<TaskStage, { label: string; cls: string }> = {
  created: { label: "已创建", cls: "bg-white/6 text-white/70 ring-white/10" },
  parsing: { label: "解析中", cls: "bg-neon-500/10 text-neon-400 ring-neon-500/20" },
  downloading: { label: "下载中", cls: "bg-neon-500/10 text-neon-400 ring-neon-500/20" },
  transcribing: { label: "字幕中", cls: "bg-neon-500/10 text-neon-400 ring-neon-500/20" },
  summarizing: { label: "摘要中", cls: "bg-neon-500/10 text-neon-400 ring-neon-500/20" },
  mindmap: { label: "导图中", cls: "bg-neon-500/10 text-neon-400 ring-neon-500/20" },
  indexing: { label: "索引中", cls: "bg-neon-500/10 text-neon-400 ring-neon-500/20" },
  ready: { label: "就绪", cls: "bg-emerald-400/10 text-emerald-200 ring-emerald-400/20" },
  failed: { label: "失败", cls: "bg-red-400/10 text-red-200 ring-red-400/20" },
  canceled: { label: "已取消", cls: "bg-white/6 text-white/55 ring-white/10" },
};

export default function StageBadge({ stage, className }: { stage: TaskStage; className?: string }) {
  const m = map[stage];
  return (
    <span className={cn("inline-flex items-center rounded-full px-2.5 py-1 text-[11px] ring-1", m.cls, className)}>
      {m.label}
    </span>
  );
}

