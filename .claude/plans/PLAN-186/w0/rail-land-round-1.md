Rail-Verdict: CHANGES-REQUESTED (2 achados REAIS — 2 P2 — verificados por mim no código antes de aceitar, e CURADOS no derivador)

# Pair-rail do LAND — ac10-below-floor-v4, rodada 1

Comando, da raiz do repo (árvore VIVA, patch aplicado pelo derivador,
`git add -A` já feito):

```
codex exec review --uncommitted --skip-git-repo-check -c sandbox_mode="workspace-write" </dev/null
```

Saída bruta: `codex-r1.txt` (388 KB), exit 0. Diff revisado: 2 files,
438 insertions(+), 1 deletion(-) sobre `b53fec1`.

Os DOIS achados são REAIS. Abri o código citado antes de reescrever uma linha.

## R1 [P2] — o gate do ARQUIVO não é alcançado pelo `subagent_type`

Rail: «`check_agent_spawn.py:2435-2440` deriva os papéis varrendo só
`description` e `prompt`, ignorando `subagent_type`». **Confere, verbatim:**

```python
haystack_lower = " ".join([(description or "").lower(), (prompt or "").lower()])
for _role in sorted(_agent_frontmatter.VETO_FLOOR_ROLES):
    if _role.lower() not in haystack_lower:
        continue
```

Logo um spawn DIRETO cujo `subagent_type` seja um papel VETO mas cujo texto
livre não cite o slug **nunca chega** à comparação. A conclusão categórica
«arquivo gateado» / «gate de verdade» escondia um SEGUNDO contorno.

**Cura (nos dois arquivos):** a passagem ganha as duas ressalvas —
(a) derivação por substring que ignora o `subagent_type`, com a rota que
falta nomeada (lookup autoritativo por `subagent_type`); nestas células o
`description` (verbatim no sidecar shipado) NÃO carrega o slug, então se o
ramo rodou dependeu do prompt, não do arquétipo; (b) mesmo alcançado não
bloquearia, porque `code-reviewer.md` seguia pinado em `claude-fable-5`.
O par final vira **«arquivo gateado QUANDO o papel é nomeado no texto livre
do spawn, chamada nunca»**, nos dois arquivos.

## R2 [P2] — «impossibilidade» contradizia o próprio residual

Rail: a frase «A impossibilidade documentada é do PreToolUse do `Agent` tool»
contradiz o residual da MESMA página, que declara NÃO MEDIDO se o `model:`
chega ao `tool_input` — e poderia desviar a cura do hook nativo. **Confere:**
a página diz «não medido» em dois lugares e o adaptador preserva o dict
inteiro.

**Cura:** a frase passa a dizer que do lado do `Agent` tool o que existe é uma
pergunta ABERTA, não uma impossibilidade, e que a diferença entre os rails é
que no Workflow a pergunta nem se coloca.

## Cura de coerência aplicada ANTES da rodada (P3 do refutador)

A nota do plano dizia que `main()` repassa a `decide()` «só
`description/prompt/subagent_type`» enquanto a seção us4 dizia quatro campos.
Abri `check_agent_spawn.py:3140-3148`: são QUATRO, e `names_regex` vem de
`team.load_names`, não do payload. A nota passa a dizer exatamente isso.

## Bateria

Controles positivos re-executados DEPOIS da cura (restore + re-apply); gates
de corpus re-executados sobre a árvore staged final. Detalhe no relatório
do land.
