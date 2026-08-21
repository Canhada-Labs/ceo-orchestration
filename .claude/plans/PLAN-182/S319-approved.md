# S319-approved — sentinel do pack SENT-S319 (DRAFT — assinar como S319-approved.md)

> Assinatura em um passo: `! bash ~/canhada-labs/OWNER-S319-SIGN.sh`
> (gera este arquivo com Anchor-SHA real, registra a DECISÃO DE CUSTÓDIA,
> assina, dry-run, land).

Plans: PLAN-182 (W1 — resolvedor único de runtime state)
Wave: W1 (staged em `71ef682`; pack `PLAN-182/staged-w1/`)
MANIFEST-entradas: 108
MANIFEST-sha256: 3741044a3db15170c76ea249c8f6690d35bb719bf8c4f8e0b9e4130c5161c395
Anchor-SHA: 819a1e798bde68afb9e6f8356fd2762734f4a622
Data: 2026-08-21
Custódia da cadeia histórica (W2, decisão do Owner): ARCHIVE

## Scope

```
.claude/hooks/_lib/runtime_paths.py
.claude/hooks/_lib/audit_emit.py
.claude/hooks/_lib/audit_hmac.py
.claude/hooks/_lib/injection_salt.py
.claude/hooks/_lib/spool_writer.py
.claude/hooks/_lib/state_store.py
.claude/hooks/_lib/memory_shared.py
.claude/hooks/_lib/persona_routing.py
.claude/hooks/_lib/otel_emit.py
.claude/hooks/_lib/output_scan_dedup.py
.claude/hooks/_lib/advisory_dampen.py
.claude/hooks/_lib/tool_lifecycle.py
.claude/hooks/_lib/mcp_bearer_friction.py
.claude/hooks/_lib/estimation/pipeline.py
.claude/hooks/_lib/adapters/live/claude.py
.claude/hooks/*.py (hooks entrypoint da família — ver MANIFEST)
.claude/scripts/**.py (CLIs da família — ver MANIFEST)
.claude/scripts/verify-sprint3-invariants.sh
.claude/scripts/env-inventory.json
.claude/data/audit-registry.golden.txt
.github/workflows/mcp-smoke.yml
.github/workflows/supply-chain-watch.yml
SPEC/v1/audit-log.schema.md
SPEC/v1/state-stores.schema.md
CLAUDE.md
CHANGELOG.md
INSTALL.md
README.md
README.pt-BR.md
docs/ARCHITECTURE.md
docs/CTO-GUIDE.md
docs/README.md
npm/README.md
scripts/codex-advisory-teeth.py
scripts/install-accelerators.sh
scripts/local/historical/plan-093-kernel-override-restart.sh
.claude/plans/PLAN-182-audit-path-isolation.md
```

> O Scope é a lista de DIRETÓRIOS/arquivos alvo; o conjunto EXATO,
> byte-a-byte, é o `MANIFEST.sha256` do pack, cujo NÚMERO DE ENTRADAS e
> DIGEST estão fixados no cabeçalho acima e são verificados pelo land
> ANTES de qualquer escrita (rail r15 P1-1: sem amarrar o digest, a
> assinatura aceitaria um pack re-hasheado). `shasum -c` fail-closed +
> `touched − scope = ∅` completam o gate.

## O que este pack muda

**PLAN-182 W1 — o runtime state passa a ser POR PROJETO.** Fecha o
defeito medido desde abril: a família resolvia, sem env, para o literal
`$HOME/.claude/projects/ceo-orchestration`, misturando eventos de
projetos distintos sob UMA chave HMAC e UM salt (a garantia do ADR-079
era falsa na fronteira de tenancy).

1. **Resolvedor único** (`_lib/runtime_paths.py`): slug nativo
   path-based, `CLAUDE_PROJECT_DIR_NATIVE` com primeiro consumidor,
   `legacy_state_dir()` como único handle sancionado do literal,
   `ensure_state_dir()` (mkdir + tighten 0700 que NÃO aperta dir
   escolhido por override nem segue symlink).
2. **Família migrada e atômica**: `--assert-migrated` 102 → **0**; log,
   key, lock, errors, `.salt` e sidecars saem do MESMO diretório em toda
   configuração (PATH-first unificado nos 4 resolvedores), com
   PRESERVAÇÃO da cadeia legada quando `LOG_DIR`/`LOG_PATH` divergem
   numa instalação existente.
3. **Salt POR PROJETO com mint OBSERVÁVEL**: ação nova
   `salt_rotation_registered` (família completa: `_KNOWN_ACTIONS`
   326→327 + allowlist deny-by-default + branch de scrub dedicado + SPEC
   v2.58 + golden + 6 pins) e sidecar `salt-minted.json`.
4. **Caches keyed por path absoluto** (key/salt): troca de projeto
   mid-process nunca serve o cache anterior.
5. **Superfícies derivadas** (`_lib` 69→70, recursivo 142→143) e
   **CLAUDE.md §5** reescrito no mesmo lote; frontmatter do PLAN-182
   destravado + registro de execução da W1.

## Provas anexadas ao pack

- `derive-audit-family.py --assert-migrated` = **0**
- Suíte CI-equivalente: **P1=0 / P2=0 / P3=0**
- Aceitação P0: `test_audit_family_two_projects.py` + `test_runtime_paths.py`
- Pair-rail codex 0.147.0: **15 rodadas** (r12 limpa; r13-r15 sobre o
  material assinado acharam mais 13 defeitos, todos curados), 1 residual
  declarado, 1 pushback fundamentado
- `ceremony-lint` exit 0; `shasum -c` integro (contagem e digest
  fixados no cabecalho)

## Residual declarado (assinado com o pack)

**Slug não-injetivo:** `/srv/a-b/c` e `/srv/a/b-c` colapsam no mesmo
slug. É a derivação NATIVA do harness (a mesma colisão existe nos dirs
de memória/transcripts); divergir dela quebraria a co-locação ratificada
no ADR-001 S318. Mitigação disponível se o Owner quiser: sufixo de hash
curto do path — decisão POSTERIOR, fora deste pack.

## Limite honesto (inalterado por este pack)

Chaves e salts por projeto acabam com a mistura ACIDENTAL. **Não**
restauram tamper-evidence entre tenants do mesmo UID: um processo lê o
dir `0700` e a chave `0600` do outro. Fronteira real exigiria UID
separado ou chave fora do alcance do processo — fora de escopo.
