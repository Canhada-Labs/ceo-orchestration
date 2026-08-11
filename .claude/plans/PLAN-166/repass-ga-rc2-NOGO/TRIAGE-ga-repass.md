# Triagem — re-pass do hold GA v1.3.0 (10/08/2026, noite)

Rodada: `OWNER-GA-CUT.sh` 1/8 (re-pass em 2 partes sobre a árvore da rc.2, `0cb09c3`).
Veredito codex: **NO-GO nas duas partes** — script abortou antes do corte (fail-closed correto).
Triagem: CEO (Claude), verificação item a item contra a árvore local. **8/8 achados REAIS; 0 ruído.**

## Parte 1 — superfícies de release (verdict-ga-1.txt)

| # | Sev | Achado | Verificação | Disposição |
|---|-----|--------|-------------|------------|
| 1 | P1 | `CHANGELOG.md:12` e `:122` publicam **188 ADRs**; disco tem **190** (ADR-189/190 do PLAN-166 W1/168). `verify-counts.sh` não varre CHANGELOG → drift fica verde. | CONFIRMADO (`ls .claude/adr/ADR-*.md | wc -l` = 190; grep no CHANGELOG mostra 188 em 2 sítios). Mesma classe da lição [[feedback-adr-count-drift-unwatched-docs]] — CHANGELOG é mais um doc NÃO-vigiado. | CURAR pré-GA: 188→190 nos 2 sítios + adicionar CHANGELOG.md ao verify-counts.sh (matcher de ADR-count). |
| 2 | P1 | Notas v1.3.0 do CHANGELOG não mencionam a semântica de upgrade adopter-visível dos PLAN-166–169 (SPEC/v1 forçado, backups, `.framework-version`, root `VERSION` intencionalmente stale) — contradiz o contrato do próprio log ("behavior an adopter would notice after upgrading"). | CONFIRMADO (seção v1.3.0 só cita PLAN-162/165; comportamento documentado em `INSTALL.md:630-641`). | CURAR pré-GA: acrescentar subseção de upgrade v1.3.0. |
| 3 | P2 | `.github/release-checklist.md:37-46` (inventário "exaustivo" de version-sites) omite `.claude/.framework-version`. | CONFIRMADO (grep sem hit no checklist; site real em `_release_bump_sites.py:78-84`). | Cura barata junto com o pacote de docs. |
| 4 | P2 | Checklist diz "~29 steps"; `release.yml` tem 31 nomeados (`RELEASE.md` já diz 31). | CONFIRMADO. | Cura barata (ou derivar do oracle). |

## Parte 2 — mecânica de publish (verdict-ga-2.txt)

| # | Sev | Achado | Verificação | Disposição |
|---|-----|--------|-------------|------------|
| 5 | **P1** | `npm-publish.yml`: run OBSOLETO pode publicar a árvore errada. Cenário: tag em A → gate verde → tag deletada/recriada em B (procedimento de recovery documentado no próprio workflow) → o run antigo ainda pode ser aprovado/rerun com checkout pinado em A → `npm publish` de A, irreversível, com a tag viva apontando pra B. Nenhum passo re-resolve a tag remota contra `GITHUB_SHA` antes do publish. | CONFIRMADO na leitura do job `publish-release` (checkout do SHA do evento; guard `already_published` não cobre; environment-approval é a única barreira — humana, exatamente a que o recovery manda usar). | **CURAR pré-GA** (é o P1 que motivou o NO-GO da parte 2): passo fail-closed imediatamente antes do publish — `git ls-remote` da tag, peel, exigir `== GITHUB_SHA` — + teste de regressão delete/re-tag. |
| 6 | P2 | `verify-counts.sh --help` imprime contrato estático com exatos velhos (ADRs 188, steps 29, workflows 21) vs disco (190/31/22); o gate nunca checa o próprio help. | CONFIRMADO (header lines 35-45; `--help` faz `sed` do header). | Follow-up (pode ir no W3/W4 ou junto das curas de docs). |
| 7 | P2 | `await_release_gate.py::parse_timestamp` aceita componentes fora de faixa (`99:99:99`) porque `calendar.timegm` normaliza — contradiz fail-closed-on-malformed. | CONFIRMADO (regex `\d{2}` sem validação de faixa antes da conversão). | Follow-up (validar faixas + testes negativos). |
| 8 | P2 | `install-npm.sh` (stager LOCAL) ainda copia root `README.md` → `npm/`, sobrescrevendo o npm/README revisado; produção foi curada (S288) mas o espelho local diverge — smoke local valida artefato ≠ do publicado. | CONFIRMADO (`for src in ... README.md; rsync → $NPM_DIR/`). | Follow-up (remover da lista + teste de paridade stager-local ↔ produção). |

## Decisão de rota — PENDENTE DO OWNER

Curar os P1 (#1, #2, #5) exige commits em `main` ⇒ `origin/main` deixa de ser a árvore da rc.2 ⇒ **a rc.2 deixa de ser o candidato GA**. Opções:

- **(A) Recomendada:** curar P1s (+P2 #3/#4 baratos, mesma superfície de docs) → cortar **rc.3** → hold ADR-103 de 24h → GA em ~12/08. Segue o protocolo à risca; o hold re-passa sobre a árvore curada.
- **(B)** Curar P1s → GA direto com **rc-hold-waiver** registrado (mecanismo existe; check `rc_hold_aged` o vigia). Economiza 24h ao custo de furar o hold numa árvore que nunca ficou 24h sob observação. Não recomendo com um P1 de publish-mechanics recém-curado.
- Em ambas: P2 #6/#7/#8 podem ir no trem seguinte (W3/W4 do PLAN-169) sem bloquear GA — nenhum altera o artefato publicado.

Interação com o W3 (PLAN-169): o pack staged já toca `release.yml` (bump timeout 20→35 via `~/.rc2-backup/w3-timeout-bump-postGA.patch`, planejado PÓS-GA). Se a rota for (A), avaliar incluir o bump do timeout **já na rc.3** (evita o rerun-ritual do gate) — exige re-pin do staged MANIFEST e ajuste do draft W3.

## Evidência

- Vereditos: `verdict-ga-1.txt`, `verdict-ga-2.txt` (rc=0 nos dois; NO-GO textual).
- Transcripts: `transcript-ga-1.log` (16.572 linhas), `transcript-ga-2.log` (13.510 linhas).
- Payloads redigidos + diffs + `PROVENANCE-ga.md` + `MANIFEST-ga.sha256` neste diretório.
- Nenhum commit feito nesta sessão (autorização do Owner pendente para as curas).
