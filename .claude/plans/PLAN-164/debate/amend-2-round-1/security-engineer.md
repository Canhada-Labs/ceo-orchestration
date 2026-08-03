---
plan: PLAN-164 (ADR-110-AMEND-2)
round: amend-2-round-1
role: Principal Security Engineer
skill: security-and-auth v1.1.0
created_at: 2026-08-03
---

# Critique — ADR-110-AMEND-2 (recalibração 120/150 → 180/210)

## Verdict

**ADJUST** — o número 180/210 sobrevive e está *melhor* embasado do que a
proposta argumenta, mas a seção de medição está factualmente errada (n=20,
não 14; p95 = 119.8s, *abaixo* do budget, não 121.2s acima), a afirmação
de que o teste de invariante "passa sem edição" é falsa, e o residual
§4(i) fica materialmente pior sob 180 sem um campo de auditoria de 1 linha.

## Summary

Re-executei a query normativa do §3 de forma independente sobre a união
`~/.claude/projects/ceo-orchestration/audit-log-2026-0*.jsonl` + o vivo
(8 arquivos). Resultado:

| Métrica | Proposta | Medido por mim |
|---|---|---|
| n saudáveis | 14 (A:10, B:4) | **20 (A:14, B:6)** |
| latências (s) | 33,41,44,48,49,55,61,70,71,79,95,115,115,120 | 33,41,44,48,49,**54**,55,61,70,71,79,**82**,**92**,95,**105**,**105**,**114**,115,115,120 |
| mediana | 65.5 | **75.0** |
| p95 (`quantiles(n=20)[18]`) | 121.2 (> budget) | **119.8 (< budget)** |
| p95 empírico (nearest-rank) | — | **115.0** |
| case-F "no período" | 3 | **7 joináveis; 18 no disco** |

Os 6 valores que faltam na proposta são *interiores* (54, 82, 92, 105,
105, 114) — não é dataset que cresceu depois, é **um arquivo inteiro que
a query não leu**. Confirmei qual: o conjunto exato da proposta (A:10,
B:4) é o conteúdo de `audit-log-2026-08.jsonl` **sozinho**;
`audit-log-2026-08-1.jsonl` (A:4, B:2, F:4 — os eventos de hoje) ficou de
fora. A emenda que existe para consertar "query normativa aponta para
arquivo que rotacionou" reproduziu a mesma classe de bug dentro da sua
própria evidência. Isso responde AQ2 sozinho.

**A conclusão 180 continua certa — por um argumento melhor.** Não precisa
de p95 interpolado nem de extrapolação acima do máximo. Basta contar:

- pós-uplift (cerimônia 2026-07-29) há **20 reviews saudáveis + 6 case-F
  cravados em 120.0/121.0s** = 26 reviews;
- portanto **23.1% (6/26) das reviews levam ≥120s**;
- se 23% da distribuição está em ≥120s, o percentil 95 **é ≥120s por
  contagem** — provado, não interpolado;
- a convenção de folga do AMEND-1 (~1.5× p95) sobre um p95 que é ≥120
  dá **≥180**.

Ou seja: 180 é o **piso** implicado pela própria convenção, não a escolha
generosa. E isso refuta a alternativa (a) 150/180 de forma rigorosa —
150 < 180 ≤ 1.5×p95 — sem depender do apelo elástico à censura. Todos os
20 saudáveis são pós-uplift (o menor é 33s; sob o cap antigo de 30s
nenhum poderia ter completado), então a partição está limpa.

Da minha lente, o número que a proposta nunca declara é o que importa
para um controle de segurança: **23% dos edits canônicos L3+ pós-uplift
passaram sem review**. Essa é a taxa de fail-open atual. O trade não é
"fail-open window × hold síncrono" em abstrato — é "23% agora × ~3 min de
hold no pior caso".

## Risks

1. **R1 — O argumento como escrito é elástico e é falsificável em uma
   tarde.** "p95 121.2 > budget, EMPATA/EXCEDE, escalada MANDATÓRIA" é
   falso hoje (119.8 < 120) e mudou duas vezes em horas (a memória de
   sessão registra n=10/p95 122.2; a proposta diz n=14/121.2; eu meço
   n=20/119.8). Um revisor cross-vendor que refizer a conta derruba a
   seção §2 da emenda e, com ela, a legitimidade da cerimônia. O risco
   não é o número — é a emenda ficar com uma justificativa que não
   reproduz.
2. **R2 — A grandeza medida ⊋ a grandeza capada.**
   `pair_rail_review_expected` é emitido em `check_pair_rail.py:1469`,
   **antes** de `_invoke_codex_review` (:1476). Dentro dele, e antes do
   `subprocess.run(timeout=timeout_s)` (:1038), rodam: `_resolve_codex_bin()`
   (verificação de pin ADR-182 — sha256 do payload nativo), build do
   prompt, redação de egress ADR-114 (fail-CLOSED) e `mkdtemp`. Depois do
   subprocess ainda vêm readback com re-validação TOCTOU, parse, redação e
   o emit. Logo `latência_log = overhead_não_capado + subprocess(≤cap)`.
   Comparar p95(end-to-end) com o cap do subprocess compara grandezas
   diferentes. O "máx observado 120.0s (= o budget interno!)" é o artefato
   disso: um caso **saudável** a 120.0s teve subprocess estritamente
   <120s. Prova: os case-F censurados aparecem em 120.0 e 121.0 — os
   mesmos valores de relógio do máximo "saudável". A métrica não separa
   review completada de review morta na fronteira.
3. **R3 — §4(i) fica pior sob 180, e o bypass mais silencioso é o
   não-controlado.** Confirmei que nenhum evento registra o budget
   efetivo: a união de campos de `pair_rail_case` /
   `pair_rail_review_expected` no log real é `action, case, claude_verdict,
   codex_verdict, file_path_hash_prefix, jaccard_similarity_bucket,
   precondition_met, review_id, rubric_violation_id, session_id, severity,
   tool_name, ts, tokens_*, hmac, …` — **não há `timeout_s`**. Consequência:
   `CEO_PAIR_RAIL_TIMEOUT_S=5` produz case-F **indistinguível** de uma
   indisponibilidade real do Codex. Compare com o kill-switch documentado:
   `CEO_PAIR_RAIL_DISABLE=1` emite `_AUDIT_KILL_SWITCH` (:1412-1417),
   um evento próprio e ruidoso, antes de qualquer `review_expected`. Ou
   seja, **o knob sem piso é hoje o bypass mais furtivo que o kill-switch
   oficial** — gradiente de incentivo invertido. Subir o default para 180
   aumenta o custo de UX da review honesta e portanto a pressão para usar
   exatamente esse caminho. A frase do §4(i) ("every such miss is auditable
   as a case-F event") é verdadeira só quanto à *existência* da falha,
   nunca quanto à *causa*.
4. **R4 — AQ3 não é UX, é um gate de segurança com modo de falha pior que
   o atual.** `_python-hook.sh` não impõe timeout próprio; o único teto é
   o registro do harness. Se o Claude Code tiver teto duro (ou global)
   abaixo de 210s, o harness mata o hook **antes** do cap interno de 180 —
   e um hook morto não emite `pair_rail_case` nenhum. O resultado é
   fail-open **sem evento**, invisível para a query do §3 (nem numerador
   nem denominador) e detectável só como `review_expected` órfão. É
   estritamente pior que o case-F de hoje, que ao menos é contável. Nota
   útil: medi **0 órfãos** em toda a história joinável (e 0 cases sem
   expected) — evidência de que a 150s o harness **não** vem matando o
   hook. Isso dá baseline falsificável para a sonda.
5. **R5 — O dataset se move enquanto é medido.** Quatro dos case-F são
   de hoje (19:00, 19:02, 19:09, 19:11 Z) — a sessão que *mede* também
   *gera* amostras. Sem congelar o corte, cada re-execução dá outro
   número e nenhuma verificação bate.
6. **R6 — A query normativa descarta 11 case-F em silêncio.** Dos 18
   `pair_rail_case` com `case=F` no disco, **11 não têm `review_id`**
   (schema anterior ao threading do PLAN-161) e são dropados pelo join.
   "3 case-F no período" nunca foi contagem de F — era contagem de F
   *joinável*. Não muda a decisão (são pré-uplift), mas é exatamente o
   tipo de silêncio que a emenda precisa parar de produzir.

## Must-fix

- **MF1 — Trocar a justificativa, manter o número.** Reescrever §2/§3 da
  emenda com n=20, mediana 75.0, p95 interpolado 119.8 (**abaixo** do
  budget) e p95 empírico 115.0 — e sustentar a escalada pelo argumento de
  contagem: 6/26 = 23.1% das reviews ≥120s ⟹ p95 verdadeiro ≥120s por
  contagem ⟹ 1.5× ⟹ ≥180. Declarar explicitamente que 180 é
  **estimator-robusto** (1.5×115 = 172.5 e 1.5×119.8 = 179.7 arredondam
  para 180 pela mesma convenção). Remover "EMPATA/EXCEDE" e "mandatória"
  na forma atual — não se sustentam.
- **MF2 — Corrigir o escopo: a mudança NÃO são 3 literais.** A afirmação
  "`test_pair_rail_timeout_invariant.py` passa sem edição — o teste
  verifica a desigualdade, não literais" é **falsa**. O teste tem
  `_RATIFIED_INTERNAL_S = 120`, `_RATIFIED_REGISTRATION_S = 150` e
  `test_ratified_absolute_values`, que afirma o default interno == 120 **e**
  `_FALLBACK_RE.findall(...) == ["120", "120"]` **e** as duas registrations
  == 150. O docstring do próprio teste diz que isso é o contrato: *"A
  deliberate recalibration must edit THIS test in the same change"*. Sem
  editar o teste, a suíte vai vermelha. Superfície real:
  1. `.claude/hooks/check_pair_rail.py` :1717 (`"120"`), :1720, :1722
     (`timeout_s = 120.0`) — **e o docstring :51** (`default 120`), que o
     AMEND-1 §1.1 já listava como 4º ponto e a proposta omite;
  2. `.claude/hooks/tests/test_pair_rail_timeout_invariant.py` — os dois
     literais ratificados + a narrativa do docstring;
  3. `.claude/settings.json` :285-286 e
     `templates/settings/settings.base.json` :98-99 (timeout + statusMessage);
  4. `CHANGELOG.md` :43 carrega `"may take 1-2 min"` — vira stale com o
     statusMessage de ~3 min (classe doc-freshness que já deixou a rc.2
     vermelha);
  5. o arquivo ADR-110-AMEND-2 é um **ADR novo** ⟹ contagem 184→185 em
     `CLAUDE.md` + superfícies derivadas (`check-claude-md-claims.py`
     tolerance=0, e a classe de docs não vigiados do S275).
  Sem isso, `touched − scope ≠ ∅` na cerimônia.
- **MF3 — Emitir o budget efetivo no evento.** Adicionar `timeout_s` (o
  valor pós-clamp) em `pair_rail_case` e/ou `pair_rail_review_expected`.
  Justificativa de segurança: é o que transforma §4(i) de auditável-na-
  existência em auditável-na-causa, e é o que permite a qualquer
  recalibração futura distinguir "F sob budget de 180" de "F sob budget de
  5". **Não conflita com o item 2 deferido do consensus do AMEND-1** — não
  muda a semântica do knob nem impõe piso; só registra o que já foi
  decidido em runtime. Um campo. Sem isso, a série histórica que a
  *próxima* emenda vai consultar já nasce ambígua (todo F de 120s de hoje
  fica indistinguível de um knob setado em 120 amanhã).
- **MF4 — Sonda de teto do harness ANTES da cerimônia (AQ3 = gate,
  não UX).** Critério de aceite explícito: um hook registrado a 210s que
  bloqueia ~185s ainda **retorna** e ainda **emite `pair_rail_case`**; e a
  contagem de `review_expected` órfãos permanece **0** (baseline medido
  hoje: 0). Se o harness tiver teto abaixo de 210, a emenda não pode
  landar como está — o modo de falha resultante é fail-open sem nenhum
  evento, pior que o case-F atual. `scripts/doctor.sh` já documenta essa
  ameaça em prosa (`_pair_rail_timeout_check`, "the harness can KILL the
  hook before the codex verdict lands"); a emenda deve provar que 210 é
  honrado, não assumir.
- **MF5 — AQ2: sim, script versionado — e a razão é empírica, não
  teórica.** A query manual falhou **nesta rodada**, de um jeito novo:
  não devolveu n=0 (o bug de rotação que a emenda conserta), devolveu um
  **subconjunto** cujo p95 sustenta a conclusão desejada onde o conjunto
  completo não sustenta. Essa é a classe vacuous-gate na sua forma pior —
  um gate que responde, com o número errado. O script (ex.
  `.claude/scripts/local/pair-rail-latency.py`) deve imprimir os
  **inputs**, não só o resultado: lista de arquivos lidos + mtimes,
  contagem por `case`, n joinável, **quantos F foram descartados por falta
  de `review_id`**, contagem de órfãos, taxa de censura e o `ts` máximo
  usado como corte. Um verdict de governança precisa ser reproduzível por
  terceiro; hoje não é.

## Nice-to-have

- **Trocar a métrica de gatilho da recalibração**: p95 de amostra
  censurada é estruturalmente inestimável (é o argumento (c) da própria
  proposta, e ele está certo). **Taxa de censura** — fração de reviews que
  batem no cap — é observável sob qualquer budget e não depende de
  extrapolar acima do máximo. Sugestão de texto para o §3 sucessor:
  reabrir se a taxa de censura exceder ~5% em n≥20 pós-mudança. Isso
  também dá resposta honesta a "180 é suficiente?": **não sabemos**, e com
  23% censurado hoje é plausível que a cauda passe de 180. A emenda deve
  dizer isso em vez de sugerir que 180 fecha o assunto.
- Reportar os censurados junto (n, min, max) em vez de só citá-los; com
  6 censurados e 20 completos, um Kaplan-Meier é aritmética de guardanapo
  e dá um limite inferior defensável para o p95.
- Os `ts` do log têm **resolução de 1 segundo** (todas as latências são
  inteiras). Reportar p95 com uma casa decimal (121.2 / 119.8) é precisão
  espúria; arredondar para segundo inteiro.
- Congelar o dataset da emenda por `ts` de corte (R5), citado no texto.

## Unseen

- A proposta enquadra o trade sem nunca declarar a **taxa de fail-open
  atual (23%)**. É o único número que dimensiona o controle: sem ele,
  "180 vs 150" parece preferência de folga; com ele, é "quantos edits L3+
  seguem sem review".
- **O incentivo, não o mecanismo, é o vetor** (R3). O modelo de ameaça do
  §4(i) trata o knob como privilégio já detido pelo operador. Correto —
  mas ignora que *elevar o custo do caminho honesto* converte um knob
  documentado em prática rotineira. Três minutos de hold síncrono é
  exatamente a dor que faz alguém exportar `CEO_PAIR_RAIL_TIMEOUT_S=30`
  "só nesta sessão" — e o log não vai saber diferenciar isso de o Codex
  ter caído. MF3 é o custo mínimo de manter §4(i) honesto sob 180.
- O `subprocess.run` cobre a chamada, mas o **overhead não-capado** (R2)
  cresce com o tamanho do payload do Codex (sha256 do binário nativo a
  cada invocação) e com o tamanho do prompt (redação ADR-114). Sob carga,
  esse pedaço não é limitado por budget nenhum: é a margem de 30s do
  registro que absorve, e ela é absoluta, não proporcional. Vale uma
  linha nos residuais.
- **O que o `>600` faz sob 180**: o clamp continua *resetando* para o
  default (wart §4(ii)), então quem setar 9999 passa a ganhar 180 em vez
  de 120 — silenciosamente mais permissivo que antes. Não é bug novo, mas
  a emenda deve registrar que o wart §4(ii) muda de magnitude junto.

## What I would NOT change

- **As três rejeições (a)/(b)/(c) estão certas.** Reforço (b) com o dado
  de R3: institucionalizar o env-knob como mecanismo de calibração seria
  promover o bypass *mais furtivo que o kill-switch oficial* a instrumento
  de governança. E (c) está certo pelo motivo certo — mais amostras
  saudáveis não revelam a cauda; só subir o cap e re-medir a censura revela.
- **Os 3 literais não abrem caminho fail-open novo — confirmado.** Grepei
  todo o dataflow de `timeout_s` (`:845, :1038, :1042, :1396, :1481,
  :1716, :1720-1722, :1733, :2272, :2310`): o valor só alimenta
  `subprocess.run(timeout=...)` e a string de erro do `CodexTimeout`. Não
  há segundo consumidor, não há comparação derivada, não há caminho novo.
  A mudança é inerte no dataflow além do cap. Minha objeção de escopo
  (MF2) é sobre *outros arquivos*, não sobre o hook.
- **Clamp `>600` intocado** — correto. Subir o teto do clamp junto seria
  ampliar o espaço do knob no mesmo commit em que se declara que o knob é
  residual de fail-open.
- **Margem de 30s entre camadas — manter absoluta, não escalar.** Ela
  cobre startup de Python + pin-verify + validação, que são custo absoluto,
  não percentual. Escalar para 45/60 "por proporção" seria numerologia.
- **`scripts/doctor.sh` não precisa de edição** — `_pair_rail_timeout_check`
  extrai o literal por regex
  (`os\.environ\.get("CEO_PAIR_RAIL_TIMEOUT_S", "\([0-9][0-9]*\)")`) e
  compara com `+30`; auto-adapta a 180/210. Não mexer.
- **Manter fail-OPEN no timeout (ADR-106).** Nada nesta emenda deve
  transformar timeout em block: isso converteria uma indisponibilidade do
  Codex em DoS do próprio operador (a classe C3 self-DoS do S284). O
  fail-open aqui é decisão registrada, e continua correta.
- **Manter o `statusMessage`** e atualizá-lo — a mitigação real do hold é
  o feedback, e sob 180s ela deixa de ser cosmética.
