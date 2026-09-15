# Decisões do Owner — S353 (2026-09-15, ~20:45–20:55 BRT)

> Registro VERBATIM das 8 respostas dadas por `AskUserQuestion` na sessão S353,
> depois do boot pós-GA v1.4.0. Uma linha por decisão, rótulo copiado do
> instrumento; a leitura do CEO vem marcada como tal. Copiadas para os planos
> de destino na mesma sessão. Precedente: `owner-decisions-S347.md`,
> `owner-decisions-S348-c.md` (mesmo diretório).

| # | Pergunta (resumo) | Resposta do Owner (verbatim) | Contra a recomendação? | Destino |
|---|---|---|---|---|
| 1 | Baseline N=20 desta noite: quais modelos | **«Todos os 7 modelos»** | sim (rec.: 3 novos + âncora Haiku) | memória `project-model-baseline-matrix-next-terminal`; sem plano ativo (PLAN-134 arquivado) |
| 2 | AC-13 (detector de drift de roteamento, pack livre, 35 rodadas) landar sem novo Codex | **«Sim, landar livre (Recomendado)»** | não | PLAN-186 (progress log) |
| 3 | PLAN-171: re-escopar para fechar (W1 pelo 188, W2 follow-up) | **«Manter como está»** | sim (rec.: fechar com re-escopo) | PLAN-171 (registro de execução) |
| 4 | Ordem das assinaturas de amanhã (toolkit W0a × ponteiro 183 W1) | **«As duas na mesma manhã»** | n/a (rec.: toolkit primeiro) | PLAN-188 e PLAN-183 (progress log) |
| 5 | Branch local `post-rc4-hold-artifacts` (1 commit de 16/08) | **«Apagar (Recomendado)»** | não | executado nesta sessão: `git branch -D`; SHA preservado abaixo |
| 6 | PLAN-189 OQ-1: W0 e W3 na mesma assinatura? | **«W0 primeiro, sozinha (Recomendado)»** | não | PLAN-189 §Open questions |
| 7 | PLAN-189 OQ-2: definição operável de «mesma classe» | **«Propriedade OU superfície, julgado pelo autor (Recomendado)»** | não | PLAN-189 §Open questions |
| 8 | PLAN-189 OQ-3: telemetria do rail (W2) agora ou depois | **«Fazer agora junto»** | sim (rec.: esperar W0/W1) | PLAN-189 §Open questions |

## Leituras do CEO (não são decisões)

- Decisões 6 e 8 combinadas: W0 (regra de classe no `PROTOCOL.md`) vai numa
  assinatura própria e pequena; W2 (telemetria, toca `_lib/audit_emit.py`,
  canônico) entra no programa AGORA e viaja com a W1 na assinatura seguinte, não
  com a W0. Se o Owner quiser W2 na mesma assinatura da W0, é decisão nova.
- Decisão 4: as duas cerimônias (p188-w0a e p183-w1-pointer) ficam prontas
  como blocos SIGN independentes; a ordem de execução na manhã é livre, mas o
  toolkit W0a primeiro continua sendo a recomendação, porque a W0b (livre) só
  landa depois dela.
- Decisão 3: o PLAN-171 segue `executing` com W0 + W1 + W2; a W1 continua
  esperando o toolkit do PLAN-188; o item do censo que falta (controle do
  caminho de bloqueio de `check_cost_envelope.py`) segue livre e pode landar.
- Decisão 1: instrumento intacto entre os 7 modelos; fumaça de 1 tarefa antes
  do primeiro; ordem decrescente de importância (opus-5, fable-5-1, sonnet-5,
  opus-4-8, fable-5, sonnet-4-6, haiku-4-5). Quota: conta NOVA dedicada à
  noite (Owner, 20:5x) — a restrição semanal de 78 % desta conta não se aplica.

## Branch apagado

`post-rc4-hold-artifacts` apontava para **`99b089441f01`** (2026-08-16, «chore(PLAN-177
rc.4): gerador do envelope … pós-tag, branch de hold»), 1 commit à frente e 503
atrás de `origin/main`. Recuperável por `git branch post-rc4-hold-artifacts 99b089441f01`
enquanto o objeto existir no repositório.
