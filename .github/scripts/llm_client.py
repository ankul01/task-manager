"""
llm_client.py — Production-grade multi-provider LLM execution layer.

Zero external dependencies (stdlib only: urllib, json, os, time, random,
argparse, dataclasses, abc, pathlib, sys).

Usage (CLI):
    python3 .github/scripts/llm_client.py \\
        --profile planner \\
        --prompt-file /tmp/prompt.txt \\
        --output-file /tmp/out.txt \\
        --meta-file /tmp/meta.json

Usage (Python import):
    from llm_client import LLMRouter
    router = LLMRouter()
    response = router.generate(profile="planner", user_prompt="…")
    print(response.text)
"""

from __future__ import annotations

import abc
import argparse
import dataclasses
import json
import os
import pathlib
import random
import sys
import time
import urllib.error
import urllib.request
from typing import Optional

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class RouteConfig:
    name: str
    adapter: str
    base_url: str
    model: str
    api_key_env: str
    timeout_sec: float = 120.0
    retries: int = 1
    backoff_sec: float = 10.0
    max_input_chars: Optional[int] = None
    max_tokens: Optional[int] = None


@dataclasses.dataclass
class LLMResponse:
    text: str
    route_name: str
    adapter: str
    model: str
    tier_index: int
    elapsed_sec: float
    attempts: int


# ---------------------------------------------------------------------------
# Transient / non-transient HTTP status classification
# ---------------------------------------------------------------------------

_TRANSIENT_CODES = {429, 500, 502, 503, 504}
_FATAL_CODES = {400, 401, 403, 404, 410}


def _is_transient(code: int) -> bool:
    return code in _TRANSIENT_CODES or 500 <= code < 600


# ---------------------------------------------------------------------------
# Provider adapters
# ---------------------------------------------------------------------------

class ProviderAdapter(abc.ABC):
    """Abstract base; each concrete class handles one API shape."""

    @abc.abstractmethod
    def invoke(
        self,
        route: RouteConfig,
        api_key: str,
        system_prompt: str,
        user_prompt: str,
        timeout_sec: float,
    ) -> str:
        """Call the provider and return the generated text, or raise."""

    # ------------------------------------------------------------------
    # Shared HTTP helper — NEVER logs the api_key value
    # ------------------------------------------------------------------
    @staticmethod
    def _do_request(
        url: str,
        body: bytes,
        headers: dict,
        timeout_sec: float,
    ) -> dict:
        req = urllib.request.Request(
            url,
            data=body,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            return json.load(resp)


class GeminiAdapter(ProviderAdapter):
    """Calls {base_url}/models/{model}:generateContent."""

    def invoke(
        self,
        route: RouteConfig,
        api_key: str,
        system_prompt: str,
        user_prompt: str,
        timeout_sec: float,
    ) -> str:
        url = f"{route.base_url}/models/{route.model}:generateContent"

        payload: dict = {
            "contents": [{"parts": [{"text": user_prompt}]}],
        }
        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }
        if route.max_tokens is not None:
            payload["generationConfig"] = {"maxOutputTokens": route.max_tokens}

        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,          # key in header, never logged
        }

        result = self._do_request(url, body, headers, timeout_sec)
        candidates = result.get("candidates", [])
        if not candidates:
            raise ValueError("Gemini returned no candidates")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "\n".join(p.get("text", "") for p in parts).strip()
        if not text:
            raise ValueError("Gemini returned empty text")
        return text


class OpenAICompatAdapter(ProviderAdapter):
    """Calls {base_url}/chat/completions (OpenAI-compatible endpoints)."""

    def invoke(
        self,
        route: RouteConfig,
        api_key: str,
        system_prompt: str,
        user_prompt: str,
        timeout_sec: float,
    ) -> str:
        url = f"{route.base_url}/chat/completions"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        payload: dict = {"model": route.model, "messages": messages}
        if route.max_tokens is not None:
            payload["max_tokens"] = route.max_tokens
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",   # key in header, never logged
        }

        result = self._do_request(url, body, headers, timeout_sec)
        choices = result.get("choices", [])
        if not choices:
            raise ValueError("OpenAI-compat returned no choices")
        # Require non-empty final content; reasoning_content alone is not a valid answer.
        text = ((choices[0].get("message") or {}).get("content") or "").strip()
        if not text:
            raise ValueError("OpenAI-compat returned empty content")
        return text


class OpenAIResponsesAdapter(ProviderAdapter):
    """Calls {base_url}/responses and extracts output_text chunks."""

    def invoke(
        self,
        route: RouteConfig,
        api_key: str,
        system_prompt: str,
        user_prompt: str,
        timeout_sec: float,
    ) -> str:
        url = f"{route.base_url}/responses"

        payload: dict = {
            "model": route.model,
            "input": user_prompt,
        }
        if system_prompt:
            payload["instructions"] = system_prompt
        if route.max_tokens is not None:
            payload["max_output_tokens"] = route.max_tokens

        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",   # key in header, never logged
        }

        result = self._do_request(url, body, headers, timeout_sec)

        # Extract output_text from the output array (Responses API shape)
        output = result.get("output", [])
        chunks: list[str] = []
        for item in output:
            # item may be {"type": "message", "content": [{"type": "output_text", "text": "…"}]}
            if isinstance(item, dict):
                for content_block in (item.get("content") or []):
                    if isinstance(content_block, dict) and content_block.get("type") == "output_text":
                        chunks.append(content_block.get("text", ""))
        text = "".join(chunks).strip()

        # Fallback: some versions surface output_text at the top level
        if not text:
            text = result.get("output_text", "").strip()

        if not text:
            raise ValueError("OpenAI Responses API returned empty output_text")
        return text


# ---------------------------------------------------------------------------
# Adapter registry — adding a new provider = one class + one entry here
# ---------------------------------------------------------------------------

ADAPTERS: dict[str, type[ProviderAdapter]] = {
    "gemini": GeminiAdapter,
    "openai_compat": OpenAICompatAdapter,
    "openai_responses": OpenAIResponsesAdapter,
}


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

class LLMRouter:
    """
    Loads llm_profiles.json, walks the route waterfall with retry /
    failover logic, and enforces a global_timeout_sec budget.
    """

    # Default config path relative to the repo root (resolved at runtime)
    _DEFAULT_CONFIG = pathlib.Path(".github/config/llm_profiles.json")

    def __init__(self, config_path: Optional[pathlib.Path] = None) -> None:
        self._config_path = config_path or self._DEFAULT_CONFIG
        self._config: dict = {}

    # ------------------------------------------------------------------
    # Config loading
    # ------------------------------------------------------------------

    def _load_config(self) -> dict:
        if self._config:
            return self._config
        cfg_file = pathlib.Path(self._config_path)
        if not cfg_file.is_file():
            # Try resolving relative to the script's repo root
            script_dir = pathlib.Path(__file__).resolve().parent
            repo_root = script_dir.parent.parent
            cfg_file = repo_root / self._config_path
        if not cfg_file.is_file():
            sys.exit(f"[ERROR] Config file not found: {self._config_path}")
        with cfg_file.open(encoding="utf-8") as fh:
            self._config = json.load(fh)
        return self._config

    def _get_routes(self, profile: str) -> tuple[list[RouteConfig], float]:
        cfg = self._load_config()
        global_timeout = float(cfg.get("global_timeout_sec", 540))
        profiles = cfg.get("profiles", {})
        if profile not in profiles:
            sys.exit(f"[ERROR] Profile '{profile}' not found in config. "
                     f"Available: {list(profiles.keys())}")
        raw_routes = profiles[profile].get("routes", [])
        if not raw_routes:
            sys.exit(f"[ERROR] Profile '{profile}' has no routes configured.")
        routes = []
        for r in raw_routes:
            routes.append(RouteConfig(
                name=r["name"],
                adapter=r["adapter"],
                base_url=r["base_url"],
                model=r["model"],
                api_key_env=r["api_key_env"],
                timeout_sec=float(r.get("timeout_sec", 120)),
                retries=int(r.get("retries", 1)),
                backoff_sec=float(r.get("backoff_sec", 10)),
                max_input_chars=r.get("max_input_chars"),
                max_tokens=int(r["max_tokens"]) if r.get("max_tokens") is not None else None,
            ))
        return routes, global_timeout

    # ------------------------------------------------------------------
    # Single-route override (for manual workflow_dispatch overrides)
    # ------------------------------------------------------------------

    @staticmethod
    def _build_override_route(
        model: str,
        adapter: str,
        base_url: str,
        api_key_env: str,
        max_tokens: Optional[int] = None,
    ) -> RouteConfig:
        return RouteConfig(
            name=f"override-{model}",
            adapter=adapter,
            base_url=base_url,
            model=model,
            api_key_env=api_key_env,
            timeout_sec=120,
            retries=1,
            backoff_sec=10,
            max_tokens=max_tokens,
        )

    # ------------------------------------------------------------------
    # Core generate method
    # ------------------------------------------------------------------

    def generate(
        self,
        profile: str = "default",
        system_prompt: str = "",
        user_prompt: str = "",
        model_override: Optional[str] = None,
        adapter_override: Optional[str] = None,
        base_url_override: Optional[str] = None,
        api_key_env_override: Optional[str] = None,
    ) -> LLMResponse:
        routes, global_timeout = self._get_routes(profile)

        # Build effective route list
        if model_override:
            # Determine which profile route matched the model to inherit adapter/base_url
            matched = next((r for r in routes if r.model == model_override), None)
            override_adapter = adapter_override or (matched.adapter if matched else "gemini")
            override_base_url = base_url_override or (matched.base_url if matched else routes[0].base_url)
            override_key_env = api_key_env_override or (matched.api_key_env if matched else routes[0].api_key_env)
            override_max_tokens = matched.max_tokens if matched else (4096 if profile == "reviewer" else 8192)
            routes = [self._build_override_route(
                model=model_override,
                adapter=override_adapter,
                base_url=override_base_url,
                api_key_env=override_key_env,
                max_tokens=override_max_tokens,
            )]

        global_deadline = time.monotonic() + global_timeout
        attempt_log: list[str] = []

        for tier_index, route in enumerate(routes):
            # --- Skip: missing API key ---
            api_key = os.environ.get(route.api_key_env, "").strip()
            if not api_key:
                msg = f"[SKIP] {route.name}: {route.api_key_env} not configured"
                print(msg)
                attempt_log.append(msg)
                continue

            # --- Skip: prompt too large ---
            total_chars = len(system_prompt) + len(user_prompt)
            if route.max_input_chars is not None and total_chars > route.max_input_chars:
                msg = (f"[SKIP] {route.name}: prompt length {total_chars} "
                       f"exceeds max_input_chars {route.max_input_chars}")
                print(msg)
                attempt_log.append(msg)
                continue

            # --- Skip: global deadline already passed ---
            if time.monotonic() >= global_deadline:
                msg = f"[SKIP] {route.name}: global_timeout_sec exhausted"
                print(msg)
                attempt_log.append(msg)
                break

            # Resolve adapter
            adapter_cls = ADAPTERS.get(route.adapter)
            if adapter_cls is None:
                msg = f"[SKIP] {route.name}: unknown adapter '{route.adapter}'"
                print(msg)
                attempt_log.append(msg)
                continue

            adapter = adapter_cls()
            route_start = time.monotonic()
            last_error = ""
            attempts = 0

            for attempt in range(route.retries + 1):
                attempts = attempt + 1

                # Remaining global time
                remaining = global_deadline - time.monotonic()
                if remaining <= 0:
                    last_error = "global timeout expired"
                    break

                effective_timeout = min(route.timeout_sec, remaining)

                try:
                    text = adapter.invoke(
                        route=route,
                        api_key=api_key,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        timeout_sec=effective_timeout,
                    )
                    elapsed = time.monotonic() - route_start
                    result_msg = (f"[OK] {route.name} ({route.adapter}/{route.model}) "
                                  f"tier={tier_index} attempt={attempts} elapsed={elapsed:.1f}s")
                    print(result_msg)
                    return LLMResponse(
                        text=text,
                        route_name=route.name,
                        adapter=route.adapter,
                        model=route.model,
                        tier_index=tier_index,
                        elapsed_sec=elapsed,
                        attempts=attempts,
                    )

                except urllib.error.HTTPError as exc:
                    body_snippet = (exc.read() or b"").decode("utf-8", errors="replace")[:300]
                    last_error = f"HTTP {exc.code}: {body_snippet}"
                    if exc.code in _FATAL_CODES:
                        print(f"[FAIL] {route.name} attempt {attempts}: "
                              f"non-transient HTTP {exc.code} — failing over immediately")
                        break
                    if _is_transient(exc.code) and attempt < route.retries:
                        delay = route.backoff_sec * (2 ** attempt) + random.uniform(0, 2)
                        delay = min(delay, global_deadline - time.monotonic())
                        if delay > 0:
                            print(f"[RETRY] {route.name} attempt {attempts}: "
                                  f"HTTP {exc.code}; sleeping {delay:.1f}s before retry")
                            time.sleep(delay)
                    else:
                        print(f"[FAIL] {route.name} attempt {attempts}: "
                              f"HTTP {exc.code} after retries exhausted — failing over")
                        break

                except (urllib.error.URLError, TimeoutError, OSError) as exc:
                    last_error = f"{type(exc).__name__}: {exc}"
                    if attempt < route.retries:
                        delay = route.backoff_sec * (2 ** attempt) + random.uniform(0, 2)
                        delay = min(delay, global_deadline - time.monotonic())
                        if delay > 0:
                            print(f"[RETRY] {route.name} attempt {attempts}: "
                                  f"{type(exc).__name__}; sleeping {delay:.1f}s before retry")
                            time.sleep(delay)
                    else:
                        print(f"[FAIL] {route.name} attempt {attempts}: "
                              f"{type(exc).__name__} after retries — failing over")
                        break

                except Exception as exc:  # noqa: BLE001
                    last_error = f"{type(exc).__name__}: {exc}"
                    print(f"[FAIL] {route.name} attempt {attempts}: "
                          f"unexpected error — {last_error[:300]}")
                    break

            attempt_log.append(
                f"[TRIED] {route.name} ({route.adapter}/{route.model}): {last_error}"
            )

        # All routes failed
        summary = "\n  ".join(attempt_log)
        sys.exit(
            f"[ERROR] All LLM routes failed for profile '{profile}'.\n"
            f"  {summary}"
        )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="llm_client.py",
        description="Multi-provider LLM client with waterfall failover.",
    )
    p.add_argument("--profile", default="default",
                   help="Profile name from llm_profiles.json (default: 'default')")
    p.add_argument("--config", default=None,
                   help="Path to llm_profiles.json (default: .github/config/llm_profiles.json)")
    p.add_argument("--system-file", default=None,
                   help="Path to file containing the system prompt (optional)")
    p.add_argument("--prompt-file", required=True,
                   help="Path to file containing the user prompt")
    p.add_argument("--output-file", required=True,
                   help="Path to write the LLM output text")
    p.add_argument("--meta-file", default=None,
                   help="Path to write JSON metadata of the winning route")
    p.add_argument("--model-override", default=None,
                   help="Force a single model, bypassing the waterfall")
    p.add_argument("--adapter-override", default=None,
                   help="Adapter to use with --model-override (e.g. 'gemini')")
    p.add_argument("--base-url-override", default=None,
                   help="Base URL to use with --model-override")
    p.add_argument("--api-key-env-override", default=None,
                   help="Env-var name holding the API key for --model-override")
    return p


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    parser = _build_arg_parser()
    args = parser.parse_args()

    config_path = pathlib.Path(args.config) if args.config else None
    router = LLMRouter(config_path=config_path)

    # Read prompts from files
    prompt_path = pathlib.Path(args.prompt_file)
    if not prompt_path.is_file():
        sys.exit(f"[ERROR] --prompt-file not found: {args.prompt_file}")
    user_prompt = prompt_path.read_text(encoding="utf-8")

    system_prompt = ""
    if args.system_file:
        sys_path = pathlib.Path(args.system_file)
        if not sys_path.is_file():
            sys.exit(f"[ERROR] --system-file not found: {args.system_file}")
        system_prompt = sys_path.read_text(encoding="utf-8")

    response = router.generate(
        profile=args.profile,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model_override=args.model_override,
        adapter_override=args.adapter_override,
        base_url_override=args.base_url_override,
        api_key_env_override=args.api_key_env_override,
    )

    # Write output text
    out_path = pathlib.Path(args.output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(response.text, encoding="utf-8")
    print(f"[OUTPUT] Written to {out_path} ({len(response.text)} chars)")

    # Write metadata JSON
    if args.meta_file:
        meta = {
            "route_name": response.route_name,
            "adapter": response.adapter,
            "model": response.model,
            "tier_index": response.tier_index,
            "elapsed_sec": round(response.elapsed_sec, 2),
            "attempts": response.attempts,
            "profile": args.profile,
        }
        meta_path = pathlib.Path(args.meta_file)
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        print(f"[META] Written to {meta_path}")


if __name__ == "__main__":
    main()
