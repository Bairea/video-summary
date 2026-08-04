import { useEffect, useMemo, useRef } from "react";
import { Transformer } from "markmap-lib";
import { Markmap } from "markmap-view";
import { cn } from "@/lib/utils";

const transformer = new Transformer();

export default function MarkmapView({
  markdown,
  className,
  onSvgChange,
}: {
  markdown: string;
  className?: string;
  onSvgChange?: (svg: string) => void;
}) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const id = useMemo(() => `markmap-${Math.random().toString(16).slice(2)}`, []);

  useEffect(() => {
    const svgElement = svgRef.current;
    if (!svgElement) return;

    svgElement.innerHTML = "";

    try {
      const { root } = transformer.transform(markdown);
      const instance = Markmap.create(svgElement, { autoFit: true, duration: 0, paddingX: 24 }, root);

      queueMicrotask(() => {
        onSvgChange?.(svgElement.outerHTML);
      });

      return () => {
        instance.destroy?.();
        svgElement.innerHTML = "";
        onSvgChange?.("");
      };
    } catch {
      onSvgChange?.("");
      svgElement.innerHTML = "";
      return;
    }
  }, [markdown, onSvgChange]);

  return (
    <div
      className={cn(
        "h-full w-full overflow-auto rounded-2xl border border-white/10 bg-ink-900/35 p-4",
        className,
      )}
    >
      <svg id={id} ref={svgRef} className="min-h-full min-w-[860px]" />
      {!markdown.trim() ? <div className="text-sm text-white/55">暂无导图（或导图尚未生成）</div> : null}
    </div>
  );
}
