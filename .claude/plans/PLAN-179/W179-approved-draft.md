# W179-approved — sentinel do pack de continuidade de contexto (DRAFT — assinar como W179-approved.md)

> Assinatura em um passo: `! bash ~/canhada-labs/OWNER-W179-SIGN.sh`
> (gera este arquivo com Anchor-SHA real, assina, dry-run, land).

Plan: PLAN-179
Wave: W0 (sonda + medição) + W1 (cura do snapshot vazio) + W1-b (Constraint Pinning)
Anchor-SHA: <HEAD-NO-MOMENTO-DA-ASSINATURA>
Data: <AAAA-MM-DD>

## Autorização de governança

- **Debate L3 cumprido:** round-1 na S312 (`PLAN-179/debate/round-1/consensus.md`,
  3× ADJUST / 0 VETO, veredito PROCEED) com as 9 emendas de consenso aplicadas
  ao plano. `status: reviewed` ratificado pelo Owner em 2026-08-18 (`a71229e`).
- **Emenda 8.2 (escopo da cerimônia):** UM sentinel cobre TODOS os paths
  tocados — não apenas os ADRs. O bloco `## Scope` abaixo é verificado
  MECANICAMENTE contra o manifesto do pack pelo gate G2b do land script; se
  divergir em qualquer direção, o land aborta.

## Scope

<!-- SCOPE-BLOCK — gerado do MANIFEST.sha256 do pack; não editar à mão -->
```
.claude/adr/ADR-153-compaction-continuity.md
.claude/hooks/_lib/audit_emit.py
.claude/hooks/_lib/pinned_constraints.py
.claude/hooks/_lib/scratchpad_lib.py
.claude/hooks/check_compact_pinning.py
.claude/hooks/check_postcompact_reinject.py
.claude/hooks/check_precompact_continuity.py
.claude/hooks/tests/test_audit_emit_api_contract.py
.claude/hooks/tests/test_check_compaction_continuity.py
.claude/hooks/tests/test_plan179_integration.py
.claude/scripts/probes/probe_postcompact_channel.py
.claude/scripts/tests/test_probe_postcompact_channel.py
.claude/settings.json
SPEC/v1/audit-log.schema.md
```

## O problema que este pack fecha

A prova viva exigida pelo ADR-153 foi cumprida e o resultado foi **NEGATIVO**:
o autocompact real de 2026-08-16T09:34Z disparou os dois hooks e entregou
nada — `plan_id=unknown`, `snapshot_outcome=scratchpad_unavailable`,
`snapshot_found=false`, `pointer_count=1`.

A causa é ESTRUTURAL, não um bug de borda: `resolve_plan_id` exige um evento
`plan_transition` **da própria sessão**, e transição só ocorre em mudança de
status de plano — censo real: **2 eventos em 12.515 linhas de audit log**,
ambos de outra sessão. Ou seja, a continuidade só funcionava em sessões
curtas, exatamente as que não precisam dela. O "residual risk #3" registrado
no ADR-153 era o caminho **dominante**.

## O que muda

1. **Fallback por escopo de SESSÃO** (W1): quando não há plano resolvido, a
   escrita de continuidade não é mais pulada — cai para um store de sessão
   com `store_name` PRÓPRIO e `scope_kind` no blob, nunca sobrecarregando o
   campo `plan_id` (o invariante de isolamento por plano fica intacto). O
   `session_id` vem SOMENTE do input do hook: se viesse de env var seria
   spoofável por agente, então esse caminho é RECUSADO explicitamente.
   Escrita com `ttl_seconds` explícito + GC limitado de arquivos órfãos.
2. **Novo outcome `written_session_scope`** no enum fechado. A partir daqui
   `scratchpad_unavailable` significa falha real de I/O — não "não achei o
   plano". A distinção é o que torna a métrica honesta.
3. **Constraint Pinning** (W1-b): ponteiro não é restrição. As invariantes de
   governança viram **constante de CÓDIGO** em `_lib/` (nunca lidas de um
   `.md` em runtime — é isso que torna "não derivado de disco" verdadeiro por
   construção) e são entregues por **canal próprio**
   (`SessionStart` com `source=compact`), com orçamento SEPARADO do dos
   ponteiros: o cap de ponteiros nunca trunca uma regra de governança. O
   PostCompact segue como reforço, então a wave não fica refém do veredito de
   canal da sonda.
4. **Claim falsa corrigida** (emenda 8.3): `state_store` só redige `str`, e o
   snapshot gravava `bytes` — a promessa "secrets-redacted" era **falsa no
   caminho realmente usado**. Corrigida no código e nas três superfícies que a
   afirmavam (docstring do módulo, docstring da função, SPEC).
5. **`context_pressure_observed`** (W0/emenda 8.1): ação nova de audit, enum
   fechado, inteiros com a unidade no nome (float sob HMAC descarta o evento
   inteiro), **edge-triggered** — emite só na transição de bucket, para medir
   sem destruir a série.
6. **Sonda de canal** (W0-1) e seu **controle positivo**: operator/local-only,
   recusa rodar em CI, dois canários numa única compactação paga. Uma sonda
   que não falha é sonda morta — o controle prova que ela falha.

## Premissas do plano que caíram na execução (registradas, não escondidas)

- **W0 não era read-only** como dizia o §7 do plano: `audit_emit.py` e o
  progress-guard são superfícies canônicas ⇒ W0 entra nesta cerimônia.
- **O progress-guard não pode HALTAR** a compactação: o hook PreCompact não
  tem canal de deny (`gate()` retorna `{}` por contrato) e o harness já
  decidiu compactar quando o dispara. Entregue honestamente como
  **observe+notify**, com o piso numérico desabilitado por padrão até `F` ser
  medido — um piso inventado seria pior que nenhum.

## Fora deste pack

W2 (ledger de fronteira de trabalho) e W4 (governança do estado durável)
seguem em waves próprias; W3 (redução do piso `F`) landa por commit normal
por ser superfície livre. O corte da v1.4.0 não depende deste pack.
