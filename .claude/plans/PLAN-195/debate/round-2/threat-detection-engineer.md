---
round: 2
archetype: Threat Detection Engineer
skill: security-and-auth (§Detection-as-Code, references/detection-as-code.md)
agent_persona: Principal Threat Detection Engineer (VETO de escopo estreito — cobertura, FPR, operabilidade)
generated_at: 2026-10-01T03:16:17Z
---

> Base lida: HEAD `d572e374` — plano revisto, `round-1/consensus.md` e as três críticas da
> rodada 1. Toda afirmação sobre código abaixo foi conferida no disco nesta rodada; nada foi
> sondado contra o hook. Correção do meu frontmatter da rodada 1: o `generated_at` gravado lá
> era hora local rotulada como UTC (registrado no `anonymization-map.md`); este é UTC real.
> Aceito as correções da verificação: a janela móvel de 7 dias dá 17 + 10 (C7d; reconferi às
> 03:14Z: 17 `bash_parse_failed_fail_closed` + 10 `fact_gate_shadow_deny`), e o «≤ 3 em 7
> dias» do §4.4 é orçamento de uso do kill-switch, não de FPR (C20).

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- O plano revisto incorporou o essencial da minha rodada 1: `reason_code` próprio por classe
  (Thesis 7, W1a, W2 item 6), emitido uma vez por comando a partir de um único ponto (passada
  aditiva única), técnica mapeada no conteúdo da ADR-201, corpus sintético representativo
  (Prova (e)) e replay offline antes do land (OQ-1). A mutação por sub-regra (Prova (f)) é
  detection-as-code de verdade: prova que cada regra tem fixture que dispara.
- Falta uma coisa que transforma a observabilidade de promessa em fato: nada no plano PROVA
  que o evento é gravado. E o substrato tem um modo silencioso documentado — `emit_generic`
  com ação não registrada faz «breadcrumb + silent return» (`_lib/audit_emit.py`, docstring e
  primeiro `if` de `emit_generic`). Um nome de ação novo deixaria o painel de 7 dias em zero
  por construção, com todos os testes verdes.
- A proposta do K1 (BLOCK + rebaixamento pré-registrado para advisory, nunca ASK) atende a
  minha preocupação de FPR e de muting, com três condições de texto: número e denominador do
  limite na ADR-201, advisory que continua emitindo, e kill-switch que não desliga em
  silêncio.

## Risks

- **R2-TDE1 — HIGH — observabilidade não provada (painel zero por construção).** Conferido:
  `emit_generic` retorna em silêncio para ação fora de `_KNOWN_ACTIONS`; `veto_triggered` é
  registrada e está em `_EMIT_GENERIC_PASSTHROUGH` (os campos extras sobrevivem — conferi as
  chaves de um `fact_gate_shadow_deny` real no log: `command_sha256`, `gate_outcome`,
  `fact_gate_mode` presentes). `Decision` não tem campo de motivo-classe
  (`check_bash_safety.py:299-322`), então o emit vai sair de `main()` por um caminho novo — o
  ponto onde esse tipo de defeito nasce. A Prova (b) afirma a classe no `Decision`, não o
  EVENTO. *Mitigação:* must-fix 1.
- **R2-TDE2 — MEDIUM — o limite de rebaixamento pode virar número escolhido depois do dado.**
  A OQ-9 diz «limite fixado na ADR-201», sem número, sem denominador e sem definição
  operacional de «bloqueio legítimo». Com corpus pequeno, porcentagem não tem sentido; e sem
  a definição, a classificação manual do delta fica subjetiva. *Mitigação:* must-fix 2(a).
- **R2-TDE3 — MEDIUM — mute silencioso.** O kill-switch novo (W1a) é a alavanca de mute da
  regra; o do rawscan (`check_bash_safety.py:509-523`) não emite nada quando desligado. Se o
  novo herdar esse molde, desligar a regra não deixa rastro — o pecado capital do
  §Detection-as-Code. Hipótese (não medida): se o `env` de um arquivo de settings chega ao
  processo do hook, o desarme também passa pela escrita com alvo computado, que segue aberta
  até a W2 (o `.claude/settings.local.json` é canônico — oráculo 1 — e protegido só na grafia
  literal). *Mitigação:* must-fix 2(c).
- **R2-TDE4 — LOW — duplo sinal e desfecho final.** Com `destructive=True` (Thesis 7) o mesmo
  comando também emite `fact_gate_shadow_deny` (`check_bash_safety.py:1957-1968`); e, com o
  fact-gate em ENFORCE ou o piloto de citação armado, um bloqueio pode virar ALLOW por
  citação. Contar «bloqueios» pela soma dos dois códigos, ou contar o casamento como
  bloqueio quando o desfecho foi liberação, distorce a taxa. *Mitigação:* nice-to-have 2.
- **R2-TDE5 — LOW — corpus de um repositório só.** O replay mede o dogfood DESTE repo,
  moldado pelo guarda existente (o modelo já evita as formas bloqueadas) e sem a carga típica
  de adopter (instaladores por cano, por exemplo). O FPR do adopter é invisível ao
  mantenedor. *Mitigação:* nice-to-have 3.

## Must-fix (blocking)

1. **Prova de emissão (novo item na Prova de W1a/W1b e da W2).** Com o diretório de auditoria
   isolado (a suíte já tem o isolamento do `conftest`), cada linha BLOCK da passada nova e de
   `TestComputedCanonicalTarget` grava EXATAMENTE UM evento da ação já registrada
   `veto_triggered` (via `emit_veto_triggered` ou `emit_generic("veto_triggered", …)`,
   precedente do fact-gate, `check_bash_safety.py:1637-1690`), com o `reason_code` da classe e
   o campo de técnica; os controles de `TestIndirectLegitAllow` gravam ZERO eventos da classe
   nova. O plano declara que não se cria ação nova (logo, sem tocar o `_lib/audit_emit.py`,
   que é canônico). Sem isso, o «`reason_code` emitido» e a «contagem por 7 dias» são
   observabilidade de papel.
2. **Condições do K1 escritas no conteúdo mínimo da W1-ADR** (que landa antes do código, então
   o pré-registro sai antes do delta por construção):
   (a) tabela por sub-forma: classe (EQUIVALÊNCIA com a forma direta ⇒ meta zero; HEURÍSTICA
   ⇒ limite) — a regra do verbo computado (Thesis 4b) e os alimentadores opacos são
   HEURÍSTICAS —, o limite como NÚMERO ABSOLUTO de comandos legítimos distintos no corpus de
   replay, o denominador registrado junto (janela UTC, comandos, comandos distintos,
   sessões) e a definição operacional: falso-positivo = bloqueio novo em comando cuja forma
   direta equivalente seria ALLOW; bloqueio de comando cuja forma direta também é bloqueada é
   «consistente com a política», não falso-positivo;
   (b) sub-forma rebaixada para advisory continua emitindo o MESMO `reason_code` com desfecho
   distinto (ex.: campo `gate_outcome` de «faria bloquear»), para que a migração de ataque
   para ela fique visível;
   (c) kill-switch desligado ⇒ um evento por sessão da ação já registrada
   `learning_rail_disabled` (precedente A12 do fact-gate, `check_bash_safety.py:1715-1732`,
   usado em `:1872-1873`); e o kill-switch distingue, no mínimo, «desligar só as sub-formas
   heurísticas» de «desligar a passada inteira» — senão um falso-positivo num alimentador
   opaco empurra o operador a desligar também as regras de equivalência, o mesmo problema do
   rawscan um nível abaixo.

## Nice-to-have (advisory)

1. **Telemetria de forma residual.** Depois da cura, o atacante migra para os residuais
   declarados (verbo totalmente computado sem marcador, API destrutiva de outra linguagem).
   Um evento advisory (ALLOW) nas formas residuais que a passada RECONHECE estruturalmente é a
   única detecção dessa migração. Medir o volume no próprio replay; se for ruidoso, descartar
   com o número registrado.
2. **Contagem pelo casamento, desfecho separado.** O painel de 7 dias conta o `reason_code`
   novo (não soma com `fact_gate_shadow_deny`) e registra o desfecho final num campo
   (bloqueado / liberado por citação / advisory).
3. **Limitação do corpus declarada na ADR-201** (um repositório, viés de sobrevivência,
   retenção dos transcripts pela varredura do Claude Code) e a mensagem acionável traz o
   `reason_code`, para que um adopter consiga relatar um falso-positivo sem expor o comando.
4. **Controle legítimo da conjunção (Thesis 4).** Em `TestIndirectLegitAllow`, verbo
   computado com marcadores que também pertencem a verbos de cópia e de ligação (não do trio)
   ⇒ ALLOW; e os marcadores definidos POR VERBO do trio, não «qualquer flag com cara de
   destrutiva».
5. **Campo `project` vazio.** Medido: 473 dos 685 eventos do hook têm `project` vazio —
   exatamente os `bash_parse_failed_fail_closed`, cujo emit não passa `project` nem
   `session_id` (`check_bash_safety.py:2197-2202`). «Por projeto» funciona hoje pelo
   DIRETÓRIO da cadeia (por projeto desde a W1 do PLAN-182), não pelo campo; o emit novo deve
   preencher os dois a partir do evento do stdin (o adaptador já os tem,
   `_lib/adapters/claude.py:72`, `:82`). Fica como FU de telemetria, como o consenso decidiu.

## Unseen by the original plan

1. **O modo silencioso do `emit_generic`** (ação não registrada ⇒ breadcrumb e retorno, sem
   evento). É a forma concreta pela qual o must-fix 1 da rodada 1 pode ser «cumprido» no
   código e falhar no log. O plano não nomeia o risco nem a ação a usar.
2. **Kill-switch como canal de mute sem rastro** (R2-TDE3). O kill-switch próprio entrou pelo
   consenso (insight 10), mas sem o requisito de emitir quando desligado.
3. **A tag `destructive` deixa de significar «o trio».** O docstring de `Decision`
   (`check_bash_safety.py:315-320`) diz que `destructive=True` vale SÓ para os três matchers,
   porque o citation-gate e o fact-gate se apoiam nela. A extensão de vocabulário da W1b (A-9;
   A-8 conforme OQ-8) com `destructive=True` muda o que é liberável por citação e mistura
   esses bloqueios no `fact_gate_shadow_deny`. A ADR-201 precisa declarar a mudança de
   contrato, e o `reason_code` precisa separar trio de vocabulário estendido.

## What I would NOT change

1. **Passada aditiva única com um só ponto de evento** — resolve a minha preocupação da OQ-2
   (dois sítios, um sem telemetria) melhor do que o helper que eu tinha sugerido.
2. **BLOCK, nunca ASK.** Retiro o pedido de ASK: o canal não existe (`Decision` só tem
   allow/block/rewrite-ask, `check_bash_safety.py:299-322`) e sem humano um ASK trava. O
   rebaixamento para advisory é a válvula certa: granular por sub-forma e sem travar
   execução.
3. **Prova (b) e (f)** — afirmar a classe do motivo e exigir que desligar cada sub-regra
   deixe uma linha vermelha. Isso é «a regra dispara na fixture», não «a regra existe».
4. **Replay offline com só contagens no repo** e o delta classificado na evidência privada.
5. **Piso de literais só na W2** (ver K2 abaixo).

## Respostas da rodada 2

1. **Must-fix 1–4 da rodada 1:**
   - MF1 (`reason_code` distinto por classe, inclusive parte B) — **atendido** no texto
     (Thesis 7; W1a «emitido uma vez por comando»; W2 item 6, que reconhece que o bloqueio
     canônico não emite e que o fact-gate só roda sob `destructive`). Falta a PROVA de que o
     evento é gravado — must-fix 1 desta rodada.
   - MF2 (ASK-vs-BLOCK pré-registrado por sub-forma) — **em parte.** ASK saiu por fato de
     substrato (aceito); virou BLOCK-vs-advisory por sub-forma, que é a forma certa. Falta o
     número, o denominador e a definição de falso-positivo no conteúdo da W1-ADR — must-fix 2(a).
   - MF3 (corpus de controle legítimo representativo) — **atendido** (Prova (e) traz as
     categorias que pedi). Acréscimo opcional: nice-to-have 4.
   - MF4 (técnica mapeada) — **atendido** no conteúdo da W1-ADR e no C14; a verificação do
     campo entra no must-fix 1.
   - **VETO:** não cai ainda; cai com os must-fix 1 e 2 desta rodada escritos no plano — texto,
     sem código, sem nova rodada para mim (regra de parada: correção de texto não reabre).

2. **OQ-9 / K1.** Sim, atende a preocupação de FPR e de muting — o replay antes do land dá a
   estimativa pré-deploy que eu exigia, e o rebaixamento por sub-forma é a válvula granular
   que torna desnecessário desarmar o trilho inteiro. A alteração MÍNIMA, sem ASK, é o
   must-fix 2: (a) número absoluto + denominador + definição de falso-positivo na ADR-201;
   (b) advisory continua emitindo o mesmo `reason_code` com desfecho distinto; (c) kill-switch
   que emite ao ser desligado e que separa heurísticas de equivalências.

3. **K2.** Aceito, e corrijo minha posição da rodada 1: defendi o piso de literais em geral,
   mas na posição do verbo ele vira ALLOW por aritmética — o piso conta caracteres literais
   do nome-base (`_E4_GLOB_MIN_LITERALS = 4`, `check_bash_safety.py:2569`, uso em `:2935`) e os
   nomes do trio têm 2 e 3 letras; a nota do arquivo exemplifica a posição de operando
   (`:3461-3466`). Piso só na W2 (alvo de caminho). A regra de conjunção da Thesis 4 é a
   escolha de precisão certa (exige verbo indecidível E marcador literal do trio), com duas
   condições já no must-fix 2(a) e no nice-to-have 4: ela é HEURÍSTICA (entra na tabela de
   rebaixamento) e os marcadores são definidos por verbo do trio.

4. **OQ-1 revista.** Suficiente como orçamento pré-deploy, desde que o denominador e a
   definição de falso-positivo do must-fix 2(a) estejam escritos, e que o replay seja
   diferencial nos dois sentidos: ALLOW→BLOCK contado e classificado; BLOCK→ALLOW tem de ser
   zero (a passada é aditiva, então qualquer caso é defeito). A contagem por 7 dias por
   projeto só vale com o must-fix 1 (evento provadamente gravado) e é por DIRETÓRIO da
   cadeia, não pelo campo `project` (nice-to-have 5).

5. **Afirmação falsa ou P0.** Nenhum P0 novo. Nenhuma afirmação falsa sobre o código que
   justifique NO-GO. Duas correções de texto:
   - **Contradição interna (P3 de texto):** a primeira «Alternativa descartada»
     (`PLAN-195:197-200`) ainda diz que «a cura tem de usar o esqueleto com piso de literais»
     e atribui a nota de lockout à «posição de comando/alvo»; a própria verificação do
     consenso (C2c) registra que a nota exemplifica a posição de OPERANDO, e a Thesis 4 decide
     verbo SEM piso. Restringir a alternativa à posição de operando/alvo e apontar a Thesis 4
     para o verbo.
   - **Referência de linha:** a W2 item 6 cita `:3838-3841` para o bloqueio canônico sem
     `destructive`; o sítio é `check_bash_safety.py:3839-3842` (comentário, chamada, `if`,
     `return`). Imaterial.

## VETO

**Mantido, condicional e reduzido.** Cai quando o plano trouxer, por texto: (1) o item de
prova de emissão do must-fix 1 (evento gravado da ação registrada `veto_triggered`, um por
linha BLOCK, zero nos controles, sem ação nova); (2) as condições (a)–(c) do must-fix 2 no
conteúdo mínimo da W1-ADR. Não peço nova rodada: conferido o texto, o VETO está retirado.

## Esforço

- Edição do plano (CEO) para os must-fix 1 e 2: ~10-20k tokens, dentro da sessão corrente.
- Impacto na implementação, absorvido em W1a/W1b/W2 sem sessão nova e sem path novo (a ação
  `veto_triggered` já é passthrough e `learning_rail_disabled` já é registrada — nada no
  `_lib/audit_emit.py`): teste de emissão ~30-60 linhas (~20-40k tokens); breadcrumb do
  kill-switch e desfecho do advisory ~15-25 linhas no hook (~10-20k tokens).
- Nice-to-have 1 (telemetria de residual): ~20-40k tokens, medido no próprio replay.
- `external_wait`: inalterado (GPG do Owner por pacote; fechamento do debate).

## Confirmação do VETO (pós-edição)

Sujeito lido (o veredito vale só para ele): `git diff -- .claude/plans/PLAN-195-bash-guard-indirect-execution.md`
sobre a base `d572e374`, árvore de trabalho NÃO commitada; sha256 do arquivo lido
`fc48632ae97c16c1e72a4710b413b43929baa2038c6f513ea47144b3d7370a99`, conferido em
2026-10-01T03:24:47Z. Se o texto commitado divergir deste, a confirmação não se estende a ele.

1. **Prova de emissão (must-fix 1) — ATENDIDA.** O item (k) da Prova da W1 exige, com o
   diretório de auditoria isolado pelo `conftest`, EXATAMENTE UM `veto_triggered` por linha
   BLOCK, com `reason_code` da classe e campo de técnica; ZERO eventos da classe nova nos
   controles de `TestIndirectLegitAllow`; `learning_rail_disabled` uma vez com o kill-switch
   desligado; desfecho «faria bloquear» na sub-forma rebaixada; nenhuma ação nova. Os
   checkboxes de W1a e W1b passam a citar a prova (a)-(k). A W2 herda (k) por nome e afirma o
   evento próprio do bloqueio canônico com alvo computado (a técnica vem pela herança de (k)).
   O conteúdo da W1-ADR declara a observabilidade sem ação nova e o motivo (o `emit_generic`
   descarta ação não registrada em silêncio; `_lib/audit_emit.py` não é tocado). Detalhe
   imaterial: o precedente citado `:1715-1733` termina em `:1732`.
2. **Condições do K1 na W1-ADR (must-fix 2) — ATENDIDAS.** (a) Tabela por sub-forma com
   classe equivalência × heurística (verbo computado e alimentadores opacos como heurísticas),
   limite como número absoluto de comandos legítimos distintos, denominador (janela UTC,
   comandos, distintos, sessões) e definição operacional de falso-positivo — fixada ANTES do
   replay. (b) A sub-forma rebaixada segue emitindo o mesmo `reason_code` com desfecho «faria
   bloquear» e entra nos residuais. (c) Kill-switch com dois níveis («só heurísticas» e
   «passada inteira») que emite `learning_rail_disabled` uma vez por sessão quando desligado.
   O texto vai além do que pedi em dois pontos que fortalecem a operabilidade: o rebaixamento
   é por cerimônia, não por configuração de runtime (o único botão em runtime é o kill-switch,
   que fica visível no log); e uma sub-forma cujo produtor visível baixa da rede nunca é
   rebaixada.

Também conferidos no diff: replay diferencial nos dois sentidos com BLOCK→ALLOW = zero (prova
(i)); mudança de contrato da tag `destructive` declarada na W1-ADR, com `reason_code`
separando trio de vocabulário estendido (W1b); limitações do corpus declaradas; Alternativa 1
restrita à posição de operando/alvo, com a Thesis item 4 para o verbo (o P3 que apontei).

VETO: RETIRADO

## Reconfirmação sobre o sha256 final

Sujeito: `.claude/plans/PLAN-195-bash-guard-indirect-execution.md` na árvore de trabalho (não
commitado; HEAD `d572e374`), sha256 calculado por mim
`9894151f1648b0f7743cea526a89eab37f97f67326ae6b3c25227865ec6e0406`, em 2026-10-01T03:32:57Z.
As três mudanças foram conferidas no arquivo atual e contra o código.

1. **W1-ADR — coerção do `learning_rail_disabled`: ACEITA.** Conferi no código: o ramo de
   `emit_generic` para essa ação troca `rail` fora de `_LEARNING_RAIL_ENUM` por `observe` e
   `switch` fora de `_LEARNING_SWITCH_ENUM` por `other` (`_lib/audit_emit.py:7585-7591`;
   enumerações em `:8316-8322`). A ação não é passthrough. Emitida com o nome do kill-switch
   novo, ela gravaria um desarme atribuído ao trilho de aprendizado — exatamente o mute mal
   atribuído que o meu must-fix 2(c) queria evitar. Fui eu que propus essa ação sem conferir o
   esquema dela; a correção é devida. As duas saídas (estender as enumerações ou usar outra
   ação já registrada cujo esquema caiba) são aceitáveis do ponto de vista de detecção.
   Observação, sem bloquear: se a ADR escolher estender as enumerações, o
   `SPEC/v1/audit-log.schema.md` (canônico, oráculo 1) documenta essas mesmas enumerações
   fechadas, com a coerção, na linha do `learning_rail_disabled` (`:484`). Estender o código sem
   essa linha produz deriva entre o produtor e o esquema documentado. O caminho condicional são,
   então, dois arquivos canônicos (mais a linha de versão do SPEC, se a convenção pedir), não um.
   Recomendo uma oração de texto na W1-ADR e na lista de paths da W1a.
2. **Prova (k) — CONTEÚDO, não só contagem: ACEITA.** O teste passa a afirmar os campos do
   evento de desarme com os valores do kill-switch novo, e não os coagidos. Isso fecha a forma
   de falha acima. Observação, sem bloquear: o texto nomeia `rail`/`switch`, o esquema do
   `learning_rail_disabled`. Se a ADR escolher outra ação, o teste afirma os campos
   equivalentes. E os DOIS níveis do kill-switch («só heurísticas» × «passada inteira») devem
   ser distinguíveis no conteúdo do evento, porque são riscos diferentes.
3. **W2 — exceção declarada ao «BLOCK→ALLOW = zero»: ACEITA.** É a forma certa de manter vivo um
   detector de regressão diante de uma correção deliberada de falso-positivo. A exceção cobre só
   as transições do ramo do verbo de busca limitado ao segmento. Cada uma é classificada à mão
   como falso-positivo corrigido, com contagem e denominador no pacote (prova (i)), e qualquer
   outra transição BLOCK→ALLOW segue sendo defeito. A mensagem A3 não muda veredito.

As duas observações dos itens 1 e 2 são correção de texto (P3) e não condicionam a retirada:
nenhuma deixa a regra invisível, e o teste de conteúdo do item 2 pegaria a coerção.

VETO: RETIRADO (sha256 9894151f)
