#!/usr/bin/env python3
"""OSV.dev / OSSF malicious-packages supply-chain gate (PLAN-133 §E2).

Purpose
-------
Before a skill/squad install runs an ``npx`` / ``uvx`` / ``pip install`` of a
third-party package, ask OSV.dev whether that exact package version (or the
package at large) carries a **malicious-package advisory** (the ``MAL-*`` /
OSV-malicious id space sourced from the OpenSSF malicious-packages feed).

Decision contract (load-bearing — see PLAN-133 §3 doctrine + §E2):

* **MAL hit  → fail-CLOSED**  — verdict ``BLOCK``. A present MAL advisory can
  NEVER be downgraded to "unknown" (property test ``test_mal_never_downgraded``).
* **No advisory → fail-OPEN** — verdict ``ALLOW`` (``unknown`` reason). OSV not
  knowing about a package is NOT evidence of malice.
* **Network timeout / connection error → fail-OPEN + breadcrumb** — verdict
  ``ALLOW`` with reason ``network_timeout`` / ``network_error``. Never hang.
* **Malformed / empty body → inconclusive** — verdict ``ALLOW`` with reason
  ``malformed_response``. Inconclusive is treated as fail-OPEN, but it is a
  DISTINCT reason from ``unknown`` and from ``clean`` and is NEVER an
  allow-on-MAL: an empty/garbled body can never satisfy the MAL branch.
* **Offline-detect / hard timeout → advisory-skip + breadcrumb** — verdict
  ``SKIP`` with reason ``offline`` / ``disabled``. Never hang the install.

Safety posture
--------------
* stdlib only (``urllib``), Python >= 3.9, ``from __future__ import annotations``.
* **fail-open-on-infra**: any exception in the network / parse path resolves to
  ALLOW (advisory). We never block an install because OSV is slow or broken.
* **Default-OFF for the BLOCKING behavior.** With ``CEO_OSV_GATE`` unset (the
  default) the checker is *advisory*: it computes the same verdict and emits the
  same breadcrumb, but :func:`gate_exit_code` returns 0 even on a MAL hit so an
  install is never blocked by a behavioral change that has not been measured.
  Set ``CEO_OSV_GATE=block`` to make a MAL hit return a non-zero gate exit code.
* **Hard timeout** on every request (``CEO_OSV_TIMEOUT_S``, default 4s, hard
  ceiling 10s) so the gate can never out-live a fast install step.
* ``CEO_OSV_DISABLE=1`` (or the framework-wide ``CEO_SOTA_DISABLE=1``) → SKIP.

This module emits a **stderr JSON breadcrumb** only; it does NOT write to the
HMAC-chained audit log (that would require touching the canonical
``_lib/audit_emit.py`` ``_KNOWN_ACTIONS`` set — see ``E2.proposal.md`` for the
staged closed-enum ``supply_chain_advisory_emitted`` audit action + SHA bump).
The breadcrumb is value-safe: it carries the package *name* and *ecosystem*
(needed to action a finding) and the advisory *ids*, but never the install
command bytes, never any env/secret, never a network error body.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from typing import Dict, List, Optional, Tuple

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

OSV_QUERYBATCH_URL = "https://api.osv.dev/v1/querybatch"
OSV_QUERY_URL = "https://api.osv.dev/v1/query"

# Hard ceiling so a misconfigured env can never make the gate out-live an
# install. Below this we honor CEO_OSV_TIMEOUT_S; above it we clamp.
_TIMEOUT_DEFAULT_S = 4.0
_TIMEOUT_HARD_CEILING_S = 10.0

# OSV ecosystem names (https://ossf.github.io/osv-schema/#defined-ecosystems).
_ECO_NPM = "npm"
_ECO_PYPI = "PyPI"

# Malicious-advisory id prefixes (OpenSSF malicious-packages → OSV "MAL-YYYY-N";
# some feeds also surface "OSV-MAL-..." or "GHSA-...MAL..." — we match by the
# OSV-schema "malicious" id family conservatively + a `MAL` token anywhere in
# the id, but ONLY ids; we never infer malice from free text.
_MAL_ID_RE = re.compile(r"(?:^|[-/])MAL[-_]", re.IGNORECASE)

# Verdicts.
VERDICT_BLOCK = "BLOCK"   # MAL advisory present — fail-CLOSED
VERDICT_ALLOW = "ALLOW"   # no MAL advisory / unknown / inconclusive — fail-OPEN
VERDICT_SKIP = "SKIP"     # disabled / offline / nothing to check — advisory-skip

# Reasons (closed enum — mirrors the staged audit closed-enum field).
REASON_MAL = "mal_advisory_present"
REASON_CLEAN = "clean"                    # OSV answered, no MAL ids
REASON_UNKNOWN = "unknown"                # OSV had no record for the package
REASON_MALFORMED = "malformed_response"   # empty/garbled body — inconclusive
REASON_NETWORK_TIMEOUT = "network_timeout"
REASON_NETWORK_ERROR = "network_error"
REASON_OFFLINE = "offline"
REASON_DISABLED = "disabled"
REASON_NO_PACKAGE = "no_package"          # nothing parseable to check

_VALID_REASONS = frozenset({
    REASON_MAL, REASON_CLEAN, REASON_UNKNOWN, REASON_MALFORMED,
    REASON_NETWORK_TIMEOUT, REASON_NETWORK_ERROR, REASON_OFFLINE,
    REASON_DISABLED, REASON_NO_PACKAGE,
})


# --------------------------------------------------------------------------- #
# Env helpers
# --------------------------------------------------------------------------- #

def _is_disabled(env: Optional[Dict[str, str]] = None) -> bool:
    e = os.environ if env is None else env
    return e.get("CEO_OSV_DISABLE", "0") == "1" or e.get("CEO_SOTA_DISABLE", "0") == "1"


def _is_offline(env: Optional[Dict[str, str]] = None) -> bool:
    """Explicit offline switch (CI / air-gapped installs).

    We do NOT probe DNS — a probe is itself a network call that can hang. An
    adopter / CI sets CEO_OSV_OFFLINE=1 to declare the box has no egress.
    """
    e = os.environ if env is None else env
    return e.get("CEO_OSV_OFFLINE", "0") == "1"


def _gate_mode(env: Optional[Dict[str, str]] = None) -> str:
    """Return the gate mode: 'block' or 'advisory' (default).

    Default-OFF: only CEO_OSV_GATE=block makes a MAL hit non-zero exit.
    """
    e = os.environ if env is None else env
    return "block" if e.get("CEO_OSV_GATE", "").strip().lower() == "block" else "advisory"


def _timeout_s(env: Optional[Dict[str, str]] = None) -> float:
    e = os.environ if env is None else env
    raw = e.get("CEO_OSV_TIMEOUT_S", "")
    try:
        val = float(raw) if raw else _TIMEOUT_DEFAULT_S
    except (TypeError, ValueError):
        val = _TIMEOUT_DEFAULT_S
    if val <= 0:
        val = _TIMEOUT_DEFAULT_S
    # Hard ceiling — never let env make the gate out-live the install.
    return min(val, _TIMEOUT_HARD_CEILING_S)


# --------------------------------------------------------------------------- #
# Command parsing — first package token + ecosystem
# --------------------------------------------------------------------------- #

# An install command can be wrapped (`sudo`, `env FOO=bar`, `&&` chains). We
# scan tokens for the FIRST recognized installer verb and take the first
# package-shaped argument after it. This is intentionally conservative: it is a
# supply-chain *advisory*, not a parser of arbitrary shell.
_INSTALLER_VERBS = {
    "npx": _ECO_NPM,
    "uvx": _ECO_PYPI,        # uvx runs a PyPI tool
    "pipx": _ECO_PYPI,
    "uv": _ECO_PYPI,         # `uv pip install ...` / `uv tool install ...`
    "pip": _ECO_PYPI,
    "pip3": _ECO_PYPI,
}

# Flags we skip when hunting for the package token.
_SKIP_FLAG_RE = re.compile(r"^-")

# A package spec like `name`, `name@1.2.3`, `name==1.2.3`, `@scope/name`,
# `name>=1.0`. We split off the version for the OSV query.
_PYPI_VER_SPLIT = re.compile(r"(===|==|>=|<=|~=|!=|>|<|=)")


def _strip_quotes(tok: str) -> str:
    if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in ("'", '"'):
        return tok[1:-1]
    return tok


def _tokenize(command: str) -> List[str]:
    """Cheap shell-ish tokenizer (whitespace split + quote strip).

    We deliberately avoid ``shlex`` round-tripping surprises; the goal is to
    find a package name, not to faithfully reconstruct the command.
    """
    out: List[str] = []
    for raw in command.replace("\t", " ").split(" "):
        tok = _strip_quotes(raw.strip())
        if tok:
            out.append(tok)
    return out


def _looks_like_package(tok: str, ecosystem: str) -> bool:
    if not tok or _SKIP_FLAG_RE.match(tok):
        return False
    # Local path / URL / VCS installs are not OSV-name queries.
    if tok.startswith((".", "/", "~")):
        return False
    if "://" in tok or tok.startswith("git+"):
        return False
    if ecosystem == _ECO_NPM:
        # npm package: optional @scope/, then name; reject obvious file specs.
        if tok.endswith((".tgz", ".tar.gz")):
            return False
        return True
    # PyPI: a requirement; reject `.whl` / requirement files.
    if tok.endswith((".whl", ".txt")) or tok.startswith("-r"):
        return False
    return True


def _split_name_version(tok: str, ecosystem: str) -> Tuple[str, Optional[str]]:
    """Return (package_name, version_or_None) for an OSV query."""
    if ecosystem == _ECO_NPM:
        # @scope/name@1.2.3  → split on the LAST '@' if it is not the scope '@'.
        if tok.startswith("@"):
            # @scope/name[@ver]
            rest = tok[1:]
            if "@" in rest:
                name_part, ver = rest.rsplit("@", 1)
                return "@" + name_part, ver or None
            return "@" + rest, None
        if "@" in tok:
            name, ver = tok.rsplit("@", 1)
            return name, ver or None
        return tok, None
    # PyPI
    m = _PYPI_VER_SPLIT.search(tok)
    if m:
        name = tok[: m.start()].strip()
        ver = tok[m.end():].strip().split(",", 1)[0].strip()
        # `name[extra]` → drop the extras marker for the OSV name.
        name = name.split("[", 1)[0]
        return name, (ver or None)
    name = tok.split("[", 1)[0]
    return name, None


def parse_install_target(command: str) -> Optional[Dict[str, Optional[str]]]:
    """Extract the FIRST install target from a command string.

    Returns ``{"name": str, "version": Optional[str], "ecosystem": str}`` or
    ``None`` if the command is not a recognized package install.
    """
    if not command or not isinstance(command, str):
        return None
    tokens = _tokenize(command)
    i = 0
    n = len(tokens)
    while i < n:
        verb = tokens[i]
        eco = _INSTALLER_VERBS.get(verb)
        if eco is None:
            i += 1
            continue
        # `uv pip install X` / `uv tool install X` / `pip install X`.
        j = i + 1
        # Skip subcommands for uv/pip-style verbs until we pass `install`.
        if verb in ("uv", "pip", "pip3", "pipx"):
            saw_install = (verb == "npx")  # never; placeholder
            while j < n:
                t = tokens[j]
                if t in ("pip", "tool", "install", "run", "--with"):
                    if t == "install":
                        saw_install = True
                    j += 1
                    continue
                break
            if not saw_install and verb in ("pip", "pip3", "uv", "pipx"):
                # `pip download` / `uv venv` etc. — not an install.
                i += 1
                continue
        # Now hunt for the first package-shaped token.
        while j < n:
            cand = tokens[j]
            if _looks_like_package(cand, eco):
                name, ver = _split_name_version(cand, eco)
                if name:
                    return {"name": name, "version": ver, "ecosystem": eco}
            j += 1
        i += 1
    return None


# --------------------------------------------------------------------------- #
# OSV query
# --------------------------------------------------------------------------- #

def _extract_mal_ids(vulns: List[dict]) -> List[str]:
    """Return the subset of advisory ids that are malicious-package ids.

    Looks at the top-level ``id`` and every ``aliases`` entry. A present MAL id
    is the BLOCK trigger; this function never invents one.
    """
    mal: List[str] = []
    for v in vulns:
        if not isinstance(v, dict):
            continue
        candidates: List[str] = []
        vid = v.get("id")
        if isinstance(vid, str):
            candidates.append(vid)
        aliases = v.get("aliases")
        if isinstance(aliases, list):
            candidates.extend(a for a in aliases if isinstance(a, str))
        for c in candidates:
            if _MAL_ID_RE.search(c):
                mal.append(c)
    # De-dup, stable order.
    seen = set()
    out = []
    for m in mal:
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out


def _post_json(url: str, payload: dict, timeout_s: float) -> Tuple[Optional[dict], str]:
    """POST JSON, return (parsed_body_or_None, status_reason).

    status_reason ∈ {clean-path "ok", REASON_NETWORK_TIMEOUT,
    REASON_NETWORK_ERROR, REASON_MALFORMED}. Never raises.
    """
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310 (https only, fixed host)
            raw = resp.read()
    except urllib.error.URLError as exc:  # includes socket.timeout via reason
        reason = getattr(exc, "reason", None)
        if isinstance(reason, TimeoutError) or "timed out" in str(reason).lower():
            return None, REASON_NETWORK_TIMEOUT
        return None, REASON_NETWORK_ERROR
    except TimeoutError:
        return None, REASON_NETWORK_TIMEOUT
    except Exception:  # noqa: BLE001 — fail-open-on-infra
        return None, REASON_NETWORK_ERROR
    if not raw:
        return None, REASON_MALFORMED
    try:
        body = json.loads(raw.decode("utf-8", errors="replace"))
    except (ValueError, UnicodeDecodeError):
        return None, REASON_MALFORMED
    if not isinstance(body, dict):
        return None, REASON_MALFORMED
    return body, "ok"


def query_osv(
    name: str,
    ecosystem: str,
    version: Optional[str],
    timeout_s: float,
    _url: str = OSV_QUERY_URL,
) -> Dict[str, object]:
    """Query OSV for a single package; return a verdict dict.

    Verdict dict shape: ``{"verdict", "reason", "advisory_ids", "name",
    "ecosystem"}``. Pure decision logic — no exit code, no I/O side effects
    beyond the single HTTP call.
    """
    pkg: Dict[str, str] = {"name": name, "ecosystem": ecosystem}
    payload: Dict[str, object] = {"package": pkg}
    if version:
        payload["version"] = version

    body, status = _post_json(_url, payload, timeout_s)

    if status == REASON_NETWORK_TIMEOUT:
        return _verdict(VERDICT_ALLOW, REASON_NETWORK_TIMEOUT, [], name, ecosystem)
    if status == REASON_NETWORK_ERROR:
        return _verdict(VERDICT_ALLOW, REASON_NETWORK_ERROR, [], name, ecosystem)
    if status == REASON_MALFORMED or body is None:
        # Inconclusive — fail-OPEN, but DISTINCT from unknown and NEVER a MAL
        # downgrade: an empty/garbled body can not produce a MAL id.
        return _verdict(VERDICT_ALLOW, REASON_MALFORMED, [], name, ecosystem)

    vulns = body.get("vulns")
    if not isinstance(vulns, list) or len(vulns) == 0:
        # OSV answered with no record → unknown (fail-OPEN).
        return _verdict(VERDICT_ALLOW, REASON_UNKNOWN, [], name, ecosystem)

    mal_ids = _extract_mal_ids(vulns)
    if mal_ids:
        # fail-CLOSED — a present MAL advisory is BLOCK, never downgraded.
        return _verdict(VERDICT_BLOCK, REASON_MAL, mal_ids, name, ecosystem)

    # Vulns present but none malicious → clean (advisory; not our concern here).
    return _verdict(VERDICT_ALLOW, REASON_CLEAN, [], name, ecosystem)


def _verdict(
    verdict: str,
    reason: str,
    advisory_ids: List[str],
    name: str,
    ecosystem: str,
) -> Dict[str, object]:
    assert reason in _VALID_REASONS, "closed-enum reason invariant"
    # MAL-never-downgraded property enforced at the type boundary: a MAL reason
    # MUST carry BLOCK and at least one id; nothing else may claim REASON_MAL.
    if reason == REASON_MAL:
        assert verdict == VERDICT_BLOCK and advisory_ids, "MAL must be BLOCK+ids"
    return {
        "verdict": verdict,
        "reason": reason,
        "advisory_ids": list(advisory_ids),
        "name": name,
        "ecosystem": ecosystem,
    }


# --------------------------------------------------------------------------- #
# Breadcrumb (stderr JSON — NOT the HMAC chain; see E2.proposal.md)
# --------------------------------------------------------------------------- #

def emit_breadcrumb(result: Dict[str, object], *, stream=None) -> None:
    """Write one value-safe JSON breadcrumb line to stderr.

    Never raises (fail-open-on-infra). Carries name/ecosystem/ids only — never
    the command bytes, env values, or a network error body.
    """
    stream = sys.stderr if stream is None else stream
    record = {
        "event": "supply_chain_advisory_emitted",
        "verdict": result.get("verdict"),
        "reason": result.get("reason"),
        "ecosystem": result.get("ecosystem"),
        "package": result.get("name"),
        "advisory_ids": result.get("advisory_ids", []),
        "ts": int(time.time()),
    }
    try:
        stream.write(json.dumps(record, separators=(",", ":")) + "\n")
        stream.flush()
    except Exception:  # pragma: no cover — fail-open-on-infra
        pass


# --------------------------------------------------------------------------- #
# Top-level check + gate exit code
# --------------------------------------------------------------------------- #

def check_command(
    command: str,
    env: Optional[Dict[str, str]] = None,
    *,
    _url: str = OSV_QUERY_URL,
) -> Dict[str, object]:
    """Full pipeline for a single command string. Always returns a verdict.

    Never raises; never hangs beyond the hard timeout. Emits a breadcrumb.
    """
    if _is_disabled(env):
        result = _verdict(VERDICT_SKIP, REASON_DISABLED, [], "", "")
        emit_breadcrumb(result)
        return result
    if _is_offline(env):
        result = _verdict(VERDICT_SKIP, REASON_OFFLINE, [], "", "")
        emit_breadcrumb(result)
        return result

    target = parse_install_target(command)
    if target is None:
        result = _verdict(VERDICT_SKIP, REASON_NO_PACKAGE, [], "", "")
        # No breadcrumb for non-install commands (noise reduction).
        return result

    name = str(target.get("name") or "")
    ecosystem = str(target.get("ecosystem") or "")
    version = target.get("version")
    version = str(version) if version else None

    try:
        result = query_osv(name, ecosystem, version, _timeout_s(env), _url=_url)
    except Exception:  # noqa: BLE001 — fail-open-on-infra, never block on a bug
        result = _verdict(VERDICT_ALLOW, REASON_NETWORK_ERROR, [], name, ecosystem)
    emit_breadcrumb(result)
    return result


def gate_exit_code(result: Dict[str, object], env: Optional[Dict[str, str]] = None) -> int:
    """Map a verdict to a process exit code, honoring the default-OFF gate.

    * advisory mode (default): always 0 — the checker is observe-only.
    * block mode (``CEO_OSV_GATE=block``): BLOCK → 3 (a MAL hit); everything
      else → 0. Never returns non-zero for a timeout / unknown / malformed
      (those are fail-OPEN by contract).
    """
    if _gate_mode(env) != "block":
        return 0
    if result.get("verdict") == VERDICT_BLOCK and result.get("reason") == REASON_MAL:
        return 3
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="osv_check",
        description=(
            "OSV.dev malicious-package supply-chain gate (PLAN-133 E2). "
            "Advisory by default; set CEO_OSV_GATE=block to fail-CLOSED on a "
            "MAL advisory. Never hangs an install (hard timeout + fail-open)."
        ),
    )
    p.add_argument(
        "--command",
        help="The install command string to scan (e.g. 'npx left-pad@1.0.0').",
    )
    p.add_argument(
        "--package",
        help="Explicit package name (skips command parsing).",
    )
    p.add_argument(
        "--ecosystem",
        choices=[_ECO_NPM, _ECO_PYPI],
        help="OSV ecosystem for --package.",
    )
    p.add_argument("--version", help="Optional package version for --package.")
    p.add_argument(
        "--json",
        action="store_true",
        help="Emit the verdict dict as JSON on stdout (in addition to the breadcrumb).",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.package:
        if not args.ecosystem:
            sys.stderr.write("--ecosystem is required with --package\n")
            return 2
        try:
            result = query_osv(args.package, args.ecosystem, args.version, _timeout_s())
        except Exception:  # noqa: BLE001 — fail-open-on-infra
            result = _verdict(VERDICT_ALLOW, REASON_NETWORK_ERROR, [], args.package, args.ecosystem)
        emit_breadcrumb(result)
    elif args.command:
        result = check_command(args.command)
    else:
        sys.stderr.write("provide --command or --package\n")
        return 2

    if args.json:
        sys.stdout.write(json.dumps(result, separators=(",", ":")) + "\n")
    return gate_exit_code(result)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
