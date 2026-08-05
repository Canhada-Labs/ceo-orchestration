---
round: 2
archetype: Principal Security Engineer
skill: security-and-auth
agent_persona: Principal Security Engineer (core team.md ICs — VETO em auth/token/input-handling per ADR-052)
generated_at: 2026-08-05T00:00:00Z
veto_round_1: LEVANTADO
veto_round_2: LEVANTADO-CONFIRMADO (design v3 marcador-RASTREADO re-verificado em 2026-08-05; supersede a verificação da Forma A anterior, cujas proteções eram condicionais)
---

## Verdict

**ADJUST** — **VETO do round 1: LEVANTADO.** O AC-2 v2 satisfaz a
condição textual item por item (tabela abaixo). Abro **um VETO novo,
escopado e barato de levantar**, sobre a única cláusula que o v2 criou e
que ninguém revisou ainda: `.claude/.framework-version` vira autoridade
de um **gate de release** sendo um arquivo sem guard canonical, fora do
inventário de integridade e fora do `verify-counts`.

### Verificação literal do AC-2 v2 contra a condição do VETO

| Condição (round 1, must-fix 1) | Texto v2 | Estado |
|---|---|---|
| run do workflow `release.yml` | AC-2: "run de `release.yml`" | ✅ |
| `event == push` | AC-2: "`event==push`" | ✅ |
| `head_branch == <nome da tag>` | AC-2: "`head_branch==<tag>`" | ✅ |
| `head_sha == SHA da tag` | AC-2: "`head_sha==GITHUB_SHA`" | ✅ |
| conclusão do **JOB** `release-gate` == success | AC-2: "job `release-gate` `conclusion=="success"`" | ✅ |
| nunca a conclusão do RUN | §OQ-1: "nunca a conclusão do run (`CEO_SOTA_DISABLE=1` pula jobs sem avermelhar)" + controle plantado "job skipped" | ✅ |
| `skipped` bloqueia | AC-2, controle 1 | ✅ |
| `null` bloqueia | §OQ-1 estado `running` + fail-CLOSED em deadline | ⚠️ semântica presente, **controle plantado ausente** (must-fix 1) |
| 6 controles plantados sem rede | AC-2 lista os 6, incl. JSON malformado | ✅ |

Os 6 must-fix do round 1 também estão atendidos no texto novo: **MF2**
(a′ dois jobs no mesmo arquivo, filename e environment intactos) §OQ-1 +
W1.1; **MF3** (gate roda em RC) §OQ-1 + W2.2 + AC-7; **MF4** (pins
fortalecidos, não relocados) W1.1 + AC-2 §"Asserts estruturais";
**MF5** (função stdlib testável sem rede + 6 controles) §OQ-1 + AC-2;
**MF6** (três listas do F3) §OQ-3 (a)(b)(c); **MF7** (ceremony-gate lido
do `.install-state.json`, fail-open se ausente) §OQ-3. Nada ficou por
fora, e a rejeição do `workflow_call` está registrada com blast radius em
§Deferred — não contesto: (a′) fecha o mesmo buraco tocando um arquivo,
e o argumento de que `release.yml` tem 29 steps pinados é verificável.

## Summary (≤ 3 bullets)

- O v2 é materialmente melhor e corrigiu duas coisas que eu **não** tinha
  visto no round 1: o fix de `VERSION` do v1 seria destrutivo
  (`install_one` é skip-if-exists — confirmei em `install.sh:854-867` —
  contra `backup_and_replace` que é delete+replace), e o teste do F4 está
  morto **duas** vezes (confirmei: `grep -rln test_install_baseline_manifest
  .github/workflows/` não retorna nada).
- A reclassificação canonical do C10 confere: rodei os 76 padrões reais de
  `_CANONICAL_GUARDS` contra os caminhos citados — `scripts/tests/**`,
  `INSTALL.md`, `.claude/scripts/local/release.sh` e
  `.claude/scripts/check-canonical-doc-freshness.py` são **livres**;
  `.github/workflows/smoke-install.yml` é guardado.
- Duas coisas quebram: (1) `.claude/governance/npm-trusted-publisher.txt`
  **É canonical-guarded** (`.claude/governance/*.txt`) e está fora do
  §W1 "Escopo canonical REAL" — a cerimônia landa com touched−scope ≠ ∅;
  (2) o marcador `.claude/.framework-version` é uma autoridade de gate
  sem nenhuma das três proteções que `VERSION` tem.

## Risks

**R2-SEC1 — CRITICAL — o marcador novo é um bypass de gate de release de
um arquivo só.** `check-canonical-doc-freshness.py` **é** o "Canonical doc
freshness gate" do `release.yml:205-208`, e lê a versão corrente em
`:138` (`open(repo_root/"VERSION")`). §OQ-3 manda esse leitor "preferir o
marcador com fallback para `VERSION`". O gate reprova um doc quando a
distância em MINORs entre a stamp e a versão corrente passa do limiar do
tier — logo **baixar a versão corrente encolhe todas as distâncias e faz
todo doc parecer fresco**. Escrever `1.0.0` em `.claude/.framework-version`
passa o gate inteiro. Verifiquei as três proteções que `VERSION` tem e o
marcador não teria:
- **canonical guard:** rodei os 76 padrões de `_CANONICAL_GUARDS` —
  `.claude/.framework-version` → **NO MATCH** (nenhum padrão tem a forma
  `.claude/.<dotfile>`). Um agente escreve o arquivo sem sentinel.
- **inventário:** §OQ-3 o coloca deliberadamente "fora do conjunto
  enumerado" → fora do `.install-manifest.sha256` → invisível ao
  `doctor.sh` (`:598-642`). É **exatamente a cegueira que o próprio F3
  está fechando para `SPEC/v1`**, recriada para a nova âncora forense.
- **`verify-counts`:** não está em `VERSION_SITES`, então nada obriga
  marcador e `VERSION` a andarem juntos no bump.
E o leitor que passaria a confiar nele
(`.claude/scripts/check-canonical-doc-freshness.py`) também é **livre**
(NO MATCH nos 76 padrões). São dois elos sem guard na mesma corrente.
*Mitigação:* ver Must-fix 2 — duas linhas resolvem.

**R2-SEC2 — HIGH — a cerimônia W1 vai bater no próprio guard.**
`.claude/governance/npm-trusted-publisher.txt` (W1.4) casa
`.claude/governance/*.txt`. O §W1 "Escopo canonical REAL (verificado
contra `_CANONICAL_GUARDS`)" nomeia 5 arquivos + ADR e **não** o inclui;
o consensus (kept 7) o chama de "livre". Com o Scope do sentinel escrito
assim, ou o hook bloqueia a criação do arquivo no meio da cerimônia, ou o
land viola a regra da casa (`touched − scope = ∅` antes de commitar).
*Mitigação:* incluir no Scope, grupo "trem de release".

**R2-SEC3 — MEDIUM — `ceo-boot` perde a invariante que ele existe para
checar.** `check_tier_a_npm_version_match` (`ceo-boot.py:951+`) compara
`VERSION` × `package.json` — o mesmo par que o `npm-publish.yml:113-122`
usa como gate de publish. Se esse leitor passar a preferir o marcador, o
boot passa a comparar marcador × `package.json` e o drift real
`VERSION`×`package.json` deixa de ser observado justamente onde ele é
barato de pegar. `check_tier_a_spec_version_drift` (`:930+`) tem o mesmo
problema, e o §Deferred já o registra como vacuoso.
*Mitigação:* no repo do framework, **nenhum** leitor prefere o marcador
(ver Must-fix 2); a preferência é semântica de árvore de ADOPTER.

**R2-SEC4 — MEDIUM — o estado `running`/`conclusion: null` não tem
controle plantado.** §OQ-1 modela três estados e manda fail-CLOSED no
deadline, o que está certo. Mas o AC-2 lista 6 controles e nenhum é "job
`release-gate` presente com `conclusion: null`" — que é o estado normal
enquanto o gate roda, e o mais provável de ser implementado errado
(`!= "failure"` em vez de `== "success"` libera `null` e `skipped` de
uma vez). O bug clássico dessa função é exatamente esse.
*Mitigação:* sétimo controle plantado. Uma linha de teste.

**R2-SEC5 — LOW/MEDIUM — o gate de ancestralidade do `tag()` faz rede.**
`git fetch --quiet origin main && git merge-base --is-ancestor HEAD
origin/main || die` (§OQ-2) é a mitigação certa para a classe C9, mas
`&&` encadeado com `|| die` faz **falha de rede virar recusa de tag**.
Isso é fail-closed (bom) e vai acontecer offline (ruim, sem mensagem
distinta). Pior: se alguém "consertar" trocando por `;`, um fetch que
falha deixa o `merge-base` rodar contra um `origin/main` STALE e
aprovar um HEAD que não está no main remoto.
*Mitigação:* separar os dois erros com mensagens distintas ("não consegui
falar com origin" ≠ "HEAD não é ancestral de origin/main") e escotilha
explícita e nomeada para o caso offline — nunca um `;`.

## Must-fix (blocking)

1. **[não-VETO] Sétimo controle plantado no AC-2: `conclusion: null`.**
   Job `release-gate` presente, run em andamento, `conclusion: null` →
   **não libera** (fica em `running` até o deadline, e o deadline é
   fail-CLOSED). Sem esse caso, a implementação `!= "failure"` passa nos
   6 controles atuais e é um bypass.

2. **[VETO escopado — condição textual de levantamento] O marcador não
   pode ser autoridade de gate sem as proteções de `VERSION`.**
   Levanto o VETO quando o §OQ-3 disser, textualmente, **uma** destas
   duas formas:
   - **Forma A (preferida, 2 linhas):** o marcador entra em
     `VERSION_SITES` do `verify-counts.sh` **e** o `release.yml` ganha um
     assert `.claude/.framework-version`, se presente, `== VERSION`
     (fail-closed), ao lado dos asserts VERSION↔tag que já existem
     (`:55-70`). Com isso o marcador vira uma cópia provada, e "preferir o
     marcador" deixa de poder divergir; **ou**
   - **Forma B:** o marcador é declarado **advisory**, nenhum gate de
     release o lê — `check-canonical-doc-freshness.py` continua lendo
     `VERSION` e só leitores de boot (advisory) preferem o marcador.
   Em qualquer das duas, mais: o marcador **entra no conjunto enumerado**
   pelo precedente que o próprio repo já tem — `_framework_manifest_set.sh`
   trata `PROTOCOL.md` como "Generated pointer" **dentro** da enumeração,
   com hash canônico (`:202`, `:226-234`). Logo "é derivado, então fica de
   fora" é contrariado pelo desenho do arquivo que o plano está editando.
   Justificativa de autoridade: ADR-052 me dá VETO sobre mudança de
   trust boundary, e §OQ-3 cria uma âncora de confiança nova lida por um
   gate de release.

3. **Corrigir o §W1 "Escopo canonical REAL": `.claude/governance/npm-trusted-publisher.txt`
   é guardado.** Casa `.claude/governance/*.txt` (verificado contra a lista
   real de 76 padrões). Entra no Scope do sentinel, grupo "trem de
   release". O consensus kept-7 que o chama de "livre" precisa da mesma
   correção, senão a cerimônia é escrita a partir dele.

4. **O assert do `npm-trusted-publisher.txt` tem de comparar com o
   arquivo, não com um literal.** W1.4 diz "assert estrutural de que o
   workflow usa exatamente esses valores". Para isso valer alguma coisa, o
   teste tem de LER `.claude/governance/npm-trusted-publisher.txt` e
   comparar com o `npm-publish.yml` — se o teste embutir os três valores,
   ele passa a ser uma quarta cópia da verdade e o arquivo vira decoração.
   Controle positivo: trocar o `environment:` no workflow numa cópia →
   teste vermelho.

5. **Declarar o que o AC-2 NÃO prova, junto do que prova.** O AC-2 já é
   honesto sobre o e2e ("o controle end-to-end vivo é a rc.2"). Falta a
   segunda metade: o exercício da rc.2 prova o **poll**, não o
   **acoplamento ao publish** — na rc.2 o job `publish` é pulado pelo
   `if` de RC, então a aresta `needs:` só é exercida de verdade no GA. Um
   AC que não diz isso vira, daqui a três releases, a frase "isso já foi
   provado ao vivo".

## Nice-to-have (advisory)

1. Adicionar o marcador ao `.gitignore` do adopter (o `install.sh` já
   instala ignores de postura — PLAN-165 CX-3, `:1801`) para não poluir o
   `git status` de quem instala. Verifiquei que hoje nenhuma regra casa
   `.claude/.framework-version`.
2. `.claude/scripts/check-canonical-doc-freshness.py` é livre e é entrada
   de gate de release. Fora do escopo deste plano, mas vale a nota: a
   família "script livre que decide gate de release" merece um passe
   próprio (é a mesma forma do `verify-counts.sh`).
3. No teste do W0.5 (guarda do `pair-rail-inputs-hash-manifest.txt`),
   derivar a lista de arquivos tocados pelo bump **do módulo**
   `_release_bump_sites.py`, não de uma cópia — senão o guard e o bump
   divergem no primeiro site novo (é a mesma classe do must-fix 4).
4. O §Deferred registra o `workflow_call` como candidato pós-GA. Vale
   anexar a ele a condição de disparo: "quando o `release.yml` for
   refatorado por outro motivo" — senão vira dívida sem gatilho.

## Unseen by the original plan

1. **O marcador herda a cegueira que o F3 está fechando, no mesmo
   commit.** O plano descreve F3 como "SPEC/v1 está fora do inventário de
   integridade do adopter inteiro (baseline manifest + doctor.sh cegos)" —
   e resolve isso — enquanto §OQ-3 coloca o marcador novo exatamente nessa
   posição, por escolha explícita. Uma âncora forense não inventariada é
   forjável, e a única razão de ela existir é ser confiada.
2. **O `already_published` deixa de ser barreira depois da reordenação, e
   isso é novo.** Hoje ele roda no mesmo job que a aprovação; sob (a′) a
   ordem vira gate → aprovação → registry-check → publish. Está correto
   (não gastar aprovação antes do gate), mas significa que a aprovação
   manual do Owner passa a acontecer **depois** de o gate já ter dito sim
   — ou seja, o Owner aprova com menos informação nova do que antes, não
   mais. Vale uma linha no checklist dizendo o que a aprovação ainda
   significa nesse ponto (é a última chance humana, não uma segunda
   opinião sobre o gate).
3. **`VERSION` também não é canonical-guarded** (NO MATCH nos 76
   padrões). Isso é pré-existente e hoje é compensado por três gates que
   o leem (`release.yml:55-70`, `npm-publish.yml:101-111`,
   `verify-counts`). Menciono porque é o argumento de por que o marcador
   precisa de Must-fix 2: `VERSION` sobrevive sem guard **porque três
   gates o cruzam com a tag**; o marcador não teria nenhum.
4. **O ceremony-gate do upgrade tem um modo silencioso que vale nomear.**
   §OQ-3 manda ler a ceremony do `.install-state.json` e fail-open se o
   estado estiver ausente/ilegível (pré-Wave-B) — concordo, é a escolha
   certa. Consequência: um adopter `--ceremony user` **pré-Wave-B** recebe
   `SPEC/v1` no upgrade, porque não há estado para dizer o contrário. Não
   é motivo para mudar a decisão (o fail-closed bloquearia todo upgrade
   legado), mas o `INSTALL.md` deve dizer em uma linha que instalações
   sem `.install-state.json` são tratadas como maintainer.

## What I would NOT change

- **A resolução do OQ-1 como (a′), e a rejeição do `workflow_call` com
  registro.** O argumento de blast radius é verificável e a nota de
  cabeçalho (kept 9) impede que a próxima pessoa "melhore" e quebre a
  invariante de rollback do `:14-18`. Não reabro.
- **`VERSION` da raiz do adopter fora do upgrade, com `ADR-155-AMEND-1`.**
  Confirmei `install_one` skip-if-exists (`install.sh:854-867`) — a
  assimetria é a decisão correta e o ADR é o que impede que ela seja
  "consertada" depois. Esse foi o melhor achado do round 1, e não era meu.
- **Fail-CLOSED em deadline, erro de API e JSON malformado**, ancorado em
  ADR-186 como verificação de INPUT. É a leitura certa da doutrina da
  casa: infra falha aberta, input falha fechado, e um poll que não
  consegue ler a resposta não sabe se o gate passou.
- **O composto F1+F2 declarado como risco único e a proibição explícita
  de adiar qualquer um dos dois.** É o parágrafo mais importante do plano.
- **Os controles positivos por rótulo do F5 e o "vermelho do JOB, não do
  script local" do F4.** Os dois convertem "o teste passa" em "o teste
  falharia se estivesse errado", que é a única forma de gate que conta.
- **O AC-2 declarar em voz alta o que ele não prova.** Ampliar (must-fix
  5), nunca remover.

## Verificação Forma A (pós-síntese)

**Estado final: VETO#2 LEVANTADO (2026-08-05).** Esta seção supersede o
status "ABERTO" registrado em `## Verdict` e no must-fix 2 acima — os
dois ficam como registro histórico do round, não como estado corrente.

Verificação literal do §OQ-3 do plano (v2.1) contra a condição textual
de levantamento que eu declarei no must-fix 2:

| # | Condição | Texto v2.1 (§OQ-3, bullet do marcador) | Estado |
|---|---|---|---|
| (i) | marcador em `VERSION_SITES` do `verify-counts.sh` | "(i) entra em `VERSION_SITES` do `verify-counts.sh` (o bump o escreve; o gate o cruza com `VERSION`)" | ✅ |
| (ii) | assert `marcador == VERSION` no `release.yml` quando presente, fail-closed, ao lado dos asserts VERSION↔tag | "(ii) `release.yml` ganha assert `marcador == VERSION` quando o arquivo existe (fail-closed, ao lado dos asserts VERSION↔tag `:55-70`)" | ✅ |
| (iii) | entrada em `_framework_target_entries()` pelo precedente generated-pointer do `PROTOCOL.md` | "(iii) entra em `_framework_target_entries()` pelo precedente generated-pointer do próprio arquivo (PROTOCOL.md, `:202,:226-234`) — inventariado, visível ao doctor" | ✅ |
| (iv) | nenhum gate do repo do framework lê o marcador (não era condição minha — é a Forma B, adotada em conjunto) | "**Nenhum gate do repo do framework passa a lê-lo**: `check-canonical-doc-freshness.py` continua lendo `VERSION`; a preferência marcador-com-fallback é exclusiva de leitores em árvore de ADOPTER (`ceo-boot.py:932,952` — advisory)" | ✅ **excede** |
| (v) | gitignore de postura (era nice-to-have 1, não condição) | "Entra no gitignore de postura do install (PLAN-165 CX-3)" | ✅ |

Notas de encerramento:

1. **A condição foi Forma A OU Forma B; o plano adotou as DUAS.** Com
   (iv), o marcador deixa de ser entrada de qualquer gate do repo do
   framework, e com (i)+(ii) ele não pode divergir de `VERSION` mesmo
   assim. Isso fecha o R2-SEC1 (bypass do freshness gate) na origem e o
   **R2-SEC3** (o `check_tier_a_npm_version_match` do `ceo-boot` continua
   comparando `VERSION` × `package.json` no repo do framework) sem que eu
   tivesse pedido — o R2-SEC3 estava listado como risco, não como
   condição.
2. **(iii) mata a cegueira que eu levantei no Unseen 1**: o marcador
   passa a ser inventariado no baseline manifest e visível ao
   `doctor.sh`, em vez de recriar, para a âncora nova, a mesma cegueira
   que o F3 está fechando para `SPEC/v1`.
3. **Residual honesto (não bloqueante, não é gap da condição):** o assert
   (ii) é condicional à presença do arquivo, e no repo do framework o
   marcador normalmente não existe (install/upgrade escrevem no TARGET).
   Ou seja, o assert é uma rede para o caso de alguém criar o arquivo no
   repo — que é exatamente a superfície de ataque que eu descrevi — e não
   um gate que roda em toda release. Isso é o desenho correto; registro
   para que ninguém depois leia "o assert roda sempre" na cascata.
4. Meus must-fix 1, 3, 4 e 5 do round 2 foram reportados como aplicados
   (8º controle plantado com `WAIT` para `conclusion: null`; 6ª superfície
   canonical no §W1 — `.claude/governance/npm-trusted-publisher.txt`;
   assert que LÊ o arquivo em vez de embutir literais; AC-2 declarando o
   que a rc.2 não prova). Não os re-verifiquei nesta rodada: o pedido
   desta mensagem foi escopado ao §OQ-3, e eles caem na cascata de
   verificação normal do plano.

**PROCEED** do lado de segurança. Sem VETO aberto.

> **SUPERSEDED (2026-08-05).** A seção acima verificou o design
> "marcador gerado só no destino", substituído pelo design
> marcador-RASTREADO. Estado corrente na seção seguinte.

## Re-verificação v3 (marcador rastreado, pós-r16)

**Estado final: VETO#2 LEVANTADO-CONFIRMADO (2026-08-05).** Esta seção é
o estado corrente e supersede a `## Verificação Forma A (pós-síntese)`.

### Correção do meu próprio registro

O codex r16 está certo: meu levantamento anterior verificou um design
cujas duas proteções eram **condicionais à existência do arquivo**, e num
marcador gerado-só-no-destino o arquivo não existe no checkout de
release — o `verify-counts` pula site ausente e um assert condicionado a
existência nunca roda. As duas proteções eram vacuosas exatamente na
árvore que importa (classe "gate vacuoso" de S291/S287). Eu cheguei a
registrar a condicionalidade no residual 3 acima e a classifiquei como
"desenho correto"; era um defeito, não uma nota. O design novo o corrige.

### Avaliação do design v3 contra a condição ORIGINAL

Condição (must-fix 2, round 2): *o marcador não pode ser autoridade de
gate sem as proteções de `VERSION`.*

| # | Design v3 (§OQ-3) | Efeito na condição |
|---|---|---|
| (i) | Arquivo **rastreado** do repo; `bump` o escreve como **12º site** e ele entra em `VERSION_SITES` — "site sempre presente, o gate cruza com `VERSION` em toda release" | Proteção 1 deixa de ser vacuosa: passa a rodar **em toda release**, não só quando o arquivo existe |
| (ii) | `release.yml` ganha assert `marcador == VERSION` **INCONDICIONAL**, fail-closed, ao lado de `:55-70` | Proteção 2 vira real e bidirecional: **ausente OU divergente = release vermelha** |
| (iii) | Entrada **NORMAL** em `_framework_target_entries()` — presente na árvore FONTE, preservada por `FMS_HASH_ROOT` (`manifest-set:245-249`), sem special-case generated-pointer | Inventariado e visível ao `doctor.sh` **sem** a gambiarra que eu mesmo havia proposto pelo precedente do `PROTOCOL.md` |
| (iv) | "Nenhum gate do repo do framework passa a LÊ-LO como autoridade": `check-canonical-doc-freshness.py` segue em `VERSION`; leitores marker-first são só de árvore de ADOPTER (`check_tier_a_spec_version_drift` advisory + `check-framework-updates.sh:82-103`); `check_tier_a_npm_version_match` **NÃO** adota (o `package.json` da raiz de um adopter é o do APP — comparar seria false-red permanente) | Condição atendida na origem, e o R2-SEC3 fica fechado com razão explícita |
| (v) | Sem gitignore (arquivo entregue é commitável) + entrega por **escritas explícitas nos dois caminhos** (`install_one` + refresh no upgrade) ALÉM da entrada FMS, porque "a enumeração NÃO entrega, só alimenta os manifest writers" | É o meu must-fix 6 do round 1 (as três listas) aplicado ao próprio marcador — a lição não ficou presa ao `SPEC/v1` |

**Veredito:** o design v3 é **estritamente mais forte** que a Forma A que
eu havia aceitado. As proteções passam de condicionais a incondicionais,
e o caminho de entrega deixa de depender da enumeração.

### Por que o guard canonical ausente deixou de segurar o VETO

Em round 2 eu verifiquei que `.claude/.framework-version` **não casa
nenhum** dos 76 padrões de `_CANONICAL_GUARDS`. Isso não mudou. O que
mudou é a **classe** da consequência:

- **Design antigo:** arquivo sem guard + proteções condicionais = um
  arquivo escrevível sem sentinel podia **enfraquecer** um gate (plantar
  `1.0.0` fazia todo doc parecer fresco). Classe **bypass** → VETO.
- **Design v3:** com o assert incondicional `marcador == VERSION`,
  qualquer adulteração do marcador **quebra a release** em vez de
  aprová-la, e nenhum gate do framework o consulta como autoridade.
  Classe **disponibilidade** (DoS auto-infligido, ruidoso e imediato) →
  não sustenta VETO.

Um guard canonical no marcador continuaria sendo um plus, mas deixou de
ser condição: ele é agora uma cópia cuja divergência é provada por um
gate a cada release.

### Residuais (não bloqueantes, para a cascata)

1. **(iii) é load-bearing, não arrumação.** Com `check-framework-updates.sh`
   marker-first, um marcador de adopter com versão **inflada** faz o
   checker dizer "em dia" e **suprime silenciosamente um upgrade de
   segurança**. O que detecta isso é precisamente o inventário do
   baseline manifest + `doctor.sh` que (iii) acabou de criar. Registro o
   acoplamento para que ninguém remova (iii) depois como simplificação:
   sem ela, o update checker vira superfície de supressão de update.
2. **Ordenação de land (verificar, não afirmo).** O assert (ii) é
   incondicional, então qualquer tag cortada de uma árvore que tenha o
   assert e **não** tenha o marcador fica vermelha. O assert vive em
   `.github/workflows/release.yml` (canonical, `.github/workflows/*.yml`)
   e o marcador é livre — classes de guard diferentes que precisam landar
   no **mesmo commit**. Além disso, `release.yml` passa a ser o **segundo
   workflow** tocado pela cerimônia (depois do `npm-publish.yml`): vale
   conferir se ele está no §W1 "Escopo canonical REAL" do sentinel. **Não
   reli o §W1 nesta passada** — o pedido foi escopado ao §OQ-3 — então
   isto é item de checagem, não achado. É a mesma forma da omissão do
   `.claude/governance/npm-trusted-publisher.txt` que peguei no round 2.

**PROCEED** do lado de segurança. VETO#2 encerrado como
LEVANTADO-CONFIRMADO; nenhum VETO aberto.
