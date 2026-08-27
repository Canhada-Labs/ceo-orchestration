# Pacote E — rail codex rodada 7 (shadow-E curada do r6, 2026-08-27 ~13:50 -03)

Rail-Verdict: REJECT
Comando: `codex exec review --uncommitted --skip-git-repo-check` na shadow-E após a cura do r6 (seleção do template pela cerimônia; unit 57/57; e2e 60/0). Modelo `gpt-5.6`, esforço xhigh. Saída bruta: `<scratchpad 02edd09e>/rail-E-round-7.txt`.

## Achados

- **[P1] Preserve advisory mode when merging user hooks** — `upgrade.sh` (função `_merge_lifecycle_hooks_into_settings`). O merge copia só `.hooks`; `settings.user.json` entrega `check_config_protection.py` JUNTO com `env.CEO_CONFIG_PROTECTION_ADVISORY=1`, e sem a chave o hook é BLOQUEANTE. Um adopter `user` pré-PLAN-124 receberia o hook sem a chave. **REAL, medido** (template user: 2 chaves de env; base: 6, nenhuma a advisory; `upgrade.sh` não tocava `.env`).
- **[P1] Supply the required Owner-signed sentinel** — sentinel com `TO-FILL-AT-SIGN`, sem `.asc`. **Por construção** (estado pré-SIGN; o SIGN preenche e assina, o LAND recusa sem). Disposto como nas rodadas 2 e 3.
- **[P2] Require a leading boundary for Python hook keys** — regex de `_keys` sem lookbehind: `.check_ledger_checkpoint.py` rendia `check_ledger_checkpoint.py` (medido em jq); o oráculo Python já tinha a fronteira. **REAL.**
- **[P2] Reject multi-document template streams** — `jq -e` sobre stream de 2 documentos passa; `--slurpfile` carrega 2; o programa lê `$tpl[0]`. **REAL, medido.**

## Disposição

- **CURADOS na sombra** (DESIGN-E §12): `.env` do template viaja com `.hooks` (aditivo, adopter vence, forma inesperada preservada + nomeada, template sem `.env` não inventa chave; alargamento para o perfil maintainer DECLARADO); lookbehind no `match` de `_keys`; guard de documento único fail-closed e nomeado.
- Testes: unidade 57 → 69 (3 classes novas: `TestEnvTravelsWithTheRoster` 7, `TestTemplateMustBeExactlyOneDocument` 2, `TestHiddenScriptIsNotTheCanonicalRegistration` 3); e2e 60 → 62 (E.14j chave `user`-only derivada volta com o valor do template; E.14k controle `maintainer` não a recebe).
- Sentinel: por construção, sem ação.
- Próxima rodada: r8 sobre a sombra curada; o SIGN exige que o ÚLTIMO registro seja APPROVE.
