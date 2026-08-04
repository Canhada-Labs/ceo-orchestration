# HANDOFF S291 — o que está pronto, o que o Owner executa

> Sessão de zeragem de dívida. Nada foi commitado (CLAUDE.md §Anti-patterns:
> "NEVER commit without explicit Owner authorization"). Tudo abaixo está em
> disco, verificado, com os comandos prontos.

## 1. Landado em disco na árvore principal (falta commitar)

| Arquivo | O quê |
|---|---|
| `.claude/scripts/local/verify-counts.sh` | `registered` deixou de ser vacuoso: parse do subtree `hooks{}` (46 distintos / 48 registrations) em vez de grep do arquivo inteiro com regex sem hífen (que contava `statusline-ceo.py` como um fantasma `ceo.py` = 47). Regras mortas ressuscitadas: `registered` (0 matches → 5), `registrations` (nova, 4), `release_steps` (0 → 1). `workflows` documentado como NÃO doc-gated. Novo campo `rule_matches` no `--json`. |
| `.claude/scripts/tests/test_verify_counts*.py` | +2 testes: `test_statusline_decoy_not_counted` (a classe do fantasma) e `test_real_repo_rule_liveness` (**gate anti-vacuous**: métrica com 0 matches falha o teste). settings.json dos scaffolds virou JSON válido com o decoy do statusLine. 21 passed. |
| `RELEASE.md` | 27 → 29 steps (o número real). |
| `.github/release-checklist.md` | `unittest discover` → invocação do CI (a classe que barrou o GA v1.2.0); VERSION puro em RC + 6 sites doc/package + 2 manifests de plugin; GPG signing descrito como é (tag assinada, `commit.gpgsign` UNSET por design); driver de release na receita; ~22 → ~29 steps. |
| `.claude/plans/PLAN-163-substrate-uplift.md` | Emenda datada no OQ5: `disableAutoMode` REVERTIDO pela cerimônia S290. |
| `.claude/plans/PLAN-162-*.md` | `draft` → **`reviewed`**; W0 documentado; OQ1/OQ2/OQ3 resolvidas. |
| `.claude/plans/PLAN-165-*.md` | OQ1-redo/OQ2/OQ3 ratificadas pelo Owner, verbatim. |
| `.claude/plans/PLAN-162/debate/round-1/` | proposal + 3 critiques + anonymization-map + **consensus** (14 ajustes). |
| `.claude/plans/PLAN-164/debate/amend-2-round-1/` | proposal + 2 critiques + **consensus** (9 ajustes). |
| `.claude/hooks/tests/test_redact_mutation_kills.py` | Testes que matam os mutantes sobreviventes do `redact.py`. |
| `.claude/scripts/local/json_ok.py` | Helper de preflight (evita `python3 -c` referenciando caminho canônico, que o bash-safety bloqueia — corretamente). |

Comando (o Owner decide se commita tudo junto ou separa):

```bash
cd ~/canhada-labs/ceo-orchestration
git add -A && git commit -m "fix(gates): verify-counts vacuous-gate + release docs + PLAN-162 W0 debate"
```

## 2. Worktree `plan-165-draft` (`.claude/worktrees/plan165`)

- `night-mode.py`: **NM-04 endurecido** — o seam `CEO_NIGHT_MODE_TEST_SEAM`
  deixou de ser bypass geral; só alarga o confinamento para alvos sob o
  tempdir do sistema. Teste novo `test_seam_does_not_widen_outside_tempdir`
  (redireciona `TMPDIR` do filho). **86 passed.**
- `ceremony-staged/`: pack com **5 patches** + MANIFEST regenerado
  (`shasum -c` OK).

## 3. Cerimônia S291 — PRONTA, Owner executa

Script: `<scratchpad>/ceremony-s291.sh` (shellcheck limpo, `--dry-run`
restaura árvore E índice via trap, assina INLINE, **nunca pusha**).

> ### ⚠ PASSO 0 OBRIGATÓRIO — commitar o pack ANTES da cerimônia
>
> O ensaio em clone limpo **falhou no BLOCK 2** e a causa é real: o pack
> corrigido (p1-corrected + p2b + p4 + MANIFEST novo) vive **apenas no
> worktree, não commitado**. Um clone puxa o pack COMMITADO, que ainda é
> o antigo — e o p1 antigo **não aplica mais**, porque o p3 (landado em
> `9f53628`) reescreveu exatamente o `settings.json:763` que ele usa de
> contexto.
>
> Ler o pack direto do worktree seria a saída errada: a disciplina do
> repo (S274) exige manifesto de hash **RASTREADO** no momento da
> cerimônia. Então:
>
> ```bash
> cd ~/canhada-labs/ceo-orchestration/.claude/worktrees/plan165
> git add -A && git commit -m "pack(PLAN-165): p1-corrected + p2b + p4 + NM-04 hardening"
> ```
>
> Só depois rodar a cerimônia na árvore principal. Com o pack corrigido
> em disco, o ensaio passa (log em `<scratchpad>/rehearse2.log`).

Landa 4 patches:
- **p1-corrected** (4 arquivos) — 6 entradas de deny + espelho no template
  + os 3 caminhos em `_CANONICAL_GUARDS` (o rail que de fato fecha o Bash;
  o codex CX-1 provou que deny é por-FERRAMENTA) + overlay/marker em
  `_KERNEL_PATHS`. Implementa o OQ1-redo ratificado.
- **p2** — `night_mode_toggled` no `audit_emit.py`.
- **p2b** (NOVO) — os 4 testes de contrato que o p2 deixa vermelhos
  (sha256 de `_KNOWN_ACTIONS` 323→324, dois pins de contagem, o
  `_EXPECTED_PUBLIC_SYMBOLS`) + o teste de cobertura por-ação que o
  checklist do pack exigia (item 4). **Sem ele o p2 sozinho reddena o CI.**
- **p4** (NOVO) — `install.sh` ganha as entradas de `.gitignore` de
  postura (CX-3): sem elas `/night-mode on` suja a árvore do adopter.

Preflight já rodado em clone limpo com os 4 aplicados: **997 passed,
15 skipped, 5 xfailed** nas suítes alvo; JSON parseia; shellcheck limpo.

**ENSAIO COMPLETO em clone limpo (`<scratchpad>/rehearse2.log`)** — todos
os blocos, com o GPG stubado:

```
BLOCK 1 manifesto      6/6 OK (fail-closed)
BLOCK 2 apply --check  4/4 ok
BLOCK 3 apply          4 patches
BLOCK 4 gates          json ok · shellcheck ok · 953 passed, 13 skipped, 5 xfailed
BLOCK 5 sentinel       16 linhas, Scope = 9 arquivos
BLOCK 7 scope          touched - scope = ∅  ✓
BLOCK 8 commit         monta (13bc7a4)
```

Escopo que o sentinel vai assinar (9 arquivos):
`_lib/audit_emit.py` · `check_arbitration_kernel.py` ·
`check_canonical_edit.py` · 3 testes de audit_emit · `.claude/settings.json` ·
`scripts/install.sh` · `templates/settings/settings.base.json`.

```bash
bash <scratchpad>/ceremony-s291.sh --dry-run   # ensaio
bash <scratchpad>/ceremony-s291.sh             # real (pede GPG)
```

## 4. Pronto, aguardando a 2ª cerimônia

- **ADR-110-AMEND-2** (`<scratchpad>/ADR-110-AMEND-2-*.md`) — 120/180 →
  180/210. O debate matou a minha justificativa: eu medi **n=14** lendo 7
  de 8 arquivos de log (uma rotação criou o 8º no meio da sessão). A
  verdade é **n=20, p95 = 119.8 s — ABAIXO do budget**. O número 180
  sobrevive por um argumento melhor: **25.9 % das reviews levam ≥120 s**,
  logo p95 ≥ 120 por CONTAGEM, logo 1.5× ⟹ ≥180. Gatilho do §3 trocado de
  p95 (inestimável sob censura) para **taxa de censura >5 %**.
  Instrumento versionado junto: `pair-rail-latency.py`.
  **Gate bloqueante antes de landar (§6):** sondar se o harness honra 210 s
  — se matar o hook antes, o modo de falha é fail-open SEM evento, pior
  que hoje.
- **PLAN-162 W1** — testes red-first (agente em execução).
- **RC3-F7** (`upgrade.sh:1776`) e **ADR-164-AMEND-1** (o finding #1 já é
  residual ACEITO no ADR-164 — a medição refuta a premissa "512 paths").

## 4-B. Pair-rail cross-model — 3 rodadas (o Stop-hook exigiu)

Rodei `codex exec review --uncommitted` até parar de achar. **Duas
correções que os 3 lanes do debate não pegaram**, ambas dentro do meu
próprio trabalho:

- **R1/P1 — a classe vacuous-gate tem CAMADAS.** Consertei a regra morta
  (`registered` casava 0 docs); a corrigida passou a casar 5 e ficou com
  cara de viva — enquanto `docs/GUIA-COMPLETO.md:86` ("hooks wired **in**",
  preposição diferente) seguia stale em **44** com 46 vivos. Meu teste de
  liveness novo não pegou: a métrica tinha matches > 0. Corrigido +
  controle positivo (semear 44 ⇒ exit 1; restaurar ⇒ exit 0).
- **R2/P1 — a mitigação de segurança que EU escrevi era defeituosa.**
  O consenso dizia "sentinels rastreados no git **ou** pré-existentes à
  sessão". Derrotável em um comando: o agente escreve o `approved.md` e
  roda `git add` — `ls-files --error-unmatch` passa a chamá-lo tracked.
  E o teste de controle comitava um sentinel criado pelo próprio teste
  afirmando que ele CONCEDE, codificando o bypass como desejado.
  Corrigido: anchor = início da sessão; 3 negativos (untracked / staged /
  committed). Suíte: **19 passed, 24 xfailed, 0 XPASS**.
- **R2/P2 — dois sites de versão mortos de nascença.** `CLAUDE.md` e
  `README.md` nunca tiveram `VERSION=` (`git log -S` confirma), e o
  checklist que escrevi HOJE os anunciava como checados. Removidos +
  liveness estendida à família de versão inteira: site declarado com zero
  matches agora falha como "dead release gate". Controle positivo no
  `INSTALL.md`.
- **R3/P1 — eu quebrei 2 testes e não vi.** Adicionei o gate de liveness
  de versão e **não re-rodei a suíte que o cobre**; as fixtures sintéticas
  não trazem `docs/ARCHITECTURE.md`/`npm/README.md` e o gate falhava
  incondicionalmente. Discriminação correta implementada: doc que EXISTE
  sem o literal = gate morto (falha); doc AUSENTE = site inaplicável
  (pula).
- **R3/P2-1 — o teste era da fixture, não da realidade.**
  `test_claude_md_version_drift_fails` só passava por causa de OUTRAS
  falhas; a regra do `CLAUDE.md` foi escrita para a forma que o
  `_scaffold` injeta. Convertido em teste que fixa a DECISÃO (site não
  gated), de modo que reverter exija flipar o teste.
- **R3/P2-2 — a minha própria lição não estava no código.** Eu escrevi na
  memória "liveness por métrica é piso, controle positivo por SITE é a
  prova" e deixei o código com liveness por métrica. Agora há
  `rule_matches_by_doc` (`metric@doc`) + conjunto de expectativa
  explícito no teste. Controle positivo: mudar a redação de UM doc falha
  por nome (`registered@docs/GUIA-COMPLETO.md`).
- **R3/P2 (3 restantes) — checklist**: sites de versão agora batem com o
  que o verificador lê (5, não os 8 que eu listei); `preflight` leva o
  mesmo seletor `--rc N`/`--stable`; a fase `bump` (que eu tinha omitido)
  voltou — sem ela o `tag()` aborta no próprio check.
- **R1/P1 refutada** (1 de 8): o codex alegou contrato de revisor
  proibindo claim de speedup. Não existe — o único hit no skill é um
  EXEMPLO que inclui "~12% p95 throughput improvement" como anotação
  legítima; o "no speed claim" do CLAUDE.md é sobre a proposta de valor
  do framework, não latência de hook. E o número vive num artefato de
  DEBATE: editá-lo falsificaria o registro.

Disposição completa da R1: `<scratchpad>/pair-rail-r1-disposition.md`.

## 5. Achado P0 que não estava em nenhuma lista

**Bypass por filesystem case-insensitive.** `_match_segments` usa
`fnmatch.fnmatchcase` nos DOIS rails; APFS (default do macOS) não
diferencia caixa. Verificado em primeira mão:

```
                                    canonical  kernel
.claude/settings.json                  True     True
.claude/settings.JSON                 False    False   ← fura os DOIS
.claude/hooks/_lib/audit_emit.PY      False    False   ← fura os DOIS
```

E a escrita via o nome alternativo **sobrescreve o arquivo real**
(reproduzido). Alcança o kernel hard-deny nos arquivos que IMPLEMENTAM a
verificação de assinatura. Entra como FIX P0 no PLAN-162.
