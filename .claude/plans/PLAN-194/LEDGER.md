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

## Unidade atual — S362 (2026-10-02; `main` = `97a78fce`)

- Landados com a assinatura do Owner desde a abertura da S361: W2.0, a cura da condição 67
  (`65cd50d7`); W3b.1 (`a0a6df06`); W1 (`c54934d8`).
  verifier: `git merge-base --is-ancestor 65cd50d7 HEAD && git merge-base --is-ancestor a0a6df06 HEAD && git merge-base --is-ancestor c54934d8 HEAD` exit=0
- Debate L3 ratificado pelo Owner (`debate/round-3/approved.md`, commit `5c52998b`): W5c e W2 PROCEED;
  decisões 2, 4, 5 e 6 aceitas; decisão 1 superada; decisão 3 NÃO tomada ⇒ W3 ADIADA para a 1.4.4.
  verifier: `git merge-base --is-ancestor 5c52998b HEAD && test -f .claude/plans/PLAN-194/debate/round-3/approved.md` exit=0
- Em curso: o RP (seção acima). Decisões da abertura do trem: seção «Decisões do Owner — S362» do plano.

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

## W0.2 — manifesto do setup-python (controle vermelho da W1)

- 2026-10-01 (S361): no `versions-manifest.json` do ramo `main` de `actions/python-versions`, o
  Python 3.9 NÃO tem nenhum build linux para Ubuntu 26.04 (só até 24.04); 3.10 e 3.14 têm.
- ARQUIVADA em 2026-10-02 (S362), depois do LAND da W1 (`c54934d8`); o texto acima é o integral.

## W0.1 — Docker `ubuntu:26.04` (parcial)

- ARQUIVADA em 2026-10-02 (S362), depois do LAND da W1 (`c54934d8`), cujo sentinel assinado
  (`wave-w1-approved.md`, seção «Evidência») cita este registro. O título fica, para a âncora não
  mudar. Texto integral (substrato, itens (a) a (d), ferramenta e limpeza): `git show
  97a78fce:.claude/plans/PLAN-194/LEDGER.md`, linhas 52 a 198.
  verifier: `git show 97a78fce:.claude/plans/PLAN-194/LEDGER.md | sed -n '52p' | grep -q '^## W0.1 '` exit=0
- Resumo: medido de 2026-10-01T20:41Z a 2026-10-02T03:30Z (S361), colima aarch64 com 4 CPU e 6 GiB;
  `ubuntu:26.04` = `sha256:da6fc2be547864451aa253836dd926da33623312df4a9a243e35dc877c378a78` («Ubuntu
  26.04.1 LTS»), `python3` 3.14.4 na imagem.
  - (a) Template do adopter ativado e executado: 10/10 steps `run:` verdes no 26.04 e no 24.04 ⇒ W1.4
    sem mudança.
  - (b) Job `validate` antes do `setup-python`: só o step dos `import yaml` depende do sistema (PyYAML
    ausente) ⇒ W1.2.
  - (c) Suíte da matriz no 3.14: falhas contidas na linha de base 3.12, todas da classe «orçamento de
    tempo absoluto» ⇒ nada atribuível ao 3.14 nem ao 26.04.
  - (d) Censo: 21 workflows em `ubuntu-latest` (28 jobs) e 6 jobs `Ceo`; nenhum marcado como quebrando
    ⇒ W1.5 sem pacote. Não medidos: os dois jobs do `npm-publish.yml` e o TLC do `formal-verify.yml`.

## W3b.3 — verificação em fonte primária (ids da OpenAI)

- 2026-10-02 ~00:30Z (S361), fonte: página oficial de deprecações da OpenAI
  (`https://platform.openai.com/docs/deprecations`, que redireciona com 301 para
  `https://developers.openai.com/api/docs/deprecations`), lida por WebFetch (extração por modelo
  auxiliar; as linhas abaixo foram pedidas verbatim):
  - seção «2026-06-11: GPT-5 and o3 model deprecations»: desligamento em **Dec 11, 2026** de
    `gpt-5-2025-08-07`, `gpt-5-mini-2025-08-07`, `gpt-5-nano-2025-08-07`, `gpt-5-pro-2025-10-06`,
    `o3-2025-04-16` e `o3-pro-2025-06-10` (substitutos `gpt-5.6-sol`/`-terra`/`-luna`);
  - seção «2026-04-22: Legacy GPT model snapshots (July 2026 shutdown)»: desligamento em
    **July 23, 2026** (já passado) de `gpt-5-codex`, `gpt-5-chat-latest`, `gpt-5.1-codex`,
    `gpt-5.1-codex-max`, `gpt-5.1-codex-mini`, `gpt-5.2-codex`, `gpt-5.1-chat-latest` e
    `o3-deep-research-2025-06-26`;
  - **`gpt-5.5` NÃO aparece na página** ⇒ a aposentadoria em 2026-10-14 NÃO se confirma; pelo texto
    da W3b.3 o item fecha sem a linha no `model-deprecations.json` (Check: none, resultado aqui).
  - `o3-mini`: uma primeira extração resumida citou «October 23, 2026», mas a extração verbatim não
    trouxe linha de `o3-mini` ⇒ NÃO confirmado; re-conferir à mão antes da W3b.1.
- Consequência para a W3b (achado do builder da W3b.0 + esta leitura): com a cura do detector, uma
  variante só casa se o ledger a listar; `gpt-5-codex` (desligado em 2026-07-23) e os demais ids da
  seção de julho precisam entrar no `model-deprecations.json` para não ficarem escondidos (hoje o
  `gpt-5-codex` aparece em `codex_invoke.py` e `codex_phase_gate.py`). Entra no refresh do ledger
  junto da W3b.3 (mesmo arquivo; a regra INERT do `check-model-currency.py:64`, opção A do builder,
  vai no mesmo land).
- 2026-10-02T00:55Z (S361), re-conferência pedida acima («re-conferir à mão antes da W3b.1»), feita
  pelo builder da W3b.1 sobre o HTML CRU da mesma página (`curl -sSL
  https://developers.openai.com/api/docs/deprecations`, 482.750 bytes, sha256
  `d7f797e77e57c9b05c6b2e569499a60ece6a6917c934cdb779c4149a631d552d`; texto extraído por script,
  sem modelo auxiliar). A página tem DUAS seções com data 2026-04-22: a de julho (lida acima) e
  «2026-04-22: Legacy GPT model snapshots», SEM o parêntese, cujas linhas têm desligamento em
  **October 23, 2026** — 12 snapshots na tabela principal e 5 modelos com ajuste fino. Entre elas:
  - `o3-mini-2025-01-31 | o3-mini`, substituto `gpt-5.6-sol` ⇒ `o3-mini` CONFIRMADO (supera a linha
    «NÃO confirmado» acima; a primeira extração resumida acertou a data);
  - `o4-mini-2025-04-16 | o4-mini`, substituto `gpt-5.6-terra` ⇒ `o4-mini` também se aposenta (não
    estava na leitura de 2026-10-02 ~00:30Z).
  - `gpt-5.5` segue AUSENTE da página (0 ocorrências no HTML cru).
- Consequência (land livre, antes do SIGN da W3b.1): `o3-mini` e `o4-mini` ganham linha no
  `model-deprecations.json` (substituto `gpt-5.6-sol` pela política de alvo único do `_meta`; a
  página dá `gpt-5.6-terra` para o `o4-mini`, registrado na nota da linha), e o mapa de dívida
  `W3B1_DECLARED_DEBT` cresce de 12 para 14 acertos (os dois em `codex_cli_shape.py`). As outras 15
  linhas da seção de outubro (`gpt-3.5-turbo*`, `gpt-4*`, `o1*`, `gpt-image-1`, ajuste fino) e as 6
  linhas da seção de julho que o ledger não tem (`computer-use-preview*`, as duas `*-search-preview`,
  `gpt-audio-mini-*`, `gpt-realtime-mini-*`, `o4-mini-deep-research*`) NÃO entram: medido com um
  ledger de sonda contendo todas elas, nenhuma tem referência viva (não-INERT) nesta árvore
  (`check-model-deprecations.py --ledger <sonda> --json --today 2026-10-13` = só os 14 acertos acima).
  Ficam como backlog declarado (refresh completo do ledger da OpenAI, com substitutos por faixa
  depois que a W3b.1 põe a família `gpt-5.6-*` em `_VALID_MODELS`). A linha `o3-deep-research-2025-06-26`
  do ledger diz que nenhum alias sem data foi inferido, mas a página lista `o3-deep-research` como
  alias — mesmo backlog.

## W0.6 — verificador de procedência do Codex (S361, 2026-10-02)

- Medição completa (comandos, versões, células, saídas): fora do repositório, no checkpoint
  `s361-packs/b11-w06/W0.6-medicao.md` da sessão S361 (npm 11.16.0; `sigstore` 4.1.1 interno do npm;
  versões 0.160.0 e 0.156.1 do Codex; registro oficial e CDN do TUF do Sigstore).
- `npm audit signatures` NÃO serve para a W3: verifica só o que o REGISTRO declara (assinatura do
  registro e bundle do atestado), não os bytes locais, não fixa identidade, não exige o atestado e fica
  verde sem rede com cache quente. Células medidas: payload adulterado instalado ⇒ exit 0 «verified»;
  atestado removido ⇒ exit 0; atestado de outro repositório ⇒ verde.
- O `sigstore` interno do npm chamado com política de identidade (`certificateIdentityURI` +
  `certificateIssuer`) + vínculo em stdlib (sha512 do tarball = `subject` do atestado; sha256 do
  `bin/codex` lido em fluxo) dá verde no íntegro e vermelho em toda adulteração e identidade divergente.
  Decisão de desenho pendente do Owner: módulo interno do npm vs. `sigstore` fixado no staging.
- Identidade literal do construtor (0.160.0 e 0.156.1): repositório `https://github.com/openai/codex`,
  workflow `.github/workflows/rust-release.yml`, ref `refs/tags/rust-v<X.Y.Z>`, emissor OIDC
  `https://token.actions.githubusercontent.com`, `predicateType` `https://slsa.dev/provenance/v1`,
  purl de plataforma `pkg:npm/%40openai/codex@<X.Y.Z>-darwin-arm64`.
- Tamanhos 0.160.0: tarball de plataforma 134.311.083 bytes (332.972.398 descomprimido; `bin/codex`
  241.555.024). O pacote de plataforma traz outros executáveis fora do sha256 pinado (`rg`, `zsh`,
  `codex-voice-host`, dylibs) — entra no «escopo honesto» do ADR-182-AMEND-1.
- Controle: o sha256 do `bin/codex` da 0.156.1 lido do tarball = o do manifesto assinado (`0196e89f…`).

## Arquivo (S362, 2026-10-02)

- T0 (topo): CONGELADO no lugar, sem edição. `debate/round-1/security-engineer.md:263` cita
  `LEDGER.md:16-18`, `debate/round-1/qa-architect.md:40` cita «LEDGER, T0», e os registros de debate
  não se editam. A última frase do T0 está superada pela seção RP.
- W0.2 e W0.1: arquivadas nas próprias seções, com os títulos mantidos (âncoras estáveis). O texto
  integral da W0.1 está no histórico do git, preso ao `97a78fce` do `main`.
- O `LEDGER-ARCHIVE.md` da convenção do hook de checkpoint não foi criado nesta rodada; o histórico do
  git faz o papel de arquivo.
