"""FastAPI 应用入口。路由挂载与响应形状对齐旧 TS app.ts。"""

import asyncio
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ..paths import resolve_static_dir, set_task_output_dir
from ..repositories.settings_repo import load_settings
from ..services.health_service import get_health_snapshot
from ..services.task_service import job_queue
from .routes_settings import router as settings_router
from .routes_tasks import router as tasks_router

logger = logging.getLogger(__name__)

load_dotenv()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = await asyncio.to_thread(load_settings)
    set_task_output_dir(settings["download"].get("outputDir"))
    job_queue.start(asyncio.get_running_loop())
    yield
    await job_queue.stop()


def create_app() -> FastAPI:
    app = FastAPI(title="video-summary", lifespan=lifespan, docs_url=None, redoc_url=None)

    # 仅监听 127.0.0.1（见 vsum serve）；CORS 只放行 localhost 来源，
    # 避免任意网页通过浏览器脚本调用本机无鉴权 API。curl/Agent 等非浏览器客户端不受影响。
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(tasks_router, prefix="/api/tasks")
    app.include_router(settings_router, prefix="/api/settings")

    @app.get("/api/health")
    async def health():
        return await get_health_snapshot()

    static_dir = resolve_static_dir()
    if static_dir is not None:
        assets_dir = static_dir / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa_fallback(path: str):
            if path.startswith("api/"):
                return JSONResponse(status_code=404, content={"success": False, "error": "API not found"})
            index_html = static_dir / "index.html"
            if not index_html.is_file():
                return JSONResponse(status_code=404, content={"success": False, "error": "frontend build missing"})
            return FileResponse(index_html)

    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
    def api_404(path: str):
        return JSONResponse(status_code=404, content={"success": False, "error": "API not found"})

    @app.exception_handler(Exception)
    async def error_handler(request: Request, exc: Exception):
        if isinstance(exc, asyncio.CancelledError):
            raise exc
        logger.exception("unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc) or "Server internal error"})

    return app


app = create_app()
