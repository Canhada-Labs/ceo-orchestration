#!/usr/bin/env python3
"""GitHub API client — stdlib wrapper with circuit breaker + retry.

PLAN-019 F-CHAOS-11 (PLAN-018 Chaos finding): GitHub API calls in CI
workflows and the /gh-based commands previously used raw `curl` /
`gh api` without any circuit-breaker protection. A GitHub incident or
rate-limit burst would cause cascading CI failures with no back-off.

This module provides a minimal stdlib-only (urllib) wrapper with:

1. **Token-less or token-bearing** (env var GITHUB_TOKEN if present).
2. **Circuit breaker** — after `breaker_threshold` consecutive 5xx or
   rate-limit-exceeded responses, the breaker opens for `breaker_cooldown`
   seconds and subsequent calls raise `CircuitOpenError` without network
   I/O. One "half-open" request is allowed to re-test after cooldown.
3. **Exponential back-off retry** — 429 (rate-limit) and 5xx responses
   trigger retry with jittered exponential back-off up to `max_retries`.
4. **Deterministic JSON decode** — always returns a dict; API errors
   raise `GitHubAPIError` with the HTTP status + error body (truncated).

## Usage

```python
from github_api_client import GitHubClient, CircuitOpenError

client = GitHubClient()
try:
    data = client.get("/repos/anthropics/claude-code/pulls/123")
except CircuitOpenError:
    # breaker open; shed load gracefully
    ...
```

## Scope

Stdlib only. No requests / httpx. Read-only GET + authenticated POST
for the narrow set of endpoints CI scripts need. NOT a full SDK.

## Thread safety

The breaker state is process-local (module-level). For multi-process
CI jobs, each job has its own breaker — this is intentional (job
isolation). For in-process concurrent callers, a lock guards state
transitions.
"""

from __future__ import annotations

import json
import os
import random
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

GITHUB_API_ROOT = "https://api.github.com"
DEFAULT_USER_AGENT = "ceo-orchestration-github-client/1.0"


class GitHubAPIError(Exception):
    """Non-retryable HTTP error returned by the GitHub API."""

    def __init__(self, status: int, body: str, url: str):
        super().__init__(f"GitHub API {status} on {url}: {body[:200]}")
        self.status = status
        self.body = body
        self.url = url


class CircuitOpenError(Exception):
    """Breaker is open; network call short-circuited to protect downstream."""


@dataclass
class _BreakerState:
    """Consecutive-fail breaker with half-open probe."""

    threshold: int = 5
    cooldown_s: float = 60.0
    consecutive_fails: int = 0
    opened_at: float = 0.0
    half_open_in_flight: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)

    def is_open(self, now: float) -> bool:
        """True if breaker is currently open (callers should shed)."""
        with self.lock:
            if self.opened_at == 0:
                return False
            elapsed = now - self.opened_at
            if elapsed >= self.cooldown_s:
                # Half-open probe window.
                if not self.half_open_in_flight:
                    self.half_open_in_flight = True
                    return False
                return True
            return True

    def record_success(self) -> None:
        with self.lock:
            self.consecutive_fails = 0
            self.opened_at = 0.0
            self.half_open_in_flight = False

    def record_failure(self, now: float) -> None:
        with self.lock:
            self.consecutive_fails += 1
            self.half_open_in_flight = False
            if self.consecutive_fails >= self.threshold:
                self.opened_at = now


class GitHubClient:
    """Thin stdlib GitHub API client with circuit breaker + retry.

    Args:
        token: GitHub personal access token (falls back to GITHUB_TOKEN env).
        breaker_threshold: consecutive 5xx/429 failures before breaker opens.
        breaker_cooldown_s: seconds to wait before half-open probe.
        max_retries: per-call exponential back-off retries on 429/5xx.
        base_url: override for testing (default https://api.github.com).
    """

    def __init__(
        self,
        token: Optional[str] = None,
        breaker_threshold: int = 5,
        breaker_cooldown_s: float = 60.0,
        max_retries: int = 3,
        base_url: str = GITHUB_API_ROOT,
        timeout_s: float = 10.0,
    ) -> None:
        self.token = token or os.environ.get("GITHUB_TOKEN") or ""
        self.max_retries = max_retries
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.breaker = _BreakerState(
            threshold=breaker_threshold,
            cooldown_s=breaker_cooldown_s,
        )

    def _headers(self) -> Dict[str, str]:
        h = {
            "Accept": "application/vnd.github+json",
            "User-Agent": DEFAULT_USER_AGENT,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> Tuple[int, bytes]:
        if not path.startswith("/"):
            path = "/" + path
        url = self.base_url + path
        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, method=method, headers=self._headers()
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read() or b""

    def _call_with_retry(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        now = time.monotonic()
        if self.breaker.is_open(now):
            raise CircuitOpenError(
                f"GitHub API breaker OPEN for {method} {path}; call shed"
            )

        last_status = 0
        last_body = b""
        for attempt in range(self.max_retries + 1):
            status, raw = self._request(method, path, body)
            last_status = status
            last_body = raw

            # Success path: 2xx.
            if 200 <= status < 300:
                self.breaker.record_success()
                if not raw:
                    return {}
                try:
                    return json.loads(raw.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # Non-JSON response — return raw for caller inspection.
                    return {"_raw": raw.decode("utf-8", errors="replace")}

            # Non-retryable client errors (4xx except 429) — fail fast.
            if 400 <= status < 500 and status != 429:
                self.breaker.record_success()  # API reachable, just rejected us.
                raise GitHubAPIError(
                    status,
                    raw.decode("utf-8", errors="replace"),
                    self.base_url + path,
                )

            # Retryable: 429 / 5xx. Back off with jitter.
            self.breaker.record_failure(time.monotonic())
            if attempt < self.max_retries:
                delay = (2 ** attempt) + random.uniform(0, 0.5)
                time.sleep(min(delay, 30.0))
            if self.breaker.is_open(time.monotonic()):
                raise CircuitOpenError(
                    f"GitHub API breaker opened mid-call for {method} {path}"
                )

        # Exhausted retries.
        raise GitHubAPIError(
            last_status,
            last_body.decode("utf-8", errors="replace"),
            self.base_url + path,
        )

    def get(self, path: str) -> Dict[str, Any]:
        """GET request with breaker + retry. Returns decoded JSON or {_raw: ...}."""
        return self._call_with_retry("GET", path)

    def post(self, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """POST request with breaker + retry. Body is JSON-encoded."""
        return self._call_with_retry("POST", path, body)

    # ---- Introspection helpers (for tests / observability) ----

    def breaker_is_open(self) -> bool:
        """True if breaker currently forbids new calls (half-open in flight excluded)."""
        return self.breaker.opened_at > 0 and (
            time.monotonic() - self.breaker.opened_at < self.breaker.cooldown_s
        )

    def breaker_state(self) -> Dict[str, Any]:
        """Diagnostic snapshot (safe to log)."""
        return {
            "consecutive_fails": self.breaker.consecutive_fails,
            "opened_at_monotonic": self.breaker.opened_at,
            "threshold": self.breaker.threshold,
            "cooldown_s": self.breaker.cooldown_s,
        }


def main() -> int:
    """CLI: `github-api-client.py GET /repos/<owner>/<repo>` prints JSON."""
    import sys

    if len(sys.argv) < 3:
        print(
            "usage: github-api-client.py <GET|POST> <path> [<json_body>]",
            file=sys.stderr,
        )
        return 2
    method, path = sys.argv[1].upper(), sys.argv[2]
    body: Optional[Dict[str, Any]] = None
    if len(sys.argv) >= 4 and method != "GET":
        try:
            body = json.loads(sys.argv[3])
        except json.JSONDecodeError as e:
            print(f"bad JSON body: {e}", file=sys.stderr)
            return 2
    client = GitHubClient()
    try:
        if method == "GET":
            out = client.get(path)
        elif method == "POST":
            out = client.post(path, body)
        else:
            print(f"unsupported method: {method}", file=sys.stderr)
            return 2
    except CircuitOpenError as e:
        print(f"CIRCUIT_OPEN: {e}", file=sys.stderr)
        return 3
    except GitHubAPIError as e:
        print(f"API_ERROR {e.status}: {e.body[:500]}", file=sys.stderr)
        return 4
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
