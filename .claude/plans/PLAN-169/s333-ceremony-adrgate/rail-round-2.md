# wave-adrgate — rail codex rodada 2 (sombra curada da r1, 2026-08-31 ~04:4x -03)

Rail-Verdict: CHANGES-REQUESTED (0 P1, 4 P2 — todos REAIS, todos a MESMA
classe, curados por troca de arquitetura e não ramo a ramo)

Comando: `codex exec review --uncommitted --skip-git-repo-check -c sandbox_mode="workspace-write"`,
via `rail_round.sh`. Substrato: codex-cli 0.147.0. Saída bruta:
`<scratchpad 889bc1bd>/adrgate-r2.txt`. Wrapper: **TREE INTACT**.

## A classe: a isenção era mais FROUXA do que a semântica que ela declara

Os quatro achados são a mesma forma — cada um é um caminho pelo qual a isenção
que a r1 shipou concede o waiver a algo que ela não pretendia cobrir. Por isso
a cura não foi remendar quatro ramos (anti-padrão S296), e sim **estreitar a
gramática e a origem** dos qualificadores.

### [P2-a] Qualificador lido do documento INTEIRO

`original_id`, `amended_by` e `rename_source` eram buscados no texto todo,
então um **exemplo cercado** no corpo virava declaração real: um ADR que
apenas MOSTRA `original_id: ADR-111` num bloco ```yaml``` concedia a si mesmo
o waiver. **Cura:** os três passam a ser lidos **somente do bloco de
frontmatter** (`_FM_FENCE_RE`, o mesmo delimitador que `_extract_yaml_supersedes`
já usava). São chaves de metadado — nunca prosa.

### [P2-b] `amended_by` perdia o sufixo AMEND

`ADR_ID_RE` trunca `ADR-019-AMEND-2` para `ADR-019`, e o corpus indexa
registros AMEND pelo **stem completo**. O waiver destinado ao AMEND-2 pousava
no ADR-019 BASE, e o declarante real nunca conseguia reivindicá-lo. **Cura:**
`_AMEND_STEM_RE` preserva o stem (`ADR-\d{3}(?:-AMEND-\d+)?`).

### [P2-c] Slug de rename com `.md`, e prefixo sem fronteira

Escrito `rename_source: ADR-111-old.md`, o teste de prefixo passava mas a
sonda de existência procurava `ADR-111-old.md.md` — o arquivo **sobrevivente
era perdido** e o waiver concedido. E `startswith` aceitava `ADR-1110` como
evidência para `ADR-111`. **Cura:** o slug é normalizado uma vez (sufixo `.md`
removido) para que id-test e sonda não possam discordar, e o id tem de terminar
em **fronteira** (igual, ou seguido de `-`).

### [P2-d] Bullet sem espaço, e o `*` solto que o `\**` engolia

`-status: ACCEPTED`, `---status:` e `*status:` eram lidos como status válido —
e o gerador de índice rejeita as mesmas linhas, então depois de regenerar o
README **os dois gates recém-ligados aprovariam entrada malformada**. **Cura
em duas pernas:** o bullet exige espaço (`(?:[-*][\t ]+)?`) e o marcador
**bold** passa a ser exatamente dois asteriscos (`(?:\*\*)?`). A segunda perna
só apareceu na medição: com o bullet corrigido, `*status:` **continuava
passando**, porque o quantificador `\**` do bold absorvia alegremente o
asterisco que a classe acabara de recusar.

## Achado de gate que veio junto (não do revisor)

A bateria acusou **`verify-counts.sh` rc 1**: os testes novos empurraram a
contagem viva de 15.461 para 15.480, e a citação `~14.700` — que na árvore
viva estava dentro da banda ±5% **por 13 testes de margem** — saiu dela.
Medido nos dois lados (árvore viva: «no drift detected»), portanto é efeito
DESTE pacote e não dívida herdada. Atualizadas **15 citações em 9 arquivos**,
em quatro grafias diferentes (`14,700`, `14.700` no pt-BR, `~14.7k` em prosa e
na tabela do `ARCHITECTURE`), porque o gate também exige **igualdade
cross-doc**. `verify-counts` volta a **rc 0**.

## Medições após a disposição

`check-adr-chain.py` rc **0**; `generate-adr-index.py --check` rc **0**;
`test_check_adr_chain.py` **45 → 51** casos; censo de status: 0 ADRs sem
status antes e depois da cura (a classe fechou sem mover mais nada);
`verify-counts.sh` rc **0**; `check-claude-md-claims.py` rc **0**;
`CLAUDE.md` 39.944 B (teto 40.000).

## Disposição

CHANGES-REQUESTED. Curas aplicadas na sombra; a rodada 3 revisa o conjunto,
agora incluindo as citações.
