# DESIGN — wave `179-followup-flip` (S338, 2026-09-01/02) — PLAN-179-FOLLOWUP AC item 1 (+ emenda S337 + rail r1)

**Origem:** achado REAL do pair-rail r6 da wave-179close (P2, registrado em
`PLAN-179/s335-ceremony-179close/rail-round-6.md`) + a varredura P2 da S337
(registro completo em `PLAN-179-FOLLOWUP-sessionstart-anchor-id.md`,
commitada em `6160578`): os produtores LEGADOS resolviam o id **env-first**
(`CLAUDE_SESSION_ID` > payload) enquanto o consumidor US8
(`SessionEnd._session_start_ts`) casa `session_start` (`:618`) **e**
`session_end` (`:600`) pelo id do **PAYLOAD** por decisao de seguranca (rails
r3/r4: env e agent-spoofable e NUNCA ancora). Quando env ≠ payload, toda
sessao degradava para `start_unknown` / `anchor_source=none` e a segmentacao
do resume ficava cega ao `session_end`.

Medido na sombra ANTES do flip (baseline, `exp_baseline.py`, 2026-09-02):
`session_start | env-divergent-id`, `session_end | env-divergent-id`,
`session_memory_delta_observed | payload-id` na MESMA cadeia; o consumidor
devolveu `(None, "none")` para o id do payload. A degradacao e SEGURA (nunca
janela errada) — o que esta wave entrega e o alinhamento do PRODUTOR, a
unica direcao compativel com a doutrina.

## Decisoes de desenho

1. **Flip dos QUATRO produtores de ciclo de vida no MESMO patch; precedencia-modelo = `payload_sid`.**
   `SessionStart.py::main` (`session_start`), `UserPromptSubmit.py::main`
   (`prompt_submitted`), `Stop.py::main` (`session_stop`) e
   `SessionEnd.py::main` (`session_end`) passam a
   `payload > CLAUDE_SESSION_ID > timestamp`. O AC nomeava DOIS (start + end,
   emenda S337); o **pair-rail r1 desta wave** (P1, verificado REAL por censo
   mecanico — `rail-round-1.md`) mostrou que um flip PARCIAL fragmenta o
   ciclo de vida de UMA sessao em dois ids para leitores que particionam por
   `session_id` (`ceo-escalation-detector.py:163-178`), e o censo de TODO
   sitio `CLAUDE_SESSION_ID` em hooks/scripts provou que a classe «produtor de
   ciclo de vida env-first» tem EXATAMENTE estes 4 membros, com a MESMA
   linha. Doutrina do repo aplicada: patch ramo-a-ramo gera a proxima
   regressao; rail acha a classe, censo fecha. **Expansao de escopo em
   relacao ao brief (2 → 4 hooks; 3 → 5 paths), declarada aqui e no retorno
   estruturado para veto do Owner no SIGN.** A redacao original do AC
   ("espelhando `SessionEnd.py::main`") estava errada — o `main` legado ERA
   `env or payload`; o modelo e o rail novo (`payload_sid`, `SessionEnd.py`),
   que segue INTOCADO (sem fallback; unico id que o memory-delta aceita).
2. **Sem mudanca de comportamento alem da precedencia.** Os dois fallbacks
   sobrevivem e sao testados nos 4 produtores: payload sem id ⇒ env; nem
   payload nem env ⇒ `%Y%m%dT%H%M%S` UTC. `payload_session_id=payload_sid`
   continua viajando separado para `SessionEnd.decide()`. Colateral medido:
   `check_anti_ceo_overhead.py:166` chaveia o record do tool_lifecycle pelo id
   do EVENTO, entao `SessionEnd._cleanup_tool_lifecycle(session_id)` passa a
   apagar o record CERTO sob divergencia.
3. **O consumidor NAO e relaxado.** `test_divergent_env_id_never_anchors`
   fica (so o docstring deixa de apontar para um futuro que virou passado);
   `_session_start_ts` nao e tocado. A wave e producer-side por
   construcao — e o teste de integracao prova o OUTRO lado da mesma moeda:
   com env divergente, o start GRAVADO pelo produtor real e ancorado
   (`anchor_source=chain`) e o `session_end` gravado pelo produtor real
   segmenta a janela do resume (`outcome=absent` para topico da invocacao
   anterior — pre-flip o mesmo fluxo dizia `written`).
4. **O lock env-first da r12 P2-b e INVERTIDO em-lugar, e vira ESTRUTURAL.**
   `test_lifecycle_id_mirrors_sessionstart_env_first` (wave-179close)
   afirmava a precedencia que esta wave troca — ficaria VERMELHO por desenho.
   Substituido no mesmo lugar por
   `test_lifecycle_id_is_payload_first_in_all_four_producers`: ordem dos
   operandos do `or` na atribuicao `session_id = ...` por **AST**
   (`_session_id_operands`, grupos aninhados achatados — parenteses nao
   escondem operando), nos 4 `main()`; o `str.index` do teste antigo era
   enganavel por comentario/reflow. O docstring antigo tambem afirmava que
   `main()` "nao e honestamente construivel aqui" — REFUTADO: o adapter
   resolve `sys.stdin` em tempo de CHAMADA por desenho (`adapters/claude.py`),
   entao `_run_hook_main` (stdin JSON + env via `mock.patch.dict`) dirige o
   `main()` REAL, como o harness. Toda assercao e sobre a LINHA GRAVADA na
   cadeia isolada, nunca sobre a variavel que o hook computou.
5. **Um arquivo de teste, cinco paths tocados.** Os testes de unidade (4
   actions) e a integracao vivem em `test_session_end_memory_delta.py` — ele
   ja possui a cadeia isolada, o dir de memoria derivado pelo resolvedor
   unico, o seed assinado e a trava do consumidor; um helper
   (`_run_hook_main`) em vez de copias por hook. Alternativa (casa "natural"
   por hook) rejeitada por duplicacao e +4 paths sem ganho de cobertura.
   Nenhum teste existente de Stop/UserPromptSubmit afirmava env-first
   (grep em `hooks/tests`).
6. **Fronteira do segundo e contrato, nao flake.** O primeiro run do teste
   de start deu `absent`: o `ts` do wire e second-floor e o consumidor abre
   a janela no PROXIMO segundo inteiro (`SessionEnd.py:828-829`,
   `start_ts += 1.0` — escrita dentro do segundo do start NUNCA e
   reivindicada). Cura no TESTE, nao no hook: espera limitada (<1,1 s) pela
   fronteira no relogio REAL, derivada do `ts` da linha gravada; mockar o
   teto (`time.time`) testaria a costura, nao o contrato de producao.
7. **Kernel.** Os 4 hooks ∈ `_KERNEL_PATHS` (`check_arbitration_kernel.py:218-221`,
   membros desde `9777a8d` v1.0.0 — o PROPOSED da wave-179close rotulou
   `SessionEnd.py` so "CANONICO"; a medicao mecanica por `fnmatch` sobre a
   lista viva diz KERNEL). O LAND arma `CEO_KERNEL_OVERRIDE`/`_ACK` no MENOR
   escopo (molde 179close/183batch/fable51). Nenhum dos 5 paths e membro do
   manifesto ADR-192.
8. **Derivacao byte-a-byte.** `apply-179fu-flip.py`: 11 edicoes
   `(path, ancora EXATA, substituto, contagem)` planejadas ANTES de qualquer
   escrita; ancora ausente/ambigua ⇒ recusa nomeada; guard de dupla aplicacao
   pelo marcador `PLAN-179-FOLLOWUP (S338)` (0× em HEAD nos 5 paths; presente
   em TODO substituto — auto-verificado no `_plan`, porque as insercoes puras
   deixam a ancora viva). Re-aplicacao medida: RECUSADO (arvore intocada).
   Verificado em DOIS HEADs — `dc72bf1` (inicio da sessao) e `f0e98de`
   (HEAD corrente; `6160578` + materiais fable51 entraram durante a
   construcao): os 5 paths sao byte-identicos entre eles.
9. **`dist/` fora.** `dist/ceo-plugin/hooks/*` e gitignored (`.gitignore:198`),
   gerado por `scripts/build-plugin.py` — nao viaja no patch.

## O que fica FORA, nomeado

- `check_output_secrets.py:404-408` (`env or parsed.session_id`): env-first,
  mas security-matcher PostToolUse — outra classe de risco; e os ~20 emits
  `session_id=os.environ.get("CLAUDE_SESSION_ID","")` (env-ONLY, sem payload
  em escopo) — atribuicao best-effort, nao precedencia. Censo em
  `rail-round-1.md`; decisao do Owner.
- `SPEC/v1/audit-log.schema.md` linhas v2.7 (`session_start`/`session_end`/
  `prompt_submitted`/`session_stop`): registrar a precedencia e opcional e
  CANONICO (deny-Edit) — compatibilidade concluida na varredura S337.
- `scripts/codex-advisory-teeth.py`, `ceo-escalation-detector.py`: leitores
  ALINHADOS pelo flip (cura colateral), sem edicao.
- Item 2 do FOLLOWUP (`harness-noop-allowlist.txt`): WITHDRAWN na r14.
- Frontmatter/`[x]` do `PLAN-179-FOLLOWUP-...md` (commitado em `6160578`):
  o flip do plano e do orquestrador/Owner, nao deste pack.

## Numeros medidos (fontes no EXPECTED-BASELINE-DRAFT.txt e EVIDENCE.md)

- 5 paths: 4 canonicos (TODOS KERNEL) + 1 livre; 0 membros do manifesto;
  5 `.py`, 0 `.sh`; 11 edicoes.
- Arquivo tocado sozinho: **60 passed** (52 → 60: +9 novos, −1 substituido
  em-lugar). Bateria declarada de 21 arquivos: ver EVIDENCE §3 (medida
  DEPOIS da ultima edicao, sombra re-derivada do zero).
- Controle positivo (script FINAL aplicado, os QUATRO hooks revertidos a
  HEAD numa worktree de controle descartada): **7 failed / 2 passed** nos 9
  testes novos — RED exatamente os 7 dependentes do flip (4 unit "records
  payload id", lock estrutural, 2 integracao); GREEN os 2 de preservacao de
  fallback (env-only, timestamp), que DEVEM passar pre-flip. Arquivo inteiro
  no controle: 7 failed / 53 passed — os 53 pre-existentes nao se movem.
- Rail codex: r1 = 1 P1 REAL (classe fechada por censo → 4 produtores);
  r2 = ver `rail-round-2.md` (a ultima rodada registrada e a que autoriza).
