---
plan: PLAN-195
round: 2
rounds_synthesized: [round-1, round-2]
critics: [Critic-A, Critic-B, Critic-C]
agents_considered: [Critic-A, Critic-B, Critic-C]
verdicts: [ACCEPT, ADJUST, ADJUST]
vetoes: "Critic-B e Critic-C: RETIRADOS por leitura do diff e RECONFIRMADOS sobre o sha256 final do plano 9894151f (seções no fim do arquivo de cada um)"
plan_sha256_final: 9894151f1648b0f7743cea526a89eab37f97f67326ae6b3c25227865ec6e0406
external_lane: "Codex review --uncommitted sobre o diff da rodada 2 (regra de parada pré-registrada: 1 rodada; P2/P3 de texto corrigidos sem nova rodada): REJECT com 2 P2 — (1) consolidação com campos de reconfirmação ainda vazios (eram placeholders, preenchidos abaixo antes do commit); (2) a W2 herdava «BLOCK→ALLOW = zero» mas corrige de propósito o falso-positivo A3-5 — exceção declarada no plano. Os 2 procedem."
round_verdict: PROCEED
design_coherent: true
consensus_adjustments: 17
decisions_revised_in_plan:
  - "Thesis item 2 — pré-léxico fiel ao bash (comentário só no início de palavra; quebra de linha; here-doc citado × não citado; tipo de aspas)"
  - "Goal — lista de residuais escrita UMA vez (12 itens), fonte única para a W0 e a ADR-201"
  - "Alternativa 1 — restrita à posição de operando/alvo (contradição com a Thesis item 4)"
  - "W1-ADR — observabilidade sem ação nova; condições do K1; mudança de contrato da tag destructive; kill-switch de dois níveis; coerção de campos do learning_rail_disabled"
  - "W1a — pré-léxico, chaves por pertença, dono da substituição entre aspas duplas e em here-doc não citado; split W1a-1/W1a-2 provável"
  - "W1b — A-8 fora (OQ-8); reason_code de vocabulário estendido"
  - "Prova — eixos comentário e tipo de aspas; replay diferencial; prova de emissão (k)"
  - "W2 — cwd só intra-comando; split W2a (mensagem A3) → W2b (alvo + argv) provável; prova de emissão"
  - "OQ-1, OQ-2, OQ-8, OQ-9 resolvidas; OQ-10 nova (Owner)"
synthesized_at: 2026-10-01T03:35:00Z
synthesized_by: CEO
synthesized_from: "texto anonimizado das críticas da rodada 2 (anonymization-map.md). Mesma limitação declarada da rodada 1: o sintetizador é a sessão que despachou os críticos; cada decisão abaixo se apoia em fato conferido no código."
---

# Consenso — PLAN-195, rodada 2

> **Escopo do veredito:** `design-coherent` (PLAN-134 W1) — o desenho ficou internamente
> coerente entre as três perspectivas forçadas. NÃO autoriza ship: só a cascata V0 → V1 → V2
> (rail Codex) → V3 (GPG do Owner) autoriza, pacote a pacote. O flip `draft → reviewed` do plano
> é do Owner (PLAN-SCHEMA §4: portão humano).
>
> **Divulgação:** repo público; formas só em prosa; matriz privada só por id.

## Fatos conferidos no código nesta rodada

- **Léxico do E3 × bash** (trazido por Critic-C): no `shlex`, no estado de palavra
  (`state in ('a','c')`), um caractere de `commenters` encerra o token e descarta o resto da
  linha; o E3 cria o léxico com `commenters` padrão (`#`); o normalizador de quebra de linha do
  E4 controla aspas mas não comentário. O bash só abre comentário no INÍCIO de palavra.
- **`emit_generic` silencioso** (Critic-B): ação fora de `_KNOWN_ACTIONS` ⇒ breadcrumb e
  retorno, sem evento (`_lib/audit_emit.py`, `emit_generic`); `veto_triggered` é registrada e
  passthrough; `learning_rail_disabled` é registrada.
- **Coerção do `learning_rail_disabled`** (Critic-C, na confirmação do VETO): `rail` fora de
  `_LEARNING_RAIL_ENUM` vira `observe`; `switch` fora de `_LEARNING_SWITCH_ENUM` vira `other`
  (`_lib/audit_emit.py:7585-7591`, `:8316-8321`).
- **O trio e a remoção sem força** (decisivo para a OQ-8): `_check_rm_rf` só recusa com as
  opções recursiva E de força juntas (`check_bash_safety.py:383-418`); a remoção recursiva sem
  força passa.

## Consensus findings (2+ críticos)

1. **R2-C1 — K3/OQ-2 fechada:** a passada aditiva única, monotônica, na cauda de
   `decide_command`, atende «os dois sítios consomem o mesmo caminhador» e tem um só ponto de
   evento. Critic-A, Critic-B, Critic-C (3/3). → OQ-2 resolvida.
2. **R2-C2 — K1/OQ-9 fechada:** BLOCK + `reason_code` + kill-switch próprios + replay offline +
   rebaixamento pré-registrado por sub-forma para advisory, nunca ASK. Critic-A, Critic-B
   (retirou o pedido de ASK pelo fato de substrato), Critic-C. Condições somadas: definição
   pela forma de alimentador opaco; tabela por sub-forma (equivalência × heurística; limite
   como número absoluto; denominador; definição de falso-positivo) fixada antes do replay;
   rebaixamento por cerimônia, não por runtime; advisory continua emitindo o mesmo
   `reason_code` com desfecho distinto e vira residual; baixador de rede nunca rebaixado;
   kill-switch de dois níveis que deixa rastro. → OQ-9 resolvida, W1-ADR.
3. **R2-C3 — K2 fechada:** piso de literais só na W2; a regra de conjunção é a do verbo
   computado. Critic-B corrigiu a própria posição da rodada 1. 3/3.
4. **R2-C4 — Observabilidade provada, não prometida:** Critic-B (must-fix), Critic-A (estado
   advisory tem de emitir), Critic-C (conteúdo do evento). Prova (k): um `veto_triggered` por
   BLOCK, zero nos controles, evento de desarme com campos corretos, sem ação nova. → Prova,
   W1-ADR, W2.
5. **R2-C5 — Divisões prováveis pré-registradas:** W1a-1/W1a-2 (Critic-C) e W2a/W2b
   (Critic-A), cada pacote ≤ 400 linhas, na mesma vaga. → W1a, W2.

## Single-agent insights kept

1. **Critic-C — pré-léxico fiel ao bash** (fato novo, conferido): Thesis item 2 e escopo da
   W1a, com dono explícito da substituição de comando entre aspas duplas e da substituição em
   here-doc de delimitador não citado; eixos «comentário» e «tipo de aspas» na prova (c).
2. **Critic-C — chaves por pertença** no normalizador, com BLOCK acima de
   `_E4_BRACE_MAX_WORDS`.
3. **Critic-C — lista de residuais escrita uma vez** (a referência do plano era circular):
   agora no Goal, 12 itens.
4. **Critic-C — coerção dos campos do `learning_rail_disabled`:** a ADR-201 escolhe entre
   estender as enumerações (o `_lib/audit_emit.py`, canônico, vira path condicional da W1a) e
   outra ação registrada; a prova (k) afirma o conteúdo.
5. **Critic-C — retorno antecipado da reescrita de força-push é inerte** (re-citação token a
   token): declarado na W1-ADR.
6. **Critic-B — mudança de contrato da tag `destructive`:** o docstring de `Decision` a reserva
   ao trio; estendê-la ao vocabulário novo muda o que é liberável por citação. Declarado na
   W1-ADR; `reason_code` separa trio de vocabulário estendido.
7. **Critic-B — replay diferencial nos dois sentidos:** BLOCK→ALLOW tem de ser zero.
8. **Critic-B — limitações do corpus de replay declaradas** (um repositório, viés de
   sobrevivência, retenção dos transcripts).
9. **Critic-A — `cwd` só dentro do mesmo comando:** o `cd` entre chamadas vira residual 11 e
   FU; ler o `cwd` do stdin mudaria a assinatura de `decide_command` e o `main()`.
10. **Critic-B (P3) — Alternativa 1 contradizia a Thesis item 4:** corrigida.

## Single-agent insights rejected / deferred

1. **Critic-C — OQ-8 opção (a) estreita** → não adotada. Fato decisivo (conferido e aceito por
   Critic-C na confirmação do VETO): o equivalente direto da A-8 é a remoção recursiva SEM
   força, que o trio permite. Bloquear só a forma indireta deixaria a política incoerente. A
   pergunta de fundo vale para as duas formas e vai para o Owner como OQ-10, com o argumento
   do «contorno natural» de Critic-C registrado como insumo.
2. **Critic-B — telemetria de forma residual** (evento advisory nas formas residuais que a
   passada reconhece) → adiado: medir o volume no próprio replay antes de decidir (nice-to-have).
3. **Critic-B — preencher `session_id`/`project` no emit do hook** → FU de telemetria (como na
   rodada 1); «por projeto» funciona hoje pelo diretório da cadeia.
4. **Critic-A — caminhador único parametrizado por predicado (E4 + novo)** → FU declarado na
   ADR-201.
5. **Critic-C — p95 sobre a bateria combinatória com a linha no teto** → advisory para a
   W1a; a prova (d) já mede antes e depois.
6. **Critic-C — FU do normalizador de comentário do E4** → residual 12 do Goal + FU
   `PLAN-195-FOLLOWUP-e4-comment-normaliser`.

## Conflito resolvido nesta rodada

- **OQ-8 (A-8):** Critic-A pediu (b); Critic-C pediu (a) estreita; Critic-B não opinou. O CEO
  decidiu (b) pelo fato do código acima, e Critic-C aceitou a decisão na confirmação do VETO.
  A política (remoção recursiva sem força + A-8) é a OQ-10 do Owner, depois do replay.

## Plan adjustments

Índice das edições em `PLAN-195-bash-guard-indirect-execution.md` nesta rodada:

1. Thesis item 2: pré-léxico fiel ao bash; passada monotônica.
2. Goal: lista de residuais (12 itens), fonte única.
3. Alternativa 1: restrita a operando/alvo.
4. Oráculo: `_lib/audit_emit.py` como path condicional da W1a.
5. W0: §6.6 remete à lista do Goal.
6. W1-ADR: alimentador opaco pela OQ-9; pré-léxico; observabilidade sem ação nova; tabela,
   rebaixamento e piso da OQ-9; kill-switch de dois níveis; coerção do evento de desarme;
   contrato da tag `destructive`; reescrita de força-push inerte; limitações do corpus.
7. W1a: pré-léxico; dono da substituição entre aspas duplas e em here-doc não citado; chaves
   por pertença; `_lib/audit_emit.py` condicional; split W1a-1/W1a-2 provável.
8. W1b: A-8 fora; `reason_code` de vocabulário estendido.
9. Prova: (c) com eixos novos; (i) diferencial; (k) emissão com conteúdo.
10. Checklists de W1a/W1b: prova (a)-(k).
11. W2: `cwd` intra-comando decidido; prova herdada com (i) e (k); split W2a (mensagem A3) →
    W2b (alvo + argv) provável.
12. OQ-1 e OQ-2 resolvidas.
13. OQ-8 resolvida (b), com o fato do código e a ressalva de comportamento POSIX inferido.
14. OQ-9 resolvida com definição e condições.
15. OQ-10 nova (Owner).
16. How to continue e Session history (entrada S360 rodada 2).
17. W2: exceção declarada ao «BLOCK→ALLOW = zero» da prova (i) — só as transições do ramo do
    verbo de busca limitado ao segmento (A3-5), classificadas à mão (revisão Codex da rodada 2).

## Reconfirmação dos VETOs sobre o texto final

Critic-B retirou o VETO sobre o sha256 `fc48632a…370a99` do plano e declarou que a
confirmação não se estende a outro texto. Depois disso, o plano mudou para incorporar a coerção
do evento de desarme (achado de Critic-C na própria confirmação) e as correções da revisão
Codex desta rodada. Os dois portadores reconfirmam sobre o sha256 FINAL, registrado aqui antes
do commit:

- sha256 final do plano: `9894151f1648b0f7743cea526a89eab37f97f67326ae6b3c25227865ec6e0406`
  (calculado pelo CEO e, de forma independente, pelos dois portadores).
- Critic-B: «VETO: RETIRADO (sha256 9894151f)» — seção «Reconfirmação sobre o sha256 final»
  no fim de `threat-detection-engineer.md`; aceitou as 3 mudanças.
- Critic-C: «VETO: RETIRADO (sha256 9894151f)» — mesma seção no fim de `security-engineer.md`;
  aceitou as 3 mudanças.

Os bytes do plano commitados nesta rodada são exatamente esses; nenhuma edição do plano depois
das reconfirmações.

## Itens a carregar (não bloqueiam; entram no plano na abertura da wave dona)

Vieram nas reconfirmações. Não foram aplicados ao plano agora para não invalidar os bytes
reconfirmados; a wave dona os incorpora ao abrir, e o rail do pacote confere.

1. **W2 — limite da varredura do verbo de busca (Critic-C).** O critério «sem edição canônica
   no próprio segmento» da exceção A3-5 não pode usar o segmento do léxico do E3, que corta por
   pertença de string a `_E3_TERMINATORS` (`check_bash_safety.py:2097`): no modo POSIX, o
   terminador escapado ou citado da ação de execução do verbo de busca vira a mesma string do
   separador real. O limite é o fim da EXPRESSÃO do verbo de busca em termos de bash, usando o
   tipo de aspas do pré-léxico (Thesis item 2 (d)); a classificação manual julga a invocação
   inteira; e entra uma linha BLOCK de controle com edição canônica depois do terminador
   escapado.
2. **W1-ADR/W1a — documento do esquema (Critic-B, P3).** Se a ADR-201 escolher estender
   `_LEARNING_RAIL_ENUM`/`_LEARNING_SWITCH_ENUM`, o `SPEC/v1/audit-log.schema.md:484`
   (canônico, oráculo 1) documenta as mesmas enumerações fechadas e muda no mesmo pacote.
3. **Prova (k) (Critic-B, P3).** O teste distingue os DOIS níveis do kill-switch («só
   heurísticas» × «passada inteira») no conteúdo do evento de desarme — são riscos diferentes.

## Round verdict

**PROCEED** — `design-coherent`. Os três críticos ficaram sem must-fix aberto; os dois VETOs
foram retirados por leitura do diff e reconfirmados sobre o sha256 final `9894151f`; três itens
não bloqueantes ficam registrados acima para a wave dona. O plano segue em
`draft` até o Owner fazer o flip para `reviewed` (portão humano) e decidir a OQ-10 depois do
replay. Regra de parada respeitada: 2 rodadas de 3.
