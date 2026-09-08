# wave-rc1cure — sentinel de aprovação (DRAFT: o SIGN preenche Data / Anchor-SHA / Approved-By e assina)

> Caminho casa `PLAN-*/wave-*-approved.md` (união fechada de padrões em
> `check_canonical_edit.py`). O binding é o `Patch-sha256` — land por PATCH.
> O bloco `Scope:` é **DERIVADO** por `s349-ceremony-rc1cure/bind-patch.sh` a
> partir de `git apply --numstat` sobre o patch congelado, e cruzado com o
> `SCOPE.txt` que o pack declarou: divergência entre o que o autor disse e o
> que o patch toca **aborta o bind**. O `OWNER-RC1-CURE-SIGN.sh` regenera
> escopo e baseline e compara byte a byte **antes** de pedir a assinatura. O
> `Anchor-SHA` é preenchido no momento da assinatura; o
> `OWNER-RC1-CURE-LAND.sh` aborta se o HEAD tiver andado. Reescrever um byte
> deste arquivo depois de assinar invalida o `.asc`.

Plans: PLAN-169
Wave: wave-rc1cure (PLAN-169 — as curas CANÔNICAS dos achados da rodada 1 do re-pass da v1.4.0-rc.1)
Patch: .claude/plans/PLAN-169/s349-ceremony-rc1cure/RC1CURE.patch
Patch-sha256: a9df985c1553b68fd2e3870b8fe7950b965fae537c4f9128c212c3a158de44dd
Patch-base: 538053099b73620c7224b9289543573f39ccbc8c
Anchor-SHA: 538053099b73620c7224b9289543573f39ccbc8c
Data: 2026-09-08
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74

## Por que esta wave existe

A rodada 1 do re-pass da rc.1, sobre o candidato `4a1b448`, voltou **NO-GO em
quatro partes**. As curas que caem em arquivos **livres** já landaram em
`6b3ab79`, sem cerimônia. O que sobra são as curas que tocam caminhos
**canônicos** — e caminho canônico só se move sob assinatura do Owner. É isto
que esta wave carrega, e nada além disso.

O escopo exato está no bloco `Scope:` abaixo, derivado do patch. Os achados que
o originaram estão registrados no re-pass da rodada 1; o pacote de curas e a
sua justificativa item a item estão em `<PK>/rc1-cure/PROPOSED.md` e
`<PK>/rc1-cure/TESTS.md`.

## O que esta cerimônia prova antes de você assinar

Numa cerimônia por **patch** não há derivador para re-executar, então a
pergunta muda. O que os scripts medem, nesta ordem:

1. **O patch aplica em HEAD.** `git apply --check` contra o `Anchor-SHA`.
2. **O patch toca exatamente o escopo assinado.** O escopo é derivado de
   `git apply --numstat` e cruzado com o `SCOPE.txt` declarado pelo pack;
   qualquer diferença aborta o bind, antes de existir material para assinar.
3. **A decomposição por item reproduz o patch inteiro.** O LAND não aplica o
   patch de uma vez: aplica `git apply --include=<path>` por item do escopo,
   para que um hunk destinado a um caminho fora do escopo não entre de carona.
   O `finalize` e o V1 do LAND provam, byte a byte, que essa decomposição
   produz exatamente o patch que você assinou.
4. **Os alvos ainda estão no estado PRÉ-edição.** Os hashes do
   `EXPECTED-BASELINE.txt` são conferidos contra a árvore viva no SIGN e de
   novo no LAND.

## O manifesto ADR-192

Ele entra no escopo **apenas se** o patch tocar algum membro do roster de
gate-scripts. O `bind-patch.sh` verifica isso mecanicamente: se um membro for
tocado e o manifesto **não** estiver no escopo, o bind aborta, porque o gate
`Gate-scripts integrity` do `release.yml` reprovaria o land. Se nenhum membro
for tocado, o manifesto fica de fora — conferir o roster inteiro aqui
reprovaria por drift alheio a esta cerimônia.

## O corte da rc.1 continua em voo

O V-block do LAND roda, sobre a árvore já patchada, os mesmos gates que o corte
vai rodar: a suíte do driver nas duas invocações do preflight, o gate de
frescor dos docs canônicos, `verify-counts`, `validate-governance` completo,
`build-plugin --check`, os claims do `CLAUDE.md`, contaminação, e
`bump --rc 1 --dry-run` exigindo **no-op**. Também confere que `TARGET_BASE` e
`VERSION` continuam concordando — se estas curas os separassem, a janela
vermelha da suíte do driver reabriria.

## Recuperação

Se o LAND abortar depois de aplicar o patch, ele restaura os alvos a partir do
snapshot em bytes que o `finalize` tirou, por escrita Python — `git checkout --`
é recusado sobre caminho canônico, e um `|| true` ali deixaria a árvore suja.
Se abortar **depois** do commit local, o commit fica local e nada foi
empurrado.

Scope:
  - .claude/hooks/_lib/audit_emit.py
  - .claude/hooks/_lib/injection_salt.py
  - .claude/hooks/check_postcompact_reinject.py
  - .claude/hooks/check_precompact_continuity.py
  - .claude/hooks/tests/test_check_compaction_continuity.py
  - .claude/hooks/tests/test_injection_salt.py
  - .claude/hooks/tests/test_postcompact_reinject_no_exec_payload.py
  - .claude/scripts/data/installer-write-safety-baseline.txt
  - .github/workflows/validate.yml
  - SPEC/v1/audit-log.schema.md
  - scripts/_framework_manifest_set.sh
  - scripts/install.sh
  - scripts/tests/test-installer-write-safety-e2e.sh
  - scripts/tests/test-manifest-delivery-route.sh
  - scripts/tests/test-upgrade-historical-adopter.sh
  - scripts/upgrade.sh
