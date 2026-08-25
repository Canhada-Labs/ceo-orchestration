# Pair-rail round 3 — PLAN-183 W5 (S327 night-run)

**Instrumento:** `codex exec review --uncommitted --skip-git-repo-check` sobre o clone-sombra `shadow-183` (HEAD 56f050c + patch W5), com `git add -N` para incluir arquivos novos. rc=0, 826s, 2026-08-24T23:33Z.

## Saída do revisor (dado a verificar contra os arquivos, não ordem)

```text
The delivered-template list can expand attacker-influenced glob patterns into unrelated framework-owned manifest entries, creating a potential deletion path. The patch also records failed upgrades as successful and introduces CI and parity gaps that can conceal regressions.

Full review comments:

- [P1] Prevent glob expansion in delivered-template paths — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-fix/scripts/_framework_manifest_set.sh:205-205
  `FMS_DELIVERED_TEMPLATES` is treated as untrusted, but this unquoted `for` performs pathname expansion after newline splitting. A destination such as `docs/*`, which `_wbm_route_relpath_ok` accepts, expands to every matching file in the caller's working directory; from the repo root it yields 125 docs paths. The generator can then baseline unrelated adopter files as framework-owned, allowing a manifest-honoring uninstall to delete them. Consume the list with a quoted `while read` loop or reject glob metacharacters, consistent with the fail-closed input rule in [AGENTS.md:23](AGENTS.md#L23).

- [P2] Mark failed route delivery in the persisted upgrade state — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-fix/scripts/upgrade.sh:4632-4638
  When the route table yields zero or rejected rows, this branch exits 3 only after `_write_upgrade_state` has persisted `result.upgrade_succeeded: true` and the script has printed `Upgrade complete`. Thus a missing or poisoned table leaves a durable audit record claiming success despite the failed upgrade. Handle the flag before writing state/banner output, or persist an explicit partial-failure result.

- [P2] Track the exact known-open assertion instead of C.6 — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-fix/.github/workflows/ownership-nightly.yml:149-151
  The gate reduces failures to their second whitespace-delimited field and deduplicates them, but the suite has nine distinct `bad "C.6 ..."` sites. If another C.6 assertion regresses while the known failure remains—or the known failure disappears while a different C.6 assertion fails—`OBSERVED` remains `C.6` and nightly reports success despite a changed failure set. Assign stable unique IDs or compare the exact expected assertion.

- [P2] Normalize modes when refreshing existing template files — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-fix/scripts/upgrade.sh:3751-3754
  For an existing destination, both `cat >` and ordinary `cp` preserve the destination inode's mode rather than reproducing fresh-install permissions; the `IDENTICAL` branch also performs no mode check. If a template's executable bit changed between framework generations, an upgrade refreshes the bytes but retains the old bit, leaving the parity classifier's fatal `MODE_DIFF` even though the upgrade reports success. Explicitly compare and normalize the delivered mode.

- [P2] Treat dangling CODEOWNERS symlinks as present — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-fix/scripts/upgrade.sh:4127-4127
  When a historical adopter has no recorded owner and `.github/CODEOWNERS` is a dangling symlink, `-e` is false, so this branch installs `.github/CODEOWNERS.template` while leaving the CODEOWNERS path in place. That violates the stated mutual-exclusivity invariant and can produce two active CODEOWNERS surfaces if the symlink target later appears. Include `-L` in the presence check.```

## Resposta do CEO/engenharia (S327)

> Curas na árvore-sombra `scratchpad/shadow-fix2` (clone de `56f050c` + patch W5),
> em cima das curas das rodadas 1 e 2 — nenhuma delas foi regredida. Todo número
> abaixo foi **executado nesta sessão**; nada foi commitado. Linhas citadas são as
> da sombra PÓS-cura.

**R3-F1 [P1] — ACEITO e curado em QUATRO camadas; o número do revisor foi
REPRODUZIDO exatamente.** Com `FMS_DELIVERED_TEMPLATES='docs/*'` e o repo root
como cwd, `_framework_target_entries` emitiu **125** relpaths `docs/…` — cada um
confinado, relativo e legítimo, e cada um um arquivo do ADOPTER gravado como
framework-owned. O `for` sem aspas fazia word-splitting por newline e **depois**
expansão de pathname, então o predicado de forma via `docs/ACCELERATORS.md`, não
`docs/*`.
- (a) **Sem expansão de pathname em lugar nenhum do enumerador** —
  `_framework_manifest_set.sh:127` liga `set -f` no topo do brace group (com
  save/restore, porque a subshell do pipeline é verdade *hoje*, não uma garantia
  de refactor); word-splitting continua ligado, que é o que `FMS_PROFILE_PARTS`
  precisa.
- (b) **Consumo com `while read` citado** (`:225`), substituindo o `for`+IFS.
- (c) **Metacaracteres de glob rejeitados pelo predicado** (`:480-483`: `*`, `?`,
  `[`, `]`), independente da ordem em que alguém reintroduza uma expansão.
- (d) **WHITELIST — a cura que não depende de imaginar a próxima forma insegura.**
  `_wbm_route_dest_declared` (`:576`) aceita uma entrada só se ela for
  byte-igual a um `dest` de uma linha **já validada** da tabela compartilhada;
  qualquer outra coisa é recusa NOMEADA e não entra. Isto é a inversão que a §5
  do CLAUDE.md já registra para o PLAN-185 W0 (enumerar o PROVADO seguro), e é
  deliberadamente arquitetural: as rodadas 1 e 2 curaram esta classe **enumerando
  o proibido** (absoluto, `..`, backslash) e a rodada 3 achou a forma seguinte.
  Fail-CLOSED por construção: sem tabela, a lista de destinos é vazia e nada é
  gravado. A mesma disciplina foi aplicada nos DOIS sítios que exportam a lista —
  `install.sh:1524` (`_append_delivered_template`) e `upgrade.sh:3919`
  (`_up_tpl_register`), ambos guardados por `command -v` porque a biblioteca é
  sourcada condicionalmente; o **piso** fail-closed é o gerador, que vive no
  mesmo arquivo do leitor e sempre pode consultar a tabela.

Controles (novos: `test-manifest-delivery-route.sh` S.8, 11 asserções):

| controle | RED (pré-cura) | GREEN (pós-cura) |
|---|---|---|
| `docs/*` do repo root | **125** entradas `docs/` gravadas | **0**, recusa nomeada em stderr |
| predicado, 4 metacaracteres | ACEITOS os 4 | recusados os 4 |
| `docs/adopter-owned.md` (confinado, NÃO declarado) | entra no conjunto | recusado, nomeando path + tabela |
| sem tabela + destino REAL | gravado (fail-open) | não gravado (fail-closed) |
| oráculo, pré-cura completa | `36 passed / 9 failed` | `45 passed / 0 failed` |
| oráculo, **só** a whitelist neutralizada | `42 passed / 3 failed` | idem |
| controle de escopo | — | os 6 destinos declarados seguem gravados |

A penúltima linha é o que prova **independência de camada**: com a whitelist
removida e o resto intacto, as 3 pernas dela ficam vermelhas e as de glob
continuam verdes — cada parede segura algo que as outras não seguram.

**R3-F2 [P2] — ACEITO e curado; a mentira durável foi REPRODUZIDA em bytes.**
Verificado por leitura e por execução: `_write_upgrade_state` rodava ANTES da
saída diferida e gravava `result.upgrade_succeeded: true` fixo, e o banner
`Upgrade complete.` era incondicional. Cura:
- `upgrade.sh:3645` `_UP_DELIVERY_PRECONDITION_REASON` (token por sítio:
  `zero-routes`, `rejected-route-row`, `unclassified-route`) — "falhou" sozinho
  não é triável depois que o scrollback some;
- `:4519` o flag e o motivo entram nos `pairs` **antes** de qualquer escrita;
  `:4609` são lidos antes de o registro ser montado; `:4633`
  `upgrade_succeeded` passa a ser DERIVADO e `result.route_delivery` carrega
  `ok` ou `failed(<motivo>)`;
- `:4744` o banner passa a ser derivado do MESMO flag do rc.

| controle (tabela envenenada, e2e real) | RED (pré-cura) | GREEN (pós-cura) |
|---|---|---|
| rc | 3 | 3 |
| banner | `Upgrade complete.` | `Upgrade INCOMPLETE` |
| registro persistido | `upgrade_succeeded=True route_delivery=None` | `upgrade_succeeded=False route_delivery=failed(rejected-route-row)` |
| **controle de escopo** — upgrade saudável | — | rc=0, `Upgrade complete.`, `True / ok` |

Pernas novas **H.13f/g/h** no e2e histórico (reusam a fixture envenenada da
H.13: nenhum upgrade extra). Nenhuma chave nova quebra
`test_install_state_replay.sh` — ele lê `result.install_succeeded` (lado
install), medido: `grep` = 1 sítio, `scripts/tests/test_install_state_replay.sh:164`.

**R3-F3 [P2] — ACEITO e curado; o ponto cego foi REPRODUZIDO.** Verificado: o
gate reduzia toda falha ao 2º campo e a suíte tem **nove** sítios `bad` distintos
na família C.6 (linhas 374/384/387/391/398/402/412/415/418). Cura:
- cada sítio ganhou um id **estável e único** `C.6.<n>` em ordem de arquivo; o
  cabeçalho §ASSERTION IDS declara que id é RÓTULO, nunca ordenação — um sítio
  novo pega o próximo número livre e um id existente jamais é renumerado ou
  reusado, senão o conjunto declarado passa a significar outra coisa em silêncio;
- `ownership-nightly.yml:160` declara `EXPECTED="C.6.2"` — **medido**, não
  suposto: a suíte inteira rodou nesta sessão e a única falha é
  `C.6.2 root PROTOCOL.md NOT backed up without a manifest`;
- **anti-rot:** `test_install_baseline_manifest.sh:97` acrescenta a asserção
  `C.6.0` (barata, roda antes das pernas caras) que falha se aparecer um sítio
  sem id ou um id duplicado — é a premissa do gate defendida por um teste, não
  por um comentário.

Gate simulado com a lógica EXTRAÍDA do YAML (só duas substituições, ambas de
caminho/invocação; nenhuma linha de lógica reescrita):

| perna | veredito |
|---|---|
| (i) saída known-open exata, rc=1 | **GREEN** |
| (ii) um C.6 DIFERENTE falha (`C.6.7`), o known-open passa | **RED** — `declared [C.6.2], observed [C.6.7]` |
| (iii) nenhuma falha, rc=0 | **RED** (encolhimento) |
| (iv) log truncado sem `RESULT:` | **RED** |
| (v) `C.6.2` falhando com rc=0 | **RED** (incoerência) |
| (vi) **gate PRÉ-CURA** (`EXPECTED="C.6"`) no cenário (ii) com ids nus | **rc=0, `OK: … matches the declared known-open set [C.6]`** |

A linha (vi) é o achado literal: o nightly reportava sucesso num run cujo
conjunto de falhas MUDOU. E a `C.6.0`: verde no arquivo real (10 ids, todos
únicos), vermelha com um sítio nu plantado (`bare_sites=1`) e vermelha com um id
duplicado (`idded=11 unique=10`).

**R3-F4 [P2] — ACEITO e curado nas DUAS pernas; a semântica foi MEDIDA, não
lembrada.** Medido nesta sessão: `cp src dst` com `dst` pré-existente em 0755
deixa **0755**; o mesmo `cp` para um destino inexistente dá **644** (o modo da
FONTE); e o redirecionamento `>` dá 0666&~umask. Logo `REFRESHED` conserva o bit
velho e `IDENTICAL` — que não escreve nada — nunca converge, com o `MODE_DIFF`
FATAL do classificador de paridade (`_parity_classify.py:203`, bit de execução)
de pé sobre um run que reporta sucesso.
Cura em `upgrade.sh:3781/3796/3813` — `_up_tpl_stat_mode` (GNU-first, BSD
fallback e **saída validada**, porque no GNU `stat -f` SUCEDE imprimindo o
filesystem), `_up_tpl_install_mode` (por transform: identity ⇒ o modo da FONTE,
espelhando `install.sh:1494`; rendered ⇒ `0666 & ~umask`, espelhando o
redirecionamento de `install.sh:1602` — a fonte NÃO serve nessa pista, é o
buffer `mktemp` 0600, que é justamente por que `_up_tpl_write` usa `cat >` ali)
e `_up_tpl_normalize_mode`, chamado em `:4010` (IDENTICAL) e `:4040` (REFRESHED).
Uma linha nomeada por path (`MODE-NORMALIZED (755 -> 644): <path>`); silencioso
quando já está correto; fail-OPEN se o `stat` não responder (isso é
infraestrutura, não input).

| controle | RED (normalize neutralizado) | GREEN |
|---|---|---|
| harness de funções extraídas, REFRESHED | `refresh.md mode=755` | `644` + linha `MODE-NORMALIZED` |
| idem, IDENTICAL | `ident.md mode=755` | `644` + linha |
| e2e H.16 (fixture (a), drift plantado nas duas pistas) | — | modo de volta ao de um install fresco nas duas |

O e2e compara contra o modo de um **install fresco lido da própria fixture**,
nunca contra um `0644` hardcoded, então a asserção sobrevive a qualquer umask; e
ele aborta como `scaffold` se o install já entregar bit de execução (aí o drift
plantado seria indistinguível do normal).

**R3-F5 [P2] — ACEITO e curado; as duas metades da exclusividade passaram a
perguntar a MESMA coisa.** Verificado e reproduzido num upgrade real: com
`.github/CODEOWNERS` sendo um symlink pendurado, `-e` responde falso, a rota
renderizada saía `SKIPPED (branch not taken)` e a rota `.template` **INSTALAVA** —
duas superfícies ativas no instante em que o alvo do link aparecer, e
permanentemente (o próximo upgrade acha o template IDENTICAL e nunca o remove).
Cura: `upgrade.sh:3845` `_up_codeowners_present` — UMA definição
(`-e || -L`), consultada pelos DOIS ramos (`:4194` renderizado, `:4246`
`.template`), com mensagem específica de symlink em `:4248`. Dois ramos
perguntando a mesma coisa de dois jeitos é como esta classe nasceu (rodada 1 F5),
então a pergunta ganhou exatamente uma implementação.

| controle (e2e real, fixture pendurada) | RED (pré-cura `-e`) | GREEN |
|---|---|---|
| `.github/CODEOWNERS.template` | `INSTALLED` | ausente |
| superfícies CODEOWNERS ativas | **2** | **1** |
| linha no log | `SKIPPED (branch not taken)` + `INSTALLED` | `PRESERVED (unclaimed)` + `SKIPPED (CODEOWNERS path present as symlink)` |

Perna nova **H.17** (5 asserções), incluindo que nada foi escrito ATRAVÉS do link
e que a lei de conservação segue fechando 6 de 6.

### Achado colateral do próprio instrumento (curado)
`_up_tpl_install_mode` e `_up_tpl_normalize_mode` nasceram com comentário na
linha da definição. Os oráculos deste repo extraem funções POR NOME com
`sed -n '/^nome() {$/,/^}$/p'`, e um comentário ali **esvazia o fragmento em
silêncio** — foi assim que o primeiro harness do F4 falhou. Os cabeçalhos foram
normalizados para `nome() {` puro, com o motivo escrito ao lado.

### Verificação (tudo executado na sombra)

| oráculo | resultado |
|---|---|
| `bash -n` (7 arquivos shell tocados/vizinhos) | OK nos 7 |
| `shellcheck -S warning -x` | **0** achados em todos; histograma IDÊNTICO ao HEAD nos pré-existentes |
| `yaml.safe_load` dos 2 workflows | OK — nightly 10 steps/timeout 150, smoke 23/68 |
| SHA-pins (`uses:`) vs HEAD | **byte-idênticos** nos dois workflows |
| `test-ownership-verdict-unit.sh --quiet` | `PASS=63 FAIL=0 SKIPPED=2` (inalterado) |
| `test-manifest-delivery-route.sh` | **45 passed / 0 failed** (era 34/0 — +11 do F1) |
| `test-upgrade-historical-adopter.sh` | **64 passed / 0 failed** (era 52/0 — +12 do F2/F4/F5) |
| `test-doctor-delivery-route.sh` | **59 passed / 0 failed** (inalterado) |
| `test_install_baseline_manifest.sh` | **33 passed / 1 failed**, a falha sendo exatamente `C.6.2` (era 32/1; +1 é a `C.6.0` nova) |
| paridade `--mode maintainer` | `IDENTICAL 530`, `STALE 0`, `UNCLASSIFIED 0`, `MISSING_IN_B 0`, `ONLY_IN_B_OUTSIDE_CLAUDE 0`, `MODE_DIFF 0`, **rc=0** |
| paridade `--mode user` | `IDENTICAL 488`, todas as classes fatais **0**, **rc=0** |

Os dois modos de paridade seguem batendo célula a célula com `EXPECTED-BASELINE.txt`.

### Dívida declarada (fora do FILE ASSIGNMENT desta rodada)

1. **As 6 pernas do gate known-open ainda não são um teste rastreado.** A
   simulação acima extrai a lógica do YAML e roda 6 cenários, mas ela vive nesta
   sessão. A casa certa é `scripts/tests/test-ownership-nightly-gate.sh` (que já
   é o "Gate positive control" do mesmo workflow) e esse arquivo não está no
   FILE ASSIGNMENT desta rodada. A `C.6.0` cobre a metade que importa mais — a
   PREMISSA (ids únicos) — de dentro da suíte, e essa sim é rastreada.
2. **`EXPECTED="C.6.2"` continua inline no workflow**, não num arquivo ao lado de
   `ownership-expected-reds.txt` (dívida herdada da rodada 2, agora com um id
   mais preciso mas na mesma segunda cópia de verdade).
3. **`C.6.2` segue medido só no Darwin.** Se o ubuntu passar nele, o step fica
   VERMELHO na primeira noite nomeando a diferença — modo de falha pretendido.
4. **A whitelist do F1 é consultada por chamada** (`_wbm_route_dest_declared`
   relê a tabela de 6 linhas por entrada). Deliberado: cache no chamador seria
   uma segunda cópia da verdade com janela de staleness, e o custo medido é
   irrelevante. Se a tabela crescer uma ordem de grandeza, isto vira medição.
