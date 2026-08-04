import { NavLink } from "react-router-dom";
import { cn } from "@/lib/utils";
import { LayoutGrid, Settings, Sparkles } from "lucide-react";

const links = [
  { to: "/", label: "工作台", icon: LayoutGrid },
  { to: "/settings", label: "设置", icon: Settings },
];

export default function Sidebar() {
  return (
    <aside className="relative flex h-full w-[300px] flex-col border-r border-white/10 bg-ink-950/55">
      <div className="px-6 pb-5 pt-6">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-neon-400/40 to-white/5 ring-1 ring-neon-400/35">
            <Sparkles className="h-5 w-5 text-neon-400" />
          </div>
          <div>
            <div className="font-display text-lg font-semibold tracking-wide">视频总结器</div>
            <div className="text-xs text-white/55">YouTube / Bilibili</div>
          </div>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-1 px-3">
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            className={({ isActive }) =>
              cn(
                "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition",
                "hover:bg-white/5 hover:text-white",
                isActive ? "bg-white/6 text-white ring-1 ring-white/10" : "text-white/70",
              )
            }
            end={l.to === "/"}
          >
            <l.icon className="h-4 w-4 opacity-85 transition group-hover:opacity-100" />
            <span className="font-medium">{l.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="px-6 pb-6 pt-4 text-[11px] text-white/45">
        <div className="flex items-center justify-between">
          <span className="font-mono">Local-first</span>
          <span className="font-mono text-neon-400/90">v0</span>
        </div>
      </div>
    </aside>
  );
}

