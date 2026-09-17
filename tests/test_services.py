"""服务层纯逻辑测试（对应旧 mindmapService.test.ts / qaService.test.ts）。"""

from video_summary.services.anthropic_compat import (
    normalize_anthropic_base_url,
    split_system_messages,
)
from video_summary.services.mindmap_service import normalize_markmap_markdown
from video_summary.services.openai_compat import resolve_ai_settings
from video_summary.services.qa_service import pick_context, safe_json_parse, tokenize
from video_summary.types import default_settings, empty_artifacts

SEGMENTS = [
    {"startMs": 0, "endMs": 1000, "text": "今天讲的是机器学习的基础概念"},
    {"startMs": 1000, "endMs": 2000, "text": "模型训练需要大量数据"},
    {"startMs": 2000, "endMs": 3000, "text": "推理阶段关注速度"},
]


def test_normalize_markmap_with_heading():
    out = normalize_markmap_markdown("# 主题\n\n## 章节\n- 要点")
    assert out == "# 主题\n\n## 章节\n- 要点"


def test_normalize_markmap_fenced():
    out = normalize_markmap_markdown("```markdown\n# 主题\n\n- a\n- b\n```")
    assert out == "# 主题\n\n- a\n- b"


def test_normalize_markmap_plain_lines():
    out = normalize_markmap_markdown("1. 第一点\n- 第二点\n第三点")
    assert out == "# 视频要点\n\n- 第一点\n- 第二点\n- 第三点"


def test_normalize_markmap_keeps_existing_heading_lines():
    # 与旧实现一致：任何以 # 开头的行存在时原样返回
    out = normalize_markmap_markdown("1. 第一点\n### 第三点")
    assert out == "1. 第一点\n### 第三点"


def test_normalize_markmap_empty():
    assert normalize_markmap_markdown("") == "# 视频要点\n\n- 暂无内容"


def test_tokenize():
    tokens = tokenize("机器学习 训练 数据？")
    assert "机器学习" in tokens
    assert "训练" in tokens
    assert len([t for t in tokens if len(t) < 2]) == 0


def test_pick_context_ranks():
    picked = pick_context("机器学习 数据", SEGMENTS)
    assert picked[0]["startMs"] == 0  # 匹配 2 个词
    assert len(picked) <= 10


def test_pick_context_empty_question_falls_back():
    picked = pick_context("???", SEGMENTS)
    assert picked == SEGMENTS[:10]


def test_safe_json_parse():
    assert safe_json_parse('{"answer": "ok"}')["answer"] == "ok"
    assert safe_json_parse('前缀{"answer": "ok"}后缀')["answer"] == "ok"
    assert safe_json_parse("不是 json") is None


def test_normalize_anthropic_base_url():
    assert normalize_anthropic_base_url("https://www.yydsapi.uno/") == "https://www.yydsapi.uno"
    assert normalize_anthropic_base_url("https://www.yydsapi.uno/v1") == "https://www.yydsapi.uno"
    assert normalize_anthropic_base_url("") == ""


def test_split_system_messages():
    system, msgs = split_system_messages([
        {"role": "system", "content": "你是助手"},
        {"role": "user", "content": "你好"},
    ])
    assert system == "你是助手"
    assert msgs == [{"role": "user", "content": "你好"}]


def test_split_system_messages_merges_consecutive_roles():
    system, msgs = split_system_messages([
        {"role": "system", "content": "a"},
        {"role": "system", "content": "b"},
        {"role": "assistant", "content": "hi"},
        {"role": "user", "content": "q"},
    ])
    assert system == "a\n\nb"
    # 首条必须为 user 角色
    assert msgs[0]["role"] == "user"
    assert [m["role"] for m in msgs] == ["user", "assistant", "user"]


def test_resolve_ai_settings_anthropic_default(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    resolved = resolve_ai_settings({"ai": {"provider": "anthropic_compatible", "apiKey": "sk-test"}})
    assert resolved["provider"] == "anthropic_compatible"
    assert resolved["baseUrl"] == "https://api.anthropic.com"  # 未填时回退官方地址
    assert resolved["model"] == "grok-4.6"
    assert resolved["apiKey"] == "sk-test"

    # 项目默认配置（yydsapi 网关）经 resolve 后保持不变
    resolved = resolve_ai_settings(default_settings())
    assert resolved["baseUrl"] == "https://www.yydsapi.uno"
    assert resolved["model"] == "grok-4.6"


def test_resolve_ai_settings_unknown_provider_falls_back(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    resolved = resolve_ai_settings({"ai": {"provider": "nope"}})
    assert resolved["provider"] == "openai_compatible"
    assert resolved["baseUrl"] == "https://api.deepseek.com"


def test_resolve_ai_settings_env_key_and_provider_switch(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-openai-env")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    resolved = resolve_ai_settings({"ai": {"provider": "openai_compatible"}})
    assert resolved["provider"] == "openai_compatible"
    assert resolved["baseUrl"] == "https://api.deepseek.com"
    assert resolved["apiKey"] == "sk-openai-env"
    assert resolved["model"] == "deepseek-v4-flash"

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-anthropic-env")
    resolved = resolve_ai_settings({"ai": {"provider": "anthropic_compatible", "apiKey": "sk-local"}})
    assert resolved["apiKey"] == "sk-anthropic-env"  # 环境变量优先
    assert resolved["baseUrl"] == "https://api.anthropic.com"
    assert resolved["model"] == "grok-4.6"


# ---- 流水线续跑与任务清理 ----

def _req():
    return {
        "url": "https://www.youtube.com/watch?v=abc",
        "language": None,
        "download": {},
        "pipeline": {"parse": True, "download": True, "subtitles": True,
                     "summary": True, "mindmap": True, "qaIndex": True},
    }


def test_reset_task_for_retry_preserves_artifacts():
    from video_summary.repositories import task_repo

    task = task_repo.create_task(_req(), "youtube")
    task_repo.update_task_stage(task["id"], "failed", {"runtime": {
        "status": "failed", "retryable": True,
        "artifacts": {**empty_artifacts(), "transcriptReady": True},
    }})
    task_repo.reset_task_for_retry(task["id"])

    refreshed = task_repo.get_task(task["id"])
    assert refreshed["status"] == "queued"
    assert refreshed["artifacts"]["transcriptReady"] is True


def test_run_pipeline_resumes_from_ready_artifacts(monkeypatch):
    import asyncio
    from video_summary.repositories import summary_repo, task_repo
    from video_summary.services import task_service as ts
    from video_summary.services.file_store import ensure_task_dir, task_file

    task = task_repo.create_task(_req(), "youtube")
    tid = task["id"]
    ensure_task_dir(tid)
    task_file(tid, "subtitles.json").write_text("[]", "utf-8")
    summary_repo.upsert_summary(tid, "# 已有摘要")
    task_repo.update_task_stage(tid, "failed", {"runtime": {
        "status": "failed", "retryable": True,
        "artifacts": {**empty_artifacts(), "transcriptReady": True, "summaryReady": True,
                      "subtitleFormats": ["srt", "vtt", "txt", "json"]},
    }})
    task_repo.reset_task_for_retry(tid)

    calls = []

    async def should_not_run(*args, **kwargs):
        calls.append("should_not_run")
        raise AssertionError("已完成阶段不应重跑")

    async def fake_dump(url, signal=None):
        calls.append("parse")
        return {"title": "T", "duration": 12}

    async def fake_mindmap(segments, signal=None):
        calls.append("mindmap")
        return "# 视频要点\n\n- 新要点"

    monkeypatch.setattr(ts, "dump_info", fake_dump)
    monkeypatch.setattr(ts, "download_media", should_not_run)
    monkeypatch.setattr(ts, "fetch_subtitles", should_not_run)
    monkeypatch.setattr(ts, "generate_summary", should_not_run)
    monkeypatch.setattr(ts, "generate_mindmap", fake_mindmap)

    asyncio.run(ts.task_service.run_pipeline(tid, _req(), asyncio.Event()))

    done = task_repo.get_task(tid)
    assert done["stage"] == "ready"
    assert calls == ["parse", "mindmap"]
    assert summary_repo.get_summary(tid) == "# 已有摘要"
    assert done["artifacts"]["mindmapReady"] is True
    assert done["artifacts"]["qaReady"] is True


def test_prune_old_tasks_removes_oldest_inactive(monkeypatch):
    from pathlib import Path

    from video_summary.paths import resolve_task_dir
    from video_summary.repositories import task_repo
    from video_summary.services import task_service as ts
    from video_summary.services.file_store import ensure_task_dir

    counter = {"n": 0}

    def fake_now():
        counter["n"] += 1
        return f"2026-09-17T00:00:{counter['n']:02d}.000Z"

    monkeypatch.setattr("video_summary.repositories.task_repo._now", fake_now)

    tasks = [task_repo.create_task(_req(), "youtube") for _ in range(4)]
    for t in tasks[:3]:  # 最旧的三个已完成，最新一个排队中
        task_repo.update_task_stage(t["id"], "ready", {"runtime": {"status": "succeeded", "retryable": False}})
        ensure_task_dir(t["id"])
    ensure_task_dir(tasks[3]["id"])

    ts.task_service.prune_old_tasks(max_tasks=2)

    ids = [t["id"] for t in tasks]
    assert task_repo.get_task(ids[0]) is None
    assert task_repo.get_task(ids[1]) is None
    assert task_repo.get_task(ids[2]) is not None
    assert task_repo.get_task(ids[3]) is not None  # 排队中的任务不被清理
    assert not Path(resolve_task_dir(ids[0])).exists()
    assert Path(resolve_task_dir(ids[2])).exists()
