Rail-Verdict: CHANGES-REQUESTED (rodada 2 do LAND, 2 lanes codex: TEXTO APPROVE; MECANISMO 3 achados — 1 REFUTADO com citação verbatim de disco, 2 DECLARADOS como residuais fora dos paths do pack. Critério de parada de 2 rodadas atingido; o pack ATERRISSA com os residuais declarados.)

# Rail do LAND — rodada 2 — pack `p171-w0-lote1` (S345)

Rodada sobre a MESMA árvore viva, depois da cura da rodada 1. As duas
lanes foram lançadas pelo `codex-gate.sh`, uma por chamada, com mais de
60 s de intervalo.

- **Lane de TEXTO** (`codex exec --sandbox read-only`, brief no stdin
  com as três curas nomeadas para verificação): **`APPROVE`**.
  VIVA: `tokens used` = 257.990. Nenhuma ocorrência de `usage limit`.
- **Lane de MECANISMO** (`codex exec review --uncommitted`): bloco
  `Full review comments:` presente (VIVA), 3 achados.

**As três curas da rodada 1 não foram re-levantadas por nenhuma das duas
lanes.** A lane de TEXTO, que recebeu as três no brief com ordem de
verificar e não de acreditar, devolveu `APPROVE`.

## Achado 1 — [P1] alegado «rodar o Gate 3 antes de flipar para executing» — REFUTADO com evidência

> «At this first `reviewed → executing` transition,
> `.claude/plans/PLAN-171/debate/round-1/` does not exist, although the plan
> says `/debate start PLAN-171` runs at execution start/before its first L3
> item … include the Gate-3 artifacts before this flip or keep the plan
> reviewed.»

**O que é VERDADE no achado, verificado por mim:** o diretório de debate
do PLAN-171 realmente NÃO existe (`ls .claude/plans/PLAN-171/*` devolve
só `w0`).

**Por que a conclusão não se sustenta — duas citações verbatim de disco:**

1. O critério do PRÓPRIO plano, `PLAN-171-governance-imports-provenance.md:215`:
   «AC-9. Gate 3: `/debate start PLAN-171` **antes do primeiro item L3**.»
   A obrigação está presa ao primeiro ITEM L3, não à transição de status.
2. `PLAN-SCHEMA.md` §«Why state transitions matter»:
   «**`reviewed` → `executing`** is the self-gate: the CEO marks the plan
   as in-progress **when the first commit lands**.» Este é o primeiro
   commit de execução do PLAN-171 — flipar aqui é exatamente o que o
   schema manda; deixar `reviewed` publicaria estado durável falso.

E o que este pack entrega NÃO é um item L3: dois arquivos `.md`, os dois
com oráculo `--is-canonical` = **0** (lido do stdout), zero código, zero
hook, zero `settings.json`, zero workflow. O `CLAUDE.md` Gate 3 condiciona
o `/debate` a «L3+ tasks».

**Residual DECLARADO (a parte do achado que FICA):** a partir deste
commit o PLAN-171 está `executing`, e o primeiro item L3 dos lotes 2-6
**exige** `/debate start PLAN-171` antes de ser executado. O achado é
registrado aqui como a obrigação futura que este land cria, nomeada para
que o próximo executor não a perca. Nenhum byte foi mudado por ele.

## Achado 2 — [P2] evidência machine-readable não rastreada — DECLARADO (fora dos paths do pack)

> «In a fresh checkout this command fails before pytest because
> `node-ids.txt` is not committed; `red-half.json` and the repeatedly cited
> pack `EVIDENCE.md` are absent as well.»

**Reproduz** — é o mesmo residual da rodada 1, agora com o número de
linha do Apêndice A. O relatório já diz, em texto, que esses arquivos
«vivem no pack da sessão». Curá-lo significaria commitar um diretório
que NENHUM pack declarou — precisamente a bandeira vermelha que um land
não pode levantar. **DECLARADO** para uma wave que decida a política de
arquivamento de packs; não é curável dentro dos dois paths deste pack.

## Achado 3 — [P2] faixa de linhas do C.2 — DECLARADO (defeito HERDADO, raiz fora dos paths do pack)

> «The actual file is `.claude/scripts/local/pair-rail-gate.sh`, and lines
> 64-83 only begin Gate 1; login acceptance is at lines 91-100 and the
> Gate-2 login skip is at lines 103-110.»

**Reproduz, e eu confirmei no disco:** em `.claude/scripts/local/pair-rail-gate.sh`
a linha 64 abre o comentário do Gate 1; a aceitação da rota `login`
(`~/.codex/auth.json` ⇒ `AUTH_ROUTE="login"`) está por volta de 91-100 e
o `Gate 2: rotation cadence SKIPPED (route=login …)` por volta de
103-110. A faixa `64-83` cobre só o começo do Gate 1.

**Por que fica DECLARADO e não curado:** a célula do §2 é uma CITAÇÃO
verbatim do registro do PLAN-169 (`PLAN-169-closure-and-cross-session-evolution.md:1663`,
que é onde a faixa `64-83` nasce), e o §2 declara em texto que «o W0
auditou o REGISTRO». A raiz do defeito está num arquivo que este pack
NÃO toca; reescrever a citação para divergir do registro citado é outra
decisão, de outra wave. Registrado com a faixa correta MEDIDA acima,
para quem for corrigir o 169.

## Observação minha (nenhuma lane a levantou) — a linha do Apêndice A

O Apêndice A cita `10 passed, 1 warning in 4.49s`. Rodei eu mesmo o
comando exato do Apêndice, nesta máquina, e obtive `10 passed in 9.90s`
— o número que carrega a prova (**10 passed**) reproduz; o contador de
warning e o relógio não. A linha está atribuída no relatório como a
captura da derivação FINAL do pack (feita na sombra, com `cd` para a
sombra no comando registrado no `EVIDENCE.md` §4), e o `EVIDENCE.md`
diz explicitamente «Re-rodar mudaria só o relógio». Fica **DECLARADO**
como diferença de ambiente, não curada: já gastei a única iteração de
cura permitida e o fato load-bearing (dez controles verdes) reproduz.

## Estado no fim da rodada 2

Oráculo canônico: `0` nos DOIS paths (lido do stdout). Conjunto de paths
inalterado. Metade VERDE re-rodada depois da cura: `10 passed`.
`verify-counts.sh`: `no drift detected`, rc 0. Bateria e gates de corpus
todos rc 0 sobre a árvore ESTAGIADA.
