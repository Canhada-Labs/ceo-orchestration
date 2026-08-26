# Pacote C — rail codex rodada 2 (shadow-185, 2026-08-26T22:23:16Z)

Rail-Verdict: REJECT
Comando: `codex exec review --uncommitted --skip-git-repo-check` na shadow-185 (W1+W2 + metade CI/docs; estado das ~19:10)
Achados: 3 P1 + 1 P2 — 2 P1 de código → u1-3-w1w2-cure-writer-r2; 1 P1 (step do censo sem bundle na sombra) + 1 P2 (ADR-196 §6 vs código) → c-ci-docs-writer (19:25).

Full review comments:

- [P1] Add the census bundle before enabling its blocking step — .github/workflows/validate.yml:365-368
  The staged tree contains neither `.claude/scripts/check-installer-write-safety.py` nor its baseline and unit test, so every validate run reaches `.github/workflows/validate.yml:368` and fails with “can't open file.” The change's own `DESIGN-C.md:640-647` identifies this as a blocker; add the required bundle or defer this workflow step.

- [P1] Preflight fixed project templates before any write — scripts/install.sh:991-996
  On a fresh maintainer target with `CLAUDE.md`, `MEMORY.md`, or `.mcp.json` planted as a dangling symlink, this global list passes because those fixed destinations are omitted. Their later `install_template` check records the refusal only after `.claude/`, `docs/`, and `.github/` have been populated; because a fresh target has no `BACKUP_DIR`, the final failure leaves a large unmanifested partial install. Add these known destinations to the global preflight at `scripts/install.sh:991-1005`.

- [P1] Reject resolved symlinks used as target roots — scripts/_framework_manifest_set.sh:766-773
  When the caller supplies an existing resolved symlink as the target root, `-e` is true, so this branch never checks `-L`; the subsequent `cd -P` changes the confinement baseline to the referent and accepts every write beneath it. Thus the installer writes through the root symlink instead of issuing the refusal promised by `scripts/_framework_manifest_set.sh:763-765`; test `-L` before resolving the root.

- [P2] Align the ADR's CODEOWNERS provenance rule with the code — .claude/adr/ADR-196-installer-write-confinement.md:104-109
  This canonical decision says a previously recorded `github_owner` authorizes recovery, while `_codeowners_provenance` and the new F2.8 test deliberately accept only a baseline delivery record. In the covered scenario—an adopter-owned CODEOWNERS was skipped while the request was persisted, then deliberately emptied—the ADR's rule would silently re-enable review routing. Update ADR-196 §6, DESIGN-C §5, and threat-model T-008 to specify delivery-record-only provenance.
The patch introduces an always-failing CI step because its executable is absent, and the destination-confinement implementation still permits partial installs and resolved target-root symlinks in specific cases. Its canonical provenance documentation also contradicts the implemented security policy.

