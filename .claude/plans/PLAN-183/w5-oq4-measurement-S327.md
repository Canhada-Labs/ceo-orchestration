# PLAN-183 W5 — OQ-4: medição da PISTA do gerador (braços A/B/C)

> **S327 night-run, 2026-08-24.** Executado numa árvore-sombra
> (`scratchpad/shadow-183`, clone `--local` de `main@56f050c`, tag `v1.2.0`
> presente). **Nenhuma linha foi escrita em `scripts/tests/ownership_table.tsv`**
> — a regra do Owner ("zero linhas até o veredito da OQ-4") está respeitada e
> foi verificada por `git status` da sombra ao fim de cada braço.
>
> **Veredito: pendente (Owner ratifica).**

---

## 0. O que cada braço é

| braço | pista do gerador para as 6 rotas |
|---|---|
| **A** | HEAD intocado (`56f050c`). Baseline. |
| **B** | As 6 rotas na pista **NÃO-condicional**: enumeração + leitor de rota + resolução por rota. |
| **C** | Pista **MISTA**: as 5 rotas verbatim ficam na não-condicional (idêntico ao B); só `.github/CODEOWNERS` (renderizada) entra na **condicional**. |

B e C **não** são alternativas de mesmo custo: **C é B mais 22 linhas de código**.
A pista mista é um superconjunto estrito, não um atalho.

---

## 1. Decisões do CEO aplicadas (e o que a medição disse sobre cada uma)

### C5 — entradas de ARQUIVO, nunca de DIRETÓRIO
`_framework_target_entries()` enumera exatamente os relpaths de DESTINO que o
caller entregou nesta execução, passados numa variável nova
`FMS_DELIVERED_TEMPLATES` (separada por newline). `docs/` e `.github/` são
árvores do ADOPTER que apenas CONTÊM entregas do framework; uma entrada de
diretório faria `_framework_manifest_files` caminhá-las e registrar cada arquivo
do adopter como framework-owned — a classe que o `uninstall` apaga por hash.

A exclusividade `.github/CODEOWNERS` × `.github/CODEOWNERS.template`
(`install.sh:1496` elif × `:1511` else) é **herdada do caller**: só o ramo que
rodou faz o append, então o gerador nunca precisa conhecê-la. Confirmado em
execução: com `--github-owner`, o conjunto entregue tem **5** destinos, nunca 6.

### Regra de registro — byte-compare (não "result-only")
Espelha `install.sh:1318-1329`: registra quando ESTA execução escreveu **OU**
quando o alvo pré-existente é byte-idêntico à FONTE resolvida.

**Medido, não assumido — este era o risco nomeado no brief.** Um SEGUNDO
install consecutivo (todos os 5 destinos caem em `EXISTS (skipping)`) mantém
**5/5 registros**. A regra "result-only" derrubaria os 5 e embarcaria VERDE,
porque nenhum Check roda install duas vezes.

Armadilha confirmada e curada: `install_docs_template` (`install.sh:1446`)
**nunca** seta `INSTALL_ONE_WROTE` — essa variável é de `install_one`
(`:877/:905/:919`). Reusá-la faria uma entrega de docs sobrescrever o flag que
os registros de schema leem duas chamadas adiante. Flag própria
(`_DOCS_TEMPLATE_WROTE`), resetada em TODA entrada da função.

Para a rota RENDERIZADA o byte-compare é contra os **bytes renderizados**
(render para tempfile + `cmp -s`), nunca contra o `.template`: um arquivo do
adopter que por acaso casasse com o template não-renderizado não é uma entrega
do framework.

`PRESERVED` (difere) e `SKIPPED` (fonte ausente) ficam **fora**.

### Declarar em TODA rota de entrega, nunca só na continuidade
Precedente de custo no próprio código (`install.sh:2508-2511`): a tentativa
anterior desta wave regrediu 24 células por deixar installs frescos
não-declarados. No braço C, `FMS_HASH_SOURCE_CODEOWNERS` é exportado tanto na
entrega fresca (`HASH_TARGET`) quanto na continuidade (`HASH_PRIOR_RECORD`).

---

## 2. Oráculos rápidos por braço

| oráculo | A (HEAD) | B | C |
|---|---|---|---|
| `bash -n` (3 scripts + teste novo) | OK | **OK** | **OK** |
| `shellcheck -S warning` (arquivo inteiro, 4 arquivos) | limpo | **limpo** | **limpo** |
| `test-ownership-verdict-unit.sh --quiet` | PASS=63 FAIL=0 SKIPPED=2 | **PASS=63 FAIL=0 SKIPPED=2** | **PASS=63 FAIL=0 SKIPPED=2** |
| `test-manifest-delivery-route.sh` (novo) | n/a (não existe) | **24 passed / 0 failed** | **24 passed / 0 failed** |
| `test_install_baseline_manifest.sh` | **24 passed / 1 failed — rc=1** | não executado | **24 passed / 1 failed — rc=1** (idêntico ao A, mesma falha) |

> **O braço A já é VERMELHO neste oráculo.** A falha é
> `C.6 root PROTOCOL.md NOT backed up without a manifest`, **pré-existente em
> `56f050c`** e não causada por nenhum braço. Julgue B e C contra
> `24/1`, **nunca contra zero**.
>
> Nota de método: o wrapper de background reportou "exit code 0" porque o
> último comando da lista era um `echo`. O rc real (`1`) foi capturado com
> `echo "rc=$?"` dentro do arquivo. É a classe de erro que a memória
> `feedback-pytest-pipe-tail-masks-exit` registra.

### Controles positivos do teste novo (VERMELHO → VERDE, todos demonstrados)

Rodados contra uma **CÓPIA** da árvore em `mktemp -d`; nenhum arquivo rastreado
foi mutado (`scripts/delivery-routes.tsv` intocado, por FILE ASSIGNMENT).

| controle | resultado | evidência |
|---|---|---|
| linha re-apontada para fonte **errada-mas-existente** | **RED 23/1** | `FAIL S.2 docs/BRANCH-PROTECTION.md: install.sh copies from 'templates/docs/BRANCH-PROTECTION.md' but the route table answers … 'templates/docs/rotation-log.md' — fix the row for '…'` |
| tabela **apagada** | **RED 13/11** | `FAIL S.0 shared route table MISSING at …` + 5×`FAIL S.2` + `FAIL S.6 … dropped SILENTLY` |
| linha **renderizada virada para `identity`** | **RED 21/3** | `FAIL S.6 a RENDERED destination was recorded (1955b01a…)` — exatamente a classe de vazamento do CODEOWNERS vivo |
| tabela restaurada | **GREEN 24/0** | — |

**A verificação não é `grep` (convergência C3).** As expectativas do S.2 são
derivadas por parsing dos **call-sites do `install.sh`** (`install_docs_template
"<src>" "<dst>"` + o sítio do `sed s/{{OWNER_HANDLE}}/…/`), nunca da própria
tabela. S.1 falha se o parser extrair menos de 5 call-sites ou não achar o sítio
renderizado — sem isso, todo o resto seria vacuoso. S.2b cruza os argumentos de
`_register_delivered_template` contra os do `install_docs_template`, então um
typo no registro (que faria o byte-compare comparar o arquivo ERRADO) sai
vermelho.

---

## 3. `git diff --stat` — o orçamento real da OQ-4

### Total (inclui o teste novo, 355 linhas)

| arquivo | B | C |
|---|---|---|
| `scripts/_framework_manifest_set.sh` | 130 (+/−2) | 141 (+/−2) |
| `scripts/install.sh` | 72 | 97 |
| `scripts/upgrade.sh` | 54 | 67 |
| `scripts/tests/test-manifest-delivery-route.sh` (novo) | 355 | 355 |
| **soma adicionada** | **611** | **660** |

### Só os 3 scripts CANÔNICOS (o número que decide a cerimônia)

| métrica | B | C | C − B |
|---|---|---|---|
| linhas adicionadas | 256 | 305 | **+49** |
| **linhas de código** (sem comentário/branco) | **136** | **158** | **+22** |
| linhas de comentário | 113 | 139 | +26 |

**A hipótese "MISTA encolhe a OQ-4 de ~13 para ~2-3 linhas" está REFUTADA**, e a
razão é a que o próprio brief já havia corrigido: o orçamento nunca foi "linhas
de TSV". É *enumeração + declaração + resolução*. Medido, a pista mista **custa
+22 linhas de código sobre a não-condicional**, porque C = B **mais** o ramo
condicional. Nenhum dos dois braços escreve uma linha em
`scripts/tests/ownership_table.tsv`.

> **Achado de instrumento, verificado no arquivo:** o e2e de ownership não pode
> observar nenhuma das 6 rotas. `_relpath_for`
> (`scripts/tests/test-ownership-table.sh:117-123`) só conhece
> `spec|protocol|marker` e devolve rc=1 para o resto. Ele é o detector de
> REGRESSÃO das 3 superfícies existentes, não um observador das novas. Os
> observadores são `test-install-upgrade-parity-e2e.sh` e
> `test_install_baseline_manifest.sh`.

---

## 4. O que cada braço REGISTRA (medição de campo, install + upgrade reais)

Alvo `mktemp -d` + `git init`, `install.sh … --profile core --github-owner
Canhada-Labs`, depois `upgrade.sh … --no-diff-warn`.

| braço | install | upgrade | `.github/CODEOWNERS` no upgrade |
|---|---|---|---|
| **A** | **0/5** | **0/5** | ausente — nunca enumerado |
| **B** | **5/5** | **4/5** | **DERRUBADO, com breadcrumb nomeando o path** |
| **C** | **5/5** | **5/5** | **mantido, com o digest RENDERIZADO** |

("5", não "6": as duas linhas de CODEOWNERS são mutuamente exclusivas por
execução.)

**O braço A confirma o achado bloqueante do brief — D3 é latente-por-não-entrada.**
Com HEAD, as 6 rotas nunca chegam ao resolvedor: **0 registros**, install e
upgrade. Um braço que corrigisse apenas a resolução seria byte-idêntico ao
baseline e a corrida seria vacuosa.

### Prova de que a resolução por rota está CERTA (não só presente)

| path | digest registrado (B e C) | template | homônimo da RAIZ |
|---|---|---|---|
| `docs/BRANCH-PROTECTION.md` | `966e0571…` | `966e0571…` (8.468 b) | `01eab4f2…` (21.513 b) |
| `docs/rotation-log.md` | `0ab61d16…` | `0ab61d16…` (536 b) | `0249879f…` (6.940 b) |

O digest gravado é o do **template**, não o do homônimo — que é o defeito D3.
E `.github/workflows/validate.yml.template` **não existe** na raiz da fonte
(verificado): sem o leitor de rota ele cai no `continue` e some do baseline em
SILÊNCIO; em B e C ele está registrado.

### O breadcrumb do braço B (a deficiência medida, não escondida)

```
NOTE: .github/CODEOWNERS is delivered through a TRANSFORM (or its route row is
      malformed) — no framework source bytes on this lane; NOT recorded
      (fail-closed)
```

Para que essa linha pudesse sequer disparar foi preciso REGISTRAR a rota
renderizada no upgrade sob continuidade de ownership (o alvo existe **e** o
manifesto anterior já o registrava — a mesma regra de evidência do
`PROTOCOL.md`/`HASH_PRIOR_RECORD`). Sem isso o destino seria descartado uma
camada antes, no registro, e a deficiência do braço B apareceria como um
silencioso 4-vs-5. Essa peça é compartilhada por B e C.

### O que o braço C compra, medido

`.github/CODEOWNERS` sobrevive ao upgrade com `d3b88d17…` = os **bytes
renderizados no alvo**, que são comprovadamente ≠ do template
`1955b01a…`. Isto é, a pista condicional **não** vaza a fonte: ela carrega o que
foi entregue. É a única pista das duas capaz de expressar isso, porque os bytes
renderizados não existem em checkout nenhum.

### Checagens de regressão nas rotas onde um defeito se esconderia (braço C, installs reais)

| caso | esperado | medido |
|---|---|---|
| `--ceremony user` | 0 registros (as duas funções de entrega são gateadas em `CEREMONY != user`) | **0** ✓ |
| sem `--github-owner` | 5 registros, com `.github/CODEOWNERS.template` (`1955b01a…`) e **sem** `.github/CODEOWNERS` | **5, exatamente assim** ✓ |
| `--dry-run` | nenhum manifesto escrito | **nenhum** ✓ |

O caso do meio é o que fecha o risco "as duas linhas de CODEOWNERS são
mutuamente exclusivas ⇒ a enumeração não pode emitir as duas, ou uma vira um
miss espúrio garantido": a lista entregue carrega **só** o ramo que rodou.

### Controle de SOBRE-REIVINDICAÇÃO — nos dois sentidos (braço C, installs reais)

Esta é a classe que o `uninstall` apaga: registrar bytes do ADOPTER como
framework-owned. Testada nos dois sentidos, porque um teste de um sentido só
prova metade.

| cenário | esperado | medido |
|---|---|---|
| alvo já tem `.github/CODEOWNERS` **DIFERENTE** (`* @some-other-org`) e `docs/BRANCH-PROTECTION.md` próprio | nenhum dos dois registrado; arquivos intactos | **nenhum registrado** (só as 3 rotas realmente entregues); os dois arquivos **byte-intactos** ✓ |
| alvo já tem `.github/CODEOWNERS` **byte-idêntico** ao que renderizaríamos | registrado | **registrado** (`d3b88d17…`) ✓ |

A primeira linha prova que a metade `cmp -s` não sobre-reivindica; a segunda
prova que ela não é decorativa. Uma regra "result-only" passaria na primeira e
FALHARIA na segunda — e é a segunda que descreve o adopter que rodou install e
depois upgrade.

---

## 5. Resultados lentos — MEDIDOS pelo CEO (S327, 16:11–17:40 local)

Executados pelo CEO em clones separados (`shadow-A` pristine; `shadow-B`/`shadow-C` = pristine + diff do braço), julgando B e C contra os números **medidos do braço A** — nunca contra a prosa do CLAUDE.md e nunca contra zero (o main é VERMELHO por desenho: D1 aberto ⇒ `STALE 3`). Controle da cadeia viva de auditoria: o delta durante as corridas (645/320/316 linhas) é integralmente eventos de ferramenta dos agentes da sessão (`tool_call_lifecycle_recorded`, `output_scan_*`) — os e2e **não** escrevem na cadeia.

- [x] **e2e de ownership** (CEO, `CELL_TIMEOUT=180`, clones pristine de `56f050c` + `arm{B,C}.diff`; `scratchpad/run-arm.sh`): nos TRÊS braços o conjunto RED é **exatamente** `{OWN-0016, OWN-0024, OWN-0027}` = `ownership-expected-reds.txt`, `GREEN=62 RED=3 AMBIG=0 HARNESS-ERR=0`, 65/65 ids, zero TIMEOUT/ESCAPE/AMBIG, rc=1 (esperado). Tempo: A 1818 s (sozinho), B 2472 s e C 2456 s (em paralelo, máquina carregada) — nenhum TIMEOUT mesmo sob carga.
      - A: `{0016,0024,0027}` 62/3/0  B: `{0016,0024,0027}` 62/3/0  C: `{0016,0024,0027}` 62/3/0 → **delta vs expected = NONE nos três; nenhuma célula mudou de cor (a regressão de 24 células NÃO se repetiu).**
- [x] **parity e2e `--mode maintainer`** (CEO): idêntico nos três braços — `IDENTICAL=527 PERSONALIZED=31 STALE=3 MISSING_IN_B=0 UNCLASSIFIED=0 ONLY_IN_B=393 ONLY_IN_B_OUTSIDE_CLAUDE=0 MODE_DIFF=0`, rc=1 (A 58 s, B 90 s, C 91 s). D3 sozinho não muda a paridade: os 3 STALE são o D1 (upgrade ainda não entrega), como previsto em §8.8 do plano.
      - A = B = C (linha acima)
- [x] **parity e2e `--mode user`** (CEO): idêntico nos três braços — `IDENTICAL=488 PERSONALIZED=31 STALE=0 MISSING_IN_B=0 UNCLASSIFIED=0 ONLY_IN_B=393 ONLY_IN_B_OUTSIDE_CLAUDE=0 MODE_DIFF=0`, rc=0 (A 55 s, B 71 s, C 70 s). **0 fatais nos três.**
      - A = B = C (linha acima)
- [x] **Sonda independente do CEO — manifesto no install fresco** (`install.sh <alvo> --profile core --ceremony maintainer --github-owner probeowner`, um alvo por braço, `scratchpad/manifest-probe/`): A registra **0/5** rotas (524 linhas no manifesto — o D3 latente-por-não-entrada confirmado em campo); B e C registram **5/5** (529 linhas; a 6ª rota, `CODEOWNERS.template`, é exclusiva com `CODEOWNERS` quando há owner), e as 5 linhas são **byte-idênticas entre B e C** — cada digest é igual ao `shasum -a 256` do arquivo entregue (`docs/BRANCH-PROTECTION.md` = `966e0571…` = sha do template em HEAD, o mesmo hash que a paridade acusa como divergente do pin `61025a16…`). Conclusão: no install fresco as pistas são indistinguíveis; a diferença entre B e C é SÓ a continuidade do `CODEOWNERS` renderizado no upgrade (§4 e §6), onde a pista não-condicional não tem bytes para hashear.
- [x] ~~`test_install_baseline_manifest.sh` no braço **C**~~ — **EXECUTADO:
      24 passed / 1 failed, rc=1.** Byte a byte o mesmo resultado do braço A,
      com a MESMA única falha
      (`C.6 root PROTOCOL.md NOT backed up without a manifest`). Critério
      "não pior que o A" **atendido**; "verde" era inalcançável porque o A já
      é vermelho.

---

## 6. Recomendação (evidência, não veredito)

> **Posição do CEO (S327), à luz de §5:** recomendo a pista **MISTA (braço C)** como conteúdo do patch a assinar. Evidência: (i) os três braços são indistinguíveis em TODOS os oráculos de regressão (ownership e2e id-set exato, paridade, unit, baseline 24/1, rota 24/0) — o custo de C sobre B é +49 linhas de diff e zero regressão medida; (ii) só C registra o `CODEOWNERS` renderizado na continuidade do upgrade, e é exatamente a população da OQ-5 (adopter histórico) que depende disso — sem `HASH_PRIOR_RECORD` o D1 teria de RE-RENDERIZAR gerações anteriores com um handle que o install-state pode não ter, e um arquivo não reconhecido cai em PRESERVED para sempre (STALE silencioso, a classe deste plano); (iii) o sobre-reivindicar temido em B é limitado ao `CODEOWNERS` que o próprio framework renderizou — bytes editados pelo adopter deixam de casar o hash e caem em PRESERVED. **A assinatura do Owner sobre `wave-w5-approved.md` ratifica esta escolha (OQ-4 = pista MISTA; linhas do TSV de ownership: só as do `CODEOWNERS`, contadas em §3).** Sem assinatura, nada muda no main.

A medição não sustenta a hipótese que motivou o experimento, e sustenta uma
distinção diferente e mais útil. A pista MISTA não é uma versão barata da
não-condicional: é a não-condicional **mais** um ramo (+22 linhas de código nos
3 scripts canônicos). O que ela compra é exatamente um item, e é um item que a
pista não-condicional **não consegue** entregar por construção: o registro de
`.github/CODEOWNERS` no upgrade, com os bytes RENDERIZADOS (`d3b88d17…`, ≠
template `1955b01a…`). Os bytes renderizados não existem em checkout nenhum,
então nenhum leitor de rota pode hasheá-los; só uma declaração explícita de
`hash_source` pode. Nas outras 5 rotas os dois braços são idênticos e ambos
curam D3 de forma verificável — digest do template, não do homônimo, e o
`.template` que hoje some em silêncio passa a ser registrado. A decisão do
Owner, portanto, não é "qual pista é mais barata", e sim: **`.github/CODEOWNERS`
deve ser framework-owned no manifesto do adopter?** Se sim, a pista mista é o
único caminho e as +22 linhas são o preço; se não, o braço B já entrega a cura
de D3 com uma recusa NOMEADA em stderr em vez de um silêncio — e o braço B é o
estado mais conservador dos dois, porque sub-reivindica ownership, que é
recuperável, em vez de reivindicar demais, que é a classe que o `uninstall`
apaga.

---

## 7. Notas de execução / pontos abertos

- **⚠ COLISÃO DE DIRETÓRIO DE SAÍDA, detectada em execução.** O `$OUT` que o
  brief fixa (`scratchpad/oq4-out`) está sendo escrito por **mais de um
  agente**: `armA.map`, `armA.parity-maintainer`, `armA.parity-user`,
  `armA.red`, `armA.unit` apareceram entre 16:11 e 16:13 sem serem meus, e o
  `armA.baseline` que eu havia produzido (24 passed / 1 failed, rc=1) foi
  **sobrescrito às 16:14** por uma corrida em andamento de outro agente. Os
  números do braço A citados neste documento são os da MINHA corrida, lidos
  antes da sobrescrita; os do braço C foram copiados para
  `scratchpad/oq4-devops-mine/` assim que a colisão foi detectada. **Quem for
  preencher os `TODO(CEO)` precisa de um `$OUT` por agente**, ou os números de
  braços diferentes se misturam sem aviso — e um `armX.baseline` truncado no
  meio parece "0 falhas" para um `grep -c FAIL`.

- **⚠ OUTRO AGENTE ESTÁ ESCREVENDO NA MESMA SOMBRA — e no MESMO assunto.**
  Durante esta execução apareceram, sem serem meus:
  `.claude/adr/ADR-194-delivery-route-resolution.md` (untracked) e uma edição
  de **`CLAUDE.md`** (`194 ADRs` → `195 ADRs`, o bump derivado do ADR novo).
  Ou seja: um segundo engenheiro já redigiu o ADR **de D3**, o assunto deste
  documento. Não toquei em nenhum dos dois. **Os dois diffs estão limpos** —
  `diff --git` lista exatamente 4 arquivos em cada
  (`_framework_manifest_set.sh`, `install.sh`, `upgrade.sh`, o teste novo);
  qualquer `grep CLAUDE.md` neles casa apenas os meus COMENTÁRIOS citando
  "CLAUDE.md §4". Os dois trabalhos precisam ser reconciliados antes da
  cerimônia: o ADR alheio deve descrever a pista que o Owner ratificar, e o
  bump de `CLAUDE.md` colide com a regra de cache-discipline da §0
  (edição só em closeout).
- **A sombra fica no braço C**, conforme instruído (o D1 é construído em cima).
  `git status` da sombra: 3 modificados + 1 novo teste untracked (+ o ADR-194
  alheio). `scripts/delivery-routes.tsv` e `scripts/tests/ownership_table.tsv`
  **intocados**.
- Ambos os diffs contêm `new file mode` para o teste novo — é a perna que o
  `finalize_patch.py` (que usa `git diff` puro) **nunca exercitou** na S326 e
  que sumiria em silêncio do patch ASSINADO. Capturados com `git add -N` +
  `git reset -- <path>`; `git apply --check` de ambos passa contra um clone
  pristine de `56f050c`.
- **Dívida de cerimônia herdada, agora mais cara:** `scripts/delivery-routes.tsv`
  continua ausente das duas listas `paths:` do `smoke-install.yml`. Com o
  terceiro leitor sendo CANÔNICO, um typo confinado à tabela passa a poder
  quebrar o gerador de manifesto sem disparar o e2e que o consome. Fechar na
  mesma cerimônia.
- **RESIDUAL NOMEADO (forma, e é da classe desta wave):**
  `_register_delivered_template "<dst>" "<src>"` recebe o relpath de FONTE como
  **literal** em cada call-site, em vez de resolvê-lo pela tabela. Ou seja, o
  par destino→fonte é reafirmado num segundo lugar. Atenuantes medidos: o
  literal fica **uma linha** abaixo do `install_docs_template "<src>" "<dst>"`
  que faz a cópia, e o **S.2b** do teste novo cruza mecanicamente os dois
  conjuntos de argumentos — um typo no registro (que faria o `cmp -s` comparar
  o arquivo ERRADO e derrubar o registro em silêncio) sai VERMELHO nomeando o
  destino. Cura, se o Owner quiser fechá-la nesta cerimônia: assinatura de um
  argumento só (`_register_delivered_template "<dst>"`), resolvendo a fonte por
  `_wbm_route_src`, o que torna o `install.sh` um **quarto consumidor** da
  tabela e fail-CLOSED se ela sumir. Não foi feito aqui porque amplia o escopo
  do braço além de "enumeração + leitor + resolução", que é o que a OQ-4 mede.
- **Empacotamento verificado (não é risco):** `scripts/` está na lista `files`
  do `npm/package.json`, então `delivery-routes.tsv` viaja com o pacote; e o
  `doctor.sh` já depende da MESMA tabela desde a S325 (`:416`), então o
  precedente de distribuição está estabelecido.
- **Forma, para o rail olhar:** o discriminante de continuidade que copiei do
  precedente (`case "$_CONTINUITY_PATHS" in *".github/CODEOWNERS"*`) é um match
  de SUBSTRING, e `.github/CODEOWNERS` é PREFIXO de
  `.github/CODEOWNERS.template`. Hoje é inerte (`_CONTINUITY_PATHS` só carrega
  SPEC/PROTOCOL/marker), mas é o mesmo formato frouxo dos vizinhos. Na lista de
  entregues eu **não** usei substring: `_delivered_template_has` é
  linha-exata, justamente porque ali os dois nomes coexistem no domínio.
- O teste novo é **lane-agnóstico de propósito** em S.6: aceita a recusa da
  pista não-condicional ("delivered through a TRANSFORM") **ou** a da
  condicional ("declared no hash_source"), exigindo em ambos os casos que o
  path seja NOMEADO. Fixar uma das duas redações faria a suíte votar numa pista
  e transformar a outra num falso VERMELHO — a pista se decide na medição, não
  no teste.
- `scripts/tests/` **não** está em `pytest.ini testpaths`; o teste novo é bash e
  roda por invocação direta, como seus irmãos `test-doctor-delivery-route.sh` e
  `test_install_baseline_manifest.sh`. O wiring em CI é canônico e pertence à
  cerimônia.
