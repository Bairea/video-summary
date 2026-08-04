import { cn } from "@/lib/utils";

export default function ProgressBar({ value, className }: { value?: number; className?: string }) {
  const v = Math.max(0, Math.min(100, value ?? 0));
  return (
    <div className={cn("h-2 w-full rounded-full bg-white/7", className)}>
      <div
        className="h-2 rounded-full bg-gradient-to-r from-neon-400 to-neon-600 shadow-[0_0_24px_rgba(60,246,255,0.18)]"
        style={{ width: `${v}%` }}
      />
    </div>
  );
}

