# Cerimônia 2 (S292) — RUNBOOK Owner-executado

> **Forma:** runbook copy-paste (padrão `PLAN-163/CEREMONY-RUNBOOK.md`) — o
> Owner lê e cola cada bloco no terminal (rail humano). Assinatura é INLINE
> em cada fase; nenhum `.asc` pré-existente é exigido.
>
> **Estrutura: fases separáveis** (consensus S7 — um REJECT num rider não
> trava a leva). Cada fase produz UM commit assinado com sentinel próprio e
> deixa a árvore internamente consistente (contagens batem em todo commit).
>
> **Decisões que o Owner toma ANTES de colar (2):**
> 1. **NF-08** (round-3 security-review): **(a)** aplicar
>    `nf08-invocation-guard.patch` + `nf08-self-path-guard.patch` +
>    `nf08-night-mode-command-doc.patch` — implementa a ratificação
>    OQ1-redo (recomendado) — ou **(b)** não aplicar e reescrever os 3
>    comentários assinados + re-ratificar OQ1-redo. Os blocos abaixo
>    assumem **(a)**; para (b), pule os 3 `git apply` do NF-08 na Fase A.
>
>    ⚠ **O que (a) entrega, dito com precisão** (o pair-rail achou bypass
>    no matcher em QUATRO rounds seguidos — r2 env/sudo, r4 brace, r5
>    xcrun, r6 assignments compostos; cada fix foi real e cada rodada
>    seguinte achou outro): parsing estático de shell **não** produz um
>    matcher completo — o shell é reescrevível demais (renomear o
>    interpretador já derrota qualquer lista, e isso está MEDIDO no
>    `nf08-invocation-guard-NOTES.md` §7 residual 5). Por isso a camada
>    que efetivamente fecha a fronteira é o **`nf08-self-path-guard`**: o
>    próprio `night-mode.py` recusa rodar quando seu `__file__` resolvido
>    não é o caminho canônico — independe de o matcher ter visto o
>    comando. O matcher é defesa-em-profundidade + mensagem pedagógica
>    ("use `!` ou o terminal"), não a fronteira.
>    **Consequência para o texto assinado:** os 3 comentários devem dizer
>    o que o par realmente faz — "a escrita do writer e do estado está
>    fechada nos dois rails; a INVOCAÇÃO é barrada pelo self-path guard do
>    script e, no melhor esforço, pelo matcher" — e **não** "o rail do
>    modelo não consegue invocar". O residual composto do r6 fica
>    ACEITO E REGISTRADO, não silenciado: novas rodadas de matcher têm
>    retorno decrescente enquanto a camada que decide é a do script.
> 2. **Sonda 210s** (Fase 0): GO ⇒ Fase C completa (AMEND-2 landa, contagem
>    187). NO-GO ⇒ Fase C′ (só AMEND-1, contagem 186; AMEND-2 NÃO landa
>    como está — §6 da emenda).
> 3. 🔴 **CONFLITO DE CONTRATO — BLOQUEIA A FASE B, exige ADR do Owner.**
>    **O draft do ADR já está pronto**: `ADR-186-hook-deadline-policy-DRAFT.md`
>    neste mesmo diretório, com as duas leituras, o custo de cada uma e a
>    lista do que entra no MESMO commit em cada caso. Basta escolher no §4,
>    preencher a justificativa e copiá-lo para `.claude/adr/` na Fase B
>    (o que muda a contagem-alvo de ADRs — ver `counts-and-lifecycle.md`).
>    O deadline que o `plan162-w2-fixes.patch` introduz é **fail-CLOSED**
>    (bloqueia o edit quando o budget de 4s estoura). Isso é o consensus C2
>    do debate do PLAN-162 (+ F-01-07) — e **contradiz** o contrato escrito
>    em `CLAUDE.md` §4 / `AGENTS.md` §1: *"hooks never block the user
>    session on INFRASTRUCTURE bugs — on a missing file, import failure, or
>    **timeout**, a hook logs a breadcrumb and emits `{}` (allow)"*; só
>    falha de PARSE de input em matcher de segurança é fail-closed.
>    O pair-rail apontou isso de forma INDEPENDENTE (round 3, P1
>    "Keep infrastructure timeouts fail-open"), confirmando o conflito que
>    a S291 já registrara como não resolvido (o teste correspondente está
>    SKIPADO de propósito, não xfail — xfail ficaria verde sob as DUAS
>    implementações).
>    **As duas leituras são defensáveis e a escolha é doutrinária:**
>    - **(i) manter fail-CLOSED** (como o patch está): um gate que não
>      consegue decidir dentro do budget não deve deixar passar um edit
>      canônico; o timeout aqui não é "infra quebrada", é *sinal de que a
>      verificação não terminou*. Custo: um `gpg-agent` lento vira bloqueio
>      do Owner — precisa da rota de recuperação documentada (unlock).
>    - **(ii) mudar para fail-OPEN + breadcrumb** (como o contrato escrito
>      manda): coerente com o resto dos hooks; custo: reintroduz a janela
>      que o C2 quis fechar, e o breadcrumb vira o único registro.
>    **Nenhuma das duas pode landar sem ADR** — a escolha muda um contrato
>    publicado. Se o Owner não quiser decidir agora: **pule a Fase B**
>    (as fases são separáveis por construção) e mantenha o resto da leva.

> **LEIA ANTES: `OPEN-FINDINGS.md`** — os achados do pair-rail que NÃO
> foram fechados (com o motivo de cada um) e o critério de parada usado
> após 8 rounds. Nenhum impede a cerimônia; um deles (a política de
> deadline) é decisão sua e bloqueia só a Fase B.

Pré-condições: main == `9c63750` (ou descendente que NÃO toque
`.claude/scripts/ceo-boot.py` nem `.claude/plans/PLAN-163-substrate-uplift.md`
— senão RE-ENSAIAR via `plan165-merge-resolved/MERGE-RECIPE.md`); árvore
limpa; `plan-165-draft` tip = `fa67642`; chave GPG `CFCFACF00335DC74`.

**Convenção de assinatura por fase.** Cole `set -euo pipefail` UMA vez por
shell antes de qualquer bloco (Codex r3 P1: sem errexit, um gate vermelho
seguiria direto para o commit assinado).

⚠ **Path e formato do sentinel são load-bearing** (Codex r3 P1 — a versão
anterior deste runbook gerava sentinels que `_find_sentinels()` NUNCA
descobre). O guard só varre os globs de `check_canonical_edit.py:850-861`;
o formato abaixo é o do sentinel que autorizou `610d9ec` em S291
(`Anchor-sha:` / `Scope:` + bullets `- <path>` / `Signed-by:`).

Cada fase usa seu próprio `round-N` sob `architect/` do plano dono:
fase A → `PLAN-165/architect/round-4`; fases B/C/D → `PLAN-162/architect/
round-1|round-2|round-3`.

```bash
set -euo pipefail          # UMA vez por shell — sem isto o gate não bloqueia

sign_phase() {             # sign_phase <plan-dir> <round-dir> <título>
  local DIR=".claude/plans/$1/architect/$2"
  mkdir -p "$DIR"
  {
    echo "# $3 — Owner sentinel (cerimônia 2, S292)"; echo
    echo "Anchor-sha: $(git rev-parse HEAD)"
    echo "Ceremony: S292 ceremony 2"; echo
    echo "Scope:"
    git diff --cached --name-only | sort | sed 's|^|- |'
    echo "- $DIR/approved.md"
    echo "- $DIR/approved.md.asc"; echo
    echo "Rationale: ver CEREMONY-2-RUNBOOK.md + os NOTES de cada patch."; echo
    # Approved-By é GATE OBRIGATÓRIO, verificado ANTES do GPG
    # (check_canonical_edit.py:995 — `if not _APPROVED_BY_RE.search(text)`
    # → return False). Shape exigido: `Approved-By: @handle <token>`.
    # Codex r4 P1: a versão anterior emitia só `Signed-by:` e o sentinel
    # seria rejeitado antes de a assinatura sequer ser lida.
    echo "Approved-By: @Canhada-Labs (Owner GPG — signed inline by the ceremony)"
    echo "Signed-by: Owner"
  } > "$DIR/approved.md"
  export GPG_TTY=$(tty)
  gpg --local-user CFCFACF00335DC74 --armor --detach-sign \
      --output "$DIR/approved.md.asc" "$DIR/approved.md"
  gpg --verify "$DIR/approved.md.asc" "$DIR/approved.md"
  git add "$DIR/approved.md" "$DIR/approved.md.asc"
  # scope-check BLOQUEANTE (touched − scope = ∅). Ambos os lados ORDENADOS
  # (comm exige) e o resultado FALHA o shell se houver sobra (Codex r3 P2).
  local extra
  extra=$(comm -23 \
    <(git diff --cached --name-only | sort) \
    <(sed -n '/^Scope:/,/^$/p' "$DIR/approved.md" | sed -n 's/^- //p' | sort))
  if [ -n "$extra" ]; then
    printf 'FORA-DO-SCOPE:\n%s\n' "$extra" >&2
    return 1
  fi
  echo "sentinel OK: $DIR (escopo fechado)"
}
```

---

## Fase 0 — preflight + SONDA (read-only; nada commitado)

```bash
cd "$(git rev-parse --show-toplevel)"   # sem path pessoal: o repo é público
STAGE=.claude/plans/PLAN-162/ceremony-2-staged
set -euo pipefail   # Codex r3 P1: sem isto um gate vermelho segue p/ o commit
test -z "$(git status --porcelain)" || { echo "ABORTAR: árvore suja"; exit 1; }
git fetch origin && test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" || { echo "ABORTAR: main != origin"; exit 1; }
git diff --quiet 9c63750..HEAD -- .claude/scripts/ceo-boot.py .claude/plans/PLAN-163-substrate-uplift.md || { echo "ABORTAR: re-ensaiar merge (MERGE-RECIPE.md)"; exit 1; }
( cd "$STAGE" && shasum -c MANIFEST.sha256 ) || { echo "ABORTAR: staging adulterado"; exit 1; }
for p in plan162-w2-fixes deny-write-twins amend2-pair-rail workflows-fixes nf08-invocation-guard; do
  git apply --check "$STAGE/$p.patch" && echo "OK  $p" || echo "FAIL $p"
done
gpg --list-secret-keys CFCFACF00335DC74 >/dev/null && echo "OK  gpg"

# SONDA 210s (§6 ADR-110-AMEND-2 — BLOQUEANTE p/ Fase C; ~4min):
bash "$STAGE/probe-hook-timeout-210s.sh"
# GO/NO-GO conforme probe-hook-timeout-README.md. Registre o resultado.
```

## Fase A — PLAN-165 W1-land `[SENT-S292-A]`

Merge ensaiado (276 testes verdes no ensaio) + fixes obrigatórios da
re-review round-3 no MESMO commit (NF-07 emit + NF-09) + NF-08 opção (a).

```bash
# Codex r6 P1: o tip do branch é PARTE do que foi revisado. Se ele avançou
# desde o ensaio, mudanças extras que fazem merge limpo NÃO alteram o
# conjunto de conflitos ensaiado — passariam despercebidas e seriam
# assinadas pelo Owner. Verifique ANTES de mesclar.
test "$(git rev-parse plan-165-draft)" = "$(git rev-parse fa67642)" \
  || { echo "ABORTAR: plan-165-draft != fa67642 (tip revisado). RE-ENSAIAR."; exit 1; }
git merge --no-ff --no-commit plan-165-draft || true
# Codex S292 r2 P2: o conjunto de conflitos DEVE ser exatamente o ensaiado —
# `|| true` acima engole qualquer surpresa, e o `git add -A` adiante marcaria
# marcadores de conflito como resolvidos. Aborte se divergir.
REHEARSED=".claude/plans/PLAN-163-substrate-uplift.md
.claude/plans/PLAN-165-night-mode-owner-autonomy-toggle.md
.claude/plans/PLAN-165/ceremony-staged/MANIFEST.sha256
.claude/plans/PLAN-165/ceremony-staged/README.md
.claude/plans/PLAN-165/ceremony-staged/p1-deny-overlay.patch
.claude/plans/PLAN-165/probes/W0-EVIDENCE.md
.claude/scripts/ceo-boot.py"
if [ "$(git diff --name-only --diff-filter=U | sort)" != "$(printf '%s' "$REHEARSED" | sort)" ]; then
  echo "ABORTAR: conjunto de conflitos != ensaiado. Diferença:"
  diff <(git diff --name-only --diff-filter=U | sort) <(printf '%s\n' "$REHEARSED" | sort)
  echo "-> git merge --abort e RE-ENSAIAR (MERGE-RECIPE.md)"
  exit 1
fi
git checkout --ours .claude/plans/PLAN-165-night-mode-owner-autonomy-toggle.md \
                    .claude/plans/PLAN-165/probes/W0-EVIDENCE.md
git checkout --theirs .claude/plans/PLAN-165/ceremony-staged/MANIFEST.sha256 \
                      .claude/plans/PLAN-165/ceremony-staged/README.md \
                      .claude/plans/PLAN-165/ceremony-staged/p1-deny-overlay.patch
cp "$STAGE/plan165-merge-resolved/ceo-boot.py.resolved" .claude/scripts/ceo-boot.py
cp "$STAGE/plan165-merge-resolved/PLAN-163-substrate-uplift.md.resolved" .claude/plans/PLAN-163-substrate-uplift.md
( cd "$STAGE/plan165-merge-resolved" && shasum -c RESOLVED.sha256 )
git add -A
git apply --index "$STAGE/w1-land-fixes.patch"
# NF-08 opção (a) — pule estas 3 linhas se o Owner escolheu (b).
# ORDEM LOAD-BEARING: o self-path-guard toca night-mode.py + test_night_mode.py,
# que o w1-land-fixes acima também edita — aplicar antes CONFLITA (nf08 NOTES §4).
git apply --index "$STAGE/nf08-self-path-guard.patch"      # NF-08b (defesa no script)
git apply --index "$STAGE/nf08-invocation-guard.patch"     # NF-08a (matcher canonical)
git apply --index "$STAGE/nf08-night-mode-command-doc.patch"

# gates da fase (árvore consistente: docs 185 == disco 185 pós-merge):
python3 -m pytest .claude/scripts/tests/test_night_mode.py \
  .claude/scripts/tests/test_reality_ledger.py \
  .claude/scripts/tests/test_check_audit_registry_coverage.py -q
# Codex S292 r2 P2: o -k "bash_safety" NÃO casa o arquivo novo do NF-08
# (test_bash_posture_toggle_invocation.py) — cite-o explicitamente, senão a
# fase A commita sem rodar os testes que validam o patch que ela acabou de
# aplicar. Só com NF-08(a):
# Só existe sob a opção (a) — sob (b) o arquivo não é criado e o `set -e`
# abortaria a Fase A num erro de arquivo ausente (codex r7 P2).
test -f .claude/hooks/tests/test_bash_posture_toggle_invocation.py \
  && python3 -m pytest .claude/hooks/tests/test_bash_posture_toggle_invocation.py -q
python3 -m pytest .claude/hooks/tests/ -k "bash_safety" -q
bash .claude/scripts/local/verify-counts.sh
python3 scripts/build-plugin.py --check || python3 scripts/build-plugin.py --write-manifests
git add -A
sign_phase PLAN-165 round-4 "PLAN-165 W1-land + NF-07/NF-09/NF-08"
git commit -S -m "governance(PLAN-165): W1-land — night-mode merge + NF-07 emit + NF-09 + NF-08(a) invocation guard [SENT-S292-A]"
```

## Fase B — PLAN-162 W2 + deny-twins `[SENT-S292-B]` (SEM ADRs, SEM counts)

🔴 **NÃO COLE ESTE BLOCO ANTES DE RESOLVER A DECISÃO #3 DO CABEÇALHO.**
O `plan162-w2-fixes.patch` implementa o deadline **fail-CLOSED**, que
contradiz o contrato escrito (`CLAUDE.md` §4 / `AGENTS.md` §1: timeout de
hook é falha de INFRAESTRUTURA ⇒ breadcrumb + `{}` allow). O pair-rail
apontou isso em DOIS rounds independentes (r3 e r5). Ratifique por ADR —
mantendo fail-closed **ou** convertendo para fail-open — antes de assinar.
Sem essa ratificação, **pule a Fase B**: as fases são separáveis e o resto
da leva não depende dela (mas veja o acoplamento do ADR-164-AMEND-1 na
Fase C).

```bash
git apply --index "$STAGE/plan162-w2-fixes.patch"
git apply --index "$STAGE/deny-write-twins.patch"
python3 -m pytest .claude/hooks/tests/test_canonical_edit_plan162_findings.py -q   # esperado: 42 passed, 1 skipped
python3 -m pytest .claude/hooks/tests/ -n auto -m 'not serial' -q
bash .claude/scripts/local/verify-counts.sh      # passa: nenhum ADR novo nesta fase
python3 .claude/scripts/check-claude-md-claims.py
git add -A
sign_phase PLAN-162 round-1 "PLAN-162 W2 fixes + deny Write-twins"
# check_canonical_edit.py + check_arbitration_kernel.py são KERNEL:
CEO_KERNEL_OVERRIDE="PLAN-162-W2-FIXES" CEO_KERNEL_OVERRIDE_ACK="I-ACCEPT" \
git commit -S -m "governance(PLAN-162): W2 — S1 case-fold P0 (ambos os rails) + cache partition + wall deadline fail-closed + deny Write-twins removed [SENT-S292-B]"
```

## Fase C (sonda GO) — AMBOS os AMENDs + pair-rail 180/210 `[SENT-S292-C]`

⚠ **ACOPLAMENTO (Codex r4 P1):** o `ADR-164-AMEND-1` DOCUMENTA o fix que a
**Fase B** implementa (partição de cache + wall deadline). Se a Fase B for
pulada — o que a decisão #3 permite explicitamente — este ADR descreveria
como ACCEPTED uma decisão sem implementação no HEAD. **Regra:** o
`ADR-164-AMEND-1` só entra nesta fase **se a Fase B tiver landado**; caso
contrário, deixe-o no staging e a contagem de ADRs vai a **186** (só o
AMEND-2), não 187 — `apply-counts.sh` pina 187 e vai RECUSAR pelo guard
fail-closed, que é o comportamento correto: ajuste os sites pela tabela de
`counts-and-lifecycle.md` com alvo 186.

```bash
# patch de código do AMEND-2 (check_pair_rail + settings 210 + timeout_ms):
git apply --index "$STAGE/amend2-pair-rail.patch"
# ADRs (normalizando o tag de autorização dos drafts p/ o tag REAL):
sed 's/\[SENT-S291\]/[SENT-S292-C]/' "$STAGE/ADR-110-AMEND-2-rail-timeout-recalibration.md" \
  > .claude/adr/ADR-110-AMEND-2-rail-timeout-recalibration.md
# SOMENTE se a Fase B landou (ver acoplamento acima):
sed 's/\[SENT-S291\]/[SENT-S292-C]/' "$STAGE/ADR-164-AMEND-1-draft.md" \
  | sed '/^<!-- Ceremony copy target/d' \
  > .claude/adr/ADR-164-AMEND-1-cache-partition-and-wall-deadline.md
install -m 0755 "$STAGE/pair-rail-latency.py" .claude/scripts/local/pair-rail-latency.py
# O glob do AMEND-1 só casa se a Fase B landou; sem ela o `git add` do
# literal aborta em bash E em zsh (codex r7 P2). Adicione o que existe:
git add .claude/adr/ADR-110-AMEND-2-*.md .claude/scripts/local/pair-rail-latency.py
ls .claude/adr/ADR-164-AMEND-1-*.md >/dev/null 2>&1 \
  && git add .claude/adr/ADR-164-AMEND-1-*.md \
  || echo "(Fase B pulada: AMEND-1 não entra; alvo de contagem = 186)"
# contagens 185 -> 187 (guard fail-closed exige os 2 AMENDs já no disco):
bash "$STAGE/apply-counts.sh"
python3 -m pytest .claude/hooks/tests/ -k "pair_rail" -q     # esperado: 231 passed, 1 skipped
python3 -m pytest .claude/hooks/tests/test_audit_emit_ghost_action_guard.py \
  .claude/hooks/tests/test_audit_emit_coverage.py \
  .claude/hooks/tests/test_audit_emit_callsite_coverage_matrix.py -q
bash .claude/scripts/local/verify-counts.sh
git add -A
sign_phase PLAN-162 round-2 "ADR-110-AMEND-2 + ADR-164-AMEND-1 + pair-rail 180/210"
CEO_KERNEL_OVERRIDE="ADR-110-AMEND-2-RECALIBRATION" CEO_KERNEL_OVERRIDE_ACK="I-ACCEPT" \
git commit -S -m "governance(ADR-110-AMEND-2 + ADR-164-AMEND-1): pair-rail 120/150->180/210 + timeout_ms + censoring-rate trigger; ADR count 187 [SENT-S292-C]"
```

## Fase C′ (sonda NO-GO) — só ADR-164-AMEND-1, contagem 186

`apply-counts.sh` pina 187 e vai RECUSAR (guard) — correto. Bump manual
pelos sites da tabela de `counts-and-lifecycle.md` com alvo **186**, e
controle `verify-counts.sh` no fim. AMEND-2 + `amend2-pair-rail.patch` +
`pair-rail-latency.py` **não landam**; abrir item p/ nova sonda/emenda.

## Fase D — workflows agendados `[SENT-S292-D]` (kernel-hard-deny)

```bash
git apply --index "$STAGE/workflows-fixes.patch"
git add -A
sign_phase PLAN-162 round-3 "workflows agendados (tournament/reality-ledger/mutation-gate)"
CEO_KERNEL_OVERRIDE="S292-SCHEDULED-WORKFLOWS-FIX" CEO_KERNEL_OVERRIDE_ACK="I-ACCEPT" \
git commit -S -m "fix(ci): tournament stderr-unmerge + reality-ledger labels idempotentes + mutation-gate junitxml/redact-inline/SHA-repin [SENT-S292-D]"
```

## Fase E — lifecycle + gates finais + push (sem sentinel)

Lifecycle (plan files não-canonical; receita completa em
`counts-and-lifecycle.md`): PLAN-165 `reviewed→executing` num commit; probes
**AC-7/AC-8 INTERATIVAS** (AC-8 exige camada user neutralizada + controle
que falha — ver round-3 §ac8-probe-spec; `claude -p` NÃO serve); depois
`done` + `completed_at` + `related_commits` (merge-sha + `610d9ec` +
`9f53628`). PLAN-162 `reviewed→executing` (fica até W2 verificado em CI).
`reviewed→done` direto é ILEGAL.

```bash
bash .claude/scripts/local/verify-counts.sh
python3 scripts/build-plugin.py --check
python3 .claude/scripts/check-claude-md-claims.py
python3 -m pytest .claude/hooks/tests/ -n auto -m 'not serial' -q
python3 -m pytest .claude/hooks/tests/ -m 'serial' -q
python3 -m pytest .claude/scripts/tests/ .claude/scripts/optimizer/tests/ -n auto -m 'not serial' -q
git push origin main
# pós-push: workflow_dispatch nos 3 workflows consertados (validação sem
# esperar o cron): gh workflow run tournament.yml / reality-ledger.yml /
# mutation-gate.yml ; e zerar audit-log.errors via `!` (91 linhas, 3
# classes benignas — triagem no diagnóstico S292).
```

## Pós-cerimônia

- **Recuperação por unlock (contrato ATUALIZADO pela fase B — Codex r3 P2):**
  desde o fold P1-3 do round 2, dentro de um worktree git o par
  `CEO_SENTINEL_UNLOCK` + `_ACK` sozinho NÃO basta: é preciso também a
  PROVENIÊNCIA (`CEO_SESSION_ANCHOR_SHA` ou `CEO_SENTINEL_UNLOCK_SHA256`),
  e a decisão passa a ser tomada sobre os BYTES ANCORADOS do sentinel, não
  sobre os bytes em disco. Consulte `plan162-w2-NOTES.md` §"Codex r2 fold"
  para os valores exatos e a mensagem de erro que ensina o valor a fornecer.
- Recomputar `inputs_hash` do pair-rail p/ o PRÓXIMO verdito
  (`audit_emit.py` mudou — amend2 NOTES §"Pair-rail inputs_hash").
- Worktree `.claude/worktrees/plan165` removível pós-merge.
- AC-10 residual: round-3 = NEEDS_CHANGES com NF-07/NF-09 aplicados na
  Fase A e NF-08 decidido — anexar nota de fechamento no plan file citando
  o artefato `architect/round-3/security-review.md`.
- Wording §6 (nf08 NOTES): os 3 comentários assinados devem dizer o que o
  controle FAZ (real, não absoluto), não "cannot" — ajustar na primeira
  cerimônia que tocar esses arquivos (ou nesta, se (a) aplicado: já coberto
  pelo texto do matcher).
