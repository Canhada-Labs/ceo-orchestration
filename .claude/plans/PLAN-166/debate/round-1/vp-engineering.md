---
round: 1
archetype: VP Engineering
skill: architecture-decisions
agent_persona: (team.md is the framework template — archetype row only, no filled persona; expected in dogfood mode)
generated_at: 2026-08-05T00:00:00Z
---

## Verdict

**ADJUST** — os 6 findings são reais (verifiquei cada um contra a árvore;
nenhum refutado), mas o plano erra a classificação canonical de duas
superfícies, não tem item de ADR para uma mudança de contrato do ADR-155,
sub-escopa F5 e AC-4, e não enuncia o composto F1+F2 — que é o caminho
único e coerente para publicar uma árvore não revisada.

## Summary (≤ 3 bullets)

- **O que o plano tenta fazer:** fechar os 6 findings do re-pass NO-GO
  antes do GA, via W0 (livre) + W1 (cerimônia única) + W2 (rc.2 → hold →
  GA). A decisão de corrigir tudo antes do GA está certa.
- **Onde é forte:** a triagem por superfície (livre vs canonical) é o
  eixo certo de decomposição; agrupar TODOS os patches canônicos numa
  cerimônia é correto; o plano já vai ALÉM do verdito em F5 (achou o
  drift de `~12.000` que o codex não citou) e em F6 (achou os 11 sites).
- **Onde é fraco:** (i) a tabela de findings marca F4 e F6 como canonical
  — os dois são **livres**, o que muda o escopo do sentinel de ~6
  superfícies para **3 arquivos**; (ii) **nenhuma wave cria ADR**, e F3
  altera o contrato do ADR-155 no diretório raiz do adopter; (iii) AC-4
  prova que o *teste* falha, não que o **CI** fica vermelho — e o teste
  de F4 **não é executado por nenhum workflow hoje**; (iv) AC-5 fecha
  `README.pt-BR.md` enquanto `npm/README.md` — o artefato que o npm
  publica, e que **já está em `DOCS`** — carrega o mesmo número stale.

## Risks

**R-VP1 — CRITICAL — F3 como escrito é uma ESCALAÇÃO destrutiva, não paridade.**
`install_one()` (`scripts/install.sh`) é *skip-if-exists*:
`if [[ -e "$dst" || -L "$dst" ]]; then echo "    EXISTS (skipping)"; return; fi`.
`backup_and_replace()` do `upgrade.sh` é delete+replace-com-backup. Tornar
`VERSION` uma superfície de upgrade "com a semântica de backup existente"
faz o upgrade **sobrescrever** um arquivo que o install **nunca**
sobrescreve — num nome genérico (`VERSION`) na **raiz** do repo do
adopter, fora de `.claude/`. É exatamente a classe de perda de dados S238
que o ADR-155 existe para prevenir, e o próprio ADR-155 chama o arquivo
de raiz de "the verified worst case".
*Mitigação:* separar F3 em duas decisões — `SPEC/v1` vira superfície de
upgrade (namespace do framework, colisão zero); o marcador de versão do
framework passa a ser `.claude/.framework-version`, escrito
incondicionalmente por install E upgrade, e o `VERSION` da raiz **não é
tocado pelo upgrade**. Leitores verificados do VERSION instalado:
`.claude/scripts/ceo-boot.py:932,952` e
`.claude/scripts/check-canonical-doc-freshness.py:138` — ambos são
scripts SHIPADOS (dentro de `.claude/scripts`, superfície de upgrade), logo
podem ser ensinados a preferir `.claude/.framework-version` com fallback
para `VERSION`. Mudança contida; clobber da raiz do adopter não é.

**R-VP2 — HIGH — o classificador de baseline não salva `VERSION`; ele o mata.**
Como o install **pulou** o `VERSION` do adopter, o próximo
`_write_baseline_manifest` gravaria `hash(VERSION-do-adopter)` como
baseline framework-owned. O upgrade seguinte lê `H_dst == H_base` →
classifica FRAMEWORK-CHANGED → clobber. É a falha de idempotência C.5
**já documentada** no comentário `FMS_HASH_ROOT` dentro do próprio
`scripts/_framework_manifest_set.sh`. Adicionar `VERSION` ingenuamente
entra numa armadilha que o arquivo descreve.
*Mitigação:* mesma de R-VP1 — não adicionar `VERSION` ao conjunto.

**R-VP3 — HIGH — a tag pode apontar para um commit fora de `origin/main`, e nada verifica.**
`preflight()` afirma `HEAD == origin/main` (`release-v1-2-0.sh:150-153`),
e só então `bump()` cria um commit por cima. `tag()` re-checa apenas
VERSION + árvore limpa. Grepei `merge-base|is-ancestor|--contains` em
`release.yml` e no driver: **zero** ocorrências. Logo a asserção mais
forte do preflight é vacuosa para a árvore que é efetivamente assinada,
em QUALQUER run em que o bump commite — não só no caso D+1. F2 torna o
caso comum um no-op mas deixa a **classe** aberta.
*Mitigação:* `tag()` ganha, após um `git fetch --quiet origin main`,
`git merge-base --is-ancestor HEAD origin/main || die "o bump criou um
commit — pushe main e re-rode o preflight"`. ~4 linhas, superfície livre,
converte um risco silencioso em instrução alta.

**R-VP4 — HIGH — F1 e F2 COMPÕEM; o plano trata os dois como independentes.**
Hoje o único gate que revalida a árvore da tag é o `release.yml` (ele faz
checkout da tag). O `npm-publish.yml` **não observa** o `release.yml`.
Somando R-VP3: "tag GA num commit que nunca esteve em main e nunca passou
por CI" + "npm publica sem observar o gate" é um caminho único e coerente
para publicar uma árvore não revisada. Nem o verdito nem o plano enunciam
o composto — e é o argumento mais forte para F1 e F2 saírem na MESMA
release.
*Mitigação:* declarar o composto no §Riscos do plano e proibir
explicitamente adiar qualquer um dos dois para pós-GA.

**R-VP5 — MEDIUM — o gate de F4 está morto DUAS vezes; o plano corrige só uma.**
Além da tautologia, `scripts/tests/test_install_baseline_manifest.sh`
**não é executado por nenhum workflow**. Grepei todos os `.yml`: a única
referência executável fora do próprio arquivo é
`.claude/plans/PLAN-161/land-plan161.sh:259` (script one-shot de landing).
`smoke-install.yml` roda `smoke-install.sh`,
`test-upgrade-dryrun-identity.sh` e `test-upgrade-exclusions.sh` — não
este. Corrigir só a tautologia produz um teste correto que continua nunca
rodando: a quinta instância da classe "gate vermelho invisível" deste repo.
*Mitigação:* AC-4 passa a exigir que **o job de CI fique vermelho** com a
divergência plantada, observado numa run real — não que o script saia
não-zero localmente.

**R-VP6 — MEDIUM — nenhuma wave produz ADR.**
`_framework_manifest_set.sh` se autodescreve como "the SINGLE canonical
enumeration of framework-owned files that an upgrade overwrites
(PLAN-138 Wave C / ADR-155)". Alterar esse conjunto muda o que
"framework-owned" significa para o adopter e — na formulação do verdito —
muda a postura destrutiva na raiz do repo dele. CLAUDE.md §4 exige ADR
para escolha arquitetural transversal. O plano não tem item de ADR em
wave nenhuma.
*Mitigação:* `ADR-155-AMEND-1` em W1, no mesmo commit da cerimônia
(precedente: ADR-186 ratificado junto com a emenda a CLAUDE.md §4).

**R-VP7 — MEDIUM — os dois `paths:` de `smoke-install.yml` já estão dessincronizados.**
`pull_request` filtra `SPEC/v1/install-cli.md` e
`.github/workflows/smoke-install.yml`; `push` não filtra nenhum dos dois
— apesar do comentário no próprio arquivo: "keep BOTH filter lists
(pull_request + push) in sync". Qualquer fiação de CI para F3/F4 herda um
gatilho meio-armado.
*Mitigação:* corrigir a dessincronização no mesmo patch e adicionar
`SPEC/v1/**` + o novo teste a AMBAS as listas.

**R-VP8 — MEDIUM — o job de poll de OQ-1(a) precisa ser fail-CLOSED.**
Se escrito com o reflexo do §4 ("fail-open em infra"), o gate vira
decorativo: timeout de API → publica. Isto é verificação de INPUT (a
conclusão do gate é o input), não infraestrutura — precedente ADR-186.
*Mitigação:* deadline explícito, `permissions: actions: read`, e saída
não-zero em timeout/erro de API, com teste do caminho de erro.

**R-VP9 — LOW — orçamento de 2 sessões é otimista.**
W1 (cerimônia) + round codex + rc.2 + hold 24h + round final é
realisticamente mais. Não é risco de correção; é de honestidade de prazo.

## Must-fix (blocking)

1. **Corrigir a tabela de findings: F4 e F6 são superfícies LIVRES.**
   Verifiquei `_CANONICAL_GUARDS` em `.claude/hooks/check_canonical_edit.py`:
   `scripts/tests/**` não aparece; `INSTALL.md` não aparece (entre os docs
   de raiz só `PROTOCOL.md` é guardado, e `CLAUDE.md` é excluído
   explicitamente). O escopo real da cerimônia W1 é **3 arquivos**:
   `.github/workflows/npm-publish.yml` (:184), `scripts/upgrade.sh` (:191),
   `scripts/_framework_manifest_set.sh` (:199) — mais
   `.github/workflows/smoke-install.yml` se a fiação de CI de F4 entrar no
   mesmo patch (e deve). Escopo menor = `touched−scope=∅` sustentável, que
   é o modo de falha que este repo já pagou.
2. **Mover F6 inteiro para W0** (consequência de 1) e **renomear o driver**
   — ver Must-fix 7.
3. **Adicionar `ADR-155-AMEND-1` a W1** (R-VP6).
4. **Reescrever a direção de F3** conforme R-VP1/R-VP2: `SPEC/v1` entra no
   conjunto de upgrade; `VERSION` da raiz **não**; marcador vai para
   `.claude/.framework-version`. E mirrorar o gate de cerimônia: o install
   condiciona ambos a `CEREMONY != user`
   (`scripts/install.sh:1310` e `:1325`) — o upgrade não tem conceito de
   ceremony, então ou espelha o gate, ou a perna
   `--ceremony user` que `smoke-install.yml:94` já exercita (e que afirma
   "nada escrito fora de `.claude/`") fica vermelha.
5. **AC-4 passa a exigir vermelho de CI observado**, e W1 ganha item
   explícito de fiação: adicionar `test_install_baseline_manifest.sh` aos
   steps de `smoke-install.yml` **e a AMBAS** as listas `paths:`, junto com
   `SPEC/v1/**` (R-VP5/R-VP7). Registrar que isto fecha o NTH-3 do crítico
   devops do PLAN-161, que especificou exatamente esta fiação e nunca foi
   feita — é reincidência, não novidade.
6. **AC-5 sub-escopa F5 em dois eixos** (ver Unseen 1 e 2):
   (a) são **6 ocorrências em 5 linhas** no pt-BR, não 4 contagens —
   `:53` (55), `:54` (44 e 46), `:58` (~12.000), `:60` (55 e 44, na frase
   em prosa), `:167` (~12.000, no snippet de verificação). Um fix só da
   tabela deixa `:60` e `:167` stale. O EN carrega a mesma forma em `:62`
   e `:187`, então o alvo é conhecido.
   (b) `npm/README.md:60` e `:123` e `docs/FAQ.md:109` dizem `~12,000`
   contra `~13,000` do `README.md` — **e os três já estão em `DOCS`**.
   Corrigir os três em W0 e adicionar uma regra que case a forma
   `~N cases` / `~N casos`.
7. **Renomear `release-v1-2-0.sh` → `release.sh` e derivar toda string de
   versão de `TARGET_BASE`/`VERSION`** (regra dos 10x, ver Unseen 5).
   Todos os sub-findings de F6 são a MESMA classe: literal por-release num
   artefato reutilizado. Corrigir as strings para 1.3.0 compra exatamente
   uma release. Blast radius verificado: `.github/release-checklist.md`
   cita o nome literal em 6 linhas (`:93-103`) — superfície livre. Custo
   único, remoção permanente da classe.
8. **Adicionar o gate de ancestralidade em `tag()`** (R-VP3). Superfície
   livre, cabe em W0, e é o que impede que F2 feche o caso e deixe a classe.
9. **Enunciar o composto F1+F2 no §Riscos** (R-VP4).

## Nice-to-have (advisory)

1. Deletar (ou derivar) a lista fechada de "required entries" do C.2 em
   `test_install_baseline_manifest.sh` assim que a comparação e2e real
   entrar: um conjunto fechado escrito à mão vira segunda fonte de verdade
   e vai driftar — `feedback-closed-sets-must-be-derived-not-recalled`.
2. Remover as contagens de sites dos comentários do driver em vez de
   corrigi-las: um número num comentário ao lado da lista que ele descreve
   é superfície de drift pura. São 3 sites hoje (`:290` "SIX version sites,
   not two", `:388` "seventh and eighth version sites", `:395`
   "verify-counts covers the six doc/package sites above") contra 11
   entradas reais em `SITES` — o plano cita 1.
3. Registrar (fora deste plano) que `check_tier_a_spec_version_drift`
   (`.claude/scripts/ceo-boot.py:930-947`) nunca faz a comparação que o
   nome e a docstring prometem — todos os ramos retornam green com uma
   string formatada. Não bloqueia o PLAN-166; é mais uma instância da
   classe vacuous-check.
4. Se OQ-1 ficar em (a), documentar no cabeçalho do `npm-publish.yml` POR
   QUE `workflow_run` foi recusado — senão a próxima pessoa "melhora" isso
   e quebra a invariante de rollback (ver OQ-1).

## Unseen by the original plan

1. **`npm/README.md` — o artefato que o npm publica — carrega HOJE a
   contagem stale, e já está em `DOCS`.** `README.md:60` diz
   `**~13,000 cases**`; `npm/README.md:60` diz `**~12,000 cases**` e
   `npm/README.md:123` diz `~12,000 collected cases`; `docs/FAQ.md:109`
   diz `~12,000 collected cases`. A regra `tests` é
   `("tests", "floor", [r'(\d+)\+ tests', r'(\d+)\+ unit tests'])`;
   varri os 7 docs de `DOCS` por esses literais e só casam
   `INSTALL.md` (`11000+ unit tests`) e `docs/GUIA-COMPLETO.md`
   (`10500+ tests`). A forma `~N,000 cases` não casa regra nenhuma.
   Consequência dupla: (i) a premissa de F5 ("o problema é o pt-BR estar
   fora de `DOCS`") é incompleta — estar em `DOCS` não basta, a FRASE
   precisa ser casada, e `npm/README.md` prova isso; (ii) **o GA v1.3.0
   sairia com o README publicado no npm afirmando ~12.000 contra ~13.000
   do README do repo**, e AC-5 como escrita passaria assim.
   Nota de design: `tests` é regra **floor** — mesmo adicionando a frase à
   regra existente, `12.000 ≤ 13.000` satisfaz um floor e continuaria
   invisível. Precisa de regra própria exact-com-tolerância, ou os docs
   adotam a forma `N+`. O plano precisa dizer qual.
2. **F5 são 6 números em 5 linhas, não 4 contagens** — detalhe em
   Must-fix 6(a). A frase em prosa `:60` ("A diferença entre **55 em
   disco** e **44 ligados**") repete os dois números stale fora da tabela;
   `TABLE_RULES` casa só a célula de rótulo, então nem a extensão proposta
   pegaria essa linha.
3. **`README.pt-BR.md` em `DOCS` sem matchers pt-BR falha de forma
   enganosa, não silenciosa.** Os rótulos `Slash commands` e
   `Architecture decision records` são IDÊNTICOS em pt-BR e estão
   **corretos** (27 e 188 — conferi contra disco). Já `Scripts de hook (em
   disco)` e `Hooks ligados em settings.json` não casam
   `^Hook scripts\b` / `^(?:Hooks wired in|Hook registrations)\b` — e são
   justamente os stale. Adicionar o doc sem os rótulos produz um gate que
   RODA, reporta matches, contabiliza liveness e erra exatamente as linhas
   que driftaram. Por isso o controle positivo de AC-5 tem de ser
   **por RÓTULO**, não por documento.
4. **O teste de F4 não roda em CI** (R-VP5) — nem o plano nem o verdito
   mencionam. "Tautológico" subestima: é incapaz de falhar E nunca
   executado.
5. **A raiz de F6 é o nome do arquivo, não os comentários.** O driver
   chama-se `release-v1-2-0.sh` e está conduzindo o trem 1.3.0. Cada
   sub-finding de F6 é a mesma classe. O plano propõe corrigir as strings
   — o que garante a terceira ocorrência em v1.4.0. Ver Must-fix 7.
6. **A assimetria skip-vs-clobber vai virar vermelho-por-design no teste
   de F4 corrigido.** Numa fixture em que o adopter já tem `VERSION`, o
   install produz o arquivo DELE e o upgrade (pós-F3 ingênuo) produz o do
   framework. A comparação de árvores acusaria divergência que é
   comportamento CORRETO do install e BUG do upgrade. O teste precisaria de
   uma noção de "framework-owned" que absorva o skip-if-exists — ou, melhor,
   a divergência some com `.claude/.framework-version` (R-VP1). Preferir
   remover a assimetria a asserir em volta dela.
7. **Acoplamento de `release_steps`.** `RELEASE.md:19` afirma
   "release-gate + publish-release (29 steps, ...)"; `verify-counts.sh`
   deriva `grep -c '      - name:' release.yml` = 29 com tolerância **exact**.
   Confirmei: o `release.yml` vivo tem 29. OQ-1 opção (b) muda esse número
   e derruba `verify-counts` se `RELEASE.md` não for editado no mesmo
   commit — mais um custo de (b) que o plano não contabiliza.

## What I would NOT change

1. **Corrigir os 6 antes do GA.** F1+F2 compõem (R-VP4) e F3 entrega um
   estado de adopter internamente contraditório. Nenhum dos dois é
   pós-GA.
2. **Um plano só, uma cerimônia só.** F1 não deve virar plano separado:
   separar permite que metade do composto embarque sozinha. Sugiro apenas
   que o `Scope` do sentinel nomeie **dois grupos** (trem de release / upgrade
   do adopter) para permitir revert parcial — sem dividir a cerimônia.
3. **`--npm-readme-reviewed` continua obrigatório.** É tripwire deliberado
   (`release-v1-2-0.sh:36-40, 315-318`). OQ-2(a) não o enfraquece: apenas
   impede que dispare falsamente numa promoção de mesma árvore.
4. **A exclusão de tags RC e o `environment: production-npm` no
   `npm-publish.yml`.** `if: "!contains(github.ref, '-rc.')"` e o environment
   devem sobreviver a F1 intactos, e `test_release_workflow_asserts.py`
   (`test_rc_exclusion_present`, `test_rc_exclusion_precedes_publish_command`,
   `test_manual_approval_environment_gate_present`,
   `test_rc_exclusion_survives_wave_b`) deve continuar pinando os dois.
5. **`MANIFEST.sha256` rastreado + `shasum -c` fail-closed para o staged.**
   Correto, e vem de falha real anterior.
6. **Nunca aceitar transcript truncado do codex.** Manter.
7. **A wave W0 sem cerimônia.** Com a correção do Must-fix 1, W0 fica ainda
   maior (F2+F5+F6 inteiro+ancestralidade) e W1 encolhe para 3 arquivos —
   exatamente a direção certa.

---

## Respostas às OQ (lente VP Engineering)

### OQ-1 — Direção do F1: **(a)**, com mecanismo especificado.

Três evidências, todas verificadas:

1. **O próprio `npm-publish.yml` declara a invariante que (b) e
   `workflow_run` quebram.** Cabeçalho, linhas 14-18: "tag runs pin the
   workflow to the tag's tree, so a failed GA publish means rollback +
   delete/re-tag; there is no `workflow_dispatch` here by design". Um
   trigger `workflow_run` executa **o arquivo de workflow do branch
   default**, não o da árvore da tag, e roda com `github.ref` do branch
   default — a história de rollback (re-tag re-executa a árvore da tag)
   morre. O `oidc-failure-playbook.md` depende dela.
2. **(b) move o publish para um workflow diferente e o OIDC está
   registrado por NOME de workflow.** Cabeçalho :9-11 e o step de publish
   :275-280: a credencial é escopada a "repo Canhada-Labs/ceo-orchestration,
   workflow npm-publish.yml, environment production-npm". Reconfigurar é
   uma mudança manual no console do npmjs que **nenhum gate de CI
   consegue verificar** — trocar um acoplamento verificável por uma
   invariante de console web é regressão de governança, além do risco de
   ciclo que o plano já nota.
3. **(b) invalida ~6 pins de teste e o gate de contagem.**
   `test_release_workflow_asserts.py` pina
   `test_rc_exclusion_precedes_publish_command`,
   `test_manual_approval_environment_gate_present`,
   `test_publish_step_gated_on_guard`, `test_already_published_guard_present`,
   `test_noop_success_path_is_explicit`,
   `test_rc_exclusion_survives_wave_b`; e o `grep -c '      - name:'`
   de `release.yml` (29) é pinado **exact** contra `RELEASE.md:19` por
   `verify-counts.sh` (Unseen 7).

**Mecanismo para (a).** Job novo `await-release-gate` em
`npm-publish.yml`, ANTES do job `publish`, sem `environment`, com
`permissions: {contents: read, actions: read}`: resolve `github.sha` (o
commit da tag) e faz poll em
`/repos/{owner}/{repo}/actions/runs?head_sha=<sha>` procurando um run do
workflow `Release` com `conclusion == success`; **fail-CLOSED** em
timeout ou erro de API (R-VP8). Depois `publish: needs: await-release-gate`.

Ordem importa e o plano não a especifica: o gate vem **antes** do job com
`environment`. Assim a aprovação manual do Owner só aparece depois do gate
verde — o que também faz a aprovação significar alguma coisa, em vez de
ser um aceite dado enquanto o gate ainda pode reprovar.

**Sobre AC-2 e o controle positivo.** "gate red → publish não roda" ao vivo
exige um `release-gate` reprovado numa tag real, o que custa um ciclo de
release. Proposta honesta em duas camadas: (i) assert estrutural em
`test_release_workflow_asserts.py` de que o job `publish` tem
`needs: await-release-gate` e de que o `environment` continua no job de
publish; (ii) controle positivo executável sobre a **função de decisão**
do poll, alimentada com uma resposta fabricada `conclusion: failure` e com
uma resposta de erro — ambas devem sair não-zero. Declarar explicitamente
no plano que o controle end-to-end vivo **não** roda a cada release; o que
não pode acontecer é o AC afirmar prova que não existe.

### OQ-2 — Semântica de idempotência do F2: **(a)**, com o predicado corrigido.

**O que `last-reviewed:` SIGNIFICA.** O próprio driver define:
"its date+version line asserts the npm-facing copy was re-read **for this
release**" (:36-40) e `--npm-readme-reviewed` "acknowledges that
npm/README.md was actually re-read" (:315-318). A unidade é **a release**
(o trem 1.3.0), não o dia de calendário da tag. Sob essa definição, a
promoção rc.1→GA sobre a MESMA árvore é a mesma release: o stamp de 04/08
continua **verdadeiro**. Re-datar para 05/08 afirmaria uma re-leitura que
não houve — claim falsa numa superfície que o Owner assina, que é a classe
P0 declarada deste repo (o mesmo raciocínio que o r3 aplicou à anotação da
tag, :466-468). Portanto (a) é a leitura honesta, e não há tensão real com
"quem espera o stamp do dia do GA": quem espera isso está esperando uma
data de *corte*, não de *revisão* — e data de corte já existe, é a tag.

**Mas (a) como enunciada está sub-especificada e reintroduziria o bug do
r4 em espelho.** O predicado NÃO pode ser "VERSION já == alvo" (foi o fix
do r4 e é insuficiente — é exatamente o que F2 explora), nem "diff
ignorando stamps" (é (b)). O predicado correto é **"a promoção é de mesma
árvore"**:

> `bump --stable` verifica primeiro se a árvore JÁ satisfaz o alvo —
> `VERSION == TARGET_BASE` **e** `verify-counts --quiet --no-tests` limpo
> **e** `build-plugin.py --check` limpo. Se sim: **não executa o passo de
> substituição** (não escreve arquivo nenhum), imprime o no-op e retorna 0.
> Só se a árvore NÃO satisfizer é que a substituição roda — e aí `today` é
> legítimo, porque algo mudou de fato.

Duas razões concretas para preferir isso a (b):

- **(b) escreve para depois restaurar.** Uma queda entre o write e o
  restore deixa a árvore com stamps do dia — estado rasgado justamente na
  árvore que o Owner vai assinar. (a) nunca escreve.
- **(b) engole uma mudança legítima.** "Se só datas mudariam, restaure" é
  heurística sobre um diff; ela silencia o caso em que o operador
  *realmente* re-revisou e quer o stamp novo. (a) com uma escotilha
  explícita (`--restamp`) é mais honesta e mantém o tripwire vivo.

**AC-1 fecha o caso, não a classe.** Ver R-VP3: o buraco estrutural é que
`bump` roda DEPOIS do `preflight`, e a asserção mais forte do preflight
(`HEAD == origin/main`) não é re-verificada por `tag()` nem pelo
`release.yml`. Acrescentar o gate de ancestralidade em `tag()` é o item
que transforma AC-1 de "o caso D+1 virou no-op" em "a classe está fechada".

### OQ-3 — Escopo do F3: **`SPEC/v1` sim; `VERSION` da raiz não.**

Detalhado em R-VP1/R-VP2 e Must-fix 4. Respondendo diretamente às três
opções que a proposta oferece para o adopter que EDITOU seu SPEC local:

- **`SPEC/v1`: sobrescrever com backup.** É contrato publicado de
  conformidade — o adopter que o editou tem um fork do contrato, não uma
  customização. `backup_and_replace` (delete+replace com cópia em
  `.claude.bak/<timestamp>/`) é a semântica certa, e é a que install já
  implica (o SPEC não pré-existe num repo virgem). Three-way é
  complexidade sem consumidor: nada no framework faz merge de schema.
  Recusar-e-instruir transformaria toda release de SPEC num bloqueio
  manual de upgrade — custo alto, benefício nulo, porque o dano de rodar
  enforcement v1.3 contra contrato v1.2 é maior que o de perder um fork de
  schema que está em `.claude.bak/`.
- **`VERSION` da raiz: nenhuma das três.** A pergunta pressupõe que o
  arquivo é do framework; verifiquei que não é — `install_one` é
  skip-if-exists, então num adopter com `VERSION` próprio o framework
  **nunca escreveu ali**. Não há o que "sobrescrever com backup": haveria
  o que *tomar*. Marcador vai para `.claude/.framework-version`.

**Consequência para o patch de `_framework_manifest_set.sh`:** entra UMA
entrada nova (`SPEC/v1`) em `_framework_target_entries`, gated pelo mesmo
predicado de ceremony que o install usa; `.claude/.framework-version` é
escrito pelos dois lados fora do conjunto enumerado (é derivado, como os
plugin manifests, não conteúdo copiado). E entra `ADR-155-AMEND-1`
registrando por que a raiz ficou de fora — senão o próximo mantenedor
"conserta" a assimetria e reabre a classe S238.

### OQ-4 — F4 sem tautologia: e2e em fixtures, **no CI**, com controle positivo observado no CI.

**Confirmação da tautologia.** `test_install_baseline_manifest.sh` §C.2:
`entries_install="$( _framework_target_entries )"` seguido de
`entries_upgrade="$( _framework_target_entries )"` e `diff -q` — com o
comentário admitindo "derive an identical target set by construction".

**Mas set-equality NÃO teria pego F3 nem se fosse honesta.** `SPEC/v1` e
`VERSION` são entregues pelo `install.sh` por `install_one` direto
(:1307, :1322), **fora** da enumeração FMS. Comparar enumerações — mesmo
que derivadas independentemente — nunca alcançaria esses caminhos. O
oráculo TEM de ser a árvore resultante, como o plano diz em W1.3. Isso
está certo; o que falta é o resto.

**Custo/benefício e2e no CI vs local-only: CI, sem hesitação.** Três
razões: (i) local-only é exatamente a classe que este plano existe para
matar; (ii) o crítico devops do PLAN-161 já mediu — "install 30-60 s +
upgrade ≈ 2-3 min total", e `smoke-install.yml` já provisiona python3+jq;
(iii) o job já existe e já roda os oráculos de upgrade U1/U2/U3 — o
incremento é um step, não um workflow.

**Forma concreta:**
- Fixture A: `install.sh` na versão corrente → conjunto de arquivos
  framework-owned + hashes.
- Fixture B: instalação v1.2.0 (pin) → `upgrade.sh` para a corrente →
  mesmo conjunto + hashes.
- Comparar. Divergência = falha. Manter bash-3.2-safe e as convenções do
  arquivo (`mktemp -d`, `CEO_INSTALL_SKIP_SELF_SHA=1`,
  `CEO_RAG_INSTALL_PROMPT=0`, retry no `git init`) para o Owner rodar no
  macOS.
- **Controle positivo:** plantar a divergência removendo uma entrada de
  `_framework_target_entries` numa cópia da fixture e provar que o **job
  de CI** fica vermelho. Não o script local.
- **Fiação:** step novo em `smoke-install.yml` + o arquivo de teste +
  `SPEC/v1/**` em **ambas** as listas `paths:`, corrigindo de passagem a
  dessincronização já existente (R-VP7). Sem isso, o assert novo não roda
  na classe de mudança que produziu F3.
- **E cuidado com o vermelho-por-design:** ver Unseen 6 — a fixture com
  `VERSION` pré-existente só não vira falso-vermelho se F3 sair na forma
  de R-VP1.

### Regra dos 10x aplicada ao trem de release

**Esta maquinaria sobrevive a 10 releases sem outra classe de defeito que
bloqueie o hold?** Como está no plano, **não** — e dá para nomear a
próxima ocorrência com precisão:

- **Driver com nome de release.** `release-v1-2-0.sh` conduzindo 1.3.0
  produziu F6 inteiro. Corrigir as strings compra uma release; em v1.4.0 o
  codex reporta a mesma classe. Must-fix 7 elimina a classe (renomear +
  derivar de `TARGET_BASE`, apagar contagens em comentário).
- **Contagens numéricas espalhadas por docs.** F5 é a segunda ocorrência
  registrada da classe unwatched-doc, e Unseen 1 mostra que a terceira
  **já está em produção** num doc *vigiado* (`npm/README.md`). A cura
  durável não é "adicionar doc a `DOCS`", é: toda frase que carrega número
  precisa de regra que a case, e a contabilidade de liveness precisa ser
  por par `(métrica, doc)` com asserção de que cada doc vigiado contribui
  pelo menos um match para cada métrica que ele visivelmente afirma. Sem
  isso, adicionar `README.pt-BR.md` a `DOCS` é o quarto gate que roda,
  reporta matches e erra a linha certa.
- **Gates que não rodam.** F4 é a quinta instância desta família neste
  repo (as quatro anteriores estão na memória como "gate agendado vermelho
  invisível"). O que muda a trajetória não é consertar este teste: é o AC
  passar a exigir **vermelho de CI observado** como definição de gate novo,
  em vez de "o script sai não-zero". Recomendo elevar isso do PLAN-166
  para o contrato de S291 no `CLAUDE.md` §4 — mas em cerimônia separada,
  fora desta release (o §0 proíbe editar Gate-1 mid-session, e não vale
  arriscar o cache-boot no meio de um hold).

Com Must-fix 1-9, a resposta vira **sim para o trem de release** (driver
genérico, gate acoplado, ancestralidade verificada) e **sim para o upgrade
do adopter** (paridade provada contra árvores reais, no CI, com controle
positivo). A classe de contagens em doc continua a mais frágil das três,
e é a que eu vigiaria no re-pass r2.
