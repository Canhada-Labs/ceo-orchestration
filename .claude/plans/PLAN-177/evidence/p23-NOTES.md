# NOTES — PLAN-177 W0 itens 2/3 (P1-2, P1-3 rota ii), v2 pós-consenso

Base: `3842d4f`. Ambos os patches passam `git apply --check` em árvore
pristina nessa base. Nenhuma escrita no repo canônico.

## Entregáveis

| Arquivo | Conteúdo |
|---|---|
| `p23-docs.patch` | `npm/INTEGRITY.md`, `npm/SHA256SUMS.txt`, `SUPPORT.md`, `README.md`, `.github/release-checklist.md` |
| `p23-gates.patch` | `.claude/scripts/tests/test_release_bump_sites.py` (SCAN_ROOTS + 6 testes) |
| `CONTROLES.md` | os 12 reds, saída literal |
| `controls.sh` + `plant.py` | reprodução dos controles (um comando) |

Separados porque o pack canônico do W1 não os envolve: **nenhum** dos 6
arquivos está sob canonical-guard — verificado em `_CANONICAL_GUARDS`
(`check_canonical_edit.py:115-240`; só `.claude/adr/README.md` está lá, não o
`README.md` da raiz). Podem landar juntos num commit livre.

## Os 5 ajustes do consenso — como ficaram

**1. CF-5 — `SCAN_ROOTS` recebe ARQUIVOS, não a pasta.** Entraram
`"npm/INTEGRITY.md"` e `"npm/README.md"`. O raciocínio do consenso está certo e
**meu scanner tinha o mesmo defeito**: a v1 fazia `rglob("npm/**/*.md")`, que
desceria em `npm/.claude/**` e `npm/templates/**` do bundle espelhado. Agora as
superfícies do teste de semver são **derivadas** de `SCAN_ROOTS`
(`NPM_DOC_SURFACES = [r for r in SCAN_ROOTS if r.startswith("npm/") and
r.endswith(".md")]`) — acrescentar uma terceira superfície lá estende a regra
aqui, e as duas listas não podem divergir. Controle positivo planta o semver
**no próprio `npm/INTEGRITY.md` do fixture** (e no `npm/README.md`), nos mesmos
paths relativos: prova a superfície, não a regra.

**2. CF-6 — coluna `Status` de conjunto fechado.** Tabela reescrita para 4
colunas. `Status ∈ {enforced, deferred, operator}`; qualquer outro valor é red
(fail-closed em vocabulário desconhecido — C4). Só linhas `enforced` são lidas
para verificação de mecanismo; a forma é `` `<workflow>` step "<nome>" ``, com
workflow que existe e `- name:` casando por **igualdade exata**
(`step not in _yaml_step_names(wf)`, nunca substring — C2 planta um PREFIXO
válido de propósito). Piso `_MIN_ENFORCED_PAIRS = 2` (C5).

**3. CF-8 — sweep do arquivo inteiro.** Os 3 achados verificados por mim antes
de curar (ver C9). §Signing keys reescrita: a chave que existe é
`.claude/trust/owner.asc`, e o que ela assina são **tags**, não tarballs; as
duas fontes fantasma são nomeadas como inexistentes. §Reproducible-build ganhou
`Status: specification only — nothing asserts it, in any workflow`. §CI
verification descreve o packlist gate real (`npm packlist gate …`,
`validate.yml:1030`) e diz o que ele **não** prova (`--dry-run` não escreve
archive ⇒ nada sobre bytes) — a v1 desse arquivo descrevia um step com
`SOURCE_DATE_EPOCH` que nunca existiu.

**4. Receita de consumidor REMOVIDA**, não ressalvada. O gate proíbe o literal
`sha256sum -c SHA256SUMS.txt` no arquivo — inclusive na frase que explica a
remoção (dois reds do meu próprio texto durante o desenvolvimento; a redação
final descreve a receita sem reproduzi-la).

**5. Sweep de vocabulário** em `README.md`, `npm/README.md`, `SECURITY.md`,
`docs/`. Um achado real, curado: `README.md:98` alegava **"SLSA 3
provenance"** — `npm publish --provenance` é Level **2**, e o próprio
`INTEGRITY.md` diz que Level 3 está fora de escopo. Mesma linha também dizia
"GitHub releases ship SHA-256 checksums" no plural/agregado, enquanto
`SECURITY.md:79-80` afirma que a cobertura é `install.sh` **só**. As duas
curadas e pinadas por teste (C11). `SECURITY.md:75-81` é o contra-exemplo
honesto do repo e não precisou de nada; `npm/README.md` não tinha claim de
enforcement.

### Nada ficou como "item nomeado do v1.4.0" por este lote

O sweep não deixou resíduo em aberto nos arquivos varridos. Fora de escopo por
decisão prévia (não achados novos): rota (i) do P1-3 (gerar/hashar o tarball) e
`scripts/install-npm.sh:182-184` — comentário igualmente falso ("CI verification
(npm-publish.yml) computes the checksum … and appends to the release notes"),
**canônica**, vai no pack do W1.

## Outras decisões

**`npm/INTEGRITY.md` não é site de bump.** Prosa version-neutral, `VERSION`
como autoridade única, conforme `_release_bump_sites.py:82-91` (writer sem
oráculo = dead rule reintroduzida na escrita). O texto diz isso explicitamente,
para o próximo leitor não "consertar" adicionando a linha de volta.

**Exclusões do predicado de semver** (documentadas no código): `SHA256SUMS.txt`
(nomes de tarball = dado histórico), `.npmignore` (incidentes citados pela
versão em que ocorreram), `package.json` (site de bump com oráculo). Isenção
interna: linha de stamp, que é ela própria um site de bump.

**Linhas novas na tabela para controles que EXISTEM** e não estavam
documentados: self-SHA trailer, tag/SHA binding, packlist. Documentar o que
roda é o outro lado da honestidade — e é o que dá ao piso de contagem algo real
para contar.

**Fixtures dos controles in-test são DERIVADOS da tabela parseada.** A v1
ancorava num literal de linha; ao plantar o defeito nessa mesma linha o fixture
não se construía e o teste falhava pelo motivo errado. O guard fail-loud
(`assert renamed != doc`) ficou.

**`test_checklist_attributes_repo_exhaustiveness_to_the_scanner`** exige que
toda entrada de `SCAN_ROOTS` apareça na prosa do checklist. Limite honesto: o
assert é substring, então pega raiz **adicionada** e não documentada (o caso
que importa), não uma renomeação para um prefixo já presente.

## Cobertura de teste rodada

- `test_release_bump_sites.py`: **58 passed** (52 + 6 novos), no clone e na
  árvore pristina pós-`git apply`.
- `test_install_npm_sha256.py`: 11 passed. `test_check_canonical_doc_freshness.py`:
  9 passed. São, por grep, os únicos outros arquivos de teste que leem qualquer
  um dos 6 arquivos tocados.
- `.claude/scripts/tests` inteiro (230 arquivos), na árvore **pristina** em
  `3842d4f` com os dois patches finais aplicados: **5049 passed, 24 skipped,
  exit 0 em 15min49s**. (Baseline antes deste lote, mesma raiz: 5047 passed —
  a diferença são os testes novos, e nenhum pré-existente virou vermelho.)

## Riscos de merge

`p23-gates.patch` toca `test_release_bump_sites.py` em dois pontos:
`SCAN_ROOTS` (~:1158) e um bloco inserido antes de
`test_checklist_documents_the_new_driver_and_the_await_gate_recovery` (~:1275).
Se o agente do P1-4 acrescentar testes no **fim** do arquivo ou editar
`write_verdict`/`arm_verdict` (topo), não há conflito.
