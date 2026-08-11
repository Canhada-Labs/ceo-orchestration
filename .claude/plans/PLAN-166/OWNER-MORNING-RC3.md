# OWNER-MORNING — corte da rc.3 (escrito na madrugada de 10→11/08)

## O que aconteceu enquanto você dormia

1. **O GA-CUT abortou certo.** O re-pass do hold sobre a rc.2 deu
   **NO-GO nas 2 partes** — 8 achados, **todos verificados como REAIS**
   contra a árvore (0 ruído). Triagem completa:
   `repass-ga-rc2-NOGO/TRIAGE-ga-repass.md`.
2. **Todas as curas foram autoradas** em worktree da rc.2 e revisadas
   pelo rail codex até GO (`repass-rc3-cures/`). Destaques:
   - `npm-publish.yml`: guard fail-closed de tag-liveness antes do
     publish (o P1 que motivou o NO-GO da parte 2) + testes de pin.
   - `CHANGELOG.md`: 188→190 ADRs + seção de upgrade adopter-visível.
   - `verify-counts.sh`: matcher escopado do header do CHANGELOG.
   - `release.yml`: **timeout 20→35 já na rc.3** (a lição do rerun da
     rc.2; o patch pós-GA do W3 foi aplicado ao staged AGORA e o
     MANIFEST re-pinado — você NÃO precisa mais aplicar
     `~/.rc2-backup/w3-timeout-bump-postGA.patch` depois do GA).
   - Espelho no `staged-w3` para o W3 não reverter nada.
3. **Pack fechado**: `staged-rc3/` (7 arquivos, MANIFEST + BASELINE),
   sentinel `RC3-approved-draft.md` com Anchor-SHA pré-preenchido,
   templates de verdito rc.3, e o `OWNER-GA-CUT.sh` já re-apontado
   para a rc.3.

## Rota ratificanda (recomendação (A) da triagem)

Curas → **rc.3** → hold ADR-103 de 24h → GA (~1 dia depois do corte).
Rodar o script abaixo É a ratificação da rota. Se preferir a rota (B)
(waiver do hold), NÃO rode — me chame no Claude.

## O ÚNICO comando

```bash
cd /Users/joaocanhada/canhada-labs/ceo-orchestration
bash .claude/plans/PLAN-166/OWNER-RC3-CUT.sh
```

- **3 pinentries**: sentinel → verdict-fields → tag.
- **Confirmação do push da tag = `SIM` MAIÚSCULO.**
- CI do push: com o bump 20→35 o release-gate não deve mais estourar;
  se algum workflow do PUSH ficar vermelho, o script para — me chame.
- Pode deixar rodando e sair; ele avisa com som/notificação nos
  momentos que precisam de você.

## Depois da rc.3 (mesma sequência de antes, 1 dia depois)

1. Hold 24h do publishedAt da rc.3.
2. `bash .claude/plans/PLAN-166/OWNER-GA-CUT.sh` (re-pass roda de novo,
   agora sobre a árvore CURADA).
3. Pós-GA — assinar W3 (SEM patch de timeout, já aplicado):
   ```bash
   cd /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-169
   cp W3-approved-draft.md W3-approved.md
   # preencher Anchor-SHA = git rev-parse HEAD e a Data
   gpg --armor --detach-sign -u CFCFACF00335DC74 W3-approved.md
   bash OWNER-W3-LAND.sh --dry-run   # depois sem flag
   ```

## Registro honesto

- P2 deferidos (não mudam o artefato publicado; vão pro ledger 169):
  `parse_timestamp` aceita 99:99:99; `install-npm.sh` local copia root
  README sobre npm/README.
- O verdito da rc.3 segue GO-WITH-CONDITIONS com as MESMAS 4 exceções
  do trem (V1/V2/V4/V5 — curas no W3 pós-GA). Nada novo entrou.
