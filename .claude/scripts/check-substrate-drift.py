#!/usr/bin/env python3
"""check-substrate-drift.py — fast-lane substrate drift detector (lane C2).

Answers, OFFLINE by default, the three questions whose late answers cost the
framework days of latency. Measured: Claude Fable 5.1 launched 2026-09-01; the
framework adopted it explicitly in ``ab56e76`` (2026-09-02) and shipped that
adoption with v1.4.0 on 2026-09-15. ``@openai/codex`` 0.155.1 was published to
npm on 2026-09-18 and first noticed on 2026-09-22.

  1. CODEX — is the INSTALLED ``@openai/codex`` the version the ADR-182
     payload manifest pins (``.claude/governance/codex-cli-pin-manifest.json``
     ``package_version``)? A different version means the pair-rail's payload
     sha256 check will not match and ``check_pair_rail.py --verify-codex-pin``
     fails CLOSED at the next L3+ call. The installed version is READ, never
     probed: the binary is not executed (ADR-182 M4 — an unverified payload is
     never exec'd, ``pair-rail-gate.sh`` Gate 3a), and the drift case is
     exactly the unverified one. The launcher found on ``$PATH`` is resolved
     the way ``check_pair_rail._resolve_codex_payload`` resolves it
     (``<pkg>/bin/<launcher>`` -> ``<pkg>``); the version comes from the
     payload package ``@openai/codex-<os>-<cpu>/package.json``
     (``<version>-<os>-<cpu>``), else from ``<pkg>/package.json``. With a
     cached ``--fetch`` result it also answers: has npm ``@openai/codex``
     ``latest`` moved PAST the pin? No cache, or a cache older than
     ``--max-cache-age-days``, is a named ``unknown`` (never a silent
     "current"). This check compares VERSION STRINGS only; it never hashes
     the payload. An install whose version equals the pin but whose bytes
     differ reads as no finding here, while ``check_pair_rail.py
     --verify-codex-pin`` (the payload sha256 gate) says ``mismatch``. So a
     codex result with no finding is not "pair-rail verified"; the report's
     codex line and component say so (``_CODEX_VERSION_ONLY``).
  2. CLAUDE CODE — does the installed ``claude --version`` differ from the
     version the substrate ledger (``.claude/scripts/substrate-watch.json``,
     component ``claude_code``) was last reconciled against?
  3. MODELS — which model ids does the INSTALLED Claude Code know that the
     ADR-149 ``AVAILABLE_MODELS_WORKING_SET`` does not cover?

Model catalog source (declared honestly). Claude Code (measured on 2.1.280,
the darwin-arm64 build, 2026-09-22) exposes NO documented listing surface:
``claude --help`` lists no models subcommand and the settings ``model`` key
is a free string. The installed binary does, however, embed a structured
baked catalog (layout measured on that one build only) — records of
the shape ``{id:"claude-…",family:"…",display_name:"…",…}`` followed by an
``aliases:{<name>:{default:"claude-…"…}}`` block and a
``latest_per_family:{<family>:"claude-…"}`` block. This script scrapes THAT
structure defensively (bounded regexes over a read-only mmap of the resolved
binary) and fails OPEN with a named ``unknown`` when no record matches — a
binary format change degrades to "unknown", never to a silent "current".

Findings are NAMED (component, kind, severity, claim, next commands):
  severity ``drift``   — actionable divergence (``--strict`` exits 1 on these)
  severity ``info``    — context worth seeing, never a failure
  severity ``unknown`` — an input could not be observed (infra fail-open)

Adopter shape: an input FILE that is absent makes its comparison NOT
APPLICABLE (``info``); a file that is present but unreadable or unparseable
stays a named ``unknown``. The codex pin manifest (``.claude/governance/``)
and ADR-149 reach no adopter (install.sh ships only ``.claude/adr/README.md``;
neither directory is an upgrade target). The substrate ledger is absent after
a fresh install (install.sh copies only the ``*.sh``/``*.py``/``*.yaml`` of
``.claude/scripts/``) but present after an upgrade (the whole directory is an
upgrade target) — and then it records the MAINTAINER's reconciliation, which
the next upgrade overwrites again. So the ledger is compared only in the
framework checkout (the pin manifest or ADR-149 is present), or when
``--ledger`` names a ledger explicitly; elsewhere it is NOT APPLICABLE.

Network: NONE unless ``--fetch`` is passed. ``--fetch`` runs
``npm view @openai/codex dist-tags --json`` ONCE and caches the validated
result under the project runtime state dir (resolved by the single resolver
``_lib/runtime_paths.py``); every later offline run reads that cache and
reports its age. Executables run: ``claude --version`` (one code-defined
``[<bin>, "--version"]`` probe; skipped by ``--no-probe``; from ``$PATH`` or
``--claude-bin``, never from a file) and, ONLY under ``--fetch``, that one
``npm view`` (from ``$PATH`` or ``--npm-bin``). ``codex`` is never run.

The re-pin recommendation first asks ``re-pin-codex.py`` (``mold_inventory``)
whether a pack already pins the version: then the next step is to apply that
pack (the Owner's ceremony), never to generate another. Otherwise it asks
``newest_mold`` which mold the generator would build from, so it never names
a mold the generator refuses; for a constants-block mold the command carries
``--ga-tag``. When the newest pack's mold is not generator-compatible it says
"clone it by hand" and names why.

Adopter shape of the catalog check: without ADR-149 the comparison is NOT
APPLICABLE and the Claude Code binary is not scanned at all. This file ships
to adopters (``install.sh`` copies every ``.claude/scripts/*.py``); in an
adopter tree the three comparisons report NOT APPLICABLE (no pin manifest,
the ledger is the maintainer's, no ADR-149) — see "Adopter shape" above.

Wiring: when this file was introduced nothing ran it — not ``/ceo-boot``
(``.claude/scripts/ceo-boot.py``), not a workflow, not the release
preflight — and ``re-pin-codex.py`` is reached only through the commands
this script prints. Until a caller exists, the latency it cures (a new model
or a codex release noticed days late) stays uncured: it answers only when
someone runs it. The natural caller is ``/ceo-boot``, offline (no
``--fetch``), reading the cache an explicit ``--fetch`` left.

Exit codes:
  0 — always in report mode (drift, unknown and infra failures included)
  1 — ``--strict`` only: at least one ``drift`` finding
  2 — CLI usage error (argparse)

Emits NO audit events. Apart from the bytecode the Python interpreter itself
caches for the standard library at startup, it writes nothing except the
``--fetch`` cache file: the repo modules it loads at run time write no
bytecode, and npm's own cache, logs and
update-notifier state are pointed at a throwaway directory next to the cache
file and removed when the fetch returns. Probe output is untrusted: it is
parsed against a strict grammar and never echoed (a failed probe reports its
rc only); scraped display names keep only a plain-name charset.
Stdlib only. Python >= 3.9.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import importlib.util
import json
import mmap
import os
import posixpath
import re
import shutil
import subprocess  # nosec B404 — code-defined read-only probes, fail-soft
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_REPO_ROOT = SCRIPT_DIR.parents[1]

SCHEMA = 1
_PROBE_TIMEOUT_S = 8.0
_FETCH_TIMEOUT_S = 30.0
_CATALOG_MAX_BYTES = 1 << 30  # 1 GiB: larger than any shipped CC build
_PKG_JSON_MAX_BYTES = 1 << 20  # a package.json larger than 1 MiB is not read
_CACHE_STALE_DAYS_DEFAULT = 7
_CACHE_SUBDIR = "substrate-drift"
_CACHE_NAME = "codex-npm-dist-tags.json"
_NPM_PACKAGE = "@openai/codex"
#: The registry --fetch names explicitly (never ~/.npmrc's choice). Kept
#: equal to re-pin-codex.py NPM_REGISTRY_ARGS (a unit test pins the
#: equality), so the detector and the generator read the same "latest".
#: Both flags: a scoped ``@openai:registry`` line outranks ``registry``.
_NPM_REGISTRY = "https://registry.npmjs.org/"
_NPM_REGISTRY_ARGS = ("--registry=" + _NPM_REGISTRY, "--@openai:registry=" + _NPM_REGISTRY)

_SEMVER_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.\-]{1,64}))?")
_SEMVER_FULL_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.\-]{1,64})?$")
_RELEASE_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_TAG_KEY_RE = re.compile(r"^[A-Za-z0-9._\-]{1,64}$")
_RANGE_CLAUSE_RE = re.compile(r"^(>=|<=|>|<|==|=)?\s*(\d+\.\d+\.\d+(?:-[0-9A-Za-z.\-]+)?)$")

# Baked-catalog record: {id:"claude-x",family:"x",display_name:"X"} — keys may
# be bare (minified JS) or quoted (JSON); whitespace tolerated. Anchored on
# "{" (measured 2026-09-23: scan_catalog ~0.09 s over the 221 MB CC 2.1.281
# darwin-arm64 binary, maintainer's Apple M3 Max; one machine, one build).
_RECORD_RE = re.compile(
    rb'\{\s*"?id"?\s*:\s*"(claude-[a-z0-9][a-z0-9.\-]{0,62})"\s*,\s*'
    rb'"?family"?\s*:\s*"([a-z][a-z0-9]{0,31})"\s*,\s*'
    rb'"?display_name"?\s*:\s*"([^"\\\x00-\x1f]{1,64})"'
)
_ALIASES_OPEN_RE = re.compile(rb'"?aliases"?\s*:\s*\{')
_ALIAS_ENTRY_RE = re.compile(
    rb'(?<![A-Za-z0-9_])"?([a-z][a-z0-9_]{0,31})"?\s*:\s*\{\s*'
    rb'"?default"?\s*:\s*"(claude-[a-z0-9][a-z0-9.\-]{0,62})"'
)
_LATEST_RE = re.compile(rb'"?latest_per_family"?\s*:\s*\{([^{}]{0,2048})\}')
_LATEST_ENTRY_RE = re.compile(
    rb'"?([a-z][a-z0-9_]{0,31})"?\s*:\s*"(claude-[a-z0-9][a-z0-9.\-]{0,62})"'
)
_CATALOG_WINDOW = 64 * 1024  # cap on the gap after a record searched for aliases/latest
_UNSAFE_NAME_RE = re.compile(r"[^A-Za-z0-9 ._()+\-]")

# The harness's availableModels match, verified in the CC 2.1.280 binary:
# ``function wS(e,n){if(!e.startsWith(n))return!1;return
# e.length===n.length||e[n.length]==="-"}`` — a SEGMENT-prefix match.
_PREFIX_SEMANTICS_NOTE = "segment-prefix match verified in Claude Code 2.1.280"
#: What the codex check compares (C-R1-04): version strings, never bytes.
_CODEX_VERSION_ONLY = ("version check only — the payload sha256 gate is "
                       "check_pair_rail.py --verify-codex-pin")


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def _finding(component: str, kind: str, severity: str, claim: str,
             next_cmds: Optional[List[str]] = None,
             extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "component": component, "kind": kind, "severity": severity,
        "claim": claim, "next": list(next_cmds or []),
    }
    if extra:
        row.update(extra)
    return row


def semver_key(text: str) -> Optional[Tuple[Any, ...]]:
    """Sortable SemVer §11 key: a release outranks its own prereleases, and
    prerelease identifiers compare numerically where numeric (alpha.9 < alpha.10)."""
    m = _SEMVER_RE.search(text or "")
    if not m:
        return None
    pre = m.group(4) or ""
    pre_key = tuple((0, int(p), "") if p.isdigit() else (1, 0, p)
                    for p in pre.split(".")) if pre else ()
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)),
            0 if pre else 1, pre_key)


def _semver_str(text: str) -> Optional[str]:
    m = _SEMVER_RE.search(text or "")
    return m.group(0) if m else None


def parse_range(text: str) -> Optional[List[Tuple[str, Tuple[Any, ...]]]]:
    clauses: List[Tuple[str, Tuple[Any, ...]]] = []
    for raw in (text or "").split(","):
        raw = raw.strip()
        m = _RANGE_CLAUSE_RE.match(raw)
        if not m:
            return None
        key = semver_key(m.group(2))
        if key is None:
            return None
        clauses.append((m.group(1) or "==", key))
    return clauses or None


def in_range(version: str, clauses: List[Tuple[str, Tuple[Any, ...]]]) -> bool:
    key = semver_key(version)
    if key is None:
        return False
    for op, bound in clauses:
        ok = {
            ">=": key >= bound, ">": key > bound, "<=": key <= bound,
            "<": key < bound, "==": key == bound, "=": key == bound,
        }[op]
        if not ok:
            return False
    return True


def _run(argv: List[str], timeout: float, cwd: Optional[str] = None,
         env: Optional[Dict[str, str]] = None) -> Tuple[int, str, str]:
    """Run a code-defined argv; NEVER raises. rc -1 = could not run.

    The child's stdout/stderr are UNTRUSTED data: callers parse them against a
    strict grammar and never echo them into a report (a probe that fails is
    reported by its rc alone — the channel is closed by removal).
    """
    try:
        proc = subprocess.run(  # nosec B603 — argv is code-defined, no shell
            argv, capture_output=True, text=True, timeout=timeout, cwd=cwd,
            env=env, check=False,
        )
    except FileNotFoundError:
        return -1, "", "not found: {}".format(argv[0])
    except subprocess.TimeoutExpired:
        return -1, "", "timeout after {:.0f}s: {}".format(timeout, argv[0])
    except (OSError, ValueError) as exc:
        return -1, "", "{}: {}".format(type(exc).__name__, exc)
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def _resolve_bin(explicit: Optional[str], name: str) -> Optional[str]:
    if explicit:
        return explicit if os.path.isfile(explicit) else None
    return shutil.which(name)


def probe_version(bin_path: Optional[str], name: str) -> Tuple[Optional[str], str]:
    """(version, note). version None => unknown, note says why."""
    if not bin_path:
        return None, "{} not found on PATH (or --{}-bin missing)".format(name, name)
    rc, out, _err = _run([bin_path, "--version"], _PROBE_TIMEOUT_S)
    if rc != 0:
        return None, "{} --version failed (rc={}; run it by hand to see why)".format(name, rc)
    ver = _semver_str(out)
    if ver is None:
        return None, "{} --version printed no X.Y.Z version".format(name)
    return ver, "probed {} --version".format(bin_path)


def npm_platform_suffix() -> Optional[str]:
    """The ``<os>-<cpu>`` suffix of this host's ``@openai/codex-<os>-<cpu>``
    payload package (npm's ``process.platform``/``process.arch`` spelling —
    the same suffixes re-pin-codex.py maps to a targetTriple), or None."""
    import platform as _platform
    try:
        sysname, machine = _platform.system(), _platform.machine().lower()
    except Exception:  # noqa: BLE001 — infra fail-open
        return None
    os_name = {"Darwin": "darwin", "Linux": "linux", "Windows": "win32"}.get(sysname)
    cpu = ("arm64" if machine in ("arm64", "aarch64")
           else "x64" if machine in ("x86_64", "amd64") else None)
    return "{}-{}".format(os_name, cpu) if os_name and cpu else None


def _package_json(path: Path) -> Tuple[Optional[str], Optional[str]]:
    """(name, version) of a package.json; (None, None) when absent or unusable.

    Untrusted data: both values are validated by the caller before any use
    and never echoed unvalidated.
    """
    try:
        with open(path, "rb") as fh:
            raw = fh.read(_PKG_JSON_MAX_BYTES + 1)
        if len(raw) > _PKG_JSON_MAX_BYTES:
            return None, None
        data = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError):
        return None, None
    if not isinstance(data, dict):
        return None, None
    name, ver = data.get("name"), data.get("version")
    return (name if isinstance(name, str) else None,
            ver if isinstance(ver, str) else None)


def read_codex_install(bin_path: Optional[str]) -> Tuple[Optional[str], str]:
    """(version, note) of the installed ``@openai/codex`` — EXEC-FREE.

    Nothing is run (ADR-182 M4: an unverified payload is never exec'd, and a
    version that differs from the pin is by definition unverified). The npm
    launcher on ``$PATH`` resolves to ``<pkg>/bin/<launcher>``, as in
    ``check_pair_rail._resolve_codex_payload``; ``<pkg>/package.json`` must
    name ``@openai/codex``. The payload package ``@openai/codex-<os>-<cpu>``
    is looked up in ``node_modules/`` from ``<pkg>`` upward (the same walk)
    and its ``<version>-<os>-<cpu>`` names the binary the launcher would
    spawn; without it (the launcher's own ``vendor/`` fallback) the launcher
    package's version is used. version None => unknown, the note says why.
    """
    if not bin_path:
        return None, "codex not found on PATH (or --codex-bin missing)"
    try:
        pkg_dir = Path(bin_path).resolve(strict=True).parent.parent
    except (OSError, RuntimeError):
        return None, "codex entry {} does not resolve".format(bin_path)
    name, main = _package_json(pkg_dir / "package.json")
    if name != _NPM_PACKAGE or main is None or not _SEMVER_FULL_RE.match(main):
        return None, ("codex at {} is not the npm {} launcher layout (<pkg>/bin/<launcher> "
                      "next to <pkg>/package.json); its version is read from package.json, "
                      "never by running it".format(bin_path, _NPM_PACKAGE))
    suffix = npm_platform_suffix()
    if suffix is None:
        return main, "read {} (host platform unmapped: payload package not looked up)".format(
            pkg_dir / "package.json")
    tail = "-" + suffix
    for anc in [pkg_dir] + list(pkg_dir.parents):
        pkg_json = anc / "node_modules" / "@openai" / ("codex" + tail) / "package.json"
        if not pkg_json.is_file():
            continue
        _name, raw = _package_json(pkg_json)
        ver = raw[:-len(tail)] if raw and raw.endswith(tail) else None
        if ver is None or not _SEMVER_FULL_RE.match(ver):
            return None, "payload package {} carries no <version>{} version".format(pkg_json, tail)
        note = "read {} (the binary was not executed)".format(pkg_json)
        if ver != main:
            note += "; the launcher package says {}".format(main)
        return ver, note
    return main, ("read {}; no payload package @openai/codex{} under node_modules "
                  "(launcher vendor/ fallback)".format(pkg_dir / "package.json", tail))


def _rel(repo: Path, path: Path) -> str:
    try:
        return str(path.relative_to(repo))
    except ValueError:
        return str(path)


# --------------------------------------------------------------------------
# codex
# --------------------------------------------------------------------------

def read_codex_pin(repo: Path) -> Dict[str, Any]:
    """Pinned package_version (manifest) + pre-flight semver range (pin txt)."""
    gov = repo / ".claude" / "governance"
    manifest = gov / "codex-cli-pin-manifest.json"
    out: Dict[str, Any] = {"manifest": _rel(repo, manifest), "package_version": None,
                           "range": None, "status": "ok", "note": ""}
    if not manifest.is_file():
        out["status"] = "absent"
        out["note"] = "no pin manifest (adopter installs do not receive .claude/governance)"
        return out
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        ver = data.get("package_version") if isinstance(data, dict) else None
    except (OSError, ValueError) as exc:
        out["status"] = "unreadable"
        out["note"] = "manifest unreadable: {}".format(exc)
        return out
    if not isinstance(ver, str) or not _SEMVER_FULL_RE.match(ver):
        out["status"] = "unreadable"
        out["note"] = "manifest package_version missing or not semver"
        return out
    out["package_version"] = ver
    pin_txt = gov / "codex-cli-pin.txt"
    try:
        lines = [ln.strip() for ln in pin_txt.read_text(encoding="utf-8").splitlines()]
        body = [ln for ln in lines if ln and not ln.startswith("#")]
        out["range"] = body[-1] if body else None
    except OSError:
        out["range"] = None
    return out


def _load_repin_tool() -> Tuple[Optional[Any], str]:
    """re-pin-codex.py (next to this script) — the ONE mold predicate.

    The recommendation below never ranks or parses molds itself: it asks the
    generator which mold it would build from (``newest_mold``), so it cannot
    name a mold the generator refuses. Fail-open, named.
    """
    path = SCRIPT_DIR / "re-pin-codex.py"
    try:
        spec = importlib.util.spec_from_file_location("_re_pin_codex_for_drift", str(path))
        if spec is None or spec.loader is None:
            return None, "cannot load {}".format(path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, ""
    except Exception as exc:  # noqa: BLE001 — infra fail-open, named
        return None, "cannot load {}: {}: {}".format(path, type(exc).__name__, exc)


def repin_next(repo: Path, version: str) -> List[str]:
    """The exact next command(s) to re-pin ``version`` — probed, not assumed.

    The mold is the one ``re-pin-codex.newest_mold`` names: packs ranked by
    the version each pins (its ``codex-cli-pin-manifest.json.new``), never by
    plan number. When the newest pack's mold is not generator-compatible the
    answer is "clone it by hand" — never an older mold that parses (that
    would drop what the newer pack hardened).
    """
    cmds: List[str] = []
    if not _RELEASE_RE.match(version):
        # re-pin-codex.py accepts X.Y.Z releases only (its own semver grammar).
        cmds.append("{} is a prerelease — the ADR-182 pin ceremony pins releases only; do not "
                    "re-pin it".format(version))
        cmds.append("python3 .claude/hooks/check_pair_rail.py --verify-codex-pin")
        return cmds
    in_repo = (repo / ".claude" / "scripts" / "re-pin-codex.py").is_file()
    tool, err = _load_repin_tool()
    mold: Optional[Dict[str, Any]] = None
    existing = _existing_pack_for(tool, repo, version) if tool is not None else None
    stale = _stale_pack_reason(tool, repo, existing) if existing is not None else None
    if existing is not None and stale is not None:
        # C-R2M-07: its ceremony would die at its own drift guard ("remonte o
        # pack"), and the generator refuses a second pack for the version.
        cmds.append("the existing pack {} for {} is STALE: {} — its ceremony dies at its "
                    "drift guard; remove {} and run this check again for the generator "
                    "command (re-pin-codex.py refuses a second pack for the same "
                    "version)".format(posixpath.dirname(existing), version, stale,
                                      posixpath.dirname(existing)))
    elif existing is not None:
        # A pack that already pins this version is signed and applied, never
        # regenerated (C-R1-CL-08): the generator would refuse a second pack
        # for the same version, and cloning by hand would duplicate it.
        cmds.append("apply the existing pack {}: its codex-cli-pin-manifest.json.new already "
                    "pins {} — Owner ceremony: bash {} --dry-run, then the same without "
                    "--dry-run (ADR-182); do not generate another pack".format(
                        posixpath.dirname(existing), version, existing))
    elif tool is None:
        cmds.append("re-pin {} via the ADR-182 pin ceremony (the mold check is unavailable: "
                    "{})".format(version, err))
    else:
        try:
            mold = tool.newest_mold(repo)
        except tool.RePinError as exc:
            cmds.append("re-pin {} via the ADR-182 pin ceremony — no generator-compatible mold: "
                        "{}".format(version, exc))
        except OSError as exc:
            cmds.append("re-pin {} via the ADR-182 pin ceremony (the mold check failed: {})".format(
                version, type(exc).__name__))
        else:
            if mold is None:
                cmds.append("re-pin {} via the ADR-182 pin ceremony (no pack mold found under "
                            ".claude/plans/{})".format(version, tool.MOLD_GLOB))
            elif not mold["compatible"]:
                cmds.append("re-pin {} by cloning the newest pin-pack mold {} by hand (ADR-182 "
                            "ceremony) — no generator-compatible mold: re-pin-codex.py refuses it "
                            "({})".format(version, mold["rel"], mold["reason"]))
            elif in_repo:
                ga = (" --ga-tag vA.B.C" if mold.get("grammar") == tool.GRAMMAR_CONSTANTS
                      else "")
                ga_note = ("; vA.B.C = the release tag the re-pin must follow (the mold's "
                           "GA_TAG)" if ga else "")
                cmds.append("python3 .claude/scripts/re-pin-codex.py {} --mold {} --plan "
                            "PLAN-NNN{}   # PLAN-NNN = the plan that carries the re-pin{}; "
                            "emits the pin pack (never applies it); the Owner signs it "
                            "(ADR-182)".format(version, mold["rel"], ga, ga_note))
            else:
                cmds.append("re-pin {} by cloning the newest pin-pack mold {} (ADR-182 "
                            "ceremony)".format(version, mold["rel"]))
    cmds.append("python3 .claude/hooks/check_pair_rail.py --verify-codex-pin")
    return cmds


def _existing_pack_for(tool: Any, repo: Path, version: str) -> Optional[str]:
    """The mold of a pack whose manifest ``.new`` already pins ``version``,
    unless the live manifest pins it too (then that pack is the applied one).
    None when there is none or the inventory cannot be read (fail-open: the
    caller falls back to the generator's own answer)."""
    pinned = read_codex_pin(repo).get("package_version")
    if pinned == version:
        return None
    try:
        want = tool.parse_version(version)
        rows = tool.mold_inventory(repo)
    except Exception:  # noqa: BLE001 — infra fail-open; newest_mold() names it
        return None
    hits = sorted(r["rel"] for r in rows if r.get("target") == want)
    return hits[-1] if hits else None


def _stale_pack_reason(tool: Any, repo: Path, mold_rel: str) -> Optional[str]:
    """Why an existing constants-block pack can no longer be applied, or None.

    That grammar records the sha256 of the live pin and manifest when the
    pack was generated (``BASE_PIN_SHA256``/``BASE_MAN_SHA256``) and its
    ceremony dies when either file changed since. A heredoc-grammar pack
    records neither, and a mold this generator does not parse is not judged
    (fail-open: the caller keeps the "apply the existing pack" advice).
    """
    try:
        text = (repo / mold_rel).read_bytes().decode("utf-8")
        parts = tool.parse_mold(text)
    except Exception:  # noqa: BLE001 — infra/unparsed mold: not judged
        return None
    if parts.get("grammar") != getattr(tool, "GRAMMAR_CONSTANTS", None):
        return None
    consts = parts.get("consts") or {}
    changed = []
    for key, rel in (("BASE_PIN_SHA256", tool.PIN_REL), ("BASE_MAN_SHA256", tool.MANIFEST_REL)):
        entry = consts.get(key)
        if entry is None:
            return None
        try:
            live = hashlib.sha256((repo / rel).read_bytes()).hexdigest()
        except OSError:
            return None
        if entry[1].strip("'") != live:
            changed.append(rel)
    if not changed:
        return None
    return "{} changed after the pack was generated (its {} no longer match)".format(
        " and ".join(changed), "BASE_*_SHA256" if len(changed) > 1 else "BASE_* sha256")


def _codex_installed_findings(repo: Path, pin: Dict[str, Any],
                              installed: str) -> List[Dict[str, Any]]:
    pinned = pin["package_version"]
    clauses = parse_range(pin["range"]) if pin.get("range") else None
    range_note = ""
    if clauses is not None:
        range_note = " (pre-flight range {}: {})".format(
            pin["range"], "inside" if in_range(installed, clauses) else "OUTSIDE")
    if installed == pinned:
        if clauses is not None and not in_range(pinned, clauses):
            return [_finding("codex", "CODEX_PIN_PACK_INCOHERENT", "drift",
                             "manifest pins {} but codex-cli-pin.txt range {} excludes it".format(
                                 pinned, pin["range"]), repin_next(repo, pinned))]
        return []
    ikey, pkey = semver_key(installed), semver_key(pinned)
    claim = ("installed codex {} is not the pinned {}{} — the payload sha256 will not "
             "match the manifest, so the pair-rail fails CLOSED at the next L3+ call"
             ).format(installed, pinned, range_note)
    if (ikey is not None and pkey is not None and ikey < pkey) or not _RELEASE_RE.match(installed):
        # Older than the pin, or a prerelease (never re-pinned): restore.
        nxt = ["npm i -g {}@{}   # Owner-run: restore the pinned binary".format(
            _NPM_PACKAGE, pinned),
            "python3 .claude/hooks/check_pair_rail.py --verify-codex-pin"]
    else:
        nxt = repin_next(repo, installed) + [
            "or restore the pinned binary (Owner-run): npm i -g {}@{}".format(
                _NPM_PACKAGE, pinned)]
    return [_finding("codex", "CODEX_INSTALLED_NOT_PINNED", "drift", claim, nxt,
                     {"installed": installed, "pinned": pinned})]


# --------------------------------------------------------------------------
# npm dist-tags cache (the ONLY network path; opt-in)
# --------------------------------------------------------------------------

def default_cache_path(repo: Path, project: Optional[str]) -> Optional[Path]:
    """Cache under the project runtime state dir — the single resolver.

    ``project`` None keeps the resolver's own precedence (CLAUDE_PROJECT_DIR,
    else cwd); an explicit --repo-root is passed AS GIVEN (no realpath: the
    harness slugs the launch path as given — runtime_paths "symlink honesty").
    """
    hooks = repo / ".claude" / "hooks"
    candidates = [hooks, SCRIPT_DIR.parent / "hooks"]
    for cand in candidates:
        if (cand / "_lib" / "runtime_paths.py").is_file():
            if str(cand) not in sys.path:
                sys.path.insert(0, str(cand))
            break
    try:
        from _lib import runtime_paths as _rp  # noqa: E402
    except Exception:  # noqa: BLE001 — infra fail-open
        return None
    return _rp.runtime_state_dir(project=project) / _CACHE_SUBDIR / _CACHE_NAME


def validate_dist_tags(obj: Any) -> Optional[Dict[str, str]]:
    """Untrusted data: keep only tag -> strict-semver pairs (first 256).

    Entries of any other shape are DROPPED, never echoed; the result is None
    (unusable) unless a strict-semver ``latest`` survives — the one tag the
    upstream check reads.
    """
    if not isinstance(obj, dict):
        return None
    tags: Dict[str, str] = {}
    for key, val in list(obj.items())[:256]:
        if isinstance(key, str) and _TAG_KEY_RE.match(key) and \
                isinstance(val, str) and _SEMVER_FULL_RE.match(val):
            tags[key] = val
    return tags if "latest" in tags else None


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, str(path))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def fetch_dist_tags(npm_bin: Optional[str], cache_path: Path,
                    now: _dt.datetime) -> Tuple[bool, str]:
    """Run ``npm view @openai/codex dist-tags --json`` ONCE; cache on success."""
    if not npm_bin:
        return False, "npm not found on PATH (or --npm-bin missing)"
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    except OSError as exc:
        return False, "cannot create cache dir: {}".format(exc)
    # npm keeps its own cache/logs/update-notifier state (~/.npm by default);
    # point all of it at a throwaway dir removed on return, so --fetch writes
    # nothing outside the one cache file.
    try:
        with tempfile.TemporaryDirectory(prefix="npm-", dir=str(cache_path.parent)) as scratch:
            env = dict(os.environ)
            env.update({"npm_config_cache": scratch, "npm_config_logs_max": "0",
                        "npm_config_update_notifier": "false", "npm_config_fund": "false",
                        "npm_config_audit": "false"})
            rc, out, _err = _run([npm_bin, "view", _NPM_PACKAGE, "dist-tags", "--json",
                                  *_NPM_REGISTRY_ARGS],
                                 _FETCH_TIMEOUT_S, cwd=scratch, env=env)
    except OSError as exc:
        return False, "npm scratch dir: {}".format(exc)
    if rc != 0:
        return False, "npm view failed (rc={}; run it by hand to see npm's message)".format(rc)
    try:
        tags = validate_dist_tags(json.loads(out))
    except ValueError:
        tags = None
    if tags is None:
        return False, "npm view printed no valid dist-tags JSON"
    payload = {"schema": SCHEMA, "package": _NPM_PACKAGE, "registry": _NPM_REGISTRY,
               "fetched_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "dist_tags": tags}
    try:
        _atomic_write_json(cache_path, payload)
    except OSError as exc:
        return False, "cannot write cache: {}".format(exc)
    return True, "fetched and cached"


def load_cache(cache_path: Optional[Path]) -> Tuple[Optional[Dict[str, Any]], str]:
    if cache_path is None:
        return None, "cache path unresolvable (runtime_paths unavailable)"
    if not cache_path.is_file():
        return None, "absent"
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, "unreadable: {}".format(exc)
    if not isinstance(data, dict) or data.get("package") != _NPM_PACKAGE:
        return None, "unparseable: wrong shape"
    if data.get("registry") != _NPM_REGISTRY:
        return None, "unparseable: cache not fetched from {}".format(_NPM_REGISTRY)
    tags = validate_dist_tags(data.get("dist_tags"))
    try:
        fetched = _dt.datetime.strptime(str(data.get("fetched_at")), "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        fetched = None
    if tags is None or fetched is None:
        return None, "unparseable: invalid dist_tags or fetched_at"
    return {"dist_tags": tags, "fetched_at": fetched}, "ok"


def _upstream_findings(repo: Path, pinned: Optional[str], cache: Optional[Dict[str, Any]],
                       cache_note: str, now: _dt.datetime,
                       stale_days: int) -> List[Dict[str, Any]]:
    # An absent or stale cache is UNKNOWN, never info: offline, "npm latest is
    # past the pin" is only as fresh as the last explicit --fetch, and a
    # quiet "current" over a never-refreshed cache is the blind spot this
    # check exists to close. The fetch itself stays explicit (no network
    # unless asked).
    if cache is None:
        if cache_note == "absent":
            return [_finding("codex", "CODEX_UPSTREAM_NOT_FETCHED", "unknown",
                             "no cached npm dist-tags — whether npm latest is past the pin "
                             "is not known offline",
                             ["python3 .claude/scripts/check-substrate-drift.py --fetch"])]
        return [_finding("codex", "CODEX_UPSTREAM_CACHE_UNUSABLE", "unknown",
                         "npm dist-tags cache {}".format(cache_note),
                         ["python3 .claude/scripts/check-substrate-drift.py --fetch"])]
    out: List[Dict[str, Any]] = []
    age_days = max(0, (now - cache["fetched_at"]).days)
    if age_days > stale_days:
        out.append(_finding("codex", "CODEX_UPSTREAM_CACHE_STALE", "unknown",
                            "cached npm dist-tags are {} days old (> {}) — a newer npm latest "
                            "would not show".format(age_days, stale_days),
                            ["python3 .claude/scripts/check-substrate-drift.py --fetch"]))
    latest = cache["dist_tags"].get("latest")
    lkey, pkey = semver_key(latest or ""), semver_key(pinned or "")
    if latest and lkey is not None and pkey is not None and lkey > pkey:
        out.append(_finding(
            "codex", "CODEX_UPSTREAM_AHEAD", "drift",
            "npm {} latest {} is past the exact pin {} (cache {} day(s) old) — re-pin "
            "BEFORE the next release cut; never a casual npm update -g".format(
                _NPM_PACKAGE, latest, pinned, age_days),
            repin_next(repo, latest), {"latest": latest, "pinned": pinned}))
    return out


def check_codex(repo: Path, codex_bin: Optional[str], probe: bool,
                cache: Optional[Dict[str, Any]], cache_note: str,
                now: _dt.datetime, stale_days: int) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    pin = read_codex_pin(repo)
    comp: Dict[str, Any] = {"pin": pin, "installed": None, "probe_note": "not read (--no-probe)",
                            "verification": _CODEX_VERSION_ONLY}
    findings: List[Dict[str, Any]] = []
    if pin["status"] == "absent":
        findings.append(_finding("codex", "CODEX_PIN_NOT_APPLICABLE", "info", pin["note"]))
        return comp, findings
    if pin["status"] != "ok":
        findings.append(_finding("codex", "CODEX_PIN_UNREADABLE", "unknown", pin["note"]))
        return comp, findings
    if probe:
        installed, note = read_codex_install(codex_bin)
        comp["installed"], comp["probe_note"] = installed, note
        if installed is None:
            findings.append(_finding("codex", "CODEX_NOT_OBSERVED", "unknown", note))
        else:
            findings.extend(_codex_installed_findings(repo, pin, installed))
    findings.extend(_upstream_findings(repo, pin["package_version"], cache, cache_note,
                                       now, stale_days))
    return comp, findings


# --------------------------------------------------------------------------
# claude code version vs the substrate ledger
# --------------------------------------------------------------------------

def ledger_last_seen(ledger_path: Path, key: str = "claude_code") -> Tuple[Optional[str], str]:
    """(version, note); note ``absent`` = no ledger file at all (adopter shape)."""
    if not ledger_path.is_file():
        return None, "absent"
    try:
        data = json.loads(ledger_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, "ledger unreadable: {}".format(exc)
    for comp in (data.get("components") or []) if isinstance(data, dict) else []:
        if isinstance(comp, dict) and comp.get("key") == key:
            ver = (comp.get("last_seen") or {}).get("version")
            if isinstance(ver, str) and _SEMVER_FULL_RE.match(ver):
                return ver, "ok"
            return None, "ledger {} last_seen.version is not semver".format(key)
    return None, "ledger has no {} component".format(key)


def is_framework_checkout(repo: Path) -> bool:
    """The framework's own checkout: it carries a maintainer-only input (the
    codex pin manifest or ADR-149), which neither install.sh nor upgrade.sh
    delivers to an adopter."""
    return ((repo / ".claude" / "governance" / "codex-cli-pin-manifest.json").is_file()
            or (repo / ".claude" / "adr" / "ADR-149-model-id-allowlist.md").is_file())


def check_claude_code(installed: Optional[str], probe_note: str, ledger_path: Path,
                      applicable: bool = True) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    if not applicable:
        # An upgraded adopter HAS the ledger (upgrade.sh replaces .claude/scripts/
        # whole), but it records the maintainer's reconciliation and the next
        # upgrade overwrites any local refresh: comparing against it would be a
        # standing drift with no fix the adopter can keep.
        return ({"installed": installed, "probe_note": probe_note, "ledger_last_seen": None},
                [_finding("claude_code", "CC_LEDGER_NOT_APPLICABLE", "info",
                          "not the framework checkout (no codex pin manifest, no ADR-149): the "
                          "substrate ledger here is the maintainer's, shipped by upgrade.sh — "
                          "pass --ledger to compare against one anyway")])
    seen, note = ledger_last_seen(ledger_path)
    comp = {"installed": installed, "probe_note": probe_note, "ledger_last_seen": seen}
    if note == "absent":
        # Same doctrine as the codex pin manifest: install.sh copies only the
        # *.sh/*.py/*.yaml of .claude/scripts/, so a freshly installed adopter
        # has no ledger — not applicable, never a standing "unknown".
        return comp, [_finding(
            "claude_code", "CC_LEDGER_NOT_APPLICABLE", "info",
            "no substrate ledger at {} — nothing to compare the installed Claude Code "
            "against (install.sh does not copy substrate-watch.json)".format(ledger_path))]
    if installed is None:
        return comp, [_finding("claude_code", "CC_NOT_OBSERVED", "unknown", probe_note)]
    if seen is None:
        return comp, [_finding("claude_code", "CC_LEDGER_UNREADABLE", "unknown", note)]
    if installed == seen:
        return comp, []
    direction = "AHEAD of" if (semver_key(installed) or ()) > (semver_key(seen) or ()) else "BEHIND"
    return comp, [_finding(
        "claude_code", "CC_LEDGER_DRIFT", "drift",
        "installed Claude Code {} is {} the version the substrate ledger was reconciled "
        "against ({}) — re-verify the knob routes before trusting old assumptions".format(
            installed, direction, seen),
        ["python3 .claude/scripts/check-substrate-watch.py --probe-installed",
         "python3 .claude/scripts/check-substrate-watch.py --refresh   # prints the Owner-run ledger refresh recipe"],
        {"installed": installed, "ledger_last_seen": seen})]


# --------------------------------------------------------------------------
# model catalog (baked into the installed Claude Code)
# --------------------------------------------------------------------------

def _object_body(window: bytes, start: int) -> Tuple[Optional[int], bytes]:
    """Scan from just after an opening ``{``: (index of the matching ``}``,
    per-byte depth map of the body — 1 = top level, 0 = inside a string).
    (None, b"") when the object does not close inside ``window``."""
    depth, quote, esc = 1, 0, False
    depths = bytearray()
    for i in range(start, len(window)):
        c = window[i]
        depths.append(0 if quote else min(depth, 255))
        if quote:
            if esc:
                esc = False
            elif c == 0x5C:  # backslash
                esc = True
            elif c == quote:
                quote = 0
            continue
        if c in (0x22, 0x27, 0x60):  # " ' `
            quote = c
        elif c == 0x7B:
            depth += 1
        elif c == 0x7D:
            depth -= 1
            if depth == 0:
                return i, bytes(depths)
    return None, b""


def _parse_blocks(window: bytes) -> Tuple[Optional[Dict[str, str]], Optional[Dict[str, str]]]:
    """(aliases, latest_per_family) found in ``window``; None = block absent.

    Alias entries are read only at the TOP level of the brace-matched aliases
    object — a later sibling (``defaults:{x:{default:"claude-…"}}``) or a
    nested object can never pass for an alias. An unclosed object is absent.
    """
    aliases: Optional[Dict[str, str]] = None
    latest: Optional[Dict[str, str]] = None
    lm = _LATEST_RE.search(window)
    am = _ALIASES_OPEN_RE.search(window)
    if am is not None:
        end, depths = _object_body(window, am.end())
        if end is not None:
            aliases = {}
            for em in _ALIAS_ENTRY_RE.finditer(window, am.end(), end):
                if depths[em.start() - am.end()] == 1:
                    aliases.setdefault(em.group(1).decode("ascii"), em.group(2).decode("ascii"))
    if lm is not None:
        latest = {}
        for em in _LATEST_ENTRY_RE.finditer(lm.group(1)):
            latest.setdefault(em.group(1).decode("ascii"), em.group(2).decode("ascii"))
    return aliases, latest


def _parse_catalog_bytes(buf: Any) -> Dict[str, Any]:
    """Records, then the aliases / latest_per_family blocks that FOLLOW a record.

    Each block is searched in the gap between one record and the next (the
    tail after the last record is capped at _CATALOG_WINDOW); the LAST gap
    holding a block wins. A stray catalog-shaped record after the blocks
    therefore cannot hide them (it only opens one more, empty, gap).
    """
    records: List[Dict[str, str]] = []
    seen = set()
    spans: List[Tuple[int, int]] = []
    for m in _RECORD_RE.finditer(buf):
        spans.append((m.start(), m.end()))
        mid = m.group(1).decode("ascii", "replace")
        if mid in seen:
            continue
        seen.add(mid)
        records.append({"id": mid, "family": m.group(2).decode("ascii", "replace"),
                        # scraped text is data: only a plain-name charset survives
                        "display_name": _UNSAFE_NAME_RE.sub(
                            "?", m.group(3).decode("utf-8", "replace"))})
    aliases: Dict[str, str] = {}
    latest: Dict[str, str] = {}
    for i, (_, end) in enumerate(spans):
        limit = spans[i + 1][0] if i + 1 < len(spans) else end + _CATALOG_WINDOW
        found_a, found_l = _parse_blocks(bytes(buf[end:min(limit, end + _CATALOG_WINDOW)]))
        if found_a is not None:
            aliases = found_a
        if found_l is not None:
            latest = found_l
    return {"records": records, "aliases": aliases, "latest_per_family": latest}


def scan_catalog(path: Optional[str]) -> Dict[str, Any]:
    """Scrape the baked model catalog from ``path``; status ok|unknown, never raises."""
    out: Dict[str, Any] = {"status": "unknown", "source": path, "note": "",
                           "records": [], "aliases": {}, "latest_per_family": {}}
    if not path:
        out["note"] = "no Claude Code binary to scan (claude not on PATH; pass --catalog-file)"
        return out
    real = os.path.realpath(path)
    out["source"] = real
    try:
        size = os.path.getsize(real)
        if size == 0 or size > _CATALOG_MAX_BYTES:
            out["note"] = "binary size {} outside (0, {}]".format(size, _CATALOG_MAX_BYTES)
            return out
        with open(real, "rb") as fh:
            with mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as buf:
                parsed = _parse_catalog_bytes(buf)
    except (OSError, ValueError) as exc:
        out["note"] = "cannot read {}: {}".format(real, exc)
        return out
    out.update(parsed)
    if not parsed["records"]:
        out["note"] = ("no baked-catalog records matched in {} (format changed, or a wrapper "
                       "script — pass --catalog-file <the real binary>)".format(real))
        return out
    out["status"] = "ok"
    return out


def model_family_gen(model_id: str) -> Tuple[str, Tuple[int, ...]]:
    """('opus', (5, 5)) for claude-opus-5-5; a legacy id with the generation first
    (claude-<major>-<minor>-<family>) gives ('<family>', (<major>, <minor>)).

    Numeric tokens of >= 6 digits are snapshot dates and do not order generations.
    """
    tokens = model_id.split("-")[1:]
    family = next((t for t in tokens if t.isalpha()), "")
    gen = tuple(int(t) for t in tokens if t.isdigit() and len(t) < 6)
    return family, gen


def load_working_set(repo: Path) -> Tuple[Optional[List[str]], str]:
    """ADR-149 working set via the ONE parser (generate-available-models.py)."""
    gen_path = SCRIPT_DIR / "generate-available-models.py"
    adr = repo / ".claude" / "adr" / "ADR-149-model-id-allowlist.md"
    if not adr.is_file():
        return None, "absent"
    try:
        spec = importlib.util.spec_from_file_location("_gen_available_models", str(gen_path))
        if spec is None or spec.loader is None:
            return None, "cannot load {}".format(gen_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        ids, source = mod.parse_working_set(adr)
    except Exception as exc:  # noqa: BLE001 — infra fail-open, named
        return None, "ADR-149 working set unreadable: {}".format(exc)
    return list(ids), source


def _new_model_next(repo: Path) -> List[str]:
    cmds = ["adopt via an Owner-signed ADR-149 amendment appending the id to "
            "AVAILABLE_MODELS_WORKING_SET, then: python3 .claude/scripts/generate-available-models.py --check"]
    if (repo / "scripts" / "upgrade.sh").is_file():  # probed: the framework checkout only
        cmds.append("python3 .claude/scripts/derive-settings-baselines.py --check scripts/upgrade.sh")
    doc = repo / "docs" / "adopter-new-model-fast-access.md"
    if doc.is_file():
        cmds.append("to use it before a framework release: docs/adopter-new-model-fast-access.md")
    return cmds


def _prefix_admitter(model_id: str, ws: List[str]) -> Optional[str]:
    for entry in ws:
        if model_id.startswith(entry) and len(model_id) > len(entry) and model_id[len(entry)] == "-":
            return entry
    return None


def _ws_generations(records: List[Dict[str, str]], ws: List[str]) -> Dict[str, List[Tuple[int, ...]]]:
    """family -> generations of its working-set members (catalog family wins)."""
    fam_of = {r["id"]: r["family"] for r in records}
    ws_fam: Dict[str, List[Tuple[int, ...]]] = {}
    for wid in ws:
        fam = fam_of.get(wid) or model_family_gen(wid)[0]
        ws_fam.setdefault(fam, []).append(model_family_gen(wid)[1])
    return ws_fam


def new_model_ids(catalog: Dict[str, Any], ws: List[str],
                  ws_fam: Dict[str, List[Tuple[int, ...]]]) -> List[str]:
    """Catalog ids newer than the working set.

    The harness's own statement first (``latest_per_family``), then every
    record of an ADOPTED family whose generation outranks the working set's
    newest member of that family. Older ids of adopted families are legacy
    and stay silent.
    """
    def newer(mid: str, fam: str) -> bool:
        return fam not in ws_fam or model_family_gen(mid)[1] > max(ws_fam[fam])

    out: List[str] = []
    for fam, latest in sorted(catalog["latest_per_family"].items()):
        if latest not in ws and latest not in out and newer(latest, fam):
            out.append(latest)
    for rec in catalog["records"]:
        rid, fam = rec["id"], rec["family"]
        if rid not in ws and rid not in out and fam in ws_fam and newer(rid, fam):
            out.append(rid)
    return out


def _new_model_findings(catalog: Dict[str, Any], ws: List[str], new_ids: List[str],
                        ws_fam: Dict[str, List[Tuple[int, ...]]], repo: Path) -> List[Dict[str, Any]]:
    fam_of = {r["id"]: r["family"] for r in catalog["records"]}
    names = {r["id"]: r["display_name"] for r in catalog["records"]}
    out: List[Dict[str, Any]] = []
    for nid in new_ids:
        fam = fam_of.get(nid) or model_family_gen(nid)[0]
        admitter = _prefix_admitter(nid, ws)
        adm = (" ; already admitted by the working-set entry {!r} ({})".format(
            admitter, _PREFIX_SEMANTICS_NOTE) if admitter else " ; NOT admitted by any working-set entry")
        if fam in ws_fam:
            kind, what = "MODEL_NEW_IN_HARNESS", "newer than every ADR-149 working-set {} id".format(fam)
        else:
            kind = "MODEL_FAMILY_NEW_IN_HARNESS"
            what = "the harness's latest {!r} — a family with no ADR-149 working-set member".format(fam)
        out.append(_finding(
            "catalog", kind, "drift",
            "installed Claude Code knows {} ({}) — {}{}".format(nid, names.get(nid, "?"), what, adm),
            _new_model_next(repo), {"model_id": nid, "prefix_admitted_by": admitter}))
    return out


def _coverage_findings(catalog: Dict[str, Any], ws: List[str], new_ids: List[str],
                       ws_fam: Dict[str, List[Tuple[int, ...]]], repo: Path) -> List[Dict[str, Any]]:
    """Aliases outside the working set, working-set ids the harness lacks, unadopted families."""
    out: List[Dict[str, Any]] = []
    for alias, target in sorted(catalog["aliases"].items()):
        if target not in ws:
            out.append(_finding(
                "catalog", "MODEL_ALIAS_OUTSIDE_WORKING_SET", "drift",
                "harness alias {!r} resolves to {} — outside the ADR-149 working set".format(alias, target),
                _new_model_next(repo), {"alias": alias, "target": target}))
    ids = [r["id"] for r in catalog["records"]]
    for wid in ws:
        if wid not in ids:
            out.append(_finding(
                "catalog", "WORKING_SET_ID_NOT_IN_HARNESS", "drift",
                "ADR-149 working-set id {} is not in the installed harness catalog "
                "(retired, renamed, or not yet shipped in this Claude Code)".format(wid),
                ["python3 .claude/scripts/check-model-deprecations.py"], {"model_id": wid}))
    unadopted: Dict[str, List[str]] = {}
    for rec in catalog["records"]:
        if rec["family"] not in ws_fam and rec["id"] not in new_ids:
            unadopted.setdefault(rec["family"], []).append(rec["id"])
    for fam, fids in sorted(unadopted.items()):
        out.append(_finding(
            "catalog", "MODEL_FAMILY_NOT_ADOPTED", "info",
            "harness catalog family {!r} has no ADR-149 working-set member: {}".format(
                fam, ", ".join(fids))))
    return out


def classify_catalog(catalog: Dict[str, Any], ws: List[str], repo: Path) -> List[Dict[str, Any]]:
    ws_fam = _ws_generations(catalog["records"], ws)
    new_ids = new_model_ids(catalog, ws, ws_fam)
    return (_new_model_findings(catalog, ws, new_ids, ws_fam, repo)
            + _coverage_findings(catalog, ws, new_ids, ws_fam, repo))


def check_catalog(repo: Path, catalog_path: Optional[str],
                  skip: bool) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    if skip:
        return {"status": "skipped"}, []
    ws, ws_note = load_working_set(repo)
    if ws is None and ws_note == "absent":
        # install.sh ships only .claude/adr/README.md and upgrade.sh has no
        # .claude/adr target — an adopter has no ADR-149 to compare against,
        # so the binary is not even scanned (C-R1-05).
        return ({"status": "not-applicable", "source": None, "working_set": None,
                 "working_set_source": ws_note}, [_finding(
            "catalog", "WORKING_SET_NOT_APPLICABLE", "info",
            "no .claude/adr/ADR-149-model-id-allowlist.md (install and upgrade do not "
            "deliver the framework ADRs) — the catalog comparison does not apply")])
    catalog = scan_catalog(catalog_path)
    comp = {"status": catalog["status"], "source": catalog["source"], "note": catalog["note"],
            "model_count": len(catalog["records"]), "aliases": catalog["aliases"],
            "latest_per_family": catalog["latest_per_family"],
            "working_set": ws, "working_set_source": ws_note}
    if catalog["status"] != "ok":
        return comp, [_finding("catalog", "CATALOG_UNKNOWN", "unknown", catalog["note"])]
    if ws is None:
        return comp, [_finding("catalog", "WORKING_SET_UNKNOWN", "unknown", ws_note)]
    partial: List[Dict[str, Any]] = []
    if not catalog["aliases"] and not catalog["latest_per_family"]:
        # Records parsed but neither block did: the alias check and the
        # harness's own "latest" statement are blind — say so, never "current".
        partial.append(_finding(
            "catalog", "CATALOG_PARTIAL", "unknown",
            "{} model records matched in {} but no aliases / latest_per_family block "
            "followed them (format changed?) — alias coverage not checked".format(
                len(catalog["records"]), catalog["source"])))
    return comp, partial + classify_catalog(catalog, ws, repo)


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------

def build_report(args: argparse.Namespace, now: _dt.datetime) -> Dict[str, Any]:
    explicit = args.repo_root is not None
    repo = Path(os.path.abspath(args.repo_root)) if explicit else DEFAULT_REPO_ROOT
    probe = not args.no_probe
    cache_path = (Path(args.cache_dir) / _CACHE_NAME if args.cache_dir
                  else default_cache_path(repo, str(repo) if explicit else None))
    fetch_note = "not requested (offline)"
    fetch_findings: List[Dict[str, Any]] = []
    if args.fetch:
        if cache_path is None:
            ok, fetch_note = False, "cache path unresolvable (runtime_paths unavailable)"
        else:
            ok, fetch_note = fetch_dist_tags(_resolve_bin(args.npm_bin, "npm"), cache_path, now)
        if not ok:
            fetch_findings.append(_finding("codex", "CODEX_FETCH_FAILED", "unknown", fetch_note))
    cache, cache_note = load_cache(cache_path)
    codex_comp, codex_f = check_codex(repo, _resolve_bin(args.codex_bin, "codex"), probe,
                                      cache, cache_note, now, args.max_cache_age_days)
    codex_comp["cache"] = {"path": str(cache_path) if cache_path else None,
                           "note": cache_note, "fetch": fetch_note}
    claude_bin = _resolve_bin(args.claude_bin, "claude")
    if probe:
        applicable = bool(args.ledger) or is_framework_checkout(repo)
        cc_ver, cc_note = (probe_version(claude_bin, "claude") if applicable
                           else (None, "not probed (ledger comparison not applicable)"))
        cc_comp, cc_f = check_claude_code(
            cc_ver, cc_note,
            Path(args.ledger) if args.ledger else repo / ".claude" / "scripts" / "substrate-watch.json",
            applicable=applicable)
    else:
        cc_comp, cc_f = {"installed": None, "probe_note": "not probed (--no-probe)"}, []
    cat_comp, cat_f = check_catalog(repo, args.catalog_file or claude_bin, args.skip_catalog)
    findings = fetch_findings + codex_f + cc_f + cat_f
    sev = [f["severity"] for f in findings]
    status = "drift" if "drift" in sev else ("unknown" if "unknown" in sev else "current")
    return {"schema": SCHEMA, "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "repo_root": str(repo), "status": status,
            "counts": {s: sev.count(s) for s in ("drift", "info", "unknown")},
            "components": {"codex": codex_comp, "claude_code": cc_comp, "catalog": cat_comp},
            "findings": findings}


def render_text(report: Dict[str, Any]) -> str:
    c = report["counts"]
    lines = ["substrate-drift: {} ({} drift, {} info, {} unknown)".format(
        report["status"].upper(), c["drift"], c["info"], c["unknown"])]
    codex = report["components"]["codex"]
    pin = codex.get("pin") or {}
    lines.append("[codex] installed {} | pinned {} | range {} | {}".format(
        codex.get("installed") or "?", pin.get("package_version") or "?", pin.get("range") or "?",
        _CODEX_VERSION_ONLY))
    cc = report["components"]["claude_code"]
    lines.append("[claude_code] installed {} | ledger last_seen {}".format(
        cc.get("installed") or "?", cc.get("ledger_last_seen") or "?"))
    cat = report["components"]["catalog"]
    if cat.get("status") == "ok":
        ws_ids = cat.get("working_set")  # None = unreadable, never "0 ids"
        lines.append("[catalog] {} models in {} | working set {} ids".format(
            cat["model_count"], cat["source"], len(ws_ids) if ws_ids is not None else "?"))
    else:
        lines.append("[catalog] {}".format(cat.get("status")))
    for f in report["findings"]:
        lines.append("  {} [{}] {}: {}".format(
            f["severity"].upper(), f["component"], f["kind"], f["claim"]))
        for cmd in f["next"]:
            lines.append("      next: {}".format(cmd))
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Offline substrate drift detector "
                                "(codex pin, Claude Code ledger, model catalog).")
    p.add_argument("--repo-root", help="repository root (default: the checkout holding this script)")
    p.add_argument("--json", action="store_true", dest="as_json")
    p.add_argument("--strict", action="store_true", help="exit 1 on any drift finding")
    p.add_argument("--fetch", action="store_true",
                   help="opt-in network: npm view @openai/codex dist-tags, cached")
    p.add_argument("--no-probe", action="store_true",
                   help="do not read the installed codex version nor run claude --version")
    p.add_argument("--skip-catalog", action="store_true")
    p.add_argument("--codex-bin")
    p.add_argument("--claude-bin")
    p.add_argument("--npm-bin")
    p.add_argument("--catalog-file", help="scan this file instead of the resolved claude binary")
    p.add_argument("--ledger", help="substrate-watch.json override")
    p.add_argument("--cache-dir", help="dist-tags cache dir override")
    p.add_argument("--max-cache-age-days", type=int, default=_CACHE_STALE_DAYS_DEFAULT)
    args = p.parse_args(argv)
    # The resolver and the ADR-149 parser are imported at run time: keep the
    # "writes nothing but the --fetch cache" promise — no __pycache__ either.
    sys.dont_write_bytecode = True
    now = _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None, microsecond=0)
    try:
        report = build_report(args, now)
    except Exception as exc:  # noqa: BLE001 — infra fail-open, but NAMED
        report = {"schema": SCHEMA, "status": "unknown", "counts": {"drift": 0, "info": 0, "unknown": 1},
                  "components": {}, "findings": [_finding(
                      "detector", "DETECTOR_ERROR", "unknown",
                      "{}: {}".format(type(exc).__name__, exc))]}
        sys.stdout.write(json.dumps(report, indent=2) + "\n" if args.as_json else
                         "substrate-drift: UNKNOWN (detector error: {}: {})\n".format(
                             type(exc).__name__, exc))
        return 0
    if args.as_json:
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=False) + "\n")
    else:
        sys.stdout.write(render_text(report) + "\n")
    if args.strict and report["counts"]["drift"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
