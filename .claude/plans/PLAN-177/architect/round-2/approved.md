# APPROVED — PLAN-177 round-2 (re-pass rc.4 t7: wiring CI dos controles)

Anchor-SHA: 8261acae552a1fe767b7aa34b1b3fc298c21a2b8

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @joaocanhada 8261acae552a1fe767b7aa34b1b3fc298c21a2b8
Plans: PLAN-177
Scope:
- .github/workflows/ownership-nightly.yml
- .github/workflows/validate.yml
<!-- END SIGNED SCOPE -->

(`.github/workflows/smoke-install.yml` segue autorizado pelo sentinel
raiz do PLAN-177, já assinado — as edições t7 nele são a continuação do
mesmo escopo: step novo do unit + path filters em sync.)

## O que muda

**t7 P2 (condition 5 do t6 — wiring CI dos controles).** O re-pass t7
apontou que `test_install_state_replay.sh` era local-only e
`test-gitignore-symlink-and-dryrun-unit.sh` não rodava em workflow
nenhum — o CI ficava verde após regressão em: persistência da ceremony
pré-state (B2-c2), refresh hash-gated dos schemas (B2-c3) e as pernas
novas de recusa de symlink / `--skip` / fallback de hasher (B2-c4).

- `ownership-nightly.yml`: step novo "Install-state replay suite"
  (após o preflight do verdict-unit) rodando a suíte inteira
  (64 casos, ~11 min local); `timeout-minutes` 90 → 110 com a mesma
  regra de dimensionamento anti-flake medida do smoke-install (F4).
- `validate.yml`: SÓ o comentário estale da linha ~869 — a claim
  "test_install_state_replay.sh ... local/landing-gate only" deixa de
  ser verdade com o wiring acima; o comentário passa a apontar o
  nightly. Nenhuma mudança executável.

## Provenance

- Autor: sessão S308 (Claude Fable 5), re-pass rc.4 t7.
- Rail: veredito t7 parte 2 (`repass-rc4/verdict-rc4-2.txt` da rodada
  NO-GO em triagem), achado P2 #5; curas revisadas pelo t8 (o re-pass
  roda de novo sobre o commit que contém este wiring).
