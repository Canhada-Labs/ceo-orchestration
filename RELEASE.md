# RELEASE — Procedimento para tagear v1.0.0 (RETIRED)

> **RETIRED 2026-04-29 (Session 74).** Este guia descreve o
> procedimento original para tagear `v1.0.0-rc.1`. O framework já
> está em `v1.0.0` (ver `CHANGELOG.md` para a cadência completa).
> Per ADR-096 (`vibecoder-only by design`) e ADR-095 (calendar-gates
> retracted), **não há mais cadência formal de release por
> calendário**: a tag sai quando o Owner decide, sem o antigo hold
> de 7 dias e sem cron de revisão. O `release.yml` ainda exige a
> janela mecânica de re-pass do Codex de 24h (ADR-103) entre a tag
> `-rc.N` e a GA. CHANGELOG.md é o registro autoritativo de cadência
> observável.
>
> **Para ver a versão atual e changelog:**
>
> - `cat VERSION` — versão semântica corrente (`1.0.0`)
> - `git tag -l 'v*' --sort=-creatordate | head -5` — últimas 5 tags
> - `CHANGELOG.md` — entries por versão
> - `.github/workflows/release.yml` — release-gate + publish-release (27 steps,
>   GPG-signed tags)
>
> Histórico preservado abaixo apenas como referência de como o
> framework operava em v1.0.0-rc.1.

> Guia passo-a-passo para o Owner tagear `v1.0.0-rc.1` e, após
> 7 dias de hold, promover para `v1.0.0` estável. Todos os comandos
> são copy-paste ready (absolutos, sem placeholder).

## Pré-requisitos

Antes de começar, confirme:

- [ ] CI 100% verde na main (`gh run list --branch main --limit 5`
      todos em `success`)
- [ ] Branch protection ligado no GitHub (`Settings → Branches → main`)
- [ ] CODEOWNERS atualizado (`cat .github/CODEOWNERS`)
- [ ] CHANGELOG atualizado na `CLAUDE.md` §CHANGELOG
- [ ] `docs/coverage-baseline.md` tem números reais (não `_pending_`)
- [ ] Sua chave GPG está configurada pro git:
      `git config --global commit.gpgsign true`

Se qualquer item faltar, resolva antes de prosseguir.

## Passo 1 — Verificar estado pré-tag

Rode do diretório do repo:

```bash
cd /Users/devuser/ceo-orchestration

# Atualiza local
git fetch origin
git checkout main
git pull origin main

# Verifica que não há commits pendentes
git status

# CI verde
gh run list --branch main --limit 5

# Tests passing local
python3 -m unittest discover -s .claude/hooks/tests -p 'test_*.py' 2>&1 | tail -3
python3 -m unittest discover -s .claude/scripts/tests -p 'test_*.py' 2>&1 | tail -3

# Governance
bash .claude/scripts/validate-governance.sh

# VERSION file existe
cat VERSION
# Deve ser: 1.0.0-rc.1
```

**Todos verdes?** Pode tagear. **Qualquer vermelho?** Corrige antes.

## Passo 2 — Criar tag `v1.0.0-rc.1`

```bash
cd /Users/devuser/ceo-orchestration

git tag -s v1.0.0-rc.1 -m "Release candidate 1 — v1.0.0

Primeiro release candidate do ceo-orchestration para uso público.

Scope: framework completo para Claude Code.
- 42 skills (19 core + 8 frontend + 9 fintech + 3 lgpd + 3 trading-hft)
- 6 Python hooks (todos via Adapter Layer)
- 17 ADRs
- 537 testes (303 hook + 234 script)
- Coverage enforcing 86%
- Agent Architect meta-agent
- Reflexion v2 com outcome loop
- Cross-adapter golden fixtures (Claude prod, Gemini stub)

Changelog completo: CLAUDE.md §CHANGELOG + git log"

git push origin v1.0.0-rc.1
```

O `-s` faz tag **signed annotated** (assinado com sua GPG key).

## Passo 3 — Verificar release workflow

Ao dar push, dispara automaticamente `.github/workflows/release.yml`
com 7 gates. Acompanhe:

```bash
# Aguarda 30s pro workflow começar
sleep 30

# Lista a run mais recente do workflow Release
gh run list --workflow Release --limit 1

# Acompanha em tempo real
gh run watch $(gh run list --workflow Release --limit 1 --json databaseId -q '.[0].databaseId')
```

Os 7 gates:

1. Checkout + Python setup
2. Version match (VERSION file == tag)
3. Hook tests green
4. Script tests green
5. Governance validate
6. Contamination check
7. Smoke-install on clean dir

**Se qualquer gate falhar:** deleta a tag, corrige, re-tag:

```bash
# Remover tag local + remote
git tag -d v1.0.0-rc.1
git push origin :refs/tags/v1.0.0-rc.1

# Corrige o problema, commita, aí volta ao Passo 2
```

## Passo 4 — Criar GitHub Release (UI)

Com todos os 7 gates verdes:

1. Vá em https://github.com/Canhada-Labs/ceo-orchestration/releases
2. "Draft a new release"
3. Escolha tag `v1.0.0-rc.1`
4. Title: `v1.0.0-rc.1 — Release Candidate 1`
5. Body: copie a mensagem do tag annotated (Passo 2)
6. Marca ☑ "This is a pre-release"
7. Click "Publish release"

## Passo 5 — Período de hold (7 dias)

Durante 7 dias:

- Se aparecer bug crítico: corrige, bumps pra `v1.0.0-rc.2`, repete
  Passo 2-4
- Se tudo OK, prossegue Passo 6

Monitorar durante hold:

```bash
# Consulta issues abertas
gh issue list --label bug

# Consulta audit log de eventuais instalações
python3 .claude/scripts/audit-query.py health
```

Se quiser que eu investigue algo durante o hold, me chama — o CEO
continua disponível.

## Passo 6 — Promover para `v1.0.0`

Após 7 dias sem regressão:

```bash
cd /Users/devuser/ceo-orchestration
git fetch origin
git checkout main
git pull origin main

# Bump VERSION file
echo "1.0.0" > VERSION
git add VERSION
git commit -m "chore: bump VERSION to 1.0.0 (stable)"
git push origin main

# Aguarda CI verde pro commit de bump
sleep 60
gh run list --branch main --limit 3

# Tag estável
git tag -s v1.0.0 -m "Release 1.0.0 — ceo-orchestration (stable)

Stable release promoted from v1.0.0-rc.1 after 7-day smoke hold.
No regressions observed during hold window.

See v1.0.0-rc.1 release notes for feature list.
GitHub release: https://github.com/Canhada-Labs/ceo-orchestration/releases/tag/v1.0.0"

git push origin v1.0.0
```

Repete Passo 3 + Passo 4 para `v1.0.0` (sem marcar "pre-release").

## Passo 7 — Release comunicação

Após `v1.0.0` estável:

1. Atualiza `README.md` com badge de versão:
   ```markdown
   [![release](https://img.shields.io/github/v/release/Canhada-Labs/ceo-orchestration)](https://github.com/Canhada-Labs/ceo-orchestration/releases)
   ```

2. Convida primeiro funcionário:
   - Manda `docs/QUICKSTART.md` + `docs/FOR-EMPLOYEES.md`
   - Pede pra seguir `examples/first-session.md`
   - Debrief depois de 1 semana — o que funcionou, o que confundiu

3. (Opcional) NPM publish: ver `SPEC/v1/npm-shim.md`.

## Emergências

### Tag errada, preciso remover

```bash
git tag -d v1.0.0-rc.1                         # local
git push origin :refs/tags/v1.0.0-rc.1         # remote

# Se criou GitHub Release: delete no UI primeiro, depois re-tag
```

### Commit ruim em main depois do tag

```bash
git revert <sha-do-commit-ruim>
git push origin main
# Dispara CI; aguarda verde; aí tag v1.0.0-rc.2
```

### Precisa voltar atrás no bump de VERSION

```bash
echo "1.0.0-rc.1" > VERSION
git add VERSION
git commit -m "chore: revert VERSION to 1.0.0-rc.1 (issue found, hold extended)"
git push origin main
```

## Branch protection — setup recomendado

No GitHub → Settings → Branches → Add rule:

- Branch name pattern: `main`
- ☑ Require a pull request before merging
- ☑ Require approvals: 1
- ☑ Require review from Code Owners
- ☑ Require status checks to pass before merging:
  - `Governance, health, contamination, shellcheck`
  - `Python unittest coverage (enforcing, --fail-under=86)`
  - `smoke`
- ☑ Require branches to be up to date before merging
- ☑ Require signed commits
- ☑ Require linear history
- ☐ Allow force pushes (deixa desmarcado)
- ☐ Allow deletions (deixa desmarcado)
- ☐ Allow administrators to bypass (deixa DESmarcado — você precisa
  seguir sua própria regra)

Salva. Teste tentando force-push (deve bloquear).

## Rollback de release (se der muito errado)

Se `v1.0.0` der problema grave:

```bash
# Não remove o tag (histórico imutável). Cria v1.0.1 com o fix:
git checkout main
git pull origin main
# ... faz o fix ...
echo "1.0.1" > VERSION
git add VERSION
git commit -m "fix: critical bug in X (v1.0.0 rollback via v1.0.1)"
git push origin main
git tag -s v1.0.1 -m "1.0.1 — critical fix over v1.0.0"
git push origin v1.0.1
```

No GitHub release de `v1.0.0`: edita pra marcar "deprecated, use v1.0.1".

## Owner-only knobs (Sprint 9+)

Env vars que só o Owner deve setar. Não documentadas em QUICKSTART /
FOR-EMPLOYEES (deliberadamente — previne flip acidental).

### `CEO_CONFIDENCE_ENFORCE` (Sprint 9, ADR-019)

- **Default:** 0 (advisory-hook; CLI fails não bloqueiam)
- **Quando setar:** após 1 semana de FPR baseline coletado, SE FPR < 5%
  em 50+ spawns
- **Efeito quando =1:** qualquer `CLAIM:` que falhar faz o hook
  bloquear (exit 2 + reason). Mantém fail-open em timeout/infra.
- **Rollback signal:** se >1 spawn legítimo/dia for bloqueado, revert
  para 0 e abre issue `confidence-gate-fp` com output + evento.

### `CEO_CONFIDENCE_BYPASS` (escape hatch)

- **Default:** 0
- **Quando setar:** apenas quando `CEO_CONFIDENCE_ENFORCE=1` está
  wedgando uma sessão legítima e você precisa destravar em segundos.
- **Escopo:** session-local (`export` na shell atual; não persiste).
- **Efeito:** hook sempre permite, ignora exit code do CLI.
- **Post-uso:** `unset CEO_CONFIDENCE_BYPASS` assim que a sessão
  travada for liberada.

### `CEO_PRUNE_EXECUTE` (Sprint 8, ADR-017 amended)

- **Default:** 0 (plan-only preview)
- **Quando setar:** manualmente no terminal antes de rodar
  `prune-lessons.py --execute`, para coletar baseline de restore-ratio.
- **Guard-rails:** `--max-archive N` cap obrigatório + receipt file
  + companion `lesson-restore.py` para reverter.

### `CEO_CONFIDENCE_MAX_CLAIMS` (PLAN-009 A12)

- **Default:** 200
- **Quando setar:** raro — apenas se um agente legítimo gera centenas
  de claims. Default cobre 99%+ dos casos.
- **Efeito:** acima do cap, `extract_claims` trunca + emite evento com
  `truncated=true` + `raw_claim_count=N`.

## Timeline esperada

| Etapa | Tempo |
|---|---|
| Pré-check (Passo 1) | 10 min |
| Tag rc.1 (Passo 2-4) | 15 min |
| Hold (Passo 5) | 7 dias |
| Promote v1.0.0 (Passo 6) | 15 min |
| Comunicação + NPM (Passo 7) | 1h |

**Total ativo: ~1h 40min ao longo de 7 dias.**

## Checklist final (imprima e risque)

- [ ] Passo 1: pré-checks todos verdes
- [ ] Passo 2: tag `v1.0.0-rc.1` criada e pushada
- [ ] Passo 3: release workflow 7/7 gates verdes
- [ ] Passo 4: GitHub Release `v1.0.0-rc.1` publicado (pre-release)
- [ ] Passo 5: 7 dias de hold cumpridos, sem regressão
- [ ] Passo 6: tag `v1.0.0` criada + pushada
- [ ] Passo 7: comunicação enviada, primeiro funcionário onboarded

Ao risar todos os 7, o ceo-orchestration está **released e em uso**.
