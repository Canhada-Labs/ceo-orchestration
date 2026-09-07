---
round: 3
archetype: Principal QA Architect
skill: testing-strategy
agent_persona: (nenhuma — arquétipo sem bloco em `team.md` nem arquivo em `.claude/agents/`; perfil sintetizado da linha do SKILL MAP)
generated_at: 2026-09-07T00:20:00Z
---

## Verdict

ADJUST — **3 bloqueantes** (Q1, Q2, Q3). Zero deles pede arquitetura nova: os
três são a METADE VERMELHA de um Check que, do jeito escrito, não pode acender.

## Summary (≤ 3 bullets)

- **Onde é forte, e verificado por mim em disco:** os números do plano batem.
  Árvore viva = `122` descobertos / `121` sob `.claude/plans/**` / `55` com
  BLOCKING (`python3 .claude/scripts/check-ceremony-script.py --json`,
  exatamente a tripla que o §Riscos publica); `discovered_tracked` = `109`;
  R8 = `28`, todos `28` waivados e rastreados; `waivers_active` = `44` e as 44
  entradas do JSON têm sha único + `reason` + `date` (as duas contagens que o
  plano trata como iguais SÃO iguais); `_KERNEL_PATHS` = **110** e não casa
  nenhum dos dois arquivos do lint; manifesto ADR-192 = **9**; `48`
  `OWNER-*(SIGN|LAND)*.sh` com `41`×`100644` / `7`×`100755`; `33` deles leem
  `sentinel-signers`; oráculo `--is-canonical` = 0 para o checador, para o JSON
  de waivers e para `sentinel-signers.txt`, e = 1 para os três workflows
  citados; `shasum -a 256` de `measure-rail-classes-v2.py` =
  `d2234bdf…b181062`, idêntico ao pin do AC-4, e `s345-rail-classes.txt` traz
  `ceremony 122 23,1 %` como escrito. **Nenhum número deste plano é digitado.**
- **Onde é fraco:** três controles declarados não têm metade vermelha alcançável
  — um cita um rc que o step não pode devolver (Q1), um depende de um evento que
  nenhum workflow escuta (Q2), e um é verde por construção sobre o corpus
  congelado (Q3). É a MESMA classe que o round 2 curou no D1; ela reapareceu em
  outros três sítios.
- **Aritmética de controles:** o AC-1 promete «≥ 1 controle VERMELHO por
  invariante» e depois fecha em `5/5` — mas a invariante 3 sozinha exige TRÊS
  vermelhos e a invariante 9 não tem nenhum (Q4, Q5).

## Risks

**Q1 — P1 — «o passo devolve rc 1» é FALSO no HEAD; a metade vermelha do
quarto achado do AC-1 não existe em CI.**
O plano escreve, em `.claude/plans/PLAN-188-shared-ceremony-toolkit.md:121-127`,
que um `.py` no conjunto do `--list` «sai como `SC1071` e **o passo devolve rc
1**», e o AC-1 (`:850-852`) põe «o job `shellcheck-ceremony` recebendo um `.py`
no conjunto do `--list`» na lista de FALHA. Medido no HEAD, esse step não pode
devolver rc 1 por dois motivos somados: `.github/workflows/ceremony-lint.yml:75`
é `continue-on-error: true` e `:81-82` termina a invocação com
`> shellcheck-ceremony.txt 2>&1 || true`; o `run:` abre com `set -uo pipefail`
(sem `-e`) e o último comando do step é o redirecionamento para
`$GITHUB_STEP_SUMMARY` (`:84-89`). O comentário `:72` do próprio workflow diz
«ADVISORY nesta fase». Consequência de QA: o defeito que o plano quer prevenir
(um `.py` entrando no conjunto do shellcheck) **não fica vermelho em lugar
nenhum** — some num `.txt` de sumário. O parágrafo se contradiz sozinho ao
chamar o mesmo artefato de «relatório advisory» duas linhas abaixo.
*Cura mínima (texto, não arquitetura):* trocar «o passo devolve rc 1» por «o
comando `shellcheck` sai rc 1 e o step o engole (`|| true` + `continue-on-error`)
— o sintoma é ruído permanente no relatório, não um job vermelho», e reescrever
o quarto item de FALHA do AC-1 como um controle EXECUTÁVEL: rodar
`shellcheck -S warning $(check-ceremony-script.py --list)` fora do workflow e
exigir rc 0. Um critério de falha que só um humano lendo um sumário pode
observar não é gate.

**Q2 — P1 — o controle vermelho (ii) do AC-6 não é alcançável pelo evento que
o dispara.**
O AC-6 (`:1059-1063`) exige ver DOIS vermelhos, e o (ii) é «uma entrada é
acrescentada ao `ceremony-lint-waivers.json` sem bump do manifesto». Medido: a
verificação `shasum -c` do manifesto ADR-192 mora em QUATRO workflows —
`.github/workflows/release.yml:58`, `npm-publish.yml:139`,
`ownership-nightly.yml:62`, `smoke-install.yml:358` (e o próprio
`ADR-192:49-53` diz «4 superfícies»). Nenhum dos quatro é disparado por uma
mudança nesse JSON: os `paths:` de `smoke-install.yml` (linhas 5-30) não têm
**nenhuma** entrada `.claude/**`, e release/npm-publish são gatilhos de tag e de
publish. Enquanto isso, o `ceremony-lint.yml` — que É disparado pelo JSON
(`:10`, `:17`) — não verifica o manifesto. Ou seja: um PR que só faz o append
de waiver passa por CI verde. E o item de W0 que deveria fechar isso pede «as
DUAS entradas nos dois `paths:` do `smoke-install.yml`» (`:656`) — duas, para o
toolkit; os dois arquivos do lint que o AC-6 absorve não estão nomeadas nelas.
*Cura mínima:* o «quarto sítio» passa a ser QUATRO entradas por gatilho
(`.claude/scripts/ceremony/**`, `.claude/scripts/check-ceremony-script.py`,
`.claude/scripts/ceremony-lint-waivers.json` e
`.claude/governance/gate-scripts-manifest.txt`), OU o step de `shasum -c` entra
no `ceremony-lint.yml`, que já escuta os dois. Sem isso o AC-6 shipa com um dos
seus dois vermelhos obrigatórios impossível de ver, e o §Riscos passa a dever
mais do que «detecção post-hoc»: é **não-detecção** no PR que importa.

**Q3 — P1 — o único controle do AC-4 para a MUDANÇA DE REGRA do classificador é
verde por construção.**
O AC-4 (`:988-992`) declara: «o controle de que a mudança foi só de CLI é a base
re-medida bater classe a classe com a saída congelada em
`s345-rail-classes.txt`». Mas o MESMO patch muda as REGRAS: `:1028-1030` manda
acrescentar `.claude/scripts/ceremony/**` às raízes de `ceremony`. Verificado no
instrumento, `measure-rail-classes-v2.py:52-64` (`classify_path`) resolve
`.claude/scripts/ceremony/read_manifest.py` como `product` via
`PRODUCT_RE` (`:40`, `\.claude/scripts/[\w\-/]+\.py`) — o plano acerta o
diagnóstico. O problema é o controle: o corpus congelado é de 04→05/09 e o
diretório do toolkit **não existe**, logo ZERO bloco do corpus cita esse
prefixo, e a igualdade classe-a-classe se mantém quer a raiz nova esteja certa,
quer esteja com um typo (`ceremonies/`, `ceremony/**` mal ancorado, ordem
errada em relação a `TEST_RE`/`CEREMONY_RE`). O controle fica verde com a
mudança de regra REMOVIDA — o red flag exato que o D1 do round 2 já custou uma
rodada.
*Cura mínima:* um controle POSITIVO sintético no mesmo patch — um bloco de
achado citando `.claude/scripts/ceremony/read_manifest.py` classifica `product`
sob as regras antigas e `ceremony` sob as novas, com as duas saídas na
EVIDENCE; e um NEGATIVO — um bloco citando `.claude/scripts/check_contamination.py`
continua `product`. A igualdade classe-a-classe fica onde está, medindo o que
ela de fato mede (a mudança de CLI).

**Q4 — P2 — `5/5` é uma contagem DIGITADA, e na granularidade errada.**
O Check da W0 (`:822-823`) diz «o runner de controles imprime **5/5**
VERMELHO-antes / VERDE-depois», e os Itens (`:644-649`) confirmam a origem do
5: são cinco ARQUIVOS de controle (`inv1_…`, `inv3_…`, `inv4_…`, `inv5_…`,
`inv10_…`). Só que a invariante 3 (`:465-476`) exige **TRÊS** controles
vermelhos nomeados — (i) material sem o argumento, (ii) sentinela de conteúdo +
variável de ambiente do rascunho, (iii) material MARCADO fora do self-test — e
o (ii)+(iii) são justamente os que provam que os dois canais do rascunho estão
MORTOS. Um runner que agrega por ARQUIVO imprime `5/5` mesmo com dois dos três
ausentes. O piso real da W0 é **7** vermelhos, não 5.
*Cura:* o runner imprime `N/N` DERIVADO da enumeração (um id por controle,
`inv3a/inv3b/inv3c`), e o AC cita o id, nunca o total digitado — é a regra
«EVIDENCE/DESIGN são GERADOS, nunca digitados» aplicada ao próprio aceite.

**Q5 — P2 — o cabeçalho do AC-1 e os seus dois Checks discordam sobre a
invariante 9.**
`:815` promete «≥ 1 controle VERMELHO por invariante». Os Checks enumeram
`{1,3,4,5,10}` na W0 (`:817`) e `{2,6,7,8}` + as duas metades de escrita de 4 e
5 na W1 (`:853-859`): a invariante **9** não aparece em nenhum dos dois. Ela é
declarada ADVISORY em `:496-505` («INFORMA e nunca recusa»), então a ausência
está CERTA — o que está errado é o cabeçalho, que promete o que o plano
deliberadamente não entrega. Um leitor que audite o AC-1 pelo cabeçalho conta 10
e acha 9.
*Cura:* «≥ 1 controle VERMELHO por invariante BLOQUEANTE (a 9 é ADVISORY por
decisão registrada em §Approach)».

**Q6 — P3 — o censo único descreve o mecanismo da exclusão pelo lado errado.**
O §Riscos (`:269-273`) conclui «sem sobra para "arquivos não rastreados", que
num checkout limpo não existem», atribuindo a ausência à `gitignore` do
worktree. O mecanismo real de gate é outro e vale nas DUAS árvores:
`check-ceremony-script.py:329` só soma `blocking_live` quando
`n_block and not waived and is_tracked`. Medido por mim na árvore viva: `55`
arquivos com BLOCKING, `42` waivados, **13 não-waivados** — e ainda assim
`blocking_unwaived: 0`, porque os 13 são untracked e o `:329` os descarta.
`blocking_unwaived` também conta ACHADOS, não arquivos (`:322`, `:330`), então
um leitor que derive «42 de 42» a partir do `0` erra em qualquer árvore de
trabalho. Não muda decisão nenhuma; muda o que a evidência do pacote precisa
imprimir.
*Cura:* o censo cita a derivação («arquivos com ≥1 BLOCKING» e «desses,
`waived: true`» contados a partir de `files[]` do `--json`) e nomeia `:329` como
a razão de `blocking_unwaived` ser 0 nas duas árvores.

## O que falta antes de executar (OQ que o Owner ratifica)

- **OQ-7** (braço do `scope_generated_from`) e **OQ-9** (executor do runner de
  controles + chaveiro GPG descartável da inv. 10) já estão promovidas a
  PRÉ-CONDIÇÃO da W0 no texto (`:346-353`, `:881-884`) — corretamente: as duas
  mudam ARTEFATO da W0, não só ordem de trabalho. Sem elas o AC-1 não fecha.
- **OQ-5** (corrigir × congelar o classificador) continua sendo o que decide se
  o AC-4 é gate ou observação; a Q3 acima é independente da escolha — nos dois
  braços o controle da mudança de regra precisa existir.
- **Recomendação (não decisão):** OQ-9 no braço «workflow barato próprio», não
  no `smoke-install.yml`. O plano já mediu que aquele job custa ~1 h para rodar
  um `shasum -c` de segundos (`:657-658`), e a Q2 mostra que o `paths:` dele
  teria de crescer em quatro entradas `.claude/**` que nada têm a ver com
  install/upgrade — acoplamento que a própria casa já pagou como «gate que
  ninguém roda».

## Resposta ao consenso do round 2

Os cinco D e os itens mantidos foram conferidos por mim em disco e estão
FECHADOS no texto: D1 (predicado por diretório, `.sh` **e** `.py`, controle
positivo refeito para «arquivo SEM token», `:99-132` + `:828-841`), D2 (cinco
classes e a tabela de marca por arquivo, `:145-167`), D3 (o escape por waiver e
a absorção no ADR-192, `:226-296` + `:1050-1058`), D4 (razão do `:192-194`
emendada no mesmo patch, `:169-190`), D5 (executor nomeado como pré-condição,
`:872-884`). K5, K6, K7, K8, K9, K10, K11 idem. **O que o round 3 acrescenta
não é uma sexta classe nova: é a mesma classe do D1 — controle sem metade
vermelha — em três sítios que o round 2 não visitou** (o job do shellcheck, o
evento do ADR-192, e o classificador do AC-4).
