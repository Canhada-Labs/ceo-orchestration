---
id: PLAN-190
title: Execução autônoma utilizável nos consumidores — preservar trabalho pago, recuperar progresso, aprovar por código
status: draft
created: 2026-09-17
owner: CEO
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
- **Guard de retomada**: com `resumeFromRunId`, carrega o manifesto vinculado a esse run e compara
  `sha256` do script e `args` literal; divergência ⇒ **bloqueia** nomeando as chaves diferentes e a
  rota de recuperação (`CEO_WORKFLOW_RESUME_FORCE=1`, registrada no ledger com motivo). Sem manifesto
  vinculado ⇒ registra e segue (advisory). Falha de infraestrutura ⇒ `{}` (fail-open); entrada
  ilegível ⇒ registra `unparsed` e segue advisory (não é matcher de segurança).
- **CLI** `ceo-launches.py list|show <run|launch>|relaunch <run>|check --script … --args … --resume <run>|report`:
  `relaunch` imprime a chamada EXATA (scriptPath + hash esperado + args literal) — nunca reconstruir de
  memória; `check` é o mesmo predicado do guard, utilizável pelo rito do consumidor mesmo antes de o hook
  chegar lá.
- **Testes**: registro antes do despacho; ausente ≠ `null` nos args; hash muda ⇒ bloqueio nomeado; args
  mudam ⇒ bloqueio nomeado; `FORCE` registra e libera; sem manifesto ⇒ advisory; `{}` em falha de infra;
  isolamento por `TestEnvContext`.
- **Distribuição**: hook chega pela enumeração de `.claude/hooks/` no manifesto; registração pelo
  template `settings.base.json` (o `upgrade.sh` mescla por cerimônia; o perfil `user` deriva por
  subtração — o hook NÃO entra na lista de subtração); smoke-install verifica presença + registração.
- **Limitação declarada**: o guard vê a CHAMADA da tool `Workflow`; não vê `agent()` interno nem consegue
  impedir que o harness recalcule a chave de cache — ele impede o OPERADOR de retomar sobre script/args
  diferentes sem saber. Checkpoint dentro de `agent()` continua limite do runner (W2 dá a alternativa).

### W2 — Mutações isoladas, escritor único, checkpoint por fase  [P0]  (CLIs livres + 1 hook canônico)
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
- OQ-2: a resposta da tool `Workflow` traz o `run_id` de forma estável para o vínculo do PostToolUse?
  (W1 trata ausência como advisory e o `bind` manual do CLI cobre.)
- OQ-3: o perfil `user` derivado por subtração precisa do hook de lançamento? (padrão: sim — é
  proteção do operador, não do mantenedor.)
- OQ-4: `Workflow.totalTokens` = soma de picos vale em todas as versões da CLI vistas? (verificado em
  697 runs do consumidor, CLI 2.1.27x; re-verificar a cada geração.)

## How to continue
1. Debate r1 (`/debate start PLAN-190 "W1 ledger de lançamento + guard de retomada"`) — L3.
2. W1 em sombra (worktree descartável): lib + hook + CLI + testes verdes; pacote de cerimônia no molde
   S332/S336 (SIGN/LAND com V-block); rail codex sobre os bytes canônicos; assinatura do Owner.
3. W2/W3 CLIs e testes landam livres em paralelo; guard de W2 e enforce de W4 seguem measure-first.
4. Smoke-install estendido a cada land; `upgrade.sh` no consumidor após cada wave; medir as métricas
   do §Goal por 2 semanas antes de qualquer flip para enforce.

## Success criteria
- [ ] W1: 100 % dos lançamentos de Workflow com manifesto ANTES do despacho; retomada sobre hash/args
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
