# Critic-B — crítica independente (W5-b, round-1 aditivo)

> Lente deliberadamente OMITIDA deste arquivo. O mapa está em
> `anonymization-map.md`. Anti-halo: os achados são pesados pelo
> conteúdo, não por quem os disse (`PROTOCOL.md` §Debate regra 5).

**Veredito:** `ESCALATE`  ·  **8 achados**

## Critic-B-1 · `[P0]` A regra de registro da W5-b ("INSTALLED/REFRESHED/IDENTICAL registram; PRESERVED/SKIPPED nao") e uma REGRESSAO contra o precedente que a wave diz copiar: o precedente registra tambem quando NAO escreveu, por byte-compare (`INSTALL_ONE_WROTE || cmp -s`) e por tres ramos explicitos de ownership-continuity. Implementada como escrita, o SEGUNDO install derruba os 5 registros novos.

**Evidência**

MEDIDO em /tmp: dois installs consecutivos do HEAD (`bash scripts/install.sh $W/t1 --profile core --ceremony maintainer`, rc=0 nos dois). Run1: `COPIED: .claude/plans/PLAN-SCHEMA.md` (i1.log:371). Run2: `EXISTS (skipping): .claude/plans/PLAN-SCHEMA.md` (i2.log:372) — INSTALL_ONE_WROTE=0 — e os dois schema docs CONTINUAM no manifesto (`grep -E '  \.claude/plans/(PLAN|DEBATE)-SCHEMA\.md$'` = 2 linhas). Mecanismo: `scripts/install.sh:1318-1329` — `if [[ "$INSTALL_ONE_WROTE" = "1" ]] || cmp -s "$SOURCE_DIR/..." "$TARGET/..."` com o comentario "Delivered == this call wrote it, OR the pre-existing copy is byte-identical to the framework source". Mais os 3 ramos de continuity em `install.sh:2439-2490`, observados no log run2: i2.log:539-541 (`ownership continuity: SPEC/v1 / PROTOCOL.md / .framework-version delivery record preserved from prior manifest`). No draft (38440 b, 17:48): `grep -ci 'continuity|continuidade'` = 0, `grep -c 'cmp -s'` = 0. A unica checkbox de idempotencia cobre upgrade DUAS vezes (draft:206); nada roda install duas vezes, e o e2e faz exatamente UM install por rota (`test-install-upgrade-parity-e2e.sh:263-272`).

**Consequência**

Um segundo install (ou um install sobre alvo ja upgraded — rota documentada de re-instalacao) apaga do manifesto os 5 paths de `.github/`+`docs/`. Consequencias em cascata: `uninstall.sh` deixa de remover arquivos que o framework entregou (nao ha entrada para casar), `doctor.sh` deixa de vigiar drift neles (so caminha entradas do manifesto), e o upgrade seguinte perde o prior-record. O defeito embarca VERDE: todos os Checks da wave passam, porque nenhum roda install duas vezes.

**Mudança proposta**

Adicionar uma checkbox `[P0]` antes do item de granularidade: (a) cada um dos 5 destinos ganha a MESMA disjuncao do precedente — registrou-se se esta execucao escreveu OU se o arquivo pre-existente e byte-identico a fonte do framework (`cmp -s`), citando `install.sh:1318-1329`; (b) cada um ganha ramo de ownership-continuity no bloco `install.sh:2439-2490`, com a mensagem nomeada; (c) corrigir o Check dos CINCO estados, que hoje afirma o oposto para SKIPPED; (d) Check novo de idempotencia: `install.sh` rodado DUAS vezes no mesmo target produz o MESMO conjunto de paths de `.github/`+`docs/` no manifesto (e o teste fica vermelho se o segundo run derrubar qualquer um).

## Critic-B-2 · `[P0]` A wave nao escolhe entre as DUAS pistas mutuamente exclusivas do gerador de manifesto, e as duas quebram de modo diferente: se os 5 paths entrarem como superficie CONDICIONAL sem `FMS_HASH_SOURCE_*` declarado eles caem no fail-closed e NAO sao gravados (aviso em stderr); se entrarem como nao-condicional, as ~13 linhas novas da `ownership_table.tsv` (recomendacao da OQ-4) ficam INERTES, porque a coluna HASH_SOURCE tem um unico consumidor e ele so roda na pista condicional.

**Evidência**

`scripts/_framework_manifest_set.sh:395-396` e a UNICA chamada de `_wbm_declared_hash_source`, e esta atras de `elif _wbm_is_conditional "$_wbm_rel"`. As duas funcoes tem `case` com os MESMOS 3 relpaths hardcoded (`:311-318` e `:320-325`) e default vazio. O ramo `*)` em `:412-419` e fail-closed: `NOTE: $_wbm_rel delivered but declared no hash_source — NOT recorded (fail-closed; ownership under-claimed)`. O comentario de `:307-310` diz: "Across all 62 rows of the table the default (HASH_TARGET) is never the correct answer, and it is exactly what let three P1 defects re-baseline adopter content as framework-owned". E `install.sh:2508-2511` registra o precedente historico: "Declare on EVERY delivery path, not only continuity … the previous attempt at this wave regressed 24 cells precisely because it left fresh installs undeclared" — seguido das declaracoes fresh-vs-continuity em `:2519-2536` (HASH_TARGET no fresh, HASH_SOURCE/HASH_PRIOR_RECORD na continuidade). No draft: `grep -c 'FMS_HASH_SOURCE|hash_source'` = 0.

**Consequência**

Na pista condicional o executor descobre, JA com o Scope assinado, que faltam entradas em quatro `case` hardcoded (`_framework_target_entries`, `_wbm_is_conditional`, `_wbm_declared_hash_source`, mais os exports em install.sh E upgrade.sh) e que o modo de falha e um NOTE em stderr dentro do log de install — que nenhum step de CI grepa; o Check "nenhum path ausente" fica vermelho sem causa aparente. Na pista nao-condicional, a decisao da OQ-4 (que a wave declara BLOQUEANTE) e trabalho morto: nada le a coluna. Precedente medido de custo: 24 celulas da tabela de ownership regredidas na tentativa anterior desta mesma forma.

**Mudança proposta**

Item `[P0]` novo, ANTES do item da OQ-4 e antes do debate: decidir e registrar no ADR qual pista os 5 destinos ocupam. Se CONDICIONAL: enumerar explicitamente as edicoes em `_wbm_is_conditional` + `_wbm_declared_hash_source` + `FMS_HASH_SOURCE_<superficie>` exportado nas DUAS metades (fresh=HASH_TARGET, continuity=HASH_SOURCE) em install.sh e upgrade.sh, e um Check que grepa o `NOTE: … NOT recorded` no log de install/upgrade e falha se aparecer. Se NAO-condicional: declarar explicitamente que a OQ-4 nao ganha linhas para estes paths e que o mecanismo e o fallback `templates/` do item D3 — o que torna a recomendacao atual da OQ-4 (~13 linhas) obsoleta e precisa voltar ao Owner.

## Critic-B-3 · `[P0]` A rota (ii) da OQ-5 nao alcanca a populacao para a qual foi escolhida. Sem install-state legivel, `upgrade.sh` resolve cerimonia = `user` por fail-safe, e a entrega das duas arvores e gateada em maintainer — logo o adopter historico (o caso que a rota (ii) existe para curar) nao recebe nada, e o e2e e estruturalmente incapaz de observar isso.

**Evidência**

`scripts/upgrade.sh:797-799`: `CEREMONY_EFFECTIVE="user"` / `_CEREMONY_SOURCE="default (no readable install-state — fail-safe user; pass --ceremony maintainer to opt back in)"`; recorded/flag/env sobrescrevem em `:805-816`. As duas funcoes de entrega do install estao atras de `if [[ "$CEREMONY" != "user" ]]` (PLAN-183 §8.1, confirmado). Por que o e2e nao ve: o pin do e2e grava cerimonia — `git show v1.2.0:scripts/install.sh | grep -c '"ceremony"'` = 2 — e o meu install do HEAD confirma a chave gravada (`.claude/.install-state.json` → `request.ceremony = "maintainer"`). A rota B (`test-install-upgrade-parity-e2e.sh:272-287`) sempre instala no pin e depois faz upgrade, logo sempre resolve `recorded install request`.

**Consequência**

A paridade do main fecha (a fixture tem estado gravado) enquanto a populacao real pre-v1.2 continua STALE nas duas arvores — exatamente o custo que a tabela da §8.7 atribui a rota (i)/(iii), pago silenciosamente dentro da rota (ii). Para esses adopters a cura exige um ato humano explicito (`--ceremony maintainer` / `CEO_UPGRADE_CEREMONY=maintainer`), que e a rota (iii) disfarcada. O verde do CI passa a responder uma pergunta diferente da que o Owner comprou.

**Mudança proposta**

Levar de volta ao Owner como emenda a OQ-5 (nao como item de wave): a rota (ii) so alcanca alvos com cerimonia GRAVADA; para alvos sem install-state a wave PRESERVA e o adopter precisa de um ato explicito. Registrar isso verbatim no ADR e na §8.7. E adicionar Check: fixture sem install-state em que o upgrade (a) NAO escreve `.github/`/`docs/`, (b) imprime a razao nomeada citando o fail-safe de `:797-799`, e (c) com `--ceremony maintainer` explicito passa a entregar — provando que a rota de recuperacao existe e e observavel.

## Critic-B-4 · `[P0]` A enumeracao do Scope no item de cerimonia continua incompleta, e um dos paths faltantes e CANONICO — `.github/workflows/smoke-install.yml`. Alem disso o Check usa "os testes" como se fosse um path, e o G4 consome conjunto literal.

**Evidência**

Check atual (draft, ultimo item): "a UNIAO de todos os paths tocados (os 3 canonicos + o ADR + scripts/doctor.sh + os testes)". `.claude/hooks/check_canonical_edit.py:183-184` guarda `.github/workflows/*.yml` / `*.yaml` — canonico, portanto precisa do GRANT do sentinel, nao so de estar no Scope. Por que ele sera tocado: o novo arquivo de dados de rotas (item 4) e qualquer `scripts/tests/*.sh` novo precisam entrar nos DOIS filtros `paths:` do `smoke-install.yml` (`:5-84` pull_request e `:86+` push, com o comentario `:19-21` "an unwired test is the same as no test" e `:31-33` "KEEP IDENTICAL"). Faltam tambem no Scope: o proprio arquivo de rotas, `scripts/tests/_parity_classify.py` (o item 4 exige que ele PARE de carregar mapa proprio, logo sera re-editado), `scripts/tests/ownership_table.tsv` + `docs/ownership-decision-table.md` + `scripts/tests/ownership-expected-reds.txt` (itens da OQ-4/nightly) e `CLAUDE.md` (contagem de ADR — nao guardado, mas tocado). G4: `.claude/plans/PLAN-182/OWNER-S321-LAND.sh:166-179` faz `awk` dos bullets, `git apply --numstat` e `comm -23`, sem filtro de canonicidade.

**Consequência**

E a MESMA falha que a S324 corrigiu para `doctor.sh`, ainda aberta para >=5 paths. Dois modos: (a) o land aborta em `die "o patch toca path(s) FORA do Scope assinado"` depois de a assinatura estar gasta; (b) pior, o hook BLOQUEIA a edicao de `smoke-install.yml` no meio da implementacao, porque o sentinel assinado nao concede um path canonico que ele nao lista — e sem essa edicao o teste novo nasce nao-wired (gate que ninguem roda).

**Mudança proposta**

Substituir "os testes" pela enumeracao literal e acrescentar ao Scope: `.github/workflows/smoke-install.yml`, o arquivo de dados de rotas (com o path exato), `scripts/tests/_parity_classify.py`, `scripts/tests/test-install-upgrade-parity-e2e.sh`, `scripts/tests/ownership_table.tsv`, `docs/ownership-decision-table.md`, `scripts/tests/ownership-expected-reds.txt`, `CLAUDE.md` e o proprio script de LAND. Endurecer a prova mecanica: `_sentinel_grants_path` True para TODO path canonico do patch (hoje o Check pede so os 3 + ADR), e um pre-check que roda `git apply --numstat` do patch contra o bloco Scope ANTES de pedir assinatura.

## Critic-B-5 · `[P0]` A ordem dos itens e inexecutavel e o artefato de land nao existe. O hook bloqueia edicao canonica sem sentinel assinado E VERIFICADO, mas o item de cerimonia e o ULTIMO e o item 1 (sinal de entrega em install.sh) e o PRIMEIRO; o item de debate diz "antes de qualquer linha" e esta em 5o lugar. E nenhuma checkbox cria o script de LAND que o Check final invoca.

**Evidência**

`check_canonical_edit.py`: `scripts/install.sh` / `upgrade.sh` / `_framework_manifest_set.sh` na guard list (`:188-197`), decisao `{"decision": "block", "reason": …}` (`:686`), mensagem "Edits require an Owner-signed sentinel at …" (`:2102`), assinatura destacada obrigatoria (`:1352` monta `<sentinel>.asc`, `:1377 _verify_signature_rail`). Ordem medida no arquivo atual (`awk '/^#### W5-b/,0' | grep -n '^- \[ \]'`): 1=sinal em install.sh, 4=tabela de rotas, 5=debate, 18=cerimonia. LAND: `ls .claude/plans/PLAN-183/` = debate/, resposta-ao-campo.md, w0-us2/, w5-draft-s323.md — nao ha script nem diretorio de cerimonia; o unico LAND existente hardcoda o outro plano (`PLAN-182/OWNER-S321-LAND.sh:31-32` SENTINEL/PATCH) e valida `Patch-sha256` contra o patch (`:135`).

**Consequência**

Executado top-down, o item 1 bate no bloqueio do hook no primeiro Edit — e a recuperacao e `CEO_SENTINEL_UNLOCK` provenance-pinned, nao a sequencia da wave. Como o LAND casa `Patch-sha256` com o patch final, e como o e2e/bateria de ownership (as fontes mais provaveis de correcao) rodam DEPOIS de o patch existir, sao estruturalmente necessarios >=2 eventos de assinatura do Owner (um para destravar as edicoes, outro para amarrar o patch congelado) — contra um orcamento declarado de "1 sessao" e um unico item de cerimonia.

**Mudança proposta**

Reordenar explicitamente: (1) debate L3; (2) decisao da pista condicional (achado acima) + OQ-4; (3) escrever o sentinel com o Scope COMPLETO e obter a 1a assinatura (destrava as edicoes canonicas); (4) implementar; (5) rodar e2e/bateria em arvore-sombra ate verde; (6) congelar o patch, recalcular `Patch-sha256`, RE-assinar; (7) LAND. Acrescentar checkbox `[P0]` para criar `.claude/plans/PLAN-183/OWNER-W5B-LAND.sh` (copia parametrizada do de PLAN-182, com SENTINEL/PATCH proprios) e declarar no orcamento que a wave exige duas assinaturas.

## Critic-B-6 · `[P1]` O instrumento do item D4 nao roda em CI nenhum, a fixture (c) e impossivel como escrita, e reparar a rota RENDERIZADA exige um caminho de ESCRITA novo no doctor — nao "o mesmo mapeamento".

**Evidência**

CI: `grep -c 'test-doctor' .github/workflows/smoke-install.yml` = 0; a unica mencao em workflows e `.github/workflows/validate.yml:878-882`, que declara `scripts/tests/test-doctor.sh` "local/landing-gate only … smoke-install.yml wiring is a separate ceremony". Fixture (c) pede `.github/CODEOWNERS` "deletado E com drift": sao ramos mutuamente exclusivos — ausencia entra em `doctor.sh:504` (`if [ ! -e "$fpath" ] …`), drift so e alcancado depois de `cur != base` em `:548-553`. Rota renderizada: `grep -n 'install-state|OWNER_HANDLE' scripts/doctor.sh` = zero ocorrencias, e o reparo e `cp -p "$SOURCE_DIR/$_rf_rel"` (`:401`) com verificacao pos-copia `_rf_after = _rf_base` (`:404-407`) — copiar template cru nunca vai re-hashear para o baseline renderizado.

**Consequência**

A cura do doctor embarca sem guarda: qualquer PR futuro reverte o mapeamento e todos os gates seguem verdes (a classe "red gate nobody runs" que os proprios comentarios do smoke-install.yml citam cinco vezes). A fixture (c) sera descoberta impossivel na hora de escrever, dentro da cerimonia. E o executor descobre que precisa de um leitor de install-state + renderizacao no doctor, escopo que o Scope assinado nao previu.

**Mudança proposta**

Nomear onde as fixtures vivem e wire-la: ou (a) `scripts/tests/test-doctor.sh` entra nos DOIS filtros `paths:` e ganha step proprio no `smoke-install.yml` (path canonico — ver achado do Scope), ou (b) as tres fixtures entram no `test-install-upgrade-parity-e2e.sh`, que ja e wired. Separar (c) em duas fixtures (ausente / drift). E acrescentar sub-item explicito: o doctor passa a ler `github_owner` do install-state e a REPARAR renderizando, o que muda `_restore_file` (`:401`) — nao apenas a resolucao de path; sem estado, PRESERVAR e reportar not-repairable com razao nomeada.

## Critic-B-7 · `[P1]` Nenhum Check exercita o consumidor DESTRUTIVO (`uninstall.sh`) nem os tres oraculos que guardam as superficies de ESCRITA do upgrade (U1 dry-run identity, U2/U3 exclusion parity + purge), embora a wave adicione duas superficies de escrita novas ao upgrade.

**Evidência**

`grep -n uninstall .github/workflows/smoke-install.yml` = vazio (uninstall nao roda no workflow que a wave usa como gate). `scripts/uninstall.sh:225-243`: caminha o manifesto e faz `rm -f "$fpath"` quando `actual_sha = recorded_sha` (e com `--force` mesmo em mismatch); a limpeza de diretorio vazio e escopada so a `.claude/` (`:277` `find "$TARGET/.claude" -depth -type d -empty -delete`). No draft, `uninstall` aparece 2 vezes, ambas em prosa (draft:288 "blast radius a declarar" e draft:314). `grep -c 'U1|U2|U3'` no draft = 0, enquanto os oraculos sao steps vivos do mesmo workflow (`smoke-install.yml:288-298`: "Upgrade oracle — --dry-run identity (U1)" e "exclusion parity + opt-in purge (U2/U3)").

**Consequência**

Registrar `.github/CODEOWNERS` (que em modo `--github-owner` e um arquivo de CONTROLE ativo do GitHub, sem sufixo `.template`) torna-o hash-deletavel por `uninstall.sh` sem que nenhum teste da wave observe isso; e `.github/workflows/` fica como diretorio vazio porque a varredura so limpa `.claude/`. Do outro lado, qualquer esquecimento de guarda `DRY_RUN` no codigo de entrega novo derruba U1, e a enumeracao nova pode colidir com o walk de exclusao/purge — dois vermelhos que a wave nao antecipa e que aparecem no mesmo run do gate principal.

**Mudança proposta**

Duas checkboxes novas: (a) `[P0]` e2e de uninstall — depois de install+upgrade com as duas arvores registradas, `uninstall.sh --dry-run` lista EXATAMENTE os paths entregues e nao lista os pre-existentes/preservados; o run real remove so aqueles; e o comportamento de `--force` sobre `docs/*` fica declarado no ADR como blast radius (nao apenas em prosa). (b) `[P1]` regressao dos oraculos de escrita: `test-upgrade-dryrun-identity.sh` e `test-upgrade-exclusions.sh` saem 0 depois da cura, citados por nome no Check junto da bateria de ownership.

## Critic-B-8 · `[P2]` Metade do Check (a) do item D4 e VACUOSA: a clausula "nao com o doc da raiz" nao tem poder de deteccao nenhum, porque o reparo do doctor ja e guardado por igualdade de hash — e um doctor NAO curado tambem passa nessa metade. E o item da §9.8 (controle positivo precisa rodar independente do step principal) continua sem checkbox.

**Evidência**

`scripts/doctor.sh:507-517`: `src_hash=$(_hash_file "$SOURCE_DIR/$rel")`; se `src_hash != base` → `MISSING (framework source diverged from baseline — run upgrade.sh)` + BLOCKED, sem `_restore_file`. O mesmo guard no ramo de drift (`:553-563`). Com D3 curado, o baseline de `docs/BRANCH-PROTECTION.md` guarda o digest de `templates/` (medido: entregue = template = `966e057147fbc3dc`) e o doc da raiz tem outro digest, logo a copia do arquivo errado e INALCANCAVEL em qualquer implementacao — inclusive na nao-curada. §9.8: `grep -c 'always()'` no draft = 0.

**Consequência**

O Check (a) transmite seguranca que nao tem: passa com o doctor intocado. E a severidade que a wave atribui a D4 ("repara com o arquivo errado, pior que nao reparar") so e alcancavel no mundo em que D3 esta quebrado — depois da cura o comportamento real e um "not repairable" permanente com mensagem enganosa ("run upgrade.sh", que nao resolve, porque a fonte e outro arquivo). Sem o item da §9.8, a cura de D1 sera validada num run em que o controle positivo ficou `skipped`.

**Mudança proposta**

Reescrever o Check (a) para asserir o resultado POSITIVO com contador/rc (`REPAIRED_COUNT` incrementa e o arquivo restaurado re-hasheia para o baseline de `templates/`) e remover a clausula sem poder; acrescentar asserção de que o doctor NAO curado imprime `MISSING (framework source diverged …)` — a mensagem enganosa — para que o controle negativo tenha alvo nomeado. E promover a §9.8 a checkbox `[P1]`: o step de controle positivo (e os dois steps de ownership hoje `skipped`) rodam com `if: always()`, lembrando que `smoke-install.yml` e canonico e portanto entra no Scope assinado.

## Comandos executados

- `wc -l .claude/plans/PLAN-183-adopter-fitness.md .claude/plans/PLAN-183/w5-draft-s323.md`
- `git log --oneline -8`
- `cat -n .claude/plans/PLAN-183/w5-draft-s323.md (integral, 2 leituras: 15:46 e 17:48)`
- `sed -n '366,990p;1429,1545p' .claude/plans/PLAN-183-adopter-fitness.md`
- `grep -c -i 'pre-Wave-B|sintetiz|always()|coexist|F3|substitui|uninstall|LAND|continuity|cmp -s|FMS_HASH_SOURCE|hash_source|U1|U2|U3' .claude/plans/PLAN-183/w5-draft-s323.md`
- `awk '/^#### W5-b/,0' .claude/plans/PLAN-183/w5-draft-s323.md | grep -n '^- \[ \]'`
- `grep -n 'manifest|sha256|rm -|remove' scripts/uninstall.sh ; sed -n '190,282p' scripts/uninstall.sh`
- `sed -n '113,195p' scripts/_framework_manifest_set.sh`
- `sed -n '260,277p;305,335p;392,440p' scripts/_framework_manifest_set.sh`
- `grep -rln uninstall scripts/tests/ .github/workflows/ ; grep -n uninstall .github/workflows/smoke-install.yml`
- `sed -n '1,110p;299,340p' .github/workflows/smoke-install.yml`
- `grep -rn 'test-doctor' .github/workflows/ ; grep -c 'test-doctor' .github/workflows/smoke-install.yml ; sed -n '866,895p' .github/workflows/validate.yml`
- `grep -n 'FMS_DELIVERED|_DELIVERED_|INSTALL_ONE_WROTE' scripts/install.sh scripts/upgrade.sh`
- `sed -n '1310,1335p;2425,2475p;2492,2545p' scripts/install.sh`
- `sed -n '2196,2240p;2928,2960p;2120,2140p' scripts/install.sh`
- `grep -n 'ceremony' scripts/upgrade.sh ; sed -n '788,830p;3466,3486p;3100,3120p' scripts/upgrade.sh`
- `git show v1.2.0:scripts/install.sh | grep -c '"ceremony"'`
- `sed -n '390,412p;488,565p' scripts/doctor.sh ; grep -n 'install-state|OWNER_HANDLE' scripts/doctor.sh`
- `sed -n '170,215p' .claude/hooks/check_canonical_edit.py ; grep -n 'deny|"block"|gpg|\.asc|verify' .claude/hooks/check_canonical_edit.py`
- `ls -la .claude/plans/PLAN-182/OWNER-S321-LAND.sh ; grep -n 'PLAN-182|SENTINEL|PATCH=' .claude/plans/PLAN-182/OWNER-S321-LAND.sh ; sed -n '160,200p' ...`
- `ls -la .claude/plans/PLAN-183/`
- `sed -n '255,300p;110,145p' scripts/tests/test-install-upgrade-parity-e2e.sh`
- `bash scripts/install.sh /tmp/w5crit.c/t1 --profile core --ceremony maintainer  (2x, rc=0 nos dois)`
- `wc -l /tmp/w5crit.c/t1/.claude/.install-manifest.sha256 ; grep -cE '  (docs|\.github)/' <manifesto> ; grep -E '  PROTOCOL\.md$|SCHEMA\.md$' <manifesto>`
- `grep -n 'ownership continuity|EXISTS (skipping)|COPIED.*SCHEMA' /tmp/w5crit.c/i1.log /tmp/w5crit.c/i2.log`
- `shasum -a 256 de docs/BRANCH-PROTECTION.md, docs/rotation-log.md, .github/CODEOWNERS.template (entregue vs templates/) ; grep -c '{{' nos templates`
- `head -3 scripts/tests/ownership_table.tsv ; wc -l scripts/tests/ownership_table.tsv ; sed -n '1,40p' scripts/tests/test-upgrade-exclusions.sh`
