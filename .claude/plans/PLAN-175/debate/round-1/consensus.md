---
plan: PLAN-175
round: 1
rounds_synthesized: [round-1]
agents_considered: [Critic-A, Critic-B, Critic-C]
decisions_revised_in_plan:
  - "frontmatter (:13 external_wait) — o gatilho de CALENDÁRIO é REFUTADO em disco; external_wait passa a nomear a data de acumulação da família per-projeto (2026-08-21) e o comando que a deriva, ou é removido em favor de um gate de DENOMINADOR"
  - "frontmatter (:10-11 budget) — budget_tokens ganha unidade + fonte, +budget_usd_estimate, +tier_mix_estimate derivados por instrumento, com a linha de comando que os produziu"
  - "§1 passo 1 (:29-37) — o LEITOR de telemetria é nomeado (skill-health.py com --include-rotated e --since explícito); a fronteira vira UMA (o plano diz ≥0,10, o código diz >0.10); N≥100 vira guarda mecânica, não prosa"
  - "§1 passo 2 (:38-44) — a regra ganha guarda de denominador (min_window_coverage_days, min_observed_spawns) e RECUSA como saída; a perna «0 invocações» declara QUAL canal conta como uso; o alvo 42→~25 sai da regra (a regra dá 3) e passa a ser derivado do passo de consolidação; o destino do archive/ é nomeado FORA de .claude/skills/ (ou a exclusão viaja no mesmo patch); o item accessibility sai do passo que escopa «core»"
  - "§1 passo 3 (:45-49) — P3 não abre antes de o ARTEFATO do W1c existir (path + data); o AC-mestre é dividido em «install sem packs» e «install --profile core,<domain> depois da mudança»; os 116 domain são decompostos em packs do modelo v2"
  - "§1 passo 5 (:55-58) — o AC do P5 passa a asserir a CONTAGEM de sítios casados (não só a cor do gate) e o censo de superfícies com literal inclui as que estão fora da lista DOCS"
  - "§3 ACs (:73-86) — P1 ganha AC para a decisão (b) de idioma (conjunto fechado, dono, critério de morte) e para a rota de bootstrap/invalidação do índice; o positive control do P1 declara o consumidor que o torna escrevível"
  - "§3.1 (:97-161) — a nota bloqueante é RE-DERIVADA com o leitor certo (a família de 15,8 dias já entrega N=102 spawns); a sonda é corrigida (usa o mode que descarta, path absoluto, sem literal digitado); o censo do grep é GERADO na execução"
  - "§3 (:94-95) — a linha de debate diz qual artefato satisfaz o runbook e afirma que nenhum dos dois gates autoriza execução sozinho"
  - "§Guard-rails (:60-69) — entra a guarda de amostra insuficiente como razão explícita de RECUSA, alinhada ao §2 «se o ratio não cair, o problema é o INJECTOR»"
synthesized_at: 2026-09-06T05:10:00Z
synthesized_by: VP Engineering (synthesizer, anonymized input) for CEO
---

# PLAN-175 — consenso do round 1

Três críticos, três `ADJUST`, 31 achados somados (14 bloqueantes declarados).
Nenhum pediu `REJECT`. Toda claim citada abaixo foi verificada em disco em HEAD
antes de virar ajuste; as que não sobreviveram estão em
`## Single-agent insights rejected / deferred`.

**Nota de setup (os três críticos, independentemente).** O caminho da convocação
(`.claude/plans/PLAN-175.md`) NÃO existe em HEAD. O arquivo real é
`<ROOT>/.claude/plans/PLAN-175-skills-pruning-discovery.md`, 172 linhas,
`status: reviewed`. Os três criticaram o arquivo real; esta síntese também.

**O que os três mantêm.** A ORDEM de ataque (descoberta ANTES de poda), a forma
DETERMINÍSTICA da regra de poda (contra curadoria à mão), o «arquivar, nunca
deletar», e a honestidade do §3.1 — que documenta um mecanismo morto em vez de
declarar vitória. Nenhum ajuste abaixo toca esses quatro. O que quebra é a
INSTRUMENTAÇÃO: o plano mede com um leitor que não é o seu, sobre uma janela que
não existe, com uma regra cujo resultado real é 12× menor que o prometido.

## Consensus findings (2+ agents flagged)

### C1 — CRITICAL — a janela de 90d que o P1 e o P2 exigem não existe (Critic-A, Critic-B, Critic-C)

Medido sobre a família INTEIRA (9 arquivos `audit-log*.jsonl` do diretório de
estado per-projeto): **133.802 eventos, o mais antigo `2026-08-21T12:13:43Z`, o
mais recente `2026-09-06T07:35:18Z` = 15,8 dias.** A família nasceu com a W1 do
PLAN-182 (split per-projeto; `.salt` e chave HMAC datados de 21/08), então não há
histórico anterior atribuível a este projeto.

O plano pede `janela = 90d` (`:36`) e `0 invocações em ≥90d` (`:38-39`). Sob essa
letra, TODA skill core satisfaz a perna de telemetria por construção — não porque
esteja morta, mas porque o substrato tem 16 dias. E o `external_wait` do
frontmatter (`:13`, «pós-GA v1.3.0; W1c do PLAN-171») nunca nomeia a data de
acumulação, então nenhum leitor mecânico consegue dizer quando a janela abre.

**Severidade acordada:** CRITICAL. **Mitigação:** o `≥90d` é substituído por um
critério de COBERTURA declarada («histórico atribuível completo, profundidade
publicada, ≥ N spawns observados»), ou o `external_wait` nomeia a data
(2026-08-21 ⇒ 90d abrem ~2026-11-19) e o comando que a deriva.
**Landa em:** frontmatter `:13`, §1 `:36`, §1 `:38-39`.

### C2 — CRITICAL — a regra determinística não produz o número que o plano promete, e não tem guarda de denominador (Critic-A, Critic-B, Critic-C)

Duas pernas, ambas medidas em HEAD.

**Perna 1 — o resultado.** Aplicando a regra do `:38-39` sobre o corpus COMPLETO
(as 9 rotações, não o log vivo): 42 skills core; **31 com zero `agent_spawn`**;
**39 presentes no texto do SKILL MAP** (`.claude/team.md` + `.claude/frontend-team.md`);
**o AND das duas pernas dá 3** — `agent-architect`, `ceo-orchestration`,
`terse-mode`. O título (`:3`) e o `:41` prometem `42 → ~25`. A regra escrita
entrega `42 → 39`. Os `~25` não são deriváveis dela: vêm do passo de
CONSOLIDAÇÃO de sobreposições, que não tem critério escrito.

**Perna 2 — a guarda.** O passo 1 carrega `N mínimo = 100 spawns` (`:36`); o passo
2 (`:38-41`) não carrega nenhuma. E o instrumento citado pelo próprio §3.1 devolve
`green` com denominador zero: `<ROOT>/.claude/scripts/ceo-boot.py:695-706`
(`if total == 0: ... return "green"`). Uma regra sem `RECUSA` como saída não pode
ficar vermelha por amostra insuficiente — o AC do P2 (`:79-81`) exige apenas que a
lista seja DERIVADA, o que uma derivação de denominador zero satisfaz trivialmente.

**Severidade acordada:** CRITICAL. **Mitigação:** `min_window_coverage_days` e
`min_observed_spawns` entram na regra com `RECUSA` como terceira saída; o alvo
numérico sai da regra e passa a ser derivado do passo de consolidação, com
critério próprio. **Landa em:** §1 `:38-44`, AC do P2 `:79-81`, título `:3`.

### C3 — HIGH — o §3.1 prova «não há sinal» com o leitor errado; duas seções discordam de quem define a janela (Critic-A, Critic-B, Critic-C)

A nota bloqueante do `:147-156` cita `skill_unknown_ratio` do `/ceo-boot`.
Verificado: `ceo-boot.py:448` (`_iter_audit_events_since(hours: float = 24.0)`)
abre **apenas** `AUDIT_LOG_DEFAULT` (`:81`), sem descoberta de rotacionados, e a
função de unknown-ratio o chama com `24` (`:661`). O log vivo cobre ~5,5 h.

O instrumento REAL do plano é outro e sabe fazer o certo:
`<ROOT>/.claude/scripts/skill-health.py:207` (`discover_logs`) agrega os irmãos
`audit-log*.jsonl` — mas só sob `--include-rotated` (`:699`), e o default de janela
é `30d` (`:705`), não 90d. Ou seja: as duas seções do plano dependem de leitores
diferentes, e nenhuma das duas invocações default responde à pergunta que o plano faz.

**Severidade acordada:** HIGH. **Mitigação:** todo AC de telemetria nomeia o
leitor E a invocação completa (`skill-health.py --include-rotated --since <janela>`);
a nota do `:147-156` é re-derivada com ele. **Landa em:** §3.1 `:147-156`, ACs `:73-78`.

### C4 — HIGH — o `archive/` do P2 não tira a skill de nenhuma contagem nem de nenhum gate, e o plano nunca nomeia o destino (Critic-A, Critic-B)

`<ROOT>/.claude/scripts/local/verify-counts.sh:192` deriva com
`find "$REPO_ROOT/.claude/skills" -name SKILL.md` — recursivo e cego a tier.
`<ROOT>/.claude/scripts/check-claude-md-claims.py:89` usa o glob
`.claude/skills/**/SKILL.md`, igualmente recursivo. Um `archive/` criado sob
`.claude/skills/` continua contando: `166` permanece `166`. Hoje
`ls .claude/skills` devolve exatamente `core domains frontend` — o destino não
existe e o plano (`:40-41`, `:47-48`) promete «`archive/` restaurável» e alívio de
CI/soak sem nomear um path.

**Severidade acordada:** HIGH. **Mitigação:** destino FORA de `.claude/skills/`
(ou a exclusão nos DOIS derivadores viajando no mesmo patch), com controle
positivo `166 → 165` no PR que arquiva a primeira skill.
**Landa em:** §1 `:40-41`, AC do P2 `:79-81`.

### C5 — HIGH — o P3 depende de um W1c que não existe e muda o CAMINHO de instalação, não só a árvore (Critic-A, Critic-B, Critic-C)

`<ROOT>/.claude/plans/PLAN-171-governance-imports-provenance.md` está
`status: executing` (`executing_at: 2026-09-05`) e o W1c é **contract-only** e
não iniciado (`:143`, `:165`, `:189`). O P3 declara a dependência (`:49`, `:88-89`)
mas não nomeia o artefato que a satisfaz.

E mover os 116 domain não é uma mudança de repo: `<ROOT>/scripts/install.sh:1310`
resolve `DOMAIN_SRC="$SOURCE_DIR/.claude/skills/domains/$part"` e `:1319` instala
o path; `<ROOT>/scripts/_framework_manifest_set.sh:194` emite
`.claude/skills/domains/$_fms_part` por parte de perfil. O opt-in por perfil JÁ
EXISTE — o P3 remove a FONTE que esse caminho lê. O AC-mestre (`:83-84`) testa
apenas «install SEM packs», que é justamente o caminho que não regride.

**Severidade acordada:** HIGH. **Mitigação:** artefato do W1c (path + data) vira
bloqueador NOMEADO do P3; o AC-mestre é dividido em duas pernas, a segunda sendo
`install --profile core,<domain>` DEPOIS da mudança.
**Landa em:** §1 `:45-49`, §3 `:83-84`, `:88-89`.

### C6 — HIGH — o AC do P5 não pode ficar vermelho na propriedade que enuncia, e o despino tira sítios do matcher (Critic-A, Critic-B, Critic-C)

`python3 .claude/scripts/check-claude-md-claims.py` sai `rc=0` HOJE, antes de
qualquer mudança: o checker deriva de disco com `tolerance: int = 0` default
(`:68`, `:77`) e mede DRIFT, não «número digitado». O AC do P5 (`:85-86`)
— «`check-claude-md-claims` verde com tolerance=0 após a mudança» — é satisfeito
pelo estado anterior à mudança.

Pior: o casamento é por regex de PROSA (`verify-counts.sh:584+`), e uma claim
REESCRITA simplesmente deixa de casar — nunca é checada de novo. E a lista `DOCS`
(`verify-counts.sh:563-566`) inclui `docs/GUIA-COMPLETO.md` mas **não**
`docs/GUIA-COMPLETO.pt-BR.md`, que carrega o literal em `:73` («166 skills em»).
Esta é a classe `feedback-adr-count-drift-unwatched-docs` já registrada na memória.

**Severidade acordada:** HIGH. **Mitigação:** o AC do P5 asserta a CONTAGEM de
sítios CASADOS (`rule_matches_by_doc`), não a cor do gate; o censo de superfícies
com o literal é gerado e inclui as que estão fora de `DOCS`.
**Landa em:** §1 `:55-58`, §3 `:84-86`, §2 `:64-66`.

### C7 — MEDIUM — a decisão (b) do gap de idioma não tem AC, dono nem critério de morte (Critic-A, Critic-B, Critic-C)

O `:135-140` lista três opções (indexar PT, normalizar a query, manter o fallback)
e **não escolhe nenhuma**, e o `:138-140` afirma que ligar tf-idf em sessão PT é
uma regressão MEDIDA (2/8 contra 4/8). Os ACs do P1 (`:73-78`) exigem mecanismo
vivo + baseline + re-medição aos 30d + regra de Fase 2 — nunca idioma. O P1 pode,
portanto, fechar VERDE exatamente sobre o risco que o §3.1 identificou.

**Severidade acordada:** MEDIUM (HIGH se o P1 abrir antes da decisão).
**Mitigação:** (b) vira AC P1 com conjunto fechado de opções, dono e critério de
morte escrito, ratificado ANTES de ligar a sugestão. **Landa em:** §3 `:73-78`, §3.1 `:135-140`.

### C8 — MEDIUM — o índice não tem rota de bootstrap nem de invalidação, e o censo do §3.1 não reproduz (Critic-A, Critic-B, Critic-C)

`skill-index.sqlite` **existe hoje** no diretório de estado per-projeto
(1.306.624 bytes, mtime 2026-08-22) — a cura foi manual, numa máquina. O `:102-104`
diz «não existia» no presente; a afirmação está estruturalmente certa (não há
bootstrap) e literalmente vencida. Verificado que o censo `grep -rln
skill-index-build` sobre `.claude/hooks/`, `.github/workflows/` e `scripts/`
devolve em HEAD **apenas** `.claude/hooks/_lib/frontmatter.py` (linha 22, docstring)
— nenhuma das três rotas que o `:107-109` cita. A CONCLUSÃO sobrevive (nenhum hook,
nenhum step de CI, nenhuma rota de install); a FIGURA não. E nenhum AC invalida o
índice depois da poda: a sugestão apontaria para skills arquivadas.

**Severidade acordada:** MEDIUM. **Mitigação:** rota de bootstrap + gatilho de
rebuild viram AC do P1; o censo do `:105-109` é GERADO na execução, nunca digitado.
**Landa em:** §3.1 `:102-113`, §3 `:73-74`.

### C9 — MEDIUM — o plano não tem decomposição em waves e o P3 não cabe no modelo de operação v2 (Critic-A, Critic-C)

O §1 são cinco passos sem rótulo de wave; o `budget_sessions: 2-4` (`:11`)
antecede o modelo v2. O P3 move 116 skills numa moção só, contra o teto de
**≤400 linhas alteradas OU ≤8 paths por pacote**.

**Severidade acordada:** MEDIUM. **Mitigação:** decomposição em packs com regra de
parada pré-registrada por pack; o P3 é dividido por domínio.
**Landa em:** §1 `:45-49`, frontmatter `:10-11`.

## Single-agent insights kept

1. **K1 (Critic-C, R-FIN3) — a regra arquivaria `ceo-orchestration`, que o Gate 2
   do `CLAUDE.md` manda invocar em TODA sessão.** Verificado: a saída da regra em
   HEAD é `{agent-architect, ceo-orchestration, terse-mode}`; `CLAUDE.md:26` diz
   «**Invoke the `ceo-orchestration` skill**» sob «Gate 2 — CEO activation
   (before any work)». Causa de forma: `skill-health.py:363-367` conta apenas
   `action == "agent_spawn"` carregando `skill`, e o censo de 133.802 eventos
   devolve **ZERO** ações cujo nome contenha `skill` — o canal de invocação por
   assento/slash-command não emite nada. As outras duas candidatas também são
   invocadas por comando (`.claude/commands/architect.md`, `.claude/commands/terse.md`).
   **Decisão:** vira must-fix. Enquanto o canal de assento não emitir evento, a
   perna «0 invocações» é INOBSERVÁVEL para uma classe inteira e tem de sair da
   regra (ou a regra declara explicitamente que só cobre spawns nomeados).

2. **K2 (Critic-C, R-FIN4) — o `external_wait` de CALENDÁRIO do §3.1 está
   REFUTADO em HEAD.** Medido sobre a família: **102 eventos `agent_spawn`,
   74 com skill nomeada, 28 unknown ⇒ unknown-ratio 0,2745, 11 skills distintas**,
   acumulados em 15,8 dias. O `:145` pede N≥30 e o `:36` pede N≥100 — os DOIS já
   estão satisfeitos. A nota `:147-161` («não há sinal a medir hoje», «é um gate
   que o CALENDÁRIO abre») é falsa no substrato atual; ela mediu com o leitor de
   24 h do C3. O baseline `0,434` da semente (`:21-22`) é da família
   pré-migração e está vencido: a medida de hoje é 0,275.
   **Decisão:** vira must-fix. É a mudança mais consequente do round — o P1 deixa
   de ser bloqueado por calendário e passa a ser bloqueado por INSTRUMENTAÇÃO,
   que é trabalho que uma sessão executa.

3. **K3 (Critic-B, R-QA3) — a fronteira 0,10 tem dois donos que discordam
   exatamente no ponto de decisão.** O plano ativa fail-high em `≥ 0,10` (`:34`);
   `ceo-boot.py:708` marca `red` só em `ratio > 0.10`. Um ratio de exatamente 0,10
   é «atingido» para um e «Fase 2 ativada» para o outro. **Decisão:** must-fix,
   custo de uma linha.

4. **K4 (Critic-B, R-QA4) — o positive control do AC do P1 é hoje inescrevível.**
   Verificado: nenhum hook em `.claude/hooks/*.py` importa `rag_router`/`rag_bridge`
   (os únicos consumidores são `_lib/` e testes), e `rag_router.py:22-33` declara
   o wire-up explicitamente FORA de escopo, delegado a
   `PLAN-097-FOLLOWUP-rag-router-wireup`. O AC `:73-74` («spawn sem skill ⇒
   sugestão aparece no transcript») não tem consumidor que produza o transcript.
   **Decisão:** must-fix — o P1 declara se o wire-up é PRÉ-REQUISITO nomeado ou
   escopo próprio; sem isso o AC é decorativo.

5. **K5 (Critic-B, R-QA5) — a sonda do §3.1 não é um controle.** Verificado em
   `<ROOT>/.claude/plans/PLAN-175/p1/probe-retrieval-language-gap.py`: a linha 25
   atribui `me, re_ = run(en); mp, rp = run(pt)` e **nunca usa `me`/`mp`** — o
   `mode` retornado (a única coisa que distingue tf-idf de static-fallback) é
   descartado; `run()` converte QUALQUER exceção em `("PARSE-FAIL", [])`, que o
   chamador conta como miss; o subprocess usa path RELATIVO; e a linha
   «(static-fallback medido antes: 4/8)» é string DIGITADA no `print` (`:30`),
   não medida. A tabela `:118-122` cita essa sonda como reprodutível.
   **Decisão:** must-fix antes de qualquer re-medição com N≥30 — a classe
   `feedback-instrument-needs-same-scrutiny-as-subject`.

6. **K6 (Critic-C, R-FIN5) — o budget não tem unidade, fonte nem spread.**
   `:10-11`: `budget_tokens: 150-300k` e `budget_sessions: 2-4` ⇒ 50-75k por
   sessão; sem `budget_usd_estimate`, sem `tier_mix_estimate`. O `CLAUDE.md` §5
   registra piso de gate-boot re-pago **F ≈ 97.292 tokens com spread de 51,7 %
   sobre n=41** — o orçamento por sessão é MENOR que o custo de entrar na sessão.
   **Decisão:** must-fix, com os números derivados por instrumento e a linha de
   comando publicada junto (regra `feedback-measurement-must-list-its-inputs`).

7. **K7 (Critic-A, R-VP7) — o item accessibility está fora do escopo do passo que
   o carrega, e a figura `lgpd×4` não reproduz.** Verificado: as três skills de
   accessibility vivem em `.claude/skills/frontend/{accessibility-and-wcag,
   frontend-accessibility}` e `.claude/skills/domains/government/skills/
   accessibility-section-508` — **nenhuma em core**, enquanto o `:38` escopa o
   passo a «podar o core». `grep -rli lgpd` sobre core devolve **9** arquivos, não
   4. Os basenames duplicados são exatamente **2** (`frontend-data-layer`,
   `frontend-patterns`) — essa figura SOBREVIVE. **Decisão:** must-fix — as quatro
   figuras de consolidação são GERADAS na execução, e o item accessibility migra
   para o passo cujo escopo o contém.

8. **K8 (Critic-A, R-VP11) — o denominador da semente discorda do catálogo.**
   `:21` diz «157/164 skills (96%)»; o título e o `:55` dizem `166`. Disco em HEAD:
   **166 = 42 core + 8 frontend + 116 domain**, batendo com `verify-counts.sh:31-34`.
   **Decisão:** mantido como correção de texto (P3, não bloqueante), mas a semente
   passa a datar seu denominador.

9. **K9 (Critic-A, R-VP12 + Critic-B, R-QA9) — duas ambiguidades de governança.**
   (a) O `:94-95` («Codex r1→r3 (GO no r3); `/debate start PLAN-175` no início da
   execução») não diz qual artefato satisfaz a linha do runbook, e nenhum dos dois
   gates autoriza execução sozinho. (b) Há DOIS `external_wait` para o mesmo plano
   em fontes diferentes: o frontmatter `:13` e o bloco `:158-161`; um leitor
   mecânico do frontmatter conclui que o gatilho já passou. **Decisão:** must-fix
   de texto — uma fonte só de `external_wait` (C1 já a reescreve) e uma frase
   dizendo que este round é coerência de DESENHO, não autorização.

## Single-agent insights rejected / deferred

1. **REFUTADO EM PARTE — «com telemetria vazia a regra arquiva TODA skill core
   fora do SKILL MAP» (Critic-A, R-VP2).** A guarda ausente é real (é a perna 2 do
   C2), mas o raio de explosão não é o afirmado: o conjunto «core ausente do SKILL
   MAP» tem **exatamente 3 membros** em HEAD (39 dos 42 estão no MAP), então a
   falha-aberta arquiva 3 skills, não 42. O agravante verdadeiro é K1 — uma das 3
   é `ceo-orchestration`. Registrado com a aritmética correta; a severidade
   CRITICAL sobrevive pelo CONTEÚDO do conjunto, não pelo seu tamanho.

2. **REFUTADO EM PARTE — `scripts/install.sh:3732` como superfície com o literal
   «166» (Critic-B, R-QA7).** Verificado: essa linha lê `"    - 12 fintech skills
   in .claude/skills/domains/fintech/skills/"` — o literal ali é `12`, não `166`.
   A claim de que existem superfícies com literal FORA do gate sobrevive com um
   sítio verificado: `docs/GUIA-COMPLETO.pt-BR.md:73`, ausente da lista `DOCS` de
   `verify-counts.sh:563-566`. O censo do C6 é GERADO, não copiado desta lista.

3. **REFUTADO EM PARTE — «o mecanismo de sugestão não tem consumidor em HEAD»
   (Critic-B, R-QA4).** `rag_router.py:22-33` diz o oposto na letra:
   `route_query()` **É** chamado em produção por `skill-retrieve.py::_rag_retrieve`
   — «LOAD-BEARING but TELEMETRY-ONLY», opt-in default-OFF. A formulação exata que
   sobrevive (e vira o K4) é: nenhum HOOK injeta a sugestão no transcript de um
   spawn, logo o positive control DO AC não é escrevível. A diferença importa: o
   plano não precisa construir o retriever, precisa construir o injetor.

4. **DEFERIDO — a figura do censo `grep -rln skill-index-build` (Critic-A R-VP10,
   Critic-C R-FIN7).** Confirmado que não reproduz (HEAD devolve
   `.claude/hooks/_lib/frontmatter.py:22`, uma docstring). É defeito de FIGURA, não
   de MODELO: nenhuma das ocorrências é rota de bootstrap, então a conclusão do
   §3.1 fica de pé. Absorvido dentro do C8 como «gerar na execução», sem reescrever
   o achado.

5. **DEFERIDO — o P4 não nomeia o ponteiro do nightly (Critic-C, R-FIN10).**
   Verificado que `check-model-deprecations.py` resolve raízes por precedência
   (argv > `CEO_DEPRECATION_SCAN_ROOTS` > repo) e que nenhum dos dois planos nomeia
   o arquivo do nightly nem a variável. Mas o `:50-51` delega a EXECUÇÃO ao W-IM do
   PLAN-172 sob a regra «dono único, sem rota dupla» — nomear o sítio AQUI recria a
   rota dupla que o r2 fechou. Fica como nota para o PLAN-172, não como ajuste deste.

6. **NÃO ALTERADO — o Anexo §4 (reframe context-engineering, `:163-172`).**
   Nenhum dos três críticos o examinou. Permanece como está; um round futuro que
   queira revisá-lo tem de pedir foco nele.

## Plan adjustments

| § do plano | mudança |
|---|---|
| frontmatter `:10-11` | `budget_tokens` com unidade + fonte; `+budget_usd_estimate`; `+tier_mix_estimate` derivados por instrumento, com a linha de comando publicada (K6) |
| frontmatter `:13` | `external_wait` reescrito: a data de acumulação da família per-projeto (2026-08-21) ou a substituição do `≥90d` por critério de cobertura; fonte ÚNICA, reconciliada com `:158-161` (C1, K9b) |
| §1 passo 1 `:29-37` | leitor de telemetria NOMEADO com invocação completa (`skill-health.py --include-rotated --since <janela>`); fronteira `≥0,10` vs `>0.10` unificada com dono único; `N≥100` vira guarda mecânica (C3, K3) |
| §1 passo 2 `:38-44` | `+min_window_coverage_days`, `+min_observed_spawns`, `RECUSA` como saída; declaração de QUAL canal conta como uso (K1); alvo `42→~25` migra da regra para o passo de consolidação, com critério próprio; destino do `archive/` nomeado fora de `.claude/skills/`; item accessibility movido para o passo cujo escopo o contém; as 4 figuras de consolidação GERADAS (C2, C4, K7) |
| §1 passo 3 `:45-49` | artefato do W1c (path + data) como bloqueador nomeado; decomposição por domínio sob o modelo v2 com regra de parada por pack (C5, C9) |
| §1 passo 5 `:55-58` | censo GERADO das superfícies com o literal, incluindo as fora de `DOCS` (C6) |
| §2 Guard-rails `:60-69` | amostra insuficiente entra como razão explícita de RECUSA, alinhada ao «se o ratio não cair, o problema é o INJECTOR» |
| §3 ACs `:73-86` | P1: `+AC` decisão (b) de idioma (conjunto fechado, dono, critério de morte), `+AC` bootstrap/invalidação do índice, consumidor do positive control declarado; P2: `+` controle positivo `166→165`; P3: AC-mestre dividido em duas pernas; P5: asserção sobre CONTAGEM de sítios casados (C6, C7, C8, K4) |
| §3 `:94-95` | qual artefato satisfaz a linha do runbook + frase de que nenhum dos dois gates autoriza execução (K9a) |
| §3.1 `:97-161` | nota bloqueante RE-DERIVADA (a família de 15,8 dias já entrega 102 spawns / ratio 0,275); sonda corrigida (usa o `mode`, path absoluto, sem literal digitado); censo do `:105-109` gerado; baseline `0,434` datado como pré-migração (K2, K5, C8) |
| Semente `:19-25` | denominador `164` datado e reconciliado com os 166 de disco (K8) |

## Round verdict

**RUN-ANOTHER-ROUND**

Regra aplicada: risco levantado por 2+ críticos ⇒ o plano MUDA (nove findings,
C1-C9, todos aplicados); risco de um só crítico ⇒ decisão escrita do sintetizador
(nove mantidos com verificação em disco, seis rejeitados, refutados em parte ou
deferidos com razão).

O rótulo **`design-coherent` NÃO é registrado**: a regra é que ele só vale quando
o round TERMINA com zero itens bloqueantes nas três críticas, e este round abriu
com 14 bloqueantes declarados e fecha com nove ajustes CRITICAL/HIGH pendentes de
absorção no texto.

**Por que não PROCEED:** os três críticos retornaram `ADJUST` e o plano sai do
round com estrutura diferente. As duas mudanças que mais movem a agulha são
opostas em sinal e ambas medidas: o `≥90d` da regra é insustentável (C1) e, ao
mesmo tempo, o bloqueio por CALENDÁRIO do §3.1 é falso (K2) — o P1 destrava, o P2
aperta. O round 2 tem de revisar o plano REVISADO, com esses dois fatos já dentro
do texto; revisar o que foi criticado seria revisar uma versão que ninguém vai
executar (doutrina `feedback-clean-rail-round-is-not-the-end`).

**Por que não ESCALATE-TO-OWNER:** nenhum dos nove ajustes exige decisão do Owner
para SER ESCRITO. Dois são Owner-facing e podem ser colhidos em PARALELO ao round
2, sem bloquear: (i) o `external_wait` do frontmatter é texto ratificado na S302f,
então sua reescrita pede ciência do Owner; (ii) a decisão (b) do gap de idioma
(C7) fixa uma política de produto — o round 2 apresenta o conjunto fechado de
opções com o custo de cada uma, e o Owner escolhe. O P1, depois de absorvido este
round, é um pacote LIVRE (instrumentação + medição, nenhum path canônico) e cabe
no modelo de operação v2; o P2 e o P3 continuam bloqueados por C2/C5.

**O que falta antes de o P1 abrir como pacote livre** (resposta direta à pergunta
da convocação): (1) o leitor e a janela nomeados nos ACs (C3); (2) a guarda de
denominador escrita, com `RECUSA` como saída (C2 perna 2); (3) o consumidor que
torna o positive control escrevível — wire-up como pré-requisito nomeado ou como
escopo do P1 (K4); (4) a sonda do §3.1 corrigida antes de qualquer re-medição (K5);
(5) a decisão (b) de idioma ratificada, porque ligar tf-idf em sessão PT é
regressão medida (C7). Nada disso depende de calendário — depende de instrumento,
que é trabalho que uma sessão executa.
