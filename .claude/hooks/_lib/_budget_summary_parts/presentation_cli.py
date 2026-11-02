from __future__ import annotations

def load_transcripts_instrument():
    """Import `ceo-cost-transcripts.py` from next to this file, or None.

    Fail-soft by construction: an unimportable instrument degrades the
    primary source to a labelled note, it never breaks the audit rollup.
    """
    cached = sys.modules.get(_TRANSCRIPTS_MODULE_NAME)
    if cached is not None:
        return cached
    src = Path(__file__).resolve().parent / _TRANSCRIPTS_FILENAME
    if not src.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(
            _TRANSCRIPTS_MODULE_NAME, src
        )
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        # Registered BEFORE exec_module: with `from __future__ import
        # annotations`, @dataclass resolves sys.modules[cls.__module__] at
        # class-definition time and blows up on a missing entry.
        sys.modules[_TRANSCRIPTS_MODULE_NAME] = mod
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        sys.modules.pop(_TRANSCRIPTS_MODULE_NAME, None)
        return None


def transcripts_root(root_arg: Optional[str] = None) -> Optional[Path]:
    """Resolve the transcripts corpus root (flag > env > shared resolver)."""
    mod = load_transcripts_instrument()
    if mod is None:
        return Path(root_arg) if root_arg else None
    return mod.resolve_root(root_arg)


def _tx_audit_pinned(path_arg: Optional[str] = None) -> bool:
    """True when the SECONDARY (audit) ledger was pointed at a specific
    place — by flag or by CEO_AUDIT_LOG_PATH / CEO_AUDIT_LOG_DIR. Rail r3
    P1-1: a flag is not the only carrier, and the cross-project pairing only
    EXISTS when both ledgers are on screen.
    """
    mod = load_transcripts_instrument()
    if mod is None:
        return bool(path_arg)
    return mod.audit_source_is_pinned(
        path_arg, carriers=_AUDIT_ENV_CARRIERS
    )


def collect_transcripts(
    root_arg: Optional[str] = None,
    cutoff: Optional[datetime] = None,
    audit_override: bool = False,
) -> Dict[str, Any]:
    """Primary-source rollup, or a `{"available": False, "reason": ...}` note.

    `budget-summary` has no `--by` flag, so the breakdown dimension is fixed
    to `model` — the same dimension its audit-side `per_plan` table is most
    comparable against. `audit_override` says `--audit-dir` pointed the
    SECONDARY source at an explicit path; with no explicit transcripts root
    that pairing crosses projects and is refused by name (rail r2 P1-1).
    """
    mod = load_transcripts_instrument()
    if mod is None:
        return {
            "available": False,
            "reason": "instrument ceo-cost-transcripts.py is not importable",
        }
    return mod.collect(
        root_arg=root_arg,
        cutoff=cutoff,
        by="model",
        audit_override=audit_override,
    )


def format_human(data: Dict[str, Any], memory_claim: Optional[Dict[str, Any]] = None) -> str:
    """Render the rollup as a human-readable text block.

    PLAN-186 W0 (AC-1b): when `data` carries a `source` key the PRIMARY
    transcripts block is rendered first, labelled; `source == 'audit'`
    sets NO key at all, so that rendering is byte-identical to the
    pre-integration one.
    """
    lines: List[str] = []
    source = data.get("source")
    if source is not None:
        mod = load_transcripts_instrument()
        if mod is None:
            lines.append(
                "transcripts source UNAVAILABLE: instrument "
                "ceo-cost-transcripts.py is not importable"
            )
        else:
            lines.extend(mod.render_block(data.get("transcripts")))
        lines.append("")
        if source == "transcripts":
            return "\n".join(lines)
        lines.append(AUDIT_BANNER)
        lines.append("")
    scope = data.get("plan_filter") or "(all plans)"
    since = data.get("since") or "(all time)"
    lines.append(f"FinOps summary — scope={scope} since={since}")
    lines.append("-" * 70)
    lines.append(f"Audit dir       : {data.get('audit_dir')}")
    files = data.get("log_files_read") or []
    lines.append(f"Logs read       : {len(files)} file(s)")
    for f in files:
        lines.append(f"                  - {f}")
    lines.append(f"Events          : {data['total_events']:>14,}")
    lines.append(f"Codex events    : {data['codex_event_count']:>14,}")
    lines.append(f"Unknown plan_id : {data['unknown_plan_count']:>14,}")
    lines.append(f"Tokens in       : {_fmt_tokens(data['total_tokens_in'])}")
    lines.append(f"Tokens out      : {_fmt_tokens(data['total_tokens_out'])}")
    lines.append(f"Tokens total    : {_fmt_tokens(data['total_tokens'])}")
    cost = data.get("total_cost_usd")
    src = data.get("cost_source") or "unknown"
    if cost is None:
        lines.append(f"Cost (USD)      : -              (source={src})")
    else:
        lines.append(f"Cost (USD)      : ${cost:>13,.4f} (source={src})")

    per_plan = data.get("per_plan") or []
    if per_plan and not data.get("plan_filter"):
        lines.append("")
        lines.append("Per plan:")
        lines.append(
            f"  {'plan_id':<14}  {'events':>7}  {'tokens_total':>14}  "
            f"{'cost_usd':>12}"
        )
        for row in per_plan:
            cost_col = (
                f"${row['cost_usd']:.4f}" if row.get("cost_known") else "-"
            )
            lines.append(
                f"  {row['plan_id']:<14}  {row['event_count']:>7,}  "
                f"{row['tokens_total']:>14,}  {cost_col:>12}"
            )

    per_wave = data.get("per_wave")
    if per_wave:
        lines.append("")
        lines.append("Per wave:")
        lines.append(
            f"  {'wave':<14}  {'events':>7}  {'tokens_total':>14}  "
            f"{'cost_usd':>12}"
        )
        for row in per_wave:
            cost_col = f"${row['cost_usd']:.4f}" if row['cost_usd'] else "-"
            lines.append(
                f"  {row['wave']:<14}  {row['event_count']:>7,}  "
                f"{row['tokens_total']:>14,}  {cost_col:>12}"
            )

    # PLAN-133 C4 — harbor-style benchmark co-report (only when --benchmarks).
    benchmarks = data.get("benchmarks")
    if benchmarks is not None:
        rows = benchmarks.get("per_skill") or []
        lines.append("")
        lines.append("Benchmarks (harbor-style — pass-rate never read alone):")
        if not rows:
            lines.append("  (no benchmark_run events in scope)")
        else:
            lines.append(
                f"  {'skill':<24}  {'runs':>4}  {'pass_rate':>9}  "
                f"{'cost_usd':>10}  {'compute_s':>10}  {'turns':>7}"
            )
            for row in rows:
                lines.append(
                    f"  {str(row['skill'])[:24]:<24}  {row['runs']:>4}  "
                    f"{row['latest_pass_rate']:>9.3f}  "
                    f"${row['total_cost_usd']:>9.4f}  "
                    f"{row['total_compute_s']:>10.1f}  "
                    f"{row['total_turns']:>7,}"
                )
            lines.append(
                f"  {'TOTAL':<24}  {'':>4}  {'':>9}  "
                f"${benchmarks['total_cost_usd']:>9.4f}  "
                f"{benchmarks['total_compute_s']:>10.1f}  "
                f"{benchmarks['total_turns']:>7,}"
            )

    # PLAN-178 W1.2 — native cross-check (only when --native / env opt-in).
    native = data.get("native_cross_check")
    if native is not None:
        lines.extend(_format_native_block(native))

    if memory_claim is not None:
        lines.append("")
        lines.append("Memory-claim validation:")
        lines.append(f"  status  : {memory_claim['status']}")
        lines.append(f"  message : {memory_claim['message']}")
        # Rail r2 P2-2: say WHICH ledger the verdict is about. Only when
        # a second ledger is on screen — audit-only output is unchanged.
        if data.get("source") is not None:
            lines.append(
                "  scope   : validates the AUDIT total (SECONDARY); the "
                "transcripts total above is the PRIMARY figure"
            )

    return "\n".join(lines)


def format_json(data: Dict[str, Any], memory_claim: Optional[Dict[str, Any]] = None) -> str:
    payload = dict(data)
    if memory_claim is not None:
        payload["memory_claim_validation"] = memory_claim
    return json.dumps(payload, indent=2, sort_keys=True)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="budget-summary",
        description=(
            "FinOps rollup across all audit-log rotations "
            "(PLAN-083 Wave 0b sub-0.8)."
        ),
    )
    sub = p.add_subparsers(dest="subcommand")

    sp = sub.add_parser("summary", help="Print cumulative summary.")
    sp.add_argument("--since", metavar="EXPR", default=None,
                    help="Time window (Nm/Nh/Nd, e.g. 30d).")
    sp.add_argument("--plan-id", metavar="PLAN-NNN", default=None,
                    help="Limit rollup to a single plan_id.")
    sp.add_argument("--by-wave", action="store_true",
                    help="Include per-wave aggregates.")
    sp.add_argument("--json", action="store_true",
                    help="Emit JSON (default: human table).")
    sp.add_argument("--validate-memory-claim", action="store_true",
                    help="Cross-check rollup against CLAUDE.md memory claim band.")
    sp.add_argument("--audit-dir", metavar="PATH", default=None,
                    help="Override audit-log directory.")
    # PLAN-133 C4 — default-OFF harbor-style benchmark co-report.
    sp.add_argument("--benchmarks", action="store_true",
                    help=(
                        "Append a harbor-style benchmark co-report "
                        "(cost + compute + turns alongside pass-rate per "
                        "skill). Default-OFF; also enabled by "
                        "CEO_BUDGET_BENCHMARKS=1 (PLAN-133 C4)."
                    ))
    # PLAN-178 W1.2 — default-OFF native-source cross-check.
    sp.add_argument("--native", action="store_true",
                    help=(
                        "Append the native-source cross-check: audit-log "
                        "agent_spawn ledger joined against the harness "
                        "transcript corpus under ~/.claude/projects/"
                        "<cwd-slug>/. Cross-check, not authority-swap; "
                        "UNMATCHED residue on both sides is always shown. "
                        "Default-OFF; also enabled by CEO_BUDGET_NATIVE=1 "
                        "(PLAN-178 W1.2)."
                    ))
    sp.add_argument("--native-root", metavar="PATH", default=None,
                    help=(
                        "Override the native transcript root (default: "
                        "~/.claude/projects/<cwd-slug>; env override "
                        "CEO_NATIVE_USAGE_DIR)."
                    ))
    # PLAN-186 W0 (AC-1b) — the two-source surface.
    sp.add_argument("--source", choices=SOURCE_CHOICES, default="both",
                    help=(
                        "Which ledger to report. 'transcripts' = "
                        "harness-native message.usage (PRIMARY, "
                        "cache-aware); 'audit' = the governance audit "
                        "log (SECONDARY, byte-identical to the "
                        "pre-PLAN-186 output); 'both' (default) prints "
                        "them labelled, side by side."
                    ))
    sp.add_argument("--transcripts-root", metavar="PATH", default=None,
                    help=(
                        "Transcripts corpus root. Default: $%s, else the "
                        "shared _lib.runtime_paths resolver. Distinct "
                        "from --native-root, which feeds the older "
                        "--native cross-check." % ROOT_ENV
                    ))
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 2

    if args.subcommand is None:
        # Default to "summary" when invoked bare.
        args.subcommand = "summary"
        args.since = None
        args.plan_id = None
        args.by_wave = False
        args.json = False
        args.validate_memory_claim = False
        args.audit_dir = None
        args.benchmarks = False
        args.native = False
        args.native_root = None
        args.source = "both"
        args.transcripts_root = None

    if args.subcommand != "summary":
        sys.stderr.write(f"budget-summary: unknown subcommand {args.subcommand!r}\n")
        return 2

    since_delta: Optional[timedelta] = None
    if args.since:
        try:
            since_delta = parse_since(args.since)
        except ValueError as e:
            sys.stderr.write(f"budget-summary: {e}\n")
            return 2

    if args.plan_id and not _PLAN_ID_RE.match(args.plan_id):
        sys.stderr.write(
            f"budget-summary: --plan-id must look like PLAN-NNN "
            f"(got {args.plan_id!r})\n"
        )
        return 2

    audit_dir = Path(args.audit_dir) if args.audit_dir else None

    # Rail r3 P2-1: ONE wall clock for both ledgers. `rollup()` captures
    # its own `now` internally; taking a second one after it returns let
    # a record land inside the audit window and outside the transcripts
    # window while both blocks printed the same `--since`.
    _now = datetime.now(timezone.utc)

    # PLAN-186 W0 (AC-1b): the PRIMARY source. `--source audit` adds NO
    # key to `data`, which is what keeps that rendering byte-identical.
    source = getattr(args, "source", "audit")
    # Rail r1 P1-2: the transcript corpus carries NO plan field (the same
    # limitation the --native cross-check hit in S306). A project-wide
    # transcripts total printed as PRIMARY beside a plan-scoped audit
    # block is the wrong number for the plan that was asked about. Under
    # --plan-id it is suppressed; an EXPLICIT --source transcripts there
    # is a named refusal, never a silently unscoped answer.
    if source != "audit" and getattr(args, "plan_id", None):
        if source == "transcripts":
            sys.stderr.write(
                "budget-summary: --source transcripts cannot be scoped "
                "by --plan-id (the transcript corpus has no plan "
                "field); drop one of the two flags\n"
            )
            return 2
        sys.stderr.write(
            "budget-summary: transcripts source suppressed under "
            "--plan-id (the transcript corpus has no plan field; run "
            "without --plan-id to see it)\n"
        )
        source = "audit"
    # Rail r2 P2-2: --validate-memory-claim compares the AUDIT total
    # against CLAUDE.md's claim band; under --source transcripts there is
    # no audit total to validate, and returning 'unknown' would look like
    # a verdict. Named refusal instead.
    if source == "transcripts" and getattr(
        args, "validate_memory_claim", False
    ):
        sys.stderr.write(
            "budget-summary: --validate-memory-claim validates the AUDIT "
            "total and cannot run under --source transcripts; use "
            "--source both or audit\n"
        )
        return 2
    if source == "transcripts":
        # Rail S341 (A): --by-wave shapes the AUDIT rollup (wave_hint
        # on agent_spawn rows). With rollup() skipped there is no block
        # to shape, so the flag is DROPPED -- named on stderr, never
        # silently swallowed, exactly like the two co-reports below.
        if getattr(args, "by_wave", False):
            sys.stderr.write(
                "budget-summary: --by-wave shapes the AUDIT rollup and "
                "is dropped under --source transcripts (the transcript "
                "corpus has no wave field); use --source both or "
                "audit\n"
            )
        data: Dict[str, Any] = {"since": args.since}
    else:
        data = rollup(
            audit_dir=audit_dir,
            plan_filter=args.plan_id,
            since=since_delta,
            by_wave=args.by_wave,
            # Rail S341 r1 [P2]: capturing `_now` and letting rollup()
            # take its own clock delivers HALF of D10 -- a record on the
            # window boundary could still land inside one ledger and
            # outside the other while both blocks print the same --since.
            now=_now,
        )
        data["since"] = args.since
    if source != "audit":
        data["source"] = source
        data["transcripts"] = collect_transcripts(
            root_arg=getattr(args, "transcripts_root", None),
            cutoff=(
                _now - since_delta if since_delta is not None else None
            ),
            audit_override=(
                source == "both"
                and _tx_audit_pinned(
                    str(audit_dir) if audit_dir is not None else None
                )
            ),
        )

    # PLAN-133 C4 — default-OFF benchmark co-report. Enabled by --benchmarks
    # or CEO_BUDGET_BENCHMARKS=1. When OFF, output is byte-for-byte unchanged.
    benchmarks_on = bool(getattr(args, "benchmarks", False)) or (
        os.environ.get("CEO_BUDGET_BENCHMARKS", "") == "1"
    )
    # Both co-reports are AUDIT-side; under --source transcripts there is
    # no audit rollup to append them to. Rail S341 (A): a REQUESTED
    # block that vanishes with rc 0 and an empty stderr is the shape
    # this pack removed everywhere else -- so it is dropped by NAME,
    # mirroring the CEO_NATIVE_COST_DISABLE / --plan-id lines below.
    if source == "transcripts":
        if benchmarks_on:
            sys.stderr.write(
                "budget-summary: --benchmarks is an AUDIT-side "
                "co-report and is dropped under --source transcripts; "
                "use --source both or audit\n"
            )
        benchmarks_on = False
    if benchmarks_on:
        data["benchmarks"] = benchmark_rollup(
            audit_dir=audit_dir,
            since=since_delta,
        )

    # PLAN-178 W1.2 — default-OFF native cross-check. Enabled by --native or
    # CEO_BUDGET_NATIVE=1. When OFF, output is byte-for-byte unchanged (and
    # a dormant corpus degrades to a one-line dormant note, never a crash).
    # Note: the cross-check is session-scoped; --plan-id does NOT filter it
    # (the native corpus carries no plan_id field — probe §handoff item 6).
    native_on = bool(getattr(args, "native", False)) or (
        os.environ.get("CEO_BUDGET_NATIVE", "") == "1"
    )
    if source == "transcripts":
        if native_on:
            sys.stderr.write(
                "budget-summary: --native is an AUDIT-side cross-check "
                "and is dropped under --source transcripts; use "
                "--source both or audit\n"
            )
        native_on = False
    # Kill-switch (W1.2-5b, env-inventory.json): dominates the opt-in.
    if native_on and os.environ.get("CEO_NATIVE_COST_DISABLE", "") == "1":
        native_on = False
        sys.stderr.write(
            "budget-summary: native cross-check disabled by "
            "CEO_NATIVE_COST_DISABLE=1\n"
        )
    # codex S306 P2 cure: the native source carries no plan field (probe
    # §handoff item 6), so under --plan-id an unscoped cross-check would put
    # every plan's native activity inside a plan-scoped report. Suppress it.
    if native_on and getattr(args, "plan_id", None):
        native_on = False
        sys.stderr.write(
            "budget-summary: native cross-check suppressed under --plan-id "
            "(native source has no plan field; run without --plan-id to "
            "see it)\n"
        )
    if native_on:
        native_root = (
            Path(args.native_root)
            if getattr(args, "native_root", None)
            else None
        )
        data["native_cross_check"] = native_cross_check(
            audit_dir=audit_dir,
            native_root=native_root,
            since=since_delta,
        )

    memory_claim: Optional[Dict[str, Any]] = None
    if args.validate_memory_claim:
        memory_claim = validate_memory_claim(data.get("total_cost_usd"))

    if args.json:
        print(format_json(data, memory_claim))
    else:
        print(format_human(data, memory_claim))
    return 0



