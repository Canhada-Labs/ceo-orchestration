# GATE-V2 — probe fresco 2026-07-29: FAIL + diagnóstico de root cause

> Registro exigido pelo CEREMONY-RUNBOOK.md Passo 2 (evidência do gate).
> Verdito: **FAIL** — a invocação fresca pós-âncora fail-openou (case F).
> Status: **incidente do rail** (runbook: "NÃO prossiga com FAIL").

## Timeline do probe (padrão S281, bytes idênticos)

- Âncora: `sha=a4371c7` `ts=2026-07-29T10:16:16-03:00` (GATE-PIN-ANCHOR).
- Probe: Write de bytes IDÊNTICOS em `.claude/hooks/check_subagent_fabrication.py`
  (cópia verificada por `cmp` antes do Write; guard bloqueou como esperado —
  árvore intacta).
- Eventos emitidos (audit-log, sessão `6de4f28e`):
  - `pair_rail_review_expected` ts=2026-07-29T15:59:46Z review_id=6c34ff5c409df402
  - `pair_rail_outgoing_redaction_applied` (callsite `_invoke_codex_review`,
    bytes_scanned=2153) — redactor OK
  - `pair_rail_case` ts=2026-07-29T16:00:16Z: **case=F, claude_verdict=PASS,
    codex_verdict=TIMEOUT** (exatos 30 s após o expected)
- `--gate-v2`: pós-âncora expected=1 healthy=0 **failopen=1** → FAIL.
- Self-check do pin no gate: **OK** ("payload sha verified against the landed
  manifest") — a integridade ADR-182 está saudável.

## Root cause (medido, não inferido)

O default `CEO_PAIR_RAIL_TIMEOUT_S=30` é estruturalmente menor que a latência
real de um verdito codex:

| Medição (2026-07-29, mesma máquina) | Latência |
|---|---|
| `codex exec` trivial via launcher (`/opt/homebrew/bin/codex`) | 8,1 s |
| MESMA chamada do hook (payload pinado ADR-182, argv `build_verdict_argv`, `input=""`) — prompt trivial | 8,3 s, rc=0 |
| Idem com prompt realista de review (2.017 bytes, shape do rail) | **36,3 s**, rc=0, verdito PASS |

Config codex efetiva: `model gpt-5.6-sol`, `reasoning effort: xhigh`.
Overhead de startup ~8 s + raciocínio xhigh sobre um review real ⇒ >30 s
sempre. Consistente com o histórico: **12 de 12 `pair_rail_case` na vida
inteira do log são F/TIMEOUT** — o rail NUNCA completou um review vivo
in-hook. Os 11 case-F da janela 168h não eram um transiente que o pin
curaria: o pin corrigiu integridade (payload/verify-then-invoke), não
latência.

Descartados por evidência: stdin-hang (hook usa `input=""`), untrusted-dir
hang (cwd=repo), auth (round manual completa), payload errado (sha verify OK
+ round manual pelo MESMO binário completa).

## Restrições para o fix

1. Harness (settings.json, kernel): registration do hook tem `timeout: 60` —
   o budget interno precisa caber em ~60 s com overhead (startup python +
   redaction + validação do verdito). Teto interno prático ≈ 48–50 s.
2. O main-pack staged NÃO toca `check_pair_rail.py` (0 hits no MANIFEST) e
   mantém `timeout: 60` na registration — um fix de 1 arquivo no hook não
   conflita com os bytes congelados (double-APPROVE preservado).
3. Aritmética do gate: o log é append-only (HMAC) — o case-F fresco é
   permanente no conjunto pós-âncora. `failopen==0` é INSATISFAZÍVEL contra
   a âncora atual. Qualquer caminho de PASS exige RE-ANCORAR (nova cerimônia
   sentinel-tagged; o `--gate-v2` resolve âncora por ANCHOR_FILE, com
   fallback git-log pelo commit `[SENT-PLAN163-PIN]`).

## Opções (decisão do Owner)

- **A (recomendada): fix mínimo governado + re-âncora.** Cerimônia mínima
  (sentinel round novo, escopo = `check_pair_rail.py` apenas) subindo o
  default interno 30→48 s; a própria cerimônia re-escreve/atualiza a âncora;
  probe fresco → esperado healthy (36,3 s < 48 s); `--gate-v2` PASS → pack.
  Margem ainda apertada sob carga → registrar follow-up (PLAN-162) para o
  fix durável: registration 60→120 s (kernel, pós-pack) + interno ~100 s.
- **B: env-knob sem mudança de bytes.** Relançar a sessão com
  `CEO_PAIR_RAIL_TIMEOUT_S=50` exportado + re-rodar a cerimônia do pin para
  re-ancorar. Prova vale, mas o default da frota continua quebrado
  (adopters seguem 100% fail-open) e o re-run do pin com árvore idêntica
  pode morrer em commit vazio (sem handling no script).
- **C: incidente formal, pack adiado.** Tratar o rail primeiro em plano
  próprio, com folga para o fix durável de kernel; GATE-V2 e pack depois.

## Nota colateral

`stop_review` na janela: 1 evento nudge-only (review nunca rodou) —
transiente já conhecido (S284), fora do escopo do GATE-V2.
