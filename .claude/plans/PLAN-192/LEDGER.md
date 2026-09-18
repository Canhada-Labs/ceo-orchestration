# LEDGER — PLAN-192 (corte da v1.4.1)

> Só identificadores verbatim (paths, SHAs, ids) — nunca corpo de transcript
> (repo público). Escrito em fronteira de unidade. Teto ≤ 2k tokens.

## Unidade corrente — materiais prontos e ensaiados; aguardando as duas assinaturas do Owner (S356, 2026-09-18)

- Status do plano: `draft` (`.claude/plans/PLAN-192-release-v1-4-1.md`); OQ-1 e OQ-2 RESOLVIDAS (verbatim no plano).
- Lands, em ordem: `38eb917c` (pack `PLAN-189/codex-pin-0155/`), `47870320` (PLAN-190 W1.1), `737814a5` (plano + CHANGELOG `[1.4.1]`), `c782cbea` (kit de corte + materiais da relmeta-141), esta unidade (este LEDGER).
- Materiais no diretório: `derive-kit-141.py` → `repass-rc1/run-rc1-repass.sh`, `gen-envelope-rc1.py`, `OWNER-RC1-CUT.sh`, `test-rc1-kit.sh` (derivados; `--check` byte a byte); `repass-rc1/README-rc1.md`, `repass-rc1/CONDITIONS-rc1.md`, `repass-rc1/.gitignore`; `relmeta/apply-relmeta141-edits.py`, `relmeta/derive-relmeta141.sh`, `relmeta/RELMETA141.patch` (sha256 `edba3bb889ffd2c7ffde2c56c5ce474581e829a55b8f2b06db9992dfe7766dae`), `relmeta/relmeta141-approved.md`, `relmeta/OWNER-RELMETA141-SIGN.sh`.
- Próxima unidade (Owner, nesta ordem, as duas ANTES de esperar o CI): `PLAN-189/codex-pin-0155/OWNER-PIN-SIGN.sh` + push; `PLAN-192/relmeta/OWNER-RELMETA141-SIGN.sh` + push. Depois: todos os workflows do HEAD verdes (Smoke Install 1h40–1h55) → `PLAN-192/OWNER-RC1-CUT.sh`.
- Invariante até a assinatura da relmeta: nenhum assunto de commit em `v1.4.0..HEAD` pode citar um `PLAN-NNN` fora de {169, 189, 190, 191, 192}, e `release.sh`, `gate-scripts-manifest.txt` e `test_release_bump_sites.py` não mudam — senão o passo 1/8 da cerimônia aborta (re-derivar com `relmeta/derive-relmeta141.sh`, commitar, re-ensaiar).
- Regra de parada do re-pass, pré-registrada: 2 rodadas no máximo; `NO-GO` só por condição declarada FALSA ou P0; 2.ª `NO-GO` ⇒ parar e levar ao Owner.
- Dívida assinada que este corte transfere: o anexo P1 do envelope `pair-rail-verdict-v1.4.0.md` («cura na 1.4.1») passa para a 1.4.2 (OQ-1; CHANGELOG `[1.4.1]` §Known-open; condição 1 de `CONDITIONS-rc1.md`).
