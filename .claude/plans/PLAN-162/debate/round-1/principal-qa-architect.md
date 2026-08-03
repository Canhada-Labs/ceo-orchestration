---
round: 1
archetype: Principal QA Architect
skill: testing-strategy
agent_persona: null
generated_at: 2026-08-03T00:00:00Z
---

## Verdict

ADJUST — todas as 12 disposições sobrevivem à re-verificação contra o HEAD atual
(check_canonical_edit.py, 2166 linhas; nenhuma claim está stale), mas a postura de
testabilidade está subespecificada de um jeito que vai produzir testes red-first
não-reproduzíveis, uma regressão real na suíte existente, ou uma severidade mal
calibrada em pelo menos duas findings — nenhum desses problemas exige reabrir o
mérito das disposições, só corrigir COMO elas vão virar prova antes do W1 começar.

## Summary

- Reverifiquei as 12 findings + o rider R1 diretamente contra o HEAD (não os line
  numbers de 2026-07-27 do council report) — grep + leitura completa de
  `check_canonical_edit.py`, `check_arbitration_kernel.py`, `check_budget.py`, e
  os 8 arquivos de teste existentes para esses hooks. Nenhuma claim é stale.
- A proposta não menciona `test_canonical_edit_council_findings.py` — que É o
  precedente metodológico direto (mesmo arquivo, mesmo travamento
  canonical-guarded, mesma obrigação red-first-antes-da-cerimônia) de um debate
  anterior (PLAN-160/S276-S277). Reinventar a convenção de teste em vez de
  reusá-la é o maior ponto cego da proposta.
- R1 (check_budget.py), como escrito, não é red-first-testável — "plano do
  CWD/branch se derivável" não tem NENHUM mecanismo de derivação hoje no código,
  e o fix, do jeito que está desenhado, quebra um teste existente que já fixa o
  contrato atual (`test_indeterminate_plan_skips`).

## Risks

- **R-QA1 (HIGH)** — Regressão certa no land: `.claude/hooks/tests/test_check_budget.py:472`
  (`test_indeterminate_plan_skips`) já fixa como contrato o comportamento que R1
  quer substituir (2+ planos ativos → breadcrumb + allow sempre, zero
  enforcement; asserção `self.assertIn("indeterminate", errors)` na linha ~492).
  Se o fix de R1 landar sem reescrever esse teste no MESMO patch, a suíte de
  ~13k casos fica vermelha no closeout — exatamente o "Validate green" que o
  plano lista como success criterion.
- **R-QA2 (MEDIUM)** — Se o fix de #1 (orçamento GPG) for implementado com
  `time.sleep`/`time.monotonic()` inline sem seam injetável, o teste red-first
  ou precisa de sleeps reais de vários segundos (flaky sob carga de runner —
  este repo já tem histórico documentado de flake em N=20 sob carga, memória
  `feedback-perf-gate-n20-load-flake`), ou não consegue exercitar o caminho
  lento de forma determinística.
- **R-QA3 (MEDIUM)** — Sem adotar a convenção `PLAN1XX_FIX_<letra>` já
  estabelecida, 9 findings FIX independentes arriscam 9 harnesses de teste
  reinventados, inflando a superfície que o pair-rail codex e a cerimônia GPG
  única (W2, "cerimônia consolidada") precisam revisar de uma vez.
- **R-QA4 (LOW-MEDIUM)** — #10 tratada como "fecha um exploit ao vivo por
  invocação" quando na verdade é defesa-em-profundidade só para reuso
  in-process — risco de alocação de esforço desproporcional frente ao trio
  convergente #1/#2/#3.

## Must-fix

1. **Adotar a convenção `PLAN160_FIX_<letra>`** (já implementada em
   `test_canonical_edit_council_findings.py:96-120`) para TODAS as findings FIX
   deste plano: um marcador de string `PLAN162_FIX_<N>` no source do hook +
   `pytest.mark.xfail(condition=not FIXED_N, strict=True)`. É o padrão que já
   funciona para este exato arquivo canonical-guarded (teste escrito ANTES do
   fix, em `hooks/tests/` que NÃO é canonical-guarded; o `strict=True` força a
   falha se o teste passar "por acidente" antes do fix real — o próprio
   docstring do arquivo já documenta essa armadilha para a finding A, linhas
   34-39: uma ordem de candidatos que passa por acidente NÃO pode carregar
   xfail estrito).
2. **R1 não é testável como descrito.** Não existe hoje nenhuma derivação
   CWD→plan_id ou branch→plan_id em `check_budget.py` (confirmei via leitura
   completa do arquivo, 917 linhas) — um teste red-first não pode ser escrito
   contra uma heurística que ainda não tem espec. Proponho desenho concreto
   para o W1, restrito ao que é provável hoje:
   (a) um override explícito `CEO_ACTIVE_PLAN_ID` (espelha o precedente
   `CEO_MAX_PLAN_TOKENS`, `check_budget.py:70-77`) — se setado e bater com um
   dos plan_ids ativos, usa ele;
   (b) na ausência disso, somar tokens de TODOS os planos ativos e comparar
   contra `MIN(cap)` entre eles (mais conservador), e emitir SEMPRE um
   `systemMessage` visível — hoje só existe um breadcrumb em
   `audit-log.errors` (arquivo, não visível em tempo real no transcript);
   (c) deferir "derivável de CWD/branch" para um plano próprio com espec
   própria — não travar o W1 do PLAN-162 inventando essa heurística agora.
3. **Corrigir o enquadramento "skip-silencioso".** `check_budget.py:854-867`
   JÁ escreve um breadcrumb em `audit-log.errors` quando
   `active_plan_count >= 2` — provado pelo teste que já passa,
   `test_indeterminate_plan_skips` (`self.assertIn("indeterminate", errors)`).
   O defeito real é o ENFORCEMENT pulado (decisão sempre allow, nenhum
   `budget_exceeded` jamais emitido), não a ausência de um breadcrumb. Um
   teste red-first escrito contra "não existe breadcrumb hoje" seria um
   falso-vermelho (já existe) e miraria no alvo errado.
4. **Fold #3+#8 (OQ2) esconde uma diferença real de severidade.** Verifiquei
   `_KERNEL_PATHS` em `check_arbitration_kernel.py` (linhas 76-254): contém
   `.claude/dispatcher/**/*` (linha 133) — cobrindo o gap de YAML aninhado da
   #12 como backstop real de defesa-em-profundidade — mas NÃO contém nenhum
   padrão `.claude/security/*` nem `drift-manifest`. Ou seja, #3 (signer
   registry) e #8 (drift-manifest) não têm NENHUMA segunda camada, enquanto
   #12 tem. Foldar #3+#8 num único patch está ok pela implementação, mas não
   herdem o enquadramento "ACCEPT+DOC, low, mitigado" da #12 pra elas — cada
   uma precisa do próprio teste red-first provando o estado hoje
   DUPLAMENTE desguardado (nem `_CANONICAL_GUARDS` nem `_KERNEL_PATHS`), pra
   que a urgência não seja diluída pela associação com a gêmea de severidade
   menor.
5. **#10 precisa de teste in-process, não subprocess E2E.** O próprio arquivo
   já prova (`FindingBCacheBlastRadiusTest`,
   `test_canonical_edit_council_findings.py:605-645`) que a invocação real do
   hook — subprocess novo por evento PreToolUse, via `_python-hook.sh` — já
   mata o cache module-scope entre invocações. Um repro via subprocess para
   #10 dá XPASS por acidente (a mesma armadilha que o docstring já nomeia
   para a finding A). O teste correto é in-process, no estilo de
   `SentinelCacheKeyRegressionTest` (linhas 353-373): carregar o módulo uma
   vez, chamar `_sentinel_grants_path`/`_compute_sentinel_cache_key`
   diretamente, mutar bytes do `.asc`/allowlist/registry ENTRE duas chamadas
   no MESMO processo. Reformular a disposição pra deixar claro que #10 é
   defesa-em-profundidade para reuso in-process (evento multi-candidato
   repetindo o mesmo par sentinel/target, ou um futuro chamador in-process),
   não o fechamento de um exploit ativo por-invocação.
6. **Escopo honesto do teste red-first de #1.** O orçamento de verificação
   GPG só pode ser provado, a partir de `hooks/tests/`, no nível do
   comportamento INTERNO do hook (o loop `for sentinel in sentinels` degrada
   graciosamente um GPG lento para "não verificado → sem grant", nunca para
   "allow"). O teste NÃO consegue reproduzir o harness do Claude Code matando
   o subprocess aos 5s (`settings.json:189`) — isso é comportamento externo
   ao processo Python, inobservável de dentro da suíte. O critério de sucesso
   do fix deve ficar restrito ao que é local ao hook; não deixe o rider
   deslizar para uma alegação sobre o harness que este repo não consegue
   testar.
7. **OQ1 (#5) precisa de um teste-alfinete, seja qual for o veredito.** Grep
   em todos os `test_check_canonical_edit*.py` + `test_canonical_edit_council_findings.py`
   por `parse_error` retorna ZERO ocorrências — o contrato
   `event.parse_error → allow` (main(), linhas ~1907-1909) não está fixado por
   nenhum teste hoje. Se o debate confirmar ACCEPT (leitura minha: deveria —
   `check_arbitration_kernel.py:42-51` documenta explicitamente a assimetria
   fail-open/fail-closed entre os dois hooks como DELIBERADA, não drift),
   ainda assim precisa de UM teste fixando o comportamento atual — senão um
   refactor futuro pode inverter o contrato em qualquer direção sem nada
   pegar. É exatamente a classe "guard que parece proteger mas não protege"
   que este PLAN-162 inteiro existe para fechar.

## Nice-to-have

- Para #11 (unicode guard): um teste de propriedade no estilo de
  `FindingCDeadnessTest.test_c_property_...` — "todo candidato SKILL.md
  GRANTED num evento multi-candidato é escaneado" sobre N candidatos
  sintéticos, não só um repro fixo de 2 candidatos; mais barato de estender e
  pega regressões off-by-one em qualquer lógica de seleção de candidato que o
  fix introduzir.
- Para #9 (blocked_tool): um único teste parametrizado cobrindo os 3 sites
  hardcoded (linhas 1186, 1308, 1759) em vez de 3 testes separados — blast
  radius baixo, não superinvestir superfície de teste.
- Reusar `_CouncilFindingsBase._mcp_bulk_write_event` / `_write_sentinel`
  (já em `test_canonical_edit_council_findings.py`) em vez de re-derivar
  helpers de fixture — este arquivo já tem 7 arquivos de teste irmãos
  (`test_check_canonical_edit.py`, `_coverage.py`, `_kernel_v2.py`,
  `_markers.py`, `_mcp.py`, `_session67_format.py`,
  `_council_findings.py`, ~3400 linhas somadas); adicionar um esquema de
  nomes `PLAN162_...` sem reusar a base class multiplica custo de
  manutenção.
- Para #2/#7 (defeitos de CLASSIFICAÇÃO pura, não de grant de sentinel):
  considerar testar via o oracle `--is-canonical` CLI (linhas 1815-1872,
  `python3 check_canonical_edit.py --is-canonical <path>`) em vez de montar o
  payload JSON completo de PreToolUse que as outras findings exigem — mais
  barato e mais direto ao ponto pra essas duas.

## Unseen

- A proposta nunca menciona `test_canonical_edit_council_findings.py` —
  apesar de ser o precedente metodológico direto (mesmo arquivo, mesmo
  enquadramento "council findings triage", mesma restrição de fix-via-
  cerimônia) de um debate um round atrás. É o maior ponto cego: o plano está
  resolvendo um problema ("como provar red-first um fix num hook
  canonical-guarded que não podemos editar diretamente") que o PLAN-160 já
  resolveu e deixou documentado.
- Nenhuma menção a possíveis interações ENTRE as 9 findings FIX dentro do
  mesmo loop de scan multi-candidato em `main()` (linhas 1972-2025) — por
  exemplo, o fix de #2 (profundidade de symlink) muda quais candidatos
  `_find_sentinels()` retorna de um jeito que pode inverter os fixtures do
  teste de #10? O fix de #7 (strip de scheme em URI) muda o que
  `_canonical_rel()` retorna pra um candidato `uri`-keyed MCP de um jeito que
  interage com a forense de `blocked_tool` da #9 no MESMO evento mcp__? O
  próprio arquivo já tem um teste nomeado explicitamente como interação A×B
  (`SentinelCacheKeyRegressionTest`, herdado do fix PLAN-094 Wave C) — esse
  tipo de bug de interação JÁ mordeu este arquivo antes. O W1 deveria
  orçar pelo menos uma passada de interação N-findings, não só N testes
  unitários independentes.
- Nenhuma discussão de que o fix de R1 é uma MUDANÇA DE COMPORTAMENTO, não
  aditiva — precisa reescrever/aposentar `test_indeterminate_plan_skips`
  como parte do MESMO patch, não como um item separado do W1.

## What I would NOT change

- A tabela de disposições em si (FIX/ACCEPT/DOC-GAP por finding) — toda claim
  que reverifiquei independentemente contra o HEAD (arquivo atual de 2166
  linhas, não os line numbers de 2026-07-27 do council report) se sustentou;
  nada estava stale, nada era falso-positivo. É um sinal forte de que a
  obrigação de dedup-e-verificação foi realmente feita, não carimbada.
  Verificações específicas que fecharam: #2 (symlink check cobre só `p`,
  `p.parent`, `p.parent.parent` — linhas 858-864 — mas os patterns
  `PLAN-*/architect/round-*/approved.md` e o `audit-v2` são 4-5 segmentos, o
  diretório `PLAN-NNN` em si nunca é checado); #7 (`"uri"` está em
  `_MCP_WRITE_PATH_KEYS`, linha 355, mas não existe `urlparse`/scheme-strip
  em lugar nenhum do arquivo); #9 (3 sites hardcoded confirmados, linhas
  1186/1308/1759); #11 (scan de unicode roda só sobre o `file_path` único
  resultante do scan multi-candidato, linhas 2134-2147); #12 (padrões de
  dispatcher cobrem só `*.yaml`/`*.yml` de segmento único + `**/*.py`
  aninhado — nenhum `**/*.yaml`).
- Prioridade 1 na #1 (fail-open por timeout GPG) — corretamente identificada
  como a pior classe de defeito (um guard que pode ser morto para fail-open
  exatamente no caminho — BLOCK — onde fail-open mais importa) e
  corretamente ordenada à frente do resto.
- Deferir o OQ3/R2 (recalibração do instrumento do council) para plano
  próprio — é genuinamente ortogonal ao `check_canonical_edit.py` e
  empacotar aqui só diluiria o escopo da cerimônia.
- Pular o W3 (re-run do council pós-fix) pela ratificação do Owner em
  2026-08-03 — red-first tests + pair-rail codex é verificação adequada para
  uma triagem de 9 findings não-arquiteturais; um segundo council 3-lane
  pago só para confirmação seria sobre-verificação para este escopo.
