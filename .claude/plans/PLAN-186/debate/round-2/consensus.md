---
plan: PLAN-186
round: 2
rounds_synthesized: [round-1, round-2]
agents_considered: [Critic-A, Critic-B, Critic-C]
decisions_revised_in_plan:
  - "frontmatter — W1 e W4 reclassificadas como cerimônia GPG; budget_tokens RE-DERIVADO a partir de F medido + trabalho; +budget_tokens_gateboot; budget_sessions 9-12 → 15-18; tier_mix_estimate.seat descreve o plano inteiro; PLAN-184 vira «coordena com», não depends_on"
  - "§2b — partição TOTAL: terceira linha (pesquisa/leitura com pergunta FIXADA → Sonnet 5) e censo dividido em mecânico (EXECUTA) vs desenho do predicado (DEFINE); a regra é NORMATIVA já na W1; removida a frase falsa «.github/workflows/** é livre»"
  - "§3 W1 — cerimônia GPG; gate na OQ-7 com escape declarado; o derivador em disco é INSUMO (eixo antigo) e é re-derivado sob §2b com tabela por sítio publicada"
  - "§3 W3 — gatilho de FIM da transição de dois ids; piso efetivo = membro mais fraco da allowlist, escrito"
  - "§3 W4 — cerimônia GPG; forma trocada: PRIMEIRO medir a deleção dos steps duplicados, depois decidir a matriz; censo do nome de check DERIVADO por comando; checkout fora do composite; AC-6 nomeia o job-bound"
  - "§Acceptance criteria — AC-11 re-escrito (classe de runner + instrumento próprio); +AC-13 (detector permanente), +AC-14 (classificador), +AC-15 (sonda US6); lista reordenada"
  - "§Open questions — OQ-6 ganha segunda cláusula (composição + âncora, PLAN-SCHEMA:328 nomeado); +OQ-9 (W1 e W4 numa cerimônia ou em duas)"
synthesized_at: 2026-09-02T21:10:00Z
synthesized_by: VP Engineering (synthesizer, anonymized input) for CEO
---

# PLAN-186 — consenso do round 2

Três críticos, três `ADJUST`, nenhum `REJECT`. Dos 26 must-fix do round 1: **20
resolvidos, 6 parciais, 0 abertos**. O round 2 trouxe **13 must-fix novos, 12 após
dedup**. Toda claim citada abaixo foi verificada em disco antes de virar ajuste.

## Must-fix do round 1 — estado consolidado

| # | tema | crítico | estado |
|---|---|---|---|
| 1 | rota papel→model id antes dos literais | A | **PARCIAL** — censo virou W0-US5/AC-12, tabela é OQ-7; faltava gate na W1 |
| 2 | raio da W3 (allowlist + dicts congelados) | A, B, C | RESOLVIDO |
| 3 | precedência `inherit` × pin | B, C | RESOLVIDO (W0-US4 + AC-10, W3 gated) |
| 4 | regra de effort / eixo da matriz | A, B, C | **PARCIAL** — eixo trocado curou a contradição, criou três novas |
| 5 | 6 sítios do Step 0 | A | RESOLVIDO |
| 6 | cobertura e re-precificação da W1 | A, B | **PARCIAL** — AC dividido; o derivador segue no eixo antigo |
| 7 | OQ-5 vira sonda | A, C | RESOLVIDO |
| 8 | `CONSUMES:` com residual de valor-de-retorno | A | RESOLVIDO |
| 9 | reconciliação com `parallelization-by-default` + hook | A | RESOLVIDO |
| 10 | envelope de custo / unidade de `budget_tokens` | B | **PARCIAL** — unidade resolvida; CALIBRAÇÃO não |
| 11 | desenho do A/B (ABBA, custo de troca, censura, MDE) | B | RESOLVIDO |
| 12 | AC-1 reancorado | B | RESOLVIDO |
| 13 | `fail-fast: false` + gate de forma | C | RESOLVIDO |
| 14 | baseline de node-ids pela união dos dois passes | C | RESOLVIDO |
| 15 | composite bootstrap + `shasum -c` do ADR-192 | C | **PARCIAL** — o checkout não pode viver dentro do composite |
| 16 | nome de job preservado | C | **PARCIAL** — 3 sítios afirmados, o disco tem ≥ 5 |
| 17 | toolchain replicado com assert | C | RESOLVIDO |
| 18 | enforce de `model` com rota de recuperação | A, C | RESOLVIDO |
| 19 | dois ids no piso VETO | A, B, C | RESOLVIDO |
| 20 | sonda de concorrência re-desenhada | A, B, C | RESOLVIDO |
| 21 | sonda de hookabilidade antes do rail | C | RESOLVIDO |
| 22 | correlation id nos dois projetos | A, C | RESOLVIDO |
| 23 | critério de morte falsificável | B | RESOLVIDO |
| 24 | 4 pins de IC em `claude-sonnet-4-6` | B | RESOLVIDO |
| 25 | §1 auto-contraditório (RAZÃO vs ABSOLUTO) | B | RESOLVIDO |
| 26 | delta de runner-minutos medido e gated | C | **PARCIAL** — AC-11 sem instrumento e sem dependência declarada |

## Consensus findings (2+ agents flagged)

### D1 — CRITICAL — o derivador da W1 codifica o eixo que §2b substituiu (Critic-A, Critic-B)

Verificado em `.claude/plans/PLAN-186/w1/apply-w1-explicit-model.py`: o sítio
`hygiene:${d.key}` de `nightly-hygiene.js` recebe `claude-sonnet-5` sob o rótulo
`finder/pesquisa/censo`, e `lane:${vendor}` de `council-audit.js` recebe
`claude-sonnet-5` sob `finder/pesquisa [DUVIDA]` — o próprio derivador registra a
dúvida. §2b põe **censo** na linha DEFINE → `claude-opus-5`. O AC-3a («campo `model`
da resposta servida») fica VERDE sobre a classificação antiga aplicada sob o nome da
regra nova. É a forma «material curado no vivo é invisível à sombra que o rail
revisa», invertida: o material precede o plano e discorda dele em bytes.

**Severidade acordada:** CRITICAL para a conformidade, HIGH para a wave.
**Mitigação:** o derivador em disco é declarado INSUMO (eixo antigo). A W1 re-deriva
a classificação dos 10 sítios sob §2b e PUBLICA a tabela por sítio; o AC-3a ganha a
perna que compara `model` servido contra a classe §2b do sítio. Consequência de custo
registrada: a W1 passa a ser wave de CORREÇÃO DE ROTEAMENTO, não de economia, até o
C2 re-derivado dizer outra coisa.
**Landa em:** §2b, §3 W1, AC-3a.

### D2 — MEDIUM — o orçamento não sobrevive à própria aritmética (Critic-A, Critic-B)

`budget_tokens: 850k-1.45M` e `budget_sessions: 9-12` são as strings do round 1 sob
escopo materialmente maior (W0 ganhou três US, W1 ganhou quatro itens). E o piso de
boot refuta o limite inferior: `F` medido em `.claude/plans/PLAN-179/w0-measurement.md:539`
= **97.292 tokens** (controle cold-F 97.097, n=41, spread 51,7 % da média). 9 × 97k =
**875k**, acima dos 850k declarados. Verificado também `PLAN-SCHEMA.md` §328: «Each new
session pays gate-boot cost **~27k tokens**» — 3,6× abaixo do medido, e é a constante
que converte `budget_sessions` em tokens para todos os ~15 planos do repo.

**Severidade acordada:** MEDIUM (o número está errado, não a estrutura).
**Mitigação:** `budget_tokens` passa a ser TRABALHO, re-derivado wave a wave com o
escopo novo e o custo de cerimônia; `budget_tokens_gateboot` entra ao lado, explícito;
`budget_sessions` re-derivado. A OQ-6 ganha segunda cláusula: além de qual definição é
normativa, **o que compõe o campo e qual é a âncora**, com `PLAN-SCHEMA:328` nomeado
como sítio de folclore a curar em carona repo-wide (o valor honesto é FAIXA, não
constante).
**Landa em:** frontmatter, OQ-6.

### D3 — HIGH — o eixo novo de §2b não é total e não foi re-precificado (Critic-A, Critic-B)

§2b tem duas linhas produtivas, DEFINE e EXECUTA. **«Pesquisa/leitura» não está em
nenhuma** — era linha própria na matriz antiga. Duas consequências materiais: (a) os
quatro pesquisadores em Sonnet 5 que produziram os relatórios 01-04, citados pelo
próprio estudo como evidência de que Sonnet 5 entrega citação verificada, caem em
«censo» → Opus 5 e viram violação RETROATIVA da política que a evidência deles
sustenta; (b) no corpus de workflows deste repo, finders, censos e lanes são todos
produtores de claims — a partição por incerteza de especificação empurra a maioria dos
sítios para Opus 5, e nenhum número do plano reflete isso. Uma partição que não cobre
o domínio não classifica.

**Severidade acordada:** HIGH. **Mitigação:** partição TOTAL com terceira linha —
«pesquisa/leitura com pergunta FIXADA pelo CEO» → `claude-sonnet-5` — e «censo»
dividido em MECÂNICO (enumerar sob predicado dado → EXECUTA) versus DESENHAR O
PREDICADO (→ DEFINE). Com isso o `hygiene:${d.key}` sobrevive em Sonnet 5 por MÉRITO,
não por inércia, e a evidência do estudo deixa de ser retroativamente ilegal.
**Landa em:** §2b, §3 W1, `tier_mix_rationale`.

## Single-agent insights kept

1. **K18 (Critic-A) — W1 e W4 são cerimônia GPG, rotuladas «livre». O achado mais
   material do round.** Verificado em `.claude/hooks/check_canonical_edit.py`:
   `.github/workflows/*.yml` e `*.yaml` na lista canônica (`:183-185`), e
   `.claude/workflows/**/*.js` em `:331`, cujo comentário `:329-330` diz literalmente
   «Cost accepted at ratification: authoring ANY `.claude/workflows/*.js` becomes a
   sentinel ceremony». A W1 edita os quatro `.claude/workflows/*.js`; a W4 reescreve
   `validate.yml` e `smoke-install.yml`. O plano chamava as duas de «livre» e
   `external_wait` só reconhecia espera de GPG na W3. Agravante interno verificado: o
   próprio `w1/DESIGN-W1-S339.md` §3 (`:108-124`) já descreve LAND com `ANCHOR_SHA`,
   sentinel e assinatura do Owner, no molde `OWNER-S338-FABLE51-LAND.sh` — o material
   sabia o que o plano não dizia. Consequência operacional: **nenhuma das duas pode
   LANDAR numa night-run.** Aceito integralmente.
2. **K19 (Critic-A) — o censo do nome de check afirma conjunto fechado que o disco
   refuta.** Derivação executada agora: `RELEASE.md:258`, `docs/BRANCH-PROTECTION.md:104`,
   `templates/docs/BRANCH-PROTECTION.md:44`,
   `templates/.github/workflows/validate.yml.template:33` e o próprio
   `.github/workflows/validate.yml:30`, mais `PLAN-184:128` e `:1100`. São **≥ 5**, não
   três, e o K16 já havia crescido de 2 para 3 no round 1. Classe
   `feedback-closed-sets-must-be-derived-not-recalled`. Aceito: a lista sai, entra o
   COMANDO de derivação, executado no LAND.
3. **K20 (Critic-C) — o mecanismo escolhido para o Validate é o mais caro dos dois, e
   o barato é uma deleção.** Verificado: `hook-tests-python-matrix` (`:1606`, `runs-on: Ceo`)
   roda no `push` em 3.9 **e 3.12** o comando
   `pytest .claude/hooks/tests/ .claude/scripts/tests/ .claude/scripts/optimizer/tests/`
   nos dois passes (`:1636-1646`) — a união exata dos dois steps mais caros do job
   `validate`: «Run Python hook unit tests» (`:454`, 5m57s) e «Run Python script unit
   tests» (`:539`, 8m05s). São 14m02s dos 22m22s. Ambas as rotas param no MESMO piso de
   10m39s, que pertence a um job fora do escopo da W4. Aceito: **medir a deleção
   primeiro**. Refinamento do sintetizador: o delta de ambiente é DUPLO, não simples —
   `PYTHONPATH: "."` existe no matrix e falta nos dois steps, e `CEO_HOOK_ADAPTER: claude`
   existe no step de hooks (`:455-456`) e falta no matrix. A deleção tem de declarar os
   dois.
4. **K21 (Critic-C) — `validate.yml` não tem nenhum `if: always()`.** Contagem
   confirmada: zero. Hoje um step vermelho impede os posteriores de rodar, logo a
   justificativa REAL do split é atribuição independente de falha, não velocidade. Fica
   escrita na wave: as duas rotas são complementares.
5. **K22 (Critic-C) — o composite não pode conter o `actions/checkout`.** Referência
   local (`uses: ./.github/actions/...`) exige o repositório já em disco. O checkout é o
   primeiro step de cada leg, fora do composite, e o gate asserta DUAS coisas: checkout
   pinado + uso do composite. Aceito.
6. **K23 (Critic-C) — AC-11 mede minutos sem distinguir runner pago de grátis.**
   Verificado: `validate.yml:36` e as duas matrizes em `runs-on: Ceo` (larger runner
   pago por budget de org); `smoke-install.yml:196` em `ubuntu-latest`, gratuito em repo
   público. Um AC único sobre «runner-minutos totais» reprova a matriz do Smoke por um
   número que custa zero e passa folgado no Validate, que é onde o dinheiro está.
   Aceito: AC-11 denominado por CLASSE de runner.
7. **K24 (Critic-C) — o AC-11 ancora numa base de custo que o PLAN-184 declara
   não-derivada.** Verificado: `PLAN-184` em `status: draft`; `[P0][US4]` (`:959`,
   baseline de confirmação) ABERTO; `[P0][US5]` (`:970`) com os números marcados
   `NÃO-DERIVADOS` (`:979`); endpoint clássico de billing em HTTP 410 (`:43`, `:1272`).
   Aceito: o AC-11 ganha instrumento PRÓPRIO — soma por classe de runner via
   `gh run view <id> --json jobs` cruzada com o label do runner — e compara contra
   baseline LOCAL de 3 runs verdes pré-matriz. O PLAN-184 vira «coordena com», não
   `depends_on`, porque um plano em draft com dois `[P0]` abertos não é dependência
   satisfazível.
8. **K25 (Critic-B) — a transição de dois ids no piso VETO não tem fim declarado, e o
   piso efetivo é o membro mais fraco.** Com `claude-fable-5-1` somado,
   `VETO_FLOOR_ALLOWED` vai a quatro membros e o mais fraco é `claude-opus-4-8`, uma
   geração atrás; o comentário no código declara doutrina aditiva. «Transição» sem
   gatilho é permanente por omissão — foi assim que o conjunto chegou a três. Aceito:
   gatilho de FIM escrito no sentinel da W3.
9. **K26 (Critic-A) — a W1 não tem gate na OQ-7; a W3 tem na W0-US4.** A assimetria
   decide o resultado na prática, porque a W1 é a wave mais barata e mais tentadora de
   executar primeiro. Aceito com as DUAS pernas escritas: gate por padrão, escape
   nomeado se o Owner responder «wave própria» à OQ-7.
10. **K27 (Critic-A) — três entregáveis novos vivem só no corpo das waves.** Detector
    permanente de roteamento (K2), classificador de «tarefa especificada» (W5-US2) e
    sonda de hookabilidade (W0-US6) não têm AC. O que não está em AC pode não acontecer
    sem que nada fique vermelho. Aceito: AC-13, AC-14, AC-15.
11. **K28 (Critic-B) — `tier_mix_estimate.seat` descreve uma wave, não o plano.**
    `{fable_5_1: 0.50, opus_5: 0.50}` é o split do A/B da W2, que são ~2 de 15-18
    sessões. O bloco que existe para descrever 71,6 % da conta descrevia ~4 % das
    sessões. Aceito: duas linhas, período-W2 e resto do plano.
12. **K29 (Critic-A) — a lista de ACs perdeu a ordem.** A sequência em disco é
    AC-1…AC-8, AC-10, AC-11, **AC-9**, AC-12. Aceito: reordenada por wave, sufixos
    mantidos só onde nomeiam a mesma prova dividida (`3a`/`3b`).
13. **K30 (Critic-C, advisory promovido) — o AC-6 tem teto que a W4 não controla.** O
    caminho crítico para em `hook-tests-python-matrix (3.12)`, 10m39s medidos, job fora
    do escopo. Se ele crescer, o AC-6 reprova por motivo alheio e a leitura natural
    será «a matriz regrediu». Aceito: o AC-6 NOMEIA o job-bound e sua duração medida.

## Single-agent insights rejected / deferred

1. **DEFERIDO — «`.claude/hooks/tests/` roda cinco vezes por push» (Critic-C,
   advisory 3).** A contagem é plausível e o número é interessante, mas a W4 já ganhou
   a medição da deleção, que é o instrumento que produz o número certo. Registrar a
   contagem ANTES de medir seria repetir a classe que este round está curando. Entra
   como saída da medição, não como premissa.
2. **DEFERIDO — não compartilhar `.git` entre legs do Smoke por artifact/cache
   (Critic-C, advisory 2).** Correto e já implícito no composite; não muda texto do
   plano. Fica como nota da execução da W4.
3. **DEFERIDO — «a W2 escolhe AGORA uma das três opções de custo de troca» (Critic-B,
   advisory 3).** Legítimo, mas a escolha depende do spread real das primeiras janelas,
   que a W2 mede. Mantido «escolher UMA antes da primeira janela», que é o momento em
   que o pré-registro ainda é pré.
4. **DEFERIDO — ramo para MDE > 20 % na tabela de decisão da W2 (Critic-B,
   advisory 4).** Aceito em substância, mas cabe no AC-4 já escrito («MDE declarado
   ANTES»); acrescentar ramo agora é texto sem decisão nova. Fica nomeado aqui para a
   execução da W2.
5. **NÃO ALTERADO — a W6.** Terceiro round consecutivo sem exame por nenhum crítico.
   Permanece como está; quem a quiser revisar tem de pedir foco nela.
6. **CORRIGIDO sem virar ajuste — `inject-agent-context.sh:281-302`** subestima o
   bloco `MODEL_HINT`, que vai de `:278` a `:314` (Critic-A, advisory 3). A citação no
   plano é atualizada em carona; não muda decisão.

## Plan adjustments

| § do plano | mudança |
|---|---|
| frontmatter | W1 e W4 rotuladas cerimônia GPG; `budget_tokens` RE-DERIVADO (trabalho) + `budget_tokens_gateboot` explícito a partir de `F=97.292`; `budget_sessions` 9-12 → 15-18; `tier_mix_estimate.seat` em duas linhas; `external_wait` e `eta_calendar` reconhecem três cerimônias; PLAN-184 como «coordena com» |
| §2b | partição TOTAL (3ª linha: pesquisa/leitura com pergunta FIXADA → Sonnet 5); censo dividido em mecânico vs desenho do predicado; NORMATIVA já na W1, refinada (não suspensa) pela W5; removida a frase falsa sobre `.github/workflows/**` |
| §3 W1 | cerimônia GPG; gate na OQ-7 com escape declarado; derivador em disco = INSUMO; re-derivação sob §2b com tabela por sítio; wave de CORREÇÃO DE ROTEAMENTO, não de economia |
| §3 W3 | gatilho de FIM da transição (1 wave após o land sem violação ⇒ remover `claude-fable-5`); piso efetivo = membro mais fraco |
| §3 W4 | cerimônia GPG; PRIMEIRO medir a deleção dos steps duplicados (delta de env DUPLO: `PYTHONPATH` e `CEO_HOOK_ADAPTER`), depois decidir a matriz; split justificado por ATRIBUIÇÃO (zero `if: always()`), não por velocidade; censo do nome de check DERIVADO por comando; checkout fora do composite |
| Acceptance criteria | AC-11 re-escrito por classe de runner com instrumento próprio; +AC-13, AC-14, AC-15; AC-6 nomeia o job-bound; lista reordenada por wave |
| Open questions | OQ-6 + segunda cláusula (composição + âncora; `PLAN-SCHEMA:328` nomeado); +OQ-9 (uma cerimônia ou duas para W1/W4) |
| Riscos | +«wave canônica não landa em night-run»; +«`validate.yml` sem `if: always()` mascara atribuição de falha» |
| Progress log | entrada «round 2 sintetizado» |

## Round verdict

**PROCEED**

Os 12 must-fix novos (13 declarados, dedup A#2 ≡ B#1) estão aplicados no plano, e
nenhum deles depende de decisão do Owner para avançar. As duas questões que tocam o
Owner — OQ-7 (escopo da rota única) e OQ-9 (uma cerimônia ou duas) — têm as duas
pernas ESCRITAS no plano, então a ausência de resposta atrasa uma wave, não o
sequenciamento: a W0 é livre, vem primeiro e responde sozinha o que dimensiona W1, W3
e W4.

Por que não RUN-ANOTHER-ROUND na forma completa: o round 2 não mudou a estrutura do
plano como o round 1 mudou. Mudou rótulos (duas waves viraram cerimônia), aritmética
(orçamento re-derivado), totalidade de uma partição e a forma de um AC. Nenhuma wave
nasceu, nenhuma morreu. A doutrina desta casa é que rodada limpa prova a superfície
revisada — por isso o **round 3 é CONFIRMAÇÃO curta**: cada crítico lê apenas os §
que respondem aos SEUS must-fix e devolve `ACCEPT` ou `ADJUST` sobre eles, sem
re-crítica do plano inteiro. Um `ADJUST` no round 3 reabre só o item, não o round.

Por que não ESCALATE-TO-OWNER: nada bloqueia sem o Owner. O que o Owner passa a ter
de saber, e está escrito no plano, é que **três waves agora exigem a assinatura dele
(W1, W3, W4)** e que nenhuma das três pode landar numa night-run.
