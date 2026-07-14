#!/usr/bin/env bash
# =============================================================================
# land-plan157-graduation.sh — PLAN-157 W2/W3 graduation ceremonies
# (Owner runs via `!`). ONE parametrized script, FOUR independent
# go/no-go ceremonies, each its own signed commit:
#
#     W2:  jvm, cpp          W3:  golang, data-ml
#
# Usage:
#     bash .claude/plans/PLAN-157/land-plan157-graduation.sh <squad> [--dry-run] [--apply-sp047]
#         <squad>        one of: jvm | cpp | golang | data-ml
#         --dry-run      preflight + plan report only; mutates NOTHING,
#                        requires NO gpg (gh/network degrade to warnings)
#         --apply-sp047  data-ml only: apply the SP-047 prisma-patterns
#                        move (git mv + one-line frontmatter edit) inside
#                        this ceremony, ahead of the bundle copy
#
# Pattern: land-plan157-w1.sh lineage — the sentinel is CREATED AND SIGNED
# AT THE CEREMONY (before running this) and this script only VERIFIES it.
# The script applies the staged bundle MECHANICALLY and never thinks; every
# number it writes is DERIVED FROM DISK at apply time (waves may run in any
# order relative to W1 — no count is assumed, no literal is hardcoded).
#
# ⚠ PREREQUISITES (Owner, at the ceremony, BEFORE running this):
#   1. Owner go/no-go for THIS squad (PLAN-157 §Approach — per-squad, no
#      sunk-cost commitment). data-ml additionally requires the explicit
#      ack recorded in its sentinel body (+2 skills vs OQ5 wording).
#   2. Graduation sentinel: $SENTINEL_DIR/approved.md with
#      Anchor-SHA = current HEAD and the Scope block from the pre-authored
#      body (.claude/plans/PLAN-157/architect/grad-<squad>/approved.body.md),
#      detach-signed to approved.md.asc.
#      Default dir: .claude/plans/PLAN-157/architect/grad-<squad>
#      (override with PLAN157_GRAD_SENTINEL_DIR=<dir>).
#   3. data-ml + --apply-sp047: Owner .asc sibling for SP-047 next to the
#      staged .md (soak waiver = the Owner's detach signature, OQ4).
#   4. Validate green on HEAD (checked via `gh run list`).
#
# Landing order (single commit per squad):
#   [0] preflight       (clean tree, main==origin/main, Validate green,
#                        sentinel GPG-verified + anchored at HEAD, bundle
#                        integrity, surface pre-check, roster pre-check)
#   [1] SP-047          (data-ml only — move prisma-patterns, hash-pinned)
#   [2] bundle copy     (MERGE, strictly additive: existing canonical
#                        skills stay; only NEW files copied; never deletes)
#   [3] roster triplet  (SQUAD_GRANDFATHER − squad; policy member removed,
#                        current−1, cap := current per OQ3 + comment
#                        refresh; _EXPECTED_DOMAIN_CAP := cap — ONE commit)
#   [4] count reconcile (totals derived FROM DISK, replaced into the 8
#                        reconcile surfaces; old value read from each file)
#   [5] regen           (COMMAND-SKILL-HOOK-MAP --write; skill inventory
#                        re-embed between markers + --check)
#   [6] FULL gate set   (12 gates incl. the ADR-009 bundle validator and
#                        the full pytest — no gate skipped)
#   [7] scope assert    (touched − scope = ∅, or no commit)
#   [8] git add exact list + single `git commit -S` (NO auto-push)
#
# S272-P1 rider: NOTHING under a gitignored staged/ path is ever passed to
# `git add` (silently-skipped class). The ADD list is asserted against
# `git check-ignore` before staging.
#
# NOTE: the Owner-shell apply route (cp/git/sed here) does not trip the
# in-session canonical hooks — those gate Claude's tool calls, not the
# Owner's shell. The signed sentinel IS the authorization record (S261
# precedent); the guarded files this script rewrites (grandfather-cap
# policy, CLAUDE.md, core ceo-orchestration SKILL.md, domains/** writes)
# are covered by it.
# =============================================================================
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO"

# --- args --------------------------------------------------------------------
SQUAD="${1:-}"
DRY=0
APPLY_SP047=0
shift || true
for arg in "$@"; do
  case "$arg" in
    --dry-run)      DRY=1 ;;
    --apply-sp047)  APPLY_SP047=1 ;;
    *) echo "FATAL: unknown argument: $arg" >&2; exit 2 ;;
  esac
done

case "$SQUAD" in
  jvm)     WAVE="W2"; NEW_SKILLS=(jvm-testing) ;;
  cpp)     WAVE="W2"; NEW_SKILLS=(cpp-build-systems) ;;
  golang)  WAVE="W3"; NEW_SKILLS=(golang-testing golang-services) ;;
  data-ml) WAVE="W3"; NEW_SKILLS=(ml-evaluation-patterns ml-serving-patterns) ;;
  *)
    echo "usage: $0 <jvm|cpp|golang|data-ml> [--dry-run] [--apply-sp047]" >&2
    exit 2
    ;;
esac
if [ "$APPLY_SP047" = 1 ] && [ "$SQUAD" != "data-ml" ]; then
  echo "FATAL: --apply-sp047 is only valid with the data-ml ceremony" >&2
  exit 2
fi
SENT_TAG="SENT-GRAD-$(printf '%s' "$SQUAD" | tr '[:lower:]' '[:upper:]')"
DRY_LABEL=""
[ "$DRY" = 1 ] && DRY_LABEL=" [DRY-RUN]"

# --- constants ---------------------------------------------------------------
BUNDLE=".claude/plans/PLAN-157/staged/$SQUAD"          # gitignored, machine-local
DEST=".claude/skills/domains/$SQUAD"
SENTINEL_DIR="${PLAN157_GRAD_SENTINEL_DIR:-.claude/plans/PLAN-157/architect/grad-$SQUAD}"
KEY="AE9B236FDAF0462874060C6BCFCFACF00335DC74"
CORE_SKILL=".claude/skills/core/ceo-orchestration/SKILL.md"
VG=".claude/scripts/validate-governance.sh"
# (the grandfather-cap policy + cap-test paths live inside roster_triplet.py)

# SP-047 (data-ml precondition — OQ5 resolution; see the SP for mechanics)
SP047_FILE="SP-047-prisma-patterns-saas-platforms-move-2026-07-13.md"
SP047_STAGED=".claude/plans/PLAN-157/staged/w1/proposals/$SP047_FILE"
SP047_SRC=".claude/skills/domains/data-ml/skills/prisma-patterns"
SP047_DST=".claude/skills/domains/saas-platforms/skills/prisma-patterns"
# pre-move source pin (cross-asserted against the SP's own prose in preflight)
SP047_SRC_PIN="0eaa69c7a77f9f91927c1c5dacc3d7b3149c61e7f4396b3a7d483aa9772695bd"

export GPG_TTY="${GPG_TTY:-$(tty || true)}"

say()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m    WARN: %s\033[0m\n' "$*"; }
die()  { printf '\n\033[1;31mFATAL: %s\033[0m\n' "$*" >&2; exit 1; }
sha()  { shasum -a 256 "$1" | awk '{print $1}'; }
fm()   { sed -n "s/^$2: *//p" "$1" | head -1 | sed 's/[[:space:]]*#.*$//; s/[[:space:]]*$//'; }

# --- count derivation: ALWAYS from disk, never a literal ----------------------
count_total()  { find .claude/skills/core .claude/skills/frontend .claude/skills/domains -type f -name SKILL.md | wc -l | tr -d ' '; }
count_domain() { find .claude/skills/domains -type f -name SKILL.md | wc -l | tr -d ' '; }
count_squad()  { find "$DEST/skills" -mindepth 2 -maxdepth 2 -type f -name SKILL.md 2>/dev/null | wc -l | tr -d ' '; }

# --- failure trap: never leave a dirty repo without a restore hint ------------
CLEAN_HEAD=""
MUTATING=0
COMMITTED=0
TMP_CEREMONY="$(mktemp -d)"
on_exit() {
  local rc=$?
  rm -rf "$TMP_CEREMONY"
  if [ "$rc" -ne 0 ] && [ "$MUTATING" -eq 1 ] && [ "$COMMITTED" -eq 0 ]; then
    {
      printf '\n\033[1;33mABORTED MID-APPLY — the repo is dirty; NOTHING was committed or pushed.\033[0m\n'
      printf 'Restore the pre-ceremony state (tree was verified clean at preflight):\n'
      printf '    git reset --hard %s\n' "$CLEAN_HEAD"
      printf '    git clean -nd %s .claude/proposals   # inspect, then -fd to drop copies\n' "$DEST"
      printf 'The staged bundle under %s is read-only input and was not modified.\n' "$BUNDLE"
    } >&2
  fi
  return "$rc"
}
trap on_exit EXIT

gpg_verify_owner() { # <detached.asc> <file>
  local out
  out="$(gpg --status-fd 1 --verify "$1" "$2" 2>/dev/null || true)"
  printf '%s\n' "$out" | grep -q "^\[GNUPG:\] VALIDSIG .*$KEY" \
    || die "GPG verification failed for $2 (need VALIDSIG by $KEY)"
  echo "    GPG OK: $2"
}

# --- helper programs (written once, invoked in check/plan AND apply modes) ----
ROSTER_PY="$TMP_CEREMONY/roster_triplet.py"
cat > "$ROSTER_PY" <<'PY'
"""Roster triplet edit: SQUAD_GRANDFATHER, grandfather-cap policy, cap test.

argv: <plan|apply> <squad> <wave>
plan  — validate everything, print "CUR NEWCUR CAP NEWCAP", write nothing.
apply — same validation, then write all three files (two-phase).
Every number is read from the files themselves; nothing is assumed.
"""
import re
import sys

mode, squad, wave = sys.argv[1], sys.argv[2], sys.argv[3]
VG = ".claude/scripts/validate-governance.sh"
POLICY = ".claude/policies/grandfather-cap.policy.yaml"
CAP_TEST = ".claude/scripts/tests/test_squad_grandfather_cap.py"

# --- 1. SQUAD_GRANDFATHER token removal (validate-governance.sh) -------------
vg_text = open(VG, encoding="utf-8").read()
matches = re.findall(r'(?m)^SQUAD_GRANDFATHER="([^"]*)"$', vg_text)
if len(matches) != 1:
    sys.exit("FATAL: expected exactly 1 SQUAD_GRANDFATHER assignment, found %d" % len(matches))
tokens = matches[0].split()
if squad not in tokens:
    sys.exit("FATAL: %s not in SQUAD_GRANDFATHER — already graduated?" % squad)
if len(tokens) != len(set(tokens)):
    sys.exit("FATAL: duplicate tokens in SQUAD_GRANDFATHER")
new_tokens = [t for t in tokens if t != squad]
vg_new = vg_text.replace(
    'SQUAD_GRANDFATHER="%s"' % matches[0],
    'SQUAD_GRANDFATHER="%s"' % " ".join(new_tokens),
)

# --- 2. policy: member removed, current-1, cap := current, comments ----------
plines = open(POLICY, encoding="utf-8").read().splitlines(keepends=True)
start = None
end = len(plines)
for i, ln in enumerate(plines):
    if ln.rstrip("\n") == "domain_bundles:":
        start = i
    elif start is not None and i > start and ln.strip() and ln[0] not in " \t#":
        end = i
        break
if start is None:
    sys.exit("FATAL: domain_bundles: section not found in policy")
cap_i = cur_i = mem_i = None
cap = cur = None
for i in range(start, end):
    s = plines[i]
    m = re.match(r"^(\s*)cap:\s*(\d+)\s*$", s)
    if m:
        cap_i, cap = i, int(m.group(2))
    m = re.match(r"^(\s*)current:\s*(\d+)\s*$", s)
    if m:
        cur_i, cur = i, int(m.group(2))
    if re.match(r"^\s*- %s\s*$" % re.escape(squad), s):
        if mem_i is not None:
            sys.exit("FATAL: duplicate policy member line for %s" % squad)
        mem_i = i
if cap_i is None or cur_i is None:
    sys.exit("FATAL: could not locate domain_bundles cap:/current: lines")
if mem_i is None:
    sys.exit("FATAL: policy member line for %s not found — roster surfaces diverged?" % squad)
new_cur = cur - 1
new_cap = new_cur  # OQ3 (Owner-ratified): cap := current at every wave boundary
history = (
    "  # cap lowered %d→%d (PLAN-157 %s graduation: %s — full ADR-009\n"
    "  # bundle landed, squad off the roster; OQ3 cap := current).\n"
    % (cap, new_cap, wave, squad)
)
out = []
for i, ln in enumerate(plines):
    if i == mem_i:
        continue  # member line removed
    if i == cap_i:
        out.append(history)
        out.append(re.sub(r"\d+", str(new_cap), ln, count=1))
        continue
    if i == cur_i:
        out.append(re.sub(r"\d+", str(new_cur), ln, count=1))
        continue
    if start < i < end:
        # best-effort stale-comment refresh (roster counts stated in prose)
        ln = re.sub(r"\b\d+ entries\b", "%d entries" % new_cur, ln)
        ln = re.sub(r"\b(\d+) remaining\b", lambda m: "%d remaining" % (int(m.group(1)) - 1), ln)
        ln = ln.replace("= %d)" % cur, "= %d)" % new_cur)
    out.append(ln)
pol_new = "".join(out)
# post-edit name-level set-equality (the pytest tamper rider re-checks later)
sec = pol_new.split("domain_bundles:", 1)[1].split("sunset_reopen_window_days", 1)[0]
members_after = re.findall(r"(?m)^\s*- ([a-z0-9-]+)\s*$", sec)
if set(members_after) != set(new_tokens):
    sys.exit(
        "FATAL: post-edit roster mismatch (policy vs bash array), symmetric diff: %s"
        % sorted(set(members_after) ^ set(new_tokens))
    )

# --- 3. cap test: _EXPECTED_DOMAIN_CAP := new cap -----------------------------
t_text = open(CAP_TEST, encoding="utf-8").read()
tm = re.findall(r"(?m)^_EXPECTED_DOMAIN_CAP = (\d+)", t_text)
if len(tm) != 1:
    sys.exit("FATAL: expected exactly 1 _EXPECTED_DOMAIN_CAP assignment, found %d" % len(tm))
if int(tm[0]) != cap:
    sys.exit("FATAL: _EXPECTED_DOMAIN_CAP (%s) != policy cap (%d) BEFORE edit — pre-existing drift" % (tm[0], cap))
marker = "# PLAN-157 %s graduation (%s): cap %d→%d (OQ3 cap := current).\n" % (wave, squad, cap, new_cap)
t_new = re.sub(
    r"(?m)^_EXPECTED_DOMAIN_CAP = \d+",
    marker + "_EXPECTED_DOMAIN_CAP = %d" % new_cap,
    t_text,
    count=1,
)

if mode == "plan":
    print(cur, new_cur, cap, new_cap)
    sys.exit(0)

# --- apply: all computed and validated, now write all (two-phase) -------------
open(VG, "w", encoding="utf-8").write(vg_new)
open(POLICY, "w", encoding="utf-8").write(pol_new)
open(CAP_TEST, "w", encoding="utf-8").write(t_new)
print("    roster %d->%d names; policy current %d->%d, cap %d->%d; test cap := %d"
      % (len(tokens), len(new_tokens), cur, new_cur, cap, new_cap, new_cap))
PY

COUNTS_PY="$TMP_CEREMONY/reconcile_counts.py"
cat > "$COUNTS_PY" <<'PY'
"""Count-literal reconcile across the 8 PLAN-157 surfaces.

argv: <check|apply> <pre_total> <post_total> <pre_domain> <post_domain>
check — assert every surface carries the CURRENT on-disk numbers on a
        skill-line (pass post==pre); write nothing.
apply — replace pre->post on skill-lines, two-phase (validate all files,
        then write all files); print every changed line.
The old value is READ FROM EACH FILE (found-or-fail); the new value is
derived from disk by the caller. No number is assumed.
"""
import io
import re
import sys

mode = sys.argv[1]
pre_t, post_t, pre_d, post_d = (int(x) for x in sys.argv[2:6])
SURFACES = [  # (path, domain-literal required on some skill-line?)
    ("CLAUDE.md", True),
    ("README.md", True),
    ("INSTALL.md", True),
    ("docs/ARCHITECTURE.md", True),
    ("docs/GUIA-COMPLETO.md", False),
    ("docs/GUIA-COMPLETO.pt-BR.md", False),
    (".claude/scripts/local/verify-counts.sh", True),
    (".claude/skills/core/ceo-orchestration/SKILL.md", True),
]
rx_skill = re.compile(r"skill", re.I)
rx_t = re.compile(r"\b%d\b" % pre_t)
rx_d = re.compile(r"\b%d\b" % pre_d)
staged = []
fail = False
for path, need_domain in SURFACES:
    with io.open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines(keepends=True)
    n_t = n_d = 0
    out = []
    for ln in lines:
        if rx_skill.search(ln):
            ln2, k = rx_t.subn(str(post_t), ln)
            n_t += k
            ln3, k = rx_d.subn(str(post_d), ln2)
            n_d += k
            if mode == "apply" and ln3 != ln:
                sys.stdout.write("    %s: %s" % (path, ln3 if ln3.endswith("\n") else ln3 + "\n"))
            out.append(ln3)
        else:
            out.append(ln)
    if n_t < 1:
        print("FATAL: %s: skills-total literal %d not found on any skill-line" % (path, pre_t))
        fail = True
    if need_domain and n_d < 1:
        print("FATAL: %s: domain-count literal %d not found on any skill-line" % (path, pre_d))
        fail = True
    staged.append((path, "".join(out)))
if fail:
    sys.exit(1)
if mode == "apply":
    for path, text in staged:  # two-phase: validated all above, write all now
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
PY

# =============================================================================
# [0/8] Preflight
# =============================================================================
say "[0/8] Preflight — graduate '$SQUAD' ($WAVE)$DRY_LABEL"
[ "$(git rev-parse --abbrev-ref HEAD)" = "main" ] || die "not on main"
if [ -n "$(git status --porcelain=v1)" ]; then
  if [ "$DRY" = 1 ]; then
    warn "working tree not clean — a REAL run will refuse to start"
  else
    git status --short >&2
    die "working tree not clean — commit/stash unrelated changes first"
  fi
fi
CLEAN_HEAD="$(git rev-parse HEAD)"

say "[0/8] Preflight: main up to date with origin"
if git fetch origin main --quiet 2>/dev/null; then
  if [ "$CLEAN_HEAD" != "$(git rev-parse origin/main)" ]; then
    if [ "$DRY" = 1 ]; then
      warn "local main != origin/main — sync before the real ceremony"
    else
      die "local main ($CLEAN_HEAD) != origin/main — sync first (git pull --ff-only) or push"
    fi
  fi
else
  [ "$DRY" = 1 ] || die "git fetch origin main failed — network/auth?"
  warn "git fetch failed (offline?) — tolerated in dry-run only"
fi

say "[0/8] Preflight: Validate green on HEAD ($CLEAN_HEAD)"
if command -v gh >/dev/null 2>&1 \
   && _runs_json="$(gh run list --workflow validate.yml --branch main --limit 30 --json headSha,status,conclusion 2>/dev/null)"; then
  _state="$(printf '%s' "$_runs_json" | python3 -c '
import json, sys
head = sys.argv[1]
runs = [r for r in json.load(sys.stdin) if r.get("headSha") == head]
print((str(runs[0].get("status")) + "/" + str(runs[0].get("conclusion"))) if runs else "none/none")
' "$CLEAN_HEAD")"
  if [ "$_state" != "completed/success" ]; then
    if [ "$DRY" = 1 ]; then
      warn "Validate on HEAD is '$_state' — must be completed/success at the real ceremony"
    else
      die "Validate on HEAD is '$_state' (need completed/success) — wait for CI before landing"
    fi
  else
    echo "    Validate: completed/success"
  fi
else
  [ "$DRY" = 1 ] || die "gh run list failed (is gh authenticated?)"
  warn "gh unavailable — Validate-green check skipped (dry-run only)"
fi

say "[0/8] Preflight: staged bundle integrity ($BUNDLE)"
[ -d "$BUNDLE" ] || die "staged bundle missing: $BUNDLE (machine-local — was it built on this machine?)"
for f in team-personas.md pitfalls.yaml task-chains.yaml rationale.md; do
  [ -f "$BUNDLE/$f" ] || die "staged bundle file missing: $BUNDLE/$f"
done
[ "$(find "$BUNDLE/examples" -maxdepth 1 -type f -name '*.md' 2>/dev/null | wc -l | tr -d ' ')" -ge 1 ] \
  || die "staged bundle has no examples/*.md"
# staged skills/ must contain EXACTLY the expected new skills for this squad
_staged_skills="$(find "$BUNDLE/skills" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sed 's|.*/||' | sort | tr '\n' ' ')"
_want_skills="$(printf '%s\n' "${NEW_SKILLS[@]}" | sort | tr '\n' ' ')"
[ "$_staged_skills" = "$_want_skills" ] \
  || die "staged skills/ dirs ($_staged_skills) != expected new skills ($_want_skills) — bundle/script drift"
for s in "${NEW_SKILLS[@]}"; do
  [ -f "$BUNDLE/skills/$s/SKILL.md" ] || die "staged skill missing SKILL.md: $BUNDLE/skills/$s"
done
# MERGE is strictly additive: every staged file's canonical target must NOT exist
[ -d "$DEST" ] || die "canonical squad tree missing: $DEST — graduation MERGES into it, never creates it"
_collisions=""
while IFS= read -r rel; do
  if [ -e "$DEST/$rel" ]; then
    _collisions="$_collisions $DEST/$rel"
  fi
done < <(cd "$BUNDLE" && find . -type f ! -name rationale.md | sed 's|^\./||' | sort)
[ -z "$_collisions" ] \
  || die "bundle collision — canonical file(s) already exist (additive-only merge):$_collisions"
echo "    bundle OK: 3 core files + examples + skills/{${NEW_SKILLS[*]}} — all targets new (rationale.md stays in staging)"

say "[0/8] Preflight: roster pre-check (numbers derived from disk)"
_plan_out="$(python3 "$ROSTER_PY" plan "$SQUAD" "$WAVE")" \
  || die "roster plan derivation failed (see message above)"
read -r CUR NEWCUR CAP NEWCAP <<<"$_plan_out"
[ -n "${NEWCAP:-}" ] || die "roster plan derivation returned nothing"
echo "    roster plan: current $CUR -> $NEWCUR; cap $CAP -> $NEWCAP (OQ3 cap := current); _EXPECTED_DOMAIN_CAP -> $NEWCAP"

say "[0/8] Preflight: count-surface pre-check (disk vs the 8 reconcile surfaces)"
PRE_TOTAL="$(count_total)"
PRE_DOMAIN="$(count_domain)"
PRE_SQUAD="$(count_squad)"
python3 "$COUNTS_PY" check "$PRE_TOTAL" "$PRE_TOTAL" "$PRE_DOMAIN" "$PRE_DOMAIN" \
  || die "count-surface pre-check FAILED — a reconcile surface disagrees with disk (did W1 land? was an earlier graduation pushed?). Reconcile before graduating."
echo "    disk: total=$PRE_TOTAL domain=$PRE_DOMAIN ${SQUAD}-skills=$PRE_SQUAD — all 8 surfaces agree"

if [ "$SQUAD" = "data-ml" ]; then
  say "[0/8] Preflight: SP-047 precondition (OQ5 — prisma-patterns home)"
  if [ "$APPLY_SP047" = 1 ]; then
    [ -f "$SP047_STAGED" ] || die "staged SP missing: $SP047_STAGED"
    grep -qF "$SP047_SRC_PIN" "$SP047_STAGED" \
      || die "SP-047 does not carry the expected pre-move source pin — SP/script drift"
    [ -d "$SP047_SRC" ] || die "--apply-sp047 given but $SP047_SRC is absent (already applied? drop the flag)"
    [ ! -e "$SP047_DST" ] || die "--apply-sp047 given but $SP047_DST already exists"
    [ "$(sha "$SP047_SRC/SKILL.md")" = "$SP047_SRC_PIN" ] \
      || die "pre-move $SP047_SRC/SKILL.md sha256 != SP-047 source pin — base drifted; REBUILD the SP"
    [ "$(find "$SP047_SRC" -type f | wc -l | tr -d ' ')" = "1" ] \
      || die "$SP047_SRC contains more than SKILL.md — SP-047 move contract assumes a single file"
    if [ "$DRY" = 1 ]; then
      if [ -f "$SP047_STAGED.asc" ]; then
        echo "    SP-047 signature present (GPG-verified at the real run)"
      else
        warn "SP-047 Owner signature missing — detach-sign before the real run: gpg --local-user $KEY --armor --detach-sign $SP047_STAGED"
      fi
    else
      [ -f "$SP047_STAGED.asc" ] \
        || die "missing Owner signature $SP047_STAGED.asc — detach-sign at the ceremony (OQ4 soak waiver = your signature)"
      gpg_verify_owner "$SP047_STAGED.asc" "$SP047_STAGED"
    fi
    echo "    SP-047 ready to apply (source pin OK)"
  else
    [ -f "$SP047_DST/SKILL.md" ] \
      || die "SP-047 NOT applied ($SP047_DST/SKILL.md absent). data-ml graduates ONLY after the prisma move (OQ5). Re-run with --apply-sp047, or land the move first."
    [ ! -e "$SP047_SRC" ] \
      || die "SP-047 half-applied: $SP047_SRC still exists next to $SP047_DST — resolve before graduating"
    echo "    SP-047 already applied (dst present, src absent)"
  fi
fi

say "[0/8] Preflight: graduation sentinel at $SENTINEL_DIR"
if [ "$DRY" = 1 ]; then
  if [ -f "$SENTINEL_DIR/approved.md" ] && [ -f "$SENTINEL_DIR/approved.md.asc" ]; then
    echo "    sentinel + signature present (GPG verify happens at the real run)"
  else
    warn "sentinel not signed yet — at the ceremony: cp $SENTINEL_DIR/approved.body.md $SENTINEL_DIR/approved.md; fill __ANCHOR_SHA__ with HEAD; gpg --local-user $KEY --armor --detach-sign $SENTINEL_DIR/approved.md"
  fi
else
  gpg --list-secret-keys "$KEY" >/dev/null 2>&1 || die "signing key $KEY not in your keyring"
  [ -f "$SENTINEL_DIR/approved.md" ]     || die "sentinel missing: $SENTINEL_DIR/approved.md (create from approved.body.md + sign at the ceremony first)"
  [ -f "$SENTINEL_DIR/approved.md.asc" ] || die "sentinel signature missing: $SENTINEL_DIR/approved.md.asc"
  gpg_verify_owner "$SENTINEL_DIR/approved.md.asc" "$SENTINEL_DIR/approved.md"
  _anchor="$(sed -n 's/^Anchor-SHA: *//p' "$SENTINEL_DIR/approved.md" | head -1)"
  [ "$_anchor" = "$CLEAN_HEAD" ] \
    || die "sentinel Anchor-SHA ($_anchor) != HEAD ($CLEAN_HEAD) — re-sign the sentinel at current HEAD"
  grep -q 'PLAN-157' "$SENTINEL_DIR/approved.md" || die "sentinel does not reference PLAN-157"
  _scope_block="$(sed -n '/^Scope:/,/END SIGNED SCOPE/p' "$SENTINEL_DIR/approved.md")"
  [ -n "$_scope_block" ] || die "sentinel has no Scope: block"
  _musts=(
    CLAUDE.md
    .claude/policies/grandfather-cap.policy.yaml
    .claude/skills/core/ceo-orchestration/SKILL.md
    ".claude/skills/domains/$SQUAD/"
  )
  if [ "$SQUAD" = "data-ml" ]; then
    _musts+=(".claude/skills/domains/saas-platforms/skills/prisma-patterns/")
  fi
  for must in "${_musts[@]}"; do
    printf '%s\n' "$_scope_block" | grep -qF "$must" \
      || die "sentinel Scope is missing guarded path: $must — fix + re-sign"
  done
  echo "    sentinel scope covers all guarded targets"
fi

# --- dry-run stops here: report the plan, mutate nothing -----------------------
if [ "$DRY" = 1 ]; then
  _n_new=${#NEW_SKILLS[@]}
  _squad_end=$((PRE_SQUAD + _n_new))
  say "[DRY-RUN] Plan for '$SQUAD' ($WAVE) — nothing was changed"
  echo "    bundle copy (additive merge into $DEST):"
  (cd "$BUNDLE" && find . -type f ! -name rationale.md | sed 's|^\./|      + |' | sort)
  if [ "$SQUAD" = "data-ml" ] && [ "$APPLY_SP047" = 1 ]; then
    echo "    SP-047: git mv $SP047_SRC -> $SP047_DST (+ frontmatter domain edit, hash-pinned)"
    _squad_end=$((_squad_end - 1))  # prisma-patterns leaves data-ml in this run
  fi
  echo "    roster:  current $CUR -> $NEWCUR; cap $CAP -> $NEWCAP; _EXPECTED_DOMAIN_CAP -> $NEWCAP"
  echo "    counts:  total $PRE_TOTAL -> $((PRE_TOTAL + _n_new)); domain $PRE_DOMAIN -> $((PRE_DOMAIN + _n_new)); $SQUAD skills $PRE_SQUAD -> $_squad_end (ADR-009 needs >=3)"
  echo "    then:    regen map+inventory, 12 gates, scope assert, ONE signed commit [$SENT_TAG]"
  echo ""
  echo "    Rehearsed OK. The real run additionally needs: signed sentinel,"
  echo "    gpg key $KEY, gh authenticated, clean tree at origin/main."
  exit 0
fi

# =============================================================================
# [1/8] SP-047 (data-ml only)
# =============================================================================
if [ "$SQUAD" = "data-ml" ] && [ "$APPLY_SP047" = 1 ]; then
  say "[1/8] Apply SP-047 — move prisma-patterns to saas-platforms (OQ5)"
  MUTATING=1
  git mv "$SP047_SRC" "$SP047_DST"
  # the one-line content delta pinned by the SP's inline diff:
  sed -i '' 's/^  domain: data-ml$/  domain: saas-platforms/' "$SP047_DST/SKILL.md"
  _want_staged="$(fm "$SP047_STAGED" sha256_of_staged)"
  _got_staged="$(sha "$SP047_DST/SKILL.md")"
  [ "$_got_staged" = "$_want_staged" ] \
    || die "post-move $SP047_DST/SKILL.md sha256 ($_got_staged) != SP-047 sha256_of_staged ($_want_staged)"
  cp "$SP047_STAGED" ".claude/proposals/$SP047_FILE"
  cp "$SP047_STAGED.asc" ".claude/proposals/$SP047_FILE.asc"
  echo "    moved + frontmatter edited (staged-hash OK); SP registered in .claude/proposals/"
else
  say "[1/8] SP-047 — n/a for this ceremony (skipped)"
fi

# =============================================================================
# [2/8] Bundle copy — MERGE, strictly additive
# =============================================================================
say "[2/8] Copy staged bundle into $DEST (existing canonical skills stay untouched)"
MUTATING=1
while IFS= read -r rel; do
  src="$BUNDLE/$rel"
  dst="$DEST/$rel"
  [ ! -e "$dst" ] || die "bundle collision mid-copy (preflight raced?): $dst"
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
  echo "    + $dst"
done < <(cd "$BUNDLE" && find . -type f ! -name rationale.md | sed 's|^\./||' | sort)
# rationale.md deliberately NOT copied (staging-only, per its own header)

# =============================================================================
# [3/8] Roster triplet — commit-atomic (roster line, policy, cap test)
# =============================================================================
say "[3/8] Roster triplet: remove '$SQUAD'; current $CUR->$NEWCUR; cap := $NEWCAP (OQ3)"
python3 "$ROSTER_PY" apply "$SQUAD" "$WAVE" || die "roster triplet edit failed"
if grep -qE "^SQUAD_GRANDFATHER=\"([^\"]* )?$SQUAD( [^\"]*)?\"$" "$VG"; then
  die "$SQUAD still on SQUAD_GRANDFATHER after edit"
fi
[ "$(grep -c '^SQUAD_GRANDFATHER=' "$VG")" = 1 ] || die "unexpected extra SQUAD_GRANDFATHER assignment"

# =============================================================================
# [4/8] Count-literal reconcile — derived FROM DISK after the copy
# =============================================================================
say "[4/8] Count reconcile across the 8 surfaces (from-disk derivation)"
POST_TOTAL="$(count_total)"
POST_DOMAIN="$(count_domain)"
POST_SQUAD="$(count_squad)"
_n_new=${#NEW_SKILLS[@]}
[ "$POST_TOTAL" = "$((PRE_TOTAL + _n_new))" ] \
  || die "post-copy total ($POST_TOTAL) != pre ($PRE_TOTAL) + new skills ($_n_new) — unexpected catalog delta"
[ "$POST_DOMAIN" = "$((PRE_DOMAIN + _n_new))" ] \
  || die "post-copy domain count ($POST_DOMAIN) != pre ($PRE_DOMAIN) + $_n_new"
[ "$POST_SQUAD" -ge 3 ] || die "$SQUAD has $POST_SQUAD skills post-copy — below the ADR-009 minimum of 3"
echo "    derived: total $PRE_TOTAL->$POST_TOTAL; domain $PRE_DOMAIN->$POST_DOMAIN; $SQUAD skills=$POST_SQUAD"
python3 "$COUNTS_PY" apply "$PRE_TOTAL" "$POST_TOTAL" "$PRE_DOMAIN" "$POST_DOMAIN" \
  || die "count-literal reconcile failed"

# =============================================================================
# [5/8] Regenerate derived surfaces
# =============================================================================
say "[5/8] Regen: COMMAND-SKILL-HOOK-MAP"
python3 .claude/scripts/gen-command-skill-hook-map.py --write \
  || die "gen-command-skill-hook-map --write failed"

say "[5/8] Regen: skill inventory block in core SKILL.md"
INV_TMP="$TMP_CEREMONY/inventory.md"
bash .claude/scripts/generate-skill-inventory.sh > "$INV_TMP" \
  || die "generate-skill-inventory.sh failed"
python3 - "$INV_TMP" "$CORE_SKILL" <<'PY'
import pathlib, sys
gen = pathlib.Path(sys.argv[1]).read_text()
skill = pathlib.Path(sys.argv[2])
lines = skill.read_text().splitlines(keepends=True)
B = "<!-- BEGIN AUTO-GENERATED SKILL INVENTORY -->"
E = "<!-- END AUTO-GENERATED SKILL INVENTORY -->"
bi = [i for i, l in enumerate(lines) if l.rstrip("\n") == B]
ei = [i for i, l in enumerate(lines) if l.rstrip("\n") == E]
if len(bi) != 1 or len(ei) != 1 or bi[0] >= ei[0]:
    sys.exit("FATAL: AUTO-GENERATED markers not found exactly once in core SKILL.md")
out = "".join(lines[: bi[0]]) + gen + "".join(lines[ei[0] + 1 :])
skill.write_text(out)
print("    re-embedded %d generated lines" % gen.count("\n"))
PY
bash .claude/scripts/generate-skill-inventory.sh --check \
  || die "skill-inventory idempotency check failed right after re-embed"

# =============================================================================
# [6/8] FULL per-wave check set (PLAN-157 §checklist — no gate skipped)
# =============================================================================
say "[6/8] Gate 1/12: validate-governance (FULL — $SQUAD now at ERROR level)"
bash .claude/scripts/validate-governance.sh || die "validate-governance red"

say "[6/8] Gate 2/12: ADR-009 bundle validator (S272 staging check, re-run on canonical)"
python3 .claude/scripts/validate-squad-contract.py --squad "$DEST" \
  || die "validate-squad-contract red for $DEST"

say "[6/8] Gate 3/12: check-claude-md-claims"
python3 .claude/scripts/check-claude-md-claims.py || die "CLAUDE.md claims red"

say "[6/8] Gate 4/12: verify-counts --no-tests"
bash .claude/scripts/local/verify-counts.sh --no-tests || die "verify-counts red"

say "[6/8] Gate 5/12: gen-command-skill-hook-map --check"
python3 .claude/scripts/gen-command-skill-hook-map.py --check || die "map drift after --write (regenerator bug?)"

say "[6/8] Gate 6/12: skill-inventory --check"
bash .claude/scripts/generate-skill-inventory.sh --check || die "skill-inventory drift"

say "[6/8] Gate 7/12: check-install-profiles (graduation keeps the squad installed — profiles.json untouched)"
python3 .claude/scripts/check-install-profiles.py || die "install-profiles red"

say "[6/8] Gate 8/12: check-docs-freshness"
python3 .claude/scripts/check-docs-freshness.py --format=text \
  || die "docs-freshness red — expected ZERO new breaks. If a link target newly broke (data-ml prisma move), append the exact bare path (one per line, #fragment stripped) to docs/docs-freshness-allowlist.txt and re-run."

say "[6/8] Gate 9/12: check-tier-boundaries"
python3 .claude/scripts/check-tier-boundaries.py || die "tier-boundaries red"

say "[6/8] Gate 10/12: registry --validate"
python3 .claude/scripts/registry.py --validate || die "registry red (routing-table skill refs?)"

say "[6/8] Gate 11/12: lint-skills --strict-yaml on the graduated squad"
python3 .claude/scripts/lint-skills.py --strict-yaml "$DEST" || die "lint-skills red for $DEST"

say "[6/8] Gate 12/12: full pytest (hooks + scripts + optimizer) — slow, not skippable"
python3 -m pytest .claude/hooks/tests/ .claude/scripts/tests/ .claude/scripts/optimizer/tests/ -q \
  || die "pytest red — do not land"

# =============================================================================
# [7/8] Scope assert: touched − scope = ∅, or no commit
# =============================================================================
say "[7/8] Scope assert (touched set vs $SENT_TAG sentinel scope)"
_scope_re='^(\.claude/skills/domains/'"$SQUAD"'/'
_scope_re+='|CLAUDE\.md$|README\.md$|INSTALL\.md$'
_scope_re+='|docs/ARCHITECTURE\.md$|docs/GUIA-COMPLETO\.md$|docs/GUIA-COMPLETO\.pt-BR\.md$'
_scope_re+='|docs/COMMAND-SKILL-HOOK-MAP\.md$'
_scope_re+='|\.claude/policies/grandfather-cap\.policy\.yaml$'
_scope_re+='|\.claude/scripts/validate-governance\.sh$'
_scope_re+='|\.claude/scripts/tests/test_squad_grandfather_cap\.py$'
_scope_re+='|\.claude/scripts/local/verify-counts\.sh$'
_scope_re+='|\.claude/skills/core/ceo-orchestration/SKILL\.md$'
if [ "$SQUAD" = "data-ml" ]; then
  _scope_re+='|\.claude/skills/domains/saas-platforms/skills/prisma-patterns/'
  _scope_re+='|\.claude/proposals/SP-047-[A-Za-z0-9.-]+\.md(\.asc)?$'
  _scope_re+='|docs/docs-freshness-allowlist\.txt$'
fi
_scope_re+='|'"${SENTINEL_DIR//./\\.}"'/)'
_touched="$(git status --porcelain=v1 -uall | sed -E 's/^.{3}//; s/^.* -> //')"
[ -n "$_touched" ] || die "nothing touched — apply phase did not run?"
_extras="$(printf '%s\n' "$_touched" | grep -Ev "$_scope_re" || true)"
if [ -n "$_extras" ]; then
  printf '%s\n' "$_extras" >&2
  die "touched files OUTSIDE the $SQUAD graduation scope — touched minus scope must be the empty set; NOT committing"
fi
echo "    touched - scope = (empty set)"

# =============================================================================
# [8/8] Single signed commit (NO auto-push)
# =============================================================================
say "[8/8] git add exact scope + git commit -S"
ADD_PATHS=(
  ".claude/skills/domains/$SQUAD"
  CLAUDE.md
  README.md
  INSTALL.md
  docs/ARCHITECTURE.md
  docs/GUIA-COMPLETO.md
  docs/GUIA-COMPLETO.pt-BR.md
  docs/COMMAND-SKILL-HOOK-MAP.md
  .claude/policies/grandfather-cap.policy.yaml
  .claude/scripts/validate-governance.sh
  .claude/scripts/tests/test_squad_grandfather_cap.py
  .claude/scripts/local/verify-counts.sh
  .claude/skills/core/ceo-orchestration/SKILL.md
  "$SENTINEL_DIR"
)
if [ "$SQUAD" = "data-ml" ]; then
  if [ "$APPLY_SP047" = 1 ]; then
    # the data-ml side of the rename was staged by `git mv` in [1/8]
    ADD_PATHS+=(
      .claude/skills/domains/saas-platforms/skills/prisma-patterns
      ".claude/proposals/$SP047_FILE"
      ".claude/proposals/$SP047_FILE.asc"
    )
  fi
  # contingency only (gate 8 would have died on an unallowlisted break):
  if git status --porcelain=v1 -- docs/docs-freshness-allowlist.txt | grep -q .; then
    ADD_PATHS+=(docs/docs-freshness-allowlist.txt)
  fi
fi
# S272-P1 rider: refuse to git-add anything gitignored (silently-skipped class)
for p in "${ADD_PATHS[@]}"; do
  case "$p" in
    *staged/*) die "ADD list contains a staged/ path ($p) — gitignored, would be silently skipped" ;;
  esac
  if git check-ignore -q -- "$p" 2>/dev/null; then
    die "ADD list contains a gitignored path ($p) — it would be silently skipped (S272 P1 class)"
  fi
done
git add -- "${ADD_PATHS[@]}"

_sp047_note=""
if [ "$SQUAD" = "data-ml" ] && [ "$APPLY_SP047" = 1 ]; then
  _sp047_note="
SP-047 applied in-ceremony: prisma-patterns moved to saas-platforms
(OQ5, hash-pinned, Owner-signed; soak waived per OQ4). Owner ack of
+2-skills-vs-OQ5-wording recorded in the signed sentinel."
fi
git commit -S -m "feat(PLAN-157): $WAVE — graduate $SQUAD (full ADR-009 bundle; roster $CUR->$NEWCUR)

Graduates the $SQUAD squad (PLAN-153 Wave-D import) off the grandfather
roster: staged bundle merged additively into .claude/skills/domains/$SQUAD
(team-personas, pitfalls, task-chains, examples, +$_n_new new skill(s):
${NEW_SKILLS[*]}); existing imported skills untouched. Roster triplet
commit-atomic $CUR->$NEWCUR: validate-governance SQUAD_GRANDFATHER,
grandfather-cap policy current+cap:=$NEWCAP (OQ3), _EXPECTED_DOMAIN_CAP.
Count reconcile $PRE_TOTAL->$POST_TOTAL skills / $PRE_DOMAIN->$POST_DOMAIN domain across CLAUDE.md,
README, INSTALL, ARCHITECTURE, GUIA twins, verify-counts, core SKILL.md;
COMMAND-SKILL-HOOK-MAP + skill inventory regenerated. Criterion:
reach/consumer-plausibility (OQ1, Owner-ratified S270 — telemetry
structurally blind, no usage claim). ADR-009 validated at ERROR level
post-roster-removal. Full per-wave gate set green pre-commit.$_sp047_note [$SENT_TAG]

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>" || die "commit failed"
COMMITTED=1

# =============================================================================
# WRAP — verify + next steps (push is the Owner's explicit act)
# =============================================================================
say "DONE — $SQUAD graduated as ONE signed commit. Review, then push:"
echo "    git log -1 --show-signature"
echo "    git show --stat HEAD | head -60"
echo "    git push origin main"
echo "    gh run watch \$(gh run list --workflow validate.yml --limit 1 --json databaseId --jq '.[0].databaseId')"
echo ""
echo "  Recommended post-land proof (73f9b0e clean-clone pattern, for the"
echo "  changed test file):"
echo "    d=\$(mktemp -d) && git clone --local --quiet . \"\$d\" \\"
echo "      && (cd \"\$d\" && python3 -m pytest .claude/scripts/tests/test_squad_grandfather_cap.py -q)"
echo ""
echo "  WAIT for Validate green on the push BEFORE the next squad's ceremony"
echo "  (each sentinel anchors at the new HEAD). Order: jvm -> cpp -> golang"
echo "  -> data-ml (data-ml needs SP-047 — see staged/GRADUATION-README.md)."
echo "  After data-ml: policy should read current: 24 + cap: 24 (plan goal);"
echo "  tick $WAVE progress in .claude/plans/PLAN-157-architect-graduation.md"
echo "  next session (status stays executing until the W3 closeout)."
