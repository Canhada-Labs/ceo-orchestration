# wave-179fu — sentinel de aprovação (DRAFT: o SIGN preenche Data / Anchor-SHA / Approved-By e assina)

> Caminho casa `PLAN-*/wave-*-approved.md` (união fechada de padrões em
> `check_canonical_edit.py`). O binding é o `Patch-sha256` (land por PATCH, sem
> `MANIFEST-*`). O bloco `Scope:` é **DERIVADO** por
> `PLAN-183/w5-ceremony/finalize_patch.py` a partir de `git apply --numstat` —
> nunca escrito à mão. O `Anchor-SHA` é preenchido pelo
> `OWNER-S338-179FU-SIGN.sh` no momento da assinatura; o
> `OWNER-S338-179FU-LAND.sh` aborta no G1 se não casar. Reescrever um byte
> deste arquivo depois de assinar invalida o `.asc`.

Plans: PLAN-179
Wave: wave-179fu (PLAN-179-FOLLOWUP-sessionstart-anchor-id, AC item 1 + emenda S337 + rail r1 da S338 — os QUATRO produtores LEGADOS de ciclo de vida (`SessionStart.py` session_start, `UserPromptSubmit.py` prompt_submitted, `Stop.py` session_stop, `SessionEnd.py` session_end) passam a resolver o `session_id` PAYLOAD-first (payload > `CLAUDE_SESSION_ID` > timestamp), espelhando o `payload_sid` do rail novo; o consumidor US8 (payload-gated) e o rail novo ficam INTOCADOS; +9 testes (unidade ×4 actions, fallbacks env/timestamp ×4, trava ESTRUTURAL por AST invertida em-lugar, integração produtor→consumidor start E end). **DECISÃO RATIFICADA PELA ASSINATURA:** o AC nomeava 2 produtores; o censo mecânico do rail r1 provou que a classe tem exatamente 4 membros e que um flip PARCIAL fragmenta a sessão em dois ids para leitores que particionam por `session_id` — o Owner ratifica a expansão 2→4 ao assinar este Scope)
Patch: .claude/plans/PLAN-179/s338-followup-flip/W179FU.patch
Patch-sha256: ba5efe981865076e132f688b6b52741f8eb55ede877601cf6bb8ddc212dc021b
Patch-base: f0e98de30f420559cc6b7ac0b525f8410dcb3a26
Anchor-SHA: ab56e76f057f7cd6ad4a855cfb2a32590ef4a43e
Data: 2026-09-02

## O que esta wave entrega

**Quatro arquivos canônicos (todos KERNEL)** e **um livre** que só são
verdadeiros juntos — todos DERIVADOS de um único material versionado,
`s338-followup-flip/apply-179fu-flip.py` (11 edições com âncora exata,
contagem declarada e marcador `PLAN-179-FOLLOWUP (S338)` em todo substituto;
o LAND prova `HEAD + script == patch` byte a byte):

1. **`.claude/hooks/SessionStart.py`** — `main()`: `session_id` resolve
   PAYLOAD-first; fallback de timestamp inalterado.
2. **`.claude/hooks/UserPromptSubmit.py`** e **`.claude/hooks/Stop.py`** —
   idem (`prompt_submitted`, `session_stop`) — **os dois membros que o rail
   r1 trouxe** (censo: classe «produtor de ciclo de vida env-first» = 4
   sítios com a MESMA linha; `check_output_secrets.py:404-408` é env-first
   mas security-matcher — outra classe, declarado fora).
3. **`.claude/hooks/SessionEnd.py`** — `main()` legado (produtor do
   `session_end`) idem; `payload_sid` do rail novo e o consumidor
   `_session_start_ts` INTOCADOS (a trava `test_divergent_env_id_never_anchors`
   fica).
4. **`.claude/hooks/tests/test_session_end_memory_delta.py`** (livre): helpers
   que dirigem o `main()` REAL de cada hook (stdin JSON + env via
   `mock.patch.dict`); `TestProducerIdPrecedence` (as 4 actions gravam o id
   do PAYLOAD sob env divergente; fallback env ×4; timestamp ×4);
   `TestProducerConsumerAlignment` (start ancorado `chain`/`written`; end
   segmenta a janela do resume); o lock env-first da r12 P2-b vira lock
   payload-first ESTRUTURAL (AST) sobre os 4 `main()` — 52 → 60 testes.

## Evidência (S338; builder do Workflow + refutador independente + rail)

- Suíte de 21 arquivos **551 passed / 0 skipped / 2 xfailed** (pré-existentes);
  arquivo tocado 60/60; `check-hook-stdout-schema --only` ×4 → `4 wired
  script(s), 4 registration(s), 0 violation(s)`; active-hooks 0; env-hygiene 0;
  verify-counts 0; claims 0; ratchet 0.
- Controle positivo: 4 hooks em HEAD + testes novos ⇒ **7 failed / 2 passed**
  (RED exatamente os dependentes do flip; GREEN os 2 de preservação de
  fallback). Reproduzido pelo refutador em worktree próprio (`refuted=false`).
- Rail codex: r1 = 1 P1 REAL (→ classe fechada nos 4 produtores); r2 e r3 =
  só o item de PROCESSO (o sentinel que ESTA cerimônia produz) — ver
  `rail-round-*.md`.

## Kernel

Os 4 hooks ∈ `_KERNEL_PATHS` (`check_arbitration_kernel.py:218-221`). O LAND
arma `CEO_KERNEL_OVERRIDE` ele mesmo, no menor escopo (export antes do apply,
unset após o commit, backstop no trap), com o par reason-SLUG + `I-ACCEPT`
validado VIVO contra o contrato do hook — mecanismo idêntico ao fable51, ao
183batch (`b7dad83`), ao 179close (`bc82651`) e ao adrgate (`cfab980`).

## Residuais declarados

- `check_output_secrets.py:404-408` (env-first, security matcher) e ~20 emits
  env-ONLY em `_lib/`/`check_bash_safety.py` (atribuição best-effort, não
  precedência) — fora, por classe.
- O flip do `[x]` do AC item 1 e o registro da ratificação 2→4 no
  `PLAN-179-FOLLOWUP-…md` são do closeout (livre), não deste land.
- `dist/ceo-plugin/hooks/*` são build outputs gitignored — nada a commitar.
- O teste de integração da perna start espera <1,1 s no relógio real pela
  janela do consumidor (deliberado, documentado no teste).

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Plans: PLAN-179
Scope:
  - .claude/hooks/SessionEnd.py
  - .claude/hooks/SessionStart.py
  - .claude/hooks/Stop.py
  - .claude/hooks/UserPromptSubmit.py
  - .claude/hooks/tests/test_session_end_memory_delta.py
<!-- END SIGNED SCOPE -->
