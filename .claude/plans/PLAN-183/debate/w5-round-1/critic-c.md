# Critic-C — crítica independente (W5-b, round-1 aditivo)

> Lente deliberadamente OMITIDA deste arquivo. O mapa está em
> `anonymization-map.md`. Anti-halo: os achados são pesados pelo
> conteúdo, não por quem os disse (`PROTOCOL.md` §Debate regra 5).

**Veredito:** `PROCEED-WITH-CONDITIONS`  ·  **6 achados**

## Critic-C-1 · `[P0]` A ORDEM está errada: a contenção de perímetro tem de ser o item 0 da W5-b, não um "plano próprio" depois. O guard que a F1 (§9.1) precisa JÁ EXISTE no install.sh, é chamado pelo install_one, e NÃO é chamado por install_docs_template — a função que o primeiro item da W5-b edita. E o eixo grave não é o que a §9.1 descreve (leaf `-e`): é o COMPONENTE PAI. A W5-b transforma esse buraco de "acontece uma vez, no install" em "acontece a cada doctor --repair e a cada refresh do upgrade".

**Evidência**

scripts/install.sh:848 `_assert_no_symlink_parents()` — comentário próprio: "closes the gap where e.g. $TARGET/.claude -> /etc would make mkdir -p + cp -R write under /etc"; chamado em :895 por install_one, que também guarda o leaf com `[[ -e "$dst" || -L "$dst" ]]` (:885, :898). install_docs_template (:1446-1474) usa só `[[ -e "$dst" ]]` (:1466) e NUNCA chama o guard. doctor.sh:_restore_file (:399-401) faz `mkdir -p "$TARGET/$(dirname $rel)"` + `cp -p` sem guard nenhum. PROVA COMPORTAMENTAL (executada em /tmp, código verbatim): com `$TARGET/docs -> /tmp/outside`, o guard de leaf do doctor (:534 `[ -L "$fpath" ] || [ ! -f "$fpath" ]`) NÃO dispara (o leaf é regular file através do pai), o ramo escolhido é MISSING (:504) — que repara SEM `_confirmed` (:518-528) — e `cp -p` gravou em /private/tmp/w5b-sym2.94789/outside/rotation-log.md, com realpath fora do $TARGET (`startswith($TARGET) == False`). A §9.1 cita como defesa análoga install.sh:2139-2159 (guard de substituição), não :848 — e não menciona o eixo pai em nenhum ponto. Grep no draft atual (536 linhas): `symlink` = 0 ocorrências.

**Consequência**

O primeiro item da W5-b copia de install_one o SINAL DE ENTREGA (`INSTALL_ONE_WROTE`, :874-876) e não copia os DOIS guards de contenção do mesmo bloco. Resultado: um registro de entrega (`FMS_DELIVERED_*`) para bytes que aterrissaram FORA do target; o manifesto passa a afirmar posse de um path cujo conteúdo real está fora da árvore; e o item D4 arma `_restore_file` para `docs/` e `.github/` — justamente as duas árvores que adopters reais symlinkam (`.github` para config de org, `docs` para monorepo de documentação), ao contrário de `.claude/`. Adiar: a cerimônia L3+ da W5-b assina hunks em install.sh:1446-1522 e em doctor.sh; o "plano de segurança" depois reabre EXATAMENTE essas linhas ⇒ segunda cerimônia L3+ sobre hunks sobrepostos, com anchor-sha conflitante — a classe `feedback-fix-of-fix-means-change-the-cure-architecture`.

**Mudança proposta**

Inserir como ITEM 0 da W5-b (antes do item do sinal de entrega): (a) promover `_assert_no_symlink_parents` para `scripts/_hash_lib.sh` — o lib compartilhado que install.sh:178, doctor.sh:178, upgrade.sh e _framework_manifest_set.sh já sourceiam (verificado; e ele é NÃO-canônico pelo oráculo: `check_canonical_edit.py --is-canonical scripts/_hash_lib.sh` → 0); (b) chamá-lo em install_docs_template ANTES do `mkdir -p`, e trocar `[[ -e "$dst" ]]` por `[[ -e "$dst" || -L "$dst" ]]`; (c) chamá-lo em `_restore_file` e no ramo de re-link (doctor.sh:453), fail-CLOSED (path bloqueado, nunca reparado); (d) Check com controle positivo nos DOIS eixos: fixture com `$TARGET/docs -> /tmp/x` (pai) e fixture com leaf symlink pendente — install ABORTA e doctor reporta blocked, e as duas ficam VERDES-por-bloqueio e VERMELHAS com o guard revertido. Acrescentar `scripts/_hash_lib.sh` ao Scope do sentinel (é path novo tocado; o G4 do LAND é `comm -23 touched scope` sem filtro de canonicidade).

## Critic-C-2 · `[P0]` A W5-b amplia o alcance de uma autoridade de DELEÇÃO que é, hoje, não-autenticada, não-confinada e — para as duas árvores novas — não coberta pelo backup. Este é o pior caso concreto pedido: uninstall.sh apaga um arquivo do adopter tomado por colisão de hash, sem `--force`, sem aviso de mismatch, e a rede de segurança do próprio framework não contém o arquivo.

**Evidência**

scripts/uninstall.sh:178 — o backup pré-uninstall é `( cd "$TARGET" && tar czf "$backup" .claude/ )`: SÓ `.claude/`. `docs/` e `.github/` ficam fora. :210 `fpath="$TARGET/$rel"`, :231 `rm -f "$fpath"` no ramo em que `actual_sha == recorded_sha` — deleção silenciosa, sem `--force` e sem contar como mismatch (:227-233). Contenção: `grep -c 'realpath|\.\./|startswith|_assert' scripts/uninstall.sh` = **0** — nenhuma normalização de `..` sobre `$rel`. Autenticação: o cabeçalho documenta exit 3 = "HMAC verification failed (manifest tampered)" e a flag `--no-hmac-verify` (:18, :25), mas `grep -c 'exit 3' scripts/uninstall.sh` = **0** e `NO_HMAC_VERIFY` só é consumido em :114, dentro do RESTORE mode — o modo uninstall NÃO verifica HMAC nenhum do manifesto. No draft atual, `uninstall` aparece só em prosa (:315, :341); zero checkboxes.

**Consequência**

Hoje o manifesto só reivindica `.claude/**`, que o backup cobre — então um erro de posse é recuperável. Depois da W5-b ele reivindica `docs/BRANCH-PROTECTION.md`, `docs/rotation-log.md` e até 3 paths de `.github/`, e a colisão que a OQ-5 aceita como risco declarado passa a ter cauda IRRECUPERÁVEL pelo caminho do próprio framework. Agrava: `docs/rotation-log.md` é, por desenho, um log append-only de rotação de `ANTHROPIC_API_KEY` (templates/docs/rotation-log.md:1-14, 536 b, "NEVER paste a key into this file") — um arquivo cujo ciclo de vida é o ADOPTER escrever nele, não o framework. Colocá-lo no baseline faz o doctor classificar todo adopter que já rotacionou chave como DRIFT permanente ⇒ `UNRESOLVED > 0` ⇒ `exit 1` (doctor.sh:751-753) para sempre: o verificador de integridade vira alarme crônico, e alarme crônico é ignorado.

**Mudança proposta**

Três itens novos na W5-b, todos com Check: (1) o backup pré-uninstall deriva o conjunto do tar dos TOP-LEVELS que o manifesto reivindica, não do literal `.claude/` — Check: fixture com os 5 paths novos registrados; o tarball contém `docs/` e `.github/`, e o teste fica vermelho se algum path reivindicado ficar fora. (2) `uninstall.sh` recusa `$rel` que não resolva para dentro do `$TARGET` (realpath + prefixo), fail-CLOSED — Check: linha de manifesto com `../` é REJEITADA com exit ≠ 0, e nada é apagado. (3) classificar `docs/rotation-log.md` como SEED (entregue uma vez, nunca refrescado, nunca reparado, nunca reivindicado no manifesto) e só `BRANCH-PROTECTION.md` como conteúdo de framework — decisão que precede a OQ-4, porque muda a contagem de linhas da ownership_table.tsv. Precedente para a classe SEED: o `ACCEPTED` do _parity_classify.py:118-121.

## Critic-C-3 · `[P0]` O desenho nunca fixa se as duas árvores entram no enumerador como ENTRADAS DE ARQUIVO ou como ENTRADAS DE DIRETÓRIO — e o Check de D3 ("o conjunto EXATO de registros") é VACUOSO quanto a isso, porque toda fixture do e2e é um target LIMPO, onde os dois desenhos produzem o mesmo conjunto.

**Evidência**

`_framework_target_entries` (scripts/_framework_manifest_set.sh:113-185) emite as duas formas no mesmo `printf`: arquivos (`PROTOCOL.md`, `.claude/team.md`) e DIRETÓRIOS (`.claude/hooks`, `.claude/scripts`, `.claude/commands`, `.claude/skills/core`). O docstring de `_framework_manifest_files` (:186-192) confirma: "Directories are walked (regular files only…)". O consumidor a jusante é o orphan scan do doctor: `FMS_ROOT=$TARGET` + `_framework_manifest_files > enumerated` (doctor.sh:649-651), `comm -23 enumerated manifest-rels > orphans` (:664), cada linha vira `ORPHAN?:` (:672) e `--strict-orphans` faz exit 1 (:754-756). Grep no draft atual: `orphan`/`ORPHAN` = **0 ocorrências**; no PLAN-183 inteiro também = 0 (grep executado).

**Consequência**

Se `docs` e `.github` entrarem como entradas de DIRETÓRIO, num adopter real todo arquivo próprio dele sob `.github/workflows/` e `docs/` passa a ser enumerado como "framework-owned dir" — acusado como `ORPHAN?` e derrubando `doctor --strict-orphans`, além de o writer de manifesto omitir cada um deles em SILÊNCIO (`continue` de _framework_manifest_set.sh:430-436, quando `$FMS_HASH_ROOT/$rel` não existe). O CI/e2e nunca vê nada disso: em target limpo o walk devolve exatamente os 5 delivered, e o Check "conjunto EXATO" passa. É a classe "instrumento verde cuja PERGUNTA envelheceu" replicada no instrumento novo — e o dano é acusar o adopter de posse indevida sobre a árvore dele.

**Mudança proposta**

Pinar como CONTRATO no item de D3 e no ADR: as duas árvores entram SOMENTE como entradas de ARQUIVO (uma por destino entregue), NUNCA como entrada de diretório — `docs/` e `.github/` são namespaces COMPARTILHADOS, ao contrário de `.claude/hooks`. Check não-vacuoso, e ele exige fixture SUJA: target que já contém `.github/workflows/deploy.yml`, `.github/ISSUE_TEMPLATE/bug.md` e `docs/adr/0001-x.md` autorais do adopter ⇒ o manifesto lista os 5 delivered e NENHUM dos autorais; `doctor --strict-orphans` sai 0 e o log não contém `ORPHAN?` para nenhum path dessas duas árvores; o teste fica VERMELHO se a implementação usar entrada de diretório.

## Critic-C-4 · `[P0]` O Check (c) do item D4 é VACUOSO — a assertion negativa `grep {{OWNER_HANDLE}} == 0` é satisfeita EXATAMENTE pelo modo de falha perigoso — e `_restore_file` não é atômico: a verificação pós-cópia é um RELATÓRIO, não um gate, então o doctor deixa os bytes errados no disco quando falha.

**Evidência**

Check atual (draft, item D4, fixture (c)): "...doctor repara com os bytes RENDERIZADOS, o re-hash bate com o baseline e grep por {{OWNER_HANDLE}} no arquivo reparado devolve ZERO". Executado: `sed "s/{{OWNER_HANDLE}}//g" templates/.github/CODEOWNERS.template` produz linhas `".claude/skills/**    @"` — dono VAZIO — e `grep -c '{{OWNER_HANDLE}}'` nessa saída = **0**, isto é, o Check PASSA sobre um CODEOWNERS sem nenhum dono. O render vazio é o caminho DEFAULT quando falta estado: upgrade.sh:3629-3633 sintetiza `placeholders: {}` para alvo pré-Wave-B (medido e já declarado na §8.5.3), e `grep 'github_owner|GITHUB_OWNER|CODEOWNERS' scripts/upgrade.sh` = 0. E `_restore_file` (doctor.sh:397-411): `cp -p` PRIMEIRO (:401), depois `_hash_file` (:404) e, no mismatch, apenas `_log "RESTORE-FAILED"` + `return 1` (:410-411) — sem rollback. No ramo MISSING (:518-528) não há `_backup_file` e não há `_confirmed`, logo não existe nem cópia anterior nem consentimento.

**Consequência**

Um `doctor --repair` num adopter sem `github_owner` gravado escreve um `.github/CODEOWNERS` cujas regras têm dono vazio, falha a verificação, loga RESTORE-FAILED e DEIXA o arquivo lá. O GitHub ignora silenciosamente regra de CODEOWNERS com dono inválido: a exigência de revisor desaparece sem nenhum sinal no repositório do adopter — controle de segurança removido por uma operação de "reparo", com uma linha de log como único aviso. O novo item "pré-Wave-B COM owner" define PRESERVAR para o UPGRADE; para o ramo MISSING do doctor não há o que preservar e o comportamento fica indefinido.

**Mudança proposta**

(a) Tornar `_restore_file` atômico: escrever em temp no MESMO diretório, verificar o hash contra o baseline, e só então `mv` — no mismatch, remover o temp e reportar not-repairable, sem tocar o destino. (b) Rota RENDERIZADA fail-CLOSED: quando qualquer insumo de render estiver ausente (`github_owner` unset/synthesized), o path é NOT-REPAIRABLE e NÃO-REIVINDICÁVEL — nunca "reparar com o melhor palpite". (c) Substituir a assertion negativa por AFIRMATIVA: toda linha de regra não-comentário do arquivo reparado termina em `@<handle>` igual ao `github_owner` registrado, o re-hash bate com o baseline ANTES do arquivo ser posicionado, e a fixture com estado AUSENTE assere que o doctor NÃO escreveu nada e reportou blocked.

## Critic-C-5 · `[P1]` O censo de consumidores do doctor.sh está incompleto: existe um QUARTO sítio, `_dr_delivered`, e ele decide ENUMERAÇÃO (logo, quem é acusado de órfão), não hash. O desenho nomeia só :401, :507 e :553.

**Evidência**

scripts/doctor.sh:625-648 — `_dr_delivered() { # $1 = ERE fragment anchored at the relpath position }` reconstrói as flags de entrega LENDO o manifesto por ERE hardcoded, e só três: `SPEC/v1` (:633), `PROTOCOL\.md` (:638), `\.claude/\.framework-version` (:643); exporta `FMS_DELIVERED_SPEC/PROTOCOL/MARKER` (:648) antes do `_framework_manifest_files` do orphan scan (:651). `FMS_DELIVERED_PLAN_SCHEMA` e `FMS_DELIVERED_DEBATE_SCHEMA` — que _framework_manifest_set.sh:158-165 exige — NÃO são reconstruídos ali: a precedência instalada já sub-enumera em silêncio. Grep no draft atual: `_dr_delivered` = **0 ocorrências**.

**Consequência**

A W5-b cria até 5 flags `FMS_DELIVERED_*` novas por PATH. Se o `_dr_delivered` não for estendido, o orphan scan sub-enumera (direção segura, mas o instrumento passa a mentir por omissão sobre as árvores novas); se for estendido com mais um `case`/ERE hardcoded, ele se torna o quarto ramo local do MESMO conhecimento — exatamente o anti-padrão que o CLAUDE.md §4 proíbe e que o item da tabela compartilhada existe para fechar. O Check da tabela de rotas, como está escrito, prova que três consumidores a leem e não vê esse quarto.

**Mudança proposta**

Incluir `_dr_delivered` (doctor.sh:625-648) no censo do item "tabela de ROTAS vira dado COMPARTILHADO", e reformular o Check: o teste de censo enumera TODOS os sítios que decidem origem/rota/entrega — `_parity_classify.py`, `_framework_manifest_set.sh:430-436`, `doctor.sh:401/507/553` E `doctor.sh:625-648` — e falha se qualquer um deles derivar a resposta localmente. A reconstrução das flags a partir do manifesto passa a ser UMA função no lib compartilhado, com um teste que assere que o conjunto reconstruído == o conjunto declarado (hoje: 3 de 5, medido).

## Critic-C-6 · `[P1]` O argumento de aceite da OQ-5 — "bytes idênticos são prova de origem quando o CONTEÚDO é framework-specific" — NÃO resiste: ele raciocina sobre a população errada. Conteúdo framework-specific torna a rota humana deliberada MAIS provável, não menos — e é justamente a rota que não deixa registro nenhum.

**Evidência**

O próprio PLAN-183 §8.6 cita README.md:104-121 (install por clone "instala qualquer commit de main") como a razão de as gerações virem do histórico git e não de tags. As mesmas rotas manuais (`cp` de um clone, vendoring, `git subtree`, fork interno, template de org) produzem bytes byte-idênticos a uma geração conhecida com ZERO registro de install — o mesmo estado de evidência de um adopter histórico, que é a hipótese em que a rota (ii) reivindica posse. Já para `docs/BRANCH-PROTECTION.md` (8.468 b) o próprio desenho admite risco residual (§8.7); e `docs/rotation-log.md` é um stub de 536 b cujo conteúdo pristine significa "o adopter nunca rotacionou chave" — o caso pristine é o COMUM, não a borda. Blast radius medida no achado P0 sobre uninstall: `rm -f` em uninstall.sh:231 sem `--force`, com backup que cobre só `.claude/` (:178).

**Consequência**

A rota (ii) mistura duas autoridades muito diferentes num único gate de hash: REFRESCAR (idempotente, e o pior caso é reescrever bytes idênticos aos que já estão lá) e REMOVER (destrutivo, sem backup para essas árvores). A justificativa de probabilidade — mesmo aceitando-a — só sustenta a primeira. Manter as duas juntas significa que a decisão "fechar o main" compra, de carona, a autoridade de apagar arquivo que nunca entregamos.

**Mudança proposta**

Manter a rota (ii), mas SEPARAR as autoridades no ADR e no manifesto: entradas nascidas de migração por hash-gate (sem registro de entrega) recebem classe própria — p.ex. gravadas como linha `#MIGRATED <sha>  <rel>`, que o `case "$line" in '#'*) continue` de uninstall.sh:202-204 já ignora por construção, enquanto upgrade e doctor podem optar por lê-las. Efeito: o refresh migra (main fecha, paridade sai 0), a remoção exige ato explícito (`--force`) e a colisão aceita deixa de ter consequência destrutiva. Registrar no ADR a frase correta: "bytes idênticos autorizam REFRESH, nunca REMOÇÃO", e declarar a rota manual (clone/vendoring) como a população real do risco.

## Comandos executados

- `sed -n '366,600p' .claude/plans/PLAN-183-adopter-fitness.md  (e 600,880 / 880,990 / 1429,1545)`
- `sed -n '1,180p' / '180,380p' / '380,509p' .claude/plans/PLAN-183/w5-draft-s323.md`
- `sed -n '1440,1535p' scripts/install.sh   # install_docs_template + install_github_templates`
- `sed -n '838,900p' scripts/install.sh     # _assert_no_symlink_parents (:848) + install_one (:895 chamada, :874-876 INSTALL_ONE_WROTE)`
- `cat -n scripts/uninstall.sh`
- `grep -c 'exit 3' scripts/uninstall.sh   -> 0`
- `grep -n 'NO_HMAC_VERIFY' scripts/uninstall.sh   -> :47 :56 :114 (so restore mode)`
- `grep -cn 'realpath|\.\./|startswith|_assert' scripts/uninstall.sh   -> 0`
- `sed -n '178p;209,211p;230,232p' scripts/uninstall.sh`
- `sed -n '355,420p' / '440,610p' / '640,700p' / '748,757p' scripts/doctor.sh`
- `grep -n '_dr_delivered' scripts/doctor.sh   -> :625 :633 :638 :643`
- `sed -n '113,195p' scripts/_framework_manifest_set.sh   # _framework_target_entries (arquivo E diretorio) + docstring do walk`
- `grep -n 'source |. "$' scripts/doctor.sh + grep -rln '_hash_lib.sh' scripts/   # lib compartilhado ja sourceado por install/upgrade/doctor/fms`
- `for p in _hash_lib.sh uninstall.sh doctor.sh install.sh; do python3 .claude/hooks/check_canonical_edit.py --is-canonical scripts/$p; echo $?; done   -> 0 0 0 0`
- `wc -c templates/docs/BRANCH-PROTECTION.md templates/docs/rotation-log.md templates/.github/CODEOWNERS.template ; head -25 templates/docs/rotation-log.md`
- `grep -n 'OWNER_HANDLE' templates/.github/CODEOWNERS.template ; sed "s/{{OWNER_HANDLE}}//g" templates/.github/CODEOWNERS.template | grep -c '{{OWNER_HANDLE}}'   -> 0 (Check passa com dono VAZIO)`
- `DEMO /tmp (codigo verbatim do doctor): TARGET/docs -> /tmp/outside ; guard de leaf (:534) NAO dispara ; ramo MISSING (:504) ; mkdir -p + cp -p gravou em /private/tmp/.../outside/rotation-log.md ; realpath.startswith(TARGET) == False`
- `grep -n 'pre-install-state|8.5.3|sintetiz|symlink|orphan|uninstall|_dr_delivered|backup' .claude/plans/PLAN-183/w5-draft-s323.md   # symlink/orphan/_dr_delivered = 0 ocorrencias no draft atual (536 linhas)`
- `grep -n 'uninstall|orphan|ORPHAN' .claude/plans/PLAN-183-adopter-fitness.md   -> :856 :1426 (orphan = 0)`
