# Cerimônia 2 (S291-B) — checklist de superfície derivada

## ⚠ ITEM NOVO — SHA-pin drift no `mutation-gate.yml` (supply-chain-watch)

O `supply-chain-watch` (agendado semanal) está **vermelho desde
2026-07-20** — 4ª ocorrência da classe "gate periódico vermelho
invisível" neste repo. Causa verificada:

```
DRIFT mutation-gate.yml:75  actions/checkout@34e114876b0b...
      claims tag v4; upstream v4 → 11d5960a3267...
inventory: 69 compliant, 1 drift(s)
```

Verificado contra a autoridade (`gh api repos/actions/checkout/git/ref/tags/v4`):
upstream v4 = `11d5960a326750d5838078e36cf38b85af677262`. **Mas o padrão do
repo é outro**: 27 workflows usam `de0fac2e4500…`; o `mutation-gate.yml`
é o único que ficou para trás quando os demais foram atualizados.

**Recomendação:** alinhar ao SHA que os outros 27 já usam (consistência
interna), não ao v4 corrente — a menos que haja razão para o
mutation-gate ficar numa major diferente.

`.github/workflows/*.yml` é canonical-guarded **E** kernel-hard-deny ⇒
exige sentinel + `CEO_KERNEL_OVERRIDE`. Uma linha, mas cerimônia.


> A cerimônia 1 (`ceremony-s291.sh`) NÃO mexe em contagem nenhuma.
> A cerimônia 2 adiciona **2 ADRs** (`ADR-110-AMEND-2`, `ADR-164-AMEND-1`)
> e por isso arrasta superfícies derivadas com **tolerância 0**.

## Sites de contagem de ADR: 184 → 186

Verificados em disco hoje (`ls .claude/adr/ADR-*.md | wc -l` = 184):

| Arquivo | Linha | Forma |
|---|---|---|
| `CLAUDE.md` | 54 | `**184 ADRs**` |
| `README.md` | 186 | `# 184 ADRs` (comentário no bloco de comandos) |
| `npm/README.md` | 122 | `# 184 ADRs` |
| `docs/ARCHITECTURE.md` | 56 | `# 184 architecture decision records` (comentário da árvore) |
| `docs/ARCHITECTURE.md` | 71 | célula de tabela `\| ADRs \| 184 \|` |
| `docs/ARCHITECTURE.md` | 237 | prosa `(184 to date)` |

**Atenção:** `verify-counts.sh` só casa `(\d+) ADRs total` / `(\d+) ADRs on
disk` (prosa) + a regra de célula de tabela. As formas de **comentário**
(`# 184 ADRs`, `# 184 architecture decision records`) e a prosa
`(184 to date)` **não são vigiadas por nenhuma regra** — são a classe
[[feedback-adr-count-drift-unwatched-docs]]. Atualize-as à mão e confirme
com um grep, não com o gate.

## Regeneração obrigatória (nunca editar à mão)

```bash
python3 scripts/build-plugin.py --write-manifests
bash .claude/scripts/local/regenerate-command-skill-hook-map.sh  # se existir;
# senão o gerador nomeado em docs/COMMAND-SKILL-HOOK-MAP.md
```

`docs/COMMAND-SKILL-HOOK-MAP.md` é derivado sob **gate duro de CI** — foi
o item que o lane de code-review nomeou como "o que reprova o CI se
escapar".

## Gate ANTES de landar o ADR-110-AMEND-2 (§6 da emenda)

Sonda do teto do harness — bloqueante:

- um hook registrado a **210 s** que bloqueia ~185 s ainda RETORNA e ainda
  emite `pair_rail_case`;
- a contagem de `review_expected` órfãos permanece **0**
  (baseline medido hoje a 150 s: **0** —
  `python3 .claude/scripts/local/pair-rail-latency.py --budget-s 180`).

Se o harness matar o hook antes, o modo de falha resultante é fail-open
**sem evento nenhum** — invisível ao instrumento no numerador E no
denominador, estritamente pior que o case-F de hoje. Nesse caso a emenda
NÃO landa como está.

## Ordem do Scope do sentinel (consensus S7)

Ordenar para que os fixes fail-closed do `check_canonical_edit` fiquem
SEPARÁVEIS dos riders (ADR-110-AMEND-2, RC3-F7, R1/check_budget): um
REJECT do pair-rail num rider não pode travar a leva inteira.

## Checagem final antes do push

```bash
bash .claude/scripts/local/verify-counts.sh          # tolerância 0
python3 scripts/build-plugin.py --check
python3 .claude/scripts/check-claude-md-claims.py
python3 -m pytest .claude/hooks/tests/ -n auto -m 'not serial' -q
python3 -m pytest .claude/hooks/tests/ -m 'serial' -q
python3 -m pytest .claude/scripts/tests/ .claude/scripts/optimizer/tests/ -n auto -m 'not serial' -q
```
