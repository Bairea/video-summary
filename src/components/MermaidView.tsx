import { useEffect, useMemo, useState } from "react";
import mermaid from "mermaid";
import { cn } from "@/lib/utils";

mermaid.initialize({
  startOnLoad: false,
  securityLevel: "strict",
  theme: "dark",
  themeVariables: {
    background: "transparent",
    primaryColor: "#0A1020",
    primaryBorderColor: "rgba(255,255,255,0.12)",
    primaryTextColor: "rgba(244,247,255,0.92)",
    lineColor: "rgba(60,246,255,0.35)",
    tertiaryColor: "#070A10",
  },
});

export default function MermaidView({ code, className }: { code: string; className?: string }) {
  const [svg, setSvg] = useState<string>("");
  const id = useMemo(() => `m_${Math.random().toString(16).slice(2)}`, []);

  useEffect(() => {
    let cancelled = false;
    setSvg("");
    mermaid
      .render(id, code)
      .then((r) => {
        if (!cancelled) setSvg(r.svg);
      })
      .catch(() => {
        if (!cancelled) setSvg("");
      });
    return () => {
      cancelled = true;
    };
  }, [code, id]);

  return (
    <div
      className={cn(
        "h-full w-full overflow-auto rounded-2xl border border-white/10 bg-ink-900/35 p-4",
        className,
      )}
    >
      {svg ? <div className="min-w-[860px]" dangerouslySetInnerHTML={{ __html: svg }} /> : <div className="text-sm text-white/55">无法渲染导图（请检查 Mermaid 语法）</div>}
    </div>
  );
}

