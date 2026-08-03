---
round: 1
archetype: Staff Code Reviewer
skill: code-review-checklist
agent_persona: Staff Code Reviewer (core archetype)
generated_at: 2026-08-03T19:40:00Z
---

## Verdict

ADJUST — a direção (escalada upward) está certa e é mandatória pelos critérios do próprio §3, mas a superfície de mudança declarada está INCOMPLETA (falta um gate duro de CI + 3 sites de literal) e um claim explícito sobre teste é FALSO.

## Summary (≤ 3 bullets)

- **O que a proposta tenta fazer:** recalibrar o par de timeouts do pair-rail 120/150 → 180/210 via nova emenda, acionada pelo gatilho de ≥10 casos saudáveis do ADR-110-AMEND-1 §3.
- **Onde é forte:** a regra de decisão do §3 é aplicada honestamente; o argumento de censura à direita é o argumento certo e sobrevive à re-medição; a rejeição da alternativa (b) (env-knob como mecanismo de calibração) está correta e bem fundamentada no §4(i) do AMEND-1.
- **Onde é fraca:** a superfície de mudança listada (3 literais + 2 espelhos + statusMessage) não é a superfície real (são 4 literais + 2 espelhos + 2 `_comment` + 1 doc DERIVADO sob gate duro de CI + 2 constantes de teste); o claim "o teste passa sem edição" é verificavelmente falso; e os números da medição não reproduzem.

## Risks

**R-CR1 — CRITICAL — o claim "`test_pair_rail_timeout_invariant.py` passa sem edição" é FALSO.**
O teste NÃO verifica só a desigualdade. Ele pina os valores absolutos:
`_RATIFIED_INTERNAL_S = 120` (`.claude/hooks/tests/test_pair_rail_timeout_invariant.py:103`) e `_RATIFIED_REGISTRATION_S = 150` (`:104`), consumidos por `test_ratified_absolute_values` (`:236`). A 180/210 esse método falha em três pontos: o default interno (`:237`), os dois fallbacks — a asserção compara a lista inteira contra `["120","120"]` (`:245-256`) — e os dois timeouts de registro (`:261`). O docstring do próprio teste (`:26-28`) já antecipa isto: *"A deliberate recalibration ... must edit THIS test in the same change — that is the contract, not an inconvenience."*
*Mitigação:* a emenda deve listar o teste e as duas constantes como parte da superfície, e o escopo do sentinel da cerimônia deve incluir o arquivo. Sem isso, ou o land vai vermelho, ou `touched − scope ≠ ∅` barra o commit.

**R-CR2 — CRITICAL — `docs/COMMAND-SKILL-HOOK-MAP.md` é doc DERIVADO atrás de gate duro de CI.**
A linha 98 é `| PreToolUse | Edit\|Write\|MultiEdit | check_pair_rail.py | 150 |`. O doc é gerado por `.claude/scripts/gen-command-skill-hook-map.py` a partir de `.claude/settings.json`, e `.github/workflows/validate.yml:291` roda `--check`, que sai 1 em drift. Mudar o registro para 210 sem regenerar = **validate.yml VERMELHO no commit da cerimônia**. É exatamente a classe S275 (número dentro de tabela markdown em superfície derivada — grep por contexto não acha).
*Mitigação:* incluir `python3 .claude/scripts/gen-command-skill-hook-map.py --write` na receita da cerimônia e o doc no escopo do sentinel.

**R-CR3 — MAJOR — os campos `_comment` dos DOIS settings carregam os literais e não estão listados.**
Kernel `.claude/settings.json:279` e template `templates/settings/settings.base.json:92` terminam ambos com: `CEO_PAIR_RAIL_TIMEOUT_S (default 120s; registration cap 150s — invariant guarded by test_pair_rail_timeout_invariant.py)`. A proposta lista só `timeout` e `statusMessage`. Nota de localização: o `_comment` fica no nível do GRUPO (entrada do matcher), não dentro do dict do hook — quem varrer só os dicts de hook não o vê.
*Mitigação:* listar os dois `_comment`. Um knob documentado que mente sobre o próprio default é a classe de dívida que o AMEND-1 nasceu para fechar.

**R-CR4 — MAJOR — a medição não reproduz; o número já está velho.**
Re-rodei a query normativa do §3 sobre a mesma união (verificar o claim, não o report). Verificado agora:

| | proposta | re-medido (2026-08-03T19:40Z) |
|---|---|---|
| n saudável | 14 (A:10, B:4) | **20** (A:14, B:6) |
| p95 | 121.2s | **119.8s** |
| máx | 120.0s | 120.0s |
| case-F | 3 | **7** |

Não é erro do proponente: a fatia anterior a 2026-08-03 é EXATAMENTE os 14 samples da proposta (33…120, mediana 65.5). Esta sessão de debate (`d2c626bc`) gerou mais 6 saudáveis + 4 F's **enquanto o debate rodava**. Consequência dura: o claim retórico de cabeçalho — "p95 EMPATA/EXCEDE o budget" — **inverte de sinal** na re-medição (119.8 < 120).
*Mitigação:* a conclusão sobrevive (119.8 é 99.8% do budget: "approaches" sem ambiguidade), mas a emenda NÃO pode carregar `n=14 / p95=121.2` como texto ratificado. Congele a medição com timestamp + conjunto de arquivos lidos, ou (melhor) cite a saída do script versionado da AQ2.

**R-CR5 — MEDIUM — AQ3 não tem evidência no repo e a sonda está bloqueada por ordenação.**
O maior timeout registrado hoje no kernel é 150 (o próprio pair-rail); o seguinte é 130 (Stop). 210 é território não atestado, e não há nada no repo documentando teto do harness. Pior: **não dá para sondar internal=180 só por env**, porque o registro a 150 mataria o hook antes — a sonda exige justamente o aumento que está sendo ratificado.
*Mitigação:* sonda independente ANTES da cerimônia — registrar um hook descartável com `timeout: 210` rodando `sleep 200` num settings de rascunho e confirmar que não é morto. Se houver teto não documentado abaixo de 210, 180/210 é inembarcável e 150/180 vira a única opção — o que reordena a decisão inteira.

## Must-fix (blocking)

1. **Corrigir o claim do teste e listar `test_pair_rail_timeout_invariant.py` na superfície** (R-CR1), nomeando `_RATIFIED_INTERNAL_S` (`:103`) e `_RATIFIED_REGISTRATION_S` (`:104`) como parte da mudança. Precisão para o escopo: falha **um** método (`test_ratified_absolute_values`), em **três** sites de asserção. Os outros três métodos passam a 180/210 — inclusive o de margem, que passa na igualdade exata (210 ≥ 180+30).
2. **Adicionar `docs/COMMAND-SKILL-HOOK-MAP.md` à superfície + o passo de regeneração à receita da cerimônia** (R-CR2). Este é o item que reprova o CI se escapar.
3. **Adicionar os dois `_comment`** (kernel `:279`, template `:92`) à lista de mudanças de texto (R-CR3).
4. **Trocar `n=14 / p95=121.2` por números re-medidos no momento de escrever a emenda**, com timestamp de execução e a lista de arquivos lidos (R-CR4). Se o texto da emenda afirmar "p95 excede o budget", ele afirma algo que a query não devolve mais.

## Nice-to-have (advisory)

1. **O 4º literal: o docstring.** `.claude/hooks/check_pair_rail.py:51` diz `CEO_PAIR_RAIL_TIMEOUT_S (default 120)`. O AMEND-1 §1.1 listou explicitamente ("plus the docstring at ~L51-52"); a AMEND-2 diz "os mesmos 3 literais" e o perde. Nenhuma asserção o cobre — logo ele deriva em silêncio. MINOR, mas é regressão de completude em relação à emenda que ela mesma cita como precedente.
2. **statusMessage:** a proposta já prevê "~3 min", correto. Registre que o teste só assere presença + não-vazio (`:214-232`), então **nenhum gate pega uma string velha** — é disciplina humana, não mecânica.
3. **`CHANGELOG.md:28` e `:43`** citam "30 → 120" e "may take 1-2 min". São registro histórico do v1.2.0 GA: **não editar**. Entrada nova em Unreleased.
4. **Medir o overhead δ** (ver Unseen 3): é o número em que a margem de 30s realmente se apoia e ninguém mediu.

## Unseen by the original plan

1. **O dataset é co-gerado pela cerimônia que o consome.** Os 6 samples de hoje vieram desta própria sessão de debate — e enviesam para cima: mediana **98.5s** sob carga de 7 agentes paralelos vs **65.5s** no lote ocioso de 07-31. A cauda que o budget precisa cobrir é a cauda SOB CARGA, e a cerimônia é a carga. Isso **reforça** 180 (argumento mais forte que o da própria proposta) e também mostra que a alternativa (c) "esperar mais amostras" não é só inútil: é auto-perturbadora. A emenda deveria nomear isso como risco de método permanente — toda recalibração futura lê um dataset que a sessão da recalibração está escrevendo.
2. **Resolução de 1 segundo nos timestamps.** Todas as latências são inteiras (33.000, 41.000, …). Logo "máx observado 120.0 = o budget!" vale ±1s, e um caso saudável **não pode** ter consumido os 120s de subprocess (teria levantado `CodexTimeout` → case F). O "cravado no teto" é artefato de arredondamento, e "p95 interpolado 121.2" interpola sobre grade de 1s. Não construa a retórica da emenda sobre precisão sub-segundo que o log não expressa — o argumento de censura (7 F's) é o que sustenta o peso, e sustenta sozinho.
3. **A grandeza medida NÃO é a grandeza que `timeout_s` limita.** `_emit_pair_rail_review_expected` dispara em `check_pair_rail.py:1469`, ANTES de `_invoke_codex_review` (`:1477`); a verificação sha256 do payload acontece DENTRO do helper (`:883`), antes do `subprocess.run(..., timeout=timeout_s)` (`:1033`). Então o delta de auditoria abrange sha-verify + subprocess + validação do verdict + emit do case, enquanto `timeout_s` limita **só o subprocess**. Definir interno = 1.5 × (grandeza estritamente maior que a limitada) é conservador — ok — mas a emenda deve dizer isso, porque a margem de 30s entre camadas é dimensionada contra o MESMO overhead que já está dentro da medição. Se o overhead é δ, o p95 real do subprocess é ~119.8−δ e o registro precisa cobrir 180+δ; com 210, isso orça δ ≤ 30s. Ninguém mediu δ.
4. **Verificado e limpo (registre para o próximo revisor não re-derivar):** há exatamente UM `subprocess.run` (`:1033`) e UMA chamada a `_invoke_codex_review` (`:1477`) — sem retry-loop. Chequei porque um retry faria o pior caso 2×timeout > registro e quebraria o PROPÓSITO do invariante (o hook, não o harness, é dono do braço de timeout). Também confirmado: o hook **não** passa por `_lib/codex.py`, então o cap de classe de 240s citado em `docs/CROSS-LLM-THREAT-MODEL.md:282` não engole o aumento.
5. **Armadilha latente de ordenação na query da união (munição para a AQ2).** Neste diretório, `sorted(glob("audit-log-2026-0*.jsonl"))` devolve `2026-08-1` ANTES de `2026-08` (porque `'-'` < `'.'`), enquanto o mtime diz o contrário — ordem cronologicamente invertida, e um `expected` no arquivo mais velho com o `case` no mais novo não pareia. **Testei: hoje não morde** (n=20 idêntico nas duas ordens, zero `case` órfão). É risco LATENTE, não defeito observado — reporto assim de propósito. Morde exatamente quando um review atravessa a fronteira de rotação, que é o cenário que a AQ2 quer matar.

## What I would NOT change

- **A direção (upward, não downward).** Confirmada contra dados re-medidos, não contra o report.
- **A rejeição da alternativa (b)** (env-knob institucionalizado como calibração). Correta e coerente com o §4(i) do AMEND-1.
- **180 sobre 150.** Mantenho 180 (condicionado à sonda R-CR5). Com p95 re-medido em 119.8, mediana de 98.5 no lote sob carga e censura à direita com 7 F's, 150 daria só 30s sobre o máximo observado de uma distribuição cujos samples carregados estão subindo. A assimetria de custo também não é simétrica e a proposta não a explicita: um F é fail-open silencioso (perda de governança), uma conclusão lenta é custo de UX. Sob essa assimetria, errar para cima é o lado certo.
- **A margem de 30s ABSOLUTA (não proporcional).** O overhead que ela cobre é custo fixo (startup do Python, sha do payload, redação, validação), não proporcional ao budget. Absoluta é a forma certa — não "melhore" para percentual.
- **O clamp `>600` intocado** e o wart de clamp-reset (AMEND-1 §4-ii) fora do pacote. 180 e 210 cabem folgados dentro de 600; empacotar o wart aqui amplia o raio da cerimônia sem necessidade.
- **`statusMessage` como mitigação**, em vez de migrar para lane assíncrona (AMEND-1 §5-a). O valor do rail é o veto PRÉ-escrita.

## Respostas diretas às AQ

- **AQ1 (180/210 vs 150/180):** 180/210, condicionado à sonda da R-CR5. Dois critérios não pesados: (i) a mistura de lotes — o número ratificado sai de um conjunto que mistura máquina ociosa (mediana 65.5) com máquina sob carga (mediana 98.5), e a carga é o regime em que edits canônicos de fato acontecem, o que faz de 180 o piso e não a opção generosa; (ii) a assimetria de custo F-vs-lentidão descrita acima.
- **AQ2 (texto vs script versionado):** **script**, por três razões concretas — (i) a query do §3 lê UM `LOG` e devolve n=0 pós-rotação, reproduzido ao vivo; (ii) a ordenação ingênua do glob é cronologicamente errada NESTE diretório (Unseen 5) — latente hoje, mas é precisamente a classe que a AQ2 quer matar, e um script é onde o `key=os.path.getmtime` fica registrado; (iii) só um script torna o "medido em T" re-executável e auditável. O script deve emitir n, p95, máx, contagem de F, **o timestamp da execução e a lista de arquivos lidos** — sem isso ele reproduz o mesmo problema em forma nova.
- **AQ3 (teto do harness):** sonda obrigatória antes da cerimônia; ver R-CR5 para o desenho e para o motivo de a sonda não poder ser feita por env.
