# LEDGER — PLAN-192 (corte da v1.4.1)

> Só identificadores verbatim (paths, SHAs, ids) — nunca corpo de transcript
> (repo público). Escrito em fronteira de unidade. Teto ≤ 2k tokens.

## Unidade corrente — rodada 1 do re-pass `NO-GO`; candidato da rodada 2 = só texto (S356, 2026-09-18)

- Rodada 1: candidato `9e9840b2fc6c033498a0c12c65178a5254d0b04e` (bump, CI verde), `NO-GO` nas 3 partes, sem P0; condições falsas 7, 10, 12, 14, 15. Arquivada em `PLAN-192/repass-rc1-20260918-NOGO-r1/` (`record.md`; vereditos sha256 `f46ebb9e…`, `13716c56…`, `a4d9c157…`).
- Candidato da rodada 2: `CONDITIONS-rc1.md` (seção D nova), `README-rc1.md`, `run-rc1-repass.sh` (via `derive-kit-141.py`: contexto «ROUND 2» no prompt), `CHANGELOG.md`, `docs/workflow-recovery.md`, `docs/approval-gate.md`. Nenhum arquivo sob `.claude/hooks/`, `.claude/scripts/`, `scripts/`, `templates/`.
- Regra de parada: esta é a ÚLTIMA rodada. 2.ª `NO-GO` ⇒ parar e levar as duas ao Owner.
- Próxima unidade: CI verde no candidato → CEO grava `repass-rc1/CANDIDATE.sha` e roda `repass-rc1/run-rc1-repass.sh` → se GO/GWC ×3, Owner roda `PLAN-192/OWNER-RC1-CUT.sh` do passo 1 (`.cut-state` zerado; o passo 6 reconhece a evidência completa).
- Residual para o Owner: `RELEASE_HEADLINE` do `release.sh` diz «o arquivo inteiro ou nenhum arquivo» (condição 14 declara o limite).

## Unidade anterior — as duas cerimônias ASSINADAS; corte em curso, preflight curado (S356, 2026-09-18)

- Assinados pelo Owner: `7d807f4c` (re-pin codex 0.155.0) e `83fa5b64` (relmeta-141; `TARGET_BASE="1.4.1"`).
- Tentativas do `OWNER-RC1-CUT.sh`: 1.ª morreu no passo 1 por carga de CPU (`TestOutputScanPerfRigorous::test_p99_{1kb,5kb,10kb}` sob saturação); 2.ª morreu no passo 1 em `verify-counts.sh` completo (cifra `~15,400` × 16.231 coletados). Cura: esta unidade (16 sítios em 9 docs → `~16,200`; `docs/FAQ.md` e `docs/WHAT-WE-ARE.md` na parte 2 do runner).
- Próxima unidade: Validate verde no HEAD novo → Owner roda `PLAN-192/OWNER-RC1-CUT.sh` de novo (retoma do passo 1).

## Unidade anterior — materiais prontos e ensaiados; aguardando as duas assinaturas do Owner (S356, 2026-09-18)

- Status do plano: `draft` (`.claude/plans/PLAN-192-release-v1-4-1.md`); OQ-1 e OQ-2 RESOLVIDAS (verbatim no plano).
- Lands, em ordem: `38eb917c` (pack `PLAN-189/codex-pin-0155/`), `47870320` (PLAN-190 W1.1), `737814a5` (plano + CHANGELOG `[1.4.1]`), `c782cbea` (kit de corte + materiais da relmeta-141), esta unidade (este LEDGER).
- Materiais no diretório: `derive-kit-141.py` → `repass-rc1/run-rc1-repass.sh`, `gen-envelope-rc1.py`, `OWNER-RC1-CUT.sh`, `test-rc1-kit.sh` (derivados; `--check` byte a byte); `repass-rc1/README-rc1.md`, `repass-rc1/CONDITIONS-rc1.md`, `repass-rc1/.gitignore`; `relmeta/apply-relmeta141-edits.py`, `relmeta/derive-relmeta141.sh`, `relmeta/RELMETA141.patch` (sha256 `edba3bb889ffd2c7ffde2c56c5ce474581e829a55b8f2b06db9992dfe7766dae`), `relmeta/relmeta141-approved.md`, `relmeta/OWNER-RELMETA141-SIGN.sh`.
- Próxima unidade (Owner, nesta ordem, as duas ANTES de esperar o CI): `PLAN-189/codex-pin-0155/OWNER-PIN-SIGN.sh` + push; `PLAN-192/relmeta/OWNER-RELMETA141-SIGN.sh` + push. Depois: todos os workflows do HEAD verdes (Smoke Install 1h40–1h55) → `PLAN-192/OWNER-RC1-CUT.sh`.
- Invariante até a assinatura da relmeta: nenhum assunto de commit em `v1.4.0..HEAD` pode citar um `PLAN-NNN` fora de {169, 189, 190, 191, 192}, e `release.sh`, `gate-scripts-manifest.txt` e `test_release_bump_sites.py` não mudam — senão o passo 1/8 da cerimônia aborta (re-derivar com `relmeta/derive-relmeta141.sh`, commitar, re-ensaiar).
- Regra de parada do re-pass, pré-registrada: 2 rodadas no máximo; `NO-GO` só por condição declarada FALSA ou P0; 2.ª `NO-GO` ⇒ parar e levar ao Owner.
- Dívida assinada que este corte transfere: o anexo P1 do envelope `pair-rail-verdict-v1.4.0.md` («cura na 1.4.1») passa para a 1.4.2 (OQ-1; CHANGELOG `[1.4.1]` §Known-open; condição 1 de `CONDITIONS-rc1.md`).
