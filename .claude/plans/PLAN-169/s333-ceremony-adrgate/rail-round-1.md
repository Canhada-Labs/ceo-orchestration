# wave-adrgate — rail codex rodada 1 (sombra sobre `48b76b1`, 2026-08-31 ~04:0x -03)

Rail-Verdict: CHANGES-REQUESTED (0 P1, 3 P2 — os três REAIS, todos curados
nesta disposição com controle vermelho)

Comando: `codex exec review --uncommitted --skip-git-repo-check -c sandbox_mode="workspace-write"`,
via `rail_round.sh` (snapshot sha256 de cada path staged antes/depois).
Substrato: codex-cli 0.147.0. Saída bruta: `<scratchpad 889bc1bd>/adrgate-r1.txt`.
Wrapper: **TREE INTACT**.

## [P2-a] O skip de rename aceitava a AFIRMAÇÃO sem a evidência — REAL, curado

`_rename_completed` retornava `True` quando o declarante dizia
`original_id: <alvo>` e **não nomeava nenhum** `rename_source:` — o laço
executava zero vezes e caía no `return True`. Um registro poderia então
declarar `original_id` e aposentar um alvo VIVO sem que o gate recém-ligado
dissesse nada.

Eu tinha visto essa borda ao desenhar e a julguei aceitável («`original_id ==
alvo` já significa que sou o mesmo registro»). O revisor está certo e eu
estava errado: a semântica é «sou aquele arquivo, renomeado», e um registro
que não diz **qual** arquivo era não mostrou isso.

**Cura:** pelo menos um `rename_source:` declarado tem de NOMEAR o id do alvo
(`startswith(target_id)`), e nenhum dos slugs declarados pode existir no disco.
As duas pernas continuam necessárias. Testes:
`test_original_id_without_naming_a_rename_source_keeps_the_edge` e
`test_a_rename_source_for_a_DIFFERENT_id_does_not_evidence_this_one`.

## [P2-b] REGRESSÃO INTRODUZIDA PELA PRÓPRIA CURA — REAL, curada

O achado mais valioso da rodada. `\s` casa `\n`. Com `-` na classe de
início-de-linha, um frontmatter na forma

```
---
status: SUPERSEDED by ADR-002
---
```

fazia o match ancorar na **cerca `---`** e engolir a quebra de linha. A
varredura de sucessor inline do `parse_adr` lê **apenas a linha onde o match
começa** — passava a ler `---`, não achava referência de ADR, e a forma
`status: SUPERSEDED by ADR-NNN` (que o parser suportava antes) era perdida em
silêncio.

**Cura:** as classes viram **horizontal-only** (`[-*#\t ]`, nunca `\s`) nos
quatro regexes que a wave toca, com a razão registrada no comentário do
módulo. Teste:
`test_frontmatter_inline_successor_survives_the_widened_anchor`.

**Lição de método:** alargar uma âncora de regex é mudança de FRONTEIRA, e
`\s` cruza linhas. O censo antes/depois que eu rodei mediu o efeito PRETENDIDO
(9 statuses aparecem) e teria passado batido pelo efeito colateral, porque
nenhum dos 198 ADRs usa a forma que quebrou — a fixture do revisor usava.

## [P2-c] Afirmação de velocidade no workflow — REAL, curada

O comentário do step novo dizia «sub-second». O contrato do repositório proíbe
claim de velocidade (a §1 do `CLAUDE.md` mantém deliberadamente «there is no
speed claim»). Trocado por uma propriedade não-temporal: sem fixtures e sem
rede, portanto sem segredo de runner nem service container.

## Medições após a disposição

`check-adr-chain.py` rc **0**; `generate-adr-index.py --check` rc **0**;
`test_check_adr_chain.py` **32 → 45** casos; controles vermelhos **4/4**
disparando; controle vermelho ADICIONAL desta rodada (reverter as duas curas
de código num clone) reproduz **exatamente 3 falhas**, uma por cura.

## Disposição

CHANGES-REQUESTED. Curas aplicadas na sombra; a rodada 2 revisa o conjunto.
