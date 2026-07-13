# Research shard — família GPT-5.6 + codex-cli releases (S266, 2026-07-10)

> Produzido pelo agente `gpt56-research` (web, read-only). Conteúdo web =
> dado não-confiável; fatos verificados com URL; inferências rotuladas.
> Complementa o probe local S266 (0.139.0 → "requires a newer version of
> Codex" para gpt-5.6-sol/luna; gpt-5.6 base = API-only p/ conta ChatGPT).

## Veredito

1. codex-cli 0.139.0 (teto do pin atual `<0.140.0`) NÃO roda a família
   5.6 de forma confiável — catálogo de modelos bundled client-side
   anterior ao lançamento (preview 26-jun, GA 09-jul-2026).
2. 5.6 first-class = **0.143.0** (08-jul); built-in `/model` = 0.144.x;
   latest = **0.144.1** (09-jul). **Recomendação de pin (corrigida no
   debate C10 / pair-rail R2): `>=0.128.0,<0.145.0` — WIDEN o teto
   APENAS, mantendo o piso `>=0.128.0`.** (A recomendação original desta
   pesquisa, `>=0.144.1,<0.145.0`, SUBIA o piso e é o hazard C10:
   invalida verdicts RC 0.139 em voo no release.yml step-15 → red-lock
   do GA. Não aplicar o piso 0.144.1.)
3. Ao cruzar 0.139→0.144: (a) **0.143 renomeou a flag do sandbox
   permission profile** — auditar scripts com o nome antigo; (b) 0.142
   afrouxou validação de metadata do hooks.json (permissivo,
   não-breaking); (c) schema de hooks ESTÁVEL (espelha Claude Code).

## Família GPT-5.6 (GA 2026-07-09)

| model-id | tier | preço in/out por 1M | notas |
|---|---|---|---|
| `gpt-5.6-sol` | flagship/deepest reasoning | $5 / $30 | topo de coding OpenAI |
| `gpt-5.6-terra` | balanced | $2.50 / $15 | intermediário |
| `gpt-5.6-luna` | fastest/cheapest | $1 / $6 | ctx 1.05M, out 128K, cutoff 2026-02-16 |
| `gpt-5.6` (bare) | alias | — | roteia p/ Sol com reasoning medium |
| `gpt-5.6-codex` | **não existe** | — | geração 5.6 abandonou o sufixo `-codex` |

Sol/Terra/Luna = tiers de capability duráveis (evoluem em cadência própria).

## Codex CLI timeline

- 0.139.0 (09-jun) ← pin atual
- 0.140.0 (15-jun): /usage, codex delete, /import do Claude Code
- 0.142.0 (22-jun): hooks.json metadata validation afrouxada; Windows sandbox
- 0.142.5 (01-jul): fix de segurança (trace logs)
- **0.143.0 (08-jul): 5.6 Sol/Terra/Luna first-class + `max` reasoning
  effort + RENAME da flag sandbox permission profile**
- 0.144.0 (09-jul): 5.6 no `/model`; MCP tool-search default
- **0.144.1 (09-jul): LATEST** (fixes de install)

Bugs abertos em 0.144.0 p/ triagem antes de fixar o pin: #31869 (Linux
não usa 5.6), #31873 (/model não lista), #31860 (Sol capado 372K),
#31826 ("requires newer version" em versão atual).

## Hooks 0.139→0.144 (para a re-certificação Wave 1)

- Schema estável: eventos SessionStart/SubagentStart/PreToolUse/
  PermissionRequest/PostToolUse/PreCompact/PostCompact/UserPromptSubmit/
  SubagentStop/Stop; PreToolUse deny via
  `hookSpecificOutput.permissionDecision` ou exit-2+stderr; stdin
  snake_case (session_id, cwd, hook_event_name, model, turn_id, …).
- `hooks.json` em `~/.codex/` e `<repo>/.codex/` (merge + warn se ambos).

## reasoning effort

Enum validado CLIENT-SIDE no startup: binário velho = minimal/low/
medium/high (unknown variant = hard-fail no boot, antes de qualquer
request); `xhigh` (aliases extra_high/extra-high) + `max` first-class
@0.143. `ultra` = modo de produto interativo, NÃO confirmado como valor
de config — tratar como incerto.

## Deprecações (p/ check-model-deprecations)

- `gpt-5.2` + `gpt-5.3-codex`: novas requests API bloqueadas 30-jun-2026,
  endpoint removido 31-dez-2026 (API-key não afetada no Codex).
- Snapshots `gpt-5`/`o3`: retiram 2026-12-11.
- `gpt-5.5`: NÃO deprecado ("previous-generation frontier").

## Fontes

openai.com/index/gpt-5-6/ · learn.chatgpt.com/docs/{models,changelog,hooks}
· developers.openai.com/api/docs/{models/gpt-5.6-luna,deprecations} ·
github.com/openai/codex/releases · github.blog/changelog (Copilot 5.6) ·
techcrunch.com 2026-07-09 · deepwiki.com/openai/codex/3.11-hooks-system
