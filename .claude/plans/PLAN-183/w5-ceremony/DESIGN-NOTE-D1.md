# DESIGN-NOTE-D1 — `upgrade.sh` entrega `docs/` e `.github/` (PLAN-183 W5, S327)

> Escrito na árvore-sombra `scratchpad/shadow-183`, sobre o D3 (braço C, pista
> MISTA). Todo número aqui foi **medido nesta sessão**; nada foi commitado.

## 1. O defeito e o sítio

`grep -c github scripts/upgrade.sh` = **0**, todo hit de `docs` é comentário —
remedido nesta sessão. O install entrega as duas árvores
(`install_docs_templates` `:1533`, `install_github_templates` `:1580`, ambas
atrás de `CEREMONY != user`); o upgrade nunca entregou. É o D1, e é o que
segurava a paridade em `STALE 3`. A entrega é um bloco de topo em
`scripts/upgrade.sh:3513`, **antes** do `_purge_misinstalled_scan` e do bloco
do manifesto (marcador `# D1-HOOK:` do D3), no formato das seções `.gitignore`
do PLAN-177 — fora do bloco do manifesto porque precisa rodar em `--dry-run`.
**A tabela de rotas é a verdade:** destino → fonte só é respondido por
`scripts/delivery-routes.tsv`, pelo MESMO leitor do gerador canônico
(`_wbm_route_src` / `_wbm_route_dests`, D3). Uma segunda lista de destinos aqui
seria o "ramo local que decide posse" que a §4 do CLAUDE.md proíbe e que este
repo já pagou duas vezes (PLAN-182, PLAN-167).

## 2. A escada de posse

Por destino, parando no primeiro veredito: `--skip` ⇒ `SKIPPED`; fonte
ausente ⇒ `SKIP`; destino (ou ancestral) symlink ⇒ **`PRESERVED`**; destino
ausente ⇒ `INSTALLED`; sem hasher ⇒ `PRESERVED`; `h(dst)==h(src)` ⇒
`IDENTICAL`; `h(dst)` == dígito gravado no manifesto baseline ⇒ `REFRESHED
(recorded baseline digest)`; `h(dst)` ∈ gerações git da FONTE ⇒ `REFRESHED
(pristine prior generation)`; resto ⇒ **`PRESERVED`** (alto).

Os dois REFRESH são mecanismos já estabelecidos: continuidade por dígito
gravado (forma `HASH_PRIOR_RECORD`, `install.sh:2504`) e o refresh hash-gated
por geração de `_refresh_schema_doc` (`:3204-3212`). Nenhum é heurística sobre
conteúdo; os dois são evidência de que o framework pôs aqueles bytes ali.
**Gerações derivadas do git em tempo de execução**, nunca de tags nem de pins
na mão: os pins do `_refresh_schema_doc` carregam um contrato permanente que
já foi violado uma vez (S313, o vermelho do `996d72b`) — derivar **elimina** o
contrato em vez de criar mais cinco. Sem checkout git (tarball) o degrau não
produz nada e cai em `PRESERVED`, que é a direção recuperável.

**Rota de dois estágios (§9.7):** o install faz `cp` e depois reescreve
`docs/*` in-place (`apply_placeholder_substitutions`, `:2226-2231`). Medido:
os dois templates de `docs/` têm **zero** marcadores `{{...}}`, logo comparar
contra o template está certo *hoje* — acidente de conteúdo, declarado no
código. `.github/` não está na lista `explicit_files` (`:2196-2214`).

**O MECANISMO de escrita segue o transform.** Medido: `cp` do buffer de
`mktemp` produz **0600** (mktemp nasce 0600; `cp` POSIX copia os bits da
fonte), o install produz **0644** sob umask 022 — mesmos bytes, modo
diferente, e `MODE_DIFF` é FATAL no portão que esta wave quer verde. Então
`_up_tpl_write` escolhe: identity ⇒ `cp` (igual a `install.sh:1472`),
renderizado ⇒ redireção de shell (igual ao `sed > "$dst"` de `:1576`).

## 3. CODEOWNERS

O handle vem de `request.github_owner` por leitor próprio, com **validação de
charset estrita** (`^[A-Za-z0-9][A-Za-z0-9-]{0,38}$`). Não é decoração: a §9.2
reproduziu `install.sh:1508` abortando com um CODEOWNERS de **0 bytes** quando
o handle continha `/`, e o arquivo vazio sobrevive EXISTS-skipped para sempre.
Com handle: renderiza num temp e **renderiza também as gerações** com o mesmo
handle antes de hashear — a comparação acontece nos bytes ENTREGUES. Sem
handle: arquivo existe ⇒ `PRESERVED (unclaimed)` (o framework não prova posse
sem o handle e não adivinha); ausente ⇒ vale a rota `.template`.
Exclusividade (`:1551` elif vs `:1563` else) resolvida no laço: a rota não
tomada sai `SKIPPED (branch not taken)`, contada, nunca silenciosa — 6 rotas,
5 entregas por run, sempre.

## 4. OQ-5 — sítio, e por que `_CEREMONY_PERSIST` fica 0

Sítio: `scripts/upgrade.sh:820-877`, logo após o `fi` da resolução de
cerimônia, resolvendo `_TEMPLATE_DELIVERY`. Condição: `_CEREMONY_PERSIST == 0`
(cerimônia DESCONHECIDA, não gravada como user) **e**
`.claude/.framework-version` presente.

1. **`_CEREMONY_PERSIST` fica `"0"`** — a inferência nunca chega ao state
   (`:801-803`); persistir tornaria UMA migração perdida permanente. Provado
   por **H.5**: `request.ceremony` no state reescrito é `None`.
2. **`CEREMONY_EFFECTIVE` NÃO é invertido.** Invertê-lo reabriria as
   superfícies de RAIZ para um diretório de cerimônia desconhecida — a escrita
   cross-boundary que o re-pass rc.4 t2 P2 removeu (um install `--ceremony
   user` pré-v1.2 também tem o marcador). A emenda alarga a decisão de
   **ENTREGA**, que é o que o Owner ratificou. Guardado por **H.2b**.

### 4.1 O marcador não existia antes da v1.3.0 — latência de UM upgrade

Achado desta sessão; a perna cega abortou na construção do fixture, que é
para o que a asserção serve. `git show v1.2.0:scripts/install.sh | grep -c
framework-version` ⇒ **0** (idem v1.1.0); em v1.3.0 ⇒ **13**. Medido ponta a
ponta (install real @ v1.2.0, state apagado, upgrade do HEAD):

| run | marcador na decisão | veredito | efeito |
|---|---|---|---|
| 1 | ausente | `DISABLED` | **cria** `.claude/.framework-version` |
| 2 | presente | `ENABLED — OQ-5 amendment` | `routes=6 refreshed=3 identical=2 skipped=1` |

**A população é alcançada com um upgrade de atraso — não é perdida.** A
latência é deliberada: mover `_refresh_framework_marker` para antes da decisão
tornaria a evidência auto-realizável e um diretório nunca instalado passaria a
ser tratado como adopter, que é o que **N.1** proíbe. Fixada como **N.2**
(fixture sintético, sem dependência de tag). A perna cega só constrói fixture
com `CEO_PARITY_PIN=v1.3.0`; no pin default aborta `rc=9` imprimindo a medição
e o comando certo.

## 5. Registro no manifesto

`FMS_DELIVERED_TEMPLATES` recebe INSTALLED/REFRESHED/IDENTICAL;
PRESERVED/SKIPPED ficam fora. Quando a entrega RODOU ela é a autoridade e o
bloco de registro do D3 consome a lista dela (`_D1_DELIVERY_RAN=1`) em vez de
recomputar por byte-compare — dois vereditos de posse poderiam discordar do
que acabou de decidir a escrita; o fallback do D3 fica **intocado** para runs
sem entrega (user, `--dry-run`, pré-condição falha).
`FMS_HASH_SOURCE_CODEOWNERS` é declarado **em toda via**: `HASH_TARGET` quando
o D1 registrou, `HASH_PRIOR_RECORD` no fallback — declarar só na continuidade é
o precedente das **24 células** (`install.sh:2508-2511`). Na quebra da lei de
conservação limpa-se a LISTA e **nunca** a flag `RAN`: limpar a flag devolveria
o registro ao byte-compare do D3, que registraria exatamente o que o ramo
recusou avalizar — um fail-OPEN vestido de fail-closed.

## 6. Checks e números medidos

Pré-condição AC-9 antes de qualquer entrega: `routes=0` é FALHA nomeada
fail-closed. Verificado ao vivo com `FMS_DELIVERY_ROUTES_TSV=/nonexistent`:
`routes enumerated: 0` → `PRECONDITION FAILED` → **0** entradas de CODEOWNERS
no manifesto. Mais a **lei de conservação** (`installed+refreshed+identical+
preserved+skipped == routes`), que pega um destino caindo num buraco da
análise de casos. A igualdade a **6** é asserção do TESTE, não do script: um
`6` hardcoded no script seria segunda cópia da tabela.

| oráculo | antes | depois |
|---|---|---|
| paridade `--mode maintainer` | `IDENTICAL 527 / STALE 3 / UNCLASSIFIED 0`, rc=1 | `IDENTICAL 530 / STALE 0 / UNCLASSIFIED 0`, **rc=0** |
| paridade `--mode user` | `STALE 0`, rc=0 | `STALE 0`, rc=0 (inalterado) |
| paridade cega `CEO_PARITY_PIN=v1.3.0 --blind-install-state` | (não existia) | `IDENTICAL 529 / STALE 2`, rc=1 |
| `test_install_baseline_manifest.sh` | 24 passed / 1 failed | **32 passed / 1 failed** (só C.6, pré-existente) |
| `test-upgrade-historical-adopter.sh` (novo) | — | **33 passed / 0 failed**, 357 s |
| `test-manifest-delivery-route.sh` (D3) | 24/0 | 24/0 |
| oráculo unitário de ownership | `PASS=63 FAIL=0 SKIPPED=2` | idêntico |
| `shellcheck -S warning` (5 `.sh`) | limpo | limpo, **delta 0** |

Os 3 STALE eram `docs/BRANCH-PROTECTION.md`, `…/validate.yml.template` e
`…/benchmarks.yml.template`; `docs/rotation-log.md` e
`.github/CODEOWNERS.template` são byte-idênticos pin↔HEAD — um Check que só os
tocasse passaria vacuamente.

**A perna cega responde a OQ-5.** Os 2 STALE restantes são
`SPEC/v1/audit-log.schema.md` e `SPEC/v1/state-stores.schema.md` —
superfícies de RAIZ, gateadas em `CEREMONY_EFFECTIVE != user`, exatamente o
limite declarado na §4. `docs/` e `.github/` aparecem **zero** vezes na lista
fatal: **a emenda alcança as duas árvores na população histórica**. Alargar
para `SPEC/v1` é decisão do Owner, com o custo nomeado.

`scripts/tests/test-upgrade-historical-adopter.sh` (novo, ligado ao CI, com
`if: always()`): H.1 rotas; H.2/H.2b a emenda decide e a cerimônia não muda;
H.3 REFRESH de geração plantada **a partir do git**; H.4 edição do adopter
preservada byte-idêntica; H.5 persistência 0; H.6 exclusividade nas duas
direções; H.7 handle hostil recusado; H.8 symlink pendente preservado e **nada
escrito fora do `$TARGET`**; H.9 idempotência (AC-10); H.10 `--dry-run` prevê
e não escreve; H.11 modo do CODEOWNERS entregue == modo do install fresco;
**N.1/N.2** controles negativos.

No workflow (`smoke-install.yml`, canônico): `if: always()` nos três steps que
o run `32639637945` mostrou `skipped` com o principal vermelho — controle
positivo da paridade, ownership de delivery-record e night-mode — mais o step
novo; `scripts/delivery-routes.tsv` e o teste novo entram nas **duas** listas
`paths:`, que a §9.8 e a medição da S325 (grep = 0 para a tabela) pediam.
Trade-off declarado: `always()` também roda em job CANCELADO; `!cancelled()`
excluiria esse caso, mas `always()` é o que a §9.8 especifica.
`timeout-minutes` **32 → 50**, pela mesma doutrina do arquivo (medido, com
margem anti-flake): +2 installs e +8 upgrades completos, 357 s de relógio
local sob carga, 12-18 min de CI ao fator 2-3x — e com `always()` um portão
principal VERMELHO deixa de encerrar o job cedo, então o pior caso passou a
rodar todos os steps, que é exatamente o objetivo.

`test_install_baseline_manifest.sh` ganha **C.8**: cada rota verbatim gravada
com o dígito da **FONTE**, a renderizada com o dígito dos **bytes entregues**,
a rota não tomada **ausente**, e um contador que vai RED se zero rotas forem
checadas.

## 7. O controle negativo foi DEMONSTRADO, não afirmado

Plante → RED → despante → GREEN, executado: cópia pristina de `upgrade.sh`
salva (`sha256 9588b35f…`); plante `_TEMPLATE_DELIVERY=0` → `=1` (guarda da
OQ-5 neutralizada); run ⇒ **`RESULT: 26 passed, 4 failed`, rc=1**, com `N.1`,
`N.1b`, `N.1c` e `N.2c` vermelhas — exatamente as asserções que dependem da
guarda, e só elas, porque o plante só muda o ramo `else`; restauro pela cópia
com `sha256` re-conferido byte a byte e o marcador do plante ausente (nunca
`git checkout`, que destruiria as mudanças não-commitadas da sombra); re-run
limpo na tabela da §6.

**Custo, medido e agido:** a versão sem cache levou **372 s** sob carga; ao
fator 2-3x deste workflow seriam 12-18 min de CI sobre um job que já orça 32.
O teste passou a instalar **duas** bases (uma sem e uma com `--github-owner`,
porque a flag muda QUAL linha de CODEOWNERS o install entrega) e a `cp -R` as
demais fixtures. A equivalência não é suposta: todas as fixtures se chamam
`.../adopter`, então `{{PROJECT_NAME}}` produz bytes idênticos, e nenhum leitor
do caminho de upgrade consulta o campo `target` do install-state.
