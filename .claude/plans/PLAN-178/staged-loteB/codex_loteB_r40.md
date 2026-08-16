The core enforcement and fencing changes are largely coherent, but two truncation paths can leave the operator-facing report incomplete or direct recovery to the wrong structured field.

Full review comments:

- [P2] Surface truncation even when severity already matches — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/workflows/nightly-hygiene.js:368-370
  When a dimension exceeds `INGEST_CAP`, a schema-valid synthesizer can return the correct `yellow`/`red` overall while omitting the truncation from `report`; because this branch only prepends the mechanical notice when severity must be raised, the primary report can appear complete despite receiving partial data. Prepend a truncation notice whenever `truncatedDims` is non-empty, independent of the severity comparison.

- [P3] Reference every retained dataset in truncation notices — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/workflows/council-audit.js:723-724
  If the truncated synthesis input is `verify_failed` or `lane_status`, this notice directs the operator only to `confirmed_findings`, which may be empty and does not contain that omitted data. The full values are retained under `verify_failed_findings`, `cross_vendor_disagreements`, and `lanes`, so the notice should identify the field corresponding to each truncated key.