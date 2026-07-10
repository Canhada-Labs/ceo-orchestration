# PLAN-155 Wave 6 — inverted pair-rail + advisory-rail teeth (build notes)

Staged under `.claude/plans/PLAN-155/staged/wave-6/`. Bases used (three-layer
rule): the codex host adapter/seam consumed is **wave-1** staged
(`_lib/adapters/{__init__,codex}.py`); the Stop-block wire semantics are the
**observed** codex-cli 0.139.0 wire (`stop-block-transcript.md` +
`normalization-notes.md`), not docs; `templates/codex/hooks.json` base is the
**wave-2** staged copy (Stop entry extended). No PLAN-154 sent-f file is in
this wave's scope. No repo-tree edits — all staged.

## Files (exclusive scope)

| file | class | ceremony |
|---|---|---|
| `.claude/hooks/check_codex_stop_review.py` | [CANONICAL] (new hook; NOT in `_KERNEL_PATHS` — verified) | SENT-CX-D sentinel scope; **no** kernel-override needed for this file |
| `.claude/hooks/tests/test_codex_stop_review.py` | [UNGUARDED-COMPANION] | rides same commit (incl. pre-push gate behavioral tests) |
| `.claude/hooks/tests/test_codex_advisory_teeth.py` | [UNGUARDED-COMPANION] | rides same commit |
| `templates/codex/hooks.json` | [TEMPLATE] (wave-2 base + Stop-review registration) | lands direct (unguarded) |
| `templates/codex/pre-push-review-gate.sh` | [TEMPLATE] (third `.git/` install surface) | lands direct; installer emits to `.git/hooks/pre-push` (Wave 5 lifecycle-symmetry) |
| `scripts/codex-advisory-teeth.py` | unguarded script | lands direct |
| `ceremony-riders/validate-yml-advisory-teeth.diff` | KERNEL rider (validate.yml `:135`) | Owner applies with `CEO_KERNEL_OVERRIDE=PLAN-155-CODEX-PAIRRAIL-TEETH` + ACK |

## What is proven (test commands + results, 2026-07-10)

- `python3 -m pytest .claude/plans/PLAN-155/staged/wave-6/.claude/hooks/tests/ -q`
  → **40 passed**, env unset AND `CEO_HOOK_ADAPTER=codex`. Python 3.9.6 floor:
  all four wave-6 py files `py_compile` clean.
- **Subprocess codex-wire controls** (S254 anti-dead-gate): the shipped hook
  run as a subprocess under `CEO_HOOK_ADAPTER=codex` on a composed overlay →
  canonical edit + no record ⇒ `{"decision":"block", ...}`; matching APPROVE
  record ⇒ allow; non-canonical ⇒ allow; **mutation control**: wrong-fingerprint
  record still blocks. A separate mutation control (neuter
  `latest_review_record`) turns 5 allow/APPROVE assertions RED — the gate has
  teeth.
- **advisory-teeth**: activity-without-boot-breadcrumb ⇒ RED + exit 1;
  boot breadcrumb clears it; spawn-without-SubagentStart ⇒ advisory (never
  fails the run); `--advisory-only` never exits non-zero.
- **pre-push gate** (`shellcheck -S warning` clean): canonical commit + no
  record ⇒ exit 1; `Pair-Rail-Reviewed: APPROVE` trailer clears; matching
  sidecar APPROVE clears; non-canonical passes; `--advisory` never blocks.
- **validate.yml rider**: `git apply --check` clean @ `9096813`; resulting
  YAML parses; actionlint adds no new findings.
- **LIVE-FIRE** (`wave6-stop-rail-livefire.md`): real `codex exec` 0.139.0
  session editing a canonical path → Stop #1 (`stop_hook_active:false`)
  blocked, codex auto-continued → Stop #2 (`stop_hook_active:true`) allowed
  with the RED-on-absence breadcrumb. Isolated CODEX_HOME; operator config
  untouched; mirrored credential deleted after the turn.

## Design decisions (for ADR-161 / the lander)

- **Two-phase gate matching the verified Stop-block primitive.** The hook
  never runs `claude -p` inline (a multi-minute subprocess in a Stop hook
  would hit the timeout → silent fail-open allow, the S254 class). Instead it
  emits a block with a copy-paste reviewer pipeline; the reviewer verdict is
  recorded via `--record` (its own testable mode) into a session+fingerprint
  keyed review-log; the next Stop reads it.
- **Fail-OPEN on Stop, not fail-closed.** A Stop hook is NOT a security edit
  matcher; a Stop-block on a garbled envelope would wedge every session. Parse
  error / import failure / git-absent ⇒ allow. The honesty layer is the
  RED-on-absence breadcrumbs, not a fail-closed block.
- **Reviewer pin PROVISIONAL (OQ3):** `claude-opus-4-8`, 100k token ceiling,
  overrides `CEO_PAIR_RAIL_REVIEWER_MODEL` / `CEO_PAIR_RAIL_REVIEWER_MAX_TOKENS`.
  Wave 7 lands the `docs/provider-pricing.md`-consistent row.

## Open issues (for the manifest / lander)

1. **MANIFEST-A does not yet list a wave-6 section.** Add the file table above
   (the prove/verify pass owns MANIFEST-A). Landing order: wave-6 lands AFTER
   wave-1 (host adapter/seam) and wave-2 (templates) are on main — the Stop
   hook imports the wave-1 seam and the subprocess test overlays it; the
   pre-push gate + hooks.json depend on the wave-2 template surface.
2. **Reviewer-provenance not attested** (named residual): `--record` reads the
   reviewer's stdout and cannot prove `claude -p` produced it (an operator
   could pipe `echo APPROVE`). Backstops: pre-push + CI + CODEOWNERS. Record
   in ADR-161's failure-semantics matrix.
3. **Path-set fingerprint, not content** (named residual): a review record is
   keyed to the sorted canonical PATH SET; re-editing the same files after an
   APPROVE could ride a stale record within one session. Finer layers: the
   next-Stop re-review + CI. Record in ADR-161.
4. **Session→commit bridge is loose:** the Stop hook records the working-tree
   L3 path-set fingerprint; a single pushed commit's canonical set may be a
   subset, so the pre-push sidecar-match path (b) is best-effort. The
   commit-trailer path (a) is the git-native primary and the ONLY one that
   survives a fresh clone / works in CI. Documented in the gate header.
5. **Git-worktree discovery gap** (0.139, MANIFEST-A #2) reconfirmed live: the
   Stop live-fire required a plain repo. Substrate-watch per-bump item; Wave 5
   arming check must warn; Wave 7 docs must name it.
6. **mcp__* spawn/tool interception still unrecorded** (no MCP server in the
   lab) — unchanged from wave-1 open issue #5.
7. **Wave 7 docs owe the direction-neutral same-vendor wording** — supplied in
   `same-vendor-caveat-inverted.md`; land into HONEST-LIMITATIONS +
   provider_capability_matrix + adapters + ADR-161.
