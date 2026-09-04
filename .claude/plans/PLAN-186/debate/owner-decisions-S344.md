---
plan: PLAN-186
recorded_at: 2026-09-04
recorded_by: CEO (AskUserQuestion, doutrina PLAN-135 K10 — texto da opção selecionada, verbatim)
---
# Decisões do Owner — S344 (2026-09-04), checklist do AC-16 emitido pelo `OWNER-S343-W4A-MEASURE.sh`

Contexto: a wave `wave-s343-w4a` LANDOU em `8003b65` (assinatura GPG do Owner sobre o anchor `93efbb1`);
a medição (`OWNER-S343-W4A-MEASURE.sh`) escreveu `PLAN-186/w4/validate-deletion-RESULT.md` em `0b5e6ed`
com 3 corridas serializadas verdes (`33874751641`, `33875799896`, `33876800710`) contra os 3 baselines
registrados na S340 (`33709753629`, `33656365016`, `33630753334`). O drift de baseline (3 commits
distintos; 16 commits / 125 arquivos até o HEAD medido) foi reconhecido por `CEO_W4A_BASELINE_DRIFT_ACK=I-ACCEPT`.

| Item | opção selecionada (verbatim) | efeito no plano |
|---|---|---|
| AC-16 | «Sim, marcar como concluído (Recomendado)» | AC-16 vira `[x]` com data, os commits de hoje e a ressalva carimbada dos baselines de commits diferentes; o AC-6 ganha nota (metade Validate ≤ 14 min satisfeita nas 3 corridas; metade Smoke segue aberta); o AC-11 ganha os 3 runs pós-deleção como candidato a «baseline LOCAL pré-matriz» |
| Janela de required-check | «Registrar no plano e tratar na W4b (Recomendado)» | nada muda no GitHub hoje (o `main` NÃO tem branch protection — API 404 «Branch not protected»; os pushes diretos das cerimônias continuam); a janela «matriz vermelha + Validate verde numa PR» entra como item nomeado da W4b, com a nota de que ligar a proteção do `docs/BRANCH-PROTECTION.md:101-105` bloquearia os pushes diretos de SIGN/LAND/MEASURE e é mudança de ROTA, não checkbox |

## W-ROTA (recon `w-rota-recon`, brief `DECISION-BRIEF-S344.md`; AskUserQuestion ~13:20)

| Item | opção selecionada (verbatim) | efeito na wave W-ROTA |
|---|---|---|
| SPEC/v1/tier-policy.schema.md | «Incluir o SPEC e subir a versão junto (Recomendado)» | o SPEC vira leitor GERADO da tabela; `VERSION 1.3.0 → 1.4.0` + `CHANGELOG.md` + os sites de bump (`_release_bump_sites.py print-sites`) entram no MESMO patch assinado (AC-17 ganha a perna do bump) |
| 9 chaves conflitantes | «Corrigir os 9 na mesma cerimônia» (NÃO a recomendação) | regra ÚNICA de valor, não 9 decisões: para cada chave conflitante o valor servido pela tabela é o id que a cerimônia de roteamento (W1, `wave-s340-w1`, ADR-149 working set) grava para o papel — VETO → `claude-fable-5-1`, ICs pinados (qa/perf/devops/finops) → o id que a W1 pinar; papéis que só existem no fallback do audit log ficam com o valor do fallback normalizado para a família corrente. A prova «delta 0» deixa de existir por decisão do Owner; em troca, cada valor corrigido aparece como linha explícita no diff da tabela, com o dono antigo citado. Ordem: W-ROTA constrói sobre o pack `w1-widen` (ids-alvo em `DECISIONS-W1-S340.md`) e landa DEPOIS da W1 (OQ-7). |
