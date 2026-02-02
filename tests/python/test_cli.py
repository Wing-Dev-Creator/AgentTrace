"""Tests for CLI commands."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from agenttrace._native import NativeTraceWriter


def _make_tmp() -> Path:
    return Path(tempfile.mkdtemp(prefix="agenttrace_cli_"))


def _write_trace(root: Path, trace_id: str, name: str):
    w = NativeTraceWriter(trace_id, str(root))
    w.emit(trace_id, 1, 100, "trace_start", None, None, "info", "{}",
           json.dumps({"trace_name": name, "project": "test"}))
    w.emit(trace_id, 2, 200, "user_input", "s1", None, "info", "{}",
           json.dumps({"text": "hello"}))
    w.emit(trace_id, 3, 300, "trace_end", None, None, "info", "{}",
           json.dumps({"status": "ok"}))
    w.finish()


def _run_cli(root: Path, *args: str) -> subprocess.CompletedProcess:
    env = {"AGENTTRACE_ROOT": str(root), "PATH": "", "SYSTEMROOT": "C:\\Windows"}
    return subprocess.run(
        [sys.executable, "-m", "agenttrace.cli"] + list(args),
        capture_output=True, text=True, env=env, timeout=10,
    )


def test_cli_ls():
    root = _make_tmp()
    _write_trace(root, "trace-1", "demo")

    result = _run_cli(root, "ls")
    assert result.returncode == 0
    assert "trace-1" in result.stdout
    assert "demo" in result.stdout


def test_cli_inspect():
    root = _make_tmp()
    _write_trace(root, "trace-2", "inspect-test")

    result = _run_cli(root, "inspect", "trace-2")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["id"] == "trace-2"
    assert len(data["events"]) == 3


def test_cli_inspect_not_found():
    root = _make_tmp()
    result = _run_cli(root, "inspect", "nonexistent")
    assert result.returncode != 0


def test_cli_export():
    root = _make_tmp()
    _write_trace(root, "trace-3", "export-test")

    result = _run_cli(root, "export", "trace-3")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["trace_name"] == "export-test"


def test_cli_export_to_file():
    root = _make_tmp()
    _write_trace(root, "trace-4", "file-export")
    out_file = root / "output.json"

    result = _run_cli(root, "export", "trace-4", "--out", str(out_file))
    assert result.returncode == 0
    assert out_file.exists()
    data = json.loads(out_file.read_text())
    assert data["trace_name"] == "file-export"


def test_cli_search():
    root = _make_tmp()
    _write_trace(root, "trace-5", "search-test")

    result = _run_cli(root, "search", "hello")
    assert result.returncode == 0
    assert "hello" in result.stdout or "user_input" in result.stdout
