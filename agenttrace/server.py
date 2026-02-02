"""FastAPI server for the AgentTrace visualization UI."""

from __future__ import annotations

import importlib.resources as resources
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse

from .reader import TraceReader

app = FastAPI()
_reader: Optional[TraceReader] = None


def _get_reader() -> TraceReader:
    global _reader
    if _reader is None:
        _reader = TraceReader()
    return _reader


@app.get("/api/traces")
def list_traces() -> List[Dict[str, Any]]:
    return _get_reader().list_traces()


@app.get("/api/traces/{trace_id}")
def get_trace(trace_id: str) -> Dict[str, Any]:
    trace = _get_reader().get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace


@app.get("/api/search")
def search_traces(q: str) -> List[Dict[str, Any]]:
    if not q:
        return []
    return _get_reader().search(q)


@app.get("/")
def serve_ui():
    try:
        html_path = resources.files("agenttrace.web").joinpath("index.html")
    except (AttributeError, ModuleNotFoundError, TypeError):
        html_path = Path(__file__).parent / "web" / "index.html"
    if not html_path.exists():
        return HTMLResponse(
            content="<h1>UI not found</h1><p>Ensure agenttrace/web/index.html exists.</p>",
            status_code=404,
        )
    return FileResponse(html_path)


def start_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    import uvicorn
    uvicorn.run(app, host=host, port=port)
