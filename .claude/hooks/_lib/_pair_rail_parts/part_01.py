from __future__ import annotations
from ._shared import *
from _lib import cli_currency as _cli_currency

_PRODUCTION_PROMOTED_BY_PLAN_091: bool = True

_L3_PLUS_GLOB_PATTERNS: Tuple[str, ...] = (
    ".claude/hooks/_lib/*.py",
    ".claude/hooks/_lib/**/*.py",
    ".claude/hooks/check_*.py",
    ".claude/hooks/audit_*.py",
    ".claude/scripts/local/*",
    ".claude/policies/*.yaml",
    ".claude/policies/*.yml",
    "SPEC/v1/*.md",
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    "PROTOCOL.md",
)

def _fnmatch_segments(path: str, pattern: str) -> bool:
    """Segment-wise glob matcher with `*` (one segment) and `**` (zero+).

    Stripped-down port of `check_canonical_edit._fnmatch_segments`.
    """
    import fnmatch as _fn

    p_parts = path.split("/")
    pat_parts = pattern.split("/")

    def _match(p: List[str], pat: List[str]) -> bool:
        if not pat:
            return not p
        head, rest = pat[0], pat[1:]
        if head == "**":
            for i in range(len(p) + 1):
                if _match(p[i:], rest):
                    return True
            return False
        if not p:
            return False
        if head == "*" or _fn.fnmatchcase(p[0], head):
            return _match(p[1:], rest)
        return False

    return _match(p_parts, pat_parts)

def _is_l3_plus_path(path_str: str, repo_root: Path) -> bool:
    """True if path classifies as L3+ per the production heuristic."""
    if not path_str:
        return False
    p = Path(path_str)
    try:
        rel_path = (
            p.resolve().relative_to(repo_root.resolve())
            if p.is_absolute()
            else Path(path_str)
        )
    except (ValueError, OSError):
        # Path outside repo or non-resolvable — not L3+.
        return False
    rel_str = str(rel_path).replace(os.sep, "/")
    for pattern in _L3_PLUS_GLOB_PATTERNS:
        if _fnmatch_segments(rel_str, pattern):
            return True
    return False

_CODEX_PATCH_RE = re.compile(
    r"^\*\*\*\s+(Update|Add|Delete|Move|Rename)\s+File:?\s+(.+?)\s*$",
    re.MULTILINE,
)

_CODEX_MOVE_RE = re.compile(
    r"^\*\*\*\s+(?:Move|Rename)\s+to:?\s+(.+?)\s*$",
    re.MULTILINE,
)

_UNIFIED_DIFF_RE = re.compile(
    r"^(?:---|\+\+\+)\s+(?:[ab]/)?(.+?)\s*$", re.MULTILINE,
)

_JSON_PATCH_PATH_RE = re.compile(
    r'"path"\s*:\s*"(/[^"\\]*(?:\\.[^"\\]*)*)"'
)

_MAX_RESPONSE_BYTES = 4 * 1024 * 1024  # 4 MiB

_MAX_RESPONSE_LINES = 200_000

_MAX_OUTPUT_FILE_BYTES: int = 1 * 1024 * 1024  # 1 MiB

def _detect_write_shaped_patch(response_text: str) -> Optional[str]:
    """Detect any write-shaped patch in a Codex review response.

    Returns the matched grammar tag (`codex_apply_patch`, `unified_diff`,
    `codex_move`, `json_patch`) on first detection, or None if response
    is clean. Order is: Codex envelope → unified diff → JSON patch.

    Defense:
    - Length cap (4 MiB) — pathological responses skipped (treated as
      clean by production heuristic; future revision should fail-CLOSED).
    - Line cap (200k) — bound regex iteration.
    - All regexes anchored with `^...$` (multiline) — no nested
      quantifiers susceptible to ReDoS.
    """
    if not isinstance(response_text, str) or not response_text:
        return None
    if len(response_text) > _MAX_RESPONSE_BYTES:
        # Spike: treat oversize as clean (advisory). Production note:
        # ADR-110 PROPOSED Phase 1 should fail-CLOSED here.
        return None
    # Cap line count via early exit on findall-like inspection.
    line_count = response_text.count("\n")
    if line_count > _MAX_RESPONSE_LINES:
        return None

    # Grammar 1a: Codex apply_patch envelope.
    if _CODEX_PATCH_RE.search(response_text) is not None:
        return "codex_apply_patch"

    # Grammar 1b: Codex move directive.
    if _CODEX_MOVE_RE.search(response_text) is not None:
        return "codex_move"

    # Grammar 2: Unified diff. Filter false positives from prose by
    # requiring the second-half marker to also exist (`---` AND `+++`).
    has_minus = re.search(r"^---\s+", response_text, re.MULTILINE) is not None
    has_plus = re.search(r"^\+\+\+\s+", response_text, re.MULTILINE) is not None
    if has_minus and has_plus:
        return "unified_diff"

    # Grammar 3: JSON Patch (RFC 6902). Two-pass:
    # (a) JSON-shape body — try strict json.loads.
    stripped = response_text.lstrip()
    if stripped.startswith(("[", "{")):
        try:
            parsed = json.loads(response_text)
        except (ValueError, TypeError):
            parsed = None
        if isinstance(parsed, list):
            for op in parsed:
                if (
                    isinstance(op, dict)
                    and isinstance(op.get("op"), str)
                    and isinstance(op.get("path"), str)
                    and op["path"].startswith("/")
                    and op["op"] in {"add", "remove", "replace", "move", "copy"}
                ):
                    return "json_patch"
        elif isinstance(parsed, dict):
            # Single op object (uncommon but valid).
            if (
                isinstance(parsed.get("op"), str)
                and isinstance(parsed.get("path"), str)
                and parsed["path"].startswith("/")
                and parsed["op"] in {"add", "remove", "replace", "move", "copy"}
            ):
                return "json_patch"
    # (b) Legacy regex fallback for embedded JSON-Patch fragments in
    # mixed prose.
    if (
        '"op"' in response_text
        and '"path"' in response_text
        and _JSON_PATCH_PATH_RE.search(response_text) is not None
    ):
        return "json_patch"

    return None

class CodexUnavailable(Exception):
    """Raised when Codex binary is missing or invoke fails non-recoverably."""

class CodexTimeout(Exception):
    """Raised when Codex exceeds the wall-clock cap (CEO_PAIR_RAIL_TIMEOUT_S)."""

class CodexMalformed(Exception):
    """Raised when Codex stdout cannot be parsed as a valid review envelope."""

class CodexPinMismatch(Exception):
    """ADR-182 fail-CLOSED: payload-pin verification failed on a SECURITY
    input (targetTriple absent from the manifest, malformed manifest
    entry, or SHA-256 mismatch between the resolved native payload and
    its pinned entry). The consumer (`_decide`) maps this to
    `{decision: block}` — the unverified binary is never invoked and the
    L3+ write does not proceed under a silently-degraded rail."""

_PIN_MANIFEST_REL: Tuple[str, ...] = (
    ".claude", "governance", "codex-cli-pin-manifest.json",
)

_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")

def _codex_target_triple() -> Optional[str]:
    """Derive the launcher's targetTriple for this host, or None.

    Mirrors `bin/codex.js` (`process.platform`/`process.arch` mapping,
    transcribed in PLAN-163 `probes/payload-sha-evidence.md`). Windows
    payloads carry a `.exe` suffix handled in `_resolve_codex_payload`.

    H1 fail-CLOSED test seam: `CEO_PAIR_RAIL_TARGET_TRIPLE` overrides the
    derivation ONLY under the explicit `CEO_PAIR_RAIL_TEST_MODE=1` marker.
    On the LIVE path (no marker) the override is IGNORED and the triple is
    derived from the real host, so no CODEX-specific seam can point
    verification at a foreign per-triple manifest entry. The
    derived-or-overridden triple is still VERIFIED downstream — this seam
    never relaxes the sha comparison. (Scope, PLAN-163 DIM1: this "no env"
    claim covers CODEX-specific seams only; the manifest BASE follows the
    framework-wide `CLAUDE_PROJECT_DIR` anchor — see `_pin_manifest_path`.)
    """
    if os.environ.get("CEO_PAIR_RAIL_TEST_MODE") == "1":
        override = os.environ.get("CEO_PAIR_RAIL_TARGET_TRIPLE")
        if override:
            return override
    try:
        import platform as _platform
        sysname = _platform.system()
        machine = _platform.machine().lower()
    except Exception:
        return None
    arm = machine in ("arm64", "aarch64")
    x64 = machine in ("x86_64", "amd64")
    if sysname == "Darwin":
        if arm:
            return "aarch64-apple-darwin"
        if x64:
            return "x86_64-apple-darwin"
    elif sysname == "Linux":
        if x64:
            return "x86_64-unknown-linux-musl"
        if arm:
            return "aarch64-unknown-linux-musl"
    elif sysname == "Windows":
        if x64:
            return "x86_64-pc-windows-msvc"
        if arm:
            return "aarch64-pc-windows-msvc"
    return None

def _pin_manifest_path() -> Path:
    """Resolve the ADR-182 manifest path (test seam → repo default).

    H1 fail-CLOSED: the `CEO_PAIR_RAIL_PIN_MANIFEST` override is a TEST
    seam honoured ONLY under `CEO_PAIR_RAIL_TEST_MODE=1`. On the LIVE path
    the override is IGNORED and the manifest base resolves under the
    framework-wide `CLAUDE_PROJECT_DIR` anchor. The seam never relaxes the
    sha comparison — a test manifest is still matched byte-for-byte against
    the resolved payload.

    Scope (PLAN-163 DIM1): the guarantee "no env redirects verification at
    an attacker-supplied manifest" is scoped to CODEX-SPECIFIC seams. The
    base still follows `CLAUDE_PROJECT_DIR` — the framework-wide anchor
    every hook already trusts — so an attacker who can repoint that anchor
    has already compromised the entire tree, which is OUTSIDE this pin's
    threat model. The pin defends T-8 (a payload swap under an
    otherwise-intact environment), not a hostile framework anchor.
    """
    if os.environ.get("CEO_PAIR_RAIL_TEST_MODE") == "1":
        override = os.environ.get("CEO_PAIR_RAIL_PIN_MANIFEST")
        if override:
            return Path(override)
    repo_root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    return repo_root.joinpath(*_PIN_MANIFEST_REL)

class CodexPinManifestMalformed(Exception):
    """Fail-CLOSED signal (PLAN-163 C2 fix): the pin manifest is PRESENT
    but not parseable as a valid manifest — a broken-JSON body, non-utf8
    bytes, a top-level that is not an object / carries ``schema != 1``, or
    a ``payloads`` value that is not an object. Per the PLAN-152 debate-C4
    fail-CLOSED-on-input doctrine, content a security matcher cannot parse
    is BLOCKED, never waved through as an INFRA advisory. Distinct from a
    genuinely ABSENT / unreadable manifest (OSError — content not present),
    which stays INFRA -> fail-open. ``verify_codex_payload`` catches this
    and maps it to ``status='mismatch'`` (-> ``CodexPinMismatch`` -> BLOCK).
    """

def _load_pin_manifest(path: Path) -> Optional[Dict[str, Any]]:
    """Parse the pin manifest, separating the two failure CLASSES the
    fail-CLOSED-on-input doctrine (PLAN-152 debate C4) requires:

    * Manifest ABSENT / unreadable — the content is NOT present. Any
      ``OSError`` from the read (``FileNotFoundError``, ``PermissionError``,
      ``IsADirectoryError``, ...) -> return ``None`` -> the caller
      classifies it INFRA -> fail-OPEN advisory (same doctrine as a missing
      binary).
    * Manifest PRESENT but NOT parseable as a valid manifest — a
      ``json.JSONDecodeError`` (subclass of ``ValueError``), non-utf8 bytes
      (``UnicodeDecodeError`` — also a ``ValueError``), a top-level that is
      not an object / has ``schema != 1``, or a non-object ``payloads`` ->
      raise ``CodexPinManifestMalformed`` -> the caller fail-CLOSES to
      ``status='mismatch'`` (BLOCK). A swapped / corrupt manifest must not
      silently degrade the rail to advisory (that silent degrade is the
      exact 0.144.1->0.144.6 no-gate-trip failure ADR-182 closes).

    The two classes are NEVER conflated: an ``OSError`` is not a parse
    failure, and a parse failure is not an ``OSError``.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        # Content NOT present / unreadable -> INFRA -> advisory.
        return None
    except ValueError as e:
        # UnicodeDecodeError IS-A ValueError: the bytes ARE present but are
        # not decodable as utf-8 -> content-present-not-parseable ->
        # fail-CLOSED.
        raise CodexPinManifestMalformed(
            "pin manifest not utf-8: " + type(e).__name__
        )
    try:
        data = json.loads(raw)
    except Exception as e:
        # C2 (codex R4): the bytes ARE present (read_text OSError is handled
        # above as INFRA). ANY failure parsing present bytes — json.JSONDecodeError
        # (IS-A ValueError), or a non-ValueError parser failure such as
        # RecursionError on a deeply-nested payload — is present-but-unparseable
        # security-matcher input -> fail-CLOSED (CLAUDE.md §4). A narrow
        # `except ValueError` let RecursionError escape to the caller's broad
        # infra/advisory catch-all; catch-all here keeps the block.
        raise CodexPinManifestMalformed(
            "pin manifest unparseable: " + type(e).__name__
        )
    if not isinstance(data, dict) or data.get("schema") != 1:
        raise CodexPinManifestMalformed(
            "pin manifest top-level invalid (not an object or schema != 1)"
        )
    if not isinstance(data.get("payloads"), dict):
        raise CodexPinManifestMalformed(
            "pin manifest 'payloads' is not an object"
        )
    return data

def _sha256_file(path: Path) -> Optional[str]:
    """SHA-256 hex of a file (chunked; payload is ~260 MB). None on IO error."""
    import hashlib
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None

def _resolve_codex_payload(
    launcher: Path, manifest_rel_path: str, triple: str
) -> Optional[Path]:
    """Mirror the launcher's `findCodexExecutable()` payload resolution.

    `launcher` is the `codex` entry found on $PATH (an npm symlink).
    Candidates, in launcher order:
      1. `require.resolve("@openai/codex-<platform>/package.json")` —
         node walks `node_modules/` up from the launcher package dir;
         we walk the same ancestors joining `node_modules/<manifest
         entry path>` (the manifest `path` field IS the
         package-relative payload path, e.g.
         `@openai/codex-darwin-arm64/vendor/<triple>/bin/codex`).
      2. Launcher fallback `__dirname/../vendor/<triple>/bin/codex`
         (i.e. `<pkg_dir>/vendor/...`).
    Returns the first existing regular file, else None (INFRA).
    """
    try:
        real = launcher.resolve()
    except (OSError, RuntimeError):
        return None
    pkg_dir = real.parent.parent  # <pkg>/bin/codex.js → <pkg>
    rel_parts = [p for p in manifest_rel_path.split("/") if p]
    if not rel_parts:
        return None
    exe_suffix = ".exe" if os.name == "nt" else ""
    candidates: List[Path] = []
    for anc in [pkg_dir] + list(pkg_dir.parents):
        candidates.append(anc.joinpath("node_modules", *rel_parts))
    candidates.append(pkg_dir / "vendor" / triple / "bin" / "codex")
    for cand in candidates:
        if exe_suffix and cand.suffix != exe_suffix:
            cand = cand.with_name(cand.name + exe_suffix)
        try:
            if cand.is_file():
                return cand
        except OSError:
            continue
    return None

# QDSAA-FUNCAO-LONGA: preserva numa transação a classificação fail-open/fail-closed do pin, detalhes forenses e contrato CLI.
def verify_codex_payload(
    launcher: Optional[str] = None,
    *,
    payload_override: Optional[str] = None,
) -> Dict[str, Any]:
    """ADR-182 verification kernel — shared by this hook's runtime
    verify-then-invoke path, `pair-rail-gate.sh` Gate 4 (via the
    `--verify-codex-pin` CLI below), and tests. NEVER raises.

    Two ingress shapes, ONE verification (H1 fail-CLOSED single code
    path — no env is a sha-check bypass):

      * ``payload_override`` set (the `CEO_PAIR_RAIL_CODEX_BIN` seam) —
        the override IS the native payload. Its sha256 is hashed
        DIRECTLY and compared against the manifest entry for the current
        triple. A set-but-missing / non-regular override is a fail-CLOSED
        ``mismatch`` ("inexistente = BLOQUEIA"), never a silent advisory
        degrade: a hostile override must not be able to relax the rail by
        pointing at a vanished path.
      * ``launcher`` given / discovered on $PATH — mirror the launcher's
        `findCodexExecutable()` to resolve the native payload, then hash
        + compare it.

    In BOTH shapes the resolved payload's sha256 is compared against the
    per-triple pin-manifest entry. No env relaxes this comparison.

    Returns a dict:
      status        — "verified" | "mismatch" | "triple_missing" | "infra"
      detail        — machine-readable slug for the specific arm
      path          — resolved native payload path ("" until resolved)
      sha256        — computed payload sha256 ("" until computed)
      expected_sha256 — manifest entry sha256 ("" if no entry)
      target_triple — derived/overridden triple ("" if underivable)
      manifest      — manifest path consulted

    Classification contract (docstring §ADR-182): "infra" arms are
    fail-OPEN at the consumer; "mismatch"/"triple_missing" arms are
    fail-CLOSED (`CodexPinMismatch`). An underivable host triple is
    classified `triple_missing` — a host we cannot map cannot be
    verified, and unverifiable must not silently degrade to advisory.
    """
    manifest_path = _pin_manifest_path()
    result: Dict[str, Any] = {
        "status": "infra",
        "detail": "",
        "path": "",
        "sha256": "",
        "expected_sha256": "",
        "installed_version": "",
        "target_triple": "",
        "manifest": str(manifest_path),
    }
    try:
        # Ingress-shape resolution of the LAUNCHER (needed only when no
        # direct payload override was supplied). The override path does
        # NOT resolve via a launcher — it is hashed directly below.
        launcher_path: Optional[Path] = None
        if payload_override is None:
            launcher_path = Path(launcher) if launcher else None
            if launcher_path is None:
                for entry_dir in os.environ.get("PATH", "").split(os.pathsep):
                    candidate = Path(entry_dir) / "codex"
                    if candidate.exists() and os.access(candidate, os.X_OK):
                        launcher_path = candidate
                        break
            if launcher_path is None or not launcher_path.exists():
                result["detail"] = "launcher_not_found"
                return result

        triple = _codex_target_triple()
        if triple is None:
            result["status"] = "triple_missing"
            result["detail"] = "target_triple_underivable"
            return result
        result["target_triple"] = triple

        try:
            manifest = _load_pin_manifest(manifest_path)
        except CodexPinManifestMalformed:
            # PRESENT-but-unparseable manifest = INPUT-parse failure of a
            # security matcher -> fail-CLOSED (PLAN-152 debate C4). A
            # corrupt/swapped manifest must not silently degrade the rail
            # to advisory. status='mismatch' -> CodexPinMismatch -> BLOCK.
            result["status"] = "mismatch"
            result["detail"] = "manifest_malformed"
            return result
        if manifest is None:
            # ABSENT / unreadable (OSError) -> INFRA -> fail-OPEN advisory,
            # same doctrine as a missing binary.
            result["detail"] = "manifest_unreadable"
            return result

        entry = manifest["payloads"].get(triple)
        if entry is None:
            currency_path = Path(payload_override) if payload_override else launcher_path
            if currency_path and _apply_currency_policy(
                currency_path, launcher_path, manifest, result
            ):
                return result
            result["status"] = "triple_missing"
            result["detail"] = "triple_absent_from_manifest"
            return result
        if not isinstance(entry, dict):
            result["status"] = "mismatch"
            result["detail"] = "manifest_entry_malformed"
            return result
        expected = entry.get("sha256")
        rel_path = entry.get("path")
        if (
            not isinstance(expected, str)
            or _SHA256_HEX_RE.match(expected) is None
            or not isinstance(rel_path, str)
            or not rel_path
        ):
            # Malformed SECURITY input inside the matcher → fail-CLOSED
            # (PLAN-152 debate C4 doctrine), never waved through.
            result["status"] = "mismatch"
            result["detail"] = "manifest_entry_malformed"
            return result
        result["expected_sha256"] = expected

        if payload_override is not None:
            # H1: the override is VERIFIED, never trusted un-hashed. A
            # set-but-absent / non-regular override is a fail-CLOSED
            # ``mismatch`` (BLOCK), NOT an INFRA advisory — a hostile
            # override must not degrade the rail by pointing at a vanished
            # path. The launcher indirection is skipped: the override IS
            # the payload we hash and compare.
            payload: Optional[Path] = Path(payload_override)
            try:
                is_regular = payload.is_file()
            except OSError:
                is_regular = False
            if not is_regular:
                result["status"] = "mismatch"
                result["detail"] = "override_payload_missing"
                return result
        else:
            payload = _resolve_codex_payload(launcher_path, rel_path, triple)
            if payload is None:
                # The launcher itself would throw "Missing optional
                # dependency" here — codex cannot run at all → INFRA.
                result["detail"] = "payload_not_resolved"
                return result
        result["path"] = str(payload)

        actual = _sha256_file(payload)
        if actual is None:
            result["detail"] = "payload_unreadable"
            return result
        result["sha256"] = actual

        if actual != expected:
            if _apply_currency_policy(payload, launcher_path, manifest, result):
                return result
            result["status"] = "mismatch"
            result["detail"] = "payload_sha256_mismatch"
            return result

        result["status"] = "verified"
        result["detail"] = "ok"
        return result
    except Exception as e:  # defensive: kernel never raises
        result["status"] = "infra"
        result["detail"] = f"unexpected:{type(e).__name__}"
        return result


def _apply_currency_policy(
    payload: Path, launcher: Optional[Path], manifest: Dict[str, Any], result: Dict[str, Any],
) -> bool:
    """Record qualified version and apply only the explicitly allowed currency arm."""
    installed = _cli_currency.qualified_package_version(payload, launcher)
    result["installed_version"] = installed or ""
    if installed is None:
        return False
    manifest_version = manifest.get("package_version")
    if _cli_currency.parse_semver(manifest_version) is None:
        result["status"] = "mismatch"
        result["detail"] = "manifest_package_version_malformed"
        return True
    if _cli_currency.compatible_package_version(payload, launcher, manifest_version):
        result["status"] = "compatible"
        result["detail"] = "version_floor_only"
        result["path"] = str(payload)
        return True
    return False


def _resolve_codex_bin() -> Optional[str]:
    """Return verified or floor-compatible native payload; infra is None."""
    override = os.environ.get("CEO_PAIR_RAIL_CODEX_BIN")
    res = (
        verify_codex_payload(payload_override=override)
        if override
        else verify_codex_payload()
    )
    status = res.get("status")
    if status in ("verified", "compatible"):
        return str(res.get("path") or "") or None
    if status == "infra":
        return None
    raise CodexPinMismatch(
        f"{status}:{res.get('detail')} triple={res.get('target_triple') or '?'} "
        f"payload_sha={str(res.get('sha256'))[:16] or '?'} "
        f"pin_sha={str(res.get('expected_sha256'))[:16] or '?'} "
        f"manifest={res.get('manifest')}"
    )

def _build_codex_prompt(
    tool_name: str, file_path: str, proposed_content: str
) -> str:
    """Build the read-only review prompt sent to Codex.

    Production contract: prompt asks Codex to review for governance issues
    + return REVIEW-ONLY. ANY `*** Update File:` / unified diff /
    JSON-Patch in the response → automatic violation (regardless of
    intent — the hook contract is purely structural).
    """
    # Truncate proposed_content for prompt size sanity. Phase 1 will
    # use chunked streaming; spike caps at 32 KiB.
    capped = proposed_content[:32 * 1024] if proposed_content else ""
    return (
        f"PAIR-RAIL READ-ONLY REVIEW (PLAN-075 Phase 0A spike)\n\n"
        f"Tool: {tool_name}\n"
        f"Target path: {file_path}\n\n"
        "You are a READ-ONLY reviewer. Do NOT emit any patch, diff, "
        "apply_patch envelope, or JSON-Patch op.\n"
        "If you would change the file, describe the change in PROSE "
        "ONLY (no code-fenced patches, no `*** Update File:` lines, "
        "no `--- a/...` / `+++ b/...` markers).\n\n"
        f"Proposed content (truncated to 32 KiB):\n```\n{capped}\n```"
    )

__all__ = (
    '_PRODUCTION_PROMOTED_BY_PLAN_091',
    '_L3_PLUS_GLOB_PATTERNS',
    '_fnmatch_segments',
    '_is_l3_plus_path',
    '_CODEX_PATCH_RE',
    '_CODEX_MOVE_RE',
    '_UNIFIED_DIFF_RE',
    '_JSON_PATCH_PATH_RE',
    '_MAX_RESPONSE_BYTES',
    '_MAX_RESPONSE_LINES',
    '_MAX_OUTPUT_FILE_BYTES',
    '_detect_write_shaped_patch',
    'CodexUnavailable',
    'CodexTimeout',
    'CodexMalformed',
    'CodexPinMismatch',
    '_PIN_MANIFEST_REL',
    '_SHA256_HEX_RE',
    '_codex_target_triple',
    '_pin_manifest_path',
    'CodexPinManifestMalformed',
    '_load_pin_manifest',
    '_sha256_file',
    '_resolve_codex_payload',
    '_apply_currency_policy',
    'verify_codex_payload',
    '_resolve_codex_bin',
    '_build_codex_prompt',
)
