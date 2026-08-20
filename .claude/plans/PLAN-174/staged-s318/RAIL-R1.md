# RAIL-R1 — pair-rail Codex do pack SENT-S318 (2026-08-20, S318)

Substrato: codex-cli **0.147.0** (o binário que o próprio pack re-pina;
rodada ADVISORY manual — o kernel de pin fail-closed cobre invocações
L3+ via hook, não o `codex exec` operado à mão; precedente S317).

## Como a rodada rodou

Duas invocações `codex exec review` full-auto (uma `--commit 5ba9cf6`,
uma `--uncommitted`) foram MORTAS em voo — o modo review decidiu montar
um land-sim próprio (cp do pack + pytest da suíte de hooks inteira num
TMP), pesado demais para a janela. A rodada válida foi UMA invocação
`codex exec --sandbox read-only` com prompt cirúrgico por área (A–F),
instruída a LER e DIFAR apenas, veredito em `--output-last-message`.

## Veredito bruto: REJECT — 1 P0, 5 P1, 3 P2 (9 achados)

## Triagem e disposição (cura no MESMO pack, salvo herdados)

| # | Área | Sev | Achado | Disposição |
|---|------|-----|--------|-----------|
| 1 | E | **P0** | O Scope ASSINADO nunca era comparado ao MAP executável do LAND — um MAP alterado aplicaria destinos fora do texto assinado sob sentinel válido | **CURADO**: G3 ganha set-equality NOME-a-nome Scope↔MAP (lição S272); divergência = ABORT com diff |
| 2 | E | P1 | Artefatos de cerimônia untracked garantiam abort do G6 PÓS-apply (touched-scope sujo) | **CURADO** por processo: LAND/draft/PACKMAP/BASELINE/MANIFESTs/RAIL-R1 são COMMITADOS antes da assinatura (commit 2 do prep) — o touched pós-apply volta a ser só MAP-dests + approved{,.asc} |
| 3 | E | P1 | Apply de 14 `cp` sem rollback — falha no meio deixava pack meio-aplicado | **CURADO**: `rollback_apply()` (git checkout dos tracked + rm dos novos) chamado em TODO abort pós-G5 (G6 escopo, G6 checks, G7 ×3) |
| 4 | E | P1 | Symlink no destino passava o G1 (hash segue link) e o `cp` escreveria fora do repo | **CURADO**: G1 exige arquivo regular não-symlink; G5 re-checa o destino antes de cada cp (defesa em profundidade) |
| 5 | A | P1 | `observe_rail_present` inferido por string: remover o rail DESLIGA o próprio positive control (auto-pass) | **HERDADO — NÃO CURADO AQUI**: comportamento pré-existente e deliberado (compat com adopter sem o rail, PLAN-154); o pack S318 não tocou essa lógica. Pauta nomeada para o dono (família PLAN-154/169): exigir controle de presença derivado (ex.: sentinela no repo) em vez de string-match |
| 6 | A | P1 | Negative control aceita store malformado (parse error ⇒ `rows=[]` ⇒ passa) | **HERDADO — NÃO CURADO AQUI**: mesma origem e mesmo dono do #5; registrado como pauta nomeada (parse error deve ser FAIL do controle, não vazio) |
| 7 | A | P2 | `publish()` omitia p99/advisory do step summary e o `✓` de sucesso dizia "p95/p99 within budget" com p99 estourado | **CURADO**: summary ganha cabeçalho de tetos + coluna p99 `(ok/BREACH-advisory)`; as 3 mensagens de sucesso dizem "p95 within budget (p99 advisory — see summary)" |
| 8 | C | P2 | `print()` final do unlock fora do try — BrokenPipeError podia abortar o lint após unlock válido | **CURADO**: print embrulhado em try/except (fail-open completo) |
| 9 | F | P2 | Draft citava "9 casos" no teste novo (são 12) e referenciava este RAIL-R1.md antes de ele existir | **CURADO**: draft corrigido para 12; este arquivo é o registro que faltava |

Áreas **B** (branch de scrub do `ceremony_lint_unlock_used`) e **D**
(manifest/range do re-pin): **NO FINDINGS** explícitos do revisor.

## Pós-cura

`bash -n` + shellcheck limpos nos scripts de cerimônia; set-equality
Scope↔MAP verificada contra o draft; `proof-retry-matrix.sh` re-rodada
11/11 contra o run-block re-editado do `validate.yml`; suítes-alvo
re-verdes no clone-sim (registro na §Prova do sentinel).
