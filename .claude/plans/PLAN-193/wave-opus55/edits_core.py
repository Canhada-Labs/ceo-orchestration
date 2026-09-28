"""edits_core.py — the CORE half of the wave-opus55 derivation (PLAN-193 W3/W4).

Data only: this module exposes ``EDITS`` for the governance / settings /
upgrade / adapter / env-tamper-check / mirror surfaces of the
``adopt-opus-5.5`` wave (ADR-149 Amendment 3, S357). It applies nothing.
The debate consensus of 2026-09-23 rides here too: the ``[1m]`` fold in the
env tamper check, the REVERT / NOTICE lines and ``ensure_ascii=False`` in
the settings migration, and the Critic-B test controls (planted table in a
disposable copy, shipped-shape guard over every tag). Rail round 1 (fix round
r14) adds the tier-policy ``owner-sign`` direction: one authority,
``learn._direction``, never the order of ``VALID_MODEL_IDS``. Rail round 2
(fix round r15) adds the class cure for the tests and shell harnesses that
read the HOST Claude Code CLI when they run an installer: Axis 4 of the pytest
isolation layer (``_lib/test_isolation.py``) and the ``harness-claude-stub``
block, one copy per harness. Rail round 3 (fix round r16; Owner OQ-10,
2026-09-24, verbatim «Corrigir + rodada 4 final c/ anexo (Recomendado)»)
adds the ONE builder of the settings migration's re-run command
(``_t54_rerun_cmd`` in ``scripts/upgrade.sh``), printed by every exit that
leaves ``settings.json`` unmigrated. ``apply-opus55-edits.py`` (same
directory) imports it together with ``edits_pricing.py`` and applies both,
anchor-exact, in the order ``EDITS_core + EDITS_pricing``.

Record shape — IDENTICAL to ``apply-fable51-edits.py`` (PLAN-169, S338)::

    (path relative to the repo root, EXACT anchor, replacement, expected count)

Every anchor was cut from HEAD ``19771fa1``. The derivator counts each anchor
on the PROGRESSIVELY edited text of its path (in-memory simulation before the
first write), so two edits on one path can never mutilate each other silently.

Owner decisions this table encodes (S357, verbatim options): Opus 5.5 =
«Padrão + piso VETO» (working-set append at the END, VETO-floor add, session
pin, fallback unchanged, VETO agent files unchanged); adopter effort =
«xhigh» (OQ-1: top-level ``effortLevel`` in the base template, carried into
the generated user template) narrowed by «Instalação nova + opt-in
(Recomendado)» (OQ-7, 2026-09-23: new installs ship it; ``upgrade.sh`` writes
it into an EXISTING install only under ``--adopt-setting effortLevel`` and
never overwrites an adopter value); ``ultracode`` = «Só no override local
(Recomendado)» (OQ-6, 2026-09-23: NO committed settings file carries it);
one atomic pack («Exceção declarada»).

Paths deliberately NOT here (the pricing half owns them): every cost /
telemetry table, the cost-table row, the model-currency expected reds,
``optimizer/model_normalize.py`` (alias + generic ``[1m]`` fold) and their
tests. Keeping the two halves path-disjoint is what lets the derivator
refuse a collision by name instead of guessing an order.

Stdlib-only, Python >= 3.9, no PEP 604 at runtime.
"""
from __future__ import annotations

from typing import List, Tuple

NEW_ID = "claude-opus-5-5"

ADR_REL = ".claude/adr/ADR-149-model-id-allowlist.md"
DOGFOOD_REL = ".claude/settings.json"
BASE_REL = "templates/settings/settings.base.json"
USER_REL = "templates/settings/settings.user.json"
UPGRADE_REL = "scripts/upgrade.sh"
INSTALL_REL = "scripts/install.sh"
VALIDATE_REL = ".claude/scripts/validate-governance.sh"

# --------------------------------------------------------------------------
# Shared literals. The JSON comment strings are rendered verbatim into three
# settings files; they must stay free of double quotes and backslashes so the
# hand-edited base template and the json.dumps-rendered user template carry
# byte-identical values (gen-settings-user-template.py --check).
# --------------------------------------------------------------------------
_EFFORT_COMMENT_BODY = (
    "Top-level effortLevel: in PROJECT settings "
    "it applies to every model the session uses and outranks a level a "
    "developer saved with /effort (Claude Code keeps those per model under "
    "modelSettings in user settings); a level set in "
    ".claude/settings.local.json outranks this file. Claude Opus 5.5 (the "
    "model pin above) runs at its default MEDIUM effort when no level is "
    "set, a default that an organization default effort replaces when the "
    "session runs the organization default model; Opus 5 and Fable 5 "
    "default to high. A maxEffortLevel caps any level, this one included. "
    "The key takes low, medium, high or xhigh; max is not one of its "
    "values, and Claude Code before 2.1.111 has no xhigh (this release "
    "needs 2.1.280, SUPPORT.md). New installs ship xhigh. On an existing "
    "install scripts/upgrade.sh writes xhigh only when you pass "
    "--adopt-setting effortLevel; when it moves the shipped pin "
    "claude-opus-5 to claude-opus-5-5 in a file that sets no level it "
    "writes high, the Opus 5 default; it never overwrites a value you set. "
    "Lower or delete the key to trade depth for cost and latency."
)
#: The two templates: the Owner decisions (OQ-1, OQ-7) are about adopters
#: and new installs.
_EFFORT_COMMENT = (
    "PLAN-193 / ADR-149 Amendment 3 (Owner decisions S357: OQ-1 = xhigh, "
    "OQ-7 = new install + opt-in, OQ-8 = the pin migration writes high). "
    + _EFFORT_COMMENT_BODY
)
#: The dogfood file: its key is a decision of the authoring lane (ADR-149
#: A3.2 item 5), not an Owner option — the comment must not say otherwise.
_EFFORT_COMMENT_DOGFOOD = (
    "PLAN-193 / ADR-149 Amendment 3 (dogfood: the shape of a new maintainer "
    "install, a decision of the authoring lane per A3.2 item 5; the Owner "
    "decisions S357 OQ-1, OQ-7 and OQ-8 cover adopters and new installs). "
    + _EFFORT_COMMENT_BODY
)

#: The T5.4 cost note of the opt-in effortLevel leaf. It lives inside the
#: SINGLE-QUOTED bash string that holds the table, and inside a JSON string:
#: no apostrophe, no double quote, no backslash.
_EFFORT_COST_NOTE = (
    "xhigh applies to every model of the session and typically spends more "
    "tokens (cost and latency) than the default effort; in project settings "
    "it also outranks a level a developer saved with /effort in user "
    "settings (a personal level belongs in .claude/settings.local.json), "
    "and a maxEffortLevel caps it; where no other source sets a level "
    "(CLAUDE_CODE_EFFORT_LEVEL, --effort, /effort, a level saved for the "
    "model, an effortLevel in local or managed settings, ultracode) a "
    "claude-opus-5-5 session runs at its default medium effort "
    "(claude-opus-5 defaults to high), which an organization default "
    "effort replaces when the session runs the organization default model"
)

#: The note of the effortLevel companion write (Owner OQ-8, 2026-09-24):
#: printed after the REVERT line of that MIGRATE. Same constraints as the
#: cost note (bash single-quoted table inside a JSON string).
_EFFORT_KEEP_NOTE = (
    "is the default effort of claude-opus-5 (claude-opus-5-5 defaults to "
    "medium). New installs ship xhigh; --adopt-setting never overwrites a "
    "value present in the file, so set xhigh by hand to use it here"
)

#: The dogfood _enforce_available_models_comment caveat. The old text named
#: only a managed source that FAILS to load; the settings reference (read
#: 2026-09-23) says any deployed managed settings make Claude Code read the
#: key from the managed source alone.
_ENFORCE_CAVEAT_OLD = (
    "Caveat straight from the binary: if a MANAGED-POLICY settings source "
    "exists but fails to load, the harness refuses cascade-trust mode and "
    "model enforcement from user/project settings is DISABLED with a "
    "warning — fail-open at harness level; acceptable because the "
    "availableModels pins still gate explicit selection."
)
_ENFORCE_CAVEAT_NEW = (
    "Caveat (Claude Code settings reference, read 2026-09-23): when an "
    "organization deploys ANY managed settings, Claude Code reads this key "
    "from the managed source alone and ignores it in this file — fail-open "
    "at harness level; acceptable because an availableModels list still "
    "gates explicit selection."
)

#: The T5.4 notice of the model leaf (printed whenever the pin is written).
#: Same constraints as the cost note: no apostrophe, quote or backslash.
_MODEL_NOTICE = (
    "needs Claude Code 2.1.280 or later (SUPPORT.md, which says what to "
    "edit on an older CLI)"
)

for _s in (_EFFORT_COMMENT, _EFFORT_COMMENT_DOGFOOD, _EFFORT_COST_NOTE,
           _EFFORT_KEEP_NOTE, _MODEL_NOTICE, _ENFORCE_CAVEAT_NEW):
    assert '"' not in _s and "\\" not in _s, "JSON literal must need no escaping"
for _s in (_EFFORT_COST_NOTE, _EFFORT_KEEP_NOTE, _MODEL_NOTICE):
    assert "'" not in _s, "an apostrophe ends the bash single-quoted table"

#: The Claude Code floor of this release (Owner OQ-9, 2026-09-24). ONE value:
#: the shell constant of the floor check in install.sh and upgrade.sh, the
#: model-leaf notice and the SUPPORT.md row all carry it, and a test holds
#: them equal.
CLAUDE_CODE_FLOOR = "2.1.280"
assert CLAUDE_CODE_FLOOR in _MODEL_NOTICE

#: The wall limit of the `claude --version` probe (vX r13: the probe had
#: none and inherited stdin, so a hanging CLI blocked every install and
#: upgrade). One value; TestClaudeCodeFloor plants a smaller one in a
#: disposable copy to prove the stop.
CLAUDE_CODE_PROBE_SECONDS = "10"

#: The floor check (Owner OQ-9, 2026-09-24), byte-identical in
#: scripts/install.sh and scripts/upgrade.sh between the two marker lines;
#: TestClaudeCodeFloor holds the two copies equal. bash 3.2-safe (no
#: associative arrays, no `local -n`, no `timeout` command — macOS ships
#: none); never exits — the caller decides. Fix round r13 (vX): the version
#: is read from the line that names (Claude Code) only, a suffix after the
#: three numbers counts as below the floor, and the probe runs with stdin
#: from /dev/null under a polled wall limit that stops its process group.
_FLOOR_CHECK_SH = (
    "# >>> claude-code-floor (ADR-149 Amendment 3, Owner OQ-9) >>>\n"
    "# This release needs Claude Code >= CC_FLOOR_VERSION (SUPPORT.md). The\n"
    "# settings it ships carry values an older CLI may not accept: the\n"
    "# claude-opus-5-5 pin (Anthropic documents 2.1.280 as its minimum) and\n"
    "# effortLevel xhigh (not an effort level before 2.1.111). A settings value\n"
    "# a CLI does not accept can make it skip the WHOLE project settings file,\n"
    "# every hook registration in it included (Claude Code CHANGELOG: invalid\n"
    "# legacy enum values did so until 2.1.121; CLIs before 2.1.281 skip a\n"
    "# file holding the new attribution false). The check reads the claude\n"
    "# found on PATH: below the floor it REFUSES (the caller exits 6) unless\n"
    "# --allow-old-claude-code was passed; no claude on PATH (CI, headless),\n"
    "# or a version it cannot read, is a named WARNING and the run goes on; a\n"
    "# dry run names the refusal and goes on previewing. The probe runs\n"
    "# claude --version in the background with stdin from /dev/null and polls\n"
    "# it; after CC_FLOOR_PROBE_SECONDS it stops the process group of the\n"
    "# probe and the version is unreadable (macOS ships no timeout command).\n"
    "# The version is read only from the first output line that names\n"
    "# (Claude Code); a version with anything after its three numbers (a\n"
    "# pre-release such as 2.1.280-beta.1) counts as below the floor. This\n"
    "# block is byte-identical in scripts/install.sh and scripts/upgrade.sh (a\n"
    "# test holds the two copies equal).\n"
    'CC_FLOOR_VERSION="' + CLAUDE_CODE_FLOOR + '"\n'
    "CC_FLOOR_PROBE_SECONDS=" + CLAUDE_CODE_PROBE_SECONDS + "\n"
    "_claude_code_floor_check() {\n"
    "  # $1 = 1 when --allow-old-claude-code was passed; $2 = 1 on a dry run.\n"
    "  # Returns 1 only for a refusal; a pass prints on stdout, the rest on stderr.\n"
    '  local _ccf_allow="${1:-0}" _ccf_dry="${2:-0}" _ccf_out _ccf_line _ccf_tok _ccf_ver\n'
    '  local _ccf_a _ccf_b _ccf_x _ccf_y _ccf_i _ccf_lt=0 _ccf_why=""\n'
    "  if ! command -v claude >/dev/null 2>&1; then\n"
    '    echo "WARNING: Claude Code CLI not found on PATH (claude): its version is not checked; this release needs Claude Code >= $CC_FLOOR_VERSION (SUPPORT.md)" >&2\n'
    "    return 0\n"
    "  fi\n"
    "  # The probe, in the capture's own subshell: the shell's notices go to\n"
    "  # /dev/null (the probe's output, stderr included, to the capture);\n"
    "  # disown -a empties the job table the subshell inherits, so %1 is the\n"
    "  # probe; set -m starts it in a process group of its own, so kill %1\n"
    "  # signals the whole group (a child it starts that still holds the\n"
    "  # output open is stopped with it); set +m keeps the polling sleeps off\n"
    "  # job control.\n"
    '  if ! _ccf_out="$(\n'
    "    exec 2>/dev/null\n"
    "    disown -a\n"
    "    set -m\n"
    "    claude --version </dev/null 2>&1 &\n"
    "    set +m\n"
    "    # SECONDS counts whole seconds: + 1 so the stop never comes early.\n"
    "    _ccf_end=$(( SECONDS + CC_FLOOR_PROBE_SECONDS + 1 ))\n"
    "    while kill -0 %1; do\n"
    '      if [ "$SECONDS" -ge "$_ccf_end" ]; then\n'
    "        kill -TERM %1 || true\n"
    "        sleep 1\n"
    "        kill -KILL %1 || true\n"
    "        exit 124\n"
    "      fi\n"
    "      sleep 0.1 || sleep 1\n"
    "    done\n"
    "    wait %1 || true\n"
    '  )"; then\n'
    "    echo \"WARNING: Claude Code version unreadable: 'claude --version' did not finish within ${CC_FLOOR_PROBE_SECONDS}s and was stopped; it is not checked; this release needs Claude Code >= $CC_FLOOR_VERSION (SUPPORT.md)\" >&2\n"
    "    return 0\n"
    "  fi\n"
    "  _ccf_line=\"$( printf '%s\\n' \"$_ccf_out\" | grep -F '(Claude Code)' | head -n 1 || true )\"\n"
    "  _ccf_tok=\"$( printf '%s\\n' \"$_ccf_line\" | grep -oE '[0-9]+\\.[0-9]+\\.[0-9]+[^[:space:](]*' | head -n 1 || true )\"\n"
    "  _ccf_ver=\"$( printf '%s\\n' \"$_ccf_tok\" | grep -oE '^[0-9]+\\.[0-9]+\\.[0-9]+' || true )\"\n"
    '  if [ -z "$_ccf_ver" ]; then\n'
    "    echo \"WARNING: Claude Code version unreadable: no line of 'claude --version' names (Claude Code) with a version; it is not checked; this release needs Claude Code >= $CC_FLOOR_VERSION (SUPPORT.md)\" >&2\n"
    "    return 0\n"
    "  fi\n"
    '  _ccf_a="$_ccf_ver"\n'
    '  _ccf_b="$CC_FLOOR_VERSION"\n'
    "  for _ccf_i in 1 2 3; do\n"
    '    _ccf_x="${_ccf_a%%.*}"\n'
    '    _ccf_y="${_ccf_b%%.*}"\n'
    '    if [ "$(( 10#$_ccf_x ))" -lt "$(( 10#$_ccf_y ))" ]; then _ccf_lt=1; break; fi\n'
    '    if [ "$(( 10#$_ccf_x ))" -gt "$(( 10#$_ccf_y ))" ]; then break; fi\n'
    '    _ccf_a="${_ccf_a#*.}"\n'
    '    _ccf_b="${_ccf_b#*.}"\n'
    "  done\n"
    '  if [ "$_ccf_lt" -eq 0 ] && [ "$_ccf_tok" != "$_ccf_ver" ]; then\n'
    "    _ccf_lt=1\n"
    '    _ccf_why=" (a version with anything after its three numbers counts as below it)"\n'
    "  fi\n"
    '  if [ "$_ccf_lt" -eq 0 ]; then\n'
    '    echo "    Claude Code:  $_ccf_ver (floor $CC_FLOOR_VERSION: OK)"\n'
    "    return 0\n"
    "  fi\n"
    '  if [ "$_ccf_allow" = "1" ]; then\n'
    '    echo "WARNING: Claude Code $_ccf_tok is below $CC_FLOOR_VERSION$_ccf_why, the minimum of this release; continuing because --allow-old-claude-code was passed. The settings it writes may not load on that CLI: see SUPPORT.md (Claude Code CLI) for what to edit" >&2\n'
    "    return 0\n"
    "  fi\n"
    '  if [ "$_ccf_dry" = "1" ]; then\n'
    '    echo "(dry-run) would REFUSE: Claude Code $_ccf_tok is below $CC_FLOOR_VERSION$_ccf_why, the minimum of this release; an apply run stops here (exit 6) unless you pass --allow-old-claude-code" >&2\n'
    "    return 0\n"
    "  fi\n"
    '  echo "ERROR: Claude Code $_ccf_tok is below $CC_FLOOR_VERSION$_ccf_why, the minimum of this release (SUPPORT.md): nothing was written. Update Claude Code, or pass --allow-old-claude-code to continue anyway (the settings it writes may not load on that CLI)" >&2\n'
    "  return 1\n"
    "}\n"
    "# <<< claude-code-floor <<<\n"
)
assert "CLAUDE_" not in _FLOOR_CHECK_SH and "CEO_" not in _FLOOR_CHECK_SH, \
    "an env-name-shaped token would enter the env inventory"

_ADR_AMENDMENT_3 = """
## Amendment 3 (S357 — Opus 5.5 joins the working set and the VETO floor and becomes the session pin; fallback unchanged)

> Authored S357 (2026-09-22) under PLAN-193 (W3, `wave-opus55`). Ratified by
> the Owner via AskUserQuestion at S357, verbatim option «Padrão + piso
> VETO»; adopter effort verbatim «xhigh» (OQ-1, 2026-09-22), narrowed by
> «Instalação nova + opt-in (Recomendado)» (OQ-7, 2026-09-23); `ultracode`
> verbatim «Só no override local (Recomendado)» (OQ-6, 2026-09-23); the
> effort of a migrated pin verbatim «Migrar gravando 'high' (Recomendado)»
> (OQ-8, 2026-09-24); the Claude Code floor verbatim «Exigir CC ≥ 2.1.280
> (Recomendado)» (OQ-9, 2026-09-24). Lands
> through the `wave-opus55` sentinel ceremony
> (`.claude/plans/PLAN-193/wave-opus55-approved.md`) as ONE derived pack; the
> exception to the 8-path pack rule is declared in PLAN-193 (OQ-2).

### A3.1 Facts the amendment rests on (Anthropic docs fetched 2026-09-22; Claude Code 2.1.280)

- **API id = `claude-opus-5-5`** — dateless, a pinned snapshot; a date
  suffix must never be appended.
- $4 in / $20 out per MTok; cache writes 1.25x (5 min) and 2x (1 h);
  **cache hits 0.05x the base input price ($0.20/MTok)** — not the standard
  0.1x; batch $2 / $10; the 1M context window at standard price; 128K max
  output; knowledge cutoff June 2026. Fast mode (research preview, Claude
  API only) is $8 / $40 per MTok (pricing page, fetched 2026-09-23).
- Adaptive thinking is always on: a request with thinking disabled or with
  `budget_tokens` is an HTTP 400, and so is a forced `tool_choice`
  (`any` / `tool`).
- Thinking by model (thinking troubleshooting page, fetched 2026-09-23,
  re-read 2026-09-24): `{type: enabled}` with `budget_tokens` is rejected
  on Claude 4.7 and later — Claude Mythos Preview, which supports both
  modes, excepted — deprecated on the 4.6 models, and the only mode of
  Claude 4.5 and earlier; `{type: disabled}` is rejected on the models the page lists
  as always on (the Fable and Mythos 5 models, Mythos Preview, Opus 5.5)
  and accepted where thinking defaults on (Opus 5 at effort `high` or
  below, Sonnet 5) or off (Opus 4.6 to 4.8, Sonnet 4.6).
- Default effort is **medium** (Opus 5 and Fable 5 default to high); the
  model accepts `low` through `max`.
- Claude Code **2.1.280** is the minimum CLI for the id. The model catalog
  inside the 2.1.280 binary (measured S357) lists it with adaptive thinking,
  the `xhigh` effort level, the `[1m]` suffix and `medium` as its default
  effort.
- Older CLIs and settings values (Claude Code CHANGELOG, fetched
  2026-09-24): `xhigh` became an effort level in 2.1.111; 2.1.121 fixed
  invalid legacy enum values in `settings.json` invalidating the entire
  settings file; the 2.1.281 entry that adds `"attribution": false` says
  older CLI versions skip a settings file that holds it. A settings value
  a CLI does not accept can therefore make it skip the whole project
  settings file, every hook registration in it included. Whether a CLI
  before 2.1.111 treats `effortLevel: "xhigh"` that way is not measured
  here.
- `claude-opus-5` stays Active: the change is ADDITIVE.
- Prompt caches are model-scoped (the Claude API reference bundled with
  Claude Code 2.1.280). Claude Opus 5 does not read thinking blocks
  produced by Opus 5.5 — on the Claude API only Fable 5.1 and Mythos 5.1
  read them — and the API drops, unbilled, a block the serving model
  cannot read (preserved-thinking page, fetched 2026-09-23).
- Subagent model and effort (Claude Code sub-agents page, fetched
  2026-09-23): a subagent runs on the per-invocation `model` parameter,
  else the `model` frontmatter of its agent file, else
  `CLAUDE_CODE_SUBAGENT_MODEL` when that names an alias or an id, else
  the main conversation's model; setting the variable to `inherit` is the
  same as leaving it unset (since Claude Code 2.1.196). An agent file's
  `effort` key defaults to inheriting the session effort level.
- Model fallback (Claude Code model-config page, fetched 2026-09-23): an
  availability fallback (the `fallbackModel` chain) lasts the current
  turn only — the next message tries the primary model again — and
  authentication, billing, rate-limit, request-size and transport errors
  never trigger it. A content-classifier fallback re-runs a request that
  Opus 5.5 flags on Opus 5 (biology) or Opus 4.8 (cybersecurity), and
  after it the session continues on the fallback model.
- Effort settings (Claude Code settings reference, fetched 2026-09-23):
  the `effortLevel` key takes `low`, `medium`, `high` or `xhigh`; `/effort`
  saves a level per model under `modelSettings` in user settings; across
  settings files the highest-precedence file that sets a level for a model
  decides (local over project over user), and a top-level `effortLevel` in
  project, local or managed settings applies to every model, while one in
  USER settings does not apply to Opus 5.5. A session resolves its level in
  this order (Claude Code model-config page, fetched 2026-09-23): an
  explicit choice (`CLAUDE_CODE_EFFORT_LEVEL`, `--effort`, `/effort` in
  the session), then the settings (a level saved for the model, or an
  `effortLevel` key), then the model default, which an organization's
  default effort replaces when the session runs the organization default
  model; `ultracode` runs the session at `xhigh` over `effortLevel` and
  `modelSettings`.
- API rate limits (rate-limits page, fetched 2026-09-23): Claude Opus 5.5
  and Claude Opus 5 each have a separate rate limit, outside the combined
  limit of the Opus 4.x ids. The prices above (input, output, both cache
  writes, the 0.05x cache hit, batch) were re-read on the pricing page the
  same day, unchanged.

### A3.2 Decision

1. `AVAILABLE_MODELS_WORKING_SET` gains `claude-opus-5-5` **at the end**
   (A1.1 order rule — no reorder, no removal). The generated
   `availableModels` mirrors follow via `generate-available-models.py`;
   every independent mirror bound by `test_adr149_validator_parity.py`
   carries the same append in the same patch.
2. `VETO_FLOOR_ALLOWED` — the base Decision block and
   `agent_frontmatter.VETO_FLOOR_ALLOWED`, set-equal by test — gains
   `claude-opus-5-5`. Membership makes the id ELIGIBLE to render a VETO; it
   migrates no agent file: every `veto_floor: true` agent file keeps its
   `model: claude-fable-5` pin. (A2.2 item 2 states a count of those files
   that does not match the tree it was written against; the count there is
   a known stale claim, and the class is named here by its shape instead.)
3. `FALLBACK_MODEL_CHAIN` is **unchanged** (`claude-opus-5`).
4. The session-default `model` pin moves from `claude-opus-5` to
   `claude-opus-5-5` in `.claude/settings.json`,
   `templates/settings/settings.base.json` and the GENERATED
   `templates/settings/settings.user.json`. A2.2 item 4 is superseded.
5. Effort (Owner OQ-1, verbatim «xhigh»; OQ-7, verbatim «Instalação nova +
   opt-in (Recomendado)»): the base template — and through its derivation
   the user template — carries top-level `effortLevel: "xhigh"`, so a NEW
   install ships it. In project scope the key applies to every model of
   the session and outranks a level a developer saved with `/effort` in
   user settings; a developer keeps a personal level in
   `.claude/settings.local.json`, which outranks the project file (A3.1).
   The key takes `low` through `xhigh`; `max` is not one of its values.
   The dogfood `.claude/settings.json` carries the same key — a decision
   of the authoring lane, not an Owner option: the dogfood takes the shape
   of a new maintainer install. No committed settings file carries `ultracode`
   (Owner OQ-6, verbatim «Só no override local (Recomendado)»): it stays in
   an operator's untracked local overlay, and a test keeps it out of the
   three committed files.
6. `scripts/upgrade.sh`, T5.4 table: the `availableModels` `superseded` list
   gains the 7-id array that every release from v1.4.0-rc.1 to the last one
   before this amendment shipped.
   TOP-LEVEL scalar leaves gain the same `superseded` semantics through ONE
   generic branch. This is the second occurrence of "a shipped baseline read as
   adopter-customized" (A2.2 item 5 was the array occurrence), so the cure
   is the branch, not an Opus special case: `model` declares
   `superseded: ["claude-opus-5"]` (the pin every release from v1.2.0-rc.1
   to the last one before this amendment shipped; a test walks the release
   tags a checkout holds and reads the shape each one shipped), and a leaf
   may declare `requires_member_of` — the C6 guard as
   data, generic over the array leaves of the table (the gate reads the
   value that array leaf resolved to earlier in the same pass): `model`
   migrates only when the new pin is an EXACT member of the
   effective `availableModels` — deliberately stricter than Claude Code,
   which admits an id by segment prefix (A3.3), so the warning names an
   inexact list, not a harness rejection. The new scalar leaf `effortLevel` is the
   first OPT-IN leaf (`opt_in: true` plus a `cost_note`): an existing
   install receives it only when the operator passes
   `--adopt-setting effortLevel`; without the flag the upgrade leaves the
   key absent and prints a named warning that carries the cost note and
   the flag. An adopter value is never overwritten, with or without it.
   An opt-in leaf may also declare `on_migrate_of`: a value it takes when
   another scalar leaf, walked earlier in the same pass, MIGRATEs away from
   a named value while this leaf is absent (or null) and the operator did
   not opt in. `effortLevel` declares `high` for a `model` that migrates off
   `claude-opus-5` (Owner OQ-8, verbatim «Migrar gravando 'high'
   (Recomendado)»): `high` is the Opus 5 default and medium the Opus 5.5
   one (A3.1), so a migrated install that set no level keeps the effort
   its pin ran at where no other source sets a level (A3.4). That write is
   a MIGRATE line followed by a REVERT line (delete the key) and a note
   that names the opt-in `xhigh`. A SET of the pin (a file without one)
   writes no `effortLevel`, and `xhigh` reaches an existing install only
   through the flag.
   A leaf may also carry a `notice`, printed whenever the leaf is written:
   `model` carries the Claude Code 2.1.280 floor of the new pin. Every
   MIGRATE line, in a dry run too, is followed by a `REVERT:` line — for
   a scalar value, the `.claude/settings.local.json` entry that keeps the
   previous value (local settings override the project file, and
   `upgrade.sh` never writes that file); for an array leaf or a hook
   registration, the pre-migration backup (`availableModels` and hook
   registrations merge across settings scopes, so a local entry cannot
   take a migrated value back out; `fallbackModel` is replaced wholesale
   by a higher scope, and the backup is what restores the project file
   itself). A dry run writes no backup, and its `REVERT:` line says so. An
   apply run writes the backup before anything else and treats it as a
   precondition: when the backup cannot be written the migration is
   skipped with a named note and the file is left as it was. Every exit
   of the migration that leaves the file unmigrated — the backup that
   cannot be written, `python3` missing, and the helper that fails (an
   unparseable file, an atomic write that fails, any other non-zero
   exit) — names the command that re-runs the migration alone, built by
   ONE routine that carries every operator flag deciding what the
   migration reads or writes, or whether it runs: `--adopt-setting`,
   `--allow-old-claude-code`, `--pin` and `--dry-run`, with the target
   and the `--pin` value quoted for the shell (rail round 3 of the wave;
   Owner OQ-10). The
   migration writes the file with `ensure_ascii=False`: characters outside
   ASCII stay as written instead of being escaped, so a file in the
   templates' own format keeps every line outside the migrated leaves
   byte-identical except the line just before a key the migration ADDS:
   a new key goes at the end of its object, and that line gains a
   trailing comma (tested on the base template that v1.4.1-rc.1 shipped, where the
   pin migration appends `effortLevel` after the last key, and on the
   current template); a file holding a value
   UTF-8 cannot encode (a lone surrogate) is written in the escaped form
   instead, so it still migrates. A file that an earlier release's
   migration wrote holds those characters escaped; its first migration
   under this writer rewrites every such line once, in the unescaped form.
7. `_lib/adapters/live/claude.py` inverts its thinking default. Class cure,
   second occurrence: the adaptive-only prefix list never gained
   `claude-opus-5` or `claude-sonnet-5`, so `CEO_EFFORT_OVERRIDE` sent them
   the legacy `budget_tokens` shape, which Claude 4.7 and later reject with
   an HTTP 400 (A3.1). A CLOSED list now names the pre-4.6 ids, whose only
   thinking mode is the legacy `{type: enabled, budget_tokens}` shape; they
   keep that path as before, in their first-party, Bedrock and Vertex
   (`@YYYYMMDD`) spellings. An entry of the list matches its exact id, and
   that id followed by ONE dated snapshot segment (`-YYYYMMDD`, or the
   Vertex `@YYYYMMDD`) and then a Bedrock version suffix (`-vN`, `-vN:M`),
   each optional; an id that extends an entry by any other `-` segment is
   a different id. One entry is a family: every id that starts with
   `claude-3-` (the Claude 3 generation); the bare dated ids of the 4.0
   generation (`claude-opus-4-YYYYMMDD`, `claude-sonnet-4-YYYYMMDD`) match
   only with their date. Every other id is adaptive-only,
   so the next model id is safe by default. The same list decided a caller's
   `{type: disabled}`: the adapter dropped it on every adaptive-only id,
   which on a model whose thinking defaults ON (Opus 5, Sonnet 5) would
   now turn thinking on in silence. It now drops it only on the ids it
   lists as always on (Fable 5 and 5.1, Mythos 5 and 5.1, Mythos Preview
   and Opus 5.5 — the models the thinking page lists as always on),
   matched by the same rule, where the API rejects it, and sends it as
   given everywhere else; an always-on id it does not list answers with
   an HTTP 400, never with silent thinking.
8. `tier_policy_cli/learn.py` `_tier_rank` places `claude-opus-5-5` strictly
   above `claude-opus-5` and strictly below `claude-fable-5`. The ladder is
   tier-major; the ranks are renumbered, never tied, so a move from Fable 5
   to Opus 5.5 is a `demote`. `ceo-tier-policy owner-sign` records in the
   sigchain the action `learn._direction` computes over this ladder. It
   used to read the order of `VALID_MODEL_IDS`, an allowlist in ADR order
   that is not a tier order (`claude-fable-5` is its first entry): a move
   from Fable 5 to Opus 5 already signed as `promote`, and appending
   `claude-opus-5-5` would have signed a move from Fable 5.1 to Opus 5.5
   as `promote` too. A model id the ladder does not rank, or the same
   model on both sides, is refused (exit 2) before anything is signed; a
   test requires a rank for every `VALID_MODEL_IDS` entry, no two equal.
9. `audit_log._ADR_052_ROLE_TO_MODEL["general-purpose"]` follows the session
   pin (`claude-opus-5-5`): that row states that the mitigated rail inherits
   the CEO model. It stays a POLICY value, not an observation.
10. `_lib/effective_config.py` folds ONE trailing `[1m]` tag before the env
    tamper check compares a model value with the allowlist: the tag selects
    the 1M context window, so `claude-opus-5-5[1m]` in `ANTHROPIC_MODEL` or
    in an `ANTHROPIC_DEFAULT_*` key is the floor member `claude-opus-5-5`.
    Only that exact tag folds; any other suffix is compared as written, so
    a value the check cannot classify stays flagged.
11. Claude Code floor (Owner OQ-9, verbatim «Exigir CC ≥ 2.1.280
    (Recomendado)»): this release declares Claude Code 2.1.280 as its
    minimum (`SUPPORT.md`). The settings it ships carry values an older CLI
    may not accept — the `claude-opus-5-5` pin, whose documented minimum is
    2.1.280, and `effortLevel: "xhigh"`, not an effort level before
    2.1.111 — and a
    settings value a CLI does not accept can make it skip the whole project
    settings file, hook registrations included (A3.1). `scripts/install.sh`
    and `scripts/upgrade.sh` therefore read `claude --version` before an
    install or an upgrade writes anything. What exits before the check is
    not gated, by shape: every mode that delivers no framework file —
    `--help` in both scripts, the table print `--print-settings-baselines`
    of `upgrade.sh`, and the reviewer-harness lifecycle modes of
    `install.sh` (`--arming-check`, which reads an existing wiring, and
    `--uninstall`, which removes one, for whichever harness they name,
    `codex` or `grok`) — and every refusal of an argument, a missing target
    or a failed preflight. A CLI below the floor is refused (exit 6) unless
    the operator passes `--allow-old-claude-code`, which continues with a
    named warning; no `claude` on PATH (CI, a headless host) or a version
    the scripts cannot read is a named warning and the run continues; a dry
    run names the refusal and goes on previewing. The probe runs with stdin
    from `/dev/null`, in the background, polled against a wall limit of 10
    seconds; at the limit it stops the probe's process group and the
    version is unreadable (a named warning, as above). The version is read
    only from the first output line that names `(Claude Code)`, so another
    program's version printed first is never read, and a version with
    anything after its three numbers (a pre-release such as
    `2.1.280-beta.1`) counts as below the floor. The check is one shell
    block, byte-identical in the two scripts; a test holds the two copies
    equal and ties their floor to the `notice` of the `model` leaf and to
    the `SUPPORT.md` row.

### A3.3 Earlier text, amended by shape

- A1.1 calls the floor "the only models permitted to render a VETO
  verdict". On agent-definition (native) dispatch `check_agent_spawn`
  checks the `model:` of a VETO-role agent file only when the role's slug
  (such as `security-engineer`) appears in the spawn's description or
  prompt — it does not read `subagent_type` (A3.4) — and a per-invocation
  `model` parameter outranks that file (A3.1) with no gate observing it:
  the file pin binds only an invocation that passes no model. Mitigated
  dispatch (`subagent_type: general-purpose`, the default route of some VETO
  archetypes in `.claude/team.md`) and Workflow agents, when passed no
  model, run on the model the session runs at that moment: the pin
  `claude-opus-5-5`, a floor member, by default — or whatever a `/model`,
  `--model` or `ANTHROPIC_MODEL` choice, or a content fallback that
  persists for the session, selected, which may be a model outside the
  floor. `CLAUDE_CODE_SUBAGENT_MODEL=inherit`, which the shipped settings
  carry, is the same as leaving that variable unset (A3.1); it is not what
  makes those spawns inherit. Which model actually served a given
  mitigated spawn is not measured here.
- A1.1 (the rationale of `FALLBACK_MODEL_CHAIN`) and A1.3 clause (c)
  describe the content-classifier fallback as Fable 5 falling back to the
  default Opus model. Since Claude Code 2.1.219 that fallback goes by
  category, and the session pin is itself a source (A3.1): a request Opus
  5.5 flags re-runs on Opus 5 or Opus 4.8 — both floor members — and the
  session then STAYS on that model, while an availability fallback lasts
  one turn. Clause (c) covers both switches. Rationale (ii) of A1.1 — that
  the availability fallback and the refusal fallback land on the same
  model — no longer holds for the pin: a cybersecurity flag re-runs on
  Opus 4.8 while `fallbackModel` is `claude-opus-5`, so the two can land
  on different floor members.
- A2.1 says every model but Fable 5.1 keeps the standard 0.1x cache-read
  rate and that `budget-summary.py` is the ONE cost surface that prices
  cache reads. The pricing page (re-read 2026-09-24) prices Mythos 5.1
  cache hits at 0.025x too, a model outside the working set that no cost
  surface here prices; Opus 5.5 is a further exception (0.05x, A3.1), and
  `ceo-cost-transcripts.py` prices cache reads too, with its own per-model
  multiplier table, which `test_model_fleet_presence.py` holds equal to
  the one in `budget-summary.py`.
- A1.1 calls the working set "the set of model ids the harness may select
  on ANY surface". Claude Code 2.1.280 matches `availableModels` entries by
  segment PREFIX (measured S357): an entry admits every id that extends it
  by a `-` segment (`claude-opus-5` already admitted `claude-opus-5-5`;
  `claude-fable-5` admits `claude-fable-5-1`). Where the framework DECIDES
  admission — the spawn gate, the env tamper check (after the one `[1m]`
  fold of A3.2 item 10) and the generator `--check` — it compares EXACT
  ids; advisory telemetry classifiers may match by model-family prefix
  (A3.4). The working set is therefore the exact list
  the framework ratifies and, where no managed settings define
  `availableModels`, a lower bound of what the harness admits (a managed
  list alone applies, and project, local or user entries cannot extend it);
  `enforceAvailableModels` does not redirect a harness default that extends
  an allowed entry, and the explicit `model` pin is what fixes the session
  default.
- A1.4 names the env tamper tripwires as compensating visibility. They read
  the FIRST `frozenset` block of this file — the VETO floor — so adding a
  floor member also widens the set of accepted `ANTHROPIC_MODEL` /
  `ANTHROPIC_DEFAULT_*` values. `install.sh` delivers only
  `.claude/adr/README.md` from this directory, so in an adopter the check
  finds no allowlist and runs degraded (breadcrumb, no finding).

### A3.4 Declared residuals (not cured here)

- **Subagent effort is not pinned.** The spawn gate blocks `/effort` tokens
  in spawn prompts and no agent file carries an `effort` key, so a
  subagent inherits the session effort level — documented (A3.1), not
  measured on Claude Code 2.1.280, and not measured for Workflow agents. A
  VETO verdict served by `claude-opus-5-5` therefore runs at the session
  level, which is the model default MEDIUM wherever no level is set. The
  Owner kept the id in the floor; a measurement, or an effort floor in the
  agent frontmatter, is a FOLLOW-UP.
- **The pin and the fallback now differ — a new failure mode.** Until this
  amendment they were the same model; now an availability fallback
  CHANGES the serving model (`claude-opus-5-5` to `claude-opus-5`) for the
  turn in which it fires, and the next message returns to the pin (A3.1).
  Both are floor members, so A1.3 clause (a) holds; clause (c) now
  describes a switch that can actually happen, and no hook records it.
  Each switch can have a price: prompt caches are model-scoped, so the
  `claude-opus-5` turn writes to its own cache the part of the context
  that Opus 5 holds no live cache for — the whole context when it holds
  none — at its cache-write price ($6.25/MTok for the 5-minute cache,
  1.25x its $5 input; a cache entry lives five minutes, or an hour with
  the 1-hour cache, counted from the start of the last request that read
  or wrote it, per the prompt-caching page fetched 2026-09-23), and the
  return to the pin
  writes again, at the Opus 5.5 price, what the pin's cache lost
  meanwhile. Opus 5 does not read the Opus 5.5 thinking blocks, so that
  turn runs without them, and a dropped block changes the cached prefix
  from its position onward (same page). A rate-limit error never
  triggers the switch (A3.1), so the fallback does not relieve an Opus 5.5
  rate limit. On the API the two models have separate rate limits; how a
  Claude Code subscription quota counts the two models is not stated in
  those sources and is not measured here.
- **The effort level the pin migration writes is a project setting.**
  When the upgrade migrates the shipped pin `claude-opus-5` to
  `claude-opus-5-5` in a project file that sets no level, it writes
  `effortLevel: "high"` (A3.2 item 6, Owner OQ-8). Like any top-level
  `effortLevel` in project settings, that key applies to every model of
  the session and outranks the model default, an organization's default
  effort, and a level a developer saves with `/effort` in user settings
  (A3.1); a personal level belongs in `.claude/settings.local.json`. A
  top-level `effortLevel` in a developer's user settings, which applied to
  Opus 5, does not apply to Opus 5.5 (A3.1); there the project `high` now
  decides. An explicit choice (`CLAUDE_CODE_EFFORT_LEVEL`, `--effort`,
  `/effort` in the session), `ultracode` and a `maxEffortLevel` cap still
  act over it. An `effortLevel` already in the project file is preserved,
  and it keeps applying to Opus 5.5. An install whose file had no pin (the
  pin is SET, not migrated) receives no `effortLevel`: where no other
  source sets a level it runs Opus 5.5 at its default, medium. An install
  whose pin is custom, or whose allowlist withholds the new pin, keeps its
  pin and receives no `effortLevel`.
- **User-ceremony installs.** The settings migration does not read the
  install ceremony, a known-open condition that
  `docs/UPGRADE-PROCEDURE.md` routes through `--no-settings-migrate`. An
  operator who follows that route receives neither the new pin nor
  `effortLevel` and sets them by hand; an `--adopt-setting` passed with
  it is named in a warning and ignored.
- **A downgrade does not migrate back.** No earlier release lists
  `claude-opus-5-5` or the 8-id `availableModels` in its T5.4 table, so an
  earlier release's `upgrade.sh` preserves both as adopter-customized
  (a release before this amendment cannot name them; checked S357 on the
  table of v1.4.1-rc.1, the last tag then). What undoes the migration is the
  pre-migration backup or a revert of the committed upgrade; the
  `.claude/settings.local.json` entry a `REVERT:` line names does not
  change the project file, it overrides the migrated scalar value.
  `upgrade.sh --pin <earlier release>`, run from a newer framework
  checkout, applies the T5.4 table of the RUNNING script, not the pinned
  release's: the revert-then-`--pin` rollback that
  `docs/UPGRADE-PROCEDURE.md` documents migrates the reverted settings
  forward again unless that run passes `--no-settings-migrate`. That
  behaviour predates this amendment.
- **The floor check reads one CLI.** `install.sh` and `upgrade.sh` read
  the `claude` found on PATH when they run (A3.2 item 11); the CLI that
  later opens the project can be another one. With no `claude` on PATH
  they warn and continue, and `--allow-old-claude-code` continues below
  the floor: then the shipped pin and `effortLevel` are the operator's to
  edit (`SUPPORT.md`). What a CLI older than 2.1.280 does with the pin is
  not measured here; the upgrade also prints the floor as the `notice` of
  the `model` leaf whenever it writes the pin. The probe's stop reaches
  its own process group only: a process the CLI moves out of that group
  that keeps the output open still holds the probe.
- **The floor only grows.** Removal stays an Owner-only act (base
  Consequences); this amendment adds no retirement trigger.
- **Advisory classifiers match by family prefix.** A telemetry detector
  of VETO-role spawns served by a non-floor model classifies the logged
  model by its family prefix (`claude-opus-`, `claude-fable-`), so an id
  of a floor family that the floor does not list raises no finding there.
  It decides nothing; the spawn gate, which decides, compares exact ids.
- **A nested scalar leaf has no `superseded` branch.** The generic branch
  of A3.2 item 6 walks top-level keys only. `permissions.defaultMode`
  keeps its own code, which migrates only its old baseline: a value that
  a later table moves to `superseded` there would be read as
  adopter-customized until that leaf joins a generic branch.
- **The native VETO-floor check reads text.** `check_agent_spawn` runs the
  floor check for a VETO role only when the role's slug appears in the
  spawn's description or prompt; a native spawn whose `subagent_type`
  names a VETO agent while its text names no VETO role is not checked
  (A3.3). The gate predates this amendment, which does not change it.
- **`/effort off` does not turn thinking off where it defaults on.**
  When the caller passes no thinking value, `CEO_EFFORT_OVERRIDE=off`
  makes the live adapter omit the thinking parameter, as it did before
  this amendment; on an id whose thinking
  defaults on (A3.1), omitting it leaves thinking on. Turning it off there
  would take an explicit `{type: disabled}` where A3.1 says the model
  accepts one; not changed here.
- **The opt-in native batch path forwards the caller's thinking.** With
  `CEO_NATIVE_BATCH_LIFECYCLE=1`, `_lib/adapters/live/claude_batch.py`
  builds each native batch request with the caller's `thinking` value as
  given; the thinking handling of A3.2 item 7 covers the single-call path
  and the sequential batch fallback, which goes through it. Off by
  default; not changed here.
- **A forced `tool_choice` is passed through.** A3.1 records that a forced
  `tool_choice` (`any` / `tool`) is an HTTP 400 on `claude-opus-5-5`; the
  live adapter's structured-output path sends a caller's `tool_choice` as
  given, and no caller outside the tests passes one (checked S357,
  2026-09-24). A caller that forces one on `claude-opus-5-5` gets that
  400; not changed here.

### A3.5 What this amendment does NOT decide

- Migrating any `veto_floor: true` agent file off `claude-fable-5`.
- `_lib/model_routing.py` `_ROUTING_TABLE` (debate/arch stay on
  `claude-opus-5`), the reviewer default in `check_codex_stop_review.py`,
  and the `hooks/_lib/tier_policy` `MODEL_ID` enum.
- Prices beyond the rate card (A3.1). The same derived patch gives the
  $4/$20 row to `cost-table.yaml` and to every cost-rollup table that
  `test_model_fleet_presence.py` binds to this ADR's working set, and
  0.05x to the two per-model cache-read tables that test holds equal.
  Per-model price tables outside that oracle (Owner-provenance snapshots,
  drift fixtures, research and tournament instruments, the tier-policy
  cost gate) are not changed. The rollups that look a model up by its
  exact spelling do not price the `[1m]`-tagged spelling of
  `claude-opus-5-5`.
- The `upgrade.sh` T3.4 gate that withholds the DirectoryAdded /
  Notification registrations from adopter settings: A3.2 item 11 raises
  the adopter floor to Claude Code 2.1.280 but leaves that gate OFF.
- `SPEC/v1/install-cli.md`: it lists neither `--allow-old-claude-code`,
  nor `--adopt-setting`, nor exit 6. Its exit-code table already lags the
  scripts (it stops at 3, while its own flag table names exits 4 and 5);
  the SPEC is not changed here.
- `CLAUDE.md`, `.claude/team.md` and the CHANGELOG (closeout and release
  surfaces).

The A1.1 sentence on the primary session model and A2.2 item 4 are
historical; the session pin is `claude-opus-5-5` (A3.2 item 4).
"""

#: Test classes appended to test_upgrade_settings_migration.py (debate
#: consensus, Critic-B test quality: planted-table controls in a disposable
#: copy, the REVERT and NOTICE lines, the non-ASCII rewrite, the template
#: round-trip, dry-run and second-run through the scalar MIGRATE branch, and
#: the shipped-shape guard over every tag, release candidates included). A
#: RAW string: the escapes below are test SOURCE, written as is.
_UPGRADE_TESTS_A3 = r'''class TestScalarBranchIsGeneric(_MigrationHarness):
    """ADR-149 Amendment 3 (S357) - the scalar branch is GENERIC, proved on
    PLANTED leaves that no code names, in a disposable copy of upgrade.sh
    (never a product seam). RED on 19771fa1: the scalar leaf model had its
    own code, and a table entry nothing named was never read.
    """

    _TABLE_ANCHOR = '  "model": {\n'
    _PLANTED = (
        '  "plantedScalarA": {"old": null, "superseded": ["x-a"], "new": "x-b"},\n'
        '  "plantedScalarB": {"old": "y-old", "new": "y-new"},\n'
        '  "plantedOptIn": {"old": null, "new": "z-new", "opt_in": true,\n'
        '                   "cost_note": "planted cost note"},\n'
    )

    def _planted_upgrade(self, plant: Optional[str] = None) -> Path:
        text = UPGRADE_SH.read_text(encoding="utf-8")
        self.assertEqual(text.count(self._TABLE_ANCHOR), 1,
                         "the plant anchor moved: fix the control, never skip it")
        dst = Path(self._tmp) / "fw" / "scripts" / "upgrade.sh"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(
            text.replace(self._TABLE_ANCHOR,
                         (self._PLANTED if plant is None else plant)
                         + self._TABLE_ANCHOR),
            encoding="utf-8",
        )
        return dst

    def _run_planted(
        self, extra: Optional[List[str]] = None, plant: Optional[str] = None
    ) -> "subprocess.CompletedProcess[str]":
        args = ["bash", str(self._planted_upgrade(plant)), str(self.target),
                "--settings-migrate-only", "--no-replay", "--no-deprecation-warn"]
        args.extend(extra or [])
        proc = subprocess.run(args, capture_output=True, text=True, timeout=120,
                              env=_clean_env(None))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc

    def test_planted_superseded_and_old_scalars_migrate(self) -> None:
        self.seed({"plantedScalarA": "x-a", "plantedScalarB": "y-old"})
        proc = self._run_planted()
        data = self.read_settings()
        self.assertEqual(data["plantedScalarA"], "x-b")
        self.assertEqual(data["plantedScalarB"], "y-new")
        self.assertIn("MIGRATE (matched SUPERSEDED shipped baseline -> "
                      "new baseline): plantedScalarA", proc.stdout)
        self.assertIn("MIGRATE (matched OLD baseline -> new baseline): "
                      "plantedScalarB", proc.stdout)
        self.assertIn("REVERT: to keep the previous value, merge "
                      + json.dumps({"plantedScalarA": "x-a"})
                      + " into .claude/settings.local.json", proc.stdout)

    def test_planted_absent_scalar_is_set_and_custom_is_preserved(self) -> None:
        self.seed({"plantedScalarB": "adopter-choice"})
        proc = self._run_planted()
        data = self.read_settings()
        self.assertEqual(data["plantedScalarA"], "x-b")
        self.assertEqual(data["plantedScalarB"], "adopter-choice")
        self.assertIn("WARNING: plantedScalarB is ADOPTER-CUSTOMIZED", proc.stderr)
        self.assertNotIn("adopter-choice", proc.stdout + proc.stderr,
                         "no-value-echo: an adopter value is never printed")

    def test_planted_opt_in_leaf_is_written_only_with_the_flag(self) -> None:
        self.seed({})
        proc = self._run_planted()
        self.assertNotIn("plantedOptIn", self.read_settings())
        self.assertIn("WARNING: plantedOptIn NOT written (opt-in leaf)", proc.stderr)
        self.assertIn("planted cost note", proc.stderr)
        self.setUp()
        self.seed({})
        self._run_planted(["--adopt-setting", "plantedOptIn"])
        self.assertEqual(self.read_settings()["plantedOptIn"], "z-new")
        self.setUp()
        self.seed({"plantedOptIn": "adopter-z"})
        proc = self._run_planted(["--adopt-setting", "plantedOptIn"])
        self.assertEqual(self.read_settings()["plantedOptIn"], "adopter-z")
        self.assertIn("OK (present - PRESERVED; opt-in leaf): "
                      "plantedOptIn", proc.stdout)
        self.assertNotIn("WARNING: plantedOptIn", proc.stderr)

    #: A planted scalar gated on the OTHER array leaf of the table. RED on
    #: the r9 derivation of this wave: the gate saw only availableModels,
    #: so a leaf gated on fallbackModel always failed with a false warning.
    _GATED_ON_FALLBACK = (
        '  "plantedGated": {"old": null, "new": "claude-opus-5",\n'
        '                   "requires_member_of": "fallbackModel"},\n'
    )

    def test_requires_member_of_reads_every_array_leaf(self) -> None:
        member = baselines()["fallbackModel"]["new"]
        self.assertIn("claude-opus-5", member)
        for dry in (False, True):
            with self.subTest(dry=dry):
                self.setUp()
                self.seed({"fallbackModel": list(member)})
                before = self.settings_path.read_bytes()
                proc = self._run_planted(["--dry-run"] if dry else None,
                                         plant=self._GATED_ON_FALLBACK)
                self.assertNotIn("WARNING: plantedGated", proc.stderr)
                if dry:
                    self.assertIn("(dry-run) would SET (absent [== old "
                                  "baseline] -> new baseline): plantedGated",
                                  proc.stdout)
                    self.assertEqual(self.settings_path.read_bytes(), before)
                else:
                    self.assertEqual(self.read_settings()["plantedGated"],
                                     "claude-opus-5")
        self.setUp()
        self.seed({"fallbackModel": ["claude-sonnet-5"]})
        proc = self._run_planted(plant=self._GATED_ON_FALLBACK)
        self.assertNotIn("plantedGated", self.read_settings())
        self.assertIn("WARNING: plantedGated NOT migrated: claude-opus-5 is not "
                      "an exact entry of the adopter fallbackModel", proc.stderr)

    #: A planted ARRAY leaf that no code names, and a scalar gated on it.
    #: RED on the r10 derivation of this wave: the array pass walked a
    #: literal tuple, so the planted array was never migrated and the gate
    #: always read it as missing.
    _PLANTED_ARRAY = (
        '  "plantedArray": {"old": ["pa-old"], "superseded": [["pa-s1", "pa-s2"]],\n'
        '                   "new": ["pa-new", "claude-opus-5"]},\n'
        '  "plantedOnArray": {"old": null, "new": "claude-opus-5",\n'
        '                     "requires_member_of": "plantedArray"},\n'
    )

    def test_array_pass_walks_every_array_leaf_of_the_table(self) -> None:
        new = ["pa-new", "claude-opus-5"]
        for seed, verdict in (
            ({"plantedArray": ["pa-old"]},
             "MIGRATE (matched OLD baseline -> new baseline): plantedArray"),
            ({"plantedArray": ["pa-s1", "pa-s2"]},
             "MIGRATE (matched SUPERSEDED shipped baseline -> new baseline): "
             "plantedArray"),
            ({}, "SET (absent -> new baseline): plantedArray"),
        ):
            with self.subTest(seed=seed):
                self.setUp()
                self.seed(dict(seed))
                proc = self._run_planted(plant=self._PLANTED_ARRAY)
                data = self.read_settings()
                self.assertIn(verdict, proc.stdout)
                self.assertEqual(data["plantedArray"], new)
                self.assertEqual(data["plantedOnArray"], "claude-opus-5")
                self.assertNotIn("WARNING: plantedOnArray", proc.stderr)
        self.setUp()
        self.seed({"plantedArray": ["adopter-a"]})
        proc = self._run_planted(plant=self._PLANTED_ARRAY)
        data = self.read_settings()
        self.assertEqual(data["plantedArray"], ["adopter-a"])
        self.assertIn("WARNING: plantedArray is ADOPTER-CUSTOMIZED", proc.stderr)
        self.assertNotIn("plantedOnArray", data)
        self.assertIn("WARNING: plantedOnArray NOT migrated: claude-opus-5 is "
                      "not an exact entry of the adopter plantedArray", proc.stderr)
        self.assertNotIn("adopter-a", proc.stdout + proc.stderr,
                         "no-value-echo: an adopter value is never printed")

    #: on_migrate_of as DATA (Owner OQ-8, 2026-09-24): a planted opt-in
    #: leaf takes a planted value when a planted scalar migrates off a
    #: named value, and a rule that names a leaf walked AFTER it is a
    #: named warning, never a silent skip. RED on the r11 derivation of
    #: this wave, which had no such attribute.
    _PLANTED_COMPANION = (
        '  "plantedPin": {"old": null, "superseded": ["p-old"], "new": "p-new"},\n'
        '  "plantedKeep": {"old": null, "new": "k-new", "opt_in": true,\n'
        '                  "cost_note": "planted cost note",\n'
        '                  "on_migrate_of": {"plantedPin": {"p-old": "k-kept"}},\n'
        '                  "on_migrate_note": "planted keep note"},\n'
        '  "plantedEarly": {"old": null, "new": "e-new", "opt_in": true,\n'
        '                   "on_migrate_of": {"plantedLate": {"l-old": "e-kept"}}},\n'
        '  "plantedLate": {"old": null, "superseded": ["l-old"], "new": "l-new"},\n'
    )

    def test_on_migrate_of_is_generic_data(self) -> None:
        self.seed({"plantedPin": "p-old", "plantedLate": "l-old"})
        proc = self._run_planted(plant=self._PLANTED_COMPANION)
        data = self.read_settings()
        self.assertEqual(data["plantedPin"], "p-new")
        self.assertEqual(data["plantedKeep"], "k-kept")
        lines = proc.stdout.splitlines()
        at = [i for i, ln in enumerate(lines)
              if "MIGRATE (plantedPin migrated off p-old and plantedKeep was "
                 "absent -> k-kept): plantedKeep" in ln]
        self.assertEqual(len(at), 1, proc.stdout)
        self.assertIn("REVERT: ", lines[at[0] + 1])
        self.assertIn("NOTICE: plantedKeep = k-kept planted keep note", proc.stdout)
        self.assertNotIn("WARNING: plantedKeep", proc.stderr)
        # the rule that names a leaf walked later: named, and not applied
        self.assertEqual(data["plantedLate"], "l-new")
        self.assertNotIn("plantedEarly", data)
        self.assertIn("WARNING: plantedEarly on_migrate_of names plantedLate",
                      proc.stderr)

    def test_on_migrate_of_never_beats_the_flag_or_a_present_value(self) -> None:
        for seed, extra, want in (
            ({"plantedPin": "p-old"}, ["--adopt-setting", "plantedKeep"], "k-new"),
            ({"plantedPin": "p-old", "plantedKeep": "adopter-k"}, None, "adopter-k"),
        ):
            with self.subTest(seed=seed, flag=extra is not None):
                self.setUp()
                self.seed(dict(seed))
                proc = self._run_planted(extra, plant=self._PLANTED_COMPANION)
                self.assertEqual(self.read_settings()["plantedKeep"], want)
                self.assertNotIn("plantedKeep was absent", proc.stdout)


class TestBackupIsAPrecondition(_MigrationHarness):
    """ADR-149 Amendment 3 (S357) - the REVERT lines name the pre-migration
    backup, so a backup that cannot be written must stop the migration
    (named, settings.json untouched). Proved by a planted FAULT in a
    disposable copy of upgrade.sh (never a product seam): the copy of the
    backup is replaced by `false`. RED on the r9 derivation of this wave,
    where the failed copy was swallowed and the migration went on.
    """

    _BACKUP_COPY = ('cp "$settings" '
                    '"$BAK_DIR/.claude/settings.json.pre-t54-migration"')

    def _faulty_upgrade(self) -> Path:
        text = UPGRADE_SH.read_text(encoding="utf-8")
        self.assertEqual(text.count(self._BACKUP_COPY), 1,
                         "the fault anchor moved: fix the control, never skip it")
        dst = Path(self._tmp) / "fw" / "scripts" / "upgrade.sh"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text.replace(self._BACKUP_COPY, "false"),
                       encoding="utf-8")
        return dst

    def test_a_failed_backup_skips_the_migration(self) -> None:
        self.seed({"availableModels":
                   list(baselines()["availableModels"]["old"])})
        before = self.settings_path.read_bytes()
        proc = subprocess.run(
            ["bash", str(self._faulty_upgrade()), str(self.target),
             "--settings-migrate-only", "--no-replay", "--no-deprecation-warn"],
            capture_output=True, text=True, timeout=120, env=_clean_env(None))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.settings_path.read_bytes(), before)
        self.assertIn("settings baseline migration SKIPPED", proc.stderr)
        self.assertIn("pre-migration backup could", proc.stderr)
        self.assertNotIn("BACKED UP", proc.stdout)
        self.assertNotIn("REVERT", proc.stdout)
        self.assertNotIn("MIGRATE (", proc.stdout)
        self.assertRegex(proc.stderr, r'migration alone:  scripts/upgrade.sh \S+ '
                         r'--settings-migrate-only\n')

    def test_the_rerun_hint_keeps_the_operator_flags(self) -> None:
        """vX (fix round r13): the ACTION line dropped every --adopt-setting
        the operator passed, so the suggested re-run migrated WITHOUT the
        opt-in. RED on the r12 derivation of this wave."""
        self.seed({"availableModels":
                   list(baselines()["availableModels"]["old"])})
        proc = subprocess.run(
            ["bash", str(self._faulty_upgrade()), str(self.target),
             "--settings-migrate-only", "--no-replay", "--no-deprecation-warn",
             "--adopt-setting", "effortLevel", "--adopt-setting", "plantedKey",
             "--allow-old-claude-code"],
            capture_output=True, text=True, timeout=120, env=_clean_env(None))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertRegex(proc.stderr, r'migration alone:  scripts/upgrade.sh \S+ '
                         r'--settings-migrate-only --adopt-setting effortLevel '
                         r'--adopt-setting plantedKey --allow-old-claude-code\n')


class TestMigrationOutputOracles(_MigrationHarness):
    """ADR-149 Amendment 3 (S357) - what the operator SEES and what the file
    KEEPS: every MIGRATE line is followed by its REVERT line, the model
    notice names the CLI floor, text outside ASCII is written as is, a
    template-shaped file changes only the migrated lines - plus, when the
    migration appends a key, a trailing comma on the line before it (the
    template a release shipped) - and the dry-run and second-run oracles go
    through the scalar MIGRATE branch.
    """

    #: availableModels and pin every release from v1.4.0-rc.1 to the last
    #: one before Amendment 3 shipped (frozen literals, measured S357).
    SHIPPED_V14_AVAILABLE = [
        "claude-opus-4-8", "claude-fable-5", "claude-sonnet-4-6",
        "claude-haiku-4-5", "claude-opus-5", "claude-sonnet-5",
        "claude-fable-5-1",
    ]
    SHIPPED_PIN = "claude-opus-5"

    def _v14_seed(self) -> Dict:
        return {"availableModels": list(self.SHIPPED_V14_AVAILABLE),
                "model": self.SHIPPED_PIN}

    def _every_leaf_migrates_seed(self) -> Dict:
        seed = self._v14_seed()
        seed["permissions"] = {
            "defaultMode": baselines()["permissions.defaultMode"]["old"]}
        seed["hooks"] = {"PreToolUse": [{"matcher": "Edit", "hooks": [
            {"type": "command", "command": "bash h.sh check_pair_rail.py",
             "timeout": 60}]}]}
        return seed

    def _assert_each_migrate_line_has_a_revert_line(self, stdout: str) -> None:
        lines = stdout.splitlines()
        migrate_at = [i for i, ln in enumerate(lines) if "MIGRATE (" in ln]
        self.assertGreaterEqual(len(migrate_at), 4, stdout)
        for i in migrate_at:
            self.assertLess(i + 1, len(lines), lines[i])
            self.assertIn("REVERT: ", lines[i + 1], lines[i])

    def test_every_migrate_line_is_followed_by_its_revert_line(self) -> None:
        old_mode = baselines()["permissions.defaultMode"]["old"]
        self.seed(self._every_leaf_migrates_seed())
        proc = self.run_migration()
        self._assert_each_migrate_line_has_a_revert_line(proc.stdout)
        self.assertIn("merge " + json.dumps({"model": self.SHIPPED_PIN})
                      + " into .claude/settings.local.json", proc.stdout)
        self.assertIn("merge " + json.dumps({"permissions": {"defaultMode": old_mode}}),
                      proc.stdout)
        self.assertIn("REVERT: copy the pre-migration backup", proc.stdout)

    def test_every_dry_run_migrate_line_is_followed_by_a_revert_line(self) -> None:
        """A dry run writes no backup, yet each of its MIGRATE lines still
        carries a REVERT line; RED on the first derivation of this wave,
        where the array and hook MIGRATE lines printed none in a dry run.
        """
        self.seed(self._every_leaf_migrates_seed())
        before = self.settings_path.read_bytes()
        proc = self.run_migration(dry=True)
        self.assertEqual(self.settings_path.read_bytes(), before)
        self._assert_each_migrate_line_has_a_revert_line(proc.stdout)
        self.assertIn("REVERT: an apply run backs up .claude/settings.json",
                      proc.stdout)
        self.assertNotIn("REVERT: copy the pre-migration backup", proc.stdout)

    def test_model_notice_names_the_cli_floor(self) -> None:
        spec = baselines()["model"]
        self.assertIn("2.1.280", spec.get("notice", ""))
        self.seed(self._v14_seed())
        proc = self.run_migration()
        self.assertIn("NOTICE: model = " + spec["new"] + " " + spec["notice"],
                      proc.stdout)

    def test_rewrite_keeps_text_outside_ascii_unescaped(self) -> None:
        """RED on 19771fa1 for exactly this reason: json.dump escaped every
        character outside ASCII. The fixture also migrates on 19771fa1 (the
        OLD availableModels), so only the escaping can fail it.
        """
        text = "ação — ≥ ✅"
        obj = {"_comment": text,
               "availableModels": list(baselines()["availableModels"]["old"])}
        self.settings_path.write_text(
            json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        self.run_migration()
        raw = self.settings_path.read_text(encoding="utf-8")
        self.assertIn(text, raw)
        self.assertNotIn("\\u", raw)

    def test_lone_surrogate_falls_back_to_the_escaped_writer(self) -> None:
        """json.load accepts an escaped lone surrogate, which UTF-8 cannot
        encode: the writer falls back to the escaped form, so the file still
        migrates. RED on the r8 derivation of this wave, where the write
        failed and the whole migration was skipped.
        """
        seed = self._v14_seed()
        seed["_x"] = "\ud800"
        self.settings_path.write_text(json.dumps(seed, indent=2) + "\n",
                                      encoding="utf-8")
        proc = self.run_migration()
        data = self.read_settings()
        self.assertEqual(data["model"], baselines()["model"]["new"])
        self.assertEqual(data["_x"], "\ud800")
        self.assertIn("\\ud800", self.settings_path.read_text(encoding="utf-8"))
        self.assertNotIn("SKIPPED", proc.stdout + proc.stderr)

    def test_template_shaped_install_changes_only_the_migrated_lines(self) -> None:
        """The base template with the pin and the last id reverted to what
        the releases before Amendment 3 shipped migrates back to the
        template BYTE FOR BYTE: no line outside the migrated leaves changes.
        """
        tpl = TEMPLATE_SETTINGS.read_text(encoding="utf-8")
        new = baselines()["availableModels"]["new"]
        pin_line = '  "model": "%s",\n' % baselines()["model"]["new"]
        tail = '    "%s",\n    "%s"\n  ],\n' % (new[-2], new[-1])
        self.assertEqual(tpl.count(pin_line), 1)
        self.assertEqual(tpl.count(tail), 1)
        seed = tpl.replace(pin_line, '  "model": "%s",\n' % self.SHIPPED_PIN)
        seed = seed.replace(tail, '    "%s"\n  ],\n' % new[-2])
        self.assertEqual(json.loads(seed)["availableModels"], self.SHIPPED_V14_AVAILABLE)
        self.settings_path.write_text(seed, encoding="utf-8")
        self.run_migration()
        self.assertEqual(self.settings_path.read_text(encoding="utf-8"), tpl)

    #: A release whose base template the OQ-8 append path meets AS SHIPPED
    #: (the last tag before Amendment 3; vX, fix round r13).
    SHIPPED_TEMPLATE_TAG = "v1.4.1-rc.1"

    def test_a_shipped_template_changes_the_migrated_lines_and_one_comma(self) -> None:
        """vX (fix round r13): the base template that v1.4.1-rc.1 shipped,
        read with git as is, through the pin migration that APPENDS
        effortLevel (Owner OQ-8). Every line outside the migrated leaves
        stays byte-identical except the line just before the appended key,
        which gains a trailing comma - the rule ADR-149 A3.2 item 6 states.
        The template test above seeds from the CURRENT template, which
        already carries effortLevel, so it never met the append path; the
        earlier claim ("every line outside the migrated leaves") was false
        on it. Skips, named, in a checkout without the tag.
        """
        git = shutil.which("git")
        if git is None:
            self.skipTest("git is not on PATH: the shipped template cannot be read")
        show = subprocess.run(
            [git, "-C", str(REPO_ROOT), "show",
             self.SHIPPED_TEMPLATE_TAG + ":templates/settings/settings.base.json"],
            capture_output=True, text=True, timeout=60)
        if show.returncode != 0:
            self.skipTest("%s is not in this checkout (a shallow clone fetches no "
                          "tag): the shipped template cannot be read"
                          % self.SHIPPED_TEMPLATE_TAG)
        seed = show.stdout
        shipped = json.loads(seed)
        self.assertEqual(shipped.get("model"), self.SHIPPED_PIN)
        self.assertEqual(shipped.get("availableModels"), self.SHIPPED_V14_AVAILABLE)
        self.assertNotIn("effortLevel", shipped)
        # The shipped file is in the writer's own format (it round-trips).
        self.assertEqual(json.dumps(shipped, indent=2, ensure_ascii=False) + "\n",
                         seed)
        new = baselines()["availableModels"]["new"]
        self.assertEqual(new[:-1], self.SHIPPED_V14_AVAILABLE)
        effort = baselines()["effortLevel"]["on_migrate_of"]["model"][self.SHIPPED_PIN]
        pin_old = '  "model": "%s",\n' % self.SHIPPED_PIN
        tail_old = '    "%s"\n  ],\n' % new[-2]
        self.assertEqual(seed.count(pin_old), 1)
        self.assertEqual(seed.count(tail_old), 1)
        expected = seed.replace(
            pin_old, '  "model": "%s",\n' % baselines()["model"]["new"])
        expected = expected.replace(
            tail_old, '    "%s",\n    "%s"\n  ],\n' % (new[-2], new[-1]))
        lines = expected.splitlines(True)
        self.assertEqual(lines[-1], "}\n")
        self.assertFalse(lines[-2].rstrip("\n").endswith(","), lines[-2])
        lines[-2] = lines[-2][:-1] + ",\n"  # the one line outside the leaves
        lines.insert(-1, '  "effortLevel": "%s"\n' % effort)
        self.settings_path.write_text(seed, encoding="utf-8")
        self.run_migration()
        self.assertEqual(self.settings_path.read_text(encoding="utf-8"),
                         "".join(lines))

    def test_dry_run_goes_through_the_scalar_migrate_branch(self) -> None:
        self.seed(self._v14_seed())
        before = self.settings_path.read_bytes()
        proc = self.run_migration(dry=True)
        self.assertEqual(self.settings_path.read_bytes(), before)
        self.assertIn("(dry-run) would MIGRATE (matched SUPERSEDED shipped "
                      "baseline -> new baseline): model", proc.stdout)
        self.assertFalse((self.target / ".claude.bak").exists(),
                         "--dry-run must not create the backup dir")

    def test_v14_shape_second_run_is_an_idempotent_noop(self) -> None:
        seed = self._v14_seed()
        seed["fallbackModel"] = list(baselines()["fallbackModel"]["new"])
        seed["permissions"] = {
            "defaultMode": baselines()["permissions.defaultMode"]["new"]}
        self.seed(seed)
        self.run_migration()
        first = self.settings_path.read_bytes()
        proc = self.run_migration()
        self.assertEqual(self.settings_path.read_bytes(), first)
        self.assertNotIn("MIGRATE (", proc.stdout)
        self.assertNotIn("SET (", proc.stdout)
        self.assertIn("idempotent no-op", proc.stdout)


class TestEveryShippedShapeIsKnown(_MigrationHarness):
    """ADR-149 Amendment 3 (S357) - every value a TAG shipped, release
    candidates included, must be a known baseline (old, superseded or new)
    of the table, or its adopters are read as ADOPTER-CUSTOMIZED forever.
    Two guards: SHIPPED_AT_S357 is a literal FROZEN over the v1.* tags that
    existed at S357 (measured with `git show <tag>:templates/settings/
    settings.base.json`; it runs in every checkout), and the walk reads
    the same file from EVERY v1.* tag reachable from HEAD, so a release
    tagged later is covered without editing a list (a checkout without
    tags - a shallow CI clone - skips the walk, named).
    """

    _V10 = ["claude-opus-4-8", "claude-fable-5", "claude-sonnet-4-6",
            "claude-haiku-4-5"]
    _V12 = _V10 + ["claude-opus-5", "claude-sonnet-5"]
    _V14 = _V12 + ["claude-fable-5-1"]
    #: (tags, availableModels, model or None when absent, fallbackModel)
    SHIPPED_AT_S357 = (
        (("v1.0.0", "v1.0.1-rc.1", "v1.0.1", "v1.1.0-rc.1", "v1.1.0"),
         _V10, None, ["claude-opus-4-8"]),
        (("v1.2.0-rc.1", "v1.2.0-rc.2", "v1.2.0-rc.3", "v1.2.0",
          "v1.3.0-rc.1", "v1.3.0-rc.2", "v1.3.0-rc.3", "v1.3.0-rc.4", "v1.3.0"),
         _V12, "claude-opus-5", ["claude-opus-5"]),
        (("v1.4.0-rc.1", "v1.4.0", "v1.4.1-rc.1"),
         _V14, "claude-opus-5", ["claude-opus-5"]),
    )

    @staticmethod
    def _known(spec: Dict) -> List:
        return [spec.get("old"), spec["new"]] + list(spec.get("superseded", []))

    def test_every_shipped_value_is_a_known_baseline(self) -> None:
        for tags, avail, model, fallback in self.SHIPPED_AT_S357:
            with self.subTest(tags=tags[0]):
                self.assertIn(avail, self._known(baselines()["availableModels"]))
                self.assertIn(fallback, self._known(baselines()["fallbackModel"]))
                self.assertIn(model, self._known(baselines()["model"]))

    def test_every_shipped_shape_migrates_end_to_end(self) -> None:
        for tags, avail, model, fallback in self.SHIPPED_AT_S357:
            with self.subTest(tags=tags[0]):
                self.setUp()
                seed = {"availableModels": list(avail),
                        "fallbackModel": list(fallback)}
                if model is not None:
                    seed["model"] = model
                self.seed(seed)
                self.run_migration()
                data = self.read_settings()
                self.assertEqual(data["availableModels"],
                                 baselines()["availableModels"]["new"])
                self.assertEqual(data["fallbackModel"],
                                 baselines()["fallbackModel"]["new"])
                self.assertEqual(data["model"], baselines()["model"]["new"])

    def test_every_tag_reachable_from_head_shipped_a_known_shape(self) -> None:
        git = shutil.which("git")
        if git is None:
            self.skipTest("git is not on PATH: the tag walk cannot run")
        proc = subprocess.run(
            [git, "-C", str(REPO_ROOT), "tag", "--merged", "HEAD", "--list",
             "v1.*"],
            capture_output=True, text=True, timeout=60)
        tags = sorted(t for t in proc.stdout.split() if t) if proc.returncode == 0 else []
        if not tags:
            self.skipTest("no v1.* tag reachable from HEAD in this checkout "
                          "(a shallow clone fetches none): nothing to walk; "
                          "SHIPPED_AT_S357 still runs")
        read = 0
        for tag in tags:
            show = subprocess.run(
                [git, "-C", str(REPO_ROOT), "show",
                 tag + ":templates/settings/settings.base.json"],
                capture_output=True, text=True, timeout=60)
            if show.returncode != 0:
                continue
            shipped = json.loads(show.stdout)
            read += 1
            with self.subTest(tag=tag):
                for key in ("availableModels", "fallbackModel", "model"):
                    self.assertIn(shipped.get(key), self._known(baselines()[key]),
                                  "%s shipped a %s the table does not know"
                                  % (tag, key))
        self.assertGreater(read, 0, "v1.* tags found, none carries the template")


'''

#: OQ-8 / OQ-9 test classes (Owner decisions 2026-09-24), appended with
#: _UPGRADE_TESTS_A3. A RAW string: the escapes below are test SOURCE.
_UPGRADE_TESTS_OQ8_OQ9 = r'''class TestPinMigrationKeepsTheEffort(_MigrationHarness):
    """ADR-149 Amendment 3 (S357; Owner OQ-8, 2026-09-24, verbatim «Migrar
    gravando 'high' (Recomendado)») - when the upgrade migrates the shipped
    pin claude-opus-5 to claude-opus-5-5 in a file with NO effortLevel, it
    writes the value the table maps for that pin (high, the Opus 5
    default), with a named MIGRATE line and its REVERT line. RED on the r11
    derivation of this wave: the pin migrated and effortLevel stayed absent
    (the session moved from high to the Opus 5.5 default, medium).
    Expectations derive from the table, not from literals.
    """

    _FLAG = ["--adopt-setting", "effortLevel"]

    @staticmethod
    def _rule() -> Dict:
        return baselines()["effortLevel"]["on_migrate_of"]["model"]

    def _shipped_pin(self) -> str:
        pins = [p for p in baselines()["model"]["superseded"] if p in self._rule()]
        self.assertTrue(pins, "no superseded pin has an effort mapping")
        return pins[0]

    def _seed_shipped(self, **extra) -> None:
        seed = {"model": self._shipped_pin(),
                "availableModels": list(baselines()["availableModels"]["new"])}
        seed.update(extra)
        self.seed(seed)

    def _line(self) -> str:
        pin = self._shipped_pin()
        return ("MIGRATE (model migrated off " + pin + " and effortLevel was "
                "absent -> " + self._rule()[pin] + "): effortLevel")

    def test_the_table_maps_the_shipped_pin_to_high(self) -> None:
        self.assertEqual(self._rule().get("claude-opus-5"), "high")
        self.assertIn("claude-opus-5", baselines()["model"]["superseded"])
        self.assertNotEqual(self._rule()["claude-opus-5"],
                            baselines()["effortLevel"]["new"])

    def test_pin_migration_writes_the_mapped_effort(self) -> None:
        self._seed_shipped()
        proc = self.run_migration()
        data = self.read_settings()
        self.assertEqual(data["model"], baselines()["model"]["new"])
        self.assertEqual(data["effortLevel"], self._rule()[self._shipped_pin()])
        lines = proc.stdout.splitlines()
        at = [i for i, ln in enumerate(lines) if self._line() in ln]
        self.assertEqual(len(at), 1, proc.stdout)
        self.assertIn("REVERT: to drop it, delete effortLevel", lines[at[0] + 1])
        self.assertIn("NOTICE: effortLevel = high", proc.stdout)
        self.assertNotIn("WARNING: effortLevel", proc.stderr)

    def test_second_run_is_an_idempotent_noop(self) -> None:
        self._seed_shipped()
        self.run_migration()
        first = self.settings_path.read_bytes()
        proc = self.run_migration()
        self.assertEqual(self.settings_path.read_bytes(), first)
        self.assertNotIn("MIGRATE (", proc.stdout)
        self.assertIn("OK (present - PRESERVED; opt-in leaf): effortLevel",
                      proc.stdout)

    def test_dry_run_previews_without_writing(self) -> None:
        self._seed_shipped()
        before = self.settings_path.read_bytes()
        proc = self.run_migration(dry=True)
        self.assertEqual(self.settings_path.read_bytes(), before)
        self.assertIn("(dry-run) would " + self._line(), proc.stdout)
        self.assertFalse((self.target / ".claude.bak").exists())

    def test_an_adopter_effort_level_is_never_overwritten(self) -> None:
        for custom in ("medium", "low", "xhigh", "max"):
            for extra in (None, self._FLAG):
                with self.subTest(custom=custom, flag=extra is not None):
                    self.setUp()
                    self._seed_shipped(effortLevel=custom)
                    proc = self.run_migration(extra_args=extra)
                    data = self.read_settings()
                    self.assertEqual(data["effortLevel"], custom)
                    self.assertEqual(data["model"], baselines()["model"]["new"])
                    self.assertNotIn("effortLevel was absent", proc.stdout)

    def test_the_opt_in_flag_wins_over_the_mapped_effort(self) -> None:
        self._seed_shipped()
        proc = self.run_migration(extra_args=self._FLAG)
        self.assertEqual(self.read_settings()["effortLevel"],
                         baselines()["effortLevel"]["new"])
        self.assertNotIn("effortLevel was absent", proc.stdout)

    def test_no_migration_means_no_effort_write(self) -> None:
        cases = (
            # the pin is SET (the file had none): no pin to keep the effort of
            {"availableModels": list(baselines()["availableModels"]["new"])},
            # a custom pin is preserved, not migrated
            {"model": "claude-sonnet-5",
             "availableModels": list(baselines()["availableModels"]["new"])},
            # the allowlist withholds the new pin: the pin is left untouched
            {"model": "claude-opus-5",
             "availableModels": ["claude-opus-5", "adopter-only-model"]},
        )
        for seed in cases:
            with self.subTest(seed=sorted(seed)):
                self.setUp()
                self.seed(dict(seed))
                proc = self.run_migration()
                self.assertNotIn("effortLevel", self.read_settings())
                self.assertNotIn("effortLevel was absent", proc.stdout)

    def test_adopt_setting_under_no_settings_migrate_is_named(self) -> None:
        """A-R3M-03 (rail round 3): the flag feeds only the T5.4 migration;
        under --no-settings-migrate it was dropped with no line at all."""
        self._seed_shipped()
        before = self.settings_path.read_bytes()
        proc = self.run_migration(
            extra_args=["--no-settings-migrate"] + self._FLAG)
        self.assertEqual(self.settings_path.read_bytes(), before)
        self.assertIn("WARNING: --adopt-setting effortLevel ignored: "
                      "--no-settings-migrate skips the T5.4 settings migration",
                      proc.stderr)


class TestClaudeCodeFloor(_MigrationHarness):
    """ADR-149 Amendment 3 (S357; Owner OQ-9, 2026-09-24, verbatim «Exigir
    CC >= 2.1.280 (Recomendado)») - install.sh and upgrade.sh read the
    claude found on PATH: below the floor they REFUSE (exit 6) before any
    write unless --allow-old-claude-code is passed; no claude on PATH or an
    unreadable version is a named WARNING and the run goes on; a dry run
    names the refusal and writes nothing. The PATH here holds a FAKE claude
    (or none), never the operator's. RED on the r11 derivation of this wave:
    neither script read the CLI version. Fix round r13 (vX): the version is
    read only from the line naming (Claude Code) (another program's version
    printed first read as the CLI's, a supported CLI refused), a suffix after
    the three numbers counts as below the floor (2.1.280-beta.1 passed as
    2.1.280), and the probe reads no stdin and is stopped at a wall limit (a
    hanging CLI blocked every run) - RED on the r12 derivation.
    """

    _BEGIN = "# >>> claude-code-floor"
    _END = "# <<< claude-code-floor <<<\n"
    INSTALL_SH = REPO_ROOT / "scripts" / "install.sh"
    SUPPORT_MD = REPO_ROOT / "SUPPORT.md"

    def _block(self, path: Path) -> str:
        text = path.read_text(encoding="utf-8")
        self.assertEqual(text.count(self._BEGIN), 1, path)
        self.assertEqual(text.count(self._END), 1, path)
        start = text.index(self._BEGIN)
        return text[start:text.index(self._END) + len(self._END)]

    def _floor(self) -> str:
        block = self._block(UPGRADE_SH)
        line = [ln for ln in block.splitlines() if ln.startswith("CC_FLOOR_VERSION=")]
        self.assertEqual(len(line), 1, block)
        return line[0].split("=", 1)[1].strip('"')

    def _bin_with(self, output: Optional[str]) -> str:
        """A PATH whose only claude is a fake printing ``output`` (None =
        no claude at all); the rest of PATH minus every dir holding one."""
        if output is None:
            return self._bin_with_script(None)
        return self._bin_with_script("printf '%s\\n' '" + output + "'\n")

    def _bin_with_script(self, body: Optional[str]) -> str:
        """A PATH whose only claude is a fake running the sh ``body`` (None =
        no claude at all); the rest of PATH minus every dir holding one."""
        keep = []
        for d in os.environ.get("PATH", "").split(os.pathsep):
            cand = os.path.join(d, "claude")
            if d and not (os.path.isfile(cand) and os.access(cand, os.X_OK)):
                keep.append(d)
        for tool in ("bash", "python3", "git", "grep", "head", "sed", "sleep"):
            if shutil.which(tool, path=os.pathsep.join(keep)) is None:
                self.skipTest("PATH without claude lost %s" % tool)
        if body is None:
            return os.pathsep.join(keep)
        fake = Path(self._tmp) / "fakebin"
        fake.mkdir(exist_ok=True)
        exe = fake / "claude"
        exe.write_text("#!/bin/sh\n" + body, encoding="utf-8")
        exe.chmod(0o755)
        return os.pathsep.join([str(fake)] + keep)

    def _upgrade(self, path: str, extra: Optional[List[str]] = None,
                 script: Optional[Path] = None, stdin_text: Optional[str] = None
                 ) -> "subprocess.CompletedProcess[str]":
        args = ["bash", str(script or UPGRADE_SH), str(self.target),
                "--settings-migrate-only", "--no-replay", "--no-deprecation-warn"]
        args.extend(extra or [])
        return subprocess.run(args, capture_output=True, text=True, timeout=120,
                              input=stdin_text, env=_clean_env({"PATH": path}))

    def _v14_seed(self) -> None:
        self.seed({"model": "claude-opus-5",
                   "availableModels": list(baselines()["availableModels"]["new"])})

    def test_one_floor_in_both_scripts_the_notice_and_support(self) -> None:
        self.assertEqual(self._block(UPGRADE_SH), self._block(self.INSTALL_SH))
        floor = self._floor()
        self.assertRegex(floor, r"^\d+\.\d+\.\d+$")
        self.assertIn(floor, baselines()["model"]["notice"])
        self.assertIn("| Claude Code ≥ " + floor + " |",
                      self.SUPPORT_MD.read_text(encoding="utf-8"))
        for script in (UPGRADE_SH, self.INSTALL_SH):
            text = script.read_text(encoding="utf-8")
            self.assertIn("--allow-old-claude-code)", text, script)
            self.assertIn('_claude_code_floor_check "$ALLOW_OLD_CLAUDE_CODE" '
                          '"$DRY_RUN"', text, script)

    def test_below_the_floor_is_refused_before_any_write(self) -> None:
        # 2.1.99 < 2.1.280 numerically; a string comparison would pass it.
        for out in ("2.1.279 (Claude Code)", "2.1.99 (Claude Code)",
                    "1.9.999 (Claude Code)"):
            with self.subTest(version=out):
                self.setUp()
                self._v14_seed()
                before = self.settings_path.read_bytes()
                proc = self._upgrade(self._bin_with(out))
                self.assertEqual(proc.returncode, 6, proc.stdout + proc.stderr)
                self.assertIn("ERROR: Claude Code " + out.split()[0]
                              + " is below " + self._floor(), proc.stderr)
                self.assertEqual(self.settings_path.read_bytes(), before)
                self.assertFalse((self.target / ".claude.bak").exists())

    def test_at_or_above_the_floor_passes(self) -> None:
        floor = self._floor()
        # 2.1.1000 > 2.1.280 numerically; a string comparison would refuse it.
        for out in (floor + " (Claude Code)", "2.1.1000 (Claude Code)",
                    "3.0.0 (Claude Code)"):
            with self.subTest(version=out):
                self.setUp()
                self._v14_seed()
                proc = self._upgrade(self._bin_with(out))
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertIn("Claude Code:  " + out.split()[0] + " (floor "
                              + floor + ": OK)", proc.stdout)
                self.assertNotIn("Claude Code", proc.stderr)
                self.assertEqual(self.read_settings()["model"],
                                 baselines()["model"]["new"])

    def test_the_version_is_read_from_the_claude_code_line_only(self) -> None:
        """vX (fix round r13): the first x.y.z of the whole output was read,
        so another program's version printed first decided - a CLI below the
        floor passed, a supported one was refused. RED on the r12 derivation.
        """
        floor = self._floor()
        cases = (
            ("Node v22.3.0\n2.1.279 (Claude Code)", 6,
             "ERROR: Claude Code 2.1.279 is below " + floor, "stderr"),
            ("dependency 1.0.0\n" + floor + " (Claude Code)", 0,
             "Claude Code:  " + floor + " (floor " + floor + ": OK)", "stdout"),
        )
        for out, rc, line, stream in cases:
            with self.subTest(output=out.splitlines()[0]):
                self.setUp()
                self._v14_seed()
                before = self.settings_path.read_bytes()
                proc = self._upgrade(self._bin_with(out))
                self.assertEqual(proc.returncode, rc, proc.stdout + proc.stderr)
                self.assertIn(line, getattr(proc, stream))
                if rc:
                    self.assertEqual(self.settings_path.read_bytes(), before)

    def test_a_suffix_after_the_three_numbers_counts_as_below(self) -> None:
        """vX (fix round r13): 2.1.280-beta.1 passed as 2.1.280. A version
        with anything after its three numbers counts as below the floor,
        whatever the numbers. RED on the r12 derivation."""
        floor = self._floor()
        major, minor, patch = floor.split(".")
        later = "%s.%s.%d" % (major, minor, int(patch) + 1)
        for tok in (floor + "-beta.1", later + "-beta.1"):
            with self.subTest(version=tok):
                self.setUp()
                self._v14_seed()
                before = self.settings_path.read_bytes()
                proc = self._upgrade(self._bin_with(tok + " (Claude Code)"))
                self.assertEqual(proc.returncode, 6, proc.stdout + proc.stderr)
                self.assertIn("ERROR: Claude Code " + tok + " is below " + floor
                              + " (a version with anything after its three "
                              "numbers counts as below it)", proc.stderr)
                self.assertEqual(self.settings_path.read_bytes(), before)

    def test_the_override_flag_continues_with_a_named_warning(self) -> None:
        self._v14_seed()
        proc = self._upgrade(self._bin_with("2.1.279 (Claude Code)"),
                             ["--allow-old-claude-code"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("continuing because --allow-old-claude-code was passed",
                      proc.stderr)
        self.assertEqual(self.read_settings()["model"], baselines()["model"]["new"])

    def test_no_claude_or_an_unreadable_version_warns_and_goes_on(self) -> None:
        unreadable = ("WARNING: Claude Code version unreadable: no line of "
                      "'claude --version' names (Claude Code) with a version")
        for out, warning in (
            (None, "WARNING: Claude Code CLI not found on PATH"),
            ("claude, a build without a version", unreadable),
            # a version on a line that does not name Claude Code is not read
            ("2.1.1000", unreadable),
        ):
            with self.subTest(output=out):
                self.setUp()
                self._v14_seed()
                proc = self._upgrade(self._bin_with(out))
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertIn(warning, proc.stderr)
                self.assertEqual(self.read_settings()["model"],
                                 baselines()["model"]["new"])

    def test_a_hanging_cli_is_stopped_and_the_run_goes_on(self) -> None:
        """vX (fix round r13): the probe had no wall limit, so a CLI that
        hangs blocked every install and upgrade. Planted in a disposable copy
        of upgrade.sh with a 2-second limit (never a product seam); the fake
        claude is a shell whose CHILD sleeps holding the output open, so only
        a stop of the process group lets the run go on. RED on the r12
        derivation (no limit: the child held the capture for its full sleep).
        """
        text = UPGRADE_SH.read_text(encoding="utf-8")
        anchor = "\nCC_FLOOR_PROBE_SECONDS="
        self.assertEqual(text.count(anchor), 1,
                         "the plant anchor moved: fix the control, never skip it")
        value = text.split(anchor, 1)[1].split("\n", 1)[0]
        self.assertRegex(value, r"^[0-9]+$")
        self.assertLessEqual(int(value), 60, "the wall limit must stay short")
        dst = Path(self._tmp) / "fw" / "scripts" / "upgrade.sh"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text.replace(anchor + value + "\n", anchor + "2\n"),
                       encoding="utf-8")
        self._v14_seed()
        path = self._bin_with_script("sleep 60\necho '2.1.1000 (Claude Code)'\n")
        start = time.monotonic()
        proc = self._upgrade(path, script=dst)
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, 30, "the probe was not stopped at its limit")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("WARNING: Claude Code version unreadable: 'claude --version' "
                      "did not finish within 2s and was stopped", proc.stderr)
        self.assertEqual(self.read_settings()["model"], baselines()["model"]["new"])

    def test_the_probe_reads_no_stdin(self) -> None:
        """vX (fix round r13): the probe inherited the script's stdin, so a
        CLI that reads stdin could consume what was meant for the script
        (bash fed through a pipe). The fake claude reports a version below
        the floor when it can read a line: with stdin from /dev/null it
        reads none. RED on the r12 derivation."""
        floor = self._floor()
        self._v14_seed()
        path = self._bin_with_script(
            "if read -r _line; then echo '1.0.0 (Claude Code)'; "
            "else echo '" + floor + " (Claude Code)'; fi\n")
        proc = self._upgrade(path, stdin_text="a line meant for the script\n")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("Claude Code:  " + floor + " (floor " + floor + ": OK)",
                      proc.stdout)

    def test_the_harness_never_reads_the_host_cli(self) -> None:
        """vX (fix round r13): every spawn of this module (the plain
        run_migration included) runs with a FAKE claude at the floor first on
        PATH, so a host CLI below the floor can never turn these tests into
        exit 6, and a host CLI at any version never decides them. Before the
        cure _clean_env copied the host PATH: on a host with a claude on PATH
        the plain run_migration printed THAT version (measured S357 with
        2.1.281)."""
        floor = self._floor()
        env = _clean_env(None)
        found = shutil.which("claude", path=env["PATH"])
        self.assertIsNotNone(found)
        self.assertEqual(os.path.dirname(found), env["PATH"].split(os.pathsep)[0])
        self._v14_seed()
        proc = self.run_migration()
        self.assertIn("Claude Code:  " + floor + " (floor " + floor + ": OK)",
                      proc.stdout)

    def test_a_dry_run_names_the_refusal_and_writes_nothing(self) -> None:
        self._v14_seed()
        before = self.settings_path.read_bytes()
        proc = self._upgrade(self._bin_with("2.1.279 (Claude Code)"), ["--dry-run"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("(dry-run) would REFUSE: Claude Code 2.1.279", proc.stderr)
        self.assertEqual(self.settings_path.read_bytes(), before)

    def test_install_refuses_below_the_floor_before_any_write(self) -> None:
        target = Path(self._tmp) / "fresh"
        target.mkdir()
        proc = subprocess.run(
            ["bash", str(self.INSTALL_SH), str(target)],
            capture_output=True, text=True, timeout=120,
            env=_clean_env({"PATH": self._bin_with("2.1.279 (Claude Code)"),
                            "CEO_INSTALL_SKIP_SELF_SHA": "1"}))
        self.assertEqual(proc.returncode, 6, proc.stdout + proc.stderr)
        self.assertIn("ERROR: Claude Code 2.1.279 is below " + self._floor(),
                      proc.stderr)
        self.assertEqual(sorted(p.name for p in target.iterdir()), [])

    def test_both_helps_document_the_flag(self) -> None:
        for script in (UPGRADE_SH, self.INSTALL_SH):
            proc = subprocess.run(["bash", str(script), "--help"],
                                  capture_output=True, text=True, timeout=60,
                                  env=_clean_env(None))
            self.assertEqual(proc.returncode, 0, script)
            self.assertIn("--allow-old-claude-code", proc.stdout, script)


'''

# --------------------------------------------------------------------------
# Fix round r15 (rail round 2, P2): no test and no harness reads the host
# Claude Code CLI. The class: every test or shell harness that runs
# scripts/install.sh or scripts/upgrade.sh and inherits the host PATH read the
# operator's claude against the floor (a host below it turned them into exit 6
# before they exercised anything). Cured at the two points every such run goes
# through: the pytest isolation layer (_lib/test_isolation.py, Axis 4 — a FAKE
# claude at the floor first on PATH) and ONE byte-identical block in every
# shell harness that names an installer (an exported claude FUNCTION with the
# same answer), both guarded by TestNoHarnessReadsTheHostCli.
# --------------------------------------------------------------------------
TEST_ISOLATION_REL = ".claude/hooks/_lib/test_isolation.py"

#: The block every shell harness that names an installer carries, right after
#: its first top-level `set -` line. A RAW string: the escapes are shell.
_HARNESS_CLAUDE_STUB = r'''# >>> harness-claude-stub (ADR-149 Amendment 3) >>>
# scripts/install.sh and scripts/upgrade.sh read `claude --version` against the
# Claude Code floor (CC_FLOOR_VERSION) and refuse below it (exit 6). A harness
# never reads the host CLI: this block exports a claude FUNCTION that answers
# --version with the floor of the scripts/install.sh of its own checkout, and
# every bash the harness starts with this environment runs it before any
# claude on PATH, whatever PATH that bash is given (a bash started with an
# emptied environment, env -i, does not get it). Any other call exits 127. A
# case that needs another CLI runs `unset -f claude` first. The block is
# byte-identical in every
# harness that names an installer (TestNoHarnessReadsTheHostCli, in
# .claude/scripts/tests/test_upgrade_settings_migration.py, holds the copies
# equal and finds a harness without it).
_cc_stub_root="$(CDPATH='' cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
while [ ! -f "$_cc_stub_root/scripts/install.sh" ] && [ "$_cc_stub_root" != "/" ]; do
  _cc_stub_root="$(dirname "$_cc_stub_root")"
done
CC_STUB_FLOOR="$(sed -n 's/^CC_FLOOR_VERSION="\([0-9][0-9.]*\)"$/\1/p' "$_cc_stub_root/scripts/install.sh" 2>/dev/null || true)"
case "$CC_STUB_FLOOR" in
  ''|*[!0-9.]*)
    echo "ERROR: $_cc_stub_root/scripts/install.sh carries no single CC_FLOOR_VERSION line: the claude stub has no version to report" >&2
    exit 1 ;;
esac
export CC_STUB_FLOOR
claude() {
  if [ "$#" -eq 1 ] && [ "$1" = "--version" ]; then
    printf '%s (Claude Code)\n' "$CC_STUB_FLOOR"
    return 0
  fi
  echo "claude: the harness stub answers only --version" >&2
  return 127
}
export -f claude
# <<< harness-claude-stub <<<
'''

#: (harness, its first top-level `set -` line) — every tracked shell script
#: under a `tests` directory or under scripts/local/ (outside .claude/plans/
#: and fixtures) whose HEAD text names install.sh or upgrade.sh; measured on
#: 19771fa1, each line found ONCE in its file. The guard re-derives the set
#: from disk, so a harness added later without the block is RED.
_HARNESS_SET_LINES: List[Tuple[str, str]] = [
    ("scripts/local/smoke-install-parity.sh", "set -euo pipefail\n"),
    ("scripts/tests/smoke-install.sh", "set -euo pipefail\n"),
    ("scripts/tests/test-doctor-delivery-route.sh",
     "set -uo pipefail   # NOT -e: we assert on command failures explicitly.\n"),
    ("scripts/tests/test-doctor.sh",
     "set -uo pipefail   # NOT -e: we assert on command failures explicitly.\n"),
    ("scripts/tests/test-install-deny-baseline.sh", "set -euo pipefail\n"),
    ("scripts/tests/test-install-harness-codex.sh", "set -uo pipefail\n"),
    ("scripts/tests/test-install-harness-grok.sh", "set -uo pipefail\n"),
    ("scripts/tests/test-install-sandbox-merge.sh", "set -euo pipefail\n"),
    ("scripts/tests/test-install-upgrade-parity-e2e.sh",
     "set -uo pipefail   # NOT -e: failures are classified, not fatal-by-default.\n"),
    ("scripts/tests/test-installer-write-safety-e2e.sh",
     "set -uo pipefail   # NOT -e: we assert on command failures explicitly.\n"),
    ("scripts/tests/test-manifest-delivery-route.sh",
     "set -uo pipefail   # NOT -e: we assert on command failures explicitly.\n"),
    ("scripts/tests/test-night-mode-ignore-effect.sh", "set -uo pipefail\n"),
    ("scripts/tests/test-ownership-table.sh", "set -uo pipefail\n"),
    ("scripts/tests/test-parity-stale-planted.sh", "set -euo pipefail\n"),
    ("scripts/tests/test-protocol-pointer-inv4.sh", "set -uo pipefail\n"),
    ("scripts/tests/test-protocol-pointer-render.sh", "set -uo pipefail\n"),
    ("scripts/tests/test-schema-generation-pins-unit.sh", "set -uo pipefail\n"),
    ("scripts/tests/test-two-adopter-isolation-e2e.sh",
     "set -uo pipefail   # NOT -e: failures are asserted explicitly.\n"),
    ("scripts/tests/test-upgrade-dryrun-identity.sh",
     "set -uo pipefail   # NOT -e: we assert on command failures explicitly.\n"),
    ("scripts/tests/test-upgrade-exclusions.sh",
     "set -uo pipefail   # NOT -e: we assert on command failures explicitly.\n"),
    ("scripts/tests/test-upgrade-historical-adopter.sh",
     "set -uo pipefail   # NOT -e: every failure is asserted, never fatal-by-default.\n"),
    ("scripts/tests/test-upgrade-lifecycle-hooks-derived.sh",
     "set -uo pipefail   # NOT -e: every failure is asserted, never fatal-by-default.\n"),
    ("scripts/tests/test-upgrade-spec-ownership.sh",
     "set -uo pipefail   # NOT -e: we assert on command failures explicitly.\n"),
    ("scripts/tests/test-w3-vcures.sh", "set -euo pipefail\n"),
    ("scripts/tests/test_install_baseline_manifest.sh",
     "set -uo pipefail   # NOT -e: we assert on command failures explicitly.\n"),
    ("scripts/tests/test_install_state_replay.sh",
     "set -uo pipefail   # NOT -e: we assert on command failures explicitly.\n"),
]

#: The guard of the class (appended after TestClaudeCodeFloor). A RAW
#: string: the escapes below are test SOURCE.
_UPGRADE_TESTS_HARNESS_CLI = r'''class TestNoHarnessReadsTheHostCli(_MigrationHarness):
    """ADR-149 Amendment 3, fix round r15 (rail round 2 of the wave, P2): the
    tests and the shell harnesses that run scripts/install.sh or
    scripts/upgrade.sh OUTSIDE this module and the two smokes inherited the
    host PATH, so a host claude below the floor turned them into exit 6
    before they exercised anything (reproduced S357 with a FAKE 2.1.279
    first on PATH). Cured by class at the two points every such run goes
    through, each guarded here: the pytest isolation layer
    (_lib/test_isolation.py, Axis 4) puts a FAKE claude at the floor first on
    the PATH of every test, and every shell harness that names an installer
    carries ONE byte-identical block, right after its first top-level set
    line, that exports a claude FUNCTION answering with that floor. RED on
    the r14 derivation: the suite PATH led to the host CLI and no harness
    carried the block."""

    _BEGIN = "# >>> harness-claude-stub (ADR-149 Amendment 3) >>>\n"
    _END = "# <<< harness-claude-stub <<<\n"
    INSTALL_SH = REPO_ROOT / "scripts" / "install.sh"
    REFERENCE = REPO_ROOT / "scripts" / "tests" / "smoke-install.sh"
    #: Where the census walks, and what it never walks into.
    _ROOTS = ("scripts", "tests", ".claude")
    _PRUNED = frozenset({".git", "__pycache__", "node_modules", "fixtures",
                         "worktrees"})
    _PRUNED_REL = frozenset({".claude/plans"})

    def _floor(self) -> str:
        found = [ln.split("=", 1)[1].strip('"') for ln in
                 self.INSTALL_SH.read_text(encoding="utf-8").splitlines()
                 if ln.startswith("CC_FLOOR_VERSION=")]
        self.assertEqual(len(found), 1, "scripts/install.sh must carry ONE "
                         "CC_FLOOR_VERSION line")
        return found[0]

    def _stub_block(self, path: Path) -> str:
        text = path.read_text(encoding="utf-8")
        self.assertEqual(text.count(self._BEGIN), 1, path)
        self.assertEqual(text.count(self._END), 1, path)
        start = text.index(self._BEGIN)
        return text[start:text.index(self._END) + len(self._END)]

    def _harnesses(self) -> List[Path]:
        """Every shell script under a directory named tests, or under
        scripts/local/, whose text names install.sh or upgrade.sh. A
        superset on purpose: a mention is enough, nothing about HOW the
        script runs an installer is parsed."""
        found = []
        for top in self._ROOTS:
            for dirpath, dirnames, filenames in os.walk(str(REPO_ROOT / top)):
                rel = Path(dirpath).relative_to(REPO_ROOT)
                dirnames[:] = sorted(
                    d for d in dirnames
                    if d not in self._PRUNED
                    and (rel / d).as_posix() not in self._PRUNED_REL)
                if "tests" not in rel.parts and rel.parts[:2] != ("scripts", "local"):
                    continue
                for name in sorted(filenames):
                    if not name.endswith(".sh"):
                        continue
                    path = Path(dirpath) / name
                    text = path.read_text(encoding="utf-8", errors="replace")
                    if "install.sh" in text or "upgrade.sh" in text:
                        found.append(path)
        return found

    def _checkout_with_host_cli(self, version: str) -> Tuple[Path, Path]:
        """A scratch checkout whose scripts/install.sh is the real one (the
        block reads its floor there), and a directory holding a FAKE host
        claude that reports ``version``."""
        checkout = Path(self._tmp) / "checkout"
        (checkout / "scripts" / "tests").mkdir(parents=True)
        (checkout / "scripts" / "install.sh").symlink_to(self.INSTALL_SH)
        host = Path(self._tmp) / "hostbin"
        host.mkdir()
        exe = host / "claude"
        exe.write_text("#!/bin/sh\necho '" + version + " (Claude Code)'\n",
                       encoding="utf-8")
        exe.chmod(0o755)
        return checkout, host

    def _require_the_pytest_session(self) -> None:
        """The suite isolation layer is a pytest SESSION fixture: under
        ``python -m unittest`` it never runs (the CI runs pytest only).
        pytest sets PYTEST_CURRENT_TEST while a test runs, so under pytest
        this never skips and a broken Axis 4 is RED."""
        if "PYTEST_CURRENT_TEST" not in os.environ:
            self.skipTest("the suite isolation layer runs under pytest only")

    def test_the_suite_puts_a_fake_claude_at_the_floor_first_on_path(self) -> None:
        self._require_the_pytest_session()
        floor = self._floor()
        first = os.environ.get("PATH", "").split(os.pathsep)[0]
        found = shutil.which("claude")
        self.assertIsNotNone(found, "no claude on the suite PATH")
        self.assertEqual(os.path.dirname(found), first)
        self.assertEqual(os.path.basename(first), "claude-code-stub")
        self.assertTrue(os.path.basename(os.path.dirname(first))
                        .startswith("ceo-suite-isolation-"), first)
        self.assertNotIn("BASH_FUNC_claude%%", os.environ)
        ver = subprocess.run([found, "--version"], capture_output=True,
                             text=True, timeout=30)
        self.assertEqual((ver.returncode, ver.stdout),
                         (0, floor + " (Claude Code)\n"))
        other = subprocess.run([found, "-p", "hello"], capture_output=True,
                               text=True, timeout=30)
        self.assertEqual((other.returncode, other.stdout), (127, ""))

    def test_an_installer_that_inherits_the_suite_env_reads_the_stub(self) -> None:
        self._require_the_pytest_session()
        floor = self._floor()
        self.seed({"model": "claude-opus-5",
                   "availableModels": list(baselines()["availableModels"]["new"])})
        env = dict(os.environ)
        env.pop("CEO_T34_NEW_EVENT_REGISTRATIONS", None)
        proc = subprocess.run(
            ["bash", str(UPGRADE_SH), str(self.target), "--settings-migrate-only",
             "--no-replay", "--no-deprecation-warn"],
            capture_output=True, text=True, timeout=120, env=env)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("Claude Code:  " + floor + " (floor " + floor + ": OK)",
                      proc.stdout)

    def test_every_shell_harness_that_names_an_installer_carries_the_block(self) -> None:
        reference = self._stub_block(self.REFERENCE)
        harnesses = self._harnesses()
        names = [p.relative_to(REPO_ROOT).as_posix() for p in harnesses]
        for known in ("scripts/tests/smoke-install.sh",
                      "scripts/local/smoke-install-parity.sh",
                      "scripts/tests/test-ownership-table.sh"):
            self.assertIn(known, names)
        for path, name in zip(harnesses, names):
            with self.subTest(harness=name):
                text = path.read_text(encoding="utf-8")
                self.assertEqual(self._stub_block(path), reference)
                offset = None
                position = 0
                for line in text.splitlines(True):
                    position += len(line)
                    if line.startswith("set -"):
                        offset = position
                        break
                self.assertIsNotNone(offset, "no top-level set line")
                self.assertTrue(text.startswith(self._BEGIN, offset),
                                "the block must follow the first set line")

    def test_the_block_shadows_a_host_cli_below_the_floor(self) -> None:
        """The control runs the same harness without the block first: the
        FAKE host 2.1.279 first on PATH is read and upgrade.sh refuses
        (exit 6) with nothing written; with the block the run passes."""
        floor = self._floor()
        checkout, host = self._checkout_with_host_cli("2.1.279")
        env = dict(os.environ)
        env["PATH"] = str(host) + os.pathsep + env.get("PATH", "")
        self.seed({"model": "claude-opus-5",
                   "availableModels": list(baselines()["availableModels"]["new"])})
        before = self.settings_path.read_bytes()
        runs = {}
        for name, body in (("bare", ""), ("stubbed", self._stub_block(self.REFERENCE))):
            harness = checkout / "scripts" / "tests" / (name + ".sh")
            harness.write_text(
                "#!/usr/bin/env bash\nset -uo pipefail\n" + body
                + 'bash "$1" "$2" --settings-migrate-only --no-replay'
                  ' --no-deprecation-warn\n', encoding="utf-8")
            runs[name] = subprocess.run(
                ["bash", str(harness), str(UPGRADE_SH), str(self.target)],
                capture_output=True, text=True, timeout=120, env=env)
            if name == "bare":
                self.assertEqual(self.settings_path.read_bytes(), before)
        bare, stubbed = runs["bare"], runs["stubbed"]
        self.assertEqual(bare.returncode, 6, bare.stdout + bare.stderr)
        self.assertIn("ERROR: Claude Code 2.1.279 is below " + floor, bare.stderr)
        self.assertEqual(stubbed.returncode, 0, stubbed.stdout + stubbed.stderr)
        self.assertIn("Claude Code:  " + floor + " (floor " + floor + ": OK)",
                      stubbed.stdout)

    def test_the_block_answers_under_any_path_a_child_is_given(self) -> None:
        floor = self._floor()
        checkout, host = self._checkout_with_host_cli("2.1.279")
        child = Path(self._tmp) / "child.sh"
        child.write_text('claude --version\nclaude -p hello\necho "rc=$?"\n',
                         encoding="utf-8")
        harness = checkout / "scripts" / "tests" / "path.sh"
        harness.write_text(
            "#!/usr/bin/env bash\nset -uo pipefail\n"
            + self._stub_block(self.REFERENCE)
            + 'env PATH="$1" "$BASH" "$2"\n', encoding="utf-8")
        proc = subprocess.run(["bash", str(harness), str(host), str(child)],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.stdout, floor + " (Claude Code)\nrc=127\n",
                         proc.stderr)
        self.assertIn("the harness stub answers only --version", proc.stderr)

    def test_the_block_refuses_a_checkout_without_one_floor_line(self) -> None:
        block = self._stub_block(self.REFERENCE)
        for install_text in ("#!/usr/bin/env bash\n",
                             'CC_FLOOR_VERSION="2.1.280"\nCC_FLOOR_VERSION="2.1.281"\n'):
            with self.subTest(install=install_text):
                root = Path(tempfile.mkdtemp(prefix="t54-nofloor-", dir=self._tmp))
                (root / "scripts" / "tests").mkdir(parents=True)
                (root / "scripts" / "install.sh").write_text(install_text,
                                                             encoding="utf-8")
                harness = root / "scripts" / "tests" / "h.sh"
                harness.write_text("#!/usr/bin/env bash\nset -uo pipefail\n"
                                   + block + "echo reached\n", encoding="utf-8")
                proc = subprocess.run(["bash", str(harness)], capture_output=True,
                                      text=True, timeout=60)
                self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                self.assertNotIn("reached", proc.stdout)
                self.assertIn("carries no single CC_FLOOR_VERSION line", proc.stderr)


'''

#: The guard of the rail-round-3 class (appended after
#: TestNoHarnessReadsTheHostCli). A RAW string: the escapes below are test
#: SOURCE.
_UPGRADE_TESTS_RERUN = r'''class TestEveryFailureExitKeepsTheOperatorFlags(_MigrationHarness):
    """ADR-149 Amendment 3, fix round r16 (rail round 3 of the wave, P2; Owner
    OQ-10, 2026-09-24, verbatim «Corrigir + rodada 4 final c/ anexo
    (Recomendado)»): the failure exit of the migration HELPER (settings.json
    unparseable, or the atomic write failed) printed its re-run WITHOUT the
    operator flags, so following it after repairing the JSON wrote high where
    --adopt-setting effortLevel asked for xhigh, and a present value is never
    overwritten afterwards. Cured by class: ONE builder (_t54_rerun_cmd), and
    every exit of the migration that leaves settings.json unmigrated prints
    what it builds. Each exit is forced here - by an unparseable settings.json
    or by a planted FAULT in a disposable copy of upgrade.sh (never a product
    seam) - and the printed command is parsed back as the shell would: it must
    carry exactly the operator's flags. RED on the r15 derivation of this
    wave: the helper exits printed no flag and the missing-python3 exit
    printed no command."""

    _OPERATOR = ["--adopt-setting", "effortLevel", "--adopt-setting",
                 "plantedKey", "--allow-old-claude-code"]
    #: exit -> (exact anchor in upgrade.sh, planted replacement). An anchor
    #: that is missing or repeated fails the test: a dead plant is never green.
    _FAULTS = {
        "backup": ('cp "$settings" '
                   '"$BAK_DIR/.claude/settings.json.pre-t54-migration"',
                   "false"),
        "atomic-write": ("    os.replace(tmp, path)\n",
                         '    raise OSError("planted atomic-write fault")\n'),
        "helper-crash": ("\nmode = sys.argv[1]\n",
                         '\nraise RuntimeError("planted helper fault")\n'),
        "no-python3": ("  if ! command -v python3 >/dev/null 2>&1; then\n"
                       '    echo "    NOTE: settings baseline migration skipped',
                       "  if true; then\n"
                       '    echo "    NOTE: settings baseline migration skipped'),
    }

    def _faulty(self, label: str, root: Optional[Path] = None) -> Path:
        anchor, planted = self._FAULTS[label]
        text = UPGRADE_SH.read_text(encoding="utf-8")
        self.assertEqual(text.count(anchor), 1, "the %s fault anchor moved: fix "
                         "the control, never skip it" % label)
        if root is None:
            root = Path(tempfile.mkdtemp(prefix="t54-fw-", dir=self._tmp))
        dst = root / "scripts" / "upgrade.sh"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text.replace(anchor, planted), encoding="utf-8")
        return dst

    def _seed_old(self) -> None:
        self.seed({"availableModels":
                   list(baselines()["availableModels"]["old"])})

    def _run(self, upgrade: Path, extra: List[str],
             extra_env: Optional[Dict[str, str]] = None
             ) -> "subprocess.CompletedProcess[str]":
        return subprocess.run(
            ["bash", str(upgrade), str(self.target), "--settings-migrate-only",
             "--no-replay", "--no-deprecation-warn"] + self._OPERATOR + extra,
            capture_output=True, text=True, timeout=120,
            env=_clean_env(extra_env))

    def _assert_rerun(self, proc: "subprocess.CompletedProcess[str]",
                      tail: List[str]) -> None:
        import shlex  # only this class parses a printed command back
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        hits = [ln for ln in proc.stderr.splitlines()
                if "--settings-migrate-only" in ln]
        self.assertEqual(len(hits), 1, "want ONE re-run line:\n" + proc.stderr)
        self.assertIn("scripts/upgrade.sh", hits[0])
        argv = shlex.split(hits[0][hits[0].index("scripts/upgrade.sh"):])
        self.assertEqual(argv[0], "scripts/upgrade.sh")
        self.assertEqual(os.path.realpath(argv[1]),
                         os.path.realpath(str(self.target)))
        self.assertEqual(argv[2:],
                         ["--settings-migrate-only"] + self._OPERATOR + tail)

    def test_every_failure_exit_prints_the_operator_flags(self) -> None:
        # (exit, planted fault or None, unparseable settings?, extra flags,
        #  names the pre-migration backup?)
        for label, fault, broken, extra, backup_named in (
            ("backup", "backup", False, [], False),
            ("unparseable", None, True, [], True),
            ("unparseable-dry-run", None, True, ["--dry-run"], False),
            ("atomic-write", "atomic-write", False, [], True),
            ("helper-crash", "helper-crash", False, [], True),
            ("helper-crash-dry-run", "helper-crash", False, ["--dry-run"], False),
            ("no-python3", "no-python3", False, [], False),
        ):
            with self.subTest(exit=label):
                self.setUp()
                if broken:
                    self.settings_path.write_text('{"model": ', encoding="utf-8")
                else:
                    self._seed_old()
                before = self.settings_path.read_bytes()
                upgrade = self._faulty(fault) if fault else UPGRADE_SH
                proc = self._run(upgrade, list(extra))
                self._assert_rerun(proc, list(extra))
                self.assertEqual(self.settings_path.read_bytes(), before)
                self.assertRegex(proc.stderr,
                                 r"settings baseline migration (SKIPPED|skipped)")
                self.assertEqual("Pre-migration backup:" in proc.stderr,
                                 backup_named, proc.stderr)

    def test_the_pin_rides_along_quoted_for_the_shell(self) -> None:
        """--pin picks the source checkout whose settings template the
        migration reads: the re-run carries it, quoted so that the shell
        hands the same ref back (a ref name may hold a shell metacharacter)."""
        root = Path(tempfile.mkdtemp(prefix="t54-pinfw-", dir=self._tmp))
        upgrade = self._faulty("helper-crash", root)
        git_env = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
        git = ["git", "-C", str(root), "-c", "user.name=selftest",
               "-c", "user.email=selftest@example.invalid",
               "-c", "commit.gpgsign=false"]
        ref = "pin;v1"
        for argv in (["init", "-q"], ["add", "scripts/upgrade.sh"],
                     ["commit", "-q", "-m", "fw"], ["branch", ref]):
            done = subprocess.run(git + argv, capture_output=True, text=True,
                                  timeout=60, env=_clean_env(git_env))
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self._seed_old()
        before = self.settings_path.read_bytes()
        proc = self._run(upgrade, ["--pin", ref], extra_env=git_env)
        self._assert_rerun(proc, ["--pin", ref])
        self.assertIn("--pin pin\\;v1", proc.stderr)
        self.assertEqual(self.settings_path.read_bytes(), before)

    def test_the_target_rides_along_quoted_for_the_shell(self) -> None:
        """The target is a value the operator supplied too: a space, a dollar
        sign or a quote in its path must reach the shell as the same path."""
        self.target = Path(self._tmp) / "odd dir $HOME 'q'"
        (self.target / ".claude").mkdir(parents=True)
        self.settings_path.write_text('{"model": ', encoding="utf-8")
        before = self.settings_path.read_bytes()
        proc = self._run(UPGRADE_SH, [])
        self._assert_rerun(proc, [])
        self.assertEqual(self.settings_path.read_bytes(), before)

    def test_no_exit_builds_its_own_command(self) -> None:
        """The migration body names flags in its warnings (re-run WITH
        --adopt-setting <key>), but a runnable command - the script path and
        the migrate-only switch - exists only in the builder."""
        text = UPGRADE_SH.read_text(encoding="utf-8")
        self.assertEqual(text.count("\n_t54_rerun_cmd() {\n"), 1)
        start = text.index("\n_migrate_settings_baseline() {\n")
        body = text[start:text.index("\n}\n\n# ====", start)]
        for shape in ("scripts/upgrade.sh", "--settings-migrate-only"):
            self.assertNotIn(shape, body, "an exit builds its own re-run")
        self.assertEqual(body.count("$(_t54_rerun_cmd)"), 3,
                         "the backup, missing-python3 and helper exits")


'''

#: Axis 4 of the pytest isolation layer (module docstring, constants and
#: helpers, the session activation).
_TI_AXIS4_DOC = r'''
## Axis 4 — the host Claude Code CLI (ADR-149 Amendment 3, S357)

``scripts/install.sh`` and ``scripts/upgrade.sh`` read ``claude --version``
from the claude found on PATH against ``CC_FLOOR_VERSION`` and REFUSE below it
(exit 6) before any write. A test that spawns either one inherited the suite's
PATH, so it read the OPERATOR's CLI: on a host whose claude is below the floor
every such test failed with exit 6 before it exercised anything (reproduced
S357 with a fake 2.1.279 first on PATH), and the host version decided what
the scripts printed.

Cure (``_activate_redirect``, session scope like Axis 1): a FAKE ``claude``
that reports the floor of ``scripts/install.sh`` goes FIRST on PATH, inside the
session tree (removed with it; PATH comes back with the restore snapshot). It
answers only ``--version``; any other call exits 127, so no test reaches a real
CLI through it. A test that needs another CLI puts its own first on the PATH it
hands the spawn (``TestClaudeCodeFloor`` does); a test that builds a PATH of its
own decides which claude it holds. The shell harnesses that name an installer
carry the ``harness-claude-stub`` block instead, which exports a ``claude``
FUNCTION with the same answer; bash runs a function before any PATH entry, so
one inherited here would shadow every PATH fake a test puts first, and the
session drops it. No single floor line in ``scripts/install.sh`` means no stub
(nothing reads the CLI then). Guard: ``TestNoHarnessReadsTheHostCli`` in
``.claude/scripts/tests/test_upgrade_settings_migration.py``.
'''

_TI_AXIS4_CODE = r'''# --- Axis 4 — the host Claude Code CLI (module docstring) ------------------------
#: The directory of the FAKE claude inside the session tree.
CC_STUB_DIRNAME = "claude-code-stub"
#: How bash hands an exported function named ``claude`` to its children: the
#: upstream form, and the one some vendor fixes of 2014 used.
CC_FUNCTION_CARRIERS = ("BASH_FUNC_claude%%", "BASH_FUNC_claude()")
#: What the session snapshots and restores for Axis 4.
CC_CLI_CARRIERS = ("PATH",) + CC_FUNCTION_CARRIERS
_INSTALL_SH = Path(__file__).resolve().parents[3] / "scripts" / "install.sh"
_CC_FLOOR_RE = re.compile(r'^CC_FLOOR_VERSION="([0-9]+\.[0-9]+\.[0-9]+)"$', re.M)


def claude_code_floor(install_sh: Optional[Path] = None) -> Optional[str]:
    """The Claude Code floor of ``scripts/install.sh`` (its ONE
    ``CC_FLOOR_VERSION="x.y.z"`` line), or None when the file is unreadable or
    holds no such line, or more than one."""
    try:
        text = (install_sh or _INSTALL_SH).read_text(encoding="utf-8")
    except OSError:
        return None
    found = _CC_FLOOR_RE.findall(text)
    return found[0] if len(found) == 1 else None


def _install_claude_code_stub(root: Path) -> Optional[str]:
    """Write the FAKE claude under ``root`` and return its directory; None
    when there is no floor to report."""
    floor = claude_code_floor()
    if floor is None:
        return None
    stub_dir = root / CC_STUB_DIRNAME
    stub_dir.mkdir(parents=True, exist_ok=True)
    exe = stub_dir / "claude"
    exe.write_text(
        "#!/bin/sh\n"
        "# FAKE Claude Code CLI of the pytest session (_lib/test_isolation.py,\n"
        "# Axis 4): it answers only --version, with the floor of scripts/install.sh.\n"
        'if [ "$#" -eq 1 ] && [ "$1" = "--version" ]; then\n'
        '  echo "%s (Claude Code)"\n'
        "  exit 0\n"
        "fi\n"
        'echo "claude: the test-suite stub answers only --version" >&2\n'
        "exit 127\n" % floor,
        encoding="utf-8",
    )
    exe.chmod(0o755)
    return str(stub_dir)


'''

_OLD_WS_6 = (
    '"claude-opus-4-8","claude-fable-5","claude-sonnet-4-6",'
    '"claude-haiku-4-5","claude-opus-5","claude-sonnet-5"'
)
_WS_7 = _OLD_WS_6 + ',"claude-fable-5-1"'
_WS_8 = _WS_7 + ',"claude-opus-5-5"'

# --------------------------------------------------------------------------
# (path, EXACT anchor, replacement, expected occurrences) — application order
# --------------------------------------------------------------------------
EDITS: List[Tuple[str, str, str, int]] = [
    # =============================================================== ADR-149
    (
        ADR_REL,
        '    "claude-opus-5",     # ADR-181 (PLAN-163 T1.3, OQ1=b) — Claude 5 Opus joins the floor\n'
        "})\n",
        '    "claude-opus-5",     # ADR-181 (PLAN-163 T1.3, OQ1=b) — Claude 5 Opus joins the floor\n'
        '    "claude-opus-5-5",   # ADR-149 Amendment 3 (S357, PLAN-193) — Opus 5.5 joins the floor\n'
        "})\n",
        1,
    ),
    (
        ADR_REL,
        '    "claude-fable-5-1",   # Mythos-class flagship 5.1; dateless id per the models overview\n'
        ")\n",
        '    "claude-fable-5-1",   # Mythos-class flagship 5.1; dateless id per the models overview\n'
        "    # -- Opus 5.5 -- ADR-149 Amendment 3, S357 2026-09-22; APPENDED AT END.\n"
        "    #    Working set AND VETO floor; the session-default pin. The\n"
        "    #    fallback stays claude-opus-5, which stays available. --\n"
        '    "claude-opus-5-5",    # Opus 5.5; dateless id per the models overview\n'
        ")\n",
        1,
    ),
    (
        ADR_REL,
        'The A1.1 prose sentence *"the primary session model is `claude-fable-5`"*\n'
        "is historical (it predates the ADR-181 pin); the pin above is the truth.\n",
        'The A1.1 prose sentence *"the primary session model is `claude-fable-5`"*\n'
        "is historical (it predates the ADR-181 pin); the pin above is the truth.\n"
        + _ADR_AMENDMENT_3,
        1,
    ),
    # ============================================== .claude/settings.json
    (
        DOGFOOD_REL,
        "Pinned to claude-opus-5 (OQ1=b primary/fallback). Rationale:",
        "Pinned to claude-opus-5-5 since ADR-149 Amendment 3 (S357; Claude Opus "
        "5.5 needs Claude Code >= 2.1.280); from ADR-181 until then the pin was "
        "claude-opus-5 (OQ1=b primary/fallback), which stays the fallbackModel. "
        "Rationale:",
        1,
    ),
    (
        DOGFOOD_REL,
        "The pinned value MUST remain a member of availableModels below or "
        "enforceAvailableModels rejects it (claude-opus-5 is present).",
        "The pinned value MUST remain an EXACT member of availableModels "
        "below (claude-opus-5-5 is present): SessionDefaultPinTest in "
        ".claude/hooks/tests/test_template_dogfood_parity.py compares exact "
        "ids, while Claude Code itself admits an id that extends an allowed "
        "entry by a - segment and replaces a pin the allowlist does not admit "
        "with the default model at startup (with a warning).",
        1,
    ),
    (
        DOGFOOD_REL,
        "Mirror this key in templates/settings/settings.base.json or "
        "test_session_default_pin reddens.",
        "Mirror this key in templates/settings/settings.base.json or "
        "SessionDefaultPinTest reddens.",
        1,
    ),
    (
        DOGFOOD_REL,
        '  "model": "claude-opus-5",\n'
        '  "availableModels": [\n',
        '  "model": "claude-opus-5-5",\n'
        '  "availableModels": [\n',
        1,
    ),
    (
        DOGFOOD_REL,
        '    "claude-fable-5-1"\n'
        "  ],\n"
        '  "_enforce_available_models_comment"',
        '    "claude-fable-5-1",\n'
        '    "claude-opus-5-5"\n'
        "  ],\n"
        '  "_enforce_available_models_comment"',
        1,
    ),
    (
        DOGFOOD_REL,
        "Closes Default-model drift when the harness tier default moves ahead of our pinned set.",
        "ADR-149 Amendment 3 (S357, measured on Claude Code 2.1.280): the harness "
        "matches availableModels entries by segment PREFIX (an entry admits every "
        "id that extends it by a - segment; claude-opus-5 already admitted "
        "claude-opus-5-5), so this key does NOT redirect a tier default that "
        "extends an allowed entry; the explicit top-level model pin is what "
        "fixes the session default.",
        1,
    ),
    (
        DOGFOOD_REL,
        _ENFORCE_CAVEAT_OLD,
        _ENFORCE_CAVEAT_NEW,
        1,
    ),
    (
        DOGFOOD_REL,
        '  "fallbackModel": [\n'
        '    "claude-opus-5"\n'
        "  ],\n"
        '  "_deny_baseline_comment"',
        '  "fallbackModel": [\n'
        '    "claude-opus-5"\n'
        "  ],\n"
        '  "_effort_level_comment": "' + _EFFORT_COMMENT_DOGFOOD + '",\n'
        '  "effortLevel": "xhigh",\n'
        '  "_deny_baseline_comment"',
        1,
    ),
    # ============================================== settings.base.json
    (
        BASE_REL,
        "Pinned to claude-opus-5 so that adding claude-sonnet-5 to availableModels "
        "cannot silently flip the session default to the 2.1.220 sonnet-5 "
        "tier-default (enforceAvailableModels stops redirecting once sonnet-5 is "
        "allowed). ADOPTER NOTE: a fresh install therefore inherits claude-opus-5 "
        "as the session default (Opus pricing $5/$25 per MTok).",
        "Pinned to claude-opus-5-5 since ADR-149 Amendment 3 (S357; Claude Opus "
        "5.5 needs Claude Code >= 2.1.280). ADR-181 first pinned claude-opus-5 so "
        "that adding claude-sonnet-5 to availableModels could not silently flip "
        "the session default to the 2.1.220 sonnet-5 tier-default "
        "(enforceAvailableModels stops redirecting once sonnet-5 is allowed); "
        "claude-opus-5 stays the fallbackModel. ADOPTER NOTE: a fresh install "
        "therefore inherits claude-opus-5-5 as the session default (Opus 5.5 "
        "pricing $4/$20 per MTok).",
        1,
    ),
    (
        BASE_REL,
        "the pinned value MUST stay a member of availableModels below or "
        "enforceAvailableModels rejects it.",
        "the pinned value must be one that availableModels below admits: "
        "Claude Code replaces a pin the allowlist does not admit with the "
        "default model at startup (with a warning), and admits "
        "an id that extends an allowed entry by a - segment. scripts/upgrade.sh "
        "is stricter: it writes a new framework pin into an existing install "
        "only when that pin is an EXACT entry of its availableModels, and "
        "warns otherwise.",
        1,
    ),
    (
        BASE_REL,
        "Keep this key mirrored with .claude/settings.json in the framework "
        "repo (test_session_default_pin).",
        "Keep this key mirrored with .claude/settings.json in the framework "
        "repo (SessionDefaultPinTest).",
        1,
    ),
    (
        BASE_REL,
        '  "model": "claude-opus-5",\n'
        '  "availableModels": [\n',
        '  "model": "claude-opus-5-5",\n'
        '  "availableModels": [\n',
        1,
    ),
    (
        BASE_REL,
        '    "claude-fable-5-1"\n'
        "  ],\n"
        '  "fallbackModel"',
        '    "claude-fable-5-1",\n'
        '    "claude-opus-5-5"\n'
        "  ],\n"
        '  "fallbackModel"',
        1,
    ),
    (
        BASE_REL,
        '  "fallbackModel": [\n'
        '    "claude-opus-5"\n'
        "  ],\n"
        '  "_posture_keys_comment"',
        '  "fallbackModel": [\n'
        '    "claude-opus-5"\n'
        "  ],\n"
        '  "_effort_level_comment": "' + _EFFORT_COMMENT + '",\n'
        '  "effortLevel": "xhigh",\n'
        '  "_posture_keys_comment"',
        1,
    ),
    # ================================ settings.user.json (GENERATED — the
    # bytes gen-settings-user-template.py renders from the edited base; the
    # derivator's caller proves it with `--check`).
    (
        USER_REL,
        '  "model": "claude-opus-5"\n'
        "}\n",
        '  "model": "claude-opus-5-5",\n'
        '  "_effort_level_comment": "' + _EFFORT_COMMENT + '",\n'
        '  "effortLevel": "xhigh"\n'
        "}\n",
        1,
    ),
    # ============================================================ upgrade.sh
    (
        UPGRADE_REL,
        '# The top-level scalar "model" leaf (the CC 2.1.220 session-default pin,\n'
        "# ADR-181 T1.1) has NO old-baseline value — old installs carry NO top-level\n"
        '# "model" key at all ("old": null documents that ABSENCE). Absence therefore\n'
        "# IS the old baseline: it is migrated to the new pin (claude-opus-5), closing\n"
        "# the T1.1 silent-flip (adding claude-sonnet-5 to availableModels must not\n"
        "# re-flip the session default) — BUT ONLY when claude-opus-5 is actually in\n"
        "# the resulting effective availableModels. C6 (codex R4): if an adopter has\n"
        "# CUSTOMIZED availableModels to a set that EXCLUDES claude-opus-5, setting the\n"
        "# pin would place it outside the allowlist and enforceAvailableModels would\n"
        "# reject it, so in that case the pin is NOT set and a named warning is emitted\n"
        "# (session default left to the adopter/harness). In the normal migrated case\n"
        "# claude-opus-5 IS present, so the pin is set and enforceAvailableModels\n"
        "# accepts it. Any PRESENT model value != the new pin is adopter-custom and\n"
        "# PRESERVED with a named warning (never re-flipped).\n",
        '# The top-level SCALAR leaves ("model", the CC 2.1.220 session-default pin\n'
        '# of ADR-181 T1.1, and "effortLevel", ADR-149 Amendment 3) walk ONE generic\n'
        '# branch. "old": null documents that old installs carry NO such key:\n'
        "# absence (or an explicit null) IS the old baseline and is SET to \"new\".\n"
        '# "superseded" lists every previously SHIPPED value (frozen literals, exact\n'
        "# string equality) and migrates like the old baseline: every release from\n"
        "# v1.2.0-rc.1 to the last one before ADR-149 Amendment 3 (S357) shipped the\n"
        "# pin claude-opus-5, which that amendment moved to claude-opus-5-5; without\n"
        "# the list every such adopter would be read as ADOPTER-CUSTOMIZED and keep\n"
        "# the old pin behind a warning.\n"
        '# "requires_member_of" names an ARRAY leaf whose EFFECTIVE value (resolved\n'
        "# earlier in the same pass) must contain the new value EXACTLY before a SET\n"
        "# or MIGRATE happens. C6 (codex R4): an adopter who CUSTOMIZED\n"
        "# availableModels could otherwise get a pin the allowlist does not admit,\n"
        "# which Claude Code replaces at startup with the default model (with a\n"
        "# warning). The check is deliberately STRICTER\n"
        "# than Claude Code, which admits an id that extends an allowed entry by a\n"
        "# - segment: a new value the array does not list exactly leaves the leaf\n"
        "# untouched with a named warning. Any other PRESENT value is adopter-custom\n"
        "# and PRESERVED with a named warning (never re-flipped).\n"
        '# "opt_in": true (ADR-149 Amendment 3, Owner OQ-7) marks a leaf that an\n'
        "# EXISTING install receives only when the operator passes\n"
        "# --adopt-setting <key>: a new install gets it from the template; without\n"
        "# the flag the leaf is never written, and a named warning carries its\n"
        '# "cost_note" and the flag instead. An adopter value is never overwritten,\n'
        "# flag or not. effortLevel is the first opt-in leaf.\n"
        '# "on_migrate_of" (ADR-149 Amendment 3, Owner OQ-8) on an opt-in leaf:\n'
        "# {<scalar leaf>: {<value it migrates off>: <value for this leaf>}}. When\n"
        "# that leaf, walked EARLIER in the same pass, MIGRATEs off the named value\n"
        "# while this leaf is absent (or null) and not opted in, this leaf takes\n"
        '# the mapped value: a MIGRATE line, its REVERT line and the leaf\n'
        '# "on_migrate_note". effortLevel keeps high, the claude-opus-5 default,\n'
        "# when the pin migrates off claude-opus-5 (claude-opus-5-5 defaults to\n"
        "# medium). A rule naming a leaf walked later is a named WARNING.\n"
        '# "notice" (ADR-149 Amendment 3) is a line printed whenever the leaf is\n'
        "# written (SET or MIGRATE): the model leaf carries the Claude Code floor\n"
        "# of its new pin. Every MIGRATE line is followed by a REVERT line.\n",
        1,
    ),
    (
        UPGRADE_REL,
        "# byte-exact (values AND order): a genuinely customized array still lands\n"
        "# in the PRESERVED branch.\n",
        "# byte-exact (values AND order): a genuinely customized array still lands\n"
        "# in the PRESERVED branch.\n"
        "# ADR-149 Amendment 3 (S357): every release from v1.4.0-rc.1 to the last\n"
        '# one before that amendment shipped the 7-id availableModels (the "new"\n'
        '# of Amendment 2); it joins "superseded", and "new" appends\n'
        "# claude-opus-5-5 at the END.\n",
        1,
    ),
    (
        UPGRADE_REL,
        '    "superseded": [[' + _OLD_WS_6 + "]],\n"
        '    "new": [' + _WS_7 + "]\n",
        '    "superseded": [[' + _OLD_WS_6 + "],[" + _WS_7 + "]],\n"
        '    "new": [' + _WS_8 + "]\n",
        1,
    ),
    (
        UPGRADE_REL,
        '  "model": {\n'
        '    "old": null,\n'
        '    "new": "claude-opus-5"\n'
        "  },\n",
        '  "model": {\n'
        '    "old": null,\n'
        '    "superseded": ["claude-opus-5"],\n'
        '    "new": "claude-opus-5-5",\n'
        '    "requires_member_of": "availableModels",\n'
        '    "notice": "' + _MODEL_NOTICE + '"\n'
        "  },\n"
        '  "effortLevel": {\n'
        '    "old": null,\n'
        '    "new": "xhigh",\n'
        '    "opt_in": true,\n'
        '    "cost_note": "' + _EFFORT_COST_NOTE + '",\n'
        '    "on_migrate_of": {"model": {"claude-opus-5": "high"}},\n'
        '    "on_migrate_note": "' + _EFFORT_KEEP_NOTE + '"\n'
        "  },\n",
        1,
    ),
    (
        UPGRADE_REL,
        "SETTINGS_MIGRATE_ONLY=0  # PLAN-163 T5.4: run ONLY the settings migration (test/ops seam)\n",
        "SETTINGS_MIGRATE_ONLY=0  # PLAN-163 T5.4: run ONLY the settings migration (test/ops seam)\n"
        'ADOPT_SETTINGS=""        # ADR-149 A3 (OQ-7): comma list of opted-in T5.4 leaves (--adopt-setting)\n'
        "ALLOW_OLD_CLAUDE_CODE=0  # ADR-149 A3 (OQ-9): --allow-old-claude-code continues below the floor\n",
        1,
    ),
    (
        UPGRADE_REL,
        "    --print-settings-baselines)\n"
        "      # PLAN-163 T5.4: introspection for oracles — the normative baseline\n",
        "    --allow-old-claude-code)\n"
        "      # ADR-149 Amendment 3 (S357, Owner OQ-9): continue although the\n"
        "      # claude CLI on PATH is older than the Claude Code floor of this\n"
        "      # release (a named WARNING instead of the refusal).\n"
        "      ALLOW_OLD_CLAUDE_CODE=1\n"
        "      shift\n"
        "      ;;\n"
        "    --adopt-setting)\n"
        "      # ADR-149 Amendment 3 (S357, Owner OQ-7): opt in to ONE top-level\n"
        '      # T5.4 leaf the table marks "opt_in" (effortLevel). Without it an\n'
        "      # EXISTING install never receives an opt-in leaf. Repeatable; the\n"
        "      # migration names (and ignores) a key the table does not mark.\n"
        '      _adopt_key="${2:-}"\n'
        '      if [[ ! "$_adopt_key" =~ ^[A-Za-z][A-Za-z0-9]*$ ]]; then\n'
        "        echo \"ERROR: --adopt-setting needs a top-level settings key such as effortLevel (got '$_adopt_key')\" >&2\n"
        "        exit 2\n"
        "      fi\n"
        '      ADOPT_SETTINGS="${ADOPT_SETTINGS:+$ADOPT_SETTINGS,}$_adopt_key"\n'
        "      shift 2\n"
        "      ;;\n"
        "    --print-settings-baselines)\n"
        "      # PLAN-163 T5.4: introspection for oracles — the normative baseline\n",
        1,
    ),
    (
        UPGRADE_REL,
        "  --print-settings-baselines\n"
        "                        Print the normative T5.4 baseline table (JSON) and\n"
        "                        exit 0. Oracles derive their expectations from this\n"
        "                        output instead of hardcoding the literals.\n",
        "  --print-settings-baselines\n"
        "                        Print the normative T5.4 baseline table (JSON) and\n"
        "                        exit 0. Oracles derive their expectations from this\n"
        "                        output instead of hardcoding the literals.\n"
        "  --adopt-setting <key>\n"
        "                        ADR-149 Amendment 3 (opt-in; repeatable): let the\n"
        "                        T5.4 migration write a leaf the table marks opt_in\n"
        "                        into THIS existing install. Today: effortLevel\n"
        "                        (new installs ship xhigh; it applies to every model\n"
        "                        of the session and typically costs more tokens).\n"
        "                        Without the flag the leaf is left absent and a\n"
        "                        named warning shows its cost note; a value you set\n"
        "                        is never overwritten, flag or not. When the pin\n"
        "                        migrates off claude-opus-5 in a file with no\n"
        "                        effortLevel, the migration writes high instead\n"
        "                        (the Opus 5 default) unless you pass this flag.\n"
        "  --allow-old-claude-code\n"
        "                        ADR-149 Amendment 3: continue although the claude\n"
        "                        CLI on PATH is older than the Claude Code floor of\n"
        "                        this release (2.1.280, SUPPORT.md). Without it such\n"
        "                        an upgrade is REFUSED (exit 6) before anything is\n"
        "                        written; with no claude on PATH the upgrade warns\n"
        "                        and goes on.\n",
        1,
    ),
    (
        UPGRADE_REL,
        "# (test seam + operator escape hatch). The gate NEVER affects the three\n"
        "# model/permission leaf keys — those migrate regardless.\n",
        "# (test seam + operator escape hatch). The gate NEVER affects the leaf\n"
        "# keys of the table above — those migrate regardless.\n",
        1,
    ),
    (
        UPGRADE_REL,
        "  updated in place by the default-on baseline migration (the model/permission\n"
        "  leaf keys: model, availableModels, fallbackModel, permissions.defaultMode)\n",
        "  updated in place by the default-on baseline migration (the leaf keys of\n"
        "  its table: model, availableModels, fallbackModel,\n"
        "  permissions.defaultMode; the opt-in effortLevel as xhigh only with\n"
        "  --adopt-setting effortLevel, or as high when the pin migrates off\n"
        "  claude-opus-5 in a file that sets no level)\n",
        1,
    ),
    # Codex r3 (lane A): the REVERT lines name the pre-migration backup, so
    # the backup becomes a PRECONDITION of the write — a failed copy used to
    # be swallowed (|| true) and the migration went on.
    (
        UPGRADE_REL,
        '    cp "$settings" "$BAK_DIR/.claude/settings.json.pre-t54-migration" 2>/dev/null || true\n'
        '    echo "    BACKED UP: .claude/settings.json -> $BAK_DIR/.claude/settings.json.pre-t54-migration"\n',
        "    # ADR-149 Amendment 3 (S357): every array and hook MIGRATE line prints\n"
        "    # a REVERT line that names this backup, so the backup is a PRECONDITION\n"
        "    # of the write: when it cannot be written the migration is SKIPPED\n"
        "    # (named) and settings.json stays as it was — never migrated without\n"
        "    # the way back that the REVERT line promises.\n"
        '    if ! cp "$settings" "$BAK_DIR/.claude/settings.json.pre-t54-migration" 2>/dev/null; then\n'
        '      echo "    NOTE: settings baseline migration SKIPPED — the pre-migration backup could" >&2\n'
        '      echo "          not be written under $BAK_DIR/.claude/ (settings.json is UNCHANGED)." >&2\n'
        '      echo "          ACTION: make that directory writable (or free space), then re-run the" >&2\n'
        '      echo "          migration alone:  $(_t54_rerun_cmd)" >&2\n'
        "      return 0\n"
        "    fi\n"
        '    echo "    BACKED UP: .claude/settings.json -> $BAK_DIR/.claude/settings.json.pre-t54-migration"\n',
        1,
    ),
    # Rail round 3 of the wave (P2; Owner OQ-10, 2026-09-24, verbatim
    # «Corrigir + rodada 4 final c/ anexo (Recomendado)»): the failure exit
    # of the migration HELPER printed its re-run WITHOUT the operator flags
    # (only the backup exit carried them). Cured by CLASS: ONE builder of the
    # re-run command, and every exit of the migration that leaves
    # settings.json unmigrated prints what it builds — the backup exit
    # above, the missing-python3 exit and the helper exit below.
    (
        UPGRADE_REL,
        "_migrate_settings_baseline() {\n"
        '  [[ "$SETTINGS_MIGRATE" -eq 1 ]] || return 0\n',
        "# ADR-149 Amendment 3 (S357; rail round 3 of the wave, P2): the ONE\n"
        "# builder of the \"re-run the migration alone\" command that every exit of\n"
        "# the migration below which leaves settings.json unmigrated prints. It\n"
        "# carries every operator flag that decides what this migration reads or\n"
        "# writes, or whether it runs: --adopt-setting (the opt-in leaves it may\n"
        "# write), --allow-old-claude-code (whether it runs on a Claude Code below\n"
        "# the floor), --pin (the source checkout whose settings template it\n"
        "# reads) and --dry-run (whether it writes at all). Every value the\n"
        "# operator supplied (the target, the --pin ref) is quoted for the shell\n"
        "# with printf %q. No exit builds the command by hand: a flag the\n"
        "# migration starts to honour is added HERE.\n"
        "_t54_rerun_cmd() {\n"
        "  local _rr_cmd _rr_key\n"
        "  _rr_cmd=\"scripts/upgrade.sh $(printf '%q' \"$TARGET\") --settings-migrate-only\"\n"
        "  for _rr_key in ${ADOPT_SETTINGS//,/ }; do\n"
        '    _rr_cmd="$_rr_cmd --adopt-setting $_rr_key"\n'
        "  done\n"
        '  if [[ "$ALLOW_OLD_CLAUDE_CODE" -eq 1 ]]; then\n'
        '    _rr_cmd="$_rr_cmd --allow-old-claude-code"\n'
        "  fi\n"
        '  if [[ -n "$PIN_REF" ]]; then\n'
        "    _rr_cmd=\"$_rr_cmd --pin $(printf '%q' \"$PIN_REF\")\"\n"
        "  fi\n"
        '  if [[ "$DRY_RUN" -eq 1 ]]; then\n'
        '    _rr_cmd="$_rr_cmd --dry-run"\n'
        "  fi\n"
        "  printf '%s\\n' \"$_rr_cmd\"\n"
        "}\n"
        "\n"
        "_migrate_settings_baseline() {\n"
        '  [[ "$SETTINGS_MIGRATE" -eq 1 ]] || return 0\n',
        1,
    ),
    (
        UPGRADE_REL,
        '    echo "    NOTE: settings baseline migration skipped (python3 not found) — advisory only" >&2\n'
        "    return 0\n",
        '    echo "    NOTE: settings baseline migration skipped (python3 not found) — advisory only" >&2\n'
        '    echo "          ACTION: install python3, then re-run the migration alone:" >&2\n'
        '    echo "              $(_t54_rerun_cmd)" >&2\n'
        "    return 0\n",
        1,
    ),
    (
        UPGRADE_REL,
        '    echo "          applied — ACTION: fix/validate the JSON, then re-run the migration alone:" >&2\n'
        '    echo "              scripts/upgrade.sh \\"$TARGET\\" --settings-migrate-only" >&2\n'
        '    echo "          Pre-migration backup: $BAK_DIR/.claude/settings.json.pre-t54-migration" >&2\n',
        '    echo "          applied — ACTION: fix/validate the JSON, then re-run the migration alone:" >&2\n'
        '    echo "              $(_t54_rerun_cmd)" >&2\n'
        "    # A dry run writes no backup (see above): name one only when it exists.\n"
        '    if [[ "$_mig_mode" == "apply" ]]; then\n'
        '      echo "          Pre-migration backup: $BAK_DIR/.claude/settings.json.pre-t54-migration" >&2\n'
        "    fi\n",
        1,
    ),
    # A-R1M9-02 / codex r3: "requires_member_of" names ANY array leaf of the
    # table, so the array pass records the effective value of EVERY array
    # leaf (dry run included), not only availableModels.
    (
        UPGRADE_REL,
        "# --- eff_available_models captures the EFFECTIVE availableModels value AFTER\n"
        "# --- this loop resolves its branch (SET/MIGRATE => new baseline; already-new\n"
        "# --- or CUSTOMIZED => the current value PRESERVED). It is computed\n"
        "# --- independently of the `if not dry` write guard so it holds in BOTH apply\n"
        "# --- and dry-run modes, and it is the allowlist the model-pin SET below must\n"
        "# --- respect (this loop runs BEFORE the model leaf — order is normative).\n"
        "eff_available_models = MISSING\n",
        "# --- effective_arrays[key] captures the EFFECTIVE value of EVERY array leaf\n"
        "# --- AFTER this loop resolves its branch (SET/MIGRATE => new baseline;\n"
        "# --- already-new or CUSTOMIZED => the current value PRESERVED). It is\n"
        "# --- computed independently of the `if not dry` write guard so it holds in\n"
        "# --- BOTH apply and dry-run modes, and the scalar leaves below read it\n"
        '# --- through "requires_member_of" (this loop runs BEFORE them - order is\n'
        "# --- normative).\n"
        "effective_arrays = {}\n",
        1,
    ),
    (
        UPGRADE_REL,
        '    if key == "availableModels":\n'
        "        eff_available_models = resolved\n",
        "    effective_arrays[key] = resolved\n",
        1,
    ),
    # R2M-04 / A-R2CL-05 (fix round r11): the array pass walked a literal
    # tuple, so "every array leaf of the table" held only for today's table.
    # It now walks the TABLE, the mirror of the scalar pass: an array leaf is
    # every top-level entry whose "new" is a JSON list. An array leaf may
    # omit "old" (then only absence and "superseded" migrate).
    (
        UPGRADE_REL,
        'for key in ("availableModels", "fallbackModel"):\n'
        "    spec = baselines[key]\n"
        "    cur = data.get(key, MISSING)\n",
        "# --- An ARRAY leaf is every top-level table entry whose \"new\" is a JSON\n"
        "# --- list: the loop walks the table, so a new array leaf needs no code.\n"
        "for key, spec in baselines.items():\n"
        '    if "." in key or not isinstance(spec, dict):\n'
        "        continue\n"
        '    if not isinstance(spec.get("new"), list):\n'
        "        continue\n"
        "    cur = data.get(key, MISSING)\n",
        1,
    ),
    (
        UPGRADE_REL,
        '    elif cur == spec["old"]:\n',
        '    elif spec.get("old") is not None and cur == spec["old"]:\n',
        1,
    ),
    # The migration body is a bash SINGLE-QUOTED python -c string: nothing in
    # the replacement below may contain an apostrophe.
    (
        UPGRADE_REL,
        '# --- model (top-level SCALAR session-default pin; ADR-181 T1.1 anti-silent-\n'
        '# --- flip). The OLD baseline has NO top-level "model" leaf, so ABSENCE == the\n'
        "# --- old baseline: SET the new pin. An EXPLICIT null is treated as ABSENT for\n"
        "# --- the SET decision (null is not a deliberate model choice — no session-\n"
        "# --- default pin), NOT as a customized value. The SET is CONDITIONAL on the\n"
        "# --- pin being a member of the EFFECTIVE availableModels resolved above (C6):\n"
        "# --- an adopter who customized availableModels to EXCLUDE claude-opus-5 would\n"
        "# --- otherwise get a session-default pin OUTSIDE their own allowlist, which\n"
        "# --- enforceAvailableModels rejects. If the pin is not provably in the\n"
        "# --- effective allowlist (excluded, or the allowlist is not a JSON list we can\n"
        "# --- test) we do NOT pin and emit a NAMED warn, leaving the session default to\n"
        "# --- the harness/adopter. Any PRESENT non-null value != the new pin is adopter-\n"
        "# --- custom -> PRESERVED with a named WARN (never re-flipped); no-value-echo\n"
        "# --- (the adopter value is not printed, only the key name).\n"
        'spec = baselines["model"]\n'
        'pin = spec["new"]\n'
        'cur = data.get("model", MISSING)\n'
        "absent_or_null = cur is MISSING or cur is None\n"
        "pin_in_effective_allowlist = (\n"
        "    isinstance(eff_available_models, list) and pin in eff_available_models\n"
        ")\n"
        "if absent_or_null:\n"
        "    if pin_in_effective_allowlist:\n"
        "        if not dry:\n"
        '            data["model"] = pin\n'
        "        changed[0] = True\n"
        '        act("SET (absent [== old baseline] -> new baseline): model")\n'
        "    else:\n"
        '        warn("WARNING: model pin NOT applied: adopter availableModels "\n'
        '             "excludes claude-opus-5 (session default left to "\n'
        '             "harness/adopter)")\n'
        "elif cur == pin:\n"
        '    out("OK (already at new baseline): model")\n'
        "else:\n"
        '    warn("WARNING: model is ADOPTER-CUSTOMIZED - PRESERVED "\n'
        '         "(not migrated to the new baseline)")\n',
        "# --- Top-level SCALAR leaves: the session-default pin model (ADR-181\n"
        "# --- T1.1 anti-silent-flip) and effortLevel (ADR-149 Amendment 3, S357).\n"
        '# --- A scalar leaf is every top-level table entry whose "new" is a JSON\n'
        "# --- string, and every one of them walks THIS branch - there is no per-key\n"
        "# --- code (cure the class: the 2nd occurrence of a SHIPPED baseline read\n"
        "# --- as ADOPTER-CUSTOMIZED; Amendment 2 cured the ARRAY occurrence above).\n"
        "# --- Per leaf:\n"
        "# ---   absent, or an EXPLICIT null (not a deliberate choice) -> SET new\n"
        "# ---   equal to new -> no-op\n"
        '# ---   equal to a non-null "old", or a member of "superseded" (frozen\n'
        "# ---   shipped literals, exact equality) -> MIGRATE to new\n"
        "# ---   anything else -> ADOPTER-CUSTOMIZED, PRESERVED + named WARN\n"
        '# --- "requires_member_of" (C6 as data): the SET/MIGRATE happens ONLY when\n'
        "# --- the new value is an EXACT member of the EFFECTIVE value that array\n"
        "# --- leaf resolved to above (Claude Code replaces a pin the adopter\n"
        "# --- allowlist does not admit with the default model at startup;\n"
        "# --- exact is stricter than its segment-prefix admission); any array\n"
        "# --- leaf of the table may be named. Otherwise the leaf is left\n"
        "# --- untouched with a named WARN. No-value-echo: an adopter value is\n"
        "# --- never printed - only key names and framework values.\n"
        '# --- "opt_in": true (Owner OQ-7): the SET/MIGRATE happens ONLY when the\n'
        "# --- operator passed --adopt-setting <key> (argv 6, a comma list whose\n"
        "# --- charset bash already checked); otherwise the leaf is not written and\n"
        '# --- a named WARN carries its "cost_note" and the flag. The flag never\n'
        "# --- overrides a PRESENT value: a value already in an opt-in leaf lands\n"
        "# --- in the preserved branch, which names it on stdout without a warning\n"
        "# --- (an opt-in leaf has no baseline an adopter could drift from).\n"
        '# --- "on_migrate_of" (Owner OQ-8): an absent opt-in leaf the operator did\n'
        "# --- not adopt takes the mapped value when the named scalar leaf, walked\n"
        "# --- EARLIER in this pass, MIGRATEd off the named value (migrated_from);\n"
        "# --- a rule naming a leaf not walked yet is a named WARN, never applied.\n"
        "# --- A MIGRATE prints its REVERT line (revert_local: the value it\n"
        "# --- replaced is a framework literal, never an adopter value), and a\n"
        '# --- leaf "notice" is printed whenever the leaf is written.\n'
        'adopted = set(k for k in sys.argv[6].split(",") if k)\n'
        "opt_in_leaves = sorted(k for k, s in baselines.items()\n"
        '                       if isinstance(s, dict) and s.get("opt_in") is True)\n'
        "for k in sorted(adopted - set(opt_in_leaves)):\n"
        '    warn("WARNING: --adopt-setting " + k + " ignored - not an opt-in leaf "\n'
        '         "of the T5.4 table (opt-in leaves: " + ", ".join(opt_in_leaves)\n'
        '         + ")")\n'
        "walked = set()\n"
        "migrated_from = {}\n"
        "for key, spec in baselines.items():\n"
        '    if "." in key or not isinstance(spec, dict):\n'
        "        continue\n"
        '    new_value = spec.get("new")\n'
        "    if not isinstance(new_value, str):\n"
        "        continue\n"
        "    walked.add(key)\n"
        "    cur = data.get(key, MISSING)\n"
        "    if cur is MISSING or cur is None:\n"
        '        verdict = "SET (absent [== old baseline] -> new baseline): " + key\n'
        "    elif cur == new_value:\n"
        '        out("OK (already at new baseline): " + key)\n'
        "        continue\n"
        '    elif spec.get("old") is not None and cur == spec["old"]:\n'
        '        verdict = "MIGRATE (matched OLD baseline -> new baseline): " + key\n'
        '    elif cur in spec.get("superseded", []):\n'
        '        verdict = ("MIGRATE (matched SUPERSEDED shipped baseline -> "\n'
        '                   "new baseline): " + key)\n'
        '    elif spec.get("opt_in") is True:\n'
        '        out("OK (present - PRESERVED; opt-in leaf): " + key)\n'
        "        continue\n"
        "    else:\n"
        '        warn("WARNING: " + key + " is ADOPTER-CUSTOMIZED - PRESERVED "\n'
        '             "(not migrated to the new baseline)")\n'
        "        continue\n"
        '    if spec.get("opt_in") is True and key not in adopted:\n'
        "        kept = None\n"
        '        rule = spec.get("on_migrate_of")\n'
        "        if isinstance(rule, dict):\n"
        "            for dep in sorted(rule):\n"
        "                if dep not in walked:\n"
        '                    warn("WARNING: " + key + " on_migrate_of names " + dep\n'
        '                         + ", which the T5.4 table does not walk before "\n'
        '                         + key + " - rule not applied")\n'
        "                    continue\n"
        "                prev = migrated_from.get(dep, MISSING)\n"
        "                by_prev = rule[dep]\n"
        "                if (isinstance(prev, str) and isinstance(by_prev, dict)\n"
        "                        and isinstance(by_prev.get(prev), str)):\n"
        "                    kept = (dep, prev, by_prev[prev])\n"
        "                    break\n"
        "        if kept is not None:\n"
        "            dep, prev, value = kept\n"
        "            if not dry:\n"
        "                data[key] = value\n"
        "            changed[0] = True\n"
        '            act("MIGRATE (" + dep + " migrated off " + prev + " and " + key\n'
        '                + " was absent -> " + value + "): " + key)\n'
        '            out("  REVERT: to drop it, delete " + key + " from "\n'
        '                ".claude/settings.json (a level set in "\n'
        '                ".claude/settings.local.json also outranks it)")\n'
        '            note = spec.get("on_migrate_note")\n'
        "            if isinstance(note, str) and note:\n"
        '                out("  NOTICE: " + key + " = " + value + " " + note)\n'
        "            continue\n"
        '        warn("WARNING: " + key + " NOT written (opt-in leaf): new installs "\n'
        '             "ship " + key + " = " + new_value + "; "\n'
        '             + str(spec.get("cost_note", "")) + ". To write it into this "\n'
        '             "install, re-run with --adopt-setting " + key)\n'
        "        continue\n"
        '    gate = spec.get("requires_member_of")\n'
        "    if gate is not None:\n"
        "        eff = effective_arrays.get(gate, MISSING)\n"
        "        if not (isinstance(eff, list) and new_value in eff):\n"
        '            warn("WARNING: " + key + " NOT migrated: " + new_value\n'
        '                 + " is not an exact entry of the adopter " + str(gate)\n'
        '                 + " (the harness may still admit it by prefix) - "\n'
        '                 + key + " left untouched")\n'
        "            continue\n"
        "    if not dry:\n"
        "        data[key] = new_value\n"
        "    changed[0] = True\n"
        "    act(verdict)\n"
        '    if verdict.startswith("MIGRATE"):\n'
        "        revert_local([key], cur)\n"
        "        migrated_from[key] = cur\n"
        '    notice = spec.get("notice")\n'
        "    if isinstance(notice, str) and notice:\n"
        '        out("  NOTICE: " + key + " = " + new_value + " " + notice)\n',
        1,
    ),
    (
        UPGRADE_REL,
        "def act(msg):\n"
        "    if dry:\n"
        '        out("(dry-run) would " + msg)\n'
        "    else:\n"
        "        out(msg)\n",
        "def act(msg):\n"
        "    if dry:\n"
        '        out("(dry-run) would " + msg)\n'
        "    else:\n"
        "        out(msg)\n"
        "\n"
        "\n"
        "# ADR-149 Amendment 3 (S357): every MIGRATE line, in a dry run too, is\n"
        "# followed by a REVERT line. A scalar value is overridden by\n"
        "# .claude/settings.local.json (local settings beat this file, and\n"
        "# upgrade.sh never writes that file), so revert_local prints the entry\n"
        "# that keeps the previous value; that value is always a FRAMEWORK literal\n"
        "# (an old or superseded baseline), never an adopter value. The ARRAY\n"
        "# leaves and the hook registration name the pre-migration backup instead\n"
        "# (revert_backup): availableModels and hook registrations merge across\n"
        "# settings scopes, so a local entry cannot take a migrated value back\n"
        "# out; fallbackModel is replaced wholesale by a higher scope, and the\n"
        "# backup is the route that restores the project file itself. A dry run\n"
        "# writes no backup, and its REVERT line says so.\n"
        "def revert_local(keys, previous):\n"
        "    node = previous\n"
        "    for k in reversed(keys):\n"
        "        node = {k: node}\n"
        '    out("  REVERT: to keep the previous value, merge "\n'
        "        + json.dumps(node, ensure_ascii=False)\n"
        '        + " into .claude/settings.local.json")\n'
        "\n"
        "\n"
        "def revert_backup():\n"
        "    if dry:\n"
        '        out("  REVERT: an apply run backs up .claude/settings.json "\n'
        '            "first and names the backup; copying it back undoes this")\n'
        "    else:\n"
        '        out("  REVERT: copy the pre-migration backup named above back "\n'
        '            "over .claude/settings.json")\n',
        1,
    ),
    (
        UPGRADE_REL,
        '        act("MIGRATE (matched OLD baseline -> new baseline): " + key)\n',
        '        act("MIGRATE (matched OLD baseline -> new baseline): " + key)\n'
        "        revert_backup()\n",
        1,
    ),
    (
        UPGRADE_REL,
        '        act("MIGRATE (matched SUPERSEDED shipped baseline -> new baseline): " + key)\n',
        '        act("MIGRATE (matched SUPERSEDED shipped baseline -> new baseline): " + key)\n'
        "        revert_backup()\n",
        1,
    ),
    (
        UPGRADE_REL,
        '        act("MIGRATE (matched OLD baseline -> new baseline): "\n'
        '            "permissions.defaultMode")\n',
        '        act("MIGRATE (matched OLD baseline -> new baseline): "\n'
        '            "permissions.defaultMode")\n'
        '        revert_local(["permissions", "defaultMode"], spec["old"])\n',
        1,
    ),
    (
        UPGRADE_REL,
        '            act("MIGRATE (matched OLD pair-rail cap -> template cap"\n'
        '                " + statusMessage if absent): "\n'
        '                "hooks.PreToolUse[check_pair_rail.py].timeout")\n',
        '            act("MIGRATE (matched OLD pair-rail cap -> template cap"\n'
        '                " + statusMessage if absent): "\n'
        '                "hooks.PreToolUse[check_pair_rail.py].timeout")\n'
        "            revert_backup()\n",
        1,
    ),
    (
        UPGRADE_REL,
        '    with os.fdopen(fd, "w", encoding="utf-8") as f:\n'
        "        json.dump(data, f, indent=2)\n"
        '        f.write("\\n")\n',
        "    # ADR-149 Amendment 3 (S357): ensure_ascii=False keeps every\n"
        "    # character outside ASCII as written (the templates carry many); the\n"
        "    # default escaped them all, so a one-leaf migration rewrote every such\n"
        "    # line. A string UTF-8 cannot encode (a lone surrogate, which\n"
        "    # json.load accepts in its escaped form) falls back to the escaped\n"
        "    # writer of earlier releases, so such a file still migrates. A file\n"
        "    # that an earlier release migrated holds those characters ESCAPED:\n"
        "    # its first migration here rewrites each such line once, unescaped.\n"
        '    body = json.dumps(data, indent=2, ensure_ascii=False) + "\\n"\n'
        "    try:\n"
        '        body.encode("utf-8")\n'
        "    except UnicodeEncodeError:\n"
        '        body = json.dumps(data, indent=2) + "\\n"\n'
        '    with os.fdopen(fd, "w", encoding="utf-8") as f:\n'
        "        f.write(body)\n",
        1,
    ),
    (
        UPGRADE_REL,
        'out("WROTE: .claude/settings.json (atomic; only migrated leaf keys changed)")\n',
        'out("WROTE: .claude/settings.json (atomic; only the migrated leaf values "\n'
        '    "changed; the JSON is re-serialized)")\n',
        1,
    ),
    (
        UPGRADE_REL,
        "' \"$_mig_mode\" \"$settings\" \"$_T54_BASELINES_JSON\" \"$_mig_gate\" \"$_mig_template\"; then\n",
        "' \"$_mig_mode\" \"$settings\" \"$_T54_BASELINES_JSON\" \"$_mig_gate\" \"$_mig_template\" \"$ADOPT_SETTINGS\"; then\n",
        1,
    ),
    # ADR-149 Amendment 3 (Owner OQ-9, 2026-09-24): the Claude Code floor.
    # The T3.4 comment named the adopter floor as >=2.0; the floor is now
    # 2.1.280 and the gate itself stays OFF (A3.5).
    (
        UPGRADE_REL,
        "# Notification). SUPPORT.md declares the adopter floor >=2.0; until the\n",
        "# Notification). SUPPORT.md declared the adopter floor >=2.0 when this\n"
        "# gate was written (from v1.4.2 it is 2.1.280, ADR-149 Amendment 3, which\n"
        "# leaves this gate OFF); until the\n",
        1,
    ),
    (
        UPGRADE_REL,
        "      See the 'PRECONDITION FAILED' line in the output for which one.\n",
        "      See the 'PRECONDITION FAILED' line in the output for which one.\n"
        "  6 — the claude CLI on PATH is older than the Claude Code floor of this\n"
        "      release (SUPPORT.md) and --allow-old-claude-code was not passed;\n"
        "      nothing was written.\n",
        1,
    ),
    (
        UPGRADE_REL,
        'if [[ -z "$TARGET" || ! -d "$TARGET" ]]; then\n'
        '  echo "Usage: $0 <target-repo-path> [--profile <list>] [--stack <name>] [--pin <tag>] [--dry-run] [--ceremony <maintainer|user>]" >&2\n'
        "  exit 1\n"
        "fi\n",
        'if [[ -z "$TARGET" || ! -d "$TARGET" ]]; then\n'
        '  echo "Usage: $0 <target-repo-path> [--profile <list>] [--stack <name>] [--pin <tag>] [--dry-run] [--ceremony <maintainer|user>]" >&2\n'
        "  exit 1\n"
        "fi\n"
        "\n"
        + _FLOOR_CHECK_SH
        + 'if ! _claude_code_floor_check "$ALLOW_OLD_CLAUDE_CODE" "$DRY_RUN"; then\n'
        "  exit 6\n"
        "fi\n"
        "# ADR-149 Amendment 3: --adopt-setting feeds ONLY the T5.4 migration;\n"
        "# under --no-settings-migrate it would otherwise be dropped in silence.\n"
        'if [[ -n "$ADOPT_SETTINGS" && "$SETTINGS_MIGRATE" -eq 0 ]]; then\n'
        '  echo "WARNING: --adopt-setting $ADOPT_SETTINGS ignored: --no-settings-migrate skips the T5.4 settings migration; set it by hand in .claude/settings.json" >&2\n'
        "fi\n",
        1,
    ),
    # ============================================================ install.sh
    # ADR-149 Amendment 3 (Owner OQ-9, 2026-09-24): the same floor check,
    # byte-identical block, before the install writes anything.
    (
        INSTALL_REL,
        "#   --dry-run                      Print what WOULD be done (mkdir, cp, sed) without\n"
        "#                                    touching $TARGET. Exit 0 after preview.\n",
        "#   --dry-run                      Print what WOULD be done (mkdir, cp, sed) without\n"
        "#                                    touching $TARGET. Exit 0 after preview.\n"
        "#\n"
        "#   --allow-old-claude-code        Install although the claude CLI on PATH is older\n"
        "#                                    than the Claude Code floor of this release\n"
        "#                                    (2.1.280, SUPPORT.md; ADR-149 Amendment 3).\n"
        "#                                    Without it such an install is REFUSED (exit 6)\n"
        "#                                    before anything is written; with no claude on\n"
        "#                                    PATH (CI, headless) the install warns and goes on.\n",
        1,
    ),
    (
        INSTALL_REL,
        "DRY_RUN=0\n"
        "STRICT_PLACEHOLDERS=0\n",
        "DRY_RUN=0\n"
        "ALLOW_OLD_CLAUDE_CODE=0  # ADR-149 A3 (OQ-9): --allow-old-claude-code continues below the floor\n"
        "STRICT_PLACEHOLDERS=0\n",
        1,
    ),
    (
        INSTALL_REL,
        "    --dry-run)\n"
        "      DRY_RUN=1; shift ;;\n",
        "    --dry-run)\n"
        "      DRY_RUN=1; shift ;;\n"
        "    --allow-old-claude-code)\n"
        "      # ADR-149 Amendment 3 (Owner OQ-9): continue below the floor.\n"
        "      ALLOW_OLD_CLAUDE_CODE=1; shift ;;\n",
        1,
    ),
    (
        INSTALL_REL,
        'if [[ "$DRY_RUN" -eq 1 ]]; then\n'
        '  echo "    Dry-run:      YES (no files will be written)"\n'
        "fi\n"
        'echo ""\n',
        'if [[ "$DRY_RUN" -eq 1 ]]; then\n'
        '  echo "    Dry-run:      YES (no files will be written)"\n'
        "fi\n"
        "\n"
        + _FLOOR_CHECK_SH
        + 'if ! _claude_code_floor_check "$ALLOW_OLD_CLAUDE_CODE" "$DRY_RUN"; then\n'
        "  exit 6\n"
        "fi\n"
        'echo ""\n',
        1,
    ),
    # LA-R3CL-08 (rail round 3): cite by SYMBOL, never by line, any file
    # this pack edits (the [1m] fold above shifts effective_config.py, the
    # amendment shifts ADR-149).
    (
        UPGRADE_REL,
        "# ADR-149:95-102; mirror test :127-149,193-200); any other order needs an\n"
        "# ADR-181 justification. permissions.defaultMode follows the exact read\n"
        "# contract of _lib/effective_config.py:178-180,534-542 (stripped string).\n",
        "# the ADR-149 A1.1 order rule; mirror test :127-149,193-200); any other\n"
        "# order needs an ADR-181 justification. permissions.defaultMode follows\n"
        "# the exact read contract of _lib/effective_config.py (the\n"
        "# permissions.defaultMode row of its tamper table and\n"
        "# _check_settings_layer (d)): a stripped string.\n",
        1,
    ),
    (
        UPGRADE_REL,
        "# --- permissions.defaultMode (read contract: effective_config.py\n"
        "# --- :178-180,534-542 - a stripped string under the permissions object).\n",
        "# --- permissions.defaultMode (read contract: effective_config.py, its\n"
        "# --- permissions.defaultMode row and _check_settings_layer (d) - a\n"
        "# --- stripped string under the permissions object).\n",
        1,
    ),
    (
        ".claude/scripts/tests/test_upgrade_settings_migration.py",
        "    Read contract: _lib/effective_config.py:178-180,534-542 (a stripped\n"
        "    string under the permissions object).\n",
        "    Read contract: _lib/effective_config.py, its permissions.defaultMode\n"
        "    row and _check_settings_layer (d) (a stripped string under the\n"
        "    permissions object).\n",
        1,
    ),
    # ======== installer-write-safety ratchet: NOT an edit. CLAUDE.md
    # (PLAN-185): a wave that touches scripts/ REGENERATES the baseline in
    # the same patch. apply-opus55-edits.py regenerates it with the census
    # itself over the post-edit tree and refuses unless the row delta equals
    # RATCHET_DELTA below (A-R1M9-03: a hand-patched row left the line
    # numbers of every other row of the touched scripts stale).
    # ============================================ agent_frontmatter.py floor
    (
        ".claude/hooks/_lib/agent_frontmatter.py",
        '    "claude-opus-5",   # ADR-181 (PLAN-163 T1.3, OQ1=b): Claude 5 Opus joins\n'
        "                       # the floor; claude-fable-5 remains the preferred\n"
        "                       # ceiling pin for VETO personas (frontmatter unchanged).\n"
        "})\n",
        '    "claude-opus-5",   # ADR-181 (PLAN-163 T1.3, OQ1=b): Claude 5 Opus joins\n'
        "                       # the floor; claude-fable-5 remains the preferred\n"
        "                       # ceiling pin for VETO personas (frontmatter unchanged).\n"
        '    "claude-opus-5-5",  # ADR-149 Amendment 3 (S357, PLAN-193): Opus 5.5 joins\n'
        "                        # the floor as an ELIGIBLE id; no agent file migrates\n"
        "                        # (the veto_floor agents keep claude-fable-5).\n"
        "})\n",
        1,
    ),
    # ============================ effective_config.py — [1m] fold (SI-10/FIN-2)
    (
        ".claude/hooks/_lib/effective_config.py",
        '_MODEL_REMAP_PREFIX = "ANTHROPIC_DEFAULT_"\n',
        '_MODEL_REMAP_PREFIX = "ANTHROPIC_DEFAULT_"\n'
        "#: ADR-149 Amendment 3 (S357): the trailing ``[1m]`` tag selects the 1M\n"
        "#: context window of a model; it is not part of the model id. ONE such\n"
        "#: tag is folded before the allowlist membership test, so\n"
        "#: ``claude-opus-5-5[1m]`` is the floor member ``claude-opus-5-5``. Only\n"
        "#: this exact tag folds: any other suffix is compared as written, and a\n"
        "#: value the check cannot classify stays flagged (fail-closed on input).\n"
        '_ONE_M_CONTEXT_TAG = "[1m]"\n'
        "\n"
        "\n"
        "def _fold_one_m_tag(model_id: str) -> str:\n"
        '    """Strip ONE trailing ``[1m]`` context tag (ADR-149 Amendment 3)."""\n'
        "    if model_id.endswith(_ONE_M_CONTEXT_TAG):\n"
        "        return model_id[: -len(_ONE_M_CONTEXT_TAG)]\n"
        "    return model_id\n",
        1,
    ),
    (
        ".claude/hooks/_lib/effective_config.py",
        "                if stripped not in allow_set:\n",
        "                if _fold_one_m_tag(stripped) not in allow_set:\n",
        1,
    ),
    (
        ".claude/hooks/tests/test_effective_config.py",
        "    def test_allowlist_unavailable_degrades_fail_open(self) -> None:\n",
        "    def test_one_m_context_tag_on_a_member_is_not_flagged(self) -> None:\n"
        '        """ADR-149 Amendment 3 (S357): ``[1m]`` selects the 1M context\n'
        "        window, not a model. RED on 19771fa1: the exact comparison flagged\n"
        '        the floor member written with the tag as a remap."""\n'
        '        self.write_adr149(members=("claude-opus-4-8", "claude-opus-5-5"))\n'
        "        self.write_settings(\n"
        '            "project",\n'
        '            {"env": {"ANTHROPIC_DEFAULT_OPUS_MODEL": "claude-opus-5-5[1m]"}},\n'
        "        )\n"
        "        self.assertEqual(\n"
        '            self.classify({"ANTHROPIC_MODEL": "claude-opus-5-5[1m]"}), []\n'
        "        )\n"
        "\n"
        "    def test_one_m_fold_never_launders_another_value(self) -> None:\n"
        '        """Only ONE exact trailing ``[1m]`` folds; the base must still be a\n'
        '        member, and any other suffix is compared as written."""\n'
        '        self.write_adr149(members=("claude-opus-4-8", "claude-opus-5-5"))\n'
        "        for value in (\n"
        '            "gpt-5o[1m]", "[1m]", "claude-opus-5-5[2m]",\n'
        '            "claude-opus-5-5[1m][1m]", "claude-opus-5-5[1M]",\n'
        '            "claude-opus-5-5 [1m]",\n'
        "        ):\n"
        "            with self.subTest(value=value):\n"
        '                findings = self.classify({"ANTHROPIC_MODEL": value})\n'
        "                self.assertEqual(\n"
        "                    self.classes_of(findings), [ec.TAMPER_MODEL_REMAP]\n"
        "                )\n"
        "\n"
        "    def test_allowlist_unavailable_degrades_fail_open(self) -> None:\n",
        1,
    ),
    # ================================== adapters/live/claude.py (class cure)
    (
        ".claude/hooks/_lib/adapters/live/claude.py",
        "# PLAN-134 W0 E6-F2 — extended-thinking request-surface generation gate.\n"
        "# The current API generation accepts ONLY adaptive thinking: the legacy\n"
        '# ``{"type": "enabled", "budget_tokens": N}`` shape is REMOVED (HTTP 400) on\n'
        "# Opus 4.7 / Opus 4.8 / Fable 5 and deprecated on the 4.6 family. The 4.6\n"
        "# family is deliberately included here so the deprecated shape is retired\n"
        "# everywhere; only pre-4.6 ids keep the legacy enabled/budget path.\n"
        "# Allowlist-prefix semantics (ADR-149 spirit): prefix match keeps\n"
        "# date-suffixed ids covered without pinning exact strings.\n"
        "_ADAPTIVE_ONLY_MODELS = (\n"
        '    "claude-opus-4-6",\n'
        '    "claude-sonnet-4-6",\n'
        '    "claude-opus-4-7",\n'
        '    "claude-opus-4-8",\n'
        '    "claude-fable-5",\n'
        ")\n"
        "\n"
        "\n"
        "def _is_adaptive_only(model: str) -> bool:\n"
        '    """Return True when ``model`` accepts only adaptive thinking."""\n'
        "    return isinstance(model, str) and any(\n"
        "        model.startswith(prefix) for prefix in _ADAPTIVE_ONLY_MODELS\n"
        "    )\n",
        "# PLAN-134 W0 E6-F2 — extended-thinking request-surface generation gate.\n"
        "# Every id outside the closed legacy list below is sent adaptive thinking,\n"
        "# never the legacy ``{\"type\": \"enabled\", \"budget_tokens\": N}`` shape. The\n"
        "# thinking troubleshooting page (re-read 2026-09-24) lists adaptive as a\n"
        "# mode of every model after Claude 4.5; the legacy shape is an HTTP 400 on\n"
        "# Claude 4.7 and later (Claude Mythos Preview, which supports both modes,\n"
        "# excepted) and deprecated on the 4.6 models, deliberately treated as\n"
        "# adaptive-only too.\n"
        "#\n"
        "# ADR-149 Amendment 3 (S357) — CLASS CURE, inverted default. Until S357\n"
        "# this module listed the ADAPTIVE ids and fell back to the legacy shape\n"
        "# for every other id, so each new generation had to be added by hand;\n"
        "# claude-opus-5 and claude-sonnet-5 never were (second occurrence). The\n"
        "# list is now the other one: the CLOSED set of pre-4.6 ids, whose only\n"
        "# thinking mode is the legacy enabled/budget shape, kept as before. No\n"
        "# model will ever join it, and every id outside it is adaptive-only — a\n"
        "# new model id is safe by default.\n"
        "# Match (this list and the always-on list below): an entry matches its\n"
        "# EXACT id, optionally followed by ONE dated snapshot segment \"-YYYYMMDD\"\n"
        "# (a Vertex \"@YYYYMMDD\" reads as that segment) and then by a Bedrock\n"
        "# version suffix \"-vN\" or \"-vN:M\". Nothing else extends an entry: an id\n"
        "# that adds any other \"-\" segment is a DIFFERENT id and takes the default\n"
        "# class. The one family is the Claude 3 generation\n"
        "# (_LEGACY_BUDGET_FAMILIES): every id that starts with \"claude-3-\". The\n"
        "# 4.0 generation also ships as a bare dated id (claude-opus-4-YYYYMMDD),\n"
        "# matched through _LEGACY_BUDGET_DATED_BASES only WITH its date, so\n"
        "# claude-opus-4-6 can never match. A provider prefix before \"claude-\" and\n"
        "# a trailing \"[...]\" packaging tag are ignored.\n"
        "_LEGACY_BUDGET_FAMILIES = (\"claude-3\",)  # every Claude 3.x id (pre-adaptive)\n"
        "_LEGACY_BUDGET_MODELS = (\n"
        "    \"claude-haiku-4-5\",\n"
        "    \"claude-sonnet-4-5\",\n"
        "    \"claude-opus-4-5\",\n"
        "    \"claude-opus-4-1\",\n"
        "    \"claude-opus-4-0\",\n"
        "    \"claude-sonnet-4-0\",\n"
        ")\n"
        "_LEGACY_BUDGET_DATED_BASES = (\"claude-opus-4\", \"claude-sonnet-4\")\n"
        "_PACKAGING_TAG_RE = re.compile(r\"\\[[^\\]]*\\]$\")\n"
        "_VERTEX_DATE_SUFFIX_RE = re.compile(r\"@(\\d{8})$\")\n"
        "_BEDROCK_VERSION_SUFFIX_RE = re.compile(r\"-v\\d+(?::\\d+)?$\")\n"
        "_DATE_SUFFIX_RE = re.compile(r\"-\\d{8}$\")\n"
        "\n"
        "# ADR-149 Amendment 3 (S357): the ids this adapter knows to be ALWAYS ON\n"
        "# (thinking cannot be turned off; ``{\"type\": \"disabled\"}`` is an HTTP 400):\n"
        "# the models the Anthropic thinking troubleshooting page (re-read\n"
        "# 2026-09-24) lists as always on — Fable 5 and 5.1, Mythos 5 and 5.1,\n"
        "# Mythos Preview and Opus 5.5 — by their API ids, matched by the rule\n"
        "# above. Only on these is a caller's disabled dict dropped: elsewhere it\n"
        "# is sent as given, because a model whose thinking defaults ON accepts it\n"
        "# (Sonnet 5; Opus 5 at effort high or below, the page says) and dropping\n"
        "# it would switch thinking on in silence; an always-on id missing here\n"
        "# answers with a loud 400, never with silent thinking.\n"
        "_ALWAYS_ON_THINKING_MODELS = (\n"
        "    \"claude-fable-5\",\n"
        "    \"claude-fable-5-1\",\n"
        "    \"claude-mythos-5\",\n"
        "    \"claude-mythos-5-1\",\n"
        "    \"claude-mythos-preview\",\n"
        "    \"claude-opus-5-5\",\n"
        ")\n"
        "\n"
        "\n"
        "def _normalized_model_id(model: str) -> str:\n"
        "    \"\"\"Lower-case ``model`` from ``claude-`` on, without a trailing\n"
        "    ``[...]`` tag and with a Vertex ``@YYYYMMDD`` read as ``-YYYYMMDD``\n"
        "    (\"\" when no ``claude-`` id is present).\"\"\"\n"
        "    norm = _PACKAGING_TAG_RE.sub(\"\", model.strip().lower())\n"
        "    norm = _VERTEX_DATE_SUFFIX_RE.sub(r\"-\\1\", norm)\n"
        "    start = norm.find(\"claude-\")\n"
        "    return norm[start:] if start >= 0 else \"\"\n"
        "\n"
        "\n"
        "def _base_model_id(norm: str) -> tuple:\n"
        "    \"\"\"``(base, dated)``: ``norm`` without ONE trailing Bedrock version\n"
        "    suffix and then without ONE trailing ``-YYYYMMDD`` date segment;\n"
        "    ``dated`` says whether a date segment was removed.\"\"\"\n"
        "    stem = _BEDROCK_VERSION_SUFFIX_RE.sub(\"\", norm)\n"
        "    base = _DATE_SUFFIX_RE.sub(\"\", stem)\n"
        "    return base, base != stem\n"
        "\n"
        "\n"
        "def _uses_legacy_budget(model: str) -> bool:\n"
        "    \"\"\"True when ``model`` is one of the closed pre-4.6 legacy ids.\"\"\"\n"
        "    norm = _normalized_model_id(model)\n"
        "    if not norm:\n"
        "        return False\n"
        "    if any(norm.startswith(family + \"-\") for family in _LEGACY_BUDGET_FAMILIES):\n"
        "        return True\n"
        "    base, dated = _base_model_id(norm)\n"
        "    return base in _LEGACY_BUDGET_MODELS or (\n"
        "        dated and base in _LEGACY_BUDGET_DATED_BASES\n"
        "    )\n"
        "\n"
        "\n"
        "def _rejects_disabled_thinking(model: str) -> bool:\n"
        "    \"\"\"True when ``model`` is a known always-on id (ADR-149 A3).\"\"\"\n"
        "    if not isinstance(model, str):\n"
        "        return False\n"
        "    norm = _normalized_model_id(model)\n"
        "    return bool(norm) and _base_model_id(norm)[0] in _ALWAYS_ON_THINKING_MODELS\n"
        "\n"
        "\n"
        "def _is_adaptive_only(model: str) -> bool:\n"
        "    \"\"\"Return True when ``model`` accepts only adaptive thinking.\n"
        "\n"
        "    Every non-empty id outside the closed legacy list is adaptive-only\n"
        "    (ADR-149 Amendment 3 inverted default); a non-str or empty value is\n"
        "    not a model and stays False.\n"
        "    \"\"\"\n"
        "    return (\n"
        "        isinstance(model, str)\n"
        "        and bool(model.strip())\n"
        "        and not _uses_legacy_budget(model)\n"
        "    )\n",
        1,
    ),
    (
        ".claude/hooks/_lib/adapters/live/claude.py",
        "    - Adaptive-only generation (``_ADAPTIVE_ONLY_MODELS``): returns\n",
        "    - Adaptive-only ids (every id outside the closed legacy list that\n"
        "      ``_uses_legacy_budget`` matches): returns\n",
        1,
    ),
    # R2M-06 (fix round r11): the consequence of omitting the param, by shape.
    (
        ".claude/hooks/_lib/adapters/live/claude.py",
        '      explicit ``{"type": "disabled"}`` is an HTTP 400 on Fable 5).\n',
        '      explicit ``{"type": "disabled"}`` is an HTTP 400 on Fable 5). On\n'
        "      an id whose thinking defaults on, omitting it leaves thinking ON:\n"
        "      ``off`` does not turn thinking off there (ADR-149 A3.4).\n",
        1,
    ),
    (
        ".claude/hooks/_lib/adapters/live/claude.py",
        '        #   - {"type": "disabled"}      → REMOVE the thinking key entirely\n'
        "        #     (an explicit disabled is an HTTP 400 on Fable 5; omitting the\n"
        "        #     param is the only safe spelling across the generation);\n",
        '        #   - {"type": "disabled"}      → REMOVE the thinking key entirely,\n'
        "        #     ONLY on a known always-on id (_ALWAYS_ON_THINKING_MODELS:\n"
        "        #     there an explicit disabled is an HTTP 400 and omitting the\n"
        "        #     param is the only valid spelling). Elsewhere it is sent as\n"
        "        #     given: Sonnet 5 and Opus 5 default to thinking ON and accept\n"
        "        #     it (Opus 5 at effort high or below), so dropping it would\n"
        "        #     switch thinking on in silence (ADR-149 Amendment 3);\n",
        1,
    ),
    (
        ".claude/hooks/_lib/adapters/live/claude.py",
        '            elif _t_type == "disabled":\n'
        '                body.pop("thinking", None)\n',
        '            elif _t_type == "disabled" and _rejects_disabled_thinking(model):\n'
        '                body.pop("thinking", None)\n',
        1,
    ),
    (
        ".claude/hooks/tests/test_claude_adapter_thinking.py",
        "class TestResolveEffortConfig(TestEnvContext):\n",
        "class TestAdaptiveIsTheDefault(TestEnvContext):\n"
        '    """ADR-149 Amendment 3 (S357) — class cure, inverted default.\n'
        "\n"
        "    RED on 19771fa1: the adaptive-only list was an allowlist that never\n"
        "    gained claude-opus-5 / claude-sonnet-5, so ``CEO_EFFORT_OVERRIDE``\n"
        "    sent them (and would send claude-opus-5-5, or any next id) the legacy\n"
        "    ``budget_tokens`` shape. The closed list is now the LEGACY one.\n"
        '    """\n'
        "\n"
        "    _CURRENT = (\n"
        '        "claude-opus-5", "claude-sonnet-5", "claude-opus-5-5",\n'
        '        "claude-fable-5-1", "claude-opus-5-5[1m]",\n'
        "    )\n"
        "    _FUTURE = (\n"
        '        "claude-opus-6", "claude-sonnet-5-1", "claude-some-future-model-9",\n'
        '        "claude-zeta-9",\n'
        "    )\n"
        "\n"
        "    def test_claude5_generation_is_adaptive_only(self):\n"
        "        for model in self._CURRENT:\n"
        "            self.assertTrue(claude_live._is_adaptive_only(model), model)\n"
        "\n"
        "    def test_unknown_future_id_is_adaptive_by_default(self):\n"
        "        for model in self._FUTURE:\n"
        "            self.assertTrue(claude_live._is_adaptive_only(model), model)\n"
        "\n"
        "    def test_every_legacy_id_keeps_the_budget_shape(self):\n"
        "        for model in (\n"
        '            "claude-sonnet-4-5", "claude-sonnet-4-5-20250929",\n'
        '            "claude-sonnet-4-5[1m]", "claude-opus-4-5",\n'
        '            "claude-opus-4-5-20251101", "claude-opus-4-1",\n'
        '            "claude-opus-4-1-20250805", "claude-opus-4-0",\n'
        '            "claude-opus-4-20250514", "claude-sonnet-4-0",\n'
        '            "claude-sonnet-4-20250514", "claude-haiku-4-5",\n'
        '            "claude-haiku-4-5-20251001", "claude-3-7-sonnet-20250219",\n'
        '            "claude-3-5-haiku-20241022",\n'
        '            "anthropic.claude-opus-4-5-20251101-v1:0",\n'
        "        ):\n"
        "            self.assertFalse(claude_live._is_adaptive_only(model), model)\n"
        "\n"
        "    def test_legacy_list_never_swallows_a_4_6_plus_id(self):\n"
        "        for model in (\n"
        '            "claude-opus-4-6", "claude-sonnet-4-6", "claude-opus-4-7",\n'
        '            "claude-opus-4-8", "claude-opus-4-8-20260301",\n'
        "        ):\n"
        "            self.assertTrue(claude_live._is_adaptive_only(model), model)\n"
        "\n"
        "    def test_legacy_match_stops_at_a_segment_boundary(self):\n"
        '        # "claude-opus-4-1" is legacy; "claude-opus-4-10" shares a string\n'
        "        # prefix with it but not a segment, so it is NOT legacy. Same for\n"
        '        # a longer version number or a "claude-3" look-alike.\n'
        "        for model in (\n"
        '            "claude-opus-4-10", "claude-haiku-4-50", "claude-sonnet-4-5x",\n'
        '            "claude-30-opus", "claude-opus-4-2025",\n'
        "        ):\n"
        "            self.assertTrue(claude_live._is_adaptive_only(model), model)\n"
        "\n"
        "    def test_vertex_dated_legacy_ids_keep_the_budget_shape(self):\n"
        '        # Vertex spells a dated id "<id>@YYYYMMDD" (models overview:\n'
        '        # claude-haiku-4-5@20251001). RED on the r8 derivation of this\n'
        '        # wave, which matched only a "-" boundary (codex rail r1 P1).\n'
        "        for model in (\n"
        '            "claude-sonnet-4@20250514", "claude-opus-4@20250514",\n'
        '            "claude-opus-4-1@20250805", "claude-sonnet-4-5@20250929",\n'
        '            "claude-haiku-4-5@20251001", "claude-opus-4-5@20251101",\n'
        '            "claude-3-7-sonnet@20250219", "claude-3-5-sonnet-v2@20241022",\n'
        '            "claude-sonnet-4-5@20250929[1m]",\n'
        "        ):\n"
        "            self.assertFalse(claude_live._is_adaptive_only(model), model)\n"
        "\n"
        "    def test_vertex_suffix_never_moves_a_4_6_plus_id_to_legacy(self):\n"
        "        # Shape controls (the date is synthetic): the @-date reads as a\n"
        "        # date segment, so it can only ever match a DATED legacy base.\n"
        "        for model in (\n"
        '            "claude-opus-4-8@20260101", "claude-sonnet-4-6@20260101",\n'
        '            "claude-opus-4-6@20260101", "claude-opus-5-5@20260101",\n'
        '            "claude-opus-4-10@20260101",\n'
        "        ):\n"
        "            self.assertTrue(claude_live._is_adaptive_only(model), model)\n"
        "\n"
        "    def test_only_known_always_on_ids_reject_disabled(self):\n"
        "        for model in (\n"
        '            "claude-fable-5", "claude-fable-5-1", "claude-opus-5-5",\n'
        '            "claude-opus-5-5[1m]", "anthropic.claude-opus-5-5",\n'
        '            "claude-mythos-5", "claude-mythos-5-1", "claude-mythos-preview",\n'
        "        ):\n"
        "            self.assertTrue(claude_live._rejects_disabled_thinking(model), model)\n"
        "        for model in (\n"
        '            "claude-opus-5", "claude-sonnet-5", "claude-opus-4-8",\n'
        '            "claude-sonnet-4-6", "claude-zeta-9", "claude-fable-50",\n'
        '            "claude-opus-5-50", "claude-mythos-50", "", None,\n'
        "        ):\n"
        "            self.assertFalse(claude_live._rejects_disabled_thinking(model), model)\n"
        "\n"
        "    def test_a_listed_id_extended_by_another_segment_is_a_different_id(self):\n"
        "        # A-R3CX-01 (codex lens, rail round 3): the matcher put \"<listed\n"
        "        # id>-<any segment>\" in the listed class. RED on the r11 derivation\n"
        "        # of this wave: claude-haiku-4-5-2 read as legacy and\n"
        "        # claude-opus-5-5-next as always on.\n"
        "        for model in (\n"
        "            \"claude-haiku-4-5-2\", \"claude-opus-4-5-next\",\n"
        "            \"claude-sonnet-4-5-lite\", \"claude-opus-4-1-20250805-next\",\n"
        "        ):\n"
        "            self.assertTrue(claude_live._is_adaptive_only(model), model)\n"
        "        for model in (\n"
        "            \"claude-opus-5-5-next\", \"claude-fable-5-lite\",\n"
        "            \"claude-mythos-5-1-mini\", \"claude-opus-5-5-fast\",\n"
        "        ):\n"
        "            self.assertFalse(claude_live._rejects_disabled_thinking(model), model)\n"
        "\n"
        "    def test_dated_and_bedrock_spellings_keep_their_class(self):\n"
        "        # Shape controls (synthetic dates and versions where no such id is\n"
        "        # published): ONE date segment, then ONE Bedrock version suffix.\n"
        "        for model in (\n"
        "            \"anthropic.claude-haiku-4-5-20251001-v1:0\",\n"
        "            \"us.anthropic.claude-sonnet-4-5-20250929-v1:0\",\n"
        "            \"anthropic.claude-opus-4-20250514-v1:0\", \"claude-opus-4-1-v1\",\n"
        "        ):\n"
        "            self.assertFalse(claude_live._is_adaptive_only(model), model)\n"
        "        for model in (\n"
        "            \"claude-opus-5-5-20260101\", \"anthropic.claude-opus-5-5-v1:0\",\n"
        "            \"claude-fable-5-1@20260101\", \"claude-mythos-preview-20260101\",\n"
        "        ):\n"
        "            self.assertTrue(claude_live._rejects_disabled_thinking(model), model)\n"
        "        # the 4.0 dated bases match only WITH a date\n"
        "        for model in (\"claude-opus-4\", \"claude-sonnet-4-v1:0\"):\n"
        "            self.assertTrue(claude_live._is_adaptive_only(model), model)\n"
        "\n"
        "    def test_empty_model_is_not_adaptive(self):\n"
        '        self.assertFalse(claude_live._is_adaptive_only(""))\n'
        '        self.assertFalse(claude_live._is_adaptive_only("   "))\n'
        "        self.assertFalse(claude_live._is_adaptive_only(None))\n"
        "\n"
        "    def test_effort_override_never_emits_budget_on_current_ids(self):\n"
        '        os.environ["CEO_EFFORT_OVERRIDE"] = "high"\n'
        "        for model in self._CURRENT + self._FUTURE:\n"
        "            thinking, output_config = claude_live._resolve_effort_config(model)\n"
        '            self.assertEqual(thinking, {"type": "adaptive"}, model)\n'
        '            self.assertEqual(output_config, {"effort": "high"}, model)\n'
        "\n"
        "\n"
        "class TestResolveEffortConfig(TestEnvContext):\n",
        1,
    ),
    (
        ".claude/hooks/tests/test_claude_adapter_thinking.py",
        "    def test_caller_adaptive_with_budget_tokens_stripped_on_adaptive_only(self):\n",
        "    def test_caller_disabled_dict_follows_the_documented_default(self):\n"
        '        """ADR-149 Amendment 3 (S357): a caller\'s {"type": "disabled"} is\n'
        "        dropped only on a known always-on id (the API rejects it there);\n"
        "        on an id whose thinking defaults on or off it is sent as given —\n"
        "        dropping it would switch thinking on in silence on Opus 5 and\n"
        "        Sonnet 5. RED on the r8 derivation of this wave, which dropped\n"
        '        it on every adaptive-only id."""\n'
        "        self._enable_live()\n"
        '        os.environ.pop("CEO_EFFORT_OVERRIDE", None)\n'
        '        os.environ.pop("CEO_THINKING_AUTO_DISABLE", None)\n'
        "        for model, kept in (\n"
        '            ("claude-opus-5", True), ("claude-sonnet-5", True),\n'
        '            ("claude-opus-4-8", True), ("claude-zeta-9", True),\n'
        '            ("claude-opus-5-5", False), ("claude-fable-5-1", False),\n'
        '            ("claude-opus-5-5[1m]", False), ("claude-opus-5-5-next", True),\n'
        "        ):\n"
        "            with self.subTest(model=model):\n"
        "                t = _FakeTransport()\n"
        "                self._make_adapter(t).call(\n"
        '                    messages=[{"role": "user", "content": "hi"}],\n'
        "                    model=model,\n"
        '                    thinking={"type": "disabled"},\n'
        "                )\n"
        "                self.assertIsNotNone(t.captured_body)\n"
        "                if kept:\n"
        "                    self.assertEqual(\n"
        '                        t.captured_body.get("thinking"), {"type": "disabled"}\n'
        "                    )\n"
        "                else:\n"
        '                    self.assertNotIn("thinking", t.captured_body)\n'
        "\n"
        "    def test_caller_adaptive_with_budget_tokens_stripped_on_adaptive_only(self):\n",
        1,
    ),
    (
        ".claude/hooks/tests/test_model_routing.py",
        "        # claude-opus-4-5 is outside _ADAPTIVE_ONLY_MODELS → legacy shape.\n",
        "        # claude-opus-4-5 is in the closed _LEGACY_BUDGET_MODELS → legacy shape.\n",
        1,
    ),
    # ============================================ validate-governance.sh
    (
        VALIDATE_REL,
        "    # haiku-4-5, opus-5, sonnet-5, fable-5-1 — ADR-149 Amendment 2,\n"
        "    # S338) plus the dated haiku id that agent\n",
        "    # haiku-4-5, opus-5, sonnet-5, fable-5-1 — ADR-149 Amendment 2,\n"
        "    # S338 — and opus-5-5 — ADR-149 Amendment 3, S357) plus the dated\n"
        "    # haiku id that agent\n",
        1,
    ),
    (
        VALIDATE_REL,
        '        claude-fable-5|claude-opus-4-8|claude-sonnet-4-6|claude-haiku-4-5|claude-haiku-4-5-20251001|claude-opus-5|claude-sonnet-5|claude-fable-5-1|"")\n',
        '        claude-fable-5|claude-opus-4-8|claude-sonnet-4-6|claude-haiku-4-5|claude-haiku-4-5-20251001|claude-opus-5|claude-sonnet-5|claude-fable-5-1|claude-opus-5-5|"")\n',
        1,
    ),
    (
        VALIDATE_REL,
        'claude-opus-5, claude-sonnet-5, claude-fable-5-1, or empty (inherit)"\n',
        'claude-opus-5, claude-sonnet-5, claude-fable-5-1, claude-opus-5-5, or empty (inherit)"\n',
        1,
    ),
    # ============================================ tier_policy_cli mirror
    (
        ".claude/scripts/tier_policy_cli/_types.py",
        "'claude-sonnet-5', 'claude-fable-5-1']\"\n",
        "'claude-sonnet-5', 'claude-fable-5-1', 'claude-opus-5-5']\"\n",
        1,
    ),
    (
        ".claude/scripts/tier_policy_cli/_types.py",
        "# only (not a VETO-floor member); additive.\n",
        "# only (not a VETO-floor member); additive.\n"
        "# ADR-149 Amendment 3 (S357): claude-opus-5-5 appended — working set AND\n"
        "# VETO floor; additive.\n",
        1,
    ),
    (
        ".claude/scripts/tier_policy_cli/_types.py",
        '    "claude-fable-5-1",\n'
        ")\n",
        '    "claude-fable-5-1",\n'
        '    "claude-opus-5-5",\n'
        ")\n",
        1,
    ),
    (
        ".claude/scripts/tier_policy_cli/tests/test_types.py",
        "        # ADR-149 Amendment 2 (S338): fable-5-1 added — 7 legal IDs.\n"
        "        self.assertEqual(len(VALID_MODEL_IDS), 7)\n",
        "        # ADR-149 Amendment 2 (S338): fable-5-1 added — 7 legal IDs.\n"
        "        # ADR-149 Amendment 3 (S357): opus-5-5 added — 8 legal IDs.\n"
        "        self.assertEqual(len(VALID_MODEL_IDS), 8)\n",
        1,
    ),
    (
        ".claude/scripts/tier_policy_cli/tests/test_types.py",
        '        self.assertIn("claude-fable-5-1", VALID_MODEL_IDS)\n'
        "\n"
        "    def test_retired_generation_not_valid(self):\n",
        '        self.assertIn("claude-fable-5-1", VALID_MODEL_IDS)\n'
        '        self.assertIn("claude-opus-5-5", VALID_MODEL_IDS)\n'
        "\n"
        "    def test_retired_generation_not_valid(self):\n",
        1,
    ),
    # ============================================ learn._tier_rank (SI-8)
    (
        ".claude/scripts/tier_policy_cli/learn.py",
        '        "claude-opus-5": 5,\n'
        '        "claude-opus-5-fast": 5,  # fast mode: same model, premium rate\n'
        '        "claude-fable-5": 6,  # ADR-149 flagship (Mythos-class, above Opus)\n'
        '        "claude-fable-5-1": 7,  # ADR-149 Amendment 2 (S338): Fable 5.1, above Fable 5\n'
        "    }\n",
        '        "claude-opus-5": 5,\n'
        '        "claude-opus-5-fast": 5,  # fast mode: same model, premium rate\n'
        "        # ADR-149 Amendment 3 (S357): Opus 5.5 sits strictly between Opus 5\n"
        "        # and Fable 5 (tier-major ladder, renumbered, never tied: a tie with\n"
        '        # Opus 5 would sign opus-5 -> opus-5-5 as "demote", a tie with\n'
        '        # Fable 5 would sign opus-5-5 -> fable-5 as "demote", and a rank\n'
        '        # above Fable would sign fable-5 -> opus-5-5 as "promote").\n'
        '        "claude-opus-5-5": 6,\n'
        '        "claude-fable-5": 7,  # ADR-149 flagship (Mythos-class, above Opus)\n'
        '        "claude-fable-5-1": 8,  # ADR-149 Amendment 2 (S338): Fable 5.1, above Fable 5\n'
        "    }\n",
        1,
    ),
    (
        ".claude/scripts/tier_policy_cli/tests/test_learn_mutation.py",
        "    def test_kill_direction_promote_vs_demote(self):\n",
        "    def test_kill_opus55_ranks_between_opus5_and_fable5(self):\n"
        '        """ADR-149 Amendment 3 (S357): Opus 5.5 is above Opus 5 and strictly\n'
        "        BELOW Fable 5 — Fable 5 -> Opus 5.5 is a demote (needs a signature),\n"
        '        Opus 5 -> Opus 5.5 a promote."""\n'
        '        self.assertGreater(learn._tier_rank("claude-opus-5-5"),\n'
        '                           learn._tier_rank("claude-opus-5"))\n'
        '        self.assertGreater(learn._tier_rank("claude-fable-5"),\n'
        '                           learn._tier_rank("claude-opus-5-5"))\n'
        "        self.assertEqual(\n"
        '            learn._direction("claude-fable-5", "claude-opus-5-5"), "demote"\n'
        "        )\n"
        "        self.assertEqual(\n"
        '            learn._direction("claude-opus-5", "claude-opus-5-5"), "promote"\n'
        "        )\n"
        "\n"
        "    def test_kill_direction_promote_vs_demote(self):\n",
        1,
    ),
    # ================================= tier_policy_cli owner-sign (rail r1)
    # Rail round 1 (codex, P2, confirmed): cmd_owner_sign labelled the action
    # it signs by the ORDER of VALID_MODEL_IDS — an allowlist in ADR order,
    # not a tier order (claude-fable-5 is index 0) — so fable-5 -> opus-5
    # already signed "promote" before this wave, and appending opus-5-5 made
    # fable-5-1 -> opus-5-5 sign "promote" while learn._direction says
    # "demote". Class cure: ONE authority (learn._direction over
    # learn._tier_rank); an unranked id or the same model on both sides is
    # refused before anything is signed; the signing path is tested.
    (
        ".claude/scripts/tier_policy_cli/cli.py",
        r'''    if args.agent not in CANONICAL_5_AGENTS:
        sys.stderr.write(
            "owner-sign: agent must be one of canonical-5\n"
        )
        return 2
    sigchain_path = (
        Path(args.sigchain) if args.sigchain else DEFAULT_SIGCHAIN_PATH
    )
''',
        r'''    if args.agent not in CANONICAL_5_AGENTS:
        sys.stderr.write(
            "owner-sign: agent must be one of canonical-5\n"
        )
        return 2
    # ADR-149 Amendment 3 (S357): the action this entry signs is the one
    # the learner computes — learn._direction over learn._tier_rank, ONE
    # authority. VALID_MODEL_IDS is an allowlist in ADR order, not a tier
    # order (claude-fable-5 is its first entry): its index signed
    # fable-5 -> opus-5, and fable-5-1 -> opus-5-5, as "promote". An id
    # the ladder does not rank, or the same model on both sides, is
    # refused before anything is signed.
    if (
        learn_mod._tier_rank(args.from_tier) < 0
        or learn_mod._tier_rank(args.to_tier) < 0
    ):
        sys.stderr.write(
            "owner-sign: model ID has no tier rank; aborting\n"
        )
        return 2
    action = learn_mod._direction(args.from_tier, args.to_tier)
    if action not in ("promote", "demote"):
        sys.stderr.write(
            "owner-sign: from_tier and to_tier are the same model; "
            "nothing to sign\n"
        )
        return 2
    sigchain_path = (
        Path(args.sigchain) if args.sigchain else DEFAULT_SIGCHAIN_PATH
    )
''',
        1,
    ),
    (
        ".claude/scripts/tier_policy_cli/cli.py",
        r'''    action = "promote" if (
        VALID_MODEL_IDS.index(args.to_tier)
        > VALID_MODEL_IDS.index(args.from_tier)
    ) else "demote"
    prior_tip = _read_sigchain_tip_length(sigchain_path)
''',
        r'''    prior_tip = _read_sigchain_tip_length(sigchain_path)
''',
        1,
    ),
    (
        ".claude/scripts/tier_policy_cli/tests/test_cli.py",
        "from tier_policy_cli import cli  # noqa: E402\n",
        "from tier_policy_cli import cli  # noqa: E402\n"
        "from tier_policy_cli import learn  # noqa: E402\n"
        "from tier_policy_cli._types import VALID_MODEL_IDS  # noqa: E402\n",
        1,
    ),
    (
        ".claude/scripts/tier_policy_cli/tests/test_cli.py",
        r'''        self.assertNotEqual(rc, 0)
        self.assertIn("git user.email unset", self._stderr.getvalue())


# ---------------------------------------------------------------------
# Group G — rotate-key + sigchain-rotate stubs
''',
        r'''        self.assertNotEqual(rc, 0)
        self.assertIn("git user.email unset", self._stderr.getvalue())


# ---------------------------------------------------------------------
# Group F2 — owner-sign signs the learner's direction (ADR-149 A3)
# ---------------------------------------------------------------------

class _FakeAuditHmac(object):
    """Stand-in for ``_lib/audit_hmac``: no key file, no ``$HOME``."""

    @staticmethod
    def get_or_create_key():
        return b"k" * 32

    @staticmethod
    def compute_entry_hmac(key, prev, entry):
        return bytes(32)

    @staticmethod
    def hex_digest(digest):
        return digest.hex()


class OwnerSignDirectionTests(CliTestBase):
    """ADR-149 Amendment 3 (S357, rail round 1): the action owner-sign
    writes into the sigchain is ``learn._direction``, the ladder the
    learner signs with, never the position of an id in
    ``VALID_MODEL_IDS`` (an allowlist in ADR order whose first entry is
    ``claude-fable-5``)."""

    def setUp(self):
        super().setUp()
        self.owners_file.write_text(
            "owner@example.com\n", encoding="utf-8"
        )
        self.git_calls = []

    def _fake_run(self, cmd, *args, **kwargs):
        self.git_calls.append(list(cmd))
        return mock.Mock(returncode=0, stdout="", stderr="")

    def _sign(self, from_tier, to_tier, sigchain):
        with mock.patch.object(
            cli, "_git_config_email", return_value="owner@example.com"
        ), mock.patch.object(
            cli, "_git_head_sha", return_value="a" * 40
        ), mock.patch.object(
            cli, "_load_audit_hmac_module", return_value=_FakeAuditHmac
        ), mock.patch.object(
            cli.subprocess, "run", side_effect=self._fake_run
        ):
            return cli.main([
                "owner-sign",
                "--agent", "performance-engineer",
                "--from-tier", from_tier,
                "--to-tier", to_tier,
                "--sp-chain-id", "SP-100-12345678",
                "--owners-file", str(self.owners_file),
                "--sigchain", str(sigchain),
                "--skip-commit",
            ])

    @staticmethod
    def _actions(sigchain):
        return [
            json.loads(line)["action"]
            for line in sigchain.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def test_every_valid_model_id_has_a_distinct_tier_rank(self):
        ranks = {m: learn._tier_rank(m) for m in VALID_MODEL_IDS}
        self.assertTrue(all(r >= 0 for r in ranks.values()), ranks)
        self.assertEqual(len(set(ranks.values())), len(ranks), ranks)

    def test_signed_action_is_the_learner_direction_for_every_pair(self):
        pairs = [
            (a, b) for a in VALID_MODEL_IDS for b in VALID_MODEL_IDS
            if a != b
        ]
        self.assertEqual(
            len(pairs), len(VALID_MODEL_IDS) * (len(VALID_MODEL_IDS) - 1)
        )
        for i, (from_tier, to_tier) in enumerate(pairs):
            sigchain = self.tmp / "sigchain-{i}".format(i=i)
            with self.subTest(from_tier=from_tier, to_tier=to_tier):
                rc = self._sign(from_tier, to_tier, sigchain)
                self.assertEqual(rc, 0, self._stderr.getvalue())
                self.assertEqual(
                    self._actions(sigchain),
                    [learn._direction(from_tier, to_tier)],
                )

    def test_fable_to_opus_signs_demote_and_back_promote(self):
        # Literal expectations, independent of the learner's table: the
        # new pair and its reverse, and the pair that already signed
        # inverted before Opus 5.5 existed (claude-fable-5 is index 0).
        cases = (
            ("claude-fable-5-1", "claude-opus-5-5", "demote"),
            ("claude-opus-5-5", "claude-fable-5-1", "promote"),
            ("claude-fable-5", "claude-opus-5-5", "demote"),
            ("claude-opus-5", "claude-opus-5-5", "promote"),
            ("claude-fable-5", "claude-opus-5", "demote"),
        )
        for i, (from_tier, to_tier, expected) in enumerate(cases):
            sigchain = self.tmp / "sigchain-pin-{i}".format(i=i)
            with self.subTest(from_tier=from_tier, to_tier=to_tier):
                rc = self._sign(from_tier, to_tier, sigchain)
                self.assertEqual(rc, 0, self._stderr.getvalue())
                self.assertEqual(self._actions(sigchain), [expected])

    def test_same_model_on_both_sides_is_refused_unsigned(self):
        rc = self._sign(
            "claude-opus-5-5", "claude-opus-5-5", self.sigchain_path
        )
        self.assertEqual(rc, 2)
        self.assertIn("same model", self._stderr.getvalue())
        self.assertFalse(self.sigchain_path.exists())
        self.assertEqual(self.git_calls, [])

    def test_model_id_without_a_tier_rank_is_refused_unsigned(self):
        with mock.patch.object(
            cli.learn_mod, "_tier_rank", return_value=-1
        ):
            rc = self._sign(
                "claude-opus-5", "claude-opus-5-5", self.sigchain_path
            )
        self.assertEqual(rc, 2)
        self.assertIn("no tier rank", self._stderr.getvalue())
        self.assertFalse(self.sigchain_path.exists())
        self.assertEqual(self.git_calls, [])


# ---------------------------------------------------------------------
# Group G — rotate-key + sigchain-rotate stubs
''',
        1,
    ),
    # ================================================= smoke-install.sh
    # Fix round r13 (vX) put a PATH-dir FAKE claude here; fix round r15 (rail
    # round 2) replaces it with the harness-claude-stub block every harness
    # that names an installer carries (the EDITS += at the end of this table).
    # The LAND lints every touched .sh with `shellcheck -S warning` (V1b):
    # the one warning this file already carried at the base is waived at
    # its line, with the reason; the check itself is unchanged.
    (
        "scripts/tests/smoke-install.sh",
        r'''user_extra="$(ls -A "$UTARGET" | grep -v -E '^[.]claude$|^[.]git$' || true)"
''',
        r'''# shellcheck disable=SC2010  # pre-existing; a name ls prints oddly still leaves a non-empty line, so the check below still fails
user_extra="$(ls -A "$UTARGET" | grep -v -E '^[.]claude$|^[.]git$' || true)"
''',
        1,
    ),
    # ============================================ smoke-install-parity.sh
    # Fix round r13 (vX) put a PATH-dir FAKE claude here; fix round r15 (rail
    # round 2) replaces it with the harness-claude-stub block (the EDITS +=
    # at the end of this table).
    (
        "scripts/local/smoke-install-parity.sh",
        "#      default `model` == claude-opus-5 (PLAN-163 T1.1 pin; R2-B3): a\n",
        "#      default `model` == claude-opus-5-5 (PLAN-163 T1.1 pin, moved by\n"
        "#      ADR-149 Amendment 3; R2-B3): a\n",
        1,
    ),
    (
        "scripts/local/smoke-install-parity.sh",
        "# ADR-149 Amendment 2 (S338): claude-fable-5-1 appended (working set only).\n"
        'ALLOWED_MODELS="claude-opus-4-8 claude-fable-5 claude-sonnet-4-6 claude-haiku-4-5-20251001 claude-opus-5 claude-sonnet-5 claude-fable-5-1 haiku sonnet opus inherit"\n',
        "# ADR-149 Amendment 2 (S338): claude-fable-5-1 appended (working set only).\n"
        "# ADR-149 Amendment 3 (S357): claude-opus-5-5 appended (working set + floor).\n"
        'ALLOWED_MODELS="claude-opus-4-8 claude-fable-5 claude-sonnet-4-6 claude-haiku-4-5-20251001 claude-opus-5 claude-sonnet-5 claude-fable-5-1 claude-opus-5-5 haiku sonnet opus inherit"\n',
        1,
    ),
    (
        "scripts/local/smoke-install-parity.sh",
        '    "claude-fable-5-1",  # ADR-149 Amendment 2 (S338) — appended at the end\n'
        "]\n",
        '    "claude-fable-5-1",  # ADR-149 Amendment 2 (S338) — appended at the end\n'
        '    "claude-opus-5-5",  # ADR-149 Amendment 3 (S357) — appended at the end\n'
        "]\n",
        1,
    ),
    (
        "scripts/local/smoke-install-parity.sh",
        "# arrays above, so it is asserted independently (R2-B3).\n"
        'EXPECTED_MODEL = "claude-opus-5"\n',
        "# arrays above, so it is asserted independently (R2-B3). ADR-149\n"
        "# Amendment 3 (S357) moved the pin to claude-opus-5-5.\n"
        'EXPECTED_MODEL = "claude-opus-5-5"\n'
        "# ADR-149 Amendment 3 (S357; Owner OQ-1 and OQ-7): a NEW install ships the\n"
        "# top-level effortLevel; no installed settings file carries ultracode\n"
        "# (OQ-6: it lives only in an operator local overlay).\n"
        'EXPECTED_EFFORT = "xhigh"\n',
        1,
    ),
    (
        "scripts/local/smoke-install-parity.sh",
        '        "installed availableModels %s\\n" % (model, avail)\n'
        "    )\n"
        "    rc = 1\n",
        '        "installed availableModels %s\\n" % (model, avail)\n'
        "    )\n"
        "    rc = 1\n"
        'effort = data.get("effortLevel")\n'
        "if effort != EXPECTED_EFFORT:\n"
        "    sys.stderr.write(\n"
        '        "OFFENDER(models): installed effortLevel != %r (actual: %r)\\n"\n'
        "        % (EXPECTED_EFFORT, effort)\n"
        "    )\n"
        "    rc = 1\n"
        'if "ultracode" in data:\n'
        '    sys.stderr.write("OFFENDER(models): installed settings carries ultracode\\n")\n'
        "    rc = 1\n",
        1,
    ),
    (
        "scripts/local/smoke-install-parity.sh",
        'echo "==> [6/6] installed model pin + availableModels order + fallbackModel assert"\n',
        'echo "==> [6/6] installed model pin + availableModels order + fallbackModel + effortLevel assert"\n',
        1,
    ),
    (
        "scripts/local/smoke-install-parity.sh",
        'echo "    model/availableModels/fallbackModel assert done"\n',
        'echo "    model/availableModels/fallbackModel/effortLevel assert done"\n',
        1,
    ),
    # ============================================ audit_log role map (SI-5)
    (
        ".claude/hooks/audit_log.py",
        "    # Mitigated rail — general-purpose dispatch inherits CEO model.\n"
        "    # Default-CEO is Opus-tier unless CEO_MODEL_DOWNSHIFT is honored.\n"
        '    "general-purpose": "claude-opus-5",\n',
        "    # Mitigated rail — general-purpose dispatch inherits CEO model.\n"
        "    # Default-CEO is Opus-tier unless CEO_MODEL_DOWNSHIFT is honored.\n"
        "    # ADR-149 Amendment 3 (S357): follows the session-default pin, now\n"
        "    # claude-opus-5-5. A POLICY value, not an observation: when the Task\n"
        "    # response carries no model (the common case, see _extract_model) the\n"
        "    # audit log records this row even if a per-call model or alias served\n"
        "    # the spawn.\n"
        '    "general-purpose": "claude-opus-5-5",\n',
        1,
    ),
    # ============================================ parity / mirror tests
    (
        ".claude/scripts/tests/test_generate_available_models.py",
        '    "claude-fable-5-1",  # ADR-149 Amendment 2, S338\n'
        "]\n",
        '    "claude-fable-5-1",  # ADR-149 Amendment 2, S338\n'
        '    "claude-opus-5-5",  # ADR-149 Amendment 3, S357\n'
        "]\n",
        1,
    ),
    (
        ".claude/scripts/tests/test_generate_available_models.py",
        '    "claude-fable-5-1",   # ADR-149 Amendment 2, S338\n'
        ")\n",
        '    "claude-fable-5-1",   # ADR-149 Amendment 2, S338\n'
        '    "claude-opus-5-5",    # ADR-149 Amendment 3, S357\n'
        ")\n",
        1,
    ),
    (
        ".claude/hooks/tests/test_adr149_validator_parity.py",
        '        self.assertEqual(ws[-1], "claude-fable-5-1", "A2 append must be LAST")\n'
        "        self.assertNotIn(RETIRED_ID, ws)\n",
        "        self.assertIn(\n"
        '            "claude-opus-5-5", ws,\n'
        '            "ADR-149 Amendment 3 (S357) id missing from the working set",\n'
        "        )\n"
        "        self.assertEqual(\n"
        '            ws[-2:], ["claude-fable-5-1", "claude-opus-5-5"],\n'
        '            "the A2 then A3 appends must be the LAST two, in that order",\n'
        "        )\n"
        "        self.assertNotIn(RETIRED_ID, ws)\n",
        1,
    ),
    (
        ".claude/hooks/tests/test_adr149_validator_parity.py",
        "    def test_fallback_chain_inside_floor(self) -> None:\n",
        "    def test_floor_carries_opus55(self) -> None:\n"
        '        """ADR-149 Amendment 3 (S357): Opus 5.5 joins the VETO floor."""\n'
        '        self.assertIn("claude-opus-5-5", _adr_floor())\n'
        "\n"
        "    def test_fallback_chain_inside_floor(self) -> None:\n",
        1,
    ),
    (
        ".claude/hooks/tests/test_template_dogfood_parity.py",
        '    EXPECTED_PIN = "claude-opus-5"\n',
        '    EXPECTED_PIN = "claude-opus-5-5"  # ADR-149 Amendment 3 (S357)\n',
        2,
    ),
    # A-R2CL-04 (fix round r11): Claude Code does not reject a pin outside
    # the allowlist — it replaces it at startup with the default model and a
    # warning (model-config page, "Restrict model selection", read
    # 2026-09-23); enforceAvailableModels only constrains the Default option.
    (
        ".claude/hooks/tests/test_template_dogfood_parity.py",
        "    default is an allowed model). The pinned value MUST remain a member of\n"
        "    availableModels or enforceAvailableModels rejects it.\n",
        "    default is an allowed model). The pinned value MUST remain a member of\n"
        "    availableModels: Claude Code replaces a pin its allowlist does not\n"
        "    admit with the default model at startup (with a warning).\n",
        1,
    ),
    (
        ".claude/hooks/tests/test_template_dogfood_parity.py",
        '                "availableModels — enforceAvailableModels would reject it. "\n',
        '                "availableModels — Claude Code replaces a pin its allowlist "\n'
        '                "does not admit with the default model at startup. "\n',
        1,
    ),
    (
        ".claude/hooks/tests/test_template_dogfood_parity.py",
        "            \"'model' to claude-opus-5 (ADR-181 T1.1 contingency)\",\n",
        "            \"'model' to EXPECTED_PIN (ADR-181 T1.1; moved by ADR-149 \"\n"
        '            "Amendment 3)",\n',
        1,
    ),
    (
        ".claude/hooks/tests/test_template_dogfood_parity.py",
        "            \"'model' to claude-opus-5 (adopters inherit the pin)\",\n",
        "            \"'model' to EXPECTED_PIN (adopters inherit the pin)\",\n",
        1,
    ),
    (
        ".claude/hooks/tests/test_template_dogfood_parity.py",
        '            "to claude-opus-5 so a fresh `install --ceremony user` does not "\n',
        '            "to EXPECTED_PIN so a fresh `install --ceremony user` does not "\n',
        1,
    ),
    (
        ".claude/hooks/tests/test_template_dogfood_parity.py",
        "            \"(the two mirrors must carry an identical 'model' pin)\",\n"
        "        )\n",
        "            \"(the two mirrors must carry an identical 'model' pin)\",\n"
        "        )\n"
        "\n"
        "    def test_pin_is_a_veto_floor_member_in_both_mirrors(self) -> None:\n"
        '        """ADR-149 Amendment 3 (S357): a mitigated spawn (subagent_type\n'
        "        general-purpose) or a Workflow agent that is passed no model runs\n"
        "        on the main conversation model (Claude Code sub-agents page), and\n"
        "        the spawn gate never sees it. Both mirrors set\n"
        "        CLAUDE_CODE_SUBAGENT_MODEL=inherit, which is the same as unset, so\n"
        "        no env default replaces that model; the session pin itself\n"
        '        therefore has to be a VETO-floor member."""\n'
        "        from _lib.agent_frontmatter import VETO_FLOOR_ALLOWED\n"
        "        for path in (DOGFOOD_SETTINGS, TEMPLATE_SETTINGS):\n"
        '            data = json.loads(path.read_text(encoding="utf-8"))\n'
        "            self.assertEqual(\n"
        '                (data.get("env") or {}).get("CLAUDE_CODE_SUBAGENT_MODEL"),\n'
        '                "inherit",\n'
        '                f"{path.name}: the premise changed (subagents no longer "\n'
        '                "inherit the session model) — revisit this test",\n'
        "            )\n"
        "            self.assertIn(\n"
        '                data.get("model"), VETO_FLOOR_ALLOWED,\n'
        '                f"{path.name}: the session pin is not a VETO_FLOOR_ALLOWED "\n'
        '                "member (ADR-149 Amendment 3 A3.3)",\n'
        "            )\n",
        1,
    ),
    (
        ".claude/hooks/tests/test_template_dogfood_parity.py",
        "\n"
        "\n"
        'if __name__ == "__main__":\n'
        "    unittest.main()\n",
        "\n"
        "    def test_user_template_agrees_with_base_effort_level(self) -> None:\n"
        '        """ADR-149 Amendment 3 (S357, Owner OQ-1): both adopter-facing\n'
        '        templates carry the same top-level effortLevel."""\n'
        '        user = json.loads(self.USER_TEMPLATE.read_text(encoding="utf-8"))\n'
        '        base = json.loads(TEMPLATE_SETTINGS.read_text(encoding="utf-8"))\n'
        '        self.assertIn("effortLevel", base)\n'
        "        self.assertEqual(\n"
        '            user.get("effortLevel"), base.get("effortLevel"),\n'
        '            "effortLevel drifted between the user and the base template",\n'
        "        )\n"
        "\n"
        "    def test_no_committed_settings_file_carries_ultracode(self) -> None:\n"
        '        """ADR-149 Amendment 3 (S357, Owner OQ-6 «Só no override local»):\n'
        "        ultracode belongs to an operator's local overlay; the dogfood\n"
        '        settings and both adopter templates never carry the key."""\n'
        "        for path in (DOGFOOD_SETTINGS, TEMPLATE_SETTINGS, self.USER_TEMPLATE):\n"
        '            data = json.loads(path.read_text(encoding="utf-8"))\n'
        '            self.assertNotIn("ultracode", data, f"{path.name} carries ultracode")\n'
        "\n"
        "\n"
        'if __name__ == "__main__":\n'
        "    unittest.main()\n",
        1,
    ),
    # ======== test_upgrade_settings_migration — test isolation (fix round
    # r13, vX): every spawn of install.sh / upgrade.sh in this module reads a
    # FAKE claude at the floor first on PATH, never the host CLI.
    (
        ".claude/scripts/tests/test_upgrade_settings_migration.py",
        "import json\n"
        "import os\n"
        "import shutil\n"
        "import subprocess\n"
        "import sys\n"
        "import tempfile\n"
        "import unittest\n",
        "import atexit\n"
        "import json\n"
        "import os\n"
        "import shutil\n"
        "import subprocess\n"
        "import sys\n"
        "import tempfile\n"
        "import time\n"
        "import unittest\n",
        1,
    ),
    (
        ".claude/scripts/tests/test_upgrade_settings_migration.py",
        "            [\"bash\", str(UPGRADE_SH), \"--print-settings-baselines\"],\n"
        "            capture_output=True, text=True, timeout=60,\n"
        "        )\n",
        "            [\"bash\", str(UPGRADE_SH), \"--print-settings-baselines\"],\n"
        "            capture_output=True, text=True, timeout=60,\n"
        "            env=_clean_env(None),\n"
        "        )\n",
        1,
    ),
    (
        ".claude/scripts/tests/test_upgrade_settings_migration.py",
        r'''def _clean_env(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    env = os.environ.copy()
    # The T3.4 gate env override must not leak in from the outer session.
    env.pop("CEO_T34_NEW_EVENT_REGISTRATIONS", None)
    if extra:
        env.update(extra)
    return env
''',
        r'''#: ADR-149 Amendment 3 (fix round r13, vX): the directory of the FAKE
#: claude that every spawn of this module finds first on PATH (created once
#: per process, removed at exit).
_CLAUDE_STUB_DIR: Optional[str] = None


def _supported_claude_dir() -> str:
    """A directory holding only a FAKE ``claude`` that reports the Claude
    Code floor of scripts/upgrade.sh as its version. install.sh and
    upgrade.sh read the claude found on PATH (ADR-149 A3.2 item 11); a test
    must never read the host CLI - one below the floor would turn every
    spawn into exit 6, and any host version would decide the output. Under
    pytest the suite isolation layer (_lib/test_isolation.py, Axis 4) puts
    one first on PATH too; this module keeps its own so its spawns hold the
    floor under ``python -m unittest`` as well, where no conftest runs."""
    global _CLAUDE_STUB_DIR
    if _CLAUDE_STUB_DIR is None or not os.path.isfile(
            os.path.join(_CLAUDE_STUB_DIR, "claude")):
        floor = [ln.split("=", 1)[1].strip('"')
                 for ln in UPGRADE_SH.read_text(encoding="utf-8").splitlines()
                 if ln.startswith("CC_FLOOR_VERSION=")]
        if len(floor) != 1:
            raise AssertionError("scripts/upgrade.sh must carry ONE "
                                 "CC_FLOOR_VERSION line (found %d)" % len(floor))
        stub_dir = tempfile.mkdtemp(prefix="t54-claude-stub-")
        atexit.register(shutil.rmtree, stub_dir, True)
        exe = os.path.join(stub_dir, "claude")
        with open(exe, "w", encoding="utf-8") as fh:
            fh.write("#!/bin/sh\necho '%s (Claude Code)'\n" % floor[0])
        os.chmod(exe, 0o755)
        _CLAUDE_STUB_DIR = stub_dir
    return _CLAUDE_STUB_DIR


def _clean_env(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    env = os.environ.copy()
    # The T3.4 gate env override must not leak in from the outer session.
    env.pop("CEO_T34_NEW_EVENT_REGISTRATIONS", None)
    # ADR-149 Amendment 3 (fix round r13, vX): a FAKE claude at the floor
    # first on PATH, never the host CLI; a test that needs another CLI
    # (TestClaudeCodeFloor) passes its own PATH through ``extra``.
    env["PATH"] = _supported_claude_dir() + os.pathsep + env.get("PATH", "")
    if extra:
        env.update(extra)
    return env
''',
        1,
    ),
    # ============================ test_upgrade_settings_migration (RED-first)
    (
        ".claude/scripts/tests/test_upgrade_settings_migration.py",
        "    def test_new_baseline_appends_fable51_last(self) -> None:\n"
        '        new = baselines()["availableModels"]["new"]\n'
        '        self.assertEqual(new[-1], "claude-fable-5-1")\n'
        "        self.assertEqual(new[:-1], self.SHIPPED_V12_V13_AVAILABLE,\n"
        '                         "order is normative: append at the END only")\n',
        "    #: The availableModels array every release from v1.4.0-rc.1 to the\n"
        "    #: last one before ADR-149 Amendment 3 (S357) shipped (frozen literal,\n"
        "    #: measured S357 with `git show <tag>:templates/settings/\n"
        "    #: settings.base.json`) — superseded by that amendment.\n"
        '    SHIPPED_V14_AVAILABLE = SHIPPED_V12_V13_AVAILABLE + ["claude-fable-5-1"]\n'
        "\n"
        "    def test_new_baseline_appends_fable51_then_opus55_last(self) -> None:\n"
        '        new = baselines()["availableModels"]["new"]\n'
        '        self.assertEqual(new[-1], "claude-opus-5-5")\n'
        "        self.assertEqual(new[:-1], self.SHIPPED_V14_AVAILABLE,\n"
        '                         "order is normative: append at the END only")\n'
        "\n"
        "    def test_shipped_7_id_array_is_declared_superseded(self) -> None:\n"
        '        spec = baselines()["availableModels"]\n'
        '        self.assertIn(self.SHIPPED_V14_AVAILABLE, spec.get("superseded", []))\n'
        '        self.assertNotEqual(self.SHIPPED_V14_AVAILABLE, spec["new"])\n',
        1,
    ),
    (
        ".claude/scripts/tests/test_upgrade_settings_migration.py",
        "    _PIN_NOT_APPLIED = (\n"
        '        "WARNING: model pin NOT applied: adopter availableModels excludes "\n'
        '        "claude-opus-5 (session default left to harness/adopter)"\n'
        "    )\n"
        "\n"
        "    def _pin(self) -> str:\n"
        '        return baselines()["model"]["new"]\n',
        "    def _pin(self) -> str:\n"
        '        return baselines()["model"]["new"]\n'
        "\n"
        "    def _pin_not_applied(self) -> str:\n"
        '        """ADR-149 Amendment 3 (S357): the generic scalar branch names the\n'
        '        key, the gating array and the FRAMEWORK value (never the adopter\n'
        '        value) — derived from the artifact, not a literal pin."""\n'
        '        return ("WARNING: model NOT migrated: " + self._pin()\n'
        '                + " is not an exact entry of the adopter availableModels"\n'
        '                " (the harness may still admit it by prefix) - model"\n'
        '                " left untouched")\n',
        1,
    ),
    (
        ".claude/scripts/tests/test_upgrade_settings_migration.py",
        "self._PIN_NOT_APPLIED",
        "self._pin_not_applied()",
        3,
    ),
    (
        ".claude/scripts/tests/test_upgrade_settings_migration.py",
        "class TestMixedStateAndIdempotency(_MigrationHarness):\n",
        "class TestScalarLeafGenericBranch(_MigrationHarness):\n"
        '    """ADR-149 Amendment 3 (S357) — ONE generic branch for top-level SCALAR\n'
        "    leaves, with the ``superseded`` semantics the ARRAY leaves have had\n"
        "    since Amendment 2 (second occurrence of a SHIPPED baseline read as\n"
        "    ADOPTER-CUSTOMIZED: cure the class, not the Opus case).\n"
        "\n"
        "    RED on 19771fa1: the scalar ``model`` leaf had no ``superseded`` list,\n"
        "    so an adopter still on the pin that every release from v1.2.0-rc.1 to\n"
        "    the last one before Amendment 3 shipped kept it behind a WARNING — or,\n"
        "    while that pin was still the table value, never moved at all.\n"
        '    """\n'
        "\n"
        "    #: The session-default pin every release from v1.2.0-rc.1 to the last\n"
        "    #: one before Amendment 3 SHIPPED (frozen literal, measured S357 with\n"
        "    #: `git show <tag>:templates/settings/settings.base.json`).\n"
        '    SHIPPED_PIN_BEFORE_A3 = "claude-opus-5"\n'
        "    #: The availableModels array every release from v1.4.0-rc.1 to the\n"
        "    #: last one before Amendment 3 shipped.\n"
        "    SHIPPED_V14_AVAILABLE = [\n"
        '        "claude-opus-4-8", "claude-fable-5", "claude-sonnet-4-6",\n'
        '        "claude-haiku-4-5", "claude-opus-5", "claude-sonnet-5",\n'
        '        "claude-fable-5-1",\n'
        "    ]\n"
        "\n"
        "    @staticmethod\n"
        "    def _scalar_keys() -> List[str]:\n"
        "        return [k for k, v in baselines().items()\n"
        '                if "." not in k and isinstance(v, dict)\n'
        '                and isinstance(v.get("new"), str)]\n'
        "\n"
        "    def test_shipped_pin_is_declared_superseded(self) -> None:\n"
        '        spec = baselines()["model"]\n'
        '        self.assertIn(self.SHIPPED_PIN_BEFORE_A3, spec.get("superseded", []))\n'
        '        self.assertNotEqual(self.SHIPPED_PIN_BEFORE_A3, spec["new"])\n'
        "\n"
        "    def test_shipped_pin_migrates_to_new_pin(self) -> None:\n"
        '        self.seed({"model": self.SHIPPED_PIN_BEFORE_A3,\n'
        '                   "availableModels": list(baselines()["availableModels"]["new"])})\n'
        "        proc = self.run_migration()\n"
        '        self.assertEqual(self.read_settings()["model"], baselines()["model"]["new"])\n'
        '        self.assertNotEqual(self.read_settings()["model"], self.SHIPPED_PIN_BEFORE_A3)\n'
        "        self.assertIn(\n"
        '            "MIGRATE (matched SUPERSEDED shipped baseline -> new baseline): model",\n'
        "            proc.stdout,\n"
        "        )\n"
        '        self.assertNotIn("WARNING: model is ADOPTER-CUSTOMIZED", proc.stderr)\n'
        "\n"
        "    def test_v14_adopter_as_shipped_gets_the_8th_id_and_the_new_pin(self) -> None:\n"
        '        self.seed({"availableModels": list(self.SHIPPED_V14_AVAILABLE),\n'
        '                   "fallbackModel": list(baselines()["fallbackModel"]["new"]),\n'
        '                   "model": self.SHIPPED_PIN_BEFORE_A3})\n'
        "        self.run_migration()\n"
        "        data = self.read_settings()\n"
        '        self.assertEqual(data["availableModels"], baselines()["availableModels"]["new"])\n'
        '        self.assertNotEqual(data["availableModels"], self.SHIPPED_V14_AVAILABLE)\n'
        '        self.assertEqual(data["model"], baselines()["model"]["new"])\n'
        '        self.assertIn(data["model"], data["availableModels"])\n'
        '        self.assertEqual(data["fallbackModel"], baselines()["fallbackModel"]["new"])\n'
        "\n"
        "    def test_superseded_pin_withheld_when_allowlist_excludes_new_pin(self) -> None:\n"
        '        custom = list(baselines()["availableModels"]["old"]) + ["adopter-only-model"]\n'
        '        self.assertNotIn(baselines()["model"]["new"], custom)\n'
        '        self.seed({"model": self.SHIPPED_PIN_BEFORE_A3, "availableModels": custom})\n'
        "        proc = self.run_migration()\n"
        '        self.assertEqual(self.read_settings()["model"], self.SHIPPED_PIN_BEFORE_A3)\n'
        "        self.assertIn(\n"
        '            "WARNING: model NOT migrated: " + baselines()["model"]["new"]\n'
        '            + " is not an exact entry of the adopter availableModels"\n'
        '            " (the harness may still admit it by prefix) - model left"\n'
        '            " untouched",\n'
        "            proc.stderr,\n"
        "        )\n"
        "\n"
        "    def test_every_scalar_superseded_value_migrates(self) -> None:\n"
        "        exercised = 0\n"
        "        for key in self._scalar_keys():\n"
        '            for sup in baselines()[key].get("superseded", []):\n'
        "                exercised += 1\n"
        "                with self.subTest(key=key, superseded=sup):\n"
        "                    self.setUp()\n"
        '                    self.seed({key: sup, "availableModels":\n'
        '                               list(baselines()["availableModels"]["new"])})\n'
        "                    proc = self.run_migration()\n"
        "                    self.assertEqual(self.read_settings()[key],\n"
        '                                     baselines()[key]["new"])\n'
        "                    self.assertIn(\n"
        '                        "MIGRATE (matched SUPERSEDED shipped baseline -> "\n'
        '                        "new baseline): " + key,\n'
        "                        proc.stdout,\n"
        "                    )\n"
        '        self.assertGreater(exercised, 0, "vacuous: no scalar leaf declares superseded")\n'
        "\n"
        "    def test_second_run_after_scalar_migration_is_noop(self) -> None:\n"
        '        self.seed({"model": self.SHIPPED_PIN_BEFORE_A3,\n'
        '                   "availableModels": list(baselines()["availableModels"]["new"])})\n'
        "        self.run_migration()\n"
        "        first = self.settings_path.read_bytes()\n"
        "        proc = self.run_migration()\n"
        "        self.assertEqual(self.settings_path.read_bytes(), first)\n"
        '        self.assertIn("OK (already at new baseline): model", proc.stdout)\n'
        "\n"
        "\n"
        "class TestEffortLevelLeaf(_MigrationHarness):\n"
        '    """ADR-149 Amendment 3 (S357; Owner OQ-1 «xhigh», narrowed by OQ-7\n'
        "    «Instalação nova + opt-in») — ``effortLevel`` is an OPT-IN leaf of the\n"
        "    T5.4 table: a new install gets it from the template; an EXISTING\n"
        "    install gets it only under ``--adopt-setting effortLevel``, and an\n"
        "    adopter value is never overwritten. The H8 settings-merge carries\n"
        "    only hooks and env, so the table is the one route. RED on 19771fa1:\n"
        "    the table had no such leaf and upgrade.sh had no such flag.\n"
        '    """\n'
        "\n"
        '    _FLAG = ["--adopt-setting", "effortLevel"]\n'
        '    _OPT_IN_WARN = "WARNING: effortLevel NOT written (opt-in leaf)"\n'
        '    _SET = "SET (absent [== old baseline] -> new baseline): effortLevel"\n'
        "\n"
        "    def _spec(self) -> Dict:\n"
        '        return baselines()["effortLevel"]\n'
        "\n"
        "    def test_leaf_is_declared_opt_in_and_matches_the_template(self) -> None:\n"
        "        spec = self._spec()\n"
        '        self.assertIsNone(spec["old"], "absence is the old baseline")\n'
        '        self.assertIs(spec.get("opt_in"), True)\n'
        '        self.assertTrue(str(spec.get("cost_note", "")).strip())\n'
        '        tpl = json.loads(TEMPLATE_SETTINGS.read_text(encoding="utf-8"))\n'
        '        self.assertEqual(tpl["effortLevel"], spec["new"])\n'
        "\n"
        "    def test_absent_key_is_not_written_without_the_flag(self) -> None:\n"
        "        self.seed({})\n"
        "        proc = self.run_migration()\n"
        '        self.assertNotIn("effortLevel", self.read_settings())\n'
        "        self.assertNotIn(self._SET, proc.stdout)\n"
        "        self.assertIn(self._OPT_IN_WARN, proc.stderr)\n"
        '        self.assertIn(self._spec()["cost_note"], proc.stderr)\n'
        '        self.assertIn("--adopt-setting effortLevel", proc.stderr)\n'
        "\n"
        "    def test_absent_key_is_written_with_the_flag(self) -> None:\n"
        "        self.seed({})\n"
        "        proc = self.run_migration(extra_args=self._FLAG)\n"
        '        self.assertEqual(self.read_settings()["effortLevel"], self._spec()["new"])\n'
        "        self.assertIn(self._SET, proc.stdout)\n"
        "        self.assertNotIn(self._OPT_IN_WARN, proc.stderr)\n"
        "\n"
        "    def test_adopter_value_is_never_overwritten(self) -> None:\n"
        '        for custom in ("high", "low"):\n'
        '            self.assertNotEqual(custom, self._spec()["new"])\n'
        "            for extra in (None, self._FLAG):\n"
        "                with self.subTest(custom=custom, flag=extra is not None):\n"
        "                    self.setUp()\n"
        '                    self.seed({"effortLevel": custom})\n'
        "                    proc = self.run_migration(extra_args=extra)\n"
        "                    self.assertEqual(self.read_settings()[\"effortLevel\"], custom)\n"
        "                    # An opt-in leaf has no baseline to drift from: the\n"
        "                    # preserved value is named on stdout, never warned.\n"
        "                    self.assertIn(\n"
        '                        "OK (present - PRESERVED; opt-in leaf): "\n'
        '                        "effortLevel", proc.stdout)\n'
        '                    self.assertNotIn("WARNING: effortLevel", proc.stderr)\n'
        "\n"
        "    def test_already_new_is_noop_without_warn(self) -> None:\n"
        "        for extra in (None, self._FLAG):\n"
        "            with self.subTest(flag=extra is not None):\n"
        "                self.setUp()\n"
        '                self.seed({"effortLevel": self._spec()["new"]})\n'
        "                proc = self.run_migration(extra_args=extra)\n"
        '                self.assertIn("OK (already at new baseline): effortLevel",\n'
        "                              proc.stdout)\n"
        '                self.assertNotIn("WARNING: effortLevel", proc.stderr)\n'
        "\n"
        "    def test_without_the_flag_repeated_runs_never_add_the_key(self) -> None:\n"
        "        self.seed({})\n"
        "        self.run_migration()\n"
        "        first = self.settings_path.read_bytes()\n"
        "        self.run_migration()\n"
        "        self.assertEqual(self.settings_path.read_bytes(), first)\n"
        '        self.assertNotIn("effortLevel", self.read_settings())\n'
        "\n"
        "    def test_flag_delivery_is_idempotent(self) -> None:\n"
        "        self.seed({})\n"
        "        self.run_migration(extra_args=self._FLAG)\n"
        "        first = self.settings_path.read_bytes()\n"
        "        proc = self.run_migration(extra_args=self._FLAG)\n"
        "        self.assertEqual(self.settings_path.read_bytes(), first)\n"
        "        self.assertNotIn(self._SET, proc.stdout)\n"
        '        self.assertIn("OK (already at new baseline): effortLevel", proc.stdout)\n'
        "\n"
        "    def test_dry_run_with_the_flag_previews_without_writing(self) -> None:\n"
        "        self.seed({})\n"
        "        before = self.settings_path.read_bytes()\n"
        "        proc = self.run_migration(dry=True, extra_args=self._FLAG)\n"
        "        self.assertEqual(self.settings_path.read_bytes(), before)\n"
        '        self.assertIn("(dry-run) would " + self._SET, proc.stdout)\n'
        "\n"
        "    def test_flag_for_a_non_opt_in_leaf_is_named_and_ignored(self) -> None:\n"
        '        self.seed({"model": "adopter-model"})\n'
        '        proc = self.run_migration(extra_args=["--adopt-setting", "model"])\n'
        "        self.assertIn(\n"
        '            "WARNING: --adopt-setting model ignored - not an opt-in leaf",\n'
        "            proc.stderr,\n"
        "        )\n"
        '        self.assertEqual(self.read_settings()["model"], "adopter-model")\n'
        '        self.assertIn("WARNING: model is ADOPTER-CUSTOMIZED", proc.stderr)\n'
        "\n"
        "    def test_malformed_flag_value_is_refused_before_any_write(self) -> None:\n"
        "        self.seed({})\n"
        "        before = self.settings_path.read_bytes()\n"
        '        for bad in ("", "effort-level", "effortLevel,model", "1effort"):\n'
        "            with self.subTest(value=bad):\n"
        "                proc = subprocess.run(\n"
        '                    ["bash", str(UPGRADE_SH), str(self.target),\n'
        '                     "--settings-migrate-only", "--no-replay",\n'
        '                     "--no-deprecation-warn", "--adopt-setting", bad],\n'
        "                    capture_output=True, text=True, timeout=120,\n"
        "                    env=_clean_env(None),\n"
        "                )\n"
        "                self.assertEqual(proc.returncode, 2, proc.stderr)\n"
        '                self.assertIn("ERROR: --adopt-setting", proc.stderr)\n'
        "                self.assertEqual(self.settings_path.read_bytes(), before)\n"
        "\n"
        "\n"
        + _UPGRADE_TESTS_A3
        + _UPGRADE_TESTS_OQ8_OQ9
        + _UPGRADE_TESTS_HARNESS_CLI
        + _UPGRADE_TESTS_RERUN
        + "class TestMixedStateAndIdempotency(_MigrationHarness):\n",
        1,
    ),
    (
        ".claude/scripts/tests/test_upgrade_settings_migration.py",
        "    def test_template_model_pin_is_new_baseline(self) -> None:\n"
        '        self.assertEqual(self._template()["model"],\n'
        '                         baselines()["model"]["new"])\n',
        "    def test_template_model_pin_is_new_baseline(self) -> None:\n"
        '        self.assertEqual(self._template()["model"],\n'
        '                         baselines()["model"]["new"])\n'
        "\n"
        "    def test_template_effort_level_is_new_baseline(self) -> None:\n"
        '        self.assertEqual(self._template()["effortLevel"],\n'
        '                         baselines()["effortLevel"]["new"])\n',
        1,
    ),
    # ============================ test_gen_settings_user_template (pin source)
    (
        ".claude/scripts/tests/test_gen_settings_user_template.py",
        '        self.assertEqual(shipped["model"], self.fixture["model"])\n',
        "        # ADR-149 Amendment 3 (S357) moved the session pin on purpose; the\n"
        "        # frozen pre-F copy keeps the pin the releases before it shipped.\n"
        "        # The user profile has no pin source of its own: what must survive\n"
        "        # the derivation is the BASE template pin.\n"
        '        self.assertEqual(shipped["model"], _read(BASE_TEMPLATE)["model"])\n',
        1,
    ),
    # ================================================================ SUPPORT
    (
        "SUPPORT.md",
        "| Claude Code ≥ 2.0 | ✅ Required — needs `Task` tool, slash commands, hooks, native subagents |\n",
        "| Claude Code ≥ " + CLAUDE_CODE_FLOOR + " | ✅ Required from v1.4.2 — needs `Task` tool, slash commands, hooks, native subagents; the shipped settings pin `claude-opus-5-5` (Anthropic documents " + CLAUDE_CODE_FLOOR + " as its minimum) and set `effortLevel: xhigh` (an effort level from 2.1.111). `scripts/install.sh` and `scripts/upgrade.sh` refuse a `claude` on PATH older than " + CLAUDE_CODE_FLOOR + " (exit 6) unless you pass `--allow-old-claude-code`; with no `claude` on PATH (CI, headless), or a version they cannot read (no `(Claude Code)` line with a version, or no answer to `claude --version` within " + CLAUDE_CODE_PROBE_SECONDS + " seconds), they warn and continue; a version with anything after its three numbers (a pre-release) counts as below the floor |\n"
        "| Claude Code 2.0 to 2.1.279 | ⚠️ v1.4.1 and earlier only. A settings value a CLI does not accept can make it skip the whole `.claude/settings.json`, hooks included (Claude Code changelog: invalid legacy enum values did so until 2.1.121). If you install v1.4.2 on one with `--allow-old-claude-code`, edit `.claude/settings.json`: set `model` to an id your CLI knows (for example `claude-opus-5`, the pin v1.4.2 replaced) and delete `effortLevel` |\n",
        1,
    ),
    (
        "SUPPORT.md",
        "`.claude/agents/*.md`. `enforceAvailableModels` is `true`, so a model\n"
        "outside this list cannot be selected. The session default is pinned to\n"
        "`claude-opus-5` (top-level `model` key), and `fallbackModel` is\n"
        "`claude-opus-5`.\n",
        "`.claude/agents/*.md`. `availableModels` limits the models a session\n"
        "can name (`/model`, `--model`, the `model` key, subagent models):\n"
        "Claude Code merges it with the entries of user and local settings, a\n"
        "managed-settings list replaces it, and an entry admits every id that\n"
        "extends it by a `-` segment (Claude Code 2.1.280), so an id that\n"
        "extends a listed one counts as listed. The framework's own\n"
        "`.claude/settings.json` also sets `enforceAvailableModels: true`,\n"
        "which makes the Default model option obey the list as well (Claude\n"
        "Code reads that key from managed settings alone when an organization\n"
        "deploys any); the adopter templates do not set it. The session\n"
        "default is pinned to `claude-opus-5-5` (top-level `model` key) and\n"
        "`fallbackModel` is `claude-opus-5`. A new install ships\n"
        "`effortLevel: xhigh`. On an existing install `scripts/upgrade.sh`\n"
        "writes `xhigh` only with `--adopt-setting effortLevel`; when it moves\n"
        "the shipped pin `claude-opus-5` to `claude-opus-5-5` in a file that\n"
        "sets no level, it writes `effortLevel: high`, the Opus 5 default; it\n"
        "never overwrites a value you set. Without the key, and with no other\n"
        "source setting a level (`CLAUDE_CODE_EFFORT_LEVEL`, `--effort`,\n"
        "`/effort`, a level saved for the model, `ultracode`), Opus 5.5 runs at\n"
        "its default medium effort (Opus 5 defaults to high), a default that an\n"
        "organization default effort replaces when the session runs the\n"
        "organization default model; a `maxEffortLevel` caps any level. In the\n"
        "project file the key applies to every model and outranks a level a\n"
        "developer saved with `/effort` (kept per model under `modelSettings` in\n"
        "user settings); a personal level belongs in\n"
        "`.claude/settings.local.json`, which outranks the project file.\n",
        1,
    ),
    (
        "SUPPORT.md",
        "| Fallback if newer unavailable | ⚠️ Works but not allowlisted — `enforceAvailableModels` blocks selection |\n",
        "| Fallback if newer unavailable | ⚠️ Works but not allowlisted — outside `availableModels`, so a session cannot select them unless a user or local settings file adds them |\n",
        1,
    ),
    (
        "SUPPORT.md",
        "| Opus 5 (`claude-opus-5`) | CEO orchestrator — session default pin + fallback | ✅ Required |\n",
        "| Opus 5.5 (`claude-opus-5-5`) | CEO orchestrator — session default pin (v1.4.2+) | ✅ Required (Claude Code ≥ 2.1.280) |\n"
        "| Opus 5 (`claude-opus-5`) | Fallback (`fallbackModel`) | ✅ Required |\n",
        1,
    ),
    (
        "SUPPORT.md",
        "| Opus 5 1M context (`claude-opus-5[1m]`) | CEO orchestrator (long sessions) | ✅ Supported |\n",
        "| Opus 5.5 / Opus 5 with the `[1m]` tag (`claude-opus-5-5[1m]`, `claude-opus-5[1m]`) | CEO orchestrator, when a session selects the tag (on the Anthropic API, Opus 4.7 and later run with the 1M window without it) | ✅ Supported |\n",
        1,
    ),
    # ============= _lib/test_isolation.py — Axis 4 (fix round r15, rail r2)
    (
        TEST_ISOLATION_REL,
        "log). ``HOME`` is deliberately NOT touched here — it steers user-site package\n"
        "resolution for subprocesses, and the session fixture owns that dance. Guard:\n"
        "``.claude/hooks/tests/test_collect_only_audit_isolation.py``.\n"
        '"""\n',
        "log). ``HOME`` is deliberately NOT touched here — it steers user-site package\n"
        "resolution for subprocesses, and the session fixture owns that dance. Guard:\n"
        "``.claude/hooks/tests/test_collect_only_audit_isolation.py``.\n"
        + _TI_AXIS4_DOC
        + '"""\n',
        1,
    ),
    (
        TEST_ISOLATION_REL,
        "import atexit\n"
        "import os\n"
        "import shutil\n",
        "import atexit\n"
        "import os\n"
        "import re\n"
        "import shutil\n",
        1,
    ),
    (
        TEST_ISOLATION_REL,
        "# --- Idempotent redirect state -------------------------------------------------\n",
        _TI_AXIS4_CODE
        + "# --- Idempotent redirect state -------------------------------------------------\n",
        1,
    ),
    (
        TEST_ISOLATION_REL,
        "    # 3) Snapshot every carrier + the sticky signals + the snapshot var + the\n"
        "    #    tooling vars for exact restore at session end.\n",
        "    # 3) Snapshot every carrier + the sticky signals + the snapshot var + the\n"
        "    #    tooling vars + the Axis 4 CLI carriers for exact restore at session\n"
        "    #    end.\n",
        1,
    ),
    (
        TEST_ISOLATION_REL,
        "        + TOOLING_PRESERVE_VARS\n"
        "        + TOOLING_CLEAR_VARS\n"
        "    )\n",
        "        + TOOLING_PRESERVE_VARS\n"
        "        + TOOLING_CLEAR_VARS\n"
        "        + CC_CLI_CARRIERS\n"
        "    )\n",
        1,
    ),
    (
        TEST_ISOLATION_REL,
        "    if live_log_snapshot is not None:\n"
        "        os.environ[LIVE_LOG_SNAPSHOT_VAR] = live_log_snapshot\n"
        "\n",
        "    if live_log_snapshot is not None:\n"
        "        os.environ[LIVE_LOG_SNAPSHOT_VAR] = live_log_snapshot\n"
        "\n"
        "    # Axis 4 (module docstring): an inherited exported claude FUNCTION would\n"
        "    # shadow every PATH fake, so it goes; then the FAKE claude at the floor\n"
        "    # goes FIRST on PATH, inside the session tree.\n"
        "    for key in CC_FUNCTION_CARRIERS:\n"
        "        os.environ.pop(key, None)\n"
        "    claude_stub = _install_claude_code_stub(tmp_root)\n"
        "    if claude_stub is not None:\n"
        '        inherited_path = os.environ.get("PATH")\n'
        "        # No empty entry when PATH was unset or empty: an empty entry is\n"
        "        # the current directory.\n"
        '        os.environ["PATH"] = claude_stub + (\n'
        '            os.pathsep + inherited_path if inherited_path else "")\n'
        "\n",
        1,
    ),
]

# ======== shell harnesses that name an installer (fix round r15, rail round
# 2 P2): each carries the ONE harness-claude-stub block right after its first
# top-level `set -` line (scripts/tests/smoke-install.sh and
# scripts/local/smoke-install-parity.sh included: their r13 PATH-dir stubs
# gave way to it).
EDITS += [
    (harness, set_line, set_line + _HARNESS_CLAUDE_STUB, 1)
    for harness, set_line in _HARNESS_SET_LINES
]

#: installer-write-safety ratchet — the row delta the REGENERATED baseline
#: may carry (apply-opus55-edits.py regenerates it with the census and
#: refuses any other delta). Rows are written WITHOUT the line number
#: (path:class:verdict:form:fingerprint). Measured S357 fix round r10 on a
#: fresh `git worktree add --detach 19771fa1`: the ONE site whose
#: fingerprint changes is the T5.4 migration call of scripts/upgrade.sh (its
#: python body and its new argv $ADOPT_SETTINGS); no site appears or goes.
RATCHET_DELTA = {
    "removed": [
        "scripts/upgrade.sh:write-candidate:indeterminado:"
        "i-write-candidate-unproven:a6400ee9259029c8",
    ],
    "added": [
        "scripts/upgrade.sh:write-candidate:indeterminado:"
        "i-write-candidate-unproven:a2726d31a5d35b15",
    ],
}

#: The env-name inventory (`.claude/scripts/env-inventory.json`, read by
#: `env-inventory-check.py --check` in the Validate job): the derivator
#: REGISTERS the NAMES the post-edit tree gains or loses and refuses any
#: other delta (R2M-01, fix round r11). The one new name is the Claude Code
#: effort variable that the effortLevel cost note of the T5.4 table names.
ENV_INVENTORY_DELTA = {
    "added": ["CLAUDE_CODE_EFFORT_LEVEL"],
    "removed": [],
}

#: Every path this module touches (the derivator unions it with the pricing half).
PATHS: List[str] = sorted({e[0] for e in EDITS})
