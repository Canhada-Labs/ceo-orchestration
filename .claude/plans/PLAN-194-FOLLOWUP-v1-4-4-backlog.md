---
id: PLAN-194-FOLLOWUP-v1-4-4-backlog
parent: PLAN-194
title: "Backlog da 1.4.4 saído da S363: pacotes estacionados, achados de rail e dívidas medidas"
status: draft
created: 2026-10-12
owner: CEO
depends_on: [PLAN-194]
level: L3
budget_tokens: "sem medição (estimado em 2026-10-12, S363): 3-6 M no total. Itens livres (5, 6a, 9, 10, 11 e o FD-25/FD-26) 1-2 M; canônicos (W6.2, U2-C, R4, 6b, 7, 8, 12, 13, 14, 15) 2-4 M, com o U2-C como maior parcela (redesenho + W0.5 pós-cura). Reestimar na abertura"
budget_sessions: "3-5 (estimado, sem medição); cada SIGN do Owner é uma parada"
context_risk: high
external_wait: "GA da 1.4.3 (nada canônico daqui entra antes dele); o molde «SIGN mínimo» landado no main; decisões do Owner listadas em «Open questions»"
eta_calendar: "sem data. Posição: depois do GA da 1.4.3, junto do resto da 1.4.4 (W3, PLAN-195, W7b do PLAN-183, W5c + Haiku 5.5)"
tags: [backlog, v1-4-4, followup, s363, spool, settings, ci, ceremony, classe]
---

# PLAN-194-FOLLOWUP-v1-4-4-backlog — o que a S363 mandou para a 1.4.4

> **Lineage (PLAN-SCHEMA §1.4).** Na noite S363 (2026-10-08 a 2026-10-12), vários pacotes do trem da 1.4.3
> pararam pela regra da rodada final (NO-GO por P0 ou por afirmação falsa reproduzida ⇒ o pacote sai do
> corte) ou por decisão do Owner. Outros achados de rail foram marcados «→ 1.4.4» sem registro rastreável.
> O registro da noite ficou na fila do CEO, fora do repositório. Este followup é o registro rastreável:
> cada item traz o defeito, a evidência no `main` (`dc805ed5`) ou numa ref `refs/s363/*` com SHA, se o
> caminho é canônico, a cura proposta e um Check.
>
> **O texto do PLAN-194 ainda não registra** as saídas da W6.2, do U2-C, do R4, do U2-A e do U2-B para a
> 1.4.4 (o corpo dele ainda os põe na 1.4.3). Atualizar o PLAN-194 é tarefa de uma edição própria, fora
> deste arquivo.

**Vocabulário:** *ref* = referência git local `refs/s363/<nome>`, que guarda o último commit de um pacote
fora do `main` (existe só no checkout do Owner; não foi enviada ao GitHub); *canônico* = o oráculo
`python3 .claude/hooks/check_canonical_edit.py --is-canonical <caminho>` responde `1` no STDOUT, e a
mudança exige SIGN do Owner; *livre* = o oráculo responde `0`; *SIGN mínimo* = o molde novo de
assinatura decidido pelo Owner na S363 (sem CAS, sem desfazer, sem rc 3, sem traps), hoje no branch
local `s363/sign-min` (`2bd7c18c`), ainda fora do `main`; *rodada final* = a regra pré-registrada da
S363 em que o NO-GO só vale por P0 ou por afirmação falsa reproduzida.

## Context

A S363 landou no `main` só pacotes livres e textos; nenhum canônico. Os canônicos do Lote A (W4, W5b) e
do Lote B (W7a, cost_envelope) seguem no trem da 1.4.3, migrados para o molde SIGN mínimo.

**Correção de 2026-10-12:** a versão anterior deste parágrafo punha também o U2-A e o U2-B no Lote A da
1.4.3. Os dois foram para a 1.4.4 em 2026-10-12. O micro-anexo do U2-A (`ab777824`) trouxe outra frase
falsa, e o Codex deu NO-GO: «a fotografia prova só que a configuração não mudou durante o SIGN»
(`.claude/plans/PLAN-194/w2a/rail-record.md:67-68` naquele commit) é falsa, porque a comparação é de dois
pontos e uma mudança A → B → A passa. A regra do Owner para esse anexo era «outra frase falsa ⇒ U2-A e
U2-B → 1.4.4». Estão estacionados em `refs/s363/u2a-1.4.4` = `ab777824` e `refs/s363/u2b-1.4.4` =
`49436225`. Este arquivo ainda não tem item próprio para eles; o registro (defeito, cura e Check) fica
para uma edição própria.

Ficaram para trás: a W6.2, o U2-C e o R4 (canônicos), o FD-25 e o FD-26 (livres, caíram na rodada
final), os pacotes livres C e D da triagem de planos (caíram duas vezes cada), e uma série de achados de
rail sem dono. Dois incidentes da noite (agente mexendo no checkout principal) e duas classes de crash
do Python (diálogos «Python encerrou inesperadamente» no Mac do Owner) também pedem cura estrutural.

## Goal

Cada item abaixo chega ao `main` com o Check verde (land livre ou SIGN do Owner), ou sai deste plano com
destino recíproco escrito no plano que o recebe.

## Approach

- **Canônico = pacote próprio no molde SIGN mínimo**, ≤ 400 linhas e ≤ 8 paths, rail com Codex + 2
  refutadores Claude na MESMA rodada (regra S361), e parada pré-registrada antes da 3.ª rodada.
- **Livre = land livre** com Codex + 1 refutador Claude, CI verde e gates sobre a árvore composta.
- **Ordem:** os itens que tocam `spool_writer.py` (U2-C e item 8) esperam o land do U2-A e do U2-B, que
  mudam o mesmo arquivo; os que tocam `.claude/settings.json` (W6.2 e R4) são KERNEL e vão em série; o
  item 6b espera o land da W7a, que muda `check_harness_config.py`.
- **Convenção dos Checks:** todo teste de regressão novo deste followup leva `fu144` no nome. O Check
  roda `pytest -k fu144` sobre o arquivo do item; enquanto o teste não existir, o pytest sai com rc 5
  (nada selecionado) e o Check fica vermelho. Teste novo nasce com controle vermelho→verde provado
  contra o código de antes da cura.
- **Cure a classe:** onde o item é a 2.ª ocorrência de uma forma, a cura proposta é estrutural (censo
  ou remoção), não o exemplo.

## Já registrado em outro lugar (não duplicar)

- PLAN-194 (corpo e «Decisões do Owner — S363»): W3 (pin automático), PLAN-195 inteiro, W7b do PLAN-183,
  W5c com o texto A3.1 do ADR-149 (S363-3), Haiku 5.5 (S363-7), C32/W9b do PLAN-183 (D-11), W8 e L2-L5.
- LEDGER do PLAN-194, «Saídas para a 1.4.4» (S362): F1e e o script da limpeza única da W2.6. O FD-03
  (teste instável `TestParallelWritersChain`) que estava lá foi curado no `main` pelo `bc803a7a` (S363).
- `PLAN-194-FOLLOWUP-repin-generator-hardening` (item 1) é o dono do pacote C (item 10 abaixo, só ponteiro).
- `PLAN-186-FOLLOWUP-sentinel-gpg-verification` (AC-7) é o dono do pacote D (item 11 abaixo, só ponteiro).

## Items

### Item 1 — W6.2: retenção de sessões e `_posture_comment` re-medido (canônico, KERNEL)

- **Dívida:** o sujeito é `.claude/settings.json`: `cleanupPeriodDays` 90 → 3650 (complemento do backup
  da W6, Q9/OQ-8) e os números do `_posture_comment` re-medidos no binário 2.1.295. No `main`, `:861`
  ainda diz `"cleanupPeriodDays": 90` e o comentário (`:815`) ainda cita o binário 2.1.220 («fewer than 15»).
- **Evidência:** ref `refs/s363/w62-1.4.4` = `adc927c7` (materiais no molde antigo; patch de código
  `.claude/plans/PLAN-194/w62/w62.patch`, 22 linhas, só esses dois valores). O rail dos materiais
  (rodada 4, Codex) deu NO-GO com 2 P1 de afirmação falsa reproduzida; a lane B de Claude deu GWC com 5 P3.
  As 5 curas pedidas (os 2 P1 e os 3 P2 vieram da mesma rodada 4 do Codex): P1-1 publicação por `update-ref` direto sem 2 fases («NADA publicado» depois de
  SIGKILL pós-`update-ref`); P1-2 a recusa altera estado (`git status` regrava o `.git/index`;
  `FETCH_HEAD` e temporários nascem antes da detecção); P2-1 `core.fsmonitor` com valor vazio passa como
  ausente; P2-2 TERM depois do CAS sai 143 em vez de 3; P2-3 o censo de palavras proibidas não pega
  variante sem acento nem palavra partida.
- **Canônico:** sim (`.claude/settings.json` = 1, KERNEL) ⇒ SIGN.
- **Cura:** refazer os materiais no molde SIGN mínimo. P1-1 e P2-2 somem por remoção (o molde não tem
  CAS nem rc 3); P1-2, P2-1 e P2-3 são conferidos contra o molde e, se ainda valerem, curados no molde
  (uma vez, para todos os pacotes). O patch de código não muda.

### Item 2 — U2-C: prazo da drenagem de saída, redesenho «sob prazo, zero drain» (canônico)

- **Defeito:** a drenagem forçada de saída do `spool_writer` pode estourar o prazo de decisão do hook.
  A cura da W2 (U2-C) caiu três rodadas seguidas pela MESMA classe: trabalho sem limite dentro do prazo.
- **Evidência:** ref `refs/s363/u2c-1.4.4` = `ff5c9376` (anexo sobre `2f723e39`; `spool_writer.py`
  +512 linhas e teste novo de 1477). Rodada 3 (final), Codex: NO-GO com 3 P1 de afirmação falsa
  reproduzida — a deduplicação da fase 3 escapa do prazo (3,73 s); a fase 5 regrava arquivos não
  consumidos sem limite; o teto de 64 KiB é checado antes dos flushes (journal de 79 KiB parseado em
  3,07 s). Decisão do Owner (S363, noite de 2026-10-09, UTC): U2-C → 1.4.4 com redesenho.
- **Canônico:** sim (`.claude/hooks/_lib/spool_writer.py` = 1) ⇒ SIGN. A T2 (pacote de kernel do
  `.claude/hooks/_lib/filelock.py`, oráculo 1) também.
- **Cura:** arquitetura por remoção — sob prazo, a saída não drena nada (só registra o pendente); o piso
  da perna 3 (arquivos maiores que K_MAX e órfãos de outros processos) passa a uma drenagem sem prazo fora
  do hook (no `/ceo-boot` ou no nightly) com o G3 `--residue` com chamador real (hoje sem chamador em
  produção). A T2 vira item nomeado: o sinal antecipado pós-cura (sem poder de veredito) disparou o
  gatilho dela (`exit_deadline_skip` em 81/171 e 68/171). A W0.5 pós-cura (pré-registro v2, N = 171, dois
  braços) roda no SHA que for ao SIGN, e só essa execução conta.
- **Dado-chave:** no substrato real dos hooks (python 3.11.15) o HEAD já deu X2 0/108; só o 3.9.6 perde
  (20/108). O U2-C passou do teto de 400 linhas (756 na r3); o redesenho deve caber nele ou declarar a exceção.

### Item 3 — R4: `claudeMdExcludes` com detector (canônico, KERNEL)

- **Defeito:** desde o Claude Code 2.1.293, ler um arquivo por Bash (`cat`, `sed -n`, `grep` de um arquivo)
  carrega os `CLAUDE.md` dos diretórios entre o cwd e o arquivo. Contratos velhos de pacotes encenados em
  `.claude/plans/**/staged*/` (até ~37 KB) entram no contexto. Achado de segurança junto: um
  `settings.local.json` com `claudeMdExcludes: ["**/CLAUDE.md"]` remove o `CLAUDE.md` raiz sem aviso, e
  `FORBIDDEN_KEYS` (`.claude/hooks/_lib/effective_config.py:135`) não cobre a chave (0 ocorrências no código dos hooks; a única do repositório é uma nota de observação em `.claude/scripts/substrate-watch.json:33`).
- **Evidência:** ref `refs/s363/r4-1.4.4` = `4ffb7574` (`settings.json` +4, teste novo de 549 linhas).
  Rodada 3 (final), Codex: NO-GO por 2 P2 de afirmação falsa (o censo pode omitir uma regra da raiz; «so
  a wider pattern fails» é falsa). Duas rodadas seguidas da classe «glob não ancora a raiz» (um checkout
  com a raiz dentro de `.claude/plans/**/staged*/` perde o próprio contrato). Decisão do Owner (S363,
  noite de 2026-10-09, UTC): R4 → 1.4.4 com detector.
- **Canônico:** sim (`.claude/settings.json` = 1, KERNEL; um hook novo também é canônico) ⇒ SIGN.
- **Cura:** um detector (hook de `InstructionsLoaded` ou de `SessionStart`) que acusa a raiz ausente do
  conjunto carregado; ele cobre o resíduo do glob e o canal de adulteração. Mais `claudeMdExcludes` em
  `FORBIDDEN_KEYS` quando o valor exclui a raiz.

### Item 4 — FD-25: `ceo-restore.sh` endurecido (livre)

- **Defeito:** a cópia do restore seguia symlink no `--dest` e podia sobrescrever a chave HMAC e o `.salt`
  do projeto vivo com rc 0 (P1 da r1 e da r2). Na `ref` esse P1 está curado e provado (`--dest` resolvido
  para o caminho físico, `..` recusado). A r3 (final) caiu por afirmação falsa: o dry-run aceita
  `.//audit/audit-key` (rc 0) que o apply recusa (rc 2); `.claude` como symlink pendurado deixa restauração
  parcial com «restore complete.» (rc 0); um mutante sem a pré-checagem dos destinos opcionais passa 27/27.
- **Evidência:** ref `refs/s363/fd25-ceo-restore-1.4.4` = `fa9d6bba` (`ceo-restore.sh` +399/−39; teste novo
  `.claude/scripts/tests/test_ceo_restore.py`). Dívidas no `main`: `docs/INCIDENT-RESPONSE.md:258` manda
  rodar `ceo-restore.sh … --dry-run`, e o script responde `unknown flag: --dry-run` (rc 1; medido em
  2026-10-12); `ceo-backup.sh` copia os symlinks de `memory/` como links (LEDGER do PLAN-194, entrada FD-25
  de 2026-10-09).
- **Canônico:** não (`ceo-restore.sh`, `ceo-backup.sh` e `docs/INCIDENT-RESPONSE.md` = 0) ⇒ land livre.
- **Cura:** partir da ref; paridade dry-run × apply por UMA função de validação dos nomes (normalizar
  `.//` antes); recusar `.claude` pendurado antes de qualquer escrita; teste que mata o mutante; corrigir
  o `INCIDENT-RESPONSE.md`; `ceo-backup.sh` derreferencia ou pula links (decisão do Owner, OQ-1).

### Item 5 — FD-26: `audit-verify-chain.py --strict-against-counter` (livre)

- **Defeito:** o modo strict tinha saídas fora do contrato (traceback, rc do argparse, JSON inválido). A
  r3 (final) caiu por afirmação falsa: stdin com UTF-8 inválido dá PASS strict (rc 0), enquanto os mesmos
  bytes num arquivo dão 3/`log_undecodable`; a promessa «não-strict byte-idêntico» falha com
  `--counter-override abc --help` (base rc 2, HEAD rc 0). Resíduo pré-existente registrado pela lane
  Claude da r2: um FIFO no lugar do log pendura a leitura (não reproduzido neste followup).
- **Evidência:** ref `refs/s363/fd26-verify-chain-strict-1.4.4` = `a1734e8c` (+789/−164 e +503 no teste).
  Decisão do Owner S363-4 (PLAN-194): contador AUSENTE ⇒ rc 0 com `chain_length_source:"absent"` visível;
  contador ILEGÍVEL ⇒ erro nomeado, fail-closed.
- **Canônico:** não (`.claude/scripts/audit-verify-chain.py` = 0) ⇒ land livre.
- **Cura:** stdin decodificado com `errors="strict"` (o mesmo caminho do arquivo); validação do override
  antes do `--help` só no modo strict, e o não-strict volta a ser byte-idêntico à base; abrir o log com
  `O_NONBLOCK` e recusar não-regular por `fstat` antes de ler.

### Item 6 — subgate `check-active-hooks-executable.py`: cinco follow-ups

O subgate landou no `main` (`cf785083..d8d13aaf`) depois da rodada 3 (Codex GO-WITH-CONDITIONS com 2 P2
pré-existentes como follow-up; lane Claude GO com 1 P3); estes ficaram como follow-up.

- **6a (livre — `.claude/scripts/check-active-hooks-executable.py` = 0):**
  1. **type/matcher sem validação:** `_hooks_shape_error` só exige `command` string quando
     `type == "command"` (`:112`); hook sem `type`, `type:"function"` e `matcher:7` passam verdes. A réplica
     do loader em `.claude/scripts/tests/test_settings_guard_loadability.py` (`:395-399`, `:440`) trata os
     três como fatais. Cura: validar pelo mesmo schema da réplica.
  2. **`command` lido de qualquer tipo:** o percurso aplica a regex a `hook.get("command")` sem olhar o
     tipo (`:82`); um hook `type:"prompt"` com campo extra `command:1` vira RED, embora o loader descarte o
     extra. Cura: extrair `command` só de `type == "command"`.
  3. **stat fora da rede:** `resolve()`/`is_file()`/`os.access` (`:128-132`) rodam em `main()` fora do
     `try`; laço de symlink ou `PermissionError` saem como traceback. Cura: trazer para a camada 2 (exit 2 nomeado).
  4. **settings que não é arquivo:** `if not settings_path.is_file(): return` (`:56`) pula em silêncio um
     diretório ou um symlink pendurado no lugar do settings (0 referências). Cura: só a AUSÊNCIA real é
     pulada; o resto é exit 2 nomeado.
- **6b (canônico — `.claude/hooks/check_harness_config.py` = 1, arquivo também tocado pela W7a):**
  5. **delegação engole stderr e exceção:** `run_exec_bit_gate` captura só o stdout (`:584`); o
     `::error::` do subgate vai para o stderr e some do detalhe do RED; e qualquer exceção que não seja
     `SystemExit` vira WARN «degraded» (`:589-594`), isto é, verde. Cura: capturar o stderr no detalhe e
     tratar exceção do subgate como RED nomeado (entrada que o gate não consegue ler = fail-closed).

### Item 7 — `_PLAN_PATH_RE` não casa `-FOLLOWUP-` (canônico)

- **Defeito:** o regex `\.claude/plans/PLAN-\d{3}-[a-z0-9-]+\.md$` não aceita o `FOLLOWUP` maiúsculo do
  nome de follow-up (PLAN-SCHEMA §1.4). O hook do ciclo de vida dos planos fica fail-open em TODOS os
  follow-ups: transições de `status:` não são conferidas.
- **Evidência:** `.claude/hooks/check_plan_edit.py:136` (usado em `:248` e `:532`) e
  `.claude/hooks/_lib/policy_preprocessors.py:237` (usado em `:317`). Medido em 2026-10-12: o regex dá
  `False` para `.claude/plans/PLAN-194-FOLLOWUP-repin-generator-hardening.md` e `True` para
  `PLAN-194-maintenance-train-v1-4-3.md`.
- **Canônico:** sim (os dois = 1) ⇒ SIGN, os dois no mesmo pacote (2.ª ocorrência da mesma forma).
- **Cura de classe:** um regex único num módulo compartilhado, igual ao da validação de nomes do
  PLAN-SCHEMA (`^PLAN-[0-9]{3}(-FOLLOWUP)?-[a-z0-9]+(-[a-z0-9]+)*\.md$`), importado pelos dois; teste que
  percorre os nomes reais de `.claude/plans/` e exige que todo plano casado pela validação seja casado
  pelo hook.

### Item 8 — handler de sinal do `spool_writer` se encadeia nele mesmo depois de `_reset_for_test` (canônico)

- **Defeito:** `_reset_for_test()` zera `_EXIT_HANDLER_INSTALLED` (`:2696`) sem restaurar os handlers de
  sinal. A reinstalação guarda o próprio `_signal_drain_handler` como «anterior», e o ramo
  `callable(prev)` (`:2634-2641`) chama a si mesmo até estourar a pilha.
- **Evidência (reproduzido neste followup, 2026-10-12, num diretório descartável com `HOME` e
  `CLAUDE_PROJECT_DIR` próprios):** `install_exit_handlers(); _reset_for_test(); install_exit_handlers();
  os.kill(os.getpid(), SIGTERM)`. Com `/usr/bin/python3` 3.9.6: rc 134, «Fatal Python error:
  _Py_CheckRecursiveCall: Cannot recover from stack overflow». Com python 3.11.15: rc 0 e o processo
  SOBREVIVE ao SIGTERM (a recursão é engolida pelo `except Exception` e o sinal se perde). A mesma forma
  está no `spool_writer.py` das refs do U2-B (`refs/s363/u2b-final`) e do U2-C. É a 2.ª classe dos
  diálogos de crash do Python da S363 (dois relatórios com essa mensagem).
- **Canônico:** sim (`spool_writer.py` = 1) ⇒ SIGN; landa depois do U2-A e do U2-B (mesmo arquivo).
- **Cura:** `prev is _signal_drain_handler` ⇒ tratar como `SIG_DFL` na instalação; `_reset_for_test`
  restaura os handlers anteriores. Teste em subprocesso que afirma o rc de morte por SIGTERM e a ausência
  de «Fatal Python error» nos dois Pythons.

### Item 9 — classe de teste: subprocesso Python sem assert de rc nem de «Fatal Python error» (livre)

- **Defeito:** a 1.ª classe de crash da S363 veio de `test_spool_state_amend4.py` (só no pacote U2, fora
  do `main`): o filho com uma thread daemon imprimindo 8 MiB num pipe sem leitor morria com «Fatal Python
  error: _enter_buffered_busy» (SIGABRT) no modo «exit», e o teste ficava verde porque não conferia o rc
  nesse modo. A cura desse arquivo viaja no patch do U2-A; a CLASSE fica aqui.
- **Evidência:** no `main`, nenhum teste afirma a ausência de «Fatal Python error» (`grep -rn` em
  `.claude/hooks/tests` e `.claude/scripts/tests`: 0). Medição: a contagem de `.ips` subnotifica (limite
  de 25 por assinatura); contar «Parsing corpse» no log do `ReportCrashService`.
- **Canônico:** não (testes e um script de censo em `.claude/scripts/` = 0) ⇒ land livre.
- **Cura:** um helper de teste que roda subprocesso Python e afirma o rc esperado SEM isenção por modo e a
  ausência de «Fatal Python error» no stderr; um censo AST que lista todo `subprocess.run`/`Popen` com
  `sys.executable` nos testes que não passa pelo helper nem afirma `returncode` (ratchet: a lista só diminui).

### Item 10 — pacote C: guarda do re-pin do Codex (livre; dono: `PLAN-194-FOLLOWUP-repin-generator-hardening`, item 1)

- **Estado:** estacionado em `refs/s363/plans-c-1.4.4` = `b3dfb928` (`re-pin-codex.py` +148/−33, teste
  +189, entrada no plano dono). Caiu duas vezes, as duas por enumeração de formas:
  (1) na gramática heredoc o parser aceita `SENT=/dev/null` e `SRC_PIN=/dev/null` antes do trap, e o guard
  emitido imprime PASSED com o marcador aberto; (2) formas de atribuição escapam do `_assigns`
  (subscrito `SENT[0]=`, `for SENT in`, `getopts`, `mapfile`/`readarray`, continuação de linha);
  (3) o `grep` do guard sem `-F` respeita `GREP_OPTIONS` no grep BSD (`-E` ⇒ fail-open; `-i` ⇒
  divergência); (4) rc 2 do `grep` tratado como limpo. Reproduzidos pelo refutador Claude e pelo Codex.
- **Canônico:** não (`re-pin-codex.py` = 0).
- **Cura proposta (da própria revisão):** por remoção — o guard emitido recebe como LITERAIS os caminhos
  que o gerador gravou, em vez de ler variáveis do molde; `env -u GREP_OPTIONS LC_ALL=C grep -Fn --`;
  rc ≠ 0/1 recusa. O registro e o Check ficam no plano dono; aqui só o ponteiro.

### Item 11 — pacote D: `check_contamination.scan()` fail-open (livre; dono: `PLAN-186-FOLLOWUP-sentinel-gpg-verification`, AC-7)

- **Estado:** estacionado em `refs/s363/plans-d-1.4.4` = `ea9995de` (`check_contamination.py` +183/−35,
  teste +295, plano dono). Caiu duas vezes: (1) symlink rastreado (modo 120000): a RULE 1 segue o link e
  lê outro arquivo, nunca o payload commitado (a string do destino) — repositório descartável com o termo
  só no destino do link dá rc 0 «No contamination»; (2) nomes não-UTF-8 decodificados com
  `errors="replace"` dos dois lados da prova de cobertura colidem ⇒ rc 0 sobre arquivo não lido;
  (3) frases falsas sobre o mecanismo (a caminhada vazia) e sobre o teste («each test was RED»).
- **Canônico:** não (`check_contamination.py` = 0).
- **Cura proposta:** na RULE 1, ler o symlink pelo `readlink` (como a RULE 2 já faz) e liberar só o gitlink
  160000; recusar nomes indecodificáveis no escopo antes da comparação, como a RULE 2. O `scan()` tem mais
  bordas fail-open do que o AC-7 previa: o redesenho começa por um censo das bordas. Registro e Check no
  plano dono.

### Item 12 — `cost_envelope`: dois follow-ups do pacote do Lote B (canônico)

- **Contexto:** o pacote `cost_envelope` (Lote B da 1.4.3) cura o `cost_envelope_capped` que nunca era
  gravado; o rail dele convergiu (rodada 1, Codex + 2 Claude GO) e deixou dois follow-ups.
- **12.1 — prosa × tabela do SPEC:** `SPEC/v1/audit-log.schema.md:1349-1352` diz que «raw project paths
  … NEVER persisted via this row», enquanto o índice (`:398`) lista `project` entre os campos do
  `cost_envelope_capped`, e outras tabelas tratam `project` como campo-base (`:1529`). A proibição mira
  o `project_path` cru, não o `project` do envelope; a prosa precisa dizer isso.
- **12.2 — fallback para o cwd:** `.claude/hooks/check_cost_envelope.py:177-178` —
  `_resolve_project_path()` cai em `os.getcwd()` sem `CLAUDE_PROJECT_DIR`; o envelope de custo pode ser
  contado no projeto errado. Cura: o resolvedor único (`_lib/runtime_paths.py`) e, sem projeto, decisão
  explícita (sem envelope + breadcrumb), nunca o cwd.
- **Canônico:** sim (`SPEC/v1/audit-log.schema.md` = 1; `check_cost_envelope.py` = 1) ⇒ SIGN. **Tocar o
  `SPEC/v1` muda a regra de versão do corte** (PLAN-194: se um pacote tocar o `SPEC/v1`, o CEO para e leva
  ao Owner) — OQ-5.

### Item 13 — `coverage` a 92 % do teto no `ubuntu-latest` e comentários falsos (canônico)

- **Defeito:** depois dos PRs #2 e #3 (mergeados sem cerimônia; o sentinel de ratificação
  `.claude/plans/PLAN-194/vmci-approved.md` está no `main`, à espera da assinatura do Owner), o `coverage` roda no `ubuntu-latest` em `pull_request` e no
  recuo da VM: 1925 s contra o teto de 35 min (`coverage.yml:41`), 175 s de folga. E dois comentários do
  `validate.yml` ficaram falsos: `:1646` («3.10-3.12 seguem no `Ceo`») e `:1656` («`Ceo` (8 nucleos) segue 25»).
- **Evidência:** `.claude/plans/PLAN-194/vmci/REVIEW-pr2.md` §5.1 e item 12 da lista de riscos;
  `.claude/plans/PLAN-194/vmci/red-control.txt:81` (run de PR do Coverage, 1925 s).
- **Canônico:** sim (os dois workflows = 1) ⇒ SIGN.
- **Cura:** subir o `timeout-minutes` do `coverage` ou devolvê-lo a um runner maior (OQ-3) e corrigir os
  dois comentários no mesmo pacote.

### Item 14 — guarda estrutural contra agente mexer no checkout principal (2 ocorrências)

- **Defeito (2 ocorrências na S363, no reflog do checkout principal):**
  1. 2026-10-09 21:07Z: «checkout: moving from main to ensaio-outra». Crases num COMENTÁRIO dentro de um
     heredoc sem aspas (`<<SHIM`) do harness do U2-B executaram `git switch -c ensaio-outra` no cwd do
     chamador. Restaurado em 2026-10-10 12:10Z.
  2. 2026-10-11 20:05Z: «checkout: moving from main to 598b70e5». Uma lane de revisão rodou
     `cd <sombra> ; git checkout …`, o `cd` falhou e o `;` deixou o `git` rodar no checkout principal
     (HEAD destacado por ~6 h). Restaurado em 2026-10-12 02:02Z.
  Nos dois, a ref `main` e a árvore ficaram intactas; o risco é o Owner puxar e assinar no branch errado.
  O branch `ensaio-outra` (`142f01cd`) segue no checkout principal como trava (`switch -c` falha se ele
  existe), até a cura do harness do U2-B landar.
- **Canônico:** depende da forma (OQ-2). Livre: o censo no `check-ceremony-script.py` (oráculo 0) e um
  check no `/ceo-boot` (`.claude/scripts/ceo-boot.py`, oráculo 0). Canônico: uma regra no
  `check_bash_safety.py` (oráculo 1).
- **Cura proposta (classe):** (a) o censo de cerimônia reprova crase ou `$(` dentro de heredoc sem aspas
  nos scripts de cerimônia e nos harnesses; (b) todo harness ganha a regressão «HEAD, `symbolic-ref` e
  `for-each-ref` do repositório chamador iguais antes e depois»; (c) o `/ceo-boot` acusa checkout
  principal fora de `main` ou com HEAD destacado e manda ler o reflog antes de qualquer trabalho;
  (d) opcional e canônico: o guard de Bash recusa `cd X ; git …` com escrita (exigir `cd X || exit` ou `&&`).
  Depois do land de (a)–(c), apagar o branch `ensaio-outra`.

### Item 15 — Python 3.14 só no runner hospedado (canônico; decisão do Owner)

- **Dívida:** na matriz, a 3.14 roda só no `schedule` e só no `ubuntu-26.04` hospedado
  (`validate.yml:1649-1655`, `:1673-1678`); as outras versões vão para a VM com `VM_CI_ENABLED=1`. Medido
  na S363: o push no main caiu de ~16 para ~8 min na VM, mas a corrida noturna fica em ~16 min porque a
  3.14 segue no GitHub. Item (b) da lista de decisões do Owner sobre a VM («rotear o 3.14 para a VM»),
  junto do isolamento do repositório público (decisão do Owner de 2026-10-12: «Manter e isolar»).
- **Canônico:** sim (`validate.yml` = 1) ⇒ SIGN.
- **Cura:** com a VM isolada e homogênea (mesma imagem e tool cache em todos os runners públicos, critério
  de estável = 10 verdes seguidas), tirar a exceção da 3.14 do `runs-on`; ou o Owner decide manter no
  hospedado, e o item fecha pelo registro da decisão.

### Item 16 — classe de teste: `subprocess.run(..., timeout=N)` sobre script de shell deixa netos vivos no grupo (livre)

- **Defeito (pela forma):** um teste que chama `subprocess.run(..., timeout=N)` sobre um script de shell,
  sem `start_new_session=True` e sem matar o grupo no estouro, deixa vivos os processos que o script lançou.
  No POSIX, o `subprocess.run` trata o estouro com `process.kill()` (só o filho direto), `process.wait()` e
  `raise` (conferido no código do `subprocess.run` do Python 3.9.6). Os netos ficam no grupo de processos
  de quem chamou, e um verificador que espera o grupo esvaziar (o X-BG do molde SIGN mínimo) recusa.
- **Evidência:** em 2026-10-12, o harness do molde SIGN mínimo sobre `2bd7c18c` caiu no ensaio do W5b com
  «o grupo de processos de hard 4 ainda tinha processo vivo 10 s depois de ele terminar» (X-BG; log da
  sessão, fora do repositório). No ensaio, o `hard` 4 é só
  `pytest .claude/scripts/tests/test_install_sh_placeholders.py` (lista `W5B_HARD` do `test-sign-min.py`
  no branch `s363/sign-min`); nos dados reais do W5b (`sign.tsv` do branch `s363/pk-w5b`, `124842e4`) o
  mesmo arquivo roda dentro do `hard` 9. O arquivo
  chama o `install.sh` por `subprocess.run(..., timeout=...)` sem sessão própria em dois sítios: o helper
  `_run_install` (`:87-89`, `timeout=120.0`, chamado em `:145`, `:193` e `:221`) e a chamada direta de
  `:256-259` (`timeout=120` em `:258`). A corrida que caiu estava carregada (o `hard` 3 levou 500,6 s,
  contra 379,2–410,5 s em três tentativas novas só do ensaio, nenhuma das quais reproduziu: 0 processos
  sobrando no grupo). O log do `hard` 4 da corrida que caiu foi apagado, então não está provado que o
  estouro de 120 s disparou NAQUELA corrida: a ligação é inferência do CEO, não um fato medido (o Codex da
  rodada do molde confirmou o mecanismo e disse o mesmo: «não determina a causa da corrida cujo log foi
  apagado»). O mecanismo foi medido à parte em 2026-10-12, numa sonda descartável: `bash -c 'sleep 30 | cat'` sob
  `timeout=1` deixa 2 processos vivos no grupo (`sleep` e `cat`); com `start_new_session=True` e
  `os.killpg` no estouro, 0; com `start_new_session=True` mas só o `kill` do filho, os mesmos 2 no grupo
  do filho.
- **Canônico:** não, se o helper ficar em `.claude/scripts/tests/` (o oráculo dá `0` para
  `.claude/scripts/tests/test_install_sh_placeholders.py` e para um arquivo novo nessa pasta). Em
  `.claude/hooks/_lib/testing.py` o oráculo dá `1`, ou seja, SIGN.
- **Cura (classe):** um helper de teste que roda o filho em sessão própria (`start_new_session=True`) e,
  no estouro, mata o GRUPO (`os.killpg`) antes de esperar; os dois sítios do
  `test_install_sh_placeholders.py` passam a usá-lo. Mais um censo AST que lista todo
  `subprocess.run`/`Popen`/`communicate` com `timeout` nos testes que não passa pelo helper (ratchet: a
  lista só diminui). Já existe código parecido no repositório:
  `.claude/scripts/swarm/_process_group.py` (`new_session_preexec`, `:54`; `kill_process_group`, `:92`);
  avaliar o reuso antes de escrever outro. O item 9 tem a mesma superfície (helper + censo AST sobre
  subprocesso nos testes): decidir na abertura se os dois viram um helper só, com as duas propriedades.

### Item 17 — W7ad: emenda aditiva do ADR-158 e os dois sítios com a pasta antiga das fixtures (canônico)

- **Origem:** decisão S364-1 do Owner (2026-10-15, seção «Decisões do Owner — S364» do PLAN-194). O
  sentinel da W7a (`.claude/plans/PLAN-183/w7a-approved.md`, landado em `b0f5fd45`) remete a emenda do
  ADR-158 a OUTRO pacote; ela não foi construída para a 1.4.3.
- **Defeito:** a W7a moveu as fixtures de replay para `.claude/hooks/_lib/harness_replay/` e esvaziou
  `.claude/hooks/tests/fixtures/harness-config/replay/`, mas dois sítios NORMATIVOS seguem citando a pasta
  antiga: `.claude/adr/ADR-158-harness-config-gate.md:60` e o comentário de
  `.github/workflows/validate.yml:1123` (medido em 2026-10-15 com `git grep 'harness-config/replay'` no
  `main` `4cd2bbc6`). Ficam fora, por desenho: os planos, a constante deliberada `_OLD_REPLAY_REL` de
  `.claude/hooks/tests/test_check_harness_config.py:61` e o relato histórico
  `docs/BUG-REPORT-adopter-harness-config-replay-fixtures.pt-BR.md`.
- **Canônico:** sim (oráculo `1` para o ADR e para o `validate.yml`) ⇒ SIGN.
- **Cura:** a do desenho ratificado no debate da W7 do PLAN-183 (C2,
  `.claude/plans/PLAN-183/debate/w7-round-1/consensus.md:139-140`): emenda ADITIVA dentro do ADR-158, que
  declara substituir a pasta do item 1 da Decisão (`ADR-158:57-60`), como `:166-167` já faz com texto
  antigo; a linha antiga fica como texto histórico. No mesmo pacote, o comentário do `validate.yml`
  passa a citar a pasta nova.

### Item 18 — U2-D: `ADR-055-AMEND-4` ACCEPTED e o leque (canônico, depois do U2-A ao U2-C)

- **Origem:** decisão S364-2 do Owner. A S363-3 punha o U2-D na 1.4.3; o U2-C saiu em 2026-10-09 e o U2-A e
  o U2-B em 2026-10-12 (Context). Aceitar a emenda sem o código que ela descreve declararia uma cura que
  não landou.
- **Canônico:** sim (pacote de ADR) ⇒ SIGN, depois do LAND do U2-A, do U2-B e do U2-C (item 2).
- **Cura:** o texto condensado do AMEND-4 já está no `main`, como fonte do pacote, em
  `.claude/plans/PLAN-194/w2d/ADR-055-AMEND-4.md` (`0fc2c311`, `db6bfda9`); ainda não há arquivo em
  `.claude/adr/`. O U2-D o leva a `.claude/adr/` como ACCEPTED com as
  correções que as rodadas da S363 pediram (LEDGER do PLAN-194, «Noite S363»: o 4.º abridor do journal no
  §4.4; o passo 1 do §4.1 sob `O_NONBLOCK`).

### Item 19 — F2, três levas: estresse da W2.5 (abre junto dos canônicos que estressa)

- **Origem:** decisão S364-4 do Owner. O RUNBOOK-1.4.3 punha a leva 1 do F2 para já, a leva 2 na sombra do
  U2-B e a leva 3 na sombra do U2-C; as curas que ele estressa foram todas para a 1.4.4.
- **Canônico:** a decidir pelo oráculo na abertura, caminho a caminho (pasta de teste não basta: sob
  `.claude/hooks/` há pastas de teste com oráculo `1`, como a do item 20).
- **Cura:** rodar as três levas junto dos itens 2 e 8 e do U2-A/U2-B, cada uma contra a árvore com a cura
  correspondente.

### Item 20 — classe de teste: orçamento ABSOLUTO de tempo que mede o ambiente, não o código (canônico para o teste; censo livre)

- **Defeito (pela forma):** um teste que compara um tempo de relógio com um teto fixo reprova por causa da
  máquina, do runner ou do estado do repositório, sem mudança de código. A classe já tinha registro: o
  `CLAUDE.md` (§5, S357→S358) a chama de «flake de runner», na 3.ª ocorrência, com cura estrutural
  pendente; e o LEDGER do PLAN-194 («Noite S363») registra 5 falhas só de orçamento de tempo no U2-B e o
  p99 de `test_case_a_p99_under_5ms` no U2-A.
- **Evidência (2026-10-15):**
  `.claude/hooks/_lib/tests/test_plan104_microbench.py::TestDetectorLatencyBudget::test_full_scan_subprocess_p95_budget`
  mede `persona_demand_scan._scan_branch_ahead`, que roda um `git rev-list --count` por ramo local
  (`.claude/scripts/persona_demand_scan.py:152-200`). No checkout do Owner, com 76 ramos locais, deu
  ~1,2 s contra o teto de 500 ms, com e sem os pacotes LIVRES landados no dia (`ci-free`, `plans-p195`,
  `plans-p191`; LEDGER, «Lote assinado —
  2026-10-15 (S364)»). Em clone novo e no CI, que só têm o `main`, passa. Na S364, o teste foi rodado
  isolado nas duas árvores; a passada serial em que ele falhou foi a da bateria do land.
- **Canônico:** sim para o teste desta ocorrência (o oráculo dá `1` para
  `.claude/hooks/_lib/tests/test_plan104_microbench.py`, medido em 2026-10-15) ⇒ SIGN; o censo novo pode
  ficar numa pasta de oráculo `0` (conferir na abertura).
- **Cura (classe):** orçamento RELATIVO, normalizado por unidade de trabalho (aqui, por ramo) ou contra uma
  medida de referência no mesmo processo, como o gate de latência fez (`hook_p50 ≤ K_e × ref_p50`); mais
  um censo que lista os testes com teto absoluto de relógio (ratchet: a lista só diminui).
- **2.ª evidência (2026-10-15, bateria do land da C9):**
  `tests/integration/test_install_smoke.py::test_install_creates_expected_layout` reprovou na passada
  paralela e nas 3 re-execuções isoladas da bateria por `TimeoutExpired` do `install.sh` (teto de 90 s,
  `tests/integration/test_install_smoke.py:34`), com load ~13 e o executor histórico rodando ao lado;
  depois, com load ~7,7, passou 2 de 2 isolado (67 s e 54 s). Fonte: registro da bateria da sessão S364; a
  mensagem de `7428d25b` registra a falha e os 2 verdes. O land não tocava o `install.sh` nem o teste. O
  `_run_install` é `subprocess.run(timeout=90)` sem `start_new_session`, a forma do item 16 (cada
  `TimeoutExpired` pode deixar netos do `install.sh`); o oráculo dá `0` para esse arquivo (livre).

### Item 21 — doc da W6 (FD-22) com a W6.2, o FD-25 e o FD-26 (livre; decisão do Owner S364-5)

- **O quê:** `refs/s362/w6-doc-dr-install` = `1e08dd90` (4 commits sobre `cd5b90c7`; `INSTALL.md` e
  `docs/DISASTER-RECOVERY.md`; GO na rodada 3 da S362). O texto afirma a W6.2 («The framework repository's
  own `.claude/settings.json` moves to 3650 in v1.4.3», `INSTALL.md`), que está na 1.4.4. Os trechos sobre o
  `ceo-restore.sh` («Known limitations of ceo-restore.sh») e sobre a cópia em staging com o
  `--strict-against-counter` descrevem o `main` de HOJE, pré-FD-25/FD-26: ficam falsos quando eles landarem.
- **Acoplamentos:** landar no mesmo trem que a W6.2, o FD-25 e o FD-26, com a frase da versão corrigida para
  1.4.4, a seção «Known limitations of ceo-restore.sh» reescrita depois do FD-25 e o parágrafo da cópia em
  staging reescrito depois do FD-26. O Known-open da `[1.4.3]` do `CHANGELOG.md` («… and the
  disaster-recovery guide does not say so») é verdade hoje e deixa de valer quando a doc landar: a entrada
  da 1.4.4 o retira. O conserto de `docs/substrate-adopt-2026-09.md:62` e `:116` (o P3-2 do rail da W6.2
  cita o G27, `:116`; o `:62` diz que o settings do repositório fixa 90) só vale depois do land da W6.2.
  Re-conferir o texto contra o `main` da época (o FD-23 landou depois do GO da rodada 3).
- **Land:** `merge --no-ff` (as mensagens citam SHAs).

## Open questions

- **OQ-1 (FD-25, pendente desde 2026-10-09, LEDGER do PLAN-194):** (1) backup com symlink em `memory/`:
  (a) o restore recusa e o `ceo-backup.sh` derreferencia ou pula links, ou (b) o restore pula só os links
  com aviso; (2) `.claude` symlinkado: (a) recusar `--restore-plans`/`--restore-agent-metrics` (tudo ou
  nada), ou (b) aceitar symlink só no `.claude` do projeto. Hoje a ref segue (a) nas duas.
- **OQ-2 (item 14):** só as formas livres (a)–(c), ou também a regra canônica (d) no guard de Bash?
- **OQ-3 (itens 13 e 15):** `coverage` — subir o teto ou mudar de runner? 3.14 — rotear para a VM depois
  do isolamento ou manter no hospedado?
- **OQ-4 (item 3):** o detector do R4 entra como hook de `InstructionsLoaded` ou de `SessionStart`?
  `claudeMdExcludes` entra em `FORBIDDEN_KEYS` sempre, ou só quando o valor exclui a raiz?
- **OQ-5 (item 12):** o follow-up 12.1 toca o `SPEC/v1`. Entra na 1.4.4 (com a regra de versão
  reavaliada) ou espera um corte que já toque o `SPEC/v1`?

## How to continue

«Leia `.claude/plans/PLAN-194-FOLLOWUP-v1-4-4-backlog.md`. Confira que o GA da 1.4.3 saiu e que o molde
SIGN mínimo está no `main`. Para cada item, rode o oráculo `--is-canonical` nos caminhos e o Check do item
(deve estar vermelho); abra primeiro os livres (4, 5, 6a, 9, 10, 11, 16 e o censo do 20; o 21 vai junto
do item 1 e do FD-25/FD-26; o item 19 abre
junto dos canônicos que ele estressa), cada um numa sombra própria a partir
da ref citada quando houver, com rail Codex + 1 Claude. Os canônicos seguem a ordem do Approach e esperam
as respostas das Open questions que os tocam.»

## Success criteria

- [ ] Item 1 (W6.2) landado por SIGN no molde SIGN mínimo.
  Check: `grep -q '"cleanupPeriodDays": 3650' .claude/settings.json && grep -q 're-read in the 2.1.295 binary' .claude/settings.json`
- [ ] Item 2 (U2-C) landado por SIGN, com a W0.5 pós-cura executada no SHA do SIGN e registrada no LEDGER.
  Check: `python3 -m pytest .claude/hooks/tests/test_spool_state_amend4.py -q -k "deadline or fu144"`
- [ ] Item 3 (R4) landado por SIGN, com o detector da raiz ausente.
  Check: `grep -q '"claudeMdExcludes"' .claude/settings.json && python3 -m pytest .claude/hooks/tests/test_claude_md_excludes.py -q`
- [ ] Item 4 (FD-25) landado livre; doc do restore sem a flag inexistente.
  Check: `! grep -n -- 'ceo-restore.sh .*--dry-run' docs/INCIDENT-RESPONSE.md && python3 -m pytest .claude/scripts/tests/test_ceo_restore.py -q`
- [ ] Item 5 (FD-26) landado livre.
  Check: `python3 -m pytest .claude/scripts/tests/test_audit_verify_chain.py -q -k fu144`
- [ ] Item 6a (subgate, 4 follow-ups livres) landado.
  Check: `python3 -m pytest .claude/scripts/tests/test_check_active_hooks_executable.py -q -k fu144`
- [ ] Item 6b (delegação no `check_harness_config.py`) landado por SIGN depois da W7a.
  Check: `python3 -m pytest .claude/hooks/tests/test_check_harness_config.py -q -k fu144`
- [ ] Item 7 (`_PLAN_PATH_RE`) landado por SIGN, os dois arquivos no mesmo pacote.
  Check: `python3 -m pytest .claude/hooks/tests/test_check_plan_edit.py .claude/hooks/tests/test_policy_preprocessors.py -q -k fu144`
- [ ] Item 8 (handler de sinal) landado por SIGN depois do U2-A e do U2-B.
  Check: `python3 -m pytest .claude/hooks/tests/test_spool_writer_signal_chain.py -q`
- [ ] Item 9 (helper + censo da classe) landado livre.
  Check: `python3 -m pytest .claude/scripts/tests/test_python_subprocess_rc_census.py -q`
- [ ] Item 10 fechado no plano dono (`PLAN-194-FOLLOWUP-repin-generator-hardening`, item 1).
  Check: `python3 -m pytest .claude/scripts/tests/test_re_pin_codex.py -q -k fu144`
- [ ] Item 11 fechado no plano dono (`PLAN-186-FOLLOWUP-sentinel-gpg-verification`, AC-7).
  Check: `python3 -m pytest .claude/scripts/tests/test_check_contamination_personal_path.py -q -k fu144`
- [ ] Item 12 (dois follow-ups do `cost_envelope`) landado por SIGN, com a OQ-5 respondida.
  Check: `! grep -n 'os.getcwd()' .claude/hooks/check_cost_envelope.py && python3 -m pytest .claude/hooks/tests/test_check_cost_envelope_block.py -q -k fu144`
- [ ] Item 13 (`coverage` e comentários) landado por SIGN.
  Check: ``! grep -n -F 'seguem no `Ceo`' .github/workflows/validate.yml && ! grep -n -F '`Ceo` (8 nucleos) segue 25' .github/workflows/validate.yml``
- [ ] Item 14 (guarda do checkout principal, formas livres) landado e o branch `ensaio-outra` apagado.
  Check: `python3 -m pytest .claude/scripts/tests/test_check_ceremony_script.py .claude/scripts/tests/test_ceo_boot.py -q -k fu144 && ! git show-ref --verify -q refs/heads/ensaio-outra`
- [ ] Item 15 (3.14) decidido pelo Owner e, se for para a VM, landado por SIGN.
  Check: `! grep -q -F "matrix.python-version != '3.14' && vars.VM_CI_ENABLED" .github/workflows/validate.yml`
- [ ] Item 16 (helper que mata o grupo no estouro + censo) landado livre, com os dois sítios do
  `test_install_sh_placeholders.py` convertidos.
  Check: `python3 -m pytest .claude/scripts/tests/test_install_sh_placeholders.py .claude/scripts/tests/test_subprocess_timeout_group_census.py -q -k fu144`
- [ ] Item 17 (W7ad) landado por SIGN: o ADR-158 emendado com a pasta nova e o comentário do
  `validate.yml` sem a pasta antiga (os dois sítios normativos).
  Check: `grep -q '_lib/harness_replay' .claude/adr/ADR-158-harness-config-gate.md && ! grep -n 'harness-config/replay' .github/workflows/validate.yml`
- [ ] Item 18 (U2-D) landado por SIGN, depois do U2-A, do U2-B e do U2-C.
  Check: `grep -qx 'status: ACCEPTED' .claude/adr/ADR-055-AMEND-4-*.md`
- [ ] Item 19 (F2, três levas) executado e registrado no LEDGER, cada leva contra a árvore com a sua cura.
  Check: `grep -q '^## F2 — estresse da W2.5' .claude/plans/PLAN-194/LEDGER.md`
- [ ] Item 20 (orçamento relativo + censo da classe) landado; o teste de `persona_demand_scan` passa num
  checkout com ≥ 76 ramos locais (ou numa fixture com N ramos sintéticos dentro do próprio teste).
  Check: `[ "$(git for-each-ref refs/heads | wc -l)" -ge 76 ] && python3 -m pytest .claude/hooks/_lib/tests/test_plan104_microbench.py -q` (mais o teste do censo, com o nome que a abertura fixar)
- [ ] Item 21 (doc da W6, FD-22) landado livre, com a frase da versão em 1.4.4 e os trechos do restore e do
  `--strict-against-counter` reconciliados com o FD-25 e o FD-26.
  Check: `git merge-base --is-ancestor 1e08dd90 HEAD && ! grep -q 'in v1.4.3' INSTALL.md && ! grep -q 'ceo-restore-listing' docs/DISASTER-RECOVERY.md`
