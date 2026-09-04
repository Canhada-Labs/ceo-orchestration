---
id: PLAN-185-FOLLOWUP
title: "Residuais do installer-write-safety: doctor.sh como 3o consumidor do predicado (FU-7) e a modelagem do censo (FU-1)"
status: done
created: 2026-08-31
completed_at: 2026-09-04
executing_at: 2026-09-04   # retroativo: a metade FU-7 executou na S337 (cc00235..c0cb915); o self-gate cai neste commit de fechamento
reviewed_at: 2026-09-04
reviewed_by: "Owner (S344, AskUserQuestion — OQ-W0-STOP decidida: «Manter o ratchet e fechar o plano (Recomendado)»; FU-7 ja executado sob autorizacao de chat na S337)"
related_commits: [cc00235, adb6e84, 2f71dea, c0cb915]
owner: CEO
depends_on: [PLAN-185]
level: L3
budget_tokens: "FU-7 40-80k (wave canonica de 1 path, molde = pacote E); FU-1 sem orcamento ate decisao do Owner sobre OQ-W0-STOP"
budget_sessions: 1-2
context_risk: low
external_wait: "FU-7: assinatura GPG do Owner (1 canonico). FU-1: decisao do Owner sobre OQ-W0-STOP (modelar vs manter ratchet)."
eta_calendar: "FU-7: 1 cerimonia. FU-1: indefinido (gatilho = decisao do Owner)."
tags: [seguranca, installer, doctor, censo, followup, canonico]
---

# PLAN-185-FOLLOWUP — doctor.sh no predicado de confinamento + censo

> **Lineage (PLAN-SCHEMA §1.4 — "parent shipped with explicit deferred AC
> items").** O PLAN-185 fechou `done` na S330 (`1c34eb5`) com dois residuais
> declarados no proprio fechamento (linhas 575-599 do plano-pai): FU-1 e
> FU-7/OQ-7. Este followup e o veiculo ratificado para os dois — ele NAO abre
> escopo novo.

## FU-7 — `scripts/doctor.sh` como 3o consumidor de `_wbm_dst_refuses`

**O defeito de classe:** `doctor.sh` (~1004 linhas) REPARA arquivos do
adopter com ~15 sitios de escrita (`cp`/`mv`/redirect) que nao passam pelo
predicado de confinamento de destino `_wbm_dst_refuses`
(`scripts/_framework_manifest_set.sh:743`) que `install.sh` e `upgrade.sh`
ja consomem desde `cc00235`. Um symlink pendente no lugar de um destino de
reparo escreve FORA do `$TARGET` — a mesma classe F1 do plano-pai, na
superficie que sobrou.

**Pre-requisito de ordem: CUMPRIDO.** A ratificacao de 2026-08-24 mandava
esta wave DEPOIS da OQ-E5 do PLAN-169 (wave-s330-F) — que landou em
`303ae55` (S332). Nada mais bloqueia alem da assinatura.

**Forma da wave (molde = pacote E do PLAN-185):**

> **EXECUTADA na S337 (2026-09-01), SEM cerimônia — a premissa "1 canônico"
> estava errada.** Medido antes de tocar qualquer byte: o oráculo
> `check_canonical_edit.py --is-canonical scripts/doctor.sh` responde **0**
> nas três formas (relativo, absoluto, `CLAUDE_PROJECT_DIR` explícito); a
> lista canônica de `scripts/` (`check_canonical_edit.py:189-199`) é
> `install.sh`, `install-npm.sh`, `upgrade.sh`, `_hash_lib.sh`,
> `_framework_manifest_set.sh` — `doctor.sh` não está nela, e o precedente
> `aaf32c7` (D4, S325) já o editou sem sentinel. O `level: L3` do
> frontmatter herdou a premissa errada; a wave real é L2 (1 script + 1 e2e +
> baseline), pair-rail advisory (rodada registrada abaixo). **O que o censo
> "~15 sítios" era de verdade:** 3 CLASSES de destino sob o `$TARGET` —
> (i) restore de regfile (`_restore_file`), (ii) backup pré-overwrite
> (`_backup_file` → `.claude.bak/doctor-<ts>/<rel>`), (iii) re-link de
> registros LINK (2 sítios); o resto do censo mecânico era `>&2`,
> `$WORKDIR`/`$SANITIZED` (temp fora do target) e `_log` — medidos, não
> convertidos, com razão. E o achado de FORMA: `doctor.sh` já tinha um
> `_restore_refuses` LOCAL (walk de symlink + resolução física) — a segunda
> implementação que o PLAN-182 proíbe — aplicado só à classe (i) e **sem a
> cláusula de hardlink** que o predicado compartilhado tem; (ii) e (iii) não
> perguntavam nada.

- [x] `[P1][FU7][scripts/doctor.sh]` Converter os ~15 sitios de escrita ao
      predicado: pre-voo dos destinos antes da primeira escrita, recusa
      NOMEADA (mensagem cita o path e a razao), politica no chamador.
      Check: e2e com symlink pendente plantado em cada classe de destino de
      reparo ⇒ recusa nomeada e ZERO bytes escritos fora do `$TARGET`
      (asserido em bytes, arvore-sombra descartavel — nunca no vivo).
      — ✅ S337: `_restore_refuses` mantém as pernas de FONTE
      (`_wbm_route_relpath_ok` + `_wbm_source_confined`) e delega a metade de
      DESTINO a `_wbm_dst_refuses "$TARGET" "$rel"` (a cópia local saiu);
      `_backup_file` pré-voa `"$BAK_REL_DIR/$rel"` ANTES do `mkdir -p` de
      `_ensure_bak_dir` e passa a devolver rc — os dois chamadores só
      sobrescrevem com backup feito ("sem backup, sem overwrite");
      `_link_dst_refuses` cobre os 2 sítios de `ln -s` (leaf ausente ⇒
      relpath inteiro; leaf presente ⇒ o PAI, porque o leaf de um registro
      LINK é legitimamente um symlink e é substituído por `rm -f`, nunca
      escrito através); `_wbm_dst_refuses` entra na lista `_fms_req` do
      startup (biblioteca sem ele ⇒ exit 2 nomeado); contador `Refused:` no
      summary e `UNRESOLVED` ⇒ exit 1. Mensagens: `RESTORE-BLOCKED
      (destination refused — nothing written: <why>)`, `BACKUP-BLOCKED (…)`.
      E2E: `scripts/tests/test-installer-write-safety-e2e.sh` ganhou a seção
      **D** (D.0 baseline não-vácuo: install limpo é `rc=0` e um drift
      simples É reparado com `BACKED-UP`+`RESTORED`; D.1 hardlink; D.2
      `.claude.bak` symlink + `--dry-run`; D.3 leaf pendente = type-change).
      Pós-cura: **122 passed / 0 failed**. Registros LINK (`--link`): sem
      perna e2e — o sanitizador já derruba ancestral symlinkado no INGEST, e
      sem corrida TOCTOU não há escape pré-cura reprodutível; o predicado ali
      é belt-and-braces, declarado.
- [x] `[P1][FU7]` Controle positivo: o mesmo e2e SEM o predicado (arvore
      pre-cura) reproduz a escrita fora do target — prova que o teste ve o
      defeito (doutrina write-path-tests-need-a-disposable-tree).
      — ✅ S337: o MESMO arquivo apontado para um worktree em `dc72bf1`
      (pré-cura): **112 passed / 10 failed — as 10 são exatamente D.1 (4) +
      D.2 (6)**: «the outside file CHANGED through the hard link
      (dd3be2fa… → 4d0bb564…)», «1 file(s) landed OUTSIDE the target through
      the symlinked .claude.bak», «the file was overwritten WITHOUT a
      backup», «doctor exited 0». D.0 e D.3 verdes nas duas árvores (D.3 já
      era coberto pelo veredito type-change do loop; a perna pina isso).
      Bancada prévia (S337, antes do e2e): D.1 medido à mão no vivo curado —
      vítima com sha idêntico, `Refused: 1`, rc 1.
- [x] `[P2][FU7]` O ratchet `check-installer-write-safety.py` re-baselina no
      MESMO patch (regra do plano-pai: qualquer wave que toque `scripts/`
      regenera o baseline).
      Check: `validate.yml` verde no clone pos-patch sem afrouxar regra.
      — ✅ S337: pré-regen `rc=1` (2 sítios novos `write-candidate
      indeterminado` — as DUAS chamadas `if _wbm_dst_refuses …`, a forma
      «predicado domina» que o FU-1 diz que o censo não modela); `--write-
      baseline` ⇒ 672 entradas; check `rc=0`; diff do baseline só em
      `scripts/doctor.sh` (renumeração + 2 entradas). Regra intacta.
- [x] `[P1][FU7]` ~~Cerimonia GPG de 1 canonico (`scripts/doctor.sh` tem
      oraculo `--is-canonical` = 1)~~ **N/A — oráculo = 0 (medido, ver o
      quadro acima).** O que desse item SOBREVIVE e foi feito: a bateria que
      inclui os oráculos que grepam/extraem `doctor.sh`: `scripts/tests/
      test-doctor.sh` **44/0**; `scripts/tests/test-doctor-delivery-route.sh`
      — a R.7 EXTRAI `_restore_refuses` e a avalia num harness próprio, que
      não carregava o predicado ao qual a função passou a delegar ⇒ «guard
      did not refuse (got WROTE)» (a classe LAND-verde≠CI-verde, prevista
      pelo próprio item); cura no harness pelo padrão que ele mesmo documenta
      (`_wbm_nlink` e `_wbm_dst_refuses` entram na lista de extração;
      `REFUSED_COUNT=0` nos 4 harnesses) — resultado do re-run no registro
      abaixo. Sem sentinel, sem SIGN/LAND: o land é um commit normal do Owner.

## Registro de execução — FU-7 (S337, 2026-09-01)

- **Bateria (todas na árvore viva curada):** `scripts/tests/
  test-installer-write-safety-e2e.sh` **122/0** (pós-cura) vs **112/10**
  contra worktree `dc72bf1` (pré-cura; as 10 = D.1 + D.2); `scripts/tests/
  test-doctor.sh` **44/0**; `scripts/tests/test-doctor-delivery-route.sh`
  **113/0** após o harness R.7 carregar `_wbm_dst_refuses`/`_wbm_nlink` (antes:
  2 FAIL «guard did not refuse (got WROTE)» — o harness, não o guard);
  `check-installer-write-safety.py` rc 0 com baseline regenerado (672
  entradas); `.claude/scripts/tests/test_check_installer_write_safety.py` +
  `test_parity_source_resolution.py` 161 passed; `shellcheck -S warning`
  limpo em `doctor.sh`, `uninstall.sh` e nos dois e2e; `bash -n` limpo.
- **Pair-rail:** rodada Codex r1 sobre o diff não-commitado da sessão (o
  resultado é anexado a esta linha quando a rodada termina — ver memória
  `project-s337-session-state`).
- **Ciclo de vida do plano:** o `status: draft` NÃO foi flipado por mim — a
  metade FU-7 executou sob a autorização de chat do Owner (S337, "vamos agir
  no que dá pra concluir"), a metade FU-1 segue gated na decisão do Owner
  sobre `OQ-W0-STOP`. O Owner decide entre `draft → executing` retroativo
  (FU-1 pendente) ou `superseded`/`done` com FU-1 movido para item nomeado.
- **Lição de forma (paga aqui, vale além):** o plano afirmava um oráculo
  que não mediu (`doctor.sh` = 1) e dimensionou a wave por ele (L3, GPG,
  40-80k). O oráculo custa 1 comando e mudou o custo em uma ordem de
  grandeza — [[feedback-oracle-before-editing-any-path]] agora vale também
  para DIMENSIONAR, não só para editar.

## FU-1 — o censo nao modela «predicado domina»

**Estado honesto:** 3 arquiteturas de regra falharam em 7 levas de rail
(S329, anti-padrao 6 — «forma nao modelada ⇒ fail-open»). O censo vive como
RATCHET fail-closed no `validate.yml` com pontos cegos declarados
(`OQ-W0-STOP`), e a regua do AC-3 do plano-pai ficou registrada como
TROCADA, nao cumprida.

- [x] `[P2][FU1]` **Gatilho: decisao do Owner sobre OQ-W0-STOP** (modelar o
      predicado no censo vs manter o ratchet). Sem a decisao, NADA a
      executar aqui — abrir uma 4a arquitetura de regra sem novo desenho
      repetiria a classe que ja consumiu 7 levas.
      — ✅ S344 (2026-09-04): **DECIDIDA pelo Owner (AskUserQuestion, verbatim):
      «Manter o ratchet e fechar o plano (Recomendado)».** O censo
      `check-installer-write-safety.py` permanece RATCHET fail-closed no
      `validate.yml` com os pontos cegos declarados em `OQ-W0-STOP` do
      plano-pai; a modelagem do predicado «domina» fica registrada como
      LIMITE ACEITO (molde do ADR-190), nao como divida com gatilho. Quem
      tocar `scripts/` regenera o baseline no MESMO patch (regra do PLAN-185).
- [x] `[P2][FU1]` Se o Owner decidir MODELAR: wave de modelagem do
      instrumento com debate proprio (L3), começando pelo desenho — nunca
      pela regra. O criterio de morte da tentativa anterior (fail-open na
      mesma classe em 2 rodadas consecutivas de rail) vale desde a abertura.
      — ✅ S344: NAO se aplica (o Owner decidiu manter o ratchet). O item
      fecha por decisao, sem trabalho; se um dia a modelagem for reaberta,
      e wave NOVA com debate proprio, nao reabertura deste followup.

## Registro de fechamento — S344 (2026-09-04)

- **FU-7:** executado e landado na S337 (`cc00235`, `adb6e84`, `2f71dea`,
  `c0cb915`; bateria e rail no registro acima). Sem cerimonia: o oraculo
  responde 0 para `scripts/doctor.sh`.
- **FU-1:** DECIDIDO pelo Owner (AskUserQuestion, verbatim): «Manter o
  ratchet e fechar o plano (Recomendado)». O censo segue RATCHET fail-closed
  com pontos cegos declarados (`OQ-W0-STOP` no plano-pai); a modelagem do
  predicado «domina» e LIMITE ACEITO, nao divida com gatilho.
- **Ciclo de vida:** `draft → reviewed → executing → done` neste commit, pelo
  Edit tool (o hook `check_plan_edit.py` validou cada transicao); `executing_at`
  retroativo a S337 declarado no frontmatter. Nenhum AC aberto.

## Fronteiras

- Este followup NAO reabre o plano-pai (`status: done` e terminal).
- FU-7 nao espera FU-1: o predicado ja existe e tem 2 consumidores em
  producao; a conversao do 3o e independente da modelagem do censo.
