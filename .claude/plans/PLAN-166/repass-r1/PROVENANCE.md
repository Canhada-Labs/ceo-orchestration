# Proveniência do re-pass round 1 — v1.3.0-rc.1 (ADR-103 hold)

Registro de invocação para auditoria (fecha o P2 do review pré-commit de
2026-08-05: "an auditor cannot substantiate this provenance statement
from the cited bundle").

## Invocação (comando COMPLETO de captura — emenda r18)

```
nohup codex exec --sandbox read-only --color never \
  --output-last-message <out>/verdict-r1.txt \
  - < payload.redacted.txt > <out>/transcript-r1.log 2>&1 &
```

O `transcript-r1.log` é o stdout+stderr COMPLETO do processo (redirect
`> ... 2>&1` do harness da sessão, não `tee`); `verdict-r1.txt` é a
última mensagem do modelo via `--output-last-message`. Exit status do
processo: 0 (launcher `nohup` em background; conclusão confirmada por
watcher de processo + presença do verdict não-vazio — o transcript
termina no bloco final do reviewer, sem truncamento).

- Executada de: raiz do repo (`~/canhada-labs/ceo-orchestration`)
- Data: 2026-08-05 (~01:30Z), sessão S294
- stdin: `payload.redacted.txt` (sha256 no MANIFEST — é o `inputs_hash`
  citado no plano: `c89acd4a…`)

## Metadados do harness (header do transcript, linhas 1-11)

| Campo | Valor |
|---|---|
| CLI | OpenAI Codex v0.144.6 |
| model | gpt-5.6-sol |
| provider | openai |
| approval | never |
| sandbox | read-only |
| reasoning effort | xhigh |
| reasoning summaries | none |
| session id | 019fcf82-0744-7600-9627-57a43f053862 |

## Pin ADR-182 (verificado ANTES da invocação)

`python3 .claude/hooks/check_pair_rail.py --verify-codex-pin` → rc=0:

```json
{"status": "verified", "detail": "ok",
 "path": ".../@openai/codex-darwin-arm64/vendor/aarch64-apple-darwin/bin/codex",
 "sha256": "80a3933d11a9d13ef806aa24f7bb8afc9169cfe4e9b09d6da6a92922cbde9cff",
 "expected_sha256": "80a3933d11a9d13ef806aa24f7bb8afc9169cfe4e9b09d6da6a92922cbde9cff",
 "target_triple": "aarch64-apple-darwin"}
```

Byte-exato com o `codex_payload_sha256` do verdito da rc.1
(`.claude/governance/pair-rail-verdict-v1.3.0-rc.1.md`).

## Artefatos

- `transcript-r1.log` — transcript completo da invocação (echo do
  payload + trabalho do reviewer). sha256:
  `3c7ade7fbe85d1623c3831d06843ddfcbc69e76eec050dfe6c1bf29978fb1f0f`
- `verdict-r1.txt` — `--output-last-message` (a última mensagem do
  modelo, verbatim).

## Escopo do inputs_hash (emenda r3 — honestidade da claim)

O `inputs_hash` cobre o **PAYLOAD** (prompt+diff redigidos via ADR-114).
Ele NÃO cobre as leituras que o reviewer fez por conta própria:
`--sandbox read-only` permite tool-reads da árvore viva, e o
`transcript-r1.log` mostra o reviewer abrindo arquivos do checkout além
do payload (comportamento esperado do `codex exec` — foi assim que ele
verificou claims contra o código). Essas leituras não passam pelo
redactor nem entram no hash. Estado da árvore na invocação: **limpa em
`b9ee6c4`** (mesmo anchor do verdito da rc.1; repo público; verificado
por `git status` no boot da sessão — sem conteúdo não-commitado
exposto). Para os re-passes de W2 o protocolo passa a ser snapshot limpo
da RC (worktree da tag) com estado da árvore registrado aqui.

## Desvio registrado (honestidade do registro)

Um smoke de autenticação (`codex exec ... "Reply with exactly:
SMOKE_OK"`) rodou ANTES da verificação de pin, invertendo a ordenação M4
(Gate 4 → Gate 3b). O pin verificou em seguida como byte-exato com o
binário já ratificado; nada se materializou, mas a ordem foi errada e
fica registrada. Contexto: `pair-rail-gate.sh --phase 6` é inexecutável
nesta máquina (Gate 1 exige `OPENAI_API_KEY`; o codex autentica por
login) — dívida registrada no plano.
