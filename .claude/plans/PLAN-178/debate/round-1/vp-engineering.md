---
round: 1
archetype: VP Engineering
skill: architecture-decisions
agent_persona: VP Engineering (auditor externo, ADR-058)
generated_at: 2026-08-13T00:00:00Z
---

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- O plano quer (a) fechar 4 gaps achados pela auditoria W0 e (b) adotar 4
  features do substrato 2026, com probe live-fire antes de cada adoção.
- **Forte:** o W0 é uma auditoria de verdade (6/10/4, com controles
  positivos e um gap-conhecido reportado como gap); o AC-1 tem critério
  de kill; o W1.2 (duas fontes lado a lado, switch só com divergência
  <10%) é o ÚNICO item do W1 que já embute contrato de reversibilidade.
- **Fraco (bloqueante):** a wave de adoção de substrato **colide de
  frente com o PLAN-169 W4/W4-C**, que já é dono dos mesmos probes, das
  mesmas `Agent(param:value)` rules e do mesmo `settings.json` — e o
  guard-rail "sem double-booking" do plano lista 172/175/176 e **omite
  justamente o 169**. Somado a isso: o lote C1-C5 está priorizado por
  SEVERIDADE quando o custo real é CANONICIDADE, o W2.1 aponta para um
  template que não existe, e o freeze do GA é mecânico (não social).

## Risks

**R-VP1 — Double-booking com PLAN-169 W4/W4-C. Severidade: CRITICAL.**
PLAN-169 §W4 é literalmente "Evolução do substrato" e já contém: os
probes de Workflow (`PLAN-169:179-185`, `:470-476`), as rules
`Agent(param:value)` (`:523-533` e W4-C item 4, `:640`), as linhas de
postura em `settings.json` nas **4 superfícies de entrega**
(W4-C item 3, `:610-637`) e a pinagem de versão de substrato (`:576-578`).
PLAN-178 W1.1/W1.3 re-executam esse escopo sob outro dono.
*Mitigação:* declarar a fronteira 178↔169 no §Guard-rails com a mesma
granularidade das outras três (172/175/176) — ver Must-fix 1.

**R-VP2 — AC-2 tem desfecho já conhecido e o plano não diz o que fazer
com ele. Severidade: HIGH.** `PLAN-169:470-476` registra evidência
preliminar S298: os 7 `agent()` do workflow de inventário geraram
`subagent_lifecycle_observed` e **ZERO** `agent_spawn` /
`spawn_prompt_defense_gate` — "o gate de spawn NÃO intercepta o caminho
Workflow". O AC-2 do 178 condiciona a migração ao resultado OPOSTO.
Além disso `PLAN-169:184-185` restringe Workflow a **trabalho read-only**
até os dois probes serem respondidos. O plano escreve um gate cujo
resultado provável é BLOQUEIO e não define o ramo "bloqueado".
*Mitigação:* escrever o ramo negativo (o W1.1 morre? espera o W4-C?
vira gap registrado e o piloto muda de alvo?) — Must-fix 2.

**R-VP3 — Lote C1-C5 priorizado por severidade, custeado por
canonicidade. Severidade: HIGH.** Verificado em
`check_canonical_edit.py`: C1 toca `.claude/hooks/*.py` (:139,
canônico ⇒ cerimônia); C2 toca `.claude/workflows/**/*.js` (:331,
**canônico** ⇒ cerimônia, apesar de o plano chamá-la de "cura barata");
C5 toca `.claude/settings.json` (:171, canônico ⇒ cerimônia) — o MESMO
arquivo do W1.3; C3/C4 tocam `.claude/scripts/ceo-boot.py`, que **não**
casa nenhum guard (só `lessons.py`, `prune-lessons.py`,
`lesson-restore.py`, `lesson_ranker.py`, `night-mode.py` — :131-134,
:345) ⇒ PR normal. O agrupamento certo não é "5 itens por P": é **1
lote não-canônico (C3+C4) e 1 pack de cerimônia (C1+C2+C5+W1.3)**.
*Mitigação:* re-agrupar por superfície — Must-fix 3.

**R-VP4 — Adoção de substrato sem contrato de reversibilidade.
Severidade: HIGH.** A lição codex 0.139→0.144.6 (memória
[[reference-codex-cli-substrate-drift]]) é exatamente "a feature nativa
muda de shape e o consumidor quebra em silêncio". W1.1, W1.3 e W1.4 não
têm pin de versão, fingerprint do probe, kill-switch nem entrada em
substrate-watch. Só o W1.2 tem (duas fontes + limiar).
*Mitigação:* cada item adotado do W1 sai com (a) fingerprint do probe
registrado, (b) rota de fallback, (c) entrada em substrate-watch —
Must-fix 4.

**R-VP5 — Freeze do GA é mecânico, não social. Severidade: HIGH.**
`OWNER-GA-CUT.sh:226-246` compara CADA path do delta `rc..HEAD` contra
um conjunto FECHADO (`$GA_DIR/<basename>` ∈ `$GA_OUT_OK`) e faz
`die "freeze violado"` em qualquer path fora. `.claude/plans/PLAN-178*`
não está nesse conjunto. A autorização do Owner para "trabalho pré-rc.4"
não altera o que o script checa — foi exatamente assim que a S303 perdeu
o corte. *Mitigação:* Must-fix 5.

**R-VP6 — W2.1 aponta para um alvo inexistente. Severidade: MEDIUM.**
O plano fala em "emenda ao template `run-*-review.sh`". Não existe
template vivo: as únicas instâncias são
`.claude/plans/PLAN-166/repass-rc3-scripts/run-rc3-scripts-review.sh` e
`.claude/plans/PLAN-166/repass-rc3-cures/run-rc3-cure-review.sh` —
artefatos de plano LANDADO, que o próprio PLAN-169 W0.6/W0.10 declara
"evidência imutável, ficam fora". O plano reproduz a classe que ele cura
no C4 (cura no corpo ≠ referências).
*Mitigação:* nomear a superfície real ou criar o template — Must-fix 6.

**R-VP7 — C1 tem blast radius de migração não censado. Severidade:
MEDIUM.** Tornar `## FILE ASSIGNMENT` obrigatório muda o contrato de
aceite de TODO caller de spawn (`.claude/agents/*.md`, skill `/spawn`,
`inject-agent-context.sh`, os `agent()` de `.claude/workflows/*.js`).
Hoje o hook só exige persona header (`check_agent_spawn.py:759-762`) e
`## SKILL CONTENT`/`## SKILL REFERENCE` (:1055-1068); o parse de FILE
ASSIGNMENT existe (:1687) mas serve só ao Rail 3 advisory (:1835-1853).
*Mitigação:* censo de callers + janela advisory-com-audit antes do
enforce — Must-fix 7.

**R-VP8 — A tabela MAST não é um instrumento, é uma foto. Severidade:
MEDIUM.** Nada re-executa `mast-coverage-table.md`. Ela vai envelhecer
exatamente como envelheceu a claim de `CLAUDE.md:88` — que é o achado P1
do próprio W0. Um plano cuja tese é "instrumento verde com pergunta
envelhecida" não pode entregar como artefato central uma tabela estática.
*Mitigação:* ver Nice-to-have 1 e OQ-3.

## Must-fix (blocking)

1. **Declarar a fronteira PLAN-178 ↔ PLAN-169 W4/W4-C no §Guard-rails,
   item a item.** O guard-rail atual nomeia cascata→172/176,
   context-reframe→175, best-of-N→172 §2, fleet-currency→176 e **omite o
   169** — o único plano cuja wave é, literalmente, adoção de substrato.
   Para cada item do W1, escrever o dono: W1.1 (probes de Workflow) →
   PLAN-169 W0.0/W4.2.0(b) **já é dono**, o 178 CONSOME o resultado e não
   re-executa; W1.3 (scoped permissions) → decidir entre absorver no
   W4-C ou nascer como pack próprio; W1.2 e W1.4 → 178. Sem essa tabela
   de fronteira o plano não passa do Gate 3.

2. **Escrever o ramo negativo do AC-2.** Dado `PLAN-169:470-476`
   (evidência preliminar: o gate de spawn NÃO intercepta o caminho
   Workflow) e `PLAN-169:184-185` (Workflow restrito a read-only até os
   probes fecharem), o desfecho provável do gate é BLOQUEIO. O AC-2 deve
   dizer o que acontece então: (a) W1.1 muda de alvo para um fan-out
   read-only, (b) o gap entra na tabela W0 com dono explícito, (c) a
   migração de qualquer fan-out que ESCREVA fica condicionada ao W4-C.
   Um gate cujo ramo vermelho não está escrito não é fail-closed, é
   indeciso.

3. **Re-agrupar C1-C5 por superfície, não por P.** Verificado em
   `check_canonical_edit.py`: C1 (:139), C2 (:331), C5/W1.3 (:171) são
   canônicos; C3/C4 (`.claude/scripts/ceo-boot.py`) não são. Produzir
   dois lotes: **Lote A (PR normal, sem cerimônia):** C3 + C4. **Lote B
   (UM pack GPG, escopo fechado):** C1 + C2 + C5 + W1.3 + (se aplicável)
   a linha de PROTOCOL.md do W2. Corolário: **C2 não é "cura barata"** —
   `.claude/workflows/**/*.js` foi tornado canônico deliberadamente
   (:315-331); o plano precisa corrigir esse custo antes de sequenciar.

4. **Contrato de reversibilidade por item adotado do W1.** Cada feature
   nativa que entrar em produção sai com: (a) fingerprint do probe
   (versão do substrato + shape observado) registrado no plano, (b) rota
   de fallback explícita quando o shape mudar, (c) entrada em
   substrate-watch para vigiar ESSA superfície. Se a pinagem de versão do
   PLAN-169 W4.4 (`:576-578`, `requiredMinimumVersion` + range em
   `SBOM.md`) for o mecanismo, declarar a dependência: W1 não pode landar
   adoção antes de existir o pin. Copiar o padrão do W1.2 (duas fontes +
   limiar) — é o único item que já acertou.

5. **Resolver o freeze ANTES de landar qualquer arquivo do PLAN-178.**
   `OWNER-GA-CUT.sh:226-246` faz `die` em qualquer path do delta
   `rc..HEAD` fora do conjunto fechado; `PLAN-178*` não está nele. Duas
   rotas legítimas: (i) todo o PLAN-178 fica fora de `main` até o corte
   do GA (trabalho em branch, land pós-GA), ou (ii) emenda assinada que
   adiciona os paths do 178 ao conjunto fechado. A frase "Owner autorizou
   trabalho pré-rc.4; freeze relaxado por decisão dele" (proposal.md:71)
   precisa ser trocada por uma das duas — o script não lê ratificações.

6. **Nomear a superfície real do W2.1.** Não existe template vivo
   `run-*-review.sh` (só as duas cópias congeladas em
   `.claude/plans/PLAN-166/repass-rc3-*/`, que são evidência imutável por
   `PLAN-169:W0.6/W0.10`). Escolher: criar o template em
   `.claude/scripts/` (trabalho novo, declarar) ou reescrever a AC-4
   apontando só para `.claude/commands/debate.md` + `DEBATE-SCHEMA.md`.

7. **Censo de callers antes do enforce do C1.** Levantar todo caller que
   hoje passa sem `## FILE ASSIGNMENT` (`.claude/agents/*.md`, skill
   `/spawn`, `inject-agent-context.sh`, `agent()` dos workflows) e rodar
   uma janela advisory-com-audit medindo a taxa de bloqueio que o enforce
   causaria. Enforce sem censo é uma quebra de contrato de aceite em
   superfície canônica.

8. **OQ-1 — resposta.** Sequência recomendada: **(a) C1 = enforce no
   spawn**, depois do censo (Must-fix 7), dentro do Lote B; fecha a claim
   falsa de `CLAUDE.md:88` e **restaura o sinal
   `spawn_file_assignment_recorded`** de que o Rail 3 depende
   (`check_agent_spawn.py:1836-1853`). **(b) NÃO construir hook de
   enforcement write-time.** Um hook Edit/Write que compare o path alvo
   com a atribuição do spawner precisa de um vínculo spawn→sessão
   confiável que não existe: a atribuição vive no PROMPT, superfície que
   o próprio subagente pode reafirmar. Seria um oráculo do mesmo lado da
   fronteira — a classe que a memória já registra em
   [[feedback-static-shell-matcher-cannot-close-a-boundary]]. **(c)
   INJ-4 fecha no W1.3 (capability nativa) ou não fecha** — e o W1.3 é o
   item com maior colisão de dono (Must-fix 1). Corolário: C1 fecha a
   MENTIRA do doc, não fecha o INJ-4; o plano deve dizer isso
   explicitamente para não vender cura que não entrega.

9. **OQ-3 — resposta.** **Não usar o re-pass de release como piloto.**
   Dois motivos: é o fluxo de maior blast radius do repo e está em voo
   para rc.4/GA; e ele ESCREVE, o que `PLAN-169:184-185` proíbe via
   Workflow até os probes fecharem. Piloto recomendado: **a própria
   re-auditoria MAST** — read-only, recorrente por natureza, e transforma
   `mast-coverage-table.md` de foto em instrumento (fecha R-VP8 de
   graça). Segunda escolha: a auditoria de escopo do `/council`.
   `audit-fanout` e `nightly-hygiene` já são Workflow — não servem de
   piloto de MIGRAÇÃO.

10. **OQ-4 — resposta.** A cerimônia é decidida pelo **path**, não pelo
    rótulo "advisory-até-ratificação": o guard lê
    `check_canonical_edit.py:115-345`. `PROTOCOL.md` (:205) e
    `.claude/hooks/*.py` (:139) ⇒ **cerimônia obrigatória**.
    `.claude/commands/debate.md`, `.claude/plans/DEBATE-SCHEMA.md` ⇒ PR
    normal. Recomendação: landar as regras do W2 em `DEBATE-SCHEMA.md` +
    `commands/debate.md` por PR normal, e adicionar a linha de
    `PROTOCOL.md` **dentro do Lote B** (Must-fix 3) quando ratificada —
    nunca um pack de cerimônia só para uma linha de prosa.

## Nice-to-have (advisory)

1. **Transformar a tabela MAST em instrumento re-executável.** Cada
   célula `coberto` ganha o id do seu controle positivo; um check de
   staleness reclama quando a evidência-âncora (arquivo:linha) não casa
   mais. Custo baixo, e é a única coisa que impede a tabela de virar a
   próxima `CLAUDE.md:88`.

2. **OQ-2 — critério de armamento dos detectores (C5).** Um detector só
   é armado quando tem: (a) taxa de FP MEDIDA num corpus real (replay do
   audit-log das últimas N sessões, não fixture), (b) rota de recuperação
   nomeada (env de escape), (c) controle positivo. Ordem sugerida:
   **1º `CEO_SPAWN_OVERLAP_GUARD`** — é dependência direta do C1
   (enforçar FILE ASSIGNMENT e deixar o Rail 3 advisory entrega metade da
   cura); **2º `CEO_UNICODE_HARDBLOCK`** (determinístico, FP baixo);
   **3º `CEO_VERIFY_AFTER_EDIT_BLOCK`**; **4º `CEO_SPAWN_TOOL_SCOPE`**;
   **por último `CEO_CONFIDENCE_ENFORCE`** — `settings.json:363` diz
   explicitamente "Owner-only flip; ADR-019", e é probabilístico.
   `CEO_SUBAGENT_FABRICATION_BLOCK` merece nota: `settings.json:387` diz
   que ele só escala para `systemMessage`, não bloqueia — armar é quase
   grátis e quase inútil; medir antes de gastar decisão nele.

3. **ADR-191 para a decisão do C1.** Mudar o contrato de aceite de spawn
   é cross-cutting (CLAUDE.md §4, PROTOCOL.md §Spawn Protocol,
   DEBATE-SCHEMA.md §8, todo caller). Último ADR é o 190 ⇒ ADR-191.
   Lembrar que `.claude/adr/ADR-*.md` é canônico (:178) — o ADR entra no
   MESMO pack do Lote B, não num pack próprio.

4. **W1.3: se não for absorvido pelo W4-C, replicar a disciplina das 4
   superfícies.** `PLAN-169:610-637` já pagou o preço de aprender que
   `.claude/settings.json` do dogfood **não** é o settings do adopter
   (`install.sh:1503-1558` constrói o dele do template). Um W1.3 que
   toque só o arquivo vivo entrega mudança dogfood-only — exatamente o
   defeito que o codex r3-P1/r5-P1 pegou no 169.

5. **INJ-3: o gatilho de reabertura é emenda de ADR, não item de plano.**
   ADR-089 está REFUSED com justificativa; acrescentar o vetor
   "escrita-mesmo-plano" ao gatilho é ADR-089-AMEND-1, com o ônus de
   dizer por que a justificativa do ADR-116-AMEND-1 é insuficiente para
   ESTA classe. Registrar como emenda evita que a decisão vire prosa
   dentro de um plano de outra coisa.

## Unseen by the original plan

1. **A distinção dogfood vs. adopter não existe em lugar nenhum do W1.**
   W1.1/W1.2 são mudanças do repo dogfood; W1.3 propaga para adopters via
   `templates/settings/*`. O plano trata as quatro features como uma
   categoria só. Sem essa separação, o §Guard-rails "nenhuma superfície
   canônica muda sem cerimônia própria" é verdadeiro e insuficiente:
   `templates/settings/*` é canônico (`:793` inclui o prefixo
   `templates`) **e** é produto.

2. **Tensão de direção entre 178 e 169 que ninguém nomeou.**
   `PLAN-169:476-478` recomenda `disableWorkflows: true` como default
   fail-closed **para adopters** até existir gate. O PLAN-178 W1.1 quer
   aprofundar a adoção de Workflow. As duas coisas podem coexistir
   (dogfood supervisionado ≠ default de adopter), mas isso é uma decisão
   arquitetural que precisa estar escrita — hoje ela está implícita e em
   dois planos que não se citam.

3. **C1 enforçado + Rail 3 advisory = meia cura, e a metade que sobra é a
   que importa.** O achado W0 nº1 diz que sem o parse o spawn "SOME da
   detecção de colisão". Mas o Rail 3 já está desarmado
   (`CEO_SPAWN_OVERLAP_GUARD` fora do bloco `env` de `settings.json` —
   confirmei: o bloco tem 6 chaves, `CEO_QUIET_MODE`,
   `CLAUDE_CODE_SUBAGENT_MODEL`, `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`,
   `BASH_MAX_TIMEOUT_MS`, `CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR`,
   `ENABLE_TOOL_SEARCH`). Enforçar o C1 sem armar o Rail 3 restaura um
   sinal que ninguém consome. C1 e C5-overlap são **um item**, não dois.

4. **O W0 mediu a cobertura mas não mediu a EXECUÇÃO dos controles.**
   Vários `coberto` da tabela são hooks registrados; nenhum tem taxa de
   disparo real na janela. "Registrado em settings.json" e "dispara na
   prática" são claims diferentes — a lição
   [[feedback-livefire-catches-what-fixtures-miss]] é do próprio repo, 2×
   confirmada. O AC-1 fez isso para 2 células; as outras 18 herdaram o
   benefício da dúvida.

5. **Nenhuma wave tem critério de ABORTO além do AC-1.** W1.2, W1.3,
   W1.4, W2 e W3 não dizem em que condição param. Dado que o plano nasce
   de uma pesquisa cuja conclusão foi "os gaps são quatro e cabem num
   plano curto", o risco de o W1 virar plano-guarda-chuva é real —
   e um plano guarda-chuva sobre `settings.json` colide com o pack de
   escopo fechado do 169 por construção.

6. **C4 é P3 mas é o teste mais barato da própria doutrina do plano.**
   `ceo-boot.py:240` cita `_lesson_render_safe`; o símbolo real é
   `_validate_boot_lesson` (`ceo-boot.py:4272,4436`) — confirmei os dois
   com grep. É um arquivo não-canônico, uma linha, e demonstra a classe
   "cura no corpo ≠ referências". Deveria ser o primeiro item a landar,
   não o penúltimo.

## What I would NOT change

1. **O critério de kill do AC-1** ("tudo verde sem gap ⇒ FALHA do AC").
   É o desenho correto de instrumento e é a razão de o W0 ter valor. Não
   suavizar em nenhuma rodada futura.

2. **O AC-2 como gate fail-closed antes da migração.** Continua certo
   mesmo com o desfecho previsível — o que falta é o ramo vermelho
   (Must-fix 2), não o gate.

3. **O desenho do W1.2** (duas fontes impressas lado a lado por uma
   janela, switch só com divergência <10%). É o único item do W1 com
   contrato de reversibilidade embutido e deve virar o TEMPLATE dos
   outros três, não ser simplificado por economia.

4. **Teams full-mesh fora de escopo.** MAST (coordenação = maioria das
   falhas) + a lição S284 de clobber sustentam a exclusão. Não reabrir.

5. **Números de literatura confinados a `research-S305.md`.** A regra
   está certa e o plano a cumpre — inclusive no corpo, que aponta sem
   duplicar. Manter na revisão de qualquer emenda.

6. **INJ-3 como risco aceito (ADR-089).** A postura está certa; só a
   ROTA de reabertura precisa de forma (Nice-to-have 5).

7. **W1.4 e W3 como estudos read-only com saída go/no-go.** Resistir à
   tentação de promovê-los a execução nesta rodada — é exatamente onde
   um plano de "adoção" costuma estourar o escopo.

---

## Nota de método (fora do formato de 7 seções)

Verifiquei em disco, não no texto do plano: `check_agent_spawn.py`
(:759-762 persona; :1055-1068 skill; :1687 parse de FILE ASSIGNMENT;
:1835-1853 Rail 3 advisory) — a claim de `CLAUDE.md:88` é de fato falsa
para FILE ASSIGNMENT; `ceo-boot.py:1016-1034` (`check_tier_a_spec_version_drift`
sem branch `red` alcançável, ao lado de `check_tier_a_npm_version_match`
:1037-1053 que retorna `red`) — C3 e C5 do W0 confirmados;
`ceo-boot.py:240` vs `:4272` — C4 confirmado;
`.claude/workflows/audit-fanout.js:142,190-196` interpola
`JSON.stringify(items)` cru no prompt do refuter e do synth, sem fence e
sem cap — C2 confirmado; bloco `env` de `.claude/settings.json:739-746`
com 6 chaves, nenhuma dos 6 detectores — C5 confirmado.

Nenhum conteúdo lido continha instrução dirigida a mim.
