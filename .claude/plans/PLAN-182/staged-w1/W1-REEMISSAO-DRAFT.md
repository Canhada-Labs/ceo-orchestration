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

## Rail codex r1 (S319 madrugada) — 6 achados, 5 curados, 1 pushback fundamentado

| # | Achado | Disposição |
|---|---|---|
| P1-1 | ceo-cost `parents[2]` → CLI standalone quebrado | **CURADO** (`parents[1]`; prova de vida standalone) |
| P1-2 | locks divergentes: audit_emit seguia o log movido, spool_writer/audit_log não | **CURADO** — family-follows-log nos 3 escritores (mesma derivação `resolve().parent`) + asserts de paridade dos 3 no teste P0 |
| P1-3 | "archive/custódia antes do writer switch ausente do patch" | **PUSHBACK fundamentado**: por DESIGN o pack é staged e NÃO executa migração — a custódia é decisão do Owner (W2) e a migração roda NO SCRIPT DE LAND da cerimônia, na ordem (1) archive/custódia → (2) aplicar tree/ → (3) `verify_chain()` gate. O plano (§W2) e este draft já o exigem; ordem agora EXPLÍCITA abaixo |
| P1-4 | import top-level de runtime_paths viola fail-open do hook em partial upgrade | **CURADO** — guard + `_rp_state_dir()` com fallback legado marcado `rp-allow: partial-upgrade-fallback` + stderr, nos 11 hooks entrypoint (1ª aplicação criou recursão no corpo do guard — pega pela suite, des-recursada, 154/154) |
| P2-5 | `<native-slug>` LITERAL em string de código (cc-analytics) | **CURADO** — derivação real via resolvedor + prova de vida; varredura confirmou caso único (demais hits são docstrings) |
| P2-6 | SPEC v1 normativa ainda com o literal | **CURADO** — audit-log.schema.md §Summary + state-stores.schema.md defaults → `<native-slug>` com nota v2.58 |

**Ordem OBRIGATÓRIA do script de land (P1-3):**
1. Custódia (braço A: mover legado p/ `…pre-W1-archive/` 0500; braço B: copiar chain+key+salt p/ o dir slug);
2. Aplicar `tree/` nos paths canônicos (sob sentinel);
3. `verify_chain()` no destino + controle positivo de permissão;
4. Só então o commit de land.

## Rail codex r2 (S319) — 12 achados (9P1+3P2), 11 curados, 1 residual declarado

| # | Achado | Disposição |
|---|---|---|
| A (3×P1+1×P2) | `_rp` sem import em 4 CLIs (braço default que NENHUM teste exercitava) | **CURADO** — bootstrap com âncora segura + PROVA DE VIDA do braço default nos 4; varredura mecânica `(?<![\w])_rp\.` sem binding = 0 restantes |
| B (2×P1) | caches module-level de KEY e SALT não re-resolvem na troca de projeto (chave/salt do A assinam o B; os testes escondiam com reset manual) | **CURADO** — ambos keyed pelo path resolvido; os resets manuais SAÍRAM dos testes (viraram controles da cura) |
| C (P1) | slug não-injetivo (`/srv/a-b/c` ≡ `/srv/a/b-c`) | **RESIDUAL DECLARADO** — é a derivação NATIVA do harness (mesma colisão nos dirs de memória); divergir quebraria a co-locação ratificada no ADR-001 S318. Documentado no módulo; alternativa (sufixo hash) fica como opção do Owner |
| D (P1) | precedência DIR×PATH divergente entre audit_hmac (DIR-first) e o resto (PATH-first) partia a família com AMBOS setados | **CURADO** — regra única: a família segue o LOG EFETIVO (PATH-first) nos 4; controle novo `test_both_overrides_family_still_one_dir` |
| E (P1) | ceo-cost caía no legado incondicionalmente | **CURADO** — fallback READER só quando o log do projeto não existe E o legado existe, com WARNING nomeando a fonte |
| F (P1) | dir slug pré-existente 0755 (harness) nunca era apertado | **CURADO** — `runtime_paths.ensure_state_dir()` central (mkdir+chmod self-heal, precedente spool) usado pelos criadores (key, salt) |
| G (P2) | audit-query lia errors do default com log movido | **CURADO** — family-follows-log na leitura |
| H (P2) | claim de velocidade "(~µs)" em doc | **CURADO** — removido (contrato no-speed-claims do repo) |

Prova pós-r2: 207/207 nas famílias focadas; suíte completa re-rodada (números no estado da madrugada).

## Rail r3–r10 (S319 madrugada→manhã) — convergência e cura de CLASSE

Trajetória de achados por rodada: **6 → 12 → 2 → 1 → 3 → 3 → 2 → 1 → 2 → 4**.
Cada rodada atacou bordas mais estreitas; nenhuma classe de PRODUTO
reapareceu. Curados por rodada:

- **r3 (2):** `ceo-cost` passa a preferir o log ESCOPADO quando é arquivo
  (o fallback legado não era condicional de fato); `audit-query` ganha o
  degrau `CEO_AUDIT_LOG_DIR` na cascata do `errors`.
- **r4 (1):** logs ROTACIONADOS do projeto também vencem o legado
  (`--include-rotated` não pode misturar história alheia).
- **r5 (3):** `ensure_state_dir` deixa de apertar dirs escolhidos por
  override (0750 de compliance/vault é deliberado — `docs/GOVERNANCE.md`);
  guarda de symlink antes do chmod (path-based chmod SEGUIRIA o link);
  cenários do fixture passam a usar `patch.dict` escopado.
- **r6 (3):** `CLAUDE_PROJECT_DIR_NATIVE` entra na lista de overrides que
  inibem o tighten; identidade dos caches de key e salt vira ABSOLUTA
  (override relativo + `chdir` entre projetos serviria o cache do A).
- **r7 (2):** fixture ancora os sidecars herdados (contaminação do audit
  REAL era possível); fallback legado passa a valer também quando o
  legado só tem rotacionados (simétrico ao r4).
- **r8 (1):** `CEO_AUDIT_HMAC_DISABLE` no conjunto apply/drop do worker —
  forkserver já iniciado não herda limpeza do parent (verde VACUO).
- **r9 (2):** **preservação de cadeia legada** — numa instalação com
  `LOG_DIR`/`LOG_PATH` divergentes os sidecars vivem sob `LOG_DIR`;
  trocar a precedência cunharia chave nova e NENHUMA verificaria a cadeia
  inteira, então a família CONTINUA no legado (migração = cerimônia).
  Fixture: cura de CLASSE por domínio derivado + vigia com controle
  positivo.
- **r10 (4):** preservação passa a detectar QUALQUER sidecar legado (não
  só a key de nome default) e o breadcrumb é desacoplado da decisão
  (stderr fechado não pode quebrar a cadeia). **Fixture: ARQUITETURA
  INVERTIDA** — 5 rodadas achando a mesma falha com variáveis diferentes
  é fix-of-fix (PROTOCOL anti-pattern #6); em vez de enumerar o que
  REMOVER (lista sempre incompleta — o próprio vigia por regex perdia
  acessos por CONSTANTE), o fixture passou a rodar com env MÍNIMO
  EXPLÍCITO (`patch.dict(clear=True)` + allowlist neutro). Imune a
  variável nova POR CONSTRUÇÃO; o vigia saiu por desnecessário. Os
  workers recebem o env mínimo COMPLETO (não um delta sobre o herdado).

Prova pós-r9: suíte CI-equivalente **P1=0 / P2=0 / P3=0** (zero falhas,
zero flakes na rodada). Pós-r10: caminhos sync E spool concorrente verdes
(11/11 no arquivo).

## Rail r11–r12 — o achado mais importante e a RODADA LIMPA

- **r11 (1×P1, REAL):** a inversão de arquitetura do r10 valia só no
  PARENT — o worker de multiprocessing ainda fazia `update()` sobre o
  ambiente herdado, então um forkserver já iniciado mantinha o
  `CEO_AUDIT_SYNC_MODE=1` do pai e **o teste de spool concorrente
  exercitava, na verdade, o caminho SYNC** (verde vacuoso num teste de
  regressão de concorrência). Curado com `patch.dict(clear=True)` no
  filho + **controle do modo efetivo** (cada worker registra o
  `CEO_AUDIT_SYNC_MODE` que recebeu; o parent assere). Provado nos DOIS
  sentidos: com o plant do mecanismo (`clear=False`) + veneno `SYNC=1`
  no pai o controle fica VERMELHO nomeando "env vazou do parent: ['1']";
  restaurado, 11/11.
  *Nota de método:* a primeira tentativa de discriminador (medir o que o
  parent drena) estava ERRADA — o worker drena o próprio spool no
  `atexit` (`spool_writer:2618`), então `appended` no parent é 0 nos
  DOIS caminhos. Medir o env que CHEGA no filho é o que discrimina.
- **r12 — RODADA LIMPA (critério de parada atingido):** *"The
  path-resolution, per-project cache, audit-family, and test-isolation
  changes are internally consistent. Focused tests for the affected
  audit, runtime-path, cost, query, session-graph, and skill-retrieval
  areas passed."* Zero achados.

**Critério de parada declarado e cumprido:** rodar até APPROVE (não até
"já achei o suficiente"). 12 rodadas; **35 achados curados**; 1 residual
declarado (slug não-injetivo = derivação nativa do harness, decisão do
Owner); 1 pushback fundamentado (migração pertence ao script de land).

Suíte CI-equivalente no estado final: **P1=0 / P2=0 / P3=0** nas rodadas
pós-r9 e pós-r10; na pós-r11, o único vermelho foi o perf
`test_100k_search_streams_under_budget` sob `-n auto` concorrente com o
rail — 3× verde isolado, flake de carga.

## Fila para o Owner (manhã)

1. **Custódia W2: braço A ou B** (A recomendado pela medição US3).
2. GPG da cerimônia W1 (sentinel com Scope = MANIFEST.sha256 deste pack).
3. (Item separado, achado da madrugada) eleição ADR-111 do locked-corpus
   é INEXECUTÁVEL — corpus N=0, PLAN-081 nunca entrou neste repo, 0
   eventos `pair_rail_promotion`, probe `run-promotion-gate --dry-run` =
   "MANIFEST not found" exit 1. Opções: autorar 15 fixtures (cerimônia
   própria) / emendar ADR-111 / re-eleger DEFER.
