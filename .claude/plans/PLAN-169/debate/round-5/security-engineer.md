---
plan: PLAN-169
round: 5
archetype: Security Engineer
skill: security-and-auth
agent_persona: "Security Engineer (core archetype — VETO em auth/token/input handling)"
generated_at: 2026-08-08
note: "Round 5 = triade completa sobre a v2.5 (design executável). Este arquivo já avaliava o delta do trust model do quota-resume; verdito Security ACCEPT sobre a v2.5."
---

## Verdict

ACCEPT — o trust model estreitado é **melhor** que o desenho que eu havia
aceitado no round 2: remove uma garantia falsa, não uma defesa. Zero must-fix,
VETO não exercido.

## Summary (≤ 3 bullets)

- O argumento do r11 está certo e é mais forte que o meu: eu disse "a chave é
  `0o600` do mesmo UID, logo assinar não autentica"; o r11 foi além e viu que
  fazer `statusline-ceo.py` assinar conteúdo que chega por stdin o
  transformaria num **oráculo de assinatura** — trocaria "ler um arquivo 0600"
  por "chamar o script", e ainda venderia autenticação. Descartar é a decisão
  correta.
- **O que eu exigia continua de pé:** o controle que decide QUANDO um turno não
  supervisionado nasce é fail-closed e não vem do dado suspeito — sanity-check
  de banda no `resets_at`, no-op guard exigindo evidência fresca de exaustão
  (bound + single-use), snapshot sempre advisory. A fronteira mudou de nome,
  não de posição.
- Ganho colateral que vale registrar: com os escritores intocados, o contrato
  já gravado em `statusline-ceo.py:57-60` ("Consumers MUST stay advisory-only
  on this input") permanece **verdadeiro e não emendado**. O desenho anterior
  teria exigido reescrevê-lo — e um contrato de confiança reescrito para caber
  no consumidor é como essa classe de dívida costuma nascer.

## Risks

- **R-SEC2 — LOW (era MEDIUM; AJUSTADO pelo narrowing do r11) — o snapshot
  segue sendo entrada não autenticada, e agora o plano diz isso em vez de
  simular o contrário.** A rota de assinatura foi descartada: entre processos
  do mesmo UID não existe origem inforjável, e um signer que aceita stdin
  arbitrário seria um oráculo. O que resta é declaração honesta de fronteira
  (adversário local com Bash já controla a sessão; o quota-resume não adiciona
  capacidade) mais controles contra ERRO e CORRUPÇÃO. *Residual aceito:* os
  dois controles que sobraram — banda e no-op guard — são controles de erro,
  não adversariais, e o breadcrumb de exaustão é estado local do mesmo tier;
  isso é coerente com a fronteira declarada e só vira defeito se algum texto
  futuro descrever qualquer um deles como defesa contra adversário.
  *Mitigação:* a declaração de não-garantia vai para o ADR e para a doc do
  usuário, não só para o corpo do plano.

- **R-SEC16 — LOW/MEDIUM — a migração de upgrade muda a postura de segurança
  na máquina do adopter; silêncio aqui é incidente de suporte.** `W4-C:478-489`
  entrega `crossSessionInbound: "refuse"` também pela rota de upgrade
  (`upgrade.sh:2235-2252`). Uma sessão que recusa **não mostra diferença
  visível** — o adopter que usa cross-session perde mensageria sem saber por
  quê. *Mitigação:* o upgrade IMPRIME a mudança (linha nomeada + como reverter)
  e o CHANGELOG a declara; e a regra assimétrica fica escrita: apertar pode ser
  default, **afrouxar nunca é silencioso**.

- **R-SEC1 — MEDIUM (residual, era CRITICAL) — o bypass do gate de spawn por
  Workflow deixou de ser hipótese e virou evidência; o adopter está coberto, o
  meta-repo opera sob exceção.** `:363-368` registra zero `agent_spawn` para os
  7 `agent()` do inventário, e `W4-C:506-513` fecha o lado do adopter com
  `disableWorkflows: true`. O residual é a exceção "operador-supervisionado"
  que este próprio plano usa. *Mitigação:* a exceção precisa de limite escrito
  no ADR — Workflow no meta-repo só para trabalho read-only OU com o probe (ii)
  de `check_canonical_edit.py` verde, exatamente como o `W0.0` já manda; sem
  isso a exceção vira permanente por uso.

- **R-SEC11 — LOW/MEDIUM (reafirmado do round 1, sem resposta na v2.2) —
  `Agent(param:value)` é fail-closed real, mas não é soberano.** `W4.3:414-422`
  segue sem registrar que `CLAUDE_CODE_SUBAGENT_MODEL` sobrepõe o roteamento de
  modelo e que permission rules estão migrando de escopo repo → user/managed.
  *Mitigação:* registrar a env no inventário + check e declarar a limitação de
  soberania no ADR em vez de vender enforcement absoluto.

- **R-SEC6 — LOW (residual) — o sentinela persistido do overhead-ack continua
  no texto como opção condicional.** `W3.3:237-242` já o cerca com os 5 limites
  e o AC-9 passou a medir resultado (`:689-692`). *Mitigação:* nenhuma nova —
  só não deixar a opção virar caminho por conveniência durante a cerimônia.

## Must-fix (blocking)

Nenhum.

## Nice-to-have (advisory)

1. A declaração de não-garantia precisa aterrissar no **ADR e na doc do
   usuário**, com a fronteira em uma frase: quota-resume defende contra erro e
   corrupção, **não** contra adversário local — quem tem Bash já tem a sessão.
   Sem isso, a presença de um passo chamado "verificação" convida o próximo
   leitor a inferir autenticação (é a mesma dívida que o narrowing acabou de
   pagar).
2. Os três fios do round 3/4 seguem abertos e inalterados: limite escrito da
   exceção de Workflow (R-SEC1); upgrade imprimindo a mudança de postura
   (R-SEC16); `CLAUDE_CODE_SUBAGENT_MODEL` no `env-inventory.json` (R-SEC11).

## Unseen by the original plan

1. **A ordem em que este achado apareceu é o argumento mais forte a favor do
   rail cross-vendor, e vale como registro de método:** o design de assinatura
   passou por quatro rodadas de debate — incluindo o meu próprio assento, que o
   avaliou e ACEITOU duas vezes — e só caiu no r11. Eu identifiquei a premissa
   certa (chave do mesmo UID) e ainda assim aceitei a mitigação errada, porque
   avaliei "a assinatura é fraca" em vez de "a assinatura é um oráculo". Isso é
   um caso limpo de achado que o debate mesmo-vendor não produziu, e merece uma
   linha na síntese ao lado do precedente S294.
2. Os dois controles negativos que exigi no round 3 sobrevivem ao narrowing com
   o alvo trocado: o caso (a) deixa de ser "assinatura inválida ⇒ advisory" e
   passa a ser **"snapshot ausente/ilegível/stale ⇒ advisory, NÃO arma"**. Se o
   texto do W4.1 ainda descrever (a) em termos de assinatura, o teste vai
   perseguir um caminho que não existe mais — vale conferir na montagem do pack.

## What I would NOT change

- **O narrowing inteiro**, incluindo a decisão de não tocar os escritores do
  snapshot: menos superfície nova, nenhum manuseio de chave, nenhum oráculo, e
  o contrato de `statusline-ceo.py:57-60` continua válido sem emenda.
- **A banda fail-closed no `resets_at` como o controle que DECIDE** e o no-op
  guard exigindo evidência fresca de exaustão — é o par que impede que um dado
  errado escolha quando um turno não supervisionado nasce.
- **Declarar a não-garantia em vez de vendê-la.** Uma garantia falsa é pior que
  nenhuma: ela desativa a desconfiança de quem lê depois.
- Tudo que endossei no round 4 e segue intocado: `W0.0` + `disableWorkflows`,
  `crossSessionInbound: "refuse"` nas 4 superfícies, send-gate default-deny
  incondicional com "nome de peer NÃO autentica", prompt de retomada literal,
  cap/charset em nome de peer, DEFER de channels, e a proibição de tocar
  `ownership_table.tsv`/`expected-reds`.
