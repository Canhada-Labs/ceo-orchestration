# rail-land-round-2 — segunda passagem sobre o INDEX, já com as curas da r1

- **Instrumento:** `codex exec review --uncommitted`, codex-cli 0.147.0, raiz do
  repo, index completo (27 paths).
- **Superfície:** os mesmos materiais, agora com o gate `M0-d`, o
  estreitamento do G7, o filtro de evento e as recusas do `M3` dentro.
- **Veredito bruto:** `REJECT` — **4 achados NOVOS**, nenhum deles repetição da
  rodada 1 (as quatro curas anteriores passaram). Dois P1 e dois P2, de novo
  todos nos materiais e nenhum no patch canônico.

> A lição que esta rodada paga é a que o repo já tinha escrito: *rodada limpa
> prova a SUPERFÍCIE revisada, não o entregável* — e aqui nem limpa foi. Curar
> um achado move a superfície; a rodada seguinte revisa outra coisa.

## Os quatro achados

### P1 — `OWNER-S343-W4A-LAND.sh`: a remediação impressa APAGAVA required checks

> «this `PATCH` supplies only the two new contexts; GitHub treats that array as
> the replacement configuration, so following the printed remediation can remove
> `validate` and every other required check.»

**REAL, e o mais perigoso do pacote** — porque o texto era uma receita para o
Owner colar. `PATCH /branches/{b}/protection/required_status_checks` trata
`contexts` como a configuração INTEIRA: mandar só os dois legs novos apagaria o
`validate` e todo o resto. O gate existia para PROTEGER o conjunto de required
checks e imprimia o comando que o destruiria.

**Cura:** a receita passa a usar o endpoint ADITIVO
(`POST .../required_status_checks/contexts`), com um `gh api ... --jq '.contexts'`
antes e depois para o Owner conferir, e a UI (`Settings > Branches`) como
primeira opção.

### P1 — `OWNER-S343-W4A-MEASURE.sh`: a prosa do RESULT reintroduzia o claim causal

> «These lines nevertheless attribute the entire `validate` delta to the removed
> steps and assert a run-wall relationship "by construction", creating an
> unsupported speed claim contrary to `AGENTS.md:9-11`.»

**REAL, e é a própria classe que esta wave cura.** A cura da rodada 1 fez o
relatório carimbar «parte do delta não é a deleção», mas a seção «Como ler»
seguia dizendo que o delta do job `validate` **é** o custo dos dois steps. O
documento se contradizia — e a metade mais confortável de ler era a errada.

**Cura:** a seção passa a dizer o que os números são (subtração bruta entre dois
conjuntos de runs), o que eles NÃO dizem (não isolam o custo dos steps, porque
os baselines rodaram em commits diferentes), e o que faltaria para um número
causal (três baselines re-rodados num único sha pré-deleção — exatamente o que
o §6 do relatório da S340 já pedia).

### P2 — `OWNER-S343-W4A-MEASURE.sh`: as 3 corridas podiam medir árvores diferentes

> «If a commit lands after the W4a land but before measurement without touching
> `validate.yml`, `LAND_SHA` remains the old land commit and run 1 comes from
> that tree, while runs 2 and 3 are empty commits based on the newer `HEAD`.»

**REAL.** E o comentário do bloco vendia isso como recurso («derivar assim
tolera commits livres entre o land e esta medição») — tolerava a DERIVAÇÃO do
sha, não a comparabilidade da medição.

**Cura:** `HEAD` tem de ser o commit do land. Caso contrário o `MEASURE` PARA,
imprime quantos commits entraram no meio, e só segue com
`CEO_W4A_POST_DRIFT_ACK=I-ACCEPT` — com o número carimbado no `RESULT`.

### P2 — `apply-w4a-validate-deletion.py`: a garantia transacional não cobria a EXCEÇÃO

> «If writing the second workflow raises […] the first workflow has already been
> overwritten, and neither `_postconditions` nor the rollback block is reached.»

**REAL.** O rollback cobria «pós-condição reprovou», não «a escrita levantou».
Uma permissão ou um disco cheio no segundo path deixaria a árvore meio-aplicada
— o estado que o comentário do bloco diz existir para impedir.

**Cura:** o laço de escrita vai num `try/except OSError` que restaura só o que
já foi escrito e recusa por nome; se a própria restauração falhar, o script sai
`2` dizendo qual arquivo ficou sujo e como restaurá-lo.

**O patch NÃO mudou:** a derivação foi re-executada num worktree limpo em `HEAD`
depois da cura e o `git diff` continua byte-idêntico ao `W4A.patch`, com o mesmo
`sha256 35e26cdc47e606d12eca45a267d6c147a3ed8f381693a25782f3f823066f6db3`. O V3
do LAND (`HEAD + derivador == patch`, byte a byte) segue válido.

## Controles positivos (acumulados)

`rail-land-controls.sh` — **23 PASS / 0 FAIL**, rc 0. Os três casos novos:

- **C5** verifica que a receita destrutiva (`PATCH` na lista inteira) não
  sobrevive no arquivo que será assinado e que o endpoint aditivo está lá.
- **C6** extrai o bloco de drift pós-land e o roda: `HEAD == land` passa
  (controle verde), um commit no meio PARA, e o `I-ACCEPT` libera CARIMBANDO o
  número.
- **C7** monta uma árvore descartável, torna o SEGUNDO path não-escrevível e
  roda o derivador de verdade: os dois arquivos voltam aos bytes originais e a
  recusa é nomeada; em seguida, na MESMA árvore com os dois graváveis, as 11
  edições aplicam (controle verde na mesma superfície).

**Controle RED independente do C7,** rodado fora do arquivo de controles: uma
variante PRE-cura do derivador (o `try` substituído por `if True:`) sobre a
mesma árvore deixa `smoke-install.yml` MUTADO e morre com
`PermissionError: [Errno 13]` sem restaurar nada — a árvore meio-aplicada,
reproduzida.

Rail-Verdict: CHANGES-REQUESTED (4 achados reais, todos curados nesta rodada)
