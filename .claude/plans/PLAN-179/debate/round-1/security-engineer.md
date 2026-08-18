# Security Engineer — PLAN-179 round 1

## Verdict

**ADJUST** — o diagnóstico (E1–E3) está verificado contra o disco e é sólido, mas
W1-b se contradiz (imunidade "por construção" vs conjunto definido em `.md`
desprotegido) e o write-gate de W4 nasce fail-OPEN; os dois P0 têm de cair antes
de W1-b congelar o desenho.

## Summary

O plano cria três superfícies novas de confiança e trata as três como se fossem
armazenamento: (1) **restrições fixadas** — texto que entra no fluxo de instrução
do modelo no instante de MÁXIMA degradação (pós-compactação), proposto num path
que nenhum rail guarda; (2) **escopo de sessão** do scratchpad — que reabre
exatamente o canal `env` que a consenso M2 proibiu, com colisão de namespace
possível contra escopos `PLAN-NNN` reais; (3) **ledger** — persistência re-lida
por sessões futuras, cujo gate de escrita é construído sobre um scanner
declaradamente fail-open e com histórico de sobre-redação.

O precedente que decide o P0 já está no repo e é literal:
`.claude/plans/PLAN-*/spec.md` é canonical-guarded **porque é injetado verbatim
em prompts de sub-agente** (`check_canonical_edit.py:206-210`, FINDING-14 /
ADR-058). O `pinned-constraints.md` é injetado no contexto do **próprio CEO** — é
o caso mais forte, não o mais fraco — e o plano o coloca fora de qualquer guarda.

## Risks

### P0-1 — Conjunto fixado num path sem guarda = canal de injeção privilegiado
`.claude/plans/PLAN-179-…md:298-302` (US5c) define o conjunto mínimo em
`.claude/plans/PLAN-179/pinned-constraints.md`. Confrontei a lista de guarda:
`check_canonical_edit.py:178-241` cobre `.claude/adr/ADR-*.md`, `SPEC/**`,
`PROTOCOL.md`, `.claude/plans/PLAN-*/spec.md`, `PLAN-*/canonical/*`,
`PLAN-*/corpus/locked/**` — **`PLAN-179/pinned-constraints.md` não casa com
nenhum**. Qualquer agente com Write reescreve as "restrições de governança" que o
modelo relê pós-compactação, sem sentinel, sem cerimônia, sem evento.
Regra violada: red flag "trust boundary break" + Fail-Fast Rule da skill.

### P0-2 — W1-b afirma imunidade que o próprio artefato falsifica
`PLAN-179…md:295-297` (US5b): restrições fixadas são "um conjunto FECHADO e
versionado, definido no repo, **não derivado de disco em tempo de execução** — o
que as torna imunes ao Compaction-Eviction Attack por construção". `:298-302`
(US5c) define esse conjunto num arquivo `.md` **em disco**. As duas afirmações não
podem ser verdadeiras juntas. Se o hook lê o `.md` em runtime, a imunidade é
falsa E abre um canal novo (P0-1); se o hook embute o conjunto em código, o `.md`
é documentação e vira fonte de drift silencioso. Rule 4 da minha framing
(implementação diverge do threat model ⇒ REJEITAR, não racionalizar).

### P1-3 — Fallback de escopo-sessão reabre a proibição M2 (env-spoofável) e colide de namespace
`scratchpad_lib.py:103-133` recusa derivar plano de env (doutrina M2), **mas**
`_resolve_session_id` (`scratchpad_lib.py:91-100`) cai em `CLAUDE_SESSION_ID` do
ambiente quando o argumento é `None`. W1 (`PLAN-179…md:266-274`) propõe usar o
session-id como ESCOPO de store. Consequências verificadas:
- `_validate_plan_id` (`state_store.py:145-159`) aceita qualquer
  `[A-Za-z0-9_.-]{1,64}`. Um `CLAUDE_SESSION_ID=PLAN-179` produz um store
  **idêntico** ao escopo de plano real — sobrescrita cross-scope, sem separação
  de namespace.
- O lado de leitura (`check_postcompact_reinject.py:80-88, 91-116`) usaria o
  mesmo derivador: plantar um snapshot num escopo escolhido e depois fazer uma
  sessão futura lê-lo é **injeção de ponteiros de governança entre sessões**.
Hoje isso está fechado só porque o escopo vem do audit-log.

### P1-4 — A claim "secrets-redacted" é FALSA no caminho realmente usado
`check_precompact_continuity.py:319` grava `payload.encode("utf-8")` — **bytes**.
`state_store.py:296-306`: redação só ocorre para `str`; "bytes are trusted".
Logo o snapshot **nunca** passa por `redact_secrets`. A afirmação contrária está
em `check_precompact_continuity.py:39-41` e `:300-301`, e — pior — na superfície
canônica: `SPEC/v1/audit-log.schema.md:516` ("o snapshot vive no plan-scoped,
**secrets-redacted** scratchpad"). W2 (`PLAN-179…md:330-332`) torna esse blob o
ÍNDICE do ledger, com conteúdo mais rico: a claim falsa passa a ser carregadora.

### P1-5 — Write-gate de W4 nasce fail-OPEN, contra o CLAUDE.md §4
`injection_patterns.scan_harness_mimicry` devolve `ScanResult(False, …)` para
entrada não-`str` (`injection_patterns.py:196-197`) e para falha de compilação
(`:212-213`), e engole exceção por padrão (`:229-230`). Um gate que DESCARTA no
hit e ACEITA na falha de scan admite precisamente o payload que quebrou o
scanner. CLAUDE.md §4 é explícito: "fail-open on infrastructure, **fail-closed on
input**", com precedente nomeado (`_e3` em `check_bash_safety.py`).

### P1-6 — US14 descreve errado a rota citada e cria auto-DoS de continuidade
`PLAN-179…md:394-397` diz "mesma rota do Step-4 do `/ceo-boot`. Hit ⇒ entrada
DESCARTADA, nunca redigida". A rota citada faz o **oposto**: `ceo-boot.py:273`
retorna `"[REDACTED-INJECTION-PATTERN]"`. E o catálogo é largo demais para um
gate de descarte: `\bYou are a\b` (`injection_patterns.py:127`), `^\s*Human:\s`
(`:124`), `^\s*Assistant:\s` (`:125`), `<system[-_ ]?reminder>` (`:96`) — todos
aparecem em texto LEGÍTIMO deste repo (prompts de spawn, transcripts de debate,
citações de ADR). Um ledger que registre "spawnei um agente `You are a Principal
Security Engineer`" é descartado. Vira ataque de disponibilidade: qualquer
conteúdo `agent-returned` que carregue um desses tokens **suprime o checkpoint**
— e o mecanismo existe justamente para não perder estado. Precedente de
sobre-redação com este mesmo scanner: `ceo-boot.py:259-262` (Codex S82 P0 #3,
"always truthy → over-redaction of clean strings").

### P1-7 — OQ-1 respondida: o acúmulo órfão é real, ilimitado e fora do repo
`check_precompact_continuity.py:319` grava **sem `ttl_seconds`** ⇒ `expires_at`
NULL (`state_store.py:315-318`). `prune_expired` (`:397-405`) só apaga linhas com
expiry e **nunca remove o arquivo** `.sqlite`/`.lock`. Raiz:
`$HOME/.claude/projects/<project>/state/scratchpad/` (`state_store.py:123-126`) —
fora do repo, fora do git, fora do CI. Com escopo por sessão, cada sessão deixa
um par de arquivos permanente contendo caminhos de plano, rótulos de checkbox,
paths de script de cerimônia e prefixo de HMAC — **não redigidos** (P1-4).

### P2-8 — US15/US15b apontam para um arquivo que não existe
`PLAN-179…md:398-412` alvo `THREAT-MODEL-WORKSHEET.md §2`. No disco não existe.
Existem `docs/threat-model.md` (o canônico, vigiado por
`.claude/scripts/check-threat-model-freshness.py:46`, que **vira o status para
`stale`** quando ≥2 ADRs landam sem revisão) e a referência de skill
`.claude/skills/core/security-and-auth/references/threat-model-worksheet.md`.
O plano landa exatamente 2 ADRs ⇒ flip garantido, e nenhum AC cobre o canônico.
Classe conhecida do repo: "cura no corpo ≠ cura nas REFERÊNCIAS".

### P2-9 — §7 subdeclara a cerimônia
`check_canonical_edit.py:139-144` guarda `.claude/hooks/*.py` e
`.claude/hooks/_lib/**/*.py`; `:171` guarda `.claude/settings.json`; `:181-182`
guarda `SPEC/**`. W1/W2/W4 tocam `scratchpad_lib.py`,
`check_precompact_continuity.py`, `check_postcompact_reinject.py`,
`check_ledger_checkpoint.py` (novo, + registro em settings.json),
`ledger_provenance.py`, `audit_emit.py` e um bump de SPEC — todos sentinel-gated.
§7 (`:460-467`) lista cerimônia só para os 2 ADRs. Escopo de sentinel incompleto
= `touched − scope ≠ ∅` na hora de landar.

### P2-10 — `context_pressure_observed` (US2) e OQ-4
Ação nova exige `_KNOWN_ACTIONS` + branch `_scrub_*` dedicada + allowlist + bump
de SPEC, senão o emit é descartado (padrão visível em `audit_emit.py:846,858,
6790,6816` e no contrato `SPEC/v1/audit-log.schema.md:516`: "Routes through the
dedicated `_scrub_*` branch … NEVER `_EMIT_GENERIC_PASSTHROUGH`"). Só inteiros
(float em campo coberto por HMAC descarta o evento inteiro). Sobre OQ-4: não
achei rotação do audit-log; cada emit custa filelock + append na cadeia HMAC, cuja
verificação é linear. Level-triggered é auto-inflação.

### P2-11 — A decisão de canal (W0-1) carrega junto uma decisão de sanitização
Se `additionalContext` for inerte e a rota migrar para
`SessionStart(matcher=compact)` com **stdout puro** (`PLAN-179…md:227-232`), o
payload deixa de ter chave/estrutura e vira texto livre no contexto. A
sanitização atual (`check_postcompact_reinject.py:65-70`) só tira control chars —
o próprio módulo admite em `:154-157` que "control-char strip != semantic-injection
neutralize". Restrições fixadas viajando nesse canal sem marcador não-forjável é
regressão de fronteira, não mudança de transporte.

## Must-fix

1. **US5c vira código, não `.md`.** O conjunto fixado nasce como constante em
   `.claude/hooks/_lib/` (já canonical-guarded, `check_canonical_edit.py:142-144`);
   o `.md` é documentação derivada, com teste que assere `set(md) == set(código)`.
   Resolve P0-1 e P0-2 juntos e torna a frase "não derivado de disco" verdadeira.
   **Resposta à OQ-2:** critério de corte = só invariantes cuja violação é
   irreversível (vetos ADR-052, sentinel canônico ADR-031, "não commitar sem
   autorização do Owner", fail-closed em input); mudança = **cerimônia**, nunca PR
   normal — é a superfície de instrução mais privilegiada do desenho.
2. **Escopo de sessão nunca vem de env.** Usar SOMENTE `event["session_id"]` do
   hook input; se o valor veio de `CLAUDE_SESSION_ID`, recusar o fallback e
   registrar `snapshot_outcome=…`. Prefixar e validar a forma
   (`session-[0-9a-f-]{36}`) para impedir colisão com escopos `PLAN-NNN`
   (`state_store.py:145-159` não separa namespace).
3. **Corrigir a claim de redação** — redigir explicitamente antes do `encode`, ou
   gravar `str`; e corrigir `SPEC/v1/audit-log.schema.md:516` +
   `check_precompact_continuity.py:39-41,300-301` na MESMA cerimônia.
4. **Write-gate fail-CLOSED**: wrapper que distingue "escaneado limpo" de "não
   consegui escanear"; o segundo é tratado como hit. Sem isso, US14 é teatro.
5. **Descarte VISÍVEL e escopado**: só conteúdo com proveniência `agent-returned`
   / `external-tool` (US13) passa pelo scanner; `owner-instruction` e
   `ceo-derived` nunca. Todo descarte emite evento + deixa marcador no ledger
   ("entrada rejeitada, família=X") — descarte silencioso perde o estado que o
   plano existe para preservar. FPR medida em janela advisory antes de qualquer
   enforcement (mesma disciplina do ADR-191).
6. **TTL + GC** (OQ-1, sim, precisa): `ttl_seconds` na escrita de continuidade e
   um GC que remova stores de sessão obsoletos (arquivo, não só linhas), com teto
   de contagem. Registrar retenção no threat model — hoje é crescimento ilimitado
   em `$HOME`, fora do repo.
7. **Retargetar US15/US15b para `docs/threat-model.md`** e acrescentar AC de
   closeout re-rodando `check-threat-model-freshness.py` (2 ADRs ⇒ flip certo).
8. **§7 enumera o escopo de sentinel completo** (6 hooks + settings.json + SPEC).

## Nice-to-have

- Tirar o Constraint Pinning de trás de `CEO_COMPACTION_CONTINUITY=0`
  (`check_postcompact_reinject.py:224`): hoje um kill-switch de continuidade
  desarmaria também a preservação de governança. Se ficar, o desarme emite evento.
- W2: a fronteira de unidade deve ser **estrutural** (o commit tocou path do
  plano?), nunca semântica sobre o conteúdo do ledger.
- US8 (SessionEnd): orçamento de 1,5 s (research §1.4) — o scan de delta precisa
  de deadline próprio, senão o emit morre calado.
- `context_pressure_observed` **edge-triggered** (só na transição de bucket): é
  amostragem com semântica, não taxa arbitrária.

## Unseen

- **O ledger vai para o git?** Este é o repo público/canônico. Ledger com
  excerto de transcript vira conteúdo publicado — CLAUDE.md §4 "No contamination".
  Precisa de regra explícita (só identificadores verbatim, nunca corpo) e do
  `check-contamination` do CI cobrindo o path novo.
- **Quem lê o ledger é uma sessão FUTURA** — o threat model de US15 tem de tratar
  leitura como fronteira, não só escrita: agrupar por confiança da fonte e marcar
  entrada externa na renderização (defesa de leitura do survey, research §2.5).
- **Reversão**: o plano tem `post-deletion verification` (US15c) mas nenhum
  primitivo de **rollback** do ledger (snapshot versionado com diff auditável) —
  é a defesa de armazenamento que o próprio research §2.5 nomeia.

## What I would NOT change

- **O diagnóstico E1/E2.** Verificado: `resolve_plan_id`
  (`scratchpad_lib.py:144-152`) filtra por `session_id` E exige `plan_transition`;
  a anti-correlação com sessões longas é estrutural, não conjuntural.
- **Pointers-only fechado como não-objetivo** (`PLAN-179…md:207`). A análise em
  `check_postcompact_reinject.py:148-159` está certa e não deve ser reaberta —
  W1-b acrescenta um conjunto FECHADO definido por nós, o que é categoria
  diferente de "injetar corpo de arquivo".
- **W0 como gate read-only antes de W1.** Manter. Sonda de canal ≠ sonda de
  evento é a lição que gerou este plano.
- **Ledger ADVISORY primeiro.** Correto e coerente com ADR-191 measure-first.
- **Sem RAG/vetor.** Correto para stdlib-only; e reduz superfície.
