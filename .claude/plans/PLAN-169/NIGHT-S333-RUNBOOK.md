# NIGHT-S333 — runbook da madrugada de 2026-08-30/31

> Sessão autônoma iniciada ~22:20 -03, Owner volta ~07:00. Escopo ratificado
> ANTES da saída (AskUserQuestion, verbatim): **«A+B»** e **«Aguardar reset»**.

## As duas decisões do Owner

1. **Escopo = A + B**, dois pacotes de cerimônia com destinos DISJUNTOS:
   * **A — wave-adrgate** (FU-F-ADRGATE): os 9 ADRs sem `Status:` ganham o
     campo, ADR-111 vira `SUPERSEDED`, `check-adr-chain.py` passa a sair 0, e
     os DOIS geradores (`check-adr-chain.py` + `generate-adr-index.py --check`)
     entram no `validate.yml` — hoje não rodam em lugar nenhum.
   * **B — PLAN-185-FOLLOWUP (FU-7)**: `scripts/doctor.sh` vira o 3º consumidor
     de `_wbm_dst_refuses` (molde do pacote E; ADR-196 já o nomeia).
2. **Quota**: aguardar o reset na mesma conta. Cron horário retoma a sessão.

## Bloco 0 (não estava no plano; entrou porque o main ficou VERMELHO)

O `Smoke Install` de `303ae55` (o land da wave-F) reprovou com **FATAL [STALE]**
em `.claude/adr/README.md`, nos dois modos.

**Causa medida:** `install.sh` semeia esse arquivo por um `install_adr_template`
pontual (`:1656`), FORA do walk do manifesto — e `.claude/adr` **não consta de
`_framework_target_entries`** (`scripts/_framework_manifest_set.sh`), ou seja, a
árvore nunca esteve no conjunto que o upgrade considera seu. O adopter é dono do
diretório (`install.sh:2804` nomeia `.claude/adr/ADR-*.md` como «user's own
ADRs»). É a mesma família preserve-contract de `CLAUDE.md` / `MEMORY.md`, que já
tem declaração no classificador.

Ficou invisível até agora porque o CONTEÚDO do seed não mudava desde a v1.2.0; o
land da wave-F regenerou o índice embutido (170 → 198 linhas) e o classificador
viu a primeira diferença real.

**Cura (caminho LIVRE — `_parity_classify.py` responde 0 ao oráculo):** entrada
`ACCEPTED` com a autoridade ESTRUTURAL acima. Não é encolher de ombros: o
`KNOWN_OPEN` foi considerado e REJEITADO porque o próprio driver declara que
exit 2 «is a FAILURE, not a skip» — não deixaria o main verde, e a divergência
aqui não é um bug em aberto, é o contrato de seed-once.

**Follow-up NOMEADO na própria declaração — `FU-ADR-README-SEED`:** o seed
carrega o índice dos 198 ADRs do FRAMEWORK para dentro da árvore do adopter
(família A7 de contaminação). A cura é canônica (`install.sh` + um template sem
índice) e é decisão de produto do Owner. Fora do escopo desta noite.

## Trilhos desta noite (herdados, não re-descobertos)

* **Molde de cerimônia = o da wave-F**, recém-validado ponta a ponta: sombra →
  rail até APPROVE → registro por rodada → EXPECTED re-medido → commit no vivo →
  rebase da sombra → finalize → **harness** → os 3 comandos do Owner.
* **Nunca assinar.** GPG é do Owner. O SIGN recusa sem `Rail-Verdict: APPROVE`.
* **Rodada limpa prova a SUPERFÍCIE revisada, não o entregável** — sombra
  re-derivada ganha rail inteiro.
* **Materiais curados no vivo são INVISÍVEIS à sombra** (lição da r8 desta
  wave): commitar no vivo e rebasear a sombra ANTES da rodada seguinte.
* **`Rail-Verdict:` nua** — o parser do SIGN normaliza espaços e exige igualdade
  exata com `APPROVE`; qualquer qualificação na mesma linha vira recusa.
* **Bateria depois da última edição**, `git add -A` → gates de corpus → commit.
* **Caso de ESCRITA roda em árvore descartável** (a r3 corrompeu o artefato
  shipado quando o controle vermelho rodou contra o repo real).
* **Repro destrutivo só com path RESOLVIDO** (`cd "$dir" || exit`), nunca glob —
  a S332 pagou isso com um commit espúrio na árvore viva.

## Estado ao início

`303ae55` (wave-s330-F landada, assinada pelo Owner) + Bloco 0 em curso.
`Validate` verde; `Smoke Install` vermelho SÓ pelo Bloco 0.
