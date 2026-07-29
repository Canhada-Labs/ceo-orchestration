# PLAN-163 — PROBES DIGEST (S284, 2026-07-28)

Consolidação dos artefatos de probe em `.claude/plans/PLAN-163/probes/`.
Todos os probes foram read-only sobre paths canônicos; escrita confinada a
`probes/` + scratchpad. Este digest é EVIDÊNCIA, não autorização (V0–V3 intactos).

## Tabela probe × status × verdict × artefatos

| Probe | Plano | Status | Verdict (1 linha) | Artefatos (probes/) |
|---|---|---|---|---|
| G16 model-probe | G16 | done | `self-id=claude-fable-5` (não opus apesar de opts.model='opus'); CC 2.1.220 | `g16-model-probe.md` |
| flock-2.1.220 | T4.1 | done | `cap-rec=split` — read-only fan-out sobe p/ 8; staging (git index) mantém 6; N=12 não certificado | `flock-2.1.220.md` (+ scratchpad: `flock_bench.py`, `flock_bench_results.json`, variante fsync) |
| SCHEMA-EXTRACT | T2.2 (alimenta T1.1/CF-6 e T3.1) | done | `enforceAM` idêntico a 2.1.202; managed-policy fail-open INALTERADO; unknown-key=tolera (delete+warning); DirectoryAdded novo e PÓS-facto | `hook-schema-2.1.220.json`, `schema-diff-2.1.202-to-2.1.220.md` |
| DIRADD-blockability | T3.1 (HARD GATE CF-9) | done | `diradd=notification-only; post-facto-window=reads+writes` — `decision:block` estruturalmente ignorado | `diradd-blockability.md` |
| PAYLOAD-SHA | T5.2a/b | done | `payload=80a3933d; launcher=134063e1; triple=aarch64-apple-darwin` — pin atual atesta o LAUNCHER, não o payload (T5.2a confirmado) | `pin-manifest-draft.json`, `payload-sha-evidence.md` |
| depth-probes | T4.3 (OQ3) | done | `env-verbatim=sim; negação=funciona; hook-depth2=cobre` — pin=1 remove Task/Agent do roster do depth-1 | `depth-probes.md` |
| LEDGER-refresh | T5.1 | done (1 item PENDING-OWNER) | Draft de bump pronto: CC 2.1.220, sdk-ts 0.3.220, sdk-py 0.2.128, codex 0.144.6, grok 0.2.106; model-deprecations refresh = receita Owner-run | `ledger-refresh-draft.md` |
| MISC (G6/G9/field-drop) | G6, G9, S284 drift | done | G6=assunção morta (guard não lê `mode` do Task); G9=dormente (pair-rail é CLI, não MCP); field-drop = scrub deny-by-default funcionando como projetado | `misc-probes.md` |

## Decisões alimentadas (resultado → item do plano destravado)

- **T1.1 / CF-6 ← enforceAM** (SCHEMA-EXTRACT): `enforceAvailableModels` em 2.1.220 é idêntico a 2.1.202; resolução itera `availableModels` EM ORDEM — a 1ª entrada allowed+server-available vira o Default ⇒ **ordem do pin T5.4 é load-bearing**. Sem sobrevivente = mantém tier default (fail-open). Managed-policy fail-open ("refusing cascade-trust mode") EXISTE INALTERADO ⇒ contingência T1.1 (pin explícito de default de sessão no mesmo commit) MANTIDA como pré-condição. Novo em 2.1.220: entitlement `model_access` como 2ª fonte de restrição.
- **T3.1 ← diradd** (SCHEMA-EXTRACT + diradd-blockability): DirectoryAdded é PÓS-facto (mutação aplicada ANTES; hook fire-and-forget, sem arm em hookSpecificOutput; `decision:block` ignorado). Janela pós-facto expõe **reads E writes** já vivos antes de qualquer observer ⇒ ramo hardblock-floor de T3.1 está MORTO neste substrato — usar **observer-WRITER + write-guards PreToolUse**, e o CF-9 fallback só-escrita (finding S283) é a exposição real a mitigar.
- **T4.1 ← flock**: blow-up original do PLAN-083 NÃO reproduz (flock p95 ≤0.07ms até N=8; joelho só em N=12); git index é o único mecanismo com tail e só exercitado por staging ⇒ **SPLIT: fan-out read-only N≤8, fan-out que toca índice git N≤6**. Edit futuro de `parallelization-by-default/SKILL.md` é canônico (rail SP-NNN/sentinel citando este probe). NO-SPEED-CLAIM mantido.
- **T4.3 ← depth**: `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` existe verbatim no binário (5×); pin=1 nega nível-2 por **remoção de tool do roster** (não por mensagem de erro); hook `matcher:"*"` cobre depth≥1 e calls de subagente carregam `agent_id`+`agent_type` como discriminador ⇒ OQ3 draft (pin=1) viável e observável.
- **T5.2 ← payload-sha**: pin atual (`codex-cli-binary-sha256.txt`) = sha do launcher `bin/codex.js` (134063e1…), byte-idêntico sob 0.144.1→0.144.6 ⇒ bump de payload nativo passou SEM gate (T5.2a confirmado). Manifest draft por-triple no schema do plano pronto (`pin-manifest-draft.json`, payload 80a3933d…, npm_integrity capturado) ⇒ destrava verify-then-invoke do MESMO path + ADR novo.
- **T5.1 ← ledger**: valores frescos coletados para as 6 componentes do substrate-watch (incl. grok 0.2.106 sha 7229f5e2…, confirmando drift vs pin 0.2.93); diff unificado draft pronto; semântica codex_harness `last_seen` documentada (bump condicionado a runbook de fixtures, T5.4 decide).
- **T2.2 ← schema**: enum de eventos 30→31 (só +DirectoryAdded); nenhum campo removido/re-tipado; UserPromptSubmit +`source?`; SessionStart +`fork`; Notification idêntico e seguro para wire ≥2.1.202; unknown-key tolerado em AMBAS as versões (delete + warning, nunca rejeição whole-file) ⇒ emissão em templates segue FEATURE-GATED (piso <2.1.202 não sondado — residual T3.4).
- **G16** confirma substrato de execução dos workflows: self-id `claude-fable-5` mesmo com `opts.model='opus'` — prova definitiva via campo model do journal (orquestrador).
- **G6/G9** (misc): duas assunções do gap-matrix descartadas com prova — nenhum retrabalho de guard necessário.

## Bloqueios / residuais

- **Nenhum probe blocked ou partial** — 8/8 done.
- **PENDING-OWNER (T5.1):** refresh de `model-deprecations.json` (`_meta.fetched` 2026-06-12, 46d stale) exige fetch de rede Owner-run — receita completa em `ledger-refresh-draft.md`; agentes no-network para ledgers canônicos (ADR-136-AMEND-1).
- **Residual T3.4:** piso de versão <2.1.202 para unknown-key tolerance não sondado (recipe barata documentada no schema-diff) — emissão em templates permanece feature-gated.
- **N=12 não certificado** (T4.1): joelho de contenção no flock + host não-idle durante a medição; recomendação limitada a 8/6.
- **GATE-V2 (do stop-review S283):** prova de expiração ≈08-03 NÃO satisfaz — exigir prova FRESCA sob pin novo, ordem GATE-PIN→GATE-V2→W3 (fora do escopo destes probes; registrado para o executor).
