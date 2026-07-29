# PLAN-163 — CEREMONY RUNBOOK (Owner-run, duas cerimônias declaradas)

> Ordem OBRIGATÓRIA (plan §Gates, codex F5/grok F3 + correção S283):
> **GATE-PIN → closeout(181)+push → GATE-V2 (prova FRESCA pós-âncora) →
> review 3-vendor do pack (APPROVE) → cerimônia do main-pack →
> closeout(tripla)+push.**
> A expiração natural da janela 168h (~2026-08-03) **NÃO** satisfaz o
> GATE-V2 — só um PASS sobre eventos posteriores ao commit do pin.

Scripts (não-canônicos, neste diretório):

| Script | Cerimônia | Escopo |
|---|---|---|
| `land-plan163-pin.sh` | GATE-PIN (T5.2 / ADR-182) | `staged/pin-pack/` — 20 arquivos (18 + os 2 testes migrados matrix/golden, PLAN-163 FXα) |
| `land-plan163-pack.sh` | main-pack (T1/T2/T3/T5/T6) | `staged/main-pack/` — 43 arquivos |

Sentinels (assinados INLINE pelos scripts — nunca exigem `.asc` pré-existente):
`architect/round-1-pin/approved.body.md` e `architect/round-2-pack/approved.body.md`
(Scope de cada um = set-equality NOME-a-nome com o MANIFEST respectivo,
verificado no preflight).

## Pré-requisitos (uma vez, antes de tudo)

1. **GPG**: chave `AE9B236FDAF0462874060C6BCFCFACF00335DC74` no keyring;
   presente nos DOIS rails de signer (`.claude/sentinel-signers.txt` +
   `.claude/security/sentinel-signers-registry.yaml`) — o preflight verifica.
   Se pinentry falhar: `export GPG_TTY=$(tty); gpgconf --kill gpg-agent`.
2. **Credencial codex**: `OPENAI_API_KEY` no ambiente (Gate 1 do
   pair-rail-gate) e rotação <90d em `docs/rotation-log.md` (Gate 2).
3. **codex CLI instalado** — a cerimônia do pin atesta o binário REAL
   instalado agora (payload nativo, não o launcher).
4. **Manifests-gêmeos rastreados** (staged/ é gitignored — lição S274): na
   primeira rodada o preflight cria `inputs-pin.sha256` /
   `inputs-pack.sha256` a partir dos MANIFEST.sha256 consolidados;
   commitá-los ANTES da rodada real:
   ```
   ! git add .claude/plans/PLAN-163/inputs-pin.sha256 .claude/plans/PLAN-163/inputs-pack.sha256
   ! git commit -m "docs(PLAN-163): tracked input manifests (tamper-evidence)"
   ! git push origin main
   ```
5. `main == origin/main` e Validate VERDE no HEAD (o preflight verifica;
   soften para WARN só em `--dry-run`).

## Passo 1 — GATE-PIN (cerimônia do pin codex)

```
! bash .claude/plans/PLAN-163/land-plan163-pin.sh --preflight-only
! bash .claude/plans/PLAN-163/land-plan163-pin.sh --dry-run
! bash .claude/plans/PLAN-163/land-plan163-pin.sh
```

O que a rodada real faz: assina o sentinel (âncora = HEAD pré-cerimônia),
aplica os 20 arquivos, roda os oráculos pós-apply (pytest do pin +
`--verify-codex-pin` contra o binário instalado + ADR count 181), commit
assinado `[SENT-PLAN163-PIN]` e grava `GATE-PIN-ANCHOR` (sha+ts) — o ts
desse commit é a âncora do GATE-V2.

**Closeout do pin (ANTES do push — claims tolerance=0):**
1. Atualizar CLAUDE.md: ADRs 180→181 (+ sweep dos docs não-vigiados:
   ARCHITECTURE/GUIA-COMPLETO/FAQ/npm-README).
2. `! python3 .claude/scripts/check-claude-md-claims.py` → PASS.
3. `! bash .claude/scripts/local/verify-counts.sh --no-tests --quiet` → PASS.
4. Commit de closeout + `! git push origin main` + Validate verde.

**Rollback do Passo 1:**
- Antes do push: `git reset --hard <sha pré-cerimônia impresso pelo script>`.
- Depois do push: `git revert <sha [SENT-PLAN163-PIN]>` (+ revert do
  closeout) e re-rodar a cerimônia após corrigir a causa. O revert
  também invalida a âncora — o GATE-V2 recomeça na próxima cerimônia.

## Passo 2 — GATE-V2 (prova fresca de liveness sob o pin NOVO)

O RED residual atual (11 invocações case-F fail-open, janela 168h, expira
~2026-08-03) é PRÉ-âncora por construção — ele NÃO bloqueia nem satisfaz
o gate; o row 168h do ceo-boot pode continuar vermelho até 08-03 sem que
isso signifique nada para o GATE-V2.

1. Gerar UMA invocação fresca do pair-rail sob o pin novo (padrão
   zero-risco S281): abrir uma NOVA sessão Claude Code neste repo e pedir
   um edit canônico trivial de bytes IDÊNTICOS (ex.: reescrever
   `.claude/hooks/check_pair_rail.py` com o conteúdo exato atual via
   Write). Isso percorre o caminho PreToolUse REAL como o harness roda
   (sem env manual), emitindo `pair_rail_review_expected` +
   `pair_rail_case`.
2. Avaliar o verdito (re-rodável quantas vezes quiser):
   ```
   ! bash .claude/plans/PLAN-163/land-plan163-pin.sh --gate-v2
   ```
   PASS exige, SOBRE O CONJUNTO PÓS-ÂNCORA: `expected>=1 ∧ healthy>=1 ∧
   failopen==0 ∧ unclassified==0 ∧ deficit==0`. O script também roda o
   classificador oficial (`ceo-boot --json` com
   `CEO_FAILOPEN_LIVENESS_WINDOW_H` = horas-desde-âncora) como
   confirmação ADVISORY (clamp mínimo 1h: se a cerimônia tem <1h, o row
   pode incluir eventos pré-âncora — o verdito exato é o do passo 2 do
   script).
3. Registrar o output do PASS no plano (evidência do gate).

**Se FAIL:** ou ainda não houve invocação fresca (repita o item 1), ou a
invocação fresca fail-openou (`failopen>0` pós-âncora) — nesse caso o pin
NÃO está saudável: investigar `pair_rail_case` novo no audit-log antes de
qualquer cerimônia do pack. NÃO prossiga com FAIL.

## Passo 3 — Review 3-vendor do main-pack

Fora destes scripts (instrumento `/council` / codex / grok já em uso na
sessão). Pré-condição do Passo 4: APPROVE registrado em
`.claude/plans/PLAN-163/review/`. Se o review mudar QUALQUER byte staged,
recomputar `staged/main-pack/MANIFEST.sha256`, refazer o gêmeo
`inputs-pack.sha256` (+commit) e re-rodar o preflight.

## Passo 4 — Cerimônia do main-pack

```
! bash .claude/plans/PLAN-163/land-plan163-pack.sh --preflight-only
! bash .claude/plans/PLAN-163/land-plan163-pack.sh --dry-run
! bash .claude/plans/PLAN-163/land-plan163-pack.sh --confirm-gate-pin-done --confirm-gate-v2-fresh
```

O que a rodada real faz, em ordem:
1. Gate de entrada: exige as DUAS flags + commit `[SENT-PLAN163-PIN]` no log.
2. Oráculos W2 na árvore viva; depois commita os fixes W2 não-canônicos em
   commit PRÓPRIO `fix(PLAN-163): W2 ...` (fora do escopo do sentinel).
   Nota: `smoke-install-parity.sh` aparece no W2 E no pack — o commit W2
   registra o estado intermediário; a cerimônia aplica os bytes staged
   revisados por cima (ambos test-gated).
3. Preflight completo no overlay (43 arquivos aplicados): pytest do pack,
   regen-check dos DOIS espelhos do ADR-149, mirror test, oracle
   hook-stdout-schema, fixtures de migração do upgrade 2× (idempotência),
   contagens mecânicas (57/46/48/183) e claims/verify-counts como
   EXPECTED-DRIFT (CLAUDE.md só muda no closeout).
4. Sentinel assinado inline; apply sob
   `CEO_KERNEL_OVERRIDE=PLAN-163-T3-EVENT-ACTIONS` (kernel:
   settings.json, validate.yml, audit_emit.py; SPEC via cp sob sentinel);
   suíte pós-apply; `touched ⊆ scope`; commit assinado
   `[SENT-PLAN163-PACK]`.

**Closeout do pack (ANTES do push):**
1. CLAUDE.md tripla: hooks 55→57, wired 44→46, registrations 46→48;
   ADRs →183. `team.md:578/:589` (drift de modelo, arquivo cache-stable).
2. Regenerar COMMAND-SKILL-HOOK-MAP (gen---write) + sweep dos docs
   não-vigiados.
3. claims + verify-counts PASS → commit closeout → `! git push origin main`
   → `gh run watch` no Validate.
4. Lifecycle: PLAN-163 permanece `executing` até as provas L; depois
   `executing → done` com `completed_at` + `related_commits`
   (NUNCA `reviewed → done`).

**Rollback do Passo 4:**
- Antes do push: `git reset --hard <sha pré-cerimônia impresso>` — o
  commit W2 é independente e PODE ficar.
- Depois do push: `git revert <sha [SENT-PLAN163-PACK]>` (+ closeout);
  atenção: o revert de settings.json remove as registrations novas —
  sessões abertas precisam reiniciar para desligar os hooks novos.

## Aborts conhecidos (o que fazer)

| Abort | Causa | Ação |
|---|---|---|
| `manifest twin must be git-tracked AND committed` | gêmeo criado agora | commit do gêmeo (Pré-req 4) e re-rodar |
| `staged bytes drifted from the pinned manifest` | staged/ mudou após consolidação | NÃO "consertar o hash": descobrir quem mudou; se legítimo (review), recomputar MANIFEST + gêmeo + re-review |
| `payload-sha revalidation failed` | codex upgradou desde o probe T5.2a | re-probe ADR-182 (o script imprime a receita); atualizar manifest staged + MANIFEST.sha256 + gêmeo; re-review dos bytes mudados |
| `pair-rail-gate` Gate 1/2 FAIL | env/rotação | `source` do env; rotacionar chave + logar em `docs/rotation-log.md` (override `CEO_CODEX_KEY_ROTATION_OVERRIDE=1` só emergência) |
| `HEAD != origin/main` | dessinc | `git pull --ff-only` / push pendente; re-rodar |
| `Validate on HEAD is ...` | CI não-verde | esperar/rerun do workflow; nunca assinar sobre HEAD vermelho |
| GPG `No pinentry` / sign fail | agente morto | `export GPG_TTY=$(tty); gpgconf --kill gpg-agent`; re-rodar (o sentinel é re-renderizado e re-assinado inline — idempotente) |
| `touched − scope != ∅` | sujeira fora do allowlist | inspecionar `git status`; guardar/commitar fora da cerimônia; re-rodar |
| `ORACLE RED` (qualquer) | pack quebrado | ler o log apontado; corrigir NO STAGED (nunca na árvore viva), recomputar hashes, re-review se bytes canônicos mudaram |
| GATE-V2 FAIL persistente com invocação fresca | fail-open real sob o pin novo | tratar como incidente do rail (não do gate); investigar o `pair_rail_case` novo; NÃO rodar o pack |
| claims/verify-counts RED pós-cerimônia | esperado até o closeout | fazer o commit de closeout ANTES do push (não é um bug) |
| ceo-boot row 168h ainda RED pós-GATE-V2 | 11 case-F antigos até ~08-03 | esperado; o gate é pós-âncora — registrar e ignorar |

## Idempotência / re-runs

- Ambos os scripts são re-rodáveis: preflight é read-only na árvore viva;
  `--dry-run` restaura worktree E index via trap em QUALQUER saída (S273);
  a rodada real re-renderiza e re-assina o sentinel a cada execução.
- Se a rodada real morrer ENTRE o apply e o commit: `git status` mostra o
  escopo aplicado; `git reset --hard <sha pré-cerimônia>` volta ao zero
  (o RESTORE hint é impresso em todo FATAL).
- `--gate-v2` é puro-leitura e re-rodável a qualquer momento.
