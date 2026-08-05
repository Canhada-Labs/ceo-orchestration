---
plan: PLAN-166
round: 2
rounds_synthesized: [round-1, round-2]
agents_considered: [vp-engineering, security-engineer, devops-engineer]
decisions_revised_in_plan:
  - "§W1 — npm-trusted-publisher.txt reclassificado CANONICAL (6 superfícies + ADR); nota separando 'superfícies que exigem sentinel' de 'Scope: do approved.md' (enumera TODO caminho do commit)"
  - "§OQ-2 — 4º oráculo (check-canonical-doc-freshness.py) no predicado mesma-árvore; nota dos dois oráculos distintos dos 4 stamps; --restamp exige --npm-readme-reviewed"
  - "§OQ-3 — VETO#2 fechado pela Forma A: marcador em VERSION_SITES + assert ==VERSION no release.yml + entra na enumeração (precedente PROTOCOL.md generated-pointer); gates do framework continuam lendo VERSION; preferência pelo marcador é semântica de adopter; gitignore de postura; linha no INSTALL sobre pré-Wave-B = maintainer"
  - "§OQ-1/AC-2 — semântica de ponto da função de decisão (WAIT vs BLOCK); controles plantados 6→8 (conclusion:null running; no-run-dentro-do-prazo=WAIT vs no-run-no-deadline=BLOCK); AC-2 declara que rc.2 prova o poll, não a aresta needs:; assert do trusted-publisher LÊ o arquivo"
  - "AC-5 — banda declarada: kind novo 'approx' ±5% com justificativa; formas ~N,000/~N.000/~Nk"
  - "AC-6 — INSTALL.md:627 (150→210) devolvido, wave fixada em W0; grep de controle sobre superfícies VIVAS; repass-r1/** e debate/** imutáveis"
  - "§W0/W1 — autoria de TODOS os testes livres movida para W0; W1 só fiação canônica; endereços dos testes declarados (validate.yml:424 / release.yml:332 / smoke-install.yml)"
  - "§Riscos/W2 — rota de recuperação do timeout (re-run do await-job; sem delete/re-tag); nota mesmo-commit promovida a assert no tag --stable"
synthesized_at: 2026-08-05T13:45:00Z
synthesized_by: CEO
---

# Consensus — PLAN-166 round 2

Vereditos: 3× ADJUST. **VETO do round 1 (Critic-B): LEVANTADO** com
verificação literal item-por-item do AC-2 v2. **VETO novo (Critic-B),
escopado ao marcador `.claude/.framework-version`**, com condição textual
de levantamento (Forma A/B) — fechado nesta síntese pela Forma A (ver
C2-2). Critic-C **aceitou explicitamente** a rejeição do `workflow_call`
após verificar o pin dos 29 steps; Critic-A confirmou 9/9 must-fix do
round 1 fechados no texto.

## Consensus findings (2+ agents flagged)

**C2-1 — `.claude/governance/npm-trusted-publisher.txt` É CANONICAL. [A+B, HIGH]**
Casa `.claude/governance/*.txt` (`check_canonical_edit.py:232`). O
consensus r1 (kept-7) o chamou de "livre" — erro de origem propagado ao
§W1, que teria travado a cerimônia no meio (Write bloqueado sem o path no
`Scope:`) ou violado `touched−scope=∅`. Fix: 6ª superfície canônica no
§W1 + erratum no consensus r1 + nota separando os dois conceitos
(superfícies-que-exigem-sentinel ≠ `Scope:` do approved.md, que enumera
TODO caminho do commit da cerimônia — ADR, testes e o .txt incluídos).

**C2-2 — O marcador novo não pode ser autoridade de gate sem as proteções de `VERSION`. [B VETO escopado + A R2-VP2 adjacente]**
`check-canonical-doc-freshness.py` é gate do `release.yml` e lê a versão
corrente; "preferir o marcador" entregaria o gate a um arquivo sem guard,
fora do inventário e fora do verify-counts (escrever `1.0.0` nele faria
todo doc parecer fresco). Resolução (Forma A + R2-SEC3): o marcador entra
em `VERSION_SITES` (bump o escreve e verify-counts o cruza com VERSION);
`release.yml` ganha assert `marcador == VERSION` quando presente
(fail-closed); entra em `_framework_target_entries()` pelo precedente
generated-pointer do PROTOCOL.md (`:202,:226-234`); **nenhum gate do repo
do framework passa a lê-lo** — o freshness gate continua lendo `VERSION`;
a preferência marcador-com-fallback é exclusiva de leitores em árvore de
ADOPTER (onde `VERSION` pode ser do app). Condição textual da Forma A
satisfeita; levantamento formal pendente de confirmação do autor do VETO
sobre o texto aplicado.

**C2-3 — A função de decisão do AC-2 precisa de semântica de PONTO explícita. [B+C, HIGH]**
Critic-C: "nenhum run" como bloqueio imediato contradiz os 3 estados
(not-yet-created deve AGUARDAR dentro do prazo — os dois workflows
disparam do mesmo push sem ordem; reject imediato reabre a race).
Critic-B: falta o controle `conclusion: null` (job presente, run em
andamento) — a implementação `!= "failure"` passaria nos 6 controles e é
bypass. Resolução: a função retorna GRANT/WAIT/BLOCK por avaliação de
ponto; WAIT para not-yet-created e running dentro do prazo; BLOCK no
deadline (fail-CLOSED), em mismatch, em skipped/failure e em JSON
malformado. Controles plantados 6→8: (+) `conclusion:null` → WAIT;
(+) no-run-dentro-do-prazo → WAIT; no-run-no-deadline → BLOCK.

## Single-agent insights kept

1. **[A] 4º oráculo no predicado mesma-árvore** (R2-VP2): os stamps de
   SBOM/SECURITY/VERSIONING só são vigiados por
   `check-canonical-doc-freshness.py`; sem ele no predicado, o no-op
   externo IMPEDE a auto-cura in-loop de rodar (única regressão real que
   OQ-2a introduzia). + a confirmação preciosa: o freshness gate decide
   por VERSÃO da stamp, não por data — congelar a DATA é seguro.
2. **[A] AC-6 tinha REGREDIDO vs v1**: `INSTALL.md:627` (150→210,
   ADR-110-AMEND-2) sem AC e sem wave. Devolvido; wave fixada W0 (arquivo
   livre; condicional removido). Fato verificado: `upgrade.sh:1987,2002`
   migra (60,150)→210; INSTALL ainda diz 60→150.
3. **[A] AC-5 prescrevia kind inexistente**: verify-counts só tem
   exact/floor; floor não pega undersell (12.000≤13.000 passa — que É o
   drift real). Decisão: kind `approx` com banda **±5% declarada e
   justificada** (collect-count varia com ruído de coleta por diretórios
   de plano); formas `~N,000`/`~N.000`/`~Nk` (a 3ª cobre
   `docs/ARCHITECTURE.md:74`, hoje correto mas fora das formas).
4. **[A] Autoria dos testes livres em W0** (R2-VP5): e2e do F4, asserts de
   workflow, D/D+1, unidades plantadas — iterar flake de fixture com
   sentinel assinado na mão é o modo de falha S285/S286. W1 = fiação.
   + endereços declarados (R2-VP6... [sic] must-fix 6): `.claude/scripts/tests/`
   roda via `validate.yml:424`+`release.yml:332`; `scripts/tests/*.sh` só
   via `smoke-install.yml` com paths — o plano que diagnosticou "teste que
   nunca roda" endereça os próprios testes.
5. **[A] Grep de controle do AC-6 sobre superfícies VIVAS**;
   `repass-r1/**` e `debate/**` imutáveis (um sed prestativo quebraria o
   MANIFEST.sha256 da evidência).
6. **[B] Assert do trusted-publisher LÊ o arquivo** (senão o .txt é 4ª
   cópia da verdade); controle positivo: trocar environment numa cópia →
   vermelho.
7. **[B] AC-2 declara o que a rc.2 NÃO prova**: prova o poll; a aresta
   `needs:`+publish só é exercida no GA (o `if` de RC pula o publish).
8. **[B] Semântica da aprovação manual pós-gate** no checklist: é a última
   chance humana, não segunda opinião sobre o gate.
9. **[B] Marcador no gitignore de postura** (install já instala ignores —
   PLAN-165 CX-3); **linha no INSTALL**: installs sem `.install-state.json`
   (pré-Wave-B) são tratados como maintainer no upgrade.
10. **[A] Rota de recuperação do timeout** no checklist: re-rodar o
    `await-release-gate` após o gate ficar verde — pinado à árvore da tag,
    sem delete/re-tag (todo fail-closed precisa de rota).
11. **[A] Nota mesmo-commit → assert no `tag --stable`** (divergência no
    caminho feliz é sinal; sinal barato vale gate).
12. **[A] Driver INVOCA `_release_bump_sites.py`** (não duplica a tabela
    SITES — senão nasce 2ª fonte de verdade dos 11 sites).
13. **[C] Erratum de citação no consensus r1**: o custo do workflow_call
    está em 3 testes de `WaveB5ReleaseYmlTest` (lado release.yml), não em
    R-DEVOPS4/5. A rejeição permanece válida — o pin dos 29 steps foi
    verificado pelo próprio C.
14. **[B] Gate de ancestralidade: separar os dois erros** ("não falei com
    origin" ≠ "HEAD não é ancestral"), escotilha nomeada para offline,
    NUNCA `;` (fetch falho + merge-base stale = aprovação falsa).

## Single-agent insights rejected / deferred

1. **[B nice-2] Passe na família "script livre que decide gate de
   release"** — DEFERIDO (fora do escopo; anotado em §Deferred).
2. **[B nice-4] Gatilho do workflow_call deferido** ("quando release.yml
   for refatorado por outro motivo") — ACEITO como uma linha no §Deferred
   (custo zero; evita dívida sem gatilho).
3. **[A nice-2 alternativa (ii)] Migrar docs para forma N+** — REJEITADO
   em favor do kind approx (floor perde undersell, que é o drift real
   observado).

## Plan adjustments

Ver frontmatter `decisions_revised_in_plan` (8 grupos). Erratum aplicado
ao consensus r1 kept-7 (marcado `[ERRATUM r2]`, texto original
preservado).

## Round verdict

**PROCEED** — a condição única foi SATISFEITA em 2026-08-05: o autor do
VETO escopado #2 verificou o §OQ-3 v2.1 item a item e registrou
`veto_round_2: LEVANTADO` no próprio arquivo
(`round-2/security-engineer.md`, seção "Verificação Forma A
(pós-síntese)"), notando que o plano adotou Forma A E Forma B juntas —
fechando também o R2-SEC3 sem ser condição. Debate encerrado como
`design-coherent` (2 rounds, 3 críticos, 2 VETOs escopados abertos e
levantados com verificação literal). Quem autoriza ship é a cascata
V0-V3 (pair-rail codex + GPG do Owner), nunca o debate.
