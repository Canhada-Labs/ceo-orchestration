---
plan: PLAN-174
round: 1
rounds_synthesized: [round-1]
agents_considered: [Critic-A, Critic-B, Critic-C]
decisions_revised_in_plan:
  - "W1 reescrita como catálogo-DELTA contra OWNER-CEREMONY-CONTRACT.md, em duas seções, com post-mortem 0/27 (F1/F6)"
  - "W2 reordenada: shellcheck no workflow novo + descoberta por conteúdo + lint só para o resíduo; validate.yml deferido pós-183-W2 (F2/F4/F5)"
  - "AC de FP reescrito: zero-FP só BLOCKING; waiver pinado por sha256 com data/motivo; baseline só encolhe (F3)"
  - "§2b ganha AC do loop de fechamento do W3 + enumeração de garantias derivada do contrato (singles A)"
  - "Baseline do W4 congelada por comando (34/44); semente e external_wait corrigidos (F8)"
  - "Fronteira dos signing scripts declarada com consequência de recálculo se fora-de-alcance (F7)"
created_at: 2026-08-20
synthesized_at: 2026-08-20
synthesized_by: "CEO (S316); revisão cross-model codex r1 REJECT → curas aplicadas nesta versão"
synthesis: anonimizada (DEBATE-SCHEMA 13.2) — Critic-A/B/C
round_verdict: PROCEED
scope: "W1-W2 sob waiver S316; W3-W4 mantêm gate original"
---

# consensus.md — PLAN-174, debate L3 round 1 (escopo W1-W2)

> Síntese anonimizada (DEBATE-SCHEMA §13.2). Três críticas, todas
> **ADJUST**, com convergência incomum: os três derrubaram premissas
> DE NÚMERO do plano medindo o corpus real. Nenhum VETO; nenhum
> deadlock. Onde havia divergência (F5), 2-de-3 + o risco menor
> decidem. Verificações minhas marcadas `[verificado]`.

## 1. Consensus findings

**F1 — O catálogo/mandato JÁ EXISTE, não-enforçado, e o plano ia
reescrevê-lo sem saber. (A, B)** [severidade acordada: ALTA]
`docs/OWNER-CEREMONY-CONTRACT.md` (S75/S81) já é o contrato do que todo
`OWNER-*.sh` deve fazer, já nomeia `|| true`-em-bloco-que-enforça como
anti-padrão, e já contém o MUST *"new ceremony scripts MUST be generated
by that tool"* (`:167-180`) apontando para
`.claude/scripts/local/generate-ceremony.sh` (558 linhas — a doc diz
440, stale). Sonda de conformidade (B): **0 de 27** scripts de cerimônia
carregam a marca `AUTO-GENERATED`; `grep -rln "OWNER-CEREMONY-CONTRACT"`
sobre py/sh/yml = **zero** (A). Um MUST escrito atravessou ≥8 planos com
conformidade 0/27 e NENHUM instrumento notou. ⇒ **W1 vira DELTA contra o
contrato** (quais regras têm enforcement; quais classes o contrato não
nomeia) + post-mortem de 1 parágrafo por família sobre POR QUE o MUST
falhou (hipótese forte de B: o gerador serve cerimônia de canonical-edit
com sentinel, não corte de tag/publish — se confirmada, separa as DUAS
famílias no catálogo). Primeira regra do W2 = **check de proveniência**
(script de cerimônia sem marca e sem exceção explícita ⇒ vermelho).

**F2 — O instrumento que falta já está instalado e não enxerga o alvo.
(A, B, C)** [severidade acordada: ALTA]
`validate.yml:306-310` roda shellcheck só sobre `.claude/scripts` +
`.claude/hooks`; os scripts de cerimônia moram em `.claude/plans/*/` —
**nunca foram shellcheck-ados** (e a exclusão
`owner-ceremony/archive/*` aponta para diretório inexistente). Controle
positivo (A): com `--enable=check-extra-masked-returns`, o SC2312 acusa
`run-ga-repass.sh:26` — exatamente o P1 que o round 17 do trem achou 12
rodadas depois. ⇒ **A W2 começa estendendo o escopo do shellcheck
existente + flags cirúrgicas** (`check-extra-masked-returns`, SC2154,
SC2034); NUNCA `--enable=all` (422 SC2250 + 91 SC2292 só nos 3 scripts
do round 5). O lint Python novo cobre apenas as classes que o shellcheck
não expressa.

**F3 — O AC "zero falso-positivo sobre históricos" é inalcançável como
escrito e conflita com fail-closed. (A, B, C)** [severidade acordada: ALTA]
Medido (B): 33 `|| true`, 73 `X=$(...)`, 52 `shasum` nos 14 scripts já
landados e aprovados. ⇒ AC reescrito: regras **SEMÂNTICAS** onde
possível (a classe real é "`|| true` seguido de AFIRMAÇÃO de sucesso
sobre estado remoto irreversível" — forma do P1 `OWNER-GA-CUT.sh:721`);
catálogo com split **BLOCKING/ADVISORY** por classe com justificativa
(zero-FP exigido SÓ da lista BLOCKING; ADVISORY publica taxa de disparo
medida); resíduo histórico = cura OU **waiver pinado por sha256 do
CONTEÚDO** (re-arma sozinho quando o arquivo muda), datado, com motivo,
contado em voz alta pelo CI. Waiver por caminho PROIBIDO. Baseline só
pode ENCOLHER (teste falha se crescer).

**F4 — Escopo por nome de arquivo repete a classe
guard-verde-que-não-vê-o-alvo. (A, B, C)** [severidade acordada: ALTA]
`.claude/plans/*/OWNER-*.sh` casa 14-16 arquivos, mas: a classe 3 do
catálogo (`grep|tail -1` em VERDICT) tem **ZERO ocorrências dentro do
glob e 4 fora** (os `run-*.sh` de `PLAN-166/repass-*/`); 2 scripts são
`owner-*` minúsculo; 2 moram em `scripts/local/historical/`; 43 de 95
`.sh` sob `.claude/plans` são **gitignored** (CI nunca os vê);
`glob.glob` do Python pula diretórios ocultos (89 vs 95 do `find`). ⇒
**Descoberta por PROPRIEDADE DE CONTEÚDO** (shebang bash + operações de
cerimônia: gpg/git tag/gh release/sentinel), função de descoberta ÚNICA
compartilhada entre CI e local, lista descoberta IMPRESSA, piso pinado
que falha quando o conjunto encolhe, e **controle positivo obrigatório:
a classe 3 tem de ser ENCONTRADA nos 4 arquivos onde ela está**.

**F5 — Wire de CI: a convergência REAL (2-de-3, B+C) é NÃO tocar
`validate.yml` antes de o PLAN-183 W2 fixar o ramo.** [severidade
acordada: ALTA] Adicionar step ao vivo antes disso FABRICA uma
instância nova do defeito que o 183 gradeia. Sobre O QUE fazer no
lugar, os críticos DIVERGEM — B: job próprio em arquivo novo; C:
diferir TODO wiring de CI até o 183-W2; A: step no `validate.yml`
(vencido 2-de-3). **DECISÃO DO CEO (registrada como decisão, NÃO como
consenso — correção do codex r1):** o gate nasce como job próprio em
arquivo de workflow NOVO e NÃO-templatizado, porque (i) é reversível,
(ii) não cria drift template-vs-vivo (a não-templatização do lint é
decisão registrada — o 183 cobre templates entregues, e este arquivo
não terá template), e (iii) o positive control do censo 171-W0 exige um
executor de CI existente. A via de A (estender o `find` do
`validate.yml`) vira o passo de MIGRAÇÃO pós-183-W2. A objeção de C
fica registrada como risco aceito com dono: se o 183-W2 escolher um
ramo que conflite com o arquivo novo, quem abrir o 183-W2 herda a
reconciliação.
E a perna "pre-commit" **não tem substrato hoje** (`.git/hooks` vazio,
`core.hooksPath` unset — B, C). Decisões concretas (correção do codex
r1 sobre vagueza): **CI é O GATE**; a perna local é git hook CLÁSSICO
opt-in, ENTREGUE pelo W2 como script instalador + doc, declarado
bypassável (`--no-verify`) e NUNCA contado como camada de enforcement.
Escape hatch com forma fixada: `CEO_CEREMONY_LINT_UNLOCK=<sha256 do
arquivo alvo>` + `CEO_CEREMONY_LINT_UNLOCK_REASON` OBRIGATÓRIO, ambos
gravados no audit trail (evento advisory) — provenance-pinned no padrão
ADR-186; unlock sem motivo = bloqueio mantido.

**F6 — A cauda que decide GO/NO-GO é semântica; o lint precisa declarar
o que NÃO cobre. (A, B)** [severidade acordada: ALTA]
A classe DOMINANTE do corpus (~15 achados) é *binding de evidência por
NOME em vez de CONTEÚDO* — não-lintável sintaticamente; rounds 26-30
foram 5 NO-GO consecutivos por defeitos de retomada/estado-remoto
(round25: ~3 de 13 P1 lintáveis, ~23%). As 6 classes nomeadas cobrem
~28 de ~83 achados (~34%), não 40-50%. ⇒ Catálogo em **DUAS seções**:
(A) classes lintáveis → regra executável; (B) invariantes de máquina de
estado (retomada, idempotência, fronteira irreversível remota, binding
por conteúdo) → checklist obrigatório do template W3 + **pauta
permanente do rail que o lint NÃO substitui**. A saída do lint carrega
linha literal de autolimitação ("cobre N classes sintáticas; NÃO cobre
retomada/idempotência/fronteira irreversível"). Sem isso o verde do
lint vira atestado falso usado para encurtar exatamente a revisão que
pegou os 5 NO-GO.

**F7 — Os 9 scripts que operam a chave GPG estão fora de QUALQUER
controle, e o plano não os menciona. (A, B)** [severidade acordada: ALTA]
`~/canhada-labs/OWNER-*-SIGN.sh` + `OWNER-GA-CUT-rc4.sh`: fora de repo
git (sem diff, sem histórico, sem lint, sem CI), todos com `|| true`,
3-5 invocações `gpg` cada. In-scope pela via ratificada de erro de
operador (não adversário local). ⇒ W1 **declara a fronteira por
escrito**: ou os scripts de assinatura entram no repo em diretório
dedicado, ou o catálogo registra que a família de maior privilégio está
fora do alcance do instrumento — e a claim de redução de custo é
reduzida na mesma proporção. Silêncio é o pior resultado. (Decisão de
trazer para o repo = Owner; o W1 apresenta as duas rotas.)

**F8 — Os números da tese não são deriváveis do disco; congelar baseline
por comando. (A, B)** [severidade acordada: MÉDIA]
"38 rounds / 31 em scripts": contagem comportamental dá 44 arquivos de
veredito em 6 diretórios (A) / 34 transcripts, 27 no corpus de scripts
(B) — a RAZÃO (~79%) sobrevive, o denominador não. ⇒ baseline do W4
congelada AGORA como contagem derivada de comando citado no plano, com
definição escrita de "round", enquanto os artefatos existem. Corpus da
W1 congelado pelo `SCRIPTS-MANIFEST.sha256` que já existe.

## 2. Single-agent insights KEPT

- **ADR de disciplina de erro ANTES do lint** (A): as duas metades da
  mesma cerimônia usaram disciplinas opostas (`set -uo` vs `set -euo`)
  e AMBAS produziram defeito (rounds 6/7/13/19/25 vs round 28). Sem
  decisão, as regras "`|| true`" e "rc engolido" são incoerentes.
- **Loop de fechamento da revisão como AC do W3, registrado AGORA** (A):
  rounds 12+25 — evidência de revisão de cerimônia em diretório pinado
  independente, FORA do delta manifest da release.
- **Enumeração das garantias da §2b deriva do contrato existente** (A):
  sem lista canônica, "equivalência de garantias" do golden test W3 é
  vacuous gate.
- **Classes novas no catálogo** (A, B — uma cada): tag-baseline usada
  sem verificação + pin declarado-e-nunca-lido (SC2034 pega metade);
  escrita através de symlink no DESTINO (≠ hashing de symlink — a regra
  como enunciada não pegaria o achado que a originou); "cura decorativa"
  (atribuída-e-nunca-lida); exec-bit fora do binding (classe ATIVA —
  reincidiu em S314).
- **Não-templatização do lint para adopters registrada como decisão**
  (A): cerimônia com pinentry/dois-rails é superfície DESTE projeto.

## 3. Single-agent insights REJECTED / DEFERRED

- **Entrada do lint em `_CANONICAL_GUARDS`** (B): DEFERIDO — edita hook
  canônico (cerimônia GPG própria); registrado como candidato para o
  próximo pack canônico, não pré-requisito do W2.
- **Step direto no `validate.yml`** (A): rejeitado nesta ordem — ver F5
  (2-de-3 + risco menor); a via de A vira o passo de MIGRAÇÃO pós-183-W2.

## 4. Plan adjustments (índice — edições no arquivo do plano)

1. §2 W1 reescrita: delta contra contrato + post-mortem 0/27 + duas
   seções + tabela classe→frequência→rounds + corpus congelado + classes
   novas (F1, F6, F8, singles).
2. §2 W2 reescrita na ordem: estender shellcheck + flags cirúrgicas →
   descoberta por conteúdo + controle positivo → lint Python
   (`check-ceremony-script.py` + testes) só para o resíduo; proveniência
   como regra 1; job CI próprio em arquivo novo; CI=gate, pre-commit
   advisory entregue; escape hatch ADR-186-like (F1, F2, F4, F5).
3. §2b/W3 ganha: AC do loop de fechamento + enumeração de garantias
   derivada do contrato (singles A).
4. §4 ACs reescritos: waiver sha256/split BLOCKING-ADVISORY no lugar de
   zero-FP global; baseline W4 derivada por comando (F3, F8).
5. Registro: fronteira dos scripts de assinatura = decisão do Owner com
   as duas rotas apresentadas (F7).

## 5. Round verdict

**PROCEED** (design-coherent após os ajustes acima aplicados ao corpo do
plano). Nenhum VETO; os três ADJUST convergem na mesma direção e os
ajustes cabem no envelope re-orçado (Critic-A: 110-180k/2 sessões na
ordem recomendada). Lembrete de fronteira: PROCEED registra coerência de
desenho — **não autoriza shipping**; a cascata de verificação (V2 Codex
pair-rail + V3 Owner GPG) segue sendo o único gate de verdade.
