---
id: ADR-055-AMEND-4
title: "ADR-055 §Components — estado da auditoria sem acúmulo: caminho rápido de saída, prazo na drenagem forçada de saída, journal vazio removido na origem e invariante de não-perda reescrito"
status: PROPOSED
draft: true
draft_for: "entrada da rodada 2 do debate do PLAN-194 (só W2). O arquivo canônico `.claude/adr/ADR-055-AMEND-4-spool-state-gc.md` nasce só no pacote de ADR (decisão Q5 do Owner, S361), no leque de ADR em série."
proposed_at: 2026-10-02
proposed_by: "CEO (S361, PLAN-194 W2.1); redação delegada ao arquétipo VP Engineering"
amendment_of: "ADR-055 (Audit-log HMAC chain for tamper detection — 2026-04-18 via PLAN-023)"
amends_section: "§Components §3 — drenagem forçada de SAÍDA e contabilidade de não-perda (refina ADR-055-AMEND-1 §4 Fase 1, §4 «Loss accounting» e §5; refina ADR-055-AMEND-3 §3, §4 e §5)"
veto_floor: "ADR-052 (security-engineer VETO — integridade do log de auditoria; herdado do ADR-055-AMEND-3)"
codex_pair_rail: "required per ADR-107 — pendente; a 1.ª rodada só depois do PROCEED da W2 na rodada 2 do debate"
risk_tier: A
debate_required: true
debate_record: ".claude/plans/PLAN-194/debate/round-1/consensus.md (W2: RUN-ANOTHER-ROUND; VETO de Segurança LEVANTADO; retirada condicionada a MF-W2-1..6)"
sign_precondition: "cura da corrida do `agent_spawn` (condição 67 assinada da v1.4.0-rc.1) landada ANTES do SIGN da W2 — a vaga é DECISÃO PENDENTE 1 do Owner (§13)"
related_plans: [PLAN-194, PLAN-094, PLAN-182]
related_adrs: [ADR-055, ADR-055-AMEND-1, ADR-055-AMEND-2, ADR-055-AMEND-3, ADR-052, ADR-001, ADR-081, ADR-107, ADR-115, ADR-124, ADR-125, ADR-186]
supersedes: []
amends:
  - target: "ADR-055-AMEND-3 frontmatter `amends[0].amended_clause` e §4 (drain FORÇADO)"
    original_clause: "A FORCED drain (force=True — recovery / exit-handler / session-start) blocks up to SPOOL_LOCK_TIMEOUT (a timeout there is anomalous: ok=False + error='canonical_lock_timeout' + breadcrumb, unchanged)."
    amended_clause: "Os únicos chamadores `force=True` VIVOS são as duas rotas de SAÍDA (atexit e sinal); não existe perna de recuperação nem de session-start em produção. A drenagem de saída passa por um auxiliar de saída com (a) caminho rápido — sem conteúdo próprio, não toma a trava canônica nem lista o diretório — e (b) prazo derivado do menor timeout de hook registrado. Estourado o prazo, o spool fica no disco para a perna 3 e isso NÃO é anômalo (`DrainStats.exit_deadline_skip=True`, `ok=True`, nenhum breadcrumb). `drain_now(force=True)` chamado SEM prazo mantém a semântica do AMEND-3 byte a byte."
  - target: "ADR-055-AMEND-3 §3, «No-loss invariant (corrected by debate R-QA1)»"
    original_clause: "No-loss is the UNION of (loser's own size/staleness re-drain) ∪ (loser's atexit/signal force-drain) ∪ (next drainer's dead-PID orphan sweep once `_is_alive_pid` flips False)."
    amended_clause: "Invariante INV-NP por CONJUNTO de `record_id` (cada um no log canônico exatamente uma vez), com três pernas: perna 1 = drain oportunista do próprio dono; perna 2 = drenagem de saída do próprio dono, SÓ para quem tem conteúdo próprio, com prazo; perna 3 = a varredura global da fase 2 de QUALQUER drainer seguinte deste projeto que ganhe a trava canônica (oportunista ou de saída), que recolhe spools de PID morto e todo `.draining.*`. Sem perna de `SessionStart` (§3)."
  - target: "ADR-055-AMEND-1 §4 «Loss accounting» (journal por PID) — o destino do journal compactado, que o ADR não fixava e o código reescreve com 0 byte"
    original_clause: "Per-PID journal `state/audit-pending.<pid>.journal` with buffered appends [...] drain Phase 5 appends `op:\"drained\"`."
    amended_clause: "A compactação pós-drain, sob a trava do PRÓPRIO journal, REMOVE o journal quando o resultado ficaria vazio, em vez de reescrevê-lo com 0 byte. Nenhum hook remove arquivo `*.lock` (§4.4)."
retires_revert_triggers:
  - "ADR-055-AMEND-3 frontmatter `revert_trigger_truly_lost_7d: 1` e §5 «`truly_lost > 0` over 7-day window» — morto por construção (`truly_lost` nunca é incrementado; §2.4)"
  - "ADR-055-AMEND-1 §5 gatilho 3 (`truly_lost > 0` em 7 dias) — idem"
  - "ADR-055-AMEND-1 §5 gatilho 1 e ADR-055-AMEND-3 §5 (taxa de quebra de cadeia > 0,1% em 30 dias) — não avaliável enquanto a condição 67 existir; substituído pelo gatilho G5 (§8.2)"
target_telemetry_window_days: 30
tags: [governance, audit-log, spool-writer, async-drain, amendment, hook-exit-latency, decision-delivery, no-loss-invariant, anti-accumulation, plan-194-w2]
enforcement_commit: "n/a (rascunho; o runtime nasce no pacote da W2)"
---

# ADR-055-AMEND-4 — Estado da auditoria sem acúmulo (W2 do PLAN-194)

**Status:** PROPOSED — rascunho da rodada 2 do debate; não é o arquivo canônico.
**Data:** 2026-10-02 (UTC)
**Enforcement commit:** n/a (rascunho)
**Decision drivers:** decisão de guard perdida por latência de saída; ~3 arquivos acumulados por PID; o
gatilho de reversão do AMEND-3 está morto; a corrida da condição 67 contamina a régua com que a W2 se prova.

> **Legenda de evidência.** **[disco]**: conferido por este redator no HEAD `a9924eb1` (árvore da S361).
> **[consenso]**: conferido pelo sintetizador da rodada 1 (`consensus.md` §0). **[medido: X]**: número
> medido por X, só leitura, não refeito aqui. **[plano]**: o plano afirma. **[inferência]**: dedução
> deste redator, a conferir na abertura do pacote.
>
> **O que este rascunho é.** Entrada da rodada 2, para os mesmos três críticos julgarem só a W2. Ele não
> autoriza nada: o flip para ACCEPTED só acontece no pacote da W2 (§1). Repositório público: classes de
> defeito e invariantes, nenhuma receita de contorno de guarda.

---

## §0 Sumário da decisão

1. **Invariante de não-perda por CONJUNTO** (INV-NP, §3): todo `record_id` aceito pelo spool aparece no log
   canônico exatamente uma vez. Três pernas, nenhuma de `SessionStart`. O gatilho `truly_lost` do AMEND-3
   é declarado **MORTO** e aposentado (§2.4, §8.3).
2. **Caminho rápido de saída** (§4.1): um `stat` do próprio spool e um sinalizador em processo; o flush do
   buffer do journal continua; **zero** `listdir`/`scandir`; sem conteúdo próprio, a saída não toma a trava
   canônica.
3. **Prazo na drenagem forçada de saída** (§4.2), derivado do menor timeout de hook registrado. Estourado o
   prazo, o spool fica no disco para a perna 3 — e isso deixa de ser «anômalo». Controle de **entrega da
   decisão BLOCK** sob contenção, vermelho antes e verde depois.
4. **Journal vazio removido NA ORIGEM**, pela compactação, sob a trava do próprio journal (§4.3).
5. **Nenhum hook apaga `*.lock`** (§4.4): opção T1 por padrão; T2 (re-checagem de inode no `filelock.py`,
   kernel) só em pacote próprio e condicional; T3 (relocação) fora.
6. **Versões mistas** (§4.6): seguras porque nenhum caminho de trava muda; LAND com as sessões do projeto
   fechadas; efeitos da convivência declarados.
7. **Regex ancoradas** com `fullmatch` e PID só de dígitos ASCII (§4.7); **lista do que nunca se apaga**
   (§4.8).
8. **W2.6 endurecida** (§5): resolvedor `runtime_paths`, `unlink` relativo ao descritor do diretório, reexame
   imediato, simulação por padrão, manifesto de hash dos journals com conteúdo.
9. **Limiar** (§6): os critérios de SEGURANÇA barram; o FLUXO com denominador é o critério primário de
   higiene; o teto de 1.000 é secundário e, sob T1, vale só para journals.
10. **Gatilhos de reversão em instrumentos LIGADOS**, cada um com controle positivo (§8).
11. **Observabilidade pelo resultado** no `/ceo-boot`, sem tocar o `audit_emit.py` (§9).
12. **Pré-condição do SIGN**: a cura da condição 67. A vaga é decisão pendente do Owner (§7, §13).

---

## §1 Status e portões de aceitação

PROPOSED. O flip para ACCEPTED acontece SÓ no commit de cerimônia do pacote da W2, e exige:

1. PROCEED da W2 na rodada 2 do debate, com o VETO de Segurança (ADR-052) retirado: MF-W2-1 a MF-W2-6
   endereçados aqui e no plano (tabela em §15.1).
2. A cura da condição 67 landada ANTES do SIGN da W2 (§7), ou dentro do pacote, conforme a decisão
   pendente 1 (§13).
3. A W0.5 pré-registrada no LEDGER e rodada ANTES do patch (§6.4).
4. Rail do Codex (ADR-107) até rodada limpa, com a regra de parada pré-registrada (≤ 3 rodadas; NO-GO só por
   P0 ou afirmação FALSA).
5. Assinatura GPG do Owner. O apêndice `## Amended-by` do ADR-055 landa no MESMO commit; o arquivo de
   emenda entra no leque de ADR em série (índice e documentos de contagem re-derivados no LAND).

---

## §2 Contexto

### 2.1 O sintoma e o risco real

- **Sintoma.** O state dir deste projeto tinha ~226,8 mil entradas às 23:55Z–00:00Z de 2026-10-01/02
  **[medido: críticos da rodada 1]**. O `audit-log.errors` tinha 30.258 linhas às 00:25Z, 30.068 delas
  `drain canonical lock timeout`, num ritmo de ~1.100 por hora **[consenso]**.
- **Risco real.** O risco de SEGURANÇA não é o disco: o crescimento é limitado pelo espaço de PIDs. É a
  **decisão de guard perdida**: um guard que já decidiu BLOCK e passa do timeout na SAÍDA é morto pelo
  harness, e a ação passa sem decisão (lane `CC285-05` **[plano]**). Qualquer coisa que atrase a saída
  (diretório grande, contenção, disco lento) converte decisão em allow. A contagem de arquivos é higiene.
- **Premissa que muda.** O AMEND-3 tratava o timeout do drain forçado como «genuinamente anômalo». Com a
  saída sujeita a prazo, estourar o prazo passa a ser um desvio ESPERADO, coberto pela perna 3. Mudança
  semântica ⇒ arquivo de emenda próprio (Q5; C16 do consenso).

### 2.2 De onde vêm os ~3 arquivos por PID

Cada processo que emite cria quatro arquivos: o spool `audit-spool.<pid>.jsonl`, a trava dele
`audit-spool.<pid>.jsonl.lock` (`spool_writer.py:465-467`, aberta em `:1001-1002`), o journal
`audit-pending.<pid>.journal` e a trava dele `audit-pending.<pid>.journal.lock` (`:450-472`; o flush abre
o journal com `O_CREAT` sob a trava, `:958-961`) **[disco]**. O drain renomeia o spool para `.draining.*` e
o apaga quando ele é todo consumido. A compactação reescreve o journal sem os triplos drenados e termina com
0 byte, sem nunca removê-lo (`:2276-2297`) **[disco]**. Sobram três: as duas travas e o journal vazio.
Censo: 75.587 travas de spool, 75.609 travas de journal e 75.609 journals, 75.396 deles com 0 byte, e
~214 journals com conteúdo (213 a 215, conforme a leitura) **[medido: QA, 23:55Z; consenso; plano]**.

### 2.3 Por que a saída é lenta

- Todo processo que importa o `audit_emit` registra o drain de saída no próprio import
  (`audit_emit.py:13336-13348` chama `install_exit_handlers`) **[disco]**. Por isso até um hook que nunca
  emitiu toma a trava canônica na saída (`_atexit_drain` → `drain_now(force=True)`,
  `spool_writer.py:2573-2587`), com espera de até 2,5 s (`SPOOL_LOCK_TIMEOUT`, `:66`).
- Dentro da trava, a fase 2 lista e ordena o diretório inteiro (`os.listdir`, `:1273`), ~0,24–0,30 s com
  ~219 mil nomes (lane `H-02` **[plano]**).
- As esperas se somam: o flush do journal (até 2,5 s, `:958`), a trava canônica (até 2,5 s, `:2366-2368`),
  a compactação de cada PID drenado (até 2,5 s, `:2276`) e o trabalho do próprio hook.

### 2.4 Premissas do AMEND-1 e do AMEND-3 que o disco refuta

| premissa | onde estava | o que o disco mostra | efeito neste rascunho |
|---|---|---|---|
| «`truly_lost > 0` em 7 dias» é gatilho de reversão | AMEND-1 §5 (gatilho 3); AMEND-3 frontmatter e §5 | `truly_lost` só aparece no valor padrão (`spool_writer.py:136`) e na leitura (`:2562`); nenhum caminho o incrementa **[disco]** | gatilho MORTO por construção; aposentado (§8.3) |
| a reconciliação de início de sessão roda | AMEND-1 «Loss accounting» | `reconcile_journal_at_session_start` (`:2467`) não tem chamador em produção: só a definição, um teste e cópias em sombra **[disco; consenso]**; 0 eventos `audit_flush_dropped_count` em 16 logs **[medido: DevOps]** | declarada fora de produção; ligá-la fica FORA da W2 (abriria ~76 mil journals sob o timeout de 5 s do `SessionStart`) |
| existe drain forçado de «recovery» e de «session-start» | AMEND-3 frontmatter (`:19`) | os únicos `drain_now(force=True)` vivos são o atexit (`:2581`) e o sinal (`:2610`); o de `:2539` está dentro da reconciliação morta; `SessionStart.py` não tem drain nem spool **[disco; consenso]** | não existe perna de `SessionStart` |
| «enquanto o PID vive, nenhum drainer toca os arquivos dele» | premissa de uma crítica da rodada 1 | a fase 2 recupera `.draining.*` «owned by a dead PID (or even a live one)» (`:1277-1317`), e a compactação do PID drenado trava o journal DELE (`:2276`) **[disco]** | só a remoção sob a trava do próprio journal é segura (§4.3); nenhuma trava se apaga (§4.4) |
| o `FileLock` garante exclusão mesmo se o caminho for apagado | implícita em todo GC de trava | `acquire` abre o caminho com `O_CREAT` e faz `flock` sem comparar inode (`filelock.py:144`, `:149`) **[disco]** | nenhum hook apaga `*.lock` (§4.4) |
| a taxa de quebra de cadeia mede a saúde do drain | AMEND-1 §5 (gatilho 1); AMEND-3 §5 | `audit_log.py` lê o elo anterior e calcula o HMAC FORA da trava (`:1262-1278`; trava em `:1283`), contra o contrato «MUST be called WITH the audit-log FileLock held» (`_lib/audit_hmac.py:482`) **[disco]**: condição 67 assinada (`CHANGELOG.md`, seção 1.4.0; `test_two_writer_chain.py:13-16`) | gatilho inavaliável até a cura (§7); substituído pelo G5 (§8.2) |

---

## §3 Invariante de não-perda (reescrito)

### 3.1 Enunciado — INV-NP

Seja **R** o conjunto dos `record_id` cujo `spool_append` terminou com sucesso (`last_append_succeeded()`
verdadeiro: linha escrita e com `fsync` no spool do PID). O `record_id` é carimbado em cada linha do spool
(`spool_writer.py:1026`) e sobrevive no log canônico: a fase 4 só tira os campos `_drain_*`, `hmac` e
`hmac_error` (`:1896-1900`) **[disco]**. Para todo r ∈ R:

- **(a) Segurança — nunca some.** Nenhum código apaga um arquivo que contenha r antes de r estar no log
  canônico (na família de rotação). A fase 5 só apaga `.draining.*` com TODAS as linhas consumidas; o
  restante vira um `.draining.*` novo (divisão atômica, AMEND-1 §4 Fase 5).
- **(b) Unicidade — nunca duplica.** r aparece no máximo UMA vez no log canônico (guarda de idempotência
  `_drain_sha256` na janela `K_TAIL_WINDOW`, mais a rejeição de 4-tupla duplicada).
- **(c) Vivacidade condicionada.** Se existir um drainer futuro deste projeto que ganhe a trava canônica, r
  chega ao log canônico exatamente uma vez. A exceção é r em quarentena (`.malformed.*`, `.quarantined.*`,
  `.test-origin.*`, `.corrupt-header.*`): fica no disco, contado, e nunca é apagado.

**Na prova (W2.5):** depois de um drain final até ponto fixo na árvore descartável, todo r ∈ R aparece no log
exatamente uma vez. A exceção são as células de quarentena plantadas, em que r aparece zero vezes e o arquivo
está no disco. «Contagem igual antes e depois» NÃO serve: esconde perda somada a duplicata.

**O journal NÃO entra no INV-NP.** Ele é contabilidade forense de melhor esforço, que não sustenta a
correção (AMEND-1 «Loss accounting»). Remover um journal vazio não toca nenhum r.

### 3.2 As três pernas

| perna | quem | quando | o que recolhe | código |
|---|---|---|---|---|
| **1** | o próprio dono, durante a vida | a emissão vê `should_drain()` verdadeiro (spool próprio com ≥ 100 linhas, ou idade > 100 ms) e ganha a trava canônica SEM bloquear (AMEND-3) | o próprio spool e, como a fase 2 é global, os órfãos | `audit_emit.py:2790-2791`; `spool_writer.py:1082-1119`, `:2366-2371` **[disco]** |
| **2** | o próprio dono, na saída | SÓ se houver conteúdo próprio: spool próprio não vazio (um `stat`) OU o sinalizador em processo ligado (§4.1). Com prazo (§4.2) | o próprio spool e os órfãos | auxiliar de saída chamado por `_atexit_drain` (`:2573`) e `_signal_drain_handler` (`:2590`) |
| **3** | QUALQUER drainer seguinte deste projeto que ganhe a trava canônica, seja a perna 1 ou a perna 2 de outro processo | a próxima drenagem de outro emissor | spools de PID morto (`:1343`) e TODO `.draining.*`, inclusive de PID vivo (`:1277-1317`) | `_phase2_sweep_and_rename` dentro do `with FileLock` de `drain_now` (`:2366-2371`) **[disco; consenso]** |

**Não existe perna de `SessionStart`** (§2.4). A perna 3 depende de haver um emissor seguinte neste projeto;
o «próximo `SessionStart`» que uma crítica da rodada 1 citou não drena nada.

### 3.3 Quem cumpre a perna 2 quando o caminho rápido a pula (MF-W2-4)

Ninguém precisa cumpri-la. O caminho rápido só é tomado quando a perna 2 seria VÁCUA: spool próprio ausente
ou vazio, sinalizador desligado (nenhum `.draining` próprio pendente, nenhum drain próprio falho). Os órfãos
dos OUTROS PIDs nunca foram responsabilidade da perna 2 de quem não tem conteúdo; eles ficam com a perna 3.
Quando é o PRAZO que corta a perna 2 de quem tem conteúdo, o spool fica intacto no disco. Depois que o
processo sai, o PID está morto, e a perna 3 recolhe o spool (`:1343`).

### 3.4 Vivacidade, reuso de PID e limites

- **Reuso de PID por processo alheio.** `_is_alive_pid` diz «vivo» (`:1233-1245`), e a perna 3 pula o spool
  órfão até o processo alheio morrer: ATRASO, não perda.
- **Reuso de PID por outro hook deste projeto.** O processo novo adota o cabeçalho do spool existente e
  recupera o ordinal (`_ensure_spool_header`, `:746-775`) **[disco]**, então drena o spool nas próprias pernas
  1 e 2.
- **Ninguém mais emite neste projeto.** Os órfãos ficam no disco, duráveis e não perdidos. O check do
  `/ceo-boot` os torna visíveis (§9).
- **Lote limitado.** Cada drain processa ≤ `K_MAX` = 100 entradas (`:53`); o restante fica num `.draining.*`
  para a próxima drenagem.

### 3.5 O escritor direto `agent_spawn`

O `audit_log.append_entry` escreve no log canônico sem spool e sem `record_id` (`audit_log.py:667-700`,
`:1280-1296`) **[disco]**. No estresse da W2.5, cada linha `agent_spawn` é identificada por um `desc_hash`
único que o teste controla, e o INV-NP vale também para ela: cada gravação bem-sucedida aparece exatamente
uma vez. Há um caminho de PERDA pré-existente, fora do spool: com a trava canônica ocupada por mais de 2,5 s,
o `append_entry` grava só um breadcrumb `lock timeout (stale?) would-log=…` truncado em 200 caracteres
(`audit_log.py:1325-1329`) **[disco]**. A W2 REDUZ esse caminho, porque as saídas sem conteúdo deixam de
tomar a trava canônica. Ela não o elimina, e isso fica declarado (§11). No estresse, qualquer breadcrumb
`would-log`, `spool append failed` ou `journal flush failed` conta como reprovação.

---

## §4 Decisão

### 4.1 Caminho rápido de saída (W2.2)

Um **auxiliar de saída** único, chamado por `_atexit_drain` e por `_signal_drain_handler`, e NUNCA por
`drain_now(force=True)`:

1. **Flush do buffer do journal do próprio PID**, sempre que o buffer não estiver vazio. A trava do journal
   espera no máximo o orçamento restante (§4.2); com o prazo já vencido, faz uma única tentativa sem
   bloquear (a semântica `timeout=0` do AMEND-3). Perder envelopes de journal não fere o INV-NP (§3.1).
2. **Decisão do caminho rápido**, com UM `stat` do próprio spool (`_spool_path(os.getpid())`) e o
   **sinalizador em processo** `_OWN_DRAIN_PENDING`. O sinalizador LIGA quando a fase 2 renomeia o spool do
   próprio PID para `.draining.*` (`:1398-1405`), ou quando um `drain_now` deste processo termina com
   `ok=False`. Ele DESLIGA só quando a fase 5 consome por inteiro e remove o `.draining` próprio; uma divisão
   com restante o mantém ligado.
3. **Spool próprio ausente ou com 0 byte, e sinalizador desligado ⇒ sai.** Sem trava canônica, sem
   `listdir`/`scandir`, sem `glob`, sem `iterdir`.
4. **Caso contrário** ⇒ drenagem com prazo (§4.2).

O caminho rápido mora no auxiliar de saída. Mover a lógica para dentro de `drain_now(force=True)` reprova um
teste (célula (c) do QA). O teste 4 de `test_spool_drain_contended_skip.py` (`:220-231`: `drain_now(force=True)`
direto, com spool próprio sob trava externa ⇒ `ok=False`, `error="canonical_lock_timeout"` e breadcrumb) fica
**intacto** **[disco]**.

**Células obrigatórias (`-k fast_path`):**

- (a) sem spool próprio, com envelopes no buffer do journal ⇒ o flush roda;
- (b) `.draining` próprio deixado por exceção no meio do drain ⇒ o sinalizador força a drenagem;
- (c) a lógica fica no auxiliar de saída, não em `drain_now(force=True)`;
- (d) zero chamadas a `os.listdir`, `os.scandir`, `glob` e `Path.iterdir` no caminho rápido, contadas por
  envoltório e nunca por tempo;
- (e) o teste 4 intacto;
- (f) um órfão de PID morto é recuperado pelo drain OPORTUNISTA (`force=False`) do próximo emissor (o teste 3
  atual usa `force=True`, `:195-217`).

### 4.2 Prazo na drenagem forçada de saída e entrega da decisão BLOCK (W2.2-bis; MF-W2-3)

**Âncora.** `_PROCESS_ANCHOR = time.monotonic()`, gravada no import do `spool_writer` (o `audit_emit` o
importa no próprio import). A margem absorve o intervalo entre o início do interpretador e a âncora. Ver o
resíduo da importação tardia em §11 e a pergunta R2-1 em §14.

**Prazo.** `EXIT_DEADLINE_S = T_min − EXIT_MARGIN_S`, constante canônica.

- `T_min` é o MENOR `timeout` entre as registrações de hook do `.claude/settings.json` e dos perfis
  shipados em `templates/settings/`. Hoje é 3 s: a registração PostToolUse de `check_skill_reference_read.py`
  no settings deste repositório. Nos perfis shipados, o mínimo é 5 s **[disco]**.
- Proposta inicial: `EXIT_MARGIN_S` = 1,0 s ⇒ prazo de 2,0 s contados da âncora. Os dois valores são
  re-medidos na W0.5 (p95 do encerramento do interpretador depois do atexit e intervalo até a âncora) e
  pré-registrados ANTES de rodar.
- Um teste recalcula `T_min` dos arquivos e reprova se `EXIT_DEADLINE_S + EXIT_MARGIN_S > T_min`. Uma
  registração nova com timeout menor deixa o teste VERMELHO no mesmo patch.
- Usa-se o mínimo global, e não o timeout de cada hook: o processo não sabe por qual registração foi
  chamado, e mapear por nome de script é frágil. O custo é só deixar mais spools para a perna 3, nunca perda.

**Aplicação.** `restante = EXIT_DEADLINE_S − (monotonic() − _PROCESS_ANCHOR)`.

1. `restante ≤ 0` ⇒ nenhuma tentativa na trava canônica. O spool fica no disco: `exit_deadline_skip=True`.
2. A trava canônica espera `min(SPOOL_LOCK_TIMEOUT, restante)`. `drain_now` ganha um parâmetro nomeado
   opcional com o instante-limite absoluto. Sem ele, o comportamento é o de hoje.
3. Depois de obter a trava, o prazo é conferido de novo, IMEDIATAMENTE antes da fase 2. Se tiver vencido, a
   trava é solta sem listar.
4. Dentro da seção crítica, as esperas por trava por PID (o rename da fase 2, `:1374`; a compactação,
   `:2276`) usam `min(timeout atual, restante)`. Estourar uma delas segue os desvios que JÁ existem (pular o
   PID neste ciclo; pular a compactação), nunca um caminho novo de erro.
5. **Estouro no caminho de saída** ⇒ `DrainStats.exit_deadline_skip=True`, `ok=True`, **sem** o breadcrumb
   `drain canonical lock timeout`. O campo existe só em processo e nunca é serializado (mesmo regime do
   `contended_skip` do AMEND-3).
6. **Parte não preemptível:** uma listagem, ≤ `K_MAX` entradas, um append com `fsync` e as compactações
   dos PIDs drenados. Ela é limitada pelo tamanho do diretório e por `K_MAX`, e a W0.5 a mede (§6.4).

**Por que não é «anômalo».** O trabalho cortado é durabilidade POSTERIOR à decisão, com a perna 3 como
garantia. Não se corta verificação de segurança, por isso não há conflito com o ADR-186: lá o prazo
fail-CLOSED vale para a verificação INCOMPLETA do matcher canônico. Aqui o prazo protege a ENTREGA de uma
decisão já tomada. É a cura da CLASSE «trabalho longo dentro de guard vira allow»: vale para qualquer causa
de lentidão, inclusive uma induzida.

**Controle de ENTREGA DE DECISÃO (o critério que barra, §6.1):**

- **Medição (W0.5, fora do CI).** Um guard sintético que decide BLOCK, com ≥ 9 saídas concorrentes, o
  diretório com ~220 mil entradas e um portador externo da trava canônica. O driver reproduz a regra do
  harness: processo que passa do timeout registrado é morto, e a decisão é descartada. **Vermelho no HEAD**
  (pré-registrado): ≥ 1 processo com a decisão BLOCK descartada. **Verde depois da cura:** 0 em N ≥ 30
  execuções da célula de carga máxima. Se o vermelho não reproduzir, o LEDGER registra «prova só
  estrutural», declarada no material assinado.
- **Prova estrutural (CI, `-k deadline`).** Relógio falso injetado e espião no `FileLock`; nenhuma
  asserção de tempo absoluto. Afirma que:
  - `restante ≤ 0` ⇒ zero aquisições da trava canônica e zero listagens;
  - o timeout passado à trava = `min(SPOOL_LOCK_TIMEOUT, restante)`;
  - o estouro ⇒ `exit_deadline_skip`, com o spool próprio intacto no disco (nem renomeado nem apagado) e
    sem o breadcrumb `drain canonical lock timeout`;
  - o drain oportunista seguinte de OUTRO processo recolhe esse spool (perna 3);
  - o teste da constante contra os settings (acima).

### 4.3 Journal vazio removido na origem, sob a própria trava (W2.3)

Em `_journal_compact_drained` (`:2248-2301`), sob a trava do PRÓPRIO journal (`_journal_flock_path(pid)`):

1. reexaminar a existência do journal SOB a trava; ausente ⇒ retorno silencioso, sem breadcrumb. Hoje o
   `exists()` vem antes da trava (`:2265`);
2. ler e filtrar como hoje (`:2277-2291`; linhas que não decodificam ficam);
3. **resultado vazio ⇒ `os.unlink(journal)` sob a trava**, sem escrever `.compact.tmp`. `FileNotFoundError`
   é retorno silencioso;
4. resultado não vazio ⇒ o caminho atual (`.compact.tmp`, `fsync`, `os.replace`), sem mudança.

**Por que é seguro.** Os únicos abridores do ARQUIVO do journal são o flush (`:950-966`, `O_CREAT|O_APPEND`
pelo caminho, sob a mesma trava), a compactação (sob a mesma trava) e a reconciliação morta. Nenhum outro
módulo abre `audit-pending.*` **[disco: censo por `grep`]**. Um flush posterior do dono vivo reabre pelo
caminho e cria o arquivo de novo, sem envelope perdido. A TRAVA do journal nunca é apagada, então a exclusão
mútua entre flush e compactação fica intacta.

**Por que só a compactação, e não também o dono na saída.** A compactação é o ÚNICO produtor de journal com
0 byte: o flush só cria o arquivo com conteúdo não vazio (`:947-949`, `:959-963`) **[disco]**. Remover na
compactação cobre todos os casos, inclusive o journal de PID morto drenado por outro processo. A remoção pelo
dono na saída, que o consenso admitia como alternativa, fica redundante e não entra. Ela fica declarada como
alternativa caso a rodada 2 mostre um produtor que este rascunho não viu. Um resíduo raro: `O_CREAT` seguido
de falha no `write` (disco cheio) deixa um journal com 0 byte. A W2.6 cuida dele (§11).

**Controle de intercalação (`-k origin`), por barreira determinística, sem `sleep`** (molde
`test_spool_drain_contended_skip.py`):

- o dono abre o journal para flush e pára na barreira; o compactador decide remover; libera;
- **mutante 1**, remoção FORA da trava: o envelope do dono vai para um inode desligado ⇒ VERMELHO;
- **mutante 2**, remoção com restante não vazio: o manifesto de hash do conteúdo forense acusa ⇒ VERMELHO;
- a cura ⇒ VERDE: o envelope está no journal recriado, e nenhum journal com conteúdo foi removido.

### 4.4 Regra de travas: nenhum hook apaga `*.lock` (MF-W2-2)

- **Nenhum hook faz `unlink` de caminho `*.lock`**, de nenhum módulo e por nenhum motivo. A razão está em §2.4:
  sem re-checagem de inode, apagar o caminho de uma trava cria dois «donos» para o mesmo recurso
  (R-SEC5/R-QA1).
- **T1 (padrão).** As travas ficam. O estoque é limpo pela W2.6 (sem adquirente vivo, §5). A contagem é
  reportada à parte (§6.3, §9), sem limiar de reprovação. O teto teórico é ~2 × o espaço de PIDs.
- **T2 (condicional).** Re-checagem de inode no `_lib/filelock.py` (kernel, `check_arbitration_kernel.py:173`):
  depois do `flock`, `fstat(fd).st_ino == stat(path).st_ino`, senão nova tentativa. Só entra em pacote de
  kernel PRÓPRIO, e só se a W0.5 DEPOIS da cura mostrar que a listagem das travas, sozinha, ainda estoura o
  prazo da drenagem de saída. Mesmo com a T2, a remoção de travas em hook volta a debate com o portador do
  VETO.
- **T3 (relocação).** FORA: duas travas para o mesmo recurso durante a convivência de versões (C14).
- **«O dono apaga as próprias travas na saída».** NÃO entra neste rascunho. Só volta com as quatro coisas da
  §2(b) do consenso: o censo mecânico dos 4 abridores de caminho de trava por PID (`:958`, `:1002`, `:1374`,
  `:2276`) como guarda; o sinalizador em processo do próprio `.draining`; o controle de intercalação
  (vermelho com a remoção ingênua, verde com a cura); e novo julgamento do portador do VETO.

### 4.5 GC dentro do hook: fora do pacote base (W2.4 condicional)

Com §4.3, deixa de existir produtor de journal vazio, e com §4.4 nenhuma trava se apaga em hook. **O pacote
base da W2 não leva GC no hook.** O estoque é da W2.6 (§5), e o resíduo é medido pelo fluxo (§6.3). Isso
diverge do texto atual da W2.4 do plano (pergunta R2-2). Se o fluxo, medido depois do LAND, ficar acima do
limiar, o GC de journal de PID morto volta como pacote próprio, com as condições já fixadas pelo consenso:

- de carona na listagem da fase 2, DEPOIS de soltar a trava canônica;
- teto de ≤ 200 arquivos e ≤ 50 ms por execução, a confirmar na W0.5;
- só o padrão de journal (§4.7), só 0 byte, PID morto;
- reexame sob a trava do journal;
- nenhum `*.lock`;
- a lista de §4.8;
- a tabela de predicado de §5.2, com o porquê de cada diferença.

### 4.6 Regra de versões mistas (MF-W2-4)

- **Invariante estrutural:** nenhum caminho de trava e nenhum caminho de journal mudam. A emenda não cria
  layout novo. Por isso o código velho e o novo serializam pelas MESMAS travas, e a leitura dupla de layout
  pedida para a relocação não se aplica (a relocação saiu).
- **Regra para emendas futuras:** mudar o caminho de uma trava ou de um journal exige transição explícita,
  com dupla trava ou janela sem adquirentes. É a classe da antiga W2.3, registrada aqui para não reabrir.
- **LAND** com as sessões DESTE projeto fechadas, declarado no material assinado. Cada hook é um processo
  novo que carrega o código do disco, então a convivência dura só a vida dos processos em voo no instante
  do LAND **[inferência]**.
- **Efeitos declarados da convivência** (LAND com sessão aberta, ou adopter via `upgrade.sh` com sessão
  aberta):
  - um compactador velho que encontre o journal removido por um novo grava o breadcrumb
    `journal compact failed: FileNotFoundError`. É ruído transitório, não perda: os registros já estão no
    log;
  - processos velhos seguem sem caminho rápido e sem prazo até sair;
  - um compactador velho ainda reescreve journal com 0 byte, e o novo o remove na próxima compactação
    daquele PID;
  - nenhuma combinação cria dois donos para uma trava.
- **Adopters:** o estoque dos adopters não é limpo pela W2, porque a W2.6 é operação do Owner, fora do
  repositório. A decisão BLOCK deles fica protegida pelo prazo. A limpeza do estoque do adopter é follow-up
  (§13, para ciência).

### 4.7 Nomes: expressões regulares ancoradas

Usadas pela W2.6, pelo check do `/ceo-boot` e pelo critério de sucesso (o MESMO texto nos três):

```
RE_SPOOL_LOCK   = r"audit-spool\.([1-9][0-9]{0,9})\.jsonl\.lock"
RE_JOURNAL      = r"audit-pending\.([1-9][0-9]{0,9})\.journal"
RE_JOURNAL_LOCK = r"audit-pending\.([1-9][0-9]{0,9})\.journal\.lock"
RE_DRAINING     = r"audit-spool\.([1-9][0-9]{0,9})\.draining\.([0-9a-f]{8})"
RE_ACTIVE_SPOOL = r"audit-spool\.([1-9][0-9]{0,9})\.jsonl"
```

- **Só com `re.fullmatch` e a flag `re.ASCII`.** Nunca `match`, `search` nem `$`, porque o `$` do Python
  aceita um `\n` final, e nome de arquivo pode conter `\n`.
- PID só de dígitos ASCII, sem zero à esquerda, de 1 a 10 dígitos.
- **Proibido reusar `_parse_spool_pid`** (`:1248-1257`) para decidir remoção: ele usa `int()`, que aceita `_`,
  espaços, `+` e dígitos Unicode **[disco + semântica do `int()` da stdlib]**.
- O journal agregado (`audit-pending.journal`) e a trava de agregação
  (`audit-pending.journal.aggregation.lock`) NÃO casam (`:455-462`).
- A compactação do hook (§4.3) não usa regex: o caminho é construído a partir do próprio PID.

### 4.8 O que nunca se apaga

Nem em hook, nem na W2.6:

- `.draining.*`, `.malformed.*`, `.quarantined.*`, `.test-origin.*`, `.corrupt-header.*` (`:581-582`),
  `.tmp.*` e `*.compact.tmp`;
- spool ativo `audit-spool.<pid>.jsonl`, de qualquer tamanho;
- journal com conteúdo (> 0 byte) e TODA a família dele (as duas travas do mesmo PID);
- o journal agregado e a trava de agregação dele;
- a família do log: `audit-log.jsonl`, `audit-log.lock`, `audit-log.errors`, a chave, o sal, os sidecars
  (`last-hmac`, `chain-length`, `rotation-manifest`) e os arquivos rotacionados;
- travas e temporários de outros módulos no mesmo diretório (`ceo-overhead-window*.json.lock`,
  `subagent-lifecycle.json.lock`, `output-scan-dedup.lock`, `ceo-boot-tasks-emitted.json.lock`,
  `statusline-snapshot.json.tmp.N`) **[medido: QA]**;
- tudo que não for arquivo comum (symlink, diretório) ou que tenha `st_nlink > 1`;
- qualquer coisa fora do state dir resolvido;
- **em hook:** qualquer `*.lock`, sem exceção (§4.4).

### 4.9 O que NÃO muda

- As fases 2 a 5, a ordem da cadeia HMAC, a reconstrução do `prev_hmac` pela cauda e a guarda `_drain_sha256`.
- `_lib/audit_hmac.py`, `_lib/canonical_json.py` e `audit-verify-chain.py`.
- O caminho oportunista do AMEND-3: `timeout=0`, `contended_skip` e o breadcrumb `STARVED` com gate.
- `drain_now(force=True)` sem prazo: o teste 4.
- O kill-switch `CEO_AUDIT_SYNC_MODE=1`.
- Nenhuma ação nova em `_KNOWN_ACTIONS` e nenhum toque no `audit_emit.py` (§9).

---

## §5 W2.6 — limpeza única do estoque, endurecida (MF-W2-6)

O script fica fora do repositório, é rodado pelo Owner e é confinado ao state dir.

### 5.1 Resolução e confinamento

- O state dir vem do resolvedor `_lib/runtime_paths.py` (`--state-dir`) + `/state`, NUNCA de slug derivado à
  mão (ADR-001, marcador M4). Com `CEO_AUDIT_LOG_DIR` ou `CEO_AUDIT_LOG_PATH` definidos, o script recusa:
  com eles, o state dir dos hooks diverge do resolvedor (`spool_writer.py:265-266`, `:407-412`).
- O diretório é aberto com `O_RDONLY | O_DIRECTORY | O_NOFOLLOW`. Recusa se for symlink, se o dono não for
  o UID corrente ou se o modo não for 0700.
- Cada remoção é `os.unlink(nome, dir_fd=dfd)`, relativo ao descritor do diretório, sem seguir link.
- **Reexame imediatamente antes de cada `unlink`:** `os.stat(nome, dir_fd=dfd, follow_symlinks=False)`, com
  `S_ISREG`, `st_size == 0`, `st_nlink == 1`, o mesmo `(st_dev, st_ino)` da listagem e a família ainda sem
  conteúdo.
- **Simulação por padrão;** só remove com `--apply`.
- **Resíduo declarado:** entre o reexame e o `unlink` há uma janela, porque não existe «unlink se o inode for
  X». Com as sessões do projeto fechadas, não há adquirente vivo para explorá-la.

### 5.2 Predicado pré-registrado (uma ação por célula; QA MF-6)

| célula | ação |
|---|---|
| nome casa um dos 3 padrões (§4.7); arquivo comum; 0 byte; `st_nlink == 1`; PID morto; família sem conteúdo (journal ausente ou com 0 byte, sem spool ativo com conteúdo, sem `.draining.*` do PID); mtime ≥ 10 min | **APAGA** (a simulação conta; `--apply` apaga) |
| mesma célula, com PID vivo (inclusive PID reusado por processo alheio) | **MANTÉM** a família inteira; contada como «pulada: PID vivo» |
| qualquer arquivo da família com mtime < 10 min | **RECUSA a execução inteira** (sinal de sessão viva deste projeto) — ver a decisão pendente 2 |
| journal com conteúdo | **MANTÉM** a família inteira; o journal entra no manifesto de hash |
| symlink, hardlink (`st_nlink > 1`), diretório ou outro tipo | **MANTÉM** + aviso |
| quase-acertos: travas de outros módulos, `statusline-snapshot.json.tmp.N`, `audit-pending.journal`, a trava de agregação, `*.compact.tmp`, `audit-pending.0123.journal` (zero à esquerda), `audit-pending.12a.journal`, PID com dígitos não ASCII, `audit-pending.1_0.journal`, nome com `\n` final | **MANTÉM** (não casa) |
| spool ativo, `.draining.*` e todo sufixo de §4.8 | **MANTÉM** |
| state dir symlink, de outro dono ou com modo ≠ 0700 | **RECUSA a execução** |

Diferença em relação ao hook: o hook só remove o journal do PID que está compactando, sob a trava dele e
sem regex (§4.3). A W2.6 é a ÚNICA que remove travas, e pode fazê-lo porque roda sem adquirente vivo.

### 5.3 Execução e prova

1. **Simulação.** Contagem POR CÉLULA da §5.2, gravada no LEDGER com data e substrato (versão do CC, o
   `python3` dos hooks e o sha do script).
2. **Manifesto de hash** dos journals com conteúdo (~214), antes e depois. Qualquer diferença reprova.
3. **Contagem antes e depois** pelo MESMO método do critério (§6.3). Um teste afirma: contagem registrada =
   arquivos de fato removidos.

---

## §6 Critérios de sucesso

### 6.1 Critérios que BARRAM o SIGN (segurança; domínio do VETO)

- **S1 — entrega de decisão (MF-W2-3).** O controle de §4.2 passa de VERMELHO (W0.5 no HEAD) a VERDE (W0.5
  depois da cura), e a prova estrutural `-k deadline` fica verde.
- **S2 — INV-NP por conjunto.** Verde no estresse da W2.5 (§6.2), com cada mutante reprovando.
- **S3 — cadeia.** `verify_chain()` íntegro sobre ≥ N elos sob estresse com escritores `agent_spawn`
  misturados, DEPOIS da cura da condição 67 (§7). N é pré-registrado; proposta: ≥ 1.000. Cadeia vazia ou
  curta é verde por vácuo.

`truly_lost` NÃO é critério: está morto (§2.4).

### 6.2 Estresse W2.5 (`-k invariant`; MF-W2-5)

- **Escritores em paralelo:**
  - `agent_spawn` (`audit_log.append_entry`, depois da cura W2.0, com `desc_hash` único por gravação);
  - `audit_emit` pelo spool;
  - drainers oportunistas e drenagens de saída;
  - saídas pelo caminho rápido;
  - saídas cortadas pelo prazo;
  - `kill -9` no meio do drain;
  - reuso de PID, simulado pela adoção de cabeçalho (§3.4).
- **Recuperação de órfãos:** todo spool e todo `.draining.*` deixados por processos mortos são recolhidos
  pelo drain do próximo emissor, oportunista ou de saída, MESMO com todas as outras saídas pelo caminho
  rápido. A premissa «pelo próximo `SessionStart`» foi refutada.
- **Afirmações:**
  - INV-NP por conjunto;
  - `verify_chain()` sobre ≥ N elos;
  - zero breadcrumb de perda (`would-log`, `spool append failed`, `journal flush failed`);
  - ao final, nenhum `.draining.*` nem spool órfão com conteúdo.
- **Mutantes plantados, cada um tem de reprovar:**
  - M-a: a fase 5 apaga um `.draining` parcialmente consumido (perda);
  - M-b: a guarda `_drain_sha256` desligada na recuperação (duplicata);
  - M-c: o estouro do prazo apaga ou renomeia o próprio spool (perda);
  - M-d: a fase 2 renomeia o spool de um PID vivo sem a trava do spool (append em voo roubado, com barreira).
- Os mutantes da W2.4 original (GC que apaga journal com conteúdo; caminho rápido que pula quem tem spool) vivem
  nos testes `-k origin` e `-k fast_path`.

### 6.3 Higiene: fluxo (primário) e teto (secundário)

**Método único de contagem** (W2.6, check do `/ceo-boot` e critério): uma listagem do state dir, `fullmatch`
das regex de §4.7 e `lstat` só onde a categoria exige.

- **H1 — fluxo (primário).** `F = |{p ∈ D : p morto ∧ audit-pending.<p>.journal existe com 0 byte ∧ mtime ≥
  início da janela}| / |D|`.
  - D é o conjunto dos `pid` distintos carimbados nas entradas da era-spool do log canônico (e dos arquivos
    rotacionados), com `wall_ns` na janela de 24 h.
  - Limiar proposto: **F ≤ 0,01**. Antes da cura, F ≈ 1 por construção: todo PID emissor drenado deixa um
    journal com 0 byte **[inferência a partir de `:2276-2297`]**. Por isso o critério não fica verde por
    vácuo num dia leve e não envelhece com o estoque.
  - **|D| = 0 ⇒ reprova.** Medido depois da W2.6, ou com o filtro de mtime, para que o estoque não contamine.
- **H2 — teto (secundário, sanidade).** ≤ 1.000 journals com 0 byte no state dir INTEIRO depois de 24 h de uso
  normal, medidos com as sessões do projeto paradas. **Sob T1, o teto NÃO vale para as travas:** elas crescem
  2 por PID novo, ~15,8 mil por dia no ritmo medido (+3.731 entradas em ~3h47 ⇒ ~330 PIDs por hora
  **[inferência a partir de: medido QA + plano]**). Aplicar o teto às travas reprovaria por construção.
- **H3 — travas.** Reportadas à parte (contagem por nome), sem limiar. Teto teórico: 2 × o espaço de PIDs. No
  macOS, ~10⁵ PIDs (a lane `H-02` estima ~300 mil arquivos nos 3 padrões); no Linux, depende de
  `kernel.pid_max`, que pode chegar a 4.194.304 **[inferência; conhecimento do SO]**. Num Linux de vida longa,
  T1 não tem teto prático, e esse é um gatilho candidato da T2 (pergunta R2-5).

### 6.4 W0.5 pré-registrada (QA MF-2; DevOps MF-7)

O pré-registro vai no LEDGER ANTES de rodar, em árvore descartável, com piso de `df` e limpeza confinada.

- **Células 2³:** {saída sem spool próprio, com spool próprio} × {diretório vazio, ~220 mil entradas} × {1
  saída, ≥ 9 concorrentes}, mais quatro células extras:
  - entrega de decisão BLOCK com portador externo da trava (§4.2);
  - estoque só de travas (~150 mil, a situação depois da cura sob T1, que decide a T2);
  - encerramento do interpretador depois do atexit (calibra `EXIT_MARGIN_S`);
  - intervalo entre o início do interpretador e a âncora.
- **Métricas:** p50/p95 da latência de saída; linhas `drain canonical lock timeout`; decisões descartadas.
- **Vermelho pré-registrado:** ≥ 1 timeout em {220k, ≥ 9} e 0 em {vazio, ≥ 9}; ≥ 1 decisão descartada na
  célula de entrega.
- **Depois da cura:** a mesma matriz, com razão p95 cheio/vazio ≤ 1,2 em N ≥ 30, e `SPOOL_LOCK_TIMEOUT`
  re-medido.
- **Substrato congelado:** versão do CC (Q14), `python3` dos hooks, SO e sha do instrumento.
- **Nada disso vira asserção de tempo no CI.**

### 6.5 Checks com a afirmação no código de saída (QA MF-17)

- Todo Check fica vermelho antes e verde depois, e sai ≠ 0 quando:
  - H1 > 0,01;
  - H2 > 1.000;
  - |D| = 0;
  - há linha `drain canonical lock timeout` datada depois do LAND + janela de convivência (G2, §8.2);
  - há decisão descartada na W0.5.
- **Seletores distintos:** `-k fast_path`, `-k deadline`, `-k origin`, `-k invariant` e `-k gc` (só se o GC
  voltar), com guarda de seletor que casa zero teste (molde `SupersededSelectorTest`).

---

## §7 Pré-condição do SIGN da W2: cura da condição 67 (MF-W2-1)

- **O defeito.** `audit_log.append_entry` lê a chave, o elo anterior e calcula o HMAC ANTES de tomar a trava
  canônica (`audit_log.py:1262-1278`; a trava em `:1283`) **[disco]**. Dois gravadores em paralelo encadeiam
  no mesmo antecessor, e a quebra resultante não tem autor. É a condição 67 assinada da v1.4.0-rc.1.
- **Por que barra a W2.** Sem a cura, S3 (§6.1) só se prova EXCLUINDO o `agent_spawn`, uma propriedade mais
  fraca que a afirmada, e o portador do VETO recusou declarar a exclusão (C9).
- **A cura:**
  - mover a chave, o elo anterior e o HMAC para DENTRO do `with FileLock(...)`, DEPOIS de `rotate_if_needed`
    (`:1285`), para que uma rotação na mesma seção crítica ancore o elo no arquivo novo. O pacote da cura
    confere esse ponto contra o contrato do AMEND-2;
  - um teste de barreira multiprocesso com N gravadores `agent_spawn` e gravadores `audit_emit`: um envoltório
    sobre `read_prev_hmac` sinaliza e espera (barreira menor que os 2,5 s da trava). VERMELHO no HEAD, VERDE
    com a cura;
  - um censo AST: toda chamada a `read_prev_hmac()` fora de teste fica lexicamente dentro de `with FileLock(`,
    com um módulo sintético como controle positivo (cure a classe);
  - a docstring do `test_two_writer_chain.py` corrigida.
- **Custo de cerimônia.** O `audit_log.py` está na lista de kernel (`check_arbitration_kernel.py:217`)
  **[disco]**, então a cura é cerimônia de KERNEL. A estimativa do plano é de 150–300 mil tokens + ~50 mil do
  censo, em 0 a 1 sessão.
- **A linha que aposenta a condição 67** vai no `CHANGELOG.md` do corte W7, NÃO no pacote da cura.
- **A vaga é DECISÃO PENDENTE 1 do Owner (§13).** O VETO da W2 segue levantado até a cura landar.

---

## §8 Reversão e gatilhos

### 8.1 Caminho de reversão (por PEÇA)

As três peças são separáveis e se revertem uma a uma: (a) o caminho rápido, (b) o prazo de saída e (c) a remoção
do journal na origem.

- **Imediato, sem cerimônia:** `CEO_AUDIT_SYNC_MODE=1`. O escritor deixa de usar o spool; na saída, sem spool
  próprio, o caminho rápido torna as três peças inertes. É mudança de COMPORTAMENTO, não reversão byte a byte:
  o modo síncrono tem o próprio perfil de latência (AMEND-1 §5).
- **Definitivo:** `git revert` da peça, em cerimônia canônica (o `spool_writer.py` é canônico e não é kernel).
  O status da emenda passa a `SUPERSEDED-BY-REVERT`, sem ADR novo.
- **Reverter o prazo (b) REABRE a classe da decisão perdida.** Só com decisão escrita do Owner, mesmo que um
  gatilho de higiene dispare. Gatilhos de higiene (G1, G3) revertem (c) ou (a), nunca (b) sozinhos.
- **Sem chave de ambiente nova.** O `CEO_AUDIT_SYNC_MODE=1` já cobre a emergência, e uma variável nova é
  deriva do inventário de ambiente (anti-churn).

### 8.2 Gatilhos (instrumentos LIGADOS, cada um com controle positivo)

| id | gatilho | instrumento (onde roda) | controle positivo | reverte |
|---|---|---|---|---|
| **G1** | resíduo acima do limiar (H1 > 0,01 OU H2 > 1.000) em 3 medições diárias seguidas | check do `/ceo-boot` (§9) + script do critério (§6.3), mesmo método | árvore descartável com 1.001 journals sintéticos com 0 byte de PIDs mortos ⇒ o check sai ≠ 0 | (c), depois investigar |
| **G2** | linha `drain canonical lock timeout` datada depois do LAND + janela de convivência (até todas as sessões do projeto reiniciarem) — depois da cura, NENHUM chamador vivo a produz | contagem por data no `audit-log.errors` (o breadcrumb traz carimbo UTC, `:611-613`) + a W0.5 re-rodada depois do LAND | no HEAD a taxa é ~1.100/h **[consenso]**; em teste, o `drain_now(force=True)` direto sob trava externa a produz (teste 4) | investigar o chamador; (a)/(b) se a origem for a emenda |
| **G3** | `.draining.*` OU spool órfão com conteúdo (PID morto) com mais de 24 h | check do `/ceo-boot` (§9) | arquivo plantado com mtime de 25 h numa árvore descartável ⇒ o check sinaliza | (a), depois investigar a perna 3 |
| **G4** | decisão BLOCK descartada no controle de entrega | célula de entrega da W0.5, re-rodada depois do LAND e a cada mudança de substrato (versão do CC) | o vermelho do HEAD, ou o mutante «auxiliar ignora o prazo» | (a)/(c) sob decisão do Owner; (b) nunca sem decisão escrita |
| **G5** | quebra de cadeia ATRIBUÍVEL à W2 depois da cura da condição 67: o elo quebrado, ou o antecessor, é linha anexada pelo drain (`_drain_epoch` presente) na janela pós-LAND | `audit-verify-chain.py` / `verify_chain()` sobre o log vivo e os arquivos rotacionados da janela | cópia descartável com um byte alterado numa linha anexada pelo drain ⇒ o verificador acusa e a atribuição aponta a W2 | a peça envolvida; ADR-052 avisado |
| **G6** *(proposta; ver R2-3)* | perda REAL: `record_id` com `commit` num journal de PID morto, ausente do log canônico (e dos arquivos rotacionados) e de todo spool ou `.draining.*` | verificador SÓ-LEITURA, fora de hook (sem custo no `SessionStart`) | cópia descartável com uma linha canônica removida ⇒ o verificador conta 1 | investigar; ADR-052 avisado |
| — | diretiva do Owner | — | — | qualquer peça |

### 8.3 Gatilhos herdados que este rascunho aposenta

- **`truly_lost > 0` em 7 dias** (AMEND-1 §5, gatilho 3; AMEND-3 frontmatter e §5): MORTO, porque nenhum
  caminho incrementa o campo. O MF-W2-4 pedia mantê-lo («`truly_lost_7d ≥ 1`»), mas como gatilho literal ele
  nunca dispara. Este rascunho o substitui pelo INV-NP nas provas, pelo G3 em produção e, se a rodada 2
  aceitar, pelo G6, que é a medida HONESTA de «perdido de fato». Pede novo julgamento do portador do VETO.
- **Taxa de quebra > 0,1% em 30 dias** (AMEND-1 §5, gatilho 1; AMEND-3 §5): inavaliável enquanto a condição 67
  existir. O plano cita 4 quebras em ~461 elos (≈ 0,9%) **[plano, risco 11]**. Este rascunho o substitui pelo G5.
- **«Drain lock contention caused production tool-call timeout»** (AMEND-1 §5, gatilho 2): fica, reescrito
  como G2 + G4, os instrumentos que o tornam observável.

---

## §9 Observabilidade pelo resultado, sem tocar o `audit_emit.py`

- **Nenhum evento por arquivo e nenhuma ação nova em `_KNOWN_ACTIONS`.** Um evento emitido por um processo sem
  spool recriaria os 3 arquivos que a W2 quer deixar de criar (R-DO15), e o `audit_emit.py` é kernel. Os três
  críticos concordaram (C17).
- **Check advisory no `/ceo-boot`** (`ceo-boot.py`, oráculo 0, no pacote do item livre L2; mapa de
  colisões). Ele mostra:
  - a contagem POR NOME dos 3 padrões, numa listagem sem `stat` por entrada;
  - os journals com 0 byte, com `stat` limitado aos primeiros 2.000 journals por nome e «≥ 2.000» quando o
    limite estoura (suficiente para decidir H2 ≤ 1.000);
  - a idade do `.draining.*` mais velho;
  - **a contagem e a idade do spool órfão com conteúdo mais velho (PID morto)** — o resíduo visível de
    `exit_deadline_skip`; acréscimo deste rascunho, pergunta R2-4.

  O check roda na skill, nunca em hook. Uma varredura com `stat` por entrada levou 50,7 s **[medido:
  DevOps]**. O orçamento de tempo do check é medido na W0.5.
- **O estouro do prazo é silencioso em hook.** O artefato que ele deixa, o spool órfão com conteúdo, É o sinal,
  visto pelo check. Se a rodada 2 exigir linha no `audit-log.errors` para os detectores por contagem
  (`ceo-diagnose.py:343-420`, `status.py`), ela sai do CHECK do boot quando um gatilho dispara, no máximo uma
  por execução, nunca de hook (pergunta R2-4).
- **Contagens da W2.6 no LEDGER** (§5.3).

---

## §10 Opções consideradas

| opção | decisão | por quê |
|---|---|---|
| A. Relocar journals e travas para um subdiretório (antiga W2.3) | **rejeitada** | duas travas para o mesmo recurso durante a convivência de versões (C14); journal velho órfão com conteúdo para sempre (R-DO5) |
| B. GC de travas de PID morto dentro do hook | **rejeitada** | VETO (§2(b) do consenso); sem re-checagem de inode, quebra a exclusão mútua (R-SEC5, R-QA1) |
| C. O dono apaga as próprias travas na saída | **adiada** | premissa falsa no caso `.draining` (§2.4); só volta com as quatro garantias (§4.4) |
| D. T2: re-checagem de inode no `filelock.py` | **condicional** | pacote de kernel próprio, se a W0.5 depois da cura o exigir (§4.4) |
| E. Ligar a reconciliação de início de sessão | **rejeitada na W2** | abriria ~76 mil journals sob o timeout de 5 s do `SessionStart`; follow-up |
| F. Evento por arquivo / ação nova no kernel | **rejeitada** | recria os arquivos; toca o kernel sem necessidade (§9) |
| G. Drenagem de saída SÓ do próprio spool, sem listagem | **não adotada** | a perna 3 depende da varredura global de OUTROS emissores. Hooks curtos raramente disparam o drain oportunista (`should_drain` exige spool próprio com idade > 100 ms ou ≥ 100 linhas, `:1098-1119`), então a varredura da saída é o veículo principal da perna 3 **[inferência]**. Tirá-la enfraquece a vivacidade. Concorre com a T2 se a W0.5 mostrar que a listagem sozinha estoura o prazo |
| H. Fechar o stdout antes do drain, para entregar a decisão antes | **não adotada** | depende de o harness esperar a saída do processo ou o EOF, semântica do substrato que não foi medida. O prazo funciona nos dois casos. Pode virar célula da W0.5 |
| I. Chave de ambiente nova para as peças da emenda | **não adotada** | o `CEO_AUDIT_SYNC_MODE=1` já cobre; anti-churn (§8.1) |
| J. Prazo por hook (timeout da própria registração) | **não adotada** | o processo não sabe por qual registração foi chamado; usa-se o mínimo global, com teste de deriva (§4.2) |

---

## §11 Consequências e resíduos declarados

**Positivas (+)**

- A decisão BLOCK deixa de depender do tamanho do diretório e da contenção, por qualquer causa de lentidão.
- As saídas sem conteúdo próprio, a maioria dos hooks **[inferência; a W0.5 mede]**, deixam de tomar a trava
  canônica: menos contenção para todos, inclusive para o `agent_spawn` (§3.5).
- Os journals vazios deixam de se acumular (1/3 do estoque).
- Os gatilhos de reversão passam a disparar de fato.

**Negativas (−)**

- Sob T1, as travas seguem crescendo, 2 por PID novo, até o teto do espaço de PIDs. Num Linux de vida longa
  esse teto é grande (§6.3 H3).
- O estouro do prazo adia o spool para a perna 3. Sem novo emissor no projeto, ele espera no disco: durável,
  mas sem vivacidade.
- A frequência de `exit_deadline_skip` em produção não é observável diretamente; o proxy é o spool órfão com
  conteúdo (§9).
- `DrainStats` ganha um campo em processo, e `drain_now` ganha um parâmetro opcional.

**Neutras (~)**

- Uncontended, o caminho com conteúdo próprio é idêntico ao de hoje.
- O ganho de latência vem das saídas sem conteúdo e da cauda contendida.

**Resíduos declarados (vão para o material assinado)**

1. **Âncora tardia:** o prazo conta da importação do `spool_writer`. Um hook que importa o `audit_emit` tarde,
   depois de trabalho pesado, subestima o tempo decorrido e pode passar do timeout (pergunta R2-1).
2. **Timeout de adopter:** um adopter que reduza um timeout de hook abaixo de `EXIT_DEADLINE_S + EXIT_MARGIN_S`
   quebra a garantia sem que o teste do repositório o veja.
3. **Parte não preemptível** da drenagem (§4.2, item 6), proporcional ao estoque de travas sob T1.
4. **Journal com 0 byte** por falha de `write` depois do `O_CREAT`: raro, fica para a W2.6.
5. **~214 journals com conteúdo forense-only;** sem leitor em produção (a reconciliação está morta).
6. **Perda pré-existente** do `agent_spawn` por trava canônica ocupada (`would-log`): reduzida, não eliminada
   (§3.5).
7. **Janela TOCTOU da W2.6** entre o reexame e o `unlink` (§5.1).
8. **Mesmo UID:** um processo do mesmo usuário pode apagar ou forjar arquivos do state dir. A fronteira é a
   mesma de `CLAUDE.md` §5.

---

## §12 Raio de explosão, regra 10×, paths e anti-churn

- **Módulos.**
  - `.claude/hooks/_lib/spool_writer.py`: canônico, NÃO kernel; mesma via do AMEND-3, sentinela padrão.
  - `.claude/hooks/tests/test_spool_state_gc.py` (novo) e `test_spool_drain_contended_skip.py` (teste 4 intacto).
  - `.claude/scripts/ceo-boot.py`: livre, no pacote da L2.
  - O arquivo de emenda.
  - **W2.0 à parte:** `audit_log.py` (kernel) e `test_two_writer_chain.py`.
  - **T2, condicional:** `_lib/filelock.py` (kernel).
- **Fora:** `audit_emit.py`, `SessionStart.py`, `audit_hmac.py`, `canonical_json.py` e `audit-verify-chain.py`.
- **Reversibilidade:** ALTA para (a) e (c) (§8.1); para (b) é técnica, mas reabre a classe da decisão perdida.
- **Regra 10×.** Com 10× mais hooks por dia, o estoque de travas sob T1 satura o espaço de PIDs em dias, e não em
  semanas. A listagem atinge o custo máximo mais cedo, e o prazo continua protegendo a decisão; o gatilho da T2
  (§4.4) e o H3 tornam isso visível. Os journals não escalam com o volume, porque a cura é na origem. O prazo não
  depende do volume.
- **Anti-churn (ADR-115/ADR-124).** A emenda refina mecanismos do AMEND-1 e do AMEND-3 por arquivo próprio, sem
  ABI nova de spool, sem layout novo, sem ação nova de auditoria e sem variável de ambiente nova.

---

## §13 Decisões pendentes do Owner (escritas como tais)

1. **Vaga da cura da condição 67 (decisão pendente 1 do consenso).**
   - **Recomendação do CEO:** pacote PRÓPRIO, landado ANTES do SIGN da W2, o primeiro na vaga da W2 ou a
     primeira vaga que abrir antes.
   - **Alternativa:** dentro do pacote da W2, com +2 paths.
   - **Custo:** é cerimônia de KERNEL (`audit_log.py`, §7).
   - **Efeito:** o VETO da W2 fica LEVANTADO até a cura landar. **PENDENTE.**
2. **Pré-condição da W2.6 (decisão pendente 2 do consenso).**
   - **Recomendação do CEO:** trocar «todas as sessões do Claude fechadas» por «todas as sessões DESTE projeto
     fechadas», porque o state dir é por projeto desde a W1 do PLAN-182; e rodar já.
   - **Refinamento deste rascunho, para o Owner decidir junto:** o texto do consenso fala em «recusar se achar
     arquivo da família com PID vivo». Lido como recusa da EXECUÇÃO INTEIRA, isso faria o script nunca rodar:
     os 75.609 PIDs distintos ocupam ~76% do espaço de PIDs do macOS **[medido: QA]**, então algum PID de
     família quase certamente pertence hoje a um processo alheio vivo. Proposta: PID vivo ⇒ a FAMÍLIA é
     pulada e contada; mtime < 10 min em qualquer arquivo da família ⇒ a execução inteira recusa (§5.2).
   - A decisão vigente (S359) vale até o Owner decidir. **PENDENTE.**
3. **Para ciência, sem decisão agora:**
   - o estoque dos adopters não é limpo pela W2; a recomendação é um follow-up fora da 1.4.3 (script
     entregável), declarado no material assinado;
   - reverter o prazo de saída exige decisão escrita do Owner (§8.1).

---

## §14 Perguntas para a rodada 2 (o que este rascunho propõe além do consenso)

- **R2-1 — âncora do prazo.** A âncora é a importação do `spool_writer`. Basta, com o resíduo declarado? Ou
  entra um censo AST que exija importar o `audit_emit` antes do trabalho principal, ou uma função de armar o
  prazo no início do `main` (precedente: `_start_wall_budget` de `check_canonical_edit.py:1165-1175`)?
- **R2-2 — W2.4 vira condicional.** O rascunho tira o GC em hook do pacote base, porque a compactação é o único
  produtor de journal com 0 byte (§4.3, §4.5). Isso diverge do texto atual da W2.4 do plano.
- **R2-3 — G6.** Um verificador de perda real SÓ-LEITURA, fora de hook, reabilita de forma honesta o
  «`truly_lost`» que o MF-W2-4 pedia. Entra na W2 ou vira follow-up?
- **R2-4 — sinais do check.** O spool órfão com conteúdo entra no check do boot, e o check do boot escreve no
  máximo uma linha no `audit-log.errors` quando um gatilho dispara?
- **R2-5 — valores para pré-registrar.**
  - ε = 0,01 (H1);
  - `EXIT_MARGIN_S` = 1,0 s e prazo de 2,0 s;
  - N ≥ 1.000 elos;
  - limite de 2.000 `stat` no check;
  - o teto de 1.000 só para journals sob T1;
  - o Linux de vida longa (H3) como gatilho adicional da T2.
- **R2-6 — sinalizador próprio.** A janela de vida do `_OWN_DRAIN_PENDING` (§4.1, item 2) cobre todos os
  caminhos em que o próprio processo deixa um `.draining`?
- **R2-7 — slug do arquivo.** O plano fixa `ADR-055-AMEND-4-spool-state-gc.md`. Sem GC em hook, «gc» descreve
  mal a emenda; trocar o slug custa mexer no mapa de colisões. O rascunho mantém o slug do plano.

---

## §15 Rastreabilidade dos must-fix

### 15.1 Segurança — condição do VETO da W2

| MF | pedido (resumo) | onde este rascunho o endereça | estado |
|---|---|---|---|
| **MF-W2-1** | cura da corrida do `audit_log.py` antes do SIGN, com teste vermelho→verde e `verify_chain()` íntegro | §7; §1 portão 2; §6.1 S3; §13 decisão 1; frontmatter `sign_precondition` | desenho completo; **vaga pendente do Owner** |
| **MF-W2-2** | nenhum hook apaga `*.lock`; cura na origem; GC de travas só na W2.6 | §4.4 (T1/T2/T3, «dono apaga as próprias travas» adiada); §4.3 (journal na origem, sob a própria trava); §4.5 (sem GC em hook); §5 (W2.6 é a única que remove travas) | endereçado |
| **MF-W2-3** | prazo na drenagem forçada de saída, derivado do orçamento do hook; controle de ENTREGA DE DECISÃO vermelho→verde | §4.2 (âncora, prazo, aplicação, «não anômalo», controle W0.5 + prova estrutural); §6.1 S1; §6.4; G4 em §8.2 | endereçado (valores a pré-registrar, R2-5) |
| **MF-W2-4** | arquivo próprio com: invariante de três pernas e quem cumpre a perna 2 quando o caminho rápido a pula; regra de versões mistas; regex ancoradas; lista do que nunca se apaga; reversão e gatilhos | arquivo próprio (frontmatter, §2.1); §3.1–3.3 (INV-NP e a resposta sobre a perna 2); §4.6 (versões mistas: nenhum caminho muda, logo a leitura dupla e a dupla trava não se aplicam); §4.7; §4.8 (lista ampliada com `.corrupt-header.*`, spool ativo e a família do log); §8 | endereçado. **Divergência declarada:** o gatilho `truly_lost_7d ≥ 1` pedido é inavaliável (§8.3); a substituição (G3 + INV-NP + G6 proposto) pede novo julgamento do portador do VETO |
| **MF-W2-5** | estresse com todos os gravadores; recuperação de órfão «pelo próximo `SessionStart`»; `truly_lost = 0` | §6.2 (todos os gravadores, `kill -9`, reuso de PID, mutantes); recuperação pelo drain do PRÓXIMO EMISSOR (§3.2) | endereçado com a premissa corrigida: não há drain no `SessionStart`, e `truly_lost` está morto (o INV-NP o substitui) |
| **MF-W2-6** | script da W2.6: resolvedor, recusa de symlink, `unlink` relativo ao descritor, reexame, simulação, recusa com sessão viva, contagem pelo mesmo método | §5.1–5.3 (mais o manifesto de hash e a tabela de predicado) | endereçado; a pré-condição de sessão é a **decisão pendente 2** |

### 15.2 QA Architect (must-fix da W2 e o transversal)

| MF | onde |
|---|---|
| 1 — prova de exclusão mútua para qualquer `unlink` de caminho de trava | opção (b) adotada: nenhum `unlink` de `*.lock` em hook (§4.4); o controle de intercalação vale para a remoção do JOURNAL (§4.3) e é exigido se a remoção de travas pelo dono voltar (§4.4) |
| 2 — W0.5 pré-registrada (células 2³, substrato, vermelho, razão) | §6.4 |
| 3 — limiar por FLUXO com denominador; gatilho que dispara, com controle positivo; não herdar `truly_lost` | §6.3 H1; §8.2 (todos com controle positivo); §8.3 |
| 4 — invariante por CONJUNTO, ≥ N elos, escritores mistos, mutantes | §3.1; §6.1 S2/S3; §6.2 |
| 5 — células do caminho rápido (a)–(e) + órfão pelo drain oportunista | §4.1 (células (a)–(f)) |
| 6 — tabela de predicado pré-registrada com quase-acertos e journals com conteúdo como controle | §5.2; §5.3 (manifesto de hash) |
| 7 — convivência da relocação | prejudicado (a relocação saiu); fica a regra de versões mistas (§4.6) |
| 8 — condição 67: cura, barreira, censo AST, docstring | §7 |
| 17 (transversal) — Checks vermelho→verde com a afirmação no código de saída | §6.5 |

### 15.3 DevOps Engineer (must-fix da W2)

| MF | onde |
|---|---|
| 1 — cura na origem no lugar da relocação | adotada para os JOURNALS (§4.3); a parte das travas foi recusada pelo VETO (§4.4) |
| 2 — o caminho rápido confere só o próprio spool; união de não-perda reescrita | §4.1; §3.2–3.3 |
| 3 — transição sem perda, se a relocação ficasse | prejudicado (a relocação saiu); §4.6 |
| 4 — GC de carona na fase 2, depois de soltar a trava, com teto | condicional (§4.5), com as condições preservadas |
| 5 — observabilidade pelo resultado no `/ceo-boot`; sem evento por arquivo; `audit_emit.py` fora | §9 |
| 6 — AMEND-4 em arquivo próprio; limiar absoluto; gatilhos (a)–(c) ligados; `truly_lost` declarado morto | arquivo próprio; o limiar absoluto vira teto secundário (§6.3 H2, consenso §2(d)); gatilhos G1–G3 (§8.2); §2.4 e §8.3 |
| 7 — W0.5 mede latência p50/p95 em 4 células, antes e depois | §6.4 (2³ + células extras) |
| 8 — corrida do `audit_log.py` antes ou junto; estresse com `agent_spawn` | §7; §6.2 |

---

## §16 Evidência lida (HEAD `a9924eb1`)

- `.claude/hooks/_lib/spool_writer.py`:
  - `:53`, `:63-66`: constantes;
  - `:70-79`: sufixos;
  - `:98-127`: `DrainStats`;
  - `:130-138`: `JournalReconciliation`;
  - `:265-266`: state dir;
  - `:445-481`: nomes;
  - `:581-582`: `.corrupt-header`;
  - `:606-615`: breadcrumb com carimbo UTC;
  - `:731-775`: adoção de cabeçalho;
  - `:940-973`: flush;
  - `:976-1074`: `spool_append` e `record_id`;
  - `:1082-1121`: `should_drain`;
  - `:1233-1257`: PID vivo e `int()`;
  - `:1260-1407`: fase 2;
  - `:1892-1900`: `record_id` no canônico;
  - `:2248-2301`: compactação;
  - `:2309-2326`: estagnação;
  - `:2329-2459`: `drain_now`;
  - `:2467-2565`: reconciliação morta e `truly_lost`;
  - `:2573-2682`: saída e sinal.
- `.claude/hooks/_lib/filelock.py:128-164`: `O_CREAT` + `flock`, sem inode.
- `.claude/hooks/_lib/audit_emit.py`: `:2778-2799` (spool e drain oportunista); `:13330-13348` (instalação dos
  handlers no import).
- `.claude/hooks/audit_log.py`: `:667-700` (entrada `agent_spawn`); `:1256-1331` (HMAC fora da trava; perda
  `would-log`).
- `.claude/hooks/_lib/audit_hmac.py:476-482`: contrato «MUST be called WITH the audit-log FileLock held».
- `.claude/hooks/check_arbitration_kernel.py`: `:99`, `:137`, `:173`, `:217` (kernel).
- `.claude/hooks/check_canonical_edit.py:1165-1175`: precedente de prazo de parede.
- `.claude/hooks/tests/test_spool_drain_contended_skip.py`: `:195-231` (testes 3 e 4).
- `.claude/hooks/tests/test_two_writer_chain.py:1-17`.
- `.claude/settings.json` e `templates/settings/*.json`: timeouts das registrações de hook (mínimo de 3 s no
  repositório e de 5 s nos perfis).
- `.claude/adr/ADR-055*.md` (base e AMEND-1..3); `ADR-186-hook-deadline-policy.md`; `.claude/adr/README.md`.
- `.claude/plans/PLAN-194/debate/round-1/` (consenso e as três críticas); seção W2 do plano (árvore de
  trabalho da S361, com os ajustes da rodada 1 aplicados).

Nenhum conteúdo lido trouxe instrução dirigida a este redator. Não houve injeção a relatar.
