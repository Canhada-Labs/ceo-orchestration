# PLAN-142 staging — open items (from the 3-agent staging gen, S245)

> These are DRAFTS, generated in parallel, NOT tested (the kernel rail can't be
> dogfooded without the ceremony). They are a starting point; the execution
> session reconciles + tests them. Below are the must-resolve items.

## BLOCKING — reconcile before/at apply

1. **Contract mismatch across the 3 drafts.** The helper exposes
   `build_exec_argv(...)` + `make_invoke_command(...)`; the rail draft calls
   `shape.build_argv(mode='verdict', prompt, output_last_message_path)`; the
   parsers draft assumes
   `make_invoke_command(prompt,*,model,sandbox_mode,timeout_s,output_last_message_path,json_events,output_schema_path,resume_thread_id)`.
   → Pick ONE public API on `codex_cli_shape` and update all three call sites. A
   mismatch is a TypeError at first invocation.
2. **`--model` not hands-on-verified on 0.139.** The helper emits `--model <id>`
   on `exec`. The S245 verified flag list did NOT include `--model`. → Run
   `codex exec --model gpt-5-codex --help`/a smoke call; if rejected, set the model
   via `-c model=...` or config and adjust the helper argv.
3. **Model-id (D5/OQ1).** `_VALID_MODELS` carries gpt-5/gpt-5-mini/gpt-5-codex/
   o3/o3-mini/o4-mini; DEFAULT='gpt-5-codex'; the old wrapper default `gpt-5.5` is
   NOT in the catalog. → Reconcile against the live 0.139 catalog; decide the
   default; coercion is now LOUD (raises) so an unresolved default fails loud.
4. **`_base_to_verdicts` matrix translator** (same kernel file, same ceremony).
   A structured BLOCK is a NEW signal the legacy substring-classifier never saw.
   → Re-read `_base_to_verdicts` (~L1206-1259) and confirm/extend the BLOCK +
   ADVISORY-not-clean arms classify into the intended matrix cases.
5. **`parse_verdict_strict` behavior change:** it now RETURNS an ADVISORY dict
   instead of raising CodexResponseTooLarge/CodexJsonInvalid. → grep callers +
   tests doing `pytest.raises(CodexJsonInvalid)` against it and migrate to assert
   the ADVISORY return. The sole live caller codex_invoke.py:272 must switch to
   passing the `-o` file content (param renamed stdout→last_message).
6. **Grep-gate on comments.** Both kernel drafts keep CLI literals inside `#`
   comments (migration maps). If the §3 grep gate is line-grep (not code-only),
   strip/rephrase those comments before apply, or confirm the gate excludes comments.

## VERIFY at apply

- `--output-schema` shape on 0.139 (raw JSON Schema vs envelope); whether to add a
  SECOND tmpfile (schema) to the hygiene/cleanup surface.
- Prompt delivery: confirm `codex exec ... -- "<prompt>"` accepts the prompt
  positionally on 0.139 (rail draft uses positional + `input=''`, no stdin pipe);
  watch argv length for very large prompts.
- Redaction ownership: EVERY parse_verdict_strict caller must single-pass redact
  the full bytes BEFORE calling (the reader does not redact).
- Outgoing redaction fail policy: decide fail-OPEN (today) vs fail-CLOSED (ADR-114
  §AC9) for `redact_outgoing_then_make_invoke_command` in the helper.
- tmpfile hygiene lives in check_pair_rail.py (mkdtemp 0700, O_EXCL, symlink/owner
  refusal, finally unlink+rmdir) — the helper takes caller-provided paths only.
- 256KB strict cap vs 1MiB read cap vs redactor truncation-marker: confirm a
  >256KB last-message degrades to ADVISORY cleanly (truncation marker after the
  closing brace will fail strict-parse → ADVISORY, which is acceptable).

## CAPTURE (P0 offline fixtures — separate from these drafts)

- A real 0.139 `-o` last-message file (verdict object) → golden fixture for
  redact → parse_verdict_strict → verdict + forged-PASS/oversize/symlink/empty cases.
- A real `--json` JSONL stdout sample → fixture for the rewritten `parse_usage`.

## Source of truth

ACs: `PLAN-142-codex-cli-0139-adapter-migration.md` §3 (15 ACs) + §4 (D1-D5).
Ordering: `EXECUTION-RUNBOOK.md`.
