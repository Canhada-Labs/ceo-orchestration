---
plan: PLAN-177
round: 1
agent: DevOps Engineer (Principal)
archetype: devops
created_at: 2026-08-13
---

# DevOps Engineer — round 1, PLAN-177 (rc.4)

Escopo do meu archetype: **wiring** — o teste novo é EXECUTADO pelos
workflows que decidem? o gate curado pode ser desligado por variável? a
sequência do corte tem furo operacional? Todo claim abaixo foi verificado
por mim no arquivo vivo (file:line).

## Verdict

**ADJUST** — sem VETO.

O plano está estruturalmente certo: as 4 rotas de cura atacam a causa, o
teste de regressão nasce na raiz certa, e as exclusões (rota (i), node24,
perf, `.github/scripts/tests/`) estão bem fundamentadas. Mas **duas
afirmações mecânicas do plano são falsas na leitura do disco** (M1, M2) e
uma delas (M1) faz o plano confiar em um enforcement que não existe —
literalmente a classe que o plano existe para curar. Mais três ajustes de
wiring (M3–M6). Nenhum é redesenho; todos cabem no W0/W1 como escritos.

## Summary

O que verifiquei e **confirma** o plano:

- O teste de regressão do P1-4 nasce em raiz VIVA. `validate.yml:419-421`
  roda `python3 -m pytest .claude/scripts/tests/ ... -n auto -m 'not
  serial'` + a passada `serial`; `release.yml:364` roda
  `python3 -m pytest .claude/scripts/tests -q --tb=short`. Logo
  `.claude/scripts/tests/test_release_bump_sites.py` executa nos dois.
  A escolha de NÃO usar `.github/scripts/tests/` está certa.
- O ponto de inserção do `_release_tag_guard.py` é o correto: o bloco
  proposto (:295/:296) cai dentro de `delta()` (:274-…, bind de
  `release_tag` em :288-295), e `delta` é o modo invocado **tanto** pelo
  corte local (`release.sh:630-631`, com `|| die`) **quanto** pelo passo
  servidor "Verify verdict delta + ancestry (fail-closed)"
  (`release.yml:857-859`), que **não tem** `continue-on-error`. Essa é a
  metade que realmente barra.
- A cadeia até o npm fecha: `npm-publish.yml:220` `needs:
  await-release-gate`, e `await-release-gate` faz poll do **JOB**
  `release-gate` (`npm-publish.yml:130`), não da conclusão do run.
  `release.yml:876` `publish-release: needs: release-gate`. Um
  `release-gate` red ou skipped bloqueia release e publish.
- O parity e2e roda no push para main também, não só em PR:
  `smoke-install.yml:65-67` `push: branches: [main]` com a lista de paths
  mantida idêntica à do `pull_request`; `scripts/install.sh`,
  `scripts/upgrade.sh`, `scripts/_framework_manifest_set.sh` e
  `scripts/tests/_parity_classify.py` estão nas DUAS listas. O pack W1
  dispara o gate mesmo landando direto em main.
- T-1 (tournament) está **correto**. `git apply --check` OK por mim. O
  produtor tem `working-directory: .claude/scripts`
  (`tournament.yml:145`) e escreve `projection.txt` lá — confirmado por
  `path: .claude/scripts/projection.txt` no upload (`:196`). O passo
  "Emit step summary" (`:175-190`) não tem `working-directory` e faz
  `open('projection.txt')` engolido por `2>/dev/null || echo "N/A"`
  (`:181`). O corpo desse passo **não usa nenhum outro path relativo**
  (só `$GITHUB_STEP_SUMMARY`, absoluto) ⇒ adicionar `working-directory` é
  seguro.
- OQ-3 é executável (ver M3): dos 6 controles da tabela
  (`npm/INTEGRITY.md:23-28`), 2 usam a forma parseável `` `…yml` step
  "<nome>" `` (:27, :28) e **ambos os nomes existem verbatim** —
  `npm-publish.yml:278` "Verify zero runtime dependencies" e `:255`
  "Verify VERSION matches tag".

## Risks

- **R-A — commit atômico do W1 é o ponto único de falha.** O estado
  "cura landada + allowlist não removida" é **CI-VERDE e cego** (ver M1).
  A lição do repo sobre `git add` de linha longa quebrando no paste
  (S297) transforma isso num risco operacional real, não teórico. Landar
  por manifesto, linhas curtas, e conferir `git show --stat` antes de
  push.
- **R-B — margem de timeout do smoke-install.** `timeout-minutes: 25`
  (`smoke-install.yml:100`) foi dimensionado (comentário :88-99) para a
  contagem atual de operações install/upgrade. A entrega nova do
  `.gitignore` acrescenta trabalho por modo. É pequeno, mas a lição do
  repo é medir a margem **antes** do corte: um timeout de job aparece
  como `cancelled` num passo inocente e vira debug caro no meio do W2.
- **R-C — R-2 (re-pin do W3) é uma mina pós-GA, não uma nota.** O LAND do
  kit W3 aplica com `cp` cego; rodar com os sha256 pinados de HOJE
  **regride a cura do P1-4**. Isso precisa virar linha de checklist no
  runbook do W3 agora, assinada junto, não memória de sessão.
- **R-D — concorrência do smoke-install cancela runs.**
  `smoke-install.yml:105-107` `concurrency: cancel-in-progress: true`
  agrupado por ref. Dois pushes seguidos em main cancelam o primeiro run;
  `cancelled` não é aprovação. (`release.yml:10` já é
  `cancel-in-progress: false` — correto para tags.)

## Must-fix

### M1 [P0] — a mecânica da allowlist do parity está descrita ERRADA, e o erro é na direção perigosa

O plano afirma (W0 item 4 e W1): *"allowlist `_parity_classify.py:123-132`
REMOVIDA no MESMO commit (entry órfã = MANDATORY-FIRE)"*.

Verificado no disco: a tupla `r"^\.gitignore$"` está em
**`scripts/tests/_parity_classify.py:124`**, dentro da lista
**`ACCEPTED`** (abre em `:90`) — **não** em `KNOWN_OPEN` (abre em `:159`,
hoje **vazia**). E o docstring do módulo é explícito sobre a diferença
(`:56-61`):

- `KNOWN_OPEN` = MANDATORY-FIRE, entry órfã é **FATAL**;
- `ACCEPTED` que passa a bater idêntico emite **WARNING** ("stale
  declaration, harmless").

Consequência concreta, enumerando os 4 estados:

| estado | allowlist | cura | resultado do gate |
|---|---|---|---|
| A (hoje) | presente | ausente | ACCEPTED ⇒ exit 0, **verde** |
| B (alvo) | removida | presente | idêntico ⇒ **verde** |
| C (trap) | **presente** | presente | **WARNING ⇒ verde, e cego** |
| D | removida | ausente | não casa declaração ⇒ **FATAL** |

O estado **C** é exatamente a instância 17 da classe: a cura entra, o
gate volta a allowlistar o defeito para sempre, e **o CI não avisa**. O
plano hoje se apoia num MANDATORY-FIRE que não cobre essa entry.

**Fix (escolha uma, ambas cabem no W1):**
(a) mover a entry para `KNOWN_OPEN` com `unblocked_by` **e** removê-la no
commit da cura — aí a mecânica passa a ser a que o plano descreve; ou
(b) manter em `ACCEPTED`, removê-la no commit da cura, **e** registrar
explicitamente no plano que o CI **não** protege contra o estado C ⇒ a
verificação é humana, com `git show` do commit provando as duas metades.

Não aceito a redação atual: ela promete um gate que não existe, dentro de
um plano cuja tese é "promessa sem gate".

### M2 [P0] — o controle positivo existente NÃO cobre a superfície nova (e o guard de exit codes já apodreceu)

Duas metades, ambas verificadas.

**(i) O plant do parity não consegue plantar a entrega nova.** O plano
diz (W0 item 4): *"NENHUM teste novo — o fixture v1.2.0 + controle
positivo já rodam por-PR"*. O controle positivo
(`smoke-install.yml:245-271`) roda
`test-install-upgrade-parity-e2e.sh --positive-control`, e o plant é
literalmente (`:225-231`):

```
grep -v "^backup_and_replace \"$PLANT_TARGET\"$" .../upgrade.sh > copy
```

Ou seja: só sabe apagar linhas **da forma exata**
`backup_and_replace "<dir>"`. A entrega nova do `.gitignore` proposta no
W1 é um **append idempotente** (header + gate + `_up_record_op`), não uma
linha `backup_and_replace "<dir>"` ⇒ `--plant-target` sobre ela cai no
guard de vacuidade e sai **exit 9** ("planting failed: … occurrences
before=0 after=0", `:231`).

Portanto o controle positivo que já roda prova que o gate morde
**entregas em forma de `backup_and_replace`** — e não diz **nada** sobre
a superfície que a rc.4 acrescenta. AC-3 herda essa lacuna.

**Fix:** generalizar o plant (`:225-231`) para aceitar uma segunda forma
(remover por match exato a linha de chamada do gerador novo), e rodar o
controle uma vez com esse alvo. Alternativa mais barata e aceitável:
executar uma vez, em cópia de scratch, o **estado D** (allowlist removida
+ entrega revertida) e anexar o transcript FATAL como o controle
positivo desta superfície. Sem uma das duas, o plano viola a própria
doutrina ("controle positivo em cada gate") justamente no P1 que o Codex
descreveu com mais detalhe.

**(ii) OQ-1 — `E_DECISION = 13` é a escolha certa, MAS o guard que dá
sentido a "distinto" está podre.**
`.claude/scripts/tests/test_release_workflow_asserts.py:1000-1013`
(`test_module_exit_codes_are_distinct_nonzero`) enumera os códigos **à
mão** — e a lista vai de `E_USAGE` até `E_VACUOUS` (2..11), **omitindo
`E_PARENT_NOT_ANCESTOR = 12`** (`_release_tag_guard.py:87`). Já apodreceu
uma vez. Acrescentar 13 a uma lista manual repete o padrão; não
acrescentar significa que o código novo nunca é conferido.

**Fix:** derivar o conjunto (`[v for k, v in vars(mod).items() if
k.startswith("E_")]`) e assertar não-zero + distintos + **contagem
mínima**. É a lição "conjunto fechado escrito de memória erra nos dois
sentidos" aplicada ao arquivo que a própria cura toca.

**Resposta a OQ-1:** código **novo (13)**, sim. Motivo operacional, não
estético: `E_VERDICT=10` significa "o veredito é inutilizável — conserte
o arquivo"; a decisão `NO-GO` significa "o arquivo está perfeito — **não
libere**". São respostas opostas do operador; conflacioná-las num único
código transforma triagem de release em adivinhação. Mas só vale se
M2(ii) entrar junto.

### M3 [P1] — OQ-3: o gate "Where enforced ⇒ step existe" é robusto **desde que tenha contagem mínima**

Respondendo diretamente: **é executável e não é frágil**, se o parser for
restrito. Verificado em `npm/INTEGRITY.md:21-28`, as 6 linhas têm formas
heterogêneas:

- `:23` — `` `.github/workflows/validate.yml` (to-add) `` (promessa, sem step)
- `:24` — "Release operator signs locally" (sem workflow)
- `:25` — workflow nomeado, **sem** nome de step
- `:26` — "Release script (Sprint 17 scope)" (sem workflow)
- `:27` — `` `…npm-publish.yml` step "Verify zero runtime dependencies" ``
- `:28` — `` `…npm-publish.yml` step "Verify VERSION matches tag" ``

Confirmei que os dois nomes citados existem **verbatim** em
`npm-publish.yml:278` e `:255`.

**Fix — 3 requisitos, não 1:**
1. Parsear **só** a forma restrita: workflow em backticks + palavra
   literal `step` + nome entre aspas duplas.
2. Comparar com `- name:` por **igualdade exata**, nunca `in`/substring
   (a classe substring-vs-exact mordeu 3× na S299).
3. **Assert de contagem mínima (≥ 2 hoje).** Sem isso o gate é vacuoso
   por construção: a próxima reescrita da tabela derruba os matches para
   zero e o teste fica verde sobre nada — exatamente a classe do
   `check_tier_a_spec_version_drift`. Dois controles: (a) step renomeado
   ⇒ red; (b) tabela com todas as formas `step "…"` removidas ⇒ red **na
   contagem**, não silêncio.

Observação de conteúdo: `:23` diz `(to-add)` — é a MESMA classe do P1-3
morando dentro da tabela que o gate vai vigiar. Ela fica fora do parser
restrito, então precisa ser curada por texto no W0 item 3, como o plano
já prevê.

### M4 [P1] — não adicionar `"npm"` cru a `SCAN_ROOTS` sem tripwire de staging

`scan_live_surfaces` (`test_release_bump_sites.py:1160-1177`) varre o
**filesystem** (`base.rglob("*")`), não o índice do git. E
`npm-publish.yml:288-326` ("Stage bundle into npm/") faz
`rsync -a --delete` de `scripts templates .claude SPEC VERSION LICENSE
PROTOCOL.md` **para dentro de `npm/`**.

Hoje `npm/` está limpo (6 arquivos, todos rastreados — conferi
`git ls-files npm` vs `find npm -type f`, 6 = 6). Mas qualquer execução
local de staging (e o repo já teve incidente de staging sobrescrevendo
`npm/README.md`, S288) faz o scanner varrer uma **cópia inteira de dois
roots que ele já varre** e reportar hits em paths `npm/...` que não
existem no git — red pelo motivo errado, na véspera de um corte.

**Fix:** ou listar arquivos (o `SCAN_ROOTS` já aceita entradas de
arquivo — `RELEASE.md` é uma), ou manter `"npm"` **mais** um tripwire
alto: se existir sob `npm/` qualquer diretório além de `bin/`, falhar com
"staged bundle detected under npm/ — clean before running". O importante
é que a falha **nomeie a causa real**.

### M5 [P1] — OQ-4 (parte 1): nenhuma fase do `release.sh` observa as duas variáveis que desligam os gates

`grep -n "CEO_PAIR_RAIL_VERDICT_OPTIONAL\|CEO_SOTA_DISABLE\|gh variable"
.claude/scripts/local/release.sh` retorna **zero** ocorrências. Enquanto
isso, no lado servidor:

- `release.yml:15` — `release-gate:` tem `if: vars.CEO_SOTA_DISABLE != '1'`;
- `release.yml:689` — o step 15 (**exatamente onde a cura do P1-4 entra
  no validador**) tem
  `continue-on-error: ${{ vars.CEO_PAIR_RAIL_VERDICT_OPTIONAL == '1' }}`.

Consequência que o plano precisa declarar em voz alta: **com
`CEO_PAIR_RAIL_VERDICT_OPTIONAL=1`, o gate de decisão novo dentro de
`validate-pair-rail-verdict.py` não consegue reprovar o job.** Nada vaza
(o passo delta recusa a variável de saída, `release.yml:786-790`;
`publish-release` depende de `release-gate`, `:876`; `await-release-gate`
faz poll do job) — mas o plano hoje apresenta os dois validadores como
simétricos, e eles não são:

> **a metade que enforça é `_release_tag_guard.py delta`; a metade do
> validador é defesa em profundidade que uma repo variable desliga.**

Isso também recontextualiza a variante `--parent-sha ""` da AC-1: ela é
um teste de **unidade** válido do validador, mas naquele modo o job não
falha por ele. Vale testar; não vale apresentar como prova de bloqueio.

**Fix:** (a) escrever essa frase no plano (§Riders ou AC-1); (b)
acrescentar ao W2, antes de assinar a tag, um assert de uma linha via
`gh variable list` de que `CEO_PAIR_RAIL_VERDICT_OPTIONAL` e
`CEO_SOTA_DISABLE` estão ausentes ou `0`. Custo ~zero, fecha uma classe.

### M6 [P1] — OQ-4 (parte 2): "CI verde" tem de ser por-JOB e pinado ao SHA

Três fatos que se combinam mal na ordem verdito→push→CI→preflight→tag:

1. `smoke-install.yml:105-107` cancela o run anterior no mesmo ref
   (`cancel-in-progress: true`). Um segundo push em main **cancela** a
   verificação do primeiro; `cancelled` não é `success`.
2. `smoke-install.yml:110` (`if: vars.CEO_SOTA_DISABLE != '1'`) e
   `release.yml:15` permitem o job ser **skipped** com o run verde — o
   próprio comentário do `await-release-gate` (`npm-publish.yml`, bloco
   de cabeçalho) diz isso: "never the run conclusion".
3. `release.yml` **não** roda o parity e2e, e `smoke-install.yml` só
   dispara em `pull_request` e `push: branches: main` (`:65-67`) — um
   push de **tag** não dispara nenhum dos dois. A evidência da AC-3 só
   existe se o pack for para main como push verde **e** a tag for cortada
   nesse SHA exato.

**Fix:** o passo "CI verde" do W2 vira: para
`SHA=$(git rev-parse HEAD)`, cada workflow requerido teve o **job**
relevante com conclusão `success` (nunca `cancelled`/`skipped`), e
`preflight`/`tag` assertam que HEAD ainda é esse SHA. É a doutrina que o
`await-release-gate` já usa — aplicada ao operador.

## Nice-to-have

- **N1 — T-1 é a única cura da rc.4 que entra sem controle**, contra a
  doutrina do próprio plano. Barato de resolver: assert estrutural em
  `.claude/scripts/tests/` (raiz que roda em `validate.yml:419` e
  `release.yml:364`) de que **todo** step de `tournament.yml` que
  referencia `projection.txt` carrega `working-directory: .claude/scripts`
  — hoje seriam 2 steps (`:145` produtor, `:190` summary após o patch), e
  o upload (`:196`) usa o path completo. Fecha também a regressão de
  alguém reordenar/duplicar o summary.
- **N2 — OQ-2: incluir `scripts/install-npm.sh:182-184` no pack W1.**
  São 3 linhas de comentário dentro de uma cerimônia GPG que já vai
  acontecer. Adiar troca custo ~0 por **uma segunda cerimônia** mais
  tarde + um re-finding garantido no próximo re-pass (o Codex já leu esse
  arquivo). Dívida canônica é a mais cara de carregar. Incluir.
- **N3 — escopo do sentinel precisa enumerar os arquivos LIVRES** que
  landam no mesmo commit canônico (`scripts/tests/_parity_classify.py`),
  senão o check `touched − scope = ∅` reprova o land. Não é opinião: é a
  mecânica do land assinado.
- **N4 — higiene dos testes novos.** Eles nascem em
  `.claude/scripts/tests/`, que `validate.yml:419` roda com `-n auto` e
  `--strict-markers`. Subprocessos + arquivos temporários: `tmp_path`, e
  isolamento de env por fixture autouse (vars de steering vazam sob
  xdist). Se qualquer um for sensível a ordem/relógio, marcar `serial`
  (a segunda passada `:420` os cobre) — e o marker precisa estar
  registrado, senão `--strict-markers` derruba a suíte inteira.

## Unseen

- **U1 — o validador do CI não tem NENHUMA suíte viva.** Depois da cura,
  o gate de decisão de `.github/scripts/validate-pair-rail-verdict.py` é
  exercitado **só** pelo teste novo, via subprocesso. Se essa invocação
  silenciosamente não rodar o arquivo certo (path, `sys.executable`,
  cwd), o teste passa e o gate fica sem cobertura — e nada avisa. Peça um
  assert sobre uma **string distintiva do stderr** do próprio gate, não
  só sobre `returncode` (a lição "controle que não falha = sonda morta").
- **U2 — a receita de consumidor do `INTEGRITY.md:45-48` continua
  impossível mesmo depois da cura de honestidade**, porque
  `npm/SHA256SUMS.txt` não está no `files` do `package.json` ⇒ não viaja
  no tarball. "Corrigir a receita" precisa significar **remover/substituir**
  o bloco, não anexar uma ressalva; senão o próximo re-pass reencontra o
  mesmo P1 com outra redação.
- **U3 — quem vigia a neutralidade do `INTEGRITY.md:4` depois?** O
  scanner novo é a única guarda. Então o controle positivo dele deve
  plantar um semver **nesse arquivo**, não num `npm/*.md` genérico —
  senão prova a regra, não a superfície.
- **U4 — `npm-publish.yml:443` ("Assert remote tag still points at this
  run's SHA") é a última barreira antes do publish irreversível** e não
  aparece em lugar nenhum do plano. Não peço mudança; peço que o W2 saiba
  que ela existe, porque é ela que transforma um `git tag -d && re-tag`
  durante o hold em falha limpa em vez de publish do tree errado.

## What I would NOT change

- **Não tocar `npm-publish.yml` na rc.4.** É o caminho de publish sob
  hold ativo; rota (i) para o trem v1.4.0. Correto, e pelo mesmo
  raciocínio que exclui perf e node24.
- **Não wirar `.github/scripts/tests/` agora** — toca `validate.yml`
  (KERNEL) na véspera do corte. Registrar como dívida é a decisão certa;
  wirar 15 testes nunca executados três dias antes de um GA é como se
  compra um red surpresa.
- **O gate `CEREMONY_EFFECTIVE != user` na entrega do upgrade.** Ele não
  é só paridade: `smoke-install.yml:220-232` assert que
  `--ceremony user` **não escreve nada fora de `.claude/` no top level**,
  e `install_posture_state_ignores` escreve no `.gitignore` da RAIZ.
  Entregar em modo `user` deixaria esse assert vermelho. Manter o gate,
  espelhado de `install.sh:1860` / `upgrade.sh:3084`.
- **Gerador único em `_framework_manifest_set.sh` com saída byte a byte,
  header dentro do loop.** É a forma do INV-4 e o parity compara **bytes**
  — "reimplementar bonito" é um gate vermelho garantido.
- **`release.sh` inalterado.** `:630-631` já chama o guard `delta` com
  `|| die` para RC e stable; o exit≠0 novo mata a tag sem nenhuma edição.
- **A escolha de igualdade EXATA (sem normalização de caixa, sem
  `startswith`) no conjunto `{GO, GO-WITH-CONDITIONS}`.** Não relaxar:
  `GO-WITH-CONDITIONS` começa com `GO`, então `startswith` faria
  `GO-ANYTHING` passar. O plano acertou; deixe como está.
- **Não unificar a semântica com o `OWNER-GA-CUT.sh`.** Duas superfícies
  diferentes (rail bruto vs envelope), a do Owner deliberadamente mais
  estrita. Unificar transformaria dois controles independentes em um.
