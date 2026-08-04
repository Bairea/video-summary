import { Outlet } from "react-router-dom";
import Sidebar from "@/components/Sidebar";

export default function AppLayout() {
  return (
    <div className="h-screen w-screen overflow-hidden">
      <div className="flex h-full min-h-0">
        <Sidebar />
        <main className="relative flex min-h-0 flex-1 flex-col overflow-hidden">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_8%,rgba(60,246,255,0.07),transparent_35%),radial-gradient(circle_at_70%_18%,rgba(0,169,255,0.06),transparent_40%)]" />
          <div className="relative flex min-h-0 flex-1 overflow-hidden">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
