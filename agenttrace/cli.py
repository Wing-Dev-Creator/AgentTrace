"""AgentTrace CLI (minimal scaffold)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .reader import TraceReader


def _read_events(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        yield json.loads(line)


def _trace_header(events_path: Path) -> Dict[str, Any]:
    info: Dict[str, Any] = {}
    for evt in _read_events(events_path):
        if evt.get("kind") == "trace_start":
            info["trace_name"] = (evt.get("payload") or {}).get("trace_name")
            info["project"] = (evt.get("payload") or {}).get("project")
            info["start_ns"] = evt.get("ts_unix_ns")
            break
    return info


def _format_time(ns: int | None) -> str:
    if not ns:
        return "unknown"
    return datetime.fromtimestamp(ns / 1_000_000_000).isoformat(timespec="seconds")


def _format_event(evt: Dict[str, Any]) -> str:
    kind = evt.get("kind", "event")
    attrs = evt.get("attrs") or {}
    if not isinstance(attrs, dict):
        attrs = {"value": attrs}
    payload = evt.get("payload") or {}
    if not isinstance(payload, dict):
        payload = {"value": payload}
    parts = [kind]
    if "span_id" in evt and evt["span_id"]:
        parts.append(f"span={evt['span_id']}")
    if kind == "llm_request":
        model = attrs.get("model") or payload.get("model")
        if model:
            parts.append(f"model={model}")
    if kind == "tool_call":
        tool = attrs.get("tool") or payload.get("tool")
        if tool:
            parts.append(f"tool={tool}")
    if kind == "user_input":
        text = payload.get("text")
        if text:
            parts.append(f"text={text}")
    if kind == "error":
        err = payload.get("error")
        if err:
            parts.append(f"error={err}")
    return " ".join(parts)


def _normalize_event(evt: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(evt)
    out.pop("trace_id", None)
    out.pop("ts_unix_ns", None)
    return out


def _format_value(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=True)
    except TypeError:
        return repr(value)


def _diff_dict(a: Dict[str, Any], b: Dict[str, Any], prefix: str = "") -> List[str]:
    diffs: List[str] = []
    keys = set(a.keys()) | set(b.keys())
    for key in sorted(keys):
        key_path = f"{prefix}.{key}" if prefix else key
        if key not in a:
            diffs.append(f"{key_path}: + {_format_value(b[key])}")
            continue
        if key not in b:
            diffs.append(f"{key_path}: - {_format_value(a[key])}")
            continue
        va = a[key]
        vb = b[key]
        if isinstance(va, dict) and isinstance(vb, dict):
            diffs.extend(_diff_dict(va, vb, key_path))
        elif va != vb:
            diffs.append(f"{key_path}: {_format_value(va)} -> {_format_value(vb)}")
    return diffs


def _load_events_by_seq(path: Path) -> Dict[int, Dict[str, Any]]:
    events: Dict[int, Dict[str, Any]] = {}
    for evt in _read_events(path):
        seq = evt.get("seq")
        if isinstance(seq, int):
            events[seq] = evt
    return events


def main() -> None:
    parser = argparse.ArgumentParser(prog="agenttrace")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("ls", help="List traces")

    inspect_p = sub.add_parser("inspect", help="Print events for a trace")
    inspect_p.add_argument("trace_id")

    replay_p = sub.add_parser("replay", help="Replay a trace timeline")
    replay_p.add_argument("trace_id")

    diff_p = sub.add_parser("diff", help="Diff two traces by event sequence")
    diff_p.add_argument("trace_a")
    diff_p.add_argument("trace_b")

    ui_p = sub.add_parser("ui", help="Start the visualization UI")
    ui_p.add_argument("--port", type=int, default=8000, help="Port to run server on")
    ui_p.add_argument("--host", default="127.0.0.1", help="Host to bind to")

    args = parser.parse_args()

    reader = TraceReader()
    root = reader.root

    if args.cmd == "ls":
        for t in reader.list_traces():
            print(f"{t['id']}\t{t['name']}\t({t['event_count']} events)")
        return

    if args.cmd == "inspect":
        trace = reader.get_trace(args.trace_id)
        if not trace:
            raise SystemExit(f"trace not found: {args.trace_id}")
        
        print(json.dumps(trace, indent=2))
        return

    if args.cmd == "ui":
        try:
            from .server import start_server
            print(f"Starting UI at http://{args.host}:{args.port}")
            start_server(host=args.host, port=args.port)
        except ImportError as e:
            print(f"Error: {e}")
            print("Please install UI dependencies: pip install agenttrace[ui] (or fastapi uvicorn)")
            return
        return

    if args.cmd == "replay":
        events_path = root / args.trace_id / "events.jsonl"
        if not events_path.exists():
            raise SystemExit(f"trace not found: {args.trace_id}")
        start_ns = None
        for evt in _read_events(events_path):
            ts = evt.get("ts_unix_ns")
            if start_ns is None and ts:
                start_ns = ts
            delta_s = 0.0
            if start_ns and ts:
                delta_s = (ts - start_ns) / 1_000_000_000
            print(f"[+{delta_s:0.2f}s] {_format_event(evt)}")
        return

    if args.cmd == "diff":
        path_a = root / args.trace_a / "events.jsonl"
        path_b = root / args.trace_b / "events.jsonl"
        if not path_a.exists():
            raise SystemExit(f"trace not found: {args.trace_a}")
        if not path_b.exists():
            raise SystemExit(f"trace not found: {args.trace_b}")

        events_a = _load_events_by_seq(path_a)
        events_b = _load_events_by_seq(path_b)
        all_seqs = sorted(set(events_a.keys()) | set(events_b.keys()))

        if not all_seqs:
            print("no events to diff")
            return

        for seq in all_seqs:
            evt_a = events_a.get(seq)
            evt_b = events_b.get(seq)
            if evt_a is None:
                kind = (evt_b or {}).get("kind", "event")
                print(f"seq {seq}: + {kind}")
                continue
            if evt_b is None:
                kind = (evt_a or {}).get("kind", "event")
                print(f"seq {seq}: - {kind}")
                continue

            norm_a = _normalize_event(evt_a)
            norm_b = _normalize_event(evt_b)
            if norm_a == norm_b:
                continue

            kind_a = evt_a.get("kind", "event")
            kind_b = evt_b.get("kind", "event")
            header = f"seq {seq}: {kind_a}"
            if kind_a != kind_b:
                header = f"seq {seq}: {kind_a} -> {kind_b}"
            print(header)
            diffs = _diff_dict(norm_a, norm_b)
            for diff in diffs:
                print(f"  {diff}")
        return


if __name__ == "__main__":
    main()
