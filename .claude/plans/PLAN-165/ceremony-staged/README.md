# PLAN-165 — ceremony-staged bundle (prerequisites P1 + P2)

Staged inputs for the sentinel ceremony already queued (with RC3-F7 and
GA-F3). **W1 of PLAN-165 is blocked until both patches land.** Patches were
generated against canonical HEAD `91e690aa1da0ca2a0eb2446bd764240e892b2035`;
this bundle was revised by the round-2 security fix pass (findings
NM-01/NM-03/NM-05, `PLAN-165/architect/round-2/security-review.md`) and
re-verified with `git apply --check` from the repo root on 2026-08-03.
If HEAD has moved when the ceremony runs, re-run `git apply --check` first;
on conflict, regenerate from `.claude/plans/PLAN-165/ceremony-staged/`
sources (the anchors are unique context strings, not line numbers).

Integrity: `MANIFEST.sha256` in this directory is the tracked hash manifest
(repo lesson [[feedback-staged-inputs-need-tracked-hash-manifest]]). The
ceremony executor MUST run `shasum -a 256 -c MANIFEST.sha256` fail-closed
before applying anything.

---

## p1-deny-overlay.patch — deny rules for the whole posture-write surface (P1, closes D2 + NM-01 + NM-03)

> **Round-2 revision.** The adversarial security review
> (`PLAN-165/architect/round-2/security-review.md`) proved that denying only
> the overlay leaves two open rungs on the same escalation ladder. The deny
> surface is now **six entries over three files**, identical in both mirrors.

**Touches (both canonical-guarded / kernel-adjacent):**

- `.claude/settings.json` — appends six entries to `permissions.deny`,
  **after** the `Bash(curl * | bash)` tripwire so entries 5-24 keep
  mirroring `install.sh` `DENY_BASELINE_ENTRIES` by position
  (`_deny_baseline_comment` stays true). Adds
  `_night_mode_deny_surface_comment` documenting the rationale.
- `templates/settings/settings.base.json` — the same six deny entries +
  comment. **The mirror is mandatory** — without it
  `test_template_dogfood_parity` / template-parity gates go red. The six
  entries are byte-identical in both files.

**The six entries and why each exists:**

1. `Edit(.claude/settings.local.json)` + `Write(.claude/settings.local.json)`
   — the per-machine, gitignored overlay that decides the NEXT session's
   permission posture. Under `defaultMode=acceptEdits` a tool Edit/Write of
   it is auto-accepted — the direct escalation ladder (agent enters
   acceptEdits, rewrites the overlay, the next session boots wider without
   anyone typing). Original P1 scope (plan D2).
2. `Edit(.claude/state/night-mode.json)` + `Write(.claude/state/night-mode.json)`
   — **NM-01 (CRITICAL)**: the night-mode marker/snapshot is a
   posture-write primitive **by proxy**. `night-mode off` restores
   `marker.prev_value` into the overlay, so a tool write of the MARKER
   launders into an overlay write the overlay deny cannot see — and the
   trigger is the Owner's own designed morning `off`, no attacker Bash
   approval needed (live probe in the round-2 review restored
   `bypassPermissions` this way). The script-side closed-set validation of
   `prev_value` (round-2 fix, NM-01) is the second, independent layer; this
   deny closes the write path itself. The marker is gitignored and NOT in
   `_CANONICAL_GUARDS`, so no other guard covers it.
3. `Edit(.claude/scripts/night-mode.py)` + `Write(.claude/scripts/night-mode.py)`
   — **NM-03 (HIGH)**: the single sanctioned writer itself. `.claude/scripts/`
   has no glob in `_CANONICAL_GUARDS` and `night-mode.py` is not enumerated
   there, so under the very posture night-mode creates, editing the writer
   was auto-accepted (audited by PostToolUse, not blocked). Do not ship a
   toggle whose own writer is softer than the file it writes.

All six cost no legitimate path: `night-mode.py` writes the overlay and the
marker as a *process* (tempfile + `os.replace`), never via the Edit/Write
tools, and the script itself changes only through governed review (this
worktree flow) or a future ceremony.

**Why ceremony-gated:** `.claude/settings.json` is deny-listed against Edit
(`Edit(.claude/settings.json)` is itself in `permissions.deny`), watched by
`/ceo-boot` `settings_tamper_tripwires` + `harness_config_gate`, and
`check_bash_safety.py` treats `-c`/`-e` bodies referencing it as a
canonical-edit vector (confirmed live again while building this bundle: a
read-only `python3 -c` validation referencing the path was blocked).
Sentinel ceremony is the only sanctioned write path.

**Design notes:**

- The `Write()` twins are kept deliberately despite PLAN-161 C1 (on CLIs
  >=2.1.216 `Edit(X)` deny covers all file-editing tools): these entries
  guard POSTURE-CONTROLLING files, so the old-CLI residual is not accepted
  here.
- W0 T0.4 (PLAN-165/probes/W0-EVIDENCE.md) confirmed live that a project
  deny **survives** a local overlay that only sets `defaultMode` (harness
  deep-merges permissions), so this rule keeps firing in night mode.
- `check_harness_config.py` `DENY_BASELINE` subset invariant is unaffected
  (appending entries preserves subset).
- AC-8 of the plan requires a **positive probe** after landing: observe the
  denial, do not presume it.

## p2-audit-action.patch — `night_mode_toggled` audit action (P2)

> **Atomicity requirement (round-2, NM-05/NM-08).** Emitting an
> unregistered action makes reality-ledger detector 6
> (`test_reality_ledger.py::test_detector_6_no_phantoms_at_head`) and the
> audit-registry coverage checker
> (`test_check_audit_registry_coverage.py::TestRealRepoSmoke`) go red — and
> those guards are **correct**. So the script-side emit and this
> registration must land in the SAME ceremony, atomically: there must never
> be a commit at whose HEAD the emit exists unregistered. The round-2 fix
> pass removed the pre-registration emit from the staged `night-mode.py`
> (it redded both guards and was a breadcrumb-only dead call); this ceremony
> re-adds it per §"P2 emit re-insertion" below.

**Touches:** `.claude/hooks/_lib/audit_emit.py` — arbitration-kernel path
with **no sentinel escape**; ceremony-only by construction. Four insertion
sites, matching how the file actually does it (modelled on the PLAN-163
`directory_added_recorded` / `notification_lifecycle` pair):

1. `_KNOWN_ACTIONS` += `"night_mode_toggled"` (323 → 324), with the
   standard registration comment block.
2. Module constants next to the PLAN-163 block: `_NIGHT_MODE_MODE_ENUM`
   `{acceptEdits, manual, absent, other}`, `_NIGHT_MODE_RESULT_ENUM`
   `{applied, noop, refused, failed, other}`,
   `_NIGHT_MODE_HOSTNAME_HASH_RE` (`^([0-9a-f]{12})?$`), and
   `_NIGHT_MODE_TOGGLED_ALLOWLIST = _CODEX_AUDIT_ENVELOPE |
   {mode, previous_mode, result, hostname_hash}` — the ONLY caller fields,
   per the plan. Never a file path, never file content, never the raw
   hostname.
3. A dedicated `elif action == "night_mode_toggled":` scrub branch in
   `emit_generic` — deny-by-default `_scrub_ceo_boot_event` + VALUE
   re-coercion (off-enum → closed default, never echoed; off-shape hash →
   `""`), isinstance-guard first (the H4 unhashable-TypeError class from the
   PLAN-163 fix-pass). **NEVER** `_EMIT_GENERIC_PASSTHROUGH`.
4. A typed wrapper `emit_night_mode_toggled(*, mode, result,
   previous_mode="absent", hostname_hash="", session_id="", project="")`
   with the full Sec MF-3 field-safety docstring.

Verified on a scratch overlay of `.claude/hooks/`: `py_compile` clean;
the `test_audit_emit_ghost_action_guard.py` partition invariant holds
(`night_mode_toggled` is BRANCHED, not reserved, not passthrough; 0
uncategorised members); enum/regex behaviour spot-checked.

### 4-source checklist the ceremony executor MUST complete (plan §P2)

This patch delivers source (1) and (2). Landing the ceremony requires all
four — "não é uma linha":

1. ~~`_KNOWN_ACTIONS` entry~~ — **in this patch.**
2. ~~Typed wrapper + deny-by-default scrub branch~~ — **in this patch.**
3. **SPEC schema entry — NOT in this patch** (deliberate: `SPEC/**` is
   deny-Edit'd; the SPEC edit belongs to the ceremony commit itself). Add
   the `night_mode_toggled` row to `SPEC/v1/audit-log.schema.md` with the
   field enums above and the governing ADR (PLAN-165 T1.6). Checked by
   `test_audit_emit_callsite_coverage_matrix.py` (4-source matrix; SPEC
   coverage floor) — do NOT lean on the ≥60% soft floor, add the row.
4. **Partition + chain tests — NOT in this patch.** Run at minimum:
   `pytest .claude/hooks/tests/test_audit_emit_ghost_action_guard.py
   .claude/hooks/tests/test_audit_emit_coverage.py
   .claude/hooks/tests/test_audit_emit_callsite_coverage_matrix.py` and the
   HMAC-chain suite; add per-action coverage (emit → read back → assert the
   four fields survive, a ghost field like `settings_path` is dropped, an
   off-enum `mode` coerces to `"other"`, and `verify_chain()` passes) plus
   a fixture under `.claude/hooks/tests/fixtures/` if the matrix demands
   one. Note: until `night-mode.py` lands in W1, the action has ZERO
   production callers — that is fine for a **branched** action (only
   `_RESERVED_ACTIONS` members are producer-scanned), so no
   `_RESERVED_ACTIONS` entry and no ADR-state coupling is needed.

### P2 emit re-insertion (MANDATORY — same ceremony)

**Why this is an instruction block and not a diff hunk — stated plainly:**
`night-mode.py` does not exist at canonical HEAD (W1 is blocked on this very
ceremony), so a hunk touching it can never pass this bundle's
`git apply --check` gate against HEAD; and the staged script is still being
revised by the round-2 fix pass (NM-01/NM-02/NM-04 etc.), so no context
lines can be guaranteed. Both conditions independently force the sanctioned
fallback: the emit is specified here, precisely located, with a
self-contained snippet.

**Atomicity discipline:** the registration lands with `p2-audit-action.patch`
in the ceremony commit; the emit lands in the same ceremony's W1-land commit
— the first commit that puts `night-mode.py` at HEAD. Registration-before-emit
in commit order, both inside the one ceremony: at no commit does an
unregistered emit exist at HEAD, so reality-ledger detector 6 and the
audit-registry coverage checker stay green at every point.

**1. Add the helper** (self-contained; requires the script's existing
`hashlib`, `sys`, `REPO_ROOT`, `_hostname` — all present) in the
`# Audit` section of `.claude/scripts/night-mode.py`:

```python
def _emit_audit(mode: str, previous_mode: str, result: str) -> None:
    """Best-effort night_mode_toggled emit (P2, NM-05). NEVER raises,
    NEVER blocks the toggle.

    Only the P2-allowlisted fields travel: mode, previous_mode, result,
    hostname_hash (= sha256(hostname)[:12]). Never a file path, never
    file content, never the raw hostname. Pass "other" explicitly when a
    value is unknown at the terminating path — the typed wrapper coerces
    any off-enum value to "other" anyway (never echoed).
    """
    try:
        hooks_dir = str(REPO_ROOT / ".claude" / "hooks")
        if hooks_dir not in sys.path:
            sys.path.insert(0, hooks_dir)
        from _lib import audit_emit  # noqa: E402

        audit_emit.emit_night_mode_toggled(
            mode=mode,
            previous_mode=previous_mode,
            result=result,
            hostname_hash=hashlib.sha256(
                _hostname().encode("utf-8")
            ).hexdigest()[:12],
        )
    except Exception:  # noqa: BLE001 — observability must never block
        pass
```

**2. Call sites — NM-05: one emit on EVERY terminating path of `on`/`off`.**
Placement rule (structural, not line-numbered, because the fix pass owns the
file): in `cmd_on` and `cmd_off`, every `return` statement is immediately
preceded by exactly one `_emit_audit(...)` call; `main()`'s catch-all
`except` emits once before returning 2. Exactly one emit per invocation —
no path may emit twice. `status` NEVER emits (read-only, not a toggle).

Result mapping (must match `_NIGHT_MODE_RESULT_ENUM` semantics in the patch):

| Terminating-path class                                                    | `result`  |
|---------------------------------------------------------------------------|-----------|
| exit 0, settings/marker actually written or restored                      | `applied` |
| exit 0, idempotent no-op (second `on`, second `off` — nothing written)    | `noop`    |
| exit 2 — CI refusal, malformed-input fail-closed, NM-01 closed-set `prev_value` rejection, lock contention (`FileLockTimeout`) | `refused` |
| exit 1 — write attempted but OSError / read-back diverged                  | `failed`  |

`mode` / `previous_mode` values: use the real literal when known at that
point (`"acceptEdits"`, `"manual"`, or `"absent"` for a removed/never-present
key; any other snapshotted string passes through and the wrapper coerces);
use `"other"` when the path terminates before the value is read (e.g. CI
refusal, malformed marker). For `cmd_on`, `mode` is always the module
constant `NIGHT_MODE`.

In `main()`'s catch-all: distinguish lock contention if cheaply possible
(`from _lib.filelock import FileLockTimeout` inside a try — timeout →
`result="refused"`, anything else → `result="failed"`), with
`mode="other"`, `previous_mode="other"`. If the import itself fails, emit
`failed` — never let the audit attempt raise.

**3. Update the script's module docstring `## Audit` section and `_EPILOG`**
to describe the registered emit (the round-2 fix pass removed the old
"defensive no-op until P2" wording along with the emit; do not resurrect
that wording — post-ceremony the action IS registered).

**4. Verify** (both must be green at the W1-land commit):

```
pytest .claude/scripts/tests/test_night_mode.py -q
pytest .claude/scripts/tests/test_reality_ledger.py \
       .claude/scripts/tests/test_check_audit_registry_coverage.py -q
```

The round-2 test-verification report recorded exactly these two suites red
when the emit existed unregistered — they are the atomicity oracle.

### Pair-rail inputs_hash — recompute at the ceremony

`.claude/hooks/_lib/audit_emit.py` is line 27 of
`.claude/governance/pair-rail-inputs-hash-manifest.txt`. Landing this patch
changes the file's `git hash-object` SHA, therefore the `inputs_hash` of
every FUTURE pair-rail verdict changes. The ceremony must recompute
`inputs_hash` (git hash-object + canonical_json envelope, per the verdict
template) for the next verdict; already-signed verdicts are per-tag and
stay valid.

---

## What is deliberately NOT here

- No edit to `SPEC/v1/audit-log.schema.md` (see checklist item 3).
- No `night-mode.py`, no `/night-mode` command, no ceo-boot banner — that is
  W1/W2 of the plan, blocked until this ceremony lands. The script's audit
  emit is deliberately delivered as the §"P2 emit re-insertion" instruction
  block, not a diff hunk (the file does not exist at HEAD — see that
  section for the full rationale).
- No `bypassPermissions` anywhere (plan D1 — cut in v2).

---

## p3-remove-disableautomode.patch — reversão de decisão ratificada

**O que faz.** Remove `"disableAutoMode": "disable"` do
`.claude/settings.json` e reescreve o `_posture_comment` que a descrevia.
Nada mais muda: `permissions.defaultMode` continua `"manual"`.

**Por que.** Decisão do Owner em 2026-08-03, revertendo explicitamente a
ratificação do PLAN-163 T5.3/OQ5(c). O argumento dele, verbatim: *"o
disableautomode já é escolha do usuário usando o shift+tab, não deveria
nunca ter saído — não é o framework que decide isso."*

O efeito observado da chave é maior que o documentado. O comentário dizia
"no automatic permission-mode escalation mid-session"; na prática ela
também **remove `auto` do ciclo shift+tab do operador**. Ou seja: o
framework estava retirando uma afordância nativa do Claude Code do próprio
dono da máquina. Escolher o modo da sessão é decisão do operador.

**O que NÃO muda.** O default fail-closed continua: toda sessão **começa**
em `manual`, perguntando. O que volta é a capacidade de sair disso
deliberadamente, no teclado, e só para aquela sessão.

**Medição que embasa (2026-08-03, camada de usuário neutralizada via
`CLAUDE_CONFIG_DIR`, projetos de rascunho em `/tmp/nm`):**

| overlay local | rodapé | Bash `date` | Edit | Write |
|---|---|---|---|---|
| (nenhum) | `manual mode on` | pediu aprovação | pediu | pediu |
| `acceptEdits` | `accept edits on` | passou | passou | passou |

A primeira execução da mesma sonda foi INVÁLIDA e quase passou por válida:
sem neutralizar a camada de usuário (que tem `Bash(*)`, `Edit`, `Write`
liberados globalmente), o controle `manual` não perguntou nada — idêntico
ao tratamento. Um controle que não falha quando deveria falhar é a única
defesa contra medir a coisa errada.

**Superfície de risco.** Nenhum teste afirma que a chave existe; o
`check_harness_config.py` não a exige; o `effective_config.py` não a
consome; no `templates/settings/settings.base.json` ela aparece apenas
dentro de um comentário de documentação para adopters (a chave nunca foi
enviada viva no template). Logo a remoção não redenna nada e não muda
comportamento de adopter.

**Ordem na cerimônia.** p3 é independente de p1/p2 — pode landar antes,
depois ou junto. Se landar junto com p1, os dois tocam
`.claude/settings.json`: aplique **p1 primeiro** (ele acrescenta entradas
ao `permissions.deny`), depois p3 (que remove uma chave top-level). Os
hunks não se sobrepõem, mas a ordem mantém o contexto previsível.

**Registro formal.** Isto reverte uma decisão de postura ratificada em L3.
O registro mínimo está aqui e na nota datada do PLAN-163. Se o Owner quiser
o registro formal, cabe uma emenda ao ADR de postura — não foi criada
unilateralmente para não inflar a contagem de ADRs sem ele pedir.
