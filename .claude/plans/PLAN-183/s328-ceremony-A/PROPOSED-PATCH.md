# PACOTE A — PROPOSED (PLAN-183 W5-b, fechamento) — S328, 2026-08-25

Patch: `.claude/plans/PLAN-183/s328-ceremony-A/A.patch`
Patch-sha256: 2d9326a28ff1d8e51078f7a059e0b90a3b38b720e7296addf15ab9b95f47f05d
Sentinel: `.claude/plans/PLAN-183/wave-s328-A-approved.md`
Land: `.claude/plans/PLAN-183/OWNER-S328-A-LAND.sh --ownership-e2e=run|defer`

---

## 1. O quê

Quatro arquivos. Dois canônicos (`.claude/adr/ADR-194-delivery-route-resolution.md`
e `scripts/install.sh`), o contrato-raiz (`CLAUDE.md`) que descreve o estado do
primeiro, e um teste que viaja com eles porque sem a cura ficaria vermelho no
main (`scripts/tests/test-manifest-delivery-route.sh`).

### 1.1 ADR-194 — `PROPOSED` → `ACCEPTED`, com a §7 de ratificação

O frontmatter e o cabeçalho passam a nomear **quem** ratificou e **quando**: a
assinatura GPG do Owner sobre `PLAN-183/wave-w5-approved.md` (criada
2026-08-25 11:53:12Z; land `6304f66`, 2026-08-25 09:08:28 −0300) e a decisão
verbatim de 2026-08-25 (S328) — «Pista MISTA — braço C (Recomendado)». Os
`Enforcement commits` deixam de ser "pendente" e passam a nomear `6304f66`
(D3 + D1 + emenda OQ-5) e `738007e` (deepen do histórico antes da paridade).

A seção nova **§7 Ratificação da OQ-4 (2026-08-25)** é explicitamente
**RETROATIVA**: o braço C já É o conteúdo de `6304f66`, e a seção diz isso com
as duas referências na árvore pós-land (`w5-ceremony/PROPOSED-PATCH.md:89`
declara "pista MISTA (braço C), que é o conteúdo deste patch";
`_wbm_declared_hash_source` vive em `_framework_manifest_set.sh:376` com um
consumidor em `:1085`). **Nenhuma linha de código muda por causa dela.**

O que a ratificação FIXA, nas palavras da seção: (1) a pista é MISTA — as 5
rotas verbatim na não-condicional, só `.github/CODEOWNERS` na condicional;
(2) o custo é **ZERO** linhas em `scripts/tests/ownership_table.tsv`, e a
moldura "2-3 linhas de TSV" do enunciado da OQ-4 está **refutada** pela medição
da S327; (3) a posse de `docs/` e `.github/` é decidida pelo hash-gate da
entrega mais o `hash_source` declarado do `CODEOWNERS`, **não** por superfície
nova em `_ownership_verdict()`; (4) estender a propriedade "UMA decisão" às
duas árvores continua sendo wave própria (W5-c), com OQ própria.

A seção registra também a lição do **checkout raso**, e registra a DIREÇÃO do
erro como o fato que importa: com `fetch-depth: 1` o hash-gate não enxerga a
geração `v1.2.0` da FONTE e classifica os 3 templates como `PRESERVED`, o que a
paridade maintainer acusa como `STALE 3` (run `32845976930`; reproduzido local:
fonte `--depth 1` ⇒ 3, `--unshallow` ⇒ 0). `PRESERVED` é a direção **SEGURA**:
falta de evidência nunca sobrescreve o arquivo do adopter. Foi ela que
converteu histórico incompleto em divergência **VISÍVEL** em vez de sobrescrita
silenciosa — um gate que respondesse `REFRESHED` à mesma falta de evidência
teria posto bytes do framework sobre bytes do adopter, com o run saindo verde.

Por fim, a §7 declara o que este ADR **não** mantém: o land `6304f66` criou o
arquivo com `status: PROPOSED` (medido em
`git show 6304f66:.claude/adr/ADR-194-delivery-route-resolution.md`, linha 4);
o flip textual é edição canônica posterior e chega ao main por este pacote. **O
ato que ratifica continua sendo a assinatura sobre o sentinel, não o commit que
a reescreve.**

### 1.2 `install.sh` — o discriminante da continuidade vira LINE-EXACT

Sítio: o bloco que decide `FMS_HASH_SOURCE_CODEOWNERS` dentro de
`write_install_manifest()`, sob `_delivered_template_has ".github/CODEOWNERS"`.

**Antes:**

```sh
case "${_CONTINUITY_PATHS:-}" in
  *".github/CODEOWNERS"*) export FMS_HASH_SOURCE_CODEOWNERS="HASH_PRIOR_RECORD" ;;
  *)                      export FMS_HASH_SOURCE_CODEOWNERS="HASH_TARGET" ;;
esac
```

**Depois:** um laço que compara cada linha de `$_CONTINUITY_PATHS` por
igualdade com `.github/CODEOWNERS`, com o default `HASH_TARGET` fixado antes do
laço.

**Por que o `case` é seguro nos vizinhos e não é seguro aqui.** Os três
vizinhos que usam a mesma forma — `SPEC/v1`, `PROTOCOL.md`,
`.claude/.framework-version` — são os únicos literais que qualquer escritor
acrescenta, e **nenhum é substring de outro**. `.github/CODEOWNERS`, ao
contrário, é PREFIXO de `.github/CODEOWNERS.template`; os dois coexistem no
domínio de entrega e são **mutuamente exclusivos por execução**. Uma
continuidade carregando apenas o irmão `.template` respondia
`HASH_PRIOR_RECORD` — isto é, gravava o digest ANTERIOR como baseline de um
arquivo que a execução tinha acabado de RENDERIZAR. `upgrade.sh:4746` já usa a
forma line-exact no sítio equivalente, e `_delivered_template_has` (`:1526`)
usa a mesma pelo mesmo motivo; a cura faz os dois entrypoints pararem de
discordar.

**INERTE hoje, e o patch diz isso.** Nenhum escritor de `_CONTINUITY_PATHS`
acrescenta path de `.github/`, então nenhuma execução de produção alcança o
ramo. A cura é de **FORMA** — e é por isso que ela vem com um controle
positivo: um ramo que ninguém alcança não prova nada por estar verde.

### 1.3 `test-manifest-delivery-route.sh` — S.17 e S.17-control

Cinco asserções (`S.17a`–`S.17e`) mais duas de controle. O bloco e o helper
`_delivered_template_has` são extraídos do `install.sh` por **âncora de
conteúdo**, nunca por número de linha, e a extração tem asserção própria — se
o bloco for renomeado ou movido, o teste diz "toda asserção abaixo é vácua" em
vez de passar em silêncio.

- `S.17a` continuidade com SÓ `.github/CODEOWNERS.template` ⇒ `HASH_TARGET`
- `S.17b` continuidade com `.github/CODEOWNERS` exato ⇒ `HASH_PRIOR_RECORD` (não-regressão)
- `S.17c` continuidade realista (`SPEC/v1` + `PROTOCOL.md` + o irmão `.template`) ⇒ `HASH_TARGET`
- `S.17d` continuidade vazia — o caminho que TODO install fresco toma ⇒ `HASH_TARGET`
- `S.17e` o bloco não voltou a usar `case` sobre `_CONTINUITY_PATHS`
- `S.17-control` a forma **pré-cura verbatim** responde `HASH_PRIOR_RECORD` no
  MESMO input em que a cura responde `HASH_TARGET` — logo `S.17a` não é vácua
- `S.17-control` (2ª perna) o plant e a cura **concordam** no input de
  igualdade exata: o controle isola a colisão de prefixo, não é só "um script
  diferente"

O plant é escrito no próprio teste, **não lido do histórico git**: uma vez
commitada a cura, um controle baseado em `git show` se inverteria em vermelho
permanente.

### 1.4 `CLAUDE.md` — o contrato-raiz deixa de contradizer o ADR

**Uma linha, duas frases, +111 bytes.** Achado do pair-rail (rodadas 1–3), e a
formulação mais precisa é a dele: enquanto o ADR-194 vira `ACCEPTED`, a linha
102 do `CLAUDE.md` continuava dizendo *"status textual `PROPOSED` — o flip é
edição canônica da próxima cerimônia"* e *"OQ-4 foi MEDIDA (…), **não
decidida**"*. Como o `CLAUDE.md` é lido no **Gate 1 de toda sessão** (`§0`),
landar o flip sem esta linha entregaria governança contraditória **no boot**,
por padrão, até alguém notar. As duas frases passam a:

- "ADR-194 (`ACCEPTED` desde o pacote de cerimônia S328-A; a ratificação real é
  o `.asc` commitado sobre `wave-w5-approved.md`, não o commit que reescreve o
  status)"
- "OQ-4 foi MEDIDA (`PLAN-183/w5-oq4-measurement-S327.md`) e RATIFICADA pelo
  Owner em 2026-08-25 — «Pista MISTA — braço C», retroativa a `6304f66`"

Nada mais no arquivo muda: `git diff --stat` = **1 insertion(+), 1 deletion(-)**.

**Coordenação com o closeout desta noite — decisão do CEO, registrada aqui.**
O closeout **NÃO toca a linha 102**; ele só acrescenta um bullet NOVO em §5.
Os dois hunks são disjuntos, e por isso o `finalize-A.sh` re-aplica o pacote com
`git apply --3way` — hunks disjuntos aplicam sozinhos, e um conflito ABORTA
nomeando o hunk em vez de resolver por conta própria.

**Validação do limite de tamanho.** `bash .claude/scripts/validate-governance.sh`
COMPLETO (não `--fast`, que não checa o limite) na árvore-sombra: `rc 0`, 22
gates, **0 erros**, e o gate específico diz
`OK: CLAUDE.md is 32152 bytes (limit 40000)`.

---

## 2. O que NÃO entra, e por quê

**As sete obrigações residuais da W5-b que exigem decisão de produto**
(`PLAN-183` §Open questions itens 5–11) ficam ABERTAS. O CEO não decide no
lugar do Owner:

| # | item | pergunta em aberto |
|---|---|---|
| 5 | `uninstall.sh` com `docs/`+`.github/` no manifesto | o uninstall APAGA um `.github/CODEOWNERS` renderizado, ou o PRESERVA como configuração do adopter? (~180 linhas) |
| 6 | §9.4 F4 — `.github/` fora dos dois scanners de placeholder | `*.template` entregue COM placeholders é defeito, ou é o contrato "o adopter preenche"? (o plano atribui F4 à W2) |
| 7 | §9.3/@1582 — o par install-side | o install REMOVE o arquivo superado, ou deixa o par e só se recusa a REIVINDICAR os dois? (45–70 linhas) |
| 8 | §7(a) — fonte literal em `_register_delivered_template` | colapsar para `_wbm_route_src` (o `install.sh` vira 4º consumidor do TSV) ou manter o literal + cruzamento mecânico? (35–45 linhas) |
| 9 | `_parity_classify.py` resolve a rota renderizada para `None` | um harness de TESTE pode ler o `.install-state.json` NÃO-ASSINADO do adopter? (~55 linhas) |
| 10 | §9.6 F9 — `docs/deny-baseline.md` órfão | entregar o template (7ª rota) ou reescrever as 9 mensagens que o citam? (~40 linhas) |
| 11 | STALE ×2 do `SPEC/` | estender a emenda da OQ-5 ao `SPEC/` agora, ou registrar como W5-c? |

**Três obrigações foram verificadas já ENTREGUES** e retiradas da lista pela
re-derivação read-only da S328 (workflow `wf_b2e30e3d`, 2 leitores sobre fontes
disjuntas + redutor, cada afirmação com `path:line` no HEAD `560dad0`):

- **@815** — comportamento explícito de preservar + fixture pré-install-state:
  `upgrade.sh:4457` mais `test-upgrade-historical-adopter.sh:691-730`
  (H.12/b/c/d/e).
- **@733** — promoção da tabela de rotas: `_WBM_ROUTES_TSV` em
  `_framework_manifest_set.sh:463` e seus leitores.
- **§9.8** — `if: always()` presente em 7 steps do `smoke-install.yml`.

Também não entra: `--ownership-e2e=run` não é decisão deste documento — o
argumento é obrigatório e sem default no LAND, e o `defer` deixa o e2e de ~25
min para o nightly.

---

## 3. Medições

Todas na árvore-sombra do pacote (`git worktree` destacado,
`PYTHONDONTWRITEBYTECODE=1`), com a cura aplicada.

| comando | rc | duração | resultado |
|---|---|---|---|
| `bash -n scripts/install.sh` | 0 | <1 s | — |
| `scripts/tests/test-ownership-verdict-unit.sh` | 0 | <1 s | `PASS=63 FAIL=0` (2 linhas execution-fault puladas por desenho: OWN-0024, OWN-0027) |
| `scripts/tests/test-manifest-delivery-route.sh` | 0 | 20 s | **127 passed / 0 failed** (118 antes + as 9 do S.17) |
| `scripts/tests/test-doctor-delivery-route.sh` | 0 | 218 s | — |
| `scripts/tests/test_install_baseline_manifest.sh` | 1 | ~11 min | **33 passed / 1 failed POR DESENHO**, known-open EXATO `C.6.2` |
| `scripts/tests/test-protocol-pointer-inv4.sh` | 0 | — | — |
| `scripts/tests/test-install-upgrade-parity-e2e.sh --mode maintainer` | 0 | 95 s | **STALE 0**, todas as 5 contagens fatais em 0 |
| `scripts/tests/test-install-upgrade-parity-e2e.sh --mode user` | 0 | 83 s | **STALE 0**, idem |
| `shellcheck -S warning` (scripts do pacote) | 0 | — | limpo |
| `.claude/scripts/validate-governance.sh` (COMPLETO) | 0 | 70 s | 22 gates, 0 erros; `CLAUDE.md is 32152 bytes (limit 40000)` |
| `s328-ceremony-A/test-ceremony-scripts-A.sh` | 0 | 71 s | **PASS=34 FAIL=0**, 12 controles positivos vermelhos como deviam |

`scripts/tests/test-ownership-table.sh` (~25 min) **não** foi rodado local: é o
`--ownership-e2e=run` do LAND, deferido ao nightly com `defer` documentado. O
RED set esperado é `{OWN-0016, OWN-0024, OWN-0027}` — **um all-green ali é
alarme, não vitória.**

Controle positivo re-executado: `S.17-control` — comando e saída no
`rail-round-*.md` e na tabela do relatório da noite.

---

## 4. Rodadas de pair-rail

Registros em `.claude/plans/PLAN-183/s328-ceremony-A/rail-round-*.md`, um por
rodada, cada achado com claim → verificação contra o código → cura ou pushback
com a prova. O veredito literal da última rodada está no cabeçalho do último
registro e no trailer `Pair-Rail-Reviewed:` de `COMMIT-MSG-A.txt`.

---

## 5. Base de CI esperada após o land

Inalterada em toda dimensão medida — este pacote não muda comportamento de
execução existente:

- **Smoke Install** — paridade `maintainer` e `user` com `STALE 0`.
- **Ownership nightly** — RED set `{OWN-0016, OWN-0024, OWN-0027}`. Encolher é
  falha, não sucesso (`ownership-nightly-gate.sh` compara o conjunto EXATO).
- **`test_install_baseline_manifest.sh`** — 33/1 com known-open `C.6.2`.
- **Validate** — o gate de hook-latency continua sujeito à deriva de runner
  medida na S327/S328 (local 77 ms vs CI 209→435 ms no MESMO SHA, sonda
  `UNCONTENDED`); a emenda ao ADR-163 é do pacote B, não deste.
