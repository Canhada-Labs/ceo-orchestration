---
plan: PLAN-186
round: 1
rounds_synthesized: [round-1]
agents_considered: [Critic-A, Critic-B, Critic-C]
decisions_revised_in_plan:
  - "frontmatter — unidade de budget_tokens declarada; tier_mix_estimate em 2 blocos (assento/subagente); budget_usd_estimate; depends_on += wave-fable51"
  - "§1 — cada número derivado do night-run S338 marcado RAZÃO (sobrevive) ou ABSOLUTO (inflado ~2,8×)"
  - "§2b — matriz papel × modelo × effort entra no plano com eixo trocado: DEFINE pergunta → Opus 5; EXECUTA derivação → Sonnet 5"
  - "§3 W0 — +US4 precedência inherit × pin, +US5 censo de superfícies de roteamento, +US6 sonda de hookabilidade de SendMessage; sonda de concorrência re-desenhada (3 rep/N, controle positivo, célula de output alto, célula de 2 terminais)"
  - "§3 W1 — AC dividido (workflow vs spawn direto); enforce nasce com rota de recuperação nomeada; lint de model id no mesmo patch; critério de morte com canal/janela/denominador"
  - "§3 W2 — contrabalanceamento ABBA, custo de troca assimétrico pré-registrado, janelas censadas tratadas, MDE declarado, eventos de bloqueio como instrumento primário"
  - "§3 W3 — conjunto de sítios DERIVADO mecanicamente; os DOIS ids no piso durante a transição; sha256 congelado regenerado no mesmo patch; rollback declarado como segunda cerimônia"
  - "§3 W4 — fail-fast: false + gate de forma; baseline de node-ids; composite bootstrap; nome de job preservado + 3 sítios de BRANCH-PROTECTION; toolchain replicado com assert; runner-minutos"
  - "§3 W5 — 6 sítios do Step 0; parallelization-by-default e check_anti_ceo_overhead.py no escopo; CONSUMES: na gramática; custo fixo por spawn como 3º critério"
  - "§Acceptance criteria — AC-1..AC-8 reescritos; +AC-10 (precedência), +AC-11 (runner-minutos), +AC-12 (rota de roteamento)"
  - "§Open questions — OQ-4 REABERTA; +OQ-6 (unidade de budget, repo-wide), +OQ-7 (escopo da rota única), +OQ-8 (orçamento de runner)"
synthesized_at: 2026-09-02T18:30:00Z
synthesized_by: VP Engineering (synthesizer, anonymized input) for CEO
---

# PLAN-186 — consenso do round 1

Três críticos, três `ADJUST`, 26 must-fix somados. Nenhum pediu `REJECT`.
Toda claim citada abaixo foi verificada em disco antes de virar ajuste; as que
não sobreviveram estão em `## Single-agent insights rejected / deferred`.

## Consensus findings (2+ agents flagged)

### C1 — CRITICAL — a W3 quebra todo spawn VETO como escrita (Critic-A, Critic-B, Critic-C)

`VETO_FLOOR_ALLOWED` (`.claude/hooks/_lib/agent_frontmatter.py:135-142`) tem três
membros: `claude-opus-4-8`, `claude-fable-5`, `claude-opus-5`. `claude-fable-5-1`
**não é membro** — o Amendment 2 do ADR-149 (`:248`) diz literalmente que a
allowlist fica *unchanged* e que Fable 5.1 é selecionável, não VETO-elegível.
Flipar os 5 pins sem emendar a allowlist faz `validate_veto_floor_models` reportar
violação nos cinco e `check_agent_spawn.py` — fail-closed por contrato — bloquear
todo spawn VETO. O corpo da W3 resolvia isso em quatro palavras
(«`VETO_FLOOR_ALLOWED` coerente») e o AC-5 não nomeava o path.

Dois agravantes verificados: `VETO_HARDCODE` (`tier_policy_cli/_constants.py`) e o
literal independente `VETO_HARDCODE_APPLY` (`apply.py`) guardam `claude-fable-5`
atrás de uma asserção sha256 em tempo de import — mudar o dict sem regenerar o hex
no MESMO patch derruba `learn.py`/`apply.py` no import. E `set-quality-profile.sh`
deriva de `VETO_HARDCODE`: pins mudados sem a constante são revertidos em silêncio
na próxima invocação (armadilha já registrada em `PLAN-169/fleet-currency-audit-S298.md`).

**Severidade acordada:** CRITICAL. **Mitigação:** o conjunto de sítios da W3 é
DERIVADO mecanicamente antes da cerimônia, com um oráculo por sítio; os DOIS ids
ficam aceitos no piso durante a transição (rollback vira mudança de settings, não
segunda cerimônia); o sha256 congelado é regenerado como edição derivada; controle
POSITIVO = um spawn VETO real verificado pelo campo `model` servido.
**Landa em:** §3 W3, AC-5, §Riscos.

### C2 — CRITICAL — o −US$ 1.369/mês não é atribuível à W1 como escopada (Critic-A, Critic-B)

Dois mecanismos independentes, mesma conclusão. **Cobertura:** a W1 edita `agent()`
em 4 workflows + 3 sítios do molde de night-run; o caminho de spawn dominante deste
repo é a chamada `Agent` DIRETA do CEO, que não passa por nenhum deles e herda o
assento. **Contaminação:** o split «builders 80 % / refutadores 20 %» que produz o
número vem da tabela §2.1 do relatório 05, derivada inteiramente dos 58 arquivos
que a W0 mostrou inflados ~2,7-2,9× por dedup falho — e a inflação é POR BLOCO DE
CONTEÚDO, logo enviesada por papel (builders emitem `tool_use`, refutadores
`thinking`/`text`). O split é artefato do instrumento defeituoso, não só os dólares.

**Severidade acordada:** CRITICAL para a atribuição do número; HIGH para a wave.
**Mitigação:** AC-3 dividido em caminho de workflow e caminho de spawn direto; o
split re-derivado com o instrumento novo sobre os 7 transcripts do S338 (execução
de segundos) antes de qualquer nova citação do −US$ 1.369.
**Landa em:** §1 fato 5, §3 W1, AC-3.

### C3 — HIGH — a matriz papel × modelo contradiz a regra que a governa (Critic-A, Critic-B, Critic-C)

A regra publicada é «effort escala por incerteza de especificação, não por blast
radius». A coluna de modelo particiona por blast radius («builder canônico/KERNEL
→ Opus 5» vs «builder livre/docs → Sonnet 5») e a coluna de effort está invertida
em 2 das 7 linhas: o refutador, que precisa INVENTAR a falsificação, recebe
`xhigh`, enquanto o builder canônico com derivador anchor-exact — o exemplo
canônico de tarefa especificada — recebe `max`. Critic-C acrescenta o caso que a
partição por raio deixa aberto: `.github/workflows/**` é «livre» por cerimônia, mas
os defeitos da W4 são semânticos e mudos (`fail-fast` default, nome de check, um
pass de pytest a menos) — um refutador só os pega se souber a semântica do Actions.

**Severidade acordada:** HIGH. **Mitigação:** trocar o eixo — «o artefato DEFINE
uma pergunta (gate, oráculo, instrumento, censo, critério de aceite) → Opus 5»
versus «o artefato EXECUTA uma derivação com pergunta já fixada → Sonnet 5»;
`.github/workflows/**` entra na linha canônica mesmo sem cerimônia GPG; o
classificador de «tarefa especificada» é publicado, senão a regra não é
falsificável; a razão de recusar Haiku fica escrita.
**Landa em:** §2b (matriz nova no plano), §3 W1, §3 W5-US2.

### C4 — HIGH — o enforce de `model` no spawn não tem validação nem rota de recuperação (Critic-A, Critic-C)

«O dispatcher passa a EXIGIR `model` no spawn (advisory por 30 dias, depois
bloqueante)» é a única superfície bloqueante proposta sem saída nomeada — todas as
outras deste repo têm (`CEO_SOTA_DISABLE`, `CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED`,
`CEO_PAIR_RAIL_VERDICT_OPTIONAL`, `CEO_SENTINEL_UNLOCK`). E o `model` passado no
call site não é validado por ninguém: `assertDispatchable` inspeciona só a STRING
do prompt, e `model` vive no segundo argumento de `agent(prompt, opts)` — um typo
de model id nos 10 literais novos cai em fallback silencioso.

**Severidade acordada:** HIGH. **Mitigação:** nascer como emissão VISÍVEL
(`spawn_model_recorded`, `model=''` na omissão), flip por
`CEO_SPAWN_MODEL_REQUIRED=1` (UNSET por padrão) com tabela would-block/TP-FP na
janela measure-first, e o lint de model id viajando no MESMO patch da W1 — sem ele
a wave troca herança silenciosa por literal silencioso.
**Landa em:** §3 W1, AC-3.

### C5 — HIGH — a OQ-5 é uma sonda, não uma pergunta de debate (Critic-A, Critic-C)

Verificado: `SendMessage` e `ListAgents` não aparecem em NENHUM matcher de
`.claude/settings.json` nem em `.claude/hooks/` fora de testes. O plano diz «nenhum
hook audita essa troca» e está certo, mas não vê a causa de forma: o carimbo de
ciclo de vida por tool-call anda num matcher ENUMERADO, e o precedente do
substrato é que nem tudo é interceptável (`agent()` de Workflow não passa pelo
`check_agent_spawn`, probe `wf_d7af49d9`, `blocked=false`).

**Severidade acordada:** HIGH. **Mitigação:** a OQ-5 sai da W5 e vira sonda de
interceptação na W0 (o PreToolUse dispara para `SendMessage`? um payload plantado é
bloqueado?). Se não dispara, a resposta é «doutrina + emissão voluntária» e isso
fica escrito. Se religar, ALARGAR o matcher — a lição r22 do PLAN-179 é literal:
canal instruction-adjacent fecha por REMOÇÃO, não por enumeração.
**Landa em:** §3 W0-US6, §3 W5-US3, OQ-5.

### C6 — HIGH — a troca entre terminais é incorrelacionável por construção (Critic-A, Critic-C)

A W1 do PLAN-182 separou a cadeia HMAC por projeto, com chave e salt próprios —
decisão correta que não se deve desfazer. A consequência é que uma troca entre dois
repos deixa o evento do emissor num arquivo e o do receptor noutro, assinados por
chaves diferentes: nenhuma cadeia contém os dois lados, logo «A pediu, B fez» não é
verificável. O AC-8 pedia «evento de auditoria emitido» sem notar isso. É exatamente
a superfície onde permission laundering vive.

**Severidade acordada:** HIGH. **Mitigação:** reusar a forma que o repo já tem para
o problema idêntico (`fed_correlation_id` da federação): emitir nos DOIS lados
`peer_message_sent`/`peer_message_received` com `{correlation_id, session_id do
emissor, slug do projeto emissor, nome do receptor, sha256 do corpo}` — o HASH,
nunca o corpo — e o VEREDITO local do receptor (`acted | refused-by-policy |
ignored`). Sem registrar a RECUSA, laundering e cooperação legítima são
indistinguíveis no log. Se o custo for proibitivo, o ADR declara a incorrelação
como limite aceito, no molde do ADR-190.
**Landa em:** AC-8, §3 W5-US3.

### C7 — HIGH — a sonda de concorrência não sustenta a OQ-4 (Critic-A, Critic-B, Critic-C)

O próprio `w0/concurrency-probe-S339.md` marca `n=1 por célula — indicativo, não
p95 de verdade` e diz «repetir 3× antes de citar p95 como fato (AC-2 do plano exige
3/3)». Cinco furos somados: n=1; detector de `429` sem controle positivo («0 erros»
é ausência de sinal num instrumento que ninguém viu morder); tarefa de output ~zero
enquanto o limite é por tokens/minuto; a subida de 5 s para 11 s confunde fila do
cap local, latência sob carga e backoff silencioso; e dois terminais distintos — a
pergunta 3 do Owner — está listado como NÃO testado. Ainda assim a proposta
registrou a OQ-4 como respondida.

**Severidade acordada:** HIGH. **Mitigação:** OQ-4 volta a ABERTA; a sonda repete
com 3 repetições por N, controle positivo do detector, uma célula de output alto e
uma célula de dois terminais × N. Até lá nenhum teto é citado como fato.
**Landa em:** §3 W0, AC-2, OQ-4.

### C8 — HIGH — o AC-6 mede a grandeza errada e é cego a runner-minutos (Critic-B, Critic-C)

Uma matriz que corta 55 % do relógio triplicando os jobs SOBE os runner-minutos
totais, e nenhum AC enxerga isso: é possível passar o AC-6 e piorar a conta. `Ceo`
é larger runner pago por budget de org e o Validate já sobe sete VMs num `push`;
a W4 leva a dez, comendo a folga que o corte A0 do PLAN-184 criou. O modo de falha
por budget estourado não é degradação: TODOS os workflows falham em 2-3 s com zero
steps, o que se parece com bug de código. Critic-C acrescenta que «Validate ≤ 14 min»
derivado do maior job ignora provisionamento (run inteiro 23m27s vs 22m22s do maior
job, ~65 s de overhead com sete VMs).

**Severidade acordada:** HIGH. **Mitigação:** AC-6 ganha segunda perna —
runner-minutos totais ≤ 1,3× do baseline pré-matriz, medidos em 3 runs — e passa a
ser medido em `startedAt`→`completedAt` do RUN, no mesmo evento (`push`); o land é
gated contra o teto do PLAN-184.
**Landa em:** AC-6, AC-11, §3 W4, OQ-8.

### C9 — MEDIUM — o Step 0 barateia o fan-out sem modelar o custo fixo do fan-out (Critic-A, Critic-B)

A sonda da W0 mediu ~95 k tokens de contexto por spawn (prefixo do harness +
`CLAUDE.md` + skills), quase todo cache read. A W5-US1 torna o teste de decomposição
mais permissivo em um eixo (dependência sequencial) sem acoplar esse piso: 14
concorrentes são ~1,33 M tokens de overhead por barreira, antes de qualquer
trabalho. A §2 do plano já contém a frase certa — «paralelismo não cria quota,
gasta-a mais rápido» — sem transformá-la em regra operável.

**Severidade acordada:** MEDIUM. **Mitigação:** a doutrina do Step 0 declara o custo
fixo por spawn (medido, não estimado) como TERCEIRO critério, ao lado de colisão e
dependência: um agente cujo trabalho útil esperado não excede um múltiplo do próprio
overhead de contexto vira chamada de ferramenta no assento.
**Landa em:** §3 W5-US1, AC-7.

## Single-agent insights kept

1. **K1 (Critic-A, R-VP1) — a ROTA papel→model id antes dos literais.** Verificado:
   quatro superfícies decidem papel→modelo hoje — pins de `.claude/agents/*.md`,
   o bloco `MODEL_HINT` de `.claude/scripts/inject-agent-context.sh:281-302`,
   `.claude/dispatcher/routing-matrix.yaml` (`coder_model` por arquétipo) e
   `VETO_HARDCODE`. A W1 ligaria uma quinta grafia a apenas uma delas. É a FORMA
   exata dos defeitos D1-D4 da S322-S327: a ORIGEM tinha dono, a ROTA não.
   Aceito com escopo reduzido: a W0 entrega o CENSO mecânico das superfícies; a
   tabela fonte-única é decisão de escopo do Owner (OQ-7), porque muda o tamanho
   da W1.
2. **K2 (Critic-A, R-VP3) — converter o AC-3 em detector permanente.** Verificado em
   `ADR-144:140`: o roteamento de `opts.model` é «a timeless property and carries no
   forward guarantee». A medição foi em 2.1.237 e a sonda registra 2.1.258 instalado.
   Uma prova pontual no land não protege contra o harness voltar a `inherit` — a
   classe «instrumento verde cuja pergunta envelheceu», já paga duas vezes aqui.
3. **K3 (Critic-A, R-VP5) — o Step 0 vive em 6 sítios, o AC-7 nomeava 2.** Censo
   confirmado: `PROTOCOL.md`, `PROTOCOL.pt-BR.md`, `team.en.md` (raiz do repo, NÃO
   sob `.claude/`), `.claude/team.md`, `.claude/commands/spawn.md`,
   `.claude/skills/core/ceo-orchestration/SKILL.md`, mais menção em `docs/ROADMAP.md`.
   O comando `spawn` e a skill não têm gate de paridade. A skill é Gate-2
   cache-stable: a edição pertence a um closeout.
4. **K4 (Critic-A, R-VP10) — a doutrina nova perde para o mecanismo.**
   `parallelization-by-default/SKILL.md:44-59` já contém o critério 2 («Item B
   depending on Item A's output means serial») com o default OPOSTO três linhas
   acima («>=3 independent items ⇒ CEO MUST dispatch in parallel»), e
   `check_anti_ceo_overhead.py` recomenda dispatch por CONTAGEM, sem nenhum
   predicado sobre dependência. A W5-US1 não adiciona regra ausente: reconcilia
   duas skills sem precedência mais um hook que materializa o viés.
5. **K5 (Critic-A, R-VP9) — a gramática não exprime dependência sequencial.** O
   ADR-191 declara só conjunto de ESCRITA; dependência é aresta escrita→leitura.
   Aceito: linha opcional `CONSUMES:` para as dependências mediadas por arquivo, e
   o ADR NOMEIA o residual — dependências de valor de retorno (finder→refutador do
   `audit-fanout`) seguem fora do alcance mecânico. Sem esse residual escrito, um
   check por arquivo declara fechada uma classe que ele não cobre.
6. **K6 (Critic-B, R-FIN3) — a precedência `inherit` × pin de arquétipo nunca foi
   medida.** É a maior descoberta possível deste plano: se `inherit` vence, o piso
   VETO não é enforcement de runtime — o hook valida o ARQUIVO, nunca o modelo
   SERVIDO, e um `code-reviewer` despachado de um assento Sonnet roda Sonnet com o
   gate verde. Isso é governança, do tamanho do V-block. Se o pin vence, a W3 é
   alavanca de dólar real. Sonda de 3 spawns sem `model:` responde as duas.
7. **K7 (Critic-B, R-FIN4 + R-FIN5) — o A/B tem viés estrutural contra o braço que
   ele testa.** Alternar o assento re-paga um gate-boot frio por dia
   (`F ≈ 97.292` tokens, spread 51,7 % em n=41) e o cache write do 5.1 é o DOBRO do
   Opus 5 — assimetria dentro da métrica primária. Somam-se: os dois braços dividem
   UMA janela semanal e só um tem teto de 50 %, então a ordem de depleção está
   confundida com o efeito de modelo; «minutos até o primeiro bloqueio» é observação
   censada à direita sem tratamento; e «< 4 janelas ⇒ inválido» é piso de
   quantidade, não de poder.
8. **K8 (Critic-B, R-FIN9) — o AC-1 é insatisfazível como escrito.** Exige que
   `ceo-cost.py --since 30d` reproduza o total do relatório 05 com delta ≤ 2 %; o
   que foi construído é `ceo-cost-transcripts.py`, o delta medido é 5,6 %, e a W0
   demonstrou que o número de REFERÊNCIA é que está errado. Reancorar no que a W0
   provou e abrir AC próprio para a integração, que segue aberta.
9. **K9 (Critic-B, R-FIN8) — o critério de morte não é falsificável.** «Dois P1
   consecutivos que o refutador não pegue» não nomeia canal de detecção, janela nem
   denominador — sem canal, o critério só dispara por acidente e ausência de
   resultado vira aprovação. Canal = LAND (bateria + V-block) e CI pós-land; janela
   = 6 waves ou 30 dias; denominador = P1 por wave, comparado ao histórico.
10. **K10 (Critic-B, R-FIN13) — 4 pins de IC uma geração atrás.** Verificado:
    `qa-architect`, `devops`, `performance-engineer` e `llm-finops-architect` em
    `claude-sonnet-4-6` (cache read 50 % mais caro que `claude-sonnet-5`). Entram no
    escopo da W3 — é a mesma assinatura — ou a exclusão fica escrita.
11. **K11 (Critic-B, R-FIN14) — o §1 é auto-contraditório.** O fato 1 aplica a
    correção da W0 (−5,6 %) e o fato 9, três linhas abaixo, cita absolutos vindos
    dos arquivos que a W0 mostrou inflados ~2,8×. As RAZÕES sobrevivem (−14,2 % e
    −38,9 % são contrafactuais sobre o mesmo perfil); os ABSOLUTOS não.
12. **K12 (Critic-B, R-FIN10) — a W3 reverte a recomendação explícita do estudo.**
    Verificado em `05 §5.1`, nota sob a tabela: «Linha 2 é a única onde recomendo
    **não mexer**: o ganho é ~$5/sessão e o custo é uma cerimônia sobre
    `VETO_FLOOR_ALLOWED`». O plano não registra o que mudou de evidência. A sonda do
    K6 decide se a W3 vale $0 ou ~$500/mês.
13. **K13 (Critic-C, R-DEV1) — `strategy: matrix` nasce `fail-fast: true`.**
    Verificado: 17 `if: always()` no `smoke-install.yml` (o relatório 04 diz 8 —
    número velho), e as duas matrizes já existentes no `validate.yml` (`:1578`,
    `:1613`) já declaram `fail-fast: false`. Copiar o padrão da casa e adicionar um
    gate de FORMA que reprove qualquer `strategy.matrix` sem ele.
14. **K14 (Critic-C, R-DEV3) — o split pode perder metade da suíte e ficar verde.**
    Verificado: cada suíte roda em DOIS passes (`-n auto -m 'not serial'` e
    `-m 'serial'`, `validate.yml:461-462`, `544-545`, `575/587`, `1599-1600`).
    Esquecer um pass é uma edição de uma linha sem vermelho nenhum. Baseline
    versionado de node-ids por `--collect-only` e comparação da UNIÃO — verificação
    por CONJUNTO, não por `grep` (lição C3 do PLAN-183).
15. **K15 (Critic-C, R-DEV4) — o estado partilhado do Validate é o TOOLCHAIN.**
    Verificado: `GITHUB_ENV`, `GITHUB_OUTPUT`, `upload-artifact`, `download-artifact`
    e `actions/cache` dão ZERO nos dois workflows — a pré-condição que o plano
    escreveu está satisfeita e é a pergunta errada. O real é `setup-python 3.12` +
    `pip install` no MEIO do job: um split que não os replicar roda o bloco caro
    noutra versão de Python, verde e com outra cobertura.
16. **K16 (Critic-C, R-DEV2) — nome de job é nome de check requerido.** Verificado e
    EXPANDIDO: o literal `Governance, health, contamination, shellcheck` está em
    `docs/BRANCH-PROTECTION.md:104`, `templates/docs/BRANCH-PROTECTION.md:44` **e**
    `templates/.github/workflows/validate.yml.template:33` — três sítios, não dois, e
    dois deles são ENTREGUES a adopters. Configuração server-side não volta com
    `git revert`.
17. **K17 (Critic-C, R-DEV7/8/9) — o bootstrap do Smoke tem de viajar para cada leg.**
    A ordem `fetch tags` → `deepen (--unshallow, guard gens>=2)` → e2e é fail-CLOSED:
    um leg raso reporta `STALE 3` em vez de `STALE 0` — seguro mas CEGO, que é o
    defeito S327b de volta. `Gate-scripts integrity` (ADR-192) hoje protege o job por
    rodar primeiro; em matriz protegeria um leg só. Composite action único
    (`.github/actions/smoke-bootstrap`) + gate que asserta que TODO leg o usa. E as
    cem linhas de derivação do `timeout-minutes: 126` são ledger de medição:
    preservar, dimensionar por leg, nunca copiar 126 quinze vezes.

## Single-agent insights rejected / deferred

1. **REFUTADO em parte — a aritmética do R-FIN1 («`budget_tokens` 21×-49× abaixo»;
   proposta `budget_tokens: 1_250_000_000`).** O campo TEM unidade declarada:
   `PLAN-SCHEMA.md:324` define `budget_tokens` como «CEO-context token range», e
   `850k-1.45M` é coerente com essa unidade e com os outros ~15 planos do repo. A
   crítica compara contra outra grandeza — tokens faturáveis de TODOS os transcripts
   incluindo cache read (96,8 % do volume) —, que é a definição da skill
   `llm-routing-and-finops/SKILL.md:180` («total expected (CEO + sub-agent
   fan-out)»). O defeito real não é do PLAN-186: são DUAS autoridades definindo o
   MESMO campo de formas diferentes, e um instrumento novo medindo uma terceira.
   Adotar 1,25 G tornaria este plano incomparável com todos os outros. **Mantido:** a
   ausência de `tier_mix_estimate` e `budget_usd_estimate` é violação da AC-1 da
   própria skill de FinOps e foi corrigida. **Escalado:** a unidade normativa vira
   OQ-6, decisão do Owner e repo-wide.
2. **REFUTADO em parte — «o diagnóstico *não há política, há herança* é FALSO»
   (Critic-A).** As quatro superfícies existem (verificadas), mas três delas não
   governam o caminho de despacho que a W1 toca: os pins de `agents/*.md` valem no
   rail nativo, `routing-matrix.yaml` e `VETO_HARDCODE` alimentam o dispatcher
   aprendido, e `MODEL_HINT` é TEXTO num prompt gerado, não binding. Para o
   `agent()` de workflow e para o `Agent` direto, a herança é real e o diagnóstico
   sobrevive. O que é falso é a forma absoluta «ausência de decisão»: existe decisão,
   em quatro grafias, nenhuma pinada nem medida. Registrado assim no plano.
3. **DEFERIDO — ADR registrando a escolha de roteamento por REGRA e não por
   classificador aprendido (RouteLLM).** Advisory de um só crítico, sem risco de
   correção. Entra na W5-US2 se sobrar orçamento; não bloqueia.
4. **DEFERIDO — `MODEL_HINT` de VETO emitindo `opus` (alias de família) enquanto o
   pin aponta `claude-fable-5`.** Verificado em
   `inject-agent-context.sh:281-282`. É contradição viva, mas a cura pertence à rota
   única (K1/OQ-7): curar o sítio isolado agora cria a sexta grafia. Nomeado no plano
   como consequência da OQ-7.
5. **DEFERIDO — cura textual dos 2 sítios «INERT» da W0.** Nenhum crítico tocou;
   segue como carona em cerimônia, sem mudança.
6. **NÃO ALTERADO — a W6 (adapter opcional).** Nenhum dos três críticos a examinou.
   Permanece como estava; um round futuro que a queira revisar tem de pedir foco
   nela.

## Plan adjustments

| § do plano | mudança |
|---|---|
| frontmatter | `budget_tokens` com unidade declarada + `budget_tokens_billable_est` + `budget_usd_estimate` + `tier_mix_estimate` em dois blocos (assento/subagente) + `tier_mix_rationale`; `depends_on` cita a dependência da cerimônia `wave-fable51` |
| §1 (tabela de contexto) | fatos 5 e 9 anotados RAZÃO vs ABSOLUTO; fato 5 perde o status de fato até re-derivação |
| §2 | pergunta 2 passa a apontar a OQ-4 REABERTA em vez de citar o teto como medido |
| §2b (novo) | matriz papel × modelo × effort entra no plano com o eixo trocado (DEFINE pergunta vs EXECUTA derivação) + razão da recusa de Haiku |
| §3 W0 | sonda de concorrência re-desenhada; +US4 (precedência `inherit` × pin), +US5 (censo de superfícies de roteamento), +US6 (sonda de hookabilidade de `SendMessage`) |
| §3 W1 | AC dividido; rota de recuperação nomeada; lint de model id no mesmo patch; detector permanente de roteamento; critério de morte com canal/janela/denominador |
| §3 W2 | contrabalanceamento ABBA; custo de troca; janelas censadas; MDE; eventos de bloqueio primários |
| §3 W3 | sítios derivados mecanicamente; DOIS ids no piso; sha256 congelado; 4 pins de IC; rollback declarado |
| §3 W4 | `fail-fast: false` + gate de forma; baseline de node-ids; composite bootstrap; nome de job + 3 sítios; toolchain com assert; runner-minutos |
| §3 W5 | 6 sítios do Step 0; `parallelization-by-default` + hook no escopo; `CONSUMES:`; custo fixo por spawn; correlation id |
| Acceptance criteria | AC-1..AC-8 reescritos; +AC-10, AC-11, AC-12 |
| Open questions | OQ-4 REABERTA; +OQ-6, OQ-7, OQ-8 |
| Riscos | +armadilha do `set-quality-profile.sh`; +budget de Actions estourado se parece com bug de código |
| Progress log | entrada «round 1 sintetizado» |

## Round verdict

**RUN-ANOTHER-ROUND**

Regra aplicada: risco levantado por 2+ críticos ⇒ o plano MUDA (nove findings, C1-C9,
todos aplicados); risco de um só crítico ⇒ decisão escrita do sintetizador (17
mantidos com verificação em disco, 6 rejeitados ou deferidos com razão).

Por que não PROCEED: os três críticos retornaram `ADJUST` e o plano saiu do round
com estrutura diferente — a W0 ganhou três sondas, o AC-3 virou dois, a W3 dobrou de
raio e a W4 ganhou cinco pré-condições mecânicas. A doutrina desta casa é que rodada
limpa prova a SUPERFÍCIE revisada, não o entregável; o round 2 tem de revisar o
plano REVISADO, não o que foi criticado.

Por que não ESCALATE-TO-OWNER: nenhuma das três OQs novas bloqueia o avanço. A W0 é
livre e responde sozinha às perguntas que decidem o tamanho de W1 e W3. As decisões
do Owner (OQ-6 unidade de orçamento, OQ-7 escopo da rota única, OQ-8 orçamento de
runner) podem ser colhidas em paralelo ao round 2, e só a OQ-7 muda o escopo de uma
wave livre.
