---
review: S348
archetype: qa-architect
skill: evidence-based-qa
generated_at: 2026-09-06T21:35-03:00
---

# Revisão de portfólio S348 — lente de qualidade e evidência

> **Glossário mínimo** (o Owner pediu em 04/09: nada de sigla sem explicação).
> **Pack** = pacote de trabalho de um agente, com estado e provas, guardado fora do repo.
> **Rail / rodada de rail** = revisão adversarial por um segundo modelo sobre um texto ou um diff.
> **Refutação** = um agente tentando derrubar o trabalho de outro; cada uma custa uma volta inteira.
> **Canônico** = arquivo que só muda com assinatura GPG sua; **livre** = arquivo que o CEO pode commitar sozinho.
> **Bloco SIGN** = o ponto em que um pacote está pronto para você assinar, sem achado aberto.
> **Wave (onda)** = uma fatia de um plano que termina numa entrega.
> **AC** = critério de aceitação (a caixinha que o plano marca quando fecha).

## 0. As três perguntas, respondidas em uma linha cada

- **Q1 (o que ainda compra alguma coisa):** 4 planos merecem estar ativos — 169, 171, 183, 186. Dois fecham hoje sem risco (184 e 187), cinco saem do caminho por congelamento declarado (170, 172, 173, 174, 181), e o resto é follow-up ou plano que só abre depois de uma assinatura.
- **Q2 (a madrugada):** nenhuma assinatura é possível com você dormindo, então a noite vale por **fechamentos livres** — 1 commit de decisões, 2 planos fechados, 1 onda de censo fechada, 3 pacotes livres aposentados — e por deixar **um** canônico com bloco SIGN limpo para a manhã. Alvo medido: **13 planos ativos → 4**, **6 canônicos abertos → 3**.
- **Q3 (parar de rodar em círculo):** o cuidado não está no lugar errado por ser demais, está no **sujeito errado** — 372 rodadas de rail em 40 pacotes, e apenas 11 % dos achados falam do código que vai para a assinatura. A regra mecânica que substitui disciplina é uma só: **rail com custo (codex) só toca bytes que vão ser commitados num arquivo canônico; e nenhum pacote passa de 2 rodadas por noite.**

---

## 1. TABELA — um plano por linha

**% feito** lido de `plan-progress.txt` (linhas 26–50), gerado pelo CEO às 21:35 a partir das caixinhas dos planos.
**Assinaturas que faltam** = ondas canônicas ainda por assinar; `n/d` = não derivável desta leitura de 25 min (não digito número que não li).

| plano | valor medido ou esperado (uma linha) | % feito | assinaturas | veredito | evidência |
|---|---|---|---|---|---|
| **PLAN-169** fechamento + evolução | O entregável real é a **GA v1.4.0** (AC-8); o «quota-resume» é EXPERIMENTAL e declaradamente inerte para adotantes | 55 % (5/9) | 1 (a cerimônia da GA) | **re-escopar** | `PLAN-169:1394` AC-8 = GA v1.4.0; `PLAN-169:1350` AC-4 quota-resume; `plan-progress.txt:26` |
| **PLAN-170** bateria E7 | Zero valor hoje: só abre quando a tag `v1.4.0-rc.1` existir — e ela não existe | 0 % (0/35) | 0 | **adiar** (congelado declarado) | `PLAN-170:11` «abre quando `git tag --list v1.4.0-rc.1` deixar de ser vazio, nunca antes» |
| **PLAN-171** proveniência de governança | W0 (censo dos gates) é o único pedaço com entrega medida: 4 de 6 lotes landados; W3 duplica o flip da janela advisory do PLAN-178; W5 (worktree) era pré-requisito do E5 do PLAN-172, que está congelado | 0 %* (caixinhas não instrumentadas) | ≥1 (W3), n/d | **re-escopar** (fecha W0, corta W4/W5) | `PLAN-171:79` W3 FILE ASSIGNMENT; `PLAN-171:89` W4; `PLAN-171:96` W5 «pré-requisito E5»; MORNING-S347 §3 lote5/lote6 |
| **PLAN-172** velocidade honesta | Congelado por dependência dupla (169 + 171 W5) e o braço caro (E5) só abre se o E0b liberar | 0 % | 0 | **adiar** | `PLAN-172:9` depends_on; `PLAN-172:13` «E5 adicionalmente pós-PLAN-171 W5» |
| **PLAN-173** cockpit Warp | Depende dos resultados do 172, que está congelado — dependência de segunda ordem | 0 % | 0 | **adiar** | `PLAN-173:13` «gated: resultados do PLAN-172» |
| **PLAN-174** geração de cerimônia | **Dono duplicado**: o PLAN-188 nasceu em 05/09 fazendo cerimônia compartilhada (SIGN/LAND por manifesto); o 174 tinha um waiver seu de S316 para baratear cerimônia — a mesma dor, dois donos | 0 % | n/d | **re-escopar** (um dono só; recomendo o 188) | `PLAN-174:2` título; `PLAN-188:12` título; `PLAN-174:13` waiver S316 |
| **PLAN-175** poda de skills | Revisão do plano **autorizada por você** em 06/09 (4.15); é 1 pack de docs, barato, e destrava o flip | 0 % | 0 (docs) | **manter** (executar a revisão hoje) | `OWNER-DECISIONS-S347.md` §4.15 |
| **PLAN-176** currency de modelos | Revisão **autorizada por você** (4.14); é o único caminho para detectar modelo novo sem refazer a mão a cada geração — a sua própria pergunta de 20:3x | 0 % | 0 (docs) | **manter** (executar a revisão hoje) | `OWNER-DECISIONS-S347.md` §4.14 e Bloco 3b «resposta do CEO» |
| **PLAN-181** adoção do /loop | Precisa de autorização sua **por sessão** e de 1 assinatura; nada nele está no caminho da GA | 0 % | 1 (W3) | **adiar** | `PLAN-181:9` «execução W0-W3 ainda exige a autorização de execução do Owner por sessão» |
| **PLAN-183** aptidão do adotante | **A única lacuna de campo aberta desde a S315**: o ponteiro do `PROTOCOL.md` sai com caminho absoluto na casa do mantenedor. Suas 4 leituras já foram ratificadas (4.5) | 65 % (21/32) | 1 (W1 ponteiro) | **manter** | `PLAN-183:1366` AC-1 [P0] «Nenhum caminho de home ou de usuário no ponteiro»; `plan-progress.txt:41` |
| **PLAN-184** custo de CI | **Fecha por medição**: teto medido US$ 2,195/dia < N = US$ 3/dia ⇒ o pré-registro (US0) foi cumprido e a W1 não abre | 8 % (4/48) | 0 | **fechar** (residual registrado) | `OWNER-DECISIONS-S347.md` §4.6 |
| **PLAN-185-FU / PLAN-179-FU** | Já `done` — fora desta revisão | 100 % | 0 | — | `plan-progress.txt:36,43` |
| **PLAN-186** modelo de operação | É o plano que governa todos os outros (WIP, rodadas, roteamento de modelo) e concentra **todas** as assinaturas abertas | 26 % (5/19) | ~7 (W1, W4b, W5a, W5b, W6a, W6b, W-ROTA) | **manter** (WIP ≤ 3, sua decisão 4.17) | `plan-progress.txt:48`; ACs abertos em `PLAN-186:192,196,199,202,205,206,210,214,217`; MORNING-S347 §3 (5 pacotes canônicos) |
| **PLAN-186-FU census-runtime** | Censo de roteamento por runtime; pack `partial`, 2 achados P1 na última refutação | 0 % (0/3) | 0 (livre) | **manter** (land livre) | `plan-progress.txt:45`; MORNING-S347 §6 «census-runtime refutado (2 P1 novos)» |
| **PLAN-186-FU walk-from-root** | Plano já landado (`3f8f4f0`); nenhuma onda aberta — não consome nada | 0 % (0/0) | 0 | **adiar** | `plan-progress.txt:46`; MORNING-S347 §2 linha 5 |
| **PLAN-186-FU sentinel-gpg** | O AC-0 (remoção da isenção por nome no gate de contaminação) **deixa de ser provisório** por decisão sua 4.2 — 1 linha de docs fecha um critério | 12 % (1/8) | 0 (docs para o AC-0) | **manter** | `OWNER-DECISIONS-S347.md` §4.2; `plan-progress.txt:47` |
| **PLAN-187** teto de paralelismo | **Dono duplicado e pergunta já respondida**: o AC-2 do PLAN-186 já é dono da medição «N máximo sem 429 em 3/3 repetições»; e a noite mostrou que o teto real é cota + refutação, não máquina | 0 % (0/5) | 0 | **fechar** (só o relatório AC-5) | `PLAN-187:146,152` AC-1/AC-3 vs `PLAN-186:192` AC-2 (mesma medição, dois donos); `PLAN-187:154` AC-5 relatório |
| **PLAN-188** cerimônia compartilhada | Alavancagem alta **se** o pipeline canônico continuar: 22 % dos 504 achados de rail são cerimônia. Hoje essa condição é FALSA (zero assinaturas em 3 noites) | 0 % (0/6) | n/d | **manter, condicionado** (rodada 3 do debate; W1 só abre depois da 1.ª assinatura) | memória `feedback-rail-findings-class-fractions-s345.md:13`; MORNING-S347 §5 «nenhum canônico assinável» |
| **PLAN-189** A/B construtor externo | **Testa a variável errada**: o gargalo medido é a refutação (40+ refutações, 0 assinaturas), não a construção. Mas 29 rodadas já estão gastas nos 2 packs e eles estão prontos | não landado | 0 (livre) | **re-escopar** (landar o pré-registro; não abrir o experimento) | MORNING-S347 §5; `rail-rounds-census.txt:28,27` (p189-plan-draft 18 rodadas, p189-pilot-specs 11) |

\* PLAN-171 aparece com `0/0` caixinhas na tabela de progresso (`plan-progress.txt:28`) — o plano não usa o formato de checkbox que o instrumento lê. **Isso é um achado**: um plano sem caixinha é invisível ao painel de progresso e não pode ser medido. Cura de 1 linha: os ACs do 171 passam para a forma `- [ ]`.

**Aritmética do corte:** 13 planos «vivos» hoje. Fechando 184 e 187, declarando o congelamento de 170/172/173/174/181 e tirando os 3 follow-ups do painel, sobram **169, 171, 183, 186 = 4 ativos** — exatamente o corte que o brief propôs, agora com a conta feita.

---

## 2. MADRUGADA — a lista ordenada (fechar, não avançar)

**Restrição dura:** você dorme ⇒ **zero assinatura GPG** ⇒ **zero fechamento canônico**. Portanto a noite vale por fechamentos livres + deixar UM canônico com bloco SIGN limpo.

| # | item | o que significa «pronto» | regra de parada pré-registrada | fechamentos ganhos |
|---|---|---|---|---|
| 1 | **Commit das 19 decisões** (já em voo com o agente `ledger-s347`) | As 19 respostas copiadas VERBATIM para cada plano/OQ citado + o ledger commitado em `.claude/plans/PLAN-186/debate/owner-decisions-S347.md` | Sem rodada de rail. Se um plano recusar a edição por gate, registra e segue — nunca reescreve o texto da decisão | **1 plano fechado** (184 → `done` residual) + AC-0 do sentinel-gpg ratificado + regra material-only escrita no 186 |
| 2 | **PLAN-187 → `done` com o relatório AC-5** | `docs/research/parallelism-ceiling-S34x.md` escrito **só com os 26 fatos já medidos** (`PLAN-187:30` §1), cada número com a fonte; AC-1..AC-4 marcados como transferidos para o AC-2 do PLAN-186 | 1 passe de escrita. Se algum número não tiver fonte no disco, ele **não entra** no relatório (não se digita número) | **1 plano fechado** |
| 3 | **`p171-w0-lote5` → land, depois `lote6` → land** | Os dois lotes landados fecham a **W0 do PLAN-171** (censo dos 6 lotes) | Máx. **1 rodada de mecanismo + 1 de confirmação** por lote. Achado apenas em material não-commitado ⇒ land (sua regra de 04:10). Achado que nomeie um path landado ⇒ para e registra | **1 onda fechada** |
| 4 | **`p189-plan-draft` → land, depois `p189-pilot-specs`** | Os dois packs aposentados; PLAN-189 entra como **pré-registro congelado**, com a condição escrita: «não abre enquanto nenhum canônico tiver assinado» | Já tem cap absoluto na nota r14 do próprio pack: se a confirmação achar P1 nos bytes shipados, **para** e fica para você. Não abrir uma 3.ª cura da mesma classe | **2 packs aposentados** (29 rodadas gastas encerradas) |
| 5 | **`p186fu-census-runtime-w0` → land** | Os 2 P1 da última refutação curados **na fonte** (o plano ainda diz «regex ancorada»; o AC-F1 cita nota truncada) e o pack landado | 1 + 1 rodadas. Se o AC-F1 ainda quiser ticar sobre 4 superfícies, **não tica** — vira OQ e o pack landa sem ele | **1 onda de follow-up fechada** |
| 6 | **`w4b-ci-matrix`: refutação única → bloco SIGN** | O builder chegou a `ready` às 06:26 e as **3 ratificações que faltavam são justamente a sua decisão 4.8** — falta só a refutação | Cap **1 refutação + 1 confirmação**. P1 nos bytes shipados na confirmação ⇒ pack fica `partial` e espera você. Nunca uma 3.ª cura | **1 canônico pronto para assinar de manhã** |
| 7 | **Packs de docs: revisão do PLAN-176 e do PLAN-175** | Um pack de docs cada, com os consensos do debate aplicados; flip para `executing` **só depois** (sua decisão 4.10) | 1 passe cada, sem rail pago | 2 planos destravados |
| 8 | **Marcar o congelamento de 170/172/173/174/181** | Uma linha em cada plano nomeando a **condição mecânica** de reabertura (o 170 já tem: `PLAN-170:11`) | Não inventar status: `deferred` **não é legal** no esquema (`PLAN-SCHEMA.md:421` — draft/reviewed/executing/done/abandoned/refused/superseded). A condição vai no `external_wait`, não no `status` | 5 planos fora do WIP sem mentir no campo de status |

**Ordem recomendada:** 1 → 3 → 2 → 4 → 5 → 6 → 7 → 8. Os itens 1–5 não gastam rail pago; o item 6 é o único que merece codex.

**Refutação da ordem que a sua decisão 4.17 fixou (W1 → W6a → W4b):** essa prioridade foi escolhida às 20:4x, **antes** de a sua própria 4.8 completar a lista que faltava no W4b. Pela tabela de distância do MORNING §3: **W4b** precisa de «refutação + as 3 ratificações» (ratificações = feitas); **W1** precisa de «re-derivar no HEAD, rails r27/r28, materiais m11/m12, harness»; **W6a** precisa de «re-corte no derivador + rails r4/r5 + materiais m4/m5 + digest». W4b é o mais perto por uma margem grande. **Proposta:** sua ordem 4.17 vale para a **fila de assinatura da manhã**; a ordem de **trabalho da noite** começa pelo mais perto (W4b), porque é o único que pode chegar a bloco SIGN limpo antes de você acordar. Se você preferir a ordem literal, ela custa a noite inteira e provavelmente entrega zero.

---

## 3. COMO TRABALHAR — as mudanças que param o laço

Cada mudança abaixo se apoia num número que eu li, não que eu lembrei.

**Fato 1 — o laço é medível.** `rail-rounds-census.txt`: **372 rodadas de rail em 40 pacotes**, 55 registros de refutação, 20 notas de decisão do CEO. Quatro pacotes concentram **146 rodadas (39 %)**: `ac13` 52, `w1-widen` 40, `w5-doctrine` 28, `contamination-gate-v4` 26 (linhas 4, 35, 37, 6). Desses quatro, **um** landou (o contamination-gate v4, `db05586`).

**Fato 2 — o cuidado está no sujeito errado.** Dos 504 achados medidos na noite S345: **11 % sobre código de produto**, 25 % docs, 22 % cerimônia, 12 % instrumentos (memória `feedback-rail-findings-class-fractions-s345.md:12-13`). Ou seja: quase metade do esforço de revisão foi gasto em bytes que **nunca são assinados**.

**Fato 3 — a classe que nunca converge.** Instrumento que tenta prever comportamento de código lendo TEXTO não converge sob refutação: `ac13` (3 arquiteturas, 11 refutações), `W5a` (9 famílias de falso-verde), `W1` (5 contra-exemplos) — memória `feedback-instrument-that-predicts-code-by-text-never-converges.md:11`.

### As regras (mecânicas, não disciplina)

- **R1 — Teto de rodadas, verificável pelo próprio script.** Máximo **2 rodadas por pacote por noite** (1 de mecanismo + 1 de confirmação). O lançador **recusa** abrir a rodada N+1 se `ls rail-round-*.md | wc -l` do pacote já bateu o teto — isso é uma condição de arquivo, não uma promessa. Ao bater: ou muda a arquitetura, ou o pacote fica `partial` para você. *(Apoio: Fato 1; a regra já existe como texto nas notas do CEO e foi violada 4 vezes — texto não é gate.)*
- **R2 — Onde o codex entra e onde não entra.** **ENTRA**: bytes que serão commitados num arquivo **canônico** (oráculo `--is-canonical` = 1), na rodada de mecanismo e na de confirmação. **NÃO ENTRA**: docs, planos, materiais de cerimônia (DESIGN/EVIDENCE/STATE), registros de rail, e instrumentos que ainda não têm oráculo de runtime. *(Apoio: Fato 2 — 47 % dos achados vivem fora dos bytes assinados; e sua decisão 4.1 já reserva a cota do codex para sessões de assinatura.)*
- **R3 — «Bom o bastante» por classe de artefato.** É isso, e nada além:
  - *Land livre de docs:* (a) todo número **gerado** por instrumento, nunca digitado; (b) higiene do pack verde; (c) as **duas lanes de rail do próprio lander** sobre o diff vivo; (d) CI verde depois do push. **Sem rodada de refutador.** *(Apoio: a regra material-only que você ratificou em 04:10 e que já derrubou 2 packs na noite — memória `feedback-material-only-rule-for-free-packs.md:11`.)*
  - *Pack de instrumento:* o acima **+ um controle positivo que reproduz o MECANISMO** do detector (não a aparência) **+** se a pergunta é «qual é o valor desta constante/tabela?», responder **executando em subprocesso confinado ao próprio repo**, nunca lendo texto.
  - *Pack canônico:* `refuted=false` **sobre os bytes shipados** + gates de corpo rodados **depois** da última edição + `touched − scope = ∅` + bateria + `.asc`. Nada aqui se corta.
- **R4 — WIP com trava.** ≤ 3 canônicos (sua 4.17) **e** ≤ 4 planos ativos, **e** a regra que trava o acúmulo: **nenhum plano novo abre enquanto houver 3 canônicos sem assinatura**. O PLAN-189 é o primeiro caso de teste dessa regra (land do pré-registro sim; abrir o experimento não).
- **R5 — Regra de parada escrita ANTES de relançar, e por classe.** A nota do CEO que relança um pacote declara: o teto de rodadas, o que acontece ao bater, e **a classe** do achado que encerra o assunto. Já é lição registrada; o que muda é que o teto passa a ser lido do disco (R1).
- **R6 — Um plano, um dono.** Dois donos para a mesma pergunta é laço garantido: `PLAN-187:146,152` × `PLAN-186:192` (teto de concorrência) e `PLAN-174` × `PLAN-188` (geração de cerimônia). Ao abrir wave nova, o autor cita a linha do plano que **não** é dono.

---

## 4. QUALIDADE — leitura honesta, com as provas

### A qualidade do que foi entregue está boa. A prova, e o limite dela.

- **CI:** os últimos 40 runs no `main` (`gh run list -L 40 --branch main`) trazem **zero `failure`**. Os 5 `cancelled` são cancelamento por push seguinte, não falha (confirmado por SHA: `00839a6` cancelado duas vezes e revalidado em `fad3d02`). Os jobs caros passaram: `Smoke Install` verde em `a3425ba` (2026-09-06T02:18Z), `Ownership Nightly` verde em `14892ab`, `Coverage` verde em `db05586`.
- **O limite dessa prova (regra da doutrina que eu sigo — `evidence-based-qa` §Anti-Patterns «green-build-equals-good»):** CI verde diz que **os testes que existem** passaram. Não diz que a cobertura é suficiente, não diz o poder de asserção (kill rate de mutação nos módulos tocados: **NÃO MEDIDO** nesta revisão — declaro em vez de omitir), e não diz que o resultado pós-merge continua verde.
- **Defeitos de campo:** os quatro defeitos que deixaram o `main` vermelho de S322 a S327 (D1–D4, a família «resolvia a fonte errada») foram achados por **controles positivos**, não por rodadas de texto — o controle reproduziu um vazamento do CODEOWNERS vivo do mantenedor para o adotante (`CLAUDE.md` §5). É essa a diferença entre proteção e ritual.

### Onde a qualidade **não** está boa: no processo, não no produto.

- 372 rodadas de rail produziram, em três noites, **zero pacotes canônicos assináveis** (MORNING-S347 §5). Isso não é excesso de cuidado: é cuidado aplicado a bytes que não são o entregável (Fato 2).
- Um plano em execução (`PLAN-171`) não é medível pelo painel de progresso porque não usa caixinhas (`plan-progress.txt:28` → `0/0`). Um instrumento de progresso cego a um plano ativo é um instrumento com a pergunta envelhecida.

### Salvaguardas que **carregam peso** — não afrouxar, e a classe de defeito que cada uma pega

1. **Gates de corpo rodados DEPOIS da última edição** (`git add -A` → gates sobre a árvore staged → commit). Pega: *o gate respondeu sobre a árvore anterior*. Violado 2× na S321 (`CLAUDE.md` §4).
2. **Oráculo `--is-canonical` antes de editar qualquer path.** Pega: *edição canônica por Bash/python contornando o hook de Edit* (memória `feedback-oracle-before-editing-any-path`).
3. **`touched − scope = ∅` no land.** Pega: *patch assinado carregando arquivo fora do escopo assinado* (`CLAUDE.md` §5, nasceu automatizado no `OWNER-S321-LAND.sh`).
4. **Controle positivo que reproduz o MECANISMO.** Pega: *guard falso-verde* — foi o que expôs o vazamento do CODEOWNERS (D4).
5. **Conjunto RED exato do Ownership Nightly (62 verde / 3 vermelho).** Pega: *mudança silenciosa na tabela de posse* — um run todo-verde ali significa que a tabela mudou (`CLAUDE.md` §4).
6. **Fail-closed na entrada dos matchers de segurança.** Pega: *conteúdo que o guard não consegue parsear passando adiante* (`CLAUDE.md` §4).
7. **Isolamento da cadeia de auditoria nos testes (redirect da janela de coleção).** Pega: *a suíte escrevendo na cadeia HMAC viva* — foram 2.356 eventos, 79 % do segmento vivo, antes da cura (`CLAUDE.md` §5, S326).
8. **As duas lanes de rail do lander sobre o diff vivo.** Pega: *pack livre que passou nas rodadas mas piorou nos bytes finais* — derrubou 2 packs na noite S347. **É o gate que substitui o refutador nos packs livres — se você cortar rodadas, esta fica.**

### Rituais que podem sair — e o que ocupa o lugar

| ritual | por que é ritual | o que substitui |
|---|---|---|
| Rodada de rail sobre DESIGN/EVIDENCE/STATE | 25 % dos achados são docs e nenhum deles muda um byte assinado; cada P2 em DESIGN custou 40–60 min | **Gerar** esses arquivos por instrumento: número digitado é a classe de defeito; geração remove a classe |
| Refutador em pack livre de docs | O lander já revisa os bytes finais em 2 lanes | Regra material-only (já sua, 04:10) + as 2 lanes do lander |
| A 3.ª cura da mesma classe | Medido: `ac13` 52 rodadas, 3 arquiteturas, ainda aberto | Trocar a arquitetura, ou fechar por construção (não fazer a ação), ou escalar para você |
| Instrumento que prevê runtime lendo texto | 3 packs, ~40 refutações, zero convergência | Oráculo de runtime confinado ao próprio repo, ou promessa estreitada pelo modelo de ameaça |

### O que eu **não** assino

Não assino a frase «a qualidade está boa» sem estas duas ressalvas escritas: (a) **kill rate de mutação nos módulos tocados = NÃO MEDIDO** nesta revisão; (b) há **2 flakes conhecidos e declarados** (`test_ceo_boot_enhanced.py::TestIdempotency::test_back_to_back_identical_results` e `test_write_endpoints.py::...rejects_action_not_in_allowlist`, `OWNER-DECISIONS-S347.md` §4.11) — um teste que oscila não é «verde com ruído», é sentinela não confiável, e enquanto ele estiver na bateria nenhum sign-off pode citá-lo.

---

## 5. VEREDITO — três linhas

1. **A qualidade do que foi entregue está boa e tem prova** (40 runs no `main` sem uma falha; os defeitos de campo foram pegos por controles positivos, não por rodadas de texto) — **o que não está bom é onde o cuidado é gasto**: 372 rodadas de rail para 11 % de achados sobre o código que vai à assinatura.
2. **A madrugada deve fechar, não avançar**: 2 planos fechados (184, 187), 1 onda fechada (W0 do PLAN-171), 3 packs aposentados (p189 ×2, census-runtime), 5 planos formalmente congelados e **um** canônico (`w4b-ci-matrix`) com bloco SIGN limpo esperando sua assinatura na manhã — 13 planos ativos viram 4.
3. **A cura do laço não é mais revisão nem plano novo**: é um teto de 2 rodadas por pacote lido do disco pelo próprio lançador, codex apenas sobre bytes canônicos, materiais de cerimônia gerados em vez de revisados, e a trava de que nenhum plano novo abre com 3 canônicos por assinar — as 8 salvaguardas da §4 ficam intactas, porque foram elas que pegaram os defeitos reais.
