import { useEffect } from "react";
import { useTasksStore } from "@/stores/tasksStore";

export function useTaskPolling(opts?: { intervalMs?: number }) {
  const fetchTasks = useTasksStore((s) => s.fetchTasks);

  useEffect(() => {
    fetchTasks();
    const t = setInterval(() => fetchTasks(), opts?.intervalMs ?? 1500);
    return () => clearInterval(t);
  }, [fetchTasks, opts?.intervalMs]);
}

