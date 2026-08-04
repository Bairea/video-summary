import { cn } from "@/lib/utils";
import type { HTMLAttributes } from "react";

export default function Panel({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-white/10 bg-white/[0.035] shadow-[0_0_0_1px_rgba(0,0,0,0.18),0_18px_60px_rgba(0,0,0,0.35)]",
        className,
      )}
      {...props}
    />
  );
}

