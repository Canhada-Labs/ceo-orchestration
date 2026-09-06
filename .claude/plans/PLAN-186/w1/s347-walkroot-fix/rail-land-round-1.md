Rail-Verdict: APPROVE

# rail-land-round-1 — land combinado S347, pacote `walkroot-fix` (1 path de payload)

Rodada do LANDER sobre a ARVORE VIVA (nao sobre a sombra): duas lanes codex
em paralelo, ambas `gpt-6-astra`, pelo gate de concorrencia, lancadas com
mais de 60 s de intervalo. Sujeito revisado = o diff STAGED deste commit,
isto e, exatamente os dois paths que ele carrega.

## STOP RULE — PRE-REGISTRADA (escrita ANTES de qualquer byte das duas saidas)

Orcamento deste LAND: UMA rodada, duas lanes (mecanismo = `review
--uncommitted` sobre o diff vivo; texto = brief no stdin). Segunda rodada
somente se a lane de mecanismo devolvesse um P1 NOVO dentro dos paths do
pacote.

- P1 NOVO **dentro dos paths do pacote** (`.claude/hooks/tests/test_session_start.py`,
  `.claude/plans/PLAN-186-orchestrator-operating-model.md`) => cura NO
  DERIVADOR (`apply-walkroot-fix.py`), restore + re-apply + repetir bateria e
  gates, UMA iteracao. Pacote que precise de mais de uma cura e DROPADO.
- Redacao, gosto, achado FORA dos paths do pacote, ou follow-up ja nomeado
  (a cura canonica que limita a caminhada; o nome do pacote pai dentro do
  corpo do docstring; o rail de fornecedor unico) => RESIDUAL DECLARADO, com
  o texto do codex CITADO e a verificacao em disco registrada.
- Achado que peca um SEGUNDO path de payload (embarcar o plano de follow-up;
  limitar a caminhada aqui) e FORA DE ESCOPO POR CONSTRUCAO — o split e a
  decisao ratificada. Residual declarado, citado.
- Nunca reclassificar um P1. Nunca APROVAR sobre rodada incompleta. Liveness:
  cabecalho do CLI com `model: gpt-6-astra`; a lane de review termina com o
  PROPRIO bloco final ou uma declaracao explicita de ausencia de defeito
  acionavel; a lane de texto mostra `tokens used`. `Selected model is at
  capacity`, `Review was interrupted`, `Terminated` ou arquivo cortado no meio
  de uma listagem = rodada MORTA.

## LIVENESS — verificada ANTES de ler os vereditos

| lane | rc | cabecalho | marcador de vida | marcadores de morte |
|---|---|---|---|---|
| mecanismo (`review --uncommitted`) | 0 | `model: gpt-6-astra` | declaracao explicita de ausencia de defeito acionavel | 2 ocorrencias, AMBAS texto CITADO de um registro de rail do proprio repositorio que a lane leu (linhas 2127-2128 da saida) — nunca o status desta rodada |
| texto (brief no stdin) | 0 | `model: gpt-6-astra` | `tokens used` (2 ocorrencias) | 2 ocorrencias, o MESMO texto citado (linhas 2466-2467) |

A distincao importa: o marcador so mata a rodada quando descreve o estado
DELA. Aqui ele aparece dentro de prosa que a propria lane leu do repositorio.

## VEREDITOS

**Lane de mecanismo** — rodou por conta propria os 30 testes do modulo sob
execucao isolada em Python 3.9, classificou os dois paths pelo oraculo
canonico (`0` nos dois) e checou espaco em branco no diff. Encerramento:

> APPROVE. No actionable regressions found. All 30 SessionStart tests passed
> under isolated Python 3.9 execution; the opt-in filesystem-root walk was not
> run.

**Lane de texto** — P1: nenhum; P2: nenhum. Verificacoes que ela cita:

> - `test_session_start.py:174`: `None`/`""` resolve to a uniquely created
>   empty directory. Cleanup is registered immediately; xdist workers do not
>   share ownership.
> - `test_session_start.py:181`: only exact `"1"` enables `/`; unexpected
>   values leave it disabled.
> - `test_session_start.py:186`: all three default cases execute, lifecycle
>   execution is forced on, and assertions remain unchanged.
> - `PLAN-186-orchestrator-operating-model.md:5`: frontmatter parses
>   correctly; `b00ba27` is appended once and exists in the ancestry of HEAD.

E o escopo que ela mesma declara, que este registro repete em vez de esconder:

> Approval covers the current diff, before the future progress-log append.

Verificado por mim em disco: `os.environ.get("CEO_TEST_WALK_ROOT") == "1"` e
igualdade estrita (falha FECHADA para qualquer outro valor); o diretorio vazio
vem de `tempfile.mkdtemp` com `addCleanup(shutil.rmtree, ..., True)`
registrado na linha seguinte; e a classe passou a herdar `TestEnvContext`, que
e o isolamento de ambiente exigido pelo contrato do repositorio. O apend do
progress-log e deste proprio registro entra DEPOIS da rodada — nenhum registro
de rail pode revisar a si mesmo.

## RESIDUAIS DECLARADOS (nenhum bloqueia; nenhum toca byte entregue)

1. **Cobertura padrao ESTREITA de proposito.** A raiz do sistema deixa de ser
   exercitada por padrao (`None` e `""` batiam nela duas vezes por corrida) e
   vira opt-in. A cobertura volta quando o follow-up limitar a caminhada.
   Dito no docstring do proprio teste.
2. **A cura canonica nao viaja aqui** — limitar a caminhada por orcamento de
   tempo e por teto deterministico de diretorios VISITADOS, com truncamento
   visivel ao chamador, e follow-up do PLAN-186. Fora de escopo por
   construcao.
3. **O nome do pacote pai permanece no corpo do docstring.** Mante-lo e o que
   faz o delta contra o pacote pai ser exatamente UM hunk de 5 linhas;
   muda-lo seria um segundo delta textual, fora do mandato.
4. **Rail de fornecedor unico** — as duas lanes desta rodada, como as duas
   rodadas do proprio pacote, sao codex/gpt-6-astra. Nao se gastou refutacao
   cross-vendor num pacote de 1 path com oraculo 0.
5. **O derivador nao entra no diff que o rail revisa** (classe conhecida),
   mitigado pelos controles C0..C8 e por ele ser DERIVADO do pai sob checagem
   de sha, nunca digitado.
6. **Cinco vermelhos na bateria completa sao gates de PERCENTIL sensiveis a
   CARGA**, nao deste pacote: os mesmos cinco node ids rodados ISOLADOS deram
   `5 passed` rc 0 nos DOIS bracos — worktree pristina no mesmo HEAD e arvore
   viva com o pacote aplicado.
7. **Um vermelho PRE-EXISTENTE e alheio** na suite `.claude/scripts/tests/`
   (`test_skill_patch_propose.py::test_diff_size_cap_enforced_with_many_lessons`,
   timeout de 30 s no subprocesso) — ja registrado no proprio progress-log
   deste plano na S343, fora de todo path que este pacote toca.
