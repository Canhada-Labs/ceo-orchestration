---
id: ADR-055-AMEND-4
title: "ADR-055 §Components — estado da auditoria sem acúmulo: caminho rápido de saída, prazo na drenagem forçada de saída, trava presa vira sinal, journal vazio removido na origem e invariante de não-perda reescrito"
status: PROPOSED
draft: true
revision: "r2 — aplica a lista §3(a) do consenso da rodada 2 (MF-R2-W2-1..4 e os must-fix de execução 5..16)"
draft_for: "texto do pacote de ADR da W2 do PLAN-194. O arquivo canônico `.claude/adr/ADR-055-AMEND-4-spool-state-gc.md` nasce só no pacote de ADR (decisão Q5 do Owner, S361), no leque de ADR em série. O slug fica (R2-7, anti-churn)."
proposed_at: 2026-10-02
proposed_by: "CEO (S361, PLAN-194 W2.1); redação delegada ao arquétipo VP Engineering"
amendment_of: "ADR-055 (Audit-log HMAC chain for tamper detection — 2026-04-18 via PLAN-023)"
amends_section: "§Components §3 — drenagem forçada de SAÍDA e contabilidade de não-perda (refina ADR-055-AMEND-1 §4 Fase 1, §4 «Loss accounting» e §5; refina ADR-055-AMEND-3 §3, §4 e §5)"
veto_floor: "ADR-052 (security-engineer VETO — integridade do log de auditoria; herdado do ADR-055-AMEND-3)"
debate_status: "W2 `design-coherent` na rodada 2 (PROCEED dos três críticos). VETO de Segurança RETIRADO, condicionado a MF-R2-W2-1..4 no texto deste ADR e do plano antes do pacote de ADR, e à W2.0 landada antes do SIGN. Sem nova rodada de debate: o rail V2 do pacote confere a aplicação."
debate_record: ".claude/plans/PLAN-194/debate/round-1/consensus.md; .claude/plans/PLAN-194/debate/round-2/consensus.md"
codex_pair_rail: "required per ADR-107 — pendente; roda nos bytes canônicos do pacote da W2"
risk_tier: A
debate_required: true
sign_precondition: "cura da corrida do `agent_spawn` (condição 67 assinada da v1.4.0-rc.1) landada ANTES do SIGN da W2 — a vaga é a DECISÃO PENDENTE 1 do Owner (§13), hoje o ÚNICO pré-requisito do Owner para o SIGN"
related_plans: [PLAN-194, PLAN-094, PLAN-182]
related_adrs: [ADR-055, ADR-055-AMEND-1, ADR-055-AMEND-2, ADR-055-AMEND-3, ADR-052, ADR-001, ADR-081, ADR-107, ADR-115, ADR-124, ADR-125, ADR-186]
supersedes: []
amends:
  - target: "ADR-055-AMEND-3 frontmatter `amends[0].amended_clause` e §4 (drain FORÇADO)"
    original_clause: "A FORCED drain (force=True — recovery / exit-handler / session-start) blocks up to SPOOL_LOCK_TIMEOUT (a timeout there is anomalous: ok=False + error='canonical_lock_timeout' + breadcrumb, unchanged)."
    amended_clause: "Os únicos chamadores `force=True` VIVOS são as duas rotas de SAÍDA (atexit e sinal); não existe perna de recuperação nem de session-start em produção. A saída passa por um auxiliar de saída, chamado nas DUAS rotas: (a) esvazia os buffers de stdout e stderr ANTES de qualquer drenagem; (b) caminho rápido — sem conteúdo próprio, não toma a trava canônica nem lista o diretório; (c) em processo de HOOK, prazo contado da âncora `min(import, início do processo lido do kernel)` e derivado do menor timeout de hook registrado; (d) no máximo UMA tentativa de drenagem. Esperar a trava canônica e não obtê-la deixa o spool no disco para a perna 3 e NÃO é anômalo (`DrainStats.exit_deadline_skip=True`, `ok=True`, sem o breadcrumb `drain canonical lock timeout`). A trava presa vira sinal pelo portão STARVED de saída (§4.3). `drain_now(force=True)` chamado SEM prazo mantém a semântica do AMEND-3 byte a byte."
  - target: "ADR-055-AMEND-3 §3, «No-loss invariant (corrected by debate R-QA1)»"
    original_clause: "No-loss is the UNION of (loser's own size/staleness re-drain) ∪ (loser's atexit/signal force-drain) ∪ (next drainer's dead-PID orphan sweep once `_is_alive_pid` flips False)."
    amended_clause: "Invariante INV-NP por CONJUNTO de `record_id` (cada um no log canônico exatamente uma vez), com três pernas: perna 1 = drain oportunista do próprio dono; perna 2 = drenagem de saída do próprio dono, SÓ para quem tem conteúdo próprio, com prazo; perna 3 = a varredura global da fase 2 de QUALQUER drainer seguinte deste projeto que ganhe a trava canônica (oportunista ou de saída), que recolhe spools de PID morto e todo `.draining.*`. Sem perna de `SessionStart` (§3)."
  - target: "ADR-055-AMEND-1 §4 «Loss accounting» (journal por PID) — o destino do journal compactado, que o ADR não fixava e o código reescreve com 0 byte"
    original_clause: "Per-PID journal `state/audit-pending.<pid>.journal` with buffered appends [...] drain Phase 5 appends `op:\"drained\"`."
    amended_clause: "A compactação pós-drain, sob a trava do PRÓPRIO journal, REMOVE o journal quando o resultado ficaria vazio, em vez de reescrevê-lo com 0 byte. É o ÚNICO sítio de remoção de journal em hook. Nenhum hook remove arquivo `*.lock` (§4.5)."
retires_revert_triggers:
  - "ADR-055-AMEND-3 frontmatter `revert_trigger_truly_lost_7d: 1` e §5 «`truly_lost > 0` over 7-day window» — morto por construção (`truly_lost` nunca é incrementado; §2.4); substituído pelo G6 (perda real, ATIVO) e pelo G7 (§8.2)"
  - "ADR-055-AMEND-1 §5 gatilho 3 (`truly_lost > 0` em 7 dias) — idem"
  - "ADR-055-AMEND-1 §5 gatilho 1 e ADR-055-AMEND-3 §5 (taxa de quebra de cadeia > 0,1% em 30 dias) — não avaliável enquanto a condição 67 existir; substituído pelo G5 (§8.2)"
target_telemetry_window_days: 30
tags: [governance, audit-log, spool-writer, async-drain, amendment, hook-exit-latency, decision-delivery, no-loss-invariant, anti-accumulation, starvation-signal, plan-194-w2]
enforcement_commit: "n/a (rascunho; o runtime nasce no pacote da W2)"
---

# ADR-055-AMEND-4 — Estado da auditoria sem acúmulo (W2 do PLAN-194)

**Status:** PROPOSED — texto revisado (r2) para o pacote de ADR. A W2 saiu `design-coherent` na rodada 2
(PROCEED dos três críticos); o VETO de Segurança foi RETIRADO com condições (MF-R2-W2-1..4, aplicadas nesta
revisão — tabela em §15.2). Não há nova rodada de debate: quem confere a aplicação é o rail V2 do pacote.
**Data:** 2026-10-02 (UTC)
**Enforcement commit:** n/a (rascunho)
**Decision drivers:** decisão de guard perdida por latência de saída; ~3 arquivos acumulados por PID; o
gatilho de reversão do AMEND-3 está morto; a corrida da condição 67 contamina a régua; a trava canônica presa
ficaria invisível depois da cura.

> **Legenda de evidência.** **[disco]**: conferido por este redator no HEAD `48f03b3a` (árvore da S361;
> `spool_writer.py`, `audit_log.py`, `filelock.py`, os settings e o `_python-hook.sh` estão inalterados desde
> `a9924eb1`). **[medido: redator]**: medido por este redator, só leitura, na data indicada. **[consenso]**:
> conferido pelo sintetizador da rodada indicada. **[medido: X]**: medido por X, não refeito aqui.
> **[plano]**: o plano afirma. **[inferência]**: dedução a conferir no pacote.
>
> **Regra de prevalência.** Onde o plano e este texto divergirem na W2, vale este texto (MF-R2-W2-4). O
> plano é reconciliado pelo CEO antes do pacote de ADR. Repositório público: classes de defeito e
> invariantes, nenhuma receita de contorno de guarda.

---

## §0 Sumário da decisão

1. **Invariante de não-perda por CONJUNTO** (INV-NP, §3): todo `record_id` aceito pelo spool aparece no log
   canônico exatamente uma vez. Três pernas, nenhuma de `SessionStart`. O gatilho `truly_lost` do AMEND-3 é
   declarado **MORTO** e aposentado (§2.4, §8.3).
2. **Auxiliar de saída único**, chamado no atexit E no sinal (§4.1): esvazia stdout e stderr ANTES de tudo;
   caminho rápido com um `stat` do próprio spool e um sinalizador em processo à prova de falha; zero
   `listdir`/`scandir`; no máximo uma tentativa de drenagem.
3. **Prazo na drenagem de saída de HOOK** (§4.2): âncora `min(import, início do processo lido do kernel)`,
   com o import como recurso declarado; prazo = `T_min − margem`, com `T_min` = 3 s hoje e teste de deriva.
   Estourar o prazo deixa o spool para a perna 3, e isso não é «anômalo». Controle de **entrega da decisão
   BLOCK** com guard sintético de IMPORT TARDIO e calibração contra o harness REAL.
4. **Trava canônica presa vira sinal em ≤ 1 h** (§4.3), sem volume por saída, com controle positivo de
   portador externo.
5. **Journal vazio removido NA ORIGEM**, só pela compactação, sob a trava do próprio journal (§4.4).
6. **Nenhum hook apaga `*.lock`** (§4.5): T1 por padrão, com limiar OPERACIONAL e W2.6 RECORRENTE; T2
   (re-checagem de inode no `filelock.py`, kernel) condicional, com gatilho numérico pré-registrado; T3 fora.
7. **GC em hook fora do pacote base** (§4.6, W2.4 CONDICIONAL).
8. **Versões mistas** seguras porque nenhum caminho muda, provado por teste dourado dos construtores (§4.7).
9. **Regex ancoradas** com `fullmatch` + `re.ASCII` (§4.8) e **lista do que nunca se apaga** (§4.9).
10. **W2.6 endurecida e RECORRENTE** (§5), com recusa por spool ou `.draining.*` de PID vivo.
11. **Critérios** (§6): a SEGURANÇA barra; o FLUXO H1 com `|D|_min` ≥ 200 é o critério primário de higiene
    (vermelho MEDIDO no HEAD: F = 0,999); o teto de 1.000 vale só para journals.
12. **Gatilhos em instrumentos LIGADOS** (§8), cada um com controle positivo; **G6 (perda real) e G7
    (`would-log` datado) ATIVOS na W2**.
13. **Observabilidade pelo resultado** no `/ceo-boot` e no nightly, sem tocar o `audit_emit.py` (§9).
14. **Pré-condição do SIGN**: a cura da condição 67 (W2.0). A vaga é decisão pendente do Owner (§7, §13).

---

## §1 Status e portões de aceitação

PROPOSED. O flip para ACCEPTED acontece SÓ no commit de cerimônia do pacote da W2, e exige:

1. ~~PROCEED da W2 no debate~~ — **feito** (rodada 2, `design-coherent`; VETO retirado com condições). As
   condições MF-R2-W2-1..4 estão neste texto (§15.2); a reconciliação do plano é do CEO, antes do pacote de ADR.
2. A W2.0 (cura da condição 67) landada ANTES do SIGN da W2 (§7), na vaga da decisão pendente 1 (§13).
3. A W0.5 pré-registrada no LEDGER e rodada ANTES do patch, com a calibração contra o harness real (§6.4).
4. Rail do Codex (ADR-107) nos bytes canônicos até rodada limpa, com a regra de parada pré-registrada (≤ 3
   rodadas; NO-GO só por P0 ou afirmação FALSA). O rail confere também que este texto e o plano dizem o mesmo.
5. Assinatura GPG do Owner. O apêndice `## Amended-by` do ADR-055 landa no MESMO commit; o arquivo de emenda
   entra no leque de ADR em série (índice e documentos de contagem re-derivados no LAND).

---

## §2 Contexto

### 2.1 O sintoma e o risco real

- **Sintoma.** O state dir deste projeto tinha ~226,8 mil entradas às 23:55Z–00:00Z de 2026-10-01/02
  **[medido: críticos da rodada 1]**. O `audit-log.errors` tem **31.683 linhas, 31.485 delas
  `drain canonical lock timeout`** em 2026-10-02T03:40Z **[medido: redator]** (30.068 às 00:25Z
  **[consenso r1]**: ~1.100 por hora).
- **Perda REAL já acontecendo.** No mesmo arquivo há **3 linhas `would-log=`** — `agent_spawn` descartado
  por trava canônica ocupada (`audit_log.py:1325-1329`) — datadas 2026-10-01T23:48:41Z, 2026-10-02T00:44:25Z
  e 00:52:00Z **[medido: redator]**. Nenhum instrumento as acusava.
- **Risco de segurança.** Não é o disco (o crescimento é limitado pelo espaço de PIDs). É a **decisão de
  guard perdida**: um guard que já decidiu BLOCK e passa do timeout na SAÍDA é morto pelo harness, e a ação
  passa sem decisão (lane `CC285-05` **[plano]**). E a decisão só sai DEPOIS da drenagem de saída: com stdout
  em pipe, um processo que imprime o JSON e tem um `atexit` de 1,5 s entrega o 1.º byte em **1,54 s**; com
  `flush` no início do `atexit`, em **0,03 s** **[medido: redator, CPython 3.9.6 do sistema; o consenso r2
  mediu 1,52 s]**.
- **Premissa que muda.** O AMEND-3 tratava o timeout do drain forçado como «genuinamente anômalo». Com a saída
  sujeita a prazo, não obter a trava a tempo vira desvio ESPERADO, coberto pela perna 3. Mudança semântica ⇒
  arquivo de emenda próprio (Q5; C16 do consenso r1).

### 2.2 De onde vêm os ~3 arquivos por PID

Cada processo que emite cria o spool `audit-spool.<pid>.jsonl`, a trava dele `audit-spool.<pid>.jsonl.lock`
(`spool_writer.py:465-467`, aberta em `:1001-1002`), o journal `audit-pending.<pid>.journal` e a trava dele
`audit-pending.<pid>.journal.lock` (`:450-472`; o flush abre o journal com `O_CREAT` sob a trava,
`:958-961`) **[disco]**. O drain renomeia o spool para `.draining.*` e o apaga quando todo consumido; a
compactação reescreve o journal sem os triplos drenados e termina com 0 byte, sem nunca removê-lo
(`:2276-2297`) **[disco]**. Sobram três: as duas travas e o journal vazio. Censo: 75.587 travas de spool,
75.609 travas de journal e 75.609 journals, 75.396 deles com 0 byte, e ~214 journals com conteúdo (213 a 215,
conforme a leitura) **[medido: QA r1; consenso; plano]**.

### 2.3 Por que a saída é lenta

- Todo processo que importa o `audit_emit` registra o drain de saída no próprio import
  (`audit_emit.py:13336-13348`) **[disco]**; até um hook que nunca emitiu toma a trava canônica na saída
  (`_atexit_drain` → `drain_now(force=True)`, `spool_writer.py:2573-2587`), com espera de até 2,5 s
  (`SPOOL_LOCK_TIMEOUT`, `:66`).
- Dentro da trava, a fase 2 lista e ordena o diretório inteiro (`os.listdir`, `:1273`), ~0,24–0,30 s com ~219
  mil nomes (lane `H-02` **[plano]**).
- As esperas se somam: flush do journal (até 2,5 s, `:958`), trava canônica (até 2,5 s, `:2366-2368`),
  compactação de cada PID drenado (até 2,5 s, `:2276`) e o trabalho do próprio hook.

### 2.4 Premissas do AMEND-1, do AMEND-3 e do rascunho r1 que o disco refuta

| premissa | onde estava | o que o disco mostra | efeito neste texto |
|---|---|---|---|
| «`truly_lost > 0` em 7 dias» é gatilho de reversão | AMEND-1 §5 (gatilho 3); AMEND-3 frontmatter e §5 | `truly_lost` só aparece no padrão (`spool_writer.py:136`) e na leitura (`:2562`) **[disco]** | MORTO; aposentado; G6/G7 no lugar (§8) |
| a reconciliação de início de sessão roda | AMEND-1 «Loss accounting» | `reconcile_journal_at_session_start` (`:2467`) sem chamador em produção **[disco; consenso r1]**; 0 eventos `audit_flush_dropped_count` em 16 logs **[medido: DevOps r1]** | fora de produção; ligá-la fica FORA da W2 |
| existe drain forçado de «recovery» e de «session-start» | AMEND-3 frontmatter | os únicos `force=True` vivos são o atexit (`:2581`) e o sinal (`:2610`); `:2539` está na reconciliação morta; `SessionStart.py` sem drain nem spool **[disco; consenso r1]** | sem perna de `SessionStart` |
| «enquanto o PID vive, nenhum drainer toca os arquivos dele» | crítica r1 (retirada pelo autor na r2) | a fase 2 recupera `.draining.*` «owned by a dead PID (or even a live one)» (`:1277-1317`); a compactação trava o journal do PID drenado (`:2276`) **[disco]** | só a remoção sob a trava do próprio journal é segura (§4.4); nenhuma trava se apaga (§4.5) |
| o `FileLock` garante exclusão mesmo com o caminho apagado | implícita em todo GC de trava | `acquire` abre com `O_CREAT` e faz `flock` sem comparar inode (`filelock.py:144`, `:149`) **[disco]** | nenhum hook apaga `*.lock` |
| a taxa de quebra de cadeia mede a saúde do drain | AMEND-1 §5 (gatilho 1); AMEND-3 §5 | `audit_log.py` lê o elo anterior e calcula o HMAC FORA da trava (`:1262-1278`; trava em `:1283`), contra «MUST be called WITH the audit-log FileLock held» (`_lib/audit_hmac.py:482`) **[disco]**: condição 67 | inavaliável até a cura (§7); G5 no lugar |
| a âncora do prazo no import do `spool_writer` basta | rascunho r1 §4.2 | os guards importam o `audit_emit` DENTRO de função: `check_canonical_edit.py:658`, `:725`, `:1429`; `check_skill_reference_read.py:155`, `:311` — e este é o hook de timeout 3 s; `check_agent_spawn.py:73` usa um shim de importação PREGUIÇOSA (`audit_emit_dispatch`) **[disco]** | âncora = `min(import, início do processo no kernel)` (§4.2) |
| o breadcrumb `STARVED` do AMEND-3 mantém o travamento observável | AMEND-3 §4 (MF-1) | **0 linhas `STARVED`** no `audit-log.errors` vivo **[medido: redator]**: hooks curtos raramente disparam o drain oportunista, único que o emite | portão STARVED também na SAÍDA (§4.3) |
| os detectores por contagem de linhas acusam um travamento novo | AMEND-3 §4 | `ceo-diagnose.py:371-373`/`:417` e `status.py:290` contam o TOTAL de linhas, sem janela; com 31.683 linhas eles estão SATURADOS **[disco; medido: redator]** | o sinal é distinto pelo TEXTO e datado; consumidores com janela (§9); saturação declarada |

---

## §3 Invariante de não-perda (reescrito)

### 3.1 Enunciado — INV-NP

Seja **R** o conjunto dos `record_id` cujo `spool_append` terminou com sucesso (`last_append_succeeded()`
verdadeiro: linha escrita e com `fsync` no spool do PID). O `record_id` é carimbado em cada linha do spool
(`spool_writer.py:1026`) e sobrevive no log canônico: a fase 4 só tira `_drain_*`, `hmac` e `hmac_error`
(`:1896-1900`) **[disco]**; `pid` e `wall_ns` também sobrevivem (2.614 de 2.615 entradas do log vivo os
trazem; a exceção é o marcador de reinício) **[medido: redator]**. Para todo r ∈ R:

- **(a) Segurança — nunca some.** Nenhum código apaga um arquivo que contenha r antes de r estar no log
  canônico (na família de rotação). A fase 5 só apaga `.draining.*` com TODAS as linhas consumidas; o restante
  vira um `.draining.*` novo (divisão atômica, AMEND-1 §4 Fase 5).
- **(b) Unicidade — nunca duplica.** r aparece no máximo UMA vez no log canônico (guarda `_drain_sha256` na
  janela `K_TAIL_WINDOW`, mais a rejeição de 4-tupla duplicada).
- **(c) Vivacidade condicionada.** Se existir um drainer futuro deste projeto que ganhe a trava canônica, r
  chega ao log canônico exatamente uma vez. A exceção é r em quarentena (`.malformed.*`, `.quarantined.*`,
  `.test-origin.*`, `.corrupt-header.*`): fica no disco, contado como QUARENTENADO, nunca apagado e nunca
  contado como perdido.

**Na prova (W2.5):** depois de um drain final até ponto fixo na árvore descartável, todo r ∈ R aparece no log
exatamente uma vez, salvo as células de quarentena plantadas. «Contagem igual antes e depois» NÃO serve.
**Em produção:** o G6 (§8.2) mede a violação de (a)–(c) que deixou rastro no journal.

**O journal NÃO entra no INV-NP.** É contabilidade forense de melhor esforço (AMEND-1 «Loss accounting»).

### 3.2 As três pernas

| perna | quem | quando | o que recolhe | código |
|---|---|---|---|---|
| **1** | o próprio dono, durante a vida | a emissão vê `should_drain()` verdadeiro (spool próprio com ≥ 100 linhas, ou idade > 100 ms) e ganha a trava canônica SEM bloquear (AMEND-3) | o próprio spool e, como a fase 2 é global, os órfãos | `audit_emit.py:2790-2791`; `spool_writer.py:1082-1119`, `:2366-2371` **[disco]** |
| **2** | o próprio dono, na saída | SÓ se houver conteúdo próprio: spool próprio não vazio (um `stat`) OU o sinalizador `_OWN_DRAIN_PENDING` ligado (§4.1); em hook, com prazo (§4.2) | o próprio spool e os órfãos | auxiliar de saída chamado por `_atexit_drain` (`:2573`) e por `_signal_drain_handler` (`:2590`) |
| **3** | QUALQUER drainer seguinte deste projeto que ganhe a trava canônica (perna 1 ou 2 de outro processo) | a próxima drenagem de outro emissor | spools de PID morto (`:1343`) e TODO `.draining.*`, inclusive de PID vivo (`:1277-1317`) | `_phase2_sweep_and_rename` dentro do `with FileLock` de `drain_now` (`:2366-2371`) **[disco; consenso r1]** |

**Não existe perna de `SessionStart`** (§2.4).

### 3.3 Quem cumpre a perna 2 quando o caminho rápido a pula

Ninguém precisa: o caminho rápido só é tomado quando a perna 2 seria VÁCUA (spool próprio ausente ou vazio, e
sinalizador desligado). Os órfãos dos outros PIDs nunca foram da perna 2 de quem não tem conteúdo; ficam com a
perna 3. Quando é o PRAZO (ou a trava não obtida) que corta a perna 2 de quem tem conteúdo, o spool fica intacto
no disco e, morto o PID, a perna 3 o recolhe (`:1343`).

### 3.4 Vivacidade, reuso de PID e limites

- **Reuso de PID por processo alheio:** `_is_alive_pid` diz «vivo» (`:1233-1245`), e a perna 3 pula o spool
  órfão até ele morrer — ATRASO, não perda.
- **Reuso de PID por outro hook deste projeto:** o processo novo adota o cabeçalho do spool existente e
  recupera o ordinal (`_ensure_spool_header`, `:746-775`) **[disco]**, e drena nas próprias pernas 1 e 2.
- **Ninguém mais emite:** os órfãos ficam no disco, duráveis; o check do `/ceo-boot` os mostra (§9).
- **Lote limitado:** cada drain processa ≤ `K_MAX` = 100 entradas (`:53`). A W0.5 mede se a perna 3 alcança
  a fila sob rajada (§6.4).
- **Residência fora da cadeia.** O spool é PRÉ-cadeia (sem HMAC): quanto mais tempo um evento fica no spool,
  maior a janela em que adulteração ou remoção não deixam elo quebrado. Por isso o travamento tem sinal em
  ≤ 1 h (§4.3), e os spools órfãos aparecem como taxa no boot (§9).

### 3.5 O escritor direto `agent_spawn`

O `audit_log.append_entry` escreve no log canônico sem spool e sem `record_id` (`audit_log.py:667-700`,
`:1280-1296`) **[disco]**. No estresse, cada linha `agent_spawn` é identificada por um `desc_hash` único que o
teste controla, e o INV-NP vale também para ela. Há dois caminhos de PERDA pré-existentes, fora do spool: com
a trava canônica ocupada por mais de 2,5 s, o `append_entry` grava só o breadcrumb
`lock timeout (stale?)  would-log=…` truncado em 200 caracteres (`audit_log.py:1325-1329`); e com `OSError`
no append, só `append failed: …` (`:1323-1324`) **[disco]**. Os dois já têm ocorrência real (§2.1). A W2 REDUZ
o primeiro (as saídas sem conteúdo deixam de tomar a trava canônica) e passa a MEDIR os dois (G7, §8.2). Não
os elimina — fica declarado (§11). No estresse, qualquer breadcrumb `would-log`, `append failed`,
`spool append failed` ou `journal flush failed` reprova.

---

## §4 Decisão

### 4.1 Auxiliar de saída e caminho rápido (W2.2)

Um **auxiliar de saída** único, chamado por `_atexit_drain` E por `_signal_drain_handler`, e NUNCA por
`drain_now(force=True)`. Em ordem:

1. **`sys.stdout.flush()` e `sys.stderr.flush()`**, cada um em `try` próprio (fluxo fechado ou pipe quebrado
   é ignorado). Com isso a decisão do hook sai ANTES de qualquer espera (§2.1). É barato e NÃO substitui o
   prazo: se o harness só consome a decisão na saída do processo, quem a protege é o prazo (calibração, §6.4).
2. **Flush do buffer do journal do próprio PID**, se não estiver vazio. A trava do journal espera no máximo o
   orçamento restante (§4.2); com o prazo vencido, uma única tentativa sem bloquear (`timeout=0`, AMEND-3).
   Perder envelopes de journal não fere o INV-NP (§3.1).
3. **Decisão do caminho rápido:** UM `stat` do próprio spool (`_spool_path(os.getpid())`) e o sinalizador
   em processo `_OWN_DRAIN_PENDING`, **à prova de falha**:
   - LIGA imediatamente ANTES do `os.rename` do spool do próprio PID na fase 2 (`:1383-1384`, quando
     `pid == our_pid`) — se o rename falhar, fica ligado (custa uma drenagem a mais, nunca perda);
   - LIGA quando um `drain_now` deste processo termina com `ok=False`;
   - DESLIGA só depois de a fase 5 consumir por inteiro o `.draining` próprio E a remoção dele ser
     CONFIRMADA (o `unlink` retornou sem erro); divisão com restante o mantém ligado;
   - DESLIGA também quando o `.draining` próprio vai para quarentena (estado terminal; nada pendente).
4. **Spool próprio ausente ou com 0 byte, e sinalizador desligado ⇒ sai.** Sem trava canônica, sem
   `listdir`/`scandir`/`glob`/`iterdir`.
5. **Caso contrário ⇒ UMA tentativa de drenagem** (§4.2), nunca laço.

**Células obrigatórias (`-k fast_path` e `-k flag`; nenhum seletor é substring do nome do módulo, §6.5):**

- (a) sem spool próprio, com envelopes no buffer do journal ⇒ o flush do journal roda;
- (b) `.draining` próprio deixado por exceção injetada ENTRE o rename e a fase 5 ⇒ o sinalizador está ligado e
  a saída força a drenagem;
- (c) **o auxiliar de saída é chamado no atexit E no sinal**; a lógica não está em `drain_now(force=True)`
  (um teste falha se for movida);
- (d) zero chamadas a `os.listdir`, `os.scandir`, `glob` e `Path.iterdir` no caminho rápido, contadas por
  envoltório e nunca por tempo;
- (e) o teste 4 de `test_spool_drain_contended_skip.py` (`:220-231`: `drain_now(force=True)` direto, sob trava
  externa ⇒ `ok=False`, `error="canonical_lock_timeout"` e o breadcrumb) fica **intacto** **[disco]**;
- (f) um órfão de PID morto é recuperado pelo drain OPORTUNISTA (`force=False`) do próximo emissor (o teste 3
  atual usa `force=True`, `:195-217`);
- (g) o `.draining` próprio consumido por OUTRO drainer ⇒ o sinalizador segue ligado, a saída faz a drenagem
  completa, sem erro nem perda;
- (h) spool próprio em quarentena (`.malformed`) ⇒ uma tentativa só, sem laço;
- (i) SIGTERM honra o caminho rápido e o prazo;
- (j) o `flush` de stdout e stderr acontece ANTES de qualquer aquisição de trava (espião na ordem das chamadas).

### 4.2 Prazo na drenagem de saída de hook e entrega da decisão BLOCK (W2.2-bis; MF-W2-3, MF-R2-W2-2)

**Escopo: processo de HOOK.** O prazo vale quando o processo foi lançado como hook: `Path(sys.argv[0])`
resolvido mora no diretório de hooks do próprio módulo (`_HOOKS_DIR`, `spool_writer.py:29`). O wrapper lança
exatamente esse caminho (`HOOK_SCRIPT="$HOOKS_DIR/$1"`, `_python-hook.sh:304`; `exec` em `:413`) **[disco]**.
Processos que NÃO são hook (scripts de `.claude/scripts/`, `pytest`, Workflows) não têm timeout do harness: na
saída eles esperam a trava canônica por `SPOOL_LOCK_TIMEOUT`, como hoje, mas com o mesmo caminho rápido, a
mesma classificação silenciosa (`exit_deadline_skip`) e o mesmo portão STARVED (§4.3). Sem esse escopo, todo
processo longo cairia SEMPRE no salto e deixaria o spool para a perna 3, aumentando a residência fora da
cadeia sem ganho nenhum.

**Âncora** (MF-R2-W2-2): `âncora = min(_IMPORT_ANCHOR, monotonic_agora − idade_do_processo)`.

- `_IMPORT_ANCHOR = time.monotonic()`, gravada no import do `spool_writer`.
- `idade_do_processo` lida do KERNEL, só na saída e só no caminho lento (o caminho rápido não paga nada):
  - **macOS:** `sysctl({CTL_KERN=1, KERN_PROC=14, KERN_PROC_PID=1, pid})` via `ctypes.CDLL(None)`; os 16
    primeiros bytes da `struct kinfo_proc` são o `struct timeval p_starttime`; idade = `time.time() − início`.
    **Medido nesta máquina:** retorno 0, `kinfo_proc` de 648 bytes, custo de 2,6–3,3 ms com o import do
    `ctypes` **[medido: redator, macOS 27.0, CPython 3.9.6]**.
  - **Linux:** o campo 22 (`starttime`, em ticks desde o boot) de `/proc/self/stat`, lido DEPOIS do último
    `)` (o `comm` pode conter espaços e parênteses); idade = `time.clock_gettime(time.CLOCK_BOOTTIME) −
    starttime / os.sysconf("SC_CLK_TCK")` **[inferência; NÃO medido — o host é macOS, onde
    `time.CLOCK_BOOTTIME` não existe]**.
  - **Recurso declarado:** qualquer falha (plataforma sem leitura, erro do `ctypes`, tamanho inesperado,
    parse inválido, idade negativa, não finita ou no futuro) ⇒ vale `_IMPORT_ANCHOR`. O resíduo da âncora
    tardia fica só nesse caso (§11).
- **Direção do erro:** o `min` só pode ADIANTAR a âncora (menos tempo, lado seguro). Um relógio de parede que
  salta para trás subestima a idade, mas o `min` limita o erro ao da âncora no import.
- O início lido do kernel INCLUI o tempo do wrapper, porque o `exec` mantém o PID (`_python-hook.sh:413`)
  **[disco; consenso r2]**. Exceção: no caminho bloqueante do adaptador grok o Python roda como FILHO
  (`_CEO_HOOK_STDOUT="$(...)"`, `:420`), e o tempo do wrapper antes dele fica de fora (declarado, §11).

**Prazo.** `EXIT_DEADLINE_S = T_min − EXIT_MARGIN_S`, constantes canônicas.

- `T_min` = o MENOR `timeout` entre as registrações de hook do `.claude/settings.json` e dos perfis em
  `templates/settings/`. **Hoje: 3 s** — a registração PostToolUse de `check_skill_reference_read.py`
  (`.claude/settings.json:440-441`); nos perfis shipados o mínimo é 5 s **[disco]**.
- **Teste de deriva:** recalcula `T_min` dos arquivos e reprova se `EXIT_DEADLINE_S + EXIT_MARGIN_S > T_min`.
- **Valores INICIAIS** (pré-registrados, R2-5): `EXIT_MARGIN_S` = 1,0 s ⇒ prazo de 2,0 s contados da âncora.
- **Regra da margem:** margem ≥ p99 medido do encerramento depois do auxiliar de saída (interpretador + leitura
  do harness) × 1,5. Se não couber, encolhe o PRAZO, nunca a margem. Se a margem ≥ `T_min`, a W2 PÁRA e vai ao
  Owner (parada pré-registrada). A medição é declarada como da máquina do Owner: a casa já mediu 77 ms local
  contra 209–435 ms na CI para os mesmos hooks (CLAUDE.md §5).
- Mínimo global, e não o timeout de cada hook: o processo não sabe por qual registração foi chamado.

**Aplicação** (`restante = EXIT_DEADLINE_S − (monotonic() − âncora)`):

1. `restante ≤ 0` ⇒ nenhuma tentativa na trava canônica; o spool fica no disco (`exit_deadline_skip=True`).
2. A trava canônica espera `min(SPOOL_LOCK_TIMEOUT, restante)`. `drain_now` ganha um parâmetro nomeado
   opcional com o instante-limite absoluto; sem ele, o comportamento é o de hoje (teste 4).
3. Obtida a trava, o prazo é conferido de novo IMEDIATAMENTE antes da fase 2; vencido, solta sem listar.
4. Na seção crítica, as esperas por trava por PID (rename da fase 2, `:1374`; compactação, `:2276`) usam
   `min(timeout atual, restante)`; o estouro segue os desvios que JÁ existem (pular o PID; pular a compactação).
5. **Não obter a trava na saída** ⇒ `DrainStats.exit_deadline_skip=True`, `ok=True`, SEM o breadcrumb
   `drain canonical lock timeout`, e passa pelo portão STARVED (§4.3). O campo existe só em processo, nunca é
   serializado (mesmo regime do `contended_skip` do AMEND-3).
6. **Parte não preemptível:** uma listagem, ≤ `K_MAX` entradas, um append com `fsync` e as compactações dos
   PIDs drenados — limitada pelo tamanho do diretório e por `K_MAX`; a W0.5 a mede.

**Drain oportunista ANTES da decisão** (§2(f) do consenso r2). É a mesma classe, antes do stdout: o
`audit_emit` drena em linha quando o spool próprio passa de 100 ms (`audit_emit.py:2790-2791`), e esse drain lista
o diretório e pode esperar nas travas por PID. Regra pré-registrada: se a célula da W0.5 (§6.4) medir o
intervalo «decisão tomada → stdout escrito» acima da margem, a MESMA regra de prazo (âncora, `restante`,
esperas limitadas, salto silencioso) passa a valer para o drain oportunista DENTRO do pacote da W2.

**Por que não é «anômalo» e não fere o ADR-186.** O trabalho cortado é durabilidade POSTERIOR à decisão, com
a perna 3 como garantia. O ADR-186 manda prazo fail-CLOSED para verificação INCOMPLETA do matcher canônico;
aqui o prazo protege a ENTREGA de uma decisão já tomada. É a cura da CLASSE «trabalho longo dentro de guard
vira allow».

**Controle de ENTREGA DE DECISÃO (S1, §6.1):**

- **Guard sintético de IMPORT TARDIO** (MF-R2-W2-2): imprime BLOCK depois de trabalho simulado e só ENTÃO
  importa o `audit_emit` e emite, no molde do `check_canonical_edit.py`. É ele que roda nas células de entrega;
  um guard que importa cedo seria verde pela razão errada.
- **Medição (W0.5, fora do CI):** ≥ 9 saídas concorrentes, diretório com ~220 mil entradas, portador externo da
  trava canônica; o driver aplica a regra do harness (processo que passa do timeout é morto e a decisão,
  descartada). Vermelho no HEAD pré-registrado; verde com a estatística de §6.4.
- **Calibração contra o harness REAL** (§6.4): sem ela, S1 é declarado no material assinado como prova contra
  um MODELO do harness.
- **Prova estrutural (CI, `-k deadline` e `-k anchor`),** com relógio falso e leitor do kernel falso injetados,
  e espião no `FileLock`; nenhuma asserção de tempo absoluto:
  - `restante ≤ 0` ⇒ zero aquisições da trava canônica e zero listagens;
  - timeout passado à trava = `min(SPOOL_LOCK_TIMEOUT, restante)`;
  - âncora = `min(import, kernel)`; leitor do kernel que falha, devolve idade negativa ou no futuro ⇒ âncora do
    import;
  - processo NÃO-hook (argv fora de `_HOOKS_DIR`) ⇒ espera `SPOOL_LOCK_TIMEOUT`, sem prazo de processo;
  - não obter a trava ⇒ `exit_deadline_skip`, spool próprio intacto (nem renomeado nem apagado), sem o
    breadcrumb `drain canonical lock timeout`; o drain oportunista seguinte de OUTRO processo o recolhe;
  - teste de deriva da constante contra os settings.

### 4.3 Trava canônica presa vira sinal em ≤ 1 h (MF-R2-W2-1)

**Requisito.** Uma trava canônica presa vira sinal em ≤ T, com **T = 1 h** (`STARVED_LOG_IDLE_S = 3600`,
pré-registrado), SEM volume por saída. O AMEND-3 só aceitou silenciar a contenção benigna com a condição de
manter observável um portador travado (MF-1); o salto silencioso da §4.2 não pode regredir isso. O motivo é de
segurança, não de operação: enquanto a trava está presa, os eventos ficam no spool, PRÉ-cadeia (§3.4).

**Mecanismo de referência** (o builder pode trocar por equivalente que preserve o requisito e os controles):

- **Portão** — todos verdadeiros:
  1. caminho LENTO de saída (há conteúdo próprio);
  2. houve tentativa real na trava canônica, com espera > 0, e ela terminou em `FileLockTimeout` (uma saída que
     nem tentou, por `restante ≤ 0`, NÃO passa — isso evita o falso positivo de projeto ocioso + guard lento);
  3. UM `os.stat` do log canônico (`_canonical_log_path()`) mostra `agora − st_mtime > T`. Quem segura a trava
     e trabalha anexa e faz o log avançar; depois da cura, só processos com conteúdo tomam a trava (o caminho
     rápido não a toca), então trava ocupada com log parado há mais de 1 h é patologia. Log ausente ⇒ não
     dispara.
- **Taxa limitada:** um carimbo `audit-log.starved-stamp`, no MESMO diretório do `audit-log.errors`
  (`_log_family_dir()`), modo 0600, aberto com `O_NOFOLLOW`. Só escreve se o carimbo estiver ausente ou com mtime
  mais velho que T; atualiza o carimbo e grava UMA linha. Corridas entre saídas no mesmo instante produzem, no
  máximo, uma linha por saída concorrente naquele instante — limite pequeno e declarado.
- **Texto distinto e datado:** `{ts} spool_writer: drain canonical lock STARVED (exit): canonical log idle >
  3600s while exit drain timed out on the lock`. Contém «STARVED», como o do AMEND-3, e se distingue dele por
  «(exit)».
- **Custo:** zero no caminho rápido; nas saídas lentas que não obtiveram a trava, um `stat` do log e, só com o
  log parado, um `stat` do carimbo.

**Prazo efetivo.** O sinal sai na 1.ª saída com conteúdo que não obtém a trava DEPOIS de T. Num projeto em uso,
isso é T mais o intervalo até a próxima emissão. Sem nenhum emissor, nada novo entra no spool, e o G3 do boot
cobre os órfãos antigos (declarado, §11).

**Controles (`-k starved`), em árvore descartável, com `os.utime` para simular T (sem espera real):**

- **positivo:** portador externo segura a trava canônica; o mtime do log é posto em `agora − T − 1`; uma saída
  com conteúdo e `restante > 0` ⇒ exatamente UMA linha STARVED (exit);
- **taxa:** 2.ª saída na mesma janela ⇒ nenhuma linha nova; carimbo envelhecido além de T ⇒ uma linha nova;
- **vermelho que prova que o G3 sozinho não basta:** o mesmo cenário com o comportamento do rascunho r1
  (salto silencioso, sem portão) ⇒ nenhum sinal antes de 24 h ⇒ o teste do sinal em ≤ T REPROVA (mutante
  «sem portão STARVED na saída»);
- **negativos:** portador presente com o log fresco ⇒ nenhuma linha; log parado sem portador (a trava é obtida)
  ⇒ nenhuma linha; `restante ≤ 0` com o log parado ⇒ nenhuma linha; caminho rápido ⇒ nenhum `stat` do log.

### 4.4 Journal vazio removido na origem, só pela compactação (W2.3)

Em `_journal_compact_drained` (`:2248-2301`), sob a trava do PRÓPRIO journal (`_journal_flock_path(pid)`):

1. reexaminar a existência do journal SOB a trava; ausente ⇒ retorno silencioso (hoje o `exists()` vem antes
   da trava, `:2265`);
2. ler e filtrar como hoje (`:2277-2291`; linhas que não decodificam ficam);
3. **resultado vazio ⇒ `os.unlink(journal)` sob a trava**, sem escrever `.compact.tmp`; `FileNotFoundError`
   é retorno silencioso;
4. resultado não vazio ⇒ o caminho atual (`.compact.tmp`, `fsync`, `os.replace`), sem mudança.

**Por que é seguro.** Os únicos abridores do ARQUIVO do journal são o flush (`:950-966`, `O_CREAT|O_APPEND`
pelo caminho, sob a mesma trava), a compactação (sob a mesma trava) e a reconciliação morta; nenhum outro
módulo abre `audit-pending.*` **[disco: censo por `grep`; vira teste, §6.2]**. Um flush posterior do dono vivo
reabre pelo caminho e recria o arquivo. A TRAVA do journal nunca é apagada.

**Só a compactação** (MF-R2-W2-4). Ela é o ÚNICO produtor de journal com 0 byte: o flush só cria o arquivo com
conteúdo não vazio (`:947-949`, `:959-963`) **[disco]**. A remoção pelo dono na saída SAI do desenho e do plano.
Resíduo raro: `O_CREAT` seguido de falha no `write` (disco cheio) deixa um journal com 0 byte; a W2.6 cuida
dele (§11).

**Controle de intercalação (`-k origin`), por barreira determinística, sem `sleep`**:

- o dono abre o journal para flush e pára na barreira; o compactador decide remover; libera;
- **mutante 1**, remoção FORA da trava: o envelope do dono vai para um inode desligado ⇒ VERMELHO;
- **mutante 2**, remoção com restante não vazio: o manifesto de hash do conteúdo forense acusa ⇒ VERMELHO;
- a cura ⇒ VERDE.

### 4.5 Regra de travas: nenhum hook apaga `*.lock` (MF-W2-2)

- **Nenhum hook faz `unlink` de caminho `*.lock`**, de nenhum módulo e por nenhum motivo (§2.4).
- **T1 (padrão).** As travas ficam. O estoque é limpo pela W2.6, que passa a ser **RECORRENTE** (§5). Limiar
  OPERACIONAL, não de segurança: com **≥ 100 mil travas**, o check do `/ceo-boot` recomenda rodar a W2.6 (§9).
  No ritmo medido, o estoque volta a essa faixa em ~2 a 4 semanas de uso intenso **[inferência: rascunho r1 e
  DevOps r2]**.
- **T2 (condicional).** Re-checagem de inode no `_lib/filelock.py` (kernel, `check_arbitration_kernel.py:173`):
  depois do `flock`, `fstat(fd).st_ino == stat(path).st_ino`, senão nova tentativa. Pacote de kernel PRÓPRIO.
  **Gatilho numérico pré-registrado** (qualquer um): na célula «~150 mil travas» da W0.5, com ≥ 9 saídas
  concorrentes de processos com conteúdo, `exit_deadline_skip` > 0 OU p95 da saída acima do orçamento; OU a
  W2.6 precisar rodar mais de 1× por mês; OU o projeto rodar num Linux de vida longa (§6.3, H3). Mesmo com a
  T2, a remoção de travas em hook volta a debate com o portador do VETO.
- **T3 (relocação).** FORA (C14 do consenso r1).
- **«O dono apaga as próprias travas na saída»:** fora deste ADR; só volta com as quatro garantias da §2(b) do
  consenso r1 e novo julgamento do portador do VETO.

### 4.6 GC dentro do hook: fora do pacote base (W2.4 CONDICIONAL)

Com §4.4 não há produtor de journal vazio; com §4.5 nenhuma trava se apaga em hook. **O pacote base da W2 não
leva GC no hook**, e o Check `-k gc` SAI da lista de Checks da W2. Se o fluxo H1 (§6.3), medido depois do LAND,
ficar acima do limiar, o GC de journal de PID morto volta como pacote PRÓPRIO, com as condições já fixadas: de
carona na listagem da fase 2, DEPOIS de soltar a trava canônica; teto de ≤ 200 arquivos e ≤ 50 ms por execução
(a confirmar na W0.5); só o padrão de journal (§4.8), só 0 byte, PID morto; reexame sob a trava do journal;
nenhum `*.lock`; a lista de §4.9; a tabela de §5.2, com o porquê de cada diferença.

### 4.7 Regra de versões mistas (MF-W2-4)

- **Invariante estrutural:** nenhum caminho de trava e nenhum caminho de journal mudam. **Prova mecânica:**
  teste dourado dos construtores de caminho, byte a byte contra o HEAD `48f03b3a`, para um PID de amostra
  (`-k golden_paths`): `_spool_path` → `audit-spool.<pid>.jsonl`; `_journal_path` → `audit-pending.<pid>.journal`;
  `_spool_flock_path` → `audit-spool.<pid>.jsonl.lock`; `_journal_flock_path` → `audit-pending.<pid>.journal.lock`;
  `_draining_path` → `audit-spool.<pid>.draining.<epoch>`; `_aggregate_journal_path` → `audit-pending.journal`;
  `_aggregate_journal_lock_path` → `audit-pending.journal.aggregation.lock`; `_canonical_log_lock` →
  `audit-log.lock` (`spool_writer.py:429-481`) **[disco]**.
- **Regra para emendas futuras:** mudar o caminho de uma trava ou de um journal exige transição explícita, com
  dupla trava ou janela sem adquirentes (a classe da antiga W2.3).
- **LAND** com as sessões DESTE projeto fechadas, declarado no material assinado.
- **Efeitos declarados da convivência** (LAND com sessão aberta, ou adopter via `upgrade.sh` com sessão
  aberta): o compactador velho que encontre o journal removido grava `journal compact failed:
  FileNotFoundError` (ruído transitório, não perda); processos velhos seguem sem caminho rápido, sem prazo e
  sem portão STARVED até sair; o compactador velho ainda reescreve journal com 0 byte, e o novo o remove na
  próxima compactação daquele PID; nenhuma combinação cria dois donos para uma trava.
- **Adopters:** o estoque deles não é limpo pela W2 (a W2.6 é operação do Owner, fora do repositório); a
  decisão BLOCK fica protegida pelo prazo; a limpeza do estoque do adopter é follow-up (§13, para ciência).

### 4.8 Nomes: expressões regulares ancoradas

Usadas pela W2.6, pelo check do `/ceo-boot`, pelos scripts G6/G7 e pelo Check de sucesso (o MESMO texto em
todos):

```
RE_SPOOL_LOCK   = r"audit-spool\.([1-9][0-9]{0,9})\.jsonl\.lock"
RE_JOURNAL      = r"audit-pending\.([1-9][0-9]{0,9})\.journal"
RE_JOURNAL_LOCK = r"audit-pending\.([1-9][0-9]{0,9})\.journal\.lock"
RE_DRAINING     = r"audit-spool\.([1-9][0-9]{0,9})\.draining\.([0-9a-f]{8})"
RE_ACTIVE_SPOOL = r"audit-spool\.([1-9][0-9]{0,9})\.jsonl"
```

- **Só com `re.fullmatch` e `re.ASCII`.** Nunca `match`, `search` nem `^…$` (o `$` do Python aceita um `\n`
  final); nunca `\d` (casa dígitos Unicode).
- PID só de dígitos ASCII, sem zero à esquerda, de 1 a 10 dígitos.
- **Proibido reusar `_parse_spool_pid`** (`:1248-1257`) para decidir remoção: usa `int()`, que aceita `_`,
  espaços, `+` e dígitos Unicode.
- O journal agregado e a trava de agregação NÃO casam (`:455-462`).
- **Linhas do `audit-log.errors`** (G2, G7, STARVED): o arquivo mistura dois formatos de carimbo — o do
  `spool_writer` (`AAAA-MM-DDTHH:MM:SSZ spool_writer: …`, `:611-613`) e o do `audit_log`
  (`[AAAA-MM-DDTHH:MM:SSZ] …`, `audit_log.py:1122-1124`) **[disco; medido: 31.680 e 3 linhas]**. As regex de
  linha casam os dois, ancoradas no início, e a comparação de tempo é entre DATETIMES em UTC, nunca entre
  textos.

### 4.9 O que nunca se apaga

Nem em hook, nem na W2.6:

- `.draining.*`, `.malformed.*`, `.quarantined.*`, `.test-origin.*`, `.corrupt-header.*` (`:581-582`),
  `.tmp.*` e `*.compact.tmp`;
- spool ativo `audit-spool.<pid>.jsonl`, de qualquer tamanho;
- journal com conteúdo (> 0 byte) e TODA a família dele;
- o journal agregado e a trava de agregação;
- a família do log: `audit-log.jsonl`, `audit-log.lock`, `audit-log.errors`, **`audit-log.starved-stamp`
  (novo, §4.3)**, a chave, o sal, os sidecars e os arquivos rotacionados. O `audit-log-retain.py` casa só
  `audit-log-AAAA-MM(-N)?.jsonl` (`:27-28`) e não toca o carimbo **[disco]**;
- travas e temporários de outros módulos no mesmo diretório (`ceo-overhead-window*.json.lock`,
  `subagent-lifecycle.json.lock`, `output-scan-dedup.lock`, `ceo-boot-tasks-emitted.json.lock`,
  `statusline-snapshot.json.tmp.N`) **[medido: QA r1]**;
- tudo que não for arquivo comum ou que tenha `st_nlink > 1`;
- qualquer coisa fora do state dir resolvido;
- **em hook:** qualquer `*.lock`, sem exceção.

### 4.10 O que NÃO muda

As fases 2 a 5, a ordem da cadeia HMAC, a reconstrução do `prev_hmac` pela cauda e a guarda `_drain_sha256`;
`_lib/audit_hmac.py`, `_lib/canonical_json.py` e `audit-verify-chain.py`; o caminho oportunista do AMEND-3
(`timeout=0`, `contended_skip`, `STARVED` com gate), salvo a regra condicional da §4.2; `drain_now(force=True)`
sem prazo (teste 4); o kill-switch `CEO_AUDIT_SYNC_MODE=1`; nenhuma ação nova em `_KNOWN_ACTIONS`; nenhum toque
no `audit_emit.py`.

---

## §5 W2.6 — limpeza do estoque, endurecida e RECORRENTE (MF-W2-6)

O script fica fora do repositório, é rodado pelo Owner e é confinado ao state dir. **Sob T1 ele é RECORRENTE**:
roda de novo quando o `/ceo-boot` acusar ≥ 100 mil travas (§9), a cada ~2 a 4 semanas de uso intenso
**[inferência]**. Rodar mais de 1× por mês é gatilho da T2 (§4.5). A 1.ª execução pode ser já.

### 5.1 Resolução e confinamento

- State dir pelo resolvedor `_lib/runtime_paths.py` (`--state-dir`) + `/state`, NUNCA por slug derivado à mão
  (ADR-001, marcador M4). Com `CEO_AUDIT_LOG_DIR` ou `CEO_AUDIT_LOG_PATH` definidos, recusa (o state dir dos
  hooks diverge do resolvedor, `spool_writer.py:265-266`, `:407-412`).
- Diretório aberto com `O_RDONLY | O_DIRECTORY | O_NOFOLLOW`; recusa se for symlink, de outro dono ou com modo
  ≠ 0700.
- Cada remoção é `os.unlink(nome, dir_fd=dfd)`.
- **Reexame imediatamente antes de cada `unlink`:** `os.stat(nome, dir_fd=dfd, follow_symlinks=False)` com
  `S_ISREG`, `st_size == 0`, `st_nlink == 1`, o mesmo `(st_dev, st_ino)` da listagem e a família ainda sem
  conteúdo.
- **Simulação por padrão;** só remove com `--apply`.
- **Resíduo declarado:** a janela entre o reexame e o `unlink` (não existe «unlink se o inode for X»); com as
  sessões do projeto fechadas, não há adquirente vivo para explorá-la.

### 5.2 Predicado pré-registrado (uma ação por célula)

| célula | ação |
|---|---|
| **spool ativo ou `.draining.*` com PID VIVO** (prova positiva de emissor vivo; trava aberta e `flock` não mudam o mtime) | **RECUSA a execução inteira**, nomeando o PID |
| qualquer arquivo da família com mtime < 10 min | **RECUSA a execução inteira** (sinal de sessão viva deste projeto) |
| nome casa um dos 3 padrões (§4.8); arquivo comum; 0 byte; `st_nlink == 1`; PID morto; família sem conteúdo (journal ausente ou com 0 byte, sem spool ativo, sem `.draining.*` do PID); mtime ≥ 10 min | **APAGA** (a simulação conta; `--apply` apaga) |
| mesma célula, com PID vivo nas TRAVAS ou no journal (inclusive PID reusado por processo alheio) | **MANTÉM** a família inteira; contada como «pulada: PID vivo» |
| journal com conteúdo | **MANTÉM** a família inteira; o journal entra no manifesto de hash |
| symlink, hardlink (`st_nlink > 1`), diretório ou outro tipo | **MANTÉM** + aviso |
| quase-acertos (travas de outros módulos, `statusline-snapshot.json.tmp.N`, journal agregado, trava de agregação, `*.compact.tmp`, `audit-pending.0123.journal`, `audit-pending.12a.journal`, dígitos não ASCII, `audit-pending.1_0.journal`, nome com `\n` final) | **MANTÉM** (não casa) |
| spool ativo de PID morto, `.draining.*` de PID morto e todo sufixo de §4.9 | **MANTÉM** (a perna 3 os recolhe) |
| state dir symlink, de outro dono ou com modo ≠ 0700 | **RECUSA a execução** |

**Por que «PID vivo nas travas ⇒ pula a família», e não recusa total:** os 75.609 PIDs distintos ocupam ~76%
do espaço de PIDs do macOS **[medido: QA r1]**; recusar por qualquer PID vivo faria o script nunca rodar. A
recusa total fica para a prova positiva (spool ou `.draining.*` de PID vivo) e para o mtime recente.
**Resíduo:** um spool órfão cujo PID foi reusado por processo alheio provoca recusa FALSA (estimativa grosseira
de ~0,6% por spool órfão **[inferência: ~600 processos ÷ ~10⁵ PIDs]**); o script nomeia o PID, e o Owner
confere por `lsof`/`ps` sobre o caminho, nunca `pgrep -f`.

### 5.3 Execução e prova

1. **Simulação** com contagem POR CÉLULA, gravada no LEDGER com data e substrato (versão do CC, `python3` dos
   hooks, sha do script).
2. **Manifesto de hash** dos journals com conteúdo, antes e depois; qualquer diferença reprova.
3. **Contagem antes e depois** pelo MESMO método do critério (§6.3); um teste afirma contagem registrada =
   arquivos removidos.

---

## §6 Critérios de sucesso

### 6.1 Critérios que BARRAM o SIGN (segurança; domínio do VETO)

- **S1 — entrega de decisão** (MF-W2-3, MF-R2-W2-2): a célula de entrega da W0.5, com o guard sintético de
  IMPORT TARDIO, passa de VERMELHO (HEAD) a VERDE (cura) pela estatística da §6.4; a prova estrutural
  `-k deadline`/`-k anchor` fica verde; a calibração contra o harness real é feita ou a limitação é declarada.
- **S2 — INV-NP por conjunto:** verde no estresse (§6.2), cada mutante reprovando.
- **S3 — cadeia:** `verify_chain()` íntegro sobre a cadeia composta da §6.2, DEPOIS da W2.0 (§7).
- **S4 — trava presa vira sinal** (MF-R2-W2-1): os controles da §4.3 verdes, inclusive o vermelho do mutante
  «sem portão».
- **S5 — perda real medida** (MF-R2-W2-3): G6 e G7 implementados, com controle positivo verde (§8.2).

`truly_lost` NÃO é critério: está morto.

### 6.2 Estresse W2.5 (`-k invariant`; MF-W2-5)

- **Escritores em paralelo:** `agent_spawn` (`audit_log.append_entry`, depois da W2.0, `desc_hash` único);
  `audit_emit` pelo spool; drainers oportunistas e drenagens de saída; saídas pelo caminho rápido; saídas
  cortadas pelo prazo; `kill -9` no meio do drain; reuso de PID (adoção de cabeçalho, §3.4).
- **Recuperação de órfãos** pelo drain do próximo emissor, oportunista ou de saída, MESMO com todas as outras
  saídas pelo caminho rápido.
- **Composição da cadeia** (não só tamanho): N ≥ 1.000 elos, com ≥ 100 `agent_spawn`, ≥ 100 lotes de drain
  (linhas com `_drain_epoch`, que sobrevive no canônico, `spool_writer.py:1938-1942` **[disco]**), ≥ 50
  transições ADJACENTES entre as duas classes e ≥ 1 rotação no meio. Mil elos de um escritor só seria verde por
  vácuo para a condição 67.
- **Afirmações:** INV-NP por conjunto; `verify_chain()` sobre a cadeia composta; zero breadcrumb de perda;
  ao final, nenhum `.draining.*` nem spool órfão com conteúdo; **journals COM conteúdo foram produzidos antes
  do drain** (o H1 não pode ficar verde porque o journaling quebrou).
- **Guardas mecânicas** (`-k inode`, `-k openers`): o inode `(st_dev, st_ino)` de cada caminho `*.lock` fica
  ESTÁVEL do 1.º ao último uso (inode trocado = alguém apagou e recriou); o censo dos abridores de
  `audit-pending.*` é TESTE (só o `spool_writer.py`, e só flush, compactação e reconciliação), com módulo
  sintético que abre `audit-pending.1.journal` como controle positivo.
- **Mutantes da W2.5 = M-a..M-d**, cada um reprovando:
  - M-a: a fase 5 apaga um `.draining` parcialmente consumido (perda);
  - M-b: a guarda `_drain_sha256` desligada na recuperação (duplicata);
  - M-c: o salto por prazo apaga ou renomeia o próprio spool (perda);
  - M-d: a fase 2 renomeia o spool de um PID vivo sem a trava do spool (append em voo roubado, com barreira).

### 6.3 Higiene: fluxo (primário), teto (secundário) e travas (operacional)

**Método único de contagem:** uma listagem do state dir, `fullmatch` das regex de §4.8, `lstat` só onde a
categoria exige.

- **H1 — fluxo (primário).** `F = |{p ∈ D : p morto ∧ audit-pending.<p>.journal existe com 0 byte ∧ mtime ≥
  início da janela}| / |D|`, com D = os `pid` distintos das entradas da era-spool do log canônico (e dos
  arquivos rotacionados) com `wall_ns` na janela de 24 h, lidos por SCRIPT (não por `grep`).
  - **`|D|_min` ≥ 200** pré-registrado; abaixo dele, reprova (sem carga, nada fica provado).
  - **Vermelho MEDIDO no HEAD:** **|D| = 1.049, F = 0,999** (1.048 PIDs mortos com journal de 0 byte e mtime
    na janela; 0 com conteúdo), sobre o log corrente desde a rotação de 2026-10-01T17:23:56Z
    **[medido: redator, 2026-10-02T03:40Z]**. O esperado era F ≥ 0,9.
  - **Limiar: F ≤ 0,01** (ε pré-registrado, R2-5).
- **H2 — teto (secundário).** ≤ 1.000 journals com 0 byte no state dir INTEIRO depois de 24 h de uso normal, com
  as sessões do projeto paradas. **Só journals:** sob T1 as travas crescem ~15,8 mil por dia **[inferência]**,
  e aplicar o teto a elas reprovaria por construção.
- **H3 — travas (operacional).** Reportadas à parte, por nome; **≥ 100 mil ⇒ o `/ceo-boot` recomenda a
  W2.6**; não é limiar de segurança. Teto teórico: 2 × o espaço de PIDs — ~10⁵ PIDs no macOS; no Linux depende
  de `kernel.pid_max`, que pode chegar a 4.194.304 **[inferência; conhecimento do SO]**, por isso o Linux de
  vida longa é gatilho da T2.

### 6.4 W0.5 pré-registrada (QA MF-2/5/6; DevOps MF-3/7)

Pré-registro no LEDGER ANTES de rodar, em árvore descartável, com piso de `df` e limpeza confinada. Substrato
congelado: versão do CC (Q14), `python3` dos hooks, SO, sha do instrumento.

- **Matriz base 2³:** {saída sem spool próprio, com spool próprio} × {diretório vazio, ~220 mil entradas} ×
  {1 saída, ≥ 9 concorrentes}. Métricas: latência de saída, linhas `drain canonical lock timeout`, decisões
  descartadas, taxa de `exit_deadline_skip`.
- **Células extras:**
  1. **entrega de decisão** com o guard sintético de import tardio e portador externo da trava (§4.2);
  2. **estoque só de travas (~150 mil)** — o REGIME PERMANENTE sob T1, que decide a T2;
  3. **encerramento depois do auxiliar de saída** (calibra `EXIT_MARGIN_S` pela regra da §4.2);
  4. **intervalo desde o INÍCIO DO WRAPPER até a âncora** (o `_python-hook.sh` procura o Python e pode lançar
     subprocessos antes do `exec`); com a âncora pelo kernel, mede o resíduo do recurso no import;
  5. **drain oportunista ANTES da decisão**, com ~150 mil travas e ≥ 9 concorrentes: intervalo «decisão tomada
     → stdout escrito»; acima da margem ⇒ vale a regra condicional da §4.2;
  6. **vivacidade da perna 3 sob rajada:** contagem e idade dos spools órfãos com conteúdo ao fim da carga e
     depois de N emissores seguintes (`K_MAX` = 100);
  7. **calibração contra o harness REAL:** projeto descartável, CC congelado, **2 chamadas `claude -p`** (freio
     Q1): (C1) hook PreToolUse sintético que imprime BLOCK, faz o `flush` e atrasa a SAÍDA além do timeout
     registrado; (C2) o mesmo hook saindo rápido, como controle de que o hook bloqueia. O braço «sem `flush`» não
     gasta chamada: sem `flush`, os bytes não deixam o processo antes do fim dos `atexit` (§2.1), então um
     processo morto antes disso nunca entrega. Resultado de C1: bloqueou ⇒ o harness consome a decisão antes da
     saída, e o `flush` a protege; passou ⇒ o harness exige a saída dentro do timeout, e o prazo é a defesa (o
     modelo do driver fica calibrado). Sem a calibração, S1 é declarado como prova contra um MODELO.
- **Estatística:**
  - medir PRIMEIRO a taxa p̂ de decisão perdida no HEAD (célula 1);
  - o verde é 0 perdas em N, com N tal que o limite superior de 95% (regra do três, ≈ 3/N) ≤ p̂/10;
  - p̂ = 0 (vermelho não reproduzido) ⇒ «prova só estrutural», declarada no material assinado;
  - p95 só com N ≥ 100; abaixo disso, p90.
- **Esperado por célula depois da cura** (pré-registrado para não «relaxar» depois):
  - sem spool: razão p95 cheio/vazio ≤ 1,2;
  - com spool e ~150 mil travas: decisão entregue e prazo respeitado; razão NÃO exigida (sob T1, essa razão é
    vermelha por construção — a fase 2 de quem tem conteúdo ainda lista o diretório);
  - gatilho da T2 conforme §4.5.
- **`SPOOL_LOCK_TIMEOUT` re-medido** depois da cura.
- **Nada disso vira asserção de tempo no CI.**

### 6.5 Checks com a afirmação no código de saída (QA MF-17; consenso r2 §3(a) itens 5–7)

- **Módulo de teste renomeado** para `.claude/hooks/tests/test_spool_state_amend4.py` (oráculo = 0
  **[medido: redator]**). O nome não contém nenhum seletor.
- **Seletores:** `fast_path`, `flag`, `deadline`, `anchor`, `starved`, `origin`, `golden_paths`, `inode`,
  `openers`, `invariant` (e `gc` só se o GC voltar). Nenhum é substring de `test_spool_state_amend4`. A
  **guarda de seletor** afirma que cada `-k` casa EXATAMENTE os testes declarados do próprio item (igualdade de
  conjunto, não «≥ 1»).
- **Check da W2.4-bis** ganha um seletor dos testes NOVOS do check do boot (os 120 existentes de
  `test_ceo_boot*.py` são verdes hoje).
- **Check de sucesso da W2** — sai ≠ 0 quando:
  1. qualquer seletor falha ou casa conjunto diferente do declarado;
  2. **H1:** `|D|` < 200 ou F > 0,01 (script que lê `pid`/`wall_ns`);
  3. **H2:** mais de 1.000 journals com 0 byte (só journals; travas reportadas à parte, sem limiar);
  4. **guarda de regressão (G2):** linha `drain canonical lock timeout` datada depois do LAND + a janela de
     convivência — nunca prova de ausência de contenção;
  5. **G7** > 0 depois do LAND; **G6** com perda > 0;
  6. **decisão perdida:** lê o veredito que a W0.5 grava (caminho fixado no pré-registro); veredito ausente ⇒
     ≠ 0.
  - **O carimbo do LAND sai do commit do LAND** (`git log -1 --format=%cI <sha>`), validado como ISO e
    convertido para UTC; marcador literal ou formato inválido ⇒ saída ≠ 0. Comparação entre datetimes, nunca
    entre textos (o `'2' < '<'` do `awk` tornava o braço vácuo).
  - As regex são as de §4.8.
- **Check da W2.0** — §7.

---

## §7 Pré-condição do SIGN da W2: cura da condição 67 (MF-W2-1)

- **O defeito.** `audit_log.append_entry` lê a chave, o elo anterior e calcula o HMAC ANTES de tomar a trava
  canônica (`audit_log.py:1262-1278`; trava em `:1283`) **[disco]**: dois gravadores em paralelo encadeiam no
  mesmo antecessor. É a condição 67 assinada da v1.4.0-rc.1 (`test_two_writer_chain.py:13-16`).
- **Por que barra a W2.** Sem a cura, S3 só se prova EXCLUINDO o `agent_spawn`.
- **A cura:** chave, elo anterior e HMAC DENTRO do `with FileLock(...)`, DEPOIS de `rotate_if_needed`
  (`:1285`), conferido contra o contrato do AMEND-2; teste de barreira multiprocesso (envoltório sobre
  `read_prev_hmac` que sinaliza e espera, barreira < 2,5 s), VERMELHO no HEAD e VERDE com a cura; censo AST
  (toda chamada a `read_prev_hmac()` fora de teste fica dentro de `with FileLock(`), com módulo sintético como
  controle positivo; a docstring do `test_two_writer_chain.py` corrigida.
- **Check da W2.0** (consenso r2 §3(a) item 7): o **node id** do teste de barreira e o **node id** do censo
  AST — nunca o módulo inteiro, que tem 6 testes sequenciais verdes HOJE **[disco: docstring `:3-10`]**. O
  LEDGER guarda a execução VERMELHA no HEAD ANTES do patch, com o comando e o sha.
- **Custo:** `audit_log.py` é kernel (`check_arbitration_kernel.py:217`) ⇒ cerimônia de KERNEL; 150–300 mil
  tokens + ~50 mil do censo, 0 a 1 sessão **[plano]**.
- **A linha que aposenta a condição 67** vai no `CHANGELOG.md` do corte W7.
- **A vaga é a DECISÃO PENDENTE 1 do Owner (§13)** — o único pré-requisito do Owner para o SIGN da W2.

---

## §8 Reversão e gatilhos

### 8.1 Caminho de reversão (por PEÇA)

As peças são separáveis e se revertem uma a uma: (a) auxiliar de saída e caminho rápido, (b) prazo de saída,
(c) remoção do journal na origem, (d) portão STARVED de saída.

- **Imediato, sem cerimônia:** `CEO_AUDIT_SYNC_MODE=1`. O escritor deixa de usar o spool; na saída, sem spool
  próprio, o caminho rápido torna as peças inertes. É mudança de COMPORTAMENTO (AMEND-1 §5).
- **Definitivo:** `git revert` da peça, em cerimônia canônica (`spool_writer.py` é canônico, não kernel);
  status `SUPERSEDED-BY-REVERT`, sem ADR novo.
- **Reverter (b) REABRE a classe da decisão perdida; reverter (d) REABRE o travamento silencioso.** As duas só
  com decisão escrita do Owner. Gatilhos de higiene (G1, G3) revertem (c) ou (a), nunca (b) ou (d) sozinhos.
- **Sem chave de ambiente nova** (anti-churn).

### 8.2 Gatilhos (instrumentos LIGADOS, cada um com controle positivo)

| id | gatilho | instrumento (onde roda) | controle positivo | ação |
|---|---|---|---|---|
| **G1** | H1 > 0,01 (com `|D|` ≥ 200) OU H2 > 1.000, em **3 execuções do check em dias DISTINTOS e consecutivos de uso** | check do `/ceo-boot` + script do critério, mesmo método | (i) log sintético com D ≥ 200 PIDs mortos e journals de 0 byte ⇒ F > ε ⇒ ≠ 0; (ii) 1.001 journals sintéticos ⇒ ≠ 0 | reverter (c); investigar |
| **G2** *(guarda de regressão)* | linha `drain canonical lock timeout` datada depois do LAND + convivência; depois da cura, NENHUMA rota de saída a produz | contagem datada no `audit-log.errors` (§4.8) + a W0.5 re-rodada depois do LAND | no HEAD: 31.485 linhas **[medido: redator]**; em teste, o `drain_now(force=True)` direto sob trava externa a produz (teste 4) | achar o chamador; (a)/(b) se for da emenda |
| **G3** | `.draining.*` OU spool órfão com conteúdo (PID morto) com mais de 24 h | check do `/ceo-boot` (§9) | arquivo plantado com mtime de 25 h ⇒ sinaliza | reverter (a); investigar a perna 3 |
| **G4** | decisão BLOCK descartada | célula de entrega da W0.5, re-rodada depois do LAND e a cada versão nova do CC | o vermelho do HEAD, ou o mutante «auxiliar ignora o prazo» | (a)/(c) sob decisão do Owner; (b) nunca sem decisão escrita |
| **G5** | quebra de cadeia ATRIBUÍVEL à W2 depois da W2.0 (o elo quebrado, ou o antecessor, é linha anexada pelo drain, com `_drain_epoch`) | `audit-verify-chain.py` / `verify_chain()` sobre o log vivo e os rotacionados da janela | cópia descartável com um byte alterado numa linha anexada pelo drain ⇒ acusa e atribui à W2 | a peça envolvida; ADR-052 avisado |
| **G6** *(ATIVO na W2)* | **perda REAL:** `record_id` com envelope `commit` num journal, com `wall_ns` ≥ LAND, ausente do log canônico e dos rotacionados E de todo spool ativo ou `.draining.*` | script SÓ-LEITURA, fora de hook: `.claude/scripts/check-audit-real-loss.py` (nome proposto; oráculo = 0 **[medido: redator]**) | cópia descartável: uma linha canônica removida cujo `record_id` tem `commit` no journal ⇒ perda = 1, saída ≠ 0; o mesmo `record_id` em `.malformed.*` ⇒ QUARENTENADO, saída 0; em spool ⇒ PENDENTE, saída 0 | investigar; ADR-052 avisado; reverter a peça se for da emenda |
| **G7** *(novo)* | **perda real do escritor direto:** linha `lock timeout (stale?)  would-log=` ou `append failed:` do `audit_log` datada depois do LAND | contagem datada no `audit-log.errors` (formato `[ts]`, §4.8), pelo mesmo método do G2 | natural: 3 linhas `would-log=` reais em 2026-10-01/02 **[medido: redator]**; em teste: `append_entry` com a trava canônica segura por > 2,5 s numa árvore descartável ⇒ 1 linha ⇒ G7 = 1 | investigar a contenção; reverter a peça se a emenda a aumentou |
| **G8** | sinal STARVED (exit) (§4.3) | o próprio breadcrumb datado, lido pelo check do boot e pelo nightly | os controles `-k starved` | investigar o portador da trava; reverter (a)/(b) só se o portador for código da emenda |
| — | diretiva do Owner | — | — | qualquer peça |

**G6 em detalhe** (consenso r2 §2(c)):

- **Ordem de leitura**, para não acusar perda falsa em trânsito: (1) spools ativos, `.draining.*` e arquivos de
  quarentena; (2) o log canônico corrente, por um descritor aberto; (3) a lista e o conteúdo dos rotacionados,
  listados DEPOIS. Pelo INV-NP (a), um registro está sempre num spool ou no log, e a transição é só spool → log
  (append antes do `unlink`); a rotação renomeia o log, por isso os rotacionados são listados por último. Todo
  candidato a perda é reconferido numa 2.ª passada antes de ser reportado.
- **Quarentenado ≠ perdido:** `record_id` em `.malformed.*`, `.quarantined.*`, `.test-origin.*` ou
  `.corrupt-header.*` é contado à parte.
- **Limite inferior declarado:** o journal é de melhor esforço (buffer de até 10 envelopes); um registro cujo
  `commit` nunca chegou ao disco é invisível ao G6.
- **Onde roda:** no V-block do LAND (pós-LAND) e no nightly. O `nightly-hygiene.js` é canônico (oráculo = 1
  **[medido: redator]**): a dimensão nova do G6 e a classe G7/STARVED na dimensão (i) entram no pacote da W2 se
  couberem no teto de 8 paths; senão, no pacote canônico seguinte. Até a fiação do nightly landar, o check do
  `/ceo-boot` roda o G6 e o G7 a cada execução, com orçamento medido na W0.5.

### 8.3 Gatilhos herdados que este texto aposenta

- **`truly_lost > 0` em 7 dias:** MORTO; substituído pelo INV-NP nas provas, pelo G3 em vivacidade e pelo **G6
  e G7 em perda real** — o que o portador do VETO pediu na rodada 1, agora com instrumentos que ligam.
- **Taxa de quebra > 0,1% em 30 dias:** inavaliável enquanto a condição 67 existir (4 quebras em ~461 elos ≈
  0,9% **[plano, risco 11]**); substituído pelo G5.
- **«Drain lock contention caused production tool-call timeout»** (AMEND-1 §5, gatilho 2): fica, como G2 + G4 +
  G8.

---

## §9 Observabilidade pelo resultado, sem tocar o `audit_emit.py`

- **Nenhum evento por arquivo e nenhuma ação nova em `_KNOWN_ACTIONS`** (C17 do consenso r1). O sinal de
  travamento é BREADCRUMB datado (§4.3), não evento — não contradiz o C17.
- **Check advisory no `/ceo-boot`** (`ceo-boot.py`, oráculo = 0 **[medido: redator]**, no pacote do item livre
  L2; mapa de colisões), roda na skill, nunca em hook:
  - **travas** por NOME, numa listagem sem `stat` por entrada; **≥ 100 mil ⇒ recomenda a W2.6**;
  - **journals com 0 byte**, com `stat` limitado aos primeiros 2.000 journals por nome («≥ 2.000» quando o
    limite estoura — basta para decidir H2 ≤ 1.000);
  - **idade do `.draining.*` mais velho**;
  - **spools órfãos com conteúdo (PID morto) de QUALQUER idade, como TAXA** (contagem ÷ `|D|` das últimas 24 h)
    e a idade do mais velho — o resíduo visível do `exit_deadline_skip`;
  - **linhas STARVED (exit) e G7 datadas** na janela;
  - **no máximo UMA linha por execução** no `audit-log.errors` quando um gatilho (G1, G3, G6, G7, G8) dispara.
  - Orçamento de tempo medido na W0.5; uma varredura com `stat` por entrada levou 50,7 s **[medido: DevOps r1]**.
- **Os detectores por contagem TOTAL estão saturados** (`ceo-diagnose.py:371-373`/`:417`, `status.py:290`;
  31.683 linhas, sem rotação) **[disco; medido: redator]**. O sinal novo é distinto pelo TEXTO e lido com janela
  pelo boot e pelo nightly; a rotação do `audit-log.errors` (lane `H-03`) segue follow-up.
- **Contagens da W2.6 no LEDGER** (§5.3).

---

## §10 Opções consideradas

| opção | decisão | por quê |
|---|---|---|
| A. Relocar journals e travas (antiga W2.3) | rejeitada | duas travas para o mesmo recurso na convivência (C14) |
| B. GC de travas de PID morto em hook | rejeitada | VETO; sem re-checagem de inode, quebra a exclusão mútua |
| C. O dono apaga as próprias travas na saída | adiada | premissa falsa no caso `.draining` (§2.4); quatro garantias |
| D. T2: re-checagem de inode no `filelock.py` | condicional | pacote de kernel próprio, com gatilho numérico (§4.5) |
| E. Ligar a reconciliação de início de sessão | rejeitada na W2 | ~76 mil journals sob o timeout de 5 s do `SessionStart` |
| F. Evento por arquivo / ação nova no kernel | rejeitada | recria os arquivos; toca o kernel sem necessidade |
| G. Drenagem de saída só do próprio spool | não adotada | a varredura da saída é o veículo principal da perna 3 em hooks curtos **[inferência]** |
| H. `flush` de stdout e stderr antes da drenagem | **adotada** (§4.1) | medida: 1,54 s → 0,03 s até o 1.º byte; não substitui o prazo |
| H'. Fechar o stdout antes da drenagem | não adotada | depende da semântica do harness; a calibração (§6.4) informa se vale um follow-up |
| I. Chave de ambiente nova | não adotada | `CEO_AUDIT_SYNC_MODE=1` já cobre; anti-churn |
| J. Prazo por hook (timeout da própria registração) | não adotada | o processo não sabe sua registração; mínimo global + teste de deriva |
| K. Âncora só no import | **rejeitada** | tardia nos guards reais (§2.4); o VETO prevalece (consenso r2 §2(a)) |
| L. Censo AST + «armar o prazo no `main`» | reserva | só se a leitura do kernel se mostrar inviável; toca hooks canônicos e pesa no teto de paths |
| M. Prazo em TODO processo (não só hook) | rejeitada | processos longos sempre saltariam a drenagem, aumentando a residência fora da cadeia sem ganho (§4.2) |
| N. Sinal de travamento só pelo G3 de 24 h ou por linha do check do boot | rejeitada | latência de até 24 h; controle vermelho da §4.3 (MF-R2-W2-1) |

---

## §11 Consequências e resíduos declarados

**Positivas (+)**

- A decisão BLOCK sai antes de qualquer espera (`flush`) e deixa de depender do tamanho do diretório e da
  contenção (prazo), por qualquer causa de lentidão.
- As saídas sem conteúdo deixam de tomar a trava canônica: menos contenção para todos, inclusive para o
  `agent_spawn`.
- Os journals vazios deixam de se acumular (1/3 do estoque).
- A trava presa vira sinal em ≤ 1 h; a perda real passa a ser medida (G6, G7).

**Negativas (−)**

- Sob T1, as travas seguem crescendo; a W2.6 é manutenção RECORRENTE (fechar as sessões deste projeto a cada ~2
  a 4 semanas de uso intenso).
- O salto adia o spool para a perna 3 (residência PRÉ-cadeia maior durante o salto; sinal em ≤ 1 h se for
  travamento).
- Arquivo novo na família do log (`audit-log.starved-stamp`); `DrainStats` ganha um campo em processo e
  `drain_now`, um parâmetro opcional.

**Neutras (~)** — sem contenção, o caminho com conteúdo é idêntico ao de hoje.

**Resíduos declarados (vão para o material assinado)**

1. **Âncora pelo recurso do import:** só quando a leitura do kernel falha (ou no Linux, se o método não se
   confirmar no pacote); e no caminho bloqueante do adaptador grok, em que o tempo do wrapper antes do filho
   fica de fora.
2. **Semântica do harness:** sem a calibração da W0.5, S1 é prova contra um modelo.
3. **Timeout de adopter** abaixo de `EXIT_DEADLINE_S + EXIT_MARGIN_S` quebra a garantia sem que o teste do
   repositório veja.
4. **Parte não preemptível** da drenagem, proporcional ao estoque de travas sob T1.
5. **Journal com 0 byte** por falha de `write` depois do `O_CREAT`: raro, fica para a W2.6.
6. **~214 journals com conteúdo forense-only.**
7. **Perda pré-existente do `agent_spawn`** (`would-log`, `append failed`): reduzida, não eliminada, agora
   MEDIDA pelo G7.
8. **G6 é limite inferior:** não vê registro cujo `commit` nunca chegou ao disco.
9. **Sinal STARVED** depende de haver uma saída com conteúdo depois de T; detectores por contagem total
   saturados até a rotação do `audit-log.errors` (`H-03`).
10. **Recusa falsa da W2.6** por PID de spool órfão reusado por processo alheio (§5.2).
11. **Janela TOCTOU da W2.6** entre o reexame e o `unlink`.
12. **Mesmo UID:** um processo do mesmo usuário pode apagar ou forjar arquivos do state dir (fronteira de
    `CLAUDE.md` §5).
13. **Testes que leem o log canônico depois de rodar um hook em subprocesso** deixam de poder contar com o drain
    de saída do filho (o prazo vale também ali). Há 20 módulos de teste que rodam subprocesso e citam o log
    canônico; 8 deles já citam `drain_now` ou o modo síncrono **[medido: redator, `grep`]**. O pacote faz o
    censo e cada teste drena explicitamente no pai, ou fixa `CEO_AUDIT_SYNC_MODE=1` no filho, antes de afirmar.

---

## §12 Raio de explosão, regra 10×, paths e anti-churn

- **Paths da W2** (oráculo medido nesta revisão **[medido: redator]**):
  - `.claude/hooks/_lib/spool_writer.py` (1; canônico, NÃO kernel);
  - `.claude/hooks/tests/test_spool_state_amend4.py` (0, novo) e `test_spool_drain_contended_skip.py` (0, teste
    4 intacto);
  - `.claude/scripts/check-audit-real-loss.py` (0, novo; G6 e G7, se o pacote não os separar);
  - `.claude/scripts/ceo-boot.py` (0; no pacote da L2);
  - `.claude/workflows/nightly-hygiene.js` (1) — só se couber no teto (§8.2);
  - o arquivo de emenda (1).
  - **W2.0 à parte:** `audit_log.py` (1, kernel) e `test_two_writer_chain.py` (0).
  - **T2, condicional:** `_lib/filelock.py` (1, kernel).
- **Fora:** `audit_emit.py`, `SessionStart.py`, `audit_hmac.py`, `canonical_json.py`, `audit-verify-chain.py`,
  `_python-hook.sh` e os hooks de guarda (a âncora pelo kernel dispensa tocá-los).
- **Reversibilidade:** ALTA para (a) e (c); (b) e (d) são reversíveis tecnicamente, mas reabrem classes de
  segurança (§8.1).
- **Regra 10×.** Com 10× mais hooks por dia, o estoque de travas sob T1 satura o espaço de PIDs em dias; a
  listagem atinge o custo máximo mais cedo; o prazo continua protegendo a decisão; o gatilho da T2 e o H3 o
  tornam visível; a W2.6 fica mais frequente, o que é por si gatilho da T2. Journals não escalam (cura na
  origem). Prazo, portão STARVED e `flush` não dependem do volume.
- **Anti-churn (ADR-115/ADR-124):** arquivo de emenda próprio, sem ABI nova de spool, sem layout novo, sem ação
  nova de auditoria, sem variável de ambiente nova; slug mantido (R2-7).

---

## §13 Decisões pendentes do Owner (escritas como tais)

1. **Vaga da W2.0 (cura da condição 67).** É hoje o ÚNICO pré-requisito do Owner para o SIGN da W2.
   **Recomendação do CEO:** pacote canônico PRÓPRIO (cerimônia de KERNEL), landado antes do SIGN da W2, como
   1.º pacote na vaga da W2 ou na primeira vaga que abrir antes. **PENDENTE.**
2. **Pré-condição e RECORRÊNCIA da W2.6.** **Recomendação:**
   - trocar «todas as sessões do Claude fechadas» por «todas as sessões DESTE projeto fechadas»;
   - predicado da §5.2: PID vivo nas travas ⇒ pula a família; mtime < 10 min ⇒ recusa a execução; spool ativo
     ou `.draining.*` com PID vivo ⇒ recusa a execução;
   - aceitar que, sob T1, a W2.6 é manutenção RECORRENTE (quando o `/ceo-boot` acusar ≥ 100 mil travas);
     mais de 1× por mês ⇒ gatilho da T2;
   - rodar a 1.ª já.
   A decisão vigente (S359) vale até o Owner decidir. **PENDENTE.**
3. **Para ciência, sem decisão:** a calibração da W2 custa 2 chamadas `claude -p` na vez da W2 (freio Q1); o
   estoque dos adopters não é limpo pela W2 (follow-up recomendado, fora da 1.4.3); reverter o prazo de saída ou
   o portão STARVED exige decisão escrita do Owner.

---

## §14 Perguntas da rodada 2 — respondidas e fechadas

| id | decisão | onde |
|---|---|---|
| R2-1 âncora | `min(import, início do processo no kernel)`, import como recurso declarado; S1 com guard de import tardio; censo AST só como reserva | §4.2; §10 K/L |
| R2-2 W2.4 | CONDICIONAL, fora do pacote base; Check `-k gc` sai | §4.6 |
| R2-3 G6 | ATIVO na W2, com o G7 junto | §8.2 |
| R2-4 sinais do check | spool órfão de qualquer idade como taxa; ≤ 1 linha por execução; o travamento NÃO depende do check (portão STARVED na saída) | §9; §4.3 |
| R2-5 valores | ε = 0,01 com `|D|_min` ≥ 200 e o vermelho medido (F = 0,999); margem 1,0 s e prazo 2,0 s INICIAIS, com a regra «encolhe o prazo, nunca a margem»; N ≥ 1.000 elos com composição; 2.000 `stat`; teto 1.000 só para journals; Linux de vida longa como gatilho da T2 | §4.2; §6.2; §6.3; §4.5 |
| R2-6 sinalizador | à prova de falha: liga ANTES do rename, desliga só com a remoção confirmada; células (b), (g), (h), (i) | §4.1 |
| R2-7 slug | mantido (anti-churn); teste dourado dos construtores de caminho | frontmatter; §4.7 |

---

## §15 Rastreabilidade

### 15.1 Must-fix da rodada 1 (Segurança, condição do VETO da r1 — julgados «atendidos» na r2)

| MF | seção |
|---|---|
| MF-W2-1 cura da condição 67 antes do SIGN | §7; §1 portão 2; §13 decisão 1 |
| MF-W2-2 nenhuma trava em hook; cura na origem | §4.4; §4.5; §4.6; §5 |
| MF-W2-3 prazo de saída + entrega de decisão | §4.2; §6.1 S1; §6.4 |
| MF-W2-4 arquivo próprio, pernas, versões mistas, regex, lista, gatilhos | §3; §4.7; §4.8; §4.9; §8 (`truly_lost` → G6/G7, aceito pelo portador na r2) |
| MF-W2-5 estresse com todos os gravadores | §6.2 |
| MF-W2-6 endurecimento da W2.6 | §5 |

### 15.2 Condições do VETO da rodada 2 (MF-R2-W2-1..4)

| MF | pedido | onde | estado |
|---|---|---|---|
| **MF-R2-W2-1** | trava presa vira sinal em ≤ T (≤ 1 h), sem volume por saída; controle positivo de portador externo; vermelho provando que o G3 sozinho não basta | §4.3 (portão, taxa, texto, controles); §6.1 S4; G8 em §8.2; §2.4 (0 linhas STARVED medidas) | aplicado |
| **MF-R2-W2-2** | âncora = mais cedo entre import e início do processo; fallback; S1 com guard de import tardio | §4.2 (âncora `min`, leitura do kernel medida no macOS, recurso, direção do erro, escopo de hook); §6.1 S1; §6.4 célula 1 | aplicado; Linux não medido (§11, resíduo 1) |
| **MF-R2-W2-3** | G6 (perda real, só-leitura, fora de hook, pós-LAND e nightly, quarentenado ≠ perdido) e G7 (`would-log` datado), com controle positivo, NA W2 | §8.2 (G6 em detalhe; G7 com controle natural medido); §6.1 S5; §9 | aplicado; fiação no nightly condicionada ao teto de paths |
| **MF-R2-W2-4** | reconciliar o plano com este texto | prevalência declarada no cabeçalho; §4.2 (`T_min` = 3 s, teste de deriva); §4.4 (só compactação); §4.6 (W2.4 condicional, `-k gc` fora); §6.2 (M-a..M-d); §5.2 (predicado + recusa por spool/`.draining.*` de PID vivo); §4.1 célula (c) (atexit E sinal) | aplicado neste texto; **o plano é do CEO** |

### 15.3 Lista §3(a) do consenso r2, itens 5–16

| item | onde |
|---|---|
| 5 seletores e módulo renomeado | §6.5 |
| 6 Check de sucesso reescrito | §6.5 |
| 7 Check da W2.0 por node id; vermelho no LEDGER | §7 |
| 8 `flush` e calibração com o harness real | §4.1 passo 1, célula (j); §6.4 célula 7; §10 H |
| 9 estatística e esperado por célula sob T1; gatilho da T2 | §6.4; §4.5 |
| 10 drain oportunista antes da decisão | §4.2; §6.4 célula 5 |
| 11 intervalo do wrapper; vivacidade da perna 3 | §6.4 células 4 e 6 |
| 12 composição da cadeia | §6.2 |
| 13 inode estável, censo dos abridores, células do sinalizador, sinalizador à prova de falha | §6.2; §4.1 |
| 14 T1 operacional (≥ 100 mil, taxa de órfãos, ≤ 1 linha, W2.6 recorrente, G1 com H1 e dias distintos) | §4.5; §5; §9; §8.2 G1 |
| 15 valores R2-5 com as condições | §4.2; §6.3; §14 |
| 16 slug mantido; teste dourado; journals com conteúdo antes do drain | §4.7; §6.2 |

### 15.4 Must-fix da W2 de QA e DevOps (rodada 2)

| crítico | MF | onde |
|---|---|---|
| QA | 1 reconciliação e seletores | §4.4; §4.6; §4.1 (c); §6.5 |
| QA | 2 Check de sucesso | §6.5 |
| QA | 3 Check da W2.0 | §7 |
| QA | 4 calibração contra o harness real | §6.4 célula 7 |
| QA | 5 estatística e esperado por célula | §6.4 |
| QA | 6 atraso antes da decisão | §4.2; §6.4 célula 5 |
| QA | 7 composição da cadeia | §6.2 |
| QA | 8 observabilidade que dispara (G6, órfãos de qualquer idade, taxa de salto, G1 com H1) | §8.2; §9; §6.4 |
| QA | 9 guardas mecânicas e células do sinalizador | §6.2; §4.1 |
| DevOps | 1 alinhar o plano | §15.2 MF-R2-W2-4 |
| DevOps | 2 âncora pelo início do processo; S1 com import tardio | §4.2 |
| DevOps | 3 intervalo do wrapper; vivacidade da perna 3 | §6.4 |
| DevOps | 4 T1 operacional, W2.6 recorrente, gatilho da T2 | §4.5; §5; §9 |

---

## §16 Evidência lida (HEAD `48f03b3a`)

- `.claude/hooks/_lib/spool_writer.py`: `:29` (`_HOOKS_DIR`); `:53`, `:63-66`; `:98-138`; `:265-266`;
  `:407-481`; `:581-582`; `:606-615`; `:731-775`; `:940-973`; `:976-1074` (`:1026`); `:1082-1121`;
  `:1233-1257`; `:1260-1407` (`:1273`, `:1277-1317`, `:1343`, `:1374`, `:1383-1384`, `:1398-1405`);
  `:1892-1900`; `:1938-1942`; `:2248-2301`; `:2309-2326`; `:2329-2459`; `:2467-2565`; `:2573-2682`.
- `.claude/hooks/_lib/filelock.py:128-164`.
- `.claude/hooks/_lib/audit_emit.py`: `:2778-2799`; `:13330-13348`.
- `.claude/hooks/audit_log.py`: `:564-566`; `:667-700`; `:1118-1130`; `:1256-1331` (`:1323-1324`, `:1325-1329`).
- `.claude/hooks/_lib/audit_hmac.py:473-482`.
- `.claude/hooks/check_arbitration_kernel.py`: `:99`, `:137`, `:173`, `:217`.
- `.claude/hooks/check_canonical_edit.py`: `:658`, `:725`, `:1429` (imports tardios); `:1165-1175`;
  `:3127` (oráculo `--is-canonical`, consultado só para leitura).
- `.claude/hooks/check_skill_reference_read.py`: `:155`, `:311`. `.claude/hooks/check_agent_spawn.py:73`.
- `.claude/hooks/_python-hook.sh`: `:304`, `:413`, `:420`.
- `.claude/settings.json:440-441` e `templates/settings/*.json` (timeouts).
- `.claude/scripts/ceo-diagnose.py:364-373`, `:417`; `.claude/scripts/status.py:290`;
  `.claude/scripts/audit-log-retain.py:27-28`; `.claude/scripts/ceo-backup.sh:203-233`.
- `.claude/hooks/tests/test_spool_drain_contended_skip.py:195-231`; `.claude/hooks/tests/test_two_writer_chain.py:1-17`.
- `.claude/adr/ADR-055*.md`; `ADR-186-hook-deadline-policy.md`; `.claude/adr/README.md`.
- `.claude/plans/PLAN-194/debate/round-1/` e `round-2/` (consensos e críticas).
- **Medições do redator** (2026-10-02, só leitura; nada gravado no repositório nem no state dir):
  - `audit-log.errors` vivo: 31.683 linhas; 31.485 timeouts; 3 `would-log=`; 0 `STARVED`; formatos de carimbo
    31.680 + 3;
  - H1 no log corrente: |D| = 1.049, F = 0,999;
  - leitura do início do processo pelo `sysctl` no macOS: retorno 0, 648 bytes, 2,6–3,3 ms;
  - ordem stdout × `atexit`: 1,54 s sem `flush`, 0,03 s com;
  - oráculo `--is-canonical`: `spool_writer.py` 1, `audit_log.py` 1, `nightly-hygiene.js` 1, `ceo-boot.py` 0,
    `test_spool_state_amend4.py` 0, `check-audit-real-loss.py` 0;
  - censo `grep`: 20 módulos de teste com subprocesso + log canônico, 8 com drain ou modo síncrono.

Nenhum conteúdo lido trouxe instrução dirigida a este redator. Não houve injeção a relatar.
