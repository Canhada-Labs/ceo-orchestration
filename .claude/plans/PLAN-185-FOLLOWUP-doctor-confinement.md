---
id: PLAN-185-FOLLOWUP
title: "Residuais do installer-write-safety: doctor.sh como 3o consumidor do predicado (FU-7) e a modelagem do censo (FU-1)"
status: draft
created: 2026-08-31
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

- [ ] `[P1][FU7][scripts/doctor.sh]` Converter os ~15 sitios de escrita ao
      predicado: pre-voo dos destinos antes da primeira escrita, recusa
      NOMEADA (mensagem cita o path e a razao), politica no chamador.
      Check: e2e com symlink pendente plantado em cada classe de destino de
      reparo ⇒ recusa nomeada e ZERO bytes escritos fora do `$TARGET`
      (asserido em bytes, arvore-sombra descartavel — nunca no vivo).
- [ ] `[P1][FU7]` Controle positivo: o mesmo e2e SEM o predicado (arvore
      pre-cura) reproduz a escrita fora do target — prova que o teste ve o
      defeito (doutrina write-path-tests-need-a-disposable-tree).
- [ ] `[P2][FU7]` O ratchet `check-installer-write-safety.py` re-baselina no
      MESMO patch (regra do plano-pai: qualquer wave que toque `scripts/`
      regenera o baseline).
      Check: `validate.yml` verde no clone pos-patch sem afrouxar regra.
- [ ] `[P1][FU7]` Cerimonia GPG de 1 canonico (`scripts/doctor.sh` tem
      oraculo `--is-canonical` = 1): sentinel + SIGN/LAND no molde F, com
      gate `touched − scope = ∅` e bateria que inclui os steps do Smoke
      Install que grepam `doctor.sh` (licao LAND-verde≠CI-verde).

## FU-1 — o censo nao modela «predicado domina»

**Estado honesto:** 3 arquiteturas de regra falharam em 7 levas de rail
(S329, anti-padrao 6 — «forma nao modelada ⇒ fail-open»). O censo vive como
RATCHET fail-closed no `validate.yml` com pontos cegos declarados
(`OQ-W0-STOP`), e a regua do AC-3 do plano-pai ficou registrada como
TROCADA, nao cumprida.

- [ ] `[P2][FU1]` **Gatilho: decisao do Owner sobre OQ-W0-STOP** (modelar o
      predicado no censo vs manter o ratchet). Sem a decisao, NADA a
      executar aqui — abrir uma 4a arquitetura de regra sem novo desenho
      repetiria a classe que ja consumiu 7 levas.
- [ ] `[P2][FU1]` Se o Owner decidir MODELAR: wave de modelagem do
      instrumento com debate proprio (L3), começando pelo desenho — nunca
      pela regra. O criterio de morte da tentativa anterior (fail-open na
      mesma classe em 2 rodadas consecutivas de rail) vale desde a abertura.

## Fronteiras

- Este followup NAO reabre o plano-pai (`status: done` e terminal).
- FU-7 nao espera FU-1: o predicado ja existe e tem 2 consumidores em
  producao; a conversao do 3o e independente da modelagem do censo.
