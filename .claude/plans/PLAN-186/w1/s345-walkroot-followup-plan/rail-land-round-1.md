Rail-Verdict: APPROVE

# Rail do LAND — rodada 1 — pack `walkroot-followup-plan` (S345), land combinado da noite S347

Regra de parada PRÉ-REGISTRADA (escrita ANTES de ler qualquer saída): um P1 NOVO
dentro dos paths do pack ⇒ cura no derivador + UMA rodada (teto). Achado de
redação, achado FORA dos paths declarados, ou follow-up já nomeado ⇒ residual
DECLARADO com o texto do codex citado e a verificação em disco. Rodada só com
residuais termina em `Rail-Verdict: APPROVE` com a lista abaixo. Nunca
reclassificar um P1; nunca APROVAR sobre rodada incompleta.

## Sujeito revisado

Diff não commitado (STAGED) da árvore viva, que é EXATAMENTE o path que aterrissa:

    A  .claude/plans/PLAN-186-FOLLOWUP-hint-discovery-walk-from-root.md

um arquivo NOVO, 55493 bytes, sha256 `7d7b6b82b5ee4c46288ee8b676406b5ab4ba8420b8b21d1c2f334b56f4435ae1`
— o MESMO digest do shadow que a rodada 10 do pack revisou, e o MESMO que um
worktree destacado limpo em HEAD `a2d0fad` re-deriva (classe S345-d: a última
rodada antes de `ready` lê os bytes que aterrissam). Oráculo
`check_canonical_edit.py --is-canonical` imprime `0` no path (LIVRE — nenhuma
assinatura devida, e nenhuma foi feita: noite sem o Owner).

## Lanes (duas, codex `gpt-6-astra`, esforço `max`, em paralelo pelo gate)

- **Lane A — MECANISMO**: `codex exec review --uncommitted --skip-git-repo-check`
  a partir da raiz do repositório. Veredito próprio: **APPROVE** —
  «APPROVE. The only change is a draft follow-up plan; no runtime code changed.
  Read-only plan validation passed, and no actionable defects were found.»
  A lane executou por conta própria a validação de plano do repositório
  (`plan_checks: []`) e mediu a frontmatter contra a janela do leitor de boot
  (`frontmatter_end_chars: 1360`, `visible_in_4096_prefix: True`).
- **Lane B — TEXTO**: `codex exec --sandbox read-only` com brief no stdin (o
  claim do builder, a cauda da EVIDENCE, os números da bateria do lander e os
  DOIS P1 do land anterior nomeados para verificação dirigida). Veredito
  próprio: **APPROVE** — «No verified P1/P2 defects in the staged file.»

**Liveness verificada ANTES da leitura** (nenhum veredito lido com lane viva):
`lsof` sem escritor nos DOIS arquivos de saída; cabeçalho do CLI
`model: gpt-6-astra` em ambos; lane A termina com sua declaração explícita de
ausência de defeito acionável; lane B mostra `tokens used` (3 ocorrências) e
seu próprio `APPROVE`. As ocorrências de `Selected model is at capacity` = 0 nas
duas. A ocorrência única de `Review was interrupted` na lane B e a ocorrência
única de `Full review comments:` na lane A são CONTEÚDO do repositório que os
revisores leram (um registro de rail do pack e o §5 do `CLAUDE.md`,
respectivamente), não marcadores de morte do CLI — verificado com contexto.

## Achados

Nenhum. **P1 = 0, P2 = 0, P3 = 0** nas duas lanes.

Os DOIS P1 que derrubaram o land anterior deste pack foram verificados
dirigidamente pela lane B e estão CURADOS nos bytes:

- **LAND-P1-1** — `PLAN-SCHEMA.md:156-160` é citado verbatim («Do NOT use
  when: …»), a palavra «preferência» sobrevive só dentro da frase que a
  RETRATA, e a nomenclatura `-FOLLOWUP-` é declarada como DESVIO DECLARADO
  roteado ao debate `level: L3`.
- **LAND-P1-2** — cada vermelho nomeado da tabela da §2 é renderizado a partir
  de um censo de `def <nome>` sobre as DUAS suítes e creditado ao comando que o
  COLETA; `test_100k_by_skill_streams_under_budget` aparece sob o comando (6)
  (`.claude/scripts/tests/test_audit_query.py`), nunca sob o comando (4) dos
  hooks. O controle `red_census_control.py` reproduz o defeito ORIGINAL e o
  PEGA.

## Residuais DECLARADOS (não são defeitos deste land; viajam com o plano)

1. O quinto lote de bateria de hooks do artefato-FONTE guarda um RESULTADO e
   nenhum NOME de teste: o conjunto de vermelhos da §2 é declarado um PISO, com
   a fronteira do artefato («4 battery runs + 3 scripts-suite runs») citada, e o
   AC-5 re-deriva a baseline rodando os comandos (4) e (6).
2. A nomenclatura `-FOLLOWUP-` é um DESVIO DECLARADO de `PLAN-SCHEMA.md:156-160`
   caso o Owner leia o escopo como net-new — decisão dele, no debate `level: L3`
   que o próprio plano exige.
3. `status: draft` enquanto o PLAN-186 segue `executing` (`PLAN-SCHEMA` §1.4).
4. Os dois censos (as 331 superfícies condicionais; os vermelhos da §2) são o
   estado de UM commit; as notas de rodapé (a) e (b) dizem isso e cada uma nomeia
   o comando que as re-deriva.
5. Se o PLAN-186 fornece o escopo residual que este follow-up reivindica não é
   decidível a partir dos excertos do brief — é a pergunta que o plano roteia ao
   debate L3.

## Bateria que precedeu esta rodada (na árvore viva, DEPOIS da última edição)

`controls/run-controls.sh` → 9 grupos, `CONTROLS RUNNER VERDICT: PASS`, cada
grupo com pelo menos um braço VERMELHO pego. `gen-design.py --check`,
`gen-census-op.py --root <ÁRVORE> --check` e `gen-red-census.py --root <ÁRVORE>
--check` todos rc 0. pytest dirigido ao corpus de planos (`test_plan_tokens.py`,
`test_check_tla_schema_drift.py`, `test_check_plan_edit.py`,
`test_check_staleness.py`): **88 passed, 1 skipped**, rc 0. Segunda aplicação do
derivador RECUSA por nome (rc 2). Varredura de path pessoal sobre o arquivo
commitado: rc 1 (nenhuma ocorrência).

6 gates de corpus rc 0 sobre a árvore STAGED: `validate-governance.sh` COMPLETO
(`Errors: 0`), `local/verify-counts.sh` («no drift detected»),
`check-claude-md-claims.py`, `check-staleness.py`, `check-test-env-hygiene.py`
(337 flagged, todos allowlisted), `check_contamination.py` («No contamination
outside allowed zones»).

## Parada

Rodada 1 limpa nas duas lanes ⇒ parada pela regra pré-registrada (teto: 2
rodadas; o rail é ADVISORY para packs livres, e uma rodada limpa é um claim
sobre o SUJEITO revisado, não uma prova sobre o repositório).
