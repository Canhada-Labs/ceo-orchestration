# PLAN-183 / W5 — DRAFT (S323, 2026-08-23)

> ## Autorização do Owner — 2026-08-23 (S324)
>
> **W5-a: EXECUTADA E LANDADA** em `b6de7cf` (pushado, `origin/main` =
> `2578624`). O Owner autorizou em `AskUserQuestion` ("Commitar +
> corrigir + executar W5-a"); a superfície foi MEDIDA como não-canônica
> pelo oráculo suportado
> (`check_canonical_edit.py --is-canonical scripts/tests/_parity_classify.py`
> → `0`), então dispensou sentinel e cerimônia — L2, como previsto.
> As 4 checkboxes da W5-a e a **AC-8** estão fechadas com evidência
> inline. Prova de integração: e2e de paridade em árvore-sombra passou de
> `STALE 2 + UNCLASSIFIED 1` para `STALE 3 + UNCLASSIFIED 0` — três
> fatais de UMA causa (D1) em vez de duas.
>
> **W5-b: SEGUE FECHADA.** A OQ-5 foi respondida (rota (ii) — registro
> verbatim na §Open questions do plano), mas restam a **OQ-4**
> (dimensionamento do `ownership_table.tsv`) e o **debate L3 aditivo** em
> `PLAN-183/debate/w5-round-1/`, ambos itens `[P0]` desta wave. Nenhuma
> checkbox da W5-b abre antes disso.
>
> **Correção medida na S324, incorporada:** `scripts/doctor.sh` **não é
> canônico** — a tabela §8.8 do plano dizia que era, e o item de
> cerimônia desta wave, como estava escrito, abortaria o próprio land no
> gate G4. Ver o item de cerimônia e a §8.8 corrigida.
>
> **status: draft — W5-b NÃO EXECUTAR.** Este arquivo existe separado do
> `PLAN-183-adopter-fitness.md` de propósito: aquele plano está
> `reviewed` desde 2026-08-20, e por `PLAN-SCHEMA.md` §status isso
> significa "o humano leu e aceitou; a execução pode começar". A W5
> nasceu em 2026-08-23, o Owner autorizou apenas *planejar* (§6 do
> plano), e checkboxes novas sob `reviewed` seriam lidas como
> executáveis por qualquer dispatcher. Um aviso em prosa não muda esse
> estado machine-visible — o pair-rail marcou isso em duas rodadas
> seguidas, e esta é a cura arquitetural.
>
> **Análise e evidência:** `PLAN-183-adopter-fitness.md` §8 (D1, D2, D3,
> ordem de execução, a FORMA do problema na §8.5 e o precedente hash-gated da §8.6). Este arquivo é
> só a wave e seus critérios.
>
> **Promoção:** com o aceite do Owner, o conteúdo entra no PLAN-183 com
> a revisão refrescada, ou vira plano próprio.
>
> **Orçamento próprio** (não somado ao frontmatter do PLAN-183 enquanto
> este arquivo for draft): W5-a 30-60k / 1 sessão; W5-b 100-160k / 1
> sessão pela rota LOCAL do e2e, 2-4 pela rota nightly (§7.2 do plano).
> Total da W5: **130-220k**, **2-5 sessões**. `context_risk: high` — a
> W5-b é split-session por construção.
>
> **⚠️ Trade-off declarado desta separação (achado próprio, S323):**
> `validate_governance_fast.py` percorre `.claude/plans/` com
> `iterdir()` **não-recursivo** — o comentário do próprio código diz
> *"Root level only … so PLAN-NNN/"*. Logo este arquivo **não é coberto**
> pelo gate `plan_vcheck_declarations`: qualquer verde daquele validador
> sobre ele é VACUOSO. A disciplina de `Check:` aqui é de autoria, não
> mecânica, e o heading `## Waves` foi mantido para que o enforcement
> valha assim que o conteúdo for promovido ao plano (`PLAN-SCHEMA.md`
> §13.3 só enforça seções cujo título começa com `wave`/`items`/
> `progress log`/`sprint plan`).
>
> **Pair-rail:** 5 rodadas na S323 (26 achados: 15 P1, 11 P2), todos
> verificados contra o código antes de incorporar. As correções estão
> inline, cada uma nomeando a rodada que a produziu.

## Waves

### W5 — Paridade de ENTREGA no upgrade (D1+D3) e a fonte que o classificador lê (D2)

> Aberta na S323 a partir da §8. **Ordem obrigatória: D2 antes de D1**
> (§8.8) — não se valida a cura do produto com um instrumento que
> reporta a classe errada. As duas metades têm regime de governança
> DIFERENTE: D2 é L2 não-canônico, D1 é L3+ canônico com cerimônia.

#### W5-a — D2: o classificador (L2, sem cerimônia)

> **Insumos medidos na S324 (censo mecânico) — não re-descobrir.**
>
> - **NÃO existe teste algum** para `_parity_classify.py`. Censo
>   catch-all: os únicos consumidores são `CLAUDE.md`, o driver e2e, o
>   filtro `paths:` do `smoke-install.yml` e o próprio módulo. Zero
>   arquivos `.py` de teste.
> - **`scripts/tests/` é estruturalmente incapaz de hospedar um pytest**:
>   não está em `pytest.ini` testpaths (`:38-54`), não tem `conftest.py`
>   nem `__init__.py`. Um `test_*.py` ali **não é coletado por ninguém** —
>   seria falso-verde por construção (a classe já catalogada neste repo).
> - **Runner escolhido: pytest em `.claude/scripts/tests/`**, com
>   precedente EXATO de testar um `.py` da raiz `scripts/`:
>   `test_build_plugin_idempotency.py:35,48-51` resolve
>   `REPO/"scripts"/"build-plugin.py"` e carrega por
>   `importlib.util.spec_from_file_location`, herdando de
>   `TestEnvContext`. Essa raiz **está** em testpaths e roda por-PR em
>   `validate.yml:433-434`. Alternativa descartada: shell
>   `scripts/tests/test-*-unit.sh` exige editar os **dois** filtros
>   `paths:` do `smoke-install.yml` (o comentário `:60` avisa
>   *"unwired = no test"*) e não roda por-PR no Validate.
>   ⇒ É o par "unit oracle + e2e" que o PLAN-167 já institucionalizou.
> - **Controle positivo já reproduzido:** com o homônimo de raiz presente
>   o veredito é `UNCLASSIFIED` (rc=1); removendo **apenas** o homônimo, o
>   MESMO fixture sai `STALE`. Controle nos dois sentidos — a ordem
>   identity-first é a causa, provada, não inferida.
> - **Mapa de resolução atual, medido — a cura NÃO pode quebrar isto:**
>   `docs/*` → identity vence (ERRADO); `.github/*.template` →
>   `templates/` vence (CORRETO hoje); `.claude/*` → identity (correto).
> - **O e2e nunca passa `--github-owner`** (`:297-300`, uma invocação por
>   modo de cerimônia), o que explica por que `.github/CODEOWNERS` nunca
>   acendeu.

- [x] `[P0]` `_src_digest` deixa de resolver por identity-first quando o
      path é entregue a partir de `templates/`. A ordem correta é
      **derivada da rota de entrega**, nunca da existência do arquivo: se
      o `install.sh` escreve `X` a partir de `templates/X`, a fonte de
      comparação é `templates/X` — o homônimo na raiz é outro artefato,
      do próprio framework, que o adopter jamais recebeu. Não inverter
      cegamente a ordem: `templates/`-first quebraria qualquer path
      legitimamente entregue pela identity map. A cura enumera, não
      adivinha.
      **Escopo corrigido na S324: são TRÊS paths, não dois.** Medido pelo
      próprio `_src_digest`, `.github/CODEOWNERS` resolve para o
      `.github/CODEOWNERS` **vivo da raiz** (`ba6667d9e53bee9b`,
      10.259 b) em vez da fonte real
      `templates/.github/CODEOWNERS.template` (`1955b01a16069f6d`,
      1.442 b). A S323 afirmou em prosa que *"os 3 paths de `.github/`
      resolvem CORRETO"* — refutado. E a resolução dele exige a rota 3 da
      §8.5.1: nome de fonte diferente **mais** substituição, logo
      `_src_digest` tem de comparar contra os bytes RENDERIZADOS.
      Check: assere que _src_digest resolve docs/BRANCH-PROTECTION.md e docs/rotation-log.md para o digest de templates/, que .github/CODEOWNERS resolve para os bytes RENDERIZADOS de CODEOWNERS.template (nao para o arquivo da raiz e nao para o template cru), e que os 2 workflows .template seguem resolvendo para templates/ (nenhuma regressao)
      **FECHADO (S324, `b6de7cf`).** Mapa explicito destino->fonte em
      `_TEMPLATE_DELIVERED` / `_RENDERED_DELIVERED`; identity-first
      preservada como DEFAULT. Escopo saiu de 2 para 3 paths — o
      terceiro, `.github/CODEOWNERS`, e a rota RENDERIZADA e devolve
      None (fail-loud), nao o arquivo vivo da raiz.
- [x] `[P0]` Controle POSITIVO que reproduz o MECANISMO, não a aparência:
      um path novo entregue de `templates/` com homônimo plantado na raiz
      e digest divergente sai **STALE**, e o teste falha se sair
      UNCLASSIFIED. Controle NEGATIVO: sem o homônimo plantado, o mesmo
      path segue STALE.
      Check: o teste novo passa; com a cura revertida por git stash ele fica VERMELHO e a mensagem NOMEIA o path plantado
      **FECHADO (S324).** Controle CIRURGICO: mantendo os mapas
      definidos e removendo APENAS a consulta a eles, 3 testes ficam
      vermelhos com **zero `AttributeError`** e a mensagem nomeia
      `defect D2` — a falha e SEMANTICA, entao o teste detecta o
      defeito e nao a ausencia de uma constante.
- [x] `[P0]` `docs/rotation-log.md` — o falso-verde latente — ganha
      cobertura explícita, para não voltar a depender de "ninguém editou
      os dois lados".
      Check: grep por rotation-log no teste novo devolve pelo menos uma assercao
      **FECHADO (S324).** `docs/rotation-log.md` esta no mapa e nos
      testes; e medido que ele e IDENTICO entre o pin `v1.2.0` e HEAD,
      o que explica por que o falso-verde era latente.
- [x] `[P1]` Censo `templates/` contra raiz vira **teste**, não medição de
      sessão: qualquer homônimo NOVO acende, com veredito nomeado
      (entregue / não-entregue / absorvido pelo ACCEPTED).
      Check: o teste enumera os 4 homonimos atuais e falha se o conjunto mudar sem atualizacao declarada
      **FECHADO (S324).** `test_route_map_census_is_closed` enumera os
      homonimos `templates/` vs raiz e falha se aparecer um novo fora
      do mapa e fora da lista declarada (`README.md` nao-entregue,
      `CLAUDE.md` absorvido pelo ACCEPTED).

#### W5-b — D1: a entrega no upgrade (L3+ canônico, cerimônia obrigatória)

- [ ] `[P0]` **PRÉ-REQUISITO que nenhuma análise anterior nomeou (S324):
      `install_docs_template` não tem sinal de entrega NENHUM.** Medido:
      `install.sh:1446-1474` apenas ecoa (`COPIED:` / `EXISTS (skipping):`)
      e não devolve nem grava indicação de que escreveu. Todas as 5 rotas
      das duas árvores passam por ele (exceto o ramo `GITHUB_OWNER`, que
      tem `sed` próprio em `:1508`). **Sem esse sinal, qualquer
      `FMS_DELIVERED_*` seria ADIVINHADO** a partir de presença de arquivo
      — que é exactamente a confusão EXISTS-skip ↔ entrega que a OQ-5 diz
      que nenhum hash recupera, e que o `ADR-155-AMEND-1:87-125` proíbe.
      O molde existe: `install_one` (`install.sh:874-876`) já emite sinal
      **1 somente quando aquela chamada escreveu o destino**
      (`COPIED`/`LINKED`); `EXISTS`-skip, fonte ausente e `--dry-run`
      deixam **0**. Esta unidade vem ANTES de qualquer entrada de
      manifesto.
      Check: install_docs_template devolve/grava sinal por DESTINO com a mesma semantica de install_one; teste com os quatro casos (escreveu / EXISTS-skip / fonte ausente / dry-run) assertando 1,0,0,0; e nenhuma entrada FMS_DELIVERED_* e declarada antes deste item estar verde

- [ ] `[P0]` **A tabela de ROTAS vira dado COMPARTILHADO (dívida criada
      pela W5-a, §8.5.2).** A W5-a define `_TEMPLATE_DELIVERED` /
      `_RENDERED_DELIVERED` **dentro** de `_parity_classify.py` porque é
      L2 e só toca teste. Os outros dois consumidores são **bash**
      (`_framework_manifest_set.sh`, `doctor.sh`), então uma segunda cópia
      lá seria o "ramo local" que o `CLAUDE.md` §4 proíbe. A W5-b promove
      a tabela a arquivo de dados lido pelos dois lados — a forma de
      `ownership_table.tsv`. E o manifesto persiste só
      **digest + relpath de destino**, logo o `doctor.sh` não tem de onde
      RECUPERAR a fonte sem essa tabela.
      Check: existe UM arquivo de dados de rotas, e grep prova que _parity_classify.py, _framework_manifest_set.sh e doctor.sh todos o LEEM; nenhum dos tres carrega mapa proprio; teste de censo falha se um quarto consumidor aparecer sem ler a tabela

- [ ] `[P0]` **Debate L3 antes de qualquer linha.** `upgrade.sh` e
      `_framework_manifest_set.sh` são canônicos e são o coração do
      PLAN-167/168; a memória deste repo registra que essa classe de
      script consumiu 34 de 44 rounds do trem v1.3.0.
      **Não usar `/debate start`**: `PLAN-183/debate/round-1/` já existe
      com proposal, 3 críticas, `anonymization-map.md` e `consensus.md`
      (6 arquivos, medido), e `/debate start` reescreve os artefatos de
      round-1 (`.claude/commands/debate.md:43-60`) — apagaria evidência
      permanente, contra `PLAN-SCHEMA.md:117-120`. A rodada desta wave é
      ADITIVA, em diretório próprio.
      Check: existe .claude/plans/PLAN-183/debate/w5-round-1/consensus.md com veredito nomeado, e os 6 arquivos de debate/round-1/ saem do commit com sha256 inalterado
- [ ] `[P0]` **Granularidade POR PATH DE DESTINO, nunca por árvore
      (achado P1 do pair-rail S323, verificado).** O rascunho da S323
      propunha `FMS_DELIVERED_GITHUB` / `FMS_DELIVERED_DOCS` — uma flag
      por árvore — e isso é **insuficiente por construção**:
      `_state_record_op "install_docs_templates"` é a PRIMEIRA linha da
      função (`install.sh:1479`), roda ANTES das duas cópias
      skip-if-exists (`:1480-1481`) e grava a string fixa
      `"BRANCH-PROTECTION.md + rotation-log.md"`. Ele registra a
      TENTATIVA, não a entrega. Num target que já tinha
      `docs/BRANCH-PROTECTION.md` mas não `rotation-log.md`, uma flag
      única ou reivindica posse do arquivo adopter-owned ou omite o
      recém-entregue — as duas direções erradas. `.github/` tem o mesmo
      problema em três arquivos independentemente puláveis
      (`:1493-1522`). **A decisão passa a ser por PATH e por RESULTADO da
      operação** — INSTALLED / REFRESHED / IDENTICAL entram na
      enumeração; PRESERVED e SKIPPED ficam fora — exatamente como
      `upgrade.sh:3113-3115` já faz para os schema docs (§8.6).
      `_state_record_op` continua sendo breadcrumb, não fonte de verdade
      de ownership.
      **A fixture de `docs/` sozinha é INSUFICIENTE (P1 do pair-rail
      S324).** Pré-popular só um destino de `docs/` deixa passar uma
      implementação que mantenha flag por ÁRVORE do lado do `.github/`:
      ela passa nos testes de install limpo e depois registra falsamente
      um `CODEOWNERS` adopter-owned quando só os workflows foram
      copiados. As três de `.github/` são independentemente puláveis
      (`:1493-1522`), então a fixture parcial tem de existir nas DUAS
      árvores.
      Check: DUAS fixtures parciais — (a) target que ja tem docs/BRANCH-PROTECTION.md e nao tem rotation-log.md; (b) target que ja tem .github/CODEOWNERS mas nao os dois workflows — em cada uma o manifesto lista EXATAMENTE os paths recem-entregues e NAO lista os pre-existentes, e todo arquivo pre-existente sai byte-identico do upgrade
- [ ] `[P0]` Os registros derivam do **RESULTADO da operação**, nunca da
      cerimônia e nunca da presença do arquivo. Um alvo que já tinha o
      path (skip-if-exists) permanece adopter-owned e o upgrade NÃO o
      toma — é a classe S238 ("verified worst case") que o
      ADR-155-AMEND-1 existe para impedir.
      **Correção S324 (P1 do pair-rail, confirmada pelo PRÓPRIO
      precedente citado nesta wave).** O rascunho da S323 dizia
      *"derivam da CÓPIA REALIZADA"* — e isso **contradiz**
      `upgrade.sh:3110-3113`, que esta wave adota como molde: *"the
      schemas enter the enumeration ONLY when this upgrade left FRAMEWORK
      bytes at the path (INSTALLED / REFRESHED / **IDENTICAL**).
      PRESERVED and SKIPPED stay out."* `IDENTICAL` está DENTRO da
      enumeração e `IDENTICAL` significa exatamente que **nenhuma cópia
      ocorreu**. Um critério cópia-aconteceu é insatisfazível junto com a
      rota (ii) da OQ-5 (que registra histórico byte-pristine sem
      copiar) e junto com a paridade exit 0.
      O critério correto é sobre o ESTADO resultante: *"este upgrade
      deixou bytes de FRAMEWORK neste path"*. Enumeração fechada,
      derivada do enum do precedente: **INSTALLED / REFRESHED /
      IDENTICAL entram; PRESERVED / SKIPPED ficam fora.**
      Check: a derivacao dos registros novos e uma funcao do enum de resultado por path, e o teste enumera os CINCO estados assertando que os 3 primeiros registram e os 2 ultimos nao; grep por CEREMONY na derivacao devolve zero; e2e de segundo upgrade consecutivo nao altera nenhum byte do arquivo adopter-owned
- [ ] `[P0]` **Adopters HISTÓRICOS: refresh HASH-GATED contra as gerações
      conhecidas (achado P1 do pair-rail r2, resolvido pelo precedente da
      §8.6).** Para a rota B do e2e (pin default `v1.2.0`) e para o
      adopter real, o install-state tem apenas registro grosso de
      tentativa e o baseline não contém nenhuma das duas árvores —
      registro por path só produz evidência confiável para instalações
      FUTURAS. Sem mecanismo, o upgrade não distingue "cópia do
      installer antigo" de "arquivo pré-existente pulado". A resposta
      **veio na S324: OQ-5 RESPONDIDA pelo Owner — rota (ii), migrar
      com hash-gate** (registro verbatim na §Open questions do plano).
      O hash-gate é o mecanismo certo para "pristine vs modificado", mas
      **não** separa *entregue pelo installer* de *já estava lá e por
      acaso bate com um template antigo* — nesse caso o EXISTS-skip
      deixou um arquivo adopter-owned e o gate **toma posse dele**,
      contra a regra de under-claim do `ADR-155-AMEND-1:87-125` (achado
      P1 do pair-rail r4). Nenhuma inspeção de conteúdo recupera a
      intenção de um adopter histórico: a colisão é **risco declarado e
      aceito**, não problema resolvido.
      **O argumento que sustenta o aceite foi CORRIGIDO na S324 (P1 do
      pair-rail): a fronteira é o CONTEÚDO, não o sufixo.** A versão
      apresentada ao Owner dizia *"para `.github/**/*.template` a colisão
      é praticamente impossível — são artefatos só-framework"*, traçando
      a linha pelo sufixo `.template`. Isso é impreciso: em modo
      `--github-owner` o destino é `.github/CODEOWNERS` — **sem sufixo**,
      um nome de arquivo perfeitamente comum em qualquer repo GitHub
      (`install.sh:1496-1509`, verificado). Pelo critério do sufixo ele
      cairia na classe "exposta".
      Medido, porém, a colisão segue implausível **por conteúdo**: o
      template renderizado tem **33 linhas / 1.442 bytes** e todo padrão
      nomeia paths do framework (`.claude/skills/**`, `.claude/hooks/**`,
      `.claude/plans/PLAN-*.md`, `.claude/adr/**`, `PROTOCOL.md`,
      `.claude/scripts/validate-governance.sh`). Colidir exige ter
      escrito à mão, byte a byte, um CODEOWNERS que referencia a árvore
      `.claude/` — que só existe porque o framework está instalado.
      ⇒ Enunciado correto para o ADR: **bytes idênticos são prova de
      origem quando o CONTEÚDO é framework-specific** — o que cobre as
      três de `.github/` (as duas `*.template` e o CODEOWNERS
      renderizado). O risco residual real fica em `docs/*`, onde um
      adopter pode plausivelmente ter documento próprio, e o
      `uninstall.sh` remove por hash — é essa a blast radius a declarar.
      E o conjunto de gerações vem do HISTÓRICO GIT de cada arquivo com
      contrato de append no mesmo commit — **não de tags** (o install por
      clone aceita qualquer commit de `main`), como
      `upgrade.sh:3204-3212` + `test-schema-generation-pins-unit.sh`.
      Check: OQ-5 respondida e registrada verbatim ANTES desta unidade; depois, e2e cobrindo os TRES casos — pristine de geracao conhecida, modificado, e a COLISAO (pre-existente byte-identico a template antigo) — cada um terminando no estado que a rota escolhida determina; teste de geracoes derivado do git, nao de lista memorizada
- [ ] `[P0]` **D3 — mapeamento template-aware no gerador (achado P1 do
      pair-rail S323, §8.3).** Enumerar as duas árvores sem isso
      invalida o baseline: `FMS_HASH_ROOT="$SOURCE_DIR"`
      (`upgrade.sh:3474-3476`) faz o gerador resolver
      `"$_wbm_hash_root/$_wbm_rel"` (`_framework_manifest_set.sh:430-436`)
      **sem fallback para `templates/`** — `docs/*` casa o documento
      ERRADO da raiz e `.github/*.template` cai no `continue`, sumindo do
      baseline em silêncio. A cura declara, por path, QUAL fonte é a
      verdadeira.
      **A asserção é o CONJUNTO COMPLETO, não uma amostra** (P1 do
      pair-rail r4): um mapper que ainda omitisse `benchmarks.yml.template`,
      `rotation-log.md` ou o `CODEOWNERS` default passaria num check que
      só nomeia o `validate` e um digest de docs — e o segundo upgrade
      continuaria byte-idêntico por ser identicamente incompleto.
      **E a asserção tem de correr TAMBÉM logo após um install limpo**
      (P1 do pair-rail r5): o check pós-upgrade sozinho é passável por
      uma implementação que adicione registros só do lado do upgrade e
      nunca acione as flags por path do lado do install — e o
      classificador de paridade não pega isso, porque bytes do manifesto
      estão no `ACCEPTED`. Instalação fresca ficaria sem registro, e
      `doctor.sh` e `uninstall.sh` sem entrega registrada.
      Check: o conjunto EXATO de registros para .github/ e docs/ e asserido em DOIS momentos — logo apos install limpo do HEAD e apos o upgrade — em DUAS fixtures (sem owner e com --github-owner), cada digest batendo com a fonte que o adopter recebeu (templates/... ou o renderizado), nenhum path ausente
- [ ] `[P0]` **D4 — o mesmo mapeamento no `doctor.sh` (achado P1 do
      pair-rail r5, §8.4).** Assim que os registros existirem, o doctor
      passa a consumi-los e resolve a fonte sozinho, sem fallback:
      `_hash_file "$SOURCE_DIR/$rel"` em `:507` (ausente) e `:553`
      (drift), e o REPARO em `:401` faz
      `cp -p "$SOURCE_DIR/$_rf_rel"`. Para `docs/*` isso escolhe o
      homônimo errado da raiz; para `.github/*` não há fonte e o registro
      válido vira *"not repairable"*. O `:401` não só classifica —
      **copia**: um doctor que repara com o arquivo errado é pior que um
      que não repara. O resolvedor único da §8.5 tem de cobrir o doctor,
      não só o writer de manifesto.
      **Falta a rota RENDERIZADA (P1 do pair-rail S324).** As duas
      fixtures do rascunho cobrem só cópia crua. O caso
      `.github/CODEOWNERS` é a rota 3 da §8.5.1: fonte com OUTRO nome
      (`CODEOWNERS.template`) mais substituição de `{{OWNER_HANDLE}}`. Um
      resolvedor pode passar nas duas fixtures cruas e ainda assim ou
      reportar o renderizado como *not repairable*, ou — pior —
      **reparar escrevendo o template cru, devolvendo
      `{{OWNER_HANDLE}}` literal** para o arquivo do adopter. É o `:401`
      copiando errado, na forma mais visível.
      Check: TRES fixtures — (a) docs/BRANCH-PROTECTION.md deletado: doctor repara com os bytes de templates/, nao com o doc da raiz; (b) .github/workflows/validate.yml.template deletado: doctor repara em vez de reportar not-repairable; (c) .github/CODEOWNERS deletado E com drift, em target instalado com --github-owner: doctor repara com os bytes RENDERIZADOS, o re-hash bate com o baseline e grep por {{OWNER_HANDLE}} no arquivo reparado devolve ZERO; as tres ficam VERMELHAS com o mapeamento revertido
- [ ] `[P0]` **Segundo upgrade consecutivo é o teste que pega D3.** A
      primeira rodada de paridade pode passar com o baseline errado; o
      dano aparece na classificação do upgrade SEGUINTE.
      **A asserção tem de ser ESCOPADA** (P2 do pair-rail r3): todo
      upgrade não-dry cria árvore de backup timestamped e reescreve
      `.claude/.install-state.json` incrementando `run_count`
      (`upgrade.sh:3605-3612`), então "nenhum diff no target" é
      insatisfazível mesmo com D3 curado.
      Check: e2e roda upgrade DUAS vezes; diff da segunda restrito a .github/ e docs/ e vazio, e o .install-manifest.sha256 normalizado e byte-identico entre as duas rodadas
- [ ] `[P1]` **Variante `--github-owner` coberta (achado P2 do pair-rail
      S323, verificado).** Com essa flag o install escreve um
      `.github/CODEOWNERS` SUBSTITUÍDO (`install.sh:1508`) e grava
      `github_owner` no install-state (`:2654`); medido, `grep` por
      `github_owner|GITHUB_OWNER|CODEOWNERS` em `scripts/upgrade.sh`
      devolve **ZERO** — o upgrade não repete a substituição. Sem um
      caso de paridade com owner, todos os Checks da W5 podem passar
      enquanto o CODEOWNERS personalizado fica velho ou é regenerado da
      fonte errada.
      **O Check ingênuo seria VACUOSO** e o pair-rail r2 mediu por quê:
      com o pin default `v1.2.0`
      (`test-install-upgrade-parity-e2e.sh:110`), o
      `templates/.github/CODEOWNERS.template` é **byte-idêntico** ao de
      HEAD (`1955b01a16069f6d6a5a` dos dois lados, medido) — logo um
      upgrade que nunca lê `github_owner` e deixa o arquivo do pin
      intocado passaria nas duas asserções. O teste tem de OBSERVAR uma
      mudança de fonte.
      **E o baseline tem de registrar os bytes RENDERIZADOS** (P1 do
      pair-rail r4): com `--github-owner` o install escreve
      `.github/CODEOWNERS` já com `{{OWNER_HANDLE}}` substituído
      (`install.sh:1496-1509`) — o adopter nunca recebeu os bytes crus do
      template, então registrar o digest do template cru faria o arquivo
      entregue divergir do próprio baseline no ato, produzindo drift
      falso. **A alternativa "asserir bytes de HEAD" foi REMOVIDA** (P2
      do r4): ela é vacuosa pela medição acima — só divergência plantada
      torna o teste sensível à reversão da rota.
      Check: o e2e ganha caso com --github-owner e PLANTA divergencia no template; com a rota owner-aware revertida por git stash o teste fica VERMELHO; o manifesto registra o digest RENDERIZADO e ele se mantem estavel por DOIS upgrades; {{OWNER_HANDLE}} nao reaparece
- [ ] `[P0]` Paridade install==upgrade restaurada nos 3 paths que hoje
      são fatais, no modo `maintainer`, **sem** tocar `ACCEPTED` nem
      `KNOWN_OPEN`.
      A expectativa era CONDICIONAL à rota da OQ-5 (P2 do pair-rail r5).
      **Com a OQ-5 respondida na S324 como rota (ii), a condicionalidade
      CAIU: a expectativa é exit 0, sem alternativa.** Nas rotas (i) e
      (iii) a rota B do e2e permaneceria, por desenho, uma instalação
      histórica v1.2 e os três paths não convergiriam — não é mais o
      caso. Fica registrado que, se a rota for revista, este Check volta
      a ser condicional.
      Check: test-install-upgrade-parity-e2e.sh --mode maintainer sai 0; o diff de _parity_classify.py nao inclui ACCEPTED nem KNOWN_OPEN
- [ ] `[P0]` Modo `user` permanece inalterado: nenhuma das duas árvores
      passa a ser escrita onde o install não escreveria.
      Check: bash scripts/tests/test-install-upgrade-parity-e2e.sh --mode user sai 0 e o target em modo user nao contem .github/workflows/*.template
- [ ] `[P0]` Bateria de ownership não regride — a cura toca o gerador que
      os PLAN-167/168 fecharam. Vale a regra do `CLAUDE.md` §4: o e2e
      termina **62 verde / 3 vermelho por desenho**; toda-verde é sinal
      de PARAR.
      **O total NÃO pode ser fixado aqui** (P2 do pair-rail r2): se a
      OQ-4 for resolvida acrescentando linhas ao `ownership_table.tsv`,
      o conjunto de linhas cresce e `GREEN=62 RED=3` deixa de valer —
      um Check literal ou bloquearia a extensão correta da tabela ou
      empurraria para omitir as superfícies novas. O total é DERIVADO
      depois da OQ-4, e o que permanece invariante é a REGRA: nenhum id
      muda de lado sem atualização declarada no mesmo commit, e
      toda-verde continua sendo sinal de PARAR (`CLAUDE.md` §4).
      Check: OQ-4 respondida ANTES desta unidade; bash scripts/tests/test-ownership-verdict-unit.sh sai 0; ownership-nightly-gate.sh sai 0 contra um ownership-expected-reds.txt re-derivado e versionado no MESMO commit; nenhum id pre-existente muda de lado sem justificativa escrita
- [ ] `[P1]` `ownership-baseline-map.txt` **re-gravado** pelo harness em
      `--stable-header`, nunca editado à mão; `ownership-expected-reds.txt`
      re-verificado no MESMO commit se qualquer id mudar de lado.
      Check: o diff do mapa e saida de harness (cabecalho estavel) e o gate nightly sai 0
- [ ] `[P0]` **ADR formal para a mudança de contrato de ownership
      (achado P1 do pair-rail r4).** A W5-b altera o contrato através de
      três módulos canônicos produtor/consumidor e introduz um
      trade-off de migração legada — é decisão cross-cutting L3+, e o
      `CLAUDE.md` §4 exige registro formal. Amendment ao ADR-155 (ou ADR
      novo), com a resposta da OQ-5 embutida como decisão.
      **Criar o ADR quebra a contagem derivada** (P1 do pair-rail r5):
      `CLAUDE.md:54` afirma **194 ADRs** e o disco tem exatamente 194
      (medido) — o `check-claude-md-claims.py` roda no Validate com
      tolerância zero. A atualização da contagem entra NESTE commit, e
      `CLAUDE.md` é editável só em closeout por cache-discipline (§0),
      o que faz disto um item de sequenciamento, não um detalhe.
      Check: existe .claude/adr/ADR-155-AMEND-N (ou ADR-NNN novo) em ACCEPTED nomeando as duas arvores, a regra de under-claim aplicada a elas e a rota escolhida na OQ-5; o path do ADR esta no Scope do sentinel; python3 .claude/scripts/check-claude-md-claims.py sai 0 no MESMO commit
- [ ] `[P0]` Cerimônia GPG: sentinel com Scope cobrindo **os TRÊS**
      canônicos — `scripts/install.sh`, `scripts/upgrade.sh` e
      `scripts/_framework_manifest_set.sh` — anchor-sha real, e
      `touched - scope = vazio` verificado ANTES do commit.
      **`install.sh` estava faltando** (P1 do pair-rail r3): só as
      funções de cópia dele (`:1446-1522`) sabem, por destino, se houve
      INSTALLED ou skip; o helper de manifesto não pode inferir isso de
      presença nem de bytes coincidentes. Sem ele no Scope, ou o land
      aborta no `touched - scope`, ou a instalação limpa sai sem
      registro de ownership. É canônico em `check_canonical_edit.py:189`.
      **O ADR também entra no Scope** — `.claude/adr/ADR-*.md` é guardado
      (`check_canonical_edit.py:178`).
      **O Scope enumera TODO path tocado, não só os canônicos (achado
      medido na S324 — este Check, como estava escrito, abortaria o
      próprio land).** O gate G4 (`PLAN-182/OWNER-S321-LAND.sh:174`) faz
      `comm -23 touched scope` sobre a saída de `git apply --numstat`,
      **sem filtro de canonicidade**. Medido pelo oráculo
      `check_canonical_edit.py --is-canonical`: `scripts/doctor.sh`
      devolve **0** — NÃO é canônico (controle positivo passando:
      `install.sh`/`upgrade.sh`/`_framework_manifest_set.sh` = 1). Logo o
      item D4 toca um path que o Scope de 3-scripts-mais-ADR não cobre, e
      o land morre em `die "o patch toca path(s) FORA do Scope
      assinado"`. A §8.8 do plano foi corrigida no mesmo commit.

      **⚠️ NÃO COPIAR A FORMA DO PLAN-177 — ela é INERTE (medido na
      S324).** O censo importou `check_canonical_edit.py` e chamou as
      funções: para `.claude/plans/PLAN-177/approved-amendment-1.md`,
      `_parse_scope_paths_from_text` devolve **0 paths** e
      `_sentinel_grants_path(…, "scripts/_framework_manifest_set.sh")` =
      **False** — apesar de o `.asc` existir e verificar. Causas: não tem
      linha `Approved-By:`, o heading é `## Scope — …` (que
      `_SCOPE_HEADER_RE` não casa) e os paths estão em *fence*, não em
      bullets. A distinção `Canônico:` / `Livre, MESMO commit` daquele
      arquivo é **prosa** — nunca entrou na decisão do hook.

      **A forma VIVA (PLAN-182/PLAN-184), provada ponta-a-ponta.** Path
      casando `.claude/plans/PLAN-<NNN>/wave-<slug>-approved.md` — união
      FECHADA de 10 globs (`check_canonical_edit.py:1004-1014`), sem
      catch-all: arquivo fora do padrão é ÓRFÃO e nunca é considerado.
      Preâmbulo: `Plans:` → `Wave:` → `Patch:` → `Patch-sha256:` →
      `Anchor-SHA:` → `Data:`. Depois, o bloco:

      ```
      <!-- BEGIN SIGNED SCOPE -->
      Approved-By: <fpr>
      Plans: PLAN-183
      Scope:
        - <path>
      <!-- END SIGNED SCOPE -->
      ```

      nessa ORDEM (`Approved-By:` → `Plans:` → `Scope:`), bullets com dois
      espaços de indentação. O hook lê **só** `Approved-By:`, o par de
      marcadores e os bullets; `Anchor-SHA` / `Patch-sha256` / `Wave` têm
      zero consumidores em código — são contrato humano, lidos pelo LAND.

      **E os paths LIVRES entram no MESMO bullet list**, não numa seção
      separada: o bloco é a UNIÃO de tudo que o patch toca, porque o G4
      exige `touched ⊆ scope` (no PLAN-182 o Scope tem 12 entradas,
      incluindo `conftest.py` e dois testes — todos livres). A distinção
      canônico/livre mora no glob `case` do **G0 do LAND**, que decide se
      um arquivo sujo FORA do Scope aborta (canônico) ou só avisa (livre).
      Check: o sentinel esta em .claude/plans/PLAN-183/wave-w5b-approved.md com Approved-By: + os DOIS marcadores literais + bullets, e o bloco lista a UNIAO de todos os paths tocados (os 3 canonicos + o ADR + scripts/doctor.sh + os testes); prova MECANICA, nao visual: _sentinel_grants_path devolve True para cada um dos 3 canonicos e para o ADR; o LAND roda G0..G5 e o G4 sai vazio

## Acceptance criteria (W5)

- [x] AC-8 [P0] O classificador de paridade compara contra a fonte que o
      adopter REALMENTE recebeu. Prova: `docs/BRANCH-PROTECTION.md` sai
      **STALE** (não UNCLASSIFIED) enquanto D1 estiver aberto, e o
      controle positivo do homônimo plantado fica vermelho com a cura
      revertida.
      **FECHADO (S324, `b6de7cf`) — provado end-to-end, nao por unidade.**
      E2e de paridade `--mode maintainer` numa arvore-sombra
      (`git clone --local` + a cura): passou de `STALE 2 +
      UNCLASSIFIED 1` para **`STALE 3 + UNCLASSIFIED 0`** — tres
      fatais de UMA causa (D1) em vez de duas. Mais 9 testes verdes,
      controle negativo cirurgico vermelho, rodada LIMPA de pair-rail
      sobre o codigo, e bateria `.claude/scripts/tests/` com
      5315 passed / 23 skipped / 1 xfailed.
- [ ] AC-9 [P0] `upgrade.sh` entrega `.github/` e `docs/` sob o contrato
      DELIVERY-RECORD-CONDITIONAL do ADR-155-AMEND-1, **com registro por
      PATH DE DESTINO** (não por árvore) derivado do **RESULTADO da
      operação** — `INSTALLED`/`REFRESHED`/`IDENTICAL` registram,
      `PRESERVED`/`SKIPPED` não; jamais da cerimônia ou da presença — e a
      paridade `maintainer` volta a 0 sem alargar `ACCEPTED` nem
      `KNOWN_OPEN`. (S324: a redação anterior dizia "derivado da cópia
      realizada" e era insatisfazível — `IDENTICAL` não copia. Ver o item
      correspondente na W5-b.)
- [ ] AC-10 [P0] O baseline pós-upgrade é VÁLIDO para as duas árvores
      novas: cada path registra o digest da fonte que o adopter
      realmente recebeu (`templates/…`), nenhum path some por
      `continue`, e um SEGUNDO upgrade consecutivo não reclassifica
      nada. Fecha D3 (§8.3) e D4 (§8.4).
