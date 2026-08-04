import { create } from "zustand";
import { type CreateTaskRequest, type TaskDTO } from "../../shared/types";
import { apiFetch } from "@/utils/api";

type TasksState = {
  tasks: TaskDTO[];
  loading: boolean;
  error?: string;
  fetchTasks: () => Promise<void>;
  createTask: (req: CreateTaskRequest) => Promise<TaskDTO>;
  retryTask: (id: string) => Promise<TaskDTO>;
  cancelTask: (id: string) => Promise<void>;
  deleteTask: (id: string) => Promise<void>;
};

export const useTasksStore = create<TasksState>((set, get) => ({
  tasks: [],
  loading: false,
  error: undefined,
  fetchTasks: async () => {
    set({ loading: true, error: undefined });
    try {
      const tasks = await apiFetch<TaskDTO[]>("/api/tasks");
      set({ tasks, loading: false });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "加载失败";
      set({ loading: false, error: msg });
    }
  },
  createTask: async (req) => {
    const task = await apiFetch<TaskDTO>("/api/tasks", { method: "POST", body: JSON.stringify(req) });
    set({ tasks: [task, ...get().tasks] });
    return task;
  },
  retryTask: async (id) => {
    const resp = await apiFetch<{ task: TaskDTO }>(`/api/tasks/${id}/retry`, { method: "POST" });
    await get().fetchTasks();
    return resp.task;
  },
  cancelTask: async (id) => {
    await apiFetch<{ ok: true }>(`/api/tasks/${id}/cancel`, { method: "POST" });
    await get().fetchTasks();
  },
  deleteTask: async (id) => {
    await apiFetch<{ ok: true }>(`/api/tasks/${id}`, { method: "DELETE" });
    set({ tasks: get().tasks.filter((t) => t.id !== id) });
  },
}));
