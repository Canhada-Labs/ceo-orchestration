---
plan: PLAN-164
round: 1
critic: VP Engineering
skill: core/architecture-decisions (sha256=f568c8f7…)
created_at: 2026-07-29
---

# PLAN-164 — crítica round 1 (VP Engineering)

## Verdict

ADJUST

## Summary

A direção está certa: o incidente é medido (36,3 s reais contra um budget
de 30 s; 12/12 case-F na vida do log), a opção C do Owner é a resposta
madura, e a cerimônia única (uplift + paridade + sync do pack + re-âncora
num só sentinel) é o desenho de menor superfície. Eu não ataco a tese —
ataco quatro pontos de coerência que o plano deixa abertos e que eu
verifiquei contra o código real:

1. **O plano decide "amend vs ADR novo" no vácuo, mas a decisão está
   constrangida por um interlock fail-closed que o plano não menciona.**
   `land-plan163-pack.sh:242` morre se a contagem de ADRs pré-apply ≠ 181,
   `:477` exige 183 pós-apply, e o pack congelado JÁ CONTÉM
   `ADR-183-directory-added-notification-events.md` (MANIFEST linha 7).
   Um ADR novo do PLAN-164 (que naturalmente tomaria o número 183) colide
   em número com bytes double-APPROVEd E quebra os dois oráculos do
   script. A resposta arquiteturalmente correta é amend-in-place.
2. **A re-âncora (OQ3) cria dual-source divergente.** `resolve_anchor()`
   (`land-plan163-pin.sh:96-104`) prefere o ANCHOR_FILE mas tem fallback
   `git log --grep '[SENT-PLAN163-PIN]' -n 1`. Após a re-âncora, arquivo
   e fallback apontam para commits DIFERENTES — se o arquivo sumir, o
   gate silenciosamente volta para `a4371c7`, contra a qual `failopen==0`
   é insatisfazível para sempre. O check do W2 ("imprime a âncora nova")
   testa só o caminho feliz.
3. **Os dois números do contrato de timeout ficam como literais soltos em
   arquivos distintos, com a relação entre eles mantida por disciplina de
   cerimônia.** Single-sourcing em runtime é inviável (o harness lê
   settings.json; o hook lê env/literal — consumidores genuinamente
   distintos), mas o INVARIANTE (`registration ≥ interno + overhead +
   margem`) é mecanicamente testável e o plano não pede esse teste.
4. **A calibração 36,3→100 é aposta com N=1 sobre processo de cauda
   pesada e latência exógena (xhigh configurado fora do repo).** Aceitável
   como aposta declarada, inaceitável como número sem gatilho de
   recalibração e sem alternativas arquiteturais nomeadas-como-rejeitadas
   no ADR.

Verifiquei no código o comportamento das duas camadas: timeout interno →
`CodexTimeout` (`check_pair_rail.py:1041-1042`) → case F classificado com
`codex_verdict=TIMEOUT` (confirmado pelo evento do probe). Hook-kill pelo
harness → processo morto sem emitir nada → `expected` sem `case` →
**deficit** (contado em `land-plan163-pin.sh:208`), que é gate-visível mas
em operação normal é o pior estado observável: fail-open sem classificação
nenhuma. A folga contra esse estado ENCOLHE com a proposta: hoje
60−30 = 30 s de slack pré-overhead; proposto 120−100 = 20 s. É por isso
que o invariante-como-teste e a medição do overhead real são must-fix, não
nice-to-have.

**Posições explícitas nas OQs:**

- **OQ1: 100 s.** 2,75× o único ponto medido é margem de engenharia
  defensável dado fail-open + clamp 600 mantidos; 48/60 repetem a classe
  de aposta que produziu o 30. Condição: o ADR-amend registra N=1 e um
  gatilho de recalibração (ver Nice-to-have).
- **OQ2: 120 s**, condicionado a medir o overhead não-invoke do hook antes
  da cerimônia. Se o ceiling medido passar de ~15 s, sobe-se a
  registration (130/140) — nunca se raspa o budget interno.
- **OQ3: draft (a)** — atualizar o ANCHOR_FILE no commit da própria
  cerimônia, declarado no Scope — COM o fix do fallback no mesmo commit
  (Must-fix 2). Rejeito re-rodar `land-plan163-pin.sh`: risco de
  commit-vazio sem handling e re-assinatura de um sentinel cujo escopo
  não corresponde ao delta real desta mudança.
- **OQ4: delta-confirm de 1 round**, condicionado a evidência mecânica
  que bounded o delta (Must-fix 6). O runbook JÁ codifica essa doutrina
  no abort `staged bytes drifted` ("se legítimo (review), recomputar
  MANIFEST + gêmeo + re-review") — 1 round escopado não é precedente
  novo, é a aplicação do caminho previsto.
- **ADR: AMEND do ADR-110** (pretool enforcement — o contrato operativo
  do rail in-hook; cross-ref ADR-106 se o timeout também constar lá), com
  bloco `AMEND-1` no arquivo existente. Precedente de casa: ADR-136-AMEND-1.
  Motivo decisivo: amend não muda contagem de arquivos nem consome número
  — é a única opção que não força delta-sync dos oráculos fail-closed do
  script do pack. (Verificado: o pack NÃO contém cópia staged de
  ADR-106/110, então o amend vivo não é revertido pelo apply do pack.)

## Risks

- **Calibração N=1 + latência exógena.** O reasoning effort do codex
  (xhigh) vive fora do repo; um bump de modelo ou de effort re-produz o
  incidente na mesma classe. 100 s mitiga, não cura — sem gatilho de
  recalibração, este plano é o PLAN-16X de 2027.
- **Classe deficit fica mais provável em termos relativos.** Slack na
  fronteira do hook-kill cai de 30 s para 20 s−overhead. Deficit é
  fail-open SEM classificação e sem `codex_verdict` — só o gate e o
  ceo-boot o enxergam, dias depois.
- **UX cumulativa e concorrência.** 100 s é por-edit; uma sessão de
  trabalho em hooks com 5 edits canônicos não-sentinelados pode pagar
  ~8 min de parede. Fan-out de subagentes editando paths canônicos em
  paralelo = invocações codex concorrentes = rate-limit → timeouts em
  cascata, agora com janelas 3× mais longas de sobreposição. (Efeito
  colateral desejável, registre-se: empurra o fluxo para staging, que é
  o comportamento que queremos; mas o ADR deve nomeá-lo.)
- **Precedente de tocar pack congelado.** Aceitável porque o runbook já
  prevê o caminho e o delta é minúsculo — mas só permanece aceitável se
  cada byte mudado for bounded por evidência mecânica (manifests
  rastreados antes/depois), não por narrativa de review.
- **Custo.** Reviews que agora COMPLETAM a xhigh custam tokens reais por
  edit canônico — o sucesso do fix converte fail-open barato em spend
  recorrente. Advisory (lane do finops), mas o ADR deve mencionar.

## Must-fix

1. **Resolver a OQ do ADR como AMEND (não ADR novo)** e registrar no
   plano o PORQUÊ: interlock com `land-plan163-pack.sh:242/:477`
   (contagem 181→183 fail-closed) + número 183 já consumido pelo pack
   congelado. Se o debate ainda preferir ADR novo, o plano precisa
   incluir explicitamente: numeração ≥184, delta-sync dos DOIS oráculos
   do script + do expect dict (`:369`) + das instruções de closeout — um
   custo desproporcional ao benefício.
2. **Fechar a divergência do `resolve_anchor()`** no mesmo commit da
   cerimônia: fallback passa a aceitar o sentinel-tag mais NOVO entre
   `[SENT-PLAN163-PIN]` e `[SENT-PLAN164-RAIL]`, ou ANCHOR_FILE ausente
   vira fail-loud (`die`) em vez de fallback silencioso para a âncora
   morta. O script vive em `PLAN-163/` (não-canônico) — edit barato.
3. **Invariante entre camadas como teste, não como disciplina.** Teste
   novo que parseia a registration do `check_pair_rail.py` em
   `settings.json` E `settings.base.json` e o default literal do hook, e
   asserta `registration ≥ interno + overhead_ceiling + margem_mínima`.
   Mata a classe "dois números mágicos driftando" para sempre — inclusive
   para o próximo uplift.
4. **Medir o overhead não-invoke antes de fixar 120.** O plano estima
   "~10-15 s" sem medição — o mesmo pecado metodológico que o diagnóstico
   corrigiu para a latência do codex. A instrumentação já existe (delta
   ts `expected`→`case` menos wall-clock do invoke; ou cronometrar o hook
   com invoke mockado no boundary). O número medido entra no ADR-amend
   como base da derivação 100→120.
5. **Ampliar o sweep de literais para além de `hooks/tests/`.** Grep no
   repo INTEIRO (scripts/ de install/upgrade, templates/, docs
   não-vigiados — lição S275) E no `staged/main-pack/` inteiro — o pack
   contém `test_upgrade_settings_migration.py` (MANIFEST linha 33); se as
   fixtures de migração de adopter pinarem `timeout: 60`, a máquina de
   upgrade re-introduz o valor velho na frota (exatamente a classe
   "adopter-upgrade re-abre flip silencioso" da S284).
6. **Sequenciar o gêmeo do pack ANTES do sync.** `inputs-pack.sha256`
   NÃO existe ainda (verificado em disco). Commitar primeiro o gêmeo do
   estado congelado ATUAL (os bytes do double-APPROVE R6), DEPOIS aplicar
   o delta + recomputar + segundo commit. O diff entre as duas versões
   rastreadas do gêmeo é a evidência mecânica que bounded o delta-review
   da OQ4 (deve mostrar exatamente as 2 entradas de settings mudadas —
   qualquer linha a mais é abort). Sem o "antes" rastreado, o
   delta-review não tem base de comparação tamper-evidente e o W1 item 5
   ("recomputar") está descrevendo uma operação de CRIAÇÃO.

## Nice-to-have

- **Gatilho de recalibração documentado no ADR-amend:** após ≥10 cases
  healthy, computar p95 de (`pair_rail_case.ts` −
  `pair_rail_review_expected.ts`) do audit-log e revisitar 100/120. Os
  dados já existem; documentar a query evita minerar isso de novo em 2027.
- **Breadcrumb de UX no início do invoke** (stderr: "pair-rail review in
  flight, budget Ns") — melhor esforço, não confiável em todo harness,
  mas barato e reduz a percepção de sessão travada.
- **`_comment` das registrations apontando para o teste do invariante**
  (Must-fix 3), para o próximo editor saber que o número não é livre.
- **Nomear no ADR-amend as alternativas arquiteturais rejeitadas**, por
  honestidade do registro (template da skill exige Options Considered):
  (a) review assíncrono pós-facto — rejeitado porque o valor do rail é o
  veto PRÉ-write nos REJECTs case-B/C (async detecta, não previne; a lane
  async já existe: `stop_review`); (b) downgrade de reasoning-effort por
  invocação no `build_verdict_argv` (poderia caber honestamente sob os
  60 s atuais SEM tocar kernel) — rejeitado porque qualidade de verdito a
  effort menor é não-validada e o effort é deliberadamente config externa.
  Hoje o plano só compara variantes do MESMO desenho (48 vs 100 vs
  env-knob); um ADR de contrato precisa mostrar que o espaço de desenho
  foi olhado.

## Unseen

Coisas que o plano não menciona, em ordem de gravidade:

1. **O interlock de contagem/numeração de ADR com o pack congelado**
   (Must-fix 1). É o achado que muda uma OQ de "gosto" para "restrição
   dura" — e ninguém o declarou.
2. **A divergência file-vs-fallback do `resolve_anchor()`** (Must-fix 2).
3. **A superfície de upgrade/migração de adopters** como portador
   potencial do literal velho (Must-fix 5) — o plano trata paridade
   dogfood↔template mas não a máquina que ESCREVE registrations em repos
   de adopters.
4. **A inexistência atual do gêmeo `inputs-pack.sha256`** e a consequência
   para a evidência do delta-review (Must-fix 6).
5. **Semântica do gate pós-re-âncora:** o GATE-V2 passa a provar
   "liveness sob pin + timeout novo", não mais "sob o pin" isolado. É
   estritamente mais forte (o pin não é tocado pelo PLAN-164) e portanto
   honesto — mas o registro do PASS no PLAN-163 deve dizer isso
   explicitamente, senão o leitor futuro acha que a prova original do pin
   nunca existiu.
6. **Telemetria de duração para calibração futura** — resolvível por
   query documentada, sem tocar o hook (Nice-to-have 1).

## What I would NOT change

- **A cerimônia única.** Um sentinel, um Scope, re-âncora dentro dele —
  menor número de cerimônias, trilha de auditoria contígua. Não quebrar
  em duas.
- **O contrato fail-open-em-timeout do rail** (ADR-106/110) e a exceção
  fail-closed do pin ADR-182. Ambos corretos; este plano não deve
  reabri-los — e o plano acerta ao declará-los fora de escopo.
- **O clamp `>600` e a arquitetura de duas camadas em si.** A registration
  do harness como backstop do budget interno é defense-in-depth correto —
  o problema nunca foi ter dois números, é não ter o invariante testado.
- **O padrão de prova W3** (sessão nova + probe bytes-idênticos S281 +
  `--gate-v2` sobre o conjunto pós-âncora). Zero-risco, mecânico,
  re-rodável.
- **A decisão de NÃO usar env-knob (opção B)** — default de frota quebrado
  é bug de frota; o Owner acertou e não há o que re-litigar.
- **A nota honesta sobre o row 168h do ceo-boot** seguir RED até ~08-05 —
  manter, é exatamente o tipo de honestidade operacional que diferencia
  este repo.
