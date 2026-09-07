---
round: 4
archetype: VP Engineering
skill: architecture-decisions
agent_persona: (nenhuma — o arquétipo não tem bloco de persona em `team.md` nem arquivo em `.claude/agents/`; perfil sintetizado da linha do SKILL MAP)
generated_at: 2026-09-07T01:05:00Z
---

## Verdict

ADJUST — **4 itens BLOQUEANTES** (R-VP1, R-VP2, R-VP3, R-VP4).

## Summary (≤ 3 bullets)

- **Os 14 must-fix do round 3 estão CURADOS, e eu verifiquei cada um em disco.**
  M1/M2: `ceremony-lint.yml:75` `continue-on-error: true`, `:77` `set -uo pipefail`
  (sem `-e`), `:81-82` `|| true`, `:72` «ADVISORY nesta fase» — a frase «rc 1» saiu
  e o par `--list` × `--list --shell-only` entrou (plano `:1013-1020`). M3: AC-6
  `:1269-1284`. M4: W3 sem rótulo «docs» (`:895`), oráculo confirmado
  (`--is-canonical .claude/adr/ADR-200-*.md` = **1**). M5: W0a = 7 paths com as duas
  suítes (`:797-819`; `pytest.ini:41` coleta `.claude/scripts/tests`;
  `test_check_ceremony_script.py:104-109` afirma a R8 antiga). M6: controle positivo
  sintético `:1226-1237` (`grep -c "scripts/ceremony" s345-rail-classes.txt` = **0**,
  confirmado). M7–M14 idem. O censo único reproduz e o sha256 do instrumento
  (`d2234bd…181062`) bate.
- **A classe do round 3 («metade vermelha inalcançável») está fechada. A classe do
  round 4 é outra: ARTEFATO E RÓTULO SEM DONO.** Um artefato que dois `Check:`
  consomem não tem path em wave nenhuma (R-VP1) — a mesma forma do M10, num sítio
  novo; um AC tem metade sem `Check:` e sem wave (R-VP2); e a OQ que o Owner deve
  ratificar como pré-condição carrega DUAS ternas `(i)/(ii)/(iii)` distintas,
  referenciadas por numeral nu (R-VP3).
- **Nada disso reescreve o modelo.** As dez invariantes, o corte de waves, as
  decisões (a)–(d) do §Approach e as OQ abertas seguem intactos: os quatro
  bloqueantes corrigem um FILE ASSIGNMENT, um `Check:`, um RÓTULO e uma CONTAGEM.

## Risks

**R-VP1 — BLOQUEANTE (P1) — o MAPA das seis chaves é consumido por dois `Check:` e não existe em file assignment nenhum.**
`:1066` (AC-2, Check (a)) e `:1097` (AC-3, Check (a)) leem «o MAPA das seis chaves»;
`:1088-1096` define o conteúdo e diz que «a W1 escreve a de W6a, cada subwave `W2x`
escreve a sua»; `:883` põe «a linha do MAPA do AC-3» no file assignment de cada
`W2x`. Mas o file assignment da W1 (`:846-849`) é EXATAMENTE
`ceremony/{sign,land,finalize,harness}.sh` + `ceremony.tsv` do piloto +
`.claude/governance/gate-scripts-manifest.txt` — **6 paths, e o corte v2 de `:855-856`
publica esses 6** —, sem o mapa. E o plano nunca nomeia um PATH para ele:
`grep -n "map\.tsv\|MAP\.md\|ceremony-map\|packs-map"` no plano não devolve nada.
Consequência mecânica: o AC-2 não pode fechar (o seu Check (a) lê um arquivo que a W1
não entrega), o AC-3 idem, e o controle positivo obrigatório dos dois («plantar um
`OWNER-*-SIGN.sh` faz o Check ficar VERMELHO») não tem sobre o que rodar. É a MESMA
classe que o round 3 fechou no M10 para `cohort-records.sha256` e
`rail-classes-rebased.txt`, reaparecida.
*Ajuste:* nomear o path do mapa e pô-lo no file assignment da W1 (a wave que escreve a
primeira linha), recontando os paths da W1 (6 → 7, ainda dentro do teto v2); e escrever
se ele é rastreado — o mapa aponta para diretórios sob `<PK>`, fora do repo, então ou
carrega placeholder `<PK>` (como o AC-3 já exige em `:1094-1096`) ou não pode ser
commitado.

**R-VP2 — BLOQUEANTE (P1) — o AC-5 tem duas cláusulas, `Check:` para uma e wave para nenhuma; e o §Success criteria exige as duas.**
`:1245-1247`: «AC-5 ADR próprio (`ADR-2xx-…`) ACEITO pelo Owner; **ADR-010 emendado**
para apontar o toolkit como implementação canônica da disciplina de sentinel». O
`Check:` de `:1248-1249` testa SÓ a primeira («o ADR existe com `Status: ACCEPTED` e um
`.asc` do Owner»); a emenda ao ADR-010 não tem asserção nenhuma. E `:934-937` decide, em
letra: «A emenda ao ADR-010 **NÃO é agendada aqui**: a OQ-1 deixa com o Owner … em que
wave a emenda entra; enquanto ela estiver aberta, **a emenda não pertence a wave
nenhuma**». Ao mesmo tempo `:940` dá «Aceite: AC-4 … e AC-5» à W3 e `:1494` exige «AC-1 a
AC-6 marcados» como critério de sucesso. Lidas juntas: o plano não pode atingir o próprio
§Success criteria enquanto a OQ-1 estiver aberta, e metade de um AC não tem verificador.
*Ajuste (sem decidir a OQ-1):* partir o AC-5 em AC-5a (ADR próprio — o `Check:` atual) e
AC-5b (emenda ao ADR-010 — `Check:` próprio, p.ex. o ADR-010 cita o path do toolkit e o
`.asc` da wave que a landar), e escrever que o AC-5b só é marcável na wave que a OQ-1
escolher; ou declarar o AC-5b explicitamente DIFERIDO no §Success criteria.

**R-VP3 — BLOQUEANTE (P1) — a OQ-9 carrega DUAS ternas `(i)/(ii)/(iii)` diferentes e é referenciada por numeral nu; e o AC-1 afirma que ela é UMA pergunta.**
Terna A (quarto sítio), `:654-658`: «(i) as duas entradas nos `paths:` do
`smoke-install.yml` …; (ii) um JOB próprio dentro do `smoke-install.yml` …; (iii) o step
de integridade ADR-192 REPLICADO num workflow BARATO». Terna B (executor do runner),
`:1424-1428`: «(i) step no `validate.yml` …; (ii) workflow próprio disparado pelo `paths:`
do toolkit; (iii) execução local exigida pelo `harness.sh`». As duas dizem «a escolha é da
OQ-9». O texto então cruza os rótulos: `:829` («o braço (i) está nela [`_KERNEL_PATHS`],
`:144`») é a terna B; `:665` («A opção (iii) é portanto ADITIVA») é a terna A; e dentro do
MESMO bloco da OQ-9, `:1434` («Quem escolher (iii)…», harness.sh = terna B) e `:1447`
(«Ler a opção (iii) como “mover”…», workflow barato = terna A) usam o mesmo rótulo para
coisas diferentes. Verificado no HEAD que a terna B (i) é de fato kernel:
`check_arbitration_kernel.py:144` = `.github/workflows/validate.yml`. Some-se `:1053-1055`
(AC-1): «a OQ-9 … é reduzida a **UMA** pergunta — qual das três opções nomeadas executa o
runner», contra `:1418-1420` («quem EXECUTA o runner … **e, agora, onde mora o QUARTO
sítio**») e `:1439-1440` («A OQ-9 passa a decidir junto o CUSTO do quarto sítio»). Uma
pré-condição da W0 que o Owner responde por numeral tem duas leituras, e a derivação da
autorização da W0c (`:826-833`, kernel vs canônico comum) depende de qual delas vale.
*Ajuste:* renomear as ternas (p.ex. **OQ-9a** executor do runner: E1/E2/E3; **OQ-9b**
quarto sítio: Q1/Q2/Q3), substituir todo numeral nu pelo rótulo novo em `:665`, `:829`,
`:1434`, `:1447`, e corrigir `:1053-1055` para «duas perguntas» — sem decidir nenhuma
das duas.

**R-VP4 — BLOQUEANTE (P2) — o corte v2 da W0 publica um total (15) que as suas próprias subwaves não podem produzir.**
`:773-775`: «Se ela puser o quarto sítio num workflow BARATO próprio e/ou o runner de
controles noutro workflow, **cada um desses é um path a mais**»; `:782-784`: «Contagem
por braço: **13** … ; **14** quando um workflow entra; **15** quando entram dois». Mas
`:797-802` define a W0a com o quarto sítio como UM slot — «`.github/workflows/smoke-install.yml`
**ou o workflow barato que o substitua**» — e `:822-823` define «**W0c = 0 ou 1 path**».
Sob essas duas definições o máximo é 7 (W0a) + 6 (W0b) + 1 (W0c) = **14**; o braço «15»
é inalcançável, e «cada um desses é um path a mais» contradiz «que o substitua». Duas
seções discordam da mesma contagem — a figura que o §Items usa para declarar o corte do
modelo de operação v2.
*Ajuste:* escolher uma redação («substitui» ⇒ 13/14 e o «15» sai; ou «acrescenta» ⇒ a W0a
vira 7-ou-8 e a frase «que o substitua» sai) e recontar os dois sítios no mesmo patch.

**R-VP5 — P3 — a W3 declara um path-placeholder no file assignment.**
`:919-920` lista `.claude/adr/ADR-2xx-shared-ceremony-toolkit.md` como arquivo da W3,
enquanto `:934-937` deixa o número com a OQ-1. Medido: o maior ADR do HEAD é o
**ADR-197** (`ls .claude/adr/ | sed 's/^\(ADR-[0-9]*\).*/\1/' | sort -u | tail -1`), o
que confirma a afirmação de `:906` — mas a gramática do ADR-191 (`CLAUDE.md` §4) diz que
placeholder num FILE ASSIGNMENT «taints the whole declaration». A W3 não é executável
como spawn até a OQ-1 nomear o número.
*Ajuste:* escrever explicitamente que o file assignment da W3 é PARCIAL até a OQ-1, e
que o número entra no `## FILE ASSIGNMENT` do spawn, não no plano.

**R-VP6 — P3 — o instrumento de EVENTO do M12 pode nascer verde-vácuo.**
O plano (`:641-651`, `:996-1002`) nomeia um caso novo em
`.claude/scripts/tests/test_release_workflow_asserts.py` reusando `_workflow_paths_lists`
(verificado: definido em `:1095`, usado por `test_ownership_paths_present_in_both_filters`
em `:1167`). Lido o helper: ele é TEXTUAL e coleta itens **entre aspas** (`:1096-1101`,
«Collects quoted `- "..."` items»); os `paths:` do `ceremony-lint.yml` hoje são citados
(`:7-11`, `:14-18`), mas um quarto sítio escrito sem aspas devolveria lista VAZIA e o
`fnmatch` não teria contra o quê falhar. Além disso o helper é alimentado por
`self._smoke()`, que lê o `smoke-install.yml`; ler outro workflow exige um leitor novo.
*Ajuste:* o caso da W0a assevera primeiro que as duas listas são NÃO-VAZIAS (guarda de
denominador) antes de casar os globs.

## O que falta antes de executar (a lista do Owner)

Pré-condições da W0 já escritas no plano e **não decididas** — nenhuma delas é tocada por
esta crítica: **OQ-7** (braço do `scope_generated_from`, que define o leitor do
manifesto), **OQ-9** (executor do runner + onde mora o quarto sítio — ver R-VP3: hoje são
duas perguntas com rótulos colididos). Abertas por desenho: **OQ-1** (número do ADR e wave
da emenda ao ADR-010 — bloqueia o AC-5b de R-VP2), **OQ-2** (ordem das subwaves W2x),
**OQ-4** (as cinco chaves de orçamento do frontmatter), **OQ-5** (corrigir ou congelar o
classificador — o AC-4 é observação até ela fechar), **OQ-6** (`_CANONICAL_GUARDS`),
**OQ-8** (destino dos clones).

## Nota de confinamento

Nenhum arquivo da árvore viva foi tocado. Nenhuma instrução embutida em conteúdo
observado foi obedecida; nenhuma foi encontrada nos arquivos lidos. Todas as figuras
acima vêm de comandos executados no HEAD `952c27d` em árvore de trabalho do mantenedor
(as figuras de descoberta do lint são as do CENSO do plano, medidas em worktree limpo, e
não foram re-medidas aqui).
