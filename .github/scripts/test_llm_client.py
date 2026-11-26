"""
test_llm_client.py — stdlib unittest suite for llm_client.py

Run with:
    python3 -m unittest .github/scripts/test_llm_client.py
"""

import io
import json
import os
import pathlib
import sys
import tempfile
import unittest
import unittest.mock
import urllib.error
import urllib.request

# Ensure the scripts directory is importable
_SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

import llm_client
from llm_client import (
    GeminiAdapter,
    LLMResponse,
    LLMRouter,
    OpenAICompatAdapter,
    OpenAIResponsesAdapter,
    RouteConfig,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_route(**kwargs) -> RouteConfig:
    defaults = dict(
        name="test-route",
        adapter="gemini",
        base_url="https://api.example.com/v1beta",
        model="test-model",
        api_key_env="TEST_API_KEY",
        timeout_sec=10.0,
        retries=1,
        backoff_sec=0.0,
        max_input_chars=None,
    )
    defaults.update(kwargs)
    return RouteConfig(**defaults)


def _gemini_response(text: str) -> dict:
    return {
        "candidates": [
            {"content": {"parts": [{"text": text}]}}
        ]
    }


def _openai_response(text: str) -> dict:
    return {
        "choices": [{"message": {"role": "assistant", "content": text}}]
    }


def _openai_responses_response(text: str) -> dict:
    return {
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": text}],
            }
        ]
    }


def _make_http_error(code: int, body: str = "error") -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        url="http://x",
        code=code,
        msg=str(code),
        hdrs={},  # type: ignore[arg-type]
        fp=io.BytesIO(body.encode()),
    )


def _mock_urlopen_ok(response_dict: dict):
    """Return a context-manager mock that yields a file-like JSON response."""
    raw = json.dumps(response_dict).encode()
    cm = unittest.mock.MagicMock()
    cm.__enter__ = lambda s: io.BytesIO(raw)
    cm.__exit__ = unittest.mock.MagicMock(return_value=False)
    return unittest.mock.patch(
        "urllib.request.urlopen",
        return_value=cm,
    )


class _FakeRouter(LLMRouter):
    """Router pre-loaded with an in-memory config — no filesystem needed."""

    def __init__(self, routes: list[RouteConfig], global_timeout: float = 60.0):
        super().__init__(config_path=pathlib.Path("/dev/null"))
        self._routes = routes
        self._global_timeout = global_timeout

    def _get_routes(self, profile: str):
        return self._routes, self._global_timeout


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestTier1Succeeds(unittest.TestCase):
    """TC-1: Tier 1 succeeds immediately; response metadata is correct."""

    def test_gemini_tier1_ok(self):
        route = _make_route(name="gemini-hydrogen", adapter="gemini")
        router = _FakeRouter([route])

        resp_body = _gemini_response("Hello, world!")

        with unittest.mock.patch.dict(os.environ, {"TEST_API_KEY": "fake-key"}):
            # Patch urlopen to return a successful Gemini response
            raw = json.dumps(resp_body).encode()
            mock_fp = io.BytesIO(raw)
            with unittest.mock.patch("urllib.request.urlopen") as mock_open:
                mock_open.return_value.__enter__ = lambda s: mock_fp
                mock_open.return_value.__exit__ = unittest.mock.MagicMock(return_value=False)

                result = router.generate(user_prompt="Say hi")

        self.assertIsInstance(result, LLMResponse)
        self.assertEqual(result.text, "Hello, world!")
        self.assertEqual(result.route_name, "gemini-hydrogen")
        self.assertEqual(result.adapter, "gemini")
        self.assertEqual(result.model, "test-model")
        self.assertEqual(result.tier_index, 0)
        self.assertEqual(result.attempts, 1)
        self.assertGreaterEqual(result.elapsed_sec, 0.0)


class TestFailoverOnTransient(unittest.TestCase):
    """TC-2: Tier 1 → HTTP 503 → retry once → fail → Tier 2 succeeds."""

    def test_503_failover_to_openai_compat(self):
        route1 = _make_route(
            name="gemini-primary",
            adapter="gemini",
            api_key_env="GEMINI_KEY",
            retries=1,
            backoff_sec=0.0,
        )
        route2 = _make_route(
            name="openai-secondary",
            adapter="openai_compat",
            api_key_env="OPENAI_KEY",
        )
        router = _FakeRouter([route1, route2])

        ok_body = json.dumps(_openai_response("Fallback answer")).encode()
        err_503 = _make_http_error(503)

        call_count = 0

        def fake_urlopen(req, timeout=None):
            nonlocal call_count
            call_count += 1
            # First two calls (Tier 1 attempt + retry) → 503
            if call_count <= 2:
                raise err_503
            # Third call (Tier 2) → success
            fp = io.BytesIO(ok_body)
            cm = unittest.mock.MagicMock()
            cm.__enter__ = lambda s: fp
            cm.__exit__ = unittest.mock.MagicMock(return_value=False)
            return cm

        env = {"GEMINI_KEY": "g-key", "OPENAI_KEY": "o-key"}
        with unittest.mock.patch.dict(os.environ, env):
            with unittest.mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
                result = router.generate(user_prompt="hello")

        self.assertEqual(result.text, "Fallback answer")
        self.assertEqual(result.route_name, "openai-secondary")
        self.assertEqual(result.adapter, "openai_compat")
        self.assertEqual(result.tier_index, 1)
        # Tier 2 succeeded on first attempt
        self.assertEqual(result.attempts, 1)
        # Total urlopen calls: 2 (tier1 original + tier1 retry) + 1 (tier2) = 3
        self.assertEqual(call_count, 3)


class TestMissingEnvSkip(unittest.TestCase):
    """TC-3: Route with missing API key env var is silently skipped."""

    def test_missing_env_skips_route(self):
        route1 = _make_route(
            name="no-key-route",
            adapter="gemini",
            api_key_env="NONEXISTENT_KEY_12345",
        )
        route2 = _make_route(
            name="has-key-route",
            adapter="gemini",
            api_key_env="REAL_KEY",
        )
        router = _FakeRouter([route1, route2])

        ok_body = json.dumps(_gemini_response("From route2")).encode()

        def fake_urlopen(req, timeout=None):
            fp = io.BytesIO(ok_body)
            cm = unittest.mock.MagicMock()
            cm.__enter__ = lambda s: fp
            cm.__exit__ = unittest.mock.MagicMock(return_value=False)
            return cm

        env = {"REAL_KEY": "r-key"}
        # Ensure NONEXISTENT_KEY_12345 is definitely absent
        env_patch = {k: v for k, v in os.environ.items()}
        env_patch.update(env)
        env_patch.pop("NONEXISTENT_KEY_12345", None)

        with unittest.mock.patch.dict(os.environ, env_patch, clear=True):
            with unittest.mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
                result = router.generate(user_prompt="hello")

        self.assertEqual(result.text, "From route2")
        self.assertEqual(result.route_name, "has-key-route")
        self.assertEqual(result.tier_index, 1)


class TestMaxInputCharsSkip(unittest.TestCase):
    """TC-4: Route with max_input_chars smaller than prompt is skipped (no HTTP call)."""

    def test_prompt_too_large_skips_route_without_http(self):
        route1 = _make_route(
            name="small-ctx-route",
            adapter="gemini",
            api_key_env="THE_KEY",
            max_input_chars=10,   # very small
        )
        route2 = _make_route(
            name="large-ctx-route",
            adapter="gemini",
            api_key_env="THE_KEY",
            max_input_chars=None,  # unlimited
        )
        router = _FakeRouter([route1, route2])

        ok_body = json.dumps(_gemini_response("Big prompt handled")).encode()
        http_call_count = 0

        def fake_urlopen(req, timeout=None):
            nonlocal http_call_count
            http_call_count += 1
            fp = io.BytesIO(ok_body)
            cm = unittest.mock.MagicMock()
            cm.__enter__ = lambda s: fp
            cm.__exit__ = unittest.mock.MagicMock(return_value=False)
            return cm

        long_prompt = "x" * 100  # 100 chars > 10 limit for route1

        with unittest.mock.patch.dict(os.environ, {"THE_KEY": "k"}):
            with unittest.mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
                result = router.generate(user_prompt=long_prompt)

        self.assertEqual(result.text, "Big prompt handled")
        self.assertEqual(result.route_name, "large-ctx-route")
        self.assertEqual(result.tier_index, 1)
        # HTTP should have been called only ONCE (for route2, not route1)
        self.assertEqual(http_call_count, 1)


class TestAllRoutesFail(unittest.TestCase):
    """TC-5: All routes failing exits non-zero with a clear summary."""

    def test_all_routes_fail_sys_exit(self):
        route1 = _make_route(
            name="bad-route-1",
            adapter="gemini",
            api_key_env="KEY1",
            retries=0,
        )
        route2 = _make_route(
            name="bad-route-2",
            adapter="openai_compat",
            api_key_env="KEY2",
            retries=0,
        )
        router = _FakeRouter([route1, route2])

        def fake_urlopen(req, timeout=None):
            raise _make_http_error(500, "Internal Server Error")

        env = {"KEY1": "k1", "KEY2": "k2"}
        with unittest.mock.patch.dict(os.environ, env):
            with unittest.mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
                with self.assertRaises(SystemExit) as ctx:
                    router.generate(user_prompt="hello")

        # Must exit non-zero
        self.assertNotEqual(ctx.exception.code, 0)

        # Exit message must mention each route
        exit_msg = str(ctx.exception.code)
        self.assertIn("bad-route-1", exit_msg)
        self.assertIn("bad-route-2", exit_msg)

        # Must mention the failure reason (HTTP 500)
        self.assertIn("500", exit_msg)


class TestAdapterExtraction(unittest.TestCase):
    """Unit-test each adapter's response-parsing in isolation."""

    def _run_adapter(self, adapter, route, response_body: dict) -> str:
        raw = json.dumps(response_body).encode()
        fp = io.BytesIO(raw)
        cm = unittest.mock.MagicMock()
        cm.__enter__ = lambda s: fp
        cm.__exit__ = unittest.mock.MagicMock(return_value=False)
        with unittest.mock.patch("urllib.request.urlopen", return_value=cm):
            return adapter.invoke(route, "fake-key", "", "prompt", 10.0)

    def test_gemini_adapter(self):
        route = _make_route(adapter="gemini")
        result = self._run_adapter(
            GeminiAdapter(), route, _gemini_response("Gemini says hi")
        )
        self.assertEqual(result, "Gemini says hi")

    def test_openai_compat_adapter(self):
        route = _make_route(adapter="openai_compat")
        result = self._run_adapter(
            OpenAICompatAdapter(), route, _openai_response("OAI says hi")
        )
        self.assertEqual(result, "OAI says hi")

    def test_openai_responses_adapter(self):
        route = _make_route(adapter="openai_responses")
        result = self._run_adapter(
            OpenAIResponsesAdapter(), route, _openai_responses_response("Responses says hi")
        )
        self.assertEqual(result, "Responses says hi")

    def test_gemini_adapter_with_system_prompt(self):
        """Verify systemInstruction is included when system_prompt is non-empty."""
        route = _make_route(adapter="gemini")
        raw = json.dumps(_gemini_response("ok")).encode()
        fp = io.BytesIO(raw)
        cm = unittest.mock.MagicMock()
        cm.__enter__ = lambda s: fp
        cm.__exit__ = unittest.mock.MagicMock(return_value=False)
        captured_body = {}

        def fake_urlopen(req, timeout=None):
            captured_body["data"] = json.loads(req.data.decode())
            return cm

        with unittest.mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            GeminiAdapter().invoke(route, "key", "Be concise.", "prompt", 10.0)

        self.assertIn("systemInstruction", captured_body["data"])
        self.assertEqual(
            captured_body["data"]["systemInstruction"]["parts"][0]["text"],
            "Be concise.",
        )


class TestNonTransientFatalError(unittest.TestCase):
    """HTTP 401 / 403 / 404 should fail over immediately (no retry)."""

    def test_401_fails_over_immediately(self):
        route1 = _make_route(
            name="auth-fail-route",
            adapter="gemini",
            api_key_env="KEY1",
            retries=5,   # would retry if transient
        )
        route2 = _make_route(
            name="backup-route",
            adapter="gemini",
            api_key_env="KEY2",
        )
        router = _FakeRouter([route1, route2])
        call_count = 0
        ok_body = json.dumps(_gemini_response("from backup")).encode()

        def fake_urlopen(req, timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise _make_http_error(401, "Unauthorized")
            fp = io.BytesIO(ok_body)
            cm = unittest.mock.MagicMock()
            cm.__enter__ = lambda s: fp
            cm.__exit__ = unittest.mock.MagicMock(return_value=False)
            return cm

        with unittest.mock.patch.dict(os.environ, {"KEY1": "k1", "KEY2": "k2"}):
            with unittest.mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
                result = router.generate(user_prompt="hi")

        # Should fail over after EXACTLY 1 call (no retries for 401)
        self.assertEqual(call_count, 2)
        self.assertEqual(result.route_name, "backup-route")


class TestModelOverrideRouting(unittest.TestCase):
    """TC-6: --model-override uses a single-route bypass, inheriting adapter/base_url from profile."""

    def test_model_override_uses_matched_route_adapter(self):
        route1 = _make_route(
            name="gemini-hydrogen",
            adapter="gemini",
            base_url="https://api.gemini.example.com/v1beta",
            model="gemini-4-hydrogen",
            api_key_env="GEMINI_KEY",
        )
        route2 = _make_route(
            name="openai-fallback",
            adapter="openai_responses",
            base_url="https://api.openai.example.com/v1",
            model="gpt-6-luna",
            api_key_env="OPENAI_KEY",
        )
        router = _FakeRouter([route1, route2])

        ok_body = json.dumps(_gemini_response("override response")).encode()

        def fake_urlopen(req, timeout=None):
            fp = io.BytesIO(ok_body)
            cm = unittest.mock.MagicMock()
            cm.__enter__ = lambda s: fp
            cm.__exit__ = unittest.mock.MagicMock(return_value=False)
            return cm

        with unittest.mock.patch.dict(os.environ, {"GEMINI_KEY": "g-key"}):
            with unittest.mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
                result = router.generate(
                    user_prompt="hello",
                    model_override="gemini-4-hydrogen",
                )

        # Must use the matched route's adapter and base_url
        self.assertEqual(result.text, "override response")
        self.assertEqual(result.adapter, "gemini")
        self.assertEqual(result.model, "gemini-4-hydrogen")
        # tier_index is 0 because override collapses to a single-route waterfall
        self.assertEqual(result.tier_index, 0)

    def test_model_override_with_explicit_adapter_override(self):
        """Explicit --adapter-override takes precedence over profile match."""
        route1 = _make_route(
            name="gemini-hydrogen",
            adapter="gemini",
            base_url="https://api.gemini.example.com/v1beta",
            model="gemini-4-hydrogen",
            api_key_env="GEMINI_KEY",
        )
        router = _FakeRouter([route1])

        ok_body = json.dumps(_openai_response("compat override")).encode()

        def fake_urlopen(req, timeout=None):
            fp = io.BytesIO(ok_body)
            cm = unittest.mock.MagicMock()
            cm.__enter__ = lambda s: fp
            cm.__exit__ = unittest.mock.MagicMock(return_value=False)
            return cm

        with unittest.mock.patch.dict(os.environ, {"GEMINI_KEY": "g-key"}):
            with unittest.mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
                result = router.generate(
                    user_prompt="hello",
                    model_override="gemini-4-hydrogen",
                    adapter_override="openai_compat",
                )

        self.assertEqual(result.text, "compat override")
        self.assertEqual(result.adapter, "openai_compat")


class TestOpenAIResponsesTopLevelFallback(unittest.TestCase):
    """TC-7: OpenAIResponsesAdapter falls back to top-level output_text field."""

    def test_top_level_output_text_fallback(self):
        """When output array has no output_text chunks, falls back to root output_text."""
        route = _make_route(adapter="openai_responses")

        # Response with no output_text in nested content, only top-level
        response_body = {
            "output": [
                {"type": "other_item", "content": [{"type": "not_output_text", "text": "ignored"}]},
            ],
            "output_text": "Top-level fallback text",
        }
        raw = json.dumps(response_body).encode()
        fp = io.BytesIO(raw)
        cm = unittest.mock.MagicMock()
        cm.__enter__ = lambda s: fp
        cm.__exit__ = unittest.mock.MagicMock(return_value=False)

        with unittest.mock.patch("urllib.request.urlopen", return_value=cm):
            result = OpenAIResponsesAdapter().invoke(route, "key", "", "prompt", 10.0)

        self.assertEqual(result, "Top-level fallback text")

    def test_null_content_field_does_not_crash(self):
        """content: null in an output item must not raise TypeError."""
        route = _make_route(adapter="openai_responses")

        response_body = {
            "output": [
                {"type": "message", "content": None},          # null content
                {"type": "message", "content": [
                    {"type": "output_text", "text": "good chunk"}
                ]},
            ]
        }
        raw = json.dumps(response_body).encode()
        fp = io.BytesIO(raw)
        cm = unittest.mock.MagicMock()
        cm.__enter__ = lambda s: fp
        cm.__exit__ = unittest.mock.MagicMock(return_value=False)

        with unittest.mock.patch("urllib.request.urlopen", return_value=cm):
            result = OpenAIResponsesAdapter().invoke(route, "key", "", "prompt", 10.0)

        self.assertEqual(result, "good chunk")


class TestReasoningAndNimHardening(unittest.TestCase):
    """Verify max_tokens forwarding, 410 immediate failover, and empty content rejection."""

    def test_reasoning_content_only_fails_over(self):
        route1 = _make_route(name="nim-glm", adapter="openai_compat", api_key_env="KEY1", retries=0)
        route2 = _make_route(name="nim-minimax", adapter="openai_compat", api_key_env="KEY2", retries=0)
        router = _FakeRouter([route1, route2])

        reasoning_only = {
            "choices": [{"message": {"role": "assistant", "content": "", "reasoning_content": "thinking..."}}]
        }
        valid_resp = _openai_response("Final answer")
        calls = 0

        def fake_urlopen(req, timeout=None):
            nonlocal calls
            calls += 1
            body = reasoning_only if calls == 1 else valid_resp
            fp = io.BytesIO(json.dumps(body).encode())
            cm = unittest.mock.MagicMock()
            cm.__enter__ = lambda s: fp
            cm.__exit__ = unittest.mock.MagicMock(return_value=False)
            return cm

        with unittest.mock.patch.dict(os.environ, {"KEY1": "k1", "KEY2": "k2"}):
            with unittest.mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
                result = router.generate(user_prompt="plan")

        self.assertEqual(calls, 2)
        self.assertEqual(result.text, "Final answer")
        self.assertEqual(result.route_name, "nim-minimax")

    def test_410_fails_over_immediately(self):
        route1 = _make_route(name="deprecated-route", adapter="openai_compat", api_key_env="KEY1", retries=3)
        route2 = _make_route(name="live-route", adapter="openai_compat", api_key_env="KEY2")
        router = _FakeRouter([route1, route2])
        calls = 0

        def fake_urlopen(req, timeout=None):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise _make_http_error(410, "Gone")
            fp = io.BytesIO(json.dumps(_openai_response("ok")).encode())
            cm = unittest.mock.MagicMock()
            cm.__enter__ = lambda s: fp
            cm.__exit__ = unittest.mock.MagicMock(return_value=False)
            return cm

        with unittest.mock.patch.dict(os.environ, {"KEY1": "k1", "KEY2": "k2"}):
            with unittest.mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
                result = router.generate(user_prompt="hi")

        self.assertEqual(calls, 2)
        self.assertEqual(result.route_name, "live-route")

    def test_max_tokens_sent_in_openai_compat_payload(self):
        route = _make_route(adapter="openai_compat", max_tokens=8192)
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode())
            fp = io.BytesIO(json.dumps(_openai_response("ok")).encode())
            cm = unittest.mock.MagicMock()
            cm.__enter__ = lambda s: fp
            cm.__exit__ = unittest.mock.MagicMock(return_value=False)
            return cm

        with unittest.mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            OpenAICompatAdapter().invoke(route, "key", "", "prompt", 10.0)

        self.assertEqual(captured["body"]["max_tokens"], 8192)


if __name__ == "__main__":
    unittest.main()
