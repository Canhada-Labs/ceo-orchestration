---
plan: PLAN-164
round: 1
critic: security-engineer
verdict: ADJUST
created_at: 2026-07-29
skill: core/security-and-auth (sha256=50cd673f… lida integralmente antes desta crítica)
---

# Security Engineer — crítica round 1, PLAN-164

Evidência inspecionada (não inferida): `check_pair_rail.py` L1691-1758 (resolução/clamp
do timeout), L980-1090 (`_invoke_codex_review`, mapeamento de exceptions), L1469
(`pair_rail_review_expected` emitido ANTES do subprocess), L749-780 (seam
`CEO_PAIR_RAIL_CODEX_BIN`, fail-closed H1); `land-plan163-pin.sh` L96-109
(`resolve_anchor`) e L111-272 (`gate_v2`); `settings.json` L281-282 e
`settings.base.json` L97-98 (registration `timeout: 60` em ambos);
`inputs-pin.sha256` (o pin-pack CONTÉM `.claude/hooks/check_pair_rail.py`);
`GATE-PIN-ANCHOR` atual (`a4371c7`); diagnóstico GATE-V2 de 2026-07-29;
CEREMONY-RUNBOOK §Passo 2.

## Verdict

**ADJUST**

## Summary

O uplift é necessário e a direção está certa: um "truth gate" que fail-openou em
12 de 12 invocações da história inteira não é um controle — é teatro de controle,
e a pior posição de segurança possível é a atual (a existência do rail sugere uma
revisão que nunca acontece). Subir 30→100/60→120 não concede autoridade nova a
ninguém (o rail é ADVISORY por ADR-127; um verdito BLOCK já vira system-message,
não bloqueio), então o uplift em si não enfraquece nenhum controle. Os problemas
estão nas BORDAS do plano: (1) o `resolve_anchor()` do gate confia num arquivo de
working-tree não-validado — a re-âncora proposta é aceitável, mas só se o gate
passar a validar criptograficamente para onde a âncora aponta; (2) o pin-pack
staged contém uma cópia de `check_pair_rail.py` com o default velho — depois do
PLAN-164, um re-run de `land-plan163-pin.sh` REVERTE silenciosamente o fix e o
preflight PASSA (fato verificado no manifest, não hipótese); (3) o delta-review
do pack precisa provar a NEGATIVA (41 linhas intactas), não só a positiva (2
linhas mudadas). Com esses ajustes, ACCEPT no round 2.

## Risks

- **R1 — Âncora é input de verdito não-validado (tamper surface real).**
  `resolve_anchor()` (land-plan163-pin.sh L99-101) PREFERE o arquivo
  `GATE-PIN-ANCHOR` do working tree e confia em `sha=` e `ts=` como lidos.
  `.claude/plans/` é livremente gravável (está no allowlist de sujeira RE_PLANS
  do próprio script) — ou seja, o MESMO agente cujos edits o rail supervisiona
  pode mover `ts=` para frente e "limpar" qualquer case-F embaraçoso do conjunto
  pós-âncora. Hoje o laundering completo ainda exige um healthy≥1 fresco, mas o
  PLAN-164 vai justamente tornar healthy cases rotineiros — depois do uplift, o
  custo de lavar um fail-open real cai para "editar 1 linha de um arquivo de
  plano + 1 edit trivial". O Scope do sentinel protege o COMMIT da âncora; não
  protege a LEITURA do gate, que aceita bytes de working tree. Controle de
  processo ≠ binding do input do verdito.
- **R2 — Reversão silenciosa via pin-pack stale.** O `inputs-pin.sha256` lista
  `.claude/hooks/check_pair_rail.py` entre os 20 arquivos do pin-pack. Após a
  cerimônia PLAN-164, esses bytes staged ficam obsoletos (default 30). O
  preflight do script verifica staged-vs-manifest (`shasum -c`), NUNCA
  staged-vs-árvore-viva — um re-run da cerimônia do pin (que a alternativa da
  OQ3 explicitamente contempla, e que o runbook trata como idempotente/re-rodável)
  aplicaria `cp` por cima do hook novo e reverteria o timeout para 30 com todos
  os oráculos verdes. Regressão de segurança sem nenhum gate trip.
- **R3 — Hook-kill do harness é PIOR que case F e fica mais próximo.**
  `pair_rail_review_expected` é emitido antes do subprocess (L1469); se o
  harness matar o hook na registration, o `pair_rail_case` NUNCA é emitido — o
  edit prossegue sem review E sem registro terminal no audit-log (só detectável
  via pareamento de deficit no ceo-boot). Com 30/60 a margem era 30 s; com
  100/120 cai para 20 s, e a variância é exógena (startup python frio, redaction
  de arquivo grande, carga). Nada no plano impede que um ajuste futuro inverta a
  relação interno/registration e institucionalize o hook-kill.
- **R4 — Delta-sync do pack como janela de contrabando.** Recomputar
  `MANIFEST.sha256` + gêmeo re-pina O QUE ESTIVER em staged — o `shasum -c` não
  distingue o delta pretendido de qualquer outro byte que tenha mudado nos 43
  arquivos entre o double-APPROVE e o sync. Um delta-review de 1 round que olhe
  só para as 2 registrations não detectaria um terceiro arquivo alterado.
- **R5 — Fallback do parse continua sendo o valor quebrado (pré-fix).** Hoje,
  `>600` e parse-error caem em `30.0` — pós-uplift, um operador que digitar 601
  voltaria SILENCIOSAMENTE para o único valor que garante 100 % de fail-open. O
  plano já prevê trocar os literais de L1720/1722 (bom); o risco residual é a
  SEMÂNTICA reset-to-default para overflow, que transforma fat-finger em regime
  de fail-open sem nenhum breadcrumb.
- **R6 — Env-knob como alavanca de fail-open universal (residual pré-existente).**
  `CEO_PAIR_RAIL_TIMEOUT_S=1` força case F em toda invocação. Exige controle do
  env da sessão (privilégio já alto), e cada disparo EMITE case F auditável —
  detectável, não invisível. Aceitável como residual NOMEADO no ADR; não
  aceitável como omissão.

## Must-fix

1. **Validar a âncora no gate (fecha R1).** `resolve_anchor()` deve tratar o
   arquivo como PONTEIRO, não como fonte: (a) `ts` derivado de
   `git log -1 --format=%cI <sha>` — nunca lido do arquivo (isso sozinho mata o
   tamper de mover `ts` para frente); (b) o `sha` deve resolver para um commit
   existente cujo subject carrega tag sentinel `[SENT-...]` (aceitar
   `SENT-PLAN163-PIN` E `SENT-PLAN164-RAIL`); fail-CLOSED (die) se qualquer
   condição falhar. São ~6 linhas de bash no mesmo script que o plano já toca.
2. **Neutralizar o pin-pack stale (fecha R2).** Escolher um: (a) sincronizar
   também `staged/pin-pack/.claude/hooks/check_pair_rail.py` + recomputar
   `MANIFEST.sha256` do pin + gêmeo `inputs-pin.sha256`, sob o mesmo
   delta-review; ou (b) aposentar a rota de apply do script — guard no início do
   APPLY: se `git log --grep='\[SENT-PLAN164-RAIL\]'` encontrar o commit, die
   com instrução ("pin já superado pelo PLAN-164; só `--gate-v2` permanece
   válido"). (b) é menor e suficiente; o W1 deve incluir um ou outro
   explicitamente.
3. **Cross-constraint interno < registration como teste mecânico (fecha R3).**
   A suíte de parity do W1 deve ganhar um teste que lê `settings.json`,
   `settings.base.json` E o default do hook, e asserta
   `registration − default_interno ≥ 15` nos DOIS arquivos. Sem isso, a relação
   que impede o hook-kill sistemático vive só na cabeça de quem calibrou.
   Documentar no ADR o comportamento observável do hook-kill (deficit, não
   case F) como modo de falha conhecido.
4. **Delta-review prova a negativa (fecha R4).** O artefato de review em
   `PLAN-163/review/` deve registrar: sha256 antigo → novo POR ARQUIVO para
   exatamente os 2 arquivos do delta, E o diff do gêmeo antigo vs novo
   (`inputs-pack.sha256`) limitado a exatamente 2 linhas — qualquer 3ª linha
   divergente aborta o sync. Com essa prova mecânica, 1 round de delta-confirm
   é suficiente; sem ela, não é.
5. **Nomear R6 no ADR (registro, não código).** O ADR do contrato de timeout
   deve listar `CEO_PAIR_RAIL_TIMEOUT_S` sub-piso como residual aceito, com a
   racional (fail-open é contrato ADR-106; env-control ⊃ ameaça; case F é
   auditável) — para que a próxima auditoria não "descubra" isso como gap.

## Nice-to-have

- Clamp de overflow com semântica clamp-to-bound (`min(v, 600)`) em vez de
  reset-to-default, ou ao menos um breadcrumb de audit quando o valor resolvido
  difere do solicitado (cobre R5 além do que o plano já faz).
- Piso mínimo no knob (ex.: `< 10 → default`) — barato, elimina R6 em vez de
  só nomeá-lo.
- `git verify-commit` na âncora (assinatura GPG do commit apontado) como rail
  adicional ao must-fix 1 — no host do Owner a pubkey está no keyring; num
  clone de adopter, degradar para WARN.
- Registration 130 em vez de 120 para restaurar a margem absoluta de 30 s que a
  config atual tinha (20 s é defensável com o overhead medido de 10-15 s, mas a
  medição é de UMA máquina em UM dia).
- Breadcrumb de progresso no PreToolUse longo (ex.: emitir um audit event aos
  60 s) — mitiga o incentivo operacional de baixar o timeout na mão quando a
  sessão "parece travada", que é o caminho realista para R6 acontecer em campo.

## Unseen

- **Fallback do gate pós-re-âncora resolve para a âncora VELHA.** Se
  `GATE-PIN-ANCHOR` sumir do disco, o fallback de `resolve_anchor()` greppa
  APENAS `[SENT-PLAN163-PIN]` (L104) → o gate avaliaria contra `a4371c7`, o
  case-F de 07-29 voltaria ao conjunto e o verdito seria FAIL permanente.
  Direção de falha SEGURA (falha para FAIL, nunca para PASS) — mas é um FAIL
  confuso que vai queimar tempo de diagnóstico; o must-fix 1 já resolve se o
  fallback aceitar ambas as tags (preferindo a mais recente).
- **Deleção do arquivo de âncora como ataque = inócua.** Pelo mesmo motivo:
  só produz FAIL. Registrado para constar que foi considerado.
- **`CEO_PAIR_RAIL_CODEX_BIN` está corretamente gateado.** Verifiquei o seam
  (L749-780): fail-CLOSED fora de contexto de teste (fix H1 do PLAN-163). Não é
  um segundo env-escape — nenhuma ação necessária; registrado para a próxima
  auditoria não re-flagar.
- **O uplift não muda a superfície de exfil/egress.** O redactor ADR-114 roda
  no mesmo callsite, fail-closed (`CodexUnavailable` se indisponível, L933);
  mais tempo de subprocess não altera o que sai do processo. Payload
  adversarial grande já degrada para ADVISORY por oversize antes do invoke
  (L261) — o custo de DoS por edit fica limitado ao teto da registration, por
  edit canônico, visível ao operador. Aceitável.
- **Nenhuma instrução embutida dirigida a mim** foi encontrada nos arquivos
  lidos (planos, probes, scripts, hook). Nada a citar.

## What I would NOT change

- **O contrato fail-open (ADR-106).** Fora de escopo por decisão explícita do
  Owner, e correto aqui: fail-closed num rail com dependência exógena (API
  externa, latência não-controlada) é o self-DoS que o C3 do S284 já demonstrou.
  Concordo com a exclusão.
- **O pin ADR-182.** Self-check OK, verify-then-invoke saudável, e o seam de
  teste fail-closed. Re-abrir seria churn sem ganho.
- **A aritmética append-only do gate.** `failopen==0` insatisfazível contra a
  âncora velha é o sistema funcionando: o log não esquece. A resposta certa é
  re-ancorar COM validação (must-fix 1), nunca relaxar o predicado ou tocar o
  log.
- **A ordem cerimonial** (fix → re-âncora no mesmo commit assinado → prova
  fresca em sessão nova → pack). A prova fresca pós-restart é o único teste que
  roda como o harness roda — manter.
- **O clamp superior 600.** Um teto no timeout é correto (um valor absurdo
  seria seu próprio DoS de sessão); só a semântica de overflow merece o ajuste
  do nice-to-have.

## Posição explícita nas OQs

- **OQ1 = 100 s (ACCEPT do draft).** REJEITO 48: margem de ~12 s sobre um único
  ponto medido (36,3 s) com variância exógena já observada de 8→36 s é
  exatamente a classe de aposta que produziu o 30. 100 s ≈ 2,75× o medido.
- **OQ2 = 120 s (ACCEPT condicionado ao must-fix 3).** O custo de UX (até
  ~100 s de PreToolUse síncrono) não é um custo de segurança — a alternativa
  real não é "review mais rápido", é "nenhum review". 130 como nice-to-have.
- **OQ3 = draft (âncora atualizada no commit da cerimônia PLAN-164), condicionado
  ao must-fix 1.** REJEITO a alternativa de re-rodar `land-plan163-pin.sh` — além
  do risco de commit vazio, ela REVERTERIA o fix de timeout ao re-aplicar o
  pin-pack stale (R2, fato de manifest, não especulação).
- **OQ4 = delta-confirm 1 round (ACCEPT condicionado ao must-fix 4).** Sem a
  prova da negativa (41 linhas idênticas), 1 round não preserva a cadeia de
  evidência; com ela, um full re-review de 6 rounds seria custo sem ganho de
  segurança.
