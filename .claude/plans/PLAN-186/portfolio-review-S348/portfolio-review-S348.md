---
review: S348
generated_at: 2026-09-06T21:35-03:00
critics: [Critic-A, Critic-B, Critic-C]
synthesizer: vp-engineering
scope: revisão de portfólio dos planos abertos + escopo da madrugada 06→07/09
---

# Revisão de portfólio S348 — o que fecha, o que espera, e como parar o laço

> **Glossário** (uma linha cada, porque você pediu em 04/09: nada de sigla sem explicação).
> **Pack** = pacote de trabalho de um agente, com estado e provas, guardado FORA do repo.
> **Rail / rodada de rail** = revisão adversarial feita por um segundo modelo (o codex) sobre um texto ou um diff.
> **Refutação** = um agente tentando derrubar o trabalho de outro; cada uma custa uma volta inteira.
> **Canônico** = arquivo que só muda com a sua assinatura GPG. **Livre** = arquivo que o CEO commita sozinho.
> **Bloco SIGN** = o ponto em que o pacote está pronto para você assinar, sem achado aberto.
> **Wave (onda)** = uma fatia de um plano que termina numa entrega. **AC** = critério de aceitação (a caixinha).
> **W0, W1, W4b…** = nomes de ondas dentro de um plano. **Ledger** = o registro escrito das suas 19 decisões.

---

## 1. Resposta curta ao Owner (5 linhas)

1. **Sim, estamos em laço — e ele está medido:** 372 rodadas de rail em 40 packs (`<SP>/rail-rounds-census.txt`, soma da coluna), e a última noite fechou **zero** pacotes canônicos.
2. **A causa não é rigor demais, é rigor no alvo errado:** de 504 achados de rail, só **11 % falam do código que vai ser assinado** — 25 % docs, 22 % cerimônia, 12 % instrumentos (`memory/feedback-rail-findings-class-fractions-s345.md`).
3. **A qualidade do produto está boa e tem prova:** dos últimos 40 runs no `main`, **34 sucesso, 6 cancelados por push seguinte, ZERO falha** (`gh run list -L 40 --branch main`, janela 04/09 20:14Z → 07/09 00:00Z).
4. **Quatro pacotes concentram 146 rodadas (39 %) e produziram UM land:** `ac13` 52, `w1-widen` 40, `w5-doctrine` 28, `contamination-gate-v4` 26 — e esse último só saiu quando trocamos a arquitetura da cura, nunca por insistência.
5. **O que muda:** codex só em bytes canônicos (sua decisão 4.1), teto de rodadas por classe LIDO do disco pelo lançador, rescisão de pack acima de 20 rodadas, e a madrugada dedicada a **FECHAR** (planos e ondas livres), não a avançar canônico — porque com você dormindo **nenhuma assinatura é possível**.

---

## 2. TABELA — um plano por linha

Concordância = quantos dos 3 críticos deram esse veredito. Toda evidência foi re-lida no disco por mim.

| plano | veredito | concord. | por quê (uma linha) | evidência |
|---|---|---|---|---|
| **PLAN-169** fechamento + GA | **re-escopar** | 3/3 | O que compra é a GA v1.4.0 (AC-8 aberto); o «quota-resume» é EXPERIMENTAL e declaradamente inerte para adotantes — vira follow-up próprio | `PLAN-169:1417` AC-8 `[ ]`; :1373/:1380 AC-4/AC-5 abertos; ledger 4.3 |
| **PLAN-170** bateria E7 | **adiar** | 3/3 | Congelado por construção: abre quando a tag `v1.4.0-rc.1` existir — `git tag --list 'v1.4.0*'` retorna **0 linhas** hoje | `PLAN-170:11` (`external_wait` com o comando); comando rodado 06/09 |
| **PLAN-171** proveniência | **re-escopar** | 3/3 | Só a W0 (censo dos gates) entrega: 4 de 6 lotes landados. W3 duplica um flip já agendado; W5 servia ao E5 do 172, congelado | `PLAN-171:79` (W3), `:96` («pré-requisito E5»); `plan-progress.txt:28` |
| **PLAN-172** velocidade honesta | **adiar** | 3/3 | Dupla dependência declarada no próprio plano (169 + 171 W5) | `PLAN-172:13` `external_wait` |
| **PLAN-173** cockpit Warp | **adiar** | 3/3 | Depende dos resultados do 172, que não rodou — dependência de segunda ordem | `PLAN-173` frontmatter (gated no 172) |
| **PLAN-174** geração de cerimônia | **fechar** (superseded pelo 188) | 2/3 | Mesmo defeito, dois donos — e o PLAN-188 **exige por escrito** uma decisão registrada sobre a W3 do 174 antes de aposentar o gerador | `PLAN-188:213-219` citando `PLAN-174:98`; `PLAN-174` `external_wait` (waiver S316 cobria só W1-W2) |
| **PLAN-175** poda de skills | **manter** (executar a revisão) | 2/3 | Você já autorizou a revisão; a regra como está arquivaria este próprio repo | ledger 4.15 |
| **PLAN-176** currency de modelos | **manter** (executar a revisão) | 2/3 | Você já autorizou a revisão; é o caminho de DETECÇÃO de modelo novo (adoção nunca é automática) | ledger 4.14 e Bloco 3b |
| **PLAN-181** adoção do /loop | **adiar** | 3/3 | O piloto só existe DURANTE um hold RC→GA ativo, que não há | `PLAN-181:18` `external_wait` |
| **PLAN-183** aptidão do adotante | **manter** | 3/3 | Última lacuna de campo aberta desde a S315: o ponteiro sai com caminho de casa. AC-1 é o único P0 restante | `PLAN-183:1366` AC-1 `[ ]` [P0]; AC-2 `[x]` |
| **PLAN-184** custo de CI | **fechar** | 3/3 | Fecha por medição: teto US$ 2,195/dia < N = US$ 3/dia ⇒ o pré-registro foi cumprido e a W1 não abre | ledger 4.6 — **forma legal do fecho é pergunta sua, D1 §6** |
| **PLAN-186** modelo de operação | **manter** (com WIP ≤ 3) | 2/3 | Governa todos os outros e concentra as assinaturas abertas; já entregou a W4a (Validate 20m31s→8m07s) | 14 ACs `[ ]` contra 5 `[x]` (`plan-progress.txt:48`); ledger 4.17 |
| **PLAN-186-FU census-runtime** | **manter** | 3/3 | É a cura registrada da lição-mor: responder «qual modelo é servido» EXECUTANDO, não lendo texto | `memory/feedback-instrument-that-predicts-code-by-text-never-converges.md` |
| **PLAN-186-FU walk-from-root** | **adiar** | 3/3 | Plano já landado, nenhuma onda aberta, nenhum comprador hoje | `plan-progress.txt:46` (0/0) |
| **PLAN-186-FU sentinel-gpg** | **manter** | 3/3 | Furo real: um `.asc` digitado à mão isentava documento vizinho; o AC-0 deixa de ser provisório por decisão sua | ledger 4.2; `plan-progress.txt:47` (1/8) |
| **PLAN-187** teto de paralelismo | **fechar** | 3/3 | A pergunta já foi respondida e o AC-4 é inobservável por construção (RSS por agente não é observável; custo por worktree não é derivável) | `PLAN-187` progress log 05/09; AC-5 = só o relatório |
| **PLAN-188** cerimônia compartilhada | **manter** (congelar o texto) | 2/3 | Ataca a classe que é 22 % dos achados e 28 % dos P0/P1 — mas já gastou 22 rodadas no TEXTO do plano | censo: `p188-plan-draft` 10 + `-r2` 8 + `-r3` 4; frações S345 |
| **PLAN-189** A/B construtor externo | **re-escopar** | 2/3 | Mede quem CONSTRÓI mais rápido, enquanto o gargalo medido é a REFUTAÇÃO; landar o pré-registro, não abrir o experimento | censo: `p189-plan-draft` 18 + `pilot-specs` 11 + `runner` 6 = 35 rodadas, 0 land |

**Aritmética do corte:** fechando 184, 187 e 174, e marcando o congelamento de 170/172/173/181 + FU-walk, o portfólio ativo cai de **18 para 5 planos vivos** (169, 171, 183, 186, 188) mais 2 em revisão de docs (175, 176).

---

## 3. ESCOPO DA MADRUGADA (06→07/09) — ordenado

**A restrição que decide tudo:** você dorme ⇒ **zero assinatura GPG** ⇒ **zero fechamento canônico possível**.
A noite vale por fechamentos LIVRES. Um lander por vez. Os 3 críticos convergiram nos itens 1–5.

| # | item | «pronto» é | regra de parada (pré-registrada) | ganho |
|---|---|---|---|---|
| 1 | **Ledger das 19 decisões + propagação** (já em voo com o agente `ledger-s347`) | Cada resposta copiada VERBATIM para o plano/OQ citado; ledger commitado em `.claude/plans/PLAN-186/debate/owner-decisions-S347.md` | **0 rodadas de rail** (é transcrição). Se um plano exigir julgamento NOVO, não decidir: vira OQ da manhã | 1 plano fechado (184) + AC-0 do sentinel-gpg ratificado + modelo v2 registrado |
| 2 | **`p171-w0-lote5` → `lote6`** (livres, um por vez) | Os 6 lotes do censo W0 na árvore ⇒ **W0 do PLAN-171 fechada** | lote5: **0 rodadas novas** (regra material-only). lote6: **1 rodada de mecanismo + 1 de confirmação, teto absoluto**; P1 em byte shipado na 2ª ⇒ `partial`, para | **1 onda fechada** |
| 3 | **PLAN-187 → fechado pelo AC-5** | `docs/research/parallelism-ceiling-S34x.md` só com números JÁ medidos, cada um com o comando; AC-1..AC-4 encerrados com a razão nomeada | **1 passe.** Número sem fonte no disco não entra. Achado que peça medição NOVA vira residual — não se mede | **1 plano fechado** |
| 4 | **Congelar 170/172/173/181 com gatilho executável** + propor `superseded` do 174 pelo 188 | Cada plano diz, em uma frase, o COMANDO que o reabre (o 170 já faz isso) | **0 rodadas.** Não inventar status: `deferred` não existe no esquema. Flip de status vai por pergunta sua na manhã | 4 planos fora da fila + 1 fechamento pronto |
| 5 | **`p188-plan-r3`** (livre) | O texto do PLAN-188 com as figuras medidas; depois **congelar o texto** | Teto já escrito no próprio pack: r5 mecanismo + r6 confirmação; P1 em byte shipado na r6 ⇒ STOP/`partial`/Owner. **Sem rodada 3 de debate** | Fecha o TEXTO do 188 |
| 6 | **`p189-plan-draft` → `p189-pilot-specs`** (livres, nessa ordem) | Os dois packs landados como **pré-registro congelado**, com a condição escrita: não abre enquanto nenhum canônico tiver assinado | Teto já pré-registrado no pack: r15 mecanismo + r16 confirmação; P1 na r16 ⇒ STOP/`partial`/Owner | 2 packs aposentados (35 rodadas encerradas) |
| 7 | **`p186fu-census-runtime-w0`** (livre) — se sobrar noite | Os 2 P1 da última refutação curados na fonte e o pack landado | **1 cura + 1 confirmação**, teto absoluto | Avança (não fecha) — por isso é o último |
| 8 | **Packs de docs: revisão do 176 e do 175** — só se os 7 acima fecharem | Um pack de docs cada, com os consensos do debate; flip para `executing` **só depois** (sua 4.10) | 1 passe cada, **sem rail pago** | 2 planos destravados |

**Canônicos: NENHUM esta noite** (é o padrão que estou adotando; ver D3 §6 se você quiser o contrário).
Motivo medido: os 6 canônicos abertos somam ~148 rodadas e **zero assinaturas**, e sua decisão 4.1 reserva o codex para sessões de assinatura. Sem você acordado, o melhor desfecho possível de um canônico é «pack esperando».
**Fila da manhã, na sua ordem 4.17:** W1 (`w1-widen`) → W6a (`w6-adapter`) → W4b (`w4b-ci-matrix`), WIP ≤ 3.

---

## 4. COMO TRABALHAR a partir de agora

Cada regra vem com o número que a sustenta — lido, não lembrado.

1. **R1 — Codex só toca bytes que vão para uma assinatura.** Plano, desenho, evidência, estado, material de cerimônia e instrumento **não** vão a modelo externo; o gate deles são as 2 lanes do próprio lander. *Fato: 11 % dos 504 achados eram sobre o código assinado; 59 % eram docs+cerimônia+instrumento.* (É a sua decisão 4.1 posta em prática.)
2. **R2 — Teto de rodadas por CLASSE, verificado pelo lançador antes de abrir a rodada N+1.** Prosa/docs: 1. Material de cerimônia: 1. Instrumento: 2. Bytes canônicos: 2 (mecanismo + confirmação). *Fato: 372 rodadas em 40 packs; o teto já existia como texto nas notas do CEO e foi furado — texto não é gate; condição de arquivo é.*
3. **R3 — Rescisão de pack acima de 20 rodadas.** O pack vira nota de residual e a classe só volta com ARQUITETURA diferente. *Fato: `ac13` 52, `w1-widen` 40, `w5-doctrine` 28, `contamination-gate-v4` 26 = 146 rodadas (39 % do total) e UM land — e esse só saiu com troca de arquitetura.*
4. **R4 — Proibido instrumento que prevê comportamento de código LENDO TEXTO.** Saídas legítimas, nesta ordem: fechar por construção (não fazer a ação), oráculo de runtime confinado ao próprio repo, ou estreitar a promessa pelo modelo de ameaça com lint advisory. *Fato: 3 packs morreram nessa classe na mesma noite (3 arquiteturas / 9 famílias / 5 contra-exemplos).*
5. **R5 — WIP ≤ 3 canônicos de dia (sua 4.17) e ≤ 1 à noite.** *Fato: a noite S347 rodou 6 canônicos e fechou zero, enquanto o braço livre fechou 14 lands com CI verde.*
6. **R6 — Um defeito, um dono.** Duplicata vira `superseded`, nunca «coordena com». *Fato: `PLAN-188:213-219` não pode aposentar o gerador de cerimônia porque `PLAN-174:98` agenda uma wave que o estende — o próprio plano pede a decisão.*
7. **R7 — Todo plano declara a condição de fecho como COMANDO.** *Fato: `PLAN-170:11` diz «abre quando `git tag --list v1.4.0-rc.1` deixar de ser vazio» e por isso ninguém precisa reavaliá-lo; o PLAN-186 não diz nada equivalente e por isso tem 14 caixinhas abertas.*
8. **R8 — Higiene de esquema antes de fechar qualquer plano.** Não existe status `deferred`; a espera vai no campo `external_wait`, não no `status`. *Fato: `PLAN-SCHEMA.md:422` lista os 7 status legais; `:394` diz que de `draft` só se vai para `reviewed` ou `abandoned`; `:425` exige a seção «Abandonment reason»; `:427` exige `superseded_by`.*

---

## 5. QUALIDADE — leitura honesta

**Está boa, e tem prova.** Dos últimos 40 runs no `main`: **34 sucesso, 6 cancelados, 0 falha** (janela 04/09 20:14Z → 07/09 00:00Z), cobrindo Validate (22 verdes), Smoke Install 2/2, Ownership Nightly 2/2, Coverage 2/2, Red-team 1/1, mcp-smoke 2/2. Os 14 lands da noite passada saíram verdes. Dos 3 defeitos de campo do adotante abertos desde a S315, **2 fecharam** e o terceiro é exatamente o AC-1 aberto do PLAN-183 — tem dono e é o último.

**O limite dessa prova, dito e não omitido:** CI verde diz que os testes que existem passaram. **Não medimos** nesta revisão o poder de asserção (kill rate de mutação nos módulos tocados) — declaro em vez de calar. E há **2 flakes conhecidos** já registrados por você em 4.11; enquanto estiverem na bateria, nenhum sign-off pode citá-los como prova.

**O que NÃO está bom é a vazão, e são coisas diferentes:** 372 rodadas de rail produziram, na última noite, zero pacotes canônicos assináveis. Isso não é excesso de cuidado — é cuidado gasto em bytes que nunca são assinados.

**Salvaguardas que FICAM (cada uma com a classe de defeito que pega):**
1. Assinatura GPG do Owner em pack canônico, com `refuted=false` real — pega «modelo edita governança sem dono humano». A regra material-only **nunca** vale para canônico.
2. Gates de corpus DEPOIS da última edição (`git add -A` → gates → commit) — pega «arquivo novo entra sem nenhum gate tê-lo visto» (violado 2× na S321).
3. Fail-closed no parse de INPUT dos matchers de segurança — pega «conteúdo que o guard não sabe ler passa batido».
4. `touched − scope = ∅` no land — pega «patch assinado carregando arquivo fora do escopo».
5. Controle positivo que reproduz o MECANISMO — pega guard falso-verde; foi o que expôs o vazamento do CODEOWNERS vivo para o adotante.
6. Conjunto RED exato do Ownership Nightly (62 verde / 3 vermelho) — pega mudança silenciosa na tabela de posse.
7. Isolamento da cadeia de auditoria nos testes — pega «a suíte escreve na cadeia viva» (eram 2.356 eventos, 79 % do segmento).
8. As 2 lanes de rail do próprio lander sobre o diff vivo — pega «pack livre que passou nas rodadas e piorou nos bytes finais». **Se cortar rodadas, esta é a que fica.**

**Rituais que saem:** rodada de rail sobre texto de plano/desenho/evidência (troca-se por GERAR o número em vez de digitá-lo); refutador em pack livre de docs (as 2 lanes do lander já são o gate); a 3ª cura da mesma classe (troca-se a arquitetura ou escala para você).

---

## 6. DECISÕES PARA O OWNER

**D1 — Como fechar o PLAN-184 (o esquema não permite o que o ledger escreveu).**
Seu ledger 4.6 diz «flip para done-residual». Mas `PLAN-SCHEMA.md:394` só permite `draft → reviewed` ou `draft → abandoned`; `draft → done` é transição ilegal e o gate de esquema recusa.
- (a) **`abandoned` + seção «Abandonment reason»** citando a medição (teto US$ 2,195/dia < N = US$ 3/dia). Um hop, legal, preserva sua intenção. **(Recomendado)**
- (b) `draft → reviewed → executing → done` (3 hops legais, mas afirma execução que não houve).
- (c) Manter em `draft` e só registrar o residual no corpo (não tira o plano da fila).

> **Nota do lander (S348, 2026-09-06):** esta pergunta já não estava em
> aberto quando esta revisão foi escrita nem quando o Owner respondeu —
> a opção (a) já tinha sido aplicada no commit `c05ecdc` (2026-09-06,
> sessão anterior): `PLAN-184-ci-cost-routing.md` está `status: abandoned`
> com `abandoned_at: 2026-09-06` e uma seção `## Abandonment reason`
> citando a mesma medição (teto US$ 2,195/dia < N = US$ 3/dia). D1 fica
> registrada aqui como histórico da pergunta, não como decisão pendente.

**D2 — Um dono para a cerimônia: PLAN-174 × PLAN-188.**
- (a) **PLAN-174 → `superseded_by: PLAN-188`, e o 188 assume a W3 num parágrafo** (é exatamente a decisão que `PLAN-188:213-219` exige para poder aposentar o gerador). **(Recomendado)**
- (b) Manter os dois e pagar a mesma classe duas vezes.
- (c) Fechar o 188 e manter o 174 (contra o consenso 2/3 e contra a evidência de custo da classe).

**D3 — Canônico na madrugada: os críticos divergiram 1/1/1.**
- (a) **Nenhum canônico esta noite**; a fila da manhã segue sua ordem 4.17 (W1 → W6a → W4b). **(Recomendado)** — fato: 6 canônicos abertos, ~148 rodadas, 0 assinaturas; e sua 4.1 reserva o codex para a sessão de assinatura.
- (b) **Um** canônico preparado até `PENDING-CODEX`, e ele seria o **W4b** — pela tabela de distância, W4b precisa de «refutação + 3 ratificações suas», e essas 3 já estão respondidas na sua 4.8; W1 ainda precisa de re-derivação no HEAD, 2 rails, 2 packs de materiais e harness.
- (c) Um canônico e ele é o **W1**, por ser o primeiro da sua ordem 4.17 — custa a noite e o desfecho provável é zero.

**D4 — Os packs do PLAN-189 (`p189-plan-draft`, `p189-pilot-specs`).**
- (a) **Landar os dois como pré-registro congelado**, com a condição escrita de que o experimento não abre enquanto nenhum canônico tiver assinado — é o que sua própria ordem de retomada já enfileira. **(Recomendado)**
- (b) Não landar e suspender no pack (posição de 1 dos 3 críticos): impede as 35 rodadas de continuarem, mas contraria a fila que você escreveu.
- (c) Landar e abrir o experimento (contra o consenso 2/3: mede construção quando o gargalo é refutação).

**D5 — Flip de status do PLAN-173 (estudo do cockpit) e do PLAN-175/176.**
- (a) **173 fica `reviewed` com gatilho escrito; 175 e 176 recebem a revisão de docs hoje e o flip para `executing` só depois** (sua 4.10). **(Recomendado)**
- (b) 173 vai a `abandoned` agora (é terminal e exige a seção de razão — não dá para desfazer com um clique).

**Achados de 1 crítico que eu NÃO descarto (ficam registrados):**
- O PLAN-171 aparece como `0/0` no painel de progresso porque não usa caixinhas — um plano ativo invisível ao instrumento de progresso. Cura de 1 linha: os ACs passam para a forma `- [ ]`.
- O AC-4 do PLAN-186 está marcado «REMOVIDO» mas com a caixinha `[ ]`, e por isso conta como aberto no painel.
- Dois críticos escreveram «5 runs cancelados»; a contagem que eu rodei diz **6**. Usei a minha.

---

## 7. Decisões do Owner (S348, 2026-09-06)

Respondidas via `AskUserQuestion` por volta de 21:55 (terminal
`ceo-orchestration-46`), registradas verbatim em
`owner-decisions-S348.md` (fora do repo, diretório de trabalho da
sessão). D1 (PLAN-184) já estava resolvida antes desta rodada de
perguntas — nota em §6 acima.

| # | pergunta (resumo) | resposta verbatim do Owner | efeito |
|---|---|---|---|
| Q1 | Ratifica as regras novas de trabalho (codex só em bytes canônicos; teto de rodadas por classe lido do disco; rescisão acima de 20 rodadas; um defeito um dono)? | «Ratificar as 4 regras (Recomendado)» | Modelo de operação v2.1 registrado em `PLAN-186-orchestrator-operating-model.md` (R1, R2, R3, R6/R7 do §4 acima); land de docs fecha SEM codex (gates de corpus + verificação do CEO + CI); canônico continua exigindo 2 rodadas de rail (mecanismo + confirmação) e assinatura GPG; orçamento de codex da madrugada 06→07/09 ≤ 3 rodadas no total. |
| Q2 (D3) | Um canônico até o bloco de assinatura esta noite? | «Sim, o w4b-ci-matrix, teto 2 rodadas (Recomendado)» | `w4b-ci-matrix` é o ÚNICO canônico da madrugada (cura S347-r8 + 1 rodada de mecanismo + 1 de confirmação); P1 na confirmação ⇒ `partial`; codex sem cota ⇒ `PENDING-CODEX`; W1 (`w1-widen`) e W6a (`w6-adapter`) esperam a manhã de 07/09. |
| Q3 (D2) | PLAN-174 e PLAN-188 atacam o mesmo defeito. Fundir? | «PLAN-174 vira superseded pelo PLAN-188 (Recomendado)» | `PLAN-174-ceremony-generation.md` recebe `status: superseded` + `superseded_by: PLAN-188`; o `PLAN-188-shared-ceremony-toolkit.md` assume a W3 do 174 pelo pack `p188-plan-r3` (ainda não landado — o PLAN-188 não foi editado por este pacote). |
| Q4 (D4) | Os dois packs do PLAN-189 estão prontos, com 35 rodadas gastas. O que fazer? | «Não landar; congelar nos packs, zero gasto (Recomendado)» | `p189-plan-draft`, `p189-pilot-specs` e `p189-runner` ficam congelados FORA do repo — nenhum path novo entra na árvore; nenhum plano novo entra enquanto houver canônicos sem assinatura; revisitar depois da primeira assinatura da madrugada/manhã. |

Decisão da mesma sessão, anterior a estas quatro (21:1x): «Revisão de portfólio dos 13 planos (Recomendado)» como primeiro passo antes de
relançar canônicos — é esta revisão.
