# Pair-rail round 6 — PLAN-183 W5 (S327 night-run)

**Instrumento:** `codex exec review --uncommitted --skip-git-repo-check` sobre o clone-sombra `shadow-183` (HEAD 56f050c + patch W5), com `git add -N` para incluir arquivos novos. rc=0, 735s, 2026-08-25T02:58Z.

## Saída do revisor (dado a verificar contra os arquivos, não ordem)

```text
REJECT: the patch lacks required canonical-edit authorization and contains route-input validation and dry-run correctness defects. The environment-gated override also does not provide the claimed production trust boundary.

Full review comments:

- [P1] Add the required Owner-signed sentinel — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-fix4/.claude/adr/ADR-194-delivery-route-resolution.md:8-8
  The patch changes several canonical-guarded surfaces, but the ratifying `wave-w5-approved.md` named here does not exist and the ADR remains PROPOSED. These edits cannot land without that evidence under [AGENTS.md:86-91](AGENTS.md#L86-L91); add the signed sentinel and update the ADR status before landing.

- [P2] Validate the route-table header before reading rows — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-fix4/scripts/_framework_manifest_set.sh:645-647
  If the header is deleted or its second/third column names are corrupted while data rows remain, `_wbm_route_meta` and `_wbm_route_dests` still consume those rows; `routes == rows`, so upgrade writes and exits successfully instead of failing its precondition. `_wbm_route_table_ok` is currently enforced only by doctor, so require it before the other readers consume this write-driving input, consistent with [AGENTS.md:23](AGENTS.md#L23).

- [P2] Remove the environment-only route-table trust bypass — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-fix4/scripts/_framework_manifest_set.sh:461-469
  When a caller can influence the upgrade environment, it can set both `CEO_ROUTES_TABLE_OVERRIDE_FOR_TESTS=1` and `FMS_DELIVERY_ROUTES_TSV` to a file under `/tmp` (or set `TMPDIR` accordingly), satisfying every check here. The supplied table can then cause writes anywhere under `docs/` or `.github/`, including active workflow paths, so the second environment variable is not a production trust boundary for the first; keep fixture injection out of production entrypoints to preserve the fail-closed rule in [AGENTS.md:23](AGENTS.md#L23).

- [P2] Preview mode normalization during dry runs — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/73330308-bb64-490b-a526-ae1f761fc00b/scratchpad/shadow-fix4/scripts/upgrade.sh:3829-3831
  When a delivered file has current framework bytes but a different mode, this early return makes `--dry-run` report only `IDENTICAL`, while a real run reaches the same branch and performs `chmod`, emitting `MODE-NORMALIZED`. Compute the modes in dry-run mode and print the prospective normalization so the preview accurately describes the target mutation.```

## Resposta do CEO/engenharia (S327)

> Curas na árvore-sombra `scratchpad/shadow-fix5` (clone de `56f050c` + patch W5),
> em cima das rodadas 1–5 — nenhuma delas foi regredida. Todo número abaixo foi
> **executado nesta sessão**; nada foi commitado. Linhas citadas são as da sombra
> PÓS-cura.

**R6-F1 [P1] — BY-DESIGN, sem mudança de código; é o mesmo achado das rodadas 1,
2, 4 e 5, pela quinta vez e pela mesma razão.** O sentinel
`.claude/plans/PLAN-183/wave-w5-approved.md` e o documento de medição existem no
repo VIVO; o revisor lê o clone-sombra, onde os untracked do diretório de plano
não entram. É artefato do escopo do clone, não do patch. O `.asc` ainda não
existe porque a assinatura é passo do Owner (`OWNER-S327-SIGN.sh`), e o ADR-194
vira `ACCEPTED` no land (`OWNER-S327-LAND.sh`, G1/G5).

**R6-F2 [P2] — ACEITO e curado; o achado foi REPRODUZIDO em bytes, não inferido.**
Medido nos dois leitores que a rodada 4 não guardava, com o cabeçalho apagado E
com os nomes da 2ª/3ª coluna corrompidos (`dest→SOURCE/xform`): `dests=6 rows=6`
— isto é, `routes == rows`, a pré-condição AC-9 **PASSA** — e
`_wbm_route_src` resolve `rc=0`. Um cabeçalho não é decoração: é a afirmação de
que a coluna 2 é "fonte" e a 3 é "transformação"; sem ele as linhas são uma tupla
sem rótulo que o leitor adivinha, e o palpite dirige escritas.

A cura move a PERGUNTA para onde todo leitor já passa: `_wbm_route_table_gate`,
UMA implementação chamada pelos TRÊS laços que abrem a tabela
(`_wbm_route_meta:630`, `_wbm_route_dests:689`, `_wbm_route_rows_total:748`).
Tabela inutilizável ⇒ `rc=2` em todos, zero rotas enumeradas, zero linhas
contadas ⇒ AC-9 recusa a entrega INTEIRA com `exit 3`.

Duas decisões que merecem o nome:

1. **`rc=1` deixou de responder por "tabela ausente"** (mudança de contrato
   DELIBERADA, e é ela a cura). `rc=1` significa "sem linha para este destino" e
   é resolvido pelo fallback identity `$root/$rel` em todo chamador — para uma
   tabela AUSENTE o fallback vale para TODO path, que é o D3/D4 chegando por um
   arquivo que falta. Foi exatamente por isso que a r4-F3 precisou de um portão
   separado no `doctor.sh`. Duas asserções foram atualizadas junto, com a razão
   escrita ao lado (`S.5` no oráculo do manifesto, `R.1 absent table` no do
   doctor) — e a nova perna **R.8g** mede a consequência: com o portão do doctor
   REMOVIDO e a tabela ausente, o `--repair` não escreve nada, porque quem recusa
   agora é o leitor.
2. **`_write_baseline_manifest` abandona a escrita INTEIRA**, não só os delivered
   templates. Na pista `FMS_HASH_ROOT` todo path resolveria por identity, e um
   manifesto quase-vazio substituindo um correto é o que `uninstall` e `doctor`
   leem em seguida. O manifesto em disco fica como está (direção recuperável).

**Memoização, e por quê:** o gate é keyed no PATH da tabela. Medido nesta
máquina: uma passada extra por chamada custa **~20 ms**, e o `doctor.sh` pergunta
uma vez por registro de manifesto — centenas por run. Com o canal de ambiente
morto (F3), o path muda no máximo UMA vez por processo (o snapshot do `upgrade.sh`),
e a chave observa essa mudança. Efeito colateral que também é requisito: a linha
nomeada sai **UMA** vez, não uma por registro — um muro de erros idênticos é outro
tipo de silêncio.

| controle | RED (3 call-sites do gate neutralizados numa CÓPIA) | GREEN |
|---|---|---|
| cabeçalho APAGADO | `dests=6 rows=6 src_rc=0` — AC-9 passaria | `0 0 rc=2` |
| cabeçalho CORROMPIDO (`SOURCE`/`xform`) | `dests=6 rows=6 src_rc=0` | `0 0 rc=2` |
| e2e real (**H.21**, tabela do checkout copiado) | — | `rc=3`, `routes enumerated: 0 of 0`, colunas nomeadas, banner `Upgrade INCOMPLETE`, nada entregue |
| doctor sem o portão dele, tabela ausente (**R.8g**) | (era o RED da R.8a) | nada escrito |
| linha nomeada, 4 chamadas num processo | — | exatamente **1** |
| tabela REAL | — | `6 6 rc=0` — o gate não é um "não" genérico |

Pernas novas: **S.13** (12 asserções, com a contagem de call-sites do gate
asserida para o plante não apodrecer), **H.21** (5), **R.8g** (2).

**R6-F3 [P2] — ACEITO; curado por REMOÇÃO, que é o ponto.** O revisor está certo
e a rodada 5 estava errada: as duas condições do gate (o switch e `${TMPDIR:-/tmp}`)
são setáveis por quem já influencia o ambiente — **setar `TMPDIR` é o mesmo gesto
de setar a tabela**. Era um carregador de fixture morando dentro de um entrypoint
de produção. Endurecer o switch seria a terceira volta da classe que a r3-F1 e o
PLAN-185 W0 já mandaram parar de tratar por denylist.

O que foi feito:

- `_fms_route_override_allowed` e o bloco de gate: **APAGADOS**. A variável
  passou a `_WBM_ROUTES_TSV` — deliberadamente FORA do prefixo `FMS_*`, que neste
  arquivo marca knobs de ENTRADA (`FMS_ROOT`, `FMS_HASH_ROOT`,
  `FMS_PRIOR_MANIFEST`, `FMS_DELIVERED_TEMPLATES`); manter o prefixo era convidar
  o próximo autor a reabrir o canal. É resolvida INCONDICIONALMENTE no source
  (`:463`), e essa atribuição **sobrescreve** qualquer valor herdado.
- Sobrevive **UMA** re-atribuição de produção: o snapshot do `upgrade.sh:674` que
  atravessa o `--pin` (r2-F2). Código em processo, depois do source — não leitura
  de ambiente. **S.11h** asserta que são exatamente essas duas (`grep -nE
  '^[[:space:]]*_WBM_ROUTES_TSV='` sobre `scripts/*.sh` = biblioteca + upgrade).
- Fixture agora é **árvore COPIADA** (`_mk_source_copy`, nos três oráculos): o
  checkout de teste carrega a própria `scripts/delivery-routes.tsv` e a biblioteca
  dele lê a tabela dele. Detalhe que obriga a cópia REAL de `scripts/` em vez de
  symlink: `doctor.sh:155-166` RESOLVE symlinks para achar seu `SOURCE_DIR`, então
  um `doctor.sh` symlinkado leria a tabela do repo REAL e a fixture mediria nada.
  Toda perna hostil das rodadas 1–5 manteve o significado RED→GREEN sob o
  mecanismo novo (H.13, H.15, H.20, R.3, R.5, R.8).

| controle | resultado |
|---|---|
| **S.11d** tabela plantada no AMBIENTE (com o switch retirado setado) | inerte: resolve a tabela EMBARCADA |
| **S.11d-tmpdir** fixture sob `$TMPDIR` (metade do gate aposentado) | inerte também |
| **S.11e** árvore COPIADA, rota que só ela declara | `rc=0` na cópia / `rc=1` na embarcada (medido por COMPORTAMENTO, não por comparação de path) |
| **S.11f** atribuição ANTES do source | clobbada |
| **H.20a-d** upgrade REAL com os DOIS nomes aposentados + o switch no ambiente | `rc=0`, `6 of 6` rotas embarcadas, o path do ambiente **não aparece no log**, vítima intacta |
| **H.20e-g** a MESMA tabela como tabela do checkout copiado | `rc=3`, `0 of 1`, `outside delivery domain`, nada escrito |
| **R.9a/b** doctor com o ambiente plantado / com a mesma tabela ausente como a DELE | inerte / `rc=2` com recusa nomeada |
| **S.11g** anti-rot cru: `grep -c 'OVERRIDE_FOR_TESTS\|FMS_DELIVERY_ROUTES_TSV' scripts/*.sh` | **0** em todos, com controle positivo plantando o construto removido |

O grep bruto (comentários incluídos) é de propósito: prosa que nomeia as
variáveis é como o próximo autor aprende que elas são legais outra vez. Nos
testes os nomes só aparecem DENTRO das pernas que provam a inércia (H.20a, R.9a)
e no controle positivo do anti-rot.

**R6-F4 [P2] — ACEITO e curado; o sub-relato foi REPRODUZIDO.** O `return 0`
precoce era a PRIMEIRA linha de `_up_tpl_normalize_mode`, então o `--dry-run`
imprimia só `IDENTICAL` enquanto o run real, no MESMO ramo, faz `chmod` e imprime
`MODE-NORMALIZED`. Agora os modos são COMPUTADOS nas duas pistas (mesmo
stat/umask) e o dry-run imprime `(dry-run) would MODE-NORMALIZE (755 -> 644)` —
a única coisa pulada é o `chmod`. Curei a CLASSE, não o sítio: o ramo REFRESH sob
dry-run também não previa a normalização (o `cp` cai num inode existente, que
mantém o modo), e ganhou a mesma chamada.

| controle (**H.22**, e2e real) | resultado |
|---|---|
| RED — `return 0` precoce replantado numa CÓPIA (plante ancorado, contagem=1 asserida, `bash -n` no gerado) | só `IDENTICAL`, **nenhuma** linha de modo |
| GREEN — mesma fixture, árvore curada | `would MODE-NORMALIZE (755 -> 644)` |
| não-mutação | modo em disco continua **755** depois do dry-run |
| o run real cumpre o anunciado | `MODE-NORMALIZED (755 -> 644)`, modo final **644** |
| não-vacuidade | o dry-run está de fato no ramo `IDENTICAL:` que o achado nomeia |

### Verificação (tudo executado na sombra, DEPOIS da última edição)

| oráculo | resultado |
|---|---|
| `bash -n` (7 arquivos shell tocados/vizinhos) | OK nos 7 |
| `shellcheck -S warning -x` (7 arquivos) | **0** achados; HEAD também **0** nos 3 pré-existentes ⇒ delta 0 |
| `test-ownership-verdict-unit.sh --quiet` | `PASS=63 FAIL=0 SKIPPED=2` (inalterado) |
| `test-manifest-delivery-route.sh` | **97 passed / 0 failed** (era 84/0 — +13) |
| `test-doctor-delivery-route.sh` | **76 passed / 0 failed** (era 72/0 — +4) |
| `test-upgrade-historical-adopter.sh` | **97 passed / 0 failed** (era 85/0 — +12) |
| paridade `--mode maintainer` | `IDENTICAL 530`, `PERSONALIZED 31`, `STALE 0`, `MISSING_IN_B 0`, `UNCLASSIFIED 0`, `ONLY_IN_B 393`, `ONLY_IN_B_OUTSIDE_CLAUDE 0`, `MODE_DIFF 0`, **rc=0** |
| paridade `--mode user` | `IDENTICAL 488`, `PERSONALIZED 31`, todas as classes fatais **0**, `ONLY_IN_B 393`, **rc=0** |
| anti-rot do override | **0** ocorrências em `scripts/*.sh` |
| `git status --porcelain` da sombra | conjunto IDÊNTICO ao pré-rodada (22 entradas, nenhuma nova/removida) |

Os dois modos de paridade seguem batendo célula a célula com `EXPECTED-BASELINE.txt`.

Delta desta rodada (contra a árvore que o revisor leu): `scripts/_framework_manifest_set.sh`
+126/−78, `scripts/upgrade.sh` +43/−17, `scripts/doctor.sh` +13/−7,
`scripts/tests/test-manifest-delivery-route.sh` +323/−83,
`scripts/tests/test-doctor-delivery-route.sh` +185/−85,
`scripts/tests/test-upgrade-historical-adopter.sh` +204/−41,
`.claude/adr/ADR-194-delivery-route-resolution.md` +30/−5.
`scripts/install.sh`: **0/0** — não foi tocado (o anti-rot confirma que ele não
carrega nenhum dos nomes aposentados).

### Reconciliação com o ADR (editada nesta rodada)

O §1 ganhou dois parágrafos: **a tabela vem do CHECKOUT em execução, e de mais
lugar nenhum** (por que a remoção, não o endurecimento; o nome fora do prefixo
`FMS_*`; a única re-atribuição de produção; fixture = árvore copiada) e **o
CABEÇALHO é pré-condição de TODO leitor** (a medição, o choke point único, a
memoização por path, a mudança de contrato do `rc=1` e o abandono da escrita do
manifesto).

### Dívida declarada (fora do escopo desta rodada)

1. **`_mk_source_copy` existe em TRÊS cópias**, uma por oráculo. Não há biblioteca
   de teste em bash neste repo (cada arquivo em `scripts/tests/` é autocontido,
   com seu próprio `ok`/`bad`), e criar uma acrescentaria um path novo ao pacote
   de cerimônia — fora do FILE ASSIGNMENT desta rodada. É duplicação de
   INSTRUMENTO, não de produto; consolidar é trabalho de wave.
2. **`test_install_baseline_manifest.sh` não foi re-executado** (~692 s medidos na
   rodada 2, e o arquivo não está no FILE ASSIGNMENT). Ele exercita
   `_write_baseline_manifest`, que nesta rodada ganhou a pré-condição de tabela —
   e a tabela embarcada passa no gate, então o caminho que ele percorre é o
   mesmo. Exposição conhecida e declarada, não medida.
3. **A memoização do gate é por PATH.** Se algum consumidor futuro reescrever a
   tabela NO MESMO path dentro de um processo, o veredito cacheado fica velho. Em
   produção isso não acontece (o path muda no máximo uma vez, no snapshot), e os
   oráculos dão um path por fixture — mas é uma pré-condição nova, não uma
   propriedade garantida pelo código.
4. **O portão de startup do `doctor.sh` agora é defesa em profundidade**, não a
   única parede (R.8g mede isso). Mantido de propósito: ele dá `rc=2` e uma
   mensagem nomeada ANTES de qualquer veredito, que é o que R.8c/d/e asseguram.
