# Release Checklist (pré / pós tag)

> Checklist operacional resumido. Para procedimento detalhado ver
> `../RELEASE.md`.

## Pré-tag (rodar na ordem)

### CI / testes

- [ ] `git fetch origin && git status` limpo
- [ ] `gh run list --branch main --limit 5` todos success
- [ ] `python3 -m unittest discover -s .claude/hooks/tests` all pass
- [ ] `python3 -m unittest discover -s .claude/scripts/tests` all pass
- [ ] `bash .claude/scripts/validate-governance.sh` exit 0
- [ ] `bash .claude/scripts/check-contamination.sh` exit 0

### Documentação

- [ ] `CLAUDE.md` §Current Work reflete o estado atual
- [ ] `CHANGELOG.md` tem entry pro release mais recente
- [ ] Coverage gate ENFORCING verde (`.github/workflows/coverage.yml`)
- [ ] `docs/actions-versions.md` tem SHAs atualizados
- [ ] `VERSION` file bate com a tag que vai criar

### Governança

- [ ] Branch protection `main` ativo no GitHub
- [ ] CODEOWNERS cobre `.claude/team.md`, skills core, ADRs
- [ ] GPG signing habilitado (`git config commit.gpgsign`)
- [ ] Todos os ADRs novos têm Status: ACCEPTED

### Hooks sanity

- [ ] Hook `check_agent_spawn.py` bloqueia spawn sem SKILL
- [ ] Hook `check_bash_safety.py` bloqueia `rm -rf`
- [ ] Hook `check_canonical_edit.py` bloqueia edit em SKILL.md
- [ ] Hook `audit_log.py` grava agent_spawn no audit log

## Tag + push

```bash
git tag -s v1.0.0-rc.1 -m "..."
git push origin v1.0.0-rc.1
```

## Pós-tag (monitorar)

### Release workflow (automático)

- [ ] `gh run watch` — todos os ~22 steps do `release.yml` green
  (ver `.github/workflows/release.yml`). Inclui, entre outros:
  version-match (VERSION == tag), freshness de docs canônicos, a
  janela de re-pass do Codex de 24h (ADR-103, só em tags GA),
  CHANGELOG entry, registry validate, governance, suites de
  hooks/scripts/replay, smoke install + self-SHA do install.sh,
  SBOM, verificação de assinatura GPG da tag, e o gate do
  pair-rail verdict.

### GitHub Release UI

- [ ] https://github.com/.../releases — new release from tag
- [ ] Title: `vX.Y.Z-rcN — Release Candidate N` (ou sem -rc pra stable)
- [ ] Marca ☑ "pre-release" se for -rc
- [ ] Body: copia mensagem do tag + link pro CHANGELOG

### Hold (janela de re-pass de 24h — ADR-103)

- [ ] Roda o re-pass do Codex contra a tag `-rc.N`
- [ ] Verifica issues abertos no repo + audit log (se houver telemetria)
- [ ] Smoke test em repo limpo (simulação adopter)
- [ ] ≥24h após a `-rc.N`, com CI verde: decisão — promote pra stable
      OU cut `-rc.N+1` (o relógio de 24h reinicia na última RC)

### Promote stable

- [ ] `echo "X.Y.Z" > VERSION` (sem -rcN)
- [ ] Commit bump
- [ ] `git tag -s vX.Y.Z`
- [ ] GitHub release (sem pre-release flag)
- [ ] Atualiza README badge

## Rollback

Se `v1.0.0` problem:
- [ ] NÃO remove tag (histórico imutável)
- [ ] Cria `v1.0.1` com fix
- [ ] Marca v1.0.0 release como deprecated no UI

## Comunicação

- [ ] Convida primeiro funcionário (mandar QUICKSTART + FOR-EMPLOYEES)
- [ ] Debrief com esse funcionário depois de 1 semana
- [ ] Atualiza `docs/adopters.md` (se criar) com casos de uso
