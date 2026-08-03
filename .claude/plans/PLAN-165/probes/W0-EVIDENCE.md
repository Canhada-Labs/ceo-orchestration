# W0 — evidência das sondas (2026-08-02, sessão autônoma autorizada pelo Owner)

## Predicado: PASS (T0.1 + T0.2 passam; resíduo documentado abaixo)

## T0.1 — precedência local>project: PASS (nível resolver) + resíduo
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

## T0.3 — guard inventory: ZERO hits
`_CANONICAL_GUARDS` = {team.md, frontend-team.md, pitfalls-catalog.yaml,
skills/{core,frontend}/*/SKILL.md}. Alvos night-mode.py, night-mode.md,
settings.local.json, ceo-boot.py, ADR-185, test_night_mode.py: ZERO hits.

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
