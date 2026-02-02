"""Tests for the config module."""

from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

from agenttrace.config import get_root_dir, get_store_full, get_max_field_len, get_redact_keys, _parse_bool


def test_parse_bool_true_values():
    for val in ("1", "true", "True", "TRUE", "yes", "on", " true "):
        assert _parse_bool(val) is True


def test_parse_bool_false_values():
    for val in ("0", "false", "no", "off", "random"):
        assert _parse_bool(val) is False


def test_parse_bool_none():
    assert _parse_bool(None) is False
    assert _parse_bool(None, default=True) is True


def test_get_root_dir_default():
    env_copy = dict(os.environ)
    env_copy.pop("AGENTTRACE_ROOT", None)
    with mock.patch.dict(os.environ, env_copy, clear=True):
        result = get_root_dir()
        assert result == Path.home() / ".agenttrace" / "traces"


def test_get_root_dir_custom():
    with mock.patch.dict(os.environ, {"AGENTTRACE_ROOT": "/tmp/custom"}):
        result = get_root_dir()
        assert result == Path("/tmp/custom")


def test_get_store_full_default():
    with mock.patch.dict(os.environ, {}, clear=True):
        os.environ.pop("AGENTTRACE_STORE_FULL", None)
        assert get_store_full() is False


def test_get_store_full_enabled():
    with mock.patch.dict(os.environ, {"AGENTTRACE_STORE_FULL": "true"}):
        assert get_store_full() is True


def test_get_max_field_len_default():
    with mock.patch.dict(os.environ, {}, clear=True):
        os.environ.pop("AGENTTRACE_MAX_FIELD_LEN", None)
        assert get_max_field_len() == 512


def test_get_max_field_len_custom():
    with mock.patch.dict(os.environ, {"AGENTTRACE_MAX_FIELD_LEN": "1024"}):
        assert get_max_field_len() == 1024


def test_get_max_field_len_minimum():
    with mock.patch.dict(os.environ, {"AGENTTRACE_MAX_FIELD_LEN": "10"}):
        assert get_max_field_len() == 64  # min clamp


def test_get_max_field_len_invalid():
    with mock.patch.dict(os.environ, {"AGENTTRACE_MAX_FIELD_LEN": "abc"}):
        assert get_max_field_len() == 512  # fallback


def test_get_redact_keys_default():
    with mock.patch.dict(os.environ, {}, clear=True):
        os.environ.pop("AGENTTRACE_REDACT", None)
        assert get_redact_keys() == set()


def test_get_redact_keys_custom():
    with mock.patch.dict(os.environ, {"AGENTTRACE_REDACT": "foo, BAR , baz"}):
        result = get_redact_keys()
        assert result == {"foo", "bar", "baz"}
