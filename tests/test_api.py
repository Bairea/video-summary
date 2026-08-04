"""API 端点测试（对应旧 taskService.test.ts 的 HTTP 层用例）。"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from video_summary.api.app import create_app

EMPTY_PIPELINE = {"parse": False, "download": False, "subtitles": False, "summary": False, "mindmap": False, "qaIndex": False}


@pytest.fixture()
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def make_request(url="https://www.youtube.com/watch?v=abc", pipeline=None):
    return {"url": url, "pipeline": pipeline or EMPTY_PIPELINE, "language": "zh"}


def test_health_shape(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert set(["dataDir", "aiConfig", "ytDlp", "markmap", "localWhisper", "whisperWeights", "cookies"]).issubset(body["checks"].keys())
    assert body["status"] in ("ready", "needs_attention")


def test_create_task_requires_url(client):
    resp = client.post("/api/tasks", json={})
    assert resp.status_code == 400
    assert resp.json() == {"error": "url required"}


def test_task_crud_flow(client):
    resp = client.post("/api/tasks", json=make_request())
    assert resp.status_code == 201
    task = resp.json()
    assert task["platform"] == "youtube"
    assert task["status"] == "queued"

    got = client.get(f"/api/tasks/{task['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == task["id"]

    # 空流水线任务会立即跑完
    import time
    deadline = time.time() + 5
    while time.time() < deadline:
        got = client.get(f"/api/tasks/{task['id']}")
        if got.json()["status"] == "succeeded":
            break
        time.sleep(0.05)
    assert got.json()["status"] == "succeeded"

    listed = client.get("/api/tasks")
    assert any(t["id"] == task["id"] for t in listed.json())

    deleted = client.delete(f"/api/tasks/{task['id']}")
    assert deleted.json() == {"ok": True}
    assert client.get(f"/api/tasks/{task['id']}").status_code == 404


def test_unknown_task_404(client):
    assert client.get("/api/tasks/nonexistent").status_code == 404


def test_unknown_api_404(client):
    resp = client.get("/api/nope")
    assert resp.status_code == 404
    assert resp.json()["success"] is False


def test_settings_roundtrip(client):
    resp = client.put("/api/settings", json={"ai": {"baseUrl": "https://dashscope.aliyuncs.com/compatible-mode", "apiKey": "k", "model": "qwen-plus"}})
    assert resp.json()["ok"] is True
    got = client.get("/api/settings").json()
    assert got["ai"]["baseUrl"] == "https://dashscope.aliyuncs.com/compatible-mode"
    assert got["ai"]["model"] == "qwen-plus"
    # 默认值保留
    assert got["ai"]["asrEnabled"] is True


def test_cookies_endpoints(client):
    resp = client.post("/api/settings/cookies", json={"content": "SESSDATA=abc; bili_jct=xyz"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    status = client.get("/api/settings/cookies/status").json()
    assert status["exists"] is True
    assert "cookies.txt" in status["path"]

    content = __import__("pathlib").Path(status["path"]).read_text("utf-8")
    assert content.startswith("# Netscape HTTP Cookie File")


def test_subtitles_put_and_export(client):
    task = client.post("/api/tasks", json=make_request()).json()
    tid = task["id"]
    resp = client.put(f"/api/tasks/{tid}/subtitles", json={"content": "第一段字幕。\n第二段字幕。"})
    assert resp.json() == {"ok": True}

    txt = client.get(f"/api/tasks/{tid}/subtitles?format=txt")
    assert txt.status_code == 200
    assert "第一段字幕" in txt.text
    assert "attachment" in txt.headers["content-disposition"]

    # srt 未被 PUT 生成 → 404
    assert client.get(f"/api/tasks/{tid}/subtitles?format=srt").status_code == 404
    assert client.get(f"/api/tasks/{tid}/subtitles?format=doc").status_code == 400


def test_cancel_running_task(client, monkeypatch):
    started = asyncio.Event()
    release = asyncio.Event()

    async def fake_dump_info(url, signal=None):
        started.set()
        await release.wait()

    monkeypatch.setattr("video_summary.services.task_service.dump_info", fake_dump_info)

    pipeline = {**EMPTY_PIPELINE, "parse": True}
    task = client.post("/api/tasks", json=make_request(pipeline=pipeline)).json()
    tid = task["id"]

    client.post(f"/api/tasks/{tid}/cancel")
    release.set()

    import time
    deadline = time.time() + 5
    while time.time() < deadline:
        got = client.get(f"/api/tasks/{tid}").json()
        if got["status"] == "canceled":
            break
        time.sleep(0.05)
    assert got["status"] == "canceled"


def test_retry_failed_task(client, monkeypatch):
    calls = {"n": 0}

    async def fake_dump_info(url, signal=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("模拟失败")
        return {"title": "测试视频", "duration": 120}

    monkeypatch.setattr("video_summary.services.task_service.dump_info", fake_dump_info)

    pipeline = {**EMPTY_PIPELINE, "parse": True}
    task = client.post("/api/tasks", json=make_request(pipeline=pipeline)).json()
    tid = task["id"]

    import time
    deadline = time.time() + 5
    while time.time() < deadline:
        got = client.get(f"/api/tasks/{tid}").json()
        if got["status"] == "failed":
            break
        time.sleep(0.05)
    assert got["status"] == "failed"
    assert got["failureStage"] == "parse"
    assert got["retryable"] is True

    retried = client.post(f"/api/tasks/{tid}/retry")
    assert retried.json()["task"]["status"] == "queued"

    deadline = time.time() + 5
    while time.time() < deadline:
        got = client.get(f"/api/tasks/{tid}").json()
        if got["status"] == "succeeded":
            break
        time.sleep(0.05)
    assert got["status"] == "succeeded"
    assert got["title"] == "测试视频"
    assert got["durationSec"] == 120


def test_qa_flow_with_mock_ai(client, monkeypatch):
    async def fake_chat_complete(messages, temperature=0.2, signal=None):
        return '{"answer": "机器学习基础", "insufficientEvidence": false, "citations": [{"startMs": 0, "endMs": 1000, "text": "今天讲的是机器学习"}]}'

    monkeypatch.setattr("video_summary.services.qa_service.chat_complete", fake_chat_complete)

    task = client.post("/api/tasks", json=make_request()).json()
    tid = task["id"]
    client.put(f"/api/tasks/{tid}/subtitles", json={"content": "今天讲的是机器学习基础"})

    resp = client.post(f"/api/tasks/{tid}/ask", json={"question": "讲了什么？"})
    assert resp.status_code == 200
    out = resp.json()
    assert out["answer"] == "机器学习基础"
    assert out["citations"][0]["startMs"] == 0

    messages = client.get(f"/api/tasks/{tid}/qa/messages").json()["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["citations"] == out["citations"]


def test_ask_requires_question_and_subtitles(client):
    task = client.post("/api/tasks", json=make_request()).json()
    tid = task["id"]
    assert client.post(f"/api/tasks/{tid}/ask", json={}).status_code == 400
    assert client.post(f"/api/tasks/{tid}/ask", json={"question": "hi"}).status_code == 400
