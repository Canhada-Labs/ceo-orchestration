Rail-Verdict: CHANGES-REQUESTED (2 P1 reais, 2 P2 — lane de TEXTO; lane de MECANISMO APPROVE)

# Rail do LAND — rodada 1 — pacote `p188-plan-draft` (noite S347, land combinado)

**Regra de parada PRÉ-REGISTRADA (escrita ANTES de ler qualquer saída).**
Um P1 NOVO dentro dos paths do pacote ⇒ cura + UMA rodada (cap). Achado de
redação, fora dos paths declarados, ou já nomeado como residual ⇒ residual
DECLARADO com o texto do codex citado e a verificação em disco ao lado.
Nunca re-rotular um P1; nunca APPROVE sobre rodada incompleta.

## Sujeito

`git diff` não-commitado da árvore VIVA, exatamente 4 paths:

```
M  .claude/plans/PLAN-186-orchestrator-operating-model.md
A  .claude/plans/PLAN-188-shared-ceremony-toolkit.md
A  .claude/plans/PLAN-188/measure-rail-classes-v2.py
A  .claude/plans/PLAN-188/s345-rail-classes.txt
```

## Liveness das DUAS lanes (round completo antes de qualquer leitura)

| lane | modelo | esforço | terminação própria | `lsof` no fim |
|---|---|---|---|---|
| mecanismo (`review --uncommitted`) | `gpt-6-astra` | max | bloco `codex / APPROVE.` | sem escritor |
| texto (brief no stdin) | `gpt-6-astra` | max | `tokens used 108.127` | sem escritor |

Nenhuma das duas saídas contém `Selected model is at capacity`, `Review was
interrupted`, `Terminated` ou `usage limit` emitidos pelo CLI. A única
ocorrência dessas cadeias na saída de mecanismo é conteúdo do REPOSITÓRIO
citado (linha do próprio rascunho que descreve marcadores de rodada morta),
não status do CLI.

## Lane de MECANISMO — `APPROVE`

> «APPROVE. No actionable regressions found beyond the classifier limitations
> explicitly preserved for debate. Read-only plan validation and Python 3.9
> compatibility checks passed.»

Sem bloco `Full review comments:` próprio. A lane executou por conta própria os
cinco checks de plano do validador rápido (erros `[]`) e um `ast.parse` com
`feature_version=(3, 9)` sobre o instrumento.

## Lane de TEXTO — `REJECT`, 2 P1 + 2 P2

### P1-1 — contradição de tempo verbal sobre a contagem de registros — **CURADO**

> «**P1 — Contradictory round-count history.** PLAN-188:86 says existing record
> counts are below the maximum indices, but line 53 says w6's missing records
> were restored and its set is now complete. Date the incomplete-count
> statement explicitly.»

VERIFICADO em disco: a linha 86 afirmava no PRESENTE «a contagem de registros
existentes é menor», enquanto a nota da tabela (linhas 52-53) diz que os dois
registros ausentes foram escritos depois e que HOJE o conjunto está completo.
Contradição REAL dentro do arquivo entregue.

CURA pelo DERIVADOR (`_cure_r11_index_tense.py`, âncora-exata, contagem de
ocorrências exigida == 1, segunda aplicação RECUSA — rc 1 provado): a
afirmação passa a ser DATADA («NO INSTANTE MEDIDO da noite S345 … o conjunto
daquele pacote está completo HOJE: o que estas cifras medem é o instante, não o
estado atual»). É exatamente a cura que o revisor prescreveu. Payload
re-derivado: `PLAN-188-shared-ceremony-toolkit.md` 14289 → 14538 bytes,
sha256 `20c1d65e…`; os outros dois paths permanecem byte-idênticos.

A segunda metade do mesmo item — «the frozen output also does not establish the
historical maxima 12/11; the published `ls … | wc -l` command counts files, not
maximum indices» — é o residual JÁ DECLARADO em `rail-round-3.md` §1 do pacote
e permanece declarado: o comando de contagem está publicado ao lado do número,
como o próprio texto do plano manda.

### P1-2 — evidência de rail do land citada e ausente — **CURADO**

> «**P1 — Claimed land-review evidence is missing.** PLAN-186:307 says the land
> review is recorded under `.claude/plans/PLAN-188/s345-p188-plan-draft/`. That
> directory does not exist and is absent from the staged change.»

VERIFICADO: no instante da rodada o diretório de fato não existia — a linha de
Progress-log do PLAN-186 foi escrita ANTES do registro que ela cita
(auto-referência inerente ao passo de rail do land). CURA: este arquivo. Com
ele o diretório existe, está no conjunto staged e a afirmação do PLAN-186 é
verdadeira nos bytes commitados.

### P2-1 — segundo path inexistente sem rótulo FUTURE — residual DECLARADO

> «**P2 — A second nonexistent path needs a future/example label.** The concrete
> sentinel path at PLAN-188:109 does not exist. Its example context makes this a
> documentation issue, but the claim that only `.claude/scripts/ceremony/` is
> future is incorrect.»

VERIFICADO: a linha 109 está DENTRO do bloco cercado que ilustra o manifesto
`ceremony.toml` de uma wave futura (W6a) — o mesmo bloco traz
`paths = [".claude/hooks/_lib/adapters/live/claude.py", "..."]` com reticências
literais como placeholder. É um EXEMPLO, e o revisor o classifica como questão
de documentação. Fica DECLARADO: o inventário do `cite-check.py` marca um único
`FUTURE` (`.claude/scripts/ceremony/`) e não modela paths dentro de blocos de
exemplo. Item para o `/debate start PLAN-188`.

### P2-2 — OQ-5(iv) cita a linha vizinha — residual DECLARADO

> «**P2 — OQ-5(iv) cites the wrong location.** PLAN-188:212 cites instrument
> lines 126–129. The finding-dependent creation of `per_pack` entries occurs at
> **line 136**. The described behavior reproduces correctly.»

VERIFICADO em disco: `:126-129` é o laço que decide QUAIS blocos entram na
contagem; a inserção em `per_pack` que faz um pacote sem achado sumir do
relatório está em `:136` (`total[cls] += 1; per_pack[pack][cls] += 1; …`). A
citação aponta a vizinhança correta e o COMPORTAMENTO descrito reproduz — o
próprio revisor confirma. O instrumento viaja CONGELADO por ser o snapshot que
produziu a saída citada, então a cura seria na divulgação; fica DECLARADO para
o debate junto com os outros cinco limites da OQ-5.

## O que a lane de texto CONFIRMOU

Aritmética dos totais congelados e por pacote; percentuais arredondados
corretamente; atribuição das cinco chaves de orçamento (ADR-081 × PLAN-180);
os SEIS comportamentos do classificador da OQ-5; imports stdlib e sintaxe
compatível com Python 3.9; recusa nomeada rc 1 sem diretório; oráculo canônico
`0` nos três paths; frontmatter obrigatória e id único; nenhum path pessoal ou
handle do mantenedor introduzido; e que **os 22 commits com PLAN-186 no assunto
estão todos listados, incluindo `184a1a2`**.

## Limite declarado da própria rodada

A lane de texto observa que o rascunho ORIGINAL do CEO e os geradores do pacote
ficam FORA deste checkout, então ela não pôde verificar por conta própria a
preservação verbatim das 7 linhas de classe e dos 9 invariantes. Essa perna é
sustentada pelo instrumento do pacote (`gen-baseline.py`: `VERBATIM OK` +
`BUDGET KEYS OK … (5 chaves)`), reproduzido nesta bateria, e pelo refutador
(6.ª refutação, `refuted=false`), que a reproduziu READ-ONLY em processo
(sha256 `960fd773…`, 6517 B, byte-idêntico ao original arquivado).

## Próximo passo

Rodada 2 de CONFIRMAÇÃO sobre os bytes FINAIS (payload curado + este registro),
`review --uncommitted` cujo diff é exatamente os paths landados — classe
S345-d. Registro em `rail-land-round-2.md`.
