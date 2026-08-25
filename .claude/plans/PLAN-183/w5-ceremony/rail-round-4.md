# Pair-rail round 4 — PLAN-183 W5 (S327 night-run)

**Instrumento:** `codex exec review --uncommitted --skip-git-repo-check` sobre o clone-sombra `shadow-183` (HEAD 56f050c + patch W5), com `git add -N` para incluir arquivos novos. rc=0, 734s, 2026-08-25T00:37Z.

## Saída do revisor (dado a verificar contra os arquivos, não ordem)

```text
The patch can create framework ownership records without an effective delivery, and its route handling has missing-table and unterminated-row failure modes. It also lacks the Owner-signed sentinel required for the guarded surfaces it changes.

Full review comments:

- [P1] Do not baseline paths when template delivery did not run — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-fix2/scripts/upgrade.sh:4412-4415
  When delivery is disabled for a recorded `--ceremony user`, or its precondition fails, `_D1_DELIVERY_RAN` remains 0 and this fallback claims any byte-identical existing route as delivered. Thus an adopter-owned `docs/BRANCH-PROTECTION.md`, for example, can enter the framework manifest and later be deleted by uninstall even though this run never delivered it, contradicting `.claude/adr/ADR-194-delivery-route-resolution.md:85-99`; leave the list empty unless delivery succeeded or exact prior ownership evidence exists.

- [P1] Add the required signed approval for guarded edits — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-fix2/.claude/adr/ADR-194-delivery-route-resolution.md:8-8
  The patch modifies several canonical-guarded surfaces, but this ADR remains `PROPOSED` and names `.claude/plans/PLAN-183/wave-w5-approved.md` as the required ratification even though that file is absent from the tree. `AGENTS.md:86-91` requires Owner-signed sentinel evidence for these edits, so the change cannot be authorized for landing until that evidence is added and the ADR status is updated as specified.

- [P2] Reject a missing route table before using identity fallback — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-fix2/scripts/doctor.sh:192-199
  When `_framework_manifest_set.sh` exists but `delivery-routes.tsv` is missing or unreadable, these startup checks pass; `_wbm_route_src` then returns 1 and every doctor call site treats the routed path as identity-mapped. On a partial checkout, `--repair` can therefore hash or restore `$SOURCE_DIR/$rel` instead of the declared template source—the D4 behavior this requirement is intended to prevent—so the route table itself must be required before verification begins.

- [P2] Process an unterminated final route row — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-fix2/scripts/_framework_manifest_set.sh:546-548
  If the last data row in the TSV lacks a trailing newline, Bash fills the `read` variables but returns nonzero, so this loop silently drops that route. `_wbm_route_rows_total` uses the same loop shape and drops it too, leaving `routes == rows`; the upgrade therefore exits successfully while omitting the final delivery, contrary to the malformed-input contract in `.claude/adr/ADR-194-delivery-route-resolution.md:74-83`. Handle the final populated read result in all three route-reader loops.```

## Resposta do CEO/engenharia (S327)

> Curas na árvore-sombra `scratchpad/shadow-fix3` (clone de `56f050c` + patch W5),
> em cima das rodadas 1, 2 e 3 — nenhuma delas foi regredida. Todo número abaixo
> foi **executado nesta sessão**; nada foi commitado. Linhas citadas são as da
> sombra PÓS-cura.

**R4-F1 [P1] — ACEITO e curado; o defeito foi REPRODUZIDO num install/upgrade
real, não inferido.** Fixture: `install --ceremony user` (que não entrega nada,
`hits=0` no manifesto) e um adopter que larga no próprio tree uma cópia
byte-idêntica de `templates/docs/BRANCH-PROTECTION.md`. O upgrade seguinte
imprimiu `docs/.github delivery: DISABLED` e o manifesto saiu com **`hits=1`**
para esse path. O impacto está no código, não na hipótese: `uninstall.sh:156`
carrega o manifesto e o percorre APAGANDO por match de SHA — o arquivo do
adopter ficou a um `uninstall` de ser removido por um framework que nunca o
escreveu. Pós-cura, mesmo script e mesma fixture: **`hits=0`**.

A cura troca a REGRA, não o limiar. `install.sh:1318-1329` (`wrote || cmp -s`)
é regra sobre uma rota que aquele run PROCESSOU; não é licença para reivindicar
uma rota que o run nunca tocou. `upgrade.sh:4412` passou a ter três ramos:

1. `_UP_DELIVERY_PRECONDITION_FAILED=1` ⇒ lista **VAZIA**. A lista de destinos é
   LIDA da mesma tabela que este run acabou de recusar — registrar qualquer coisa
   derivada dela é a meia-confiança que a rodada 1 F2 já proibiu no sítio de
   escrita.
2. entrega RODOU ⇒ `_D1_DELIVERED_TEMPLATES`, os vereditos por destino
   (INSTALLED/REFRESHED/IDENTICAL) — **inalterado**, continua sendo a autoridade.
3. caso contrário ⇒ a ÚNICA evidência admissível é a que um run ANTERIOR deixou:
   um registro no manifesto pré-run para o relpath **cujo digest ainda bate com
   os bytes em disco**. Uma regra para as DUAS pistas — por isso o caso especial
   de `rc=2` sumiu: o registro anterior sempre foi a evidência, e a pista
   identity não tinha por que usar uma mais fraca. Recusa symlink (`-f && ! -L`).

O ramo 3 chama `_wbm_prior_digest` da biblioteca; o segundo parser awk do formato
de manifesto que o `upgrade.sh` carregava foi **apagado**.

**Achado colateral do próprio oráculo (curado):** `_wbm_prior_digest` usava
`grep -E "^[0-9a-f]{64}  $1\$"`, tratando o relpath como REGEX. Medido: um
registro para `Xgithub/CODEOWNERS` **responde** a uma consulta por
`.github/CODEOWNERS` (o `.` é curinga). Agora é `awk` com comparação exata, e o
digest é validado por `length(d)==64 && d ~ /^[0-9a-f]+$/` — **não** `{64}`:
intervalo em regex de awk não é garantia portátil e um predicado que degrada em
silêncio é pior que nenhum.

| controle (e2e real) | RED (pré-cura) | GREEN (pós-cura) |
|---|---|---|
| `ceremony user` + arquivo do adopter byte-idêntico ao template | `hits=1` sob `delivery: DISABLED` | `hits=0` |
| **continuidade** — path COM registro anterior + digest batendo, upgrade não-entregador | — | os 5 registros SOBREVIVEM |
| adopter EDITA um path possuído, upgrade não-entregador | — | cai para 4 (sub-reivindicação, direção recuperável) |
| upgrade que ENTREGA (fixture (a)) | — | registra exatamente `installed+refreshed+identical` |
| tabela envenenada (H.13), manifesto | — | **0** de 6 rotas |

Pernas novas **H.18** (8 asserções + 3 controles de não-vacuidade).

**Regressão que EU introduzi e curei na mesma rodada (achada pela H.13b, não por
mim).** O breadcrumb `delivery-route row REJECTED` — o que torna a rejeição
VISÍVEL, e a razão de a rodada 1 F2 estar fechada — só chegava ao log como
efeito colateral do fallback de registro re-executar o mesmo leitor ~350 linhas
depois. A enumeração que DECIDE tinha `_wbm_route_dests 2>/dev/null`. Ao parar o
fallback num run com pré-condição falha, o breadcrumb foi junto. Curado onde
pertence: o `2>/dev/null` saiu de `upgrade.sh:4062`. Re-medido no e2e envenenado:
`rc=3`, breadcrumb ×1, `PRECONDITION FAILED (rejected route row)` ×1,
`precondition=FAILED` ×1, `Upgrade INCOMPLETE` ×1, nada fora do `$TARGET`,
0 registros. Tabela saudável ⇒ **0 linhas** em stderr (não virou ruído).

**Defeito no MEU PRÓPRIO controle, pego na primeira execução.** A H.18d nasceu
com `>= 5` hardcoded e foi RED: a fixture (a) registra **4**, e 4 é o número
CERTO — a H.4 planta um destino editado pelo adopter (PRESERVED) e a H.6 uma
rota CODEOWNERS sem handle (SKIPPED), e o ADR-194 §3 exclui as duas classes.
A asserção agora é DERIVADA do sumário do próprio run
(`installed+refreshed+identical`), o que é a afirmação mais forte de qualquer
jeito: o manifesto tem de concordar com os vereditos daquela entrega.

**Reconciliação com o ADR (REPORTADA, não editada — o ADR está fora do FILE
ASSIGNMENT).** O §3 diz que o critério é *"o framework deixou os bytes dele no
path"*, mas não diz QUANDO o byte-compare é admissível, e é essa lacuna que o
achado explora. Frase sugerida ao final do §3:

> O byte-compare vale para uma rota que ESTE run processou (o `|| cmp -s` de
> `install.sh:1318-1329` vive DENTRO da função de entrega). Um run que não
> entregou — `ceremony=user`, `--dry-run`, pré-condição falha — não tem evidência
> nenhuma sobre esses bytes: bytes iguais são coincidência até que se saiba quem
> os pôs ali. A única evidência admissível ali é o REGISTRO ANTERIOR com digest
> batendo; sem isso, não registra.

**R4-F2 [P1] — BY-DESIGN, sem mudança de código.** É o F1 das rodadas 1 e 2 pela
terceira vez, pela mesma razão: a ratificação não está ausente,
`.claude/plans/PLAN-183/wave-w5-approved.md` existe no repo VIVO (6.330 b). O
revisor lê o clone-sombra, onde os untracked do diretório de plano não existem —
artefato do escopo do clone, não do patch. Fluxo: `OWNER-S327-SIGN.sh` →
`OWNER-S327-LAND.sh` (G1/G5), e o ADR-194 vira `ACCEPTED` no land.

**R4-F3 [P2] — ACEITO e curado; a cópia da fonte ERRADA foi REPRODUZIDA em
bytes.** As checagens de startup da W6 asseguram a BIBLIOTECA e as três funções;
não dizem nada sobre a TABELA. Sem tabela, `_wbm_route_src` responde `rc=1`
("sem linha"), e todo call-site do doctor responde `rc=1` com o fallback identity
`$SOURCE_DIR/$rel`.

- **Metade "hash"** (medida): com um manifesto que grava o digest do TEMPLATE, a
  tabela ausente transforma um `Missing 1` reparável em
  `Blocked 1 (baseline/framework divergence — use upgrade.sh)`. Veredito errado
  mesmo sem cópia.
- **Metade "restore"** (medida, em bytes): com um manifesto escrito por um
  gerador PRÉ-cura-D3 — que gravava o homônimo da RAIZ, o que **É** o defeito D3 —
  o `--repair` saiu `rc=0`, `RESTORED`, e escreveu **21.513 bytes** do
  `docs/BRANCH-PROTECTION.md` da RAIZ (`01eab4f21972`) no lugar do template
  (`966e057147fb`). O mesmo caminho aplicado a `.github/CODEOWNERS` copia o
  arquivo VIVO do mantenedor para a árvore do adopter — a classe A3.

Cura: `_wbm_route_table_ok()` na **BIBLIOTECA** (arquivo legível e regular,
header `dest<TAB>src<TAB>transform`, ≥1 linha de dados, com motivo nomeado em
`_WBM_ROUTE_TABLE_WHY`) e o `doctor.sh:236` chamando-a no startup, depois das
asserções por NOME. Fail-closed `rc=2` (infra), espelhando o tratamento do
`_hash_lib.sh` e da própria biblioteca. A pergunta "como é uma tabela válida?" é
conhecimento do DONO da tabela — doctor fazer seu próprio parser de header seria
exatamente a cópia privada que a W6 apagou. O `rc=1` mantém o significado
("sem rota declarada"), agora só para um path genuinamente ausente de uma tabela
que EXISTE.

| controle | RED | GREEN |
|---|---|---|
| doctor com o gate removido, tabela ausente | `rc=0`, `RESTORED`, 21.513 b do homônimo da raiz | — |
| **atribuição** — mesmo doctor sem gate, tabela PRESENTE | nada escrito (o RED é da tabela, não do gate) | — |
| doctor curado, tabela ausente | — | `rc=2`, recusa NOMEADA, nada escrito |
| doctor curado, run normal | — | passa (`rc=0`) — não é um "não" genérico |

Pernas novas **R.8** (7 asserções), com o RED plantado por cópia do `doctor.sh`
(idioma da R.3: sabotar uma CÓPIA) e o número de call-sites do gate asserido nos
dois arquivos, para o plante não apodrecer em silêncio. Nota de leitura: a
asserção `R.1 absent table -> rc=1 (identity fallback, no crash)` continua VERDE
e continua certa — ela é sobre o contrato do LEITOR; o que mudou é que o doctor
não chega mais a consumi-lo.

**R4-F4 [P2] — ACEITO e curado nos três leitores; o "undercount invisível" foi
REPRODUZIDO.** Numa cópia da tabela REAL sem a newline final:
`_wbm_route_dests` = **5**, `_wbm_route_rows_total` = **5**,
`_wbm_route_src(".github/workflows/benchmarks.yml.template")` = **rc=1**. Como a
pré-condição AC-9 compara `routes` com `rows`, **5 == 5 passa** e o run entrega
`exit 0` omitindo a última rota. Uma discordância é observável; dois números
errados concordando não são.

Cura: `|| [ -n "${..._dest:-}" ]` nos três loops (`:511`, `:546`, `:621`), no loop
novo do `_wbm_route_table_ok`, e no loop do denominador do próprio e2e histórico
(`H.1`) — o instrumento que deriva o denominador não pode carregar o defeito que
está checando. Semântica verificada em **bash 3.2.57** nos três casos que
importam (linha final sem newline, com newline, arquivo vazio): `read` limpa as
variáveis num EOF verdadeiro, então a guarda é falsa na passada seguinte e o
loop termina.

"Processar" não é "confiar": os validadores continuam recusando.

| controle | resultado |
|---|---|
| tabela sem newline final, pós-cura | 6 rotas / 6 linhas; `_wbm_route_src` da última = `rc=0` |
| RED (as 3 guardas removidas por plante ancorado, contagem asserida = 3) | 5 rotas / **5** linhas — `routes==rows` satisfeito por dois erros |
| linha final HOSTIL (`../../PWNED.md`) sem newline | `routes=1 rows=2 rc=2` — a lacuna fica visível para a pré-condição |
| linha final TRUNCADA (sem coluna transform) sem newline | `rc=2` fail-closed |
| `_wbm_route_table_ok` na tabela sem newline | aceita (a tabela está completa; falta só o byte) |

Pernas novas **S.9** (9 asserções) e **S.10** (11: o predicado de tabela em 5
formas inválidas + o exato-match do prior-digest com o RED do `grep` aposentado).

### Verificação (tudo executado na sombra)

| oráculo | resultado |
|---|---|
| `bash -n` (6 arquivos shell tocados) | OK nos 6 |
| `shellcheck -S warning -x` (6 arquivos) | **0** achados; histograma de códigos IDÊNTICO ao HEAD nos 3 pré-existentes |
| `test-ownership-verdict-unit.sh --quiet` | `PASS=63 FAIL=0 SKIPPED=2` (inalterado) |
| `test-manifest-delivery-route.sh` | **65 passed / 0 failed** (era 45/0 — +20) |
| `test-doctor-delivery-route.sh` | **66 passed / 0 failed** (era 59/0 — +7) |
| `test-upgrade-historical-adopter.sh` | **72 passed / 0 failed** (era 64/0 — +8) |
| paridade `--mode maintainer` | `IDENTICAL 530`, `STALE 0`, `MISSING_IN_B 0`, `UNCLASSIFIED 0`, `ONLY_IN_B_OUTSIDE_CLAUDE 0`, `MODE_DIFF 0`, **rc=0** |
| paridade `--mode user` | `IDENTICAL 488`, todas as classes fatais **0**, **rc=0** |
| `git status --porcelain` da sombra | conjunto IDÊNTICO ao do patch pré-rodada (nenhuma entrada nova/removida) |

Os dois modos de paridade seguem batendo célula a célula com `EXPECTED-BASELINE.txt`.

Delta desta rodada (contra a árvore que o revisor leu): `scripts/upgrade.sh`
+76/−46, `scripts/_framework_manifest_set.sh` +101/−4, `scripts/doctor.sh`
+29/−1, `scripts/tests/test-manifest-delivery-route.sh` +185/−0,
`scripts/tests/test-upgrade-historical-adopter.sh` +142/−1,
`scripts/tests/test-doctor-delivery-route.sh` +115/−0.

### Dívida declarada (fora do FILE ASSIGNMENT desta rodada)

1. **O ADR-194 §3 precisa da frase de escopo acima.** Sem ela o texto autoriza
   literalmente o que o F1 aponta, e o ADR é o que um leitor futuro consulta.
   O arquivo está fora do FILE ASSIGNMENT: a edição de um parágrafo tem de entrar
   no MESMO commit da cerimônia.
2. **`install.sh` não recebeu a regra do F1** — e não precisa hoje, porque lá o
   registro já vive DENTRO da função de entrega. Mas as duas metades da mesma
   regra passam a morar em arquivos diferentes; se `install.sh` ganhar um
   registro fora da entrega, a classe volta. Fora do FILE ASSIGNMENT.
3. **`_wbm_route_table_ok` tem UM consumidor** (`doctor.sh`). O `upgrade.sh` cobre
   o mesmo território pela pré-condição AC-9 (que conta rotas) e o gerador pelo
   seu próprio fail-closed, então não há lacuna medida — mas são três respostas
   para "a tabela serve?" em vez de uma. Consolidar é trabalho de wave, não de
   rodada de rail.
4. **A R.8 constrói um espelho do source com symlinks** dentro do `mktemp -d`
   porque `SOURCE_DIR` é derivado da LOCALIZAÇÃO do script — não há como exercer
   um `doctor.sh` alterado sem isso. `doctor.sh` não invoca `git` em lugar nenhum
   (medido: 0 hits), então o `.git` espelhado é inerte. Nenhuma escrita git foi
   feita em repositório de registro.
