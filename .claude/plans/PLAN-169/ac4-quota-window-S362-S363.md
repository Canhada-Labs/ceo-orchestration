# PLAN-169-FOLLOWUP AC-4 — janela real de esgotamento (S361 noite → S363), registro falsificável

> Registro do item «Janela real (Q13-e)» do AC-4 de
> `PLAN-169-FOLLOWUP-quota-resume-and-probes.md`, escrito em 2026-10-09
> (S363). A janela é o trabalho longo que começou na S361. Tudo abaixo
> foi lido nos transcripts e no log de auditoria desta máquina; nada é
> estimativa. O nome do arquivo diz S362–S363 porque era o escopo
> pedido. O censo achou mais duas ocorrências na noite da S361, que
> também entram aqui. **Este arquivo NÃO decide o desfecho (a)/(b)/(c):**
> a §6 traz só o resultado proposto, e a decisão é do Owner.

## 0. Fontes e como reproduzir

- **Transcripts (fora do repositório, em `~/.claude/projects/<slug>/`).**
  `Lnnn` é o número da linha (base 1) no `.jsonl`. Os horários vêm do
  campo `timestamp` (UTC).
  - `<sessão 5d6890e3>` (noite S361): 14.259 linhas, sha256 `70f90c09b5c70d52b89e143622450cfe2b052626367ccc68b3b582ca096f0320`.
  - `<sessão 8a95c186>` (S362): 8.917 linhas, sha256 `72c8e9116044afa9307eae2c0037bd33973f50c8901c4ca0eca4ddd73cc4295f`.
  - `<sessão d876fa66>` (S363): o arquivo ainda cresce. O hash foi tirado
    com 11.464 linhas e a última conferência leu 11.665. O sha256 das primeiras 11.050 linhas é `bb31a78ebb96bc138b6d82f8c6d3e34493adb1e6ee2403827105b38cb8c4b299`.
    Esse prefixo fica estável enquanto o arquivo só receber acréscimos.
  - Subagentes: `<sessão>/subagents/agent-a<nome>-<hex>.jsonl`.
    Workflows: `<sessão>/subagents/workflows/wf_*/`, com `journal.jsonl`
    e um `.jsonl` por agente.
  - O CC apaga `*.jsonl` de topo depois de `cleanupPeriodDays`. Por isso
    este registro copia o texto literal e os horários.
- **Log de auditoria (só leitura).** O diretório vem de
  `runtime_paths.py --state-dir`. Os eventos citados estão em dois
  segmentos já rotacionados:
  - `audit-log-2026-10-3.jsonl` (sha256 `743b4933bd2877e7310585699cb29e182239da94979d136fb586e19f38d339bc`);
  - `audit-log-2026-10-5.jsonl` (sha256 `5d482c61966e3ac846432e041ffbb76e274ab4b9bc5319723ac917f9d8c9c791`).
    Foi rotacionado em `2026-10-09T14:37:55Z`, segundo o
    `audit-log.rotation-manifest.json`, e cobre `2026-10-02T23:39:17Z` →
    `2026-10-09T14:37:54Z`.

  Cada evento é citado pelo `record_id`.
- **Varredura.** Entram as linhas com `"error": "rate_limit"` (recusa),
  as linhas `system` informativas que contêm «Usage limit» (avisos do
  nativo) e as linhas `user` com `isMeta: true` e o texto de retomada.
  O censo cobriu os `.jsonl` de topo do diretório do projeto com mtime
  ≥ 2026-10-01. Contados em 2026-10-09T15:01Z, são 12: 7 são segmentos do
  log de auditoria (0 linhas `rate_limit`) e 5 são transcripts de sessão.
  Desses 5, 3 têm recusas (26 + 21 + 30 linhas `rate_limit`). Os totais
  por ocorrência da §2 somam exatamente esses números.
- **Versão do CC.** O registro usa o campo `version` de cada linha, que é
  a versão do processo que escreveu a linha. Ninguém rodou
  `claude --version` no instante de cada parada. Quando este registro
  foi escrito (2026-10-09 ~14:35Z), `claude --version` dava `2.1.295`.
- **Fuso.** O texto da recusa usa `America/Sao_Paulo`, que é UTC−3 (sem
  horário de verão). A conversão para UTC está na tabela. O texto dá o
  reset com precisão de minuto, então a latência «reset → retomada» é
  medida a partir do início desse minuto.

## 1. Estado efetivo do `autoContinueAtUsageLimit`

| Camada | Arquivo | Resultado (grep em 2026-10-09 ~14:35Z) |
|---|---|---|
| usuário | `~/.claude/settings.json` | existe, 0 ocorrências da chave |
| usuário (local) | `~/.claude/settings.local.json` | não existe |
| projeto | `.claude/settings.json` | existe, 0 ocorrências |
| local | `.claude/settings.local.json` | existe, 0 ocorrências |
| managed | `/Library/Application Support/ClaudeCode/managed-settings.json` | não existe |

- Para `.claude/settings.json` e `templates/`, o
  `git log -S autoContinueAtUsageLimit` não devolve nenhum commit: a
  chave nunca foi versionada.
- **Valor efetivo: ligado (chave ausente).** Os gates de servidor não
  foram medidos. O próprio harness dá a evidência direta, nas três
  sessões. Quando recusa, ele escreve uma linha `system` com
  `Usage limit reached · continuing automatically at <h> · esc to cancel`.
  Quando retoma, escreve `Usage limit reset · continuing automatically`,
  seguida de uma linha `user` `isMeta` com
  `Your claude.ai usage limit has reset. Continue the task you were working on when the limit was reached; do not repeat work that is already complete.`
- **Limite desta seção.** `~/.claude/settings.json` e
  `.claude/settings.local.json` mudaram em 2026-10-08/09 (mtime). O grep
  mostra o estado de agora, não o da S361 nem o da S362. Para essas
  janelas, a evidência são os avisos do harness citados na §2.

## 2. Ocorrências

Textos literais das recusas (as variações estão só no horário):

- **S** = `You've hit your session limit · resets <h> (America/Sao_Paulo)`
- **G** = `You've hit your individual spend limit · run /usage-credits to ask your admin for a higher limit · your session limit resets <h> (America/Sao_Paulo)`
- **W** = `You've hit your weekly limit · resets Oct 12 at 8am (America/Sao_Paulo)`

| # | Sessão / CC | 1.ª recusa na sessão principal | Reset anunciado (UTC) | Retomada da sessão principal: instante e autor | Latência | Recusas na principal |
|---|---|---|---|---|---|---|
| E1 | S361 / 2.1.287 | 2026-10-02 01:18:58Z, **S** «12:20am» (L5522) | 03:20Z | 03:21:29Z, **nativo** (L5632 + L5638) | 89 s | 13 |
| E2 | S361 / 2.1.287 | 2026-10-02 05:20:09Z, **S** «5:20am» (L9397) | 08:20Z | 08:21:38Z, **nativo** (L9578 + L9579) | 98 s | 13 |
| E3 | S362 / 2.1.287 | 2026-10-02 23:31:30Z, **G** «9:30pm» (L3411) | 00:30Z (03/10) | 23:35:24Z, **Owner**: `/login` → `Login successful` (L3420–3421), seguido de um prompt do Owner (L3424) | — | 2 |
| E4 | S362 / 2.1.287 | 2026-10-03 01:01:47Z, **S** «1:30am» (L5565) | 04:30Z | 04:31:17Z, **nativo** (L5764 + L5765), mas **recusado 1,4 s depois** por **G** «3:20am» (L5773, 04:31:18Z). Nova retomada **nativa** às 06:20:49Z (L5776 + L5777) | 77 s; depois 49 s | 9 |
| E5 | S362 / 2.1.287 | 2026-10-03 06:49:25Z, **G** «8:20am» (L7430) | 11:20Z | 11:21:26Z, **nativo** (L7469 + L7470) | 87 s | 10 |
| E6 | S363 / 2.1.295 | 2026-10-09 01:51:04Z, **S** «2:10am» (L3418) | 05:10Z | 05:11:05Z, **nativo** (L3515 + L3516) | 65 s | 7 |
| E7 | S363 / 2.1.295 | 2026-10-09 06:58:52Z, **S** «7:10am» (L5937) | 10:10Z | 10:11:23Z, **nativo** (L6081 + L6082) | 83 s | 9 |
| E8 | S363 / 2.1.295 | 2026-10-09 12:59:08Z, **G** «2pm» (L10088) | 17:00Z | 13:57:32Z, **Owner**: `/login` (L10136–10137), seguido de um prompt do Owner (L10139, 13:57:50Z). Primeira ferramenta às 13:58:22Z (L10153) | — | 13 |
| E9 | S363 / 2.1.295 | 2026-10-09 14:21:33Z, **W** (L10765) | 2026-10-12 11:00Z | 14:24:48Z, **Owner**: reset da cota semanal. O 1.º turno bem-sucedido foi disparado por um `task-notification` (L10775 → L10780). O Owner afirma o reset em L10782 (14:24:52Z) | — | 1 |

A coluna «Recusas na principal» conta as linhas `rate_limit` da
sessão principal entre a 1.ª recusa e a retomada. **Isso é contagem de
linhas, não de turnos perdidos.** Cada linha é a recusa de um turno
disparado por mensagem de colega, `task-notification` ou cron. Esta
contagem não diz se o gatilho foi tratado depois. Além disso, a sessão
principal ainda executou ferramentas DENTRO da janela, durante a
tolerância do harness:

- **E2:** 2 `Bash` (L9407, 05:27:28Z; L9452, 05:29:47Z);
- **E4:** 6 chamadas entre 01:02:47Z e 01:07:42Z (L5571–L5689): 3
  `Edit`, 2 `Bash` e 1 `SendMessage` (L5572, para `r3-refute-fd07-r1`);
- **E7:** 1 `Bash` (L5946, 07:00:41Z).

Nas outras 6 ocorrências não há linha de `assistant` sem erro entre a
1.ª recusa e a retomada.

### Aviso do nativo e cron do CEO, por ocorrência

- **E1.** O nativo foi armado em L5523: «continuing automatically at
  12:20am». O cron recorrente do CEO `ebd4acfb` (`*/20 * * * *`, criado
  em L2645) continuou disparando durante a parada, e cada disparo foi
  recusado. Conferi dois: L5600 `scheduled_task_fire` 01:49:13Z → L5602
  recusa, e L5607 → L5609. Os outros, de 20 em 20 min, têm o mesmo
  horário e não foram conferidos um a um. Pelo mesmo padrão, o próximo
  disparo seria às 03:29Z; o nativo chegou antes.
  `prompt_submitted` 03:21:29Z: `audit-log-2026-10-3.jsonl` L1507,
  `record_id` `f55a79a35e114cfeb1815f17937b083f`.
- **E2.** O nativo foi armado em L9392, 05:20:07.613Z. O cron `ebd4acfb`
  ainda estava ativo (foi cancelado em L12990, 12:09:20Z). O disparo de
  08:09Z foi recusado (L9572 `scheduled_task_fire` → L9574). Pelo padrão
  de 20 em 20 min, o seguinte seria às 08:29Z; o nativo chegou antes.
  `prompt_submitted` 08:21:38Z: `audit-log-2026-10-3.jsonl` L10527,
  `da580f46d9af4622847d8b5b79660942`.
- **E3.** O nativo foi armado em L3412 («at 9:30pm»). O Owner trocou de
  conta 55 min ANTES do reset anunciado, então **o nativo não foi
  exercido**: o desfecho está confundido pela troca de conta. O cron do
  CEO `8e0a15f9` (`34 21 2 10 *`, isto é, 00:34Z) só entrou na fila
  depois da retomada (L5061, 00:34:00Z).
- **E4.** O nativo foi armado em L5558, 01:01:46Z. Não havia cron do CEO
  armado para 04:30Z. A 1.ª retomada nativa (`prompt_submitted`
  04:31:17Z, `audit-log-2026-10-5.jsonl` L1461,
  `adad0d3225bc43c99f82898e7d2e77c1`) caiu num limite de gasto ainda
  ativo. Depois dessa recusa, o transcript não tem nova linha «Usage
  limit reached · continuing automatically» (L5774 já é das 06:20:49Z),
  mas a 2.ª retomada nativa veio mesmo assim (L1465,
  `2b667f05dfea45d4965ea0a48eabad1e`).
- **E5.** O nativo foi armado em L7431. O cron do CEO `0aba18c4`
  (`23 8 3 10 *`, isto é, 11:23Z; criado em L7030) só entrou na fila às
  11:44:48Z (L7892), depois do nativo. `prompt_submitted` 11:21:26Z: L2111,
  `d25236ab7a9944048b7e3391e2ef5c6a`.
- **E6.** O nativo foi armado em L3416, 01:51:04Z. O cron do CEO
  `cdfbdbf7` (`13 2 9 10 *`, isto é, 05:13Z; criado em L1566) entrou na
  fila às 05:13:38Z (L3706) e foi entregue às 05:16:29Z (L3852;
  `prompt_submitted` 10-5 L5086 05:16:29Z,
  `2879ae0b877145ff8192ef197e7b2c9d`), 5 min DEPOIS do
  nativo. `prompt_submitted` 05:11:05Z: L4898,
  `344c12e27c1348a1a3df9f73f1d61065`.
- **E7.** O nativo foi armado em L5938. O cron do CEO `b7bca1d5`
  (`13 7 9 10 *`, isto é, 10:13Z; criado em L5874) entrou na fila às
  10:14:32Z (L6279) e foi entregue às 10:15:51Z (L6387;
  `prompt_submitted` 10-5 L7771 10:15:52Z,
  `32135d8e95f840768e7304731ba0c47b`), depois do nativo.
  `prompt_submitted` 10:11:23Z: L7632, `42ad4c73e4854ad3acd19714ce124088`.
- **E8.** O nativo foi armado em L10089 («at 2pm»). O Owner trocou de
  conta 3 h ANTES do reset, então **o nativo não foi exercido**
  (confundido). Uma troca de conta anterior, às 12:00:19Z (L8038), não
  teve recusa antes dela no transcript.
- **E9.** **Não há aviso «continuing automatically» depois desta
  recusa.** A última linha com esse texto no transcript é L10089
  (conferido até L11665, que também não tem nenhuma recusa depois de
  L10765). O
  transcript não registra o instante exato do reset feito pelo Owner; o
  limite superior é o 1.º turno bem-sucedido, às 14:24:48Z.

Comportamento do harness em volta da recusa, observado mas não
analisado aqui. Há mensagens `isMeta` de dois tipos; o censo abaixo
cobre os 3 transcripts:

- «[Usage limit reached; a short grace allowance remains, then this turn
  is cut off without warning. …]»: S361 L5560, L9345, L9405, L9445; S362
  L5504, L5594, L5638; S363 L3365, L5944.
- «[Earlier usage-limit notes no longer apply. …]»: S361 L5567, L9395,
  L9439, L9486; S362 L5564, L5633, L5743; S363 L3417, L5989.

As chamadas de ferramenta feitas durante essa tolerância estão listadas
logo abaixo da tabela de ocorrências.

### Subagentes (time em processo, `taskKind: in_process_teammate`, e agentes gerais)

| # | Caíram (linha `rate_limit` no transcript do subagente) | Quem os retomou |
|---|---|---|
| E1 | 4 agentes `general-purpose` sem nome (`ad388a57…` 01:27:31Z, `a34ce364…` 01:29:44Z, `abf3a7eb…` 01:29:46Z, `a57bfea1…` 01:34:52Z) | `SendMessage` do CEO, 4/4, entre 03:22:17Z e 03:22:25Z (L5677–5680), depois da retomada nativa da principal |
| E2 | nenhum | — |
| E3 | `fd03-flaky-chain-test` (21:24:13Z; a notificação só chega à principal às 23:31:30Z, L3410) | `SendMessage` do CEO às 23:38:57Z (L3581) |
| E4 | `r3-refute-fd07-r1` (01:12:38Z), `fd07-spool-verifiers` (01:15:01Z) | `fd07-spool-verifiers`: `SendMessage` às 06:21:55Z (L5803). **`r3-refute-fd07-r1` não recebeu nenhum `SendMessage` depois da queda**: o último é L5572, 01:02:53Z, até o fim do arquivo (L8917) |
| E5 | `fd21-m1-c9-e1`, `fd25-ceo-restore-fixes`, `fd18-w5c-derivator`, `fd26-verify-chain-strict` (06:49:25Z–06:50:29Z) | `SendMessage`, 4/4: L7594–7595 entre 11:23:10Z e 11:23:11Z, L7795 às 11:25:21Z, L7846 às 11:44:21Z |
| E6 | `k1` (02:47:35Z), `mat-w4` (02:56:11Z) | `SendMessage`, 2/2, às 05:11:32Z e 05:11:34Z (L3554–3555) |
| E7 | `mat-w62` (07:28:58Z) | `SendMessage` às 10:11:50Z (L6100) |
| E8 | 9 agentes: `mat-w2b`, `mat-w62`, `w5b`, `mat-w2a`, `w7a`, `lote`, `r-w2c-a`, `r-w2c-b`, `r4` (13:04:37Z–13:06:59Z) | `SendMessage`, 7/9, entre 13:59:29Z e 13:59:40Z (L10214–10220). **`r-w2c-a` e `r-w2c-b` não foram retomados.** Às 14:35:18Z e 14:35:23Z (L11253–11254) receberam uma tarefa NOVA, a rodada 2, com a instrução de não revisar mais a rodada 1, que ficou abandonada. Conferido até L11665 |
| E9 | 8 agentes: `r-w7a-b`, `mat-w2b`, `lote`, `mat-w62`, `r-w05v`, `r4`, `c-w2c`, `r-w7a-a` (14:21:32Z–14:22:44Z) | `SendMessage`, 8/8, entre 14:25:57Z e 14:26:06Z (L10876–10883) |

**Em nenhuma ocorrência o harness retomou um subagente sozinho.** Dos
31 que caíram, 28 foram retomados por `SendMessage` do CEO, sempre
depois de a principal voltar. Os outros 3 não foram retomados: um nunca
mais foi contatado (E4), e dois receberam depois uma tarefa nova, com o
trabalho interrompido abandonado (E8).

### Caminho Workflow

- **Exercido uma vez, na E1.** No `wf_f525c764-c76`, o agente
  `a791a56f…` recebeu **S** às 01:27:41Z, e o seu transcript termina
  nessa linha (L626 de 626). O runtime abriu um agente NOVO (`ade7a6fa…`)
  para o MESMO passo (mesma `key` no `journal.jsonl`) às 03:21:07Z.
  Isso é 67 s depois do reset e 22 s antes da retomada nativa da
  principal. O passo foi refeito do zero, e os 8 min do agente recusado
  foram perdidos. O journal registra 1 `launched`, 3 `started` e 2
  `result`, e **nenhum** evento `workflow_rate_limit_wait`. O workflow
  terminou `completed` às 03:42:02Z (`task-notification`, L6162 da
  principal). O journal não tem timestamps; os horários vêm da 1.ª e da
  última linha de cada agente.
- Os outros workflows da janela não tiveram recusa: 14 na S361, 5 na
  S362 e 1 na S363 (`wf_8ff9b360-626`, com 9 `started` e 9 `result`).
  Nenhum dos 21 journals da janela tem um evento com
  `type: workflow_rate_limit_wait`. Os tipos presentes são só `launched`
  (21), `started` (171) e `result` (170). O único journal com `started`
  ≠ `result` é o `wf_f525c764-c76` (3/2), o da E1. A string aparece só
  como texto:
  - dentro do campo `result` de 2 journals (`wf_6efdc6cb-9db` L196, S361;
    `wf_8ff9b360-626` L14, S363);
  - em transcripts de agente de 3 workflows (`wf_6efdc6cb-9db`,
    `wf_949bca28-45d`, `wf_8ff9b360-626`).

## 3. Respostas às perguntas do AC-4

1. **Quem retoma a sessão principal.** O nativo retomou sozinho em 6 das
   9 ocorrências (E1, E2, E4, E5, E6, E7): 7 eventos de retomada, entre
   49 e 98 s depois do minuto anunciado. Toda retomada nativa tem um
   `prompt_submitted` no mesmo segundo (7/7, `record_id` na §2). O
   nativo chegou sempre ANTES do cron do CEO, quando havia um (E1, E2,
   E5, E6, E7). Nas outras 3, quem retomou foi o Owner: na E3 e na E8 por
   troca de conta antes do reset (o nativo estava armado e não foi
   exercido); na E9 pelo reset da cota semanal, e o harness não escreveu
   o aviso do nativo.
2. **Turnos perdidos na principal: não medido.** A coluna «Recusas na
   principal» conta linhas `rate_limit`, não turnos perdidos. Durante a
   tolerância, a principal ainda trabalhou dentro da janela (E2, E4 e
   E7; lista na §2). O conteúdo que disparou cada turno recusado
   continua no transcript, e a mensagem de retomada pede para não
   repetir trabalho. Não conferi, um a um, se cada gatilho recusado foi
   tratado depois da retomada.
3. **Limite 1: subagentes não retomam nativamente.** Ver a tabela de
   subagentes: 0 retomados pelo harness, 28 de 31 por `SendMessage` do
   CEO e 3 não retomados (um nunca mais contatado; dois com o trabalho
   interrompido abandonado e uma tarefa nova).
4. **Limite 2: a retomada nativa pode cair num teto de gasto ainda
   ativo.** É a E4: a retomada das 04:31:17Z foi recusada em 1,4 s por
   outro limite, e só a retomada nativa seguinte (06:20:49Z) valeu.
5. **Workflow.** Uma vez (E1): o runtime redespachou o passo recusado
   depois do reset, sem `workflow_rate_limit_wait` e com o trabalho
   parcial refeito.

## 4. Sonda W4.2.0(a) — resposta parcial: `UserPromptSubmit` dispara para mensagem de colega?

**Método** (`<sessão d876fa66>`, corte `timestamp < 2026-10-09T14:30:00Z`):

1. Turnos de colega: linhas `type: user`, sem `isMeta`, sem
   `tool_result`, cujo texto contém `<teammate-message`. São **140**.
2. Eventos: `action: prompt_submitted` com `session_id` d876fa66 em
   `audit-log-2026-10-5.jsonl`. São **50** no segmento inteiro.
3. Pareamento por |Δt| ≤ 5 s (repetido com ≤ 2 s).

**Resultado:** **0 de 140** turnos de colega têm `prompt_submitted`, nos
dois raios. Controles positivos na mesma janela:

- linhas `<task-notification`: 21 de 21 pareadas (±2 s);
- prompts digitados pelo Owner: 7 de 7. Uma 8.ª linha (L7536) é o resumo
  de compactação e não tem par.

Os 16 `prompt_submitted` sem linha `user` a ±5 s caem todos a ≤ 3 s de
uma `queue-operation`/`queued_command` com prompt do Owner ou
`task-notification` entregue no meio do turno. Nenhum cai junto de uma
`<teammate-message`, e nenhuma `queue-operation` da janela carrega
`<teammate-message`.

O emissor não filtra conteúdo: `UserPromptSubmit.py:215-256` emite para
todo prompt, salvo kill-switch. O `audit-log.errors` tem 0 linhas com
`UserPromptSubmit` em 2026-10-09.

**Por que a resposta é parcial:**

- (i) Os colegas medidos são `in_process_teammate`, no mesmo processo.
  Contei 57 `meta.json` em `subagents/` em 2026-10-09, entre 14:35Z e
  14:45Z, todos desse tipo. Às 15:02Z eram 58: o acréscimo é o `r-ac4`,
  revisor deste registro, criado depois dele e do mesmo tipo. Mensagem de outra
  sessão, terminal ou máquina não foi exercitada.
- (ii) A ausência do evento não separa «o hook não disparou» de «o hook
  disparou e falhou antes de emitir». Os controles e o zero de erros
  tornam improvável uma falha sistemática, mas isso não foi medido.
- (iii) Não reproduzi a contagem preliminar da sessão, «133 de 134»
  (1 com evento). Com o método acima, nenhum dos 140 tem evento.

## 5. O que este registro NÃO conferiu

- O `claude --version` no instante de cada parada; usei o campo
  `version` das linhas.
- O `resets_at` do sidecar antes de cada parada. O sidecar é
  sobrescrito e não guarda histórico. Só na E6 há uma leitura do CEO na
  fila efêmera da sessão («reset 05:10Z»), coerente com a recusa.
- O estado das camadas de settings do usuário e local durante a S361 e a
  S362 (§1).
- Os gates de servidor do nativo.
- Se a recusa deixa rastro na cadeia HMAC nesta janela.
  `w4.1-probe-S328.md` §1 mediu «nenhum» na S328; aqui não repeti.
- Se a cota semanal da E9 foi resetada antes das 14:24:48Z, e quando
  exatamente (o ato do Owner fica fora do transcript).
- Transcripts de outros projetos do mesmo `$HOME`.

## 6. Resultado proposto (NÃO decidido)

**Resultado proposto: (a) para a sessão principal, com 2 limites
declarados (subagentes não retomam nativamente; retomada nativa pode
cair num teto de gasto ainda ativo) — decisão do Owner pendente.**

As caixas do AC-4 seguem desmarcadas e o `status` do plano não muda.
Fatos que pesam na decisão e não cabem na frase:

- E3, E8 e E9 não testam o nativo, porque o Owner agiu antes do reset.
- E9 é um limite semanal, e nela o harness não armou a retomada.
- O caminho Workflow retomou uma vez (E1), mas refez o passo do zero.
