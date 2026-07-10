# Distiller fixtures (PLAN-154 item 2 — hermetic CI contract)

Recorded inputs for `distill-lessons.py` tests. CI NEVER calls a live
model: the `model_output_*.json` files are the `--from-fixture`
recorded-output contract (`{"model", "tokens_in", "tokens_out",
"output"}`).

The `*_observations.jsonl` files are synthetic OPT-IN observe-store
windows — the on-disk shape written by the observe rail's closed-schema
coercer (`_lib.tool_lifecycle._append_observation`), i.e. one JSON object
per line with the fields `{v, tool_name_enum, duration_bucket, success,
orphan, paired, tool_use_hash}` and NO `action` key. The distiller reads
these from `<audit_dir>/tool-lifecycle/*.observe.jsonl`, NEVER the
always-on `tool_call_lifecycle_recorded` audit action — that read-surface
repoint is the Codex pair-rail S265 P2#4 fix (A12 kill-switch coupling).

Positive-control map (A18 shape — planted violation → expected RED):

| Fixture | Planted violation | Expected behavior |
|---|---|---|
| `hostile_observations.jsonl` | free-text smuggled in `tool_name_enum` + bad bucket + non-bool `success` + extra free-text field | tampered rows DROPPED at the distiller's closed-enum read boundary (defense-in-depth: the writer already coerces, the distiller re-validates); payload never reaches the prompt |
| `killswitch_always_on_audit_log.jsonl` | ALWAYS-ON `tool_call_lifecycle_recorded` rows (audit-log shape, `action` key) that fire even when nobody opted in | the trap for `TestKillSwitchNegativeControl`: seeded into `<audit_dir>/audit-log.jsonl`; a correct distiller reads the observe store and IGNORES these → zero candidates. A regressed distiller (reads the audit action) would mint candidates → RED |
| `model_output_hostile.json` | direct-override injection payload in `advisory_text` | candidate rejected PRE-candidate (scan hit); `add_candidate` never called |
| `model_output_malformed.json` | non-JSON model output | fail-CLOSED: zero candidates written, cursor NOT advanced |
| `model_output_over_schema.json` | extra top-level key (free-text side channel) | fail-CLOSED: zero candidates written, cursor NOT advanced |
| `model_output_benign.json` | none | benign candidate survives to PENDING via `lessons.add_candidate` |
| `model_output_empty.json` | none (model found nothing) | valid empty run; cursor advances |
