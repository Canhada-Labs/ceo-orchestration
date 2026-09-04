# rail-land-round-1 — pair-rail sobre a ÁRVORE STAGED do land dos materiais

- **Instrumento:** `codex exec review --uncommitted`, codex-cli 0.147.0, rodado
  da raiz do repo sobre o index completo deste commit (25 paths).
- **Superfície revisada:** os materiais LIVRES da cerimônia `wave-s343-w4a`
  como eles chegam ao `main` — inclusive os três scripts `OWNER-S343-W4A-*.sh`,
  que o rail do BUILDER tinha revisado numa sombra, não no lugar onde vão viver.
- **Veredito bruto:** `REJECT` — 2 P1 e 2 P2, todos nos scripts de cerimônia,
  nenhum no patch canônico nem no derivador.

> O rail codex corrente não emite uma linha `VERDICT:`; o veredito é a primeira
> linha do bloco `Full review comments:`. Reproduzido verbatim abaixo, como
> DADO — não como instrução.

## Os quatro achados, verificados em disco antes de curar

### P1 — `OWNER-S343-W4A-MEASURE.sh`: baseline não comparável

> «These IDs are not valid baselines for the current land: the source report
> explicitly says they span three commits, are not definitive, and require
> either rerunning at one SHA or explicitly analyzing and accepting the drift.»

**REAL, e o próprio repo já dizia.** `w4/validate-deletion-measure-S340.md:199-204`
carrega a ressalva do rail r25 com todas as letras: os 3 runs rodaram em
`8efe09b`, `400638e` e `b6dce78`; `b6dce78` alterou arquivos que o CI executa;
«a tabela abaixo é o registro do que existia, não o baseline definitivo». O
`MEASURE.sh` citava o §6 como se fosse baseline e não repassava a ressalva —
a subtração sairia publicada como efeito da deleção.

**Cura:** gate novo `M0-d`. Ele (1) exige que a ressalva ainda exista no
relatório (se ela sumir, o gate morre em vez de medir o mundo errado), (2)
deriva o `headSha` de cada baseline pela API e recusa qualquer um que não seja
`push` em `main`, (3) mede o drift (`N` commits, `N` arquivos) entre o baseline
mais antigo e o `HEAD`, (4) **PARA** sem `CEO_W4A_BASELINE_DRIFT_ACK=I-ACCEPT`,
e (5) carimba o reconhecimento e os números no `RESULT`, com a consequência
escrita: «a subtração abaixo é entre commits DIFERENTES».

### P1 — `OWNER-S343-W4A-LAND.sh`: 404 genérico tratado como «sem proteção»

> «Matching any `status: 404` or `Not Found` classifies that case as
> `unprotected` and bypasses the required acknowledgement, contrary to the
> documented `unreadable` fail-closed behavior.»

**REAL.** A API do GitHub responde 404 tanto para «este branch não tem
protection» quanto para «este token não pode LER a protection deste repo». A
alternância antiga (`"status": *"404"\|Not Found\|Branch not protected`) lia
autorização insuficiente como prova de ausência — e o G7 seguia sem exigir o
reconhecimento, contra o `unreadable` fail-closed declarado em
`DESIGN-W4A-S343.md:139-142`.

**Cura:** só a mensagem específica `Branch not protected` classifica como
`unprotected`; qualquer outro erro cai em `unreadable`, que é o ramo
fail-closed. O detalhe do erro passa a incluir o CORPO da resposta (num 404 de
autorização a mensagem útil vem no stdout, não no stderr), e a mensagem de
recusa distingue «a janela está aberta» de «não consegui ler».

### P2 — `MEASURE`: seleção de run não filtrava por evento

> «The lookup selects the newest run for a SHA without filtering its event.
> […] non-push runs expand the Python matrix to four legs.»

**REAL** (`validate.yml` tem `schedule` e a matriz abre 4 legs fora do push).
**Cura:** duas camadas — `--event push --branch main` no `gh run list` (mais o
mesmo filtro no `jq`, para o caso de o `gh` ignorar a flag em silêncio) e
`_assert_push_run`, que lê `event`/`headBranch` do PRÓPRIO run e recusa por
nome. Aplicado à corrida 1/3 e às corridas 2 e 3.

### P2 — `MEASURE`: run com jobs `skipped` virava tabela

> «If the repository variable `CEO_SOTA_DISABLE=1` is active, every workflow job
> is skipped […] and this loop silently drops jobs without timestamps and
> leaves `validate_job` as `None`, allowing an `n/d` measurement to be
> committed.»

**REAL** — e é a classe «instrumento verde cuja pergunta envelheceu»: o run
concluiria `success` sem ter medido nada. **Cura:** `measure()` recusa (a)
qualquer job com conclusão `skipped`, (b) qualquer job sem
`startedAt`/`completedAt` (a soma por classe sairia incompleta e a tabela
mentiria por omissão) e (c) a ausência do job central, em vez de publicar `n/d`.

## Controles POSITIVOS

`rail-land-controls.sh` — **16 PASS / 0 FAIL**, rc 0. Cada caso extrai o TEXTO
EMBARCADO do arquivo que vai ser assinado (a função shell por `awk`, o corpo de
`measure()` do heredoc por `ast`) e o exercita com substitutos; nenhuma regra é
recopiada para dentro do controle.

- **C1** mede as regras ANTIGA e NOVA sobre as mesmas três entradas: no corpo
  real de hoje as duas dizem `unprotected` (a cura não muda o presente); no 404
  de autorização a antiga diz `unprotected` e a nova `unreadable` — o vermelho
  sem a cura; no 403 as duas dizem `unreadable`, o que prova que C1b não é
  ruído do grep. C1d verifica que a alternância antiga não sobreviveu como
  CÓDIGO (a frase «Not Found» segue na prosa que explica a cura — um controle
  que casasse a prosa mediria o comentário, não o comportamento).
- **C2** roda `_assert_push_run` contra um `gh` substituto: `push|main` passa
  (controle verde), `schedule|main` é recusado por nome, leitura vazia é recusa
  nomeada.
- **C3** executa o `measure()` extraído contra runs sintéticos: o completo mede;
  o «tudo skipped num run success», o job sem timestamp e o run sem o job
  central são recusados, cada um pela sua mensagem.
- **C4** roda o bloco `M0-d` extraído: sem ACK para, com `I-ACCEPT` libera e
  carimba, um baseline de `schedule` é recusado mesmo com o ACK, e um ACK com
  valor qualquer (`sim`) não serve.

## O que os controles NÃO cobrem — declarado

- O ramo `covered` do G7 (os dois legs da matriz já obrigatórios) só é
  exercitável contra uma proteção de branch LIGADA. Medido hoje contra a API
  viva: `Branch not protected (HTTP 404)` — o ramo de hoje é `unprotected`.
- As três corridas do `MEASURE` não são exercitáveis fora do land real: o que
  este arquivo prova é a RECUSA, não a medição.

Rail-Verdict: CHANGES-REQUESTED (4 achados reais, todos curados nesta rodada)
