# Pair-rail round 1 — PLAN-183 W5 (S327 night-run)

**Instrumento:** `codex exec review --uncommitted --skip-git-repo-check` sobre o clone-sombra `shadow-183` (HEAD 56f050c + patch W5), com `git add -N` para incluir arquivos novos. rc=0, 453s, 2026-08-24T20:28Z.

## Saída do revisor (dado a verificar contra os arquivos, não ordem)

```text
The patch lacks required guarded-surface ratification, permits route-driven writes outside the target, and introduces a CI test that cannot obtain the history it requires. It also has ownership and CODEOWNERS edge cases that can produce unsafe manifests or divergent delivered trees.

Full review comments:

- [P1] Add the signed sentinel before landing guarded edits — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-183/.claude/adr/ADR-194-delivery-route-resolution.md:8-8
  This patch changes several guarded surfaces listed in [AGENTS.md:84-91](AGENTS.md#L84-L91) and [AGENTS.md:108-116](AGENTS.md#L108-L116), but the ratification named here (`.claude/plans/PLAN-183/wave-w5-approved.md`) is absent and the ADR remains PROPOSED with enforcement pending. The canonical-edit gate therefore lacks the required Owner-signed evidence, so this change cannot land as-is.

- [P1] Reject route destinations that escape the target — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-183/scripts/upgrade.sh:3728-3729
  When the configured route table contains a destination such as `../../outside`, `_wbm_route_dests` accepts it and this branch writes through `$TARGET/../../outside` before any ownership hash gate. Because `FMS_DELIVERY_ROUTES_TSV` is overridable, malformed route input can create or overwrite files outside the requested target; validate destinations as normalized, confined relative paths before delivery.

- [P1] Fetch history before requiring a prior generation — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-183/scripts/tests/test-upgrade-historical-adopter.sh:203-203
  In `smoke-install.yml`, checkout and the later tag fetches are depth-1, while this `git log` starts from shallow `HEAD` rather than the fetched refs. It therefore sees no older template generation, leaving `PRIOR_GEN` empty and causing the wired H.3 fixture and refresh assertions to fail on every CI run; unshallow the relevant history or derive generations from the fetched release refs.

- [P2] Initialize the delivered-template accumulator — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-183/scripts/install.sh:1500-1503
  If the parent environment exports `_DELIVERED_TEMPLATES`, the first append preserves that inherited value because the variable is never reset; under user ceremony, the inherited value is exported even though no delivery function runs. The manifest can consequently claim arbitrary adopter paths as framework-owned, allowing a later manifest-honoring uninstall to remove them when hashes match, so initialize this accumulator to empty alongside the other delivery flags.

- [P2] Skip the template when an unclaimed CODEOWNERS exists — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-183/scripts/upgrade.sh:3892-3898
  When a historical adopter already has rendered `.github/CODEOWNERS` but its install state is missing, unreadable, or lacks a valid `github_owner`, the preceding branch preserves that file and this branch still installs `.github/CODEOWNERS.template`. The upgrade permanently leaves both mutually exclusive files on disk; the template route should be suppressed when an existing rendered CODEOWNERS cannot be reconstructed or claimed.

- [P2] Wire the route-resolution oracle into CI — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-183/scripts/tests/test-manifest-delivery-route.sh:31-31
  The new `test-manifest-delivery-route.sh` is only referenced by itself: no workflow step invokes it, and neither smoke workflow path filter includes the file. Its independent installer-versus-route checks and malformed-row controls therefore never execute in CI, so add both the trigger entries and an explicit test step.```

## Resposta do CEO/engenharia (S327)

> Curas feitas na árvore-sombra `scratchpad/shadow-fix` (clone de `56f050c` +
> patch W5). Todo número abaixo foi **executado nesta sessão**; nada foi
> commitado. Linhas citadas são as da sombra PÓS-cura.

**F1 [P1] — BY-DESIGN, sem mudança de código.** A ratificação NÃO está ausente:
`.claude/plans/PLAN-183/wave-w5-approved.md` existe no repo VIVO (6.330 b,
2026-08-24 17:26). O revisor leu o clone-sombra, onde arquivos untracked do
diretório de plano não existem — o achado é um artefato do escopo do clone, não
do patch. O fluxo é `OWNER-S327-SIGN.sh` → `OWNER-S327-LAND.sh` (G1/G5
enforcement, `w5-ceremony/`), e o ADR-194 vira `ACCEPTED` no land. Nada a curar.

**F2 [P1] — ACEITO e curado em duas camadas independentes.**
REPRODUZIDO pré-cura, não inferido: com `FMS_DELIVERY_ROUTES_TSV` apontado para
uma tabela com `dest=../../outside/PWNED.md`, os DOIS leitores responderam
`rc=0` e `_up_deliver_template` escreveu **536 bytes** em
`$TARGET/../../outside/PWNED.md` — fora do alvo, antes de qualquer portão de
posse. Uma linha `src=../../../../etc/passwd` chegou ao `cp` pelo mesmo caminho.
- (a) **Leitor único** — `_framework_manifest_set.sh:432` `_wbm_route_relpath_ok`
  (ENUMERA as formas aceitáveis: relativa, sem segmento `..`, sem `./` inicial,
  sem `//`, sem `\`, sem espaço/controle) e `:451` `_wbm_route_row_ok` (valida
  `dest` e `src` juntos, com breadcrumb NOMEANDO a linha em stderr). Rejeição é
  `rc=2` fail-CLOSED, **nunca `rc=1`**: `rc=1` significa "sem linha" e os
  chamadores respondem isso com o fallback identity `"$root/$rel"`, que É o D3
  voltando. `_wbm_route_dests` dropa a linha; `:518` `_wbm_route_rows_total` é o
  denominador que torna o drop OBSERVÁVEL. Mesma classe fechada em `:213` para
  `FMS_DELIVERED_TEMPLATES`, que chega pelo AMBIENTE.
- (b) **Sítio de escrita** — `upgrade.sh:3715` `_up_tpl_confined_refuses`:
  léxico (o mesmo predicado) **mais** físico (`cd -P`/`pwd -P` sobre o ancestral
  existente mais profundo, comparado contra o `$TARGET` resolvido — piso bash
  3.2, sem `realpath`), rodando **antes do `mkdir -p`**, porque `mkdir -p` de um
  destino que escapa já cria diretórios fora. E `:3918`: a pré-condição AC-9
  passou a comparar `routes` × linhas do TSV e recusa a entrega **INTEIRA**
  (`PRECONDITION FAILED (rejected route row)`) em vez de seguir com as
  sobreviventes — meia-confiança numa tabela envenenada é o "silent continue" do
  achado.

Controles positivos, todos executados:
| controle | RED (pré/plantado) | GREEN (pós-cura) |
|---|---|---|
| leitor, 4 linhas hostis | `rc=0` nas 4; `dests=4 rows=4` | `rc=2` nas 4; `dests=0 rows=4` |
| escrita, `dest=../../outside/PWNED.md` | 536 b **fora** do `$TARGET` | arquivo ausente, recusa nomeada |
| oráculo com o predicado neutralizado | `29 passed, 5 failed` | `34 passed, 0 failed` |
| oráculo com AS DUAS camadas neutralizadas | `27 passed, 7 failed` (+ arquivo fora) | idem |
| e2e real, tabela envenenada (H.13) | — | 3 asserções verdes, nada fora do `$TARGET` |
| predicado, 28 entradas nomeadas | — | 28/28, inclusive `a..b/c` e `..hidden/x` ACEITOS (rejeitar por SUBSTRING `..` seria falso-positivo) |
Controle de escopo: a tabela REAL segue `dests=6 rows=6` e `docs/BRANCH-PROTECTION.md → rc=0`, e o destino confinado é entregue no MESMO run em que o hostil é recusado — a recusa é dirigida, não geral.

**F3 [P1] — ACEITO e curado nas DUAS pontas.** Verificado: `PRIOR_GEN` vem de
`git log` sobre `$REPO_ROOT`, e o checkout do workflow é `fetch-depth: 1`.
Medido nesta sessão: `templates/docs/BRANCH-PROTECTION.md` tem **2 gerações** —
a atual em depth 40, a única divergente é o commit-RAIZ em **depth 502 de 503**.
Logo **não existe `--deepen=<N>` honesto** aquém da história inteira; o step usa
`git fetch --unshallow --no-tags` (503 commits / 43 MB — segundos contra um job
de 58 min).
- (a) teste: `test-upgrade-historical-adopter.sh:88` sonda
  `rev-parse --is-shallow-repository` e sai `scaffold` (rc=9) com a causa e o
  comando de remédio; `:244` promove o antigo `bad` de "sem geração anterior" a
  `scaffold` — uma FAIL entre 41 asserções se lê como "uma perna regrediu",
  quando a verdade é que o instrumento não rodou.
- (b) workflow: step novo `Deepen git history` (`:490`), **com `if: always()`**
  — sem isso um step vermelho anterior pularia o deepen e rodaria o e2e raso,
  devolvendo o achado; e ele falha fechado se o deepen não expuser ≥2 gerações.
Controle: clone `--depth 1` da sombra + overlay da working tree ⇒ **rc=9** com a
mensagem nomeada; após `fetch --unshallow --no-tags` ⇒ 503 commits, 2 gerações,
e o e2e completo **41 passed / 0 failed**.

**F4 [P2] — ACEITO e curado; e a FAMÍLIA foi varrida.** Verificado:
`_DELIVERED_TEMPLATES` era só lido e concatenado, nunca inicializado. **O
vazamento só é observável quando o path herdado EXISTE no alvo** — foi assim que
ele reproduziu: com `_DELIVERED_TEMPLATES=ADOPTER-OWNED.md` exportado e um
arquivo do adopter com esse nome, um install `--ceremony user` (que não roda
NENHUMA das duas funções de entrega) gravou o arquivo do adopter como
framework-owned no manifesto (`count=1`). Pós-cura, mesmo script e mesma fixture:
`count=0`. Cura em `install.sh:811` e vizinhas — `_DELIVERED_PLAN_SCHEMA`,
`_DELIVERED_DEBATE_SCHEMA`, `_DOCS_TEMPLATE_WROTE` e `_CONTINUITY_PATHS` eram a
MESMA classe, latentes pela mesma razão, e foram resetadas junto.
Em `upgrade.sh` **não havia lacuna** (medido: `_D1_DELIVERY_RAN`,
`_D1_DELIVERED_TEMPLATES`, `_D1_CODEOWNERS_REGISTERED`, `_UP_DELIVERED_TEMPLATES`,
`_MARKER_DELIVERED`, `_SCHEMA_DELIVERED_*` já nascem zerados) — nenhuma linha
decorativa foi adicionada lá.

**F5 [P2] — ACEITO e curado.** Verificado por leitura e reproduzido em fixture: o
`-n "$_UP_GH_OWNER"` da rota `.template` não cobre o caso que importa — adopter
com `.github/CODEOWNERS` RENDERIZADO e install-state ausente sai
`PRESERVED (unclaimed)` na primeira rota e a segunda instalava o `.template`
mesmo assim. Cura em `upgrade.sh:4004`: a rota `.template` é suprimida sempre que
`.github/CODEOWNERS` existe — reivindicado ou não —, com
`SKIPPED (CODEOWNERS present)`. Perna nova **H.12** (`:588`): fixture instalada
COM `--github-owner`, state apagado; assere `PRESERVED (unclaimed)` +
`SKIPPED (CODEOWNERS present)` + exatamente UM dos dois em disco + o CODEOWNERS
byte-idêntico + **exatamente um também após um SEGUNDO upgrade** (a metade
"permanente" do achado: o próximo upgrade acharia o template IDENTICAL e nunca o
removeria).

**F6 [P2] — ACEITO e curado.** Verificado: `grep -rn test-manifest-delivery-route`
em `.github/` = **0 hits**, e o único arquivo que o mencionava era ele mesmo;
`smoke-install.sh` não é driver de testes irmãos (o workflow invoca cada um
explicitamente). Cura: step `Delivery-route resolution oracle (manifest
generator, D3)` (`smoke-install.yml:282`, `if: always()` pela mesma razão da
§9.8 — é o instrumento que certifica a tabela de que os steps de entrega
dependem) e a entrada nas **duas** listas `paths:` (`:40` e `:120`).
SHA-pins byte-idênticos ao HEAD (diff das linhas `uses:` = vazio).

### Achado colateral do próprio oráculo (curado)
O harness de fragmento do `test-manifest-delivery-route.sh` extraía só
`_wbm_route_src`. Com os validadores novos, `_wbm_route_row_ok` ficava
indefinido no harness e — como o leitor é fail-CLOSED — **toda** consulta
respondia `rc=2`, inclusive a da tabela real: 7 FAILs cujo defeito estava no
INSTRUMENTO, não no produto. `:58` agora extrai as três funções POR NOME e
assere a presença de cada uma, então um quarto helper não wired vai RED na
extração em vez de envenenar 6 asserções em silêncio.

### Fora do escopo desta rodada (NÃO curado — decisão do Owner)
`scripts/doctor.sh` é o **QUARTO** leitor da mesma tabela e tem a MESMA classe do
F2: `:416` `DELIVERY_ROUTES_TSV="${DELIVERY_ROUTES_TSV:-...}"` é sobreponível
pelo ambiente, `:418` `_route_source` não valida relpath nenhum, e o resultado
alimenta `_restore_file` (`:460`), que COPIA. `doctor.sh` está fora do
FILE ASSIGNMENT desta wave e não foi tocado. `scripts/tests/_parity_classify.py`
lê a mesma tabela (só teste). A cura definitiva da FORMA é o terceiro leitor
canônico que o CLAUDE.md §4 já nomeia como dívida.

### Verificação (tudo executado na sombra)
| oráculo | resultado |
|---|---|
| `bash -n` (5 arquivos shell tocados) | OK nos 5 |
| `shellcheck -S warning -x` (5 arquivos) | **0** achados; histograma de códigos IDÊNTICO ao HEAD nos 3 pré-existentes |
| `test-ownership-verdict-unit.sh --quiet` | `PASS=63 FAIL=0 SKIPPED=2` (inalterado) |
| `test-manifest-delivery-route.sh` | **34 passed / 0 failed** (era 24/0; +10 do F2) |
| `test-upgrade-historical-adopter.sh` | **41 passed / 0 failed**, 9m12s sob carga concorrente (era 33/0; +8 do F5/F2) |
| idem, no clone UNSHALLOWED (metade GREEN do F3) | **41 passed / 0 failed** |
| paridade `--mode maintainer` | `IDENTICAL 530 / STALE 0 / MISSING_IN_B 0 / UNCLASSIFIED 0 / ONLY_IN_B_OUTSIDE_CLAUDE 0 / MODE_DIFF 0`, **rc=0** |
| paridade `--mode user` | `IDENTICAL 488`, todas as classes fatais **0**, **rc=0** |
| `test_install_baseline_manifest.sh` | **32 passed / 1 failed** (só C.6, pré-existente) |
| `pytest .claude/scripts/tests/test_verify_counts.py` | 28 passed |
| YAML do workflow | 22 steps, `timeout-minutes: 58`, os 2 steps novos com `if: always()` |
Os dois modos de paridade batem célula a célula com `EXPECTED-BASELINE.txt`.

**Custo de CI reavaliado e declarado:** `timeout-minutes` **50 → 58**. As pernas
H.12/H.13 somam 2 fixtures em cache (`cp -R`) e **3 upgrades completos** (8 → 11);
medido 9m12s de relógio para a versão de 11 upgrades sob contenção deliberada
(limite superior), contra os 357 s da de 8. O deepen e o oráculo de rotas são
segundos e não são o que moveu o número. **O job por-PR passou a orçar quase uma
hora — vale uma decisão do Owner sobre mover o e2e histórico para o nightly.**
