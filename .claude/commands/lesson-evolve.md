---
description: Cluster accrued lessons into SP-NNN skill-patch drafts — /lesson-evolve
allowed-tools: Bash
---

# /lesson-evolve — instinct → skill promotion pipeline (PLAN-154 item 7)

Deterministically clusters the LIVE lessons store (Jaccard similarity
over `scope_tags` — $0 model spend) and, on explicit confirmation,
drafts one `SP-NNN` skill-patch proposal per resolved cluster via the
EXISTING ADR-031 pipeline (`skill-patch-propose.py`, CR1 scans intact).
Proposals are inert drafts under `.claude/proposals/` — the ONLY
activation path is the Owner running `/skill-review` (approve → shadow
→ 7-day soak → promote). Nothing self-activates.

Backing script: `.claude/scripts/lesson_evolve.py`.

## Arguments received

`/lesson-evolve $ARGUMENTS`

- no args → dry-run cluster report (writes NOTHING)
- `--propose` → draft SP-NNN proposals for resolved clusters
- `--threshold <0..1>` → Jaccard threshold (default 0.5)
- `--min-cluster <n>` → minimum cluster size (default 2)

## Procedure

### Step 1 — Dry-run report (always first)

```bash
python3 .claude/scripts/lesson_evolve.py
```

Print the report. It is deterministic (byte-identical on re-run against
an unchanged store — no timestamps), so the user can diff runs. Each
cluster shows: stable cluster id, size, dominant archetype, tag union,
resolved `target_skill` (or `(unresolved)`), and member lesson
one-liners. Only lessons with a LIVE status are scanned — PENDING /
QUARANTINED / EXPIRED candidates from the PLAN-154 learning loop never
feed a skill patch.

### Step 2 — Confirm before proposing

Do NOT proceed to `--propose` unless the user explicitly confirms after
seeing the dry-run report. Proposing writes `SP-NNN-*.md` draft files
under `.claude/proposals/` (still inert, but they consume proposal
sequence numbers and queue Owner review work).

### Step 3 — Propose

```bash
python3 .claude/scripts/lesson_evolve.py --propose
```

Per cluster, the script stages bounded lesson summaries and shells out
to `skill-patch-propose.py`, which re-runs the full CR1 defense set
(injection scan, bidi/zero-width, homoglyph, long-line, fenced
executable code, 200-line diff cap). A cluster whose lessons fail CR1
is REJECTED there (an `SP-REJECTED-*.md` audit stub is written) — report
that to the user; do not retry blindly.

### Step 4 — Hand off to /skill-review

Relay the script's hand-off block verbatim:

```
/skill-review list
/skill-review approve SP-NNN --confirm "I have read SP-NNN" --signature <path>
```

The 7-day soak + promote flow is documented in `skill-review.md`. This
command's job ends at the hand-off — approval authority is the Owner's.

## Exit codes

- `0` — report rendered; all attempted proposals drafted (or dry-run)
- `1` — at least one propose subprocess failed (see per-cluster notes)

## Safety notes

- `CEO_SOTA_DISABLE=1` → the script is a no-op (exit 0), matching the
  `skill-patch-propose.py` posture. The skill-patch sentinel stays
  active regardless.
- Clustering is deterministic v1 (consensus A15): no model call, no
  network, no token spend.
- Unresolved clusters are never auto-assigned a skill — the report says
  `(unresolved — pick a skill manually)` and the propose pass skips
  them.
