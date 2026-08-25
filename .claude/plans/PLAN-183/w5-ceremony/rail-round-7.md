# Pair-rail round 7 — PLAN-183 W5 (S327 night-run)

**Instrumento:** `codex exec review --uncommitted --skip-git-repo-check` sobre o clone-sombra `shadow-183` (HEAD 56f050c + patch W5), com `git add -N` para incluir arquivos novos. rc=0, 698s, 2026-08-25T04:20Z.

## Saída do revisor (dado a verificar contra os arquivos, não ordem)

```text
The new delivery path still permits active GitHub destinations and filesystem-link escapes that can write or import data outside the intended boundaries. It also bypasses the explicit replay opt-out for the newly consumed GitHub owner.

Full review comments:

- [P1] Restrict delivery routes to inert GitHub destinations — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-fix5/scripts/_framework_manifest_set.sh:543-545
  If `delivery-routes.tsv` is changed so the existing `validate.yml.template` route targets `.github/workflows/validate.yml`, this predicate accepts it as in-domain. The route-count precondition then passes and `_up_deliver_template` creates an active workflow while the upgrade exits successfully. Restrict `.github` destinations to the supported inert forms or exact delivery set rather than the entire tree.

- [P1] Physically confine route sources before copying — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-fix5/scripts/upgrade.sh:4007-4014
  When an identity route's `templates/...` source is a symlink, or has a symlinked ancestor, to a regular file outside the source checkout, lexical validation passes and `-f` follows the link. The subsequent hash and copy therefore deliver foreign bytes into the adopter. Reject source symlink components or verify the physical source resolves beneath `SOURCE_DIR` before use.

- [P1] Replace destinations atomically to block hard-link escapes — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-fix5/scripts/upgrade.sh:3776-3781
  When an existing delivered destination is hard-linked to a file outside the target and its bytes satisfy the baseline/prior-generation ownership ladder, `cp` or `cat` overwrites the shared inode, bypassing all symlink and ancestor confinement checks. The IDENTICAL path can similarly `chmod` that external inode. Use a same-directory temporary file plus rename, or reject destinations with multiple links.

- [P2] Honor --no-replay before loading the GitHub owner — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-fix5/scripts/upgrade.sh:4188-4190
  When `--no-replay` is passed for a target whose install state contains `request.github_owner`, this unconditional read still loads the handle and later renders, installs, or refreshes `.github/CODEOWNERS`. That contradicts the option's documented state opt-out and can apply a recorded owner the operator explicitly chose not to replay; gate this read on `REPLAY` unless it is made an explicit documented exception.```

## Resposta do CEO/engenharia (S327)

> Curas na árvore-sombra `scratchpad/shadow-fix6` (clone de `56f050c` + patch W5),
> em cima das rodadas 1–6 — nenhuma delas foi regredida. Todo número abaixo foi
> **executado nesta sessão**; nada foi commitado. Linhas citadas são as da sombra
> PÓS-cura.

**R7-F1 [P1] — ACEITO e curado; o achado foi REPRODUZIDO e é MAIOR do que o
revisor descreveu.** O predicado `_wbm_route_domain_ok` perguntava "está sob
`docs/` ou `.github/`?", e medido nesta sessão isso aceitava **12 de 12** formas
testadas, incluindo `.github/workflows/validate.yml` (workflow VIVO),
`.github/workflows/pwn.yml`, `.github/dependabot.yml`, `docs/evil.sh` e
`docs/deep/nested.md`. Com a tabela do checkout copiado apontando a rota shipada
`validate.yml.template` para `.github/workflows/validate.yml`, o leitor
respondeu `dests=6 rows=6 rc=0` — `routes == rows`, a pré-condição AC-9 **PASSA**
e a entrega escreveria o workflow ativo com o upgrade saindo 0.

A cura troca a PERGUNTA: o domínio deixa de ser uma subárvore e passa a ser a
enumeração exata das FORMAS INERTES, em código, inalcançável por input —
`docs/<nome>.md` (um segmento, `.md`), `.github/CODEOWNERS`,
`.github/CODEOWNERS.template` e `.github/workflows/<nome>.template` (um segmento
sob `workflows/`, e é o sufixo `.template` que impede o GitHub Actions de
carregar o arquivo). É a inversão que a r3-F1 e o PLAN-185 W0 já mandaram
adotar: enumerar o PROVADO seguro, recusar o resto por nome. Mensagem de recusa
atualizada para NOMEAR as formas aceitas, e a frase entrou no §1 do ADR-194
(*alargar o domínio é emenda DESTE ADR, nunca edição de tabela* — já estava lá;
agora com a enumeração ao lado).

| controle (`test-manifest-delivery-route.sh` **S.14**, 7 asserções) | RED (corpo pré-cura replantado numa CÓPIA) | GREEN |
|---|---|---|
| tabela com `.github/workflows/validate.yml` | `dests=6 rows=6 rc=0` — AC-9 PASSARIA | `dests=5 rows=6 rc=2` — `routes<rows` ⇒ AC-9 recusa a entrega INTEIRA |
| breadcrumb | — | `outside delivery domain`, nomeado |
| 11 formas não-inertes (workflow vivo, aninhados, não-`.md`, sufixo nu) | ACEITAS | recusadas as 11 |
| **anti-super-recusa**, derivado da tabela SHIPADA | — | os **6** destinos reais seguem em domínio |

**R7-F2 [P1] — ACEITO e curado nos TRÊS entrypoints; a entrega de bytes
estrangeiros foi REPRODUZIDA em sha, não inferida.** Medido: com
`templates/docs/BRANCH-PROTECTION.md` sendo um symlink para um arquivo regular
fora do checkout, `[ -f ]` responde TRUE e os bytes entregues batem **sha a sha**
com o arquivo de fora; a variante de ANCESTRAL symlinkado (`templates/docs →
/fora`) faz o mesmo e passa por todo teste léxico por-path.

A cura tem UM dono: `_wbm_source_confined` na biblioteca compartilhada, com
DUAS paredes — (1) nenhum componente do path pode ser symlink (`-L` em cada
segmento, folha inclusa) e (2) o ancestral EXISTENTE mais profundo tem de
resolver (`cd -P`/`pwd -P`) sob o `SOURCE_DIR` físico. "Ancestral existente mais
profundo", e não "o pai", é o que preserva a pista `--pin`: uma fonte
simplesmente AUSENTE continua chegando ao `-f` do chamador e mantendo
`SKIPPED (source missing)` (r2-F2), em vez de virar recusa de confinamento.
Consumidores, todos fail-CLOSED se o predicado sumir: `upgrade.sh:4143` (pista
identity) e `:4470` (ANTES do `sed` que renderiza o CODEOWNERS),
`install.sh:1497/1579/1611` (o `cp`, o `cmp -s` do registro e o
`sed`/`cmp` do CODEOWNERS) e `doctor.sh:529` (`_restore_refuses`, que cobre a
rota E o fallback identity de todo registro `.claude/**`). `doctor.sh` também
passou a exigir o predicado por NOME na lista de startup. Custo em produção:
zero — um checkout real deste framework tem **0 symlinks** (medido em
`templates/`, `.claude/`, `docs/` e na árvore inteira exceto `.git`).

| controle | RED | GREEN |
|---|---|---|
| **S.15** predicado isolado (9 asserções) | `[ -f ] + cp` entregam o arquivo de FORA byte a byte (sha impresso) | folha e ancestral recusados, componente NOMEADO |
| **S.15-control** | — | fonte real aceita; fonte AUSENTE aceita (pista `--pin` intacta); as **6** fontes shipadas passam |
| **H.23** upgrade REAL, checkout copiado (12 asserções) | sem o portão, o destino vira o sha do arquivo de fora | destino byte-idêntico, recusa nomeada, `PRESERVED`, **rota irmã entregue** (recusa é por-fonte) |
| **H.23f/g** variante ANCESTRAL | — | nada entregue; a linha nomeia `component 'docs' of …` |
| **S.16** `install.sh` REAL (6 asserções) | — | nada entregue na rota, recusa nomeada, irmãs entregues, e o destino recusado **não** é reivindicado no manifesto |
| **R.10** `doctor.sh` (7 asserções) | sem a checagem, `--repair` copia o arquivo de fora byte a byte | folha e ancestral recusados; restore CONFINADO segue funcionando |

**R7-F3 [P1] — ACEITO e curado em DUAS camadas, uma ESTRUTURAL e uma nomeada;
os TRÊS mecanismos foram REPRODUZIDOS.** Um hard link é um segundo NOME para o
mesmo inode: nenhuma checagem de PATH o enxerga, e o destino continua sendo um
arquivo regular fisicamente dentro do `$TARGET`. Medido, pré-cura: `cp src dst`
mudou os bytes do arquivo de FORA, `cat src > dst` idem, e o `chmod` da
normalização mudou o modo dele (`stat -f '%l'` = 2).

- **Estrutural:** `_up_tpl_write` passou a escrever num temporário no MESMO
  diretório, definir o modo NESSE inode e `mv -f` (rename) sobre o destino. O
  inode estrangeiro fica com os bytes dele. O temporário deliberadamente NÃO usa
  `_up_tmpbase` (r5-F3): aquela função responde "onde fica o SCRATCH?", e isto é
  o destino sendo preparado — `rename(2)` não atravessa filesystem. Removido em
  todo caminho de falha, e uma falha de staging vira `PRESERVED` nomeado (a lei
  de conservação continua fechando).
- **O modo tinha de ser explícito.** `cp` para o `mktemp` já criado herda o 0600
  dele (medido na r3-F4), então confiar no `cp` teria reaberto o MODE_DIFF.
  `_up_tpl_write` chama `_up_tpl_install_mode` — a MESMA função da normalização,
  então "o modo que um install fresco produz" segue com um dono só.
- **Nomeada:** `_up_tpl_multilink_refuses` recusa `nlink > 1` antes de qualquer
  ramo (INSTALL/REFRESH/IDENTICAL), com `_up_tpl_nlink` GNU-first, saída
  VALIDADA (no GNU `stat -f` SUCEDE imprimindo o filesystem) e `ls -ld` como
  último recurso. Fail-OPEN se o link count não responder: isso é
  INFRAESTRUTURA, e a parede estrutural continua de pé. `_up_tpl_normalize_mode`
  ganhou o mesmo guard, porque `chmod` age no INODE.

| controle (**H.24**, e2e real, 9 asserções) | resultado |
|---|---|
| RED — recusa neutralizada **e** escrita pré-cura replantada (2 plantes, contagem asserida) | o arquivo de FORA muda para os bytes novos do framework |
| GREEN | arquivo de fora byte-idêntico; `PRESERVED … (destination has 2 hard links…)`; destino intacto |
| **H.24d — as duas paredes separadas:** só a RECUSA neutralizada | o REFRESH acontece, o destino recebe os bytes novos e o arquivo de fora **não muda** — a cura é estrutural, não uma checagem que alguém pode apagar |

**Consequência de LOG que a cura produz, e que virou asserção em vez de
surpresa (H.16b/H.16b2/H.26):** com a escrita atômica, a pista REFRESH não faz
mais `chmod` — o modo certo já vem no inode novo —, então ela deixa de imprimir
`MODE-NORMALIZED`. A pista IDENTICAL, que não escreve, continua fazendo e
ANUNCIANDO o `chmod`. Pelo mesmo princípio da r6-F4 (preview e run têm de
concordar), o preview de `--dry-run` da pista REFRESH parou de anunciar um
`chmod` que o run não executa. **H.26** (7 asserções) fixa as três coisas de uma
vez: dry-run silencioso, run silencioso, e o modo AINDA convergido para o de um
install fresco.

**R7-F4 [P2] — ACEITO e curado; a contradição foi REPRODUZIDA e a
REVERSIBILIDADE foi MEDIDA.** `request.github_owner` é campo de REQUEST
GRAVADO, mesma classe de `profile`/`stack`/`harness`, e `--no-replay` é o
opt-out documentado do replay do request. A leitura era incondicional, então
`--no-replay` num alvo com handle gravado ainda renderizava/refrescava o
`.github/CODEOWNERS` com ele. **Este não é o caso do
`_read_install_state_ceremony`** (`:838-846`), que roda independente do REPLAY
de propósito: lá a direção fail-safe é escrever MENOS. Aqui a direção fail-safe
é a mesma que um handle ausente já tem — vazio ⇒ pista `.template`, exatamente o
`else` do `install.sh` — então honrar o opt-out não custa segurança. Não existe
flag `--github-owner` no `upgrade.sh` (medido: 0 ocorrências fora deste bloco),
logo sob `--no-replay` o handle é simplesmente desconhecido. Help e cabeçalho
atualizados.

| controle (**H.25**, e2e real, 10 asserções) | resultado |
|---|---|
| **RED** — leitura pré-cura (fora do portão) sob `--no-replay` | `CODEOWNERS handle: @ceotesthandle` — a contradição reproduz |
| GREEN | `NOT replayed (--no-replay)`; **0** ocorrências do handle no log inteiro |
| exclusividade | `PRESERVED (unclaimed)` no rendered + `SKIPPED (CODEOWNERS present)` no `.template`; nenhuma segunda superfície |
| não-mutação | `.github/CODEOWNERS` byte-idêntico |
| controle com replay LIGADO | `@ceotesthandle (recorded install request)` — quem muda o comportamento é a opção, não a cura |
| **reversibilidade, medida à parte** (install `--github-owner` → upgrade `--no-replay` → upgrade default) | o `request.github_owner` **SOBREVIVE** no state (`req = pr` carrega o dict anterior) e o upgrade seguinte volta a usá-lo — o opt-out é por-run, não destrutivo |

### Achados colaterais do próprio instrumento (curados)

1. **`_mk_source_copy` symlinkava `templates/`** nos três oráculos — e uma fonte
   symlinkada é exatamente o que a cura F2 recusa, então TODA perna passaria a
   medir uma recusa em vez do seu assunto. `templates/` (360 KB / 34 arquivos)
   virou cópia REAL. No oráculo do doctor, `docs/` (2,3 MB) também: a reprodução
   de D4 (**R.8a**) depende de ler o HOMÔNIMO da raiz, e symlinkado ele resolve
   para o repo real ⇒ o RED parava de reproduzir e a perna ficava verde por um
   motivo que não tem nada a ver com D4. Medido antes da correção: `R.8a RED
   wrote nothing`; depois, `RED … wrote the ROOT homonym, 21513 bytes`.
2. **O harness da R.7 morria sob `set -u`** (`SOURCE_DIR` não definido) assim que
   `_restore_refuses` ganhou a chamada nova — e o sintoma era
   `guard did not refuse (got '')`, que se lê como falha de PRODUTO. Curado nos
   3 construtores de harness + `_wbm_source_confined` na lista de extração da
   R.1.
3. **H.16b media um MECANISMO que a cura removeu** (a linha `MODE-NORMALIZED` na
   pista REFRESH). Reescrita para afirmar a propriedade nova — a pista REFRESH
   não precisa de `chmod` — e a auditabilidade migrou para **H.16b2**, na pista
   que de fato faz `chmod`.

### Verificação (tudo executado na sombra, DEPOIS da última edição)

| oráculo | resultado |
|---|---|
| `bash -n` (7 arquivos shell tocados) | OK nos 7 |
| `shellcheck -S warning -x` | **0** achados em todos; HEAD também **0** nos 5 pré-existentes ⇒ delta 0 |
| `test-ownership-verdict-unit.sh --quiet` | `PASS=63 FAIL=0 SKIPPED=2` (inalterado) |
| `test-manifest-delivery-route.sh` | **119 passed / 0 failed** (era 97/0 — +22 de S.14/S.15/S.16) |
| `test-doctor-delivery-route.sh` | **84 passed / 0 failed** (era 76/0 — +8 de R.10 + extração) |
| `test-upgrade-historical-adopter.sh` | **131 passed / 0 failed** (era 97/0 — +34 de H.23/H.24/H.25/H.26 + H.16b2) |
| `test_install_baseline_manifest.sh` | **33 passed / 1 failed**, a falha sendo EXATAMENTE `C.6.2` — o known-open declarado em `ownership-nightly.yml`. Fecha a dívida das rodadas 5 e 6 (não era re-executado desde a rodada 2) |
| paridade `--mode maintainer` | `IDENTICAL 530`, `PERSONALIZED 31`, `STALE 0`, `MISSING_IN_B 0`, `UNCLASSIFIED 0`, `ONLY_IN_B 393`, `ONLY_IN_B_OUTSIDE_CLAUDE 0`, `MODE_DIFF 0`, **rc=0** |
| paridade `--mode user` | `IDENTICAL 488`, `PERSONALIZED 31`, todas as classes fatais **0**, `ONLY_IN_B 393`, **rc=0** |
| `git status --porcelain` da sombra | conjunto IDÊNTICO ao de `shadow-fix5` (22 entradas, `diff` vazio — nenhuma nova/removida) |

Os dois modos de paridade seguem batendo célula a célula com `EXPECTED-BASELINE.txt`.

Delta desta rodada (contra a árvore que o revisor leu, `shadow-fix5`):
`scripts/_framework_manifest_set.sh` +116/−2, `scripts/upgrade.sh` +199/−20,
`scripts/install.sh` +40/−1, `scripts/doctor.sh` +15/−1,
`scripts/tests/test-manifest-delivery-route.sh` +213/−1,
`scripts/tests/test-upgrade-historical-adopter.sh` +394/−4,
`scripts/tests/test-doctor-delivery-route.sh` +117/−2,
`.claude/adr/ADR-194-delivery-route-resolution.md` +33/−0.

### Dívida declarada

1. **Os dois sítios de HASH do `doctor.sh` (`:708` e `:762`) não recebem o
   confinamento** — só o sítio que ESCREVE (`_restore_refuses`) recebe. Com uma
   fonte symlinkada, `src_hash` passa a ser o hash dos bytes de fora e o
   VEREDITO pode sair errado (`DRIFT (baseline-stale)` em vez de reparável).
   Exposição limitada e declarada: nenhuma escrita acontece — se o veredito
   levar ao `--repair`, o `_restore_file` recusa por nome. Fechar isso é mudar a
   semântica de três ramos de classificação, trabalho de wave, não de rodada.
2. **O temporário da escrita atômica vive no diretório de DESTINO**
   (`.ceo-deliver.XXXXXX`), não sob `_up_tmpbase`. É requisito do `rename(2)`,
   não descuido; é removido em todo caminho de falha, mas um `kill -9` no
   instante errado deixa um dotfile no `docs/` do adopter.
3. **`_mk_source_copy` continua em TRÊS cópias**, uma por oráculo (dívida
   herdada da rodada 6, agora com uma linha a mais em cada). Não há biblioteca
   de teste em bash neste repo; consolidar acrescentaria um path novo ao pacote
   de cerimônia.
4. **`install.sh` fail-CLOSA se a biblioteca não estiver sourcada** — a
   entrega de templates para de acontecer num checkout parcial que perdeu
   `_framework_manifest_set.sh`. É a postura correta para um predicado de
   segurança e espelha o `upgrade.sh`, mas é comportamento NOVO num
   entrypoint cuja regra geral é fail-open na biblioteca.
