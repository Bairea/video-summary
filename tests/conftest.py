import asyncio

import pytest


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("VIDEO_SUMMARY_DATA_DIR", str(tmp_path / "data"))
    yield


@pytest.fixture(autouse=True)
def reset_job_queue():
    from video_summary.services.task_service import job_queue
    job_queue._queue.clear()
    job_queue._running = None
    job_queue._worker = None
    job_queue._notify = asyncio.Event()
    yield
