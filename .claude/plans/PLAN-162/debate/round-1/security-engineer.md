---
plan: PLAN-162
round: 1
lane: security-engineer
archetype: Principal Security Engineer
skill: security-and-auth
veto_authority: true
created_at: 2026-08-03
---

# PLAN-162 round-1 — Security Engineer critique

## Verdict

**ADJUST** — a direção das 12 disposições está majoritariamente certa, mas a
proposta erra a CAUSA RAIZ do finding #1 (mede-se 17ms por GPG, não 15s: o
custo real é amplificação O(candidatos × sentinels)), propõe o fold errado
(#3+#8 em vez de #1+#10, que é o fold que fecha os dois de uma vez), e
**deixa fora do escopo um bypass P0 que eu VETO no merge**: em filesystem
case-insensitive — o padrão do macOS, a plataforma do Owner — `.claude/settings.JSON`
e `.claude/hooks/_lib/gpg_verify.PY` escapam dos DOIS rails e sobrescrevem
os arquivos reais.

---

## Summary

Verifiquei os 12 claims contra o HEAD (`check_canonical_edit.py`, 2165
linhas, último toque `8ed9f6f`). **Nenhum é STALE**; todos reproduzem, com
os line numbers deslocados. Confirmações objetivas:

| # | Claim | HEAD | Evidência |
|---|-------|------|-----------|
| 1 | GPG timeout 15s > budget 5s | **CONFIRMADO, causa raiz errada** | `check_canonical_edit.py:1011` (`timeout=15.0`) vs `settings.json` matcher `Edit\|Write\|MultiEdit\|mcp__.*` timeout=5. Mas ver §Risks R1 — o driver não é a latência. |
| 2 | symlink-reject só depth ≤2 | **CONFIRMADO** | `:857-867` checa `p`, `p.parent`, `p.parent.parent`; o pattern `PLAN-*/audit-v2/architect/round-*/approved.md` (`:847`) tem 5 segmentos → `audit-v2/` e `PLAN-*/` não são checados. |
| 3 | signer registry desguardado | **CONFIRMADO + assimetria pior que o descrito** | `.claude/security/sentinel-signers-registry.yaml`: canonical=**False**, kernel=**False**. O legacy `.claude/sentinel-signers.txt`: canonical=**False**, kernel=**True**. Ou seja: o legacy tem UM rail; o registry ADR-121 tem ZERO. |
| 4 | oversize → Tier-1→Tier-2 | **CONFIRMADO, reproduzido** | `:1122`. Com 64KiB+1 de padding o parser honra bullets FORA dos markers: reproduzi `{'.claude/team.md'}` (Tier-1) virando `{'.claude/team.md', '.claude/settings.json', 'PROTOCOL.md'}` (Tier-2). |
| 5 | parse_error → allow | **CONFIRMADO** | `:1903-1909`. |
| 6 | Layer-A nested MCP | **CONFIRMADO — e o mitigante não existe neste repo** | `:359-385`. Ver §Unseen U4. |
| 7 | `file://` sem scheme-strip | **CONFIRMADO** | `uri` em `_MCP_WRITE_PATH_KEYS:355`; `file:///…/.claude/team.md` → `_is_canonical` = **False** (o path absoluto equivalente = True). |
| 8 | `.drift-manifest.json` desguardado | **CONFIRMADO** | canonical=False, kernel=False. Arquivo existe em disco (544 B). |
| 9 | `blocked_tool` hard-coded | **CONFIRMADO — 3 call sites, não 2** | `:1186`, `:1308`, e `:1759` (`_audit_session_root_block`). `_audit_registry_unreadable:1738` usa `blocked_tool=""`. |
| 10 | cache key incompleta | **CONFIRMADO + comentário falso localizado** | `:894-916` — a key é `(path, ino, mtime_ns, size, sha256(conteúdo), target_rel, fmt)`. O comentário FALSO está em `:877-879` ("sha256_full transitively covers signer changes via .asc bytes" — o sha256 é do sentinel, não do `.asc`). |
| 11 | unicode guard só no file_path | **CONFIRMADO** | `:2134-2136`. |
| 12 | dispatcher YAML nested | **CONFIRMADO no rail canonical, mitigante MAIS FORTE que o descrito** | `.claude/dispatcher/sub/x.yaml`: canonical=False mas kernel=**True** via `.claude/dispatcher/**/*` — hard-deny SEM escape de sentinel. |

**Medições que mudam a disposição de #1** (repo real, 16 sentinels em disco,
todos com `.asc`):

```
1 GPG verify (warm)                        0.017 s
decide() bloqueando 1 path (16 sentinels)  0.217 s
40 alvos canônicos DISTINTOS granted       4.227 s   <- budget do hook = 5 s
extrapolado ao cap de 512 candidatos      54.1   s
```

E a amplificação é **plantável pelo agente**: `.claude/plans/PLAN-*/architect/round-*/approved.md`
não é guardado por rail nenhum (canonical=False, kernel=False). Em árvore
temporária, 60 sentinels plantados com `.asc` de lixo custaram 0,48 s →
**~628 arquivos triviais colocam TODO evento canônico acima do budget**.

---

## Risks

**R1 — a proposta trata #1 como problema de LATÊNCIA; é problema de TRABALHO.**
O fix proposto ("orçamento de verificação derivado do budget registrado, cap
de sentinels verificados") é um deadline. Um deadline por-sentinel não
resolve: N sentinels × deadline continua estourando. E um cap de sentinels
verificados é *pior* que o bug — parar de verificar sentinels é exatamente
como um sentinel legítimo deixa de conceder, transformando um controle de
integridade em roleta. O que precisa ser limitado é a CONTAGEM DE
VERIFICAÇÕES, e ela é hoje O(candidatos × sentinels) porque a cache
(`:894-916`) é chaveada em `target_rel`: o mesmo sentinel é re-verificado
criptograficamente uma vez por alvo distinto.

**R2 — fail-CLOSED por deadline é barato aqui, mas o rail já tem rota de
recuperação e ela precisa ser nomeada.** OQ3 supõe um trade-off que a medição
não sustenta: a cerimônia legítima custa 0,217 s contra um budget de 5 s —
margem de 23×. Não existe evento legítimo perto do teto. Mas todo gate
fail-closed sem rota de recuperação é um travamento: aqui a rota já existe
(`CEO_SENTINEL_UNLOCK` + `_ACK`, `:987-993`, que pula o GPG inteiro) e o ADR
tem de citá-la explicitamente como a saída sob carga patológica.

**R3 — `_BOOTSTRAP_REGISTRY_SHA256 = None` (`:88`) torna morto todo o ramo
post-GENESIS.** Hoje, falha de parse do registry → fallback silencioso para o
legacy (`:1070-1074`). Qualquer fix de #3 que dependa de "fail-closed
post-GENESIS" está escrevendo em código que não executa. O fix precisa ser
estrutural (guardar o arquivo), não comportamental.

**R4 — o fix de #9 pode abrir uma classe nova.** Trocar o literal por
`event.tool_name` injeta entrada influenciável pelo atacante num log
HMAC-encadeado que humanos leem e que `audit_tokens_allowlist` consome.
`tool_name` tem de passar por enum fechado / regex `^mcp__[a-z0-9_]+$` antes
de virar campo de auditoria.

**R5 — o fix de #4 como proposto ("oversize ⇒ reject fail-closed") pode
brickar sentinel legítimo**, e a métrica está errada: `:1122` compara
`len(text)` em CARACTERES contra `_SCOPE_MARKER_CAP_BYTES`. Verifiquei: um
arquivo de 40.175 chars / 80.175 bytes ainda entra em Tier-1. Trocar para
bytes muda o comportamento de arquivos que hoje passam.

---

## Must-fix

**MF-1 (P0 — VETO no merge; NÃO está nas 12 findings). Bypass por
case-insensitive filesystem, derruba os DOIS rails.**
`_match_segments` usa `fnmatch.fnmatchcase` (`check_canonical_edit.py:816`) e
`check_arbitration_kernel.py` usa a MESMA função case-sensitive. Em APFS/HFS+
(default do macOS — a plataforma deste repo) o arquivo é o mesmo:

```
kernel=False canonical=False  .claude/settings.JSON
kernel=False canonical=False  .claude/hooks/_lib/gpg_verify.PY
kernel=False canonical=False  .claude/hooks/check_canonical_edit.PY
kernel=False canonical=False  .claude/sentinel-signers.TXT
```

Reproduzi a escrita: criar `.claude/team.md`, escrever em `.claude/TEAM.md`,
ler `.claude/team.md` → conteúdo sobrescrito. Isso alcança o *kernel hard-deny*
nos arquivos que IMPLEMENTAM a verificação de assinatura (`gpg_verify`), o
registro de assinantes e o `settings.json` — todo o modelo de ameaça
(T-003, ADR-116 vetores 1 e 2) assume que esses caminhos são inalcançáveis.
Isto é estritamente mais severo que 10 das 12 findings e pertence a esta
cerimônia. Fix: comparar case-fold **quando o FS de destino for
case-insensitive** (detecção por probe, não por `sys.platform`), ou —
preferível, sem detecção — casar sempre com `fnmatch.fnmatch` normalizado
para lowercase nos DOIS hooks, aceitando o over-classify (direção segura) e
fixando o comportamento com teste red-first nos dois rails.

**MF-2. Re-diagnosticar #1 e FOLD #1+#10 (não só #3+#8).** A cache mistura
duas perguntas com custos e chaves diferentes:

- *"esta assinatura é válida?"* — cara (subprocess GPG), **independente do
  alvo**, e deve ser chaveada em `(bytes do sentinel, bytes do .asc, digest
  da allowlist, digest do registry)`;
- *"este escopo concede este alvo?"* — barata (parse de texto), dependente
  do alvo, sem subprocess.

Separá-las (a) elimina a re-verificação por alvo que produz os 4,2 s medidos,
e (b) coloca `.asc`/allowlist/registry na chave — que é literalmente o pedido
de #10. **Um patch fecha #1 e #10.** O fold #3+#8 (OQ2) está certo e não tem
razão para ficar separado, mas é o fold de menor valor dos dois.

**MF-3. O deadline de #1 tem de ser por EVENTO e fail-CLOSED, não por
sentinel.** Ao expirar: bloquear com `canonical_edit_hook_fault`, nunca
"allow por não ter conseguido decidir", e nunca "parar de verificar
sentinels". Com MF-2 aplicado, o deadline vira defesa em profundidade e não o
mecanismo principal.

**MF-4. Guardar o conjunto de sentinels (habilita o vetor plantado).**
`.claude/plans/PLAN-*/architect/round-*/approved.md` e `*.asc` não estão em
`_CANONICAL_GUARDS` nem em `_KERNEL_PATHS`. Enquanto o agente puder CRIAR
arquivos que `_find_sentinels` enumera, ele controla o custo do gate (~628
arquivos → guard desarmado se o harness fail-open no timeout) **e** o
conteúdo do sentinel durante uma janela de `CEO_SENTINEL_UNLOCK` do Owner.
Ver U2 — a segunda metade é auth bypass, não DoS.

**MF-5. Corrigir o dedup: #1 já é residual ACEITO no ADR-164.**
`ADR-164:119-129` registra "Near-cap all-granted GPG cost… Accepted; a future
mitigation… is a follow-up, not a blocker", com a premissa "requires 512
distinct validly-signed+scoped canonical paths — operationally absurd".
Minha medição **refuta a premissa**: 47 alvos bastam (não 512), e o vetor de
sentinel plantado não precisa de nenhum path concedido. Reabrir está certo,
mas o entregável tem de ser uma **revisão do §Residual do ADR-164**, não uma
finding nova — senão a cerimônia landa um fix que contradiz um ADR ACCEPTED
sem emendá-lo.

**MF-6 (OQ1). ACCEPT+DOC está certo, a justificativa não.** "Tier mais alto =
postura mais dura" não é um discriminador — é uma racionalização post-hoc. O
discriminador correto, e o que PLAN-152 C4 de fato diz, é *o que* falhou ao
parsear: **envelope de transporte** (INFRA → fail-open, ADR-010) vs **conteúdo
de `tool_input` que o matcher precisa ler** (INPUT → fail-closed). Em `:1907`
o `event.parse_error` cobre os DOIS. Antes de landar o ACCEPT é obrigatório
provar que `parse_error` nunca é setado com envelope bem-formado e
`tool_input` ilegível; se for, o ACCEPT está protegendo um fail-open de
classe INPUT com a citação de um ADR que fala de outra coisa. **Não concedo
ACCEPT em #5 sem essa verificação no adapter.**

**MF-7. #4: o fix mínimo não é rejeitar oversize.** É: *se o marker BEGIN
existir em qualquer ponto do texto, JAMAIS cair para Tier-2* — a presença do
marker já é sinal explícito de intenção do Owner e o código já fail-CLOSA
nesse princípio em `:1130`. Isso fecha a classe sem risco de brickar sentinel
grande legítimo. Rejeitar por tamanho é decisão separada e mais arriscada
(R5), e se for tomada precisa decidir chars-vs-bytes explicitamente.

**MF-8. #3: guardar o ARQUIVO, não inverter o `.exists()`.** "Ausência ⇒
fail-closed quando o dual-rail é esperado" exige uma definição de "esperado"
que não seja ela mesma editável pelo agente — caso contrário deletar um
arquivo passa a *escolher* a postura. Fix mínimo e sólido: pôr
`.claude/security/sentinel-signers-registry.yaml` no `_KERNEL_PATHS`
(espelhando `.claude/sentinel-signers.txt`, que já está lá) e em
`_CANONICAL_GUARDS`. Idem `.claude/policies/.drift-manifest.json` (#8).
Lembrete de cerimônia: estender `_CANONICAL_GUARDS` é KERNEL HARD-DENY —
exige `CEO_KERNEL_OVERRIDE=<slug>` + `CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT`
além do sentinel.

**MF-9. #9: varrer a FAMÍLIA (3 call sites) e validar `tool_name` (R4).**
`:1186`, `:1308`, `:1759` — mais `:1738`, que usa `blocked_tool=""` e ficaria
inconsistente se só os dois primeiros forem corrigidos.

**MF-10 (rider R1). Rejeito o desenho proposto para `check_budget.py`, por
dois motivos verificados.**

1. *A premissa está errada.* "zero enforcement" sugere que o skip custou
   enforcement. Não custou: `CEO_BUDGET_ENFORCE` default é `0` e o hook é
   **advisory-only por design** (`check_budget.py:2-7,75`) — mesmo com
   `plan_id` determinado ele não bloquearia nada. O que os 20 skips custaram
   foi **observabilidade**, e o breadcrumb já existe para `active_plan_count >= 2`
   (`:854-866`). O ganho real do fix é telemetria, não enforcement — e isso
   muda a prioridade dele.
2. *A heurística proposta contradiz o modelo de ameaça.* "plano do CWD/branch
   se derivável" reintroduz exatamente o que **T-001 (State-store poisoning
   via plan-id spoof)** mitiga: `docs/threat-model.md:207` registra a
   mitigação como *"audit-log-session-derived plan-id **not env var**"*.
   Derivar de CWD/branch é entrada spoofável. E "senão o de budget mais
   restritivo" é auto-DoS: o orçamento esgotado de um plano não relacionado
   passa a barrar trabalho em outro.

   Desenho que eu aceito: manter allow (é advisory), **sempre** emitir o
   breadcrumb + evento de auditoria com `active_plan_count` e a LISTA de
   plan-ids candidatos (contagem e ids de arquivo, sem eco de conteúdo), e
   resolver ambiguidade **apenas** por vínculo autoritativo — o plan-id
   derivado da sessão no audit-log, o mesmo mecanismo que T-001 já
   estabeleceu. Sem vínculo autoritativo: nunca escolher; reportar alto.

---

## Nice-to-have

- **#7: rejeitar, não normalizar.** Fazer scheme-strip de `file://` cria um
  acordo implícito entre o guard e o servidor MCP que de fato escreve. Se
  eles divergirem em qualquer detalhe (host component, percent-encoding,
  `file://localhost/…` — que também classifiquei False), volta o bypass numa
  forma nova. Postura mais segura e mais barata: um valor sob
  `_MCP_WRITE_PATH_KEYS` que **não** é interpretável como path de filesystem
  é entrada que o matcher não consegue parsear → fail-CLOSED (tratar como
  canônico). Over-trigger é a direção segura, e é o mesmo princípio que o
  oracle CLI já adota em `:1866-1869`.
- **#11:** o gap é mais fundo que "escanear todos os GRANTED". `_staged_content`
  (`:620-654`) devolve **um blob só** e não sabe qual conteúdo pertence a qual
  path. Escanear N paths com o mesmo blob dá falso-positivo e falso-negativo.
  O fix honesto é: enquanto não houver mapa path→content, escanear o blob uma
  vez e atribuir o bloqueio ao EVENTO (não ao path), documentando a
  imprecisão — ou implementar o mapa. Não vender cobertura por-path que o
  extractor não sustenta.
- **#12:** registrar o residual com a precisão que verifiquei — o mitigante
  não é "sem YAML nested em disco" (estado transitório), é
  `.claude/dispatcher/**/*` no `_KERNEL_PATHS` (**hard-deny, sem escape de
  sentinel**). Com essa formulação o ACCEPT fica robusto a alguém criar o
  YAML nested amanhã.
- Trailing slash: `<abs>/.claude/team.md/` classifica canônico=True
  (over-classify, direção segura). Sem ação; registrar para não ser
  re-flagado como bug em auditoria futura.

---

## Unseen

**U1 — o bypass por case (MF-1).** Não está nas 12. É o achado mais severo
deste round e o único que alcança o kernel hard-deny.

**U2 — o arquivo sentinel é o trust anchor e não é guardado; a janela
`CEO_SENTINEL_UNLOCK` fecha o laço.** O docstring em `:942-947` afirma que o
override env é dual-auth porque *"a sub-agent cannot forge the env vars"*.
Verdadeiro e **insuficiente**: o sub-agente não precisa forjar o env — ele
precisa do ARQUIVO, e o env quem fornece é o Owner. Como
`.claude/plans/PLAN-*/**/approved.md` não é guardado por rail nenhum (medido)
e `_find_sentinels` enumera qualquer `PLAN-*` (`:837-848`), um agente pode
escrever seu próprio `approved.md` com um `Scope:` arbitrário; se qualquer
`CEO_SENTINEL_UNLOCK` do Owner estiver ativo na sessão, `:994` pula o GPG
inteiro e esse sentinel **concede**. Isso é bypass de autorização, não DoS, e
está na minha faixa de VETO. Mitigação mínima nesta cerimônia: sob
`env_override`, aceitar apenas sentinels **rastreados no git** (`git
ls-files`) ou pré-existentes ao início da sessão — nunca um arquivo que
apareceu durante a janela.

**U3 — o dedup ignorou os RESIDUAIS aceitos, não só os fixes.** A tabela de
dedup cruza contra S276 e contra "PLAN-160 já FIXOU A/C/D". Não cruza contra
o §Residual risk do ADR-164, onde #1 já está aceito (MF-5). Regra para o
plano: dedup contra findings *fechadas* e contra residuais *aceitos* — um
residual aceito é uma decisão registrada, e contrariá-la sem emenda é drift
de governança.

**U4 — o mitigante de #6 não é verificável neste repo.** A disposição
DOC-GAP se apoia em "Layer B (server-side canonical_guard, PLAN-070) cobre
MCP writes por design". Procurei: **não existe** arquivo de implementação com
`canonical_guard` (as ocorrências são texto de ADR/SPEC e fixtures de teste) e
**não existe** `PLAN-070` em `.claude/plans/`. A disposição honesta é
ACCEPTED-BOUNDARY **sem controle compensatório neste repo** — postura mais
fraca que a proposta afirma. Se Layer B for do alvo instalado e não deste
repo, o DOC-GAP tem de dizer isso explicitamente.

**U5 — o custo de #1 não é só o do atacante.** Com 16 sentinels e cache por
alvo, uma cerimônia grande legítima (o pack consolidado que esta própria
PLAN-162 vai produzir, com dezenas de paths no Scope) caminha para o mesmo
teto: 40 alvos = 4,2 s. Ou seja, o fix de #1 não é só hardening — é
pré-requisito de liveness da cerimônia que vai landar estes fixes.

---

## What I would NOT change

- **Contrato ADR-010 de fail-open no envelope.** Concordo: falha de transporte
  é INFRA. A ressalva é só sobre o que `parse_error` de fato cobre (MF-6),
  não sobre o contrato.
- **Adiar Layer-A nested MCP (#6).** Parse profundo no hot path não fecha
  custo/benefício e o guard já é O(candidatos×sentinels) demais. Adiar sim —
  mas com o mitigante descrito honestamente (U4).
- **Não mexer nos literais de timeout do pair-rail.** Correto isolar em
  ADR-110-AMEND-2.
- **O cap `_PLAN160_MAX_CANDIDATES = 512` e o ramo over-cap fail-CLOSED**
  (`:1976-1988`). Está certo e é a única parte do caminho multi-candidate que
  não preciso tocar. Com MF-2 aplicado o cap pode até ser reduzido, mas não
  precisa ser.
- **Pular W3 (council re-run).** Concordo, e agora com razão mais forte que
  "o Owner ratificou": as medições deste round são **reprodutíveis
  localmente em segundos** (números em §Summary). Teste red-first + pair-rail
  codex cobrem melhor que um re-run de council que custa egress e quorum.
- **#12 ACCEPT e #6 DOC-GAP como classificação.** As disposições estão
  certas; só o texto do racional precisa de precisão (§Nice-to-have, U4).
