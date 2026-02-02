"""AgentTrace CLI (minimal scaffold)."""

from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List

from .reader import TraceReader

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
    out.pop("seq", None) # Sequence might differ if inserted differently
    out.pop("id", None) # DB ID
    return out

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

    ui_p = sub.add_parser("ui", help="Start the visualization UI")
    ui_p.add_argument("--port", type=int, default=8000, help="Port to run server on")
    ui_p.add_argument("--host", default="127.0.0.1", help="Host to bind to")

    args = parser.parse_args()

    reader = None
    if args.cmd in ["ls", "inspect", "search", "diff"]:
        try:
            reader = TraceReader()
        except Exception as e:
            pass

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
            
            # Simple seq-based diff
            len_a = len(events_a)
            len_b = len(events_b)
            max_len = max(len_a, len_b)
            
            print(f"Diffing {args.trace_a} vs {args.trace_b}")
            
            for i in range(max_len):
                ea = events_a[i] if i < len_a else None
                eb = events_b[i] if i < len_b else None
                
                seq_str = f"Seq {i+1}:"
                
                if not ea:
                    print(f"{seq_str} + {eb['kind']}")
                    continue
                if not eb:
                    print(f"{seq_str} - {ea['kind']}")
                    continue
                
                na = _normalize_event(ea)
                nb = _normalize_event(eb)
                
                if na == nb:
                    continue # Identical
                    
                print(f"{seq_str} {ea['kind']}")
                diffs = _diff_dict(na, nb)
                for d in diffs:
                    print(f"  {d}")
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
