---
id: PLAN-196
title: "Backlog consolidado da v1.5 — escopo e condições herdados"
status: draft
created: 2026-11-01
owner: CEO
depends_on: [PLAN-167, PLAN-168, PLAN-169, PLAN-171, PLAN-190]
related_commits: []
level: L3
budget_tokens: "a reestimar por onda antes da execução; estimativas originais preservadas nas fontes"
budget_sessions: "a reestimar por onda antes da execução"
context_risk: high
external_wait: "Decisões, congelamentos, evidências de fechamento e assinaturas do Owner herdados das fontes; a consolidação não libera execução"
tags: [backlog, consolidation, v1-5, governance]
---

# PLAN-196 — Backlog consolidado

## Context

Em 2026-11-01, o CEO/Owner aprovou a consolidação proposta pela PISTA 1:
este plano assume integralmente o escopo ainda pendente das doze fontes abaixo,
que passam a `superseded`, com `superseded_by: PLAN-196`, conforme
[PLAN-SCHEMA §11](PLAN-SCHEMA.md#superseded-status-added-plan-113-w2).
O trabalho entregue, os commits, as datas originais e as decisões permanecem
nas fontes. A data deste novo plano registra a consolidação, não uma nova
data de início das implementações antigas.

## Goal

Manter um destino único e executável para as pendências, sem perder critérios
de aceite, dependências, recusas, congelamentos ou evidências. O rótulo v1.5
organiza o backlog; não altera a versão de entrega já decidida para uma onda
nem promete que todos os itens entrarão no mesmo release.

## Scope and source contracts

Cada fonte é incorporada integralmente por referência quanto ao seu escopo
ainda aberto: waves, ACs, perguntas abertas, limites, regras de parada,
condições externas e anexos vinculados. As seções seguintes são um índice de
execução, não uma redução desses contratos. Decisões posteriores registradas
na própria fonte prevalecem sobre checkboxes e propostas históricas; uma caixa
aberta não reabre uma opção explicitamente recusada. Divergências sem decisão
continuam pendentes para o Owner antes da onda afetada.

| Frente | Fonte incorporada | Dependências e vínculos preservados |
| --- | --- | --- |
| P169-mensageria | [Sondas SendMessage](PLAN-169-FOLLOWUP-sendmessage-probes.md) | PLAN-169 AC-5, pernas 2–4; P186 AC-15; decisão do Owner de 2026-10-12 e OQ-2 adiada |
| P175 | [Skills, poda e descoberta](PLAN-175-skills-pruning-discovery.md) | PLAN-171; Fase 2 separada; cerimônias W0b/W1/W2b/W4c |
| P176 | [Atualização de modelos](PLAN-176-model-currency-refresh.md) | PLAN-169; W1c espera a W4b de P186; ADR-149/180/192 |
| P183 | [Adopter fitness](PLAN-183-adopter-fitness.md) | PLAN-167/168; mapa de colisões e vagas com PLAN-194/195 |
| P186 | [Modelo operacional](PLAN-186-orchestrator-operating-model.md) | PLAN-169; [LEDGER](PLAN-186/LEDGER.md), unidade S363 |
| P186-censo | [Censo runtime](PLAN-186-FOLLOWUP-census-runtime.md) | Fechamento do escopo pai P186; W0 já entregue, W1 aberta |
| P186-hint | [Descoberta desde a raiz](PLAN-186-FOLLOWUP-hint-discovery-walk-from-root.md) | Fechamento do escopo pai P186 e gates canônicos |
| P186-sentinel | [Fronteira do sentinel](PLAN-186-FOLLOWUP-sentinel-gpg-verification.md) | Fechamento do escopo pai P186; decisão S363; backlog 1.4.4, item 11 |
| P188 | [Toolkit de cerimônia](PLAN-188-shared-ceremony-toolkit.md) | P186/W6a como piloto; congelamento Q13-c |
| P189 | [Qualidade da cura e instrumentação](PLAN-189-cure-quality-and-rail-instrumentation.md) | Congelamento até o gatilho de GA da W7 do PLAN-194 |
| P190-audit | [Ações auditadas do workflow](PLAN-190-FOLLOWUP-audit-actions.md) | PLAN-190; registro de ações, scrub e SPEC |
| P191 | [Torneio, cascata e triagem](PLAN-191-cheap-brain-tier-tournament-cascade-triage.md) | Pré-registro, decisões do Owner, medições e gates W0–W4 |

## Approach

As dependências entre fontes migradas tornam-se dependências entre as frentes
identificadas acima. Elas não dependem de este plano inteiro chegar a `done`.
O gate que exigia o pai `done` continua exigindo o fechamento comprovado de
**todo o escopo herdado daquele pai**, registrado aqui com seus ACs e evidências;
`superseded` sozinho nunca satisfaz esse gate. Antes de executar um followup,
registrar esse fechamento e a correspondência com o contrato original.

Debates, vetos, assinaturas e limites de WIP continuam valendo por onda. Uma
assinatura existente só vale para seu conteúdo e escopo originais. O Owner
aprovou a migração documental, não um descongelamento geral, novos gastos,
mudanças de roteamento ou uma autorização canônica coletiva. Ao abrir cada
onda, conferir o código integrado e os anexos vigentes, registrar o delta
restante e reestimar o esforço; não somar estimativas históricas sobrepostas.

## Items

### P169-mensageria — Sondas e doutrina de mensagens

Incorporar as pernas 2–4 do AC-5 do PLAN-169, com todos os critérios e
registros do [followup](PLAN-169-FOLLOWUP-sendmessage-probes.md). A perna 1
continua no AC-15 de P186, já herdado acima; coordenar o matcher, sem duplicá-lo.

W1 preserva as seis sondas W4.2.0: (a) `UserPromptSubmit` para mensagens de
outra sessão, terminal ou máquina, distinguindo ausência de disparo de falha
antes da emissão; (b) `SubagentStart` para `agent()` de Workflow; (c) roteamento
entre máquinas, reply-only versus name-first; (d) efeito de `refuse` sobre
filhos da própria sessão; (e) visibilidade HMAC de turnos nascidos de mensagens
recebidas; (f) `PreToolUse` de `SendMessage` emitido por subagentes/peers,
coordenado com P186 AC-15. Cada sonda exige sua linha de evidência.

W2 ocorre em clone descartável, nunca no repositório canônico. Medir as três
células aprovadas pelo Owner em 2026-10-12: `refuse` sem turno; `hold` sem turno
imediato, registrando retenção e entrega após a troca para `accept`; `accept`
como controle positivo. Revalidar a chave e a precedência de settings de
projeto no Claude Code vigente antes da medição. Os textos históricos do
binário não comprovam comportamento; OQ-1 só fecha com as três células medidas.

W3 exige ADR aceito e cerimônia com a decisão sobre visibilidade das tentativas
recusadas; uma postura diferente de `refuse` deve declarar explicitamente o
escopo degradado de auditabilidade. Preservar OQ-2 adiada pelo Owner: decidir
sobre o adopter com `accept` explícito antes de acrescentar qualquer linha em
template. W1/W2 podem ser medidas sem essa resposta, conforme a fonte. OQ-3
mantém a estimativa de tokens e sessões para o refinamento. A migração não
declara sondas, controles nem ADR já entregues.

### P175 — Skills, poda e descoberta

Preservar todas as ACs abertas e OQs da fonte, incluindo W0b/AC-0.6 (referência
morta do roteador), W1/AC-1.4–1.6 (contrato e injetor), W4/AC-4.2 (contagens
derivadas e manifesto ADR-192), W2 (poda/consolidação) e W3/AC-3.0–3.4
(ownership do domain-pack, perfis e instalação com/sem domínio). W4c deve
preceder ou acompanhar as contagens conforme o apêndice mais recente.

W2a mantém os controles de cadeia íntegra ou lista de arquivo vazia,
restauração em árvore descartável e redução medida de tokens. A recusa de
poda com cadeia danificada e as decisões do Owner OQ-3/OQ-7 permanecem.
W0a e demais entregas comprovadas não são refeitas. A Fase 1 termina no
baseline; a re-medição pertence ao followup externo indicado abaixo.

### P176 — Atualização de modelos

A Onda 6B de 2026-11-01 concluiu a admissão por família e piso de VETO do
PLAN-176, agora `done`. A exigência histórica de GPG por versão foi substituída
pelo ADR-149 A4. Os itens abaixo conservam apenas as entregas remanescentes;
esta conclusão não prova feed, preços, medidas ou cerimônias ainda pendentes.

Manter W0b (feed upstream opcional, desligado por padrão), resíduos de W1a
(lint e grandfather list), W1b (registro T, resolver e ADR-180), W1c
(manifesto/CI), W2a (proposta auditada) e W3b (varredura noturna). Preservar
as entregas já registradas de W0a, preference data e W3a. W1b/W1c exigem
cerimônias próprias; a W1c só parte depois da W4b efetivamente integrada.
O nome antigo `w4b-ci-matrix` deve ser lido com a sucessão para `w4b-gates-v2`
registrada no LEDGER de P186, sem presumir que esse land já aconteceu.

Também continuam abertos P176-EXPIRY (`cost_table_valid_until`), a decisão de
renovação/preços e o followup ainda a criar; autenticação do conjunto vermelho
C4; K6–K10/C5; e as OQs do §5b. Essas OQs não bloqueiam as rotas baratas
quando a fonte assim declara. A rota cara de `audit_emit.py` conserva as
decisões pendentes sobre corte, AC de auditoria e W0b, incluindo o campo
`decision` exigido por `refused_destination_emits_event`. Fusão automática
continua fora de W2a e depende de ADR próprio ratificado.

### P183 — Adopter fitness

Seguir a seção **Waves S359**, seu mapa de colisões e as decisões posteriores:
W1 antiga exige rederivação/divisão W1a/W1b; W7a/W7b cobrem A1; W8 cobre
A7/A2 e `_dispatch.md`; W9a/W9b cobrem A4/A5; W10 cobre o validador de skills.
Preservar AC-11–16, as ACs residuais anteriores e o critério de `done` S361.
A3 permanece atribuída ao PLAN-195. As entregas e ratificações de W2/AC-2,
W5 e W5-b permanecem como evidência nas fontes, não como trabalho novo.

O [approved da W7](PLAN-183/debate/w7-round-2/approved.md), as vagas e os
gates com PLAN-194 continuam obrigatórios: W5b antes da W1 correspondente,
W7a antes dos dependentes que a exigem; W7b/C37 e demais itens destinados à
1.4.4 mantêm essa decisão. Preservar P4 forensic opção (i), fixtures de
harness replay e a asserção de PRESENÇA no packlist npm (C8), após o GA e o
LAND W4 do PLAN-194 e antes da unificação. A purga no adopter (OQ-18) continua
sendo uma ação do Owner em sessão própria. Os resíduos W2/W3-P1/W4/W5-b e os
followups da C10 continuam sujeitos ao critério de fechamento da fonte.

### P186 — Modelo operacional

O [LEDGER, unidade S363](PLAN-186/LEDGER.md) preserva a fila W4b
(`w4b-gates-v2`, sucessor do pacote rescindido) → W6a adapter → W1
re-arquitetada. W1 exige resposta à OQ-11 e pacote novo; a referência de pin
é a Emenda 3 do ADR-149, não o alvo antigo de Fable 5.1. W0/W4a e ACs
fechadas com evidência no LEDGER não são reabertas.

Incorporar também todos os resíduos W2–W6, W-ROTA/AC-17 e demais ACs/OQs
abertas da fonte: medições do assento, despacho, cobertura e custo da CI por
classe de runner, doutrina/coordenação entre terminais e integração do adapter.
Os limites aceitos de AC-12 permanecem vinculados aos followups. A medição
histórica do Validate não prova o alvo do Smoke; os gates exigem as medições
definidas na fonte. W4b e W6a seguem pelo molde por onda enquanto P188 estiver
congelado; não esperar um toolkit que o Owner retirou do caminho crítico.

### P186-censo, P186-hint e P186-sentinel

- **Censo:** W0/piloto já entregue; W1/AC-F1 amplia o conjunto de donos
  reaberto na nota S340, com leitores por tipo e tabela derivada, sem inventar
  alias→modelo. AC-F2/F3 permanecem cumpridas conforme a fonte. Conservar
  todas as curas e bordas posteriores; uma rodada com três ou mais P1 novos
  da mesma classe aciona a regra de parada e decisão do CEO.
- **Hint:** manter AC-1–6: limites de tempo e de diretórios, truncagem
  propagada como incompletude fail-closed, provenance persistida sem seguir
  symlinks, opt-in `/`, bateria antes/depois e cerimônia de sentinel/kernel
  com escopo integral e bump. S363 escolheu estender `hint_provenance_recorded`.
  Continuam os bloqueios da fonte, o fechamento do pai e o intervalo RC→GA.
- **Sentinel:** a opção GPG no CI foi recusada; AC-1–5 não são reativadas.
  AC-0 permanece entregue/ratificada. AC-7 exige censo e redesenho das bordas
  fail-open (incluindo symlink rastreado e nomes não-UTF-8), com vínculo ao
  [backlog 1.4.4, item 11](PLAN-194-FOLLOWUP-v1-4-4-backlog.md). O pacote
  estacionado fora da main não é entrega. AC-6 (índice × worktree) continua
  sem decisão; não inferir sua resolução da recusa da opção GPG.

### P188 e P189 — Congelamentos preservados

P188 permanece congelada pela Q13-c até **nova decisão do Owner**, sem gatilho
automático. Nenhuma wave ou nova rodada de debate abre por esta consolidação.
Continuam incorporados W0/W1/W0c, leitor de manifesto, SIGN/LAND/finalize,
gates, controles falsificáveis, migrações, medição do rail, ADR e manifesto
ADR-192. Os dependentes seguem os moldes por onda autorizados.

P189 conserva o gatilho verificável de GA da W7 do PLAN-194, com a versão
decidida pelo diff do SPEC. W0 não landou segundo o registro da fonte.
W0–W3 cobrem regra de cura por classe, controles proporcionais, telemetria por
rodada com desconhecidos ausentes (nunca zero) e preservação do relato e da
severidade originais. As OQs respondidas continuam válidas. A regra prática
no CLAUDE.md e os materiais de re-pin excluídos do congelamento preservam
seu tratamento original.

### P190-audit — Eventos do workflow

W1 registra `workflow_launch_recorded`, `workflow_resume_guard`,
`workflow_run_bound` e `workflow_run_orphan`, com os campos, enums, hashes,
contagens e scrub fechados da fonte; nenhum conteúdo de `args`. W2 emite
no hook com import na chamada e fail-open na falha de emissão. W3 cruza
`launches.jsonl` (`launch`, `bind`, `orphan`, `force_token`) com a cadeia HMAC
e o relatório. Se isso exigir mudança de esquema além de acrescentar linhas
ao SPEC, parar e abrir ADR. A migração não declara essas waves entregues.

### P191 — Medições de tier, cascata e triagem

W0-pre tem as curas registradas no
[relatório S363](PLAN-191/w0/w0-pre-minimal-response-S363.md); seus residuais
continuam declarados e nenhuma tarefa foi excluída. W0 ainda requer
pré-registro, data/noite do Owner, tabela tarefa/modelo/repetição e decisão
de financiamento de W0.c. W0.b foi financiado; manter a partição de W0 ∪ W0.b.
W1 compara Opus direto, cascata e tier na segunda noite aprovada; o perímetro
financeiro não desce de tier.

Preservar a regra de parada de W2: zero qualificadas encerra W2; uma ou duas
permitem reaplicar a regra uma única vez ao conjunto unido, abrindo só com
pelo menos três; três ou mais permitem abrir. W2 deve superar W1-B em custo
à mesma pass rate; lane Jev exige ganho mínimo de cinco pontos percentuais
contra o baseline local. W3 depende da rotulagem do Owner e compara os quatro
braços com os critérios pré-registrados. W4 requer uma compactação real
comparável. As [decisões S355](PLAN-191/owner-decisions-S355.md), o opt-in de
egresso TypeSafe (sem flag, pular braços Jev), os adendos textuais e os limites
de roteamento continuam válidos; uma lane/política nova exige plano e cerimônia.

## Linked work outside this consolidation

Estes documentos mantêm seus estados e escopos próprios. Seus vínculos não
são apagados nem considerados satisfeitos por um pai ficar `superseded`:

- [P175 Fase 2](PLAN-175-FOLLOWUP-fase2-remedicao.md): fechamento da Fase 1,
  W1b integrada e pelo menos 30 `agent_spawn` posteriores; decidir pelo
  predicado `10 × unknown > total`, sem arredondamento. Hook adicional exige
  pacote e assinatura próprios.
- [P183 censo do gate entregue](PLAN-183-FOLLOWUP-delivered-gate-default-path-census.md),
  [unificação de predicados](PLAN-183-FOLLOWUP-delivery-predicate-unification.md)
  e [binding do censo JSON](PLAN-183-FOLLOWUP-json-census-call-binding.md):
  preservar a ordem C8/unificação, W7a/binding e os gates de fechamento/1.4.4.
- [P186 linha do assento](PLAN-186-FOLLOWUP-seat-fable51-row.md): preservar a
  medição residual e o gate do pai. Antes de executar qualquer followup
  externo, atualizar formalmente o vínculo de dependência para o sucessor
  com a evidência do fechamento exigido; esta migração não o libera.
- [PLAN-194](PLAN-194-maintenance-train-v1-4-3.md) e seu
  [backlog 1.4.4](PLAN-194-FOLLOWUP-v1-4-4-backlog.md) conservam as demais
  waves, decisões de release e colisões. P196 não duplica a propriedade delas.
- [PLAN-195](PLAN-195-bash-guard-indirect-execution.md) foi autorizado pelo
  CEO/Owner a `done`, com `completed_at: 2026-11-01`, nesta onda. A entrega
  GuardFall pertence à frente responsável; este commit registra o ciclo de
  vida e não constitui evidência de validação da implementação GuardFall.

## Acceptance criteria

- [ ] Cada frente herdada fecha todos os seus itens/ACs ainda vigentes com
  evidência, ou transfere o restante para destino recíproco autorizado.
- [ ] Gates de pais, dependências entre ondas, congelamentos, vetos,
  cerimônias e critérios de medição são demonstrados antes da execução/land
  correspondente; nenhuma opção recusada é reaberta por inferência.
- [ ] Followups externos mantêm dono e vínculo executável com os marcos de
  fechamento; nenhum fica liberado apenas pela troca de status do pai.
- [ ] O fechamento final distingue entregas desta consolidação das entregas
  técnicas de cada frente, sem usar ausência de alertas como prova de entrega.

## Progress log

- 2026-11-01: consolidação documental autorizada pelo CEO/Owner. As onze
  fontes passam a `superseded`; critérios, condições e evidências permanecem
  vinculados aqui. Este plano começa em `draft`, com as ACs acima abertas.
- 2026-11-01: CEO/Owner autoriza incorporar também o followup SendMessage
  de P169 após sua detecção pelo gate de staleness. A décima segunda fonte
  passa a `superseded`, com vínculo recíproco e preservação de W1–W3, critérios
  de sucesso, decisão de três células e OQ-2 adiada.
