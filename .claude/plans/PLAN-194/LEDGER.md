# PLAN-194 — LEDGER (diário de identificadores e medições)

Registro datado de comandos, identificadores e resultados das medições e dos lands do PLAN-194
(trem de manutenção até a v1.4.3). Uma entrada por fato; o que é medição diz o comando, a data e o
substrato. Este arquivo é LIVRE (oráculo de canonicidade = 0).

## T0 do trabalho longo — 2026-10-01 (S361)

- Owner aceitou em bloco as decisões Q1–Q14 (ver `PLAN-194-maintenance-train-v1-4-3.md`, seção
  «Decisões do Owner — S361»). Primeiro commit do trabalho longo: `6a9abb10` (emendas de texto).
- Substrato no T0: macOS 27.0.1; Claude Code 2.1.287 (auto-atualizado de 2.1.286 às
  2026-10-01T18:21:01Z, segundo `~/.claude/.last-update-result.json`); Codex CLI 0.156.1 pinado
  (`check_pair_rail.py --verify-codex-pin` = `verified`); Codex 0.160.0 publicado no npm em
  2026-10-01T20:26:19Z (não instalado; o Owner decidiu em 2026-10-01 atualizar pela W3, sem re-pin
  manual).
- Cadeia de auditoria no T0: `audit-log-2026-10.jsonl` com 1.ª quebra na linha 7726 (mesma da linha
  de base S360) e `audit-log.jsonl` vivo íntegro (372 elos) antes do primeiro spawn paralelo; as
  quebras posteriores em `agent_spawn` são a corrida no produtor descrita no risco 11.
- Backup da cadeia (W6.1, primeiro): `~/.ceo-backups/<slug>/ceo-backup-2026-10-01T195004Z.tar.gz`,
  30.111.116 bytes, sha256 `2217cafb1554e640183d087c182d20e4b8dd9399429d2fbce2ec06cd4f3ffe78`
  (15 arquivos `.jsonl` + `audit-log.errors` + `memory/`; sem `audit-key`, `.salt`,
  `audit-log.rotation-manifest.json`, `audit-log.last-hmac` e `audit-log.chain-length`).

## RP — re-pin manual do Codex 0.156.1 → 0.160.0: decisão e pré-voo (2026-10-02, S362)

- Decisão do Owner (2026-10-02): re-pin MANUAL 0.156.1 → 0.160.0 como 1.ª tarefa do trem da 1.4.3,
  pelo molde `.claude/plans/PLAN-193/codex-pin-0156/OWNER-PIN-SIGN.sh` com `--ga-tag v1.4.2`; pacote em
  `.claude/plans/PLAN-194/codex-pin-0160/`; SIGN do Owner previsto para sábado 2026-10-03. A decisão 3
  NÃO foi tomada ⇒ a W3 (pin automático) fica para depois da 1.4.3 e o VETO de Segurança segue levantado.
  Esta entrada supera a última frase do T0 («atualizar pela W3, sem re-pin manual»).
- Pré-voo medido em 2026-10-02 ~19:43Z, macOS 27.0.1, Claude Code 2.1.287 (`claude --version`):
  - `npm view @openai/codex dist-tags --json`: `latest` = 0.160.0, `alpha` = 0.162.0-alpha.7;
    `npm view @openai/codex versions --json`: nenhuma 0.160.x além da 0.160.0 (depois dela, só alphas).
  - Codex global: `codex --version` = `codex-cli 0.156.1`; `check_pair_rail.py --verify-codex-pin
    "$(command -v codex)"` = `verified`, payload sha256
    `0196e89fe5a7598f816ee54232c3d7c26d75e502ab5cfe2c9240e81d90f7255a` = o do manifesto
    (`package_version` 0.156.1).
  - `main` = `origin/main` = `97a78fce` (`git ls-remote origin refs/heads/main`).
  - Validate do `97a78fce`: verde (run 37038462492). Validate do `5c52998b`: vermelho (run
    37032883788) só no job `hook-tests-python-matrix (3.12)`, por 1 teste:
    `test_two_writer_chain.py::TestParallelWritersChain::test_parallel_spawn_and_sync_emit_writers_keep_the_chain`
    («writer kinds not interleaved»), o teste instável conhecido da guarda anti-vácuo; a cura de classe
    é um land livre próprio (FX).
  verifier: `test "$(gh run view 37038462492 --json conclusion --jq .conclusion)" = success` exit=0
- Detector do ensaio (`rehearse-pin-0156.sh:236-249`, com `NEW_VER=0.160.0`) sobre
  `PLAN-194-*.md`: no `97a78fce` acusava 1 linha (o passo do Owner com `<versão exata>`); com o texto do
  re-pin, saída vazia.
- Sonda da 0.160.0 (2026-10-02, S362; prefixo npm descartável, `--ignore-scripts`, registro fixo;
  `CODEX_HOME` temporário com cópia do config e da credencial, apagado no fim — D-20): **VERDE**.
  Payload `aarch64-apple-darwin`, lido ANTES de executar: sha256
  `112fae7a5a1223e673c8a1791d32338f37df8b527ff1159bb8adac6c4dbf1b4b`, 241.555.024 bytes;
  `--verify-codex-pin <prefixo>/bin/codex` ⇒ rc 1, `mismatch`/`payload_sha256_mismatch` (o rail fecha,
  como deve); `--version` = `codex-cli 0.160.0` (< 2 s); argv do hook (`build_verdict_argv`, com e sem
  `--json`) e argv do CEO aceitos (rc 0, nenhuma linha unexpected/unrecognized; controles negativos rc 2);
  `exec review`, `app-server` e `execpolicy check` vivos; `test_live_execpolicy_check` PASSED com o
  prefixo no `PATH`; canários reais servidos em `gpt-6-astra`/`xhigh`. A 0.160.0 anexa stdin em pipe
  como bloco `<stdin>` (o hook passa entrada vazia). O prefixo fica em `work/fd02/prefix`, no scratchpad
  da sessão, para o ensaio do pacote do RP.
- 2026-10-02 (S362): o rail do RP (rodada 1, lente de afirmações) deu P1 — o sentinel do pacote 0160 dizia «reportado para cura no gerador» sem registro rastreável; registro em `.claude/plans/PLAN-194-FOLLOWUP-repin-generator-hardening.md` (`draft`). Medido no mesmo dia: o endpoint de atestados do npm para `@openai/codex@0.160.0-darwin-arm64` responde HTTP 200 com o atestado de publicação e o SLSA `provenance/v1`; o gerador não o confere.

## Unidade atual — S362 (2026-10-03; `main` = `4a1eec73`)

- 2026-10-03: `main` = `origin/main` = `4a1eec73` (RP assinado pelo Owner e landado; Validate verde, run 37121036583).
  verifier: `git merge-base --is-ancestor 4a1eec73 HEAD` exit=0
- Landados com a assinatura do Owner desde a abertura da S361: W2.0, a cura da condição 67
  (`65cd50d7`); W3b.1 (`a0a6df06`); W1 (`c54934d8`).
  verifier: `git merge-base --is-ancestor 65cd50d7 HEAD && git merge-base --is-ancestor a0a6df06 HEAD && git merge-base --is-ancestor c54934d8 HEAD` exit=0
- Debate L3 ratificado pelo Owner (`debate/round-3/approved.md`, commit `5c52998b`): W5c e W2 PROCEED;
  decisões 2, 4, 5 e 6 aceitas; decisão 1 superada; decisão 3 NÃO tomada ⇒ W3 ADIADA para a 1.4.4.
  verifier: `git merge-base --is-ancestor 5c52998b HEAD && test -f .claude/plans/PLAN-194/debate/round-3/approved.md` exit=0
- RP LANDADO em `4a1eec73` (pai `4e4e21a8`; 4 paths: os 2 do pin, o sentinel e o `.asc`). Conferido pelo CEO: assinatura
  do sentinel válida com a chave do allowlist; os 2 arquivos do pin byte-iguais aos `.new` revisados; faixa
  `>=0.128.0,<0.161.0`; `check_pair_rail.py --verify-codex-pin` = `verified` (payload `112fae7a…`). O rail oficial passa
  a correr no Codex 0.160.0. Decisões da abertura do trem: seção «Decisões do Owner — S362» do plano.
  verifier: `git merge-base --is-ancestor 4a1eec73 HEAD && grep -q '<0.161.0' .claude/governance/codex-cli-pin.txt` exit=0

## Saídas para a 1.4.4 e hotfix do teste do F1 (2026-10-03, S362)

- FD-03 (cura do teste instável `TestParallelWritersChain`) SAI da 1.4.3 → 1.4.4: o anexo mecânico que o
  Owner decidiu deu NO-GO no Codex por afirmação falsa («todo caminho»: o `start()` ~`:615` e o assert
  ~`:474` ficam antes do `try`). Patches guardados fora do repositório. Até lá, o CI pede re-run quando o
  teste instável falhar — resíduo declarado da rc; a dependência FX da rc vira resíduo.
- F1e (rail r2 do F1; sombra do FD-07, commit `26ac3461`, fora do `main`) SAI da 1.4.3 → 1.4.4: na rodada
  3, FINAL, o Codex deu NO-GO com afirmação falsa reproduzida — «G7 never a silent 0» falha quando o
  `audit-log.errors` some e outro arquivo vazio ocupa o mesmo nome antes da 2.ª tentativa (G7 = 0,
  exit 0); o censo AST aceita `_spool_path(f.pid + 1)` no destino. O F1 landado (`9d47790f`..`eceb07af`)
  fica como está.
- Hotfix do teste do F1 landado em DUAS partes: `2b96bfd7` (o teste do race do G6 isolado do estado de
  PROCESSO do `spool_writer`) e `c4670649` (o controle parte de um buffer VAZIO: com ≥ 8 envelopes
  sobrando de testes anteriores, o begin/commit passava do `_JOURNAL_FLUSH_EVERY` = 10 e descarregava
  antes da checagem). Verificação (CEO, python 3.9.6): pareado 27 passed; ordem do CI em processo único
  (`.claude/hooks/tests` + o arquivo, `-m 'not serial'`) 7.137 passed, 34 skipped, 4 xfailed, rc 0.
  verifier: `git merge-base --is-ancestor 2b96bfd7 HEAD && git merge-base --is-ancestor c4670649 HEAD` exit=0
- Script da limpeza única da W2.6 (fora do repositório, `s362-tools/w26/`, sha `1191f7cc…` na rodada 3) SAI da 1.4.3 →
  1.4.4: na rodada 3, FINAL, o Codex deu NO-GO com duas afirmações falsas reproduzidas — «a família só sai inteira»
  (acréscimo num membro candidato depois do fsync da intenção ⇒ remoção parcial) e «o `--reconcile` nunca sai 0 com
  contagem inexata» (SIGSTOP/SIGKILL no meio ⇒ `exact=true`, rc 0, com 1 unlink efetivo). A cura pede troca de
  arquitetura: uma trava de manutenção honrada pelos escritores, em vez de detectar mudança depois do fato. A W26
  (limpeza do Owner, Lote 6) sai junto; a regra «agentes 8 → 12 depois da W2.6» fica sem gatilho.

## Bloqueios em aberto

- SIGN do Owner pendente: RP (sábado 2026-10-03). Antes dele: sonda da 0.160.0, pacote
  `codex-pin-0160` gerado, ensaio verde e rail no 0.156.1.
- Decisão 3 do Owner (empacotamento do verificador de procedência) NÃO tomada ⇒ W3 adiada para a
  1.4.4, VETO de Segurança levantado; seção W0.6, abaixo.
- Antes do SIGN do U2-A: a W0.5 no HEAD (pré-registro abaixo). O H1 vivo já está registrado (seção
  «W2 — H1 vivo»), antes do LAND do U2-A.
- Backlog declarado: refresh completo do ledger da OpenAI; seção W3b.3, abaixo.

## W0.5-pré-registro (gravado em 2026-10-02, S362, ANTES de qualquer execução)

Fonte: item W0.5 do plano (pré-registrado nas rodadas 1 e 2 do debate). Nada nesta seção foi medido
ainda; os resultados entram em entradas datadas abaixo dela.

- **Instrumento:** `.claude/plans/PLAN-194/w2/w05/w05_harness.py` (novo). O sha256 dele entra numa
  linha `W0.5-instrumento:` desta seção ANTES da 1.ª execução; execução com outro sha não conta.
- **Árvore:** descartável, no scratchpad da sessão, com ~233 mil entradas sintéticas (233.055 no state
  dir vivo, medidas pelo CEO em 2026-10-02); piso de `df` de 60 GB; limpeza confinada ao próprio
  diretório. NUNCA o state dir vivo.
- **Substrato, registrado em toda entrada:** versão do Claude Code (congelada; 2.1.287 em 2026-10-02);
  o `python3` que o `_python-hook.sh` usa (`/usr/bin/python3` 3.9.6, medido em 2026-10-02); SO (macOS
  27.0.1); sha do instrumento; carga no momento (agentes vivos). Rodar numa janela com poucos agentes
  vivos, ou registrar a carga.
- **Células (2^3 = 8), enumeradas antes:**

  | célula | spool próprio | diretório | saídas |
  |---|---|---|---|
  | C1 | não | vazio | 1 |
  | C2 | não | vazio | ≥ 9 concorrentes |
  | C3 | não | ~233 mil entradas | 1 |
  | C4 | não | ~233 mil entradas | ≥ 9 concorrentes |
  | C5 | sim | vazio | 1 |
  | C6 | sim | vazio | ≥ 9 concorrentes |
  | C7 | sim | ~233 mil entradas | 1 |
  | C8 | sim | ~233 mil entradas | ≥ 9 concorrentes |

- **Extras (numeração do item W0.5 do plano):** X1 — estoque só de travas (~150 mil) com ≥ 9
  concorrentes, a situação PERMANENTE sob T1, que decide a T2; X2 — entrega de decisão: guard que decide
  BLOCK, ≥ 9 saídas concorrentes, diretório cheio e um portador externo da trava canônica; X3 —
  encerramento do interpretador depois do `atexit` (a margem; calibra `EXIT_MARGIN_S`); X4 — intervalo do
  início do wrapper (`_python-hook.sh`, que mantém o PID por `exec`) até a âncora do prazo; X5 — drain
  oportunista ANTES da decisão; X6 — vivacidade da perna 3 sob rajada (`K_MAX` = 100); X7 — calibração
  com o harness REAL: só 2 chamadas `claude -p` (freio Q1), CC congelado, com um guard sintético de
  IMPORT TARDIO que imprime BLOQUEIO e atrasa a saída além do timeout, contra o mesmo guard saindo rápido,
  com e sem `flush`. Sem X7, o controle S1 é declarado no material assinado como prova contra um MODELO
  do harness.
- **Métricas:** p50 e p95 da latência de saída; decisão entregue ou descartada; linhas
  `drain canonical lock timeout`; taxa de `exit_deadline_skip`.
- **Estatística:** medir primeiro, no HEAD, a taxa p̂ de perda de decisão; escolher N com 3/N ≤ p̂/10;
  p95 só com N ≥ 100 (senão p90).
- **Critério de vermelho no HEAD:** ≥ 1 timeout em C4 ou C8; 0 timeout em C2 e em C6; decisão perdida
  em X2; H1 vermelho no HEAD (esperado F ≥ 0,9). Vermelho não reproduzido ⇒ esta seção registra
  «controle vermelho não reproduzido», e a prova da W2 passa a ser só estrutural, declarada como tal.
- **Esperado depois da cura (U2-C):** sem spool próprio (C1 a C4), razão p95 cheio/vazio ≤ 1,2; com
  spool próprio e ~150 mil travas, decisão entregue e prazo respeitado, sem exigir razão.
- **Valores iniciais:** ε = 0,01 (só com `|D|_min` ≥ 200 e o H1 medido no HEAD); `EXIT_MARGIN_S` = 1,0 s;
  prazo de 2,0 s; regra: margem ≥ p99 medido × 1,5 — se não couber, encolhe o PRAZO, nunca a margem
  (medição da máquina do Owner; a CI é mais lenta); limite de 2.000 `stat` no check do `/ceo-boot`.
- **Parada (regra do CEO, S362):** margem medida em X3 ≥ 3 s ⇒ a W2 PARA e vai ao Owner (o menor timeout
  registrado de hook é 3 s).
- **Gatilho da T2 (pacote de kernel próprio no `filelock.py`):** em X1, `exit_deadline_skip` > 0 ou p95
  de saída acima do orçamento; ou a W2.6 precisar rodar mais de 1× por mês; ou um Linux de vida longa.
- **Veredito:** uma linha por braço (no HEAD e depois da cura), no formato do item W0.5 do plano, com os
  campos `decisoes_descartadas` e `N`; a do braço depois da cura é a que o Check de sucesso da W2 lê. O
  mesmo instrumento roda o braço depois da cura NA SOMBRA do U2-C, antes do SIGN dele.
- Medição fora do CI; nenhuma asserção de tempo absoluto em teste.

## W2 — H1 vivo, antes da cura (2026-10-02, S362)

- `python3 .claude/scripts/audit_spool_state.py --flux --d-min 200 --since <ISO>` (`--since` conforme o
  relatório do FD-07; script do F1, ainda na sombra do FD-07, commits `ff843289` + `0f0a7b1a`), no state
  dir VIVO, SÓ LEITURA (`sandbox-exec` negando `file-write*` + audit hook do Python): **|D| = 14.572,
  F = 0,9947 ⇒ H1 VERMELHO no HEAD**, como esperado antes da cura da W2 (journals vazios de PID morto).
- 2026-10-02 (S362), `audit-log.errors` vivo, só leitura: contagens que o `ADR-055-AMEND-4` condensado
  cita e que sumiriam na rotação do arquivo (lane `H-03`); conferidas também pelo refutador do AMEND-4.
- STARVED do dreno oportunista (`drain canonical lock STARVED: … opportunistic drain yielded`): 0 às
  03:40Z (contagem do rascunho); 2 às 08:36Z (08:35:20Z e 08:36:23Z; registro do workflow do CEO, fora do
  repositório); 6 às 20:57Z. «STARVED (exit)»: 0.
- `would-log=` (linha que um `FileLockTimeout` do `audit_log.py` manda só para o breadcrumb; G7): 15, a
  1.ª em 2026-10-01T23:48:41Z e a última em 2026-10-02T20:49:53Z; 3 antes de 12:18:02Z (carimbo do commit
  `65cd50d7`, a W2.0) e 12 depois. Correlação, não causa provada: olhar antes do SIGN do U2-A.
- `drain canonical lock timeout`: 37.715 linhas às 20:57Z.
- Re-medido às 23:55Z (`grep -c` dos mesmos padrões; o verificador do F1 ainda não está no `main`):
  STARVED oportunista 6 (08:35:20Z, 08:36:23Z, 20:07:54Z, 20:14:27Z, 20:20:13Z, 20:29:48Z); «STARVED
  (exit)» 0; `would-log=` 15, nenhum novo desde 20:49:53Z, todos de `agent_spawn`; `drain canonical lock
  timeout` 38.054 (o arquivo tem 38.303 linhas).

## W4 — linha de base do publish (2026-10-02, S362; base da D-12)

- `gh run view 36719886734 --log` (NPM Publish do GA v1.4.2, `b55084da`, 2026-09-30, success; log de
  2.839 linhas, sha256 `4bfff28334cacd4faf0336e574070bc471bf4211c97dcf7d075b20d9cce39285`): job `publish`
  com `actions/setup-node@48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e` ⇒ `node: v20.20.2`, npm embutido
  10.8.2, passo do npm ⇒ `OK: npm 11.20.0`; `ceo-orchestration@1.4.2` publicado com proveniência.

## W6.0 — `cleanupPeriodDays` no binário do CC 2.1.287 (2026-10-02, S362; leitura, sem isca paga)

- Binário `versions/2.1.287`, sha256 `6eab8333fe2121553100d8f40bfada384a3e989b94f947e18ba6677a6fcb41ea`;
  leitura de código minificado (resíduo: não é execução). Os 5 pontos fecharam; a isca paga não foi
  necessária.
- A varredura apaga arquivos de topo `.jsonl` (inclusive `audit-log-*.jsonl`) de TODOS os diretórios de
  `~/.claude/projects/` com mtime mais velho que N dias; N = `cleanupPeriodDays` dos settings MESCLADOS
  da sessão que varre (padrão 30; inteiro ≥ 1). Não toca `audit-key`, `.salt`, `salt-minted.json`, os
  sidecars, `.lock` nem `.errors`. Todo processo que vive ~10 min varre (`.last-cleanup` < 24 h só adia).
- Precedência usuário → projeto → local → `--settings` → policy (a última vence): aqui vale 90
  (`.claude/settings.json:861`) sobre 3650 (usuário). Logo, 3650 aqui só protege das sessões DESTE
  repositório; o backup segue como proteção principal.
- W6.2: o binário diz `"medium" fewer than 10`; o `_posture_comment` (`.claude/settings.json:815`) diz 15.

## W6.3 — restaurar e verificar (2026-10-02, S362)

- Decisão do CEO, registrada antes de executar: aceitar as 2 escritas temporárias do `ceo-restore.sh`
  fora do `--dest` (listagem em `/tmp`, `:194-196`; extração inteira em `mktemp -d -t`, que no macOS
  ignora `TMPDIR`, `:230-233`); parada se algo fosse ao state dir vivo ou ao repositório.
- `bash .claude/scripts/ceo-restore.sh ~/.ceo-backups/<slug>/ceo-backup-2026-10-01T195004Z.tar.gz --dest
  <dir descartável>/restore --apply --force` ⇒ rc 0, `sha256: verified` (2026-10-02T20:08:00Z); nada
  sobrou em `/tmp` nem em `/var/folders/…/T`; state dir vivo e repositório intocados.
- `audit-verify-chain.py --log-file <arquivo> --key-file <state dir vivo>/audit-key --json`, cópia ×
  original: **paridade 15/15**, saída e stderr byte-idênticos. Exit 0: `08-1`, `09-3`, `09-4`, `09-5`,
  `09-8`, `09-9` e o `audit-log.jsonl` da cópia × o prefixo de 231.305 bytes (302 linhas) do vivo
  `audit-log-2026-10-1.jsonl`. Exit 1 (`hmac_mismatch`), mesma 1.ª linha nos dois: `08-2`:9729,
  `09`:13945, `09-1`:790, `09-2`:2582, `09-6`:5142, `09-7`:2849, `09-10`:12723, `10`:7726.
- Fora do backup de 2026-10-01: o resto do `10-1`, o `10-2`, o `10-3` e o `audit-log.jsonl` atual; por
  desenho, `audit-key`, `.salt`, `salt-minted.json` e os sidecars do log. Sem a chave original, a cópia
  é inverificável (D-13).
- Leitura (FD-09, sem patch): o log vivo nasce 0644 quando a rotação vem do dreno do spool
  (`audit_emit.py:2721`, `open("a")` sem `chmod`; a fase 5 do `spool_writer.py` não corrige); o
  `audit-log.errors` nasce 0644 por `open("a")` sem modo. Cura fora da 1.4.3 (D-11).
- **Achado ABERTO, sem patch — defeitos do `.claude/scripts/ceo-restore.sh`** (13 no relatório): listagem
  em caminho fixo de `/tmp`, fora do `trap` (`:194-196`, classe CWE-377); SIGPIPE sob `pipefail` aborta
  a partir de ~2.000 entradas (`:194`); `mktemp -t` ignora `TMPDIR` e `--dest` (`:230`); extração
  integral em claro, limpa só por `trap EXIT` (`:231-233`); destino 0755 e modos 0644 preservados
  (`:227`, `:239`, `:247`); o prompt anuncia `$DEST/audit/`, mas a cópia vai flat (`:211` × `:239`); o
  cabeçalho diz exit 1 no SHA divergente e o código sai 2 (`:15` × `:184`); sem `.sha256` o `--apply`
  segue (fail-open, `:177-189`); sem `--dest`, sobrescreve o `audit-log.jsonl` ativo sem tratar os
  sidecars (`:239`); `--restore-*` escrevem no CWD (`:253-265`); `--dest` sem valor ⇒ `unbound variable`
  (`:64`); aviso de listagem sempre impresso (cosmético). No backup: tarball 0644 em diretórios 0755,
  legível pelo grupo.

## Operação S362 — limites e cadeia (2026-10-02)

- Medido pelo CEO, 19:45Z–19:51Z: 7 agentes Opus 5.5 em xhigh ≈ 3–4 %/min da janela de 5 h e
  ≈ 0,6 %/min da semanal; o «101 %» do sidecar não parou os agentes; cadeia HMAC viva intacta com até 11
  agentes simultâneos (`audit-verify-chain.py`, ~6 mil elos). Reconfirmado às 20:24Z:
  `audit-verify-chain.py --log-file <state dir>/audit-log.jsonl --key-file <state dir>/audit-key --json`
  ⇒ `intact`, 10.887 elos.

## CC 2.1.288 — adoção e re-medição 287 × 288 (2026-10-02, S362)

- Decisão do Owner (2026-10-02, por múltipla escolha): «Adotar o 2.1.288». O 2.1.287 se atualizou
  sozinho às ~20:31Z (binário novo gravado às 20:31:44Z): o `DISABLE_AUTOUPDATER` não estava gravado, e o
  `autoUpdates=false` do `~/.claude.json` não protege instalação nativa com
  `autoUpdatesProtectedForNative=true`.
- Binários (só leitura; o único comando executado foi `--version`): 2.1.288 sha256
  `bbe93063f7a0879a1021b2891e5c9354e5b3b98433e32efe6750f7710afed750` (229.255.312 bytes; build
  2026-10-02T16:42:03Z, git `17fe1eb7`); 2.1.287 sha256
  `6eab8333fe2121553100d8f40bfada384a3e989b94f947e18ba6677a6fcb41ea` (build 2026-10-01T16:02:06Z, git
  `3c446a1b`). Método: busca de bytes e comparação de funções com os identificadores minificados
  normalizados. Reconferido às 2026-10-03T00:17Z: os dois sha e `claude --version` = 2.1.288.
- (1) `cleanupPeriodDays`: IGUAL (chunk da varredura com 36.757 bytes nas duas, diff normalizado vazio;
  padrão 30; mesma precedência; mesmo pulo `user_source_disabled`) ⇒ a W6.0 vale no 2.1.288.
- (2) `workflowSizeGuideline`: texto byte-idêntico (`{small:5,medium:10,large:50}`, padrão `medium`;
  guideline, não limite) ⇒ a correção do `_posture_comment` (15 → 10) da W6.2 segue válida.
- (3) Loader replicado por `.claude/scripts/tests/test_settings_guard_loadability.py`: IGUAL entre 287 e
  288 (33 eventos na mesma ordem, 9 chaves isentas, 26 funções com `unloadableGuards` normalizadas
  idênticas). Deriva no docstring do teste: a âncora `return{settings:c.data,errors:i}` não existe mais
  (hoje `errors:d`). A equivalência 2.1.280 → 2.1.288 foi checada só pelas constantes (o 2.1.280 não
  está em disco).
- (4) Watchdog e concorrência do Workflow: IGUAL — stall de 600 s, pausado com ferramenta em voo;
  concorrência `min(16, max(2, ncpu−2))` = 14 nesta máquina.
- (5) Mudanças periféricas, só adições: `modelSettings.<modelo>.autoCompactWindow` (100k a 1M ou `auto`);
  `/restart` no lugar do `/update` oculto, atrás de flag de servidor (`tengu_fancy_wand`); a espera de
  quota do subagente de Workflow (`workflowWaitsOutUsageLimit`), atrás de flag de servidor
  (`tengu_lantern_snuffer`, padrão desligado). Nada toca a varredura, o atualizador nem
  `availableModels`/`effortLevel`.
- (6) `DISABLE_AUTOUPDATER=1` ainda desliga o atualizador no 2.1.288 (o env do settings do usuário entra
  antes da confiança no workspace). Estado em 2026-10-03T00:17Z (21:17 de 2026-10-02 em Brasília): o
  `~/.claude/settings.json` AINDA não tem a chave ⇒ o congelamento só vale depois que o Owner gravá-la, e
  não vale sob `--setting-sources` sem `user`.

## CC 2.1.295 — adoção e re-medição 288 × 295 (2026-10-09, S363)

- Decisão do Owner (2026-10-08): adotar o 2.1.295. O atualizador subiu sozinho do 2.1.288 até o 2.1.295 (2.1.292
  gravado 2026-10-07T15:12Z; 2.1.293 às 18:13Z; 2.1.294 2026-10-08T05:24Z; 2.1.295 às 19:52Z). O 2.1.288 e os
  2.1.289–2.1.291 não estão mais em disco. `env.DISABLE_AUTOUPDATER="1"` entrou no `~/.claude/settings.json` em
  2026-10-09 ~00:45Z (mtime 00:47:22Z); nenhum binário novo depois disso.
- Binários (só leitura; o único comando executado foi `--version`): 2.1.295 sha256
  `0116ee2e0a513900b633d9951367f18747686478e2b462805b8c31609f047f70` (239.695.888 bytes; build 2026-10-08T16:50:59Z, git
  `07e8f67e`); ponto intermediário 2.1.292 sha256 `97a01e5bc74a199e67189435d0331ea3a24eac2e07db4b76d9148c5b0386138f`
  (235.017.328 bytes; build 2026-10-06T05:25:12Z, git `37832d0b`). Sem o 2.1.288, o 295 foi comparado com os fatos
  desta LEDGER e, função a função, com o 292. Método: módulos extraídos do grafo do Bun (`/$bunfs/root/chunk-*.js`) e
  comparação «idêntica a menos de renomeação» (texto de literais byte a byte).
- (1) `cleanupPeriodDays`: semântica IGUAL (mesma varredura, padrão 30, mesma precedência, mesmo pulo
  `user_source_disabled`; funções idênticas às do 292) ⇒ a W6.0 vale no 2.1.295. O chunk mudou: 36.757 → 38.217 bytes
  (292: 37.886). Do 292 para o 295 entrou só a varredura de `~/.claude/seed-admin`, que roda antes do teste de pulo e
  não toca `~/.claude/projects/`. O delta 288 → 292 (+1.129 bytes) não foi medido por diff.
- (2) `workflowSizeGuideline`: describe byte-idêntico (496 bytes, sha256 `ac6f84ab1841f8b6…`; zod em 187905139,
  describe em 187905221) e runtime idêntico ao 292 (`{small:5,medium:10,large:50}`, padrão `medium`, `small` em Pro)
  ⇒ o `_posture_comment` pode citar o 2.1.295 trocando só os números.
- (3) Loader replicado por `.claude/scripts/tests/test_settings_guard_loadability.py`: regra IGUAL (33 eventos na mesma
  ordem, 9 chaves isentas, `unloadableGuards` em 26 pontos do JS, funções-âncora idênticas às do 292). MUDOU o schema
  das entradas: `onFailure` (`continue`|`block`, sem `.catch`) em `command` e `http`. Valor inválido num guard ⇒
  `fatal` ⇒ arquivo inteiro `null`; a réplica não conhece o campo e dá verde (contradiz o «never the reverse» do
  docstring). Nenhuma superfície usa `onFailure` hoje. A âncora `return{settings:c.data,errors:i}` segue ausente
  (`errors:d`).
- (4) Watchdog e concorrência do Workflow: IGUAL no padrão — stall de 600 s, adiado com ferramenta em voo;
  concorrência `min(16, max(2, ncpu−2))` = 14. Novo desde o 292: o servidor pode subir a base do stall
  (`stream_idle_timeout_ms`, até 1.800 s ⇒ stall até 2.100 s).
- (5) Periféricas: o alias `haiku` passou a Haiku 5.5 (first party); `budget.total` do Workflow é sempre `null` (o
  orçamento de turno saiu do binário, sem linha no changelog; os 4 workflows do repositório não o usam); `onFailure`
  nos hooks; autoupdate de plugins sob host-pin. Chaves de settings (192) e comandos (99) iguais aos do 292. Nada toca
  a varredura dos projetos, o gate do atualizador nem `availableModels`/`effortLevel` (`max` segue fora).
- (6) `DISABLE_AUTOUPDATER=1` ainda desliga o atualizador no 2.1.295 (o env do settings do usuário entra antes da
  confiança no workspace). Estado em 2026-10-09T01:25Z: a chave está gravada (`~/.claude/settings.json:4`). Não vale
  sob `--setting-sources` sem `user`.
- (7) Modelos: entra `claude-haiku-5-5` (esforço padrão `medium`, aceita `max` e `xhigh`, 1M nativo; 0,10/0,50 USD por
  Mtok). Sonnet 5.5 e Opus 5.5: `medium`; Fable 5.1: `high`; entradas idênticas às do 292. O working set do ADR-149 tem
  `claude-haiku-4-5`, que pelo prefixo não admite `claude-haiku-5-5`; o modelo auxiliar do harness pode ir para Haiku
  5.5 mesmo assim (só `deniedModels` o barra). Adotar Haiku 5.5 é emenda da camada T.
- (9) Desde o 2.1.293 (ausente no 2.1.292), a leitura de UM arquivo pelo Bash também dispara o CLAUDE.md aninhado e
  as regras por caminho. Formas: `cat`/`nl`/`bat`, `head`, `tail`, `sed -n 'A,Bp'`; `grep`/`rg` só como comando único
  e com exit 0. Qualquer `|`, `<` ou `>` no texto desliga o gatilho; `cd x && cat y` não dispara. Carrega o CLAUDE.md
  de cada diretório entre o cwd e o arquivo, só dentro dos diretórios de trabalho e fora de deny de Read. Vale para
  subagentes e para o subagente de Workflow (mesmo runner, lista de gatilhos própria). `claudeMdExcludes` existe
  desde ≤ 2.1.220 com o mesmo texto: globs picomatch (`dot:true`) contra o caminho ABSOLUTO, lidos dos settings
  mesclados de todas as camadas (arrays somados); exclui `User`/`Project`/`Local`, nunca `Managed`, e vale também
  para o carregamento via Bash. Padrão relativo sem `**/` não casa nada. Medido: 8 `CLAUDE.md` encenados sob
  `.claude/plans/*/staged*/` (o maior com 37.485 bytes).
- Proveniência dos números históricos do `_posture_comment` (cura do P3 da rodada 1 da W6.2, lente r-w62-a;
  medidos com o binário de cada versão, só leitura): **2.1.295** (medido em 2026-10-09, S363): zod 187905139;
  describe 187905221; sha256 do span de 496 bytes
  `ac6f84ab1841f8b685fa9d399e771fa8c07ce5f26d168a88dcad1a7d3b146d2f`; sha256 do binário
  `0116ee2e0a513900b633d9951367f18747686478e2b462805b8c31609f047f70`. **2.1.288** (medido em 2026-10-02, S362): zod
  179683570; describe 179683652; sha256 do binário
  `bbe93063f7a0879a1021b2891e5c9354e5b3b98433e32efe6750f7710afed750`. **2.1.287** (medido em 2026-10-02, S362):
  offset 178658526 (o registro original não diz se é zod ou describe); sha256 do binário
  `6eab8333fe2121553100d8f40bfada384a3e989b94f947e18ba6677a6fcb41ea`. Os offsets do 2.1.288 e do 2.1.287 estavam
  registrados só no commit `1dafd090` da W6.2 (`ceremony(PLAN-194 W6.2)`, 2026-10-02), que NÃO é ancestral do
  `main` em 2026-10-09 (`git merge-base --is-ancestor 1dafd090 HEAD` = 1); os sha256 dos binários 2.1.287 e
  2.1.288 já constavam na seção «CC 2.1.288 — adoção e re-medição 287 × 288». Os binários 2.1.287 e 2.1.288 estão
  fora do disco desde então ⇒ esses números são INVERIFICÁVEIS hoje; o span de 496 bytes do 2.1.292, em disco, tem
  o mesmo sha256 (controle). Registro da lente: `rail/w62-r1/claude-r-w62-a-verbatim.md` (scratchpad da sessão
  `d876fa66`).
- Retenção — P2 medido pelo rail da W6.2 (lente r-w62-b, 2026-10-09 ~01:50Z; fora do diff da W6.2): há 55 checkouts
  irmãos em `~/canhada-labs` com `cleanupPeriodDays` 90 nesta máquina; a varredura de qualquer sessão deles apaga os
  `*.jsonl` de topo de TODOS os diretórios de `~/.claude/projects/` (corte de 90 dias EFETIVO; `last-cleanup`
  2026-10-08 21:59). O `audit-log-2026-08-1.jsonl` (mtime 2026-08-23) completa 90 dias em 2026-11-21 e será
  apagado nessa data, com ou sem o patch da W6.2. Curas possíveis, a decidir pelo Owner: managed/policy settings
  com 3650 (vence todas as camadas, @204769628 no binário 2.1.295), ou 3650 na camada local de cada checkout
  irmão; e agendar a W6.1.

## Noite S363 (2026-10-09) — construção e rail

Linhas propostas pelos builders (`b-w2b`, `c-w2a`, `c-free`) em `ledger-inbox/` do scratchpad da sessão
`d876fa66`, transcritas VERBATIM; só o título de cada arquivo virou subtítulo. **FD-25** = pacote livre do
`ceo-restore.sh`; **FD-26** = pacote livre do modo `--strict-against-counter` do `audit-verify-chain.py`.

### U2-B — construção (b-w2b, 2026-10-09 ~01:27Z)

- 2026-10-09 — U2-B construído na sombra: c8f61ccc6b49 sobre f03003d7 (peças (c) e (d) do ADR-055-AMEND-4); 2 paths (+334/−7); Check da W2: base 37/0 × cura 46/0; suíte .claude/hooks/tests -n auto: cura − base = ∅ (cópias sem .git) e, na sombra, 5 falhas só de orçamento de tempo, verdes em série nas duas árvores; 13 mutantes VERMELHOS; barreira 20/20 na cura e 0/10 em m1 e m2; gates staged rc=0; patch e sha256 em s363-packs/w2b (e3b0b8fc…afb48c3e).
- 2026-10-09 — Achado do censo openers: o 4.º abridor do journal, _invalidate_per_pid_caches_on_project_switch (spool_writer.py:252-253 no f03003d7; :256-257 em c8f61ccc; PLAN-182 r13/r14), anexa SEM a trava do journal. O «só flush, compactação e reconciliação» do AMEND-4 §4.4 está incompleto; janela de perda = a do os.replace atual (journal fora do INV-NP). Corrigir o texto no U2-D; pôr o anexo sob a trava = follow-up.
- 2026-10-09 — Dependência do U2-C: gatilho do STARVED (exit) = error=="canonical_lock_timeout" (spool_writer.py:2702 em c8f61ccc). O U2-C religa a exit_deadline_skip com espera efetiva > 0 e troca a célula negativa «espera zero» por «restante ≤ 0». Rede: -k starved reprova se o portão morrer (m3).
- Fora do pacote: peça (b) prazo (U2-C); seletores deadline/anchor/inode/invariant; texto §4.4 + Amended-by (U2-D); anexo da troca de projeto sob trava (follow-up); censo openers só superfície de hook (ponto cego: nome montado dinamicamente).
- Riscos: carimbo symlink fresco silencia até T (same-UID); «UM stat» medido em 3.9.6/3.11, não em 3.12/3.14; gate roda no handler SIGTERM (só syscalls).

### U2-A rodada 2 (c-w2a, 2026-10-09 ~05:12Z)

- 2026-10-09 (S363): U2-A rodada 2 do rail — cura 2474fed6 sobre f03003d7 (sombra w2a; patch s363-packs/w2a/3-r2-cure.patch sha256 212e127d…). Curados: Codex P1 (flush em pipe cheio), Codex P2 (chave textual), r-w2a-b P1 (journal na troca de projeto), r-w2a-a P2 (mutante M4), r-w2a-b P3 (célula (b)) e P3 de redação. 14 mutantes, 14 mortos; vermelho no f03003d7 nos 3 achados de comportamento.
- 2026-10-09 (S363): medido — flush com O_NONBLOCK nas duas camadas PERDE a decisão (TextIOWrapper em C descarta em EAGAIN o que não cabe no buffer binário; Linux: 4096 de 6000 bytes). A cura só esvazia a camada de texto quando cabe provadamente; no Linux a decisão que está na camada de texto sai no flush final, depois do drain (ordem da base), sob o prazo do U2-C. §4.1 passo 1 do AMEND-4 condensado precisa de emenda (FD-16) e o w2a-approved declara.
- 2026-10-09 (S363): bateria U2-A r2 — 5 arquivos ∅=∅; .claude/hooks/tests mesmo conjunto de 10 ids base × HEAD (ambiente sem .git); na sombra com .git 1 failed (p99 test_case_a_p99_under_5ms, orçamento absoluto). Gate de latência: pior R_e 1,015. Fast path de saída 15,5 µs (base 97,8). Canário: 0 linha de teste.
- 2026-10-09 (S363): censo do resíduo 13 — largo 37/26, estreito 26/15 (comando work/c-w2a/census.sh); bateria dos 37 com conjunto idêntico base × HEAD. O 20/8 do rascunho :884-886 não reproduz com nenhum dos dois recortes.
- Riscos: teto 721 linhas (canônico +167/−15; teste livre 539) > 400 — decisão do Owner; O_NONBLOCK na descrição de arquivo compartilhada (filhos veem na janela; SIGTERM padrão na janela sai com a flag ligada) — declarado; __sizeof__ detalhe do CPython (fora dele: lado seguro); tty com XOFF pode esperar; (pid, None) nunca removido (só se os.stat falhar logo após _state_dir()).

### FD-25 / FD-26 rodada 2 (c-free, 2026-10-09 ~05:12Z)

- 2026-10-09 · FD-26 r2 · 6fddda301a43 · sucesso strict sempre nomeado («absent» sem --verbose); log, chave e override com motivo nomeado e UM objeto JSON; só EACCES/EPERM dão 4; teste de troca open×fstat; 10/10 mutantes; sem strict byte-idêntico ao fd2d663f em 21 casos · resíduo: tracebacks sem strict (rc 1) → 1.4.4.
- 2026-10-09 · FD-25 r2 · d18e3838a32a · restauração nunca escreve através de symlink (dest, intermediário, folha), tudo-ou-nada; allowlist em audit/; tarball só com arquivo/diretório relativo, checado antes e depois de extrair; escrita via temporário no destino + rename; modos pré-existentes intocados; dest não é varrido; 17/17 mutantes; verde em bash 3.2/5.3 + bsdtar e GNU tar 1.35 · resíduo: TOCTOU same-UID declarado (classe PLAN-185).
- 2026-10-09 · FD-25 DECISÃO DO OWNER pendente: (1) backup com symlink em memory/ agora recusado (rc 2) — (a) manter + ceo-backup.sh derreferenciar/pular links (1.4.4) ou (b) restore pula só os links com aviso; (2) .claude symlinkado recusa --restore-plans/--restore-agent-metrics (rc 1, tudo-ou-nada) — (a) manter ou (b) aceitar symlink só no .claude do projeto. CEO seguiu com (a) nas duas (fail-closed) até a decisão.
- 2026-10-09 · FD-25 follow-up · ceo-backup.sh copia symlinks de memory/ como links; docs/INCIDENT-RESPONSE.md:258 cita --dry-run, que o script recusa → 1.4.4.

## Seções arquivadas (2026-10-03, S362)

O T0 fica no topo, congelado: `debate/round-1/security-engineer.md:263` cita `LEDGER.md:16-18`.
A convenção do hook de checkpoint chama o arquivo de `LEDGER-ARCHIVE.md`; o nome abaixo foi fixado pelo CEO.

- §W0.2 — manifesto do setup-python (controle vermelho da W1): arquivada em `LEDGER-archive-s361-s362.md` (sha256 `01963694d0827d89e38a9ca92fd266a30eaa39e172c803ce5c34cf652ae19b22`).
- §W0.1 — Docker `ubuntu:26.04` (parcial): arquivada em `LEDGER-archive-s361-s362.md` (sha256 `01963694d0827d89e38a9ca92fd266a30eaa39e172c803ce5c34cf652ae19b22`).
- §W3b.3 — verificação em fonte primária (ids da OpenAI): arquivada em `LEDGER-archive-s361-s362.md` (sha256 `01963694d0827d89e38a9ca92fd266a30eaa39e172c803ce5c34cf652ae19b22`).
- §W0.6 — verificador de procedência do Codex (S361, 2026-10-02): arquivada em `LEDGER-archive-s361-s362.md` (sha256 `01963694d0827d89e38a9ca92fd266a30eaa39e172c803ce5c34cf652ae19b22`).
- §Arquivo (S362, 2026-10-02): arquivada em `LEDGER-archive-s361-s362.md` (sha256 `01963694d0827d89e38a9ca92fd266a30eaa39e172c803ce5c34cf652ae19b22`).
