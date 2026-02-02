"""AgentTrace CLI (minimal scaffold)."""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List

from .reader import TraceReader


def _format_event(evt: Dict[str, Any]) -> str:
    kind = evt.get("kind", "event")
    attrs = evt.get("attrs") or {}
    payload = evt.get("payload") or {}
    parts = [kind]
    if evt.get("span_id"):
        parts.append(f"span={evt['span_id']}")
    if kind == "llm_request":
        model = (attrs.get("model") if isinstance(attrs, dict) else None) or payload.get("model")
        if model:
            parts.append(f"model={model}")
    if kind == "tool_call":
        tool = (attrs.get("tool") if isinstance(attrs, dict) else None) or payload.get("tool")
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

def _normalize_event(evt: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(evt)
    out.pop("trace_id", None)
    out.pop("ts_unix_ns", None)
    out.pop("seq", None)  # Sequence might differ if inserted differently
    out.pop("id", None)  # DB ID
    return out


def _events_by_seq(events: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    mapped: Dict[int, Dict[str, Any]] = {}
    for idx, evt in enumerate(events):
        seq = evt.get("seq")
        if isinstance(seq, int):
            mapped[seq] = evt
        else:
            mapped[idx + 1] = evt
    return mapped

def main() -> None:
    parser = argparse.ArgumentParser(prog="agenttrace")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("ls", help="List traces")

    inspect_p = sub.add_parser("inspect", help="Print events for a trace")
    inspect_p.add_argument("trace_id")

    search_p = sub.add_parser("search", help="Search events for text")
    search_p.add_argument("query")

    diff_p = sub.add_parser("diff", help="Diff two traces")
    diff_p.add_argument("trace_a")
    diff_p.add_argument("trace_b")

    replay_p = sub.add_parser("replay", help="Replay a trace timeline")
    replay_p.add_argument("trace_id")
    replay_p.add_argument("--step", action="store_true", help="Step through events one at a time")
    replay_p.add_argument("--kind", action="append", help="Filter by event kind (can be repeated)")
    replay_p.add_argument("--span", help="Filter by span_id")

    export_p = sub.add_parser("export", help="Export trace as JSON")
    export_p.add_argument("trace_id")
    export_p.add_argument("--out", help="Write JSON to file instead of stdout")

    ui_p = sub.add_parser("ui", help="Start the visualization UI")
    ui_p.add_argument("--port", type=int, default=8000, help="Port to run server on")
    ui_p.add_argument("--host", default="127.0.0.1", help="Host to bind to")

    args = parser.parse_args()

    reader = None
    if args.cmd in ["ls", "inspect", "search", "diff", "replay", "export"]:
        try:
            reader = TraceReader()
        except Exception as e:
            import sys
            print(f"Error: could not initialize trace reader: {e}", file=sys.stderr)
            raise SystemExit(1)

    if args.cmd == "ls":
        if reader:
            for t in reader.list_traces():
                status = t.get('status', '')
                suffix = f"\t[{status}]" if status else ""
                print(f"{t['id']}\t{t['name']}\t({t['event_count']} events){suffix}")
        return

    if args.cmd == "inspect":
        if reader:
            trace = reader.get_trace(args.trace_id)
            if not trace:
                raise SystemExit(f"trace not found: {args.trace_id}")
            print(json.dumps(trace, indent=2))
        return

    if args.cmd == "search":
        if reader and hasattr(reader, "search"):
            results = reader.search(args.query)
            for r in results:
                print(f"{r['trace_id'][:8]}... | {r['kind']} | {r.get('trace_name', '')}")
                print(f"  {str(r.get('payload', ''))[:100]}...")
                print()
        else:
            print("Search is not available with the current storage backend.")
        return

    if args.cmd == "diff":
        if reader:
            t1 = reader.get_trace(args.trace_a)
            t2 = reader.get_trace(args.trace_b)
            if not t1: raise SystemExit(f"Trace not found: {args.trace_a}")
            if not t2: raise SystemExit(f"Trace not found: {args.trace_b}")

            events_a = t1["events"]
            events_b = t2["events"]
            map_a = _events_by_seq(events_a)
            map_b = _events_by_seq(events_b)
            all_seqs = sorted(set(map_a.keys()) | set(map_b.keys()))

            print(f"Diffing {args.trace_a} vs {args.trace_b}")
            for seq in all_seqs:
                ea = map_a.get(seq)
                eb = map_b.get(seq)

                seq_str = f"Seq {seq}:"
                if not ea:
                    print(f"{seq_str} + {eb['kind']}")
                    continue
                if not eb:
                    print(f"{seq_str} - {ea['kind']}")
                    continue

                na = _normalize_event(ea)
                nb = _normalize_event(eb)
                if na == nb:
                    continue

                print(f"{seq_str} {ea['kind']}")
                diffs = _diff_dict(na, nb)
                for d in diffs:
                    print(f"  {d}")
        return

    if args.cmd == "replay":
        if reader:
            trace = reader.get_trace(args.trace_id)
            if not trace:
                raise SystemExit(f"trace not found: {args.trace_id}")

            events = trace["events"]
            if args.kind:
                kinds = set(args.kind)
                events = [e for e in events if e.get("kind") in kinds]
            if args.span:
                events = [e for e in events if e.get("span_id") == args.span]
            start_ns = None
            for evt in events:
                ts = evt.get("ts_unix_ns")
                if start_ns is None and ts:
                    start_ns = ts
                delta_s = 0.0
                if start_ns and ts:
                    delta_s = (ts - start_ns) / 1_000_000_000
                print(f"[+{delta_s:0.2f}s] {_format_event(evt)}")
                if args.step:
                    try:
                        input("Press Enter to continue (Ctrl+C to stop)...")
                    except KeyboardInterrupt:
                        print("\nStopped.")
                        break
        return

    if args.cmd == "export":
        if reader:
            trace = reader.get_trace(args.trace_id)
            if not trace:
                raise SystemExit(f"trace not found: {args.trace_id}")
            output = json.dumps(trace, indent=2)
            if args.out:
                with open(args.out, "w", encoding="utf-8") as f:
                    f.write(output)
            else:
                print(output)
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

if __name__ == "__main__":
    main()
