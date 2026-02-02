"""Backend dispatcher: prefer native Rust extension, fall back to pure Python."""

from __future__ import annotations

NATIVE_AVAILABLE = False

try:
    from agenttrace_native import NativeTraceWriter, NativeTraceReader  # type: ignore[import-not-found]
    NATIVE_AVAILABLE = True
except ImportError:
    from ._native import NativeTraceWriter, NativeTraceReader  # type: ignore[assignment]

__all__ = ["NativeTraceWriter", "NativeTraceReader", "NATIVE_AVAILABLE"]
