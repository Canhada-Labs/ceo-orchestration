# Pacote C — rail codex rodada 1 (shadow-185, 2026-08-26T21:41:22Z)

Rail-Verdict: REJECT
Comando: `codex exec review --uncommitted --skip-git-repo-check` na shadow-185 (W1+W2 sem a metade CI/docs; estado das 18:34)
Achados: 2 P1 + 1 P2 — curas despachadas ao agente u1-3-w1w2-cure-writer-r2 (19:05).

Full review comments:

- [P1] Preflight refusals before any installation writes — scripts/install.sh:3468-3469
  When a destination is refused, for example a dangling `docs/rotation-log.md`, the failure is deferred until here even though `.claude` has already been copied and later root or `.github` writers may also have run. On a fresh target `BACKUP_DIR` is empty, so the exit trap removes none of this partial installation; on an existing target it restores only `.claude`, leaving other writes behind without a manifest or install-state. Preflight all applicable destinations before the first write, or extend rollback to every affected surface.

- [P1] Require actual delivery before accepting owner provenance — scripts/install.sh:1884-1886
  A recorded `github_owner` does not prove the framework wrote CODEOWNERS: if an adopter-owned nonempty `.github/CODEOWNERS` exists, install skips it but still persists the requested owner. If the adopter later intentionally empties that file, this branch treats the request as provenance and overwrites it with the framework template, silently re-enabling review routing despite there being no delivery record. Only a manifest delivery record or an explicit persisted delivery flag should authorize recovery.

- [P2] Preserve dry-runs against absent targets — scripts/_framework_manifest_set.sh:755-758
  For `install.sh --dry-run` with a nonexistent target—including the supported no-target synthetic preview path—`cd -P` necessarily fails here, so every checked destination is recorded as refused and the final verdict exits 1. This breaks the documented dry-run behavior of previewing an absent target without creating it and returning success; the dry-run path needs confinement based on an existing ancestor or a non-writing-specific policy.
The hardening closes write-through paths, but its deferred failure can leave partial untracked installations, its provenance test can overwrite adopter-owned CODEOWNERS, and it regresses supported dry-runs against absent targets.

