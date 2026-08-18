# VP Engineering — PLAN-181 round 1

## Verdict

**ADJUST** — a tese ("adotar com wrapper, nunca cru") está certa, mas o
mecanismo escolhido para o wrapper é o errado pela matriz canônica do
próprio repo, e o W0 executa a capacidade Tier-C antes de satisfazer o
pré-requisito que o ADR-125 impõe para ela.

## Summary

Verifiquei em disco os cinco pilares do plano. Três se sustentam e dois
caem:

- **Sustenta-se:** /loop é Tier-C nato pelo critério 1 do
  `ADR-125:211-218` ("spends tokens autonomously without per-action user
  prompt"); a prescrição órfã existe mesmo
  (`docs/AUTONOMOUS-LOOP-GUIDE.md:19` prescreve `/loop 24h
  /nightly-hygiene`); e o kill-switch único
  (`CLAUDE_CODE_DISABLE_CRON`) é o que a doutrina reconhece
  (`AUTONOMOUS-LOOP-GUIDE.md:169-173`).
- **Cai (P1):** "wrapper = SKILL". A matriz canônica marca *Recurring
  scheduled work* como Skill ❌ / Hook ❌ / Slash cmd ✅
  (`docs/MECHANISM-SELECTION.md:63`), e o molde que o plano invoca —
  night-mode — **não é uma skill**: é comando + script + entrada no
  `_CANONICAL_GUARDS` + deny em `settings.json` + matcher de Bash. Não
  existe `.claude/skills/core/night-mode/`.
- **Cai (P1):** "acionar `_lib/cost_envelope.py` por tick" como se fosse
  um call-site. Os DOIS trilhos de budget hoje wired são cegos a um tick
  de /loop (evidência no risco 4).

O plano também trata como OQ aberta (OQ-2) uma composição que é P0:
`night-mode on` + `/loop` = escrita não-atendida sem prompt por ação.

## Risks

### P0-1 — W0 roda a capacidade Tier-C antes do manifesto que a autoriza

`ADR-125:230-233`: *"Cost-envelope manifest: each Tier-C opt-in MUST
declare in its plan §Cost section: (a) per-invocation token estimate,
(b) daily burn cap, (c) cost-cap enforcement mechanism."*
`PLAN-181-loop-governed-adoption.md` **não tem seção §Cost** (as seções
são Origem / Waves / Riscos / How to continue); o plano adia o §Cost para
o W3 (`:84`), que é a ÚLTIMA wave. W0 (`:34-46`) é a PRIMEIRA e já gasta
tokens em ticks recorrentes.

O plano se auto-concede uma dispensa em `:36-38` ("Owner PRESENTE (não é
autonomia prolongada ⇒ não exige o opt-in Tier-C ainda)"). Essa dispensa
não existe: `grep -i "attended|owner present|presente|short-lived"` sobre
`ADR-125-risk-tiered-defaulting-doctrine.md` retorna **zero** ocorrências,
e o critério 1 do Tier C é sobre *ausência de prompt por ação*, não sobre
presença do Owner. `ADR-133:346-348` reforça: o invariante Tier-C é
"Owner physical consent (GPG sentinel + env flag) + cost-envelope
manifest", preservado sem exceção atendida.

### P0-2 — composição night-mode × /loop é P0, não uma pergunta aberta

O plano lista isso como OQ-2 (`proposal.md:65-67`). É um risco de
composição concreto e verificável: `/night-mode on` grava
`permissions.defaultMode: "acceptEdits"` no overlay
(`.claude/commands/night-mode.md:11-13`). Um tick de /loop numa sessão
assim herda autonomia de ESCRITA e não passa por prompt por ação. O
produto das duas capacidades default-OFF é uma terceira capacidade que
ninguém habilitou explicitamente.

### P1-3 — mecanismo errado para o wrapper (OQ-3)

`MECHANISM-SELECTION.md:63` já responde OQ-3, e responde contra o plano.
Reforço em `§5:238-248` ("skills são consultadas probabilisticamente… uma
regra que DEVE valer precisa de hook") e `§5:258-266` ("enforcement
belongs in hooks").

O molde citado prova o ponto por construção. Night-mode fecha o mesmo
tipo de gap com **quatro** artefatos, nenhum deles skill:

| Camada | Arquivo |
|---|---|
| Superfície do operador | `.claude/commands/night-mode.md` |
| Lógica | `.claude/scripts/night-mode.py` |
| Guarda canônica | `check_canonical_edit.py:344-345` (script + estado no `_CANONICAL_GUARDS`) |
| Trilho mecânico | deny em `settings.json` + `check_bash_safety._e4_check_posture_toggle_invocation` |

W2.6 ("tick jamais edita Gate-1 files, hooks/, ADRs, SPEC", `:70`) é o caso
mais claro: é exatamente a classe "no floats in financial math" do
`MECHANISM-SELECTION.md:132-150` — hook, com skill só reforçando.

### P1-4 — nenhum trilho de budget existente enxerga um tick

Medido em disco:

- `check_cost_envelope.py` está wired em **PreToolUse / matcher `"Bash"`**
  (`.claude/settings.json:313-318`) e o comentário do próprio wiring diz
  que ativa "ONLY when BOTH `CEO_SWARM=1` AND command body matches a real
  swarm coordinator signature". Um tick de /loop não roda o coordinator ⇒
  **inerte**.
- `check_budget.py` está wired em **PreToolUse / matcher `"Agent"`**
  (`.claude/settings.json:255-262`) — só dispara em spawn de agente, e é
  advisory ("ALWAYS allows in Sprint 11 (State 0 advisory)").

Logo W2.2 (`:66`) não é "acionar a lib": é criar (ou estender a predicate
de ativação de) um hook sob `.claude/hooks/*.py`, que está no
`_CANONICAL_GUARDS` (`check_canonical_edit.py:139`) ⇒ cerimônia GPG + ADR
por hook novo (`MECHANISM-SELECTION.md:366-369`). O budget de 60-100k para
W2 não reflete isso.

### P1-5 — o ponto de interceptação do tick nunca foi medido

W2.1/W2.2/W2.6 pressupõem que existe um lugar mecânico onde o tick passa.
`UserPromptSubmit` está wired em `.claude/settings.json`, e é o candidato
óbvio — mas **não há medição** de quais eventos de hook um tick de /loop
dispara. Nenhuma AC do plano cobre isso, e todo o desenho do W2 depende da
resposta. Sem isso, W2 pode nascer como o `additionalContext` do PostCompact
no ADR-153: canal presumido, nunca provado
(lição `feedback-event-probe-is-not-channel-probe`).

### P1-6 — evento novo sem consumidor (OQ-4)

Precedente que funciona: `swarm_iteration` tem consumidor real —
`swarm_circuit_breaker.py:132` conta os eventos e `audit-dashboard.py:881`
os agrega. Precedente que falhou: o HMAC de `execution_context` —
`grep -rn "execution_context" --include="*.py" .claude/hooks/*.py
.claude/scripts/` retorna **zero produtores**, exatamente como o plano
admite em `:73-75`.

W1 (`:48-57`) e W2.4 (`:68`) criam eventos sem nomear consumidor. Isso é a
classe E4 que a OQ-4 teme — e a resposta não é "cortar W1", é "W1 landa com
o consumidor na mesma wave".

### P2-7 — `session_crons` é opcional; ausência é ambígua

`.claude/data/hook-schema-2.1.220.json:88` declara
`"session_crons": "array<CronSummary>?"` — campo **opcional** em Stop e
SubagentStop. Um inventário que loga só o conteúdo não distingue "zero
loops vivos" de "esta versão do harness não emitiu o campo". Inventário que
mente por omissão é a classe "instrumento verde cuja pergunta envelheceu".

### P2-8 — PLAN-135 não existe em disco; e o ask citado não é o ask real

`find .claude/plans -maxdepth 2 -name "*135*"` e
`git log --all -- '.claude/plans/PLAN-135*'` retornam vazio. A doutrina
citada existe (`MECHANISM-SELECTION.md:290`, `AUTONOMOUS-LOOP-GUIDE.md:7`),
mas o que ela pede é literalmente *"inventory it alongside the swarm layers
in §6"* (`AUTONOMOUS-LOOP-GUIDE.md:171-173`) — inventariar o KILL SWITCH na
tabela de docs. W1 converte isso em evento HMAC novo + bump de schema SPEC.
É inflação de escopo sobre uma referência dangling.

### P2-9 — OQ-1 já está respondida pela doutrina canônica

`AUTONOMOUS-LOOP-GUIDE.md:24`: *"recurring → `/loop`; vigil/approval →
Monitor + PushNotification"*, e a linha `:22` marca o vigia pós-cerimônia
como **PRESCRIBED** para Monitor. O W0 escolhe /loop para a forma que a
doutrina atribui ao Monitor — e a S311/S312 já refutou empiricamente
(`proposal.md:31-33`). O candidato sugerido ("exercita ScheduleWakeup") é
uma sonda de substrato, não um piloto de vigia: pertence ao W1.

### P2-10 — `.claude/commands/*.md` não é guardado como CLASSE

Só `council.md` está no `_CANONICAL_GUARDS`, por nome
(`check_canonical_edit.py:332`). Se `/loop-governed` virar comando, o
GATILHO de uma capacidade Tier-C nasce ordinariamente editável. E o
comentário logo acima (`check_canonical_edit.py:325-330`) já diagnosticou
essa exata classe: *"the exact-path entry guarded the INSTANCE, not the
CLASS"*. Guardar `loop-governed.md` por nome repete o defeito que o
PLAN-156-FOLLOWUP F3 fechou.

## Must-fix

1. **Adicionar §Cost ao PLAN-181 ANTES de qualquer wave** com as três
   alíneas do `ADR-125:230-233`. Sem ela nenhuma wave que gaste tokens em
   tick pode rodar (fecha P0-1).
2. **Remover a dispensa "Owner presente"** de `:36-38`. Ou W0 vira
   estritamente `$0` (nenhum tick de modelo — só script + Monitor), ou W0
   exige o opt-in Tier-C completo. Não há terceira via em ADR-125.
3. **Reescrever W2 como composição de 3-4 artefatos, não como uma skill**
   (fecha P1-3): comando `.claude/commands/loop-governed.md` (superfície),
   `.claude/scripts/loop_governed.py` (lógica) **adicionado ao
   `_CANONICAL_GUARDS`**, e um hook novo para W2.2/W2.3/W2.6
   (enforcement). A SKILL, se existir, carrega só doutrina — nunca as ACs
   de enforcement. Reajustar o budget de W2 (hook novo = ADR + cerimônia).
4. **Guardar `.claude/commands/**/*.md` por CLASSE** ou justificar em ADR
   por que a instância basta (fecha P2-10).
5. **Mover a medição "quais eventos de hook um tick dispara" para W1 como
   AC bloqueante de W2** (fecha P1-5 e converte OQ-4 em sequência
   justificada: W1 é o input de seleção de mecanismo do W2, não sonda
   órfã).
6. **Todo evento novo (W1, W2.4) landa com seu consumidor na mesma wave**,
   com controle positivo que prove o consumo (fecha P1-6).
7. **W2.1 deve checar a composição com `acceptEdits` e RECUSAR
   fail-closed** — um loop governado não arma sob posture `acceptEdits`
   sem um segundo ack explícito (fecha P0-2). E a recusa precisa de
   controle positivo, não de `return 0` com aviso (o próprio plano
   antecipa isso em `:92-94` — aplique a W2.1).
8. **Registrar a decisão de mecanismo num ADR novo** (ou emenda a
   ADR-125 §Tier C acrescentando `/loop-governed` à tabela de plans in
   Tier C, `:227-234`). W3 hoje só prevê debate + sentinel; capacidade
   Tier-C nova sem ADR contraria `MECHANISM-SELECTION.md:45`.

## Nice-to-have

- W2.3 ("mesma classe de achado em 2 ciclos ⇒ parar") precisa de uma
  CHAVE DE CLASSE estável para comparar achados entre ciclos. Sem chave
  derivada mecanicamente, "mesma classe" é julgamento do modelo — e a
  AC-W0.2 do próprio plano (`:45-46`) já proíbe isso na outra ponta.
- Kill-file além do env var: o swarm tem `touch .claude/swarm-kill`
  (`AUTONOMOUS-LOOP-GUIDE.md:159`). `CLAUDE_CODE_DISABLE_CRON` é env de
  processo — não mata um loop armado em outra sessão. Um sentinel em disco
  é a única rota de parada para o Owner que não sabe qual sessão armou o quê.
- `eta_calendar` já está no frontmatter (`:14`) — bom, e é a doutrina do
  PLAN-180. Manter.

## Unseen

- **Regra do 10x.** `cost_envelope` chaveia estado por
  `project_path + user_id + date` (`cost_envelope.py:132`). Com N loops
  governados simultâneos, todos compartilham UM envelope: o primeiro a
  esgotar mata os outros, e não há atribuição por loop. Nenhuma AC cobre
  N>1. A resposta pode ser "max 1 loop governado por projeto" — mas então
  isso é um invariante que precisa de enforcement, não de suposição.
- **Reversibilidade / blast radius.** O plano não classifica a
  reversibilidade da decisão. Adicionar um hook novo no PreToolUse é
  MEDIUM (reverter = cerimônia); habilitar autonomia recorrente é o
  eixo M3 "Distância de Irreversibilidade" da auditoria S302b. Falta a
  seção Blast Radius que a própria skill de arquitetura exige.
- **Acoplamento com PLAN-179 é mais forte do que o plano admite.** O
  achado do 179 é que governança decai 30-59% após compactação. Um loop de
  24h VAI compactar. A restrição mais sujeita a decaimento é exatamente
  W2.6 (proibição de tocar governança) — e o plano a implementa na camada
  mais frágil (prompt/skill). Esse é, sozinho, o argumento mais forte para
  hook. Recomendo tornar W2.6 dependência dura de PLAN-179 W-Constraint
  Pinning, ou implementá-la só em hook.
- **Modo degradado.** O que acontece quando o hook de enforcement falha
  por INFRA no meio de um loop não-atendido? A doutrina do repo é
  fail-open on infra (CLAUDE.md §4) — o que aqui significa "o tick
  prossegue sem budget". Para uma capacidade Tier-C isso pode precisar da
  exceção deliberada do ADR-186 (fail-CLOSED com rota de recuperação).
  Decidir explicitamente, não herdar por default.

## What I would NOT change

- A LINHA DURA do W0 (`:41-42`): o loop jamais corta tag, executa GA-CUT
  ou landa. Correto e não-negociável.
- AC-W0.2 (`:45-46`): check determinístico por exit code, nunca julgamento
  do modelo. É a doutrina "espere pelo ARTEFATO" aplicada certo.
- A honestidade declarada sobre o HMAC sem produtores (`:73-75`) — está
  verificada em disco e é exatamente o tipo de claim que o repo costuma
  inflar. Manter a redação.
- Primeiro consumidor `nightly-proposals.py` → `morning_ledger.py`
  (`:77-79`): $0 e ratificação Owner-only é a escolha certa de primeiro
  caso real.
- Teto de iterações + troca de alvo (W2.3): é a lição-mãe da S296 aplicada
  corretamente, e a literatura citada sustenta.
- O veredito de origem ("adotar com wrapper, nunca cru") — a crítica acima
  é sobre QUAL wrapper, não sobre se deve haver um.

DONE_WITH_CONCERNS
