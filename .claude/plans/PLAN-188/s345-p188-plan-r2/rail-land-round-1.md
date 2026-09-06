Rail-Verdict: APPROVE

# Rail do LAND — rodada 1 (pack `p188-plan-r2`, S347, noite autónoma)

## Regra de parada PRÉ-REGISTRADA (escrita ANTES de ler qualquer saída)

- Um achado P1 NOVO dentro dos paths do pacote (`.claude/plans/PLAN-188-shared-ceremony-toolkit.md`)
  ⇒ cura NO DERIVADOR + UMA rodada (teto). Nunca edição à mão na árvore viva.
- Achado de REDAÇÃO, FORA dos paths do pacote, ou follow-up já nomeado
  ⇒ residual DECLARADO, com o texto do codex citado e a verificação em disco.
- Rodada só com residuais termina em `Rail-Verdict: APPROVE` com a lista abaixo.
- Nunca re-rotular um P1; nunca APPROVE sobre rodada incompleta ou com lane viva.

## Sujeito revisado

O `git diff` NÃO-COMMITADO da árvore viva no momento da revisão: **exatamente
UM path**, `.claude/plans/PLAN-188-shared-ceremony-toolkit.md`, 560 inserções /
58 deleções (618 linhas). É o conjunto EXATO de paths do pacote — a classe
S345-d («veredito de rail vale só para o SUJEITO revisado») é satisfeita por
construção: as DUAS lanes imprimiram o próprio `git status --short` na saída e
ele mostra esse único path.

## Lanes (as duas em paralelo, através do gate de concorrência)

| lane | comando | liveness | veredito |
|---|---|---|---|
| MECANISMO | `codex exec review --uncommitted --skip-git-repo-check -c sandbox_mode=workspace-write -c model_reasoning_effort=max` | cabeçalho da CLI `model: gpt-6-astra` 1×; `Selected model is at capacity` 0×; `usage limit` 0×; `Review was interrupted` 0×; `lsof` sem escritor; bloco terminal próprio | **APPROVE** |
| TEXTO | `codex exec --sandbox read-only --skip-git-repo-check -c model_reasoning_effort=max` (brief no stdin) | `model: gpt-6-astra` 1×; `tokens used` 5×; `Selected model is at capacity` 0×; `usage limit` 0×; `lsof` sem escritor; `tokens used` final próprio | **APPROVE** |

Veredito da lane de MECANISMO, verbatim:

> «APPROVE. The only change is a draft-plan revision; no runtime code or tests
> changed. I found no actionable defects introduced by the revision.»

Veredito da lane de TEXTO, verbatim:

> «APPROVE — No P1/P2 findings in the uncommitted diff. Verified citations
> against current HEAD, including both chain-of-custody ranges. Counts and
> classifier digest match disk; invariant 9's advisory status is authorized by
> the consensus. No personal absolute path found. The diff matches 560
> insertions/58 deletions in one noncanonical draft plan.»

**P1: zero. P2: zero. Nenhum achado a curar, nenhum residual de rail.**

### Nota de liveness (falso-positivo de marcador, verificado em disco)

A lane de MECANISMO contém 1 ocorrência da string `at capacity` e 3 de
`Full review comments:`. NENHUMA é marcador da CLI: todas são conteúdo do
REPOSITÓRIO que o revisor leu e citou de volta (`CLAUDE.md` linha 115 e linha
108; `PLAN-188-shared-ceremony-toolkit.md` linhas 263 e 265, que discutem
exatamente esses marcadores). O marcador de rodada morta —
`Selected model is at capacity` — aparece **0 vezes**. A rodada é VÁLIDA.

## Residuais DECLARADOS (não são achados desta rodada; vêm do pacote)

Nenhum residual de rail. Os residuais que viajam são do PLANO, por desenho:

1. **As OQ-1..OQ-9 do próprio PLAN-188 seguem ABERTAS por desenho** — são
   decisões do Owner (chaves de orçamento da OQ-4, o número `ADR-2xx`, o destino
   dos clones) e matéria do round 2 do debate. O plano está em `status: draft`.
2. **O round 2 do debate ainda NÃO rodou** — este pacote entrega justamente o
   arquivo REVISADO sobre o qual ele roda.
3. **Observação do refutador, não achado:** o plano diz que `generate-ceremony.sh`
   G1/G6 são «parentes diretos das invariantes 5 e 6» enquanto o consenso K1 diz
   «3 e 5». É deriva de prosa entre dois documentos, não afirmação falsificável
   em disco — material do round 2.
4. **618 linhas alteradas excedem a metade «≤ 400 linhas» do corte v2**; o pacote
   satisfaz a DISJUNÇÃO pelo outro lado (**1 path** ≤ 8), e o DESIGN publica o
   número em vez de escondê-lo.
5. **A cobertura 15/15 prova DECLARAÇÃO**, não que a prosa fecha cada must-fix
   (todo must-fix do consenso tem uma op que o carrega em `mf`; o gerador recusa
   se sobrar must-fix sem op). O DESIGN diz exatamente isso e atribui o
   julgamento ao round 2 do debate.

## Refutador

`REFUTER-VERDICT-S344.json`: `refuted=false`, `findings: []`. O refutador
reproduziu o pacote INTEIRO num HEAD DOIS commits além da base do pacote e
obteve o mesmo digest e a mesma bateria — o derivador se auto-cura sob deriva de
base. Este lander repetiu a prova num TERCEIRO HEAD.

## Fornecedor único

As duas lanes são do MESMO fornecedor (codex/GPT-6 Astra). O caveat de
`shared-vendor blind spot` do `CLAUDE.md` §5 vale: a rodada é ADVISORY, e o
pacote é livre (oráculo 0 em todos os paths, nenhuma assinatura devida e
nenhuma foi feita — noite sem o Owner).
