# Critic-A — crítica independente (W5-b, round-1 aditivo)

> Lente deliberadamente OMITIDA deste arquivo. O mapa está em
> `anonymization-map.md`. Anti-halo: os achados são pesados pelo
> conteúdo, não por quem os disse (`PROTOCOL.md` §Debate regra 5).

**Veredito:** `ESCALATE`  ·  **10 achados**

## Critic-A-1 · `[P0]` O Check do item 1 (`assertando 1,0,0,0`) mede o CALLEE, e a reivindicação de posse mora no CALLER — onde o próprio precedente citado tem DUAS idiomas contraditórias. Uma implementação que copie a idioma errada passa em TODOS os Checks da wave e reivindica posse de arquivo EXISTS-skipped.

**Evidência**

`sed -n '1315,1330p' scripts/install.sh`: para os schema docs o caller é LOOSE — `if [[ "$INSTALL_ONE_WROTE" = "1" ]] || cmp -s "$SOURCE_DIR/..." "$TARGET/..."` → `_DELIVERED_PLAN_SCHEMA=1` (:1318-1322 e :1325-1329), com o comentário :1315 justificando ("recording an identical copy loses no adopter content"). `sed -n '1355,1368p'` e `sed -n '1400,1410p'`: para SPEC/v1 (:1361) e o marker (:1405) o caller é STRICT — só `INSTALL_ONE_WROTE == 1`. O item 1 do draft (w5-draft-s323.md:161-176) cita `install.sh:874-876` como "o molde" e o Check só assere o retorno do callee.

**Consequência**

O item vizinho exige "jamais da presença do arquivo", mas a idioma LOOSE viva no mesmo arquivo é exatamente presença-mais-bytes. Um executor que copie o caller dos schema docs para `docs/*` registra como framework-owned um `docs/BRANCH-PROTECTION.md` que o installer EXISTS-skipou — a classe S238/under-claim do ADR-155-AMEND-1:87-125 — e o `uninstall.sh` passa a removê-lo por hash. Todos os Checks ficam verdes: item 1 (callee 1,0,0,0 ✓), granularidade por path ✓, `grep por CEREMONY = zero` ✓ (é um `cmp`, não CEREMONY).

**Mudança proposta**

Reescrever o Check do item 1 para asserir o SÍTIO DE DECISÃO, não o helper: (a) declarar explicitamente qual idioma cada árvore adota — STRICT para `docs/*` (é o residual de colisão que a própria wave declarou) e a idioma hash-gated só onde a OQ-5 rota (ii) a autorizou (`.github/*`); (b) acrescentar ao Check `grep -n 'cmp -s' <derivação nova>` = 0 para `docs/*`; (c) fixture obrigatória: target com `docs/BRANCH-PROTECTION.md` PRÉ-EXISTENTE byte-idêntico ao template de HEAD — o manifesto NÃO pode listá-lo, e o teste fica vermelho se listar.

## Critic-A-2 · `[P0]` O molde que a §8.6 adota (`_refresh_schema_doc`) é identity-mapped por construção e NÃO tem camada de resolução de fonte nenhuma — é um dos sítios latentes. Estendê-lo literalmente às duas árvores novas re-cria D3 DENTRO do hash-gate, e ele é um QUARTO consumidor que nenhum item da wave atribui.

**Evidência**

`sed -n '3116,3150p' scripts/upgrade.sh`: `_rsd_src="$SOURCE_DIR/$_rsd_rel"` (:3127) — relpath de DESTINO sob a raiz de fonte. `ls .claude/plans/PLAN-SCHEMA.md templates/.claude/plans/PLAN-SCHEMA.md` → o template não existe: os schema docs SÃO identity-mapped, por isso o molde nunca precisou de mapeamento. Censo estreito re-executado: `grep -rn '\$SOURCE_DIR/\$\|\$FMS_HASH_ROOT/\$\|\$_wbm_hash_root/\$\|\$src_root/\$' scripts/ --include='*.sh' | wc -l` = 28 sítios / 9 arquivos, dos quais 12 em `scripts/upgrade.sh` (`:3127` entre eles). O item da tabela de rotas (w5-draft:204-215) nomeia só `_parity_classify.py`, `_framework_manifest_set.sh` e `doctor.sh`.

**Consequência**

Para `docs/BRANCH-PROTECTION.md` o refresh hash-gated compararia o arquivo do adopter contra o doc de 21.513 b da RAIZ (e escreveria esses bytes), não contra `templates/docs/BRANCH-PROTECTION.md` (8.468 b). Para `.github/CODEOWNERS` não há fonte alguma nesse endereço. O mesmo vale para o instrumento de gerações: `scripts/tests/test-schema-generation-pins-unit.sh:93,102,108` faz `git show "$ref:$doc"` com `$doc` = relpath de DESTINO e `DOCS` hardcoded (`:46`), logo o conjunto de gerações de `docs/*` sairia do histórico do arquivo ERRADO, e para o CODEOWNERS renderizado não existe histórico dos bytes entregues.

**Mudança proposta**

Acrescentar `scripts/upgrade.sh:_refresh_schema_doc` (ou a função nova de refresh) à lista de consumidores OBRIGATÓRIOS da tabela de rotas, no MESMO item [P0]; e trocar o Check do hash-gate por: "o conjunto de gerações de cada destino é derivado do histórico git da FONTE declarada na tabela de rotas (não do relpath de destino), e para a rota renderizada é `render(geração, handle do install-state)` — teste com controle negativo: apontar a rota de `docs/rotation-log.md` para uma fonte falsa deixa o gate VERMELHO".

## Critic-A-3 · `[P0]` A rota recomendada para a OQ-4 (~13 linhas novas na `ownership_table.tsv` com uma superfície nova) é MECANICAMENTE inexecutável, e o dimensionamento apresentado ao Owner está refutado: uma superfície desconhecida não vira id vermelho — mata a rodada INTEIRA como HARNESS-ERR.

**Evidência**

`sed -n '116,125p' scripts/tests/test-ownership-table.sh`: `_relpath_for()` é um `case` FECHADO de 3 braços (`spec|protocol|marker`) com `*) return 1`. `sed -n '550,560p'`: `_run_row` faz `rel="$( _relpath_for "$surface" )" || { ERR=$((ERR+1)); return; }` (:557). Summary em `:784` (`GREEN=... HARNESS-ERR=$ERR`) e o gate em `scripts/tests/ownership-nightly-gate.sh:71-72` exige o literal `HARNESS-ERR=0`, senão "partial or vacuous output cannot pass". Além de `_relpath_for`, a superfície nova precisa de braços em `_alt_source` (:256-261), `_mutate_surface` (:301-303), `_derive_verdict` (:430-433), `_derive_hash_source` (:469-489, com o caso especial `spec` de árvore) e na guarda de cerimônia `user` (:568). E `_relpath_for` devolve UM relpath por superfície, enquanto as árvores novas são 5 destinos — um deles dependente de flag.

**Consequência**

O item [P0] "Bateria de ownership não regride" é insatisfazível como escrito: ou o gate nightly sai vermelho por HARNESS-ERR, ou as linhas novas ficam fora da tabela — e ficar fora é ILEGAL pelo contrato do CLAUDE.md §4. O custo real da OQ-4 não é 13 linhas de TSV: são 5+ funções de um harness de 800 linhas com ciclo de ~25 min, fora do Scope enumerado e fora do orçamento (100-160k / 1 sessão). O Owner está sendo pedido a ratificar uma decisão com base de custo errada.

**Mudança proposta**

Antes de levar a OQ-4 ao Owner, acrescentar item [P0] explícito "geometria de superfície no harness de ownership" com as 6 funções nomeadas e a decisão de modelagem (5 superfícies de arquivo único vs. 2 superfícies de ÁRVORE com linhas por-arquivo, seguindo o precedente `spec` de `:200`), re-orçar, e mudar o Check para "o harness enumera as superfícies novas com `HARNESS-ERR=0` e cada destino novo aparece no `--list`".

## Critic-A-4 · `[P0]` O gate de FORMA do `_ownership_verdict` (A5) não tem braço para uma superfície nova: MEDIDO, `docs`/`github` com registro prévio e um DIRETÓRIO ou um `special` no destino devolvem `REFRESH HASH_SOURCE`, onde toda superfície de arquivo único devolve `PRESERVE_UNOWNED HASH_NONE`. O Check "unit oracle sai 0" não detecta isso, e o Check vizinho legaliza absorver o vermelho.

**Evidência**

`bash /tmp/ov_probe2.sh` (sourcing `scripts/_framework_manifest_set.sh`, chamando a função pura): com `prior=hash, op=upgrade` → `spec=REFRESH HASH_SOURCE`, `protocol=PRESERVE_UNOWNED HASH_NONE`, `marker=PRESERVE_UNOWNED HASH_NONE`, **`docs=REFRESH HASH_SOURCE`, `github=REFRESH HASH_SOURCE`** para `live_type=dir`; idem para `live_type=special` (onde até `spec` devolve PRESERVE_UNOWNED). Causa: `_framework_manifest_set.sh:559-565` só tem braços `spec)` e `protocol|marker)`. Perfil `protocol` medido — `awk -F'\t' '$2=="protocol"'` = 13 linhas, incluindo OWN-0032 (`dir`) e OWN-0033 (`special`), as duas esperando `PRESERVE_UNOWNED HASH_NONE`.

**Consequência**

Se as linhas novas variarem a dimensão de forma (como o perfil `protocol` faz), 2 delas nascem VERMELHAS no unit oracle — e nada no desenho diz qual lado é a verdade, então o executor pode "corrigir" a EXPECTATIVA para `REFRESH` e embarcar o furo. Se não variarem a forma, o unit oracle fica verde e o furo embarca calado: um adopter que trocou `docs/rotation-log.md` por um diretório (ou um fifo) recebe verdito REFRESH, e o caller executa uma escrita através de uma forma que não possui — vizinha do F1 (§9.1) que a wave mandou para outro plano.

**Mudança proposta**

Acrescentar item [P0]: "`_ownership_verdict` ganha as superfícies novas no braço A5 `protocol|marker` (dir|dir_empty|special ⇒ PRESERVE_UNOWNED)", com Check comportamental que NÃO é o TSV: chamar a função para o produto cartesiano `{superfícies novas} × {dir, dir_empty, special, symlink} × {prior=hash, upgrade}` e asserir `PRESERVE_UNOWNED HASH_NONE` em todos; e exigir que as linhas novas do TSV INCLUAM essas formas (o oráculo é o contrato, não o output observado).

## Critic-A-5 · `[P0]` O Check da bateria de ownership é CIRCULAR: `ownership-nightly-gate.sh sai 0 contra um ownership-expected-reds.txt re-derivado` passa por construção. É o único Check da wave cujo poder de detecção é exatamente zero para o que a wave acrescenta.

**Evidência**

w5-draft-s323.md:426 (Check do item de bateria) e :429-430 (item [P1] do baseline-map). `scripts/tests/ownership-nightly-gate.sh:8-30`: o gate "compares the observed RED id set against scripts/tests/ownership-expected-reds.txt. ANY set difference fails". `cat scripts/tests/ownership-expected-reds.txt` = 3 ids (OWN-0016/0024/0027). Se o arquivo de expectativa é re-derivado da rodada, `observed == expected` é uma tautologia.

**Consequência**

Combinado com o achado A5 acima: as 2 linhas novas que legitimamente ficariam vermelhas viram "expected reds" no MESMO commit, o gate sai 0, o nightly fica verde para sempre e o furo de forma nunca mais é visto. A cláusula de salvaguarda ("nenhum id pré-existente muda de lado sem justificativa escrita") é prosa, não mecanismo — nada no gate compara contra a geração ANTERIOR do arquivo de expectativa.

**Mudança proposta**

Trocar o Check por dois, mecânicos: (1) `git diff` de `ownership-expected-reds.txt` no commit tem de ser vazio OU cada linha adicionada carrega um id JÁ existente antes da wave — id NOVO em expected-reds é PROIBIDO nesta wave (as superfícies novas nascem verdes ou a wave não fecha); (2) controle positivo do próprio gate já existe (`test-ownership-nightly-gate.sh`, seam `OWNERSHIP_GATE_EXPECTED`) — exigir que ele rode com um expected-reds que OMITE um id vermelho e o gate saia 1.

## Critic-A-6 · `[P0]` O item "Segundo upgrade consecutivo é o teste que pega D3" reivindica um poder de detecção que ele não tem: os DOIS lados do Check passam com D3 presente. A wave fica acreditando que tem um detector de reserva para D3 quando o único detector é o item vizinho.

**Evidência**

w5-draft-s323.md:364-372, Check: "diff da segunda restrito a .github/ e docs/ e vazio, e o .install-manifest.sha256 normalizado e byte-identico entre as duas rodadas". Um baseline identicamente incompleto é byte-idêntico entre rodadas — o próprio desenho escreve isso no item de D3 (:335, "o segundo upgrade continuaria byte-idêntico por ser identicamente incompleto"). E um path AUSENTE do baseline não é reclassificado nem reescrito, logo o diff também sai vazio. `_framework_manifest_set.sh:430-436` faz `continue` quando a fonte não resolve — a omissão é estável, não flutuante.

**Consequência**

Se o item do CONJUNTO EXATO (:342) for enfraquecido, descopado ou amostrado durante a execução — o cenário normal numa cerimônia grande — a wave perde o único detector de D3 e acredita que o segundo-upgrade cobre. Verde não atribuível: exatamente a razão pela qual a §8.8 exigiu D2 antes de D1.

**Mudança proposta**

Reescrever o item: ele não pega D3, pega ESTABILIDADE. Renomear para "o baseline é estável sob re-upgrade" e acrescentar ao Check a única asserção com poder: "o conjunto de paths registrados na segunda rodada é IGUAL ao conjunto esperado enumerado literalmente (5 destinos sem owner / 5 com `--github-owner`), e o teste fica VERMELHO se qualquer um estiver ausente" — isto é, cardinalidade + identidade, não igualdade entre rodadas.

## Critic-A-7 · `[P1]` O item que a §9.8 promete ("o controle positivo tem de rodar independentemente do step principal") NÃO EXISTE em nenhuma checkbox da W5 — e o remédio que a §9.8 sugere (`if: always()`) é refutado pelo comentário do próprio step, que o tornaria vacuoso.

**Evidência**

`grep -n 'always\|if: ' .claude/plans/PLAN-183/w5-draft-s323.md` → zero itens sobre isso (só :80 e :94, sobre filtros `paths:`). `grep -n 'name:\|if:' .github/workflows/smoke-install.yml`: o único `if:` do job está em `:149`; o step `Install/upgrade parity - positive control (planted divergence)` (:339) não tem `if:`, logo é skipped por default quando `:328` falha. E `sed -n '331,338p'` traz o invariante documentado: "This step MUST stay AFTER the plain gate: if the un-planted run were already fatal, rc=1 here would prove nothing about the plant."

**Consequência**

Duas consequências, ambas na minha lente. (a) A W5-a JÁ alterou `_parity_classify.py` e, com o main vermelho, o controle de poder de detecção desse classificador não roda em CI — a cura de D1 vai ser validada por um instrumento cuja capacidade de detectar não foi reexecutada no mesmo run (verde de pergunta envelhecida). (b) Implementar `if: always()` como a §9.8 sugere produz um controle estruturalmente sem sentido enquanto o principal estiver fatal: rc=1 no plantado não distingue "a planta morde" de "já estava vermelho".

**Mudança proposta**

Criar item [P0] na W5-b com o remédio correto: o `--positive-control` passa a asserir sua PRÉ-CONDIÇÃO internamente (rodada não-plantada verde ⇒ só então a plantada tem de sair rc=1; pré-condição violada ⇒ rc próprio, nomeado, ≠ 1 e ≠ 0), e o step ganha `if: always()` só DEPOIS disso. Acrescentar ao Check do item de paridade: "`--positive-control` sai exatamente 1 no mesmo run em que `--mode maintainer` sai 0" — sem isso, a wave fecha sem nunca ter reverificado a planta.

## Critic-A-8 · `[P1]` Fixture que envelhece, com a data de validade já conhecida: os Checks de D3 e D4(a) codificam como valor ESPERADO uma igualdade ACIDENTAL (template == arquivo pós-substituição), então nenhum deles pode distinguir a fonte certa da errada para `docs/*`.

**Evidência**

Medido: `grep -o '{{[A-Z_]*}}' templates/docs/BRANCH-PROTECTION.md templates/docs/rotation-log.md` → nenhuma ocorrência (o único `{{` em BRANCH-PROTECTION.md é `${{ secrets.ANTHROPIC_API_KEY }}`, expressão do GitHub Actions, :120). Os tokens substituíveis são `{{KEY}}` de `build_sed_script` (`install.sh:2036-2066`), e `apply_placeholder_substitutions` reescreve `$TARGET/docs/BRANCH-PROTECTION.md` e `$TARGET/docs/rotation-log.md` in-place (`install.sh:2126-2135`). Checks afetados: w5-draft:342 ("cada digest batendo com a fonte que o adopter recebeu (templates/... ou o renderizado)") e :362 ("(a) ... doctor repara com os bytes de templates/").

**Consequência**

A §9.7 declara o REQUISITO ("todo hash de baseline de docs/* tem de sair do arquivo PÓS-substituição"), mas nenhum Check o exercita — e não pode, porque hoje os dois digests coincidem. Uma implementação que hasheie o template cru sai verde. No dia em que qualquer um dos dois templates ganhar um `{{PROJECT_NAME}}`, o baseline de `docs/*` fica errado no ato (drift falso em todo adopter que instalou com `--project`) e o `doctor.sh` passa a REPARAR com placeholders literais — sem um único teste vermelho.

**Mudança proposta**

Tornar o teste sensível por PLANTIO, como a wave já faz para o CODEOWNERS: na fixture, injetar uma linha `{{PROJECT_NAME}}` em `templates/docs/rotation-log.md` (árvore de fonte da fixture, não o repo) e instalar com `--project`; asserir que o baseline registra o digest PÓS-substituição, que `doctor.sh` repara com os bytes substituídos e que `grep -c '{{PROJECT_NAME}}'` no arquivo reparado devolve 0. Sem plantio, retirar a palavra "templates/" dos dois Checks e escrever "os bytes que o install DEIXOU no destino".

## Critic-A-9 · `[P1]` O Check da tabela de rotas compartilhada é por `grep` (prova menção, não uso) e o censo que deveria fechar a classe — o que a W5-a landou — é estruturalmente CEGO à rota renomeada, exatamente a rota que os Checks mais duros de D4 exercitam.

**Evidência**

Check em w5-draft:215: "grep prova que _parity_classify.py, _framework_manifest_set.sh e doctor.sh todos o LEEM; nenhum dos tres carrega mapa proprio; teste de censo falha se um quarto consumidor aparecer". O censo landado: `.claude/scripts/tests/test_parity_source_resolution.py:203-231` enumera `rel = p.relative_to(templates)` e testa `(REPO/rel).is_file()` — colisões de MESMO relpath. Reproduzido em Python: conjunto = `['CLAUDE.md','README.md','docs/BRANCH-PROTECTION.md','docs/rotation-log.md']`; `'.github/CODEOWNERS' in coll` → **False** (a fonte é `templates/.github/CODEOWNERS.template` e `REPO/.github/CODEOWNERS.template` não existe). E `_RENDERED_DELIVERED` nem é subtraído do conjunto (:222 só subtrai `_TEMPLATE_DELIVERED`). A §8.2 do plano já havia declarado que "um censo que procura homônimos de mesmo nome é estruturalmente cego a essa rota" — e o teste landado tem essa forma.

**Consequência**

O item [P1] da W5-a foi fechado com um instrumento da forma que a análise rejeitou: qualquer rota nova de destino RENOMEADO (o padrão `X.template → X`) nasce invisível, e é justamente a classe onde D3/D4 gravam o hash errado e o `doctor.sh` REPARA errado. Somado ao Check por grep, a promessa "um resolvedor único + censo que o protege" fica sem a metade que protege: o grep passa mesmo que os três consumidores mantenham o mapa local como fallback (o que `_parity_classify.py:269-280` de fato faz — identity-first é o default).

**Mudança proposta**

Duas mudanças no item [P0] da tabela: (1) controle positivo COMPORTAMENTAL em vez de grep — mutar o arquivo de dados numa cópia (apontar `docs/rotation-log.md` para uma fonte falsa) e asserir que os TRÊS consumidores mudam de resposta; um consumidor que não muda tem mapa local, e o teste nomeia qual; (2) re-formar o censo em torno de ROTAS: extrair os pares (fonte, destino) das chamadas de cópia do `install.sh` (`install_docs_template "<src>" "<dst>"`, mais o ramo `sed` de `:1508`) e falhar se existir rota fora da tabela — hoje seriam 5 destinos + 1 dependente de flag, e o CODEOWNERS renomeado apareceria.

## Critic-A-10 · `[P2]` Duas inversões de ordem no checklist: um item [P1] é pré-requisito de três itens [P0], e o item de debate — cujo texto diz "antes de qualquer linha" — está em 5º lugar, depois de uma edição canônica.

**Evidência**

`grep -n '^- \[ \] `\[P' .claude/plans/PLAN-183/w5-draft-s323.md`: ordem = :161 (sinal de entrega, edita `install.sh`, CANÔNICO), :177 (fixture pré-Wave-B com owner), :193 (coexistência CODEOWNERS), :204 (tabela de rotas), :216 (**debate L3**), … :373 (`[P1]` variante `--github-owner`). O Check de D3 (:342) exige "DUAS fixtures (sem owner e com `--github-owner`)"; o de D4 (:362) exige "(c) … em target instalado com `--github-owner`"; e o item :177 é uma fixture de owner — os três [P0] dependem do trabalho do [P1] :373. `check_canonical_edit.py --is-canonical scripts/install.sh` = 1 (medido, citado no próprio draft :443).

**Consequência**

Execução por prioridade ([P0] antes de [P1]) trava em três itens [P0] cujo insumo não existe; e execução na ordem do arquivo começa por uma edição canônica de `install.sh` antes do debate L3 que o PROTOCOL.md exige — o land assinado ficaria em cima de uma decisão L3+ nunca debatida, com o item de debate a jusante "fechando" o que já foi escrito.

**Mudança proposta**

Reordenar: (1) debate L3 aditivo + resposta da OQ-4 (os dois já são [P0] e são portões), (2) a variante `--github-owner` promovida a [P0] e movida para antes de D3/D4 — ela é o INSUMO das fixtures, não uma cobertura extra, (3) o sinal de entrega e o resto da implementação, (4) cerimônia. E marcar no item de debate que nenhuma edição em path canônico começa antes de `w5-round-1/consensus.md` existir.

## Comandos executados

- `wc -l .claude/plans/PLAN-183-adopter-fitness.md .claude/plans/PLAN-183/w5-draft-s323.md`
- `sed -n '366,1000p' .claude/plans/PLAN-183-adopter-fitness.md  (§8 completa)`
- `sed -n '1429,1545p' .claude/plans/PLAN-183-adopter-fitness.md  (§9)`
- `sed -n '1,509p' .claude/plans/PLAN-183/w5-draft-s323.md  (draft integral, re-lido apos mudanca em disco: 550 linhas)`
- `git show --stat b6de7cf`
- `grep -rn '_TEMPLATE_DELIVERED\|_RENDERED_DELIVERED' --include='*.py' .`
- `sed -n '215,300p' scripts/tests/_parity_classify.py`
- `sed -n '330,382p' scripts/tests/_parity_classify.py  (loop de classificacao: _src_digest None -> UNCLASSIFIED)`
- `sed -n '190,240p' .claude/scripts/tests/test_parity_source_resolution.py`
- `python3 - <<'EOF' ... (reproduz test_route_map_census_is_closed: colisoes = ['CLAUDE.md','README.md','docs/BRANCH-PROTECTION.md','docs/rotation-log.md']; '.github/CODEOWNERS' in coll -> False; REPO/.github/CODEOWNERS.template nao existe)`
- `sed -n '1440,1530p' scripts/install.sh  (install_docs_template + install_github_templates, 5 rotas + ramo sed)`
- `sed -n '860,885p' scripts/install.sh  (INSTALL_ONE_WROTE, semantica 1/0/0/0)`
- `grep -rn 'INSTALL_ONE_WROTE' scripts/ .github/  (7 sitios, ZERO em tests/)`
- `sed -n '1315,1330p' scripts/install.sh  (caller LOOSE: || cmp -s)`
- `sed -n '1355,1368p' scripts/install.sh ; sed -n '1400,1410p' scripts/install.sh  (callers STRICT)`
- `sed -n '2092,2140p' scripts/install.sh ; grep -n -A30 'build_sed_script()' scripts/install.sh`
- `grep -c '{{' templates/docs/*.md templates/.github/CODEOWNERS.template templates/.github/workflows/*.template ; grep -o '{{[A-Z_]*}}' templates/docs/BRANCH-PROTECTION.md templates/docs/rotation-log.md | sort | uniq -c  (zero tokens substituiveis)`
- `head -20 scripts/tests/ownership_table.tsv ; grep -vc '^#' ownership_table.tsv (66 = header+65 rows) ; cat scripts/tests/ownership-expected-reds.txt (3 ids)`
- `awk -F'\t' '$1 ~ /^OWN-/ {c[$2]++} END{for(s in c) print s, c[s]}' scripts/tests/ownership_table.tsv  (protocol 13, spec 29, marker 23)`
- `awk -F'\t' '$2=="protocol"' ... (perfil protocol inclui OWN-0032 dir, OWN-0033 special, OWN-0034 symlink -> PRESERVE_UNOWNED)`
- `bash /tmp/ov_probe.sh  (source _framework_manifest_set.sh; _ownership_verdict com surface nova: rc=0 em todas as celulas provadas)`
- `bash /tmp/ov_probe2.sh  (prior=hash+upgrade: docs/github + dir|special -> REFRESH HASH_SOURCE vs protocol/marker -> PRESERVE_UNOWNED HASH_NONE)`
- `sed -n '460,500p' scripts/_framework_manifest_set.sh ; sed -n '526,570p' ; sed -n '595,640p'  (A1/A2/A5/Stage C, braços case)`
- `sed -n '116,125p' scripts/tests/test-ownership-table.sh ; sed -n '550,560p' ; grep -n 'HARNESS-ERR' (ERR++ em :557, summary :784)`
- `sed -n '1,60p' scripts/tests/ownership-nightly-gate.sh ; grep -n 'HARNESS-ERR' (:71-72 exige HARNESS-ERR=0)`
- `sed -n '30,107p' scripts/tests/test-ownership-verdict-unit.sh  (le a TSV e compara com a propria expectativa da linha)`
- `grep -n 'name:\|run:\|if:' .github/workflows/smoke-install.yml ; sed -n '326,346p' ; sed -n '374,396p'  (step :339 sem if:, comentario :331-338)`
- `sed -n '176,218p' .github/workflows/smoke-install.yml  (fetch-depth: 1)`
- `sed -n '85,125p' scripts/tests/test-schema-generation-pins-unit.sh  (SHALLOW=1 reduz o conjunto a tags, sem vermelho; DOCS hardcoded :46; git show "$ref:$doc" com relpath de DESTINO)`
- `sed -n '3116,3150p' scripts/upgrade.sh ; sed -n '3196,3225p'  (_rsd_src="$SOURCE_DIR/$_rsd_rel", identity-mapped)`
- `ls .claude/plans/PLAN-SCHEMA.md templates/.claude/plans/PLAN-SCHEMA.md  (nao existe template: molde e identity por construcao)`
- `grep -rn '\$SOURCE_DIR/\$\|\$FMS_HASH_ROOT/\$\|\$_wbm_hash_root/\$\|\$src_root/\$' scripts/ --include='*.sh' | wc -l  (28 sitios / 9 arquivos; 12 em upgrade.sh)`
- `git show v1.2.0:scripts/install.sh | grep -c 'github_owner'  (=2: o pin GRAVA o estado, logo a fixture de owner do e2e NAO exercita o caso pre-Wave-B)`
- `grep -n -- '--mode\|--pin\|PIN=' scripts/tests/test-install-upgrade-parity-e2e.sh  (--mode existe, PIN default v1.2.0 em :110)`
- `grep -n '^- \[ \] `\[P' .claude/plans/PLAN-183/w5-draft-s323.md  (ordem dos itens: debate em 5o lugar, :216; --github-owner [P1] em :373)`
