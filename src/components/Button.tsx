import { cn } from "@/lib/utils";
import type { ButtonHTMLAttributes } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "ghost" | "danger";
  size?: "sm" | "md";
};

export default function Button({ className, variant = "ghost", size = "md", ...props }: Props) {
  const base =
    "inline-flex items-center justify-center gap-2 rounded-xl font-medium transition disabled:cursor-not-allowed disabled:opacity-50";
  const sizes = size === "sm" ? "px-3 py-2 text-sm" : "px-4 py-2.5 text-sm";
  const styles =
    variant === "primary"
      ? "bg-neon-500/95 text-ink-950 hover:bg-neon-400 shadow-[0_0_0_1px_rgba(60,246,255,0.35),0_10px_35px_rgba(0,169,255,0.14)]"
      : variant === "danger"
        ? "bg-red-500/15 text-red-100 ring-1 ring-red-500/25 hover:bg-red-500/22"
        : "bg-white/5 text-white/85 ring-1 ring-white/10 hover:bg-white/8";

  return <button className={cn(base, sizes, styles, className)} {...props} />;
}

