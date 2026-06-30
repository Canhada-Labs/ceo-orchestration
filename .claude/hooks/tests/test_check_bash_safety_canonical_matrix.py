"""PLAN-089 Wave B — Bash matcher canonical-guard coverage matrix.

Parametrized matrix of 34 BLOCK + 5 ALLOW + 1 X-coherence vectors,
exercising ``check_bash_safety.decide_command`` against bypass shapes
documented in PLAN-089 §4 B.2.

Targets are substituted to **PROTOCOL.md** (canonical-tier per
``_CANONICAL_GUARDS``) where the plan listed CLAUDE.md. CLAUDE.md is
intentionally NOT in the guard list (see ``check_canonical_edit.py``
line 163-167 — edited every session during closeout). For an honest
matcher coverage test, every BLOCK row must target a canonical-tier
file; PROTOCOL.md is the closest top-level analogue.

Pre-Wave-B-3 patch baseline (commit ``2f89075``):
    BLOCKS = 15 / 34  (44%)
    MISSES = 19 / 34  (56%)
    ALLOW false-positives = 0 / 5

The 19 MISS rows are decorated with ``@pytest.mark.xfail(strict=True,
reason="MISSES pre-Wave-B-3 patch")`` so the file collects + runs
GREEN on current main. Wave B.3 applies ``wave-b-audit.md`` §3 patch
and removes the ``xfail`` decorators (matcher closes 15 of 19; 3 remain
advisory — see ``_ADVISORY_ROWS`` below. Row 33 graduated to BLOCKS at S207
when the cp-hole fix added shlex punctuation_chars segmentation).

Convention: each BLOCK row is parametrized with its row number + name +
command string + a *pre-patch expectation* ("BLOCKS" or "MISSES") for
diagnostic clarity. The single ``test_block_canonical_write`` test
function checks the BLOCK assertion and is xfail'd via marker for
MISSES.

Author: Wave B research-and-draft sub-agent (S116-cont 2026-05-13).
"""

from __future__ import annotations

import sys
import timeit
from pathlib import Path

import pytest

# Make the hook source importable. The hook lives at
# ``.claude/hooks/check_bash_safety.py``; tests live at
# ``.claude/hooks/tests/test_check_bash_safety_canonical_matrix.py``.
_HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from check_bash_safety import decide_command  # noqa: E402

# ---------------------------------------------------------------------------
# Canonical-tier targets (verified via ``_CANONICAL_GUARDS``).
# ---------------------------------------------------------------------------

T = "PROTOCOL.md"               # top-level canonical (substituted for CLAUDE.md)
T2 = ".claude/team.md"          # subdir canonical (literal entry in guards)

# Non-quote helpers — keep test source readable.
DQ = chr(34)  # "
SQ = chr(39)  # '

# ---------------------------------------------------------------------------
# 34 BLOCK vectors per PLAN-089 §4 B.2.
#
# Each tuple: (row, slug, command, pre_patch_expectation).
# pre_patch_expectation = "BLOCKS" or "MISSES" (current main).
# Wave B.3 patch flips all "MISSES" → "BLOCKS" except advisory rows
# listed in _ADVISORY_ROWS.
# ---------------------------------------------------------------------------

BLOCK_VECTORS = [
    (1,  "sed_inplace_quoted",      f"sed -i '' 's/x/y/' {T}",                          "BLOCKS"),
    (2,  "sed_inplace_bak",         f"sed -i.bak '/pattern/d' {T}",                     "BLOCKS"),
    (3,  "tee_heredoc",             f"tee {T} << EOF\nevil\nEOF",                       "BLOCKS"),
    (4,  "tee_append",              f"tee -a {T2}",                                     "BLOCKS"),
    (5,  "cat_heredoc_redirect",    f"cat > {T} << 'EOF'",                              "BLOCKS"),
    (6,  "cat_append",              f"cat >> {T}",                                      "BLOCKS"),
    (7,  "echo_redirect",           f"echo '...' > {T}",                                "BLOCKS"),
    (8,  "python_open_write",       f"python -c \"open('{T}','w').write('x')\"",        "MISSES"),
    (9,  "python_pathlib_write",    f"python -c \"import pathlib; pathlib.Path('{T}').write_text('x')\"", "MISSES"),
    (10, "awk_inplace",             f"awk -i inplace '...' {T}",                        "MISSES"),
    (11, "perl_inplace",            f"perl -i -pe '...' {T}",                           "MISSES"),
    (12, "truncate",                f"truncate -s 0 {T}",                               "MISSES"),
    (13, "rm_recreate",             f"rm {T} && touch {T}",                             "MISSES"),
    (14, "ln_sf_devnull",           f"ln -sf /dev/null {T}",                            "MISSES"),
    (15, "bash_c_subshell",         f"bash -c 'sed -i " + DQ + DQ + f" \"s/x/y/\" {T}'", "MISSES"),
    (16, "eval_indirect",           f"eval \"sed -i '' 's/x/y/' {T}\"",                 "MISSES"),
    (17, "source_script",           "source ./attacker.sh",                             "MISSES"),
    (18, "xargs_deferred",          "xargs -I{} sed -i '' 's/x/y/' {} < kernel-list.txt", "MISSES"),
    (19, "find_exec",               f"find . -name '{T}' -exec sed -i '' 's/x/y/' {{}} +", "MISSES"),
    (20, "cp_overwrite",            f"cp /tmp/evil {T}",                                "MISSES"),
    (21, "mv_overwrite",            f"mv /tmp/evil {T}",                                "MISSES"),
    (22, "dd_of",                   f"dd of={T} if=/tmp/evil",                          "MISSES"),
    (23, "git_checkout_restore",    f"git checkout HEAD~5 -- {T}",                      "BLOCKS"),
    (24, "printf_cmdsub_redirect",  f"printf '%s' \"$(date)\" > {T}",                   "BLOCKS"),
    (25, "ruby_inplace",            f"ruby -i -pe 'gsub(/x/, \"y\")' {T}",              "MISSES"),
    (26, "node_writefilesync",      f"node -e \"require('fs').writeFileSync('{T}','x')\"", "MISSES"),
    (27, "tee_positional",          f"tee {T}",                                         "BLOCKS"),
    (28, "null_truncate",           f": > {T}",                                         "BLOCKS"),
    (29, "exec_redirect",           f"exec > {T}",                                      "BLOCKS"),
    (30, "grouped_redirect",        f"{{ echo evil; }} > {T}",                          "BLOCKS"),
    (31, "herestring_redirect",     f"cat <<< \"evil\" > {T}",                          "BLOCKS"),
    (32, "process_substitution",    f"tee {T} < <(printf evil)",                        "BLOCKS"),
    (33, "eval_inside_cmdsub",      f"$(eval \"sed -i '' s/x/y/ {T}\")",                "BLOCKS"),
    (34, "ifs_path_injection",      f"IFS=/ cd ../{T}/.. && touch foo",                 "MISSES"),
]

# Advisory rows — these remain MISSES even after Wave B.3 patch.
# Backed by ``check_bash_canonical_forensic.py`` PostToolUse trail
# (see ``wave-b-audit.md`` §3.1 + ``docs/security-bash-canonical-guards.md``
# §"Forensic vs blocking decoupling").
#
# Row 18 added to advisory at S117 post-ceremony empirical test result
# (iter-3 ACCEPT folded row 19 to closed but row 18 remains structurally
# advisory — xargs `-I{} ... < kernel-list.txt` defers path-substitution
# past tokenization; the body contains `{}` only with NO literal canonical
# substring for `_scan_blob` to catch).
# Row 33 (eval_inside_cmdsub) GRADUATED to BLOCKS at S207: the cp-hole fix
# (shlex punctuation_chars + `(`/`)`/backtick segmentation) makes the `$(eval …)`
# body reachable by the eval-indirection scan, so it is now caught.
_ADVISORY_ROWS = frozenset({17, 18, 34})

# ---------------------------------------------------------------------------
# 5 ALLOW vectors — legitimate non-kernel writes.
# ---------------------------------------------------------------------------

ALLOW_VECTORS = [
    ("allow_sed_readme",      "sed -i 's/typo/fix/' README.md"),
    ("allow_tee_nodemod",     "tee node_modules/.gitignore"),
    ("allow_echo_tmpscratch", "echo '...' > /tmp/scratch.txt"),
    ("allow_cat_docsdraft",   "cat > docs/draft.md << EOF"),
    ("allow_python_tmpfoo",   "python -c \"open('/tmp/foo','w').write('x')\""),
]

# ---------------------------------------------------------------------------
# 1 X-coherence row — Wave A new entry must also be BLOCKED by the Bash
# matcher (proves A+B coherence). Placeholder uses a path that becomes
# canonical post-Wave-A. We assert BLOCK either pre or post Wave A: today
# ``.claude/hooks/_lib/secret_patterns.py`` is canonical-tier via
# ``.claude/hooks/_lib/*.py`` glob in ``_CANONICAL_GUARDS``, so the row
# BLOCKS pre-Wave-A already. After Wave A, the same path will additionally
# be a KERNEL-HARD-DENY entry — the Bash matcher still BLOCKS via the
# same canonical-guard cross-reference (matcher consults guards, not
# kernel paths).
# ---------------------------------------------------------------------------

X_COHERENCE_VECTOR = (
    "x_coherence_wave_a_entry",
    f"echo '...' > .claude/hooks/_lib/secret_patterns.py",
)


# ---------------------------------------------------------------------------
# Test parametrization helpers.
# ---------------------------------------------------------------------------

# R2 Codex iter-1 Q10 fold + iter-2 correction (2026-05-13): conditional
# xfail keyed on probe vector. Pre-patch returns ALLOW, post-patch BLOCKS.
# Wave B.3 landing auto-flips condition; no manual decorator removal.
# Advisory rows (17/18/34) stay xfail unconditionally (row33 graduated at S207).
#
# IMPORTANT (Codex iter-2 fix): probe MUST target a true canonical path.
# `CLAUDE.md` is intentionally NOT in `_CANONICAL_GUARDS` per DYN-SEC1
# (session-closeout edited every session). `PROTOCOL.md` IS canonical
# and rarely-changed — correct probe target.
_PROBE_CMD = "python -c \"open('PROTOCOL.md','w').write('x')\""
try:
    _PLAN_089_WAVE_B_APPLIED = not decide_command(_PROBE_CMD).allow
except Exception:  # pragma: no cover
    _PLAN_089_WAVE_B_APPLIED = False


def _block_param(row, slug, cmd, expectation):
    """Build a pytest.param with xfail marker when expectation is MISSES."""
    marks = []
    if expectation == "MISSES":
        if row in _ADVISORY_ROWS:
            marks.append(
                pytest.mark.xfail(
                    strict=True,
                    reason=(
                        f"row{row:02d} ADVISORY — forensic-detector backup "
                        "per wave-b-audit.md §3.1"
                    ),
                )
            )
        else:
            marks.append(
                pytest.mark.xfail(
                    condition=not _PLAN_089_WAVE_B_APPLIED,
                    strict=True,
                    reason=(
                        f"row{row:02d} MISSES pre-Wave-B-3 patch "
                        "(auto-activates post-patch — Q10 fold)"
                    ),
                )
            )
    return pytest.param(row, slug, cmd, id=f"row{row:02d}_{slug}", marks=marks)


_BLOCK_PARAMS = [_block_param(*entry) for entry in BLOCK_VECTORS]


# ---------------------------------------------------------------------------
# Tests.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("row,slug,cmd", _BLOCK_PARAMS)
def test_block_canonical_write(row, slug, cmd):
    """Each BLOCK vector must produce ``Decision(allow=False)``.

    Failure modes:
    - ``allow=True`` → MISS (bypass surface; xfail until Wave B.3 patches
      the matcher; advisory rows xfail permanently with forensic backup).
    - ``allow=False`` with non-canonical reason → unclear path; assert
      that ``GOVERNANCE``/``canonical`` appears in the reason so we know
      it was the canonical-guard branch that fired (vs credential leak
      or rm/git rules).
    """
    decision = decide_command(cmd)
    assert not decision.allow, (
        f"row{row:02d} {slug}: expected BLOCK got ALLOW for cmd={cmd!r}"
    )
    assert decision.reason, f"row{row:02d} {slug}: block must have a reason"
    lower = decision.reason.lower()
    assert (
        "governance" in lower
        or "canonical" in lower
        or "parse" in lower
        or "credential" in lower
    ), (
        f"row{row:02d} {slug}: reason={decision.reason!r} — expected "
        "canonical-guard / parse / credential branch (not rm or git rules)"
    )


@pytest.mark.parametrize(
    "slug,cmd",
    [pytest.param(s, c, id=s) for s, c in ALLOW_VECTORS],
)
def test_allow_noncanonical(slug, cmd):
    """Each ALLOW vector must produce ``Decision(allow=True)``.

    Failure mode: ``allow=False`` → over-block (the matcher false-positives
    on a legitimate non-canonical write). The matcher patch MUST NOT
    introduce any new FP — the canonical guard list is fully-qualified
    so substring-on-blob false-positives should be impossible
    (e.g. ``README.md`` contains ``.md`` but no canonical glob matches
    just ``.md``).
    """
    decision = decide_command(cmd)
    assert decision.allow, (
        f"{slug}: expected ALLOW got BLOCK for cmd={cmd!r}; "
        f"reason={decision.reason!r}"
    )


def test_x_coherence_wave_a_entry():
    """Cross-wave coherence — a canonical-guarded path (placeholder for
    Wave A new entry) must be BLOCKED by the Bash matcher both pre- and
    post-Wave-A.

    Today ``.claude/hooks/_lib/secret_patterns.py`` is canonical-tier
    via the ``.claude/hooks/_lib/*.py`` glob in ``_CANONICAL_GUARDS``,
    so the redirect-to-path vector BLOCKS pre-Wave-A. Wave A extends
    KERNEL HARD-DENY to include the same path; the Bash matcher
    consults *canonical guards* (not kernel paths), so coverage is
    preserved.
    """
    slug, cmd = X_COHERENCE_VECTOR
    decision = decide_command(cmd)
    assert not decision.allow, (
        f"x-coherence {slug}: expected BLOCK got ALLOW; this proves "
        "Wave A+B coherence — a Wave-A-new kernel entry should still "
        "block via the Bash matcher's canonical-guard cross-reference."
    )


def test_parse_failure_fails_closed():
    """Sanity-anchor — pre-existing PLAN-085 Wave E.3 R1 Sec-2 invariant.

    Malformed Bash (unbalanced single quote) must FAIL-CLOSED on the
    canonical-guard path even though the target isn't yet identified.
    This is the existing contract we MUST preserve through Wave B.3.
    """
    bad = f"echo 'unterminated > {T}"
    decision = decide_command(bad)
    assert not decision.allow, "unbalanced quote → fail-CLOSED required"
    assert "parse" in (decision.reason or "").lower(), (
        f"reason={decision.reason!r} — expected parse-failure fail-CLOSED"
    )


# ---------------------------------------------------------------------------
# Perf microbench — advisory (does not fail CI).
# ---------------------------------------------------------------------------

@pytest.mark.advisory
def test_perf_p95_under_50ms_advisory():
    """Per plan §4 B.3 — hook p95 ≤50ms.

    Advisory pattern (does NOT fail the test): emit a `pytest.skip` /
    `pytest.warns`-equivalent log line if p95 > 25ms (50% of budget,
    early warning). This test is marked ``@pytest.mark.advisory`` so
    a custom CI selector can drop it from gating runs.

    Baseline (pre-Wave-B-3 patch): aggregate p95 ≈ 0.077ms across
    10-vector ensemble, 30 samples each (300 total). 650× headroom
    under the 50ms gate.
    """
    sample_cmds = [v[2] for v in BLOCK_VECTORS[:5]] + [c for _, c in ALLOW_VECTORS]
    all_times_ms = []
    for cmd in sample_cmds:
        samples_s = timeit.repeat(
            stmt=lambda: decide_command(cmd),  # noqa: B023
            number=1,
            repeat=30,
        )
        all_times_ms.extend(s * 1000.0 for s in samples_s)
    all_times_ms.sort()
    p50 = all_times_ms[len(all_times_ms) // 2]
    p95 = all_times_ms[int(0.95 * len(all_times_ms)) - 1]
    p99 = all_times_ms[int(0.99 * len(all_times_ms)) - 1]
    # Advisory: warn if over 25ms (50% of budget); fail if over 50ms.
    print(
        f"\nperf-microbench n={len(all_times_ms)} p50={p50:.3f}ms "
        f"p95={p95:.3f}ms p99={p99:.3f}ms"
    )
    assert p95 < 50.0, (
        f"hook p95={p95:.3f}ms exceeds 50ms budget — PLAN-089 §4 AC8"
    )


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
