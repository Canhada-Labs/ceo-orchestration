# wave-rc1cure3 — sentinel de aprovação (DRAFT: o SIGN preenche Data / Anchor-SHA / Approved-By e assina)

> Caminho casa `PLAN-*/wave-*-approved.md` (união fechada de padrões em
> `check_canonical_edit.py`). O binding é o `Patch-sha256` — land por PATCH.
> O bloco `Scope:` é **DERIVADO** por `s349-ceremony-rc1cure3/bind-patch.sh` a
> partir de `git apply --numstat` sobre o patch congelado, e cruzado com o
> `SCOPE.txt` que o pack declarou: divergência entre o que o autor disse e o
> que o patch toca **aborta o bind**. O `OWNER-RC1-CURE3-SIGN.sh` regenera
> escopo e baseline e compara byte a byte **antes** de pedir a assinatura. O
> `Anchor-SHA` é preenchido no momento da assinatura; o
> `OWNER-RC1-CURE3-LAND.sh` aborta se o HEAD tiver andado. Reescrever um byte
> deste arquivo depois de assinar invalida o `.asc`.

Plans: PLAN-169
Wave: wave-rc1cure3 (PLAN-169 — as curas CANÔNICAS dos P1 das rodadas 11 e 12 do re-pass da v1.4.0-rc.1, pacote do Codex revisado)
Patch: .claude/plans/PLAN-169/s349-ceremony-rc1cure3/RC1CURE3.patch
Patch-sha256: TO-FILL-BY-FINALIZE
Patch-base: TO-FILL-BY-FINALIZE
Anchor-SHA: TO-FILL-BY-SIGN
Data: TO-FILL-BY-SIGN
Approved-By: TO-FILL-BY-SIGN

## Por que esta wave existe

As rodadas 11 e 12 do re-pass da rc.1 acharam **P1 de código** em caminhos
canônicos: um ancestral NÃO-diretório (`docs`, `.github/workflows`, `SPEC`
como arquivo regular) passava o predicado de confinamento do instalador e do
upgrader e o `mkdir -p` sem guarda abortava a execução a meio, sem manifesto
nem banner; o índice de planos do PreCompact abria `PLAN-NNN-*.md` seguindo
symlink e podia eleger um plano a partir de bytes externos; e três módulos de
auditoria carregavam comentários falsos (contagem de `getenv`, «slug/path
never reaches the log», garantia de coleta do GC, série durável do ledger).
As curas tocam caminhos **canônicos**, e caminho canônico só se move sob
assinatura do Owner. É isto que esta wave carrega, e nada além disso.

O escopo exato está no bloco `Scope:` abaixo, derivado do patch. O pacote foi
escrito pelo Codex (autoria de outro fornecedor) sobre `7f7cda0`, revisado por
três leitores independentes e pelo Fable, e corrigido antes desta cerimônia
(`SPEC/v1` nos dois scripts, `--dry-run` diagnóstico, ancestral do leitor de
`LEDGER.md`, frases absolutas). Uma revisão read-only do Codex sobre os bytes
FINAIS (09/09 21:34, NO-GO: 2 P1 + 2 P2, todos verificados no código e um deles
reproduzido pelo e2e histórico) foi absorvida na versão 3 do patch — ancestral
symlink que não resolve para diretório recusado na preflight dos dois scripts;
tabela de rotas inutilizável delegada ao gate de entrega, que persiste
`upgrade_succeeded: false`; dois limites declarados no item 60 do envelope;
HOME isolado no kit — e a segunda passagem do Codex sobre a v3 devolveu
`NO-GO: 1 P1 (baseline do censo, regenerado no proprio pack) + 2 P2 de texto, absorvidos na v4`; a versão 4 (a deste patch) absorve os dois P2 de texto dessa
passagem (47: um `SPEC` symlink→diretório não é escrito através; 18: os
ancestrais de `LEDGER.md` ficam curados). A revisão do Fable está em
`<PK>/rc1-scratch-s348/REVIEW-FABLE-20260909.md` (o diretório temporário do
pacote original não sobreviveu ao reboot de 09/09); os achados que o
originaram estão em `repass-rc1-20260908-NOGO/r11` e `r12`, e a trilha das
emendas em `repass-rc1/CONDITIONS-history.md` (v53 e v54).

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
TO-FILL-BY-FINALIZE
