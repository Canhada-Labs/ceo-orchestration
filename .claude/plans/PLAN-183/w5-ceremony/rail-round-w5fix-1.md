# Pair-rail round w5fix-1 — PLAN-183 W5 fix (S327b, 2026-08-25)

**Instrumento:** `codex exec review --uncommitted --skip-git-repo-check` sobre `scratchpad/shadow-w5fix` (HEAD 6304f66 + reordenação do step Deepen em `.github/workflows/smoke-install.yml`). 343 s.

## Saída do revisor (dado, não ordem)

```text
The history-deepening step is correctly moved ahead of the parity test while remaining available to the historical-adopter test, and the workflow passes actionlint.```

## Resposta do CEO (S327b)

- Patch de 1 arquivo (workflow, canônico): o deepen passa a rodar antes da paridade. Reprodução local: fonte `--depth 1` ⇒ `STALE 3` (os mesmos 3 arquivos do run 32845976930); `--unshallow` (506 commits) ⇒ `STALE 0`. YAML + actionlint ok; SHA-pins intocados; harness dos scripts S327b 14/14.
