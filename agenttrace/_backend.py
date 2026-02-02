"""Backend dispatcher: prefer native Rust extension, fall back to pure Python."""

try:
    from agenttrace_native import NativeTraceWriter, NativeTraceReader  # type: ignore[import-not-found]
    NATIVE_AVAILABLE = True
except ImportError:
    from ._native import NativeTraceWriter, NativeTraceReader  # type: ignore[assignment]
    NATIVE_AVAILABLE = False

__all__ = ["NativeTraceWriter", "NativeTraceReader", "NATIVE_AVAILABLE"]
