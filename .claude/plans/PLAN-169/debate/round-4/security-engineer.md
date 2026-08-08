---
round: 4
archetype: Security Engineer
skill: security-and-auth
agent_persona: Security Engineer (core archetype — VETO em auth/token/input handling)
generated_at: 2026-08-08T13:11:53Z
---

## Verdict

ACCEPT — o único must-fix do round 3 está aplicado literalmente na seção
"Testes" do W4.1, com a menção à família E.2; **zero must-fix, VETO não
exercido, plano endossado para execução do meu assento.**

## Summary (≤ 3 bullets)

- Verificado no texto: os dois controles negativos entraram como pedido —
  (a) assinatura ausente/inválida ⇒ modo advisory, NÃO arma, **incluindo
  `CEO_AUDIT_HMAC_DISABLE` setado**; (b) `resets_at` fora da banda (passado ou
  além de 5h+margem) ⇒ NÃO arma, avisa e registra — e a justificativa cita a
  família E.2 (exceção engolida no caminho de verificação), que era exatamente
  o ponto.
- **Estabilização: 5 riscos duráveis persistem VERBATIM, 0 removidos, 0 novos.**
  Nenhum deles é defeito aberto do plano: são residuais aceitos, três com um
  fio de uma linha cada já listado como nice-to-have no round 3 (frase do ADR
  sobre confiança no snapshot; limite escrito da exceção de Workflow; upgrade
  imprimindo a mudança de postura). Não bloqueiam e não precisam de round novo.
- Este fix não removeu risco nenhum porque não era um risco — era cobertura de
  teste sobre um caminho fail-closed. O que ele muda é que agora existe algo
  que falha se o comportamento não existir, e é isso que o AC-4 passa a exigir.

## Risks

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

Inalterados desde o round 3, todos de uma linha e nenhum bloqueante:
(1) frase do ADR sobre confiança no snapshot (a ordem está no W4.1; o item 7
do `W4-C` enumera o ADR sem ela); (2) limite escrito da exceção de Workflow do
meta-repo — read-only OU probe (ii) verde; (3) upgrade imprime a mudança de
`crossSessionInbound` + regra assimétrica escrita; (4)
`CLAUDE_CODE_SUBAGENT_MODEL` no `env-inventory.json` junto com as envs do W4.

## Unseen by the original plan

Nada novo neste round. O único item do round 3 segue valendo como observação
para quem montar o pack, não como achado: o `W4-C` assina, num único escopo e
numa única sessão, o emissor de auditoria (`audit_emit.py` +
`SPEC/v1/audit-log.schema.md`) e o guard de config (`check_config_change.py`)
ao lado do gate de mensageria — o teste de CAMPOS do checklist R-SEC9 é o
controle positivo desse pack, não higiene.

## What I would NOT change

- **Os dois controles negativos exatamente como ficaram escritos**, incluindo o
  caso `CEO_AUDIT_HMAC_DISABLE` e a citação da família E.2 na justificativa —
  é o que impede o próximo leitor de encurtar o teste por parecer redundante.
- **A ordem dos controles do snapshot** (banda decide, assinatura detecta
  corrupção) e o **prompt de retomada literal com guard de no-op**.
- **`W0.0` + `disableWorkflows: true` de adopter**, e a evidência preliminar do
  probe (b) registrada honestamente como preliminar.
- **`crossSessionInbound: "refuse"` nas 4 superfícies de entrega, incluindo a
  rota de upgrade**; send-gate default-deny, INCONDICIONAL, com "nome de peer
  NÃO autentica" no ADR; cap/charset em nome de peer.
- **Isolamento do fleet por propriedades verificáveis no clone**, DEFER de
  channels, AC-9 medindo resultado, e a proibição de tocar
  `ownership_table.tsv`/`expected-reds`.
