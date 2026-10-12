---
id: PLAN-169-FOLLOWUP-sendmessage-probes
parent: PLAN-169
title: Mensageria entre agentes — controle refuse × accept, ADR de visibilidade e sondas W4.2.0 (pernas 2–4 do AC-5 do PLAN-169)
status: reviewed
created: 2026-10-11
reviewed_at: 2026-10-12
reviewed_by: "Owner (S363, AskUserQuestion do CEO, 2026-10-12 ~12:50Z): «Sim, três modos; revisado (Recommended)», em resposta a «o teste cobre os três modos (refuse, hold, accept), e posso marcar o plano como revisado, deixando para depois a pergunta sobre o adopter que já usa accept?»"
owner: CEO
depends_on: [PLAN-169]
level: L3
tags: [security, messaging, probes, followup]
---

## Context

O AC-5 do PLAN-169 migrou para o `PLAN-169-FOLLOWUP-quota-resume-and-probes`
quando o PLAN-169 fechou (`PLAN-169-closure-and-cross-session-evolution.md:1393-1399`).
Aquele follow-up fechou `done` em 2026-10-10 com o AC-5 movido, em dois
destinos:

- **Perna 1** (um peer tenta induzir edição canônica via `SendMessage` ⇒
  BLOQUEADO, com evento HMAC de campos whitelisted, checklist R-SEC9): vai para
  o AC-15 do PLAN-186, que já é dono do matcher do `SendMessage`. A linha
  recíproca está sob o AC-15 em `PLAN-186-orchestrator-operating-model.md`.
- **Pernas 2–4: este plano.** Escopo copiado do PLAN-169 (§W4.2.0 em
  `:597-620`, postura default em `:621-635`, AC-5 em `:1393-1399`).

## Goal

Saber, com evidência registrada, se a postura `refuse` impede um turno nascido
de mensagem de outra sessão, o que a cadeia HMAC registra desse turno, e ter a
doutrina escrita num ADR.

## Items

### W1 — sondas W4.2.0 (a)–(f)  [P1]  (medição; o que mexer em settings é cerimônia)
- **(a)** O `UserPromptSubmit` dispara para mensagem de peer? Há resposta
  PARCIAL no registro do AC-4 (`.claude/plans/PLAN-169/ac4-quota-window-S362-S363.md`
  §4): 0 de 140 turnos de colega em processo tiveram `prompt_submitted`, contra
  21/21 `task-notification` e 7/7 prompts do Owner. Falta: mensagem de OUTRA
  sessão, terminal ou máquina, e separar «o hook não disparou» de «disparou e
  falhou antes de emitir».
- **(b)** O `SubagentStart` dispara para `agent()` de Workflow?
- **(c)** Envio entre máquinas: a doc diz reply-only, o changelog 2.1.225 diz
  name-first. Testar.
- **(d)** [Sec-U1] O `refuse` também recusa um filho da própria sessão?
- **(e)** [Sec-U2/U-2] O que o HMAC registra HOJE de um turno nascido de
  mensagem recebida. É essa medição que permite a frase honesta do ADR (W3).
- **(f)** [Sec-U4] O PreToolUse dispara para `SendMessage` emitido por
  subagente ou colega? Depende do matcher registrado do AC-15 do PLAN-186:
  coordenar com aquela cerimônia, não duplicar o matcher.

### W2 — controle refuse × hold × accept  [P1]  (clone descartável; nunca no repo canônico)
- Com `crossSessionInbound: "refuse"`, nenhum turno nasce de mensagem de outra
  sessão. Controle positivo: com `accept`, o turno nasce. A rota de clone
  dedicado segue o PLAN-169 (`:624-628`): o valor de projeto vence o
  `--settings`.
- **Terceira célula, `hold` (acrescentada em 2026-10-11, S363, pela OQ-1):** o
  CC 2.1.295 tem um terceiro valor, `hold`, que os textos do binário descrevem
  como «mensagens retidas» até o valor virar `accept`. A expectativa a medir:
  com `hold`, nenhum turno nasce no envio, e a mensagem fica retida em vez de
  descartada; ao trocar para `accept`, a mensagem retida chega. As duas metades
  são afirmações a medir, não fatos: o binário só mostra os textos.

### W3 — ADR da doutrina  [P1]  (canônico: ADR + cerimônia)
- Inclui a decisão sobre a visibilidade das tentativas recusadas («recusado e
  invisível» é escolha, não default). Se a postura não for `refuse`, inclui
  também o escopo degradado EXPLÍCITO da claim de auditabilidade.

## Decisão do Owner (2026-10-12)

Pergunta do CEO (AskUserQuestion, S363, ~12:50Z): «o teste cobre os três modos
(refuse, hold, accept), e posso marcar o plano como revisado, deixando para
depois a pergunta sobre o adopter que já usa accept?». Resposta do Owner: «Sim,
três modos; revisado (Recommended)».

- **Três células na W2.** O texto já as tinha desde `95ba98c4` (W2, terceira
  célula `hold`; OQ-1, registro de 2026-10-11) e o Check do segundo critério de
  sucesso já exige as três linhas (`refuse`, `hold`, `accept`) no
  `refuse-accept.md`. A decisão confirma esse desenho; nada mais muda na W2.
- **Revisado.** O `status` passou de `draft` a `reviewed` no commit anterior a
  este, sozinho.
- **OQ-2 adiada.** A pergunta sobre o adopter que já usa `accept` fica para
  depois (ver a OQ-2).

## Open questions

- **OQ-1.** A chave `crossSessionInbound` e o comportamento medido no PLAN-169
  são de gerações anteriores do Claude Code. Re-verificar no CC vigente antes
  da W2 (modelo novo ⇒ re-testar).
  - **Registro de 2026-10-11 (S363), só leitura de textos do binário, sem
    executar nada.** Conferido com `grep -a` no binário instalado do CC
    2.1.295 (`~/.local/share/claude/versions/2.1.295`), por exemplo
    `grep -a -o 'crossSessionInbound.\{0,100\}' <binário>`:
    - a chave `crossSessionInbound` existe e aceita três valores: `refuse`,
      `hold` e `accept`. O par `refuse`/`hold` aparece como a lista de valores
      «restritivos» (`restrictive:["refuse","hold"]`);
    - o texto «a repo may only tighten» aparece: um valor de repositório só
      pode apertar, e um `accept` do próprio usuário não desfaz um `hold`
      posto pelo repositório nem pela política gerenciada da organização. Isso
      bate com o PLAN-169 (`:621-628`: o valor de projeto mais estrito vence);
    - os motivos de retenção mostrados ao usuário incluem `explicit-setting`,
      `managed-setting`, `invalid-setting`, `bypass-default` e
      `mode-mismatch` (e também `no-mode-asserted`). O texto de
      `invalid-setting` diz que um valor não reconhecido faz as mensagens
      ficarem retidas enquanto ele existir.
    - **O que isto NÃO prova:** comportamento. Os textos mostram que os valores
      e os motivos existem; se um turno nasce ou não em cada valor é a W2 que
      mede. Por isso a W2 passou a ter três células (`refuse`, `hold`,
      `accept`). A OQ-1 fica aberta até a W2 registrar as três.
- **OQ-2.** A linha `refuse` no `settings.json` do adopter passa pela decisão de
  posse (PLAN-169 `:629-635`, classe PLAN-167): um adopter com `accept`
  explícito fica preservado? Responder antes de qualquer linha nova em template.
  - **Adiada pelo Owner em 2026-10-12** (ver «Decisão do Owner (2026-10-12)»):
    fica aberta. A W1 e a W2 são medição (a W2 num clone descartável) e não
    acrescentam linha em template, então não esperam por ela. A regra acima
    continua: nenhuma linha nova em template antes da resposta.
- **OQ-3.** O custo fica a firmar no refinamento, em tokens e sessões (ADR-081).

## Success criteria

- [ ] As seis sondas W4.2.0 (a)–(f) registradas com evidência, uma linha por sonda.
  Check: `grep -cE '^\| \((a|b|c|d|e|f)\) ' .claude/plans/PLAN-169-FOLLOWUP-sendmessage-probes/w4.2.0-probes.md` (espera 6)
- [ ] Controle refuse × hold × accept registrado nas três células: com `refuse` não nasce turno; com `hold` não nasce turno no envio e o registro diz se a mensagem ficou retida; com `accept` nasce.
  Check: `grep -qE '^\| refuse \|' .claude/plans/PLAN-169-FOLLOWUP-sendmessage-probes/refuse-accept.md && grep -qE '^\| hold \|' .claude/plans/PLAN-169-FOLLOWUP-sendmessage-probes/refuse-accept.md && grep -qE '^\| accept \|' .claude/plans/PLAN-169-FOLLOWUP-sendmessage-probes/refuse-accept.md`
- [ ] ADR aceito com a decisão sobre a visibilidade das tentativas recusadas.
  Check: `grep -l 'tentativas recusadas' .claude/adr/ADR-*.md`
