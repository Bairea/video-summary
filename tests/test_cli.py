"""CLI 命令测试。"""

import json

from typer.testing import CliRunner

from video_summary.cli import app

runner = CliRunner()


def test_config_show_and_set(tmp_path, monkeypatch):
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert json.loads(result.output)["ai"]["model"] == "grok-4.6"

    result = runner.invoke(app, ["config", "set", "ai.model", "qwen-plus"])
    assert result.exit_code == 0

    result = runner.invoke(app, ["config"])
    assert json.loads(result.output)["ai"]["model"] == "qwen-plus"

    result = runner.invoke(app, ["config", "set", "ai.asrEnabled", "false"])
    assert result.exit_code == 0
    result = runner.invoke(app, ["config"])
    assert json.loads(result.output)["ai"]["asrEnabled"] is False


def test_config_set_invalid_path():
    result = runner.invoke(app, ["config", "set", "nope.key", "x"])
    assert result.exit_code == 1


def _make_fake_pipeline(task_repo):
    async def fake(task_id, req, signal):
        task_repo.update_task_stage(task_id, "ready", {
            "progress": 100, "error": None,
            "runtime": {
                "status": "succeeded", "currentStage": None, "lastCompletedStage": "qaIndex",
                "failureStage": None, "failureCode": None, "retryable": False,
                "artifacts": {"transcriptReady": True, "summaryReady": True, "mindmapReady": True,
                              "qaReady": True, "subtitleFormats": []},
            },
        })
    return fake


def test_summarize_markdown_output(monkeypatch):
    from video_summary.repositories import task_repo
    monkeypatch.setattr("video_summary.cli.task_service.run_pipeline", _make_fake_pipeline(task_repo))
    monkeypatch.setattr("video_summary.cli.summary_repo.get_summary", lambda tid: "# 一句话摘要\n\n- 要点A")
    monkeypatch.setattr("video_summary.cli.mindmap_repo.get_mindmap", lambda tid: "# 视频要点")

    result = runner.invoke(app, ["summarize", "https://www.youtube.com/watch?v=abc"])
    assert result.exit_code == 0
    assert "# 一句话摘要" in result.output


def test_summarize_json_output(monkeypatch):
    from video_summary.repositories import task_repo
    monkeypatch.setattr("video_summary.cli.task_service.run_pipeline", _make_fake_pipeline(task_repo))
    monkeypatch.setattr("video_summary.cli.summary_repo.get_summary", lambda tid: "# 摘要")

    result = runner.invoke(app, ["summarize", "https://www.bilibili.com/video/BV1xx", "--json"])
    assert result.exit_code == 0
    body = json.loads(result.output)
    assert body["task"]["status"] == "succeeded"
    assert body["summary"] == "# 摘要"


def test_tasks_empty():
    result = runner.invoke(app, ["tasks"])
    assert result.exit_code == 0
    assert "暂无任务" in result.output


def test_skill_install_uninstall(tmp_path, monkeypatch):
    # Windows 上 Path.home() 认 USERPROFILE，POSIX 认 HOME，两个都设
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    result = runner.invoke(app, ["skill", "install"])
    assert result.exit_code == 0
    skill_dir = tmp_path / ".claude" / "skills" / "video-summary"
    assert (skill_dir / "SKILL.md").is_file()

    # 幂等重装
    result = runner.invoke(app, ["skill", "install"])
    assert result.exit_code == 0

    result = runner.invoke(app, ["skill", "uninstall"])
    assert result.exit_code == 0
    assert not skill_dir.exists()


def test_uninstall_conservative(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    # 造数据目录
    data_dir = tmp_path / "data"
    (data_dir / "models").mkdir(parents=True)
    (data_dir / "models" / "model.bin").write_text("x")

    monkeypatch.setenv("VIDEO_SUMMARY_DATA_DIR", str(data_dir))
    runner.invoke(app, ["skill", "install"])

    result = runner.invoke(app, ["uninstall"])
    assert result.exit_code == 0
    # 保守模式：skill 删除，数据保留
    assert not (tmp_path / ".claude" / "skills" / "video-summary").exists()
    assert data_dir.exists()

    result = runner.invoke(app, ["uninstall", "--purge-all"])
    assert result.exit_code == 0
    assert not data_dir.exists()
