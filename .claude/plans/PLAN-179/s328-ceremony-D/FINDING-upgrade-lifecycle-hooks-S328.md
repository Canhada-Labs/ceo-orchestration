# Achado de campo (S328, rail codex rodada 3 do pacote D) — o upgrade não registra hooks novos no adopter

> Registrado pelo CEO em 2026-08-26 01:10 a partir do relatório do agente
> `d2-pack-w24-ceremony-builder` (rail codex, P1). Verificado no disco:
> `scripts/upgrade.sh:2497` define `_merge_lifecycle_hooks_into_settings()`
> e `:3434` a chama. Arquivo CANÔNICO — fora do pacote D e fora do escopo
> da noite. Wave própria a abrir.

## O que foi medido

`_merge_lifecycle_hooks_into_settings` preserva o `settings.json` do
adopter e **hard-codeia SEIS hooks de ciclo de vida** para o merge. Não há
entrada para `check_ledger_checkpoint.py` (o hook que o pack `staged-w24`
registra em `.claude/settings.json` e no espelho
`templates/settings/settings.base.json`).

Consequência: o adopter que faz **upgrade** recebe o SCRIPT do hook e
**não** recebe a registração — o hook fica sem fio e a telemetria de
checkpoint nunca roda nesse adopter. Instalações NOVAS ficam corretas (o
espelho do template cobre), e por isso o `test_template_dogfood_parity`
não vê nada: ele compara dogfood ↔ template, não dogfood ↔ resultado de um
upgrade.

## Por que é a mesma FORMA que o PLAN-183 passou cinco sessões curando

A entrega ao adopter não acompanha o que o dogfood ganha: uma lista
LITERAL em `upgrade.sh` é a segunda declaração de uma verdade que já vive
no template. A cura certa não é acrescentar a sétima entrada — é fazer a
lista DERIVAR do template (um dado com leitores, como
`scripts/delivery-routes.tsv` fez com as rotas), com um teste que falhe
quando um hook entrar no template e não no merge.

## Efeito hoje

O pacote D é ADVISORY por construção (o hook não tem braço de deny): o
efeito é telemetria ausente em adopters que fazem upgrade, não quebra.
Não impede o land do pack; impede que a W2 do PLAN-179 seja declarada
entregue "em campo".

## Disposição

- Wave própria (sugestão: PLAN-179 W2.x "merge de hooks derivado do
  template"), canônica (`scripts/upgrade.sh`), com cerimônia.
- Até lá: registrar no `README-D.md` como residual conhecido do land de D,
  e no PLAN-179 na próxima edição do plano.
