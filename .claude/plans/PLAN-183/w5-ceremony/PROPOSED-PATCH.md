# PLAN-183 — cerimônia `wave-w5`: D3 (rota única de entrega) + D1 (`docs/` e `.github/` no upgrade) + emenda da OQ-5

**Sessão:** S327 (2026-08-24/25). **Sentinel:** `.claude/plans/PLAN-183/wave-w5-approved.md`.
**Patch:** `w5-ceremony/S327-W5-DELIVERY.patch` (gerado da árvore-sombra por `finalize_patch.py`; `Patch-sha256` no sentinel).
**Scripts:** `OWNER-S327-SIGN.sh` (assina, não aplica) → `OWNER-S327-LAND.sh --dry-run --ownership-e2e=<run|defer>` → `OWNER-S327-LAND.sh --ownership-e2e=<run|defer>` (aplica, verifica V1–V7, faz o staging exato, **commita e empurra**).

Patch-sha256: eaba627e0faa74b33e0ab047cc46eeefdf6ec8b40cb0c26f9975fec8fe8be45f

## 1. O que o pacote entrega

| # | Unidade | Canônico? | O quê |
|---|---|---|---|
| D3 | `scripts/_framework_manifest_set.sh` | **sim** | Terceiro leitor de `scripts/delivery-routes.tsv`: `_wbm_route_src` com varredura linear (idioma de `doctor.sh:418-449`; piso bash 3.2 não tem `declare -A`), `${_rs_transform:-}` com default **vazio**, rota renderizada devolve rc≠0. Enumeração das 6 rotas em `_framework_target_entries()` atrás de `FMS_DELIVERED_TEMPLATES`. |
| D1 | `scripts/upgrade.sh` | **sim** | Entrega de `docs/` e `.github/`, inserida **antes** de `_write_baseline_manifest`; `export FMS_HASH_ROOT="$SOURCE_DIR"` é o que faz D3 morder. |
| D1 | `scripts/install.sh` | **sim** | Sinal de entrega por destino em `install_docs_template` (hoje ele **nunca** seta `INSTALL_ONE_WROTE`, então o idioma de `:1318-1329` não é copiável). |
| OQ-5 | `scripts/upgrade.sh` | **sim** | `.framework-version` presente + install-state ilegível ⇒ tratar como adopter e ENTREGAR, **sem** `_CEREMONY_PERSIST=1`. |
| — | `.github/workflows/smoke-install.yml` | **sim** | `scripts/delivery-routes.tsv` + o teste novo nas duas listas `paths:` (dívida de cerimônia declarada na S325); `if: always()` no controle positivo da paridade, na ownership SPEC/marker, no night-mode e no step novo do adopter histórico (§9.8 do plano — nunca mais `skipped` quando o step principal está vermelho); `timeout-minutes` 32→50 (medido). SHA-pins intocados. |
| — | `.claude/adr/ADR-194-delivery-route-resolution.md` | **sim** | O ADR da decisão (status PROPOSED; a assinatura do Owner o ratifica → ACCEPTED no land). |
| — | `CLAUDE.md` + 9 superfícies derivadas (`README.md`, `README.pt-BR.md`, `docs/{README,ARCHITECTURE,CTO-GUIDE,GUIA-COMPLETO,FAQ}.md`, `npm/README.md`, `CHANGELOG.md`) | não | Bump da contagem de ADRs 194→195 (15 sítios) — `check-claude-md-claims.py` e `verify-counts.sh` verdes na sombra; sem isso o V6a do land morre. |
| — | `scripts/tests/test-upgrade-historical-adopter.sh` (novo), `test-manifest-delivery-route.sh` (novo), `test_install_baseline_manifest.sh` (+C.8), `test-install-upgrade-parity-e2e.sh` (perna cega) | não | Observadores das rotas novas e da emenda OQ-5, com controles negativos demonstrados. |
| — | testes / `docs/` / ADR / plano | não | Observadores das rotas novas + registro da decisão. |

**A ordem não é preferência.** `_framework_manifest_set.sh:430-437` resolve `$FMS_HASH_ROOT/$rel` sem fallback. Alargar a enumeração (D1) antes de curar a resolução (D3) converte ~25 sítios latentes em vivos de uma vez — a mesma forma que este repo já pagou duas vezes (PLAN-182: 16 módulos → resolvedor único; PLAN-167/168: `_ownership_verdict()`).

## 2. Decisão explícita: o e2e de ownership roda DENTRO do land?

**Resposta: é do Owner, por argumento OBRIGATÓRIO sem default. Recomendação do CEO (S327): `defer`** — o e2e de ownership foi executado nesta noite nos três braços do experimento (A/B/C: conjunto RED exato `{OWN-0016, OWN-0024, OWN-0027}`, 62/3/0, 65/65 ids, 1818–2472 s) e na árvore integrada final (resultado em `w5-oq4-measurement-S327.md` §5 e no relatório da S327); o nightly repete a comparação contra `ownership-expected-reds.txt` após o land.

`OWNER-S327-LAND.sh` exige `--ownership-e2e=run|defer`. Não há default porque **um parâmetro que muda o veredito não tem default** — esquecer o argumento tem de ser um erro, nunca uma escolha silenciosa tomada pelo script.

- `defer` (recomendado): o land termina em minutos; o `ownership-nightly.yml` compara o conjunto RED contra `scripts/tests/ownership-expected-reds.txt`. Justificativa: **o e2e de ownership não observa as rotas novas** — `_relpath_for` (`test-ownership-table.sh:117-123`) conhece apenas `spec|protocol|marker`. Ele é o detector de regressão das 3 superfícies existentes, e como detector de regressão o nightly serve.
- `run`: soma ~25 min ao land, com `CELL_TIMEOUT=180` (o default 60 flaka em TIMEOUT sob carga, e o gate trata TIMEOUT como falha mesmo com o id-set intacto).

Em ambos os casos o conjunto esperado sai de `EXPECTED-BASELINE.txt` e **encolher é FALHA**: all-green significa que a tabela-verdade mudou.

## 3. Base de CI esperada — e por que ela é declarada, não inferida

O `main` está **vermelho por desenho** hoje: D1 aberto ⇒ `templates/docs/BRANCH-PROTECTION.md` divergiu (`61025a16` → `966e0571`) ⇒ `STALE 3` na paridade `maintainer`, que é FATAL. Um V-block que compara contra zero seria ruído em toda execução.

Por isso o land lê `w5-ceremony/EXPECTED-BASELINE.txt` e **aborta se o arquivo faltar**. Chaves lidas (todas obrigatórias; chave ausente ⇒ abort nomeado):

```
EXPECTED_PARITY_MAINTAINER_RC
EXPECTED_PARITY_MAINTAINER_STALE
EXPECTED_PARITY_MAINTAINER_MISSING_IN_B
EXPECTED_PARITY_MAINTAINER_UNCLASSIFIED
EXPECTED_PARITY_MAINTAINER_MODE_DIFF
EXPECTED_PARITY_MAINTAINER_ONLY_IN_B_OUTSIDE_CLAUDE
EXPECTED_PARITY_USER_RC
EXPECTED_PARITY_USER_STALE
EXPECTED_PARITY_USER_MISSING_IN_B
EXPECTED_PARITY_USER_UNCLASSIFIED
EXPECTED_PARITY_USER_MODE_DIFF
EXPECTED_PARITY_USER_ONLY_IN_B_OUTSIDE_CLAUDE
EXPECTED_UNIT_ORACLE_FAIL
EXPECTED_OWNERSHIP_RED_IDS
```

Valores esperados **após** o land: `maintainer` rc=0 com as 5 contagens fatais em 0; `user` inalterado em 0; oráculo unitário `FAIL=0`; conjunto RED `{OWN-0016, OWN-0024, OWN-0027}`.

## 4. Matriz de verificação (o land executa, fail-closed)

| passo | o que prova | fonte da verdade |
|---|---|---|
| G0 | árvore limpa nos paths do patch; nenhum path canônico sujo fora do Scope; materiais rastreados; rename aborta | oráculo `--is-canonical`, `porcelain -z` |
| G1 | assinatura GPG válida, signer no rail, campos sem placeholder, `Anchor-SHA == HEAD` | `gpg --verify`, `.claude/sentinel-signers.txt` |
| G2 | o patch no disco é o patch assinado | `Patch-sha256` |
| G3 | aplica limpo | `git apply --check` |
| G4 | `touched − Scope = ∅` **e** `Scope − touched = ∅` | `git apply --numstat` |
| G5 | todo path canônico tocado é **concedido** pelo sentinel; membro do ADR-192 tocado ⇒ manifesto no patch | `_sentinel_grants_path` (a mesma função do hook) |
| V1 | sintaxe dos scripts shell tocados | `bash -n` + `shellcheck -S warning` |
| V2 | manifesto ADR-192 casa, com asserção de **conjunto** | `shasum -a 256 -c` + contagem |
| V3 | oráculo unitário de ownership | `FAIL=0` vs baseline |
| V4 | manifesto de baseline do install | `test_install_baseline_manifest.sh` |
| V5 | paridade install/upgrade nos 2 modos | contagens vs baseline declarada |
| V6 | contagens derivadas, claims do CLAUDE.md, subconjunto pytest | `verify-counts.sh`, `check-claude-md-claims.py` |
| V7 | conjunto RED de ownership | `ownership-nightly-gate.sh` (ou diferido) |

**Verificação não é `grep`** (convergência C3 do debate): a S325 mediu que apontar uma rota para uma fonte *errada mas existente* mantinha os 10 testes verdes — tautologia estrutural. A verdade tem de vir dos call-sites do `install.sh`, independentes da tabela.

## 5. G5 existe porque assinatura válida ≠ autorização

Lição S318: um sentinel com assinatura GPG **válida** concedia **zero** paths. `gpg --verify` responde sobre bytes, não sobre autorização. O G5 chama `_sentinel_grants_path` — a mesma função que o hook usa — para cada path canônico tocado. Um Scope malformado (marcador `BEGIN` sem `END`, `Plans:` depois de `Scope:`, arquivo > 64 KiB) é fail-CLOSED lá dentro e o land para aqui.

## 6. Fora de escopo, declarado

- **OQ-4 — MEDIDA na S327 (`w5-oq4-measurement-S327.md`), veredito proposto = pista MISTA (braço C), que é o conteúdo deste patch.** Fatos medidos: (i) os três braços são indistinguíveis em todos os oráculos de regressão (ownership e2e id-set exato, paridade maintainer/user, unit 63/0, baseline 24/1, rota 24/0); (ii) no install fresco os manifestos de B e C são byte-idênticos (5/5 rotas; a 6ª, `CODEOWNERS.template`, é exclusiva com `CODEOWNERS`); (iii) a diferença entre as pistas é só a continuidade do `CODEOWNERS` RENDERIZADO no upgrade — bytes que não existem em checkout nenhum só podem ser registrados por `hash_source` declarado (`HASH_TARGET` na entrega, `HASH_PRIOR_RECORD` na continuidade), e é exatamente a população da OQ-5 que depende disso; (iv) a moldura "2-3 linhas de TSV" estava ERRADA: o custo real de C sobre B é +22 linhas de código (enumeração + declaração + resolução) e **nenhum braço escreve linha em `scripts/tests/ownership_table.tsv`** (0 linhas neste patch). **Residual de desenho, declarado para ratificação:** a posse das duas árvores é decidida pelo hash-gate da entrega no `upgrade.sh` (por arquivo, contra gerações git da FONTE) + o `hash_source` declarado do `CODEOWNERS` — não por uma superfície nova em `_ownership_verdict()`. Se o Owner quiser estender a propriedade "UMA decisão" (CLAUDE.md §4) às duas árvores, isso é uma wave própria (W5-c: superfície `template` com linhas de 9 dimensões na tabela-verdade), não este patch. **Assinar o sentinel ratifica a pista MISTA e este residual** — não há segundo ato de aprovação.
- **Re-sequenciamento do checklist da W5-b**: terceira decisão do Owner, ainda ABERTA.
- `dist/` é gitignored; espelhos saem de `python3 scripts/build-plugin.py`.

## 7. Riscos conhecidos que o pacote NÃO fecha

- Um workflow ou script novo que leia a tabela de rotas com um mapa próprio nasce fora do censo — o guard de consumidores é quem impede, e ele precisa existir.
- `.github/CODEOWNERS` e `.github/CODEOWNERS.template` são mutuamente exclusivos por execução (`install.sh:1496` elif vs `:1511` else): a enumeração não pode emitir os dois.
- `install_docs_template` nunca setou `INSTALL_ONE_WROTE`; a regra de registro (byte-compare vs só-resultado) precisa ser reconciliada explicitamente entre `install.sh:1318-1329` e `upgrade.sh:3110-3115` — adotar "PRESERVED/SKIPPED ficam fora" derruba os 5 registros num SEGUNDO install e embarca VERDE, porque nenhum Check roda install duas vezes.

## 8. Residuais medidos pelo engenheiro do D1 (S327), declarados

- **Perna cega da paridade (adopter histórico, sem install-state):** com o pin `v1.2.0` a perna sequer sobe (`.framework-version` só entra no `install.sh` na v1.3.0 — v1.2.0 grep=0, v1.3.0=13); com `CEO_PARITY_PIN=v1.3.0` ela mede `IDENTICAL 529 / STALE 2`, e os 2 STALE são `SPEC/v1/{audit-log,state-stores}.schema.md` — `docs/` e `.github/` ficam em **zero**. A emenda foi implementada como `_TEMPLATE_DELIVERY` (entrega das duas árvores) **sem** flipar `CEREMONY_EFFECTIVE`, porque flipar reabre as escritas na raiz que o rc.4 t2 P2 fechou deliberadamente para um install pré-v1.2 `--ceremony user`. Estender a emenda ao `SPEC/` é decisão do Owner, fora deste patch.
- **Latência de um upgrade para adopters pré-v1.3.0:** sem marcador, o 1º upgrade não entrega mas CRIA `.framework-version`; o 2º entrega (`refreshed=3`). Fixado como caso N.2 do teste novo; mover `_refresh_framework_marker` para antes tornaria a evidência auto-realizável e quebraria N.1.
- **Achado e curado durante a implementação:** o `cp` do buffer de render deixava `CODEOWNERS` em modo `0600` (o install grava `0644`); `_up_tpl_write` agora casa o mecanismo por transformação e H.11b o afirma contra um install fresco.
- `if: always()` também roda em job **cancelado** (`!cancelled()` não rodaria); seguiu-se o §9.8 do plano à letra.
- `test_install_baseline_manifest.sh` declara-se gate de land (nenhum workflow o roda): o C.8 novo não é vigiado pela CI; os equivalentes visíveis à CI vivem em `test-upgrade-historical-adopter.sh`, que o `smoke-install.yml` passa a executar.

## 9. Evidência da árvore INTEGRADA (S327, `shadow-fix` = HEAD 56f050c + patch W5 após a rodada 1 do rail)

Bateria `scratchpad/run-arm.sh shadow-fix final2` + `test-upgrade-historical-adopter.sh`, 18:40–19:10 local:

| oráculo | resultado | baseline pré-patch (braço A) |
|---|---|---|
| ownership e2e (`CELL_TIMEOUT=180`) | RED = **`{OWN-0016, OWN-0024, OWN-0027}`** exato, `GREEN=62 RED=3 AMBIG=0 HARNESS-ERR=0`, 65/65 ids, 2051 s | idêntico |
| paridade `--mode maintainer` | **rc=0**, `IDENTICAL=530 PERSONALIZED=31 STALE=0 MISSING_IN_B=0 UNCLASSIFIED=0 ONLY_IN_B=393 ONLY_IN_B_OUTSIDE_CLAUDE=0 MODE_DIFF=0` | rc=1, `STALE=3` (D1) |
| paridade `--mode user` | rc=0, `STALE=0` (inalterado) | idêntico |
| `test-upgrade-historical-adopter.sh` (OQ-5 sem pin, controle negativo, 2º upgrade, CODEOWNERS presente, clone raso rc=9) | **41 passed / 0 failed** (444 s) | n/a (novo) |
| `test-manifest-delivery-route.sh` (3º leitor vs call-sites; rotas hostis; nada fora do alvo) | **34 passed / 0 failed** | n/a (novo) |
| `test_install_baseline_manifest.sh` | 32 passed / 1 failed (**só C.6, pré-existente**) | 24/1 (C.6) |
| oráculo unitário de ownership | PASS=63 FAIL=0 SKIPPED=2 | idêntico |
| `bash -n` ×3 + `shellcheck -S warning` (manifest) | limpos | — |
| `check-claude-md-claims.py`, `verify-counts.sh`, `check-staleness.py` (na sombra) | rc=0 / rc=0 / rc=0 | verify-counts reprovava sem o bump 194→195 |
| pytest `.claude/scripts/tests` + Axis-3/runtime | 5364 passed (4 `test_verify_counts` reprovaram por CORRIDA com o bump em andamento; re-rodados isolados: 4 passed) | — |

Os mesmos oráculos na árvore pré-rodada-1 (`shadow-183`) deram o mesmo veredito (RED set exato, paridade 0/0, 32/1, 24/0 no teste de rota antigo) — a rodada 1 do rail não moveu nenhum número de regressão, só fechou os buracos F2–F6.

**Residuais adicionais declarados (engenheiro D3, S327):** (a) `_register_delivered_template` em `install.sh` recebe o relpath de FONTE como literal por call-site (uma linha abaixo da cópia) em vez de resolver pela tabela — mitigado pela verificação S.2b do teste de rota que cruza os dois conjuntos de argumentos; cura completa = assinatura de um argumento resolvendo pela tabela (install.sh vira 5º consumidor), fora deste patch; (b) o discriminante de continuidade do `install.sh` usa o idioma solto `case *".github/CODEOWNERS"*` dos vizinhos, prefixo de `CODEOWNERS.template` — inerte hoje (`_CONTINUITY_PATHS` só carrega SPEC/PROTOCOL/marcador); a lista de entregues usa comparação exata por linha; (c) `scripts/doctor.sh` consolidado no leitor validado nesta mesma cerimônia (ver `DESIGN-NOTE-DOCTOR.md`) — se a nota não existir no pacote, o doctor ficou como dívida declarada e a rodada 1 do rail registra o achado.
- **Achado do engenheiro do doctor (S327), curado pelo CEO na árvore final:** `upgrade.sh` `_utc_tgt`/`_utc_res` (`cd -P … && pwd -P`) sem `|| true` sob `set -euo pipefail` — um `cd -P` falho abortava o upgrade inteiro em vez de chegar à recusa nomeada (o `doctor.sh` já carregava o `|| true`). Dois sítios corrigidos; `bash -n` + shellcheck delta 0.

## 10. Pair-rail (V2 do PROTOCOL): 8 rodadas, critério de parada e residual

| rodada | árvore | P1 reais | P2 | destino |
|---|---|---|---|---|
| 1 | shadow-183 (D3+D1) | 2 (rota escapa `$TARGET`; teste exige histórico git que a CI depth-1 não tem) | 3 | curados (w3) |
| 2 | shadow-fix | 1 (`--pin` pré-aaf32c7 perde o TSV ⇒ 0 rotas + exit 0) | 2 | curados (w7) |
| 3 | shadow-fix2 | 1 (glob expansion em `FMS_DELIVERED_TEMPLATES` ⇒ 125 paths alheios baselinizados) | 4 | curados (w8) |
| 4 | shadow-fix3 | 1 (fallback registra rotas byte-idênticas SEM entrega ter rodado) | 2 | curados (w9) |
| 5 | shadow-fix4 | 1 (tabela hostil bem-formada via override ⇒ escrita em `.git/hooks/`) | 2 | curados (w10: domínio como constante de código) |
| 6 | shadow-fix5 | 0 | 3 (cabeçalho; override só-por-env; preview de modo) | curados (w11: override APAGADO) |
| 7 | shadow-fix6 | 3 (domínio `.github/` amplo; symlink na FONTE; hard-link no destino) | 1 (`--no-replay`) | curados (w12) |
| 8 | shadow-fix6 (final) | **0** | 2 (fixture do controle positivo; memo do doctor) | curados (CEO) |

Em TODAS as rodadas o revisor abriu com "sentinel assinado ausente" — by-design: o sentinel vive no repositório vivo e a assinatura é o passo do Owner. **Critério de parada (declarado antes da rodada 7):** rodada sem P0/P1 reais ⇒ finalizar; a rodada 8 cumpriu. A classe que o rail perseguiu de 1 a 7 é a de **segurança de escrita do installer** (a mesma do PLAN-185: escapes por `..`, symlink, hard-link, glob, tabela hostil) — as curas viveram no **leitor único** (`_framework_manifest_set.sh`) e nos dois sítios de escrita (`upgrade.sh`, `doctor.sh`), com controle positivo em bytes em cada rodada. **Residual declarado (rodada 5, mantido):** dentro do domínio inerte uma tabela COMMITADA no framework ainda decide *quais* templates entram — isso é decisão de mantenedor, não input de adopter, e o override de tabela foi removido do código de produção (rodada 6). Trailer `Pair-Rail-Reviewed: APPROVE` = este registro.

