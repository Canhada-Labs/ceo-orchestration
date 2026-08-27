# Pacote E — rail codex rodada 6 (shadow-E RE-DERIVADA sobre cc00235, 2026-08-27 ~13:10 -03)

Rail-Verdict: REJECT
Comando: `codex exec review --uncommitted --skip-git-repo-check` na shadow-E re-derivada por item (DESIGN-E §10: rebase sobre `cc00235` depois do land de C; `smoke-install.yml` composto, `timeout-minutes` 83+43=126). Modelo `gpt-5.6`, esforço xhigh. Saída bruta: `<scratchpad 02edd09e>/rail-E-round-6.txt`.

## Achados

- **[P1] Select the hook template for the active ceremony** — `scripts/upgrade.sh:2570` (`_merge_lifecycle_hooks_into_settings`). A derivação lia `settings.base.json` incondicionalmente; `install.sh:2145` instala `settings.user.json` sob `--ceremony user`, um perfil que omite de propósito os 10 hooks de governança que bloqueiam ou exigem GPG/sentinel. O upgrade re-registraria exatamente esses, convertendo o perfil advisory em maintainer.

## Verificação (claim COMO FEITA — medida)

- `settings.base.json` = 47 registros; `settings.user.json` = 20. Só-na-base = 26 = 10 excluídos de propósito (lista do `_comment` do template) + 16 defasados (a base cresceu depois de 30/07; `check_ledger_checkpoint.py` entre eles).
- `CEREMONY_EFFECTIVE` já é a decisão única da cerimônia no `upgrade.sh` (:884–:900; fail-safe `user`); o merge era o único consumidor que a ignorava.
- Classe pré-existente e ALARGADA pela wave: os 6 literais pré-cura também são só-na-base (6 → 27 nomes, agora com os 10 bloqueadores). As rodadas 1–5 não viram — rodada limpa prova a superfície, não o entregável.

## Disposição

- **CURADO na sombra** (DESIGN-E §11): seleção do template pelo `CEREMONY_EFFECTIVE` (`maintainer` → base; qualquer outro valor, inclusive ausente → `user`, fail-safe); mensagem nomeia template e cerimônia; 4g continua 0 literais `.py`.
- Testes: unidade 49 → 57 (`TestCeremonySelectsTheTemplate`, 8 casos, com controle positivo de seleção viva; `TestNoSecondRoster` +2 asserções); controle vermelho do oráculo contra a função pré-cura registrado no log da sessão; e2e +E.14 (9 asserções, install real `--ceremony user`, controle positivo E.14i).
- Residual declarado → **OQ-E5**: `settings.user.json` defasado (16 hooks não-deliberados ausentes) — wave própria (derivar por subtração + paridade), fora do Scope de E.
- Próxima rodada: r7 sobre a sombra curada; o SIGN exige que o ÚLTIMO registro seja APPROVE.
