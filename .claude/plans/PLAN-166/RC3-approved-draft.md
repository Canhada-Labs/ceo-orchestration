# RC3-approved — sentinel do pack de curas rc.3 (PLAN-166 W2)

> **Assinatura:** o próprio `OWNER-RC3-CUT.sh` copia este draft para
> `RC3-approved.md` e chama o gpg (pinentry 1) — você não precisa fazer
> nada à mão. O Anchor-SHA abaixo já está preenchido porque o corte
> exige HEAD exatamente nesse commit (G0 aborta se main tiver andado).

Plan: PLAN-166
Wave: W2 (curas do NO-GO do re-pass GA — corte da v1.3.0-rc.3)
Anchor-SHA: 0cb09c3cc587abdeaed33e0ff13b1c8b3677061d
Data: 2026-08-11

## Scope

```
CHANGELOG.md
.claude/scripts/local/verify-counts.sh
.github/release-checklist.md
.github/workflows/npm-publish.yml
.github/workflows/release.yml
.claude/scripts/tests/test_release_workflow_asserts.py
.claude/scripts/tests/test_verify_counts.py
```

Espelho fora do escopo canônico (mesmo commit, staged do W3 — evita que
o land do W3 REVERTA curas): `.claude/plans/PLAN-169/staged-w3/.github/workflows/{npm-publish,release}.yml`,
`.claude/plans/PLAN-169/staged-w3/MANIFEST.sha256`,
`.claude/plans/PLAN-169/W3-approved-draft.md` (prosa do item 8).

## O que este pack muda (curas dos 8 achados REAIS do NO-GO de 10/08)

Triagem completa: `repass-ga-rc2-NOGO/TRIAGE-ga-repass.md`. Rail de
curas (codex, worktree da rc.2): `repass-rc3-cures/` — verdito final GO.

1. **P1-a** `CHANGELOG.md`: header "as of v1.3.0" 188→190 ADRs;
   narrativa de governança 184→190 com os +2 nomeados (ADR-155-AMEND-1,
   ADR-190).
2. **P1-b** `CHANGELOG.md`: seção nova "Changed — install/upgrade
   semantics (PLAN-166/167/168)" — decisão única de ownership (ADR-190),
   rota forçada do SPEC/v1 com backup (ADR-155-AMEND-1), marker
   `.claude/.framework-version` MARKER-FIRST (root VERSION nunca tocado
   por upgrade), gerador único do pointer do PROTOCOL.md. Intro do
   1.3.0 cobre o trem inteiro.
3. **P1-a(gate)** `verify-counts.sh`: regra ESCOPADA do header do
   CHANGELOG — só o PREÂMBULO (antes do primeiro "## [") é varrido, com
   `finditer` e exigência de EXATAMENTE uma claim (rail r1 P1-4: claim
   de corpo não mascara header removido nem duplica o censo). CHANGELOG
   fica FORA de DOCS — o corpo carrega contagens históricas legítimas.
   Fail-closed em três modos: contagem errada, matcher morto e claim
   duplicada; 6 testes de fixture novos (`TestChangelogHeaderRule`).
   Parentéticos do help 188/29/21 → 190/31/22. Censo-espelho ratificado:
   +4 pares `*@CHANGELOG.md` em `test_verify_counts.py::_EXPECTED_SITES`.
4. **P2-d/e** `release-checklist.md`: inventário de version-sites ganha
   `.claude/.framework-version`; contagem hardcoded "~29 steps" REMOVIDA
   (o número re-stalearia no W3, que adiciona um step).
5. **P1-c** `npm-publish.yml`: passo fail-closed "Assert remote tag
   still points at this run's SHA" imediatamente antes do publish —
   UM snapshot `git ls-remote` (plain + peeled na mesma invocação;
   rail r1 P1-1) comparado a `GITHUB_SHA`; tag deletada (resolve vazio)
   e tag movida abortam; mesmo `if:` do publish (não avermelha o rerun
   idempotente já-publicado; rail r1 P1-2). Fecha o cenário
   delete/re-tag em que o run OBSOLETO ainda aprovável publicaria a
   árvore errada irreversivelmente. Pins de regressão:
   `NpmPublishTagLivenessTest` (presença, shape fail-closed,
   single-snapshot, if-condition, ordem imediatamente-antes-do-publish;
   resolver LIVE-ONLY com marker `PLAN-166 W2 rc.3` — ausência = FALHA
   dura, nunca skip; rail r1 P1-5).
6. **Lição S300** `release.yml`: timeout do release-gate 20→35 min
   (suíte leva 19-20 min em runner carregado; attempt-1 da rc.2 estourou;
   regra "margem <20% ⇒ bump pré-tag"). Cascata do observador (rail r1
   P1-3): deadline do poller do await-release-gate 1800→2700 s e
   timeout do job 35→50 min — o observador SEMPRE sobrevive ao
   produtor (release-gate 35), com teste relacional
   `ObserverProducerDeadlineTest` (deadline ≥ gate+10min; job > deadline).
   Mesmo hunk no staged-w3 (patch pós-GA aplicado ANTES do corte +
   re-pin do MANIFEST) — live e staged idênticos; o W3 apenas mantém.

## Resíduo aceito (registro honesto)

- (curado no rail r1 P1-5) O resolver dos pins rc.3 é LIVE-ONLY e
  fail-hard: sem fallback staged; live sem o marker = FALHA do teste,
  nunca skip. O land é atômico (workflow curado + testes no mesmo
  commit), então não existe janela legítima de skip.
- (rail r3 P1-1) O CLAUDE.md §4 ainda diz "install.sh e upgrade.sh
  observam → chamam → executam" — impreciso: os call sites de
  `_ownership_verdict()` são só do upgrade (1634/1944/2107); o install
  fica ANTES da decisão (registra a entrega ADR-155 que o upgrade lê).
  O CHANGELOG desta rc.3 descreve o split verdadeiro; a prosa do
  CLAUDE.md é cache-stable e vai ao ledger do PLAN-169 (cura via
  cerimônia futura, não neste corte).
- P2 deferidos ao próximo trem (não mudam o artefato publicado):
  `await_release_gate.parse_timestamp` normaliza componentes fora de
  faixa (99:99:99) via `calendar.timegm`; `install-npm.sh` (stager
  LOCAL) ainda copia root README.md sobre npm/README.md (paridade de
  tooling local; produção já preserva). Ambos vão para o ledger do
  PLAN-169.

## Autorização

A assinatura GPG deste arquivo autoriza o `OWNER-RC3-CUT.sh` a aplicar
`staged-rc3/` (MANIFEST + BASELINE conferidos fail-closed) sobre os 7
caminhos canônicos do Scope, commitar conforme a allowlist fechada do
script, e cortar a tag v1.3.0-rc.3. O hold ADR-103 reinicia no
publishedAt da rc.3.
