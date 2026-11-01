"""Sentinel scope, signature caches and unlock provenance.

Functions are bound to the owning hook namespace by ``bind``. This keeps
its injectable dependencies and per-import state on the public hook.
"""
from __future__ import annotations

__all__ = ('_parse_scope_paths_from_text', '_sentinel_cache_disabled', '_compute_sentinel_cache_key', '_file_digest', '_compute_sig_cache_key', 'sentinel_cache_stats', '_verify_signature_rail', '_signature_rail_ok', '_repo_root_for_sentinels', '_reset_unlock_trust_diag', '_note_unlock_trust_diag', '_git_anchor_timeout', '_anchored_blob_text', '_pinned_sentinel_digests', '_unlock_trusted_text', '_unlock_trust_hint', '_sentinel_grants_path')


def _parse_scope_paths_from_text(scope_text: str) -> "Set[str]":
    """Extract declared canonical paths from a Scope block.

    PLAN-064 Option D — extracted helper used by both Tier-1 (marker
    region) and Tier-2 (legacy `_SCOPE_HEADER_RE`) parser paths.

    The Scope block extends from the `Scope` header line to the first
    top-level continuation header (Effective:, Plans:, Rationale,
    Authorization source:, Anchor commit:, a re-encountered
    `Approved-By:`) or markdown horizontal rule (---, ***, ___) or
    end-of-text. Sub-headers within Scope (lines ending with `:` that
    are NOT in the terminator set) are silently skipped.
    """
    import os as _os
    declared_paths: Set[str] = set()
    scope_header = _SCOPE_HEADER_RE.search(scope_text)
    if not scope_header:
        return declared_paths
    post = scope_text[scope_header.end():]
    for line in post.splitlines():
        if _SCOPE_TERMINATOR_RE.match(line) or _SCOPE_HR_RE.match(line):
            break
        m = re.match(r"\s*-\s*(\S+)", line)
        if not m:
            # Blank line or sub-header (e.g. "Hook code (PLAN-052):") —
            # keep collecting; only the explicit terminators stop us.
            continue
        raw = m.group(1)
        # PLAN-024 F-sec-003 P1 fix: reject any control-char in scope
        # entries (bidi, null, ANSI escape, etc.) before normalization.
        if any(ord(c) < 0x20 for c in raw):
            continue
        # Normalize `./foo/bar` -> `foo/bar` and strip any ending
        # separator so sentinel-declared paths match target_rel
        # resolution consistently.
        normalized = _os.path.normpath(raw).replace(_os.sep, "/")
        if normalized == ".":
            continue
        declared_paths.add(normalized)
    return declared_paths



def _sentinel_cache_disabled() -> bool:
    """Kill-switch CEO_SENTINEL_SESSION_CACHE_DISABLED=1 bypasses cache."""
    return os.environ.get("CEO_SENTINEL_SESSION_CACHE_DISABLED", "") == "1"



def _compute_sentinel_cache_key(
    sentinel_path: Path,
    target_rel: str = "",
) -> Optional[Tuple[str, int, int, int, str, str, int]]:
    """Return composite key or None on stat/read failure (don't cache errors).

    iter-1 P0 fix: target_rel included so cache value (grant decision
    dependent on target_rel) is correct on hit.
    """
    try:
        st = sentinel_path.stat()
        content = sentinel_path.read_bytes()
    except OSError:
        return None
    return (
        str(sentinel_path),
        st.st_ino,
        st.st_mtime_ns,
        st.st_size,
        hashlib.sha256(content).hexdigest(),
        target_rel,
        _SENTINEL_CACHE_FORMAT_VERSION,
    )



def _file_digest(path: Optional[Path]) -> str:
    """sha256 of a file's bytes, or a stable marker when unreadable.

    PLAN162_FIX_1 helper. ``"-"`` distinguishes "no such file" from any
    real digest, so a signer allowlist APPEARING (or vanishing) changes
    the signature cache key just like editing it does.
    """
    if path is None:
        return "-"
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return "-"



def _compute_sig_cache_key(sentinel_path: Path) -> Optional[tuple]:
    """Target-FREE key over everything the SIGNATURE decision depends on.

    PLAN162_FIX_1 (#1 partition + #10 staleness). Covers the sentinel's
    own identity/bytes AND the three signing-material inputs — the
    detached ``.asc``, the legacy signer allowlist, and the ADR-121 YAML
    registry — plus the PATH of the latter two (they are module-level
    seams; a different file is a different decision).

    Returns ``None`` on stat/read failure of the sentinel itself, which
    means "do not cache" — errors are never memoized.
    """
    try:
        st = sentinel_path.stat()
        content = sentinel_path.read_bytes()
    except OSError:
        return None
    sig_path = sentinel_path.with_name(sentinel_path.name + ".asc")
    return (
        str(sentinel_path),
        st.st_ino,
        st.st_mtime_ns,
        st.st_size,
        hashlib.sha256(content).hexdigest(),
        _file_digest(sig_path),
        str(_SENTINEL_SIGNERS_FILE),
        _file_digest(_SENTINEL_SIGNERS_FILE),
        str(_SENTINEL_SIGNERS_REGISTRY_YAML),
        _file_digest(_SENTINEL_SIGNERS_REGISTRY_YAML),
        _SIG_CACHE_FORMAT_VERSION,
    )



def sentinel_cache_stats() -> Dict[str, int]:
    """Return session-scoped cache counters (skill_cache_stats sibling)."""
    return {
        "hit_count": _SENTINEL_CACHE_HITS,
        "miss_count": _SENTINEL_CACHE_MISSES,
        "size": len(_SENTINEL_VERIFY_CACHE),
    }



def _verify_signature_rail(sentinel_path: Path) -> bool:
    """The full detached-GPG + dual signer-registry rail for ONE sentinel.

    Extracted verbatim from ``_sentinel_grants_path`` (PLAN162_FIX_1) so
    the decision it produces — which is INDEPENDENT of the edit target —
    can be cached target-free. Behaviour is unchanged: fail-CLOSED on a
    missing helper, bad signature, unlisted fingerprint, bootstrap-SHA
    mismatch, or (post-GENESIS) a registry parse failure.
    """
    if _gpg_verify is None:
        # _lib.gpg_verify is unavailable — fail-CLOSED. No sentinel
        # can grant canonical edits without the verification helper.
        return False
    sig_path = sentinel_path.with_name(sentinel_path.name + ".asc")
    # PLAN-089 Wave C.4 — dual-rail signer verification (ADR-121).
    # First-class path: legacy `.claude/sentinel-signers.txt` (existing).
    # Defense-in-depth: if YAML registry exists, re-check fingerprint via
    # _lib.sentinel_signers + bootstrap-SHA pin. Either rail rejecting
    # → fail-CLOSED. Post-GENESIS (_BOOTSTRAP_REGISTRY_SHA256 set),
    # parse/hash failure → fail-CLOSED (R2 Codex iter-1 Q5+Q7 fold);
    # pre-GENESIS (None), parse failure → legacy-only fallback.
    # PLAN162_FIX_1 (Codex P1 fold) — the subprocess is bounded by what is
    # LEFT of the invocation budget, minus the margin needed to still emit
    # a decision. ``None`` => not enough budget to verify AND emit: refuse
    # the spawn and latch, so the caller's next deadline poll produces the
    # fail-closed wall-deadline block instead of a harness kill.
    _timeout = _gpg_verify_timeout()
    if _timeout is None:
        _mark_wall_budget_exhausted()
        return False
    ok, _fpr, _reason = _gpg_verify.verify_detached(
        sentinel_path,
        sig_path,
        allowlist_path=_SENTINEL_SIGNERS_FILE,
        timeout=_timeout,
    )
    if not ok:
        return False
    if (
        _sentinel_signers is not None
        and _SENTINEL_SIGNERS_REGISTRY_YAML.exists()
        and _fpr
    ):
        _post_genesis = _BOOTSTRAP_REGISTRY_SHA256 is not None
        try:
            # Bootstrap SHA pin verification (post-GENESIS only).
            if _post_genesis:
                import hashlib as _hashlib
                _yaml_bytes = _SENTINEL_SIGNERS_REGISTRY_YAML.read_bytes()
                _computed_sha = _hashlib.sha256(_yaml_bytes).hexdigest()
                if _computed_sha != _BOOTSTRAP_REGISTRY_SHA256:
                    try:
                        from _lib import audit_emit as _audit_emit
                        if hasattr(_audit_emit, "emit_sentinel_signer_quorum_failed"):
                            _audit_emit.emit_sentinel_signer_quorum_failed(
                                key_id=_fpr,
                                reason="bootstrap_sha_mismatch",
                                source="canonical_edit_bootstrap_pin",
                            )
                    except Exception:  # pragma: no cover
                        pass
                    return False
            _registry = _sentinel_signers.load_registry(
                _SENTINEL_SIGNERS_REGISTRY_YAML
            )
            _valid, _why = _sentinel_signers.is_valid_signer(
                _fpr, registry=_registry
            )
            # PLAN-113 WIRE-AUDIT: emit quorum_attempted on EVERY
            # signer verification attempt (success + failure).
            try:
                from _lib import audit_emit as _audit_emit_qa
                if hasattr(_audit_emit_qa, "emit_sentinel_signer_quorum_attempted"):
                    _audit_emit_qa.emit_sentinel_signer_quorum_attempted(
                        distinct_signers=1,
                        threshold_required=1,
                        outcome="valid" if _valid else "failed",
                        source="canonical_edit_sentinel_verify",
                    )
            except Exception:  # pragma: no cover
                pass
            if not _valid:
                try:
                    from _lib import audit_emit as _audit_emit
                    if hasattr(_audit_emit, "emit_sentinel_signer_quorum_failed"):
                        _audit_emit.emit_sentinel_signer_quorum_failed(
                            key_id=_fpr,
                            reason=_why,
                            source="canonical_edit_sentinel_verify",
                        )
                except Exception:  # pragma: no cover
                    pass
                return False
        except Exception:  # pragma: no cover
            # Pre-GENESIS (constant None) — degrade to legacy-only.
            # Post-GENESIS — fail-CLOSED (R2 Codex Q7 fold).
            if _BOOTSTRAP_REGISTRY_SHA256 is not None:
                return False
    return True



def _signature_rail_ok(sentinel_path: Path) -> bool:
    """``_verify_signature_rail`` behind the target-FREE signature cache.

    PLAN162_FIX_1: this is the O(sentinels) rail. The caller's grant
    lookup stays O(sentinels x targets) but is pure string work.
    """
    if _sentinel_cache_disabled():
        return _verify_signature_rail(sentinel_path)
    sig_key = _compute_sig_cache_key(sentinel_path)
    if sig_key is None:
        return _verify_signature_rail(sentinel_path)
    cached = _SIG_VERIFY_CACHE.get(sig_key)
    if cached is not None:
        return cached
    result = _verify_signature_rail(sentinel_path)
    if _WALL_BUDGET_EXHAUSTED:
        # PLAN162_FIX_1 (Codex P1 fold): a budget REFUSAL is not a verdict
        # on this sentinel — memoizing it would poison the signature cache
        # for the rest of the process with a `False` no gpg ever produced.
        # Same contract as the `sig_key is None` path above: errors and
        # non-verdicts are never cached.
        return result
    _SIG_VERIFY_CACHE[sig_key] = result
    return result



def _repo_root_for_sentinels() -> Path:
    """Repo root, resolved exactly as ``main()`` resolves it."""
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())



def _reset_unlock_trust_diag() -> None:
    global _UNLOCK_TRUST_DIAG
    _UNLOCK_TRUST_DIAG = None



def _note_unlock_trust_diag(code: str) -> None:
    global _UNLOCK_TRUST_DIAG
    if _UNLOCK_TRUST_DIAG is None:
        _UNLOCK_TRUST_DIAG = code



def _git_anchor_timeout() -> Optional[float]:
    """Subprocess timeout for ONE ``git cat-file`` anchor probe.

    PLAN162_FIX_S2R2 (codex P1-2). Same shape and the same two constants
    as ``_gpg_verify_timeout``: the probe must finish AND leave room to
    emit. ``None`` means DO NOT SPAWN — callers translate that into
    fail-CLOSED plus a latched budget, never into an allow and never into
    a fork the harness kills mid-flight.
    """
    if _WALL_DEADLINE_AT is None:
        return _GIT_ANCHOR_TIMEOUT_CAP_S
    usable = (_WALL_DEADLINE_AT - _now()) - _GPG_EMIT_MARGIN_S
    if usable < _GPG_MIN_SPAWN_S:
        return None
    return min(_GIT_ANCHOR_TIMEOUT_CAP_S, usable)



def _anchored_blob_text(repo_root: Path, anchor: str, rel: str) -> Optional[str]:
    """Text of ``rel`` AS OF ``anchor``, or ``None`` when unprovable."""
    cache_key = (str(repo_root), anchor, rel)
    if cache_key in _ANCHOR_BLOB_CACHE:
        return _ANCHOR_BLOB_CACHE[cache_key]
    timeout = _git_anchor_timeout()
    if timeout is None:
        # P1-2: refuse the spawn and latch, so the caller's next deadline
        # poll produces the fail-closed wall-deadline block instead of a
        # harness kill. NOT memoized — a budget refusal is not a verdict.
        _mark_wall_budget_exhausted()
        return None
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "cat-file", "blob",
             "{0}:{1}".format(anchor, rel)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
        )
    except Exception:
        # git missing / hung / unusable: the work tree says the proof
        # mechanism SHOULD exist, so an unusable one is fail-CLOSED.
        return None
    if proc.returncode != 0:
        _ANCHOR_BLOB_CACHE[cache_key] = None
        return None
    try:
        text = proc.stdout.decode("utf-8")
    except Exception:
        _ANCHOR_BLOB_CACHE[cache_key] = None
        return None
    _ANCHOR_BLOB_CACHE[cache_key] = text
    return text



def _pinned_sentinel_digests(src_env) -> Tuple[Set[str], bool]:
    """``(digests, malformed)`` from ``CEO_SENTINEL_UNLOCK_SHA256``.

    Empty + not-malformed means "the Owner pinned nothing" (rail B
    decides). ANY unparseable token makes the whole value malformed:
    a typo'd trust input is never silently narrowed to the tokens that
    happened to parse.
    """
    raw = (src_env.get(_UNLOCK_DIGEST_ENV) or "").strip()
    if not raw:
        return (set(), False)
    tokens = [t for t in re.split(r"[,\s]+", raw) if t]
    digests = set()  # type: Set[str]
    for token in tokens:
        if not _SHA256_RE.match(token):
            return (set(), True)
        digests.add(token.lower())
    return (digests, not digests)



def _unlock_trusted_text(sentinel_path: Path, env=None) -> Tuple[bool, Optional[str]]:
    """``(authorized, text_to_parse)`` for ONE sentinel under an unlock.

    PLAN162_FIX_S2 / PLAN162_FIX_S2R2. Consulted ONLY on the
    ``env_override`` path, where the GPG rail is skipped entirely and the
    only thing separating an Owner-signed sentinel from one the AGENT
    just wrote is provenance.

    ``text_to_parse`` is ``None`` for "parse what is on disk" — returned
    only by the two paths where disk bytes ARE the authorized bytes: an
    Owner-pinned digest (which covers exactly those bytes) and the
    non-git residual.
    """
    src_env = env if env is not None else os.environ
    repo_root = _repo_root_for_sentinels()

    # ---- Rail A: the Owner pinned this sentinel's CONTENT (P1-3) ----
    pinned, malformed = _pinned_sentinel_digests(src_env)
    if malformed:
        _note_unlock_trust_diag("digest_malformed")
        return (False, None)
    if pinned:
        try:
            raw = sentinel_path.read_bytes()
        except OSError:
            _note_unlock_trust_diag("sentinel_unreadable")
            return (False, None)
        if hashlib.sha256(raw).hexdigest() in pinned:
            try:
                return (True, raw.decode("utf-8"))
            except Exception:
                _note_unlock_trust_diag("sentinel_undecodable")
                return (False, None)
        # A pin that does not cover THIS sentinel is not a verdict on the
        # others: fall through to the anchor rail, or the pack's
        # pre-existing sentinels would be self-DoS'd by pinning one file.
        _note_unlock_trust_diag("digest_mismatch")

    # ---- Rail B: the sentinel predates the session (anchored bytes) ----
    try:
        is_git = (repo_root / ".git").exists()
    except OSError:
        is_git = False
    if not is_git:
        return (True, None)  # documented residual: no anchor mechanism
    anchor = (src_env.get(_SESSION_ANCHOR_ENV) or "").strip()
    if not _ANCHOR_SHA_RE.match(anchor):
        _note_unlock_trust_diag("anchor_missing" if not anchor else "anchor_malformed")
        return (False, None)
    try:
        rel = str(sentinel_path.relative_to(repo_root)).replace(os.sep, "/")
    except ValueError:
        # A sentinel outside the repo root can never be anchored.
        _note_unlock_trust_diag("sentinel_outside_repo")
        return (False, None)
    text = _anchored_blob_text(repo_root, anchor, rel)
    if text is None:
        _note_unlock_trust_diag("not_anchored")
        return (False, None)
    # P1-1: the ANCHORED bytes are the authorization, not the bytes an
    # in-window writer left at that path.
    return (True, text)



def _unlock_trust_hint() -> str:
    """Teaching suffix for a block an armed unlock window could not lift.

    PLAN162_FIX_S2R2 (codex P1-3). Without this, the operator whose
    recovery route just started failing closed reads "declare the path in
    the Scope: block" about a path that IS declared, and has no way to
    learn which value is missing. Empty string when the unlock rail was
    never the reason.
    """
    if _UNLOCK_TRUST_DIAG is None:
        return ""
    return (
        "\n\nUNLOCK WINDOW ARMED, NO TRUSTED SENTINEL ({diag}). Inside a "
        "CEO_SENTINEL_UNLOCK window the GPG rail is skipped, so a sentinel "
        "must prove it was not written by the agent, by ONE of:\n"
        "  (a) predating the session — export {anchor}=<sha of a commit "
        "taken BEFORE this agent session started>; capture it in your own "
        "shell (`git rev-parse HEAD`) before launching, never after;\n"
        "  (b) Owner-pinned content — export {digest}=<sha256 of the "
        "approved.md>, e.g. `shasum -a 256 <approved.md> | cut -d' ' -f1` "
        "(space- or comma-separate several).\n"
        "See ADR-119 Invariant 5."
    ).format(
        diag=_UNLOCK_TRUST_DIAG,
        anchor=_SESSION_ANCHOR_ENV,
        digest=_UNLOCK_DIGEST_ENV,
    )



def _sentinel_grants_path(sentinel_path: Path, target_rel: str) -> bool:
    """Check whether a sentinel file grants the given target path.

    PLAN-045 Wave 1 P0-01: verification is now two-tiered:

    1. **Plaintext ``Approved-By:`` line** — existing fast check (visual
       Owner signoff marker).
    2. **Detached GPG signature** at ``<sentinel>.asc`` — verified
       against ``.claude/sentinel-signers.txt`` allowlist via
       ``_lib.gpg_verify.verify_detached``. Fail-CLOSED on: missing
       .asc, bad signature, signer fpr not in allowlist, empty
       allowlist.

    **Environment bypass (interim, per ADR-010 amendment)**: setting
    ``CEO_SENTINEL_UNLOCK=<plan-id>`` + ``CEO_SENTINEL_UNLOCK_ACK=I-ACCEPT``
    in the parent shell short-circuits the .asc requirement. This is a
    dual-auth mechanism mirroring the arbitration-kernel escape hatch;
    a sub-agent cannot forge the env vars. The override is logged via
    ``veto_triggered(reason_code=sentinel_unlock_used)``.

    The sentinel must contain:
    1. A valid ``Approved-By: @<handle> <commit-sha>`` line
    2. A ``Scope:`` block listing the target path (one bullet per line)
    3. A sibling ``<sentinel>.asc`` detached GPG signature (unless env
       override is set)
    """
    # PLAN-094 Wave C — session cache fast-path before expensive GPG verify.
    # Cache key (iter-1 P0 fix): (path, inode, mtime_ns, file_size, sha256_full,
    # target_rel, fmt_version). Cache value: granted (bool). env_override path
    # bypasses cache (CEO_SENTINEL_UNLOCK semantic: must re-verify).
    global _SENTINEL_CACHE_HITS, _SENTINEL_CACHE_MISSES

    # PLAN-045 Wave 1 P0-01: env-override (CEO_SENTINEL_UNLOCK) detection.
    env = os.environ
    unlock_reason = (env.get("CEO_SENTINEL_UNLOCK") or "").strip()
    unlock_ack = (env.get("CEO_SENTINEL_UNLOCK_ACK") or "").strip()
    env_override = bool(
        unlock_reason
        and unlock_ack == "I-ACCEPT"
        and re.match(r'^(ADR-\d{3,4}|PLAN-\d{3})-[a-z0-9-]{3,100}$', unlock_reason)  # PLAN-086 Wave I.1 — ADR-119 tightening
    )

    # PLAN162_FIX_1 — SIGNATURE RAIL FIRST, and it is target-FREE.
    #
    # Two reasons the order changed (both are the fix):
    #   * #1 — verifying once per SENTINEL instead of once per
    #     (sentinel x target) is the whole amplification collapse; and
    #   * #10 — the target-keyed grant cache below hashes only
    #     approved.md, so a mutated .asc / allowlist / registry would ride
    #     a stale True if the grant fast-path ran first. Consulting the
    #     material-keyed rail up front makes a revocation land immediately.
    _trusted_text = None  # type: Optional[str]
    if not env_override:
        if not _signature_rail_ok(sentinel_path):
            return False
    else:
        # PLAN162_FIX_S2 — inside an unlock window the GPG rail is skipped
        # entirely, so the only thing separating an Owner-signed sentinel
        # from one the AGENT just wrote is provenance. See the module note
        # above for the two proof forms and the residual.
        _authorized, _trusted_text = _unlock_trusted_text(sentinel_path, env=env)
        if not _authorized:
            return False

    # PLAN-094 Wave C — session cache fast-path (now scope-only).
    # Cache key (iter-1 P0 fix): (path, inode, mtime_ns, file_size, sha256_full,
    # target_rel, fmt_version). Cache value: granted (bool). env_override path
    # bypasses cache (CEO_SENTINEL_UNLOCK semantic: must re-verify).
    _cache_key = None
    if not _sentinel_cache_disabled() and not env_override:
        _cache_key = _compute_sentinel_cache_key(sentinel_path, target_rel)
        if _cache_key is not None:
            _cached = _SENTINEL_VERIFY_CACHE.get(_cache_key)
            if _cached is not None:
                _SENTINEL_CACHE_HITS += 1
                return _cached
            _SENTINEL_CACHE_MISSES += 1

    # PLAN162_FIX_S2R2 (codex P1-1): under an unlock window the bytes that
    # decide are the ANCHORED bytes, never whatever an in-window writer
    # left at that path. ``None`` means "disk bytes ARE the authorized
    # bytes" (Owner-pinned digest, or the non-git residual).
    if _trusted_text is not None:
        text = _trusted_text
    else:
        try:
            text = sentinel_path.read_text(encoding="utf-8")
        except OSError:
            return False

    # Check plaintext signature marker first (cheap).
    if not _APPROVED_BY_RE.search(text):
        return False

    # Parse Scope: block.
    #
    # PLAN-064 Option D (DIM-13 closure, 2026-05-04) — tier-prioritized
    # parser:
    #   Tier 1: if HTML-comment markers <!-- BEGIN SIGNED SCOPE --> /
    #           <!-- END SIGNED SCOPE --> are present, parse Scope: ONLY
    #           from text between those markers. Lifecycle text outside
    #           the markers is ignored for grant decisions; it is
    #           documentation. The GPG `.asc` continues to cover the
    #           whole file (any tamper breaks the signature).
    #   Tier 2: if markers absent (legacy 44 sentinels at 2026-05-04),
    #           fall back to existing _SCOPE_HEADER_RE parser path
    #           below. No env flag — auto-detected.
    #
    # PLAN-044 audit-v2 C6-P0-04 (Tier 2 fallback) — supports two
    # on-disk formats:
    #
    # Format A (PLAN-050 round-17 era — single contiguous bullet list):
    #
    #     Scope:
    #       - .claude/path/one.md
    #       - .claude/path/two.md
    #
    # Format B (Session 67 mega-sentinel — categorized with sub-headers
    # and blank lines between groups):
    #
    #     Scope (24 canonical paths):
    #
    #     ADR canonical promotions (9 files, all from staging):
    #     - .claude/adr/ADR-083-...
    #     - .claude/adr/ADR-084-...
    #
    #     Hook code (PLAN-052):
    #     - .claude/hooks/_lib/foo.py (new)
    #     - .claude/hooks/check_bar.py (new)
    #
    # The Scope block extends from the `Scope` header line to the first
    # top-level continuation header (`Effective:`, `Plans:`, `Rationale`,
    # `Authorization source:`, `Anchor commit:`, a re-encountered
    # `Approved-By:`) or markdown horizontal rule (`---`, `***`, `___`)
    # or end-of-file. Sub-headers within Scope (lines ending with `:`
    # that are NOT in the terminator set) are silently skipped.

    # ---- PLAN162_FIX_4 (finding #4, consensus C5 — narrowed) ----
    #
    # The original council proposal ("parse ONLY inside the markers")
    # would have bricked 31% of live sentinels: 5 of 16 carry no BEGIN
    # marker, including the two most recent ceremonies. What ships is
    # three narrow rules instead:
    #
    #   1. A BEGIN marker with no well-formed PAIR must NEVER silently
    #      downgrade to the Tier-2 whole-file parser. The code already
    #      fail-CLOSES on that exact principle for a marker region with an
    #      unparseable INTERIOR; a BEGIN with a missing/malformed END did
    #      the opposite, which is the containment loss #4 reported —
    #      Scope bullets OUTSIDE the Owner's intended region were honored.
    #   2. Oversize (> _SCOPE_MARKER_CAP_BYTES) REJECTS fail-closed
    #      rather than downgrading to Tier-2. Blast measured ~zero (the
    #      largest live sentinel is 6,801 B = 10.4% of the cap).
    #   3. The END marker terminates a Tier-2 Scope block (added to
    #      _SCOPE_TERMINATOR_RE), so a bullet placed AFTER an END in a
    #      marker-less file is no longer collected.
    #
    # CHARS-vs-BYTES, decided explicitly (C5 required a decision): the cap
    # is named in BYTES, so it is now measured in BYTES. HEAD compared
    # len(text) in CHARACTERS, which for a non-ASCII sentinel understated
    # the real size. Since oversize is now a REJECT (rule 2) rather than a
    # silent downgrade, the stricter of the two readings is also the
    # safer one.
    declared_paths: Set[str] = set()
    try:
        _text_bytes = len(text.encode("utf-8", "surrogatepass"))
    except Exception:  # pragma: no cover - defensive
        _text_bytes = len(text)
    if _text_bytes > _SCOPE_MARKER_CAP_BYTES:
        # Rule 2 — fail-CLOSED. An oversize sentinel is not parsed by
        # EITHER tier; it is rejected.
        return False
    if _BEGIN_MARKER_RE.search(text):
        marker_match = _SCOPE_MARKER_RE.search(text)
        if marker_match is None:
            # Rule 1 — a BEGIN marker is an explicit (if broken) Owner
            # intent signal. Never Tier-2 behind its back.
            return False
        scope_region = marker_match.group(1)
        declared_paths = _parse_scope_paths_from_text(scope_region)
        # If markers present but no scope paths extracted (malformed
        # interior), fail-CLOSED rather than silently fall through
        # to Tier 2 — markers are an explicit Owner intent signal.
        if not declared_paths:
            return False
        granted = target_rel in declared_paths
        if granted and env_override:
            _emit_unlock_audit(target_rel, unlock_reason)
        # PLAN-094-FOLLOWUP Wave C-tier1 — store Tier-1 grant decision
        # in cache (parity with Tier-2 store path below). env_override
        # path is NOT cached (mirrors Tier-2 invariant).
        if (
            _cache_key is not None
            and not env_override
            and not _sentinel_cache_disabled()
        ):
            _SENTINEL_VERIFY_CACHE[_cache_key] = granted
        return granted

    # Tier 2 — legacy _SCOPE_HEADER_RE parser (no markers in file).
    declared_paths = _parse_scope_paths_from_text(text)
    if not declared_paths:
        return False

    granted = target_rel in declared_paths
    if granted and env_override:
        _emit_unlock_audit(target_rel, unlock_reason)

    # PLAN-094 Wave C — store result into module-scope cache (NEVER file-backed).
    # env_override path is NOT cached (semantic: unlock env must always re-verify
    # to honor freshly-regenerated .asc files even when bytes are unchanged).
    if (
        _cache_key is not None
        and not env_override
        and not _sentinel_cache_disabled()
    ):
        _SENTINEL_VERIFY_CACHE[_cache_key] = granted

    return granted
