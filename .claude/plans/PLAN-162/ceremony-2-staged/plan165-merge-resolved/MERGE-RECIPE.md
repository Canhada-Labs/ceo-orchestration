# PLAN-165 merge — receita determinística (ensaiada S292, 276 testes verdes)

Pré-condição: main == 9c63750 (ou descendente que NÃO toque
.claude/scripts/ceo-boot.py nem .claude/plans/PLAN-163-substrate-uplift.md;
caso contrário RE-ENSAIAR).

```bash
git merge --no-ff --no-commit plan-165-draft
# KEEP MAIN (2):
git checkout --ours .claude/plans/PLAN-165-night-mode-owner-autonomy-toggle.md \
                    .claude/plans/PLAN-165/probes/W0-EVIDENCE.md
# TAKE BRANCH (3 — pack corrigido as-landed):
git checkout --theirs .claude/plans/PLAN-165/ceremony-staged/MANIFEST.sha256 \
                      .claude/plans/PLAN-165/ceremony-staged/README.md \
                      .claude/plans/PLAN-165/ceremony-staged/p1-deny-overlay.patch
# HAND-MERGED (2 — blobs resolvidos ensaiados, sha256 em RESOLVED.sha256):
cp .claude/plans/PLAN-162/ceremony-2-staged/plan165-merge-resolved/ceo-boot.py.resolved \
   .claude/scripts/ceo-boot.py
cp .claude/plans/PLAN-162/ceremony-2-staged/plan165-merge-resolved/PLAN-163-substrate-uplift.md.resolved \
   .claude/plans/PLAN-163-substrate-uplift.md
git add -A
```

## Verificações do ensaio (S292, clone scratch)
- Regressões previstas: GUIA-COMPLETO "46 hooks wired" ✓ + "185 ADRs" ✓;
  npm/README stamp 2026-08-02 ✓ + 27 commands/185 ADRs ✓; CLAUDE.md 185/27 ✓.
- verify-counts.sh: no drift (54 pares; adrs=185, commands=27, registered=46).
- check-claude-md-claims.py: limpo. build-plugin --check: in sync.
- env-inventory: ENV-DRIFT 24 == baseline da main (sem drift novo).
- pytest night_mode + ceo_boot_night_mode + sched_red + ceo_boot + liveness:
  276 passed, 1 skipped.
- Resolução ceo-boot.py: check 24 (scheduled_workflows_red, S292) E banner +
  advisory night-mode (branch) coexistem; severidade high p/ 008-night-mode
  E 008-scheduled-red.
- Resolução PLAN-163: nota 2026-08-02 (branch) + emenda datada 2026-08-03
  (main) em ordem cronológica.
