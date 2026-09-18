# PLAN-191 — rail round 1 (Codex GPT-6 Astra, `codex review --uncommitted`, 2026-09-18)

**Sujeito revisado:** diff não commitado do `PLAN-191-cheap-brain-tier-tournament-cascade-triage.md`
(versão ANTERIOR às quatro edições do braço Haiku-sinais/`$.model.classify`) + `CLAUDE.md` (linha do
Jev em §5). Codex CLI 0.155.0. Saída bruta preservada no scratchpad da sessão
(`codex-review-plan191.out`, 249 KB); só o bloco de achados está transcrito aqui.

**Veredito:** `REJECT — insufficient sampling, incomplete or conflicting decision rules, acceptance
metrics that do not establish the stated objectives. Read-only freshness and numerical-claim checks
passed.` Cinco P2, nenhum P0/P1.

| # | achado (Codex) | classe | cura (mesma sessão) |
|---|---|---|---|
| 1 | W0: 10 tarefas × 3 repetições = 30 por MODELO, mas 3 por tarefa×modelo; `ADR-064:108-109` exige n ≥ 30 por célula papel×tipo — agrupar tarefas heterogêneas não satisfaz; ou aumenta a amostra ou declara piloto | pré-registro com claim maior que a amostra | W0 renomeado **PILOTO**; a evidência do PLAN-186:29 passa a ser W0.c (células por tipo, n ≥ 30); adendo ao 186 reescrito «piloto, não equivalente» |
| 2 | W2: com exatamente 1-2 tarefas qualificadas nem a regra de cancelar nem a de abrir se aplica — decisão pós-hoc | partição incompleta | partição TOTAL: 0 ⇒ morre; 1-2 ⇒ W0.b + reaplicação ÚNICA da mesma regra; ≥ 3 ⇒ abre. W0.b passa a disparar com 0-2 |
| 3 | W1: o mesmo `verify` decide aceitação da cascata E sucesso do benchmark ⇒ não enxerga os próprios falsos positivos; **`t09_readme_doc.verify` devolve 1,0 para `# add subtract multiply usage`** | oráculo julga a si mesmo | escape redefinido = aceito pelo `verify` e reprovado por juiz CEGO ao braço (grader Opus com rubrica, ou pair-rail) sobre TODAS as saídas aceitas de B/C + amostra igual de A; `t09` consertado ou excluído ANTES de rodar |
| 4 | W1: «custo ≤ 0,67 × A» passa sem cortar tokens (Sonnet = 40 % do preço de Opus a volume igual); API-equivalente não prova quota | métrica ≠ objetivo | SUCESSO exige **tokens ≤ 0,67 × A** E custo ≤ 0,67 × A; quota lida antes/depois; «preço cai, quota não» vira resultado separado, não sucesso do Goal 1 |
| 5 | W3: sucesso permite «≥ 3 pp OU −30 % minutos», parada diz «empate ≤ 3 pp ⇒ nenhuma lane» — o mesmo resultado (Δ = 3 pp; ou tempo −30 % com empate) produz vereditos opostos | regras que se contradizem | regra ÚNICA: nasce sse `Δ ≥ 3 pp` OU (`T ≤ −30 %` E `Δ ≥ −1 pp`), `Δ` contra o MELHOR local/nativo; Regra de parada espelha byte a byte |

**Colateral fora do plano:** o achado 3 expõe um defeito REAL em `.claude/eval/tasks/t09_readme_doc.py`
(verificador aceita README só com título) — entra na lista de mecanismos inertes/fracos
(`project-inert-mechanisms-s355`) e é pré-condição do W0.

**Regra de parada desta rodada (pré-registrada, S349/S354):** rodada final com anexo — NO-GO só por
condição FALSA ou P0; P1 novo = anexo. Esta rodada teve só P2 de texto ⇒ curas aplicadas; a rodada 2
corre sobre o diff curado (que inclui as quatro edições que a r1 não viu) e é a FINAL.
