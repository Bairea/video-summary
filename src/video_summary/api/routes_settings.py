"""设置 API 路由。端点路径/状态码/响应体与旧 TS routes/settings.ts 一致。"""

import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..lib.cookies import cookie_header_to_netscape, is_probably_netscape_cookies
from ..paths import resolve_data_dir, set_task_output_dir
from ..repositories.settings_repo import load_settings, save_settings
from ..services.openai_compat import test_ai_connection
from ..services.ytdlp_service import resolve_cookies_path

router = APIRouter()


@router.get("")
@router.get("/")
async def get_settings():
    settings = await asyncio.to_thread(load_settings)
    effective_cookies_path = resolve_cookies_path(
        settings["download"].get("cookiesPath"),
        str(resolve_data_dir() / "cookies.txt"),
    )
    return {
        **settings,
        "download": {
            **settings["download"],
            "cookiesPath": effective_cookies_path,
        },
    }


@router.put("")
@router.put("/")
async def put_settings(request: Request):
    try:
        partial = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        partial = {}
    settings = await asyncio.to_thread(save_settings, partial)
    set_task_output_dir(settings["download"].get("outputDir"))
    return {"ok": True, "settings": settings}


@router.post("/test-ai")
async def test_ai():
    return await test_ai_connection()


@router.get("/cookies/status")
async def cookies_status():
    settings = await asyncio.to_thread(load_settings)
    p = (
        resolve_cookies_path(settings["download"].get("cookiesPath"), str(resolve_data_dir() / "cookies.txt"))
        or str(resolve_data_dir() / "cookies.txt")
    )
    from pathlib import Path
    exists = Path(p).is_file()
    return {"exists": exists, "path": p}


@router.post("/cookies")
async def save_cookies(request: Request):
    try:
        body = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        body = {}
    content = str(body.get("content") or "")
    if not content.strip():
        return JSONResponse(status_code=400, content={"ok": False, "message": "content required"})

    p = resolve_data_dir() / "cookies.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    body_content = content if is_probably_netscape_cookies(content) else cookie_header_to_netscape(content)
    p.write_text(body_content, "utf-8")
    settings = await asyncio.to_thread(save_settings, {"download": {"cookiesPath": str(p)}})
    return {"ok": True, "path": str(p), "settings": settings}
