---
round: 2
archetype: VP Engineering
skill: architecture-decisions
agent_persona: (team.md é o template do framework — linha de arquétipo apenas; esperado em dogfood)
generated_at: 2026-08-05T00:00:00Z
verifies: round-1/vp-engineering.md must-fix 1-9
---

## Verdict

**ADJUST** — 9 de 9 must-fixes do round 1 estão no texto, a maioria melhor
do que eu pedi; mas a reescrita introduziu **4 defeitos textuais novos e
verificáveis**, sendo um deles a MESMA classe que o must-fix 1 corrigiu
(superfície canônica classificada como livre) e outro uma **regressão de
cobertura** (um finding perdeu o AC que a v1 tinha).

## Summary (≤ 3 bullets)

- **O que verifiquei:** cada must-fix contra o § do texto novo, e cada
  afirmação factual nova do plano contra a árvore (não contra a intenção).
  As três afirmações de habilitação mais críticas de OQ-3 são **VERDADEIRAS**:
  `install.sh:2286` grava `"ceremony" "$CEREMONY"` e ela aterrissa no JSON
  em `:2411`; `upgrade.sh:691-701` já replaya `--profile/--stack/--harness`
  do `.install-state.json`, com fail-open em inválido (`:712`) e ausente
  (`:720`). O gate de ceremony do OQ-3 é implementável exatamente como escrito.
- **Onde ficou forte:** OQ-1 (a′) e OQ-2 (a) ganharam precisão que o round 1
  não tinha — bind conjuntivo por **job** (não por run), estados
  `not-yet-created/running/concluded`, `--today` sem default, `--restamp`,
  e o composto F1+F2 promovido a proibição explícita. §OQ-4 acertou o ponto
  que eu tinha subestimado: set-equality honesta ainda não alcançaria os
  sites fora da enumeração.
- **Onde quebrou:** `.claude/governance/*.txt` **É** canonical
  (`check_canonical_edit.py:232`) e o `npm-trusted-publisher.txt` está fora
  da lista de escopo de W1; o predicado mesma-árvore omite o quarto oráculo
  e com isso **remove uma propriedade de auto-cura** que o código atual tem;
  AC-6 perdeu o `INSTALL.md:627`; e AC-5 especifica um tipo de regra
  (`exact-com-tolerância`) que o `verify-counts.sh` **não implementa**.

## Risks

**R2-VP1 — HIGH — `.claude/governance/*.txt` é CANONICAL; a lista de escopo de W1 está incompleta.**
`_CANONICAL_GUARDS` inclui `.claude/governance/*.txt` /`*.md` /`*.yaml`
/`*.json` (`check_canonical_edit.py:232-235`). O §W1 item 4 cria
`.claude/governance/npm-trusted-publisher.txt`, mas o cabeçalho de W1
("Escopo canonical REAL (verificado contra `_CANONICAL_GUARDS`)") lista só
`npm-publish.yml`, `install.sh`, `upgrade.sh`, `_framework_manifest_set.sh`,
`smoke-install.yml` + o ADR. O `consensus.md` propagou o erro na origem
(kept-7: "arquivo novo em `.claude/governance/`, **livre**"). Consequência
mecânica: o `Write` desse arquivo é BLOQUEADO sem sentinel que o declare em
`Scope:` — a cerimônia trava no meio, com o sentinel já assinado.
*Mitigação:* adicionar `.claude/governance/npm-trusted-publisher.txt` à
lista de escopo de W1 (vira **6** superfícies canônicas + ADR) e corrigir a
linha do consensus. É a mesma classe do meu must-fix 1 do round 1 — a
verificação contra `_CANONICAL_GUARDS` foi feita para 5 caminhos e não para
o 6º, que nasceu na própria reescrita.

**R2-VP2 — HIGH — o predicado mesma-árvore omite o oráculo que cobre 3 dos 4 stamps, e com isso apaga uma auto-cura existente.**
§OQ-2 define o predicado como `VERSION == TARGET_BASE` **E** `verify-counts`
limpo **E** `build-plugin.py --check` limpo. Mapeei os 11 sites do bump
contra os oráculos: `VERSION`, `npm/package.json`
(`verify-counts.sh:560-572`), `pyproject.toml` (`:580-598`), `INSTALL.md`,
`docs/ARCHITECTURE.md`, `npm/README.md` (stamp), `SBOM.md`
(`**Version:**`), `SECURITY.md`/`VERSIONING.md` (janela Current/Previous)
estão cobertos. **Mas os stamps `last-reviewed:` de `SBOM.md`,
`SECURITY.md` e `VERSIONING.md` NÃO estão em `VERSION_SITES`** — o único
oráculo desses três é `check-canonical-doc-freshness.py`, que o predicado
não consulta. Hoje o `bump` reescreve esses stamps incondicionalmente, ou
seja, **se auto-cura**; sob OQ-2(a) ele não escreve nada e a stamp stale
sobrevive. O caminho documentado (preflight → bump → tag) mascara isso
porque o preflight roda o freshness gate antes; mas as três fases são
invocáveis de forma independente (a ordem é documentação, não enforcement),
e `tag()` só checa VERSION + árvore limpa.
*Mitigação:* acrescentar `check-canonical-doc-freshness.py` como **quarto
conjunto** do predicado. Custo: uma linha. Efeito: "mesma árvore" passa a
significar *os quatro oráculos limpos*, e uma stamp stale força o caminho de
substituição — que é justamente onde a camada in-loop já faz a coisa certa
(o skip por-site só dispara "quando a versão na stamp já é o alvo", logo uma
stamp em v1.2.0 é reescrita). Sem isso as duas camadas ficam inconsistentes:
a interna cura, a externa impede a interna de rodar.

**R2-VP3 — MEDIUM — AC-6 perdeu o `INSTALL.md:627`: um finding sem AC.**
A linha de F6 na §Findings lista "`INSTALL.md:627` migração obsoleta", e a
v1 do plano tinha "AC-6 ... INSTALL descreve 150→210". O AC-6 da v2 cobre
rename, strings v1.2.0, contagens, claim de publish e checklist — **nada de
INSTALL.md**. AC-3 (F3) também não: §OQ-3 fala da "lista de refresh do
`INSTALL.md`", que é outra parte do arquivo (a lista "What gets refreshed",
`INSTALL.md:615-619`), não o texto de migração de `:627`. E §W0.4 deixa o
destino do arquivo condicional ("fica para W1 apenas se o texto 150→210
couber no mesmo patch de F3"). Resultado: o único sub-finding de F6 que
descreve comportamento errado a um adopter fica sem critério de aceitação e
sem wave definida.
*Mitigação:* devolver a cláusula a AC-6 ("`INSTALL.md:627` descreve
150→210, ADR-110-AMEND-2") e fixar a wave. Verifiquei o fato: `upgrade.sh`
tem `OLD_PAIR_RAIL_CAPS = (60, 150)` migrando para 210
(`scripts/upgrade.sh:1987, :2002-2018`), enquanto `INSTALL.md:627` ainda diz
"60 → 150 s, ADR-110-AMEND-1".

**R2-VP4 — MEDIUM — AC-5 especifica um tipo de regra que o `verify-counts.sh` não tem, sem banda declarada.**
O script só implementa dois `kind`: `"exact"` (igualdade) e `"floor"`
(`.claude/scripts/local/verify-counts.sh:299`, aplicado em `:463-465`). AC-5
exige "regra nova casa a forma e é **exact-com-tolerância**". Não existe
tolerância no script — e o valor nos docs é ARREDONDADO (`~13,000`) contra
um derivado cru (`VC_TESTS`, de `pytest --collect-only -q .claude/`,
`:160`). Uma regra `exact` sobre `13000` vs a contagem real falha no dia 1;
uma tolerância escolhida depois, para o número de hoje passar, é gate
calibrado para passar — a família
`feedback-measurement-must-list-its-inputs`.
*Mitigação:* decidir no texto e declarar a banda: ou (i) terceiro `kind`
(`approx`) com banda EXPLÍCITA e justificada (ex.: `±5%`, com o motivo
escrito), ou (ii) migrar os docs para a forma `N+` já suportada
(`~13,000 cases` → `13000+ cases`) e reusar `floor`. (ii) é mais barato e
não adiciona maquinaria — mas perde a detecção de "número muito ALTO", que é
exatamente a direção do drift do `npm/README.md` hoje. Recomendo (i) com
banda declarada; o importante é que o plano ESCOLHA, porque hoje ele
prescreve algo inexistente.

**R2-VP5 — MEDIUM — W1 concentra o item mais propenso a iteração DENTRO da cerimônia.**
O e2e de F4 (fixtures reais, install v1.2.0 pinado, upgrade, dois modos de
cerimônia, comparação de árvores) é o item com maior chance de precisar de
várias voltas — e está em W1, onde o sentinel já foi assinado (reescrever
`approved.md` obriga a re-assinar). Mas o **arquivo de teste é livre**:
confirmei que não há glob cobrindo `scripts/tests/**` nem
`.claude/scripts/tests/**` em `_CANONICAL_GUARDS`. Só a **fiação**
(`smoke-install.yml`) é canônica.
*Mitigação:* autorar e estabilizar o e2e e os asserts novos de
`test_release_workflow_asserts.py` em **W0** (livre, iterável à vontade), e
deixar em W1 apenas a fiação de uma linha + a sincronização dos `paths:`.
Mesma lógica para o teste D/D+1 de AC-1 e as 6 unidades plantadas de AC-2.
Reduz o risco de estar depurando flake de fixture com sentinel assinado na
mão.

**R2-VP6 — LOW — o rename não pode tocar a evidência hash-manifestada.**
`grep -rn 'release-v1-2-0'` no repo acha ocorrências em
`PLAN-166/repass-r1/{verdict-r1.txt,paths.manifest.txt,payload.redacted.txt}`
e nos arquivos do round 1. Um `sed -i` "prestativo" durante o rename
quebraria o `MANIFEST.sha256` da própria evidência que sustenta o plano.
*Mitigação:* AC-6 diz explicitamente que o grep de controle é sobre
**superfícies vivas** e que `PLAN-166/repass-r1/**` e `debate/**` são
imutáveis por construção. (O escopo do grep — `.github/ RELEASE.md` — está
ADEQUADO: confirmei que fora de `plans/` a única referência viva é
`.github/release-checklist.md`; `RELEASE.md` não cita o driver hoje.)

**R2-VP7 — LOW — a nota de UX do timeout deve dizer a ROTA DE RECUPERAÇÃO, não só "não é falha real".**
§Riscos promete "nota de UX no checklist (timeout ≠ falha real)". Um
fail-CLOSED sem rota documentada é a metade ruim do contrato (memória
`feedback-closed-sets-must-be-derived-not-recalled`: todo gate fail-closed
precisa de rota de recuperação).
*Mitigação:* a nota deve dizer *o que fazer*: re-rodar o job
`await-release-gate` depois que o `release-gate` ficar verde — o run da tag
está pinado à árvore da tag, então o re-run é seguro e NÃO exige
delete/re-tag.

## Must-fix (blocking)

1. **Adicionar `.claude/governance/npm-trusted-publisher.txt` ao escopo
   canônico de W1** (R2-VP1). Evidência: `check_canonical_edit.py:232`.
   Corrigir também a linha kept-7 do `consensus.md`, que é a origem do erro.
2. **Acrescentar `check-canonical-doc-freshness.py` ao predicado
   mesma-árvore de §OQ-2** (R2-VP2), e dizer no texto por quê: é o único
   oráculo dos stamps `last-reviewed:` de SBOM/SECURITY/VERSIONING, e sem ele
   o no-op externo impede a cura in-loop de rodar.
3. **Devolver `INSTALL.md:627` (150→210) a AC-6 e fixar a wave** (R2-VP3).
   Remover o condicional "fica para W1 apenas se couber" do §W0.4 — um
   arquivo livre não precisa de condicional; escolha W0 e pronto.
4. **Declarar a banda de tolerância de AC-5, ou migrar os docs para a forma
   `N+`** (R2-VP4). Como está, AC-5 prescreve um `kind` que não existe.
5. **Mover a AUTORIA dos testes livres para W0** (R2-VP5): e2e de F4,
   asserts de `test_release_workflow_asserts.py`, teste D/D+1 de AC-1 e as 6
   unidades de AC-2. W1 fica com a fiação canônica.
6. **Dizer ONDE os testes novos vivem** — e que é dentro do conjunto que o
   CI roda. `.claude/scripts/tests/` é executado por `validate.yml:424` e
   `release.yml:332`; `scripts/tests/*.sh` só roda via `smoke-install.yml`
   (com filtro de `paths:`). O plano acabou de diagnosticar F4 como "teste
   que nunca rodou"; seus próprios testes novos precisam do endereço
   escrito, senão a lição não se aplica a si mesma.
7. **AC-6 declara o grep como controle de superfícies VIVAS** e marca
   `PLAN-166/repass-r1/**` + `debate/**` como imutáveis (R2-VP6).

## Nice-to-have (advisory)

1. §Riscos: a nota do timeout ganha a rota de recuperação explícita
   (R2-VP7).
2. `docs/ARCHITECTURE.md:74` diz `~13k parametrized` — forma diferente das
   duas que AC-5 vai cobrir (`~N,000` / `~N.000`). Está com o valor CERTO
   hoje, então não é finding; mas se a regra nova nascer só com as duas
   formas, ARCHITECTURE fica de fora do gate. Ou inclui `~Nk`, ou registra a
   omissão deliberadamente (não silenciosamente).
3. `.claude/scripts/local/_release_bump_sites.py` — nome novo, arquivo
   livre, sem colisão. Vale afirmar no texto que o driver passa a
   INVOCAR o módulo (não duplicar a tabela `SITES`), senão nasce uma segunda
   fonte de verdade dos 11 sites.
4. §W2.5 (nota "tag GA e última RC apontam para o mesmo commit") é boa e
   barata; considerar promovê-la de nota de checklist a **assert** no
   `tag --stable` — se sob OQ-2(a) o caminho feliz garante mesmo-commit,
   divergência é sinal, e sinal barato vale gate.

## Unseen by the original plan

1. **A auto-cura que OQ-2(a) remove** (R2-VP2). O round 1 não podia ver isto
   — a OQ ainda não tinha resposta. É a única consequência do OQ-2 que
   piora algo que hoje funciona, e o conserto custa uma linha. Detalhe que
   torna o achado preciso: o freshness gate decide por **MINOR releases
   atrás**, lendo a VERSÃO da stamp, não a data
   (`check-canonical-doc-freshness.py`, `stamp = (int(m.group(2)), …)`,
   `behind = minor_releases_behind(cur, stamp)`; `m.group(1)`, a data, é só
   reportada). Isso confirma que **congelar a DATA é seguro** — a
   preocupação natural com OQ-2(a) não se materializa — e isola o problema
   real na VERSÃO da stamp quando o predicado externo curto-circuita.
2. **`npm/README.md` não está em `DOC_TIERS`.** Dos 4 stamps que o bump
   toca, três (SBOM, SECURITY, VERSIONING) são vigiados pelo freshness gate
   e o quarto (`npm/README.md`) é vigiado por `verify-counts` via
   `VERSION_SITES` (`:487`). São oráculos DIFERENTES para o mesmo tipo de
   stamp. O skip por-site precisa preservar os dois; o texto de §OQ-2 fala
   de "os 4 sites" como se fossem homogêneos. Não é bug, é uma armadilha de
   implementação que merece uma frase.
3. **A lista de escopo de W1 mistura dois conceitos.** O cabeçalho diz
   "Escopo canonical REAL", e §W1.5 diz "Scope do sentinel em DOIS grupos".
   São coisas distintas: o conjunto de superfícies que EXIGEM sentinel, e o
   bloco `Scope:` do `approved.md`. O hook só bloqueia caminhos canônicos
   fora de `Scope:`, mas a disciplina de land deste repo é
   `touched − scope = ∅` sobre o commit inteiro. Se o implementador copiar a
   lista de 5 (ou 6) para o `Scope:` e o commit da cerimônia carregar também
   o ADR, o teste novo e o `npm-trusted-publisher.txt`, o land trava. Vale
   uma frase separando os dois conceitos e dizendo que o `Scope:` enumera
   **todo caminho do commit**.
4. **O `--restamp` precisa de contrato com o `--npm-readme-reviewed`.** Os
   dois existem pela mesma razão (afirmar re-leitura real), e agora coexistem
   com semânticas próximas. Se `--restamp` re-data sem exigir
   `--npm-readme-reviewed`, ele vira o bypass do tripwire que OQ-2 acabou de
   defender. Uma linha: `--restamp` IMPLICA `--npm-readme-reviewed`
   (ou o exige).

## What I would NOT change

1. **OQ-1 = (a′) com bind conjuntivo por JOB, não por run.** O detalhe
   `conclusion` do **job** `release-gate` (e não do run) é mais forte do que
   eu pedi no round 1 e fecha o buraco do `CEO_SOTA_DISABLE`. Manter
   verbatim, incluindo os três estados do poll.
2. **`await-release-gate` sem exclusão de RC, `publish` com ela.** É o que
   dá controle positivo VIVO na rc.2 sem publicar nada. Não "otimizar" a
   ordem depois, e não mover o `already_published` para fora do publish.
3. **OQ-2 = (a), e a recusa explícita de (b).** O argumento de
   estado-rasgado e o de claim-falsa-em-superfície-assinada continuam
   corretos. O `--today` obrigatório sem default está certo pela memória
   `frozen-evidence`.
4. **OQ-3: `VERSION` da raiz intocado + `.claude/.framework-version`.**
   Re-verifiquei as duas premissas: `install_one` é skip-if-exists e o
   `_write_baseline_manifest` documenta a armadilha C.5 no próprio arquivo.
   E o gate de ceremony é implementável: `install.sh:2286` grava a ceremony,
   `:2411` a serializa, `upgrade.sh:691-720` já tem o padrão de replay com
   fail-open. Nada a mudar aqui.
5. **OQ-4 por modo de cerimônia.** "Senão a divergência by-design vira
   allowlist, e allowlist é onde gates morrem" — é a frase certa. Manter.
6. **§Deferred como está.** O `workflow_call` está corretamente registrado
   como candidato pós-GA com o motivo do blast radius; a rejeição está
   documentada, que era a condição justa para quem propôs.
7. **Orçamento 3-4 sessões.** Com o must-fix 5 (autoria dos testes em W0)
   continua realista. Vale só registrar que `budget_sessions` e o hold de
   24h são unidades diferentes: W2.3-4 é bloqueado por relógio, não por
   trabalho — o `external_wait` no frontmatter já diz isso, então não peço
   mudança.

---

## Verificação item-a-item dos must-fix do round 1

| # (round 1) | Onde fecha no texto v2 | Status |
|---|---|---|
| 1. F4/F6 livres; escopo W1 real | §Findings (F4 "**livre** (`scripts/tests/**` não é guardado)"; F6 "**livre** (INSTALL.md não é guardado)") + §W1 cabeçalho | ✅ **com exceção**: falta `.claude/governance/*.txt` (R2-VP1) |
| 2. F6 inteiro para W0 | §W0.4 "F6 completo" | ✅ **parcial**: o condicional do INSTALL.md deixa uma parte sem wave (R2-VP3) |
| 3. ADR-155-AMEND-1 em W1 | §W1 cabeçalho + §W1.2 + §OQ-3 último bullet | ✅ |
| 4. Reescrever direção de F3 | §OQ-3 (SPEC/v1 nas três listas; VERSION intocado; marcador; ceremony-gate) | ✅ **e as premissas verificam**: `install.sh:2286/:2411`, `upgrade.sh:691-720` |
| 5. AC-4 = vermelho de CI + fiação | AC-4 + §OQ-4 bullets 3-4 (paths em AMBAS as listas) | ✅ |
| 6. AC-5 sub-escopo (6 ocorrências + npm/README + FAQ) | §Findings F5 + AC-5 | ✅ no escopo; ❌ no tipo de regra (R2-VP4) |
| 7. Rename do driver | §W0.4 + AC-6 (grep de controle) | ✅; escopo do grep verificado adequado, falta a exclusão da evidência (R2-VP6) |
| 8. Gate de ancestralidade em `tag()` | §OQ-2 último bullet + §W0.2 + §Riscos | ✅ |
| 9. Composto F1+F2 declarado | §Riscos 1º bullet ("Proibido adiar F1 ou F2 para pós-GA") | ✅ **melhorado** (somou a cegueira do step 15) |

### (ii) Coerência das resoluções — cruzamentos checados

- **Predicado mesma-árvore × rename do driver:** batem. O driver
  (`release.sh`) invoca `verify-counts.sh` e `build-plugin.py` por caminho,
  não por nome próprio; o módulo novo
  (`.claude/scripts/local/_release_bump_sites.py`) é livre (sem glob em
  `_CANONICAL_GUARDS`); `.github/release-checklist.md` é livre e está em
  W0.4. Nenhuma referência cruzada quebra. A única ressalva é editorial
  (nice-3): o driver deve INVOCAR o módulo, não duplicar `SITES`.
- **Predicado × oráculos:** NÃO batem — R2-VP2. Mapeei os 11 sites; três
  stamps ficam fora dos três conjuntos do predicado.
- **Predicado × freshness por DATA:** batem, e melhor do que se poderia
  temer — o gate é por MINOR, não por data (Unseen 1).
- **Predicado × `npm/package.json`:** batem.
  `verify-counts.sh:560-572` (e `:580-598` para `pyproject.toml`) comparam
  exact contra o VERSION vivo, com liveness fail-closed em zero matches.
  Congelar a substituição não deixa esses dois driftarem sem alarme.
- **OQ-3 × F4:** batem. Como o upgrade não toca a raiz, a fixture com
  `VERSION` pré-existente não gera o vermelho-por-design que eu levantei no
  round 1 — o §OQ-4 último bullet já registra a dependência explicitamente.
- **OQ-1 × pins de RC:** batem. `publish` mantém `if:` e `environment`
  verbatim, e os asserts de `test_release_workflow_asserts.py` são
  descritos como FORTALECIDOS, não relocados.

### (iii) Orçamento e estrutura de waves

Com o escopo expandido, **W0 carrega mais massa que W1** (F2 completo + F5
em 4 docs + regra nova + F6 com rename + teste do inputs-hash-manifest +
gate de ancestralidade). Isso é bom: é tudo superfície livre, iterável,
paralelizável, e sem custo de re-assinatura. A incoerência é a oposta da que
se esperaria — **W1 está pesado demais para uma cerimônia de tiro único**,
porque colocou lá dentro o item mais experimental (o e2e de F4) sem
necessidade: o arquivo de teste é livre, só a fiação é canônica (R2-VP5,
must-fix 5). Movendo a autoria para W0, W1 fica com 6 superfícies canônicas,
o ADR e alterações pequenas e bem definidas — que é o formato certo para
`touched − scope = ∅` sobreviver.

`budget_sessions: 3-4` fica coerente sob essa redistribuição. W2 continua
dominado por relógio (hold de 24h) e por rounds de codex, não por trabalho
de edição.
