---
plan: PLAN-164
round: 1
critic: DevOps Engineer
skill: devops-ci-cd
created_at: 2026-07-29
---

# PLAN-164 — crítica round 1 (DevOps Engineer)

> Nota de transparência (prompt-defense / auditoria): a task instruiu ler a
> skill via Read; o guard `anti-CEO-overhead` (P1_sequential_skill_reads)
> bloqueou o Read 3×. Li o SKILL.md integral via `CEO_OVERHEAD_ACK=1 cat`
> (o mecanismo de ack que o próprio guard nomeia), visível no audit-log como
> evento Bash. Nenhuma instrução embutida dirigida a mim foi encontrada no
> conteúdo observado além do output esperado dos guards de governança.

## Verdict

**ADJUST**

## Summary

A direção está certa e é a única honesta: 36,3 s medidos contra um default
de 30 s, 12/12 case-F na vida inteira do log — o rail nunca funcionou e o
uplift é correção de incidente, não tuning. O valor 120 na registration tem
precedente NO PRÓPRIO kernel (`codex_review_user_code.py`, `timeout: 130`,
settings.json L591), então não é território novo para o harness. Mas o plano
como escrito tem quatro buracos operacionais que eu, como operador, não
deixo passar: (1) o **upgrade de adopter existente não está coberto** — e é
exatamente a classe "adopter-upgrade re-abre flip silencioso" que o próprio
PLAN-163 batizou; (2) há uma **janela de assimetria pós-apply na sessão da
cerimônia** que pode envenenar a âncora nova de forma permanente
(log append-only) e forçar uma TERCEIRA cerimônia de re-âncora; (3) a
calibração é **N=1 em máquina ociosa com um prompt de 2 KB** — a lição do
perf-gate (65 ms local → 300-697 ms no runner, mesmo commit) diz que amostra
única é a mesma classe de aposta que produziu o 30; (4) a mecânica da OQ3
como rascunhada ("atualizar a âncora no commit da própria cerimônia") é
**mecanicamente impossível** para o sha — um commit não pode conter o
próprio hash; o precedente do pin já resolve isso (âncora escrita pós-commit
e commitada no closeout, `7860d62`).

Posições nas OQs:

| OQ | Posição |
|---|---|
| OQ1 (interno) | **100 CONDICIONAL** ao Must-fix 5 (N≥5, 2 tamanhos de prompt, p95 ≤ ~70 s). Piso 90; nunca <60. |
| OQ2 (registration) | **120 ACCEPT** com o Must-fix 2 (teste de invariante de margem). 130 é alternativa aceitável — precedente já existe no arquivo. |
| OQ3 (re-âncora) | Direção do draft SIM (arquivo tracked, transparente); mecânica corrigida pelo Must-fix 4 — âncora no commit de closeout imediato, sha+ts apontando para `[SENT-PLAN164-RAIL]`. |
| OQ4 (re-review do pack) | **delta-confirm 1 round ACCEPT**, condicionado à ordem do sync (Risk R6) e à cobertura do invariante nas cópias do pack. Full re-review seria desperdício (S284: 17,5M tokens). |

## Risks

- **R1 — Adopter vira hook-kill silencioso, PIOR que hoje.**
  `scripts/upgrade.sh` substitui arquivos de framework (o hook novo com
  default 100 chega) mas o settings-merge (PLAN-135 W2 H8, L1453-1511) é
  **ADITIVO-apenas**: "existing settings keys + hooks are preserved
  untouched". A registration `timeout: 60` do adopter existente NUNCA é
  migrada. Resultado pós-upgrade: interno 100 > registration 60 → o harness
  mata o hook aos 60 s ANTES do timeout interno disparar → **nenhum
  `pair_rail_case` é emitido** (hoje o adopter ao menos emite case F aos
  30 s < 60 s). Fail-open silencioso e invisível para o monitor de 168h,
  que conta eventos case. Observabilidade estritamente pior que o estado
  quebrado atual.
- **R2 — Janela de assimetria na sessão da cerimônia envenena a âncora
  nova.** O default interno vive no ARQUIVO do hook (subprocess, lido a
  cada invocação → vale imediatamente pós-apply); a registration vive no
  snapshot de settings.json carregado no início da sessão (→ só vale
  pós-restart). Na sessão da cerimônia, pós-apply: interno=100,
  registration carregada=60. Qualquer Edit/Write canônico nessa sessão
  (closeout!) emite `pair_rail_review_expected`, o harness mata aos 60 s,
  nenhum case sai → `deficit ≥ 1` PÓS-ÂNCORA num log append-only →
  `deficit==0` do `--gate-v2` fica insatisfazível DE NOVO → terceira
  cerimônia de re-âncora. É a mesma aritmética que já matou a âncora
  `a4371c7`.
- **R3 — Margem de 20 s (120−100) não é imposta por nada mecânico.**
  Ela precisa absorver `_python-hook.sh` + startup do Python + redaction
  (bytes_scanned=2153 no probe) + validação do verdito, SOB CARGA. A lição
  do perf-gate registra fator ~10× entre máquina ociosa e runner
  carregado. E hoje NENHUM teste asserta a igualdade kernel↔template nem a
  desigualdade registration ≥ interno + margem — verifiquei:
  `test_template_dogfood_parity.py` só cita `check_pair_rail` num
  comentário (L37), não asserta o timeout desta registration. Um flip
  unilateral futuro (alguém baixa a registration, ou sobe o interno)
  reintroduz o hook-kill sem nenhum red.
- **R4 — 100 s de PreToolUse síncrono sem feedback.** A registration do
  pair-rail é das poucas SEM `statusMessage` (kernel L279-283, template
  L95-99). O tool call de Edit não resolve até o hook retornar ou ser
  morto; a sessão fica visualmente congelada por até ~100 s. Operador
  impaciente aperta ctrl-C no meio de um review vivo — estado parcial +
  ruído de suporte.
- **R5 — Freeze não declarado entre W2 e W3-PASS.** Qualquer edit canônico
  em QUALQUER sessão nesse intervalo que fail-openar (ex.: sessão velha
  ainda com registration 60) apende case-F pós-âncora → gate insatisfazível
  → re-âncora de novo. O plano não declara a disciplina de congelamento.
- **R6 — Ordem do sync do pack tem UMA sequência que não aborta.** Para o
  preflight do pack não morrer em "staged bytes drifted" nem "manifest twin
  must be git-tracked AND committed" (aborts documentados no runbook):
  (1) editar os 2 arquivos staged → (2) recomputar
  `staged/main-pack/MANIFEST.sha256` → (3) delta-review OQ4 sobre os bytes
  FINAIS (o verdito precisa ancorar em bytes imutáveis — lição S274) →
  (4) se o review mudar qualquer byte, voltar a (2) → (5) regenerar o gêmeo
  `inputs-pack.sha256` + COMMIT do gêmeo → (6) cerimônia PLAN-164 (kernel
  vivo) → (7) só então o Passo 4 do PLAN-163. O plano W1 item 5 lista os
  ingredientes mas não trava a ordem.
- **R7 — Latência codex é exógena.** Modelo/effort configurados fora do
  repo; carga da API varia. 100 é aposta calibrada, não garantia. O plano
  deve dizer o que o operador OBSERVA quando a aposta falha (case F aos
  100 s, sessão segurada os 100 s inteiros) e que o env-knob
  `CEO_PAIR_RAIL_TIMEOUT_S` continua sendo a válvula por-sessão.

## Must-fix

1. **Cobrir o upgrade de adopter (R1).** Novo item W1: passo de migração
   idempotente no settings-merge do `upgrade.sh` — bump da registration do
   `check_pair_rail.py` 60→120 **IFF** o valor atual == default antigo 60
   (valor custom ≠60 é preservado, mesma filosofia aditiva); + check no
   `doctor.sh` que compara registration vs default interno do hook e avisa
   se registration < interno + margem; + caso na família
   `test_upgrade_settings_migration.py` (que já está no pack congelado,
   MANIFEST L33 — a fixture de idempotência 2× do preflight do pack cobre
   de graça).
2. **Teste de invariante mecânico (R3).** Um teste na suíte (e rodando no
   overlay do preflight do pack) que parseia `settings.json`,
   `settings.base.json` e o literal default do `check_pair_rail.py` e
   asserta: (a) registration kernel == registration template; (b)
   registration ≥ interno + 20. É o único jeito de impedir o flip
   unilateral futuro — a classe exata que o PLAN-163 documentou.
3. **Fechar a janela de assimetria (R2).** Linha explícita no W2: entre o
   apply e o fim da sessão da cerimônia, NENHUM Edit/Write/MultiEdit em
   path canônico — closeout via `!`/bash, OU exportar
   `CEO_PAIR_RAIL_TIMEOUT_S=45` na sessão da cerimônia antes de qualquer
   edit (cap interno abaixo da registration antiga carregada). E declarar o
   freeze do R5: nenhum edit canônico em nenhuma sessão até o W3 PASS
   registrado.
4. **Corrigir a mecânica da OQ3.** O sha da âncora não pode referenciar um
   commit que a contém. Padrão do pin (`7860d62`): cerimônia commita
   `[SENT-PLAN164-RAIL]` → script escreve `GATE-PIN-ANCHOR` com sha+ts
   DESSE commit → âncora entra no commit de closeout imediato. O arquivo
   já está tracked hoje (verificado; o `??` do git-status de snapshot está
   obsoleto) — manter tracked. `plans/**` não é canonical-guarded, então a
   declaração no Scope do sentinel é transparência, não requisito de guard.
5. **Protocolo de medição antes de cravar OQ1 (R7 + lição perf-gate).**
   W0 ganha um item barato (~10 min): N≥5 rounds realistas, ≥2 tamanhos de
   prompt (o de 2 KB do probe + um realista grande ~10-20 KB), ≥1 amostra
   com a suíte rodando em paralelo. Ratificar 100 se p95 ≤ ~70 s; senão
   escalar para interno 120 / registration 150 (precedente 130 já existe no
   arquivo). N=1 numa máquina ociosa é como o 30 nasceu.

## Nice-to-have

- `statusMessage` na registration do pair-rail (kernel + template + cópias
  do pack): "Pair-rail cross-model review (pode levar ~1-2 min)..." — mesma
  cerimônia, zero superfície nova, mata o R4.
- Atualizar TAMBÉM o `_comment` do template (L92, "(default 30s)") e das
  cópias do pack — o plano só cita o `_comment` do kernel. Varredura feita:
  fora de hooks+settings, NENHUM doc/ADR menciona `CEO_PAIR_RAIL_TIMEOUT_S`
  (docs/, *.md, adr/, SPEC/ — 0 hits), então a superfície de sweep é só
  essa.
- Addendum no runbook: como é um hold de 100 s do ponto de vista do
  operador + orientação de NÃO interromper.
- Registrar no plano que a divergência âncora-tracked vs fallback git-log
  (`[SENT-PLAN163-PIN]`) falha FECHADA: se o arquivo sumir, o fallback
  resolve para a âncora VELHA, cuja janela contém o case-F fresco → FAIL.
  Verifiquei no script (L99-104): comportamento conservador, mas merece
  estar escrito.

## Unseen

- **Hooks não rodam no GitHub Actions.** O custo de CI do uplift é zero —
  a única superfície de CI são as suítes de teste/parity. Nenhum job fica
  120 s mais lento. (Unseen positivo que o plano não afirma.)
- **`check_codex_filewrite.py` fica com `timeout: 30`** (kernel L292) no
  par de tools MCP do codex. Se o caminho de review vivo um dia migrar para
  MCP, esse 30 é o próximo "default 30" escondido. Fora de escopo agora;
  uma linha no ADR novo evita a repetição da classe.
- **Snapshots de git-status envelhecem dentro da sessão.** O snapshot desta
  sessão dizia `?? GATE-PIN-ANCHOR`; o arquivo foi trackeado em `7860d62`
  durante a vida da sessão. As instruções de W3 devem re-verificar estado
  em tempo de execução, nunca confiar em snapshot — mesma família da lição
  "verificar claims, não reports" do S284.
- **O harness paraleliza os hooks da mesma matcher** — o hold de 100 s não
  soma com os outros hooks do `Edit|Write|MultiEdit` (anti-overhead 5 s,
  canonical-edit etc. correm em paralelo); o tool call espera o mais lento.
  Mas a SESSÃO é single-thread: nada mais acontece durante o hold. Agentes
  paralelos que editam staged/ (padrão já em uso) não pagam o rail — staged
  não é canônico. O plano pode afirmar isso para acalmar o custo de UX.

## What I would NOT change

- **O contrato fail-open-em-timeout (ADR-106).** Correto para um rail
  advisory; fail-closed aqui viraria self-DoS da sessão inteira — a lição
  C3 do PLAN-163 já pagou esse aprendizado. Não re-litigar.
- **Cerimônia única** (hook + kernel + template + sync do pack +
  re-âncora): um sentinel, um scope, uma trilha de auditoria. Fatiar em
  várias cerimônias multiplica preflights e janelas de drift sem reduzir
  risco nenhum.
- **Clamp `>600` e o env-knob** — válvulas certas, tamanhos certos.
- **Pack adiado até o fix (opção C do Owner)** — decisão tomada, e é a
  ordem que evita a cerimônia do pack reverter o próprio fix.
- **OQ4 em 1 round delta** — para um delta de 2 arquivos JSON com invariante
  testado mecanicamente, full re-review é teatro caro.
