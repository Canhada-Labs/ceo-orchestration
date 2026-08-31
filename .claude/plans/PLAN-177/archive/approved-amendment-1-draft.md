# PLAN-177 — approved-amendment-1.md (DRAFT — Owner pina o anchor ao assinar)

> Emenda ao sentinel W1 (`approved.md`, anchor `ab506cd`): UMA cura
> canônica achada pelo re-pass rc.4 tentativa 1 (NO-GO arquivado em
> `repass-rc4-20260813-NOGO/`). Inputs staged em
> `.claude/plans/PLAN-177/staged-t2/` (rastreado; sha256 abaixo).

```
Anchor-SHA: ANCHOR-PLACEHOLDER
Plan: PLAN-177
Wave: W1-amendment-1 (cura P1-b do re-pass t1)
Ceremony: canonical-edit (Owner GPG, assinatura detached .asc)
```

## Scope — os paths exatos que esta emenda autoriza

Canônico:
```
scripts/_framework_manifest_set.sh
```
Livre, MESMO commit (o e2e é o controle da cura):
```
scripts/tests/test-night-mode-ignore-effect.sh
```

## O que muda

`_apply_claude_dir_gitignore` deixa de ser create-if-missing-ONLY:
quando `.claude/.gitignore` JÁ EXISTE sem `/state/` e/ou
`/settings.local.json` (adopter com arquivo próprio, ex. só `/cache/`),
as entries faltantes são ANEXADAS por linha (`grep -Fxq`, mesmo
predicado dos blocos do root), preservando cada byte do adopter —
nunca rewrite. Era o P1-b: o helper via o arquivo, retornava, e o
night-mode ficava commit-eligible no modo user. E2e ganha cenários
D (install user seeded) e D2 (upgrade seeded): adopter bytes
preservados + as duas entries presentes + porcelain limpo.

## Evidência

Vermelho PRÉ-cura provado (8 FAILs na forma exata do P1, gerador
antigo) → verde PÓS-cura no e2e completo (todos os cenários A/B/C/D/D2
+ controles inline). Patches: `staged-t2/t2c-generator.patch`,
`staged-t2/t2c-e2e.patch`.
