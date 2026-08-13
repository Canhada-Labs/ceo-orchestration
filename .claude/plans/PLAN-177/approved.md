# PLAN-177 — W1 approved.md (DRAFT — Owner pina o anchor ao assinar)

> **`Anchor-SHA` é PLACEHOLDER de propósito.** O Owner pina ao HEAD real
> no momento da assinatura — é o que amarra a aprovação a um estado de
> árvore, não a um alvo móvel. Inputs: os 9 patches em
> `.claude/plans/PLAN-177/staged-w1/` com `MANIFEST.sha256` RASTREADO;
> o land roda `shasum -c` fail-closed antes de aplicar.

```
Anchor-SHA: ab506cd9fb9ea1ea2b1694a7cca6244a7c9dd348
Plan: PLAN-177
Wave: W1 (pack canônico único — §W1 do plano v4.1)
Ceremony: canonical-edit (Owner GPG, assinatura detached .asc)
```

## Scope — os paths exatos que esta aprovação autoriza

Grupo **A — canônicos (`_CANONICAL_GUARDS`), a razão da cerimônia**:

```
scripts/_framework_manifest_set.sh
scripts/install.sh
scripts/upgrade.sh
scripts/install-npm.sh
.github/workflows/tournament.yml
.github/workflows/smoke-install.yml
```

Grupo **B — superfície livre, MESMO commit (atomicidade CF-2)**:

```
scripts/tests/_parity_classify.py
scripts/tests/test-night-mode-ignore-effect.sh          (novo, mode 100755)
.claude/scripts/tests/test_tournament_projection_workdir.py  (novo)
```

## O que muda

**P1-1 (o 4º e último P1 do re-pass GA).** O texto dos blocos de
`.gitignore` passa a viver em UM gerador (`_framework_manifest_set.sh`,
6 funções — INV-4/PLAN-168): mcp-secrets + posture no root (byte-
idênticos ao install atual, idiossincrasias preservadas e plantadas
como mutação no BYTE-PROOF), entregues TAMBÉM pelo upgrade (fecha o
adopter pré-v1.2.0); e o arquivo NOVO `.claude/.gitignore` (`/state/`
+ `/settings.local.json`), todas as cerimônias inclusive `user`,
create-if-missing/nunca sobrescrever, fora do baseline manifest (o
upgrade não pode clobberar) e fora do uninstall. Allowlist
`^\.gitignore$` REMOVIDA no mesmo commit (estado C = CI-verde e cego;
`git show --stat` pré-push é a verificação humana das duas metades).

**Eficácia, não só parity (codex v4 P1-3):** e2e novo
`test-night-mode-ignore-effect.sh` — simula `/night-mode on` e asserta
porcelain limpo nas rotas upgrade-v1.2.0 E install `--ceremony user` —
WIRADO no smoke-install (e2e não-wirado = teste morto), com timeout
25→32 MEDIDO (2m06s × fator 2-3 do runner).

**T-1:** tournament.yml `working-directory` no step de summary +
assert estrutural restrito a run-steps relativos.

**install-npm.sh:** bloco :176-190 — as DUAS claims falsas curadas
(CI que não computa checksum; receita de consumidor impossível), e a
meia-cura do rascunho anterior rejeitada por medição (a receita
"maintainer local" com o manifesto cumulativo também falha — rc=1
reproduzido; o que verifica é o sidecar `<tarball>.sha256`, rc=0).

## Evidência (staged-w1/, sha256 no MANIFEST rastreado)

BYTE-PROOF (9 cenários + mutações plantadas pegas) · STATE-D-PROOF
(FATAL provado: MISSING_IN_B=1, UNCLASSIFIED=1) · PARITY-RUN (cura=0,
estado-D=1, clean-clone=0, controle positivo dispara) · night-mode e2e
PASS com controles inline · idempotência install×2/upgrade×2/adopter-
editou-comentário · journal 34/34 · shellcheck manual 0 findings
(`scripts/` da raiz NÃO é coberto pelo CI — rider).

## Riders que o Owner ratifica ao assinar

- R-2 AMPLIADO: `PLAN-169/staged-w3/scripts/` tem cópias whole-file
  PRÉ-cura dos 3 scripts — o W3 exige RE-STAGING + re-pin do
  gate-scripts-manifest antes de assinar, senão o cp cego reverte a
  cura P1-1 inteira.
- Postura deliberada: idempotência por-linha ⇒ entry deletada pelo
  adopter é re-anexada no próximo upgrade (postura de segurança,
  documentada; release notes avisam).
- Fail-loud: gerador ausente ABORTA o upgrade (~95%) antes do rewrite
  do baseline manifest — postura install.sh:1898, não a
  preserve-surface do pointer.
