---
round: 2
archetype: LLM FinOps Architect
skill: llm-routing-and-finops
agent_persona: (crítico de custo, cota e semântica de roteamento — perfil sintetizado da linha do SKILL MAP)
generated_at: 2026-09-07T02:20:00Z
---

## Verdict

ADJUST — **5 itens BLOQUEANTES** (F1, F2, F4, F6, F10).

## Summary (≤ 3 bullets)

- A revisão curou de verdade a metade textual do K6: o orçamento agora tem unidade, instrumento nomeado e invocação completa (§9:489-505). É a primeira versão deste plano em que dá para REFUTAR o número — e foi o que fiz: rodei a invocação impressa.
- **Onde é forte:** o `0,1753/turno` não é folclore — ele REPRODUZ (subagente US$ 8.740,53 / 49.873 turnos = US$ 0,1752 na janela de hoje). A perna 0 de elegibilidade e o par AC-0.2/AC-0.3 são um controle de verdade (positivo + negativo) e o AC-0.4 pode ficar vermelho.
- **Onde é fraco:** a mesma invocação que dá o preço unitário refuta o VOLUME orçado (F2); a guarda de denominador de 90 dias reintroduz por dentro o calendário que o §0 declara refutado e trava a W2 (F1); a telemetria que sustenta todo o §4 é reportada pelo próprio leitor como cadeia NÃO ÍNTEGRA (F4); e a flag que a W3 usa como teste-mestre não existe (F6).

## Risks

**F1 — P1 — A guarda de 90 dias torna a W2 inexecutável e contradiz o frontmatter.**
§2.1:120 declara `min_window_coverage_days = 90`, e "abaixo de qualquer uma, a saída é RECUSA". §4:182 mede a cobertura da família: `2026-08-21T12:13:43Z` a `2026-09-07T01:35:30Z` = **16,6 dias**. Logo a regra da W0, rodada hoje, devolve `RECUSA` para **toda** skill — e o AC-2.1 ("lista DERIVADA") e o AC-2.2 ("a contagem cai de 166 para 165 no patch que arquiva a primeira skill", §5) só ficam verdes a partir de ~2026-11-19. Isso colide com `external_wait: none` (:16) e `eta_calendar: "mesmo-dia a D+1"` (:17). Pior, §8:467 registra o consenso C1 ("janela de 90 dias inexistente") como CURADO **pela própria guarda** `min_window_coverage_days` — a cura reintroduz o defeito num lugar onde nenhum campo de frontmatter o declara.
*Mitigação:* ou a W2 ganha data mínima de abertura escrita (`W2 não abre antes de <data>`), ou a guarda passa a ser derivada da cobertura disponível com o número ratificado pelo Owner — e o §6 deixa de dizer "não há segundo lugar no corpo que afirme espera".

**F2 — P1 — `budget_usd_estimate: 490-610` é refutado pelo instrumento que o §9 imprime.**
Rodei `python3 <ROOT>/.claude/scripts/ceo-cost.py --since 3d --source transcripts --format json`. Na janela de hoje: **total US$ 9.400,30**; `by_role.assento` = US$ 659,77 em **1.836 turnos**; `by_role.subagent` = US$ 8.740,53 em **49.873 turnos**. O §9:500 orça a perna de refutação em `8 rodadas × 40..120 turnos × US$ 0,1753` = **US$ 56 a 168**, isto é **320 a 960 turnos** — 0,6% a 1,9% do volume de subagente que o MESMO instrumento, na MESMA janela, mede em 3 dias. O plano usa a janela para o PREÇO e ignora-a para a QUANTIDADE, sem uma linha dizendo por que este plano gastaria 1/50 do ritmo observado. Como o custo é 93% subagente, o teto de 610 não sobrevive a uma noite no ritmo medido.
*Mitigação:* derivar o volume do mesmo JSON (turnos de subagente por sessão × 4) ou declarar explicitamente o regime de operação que justifica 320–960 turnos, com critério de morte por custo.

**F3 — P2 — A unidade "assento" medida é FABLE 5.1; o plano orça assento em OPUS 5.**
`by_role.assento` de hoje (US$ 659,77) é byte-a-byte a linha `claude-fable-5-1` do mesmo relatório — o papel de assento roda Fable. Em `<ROOT>/.claude/scripts/cost-table.yaml:70-73` Fable 5.1 é `10/50` por MTok e em `:85-88` Opus 5 é `5/25` — **2×**. O `tier_mix_estimate` (:14) declara "assento Opus 5". Então US$ 109,20/sessão é preço de assento Fable aplicado a um assento Opus sem conversão declarada — a figura tem fonte, mas não tem a transformação que a torna aplicável ao mix planejado.

**F4 — P1 — O ledger que sustenta o §4 inteiro é reportado como NÃO ÍNTEGRO.**
Rodei o Check da AC-1.1 (`skill-health.py --include-rotated --since all --json`): `chain_status = "NOT INTACT: status=tamper reason=hmac_mismatch — treat this report's telemetry as potentially tampered"`. Nenhuma linha do plano cita o estado da cadeia. Os 109 spawns, o 0,257 e o "zero invocações" que decidem ARQUIVAR vêm todos desse log. Arquivar skill (edição canônica, assinatura do Owner) por evidência que o instrumento marca como possivelmente adulterada inverte a doutrina da casa.
*Mitigação:* AC novo na W0 — a regra RECUSA quando `chain_status` não é íntegro, ou registra o estado nos INPUTS impressos (a AC-0.1 já promete imprimir inputs; a cadeia é um deles).

**F5 — P2 — `--include-rotated` é inerte hoje, e os números do §4 são móveis.**
O mesmo run devolve `rotated_siblings_present: False` — não há sibling rotacionado nesta família, então a frase do §1:68-70 ("sem `--include-rotated` o leitor vê só o arquivo vivo e subconta") não é reproduzível no HEAD. E os totais já andaram: `events_scanned = 143.533` (plano: 141.988), `total_invocations = 111` (plano: 109), `unknown_invocation_ratio = 0,252` (plano: 0,257). Direção preservada, magnitude móvel — figuras sem data-âncora dentro do texto.

**F6 — P1 — A W3 depende de uma flag que não existe; as duas pernas do teste-mestre são a mesma perna.**
`<ROOT>/scripts/tests/smoke-install.sh:17` faz `TARGET="${1:-}"` e `:34` invoca o installer com `--profile core,frontend` **fixo**; não há parsing de `--profile` no script (o flag é do `install.sh`, documentado em `scripts/install.sh:12-15`). Então o Check da AC-3.3, `bash scripts/tests/smoke-install.sh --profile core,<domínio>`, trata `--profile` como diretório-alvo (morre no `mkdir`, ou instala num diretório assim chamado) e **nunca** exercita `scripts/install.sh:1310` (`.claude/skills/domains/$part`) — que é exatamente a rota que o §1 passo 3 nomeia como a que regride. E a AC-3.2 ("SEM pacotes") roda o MESMO script, que instala COM frontend. As duas pernas medem a mesma coisa, e nenhuma mede domínios.
*Mitigação:* a W3 entrega primeiro a flag no harness (ou um harness próprio de perfil), e o AC nomeia o caminho que tem de aparecer/desaparecer no alvo.

**F7 — P2 — Minutos de CI e de cerimônia estão fora do orçamento.**
§9 tem três linhas de custo (piso, assento, refutação) e nenhuma de runner. O `Smoke Install` é medido em 58 min a 1h08 (`<ROOT>/CLAUDE.md` §5, linha do `timeout-minutes 126`), e a W3 o chama duas vezes por rodada; a W2 e a W3 são canônicas (§6, "custo de assinatura"), logo carregam rodadas de rail e cerimônia. Um orçamento de plano que ignora a perna mais lenta é uma estimativa de assento, não de plano.

**F8 — P2 — O spread é declarado e não é propagado.**
§9:491-494 mede o piso em 97.292 tokens, diz que a série fria tem "espalhamento de 51,7% sobre a média em 41 amostras" e que "reportar só a média engana" — e a linha seguinte (:495) usa o ponto ~97k. Com o próprio spread, `4 × ((47k..147k) + (60k..140k))` = **428k a 1,15M**; a faixa publicada `620-950k` é mais ESTREITA que a incerteza que o plano acabou de declarar.

**F9 — P3 — Nenhuma figura de §9 é reproduzível: janela relativa sem âncora.**
`--since 3d` é janela móvel. Hoje o papel assento dá 659,77 (plano: 655,23) e a mix dá 92,50/7,02/0,48 (plano: 92,57/6,97/0,45). Reproduz a DIREÇÃO, nunca o número.
*Mitigação:* `--since <ISO>` com data, ou o JSON gerado congelado sob `PLAN-175/evidence/` e citado pelo caminho (a regra da casa: figura GERADA, nunca digitada — aqui ela é gerada e depois digitada).

**F10 — P1 — A AC-1.7 é uma espera de calendário de 30 dias dentro de um plano que declara `external_wait: none`.**
§5:380: "a re-medição **aos 30 dias** é publicada E a decisão de Fase 2 é APLICADA… A Fase 1 não fecha no baseline", com Check `--since 30d`. §6:431 afirma "não há segundo lugar no corpo que afirme espera" e o frontmatter diz `eta_calendar: "mesmo-dia a D+1"` (:17). São duas seções que discordam sobre o mesmo fato — a classe que o round 1 chamou de C3.
*Mitigação:* ou a Fase 1 fecha no baseline (e a re-medição vira follow-up com plano próprio), ou o frontmatter reconhece a espera e a ETA deixa de ser D+1.

**F11 — P3 — Checks que não podem ficar verdes / não podem ficar vermelhos.**
(a) AC-1.4: `grep -n "decisao-b" .claude/plans/PLAN-175/decisions/` — o diretório não existe (rc=2, "No such file") e, mesmo existindo, `grep` sem `-r` sobre diretório não casa. (b) AC-1.2, perna 1, já está VERDE no HEAD antes de qualquer trabalho (rodei: rc=1, sem saída) — é guarda de drift, não critério de aceite da onda; e o padrão proibido não cobre `>=0,10` sem espaço nem a grafia com ponto decimal. (c) AC-0.6 e AC-1.5 estão corretos e podem ficar vermelhos hoje (verificado: `rag_router.py:32` carrega o nome do plano inexistente; `skill-index-build` só aparece na docstring de `_lib/frontmatter.py`).

**F12 — P3 — O progress log contradiz a ratificação.**
A última linha do log (:528) diz que o `external_wait: none` está "**PENDENTE** de ratificação do Owner". A ratificação existe (2026-09-06, «Sim, ratificar junto com o flip para executing»). Texto envelhecido em campo que decide sequenciamento.

## O que falta antes de executar (OQ para o Owner ratificar)

- **OQ-1 (F1):** data mínima de abertura da W2 sob `min_window_coverage_days = 90` — ou o número novo da guarda, com a razão.
- **OQ-2 (F2):** teto de gasto do plano e critério de morte por custo, derivados do `by_role` do `ceo-cost.py`, não de 8×(40..120) digitado.
- **OQ-3 (F3):** a unidade orçada é assento Fable 5.1 (medido) ou assento Opus 5 (declarado no `tier_mix_estimate`)?
- **OQ-4 (F4):** a poda pode decidir sobre um ledger com `chain_status` NÃO íntegro? Se não, a regra RECUSA nesse estado.
- **OQ-5 (F7):** minutos de CI/e2e e rodadas de cerimônia entram no `budget_usd_estimate`?
- **OQ-6 (F10):** a Fase 1 fecha no baseline, ou o plano reconhece a espera de 30 dias no frontmatter?
- **OQ-7 (F6):** quem entrega a perna de perfil do harness de instalação — a W3 deste plano ou o PLAN-171?

## Nota de escopo

Este parecer certifica COERÊNCIA DE DESENHO do texto do plano contra a árvore no HEAD. Ele não autoriza execução, não é rail entre fornecedores e não substitui a decisão 4.10 do Owner. Todos os comandos citados foram rodados em modo leitura; nenhum arquivo da árvore viva foi tocado.
