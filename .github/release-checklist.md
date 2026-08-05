# Release Checklist (pré / pós tag)

> Checklist operacional resumido. Para procedimento detalhado ver
> `../RELEASE.md`.

## Pré-tag (rodar na ordem)

### CI / testes

- [ ] `git fetch origin && git status` limpo
- [ ] `gh run list --branch main --limit 5` todos success
- [ ] Suítes na **invocação do CI** (NUNCA `unittest discover` — a suíte é
      pytest-only por construção: conftest.py e fixtures `autouse` não
      existem sob unittest, a isolação desliga em silêncio e produz
      falso-verde/falso-vermelho; foi exatamente isso que barrou o promote
      do GA v1.2.0 em 2026-08-02):
  - [ ] `python3 -m pytest .claude/hooks/tests/ -n auto -m 'not serial' --strict-markers -q`
  - [ ] `python3 -m pytest .claude/hooks/tests/ -m 'serial' --strict-markers -q`
  - [ ] `python3 -m pytest .claude/scripts/tests/ .claude/scripts/optimizer/tests/ -n auto -m 'not serial' --strict-markers -q`
  - [ ] `python3 -m pytest .claude/scripts/tests/ .claude/scripts/optimizer/tests/ -m 'serial' --strict-markers -q`
      ← **as QUATRO**, não três: `validate.yml:425` roda a partição
      serial dos scripts também (é onde vivem os testes de wall-clock/perf).
      Rodar só as não-seriais dá falso-verde pré-tag quando um teste
      serial quebra.
- [ ] `bash .claude/scripts/validate-governance.sh` exit 0
- [ ] `bash .claude/scripts/check-contamination.sh` exit 0

### Documentação

- [ ] `CLAUDE.md` §Current Work reflete o estado atual
- [ ] `CHANGELOG.md` tem entry pro release mais recente
- [ ] Coverage gate ENFORCING verde (`.github/workflows/coverage.yml`)
- [ ] `docs/actions-versions.md` tem SHAs atualizados
- [ ] `VERSION` file coerente com a tag: em tag **`-rc.N` o VERSION fica
      PURO** (`X.Y.Z`, sem sufixo — o `release.yml` strippa `-rc.N` na
      validação); em tag stable, idêntico. E o bump NÃO é 1 site. Os
      sites que `verify-counts.sh` de fato checa (§VERSION_SITES + os
      lidos à parte), mais o `VERSION` que é a fonte da verdade:
      `VERSION` (fonte) ·
      `INSTALL.md` (`--pin vX.Y.Z`) ·
      `docs/ARCHITECTURE.md` (`currently vX.Y.Z, aligned with the repo`) ·
      `npm/README.md` (`last-reviewed: <data> vX.Y.Z`) ·
      `npm/package.json` (`"version"`) · `pyproject.toml` (`version =`) ·
      `SBOM.md` (`**Version:** \`X.Y.Z\``) ·
      `SECURITY.md` + `VERSIONING.md` (janela de suporte
      `Current/Previous MINOR (vX.Y.x)` — **família minor**).
      ⚠ **O driver NÃO cobre tudo** (S293, codex r2/r3): ele reescreve os
      stamps `last-reviewed` e o triple do SBOM, mas o **shift da janela
      de suporte** (`Previous` ← `Current`) e a **anotação da tag** são
      MANUAIS de propósito — ambos exigem juízo de release-train. O
      `verify-counts` falha alto na janela; a prosa da tag **nenhum gate
      prova**, então releia-a antes de assinar.
      **`CLAUDE.md` e `README.md` NÃO são sites de versão** — nunca
      carregaram literal de versão (`git log -S 'VERSION='` não acha
      commit que o tenha adicionado); procurá-los num bump é perder tempo
      atrás de literal inexistente
      **+ os 2 manifests de plugin** (`.claude-plugin/{plugin,marketplace}.json`,
      regenerados via `scripts/build-plugin.py --write-manifests`, nunca
      hand-patch; o gate deles vive só no `release.yml`).
      O badge do README **não** é site de versão — é dinâmico e o driver
      não o toca; auditar por ele deixa passar drift real.
      O driver cobre os sites mecânicos listados acima — **exceto** o
      shift da janela de suporte e a prosa da tag, que são manuais por
      desenho (ver o aviso acima e §Promote stable).

### Governança

- [ ] Branch protection `main` ativo no GitHub
- [ ] CODEOWNERS cobre `.claude/team.md`, skills core, ADRs
- [ ] Chave GPG de release do Owner disponível (`gpg -K`).
      `commit.gpgsign`/`tag.gpgsign` ficam **UNSET por design** — commits
      comuns não são assinados; o driver assina a TAG inline com `-u`
      (o que o Owner assina no release é a tag, não os commits)
- [ ] Todos os ADRs novos têm Status: ACCEPTED

### Hooks sanity

- [ ] Hook `check_agent_spawn.py` bloqueia spawn sem SKILL
- [ ] Hook `check_bash_safety.py` bloqueia `rm -rf`
- [ ] Hook `check_canonical_edit.py` bloqueia edit em SKILL.md
- [ ] Hook `audit_log.py` grava agent_spawn no audit log

## Tag + push

Preferir o driver (3 fases fail-closed, assina inline, **nunca pusha**):

O driver tem **três** fases e o seletor de alvo (`--rc N` / `--stable`)
tem de ser o MESMO nas três — `preflight` sem seletor checa o alvo
errado, e pular `bump` faz o `tag()` abortar no seu próprio check
`VERSION != TARGET_BASE` (nenhum dos sites de versão foi atualizado).

```bash
# RC:
bash .claude/scripts/local/release.sh preflight --rc N
bash .claude/scripts/local/release.sh bump      --rc N --npm-readme-reviewed
bash .claude/scripts/local/release.sh tag       --rc N
git push origin vX.Y.Z-rc.N        # push é manual, sempre

# STABLE (a tag criada é vX.Y.Z, sem sufixo — pushe ESSE nome):
bash .claude/scripts/local/release.sh preflight --stable
bash .claude/scripts/local/release.sh bump      --stable --npm-readme-reviewed
bash .claude/scripts/local/release.sh tag       --stable
git push origin vX.Y.Z
```

O nome da tag muda com a fase; pushar `-rc.N` depois de `tag --stable`
falha (a tag não existe) ou publica a errada.

**O `bump` é idempotente (PLAN-166/F2).** Numa árvore já no alvo com os
quatro oráculos limpos (`VERSION`, `verify-counts`, `build-plugin
--check`, `check-canonical-doc-freshness`) ele **não escreve arquivo
nenhum** e retorna 0 — inclusive no D+1 do hold. Isso é SUCESSO, não
falha: a pós-condição da fase já está satisfeita. Para uma re-revisão de
verdade dos docs (mexer nas stamps `last-reviewed:` sem mudar versão) o
caminho nomeado é `bump --restamp --npm-readme-reviewed`.

**Se o `bump` criou commit, pushe `main` ANTES de taggear.** A fase `tag`
roda dois guards fail-closed, RC e stable igualmente:

- **ancestralidade** — `HEAD` tem de ser ancestral de `origin/main`.
  Falha de rede e "HEAD não está em main" são erros DISTINTOS; para
  operar offline de propósito existe `--offline-ack` (anunciado alto).
- **delta restrito** — `git diff <parent_sha do verdito>..HEAD` tem de
  caber na allowlist FECHADA que o verdito assinado
  (`.claude/governance/pair-rail-verdict-<TAG>.md`) declara: o próprio
  verdito, o `verdict-fields-<TAG>`, e os artefatos do re-pass por nome
  exato — com o `sha256` do `MANIFEST.sha256` pinado no verdito e
  `shasum -a 256 -c` rodado por cima. Nada de wildcard. O invariante é
  "nada landou depois do que o re-pass revisou".

O assert local **não basta** e não pretende bastar: uma tag assinada à
mão pula o driver. O mesmo assert entra server-side no `release.yml`.

## Pós-tag (monitorar)

### Release workflow (automático)

- [ ] `gh run watch` — todos os ~29 steps do `release.yml` green
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

- [ ] Gate de 24h: delta ≥24h da **rc mais RECENTE por creator-date**
      (sem rc prévia = fail; rc deletada não conta)
- [ ] **Novo** `pair-rail-verdict-vX.Y.Z.md` (o verdict é POR TAG — o
      step do release.yml roda no GA também; o da rc não vale)
- [ ] `bash .claude/scripts/local/release.sh preflight --stable`
      ← **não pule**: é aqui que o driver re-checa árvore limpa/main, CI,
      governança, usabilidade da chave de assinatura e disponibilidade da
      tag stable. Ir direto ao `bump` depois do hold pula tudo isso
- [ ] `bash .claude/scripts/local/release.sh bump --stable --npm-readme-reviewed`
      — atualiza os sites doc/package E regenera os manifests de plugin
      (NUNCA `echo > VERSION` à mão: bumpar um site com o resto vivo foi
      a causa do red da rc.1 da v1.2.0). Depois do hold isso normalmente
      é um **no-op** — a árvore já está no alvo. No-op é sucesso
- [ ] `bash .claude/scripts/local/release.sh tag --stable` + `git push origin vX.Y.Z`
      — o guard de delta restrito exige que o único delta desde o
      `parent_sha` do verdito seja o próprio verdito + evidência pinada
- [ ] GitHub release (sem pre-release flag)

### Se o `npm-publish.yml` estourar o prazo esperando o gate

O job `await-release-gate` tem prazo próprio. Se ele expirar porque o
`release-gate` ficou preso em fila, a rota de recuperação é
**re-rodar o job `await-release-gate`** depois que o `release-gate`
ficar verde: o run da tag está pinado à ÁRVORE DA TAG, então o re-run é
seguro e **não** exige deletar/re-criar a tag.

E a aprovação manual do environment `production-npm` é a **última chance
humana** antes do publish — não é uma segunda opinião sobre o gate. Se o
gate está vermelho, a resposta é consertar e re-rodar, nunca aprovar por
cima.

## Rollback

Se `v1.0.0` problem:
- [ ] NÃO remove tag (histórico imutável)
- [ ] Cria `v1.0.1` com fix
- [ ] Marca v1.0.0 release como deprecated no UI

## Comunicação

- [ ] Convida primeiro funcionário (mandar QUICKSTART + FOR-EMPLOYEES)
- [ ] Debrief com esse funcionário depois de 1 semana
- [ ] Atualiza `docs/adopters.md` (se criar) com casos de uso
