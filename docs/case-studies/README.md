# Case studies

Artefatos que documentam o install + 14-day uso real do ceo-orchestration
em adopters concretos. Cada case study vira evidência pública (Sprint 17)
ou interna (Sprint 15+16) de que o framework entrega valor em produção, não
apenas em benchmarks sintéticos.

## Conteúdo

| Arquivo | Uso |
|---------|-----|
| `_TEMPLATE.md` | Skeleton para um single-project case study (install → 14d → closeout) |
| `_TEMPLATE-cross-project.md` | Skeleton para cross-adopter analysis (Sprint 16) |
| `<adopter>-case-study.md` | Instâncias concretas (gerado a partir de `_TEMPLATE.md` em Phase 4 do Sprint N) |

## Naming convention

- Single-project: `<adopter-slug>-case-study.md` (ex: `adopter-1-case-study.md`)
- Cross-project: `internal-validation-summary.md` (Sprint 16) /
  `public-launch-retrospective.md` (Sprint 17+)

Use slugs lowercase-com-hífens, sem espaços. Identificador do adopter
deve matchear o `--adopter-name` passado em
`.claude/scripts/adopter-metrics.py`.

## How to use the templates

### `_TEMPLATE.md` (single-project)

1. Copie o template: `cp _TEMPLATE.md adopter-1-case-study.md`
2. Preencha "Adopter context" antes de começar o install (Phase 1 do Sprint)
3. Atualize "Install timeline" ao fim da Phase 1
4. Cole outputs semanais de `adopter-metrics.py` em "Quantitative metrics"
   durante Phase 2
5. Sintetize "Qualitative friction log highlights" a partir de
   `.claude/plans/PLAN-NNN/frictions.md` no fim de Phase 2
6. Documente "Framework fixes" com PR refs durante Phase 3
7. Owner escreve "Verdict" em Phase 4

### `_TEMPLATE-cross-project.md` (Sprint 16 cross-adopter)

1. Pré-requisito: ≥2 single-project case studies já existem
2. Rode `compare-adopters.py` com os weekly JSON reports de ambos adopters
   e cole a tabela em "Cross-adopter metrics"
3. Identifique "Patterns que generalizam" vs "Divergências por domínio"
4. Owner toma decisão go/no-go pra Sprint 17 público

## Boundaries

- Case studies escritos nestes arquivos NÃO são placeholders narrativos —
  todos os números vêm de `adopter-metrics.py` JSON output, todas as
  fricções vêm de `.claude/scripts/log-friction.sh`, todas as fixes vêm
  de PR refs reais. Fabricar dados aqui quebra o propósito do exercício.
- Não apague case studies antigos mesmo se o framework evoluiu —
  histórico é evidência longitudinal.
