---
id: PLAN-190
title: Execução autônoma utilizável nos consumidores — preservar trabalho pago, recuperar progresso, aprovar por código
status: executing
created: 2026-09-17
owner: CEO
reviewed_at: 2026-09-17
reviewed_by: "Owner (assinatura GPG do sentinel da W1, chave AE9B236F)"
related_commits:
  - 075beed9d5f3e729b3abd5b7a7140dc16e214249
depends_on: []
level: L3
budget_tokens: "W0 feito (S354, ~0 pago: instrumentos stdlib); W1 150-300k + debate r1; W2 200-400k; W3 150-250k; W4 100-200k; W5 100-200k; W6 e2e no smoke (CI). Teto do plano: 1,5 M de agente + cerimônias."
budget_sessions: "W0 1 (feita); W1 1-2; W2 1-2; W3 1; W4 1; W5 1; W6 acoplada a cada wave"
context_risk: high
external_wait: "cerimônia GPG do Owner por wave canônica (W1, W2-guard, W4-enforce, W5-hook); nenhuma dependência externa de fornecedor — o que depender do runner nativo fica DECLARADO como limitação (§O que este plano NÃO faz)"
eta_calendar: "W1 assinável em 1-2 sessões após debate r1; W2-W3 na semana seguinte; W4-W5 medir antes de impor"
tags: [workflow, recovery, quota, mutation-testing, approval-gate, distribution, consumer]
---

## Context

**Ordem do Owner (2026-09-17, S354):** «corrigir o ceo-orchestration para que a execução autônoma seja
utilizável nos repositórios consumidores» — investigar, implementar e validar, sob a governança vigente;
não encerrar em estudo. JEV fica como hipótese futura: nenhuma integração, dependência ou implementação.

**Evidência (repositório consumidor, código financeiro; esteira autônoma 15→17/09/2026; medida nesta
sessão com instrumentos stdlib sobre os transcripts locais — nomes do consumidor NÃO entram aqui):**

| medida | valor | fonte |
|---|---|---|
| janela do incidente | 38,2 h (2026-09-15T23:00Z → 09-17T13:10Z) | relato do operador, reconciliado |
| runs de Workflow com turnos na janela | 35 (mediana 13 agentes e 205 mi de cache read por run) | transcripts |
| custo API-equivalente na janela | ≈ US$ 4,3k (subagentes 3,96k; 24.639 turnos; ≈ 248k por turno) | coletor `ceo-cost-transcripts.py` |
| prefixo de abertura por subagente | p50 154k / p90 166k tokens (n=495) | `tools/audit_collector.py` |
| pico de contexto por subagente | p50 280k / p90 358k | idem |
| `totalTokens` que o runner reporta por run | = soma dos PICOS dos agentes (razão 1,00 na mediana, 697 runs); o consumo deduplicado é 56× maior (p10 24×, p90 162×) | `wf_*.json` × transcripts |
| fases iniciadas sem resultado («perdidas») | **643 de 4.147 starts (15,5 %)**, em 274 de 699 runs | `journal.jsonl` do runner |
| reexecuções (mesma chave iniciada > 1 vez) | 420 chaves; 666 starts extras (16 % dos starts) | idem |
| mortes por quota | 10 em 34 h; tipos vistos: `rate_limit`/`five_hour`, `session limit`, `spend limit`, `org_spend_cap_reached` | relato + grep dos transcripts |
| merges na main | 4 de 23 fatias planejadas (`args` do consumidor listam 27 entradas: fatias + costuras + relançamentos) | git do consumidor |
| framework instalado | **1.4.0** via `upgrade.sh` (10/09; o relato dizia rc.4), perfil `core,frontend,fintech`, 96 registrações de hook, 59 hooks; **nenhum matcher para a tool `Workflow`**; nenhum TTL/omit/autocompact configurado | `.claude/.install-state.json` do consumidor |
| o que o harness persiste por run | `<session>/workflows/wf_<id>.json` ao TÉRMINO (completed/killed/failed): script inteiro, `scriptPath`, `args` em 552/697 runs, `totalTokens`, `phases`, `defaultModel`; **nada no lançamento; sem hash do script, sem revisão do código, sem versão da CLI**; `subagents/workflows/<wf>/journal.jsonl` = cache de resultados por chave `v2:<hash>` (`started`/`result`) | inspeção dos arquivos |

Fatos do relato que a medição CONFIRMA: prompt do script editado com runs em voo ⇒ chave de cache de
todas as fases muda ⇒ reimplementação (17 fatias); args reconstruídos de memória ⇒ 11 regressões de
fase; args exatos ⇒ 12/12 retomadas na fase certa; mutantes plantados NA árvore de trabalho e
deixados por morte/pausa (13); «verde» declarado com nota do revisor cruzado abaixo da barra (3); 9
falsos «PROVAS-INCOMPLETAS» por comparar NOME DE FUNÇÃO com CAMINHO; 18 «pinos» derivados
compartilhados ⇒ 20-40 min de costura por merge; o rito pegou defeitos financeiros REAIS (valor a
preservar). Fatos que a medição CORRIGE: os «250-650k por fase» e as taxas por hora do relato estão na
unidade do runner (soma de picos), não em consumo; «56k por agente» era uma sonda, a distribuição é
p50 154k.

**Separação exigida pela ordem (defeito do framework × customização local × limite do Claude Code):**
- *Limite do Claude Code:* não há checkpoint dentro de um `agent()` de Workflow; `agent()` não passa
  por `check_agent_spawn`; o runner espera `resetsAt` da conta antiga; o cache de resultados é do
  runner (chave = hash de prompt+opts); `Workflow.totalTokens` = soma de picos.
- *Customização local (script do consumidor):* mutantes na árvore; «verde» por P0/P1 sem nota mínima;
  matcher de testes por caminho; pinos como constantes; `effort: 'max'` em todas as fases.
- *Defeito/lacuna do framework:* nenhuma superfície observa o lançamento de um Workflow (sem matcher,
  sem ledger, sem guard de resume); nenhum lock de escritor por worktree; nenhum contrato de
  aprovação/evidência executável para scripts de consumidor; quota nativa lida pela statusline mas
  não persistida nem usada para admissão; instrumentos de custo advisory sem ligação a entrega.

## Goal

Mais trabalho **aprovado por unidade de quota**, com menos reexecução, menos fase perdida e sem
enfraquecer cético, revisão cross-model ou o perímetro financeiro (Opus/Fable). Métricas (baseline no
consumidor, S354): fases perdidas 15,5 % dos starts; reexecuções 16 %; tokens por entrega aprovada
NÃO medido (definição de «aprovada» = item W0.2); tempo esperando capacidade NÃO medido; quantidade de
agentes ativos NÃO é indicador.

## Thesis

O menor conjunto de mudanças que elimina as perdas DEMONSTRADAS é, nesta ordem: (1) tornar cada
lançamento e retomada de Workflow recuperável e verificável ANTES do despacho — args literais, hash do
script, revisão do código, opções efetivas — com um guard que recusa retomar sobre entradas diferentes;
(2) tirar as mutações da árvore de implementação e impedir dois escritores; (3) computar aprovação por
código a partir de evidência tipada; (4) admitir trabalho por fase pesada com a quota nativa como
sinal, distinguindo reset de teto de gasto; (5) automatizar costura e reduzir contexto por fase. Tudo
stdlib, distribuído pelo mecanismo existente (`templates/settings/` por cerimônia + enumeração de
`.claude/hooks/` no manifesto + `upgrade.sh`), validado por testes e pelo smoke-install em consumidor
isolado.

## Items

### W0 — Inventário e baseline  [P0] — FEITO (S354)
- Inventário do consumidor (tabela acima); auditoria do coletor (`docs/research/s354-token-consumption-study/03-collector-audit.md`).
- Falta **W0.2**: definição executável de «entrega aprovada» (merge em `main` com gate verde + veredito do
  revisor cruzado dentro da política) e o roteiro de medição «quota/tokens por entrega» =
  `ceo-cost-transcripts.py --by session` × ledger de lançamentos (W1) × commits. Entregável: seção no
  `docs/workflow-recovery.md` + script `ceo-launches.py report`.

### W1 — Lançamentos e retomadas recuperáveis  [P0]  (pacote canônico: cerimônia)
**Estado (S354, 17/09):** v6.3 construída na sombra `p190-w1-v6` e provada; patch de 24 paths em
`PLAN-190/w1/p190-w1.patch`. Histórico de revisão: debate r1 = 3× ADJUST → PROCEED (design-coherent);
rail Codex r1 NO-GO 7, r2 NO-GO 3, r3 NO-GO 2, r4 NO-GO 4 — a terceira rodada seguida na classe
«estado em disco lido de volta para dentro da decisão» (token de override: rota, parse, corrida,
exceções; manifesto sem validação; snapshot sem conferência de hash). Pela regra de teto por classe a
decisão foi ao Owner, que escolheu trocar a arquitetura (registro em OQ-6). A v6 remove o token do
disco (override declarado na própria chamada ou no ambiente), valida o manifesto lido de volta
(`manifest_problem`), torna o guard total (exceção = inconclusivo registrado; falha de escrita não
desfaz bloqueio) e serializa em ASCII. Uma revisão adversarial multi-lente (workflow `wf_bf51d949-ac2`:
5 lentes Opus, 2 refutadores por achado, crítico de completude) sobre a v5 achou, entre os que
sobrevivem à v6: um P0 de CI vermelho pós-land (a lista ratificada do teste do template `user` não
incluía o hook — a bateria da cerimônia não rodava as suítes do CI), leitura de `scriptPath` sem
limite de tipo e tamanho, índice sem reparo de fronteira, advisory que mandava re-emitir uma chamada
que prossegue, CLI que não achava o ledger a partir de subdiretório, plugin que registraria o guard
sem o CLI de recuperação, texto do sentinel e da mensagem de commit maiores que a entrega, e oito
lacunas de teste. Todos curados na v6.1–v6.3 com regressões; prova por mutação com 31 mutantes (um
equivalente declarado). O script de cerimônia foi reordenado (nada assinado antes da bateria; sentinel
restaurado e `.asc` removida em qualquer falha) e a bateria passou a rodar as suítes do `pytest.ini`
como o CI, comparando o conjunto exato de falhas contra `suite-baseline.txt` medido no main por
`measure-suite-baseline.sh`, com uma nova tentativa isolada para instabilidade conhecida. Rail r5 =
NO-GO com 3 (construção fora da totalidade, hash ausente aceito, breadcrumb perdido); o crítico de
completude do workflow achou lacunas de desenho que nenhuma lente cobriu — ordem das chaves dos args
perdida na forma canônica (o `relaunch` imprimia outra ordem), retomada DELIBERADA (`args.resume`)
tratada como perda e motivo que exagerava a reexecução, avisos que não chegavam ao modelo, run id por
primeira ocorrência, leituras e escritas do CLI sem limite — e a sonda real do harness confirmou os
fatos do substrato (`.script` aceito, ordem preservada, `Run ID:` no lançamento e na retomada, mesmo id).
Curados na v6.4–v6.5 com regressões e mutação (47 mutantes, 5 equivalentes declarados). **Regra de
parada aplicada (17/09, após o Owner perguntar se a sessão estava em loop):** o rail r6 é a RODADA FINAL
— reprova só por P0 ou por afirmação falsa no texto assinado; P1/P2 novos viram anexo declarado e
W1.1 depois da assinatura (a regra «rodada final com anexo» que o Owner ratificou para o corte da rc.1
em 10/09). Motivo: r4 e r5 acharam P2 cada vez mais estreitos, o padrão de retorno decrescente já
registrado, e a revisão adversarial custou ≈ 12,5 M de tokens de subagentes. **Rail r6 (final):
nenhum P0**; quatro frases do texto assinável contradiziam o código e foram corrigidas NO TEXTO, sem
mudança de comportamento; um P2 de implementação (`relaunch --out` sem conferir escrita parcial) vai
para a **W1.1**, declarado no anexo do sentinel. Ensaio completo da cerimônia (clone separado, suítes do
CI contra a linha de base) verde sobre a v6.5 e repetido sobre o patch com as correções de texto. **LANDADA em `075beed9` (17/09/2026, assinatura GPG do Owner sobre a âncora `440a5306`, patch
`02e8831f…`).** A cerimônia exercitou a própria cura de recuperação: a primeira execução falhou no GPG
(trava velha do chaveiro deixada por um processo morto em 09/09) e desfez tudo — patch revertido,
sentinel restaurado, nenhuma assinatura pela metade; removidas as travas órfãs, a segunda execução
passou. Duas instabilidades apareceram sob execução paralela e passaram na nova tentativa isolada que a
bateria faz (o mecanismo funcionou em campo). Push e adoção nos consumidores seguem como decisão do
Owner. Segue a **W1.1** (`PLAN-190-FOLLOWUP-relaunch-out-partial-write`).
Paths (≤ 8): `.claude/hooks/_lib/launch_ledger.py` (C), `.claude/hooks/check_workflow_launch.py` (C),
`.claude/settings.json` (C, matcher `Workflow` em PreToolUse e PostToolUse), `templates/settings/settings.base.json`
(C, mesma registração — o `user` deriva por subtração), `.claude/scripts/ceo-launches.py` (livre),
`.claude/hooks/tests/test_check_workflow_launch.py` (livre), `tests/unit/test_launch_ledger.py` (livre),
`docs/workflow-recovery.md` (livre).
- **Persistir ANTES do despacho** (PreToolUse `Workflow`): `launch_id`, instante, `session_id`, `cwd`,
  `sha256` + tamanho do script (texto inline ou `scriptPath`), `args` como JSON LITERAL (campo ausente
  fica ausente; `null` fica `null`), `resumeFromRunId`, `name`, revisão do código (`git rev-parse HEAD`
  + `git status --porcelain` vazio/não do `cwd`), versão da CLI se disponível no evento, perfil de
  cerimônia. Arquivo por lançamento em `<state-dir>/launches/<launch_id>.json` (escrita atômica,
  `FileLock`) + índice `launches.jsonl`. Evento de auditoria `workflow_launch_recorded`.
- **Vincular ao run** (PostToolUse `Workflow`): extrai o `wf_<id>` da resposta e grava `run_id` no
  manifesto; se a resposta trouxer o `scriptPath` persistido pelo harness, grava também.
- **Guard de retomada** (forma final após debate r1 + rail r1, `PLAN-190/debate/round-1/consensus.md`):
  com `resumeFromRunId`, carrega o manifesto vinculado a esse run e compara `sha256` do script e
  `args` literal. `args` diferentes ⇒ **bloqueia** com motivo SÓ de contagens (a lista de chaves fica
  no manifesto — canal instruction-adjacent fechado por remoção); script diferente com `args` iguais
  ⇒ advisory (`systemMessage`; `CEO_WORKFLOW_SCRIPT_GUARD=enforce` bloqueia); com `args` iguais, hash
  indisponível ⇒ inconclusivo (nunca bloqueia, nunca é `match`); manifesto lido de volta que falha na
  validação ⇒ inconclusivo; exceção no guard ⇒ inconclusivo registrado; manifesto vinculado por heurística ⇒ advisory, de
  args OU de script (vínculo heurístico nunca sustenta bloqueio; a advisory nomeia a rota `bind`);
  tentativa bloqueada fica no índice (`blocked: true`) e nunca é candidata ao vínculo por único pendente.
  Rotas: `ceo-launches.py relaunch <run>` (chamada exata a partir do SNAPSHOT dos bytes do script,
  recusada com rc 7 se o registro falhar na validação); override numa rota só e NUNCA em estado no
  disco (OQ-6): `description` da própria chamada com o prefixo exato `CEO_WORKFLOW_RESUME_FORCE:` e
  motivo, ou `CEO_WORKFLOW_RESUME_FORCE=1` no ambiente — registrado como `mismatch_forced` com origem e
  motivo, anunciado;
  `CEO_WORKFLOW_RESUME_GUARD=0` (advisory mantendo o ledger) /
  `CEO_WORKFLOW_LEDGER=0` no ambiente do harness. Sem manifesto vinculado ⇒ registra e segue. Falha de
  infraestrutura ⇒ `{}` (fail-open; não é matcher de segurança).
- **Manifesto antes de qualquer coisa lenta**: escrita atômica do manifesto + snapshot PRIMEIRO; a
  revisão git entra depois com orçamento de 1,2 s e `--no-optional-locks` (desconhecida em falha).
- **Vínculo sem adivinhação**: por `tool_use_id` exato; sem `tool_use_id`, só quando há UM lançamento
  pendente na sessão; o resto vira `orphan` (fechado à mão por `bind`); `bind_method` registrado;
  rebind invalida a associação anterior.
- **CLI** `ceo-launches.py list|show <run|launch>|relaunch <run>|check --script … --args … --resume <run>|report`:
  `relaunch` imprime a chamada EXATA (scriptPath + hash esperado + args literal) — nunca reconstruir de
  memória; `check` é o mesmo predicado do guard, utilizável pelo rito do consumidor mesmo antes de o hook
  chegar lá.
- **Testes**: registro antes do despacho; ausente ≠ `null` nos args; hash muda ⇒ bloqueio nomeado; args
  mudam ⇒ bloqueio nomeado; `FORCE` registra e libera; sem manifesto ⇒ advisory; `{}` em falha de infra;
  isolamento por `TestEnvContext`.
- **Distribuição**: hook chega pela enumeração de `.claude/hooks/` no manifesto; registração pelo
  template `settings.base.json` (o `upgrade.sh` mescla por cerimônia GRAVADA no install-state — alvo
  sem cerimônia gravada não recebe hooks: precondição declarada em `docs/workflow-recovery.md`, as duas
  pernas testadas em W6); o perfil `user` deriva por subtração, NÃO exclui este hook e o nomeia em
  `_derivation.blocking_inclusions` com a rota; smoke-install verifica presença + registração.
- **Paths reais do patch: 24** (5 canônicos: lib, hook, `settings.json`, `settings.base.json`,
  `settings.user.json`; CLI; 2 testes novos + pinos do teste de paridade + lista ratificada do teste do
  template `user`; `scripts/build-plugin.py`; doc do rito; 10 docs com contagens; mapa
  comando→skill→hook e inventário de env regenerados; CHANGELOG). Os bumps são
  mecânicos (derivadores em `PLAN-190/w1/`), mas a lista é a real.
- **Limitação declarada**: o guard vê a CHAMADA da tool `Workflow`; não vê `agent()` interno nem consegue
  impedir que o harness recalcule a chave de cache — ele impede o OPERADOR de retomar sobre script/args
  diferentes sem saber. Checkpoint dentro de `agent()` continua limite do runner (W2 dá a alternativa).

### W2 — Mutações isoladas, escritor único, checkpoint por fase  [P0]  (CLIs livres + 1 hook canônico)
**Estado (S354):** as três CLIs livres LANDARAM em `6fec455b` (`mutant_sandbox.py`,
`worktree_lock.py`, `phase_checkpoint.py`, 10 testes em `tests/unit/test_w2_recovery_tools.py`:
árvore intocada após interrupção, resultado reaproveitado só na mesma revisão, segundo escritor
recusado, steal só quando vencido, retomada pula passos só na mesma revisão). Faltam o hook
`check_writer_lock.py` + `_lib/writer_lock.py` (cerimônia, measure-first) e a adoção nos prompts de
fase do consumidor.
- `.claude/scripts/mutant_sandbox.py` (livre): `run --rev <sha> --repo <path> --mutant <patch> --cmd "<teste>"
  --ledger <jsonl>`: cria cópia DESCARTÁVEL da revisão identificada (`git worktree add --detach` em
  scratch, ou `git archive` quando não houver git), aplica o mutante, roda o comando, registra
  `{rev, mutant_sha, cmd, killed|survived|error, rc, duração}`; `query` devolve resultado existente para
  a mesma chave (reaproveitamento); remoção da cópia em `finally` + registro de cópias órfãs em
  `sandboxes.jsonl` com `gc`. A árvore de implementação NUNCA é tocada. Teste: falha (SIGKILL simulado /
  exceção) ⇒ `git status` da árvore de implementação limpo; resultado por mutante reaproveitado.
- `.claude/scripts/worktree_lock.py` (livre) + `_lib/writer_lock.py` (C) + `.claude/hooks/check_writer_lock.py`
  (C, PreToolUse `Edit|Write|MultiEdit|NotebookEdit`): lock em `<worktree>/.claude/state/writer.lock`
  {owner, kind, pid, host, since, heartbeat}; owner = `agent_id` do evento se presente, senão
  `transcript_path`, senão `session_id` (o hook registra QUAL identidade estava disponível —
  measure-first); primeiro escritor adquire; segundo escritor com owner diferente ⇒ **bloqueia** nomeando
  o dono e a rota (`worktree_lock.py steal --stale-minutes N` só com heartbeat vencido; `release`
  explícito no rito de recuperação). Bash que escreve fica fora do escopo mecânico nesta wave
  (declarado). Enforce atrás de `CEO_WRITER_LOCK_REQUIRED=1` após janela advisory (≥ 20 sessões ou
  ≥ 30 dias, tabela would-block).
- `.claude/scripts/phase_checkpoint.py` (livre): JSONL append-only por `<run_id>/<fase>` com passos
  concluídos vinculados à revisão (`rev`, `step_id`, `evidence_sha`); `status` imprime o que já está
  feito para a fase — o prompt da fase manda o agente LER o checkpoint antes de começar e ESCREVER a
  cada passo; a fase que morre aos 400k retoma dos passos registrados. Invalidação: `rev` diferente ⇒
  checkpoint não conta. Teste: interromper após k passos, retomar, k passos pulados, k+1.. executados;
  mudar a revisão ⇒ zero pulados.

### W3 — Contratos de aprovação e evidência por código  [P0]  (livres + bloco COMMON documentado)
**Estado (S354):** LANDADA em `6fec455b` — `approval_gate.py` (política fechada + evidência tipada ⇒
APPROVED/REJECTED com motivos; 20 testes), `test_refs.py` (normalização por AST, ambíguo ⇒ erro;
9 testes), `docs/approval-gate.md` com o bloco COMMON JS, fixtures neutras em
`tests/fixtures/approval/`. Falta a adoção no script do consumidor (bloco COMMON no gate) — fora do
repo público.
- `.claude/scripts/approval_gate.py`: `decide --policy <json> --evidence <json>` ⇒ `{decision: APPROVED|REJECTED,
  reasons[]}`. Política: nota mínima do revisor cruzado, severidades impeditivas, exigência de revisão
  sobre a REVISÃO FINAL (`reviewed_rev == final_rev`), campos obrigatórios, enumerações fechadas
  (`ALTA|MEDIA|BAIXA`, `P0|P1|P2`). Evidência ausente, ambígua, fora do enum ou revisão diferente ⇒
  `REJECTED` com motivo nomeado. Nunca verde por omissão.
- `.claude/scripts/test_refs.py`: normaliza referências de teste (caminho, nodeid `a/b.py::test_x`,
  nome de função) contra a árvore (AST, sem executar) para nodeids canônicos; ambíguo ⇒ erro listando
  candidatos; inexistente ⇒ erro. Elimina a classe «nome × caminho».
- `docs/workflow-recovery.md` ganha o **bloco COMMON de aprovação** (JS, byte-a-byte, no molde dos 4
  workflows shipados): o script só marca verde se `approval_gate.py` (via agente ou via resultado
  tipado) devolver `APPROVED`. Fixtures neutras (`tests/fixtures/approval/*.json`).

### W4 — Quota e admissão por fase  [P1]  (livre; enforce só após medir)
- `statusline-ceo.py` (livre) persiste `rate_limits` em `<state-dir>/quota-state.json` (instante,
  `five_hour`, `seven_day`); ausência ou idade > N min ⇒ **desconhecido**, nunca «saldo livre».
- `.claude/scripts/quota_watch.py` (livre, determinístico, sem LLM): lê o snapshot; classifica o último
  erro de quota nos transcripts recentes em `five_hour` (esperar `resets_at`) × `session limit`/`spend
  limit`/`org_spend_cap_reached` (parar e avisar — não depende de alternar conta); detecta troca de
  conta por `resets_at`/`used_percentage` inconsistentes com o snapshot anterior; `admit --max-heavy N`
  conta lançamentos abertos (W1) e fases pesadas em voo (por label nos transcripts) e responde
  `ADMIT|HOLD|UNKNOWN`. Teto inicial 3-4 fases pesadas = CONTENÇÃO A MEDIR, não ótimo.
- Enforce no hook de lançamento (W1) só depois de janela advisory com tabela would-block.

### W5 — Integração determinística e contexto por fase  [P1]
- `.claude/scripts/repin.py` (livre): manifesto TSV `arquivo \t marcador \t comando-de-medida`; re-mede
  na revisão de integração, reescreve o valor EXATO, re-roda a verificação; conflito semântico ⇒ sai
  com lista para análise (nunca soma delta). Mesmo padrão do `verify-counts.sh` do framework.
- Contexto por fase: `omitClaudeMd` + contrato mínimo por papel nos agentes de fase (documentado;
  mudança em `agents/*.md` é canônica — plano segue medição de W0.2); spec por fase em vez do spec
  inteiro (padrão no bloco COMMON); `bashOutputMaxChars`/`updatedToolOutput` para saídas de teste com
  log completo em arquivo — recomendação no template SÓ após medir (o relato mostra pytest entrando
  dezenas de vezes no contexto; «crescimento» = 6,2 % do custo do framework).
- Effort por fase avaliado com qualidade medida; modelos do perímetro financeiro NÃO descem (R1).

### W6 — Distribuição e validação e2e  [P0, acoplada a cada wave]
- `smoke-install.sh` em consumidor isolado: presença dos scripts/hook, registração por cerimônia,
  `ceo-launches.py check` funcional, `upgrade.sh --dry-run` NO-OP em segunda passada.
- Bateria pedida pela ordem: interrupção e retomada sem repetir etapas válidas (W2 checkpoint + W1
  guard); invalidação quando entradas relevantes mudam (hash/args/rev); ausência de mutantes na
  árvore após falha (W2); impedimento de dois escritores (W2); rejeição de aprovação incompleta ou
  incompatível com a revisão final (W3); tratamento distinto de quota temporária e teto de gasto (W4);
  instalação/upgrade em consumidor isolado (W6).

## O que este plano NÃO faz (declarado)
- Não integra JEV nem qualquer capacidade não aprovada do fornecedor.
- Não promete checkpoint dentro de `agent()` do runner, retomada automática após troca de conta pelo
  runner, nem controle da chave de cache do runner — limites do substrato, documentados.
- Não altera produção financeira; não rebaixa modelo no perímetro financeiro; não dispensa cético nem
  revisão cross-model; não automatiza alternância de contas (R3).
- Não publica promessa de velocidade ou economia: cada ganho entra com medição (baseline acima).
- Não copia specs, scripts, nomes ou dados do consumidor para o repo público: fixtures neutras.

## Open questions
- OQ-1: o evento PreToolUse dentro de subagente traz `agent_id`? (decide a identidade do lock em W2;
  o hook registra o que recebeu — measure-first.)
- OQ-2 — RESPONDIDA (S354): a resposta da tool `Workflow` chega 0,3 s após a chamada («Workflow
  launched in background. Task ID …»; 281 pares reais medidos num consumidor) e carrega o `wf_<id>`
  em 98,5 % dos casos (324/329 no próprio repo); ausência ou ambiguidade de id ⇒ nada é vinculado nem
  registrado (o lançamento fica sem vínculo) + `bind` manual.
- OQ-3 — RESPONDIDA (debate r1): sim, o perfil `user` recebe o hook (proteção do operador), nomeado
  em `blocking_inclusions` com rota (kill-switch, advisory, token de force).
- OQ-4: `Workflow.totalTokens` = soma de picos vale em todas as versões da CLI vistas? (verificado em
  697 runs do consumidor, CLI 2.1.27x; re-verificar a cada geração.)
- OQ-5 — decisão do debate r1: o override em sessão (`force` com motivo, one-shot, anunciado) é
  visibilidade, não prevenção — o guard é instrumento de recuperação; a razão
  `forced/(forced+blocked)`, calculada das contagens que o `report` imprime, é a métrica da regra de
  parada. Registrar evento de auditoria
  para bloqueio/override é `PLAN-190-FOLLOWUP-audit-actions` (cerimônia do dono do audit).
- OQ-6 — DECIDIDA pelo Owner (2026-09-17, após o rail r4, escolha estruturada entre três opções).
  Pergunta: «A rodada 4 do Codex deu NO-GO com 4 achados P2 (nenhum grave), terceira rodada seguida na
  mesma classe: estado gravado em disco que volta para a decisão do guard. Como seguimos?» Opção
  escolhida, verbatim: «Trocar a arquitetura (Recomendado)» — «Tiro o token de override do disco: o
  override passa a ser declarado na própria chamada (campo description) ou no ambiente. Some a corrida
  e a leitura de token por construção. Qualquer exceção dentro do guard vira resultado inconclusivo
  registrado. Um validador único confere manifesto lido de volta. O relaunch confere o hash do
  snapshot.» Opções não escolhidas: assinar a v5 com os 4 achados como residual; tirar o override em
  sessão sem substituto.

## How to continue
1. Debate r1 (`/debate start PLAN-190 "W1 ledger de lançamento + guard de retomada"`) — L3.
2. W1 em sombra (worktree descartável): lib + hook + CLI + testes verdes; pacote de cerimônia no molde
   S332/S336 (SIGN/LAND com V-block); rail codex sobre os bytes canônicos; assinatura do Owner.
3. W2/W3 CLIs e testes landam livres em paralelo; guard de W2 e enforce de W4 seguem measure-first.
4. Smoke-install estendido a cada land; `upgrade.sh` no consumidor após cada wave; medir as métricas
   do §Goal por 2 semanas antes de qualquer flip para enforce.

## Success criteria
- [x] W1 LANDADA (`075beed9`): 100 % dos lançamentos de Workflow com manifesto ANTES do despacho; retomada sobre hash/args
  diferentes bloqueada com chaves nomeadas; `relaunch` reproduz a chamada exata; testes verdes.
- [ ] W2: zero mutante na árvore de implementação após N interrupções (teste); zero segundo escritor
  (teste); fase interrompida retoma pulando passos registrados (teste).
- [ ] W3: aprovação computada por código em 100 % dos casos de fixture; incompleto/ambíguo ⇒ REJECTED.
- [ ] W4: `quota_watch` distingue reset de teto de gasto nos 4 tipos vistos; desconhecido nunca vira
  «livre».
- [ ] W6: smoke-install verde; consumidor isolado recebe hook + scripts pelo `upgrade.sh`.
- [ ] Métricas no consumidor após adoção (2 semanas): fases perdidas < 2 % dos starts; reexecução de
  chave concluída = 0; tokens por entrega aprovada REPORTADOS por sessão.

## Regra de parada (pré-registrada)
- Se o guard de W1 produzir bloqueio falso em > 5 % dos lançamentos na janela advisory ⇒ não flipar
  enforce; rever o predicado (chaves ignoradas por política), não relaxar o registro.
- Se o lock de W2 bloquear o próprio dono (identidade instável entre eventos) ⇒ recuar para advisory e
  abrir follow-up de identidade; nunca desligar o registro.
- Qualquer wave que exija tocar código financeiro do consumidor ⇒ fora do plano.
