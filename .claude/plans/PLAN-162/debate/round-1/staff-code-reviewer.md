---
plan: PLAN-162
round: 1
critic: Staff Code Reviewer
verdict: ADJUST
created_at: 2026-08-03
---

# PLAN-162 round-1 critique — Staff Code Reviewer

## Verdict

ADJUST — o dedup está correto e 12/12 claims reproduzem no HEAD, mas três
disposições repousam em premissas não-verificadas (a citação de ADR-010 em #5
**não existe**; #11 é inexequível enquanto #6 for DOC-GAP; R1 mede a severidade
errada) e os dois fixes de maior prioridade (#1, #2) estão especificados com
desenhos que não fecham o defeito.

## Summary

- A proposta faz o que promete: dedup contra S276/PLAN-160 defensável, e
  **todos os 12 claims reproduzem no HEAD** — nenhum é STALE em substância.
  Três têm line numbers deslocados e um está sub-escopado (tabela abaixo).
- Onde está forte: o fold #3+#8 é correto (respondo OQ2 abaixo), #7/#8/#10/#12
  estão bem classificados, e pular W3 é a decisão certa.
- Onde está fraco: os fixes propostos para #1 e #2 tratam o sintoma citado pelo
  council, não o mecanismo real. Eu medi o mecanismo real — **4,16 s de um
  budget de 5 s com GPG saudável**, sem nenhum hang.

## Risks

### R-CR1 — CRITICAL — o breach de timeout do #1 é alcançável HOJE, sem GPG degradado

O council enquadrou #1 como "GPG lento/deny-all mata o hook". Isso subestima.
Medido nesta máquina, no HEAD, com `gpg-agent` saudável:

```
sentinels descobertos: 16   (o council contou 12 — cresceu em 7 dias, todos com .asc)
block-path, 1 alvo:     0,286 s   (17,9 ms/sentinel)
2º alvo distinto:       0,190 s   | cache: 0 hits / 32 misses
evento apply_patch de 20 caminhos canônicos (tamanho de um pack de cerimônia):
                        4,16 s    | cache: 0 hits / 320 misses
                        ^^^^^^^ 83% do timeout registrado de 5 s
```

Causa real: `_sentinel_grants_path` (L928) faz a verificação GPG **antes** do
parse de Scope, mas o cache (`_compute_sentinel_cache_key`, L894-916) inclui
`target_rel` na chave. A verificação de assinatura é **independente do alvo** —
`verify_detached(sentinel, sig, allowlist, timeout)` (L1007-1012) não recebe
alvo, e o rail de registry + bootstrap-pin (L1015-1069) também não. Só o parse
de Scope (L1076+) consome `target_rel`. Resultado: um subprocess GPG
target-independente é re-executado uma vez por `(sentinel × alvo)` — 320
invocações no evento medido, onde 16 bastariam.

**Mitigação:** partir o cache em dois, preservando comportamento —
`_SIG_VERIFY_CACHE[(path, ino, mtime_ns, size, sha256, ver)] -> bool` (rail de
assinatura+signer, sem alvo) e `_GRANT_CACHE[(…, target_rel, ver)] -> bool`
(decisão de escopo, barata). Colapsa 320 → 16 subprocessos no evento medido
(4,16 s → ~0,3 s). Isso é o fix do #1; o resto é defesa em profundidade.

### R-CR2 — HIGH — o cap de sentinels proposto para #1 é uma regressão de segurança

"Cap de sentinels verificados" tem duas falhas. **Primeira:** `_find_sentinels`
retorna ordenado (`sorted(base.glob(pat))`, L852) e o pack recém-assinado é o de
número mais alto — com 16 sentinels e um cap de N, o sentinel que para de
conceder é exatamente o da cerimônia que acabou de ser assinada. É self-DoS com
a assinatura do Owner na mão. **Segunda:** não resolve o caso de hang. UM
`gpg` pendurado custa 15 s (L1011) — 3× o budget — mesmo com cap=1.

**Mitigação:** remover o cap do desenho. O que faz o hook "sempre responder" é
um **deadline global de wall-clock** por invocação, checado no topo do loop de
sentinels (L1234-1236 e L1277-1279), não um cap de cardinalidade.

### R-CR3 — HIGH — derivar o budget de `settings.json` em runtime é circular

A proposta diz "orçamento de verificação derivado do budget registrado". O
budget registrado vive em `.claude/settings.json` — **o arquivo que este hook
guarda** (`_CANONICAL_GUARDS` L169). Ler + parsear JSON no hot path a cada
PreToolUse para descobrir o próprio timeout adiciona I/O e uma dependência
circular no caminho que está sendo otimizado.

**Mitigação:** constante de módulo (`_HOOK_WALL_BUDGET_S = 3.5`) + um teste de
drift no CI que afirma `constante <= timeout registrado em settings.json`. O
repo já tem essa forma de gate (`check-claude-md-claims.py`, `verify-counts.sh`).

### R-CR4 — HIGH — a justificativa de ACCEPT do #5 cita um ADR que não diz isso

`grep -n -i "fail-open|fail_open|envelope|exception|parse"` em
`.claude/adr/ADR-010-canonical-edit-sentinel.md` (181 linhas): **zero
ocorrências** de qualquer postura de falha. O "contrato fail-open" que a
proposta atribui a ADR-010 existe apenas como docstring do próprio hook
(L36-41). Citar o comentário do hook como o ADR que autoriza o hook é
circular. (Nove outros ADRs carregam a string "fail-open contract"; ADR-010
não é um deles.) O council cometeu o erro primeiro — "Documentado como o
contrato ADR-010 fail-open (L36-41)" — e a proposta o herdou sem verificar.

**Mitigação:** ver Must-fix 4. A disposição pode continuar sendo ACCEPT para
metade do #5, mas não com essa citação.

### R-CR5 — MEDIUM — o fix do #4 como redigido nega 5 dos 16 sentinels vivos

"Scope parse APENAS dentro dos markers assinados". Medido: **5 dos 16 sentinels
vivos não têm `BEGIN SIGNED SCOPE`** — PLAN-160, PLAN-161, PLAN-163 (round-1-pin
e round-2-pack), PLAN-164. São 31%, incluindo as duas cerimônias mais recentes.
Todos são Tier-2 por construção (`PLAN-164/architect/round-1/approved.md` tem
`Scope:` na L118 e zero markers). Aplicado literalmente, o fix bricka a
cerimônia anterior.

**Mitigação:** escopar para "quando os markers ESTÃO presentes" — que é
exatamente o que Tier-1 já faz (L1122-1131). Ver Must-fix 5 para o fix correto,
que é mais estreito que o proposto.

### R-CR6 — MEDIUM — regressão silenciosa de over-grant no patch do #1

O patch do #1 toca o caminho de concessão pelo qual passa **toda** edição
canônica. Um bug na partição do cache não falha ruidosamente: concede a mais,
em silêncio. Blast radius L3.

**Mitigação:** teste red-first com duas asserções, não uma — (a) mock em
`verify_detached` afirmando que a **contagem de chamadas** cai para
`len(sentinels)` e não `len(sentinels) × len(alvos)`; (b) matriz de
equivalência afirmando decisões byte-idênticas antes/depois sobre os 16
sentinels vivos × um conjunto de alvos concedidos e negados.

### R-CR7 — LOW — R1 compete por um slot de cerimônia que não merece

Ver Must-fix 7: `check_budget.py` não tem caminho de bloqueio nenhum. O custo
do skip foi uma linha de warning, não enforcement.

## Must-fix

### 1. Auditoria de staleness — publicar esta tabela no consenso

Verifiquei os 12 contra o HEAD (2165 linhas). **Nenhum claim é STALE em
substância**; três estão STALE em localização e um está sub-escopado. O plano
exige "claim que não se reproduz no HEAD deve ser reportado como STALE" — o
resultado honesto é que nada foi refutado, e isso precisa ficar registrado
para não ser re-litigado no round 2.

| # | Linhas citadas | Estado no HEAD |
|---|---|---|
| 1 | L1011 | EXATA. Mas "12 sentinels" → **16** hoje, todos com `.asc`. |
| 2 | L858-864, L838-847 | EXATAS. Reproduzido com controle positivo (abaixo). |
| 3 | L1017, L1015-1069 | EXATAS. Oráculo → 0. |
| 4 | L1122/L1147, L413/L420 | EXATAS. |
| 5 | L1450-1458 | **STALE-LOCATION** — essa faixa hoje é `_session_roots_*` (PLAN-163 T3.1/ADR-183). Real: **L1902-1909**. Substância reproduz. |
| 6 | L346-356, L370-385 | EXATAS. `L1485-1487` (allow) deslocou. Reproduzido: `files:[{path,content}]` → `[]`. |
| 7 | L355, L662 | EXATAS. Oráculo: `file://…/settings.json` → 0, caminho simples → 1. |
| 8 | — | Oráculo → 0. |
| 9 | L1186, L1308 | EXATAS mas **SUB-ESCOPADO** — ver Must-fix 6. |
| 10 | L877-879, L903-916 | EXATAS. Medido: 0 hits / 32 misses em 2 alvos. |
| 11 | L1556, L1649-1651 | **STALE-LOCATION** — gate real **L2133-2145**, scanner **L561-614**. Substância reproduz. |
| 12 | L164-167 | EXATAS. Oráculo: `dispatcher/nested/sub.yaml` → 0, `routing-matrix.yaml` → 1. |

### 2. #1 — trocar o desenho: partição de cache primeiro, deadline depois, no MESMO patch

Substituir os três sub-itens propostos por:
(a) **partir o cache** (R-CR1) — é o que remove a amplificação;
(b) **deadline global de wall-clock** checado no topo dos loops L1234/L1277,
constante de módulo + teste de drift no CI (R-CR3), sem cap de cardinalidade
(R-CR2);
(c) manter "GPG lento ⇒ sentinel não-verificado, sem grant" — está correto e é
fail-closed.

A ordem importa e não é negociável: **um deadline sem a partição do cache
dispara no evento medido de 4,16 s** e nega a própria cerimônia. Os dois têm
que viajar no mesmo patch, ou o patch introduz o DoS que a OQ3 teme.

### 3. #2 — o fix proposto re-abre o buraco no próximo pattern

"Guard depth tem de cobrir a profundidade real dos patterns" re-acopla o guard
à lista de patterns. O próximo pattern adicionado a `_PATTERNS` (L837-848) com
6 segmentos re-abre o furo em silêncio — é a classe dead-gate do S254 outra vez,
no mesmo arquivo que já a sofreu duas vezes (`_CANONICAL_PREFIXES`, L662-679).

O fix tem de ser **independente de profundidade**: subir de `p` até `base`
rejeitando qualquer segmento symlinkado, e/ou afirmar que
`os.path.realpath(p)` está contido sob `os.path.realpath(base)`.

Reprodução (root falso, repo intocado), com controle positivo:

```
A) PLAN-999 -> /…/OUTSIDE (symlink no segmento PLAN-*, 3 níveis acima do arquivo)
   ACEITO -> …/repo/.claude/plans/PLAN-999/architect/round-1/approved.md
   realpath: …/OUTSIDE/architect/round-1/approved.md      → BYPASS REPRODUZIDO
B) controle: symlink em p.parent (profundidade coberta)   → rejeitado (guard segurou)
```

O controle B é o que prova que a sonda está viva: o guard funciona onde diz
funcionar e falha exatamente onde o council apontou.

**Pré-condição a provar em W1, não a assumir:** `.claude/plans/PLAN-*/` **não é
canônico** (oráculo: `.claude/plans/PLAN-162/x.md` → 0) e `check_bash_safety.py`
não tem regra alguma para `ln`/symlink (grep: zero hits). Eu **não** rodei uma
sonda `ln` viva, então registro isto como "nenhuma regra encontrada", não como
"alcançabilidade provada". O ônus é do plano provar que a pré-condição está
gated — uma sonda de 3 linhas em W1 resolve.

### 4. #5 — dividir em 5a/5b; a assimetria alegada é metade falsa

Verifiquei `check_arbitration_kernel.py`: **L541-543 também é fail-open na
exceção de `read_event`** — forma byte-idêntica à do hook sentinel. Os dois
hooks divergem **apenas** em `event.parse_error` (kernel L548-563), e mesmo ali
o kernel só bloqueia quando `tool_name in {Edit, Write, MultiEdit}` — para a
superfície `mcp__*`, **ambos os hooks são fail-open em parse_error**. A frase do
council "UNLIKE the sentinel hook" é verdadeira para metade do achado.

- **5a — `read_event` levanta exceção → ACCEPT.** Falha genuína de
  infraestrutura; CLAUDE.md §4 "fail-open on INFRASTRUCTURE" cobre. Documentar.
- **5b — `event.parse_error` → FIX.** `parse_error` é, por nome e por
  construção, o sinal estruturado de que o **payload** (o input) não parseou.
  CLAUDE.md §4 é literal: "fail-closed on INPUT (security matchers)". O kernel
  já implementa a forma precedente para edit-class. O hook sentinel é o
  **drift**, não o contrato.

Consequência para o gating: a proposta diz "se o debate decidir fail-closed,
precisa emenda de ADR-010". **Não precisa** — não há nada em ADR-010 para
emendar (R-CR4). CLAUDE.md §4 já É a doutrina. O que falta escrever é o ADR que
nunca documentou o fail-open. Isso é um ADR novo (ou uma seção em ADR-010),
não uma emenda a um texto inexistente.

### 5. #4 — estreitar o fix; e registrar a regressão de disciplina de markers

O fix correto é menor que o proposto, em duas partes:
(i) oversize (>64 KiB, `_SCOPE_MARKER_CAP_BYTES` L453) ⇒ **reject fail-closed**
em vez do downgrade silencioso Tier-1→Tier-2 (L1122→L1147). Blast **zero**: o
maior sentinel vivo tem 6.801 B — 10,4% do cap;
(ii) adicionar o marker END a `_SCOPE_TERMINATOR_RE` (L413) para que o Tier-2
**também** pare nele. Hoje o END não casa nem o terminator nem o HR (L420).

Não incluir "parse só dentro dos markers" (R-CR5).

**Observação que o council não fez:** a disciplina de markers do PLAN-064
Option D **regrediu**. As cerimônias mais recentes (PLAN-163, PLAN-164) são
Tier-2. Consertar #4 sem consertar o template de cerimônia só re-acumula a
dívida no próximo pack.

### 6. #9 — sub-escopado: são quatro sítios, não dois

`grep -n blocked_tool` no HEAD:

```
1186:  blocked_tool="Edit|Write|MultiEdit",
1308:  blocked_tool="Edit|Write|MultiEdit",
1738:  blocked_tool="",                      ← _audit_session_roots_registry_fault
1759:  blocked_tool="Edit|Write|MultiEdit",  ← _audit_session_root_block
```

L1738 e L1759 são da era PLAN-163 — **entraram depois** do council rodar, que
por isso só viu dois. Um fix escopado em "L1186/L1308" deixa metade dos sítios
de emissão errados e re-abre o mesmo achado no próximo council. Plumbar
`event.tool_name` nos quatro.

### 7. R1 — duas correções de fato antes de decidir prioridade

**(a) Não é silencioso.** L860-868 emite
`_breadcrumb("indeterminate plan_id — N active plans; skipping budget check")`
sempre que `active_plan_count >= 2`. As "20 ocorrências no audit-log" que a
proposta cita **são esse breadcrumb funcionando**. O que falta não é o aviso —
é a checagem.

**(b) "Zero enforcement" é verdade, mas vazia.** `check_budget.py` não tem
caminho de bloqueio nenhum: `grep "_contract.block"` → zero hits; todo retorno é
`_contract.allow(...)`, inclusive o over-cap (L709-733), que permite com
systemMessage `"Advisory-only (Sprint 11)"` (ADR-033). Registrado em
`PreToolUse` matcher `Agent`, timeout 5. O arco de 17,5M tokens perdeu **uma
linha de warning e um evento `budget_exceeded`** — não enforcement. R1 é fix de
**observabilidade**, não de segurança, e não deveria ocupar slot numa cerimônia
GPG cujos outros riders são guards fail-open.

**(c) O tie-break proposto é teatro de enforcement.** `_plan_tokens_total`
(L515-521) filtra eventos por `ev_plan != plan_id`. Escolher "o plano de budget
mais restritivo" pareia o **cap** do plano B com o **uso** do plano B — que é
~zero, porque a sessão está gastando sob o plano A. Cap apertado sobre
numerador vazio nunca dispara.

**Desenho concreto que proponho — eliminar o tie-break:**

```
_resolve_active_plan já lê TODOS os planos ativos (L240-262) e hoje descarta
tudo quando len(matches) != 1. Em vez disso:

1. Retornar a LISTA de (plan_path, plan_id) ativos.
2. Uma única passada de iter_events(action_filter="agent_spawn") fazendo
   bucket por plan_id (hoje já é uma passada, só que filtrada a um id).
3. Para cada plano ativo i: comparar usage_i contra cap_i — o próprio cap do
   próprio plano, via _resolve_cap(plan_path_i).
4. Warning (allow + systemMessage) se QUALQUER plano estourar o próprio cap;
   a mensagem nomeia qual.
```

Isso é coerente sob N≥2, não precisa de heurística de CWD/branch, e é uma
mudança **menor** que inventar uma ordem de resolução. Custo limitado: os
arquivos de plano já são lidos; o rollup continua sendo uma passada só.

Se ainda assim um único plano precisar ser nomeado, derivar do **evento**
(`event.plan_id` do spawn sendo gated) — nunca de CWD/branch. O spawn já
carrega a atribuição pela qual o rollup filtra.

## Nice-to-have

1. **#10 tem cura grátis dentro do fix do #1.** A partição de cache do Must-fix
   2 já força revisitar a chave. Incluir digest/mtime de `.asc` + allowlist +
   registry na chave de assinatura no mesmo patch, e corrigir o comentário
   mentiroso de L877-879 ali. Um patch, dois achados, zero superfície extra.
2. **#7 — normalizar o scheme antes de `Path`, não depois.** O extrator já
   devolve o URI como candidato (medido: `{"uri": "file:///x/…"}` →
   `['file:///x/…']`); só o `first_seg` (L745) o descarta. Fazer o strip em
   `_extract_mcp_target_paths` (L358-385) mantém o fix numa função só; fazer em
   `_canonical_rel` espalha por três chamadores.
3. **#12 — se for ACCEPT, o residual precisa de nome e gatilho.** Meu skill
   exige que risco residual aceito cite o controle compensatório. Aqui ele
   existe e é real (`.claude/dispatcher/**/*` no kernel deny,
   `check_arbitration_kernel.py` L133) — mas o ACCEPT tem que citá-lo
   explicitamente e nomear o gatilho de reabertura: "primeiro `.yaml` aninhado
   que nascer sob `dispatcher/`". Sem gatilho, é adiamento, não aceitação.
4. **R2 (instrumento do council) — concordo com DEFER**, sem ressalva. Não é
   `check_canonical_edit`, e a fórmula `180+2N` já foi contornada na prática com
   o cap de 600 s (cabeçalho do report S280).

## Unseen

1. **#11 é inexequível enquanto #6 for DOC-GAP.** O gate de unicode
   (L2133-2145) lê **um** blob de conteúdo — `event.new_content` ou
   `_staged_content(event)` (L620). Não existe conteúdo por-caminho no Layer-A
   porque `_extract_mcp_target_paths` descarta dicts aninhados (medido:
   `files:[{path,content}]` → `[]`). Logo "escanear todo SKILL.md GRANTED" é
   **impossível de implementar**: não se escaneia conteúdo que nunca foi
   extraído. As duas disposições — #6 DOC-GAP e #11 FIX — são mutuamente
   incoerentes. Escolher uma: ou #6 ganha o parse aninhado de
   `files:[{path,content}]` (e aí #11 vira fix real), ou #11 desce para DOC-GAP
   junto do #6.
2. **A contagem de sentinels é uma superfície que cresce sozinha.** 12 no S280,
   16 hoje — ~1 por cerimônia, monotônico, sem poda. O custo do block-path é
   O(sentinels × candidatos) e nenhum gate observa esse crescimento. Mesmo com
   a partição de cache do Must-fix 2, o termo linear em sentinels persiste. Vale
   um teste de gate barato: afirmar que `len(_find_sentinels(root))` está abaixo
   de um teto, ou que o sweep block-path de alvo único fica sob X ms. Sem isso,
   o #1 volta em 2027 com números maiores.
3. **A proposta não diz o que acontece com os 5 sentinels Tier-2 vivos.** Se a
   direção estratégica é markers assinados (PLAN-064 Option D), PLAN-160/161/163
   ×2/164 estão fora dela e ninguém está contando. Isso não é finding do council
   — é dívida que o council não podia ver porque olhou o código, não o disco.
4. **A cerimônia consolidada empacota riders de posturas de falha opostas.**
   #1/#2/#3/#5b endurecem para fail-closed; R1 é observabilidade advisória;
   RC3-F7 e ADR-110-AMEND-2 são outra coisa ainda. Um único sentinel GPG cobrindo
   tudo significa que um REJECT do pair-rail em qualquer rider trava todos. Vale
   pelo menos ordenar o Scope do sentinel para que os fixes fail-closed do
   canonical-edit sejam separáveis dos demais se o rail rejeitar um.

## What I would NOT change

1. **O dedup.** Está certo. #10 ≈ S276 B com o comentário falso ainda no lugar
   (verifiquei L877-879), #5 ≈ S276 E, #6 ≈ S276 F. E não re-litigar A/C/D do
   PLAN-160 é disciplina correta — confirmei que os três estão fixados no HEAD
   (`_PLAN160_MAX_CANDIDATES` L688/L1976, `_canonical_rel` L753+, o
   `_forced_out` fail-closed em L1975-1988).
2. **O fold #3+#8 (OQ2).** Não há razão para manter separados. Mesma classe
   ("guard-the-guardfiles"), mesma correção mecânica (entrada em
   `_CANONICAL_GUARDS` + ausência ⇒ fail-closed), mesma seção de teste, mesmo
   trecho de Scope. Ambos confirmados pelo oráculo em conjunto:
   `sentinel-signers-registry.yaml` → 0 e `.drift-manifest.json` → 0. Separá-los
   dobra a superfície de cerimônia sem nenhum ganho de revisão. **Mantenha o
   fold.**
3. **Pular W3.** O council custou 600 s/lane e egresso autorizado pelo Owner
   para produzir evidência ADVISORY. Testes red-first + pair-rail codex sobre o
   diff são verificação *mais forte* do que um re-run: provam a mudança, não
   re-opinam sobre o arquivo. A ratificação do Owner está certa.
4. **Não mexer em Layer-A v1 (nested MCP) por custo no hot path.** Concordo com
   a análise — com a ressalva de que ela colide com #11 (Unseen 1). Se o CEO
   mantiver Layer-A v1, a consequência coerente é **#11 → DOC-GAP**, não FIX.
5. **Não tocar literais de timeout do pair-rail.** Correto: é ADR-110-AMEND-2,
   outro debate, outra evidência (n=14). Misturar aqui contaminaria as duas
   decisões.

---

### Nota de método

Toda medida acima foi produzida no HEAD desta árvore, nesta máquina, com
`gpg-agent` saudável: 16 sentinels reais, oráculo `--is-canonical` para as
classificações, e um root falso em scratchpad para a reprodução do #2 (repo
intocado, com controle positivo). Nenhum número neste crítica foi herdado do
report do council sem re-execução. Onde não consegui provar — a
alcançabilidade do `ln` para o #2 — eu digo que não provei, em vez de arredondar
para "confirmado".
