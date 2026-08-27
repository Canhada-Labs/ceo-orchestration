# Pacote E — rail codex rodada 8 (shadow-E curada do r7, 2026-08-27 ~14:40 -03)

Rail-Verdict: REJECT
Comando: `codex exec review --uncommitted --skip-git-repo-check` na shadow-E após a cura do r7 (`.env` viaja com `.hooks`; unit 69/69; e2e 62/0). Modelo `gpt-5.6`, esforço xhigh. Saída bruta: `<scratchpad 02edd09e>/rail-E-round-8.txt`.

## Achados

- **[P1] Distinguish inferred user from recorded user** — a seleção do template lia só `CEREMONY_EFFECTIVE`; sem install-state e sem flag o resolver responde `user` apenas como fail-safe de escrita na raiz (`_CEREMONY_PERSIST=0`). Um maintainer HISTÓRICO ficava sem os hooks só-na-base (o achado S328, para a população-alvo da wave) e recebia `CEO_CONFIG_PROTECTION_ADVISORY=1` (matcher bloqueante → allow). **REAL, medido** (interseção = 20 hooks do user ⊆ base; env comum = `CEO_QUIET_MODE`; user-only = a advisory).
- **[P2] Avoid duplicating partially present multi-command blocks** — bloco com vários comandos, adopter com alguns: `all(...)` falha e o bloco inteiro é appendado (duplicatas permanentes). **REAL** como forma aceita pelo guard; nenhum template shipado a usa (medido 0/0).

## Disposição

- **CURADOS na sombra** (DESIGN-E §13): terceira postura SHARED para cerimônia desconhecida (`maintainer/1` → base; `user/1` → user; resto → interseção derivada em runtime com o MESMO `_keys`, escrita em `$BAK_DIR/.claude/settings.template-shared.json`, NOTE com `WITHHELD:` por perfil e o opt-in `--ceremony maintainer|user`); `$jq_defs` compartilhado pelos dois programas jq; append só das entradas ausentes de um bloco.
- Testes: unidade 69 → 80 (`TestUnknownCeremonyTakesTheSharedRoster` 9; `TestPartiallyPresentMultiCommandBlock` 2; os 2 testes de fail-safe do r6 re-afirmados como invariante); e2e 62 → 69 (E.15, 7 asserções com dois controles).
- Próxima rodada: r9 sobre a sombra curada; o SIGN exige que o ÚLTIMO registro seja APPROVE.
