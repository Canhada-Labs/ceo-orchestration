# wave-183batch — rail codex rodada 3 (sombra + curas r1, 2026-08-31 S335)

Rail-Verdict: CHANGES-REQUESTED (1 P2 — verificado REAL; curado ANTES da r4)

## Nota de invocação (vale para a família)

A rodada teve DUAS tentativas: a r3 original tentou passar o contexto de
protocolo via `[PROMPT]` junto de `--uncommitted` e o CLI recusou —
**são mutuamente exclusivos** (`error: the argument '--uncommitted'
cannot be used with '[PROMPT]'`). A r3b move a instrução de ALVO para
dentro do próprio prompt («review the UNCOMMITTED changes… use git
status/diff») + o contexto de protocolo (V2 roda ANTES da assinatura V3;
não flagrar ausência de sentinel assinado). Saída:
`<scratchpad S335>/183batch-r3b.txt` (3.765 linhas), TREE-INTACT.
**O contexto funcionou**: o falso-acionável de sentinel da r2 não
reapareceu, e o codex declarou «the remaining changes and targeted
validation checks appear sound».

## O achado (e a cura)

1. **[P2] `mv` de ativação podia sobrescrever um workflow existente do
   adopter** — um `.github/workflows/validate.yml` próprio (inclusive com
   conteúdo não commitado) seria destruído sem aviso. CURA: `mv -n`
   (no-clobber) + instrução de escolher outro nome quando o destino
   existir. frozen-subset segue 7/7 (comentário puro).

## Registro da r2 (contexto)

A r2 (`183batch-r2.txt`, 5.229 linhas) trouxe 1 P1 «adicionar sentinel
assinado antes de editar settings.json» — **improcedente por construção
no fluxo desta casa**: o PROTOCOL roda o pair-rail (V2) ANTES da
assinatura do Owner (V3); o sentinel-draft + SIGN/LAND rastreados são
exatamente o mecanismo que produzirá a autorização após o APPROVE. O
achado descrevia o processo já em curso; nenhuma mudança de patch cabia.
A r3b, com o contexto explícito, não o repetiu — e o comentário funcional
da r2 («functional edits and focused tests appear sound») segue válido.
