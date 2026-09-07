---
round: 3
archetype: LLM FinOps Architect
skill: llm-routing-and-finops
agent_persona: LLM FinOps Architect (Principal, advisory — NO VETO)
generated_at: 2026-09-07T02:10:00Z
---

## Verdict

ADJUST — **3 bloqueantes** (R-FIN1, R-FIN2, R-FIN3).

## Summary (≤ 3 bullets)

- **A cura da rodada 2 pegou.** Re-verifiquei em disco os itens de custo do
  consenso r2: `F = 97.292` (`CLAUDE.md:97`), Opus 5 5,00/25,00
  (`cost-table.yaml:85-87`), Sonnet 5 2,00/10,00 (`:110-112`), Haiku 4.5
  1,00/5,00 (`:115-117`), shares 0,80/0,20 (`:45-46`), `cost_table_valid_until:
  2026-09-13` (`:29`), 12 identificadores todos `claude-*`. A aritmética do §5
  fecha: 510-760k + 6-8×97.292 = 1,094-1,538M; 0,8×5+0,2×25 = 9,00/M; a mista
  70/25/5 = 7,29/M ⇒ 8,97-12,55. **C7 está curada na perna do orçamento.**
- **O que a cura não fechou é a perna de PRAZO da mesma chave C7**: a mesma
  revisão que criou W1c (espera o land de `w4b-ci-matrix`) e W3b (espera o
  PLAN-169, `status: executing`) deixou `external_wait: none` e
  `eta_calendar: mesmo-dia a D+1` intactos — o frontmatter contradiz o corpo
  em DOIS pontos novos que a própria cura introduziu.
- **E a cura de C6 parou no meio**: ela inventou K-8 e K-9 e deixou a única AC
  que exercita `--state --json` enumerando **sete** critérios contra uma tabela
  de **nove**. Os dois de fora são exatamente os que a cura criou para enxergar
  a rotina morta.

## Risks

### R-FIN1 — P1 — a AC do comando único cobre 7 critérios; a tabela publica 9, e os 2 que sobram são K-8 e K-9

`PLAN-176-model-currency-refresh.md:844-852` publica **nove** linhas `K-1..K-9`.
A caixa que fecha o comando de leitura diz, em `:364`, «serve os **SETE**
critérios de morte» e, em `:366`, «o teste enumera os sete critérios»; o `-k` é
`state_json_serves_all_seven_death_criteria` (`:370`, repetido em `:839`).

O defeito não é cosmético: K-8 (zero raias ativas) e K-9 (`ts` > 96 h ⇒ rotina
parada) foram **criados por esta mesma cura** (`:857-867`) porque «um limiar
contado só em ciclos é infalsificável quando a rotina PARA». Como escrita, a AC
fica VERDE com sete campos servidos — o teste que deveria provar que a morte é
visível é o único lugar onde a morte não é enumerada. É a classe já paga neste
repo: instrumento verde cuja PERGUNTA envelheceu.

Cura barata (uma linha): trocar «sete» por «nove» nos três sítios e renomear o
`-k` para `state_json_serves_all_nine_death_criteria`. Se K-7 (dono: Owner, «só
abre com ADR ratificado») não tem campo de estado, declarar isso na caixa e
pedir oito — o que não se pode é publicar nove e exercitar sete.

### R-FIN2 — P1 — `external_wait: none` é falso no HEAD, e `eta_calendar` não sobrevive a 4 cerimônias sob WIP ≤ 3

`:15` diz `external_wait: none` e `:16` diz `eta_calendar: "mesmo-dia a D+1"`.
O corpo diz o contrário, duas vezes, em texto que a rodada 2 acrescentou:

- `:678` — «**A W1c só abre depois do land do `w4b-ci-matrix`**». Esse pack é o
  **terceiro** na fila de WIP canônico ratificada pelo Owner
  (`PLAN-186/debate/owner-decisions-S347.md:55`, decisão 4.17: «No máximo 3 de
  dia», prioridade W1 → W6a → W4b).
- `:90` — «**Só a W3b espera o item (iv)**» do PLAN-169, cujo
  `status: executing` (`PLAN-169-closure-and-cross-session-evolution.md:4`).

Duas esperas externas ⇒ `external_wait: none` é uma afirmação falsa em disco, e
é a MESMA chave-classe que o C7 do round 2 mandou reconciliar (a cura arrumou
`budget_tokens`/`budget_sessions`/`budget_usd` e não voltou às duas vizinhas).
Some-se que o plano tem agora **quatro** pernas canônicas (W0b, W1b, W1c, W3b),
cada uma com cerimônia + 2 rodadas de trilho (`:903-907`): sob «no máximo 3
canônicos de dia», quatro assinaturas não cabem em «mesmo-dia a D+1» nem no
melhor caso. Cura: `external_wait: "W1c ⇐ land de w4b-ci-matrix; W3b ⇐ PLAN-169
W4.3 item (iv)"` e um `eta_calendar` em dias, derivado das 4 assinaturas.

### R-FIN3 — P1 — «o valor em dólares é TETO» é falso sobre o conjunto que o próprio plano declara selecionável

`:915` afirma: «**O valor em dólares é TETO** […] total × preço do Opus 5»,
9,00/M ⇒ 9,84-13,85. Opus 5 **não é** o preço máximo do conjunto que o plano
adota como autoridade. Medido: `AVAILABLE_MODELS_WORKING_SET` do ADR-149 inclui
`claude-fable-5` e `claude-fable-5-1`, e os dois estão em `cost-table.yaml:65-69`
e `:70-74` a **10,00/50,00** ⇒ blended 0,8×10+0,2×50 = **18,00/M**, exatamente
2× o número usado. A semântica do próprio ADR-149 é que o working set é «the set
of model ids the harness may select on ANY surface». Um teto sobre o conjunto
inteiro é **19,7-27,7 USD**; o piso re-pago sozinho (584-778k, declarado «100 %
contexto do CEO») já custaria 10,5-14,0 USD — acima do teto publicado.

O número de 9,00/M é defensável, mas como ESTIMATIVA SOB O PIN, não como bound:
o pin de sessão é `model: "claude-opus-5"` (`.claude/settings.json:772`). Cura de
uma linha: «teto **sob o pin `claude-opus-5`** (`settings.json:772`); sobre o
conjunto de trabalho inteiro o teto é 18,00/M ⇒ 19,7-27,7 USD». Rotular ponto
como bound é o defeito; a evidência já está toda no plano.

### R-FIN4 — P2 — o orçamento em dólares cobre um fornecedor; quatro das oito ondas são gatilhadas por outro, cuja quota não é preço nenhum

`:903-907` inclui no trabalho «a sua cerimônia + as **2 rodadas de trilho**» por
perna canônica — 4 pernas × 2 = **8 invocações do revisor externo**. Nenhuma
delas aparece em `budget_usd_estimate`, e não pode aparecer: `cost-table.yaml`
tem 12 identificadores, **todos `claude-*`** (medido; o próprio plano o diz em
`:400-408`). O trilho roda numa quota SEPARADA, com dois modos de falha já
medidos neste repo e nomeados nas regras da noite («at capacity» = rodada morta;
«usage limit» = quota morta). Consequência FinOps: o item que decide o
CALENDÁRIO de 4 das 8 ondas tem custo zero no plano e disponibilidade não
modelada. Cura barata: uma linha em §5 — «8 rodadas de trilho contra quota
externa não-Anthropic, fora do envelope em dólares; indisponibilidade dessa
quota adia onda canônica, não a encarece».

### R-FIN5 — P2 — todo dólar do plano vem de uma tabela que expira em 6 dias, e a linha do Sonnet 5 já está declarada STALE pelo ADR-149

Insumos do §5 saem de `cost-table.yaml`, que traz `cost_table_valid_until:
2026-09-13` (`:29`) e `last_verified_at: 2026-06-15` (`:34`). Hoje é 2026-09-07:
**6 dias** de validade contra `budget_sessions: 6-8` e duas ondas bloqueadas em
land alheio (R-FIN2). Pior, o ADR-149 §A2.3 (`:285-290`) declara que «the sticker
rows in `cost-table.yaml` / `docs/cost-of-operation.md` are therefore stale from
today» para o Sonnet 5 — a MESMA linha `:110-112` de que sai o 7,29/M da
derivação mista. O plano nomeia a expiração só pela perna de «raia ativa»/K-8
(`:869-874`, §6) e nunca pela perna do próprio orçamento. Cura: declarar que as
figuras em dólares são válidas até 2026-09-13 e re-derivá-las no primeiro land
posterior — a rota já existe (`--check-pricing-staleness`, `cost-table.yaml:27-28`).

### R-FIN6 — P2 — com 1 ciclo/24 h, nenhum critério de qualidade pode disparar dentro do calendário declarado

`:121-129` fixa a cadência-alvo em **um ciclo por 24 h** (a varredura é invocada
pelo operador; `grep -c 'schedule:'` = 0). Contra isso: K-1 pede 8 ciclos
(`:844`), K-5 dispara «a cada 4 ciclos» (`:848`), K-3 e K-9 pedem 96 h
(`:846`, `:852`). Piso: **8 dias** de operação até o primeiro veredito de
qualidade — e `eta_calendar` diz «mesmo-dia a D+1» (`:16`). Um plano declarado
DONE em D+1 terá n = 1 ciclo, que não separa «detector funciona» de «detector
sempre verde»: a hipótese nula e a alternativa produzem a mesma observação. O
critério ESTÁ pré-registrado antes do primeiro número (bom, e é raro), mas a
janela de observação não foi orçada. Cura: separar «ondas entregues» (D+1) de
«critérios de morte avaliáveis» (D+8), e dizer qual dos dois fecha o plano.

### R-FIN7 — P2 — a definição de «raia ativa» torna o fornecedor do trilho permanentemente INERTE para o detector

`:400-408`: raia ativa = membro do working set do ADR-149 **E** com linha de
preço em `cost-table.yaml`; sem linha de preço ⇒ INERTE por construção. Como a
tabela é 100 % `claude-*` (medido), **nenhum lançamento da linha do revisor
externo é detectável por este plano — nunca, por desenho**. E o §8 do próprio
plano (`:989-990`) inventaria, como bug VIVO, «forma do revisor externo
congelada em 0.139 contra binário 0.144.6»: a única deriva de currency que o repo
já MEDIU está na raia que o detector não pode ver. Isso não invalida o desenho
(fail-closed é a decisão certa contra raia vazia), mas é ROI que precisa ser
dito: 1,09-1,54M de tokens compram vigilância sobre a raia que já passa por
cerimônia manual. Cura barata: uma linha de relatório «fornecedor com adaptador
vivo e sem linha de preço ⇒ INERTE, listado nominalmente», para que a lacuna
apareça em cada ciclo em vez de ser silêncio.

### R-FIN8 — P2 — o multiplicador de sessões é 51-54 % do orçamento e é o único termo sem base medida

`584-778k` de piso contra `1,094-1,538M` de total = **51 % a 54 %** do envelope
vem de `budget_sessions: 6-8` (`:11`), um número escolhido, não derivado. São 8
ondas e 4 cerimônias: uma sessão por onda, sem folga para rodada de trilho
vermelha. Em 11 sessões o piso sozinho é 1,07M — o limite INFERIOR do total
publicado. O plano já sabe disso e escreve a cura em `:909-914` («`F` não é um
ponto, é uma banda… spread de 51,7 % da média… é dele que a próxima revisão deve
gerar a faixa em vez de digitá-la», instrumento em
`PLAN-179/w0/gateboot_repay.py`). Peço só que a próxima revisão execute a própria
recomendação: gerar a faixa com o instrumento e publicar `[p50, p90]` de sessões.

### R-FIN9 — P3 — a faixa em dólares publicada não se reproduz da faixa de tokens publicada

`:919-923`: «1,09M a 1,54M ⇒ **9,84 a 13,85** dólares». Com a taxa do próprio
parágrafo (9,00/M): 1,09 × 9 = **9,81** e 1,54 × 9 = **13,86**. Os endpoints
publicados vêm dos valores não-arredondados (1,094 e 1,538), que o cabeçalho não
carrega. É pequeno e é a assinatura de figura DIGITADA — o mesmo defeito que
`:913` promete não repetir. Cura: publicar a faixa com uma casa a mais
(1,094-1,538M) ou gerar as duas figuras juntas.

## Respostas ao consenso do round 2

- **C1 (conjunto-vermelho) — CURADO.** O arquivo nasce na W0a, livre, com a
  bandeira `--expected-reds` e controle de encolhimento (`:376-397`).
- **C2 (W1b 5×9) — CURADO.** W1b = 4 caminhos / 7 caixas; W1c = 4 caminhos /
  4 caixas; registro T com AC própria (`:700-716`).
- **C3, C4, C5 — CURADOS** em disco (comandos vermelhos na condição proibida;
  egresso degradado ao par host+`egress_class`; alvos reais da W3a/W3b).
- **C6 — PARCIAL:** ganhou cadência e as duas pernas, mas ver **R-FIN1**.
- **C7 — PARCIAL:** perna do orçamento curada e re-verificada; pernas
  `external_wait` e `eta_calendar` não (ver **R-FIN2**).
- **C8 (`depends_on` em plano executando) — CURADO** e melhor do que pedido: §0
  nomeia o entregável e isola a espera à W3b.

## O que falta antes de executar (OQ — o Owner ratifica, eu não decido)

As três OQ do §5b (`:961-968`) estão bem-postas: rota barata executada, rota cara
precificada. Nenhuma delas bloqueia onda. Acrescento **duas perguntas de custo**
que o texto não faz, e que são de decisão, não de cura:

1. O teto em dólares deve ser declarado **sob o pin** (9,00/M) ou **sobre o
   working set** (18,00/M)? A escolha muda o teto por 2× (R-FIN3).
2. As 8 rodadas de trilho contra quota externa entram no envelope como
   *disponibilidade* (risco de calendário) ou ficam fora por completo (R-FIN4)?

## BLOCKING count

**3** — R-FIN1, R-FIN2, R-FIN3. Todos com cura de uma a três linhas, todos
verificáveis com um comando. Os P2/P3 são melhorias de honestidade de número e
de ROI, não impedimentos.
