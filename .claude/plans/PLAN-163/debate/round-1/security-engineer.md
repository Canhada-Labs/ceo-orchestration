---
round: 1
archetype: Security Engineer
skill: security-and-auth
generated_at: 2026-07-27T00:00:00Z
---

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- O plano reconcilia a janela 2.1.199–2.1.220 com disciplina correta (red-first,
  cerimônia única, pin conservador de nesting) e a maioria das claims que
  spot-verifiquei SEGURA (VETO_FLOOR_ALLOWED em `agent_frontmatter.py:135-138`;
  payload do spawn guard em `check_agent_spawn.py:374-376`; independência de
  `mode` — zero hits de `permission_mode` nos hooks; 46 registrations
  confirmadas: 47 × `"type": "command"` − 1 `statusLine` em settings.json:880).
- Forte: T2 oracle allow+block, T3 fechar o buraco do /add-dir, OQ3 pin=1.
  Fraco: duas premissas factuais falham (G5 diz "nenhuma menção a depth>1 nos
  guards" — o Rail 2 depth-fence EXISTE em `check_agent_spawn.py:1535-1539,
  1662-1684, 1822-1833`; e são **13** event types no settings.json, não 14),
  e T5 trata o bump do pin codex como re-record de números quando o mecanismo
  de atestação em si está furado (ver R-SEC1).
- A descoberta mais grave desta crítica é PRÉ-EXISTENTE (não introduzida pelo
  plano), mas o T5 é o lugar certo de consertá-la — por isso ADJUST e não
  REJECT. **VETO não exercido** (nenhum item do plano é regressão dura; o
  plano melhora a postura em G4/G7/G13 se os must-fix entrarem).

## Risks

1. **R-SEC1 — HIGH — sha-pin do codex atesta o launcher, não o payload (T5/G13).**
   `/opt/homebrew/bin/codex` é symlink para
   `@openai/codex/bin/codex.js` — um entrypoint Node estável entre versões
   ("Unified entry point... spawn") que despacha o binário nativo real.
   `codex-cli-binary-sha256.txt` (que se autodenomina "the real supply-chain
   gate") pinna `134063e1...` = sha do LAUNCHER; verifiquei que o binário
   instalado HOJE (0.144.6, symlink mtime 2026-07-20) tem o MESMO sha do pin
   registrado na cerimônia S269 quando o instalado era 0.144.1. Ou seja: o
   upgrade 0.144.1→0.144.6 passou pelo gate sem cerimônia e sem nenhum sinal —
   e um payload adulterado em `node_modules/@openai/codex/` (fora do codex.js)
   também passaria. O V2 do verification cascade (pair-rail, único LLM truth
   gate) roda hoje sobre código não-atestado. O semver-range
   (`>=0.128.0,<0.145.0`) também já admite 0.144.6, então nenhum dos dois
   rails do pin viu o bump. Mitigação: T5 deve emendar ADR-111 para atestar o
   payload RESOLVIDO (sha do binário nativo por-arch que o launcher spawna,
   ou manifest-hash do pacote npm — tarball integrity/`npm pack` sha), não o
   `$(which codex)` pós-symlink; re-record de fixtures continua válido.
2. **R-SEC2 — HIGH — G7 audit-only default deixa a superfície user-scope
   atacável (T3).** `/add-dir` expande o perímetro de escrita mid-session. Os
   guards canônicos são relativos a `CLAUDE_PROJECT_DIR`; um diretório
   adicionado FORA do projeto (ex.: `$HOME`) expõe `~/.claude/settings.json`
   (settings user-scope: permissions, hooks adicionais, env) a Write/Edit sem
   nenhuma pilha canonical-guard e fora do perímetro HMAC-auditado. Cadeia:
   conteúdo injetado convence o agente a adicionar `$HOME` (ou usa a tool
   SlashCommand, se disponível no 2.1.220) → escrita em config user-scope →
   persistência entre sessões. Audit-only registra o furo; não o fecha.
   Mitigação: hardblock-FLOOR por política de roots sensíveis (raiz de
   `$HOME`, `~/.claude/`, qualquer dir contendo `.claude/` de outro repo,
   ancestrais do project dir) mesmo com `CEO_DIRADD_HARDBLOCK` desligado;
   audit-only para o resto; e neste repo (dogfood) ligar o hardblock.
3. **R-SEC3 — MEDIUM — pin de nesting pode ser no-op silencioso (T4/OQ3).**
   `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` NÃO está entre as 4 claims
   verificadas verbatim no CHANGELOG. Env var com nome/semântica errada =
   acreditar que está pinnado sem estar (fail-open por typo — classe já vista
   no repo). Mitigação: o Check de T4 deve exigir probe red-first que PROVA a
   negação (com o pin setado, spawn aninhado é negado; sem o pin, probe
   detecta a mudança de comportamento), não apenas "env pin presente no pack".
4. **R-SEC4 — MEDIUM — premissa do G5 falsa; cobertura do guard em depth≥2 é
   desconhecida, não ausente-por-omissão.** O Rail 2 depth-fence existe mas é
   (a) advisory-by-default (`CEO_SPAWN_DEPTH_GUARD`), e (b) alimentado por
   sinais COOPERATIVOS (marker `## SUBAGENT-CONTEXT depth=N` injetado pelo
   CEO + env `CEO_SPAWN_DEPTH`) — o payload do harness não tem campo nativo
   de depth (`check_agent_spawn.py:1536`). Nesting NATIVO do harness não
   carrega nenhum dos dois sinais → o rail não vê depth-2 real. Além disso,
   não há evidência de que PreToolUse dispara para Task calls emitidos DENTRO
   de um subagente (se não dispara, nem os rails de skill-content gateiam o
   neto). Mitigação: o probe de OQ3 precisa cobrir as duas perguntas
   (hook-fires-at-depth-2? sinais-de-depth-presentes?) e o plano deve citar o
   Rail 2 existente em vez de "nenhuma menção".
5. **R-SEC5 — MEDIUM — G4: o oracle como especificado não cobre a classe real
   de block espúrio.** Verifiquei: nenhum hook top-level usa `sys.exit(2)` —
   os blocks intencionais são stdout-JSON com exit 0 (confirmado AO VIVO no
   2.1.220 instalado: `check_bash_safety` bloqueou um `python3 -c` meu durante
   esta crítica). Logo o fix 2.1.214 não ameaça os caminhos de block
   intencionais; a superfície nova é **exit-2 ACIDENTAL**: 3 hooks wired
   importam argparse (`check_harness_config.py`, `emit_architect_outcome.py`,
   `policy_dispatch.py`) e argparse chama `sys.exit(2)` em erro de argv —
   drift de wiring/template agora vira hard-block de sessão, violando o
   fail-open-on-infrastructure do CLAUDE.md §5. Mitigação: T2 oracle deve
   assertar EXIT CODES (allow=0) além de schema, incluir caso sintético de
   argv inesperado para os 3 hooks argparse, e o fix é capturar SystemExit →
   emitir `{}`.
6. **R-SEC6 — LOW — drift de contagem dentro do próprio plano.** São 13 event
   types no `hooks` de settings.json (linhas 130-691), não 14 (G4/G7); e o
   Check de T3 diz "hook_live_smoke passa a reportar 46/46" após um 46→48 —
   inconsistente. Exatamente a classe verify-counts que este repo já tomou
   red por duas vezes.
7. **R-SEC7 — LOW — crescimento do VETO floor sem sunset (T1/OQ1).** ADR-149
   é aditivo com janela N-1 intencional; += opus-5 deixa {opus-4-8, fable-5,
   opus-5} — N-2 de fato, sem critério de saída para opus-4-8. E
   `test_veto_floor_bijection.py` valida FRONTMATTER, não o caminho de
   runtime-fallback: se OQ1(b) mexe em `fallbackModel`, nada prova que um
   fallback em contexto de VETO-role permanece ⊆ VETO_FLOOR_ALLOWED.

## Must-fix (blocking)

1. **T5:** reescrever o item do pin codex para consertar o MECANISMO de
   atestação (sha do payload resolvido por-arch ou manifest-hash do pacote,
   via emenda ADR-111), não só re-record dos números; corrigir a narrativa
   (o semver-range já cobre 0.144.6; o que está stale é o ledger e a
   caracterização — e o sha-pin atual é vácuo por construção). Evidência:
   sha idêntico pré/pós upgrade 0.144.1→0.144.6.
2. **T3:** política de hardblock-floor para roots sensíveis no
   `check_directory_added.py` (raiz de `$HOME`, `~/.claude/`, `.claude/` de
   repo alheio, ancestrais do project dir) independente do env opt-in;
   dogfood settings deste repo com `CEO_DIRADD_HARDBLOCK=1`; e probe
   red-first verificando ANTES se o evento `DirectoryAdded` aceita decisão de
   block — se for notification-only, mover o enforcement para os guards
   PreToolUse de escrita (deny de Write/Edit sob roots adicionados
   mid-session não-allowlisted), que funciona independente da semântica do
   evento.
3. **T4/OQ3:** o Check passa a exigir probe de NEGAÇÃO comprovada do pin
   (nome+semântica do env var verificados contra o binário 2.1.220) e probe
   de cobertura do spawn-guard em depth-2 (hook dispara? sinais presentes?).
   Corrigir a premissa do G5 citando o Rail 2 existente
   (`check_agent_spawn.py:1822-1833`, advisory, sinais cooperativos).
4. **T2:** estender o oracle `hook-stdout-schema-check` para assertar exit
   codes e incluir o caso argv-inesperado dos 3 hooks argparse; fix
   SystemExit→`{}` nesses hooks (doutrina fail-open on infrastructure).
5. **Counts:** corrigir 14→13 event types (G4/G7) e o Check de T3 (48/48 ou
   recontagem explícita) antes de `draft`→`reviewed`.

## Nice-to-have (advisory)

1. Probe advisory de sha por-invocação no rail vivo (hoje o sha só é checado
   em release.yml step-15 + pair-rail-gate.sh preflight — janela entre
   upgrades locais e cerimônias fica sem sinal).
2. ADR-181: critério de sunset para `claude-opus-4-8` no VETO floor (evento:
   pós-migração provada, não data — ADR-095) + nota de que fallback runtime
   não é coberto pela bijeção de floor.
3. Documentar no T4 ADR de doutrina se a tool SlashCommand existe/está
   habilitada no 2.1.220 (muda o modelo de ameaça do G7 de "só humano" para
   "agente pode invocar /add-dir").
4. G1 STALE_RE += `claude-opus-4-1` no smoke-install-parity: promover de
   "avaliar" para fazer — retirement 2026-08-05 é antes do horizonte do plano.
5. OQ5: além de expor comentado nos templates, ligar
   `sandbox.network.strictAllowlist`/`disableAutoMode` NESTE repo (dogfood
   fail-closed; adotantes decidem por si).

## Unseen by the original plan

1. **Launcher-vs-payload no sha-pin** (R-SEC1) — o plano herda a claim "the
   real supply-chain gate" do pin file sem verificar o que o sha cobre.
2. **Hooks dispararem (ou não) para tool calls de subagentes** é a premissa
   silenciosa de TODA a governança sob nesting nativo — o plano trata depth
   como questão de cap, não de cobertura de observação (R-SEC4).
3. **Caminho de runtime-fallback vs VETO floor**: a bijeção testa frontmatter;
   `fallbackModel` global pode rebaixar um VETO-role em degradação de serviço
   sem tripwire (R-SEC7).
4. **Perímetro user-scope (`~/.claude/`) fica fora do HMAC-audit por
   construção** — /add-dir é UMA porta para ele; o plano fecha a porta mas
   não nomeia o ativo que ela protege (útil para o ADR do T3 dimensionar a
   política de roots).
5. **`Notification` como input não-confiável**: o wiring de T3 vai consumir
   payloads derivados de conteúdo de agente (agent_needs_input); o hook deve
   seguir no-value-echo (nomes/enums no audit, nunca corpo de mensagem) — vale
   uma linha no plano para não nascer com echo.

## What I would NOT change

- **Pin=1 como default de nesting (OQ3 draft)** — fail-closed correto; depth-3
  sem probe de cobertura seria adotar capacidade antes de governança.
- **Red-first em T2/T4** ("o número decide, não a vontade") e a re-extração de
  schema do binário com diff por campo — é o método que pegou drift real em
  2026-07.
- **Fable-5 permanecer o teto dos VETO roles** com opus-5 entrando como
  membro do floor, não como teto (OQ1 draft) — consistente com ADR-149.
- **OQ2 draft**: permitir sonnet-5 já, migrar default advisory só pós
  re-baseline do tokenizer — budgets tokenizados são rail de custo/segurança.
- **OQ4 draft**: NÃO adotar agent-teams/SendMessage — governança de
  peer-messages (spoofing entre teammates, autoridade de mensagens) não está
  modelada; documentar a postura é o certo.
- **Cerimônia única W3 no padrão PLAN-160/161** com pair-rail APPROVE — o
  caminho que vem pegando bugs reais de primeiro draft (3 confirmações).
