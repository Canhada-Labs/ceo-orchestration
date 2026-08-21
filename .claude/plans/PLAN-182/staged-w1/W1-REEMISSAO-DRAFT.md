# PLAN-182 W1 — Reemissão pós-W0 (DRAFT S319, madrugada 2026-08-21)

> Status: **implementação COMPLETA e provada em clone-sim; land bloqueado
> por 2 decisões do Owner** (custódia W2 + assinatura GPG). O ADR-001
> S318 §4 manda "W2 precedes the W1 re-emission" — este draft cumpre a
> ordem PARAMETRIZANDO a custódia: os dois braços estão escritos; a
> escolha do Owner seleciona o braço, nada é re-implementado.

## O que o pack staged-w1/tree/ contém (103 arquivos, MANIFEST.sha256)

**Núcleo (novo):** `_lib/runtime_paths.py` — O resolvedor único do
ADR-001 S318: slug nativo path-based (`/`→`-`, grafia ATUAL do harness,
single-dash), `CLAUDE_PROJECT_DIR_NATIVE` ganha seu primeiro consumidor
(era spec fiction), `legacy_state_dir()` como ÚNICO handle sancionado do
literal (tooling de migração/W2). Sem cache próprio; symlink honesty
documentada (abspath, não realpath — alinhamento nativo).

**Família curada (delegação, zero re-derivação local):**
- 6 âncoras à mão: `audit_emit` (default + **family-follows-log**: lock
  e errors seguem `CEO_AUDIT_LOG_PATH.parent` — cura do split medido na
  W0-US2), `audit_hmac` (fim da cascata), `injection_salt` (salt POR
  PROJETO + **mint observável**), `spool_writer` (**chave de cache cobre
  TODOS os inputs do resolvedor** — switch de projeto mid-process não
  serve cache velho), `state_store` (`CEO_PROJECT_NAME` vira escape
  explícito, default = resolvedor), `check_anti_ceo_overhead` (bug
  duplo-traço W0-US7 + mkdir 0700).
- Sweep mecânico: ~50 scripts/hooks (import + expressão; py_compile
  gate). 3 grafias divergentes COLAPSADAS em delegação: basename-lowered
  (`memory_shared`), basename puro (`optimizer/fanout`), lstrip+resolve
  (`ceo-cost` — mantém fallback READER sancionado ao legado p/ dado
  pré-migração). CLIs com bootstrap local quando não havia `_lib` no
  path.
- Shell/CI: `verify-sprint3-invariants.sh` e `mcp-smoke.yml` resolvem
  via `python3 -c … runtime_paths`; `supply-chain-watch` e labels OTel/
  SBOM marcados `rp-allow: product-label` (nome do PRODUTO, não path).

**Ação nova registrada:** `salt_rotation_registered` — família COMPLETA
no mesmo lote (lição S318): `_KNOWN_ACTIONS` 326→327 + allowlist
deny-by-default + branch de scrub dedicado (enum fechado
`first_mint|migration_mint|other`; `slug_sha256` 16-hex; slug/path/salt
NUNCA no wire) + SPEC v2.58 (linha de ação + changelog) + golden
regenerado (327) + os 6 pins da família com a cadeia histórica.
Emissor: `injection_salt._register_mint` (lazy, só no mint) + sidecar
`salt-minted.json` como ground truth forense.

**Instrumento:** `derive-audit-family.py` v2 — 3 exceções DOCUMENTADAS
no código (marcador `rp-allow:`; contexto `skills/core/ceo-orchestration`
= nome da skill; donos sancionados: `runtime_paths` + o próprio censo)
+ shape de fixture (`"project": "ceo-orchestration"` em eventos
sintéticos é DADO). **Gate: `--assert-migrated` = 0** (era 102).

**env-inventory** regenerado: 503/503, drift 0 (absorve também as 2
vars do pack S318 que ficaram de fora: `CEO_CEREMONY_LINT_UNLOCK[_REASON]`).

## Prova (clone-sim `git clone --local` de 4c17b24 + pack aplicado)

- `derive-audit-family.py --assert-migrated` → **0** (102 na W0)
- P0 novos: `test_audit_family_two_projects.py` **12/12** — paridade
  dois-projetos com DUAS chaves HMAC + controle negativo comportamental
  (resolvedor-literal colapsa e o oráculo reprova); salts distintos +
  `prompt_sha256` não-correlacionável + controle negativo + HERDEIRO
  preserva bytes; spool switch mid-process; family-follows-log; mint
  observável (marker + reuso não re-registra). `test_runtime_paths.py`
  13/13.
- Famílias dos módulos curados: **803 passed / 0 failed**; pins+registry
  161/161; salt 26/26.
- Suíte COMPLETA como o CI roda (estado FINAL do pack): hooks/tests
  não-serial **6.695 passed / exit 0**; serial **481 passed / exit 0**;
  _lib+scripts+swarm **6.134 passed** — ~13.310 total, 0 failed.
  Ressalva registrada: `test_plan104_demand_resolver::test_waive_scoped_
  to_changed_paths` flakou 1×/3 rodadas sob `-n auto` (verde isolado e
  no arquivo; classe conhecida de carga; arquivo `persona_demand_
  resolver.py` só recebeu alinhamento de call-sites `project=` — pauta
  p/ rail escrutinar).
- O pack final tem **103 arquivos** (MANIFEST.sha256): os 91 da cura +
  superfícies derivadas 69→70/142→143 (3 READMEs, INSTALL, CHANGELOG,
  ARCHITECTURE, CTO-GUIDE, pt-BR, CLAUDE.md §1) + pins/testes flipados
  para o contrato pós-W1 (derive-family ×3 renomeados, circuit-breaker,
  w5 6º pin — achado em hooks/tests, a lição da família DE NOVO) +
  conversão TestEnvContext dos testes novos (higiene 0 violações).

## A custódia W2 — os dois braços (DECISÃO DO OWNER seleciona)

A medição US3 corrobora **"arquivar e recomeçar"**: 45.783 elos
quebrados (15,6%), fork multi-tenant por escritores concorrentes,
re-link impossível — a cadeia histórica é irrecuperável por-tenant.

- **Braço A — ARQUIVAR (recomendado pela medição):** o land move
  `$HOME/.claude/projects/ceo-orchestration/` INTEIRO para
  `…/ceo-orchestration.pre-W1-archive/` (read-only 0500), e ESTE projeto
  nasce limpo no dir slug com salt NOVO (mint registrado
  `migration_mint`) e chave nova. Correlação forense histórica preservada
  NO ARQUIVO (salt legado viaja junto). Nenhum herdeiro do salt.
- **Braço B — HERDAR:** este projeto (ceo-orchestration) é o herdeiro:
  o land COPIA chain+key+`.salt` legados byte-a-byte para o dir slug
  novo; demais projetos cunham salt novo registrado. Mantém continuidade
  `prompt_sha256` deste repo; a mistura estrangeira permanece DENTRO da
  cadeia herdada (imutável, documentada).

Mecânica comum aos dois braços (script de land da cerimônia): criar dir
slug 0700; instalar `.salt`/key conforme braço; `verify_chain()` como
gate pós-migração com controle positivo (chave 0644 ⇒ `perm_error`);
CLAUDE.md §5 + frontmatter do plano curados no MESMO lote.

## CLAUDE.md §5 — texto substituto (mesmo lote do land)

> **Tamper-evidence entre projetos do mesmo `$HOME`: parcialmente
> curado (W1 do PLAN-182, S319) — e PERMANENTEMENTE limitado sob mesmo
> UID.** O runtime state resolve por PROJETO via resolvedor único
> (`_lib/runtime_paths.py`, slug nativo path-based; ADR-001 S318). Fim
> da mistura ACIDENTAL: cadeias que não se entrelaçam, atribuição
> correta, `verify_chain()` significativo por projeto, salt POR PROJETO
> (`prompt_sha256` não correlaciona entre projetos — ADR-079 S318).
> `--assert-migrated` = 0 é gate de CI. O que NÃO muda, antes nem depois
> da migração: sob mesmo UID um processo lê o dir `0700` e a chave
> `0600` do outro projeto — fronteira real exigiria UID separado ou
> chave fora do alcance do processo. A cadeia histórica pré-W1 segue a
> decisão de custódia da W2 (registro no sentinel do land).

## Declarado FORA deste lote (com dono)

1. **Templates** (`templates/scripts/statusline-ceo.py`,
   `templates/{codex,grok}/pre-push-review-gate.sh`) → **W3**
   (installer/adopters; sobreposição PLAN-183 W2 declarada).
2. **F12 dois-locks** (`audit-log.lock` vs `audit-log.jsonl.lock`) →
   W2 (o W1 moveu o DIR de ambos; unificação de convenção é decisão de
   escrita da W2).
3. **Semântica do campo `project`** (46,6% sem rota — US6) → W2
   (emissores remanescentes). Os 5 hardcodes outliers foram alinhados à
   convenção existente (project_dir real).
4. **Testes legados** que citam o literal em fixtures → curados sob
   demanda pela suíte (gate não conta testes); os que quebraram foram
   atualizados no pack.
5. **dist/** não é rastreado (build local) — regenera das fontes curadas.

## Fila para o Owner (manhã)

1. **Custódia W2: braço A ou B** (A recomendado pela medição US3).
2. GPG da cerimônia W1 (sentinel com Scope = MANIFEST.sha256 deste pack).
3. (Item separado, achado da madrugada) eleição ADR-111 do locked-corpus
   é INEXECUTÁVEL — corpus N=0, PLAN-081 nunca entrou neste repo, 0
   eventos `pair_rail_promotion`, probe `run-promotion-gate --dry-run` =
   "MANIFEST not found" exit 1. Opções: autorar 15 fixtures (cerimônia
   própria) / emendar ADR-111 / re-eleger DEFER.
