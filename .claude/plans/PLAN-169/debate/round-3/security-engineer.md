---
round: 3
archetype: Security Engineer
skill: security-and-auth
agent_persona: Security Engineer (core archetype — VETO em auth/token/input handling)
generated_at: 2026-08-08T13:11:53Z
---

## Verdict

ADJUST — os 4 must-fix do round 2 estão aplicados no texto e 3 dos meus 8
riscos morreram por cura real; resta **um** item, e é o mesmo padrão que o
próprio plano cataloga como E.2: o caminho fail-closed novo não tem controle
negativo. **VETO não exercido.**

## Summary (≤ 3 bullets)

- **Estabilização honesta: 8 riscos no r2 → 5 persistem VERBATIM, 3 removidos
  por cura verificada, 0 novos.** Mortos: R-SEC13 (template constante com
  interpolação só de inteiros + doutrina do canal no ADR, escrito em W4.1),
  R-SEC14 (PreToolUse `SendMessage`/`ListAgents` INCONDICIONAL + registração
  condicional imprime a ausência, `W4-C` item 6), R-SEC15 (isolamento do fleet
  reescrito como sem-GPG/sem-remote/sem-credenciais/guards ativos/nenhum
  caminho de cerimônia, W5).
- Os 5 que ficam são residuais **aceitos**, não defeitos abertos — exceto dois
  fios de uma linha cada (a frase do ADR sobre confiança no snapshot; o
  limite escrito da exceção de Workflow). Vão como nice-to-have, não bloqueiam.
- O único bloqueio é de teste: os dois comportamentos fail-closed que sustentam
  o quota-resume inteiro — assinatura não verificável ⇒ não arma; `resets_at`
  fora da banda ⇒ não arma — não aparecem na lista de testes de W4.1, que
  enumera só os casos benignos (`<90%`, job já armado, controle negativo de
  job). *(Ref. de linha nos bullets abaixo: são as do round 2 — mantidas
  literais por exigência de comparação; a v2.3 cresceu ~26 linhas.)*

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

1. **Controle negativo dos dois caminhos fail-closed do quota-resume.** A lista
   de testes de W4.1 cobre `≥90% ⇒ injeta`, `<90% ou job armado ⇒ silêncio` e
   `controle negativo ⇒ nenhum job novo` — todos casos benignos. Faltam
   exatamente os dois que a v2.3 acabou de declarar como a defesa:
   **(a) snapshot com assinatura ausente/inválida ⇒ modo advisory, NÃO arma**
   (incluindo `CEO_AUDIT_HMAC_DISABLE` setado) e **(b) `resets_at` fora da
   banda (passado, ou além de 5h + margem) ⇒ NÃO arma, avisa e registra.**
   Sem esses dois, uma exceção engolida no caminho de verificação (o modo de
   falha que este mesmo plano cataloga em **E.2** — emits de GRANT silenciados
   por `except Exception: pass`) faz o mecanismo armar turno não supervisionado
   sobre dado não verificado, e nada na bateria enumerada acusa. Duas linhas na
   seção "Testes" do W4.1; o AC-4 ("doc promete exatamente o que o teste
   provou") passa a ter o que exigir.

## Nice-to-have (advisory)

1. A frase do ADR sobre confiança no snapshot (R-SEC2): a ordem dos controles
   está escrita no W4.1, mas `W4-C` item 7 enumera o conteúdo do ADR sem ela —
   uma linha ("assinatura = detecção de corrupção, não autenticação; a banda
   decide") impede a próxima leitura de inverter a hierarquia.
2. Limite escrito da exceção de Workflow do meta-repo (R-SEC1): o item 8 diz
   que a exceção "fica documentada no ADR"; falta o limite em si — read-only
   OU probe (ii) verde — para que o `W0.0` não caduque por uso.
3. Upgrade imprime a mudança de `crossSessionInbound` + regra assimétrica
   escrita (R-SEC16).
4. `CLAUDE_CODE_SUBAGENT_MODEL` no `env-inventory.json` junto com as envs do
   W4 (R-SEC11).

## Unseen by the original plan

1. **O pack do W4-C passou a assinar, num único escopo e numa única sessão, o
   emissor de auditoria e os guards que vigiam configuração.** A lista de
   arquivos ganhou `.claude/hooks/_lib/audit_emit.py`,
   `SPEC/v1/audit-log.schema.md` e `.claude/hooks/check_config_change.py` ao
   lado do gate de mensageria e das 4 superfícies de settings. É a composição
   certa (as mudanças são interdependentes), mas significa que a camada de
   DETECÇÃO e a camada DETECTADA entram sob a mesma assinatura — o review do
   pack é o único controle entre um erro ali e um enfraquecimento silencioso da
   detecção. Consequência prática: o teste de campos do checklist R-SEC9 (o que
   prova que os eventos novos realmente ATERRISSAM, não que `emit` foi chamado)
   deixa de ser higiene e passa a ser o controle positivo desse pack.
2. **O plano contém o precedente exato do meu must-fix e não o conecta.** E.2 é
   "emits do caminho de GRANT silenciosos, engolidos por `except Exception:
   pass`, enquanto o caminho de block funciona" — a mesma assimetria de "só o
   caminho negativo foi provado", invertida. O W3-K corrige E.2 exigindo teste
   POSITIVO do grant; o W4.1 cria a assimetria espelhada ao pedir só os testes
   benignos. Citar E.2 na justificativa do teste torna o item auto-explicativo
   para quem executar.

## What I would NOT change

- **As três curas do round 2, exatamente como ficaram:** template constante com
  interpolação só de inteiros validados + doutrina do canal no ADR;
  `SendMessage`/`ListAgents` como registração INCONDICIONAL com toda
  registração condicional imprimindo sua ausência; isolamento do fleet descrito
  por propriedades verificáveis no clone.
- **A ordem dos controles do snapshot escrita no corpo do W4.1** — banda decide,
  assinatura detecta corrupção, `CEO_AUDIT_HMAC_DISABLE` ⇒ advisory. Foi o
  ponto onde o plano poderia ter trocado um controle real por um selo.
- **`W0.0` + `disableWorkflows: true` de adopter** (a decisão de segurança mais
  importante do plano) e a evidência preliminar registrada honestamente como
  preliminar.
- **`crossSessionInbound: "refuse"` nas 4 superfícies de entrega, incluindo a
  rota de upgrade**, e o send-gate default-deny com "nome de peer NÃO autentica"
  no ADR.
- **Prompt de retomada literal com guard de no-op**, cap/charset em nome de
  peer, AC-9 medindo resultado, DEFER de channels, e a proibição de tocar
  `ownership_table.tsv`/`expected-reds`.
