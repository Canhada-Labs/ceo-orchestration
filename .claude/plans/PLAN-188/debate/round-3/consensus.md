---
plan: PLAN-188
round: 3
rounds_synthesized: [round-3]
agents_considered: [Critic-A, Critic-B, Critic-C]
decisions_revised_in_plan:
  - "§Approach decisão do filtro de shell (:150-162) — a JUSTIFICATIVA «o passo devolve rc 1 (medido no HEAD)» é falsa: o step é continue-on-error + `|| true`. A decisão de filtrar fica; a razão passa a ser «ruído SC1071 permanente no relatório advisory»."
  - "§Acceptance criteria AC-1, cláusula Falha (:851) — «o job `shellcheck-ceremony` recebendo um `.py`» sai da lista de FALHA de CI ou ganha um verificador local nomeado; um evento que não pode ficar vermelho não é critério."
  - "§Acceptance criteria AC-6, controle vermelho (ii) (:1059-1063) — o vermelho de append de waiver sem bump precisa de um sítio que o evento DISPARE, ou o AC declara que ele é observado fora de CI."
  - "§Riscos, quarto sítio (:569-571) e §Open questions OQ-9 (:1152-1156) — a suficiência «e só com ele» cai: o `ownership-nightly.yml` já roda o mesmo `shasum -c` em cron sem `paths:`, e a associação do toolkit ao manifesto só chega na W1 (AC-6)."
  - "§Waves W3 (:796-797) — «Gate: docs» contra um ADR que o oráculo responde 1 e um AC-5 que exige `.asc` do Owner: a W3 é canônica ou o ADR sai dela."
  - "§Waves W0a, file assignment (:712-717) — `.claude/scripts/tests/test_check_ceremony_script.py` entra no escopo: a W0a reescreve o predicado de descoberta e o escopo da R8, e o teste do CI ainda afirma a forma ANTIGA."
  - "§Acceptance criteria AC-4 (:1028-1033) — a mudança de REGRA do classificador ganha controle POSITIVO sintético; a igualdade classe-a-classe contra o corpus congelado é verde por construção."
  - "§Acceptance criteria AC-1 Check (W0) (:822-823) — o «5/5» é contagem de ARQUIVOS de controle; a invariante 3 sozinha exige três vermelhos, então o piso é 7."
  - "§Acceptance criteria AC-1, cabeçalho (:815) — «≥ 1 controle VERMELHO por invariante» ganha a exceção escrita da invariante 9 (ADVISORY, :496-505)."
  - "§Acceptance criteria AC-1 (:826-829 × :851) e §Riscos (:269-273) — dois ajustes de precisão: `--list` lista tudo e o filtro é do CONSUMIDOR; a exclusão de não-rastreados é o filtro `is_tracked`, não a `gitignore`."
synthesized_at: 2026-09-07T00:22:00Z
synthesized_by: VP Engineering (synthesizer, anonymized input) for CEO
---

# PLAN-188 — consenso do round 3

Três críticos, três `ADJUST`, 2 + 2 + 3 itens bloqueantes. Nenhum pediu `REJECT`.
Este round é uma checagem de COERÊNCIA INTERNA do texto do plano revisado em
`2a36e5c`; não certifica verdade externa e não autoriza wave nenhuma.
Toda claim abaixo foi re-verificada em disco no HEAD `45877e4` antes de virar
ajuste. **O que os três confirmaram primeiro:** os 15 must-fix do round 2 estão
absorvidos no texto, e o censo único do §Riscos reproduz — os três mediram
independentemente (`discovered_tracked` 109, piso 41, `blocking_unwaived` 0,
44 waivers, 9 membros do manifesto ADR-192, 48 `OWNER-*(SIGN|LAND)*.sh`
com 41×100644 / 7×100755, `_KERNEL_PATHS` = 110, sha256 do instrumento).
O que sobra é uma CLASSE só, repetida em sítios novos: **critério de aceite
cuja metade vermelha não é alcançável pelo evento que deveria dispará-la.**

## Consensus findings (2+ agents flagged)

### C1 — BLOQUEANTE — a justificativa do filtro de shell é falsa no HEAD (Critic-A, Critic-B, Critic-C)

O plano escreve, em `:154`, que um `.py` no conjunto do `--list` faz o passo
`shellcheck-ceremony` «devolve[r] rc 1 (medido no HEAD)» e chama isso de «erro
permanente»; o AC-1 promove o evento a critério de FALHA em `:851`.
Verificado em disco: `.github/workflows/ceremony-lint.yml:75` é
`continue-on-error: true`; `:77` abre com `set -uo pipefail` (sem `-e`);
`:81-82` fecha a invocação do `shellcheck` com `|| true`; e o último comando do
`run:` é o redirecionamento para `$GITHUB_STEP_SUMMARY` (`:84-89`). O comentário
de `:72` declara o passo «ADVISORY nesta fase». **Dois mecanismos independentes
mantêm o step verde: o step não pode ficar vermelho.**

A DECISÃO de filtrar continua certa — um `.py` no `shellcheck` produz `SC1071` e
polui o relatório a cada mudança legítima do toolkit. O que muda é a razão
(ruído permanente no advisory, não rc 1) e o destino da cláusula de FALHA do
AC-1: ou ela sai da lista de CI, ou o plano nomeia o verificador LOCAL que a
torna falsificável. Esta é a mesma classe do D1 do round 2.

### C2 — BLOQUEANTE — o vermelho (ii) do AC-6 não é alcançável pelo evento que o dispara (Critic-B, Critic-C)

O AC-6 (`:1059-1063`) exige DOIS controles vermelhos obrigatórios, e o segundo é
«uma entrada é acrescentada ao `ceremony-lint-waivers.json` sem bump do
manifesto». A verificação do manifesto ADR-192 mora em quatro workflows —
`release.yml:63`, `npm-publish.yml:141`, `ownership-nightly.yml:64`,
`smoke-install.yml:360` (ADR-192:49-53 diz «em 4 superfícies») — e **nenhum
deles é disparado por um PR que toca o JSON de waivers**: o `ceremony-lint.yml`
escuta o JSON (`:10`, `:17`) mas não verifica o manifesto, e os `paths:` do
`smoke-install.yml` não têm entrada `.claude/**`. O vermelho chega em
release/publish/nightly, não no PR — e o custo operacional é o outro lado da
mesma moeda: um append de waiver, hoje rotina, passa a ser cerimônia assinada
que pode travar um release. O AC precisa de um sítio que o evento dispare, ou
de escrever que esse vermelho é observado fora do PR e a que custo.

### C3 — a suficiência «e só com ele» do quarto sítio é falsa como escrita (Critic-A, Critic-B)

`:569-571` promete que «com esse quarto sítio no lugar, **e só com ele**, um
toolkit alterado fora de cerimônia fica VISÍVEL», e `:1155` repete a forma.
Duas verificações a derrubam, por caminhos diferentes:
(a) `.github/workflows/ownership-nightly.yml:19-24` roda em `schedule` (cron
`43 6 * * *`) + `workflow_dispatch`, **sem `paths:`** — e o cabeçalho do próprio
arquivo (`:7-8`) registra que eventos `schedule` IGNORAM filtros de `paths:`;
`:64` roda o mesmo `shasum -a 256 -c`. Detecção post-hoc já existe: o quarto
sítio compra LATÊNCIA de PR, não a primeira visibilidade.
(b) o step de integridade só cobre MEMBROS do manifesto, e a entrada do toolkit
no manifesto é AC-6, isto é, W1 (`:1045`): entre a W0 e a W1 o step roda e passa.
A promessa vira: «o quarto sítio antecipa a detecção do nightly para o PR, e só
passa a cobrir o toolkit quando o AC-6 fechar».

### C4 — conflito de redação sobre o `--list` (Critic-A, Critic-B)

O Check do AC-1 exige que o `--list` liste todos os arquivos do toolkit, «os
`.py` inclusive» (`:826-829`), e a cláusula de Falha do mesmo AC lista «o job
`shellcheck-ceremony` recebendo um `.py` no conjunto do `--list`» (`:851`) —
lidas juntas, as duas parecem regras opostas. A decisão de `:157-162` já resolve
(o filtro é do CONSUMIDOR), mas o texto do AC não diz isso. Verificado: o
`--list` imprime TODOS os descobertos (`check-ceremony-script.py:283-286`) e há
dois consumidores no workflow (`ceremony-lint.yml:51` no sumário e `:78` no
shellcheck) — o plano nomeia um.

## Single-agent insights kept (verified on disk)

- **S1 — BLOQUEANTE (Critic-A) — a W3 diz «Gate: docs» e entrega um ADR.**
  `:796` rotula a W3 `Gate: docs`; `:797` põe
  `.claude/adr/ADR-2xx-shared-ceremony-toolkit.md` no file assignment; o AC-5
  (`:1043-1044`) exige `Status: ACCEPTED` **e um `.asc` do Owner sobre o
  sentinel da wave**. Verificado com o oráculo do repo:
  `check_canonical_edit.py --is-canonical .claude/adr/ADR-200-shared-ceremony-toolkit.md`
  responde `1`, e `.claude/adr/ADR-010-canonical-edit-sentinel.md` também `1`.
  Um pacote «docs» não produz `.asc` e, pela regra R1 desta noite, nem recebe
  rodada de codex: duas seções discordam sobre a mesma wave. Mantido.
- **S2 — BLOQUEANTE (Critic-B) — a W0a reescreve o predicado e deixa fora o
  teste que o CI coleta.** `:712-717` fixa a W0a em 5 paths, entre eles
  `.claude/scripts/check-ceremony-script.py`, que recebe o predicado novo de
  descoberta e o escopo novo da R8. Verificado:
  `.claude/scripts/tests/test_check_ceremony_script.py` existe, `pytest.ini:38-46`
  lista `.claude/scripts/tests` em `testpaths`, e `:104-109` afirma a forma
  ANTIGA da R8 (`test_r8_exec_bit_under_plans_is_blocking`). O predicado novo
  embarcaria sem teste na bateria que o CI roda de verdade — e os controles
  vermelhos da W0b ainda não têm executor enquanto a OQ-9 estiver aberta.
  Mantido.
- **S3 — BLOQUEANTE (Critic-C) — o único controle do AC-4 para a MUDANÇA DE
  REGRA do classificador é verde por construção.** `:1028-1030` acrescenta
  `.claude/scripts/ceremony/**` às raízes de `ceremony` e re-mede a base;
  `:988-992` declara o controle como «a base re-medida bater classe a classe».
  Verificado: o corpus congelado
  `.claude/plans/PLAN-188/s345-rail-classes.txt` tem **0** ocorrências de
  `scripts/ceremony` — ele precede o diretório. A igualdade classe-a-classe
  passa com a raiz nova certa, errada ou ausente. Falta o controle POSITIVO
  sintético: um bloco citando `.claude/scripts/ceremony/read_manifest.py` sai
  `product` sob as regras antigas (`measure-rail-classes-v2.py:40` `PRODUCT_RE`
  casa `\.claude/scripts/[\w\-/]+\.py`; `:52-64` `classify_path`) e tem de sair
  `ceremony` sob as novas. Mantido.
- **S4 (Critic-C) — o «5/5» da W0 está na granularidade errada.** `:822-823`
  manda o runner imprimir `5/5`; `:644-649` nomeia cinco ARQUIVOS de controle,
  um por invariante falsificável. Mas a invariante 3 (`:465-476`) exige, com
  todas as letras, **TRÊS** controles vermelhos nomeados ((i) sem argumento,
  (ii) sentinela + env do rascunho, (iii) material MARCADO fora do self-test).
  O piso real da W0 é 7 vermelhos, não 5. Mantido — é aritmética de aceite, não
  mudança de modelo.
- **S5 (Critic-C) — o cabeçalho do AC-1 discorda dos seus próprios Checks.**
  `:815` promete «≥ 1 controle VERMELHO por invariante»; os dois Checks
  enumeram `{1,3,4,5,10}` (W0) e `{2,6,7,8}` + as metades de escrita de 4/5
  (W1). A invariante 9 não tem controle em nenhum — corretamente, porque
  `:496-505` a declara ADVISORY («INFORMA e nunca recusa»). O ajuste é escrever
  a exceção no cabeçalho, não criar controle. Mantido.
- **S6 (Critic-A, versão estreitada) — o AC-4 pede um artefato que a W3 não
  entrega.** O `--cohort` tem casa: é criado no
  `measure-rail-classes-v2.py`, que ESTÁ no file assignment da W3 (`:797-799`).
  O que não tem arquivo nomeado é a **LISTA sha256-pinada dos registros dos três
  pacotes da coorte** (`:1013-1017`) nem a base re-medida com a regra nova
  (`:1028-1030`, «grava o digest novo»). É a mesma classe que o round 2 já curou
  para o `.sha256`. Mantido nesta forma.
- **S7 (Critic-A) — a opção (iii) da OQ-9 depende de um objeto da W1.**
  `:1198-1200` nomeia «execução local exigida pelo `harness.sh` de cada
  cerimônia»; o `harness.sh` não está entre os 6 paths da W0b (`:717-720`) e
  aparece no aceite da W1 (`:853-859`). No braço (iii) os cinco (sete) vermelhos
  da W0 ficam sem executor — que é exatamente a pré-condição que a OQ-9 foi
  promovida a fechar (`:1203-1205`). **Não decidimos a OQ-9**: o ajuste é
  escrever essa consequência DENTRO da opção (iii), para o Owner escolher com
  ela à vista.
- **S8 (Critic-B) — os controles de EVENTO do AC-1 não têm instrumento
  nomeado.** «um PR do toolkit que não dispare o `ceremony-lint.yml`» (`:851`) e
  os três controles positivos do quarto sítio precisam de um PR real ou de um
  casador de glob local; sem isso provam um NOME no YAML, não um evento. O
  precedente da casa citado pelo crítico —
  `.claude/hooks/tests/test_workflows_class_guard.py` — testa o predicado, não a
  fiação. Mantido como exigência de nomear o instrumento.
- **S9 (Critic-C) — o mecanismo do censo está trocado.** `:276-278` atribui a
  ausência de «sobra não rastreada» a `staged/` ser `gitignore`d num checkout
  limpo. O mecanismo que vale nas DUAS árvores é o filtro
  `check-ceremony-script.py:329-330` (`if n_block and not waived and is_tracked`),
  e `blocking_unwaived` conta ACHADOS, não arquivos. O número não muda; a frase
  que o explica, sim. Mantido como precisão.

## Single-agent insights rejected / deferred

- **(Critic-B) acrescentar à OQ-9 uma opção (iv) «aceitar a detecção do nightly,
  sem sítio novo».** Verifiquei o fato que a sustenta (C3-a: o nightly roda o
  `shasum -c` em cron sem `paths:`) e ele entra no plano por C3. Mas escrever
  uma quarta opção é chegar perto de decidir uma OQ que o Owner mantém aberta
  por desenho, e o §Riscos já fixa a regra de que a réplica é ADITIVA e o step
  de dentro do `smoke` nunca sai (rail r2 M1). **Deferido ao Owner como
  recomendação registrada, não como must-fix.**
- **(Critic-C) segunda metade da Q4 — «o piso real da W0 é 7» lida como pedido
  de re-escopo da W0.** Rejeitado nessa leitura: o texto do plano já nomeia os
  três vermelhos da invariante 3; o defeito é a CONTAGEM publicada no Check, não
  o escopo da wave. O must-fix é aritmético (M8), e não move nada entre waves.
- **(Critic-B) P3-6, primeira metade — «um predicado de raiz do toolkit escrito
  contra `REPO_ROOT` seria invisível à suíte».** É um aviso de IMPLEMENTAÇÃO
  correto (`check-ceremony-script.py:131` constrói as raízes a partir do
  argumento `--root`, enquanto `:93` usa a constante `REPO_ROOT` para os
  waivers), mas é conselho para quem escrever a W0a, não incoerência do texto do
  plano. **Deferido para a wave**, com o path já citado aqui.

## Plan adjustments (must-fix — o texto do plano tem de absorver)

1. **[BLOQUEANTE]** `:150-156` — trocar a justificativa: o step
   `shellcheck-ceremony` **não pode** devolver rc 1
   (`ceremony-lint.yml:75` `continue-on-error`, `:81-82` `|| true`,
   `:77` sem `-e`, `:72` «ADVISORY nesta fase»). A decisão de filtrar `.sh`
   permanece; a razão passa a ser o ruído `SC1071` permanente no relatório.
2. **[BLOQUEANTE]** `:851` — remover «o job `shellcheck-ceremony` recebendo um
   `.py`» da lista de FALHA de CI **ou** nomear o verificador executável fora do
   workflow que torna esse controle falsificável.
3. **[BLOQUEANTE]** `:1059-1063` (AC-6) — o vermelho (ii) precisa de um sítio
   que o append de waiver DISPARE (nenhum dos 4 — `release.yml:63`,
   `npm-publish.yml:141`, `ownership-nightly.yml:64`, `smoke-install.yml:360` —
   é disparado por ele), ou o AC escreve que ele é observado fora do PR, e a que
   custo operacional (um append de waiver vira cerimônia que pode travar um
   release).
4. **[BLOQUEANTE]** `:796-797` — resolver a W3: ou ela deixa de ser rotulada
   «Gate: docs» (o oráculo responde **1** para
   `.claude/adr/ADR-2xx-*.md`, e o AC-5 em `:1043-1044` exige `.asc` do Owner),
   ou o ADR sai do file assignment da W3 e vai para a wave que a OQ-1 decidir.
5. **[BLOQUEANTE]** `:712-717` — `.claude/scripts/tests/test_check_ceremony_script.py`
   entra no file assignment da W0a (`pytest.ini:38-46` o coleta; `:104-109`
   afirma a forma ANTIGA da R8). Atualizar a contagem de paths da W0a no mesmo
   parágrafo.
6. **[BLOQUEANTE]** `:988-992` + `:1028-1030` — acrescentar o controle POSITIVO
   sintético da raiz nova do classificador (um bloco citando
   `.claude/scripts/ceremony/read_manifest.py`: `product` sob as regras antigas,
   `ceremony` sob as novas). A igualdade classe-a-classe contra
   `s345-rail-classes.txt` é verde por construção — o corpus tem **0**
   ocorrências de `scripts/ceremony`.
7. `:569-571` e `:1152-1156` — reescrever a suficiência: o
   `ownership-nightly.yml:19-24` já roda o mesmo `shasum -c` em cron **sem**
   `paths:`; o quarto sítio antecipa a detecção para o PR, e só cobre o toolkit
   depois que o AC-6 (W1) o puser no manifesto.
8. `:822-823` — corrigir o «5/5»: a invariante 3 (`:465-476`) exige três
   vermelhos, logo o piso da W0 é **7** vermelhos sobre 6 arquivos de controle.
9. `:815` — escrever no cabeçalho do AC-1 a exceção da invariante 9 (ADVISORY
   por `:496-505`), para o cabeçalho parar de discordar dos dois Checks.
10. `:1013-1017` + `:797-808` — nomear no file assignment da W3 os artefatos que
    o Check do AC-4 exige: a lista sha256-pinada dos registros da coorte e a
    base re-medida com a regra nova.
11. `:1198-1200` — escrever DENTRO da opção (iii) da OQ-9 que o `harness.sh` é
    entrega da W1 (`:853-859`; ausente dos 6 paths da W0b em `:717-720`), de
    modo que esse braço deixa os vermelhos da W0 sem executor. **Não decidir a
    OQ-9.**
12. `:851` + `§Riscos` — nomear o instrumento dos controles de EVENTO (PR real
    ou casador de glob local); sem ele provam um nome no YAML, não um evento.
13. `:826-829` × `:851` — desfazer a leitura contraditória do `--list`: ele
    lista TODOS os descobertos (`check-ceremony-script.py:283-286`) e o filtro é
    do CONSUMIDOR (`:157-162`); citar os dois consumidores do workflow
    (`ceremony-lint.yml:51` e `:78`), não um.
14. `:276-278` — trocar o mecanismo declarado no censo: a exclusão de não
    rastreados é o filtro `is_tracked` de `check-ceremony-script.py:329-330`
    (vale nas duas árvores), não a `gitignore`; e `blocking_unwaived` conta
    ACHADOS, não arquivos.

## Round verdict

**RUN-ANOTHER-ROUND.**

Seis itens bloqueantes sobrevivem à verificação em disco (M1–M6), dos quais um
foi levantado pelos três críticos (C1) e um por dois (C2). A regra do round é
explícita: `PROCEED` só com zero itens bloqueantes. O rótulo
**design-coherent NÃO é registrado neste round** — ele se registra apenas quando
o round ITSELF termina com zero bloqueantes nas três críticas, e aqui foram
2 + 2 + 3.

Não é `ESCALATE-TO-OWNER`: nenhum dos 14 must-fix decide uma das OQ abertas
(OQ-1, OQ-2, OQ-4, OQ-5, OQ-6, OQ-8) nem a OQ-7/OQ-9 promovidas a pré-condição.
M11 apenas escreve a consequência de um braço da OQ-9 para o Owner escolher com
ela à vista; a recomendação do Critic-B de uma opção (iv) fica registrada como
recomendação, não como mudança de texto.

Nenhum dos ajustes reescreve o MODELO do plano: todos os catorze corrigem uma
AFIRMAÇÃO, uma CONTAGEM ou um ESCOPO DE ARQUIVO — a arquitetura das dez
invariantes, o corte de waves e as decisões (a)–(d) do §Approach seguem
intactas. A classe que o round 3 fecha é a mesma do D1 do round 2: **controle de
aceite cuja metade vermelha não é alcançável pelo evento que a dispara.**

Nenhum arquivo da árvore viva foi tocado por esta síntese.
