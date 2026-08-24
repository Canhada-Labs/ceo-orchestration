# Pair-rail — wave-cli, rodada 1 (S326, 2026-08-24 15:18–15:26Z)

**Instrumento:** `codex exec review --uncommitted --skip-git-repo-check` (codex-cli 0.147.0) sobre o
clone-sombra com os 12 arquivos do pacote não-commitados. `RAIL_RC=0`.

**Resumo do revisor (verbatim):** *"The collection-window redirect loses the real live-log snapshot in
xdist workers and should fail the repository's standard parallel CI run. Backup and restore also derive
project state from an arbitrary caller CWD, which can silently target the wrong directory."*

| # | Sev | Achado | Verificação contra o código | Disposição |
|---|---|---|---|---|
| 1 | P1 | `_redirect_collection_window()` recalcula o snapshot "vivo" a partir do env; sob `pytest -n auto` (`validate.yml:350`) o worker herda `CEO_AUDIT_LOG_DIR` já apontado para o `ceo-collect-isolation-*` do controller, então o recálculo devolve o dir de coleção e SOBRESCREVE a verdade. Falha `test_live_snapshot_was_captured_before_any_redirect` no CI paralelo e degrada o comparador WS-D1. | **CONFIRMADO.** O controller importa o conftest antes de spawnar os workers; `spawn`/`fork` herdam o env. O passe não-serial do sombra (xdist) é o controle positivo. | **CURADO r2:** preservar `LIVE_LOG_SNAPSHOT_VAR` herdado quando presente; só resolver quando ausente. Teste novo: subprocesso com o var herdado + `CEO_AUDIT_LOG_DIR` apontado a um dir de coleção falso ⇒ snapshot preservado. |
| 2 | P2 | `ceo-backup.sh`/`ceo-restore.sh` chamam `_resolve_rp --slug/--state-dir` ANTES do walk-up do adopter root; de um subdiretório sem `CLAUDE_PROJECT_DIR`, o resolvedor cai no cwd e o backup reporta "nada para fazer backup" com exit 0. | **CONFIRMADO.** `ceo-backup.sh` calcula `ADOPTER_ROOT` em :120-128, depois da resolução; `ceo-restore.sh` não tem walk-up. | **CURADO r2:** walk-up ANTES da resolução nos dois; `root="${CLAUDE_PROJECT_DIR:-<walk-up>}"` passado por `--project`; sem `.claude/` acima do cwd ⇒ falha alta (exit 2), nunca palpite. |
| 3 | P3 | `TestCli` foi anexado depois do bloco `if __name__ == "__main__": unittest.main()`, então a entrada direta do arquivo não descobre a classe nova (pytest coleta normalmente). | **CONFIRMADO.** | **CURADO r2:** bloco `__main__` movido para o fim do arquivo. |

Nenhum pushback nesta rodada — os três são defeitos verificáveis. Rodada 2 sobre o pacote curado.
