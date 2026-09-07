---
review: S348
archetype: llm-finops-architect
skill: llm-routing-and-finops
generated_at: 2026-09-06T21:35-03:00
---

# Revisão de portfólio S348 — lente de custo e vazão

> **Glossário mínimo (o Owner pediu isto em 04/09):** *pack* = pasta de trabalho
> de um item (`s344-packs/<chave>/`) com o estado, a evidência e os registros de
> revisão. *rodada de rail* = uma passada de revisor externo (codex) sobre um
> pacote; cada rodada custa fila + uma volta de construtor. *pack livre* = não
> toca arquivo protegido, o CEO pode landar sozinho. *pack canônico* = toca
> arquivo protegido, só entra na árvore com a **assinatura GPG do Owner**.
> *wave* = fatia de um plano. *AC* = critério de aceitação (a caixinha do plano).
> *land* = commitar na árvore viva. *material* = papelada do pack (desenho,
> evidência, estado) — não vai para a árvore.

## 0. Os três números que respondem à pergunta do Owner

| # | Fato MEDIDO | Fonte |
|---|---|---|
| 1 | **372 rodadas de rail** registradas em **40 packs** vivos | `rail-rounds-census.txt` (soma da coluna `rail_round_records`, 40 linhas) |
| 2 | **148 dessas 372 rodadas (40 %) estão em 6 packs canônicos que fecharam ZERO assinaturas** — ac13 52, w1-widen 40, w5-doctrine 28, p183-w1 18, w6-adapter 10, w4b 0 | mesmo censo + `MORNING-S347.md:47-55` («Pacotes canônicos: nenhum assinável hoje») e `MORNING-S347.md:70` («Nenhum canônico assinável. Os 6 abertos consumiram 40+ refutações») |
| 3 | **Só 11 % dos achados de rail falam do código que vai ser assinado**; 25 % docs, 22 % cerimônia, 12 % instrumentos (n=504 achados, 163 registros) | `memory/feedback-rail-findings-class-fractions-s345.md` |

**Derivado (aritmética minha, sobre os números acima — não medido):** o braço
livre gastou as outras 224 rodadas e produziu **14 lands** na noite S347
(`MORNING-S347.md:9-24`, tabela de 13 commits + a cura do lote 2) ⇒ **≈ 16
rodadas por item fechado no braço livre, e infinito no braço canônico**. Com a
fila do codex medida em p90 = 740 s por rodada (memória das frações de classe),
as 148 rodadas canônicas representam **≈ 30 h de relógio só de espera de fila**
(teto p90, não tempo real observado) — a noite inteira, para zero fechamento.

**Tradução da frase do Owner.** «Gastando muito de codex e em looping» não é
impressão: **89 % da saída do revisor externo não toca o byte que vai ser
assinado**, e o braço onde ele é obrigatório é exatamente o que não fecha. O
excesso de cuidado é REAL e tem endereço: rodadas de texto sobre prosa
(plano, desenho, evidência, cerimônia). O cuidado que PAGA — rail de mecanismo
sobre bytes shipados — é 11 % do gasto e deve continuar.

---

## 1. TABELA — um plano por linha

`% feito` = coluna `all boxes done/total` de `plan-progress.txt` (linhas 26-50).
`assinaturas` = quantas assinaturas GPG do Owner ainda faltam para o plano
fechar, contadas pelas waves canônicas abertas.

| plano | valor medido ou esperado | % feito | assin. | veredito | evidência |
|---|---|---|---|---|---|
| **PLAN-169** fechamento + evolução | Compra a **GA v1.4.0** (AC-8). O quota-resume (W4.1) é EXPERIMENTAL e declarado inerte para adotantes ⇒ não compra nada hoje | 55 % (5/9) | 1 (corte GA) | **re-escopar** | `PLAN-169:1394` (AC-8 aberto), `:1350`/`:1357` (AC-4/AC-5 = probes de quota), `OWNER-DECISIONS-S347.md` §4.3 |
| **PLAN-171** proveniência | W0 (censo dos gates) é o único pedaço com entrega medida: 4 de 6 lotes landados. W3 duplica o flip da janela advisory do PLAN-178; W5 (worktree) era pré-requisito do E5 do PLAN-172, que está congelado | — (0/0 caixas no arquivo) | 0 esta noite | **re-escopar** | `PLAN-171:79` (W3), `:96` (W5); censo: `p171-w0-lote5`/`lote6` prontos |
| **PLAN-183** adopter fitness | Fecha a **última lacuna de campo aberta desde a S315**: o ponteiro `PROTOCOL.md` absoluto (A1). Dois dos três defeitos de campo já fecharam | 65 % (21/32) | 1 (W1) | **manter** (com teto de rodadas) | `CLAUDE.md` §5 «o ponteiro `PROTOCOL.md` absoluto (A1) segue ABERTO — é a W1»; pack `p183-w1-pointer` = 18 rodadas, 0 assinatura |
| **PLAN-186** modelo operacional | O maior consumidor do portfólio: orçamento declarado **2,42M–3,59M tokens / US$ 2.200** e 26 % feito. Entregou medida real (W4a: Validate 20m31s→8m07s) | 26 % (5/19) | 6 abertas (W1, W6a, W6b, W4b, W5a, W5b) | **re-escopar** | `PLAN-186:19-21` (orçamento), `plan-progress.txt:48`; `CLAUDE.md` §5 (W4a medida em `0b5e6ed`) |
| **PLAN-184** custo de CI | **Já respondido pela medição**: teto medido US$ 2,195/dia < N = US$ 3/dia ⇒ o pré-registro manda FECHAR como residual | 8 % (4/48) | 0 | **fechar** (esta noite, docs) | `OWNER-DECISIONS-S347.md` §4.6; `PLAN-184:891` (US0 = o resultado que mata o plano) |
| **PLAN-187** teto de paralelismo | O estudo **já respondeu a própria pergunta**: o teto real é cota + refutação, não máquina/terminais. AC-5 (relatório) é o entregável que sobra | 0 % (0/5) | 0 | **fechar** com AC-5, abandonar AC-1..AC-4 | `PLAN-187:154` (AC-5); `MORNING-S347.md:70-73` (o muro foi cota e refutação) |
| **PLAN-188** cerimônia compartilhada | Ataca a classe que é **22 % dos achados de rail** (cerimônia). Alavancagem alta SE o pipeline canônico continuar. **Contra-fato:** já consumiu 22 rodadas (10+8+4) e 2 rodadas de debate **sobre o TEXTO do plano**, com zero byte de produto | 0 % (0/6) | 0 (ainda) | **re-escopar** para o menor entregável | censo `p188-plan-draft` 10, `p188-plan-r2` 8, `p188-plan-r3` 4; memória das frações |
| **PLAN-189** A/B construtor externo | **A hipótese foi refutada antes do experimento**: o gargalo medido é a REFUTAÇÃO (89 % dos achados fora dos bytes shipados), não a construção. Já gastou 35 rodadas (18+11+6) sem landar | não landado | 0 | **fechar** (o pedaço útil — o lock de land — migra p/ 188) | censo `p189-plan-draft` 18 + `p189-pilot-specs` 11 + `p189-runner` 6; `p189-plan-draft/STATE.md` (lander derrubou no passo 6) |
| **PLAN-186-FU** censo por runtime | É **exatamente a cura registrada** da lição-mor da S347 (instrumento que prevê código por TEXTO não converge). Barato: L2, 3 caixas | 0 % (0/3) | 0 | **manter** (1 cura + land livre) | `PLAN-186-FOLLOWUP-census-runtime.md:9` (L2); `memory/feedback-instrument-that-predicts-code-by-text-never-converges.md` |
| **PLAN-186-FU** sentinel GPG | Verifica **de verdade** a assinatura de um sentinel; o AC-0 deixou de ser provisório por decisão do Owner | 12 % (1/8) | 1 (L3, futuro) | **manter**, mas só o flip do AC-0 esta noite | `OWNER-DECISIONS-S347.md` §4.2; `plan-progress.txt:47` |
| **PLAN-186-FU** walk-from-root | Plano já revisado e landado (`3f8f4f0`); nenhuma wave aberta, nenhum comprador nomeado | 0 % (0/0) | 0 | **adiar** (fila atrás de W1/W6a/W4b) | `plan-progress.txt:46`; `MORNING-S347.md:15` (land #5) |
| **PLAN-170** bateria E7 | Bateria cara com orçamento próprio; nenhum consumidor hoje. O pré-registro (169 AC-6) já está feito, então nada se perde esperando | 0 % (0/35) | 0 | **adiar** (com gatilho escrito) | `plan-progress.txt:27`; `PLAN-169:1364` (AC-6 [x]) |
| **PLAN-172** velocidade honesta | Congelado; o E5 dependia da higiene de worktree (171 W5) que estou recomendando cortar. Sem comprador | — | 0 | **adiar** | `PLAN-172:4` (`reviewed`), `:210` («congelado») |
| **PLAN-173** cockpit Warp | Estudo puro; não fecha lacuna nem gate. Zero entrega esperada no trem atual | — | 0 | **adiar** (candidato a `abandoned` na manhã) | `PLAN-173:4`, `:89` |
| **PLAN-174** geração de cerimônia | **Sobreposição direta com o PLAN-188**: os dois geram/endurecem cerimônia. Manter os dois é pagar a mesma classe duas vezes | — | 0 | **fechar** como `superseded` pelo 188 (decisão do Owner na manhã) | `PLAN-174:3` (título), `:13` (waiver + deadline v1.4.0-rc.1); `PLAN-188:3` |
| **PLAN-175** poda de skills | O Owner autorizou só a REVISÃO (pack docs). Valor real: a regra como está arquivaria o próprio repo | — | 0 | **manter** (só a revisão docs) | `OWNER-DECISIONS-S347.md` §4.15; `MORNING-S347.md:64` |
| **PLAN-176** currency de modelos | Owner autorizou a revisão. Valor: DETECÇÃO de modelo novo; a adoção nunca é automática (fica cara e manual de qualquer jeito) | — | 0 | **manter** (só a revisão docs) | `OWNER-DECISIONS-S347.md` §4.14; `CLAUDE.md` §5 («adotar modelo novo NUNCA é automático») |
| **PLAN-181** adoção do /loop | Bloqueado por espera externa declarada; o W0 só existe durante um hold RC→GA ativo, que não está aberto | — | 1 (W3) | **adiar** | `PLAN-181:18` (`external_wait`) |

**Refutação explícita do brief do CEO** (`project-portfolio-review-brief-s348.md`):
concordo com 187 (fechar), 171 (cortar W4/W5), 183 (manter), 169 (tirar o
quota-resume do caminho da GA). **Discordo em três pontos:**
1. O CEO propõe «encolher ou adiar» o PLAN-189. A medição da própria noite
   **refuta a pergunta do experimento**, não só o tamanho dele: nenhum encolhimento
   conserta um A/B sobre construção quando o gargalo medido é revisão. **Fechar.**
2. O CEO não olha o PLAN-174. Ele e o 188 compram a mesma coisa. **Um dos dois.**
3. O CEO trata o PLAN-188 como «manter, rodada 3 do debate». Rodada 3 de debate
   sobre TEXTO é exatamente o gasto que o Owner reclamou: o plano já levou 22
   rodadas de rail + 2 de debate sem produzir um script. **Congelar o texto e
   entregar o menor script útil.**

---

## 2. MADRUGADA — o que rodar esta noite (ordenado por itens fechados por token)

**Restrição estrutural que decide tudo:** o Owner dorme ⇒ **nenhuma assinatura GPG
é possível até de manhã**, e a decisão 4.1 dele diz que a cota de codex fica
**reservada para sessões de assinatura** (lander sem codex registra
`PENDING-CODEX` e para). Logo: **trabalhar em pack canônico esta noite tem
fechamento provado = 0**. A madrugada é de packs livres e de fechamento de planos
por documento.

| # | Item | O que é «feito» | Regra de parada PRÉ-REGISTRADA | Ganho de fechamento |
|---|---|---|---|---|
| 1 | **Ledger das 19 decisões + propagação** (docs livre; já em voo com o agente `ledger-s347`) | As 19 respostas copiadas VERBATIM para o plano/OQ citado em cada linha, commitadas | **0 rodadas de rail** (é transcrição de um ledger do Owner; as 2 lanes do lander são o gate). Se um plano exigir julgamento novo ⇒ NÃO decidir, anotar como OQ para a manhã | Fecha **PLAN-184** (residual) + ratifica o **AC-0** do FU-sentinel-gpg + registra o modelo v2 no PLAN-186 = **1 plano + 2 itens** |
| 2 | **`p171-w0-lote5` → `p171-w0-lote6`** (livres, um por vez) | Os 6 lotes do censo W0 do PLAN-171 na árvore ⇒ **W0 fechada** | lote5: **0 rodadas novas** (a nota r2 diz achados só em docs + 1 cruzamento ⇒ regra material-only). lote6: **1 rodada de mecanismo + 1 de confirmação, TETO ABSOLUTO**. P1 em byte shipado na 2.ª ⇒ `partial`, para, Owner decide | Fecha **1 wave inteira** (W0, 6/6) |
| 3 | **PLAN-187 → `done` com AC-5** (docs livre) | `docs/research/parallelism-ceiling-S34x.md` escrito **só com números já medidos** (os 26 fatos + os 3 fatos do §0 acima); AC-1..AC-4 marcados abandonados com a razão nomeada | **1 rodada, teto absoluto.** Achado que peça medição NOVA ⇒ não medir: vira nota de residual | Fecha **1 plano** |
| 4 | **PLAN-189 → parar de gastar** (docs livre) | Nota de 10 linhas no pack: A/B suspenso pela refutação da hipótese; o lock de land (`LAND.lock`) migra como item do PLAN-188; **`p189-plan-draft`/`p189-pilot-specs` NÃO landam** | **0 rodadas.** O flip formal para `abandoned` é pergunta da manhã (AskUserQuestion), porque a ordem derivada do ledger listava esses lands | Impede **35 rodadas** de continuarem; libera 3 packs |
| 5 | **`p188-plan-r3`** (livre) — SÓ com o teto já escrito no próprio pack | O texto do PLAN-188 com as figuras medidas em worktree limpo; depois **congelar o texto** | O teto já está pré-registrado: **r5 mecanismo + r6 confirmação; P1 em byte shipado na r6 ⇒ STOP, `partial`, Owner decide**. **Sem rodada 3 de debate esta noite** | Fecha o TEXTO do 188 (não o plano) |
| 6 | **Marcar os adiados com gatilho** (docs livre): 170, 172, 173, 181 ganham uma linha `external_wait`/gatilho; 174 ganha a PROPOSTA de `superseded` pelo 188 | Cada plano diz em uma frase o que precisa acontecer para ele voltar | **0 rodadas.** Flip de status de 173/174 **não** é decisão minha nem do CEO: vai por AskUserQuestion na manhã | Tira **4 planos** da fila ativa por documento; deixa **1 fechamento pronto** para a manhã |
| 7 | **`p186fu-census-runtime-w0`** (livre) — se sobrar noite | Censo por runtime landado | **1 cura + 1 confirmação, teto absoluto** (o pack já levou 6 rodadas e 2 P1 na última) | Avança (não fecha) — por isso é o último |

**O que NÃO rodar esta noite, e por quê:** `w1-widen`, `w6-adapter`,
`w4b-ci-matrix`, `w5-doctrine`, `ac13-routing-drift-v5`, `p183-w1-pointer`.
São os 6 canônicos; **148 rodadas até aqui, 0 assinaturas** (censo + `MORNING-S347.md:47-55`),
e sem Owner acordado o melhor desfecho possível é «pack esperando». Eles são o
**primeiro item do dia**, na ordem que o Owner fixou (W1 → W6a → W4b, WIP ≤ 3,
`OWNER-DECISIONS-S347.md` §4.17), com codex — que é onde a cota dele deve ir.

**Contagem esperada da manhã se a lista acima rodar:** 2 planos fechados
(184, 187), 1 wave fechada (171 W0), 1 plano com fechamento pronto para 1 clique
(174 → superseded), 4 planos formalmente adiados, 3 packs de 189 retirados de
circulação. Portfólio ativo cai de **18 → ~7**, e os 3 canônicos do dia começam
com a fila limpa.

---

## 3. COMO TRABALHAR — as mudanças que param o laço

Cada mudança abaixo se apoia num fato medido citado. Nenhuma delas afrouxa um
gate de produto.

**(a) Teto de rodadas por CLASSE, escrito na nota do CEO ANTES de relançar.**
- Pack canônico (bytes que o Owner assina): **1 rodada de mecanismo + 1 de
  confirmação**. Um P1 em byte shipado na 2.ª ⇒ `partial` e o Owner decide.
- Pack livre: **a rodada do próprio lander é a rodada** (regra material-only já
  ratificada).
- Texto de plano / desenho / evidência / material de cerimônia: **ZERO rodadas de
  codex**.
- *Fato:* 25 % docs + 22 % cerimônia + 12 % instrumentos = **59 % dos 504 achados
  fora do produto** (memória das frações); e a lição já registrada diz que a 4.ª
  cura da mesma classe pede troca de arquitetura, não outra rodada.

**(b) Onde o codex É usado.** Só em **bytes shipados de pack canônico** e na
sessão de assinatura (decisão 4.1 do Owner). **Onde NÃO é:** plano, desenho,
evidência, estado, registros, instrumento de medição, material de cerimônia.
*Fato:* 11 % dos achados eram sobre o código que ia ser assinado; a fila teve 503
esperas com p90 de 740 s — cada rodada em prosa compra 12 min de fila no p90 e
89 % de chance de não tocar o byte assinado.

**(c) «Bom o bastante» por classe de artefato** — o critério de parada que hoje
não existe e por isso a cura gera a cura:
| artefato | bom o bastante = |
|---|---|
| texto de plano | as figuras são GERADAS por instrumento e citam sha + linha; a prosa não é revisada por modelo externo |
| desenho / evidência | gerados, não digitados; um controle positivo reproduz |
| material de cerimônia | roda no harness e aborta onde deve; **sem rodada de rail** |
| bytes canônicos | 1 rodada de mecanismo limpa **sobre os bytes finais** + bateria verde |
| pack livre | as 2 lanes do lander no diff vivo |

**(d) WIP e ordem.** ≤ 3 canônicos de dia (decisão 4.17), ordem W1 → W6a → W4b.
*Fato:* a noite rodou 6 canônicos em paralelo contra o teto de 3 e fechou zero,
enquanto os livres fecharam 14 (`MORNING-S347.md:9-24` e `:74`).

**(e) Regra de rescisão de pack (nova — é a que faltava).** Um pack que passar de
**20 rodadas** sem virar assinável é **custo afundado**: para, vira nota de
residual, e a classe só volta com ARQUITETURA diferente. *Fato:* ac13 (52
rodadas, 3 arquiteturas), w1-widen (40), w5-doctrine (28), contamination-gate-v4
(26, e esse só saiu porque o CEO trocou a arquitetura da cura). Nenhum pack
acima de 20 rodadas fechou por insistência.

**(f) O que o orçamento de codex vira.** Se cada assinatura precisa de ~2
rodadas e o teto de dia é 3 canônicos, o consumo alvo é **≈ 6 rodadas de codex
por dia**, contra as 372 acumuladas. É essa a diferença entre «reservado para
assinatura» e o que aconteceu.

---

## 4. QUALIDADE — está boa? (leitura honesta, com evidência)

**Sim, a qualidade do que SAI está boa — e é medível.**
- **CI:** dos **40 últimos runs em `main`, 0 falharam**; 5 aparecem `cancelled`
  e todos são cancelamento por push seguinte (`gh run list -L 40 --branch main`;
  os `cancelled` são `00839a6`, `72910e9`, `7036a03`, `496a655`, `5ceae29`,
  todos com o mesmo sha revalidado depois). Inclui `Validate`, `Smoke Install`,
  `Ownership Nightly`, `Coverage`, `Red-team`.
- **14 lands na noite S347 com CI verde** e nenhuma regressão de campo relatada
  (`MORNING-S347.md:9-24`).
- **Defeitos de campo do adopter:** eram 3 desde a S315; **2 fecharam**
  (template de CI e `check_contamination.py`), sobra **1** (o ponteiro A1)
  — `CLAUDE.md` §5.

**O problema não é qualidade do produto; é o preço da certeza.** A mesma
medição que diz «só 11 % dos achados são de produto» diz que estamos comprando
certeza principalmente sobre papelada. Isso é o excesso de cuidado que o Owner
sentiu, e ele tem endereço exato (§3a).

**Salvaguardas que NÃO podem ser afrouxadas** — cada uma com a classe de defeito
que pega:
1. **Assinatura GPG do Owner em pack canônico** (`refuted=false` de verdade) —
   pega a classe «modelo edita arquivo de governança sem dono humano». A regra
   material-only **já exclui canônicos** e assim deve ficar.
2. **Gates de corpus DEPOIS da última edição** (`git add -A` → gates → commit) —
   pega «arquivo novo entra sem nenhum gate ter visto» (violado 2× na S321,
   `CLAUDE.md` §4).
3. **Fail-closed no matcher de segurança sobre INPUT** — pega «conteúdo que o
   guard não sabe ler passa batido».
4. **Isolamento da cadeia de auditoria por projeto + o guard de `--collect-only`**
   — pega «a suíte escreve na cadeia viva» (19.344 elos não atribuíveis na S321;
   2.356 eventos na S326).
5. **Rail de mecanismo sobre os bytes finais de pack canônico** — é a única
   fatia dos 11 % que compra defeito real; **manter, cortando o resto**.
6. **Piso de modelo VETO** (`code-reviewer`, `security-engineer` em Opus) e a
   saída 2′ do W1 (pin nunca migra sozinho) — pega «revisor rebaixado em
   silêncio». Não é candidato a economia: rebaixar aqui é a violação, não a
   otimização.

**O que PODE ser afrouxado sem perder nada, e o que entra no lugar:**
rodada de codex sobre **texto** (plano, desenho, evidência, material). Classe de
defeito que ela pegava: figura digitada em vez de medida, e afirmação sem
evidência. **Substituto mecânico:** a figura é **gerada por instrumento em
worktree limpo no sha registrado** e o texto cita `arquivo:linha` — que é
exatamente a cura que o próprio refutador do `p188-plan-r3` pré-registrou
(`p188-plan-r3/STATE.md`, decisão 1). Instrumento substitui rodada; é isso que
transforma disciplina em regra.

---

## 5. VEREDITO — três linhas

1. **O laço tem endereço:** 148 das 372 rodadas de rail estão em 6 packs
   canônicos que fecharam zero assinaturas, e 89 % dos achados não tocam o byte
   assinado — o desperdício é revisar TEXTO, não revisar código.
2. **Esta noite fecha por documento, não por cerimônia:** sem Owner acordado
   nenhum canônico pode fechar, então a madrugada fecha PLAN-184 e PLAN-187,
   fecha a W0 do PLAN-171, para o PLAN-189 e adia 4 planos — portfólio de 18
   para ~7, com os 3 canônicos do dia (W1 → W6a → W4b) começando limpos.
3. **A regra que substitui a disciplina:** teto de rodadas por classe (2 em
   canônico, 0 em texto), codex só na sessão de assinatura, e **rescisão
   automática de qualquer pack acima de 20 rodadas** — nenhum dos quatro packs
   que passaram desse número fechou por insistência.
