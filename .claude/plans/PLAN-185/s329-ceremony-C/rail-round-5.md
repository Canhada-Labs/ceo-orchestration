# Pacote C — rail codex rodada 5 (shadow-185 estado FINAL, 2026-08-27T04:16:10Z)

Rail-Verdict: APPROVE
Comando: `codex exec review --uncommitted --skip-git-repo-check` — ZERO blocos `Full review comments:` (rodada limpa, sem sequer citações). Histórico: r1 2P1+1P2 → r2 3P1+1P2 → r3 2×por-construção → r4 2P1+1P2 → **r5 limpa no estado final** (curas todas com reprodução; DESIGN-C §12/§13/§14). e2e final na sombra: 105 passed / 0 failed.

## Adendo (27/08 09:20) — abort do LAND em V5 (F1.8), curado no patch effaeb87…

O LAND real do Owner abortou 2× em V5 com `F1.8 — re-install into the same path DIFFERS: ./.claude/repo-profile.yaml`, enquanto 5 reproduções sem TTY davam 105/0. Mecanismo MEDIDO: o bloco RAG-sidecar do `install.sh` (`[[ -t 0 ]]`, :3053) só roda sob TTY e invoca `detect-repo-profile.py`, que carimba `detected_at`/`created_at` com o relógio ⇒ dois installs limpos diferem por timestamp SÓ no terminal do Owner. Reproduzido determinístico com `script` (pseudo-TTY): pré-cura 104/1, pós-cura 105/0. Cura (no e2e, dentro do patch): `_install` exporta `CEO_RAG_INSTALL_PROMPT=0` (o kill-switch que `smoke-install.sh:183` já usa) + o filtro do F1.8 exclui `repo-profile.yaml` (mesma classe do `.install-state.json`). Lição para todo harness: uma rodada verde SEM TTY não prova a cerimônia do Owner, que roda COM TTY. Rail-Verdict da rodada 5 mantido (a mudança é no TESTE, não no código canônico; conteúdo revisado inline pelo CEO).
