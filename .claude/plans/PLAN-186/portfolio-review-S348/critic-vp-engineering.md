---
review: S348
archetype: vp-engineering
skill: architecture-decisions
generated_at: 2026-09-06T21:35-03:00
---

# Revisão de portfólio S348 — lente VP de Engenharia

> **Glossário mínimo (o Owner pediu isso em 04/09).** *Plano* = arquivo em
> `.claude/plans/`. *Wave* = fatia de execução dentro de um plano (W0, W1…).
> *Pack* = pasta de trabalho de uma wave em `s344-packs/<chave>/`, com o patch,
> a evidência e os registros de revisão. *Rail* = rodada de revisão adversarial
> (um segundo modelo lê o patch e tenta derrubá-lo). *Canônico* = arquivo que só
> muda com assinatura GPG do Owner. *Livre* = arquivo que qualquer land pode
> tocar sem assinatura. *AC* = critério de aceite (a caixinha `[ ]` do plano).
> *Land* = commitar o pack na árvore viva.

**Mantra desta revisão:** um plano que não fecha por construção é um desejo.

---

## 0. O número que responde à frase do Owner

O Owner escreveu: «estamos gastando muito de codex na revisão e parece que
estamos em looping». O censo mede isso:

- **372 rodadas de rail em 40 packs** (soma de `rail_round_records` em
  `portfolio-review-S348/rail-rounds-census.txt`, linhas 2–41).
- **126 dessas rodadas (33,9 %) revisaram um TEXTO DE PLANO, um documento ou um
  censo** — não código que vai para uma assinatura. Contas: packs
  `p188-plan-draft` 10, `p188-plan-r2` 8, `p188-plan-r3` 4, `p189-plan-draft` 18,
  `p189-pilot-specs` 11, `walkroot-followup-plan` 10, `us5-followup-docs` 5,
  `p187-night-facts` 6, os seis lotes do censo do PLAN-171 (15+3+3+11+4+3+15=54)
  e `p184-derive-ci-cost` 0.
- **5 packs concentram 164 rodadas (44 % do total)**: `ac13-routing-drift-v5` 52,
  `w1-widen` 40, `w5-doctrine` 28, `contamination-gate-v4` 26,
  `p169-w41-quota-resume` 18 e `p183-w1-pointer` 18. **Desses, só um landou**
  (`contamination-gate-v4` → `db05586`, MORNING-S347.md:23).
- Isso confirma, com números desta casa, a medição de 05/09 registrada em
  `memory/feedback-rail-findings-class-fractions-s345.md:11-13`: de 504 achados,
  **11 % eram sobre o código que vai para a assinatura**; metade era papelada.

**Diagnóstico de arquitetura, em uma frase:** o gargalo não é construir nem
decidir — é que o mesmo instrumento de revisão caro foi apontado para a classe
de artefato ERRADA (prosa de plano e material de cerimônia), e sem teto de
rodadas. O caso extremo está no disco: `p189-plan-draft` tem **18 registros de
rail** (`s344-packs/p189-plan-draft/rail-round-1..17.md`) sobre um documento de
plano que **ainda não existe na árvore** (`ls .claude/plans/ | grep -c PLAN-189`
→ 0).

---

## 1. TABELA — um veredito por plano aberto

`% feito` é lido de `plan-progress.txt` (caixas marcadas / total). «Assinaturas»
= assinaturas GPG do Owner ainda necessárias para o plano fechar, contadas a
partir de MORNING-S347.md §3.

| plano | valor medido/esperado (1 linha) | % feito | assinaturas | veredito | evidência |
|---|---|---|---|---|---|
| **PLAN-169** closure + cross-session | O entregável real é a **GA v1.4.0** (AC-8). O `quota-resume` (retomar sessão quando a cota estoura) é EXPERIMENTAL e **inerte para adotantes** por decisão do próprio Owner | 55 % (5/9) | 1 (corte GA) | **re-escopar** | AC-8 aberto `PLAN-169:1394`; AC-4 aberto `:1350`; «inerte para adotantes até o piso de StopFailure mudar» `OWNER-DECISIONS-S347.md:18` |
| **PLAN-170** bateria E7 | Zero hoje: o gatilho declarado é a tag `v1.4.0-rc.1`, que **não existe** | 0 % (0/35) | 0 | **adiar** | `external_wait` em `PLAN-170:11`; `git tag --list 'v1.4.0*'` = vazio (rodado 06/09) |
| **PLAN-171** proveniência | W0 (censo dos gates) já mediu 4 lotes de 6 e desmentiu um zero; W3 **duplica** cerimônia que já tem dono; W5 servia a um plano congelado | 0 % (frontmatter sem caixas; 4/6 lotes landados) | 0–1 | **re-escopar** | W3 = FILE ASSIGNMENT em write-time `PLAN-171:79-88` vs. o flip já agendado em `CLAUDE.md:89` («enforce flip … FUTURE ceremony gated on the advisory window»); W5 é «pré-requisito do E5» `PLAN-171:154-155`, e o E5 mora no PLAN-172 congelado `PLAN-172:13` |
| **PLAN-172** velocidade honesta | Congelado; o braço caro (E5) depende do PLAN-171 W5, que esta revisão recomenda matar | 0 % | 0 | **adiar** | `external_wait` `PLAN-172:13` |
| **PLAN-173** cockpit Warp | Estudo explicitamente **gated nos resultados do PLAN-172** — que não rodou | 0 % | 0 | **adiar** | `PLAN-173:13` |
| **PLAN-174** geração de cerimônia | **Colide de frente com o PLAN-188.** O próprio PLAN-188 registra a colisão e exige «uma decisão registrada sobre a W3 do PLAN-174» | 0 % | 0 | **fechar** (absorver no 188) | `PLAN-188:214-219`, que cita `PLAN-174:98`; waiver do Owner de S316 nunca executado `PLAN-174:13` |
| **PLAN-175** poda de skills | Real: «166 skills» é a maior distância entre claim e realidade; mas a regra de poda como escrita **arquivaria este próprio repo** | 0 % | 0 | **re-escopar** | seed `PLAN-175:19-25`; revisão autorizada `OWNER-DECISIONS-S347.md:14`; «a regra como está arquivaria ceo-orchestration» `MORNING-S347.md:61` |
| **PLAN-176** currency de modelos | Detectar modelo novo automaticamente (a adoção nunca é automática). Debate escalou: a W1 injetaria rede em módulo declarado sem rede | 0 % | 0 | **re-escopar** | `OWNER-DECISIONS-S347.md:13`; `MORNING-S347.md:60` |
| **PLAN-181** adoção do /loop | Bloqueado por construção: a wave-piloto só existe DURANTE um hold RC→GA ativo, que não há | 0 % | 1 (W3) | **adiar** | `external_wait` `PLAN-181:18` |
| **PLAN-183** adopter fitness | A **única lacuna de campo aberta desde a S315**: o ponteiro do `PROTOCOL.md` sai com caminho absoluto na casa do adotante. Os outros 6 AC já fecharam | 65 % (21/32) | 1 (`p183-w1-pointer`) | **manter** | AC-1 é o único P0 aberto `PLAN-183:1366`; AC-2..AC-7 `[x]` `:1369-1553`; distância à assinatura `MORNING-S347.md:43` |
| **PLAN-184** custo de CI | **Fecha por medição**: teto medido US$ 2,195/dia < N = US$ 3/dia ⇒ não há corte a fazer | 8 % (4/48) | 0 | **fechar** | decisão 4.6 `OWNER-DECISIONS-S347.md:19` |
| **PLAN-186** modelo operacional | Onde está o valor de governança do trimestre (roteamento papel→modelo, teto de concorrência, CI em matriz). W4a já mediu Validate 20m31s → 8m07s | 26 % (5/19) | 4–5 (W1, W6a, W6b, W4b, W5a) | **manter, com WIP ≤ 3** | AC-16 `[x]` `PLAN-186:207`; ACs abertos `:192,196,199,202,206,210`; teto ≤3 decidido `OWNER-DECISIONS-S347.md:30` |
| **PLAN-186-FU** censo por runtime | É **a cura da classe que não converge**: responder «qual modelo é servido?» executando, não lendo texto | 0 % (0/3) | 0 | **manter** | lição `memory/feedback-instrument-that-predicts-code-by-text-never-converges.md:15-16`; lineage `PLAN-186-FOLLOWUP-census-runtime.md:20-26` |
| **PLAN-186-FU** hint walk-from-root | Bloqueado em **quatro** frentes, e duas são kernel (assinatura de sentinel não destrava kernel) | 0 % | ≥1 | **adiar** | `external_wait` `PLAN-186-FOLLOWUP-hint-discovery-walk-from-root.md:14` |
| **PLAN-186-FU** sentinel GPG | Fecha um furo real: um `.asc` de 4 bytes digitado à mão isentava qualquer documento ao lado dele | 12 % (1/8) | 0 | **manter** (fora do WIP) | `PLAN-186-FOLLOWUP-sentinel-gpg-verification.md:22-26`; AC-0 ratificado `OWNER-DECISIONS-S347.md:15` |
| **PLAN-187** teto de paralelismo | **Já entregou o que dava para entregar**: 26 fatos medidos e landados. O resto é inobservável por construção | 0 % (0/5) | 0 | **fechar** | AC-4 «PARCIALMENTE informado», «RSS por agente NÃO é observável» e correlação por worktree confundida, `PLAN-187:169`; AC-1..AC-5 `:146-154` |
| **PLAN-188** cerimônia compartilhada | Alta alavancagem SE o pipeline canônico continuar: cerimônia é 22 % dos achados e **28 % dos P0/P1** | 0 % (0/6) | 0 (por ora) | **manter** (absorvendo o 174) | fração medida `memory/feedback-rail-findings-class-fractions-s345.md:11-13`; colisão com 174 `PLAN-188:214-219` |
| **PLAN-189** A/B construtor externo | O A/B pergunta quem CONSTRÓI mais rápido. A noite mediu que o gargalo é a REFUTAÇÃO | n/a (não landado) | 0 | **re-escopar** | «os 6 abertos consumiram 40+ refutações» `MORNING-S347.md:69`; 18 rodadas de rail no rascunho (`rail-rounds-census.txt:28`) e o plano não existe em `.claude/plans/` |

### Onde eu REFUTO o brief preliminar do CEO

O brief (`memory/project-portfolio-review-brief-s348.md:16-24`) acerta em 187,
184, 183 e 171. Três correções:

1. **O brief não vê a duplicação mais cara do portfólio: PLAN-174 × PLAN-188.**
   São dois planos para o mesmo defeito (bash de cerimônia descartável). O
   PLAN-188 já sabe disso e pede a decisão em `PLAN-188:214-219`. Deixar os dois
   vivos garante que a próxima cerimônia seja revisada duas vezes. **Fechar o 174
   como `superseded` pelo 188** é o único movimento que fecha por construção.
2. **«Fechar o PLAN-184 como done-residual» não é uma transição legal.** O plano
   está em `status: draft` (`PLAN-184:4`) e o esquema só permite
   `draft → reviewed | abandoned` (`PLAN-SCHEMA.md:394`). O fecho tem de ser
   `abandoned` com a seção «Abandonment reason» (`PLAN-SCHEMA.md:425`) citando o
   teto medido. Vale o mesmo para o PLAN-187. **Não existe status `deferred`**
   no esquema (`PLAN-SCHEMA.md:421-422`) — «adiar» = manter o status e escrever o
   gatilho, não inventar campo.
3. **O brief trata os congelados 170/172/173/181 como «manter congelados».** Eles
   não custam rodada, mas custam a coisa que o Owner reclamou: a sensação de 13
   planos parados. O custo de escrever o gatilho é 4 linhas; o benefício é o
   portfólio ativo cair de 18 para 8 itens.

---

## 2. MADRUGADA — a fila desta noite, em ordem

Regras da noite: Owner dormindo ⇒ **nenhuma assinatura GPG é possível**; logo
**nenhum pack canônico pode fechar hoje** — o máximo que um canônico alcança é
«bloco de assinatura limpo, esperando a manhã». Por isso a fila abaixo prioriza
o que **FECHA** (plano vira terminal, ou wave landa) sobre o que **avança**.

| # | item | o que significa «pronto» | regra de parada (pré-registrada) | ganho |
|---|---|---|---|---|
| 1 | **Propagar as 19 decisões** (já em voo com o agente `ledger-s347`) | Um commit docs com o ledger + as notas nos 7 planos citados em `OWNER-DECISIONS-S347.md:42` | Zero rodada de rail (docs livre, regra material-only). Se o CI reprovar, corrigir e recommitar — nunca abrir rodada | destrava tudo abaixo |
| 2 | **Fechar PLAN-184** | `status: abandoned` + seção «Abandonment reason» com o teto US$ 2,195/dia < N=3 e o US0 cumprido | 0 rodadas. Se alguém achar que falta dado, o fecho continua: a decisão é do Owner (4.6) | **−1 plano** |
| 3 | **Fechar PLAN-187** | Publicar `docs/research/parallelism-ceiling-S34x.md` a partir dos 26 fatos JÁ landados (AC-5) e marcar AC-1..AC-4 abandonados com a razão medida (RSS por agente inobservável, `PLAN-187:169`) | 1 rodada de mecanismo sobre o script que gera o relatório; **nenhuma** sobre a prosa | **−1 plano** |
| 4 | **Fechar PLAN-174 como `superseded_by: PLAN-188`** | Frontmatter `status: superseded` + `superseded_by` (`PLAN-SCHEMA.md:400`) + parágrafo em PLAN-188 assumindo a W3 (a decisão que `PLAN-188:218` exige) | 0 rodadas — é transferência de escopo, não código | **−1 plano e −1 colisão** |
| 5 | **Landar `p171-w0-lote5` e depois `lote6`** | W0 do PLAN-171 fecha 6/6; o lote 6 escreve os 11 hooks não registrados + 2 validadores de release | lote5 já é admissível pela regra material-only (`MORNING-S347.md:49`); lote6: **teto de 2 rodadas**; se a 2.ª ainda achar P1 nos bytes, para e fica para a manhã | **−1 wave (W0)** |
| 6 | **Escrever o gatilho de 170/172/173/181** | Uma linha em cada `external_wait` dizendo o evento que reabre (ex.: «reabre quando `git tag --list v1.4.0-rc.1` deixar de ser vazio») + nota na revisão | 0 rodadas | portfólio ativo 18 → ~10 |
| 7 | **Landar `p189-plan-draft`** (com o escopo re-cortado) | O plano entra na árvore com o braço medido trocado: mede REFUTAÇÃO, não construção | **teto absoluto: as 2 rodadas já decididas em `p189-plan-draft/STATE.md:7` (r15+r16); se r16 ainda achar P1, o pack fica `partial` e para** — não abrir r19 | fecha 1 pack com 18 rodadas afundadas |
| 8 | **`p188-plan-r3`** (revisão do PLAN-188 com os 15 must-fix) | Plano revisado em HEAD, absorvendo a W3 do 174 (item 4) | 1 rodada de confirmação e para. **22 rodadas já foram gastas no rascunho** deste plano (10+8+4) — mais uma é a última | avança o dono único da cerimônia |
| 9 | **Só então**, um único canônico até o bloco de assinatura: **W1 (`w1-widen`)** | Bloco SIGN limpo, esperando a manhã. Nada mais | `w1-widen` já tem **40 rodadas** (`rail-rounds-census.txt:35`). **Teto: 2 rodadas.** Se não fechar, escrever a nota e parar | prepara a 1.ª assinatura da manhã |

**Ganho esperado da noite: 3 planos fechados (184, 187, 174), 1 wave fechada
(PLAN-171 W0), 4 planos formalmente adiados com gatilho, 2 packs livres landados,
1 canônico pronto para assinar.** Comparado com a noite S347 — 14 lands, **zero**
planos fechados, **zero** canônicos assináveis (`MORNING-S347.md:69`) — é a
primeira noite que reduz o portfólio em vez de engordá-lo.

**O que NÃO entra na madrugada:** W6a, W6b, W4b, W5a, ac13, p183-W1. Não porque
sejam ruins — porque o teto de 3 canônicos é do Owner
(`OWNER-DECISIONS-S347.md:30`) e porque nenhum deles pode FECHAR hoje.

---

## 3. COMO TRABALHAR — as mudanças que param o looping

Cada regra abaixo está pendurada num número lido, não numa opinião.

**R1 — O codex só revisa bytes que vão para uma assinatura.**
Medido: 33,9 % das 372 rodadas revisaram plano/documento/censo (§0), e só 11 %
dos 504 achados de 05/09 eram sobre código que vai para a assinatura
(`memory/feedback-rail-findings-class-fractions-s345.md:11-13`). Regra: rail
externo **só** em pack canônico. Plano, ADR, EVIDENCE, DESIGN, material de
cerimônia e instrumento de censo → revisão interna do lander (as duas lanes que
já existem) e ponto. Isso casa com a decisão 4.1 do Owner («reservar a cota do
codex para sessões de assinatura», `OWNER-DECISIONS-S347.md:36`) — hoje a
decisão está escrita e a prática não a segue.

**R2 — Teto de rodadas por CLASSE, escrito na nota do CEO antes de relançar.**
- prosa de plano / docs: **1** rodada (a do lander).
- material de cerimônia: **1** rodada.
- instrumento (censo, gerador, script de medição): **2** rodadas.
- bytes canônicos de produto: **2** rodadas (1 de mecanismo + 1 de confirmação).
Ao bater o teto: **muda a arquitetura ou vai ao Owner — nunca a 3.ª cura da mesma
classe** (`memory/feedback-instrument-that-predicts-code-by-text-never-converges.md:19`).
Prova de que o teto faltava: `ac13` 52 rodadas, `w1-widen` 40, `w5-doctrine` 28,
`p189-plan-draft` 18 — e um único desses landou.

**R3 — Instrumento que prevê comportamento de código lendo TEXTO é proibido.**
Três packs na mesma noite morreram nessa forma (ac13: 3 arquiteturas / 11
refutações; W5a: 9 famílias de falso-verde; W1: 5 contra-exemplos —
`memory/feedback-instrument-that-predicts-code-by-text-never-converges.md:11`).
As três saídas legítimas, em ordem de preferência: (a) **fechar por construção**
— não fazer a ação (é a saída 2′ da W1: o upgrade nunca migra o pin sozinho,
`OWNER-DECISIONS-S347.md:6`); (b) **oráculo de runtime confinado ao próprio
repo** (é o `PLAN-186-FOLLOWUP-census-runtime`); (c) **estreitar a promessa pelo
modelo de ameaça** e deixar a varredura de texto como lint advisory.

**R4 — «Bom o bastante», por classe de artefato.**
- *plano/ADR*: cada número citado é LIDO da árvore com o comando ao lado; nenhum
  P1 em fato citado. Prosa imperfeita **landa**.
- *material de cerimônia*: o script roda no ensaio (`--dry-run`) sem abortar.
- *instrumento*: tem controle POSITIVO (planta um defeito, o instrumento acusa).
- *bytes canônicos*: `refuted=false` real — a regra material-only **nunca** vale
  para canônico (`memory/feedback-material-only-rule-for-free-packs.md:12`).

**R5 — WIP ≤ 3 canônicos de dia; à noite, ≤ 1 até o bloco de assinatura.**
O teto ≤ 3 é do Owner (`OWNER-DECISIONS-S347.md:30`). O reforço noturno é meu, e
o dado o sustenta: a noite S347 rodou 6 canônicos abertos e fechou zero
(`MORNING-S347.md:63,69`). Sem assinatura possível, o 2.º canônico da noite é
trabalho especulativo.

**R6 — Um plano por defeito. Duplicata vira `superseded`, não «coordena com».**
`PLAN-188:214-219` mostra o custo de não ter essa regra: o 188 não pode aposentar
o gerador de cerimônia porque o 174 agenda uma wave que o estende. E
`PLAN-171:79-88` × `CLAUDE.md:89` mostram a mesma forma no enforce de FILE
ASSIGNMENT — dois planos, um mecanismo.

**R7 — Todo plano declara a sua condição de fecho por construção.**
Regra de admissão nova: um plano só sai de `draft` com uma linha «este plano
fecha quando X for verdade», onde X é um comando. PLAN-170 já faz isso
(`git tag --list v1.4.0-rc.1`, `PLAN-170:11`) — por isso ele é o único congelado
que ninguém precisa reavaliar. PLAN-186 não faz, e por isso tem 19 caixas.

---

## 4. QUALIDADE — a leitura honesta

O Owner escreveu «não sei nem como tá a qualidade, pode realmente estar boa». A
evidência diz: **a qualidade está boa; o que está ruim é a vazão.** Separar as
duas coisas é o achado principal desta revisão.

**O que sustenta «boa»:**
1. **CI.** Últimos 40 runs em `main` (`gh run list -L 40 --branch main`, janela
   2026-09-04T20:14Z → 2026-09-07T00:00Z): **zero `failure`**. 6 `cancelled` no
   Validate são cancelamento por push seguinte, não falha; tudo o mais
   `success`, incluindo `Smoke Install` (2/2), `Ownership Nightly` (2/2),
   `Coverage` (2/2) e o `Red-team adversarial eval` em modo enforcing.
2. **14 lands na noite S347 com CI verde** (`MORNING-S347.md:9`), incluindo o
   conserto que faz a bateria completa de hooks voltar a terminar nesta máquina.
3. **Defeitos de campo estão fechando.** O relatório do adotante da S315 tinha 3
   defeitos: dois fecharam e o terceiro (ponteiro absoluto do `PROTOCOL.md`) é
   exatamente o AC-1 aberto do PLAN-183 (`PLAN-183:1366`) — é a última lacuna de
   campo conhecida, e ela tem dono.
4. **O rail acha defeito real quando aponta para produto.** Não é teatro: 11 %
   dos 504 achados eram produto, e a noite S329 registrou 9 P1 reais curados com
   controle em bytes.

**O que sustenta «lento»:** 372 rodadas de rail produziram, na última noite,
**zero** planos fechados. A causa não é rigor demais no lugar certo — é rigor no
lugar errado (§0) e ausência de teto (R2).

**Salvaguardas que são estruturais e NÃO podem ser afrouxadas** — cada uma com a
classe de defeito que ela pega:

| salvaguarda | classe de defeito que ela pega | evidência |
|---|---|---|
| Assinatura GPG do Owner em edição canônica | mudança em arquivo que decide segurança/posse entrando sem dono humano | `CLAUDE.md:89` (protocolo de spawn); regra material-only exclui canônico explicitamente (`memory/feedback-material-only-rule-for-free-packs.md:12`) |
| `refuted=false` real em pack canônico | achado P1 nos bytes assinados sendo perdoado por «é só material» | mesma linha acima |
| Fail-closed em parse de INPUT nos matchers de segurança | conteúdo que o guard não consegue ler passando batido | `CLAUDE.md` §4, bullet «Fail-open on infrastructure, fail-closed on input» |
| Gates de corpus DEPOIS da última edição (`git add -A` → gates → commit) | arquivo novo entrando sem nenhum gate tê-lo visto (violado 2× na S321) | `CLAUDE.md` §4, bullet «Corpus gates run AFTER the last edit» |
| Verificação da assinatura do sentinel (o follow-up GPG) | `.asc` de 4 bytes digitado à mão isentando qualquer documento vizinho | `PLAN-186-FOLLOWUP-sentinel-gpg-verification.md:22-26` |
| A regra dos gatilhos de plano congelado | plano reabrir sem que a pré-condição exista (PLAN-170 sem a tag) | `PLAN-170:11` + `git tag --list` vazio |

**Onde o cuidado é excessivo, com nome e sobrenome:** rodadas de rail externo
sobre (i) texto de plano — 126 rodadas; (ii) material de cerimônia não
commitado — a regra material-only de 06/09 já o reconhece
(`memory/feedback-material-only-rule-for-free-packs.md:11`: «cada P2/P3 em DESIGN
custava uma volta inteira de builder + refutador (~40–60 min) sem mudar um byte
landado»); (iii) a 3.ª cura da mesma classe num leitor de texto. Cortar esses
três não afrouxa nenhuma linha da tabela acima — eles não são salvaguarda de
nada, são revisão de prosa.

**O que eu NÃO recomendo, e por quê:** não recomendo «mais uma rodada» como cura
de nada, e não recomendo abrir um plano novo para resolver o excesso de planos.
As duas coisas são a doença, não o remédio.

---

## 5. VEREDITO — três linhas

1. **A qualidade está boa e mensurável** (40 runs de CI sem uma falha; defeitos
   de campo fechando; a última lacuna do adotante com dono no PLAN-183); **o que
   está quebrado é a mira do instrumento de revisão** — 34 % das 372 rodadas
   revisaram prosa, e 5 packs consumiram 44 % delas com 1 land.

2. **Esta noite fecha três planos e uma wave sem gastar uma única assinatura**
   (184 → `abandoned` por medição; 187 → `abandoned` com o relatório AC-5
   entregue; 174 → `superseded_by: PLAN-188`; PLAN-171 W0 6/6), e adia
   formalmente quatro congelados escrevendo o comando que os reabre — o portfólio
   ativo cai de 18 itens para ~10 antes do café.

3. **A regra mecânica que substitui a disciplina é uma só: teto de rodadas por
   classe de artefato, com codex apontado exclusivamente para bytes canônicos**
   (R1+R2); tudo o que ela não cobre fecha por construção — um plano por defeito
   (R6) e uma condição de fecho executável em cada plano (R7). Sem isso, a
   próxima noite repete: 14 lands, zero fechamentos.
