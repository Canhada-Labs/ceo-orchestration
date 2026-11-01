"""Extracted ceo-boot declarations executed by the facade."""
from __future__ import annotations



# PLAN-177 t2 (re-pass rc.4 P1-f). The POSITIVE half of the probe test.
#
# The S303 filter below identified a probe by ABSENCE alone — five governed
# markers missing — and absence is the shape of the events the ratio exists to
# find: a markerless real spawn (including one the PreToolUse hook admitted by
# failing open) was classified as harness noise and removed from the
# denominator. A probe-only window then reported green with
# `harness_probes_skipped=1` while the governance gap it was built to surface
# went unrendered.
#
# So the structural conditions are necessary, not sufficient: the row must ALSO
# carry the observed harness signature. The signature is CLOSED — the literal
# description the tool-materialization probe emits, anchored at both ends
# (`Load <Tool> via ToolSearch?`, S303 observation, prompt `noop`) — plus
# corroboration by `desc_hash`, which the emitter computes over the RAW
# description: if the two disagree the preview was truncated or redacted, i.e.
# not this short, secret-free probe line. Anything else counts. Every
# uncertainty resolves toward VISIBLE.
_HARNESS_PROBE_DESC_RE = re.compile(
    r"\ALoad [A-Za-z0-9_.\-]+(?:,[ ]?[A-Za-z0-9_.\-]+)* via ToolSearch\?\Z"
)


def _has_harness_probe_fingerprint(ev: Dict[str, Any]) -> bool:
    """True iff the row carries the CLOSED, observed harness-probe signature.

    Positive identification, never inferred from missing fields. An absent or
    non-matching `desc_hash` is NOT corroboration, so it returns False and the
    row is counted — the safe direction for an advisory that exists to expose
    unclassified spawns.
    """
    desc = ev.get("desc_preview")
    if not isinstance(desc, str) or not _HARNESS_PROBE_DESC_RE.match(desc):
        return False
    digest = ev.get("desc_hash")
    if not isinstance(digest, str) or not digest:
        return False
    return digest == hashlib.sha256(desc.encode("utf-8")).hexdigest()


def _is_harness_probe_event(ev: Dict[str, Any]) -> bool:
    """True iff the agent_spawn row is a harness-internal tool-loading probe.

    S303: the ghost filter above was written for the ToolSearch probes of an
    older harness, whose Agent-shaped PostToolUse rows carried NO description
    (desc_preview == "" and desc_hash == SHA256(b"")). The current harness
    supplies a human-readable description for the same class of call — e.g.
    ``Load WebFetch via ToolSearch?`` with prompt ``noop`` and a fixed cheap
    model — so all four ghost conditions no longer hold and a pure
    tool-materialization probe lands in the denominator as a governance gap.

    The discriminator is ``subagent_type``: the Agent/Task spawn contract makes
    it REQUIRED for every governed dispatch (``check_agent_spawn.py`` derives
    the authoritative archetype from it, and ``extract_skill`` Path D needs it),
    so a row that carries none was never a CEO dispatch. All five conditions
    must hold — no subagent_type, no archetype, no rail attribution, no
    ``## AGENT PROFILE`` and no ``## FILE ASSIGNMENT`` — so a real named spawn
    that merely lost one field still counts.

    T-2 STATUS (re-pass rc.4 t5/t7 P2): DEFERRED, not cured — this function
    ALWAYS returns False today and probe-shaped rows COUNT in the
    denominator (a probe-only window reads 1/1 red and the operator
    triages it). The former ``harness_probes_skipped`` counter was removed
    together with the exemption; no row is skipped, so nothing is
    "reported through" anything.

    PLAN-177 t2 (P1-f): those five are NECESSARY, NOT SUFFICIENT. Absence is
    exactly the shape of the event this ratio exists to expose — a markerless
    REAL spawn, including one admitted because the PreToolUse hook failed
    open, matched all five and was deleted from the denominator. The row must
    ALSO carry the closed harness signature
    (``_has_harness_probe_fingerprint``); an unrecognised description counts,
    however markerless the row is.
    """
    # Re-pass rc.4 t2 (P1): the S303 exemption is RETIRED until trusted
    # provenance exists. `desc_preview` and `desc_hash` are both derived
    # from the same CALLER-CONTROLLED description, so the hash corroborates
    # nothing: a real markerless spawn described as
    # `Load WebFetch via ToolSearch?` was silently deleted from the
    # denominator — the exact event this ratio exists to expose. Until the
    # EMITTER can stamp provenance the caller cannot forge, probe-shaped
    # rows COUNT (the conservative direction for an advisory: a yellow the
    # operator triages beats a green that hides a fail-open spawn).
    # _has_harness_probe_fingerprint is kept (tested) as the shape
    # DETECTOR for that future provenance-bearing emitter.
    return False


def check_skill_unknown_ratio() -> Tuple[str, str, Any]:
    """Detect spawns that should have SKILL injection but didn't.

    S94 follow-up: excludes intentionally skill-less archetypes —
    `general-purpose` subagent dispatches via the mitigated rail
    (ADR-082) by design have no SKILL.md anchor. They broker cross-
    LLM gate calls and similar utility work; counting them as FPs
    inflates the ratio to 100% during healthy Codex MCP sessions
    and trains the operator to ignore the channel.

    A spawn counts as "skill missing" ONLY when its `archetype` is
    a custom (non-general-purpose) one AND `skill` is unknown/empty.
    That is the original PLAN-020 ADR-051 governance gap the
    detector was built for.
    """
    # T-2 STATUS (re-pass rc.4 t5 P2): DEFERRED, not cured. Both the S86
    # ghost filter and the S303 probe filter are RETIRED (absence-based,
    # caller-forgeable); every agent_spawn row counts until the EMITTER can
    # stamp provenance the caller cannot forge. The skipped counters were
    # removed with them — a permanently-zero counter reads as "filter
    # active, nothing skipped", which is the wrong claim.
    total = 0
    unknown = 0
    skill_less_by_design = 0
    test_pollution_skipped = 0
    for ev in _iter_audit_events_since(24):
        if ev.get("action") != "agent_spawn":
            continue
        if _is_test_pollution_event(ev):
            test_pollution_skipped += 1
            continue
        # T-2 deferred (t5 P2): ghost/probe exemptions RETIRED — the shape
        # detectors above stay tested for a future provenance-bearing
        # emitter, but no row is skipped on caller-controlled absence.

        # Skill-less by design: general-purpose archetype dispatches
        # (mitigated rail per ADR-082) AND built-in subagent types like
        # Explore/Plan/claude-code-guide that have no .claude/agents/<name>.md
        # and so cannot carry a `Loads <skill> skill via reference` phrase
        # (drift-detector contract per S143 lesson). Adding them to
        # _ARCHETYPE_TO_SKILL would violate the contract — exclude here instead.
        # S200: claude/claude-code-guide/statusline-setup are first-party
        # Claude Code built-ins (no .claude/agents anchor); counting them as a
        # governance gap is a false positive — exactly the FP class this filter
        # exists to prevent (else healthy claude-code-guide use trains the
        # operator to ignore the channel).
        _SKILL_LESS_BUILTINS = {
            "general-purpose", "Explore", "Plan",
            "claude", "claude-code-guide", "statusline-setup",
        }
        if (
            ev.get("subagent_type") in _SKILL_LESS_BUILTINS
            and ev.get("archetype") in _SKILL_LESS_BUILTINS
        ):
            skill_less_by_design += 1
            continue
        total += 1
        if ev.get("skill") in (None, "unknown", ""):
            unknown += 1
    if total == 0:
        msg = (
            "no custom-archetype spawns "
            "({s} general-purpose, {t} test-pollution)".format(
                s=skill_less_by_design, t=test_pollution_skipped,
            )
        )
        return "green", msg, {
            "unknown": 0, "total": 0,
            "skill_less_by_design": skill_less_by_design,
            "test_pollution_skipped": test_pollution_skipped,
        }
    ratio = unknown / total
    status = "red" if ratio > 0.10 else "yellow" if ratio > 0 else "green"
    return status, f"{unknown}/{total} = {ratio:.0%}", {
        "unknown": unknown, "total": total,
        "skill_less_by_design": skill_less_by_design,
        "test_pollution_skipped": test_pollution_skipped,
    }


def check_hook_live_smoke() -> Tuple[str, str, Any]:
    """PLAN-082 Codex Item D replacement for hook_test_baseline.

    Drops the broken `.claude/cache/hook-tests.json` baseline (never
    populated; required pytest 12 s — not boot-budget feasible). Per
    Codex 6th-option: replace with a cheap live hook smoke — parse
    settings.json + verify referenced hook files exist + executable +
    `py_compile` cleanly. Stdlib only, no pytest.

    Test provenance (last full pytest pass) moves to Tier-A
    (`tier_a_hook_test_baseline_age` — separate check).
    """
    import py_compile

    settings = REPO_ROOT / ".claude" / "settings.json"
    if not settings.exists():
        return "yellow", "settings.json missing", None
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return "red", f"settings.json parse: {exc.__class__.__name__}", None

    hooks_table = data.get("hooks") if isinstance(data, dict) else None
    if not isinstance(hooks_table, dict):
        return "yellow", "no hooks table", None

    shim_re = re.compile(r"_python-hook\.sh[\"']?\s+[\"']?([A-Za-z0-9_./-]+\.py)")
    direct_re = re.compile(r"\.claude/hooks/[A-Za-z0-9_./-]+\.py")
    seen: List[str] = []
    seen_set: set = set()
    for hook_list in hooks_table.values():
        if not isinstance(hook_list, list):
            continue
        for entry in hook_list:
            if not isinstance(entry, dict):
                continue
            inner = entry.get("hooks") if isinstance(entry.get("hooks"), list) else []
            for cmd_obj in inner:
                if not isinstance(cmd_obj, dict):
                    continue
                cmd_str = cmd_obj.get("command", "")
                if not isinstance(cmd_str, str):
                    continue
                refs: List[str] = []
                refs.extend(direct_re.findall(cmd_str))
                refs.extend(shim_re.findall(cmd_str))
                for raw in refs:
                    s = re.sub(r"^\$\{?CLAUDE_PROJECT_DIR\}?/", "", raw)
                    if "/" not in s:
                        s = f".claude/hooks/{s}"
                    if s not in seen_set:
                        seen_set.add(s)
                        seen.append(s)

    failures: List[str] = []
    checked = 0
    for rel in seen:
        path = REPO_ROOT / rel
        if not path.is_file():
            failures.append(f"missing:{rel}")
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except (py_compile.PyCompileError, OSError):
            failures.append(f"compile_fail:{rel}")
            continue
        checked += 1

    if failures:
        return "red", f"{len(failures)}/{len(seen)} hook(s) broken", {
            "failures": failures[:10],  # bound for sanitization
            "checked": checked,
            "total": len(seen),
        }
    if checked == 0:
        return "yellow", "no hooks discovered", {"checked": 0, "total": 0}
    return "green", f"{checked} hook(s) smoke-pass", {"checked": checked, "total": len(seen)}


# Backward-compat alias — some external callers / tests may still import the
# old name. Live smoke is a strict improvement (no cache dependency, faster).
check_hook_test_baseline = check_hook_live_smoke


def check_audit_v3_backlog() -> Tuple[str, str, Any]:
    # PoC: count plans with audit_v3_* tags still open
    plans = _get_plan_paths()
    backlog: List[str] = []
    for p in plans:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
        if not m:
            continue
        front = m.group(1)
        if "audit_v3" in front and not re.search(r"^status:\s*done\s*$", front, re.MULTILINE):
            backlog.append(p.stem)
    return ("yellow" if backlog else "green", f"{len(backlog)} open", backlog)


# ---- Padrões de sentinel: DERIVADOS da autoridade (S321) -------------------
# Este check varria UM único padrão (`PLAN-*/architect/round-*/approved.md`)
# enquanto `check_canonical_edit.py` reconhece DEZ. Consequência medida: uma
# cerimônia preparada como `PLAN-182/wave-w1-followup-approved.md` — formato
# válido e aceito pelo guard — nunca aparecia no digest de boot, e o check
# reportava "0 pending" com um sentinel esperando assinatura. Guard verde que
# não vê o alvo.
#
# A cura NÃO é copiar a lista para cá: uma segunda cópia envelhece em
# silêncio, que é a classe que este repo caça. Os padrões são EXTRAÍDOS por
# AST do arquivo que os define. `_PATTERNS` é local a uma função lá, então
# não dá para importar — o AST é o mecanismo, não a aparência.
#
# Fail-open com VOZ: se a extração falhar, cai num conjunto mínimo E o
# summary declara que está em fallback. Um degradê silencioso reproduziria o
# defeito que esta função existe para curar.
_SENTINEL_PATTERNS_FALLBACK = (
    "PLAN-*/architect/round-*/approved.md",
    "PLAN-*/approved.md",
    "PLAN-*/wave-*-approved.md",
    "PLAN-*/approved-amendment-*.md",
)


def _sentinel_patterns() -> Tuple[Tuple[str, ...], bool]:
    """(padrões, derived) — `derived=False` sinaliza fallback."""
    import ast

    src_path = REPO_ROOT / ".claude" / "hooks" / "check_canonical_edit.py"
    try:
        tree = ast.parse(src_path.read_text(encoding="utf-8"))
    except Exception:
        return _SENTINEL_PATTERNS_FALLBACK, False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if "_PATTERNS" not in names:
            continue
        try:
            value = ast.literal_eval(node.value)
        except Exception:
            continue
        pats = tuple(
            p for p in value
            if isinstance(p, str) and p.startswith("PLAN-")
        )
        if pats:
            return pats, True
    return _SENTINEL_PATTERNS_FALLBACK, False


def check_sentinels_pending_gpg() -> Tuple[str, str, Any]:
    """Count GPG-pending sentinels post-cutoff.

    Codex S82 P2 fix: previous impl scanned ALL historical sentinels with no
    date cutoff → 30+ pending entries every boot from PLAN-030/031/039 round-1
    pre-enforcement era. Now applies SENTINEL_CUTOFF_EPOCH (2026-04-22) to
    skip legacy. Also Codex S82 P2 sorted glob for CR-N7 stable ordering.
    """
    pending: List[str] = []
    plans_dir = REPO_ROOT / ".claude" / "plans"
    patterns, derived = _sentinel_patterns()
    for pat in patterns:
        for approved in sorted(plans_dir.glob(pat)):
            try:
                mtime = approved.stat().st_mtime
            except OSError:
                continue
            if mtime < SENTINEL_CUTOFF_EPOCH:
                continue  # pre-enforcement legacy
            # S321: o `.asc` acompanha o ARQUIVO, não um `approved.md` fixo
            # no diretório. A forma antiga (`parent / "approved.md.asc"`)
            # só funcionava para o padrão `.../approved.md` e teria dado
            # falso-pendente para `wave-*-approved.md`.
            if not approved.with_name(approved.name + ".asc").exists():
                rel = str(approved.relative_to(REPO_ROOT))
                if rel not in pending:
                    pending.append(rel)
    pending.sort()  # CR-N7 ordenação estável
    note = "" if derived else " [padrões em FALLBACK — a autoridade não foi lida]"
    return (
        "yellow" if pending else "green",
        f"{len(pending)} pending{note}",
        pending,
    )


def check_rc_hold_aged() -> Tuple[str, str, Any]:
    release_md = REPO_ROOT / "RELEASE.md"
    rc_hold = REPO_ROOT / "RC-HOLD.md"
    target = release_md if release_md.exists() else rc_hold if rc_hold.exists() else None
    if target is None:
        return "green", "no rc-hold doc", None
    text = target.read_text(encoding="utf-8", errors="replace")
    # PoC: count rc-hold-waiver entries (real impl would parse dates)
    n = len(re.findall(r"rc-hold-waiver", text))
    return ("yellow" if n else "green", f"{n} rc-hold-waiver entries", n)


# E7-F5 (PLAN-120-FOLLOWUP): real daily-USD burn-rate thresholds.
# Previously this check returned "green" unconditionally (Potemkin stub) — it
# tallied cost_usd over 24h but never compared it against a budget, so a
# runaway burn never surfaced at boot. We now apply a yellow/red ceiling.
# Both bounds are env-overridable (adopter sessions differ wildly in cost);
# defaults are calibrated to a typical heavy CEO session. Fail-OPEN: any
# parse/lookup error degrades to the default ceiling, never raises, and an
# empty/zero-cost log stays green (the steady-state).
_COST_YELLOW_USD_DEFAULT = 50.0
_COST_RED_USD_DEFAULT = 150.0


def _cost_threshold(env_var: str, default: float) -> float:
    """Read a positive float ceiling from env; fall back to default fail-open."""
    raw = os.environ.get(env_var, "")
    if not raw:
        return default
    try:
        val = float(raw.strip())
    except (TypeError, ValueError):
        return default
    # Reject non-finite / non-positive overrides (would defeat the gate).
    if val != val or val == float("inf") or val <= 0:
        return default
    return val


def check_cost_24h_usd() -> Tuple[str, str, Any]:
    """Sum cost_usd over 24h and gate against env-overridable USD ceilings.

    yellow at CEO_BOOT_COST_YELLOW_USD (default $50/24h); red at
    CEO_BOOT_COST_RED_USD (default $150/24h). Fail-open: no cost datapoints
    or unreadable log => green. Thresholds are advisory burn-rate alerts
    (ADR-064 50/80/95% doctrine), never a hard block.
    """
    total = 0.0
    samples = 0
    for ev in _iter_audit_events_since(24):
        c = ev.get("cost_usd")
        if isinstance(c, (int, float)) and not isinstance(c, bool):
            total += float(c)
            samples += 1
    yellow = _cost_threshold("CEO_BOOT_COST_YELLOW_USD", _COST_YELLOW_USD_DEFAULT)
    red = _cost_threshold("CEO_BOOT_COST_RED_USD", _COST_RED_USD_DEFAULT)
    # Guard against an inverted override (yellow >= red): keep red as the
    # higher bound so the status ladder stays monotonic.
    if yellow >= red:
        yellow = min(yellow, red)
    if samples == 0:
        status = "green"
    elif total >= red:
        status = "red"
    elif total >= yellow:
        status = "yellow"
    else:
        status = "green"
    return status, f"${total:.2f}/24h", {
        "total_usd": round(total, 4),
        "samples": samples,
        "yellow_usd": yellow,
        "red_usd": red,
    }


def check_active_plan_burn_ratio() -> Tuple[str, str, Any]:
    # PoC: find first executing plan, parse budget_tokens, sum tokens from log
    _, _, executing = check_plans_executing()
    if not executing:
        return "green", "no active plan", None
    plan_id = executing[0].split("-")[0] + "-" + executing[0].split("-")[1] if executing else None
    if not plan_id:
        return "green", "no plan id", None
    plan_path = REPO_ROOT / ".claude" / "plans" / f"{executing[0]}.md"
    try:
        text = plan_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "yellow", "plan unreadable", None
    m = re.search(r"^budget_tokens:\s*(.+?)$", text, re.MULTILINE)
    if not m:
        return "yellow", "no budget_tokens", None
    return "green", f"budget {m.group(1).strip()}", {"plan": plan_id, "budget_raw": m.group(1).strip()}


def check_adrs_stale_proposed() -> Tuple[str, str, Any]:
    adrs = sorted((REPO_ROOT / ".claude" / "adr").glob("ADR-*.md"))
    proposed_old: List[str] = []
    now = time.time()
    for a in adrs:
        try:
            text = a.read_text(encoding="utf-8", errors="replace")
            mtime = a.stat().st_mtime
        except OSError:
            continue
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
        if not m:
            continue
        if re.search(r"^status:\s*proposed\s*$", m.group(1), re.MULTILINE):
            age_d = (now - mtime) / 86400
            if age_d > 30:
                proposed_old.append(a.stem)
    return ("yellow" if proposed_old else "green", f"{len(proposed_old)} proposed >30d", proposed_old)


# ---- 11 Tier-A checks (--verbose mode; PLAN-065 §4.3.3) ------------------
# Selection rationale (each picked for high signal-to-cost ratio + non-overlap
# with Tier-S; see PLAN-065 §4.3.3):
#   tier_a_debate_transcripts     — debate hygiene (Round-1 archetype output)
#   tier_a_lessons_30d            — lesson velocity (memory growth pulse)
#   tier_a_spec_version_drift     — VERSION ↔ SPEC/v*/VERSION mismatch
#   tier_a_npm_version_match      — package.json vs VERSION mismatch
#   tier_a_waivers_count          — waivers/*.md aggregate (rc-hold + cosmetic)
#   tier_a_adrs_recent_status     — ADR-098..104 reservation slots tracking
#   tier_a_cache_hit_rate_24h     — ceo-boot-emitted cache_hit ratio (self-loop)
#   tier_a_hook_test_baseline_age — last-cached hook-test baseline age (S81 cache)
#   tier_a_sentinel_signers_tracked — .claude/state/sentinel-signers.txt git-tracked?
#   tier_a_gitignore_state_excluded — .gitignore covers state/ dir?
#   tier_a_model_currency         — PLAN-176 W3a trio per lane (advisory, offline)


def check_tier_a_debate_transcripts() -> Tuple[str, str, Any]:
    """Count debate transcripts produced in last 24h (forensic hygiene)."""
    debate_root = REPO_ROOT / ".claude" / "plans"
    n = 0
    cutoff = time.time() - 86400
    for transcript in debate_root.rglob("debate/*/round-*.md"):
        try:
            if transcript.stat().st_mtime >= cutoff:
                n += 1
        except OSError:
            continue
    # Status green regardless — informational. Yellow if zero AND there is an
    # executing plan (suggests work without debate trail).
    _, _, executing = check_plans_executing()
    if n == 0 and executing:
        return "yellow", f"0 transcripts/24h ({len(executing)} executing)", n
    return "green", f"{n} transcripts/24h", n


# CEO-INFORMATIONAL-ONLY: velocidade de licoes, docstring ja diz informational
def check_tier_a_lessons_30d() -> Tuple[str, str, Any]:
    """Count lessons added in memory dir over 30d (informational)."""
    # Derive the Claude Code project slug from the project dir (absolute path
    # with "/" -> "-") instead of hard-coding the meta-repo's slug, so this
    # resolves correctly in any install. (Previously hard-coded the Owner's
    # absolute home path, which broke for every other install and tripped the
    # contamination guard.)
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    slug = _rp.project_slug(project_dir)  # PLAN-182 W3 (S321): slug via resolvedor unico, nunca re-derivado
    mem_dir = Path.home() / ".claude" / "projects" / slug / "memory"
    if not mem_dir.exists():
        return "green", "memory dir absent", 0
    cutoff = time.time() - 30 * 86400
    n = 0
    for f in mem_dir.glob("*.md"):
        try:
            if f.stat().st_mtime >= cutoff:
                n += 1
        except OSError:
            continue
    return "green", f"{n} lessons/30d", n
