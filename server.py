"""Local web UI for OpenJarvis.

Serves a single-page chat interface on http://127.0.0.1:8765 and streams
tokens from the local OpenJarvis engine over Server-Sent Events.

Run with:  <repo>\\src\\.venv\\Scripts\\python.exe server.py
"""

from __future__ import annotations

import json
import logging
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "index.html"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("jarvis.web")

SYSTEM_PREAMBLE = (
    "Eres Jarvis, un asistente personal de IA que se ejecuta localmente en el "
    "equipo del usuario. Responde en espanol, de forma clara, util y concisa. "
    "No digas que eres ChatGPT, Gemini ni Claude; identificate como Jarvis "
    "solo si te lo preguntan."
)

_state: dict[str, Any] = {"jarvis": None, "model": None, "engine": None, "error": None}
_init_lock = threading.Lock()
_chat_lock: Any = None


def _init_jarvis() -> Any:
    """Create the Jarvis SDK instance once (thread-safe)."""
    if _state["jarvis"] is not None:
        return _state["jarvis"]
    with _init_lock:
        if _state["jarvis"] is None:
            from openjarvis import Jarvis

            logger.info("Initializing OpenJarvis SDK...")
            jarvis = Jarvis()
            cfg = jarvis.config
            _state["engine"] = getattr(getattr(cfg, "engine", None), "default", None)
            _state["model"] = getattr(
                getattr(cfg, "intelligence", None), "default_model", None
            )
            try:
                models = jarvis.list_models()
                if not _state["model"] and models:
                    _state["model"] = models[0]
            except Exception as exc:  # engine may not be up yet
                logger.warning("Engine prewarm failed: %s", exc)
                _state["error"] = str(exc)
            _state["jarvis"] = jarvis
            logger.info(
                "OpenJarvis ready (engine=%s, model=%s)",
                _state["engine"],
                _state["model"],
            )
    return _state["jarvis"]


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _chat_lock
    import asyncio

    _chat_lock = asyncio.Lock()
    try:
        await run_in_threadpool(_init_jarvis)
    except Exception as exc:
        logger.exception("Could not initialize OpenJarvis")
        _state["error"] = str(exc)
    yield
    jarvis = _state.get("jarvis")
    if jarvis is not None:
        try:
            jarvis.close()
        except Exception:
            pass


app = FastAPI(title="Jarvis Local", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["null"],
    allow_origin_regex=r"^https://cheche2813\.github\.io$|^http://(127\.0\.0\.1|localhost)(:\d+)?$",
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


def _sse(payload: dict[str, Any]) -> str:
    return "data: " + json.dumps(payload, ensure_ascii=False) + "\n\n"


def _build_prompt(messages: list[ChatMessage]) -> str:
    """Turn the chat history into a single prompt for the local model."""
    history = [m for m in messages if m.content.strip()][-10:]
    if not history:
        return ""
    if len(history) == 1 and history[0].role == "user":
        return history[0].content.strip()

    lines = [SYSTEM_PREAMBLE, ""]
    for message in history:
        if message.role == "user":
            lines.append(f"Usuario: {message.content.strip()}")
        elif message.role == "assistant":
            lines.append(f"Jarvis: {message.content.strip()}")
    lines.append("Jarvis:")
    return "\n".join(lines)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(INDEX_FILE, media_type="text/html; charset=utf-8")


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "ready": _state["jarvis"] is not None,
        "engine": _state["engine"],
        "model": _state["model"],
        "error": _state["error"],
    }


@app.get("/favicon.ico")
async def favicon() -> Response:
    return Response(status_code=204)


@app.post("/api/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    prompt = _build_prompt(request.messages)
    if not prompt:
        return StreamingResponse(
            iter([_sse({"type": "error", "message": "Mensaje vacio."})]),
            media_type="text/event-stream",
        )

    async def event_stream():
        yield _sse({"type": "start"})
        try:
            jarvis = await run_in_threadpool(_init_jarvis)
        except Exception as exc:
            logger.exception("SDK init failed")
            yield _sse({"type": "error", "message": f"No se pudo iniciar Jarvis: {exc}"})
            return

        try:
            async with _chat_lock:
                async for chunk in jarvis.ask_full_stream(prompt):
                    if chunk.get("done"):
                        yield _sse(
                            {
                                "type": "done",
                                "content": chunk.get("content", ""),
                                "model": chunk.get("model"),
                                "engine": chunk.get("engine"),
                            }
                        )
                    else:
                        yield _sse(
                            {"type": "token", "token": chunk.get("token", "")}
                        )
        except Exception as exc:
            logger.exception("Generation failed")
            yield _sse({"type": "error", "message": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _open_browser_when_ready(url: str) -> None:
    import time
    import urllib.request
    import webbrowser

    for _ in range(120):
        try:
            with urllib.request.urlopen(url + "/health", timeout=1) as response:
                if response.status == 200:
                    break
        except Exception:
            time.sleep(0.5)
    webbrowser.open(url)


if __name__ == "__main__":
    import uvicorn

    host, port = "127.0.0.1", 8765
    url = f"http://{host}:{port}"
    threading.Thread(
        target=_open_browser_when_ready, args=(url,), daemon=True
    ).start()
    logger.info("Jarvis UI: %s", url)
    uvicorn.run(app, host=host, port=port, log_level="warning")
