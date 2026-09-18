---
id: PLAN-192
title: Corte da v1.4.1 — patch fora de ordem que entrega o guard de Workflow aos adopters
status: draft
created: 2026-09-18
owner: CEO
depends_on: [PLAN-190]
level: L2
budget_tokens: "kit + relmeta + re-pass: 300-600k de sessão do CEO; re-pass do codex = 3 partes (cota do Owner, não tokens Claude); zero subagentes Opus previstos"
budget_sessions: "1-2 (rc.1 no dia 1; GA depois do hold de 24 h)"
context_risk: medium
external_wait: "4 momentos do Owner: assinatura do re-pin do codex, assinatura da relmeta, pinentry do verdict-fields, pinentry da tag (+ SIM do push); CI do candidato e do commit do veredito; hold ADR-103 de 24 h entre a rc.1 e o GA"
eta_calendar: "rc.1 em 2026-09-18/19; GA >= 24 h depois do publishedAt do pre-release"
tags: [release, patch, workflow-guard, adopters]
---

## Context

**Mandato do Owner (2026-09-18, registrado no fim da S355, verbatim):** «o próximo terminal finaliza o
que entra na 1.4.1, assina, publica, e atualiza os repos que uso o framework pra seguirmos trabalhando.
essa é a urgência máxima agora. inclui o que dá pra fazer rápido e bora.»

O que os adopters precisam é o guard de retomada de `Workflow` (PLAN-190 W1, assinado em `075beed9`):
o texto assinado da W1 diz que, nos consumidores, ele só vale «depois de um `upgrade.sh` para uma
versão que contenha este commit». A release é essa rota.

Medido nesta sessão (2026-09-18, checkout em `107a5bda`, Validate verde no HEAD):

| fato | valor | como |
|---|---|---|
| delta `v1.4.0..HEAD` | 96 arquivos, +15.057 linhas; fora de `.claude/plans/`: 43 arquivos | `git diff --shortstat`, `--numstat` |
| planos citados nos assuntos da faixa | PLAN-169, PLAN-189, PLAN-190, PLAN-191 | `git log --format=%s v1.4.0..HEAD` |
| ADRs tocados na faixa | nenhum | `git diff --name-only v1.4.0..HEAD -- .claude/adr/` |
| codex instalado × pin | 0.155.0 × manifesto 0.154.0 ⇒ `payload_sha256_mismatch`, rail fail-CLOSED neste repo | `check_pair_rail.py --verify-codex-pin` |
| `release.sh` e `_release_tag_guard.py` | membros do manifesto ADR-192 (canônico) ⇒ mudar o bloco por-release é cerimônia | `gate-scripts-manifest.txt` |
| rc não publica no npm | só a tag GA passa pelo `npm-publish.yml` | cabeçalho do workflow |
| bombas de calendário | nenhum achado `unhealthy` hoje; todo plano `executing` tem `related_commits` | `check-staleness.py --json` |

**O achado que mudou o desenho.** As `conditions:` do envelope ASSINADO do GA v1.4.0
(`.claude/governance/pair-rail-verdict-v1.4.0.md`) dizem que os anexos P1 da rc.1 e do GA ficam
«known-open no GA, cura na 1.4.1». Esta 1.4.1 não cura nenhum deles. Decisão do Owner na OQ-1.

## Goal

`v1.4.1-rc.1` cortada, assinada e instalada nos adopters do Owner; `v1.4.1` promovida e publicada no
npm depois do hold de 24 h — com o anexo da v1.4.0 DECLARADO aberto no material assinado, nunca omitido.

## Approach

Reusar a mecânica que cortou a v1.4.0 (`PLAN-169/OWNER-RC1-CUT.sh`, `run-rc1-repass.sh`,
`gen-envelope-rc1.py`), derivada para a 1.4.1 com âncoras exatas e com o que mudou de verdade:

- **Base do re-pass = `v1.4.0`**, e o delta é pequeno: 3 partes por raio de dano ao adopter (o hook e o
  ledger; registração + entrega + sítios de versão; as CLIs e os dois docs de operador), não 7.
- **Codex pinado = o que o manifesto ADR-182 pinar no momento do corte.** O runner resolve a versão do
  manifesto por `npx` em cache próprio e verifica o payload pelo oráculo do pair-rail; nada de constante
  de versão digitada no runner.
- **relmeta em UM script** (a forma do re-pin: assinar sentinel → aplicar patch de sha pinado no
  sentinel → verificar → bateria → commit), em vez do par SIGN/LAND de ~750 linhas da 1.4.0: o patch
  aqui são 3 arquivos.
- **Regra de parada do rail, fixada ANTES da 1.ª rodada:** no máximo 2 rodadas de re-pass. `NO-GO` só
  por condição declarada FALSA contra o código ou por P0 (a regra que o Owner ratificou em 10/09 e
  13/09); P1 não declarado vai ao anexo assinado. Se a 2.ª rodada ainda der `NO-GO`, PARAR e levar ao
  Owner com as duas rodadas — não há 3.ª por conta própria.

Alternativas descartadas: (a) apontar os adopters para o `main` — o texto assinado da W1 promete «uma
versão»; (b) waiver `rc_hold` para GA no mesmo dia — é cerimônia canônica a mais e o hold não atrasa os
adopters, que sobem para a tag da rc.1 por `upgrade.sh --pin`; (c) esticar o range do pin do codex — o
gate real é o sha do payload, esticar o range não abre nada.

**Por que L2 e sem debate.** O corte é procedimento com precedente exato no repositório (o corte da
v1.4.0 e `.github/release-checklist.md`); o conteúdo que ele entrega já passou pelo seu próprio
debate (PLAN-190 r1) e por 6 rodadas de rail, e foi assinado. As duas partes canônicas daqui são
re-pins mecânicos (pin do codex; sha do `release.sh` no manifesto). O corte tem seu V2 embutido (o
re-pass do codex, exigido pelo passo 15 do `release.yml`) e seu V3 (tag GPG do Owner).

## Items

### W0 — o que entra, land livre
Check: python3 -m pytest .claude/hooks/tests/test_check_workflow_launch.py tests/unit/test_launch_ledger.py -q
- [x] W1.1 do PLAN-190: `relaunch --out` entrega o arquivo inteiro ou nenhum arquivo (laço de escrita;
  falha ⇒ rc 2 e remoção só do inode que a chamada criou). Prova por mutação no clone descartável:
  com a cura 7/7, sem o laço 3 vermelhos.
- [x] Entrada `[1.4.1]` do CHANGELOG, com a seção «Known-open» da OQ-1 e o rótulo de contagens em `v1.4.1`.
  Check: bash .claude/scripts/local/verify-counts.sh --quiet --no-tests
- [x] `fanout.py:72` — NÃO entra. A memória o chamava de «cura de uma linha»; medido: `decompose()` só
  recebe `prompt` e `max_units`; `archetype` e `task_class` não existem no ponto da chamada, e
  `gate.complexity` é a complexidade do prompt INTEIRO, não da sub-tarefa (passá-la só encarece a
  recomendação). Vai para a 1.4.2 com os outros mecanismos inertes.
  Check: none (doc-only)

### W1 — re-pin do codex CLI 0.154.0 → 0.155.0 (cerimônia; 1 pinentry)
Check: python3 .claude/hooks/check_pair_rail.py --verify-codex-pin "$(command -v codex)"
- [ ] Materiais em `.claude/plans/PLAN-189/codex-pin-0155/` no HEAD de `origin/main`.
- [ ] Owner roda `bash .claude/plans/PLAN-189/codex-pin-0155/OWNER-PIN-SIGN.sh` e dá push.
  Ensaiado em clone descartável: dry-run verde; modo real com pseudo-TTY e chave descartável = commit
  de exatamente 4 paths, assinatura verifica, `verified`; controle vermelho (codex falso no PATH) =
  aborta no passo 4, HEAD inalterado, `.asc` removido, árvore limpa.

### W2 — relmeta-141 (cerimônia; 1 pinentry)
Check: python3 -m pytest .claude/scripts/tests/test_release_bump_sites.py -q
- [ ] Bloco por-release do `release.sh` (`TARGET_BASE="1.4.1"`, título, escopo DERIVADO de
  `git log v1.4.0..HEAD` + ADRs tocados, headline) + sha do `release.sh` no `gate-scripts-manifest.txt`
  + re-pin CONSCIENTE de `test_tag_annotation_carries_the_whole_train_and_no_stale_release`.
- [ ] O bloco é inerte em aspas duplas de bash (sem crase, sem `$` não escapado) e nenhum semver nu além
  de `TARGET_BASE` (o teste `test_driver_derives_every_version_string_from_target_base` é o oráculo).
- [ ] Materiais de cerimônia são o ÚLTIMO land livre antes da assinatura (o escopo é derivado do log).

### W3 — kit da rc.1 em `.claude/plans/PLAN-192/`
Check: bash .claude/plans/PLAN-192/test-rc1-kit.sh
- [ ] `repass-rc1/run-rc1-repass.sh` (3 partes, base `v1.4.0` pinada por objeto e commit, codex resolvido
  do manifesto), `repass-rc1/README-rc1.md` (escopo e o que fica de fora, com o motivo),
  `repass-rc1/CONDITIONS-rc1.md` (as condições declaradas: OQ-1, o hook que pode bloquear no perfil
  `user`, as CLIs sem hook, os limites assinados da W1).
- [ ] `gen-envelope-rc1.py` (precedente = `pair-rail-verdict-v1.4.0.md`; prosa do review record verdadeira
  para a 1.4.1) e `OWNER-RC1-CUT.sh` (20 passos resumíveis).
- [ ] Ensaio do kit com `CODEX_BIN` stub e chave descartável, em clone descartável.

### W4 — corte da rc.1 (Owner no terminal)
Check: python3 .claude/scripts/local/_release_tag_guard.py delta --repo . --tag v1.4.1-rc.1
- [ ] `bash .claude/plans/PLAN-192/OWNER-RC1-CUT.sh` — pinentry do verdict-fields, pinentry da tag, SIM do push.
- [ ] `release.yml` verde na tag; GitHub Release marcado pre-release, não draft.

### W5 — adopters na rc.1
Check: none (doc-only)
- [ ] Em cada repo: `.claude/` limpo (commitar antes — o `upgrade.sh --pin` recusa árvore suja), `doctor.sh`,
  `upgrade.sh --pin v1.4.1-rc.1 --dry-run`, upgrade real COM a cerimônia gravada ou passada (sem isso o
  hook chega sem registração), `doctor.sh`, commit. São três repositórios do Owner; os nomes e o
  estado medido de cada um ficam no registro privado de memória, não neste repositório público. Num
  deles o upgrade 1.4.0 foi aplicado e nunca commitado: vira commit PRÓPRIO antes da 1.4.1.
- [ ] Conferir em cada um que `check_workflow_launch.py` está REGISTRADO no `settings.json`, não só no disco.

### W6 — GA (>= 24 h depois do publishedAt do pre-release)
Check: npm view ceo-orchestration version
- [ ] Kit do GA derivado do kit da rc.1; re-pass sobre a árvore da rc.1; `--stable`; npm `latest=1.4.1`.
- [ ] Adopters re-pinados na tag GA (no-op de conteúdo esperado; se NÃO for no-op, investigar antes).

## Open questions

- **OQ-1 — o anexo da v1.4.0 prometia «cura na 1.4.1». RESOLVIDA (Owner, 2026-09-18).** Opção escolhida,
  verbatim: «Declarar e seguir (Recomendado)» — «Corto a 1.4.1 pequena agora. O material assinado da
  1.4.1 e o CHANGELOG dizem, com todas as letras, que o anexo da 1.4.0 continua aberto e passa para a
  1.4.2, e por quê (patch urgente fora de ordem). Honesto e rápido; o revisor julga isso como condição
  declarada, não como promessa quebrada.»
- **OQ-2 — commits e push de lands livres nesta sessão. RESOLVIDA (Owner, 2026-09-18).** Opção escolhida,
  verbatim: «Sim, nesta sessão (Recomendado)» — «Commito e dou push de cada land livre depois da bateria
  de gates verde, e te aviso o que subiu. Tudo que é canônico continua exigindo a sua assinatura GPG,
  como sempre. É o modelo das sessões anteriores.»
- **OQ-3 — qual `npm_integrity` o manifesto do codex grava.** O ADR-182 §5 manda o do artefato de
  PLATAFORMA; o re-pin de 0.154.0 gravou o do pacote principal sem declarar. O pack 0.155 volta ao ADR e
  declara o desvio no sentinel (o campo não tem leitor mecânico). O Owner ratifica ao assinar; trocar é
  uma linha no `.new` antes da assinatura.

## How to continue

Primeira mensagem de uma sessão nova: «Retomar o PLAN-192 (corte da v1.4.1). Ler este plano e
`git log --oneline v1.4.0..HEAD`; conferir em que W está pelo que já existe: `codex-cli-pin-manifest.json`
em 0.155.0? `TARGET_BASE` do `release.sh` em 1.4.1? `.claude/plans/PLAN-192/repass-rc1/.cut-state`?
tag `v1.4.1-rc.1` no remoto?» O `OWNER-RC1-CUT.sh` é resumível: rodar de novo retoma do primeiro passo
não concluído.

## Success criteria

- [ ] `git tag -v v1.4.1-rc.1` e `git tag -v v1.4.1` = Good signature da chave do Owner; `release.yml` verde nas duas.
- [ ] O envelope assinado das duas tags carrega a condição da OQ-1 (anexo da v1.4.0 aberto, cura na 1.4.2).
- [ ] npm `latest=1.4.1`.
- [ ] Os três adopters com o marcador `1.4.1`, `check_workflow_launch.py` registrado e o upgrade commitado.
- [ ] Memória e `CLAUDE.md` atualizados no closeout; PLAN-190-FOLLOWUP-relaunch-out-partial-write em `done`.
