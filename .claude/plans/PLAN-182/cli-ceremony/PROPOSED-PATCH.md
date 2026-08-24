# PLAN-182 — cerimônia `wave-cli`: o CLI do resolvedor único (OQ-6) + cura estrutural do achado S326

**Sessão:** S326 (2026-08-24). **Sentinel:** `.claude/plans/PLAN-182/wave-cli-approved.md`.
**Patch:** `cli-ceremony/S326-CLI-CEREMONY.patch` (gerado do clone-sombra; `Patch-sha256` no sentinel).
**Scripts:** `OWNER-S326-SIGN.sh` (assina, não aplica) → `OWNER-S326-LAND.sh --dry-run` → `OWNER-S326-LAND.sh` (aplica, verifica V1–V6 e faz o staging explícito, incluindo o `.asc`) → `git commit` → `git push`.

## O que o pacote entrega (12 paths, 1 assinatura)

| # | Path | Canônico? | O quê |
|---|---|---|---|
| 1 | `.claude/hooks/_lib/runtime_paths.py` | **sim** | `__main__` — CLI `[--state-dir\|--slug\|--project-dir] [--project PATH]`; `runtime_state_dir(project=None)` (compatível). Contrato no docstring §CLI contract. Leaf mantido (teste por AST). |
| 2 | `.claude/hooks/_lib/test_isolation.py` | **sim** | **Axis 3** — redirect da janela de COLEÇÃO no import (snapshot do log vivo ANTES; `CEO_AUDIT_LOG_DIR`+`CEO_PROJECT_STATE_DIR` → `ceo-collect-isolation-*`; `atexit` rmtree). Fecha a classe S326 e a janela de teardown. |
| 3 | `.claude/governance/gate-scripts-manifest.txt` | **sim** (ADR-192) | sha256 novo de `verify-counts.sh`. |
| 4 | `.claude/scripts/local/verify-counts.sh` | membro ADR-192 | `CEO_AUDIT_LOG_DIR` descartável SÓ no subprocesso de `--collect-only` (cinto-e-suspensório sobre o item 2). |
| 5 | `templates/codex/pre-push-review-gate.sh` | não | `_state_dir` → CLI (`--state-dir` + `/state`); `_repo_top` novo; resolvedor ausente ⇒ VAZIO + nota no stderr ⇒ path (b) indisponível, trailers seguem valendo. |
| 6 | `templates/grok/pre-push-review-gate.sh` | não | idem (gêmeos curados juntos). |
| 7 | `.claude/scripts/ceo-backup.sh` | não | slug/dir pelo CLI; `--project-slug`/`CEO_PROJECT_NAME` = override EXPLÍCITO; sem resolvedor ⇒ exit 2. |
| 8 | `.claude/scripts/ceo-restore.sh` | não | idem. |
| 9 | `.claude/scripts/tests/test_templates_use_single_resolver.py` | não | `_DECLARED_DEBT` esvaziada (anti-rot exigia) + asserção POSITIVA: os gates CHAMAM `--state-dir`. |
| 10 | `.claude/hooks/tests/test_runtime_paths.py` | não | `TestCli` (7 testes: paridade com as funções, `--project`, precedência do NATIVE, erros de uso exit 2 com stdout vazio, `-m _lib.runtime_paths`, leaf por AST). |
| 11 | `.claude/hooks/tests/test_collect_only_audit_isolation.py` | não | 3 testes unitários do Axis 3 (VERMELHOS num land parcial). |
| 12 | `.claude/plans/PLAN-182-audit-path-isolation.md` | não | checkboxes 764/766 fechadas com evidência; bloco de foco marcado ENTREGUE. |

`dist/` é gitignored — o espelho `dist/ceo-plugin/hooks/_lib/runtime_paths.py` sai de `python3 scripts/build-plugin.py` no V5 do land.

## O que fica FORA (declarado)

- **Alargar o censo M1** (`derive-audit-family.py`) para a forma `${VAR:-literal}` — muda a família publicada no `CLAUDE.md` §5 (Gate-1, só se edita no closeout). Vai no closeout da S326, agora que `ceo-backup/restore` não caem mais na forma.
- A rota do installer (`settings.base.json` + merge aditivo no `upgrade.sh`) — decisão do Owner ainda pendente (checkbox 759; recomendação do CEO: NÃO).

## Verificação (o land executa, fail-closed)

- V1 suítes-alvo (incl. os 3 testes do Axis 3, que ficam vermelhos se só metade do pacote aterrissar).
- V2 manifesto ADR-192 casa byte a byte.
- V3 `--assert-migrated` 0 e M4 sob `CEO_AUDIT_FAMILY_M4_REQUIRED=1` 0.
- V4 gates estáticos: `check-test-audit-isolation.py`, `check-test-env-hygiene.py`, `validate_governance_fast.py`.
- V5 `build-plugin.py` + espelho `dist/` byte-idêntico à fonte.
- V6 **live-fire:** `verify-counts.sh` completo com delta **0** na cadeia viva (antes da S326: 124).
