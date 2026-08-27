# Pacote E — rail codex rodada 10 (shadow-E curada do r9, 2026-08-27 ~16:00 -03)

Rail-Verdict: REJECT
Comando: `codex exec review --uncommitted --skip-git-repo-check` na shadow-E após a cura do r9 (cerimônia desconhecida ⇒ nenhum hook; unit 82/82). Modelo `gpt-5.6`, esforço xhigh. Saída bruta: `<scratchpad 02edd09e>/rail-E-round-10.txt`. Sem bloco `Full review comments:`; um único achado em `Review comment:` — tratado como achado, não como rodada limpa.

## Achado

- **[P2] Reject malformed template env before merging hooks** — um template-fonte com `.env` PRESENTE mas não-objeto era coerçido a `{}` na derivação e os hooks eram escritos sem as settings (para `settings.user.json`: `check_config_protection.py` sem a advisory ⇒ bloqueante). **REAL** (forma aceita pelo guard; nenhum template shipado a tem).

## Disposição

- **CURADO na sombra** (DESIGN-E §15): o guard estrutural do template passa a emitir `ENV (<tipo>)` quando `.env` está presente e não é objeto — recusa integral, nomeada, nada escrito (mesma regra dos eventos não-array). Unidade 82 → 84 (`TestTemplateEnvMustBeAnObject`: recusa nomeada com controle de `env: {}`).
- Próxima rodada: r11 sobre a sombra curada; o SIGN exige que o ÚLTIMO registro seja APPROVE.
