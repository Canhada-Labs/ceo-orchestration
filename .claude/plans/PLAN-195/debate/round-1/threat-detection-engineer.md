---
round: 1
archetype: Threat Detection Engineer
skill: security-and-auth (§Detection-as-Code)
agent_persona: Principal Threat Detection Engineer (detection-coverage VETO holder)
generated_at: 2026-09-30T21:35:00Z
---

## Verdict

ADJUST

(Levanto **VETO** de escopo estreito — cobertura de detecção / orçamento de FPR /
operabilidade da regra. Não é REJECT: o desenho reusa o instrumento certo. O VETO
cai assim que os must-fix de observabilidade estiverem no texto do plano, antes do
flip `draft → reviewed`.)

## Summary (≤ 3 bullets)

- A tese está correta pela doutrina de detecção: curar a CLASSE pela FORMA com o
  esqueleto do E4 + piso de literais (`check_bash_safety.py:2569`, nota de lockout
  `:3464-3465`) é um mecanismo de PRECISÃO já pré-afinado contra bypass real, e o
  controle vermelho→verde (exit 1, não exit 5) é detection-as-code honesta — a regra
  sobe com fixture que dispara e com fixture que NÃO dispara.
- O ponto fraco é de OBSERVABILIDADE, e é mais grave do que o plano admite: o bloqueio
  destrutivo direto só vira telemetria via `fact_gate_shadow_deny` (`:1957-1968`,
  default-on, porque carrega `destructive=True`), e o bloqueio de escrita canônica E3
  **não emite nada** — não seta `destructive=True` (`:3840-3842`), então pula o
  fact-gate (`:4166`); o único emit do E3 é na FALHA de parse (`:2197`). A regra nova
  da parte B nasceria, hoje, sem nenhum sinal — FPR e deriva ficam inauditáveis.
- Falta o compromisso ASK-vs-BLOCK por sub-forma. Hard-BLOCK numa forma de corpo opaco
  (cano para interpretador, decodificação) sem estimativa de FPR pré-deploy treina o
  operador a desarmar o trilho (`CEO_BASH_RAWSCAN=0`) — o equivalente a "mutar" a
  regra, o pecado capital do §Detection-as-Code.

## Risks

- **R-TDE1 — HIGH — regra nova cega (parte B sem telemetria).** Verificado:
  `_e3_check_canonical_path_write` devolve o bloqueio por `Decision(allow=False,
  reason=…)` em `check_bash_safety.py:3842` SEM `destructive=True`; em `main()` o
  fact-gate e o citation-gate só rodam sob `decision.destructive`
  (`:4166`); as caudas de emit restantes (`:4182-4214`) são de credencial / git-bypass
  / env / egress / rewrite — nenhuma casa um bloqueio de escrita canônica. Logo uma
  regra de alvo COMPUTADO que bloqueie não deixa rastro. Medido no log vivo: em 7 dias,
  só `bash_parse_failed_fail_closed` (20) e `fact_gate_shadow_deny` (17); zero evento de
  match canônico real. *Mitigação:* a cura emite um `reason_code` DISTINTO por classe
  (ex.: `indirect_destructive_blocked`, `computed_canonical_target_blocked`) via
  `emit_veto_triggered`/`emit_generic`, com `blocked_tool="Bash"`, para a parte B TAMBÉM
  (que hoje não passa pelo fact-gate). Sem isso não há como medir FPR nem deriva.
- **R-TDE2 — HIGH — FPR não estimada antes do deploy numa forma de alto ruído.** O
  cano para interpretador e a decodificação→cano entregam ao hook BYTES OPACOS; o
  esqueleto do E4 não tem o que casar. Um BLOCK amplo aqui colide com uso legítimo
  corriqueiro e estoura o orçamento (≤ 3/7d do §4.4 do guards doc, `:162-168`). O plano
  junta essas formas em "BLOCK/ASK" sem decidir. *Mitigação:* decisão PRÉ-REGISTRADA
  por sub-forma — BLOCK só onde o esqueleto nomeia DETERMINISTICAMENTE o verbo
  destrutivo (corpo `-c`/`eval` com literal); ASK (prompt de permissão, precedente da
  reescrita H5 force-push `:3909-3916`) para corpo opaco. "Afinar depois do deploy" é
  anti-padrão nomeado do §Detection-as-Code.
- **R-TDE3 — MEDIUM — corpus de controle legítimo fino demais.** O plano cita um único
  controle ALLOW (`echo "…"`). O §Detection-as-Code exige fixture should-NOT-fire
  representativa do tráfego real, senão o FPR pré-deploy é fictício. *Mitigação:*
  `TestIndirectLegitAllow` versiona um corpus sintético que espelha formas de dogfood
  reais (interpretador dirigido por variável `python3 $SCRIPT` → esqueleto `python3 *`;
  `xargs` com verbo não-destrutivo; `find` sem remoção por predicado; `bash -c` com
  verbo legítimo), não só o `echo`.
- **R-TDE4 — MEDIUM — sem mapeamento de técnica (coverage de papel).** O emitter
  forense existente carrega `atlas_technique` (`audit_emit.py:12857`, T1565.001); as
  classes novas (interpretador/scripting; impair-defenses/bypass; deleção de arquivo)
  não têm técnica atribuída. Pela doutrina Pass-1, alegar cobertura sem fixture que
  dispara + técnica mapeada é cobertura de papel. *Mitigação:* mapear cada `reason_code`
  novo a uma técnica no emit, como o forense já faz.
- **R-TDE5 — MEDIUM — fonte de log incompleta (atribuição).** Medido: 685/685 eventos
  deste hook com `session_id=''`. Qualquer painel por-sessão ou dedup por sessão do novo
  sinal é impossível com o emit atual. *Mitigação:* popular `session_id` a partir do
  stdin já bufferizado (o citation-gate já extrai `transcript_path`, `:4167`), OU
  declarar que o painel de taxa é por-PROJETO, não por-sessão — e dizer isso no plano.
- **R-TDE6 — LOW — deriva de assinatura / ciclo de vida.** FPR não é medível do log
  (o plano admite). Então o único modo de saber que a regra NÃO quebrou é o replay de
  fixture no CI (cobre "regra quebrada") + um contador de disparos por 7d (cobre "regra
  silenciosa"). Sem o `reason_code` distinto (R-TDE1), o contador não existe.

## Must-fix (blocking)

1. **Emitir um `reason_code` DISTINTO por classe nova, inclusive na parte B.** A regra
   de alvo computado NÃO passa pelo fact-gate hoje (`:4166`), então precisa de emit
   próprio. Fixar o nome do evento e o `blocked_tool="Bash"` no plano. (Fecha R-TDE1.)
2. **Pré-registrar a decisão ASK-vs-BLOCK por sub-forma antes de escrever a regra.**
   BLOCK só onde o esqueleto nomeia o verbo destrutivo de forma determinística; ASK para
   corpo opaco (cano para interpretador, decodificação). Essa decisão É o orçamento de
   FPR. (Fecha R-TDE2.)
3. **Versionar um corpus de controle legítimo (should-NOT-fire) representativo**, não o
   `echo` isolado — é o piso de FPR pré-deploy. (Fecha R-TDE3.)
4. **Mapear cada `reason_code` novo a uma técnica** (ATT&CK/ATLAS) no emit, paridade com
   o forense. (Fecha R-TDE4.)

## Nice-to-have (advisory)

1. Popular `session_id` no emit do hook (a partir do stdin já lido) ou declarar o painel
   de taxa como por-projeto. (R-TDE5.)
2. Painel/alarme de taxa 7d por `reason_code` novo + replay de fixture no CI como
   detector de deriva/regra-quebrada. (R-TDE6.)
3. Dedup: um comando com múltiplas sub-formas destrutivas deve emitir UM evento canônico,
   não um por match (evitar tempestade de alerta).

## Unseen by the original plan

1. **As classes A e B não têm backup forense PostToolUse.** Verificado:
   `check_bash_canonical_forensic.py:149-152` só emite no prefixo `!` E só para alvo de
   ESCRITA canônica — não para destrutivo indireto nem para alvo computado. O §5 do
   guards doc vende o forense como "belt-and-suspenders", mas para exatamente estas
   classes o PreToolUse é a ÚNICA detecção. Isso eleva a régua sobre acertar a
   observabilidade do PreToolUse (ligado ao must-fix 1) e o plano não nomeia esse ponto
   cego. A W0 deveria registrá-lo junto com as três afirmações falsas que já corrige.
2. **A premissa do OQ-1 ("o log só registra bloqueios") subestima o buraco.** Bloqueio
   de escrita canônica não é registrado DE FORMA ALGUMA hoje; bloqueio destrutivo só via
   o código compartilhado `fact_gate_shadow_deny`. O argumento do plano (sem corpus de
   PERMITIDOS) permanece válido, mas a conclusão operacional muda: o problema não é só
   "não dá para medir FPR", é "não dá para ver a regra disparar".
3. **Kill-switch como vetor de muting.** `CEO_BASH_RAWSCAN=0` (`:506-523`) desarma o
   rawscan inteiro. Se a regra nova reusa esse ramo e for ruidosa, o operador desarma
   TUDO. Um `reason_code` distinto + ASK nas formas opacas reduzem a pressão de desarme.

## What I would NOT change

1. Reuso do esqueleto do E4 com piso de literais em vez de fail-closed cego — é a
   escolha de PRECISÃO correta; o lockout do fail-closed cru está documentado no próprio
   arquivo (`:3464-3465`) e o plano o rejeita com razão.
2. O controle vermelho→verde com exit 1 (exit 5 não vale) e uma linha por FORMA, não por
   exemplo — isto é detection-as-code bem feita.
3. A recusa de leitura como troca de MENSAGEM apenas, sem allowlist de leitura (doutrina
   `:2492-2495`) — correto; allowlist abriria bypass de escrita.
4. Divulgação só pela FORMA, regra de 3 rodadas e a sequência W1→W2 no mesmo arquivo.

## Respostas às OQs

- **OQ-1 (orçamento de FPR / observabilidade).** Não tente medir FPR do log de bloqueios
  vivo — para a parte B ele é VAZIO (R-TDE1) e para a parte A é um código compartilhado
  de shadow. Três alavancas, nesta ordem: (a) corpus sintético versionado de controles
  legítimos = o piso de FPR PRÉ-deploy (must-fix 3); (b) `reason_code` distinto por
  classe + painel de taxa 7d por-projeto + replay de fixture no CI = regressão/deriva
  pós-deploy (must-fix 1 + nice-to-have 2); (c) ASK-vs-BLOCK por sub-forma, BLOCK só onde
  o esqueleto nomeia o verbo, ASK no corpo opaco (must-fix 2). O limite ≤ 3/7d do §4.4
  (`:162-168`) é do kill-switch de bypass, não desta regra — não reusar o número sem
  medir; deixar o orçamento da regra nova ancorado no corpus sintético, não no log.
- **OQ-2 (heredoc/aspas e os dois sítios).** UM helper único chamado pelos DOIS sítios
  (`decide_command` `:3891-3896` e `_recheck_whole_command` `:601`), herdando o
  fail-closed de `shlex` já existente. Crítico pela minha lente: o helper tem de emitir
  o MESMO `reason_code` distinto a partir dos dois sítios — senão um caminho dispara e o
  painel de taxa não enxerga, criando um ponto cego de detecção silencioso.
- **OQ-3 (`.mcp.json`/`CLAUDE.md` na parte B).** Confirmei que os dois NÃO são
  `_CANONICAL_GUARDS` hoje (oráculo `--is-canonical` = 0 para ambos). Adicioná-los muda a
  superfície de DUAS detecções (blocker + forense) e o perfil de FPR — é decisão de
  threat-model própria, com fixture própria, NÃO fold silencioso na W2. Recomendo: fora
  da W2; só entra se o threat-model listar esses arquivos como alvo de escrita canônica,
  e aí com sua própria linha de matriz e fixture.
- **OQ-4 (lacuna argv, B-6).** Parte B. Verifiquei que o laço de corpo `-c`
  (`:2333-2345`) faz `break` após o corpo e não inspeciona os posicionais seguintes, por
  isso o caminho canônico como `argv` escapa — é problema de ALVO de escrita computado,
  não de indireção de execução. Uma linha na matriz + emissão do `reason_code` da parte
  B. Concordo com o padrão do CEO (W2).

## Esforço

- W1 (parte A, cura + rail): ~300-600k tokens, ~1 sessão de execução + cerimônia.
- W2 (parte B, cura + rail): ~300-600k tokens, ~1 sessão + cerimônia.
- Acréscimo dos must-fix de observabilidade (reason_codes distintos + mapeamento de
  técnica + corpus sintético de controles + instrumento de taxa): ~80-150k tokens,
  absorvidos dentro de W1/W2 — sem sessão nova.
- `external_wait`: assinatura GPG do Owner por wave canônica; fechamento do debate L3
  antes de tocar o hook. Nenhum prazo de calendário interno além das cerimônias do Owner.
