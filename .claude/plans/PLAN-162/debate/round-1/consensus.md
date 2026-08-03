---
plan: PLAN-162
round: 1
created_at: 2026-08-03
critics: 3
verdicts: [ADJUST, ADJUST, ADJUST]
round_verdict: PROCEED
design_coherent: true
consensus_findings: 11
single_agent_kept: 8
single_agent_refuted: 1
plan_adjustments: 14
---

# PLAN-162 round-1 consensus

> **Escopo do veredito.** `PROCEED` = `design-coherent` após ajustes. NÃO
> autoriza shipping — a cascata de verificação (V1 testes red-first, V2
> pair-rail codex, V3 assinatura do Owner) é quem autoriza.

Três lanes, três **ADJUST**. Nenhuma das 12 findings foi refutada: os três
re-verificaram contra o HEAD (2165-2166 linhas) e **12/12 reproduzem**;
três têm line numbers deslocados (#5 real `:1902-1909`, #11 real
`:2133-2145`, #9 sub-escopado). O que caiu foi a minha especificação dos
FIXES, não a triagem.

## Consensus findings (2+ lanes)

### C1 — [3/3] O finding #1 é AMPLIFICAÇÃO O(candidatos × sentinels), não latência

Medido independentemente por dois lanes na mesma máquina, com `gpg-agent`
saudável: **1 GPG ≈ 17-18 ms**, mas o cache
(`_compute_sentinel_cache_key`, `:894-916`) inclui `target_rel` na chave
enquanto a verificação de assinatura é **independente do alvo**
(`verify_detached` não recebe alvo). Resultado: o mesmo sentinel é
re-verificado uma vez por alvo distinto.

| Cenário | Medido | Budget do hook |
|---|---|---|
| 1 alvo, 16 sentinels | 0.22-0.29 s | 5 s |
| 20 alvos (pack de cerimônia) | **4.16 s** (0 hits / 320 misses) | 5 s |
| 40 alvos | **4.23 s** | 5 s |
| extrapolado ao cap de 512 | ~54 s | 5 s |

**Fix acordado (substitui o meu):** partir o cache em dois —
`_SIG_VERIFY_CACHE[(path, ino, mtime_ns, size, sha256, ver)] → bool` (rail
de assinatura, sem alvo) e `_GRANT_CACHE[(…, target_rel, ver)] → bool`
(escopo, barato). Colapsa 320 → 16 subprocessos.

### C2 — [2/3, 0 contra] O cap de sentinels que propus é REGRESSÃO DE SEGURANÇA

`_find_sentinels` retorna ordenado (`sorted(base.glob(pat))`, `:852`) e o
pack recém-assinado é o de número mais alto — com cap N, **o sentinel que
para de conceder é justamente o da cerimônia que o Owner acabou de
assinar**. Self-DoS com a assinatura na mão. E não resolve hang (um `gpg`
pendurado custa 15 s mesmo com cap=1). **Cap sai do desenho.** Fica um
deadline global de wall-clock por INVOCAÇÃO, checado no topo dos loops
(`:1234`, `:1277`), fail-CLOSED (`canonical_edit_hook_fault`) — nunca
"allow por não ter decidido", nunca "parar de verificar sentinels".

### C3 — [2/3] O deadline NÃO pode ser lido de settings.json em runtime

Circular: o budget vive no arquivo que o hook guarda, e ler+parsear JSON
no hot path piora o caminho sendo otimizado. **Constante de módulo**
(`_HOOK_WALL_BUDGET_S`, folga sob o timeout registrado) + teste de drift
no CI afirmando `constante <= timeout registrado` (a forma que
`verify-counts.sh` já usa).

**Ordem não-negociável:** partição de cache e deadline no MESMO patch. Um
deadline sem a partição dispara nos 4.16 s medidos e nega a própria
cerimônia — introduziria o DoS que a OQ3 temia.

### C4 — [3/3] A citação de ADR-010 para o #5 é FALSA

`grep` em `ADR-010-canonical-edit-sentinel.md` (181 linhas): **zero**
ocorrências de fail-open/fail_open/envelope/postura de falha. O "contrato
ADR-010 fail-open" existe apenas como docstring do próprio hook
(`:36-41`) — citar o comentário do hook como o ADR que o autoriza é
circular. O council cometeu o erro primeiro e eu herdei sem verificar.

**Disposição revisada — #5 racha em dois:**
- **5a `read_event` levanta exceção → ACCEPT.** Falha genuína de infra;
  CLAUDE.md §4 cobre. O kernel irmão é fail-open IDÊNTICO aqui
  (`check_arbitration_kernel.py:541-543`) — a assimetria alegada pelo
  council é metade falsa.
- **5b `event.parse_error` → FIX (fail-closed para a classe edit).**
  `parse_error` é por nome e construção o sinal de que o PAYLOAD não
  parseou; CLAUDE.md §4 é literal ("fail-closed on INPUT"). O kernel já
  implementa a forma precedente (`:548-563`). O hook sentinel é o drift.
- Não há emenda a fazer em ADR-010 (não há texto). O que falta é
  DOCUMENTAR a postura — seção nova no ADR do pack.
- **Um teste-alfinete é obrigatório de qualquer jeito**: `grep parse_error`
  nos 8 arquivos de teste do hook = ZERO. O contrato não está fixado por
  teste nenhum, em nenhuma direção.

### C5 — [2/3] "Parse só dentro dos markers" (#4) BRICKA 31% dos sentinels vivos

Medido: **5 dos 16 sentinels vivos não têm `BEGIN SIGNED SCOPE`** —
PLAN-160, PLAN-161, PLAN-163 (×2), PLAN-164, incluindo as duas cerimônias
mais recentes. **Fix revisado, mais estreito:**
1. Se o marker BEGIN existir, JAMAIS cair para Tier-2 (o código já
   fail-CLOSA nesse princípio em `:1130`).
2. Oversize (> `_SCOPE_MARKER_CAP_BYTES`) ⇒ **reject fail-closed** em vez
   do downgrade silencioso. Blast medido ≈ zero (maior sentinel vivo =
   6.801 B, 10,4% do cap) — mas **decidir chars-vs-bytes explicitamente**:
   `:1122` compara `len(text)` em CARACTERES contra um cap em BYTES.
3. Adicionar o marker END ao `_SCOPE_TERMINATOR_RE` (`:413`) para o Tier-2
   também parar nele.

### C6 — [3/3] #9 tem 3-4 sítios, não 2

`:1186`, `:1308`, `:1759` com o literal; `:1738` com `blocked_tool=""`.
Os dois últimos nasceram DEPOIS do council (era PLAN-163). Plumbar
`event.tool_name` nos quatro **e validar contra enum fechado / regex
`^mcp__[a-z0-9_]+$`** antes de virar campo de auditoria — senão o fix
injeta entrada influenciável pelo atacante num log HMAC que humanos leem.

### C7 — [3/3] O rider R1 (check_budget) tem a premissa ERRADA — meu desenho é REJEITADO

Três verificações convergentes:
1. **Não é silencioso.** `:854-868` já emite breadcrumb sempre que
   `active_plan_count >= 2`. As 20 ocorrências no audit-log SÃO esse
   breadcrumb funcionando.
2. **"Zero enforcement" é vacuidade.** `check_budget.py` não tem caminho
   de bloqueio nenhum: `grep _contract.block` → zero hits; advisory-only
   por design (ADR-033), `CEO_BUDGET_ENFORCE` default 0. O arco de 17,5M
   tokens perdeu uma linha de warning, não enforcement.
3. **A heurística CWD/branch contradiz o modelo de ameaça.**
   `docs/threat-model.md:207` (T-001, plan-id spoof) registra a mitigação
   como *"audit-log-session-derived plan-id **not env var**"*. CWD/branch
   é entrada spoofável. E "o cap mais restritivo" é auto-DoS **e teatro**:
   `_plan_tokens_total` (`:515-521`) filtra por `ev_plan != plan_id`, então
   o cap do plano B parearia com o uso ~zero do plano B — nunca dispara.

**Desenho acordado:** manter allow (é advisory por contrato); retornar a
LISTA de planos ativos de `_resolve_active_plan`; uma passada de
`iter_events` com bucket por plan_id; comparar cada plano contra o
PRÓPRIO cap; `systemMessage` visível nomeando qual estourou. Sem
heurística, sem tie-break. Se um único id for necessário, derivar do
EVENTO (`event.plan_id` do spawn sendo gated), nunca de CWD/branch.
**R-QA1:** `test_check_budget.py:472` (`test_indeterminate_plan_skips`)
fixa o contrato atual — reescrever no MESMO patch, senão o closeout fica
vermelho.

### C8 — [2/3] #11 é INEXEQUÍVEL enquanto #6 for DOC-GAP

O gate de unicode lê **um blob só** (`_staged_content`, `:620-654`) e
`_extract_mcp_target_paths` descarta dicts aninhados — não existe mapa
path→content no Layer-A. "Escanear todo SKILL.md GRANTED" é
implementavelmente impossível. As duas disposições eram incoerentes.
**Resolução:** mantendo Layer-A v1 (decisão preservada), **#11 desce para
DOC-GAP** com o comportamento honesto: escanear o blob uma vez e atribuir
o bloqueio ao EVENTO, documentando a imprecisão — nunca vender cobertura
por-path que o extractor não sustenta.

### C9 — [2/3] O fix do #2 tem de ser INDEPENDENTE DE PROFUNDIDADE

"Cobrir a profundidade real dos patterns" re-acopla o guard à lista de
patterns: o próximo pattern com 6 segmentos re-abre o furo em silêncio
(classe dead-gate, no mesmo arquivo que já a sofreu duas vezes). **Fix:**
subir de `p` até `base` rejeitando qualquer segmento symlinkado, e/ou
afirmar `realpath(p)` contido sob `realpath(base)`. Bypass reproduzido com
controle positivo (symlink em `PLAN-*` aceito; symlink em `p.parent`
rejeitado — o controle prova que a sonda está viva).

### C10 — [3/3] Fold #3+#8 mantido (OQ2 RESOLVIDA), sem herdar o enquadramento do #12

Mesma classe, mesma correção mecânica, mesmo trecho de Scope. **Mas** #3 e
#8 não têm segunda camada nenhuma (nem `_CANONICAL_GUARDS` nem
`_KERNEL_PATHS` — verificado), enquanto #12 tem kernel hard-deny. Cada uma
precisa do próprio teste red-first provando o estado DUPLAMENTE
desguardado. Fix: guardar os ARQUIVOS (canonical + kernel), **não**
inverter o `.exists()` — "ausência ⇒ fail-closed" exigiria uma definição
de "esperado" que é ela mesma editável, e aí deletar um arquivo passa a
ESCOLHER a postura.

### C11 — [3/3] #12 ACCEPT, com o mitigante NOMEADO e gatilho de reabertura

O mitigante não é "não há YAML nested em disco" (estado transitório) — é
`.claude/dispatcher/**/*` no `_KERNEL_PATHS` (hard-deny, **sem escape de
sentinel**). Gatilho de reabertura: o primeiro `.yaml` aninhado que nascer
sob `dispatcher/`. Sem gatilho é adiamento, não aceitação.

## Single-lane MANTIDO (verificado pelo CEO em primeira mão)

### S1 — P0 fora das 12: bypass por filesystem case-insensitive (VETO-flagged)

**CONFIRMADO por verificação própria** (`scratchpad/verify_claims.py`):

```
FS case-insensitive na raiz do repo: True
  escrita via .../CaseProbe.txt → lida de .../caseprobe.TXT: sobrescrita

                                    canonical  kernel
.claude/settings.json                  True     True
.claude/settings.JSON                 False    False   ← fura os DOIS
.claude/hooks/_lib/audit_emit.py       True     True
.claude/hooks/_lib/audit_emit.PY      False    False   ← fura os DOIS
.claude/sentinel-signers.txt          False     True
.claude/sentinel-signers.TXT          False    False   ← fura o kernel
```

`_match_segments` usa `fnmatch.fnmatchcase` nos DOIS hooks; em APFS
(default do macOS, a plataforma deste repo) o arquivo é o mesmo. Alcança
o kernel hard-deny em `settings.json`, `audit_emit.py` e o registro de
assinantes — todo o modelo de ameaça assume esses caminhos inalcançáveis.
**Entra nesta cerimônia como FIX P0.** Desenho: casar com normalização
case-fold nos dois rails (over-classify é a direção segura), fixado por
teste red-first em AMBOS.

### S2 — O conjunto de sentinels é o trust anchor e não é guardado

`.claude/plans/PLAN-*/**/approved.md` + `.asc`: canonical=False,
kernel=False. Duas consequências: (a) o agente controla o CUSTO do gate
(60 sentinels plantados = 0,48 s; ~628 arquivos triviais põem todo evento
acima do budget); (b) sob uma janela `CEO_SENTINEL_UNLOCK` do Owner,
`:994` pula o GPG inteiro e um `approved.md` escrito pelo agente
**concede** — isso é bypass de AUTORIZAÇÃO, não DoS.

> **CORREÇÃO (pair-rail R2, P1).** A mitigação que eu escrevi aqui —
> "aceitar apenas sentinels rastreados no git **ou** pré-existentes ao
> início da sessão" — é **defeituosa**, e o codex provou: dentro da
> janela o agente escreve o `approved.md` e roda um `git add` comum;
> `git ls-files --error-unmatch` passa a reportá-lo TRACKED, e um check
> baseado em HEAD aceitaria igualmente um commit autorado pelo agente.
> **Estado do git é afirmação sobre o índice, não sobre quem autorizou.**
> A disjunção deixava o bypass inteiro de pé enquanto os testes passavam.
>
> Regra corrigida: o anchor de confiança é **o início da sessão, não o
> estado do git** — sob `env_override`, aceitar apenas sentinels que já
> existiam quando a sessão começou. Três negativos obrigatórios, um por
> forma de o agente vestir um arquivo novo de legítimo: **untracked**,
> **staged**, **committed** (os três em
> `S2SentinelUnderEnvOverrideTest`), com o controle anti-self-DoS
> reescrito para tomar o anchor DEPOIS do commit — sentinel genuinamente
> anterior — em vez de antes.

### S3 — #1 já é residual ACEITO no ADR-164 → o entregável é EMENDA

**CONFIRMADO:** `ADR-164-canonical-multicandidate-and-failclosed.md:119`
(`## Residual risk (pair-rail, accepted)`), `:121` ("Near-cap all-granted
GPG cost"), `:127` ("operationally absurd… Accepted"). A medição REFUTA a
premissa (47 alvos bastam, não 512; e o vetor de sentinel plantado não
precisa de path concedido nenhum). Reabrir está certo, mas o entregável é
**`ADR-164-AMEND-1`**, não uma finding nova — landar um fix que contradiz
um ADR ACCEPTED sem emendá-lo é drift de governança.

### S4 — Convenção de teste: reusar `PLAN160_FIX_<letra>` (xfail strict)

`test_canonical_edit_council_findings.py:96-120` já resolveu "como provar
red-first um fix num hook canonical-guarded que não podemos editar":
marcador de string no source + `pytest.mark.xfail(condition=not FIXED_N,
strict=True)`. `strict=True` é o que impede o teste de passar por acidente
antes do fix. **Adotar `PLAN162_FIX_<N>` e reusar
`_CouncilFindingsBase._mcp_bulk_write_event` / `_write_sentinel`.**

### S5 — #10 exige teste IN-PROCESS

`FindingBCacheBlastRadiusTest` já provou que a invocação real (subprocess
por evento) mata o cache module-scope entre invocações — um repro via
subprocess dá XPASS por acidente. Teste correto: carregar o módulo uma
vez, mutar bytes do `.asc`/allowlist/registry ENTRE duas chamadas no MESMO
processo. E reformular a severidade: #10 é defesa-em-profundidade para
reuso in-process, não exploit ativo por-invocação.

### S6 — Passada de INTERAÇÃO entre findings

O fix de #2 muda quais candidatos `_find_sentinels` retorna (pode inverter
fixtures de #10); o de #7 muda o que `_canonical_rel` devolve para
candidatos `uri` (interage com a forense de #9 no MESMO evento). Este
arquivo já foi mordido por bug de interação antes
(`SentinelCacheKeyRegressionTest`). W1 orça ≥1 passada de interação.

### S8 — O deadline de #1 precisa de CLOCK INJETÁVEL

Se o orçamento de wall-clock for implementado com `time.monotonic()` inline
sem seam, o teste red-first tem só duas saídas ruins: sleep real de vários
segundos (flaky sob carga de runner — o repo já tem histórico documentado
dessa classe, [[feedback-perf-gate-n20-load-flake]]) ou nenhuma cobertura
determinística do caminho lento. **O fix tem de aceitar um clock
injetável** (parâmetro com default `time.monotonic`, ou módulo-level
`_now = time.monotonic` monkeypatchável), decidido no MESMO patch — não
depois. Isso é requisito do FIX, não do teste.

### S7 — O Scope do sentinel precisa ser SEPARÁVEL

A cerimônia consolidada empacota posturas opostas (fixes fail-closed do
canonical-edit + observabilidade advisória + ADR-110-AMEND-2 + RC3-F7). Um
REJECT do pair-rail num rider travaria todos. Ordenar o Scope para que os
fixes fail-closed sejam destacáveis.

## Single-lane REFUTADO pelo CEO

### X1 — "Layer B (`canonical_guard`) não existe neste repo" — FALSO

Verificação: `.claude/hooks/_lib/mcp/canonical_guard.py` **existe**, 46.369
bytes, com `_extract_write_shape_paths` / `_walk_json_for_paths` / etc., e
é uma das 4 pernas do `mutation-gate.yml`. O que NÃO existe em disco é o
ARQUIVO DE PLANO `PLAN-070*` (arquivado ou nunca escrito). A conclusão
derivada ("ACCEPTED-BOUNDARY sem controle compensatório neste repo") cai:
o mitigante do #6 é real e vive no repo. Registrado como refutação para
não voltar num council futuro. **Correção honesta que sobra:** o texto do
DOC-GAP deve citar o caminho do módulo, não o número do plano.

## Deferidos / rejeitados

- **R2 (instrumento do council)** — DEFER para plano próprio (3/3).
- **#6 Layer-A nested MCP** — mantido DOC-GAP (custo no hot path), agora
  citando `_lib/mcp/canonical_guard.py` como o mitigante REAL (X1).
- **#7** — FIX mantido; forma decidida em W1 entre normalizar o scheme em
  `_extract_mcp_target_paths` (uma função só) ou tratar valor
  não-interpretável como fail-CLOSED. Ambos os lanes aceitam qualquer das
  duas; a segunda é mais conservadora.
- **W3 (council re-run)** — PULADO (3/3 + ratificação do Owner).

## Plan adjustments (aplicados ao PLAN-162)

1. #1 re-diagnosticado: amplificação, não latência; fix = partição de cache.
2. Cap de sentinels REMOVIDO do desenho (regressão).
3. Deadline global fail-closed + constante de módulo + teste de drift.
4. Fold **#1+#10** adicionado (a partição já força a chave nova).
5. #5 rachado em 5a (ACCEPT) / 5b (FIX fail-closed) + teste-alfinete.
6. Citação falsa de ADR-010 removida; postura vira seção de ADR novo.
7. #4 estreitado (marker-present ⇒ nunca Tier-2; oversize reject; END no
   terminator; decidir chars-vs-bytes).
8. #9 ampliado para 4 sítios + validação de `tool_name`.
9. #11 → DOC-GAP (inexequível sob Layer-A v1), atribuição por EVENTO.
10. #2 → fix independente de profundidade (realpath containment).
11. #12 ACCEPT com mitigante nomeado + gatilho de reabertura.
12. R1 re-desenhado (per-plano contra o próprio cap; sem heurística) +
    reescrita de `test_indeterminate_plan_skips` no mesmo patch.
13. **S1 (case-insensitive) entra como FIX P0** — o mais severo do round.
14. **S3: `ADR-164-AMEND-1`** vira entregável obrigatório do pack.

## Round verdict

**PROCEED** — `design-coherent` após os 14 ajustes. Os três lanes
convergiram em ADJUST sem VETO; o mérito da triagem sobreviveu inteiro e
o que mudou foi a especificação dos fixes, que é exatamente o que um
debate de desenho deve produzir. W1 (testes red-first) começa com o
escopo revisado. Não há necessidade de round 2: nenhuma disposição ficou
em disputa entre lanes após as verificações do CEO.
