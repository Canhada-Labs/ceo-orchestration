# EVIDENCE — PLAN-183 W1 draft (S338 night-run)

> Tudo abaixo foi EXECUTADO nesta sessão; números são os impressos pelos
> instrumentos. Comandos reproduzíveis a partir de uma árvore em BASE +
> `apply-w1-edits.py`. Nada foi commitado no repositório vivo; o índice não foi
> tocado.

## 0. Bases, sombra, controle

- **HEAD andou durante a noite:** `dc72bf1` (brief) → `6160578` (pacote S337) →
  `f0e98de` (materiais da cerimônia fable51). As 34 âncoras do script casam 1×
  em `dc72bf1`+fable51 **e** em `f0e98de`+fable51 (`--check-only`, ambas).
- **Sombra final:** `/private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/f52979b1-4c83-4346-9217-5f07d8d51bde/scratchpad/shadow-183w1`
  — `git worktree add --detach … HEAD` (= `f0e98de`) → `apply-fable51-edits.py`
  → commit interno `shadow: fable51 base` → `apply-w1-edits.py --root <sombra>`.
  Deixada no lugar (não removida).
- **Árvore de CONTROLE (sem cura):** `…/scratchpad/precure-183w1` = mesma base
  (`f0e98de`+fable51, commit interno `precure: fable51 base`) +
  `apply-w1-edits.py --control-no-cure` (20 das 34 edições: SÓ testes, funções
  novas, TSV/doc/harness; NUNCA o ramo `*)` do gerador, o `elif` de
  `_ownership_verdict`, `upgrade.sh` ou `install.sh`). É o modo do próprio
  script — reproduzível, sem edição à mão.
- **Doutrina respeitada:** nenhum `Edit`/`Write` dentro da sombra; a sombra só
  mudou pelo script; cada mudança do script ⇒ `git worktree remove --force` +
  re-derivação completa (5 derivações ao todo: r0 base `dc72bf1`; r1/r2 base
  `f0e98de` (hardening `! -L`, SC2088, grep da rota); r3 (rail r1 revisou);
  r4 = r3 + curas do rail r1 + P2 re-fonteado (rail r2 revisou); **r5 = r4 +
  curas do rail r2** — normalização física, R15, `PREV_TAG` por conteúdo, wire
  no CI — a bateria FINAL, revisada pelo rail r3). O script final tem **36
  edições em 12 paths** (`--list-paths`).

## 1. Controles positivos (árvore SEM cura — tudo tem de ficar VERMELHO)

| Instrumento | Resultado no controle | O que ficou vermelho |
|---|---|---|
| `bash scripts/tests/test-protocol-pointer-render.sh` | **3 FAILED (13 passed)**, rc 1 | R2b «healthy render still equals the legacy body» · R10 «not portable (named='/private/tmp/…/precure-183w1')» · R11b «healthy portable body misclassified as legacy» |
| `bash scripts/tests/test-ownership-verdict-unit.sh` | **PASS=65 FAIL=1**, rc 1 | `OWN-0096 FAIL exp=REFRESH HASH_CANONICAL_POINTER got=PRESERVE_UNOWNED HASH_NONE` — exatamente a lacuna do Stage B |
| `bash scripts/tests/test-protocol-pointer-inv4.sh` | **4 leg(s) FAILED**, rc 1 | L1 post-install/post-upgrade e L3 post-cure «pointer names an ABSOLUTE checkout path (pre-W1 form)» · L5 «legacy absolute pointer NOT cured» |
| `bash scripts/tests/test-protocol-pointer-portable.sh` | **10 FAILED (9 passed)**, rc 1 | P1a (absoluto) · P1b (não resolve após mover juntos) · P2a · P2b (o absoluto RESOLVE após mover o target sozinho — o teste discrimina) · P2c (sem `--protocol-source`) · P2e (sem WARNING) · P2f (`ERROR: unknown option: --protocol-source` do upgrade antigo) · P3c · P3d · P4b |

Os PASS do controle são instrumentos (R11a/R12/P3b: o reconhecedor está na
árvore de controle por desenho) ou propriedades pré-existentes (L2/L4, P1c/P2d
preservação, P3a: o `v1.3.0` escreve o absoluto).

**Controle re-executado com os instrumentos do r4** (mesma árvore sem cura,
re-derivada em `f0e98de`+fable51 + `--control-no-cure`):
`test-protocol-pointer-render.sh` **3 FAILED (14 passed)** (R2b, R10, R11b — R11d
passa: é instrumento); `test-protocol-pointer-portable.sh` **11 FAILED (9 passed)**,
rc 1 — agora com **P2g VERMELHO** («before == after == checkout do install»),
i.e. a vacuidade do P2g ficou fechada, e P2a2 verde como esperado (o install
antigo também grava o próprio checkout). O INV-4 não mudou entre r3 e r4; o
controle do r3 (4 legs FAILED) permanece válido para ele.

**Controle re-executado com os instrumentos do r5** (árvore sem cura
re-derivada + `--control-no-cure`, 22 edições): `test-protocol-pointer-render.sh`
**4 FAILED (14 passed)** — R2b, R10, R11b e o novo **R15** («symlinked target
=> dead relative path», o corpo absoluto do gerador antigo não resolve a partir
do target); `test-protocol-pointer-portable.sh` no controle r5: ver §5.
**Controle FIEL do R15 contra a lógica LEXICAL do r4** (a cura anterior, não a
árvore sem cura): com base `pwd -P` limpa e `s -> deep/root`, a própria
`_rpp_relpath` do target LÓGICO dá `../../deep/root/ceo` e
`[ -f "$target/$rel/PROTOCOL.md" ]` é FALSO — morto do diretório físico; o
render r5 dá `../ceo`. (A primeira sonda não reproduzia porque `$TMPDIR` do
macOS termina em `/` e o `//` caía na recusa lexical ⇒ verbatim absoluto —
refeita com base física.)

**Achado do controle, curado no r4:** `P2g` passava no controle porque o valor
de reparo (`$REPO_ROOT`) era IGUAL ao que o install já gravara — asserção
vácua. No r4 o P2 instala a partir da CÓPIA MOVIDA do P1 (`$C2`), lê o valor
gravado (`P2a2` = `$C2`), repara com `--protocol-source $REPO_ROOT` e exige que
o valor persistido tenha MUDADO (`P2g`). A mensagem do P2b também foi corrigida
(um ponteiro ABSOLUTO resolve após mover o target sozinho — é o defeito, não um
erro de harness).

## 2. Bateria na sombra (base `f0e98de`+fable51 + W1)

### 2.1 Rodada r3 (script antes do re-fonteamento do P2)

| Comando (dentro da sombra) | Resultado |
|---|---|
| `bash -n` nos 7 `.sh` tocados | 0 erros |
| `shellcheck -S warning` (0.11.0) nos 7 `.sh` tocados | **rc 0** (o único aviso do r0, SC2088 no literal `~/src/ceo` do R13, recebeu diretiva nomeada) |
| `bash scripts/tests/test-protocol-pointer-render.sh` | **16/16 pass**, rc 0 |
| `bash scripts/tests/test-ownership-verdict-unit.sh --quiet` | **PASS=66 FAIL=0 SKIPPED=2** (`OWN-0024/0027`, fault rows — pré-existente), rc 0 |
| `bash scripts/tests/test-protocol-pointer-inv4.sh` | **5/5 legs pass**, rc 0 |
| `bash scripts/tests/test-protocol-pointer-portable.sh` | **19/19 pass**, rc 0, **316 s** (concorrente com o INV-4 e o rail) |
| `python3 .claude/scripts/check-installer-write-safety.py --repo-root <sombra>` | **rc 0** (baseline re-gerado pelo pós-passo do script) |
| `git diff --stat` | 9 files changed, 801 insertions(+), 340 deletions(-) + 1 arquivo novo |

Rota medida no P1c (mover os dois JUNTOS e dar upgrade a partir do checkout
movido): `PRESERVED (root PROTOCOL.md is adopter-customised — pointer NOT
refreshed; backup in …)` — rc 0, byte-idêntico, sem WARNING falso (P1d). É a
OQ-3 do DESIGN: seguro, mensagem enganosa.

### 2.2 Rodada r4 (r3 + curas do rail r1 + P2 re-fonteado) — revisada pelo rail r2

Sombra re-derivada do ZERO (`f0e98de`+fable51, `--check-only` 34/34, apply).
render **17/17**; unit **66/0/2**; INV-4 **5/5**; e2e portátil **20/20** em
**324 s**; shellcheck **0**; censo **rc 0**; `git diff --stat` 9 files, +834/−340
+ 1 novo; hash `71f684ca18541bf48ad91b0ecd48388b0fa5454806d2498634daf3a1f0430075`.

### 2.3 Rodada FINAL (r5 = r4 + curas do rail r2) — a BATERIA que vale

Sombra re-derivada do ZERO (worktree removido e recriado em `f0e98de`, fable51
aplicada e commitada `e93a901`, `apply-w1-edits.py --check-only` **36/36 em 12
paths**, apply). Tudo executado DEPOIS da última edição do script.

| Comando (dentro da sombra) | Resultado |
|---|---|
| `bash -n` nos 7 `.sh` tocados | 0 erros |
| `python3 -c 'import yaml; …safe_load…'` nos 2 workflows tocados | `yaml ok` |
| `shellcheck -S warning` (0.11.0) nos 7 `.sh` tocados | **rc 0** |
| `bash scripts/tests/test-protocol-pointer-render.sh` | **18/18 pass**, rc 0 (R15 novo: target atrás de symlink de profundidade ⇒ `../ceo`, resolve) |
| `bash scripts/tests/test-ownership-verdict-unit.sh --quiet` | **PASS=66 FAIL=0 SKIPPED=2** (`OWN-0024/0027` fault rows, pré-existente), rc 0 — inclui as 3 linhas novas `OWN-0095/0096/0097` |
| `bash scripts/tests/test-protocol-pointer-inv4.sh` | ver §5 (r5) |
| `bash scripts/tests/test-protocol-pointer-portable.sh` | ver §5 (r5) |
| `python3 .claude/scripts/check-installer-write-safety.py --repo-root <sombra>` | **rc 0** (baseline re-gerado pelo pós-passo; delta por conteúdo em §3 — idêntico ao r4: `cd`/`pwd -P` são read-only) |
| `git diff --stat` | 11 files changed, 894 insertions(+), 341 deletions(-) + `scripts/tests/test-protocol-pointer-portable.sh` novo (0755) |
| `git diff \| shasum -a 256` (estado revisado pelo rail r3) | `4a270ec0ab7b7748344c2cd7628ed68b041ec0ddcdc589e1be0a5d5423f06541` |

Rota medida no P1c (os dois movidos JUNTOS, upgrade a partir do checkout
movido): `PRESERVED (root PROTOCOL.md is adopter-customised …)`, rc 0,
byte-idêntico, sem WARNING falso (P1d) — OQ-3 do DESIGN, inalterada.

**Não executado, dito:** `scripts/tests/test-ownership-table.sh` (o e2e de
ownership, ~25 min, 62 installs reais) — logo `ownership-baseline-map.txt` NÃO
foi re-gravado e `ownership-expected-reds.txt` NÃO foi re-verificado nesta
noite; o oráculo de DECISÃO (66/0) e o ramo `legacy_absolute)` do harness são a
evidência disponível. Também não executado: o smoke completo
(`smoke-install.sh`, ~1 h) e o pytest do repo (a W1 não toca Python de teste;
o único `.py` tocado é o baseline do censo, que é dado).

## 3. Ratchet PLAN-185 — o que mudou no baseline (por CONTEÚDO, ignorando nº de linha)

Base 676 entradas → sombra 683. NOVAS: `_framework_manifest_set.sh` ×4
(espelho exato dos 4 sítios de `_protocol_pointer_is_degraded`: `[ -f ]`,
`mktemp`, `> "$tmp"`, `cmp`), `install.sh` ×1 (a chamada única ao gerador,
`desguardado` como as duas que substitui — dominada por `_dst_refuses`, ponto
cego FU-1), `upgrade.sh` ×4 (`-f` das precedências/aviso, agora precedidos de
`! -L`; a chamada do reconhecedor no OBSERVE). REMOVIDAS: `install.sh:2639` e
`:2642` (`desguardado`) e uma linha de `upgrade.sh` cujo texto mudou.
**Nenhum sítio novo escreve em `$TARGET`.**

## 4. Pair-rail

Ver `rail-round-N.md` / `codex-rN.txt`. Snapshot `git diff | shasum -a 256`
antes/depois de cada rodada — TREE-INTACT/CHANGED registrado por rodada.

- **r1** (sobre o estado r3, hash `f1375a52…`): TREE-INTACT; **1 P1 + 3 P2**, todos
  verificados REAIS; 3 curados no r4 (consistência allowlist/OBSERVE; split
  ancorado à direita com espaços; sem `mktemp`), 1 DEFERIDO ao /debate (wire do
  e2e no `smoke-install.yml`, canônico — OQ-5). `Rail-Verdict: CHANGES-REQUESTED`.
- **r2** (sobre o estado r4, hash `71f684ca…`): TREE-INTACT; **2 P1 + 1 P2**, todos
  REAIS, todos curados no r5 (normalização física antes do relpath — R15;
  wire do e2e no `ownership-nightly.yml` + filtros do `smoke-install.yml`;
  `PREV_TAG` por conteúdo). `Rail-Verdict: CHANGES-REQUESTED`.
- **r3** (sobre o estado r5 = FINAL, hash `4a270ec0…`): TREE-INTACT; **1 P1 + 2 P2**,
  todos REAIS: o P1 é a OQ-3 (state absoluto pós-move ⇒ `edited`), DEFERIDA ao
  /debate por ser mudança da precedência D3 do Owner; os 2 P2
  (`_pwp_named` sem guarda sob `set -e`; ausência do aviso no ramo
  `PRESERVE_UNOWNED`) ficam ABERTOS com a cura escrita em `rail-round-3.md` —
  não aplicados por causa do teto de 3 rodadas (a sombra e o script continuam
  idênticos ao estado revisado). `Rail-Verdict: CHANGES-REQUESTED`. **Nenhuma
  rodada limpa; o último veredito é este.**

## 5. Resumo dos números FINAIS (r5, sombra `shadow-183w1`, hash `4a270ec0…`)

| Instrumento | Sombra r5 (com cura) | Controle r5 (sem cura, `--control-no-cure`) |
|---|---|---|
| `test-protocol-pointer-render.sh` | **18/18 pass**, rc 0 | **4 FAILED (14 passed)**, rc 1 — R2b, R10, R11b, R15 |
| `test-ownership-verdict-unit.sh` | **PASS=66 FAIL=0 SKIPPED=2**, rc 0 | **PASS=65 FAIL=1** (`OWN-0096`), rc 1 (medido no r3; TSV/verdict inalterados desde) |
| `test-protocol-pointer-inv4.sh` | **5/5 legs pass**, rc 0 | **4 leg(s) FAILED**, rc 1 (medido no r3; teste inalterado desde) |
| `test-protocol-pointer-portable.sh` | **20/20 pass**, rc 0, **297 s** | **11 FAILED (9 passed)**, rc 1 — P1a, P1b, P2a, P2b, P2c, P2e, P2f (`ERROR: unknown option: --protocol-source`), P2g, P3c, P3d, P4b |
| `shellcheck -S warning` (7 `.sh`) | rc 0 | — |
| YAML dos 2 workflows | parseia | — |
| `check-installer-write-safety.py` | rc 0 (baseline re-gerado) | — |
| `git diff --stat` | 11 files, +894/−341, +1 novo | — |

Rota medida no P1c (r5): `PRESERVED (root PROTOCOL.md is adopter-customised …)`,
rc 0, byte-idêntico, sem WARNING falso — OQ-3, inalterada.

Ratchet = §3. Rail = §4 e `rail-round-1..3.md`.
