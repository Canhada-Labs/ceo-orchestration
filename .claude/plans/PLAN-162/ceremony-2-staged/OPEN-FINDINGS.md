# Findings ABERTOS ao fim da S292 — o que o pair-rail apontou e eu NÃO fechei

> **Por que este arquivo existe.** O rail cross-model rodou **8 rounds**
> sobre este pack (56 findings, todos triados). A maioria foi corrigida; o
> que sobrou está aqui, nomeado, com o motivo de não ter sido fechado. Uma
> rodada limpa é claim, não prova — e uma rodada com achados escondidos é
> pior. O Owner decide o que fazer com cada item; nenhum deles impede a
> cerimônia de rodar, e nenhum é silencioso.

## Critério de parada usado (declarado, não improvisado)

Parei quando a natureza dos achados mudou: rounds 1-5 acharam **bypasses de
segurança** (todos fechados); rounds 6-8 acharam **precisão documental e
coerência interna** — e boa parte dos achados do r8 foi *gerada pelas minhas
próprias correções do r7*. Isso é ponto de equilíbrio instável, não defeito
profundo remanescente. O pack é STAGED (não landa nada sozinho) e o Owner o
revisa antes de assinar, então entregar com esta lista é melhor que iterar
até um "clean round" que o próximo round desmentiria.

---

## 1. Deadline fail-closed vs contrato publicado — **DECISÃO DO OWNER**
*(r3 P1, r5 P1, r7 P1, r8 P1 — quatro rounds, o mesmo ponto)*

O `plan162-w2-fixes.patch` implementa deadline **fail-CLOSED**; `CLAUDE.md`
§4 / `AGENTS.md` §1 dizem que timeout de hook é infra ⇒ **allow**.
**Não fechei porque não é meu para fechar.** Draft pronto com as duas
leituras e o que entra no mesmo commit em cada caso:
`ADR-186-hook-deadline-policy-DRAFT.md` §4 (em branco, aguardando escolha).
**Bloqueia a Fase B** — e só ela; as demais fases andam.

Sub-item do r8 (P2, dentro da mesma decisão): se ficar (i) fail-closed, o
estouro do deadline deve **emitir evento de auditoria**, não só bloquear —
senão o bloqueio some da cadeia HMAC. Entra no commit da escolha.

## 2. Matcher NF-08 — residuais de invocação, ACEITOS E REGISTRADOS
*(r2, r4, r5, r6 acharam bypass; r7/r8 pediram para parar de alegar o que ele não faz)*

Quatro rounds seguidos acharam bypass no matcher (env/sudo → brace → xcrun →
assignments compostos). Cada fix foi real; cada rodada seguinte achou outro.
**A causa não é descuido: parsing estático de bash não produz matcher
completo.** Está medido no `nf08-invocation-guard-NOTES.md` §7 residual 5 —
um **interpretador renomeado** (`./zz-interp <toggle> on`) passa pelo matcher
E pelo self-path guard, porque o script que roda **é** o canônico.

Decisão: o matcher fica como defesa-em-profundidade; **as claims foram
corrigidas** nos três textos (patch header, command-doc, runbook) para dizer
o que ele faz de fato. O perímetro real é `defaultMode` + allowlist de Bash
da sessão corrente. Residuais nomeados no NOTES §7 (1-5).

**Se o Owner quiser fechar de verdade:** a rota não é mais um round de
matcher — é remover a capacidade (ex.: o toggle deixar de ser um script
invocável pelo rail, virando ação de um canal que o modelo não alcança).

## 3. `p95` não estratificado por budget efetivo *(r8 P1 — instrumento)*

Com `timeout_ms` no evento, cada review passou a ser pontuada contra o SEU
budget (r6 P2, feito). Mas `p95_interpolated`/`p95_empirical` continuam
calculados sobre a amostra inteira, misturando sessões de budgets
diferentes. **Não fechei** porque hoje **todas as 41 linhas são legadas**
(pré-campo) — a estratificação seria código sem dado que a exercite. Vira
necessária no primeiro dataset pós-AMEND-2 com budgets mistos; o `--json`
já expõe `rows_scored_by_event_budget` / `rows_scored_by_cli_budget` para
detectar exatamente quando isso acontecer.

## 4. Coerência do runbook sob as combinações de decisão *(r8 P1 ×2)*

As fases são separáveis e as decisões (NF-08 a/b; sonda GO/NO-GO; deadline
i/ii) multiplicam os caminhos. Corrigi os que quebravam execução (`git add`
de glob inexistente, pytest de arquivo ausente, contagem literal → derivada
do disco). **Permanece:** o runbook não enumera exaustivamente as 12
combinações. Mitigação: cada fase tem gate próprio e o `apply-counts.sh`
agora deriva o alvo do disco com guard fail-closed, então uma combinação não
prevista **falha alto** em vez de landar torta.

## 5. `check_budget` skip-silencioso — pré-existente, fora do pack

Com 2+ planos ativos o gate de budget é pulado com breadcrumb (8 linhas em
`audit-log.errors`). Já rastreado no PLAN-162; resolve-se quando um dos
planos sair do conjunto ativo (a própria cerimônia faz isso).

---

## O que NÃO ficou aberto (fechado com prova nesta sessão)

P0 case-fold nos dois rails · partição de cache + deadline (impl.) · GPG e
git-anchor limitados pelo budget restante · trust-anchor por CONTEÚDO
ancorado · NF-07 (emit de `night_mode_toggled` — 30 sites, oráculo `ast`) ·
NF-09 (`off` mentindo `applied`) · redação de artifact fail-closed + sem
truncar em 64 KiB · kill-rate do mutation-gate lido do junitxml · tournament
`2>&1` · labels do reality-ledger · ordenação cronológica dos logs
rotacionados · budget do instrumento obrigatório e explícito · sentinel no
path/formato que o guard realmente descobre · `Approved-By` · errexit no
runbook · paths pessoais removidos (repo público).
