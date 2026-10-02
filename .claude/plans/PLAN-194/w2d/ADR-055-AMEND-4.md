---
id: ADR-055-AMEND-4
title: "ADR-055 §Components — estado da auditoria sem acúmulo: caminho rápido de saída, prazo na drenagem forçada de saída, trava presa vira sinal, journal vazio removido na origem e invariante de não-perda reescrito"
status: PROPOSED
condensed: true
source_draft: ".claude/plans/PLAN-194/debate/round-2/ADR-055-AMEND-4-draft.md — 1.038 linhas, sha256 98eab278bebc50a8f362561b1123df0b0384c09105e9deeea7eba32561dcb00a (blob no HEAD `9a458f19`; última alteração em `092377af`). Fonte integral; este arquivo é a parte normativa condensada (decisão D-6 do Owner)."
draft_for: "texto do pacote de ADR U2-D (W2D) do PLAN-194. O arquivo canônico `.claude/adr/ADR-055-AMEND-4-spool-state-gc.md` nasce só nesse pacote, com este texto. O slug fica (R2-7, anti-churn)."
proposed_at: 2026-10-02
proposed_by: "CEO (S361, PLAN-194 W2.1); rascunho integral pelo arquétipo VP Engineering; condensação FD-16 (S362) pelo arquétipo Technical Writer"
amendment_of: "ADR-055 (Audit-log HMAC chain for tamper detection — 2026-04-18 via PLAN-023)"
amends_section: "§Components §3 — drenagem forçada de SAÍDA e contabilidade de não-perda (refina ADR-055-AMEND-1 §4 Fase 1, §4 «Loss accounting» e §5; refina ADR-055-AMEND-3 §3, §4 e §5)"
veto_floor: "ADR-052 (security-engineer VETO — integridade do log de auditoria; herdado do ADR-055-AMEND-3)"
debate_status: "W2 `design-coherent` na rodada 2 (PROCEED dos três críticos); VETO de Segurança RETIRADO sob MF-R2-W2-1..4, aplicadas neste texto; debate ratificado pelo Owner em 2026-10-02 (`debate/round-3/approved.md`)."
debate_record: ".claude/plans/PLAN-194/debate/round-1/consensus.md; .claude/plans/PLAN-194/debate/round-2/consensus.md; .claude/plans/PLAN-194/debate/round-3/approved.md"
codex_pair_rail: "required per ADR-107 — pendente; roda nos bytes canônicos do pacote U2-D"
risk_tier: A
debate_required: true
sign_precondition: "SATISFEITA — a cura da corrida do `agent_spawn` (condição 67 assinada da v1.4.0-rc.1, W2.0) landou assinada em `65cd50d7` (sentinel `.claude/plans/PLAN-194/wave-auditrace-approved.md`)"
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
  - "ADR-055-AMEND-3 frontmatter `revert_trigger_truly_lost_7d: 1` e §5 «`truly_lost > 0` over 7-day window» — morto por construção (`truly_lost` nunca é incrementado; §8); substituído pelo G6 (perda real, ATIVO) e pelo G7 (§8.2)"
  - "ADR-055-AMEND-1 §5 gatilho 3 (`truly_lost > 0` em 7 dias) — idem"
  - "ADR-055-AMEND-1 §5 gatilho 1 e ADR-055-AMEND-3 §5 (taxa de quebra de cadeia > 0,1% em 30 dias) — substituído pelo G5, que atribui a quebra à W2 (§8.2, §8.3)"
target_telemetry_window_days: 30
tags: [governance, audit-log, spool-writer, async-drain, amendment, hook-exit-latency, decision-delivery, no-loss-invariant, anti-accumulation, starvation-signal, plan-194-w2]
enforcement_commit: "n/a (texto PROPOSED; o runtime nasce nos pacotes U2-A a U2-C, §12)"
---

# ADR-055-AMEND-4 — Estado da auditoria sem acúmulo (W2 do PLAN-194)

**Status:** PROPOSED, parte normativa CONDENSADA (D-6, plano `:2049`); ACCEPTED só no pacote U2-D (§1). **Data:** 2026-10-02.
**Fonte integral:** `.claude/plans/PLAN-194/debate/round-2/ADR-055-AMEND-4-draft.md`, 1.038 linhas, sha256
`98eab278bebc50a8f362561b1123df0b0384c09105e9deeea7eba32561dcb00a`. «Rascunho `:N`» aponta para esse blob.

> **Prevalência.** Normativas: §3 a §9, §11 e §12; as demais são status, contexto e índice. O rascunho guarda o detalhe
> (células de teste, opções, rastreabilidade, evidência). Onde divergir deste texto, vale este texto SÓ nos pontos
> do §0; no resto, o rascunho. Entre plano e AMEND-4, vale o AMEND-4 (MF-R2-W2-4). Seções numeradas como no
> rascunho. **[disco]** = conferido no HEAD `9a458f19`, igual ao HEAD `48f03b3a` do rascunho salvo o `audit_log.py`
> (mudado em `65cd50d7`); **[medido: X]** = medido por X, só leitura, com data.

## §0 Atualizações sobre o rascunho (FD-16, S362)

| rascunho | antes | agora |
|---|---|---|
| `:118`, `:230` | `audit_log.py:1325-1329` (`would-log`), `:1323-1324` (`append failed`) | `audit_log.py:1341-1348` (`except FileLockTimeout` em `:1341`, texto em `:1347`); `append failed` em `:1339-1340` [disco] |
| `:161`, `:722-723` | elo anterior e HMAC FORA da trava (`:1262-1278`; trava em `:1283`) | histórico até `65cd50d7`; hoje `with FileLock` em `:1275` e `read_prev_hmac` em `:1290` (§7) |
| `:226` | `append_entry` em `:667-700` e `:1280-1296` | entrada montada em `:666-702`; `append_entry` em `:1210-1350` [disco] |
| `:163`, `:965` | «0 linhas `STARVED`» | 0 às 03:40Z; 2 às 08:36Z; 6 às 20:57Z (§2) |
| `:117-119`, `:766` | 3 linhas `would-log=` | 15 às 20:57Z (§2) |
| `:643-645` | H1: \|D\| = 1.049, F = 0,999 | também LEDGER `:138-143`: \|D\| = 14.572, F = 0,9947 (§6) |
| `:480` | LAND com as sessões DESTE projeto fechadas | D-19 (§4.7) |
| `:547`, `:926` | a 1.ª W2.6 pode rodar já | depois do LAND do U2-B (D-5, plano `:2048`; §5) |
| `:18`, `:100`, `:720-737`, `:917-919` | W2.0 pendente (decisão 1 do Owner) | SATISFEITA em `65cd50d7`; decisão 1 superada (§7, §13) |
| `:357`, `:660` | ~220 mil entradas | 233.055 (LEDGER `:87-88`) |

## §1 Status e portões de aceitação

PROPOSED. O flip para ACCEPTED acontece SÓ no commit de cerimônia do U2-D e exige: (1) debate — **feito** (rodada 2
PROCEED; VETO retirado sob MF-R2-W2-1..4; ratificado pelo Owner em 2026-10-02); (2) W2.0 — **feita** (`65cd50d7`,
§7); (3) W0.5 pré-registrada (LEDGER `:80-136`), rodada no HEAD antes do SIGN do U2-A e, no braço pós-cura, na
sombra do U2-C; (4) rail do Codex (ADR-107) nos bytes canônicos, ≤ 3 rodadas, NO-GO só por P0 ou afirmação FALSA,
conferindo também que plano e texto dizem o mesmo; (5) GPG do Owner, com o `## Amended-by` do ADR-055 e o leque de
ADR re-derivado no MESMO commit.

## §2 Contexto (premissas refutadas: rascunho `:154-164`)

- **Sintoma.** 233.055 entradas no state dir (LEDGER `:87-88`). Cada emissor deixa duas travas e um journal com
  0 byte, que a compactação reescreve e nunca remove (`spool_writer.py:2276-2297`). Às 2026-10-02T20:57Z, o
  `audit-log.errors` tinha 37.970 linhas, 37.715 delas `drain canonical lock timeout` [medido: redator FD-16].
- **Perda real.** 15 linhas `would-log=` (`agent_spawn` descartado, `audit_log.py:1341-1348`) entre
  2026-10-01T23:48:41Z e 2026-10-02T20:49:53Z: 3 com carimbo anterior ao commit da W2.0 (12:18Z) e 12 posteriores
  [medido: redator FD-16]. Nenhum instrumento as acusava.
- **Risco de segurança.** Um guard que decidiu BLOCK e estoura o timeout na SAÍDA é morto pelo harness, e a ação
  passa sem decisão (lane `CC285-05` [plano]). Todo import do `audit_emit` registra o drain de saída
  (`audit_emit.py:13336-13348`), que toma a trava canônica até em hook que nunca emitiu (espera de até 2,5 s,
  `spool_writer.py:66`) e lista o diretório (`:1273`). Com stdout em pipe, o 1.º byte sai em 1,54 s; com `flush` no
  início do `atexit`, em 0,03 s (rascunho `:122-125`).
- **Premissa que muda.** O AMEND-3 chamava de anômalo o timeout do drain forçado; com prazo, vira desvio ESPERADO.
- **`STARVED` do AMEND-3.** 0 linhas às 03:40Z (rascunho); 2 às 08:36Z (08:35:20Z e 08:36:23Z; fonte: analistas do
  runbook S362, fora do LEDGER; conferidas pelo redator FD-16); 6 às 20:57Z, todas do portão OPORTUNISTA, e 0
  `STARVED (exit)` [medido: redator FD-16]. O salto de saída da §4.2 não tem portão; daí a §4.3.

## §3 Invariante de não-perda (INV-NP)

**R** = os `record_id` com `spool_append` bem-sucedido (linha escrita e com `fsync`). O `record_id` nasce em
`spool_writer.py:1026` e sobrevive no canônico, pois a fase 4 só retira `_drain_*`, `hmac` e `hmac_error`
(`:1896-1900`) [disco]. Para todo r ∈ R: **(a) segurança** — nenhum código apaga arquivo com r antes de r estar no
log canônico (a fase 5 só apaga `.draining.*` todo consumido); **(b) unicidade** — r aparece no máximo UMA vez
(`_drain_sha256` em `K_TAIL_WINDOW` e rejeição de 4-tupla); **(c) vivacidade condicionada** — havendo drainer
futuro deste projeto que ganhe a trava, r chega ao log exatamente uma vez, salvo quarentena (`.malformed.*`,
`.quarantined.*`, `.test-origin.*`, `.corrupt-header.*`), contada à parte e nunca apagada. Prova (W2.5): drain até
ponto fixo e igualdade de CONJUNTO («contagem igual» NÃO serve); em produção, o G6 mede a violação. O journal NÃO
entra no INV-NP: é contabilidade de melhor esforço.

**Pernas** (não existe perna de `SessionStart`; os únicos `force=True` vivos são atexit e sinal, `:2581`, `:2610`):
**1**, o dono em vida, com `should_drain()` verdadeiro e a trava obtida sem bloquear (`audit_emit.py:2790-2791`);
**2**, o dono na saída, SÓ com conteúdo próprio (§4.1) e com prazo em hook (§4.2); **3**, a fase 2 de QUALQUER
drainer seguinte deste projeto que ganhe a trava, que recolhe spools de PID morto (`:1343`) e todo `.draining.*`,
até de PID vivo (`:1277-1317`). Cortada pelo prazo, a perna 2 deixa o spool intacto para a perna 3. PID reusado por
processo alheio causa ATRASO, não perda; por hook deste projeto, o novo processo adota o cabeçalho (`:746-775`).
Lote ≤ `K_MAX` = 100 (`:53`). O spool é PRÉ-cadeia, sem HMAC; daí o sinal em ≤ 1 h (§4.3) e a taxa no boot (§9).

**Escritor direto `agent_spawn`** (`audit_log.append_entry`, `:1210-1350`; entrada em `:666-702`): escreve sem spool
e sem `record_id` [disco]. No estresse, cada linha leva um `desc_hash` único, e o INV-NP vale para ela. Perdas
pré-existentes: com a trava ocupada por mais de 2,5 s, grava só `lock timeout (stale?)  would-log=…` (`:1341-1348`);
com `OSError`, só `append failed: …` (`:1339-1340`). A W2 REDUZ a primeira e MEDE as duas (G7), sem eliminá-las. No
estresse, `would-log`, `append failed`, `spool append failed` ou `journal flush failed` reprova.

## §4 Decisão

### 4.1 Auxiliar de saída e caminho rápido (U2-A)

Um auxiliar único, chamado por `_atexit_drain` (`:2573`) E por `_signal_drain_handler` (`:2590`), nunca por
`drain_now(force=True)`, executa nesta ordem:
1. `sys.stdout.flush()` e `sys.stderr.flush()`, cada um em `try`: a decisão sai antes de qualquer espera. Não
   substitui o prazo.
2. Flush do buffer do journal próprio, com espera limitada ao orçamento; vencido o prazo, `timeout=0`.
3. UM `stat` do próprio spool e o sinalizador `_OWN_DRAIN_PENDING`, à prova de falha: LIGA antes do `os.rename` do
   próprio spool na fase 2 (`:1383-1384`) e quando um `drain_now` termina com `ok=False`; DESLIGA só com o
   `.draining` próprio consumido e removido, ou em quarentena.
4. Spool ausente ou com 0 byte e sinalizador desligado ⇒ sai, sem trava canônica e sem
   `listdir`/`scandir`/`glob`/`iterdir`; caso contrário, UMA tentativa de drenagem (§4.2), nunca laço.

Células (a)–(j), seletores `fast_path` e `flag`: rascunho `:263-280`. Fica INTACTO o teste 4
(`test_spool_drain_contended_skip.py:220-231`: `drain_now(force=True)` sob trava externa ⇒ `ok=False` e breadcrumb).

### 4.2 Prazo na drenagem de saída de hook (U2-C; MF-W2-3, MF-R2-W2-2)

- **Escopo:** só processo de HOOK, isto é, `Path(sys.argv[0])` em `_HOOKS_DIR` (`spool_writer.py:29`); o wrapper
  faz `exec` e mantém o PID (`_python-hook.sh:304`, `:413`). Fora de hook, a espera segue `SPOOL_LOCK_TIMEOUT`, com
  o mesmo caminho rápido, a mesma classificação silenciosa e o mesmo portão STARVED.
- **Âncora** = `min(_IMPORT_ANCHOR, monotonic_agora − idade_do_processo)`; a idade vem do KERNEL, só na saída lenta:
  no macOS, `sysctl` `KERN_PROC_PID` via `ctypes` (medido: 648 bytes, 2,6–3,3 ms); no Linux, o campo 22 de
  `/proc/self/stat` contra `CLOCK_BOOTTIME` [inferência; NÃO medido]. Falha ou idade inválida ⇒ `_IMPORT_ANCHOR`.
  O `min` só ADIANTA a âncora. No caminho bloqueante do grok, o Python é FILHO (`_python-hook.sh:420`): declarado.
- **Prazo:** `EXIT_DEADLINE_S = T_min − EXIT_MARGIN_S`; `T_min` = menor `timeout` de hook em `.claude/settings.json`
  e `templates/settings/`, hoje 3 s (`.claude/settings.json:440-441`), com teste de deriva. Iniciais: margem 1,0 s,
  prazo 2,0 s. A margem é ≥ p99 do encerramento × 1,5; se não couber, encolhe o PRAZO, nunca a margem. Margem
  medida ≥ 3 s ⇒ a W2 PARA e vai ao Owner (LEDGER `:129-130`).
- **Aplicação**, com `restante = EXIT_DEADLINE_S − (monotonic() − âncora)`: `restante ≤ 0` ⇒ nenhuma tentativa na
  trava, e o spool fica no disco; senão, a trava espera `min(SPOOL_LOCK_TIMEOUT, restante)`, por parâmetro nomeado
  opcional de `drain_now` (sem ele, vale o comportamento de hoje). Obtida a trava, o prazo é reconferido antes da
  fase 2 (vencido, solta sem listar); as esperas por PID (`:1374`, `:2276`) ficam limitadas a `restante`, e o
  estouro segue os desvios já existentes. Não obter a trava ⇒ `DrainStats.exit_deadline_skip=True` (só em
  processo), `ok=True`, SEM o breadcrumb `drain canonical lock timeout`, com o portão STARVED avaliado (§4.3). A
  W0.5 mede a parte não preemptível (uma listagem, ≤ `K_MAX`, um append com `fsync`, as compactações).
- **Drain oportunista antes da decisão** (`audit_emit.py:2790-2791`): se a W0.5 medir «decisão → stdout» acima da
  margem, a mesma regra vale para ele, no pacote da W2 (regra pré-registrada).
- **Não é anômalo nem fere o ADR-186:** o corte atinge durabilidade POSTERIOR à decisão, garantida pela perna 3, e
  não verificação INCOMPLETA; o prazo protege a ENTREGA de uma decisão já tomada.
- **Controle S1:** guard sintético de IMPORT TARDIO na W0.5; sem calibração contra o harness REAL, S1 prova contra
  um MODELO. No CI, `-k deadline` e `-k anchor` com relógio e kernel falsos, sem tempo absoluto (rascunho `:362-371`).

### 4.3 Trava canônica presa vira sinal em ≤ 1 h (U2-B; MF-R2-W2-1)

A trava canônica presa vira sinal em ≤ **T = 1 h** (`STARVED_LOG_IDLE_S = 3600`), sem volume por saída. O salto da
§4.2 não pode regredir a MF-1 do AMEND-3: com a trava presa, os eventos ficam PRÉ-cadeia. Mecanismo de referência,
trocável por equivalente que preserve requisito e controles:
- **portão:** saída LENTA; tentativa real na trava, com espera > 0, terminada em `FileLockTimeout`; e UM `os.stat`
  de `_canonical_log_path()` com `agora − st_mtime > T` (log ausente não dispara);
- **taxa:** carimbo `audit-log.starved-stamp` em `_log_family_dir()`, modo 0600, `O_NOFOLLOW`, escrito só se ausente
  ou mais velho que T; corridas geram no máximo uma linha por saída concorrente;
- **texto:** `{ts} spool_writer: drain canonical lock STARVED (exit): canonical log idle > 3600s while exit drain timed out on the lock`;
- custo zero no caminho rápido; sem emissor depois de T, o G3 cobre os órfãos; controles `-k starved` (positivo com
  portador externo, taxa, mutante «sem portão» VERMELHO, quatro negativos): rascunho `:404-413`.

### 4.4 Journal vazio removido na origem, só pela compactação (U2-B)

Em `_journal_compact_drained` (`:2248-2301`), sob a trava do PRÓPRIO journal: reexamina a existência SOB a trava;
filtra como hoje; resultado vazio ⇒ `os.unlink(journal)` sob a trava, sem `.compact.tmp` (`FileNotFoundError` é
silencioso); resultado não vazio ⇒ caminho atual. A compactação é o ÚNICO produtor de journal com 0 byte, pois o
flush só cria o arquivo com conteúdo (`:947-949`, `:959-963`) [disco]. A remoção pelo dono na saída SAI do desenho.
O censo dos abridores vira teste (`-k openers`). A TRAVA do journal nunca é apagada. Controle `-k origin`, com dois
mutantes VERMELHOS: rascunho `:436-441`.

### 4.5 Travas: nenhum hook apaga `*.lock` (MF-W2-2)

**Nenhum hook faz `unlink` de `*.lock`**, de nenhum módulo e por nenhum motivo: o `FileLock` faz `flock` sem
comparar inode (`filelock.py:144`, `:149`). **T1 (padrão):** as travas ficam, e a W2.6 RECORRENTE limpa o estoque
(§5); com ≥ 100 mil travas, o `/ceo-boot` recomenda a W2.6 (limiar OPERACIONAL). **T2 (condicional):** re-checagem
de inode no `_lib/filelock.py` (kernel), em pacote PRÓPRIO, se a célula «~150 mil travas» da W0.5 (≥ 9 saídas
concorrentes com conteúdo) mostrar `exit_deadline_skip` > 0 ou p95 acima do orçamento, se a W2.6 rodar mais de 1×
por mês, ou em Linux de vida longa. Mesmo com a T2, apagar trava em hook volta a debate com o portador do VETO.
**T3 (relocação):** FORA.

### 4.6 GC dentro do hook: fora do pacote base

Sem produtor de journal vazio nem remoção de trava, o pacote base não leva GC no hook, e o Check `-k gc` sai. Se o
H1 pós-LAND passar do limiar, o GC de journal de PID morto volta em pacote PRÓPRIO (condições: rascunho `:462-467`).

### 4.7 Regra de versões mistas (MF-W2-4)

- **Invariante:** nenhum caminho de trava ou de journal muda; prova por teste dourado dos construtores
  (`-k golden_paths`; rascunho `:471-477`; `spool_writer.py:429-481` [disco]). Mudar esses caminhos exige transição
  explícita (dupla trava ou janela sem adquirentes).
- **LAND** com a sessão aberta; efeitos de convivência (§4.7, :481-485) declarados no material assinado — decisão do Owner, 02/10/2026; a W2.6 continua exigindo as sessões deste projeto fechadas há ≥ 10 min (D-19, plano `:2062`).
- **Convivência declarada** (rascunho `:481-485`; vale também para adopter via `upgrade.sh` com sessão aberta): o
  compactador velho grava `journal compact failed: FileNotFoundError` (ruído, não perda); processos velhos seguem
  sem caminho rápido, prazo e portão até sair; o compactador velho reescreve journal com 0 byte, e o novo o remove na
  compactação seguinte; nenhuma combinação cria dois donos para uma trava.
- **Adopters:** a W2 não limpa o estoque deles; o prazo protege a decisão; a limpeza é follow-up fora da 1.4.3.

### 4.8 Nomes: expressões regulares ancoradas

A W2.6, o `/ceo-boot`, os verificadores do F1 e o Check de sucesso usam o MESMO texto, byte a byte o do rascunho
`:494-500`:

```
RE_SPOOL_LOCK   = r"audit-spool\.([1-9][0-9]{0,9})\.jsonl\.lock"
RE_JOURNAL      = r"audit-pending\.([1-9][0-9]{0,9})\.journal"
RE_JOURNAL_LOCK = r"audit-pending\.([1-9][0-9]{0,9})\.journal\.lock"
RE_DRAINING     = r"audit-spool\.([1-9][0-9]{0,9})\.draining\.([0-9a-f]{8})"
RE_ACTIVE_SPOOL = r"audit-spool\.([1-9][0-9]{0,9})\.jsonl"
```

- Só `re.fullmatch` com `re.ASCII`; nunca `match`, `search`, `^…$` (o `$` aceita `\n` final) nem `\d`. PID ASCII,
  sem zero à esquerda, de 1 a 10 dígitos. Proibido reusar `_parse_spool_pid` (`:1248-1257`): o `int()` aceita `_`,
  espaços, `+` e dígitos Unicode. Journal agregado e trava de agregação NÃO casam (`:455-462`).
- O `audit-log.errors` tem dois carimbos: `AAAA-MM-DDTHH:MM:SSZ spool_writer: …` (`spool_writer.py:611-613`) e
  `[AAAA-MM-DDTHH:MM:SSZ] …` (`audit_log.py:1118-1124`), com 37.955 e 15 linhas às 20:57Z [medido: redator FD-16].
  As regex de linha casam os dois, ancoradas no início; o tempo é comparado como DATETIME UTC, nunca como texto.

### 4.9 O que nunca se apaga (nem em hook, nem na W2.6)

`.draining.*`, `.malformed.*`, `.quarantined.*`, `.test-origin.*`, `.corrupt-header.*` (`:581-582`), `.tmp.*`,
`*.compact.tmp`; spool ativo; journal com conteúdo e sua família; journal agregado e trava de agregação; a família
do log, inclusive `audit-log.starved-stamp`, chave, sal, sidecars e rotacionados; arquivos de outros módulos
(rascunho `:526-528`); não-arquivo comum ou `st_nlink > 1`; o que está fora do state dir; **em hook, todo `*.lock`.**

### 4.10 O que NÃO muda

Fases 2 a 5, ordem da cadeia HMAC, reconstrução do `prev_hmac`, `_drain_sha256`, `audit_hmac.py`, `canonical_json.py`
e `audit-verify-chain.py`; o caminho oportunista do AMEND-3, salvo a regra da §4.2; `drain_now(force=True)` sem
prazo; `CEO_AUDIT_SYNC_MODE=1`. Nenhuma ação nova em `_KNOWN_ACTIONS`; nenhum toque no `audit_emit.py`.

## §5 W2.6 — limpeza do estoque, endurecida e RECORRENTE (MF-W2-6)

- **Quando:** script fora do repositório, rodado pelo Owner, em simulação por padrão (`--apply` remove). A 1.ª
  execução roda depois do LAND do U2-B (D-5, plano `:2048`), com as sessões DESTE projeto fechadas há ≥ 10 min
  (D-19). Depois, sempre que o `/ceo-boot` acusar ≥ 100 mil travas; mais de 1× por mês é gatilho da T2. Ratificado
  pelo Owner (decisão 2, `debate/round-3/approved.md`).
- **Confinamento:** state dir pelo `_lib/runtime_paths.py` (`--state-dir`) + `/state`, nunca por slug à mão; recusa
  com `CEO_AUDIT_LOG_DIR` ou `CEO_AUDIT_LOG_PATH` (`spool_writer.py:265-266`, `:407-412`); diretório aberto com
  `O_RDONLY | O_DIRECTORY | O_NOFOLLOW` e recusado se for symlink, de outro dono ou com modo ≠ 0700; cada remoção
  é `os.unlink(nome, dir_fd=dfd)` depois de reexame (`S_ISREG`, 0 byte, `st_nlink == 1`, mesmo `(st_dev, st_ino)`
  da listagem, família ainda sem conteúdo).
- **Predicado** (tabela: rascunho `:566-576`): spool ativo ou `.draining.*` de PID VIVO, ou arquivo da família com
  mtime < 10 min ⇒ RECUSA a execução; APAGA só trava ou journal dos 3 padrões, arquivo comum, 0 byte,
  `st_nlink == 1`, PID morto, família sem conteúdo, mtime ≥ 10 min; PID vivo nas travas ou no journal ⇒ MANTÉM.
- **Prova:** contagem POR CÉLULA no LEDGER; manifesto de hash dos journals com conteúdo, antes e depois.

## §6 Critérios de sucesso

- **Barram o SIGN:** **S1**, entrega de decisão (célula da W0.5 com guard de import tardio, VERMELHO no HEAD e VERDE
  na cura; `-k deadline` e `-k anchor` verdes); **S2**, INV-NP por conjunto no estresse, cada mutante reprovando;
  **S3**, `verify_chain()` íntegro na cadeia composta; **S4**, controles da §4.3, inclusive o mutante; **S5**, G6 e
  G7 com controle positivo. `truly_lost` NÃO é critério.
- **Estresse W2.5** (rascunho `:610-632`): todos os gravadores em paralelo, com `kill -9` e reuso de PID; N ≥ 1.000
  elos, ≥ 100 `agent_spawn`, ≥ 100 lotes de drain, ≥ 50 transições ADJACENTES e ≥ 1 rotação; mutantes M-a..M-d.
- **Higiene:** **H1** (primário): `F` = PIDs mortos com journal de 0 byte na janela ÷ \|D\|, com D = os `pid` da
  era-spool do log com `wall_ns` nas últimas 24 h; \|D\| ≥ 200; **F ≤ 0,01**. Vermelho medido: F = 0,999 (\|D\| = 1.049,
  rascunho) e F = 0,9947 (\|D\| = 14.572, LEDGER `:138-143`). **H2:** ≤ 1.000 journals vazios após 24 h. **H3:** §4.5.
- **W0.5** pré-registrada (LEDGER `:80-136`): 2³ células, extras X1–X7 (rascunho `:663-679`, com 2 `claude -p` de
  calibração), 0 perdas em N com 3/N ≤ p̂/10 (p̂ = 0 ⇒ prova só estrutural, declarada); nada de tempo no CI.
- **Checks:** `.claude/hooks/tests/test_spool_state_amend4.py`, seletores `fast_path`, `flag`, `deadline`, `anchor`,
  `starved`, `origin`, `golden_paths`, `inode`, `openers` e `invariant`, cada um casando EXATAMENTE o conjunto
  declarado; Check de sucesso nos braços do rascunho `:703-715`, com o carimbo do LAND por `git log -1 --format=%cI`.

## §7 Pré-condição do SIGN: cura da condição 67 (MF-W2-1) — SATISFEITA

Até `65cd50d7`, `append_entry` lia a chave e o elo anterior e calculava o HMAC ANTES da trava
(`audit_log.py:1262-1278`, trava em `:1283`, no HEAD `48f03b3a`): a condição 67 da v1.4.0-rc.1. A cura landou
assinada em `65cd50d7`: `with FileLock` em `audit_log.py:1275`, `rotate_if_needed` em `:1277`, marcador do AMEND-2
em `:1280-1281`, chave, elo e HMAC em `:1286-1300` (`read_prev_hmac` em `:1290`), append e sidecar em `:1307-1336`
[disco]. Guardas de regressão: `test_two_writer_chain.py:298`, `:332`, `:477` e `:480`. O `CHANGELOG.md` do corte
da 1.4.3 aposenta a condição 67.

## §8 Reversão e gatilhos

**Reversão por PEÇA** — (a) auxiliar e caminho rápido, (b) prazo, (c) journal na origem, (d) portão STARVED.
Imediata: `CEO_AUDIT_SYNC_MODE=1`. Definitiva: `git revert` da peça em cerimônia canônica (`SUPERSEDED-BY-REVERT`).
Reverter (b) ou (d) reabre uma classe de segurança e exige decisão escrita do Owner; G1 e G3 só revertem (a) ou (c).

**Gatilhos** (instrumentos LIGADOS, cada um com controle positivo; tabela integral: rascunho `:758-768`):

| id | gatilho | controle positivo | ação |
|---|---|---|---|
| G1 | H1 > 0,01 ou H2 > 1.000 em 3 dias distintos e consecutivos | F > ε sintético; 1.001 journals | reverter (c) |
| G2 | `drain canonical lock timeout` datada depois do LAND e da convivência | teste 4; 37.715 linhas às 20:57Z | achar o chamador |
| G3 | `.draining.*` ou spool órfão com conteúdo com mais de 24 h | mtime de 25 h plantado | reverter (a) |
| G4 | decisão BLOCK descartada (W0.5 re-rodada a cada CC novo) | vermelho do HEAD; mutante | (b) só com decisão escrita |
| G5 | quebra de cadeia ATRIBUÍVEL à W2 (linha com `_drain_epoch`) | um byte alterado numa linha do drain | a peça; ADR-052 avisado |
| G6 | `record_id` com `commit` no journal e `wall_ns` ≥ LAND, ausente do log, dos rotacionados e dos spools | linha removida ⇒ 1; quarentena ou spool ⇒ 0 | investigar; ADR-052 |
| G7 | `would-log=` ou `append failed:` datada depois do LAND | 15 linhas reais às 20:57Z; trava > 2,5 s em teste | investigar a contenção |
| G8 | linha `STARVED (exit)` | `-k starved` | investigar o portador |

O G6 (`.claude/scripts/check-audit-real-loss.py`, só leitura, fora de hook) lê spools e quarentena, o log corrente e,
por último, os rotacionados, e reconfere numa 2.ª passada; é limite inferior. Os verificadores do F1 (fora do HEAD
`9a458f19`) rodam no V-block do LAND; o U2-D liga G6 e G7/STARVED no nightly, e até lá o `/ceo-boot` os roda.
**Herdados:** `truly_lost` MORTO (só `spool_writer.py:136` e `:2562`); a taxa de quebra de 30 dias (≈ 0,9% com a
condição 67 [plano]) vira G5; a contenção que derruba chamada de ferramenta fica como G2 + G4 + G8.

## §9 Observabilidade sem tocar o `audit_emit.py`

Nenhum evento por arquivo e nenhuma ação nova. O check advisory do `/ceo-boot` (`ceo-boot.py`, pacote da L2; na
skill, nunca em hook) mostra travas por NOME, journals vazios (`stat` limitado a 2.000), idade do `.draining.*` mais
velho, taxa de órfãos com conteúdo, `STARVED (exit)` e G7 datados, e grava ≤ 1 linha quando um gatilho dispara. Os
detectores por total (`ceo-diagnose.py:371-373`, `status.py:290`) seguem saturados até a rotação (`H-03`).

## §10 Opções consideradas

Opções A–N: rascunho `:819-837`. Adotada: H (`flush` antes da drenagem). Condicional: D (a T2). Adiada: C.

## §11 Consequências e resíduos declarados

**Positivas:** a decisão BLOCK sai antes de qualquer espera; a trava canônica fica menos disputada, inclusive para o
`agent_spawn`; journals vazios param de acumular; a trava presa vira sinal; a perda real passa a ser medida.
**Negativas:** sob T1, as travas crescem e a W2.6 vira manutenção recorrente; o salto aumenta a residência
PRÉ-cadeia; entram um arquivo na família do log, um campo em `DrainStats` e um parâmetro em `drain_now`. **Neutras:**
sem contenção, o caminho com conteúdo fica idêntico. **Resíduos** (vão para o material assinado; rascunho
`:865-886`): (1) âncora pelo import quando o kernel falha, e o grok; (2) sem calibração, S1 é prova contra um
modelo; (3) timeout de adopter abaixo de prazo + margem; (4) parte não preemptível proporcional às travas; (5)
journal vazio por falha de `write` depois do `O_CREAT`; (6) ~214 journals com conteúdo só forense; (7) perda do
`agent_spawn` reduzida, não eliminada; (8) G6 é limite inferior; (9) o STARVED exige uma saída com conteúdo depois
de T; (10) recusa falsa da W2.6 por PID reusado; (11) janela TOCTOU da W2.6; (12) mesmo UID (`CLAUDE.md` §5); (13)
testes com hook em subprocesso drenam no pai ou fixam `CEO_AUDIT_SYNC_MODE=1` no filho.

## §12 Raio de explosão, pacotes e anti-churn

U2-A = (a); U2-B = (c) e (d); U2-C = (b), a cura de SEGURANÇA; os três tocam `.claude/hooks/_lib/spool_writer.py`
(canônico, NÃO kernel) e `.claude/hooks/tests/test_spool_state_amend4.py`. U2-D = este ADR ACCEPTED, o `## Amended-by`
do ADR-055, o leque de ADR e a fiação do `nightly-hygiene.js`. Livres: F1, F2, M0 e o script da W2.6. Fora:
`audit_emit.py`, `SessionStart.py`, `audit_hmac.py`, `canonical_json.py`, `audit-verify-chain.py`, `_python-hook.sh`
e os guards; T2 condicional no `_lib/filelock.py` (kernel). Reversibilidade ALTA em (a) e (c). Regra 10×: prazo,
portão e `flush` não dependem do volume; o estoque de travas escala sob T1, visível pelo H3. Anti-churn
(ADR-115/ADR-124): sem ABI de spool, layout, ação de auditoria ou variável de ambiente novos.

## §13 Decisões do Owner

Decisão 1 (vaga da W2.0): superada em `65cd50d7`. Decisão 2 (W2.6): ratificada em 2026-10-02 e refinada pela D-5 e
pela D-19. Ciência: 2 `claude -p` na calibração; estoque dos adopters fora da 1.4.3; reverter (b) ou (d) exige
decisão escrita do Owner.

## §14–§16 Fonte integral

Perguntas da rodada 2: rascunho `:934-944`. Rastreabilidade dos must-fix: `:948-1003`. Evidência lida: `:1007-1036`.
