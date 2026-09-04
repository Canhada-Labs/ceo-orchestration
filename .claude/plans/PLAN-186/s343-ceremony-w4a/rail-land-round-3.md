# rail-land-round-3 — terceira e ÚLTIMA passagem do rail do land

- **Instrumento:** `codex exec review --uncommitted`, codex-cli 0.147.0, raiz do
  repo, index completo (29 paths).
- **Veredito bruto:** `REJECT` — **5 achados NOVOS**, um P1 e quatro P2. De novo
  nenhum repetido, e de novo **nenhum no patch canônico**: os 12 achados das
  três rodadas do land vivem todos nos scripts de cerimônia.
- **Teto de rodadas:** o land deste pacote tinha um teto declarado de 3 rodadas.
  Esta é a terceira. Os cinco achados foram CURADOS e cada cura tem controle
  positivo, mas **a superfície resultante não foi revisada por uma 4ª rodada** —
  declarado aqui em vez de escondido, porque «rodada limpa prova a superfície
  revisada, não o entregável» vale igualmente para a última rodada suja.

## Os cinco achados

### P1 — `OWNER-S343-W4A-LAND.sh`: material de cerimônia sujo era só um AVISO

> «If a tracked ceremony input such as `EXPECTED-BASELINE.txt` or
> `COMMIT-MSG-W4A.txt` is edited after SIGN without a commit, it is classified as
> noncanonical here and merely tolerated; LAND then consumes those modified
> working-tree bytes while `Anchor-SHA` still matches the unchanged HEAD.»

**REAL, e o furo é de PROVENIÊNCIA.** O G0 classificava os paths sujos pelo
oráculo de canonicidade: canônico-fora-do-Scope ⇒ recusa; o resto ⇒ aviso
tolerado. `EXPECTED-BASELINE.txt` é não-canônico — verdade e irrelevante: é dele
que saem TODOS os limiares que o V-block compara, e o LAND o lê da **árvore de
trabalho**, enquanto o `Anchor-SHA` amarra o **commit**. Editar a base esperada
entre o SIGN e o LAND afrouxaria os gates com a assinatura ainda casando.

**Cura:** um terceiro balde no G0 — um path da lista `MATERIALS` que apareça
sujo é RECUSA nomeada, com a saída escrita (commitar e re-assinar, ou
`git restore`). **DOIS materiais ficam de fora, e não por conveniência:** o
sentinel, que o próprio SIGN muta na árvore de trabalho e cujo conteúdo é
exatamente o que o `.asc` assina (uma edição posterior derruba o G1 na
verificação GPG), e o patch, que tem gate próprio e mais específico — o G2,
que compara o sha256 contra o `Patch-sha256` assinado.

> **A primeira versão desta cura pegava TUDO — e derrubou 20 dos 27 casos do
> harness**, porque o SIGN legítimo deixa o sentinel sujo por desenho. O
> harness não é decorativo: ele reprovou uma cura escrita minutos antes e
> disse por quê. Os controles C10d–C10g fixam o escopo em ambas as direções
> (o sentinel e o patch NÃO caem no balde; a base esperada e a mensagem de
> commit caem), para que o próximo a mexer aqui veja a fronteira.

### P2 — `LAND`: o `--dry-run` podia sair 0 sem ter restaurado

> «Bash preserves that original status after an EXIT trap, so a failed reverse
> apply or fingerprint mismatch can leave canonical workflows modified while the
> command still exits successfully.»

**REAL.** Os dois ramos de falha de restauração só imprimiam diagnóstico. Um
`--dry-run` que aplicou o patch, falhou ao revertê-lo, e saiu `0` deixaria os
workflows KERNEL mutados anunciando sucesso.

**Cura:** os dois ramos escalam `_land_rc=4` e o trap termina com
`exit "$_land_rc"` — sem essa linha a atribuição era decorativa. Medido no bash
desta máquina (controle C10c): trap que só atribui ⇒ status `0`; trap com
`exit` ⇒ status `4`.

### P2 — `apply-w4a-validate-deletion.py`: o path que FALHA não era restaurado

> «If `write_text()` truncates or partially writes a file before raising
> `OSError` […] the failing path is not yet in `written`, so the exception
> handler restores earlier files only and then falsely reports that the tree was
> restored.»

**REAL — e é um defeito DA CURA da rodada 2**, o que é exatamente o que um rail
serve para pegar. O path entrava em `written` DEPOIS da escrita; um
`write_text` que trunca e só então levanta deixaria o arquivo mutilado fora da
lista, com o script anunciando «a árvore foi RESTAURADA».

**Cura, em duas metades:** (a) o path entra em `written` ANTES da escrita; (b)
se a restauração de um path falhar, o script LÊ os bytes e compara com o
original — se forem iguais, aquele path nunca mudou (é o caso do arquivo
somente-leitura cuja abertura falhou) e seguir é correto; se divergirem, aí sim
é árvore meio-aplicada, `exit 2` com o comando de recuperação. A metade (b) só
apareceu porque o controle C7 ficou VERMELHO com a metade (a) sozinha: a cura
gerou o achado seguinte, e a arquitetura mudou em vez de ganhar mais um remendo.

### P2 — `MEASURE`: a rota limpa que o próprio gate imprime era inexequível

> «If the Owner follows the printed option to replace `BASELINE_IDS` with three
> reruns from one pre-deletion SHA, this branch still unconditionally demands
> `CEO_W4A_BASELINE_DRIFT_ACK` and claims the baselines used different SHAs.»

**REAL.** O `M0-d` da rodada 1 imprimia «(a) RE-RODAR 3 baselines num único sha»
e, se o Owner fizesse isso, continuaria exigindo o reconhecimento de drift — e
carimbaria no `RESULT` uma ressalva FALSA.

**Cura:** o gate MEDE a unicidade (`sort -u` sobre os shas derivados). Um sha
único ⇒ `ok`, sem ACK, e o `RESULT` carimba «Baseline CONTROLADO» em vez da
ressalva.

### P2 — `MEASURE`: baseline que não é `success` entrava na tabela

> «The post-deletion runs are watched for `success`, but baseline IDs are checked
> only for SHA/event/branch, and `measure()` records any live conclusion.»

**REAL.** As corridas pós-deleção passam pelo `_watch` (só `completed|success`);
os baselines são ids registrados e não passavam por gate nenhum de conclusão.

**Cura:** `measure()` exige `conclusion == "success"` — dos DOIS lados da
subtração.

## Controles positivos (acumulados)

`rail-land-controls.sh` — **36 PASS / 0 FAIL**, rc 0. Os casos novos:

- **C8** roda o `M0-d` extraído com um `gh` substituto que deriva um sha por id:
  três shas IGUAIS passam sem ACK; três DIFERENTES continuam exigindo. O
  contraste na mesma superfície é o que impede o caso de virar verde vazio.
- **C9** executa o `measure()` extraído: `success` entra; `failure`,
  `cancelled` e conclusão vazia são recusados por nome.
- **C10** verifica o balde novo do G0 e a re-emissão do status no trap, mais uma
  SONDA de bash medida nesta máquina que reproduz o defeito (trap sem `exit`
  ⇒ status 0).
- **C10d–C10g** rodam o laço de materiais sujos EXTRAÍDO contra um
  `DIRTY_FILE` sintético e fixam a fronteira nas duas direções: sentinel e
  patch NÃO caem no balde novo; base esperada e mensagem de commit caem; um
  path de fora não vira falso-positivo.
- **C7** (da rodada 2) foi o caso que expôs a metade (b) da cura do derivador:
  ele ficou VERMELHO contra a primeira versão e só voltou a verde com a
  comparação de bytes.

## Residual declarado desta rodada

As cinco curas acima **não passaram por uma rodada de rail**. O teto de 3
rodadas foi respeitado; o custo é este, e ele fica escrito. As três primeiras
rodadas acharam 4, 4 e 5 defeitos reais — a curva não estava caindo, e é
razoável supor que uma 4ª rodada acharia mais. Nada disso toca o `W4A.patch`,
que segue byte-idêntico e revisado por 6 rodadas próprias.

Rail-Verdict: CHANGES-REQUESTED (5 achados reais, curados; teto de rodadas atingido)
