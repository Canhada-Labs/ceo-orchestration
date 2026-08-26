# RETOMAR AQUI — PLAN-179 · atualizado S328, 2026-08-25 (madrugada autônoma)

## Situação em uma frase

**`staged-w24` (W2+W4) está MONTADO, simulado e revisado — falta só a
assinatura do Owner.** O pack tem **27 entradas** no `MANIFEST.sha256` (22
destinos pré-existentes no `BASELINE.sha256` + 5 novos), montado sobre o HEAD
`560dad0`. Os três scripts da cerimônia estão prontos e o pacote é o **D** da
fila da manhã (ordem **B → A → C → D**).

## O que falta, exatamente

**DOIS arquivos, e nenhum deles está no FILE ASSIGNMENT dos agentes da noite.**
Enquanto não entrarem no pack, o `--dry-run` do Owner ABORTA e o SIGN RECUSA
assinar — os dois comportamentos são corretos, não defeitos.

1. `staged-w24/CHANGELOG.md` (NOVO no pack) — cópia do vivo com a linha 12:
   `195 ADRs, 70 \`_lib\` modules` → `196 ADRs, 71 \`_lib\` modules`.
   **Medido:** sem ele, `verify-counts.sh --no-tests` sai **rc=1** com
   `DRIFT: CHANGELOG.md: header cites adrs=195, live=196` e `lib=70, live=71`
   (regra `changelog/header`). Com ele: **rc=0** (verificado em clone).
2. `staged-w24/.claude/hooks/tests/test_template_dogfood_parity.py` (NOVO no
   pack) — `:102` `49`→**50**, `:103` `46`→**47**, e o comentário `:101`
   `49 == 46 + 1 + 2` → `50 == 47 + 1 + 2`.
   **Medido:** sem ele, a suíte de hooks sai **1 failed** de 6.828
   (`test_registration_counts`, `AssertionError: 50 != 49`). Com ele:
   **14 passed** (verificado em clone).

Depois dos dois: `python3 .claude/plans/PLAN-179/assemble_pack.py
.claude/plans/PLAN-179/staged-w24` → uma rodada de pair-rail → registrar
`Rail-Verdict: APPROVE` em `s328-ceremony-D/rail-round-6.md` (o SIGN LÊ esse
campo da última rodada e só assina com APPROVE).

Aí sim, os três comandos do Owner:

1. `bash .claude/plans/PLAN-179/OWNER-W179-W24-SIGN.sh` — assina.
2. `bash .claude/plans/PLAN-179/OWNER-W179-W24-LAND.sh --dry-run` — ensaio
   completo (aplica, roda a bateria, DESFAZ; ~25-35 min).
3. `bash .claude/plans/PLAN-179/OWNER-W179-W24-LAND.sh` — aplica, commita e
   empurra para o `main` sozinho.

Passo a passo para leigo, com os paths absolutos: **`s328-ceremony-D/README-D.md`**.

## Onde está cada coisa

| material | path |
|---|---|
| pack | `.claude/plans/PLAN-179/staged-w24/` (`MANIFEST.sha256`, `BASELINE.sha256`, `PACKMAP.txt`) |
| sentinel-draft | `.claude/plans/PLAN-179/W179-W24-approved-draft.md` |
| assinar | `.claude/plans/PLAN-179/OWNER-W179-W24-SIGN.sh` |
| landar | `.claude/plans/PLAN-179/OWNER-W179-W24-LAND.sh` |
| receita do Owner | `.claude/plans/PLAN-179/s328-ceremony-D/README-D.md` |
| base declarada do V-block | `.claude/plans/PLAN-179/s328-ceremony-D/EXPECTED-BASELINE.txt` |
| mensagem de commit | `.claude/plans/PLAN-179/s328-ceremony-D/COMMIT-MSG-D.txt` |
| prova da simulação | `.claude/plans/PLAN-179/s328-ceremony-D/land-sim.log` |
| pair-rail | `.claude/plans/PLAN-179/s328-ceremony-D/rail-round-1..5.md` (5 rodadas; veredito da última em `Rail-Verdict:`) |
| harness dos scripts | `.claude/plans/PLAN-179/s328-ceremony-D/test-ceremony-scripts-w24.sh` |
| receita de montagem | `.claude/plans/PLAN-179/staged-w24/README-COMO-MONTAR.md` (PACK-DOC — **não** aterrissa) |

## Decisões já tomadas (não reabrir)

- **3 ações, não 2** (Owner, 2026-08-25, verbatim: «3 ações — registra
  `ledger_entry_rejected` (Recomendado)»). `_KNOWN_ACTIONS` **327 → 330**.
  Com a terceira, o breadcrumb-only de `scanner_unavailable` / `oversize` /
  `malformed_input` deixa de ser residual.
- **ADR-195**, não 194 — o 194 foi tomado pelo PLAN-183
  (`delivery-route-resolution`, `6304f66`) enquanto este pack esperava.
  Contagem de ADRs 195 → 196.
- **SPEC v2.59** (o vivo já tem v2.56, v2.57 e v2.58).

## Contagens que o V-block exige (medidas, não lembradas)

`len(_KNOWN_ACTIONS)` 330 · golden 334 linhas · hooks 59 · ligados 48 ·
registros 50 · `_lib` 71 · ADRs 196 · 1 linha de histórico `v2.59`.
Todas declaradas em `EXPECTED-BASELINE.txt`; o land aborta se qualquer uma
divergir, **nos dois sentidos**. Se uma delas mudar porque o `main` andou, o
caminho é re-montar o pack (`assemble_pack.py`) e re-assinar — nunca afrouxar
o número.

## O que este corte NÃO fecha

- O flip de `status:` do PLAN-179 — decisão do Owner, edição canônica de
  outra janela.
- `check_contamination.py` (exceção negativa para a classe `LEDGER.md`, já
  que `.claude/plans/*` atravessa `/` no fnmatch e isenta a árvore de planos
  inteira) — script não-canônico, cabe em commit direto fora da cerimônia.
- `SESSIONEND-NOTE.md` (US8: SessionEnd emitindo o delta candidato de
  memória) — fica no pack como PACK-DOC e não aterrissa; é insumo da
  cerimônia que tocar `SessionEnd.py`.

---

## Histórico — W0+W1+W1-b (LANDADO E VERDE, S314)

O Owner assinou (opção (a) do memo — residual do cap de 20k declarado), a
cerimônia landou em `c042f9e`, dois fix-forwards fecharam os efeitos
colaterais do corte (`6f7f20e` modes parciais + banda ~730→~770; `45c75e3`
sweep completo da família `_lib`) e o CI de `45c75e3` terminou **5/5 success**
— com o profiler curado por RERUN (boundary-flake provado: verde no próprio
sha do land, hook `check_output_secrets` não tocado pelo pack, delta A/B
local 2-4 ms).

### Lições do pós-land que este corte já absorveu

- **O land copiava MODOS do pack**: `_lib/*.py` chegou 755 e o smoke-install
  compara modo na paridade install/upgrade. O `OWNER-W179-W24-LAND.sh` não
  repete o erro — o modo é **derivado do índice** para destino existente, e
  755 só para hook de profundidade 1 quando o destino é novo; o passo S
  aborta se qualquer mudança de modo aparecer no índice. (O molde antigo
  fazia `case "$p" in .claude/hooks/*.py) chmod +x`, e em `case` do bash o
  `*` **atravessa** `/` — aquilo tornava `_lib/audit_emit.py` 755.)
- Test files novos mexem na banda ±5% de contagem approx nos docs —
  contagem approx também é superfície de corte.
- `check_output_secrets` vive rente ao teto de 120 ms p95 do profiler em
  hosted runner, **independente** de qualquer pack. Se flakar: recalibrar o
  teto ou otimizar o hook em wave própria, nunca reverter o land.
- O rail do w01 rodou até o round 11 (sequência 9→4→2→3→2→3→4→4→3→3→4) e o
  critério de parada publicado disparou num achado marginal de GC.
