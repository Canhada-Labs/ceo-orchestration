---
plan: PLAN-142
round: 1
created_at: 2026-06-19
---

# PLAN-142 round-1 proposal — Codex pair-rail adapter migration to codex-cli 0.139.0

Full plan: `.claude/plans/PLAN-142-codex-cli-0139-adapter-migration.md`.

## Thesis

The automated Codex pair-rail (ADR-107) is broken against the installed
`codex-cli 0.139.0`: `codex_invoke.py` returns `{"parse_error":"[codex] empty
stdout"}` in 0.094s. Three independent breaks, each reproduced hands-on in S245.
Restore the rail by migrating the adapter to the 0.139.0 surface.

## Scope (3 fixes, 2 in a kernel path)

1. **stdin block** (NON-kernel, `.claude/scripts/codex_invoke.py`): `codex exec`
   blocks reading stdin even with a positional prompt; the wrapper's
   `subprocess.run` doesn't close stdin → instant empty stdout. Fix:
   `stdin=subprocess.DEVNULL` on both `subprocess.run` calls. Verified: same
   argv with `</dev/null` returns exit 0 + 322 bytes.

2. **`--no-color` removed** (KERNEL, `.claude/hooks/_lib/adapters/codex.py`):
   `make_invoke_command()` emits `--no-color`; 0.139.0 rejects it
   (`error: unexpected argument '--no-color'`, exit 2). Fix: `--color never`.

3. **`--json` is a JSONL event stream** (KERNEL, same adapter): with `--json`,
   `codex exec` prints JSONL events, not one object; `parse_verdict()` does
   `json.loads()` on the whole stdout → `Extra data line 2`. The verdict text is
   in the `item.completed` event with `item.type=="agent_message"` (`item.text`).
   Fix: detect the JSONL stream, extract+join `agent_message` texts, then run the
   existing text parser. Backward-compat for plain-text/JSON must be retained.

## Key decisions

- `.claude/hooks/_lib/adapters/codex.py` is an arbitration-kernel path
  (`_KERNEL_PATHS`:155). Editing it is KERNEL-HARD-DENY: sentinel GPG (Owner
  `.asc`) + `CEO_KERNEL_OVERRIDE=<token>` + `CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT`.
- The implementation diff's cross-model pass uses the manual
  `codex exec review --uncommitted` (the rail reviews its own fix — bootstrap).
- The `hook-tests-dual-rail` timeout bump (also a kernel path, `validate.yml`)
  was consciously DROPPED — out of scope here.

## Open questions for the debate

- OQ1: Is `gpt-5-codex` still a valid 0.139.0 model id? (`make_invoke_command`
  forces it regardless of the `model=` arg.)
- OQ2: Is parsing the `--json` JSONL stream the right call, or should the adapter
  switch to `-o/--output-last-message <FILE>` (last message only) — simpler, no
  event-stream parsing, but needs a temp file?
- OQ3: How to keep backward-compat so the parser doesn't regress any
  still-in-use plain-text/JSON path while adding JSONL support?
- OQ4: Test strategy for a kernel adapter whose own pair-rail is the thing being
  fixed (can't dogfood the broken rail to verify the fix).
