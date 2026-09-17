"""vsum 命令行入口：单向总结、Web 服务、任务、配置、模型、skill 与卸载。"""

import asyncio
import json
import shutil
import sys
import webbrowser
from pathlib import Path

import typer

from .paths import resolve_data_dir, resolve_models_dir, set_task_output_dir
from .repositories import mindmap_repo, summary_repo, task_repo
from .repositories.settings_repo import load_settings, save_settings
from .services.file_store import ensure_task_dir
from .services.task_service import detect_platform, task_service

app = typer.Typer(add_completion=False, no_args_is_help=True)

SETTABLE_PATHS = {
    "ai.provider", "ai.baseUrl", "ai.apiKey", "ai.model", "ai.transcriptionModel", "ai.asrEnabled",
    "download.proxy", "download.ytdlpPath", "download.cookiesPath", "download.outputDir",
}


@app.command()
def summarize(
    url: str,
    language: str | None = typer.Option(None, "--language", "-l", help="字幕/转写语言，如 zh / en"),
    json_output: bool = typer.Option(False, "--json", help="输出结构化 JSON（task + summary + mindmap）"),
):
    """单向总结：字幕 → 摘要 → 导图。默认输出摘要 Markdown。"""
    req = {
        "url": url,
        "language": language,
        "download": {},
        "pipeline": {
            "parse": True,
            "download": False,
            "subtitles": True,
            "summary": True,
            "mindmap": True,
            "qaIndex": True,
        },
    }

    def run():
        async def _run():
            settings = load_settings()
            set_task_output_dir(settings["download"].get("outputDir"))
            platform = detect_platform(url)
            task = task_repo.create_task(req, platform)
            ensure_task_dir(task["id"], settings["download"].get("outputDir"))
            await task_service.run_pipeline(task["id"], req, asyncio.Event())
            task_service.prune_old_tasks()
            return task_repo.get_task(task["id"])

        return asyncio.run(_run())

    task = run()
    if task is None:
        print("任务创建失败", file=sys.stderr)
        raise typer.Exit(1)
    summary = summary_repo.get_summary(task["id"])
    mindmap = mindmap_repo.get_mindmap(task["id"])

    if json_output:
        print(json.dumps({"task": task, "summary": summary, "mindmap": mindmap},
                         ensure_ascii=False, indent=2))
        return

    if task["status"] != "succeeded":
        print(f"总结失败：{task['error']}", file=sys.stderr)
        raise typer.Exit(1)
    if summary:
        print(summary)
    else:
        print(json.dumps(task, ensure_ascii=False, indent=2))


@app.command()
def serve(
    port: int = typer.Option(3001, "--port", "-p", help="监听端口"),
    open_browser: bool = typer.Option(False, "--open", "-o", help="启动后打开浏览器"),
):
    """启动 Web UI（内置前端，浏览器访问）。"""
    import uvicorn

    if open_browser:
        import threading
        threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    print(f"Video Summary Web UI: http://127.0.0.1:{port}")
    uvicorn.run("video_summary.api.app:app", host="127.0.0.1", port=port)


@app.command()
def tasks(limit: int = typer.Option(20, "--limit", "-n", help="最多显示条数")):
    """列出任务。"""
    rows = task_repo.list_tasks()[:limit]
    if not rows:
        print("暂无任务")
        return
    for t in rows:
        print(f"{t['id'][:8]}  {t['status']:<9} {t['platform']:<8} {t['url']}")


@app.command()
def task(task_id: str):
    """查看单个任务详情（JSON）。"""
    t = task_repo.get_task(task_id)
    if not t:
        print(f"任务不存在：{task_id}", file=sys.stderr)
        raise typer.Exit(1)
    print(json.dumps(t, ensure_ascii=False, indent=2))


@app.command()
def config(
    args: list[str] = typer.Argument(None, help="set <path> <value>，如 ai.baseUrl https://..."),
):
    """查看配置；config set <path> <value> 修改。"""
    if args:
        tokens = list(args)
        if tokens[0] == "set":
            tokens = tokens[1:]
        if len(tokens) != 2 or tokens[0] not in SETTABLE_PATHS:
            print(f"用法：vsum config set <path> <value>；可选路径：{', '.join(sorted(SETTABLE_PATHS))}", file=sys.stderr)
            raise typer.Exit(1)
        path, value = tokens
        section, key = path.split(".", 1)
        if section == "ai" and key == "asrEnabled":
            value = value.strip().lower() in ("1", "true", "yes", "是")
        settings = save_settings({section: {key: value}})
        print(f"已保存：{path} = {settings[section][key]}")
        return
    print(json.dumps(load_settings(), ensure_ascii=False, indent=2))


@app.command()
def models(
    download: bool = typer.Option(False, "--download", help="下载 ASR 模型（faster-whisper）"),
):
    """查看或下载 ASR 模型。"""
    models_dir = resolve_models_dir()
    if download:
        size = load_settings()["ai"].get("transcriptionModel") or "large-v3-turbo"
        print(f"正在下载模型 {size} 到 {models_dir} ...")
        from faster_whisper import WhisperModel
        WhisperModel(size, device="auto", compute_type="int8", download_root=str(models_dir))
        print("模型下载完成")
        return
    if models_dir.exists() and any(models_dir.iterdir()):
        total = sum(f.stat().st_size for f in models_dir.rglob("*") if f.is_file())
        print(f"模型目录：{models_dir}（{total / 1024 / 1024:.0f} MB）")
    else:
        print(f"未检测到模型：{models_dir}（运行 vsum models --download 下载）")


@app.command()
def skill(
    action: str = typer.Argument(..., help="install / uninstall"),
):
    """安装/卸载 Agent skill（复制到 ~/.claude/skills/video-summary）。"""
    source = Path(__file__).resolve().parent / "skills" / "video-summary"
    dest = Path.home() / ".claude" / "skills" / "video-summary"
    if action == "install":
        if not (source / "SKILL.md").is_file():
            print(f"包内 skill 缺失：{source}", file=sys.stderr)
            raise typer.Exit(1)
        shutil.rmtree(dest, ignore_errors=True)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, dest)
        print(f"skill 已安装：{dest}（升级包后重跑本命令刷新副本）")
    elif action == "uninstall":
        if dest.exists():
            shutil.rmtree(dest)
            print(f"skill 已移除：{dest}")
        else:
            print(f"skill 未安装：{dest}")
    else:
        print("用法：vsum skill install|uninstall", file=sys.stderr)
        raise typer.Exit(1)


@app.command()
def uninstall(
    purge_all: bool = typer.Option(False, "--purge-all", help="同时删除数据目录与模型缓存"),
):
    """卸载：默认移除 skill 与临时痕迹，保留数据/模型；--purge-all 全删。"""
    dest = Path.home() / ".claude" / "skills" / "video-summary"
    if dest.exists():
        shutil.rmtree(dest)
        print(f"已移除 skill：{dest}")

    if purge_all:
        data_dir = resolve_data_dir()
        if data_dir.exists():
            shutil.rmtree(data_dir)
            print(f"已删除数据目录：{data_dir}")
        else:
            print(f"数据目录不存在：{data_dir}")

    print("CLI 本体请用包管理器移除：uv tool uninstall vsum（或 pip uninstall vsum）")


if __name__ == "__main__":
    app()
