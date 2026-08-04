"""任务 API 路由。端点路径/状态码/响应体与旧 TS routes/tasks.ts 一致。"""

import asyncio
import json

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, Response

from ..repositories import mindmap_repo, qa_repo, summary_repo, transcript_repo
from ..services.file_store import task_file
from ..services.qa_service import answer_question
from ..services.subtitle_service import export_subtitles
from ..services.task_service import task_service

router = APIRouter()

SUBTITLE_FORMATS = ["srt", "vtt", "txt", "json"]


async def _json_body(request: Request) -> dict:
    try:
        body = await request.json()
        return body if isinstance(body, dict) else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


@router.get("")
@router.get("/")
def list_tasks():
    return task_service.list()


@router.post("", status_code=201)
@router.post("/", status_code=201)
async def create_task(request: Request):
    body = await _json_body(request)
    if not body.get("url"):
        return JSONResponse(status_code=400, content={"error": "url required"})
    return task_service.create(body)


@router.get("/{task_id}")
def get_task(task_id: str):
    task = task_service.get(task_id)
    if not task:
        return JSONResponse(status_code=404, content={"error": "not found"})
    return task


@router.get("/{task_id}/subtitles")
async def get_subtitles(task_id: str, format: str = Query(default="srt")):
    if format not in SUBTITLE_FORMATS:
        return JSONResponse(status_code=400, content={"error": "invalid format"})
    try:
        file = await export_subtitles(task_id, format)
    except FileNotFoundError:
        return JSONResponse(status_code=404, content={"error": "not found"})
    return Response(
        content=file["body"],
        media_type=file["contentType"],
        headers={"Content-Disposition": f'attachment; filename="{file["fileName"]}"'},
    )


@router.put("/{task_id}/subtitles")
async def put_subtitles(task_id: str, request: Request):
    body = await _json_body(request)
    content = str(body.get("content") or "")
    if not content.strip():
        return JSONResponse(status_code=400, content={"error": "content required"})
    task_file(task_id, "subtitles.txt").parent.mkdir(parents=True, exist_ok=True)
    task_file(task_id, "subtitles.txt").write_text(content, "utf-8")
    segments = [{"startMs": 0, "endMs": 0, "text": content.strip()}]
    task_file(task_id, "subtitles.json").write_text(json.dumps(segments), "utf-8")
    await asyncio.to_thread(transcript_repo.replace_transcript, task_id, segments)
    return {"ok": True}


@router.get("/{task_id}/summary")
async def get_summary(task_id: str):
    markdown = await asyncio.to_thread(summary_repo.get_summary, task_id)
    if not markdown:
        return JSONResponse(status_code=404, content={"error": "not found"})
    return {"markdown": markdown}


@router.get("/{task_id}/mindmap")
async def get_mindmap(task_id: str):
    content = await asyncio.to_thread(mindmap_repo.get_mindmap, task_id)
    if not content:
        return JSONResponse(status_code=404, content={"error": "not found"})
    return {"format": "markmap", "content": content}


@router.post("/{task_id}/ask")
async def ask(task_id: str, request: Request):
    body = await _json_body(request)
    question = str(body.get("question") or "").strip()
    if not question:
        return JSONResponse(status_code=400, content={"error": "question required"})
    segments = await asyncio.to_thread(transcript_repo.get_transcript, task_id)
    if not segments:
        return JSONResponse(status_code=400, content={"error": "该任务暂无字幕内容"})

    await asyncio.to_thread(qa_repo.append_message, task_id, "user", question)
    out = await answer_question(question=question, segments=segments, mode=body.get("mode"))
    await asyncio.to_thread(qa_repo.append_message, task_id, "assistant", out["answer"], {
        "citations": out["citations"],
        "insufficientEvidence": out["insufficientEvidence"],
    })
    return out


@router.get("/{task_id}/qa/messages")
async def get_qa_messages(task_id: str):
    messages = await asyncio.to_thread(qa_repo.list_messages, task_id)
    return {"messages": messages}


@router.post("/{task_id}/cancel")
def cancel_task(task_id: str):
    task_service.cancel(task_id)
    return {"ok": True}


@router.post("/{task_id}/retry")
def retry_task(task_id: str):
    task = task_service.retry(task_id)
    return {"task": task}


@router.delete("/{task_id}")
def delete_task(task_id: str):
    task_service.remove(task_id)
    return {"ok": True}
