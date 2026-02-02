"""Tests for the redaction module."""

from __future__ import annotations

from agenttrace.redaction import Redactor, RedactionConfig


def _make_redactor(store_full: bool = False, max_field_len: int = 512, extra_keys: set | None = None) -> Redactor:
    return Redactor(RedactionConfig(
        store_full=store_full,
        max_field_len=max_field_len,
        extra_keys=extra_keys or set(),
    ))


def test_redact_api_key_in_dict():
    r = _make_redactor()
    result = r.redact({"api_key": "sk-abc123", "message": "hello"})
    assert result["api_key"] == "<redacted>"
    assert result["message"] == "hello"


def test_redact_multiple_sensitive_keys():
    r = _make_redactor()
    data = {"password": "secret", "token": "tok-123", "name": "alice"}
    result = r.redact(data)
    assert result["password"] == "<redacted>"
    assert result["token"] == "<redacted>"
    assert result["name"] == "alice"


def test_redact_case_insensitive_key_matching():
    r = _make_redactor()
    result = r.redact({"Authorization": "Bearer xyz", "data": "ok"})
    assert result["Authorization"] == "<redacted>"


def test_redact_sk_pattern_in_string():
    r = _make_redactor()
    result = r.redact("My key is sk-1234567890abcdef and more text")
    assert "sk-" not in result
    assert "<redacted>" in result


def test_redact_nested_dict():
    r = _make_redactor()
    result = r.redact({"outer": {"api_key": "secret", "value": 42}})
    assert result["outer"]["api_key"] == "<redacted>"
    assert result["outer"]["value"] == 42


def test_redact_list():
    r = _make_redactor()
    result = r.redact([{"api_key": "x"}, {"msg": "hi"}])
    assert result[0]["api_key"] == "<redacted>"
    assert result[1]["msg"] == "hi"


def test_truncate_long_string():
    r = _make_redactor(max_field_len=20)
    result = r.redact("a" * 100)
    assert len(result) < 100
    assert result.endswith("...(truncated)")


def test_store_full_preserves_long_string():
    r = _make_redactor(store_full=True, max_field_len=20)
    long_str = "a" * 100
    result = r.redact(long_str)
    assert result == long_str


def test_bytes_redacted():
    r = _make_redactor()
    result = r.redact(b"binary data")
    assert result.startswith("<bytes:len=")


def test_bytes_store_full():
    r = _make_redactor(store_full=True)
    result = r.redact(b"binary data")
    # Should be base64 encoded
    assert isinstance(result, str)
    assert "<bytes" not in result


def test_extra_keys():
    r = _make_redactor(extra_keys={"custom_secret"})
    result = r.redact({"custom_secret": "value", "normal": "ok"})
    assert result["custom_secret"] == "<redacted>"
    assert result["normal"] == "ok"


def test_depth_limit():
    r = _make_redactor()
    deep = {"a": {"b": {"c": {"d": {"e": {"f": {"g": "value"}}}}}}}
    result = r.redact(deep)
    # At depth 7, should hit limit
    assert "<depth_limit>" in str(result)


def test_none_passthrough():
    r = _make_redactor()
    assert r.redact(None) is None


def test_primitives_passthrough():
    r = _make_redactor()
    assert r.redact(42) == 42
    assert r.redact(3.14) == 3.14
    assert r.redact(True) is True
