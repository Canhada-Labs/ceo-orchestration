# PLAN-183 — cerimônia `wave-w5fix`: o deepen do histórico roda ANTES da paridade

**Sessão:** S327b (2026-08-25 manhã). **Sentinel:** `.claude/plans/PLAN-183/wave-w5fix-approved.md`.
**Patch:** `w5-ceremony/S327b-W5FIX.patch` (1 arquivo: `.github/workflows/smoke-install.yml`; gerado da sombra `scratchpad/shadow-w5fix` por `finalize_patch.py`).
**Scripts:** `OWNER-S327b-SIGN.sh` → `OWNER-S327b-LAND.sh --dry-run --ownership-e2e=defer` → `OWNER-S327b-LAND.sh --ownership-e2e=defer`.

Patch-sha256: 219ec54ef1de73a7d1c60a704cd34b5265d97d14ef3457aa7eb9197fb6a48c9d

## O defeito, medido
Run `32845976930` (pós-land `6304f66`): paridade `maintainer` = `STALE 3` (`docs/BRANCH-PROTECTION.md`, `.github/workflows/validate.yml.template`, `.github/workflows/benchmarks.yml.template`), `user` = 0. LAND V5 local no mesmo conteúdo = `STALE 0`. O step `Deepen git history` (rail r1 F3) estava em `:541`, a paridade em `:425`. Reprodução local: fonte `--depth 1` ⇒ `STALE 3`; `--unshallow` ⇒ `STALE 0`.

## A cura
Mover o bloco do deepen (com `if: always()` e o fail-closed de ≥2 gerações) para logo depois de `Fetch the parity pin tag`, antes de `Protocol pointer render control` e da paridade; título do step nomeia os dois consumidores. YAML `safe_load` ok, `actionlint` ok, SHA-pins intocados. Nenhum script de produto muda.

## Verificação no land
Mesmo V-block do S327 (V1–V6 contra `EXPECTED-BASELINE.txt`; V7 diferido). A prova real é o próprio Smoke Install da CI após o land: `maintainer STALE 0`.

## Residual
Adopter com checkout RASO do framework: templates ficam PRESERVED (seguro, nomeado por path) até usar clone completo — nota para o ADR-194 na próxima cerimônia que o toque.
