Truncated nightly-hygiene results can downgrade an existing red dimension to skipped/yellow, understating a known failure.

Review comment:

- [P1] Preserve red status when truncating dimensions — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/workflows/nightly-hygiene.js:285-286
  When an oversized dimension already reports `status: 'red'`, this unconditional replacement changes it to `skipped`; the synthesis prompt then requires skipped and the mechanical floor only corrects green to yellow. The final audit can therefore downgrade a known red result to yellow, so truncation should preserve the greater severity while separately marking the dimension incomplete.