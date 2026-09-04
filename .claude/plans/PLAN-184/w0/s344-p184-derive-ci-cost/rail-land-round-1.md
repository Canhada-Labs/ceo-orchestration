Rail-Verdict: CHANGES-REQUESTED (1 P1 — no pack DROPADO; os 2 packs que landam ficam com 3 P2 declarados)

# Pair-rail do land combinado S344 — rodada 1, DUAS lanes em paralelo

Árvore revisada: diff não-commitado do repositório sobre a base `faec31f`,
contendo a UNIÃO dos três packs (`ac1-close` → `p184-derive-ci-cost` →
`contamination-gate-v3`), aplicados nessa ordem pelos derivadores.

Lanes (as duas com `model_reasoning_effort=max`):

| lane | invocação | resultado |
|---|---|---|
| A — review | `codex exec review --uncommitted --skip-git-repo-check` | 1 P1 + 2 P2, TODOS em `check_contamination.py` |
| B — texto | `codex exec --sandbox read-only` com briefing dos 3 packs | 6 achados: 4 no pack de contaminação, 1 no `ac1-close`, 2 no `p184` |

## O P1 — e por que ele DROPA o `contamination-gate-v3`

**[P1, lane A + lane B, confirmado por mim em disco] Exceção por NOME de
arquivo continua sendo um bypass de uma linha.** `is_personal_path_exempt()`
isenta qualquer basename `OWNER-*.sh` antes de qualquer leitura do conteúdo,
então um symlink RASTREADO cujo alvo é um home path real nunca tem o payload
lido.

Reprodução minha, numa árvore descartável (não a viva), com o módulo exato da
árvore aplicada e dois symlinks IDÊNTICOS que diferem apenas no nome:

```
docs/OWNER-leak.sh -> /Users/<owner>/repo     ->  NENHUM hit
docs/plain-leak.md -> /Users/<owner>/repo     ->  hit (linha 1)
exempt("docs/OWNER-leak.sh") = True
```

Esta é a MESMA classe que bloqueou a v2 no land da S343 (`.asc` isento por
sufixo, F4/G1) e que o próprio pack declara ter fechado «por REMOÇÃO, não por
enumeração». O rail voltou a achá-la na mesma função, na 3.ª versão do pack.
Curar aqui não é uma linha: a semântica da isenção `OWNER-*.sh` está escrita
no cabeçalho do módulo, no cabeçalho da allowlist, no texto de remediação e
nos testes que o pack shipa — uma cura coerente é troca de ARQUITETURA da
isenção, que é trabalho de WAVE, não de lander. Decisão: **pack DROPADO**,
paths restaurados, `LANDER-BLOCKED-S344.json` escrito. Isto confirma a lição
já registrada na S343: contamination-gate é wave.

Os outros três achados do pack dropado (não curados, registrados para quem
re-derivar): `allow_abbrev` do argparse aceita `--emit-personal-path-row` como
prefixo e entra em modo não-gating [P2]; `_PERSONAL_PATH_HOME_RE` exige UMA
barra, logo `/Users//<owner>/repo` passa [P2, reproduzido: `False` contra
`True` na forma de uma barra]; uma linha de allowlist isenta o arquivo INTEIRO
para sempre, não a linha [P2].

## Residuais DECLARADOS dos dois packs que LANDAM

Cada um verificado por mim em disco antes de ser classificado.

1. **[P2 — `ac1-close`] Janela fechada de largura zero é recusada.** Lane B:
   «Filtering is inclusive at `ceo-cost-transcripts.py:775` … Nevertheless
   `ceo-cost-transcripts.py:1461` rejects equality as necessarily empty».
   Verificado: é DELIBERADO — a recusa nomeada rc 2 para «limite superior não
   ESTRITAMENTE posterior ao inferior» está no texto do plano, nos testes que
   o pack shipa e nos residuais declarados do builder. Escolha de desenho
   registrada, não fato errado. Não bloqueia.

2. **[P2 — `p184`] A linha de MÉTODO da derivação omite o predecessor.**
   Lane B: «167 heads … supplies only 166 intervals; the first push's `before`
   SHA is absent». **A aritmética está REFUTADA**: o instrumento parte de um
   `PRED_HEAD` explícito antes do primeiro head (`derive.py:185`,
   `derive2.py:131`), logo há 167 intervalos e os «21 de 167» / «48 de 167»
   do documento estão certos. O que procede é MENOS: a linha 16 do
   `w0-derivation-S344.md` descreve o método como `head[i-1] head[i]` sem
   citar o `PRED_HEAD`. Imprecisão de redação num documento de derivação.

3. **[P2 — `p184`] Subseção antiga não marcada como substituída.** Lane B
   aponta a contradição entre `US$ 1,578/dia` + `US$ 3,74` (parágrafo novo) e
   `US$ 0,52/dia` + `US$ 19` (subseção «Ressalva de composição», pré-existente
   e não tocada pelo pack). Verificado em disco: procede — a subseção fica sem
   marcador. Mitigação verificada: o parágrafo NOVO, dois parágrafos acima,
   nomeia e substitui explicitamente o número velho («é US$ 3,74 … e não os
   US$ 19 estimados»), e o pack já substitui de forma explícita os antigos
   `US$ 9,24/dia` e `US$ 7,26/dia`. Número velho carimbado como superado pelo
   texto adjacente, não silenciosamente contradito.

Lane B também repete o P1 do pack de contaminação e a crítica de que os
scripts de derivação do `p184` ficam FORA do repositório — o que o próprio
documento declara na sua §5, e é a mesma política dos packs anteriores
(instrumento de medição da sessão, não código do repo).

## Nota de método, para não superestimar esta rodada

Após o drop, o diff que vai ao commit é um SUBCONJUNTO ESTRITO do que estas
duas lanes revisaram — nenhum byte novo entrou depois da revisão a não ser a
escrituração de plano (linhas de progress log + `related_commits` derivados do
git). Uma rodada limpa é claim, não prova; esta nem limpa foi.
