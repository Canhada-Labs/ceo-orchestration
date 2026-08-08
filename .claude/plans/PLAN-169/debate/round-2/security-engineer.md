---
round: 2
archetype: Security Engineer
skill: security-and-auth
agent_persona: Security Engineer (core archetype — VETO em auth/token/input handling)
generated_at: 2026-08-08T13:11:53Z
---

## Verdict

ADJUST — os 10 must-fix do round 1 e os 3 residuais textuais estão no texto da
v2.2; as curas do rail r3-r6 introduziram **um canal novo (hook injetando
instrução no transcript) e uma cláusula de registração condicional** que
precisam de limite escrito antes da cerimônia. **VETO não exercido.**

## Summary (≤ 3 bullets)

- Verificação do round 1: `W0.0` (`:137-144`), prompt literal (`:333-336`),
  postura efetiva (`:337-340`), default-deny do send-gate (`W4-C:475-477`),
  allowlist positiva + WARNING (`W3.1:221-231`), fleet sem `accept`+acceptEdits
  (`:531-535`), env-inventory (`:341-342`) — todos presentes. Residuais r2
  aplicados: sanity fail-closed do `resets_at` (`:321-326`), AC-9 por resultado
  (`:689-692`), cap/charset de peer name (`:402-404`), "nome de peer NÃO
  autentica" no ADR (`W4-C:502-505`).
- A assinatura HMAC do snapshot (r3) é uma melhora real contra corrupção e
  escrita não-privilegiada — mas **não autentica contra o adversário do modelo
  de ameaça** (a chave é um arquivo local `0o600` do mesmo usuário,
  `audit_hmac.py:185,333`); o controle que sustenta a decisão continua sendo o
  sanity-check de banda, e o texto precisa dizer isso para ninguém removê-lo
  depois por "já está assinado".
- O item genuinamente novo é de doutrina: `check_quota_resume.py` transforma um
  hook em **fonte de instrução para o modelo vivo**. Isso é útil e é a única
  rota que fecha o caso, mas cria um canal que hoje não tem regra — e a
  primeira coisa que ele interpola é um valor lido de disco.

## Risks

- **R-SEC13 — HIGH — hook que injeta instrução no transcript é canal novo sem
  doutrina, e já nasce interpolando dado de disco.** `check_quota_resume.py`
  (`:292-301`) injeta "quota ≥90%, `resets_at=X` verificado — agende o one-shot
  AGORA"; `X` vem do snapshot. Um campo do JSON que chegue à string injetada
  como texto livre é conteúdo de arquivo ocupando posição de instrução — a
  classe exata que o resto do plano fecha em toda outra fronteira.
  *Mitigação:* template CONSTANTE com substituição **somente de inteiros já
  validados** (nunca string do snapshot, nem rótulo de bucket, nem nome de
  plano); e uma linha de doutrina no ADR: texto injetado por hook é instrução
  do FRAMEWORK (superfície canônica, guardada), nunca relay de conteúdo
  externo — todo hook que use o canal emite template constante.

- **R-SEC14 — HIGH — "nenhuma registração nova incondicional" (`W4-C:501`)
  transforma um guard de segurança em guard silenciosamente ausente.** A
  cláusula do piso de CLI (r5) é correta para `PostToolBatch`/`TaskCompleted`,
  mas está redigida de forma geral e o pack registra também o **PreToolUse de
  `SendMessage`/`ListAgents`** (item 2) — o gate de envio. Numa CLI abaixo do
  piso, o framework instalaria com o gate ausente e sem sinal.
  *Mitigação:* condicionar cada registração ao **evento que ela usa**, não a um
  piso global; a registração do send-gate é incondicional (PreToolUse é evento
  antigo) e, se algum dia precisar de condição, a condição é a presença da
  própria feature que ela guarda + mensagem de instalação nomeando a ausência.

- **R-SEC2 — MEDIUM (era HIGH) — o snapshot continua sendo input não
  autenticado contra o adversário que importa; a assinatura não muda isso.**
  A chave de audit é arquivo local `0o600` do mesmo usuário
  (`audit_hmac.py:185,320-336`), legível por qualquer Bash que o modelo rode —
  quem forja o snapshot forja a assinatura. Some-se
  `CEO_AUDIT_HMAC_DISABLE=1` (`audit_hmac.py:49,150-151`), que curto-circuita a
  via HMAC.
  *Mitigação:* manter explicitamente os DOIS controles e a ordem entre eles —
  o sanity-check de banda (`resets_at` futuro, dentro de 5h + margem) é o
  controle load-bearing, a assinatura é detecção de corrupção; e declarar que
  `CEO_AUDIT_HMAC_DISABLE=1` degrada o quota-resume para **advisory**, nunca
  para "verificação pulada ⇒ arma". O ADR registra a limitação em uma frase.

- **R-SEC15 — MEDIUM — a postura de isolamento do fleet do 170 é internamente
  impossível como escrita, e vai ser CONGELADA por assinatura neste plano.**
  `:386-390` resolve o fleet por **clone dedicado** do repo (correto: project
  `refuse` vence `--settings`), mas `:531-535` exige sessões "sem superfície
  canônica" — um clone deste repo *é* a superfície canônica. As duas frases não
  podem ser ambas verdadeiras, e o pré-registro assinado (AC-6) as torna
  imutáveis.
  *Mitigação:* trocar "sem superfície canônica" pelo que é verificável no
  clone: **sem chave GPG no ambiente, sem remote de push, sem credenciais, com
  os guards canônicos ATIVOS e nenhum caminho de cerimônia** — e a proibição já
  escrita de `inbound=accept` junto de acceptEdits/bypass/night-mode.

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

1. **Template constante no canal de injeção** (R-SEC13): `check_quota_resume.py`
   interpola apenas inteiros já validados; nenhuma string vinda do snapshot
   entra na instrução. Uma linha de doutrina no ADR do W4-C: texto injetado por
   hook é instrução do framework, nunca relay de conteúdo externo.
2. **Condição por EVENTO, não piso global** (R-SEC14): reescrever
   `W4-C:494-501` para que a registração do PreToolUse `SendMessage`/`ListAgents`
   seja incondicional, e que qualquer registração condicional imprima a ausência
   na instalação. Um guard de segurança nunca some em silêncio.
3. **Ordem dos dois controles escrita, e `CEO_AUDIT_HMAC_DISABLE` tratado**
   (R-SEC2): o sanity-check de banda é o controle que decide; a assinatura é
   detecção de corrupção, não autenticação (chave `0o600` do mesmo usuário);
   HMAC desabilitado ⇒ advisory, nunca arm.
4. **Corrigir a postura de isolamento do fleet ANTES de assinar o pré-registro**
   (R-SEC15): trocar "sem superfície canônica" por sem-GPG / sem-remote /
   sem-credenciais / guards ativos / nenhum caminho de cerimônia.

## Nice-to-have (advisory)

1. Upgrade IMPRIME a mudança de `crossSessionInbound` e o CHANGELOG a declara;
   regra assimétrica escrita (apertar pode ser default, afrouxar nunca é
   silencioso) — R-SEC16.
2. Marker de "job já armado" (`:296-297`) é supressão de repetição, não
   autorização: se o marker sumir, o pior caso é uma injeção a mais, nunca um
   arm sem verificação. Vale a frase no teste.
3. Limite escrito para a exceção de Workflow do meta-repo (R-SEC1), para que
   `W0.0` não caduque por uso.
4. Registrar `CLAUDE_CODE_SUBAGENT_MODEL` no `env-inventory.json` junto com as
   envs do W4 (R-SEC11).

## Unseen by the original plan

1. **O plano cria um canal de "hook fala com o modelo" e não o nomeia como
   categoria.** Depois de `check_quota_resume.py`, qualquer hook futuro pode
   dizer ao modelo o que fazer, e a diferença entre "framework instruindo" e
   "conteúdo de arquivo instruindo" passa a depender de quem escreveu o hook.
   Isso merece uma seção curta no ADR — é a única superfície do pack que fala
   NA direção do modelo em vez de decidir sobre ele.
2. **A instrução injetada induz uma tool call (`CronCreate`) que não passa por
   prompt de permissão.** Não é vulnerabilidade — é uma propriedade que o ADR
   deve declarar, porque é o que torna o mecanismo possível e é o que um
   revisor futuro vai querer saber sem reconstruir a cadeia.
3. **Nenhum teste pedido prova o caso negativo do canal:** snapshot com
   assinatura inválida ⇒ hook NÃO injeta (silêncio), e `resets_at` fora da
   banda ⇒ hook NÃO injeta. O texto pede controle para `<90%` e "job já
   armado" (`:300-301`), que são os dois casos benignos.

## What I would NOT change

- **`W0.0` regendo a própria execução do plano**, agora com evidência
  preliminar de que o gate de spawn não intercepta Workflow — e
  `disableWorkflows: true` como default de adopter (`W4-C:506-513`). Esse par é
  a decisão de segurança mais importante da v2.2.
- **`crossSessionInbound: "refuse"` em TODAS as superfícies de entrega**
  (`W4-C:478-489`), incluindo a rota de upgrade — foi exatamente a lacuna que
  transformaria a postura em teatro de template.
- **Send-gate default-deny com "nome não autentica" no ADR** (`W4-C:475-477`,
  `:502-505`).
- **Sanity-check de banda no `resets_at` mantido AO LADO da assinatura**
  (`:321-326`) — a v2.2 acertou em não substituir um pelo outro.
- **Prompt de retomada literal com guard de no-op** (`:308-312`, `:333-336`):
  o "no-op" quando não há evidência de exaustão é uma boa adição do rail.
- **DEFER de channels**, **fleet sem `accept`+acceptEdits**, **cap/charset em
  nome de peer**, **AC-9 medindo resultado** e a **proibição de tocar
  `ownership_table.tsv`/`expected-reds`**.
