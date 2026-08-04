import { create } from "zustand";
import { type AppHealthReport, type AppSettings } from "../../shared/types";
import { apiFetch } from "@/utils/api";

type SettingsState = {
  settings?: AppSettings;
  health?: AppHealthReport;
  loading: boolean;
  healthLoading: boolean;
  error?: string;
  healthError?: string;
  fetchSettings: () => Promise<void>;
  fetchHealth: () => Promise<void>;
  saveSettings: (partial: Partial<AppSettings>) => Promise<boolean>;
  testAi: () => Promise<{ ok: boolean; message?: string }>;
  getCookiesStatus: () => Promise<{ exists: boolean; path: string }>;
  uploadCookies: (content: string) => Promise<{ ok: boolean; path: string }>;
};

export const useSettingsStore = create<SettingsState>((set) => ({
  settings: undefined,
  health: undefined,
  loading: false,
  healthLoading: false,
  error: undefined,
  healthError: undefined,
  fetchSettings: async () => {
    set({ loading: true, error: undefined });
    try {
      const settings = await apiFetch<AppSettings>("/api/settings");
      set({ settings, loading: false });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "加载失败";
      set({ loading: false, error: msg });
    }
  },
  fetchHealth: async () => {
    set({ healthLoading: true, healthError: undefined });
    try {
      const health = await apiFetch<AppHealthReport>("/api/health");
      set({ health, healthLoading: false });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "健康检查加载失败";
      set({ healthLoading: false, healthError: msg });
    }
  },
  saveSettings: async (partial) => {
    set({ loading: true, error: undefined });
    try {
      const resp = await apiFetch<{ ok: true; settings: AppSettings }>("/api/settings", {
        method: "PUT",
        body: JSON.stringify(partial),
      });
      set({ settings: resp.settings, loading: false });
      return true;
    } catch (e) {
      const msg = e instanceof Error ? e.message : "保存失败";
      set({ loading: false, error: msg });
      return false;
    }
  },
  testAi: async () => {
    try {
      return await apiFetch<{ ok: boolean; message?: string }>("/api/settings/test-ai", { method: "POST" });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "AI 连接失败";
      return { ok: false, message: msg };
    }
  },
  getCookiesStatus: async () => {
    return apiFetch<{ exists: boolean; path: string }>("/api/settings/cookies/status");
  },
  uploadCookies: async (content: string) => {
    const resp = await apiFetch<{ ok: boolean; path: string; settings: AppSettings }>("/api/settings/cookies", {
      method: "POST",
      body: JSON.stringify({ content }),
    });
    set({ settings: resp.settings });
    return { ok: resp.ok, path: resp.path };
  },
}));
