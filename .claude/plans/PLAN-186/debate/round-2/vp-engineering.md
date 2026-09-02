---
round: 2
archetype: VP Engineering
skill: architecture-decisions
agent_persona: (nenhuma — o arquétipo não tem bloco de persona em `team.md` nem arquivo em `.claude/agents/`; perfil sintetizado da linha do SKILL MAP)
generated_at: 2026-09-02T20:05:00Z
---

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- **Meus 9 must-fix do round 1: 6 RESOLVIDOS, 3 PARCIAIS, 0 não resolvidos.** Resolvidos: #2 raio da W3 (§3 W3 + AC-5, com a allowlist, os dois dicts congelados e o controle positivo nomeados, e a W3 agora gated na W0-US4 — mais do que pedi); #5 os 6 sítios do Step 0 (§3 W5-US1 + AC-7); #6 cobertura e re-precificação da W1 (§1 fato 5 rebaixado, §3 W1, AC-3a/AC-3b); #7 OQ-5 vira sonda (§3 W0-US6 + OQ-5); #8 `CONSUMES:` com o residual de valor-de-retorno escrito (§3 W5-US1); #9 reconciliação com `parallelization-by-default` e o hook (§3 W5-US1 + AC-7).
- **Parciais:** #1 (a ROTA) — **aceito a refutação R2 na forma absoluta**: verifiquei o mecanismo e é verdade que nenhuma das quatro superfícies faz binding do `agent()` nem do `Agent` direto, logo «ausência de decisão» sobrevive para o caminho que a W1 toca; o censo virou entregável (W0-US5, AC-12) e a tabela é OQ-7. Residual: **nada gateia a W1 na OQ-7**, enquanto a W3 ganhou gate explícito na W0-US4. #3 (detector permanente) está no corpo da W1 e em nenhum AC. #4 (regra de effort) — o eixo trocado em §2b **cura a contradição que apontei**, mas cria três novas.
- **O que o round 2 encontrou e ninguém viu:** a W1 e a W4 são **cerimônia GPG**, não waves livres. `.github/workflows/*.yml` e `.claude/workflows/**/*.js` estão os dois na lista canônica de `check_canonical_edit.py` (`:184` e `:331`), e o comentário de ratificação diz literalmente que autorar qualquer `.claude/workflows/*.js` «becomes a sentinel ceremony». O plano rotula as duas de «livre», e `external_wait` só reconhece espera de GPG na W3.

## Risks

**R-VP13 — CRITICAL — W1 e W4 são cerimônia GPG, rotuladas «livre».**
Verificado em `.claude/hooks/check_canonical_edit.py`: `.github/workflows/*.yml` e `*.yaml` na lista canônica (`:183-185`), e `.claude/workflows/**/*.js` (`:331`) com o comentário de ratificação PLAN-156-FOLLOWUP F3 em `:330`: «Cost accepted at ratification: authoring ANY `.claude/workflows/*.js` becomes a sentinel ceremony». A W1 edita os quatro `.claude/workflows/*.js`; a W4 reescreve `validate.yml` e `smoke-install.yml`. O plano diz «W1 — Herança explícita (**livre**, 1 sessão, 40-80k)» e «W4 — CI em matriz (**livre**, 3-5 sessões, 230-450k)»; `external_wait` diz «W2 apenas… W3 espera a assinatura GPG»; `eta_calendar` diz «W4-W6 sem espera externa». E o §2b usa como exemplo que «`.github/workflows/**` é "livre" por cerimônia» — premissa falsa em disco. Contradição interna: o próprio `w1/DESIGN-W1-S339.md` §3 já descreve um LAND com sentinel, `ANCHOR_SHA` e assinatura do Owner.
*Mitigação:* reclassificar as duas waves; corrigir `external_wait`, `eta_calendar` e os headers; re-orçar com o custo real de cerimônia (precedentes: `wave-fable51` 30 paths / 5 rodadas de rail, `wave-cli` 12 paths / 9 rodadas — some +1 sessão e +40-80k por wave, e nenhuma das duas pode LANDAR numa night-run). Trocar o exemplo de §2b por um artefato de fato livre (um gerador em `docs/`).

**R-VP14 — HIGH — O material da W1 no disco implementa o eixo ANTIGO; o plano afirma o novo.**
`§3 W1` diz que os 10 sítios são «roteados pela matriz §2b». O derivador em disco (`w1/apply-w1-explicit-model.py`) classifica o sítio 4 (`hygiene:${d.key}`) como **«finder/pesquisa/censo» → `claude-sonnet-5`** (`:67-69`), enquanto §2b põe **«censo»** explicitamente na linha DEFINE → `claude-opus-5`/`xhigh`. Os sítios 1 e 6 (`find:`, `lane:`) têm a mesma tensão. Executar a W1 hoje entrega a classificação velha sob um plano que declara a nova — a forma «material curado no vivo é invisível à sombra que o rail revisa», invertida.
*Mitigação:* re-derivar a classificação dos 10 sítios sob o eixo §2b e regravar o derivador (20-40k, mesma sessão), ou declarar POR SÍTIO por que a classificação antiga sobrevive ao eixo novo. Um dos dois tem de estar escrito antes da cerimônia.

**R-VP15 — HIGH — A taxonomia §2b não é TOTAL, e reclassifica retroativamente a evidência que o plano cita.**
As duas linhas produtivas são DEFINE (gate, oráculo, instrumento, censo, critério de aceite, refutação) e EXECUTA (anchor-exact, rename, docs a partir de fonte). **«pesquisa/leitura» não está em nenhuma das duas** — e era linha própria na matriz antiga. Consequência material: os quatro pesquisadores em Sonnet 5 que produziram os relatórios 01-04 (citados pelo próprio estudo como evidência de que Sonnet 5 entrega citação verificada) caem em «censo» → Opus 5 e viram violação retroativa da política. Uma partição que não cobre o domínio não classifica.
*Mitigação:* tornar a partição total — ou uma terceira linha para «pesquisa com pergunta dada» (Sonnet 5), ou dizer que pesquisa exploratória É DEFINE e aceitar o custo com o número medido ao lado. E remover «censo» de DEFINE ou distinguir «censo mecânico» (enumerar sob predicado dado) de «desenhar o predicado».

**R-VP16 — HIGH — §2b é usada como normativa na W1, mas o plano declara que ela não decide até a W5.**
O §2b termina com «O classificador de "tarefa especificada" é entregável da W5-US2 — enquanto não existir, a regra não decide nada». A W1 executa antes da W5 e roteia 13 sítios por essa regra. Ou a regra decide agora (e a frase é falsa), ou não decide (e a W1 está roteando por julgamento não escrito).
*Mitigação:* mover o classificador para a W0 como entregável de texto (10-20k, é uma página), ou declarar que a W1 roteia por uma lista NOMEADA de 13 decisões pontuais revisáveis, sem invocar a regra geral.

**R-VP17 — HIGH — O censo do nome de check afirma um conjunto FECHADO que o disco refuta.**
`§3 W4` diz «o literal … vive em `docs/BRANCH-PROTECTION.md:104`, `templates/docs/BRANCH-PROTECTION.md:44` e `templates/.github/workflows/validate.yml.template:33` — **TRÊS sítios**». Um grep sobre o repo encontra também **`RELEASE.md:258`** (runbook de release, raiz, lista de checks requeridos) e duas ocorrências no PLAN-184, que é o plano ATIVO com que a W4 tem de coordenar — `:128` na tabela de custo e `:1100` num critério de Check. O K16 já havia crescido de 2 para 3 no round 1; segue incompleto em 4+. Afirmar conjunto fechado a partir de uma lista lembrada é a classe `feedback-closed-sets-must-be-derived-not-recalled`.
*Mitigação:* substituir a lista por um comando de derivação no próprio plano e um gate que reprove o literal fora dos sítios derivados; trocar «TRÊS sítios» por «os sítios que ESTE comando retorna».

**R-VP18 — MEDIUM — O orçamento é byte-idêntico ao do round 1 com escopo materialmente maior, e o piso não sobrevive à própria aritmética.**
`budget_tokens: 850k-1.45M` e `budget_sessions: 9-12` são as mesmas strings da proposta do round 1, mas a W0 ganhou US4, US5, US6 e uma US2 re-desenhada (3 repetições por N + célula de output alto + célula de dois terminais) mantendo «150-250k», e a W1 ganhou quatro itens mantendo «40-80k». Além disso o repo MEDIU o piso re-pago em `F ≈ 97.292` tokens (`CLAUDE.md` §5): 9 sessões × 97.292k = **875k**, acima do piso declarado de 850k — o orçamento mínimo é menor que o gate-boot mínimo. (`PLAN-SCHEMA.md:328` ainda publica «~27k» para o mesmo custo, um folclore que a S322 refutou; é insumo da OQ-6, não defeito deste plano.)
*Mitigação:* re-orçar W0, W1 e W4 com o escopo novo e com o custo de cerimônia do R-VP13; e anexar à OQ-6 a constante de gate-boot do `PLAN-SCHEMA`, já que é ela que converte `budget_sessions` em tokens para todos os ~15 planos.

**R-VP19 — MEDIUM — A W1 não tem gate na OQ-7; a W3 tem na W0-US4.**
A W3 abre com «**Pré-requisito: a resposta da W0-US4**» — exatamente a forma certa. A W1 não tem nenhuma cláusula equivalente para a OQ-7, embora o plano diga que sem a rota única «a W1 cria a quinta grafia do mesmo fato, que é a forma exata dos defeitos D1-D4». Como a W1 é a wave mais barata e mais tentadora de executar primeiro, a assimetria decide o resultado na prática.
*Mitigação:* copiar a forma do gate da W3 para o topo da W1, nomeando a OQ-7 como pré-requisito ou declarando explicitamente que a W1 pode ir na frente e que a quinta grafia é dívida ACEITA, com o path do follow-up.

**R-VP20 — MEDIUM — Três entregáveis novos vivem só no corpo das waves e em nenhum AC.**
O detector permanente de roteamento (K2, corpo da W1) não aparece em AC nenhum — o AC-3a segue sendo a prova pontual «campo `model` da resposta servida», que é exatamente o que o K2 disse não bastar. O classificador de «tarefa especificada» (W5-US2) não tem AC. A sonda de hookabilidade da W0-US6 não tem AC (o AC-8 cobre a sonda de dois repos da US3, que é outra coisa). O que não está em AC pode não acontecer sem que nada fique vermelho.
*Mitigação:* três ACs curtos, ou uma perna a mais em AC-3a, AC-7 e AC-2. Custo de texto, ~5k.

**R-VP21 — LOW — A lista de ACs perdeu a ordem e a convenção de id.**
A sequência em disco é AC-1, AC-1b, AC-2, AC-3a, AC-3b, AC-4…AC-8, AC-10, AC-11, **AC-9**, AC-12 — o AC-9 caiu entre o AC-11 e o AC-12. Sufixos (`1b`, `3a`, `3b`) convivem com numeração pura. Nada mecânico quebra hoje, mas o `/fan-plan` lê blocos de AC e a lista é a superfície que o closeout marca.
*Mitigação:* reordenar; escolher uma convenção. Trivial.

## Must-fix (blocking)

1. **Reclassificar W1 e W4 como cerimônia GPG (R-VP13)** e propagar: headers das waves, `external_wait`, `eta_calendar`, orçamento, e a frase de §2b que chama `.github/workflows/**` de livre. Sem isso o plano promete em night-run duas waves que só o Owner pode landar.
2. **Re-derivar a classificação dos 10 sítios da W1 sob o eixo §2b, ou justificar sítio a sítio (R-VP14).** Hoje o artefato e o plano discordam em bytes, no mínimo em `nightly-hygiene`.
3. **Tornar a partição §2b total (R-VP15)** — «pesquisa/leitura» precisa de casa, e «censo» precisa distinguir enumerar-sob-predicado de desenhar-o-predicado, senão a política condena retroativamente a evidência que a sustenta.
4. **Resolver a ordem classificador ↔ W1 (R-VP16)**: ou o classificador sai na W0, ou a W1 roteia por lista nomeada e a regra geral não é invocada antes de existir.
5. **Trocar a lista de 3 sítios do nome de check por uma derivação (R-VP17)** e incluir `RELEASE.md` e as duas ocorrências do PLAN-184 no que a derivação tem de alcançar.
6. **Dar gate à W1 na OQ-7, no molde do gate da W3 na W0-US4 (R-VP19)** — ou declarar a quinta grafia como dívida aceita, com follow-up nomeado.
7. **ACs para o detector permanente, o classificador e a sonda US6 (R-VP20).**

## Nice-to-have (advisory)

1. Re-orçar as waves que cresceram e anexar a constante de gate-boot do `PLAN-SCHEMA:328` à OQ-6 (R-VP18); a aritmética de 9 × 97.292k vs piso de 850k é uma linha de verificação.
2. Reordenar os ACs e fixar a convenção de id (R-VP21).
3. A citação `inject-agent-context.sh:281-302` subestima o bloco: o `case` do `MODEL_HINT` vai de `:278` a `:314`. Irrelevante para a decisão, mas o censo da W0-US5 vai reler esses limites.
4. O §2b perdeu a linha do refutador não-VETO como papel nomeado (ela virou «refutação» dentro de DEFINE). Como o critério de morte da W1 depende de «P1 que o refutador não pegue», vale manter o papel visível na matriz.
5. Registrar no plano que `check_canonical_edit.py` é `_KERNEL_PATHS`: qualquer tentativa de aliviar o guard das duas árvores de workflow, se alguém propuser isso como atalho, exige override de kernel — ou seja, não é atalho.

## Unseen by the original plan

1. **As duas árvores de workflow são canônicas.** `.github/workflows/*.yml|*.yaml` (`check_canonical_edit.py:183-185`) e `.claude/workflows/**/*.js` (`:331`), esta última com o custo de cerimônia ACEITO na ratificação e escrito no comentário `:329-330`. Três críticos e o consenso trataram W1 e W4 como livres.
2. **O plano contradiz seu próprio material da W1**, que já descreve sentinel, `ANCHOR_SHA` e assinatura do Owner em `DESIGN-W1-S339.md` §3.
3. **`RELEASE.md:258` carrega o nome do check requerido** e ficou fora do censo de K16, que foi apresentado como fechado.
4. **A troca de eixo em §2b tem efeito retroativo sobre a evidência do próprio estudo** — quatro pesquisadores em Sonnet 5 passam a violar a política que a evidência deles sustenta.
5. **`PLAN-SCHEMA.md:328` publica ~27k de gate-boot**, 3,6× abaixo do `F` medido; é a constante que converte `budget_sessions` em tokens em todos os planos e pertence à OQ-6.

## What I would NOT change

- **A refutação R2 do consenso está certa e deve ficar como está.** Verifiquei o mecanismo: os pins de `agents/*.md` só vinculam no rail nativo, `routing-matrix.yaml` alimenta o `--pair-mode`, `VETO_HARDCODE` alimenta o dispatcher aprendido e o `MODEL_HINT` é texto num prompt gerado. Nenhum faz binding do `agent()` de workflow nem do `Agent` direto — minha forma absoluta («o diagnóstico é falso») era forte demais, e o escopo reduzido do K1 é a leitura correta.
- **O gate da W3 na W0-US4.** É a melhor mudança do round: transforma uma cerimônia de valor desconhecido numa cerimônia condicionada a uma medição de 3 spawns. Não afrouxar, e não inverter a ordem por conveniência de agenda.
- **A demissão do fato 5 de «fato» para «não é fato até re-derivação».** Um plano que rebaixa o próprio número-âncora está funcionando.
- **Manter os DOIS ids no piso durante a transição da W3**, para que o rollback seja mudança de settings e não segunda cerimônia. É a única forma de rollback disponível para camada T.
- **O contrabalanceamento ABBA e o tratamento de janelas censadas na W2.** Não simplificar de volta para A-B-A-B «porque é mais fácil de operar»: a ordem de depleção estava confundida com o efeito de modelo.
- **`fail-fast: false` + gate de FORMA, e o baseline de node-ids por conjunto.** São as duas defesas que impedem a W4 de ficar verde perdendo metade da suíte.
- **O residual de valor-de-retorno escrito no ADR do `CONSUMES:`.** Sem ele o check por arquivo declararia fechada uma classe que não cobre — e essa é a maior parte da classe aqui.
- **A recusa de Haiku com razão escrita no `tier_mix_rationale`.** Antecipa exatamente quem leia o estudo depois e queira «restaurar» a opção mais barata.
