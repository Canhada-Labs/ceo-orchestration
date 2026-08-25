# Pair-rail round 5 — PLAN-183 W5 (S327 night-run)

**Instrumento:** `codex exec review --uncommitted --skip-git-repo-check` sobre o clone-sombra `shadow-183` (HEAD 56f050c + patch W5), com `git add -N` para incluir arquivos novos. rc=0, 1109s, 2026-08-25T02:02Z.

## Saída do revisor (dado a verificar contra os arquivos, não ordem)

```text
The upgrade path can be driven to write arbitrary confined paths from an untrusted route table, and the new snapshot violates dry-run isolation for supported TMPDIR configurations. The guarded changes also lack the repository-required signed approval evidence.

Full review comments:

- [P1] Restrict route-table writes to canonical destinations — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-fix3/scripts/upgrade.sh:4071-4071
  When `FMS_DELIVERY_ROUTES_TSV` references an attacker-controlled but well-formed table, this output is trusted after only lexical checks and `routes == rows`. A row mapping `.git/hooks/pre-commit` to `scripts/install.sh` with transform `identity` passes every gate, is copied into an absent destination, recorded in the manifest, and the upgrade exits 0; `_wbm_route_dest_declared` is not a whitelist because it consults the same untrusted table. Validate delivery routes against non-overridable canonical destinations or otherwise authenticate the table before using it to drive writes.

- [P1] Add the signed approval before landing guarded edits — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-fix3/.claude/adr/ADR-194-delivery-route-resolution.md:8-8
  The ADR says ratification is the GPG signature over `.claude/plans/PLAN-183/wave-w5-approved.md`, but neither that file nor its signature exists, and the referenced `w5-oq4-measurement-S327.md` is also absent. This diff modifies several canonical-guarded surfaces, for which [AGENTS.md:84-91](AGENTS.md#L84-L91) requires Owner-signed sentinel evidence, so the change cannot be authorized or audited as written.

- [P2] Keep the route snapshot outside the target — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-fix3/scripts/upgrade.sh:643-645
  If the caller sets `TMPDIR` to `$TARGET` or a descendant, this unconditional `mktemp` creates and populates the route snapshot inside the adopter repository even under `--dry-run`, contradicting the CLI's no-modification contract. Normal `EXIT` cleanup hides the write from final-tree comparisons, while interruption such as `SIGKILL` leaves the file behind; apply the same physical target/TMPDIR check already used by `_load_baseline_manifest`.

- [P2] Centralize CODEOWNERS route metadata parsing — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-fix3/scripts/upgrade.sh:4177-4180
  These `awk` calls directly re-parse the environment-overridable TSV for source and transform instead of obtaining both fields from the shared validated reader. Consequently future schema or validation changes in `_wbm_route_*` can leave this rendered branch with different parsing semantics, contrary to the explicit veto on a fourth route implementation in [ADR-194:173-175](.claude/adr/ADR-194-delivery-route-resolution.md#L173-L175); expose the metadata through one canonical accessor.```

## Resposta do CEO/engenharia (S327)

> Curas na árvore-sombra `scratchpad/shadow-fix4` (clone de `56f050c` + patch W5),
> em cima das rodadas 1, 2, 3 e 4 — nenhuma delas foi regredida. Todo número
> abaixo foi **executado nesta sessão**; nada foi commitado. Linhas citadas são as
> da sombra PÓS-cura.

**R5-F1 [P1] — ACEITO e curado em TRÊS camadas; o achado foi REPRODUZIDO, não
inferido.** Verificado: a linha `.git/hooks/pre-commit ← scripts/install.sh`
(`identity`) é relativa, confinada, sem metacaractere de glob e mantém
`routes == rows` — ela passa por TODO portão das rodadas 1-4. Medido com o
predicado novo neutralizado numa CÓPIA do gerador (plante ancorado, substituição
única conferida): o leitor responde **`rc=0 → scripts/install.sh`** e enumera
`dests=1 rows=1`, isto é, a pré-condição AC-9 fica satisfeita e a entrega segue.

- (a) **O DOMÍNIO é constante de CÓDIGO, no leitor canônico.**
  `_framework_manifest_set.sh` `_wbm_route_domain_ok` — destino sob `docs/` ou
  `.github/`, fonte sob `templates/` — chamado de dentro de `_wbm_route_row_ok`,
  que é o ÚNICO choke point por onde os três leitores passam (`_wbm_route_src` via
  `_wbm_route_meta`, `_wbm_route_dests`, e portanto `_wbm_route_dest_declared`).
  A rejeição é breadcrumb NOMEADO
  (`delivery-route row REJECTED (outside delivery domain)`), a linha cai de
  `_wbm_route_dests`, `routes < rows` passa a valer e a pré-condição AC-9 recusa a
  entrega **INTEIRA** com `exit 3` — a semântica das rodadas 3/4, herdada sem um
  único ramo novo em nenhum consumidor. **Por que não mais uma regra de FORMA:**
  `_wbm_route_dest_declared` (r3) é whitelist, mas lê a MESMA tabela que deveria
  restringir; uma tabela hostil declara os próprios destinos e a whitelist
  concorda. O domínio é a única propriedade que nenhum input fornece.
- (b) **O override virou afordância de TESTE.** `FMS_DELIVERY_ROUTES_TSV` só é
  honrado sob `CEO_ROUTES_TABLE_OVERRIDE_FOR_TESTS=1` **e** a partir de um path
  fisicamente sob o `${TMPDIR:-/tmp}` do próprio processo (`cd`/`pwd -P` nos DOIS
  lados). Raiz ÚNICA, não `$TMPDIR` **e** `/tmp`: aceitar as duas passa qualquer
  checkout que more sob `/tmp` — **medido, é o caso desta própria sombra**, e foi
  assim que a primeira versão do controle nasceu falso-verde. Recusa ⇒ a tabela
  EMBARCADA ao lado do script em execução, com linha nomeada em stderr.
  `mktemp -t` lê a mesma variável, então todo oráculo do repo satisfaz a condição
  por construção; o snapshot da rodada 2 é reaponte INTERNO pós-source, não um
  segundo override.
- (c) **Cinturão e suspensórios no sítio de escrita.**
  `upgrade.sh:_up_tpl_confined_refuses` pergunta o domínio outra vez,
  imediatamente antes do `mkdir`/`cp`, e é fail-CLOSED se o predicado não existir
  (num run real a biblioteca está sourcada e, sem ela, `_wbm_route_dests` também
  sumiu e a AC-9 já recusou tudo — chegar ali sem o predicado é harness, não
  upgrade).

Controles (novos: `test-manifest-delivery-route.sh` **S.11**, 15 asserções;
`test-upgrade-historical-adopter.sh` **H.20**, 7):

| controle | RED | GREEN |
|---|---|---|
| leitor, linha hostil bem-formada | `rc=0 → scripts/install.sh`, `dests=1 rows=1` (predicado neutralizado numa cópia) | `rc=2`; `dests=0 rows=1` |
| sítio de escrita, mesma linha | — | nada escrito, recusa NOMEADA, e o destino LEGÍTIMO do mesmo run entregue |
| fonte fora de `templates/` / destino fora das duas árvores | — | `rc=2` nos dois; `dests=1 rows=3` (só a linha legítima sobrevive) |
| upgrade REAL, override sem o switch | — | `rc=0`, `routes enumerated: 6 of 6`, `override REFUSED`, vítima intacta |
| idem COM o switch (twin) | — | `rc=3`, `routes enumerated: 0 of 1`, `outside delivery domain`, vítima intacta |
| override fora do `$TMPDIR` (com switch) | — | tabela EMBARCADA em vigor |
| mesmo nome de arquivo INEXISTENTE sob `$TMPDIR` | — | honrado (o par isola LOCALIZAÇÃO, não existência) |
| escopo | — | tabela real segue `dests=6 rows=6`, paridade nos dois modos inalterada |

**Residual DECLARADO, que esta forma NÃO fecha:** dentro do domínio, uma tabela
fornecida ainda pode nomear um destino NOVO sob `docs/`/`.github/` — por exemplo
`.github/workflows/pwn.yml ← templates/.github/workflows/validate.yml.template`,
que é exatamente o *"the adopter never gets a live workflow from install"* que a
coluna `note` da tabela promete. Quem fecha isso em produção é (b), não (a); e um
atacante com controle TOTAL do ambiente seta duas variáveis em vez de uma — aí
sobram o domínio, a fonte obrigatoriamente sob `templates/` e a escada de posse
(arquivo do adopter que não casa geração nenhuma sai PRESERVED). Fechar de vez
seria whitelist EXATA dos 6 destinos em código, que é a segunda cópia da tabela
que o ADR-194 §1 proíbe — decisão de wave, não de rodada de rail.

**R5-F2 [P1] — BY-DESIGN, sem mudança de código; é o mesmo achado das rodadas 1,
2 e 4, pela quarta vez e pela mesma razão.** `ls -la` no repo VIVO, executado
nesta sessão: `.claude/plans/PLAN-183/wave-w5-approved.md` (6.330 b, 2026-08-24
17:26) e `.claude/plans/PLAN-183/w5-oq4-measurement-S327.md` (22.952 b, 17:17)
existem os DOIS. `ls` na sombra: ausentes — o revisor lê o clone, onde os
untracked do diretório de plano não entram; é artefato do escopo do clone, não do
patch. `*.asc` também não existe ainda, e esse é o estado CORRETO: o sentinel é
rascunho até `OWNER-S327-SIGN.sh` (a assinatura é passo do Owner), e o land é
`OWNER-S327-LAND.sh` (G1/G5), onde o ADR-194 vira `ACCEPTED`. Nada a curar.

**R5-F3 [P2] — ACEITO e curado; e a cura tem UM dono, não um por `mktemp`.**
Verificado por leitura e reproduzido pelo mecanismo isolado: com `TMPDIR` sob o
alvo, `${TMPDIR:-/tmp}` resolve DENTRO do repositório do adopter, e o snapshot da
rodada 2 nasceu sem herdar a checagem que `_load_baseline_manifest` já carregava
desde o PLAN-161 U1 — a assinatura de "uma cura que não virou função". Cura:
`upgrade.sh:_up_tmpbase` (base física de `${TMPDIR:-/tmp}` comparada com o
`$TARGET` resolvido; `cd`/`pwd -P` dos dois lados porque `/tmp` é symlink no
macOS), usada nos **quatro** `mktemp` do arquivo — snapshot de rotas, journal de
operações, sobreviventes do prune e buffer de render do CODEOWNERS — e o bloco
inline de `_load_baseline_manifest` foi SUBSTITUÍDO por uma chamada a ela: "onde
fica o scratch?" passou de cinco respostas para uma.

| controle | RED | GREEN |
|---|---|---|
| `_up_tmpbase` isolado, `TMPDIR=$TARGET/tmp` | a expressão pré-cura `${TMPDIR:-/tmp}` resolve **dentro** do alvo (H.19d-RED, path impresso) | a função devolve base **fora** do alvo (`/private/tmp`) |
| e2e `--dry-run` com `TMPDIR=$TARGET/tmp` | — | árvore do alvo idêntica em estrutura; **0** arquivos `ceo-*` sob o alvo |
| não-vacuidade | — | o log do MESMO run NOMEIA o snapshot tomado, logo a perna mede onde ele caiu, não um caminho que não rodou |
| não-super-correção, `TMPDIR` fora do alvo | — | devolvido INALTERADO (a cura não é "sempre /tmp") |

**R5-F4 [P2] — ACEITO e curado; e o anti-rot entrou junto.** Verificado: o ramo
renderizado do `.github/CODEOWNERS` puxava `src` e `transform` com dois `awk`
próprios sobre o TSV — o QUARTO parser que o ADR-194 veta pelo nome, e que não
herdava validador nenhum (r1/r3/r5) nem a cura de linha final sem newline
(r4-F4). Cura: `_wbm_route_meta <destino>` na biblioteca, imprimindo
`<fonte><TAB><transformação>` de uma linha JÁ validada (`rc=0` = linha válida,
qualquer transform — julgar o transform é trabalho do chamador, LER não é;
`rc=1` = sem linha; `rc=2` = linha rejeitada), e `_wbm_route_src` passou a ser a
projeção *identity* dela: o arquivo tem **um** laço de lookup por destino, não
dois que possam divergir. Contrato do `_wbm_route_src` preservado célula a célula
(probe: `docs/BRANCH-PROTECTION.md → rc=0`, `.github/CODEOWNERS → rc=2`, destino
sem linha → `rc=1`). Detalhe de custo decidido no desenho: `_wbm_route_src` chama
`_wbm_route_meta` **em processo** (stdout descartado, campos lidos de
`_WBM_ROUTE_SRC`/`_WBM_ROUTE_TRANSFORM`), porque `doctor.sh` pergunta uma vez por
registro de manifesto — centenas por run — e um `$( )` ali seria um fork por
registro. Anti-rot **S.12**: reprova se `awk` sobre a tabela reaparecer em
`upgrade.sh`/`install.sh`/`doctor.sh`, com as linhas de COMENTÁRIO removidas
antes do grep (a pergunta é sobre CÓDIGO, e a prosa desses arquivos legitimamente
DISCUTE o awk aposentado) e com controle positivo plantando o construto exato que
foi removido — sem ele o zero seria um regex morto.

### Achado colateral: um VERMELHO herdado da rodada 4 (curado)

`test-doctor-delivery-route.sh` **não estava em 66/0** na árvore que o revisor
leu. Medido antes de qualquer edição minha: **70 passed / 1 failed**, e a falha é
a anti-rot `R.1 doctor.sh references the route TABLE outside comments` disparando
contra a própria mensagem de recusa que a rodada 4 acrescentou (`doctor.sh:241`,
`echo "       Expected scripts/delivery-routes.tsv next to the manifest library,"`).
A pergunta que a perna existe para fazer é se o doctor RESOLVE o path da tabela
sozinho; uma string impressa para um operador não resolve nada. Cura no
INSTRUMENTO (a mensagem do produto fica): linhas de diagnóstico
(`echo`/`printf`/`_log`) saem do escopo do grep, **com controle positivo**
plantando `DELIVERY_ROUTES_TSV="$SOURCE_DIR/scripts/delivery-routes.tsv"` —
estreitar um padrão sem controle é como uma asserção morre calada.

### Reconciliação com o ADR (editada nesta rodada)

O §1 ganhou dois parágrafos: o acessador único (`_wbm_route_meta`, com o
anti-rot nomeado) e o DOMÍNIO — *"a tabela diz COMO rotear; o CÓDIGO diz ONDE a
entrega pode escrever"*, com `docs/`/`.github/` ← `templates/` fixados e a frase
que fecha a porta: **alargar o domínio é emenda DESTE ADR, nunca edição de
tabela**; mais a regra do override (switch de teste + `${TMPDIR:-/tmp}` físico).

### Verificação (tudo executado na sombra, DEPOIS da última edição)

| oráculo | resultado |
|---|---|
| `bash -n` (7 arquivos shell tocados/vizinhos) | OK nos 7 |
| `shellcheck -S warning -x` (5 arquivos tocados) | **0** achados; HEAD também **0** ⇒ delta 0 |
| `test-ownership-verdict-unit.sh --quiet` | `PASS=63 FAIL=0 SKIPPED=2` (inalterado) |
| `test-manifest-delivery-route.sh` | **84 passed / 0 failed** (era 65/0 — +19 de S.11/S.12) |
| `test-doctor-delivery-route.sh` | **72 passed / 0 failed** (a árvore recebida media 70/1 — ver §colateral; +R.9 e +R.1-control) |
| `test-upgrade-historical-adopter.sh` | **85 passed / 0 failed** (era 72/0 — +13 de H.19/H.20) |
| paridade `--mode maintainer` | `IDENTICAL 530`, `STALE 0`, `MISSING_IN_B 0`, `UNCLASSIFIED 0`, `ONLY_IN_B_OUTSIDE_CLAUDE 0`, `MODE_DIFF 0`, `ONLY_IN_B 393`, **rc=0** |
| paridade `--mode user` | `IDENTICAL 488`, todas as classes fatais **0**, `ONLY_IN_B 393`, **rc=0** |
| `git status --porcelain` da sombra | conjunto IDÊNTICO ao pré-rodada (22 entradas, nenhuma nova/removida) |

Delta desta rodada (contra a árvore que o revisor leu): `scripts/_framework_manifest_set.sh`
+175/−39, `scripts/upgrade.sh` +73/−21, `scripts/tests/test-manifest-delivery-route.sh`
+244/−1, `scripts/tests/test-upgrade-historical-adopter.sh` +147/−0,
`scripts/tests/test-doctor-delivery-route.sh` +61/−3,
`.claude/adr/ADR-194-delivery-route-resolution.md` +23/−0.
`scripts/doctor.sh` e `scripts/install.sh`: **0/0** — não foram tocados.

### Dívida declarada (fora do escopo desta rodada)

1. **`scripts/tests/test_install_baseline_manifest.sh` não foi re-executado.** São
   ~692 s medidos na rodada 2 e o arquivo não está no FILE ASSIGNMENT desta
   rodada. Ele exercita `_write_baseline_manifest`, que só mudou por herança
   (`_wbm_route_src` manteve o contrato célula a célula e nenhuma rota real muda
   de veredito) — exposição conhecida e declarada, não medida.
2. **`_up_tmpbase` cai em `/tmp` quando `$TMPDIR` está sob o alvo.** Se `/tmp` ele
   mesmo estivesse sob o alvo, a base voltaria para dentro. É a mesma propriedade
   que `_load_baseline_manifest` carrega desde o PLAN-161 U1; manter o mesmo
   comportamento foi decisão deliberada (uma cura, um dono), não descuido.
3. **A raiz de scratch permitida é o `${TMPDIR:-/tmp}` do PROCESSO.** Um oráculo
   futuro que crie fixture fora do `mktemp -t` (por exemplo hardcodando `/tmp` com
   `TMPDIR` setado) verá o override recusado e medirá a tabela EMBARCADA. O modo
   de falha é alto e nomeado (`override REFUSED` no log), não silencioso — mas é
   uma pré-condição nova que todo oráculo do repo passa a ter de respeitar.
