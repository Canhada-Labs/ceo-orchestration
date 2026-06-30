# Contribuindo para ceo-orchestration

> **English is canonical.** Espelho inglês: [CONTRIBUTING.md](CONTRIBUTING.md).
> EN é a Single Source of Truth. Veja `docs/translations/README.md` para
> o drift tracker; `.github/workflows/translations-drift.yml` enforce
> paridade estrutural.

Obrigado por considerar uma contribuição. Este framework é
correctness-first e opinionated — otimizamos para governança mecânica,
não amplitude. Leia este arquivo antes de abrir um PR para sua
contribuição aterrissar de primeira.

## Escada de adoção

| Nível | Artefato que disparou | O que significa |
|---|---|---|
| **Avaliador** | leu README + PROTOCOL | Você sabe o que é o framework |
| **Adopter** | rodou `install.sh`; tem `.claude/` num repo alvo | Está usando |
| **Contributor** | PR mergeado com ADR se L3+ | Você estendeu o framework |
| **Committer** | entrada em CODEOWNERS; sponsor de um squad | Você mantém parte dele |

Nenhum tier pago existe. Nenhum está planejado até 50+ adoções
orgânicas (recomendação da análise competitiva).

## Antes de abrir um PR

1. **Leia `PROTOCOL.md`** — o contrato de governança sob o qual você
   trabalha.
2. **Leia `.claude/plans/PLAN-SCHEMA.md`** — se seu trabalho atravessa
   múltiplas sessões, precisa de um plan file.
3. **Leia `SPEC/v1/README.md`** — se sua mudança toca qualquer
   schema, é uma mudança SPEC-level. Regras de SemVer aplicam.
4. **Verifique `.claude/plans/` por plans ativos** — se há um sprint
   corrente, seu trabalho provavelmente pertence àquele plan ou
   precisa de um follow-up.

## Tipos de contribuição

### Tier A — Trivial (sem gate)

- Correções de typo
- Clarificações de doc
- Ajustes de log message
- Correções de config de CI que não mudam comportamento

Abra um PR; um review aprovativo; merge.

### Tier B — Aditivo (ADR não requerido)

- Novo teste
- Novo skill sob um domínio existente
- Novo archetype em `team.md`
- Nova entrada de task chain
- Novo campo em frontmatter SKILL.md (opcional, aditivo)

Requisitos do PR:
- Passa `validate-governance.sh`
- Passa `python3 .claude/scripts/registry.py --validate`
- Passa suite de testes completa (hooks + scripts)
- Descreve a mudança + racional no corpo do PR

### Tier C — L3+ (ADR requerido, debate recomendado)

- Novo hook
- Mudança de schema (mesmo aditiva) — requer ADR documentando a adição
- Novo tipo de event em audit-log v2 — requer ADR estendendo ADR-005
- Novo squad — requer documentação de squad estilo ADR-009
- Mudanças em `PROTOCOL.md`
- Mudanças em flags ou exit codes de `install.sh`
- Mudanças no contrato `upgrade.sh --pin`
- Breaking changes de qualquer tipo (MAJOR bump de SPEC)

Requisitos do PR:
- ADR em `.claude/adr/ADR-NNN-<slug>.md` (segue formato ADR existente)
- Se L3+ plan scope: `/debate start PLAN-NNN` debate round 1 em disco
- Entrada CHANGELOG sob `## [Unreleased]`
- Todos os requisitos do Tier B

## Padrões de código

- **Python ≥ 3.9** — sem `match` statements, sem sintaxe PEP-604 union
  em runtime (use `Optional[X]` / `Union[X, Y]` de `typing`)
- **Stdlib apenas** em hooks, scripts e `_lib/` — zero `pip install`
  de dependências runtime. Deps só de dev (e.g. `coverage.py` em
  coverage.yml) OK.
- **`from __future__ import annotations`** em todo módulo
- **Type hints em funções públicas**
- **Testes unitários** via `unittest` (stdlib). `TestEnvContext` para
  isolação de env; nunca toque real `$HOME` ou `$CLAUDE_PROJECT_DIR`
  em testes
- **Fail-open em bugs de infra** — hooks NUNCA bloqueiam a sessão do
  usuário por falha própria; log um breadcrumb e permita

## Estilo de commit message

```
<scope>: <linha curta imperativa (≤ 70 chars)>

Por que esta mudança existe (parágrafo, não cada arquivo tocado).

O que shipou:
- bullet
- bullet

Tests: contagens se relevante. Zero regressions claimed = verdade.

Related: PLAN-NNN §X, ADR-NNN, consensus finding §CN.

Co-Authored-By: Claude <model-id> <noreply@anthropic.com>
```

Scope exemplos: `PLAN-004 Phase 2`, `hook`, `SPEC/v1`, `docs`, `ci`.

## Testing

```bash
# Suite completa de testes de hooks
python3 -m unittest discover -s .claude/hooks/tests -v

# Suite completa de testes de scripts
python3 -m unittest discover -s .claude/scripts/tests -v

# Governance + tier-boundary + registry check
bash .claude/scripts/validate-governance.sh
python3 .claude/scripts/registry.py --validate
python3 .claude/scripts/check-staleness.py

# Smoke install em diretório scratch
bash scripts/tests/smoke-install.sh
```

## O que NÃO contribuir

- **Nomes de pessoas reais como personas.** Apenas composites fictícios
  (apropriação de marca + risco legal).
- **JS runtime em hooks.** Stdlib Python é não-negociável.
- **Integrações SaaS em CI** (Codecov, CodeRabbit). Modelo de
  supply-chain requer zero third-party trust.
- **Conteúdo Pro/pago.** Deferred até 50+ adoções orgânicas.
- **Skills que duplicam existentes.** Verifique o registry primeiro:
  `python3 .claude/scripts/registry.py --list-skills`.
- **Comportamento dashboard-como-gate.** Observabilidade é read-only.

## Translations

PT-BR é um espelho tracked, não um segundo canonical. Veja
`docs/translations/README.md` para o workflow. Se você está adicionando
uma nova tradução (ES, ZH, etc.), abra uma issue primeiro — adiamos
novos idiomas até 50+ stars (decisão de posicionamento).

## Perguntas

Abra uma issue. Seja específico. Inclua:
- O que você tentou
- O que aconteceu
- O que você esperava

Issues com passos de repro + arquivos relevantes são triageadas mais
rápido.
