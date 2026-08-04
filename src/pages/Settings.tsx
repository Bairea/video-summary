import { useEffect, useMemo, useState } from "react";
import type { AppHealthCheck } from "../../shared/types";
import Panel from "@/components/Panel";
import Button from "@/components/Button";
import { useSettingsStore } from "@/stores/settingsStore";
import { AlertTriangle, CheckCircle2, FileUp, LoaderCircle, Save, ShieldCheck, TestTube2 } from "lucide-react";

function getHealthCardTone(item: AppHealthCheck) {
  if (item.ok) {
    return "border-emerald-400/20 bg-emerald-400/8";
  }
  return item.required ? "border-amber-400/25 bg-amber-400/10" : "border-white/10 bg-white/[0.03]";
}

export default function Settings() {
  const {
    settings,
    health,
    loading,
    healthLoading,
    error,
    healthError,
    fetchSettings,
    fetchHealth,
    saveSettings,
    testAi,
    getCookiesStatus,
    uploadCookies,
  } = useSettingsStore();
  const [tested, setTested] = useState<{ ok: boolean; message?: string } | undefined>();
  const [cookiesStatus, setCookiesStatus] = useState<{ exists: boolean; path: string } | undefined>();

  useEffect(() => {
    fetchSettings();
    fetchHealth();
  }, [fetchHealth, fetchSettings]);

  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("");
  const [transcriptionModel, setTranscriptionModel] = useState("");
  const [asrEnabled, setAsrEnabled] = useState(true);
  const [ytdlpPath, setYtdlpPath] = useState("");
  const [proxy, setProxy] = useState("");
  const [cookiesPath, setCookiesPath] = useState("");
  const [outputDir, setOutputDir] = useState("");
  const [cookiesContent, setCookiesContent] = useState("");

  useEffect(() => {
    if (!settings) return;
    setBaseUrl(settings.ai.baseUrl || "");
    setApiKey(settings.ai.apiKey || "");
    setModel(settings.ai.model || "");
    setTranscriptionModel(settings.ai.transcriptionModel || "");
    setAsrEnabled(settings.ai.asrEnabled ?? true);
    setYtdlpPath(settings.download.ytdlpPath || "");
    setProxy(settings.download.proxy || "");
    setCookiesPath(settings.download.cookiesPath || "");
    setOutputDir(settings.download.outputDir || "");
  }, [settings]);

  useEffect(() => {
    getCookiesStatus().then(setCookiesStatus).catch(() => setCookiesStatus(undefined));
  }, [getCookiesStatus]);

  const healthChecks = useMemo(() => {
    if (!health) return [];
    return Object.entries(health.checks) as Array<[string, AppHealthCheck]>;
  }, [health]);

  const dirty = useMemo(() => {
    if (!settings) return false;
    return (
      (settings.ai.baseUrl || "") !== baseUrl ||
      (settings.ai.apiKey || "") !== apiKey ||
      (settings.ai.model || "") !== model ||
      (settings.ai.transcriptionModel || "") !== transcriptionModel ||
      (settings.ai.asrEnabled ?? true) !== asrEnabled ||
      (settings.download.ytdlpPath || "") !== ytdlpPath ||
      (settings.download.proxy || "") !== proxy ||
      (settings.download.cookiesPath || "") !== cookiesPath ||
      (settings.download.outputDir || "") !== outputDir
    );
  }, [settings, baseUrl, apiKey, model, transcriptionModel, asrEnabled, ytdlpPath, proxy, cookiesPath, outputDir]);

  async function onSave() {
    setTested(undefined);
    const saved = await saveSettings({
      ai: {
        provider: "openai_compatible",
        baseUrl: baseUrl.trim(),
        apiKey: apiKey.trim(),
        model: model.trim(),
        transcriptionModel: transcriptionModel.trim(),
        asrEnabled,
      },
      download: {
        ytdlpPath: ytdlpPath.trim() || undefined,
        proxy: proxy.trim() || undefined,
        cookiesPath: cookiesPath.trim() || undefined,
        outputDir: outputDir.trim() || undefined,
      },
    });
    if (!saved) return;
    const result = await testAi();
    setTested(result);
    await Promise.all([
      fetchHealth(),
      getCookiesStatus().then(setCookiesStatus).catch(() => setCookiesStatus(undefined)),
    ]);
  }

  async function onTest() {
    const r = await testAi();
    setTested(r);
  }

  async function onUploadCookies() {
    if (!cookiesContent.trim()) return;
    const r = await uploadCookies(cookiesContent);
    setCookiesPath(r.path);
    await Promise.all([
      getCookiesStatus().then(setCookiesStatus).catch(() => setCookiesStatus(undefined)),
      fetchHealth(),
    ]);
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto p-6 pb-10">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <div className="font-display text-2xl font-semibold tracking-wide">设置</div>
          <div className="mt-1 max-w-2xl text-sm leading-6 text-white/62">
            配置 AI、下载工具与本地转写环境。敏感信息仅保存在本机 SQLite，不会写入仓库。
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button onClick={onTest} disabled={loading}>
            <TestTube2 className="h-4 w-4" />
            测试 AI
          </Button>
          <Button variant="primary" onClick={onSave} disabled={loading || !dirty}>
            <Save className="h-4 w-4" />
            保存
          </Button>
        </div>
      </div>

      <Panel className="p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="text-sm font-semibold">运行基线检查</div>
            <div className="mt-1 max-w-3xl text-xs leading-5 text-white/58">
              聚合检查 `yt-dlp`、AI 配置、Markmap、本地 Whisper、权重、数据目录与 cookies 状态。保存设置后会自动执行 AI 测试并刷新。
            </div>
          </div>
          <div
            className={`inline-flex items-center gap-2 rounded-xl px-3 py-2 text-[11px] ring-1 ${
              health?.ok
                ? "bg-emerald-400/8 text-emerald-100 ring-emerald-400/20"
                : "bg-amber-400/10 text-amber-100 ring-amber-400/20"
            }`}
          >
            {healthLoading ? <LoaderCircle className="h-4 w-4 animate-spin" /> : health?.ok ? <CheckCircle2 className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
            {healthLoading ? "检查中" : health?.ok ? "总体状态：就绪" : "总体状态：需处理"}
          </div>
        </div>

        {health ? (
          <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-white/80">
            <div>{health.summary}</div>
            <div className="mt-1 text-xs text-white/45">最近检查：{new Date(health.checkedAt).toLocaleString()}</div>
          </div>
        ) : null}

        <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-2">
          {healthChecks.map(([key, item]) => (
            <div key={key} className={`rounded-2xl border px-4 py-4 ${getHealthCardTone(item)}`}>
              <div className="flex items-center justify-between gap-3">
                <div className="text-sm font-medium text-white/90">{item.label}</div>
                <div className="rounded-lg bg-black/20 px-2 py-1 text-[10px] uppercase tracking-wide text-white/60">
                  {item.required ? "必需" : "可选"}
                </div>
              </div>
              <div className="mt-2 whitespace-pre-wrap break-words text-xs leading-6 text-white/68">{item.detail}</div>
            </div>
          ))}
        </div>

        {healthError ? <div className="mt-3 text-sm text-red-200/85">{healthError}</div> : null}
      </Panel>

      <div className="grid min-h-0 grid-cols-1 gap-6 xl:grid-cols-2">
        <Panel className="p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="text-sm font-semibold">AI（OpenAI 兼容）</div>
              <div className="mt-1 max-w-xl text-xs leading-5 text-white/58">用于摘要、导图与问答。支持自建网关或本地代理。</div>
            </div>
            <div className="inline-flex items-center gap-2 rounded-xl bg-white/5 px-3 py-2 text-[11px] text-white/65 ring-1 ring-white/10">
              <ShieldCheck className="h-4 w-4 text-neon-400/90" />
              不会上传到本项目仓库
            </div>
          </div>

          <div className="mt-4 grid gap-3">
            <label className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
              <div className="text-[11px] text-white/55">Base URL</div>
              <input
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="https://api.openai.com"
                className="mt-1 w-full bg-transparent text-sm text-white/85 outline-none"
              />
            </label>

            <label className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
              <div className="text-[11px] text-white/55">API Key</div>
              <input
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="sk-..."
                type="password"
                className="mt-1 w-full bg-transparent text-sm text-white/85 outline-none"
              />
            </label>

            <label className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
              <div className="text-[11px] text-white/55">Model</div>
              <input
                value={model}
                onChange={(e) => setModel(e.target.value)}
                placeholder="gpt-4o-mini"
                className="mt-1 w-full bg-transparent text-sm text-white/85 outline-none"
              />
            </label>

            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <label className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
                <div className="text-[11px] text-white/55">Whisper 模型</div>
                <input
                  value={transcriptionModel}
                  onChange={(e) => setTranscriptionModel(e.target.value)}
                  placeholder="whisper-1"
                  className="mt-1 w-full bg-transparent text-sm text-white/85 outline-none"
                />
              </label>

              <label className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
                <div>
                  <div className="text-[11px] text-white/55">无字幕自动 ASR</div>
                  <div className="text-sm text-white/80">Whisper fallback</div>
                </div>
                <input
                  type="checkbox"
                  checked={asrEnabled}
                  onChange={(e) => setAsrEnabled(e.target.checked)}
                  className="h-4 w-4 accent-neon-400"
                />
              </label>
            </div>

            {tested ? (
              <div
                className={`rounded-2xl border px-4 py-3 text-sm ${
                  tested.ok ? "border-emerald-400/20 bg-emerald-400/8 text-emerald-100" : "border-red-400/20 bg-red-400/8 text-red-100"
                }`}
              >
                {tested.ok ? "AI 连接成功" : tested.message || "AI 连接失败"}
              </div>
            ) : null}

            {error ? <div className="text-sm text-red-200/85">{error}</div> : null}
          </div>
        </Panel>

        <Panel className="p-5">
          <div className="text-sm font-semibold">下载与字幕</div>
          <div className="mt-1 max-w-xl text-xs leading-5 text-white/58">
            默认调用系统 <span className="font-mono text-white/80">yt-dlp</span>。B 站受限内容可通过 cookies.txt 获取权限。
          </div>

          <div className="mt-4 grid gap-3">
            <label className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
              <div className="text-[11px] text-white/55">yt-dlp 路径（可选）</div>
              <input
                value={ytdlpPath}
                onChange={(e) => setYtdlpPath(e.target.value)}
                placeholder="例如：/usr/local/bin/yt-dlp 或留空"
                className="mt-1 w-full bg-transparent text-sm text-white/85 outline-none"
              />
            </label>

            <label className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
              <div className="text-[11px] text-white/55">代理（可选）</div>
              <input
                value={proxy}
                onChange={(e) => setProxy(e.target.value)}
                placeholder="例如：socks5://127.0.0.1:7890"
                className="mt-1 w-full bg-transparent text-sm text-white/85 outline-none"
              />
            </label>

            <label className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
              <div className="text-[11px] text-white/55">cookies.txt 路径（可选）</div>
              <input
                value={cookiesPath}
                onChange={(e) => setCookiesPath(e.target.value)}
                placeholder="例如：/Users/me/cookies.txt"
                className="mt-1 w-full bg-transparent text-sm text-white/85 outline-none"
              />
            </label>

            <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-[11px] text-white/55">Cookies 管理（支持两种输入）</div>
                  <div className="mt-1 break-words text-xs leading-5 text-white/45">
                    {cookiesStatus
                      ? cookiesStatus.exists
                        ? `已检测到：${cookiesStatus.path}`
                        : `未检测到：${cookiesStatus.path}`
                      : "状态未知"}
                  </div>
                </div>
                <Button size="sm" onClick={onUploadCookies} disabled={!cookiesContent.trim() || loading}>
                  <FileUp className="h-4 w-4" />
                  写入
                </Button>
              </div>
              <textarea
                value={cookiesContent}
                onChange={(e) => setCookiesContent(e.target.value)}
                  placeholder={"可粘贴两种格式：\n1) cookies.txt（Netscape 格式）；\n2) 浏览器复制的 Cookie 字符串（a=b; c=d; ...）\n系统会自动转换后写入。"}
                className="mt-3 h-32 w-full resize-none rounded-xl border border-white/10 bg-ink-900/50 p-3 font-mono text-xs text-white/80 outline-none focus:border-neon-500/30"
              />
            </div>

            <label className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
              <div className="text-[11px] text-white/55">输出目录（可选）</div>
              <input
                value={outputDir}
                onChange={(e) => setOutputDir(e.target.value)}
                placeholder="默认：.data/tasks/<id>"
                className="mt-1 w-full bg-transparent text-sm text-white/85 outline-none"
              />
            </label>
          </div>
        </Panel>
      </div>
    </div>
  );
}
