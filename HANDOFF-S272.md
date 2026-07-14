# Handoff S272 — o que rodar quando voltar

> Tudo abaixo é **Owner-gated** (GPG / console web). Nada aqui foi executado.
> Main está verde em `b1b4ada`. Os packs de cerimônia são **machine-local**
> (`staged/` é gitignored por design) — rode nesta máquina, neste checkout.
>
> **Este arquivo é descartável**: delete-o depois de rodar os passos.

---

## ⚠ PRIMEIRO: o passo que trava tudo (console npm, 2 min)

Registrar o trusted publisher em **npmjs.com** → pacote `ceo-orchestration` →
Settings → Trusted Publisher:

- repository: `Canhada-Labs/ceo-orchestration`
- workflow: **`npm-publish.yml`** ← o **nome do arquivo**, não o display name
- environment: `production-npm`

Sem isso o publish do GA morre `ENEEDAUTH`. (Playbook de recuperação:
`.claude/plans/PLAN-158/oidc-failure-playbook.md`.)

---

## 1. Release v1.1.0 — RC (PLAN-158 Wave 3)

```bash
cd /Users/joaocanhada/canhada-labs/ceo-orchestration
export GPG_TTY=$(tty)          # se o pinentry reclamar: gpgconf --kill gpg-agent
bash .claude/plans/PLAN-158/owner-rc-ceremony.sh
```

O script: confere preflight (Validate verde, pin do codex, 6 advisories
frescas) → assina e aplica **SENT-RC-SPEC** (o P2 que o pair-rail achou) →
monta o envelope do verdict **na hora** (TTL 24h começa aí) → assina → cria e
verifica a tag `v1.1.0-rc.1` → push. No fim ele imprime o comando de watch do
release-gate.

**Pair-rail do RC já rodou: 16/16 APPROVE → GO** (R1 pegou 1 P2 real, R2
aprovou o fix). Verdict body: `.claude/plans/PLAN-158/rc-verdict-body.md`.

Depois: **RC-hold de 24h FULL** (você ratificou "full" na S270).

## 2. Release v1.1.0 — GA (≥24h depois do release-gate do RC ficar verde)

```bash
bash .claude/plans/PLAN-158/owner-ga-ceremony.sh
```

Ele confere o RC-hold (aborta se <24h), re-checa as advisories, **roda um
codex fresco** sobre o delta rc..HEAD, monta e assina o verdict GA, cria a tag
`v1.1.0` e faz push. Depois da tag, na ordem:

1. Aprove o environment `production-npm` na UI do GitHub quando o
   `npm-publish.yml` pausar.
2. Smoke: `npx ceo-orchestration@latest --help` (rc=0).
3. **REVOGUE o NPM_TOKEN** granular no npmjs.com + apague o secret do repo +
   registre em `docs/rotation-log.md`.
4. Feche o PLAN-158 (`executing` → `done` com `completed_at` + `related_commits`).

---

## 3. PLAN-157 — drenar as 8 squads (Wave 1: sunsets + folds)

```bash
bash .claude/plans/PLAN-157/land-plan157-w1.sh
```

Deleta `desktop`, `dotnet`, `architecture`, `agents-meta` (OQ2:
git-history-only + pointer commitado em
`.claude/plans/PLAN-157/w1-sunset-pointer.md`), aplica os folds **SP-043..046**
(assine os `.asc` quando ele pedir), reconcilia as 9 superfícies derivadas e
leva o roster de 32 → 28 (`cap := current`). Preflight roda pins + todos os
checks **antes** de qualquer assinatura. Não faz push — ele te diz o comando.

## 4. PLAN-157 — graduações (Waves 2/3, uma squad por vez, go/no-go seu)

```bash
bash .claude/plans/PLAN-157/land-plan157-graduation.sh jvm       # → 27
bash .claude/plans/PLAN-157/land-plan157-graduation.sh cpp       # → 26
bash .claude/plans/PLAN-157/land-plan157-graduation.sh golang    # → 25
bash .claude/plans/PLAN-157/land-plan157-graduation.sh data-ml --apply-sp047   # → 24
```

Cada uma é uma cerimônia independente (pode parar em qualquer ponto — o repo
fica consistente). Use `--dry-run` primeiro se quiser ensaiar. Runbook completo:
`.claude/plans/PLAN-157/staged/GRADUATION-README.md`.

**Uma decisão sua no data-ml:** a OQ5 dizia "+1 skill", mas com o
`prisma-patterns` saindo (SP-047 → `saas-platforms`) o ADR-009 exige ≥3 skills,
então o bundle traz **+2** (`ml-evaluation-patterns`, `ml-serving-patterns`).
O sentinel body pede seu ack explícito disso.

## 5. PLAN-156-FOLLOWUP — os 7 findings do council (precisa da sua ratificação antes)

O plano ainda está `draft`. Ratifique `draft → reviewed` (o debate já rodou:
3×ADJUST → PROCEED) e então:

```bash
bash .claude/plans/PLAN-156-FOLLOWUP/land-followup.sh --dry-run   # ensaio (auto-restaura)
bash .claude/plans/PLAN-156-FOLLOWUP/land-followup.sh             # a cerimônia
```

Ensaio completo já rodou verde aqui: preflight + 2 segmentos + **4553 testes**
passando em modo canônico pós-apply.

**Leia isto antes de assinar:** o pair-rail (codex) rodou **6 rodadas** neste
pack e cada uma achou um **fail-open real** que nem o debate nem os fixtures
pegaram — inclusive `args.scope` ausente mandando o **repo inteiro** para os
vendors externos, e o push-gate deixando passar edições canônicas em três
cenários distintos (edit+revert, branch nova, commit raiz). Todos corrigidos e
com teste de regressão. O registro completo está em
`.claude/plans/PLAN-156-FOLLOWUP/pair-rail-verdict-fu.md` — vale a leitura.

Wave 4 (live-fire 3-lane) fica para depois: precisa do
`~/.grok/sandbox.toml` e da sua autorização de egress.

---

## Ordem sugerida

1. Console npm (2 min) → 2. RC → *(24h)* → 3. GA + revogar token
4. PLAN-157 W1 → graduações (uma por vez)
5. PLAN-156-FOLLOWUP (ratificar → landar)

Cada script é fail-fast, não faz push sozinho, e nenhum assina nada antes de
todos os checks passarem.
