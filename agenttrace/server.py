import json
import importlib.resources as resources
from pathlib import Path
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse

from .reader import TraceReader

app = FastAPI()
reader = TraceReader()

@app.get("/api/traces")
def list_traces():
    return reader.list_traces()

@app.get("/api/traces/{trace_id}")
def get_trace(trace_id: str):
    trace = reader.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace

@app.get("/")
def serve_ui():
    # Serve the single page app
    try:
        html_path = resources.files("agenttrace.web").joinpath("index.html")
    except Exception:
        html_path = Path(__file__).parent / "web" / "index.html"
    if not html_path.exists():
        return HTMLResponse(content="<h1>UI not found</h1><p>Ensure agenttrace/web/index.html exists.</p>", status_code=404)
    return FileResponse(html_path)

def start_server(host="127.0.0.1", port=8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)
