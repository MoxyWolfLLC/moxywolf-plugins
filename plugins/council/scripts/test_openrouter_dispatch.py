#!/usr/bin/env python3
"""ME-004: council's Anthropic calls ask OpenRouter for caching and record what it did.

Stdlib, offline: urlopen is replaced, so the payload checked is the one call_openrouter builds.
"""
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import openrouter_dispatch as od  # noqa: E402


def call(job, usage):
    sent = {}

    class Resp(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake(req, timeout=None):
        sent.update(json.loads(req.data))
        return Resp(json.dumps({"choices": [], "usage": usage}).encode())
    real, od.urllib.request.urlopen = od.urllib.request.urlopen, fake
    try:
        return sent, od.call_openrouter(job, "k", 5)
    finally:
        od.urllib.request.urlopen = real


MSG = [{"role": "user", "content": "q"}]
HIT = {"prompt_tokens": 2000, "prompt_tokens_details": {"cached_tokens": 1500, "cache_write_tokens": 0}}


def test_an_anthropic_job_asks_for_caching_and_records_the_numbers():
    sent, r = call({"id": "a", "model": "anthropic/claude-sonnet-5", "messages": MSG}, HIT)
    assert sent["cache_control"] == {"type": "ephemeral"}, sent
    assert r["ok"] and r["cache"] == {"read": 1500, "write": 0, "requested": True}, r["cache"]


def test_other_providers_and_an_opt_out_send_no_cache_control():
    for job in ({"id": "b", "model": "deepseek/deepseek-chat", "messages": MSG},
                {"id": "c", "model": "anthropic/claude-sonnet-5", "messages": MSG, "cache": False}):
        sent, r = call(job, HIT)
        assert "cache_control" not in sent, sent
        assert r["cache"]["requested"] is False and r["cache"]["read"] == 1500, "not requested is recorded, numbers kept as returned"
        assert "cache" not in sent, "the job's own flag never reaches OpenRouter"


def test_missing_fields_are_null_with_a_reason_never_zero():
    _, r = call({"id": "d", "model": "anthropic/claude-sonnet-5", "messages": MSG}, {"prompt_tokens": 10})
    assert r["cache"]["read"] is None and r["cache"]["write"] is None and r["cache"]["reason"], r["cache"]
    _, r = call({"id": "e", "model": "anthropic/claude-sonnet-5", "messages": MSG},
                {"prompt_tokens_details": {"cached_tokens": 7}})
    assert r["cache"]["read"] == 7 and r["cache"]["write"] is None and "lacked" in r["cache"]["reason"], r["cache"]


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn(); print(f"ok  {fn.__name__}")
    print(f"\n{len(tests)} passed")
