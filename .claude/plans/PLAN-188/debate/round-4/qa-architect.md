---
round: 4
archetype: Principal QA Architect
skill: testing-strategy (`.claude/skills/core/testing-strategy/SKILL.md`, sha256 d5d9598c…0285)
agent_persona: (crítico de verificabilidade — controles, desenho de experimento, estatística do plano)
generated_at: 2026-09-07T01:05:00Z
---

## Verdict

**ADJUST — 3 itens BLOQUEANTES.**

Base de todas as medições abaixo: HEAD `952c27d`, árvore VIVA do mantenedor
(`<ROOT>`), comandos citados ao lado de cada número.

## Summary (≤ 3 bullets)

- **Os 14 must-fix do round 3 estão FECHADOS em disco.** Verifiquei um a um:
  M1 (`:155-166` — a razão do filtro passou a ser o ruído `SC1071`, e o
  `ceremony-lint.yml:75` `continue-on-error` + `:81-82` `|| true` estão citados
  como refutação), M2 (`:1015-1022` — a cláusula do job `shellcheck-ceremony`
  saiu da lista de FALHA), M3 (`:1269-1305` — o AC-6 diz ONDE o vermelho (ii) é
  observável e a que custo), M4 (`:899-913` — a W3 é canônica; oráculo mediu
  `.claude/adr/ADR-200-x.md	1`), M5 (`:812-836` — W0a = 7 paths com as duas
  suítes), M6 (`:1219-1240` — controle POSITIVO sintético do classificador),
  M7 (`:614-627`), M8 (`:961-978` — 7 ids), M9 (`:942-948`), M10 (`:925-933`),
  M11 (`:1443-1456`), M12 (`:628-644`), M13 (`:1005-1013`), M14 (`:301-345`).
- **O censo único reproduz na minha árvore, figura a figura:**
  `python3 .claude/scripts/check-ceremony-script.py --json` devolve
  `discovered_tracked` **109**, 108 sob `.claude/plans/**`, 42 arquivos
  rastreados com ≥1 BLOCKING e **42** deles waivados, R8 **28/28**,
  `floor` 41, `waivers_active` 44, `blocking_unwaived` 0; `_KERNEL_PATHS` = 110
  e `.github/workflows/validate.yml` está nela (`:144`); manifesto ADR-192 = 9;
  48 `OWNER-*(SIGN|LAND)*.sh` com 33 citando `sentinel-signers`; sha256 do
  instrumento bate com o pin do `:1123`; `grep -c "scripts/ceremony"` na saída
  congelada = **0**.
- **O que sobra é a MESMA classe que o round 3 disse ter fechado, em três
  sítios novos: um critério cujo VERDE não prova a propriedade.** Um AC que
  nomeia duas bases diferentes para a mesma comparação; um instrumento de
  gatilho cujo casador é mais permissivo que o motor que ele modela; e três
  controles positivos sem lugar declarado, cujo cumprimento literal deixa o
  gate do repo vermelho (ou paga a rota de escape que o plano condena).

## Risks

**QA-1 — BLOQUEANTE (P1) — o AC-4 nomeia DUAS bases para a mesma comparação, e
o próprio plano prova que elas têm os mesmos números.**
O cabeçalho do AC-4 (`:1114-1116`) fixa a comparação «contra a base congelada de
23,1 % (`.claude/plans/PLAN-188/s345-rail-classes.txt`)»; o passo (2) do
`Check:` do MESMO AC (`:1200-1203`) manda comparar contra
`.claude/plans/PLAN-188/rail-classes-rebased.txt`, «**nunca** contra
`s345-rail-classes.txt`». Duas metades do mesmo critério discordam sobre o
denominador do veredito — e a `Meta: < 5 %` do `:1243` foi escrita contra a
base que o `Check:` proíbe. Pior: o plano exige, em `:1160-1164`, que a base
re-medida «bata classe a classe» com a congelada, e mede em `:1224` que o
corpus congelado tem **0** ocorrências de `scripts/ceremony` — isto é, sob as
próprias regras do plano os dois arquivos têm figuras IDÊNTICAS. A distinção
«nunca contra s345» é vazia no numerador que interessa, e o leitor não
consegue dizer contra o quê `≥ 5 %` reprova.
*Ajuste:* escrever no cabeçalho a mesma base do `Check:` e declarar, em UMA
linha, que a re-medição da base é um CONTROLE de que a mudança foi só de regra
(igualdade esperada), não um denominador novo — a proteção contra a migração de
classe age no NUMERADOR da coorte futura, não na base.

**QA-2 — BLOQUEANTE (P2 por severidade, bloqueante por classe) — o instrumento
dos controles de EVENTO casa com `fnmatch`, que é mais permissivo que o filtro
de `paths:` do GitHub: o verde não prova o gatilho.**
`:1000-1004` e `:635-639` prescrevem um caso novo em
`.claude/scripts/tests/test_release_workflow_asserts.py` que «casa por
`fnmatch` cada path concreto contra os globs declarados», «na mesma forma do
`test_ownership_paths_present_in_both_filters` (`:1167-1174`)». Medido:
`grep -n fnmatch .claude/scripts/tests/test_release_workflow_asserts.py` não
devolve NADA — o precedente citado usa igualdade exata (`assertIn(required,
pr)`, `:1167-1174`), não casamento de glob. E o `fnmatch` do Python traduz `*`
para `.*`, que atravessa `/`, enquanto o filtro de `paths:` do GitHub não
atravessa. Contra-exemplo dentro do layout que a própria W0b entrega
(`controls/…`, `:820-822`): o glob `.claude/scripts/ceremony/*` faz o controle
passar para `.claude/scripts/ceremony/controls/run.sh` e o PR real **não**
dispara. O vermelho declarado («remover uma das entradas novas faz o caso
reprovar», `:1004`) continua alcançável — o defeito é o VERDE.
*Ajuste:* ou o caso assere a STRING do glob contra uma lista declarada (o
precedente da casa), ou o casador implementa a semântica do GitHub (`*` não
cruza `/`, `**` cruza) e ganha um caso NEGATIVO — um path fora do toolkit que
NÃO pode casar. Sem isso o controle é decorativo exatamente no ponto que a
`Falha` do AC-1 promete cobrir.

**QA-3 — BLOQUEANTE (P2) — os três controles positivos do lint não têm lugar
declarado; cumpridos ao pé da letra, dois deles deixam o gate do repo
VERMELHO — e a única saída é a rota de escape que o plano condena.**
`:249-252` exige «(b) um script **do toolkit** com `|| true` numa linha de
`gpg` tem de REPROVAR na R2» e «(c) um script **do toolkit** com exec-bit no
índice tem de REPROVAR na R8» (repetidos no AC-1, `:986-989`). Com o predicado
novo (decisão (a): todo `.sh`/`.py` sob o toolkit root é descoberto
INCONDICIONALMENTE), um arquivo assim RASTREADO no endereço real produz achado
BLOCKING e entra em `blocking_live` (`check-ceremony-script.py:329-330`,
`if n_block and not waived and is_tracked`) — o job de `ceremony-lint.yml:37-40`
é fail-closed e sai com o rc do checador. Hoje `blocking_unwaived` = **0** em
109 rastreados: a W0 o tornaria positivo, e a única cura seria acrescentar uma
linha ao `ceremony-lint-waivers.json` — as 44 isenções que o §Approach
(`:283-299`) existe para denunciar. A tabela «QUEM escreve o arquivo que cada
controle falsifica» (`:748-763`) resolve isso para as invariantes 1/3/4/5/10
(«o ESCRITOR é sempre a fixture do próprio controle») e **não cobre** (a)/(b)/(c).
O precedente da casa está no arquivo que a W0a já adota:
`.claude/scripts/tests/test_check_ceremony_script.py:35-44` planta o fixture em
árvore descartável e roda `--root <tmp> --floor 1`.
*Ajuste:* escrever que (b) e (c) rodam em árvore DESCARTÁVEL (`--root <tmp>`),
e que só (a) — o arquivo sem token de cerimônia — é arquivo shipado; e, no
mesmo lugar, completar os paths da W0b, que hoje aparecem sem raiz
(`controls/inv1_rail_set.sh`, `:820-822`) enquanto a W0a soletra o path inteiro.

**QA-4 — P3 — a `Falha` do AC-1 ainda promete um EVENTO que nenhum instrumento
do plano observa.**
`:1015-1018` lista como falha «um PR do toolkit que não dispare o
`ceremony-lint.yml`», e o instrumento nomeado (`:1002-1004`) declara-se
limitado ao PREDICADO. É o resíduo da classe que o M2 fechou para o job
`shellcheck-ceremony`: o critério sobrevive na forma de evento, o observador é
outro. *Ajuste:* redigir a falha como o predicado (glob × path) e escrever, em
meia linha, que o evento é conferido UMA vez, no primeiro PR real da W0a.

**QA-5 — P3 — o `N/N` é derivado pelo próprio sujeito que ele conta.**
`:975-979` manda o runner imprimir «`N/N` derivado da lista de ids que ele mesmo
enumera». Um runner que perca o `inv3b` imprime `6/6` e passa; a lição de casa
(«`EXPECTED_*` declarado à mão envelhece», `CLAUDE.md` §5) corta dos dois lados.
*Ajuste:* o conjunto de ids AUTORITATIVO é o do AC (`inv1, inv3a, inv3b, inv3c,
inv4, inv5, inv10`, `:973-975`); o runner reprova se o conjunto que ele executou
diferir dele — comparação de CONJUNTOS, nos dois sentidos, como a invariante 2
já faz com o trailer.

**QA-6 — P3 — o chaveiro GPG descartável do controle da invariante 10 é custo
sem dono.**
`:763` e `:766-769` registram que a fixture da inv. 10 «precisa de um chaveiro
GPG descartável que nenhum runner semeia hoje — custo que a OQ-9 passa a
cobrir», e `:1049-1052` repete. Mas a OQ-9, como escrita (`:1415-1465`), decide
QUEM executa o runner e ONDE mora o quarto sítio; semear chaveiro é ENTREGA,
não escolha de executor — e ela é necessária nos três braços. *Ajuste:* nomear
a semeadura como item do file assignment da W0b (dentro de
`controls/inv10_signer.sh`), independente da OQ-9.

## O que falta antes de executar (OQ que o Owner ratifica)

Nada a acrescentar às que já estão abertas — e não decido nenhuma:
**OQ-1** (número do `ADR-2xx` e a wave da emenda ao ADR-010; do braço depende a
W3 ser canônica ou livre, `:899-913`), **OQ-2** (ordem das subwaves `W2a..W2e`),
**OQ-4** (as cinco chaves de orçamento), **OQ-5** (corrigir ou congelar o
classificador — pré-condição para o AC-4 virar gate), **OQ-6** (entrada em
`_CANONICAL_GUARDS`), **OQ-8** (destino dos clones), mais as duas promovidas a
PRÉ-CONDIÇÃO da W0: **OQ-7** (o braço do `scope_generated_from`, que define o
leitor) e **OQ-9** (executor do runner + endereço do quarto sítio). Registro,
como QA e sem numerar opção: das três alternativas da OQ-9, só a (i) e a (ii)
dão executor aos SETE vermelhos antes da W1 — o `harness.sh` da (iii) é entrega
da W1 (`:846-849`), e o plano já escreve essa consequência dentro da opção
(`:1443-1456`).

## Resposta ao consenso do round 3

Concordo com o veredito e com os 14 must-fix; todos foram absorvidos e
verificados acima. Três observações de QA sobre a forma como foram absorvidos:

1. **M6 foi absorvido melhor do que o consenso pediu** — o par de blocos
   sintéticos POSITIVO/NEGATIVO (`:1226-1240`), com o `check_contamination.py`
   como negativo que tem de continuar `product`, é exatamente «controle que
   reproduz o MECANISMO». Mantenha o negativo: sem ele, uma raiz nova
   larga demais (`.claude/scripts/**`) passaria o positivo.
2. **M10 fechou o arquivo, não o experimento.** A coorte pinada em
   `cohort-records.sha256` e o critério de morte «≥ 100 blocos ⇒ NÃO
   CONCLUSIVO» (`:1241-1243`) são bons; o que continua sem célula enumerada é
   o desfecho «a coorte tem 3 pacotes mas um deles não gerou registro nenhum»
   — pelo limite (iv) do próprio instrumento (`:1334-1337`) esse pacote some de
   `per_pack` e a coorte encolhe em silêncio. Uma linha basta: coorte com
   pacote de zero registros ⇒ NÃO CONCLUSIVO, não amostra menor.
3. **M14 está correto e ficou completo** — reproduzi as duas árvores: 122/109
   descobertos, 55 arquivos com BLOCKING dos quais 42 rastreados e os 42
   waivados, `blocking_unwaived` 0 pelos DOIS mecanismos que o plano separa
   (`waived` e `is_tracked`, `:329-330`).

Nenhum arquivo da árvore viva foi tocado por esta crítica.
