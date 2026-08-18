# W3-approved — sentinel do pack canônico PLAN-169 W3 (DRAFT — assinar como W3-approved.md)

> **Como assinar (manhã, DEPOIS do GA v1.3.0):**
> 1. `cp W3-approved-draft.md W3-approved.md`
> 2. Trocar `Anchor-SHA: 996d72b811c04fed73be6f3ddbf820834d96d87d` pelo
>    `git rev-parse HEAD` REAL (o land aborta se divergir).
> 3. `export GPG_TTY=$(tty); gpgconf --kill gpg-agent` (se pinentry chiar)
> 4. `gpg --armor --detach-sign -u CFCFACF00335DC74 W3-approved.md`
>    (gera `.asc`; o land REJEITA assinatura de outra chave — r14 P1)
> 5. `bash .claude/plans/PLAN-169/OWNER-W3-LAND.sh --dry-run` → depois sem flag.

Plan: PLAN-169
Wave: W3 (pack canônico único — cerimônia GPG comum, SEM kernel)
Anchor-SHA: 996d72b811c04fed73be6f3ddbf820834d96d87d
Data: 2026-08-18

## Scope

```
scripts/upgrade.sh
scripts/_framework_manifest_set.sh
scripts/install.sh
scripts/tests/test-protocol-pointer-render.sh
scripts/tests/test-w3-vcures.sh
.github/workflows/smoke-install.yml
.github/workflows/ownership-nightly.yml
.github/workflows/release.yml
.claude/hooks/check_anti_ceo_overhead.py
.claude/hooks/check_codex_stop_review.py
.claude/hooks/audit_log.py
.claude/hooks/check_agent_spawn.py
.claude/hooks/tests/test_codex_stop_review.py
.claude/adr/ADR-163-hook-latency-gate-percentile-stability.md
.claude/adr/ADR-186-hook-deadline-policy.md
```

## Re-staging S312 (pós-GA v1.3.0 — LER ANTES DE ASSINAR)

O Scope acima é o conjunto RE-STAGED da S312 (17 receitas semânticas,
Workflow `wf_69229d1b`; BASELINE re-pinado no vivo pós-GA). Diferenças
vs o staging original de S299:
- **FORA (consumidos):** CLAUDE.md, README.md, README.pt-BR.md,
  npm/README.md, docs/{ARCHITECTURE,CTO-GUIDE,FAQ,GUIA-COMPLETO,README}.md
  e npm-publish.yml — todos os itens já chegaram ao vivo por outra rota;
  whole-file regrediria curas (SLSA Level-2, timeout 50, assert :443).
  Evidência em `staged-w3/consumed/`.
- **FORA (decisão ⚖️ pendente):** família W2.8 (ADR gate-scripts +
  manifesto + 4 steps) e ADR break-glass (W0.9) — em
  `staged-w3/pending-w28/` + `staged-w3/PENDING-DECISIONS.md`.
  Assinar este pack NÃO decide nenhum dos dois.
- **FORA (família-dependente):** RELEASE.md — único delta era "31→32
  steps" contando o step W2.8; sem a família, o vivo permanece 31.
  Em `staged-w3/pending-w28/`.
- O item 3 (W3.3/P4 advisory) e o item 4 (F4 codex default) permanecem
  como descritos abaixo — os arquivos estavam FRESH (main não moveu).

## O que este pack muda (resumo por item; staged em `staged-w3/`, MANIFEST.sha256 rastreado)

1. **W3.1 (B.a)** `upgrade.sh`: allowlist POSITIVA de charset no filtro do
   `PROTOCOL_SOURCE` (valor com newline/control char rejeita ⇒ fallback D3)
   + WARNING BARULHENTO no caller quando a chave existe e foi rejeitada.
   `_framework_manifest_set.sh`: guard de newline no gerador — valor
   irrepresentável no sed ⇒ corpo DEGRADED (alvo de cura reconhecido),
   nunca render corrompido, nunca abort. Caso R9 novo no teste de render
   (9/9), validado nos DOIS sentidos contra o staged.
2. **W3.2** `smoke-install.yml`: 2º fator do controle de paridade vira
   CAUSAL (`positive control: FIRED in every mode` + nenhum veredito
   por-modo :0/:2) — fecha a exceção nomeada do AC-4 do PLAN-166 (r6-P2).
3. **W3.3** `check_anti_ceo_overhead.py`: P4 degrada para ADVISORY nos
   tools de apply (Edit/Write/MultiEdit/NotebookEdit); Bash mantém block.
   Evidência: 4 hits legítimos bloqueados (S298 ×2, S299 ×2). R-SEC6:
   cura pelo predicado, sem sentinela persistida.
4. **W2.10-deferidos (fronteira do predicado):** F4
   `check_codex_stop_review.py` default reviewer → `claude-opus-5` +
   **teste-espelho** `tests/test_codex_stop_review.py:327` atualizado
   (a simulação G4 da S300 pegou o assert do default antigo — a classe
   "Tier-1 sem teste-espelho" em ação); F8+D1
   `audit_log.py` devops → haiku bare + docstrings de frota atualizadas;
   D2 `check_agent_spawn.py` mensagem de bloqueio passa a citar a regra
   REAL (membership em VETO_FLOOR_ALLOWED).
5. **Nightly comment** `ownership-nightly.yml`: tempo observado do run
   saudável (~41 min) no comentário; `timeout-minutes: 90` intocado.
6. **ADRs:** ADR-163 amendment (N-adequacy nos probes de teste;
   MEDIANA-on-CI re-avaliada e MANTIDA — p95 flakou no 1º run real,
   heading corrigido na r12 do rail; implementação já landou no W2.2); ADR-186 §5
   nota histórica E.17 (case-fold resolvido em `6b5dd10`); **ADR-191
   NOVO** (break-glass para kill-switches de repo — W0.9/OQ-3 aceito).
7. **Curas V1/V2/V4/V5 (S300 — as 4 exceções nomeadas do verdito
   v1.3.0-rc.2, repass-r2 parte a):** V1 `upgrade.sh`
   `_ov_obs_prior_record` recusa relpath em `_BASELINE_INVALID` (mesmo
   guard do `_baseline_lookup` — linha ambígua nunca mais autoriza
   replace forçado); V2 `upgrade.sh` NOTE do `--pin` fala a verdade
   (VERSION é snapshot do install e over-reporta até o próximo install);
   V4 `_framework_manifest_set.sh` symlink rejeitado NUNCA cai no hash
   record (novo `elif -L` + NOTE, INV-2); V5 `install.sh` (alvo NOVO no
   pack) acumula os links criados na run e exporta `FMS_LINK_PATHS`
   (conjunto vazio codificado como newline = deny-all explícito; união
   com LINK records prévios ainda válidos). **Probes:
   `scripts/tests/test-w3-vcures.sh`** — vermelho na árvore pré-pack
   (defeitos comprovados ao vivo) e 9/9 verde pós-apply (V5b da r11 incl.);
   roda no G4 da simulação.
8. **release.yml (alvo NOVO no pack):** P2 do repass-r2 parte e — o
   assert do marker vira BYTE-exato (`cmp`), como a própria mensagem de
   erro sempre prometeu; + passo W2.8 (item 9); + **timeout do
   release-gate 20→35 min** (S300: rc.1 passou com 1m23s de folga;
   attempt-1 da rc.2 estourou com stalls de runner — o corte da rc.2
   precisou de rerun; o bump LANDOU na rc.3 junto com as curas do
   re-pass GA de 10/08, este pack apenas o MANTÉM — o staged espelha o
   vivo, hunk a hunk). O npm-publish.yml staged também CARREGA o guard
   de tag-liveness da rc.3 (cura P1 do re-pass GA parte 2) — sem delta
   funcional do W3 sobre ele, apenas espelho para o land não reverter.
9. **W2.8 ratificado — rota (b)-estreita (ADR-192 NOVO):** manifesto
   canônico `.claude/governance/gate-scripts-manifest.txt` (**9 membros**
   release-críticos — os 6 do censo §3 + `validate-pair-rail-verdict.py`
   e `await_release_gate.py` (rodadas 2-3) + `ownership-expected-reds.txt` (par de dados do nightly, rodada 11) do pair-rail
   S300: decidem verdito e publish diretamente) verificado fail-closed
   ANTES de qualquer membro rodar em `release.yml`, `smoke-install.yml`,
   `ownership-nightly.yml` e `npm-publish.yml` (alvo NOVO, rodada 3 do
   rail: o await-gate é o programa que ESPERA o release gate — precisa
   ser verificado antes de rodar, não só em paralelo). Decisão do Owner por delegação explícita
   (S300: "vou seguir suas recomendações em tudo"); residuais nomeados
   no ADR-192 (validate.yml=KERNEL⇒W4-C; release.sh post-hoc;
   cópia instalada no smoke).
10. **Superfícies de contagem 190→192 ADRs (9 docs):** o pack adiciona
    2 ADRs; verify-counts (tolerance=0) e check-claude-md-claims
    gateiam claim vs disco, então os 15 sites de claim (censo por
    CLASSE, S300) entram STAGED com o número novo: CLAUDE.md, README,
    README.pt-BR, docs/{CTO-GUIDE,FAQ,GUIA-COMPLETO,ARCHITECTURE,
    README}, npm/README. + RELEASE.md: o passo W2.8 novo no release.yml
    muda release_steps 31→32 (pego pela simulação G4 — verify-counts no
    clone). Diffs auditados = SÓ as linhas de contagem (15 linhas no
    total). G4 roda verify-counts + check-claude-md-claims no clone da
    simulação — o land nunca commita claims incoerentes. Bug
    pré-existente do G4 corrigido na mesma passada: o pytest citava
    `test_check_codex_stop_review.py` (inexistente; o real é
    `test_codex_stop_review.py`) — o G4 abortaria no primeiro run real.

## Fora deste pack (não assinar achando que cobre)

- Auditoria do hit ADVISORY do P4 (r7-P2 do rail): exige ação nova
  registrada no whitelist do `audit_emit` ⇒ família de auditoria do W4.
  Até lá o hit advisory é visível no systemMessage mas NÃO auditado
  (limite honesto comentado no próprio hook).
- Ordem publish-release vs npm (r8-P1-2 do rail): o job publish-release
  do `release.yml` cria o Release logo após o release-gate, SEM esperar
  o npm-publish — comportamento PRÉ-EXISTENTE (v1.2.0 e rc.1 shiparam
  assim; GitHub Actions não tem `needs:` cross-workflow). Redesign
  (Release em draft até o npm confirmar, ou espera via gh api) =
  candidato nomeado ao trem v1.4.0; os runbooks GA carregam a mitigação
  (`gh release edit --draft`) no caminho de falha.
- W1.7 shellcheck de `scripts/tests/**` em `validate.yml` = KERNEL ⇒ W4-C.
- Passo W2.8 em `validate.yml` = KERNEL ⇒ entra na cerimônia W4-C
  (residual 1 do ADR-192).
- F1/F5/F6/F7 (decisões de tier/perfil) ⇒ W4.3; D4/D5 (team.md/SKILL.md
  Gate-2 cache-stable) ⇒ closeout de W4-C.

Assinado por: __________________ (Owner, GPG)
