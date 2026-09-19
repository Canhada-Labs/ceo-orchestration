# LEDGER — PLAN-192 (corte da v1.4.1)

> Só identificadores verbatim (paths, SHAs, ids) — nunca corpo de transcript
> (repo público). Escrito em fronteira de unidade. Teto ≤ 2k tokens.

## Unidade corrente — v1.4.1-rc.1 CORTADA; hold até 2026-09-20T02:28:57Z; main CONGELADO (S356, 2026-09-19)

- Rodada 3 (candidato `7602fbe46318a77f1f8740f81d5b08ef5080df94`): `GO-WITH-CONDITIONS` nas 3 partes, sem P0, nenhuma condição falsa. Evidência em `repass-rc1/` (MANIFEST 19/19, `RUNNER-OVERALL: rc=0`), commitada pelo passo 11.
- `OWNER-RC1-CUT.sh` 20/20 sem abort: bump no-op; passo 6 pulou por `evidence_complete_for`; veredito assinado `51bd2345cab15f182a5c6ff42f329d0e21829172` (pai = o candidato; 21 paths na allowlist fechada de 22); guard de delta verde nos passos 12, 15 e 16; **tag `v1.4.1-rc.1` assinada e verificada**; `release.yml` success; `await-release-gate` success; GitHub Release pre-release não-draft; `npm view` = 1.4.0.
- Hold ADR-103: `publishedAt = 2026-09-19T02:28:57Z` ⇒ GA só depois de `2026-09-20T02:28:57Z`. O `.tag-push-epoch` (1789783876 = 02:11:16Z) está commitado.
- **Main CONGELADO até o GA.** O único commit posterior à tag é o closeout `4606c3df7162` (CLAUDE.md + `.tag-push-epoch`), ambos FORA do escopo do re-pass (condição 15; README-rc1 §4) e não entregues a adopters.
- W5 (adopters) ADIADO por decisão do Owner (2026-09-19 ~05:05): os três ficam fora. Levantamento medido, para não refazer: memória `project-adopters-w5-survey-s356`.
- Próxima unidade: passado o hold, derivar o kit do GA deste (subir o teto de 90 min do passo 4 — o Smoke Install levou 1h51), re-pass sobre a árvore da rc.1, `release.sh bump --stable` + `tag --stable`. Depois: adopters, a opção B (`project-relaunch-out-structural-cure-after-v141`), `PLAN-190-FOLLOWUP-relaunch-out-partial-write` → `done`, e o OK do Owner para o status deste plano (segue `draft`).

## Unidade corrente — rodada 2 = GWC / `NO-GO` / GWC; Owner decidiu «A agora, B depois»; candidato da rodada 3 = só texto (S356, 2026-09-18)

- Rodada 2: candidato `3ed81cf657b3d22d012b1e32269671e86f3e4030`; só a condição 14 caiu (limpeza `lstat`→`unlink` não atômica). Arquivada em `PLAN-192/repass-rc1-20260918-NOGO-r2/` (`record.md`; vereditos sha256 `ec86430e…`, `023d8f12…`, `762f0cf1…`).
- Decisão do Owner (verbatim em `PLAN-192-release-v1-4-1.md` §Session history e no `record.md` da r2): opção A agora; opção B (cura estrutural do `relaunch --out`) depois do lançamento.
- Candidato da rodada 3: mesmos arquivos da rodada 2 (condições 7 e 14 + itens 20–22 da seção D; `### Fixed` e «Known-open» do CHANGELOG; os dois docs; README; prompt «ROUND 3» via `derive-kit-141.py`). Nenhum arquivo sob `.claude/hooks/`, `.claude/scripts/`, `scripts/`, `templates/`.
- Regra de parada da rodada 3 (fixada antes): última desta via; outra `NO-GO` ⇒ parar, Owner.
- Próxima unidade: CI verde → CEO grava `repass-rc1/CANDIDATE.sha` e roda o runner → GO/GWC ×3 ⇒ Owner roda `PLAN-192/OWNER-RC1-CUT.sh` do passo 1.
- PENDENTE no closeout (depois da tag): linha no `CLAUDE.md` sobre a opção B.

## Unidade anterior — rodada 1 do re-pass `NO-GO`; candidato da rodada 2 = só texto (S356, 2026-09-18)

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
