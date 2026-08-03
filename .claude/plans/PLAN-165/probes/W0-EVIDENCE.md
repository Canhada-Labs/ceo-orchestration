# W0 — evidência das sondas (2026-08-02, sessão autônoma autorizada pelo Owner)

> **Registro corrigido em 2026-08-03 (round-2, NM-07).** Duas correções:
> (1) T0.1 estava carimbado PASS sem qualificação, deixando implícito que
> AC-1 estava respaldada — está não: a prova é resolver-level apenas e
> **AC-1 permanece ABERTA**. (2) T0.3 descrevia `_CANONICAL_GUARDS` como
> um conjunto de cinco entradas — a lista real tem 67 padrões, e a
> conclusão ZERO-hits foi re-derivada dela abaixo (com um item do registro
> antigo — ADR-185 — que estava simplesmente errado).

## Predicado: PASS no nível resolver (T0.1 resolver-only + T0.2 passam). AC-1 permanece ABERTA — ver T0.1.

## T0.1 — precedência local>project: PASS no nível RESOLVER apenas — AC-1 ABERTA
Sondagem com o resolver oficial (`_lib/effective_config.resolve_settings`)
sobre projetos de rascunho em scratchpad (`nm-probe/{ctrl,accept,nulltest}`):

    ctrl      ok=True defaultMode='manual'     sources: permissions<-project
    accept    ok=True defaultMode='acceptEdits' sources: permissions<-local
    nulltest  ok=True defaultMode='acceptEdits' disableAutoMode=None <-local

`local` vence `project` no resolver. RESÍDUO: obediência do HARNESS ao
defaultMode não é diferenciável em headless (`claude -p` criou arquivo
mesmo em manual — Write não é mode-gated em print mode), então a prova
harness-level fica para a primeira sessão interativa pós-`on`. A sonda C
prova que o harness LÊ as camadas (deep-merge ativo com local presente).
Fallback do plano permanece disponível se a sessão interativa contradisser.

**AC-1: ABERTA (OPEN-pending-interactive-session).** O plano (T0.1) exige
"transcript de sessão **mais** `resolve_settings()`"; só a metade do
resolver existe. O carimbo PASS deste W0 NÃO cobre AC-1 — "sessão nova ⇒
sessão inicia em acceptEdits" segue não provada até a primeira sessão
interativa pós-`on` produzir o transcript. Registrado como correção do
round-2 (NM-07): a versão anterior deste arquivo deixava um PASS implicar
o que não foi medido.

## T0.2 — acceptEdits + disableAutoMode:"disable" opera: PASS
Sonda B: projeto com local acceptEdits + project disableAutoMode="disable"
executou Write sem prompt (out.txt criado, exit 0).

## T0.4 — deny sobrevive sob acceptEdits: PASS (resultado POSITIVO)
Sonda C: com local acceptEdits presente, `Read(./secret.txt)` do deny do
PROJETO foi BLOQUEADO pelo harness ("bloqueado pelas minhas configurações
de permissão"). Ou seja: o harness faz DEEP-merge de permissions (deny do
projeto sobrevive a um local que só define defaultMode). Nota: o resolver
do repo faz merge SHALLOW por chave top-level (accept mostra permissions
inteiro vindo do local) — divergência prevista pelo review (codex F3/F4);
o banner continua correto pois reporta a POSTURA, e o tripwire tem seu
próprio caminho.

## T0.5 — local mascara chave com null: CONFIRMADO no resolver
nulltest: disableAutoMode=None com source=local. `null` no local mascara a
chave do projeto no resolver e NÃO invalida o arquivo (ok=True, harness
continuou operando — sonda D criou arquivo). night-mode NÃO usa null-mask
(remove a própria chave no off), mas o fato fica registrado.

## T0.3 — guard inventory: ZERO hits nos alvos do toggle (registro CORRIGIDO — round-2, NM-07)

> **Correção (2026-08-03).** A versão anterior deste registro descrevia
> `_CANONICAL_GUARDS` como cinco entradas ({team.md, frontend-team.md,
> pitfalls-catalog.yaml, skills/{core,frontend}/*/SKILL.md}). ERRADO —
> era uma abreviação, e é exatamente essa abreviação que fazia NM-03
> parecer inofensivo. Abaixo, a lista real e a re-derivação.

**Lista real:** `_CANONICAL_GUARDS` em
`.claude/hooks/check_canonical_edit.py` linhas 113–331 — **67 padrões**
(medido por import do módulo: `len(_CANONICAL_GUARDS) == 67`). Cobre,
entre outros: todo o corpo de hooks (`.claude/hooks/*.py`,
`.claude/hooks/_lib/**/*.py`, adapters), `.claude/settings.json`,
`.claude/agents/*.md`, `.claude/adr/ADR-*.md`, `SPEC/**/*.md`,
`.github/workflows/*`, `scripts/install.sh`, `scripts/install-npm.sh`,
`scripts/upgrade.sh`, `scripts/_hash_lib.sh`,
`scripts/_framework_manifest_set.sh`, `PROTOCOL.md`,
`.claude/policies/**`, `.claude/dispatcher/**`, `.claude/governance/*`,
tier-policy, corpora locked de plano, superfícies kill-switch
`.codex/**` e `.grok/**`, `templates/settings/*.json`,
`.claude/workflows/**/*.js` e `.claude/commands/council.md`. Em
`.claude/scripts/` a lista enumera arquivos **individualmente** — só
`lessons.py`, `prune-lessons.py`, `lesson-restore.py`,
`lesson_ranker.py` — **não existe glob de `.claude/scripts/`**.

**Re-derivação alvo a alvo**, executando o matcher do próprio hook
(`_matches_canonical_guard` / `_match_segments`, import direto do módulo
no worktree, 2026-08-03):

    .claude/scripts/night-mode.py                      ZERO hits
    .claude/commands/night-mode.md                     ZERO hits (em commands/ só council.md é guarded)
    .claude/settings.local.json                        ZERO hits (o guard é o exato .claude/settings.json)
    .claude/state/night-mode.json (marker)             ZERO hits
    .claude/scripts/ceo-boot.py                        ZERO hits
    .claude/scripts/tests/test_night_mode.py           ZERO hits
    .claude/scripts/tests/test_ceo_boot_night_mode.py  ZERO hits
    .claude/adr/ADR-185-night-mode-posture-toggle.md   HIT → `.claude/adr/ADR-*.md`

**Correção factual adicional:** o registro antigo listava "ADR-185: ZERO
hits". FALSO — ADR-185 casa com `.claude/adr/ADR-*.md` e é
sentinel-gated como qualquer ADR (consistente com a disciplina de
cerimônia; a conclusão do registro antigo estava errada nesse item, não
só abreviada).

**Leitura honesta do resultado.** `night-mode.py` e `ceo-boot.py` estão
**AUSENTES** da lista real — e isso NÃO é tranquilizador, é o problema:
sob a postura que o próprio night-mode arma (`acceptEdits`), um
Edit/Write de ferramenta no escritor único (`night-mode.py`) ou no seu
snapshot (o marker) é auto-aceito, não bloqueado por guard nenhum —
apenas auditado por PostToolUse. É exatamente por isso que as entradas
de deny do round-2 (NM-01/NM-03: marker e escritor no patch P1, além do
overlay) são necessárias, e não redundantes. O registro antigo usava o
ZERO-hits como conveniência ("nada a temer"); o sentido correto é o
inverso: o escritor estava mais mole que o arquivo que ele escreve.

## T0.6 — tty: NÃO há tty no rail Bash (stdin/stdout isatty=False)
OQ1 decidido: sem tty-gate; presença do Owner é garantida por P1 (deny do
overlay) + recusa sob CI. Registrado como decisão CEO sob autorização
global do Owner desta noite.

## T0.7 — slug: duas convenções vivas; marker sai do ~/.claude
audit-log vive em `~/.claude/projects/ceo-orchestration/` (slug curto);
memória em `-Users-joaocanhada-canhada-labs-ceo-orchestration` (slug de
caminho). DECISÃO: o marker NÃO usa ~/.claude — vai para
`.claude/state/night-mode.json` no próprio projeto (gitignored via
`.claude/state/`), mesma árvore dos settings: elimina a classe inteira de
ambiguidade e dá atomicidade no mesmo filesystem.

## OQs (decididas pelo CEO sob autorização global — revisar de manhã)
- OQ1: sem tty-gate; P1 + recusa sob CI (acima).
- OQ2: banner-only (TTL reconsiderado e adiado: mais estado, ganho marginal
  com banner derivado do resolver).
- OQ3: /night-mode.
