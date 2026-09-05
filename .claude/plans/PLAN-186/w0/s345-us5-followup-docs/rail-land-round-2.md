Rail-Verdict: CHANGES-REQUESTED (grok text lane; codex unavailable — usage limit until 2026-09-07)

# Rail do LAND — rodada 2 — pack `us5-followup-docs` (S345)

Teto de rodadas do land = 2, respeitado. As curas desta rodada **não** foram
revistas por uma rodada 3 — residual declarado no fim.

- **Parte A** (arquivo novo, `sha256` do brief
  `aa204491886174a20b0f2f2c4dd328421449058c5195da8f201dbf0c99197e56`, 17 923 bytes):
  `stopReason: end_turn`, 5 turnos — **rodada COMPLETA**, com lista final.
  Confirmou a cura da rodada 1 («accurate and complete in the three places»)
  e achou mais.
- **Parte B** (hunk do plano-pai, brief de 4 990 bytes): `stopReason: cancelled`,
  3 turnos, **sem lista final — rodada MORTA**. O hunk do plano-pai (nota do
  AC-12 + `related_commits` + linha do Progress log) segue **sem revisão
  independente**; é residual declarado, não achado.
- **Lane de MECANISMO (codex): NÃO RODOU** — mesma janela de quota (reabre
  2026-09-07 00:25). Comando: `codex exec review --uncommitted`, da raiz do repo.

## P1 (parte A) — ACEITO, verificado no disco, CURADO por TROCA DE ARQUITETURA

> «alias→`model_id` is RED-if-absent only for `MODEL_HINT`; sibling surface
> `routing-matrix.yaml` stores the same unit and is not covered. Evidence:
> `.claude/dispatcher/routing-matrix.yaml:55` `coder_model: opus`; `:109`
> `coder_model: sonnet` (same aliases as `MODEL_HINT`). The four-line table
> therefore mixes alias and `model_id` unless the declared step applies to every
> alias-valued surface. Same class as the cured P1, still open on this dona.»

**Verificação do lander:** `grep -n coder_model .claude/dispatcher/routing-matrix.yaml`
devolve `opus` nas linhas 55 e 85 e `sonnet` em 109, 134, 157, 174, 191 — a mesma
unidade do `MODEL_HINT`; e o Check (a) compara contra `VETO_HARDCODE`, que devolve
`model_id` (`claude-fable-5`, medido hoje). O achado REPRODUZ.

**Cura:** este é o padrão «a cura gera o achado seguinte» — logo a arquitetura da
cura mudou em vez de remendar o `MODEL_HINT` outra vez. O problema de UNIDADE
passa a ser dito UMA vez, na Tese, como propriedade do censo: das quatro
superfícies, `MODEL_HINT` e `routing-matrix.yaml` (`coder_model`) carregam ALIAS
DE TIER e `VETO_HARDCODE` e os pins de `agents/*.md` carregam `model_id`; a regra
de resolução alias→`model_id` fica **GERAL** («VERMELHO em QUALQUER dona»), e uma
tabela que misture as duas unidades reprova mesmo com as quatro linhas presentes.

## P2 (parte A) — ACEITO, verificado, CURADO

> «Tese says MODEL_HINT is “uma cadeia de atribuicoes por arquetipo”. Disk is
> `case "$DETECTED_SKILL"` over skill ids (`code-review-checklist`,
> `security-and-auth`, …), not archetype slugs.»

**Verificação:** `sed -n '278p' .claude/scripts/inject-agent-context.sh` é
`case "$DETECTED_SKILL" in`, e o primeiro braço é
`code-review-checklist|security-and-auth)`. REPRODUZ — a frase era da cura da
rodada 1, isto é, defeito da própria cura. Corrigida para «`case` sobre
`$DETECTED_SKILL` — SKILL detectada, não slug de arquétipo», com a exigência
de um passo skill→papel DECLARADO pela mesma regra geral.

## P3 (parte A)

3. «Check (b) heading still says “SCRIPT-EMBUTIDO” after the body says it is not
   a data block.» — **CURADO** (o título passa a «donos DADO / SCRIPT»).
4. «all four surfaces share the label “dona local”, but only the three Check (b)
   rows are required to carry it; `VETO_HARDCODE` can pass Check (a) unlabeled.»
   — **DECLARADO, não curado.** É assimetria de redação entre dois Checks de um
   plano `draft`, fora da classe que bloqueia um land; fica para quem executar
   o AC-F1.

## Residuais declarados deste land

1. **As curas do P1/P2/P3-3 desta rodada não passaram por rodada 3** — o teto de
   2 rodadas foi respeitado e o custo fica escrito. As três foram verificadas
   mecanicamente (bateria completa re-executada depois da última edição) mas não
   têm revisão independente.
2. **O hunk do plano-pai não tem revisor independente** (parte B morreu por
   cancelamento do provedor).
3. **Rail de MECANISMO pendente** — nenhuma lane de código revisou o derivador
   nesta noite. O pack já trazia 5 rodadas do seu próprio build (a r4 achou 10
   defeitos de mecanismo, todos curados; a r5 morreu na quota).
4. P3-4 acima.
