Rail-Verdict: CHANGES-REQUESTED (grok text lane; codex unavailable — usage limit until 2026-09-07)

# Rail do LAND — rodada 1 — pack `us5-followup-docs` (S345)

- **Lane de TEXTO:** `grok --sandbox council --no-leader --output-format json`,
  forma artefato+ponteiro (brief redigido pelo redator de egresso, modo 0600,
  `sha256 320ada9d751114f25eb4cb414d9d6dc6191c5d8f05d4d312745193b897a4136a`,
  17 959 bytes), 1 processo, através do slot-gate de grok.
- **Lane de MECANISMO (codex): NÃO RODOU.** A conta codex bateu o limite de uso
  às 22:55 de 2026-09-04 e a janela só reabre em **2026-09-07 00:25**. Comando
  exato a rodar quando reabrir, da raiz do repo:
  `codex exec review --uncommitted` (através do `codex-gate.sh` com
  `CODEX_GATE_SLOTS=8`, um processo por chamada). Enquanto isso o rail de
  mecanismo deste land fica **PENDENTE** e está declarado no commit.
- **Envelope da rodada:** `stopReason: cancelled`, 7 turnos, 586 923 tokens.
  A lane foi cortada no meio da exploração do repo; **a rodada é INCOMPLETA**
  (não emitiu lista final formatada), mas emitiu um achado substantivo, que foi
  tratado como se fosse de uma rodada completa. Por isso houve rodada 2.

## Achado P1 — ACEITO e CURADO

> «the AC-F1 Check (b) is flawed because it assumes the MODEL_HINT block is a
> static data map, but it's actually a dynamic case statement that computes the
> alias at runtime. Regex-anchoring to the heredoc only surfaces the template
> string with the placeholder, not the mapping table.»

**Verificação do lander, no disco, antes de aceitar** (`.claude/scripts/inject-agent-context.sh`):
as atribuições `MODEL_HINT="opus"` / `MODEL_HINT="sonnet"` vivem dentro de um
`case`, e o heredoc `MODEL_HINT_HEADER` só faz `model="${MODEL_HINT}"` — isto é,
interpola a variável e não contém mapa nenhum. O achado REPRODUZ.

**Cura, feita NO DERIVADOR** (`payload/PLAN-186-FOLLOWUP-census-runtime.md`, três
sítios âncora-exatos — Tese, classe de dono do AC-F1, parser do Check (b)):
a superfície deixa de ser descrita como «bloco DE DADOS EMBUTIDO» e passa a ser
descrita como o que é — fluxo de controle rendendo **alias de tier**
(`opus`/`sonnet`), nunca `model_id`; o parser fica proibido de ancorar no
heredoc; e a ausência do passo de resolução alias→`model_id` vira VERMELHO.
Nenhuma edição à mão na árvore viva: restore → payload curado → re-aplicação
do derivador → re-execução da bateria.

## Residual declarado desta rodada

- A rodada foi **cancelada** pelo provedor no meio; a superfície que ela chegou a
  cobrir é a do arquivo novo, e o hunk do plano-pai não foi revisto aqui (foi
  para a rodada 2, parte B).
