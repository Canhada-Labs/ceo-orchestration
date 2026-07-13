#!/usr/bin/env bash
# _python-hook.sh — Python version resolver + hook invoker.
#
# Registered in .claude/settings.json as the entrypoint for every Python
# hook (check_agent_spawn.py, audit_log.py). Resolves `python3.12` →
# `python3.11` → `python3.10` → `python3` and refuses anything below 3.9.
#
# ## Why a shim?
#
# `python3` on a user's $PATH is not hermetic:
# - asdf / pyenv resolution is shell-dependent
# - macOS system Python is 3.9 on older machines
# - ubuntu-22.04 runners default to 3.10
# - ubuntu-24.04 runners default to 3.12
# - minimal containers may ship Python 3.8 or none at all
#
# Letting Claude Code run `python3 ...` directly lets a mis-resolved PATH
# silently pick a version that can't run the hooks. The shim is explicit:
# it looks for the newest Python 3.x ≥ 3.9 and refuses to continue if no
# compatible interpreter is found. The refusal message points at install
# commands so the Owner can fix it in one step.
#
# ## Minimum Python version
#
# **3.9** — the macOS system Python on Big Sur / Monterey. This is a
# concession to reality: the original PLAN-002 §11-bis Q1 targeted 3.10
# as minimum, but local dogfooding on this repo runs on 3.9.6 and
# installing 3.10+ globally is out of scope for a framework that wants
# to be "clone and use". All hook Python code is written with
# `from __future__ import annotations` + `typing.Optional/Union` and
# avoids match statements, so 3.9 is fully workable.
#
# ## Usage
#
# In settings.json:
#     "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" check_agent_spawn.py"
#
# The shim forwards stdin/stdout/stderr and passes any trailing args
# through to the Python interpreter.

# F-CHAOS-5 (PLAN-019) + PLAN-023 Phase F (F-perf-001): explicit Python
# version gate, gated to the cache-miss branch only.
#
# Framework requires Python >=3.9 (ADR-002). Earlier versions silently
# lack stdlib features (from __future__ import annotations, etc.).
#
# Pre PLAN-023 Phase F: _py_version_check() ran unconditionally at shim
# entry, spawning a `python3 -c "import sys..."` subprocess every single
# invocation (~15-20ms). Cache-hit paths paid this cost even though the
# cached interpreter had already been validated on its first resolution.
#
# Post PLAN-023 Phase F: the check is called ONLY from the cache-miss
# branch below (after CANDIDATES-loop probing). The cache file persists
# a validated interpreter absolute path; a cache-hit restore implicitly
# re-validates by invoking the cached binary for the hook itself. If the
# cached binary has been uninstalled between invocations, the subsequent
# hook invocation fails loud with the OS-level "No such file" — cleaner
# signal than a silent version re-probe.
_py_version_check() {
  local ver
  ver=$(python3 -c "import sys; print(f\"{sys.version_info.major}.{sys.version_info.minor}\")" 2>/dev/null) || {
    echo "ERROR: python3 not found or invocable. Framework requires Python >=3.9." >&2
    exit 3
  }
  local major minor
  major=${ver%.*}
  minor=${ver#*.}
  if [ "$major" -lt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -lt 9 ]; }; then
    echo "ERROR: Python $ver detected; framework requires >=3.9 (ADR-002)." >&2
    echo "       Upgrade via your package manager and retry." >&2
    exit 3
  fi
}
# NOTE: call is deferred to the cache-miss branch below (see
# `_py_version_check` call site inside the CANDIDATES loop). Intentionally
# no call here — Phase F perf optimization.

# PLAN-025 F-perf-dead-code-1: the earlier `_extract_session_id()`
# helper (P3-SEC-M PLAN-019) had no callers in production paths and
# was forking an extra `python3 -c` subprocess per invocation. Removed
# in Batch K to reduce shim overhead. If session_id breadcrumbs ever
# need to be extracted at shim level again, re-add with the Python
# JSON-parse call INSIDE the existing per-invocation python3 spawn
# (zero marginal cost) instead of a separate subprocess.

set -euo pipefail

# ---------------------------------------------------------------------------
# PLAN-156 Wave 2 (SENT-GK-A) — grok adapter AUTO-DETECT (pair-rail S269 P1 #1).
#
# THE CRITICAL single-surface fix. The grok harness arms the legacy-compat
# `.claude/settings.json`, whose hook commands do NOT carry
# `env CEO_HOOK_ADAPTER=grok` (they are the Claude-native registrations —
# adding it would break Claude Code, which shares the file). But grok delivers
# a camelCase wire (`hookEventName`/`toolName`) to those hooks, so without the
# adapter set they resolve to the CLAUDE adapter, which misparses the grok
# wire → empty tool_name → the matcher-shaped guards no-op → ENFORCEMENT
# SILENTLY FAILS (fail-open). The live-fire missed this because it set the env
# by hand; the codex pair-rail caught it.
#
# Grok injects `GROK_HOOK_EVENT` (+ GROK_SESSION_ID / GROK_WORKSPACE_ROOT) on
# EVERY hook it runs, and never sets CEO_HOOK_ADAPTER. So: if a grok runner
# var is present and the adapter is unset, we ARE under grok — select it. This
# is what makes the single-surface (`.claude/settings.json`) armed rail
# actually enforce under grok. An explicit CEO_HOOK_ADAPTER always wins (tests,
# codex, a deliberate override).
if [ -z "${CEO_HOOK_ADAPTER:-}" ] && [ -n "${GROK_HOOK_EVENT:-}${GROK_SESSION_ID:-}" ]; then
  export CEO_HOOK_ADAPTER=grok
fi

MIN_MAJOR=3
MIN_MINOR=9

# Preferred candidates, most-recent first.
CANDIDATES=(
  "python3.13"
  "python3.12"
  "python3.11"
  "python3.10"
  "python3.9"
  "python3"
)

# PLAN-019 Perf-P2-002 — resolved-interpreter cache.
#
# Measured overhead pre-optimization: ~24ms p50 (on a box where only
# `python3` exists, 5 `command -v` failures + 1 spawn of `python -c
# "import sys; print(...)"` for version probe). Hot-path cost dominated
# by the version-probe subprocess.
#
# Optimization: cache the resolved interpreter path + PATH hash in a
# per-user tempfile. On cache-hit with matching PATH signature, skip the
# probing loop entirely. Cache invalidates automatically when the user's
# PATH changes (e.g. `brew install python@3.12`) so the freshest
# interpreter is picked up without manual eviction.
#
# Expected post-fix overhead: ~2ms (single `stat` + read of cache file).
#
# Security: cache file lives under $TMPDIR (or /tmp) with user-scoped
# path, so a rogue cache from another user cannot hijack. The cached
# path is only USED if the interpreter still exists + reports the same
# version. Fail-safe: cache miss falls back to the full probe.
_cache_dir() {
  local base="${TMPDIR:-/tmp}"
  # Strip trailing slash for consistent path construction.
  base="${base%/}"
  echo "${base}/ceo-pyhook-$(id -u)"
}
_path_hash() {
  # Fast-ish, deterministic hash of the current $PATH. Prefer shasum
  # (macOS); fall back to sha256sum (Linux); fall back to cksum (POSIX)
  # if neither is available (content differs but is still deterministic).
  if command -v shasum >/dev/null 2>&1; then
    printf '%s' "$PATH" | shasum -a 256 | cut -c1-16
  elif command -v sha256sum >/dev/null 2>&1; then
    printf '%s' "$PATH" | sha256sum | cut -c1-16
  else
    printf '%s' "$PATH" | cksum | cut -d' ' -f1
  fi
}

# PLAN-152 security-01 — cache trust gate (TOCTOU / symlink hardening).
#
# The cached interpreter path is READ from $TMPDIR and later EXEC'd; under
# a shared /tmp another local user could pre-create the cache dir (or swap
# in a symlink) and plant an interpreter path of their choosing, and a
# symlinked cache DIR would additionally redirect the cache WRITE into an
# attacker-chosen location. Before any read or write we therefore require:
# the cache dir is a real directory (not a symlink) owned by the current
# uid, and the cache file (when present) is a regular non-symlink file
# owned by the current uid. Any failed check = cache miss (fall back to
# the full probe) — never a hard failure.
_owner_uid() {
  # GNU stat first (Linux); BSD stat fallback (macOS).
  stat -c '%u' "$1" 2>/dev/null || stat -f '%u' "$1" 2>/dev/null
}
_perm_bits() {
  # Octal permission bits (low bits only): GNU '%a' / BSD '%Lp'.
  stat -c '%a' "$1" 2>/dev/null || stat -f '%Lp' "$1" 2>/dev/null
}
_dir_mode_safe() {
  # PLAN-152 security-01 P2 (Codex R2): reject a group/other-writable
  # cache dir. A user-owned but world/group-writable dir lets another
  # local user swap the cache file between the trust check and the read
  # (TOCTOU), restoring the interpreter-hijack this gate closes.
  local m
  m="$(_perm_bits "$1")" || return 1
  [ -n "$m" ] && [ "$(( 0${m} & 022 ))" -eq 0 ]
}
_cache_dir_trusted() {
  [ ! -L "$_CACHE_DIR" ] && [ -d "$_CACHE_DIR" ] \
    && [ "$(_owner_uid "$_CACHE_DIR")" = "$_CUR_UID" ] \
    && _dir_mode_safe "$_CACHE_DIR"
}
_cache_file_trusted() {
  [ ! -L "$_CACHE_FILE" ] && [ -f "$_CACHE_FILE" ] \
    && [ "$(_owner_uid "$_CACHE_FILE")" = "$_CUR_UID" ]
}

parse_version() {
  # Emit "MAJOR MINOR" from `python --version` output (e.g. "Python 3.12.3")
  local py="$1"
  "$py" -c 'import sys; print(sys.version_info[0], sys.version_info[1])' 2>/dev/null
}

version_ok() {
  # Accepts "MAJOR MINOR"; returns 0 if ≥ MIN, else 1.
  local major="$1" minor="$2"
  if [ "$major" -lt "$MIN_MAJOR" ]; then
    return 1
  fi
  if [ "$major" -eq "$MIN_MAJOR" ] && [ "$minor" -lt "$MIN_MINOR" ]; then
    return 1
  fi
  return 0
}

# ---- Cache lookup (fast path) ----
FOUND_PY=""
_CUR_UID="$(id -u)"
_CACHE_DIR="$(_cache_dir)"
_PATH_SIG="$(_path_hash 2>/dev/null || echo "nohash")"
_CACHE_FILE="${_CACHE_DIR}/resolved-py-${_PATH_SIG}"

# Honour CEO_PYHOOK_NO_CACHE=1 to force re-probe (useful for testing
# the fallback path or after installing a new interpreter mid-session).
# PLAN-152 security-01: the dir + file trust gates (ownership, no
# symlinks) run BEFORE the read — an untrusted cache is a cache MISS.
if [ "${CEO_PYHOOK_NO_CACHE:-0}" != "1" ] && _cache_dir_trusted \
    && _cache_file_trusted && [ -r "$_CACHE_FILE" ]; then
  _cached_py="$(cat "$_CACHE_FILE" 2>/dev/null || echo "")"
  if [ -n "$_cached_py" ] && command -v "$_cached_py" >/dev/null 2>&1; then
    # Trust the cache: PATH-hash changes would have produced a different
    # cache filename, and the interpreter path still resolves. No version
    # recheck needed on hot path.
    FOUND_PY="$_cached_py"
  fi
fi

# ---- Cache miss: full probe + repopulate ----
if [ -z "$FOUND_PY" ]; then
  # PLAN-023 Phase F (F-perf-001): run the baseline Python≥3.9 gate ONLY
  # in the cache-miss branch. The gate's `python3 -c ...` spawn is ~15-20ms
  # that cache-hit paths no longer pay. The gate still fires on every
  # first-time or PATH-changed invocation, which is the only time a new
  # interpreter could appear.
  _py_version_check

  for candidate in "${CANDIDATES[@]}"; do
    if command -v "$candidate" >/dev/null 2>&1; then
      read -r py_major py_minor <<< "$(parse_version "$candidate")"
      if [ -n "${py_major:-}" ] && version_ok "$py_major" "$py_minor"; then
        FOUND_PY="$candidate"
        break
      fi
    fi
  done

  # Cache the result for next invocation (atomic write via mv).
  if [ -n "$FOUND_PY" ]; then
    # mkdir is idempotent + concurrent-safe (-p). Set 0700 so another
    # unix user on the host cannot read or replace the cache.
    # PLAN-152 security-01: never write through a symlinked or foreign-
    # owned cache dir (symlink-redirect write primitive).
    # Order matters (PLAN-152 security-01 P2): reject a symlinked dir
    # BEFORE chmod (never chmod an attacker's symlink target), then chmod
    # 0700 to normalize the mode under a loose umask, THEN the full trust
    # check (owner + non-symlink + no group/other write).
    if mkdir -p "$_CACHE_DIR" 2>/dev/null && [ ! -L "$_CACHE_DIR" ] \
        && chmod 0700 "$_CACHE_DIR" 2>/dev/null && _cache_dir_trusted; then
      _tmp_cache="${_CACHE_FILE}.$$"
      if printf '%s\n' "$FOUND_PY" > "$_tmp_cache" 2>/dev/null; then
        mv -f "$_tmp_cache" "$_CACHE_FILE" 2>/dev/null || rm -f "$_tmp_cache" 2>/dev/null
      fi
    fi
  fi
fi

if [ -z "$FOUND_PY" ]; then
  cat >&2 <<EOF
[_python-hook.sh] ERROR: No Python >= ${MIN_MAJOR}.${MIN_MINOR} found.
ceo-orchestration hooks require Python ${MIN_MAJOR}.${MIN_MINOR}+. Install one:

  macOS:   brew install python@3.12
  Ubuntu:  sudo apt install python3.12
  Fedora:  sudo dnf install python3.12

After installing, restart your shell so the PATH picks up the new interpreter.
EOF
  # Fail-open: emit a permissive decision so the user session isn't bricked
  # if Python is missing. The governance hook degrades gracefully.
  echo '{}'  # schema-compliant allow
  exit 0
fi

# First positional arg is the hook script name (relative to this dir).
HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
if [ $# -lt 1 ]; then
  echo "[_python-hook.sh] ERROR: missing hook script name" >&2
  echo '{}'  # schema-compliant allow
  exit 0
fi

HOOK_SCRIPT="$HOOKS_DIR/$1"
shift

if [ ! -f "$HOOK_SCRIPT" ]; then
  echo "[_python-hook.sh] ERROR: hook not found: $HOOK_SCRIPT" >&2
  echo '{}'  # schema-compliant allow
  exit 0
fi

# ---------------------------------------------------------------------------
# PLAN-156 Wave 2 (SENT-GK-A) — decision→exit chokepoint.
#
# ## Why the shim owns this
#
# Grok Build's PreToolUse contract (grok 0.2.93) and Codex's both key a
# deny on **exit 2** in addition to the stdout JSON (probes:
# PLAN-156/artifacts/characterization-grok-codex-S269.md). Before this
# block, deny-emit and process-exit were DECOUPLED: `write_decision` only
# wrote stdout and the shim `exec`'d the hook, so the hook's own exit 0
# became the process exit — a correct deny could still fail OPEN on a
# host that keys on the code. The mapping cannot live in Python (an
# interpreter crash / ImportError / signal never reaches Python), so it
# lives HERE: the single path every registered hook routes through.
#
# ## The rule: decision-derived, never exit-code-derived
#
#   emitted deny          -> exit 2   (a decision was made: enforce it)
#   emitted allow / {}    -> exit 0
#   crashed, NO decision  -> hook's own rc (fail-OPEN: the INFRASTRUCTURE
#                                     half of CLAUDE.md §4 — a missing
#                                     file, an ImportError, a timeout
#                                     must never block the user session)
#
# Reading the DECISION rather than the hook's exit code is what keeps
# those two apart: an input-class deny (a security matcher emitting a
# structured deny on a payload it cannot parse — the codex.py coherence
# gate pattern) exits 2, while a bare interpreter crash with no decision
# on stdout keeps its own (fail-open) code. A blanket "nonzero -> deny"
# remap would break the fail-open half and is explicitly NOT what this does.
#
# ## ADAPTER-AWARE: gated on CEO_HOOK_ADAPTER=grok (debate C14, per lacuna (h))
#
# The plan's Wave-2 conditional: "UNCONDITIONAL mapping SAFE iff Wave-0
# lacuna (h) confirms exit 2 is INERT on Codex; if not, the mapping is
# adapter-aware." Lacuna (h) found exit 2 is NOT inert on Codex — it is an
# ACTIVE deny on PreToolUse (probe P9a). So the plan's own fork selects the
# adapter-aware branch: gate on grok, leave Claude/Codex byte-identical.
#
# This is not a weakening. On EVERY host the stdout JSON decision blocks on
# its own (grok P2, codex JSON-deny, claude JSON-block); the exit code is
# belt-and-suspenders. Remapping deny->2 on Codex/Claude would only change
# an observable exit code with no enforcement gain, while breaking every
# existing test that pins "deny -> exit 0" — a large blast radius for zero
# security benefit. The grok gate keeps the value (a future grok release
# that tightens the docs.x.ai "deny REQUIRES exit 2" rule is covered) where
# it belongs.
#
# R-SEC2 (unset adapter under grok → fail-open) is NOT solved by an
# unconditional EXIT map anyway: on grok a `block` with exit 2 STILL
# fail-opens (P5 — malformed output beats the exit code). It is solved by
# (1) the grok registration always setting CEO_HOOK_ADAPTER=grok — exactly
# as codex sets =codex — and (2) the CI test asserting every registration
# routes through this shim (hooks/tests/test_exit2_chokepoint.py). A named
# residual, identical in kind to the codex one.
#
# ## What this block does NOT do
#
# It does NOT rewrite the decision vocabulary here — the grok block->deny
# rewrite below (also grok-gated) is the ESSENTIAL fix, because grok
# fail-OPENs on `{"decision":"block"}` EVEN WITH exit 2 (probe P5). This
# exit map is the secondary half; the meta-test asserts BOTH.
#
# CEO_HOOK_EXIT_MAP=0 disables the mapping (escape hatch if a future grok
# release turns exit-2-hostile; the arming check surfaces the override).

# The grok path has TWO halves with DIFFERENT disable semantics:
#   - vocabulary rewrite (block->deny): the ESSENTIAL grok fix — a `block`
#     fail-OPENs on grok (P4/P5). NOT disableable by CEO_HOOK_EXIT_MAP.
#   - exit-2 mapping (deny->exit 2): belt-and-suspenders. CEO_HOOK_EXIT_MAP=0
#     turns this off (a future grok release that makes exit-2 hostile).
# Both fire ONLY under CEO_HOOK_ADAPTER=grok on a BLOCKING event; every other
# path preserves the historical exec byte-for-byte (Claude/Codex unchanged).
_CEO_GROK_PATH=0
if [ "${CEO_HOOK_ADAPTER:-}" = "grok" ]; then
  _CEO_GROK_PATH=1
fi

# Event source: under grok, GROK_HOOK_EVENT is the AUTHORITATIVE source (grok
# sets it). Pair-rail S269 finding #4: a generic
# `${CLAUDE_HOOK_EVENT:-${GROK_HOOK_EVENT:-…}}` precedence lets a stale/injected
# CLAUDE_HOOK_EVENT=post_tool_use mislabel a real grok pre_tool_use as passive
# and DISABLE the chokepoint (grok then fail-opens). Since this whole block is
# already gated on CEO_HOOK_ADAPTER=grok, read grok's own var first.
_CEO_EVENT="${GROK_HOOK_EVENT:-${CLAUDE_HOOK_EVENT:-${CODEX_HOOK_EVENT:-}}}"
_CEO_BLOCKING_EVENT=1
case "$_CEO_EVENT" in
  # Passive events (grok spells them snake_case). A passive hook can never
  # block on grok, so neither the rewrite nor the exit map should touch it.
  post_tool_use|post_tool_use_failure|session_start|session_end|\
  notification|pre_compact|post_compact|subagent_start|subagent_stop|\
  permission_denied|stop_failure|stop)
    _CEO_BLOCKING_EVENT=0
    ;;
esac

if [ "$_CEO_GROK_PATH" -eq 0 ] || [ "$_CEO_BLOCKING_EVENT" -eq 0 ]; then
  # Not the grok blocking path (Claude/Codex byte-identical to the historical
  # shim), or a passive grok event: preserve the historical exec (zero added
  # latency; exit = the hook's own).
  exec "$FOUND_PY" "$HOOK_SCRIPT" "$@"
fi

# Blocking event: capture stdout so the decision can drive the exit code.
# stderr passes through untouched (breadcrumbs stay visible to the host).
# `set -e` must not kill us on a nonzero hook exit — we inspect it.
set +e
_CEO_HOOK_STDOUT="$("$FOUND_PY" "$HOOK_SCRIPT" "$@")"
_CEO_HOOK_RC=$?
set -e

# --- grok vocabulary backstop (probe P5) ------------------------------------
#
# Hooks that route their egress through `_lib/adapters/resolve()` already
# emit `deny` under CEO_HOOK_ADAPTER=grok (grok.py:write_decision). But a
# LEGACY hook that hardcodes the Claude vocabulary — today
# `check_codex_filewrite.py`, which json.dumps `{"decision": "block"}`
# directly (lines 275/294/356) — would emit a word grok does not know.
# On grok that is malformed output = hook failure = **fail-OPEN, even
# with exit 2** (P5). Re-routing that hook through this shim (PLAN-156
# Wave 2 settings edit) gives it the exit mapping but NOT the vocabulary,
# so the shim translates here as well: one chokepoint owns BOTH halves,
# and any future hook that forgets the adapter seam degrades to a correct
# deny instead of a silent allow.
#
# We are guaranteed here to be on the grok blocking path. Rewrite block→deny
# with a WHITESPACE-TOLERANT regex (pair-rail S269 finding #3): the two
# fixed-string substitutions only matched json.dumps's exact spacing
# (`"decision": "block"` and `"decision":"block"`), so a hook emitting
# `"decision" : "block"` (space before the colon) would slip through and
# grok would fail-OPEN. `[[:space:]]*` around the colon covers any spacing.
# sed is one cheap subprocess on the (rare) blocking path — acceptable vs a
# silent-allow on an unusual-but-valid deny shape.
if [ -n "$_CEO_HOOK_STDOUT" ]; then
  _CEO_HOOK_STDOUT="$(printf '%s' "$_CEO_HOOK_STDOUT" \
    | sed -E 's/"decision"[[:space:]]*:[[:space:]]*"block"/"decision": "deny"/g')"
fi

# Re-emit the hook's stdout: on grok the JSON decision is what actually blocks.
if [ -n "$_CEO_HOOK_STDOUT" ]; then
  printf '%s\n' "$_CEO_HOOK_STDOUT"
fi

# Exit-2 mapping (belt-and-suspenders; CEO_HOOK_EXIT_MAP=0 disables JUST this
# half, never the vocabulary rewrite above). After the rewrite the only deny
# vocabulary on stdout is grok's `deny` (or a codex-shaped permissionDecision
# from a legacy hook that also routed here). A crash leaves stdout empty ->
# fall through to the hook's own (fail-open) exit code; a nonzero-with-no
# -decision is NEVER turned into a deny.
if [ "${CEO_HOOK_EXIT_MAP:-1}" = "1" ]; then
  case "$_CEO_HOOK_STDOUT" in
    *'"decision"'*'"deny"'*|*'"permissionDecision"'*'"deny"'*)
      exit 2
      ;;
  esac
fi

exit "$_CEO_HOOK_RC"
