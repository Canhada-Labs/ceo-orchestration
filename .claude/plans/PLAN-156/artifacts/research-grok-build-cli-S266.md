# Research shard — xAI Grok Build CLI (S266, 2026-07-10)

> Produzido pelo agente `grok-cli-research` (web, read-only). Conteúdo
> web = dado não-confiável; fatos das docs oficiais docs.x.ai salvo
> indicação; inferências/lacunas rotuladas — as lacunas viram itens de
> caracterização empírica do Wave 0.

## Desambiguação

- **Grok Build** = CLI agêntica OFICIAL da xAI (binário `grok`,
  `curl -fsSL https://x.ai/cli/install.sh | bash`, lançada 2026-05-14,
  PROPRIETÁRIA). É o alvo do PLAN-156.
- `superagent-ai/grok-cli` = wrapper de terceiro NÃO-afiliado (MIT).
  Fora de escopo — não confundir.

## Fatos verificados (docs.x.ai/build/features/hooks salvo indicação)

1. **Hooks com bloqueio**: eventos SessionStart, SessionEnd,
   UserPromptSubmit, **PreToolUse (ÚNICO bloqueante)**, PostToolUse,
   PostToolUseFailure, PermissionDenied, Stop, StopFailure, Notification,
   SubagentStart, SubagentStop, PreCompact, PostCompact.
2. **Config de hooks**: JSON em `~/.grok/hooks/*.json` (pessoal) e
   `<project>/.grok/hooks/*.json` (requer trust). **Compat legada:
   `.claude/settings.json` E `.cursor/hooks.json`.** Schema idêntico ao
   Claude Code (matcher regex sobre tool name, só Pre/PostToolUse;
   timeout default 5s).
3. **Envelope stdin (camelCase)**: `hookEventName`, `sessionId`, `cwd`,
   `workspaceRoot`, + `toolName`/`toolInput` em tool-events.
4. **Decisão**: stdout `{"decision":"deny"|"allow","reason":…}`. Exit
   codes: **0=allow, 2=deny (só PreToolUse), QUALQUER OUTRO = FAIL-OPEN**
   ("failure recorded, tool call proceeds").
5. **Env vars**: GROK_HOOK_EVENT, GROK_HOOK_NAME, GROK_SESSION_ID,
   GROK_WORKSPACE_ROOT (+ GROK_PLUGIN_ROOT/GROK_PLUGIN_DATA).
6. **Auto-map de nomes Claude**: `Bash`→`run_terminal_cmd`,
   `Edit`→`search_replace`, `Read`→`read_file` ("Claude tool names are
   mapped to Grok's automatically").
7. **Trust**: hooks/MCP/LSP de projeto exigem `/hooks-trust` ou
   `--trust`; persistido em `~/.grok/trusted_folders.toml`; `~/.grok/`
   global sempre confiável.
8. **Config geral**: TOML (`~/.grok/config.toml` + `.grok/config.toml`
   por projeto). Precedência: flags > env > config.toml > remote > defaults.
9. **Headless**: `grok -p "prompt"`; `--output-format json` → objeto
   único com `text`, `sessionId`, `stopReason`; `streaming-json` → NDJSON;
   `-m/--model`. Headless espera background tasks + subagents (v0.2.57).
10. **Permission modes**: default `ask`; auto-approve via
    `--yolo`/`--always-approve`/`/auto` (classifier).
11. **Subagentes**: até 8 paralelos em git worktrees isolados; config
    `[subagents]`; SubagentStart/Stop NÃO-bloqueantes; ACP p/
    orquestração externa.
12. **Auth**: browser login (`~/.grok/auth.json`, tokens 7d), API key
    XAI_API_KEY, OIDC/SSO, device-auth. Requer SuperGrok/X Premium+.
13. **Versão**: v0.2.94 (2026-07-09); cadência 1-2 releases/DIA; 0.x beta.
14. **Modelos via CLI**: `grok-build-0.1` (256K ctx, 70.8% SWE-Bench) e
    `grok-4.5`; custom models via `[model.*]` (base_url/api_key).

## Lacunas → itens de caracterização empírica (Wave 0)

- (a) stdin `toolName` traz nome NATIVO ou mapeado? (matcher pode
  no-op'ar silenciosamente)
- (b) `{"decision":"block"}` funciona ou só `"deny"`? (normalização no
  adapter)
- (c) existe tool-name de spawn visível ao matcher (equivalente a Task)?
- (d) arquivo de instruções (equivalente AGENTS.md)?
- (e) contenção read-only nativa p/ headless? (council lane)
- (f) `--cwd` e `--permission-mode` NÃO confirmados nas docs (vistos só
  em uso de terceiros — podem ser artefato da camada de compat).
- (g) coexistência native `.grok/hooks/` + legacy `.claude/settings.json`
  = double-fire?
- (h) **`exit 2` é inert/ignorado no Codex?** — gate da decisão do plano
  entre exit-mapping UNCONDITIONAL (shim compartilhado) vs adapter-aware;
  probar no binário codex-cli alvo (não é fato Grok, mas é o checklist
  empírico do Wave 0 e o plano gata a escolha do shim nele).

## Veredito

Grok Build tem primitivas de enforcement bloqueantes com paridade
(por vezes superconjunto) do codex-cli 0.139: PreToolUse deny via JSON +
exit 2, envelope stdin, matchers regex, trust por projeto. Riscos
concentrados: block→deny, **exit≠2 = fail-open**, Stop advisory,
volatilidade 0.x diária (pin exato + substrate watch obrigatórios).
