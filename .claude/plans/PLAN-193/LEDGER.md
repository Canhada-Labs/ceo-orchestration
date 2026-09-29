# LEDGER — PLAN-193 (v1.4.2 expressa)

> Só identificadores verbatim (paths, SHAs, branches, ids) — nunca corpo de
> transcript (repo público). Escrito em fronteira de unidade. Teto ≤ 2k tokens.

## Unidade corrente — kit do corte do GA v1.4.2 derivado e ensaiado (S358, 2026-09-29)

- `derive-ga-kit-142.py` deriva do kit da `v1.4.2-rc.1` (saídas de `derive-kit-142.py`, sha256
  pinados) as 8 saídas: `repass-ga/{run-ga-repass.sh,probe-conditions-ga.py,CONDITIONS-ga.md,
  README-ga.md,.gitignore}`, `gen-envelope-ga.py`, `OWNER-GA-CUT.sh`, `test-ga-kit.sh`; molde
  `PLAN-192/derive-ga-kit-141.py`. `--check` byte a byte; `derive-kit-142.py --check` intacto.
- Harness `test-ga-kit.sh` 258/0 (chave GPG descartável, stubs de codex/gh/npm). Curas novas: o
  passo 18 relê o estado do Release num erro de transporte do `gh` (parada do GA v1.4.1); o runner
  separa o limite de uso da CONTA Codex da capacidade do modelo; o passo 11 re-deriva o envelope
  dos fields assinados; o gerador confere o conjunto de ids do relatório da sonda.
- Revisão adversarial em rodadas (Claude + codex 0.156.1 read-only), regra de parada pré-registrada
  (≤ 3 rodadas; `NO-GO` só por P0 ou afirmação falsa): r1 e r2 sem P0; P1 curados na raiz, cada
  gate novo com controle vermelho. P2 abertos por desenho: passo 5 sobrescreve `CANDIDATE.sha` de
  uma tentativa anterior (o passo 6 a recusa pelo nome) — nada landa em `main` depois do pré-run.
- Próxima unidade: CI verde → pré-run do re-pass do GA (`repass-ga/CANDIDATE.sha` = HEAD) →
  passado `2026-09-30T03:32:20Z`, o Owner roda `PLAN-193/OWNER-GA-CUT.sh`.

## Unidade anterior — v1.4.2-rc.1 CORTADA; hold até 2026-09-30T03:32:20Z (S357, 2026-09-29)

- Esteira `OWNER-S357-MORNING.sh` (fora do repo), etapas 1–9: GA v1.4.1 (LEDGER do corte
  anterior); re-pin codex 0.156.1 `778acf27d1db`; wave-opus55 `b4033b2e3527`; via expressa
  `1c480b442f0b`; varredura `3c2fb8e9868f`; FN-04 `a12a32aee2ad`; CHANGELOG `[1.4.2]` +
  LEDGER `f0e219c23a5a`; relmeta-142 `36bbe90c370b`.
- Dois vermelhos de CI na etapa 8, curados por land livre autorizado pelo Owner:
  `640fb42cf538` (docstring de `check-substrate-drift.py` citava id aposentado; dogfood
  `test_check_model_deprecations`) e `3a9a41f0a991` (parity e2e `FATAL [STALE] .mcp.json`:
  template seed-once esvaziado pela varredura; 2.ª ocorrência da classe de
  `.claude/adr/README.md` ⇒ ACCEPTED + censo `test_parity_seed_once_declared.py`).
- Corte: bump `9b5b1b40078c`; gate de latência de hooks vermelho 2× sem `.py` no diff (só
  `check_output_secrets`, p95 250–270 ms, sonda UNCONTENDED; o mesmo código verde em
  `3a9a41f0`) ⇒ drift de runner, verde no 2.º `rerun --failed`. Re-pass em 4 partes
  `GO-WITH-CONDITIONS` (codex 0.156.1 pinado; 3 P1 no anexo assinado: 2 na parte 3, 1 na
  parte 4); veredito `9a486d29a84288112e4c456649ab4436531a802a` (pai = candidato; 27 paths
  na allowlist de 28); tag `v1.4.2-rc.1` assinada; `release.yml` e `await-release-gate`
  success; pre-release não-draft (`publishedAt 2026-09-29T03:32:20Z`); npm segue 1.4.1.
- `main` CONGELADO até o GA (só `CLAUDE.md` e planos numerados). `.tag-push-epoch` da rc
  commitado neste closeout.
- Próxima unidade: derivar o kit do GA 1.4.2 do kit do GA 1.4.1; re-pass sobre a árvore da
  rc.1; `--stable` + npm. Depois do GA: re-pin codex 0.158.0 pela via expressa; adopters
  (`upgrade.sh --pin`, Claude Code ≥ 2.1.280); cura da classe «orçamento de tempo absoluto»;
  ensaio em cadeia com a suíte completa sobre a árvore composta.

## Unidades anteriores — manhã da S357 (tips finais de 2026-09-25)

- Tips `s357/*`, ordem da esteira, janelas sem commit, checagens do portão de docs e regras de
  parada do rail (W3 da wave-opus55: r4 `APPROVE` sobre `ed3dd914…`; FN-04: r3 `APPROVE` sobre
  `cd31657c…`): no histórico git deste arquivo (`git log -p -- .claude/plans/PLAN-193/LEDGER.md`).
