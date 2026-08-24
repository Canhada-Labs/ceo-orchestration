# Pair-rail — wave-cli, rodada 8 (S326, 2026-08-24 17:03–17:1xZ)

**Instrumento:** `codex exec review --uncommitted --skip-git-repo-check` sobre o clone-sombra com o
pacote curado das rodadas 1–7 (patch `Patch-sha256 71c8c78b…`) e todos os materiais atuais. `RAIL_RC=0`.

**Resumo do revisor (verbatim):** *"The landing workflow omits its own referenced audit artifacts
from the staged commit, and the new runtime-path CLI still mishandles a supported short option after
`--project`."*

| # | Sev | Achado | Verificação | Disposição |
|---|---|---|---|---|
| 1 | P2 | O passo S stageia só `touched ∪ {sentinel, .asc}`; se SIGN/LAND/patch/registros estiverem untracked no momento do land, o commit referencia evidência ausente do repositório (AGENTS.md:9-10). | **CONFIRMADO como risco de fluxo** (no sombra os materiais estão untracked por construção; na árvore viva o fluxo previa commitá-los antes do SIGN, mas nada VERIFICAVA isso). | **CURADO r9:** G0 exige que SIGN, LAND, PROPOSED, patch, sentinel e todos os `cli-ceremony/rail-*.md` estejam RASTREADOS (`git ls-files --error-unmatch`); ausente ⇒ ABORTA. Controle natural: na árvore viva, antes do commit dos materiais, o G0 aborta; depois, passa. |
| 2 | P2 | `runtime_paths.py --project -h` aceita `-h` como PATH (a cura da r6 só rejeitava `--`). | **CONFIRMADO.** | **CURADO r9:** qualquer valor de `--project` iniciado por `-` ⇒ erro de uso (exit 2). Teste estendido com `--project -h`. |

Sem P0/P1 pela primeira vez; conteúdo do patch: 1 caractere em `_lib`. Rodada 9 para confirmar.
