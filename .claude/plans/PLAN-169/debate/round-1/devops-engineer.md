---
plan: PLAN-169
round: 1
archetype: DevOps Engineer
---

## Verdict

ADJUST — a direção técnica (fix, riders, gate) está correta e verificada
linha-a-linha no código; falta fechar uma ambiguidade real de sequenciamento
no delta-gate de release antes de executar W6.1, e decidir explicitamente um
item hoje silencioso (B.a gateia v1.3.0 ou não).

## Summary

- W1 (fix + riders + aceite 62/3) foi conferido diretamente no código e está
  correto e falsificável; o gate (`ownership-nightly-gate.sh`) já é robusto
  (PLAN-168) e não precisa de mudança.
- O guard de delta do tag (`_release_tag_guard.py`) já foi desenhado para
  acomodar exatamente o cenário do W6.1 ("ancorar no parent_sha revisado, não
  na última RC") — mas o plano tem duas âncoras diferentes e não-reconciliadas
  para o re-pass r2 (o SHA da evidência do ledger vs. as pré-condições do
  W6.1), e a diferença decide se `bump --rc 2` passa ou é rejeitado com
  exit 6.
- A auditoria dos "48 matchers" (W4.4 P0) é bem mais barata do que soa: contei
  os matchers reais em `.claude/settings.json` e só 2 dos 48 têm hífen — vale
  escopar o item com esse número em vez de deixá-lo aberto.

## Risks

- **Delta-gate rejeitando rc.2 depois do hold já ter começado.**
  `.claude/scripts/local/_release_tag_guard.py:11-30` documenta a própria
  razão de existir: "for an rc.2 it would reject the very W0/W1 fixes the
  re-pass just reviewed" — ou seja, o `parent_sha` do verdito TEM que ser o
  SHA que o re-pass r2 efetivamente revisou, incluindo qualquer wave do 169
  que seja pré-condição do GA. Se W0-W2 (ou W3) landarem em commits DEPOIS do
  SHA que o re-pass revisou, esses commits caem fora do
  `delta_allowlist` e o guard derruba a tag com exit 6 — dentro da janela de
  hold de 24h, o que reinicia o relógio (A.3 do ledger já descreve esse
  reinício para o caso "main avançou", mas aqui a causa seria uma
  ORDEM DE EXECUÇÃO errada dentro do próprio 169, não um push alheio).
- **B.a (`upgrade.sh` aborta a meio caminho com `PROTOCOL_SOURCE` malformado)
  não está nas pré-condições de W6.1** e é um bug REPRODUZIDO no mesmo
  binário `upgrade.sh` que v1.3.0 vai distribuir aos adopters
  (`ledger-S298.md:75`, repro confirmado). O plano lista W3 como wave
  independente sem amarrar decisão a W6.1 — silêncio aqui significa "ship
  v1.3.0 com um bug de abort-de-upgrade conhecido e reproduzido", o que é
  uma decisão real, não um não-evento.
- **Espera desnecessária de até 24h para validar o W1** se o executor não
  souber que `ownership-nightly.yml` já tem `workflow_dispatch: {}`
  (confirmado no arquivo, linha ~21) — o plano não instrui usá-lo, e o
  cron só dispara às 06:43 UTC.

## Must-fix (blocking)

1. **Amarrar o `parent_sha` do re-pass r2 às pré-condições reais do W6.1.**
   Adicionar uma frase explícita em W6.1 (ou A.1 do ledger, se reaproveitado
   como runbook): "o re-pass r2 roda no HEAD que JÁ inclui todas as waves
   marcadas pré-condição de v1.3.0 GA (no mínimo W0+W1; decidir e registrar
   se W2/W3 entram também) — NUNCA no SHA `ad9cc3a` citado como evidência
   estática do ledger". Sem isso, quem executar literalmente a "Ação" do
   item A.1 (`ledger-S298.md:22`) revisa o SHA errado e o `bump --rc 2`
   subsequente será legitimamente rejeitado pelo próprio guard que o 166
   construiu.
2. **Decisão nomeada (não silêncio) sobre B.a vs. v1.3.0 GA.** Registrar em
   W6.1 (ou como 5º OQ) uma de duas rotas: (a) W3 landa e é verificado ANTES
   do corte de rc.2 — reconhecendo que isso adia o GA além do "imediato" que
   a tese do plano promete; ou (b) v1.3.0 GA sai sabendo do bug reproduzido
   em `upgrade.sh`, com a exceção nomeada no release-checklist/CHANGELOG e
   gatilho de correção para v1.4.0. Hoje o plano não escolhe nenhuma das
   duas — a leitura padrão de um executor apressado é a rota (b) por
   omissão, o que é aceitável SE for uma escolha, não um esquecimento.
3. **Instruir `workflow_dispatch` explicitamente no runbook do W1.** Uma
   linha no item "Aceite (falsificável)": "logo após o commit do fix,
   disparar `gh workflow run ownership-nightly.yml`, longe do horário do
   cron (`43 6 * * *`) para não colidir com `concurrency:
   cancel-in-progress: true` — não esperar pela janela agendada para
   confirmar 62/3".

## Nice-to-have

- Escopar W4.4 P0 com o número já levantado: `python3 -c` sobre
  `.claude/settings.json['hooks']` mostra 48 registrações totais e exatamente
  2 hifenizadas — ambas a mesma alternação
  `mcp__codex__codex|mcp__codex__codex-reply` (`PreToolUse` e `PostToolUse`).
  Isso transforma "auditoria dos 48 matchers" de tarefa aberta em "provar que
  essas 2 registrações ainda disparam", reaproveitando o padrão de teste já
  existente em `.claude/hooks/tests/test_check_codex_filewrite.py` em vez de
  desenhar harness novo.
- Fechar a higiene do `NPM_TOKEN` de rollback do PLAN-158
  (`.claude/plans/PLAN-158-release-v1-1-0.md:38` cita expiry ~2026-09-28)
  como item de checklist do W6: confirmar que foi revogado após o primeiro
  GA via OIDC (v1.2.0) — o calendário do 169 (4-6 dias mínimo) não encosta no
  prazo, mas é uma ponta solta barata de fechar junto do trem.
- Corrigir também o comentário de estimativa de tempo em qualquer lugar que
  repita a lore antiga de "50-75 min esperado" além de
  `ownership-nightly.yml:34-37` (já contemplado no plano) — vale um grep
  rápido em `smoke-install.yml` pelo mesmo texto antes de fechar W1, já que
  os dois workflows compartilham nota de sizing por runner.

## Unseen

- O que fazer se o guard de delta (`_release_tag_guard.py`, exit 6-12) disparar
  DURANTE o hold de 24h por uma causa DIFERENTE de "main avançou" — por
  exemplo, `delta_manifest_sha256` desatualizado por um re-run parcial do
  re-pass, ou um `verdict-fields-<TAG>.md` colocado no diretório errado
  (o próprio cabeçalho do script cita isso como modo de falha distinto,
  exit 9/10). O plano só descreve a rota de recuperação para o caso "main
  == SHA rc.2 falhou" (A.3, "corta-se rc.3"); os exit codes 6-12 do guard
  são mais granulares e merecem uma linha de runbook apontando pra tabela de
  exit codes do próprio script como referência de triagem.
- Colisão entre um `workflow_dispatch` manual de validação (must-fix 3) e o
  `concurrency: group: ownership-nightly, cancel-in-progress: true` do
  próprio workflow — se o port landar perto de 06:43 UTC, o disparo manual
  pode ser cancelado pelo cron (ou vice-versa). Baixo risco, mas nenhuma
  wave menciona isso.

## What I would NOT change

- O fix em si (GNU-first, `stat -c` antes de `stat -f`) — confirmado por
  leitura direta que é simétrico e correto nas duas plataformas, e que já é
  o padrão canônico do repo (`scripts/install.sh:728-730`); a única inversão
  real é `test-ownership-table.sh:162`, exatamente como o ledger afirma.
- `ownership-nightly-gate.sh` — já hardened pelo 168 (cobertura de tabela
  inteira via `--list`, TIMEOUT/ESCAPE/AMBIG fail-hard, rc-semantics
  explícita); o plano está certo em não tocar aqui e em proibir editar
  `ownership_table.tsv`/`ownership-expected-reds.txt`. Confirmei também que
  o arquivo de expected-reds tem exatamente as 3 linhas e a tabela tem
  exatamente 65 células — o "62/3" do plano bate com o disco.
- A infraestrutura de npm trusted publishing / OIDC (PLAN-158) — já
  GA-provada em v1.2.0, `environment: production-npm` com aprovação manual
  já wired, RC tags já excluídas do publish. Nenhuma mudança necessária para
  os trens v1.3.0/v1.4.0 deste plano.
- A tese de dois trens sequenciais (não um trem gordo) — consistente com o
  próprio desenho do delta-gate, que é estrito por construção contra
  featuritis dentro de uma janela de release.
