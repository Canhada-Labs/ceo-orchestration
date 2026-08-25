# Pair-rail round 2 — PLAN-183 W5 (S327 night-run)

**Instrumento:** `codex exec review --uncommitted --skip-git-repo-check` sobre o clone-sombra `shadow-183` (HEAD 56f050c + patch W5), com `git add -N` para incluir arquivos novos. rc=0, 642s, 2026-08-24T22:29Z.

## Saída do revisor (dado a verificar contra os arquivos, não ordem)

```text
The patch lacks required canonical-edit approval evidence and breaks docs/.github delivery for supported historical `--pin` references. It also bypasses transform validation for CODEOWNERS and leaves two changed regression suites unwired.

Full review comments:

- [P1] Add the Owner-signed sentinel before landing — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-fix/.claude/adr/ADR-194-delivery-route-resolution.md:8-8
  These edits touch several canonical-guarded surfaces, but the referenced `.claude/plans/PLAN-183/wave-w5-approved.md` and its signature are absent. Landing without that evidence violates the repository's guarded-surface requirement and should be rejected by the canonical-edit gate ([AGENTS.md:84-91](AGENTS.md#L84-L91), [AGENTS.md:108-116](AGENTS.md#L108-L116)).

- [P1] Keep delivery routes available during pinned upgrades — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-fix/scripts/upgrade.sh:3878-3879
  For any `--pin` predating commit `aaf32c7` (including `v1.3.0`), the earlier checkout removes `scripts/delivery-routes.tsv` after the current helper was sourced. This enumeration therefore yields zero routes, the new block reports a precondition error but the upgrade still exits successfully, and all pinned docs/.github deliveries are omitted. Snapshot the route data before checkout or otherwise make it available throughout pinned execution.

- [P2] Validate the CODEOWNERS transform before rendering — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-fix/scripts/upgrade.sh:3971-3972
  If the CODEOWNERS row's transform is empty, misspelled, or changed to another transformation, `_wbm_route_src` returns rc=2, but this branch ignores `_up_rc`, reparses the source with `awk`, and always applies the OWNER_HANDLE substitution. Malformed or future transform values are therefore accepted instead of failing closed and can produce bytes contrary to the shared route table.

- [P2] Run the changed delivery regression suites in CI — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-fix/.github/workflows/smoke-install.yml:300-300
  This workflow wires the new manifest oracle, but no workflow step invokes the substantially changed `scripts/tests/test-doctor-delivery-route.sh` or `scripts/tests/test_install_baseline_manifest.sh`, and neither test is included in the path filters. Consequently the new doctor restore/confinement cases and C.8 install/upgrade manifest assertions never execute in PR or push CI.```

## Resposta do CEO/engenharia (S327)

> Curas na árvore-sombra `scratchpad/shadow-fix` (clone de `56f050c` + patch W5),
> em cima das curas da rodada 1 — nenhuma delas foi regredida. Todo número abaixo
> foi **executado nesta sessão**; nada foi commitado. Linhas citadas são as da
> sombra PÓS-cura.

**R2-F1 [P1] — BY-DESIGN, sem mudança de código.** É o F1 da rodada 1 outra vez,
pela mesma razão: a ratificação NÃO está ausente. `ls -la` no repo VIVO mostra
`.claude/plans/PLAN-183/wave-w5-approved.md` (6.330 b, 2026-08-24 17:26). O
revisor lê o clone-sombra, onde os untracked do diretório de plano não existem —
artefato do escopo do clone, não do patch. O fluxo segue `OWNER-S327-SIGN.sh` →
`OWNER-S327-LAND.sh` (G1/G5), e o ADR-194 vira `ACCEPTED` no land.

**R2-F2 [P1] — ACEITO e curado nas DUAS metades; o defeito foi REPRODUZIDO num
`--pin v1.3.0` real, não inferido.** Mecanismo confirmado por leitura:
`FMS_DELIVERY_ROUTES_TSV` resolve em `_framework_manifest_set.sh:407` no momento
do SOURCE (`upgrade.sh:108`), mas os leitores dão `stat` no path em tempo de
CHAMADA (`:466`/`:505`/`:520`), ~3.300 linhas depois — e o checkout do `--pin`
(`upgrade.sh:659+`) fica no meio. `git show v1.3.0:scripts/delivery-routes.tsv`
responde *"exists on disk, but not in 'v1.3.0'"*.
- (a) **Snapshot** (`upgrade.sh:641-656`): os BYTES da tabela são copiados para
  um tempfile ANTES de qualquer checkout, e o leitor passa a apontar para ele
  pelo override que já é dele (nenhum segundo override foi criado). Reapeado no
  `_upgrade_cleanup` (`:607`). Tomado SEMPRE, não só sob `--pin`: a propriedade
  desejada é "a lista de destinos não muda debaixo do run". As FONTES continuam
  vindo da árvore PINADA — que é o que `--pin` significa —, e uma fonte ausente
  no pin é nomeada POR PATH (`SKIPPED (source missing at pin <ref>)`,
  `:3864` e `:4092`), nunca sumida em silêncio.
- (b) **Fail-closed no rc** (`:3640`, `:3988`, `:4000`, `:4178`, `:4638`): a
  pré-condição falha agora ALCANÇA o chamador. Escolha declarada: **saída
  DIFERIDA (`exit 3`), não `exit` imediato** — o bloco fica ~500 linhas antes do
  fim e o purge de mis-install, a reescrita C.7 do manifesto e o
  `_write_upgrade_state` ainda precisam rodar; abortar ali deixaria o alvo
  meio-atualizado, estritamente pior que o fail-open sendo curado. Então o resto
  completa, a linha de sumário passa a carregar `precondition=FAILED` (para o
  consumidor que só lê log) **e** o processo sai 3 (documentado em `--help`,
  §Exit codes). A mesma propriedade foi estendida à lei de conservação
  (`:4178`), que era a MESMA forma: erro nomeado com rc=0.

Controles positivos, todos executados (e2e real, source-repo descartável
construído de dois `git archive` dentro de `mktemp -d`):

| controle | RED (plantado) | GREEN (pós-cura) |
|---|---|---|
| `--pin v1.3.0`, entrega de rotas | `routes enumerated: 0 of 0` | `6 of 6` |
| idem, sumário | `precondition=FAILED` | `installed=0 refreshed=3 identical=2 preserved=0 skipped=1` |
| idem, veredito por rota | nenhum | 6 vereditos, 3 REFRESHED pela escada `recorded baseline digest` |
| tabela envenenada (H.13), rc | `0` (fail-open) | `3` |

O plante é cirúrgico: remove SÓ o hand-off `FMS_DELIVERY_ROUTES_TSV="$_UP_ROUTES_SNAPSHOT"`
(âncora conferida por contagem, aborta se ≠1), deixando o resto idêntico —
então o RED isola a metade (a). A metade (b) é isolada pela H.13d, que assere o
rc **por valor**: `0` é nomeado como o fail-open regredindo, e qualquer outro rc
vira `scaffold` em vez de passar por acidente.

Pernas novas: **H.14** (6 asserções — o pin é DERIVADO, nunca hardcoded: a tag de
release mais nova que NÃO carrega `scripts/delivery-routes.tsv`, o que continua
sendo a tag certa depois do próximo release; se nenhuma existir é `scaffold`,
nunca passe vacuoso) e **H.13d/H.13e**.

**R2-F3 [P2] — ACEITO e curado; a corrupção foi REPRODUZIDA em bytes.**
Verificado: o ramo ignorava `_up_rc`, re-parseava a linha só pela FONTE e
aplicava a substituição sempre. Cura em `upgrade.sh:4040-4071`: as DUAS colunas
saem da linha da tabela e o veredito do leitor é consultado — só `rc=2` **e** o
literal exato que a tabela declara (`_UP_CO_TRANSFORM_SUPPORTED`, `:4031`)
renderizam; `rc=0` (a tabela declara `identity` para um destino que este ramo
RENDERIZA) e `rc=1` (linha sumiu entre a enumeração e aqui) são recusas
nomeadas, contadas como `skipped`, sem escrever nada.

Controle positivo com a linha hostil `.github/CODEOWNERS` →
`src=templates/docs/rotation-log.md`, `transform=substitute:{{OWNER_HANDLE}}-NOT-A-REAL-TRANSFORM`
(relpaths confinados, então `routes==rows==6` e a pré-condição do H.13 NÃO
dispara — a recusa sob teste é a por-rota):

| | RED (gate neutralizado) | GREEN (pós-cura) |
|---|---|---|
| linha no log | `REFRESHED (recorded baseline digest): .github/CODEOWNERS` | `SKIPPED (unsupported transform 'substitute:{{OWNER_HANDLE}}-NOT-A-REAL-TRANSFORM'): … renders only 'substitute:{{OWNER_HANDLE}}'; route reader rc=2 — nothing written` |
| sha do CODEOWNERS depois | `0ab61d16…` = **sha de `rotation-log.md`** | `e815e43c…` = **idêntico ao de antes** |
| sumário | `refreshed=1 … skipped=1` | `refreshed=0 … skipped=2` (6 vereditos) |

Isto é literalmente o *"bytes contrary to the shared route table"* do achado:
pré-cura o `.github/CODEOWNERS` do adopter foi SOBRESCRITO com o conteúdo de
outro template, exit 0. Perna nova **H.15** (3 asserções), com a mensagem
asserida POR VALOR do transform para que não envelheça.

**R2-F4 [P2] — ACEITO e curado; e o terceiro caso da mesma classe.** Verificado:
`grep -r <nome> .github/` = **0** para os DOIS arquivos.
- `test-doctor-delivery-route.sh` → **per-PR** em `smoke-install.yml`: step
  `:335` (`if: always()`, mesma razão §9.8 do irmão D3) + a entrada nas **duas**
  listas `paths:` (`:45` e `:126`). 104 s / 59 asserções — barato para per-PR.
  É o instrumento que detecta o vazamento D4 (o `.github/CODEOWNERS` VIVO do
  mantenedor copiado para a árvore do adopter) e não rodava em lugar nenhum.
- `test_install_baseline_manifest.sh` → **nightly** em `ownership-nightly.yml`
  (`:138`), não per-PR: 692 s medidos = 22-45 min de CI no fator 2-3x deste
  repo, sobre um job já orçado em 68. É o mesmo argumento de sizing que pôs o
  `test_install_state_replay.sh` nesse workflow (re-pass rc.4 t7 P2).
- **Conjunto KNOWN-OPEN, não `continue-on-error`.** MEDIDO na árvore W5:
  **32 passed / 1 failed**, a falha sendo `C.6 root PROTOCOL.md NOT backed up
  without a manifest` — **PRÉ-EXISTENTE e não desta wave** (o patch W5 acrescenta
  95 linhas nesse arquivo e toca ZERO linhas de C.6). Ligar como `bash …` puro
  pintaria o nightly de vermelho toda noite por um defeito que ele não causou —
  é assim que um canal é treinado a ser ignorado. Então o step DECLARA o
  conjunto que falha e reprova em QUALQUER diferença: falha nova E falha que
  sumiu (mesmo contrato do `ownership-expected-reds.txt`; encolher é mudança,
  nunca sucesso), mais rc fora de {0,1} e log sem `RESULT:`.
- **O gate foi provado antes de ser confiado** (5 pernas, lógica idêntica à do
  step): log real (32/1, C.6) ⇒ GREEN; falha NOVA (`C.9`) ⇒ RED; C.6 CORRIGIDO
  (nenhum FAIL) ⇒ RED por encolhimento; log truncado sem `RESULT:` ⇒ RED;
  `C.6` presente com rc=0 ⇒ RED por incoerência.
- Orçamentos, MEDIDOS e não extrapolados da contagem: `smoke-install.yml`
  **58 → 68** (e2e histórico 552 s → 650 s com 11 → 13 upgrades + 7 s de build
  do source pinado, e +104 s do oráculo do doctor ⇒ +7-10 min de CI);
  `ownership-nightly.yml` **110 → 150**. SHA-pins byte-idênticos ao HEAD nos
  dois arquivos (`diff` das linhas `uses:` = vazio).

### Verificação (tudo executado na sombra)

| oráculo | resultado |
|---|---|
| `bash -n` (`upgrade.sh`, e2e histórico) | OK nos dois |
| `shellcheck -S warning -x` (idem) | **0** achados; histograma de códigos IDÊNTICO ao HEAD |
| `test-upgrade-historical-adopter.sh` | **52 passed / 0 failed**, 650 s (era 41/0 — +11 asserções) |
| paridade `--mode maintainer` | `IDENTICAL 530`, `STALE 0`, `UNCLASSIFIED 0`, `MISSING_IN_B 0`, `ONLY_IN_B_OUTSIDE_CLAUDE 0`, `MODE_DIFF 0`, **rc=0** |
| paridade `--mode user` | `IDENTICAL 488`, todas as classes fatais **0**, **rc=0** |
| `test-manifest-delivery-route.sh` | **34 passed / 0 failed** (inalterado) |
| `test-doctor-delivery-route.sh` | **59 passed / 0 failed**, 104 s (inalterado, medido antes E depois) |
| `test_install_baseline_manifest.sh` | **32 passed / 1 failed** (só C.6, pré-existente), 692 s |
| YAML dos 2 workflows | `yaml.safe_load` OK; smoke 23 steps/timeout 68, nightly 10 steps/timeout 150 |
| controle do gate known-open | 1 GREEN + 4 RED, como desenhado |

Os dois modos de paridade seguem batendo célula a célula com `EXPECTED-BASELINE.txt`.

### Dívida declarada (fora do FILE ASSIGNMENT desta rodada)

1. **`scripts/tests/test_install_baseline_manifest.sh:19-33` ficou MENTIROSO.** O
   cabeçalho declara *"this suite is OPERATOR-LOCAL / landing-gate only. NO
   workflow executes it (grep .github/ for this filename: zero hits)"* — e o
   próprio cabeçalho manda: *"If that ever changes, update THIS header: the
   declaration is what a census reads."* Com o F4 curado a declaração é FALSA.
   O arquivo não está no FILE ASSIGNMENT desta rodada, então **não foi tocado**:
   a edição de uma linha tem de entrar no MESMO commit da cerimônia. Precedente
   idêntico e já stale: a nota de coleção em `.github/workflows/validate.yml:879`
   chama `test_install_state_replay.sh` de landing-gate-only, e ele roda no
   nightly desde o rc.4 t7 P2.
2. **`EXPECTED="C.6"` mora inline no workflow**, não num arquivo rastreado ao
   lado de `ownership-expected-reds.txt` — criar arquivo novo está fora do
   escopo desta rodada. É uma segunda cópia de verdade, pequena e declarada.
3. **C.6 foi medido só no Darwin.** Se o ubuntu passar nele, o step novo fica
   VERMELHO na primeira noite com a mensagem nomeando a diferença. É o modo de
   falha pretendido (premissa não medida falhando alto), não regressão.
4. **A H.14 constrói um repo git descartável** (`git init` + `git add` + `git
   commit`) dentro do `mktemp -d`, porque `--pin` faz `git checkout` DENTRO do
   source e isso exige uma árvore limpa cujo HEAD seja o framework sob teste —
   não há como exercer `--pin` sem isso. Precedente no repo:
   `scripts/tests/test-night-mode-ignore-effect.sh`. Nenhuma operação de escrita
   git foi feita em repositório de registro (nem no vivo, nem na sombra).
5. **A H.14d não é a asserção load-bearing** do controle: o plante cirúrgico
   deixa o tempfile existindo, então o sufixo `[snapshot …]` continua impresso.
   Quem vai RED sob o plante é a **H.14** (`routes=6`) e a **H.14b**.
