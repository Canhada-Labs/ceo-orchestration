---
plan: PLAN-166
round: 1
rounds_synthesized: [round-1]
agents_considered: [vp-engineering, security-engineer, devops-engineer]
decisions_revised_in_plan:
  - "§Findings — F4/F6 reclassificados como superfície LIVRE; escopo da cerimônia W1 cai para 5 arquivos + ADR"
  - "§OQ-1 — resolvida: (a′) await-job com bind conjuntivo no próprio npm-publish.yml; workflow_run e workflow_call registrados como rejeitados com evidência"
  - "§OQ-2 — resolvida: (a) no-op por mesma-árvore + skip por-site + módulo importável com --today explícito + escotilha --restamp"
  - "§OQ-3 — resolvida: SPEC/v1 sim (backup_and_replace, gated por ceremony); VERSION da raiz NÃO; marcador novo .claude/.framework-version"
  - "§OQ-4 — resolvida: e2e de árvores resultantes em CI, por modo de cerimônia, controle positivo observado no JOB"
  - "§W0 — expandida: F2 (módulo+skip+ancestralidade), F5 (6 ocorrências pt-BR + npm/README + FAQ + regra exact), F6 inteiro (rename do driver)"
  - "§W1 — rescopo: 5 canônicos + ADR-155-AMEND-1; Scope do sentinel em dois grupos"
  - "§ACs — todos reescritos (AC-1 invariante de HEAD; AC-2 bind conjuntivo por JOB; AC-3 três listas; AC-4 vermelho de CI; AC-5 por rótulo; AC-6 rename)"
  - "§Riscos — composto F1+F2, cegueira do step-15, timeout do publish, orçamento honesto 3-4 sessões"
synthesized_at: 2026-08-05T12:20:00Z
synthesized_by: CEO
---

# Consensus — PLAN-166 round 1

Vereditos: 3× ADJUST (Critic-B com VETO escopado no AC-2/W1.1 tal como
escrito; condição de levantamento textual e objetiva). Os 6 findings do
re-pass foram re-verificados independentemente pelos três críticos contra
a árvore — nenhum refutado.

## Consensus findings (2+ agents flagged)

**C1 — Nunca mover o publish para fora de `npm-publish.yml` (opção b morta). [A+B+C, CRITICAL]**
O trusted publisher do npmjs.com amarra (repo, FILENAME do workflow,
environment) — evidência in-repo `PLAN-158/oidc-failure-playbook.md:18`,
corroborada no cabeçalho do próprio workflow. (b) troca um acoplamento
verificável por uma invariante de console web invisível ao CI, além de
invalidar ~6 pins de teste e o pin exact de 29 steps (`RELEASE.md:19` ×
`verify-counts.sh`). Mitigação: F1 se resolve DENTRO de `npm-publish.yml`.
Landa em §OQ-1.

**C2 — O gate do F1 tem de ser à prova de (i) run errado e (ii) run pulado. [A+B, CRITICAL]**
(i) Com OQ-2=(a), a tag GA aponta para o MESMO commit da rc.1 — poll por
`head_sha` acha o run verde da rc.1, que curto-circuitou o hold
(`release.yml:238-241`) e validou verdito da rc.1. Bind conjuntivo
obrigatório: workflow `release.yml` + `event==push` +
`head_branch==<tag GA>` + `head_sha` + conclusão do **job**
`release-gate` `== success`. (ii) `release.yml:15` tem
`if: vars.CEO_SOTA_DISABLE != '1'` — jobs pulados não avermelham o run;
conclusão de RUN não é prova; `skipped`/`null` = bloqueio. Fail-CLOSED em
timeout/erro de API/JSON malformado (verificação de INPUT, não infra —
precedente ADR-186; concordância A R-VP8 + B must-fix 5 + C R-DEVOPS2
sobre o estado `not-yet-created` ≠ falha ≠ permissão). Landa em §OQ-1 e AC-2.

**C3 — O gate novo tem de rodar em RC. [B+C-compatível, HIGH]**
`npm-publish.yml:65` exclui `-rc.` do job inteiro; um gate ali dentro
estreia no GA (a patologia "no earlier proof point" do playbook OIDC).
Estrutura: job `await-release-gate` SEM `environment` e SEM exclusão de
RC; job `publish` mantém `environment: production-npm` e o `if` de RC
verbatim; `needs: await-release-gate`. A rc.2 vira o controle positivo
vivo. Pins de posture de RC são FORTALECIDOS, não relocados (B must-fix 4;
C R-DEVOPS5). Landa em §OQ-1/W1.

**C4 — F2: no-op por mesma-árvore, implementado no laço de substituição, testável com relógio explícito. [A+B+C, HIGH]**
(a) do OQ-2, com três camadas convergentes: predicado externo de
mesma-árvore (A: `VERSION`+`verify-counts`+`build-plugin --check` limpos →
não escreve NADA); skip por-site dos 4 stamps quando a versão na stamp já
é o alvo (C must-fix 2 — a mutação morre na função que é dona dela);
extração do heredoc para módulo importável com `--today` PARÂMETRO
obrigatório sem default (C must-fix 3 + memória frozen-evidence). (b)
rejeitada: escreve-e-restaura deixa estado rasgado se cair no meio, e
re-datar sem re-revisão é claim falsa em superfície assinada (A: a unidade
de `last-reviewed` é a RELEASE, não o dia — definição do próprio driver
:36-40). Escotilha explícita `--restamp` para re-revisão real. AC-1 prova
o invariante: `git rev-parse HEAD` idêntico antes/depois do bump D+1 (B
R-SEC3). Landa em §OQ-2/W0.

**C5 — F3 reescrito: SPEC/v1 sim; VERSION da raiz NÃO; três listas; gate de ceremony. [A+B+C, CRITICAL]**
Como escrito no plano, o fix (i) NÃO ENTREGA nada — `upgrade.sh` sourcea o
manifest-set mas a entrega real é a sequência manual de
`backup_and_replace` (B must-fix 6; C Unseen 3: `install_one "SPEC/v1"`/
`"VERSION"` vivem FORA da enumeração) — e (ii) seria DESTRUTIVO para
`VERSION`: `install_one` é skip-if-exists, `backup_and_replace` é
delete+replace; upgrade tomaria um arquivo de raiz que o install nunca
tocou (A R-VP1, classe S238/ADR-155), e o classificador de baseline
CONFIRMARIA o clobber (A R-VP2, armadilha C.5 documentada no próprio
arquivo). Direção consensual: `SPEC/v1` vira superfície de upgrade
(backup_and_replace + entrada na enumeração + lista de refresh do
INSTALL.md — as TRÊS listas), gated pela ceremony gravada em
`.install-state.json` (user → pula; fail-open se estado ausente — B
must-fix 7, A must-fix 4, espelhando `install.sh:1310/:1325`); `VERSION`
da raiz NÃO é tocado pelo upgrade; marcador do framework vai para
`.claude/.framework-version`, escrito por install E upgrade; leitores
(`ceo-boot.py:932,952`, `check-canonical-doc-freshness.py:138`) preferem o
marcador com fallback. `ADR-155-AMEND-1` registra a assimetria da raiz.
Landa em §OQ-3/W1.

**C6 — F4: o único teste que fecha é executar install e upgrade REAIS sobre fixtures e diffar as árvores, NO CI. [A+B+C, HIGH]**
Set-equality — mesmo honesta — nunca alcançaria os sites fora da
enumeração (A OQ-4; C Unseen 3: duas enumerações "independentes" do mesmo
autor compartilham o mesmo ponto cego que gerou F3). E o teste atual está
morto DUAS vezes: tautológico E não executado por workflow nenhum (A
R-VP5 — só um land-script one-shot o referencia). Forma: fixture A
(install corrente) vs fixture B (install v1.2.0 → upgrade); comparar
conjunto+hashes framework-owned; POR modo de cerimônia (maintainer e
user — B Unseen 3, senão a divergência by-design vira allowlist); controle
positivo = divergência plantada deixa o JOB de CI vermelho (não o script
local); fiação em `smoke-install.yml` + `SPEC/v1/**` + o teste em AMBAS
as listas `paths:` (corrigindo a dessincronização pré-existente, A R-VP7).
Landa em §OQ-4/W1/AC-4.

**C7 — F5 é maior que o plano e a premissa estava errada: estar em DOCS não basta. [A+B]**
`npm/README.md:60,123` e `docs/FAQ.md:109` dizem `~12,000` contra
`~13,000` do README — TRÊS sites stale HOJE em docs já vigiados; a forma
`~N,000 cases` não casa regra nenhuma, e a regra `tests` é FLOOR
(12.000≤13.000 passaria mesmo casando). No pt-BR são 6 ocorrências em 5
linhas (`:53,:54,:58,:60,:167`), incluindo prosa fora da tabela. Rótulos
idênticos EN/pt (Slash commands, ADRs) estão corretos; os que driftaram
são exatamente os que não casam matcher — gate que roda e erra a linha
certa (A Unseen 3). Fix: corrigir todos os sites; regra própria
exact-com-tolerância para `~N.000 casos`/`~N,000 cases` (ou migrar docs
para forma `N+`); matchers pt-BR por RÓTULO; controle positivo POR RÓTULO;
checar colisão de rótulos pt/EN (B nice-4). Landa em §W0/AC-5.

**C8 — F6: a raiz é o NOME do driver; e há mais ocorrências que o verdito citou. [A+C]**
`:19` repete a claim falsa de publish do `:515` (cabeçalho!); `:268` é a
quarta ocorrência de "six sites"; contagens em comentário ao lado da
lista que descrevem são superfície de drift pura (3 sites: `:290`, `:388`,
`:395` vs 11 entradas reais). Corrigir strings compra UMA release
(regra 10x). Fix: renomear `release-v1-2-0.sh` → `release.sh`, derivar
toda string de versão de `TARGET_BASE`/`VERSION`, APAGAR contagens de
comentários (não corrigi-las), atualizar `release-checklist.md:93-103`
(6 linhas, livre) e a claim de publish nas DUAS ocorrências. Landa em
§W0/AC-6.

**C9 — O composto F1+F2 é o argumento de shipping conjunto. [A+B]**
"Tag GA num commit que nunca esteve em main e nunca passou por CI"
(R-VP3: nada verifica ancestralidade — `merge-base|is-ancestor` = zero
ocorrências no driver e no release.yml) + "npm publica sem observar o
gate" = caminho único e coerente para publicar árvore não revisada. E o
commit extra do F2 é INVISÍVEL ao step 15 (B R-SEC3: nenhum dos 4
arquivos re-datados está no `pair-rail-inputs-hash-manifest.txt`).
Mitigações: gate de ancestralidade em `tag()` (~4 linhas, livre, W0);
proibição explícita de adiar F1 ou F2 para pós-GA; nota no checklist: "no
caminho feliz, tag GA e última RC apontam para o mesmo commit; divergência
= algo foi tocado durante o hold" (B Unseen 4). Landa em §Riscos/W0.

**C10 — Classificação canonical corrigida; W1 encolhe. [A, confirmado contra `_CANONICAL_GUARDS` pelo CEO]**
`scripts/tests/**` e `INSTALL.md` NÃO são canonical-guarded. W1 real:
`npm-publish.yml`, `scripts/install.sh`, `scripts/upgrade.sh`,
`scripts/_framework_manifest_set.sh`, `.github/workflows/smoke-install.yml`
+ `ADR-155-AMEND-1`. F6 move inteiro para W0. Scope do sentinel nomeia
DOIS grupos (trem de release / upgrade do adopter) para revert parcial sem
dividir a cerimônia (A What-not-change 2). Landa em §W1.

## Single-agent insights kept

1. **[C] Estados do poll `not-yet-created`/`running`/`concluded`** — os
   dois workflows disparam do mesmo push sem ordem garantida; "sem run
   ainda" não é falha nem permissão. Entra na especificação da função de
   decisão do AC-2.
2. **[C] `timeout-minutes: 8` do publish vs 20 do gate** — o await-job
   ganha timeout próprio de 35min; nota de UX no checklist para o Owner
   não confundir timeout com falha real. Entra em W1.
3. **[C] Qualquer `.yml` novo entra nas tuplas de `WorkflowHygieneTest` no
   mesmo commit** — sob (a′) não há arquivo novo, mas o teste estrutural
   novo do AC-2 entra em `test_release_workflow_asserts.py` no padrão
   WaveB5. Entra em W1/AC-2.
4. **[A] Gate de ancestralidade em `tag()`** (R-VP3) — fecha a CLASSE que
   F2 só fecha no caso. W0.
5. **[A] Rename do driver + derivação de strings** (must-fix 7) — C pesou
   o ripple e preferia comentário; A mediu o ripple (6 linhas em arquivo
   livre) e o custo de NÃO renomear (F6 recorrente por construção).
   Decisão CEO: renomear. W0.
6. **[B] Função de decisão do gate como script stdlib testável sem rede**,
   com os 6 casos plantados que TÊM de bloquear (incl. JSON malformado =
   fail-CLOSED por contrato de matcher). Entra em AC-2.
7. **[B] `npm-trusted-publisher.txt` versionado + assert estrutural**
   (nice-1) — metade das causas de E403 vira erro visível no CI. W1
   (arquivo novo em `.claude/governance/`, livre).
   **[ERRATUM r2]** "livre" está ERRADO: casa `.claude/governance/*.txt`
   em `_CANONICAL_GUARDS` (`check_canonical_edit.py:232`) — é CANONICAL e
   entrou como 6ª superfície do escopo W1 (r2 C2-1, flagrado por A+B).
8. **[B] Teste guardando o `pair-rail-inputs-hash-manifest.txt` contra
   entrada acidental de arquivos tocados pelo bump** (nice-2, fecha a
   reintrodução do R-SEC3). W0.
9. **[A] Nota no cabeçalho do `npm-publish.yml` explicando por que
   `workflow_run`/`workflow_call` foram recusados** (nice-4) — senão a
   próxima pessoa "melhora" e quebra a invariante de rollback. W1 (mesmo
   patch canonical).

## Single-agent insights rejected / deferred

1. **[C] `workflow_call` reusável (must-fix 1) — REJEITADO para ESTE trem,
   com registro.** É a arquitetura mais limpa em abstrato (needs: nativo,
   zero poll), mas: exige extrair o gate de `release.yml` (o arquivo mais
   sensível do repo, 29 steps pinados exact por `RELEASE.md:19` ×
   verify-counts — A Unseen 7), reescreve pins de teste
   (**[ERRATUM r2]**: o custo real são 3 testes de
   `WaveB5ReleaseYmlTest`, lado release.yml — a citação original a
   R-DEVOPS4/5 era imprecisa; correção do próprio C, que ACEITOU a
   rejeição no r2 após verificar o pin dos 29 steps), dobra o custo de CI
   por tag, e infla a cerimônia W1 exatamente na release que um NO-GO já
   atrasou. (a′) de
   A+B fecha o mesmo buraco tocando UM arquivo. Registrado como
   refactor candidato pós-GA no §Deferred do plano; a nota de cabeçalho
   (kept 9) documenta a decisão.
2. **[A] Deletar/derivar a lista fechada "required entries" do C.2**
   (nice-1) — DEFERIDO para o patch do F4 em W1 (mesmo arquivo, mesmo
   commit), não é item independente.
3. **[A] `check_tier_a_spec_version_drift` vacuoso** (nice-3) — FORA do
   plano; registrado como dívida na memória da sessão (classe
   vacuous-check, quinta instância).
4. **[B] ADR "break-glass" para `CEO_SOTA_DISABLE`/`CEO_PAIR_RAIL_VERDICT_OPTIONAL`
   em variáveis de repositório** (nice-3) — DEFERIDO para plano próprio;
   toca doutrina de kill-switch além do escopo release.
5. **[C] Comentário "nome é histórico" no driver em vez de rename**
   (nice-2) — REJEITADO em favor do rename (ver kept 5).

## Plan adjustments

Índice das mudanças aplicadas ao arquivo do plano nesta síntese (o texto
vive no plano):

1. §Findings — tabela reclassificada (F4/F6 livres); coluna de escopo real.
2. §OQ-1..OQ-4 — todas resolvidas com os textos de C1-C3/C4/C5/C6.
3. §W0 — itens: evidência (feito), F2 completo (módulo `--today` +
   skip por-site + predicado mesma-árvore + `--restamp` + ancestralidade
   em `tag()`), F5 completo (todos os sites + regras novas + controles
   por rótulo), F6 completo (rename + derivação + duas claims de publish +
   contagens apagadas + checklist), teste do inputs-hash-manifest (kept 8).
4. §W1 — 5 arquivos canônicos + ADR-155-AMEND-1 + asserts estruturais +
   `npm-trusted-publisher.txt` + nota de cabeçalho; Scope em dois grupos.
5. §W2 — inalterada em estrutura; nota RC→GA mesmo-commit no checklist.
6. §ACs — AC-1..AC-7 reescritos conforme C2/C4/C5/C6/C7/C8.
7. §Riscos — composto F1+F2 (C9), cegueira do step-15, timeout, orçamento
   3-4 sessões (R-VP9).

## Round verdict

**RUN-ANOTHER-ROUND.** Motivos: (i) o VETO escopado de um crítico tem
condição textual de levantamento — o AC-2 reescrito precisa ser CONFIRMADO
pelo autor do VETO, não presumido; (ii) a resolução de OQ-1 rejeita o
must-fix 1 de um crítico com argumento de blast radius — ele merece ver e
contestar a rejeição; (iii) o volume de reescrita do plano é grande o
bastante para justificar um passe de verificação dos três sobre o texto
NOVO (não sobre a intenção). Round 2 com os MESMOS críticos (continuidade
via resume; re-brief só do delta).
