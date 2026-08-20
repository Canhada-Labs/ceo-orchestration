# PLAN-182 W0 — Anexo de medição (S316, 2026-08-20)

> Saída BRUTA das unidades de medição read-only, executadas por
> fan-out Workflow `wf_87d4181b-bba` (4 agentes, ADR-136 confinement,
> retornos estruturados). Anexado sob o carve-out (b) da W0.


## US6 — atribuibilidade

### summary

Sobre TODOS os 20 arquivos audit-log*.jsonl (19 rotacionados + vivo; 293.672–293.709 linhas, crescendo sob sessão concorrente): 45,3% dos eventos têm project VAZIO e 3,3% AUSENTE. Veredito de junção: PARCIAL/NÃO-universal — 53,4% dos eventos juntam a um projeto (51,4% direto pelo campo project; 2,0% indireto via session_id, que quando presente nunca é ambíguo: 0 de 120 sessões cruzam rótulo); 46,6% (136.877 eventos) não têm NENHUMA rota — sem project, sem session_id e sem repo_path_hash. A janela S315 foi reconstruída EXATAMENTE como o prefixo [0:15355] de audit-log-2026-08-17.jsonl (match perfeito: 10.254/2.136/1.706/1.053+7, e explica os 199 faltantes do total publicado = campo ABSENT). Delta desde S315: 1.530 eventos novos, dos quais 226 NÃO-atribuíveis (163 EMPTY + 63 ABSENT) — ~14,8% do fluxo novo continua nascendo sem atribuição.

### evidence

INPUTS (janela e arquivos lidos — dir $HOME/.claude/projects/ceo-orchestration/, leitura 2026-08-20 ~14:47–14:55 local / 17:47–17:55Z; log vivo cresceu 293.627→293.709 linhas entre scans, sessão concorrente escrevendo — esperado, cf. lição feedback-live-audit-isolation):
20 arquivos, nome / linhas / janela ts:
  audit-log-2026-07-5.jsonl  16114  2026-07-11T00:44Z..2026-07-20T23:57Z
  audit-log-2026-08.jsonl    15030  2026-07-20..2026-08-02 | -08-1 17692 | -08-2 18093 | -08-3 17763 | -08-4 17613 | -08-5 16931 | -08-6 16268 | -08-7 15898 | -08-8 15995 | -08-9 14564 | -08-10 12666 | -08-11 14002 | -08-12 13888 | -08-13 13523 | -08-14 13235 | -08-15 13420 | -08-16 14128
  audit-log-2026-08-17.jsonl 16223  2026-08-19T21:07Z..2026-08-20T16:38Z (rotacionado hoje 13:38 local)
  audit-log.jsonl (vivo)     626→662 no ato das leituras, 2026-08-20T16:38Z..17:47Z

(1) HISTOGRAMA project (comando: python3 inline, stdlib; label = basename quando contém '/'):
  for f in glob(base+"/audit-log*.jsonl"): for line: d=json.loads(line); hist[basename(d.get("project"))]+=1
  → 133.092 <EMPTY>; 62.950 arbitrage-monitor; 52.476 ceo-orchestration; 34.040 42ledger-core; 9.756 <ABSENT>; 1.296 foxbit-bot-arbitrage; 9 proj; 6 t4-falsegreen; 5 grok-livefire; 5×6+4+3+2 tmp* efêmeros; 3 e2e_proj. Total 293.672 no scan do histograma.

(2) session_id: filled 154.539 / empty 134.027 / absent 5.106. Correlação forte: dos 142.848 eventos sem project, 136.877 também não têm session_id.

(3) VEREDITO — comando que o produz (executado, saída literal abaixo):
  python3 - <<'EOF'
  # passo 1: sess2proj[s] = {labels} para eventos com session_id e project preenchidos
  # passo 2: classifica CADA evento: project preenchido -> direta; senão session_id em sess2proj com 1 rótulo -> indireta; senão órfão/irrecuperável
  EOF
  Saída: direct 150.860 (51,4%) | irrecuperável (sem project E sem session_id) 136.877 (46,6%) | indireta via session_id→1 projeto 5.849 (2,0%) | órfão (session_id nunca visto com projeto) 123 (0,0%).
  VEREDITO: existe chave de junção evento→projeto: NÃO como propriedade universal — SIM para 156.709/293.709 (53,4%), NÃO para 137.000 (46,6%). Quando session_id existe, ele É chave válida: 0 de 120 sessões mapeiam para >1 rótulo de projeto. Rota secundária inexistente para os irrecuperáveis: nesses 136.877, repo_path_hash presente em 0 (só spool_uuid/pid/record_id em 136.857 — nenhum é chave de projeto); os 3 repo_path_hash existentes no log mapeiam 1:1 sem ambiguidade (ceo-orchestration, arbitrage-monitor, 42ledger-core).

(4) DELTA S315 — reconstrução da janela: histograma do prefixo [0:15355] de audit-log-2026-08-17.jsonl = 10.254 <EMPTY> + 2.136 arbitrage-monitor + 1.706 42ledger-core + 1.053 ceo-orchestration(path) + 7 ceo-orchestration(literal, sem path) + 199 <ABSENT> — match EXATO com a medição S315 (e resolve as duas pontas soltas dela: o "+7" = rótulo literal sem path; os 199 que faltavam para fechar 15.355 = campo project AUSENTE, não contados no breakdown publicado). Logo tenant-a=arbitrage-monitor, tenant-b=42ledger-core.
  Delta = -17[15355:16223] (868 linhas) + vivo (662 no ato) = 1.530 eventos novos: 743 ceo-orchestration, 283 42ledger-core, 278 arbitrage-monitor, 163 <EMPTY>, 63 <ABSENT>. session_id no delta: filled 1.345 / empty 167 / absent 18.
  NÃO-ATRIBUÍVEIS NOVOS DESDE S315: 226 (163 EMPTY + 63 ABSENT) — 14,8% do fluxo novo; e a mistura entre tenants continua ativa no delta (561 eventos estrangeiros novos em <1 dia).

### table

| # | Medição | Valor | Observação |
|---|---------|-------|------------|
| 1a | project = `<EMPTY>` | 133.092 (45,3%) | maior classe do log |
| 1b | project = arbitrage-monitor | 62.950 (21,4%) | tenant estrangeiro (= "tenant-a" da S315) |
| 1c | project = ceo-orchestration | 52.476 (17,9%) | este repo (inclui 7 c/ rótulo literal sem path) |
| 1d | project = 42ledger-core | 34.040 (11,6%) | tenant estrangeiro (= "tenant-b" da S315) |
| 1e | project = `<ABSENT>` | 9.756 (3,3%) | schemas sem o campo (p.ex. keyset de 4.436 eventos c/ atlas_technique) |
| 1f | project = foxbit-bot-arbitrage | 1.296 | 3º tenant estrangeiro, ausente do censo S315 |
| 1g | project = outros (proj, t4-falsegreen, grok-livefire, e2e_proj, 9× tmp*) | 62 | resíduo de testes/e2e |
| 2a | session_id preenchido | 154.539 (52,6%) | |
| 2b | session_id vazio | 134.027 (45,6%) | co-ocorre com project vazio (136.877 sem ambos) |
| 2c | session_id ausente | 5.106 (1,7%) | |
| 3 | **Veredito junção evento→projeto** | **NÃO universal: SIM p/ 53,4% (156.709), NÃO p/ 46,6% (137.000)** | direta 51,4% + indireta via session_id 2,0%; session_id quando existe é chave sem ambiguidade (0/120 sessões cruzam projeto); irrecuperáveis não têm repo_path_hash (0/136.877) |
| 4a | Janela S315 reconstruída | prefixo [0:15355] de audit-log-2026-08-17.jsonl | match EXATO (10.254/2.136/1.706/1.053+7/199-ABSENT) |
| 4b | Eventos novos desde S315 | 1.530 | 743 este repo, 283+278 tenants, no ato da leitura (vivo=662) |
| 4c | **NÃO-atribuíveis novos desde S315** | **226** (163 EMPTY + 63 ABSENT) | ~14,8% do fluxo novo; classe segue ATIVA |

### blockers

- Nenhum bloqueio. Duas ressalvas de medição: (a) o log vivo está sob escrita concorrente (293.627→293.709 linhas entre scans) — todos os números são no-ato-da-leitura, com o instante impresso; o delta 4b/4c cresce em tempo real. (b) O total publicado da S315 (15.355) não fechava com o breakdown dela (soma 15.156): a reconstrução mostra que 199 eventos <ABSENT> e a divisão 1.053(path)+7(literal) não estavam discriminados — o breakdown S315 estava incompleto, não errado. Nenhuma instrução embutida encontrada no conteúdo lido.

## US5 — inventário do diretório

### summary

Inventário completo do runtime state dir `$HOME/.claude/projects/ceo-orchestration/`: 46 entradas de topo (48 hardlinks − `.`/`..`), todas mapeadas a dono lógico por leitura dos módulos construtores de caminho (7 em `_lib/`, 23 em `.claude/scripts/`). Achados-chave: (1) TODAS as famílias resolvem pelo literal `ceo-orchestration` — a semântica real é por-$HOME, não por-projeto (o defeito do PLAN-182); só `state/` (`CEO_STATE_ROOT`/`CEO_PROJECT_NAME`), `memory-shared/` (basename de `$CLAUDE_PROJECT_DIR`) e a família audit (`CEO_AUDIT_LOG_DIR`) têm override de env, todos com fallback no literal. (2) Modos INCONSISTENTES: 5 dos 19 logs rotacionados estão 0644 (2026-08-1, -9, -12, -13, -14) vs 0600 dos demais; `audit-log.errors` 0644; `cache/` e `tool-lifecycle/` 0755 vs 0700 dos diretórios irmãos; `speculative-ledger.json` e `state-archive-*.tar.gz` 0644. (3) `speculative-ledger.json` é ÓRFÃO — nenhum escritor vivo no tree (greps por nome e por campos `draft_accepted`/`cheap_cost_usd` = zero fora de docs de plano; pickaxe no histórico = zero), última escrita 2026-06-04. (4) DOIS locks coexistem por convenções distintas: `audit-log.lock` (audit_emit.py:2312) e `audit-log.jsonl.lock` (convenção filelock.py, usada por SessionEnd/Stop/backup-audit). (5) `state/` tem 133.124 arquivos e link count 65535 no dir. (6) 6 archives de `audit-log.errors.*` e 3 `.bak` phaseC são artefatos manuais/one-shot de operador, sem escritor em código.

### evidence

INPUTS de toda medição impressos abaixo (comando → saída relevante).

[1] Listagem de topo — `ls -la "$HOME/.claude/projects/ceo-orchestration/"`:
48 links (46 entradas reais). Dir raiz: drwx------ (0700). Saída completa usada na tabela; destaques:
  -rw------- .salt (32 B, Apr 24)
  -rw------- audit-key (32 B, Apr 18)
  -rw------- audit-log.jsonl (392.454 B, hoje)
  19 rotacionados audit-log-*.jsonl (~10,49 MB cada; threshold 10 MiB confirmado no código)
  drwx------ state (link count 65535, 4.224.672 B de dir entries)
  drwxr-xr-x cache, drwxr-xr-x tool-lifecycle (0755 — irmãos são 0700)

[2] Modos — `stat -f "%Sp %N" .../* .../.*`:
0644 (fora do padrão 0600): audit-log-2026-08-1.jsonl, -9, -12, -13, -14; audit-log.errors + seus 6 archives; cache/; speculative-ledger.json; state-archive-S293-*.tar.gz; tool-lifecycle/. Todo o resto 0600/0700.

[3] Contagem state/ — `find "$D/state" | wc -l` = 133127; `find "$D/state" -type f | wc -l` = 133124 (3 dirs).

[4] Conteúdo dos subdirs (ls -la): advisory-dampen/ = {_nosession.json 19.818 B, _nosession.json.lock}; fact-gate/ = {_nosession.json 9.072 B, .lock}; memory-shared/ = {index.jsonl 95 B, index.jsonl.lock, patterns/}; cache/ = {ceo-boot-digest.json}; tool-lifecycle/ = 3 pares <session-uuid>.json + .lock (sessões de hoje, incl. esta: baf2bbd3-...).

[5] Construtores de caminho — `grep -rln 'projects/ceo-orchestration' .claude/hooks/_lib/` = 7 módulos: adapters/live/claude.py, advisory_dampen.py, audit_hmac.py, estimation/pipeline.py, output_scan_dedup.py, state_store.py, test_isolation.py. Em `.claude/scripts/` = 23 arquivos (audit-log-retain.py, audit-query.py, audit-telemetry.py, audit-tokens.py, budget-summary.py, cc-analytics-pull.py, ceo-cost.py, ceo-diagnose.py, ceo-info.py, distill-lessons.py, hook-profiler.py, local/{pair-rail-latency,verify-staging-manifest,wave-readonly-monitor}.py, otel-local-sink.py, skill-budget-generator.py, statusline-ceo.py, swarm/loop_runner.py, verify-persona-coverage.py, verify-sprint3-invariants.sh, +2 fixtures red-team, +1 teste) — scripts são majoritariamente LEITORES.

[6] Donos por artefato (file:line):
  .salt → _lib/injection_salt.py (_SALT_FILENAME=".salt" L55, modo 0600 L57, gera os.urandom(32) L109; docstring: espelha audit_emit._audit_dir, ADR-079). Leitores: replay_redact.py, scripts/replay/replay-session.py.
  audit-key → _lib/audit_hmac.py (KEY_FILENAME L81, key_path() L185-190 com override CEO_AUDIT_KEY_PATH, get_or_create_key() L308; checagens anti-symlink/ownership L242-303). Leitor: scripts/audit-verify-chain.py.
  audit-log.jsonl → DOIS caminhos de escrita: hooks/audit_log.py::append_entry + _lib/audit_emit.py::_write_event (docstring audit_rotation.py L1-16 nomeia ambos).
  Rotacionados audit-log-YYYY-MM[-N].jsonl → _lib/audit_rotation.py::rotate_if_needed L47-100: `base = log_path.parent / f"{stem}-{month_slug}.jsonl"`, colisão vira `-{counter}` — confirma que -1..-17 são CONTADORES DE COLISÃO no mês, não dias. Threshold 10 MiB, os.replace, chamado sob FileLock pelos dois caminhos de escrita.
  audit-log.chain-length / .last-hmac → _lib/audit_hmac.py sidecars (last_hmac_path() L196; reset_chain_on_rotation limpa ambos, docstring audit_rotation L28-32). Resolução de dir L153-182: CEO_AUDIT_LOG_DIR → CEO_AUDIT_LOG_PATH parent → CEO_PROJECT_STATE_DIR → literal $HOME/.../ceo-orchestration.
  audit-log.rotation-manifest.json → _lib/audit_hmac.py L103 (ROTATION_MANIFEST_FILENAME), L581-582 (path). Leitores: audit-verify-chain.py, audit-log-retain.py.
  audit-log.lock → _lib/audit_emit.py:2312 `return _audit_dir() / "audit-log.lock"` (lock do caminho de emissão; também audit_log.py, spool_writer.py, check_precompact_continuity.py).
  audit-log.jsonl.lock → convenção _lib/filelock.py (docstring L27, L108: "Caller convention: audit-log.jsonl.lock"); usuários: hooks/SessionEnd.py, hooks/Stop.py, scripts/backup-audit.py.
  audit-log.errors → _lib/audit_emit.py:2319 (path) + _breadcrumb() L2327 — sink fail-open usado por ≥12 módulos (SessionStart.py, check_budget.py, check_pair_rail.py, metrics.py, spool_writer.py, embeddings.py, mcp_routing.py, ...).
  audit-log.errors.{6 archives} e {3} *.phaseC-20260525-213326.bak → grep por esses sufixos em hooks+scripts = ZERO escritores; nomes carimbados com sessão/data (S180/S213/S239/S250/S293, phaseC 2026-05-25) = renames manuais de triagem do operador.
  state/ → _lib/state_store.py::_state_root L114-127: CEO_STATE_ROOT → `$HOME/.claude/projects/${CEO_PROJECT_NAME:-ceo-orchestration}/state`; também _lib/output_scan_dedup.py L152-161 escreve aí.
  memory-shared/ → _lib/memory_shared.py::_storage_root L90-96 (override CEO_MEMORY_SHARED_PATH) + _project_slug L80-87: basename de $CLAUDE_PROJECT_DIR, fallback literal. audit_emit.py também referencia (eventos pattern_stored).
  advisory-dampen/ → _lib/advisory_dampen.py (_STATE_SUBDIR L99, _state_base_dir L158-166 → literal). Arquivo `_nosession.json` = fallback sanitizado sem session_id.
  fact-gate/ → hooks/check_bash_safety.py L1292-1963 (PLAN-154.F6/ADR-160): _FACT_GATE_STATE_SUBDIR L1361, `<audit_dir>/fact-gate/<sanitized session>.json` L1354; base compartilhada com advisory_dampen.py.
  tool-lifecycle/ → _lib/tool_lifecycle.py::_record_path L329-332 `<audit_dir>/tool-lifecycle/<session_id>.json`; _audit_dir L298-309 (CEO_AUDIT_LOG_DIR → literal). Leitores: profile-opus-4-7.py, distill-lessons.py.
  cache/ → scripts/ceo-boot.py (único hit de 'ceo-boot-digest'); conteúdo confirmado: {"cache_key":..., "gate_pass": false, "checks_total": 15,...}.
  speculative-ledger.json → ÓRFÃO. Greps: 'speculative-ledger' em código = só docs do PLAN-182; campos do conteúdo real ({"task_id":"task-3","cheap_tokens":0,...,"draft_accepted":true,"stub":true}) → grep 'draft_accepted|cheap_tokens|cheap_cost_usd' em *.py = zero; `git log --all -S 'draft_accepted' --diff-filter=D` = zero. Última escrita: timestamp 1780604752 ≈ 2026-06-04 (bate com mtime Jun 4).
  state-archive-S293-20260804T190750Z.tar.gz → grep 'state-archive' em hooks+scripts+histórico = zero; nome carimbado S293 (2026-08-04) = archive manual do operador (memória S293 registra a triagem).

### table

| # | Artefato (topo) | Tipo | Modo | Dono lógico (escritor) | Compartilhamento |
|---|---|---|---|---|---|
| 1 | `.salt` | arquivo (32 B) | `-rw-------` | `_lib/injection_salt.py` (ADR-079; gera+0600) | **por-$HOME de fato** (path literal; 1 salt p/ todos os projetos ⇒ `prompt_sha256` correlaciona entre tenants) |
| 2 | `audit-key` | arquivo (32 B) | `-rw-------` | `_lib/audit_hmac.py::get_or_create_key` (L308; override `CEO_AUDIT_KEY_PATH`) | **por-$HOME de fato** (1 chave HMAC compartilhada entre projetos — defeito central do PLAN-182) |
| 3 | `audit-log.jsonl` | arquivo | `-rw-------` | `hooks/audit_log.py::append_entry` + `_lib/audit_emit.py::_write_event` (2 caminhos) | **MISTO medido** — contém eventos de 2 projetos estrangeiros (2.136+1.706; CLAUDE.md S315) |
| 4–22 | `audit-log-2026-07-5.jsonl`, `audit-log-2026-08.jsonl`, `audit-log-2026-08-{1..17}.jsonl` (19 arquivos, ~10,49 MB cada) | arquivo | 14× `-rw-------`; **5× `-rw-r--r--`** (-1, -9, -12, -13, -14) | `_lib/audit_rotation.py::rotate_if_needed` (L47-100; sufixo -N = contador de colisão no mês, não dia) | mesmo MISTO do log vivo (herdam o conteúdo na rotação) |
| 23 | `audit-log.chain-length` | arquivo (3 B) | `-rw-------` | `_lib/audit_hmac.py` (sidecar; reset na rotação) | por-$HOME (co-locado com o log via `_audit_dir_from_env` L153-182) |
| 24 | `audit-log.last-hmac` | arquivo (64 B) | `-rw-------` | `_lib/audit_hmac.py::last_hmac_path` (L196) | por-$HOME (idem) |
| 25 | `audit-log.rotation-manifest.json` | arquivo (138 B) | `-rw-------` | `_lib/audit_hmac.py` (L103, L581-582); leitores: `audit-verify-chain.py`, `audit-log-retain.py` | por-$HOME |
| 26 | `audit-log.lock` | arquivo (0 B) | `-rw-------` | `_lib/audit_emit.py:2312` (lock do caminho de emissão; + `audit_log.py`, `spool_writer.py`) | por-$HOME (serializa escritores de TODOS os projetos) |
| 27 | `audit-log.jsonl.lock` | arquivo (0 B) | `-rw-------` | convenção `_lib/filelock.py` (L27/L108); usuários: `SessionEnd.py`, `Stop.py`, `scripts/backup-audit.py` | por-$HOME — **2º lock coexistente por convenção distinta** |
| 28 | `audit-log.errors` | arquivo (90 KB) | `-rw-r--r--` | `_lib/audit_emit.py::_breadcrumb` (L2319/2327) — sink fail-open de ≥12 módulos | por-$HOME (breadcrumbs de qualquer projeto) |
| 29–34 | `audit-log.errors.{archived-2026-05-28-S180, S213-triaged-stale…, archive-20260616-s239, S250-triaged-stale…, archived-2026-07-10, S293-triaged…}` + `audit-log.errors-phaseC-archived-20260525…` (na verdade 7 arquivos: 6 `errors.*` + 1 `errors-phaseC…`) | arquivo | `-rw-r--r--` | **operador (manual)** — renames de triagem S180/S213/S239/S250/S293; zero escritores em código | por-$HOME (snapshots do sink) |
| 35–37 | `audit-log.{chain-length,last-hmac,rotation-manifest.json}.phaseC-20260525-213326.bak` (3 arquivos) | arquivo | `-rw-------` | **migração one-shot Phase C (2026-05-25)** — zero escritores vivos | por-$HOME (backups congelados) |
| 38 | `state/` | dir (133.124 arquivos; link count 65535) | `drwx------` | `_lib/state_store.py::_state_root` (L114-127) + `_lib/output_scan_dedup.py` (L152-161) | **misto-por-env**: `CEO_STATE_ROOT`/`CEO_PROJECT_NAME` honrados; default literal ⇒ por-$HOME |
| 39 | `state-archive-S293-20260804T190750Z.tar.gz` | arquivo (12,5 MB) | `-rw-r--r--` | **operador (manual, S293)** — zero escritores em código/histórico | snapshot congelado |
| 40 | `memory-shared/` | dir (index.jsonl + lock + patterns/) | `drwx------` | `_lib/memory_shared.py::_storage_root` (L90-96; SPEC/v1) | **misto**: slug = basename de `$CLAUDE_PROJECT_DIR` (por-projeto-por-basename quando env presente); fallback literal ⇒ por-$HOME; colisão entre projetos homônimos |
| 41 | `advisory-dampen/` | dir (`_nosession.json` + lock) | `drwx------` | `_lib/advisory_dampen.py` (L99, L158-166) | por-$HOME no dir; arquivos POR-SESSÃO (`_nosession` = fallback sem session_id) |
| 42 | `fact-gate/` | dir (`_nosession.json` + lock) | `drwx------` | `hooks/check_bash_safety.py` (PLAN-154.F6/ADR-160; L1354, L1361) | por-$HOME no dir; arquivos POR-SESSÃO |
| 43 | `tool-lifecycle/` | dir (3× `<session-uuid>.json` + locks) | **`drwxr-xr-x`** | `_lib/tool_lifecycle.py::_record_path` (L329-332); leitores: `profile-opus-4-7.py`, `distill-lessons.py` | por-$HOME no dir; arquivos POR-SESSÃO |
| 44 | `cache/` | dir (`ceo-boot-digest.json`) | **`drwxr-xr-x`** | `scripts/ceo-boot.py` (digest de boot) | por-$HOME |
| 45 | `speculative-ledger.json` | arquivo (1.142 B) | `-rw-r--r--` | **ÓRFÃO** — nenhum escritor vivo nem no histórico (pickaxe `draft_accepted` = 0); última escrita 2026-06-04 | morto (candidato a remoção no PLAN-182) |

Nota de contagem: 46 entradas de topo = itens 1–3 (3) + 19 logs rotacionados + 24 demais; a linha 29–34 cobre 7 arquivos e a 35–37 cobre 3, batendo com o `ls` (48 hardlinks − `.`/`..`).

### blockers

- Nenhum bloqueio de execução. Anomalias a registrar (não instruções embutidas — nada de prompt-injection encontrado no conteúdo lido): (1) speculative-ledger.json sem escritor vivo — não pude determinar o módulo de origem nem via git pickaxe; classificado ÓRFÃO por evidência negativa (inputs impressos no evidence). (2) Modos inconsistentes na MESMA família: 5/19 logs rotacionados 0644 vs 0600 — sugere que algum caminho de rotação/escrita não aplica chmod; não investiguei QUAL processo criou os 0644 (exigiria correlação com histórico de sessões). (3) state/ com link count 65535 no diretório (limite de campo do HFS+/APFS stat) e 133k arquivos — inventário interno ficou fora do escopo (a tarefa pediu só contagem). (4) audit-log.lock vs audit-log.jsonl.lock: duas convenções de lock vivas para a mesma família — escritores via audit_emit e escritores via filelock-convention NÃO se serializam entre si; relevante para o PLAN-182 mas não verifiquei janela de corrida real.

## US7 — resolvedores

### summary

Há 4 famílias de resolvedores $HOME/.claude/projects/* + 1 convenção repo-local, e elas NÃO concordam nem internamente. (A) audit_emit._audit_dir() [literal `ceo-orchestration`, 129 importadores não-teste] é o WRITER dominante e vence hoje para todo o plano de auditoria (log de 475KB + journals + chave HMAC vivem lá — provado on-disk). (B) state_store._state_root() [CEO_STATE_ROOT → CEO_PROJECT_NAME default literal] é o único resolvedor com nome de projeto parametrizado — o candidato natural a virar o resolvedor compartilhado da W1. (C) a cadeia 4-step dos CLIs existe em 6 CÓPIAS divergentes: ceo-cost/token-estimator (gate frouxo `parent.is_dir()`) e ceo-info (SEM gate) mis-resolvem para o slug-dir nativo (onde NUNCA houve audit-log) sempre que CLAUDE_PROJECT_DIR está setado — hoje só 'funcionam' porque o operador roda sem esse env; audit-log-retain ainda INVERTE a ordem DIR>PATH. (D) a família slug-nativo tem 3 grafias: `-Users-…` (correta: SessionEnd, ceo-info memory/transcripts, ceo-boot, budget-summary, cc-native-usage-pull), `--Users-…` (BUG de check_anti_ceo_overhead:213 — dir duplo-traço existe e recebe escrita HOJE) e `Users-…` sem traço (lessons.py/cost_envelope — zero dirs on-disk, nunca exercitada). (E) repo-local `.claude/state/audit-log.jsonl`: writer só federation (audit_event_push:234), reader check_skill_bootstrap_post:129 sem env override; arquivo NÃO existe neste repo — o reader cai no literal. VEREDITO por família de consumidor: plano de auditoria/estado ⇒ literal vence (W1 deve fazer readers DELEGAREM ao resolvedor do writer — precedente já shipado: check_agent_spawn._audit_log_path PLAN-105 delega a audit_emit._log_path); memória/transcripts ⇒ slug nativo `-<abs-path>` vence (o harness decide, não nós); CLIs ⇒ colapsar a cadeia 4-step em delegação, não manter; federation ⇒ manter repo-local como lane isolada OU unificar deliberadamente — qualquer W1 que invente caminho novo sem migrar writer+readers atomicamente cria a TERCEIRA convenção viva. CLAUDE_PROJECT_DIR_NATIVE (ADR-001): confirmado ZERO consumidores em código (.py/.sh/.json) — só docs (CLAUDE.md, ADR-001, material do PLAN-182).

### evidence

## INPUTS de todas as medições
Env do shell de medição (impresso antes de cada corrida): CLAUDE_PROJECT_DIR=UNSET, CEO_AUDIT_LOG_DIR=UNSET, CEO_AUDIT_LOG_PATH=UNSET, CEO_STATE_ROOT=UNSET, CEO_PROJECT_NAME=UNSET, HOME=/Users/joaocanhada. Para a simulação de resolução, CLAUDE_PROJECT_DIR foi setado no subprocesso para /Users/joaocanhada/canhada-labs/ceo-orchestration (o valor que os hooks recebem via settings.json). Repo em /Users/joaocanhada/canhada-labs/ceo-orchestration, branch main.

## 1) Resolvedores localizados (leitura direta do código)
- A. `.claude/hooks/_lib/audit_emit.py:2292-2298` `_audit_dir()`: CEO_AUDIT_LOG_DIR → `$HOME/.claude/projects/ceo-orchestration` (literal). `_log_path()` :2301-2305 (CEO_AUDIT_LOG_PATH), `_lock_path()` :2308-2312 (CEO_AUDIT_LOG_LOCK), `_errors_path()` :2315-2319 (CEO_AUDIT_LOG_ERR). Sem cache (recalculado por chamada). Mirrors byte-identical declarados: `.claude/hooks/audit_log.py:284-305` `audit_paths()` (hook standalone PostToolUse, settings.json:356; cópia inline, flock via _lib.filelock — audit_log.py:116); `.claude/hooks/_lib/spool_writer.py:174-` `_project_dir_from_env()` ("BYTE-IDENTICAL to audit_emit._audit_dir", COM cache single-slot, :145-158); `.claude/hooks/_lib/audit_hmac.py:155-183` (variante com 4 envs: CEO_AUDIT_LOG_DIR → CEO_AUDIT_LOG_PATH.parent → CEO_PROJECT_STATE_DIR → literal; docstring registra o split S168 que motivou a ordem).
- B. `.claude/hooks/_lib/state_store.py:114-126` `_state_root()`: CEO_STATE_ROOT → `$HOME/.claude/projects/${CEO_PROJECT_NAME:-ceo-orchestration}/state`. Infra: SQLite WAL + synchronous=NORMAL (:230-232), validação de store/plan, audit fail-open.
- C. Cadeia 4-step DUPLICADA em 6 CLIs (grep exato por `lstrip("/").replace("/", "-")`, não-teste): ceo-cost.py:98-136, ceo-info.py:108-122 (+_memory_dir :129-140, _transcripts_dir :668-684), audit-telemetry.py:~72-100, ceo-diagnose.py:110-150, audit-log-retain.py:110-145, token-estimator.py:~585-589. Ordem canônica: CEO_AUDIT_LOG_PATH → CEO_AUDIT_LOG_DIR → slug de CLAUDE_PROJECT_DIR → literal. DIVERGÊNCIAS INTERNAS (linha citada): gate do passo 3 = `scoped.exists() or scoped.parent.is_dir()` em ceo-cost:130 e token-estimator:587 (FROUXO); SEM gate em ceo-info:119 (retorno incondicional); `scoped.is_file()` em audit-telemetry:97 e ceo-diagnose (estrito, correto); `scoped.is_dir()` em audit-log-retain:135, que ainda INVERTE a precedência (CEO_AUDIT_LOG_DIR ANTES de CEO_AUDIT_LOG_PATH, :117-127) vs. todos os irmãos.
- D. Família slug-nativo (derivações independentes): SessionEnd.py:89-90 (`f"-{slug}"` com lstrip — produz `-Users-…` correto); check_anti_ceo_overhead.py:211-214 (`"-" + proj_dir.replace("/", "-")` → `--Users-…` DUPLO TRAÇO, mkdir + .lock por janela); check_tier_policy_misrouting_24h.py:78-100 (3-step próprio: CLAUDE_PROJECT_DIR/audit-log.jsonl direto → basename literal → `-<slug>`, todos existence-gated, else None); cost_envelope.py:142-145 (`strip("-")` → `Users-…` SEM traço); lessons.py:230-235 (`lstrip("-")` → `Users-…` SEM traço; refuse-on-empty-HOME); corretos: budget-summary.py:922, ceo-boot.py:1022, cc-native-usage-pull.py:71, memory-prioritize.py:90.
- E. Repo-local: `.claude/hooks/_lib/federation/handlers/audit_event_push.py:221-234` `_resolve_audit_log_path()`: CEO_AUDIT_LOG_PATH → `${CLAUDE_PROJECT_DIR:-cwd}/.claude/state/audit-log.jsonl`. Infra: O_APPEND+fsync atômico, SEM flock, cap payload 4KiB, cadeia prev_hash (:237-259). Reader: `.claude/hooks/check_skill_bootstrap_post.py:127-136`: candidates=[repo_root/.claude/state/audit-log.jsonl, $HOME/.claude/projects/ceo-orchestration/audit-log.jsonl], primeiro-que-existe, SEM env override (hook registrado em settings.json:440).

## 2) Prova COMPORTAMENTAL (subprocesso python3 com inputs impressos acima)
```
A audit_emit._audit_dir()   = /Users/joaocanhada/.claude/projects/ceo-orchestration
B state_store._state_root() = /Users/joaocanhada/.claude/projects/ceo-orchestration/state
C chain step3 scoped = …/-Users-joaocanhada-canhada-labs-ceo-orchestration/audit-log.jsonl | scoped.exists()=False | parent.is_dir()=True
C chain VERDICT (gate frouxo, ceo-cost/token-estimator/ceo-info): retorna o slug-path INEXISTENTE
D anti_ceo_overhead slug = '--Users-joaocanhada-canhada-labs-ceo-orchestration'
E SessionEnd memory dir = …/-Users-joaocanhada-canhada-labs-ceo-orchestration/memory
F federation path = <repo>/.claude/state/audit-log.jsonl
```
Confirmação on-disk (ls): (i) `~/.claude/projects/ceo-orchestration/` contém audit-log.jsonl (475.349 bytes, mtime hoje 14:48), 19 rotações datadas, audit-key, state/ com audit-pending.*.journal+.lock — o plano de auditoria VIVE no literal. (ii) `~/.claude/projects/-Users-joaocanhada-canhada-labs-ceo-orchestration/` existe (transcripts+memory) mas NÃO tem audit-log.jsonl → o gate frouxo de C mis-resolve de fato. (iii) `~/.claude/projects/--Users-joaocanhada-canhada-labs-ceo-orchestration/state/` existe e contém ceo-overhead-window-*.json(+.lock) e ceo-overhead-emit-budget.json — o bug duplo-traço ESCREVE hoje (e há 8 dirs `--*` de outros projetos no mesmo $HOME). (iv) glob `~/.claude/projects/Users-*` = zero matches — a grafia sem traço (lessons/cost_envelope) nunca materializou dir. (v) `<repo>/.claude/state/` existe (night-mode.json, night-mode.lock, review-loop, turbo) mas SEM audit-log.jsonl — o reader E cai no literal hoje.

## 3) Importadores (contagem por grep de import, não-teste)
- audit_emit: 129 arquivos não-teste (204 incl. testes) — grep `import audit_emit|from _lib.audit_emit|from _lib import audit_emit` em .claude/hooks+.claude/scripts.
- audit_log.py: 0 importadores (entrypoint de hook; resolvedor é cópia inline).
- state_store: 2 importadores reais não-teste (`from _lib.state_store import`): _lib/scratchpad_lib.py:109,121 e scripts/scratchpad.py:68 (demais 7 hits são menções em docstring/comentário).
- Cadeia C: 0 importadores — 6 cópias coladas em CLIs entrypoint.
- audit_event_push: consumido só dentro de _lib/federation/ (handlers/__init__, audit_event_batch, identity, scopes, server) + menção em audit_emit.
- Precedente de reconciliação JÁ SHIPADO: check_agent_spawn.py:2740-2757 `_audit_log_path()` DELEGA a audit_emit._log_path() ("PLAN-105 R2 P0 #2: previously derived a slug… Now imports the real resolver so reader path == writer path").
- Módulos não-teste contendo a construção literal (grep `projects" / "ceo-orchestration"|projects/ceo-orchestration`, inclui docstrings): 65 arquivos — ordem de grandeza compatível com o censo de 63 do PLAN-182/CLAUDE.md (o censo do plano é comportamental; o meu é textual, por isso a diferença de ±2).

## 4) CLAUDE_PROJECT_DIR_NATIVE (ADR-001)
grep -rn "CLAUDE_PROJECT_DIR_NATIVE" em *.py/*.sh/*.json de .claude/ e scripts/: VAZIO. Menções só em markdown: CLAUDE.md, .claude/adr/ADR-001-runtime-state-directory.md, PLAN-182 e seus arquivos de debate. Zero consumidores em código — confirmado.

### table

| # | Resolvedor (file:line) | Caminho produzido | Envs (ordem) | Importadores (não-teste) | Infra própria | O que VENCE hoje nessa família |
|---|---|---|---|---|---|---|
| A | `audit_emit._audit_dir()` — `.claude/hooks/_lib/audit_emit.py:2292-2298` (+mirrors: `audit_log.py:284-305` inline; `spool_writer.py:174` cacheado; `audit_hmac.py:155-183` c/ CEO_PROJECT_STATE_DIR extra) | LITERAL `$HOME/.claude/projects/ceo-orchestration/` | CEO_AUDIT_LOG_PATH (arquivo) → CEO_AUDIT_LOG_DIR → literal; nunca slug, nunca CLAUDE_PROJECT_DIR | **129** (audit_emit); audit_log.py=0 (entrypoint); check_agent_spawn DELEGA (:2740-2757) | flock (audit_log.py:116 + filelock), rotação (CEO_AUDIT_LOG_ROTATE_BYTES), spool journal em state/, HMAC key sibling; SEM cache em audit_emit, cache single-slot no spool_writer | **VENCE para o plano de auditoria inteiro** — log vivo 475KB + 19 rotações + key + journals estão lá (on-disk). W1: readers delegam a ESTE resolvedor (precedente PLAN-105) e a troca literal→slug tem de ser writer+readers ATÔMICA |
| B | `state_store._state_root()` — `.claude/hooks/_lib/state_store.py:114-126` | `$HOME/.claude/projects/<CEO_PROJECT_NAME>/state` (default literal) | CEO_STATE_ROOT → HOME + CEO_PROJECT_NAME (default `ceo-orchestration`) | **2** diretos (scratchpad_lib.py:109,121; scratchpad.py:68) + transitivo via scratchpad_lib | SQLite WAL + synchronous=NORMAL (:230-232); validação de nomes; audit fail-open | Vence o literal (CEO_PROJECT_NAME nunca setado). ÚNICO resolvedor já parametrizado por projeto — o esqueleto natural do resolvedor único da W1 |
| C | Cadeia 4-step ×6 cópias — ceo-cost.py:98-136; ceo-info.py:108-122; audit-telemetry.py:~85-100; ceo-diagnose.py:110-150; audit-log-retain.py:110-145; token-estimator.py:~580-590 | slug `-<abs-path>` SE gate passa, senão literal | PATH → DIR → slug(CLAUDE_PROJECT_DIR) → literal; **retain INVERTE: DIR → PATH** (:117-127) | **0** — código colado 6×, todos CLIs entrypoint | Nenhuma compartilhada; gates DIVERGEM: frouxo `parent.is_dir()` (ceo-cost:130, token-estimator:587), SEM gate (ceo-info:119), `is_file()` estrito (audit-telemetry:97, ceo-diagnose), `is_dir()` (retain:135) | Hoje leem o literal SÓ porque o operador roda sem CLAUDE_PROJECT_DIR; sob env de hook, 3/6 mis-resolvem p/ slug-dir SEM log (provado). Veredito: colapsar em delegação ao resolvedor do writer — a cadeia não é uma convenção, é 6 |
| D | Família slug-nativo — SessionEnd.py:89-90; ceo-info._memory_dir:129-140 + _transcripts_dir:668-684; ceo-boot.py:1022; budget-summary.py:922; cc-native-usage-pull.py:71; **check_anti_ceo_overhead.py:211-214 (BUG `--slug`)**; check_tier_policy_misrouting_24h.py:78-100; lessons.py:230-235 e cost_envelope.py:142-145 (variante SEM traço) | `-Users-…` (correto) / `--Users-…` (bug, escreve HOJE) / `Users-…` (nunca materializou) | CLAUDE_PROJECT_DIR (fallback cwd/REPO_ROOT); overrides pontuais: CEO_MEMORY_DIR, CEO_INFO_TRANSCRIPTS_DIR, CEO_LESSONS_DIR | 0 (derivações locais, uma por arquivo) | anti_ceo_overhead: mkdir + .lock por janela; demais read-only ou mkdir simples | **O slug nativo `-<abs-path>` vence para memória/transcripts** — o harness (dono) escreve lá; o framework só segue. Curas: unificar a derivação (1 função), matar o `--` e a grafia sem traço |
| +1 | Repo-local — writer `audit_event_push.py:221-234`; reader `check_skill_bootstrap_post.py:127-136` | `${CLAUDE_PROJECT_DIR:-cwd}/.claude/state/audit-log.jsonl` | Writer: CEO_AUDIT_LOG_PATH → repo-local; Reader: SEM env — [repo-local, literal] primeiro-que-existe | Writer: só dentro de _lib/federation/ (server/batch/handlers); Reader: hook registrado settings.json:440 | O_APPEND+fsync atômico, SEM flock, cap 4KiB, cadeia prev_hash | Arquivo NÃO existe neste repo → reader cai no literal hoje. É a convenção adopter-forward da federation; se a W1 promover repo-local p/ tudo sem migrar A, nasce a TERCEIRA convenção viva (literal + slug já coexistem) |

**Veredito consolidado:** hoje vencem, por família de consumidor — (audit/estado) literal `ceo-orchestration` via audit_emit; (memória/transcripts) slug nativo `-<abs-path>`; (CLIs) o literal por acidente de env; (federation) repo-local latente. `CLAUDE_PROJECT_DIR_NATIVE` (ADR-001): **zero consumidores em código** (só CLAUDE.md, ADR-001 e material do PLAN-182). A W1 deve: (1) eleger UM resolvedor (state_store é o único já parametrizado; audit_emit é o de maior gravidade com 129 importadores), (2) fazer todos os readers DELEGAREM (padrão check_agent_spawn/PLAN-105), (3) migrar writer+readers do plano de auditoria no MESMO corte — qualquer meio-termo cria a terceira convenção que a tarefa manda evitar.

### blockers

- Nenhum bloqueio de execução. Anomalias a registrar (não são instruções embutidas): (1) check_anti_ceo_overhead.py:213 escreve num QUINTO caminho (`--Users-…`, duplo traço) — confirmado on-disk com 8 dirs `--*` também de outros projetos do mesmo $HOME; qualquer censo da W1 que conte '4 implementações' sem esta perde um writer vivo. (2) A cadeia 4-step não é UMA implementação: são 6 cópias com 3 gates diferentes e uma inversão de precedência de env (audit-log-retain DIR>PATH) — reconciliar 'a cadeia' exige escolher qual das 6 é a canônica. (3) audit-log-retain é WRITER (rotação/retenção) usando gate `is_dir()`: sob CLAUDE_PROJECT_DIR setado ele mira o slug-dir dos transcripts, onde não há logs de auditoria — retenção silenciosamente no-op sobre os logs reais.

## US3 — cadeia (os dois instrumentos)

### summary

W0-US3 executado read-only com os DOIS instrumentos sobre $HOME/.claude/projects/ceo-orchestration/ (log vivo + 19 rotacionados = 20 arquivos, 293.720 linhas). RESULTADO: (1) audit-verify-chain.py = log VIVO intacto (630 verificadas), mas 17/19 rotacionados reportam TAMPER (exit 1) na primeira quebra; 2 intactos (2026-08-10 e 2026-08-13 — exatamente os dois dias quase-só-de-projetos-estrangeiros). (2) check-audit-hmac-null.py = exit 0, status ok, regression_count=0 nos 20 arquivos. O DELTA: os instrumentos medem classes DISJUNTAS. O hmac-null caça defeito-de-nascença por LINHA (hmac null/ausente/hmac_error em ação conhecida) — e essa classe está 100% ausente: todas as 293.720 linhas carregam hmac bem-formado, 0 malformadas. O verify-chain verifica CONTINUIDADE DE ELO — e um censo completo (script próprio, mesma _lib) mostra 45.783 elos quebrados (15,6%), 99,8% concentrados em eventos spool-drenados policy_evaluated/policy_denied com project:"". Sondas de re-link provaram que essas entradas não encadeiam com NADA observável: nem linha precedente, nem janela de 12, nem prev por-sessão/por-projeto, nem genesis sob as 3 chaves existentes, nem os logs dos outros 2 projetos, nem o predecessor do próprio batch de spool (0/10.480 no arquivo mais quebrado). Ou seja: nasceram encadeadas a estados de cadeia que não sobreviveram em disco — assinatura de FORK por escritores concorrentes multi-projeto (o defeito S315 que o PLAN-182 cura: o censo de project confirma arbitrage-monitor/42ledger-core/foxbit escrevendo NESTE log, inclusive AGORA no log vivo), e NÃO de adulteração pós-hoc de payload (edição de payload produziria exatamente 1 quebra com o elo seguinte ainda íntegro — padrão oposto ao observado). Consequência para W0: o RED do verify-chain histórico não é evidência de tamper adversarial e o GREEN do hmac-null não é evidência de cadeia íntegra; nenhum dos dois distingue tamper de fork multi-tenant, e o verify-chain PARA na primeira quebra (os 17 relatórios cobrem 17 de 45.783 quebras). A garantia ADR-079 já está estruturalmente falsa no histórico; só os 2 arquivos de janela mono-escritor e o log vivo pós-rotação-de-hoje (13:38, confirmada: mtime de audit-log-2026-08-17.jsonl) verificam ponta a ponta.

### evidence

INSTRUMENTOS USADOS (localizados por nome direto; grep verify_chain confirmou):
- (1) /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/scripts/audit-verify-chain.py (PLAN-023/ADR-055; exit 0=intact 1=tamper 2=key 3=malformed 4=perm; docstring: NÃO usa sidecar last-hmac; chain reseta só em fronteira de arquivo; PARA na primeira falha)
- (2) /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/scripts/check-audit-hmac-null.py (PLAN-136 T2a; caça hmac null/ausente OU hmac_error em ações conhecidas; docstring declara: "regression guard, NOT a full chain verification... catches the birth-defect class which a chain walk can structurally miss")

INPUTS DA MEDIÇÃO (impressos em runtime):
- dir: /Users/joaocanhada/.claude/projects/ceo-orchestration
- chave: audit-key, 32 bytes, mode 600, mtime Apr 18 (sem rotação de chave desde abril)
- 20 arquivos: audit-log.jsonl (vivo; crescendo DURANTE a medição: 613→674 linhas — sessões ativas escrevendo) + 19 audit-log-*.jsonl (imutáveis; rotação de hoje 13:38 = mtime de audit-log-2026-08-17.jsonl, confirmada)
- sidecars: audit-log.chain-length=609; audit-log.last-hmac mtime 14:47; DOIS lockfiles de eras distintas: audit-log.lock (Apr 11) e audit-log.jsonl.lock (May 28)
- env: PYTHONDONTWRITEBYTECODE=1 em todas as execuções; nenhuma escrita fora do scratchpad

COMANDO 1 (por arquivo): python3 audit-verify-chain.py --log-file <f> --key-file <dir>/audit-key --json
Saída bruta agregada: vivo = exit 0 {"status":"intact","verified_count":630,"pre_v29_count":0}. 17 rotacionados = exit 1 {"status":"tamper","line":<N>,"reason":"hmac_mismatch..."} (linhas/ações na tabela). 2 rotacionados intactos: 2026-08-10 (verified_count=12666) e 2026-08-13 (13523). Dois arquivos falham na LINHA 1 sobre chain_reset_marker (2026-08-17 e 2026-08-4). stderr vazio em todos.

COMANDO 2 (por arquivo): python3 check-audit-hmac-null.py --log <f> --json
Saída bruta agregada: os 20 arquivos = exit 0, {"status":"ok","regression_count":0,"findings":[]}.

CENSO COMPLETO DE QUEBRAS (script read-only próprio usando a MESMA _lib.audit_hmac.compute_entry_hmac + chave real; necessário porque o verify-chain para na 1ª quebra):
- 293.720 linhas totais; 293.720 com hmac (100%); 0 malformadas; 45.783 elos quebrados (15,6%)
- Ações nas quebras: policy_evaluated 30.243 + policy_denied 15.425 = 99,8%; project:"" em 45.672/45.783
- Censo de project por arquivo prova mistura cross-tenant (S315): ex. log VIVO agora = {ceo-orchestration:424, arbitrage-monitor:149, 42ledger-core:32, "":35, None:34}; 2026-08-10 = {42ledger:6294, arbitrage:6254, "":10} → INTACTO; 2026-08-9 = {arbitrage:8381, 42ledger:2061, ceo:284, "":3709} → 1990 quebras; foxbit-bot-arbitrage presente em 07-5 e 08

SONDAS DE CLASSIFICAÇÃO (todas negativas — as entradas quebradas não re-encadeiam com nada em disco):
- janela de 12 hmacs anteriores: 9/45.783 re-linkam (lags 2-5); genesis/previous_archive_last_hmac: 0
- prev por-SESSÃO e por-PROJETO + carry cross-file (ordem cronológica por mtime): 1 session_chain/45.782
- sonda profunda (amostra seed=42, n=40, audit-log-2026-08-4.jsonl, 10.592 quebras): prev testado contra TODOS os 17.613 hmacs do arquivo = 0/40; nenhum hmac duplicado
- chaves estrangeiras: 3 audit-keys distintas existem (ceo, foxbit-bot-arbitrage, book-engine-42ledger — únicos dirs com audit-log sob ~/.claude/projects; os dirs-slug ADR-001 NÃO têm log). genesis sob cada chave = 0/12; prev vindo dos pools de hmac foxbit (33.152) e book (1.202) com chave ceo = 0/12; chave foxbit + janela ±300 = 0/12
- mecânica de spool (linhas quebradas carregam _drain_epoch/_drain_sha256/spool_uuid/ordinal_within_file; drainer em _lib/spool_writer.py:1858-1880 computa HMAC no DRAIN, encadeando last_hmac sequencial seedado do tail do log): hipótese "hmac sem campos _drain_": 0/10.592; cadeia intra-spool seed-livre (elo com o predecessor do próprio batch): 0 quebras explicadas (as 5.226 que verificam intra-spool já eram OK em ordem de arquivo); 5.128 adjacências de batch INTERLEAVED no arquivo
- _lib atual é byte-idêntica entre installs (canonical_json/audit_hmac/spool_writer sha256 iguais em ceo/arbitrage-monitor/42ledger-core; audit_emit difere 13931 vs 13452 linhas) — o skew, se houver, é HISTÓRICO (não verificável em binários já substituídos)

INTERPRETAÇÃO (o delta por escrito): o verify-chain RED histórico ≠ tamper de payload. Padrão de tamper pós-hoc = 1 quebra isolada com o elo SEGUINTE íntegro (o sucessor encadeia no hmac gravado). Padrão observado = dezenas de milhares de entradas NASCIDAS com prev não-observável, concentradas na população spool-drain project:"", em dias de alta concorrência multi-projeto, com arquivos mono-tenant PERFEITOS — assinatura de forks de cadeia por escritores concorrentes de múltiplos projetos partilhando um dir literal, uma chave e (pelo menos) dois lockfiles de gerações diferentes. O hmac-null GREEN é real mas responde OUTRA pergunta (defeito-de-nascença por linha, classe S234 — ausente). Nenhum instrumento mede "cadeia íntegra por tenant" — essa é a lacuna que o PLAN-182 endereça; a nota HMAC-483 da memória ("verify_chain cru pós-rotação dá falso mismatch") é um caso particular desta classe (os 2 chain_reset_marker de linha 1 encadeados a um last-hmac sidecar que não sobreviveu como entrada).

Artefatos intermediários (stderr/json por arquivo): /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/baf2bbd3-e122-4a22-b6d2-adfecaa60f7a/scratchpad/w0us3/

### table

| arquivo | linhas | verify-chain (exit/status) | 1ª quebra (linha/ação) | quebras TOTAIS (censo) | hmac-null (exit/status/regressões) |
|---|---|---|---|---|---|
| audit-log.jsonl (vivo) | 629→674* | 0 / intact (630 verificadas) | — | 0 | 0 / ok / 0 |
| audit-log-2026-07-5.jsonl | 16114 | 1 / tamper | 1111 / policy_evaluated | 857 | 0 / ok / 0 |
| audit-log-2026-08.jsonl | 15030 | 1 / tamper | 231 / agent_spawn | 102 | 0 / ok / 0 |
| audit-log-2026-08-1.jsonl | 17692 | 1 / tamper | 584 / policy_evaluated | 5013 | 0 / ok / 0 |
| audit-log-2026-08-2.jsonl | 18093 | 1 / tamper | 649 / policy_evaluated | 1821 | 0 / ok / 0 |
| audit-log-2026-08-3.jsonl | 17763 | 1 / tamper | 102 / policy_evaluated | 5475 | 0 / ok / 0 |
| audit-log-2026-08-4.jsonl | 17613 | 1 / tamper | 1 / chain_reset_marker | 10592 | 0 / ok / 0 |
| audit-log-2026-08-5.jsonl | 16931 | 1 / tamper | 1031 / policy_evaluated | 5824 | 0 / ok / 0 |
| audit-log-2026-08-6.jsonl | 16268 | 1 / tamper | 13658 / agent_spawn | 1 | 0 / ok / 0 |
| audit-log-2026-08-7.jsonl | 15898 | 1 / tamper | 6473 / policy_evaluated | 3390 | 0 / ok / 0 |
| audit-log-2026-08-8.jsonl | 15995 | 1 / tamper | 191 / policy_evaluated | 2941 | 0 / ok / 0 |
| audit-log-2026-08-9.jsonl | 14564 | 1 / tamper | 74 / policy_evaluated | 1990 | 0 / ok / 0 |
| audit-log-2026-08-10.jsonl | 12666 | 0 / intact (12666) | — | 0 | 0 / ok / 0 |
| audit-log-2026-08-11.jsonl | 14002 | 1 / tamper | 9306 / policy_evaluated | 1126 | 0 / ok / 0 |
| audit-log-2026-08-12.jsonl | 13888 | 1 / tamper | 11170 / policy_evaluated | 25 | 0 / ok / 0 |
| audit-log-2026-08-13.jsonl | 13523 | 0 / intact (13523) | — | 0 | 0 / ok / 0 |
| audit-log-2026-08-14.jsonl | 13235 | 1 / tamper | 332 / policy_evaluated | 115 | 0 / ok / 0 |
| audit-log-2026-08-15.jsonl | 13420 | 1 / tamper | 5540 / policy_evaluated | 138 | 0 / ok / 0 |
| audit-log-2026-08-16.jsonl | 14128 | 1 / tamper | 132 / policy_evaluated | 1454 | 0 / ok / 0 |
| audit-log-2026-08-17.jsonl (rotacionado hoje 13:38) | 16223 | 1 / tamper | 1 / chain_reset_marker | 4919 | 0 / ok / 0 |
| **TOTAL** | **293720** | **intactos 3/20; tamper 17/20** | (verify-chain só reporta a 1ª por arquivo) | **45783 (15,6%)** | **ok 20/20; regressões 0** |

\* log vivo cresceu durante a medição (sessões ativas); verify-chain rodou num instante com 630 entradas verificadas — intacto de genesis ao tail naquele momento.

### blockers

- Nenhum bloqueio de execução. Anotações de validade: (1) o log VIVO estava recebendo escritas de sessões concorrentes durante a medição (613→674 linhas) — o veredito 'intact' do vivo vale para o instante do scan; os 19 rotacionados são imutáveis e os números deles são estáveis. (2) verify-chain PARA na primeira quebra por construção — os 17 relatórios 'tamper' cobrem 17 das 45.783 quebras; o censo total exigiu script auxiliar read-only com a mesma _lib (inputs impressos na evidência). (3) A causa-raiz EXATA da população órfã (prev não-observável) não é determinável read-only a partir do estado atual: os binários dos produtores da época já foram substituídos (_lib hoje é byte-idêntica entre installs) — o que está PROVADO é o padrão fork-de-escritores-concorrentes e a exclusão das hipóteses tamper-de-payload, genesis, chaves/logs estrangeiros e cadeia intra-spool. (4) Nenhuma instrução embutida em conteúdo lido foi encontrada; nenhum conteúdo cru de payload do log foi incluído no retorno (apenas agregados, hashes e nomes de campos/ações).
