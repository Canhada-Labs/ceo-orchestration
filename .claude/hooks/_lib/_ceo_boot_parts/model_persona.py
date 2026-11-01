"""Extracted ceo-boot declarations executed by the facade."""
from __future__ import annotations



def check_tier_a_spec_version_drift() -> Tuple[str, str, Any]:
    """VERSION major vs latest SPEC/v* major agreement — red on drift.

    Cured in PLAN-178 W-C Lote A (C3): the original body read both
    inputs and never compared them — every reachable path returned
    green (the S287-class "registered-vacuous" case documented in
    memory feedback-check-tier-a-spec-version-drift-vacuous and in the
    W0 coverage table). Invariant now enforced: the MAJOR of the
    FRAMEWORK version must equal the highest SPEC/v<N> directory major.

    Ownership-aware source (codex Lote-A P2-1): the root ``VERSION``
    in an ADOPTER repo is the adopter app's version (ADR-155-AMEND-1
    §2) — comparing it to the shipped SPEC would false-red. The
    framework version is ``.claude/.framework-version`` (written by
    install/upgrade; present in the dogfood checkout too). Without
    that file no drift claim is possible — informational green, never
    red on unattributable input.

    Provenance (codex r2 P2-1, ADR-155-AMEND-1 §5): existence is not
    authority. The marker only supports a RED verdict when its
    delivery is verifiable: (a) the baseline manifest
    ``.claude/.install-manifest.sha256`` carries a record for it
    (adopter install/upgrade path), or (b) the marker is git-tracked
    in this checkout (framework/dogfood path). Unverified marker +
    mismatch => yellow (drift SUSPECTED), never red — and never a
    silent green either.
    """
    fw_file = REPO_ROOT / ".claude" / ".framework-version"
    if not fw_file.exists():
        return "green", "no .framework-version (drift not attributable)", None
    try:
        repo_v = fw_file.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return "yellow", ".framework-version unreadable", None
    provenance_ok = False
    manifest = REPO_ROOT / ".claude" / ".install-manifest.sha256"
    try:
        if manifest.exists() and ".claude/.framework-version" in manifest.read_text(
                encoding="utf-8", errors="replace"):
            provenance_ok = True
    except OSError:
        pass
    if not provenance_ok:
        try:
            provenance_ok = subprocess.run(
                ["git", "-C", str(REPO_ROOT), "ls-files", "--error-unmatch",
                 ".claude/.framework-version"],
                capture_output=True, timeout=2,
            ).returncode == 0
        except (OSError, subprocess.SubprocessError):
            provenance_ok = False
    spec_root = REPO_ROOT / "SPEC"
    if not spec_root.exists():
        return "green", f"repo {repo_v}, no SPEC dir", repo_v
    spec_majors = []
    for p in spec_root.iterdir():
        if p.is_dir() and p.name.startswith("v"):
            try:
                spec_majors.append(int(p.name[1:]))
            except ValueError:
                return "yellow", f"unparseable SPEC dir {p.name}", None
    if not spec_majors:
        return "green", f"repo {repo_v}, no SPEC versions", repo_v
    try:
        repo_major = int(repo_v.split(".", 1)[0])
    except ValueError:
        return "yellow", f"unparseable .framework-version {repo_v}", None
    latest_spec = max(spec_majors)
    detail = {"repo_version": repo_v,
              "spec_versions": ["v%d" % m for m in sorted(spec_majors)],
              "provenance_verified": provenance_ok}
    if repo_major != latest_spec:
        if provenance_ok:
            return "red", (
                f"drift: framework major {repo_major} vs SPEC v{latest_spec}"
            ), detail
        return "yellow", (
            f"drift suspected: marker {repo_major} vs SPEC v{latest_spec} "
            "(provenance unverified — ADR-155-AMEND-1 §5)"
        ), detail
    return "green", f"framework {repo_v} ~ spec v{latest_spec}", detail


def check_tier_a_npm_version_match() -> Tuple[str, str, Any]:
    """package.json version vs VERSION file (Codex S79 P1 finding)."""
    version_file = REPO_ROOT / "VERSION"
    pkg_file = REPO_ROOT / "package.json"
    if not version_file.exists() or not pkg_file.exists():
        return "green", "no npm artifacts", None
    try:
        repo_v = version_file.read_text(encoding="utf-8", errors="replace").strip()
        pkg = json.loads(pkg_file.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return "yellow", "parse error", None
    pkg_v = pkg.get("version", "")
    if pkg_v == repo_v:
        return "green", f"match {repo_v}", {"version": repo_v}
    return "red", f"drift: VERSION={repo_v} package.json={pkg_v}", {
        "repo_version": repo_v, "pkg_version": pkg_v,
    }


def check_tier_a_waivers_count() -> Tuple[str, str, Any]:
    """Aggregate waivers/*.md count (rc-hold + cosmetic + audit)."""
    waivers_dir = REPO_ROOT / "waivers"
    if not waivers_dir.exists():
        return "green", "no waivers dir", 0
    waivers = list(waivers_dir.glob("*.md"))
    n = len(waivers)
    status = "yellow" if n > 5 else "green"
    return status, f"{n} waivers", n


# CEO-INFORMATIONAL-ONLY: tracker de slots reservados, sem limiar (PLAN-178 C3)
def check_tier_a_adrs_recent_status() -> Tuple[str, str, Any]:
    """ADR-098..104 status tracker (PLAN-065 reserved slots — drift detector)."""
    adr_dir = REPO_ROOT / ".claude" / "adr"
    statuses: Dict[str, str] = {}
    for adr_num in range(98, 105):
        matches = list(adr_dir.glob(f"ADR-{adr_num:03d}-*.md"))
        if not matches:
            statuses[f"ADR-{adr_num:03d}"] = "missing"
            continue
        try:
            text = matches[0].read_text(encoding="utf-8", errors="replace")
        except OSError:
            statuses[f"ADR-{adr_num:03d}"] = "unreadable"
            continue
        m = re.search(r"^status:\s*([a-zA-Z\-]+)\s*$", text, re.MULTILINE)
        statuses[f"ADR-{adr_num:03d}"] = m.group(1).lower() if m else "unknown"
    accepted = sum(1 for v in statuses.values() if v == "accepted")
    return "green", f"{accepted}/{len(statuses)} accepted", statuses


# CEO-INFORMATIONAL-ONLY: auto-observacao de cache, sem limiar (PLAN-178 C3)
def check_tier_a_cache_hit_rate_24h() -> Tuple[str, str, Any]:
    """ceo_boot_emitted cache_hit ratio over 24h (self-observation)."""
    total = 0
    hits = 0
    for ev in _iter_audit_events_since(24):
        if ev.get("action") != "ceo_boot_emitted":
            continue
        total += 1
        if ev.get("cache_hit"):
            hits += 1
    if total == 0:
        return "green", "no boots/24h", 0
    ratio = hits / total
    return "green", f"{hits}/{total} = {ratio:.0%} cache-hit", {
        "hits": hits, "total": total, "ratio": ratio,
    }


def check_tier_a_hook_test_baseline_age() -> Tuple[str, str, Any]:
    """Age of cached hook-test baseline file (S81 cache convention)."""
    cache = REPO_ROOT / ".claude" / "cache" / "hook-tests.json"
    if not cache.exists():
        return "yellow", "no cached baseline", None
    try:
        st = cache.stat()
    except OSError:
        return "yellow", "stat failed", None
    age_h = (time.time() - st.st_mtime) / 3600.0
    status = "green" if age_h < 168 else "yellow"  # 7d window
    return status, f"{age_h:.1f}h old", {"age_hours": age_h}


def check_tier_a_sentinel_signers_tracked() -> Tuple[str, str, Any]:
    """sentinel-signers.txt presence + git-tracked status."""
    candidates = [
        REPO_ROOT / ".claude" / "state" / "sentinel-signers.txt",
        REPO_ROOT / "sentinel-signers.txt",
    ]
    found: Optional[Path] = None
    for c in candidates:
        if c.exists():
            found = c
            break
    if found is None:
        return "yellow", "sentinel-signers.txt missing", None
    try:
        proc = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "ls-files", "--error-unmatch", str(found.relative_to(REPO_ROOT))],
            capture_output=True, text=True, timeout=1.5,
        )
        tracked = (proc.returncode == 0)
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        return "yellow", "git unavailable", None
    return ("green" if tracked else "yellow",
            f"present, tracked={tracked}",
            {"path": str(found.relative_to(REPO_ROOT)), "tracked": tracked})


def check_tier_a_gitignore_state_excluded() -> Tuple[str, str, Any]:
    """.gitignore covers state/ dir (LRU cache + sentinels safety)."""
    gi = REPO_ROOT / ".gitignore"
    if not gi.exists():
        return "yellow", ".gitignore missing", None
    try:
        text = gi.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "yellow", ".gitignore unreadable", None
    # Match leading patterns: state/, .claude/state/, /state, etc.
    has_state = bool(re.search(r"(?m)^\s*\.?/?(?:\.claude/)?state/", text))
    return ("green" if has_state else "yellow",
            f"state/ excluded={has_state}",
            {"covered": has_state})


def check_main_checkout_state() -> Tuple[str, str, Any]:
    """Item 14 (c) of the 1.4.4 backlog: the main checkout off its default branch.

    Twice in S363 an agent moved HEAD in the main checkout while the `main` ref and the
    tree stayed intact (`git switch -c` from a heredoc; a failed `cd` before `git
    checkout`), so nothing else showed it, and the risk is the Owner pulling and signing
    on the wrong branch. Yellow, never red: a branch can be on purpose, and only the
    reflog tells. A linked worktree is a shadow, so it is out of scope. Read-only.
    """
    def _git(*args: str) -> "subprocess.CompletedProcess[str]":
        return subprocess.run(["git", "-C", str(REPO_ROOT)] + list(args),
                              capture_output=True, text=True, timeout=0.8, check=False)

    try:
        dirs = _git("rev-parse", "--git-dir", "--git-common-dir")
        if dirs.returncode != 0:
            return "green", "not a git checkout", None
        git_dir, common_dir = dirs.stdout.split("\n")[:2]
        if os.path.realpath(REPO_ROOT / git_dir) != os.path.realpath(REPO_ROOT / common_dir):
            return "green", "linked worktree (out of scope)", {"linked_worktree": True}
        head = _git("symbolic-ref", "-q", "HEAD")
        origin = _git("symbolic-ref", "-q", "refs/remotes/origin/HEAD")
    except (OSError, ValueError, subprocess.SubprocessError):
        return "yellow", "git did not answer about the checkout", None
    prefix = "refs/remotes/origin/"
    default = origin.stdout.strip()
    default = default[len(prefix):] if default.startswith(prefix) else "main"
    read_first = "read `git reflog -n 20` before any work"
    if head.returncode != 0:
        return "yellow", f"main checkout has a DETACHED HEAD: {read_first}", {"detached": True}
    branch = head.stdout.strip()
    branch = branch[len("refs/heads/"):] if branch.startswith("refs/heads/") else branch
    if branch != default:
        shown = branch if re.fullmatch(r"[A-Za-z0-9._/-]{1,80}", branch) else "(unprintable)"
        return ("yellow", f"main checkout is on {shown}, not {default}: {read_first}",
                {"detached": False, "branch": shown, "default": default})
    return "green", f"main checkout on {default}", {"detached": False, "default": default}


# PLAN-176 W3a — 11th Tier-A check, advisory + offline: per ACTIVE lane of the W0a
# detector (in-process; `--state --json` has no working set) the trio instalado /
# fixado (ADR-149) / upstream (W0b cache, READ, never fetched). Never red; failures
# and adopter trees (no ADR-149) degrade to «sem dado». The cache is EXTERNAL: bounded
# read, only grammar ids (<= SHOW_MAX) inside «externo, …», the rest only counted.
# W0b reader contract: {"lanes": {"<lane>": {"models": [ids]}}}; age = file mtime.
# Lane missing from the cache = «sem dado»; lane present but malformed = yellow.
_MC_ADR_REL = (".claude", "adr", "ADR-149-model-id-allowlist.md")
_MC_DETECTOR_REL = (".claude", "scripts", "check-model-currency.py")
_MC_EXPECTED_REL = (".claude", "data", "model-currency-expected-reds.txt")
_MC_CACHE_REL = (".claude", "data", "model-currency-upstream-cache.json")
MODEL_CURRENCY_CACHE_MAX_BYTES = 64 * 1024
MODEL_CURRENCY_SHOW_MAX_IDS = 3
MODEL_CURRENCY_STALE_HOURS = 96  # K-3 of PLAN-176 §4
_MC_ID_RE = re.compile(r"[a-z0-9]+(?:[.-][a-z0-9]+){0,7}\Z")
_MC_NO_DATA = {
    "absent": "sem dado (cache ausente; idade n/d)",
    "stale": "sem dado (cache com {age} > %d h)" % MODEL_CURRENCY_STALE_HOURS,
    "oversize": "sem dado (cache acima de %d bytes: leitura truncada, conteúdo "
                "descartado; idade {age})" % MODEL_CURRENCY_CACHE_MAX_BYTES,
    "malformed": "sem dado (cache malformado; idade {age})",
    "no_lane": "sem dado (cache sem a raia; idade {age})",
}


def _mc_id_ok(value: Any) -> bool:
    return isinstance(value, str) and len(value) <= 48 and bool(_MC_ID_RE.match(value))


def _mc_lane(det: Any, model_id: str) -> Optional[str]:
    try:
        return det.family_of(model_id)[0]
    except Exception:  # noqa: BLE001 — unmodelled family = no lane
        return None


def _mc_read_upstream(root: Path) -> Dict[str, Any]:
    import stat as _stat
    path = root.joinpath(*_MC_CACHE_REL)
    try:
        st = os.stat(path)
    except OSError:
        return {"state": "absent", "age": "n/d"}
    age_h = max(0.0, time.time() - st.st_mtime) / 3600.0
    out: Dict[str, Any] = {"state": "malformed", "age": "%.1f h" % age_h}
    if age_h > MODEL_CURRENCY_STALE_HOURS:
        out["state"] = "stale"
    elif _stat.S_ISREG(st.st_mode):  # a FIFO would block the boot on open()
        try:
            with open(path, "rb") as fh:
                raw = fh.read(MODEL_CURRENCY_CACHE_MAX_BYTES + 1)
            if len(raw) > MODEL_CURRENCY_CACHE_MAX_BYTES:
                out["state"] = "oversize"
            else:
                lanes = json.loads(raw.decode("utf-8")).get("lanes")
                if isinstance(lanes, dict):
                    out.update(state="ok", lanes=lanes)
        except (OSError, UnicodeDecodeError, ValueError, AttributeError):
            pass
    return out


def _mc_upstream_cell(det: Any, up: Dict[str, Any], lane: str,
                      pinned: List[str]) -> Tuple[str, List[str], str]:
    entry = (up.get("lanes") or {}).get(lane)
    models = entry.get("models") if isinstance(entry, dict) else None
    key = up["state"]
    if key == "ok" and not isinstance(models, list):
        key = "malformed" if lane in up["lanes"] else "no_lane"
    if key != "ok":
        return _MC_NO_DATA[key].format(age=up["age"]), [], key
    valid = [m for m in models if _mc_id_ok(m) and _mc_lane(det, m) == lane]
    unique = list(dict.fromkeys(valid))
    novel = [m for m in unique if m not in pinned]
    shown = novel[:MODEL_CURRENCY_SHOW_MAX_IDS]
    more = " (+%d truncados)" % (len(novel) - len(shown)) if novel[len(shown):] else ""
    return ("«externo, %s: %d ids; fora do fixado: %s%s; descartados=%d»" % (
        up["age"], len(unique), ", ".join(shown) or "nenhum", more,
        len(models) - len(valid))), novel, key


def _mc_trio(root: Path) -> Tuple[str, str, Any]:
    try:
        settings = json.loads(root.joinpath(".claude", "settings.json").read_text(
            encoding="utf-8"))
    except (OSError, ValueError):
        settings = {}
    settings = settings if isinstance(settings, dict) else {}
    raw = settings.get("model")
    installed = raw if _mc_id_ok(raw) else None
    inst = installed or ("sem dado" if raw is None else "valor não reconhecido")
    det_path = root.joinpath(*_MC_DETECTOR_REL)
    if not root.joinpath(*_MC_ADR_REL).is_file() or not det_path.is_file():
        why = ("ADR-149 ausente — árvore de adopter"
               if not root.joinpath(*_MC_ADR_REL).is_file() else "detector ausente")
        return "green", "model-currency: sem dado (%s); instalado=%s" % (why, inst), None
    import importlib.util
    spec = importlib.util.spec_from_file_location("_ceo_boot_mc_detector", str(det_path))
    det = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(det)  # type: ignore[union-attr]
    try:
        report = det.scan(root, det.build_parser().parse_args([]))
        exp = root.joinpath(*_MC_EXPECTED_REL)
        drift = (det.compare_reds(report["red_ids"], det.read_expected_reds(exp))
                 if exp.is_file() else None)
    except det.DetectorBroke as exc:
        why = _sanitize_for_recs(str(exc)).replace("|", "/")[:120]
        return "yellow", "model-currency: sem dado (detector recusou: %s)" % why, None
    pinned_all = list(report["authorities"]["working_set"])
    up = _mc_read_upstream(root)
    cells: List[str] = []
    lanes: Dict[str, Any] = {}
    for lane in report["active_lanes"]:
        pinned = [m for m in pinned_all if _mc_lane(det, m) == lane]
        mine = installed if installed and _mc_lane(det, installed) == lane else None
        member = "" if mine is None else (
            " (instalado ∈ fixado)" if mine in pinned else " (instalado FORA do fixado)")
        cell, novel, key = _mc_upstream_cell(det, up, lane, pinned)
        cells.append("%s: instalado=%s · fixado=%d ids%s · upstream=%s" % (
            lane, mine or "nenhum nesta raia", len(pinned), member, cell))
        lanes[lane] = {"installed": mine, "novel": novel[:MODEL_CURRENCY_SHOW_MAX_IDS],
                       "upstream": key}
    n_red = len(report["red_ids"])
    reds = ("vermelhos=%d (sem conjunto esperado)" % n_red if drift is None else
            "vermelhos=%d (fora do esperado: +%d/-%d)" % (n_red, len(drift[0]), len(drift[1]))
            if drift[0] or drift[1] else "vermelhos=%d (= esperado)" % n_red)
    summary = "model-currency: %s · availableModels %s · %s" % (
        " ; ".join(cells), "= fixado" if settings.get("availableModels") == pinned_all
        else "≠ fixado", reds)
    detail = {"lanes": lanes, "upstream": up["state"]}
    if (any(v["novel"] or v["upstream"] in ("oversize", "malformed") for v in lanes.values())
            or (drift is not None and (drift[0] or drift[1]))):
        return "yellow", summary, detail
    return "green", summary, detail


def check_tier_a_model_currency() -> Tuple[str, str, Any]:
    """PLAN-176 W3a advisory — never red, never raises (see block comment)."""
    try:
        return _mc_trio(REPO_ROOT)
    except Exception as exc:  # noqa: BLE001 — advisory floor: degrade, never break
        return "yellow", "model-currency: sem dado (advisory falhou: %s)" % (
            type(exc).__name__), None


# ---- Registry --------------------------------------------------------------


def check_tier_policy_misrouting_24h() -> Tuple[str, str, Any]:
    """16th Tier-S check — delegates to standalone hook module (PLAN-091 W2.1).

    Lazy-imports ``.claude/hooks/check_tier_policy_misrouting_24h.py`` so
    that the standalone module can also be invoked as a CLI smoke-test
    (``python3 .claude/hooks/check_tier_policy_misrouting_24h.py``).
    Any import-time failure surfaces as a `yellow` status (fail-soft
    Tier-S contract); the dispatcher's outer try/except still wraps the
    inner call for additional defense-in-depth.
    """
    try:
        hooks_dir = REPO_ROOT / ".claude" / "hooks"
        if str(hooks_dir) not in sys.path:
            sys.path.insert(0, str(hooks_dir))
        from check_tier_policy_misrouting_24h import (  # type: ignore
            check_tier_policy_misrouting_24h as _impl,
        )
        return _impl()
    except Exception as exc:  # noqa: BLE001 (Tier-S fail-soft floor)
        return "yellow", f"tier_policy_misrouting import error: {exc}", None


def check_cache_discipline_alerted() -> Tuple[str, str, Any]:
    """17th Tier-S check — prompt-cache coverage detection (PLAN-093 Wave C.2).

    Surfaces ``cache_discipline_alerted`` when prompt-cache coverage falls
    below 0.7 over the last 24h of audit-log events. Detection is heuristic:
    any audit row (``agent_spawn`` action) carrying a ``cache_coverage_bps``
    numeric field is averaged; rows without the field are ignored. Absent
    any datapoints, status is green with a "no data" summary (fail-soft
    Tier-S contract).

    Field alignment (F-5-5.1-0624274e fix): audit_log.py emits the
    cache-coverage metric derived from usage_metadata cache_read /
    (cache_read + cache_creation + uncached); older code read the
    non-existent ``cache_hit_rate`` field, causing the gate to always
    return green/"no data". This fix aligns the reader to the emitted field.
    PLAN-118 WS-E (S181): the emitted field is now ``cache_coverage_bps``
    (integer basis-points); this reader reads it (÷10000) and falls back to
    the legacy ``cache_coverage`` float for events emitted before the fix.

    Emits ``cache_discipline_alerted`` via ``emit_generic`` on yellow/red
    so downstream analytics can correlate with /ceo-boot runs. Action
    name is registered at ``audit_emit.py:440`` (PLAN-088 canonical).
    """
    threshold = 0.70
    try:
        rates: List[float] = []
        for ev in _iter_audit_events_since(hours=24.0):
            # S239: skip synthetic governance-probe / benchmark spawns — they
            # carry cache_coverage_bps=0 by construction (no real cached LLM
            # call), so a probe-only 24h window would pin this gate to red (FP).
            if _is_test_pollution_event(ev):
                continue
            # PLAN-118 WS-E (S181): primary field is now ``cache_coverage_bps``
            # (integer basis-points, ratio × 10000) — the legacy float
            # ``cache_coverage`` was dropped because it broke the HMAC chain.
            # Read bps first, fall back to the legacy float for events emitted
            # before the fix (the 24h window straddles the transition; without
            # the fallback this Tier-S gate would go silently dead again —
            # the exact F-5-5.1-0624274e failure mode this check exists to avoid).
            v_bps = ev.get("cache_coverage_bps")
            if isinstance(v_bps, int) and not isinstance(v_bps, bool) and 0 <= v_bps <= 10000:
                rates.append(v_bps / 10000.0)
                continue
            # F-5-5.1-0624274e: legacy float field (pre-PLAN-118 events).
            v = ev.get("cache_coverage")
            if isinstance(v, (int, float)) and not isinstance(v, bool) and 0.0 <= float(v) <= 1.0:
                rates.append(float(v))
        if not rates:
            return "green", "no cache_coverage datapoints", {"samples": 0}
        avg = sum(rates) / len(rates)
        if avg < threshold:
            try:
                if _audit_emit is not None and hasattr(
                    _audit_emit, "emit_cache_discipline_alerted"
                ):
                    _audit_emit.emit_cache_discipline_alerted(
                        hit_rate_basis_points=max(
                            0, min(1000, int(round(avg * 1000)))
                        ),
                        floor_basis_points=max(
                            0, min(1000, int(round(threshold * 1000)))
                        ),
                        session_count_24h=len(rates),
                        below_floor=True,
                        opted_out=False,
                    )
            except Exception:  # noqa: BLE001 (Tier-S fail-soft)
                pass
            return "red", f"cache_coverage {avg:.2f} < {threshold}", {
                "avg_rate": avg,
                "samples": len(rates),
            }
        return "green", f"cache_coverage {avg:.2f} ok", {
            "avg_rate": avg,
            "samples": len(rates),
        }
    except Exception as exc:  # noqa: BLE001 (Tier-S fail-soft)
        return "yellow", f"cache_discipline_alerted error: {exc}", None


# PLAN-093 Wave C.5/C.6 canonical persona × task matrix.
#
# S127 cadence-amendment (Codex R2 thread `019e33a3` AMEND verdict
# `PHASE-1+2-WITH-(c)`): the 4×4 matrix is demoted from gate-eligible to
# permanent observability. RED authority moves to a future event-driven
# demand ledger (`PLAN-104-persona-demand-ledger`); see
# `PLAN-093-FOLLOWUP-cadence-amendment.md` for the full doctrine record.
_VETO_FLOOR_PERSONAS = (
    "code-reviewer", "security-engineer", "qa-architect",
    "threat-detection-engineer",
)
_PERSONA_TASK_TYPES = ("review", "vet", "test", "detect")
_VETO_FLOOR_PERSONAS_LOWER = frozenset(p.lower() for p in _VETO_FLOOR_PERSONAS)

# PLAN-112-FOLLOWUP-persona-routing-wire W4 — F-5.4-tasktype-pollution.
# `_score_persona_coverage` previously counted task_type from ANY audit
# event whose archetype matched a VETO-floor persona. Unrelated emitters
# (notably `model_routing_advised`, which carries archetype + a bogus
# task_type like `frontmatter`/`M`) inflated the denominator + skewed cells.
# Restrict contributing events to the GENUINE persona-dispatch actions:
#   - `persona_coverage_synthesized` (SPEC/v1/audit-log.schema.md:319 —
#     carries `archetype` + `task_type`, the only fields the scorer reads)
#   - `persona_demand_*` (the persona-demand ledger family; PLAN-104)
# NOTE: `persona_dispatch` does NOT exist and must not be referenced.
_PERSONA_DISPATCH_ACTION_PREFIXES = ("persona_demand_",)
_PERSONA_DISPATCH_ACTIONS = frozenset({"persona_coverage_synthesized"})


def _is_persona_dispatch_event(ev: Dict[str, Any]) -> bool:
    """True iff `ev` is a genuine persona-dispatch event (F-5.4 filter).

    Defensive: a missing/non-str `action` -> False (excluded).
    """
    action = ev.get("action")
    if not isinstance(action, str):
        return False
    if action in _PERSONA_DISPATCH_ACTIONS:
        return True
    return any(action.startswith(p) for p in _PERSONA_DISPATCH_ACTION_PREFIXES)


def _normalize_persona_role(ev: Dict[str, Any]) -> str:
    """Case-folded canonical role extracted from any audit_log emission surface.

    PLAN-093 Wave C.5 originally read only ``archetype`` / ``persona``. Codex
    R2 thread `019e33a3` AMEND #4: audit-log events emitted from
    ``audit_log.py`` carry the role on ``subagent_type`` (canonical) and
    ``dispatch_archetype_hint`` (resolved-from-prompt) — narrow read missed
    those surfaces. First non-empty match wins, case-folded.
    """
    for field in ("archetype", "persona", "subagent_type",
                  "dispatch_archetype_hint"):
        val = ev.get(field)
        if isinstance(val, str) and val.strip():
            return val.strip().lower()
    return ""
