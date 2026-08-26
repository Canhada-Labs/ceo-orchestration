# PROPOSED-PATCH — wave-s328-B (PLAN-169): segunda chave relativa do gate hook-latency, fase 1 ADVISORY

Patch: `.claude/plans/PLAN-169/s328-ceremony-B/B.patch`
Patch-sha256: e635498ac63422537574a5ce9229d36a1ef11bc7c4aaa2f157c25b048d5e0950
Base: ver `BASE-SHA.txt` (o `finalize_patch.py` recusa uma sombra cuja base não
seja o HEAD vivo, e grava o mesmo sha no `Patch-base:` do sentinel)

---

## 1. O quê

Três arquivos **canônicos**, nenhuma linha removida:

| path | +/− | papel |
|---|---|---|
| `.github/workflows/validate.yml` | +3 / −0 | 2 flags de argv no `run_gate`; 1 `note()` no `PYSUM` |
| `.claude/adr/ADR-163-hook-latency-gate-percentile-stability.md` | +221 / −0 | emenda que DECIDE a segunda chave |
| `.claude/adr/ADR-144-subagent-model-tiering-frontmatter.md` | +57 / −0 | emenda que REFUTA o §S220 |

A **lógica inteira** (referência `ref_exec`, classificador, rótulos, exit map,
auto-cap de wall) vive em `.claude/scripts/profile-opus-4-7.py` e no seu teste
`.claude/scripts/tests/test_hook_latency_relative_gate.py`. Os dois são
**NÃO-canônicos** (oráculo `--is-canonical` responde `0` para o profiler) e
entram no `main` por commit comum, **fora** deste pacote. Este patch é
exatamente a superfície que exige assinatura — e nada além dela.

O diff canônico mínimo é o que o desenho ratificado prescreve
(`gate-design-S328.json` → `canonical_diff_minimal`): duas linhas de argv
inseridas **depois** de `--p99-ceiling-ms 160` e antes de `--p99-advisory`, e
uma `note()` a mais no bloco `publish()`.

## 2. Por quê

O gate de hook-latency reprovou o `Validate` com um veredito **falso**, e a
sonda que existe justamente para detectar isso disse que o runner estava bem.
Três pernas, todas verificadas em disco nesta sessão:

- **Run `32866209415`** (`a16ac96`): `check_output_secrets` p95
  **361,4 / 424,8 / 229,1 ms** contra o teto duro de 180 ms, com a sonda de
  contenção (PLAN-161 C4) lendo **UNCONTENDED a 7,76 ms** de piso de spawn e
  concedendo a 3ª tentativa — cuja falha virou o veredito «real regression».
- **Os mesmos bytes são rápidos em outro lugar:** 70–77 ms local no mesmo SHA.
- **Os mesmos bytes PASSARAM 3 h 22 min antes** (`6304f66`, run
  `32845976838`), e `git diff 6304f66..a16ac96 -- .claude/hooks/` toca **0
  arquivos** (medido: `git diff --name-only ... | wc -l` = 0).
  `check_output_secrets.py` está inalterado desde **2026-07-02** (`7df843d`,
  confirmado por `git log -1`). Bytes idênticos: PASS, depois FAIL.
- **Não foi uma janela ruim:** em `56f050c` (run `32758192634`) o mesmo campo
  foi de p95 209 ms para **435 ms num rerun do commit idêntico**, com a sonda
  UNCONTENDED o tempo todo.

**A causa estrutural.** `python3 -c pass` precifica a CRIAÇÃO de processo. A
entrada que estoura faz outra coisa: importa preguiçosamente um fecho `_lib` e
depois faz uma escrita travada e fsyncada. Um runner lento-mas-não-contendido
move esse trabalho várias vezes deixando o piso de spawn plano. A sonda é cega
**por construção** — nenhuma recalibração do seu limiar de 200 ms pegaria
nenhum desses runs.

**A cura não é mexer no teto.** Ele já foi movido 120 → 180 com evidência, e o
espalhamento aqui documentado (209 → 435 ms num commit) não admite teto que
sobreviva ao runner E ainda detecte regressão. Entra uma **segunda chave**,
medida na mesma janela de escalonador, e a fase 1 dela é **advisory**.

## 3. Medições feitas para este pacote

Todas no checkout vivo, com o profiler já curado, `PYTHONDONTWRITEBYTECODE=1`:

- **Suíte do gate:** `42 passed in 0,57s`, rc 0.
- **Execução REAL curta** (`--latency-iterations 30 --p95-ceiling-ms 180
  --p99-advisory --exec-reference --relative-advisory`): rc 1 (a máquina estava
  sob carga de 12 agentes; p95 acima de 180 ms — exatamente o exit de hoje,
  que é o contrato da fase 1). O relatório trouxe `phase=1-advisory`,
  `verdict_label=real_regression` no topo e, por entrada, `verdict_label`,
  `ref_p50_ms` e `R_e`. Valores observados de `R_e`: **1,567 / 2,153 / 2,183 /
  2,352 / 2,365**, com `ref_p50` entre 82,2 e 89,9 ms — dentro da faixa 2–4 que
  o desenho previa, num único ponto que **não** deve ser lido como `K`.
- **O `PYSUM` da sombra lê as chaves.** O heredoc foi EXTRAÍDO do
  `validate.yml` da sombra (não reescrito) e executado contra esse JSON real:
  rc 0, e a linha publicada saiu
  `second key phase=1-advisory verdict=real_regression — check_agent_spawn:
  real_regression ref_p50=83.0ms R_e=1.567 | ...`.
- **Controle de BACK-COMPAT:** o MESMO `PYSUM` contra um relatório gerado
  **sem** as flags novas (30 iterações) sai rc 0 e imprime `-` em todos os
  campos — não quebra. O relatório sem flags não carrega **nenhuma** das
  chaves novas (verificado chave a chave).
- **`actionlint`** no `validate.yml` da sombra: rc 0, saída **byte-idêntica**
  à do `validate.yml` do HEAD (controle).
- **`yaml.safe_load`** do `validate.yml` da sombra: OK.
- **Literais preservados:** `FAILED on BOTH attempts (rc1=` aparece **2×** no
  HEAD e **2×** na sombra. O literal `FAIL: hook latency gate —` **não vive no
  workflow** — ele está em `profile-opus-4-7.py:1672` (e é travessão U+2014,
  não `--`; o `--` do desenho é a renderização ASCII). Consumidores:
  `PLAN-161/proof-retry-matrix.sh:150,162`,
  `PLAN-159/wave2-regression-proof.sh:137,145`,
  `PLAN-159/wave1-wrapper-matrix-proof.sh:114`,
  `PLAN-174/OWNER-S318-LAND.sh:148` e o próprio teste do gate (`:771`).

### Controles positivo e negativo

O controle **hermético** exigido pelo desenho já é parte da suíte de 42 e é
**predicativo**, nunca sorte de relógio — o amostrador é injetado:

- **POSITIVO** (+150 ms na entrada com a referência plana ⇒ `real_regression`):
  `test_phase1_labels_real_regression_and_keeps_todays_exit` e
  `test_phase2_labels_real_regression_and_exits_1`.
- **NEGATIVO** (hook e referência ×3 ⇒ `advisory_slow_runner` na fase 2, e o
  rótulo já correto na fase 1):
  `test_phase1_still_reads_real_regression_and_keeps_todays_exit`,
  `test_phase2_grants_amnesty_and_exits_0` e
  `test_backstop_denies_amnesty_above_600ms`.
- **Anti-vacuidade do anti-acoplamento:**
  `test_anti_coupling_checker_is_not_vacuous` +
  `test_reference_never_imports_the_framework` (um `from _lib import ...`
  plantado tem de deixar o teste VERMELHO).
- **Anti-regressão do S318** (referência amostrada uma vez antes do laço):
  `test_reference_samples_are_spread_through_the_hook_loop` e
  `test_ref_schedule_totals_exactly_and_spreads`.

O controle **live** (`PLAN-159/wave2-regression-proof.sh`) **não roda nesta
máquina**: ele exige `timeout(1)`, ausente no macOS do mantenedor, e planta a
regressão num worktree descartável exigindo o JOB vermelho pelo wrapper real.
Ele é `workflow_dispatch` da manhã — declarado aqui, não simulado.

## 4. O que este pacote NÃO faz

- **Não deixa o `Validate` verde.** Fase 1 é advisory: exit codes idênticos aos
  de hoje. O verde vem do **rerun de madrugada** do run `32866209415` (cron
  03:03, decisão Q5 do Owner) e, se o runner estiver persistentemente lento, da
  fase 2 — que só existe depois de ≥10 runs publicarem `R_e`.
- **Não fixa `K_e`.** Zero pares `(hook, referência)` medidos em runner de CI
  existem hoje. Qualquer `K` num pacote antes dessa janela é INVENTADO.
- **Não decide as seis perguntas abertas.** Elas estão em `PLAN-169` §Open
  questions **OQ-7..OQ-12** (verificado em disco, `:1382` e `:1397..:1422`) e
  são chamada do Owner: a célula `abs_ok ∧ ¬rel_ok`; o backstop de 600 ms sem
  evidência; aceitar a janela de fase 1; o fallback se a admissibilidade voltar
  VAZIA; se os dois herdeiros do ADR-144 viajam aqui; e a exposição de
  instrumento único de `check_output_secrets`.

## 5. Manifesto ADR-192

`.github/workflows/validate.yml` **NÃO é membro** do manifesto
`.claude/governance/gate-scripts-manifest.txt` (9 membros; `grep -F` por
`validate.yml` não casa nenhuma linha). Nenhum dos três paths do patch é
membro. **Nenhum bump de sha é devido**, e o G5 do LAND prova isso
mecanicamente pela mesma leitura que o hook faz.

## 6. Rodadas de pair-rail

Registros em `rail-round-*.md` neste diretório. Cada achado foi tratado como
CLAIM: verificado contra o disco, curado na sombra quando real, com pushback
escrito quando falso.

Pair-Rail-Reviewed: ver `rail-round-*.md`
