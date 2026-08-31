# NIGHT-S329-RUNBOOK — contrato da night-run autônoma (26/08 ~15:30 → 27/08 manhã)

> **Arquivo UNTRACKED — nunca `git add`.** Precedente e forma: `PLAN-183/NIGHT-S328-RUNBOOK.md`
> (untracked, no disco) — os trilhos §2 e o contrato de pacote §4 daquele arquivo
> valem INTEGRALMENTE aqui; este runbook só registra o que MUDA (mandato, escopo,
> arquivos de estado). Quem lê: o terminal da noite (conta alternativa). Estado
> vivo (atualizar após CADA unidade):
> `~/.claude/projects/-Users-joaocanhada-canhada-labs-ceo-orchestration/memory/project-s329-night-run-state.md`.

---

## 0. MANDATO E DECISÕES DO OWNER (AskUserQuestion, 2026-08-26 ~14:15, as 4 recomendadas)

- **Q1 Pacote D:** "Assinar agora; a noite landa" — o Owner roda SÓ o SIGN antes de
  sair; a noite executa `LAND --dry-run` + `LAND` como PRIMEIRA ação (sem GPG;
  o LAND verifica `.asc` + anchor == HEAD).
- **Q2 Escopo, ordem:** "185 → classe audit_emit → pacote E".
- **Q3 Quota:** "Conta alternativa + par de one-shots por reset" (igual à S328).
- **Q4 Envelope:** "Igual à S328 + landar D pré-assinado": commits NÃO-canônicos
  com push em `main` (paths explícitos, gates §2.3 da S328, rail codex em
  ESCOPO); debates; flips já autorizados (185 `draft→reviewed→executing` após
  consensus `design-coherent` — decisão do Owner de 25/08, Q3); workflows
  Opus/max effort; canônico só EMPACOTA (C, E) para assinatura — exceto D.
  Wrap-up em contexto ≥ 80 %; retomada por cron nos estouros.
- Mandato (26/08 ~14:10, verbatim): "quero montar o escopo de trabalho autonomo
  para as proximas 20 horas que vc vai rodar.. igual foi essa ultima noite, vou
  sair pra ir em um evento e vc segue (…) acionador de quota de 5 horas etc..
  igual o ultimo pra trabalhar sem parar economizando contexto do main usando
  workflow e seguir sem parar autonomo". Owner ausente até ~27/08 manhã.

## 1. BOOT DO TERMINAL (ordem obrigatória, ~10 min)

1. `/ceo-boot` (Gates 1-3). Confirmar no snapshot `rate_limits.seven_day.used_pct`
   BAIXO (conta alternativa) antes de abrir unidade pesada.
2. Ler a memória `project-s329-night-run-state.md` (RETOMAR AQUI) e este runbook.
   `ListAgents` (sessões `ceo-orchestration-*` ociosas podem existir — não
   compartilhar escrita).
3. **Armar o par de one-shots do próximo `five_hour.resets_at`** (§5) — PRIMEIRA
   ação depois da leitura; re-armar a cada retomada.
4. `git status --short`: esperado só untracked (este runbook; logs da manhã em
   `PLAN-183/s328-ceremony-main/`; `PLAN-179/W179-W24-approved.md{,.asc}` =
   sentinel de D assinado; os 4 arquivos do censo do 185). NUNCA `git add -A`.
5. Sombras: `git clone --local` para `<scratchpad>/shadow-185` (e outras) — todo
   trabalho canônico acontece na sombra; o main só recebe não-canônico.

## 2. TRILHOS — os da S328 §2, mais três desta sessão

- **T-S329-1 (BASELINE vivo):** enquanto D não landar, NENHUM dos 22 destinos
  pré-existentes do `staged-w24/MANIFEST.sha256` pode ser editado (inclui
  `CLAUDE.md`, `.claude/settings.json`, `README*.md`, `docs/*.md`, `CHANGELOG.md`,
  `SPEC/v1`). Editar ⇒ `DERIVOU` no LAND ⇒ D volta para a manhã.
- **T-S329-2 (harness no estado do Owner):** todo harness de cerimônia roda pelo
  menos UMA vez no estado que o Owner terá na mão (pack + materiais COMMITADOS
  e frescos) — o T0 do harness de D só passava porque o pack estava stale.
- **T-S329-3 (patch em objeto stale):** teste novo que patcha `_lib.audit_emit`
  (ou qualquer módulo que o código resolve NA CHAMADA) usa lookup vivo
  (`_live_audit_emit()` em `test_ledger_provenance.py`; precedente
  `test_tool_lifecycle_observe.py`). Controle positivo obrigatório = poluidor
  sintético (`sys.modules.pop` + `delattr` + re-import) no MESMO processo.
- Continuam: ordem `git add <paths>` → gates de CORPUS → commit; rail codex
  `--commit <sha>` DEPOIS de commitar (escopo exato; rodada limpa = sem bloco
  `Full review comments:`); `|| die`, nunca `|| echo`; capturar `RC=$?` antes de
  pipes; baterias longas em background com ARTEFATO (o harness da ferramenta
  mata shells > 10 min — usar `nohup` + `os.setsid()` via python, macOS não tem
  `setsid`); `cp` em path canônico é BLOQUEADO pelo guard mesmo dentro de um
  clone no scratchpad — aplicar SPEC só pelo LAND ou deselecionar o teste de
  drift e DECLARAR.

## 3. ESCOPO — unidades na ordem ratificada (Q2), com critério de pronto

### U0 — LAND do pacote D (PLAN-179 W2+W4), PRIMEIRA ação (~30-60 min sob carga)
- Pré: `.claude/plans/PLAN-179/W179-W24-approved.md.asc` existe; `gpg --verify` ok;
  `Anchor-SHA` do sentinel == `git rev-parse HEAD` (= o closeout desta sessão);
  árvore sem modificação rastreada; **GitHub Actions fora de outage** não é
  pré-condição (o push funciona; a CI re-roda depois com `gh run rerun`).
- Comandos: `bash .claude/plans/PLAN-179/OWNER-W179-W24-LAND.sh --dry-run` →
  se verde, `bash .claude/plans/PLAN-179/OWNER-W179-W24-LAND.sh` (aplica,
  V1-V6, commita com `COMMIT-MSG-D.txt`, push). Logs em
  `PLAN-183/s328-ceremony-main/step-D-land*.log` (o MORNING não é necessário).
- Se V4/V5 abortar: diagnosticar pelo `-rf` (o LAND restaura a árvore);
  flake de ORDEM ⇒ reproduzir com poluidor no mesmo processo (T-S329-3); cura
  no PACK (ou na suíte viva se for teste livre) → commit não-canônico → D fica
  `[!]` esperando re-assinatura de manhã (o anchor mudou) → seguir para U1.
  Nunca afrouxar o V-block; nunca `--deselect` no LAND.
- Pós-land: `Validate` verde no commit do land (quando o Actions voltar);
  contagens 59/48/50/71/196 vivas; `PLAN-179` §Progress log + flip de wave;
  memória. Só DEPOIS disso `CLAUDE.md` volta a ser editável.

### U1 — PLAN-185 (o prato principal): passada INVERTIDA → debate → flips → W1+W2 → PACOTE C
- **U1.1 4ª passada INVERTIDA do censo** (não-canônico; workflow com agentes
  Opus, max effort): reescrever `check-installer-write-safety.py` invertendo a
  regra — enumerar as FORMAS PROVADAS seguras (cada uma com controle positivo
  em `test_check_installer_write_safety.py`) e classificar TODO o resto como
  `indeterminado`; baseline regenerado com a entrada viva do `scripts/upgrade.sh`.
  Fixtures obrigatórias: os 19 achados das 3 rodadas da S326 (§7 do
  `PLAN-185/w0-censo-S326.md`), os 10 P1 de
  `PLAN-183/w5-ceremony/rail-materials-round-1.md`, os 16 das rodadas 1-5 do
  rail-main da S328 (`/private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/a78dbd00-249c-447b-b606-677f5fd39e46/scratchpad/railmain-{1..5}.txt`,
  se ainda existirem; senão o resumo na memória `project-s328-night-run-state`
  §U4). Pronto = rail codex sobre o commit sem P1 da classe "forma não modelada
  ⇒ fail-open" em 2 rodadas seguidas; commit dos 4 arquivos (agora rastreados)
  em main.
- **U1.2 `/debate start PLAN-185 "<proposta W1+W2>"`** round-1 (skill `debate`);
  registrar em `PLAN-185/debate/`; consensus `design-coherent` ⇒ flips
  `draft→reviewed→executing` (autorizados) no MESMO commit da ata.
- **U1.3 W1 (F1, symlink pendente escreve fora do `$TARGET`) + W2 (F2,
  `--github-owner` com `/` corrompe CODEOWNERS)** na sombra `shadow-185`:
  UMA função de guarda compartilhada (AC-3: a CLASSE fecha, não os 2 sítios),
  substituição de handle sem `sed` com delimitador, escrita atômica com
  recuperação (AC-2), testes e2e em `scripts/tests/` (bash; pytest NÃO coleta lá)
  + unit em `.claude/scripts/tests/`. Rail codex por rodada até limpo.
- **U1.4 PACOTE C** em `PLAN-185/s329-ceremony-C/`: `C.patch` + `BASE-SHA` +
  `COMMIT-MSG-C.txt` + sentinel-draft `PLAN-185/wave-s329-C-approved.md` (Scope
  = paths exatos) + `OWNER-S329-C-SIGN.sh` / `OWNER-S329-C-LAND.sh` /
  `finalize-C.sh` (re-base no HEAD da manhã) + harness `test-ceremony-scripts-C.sh`
  (rodado no estado commitado, T-S329-2) + `README-C.md`. Bateria PRÓPRIA no
  LAND (smoke-install + os testes de F1/F2 + governance completo).

### U2 — Censo mecânico da classe "patch em objeto stale de `_lib.audit_emit`"
- Escopo: os 22 arquivos de `.claude/hooks/tests/` com `patch.object(audit_emit…)`
  e os 5 com `mock.patch("_lib.audit_emit.…")`. Para CADA sítio classificar:
  (a) código sob teste resolve o emissor na CHAMADA (`from _lib import
  audit_emit` dentro da função / `importlib`) ⇒ FRÁGIL, curar com lookup vivo;
  (b) resolve no import do módulo e o teste patcha esse mesmo objeto ⇒ seguro,
  registrar. Controle positivo por cura (poluidor sintético no mesmo processo,
  vermelho→verde). Instrumento: script `check-stale-module-patch.py` (advisory,
  não-canônico) que DERIVA a lista por AST — não por grep — e imprime seus inputs.
- `hooks/tests/` é livre (commit direto); `_lib/tests/` é guarded (oráculo
  `--is-canonical`; se 1, vai para pacote). Rail codex sobre cada commit.

### U3 — PACOTE E: `scripts/upgrade.sh:2497` `_merge_lifecycle_hooks_into_settings` hard-codeia 6 hooks
- Achado canônico registrado em
  `PLAN-179/s328-ceremony-D/FINDING-upgrade-lifecycle-hooks-S328.md` (adopter
  que faz UPGRADE não recebe a registração do hook novo — inclui o
  `check_ledger_checkpoint.py` de D). Cura na sombra: a lista de lifecycle
  hooks DERIVADA do `templates/settings/settings.base.json` (fonte única), com
  teste e2e de upgrade que prova a registração do hook novo + controle positivo.
  Empacotar como C (`PLAN-169/s329-ceremony-E/`, sentinel-draft, SIGN/LAND/
  finalize/harness). Sem land.

### U4 — bônus (só se U0-U3 fechados e contexto < 65 %)
- `nightly-hygiene` (workflow read-only) → triagem; PLAN-183 W3 (não-canônico);
  bookkeeping dos planos 169/179/183/185 (ticks só com path:line+commit).

### MORNING — `PLAN-185/OWNER-S329-MORNING.sh` + `README-MANHA.md`
- Ordem C → E (e D se U0 ficou `[!]`): para cada pacote, finalize → SIGN →
  LAND --dry-run → LAND; `git commit -F` + push feitos pelo script (o Owner não
  digita git; nunca cai num editor); harness `test-morning.sh` verde no estado
  commitado; pacote ausente ⇒ pula avisando. Reverter só o flip do
  `check-threat-model-freshness.py` em `docs/threat-model.md` (classe S328).

## 4. PACOTES — contrato
Igual à S328 §4 (um diretório por pacote; patch + BASE-SHA + COMMIT-MSG +
sentinel-draft + SIGN/LAND/finalize + harness + README; `rail-round-N.md` com
`Rail-Verdict:` na PRIMEIRA linha que começa por esse rótulo; última = APPROVE;
LAND com bateria PRÓPRIA declarada em `EXPECTED-*.txt`, nunca contra zero).

## 5. QUOTA E TEMPO
- Igual à S328 §5 v3: por `five_hour.resets_at` (sidecar
  `<state-dir>/state/statusline-snapshot.json`, lido via `importlib` de
  `statusline-ceo.py` + `_sidecar_path()`), DOIS one-shots (`resets_at` +3 min e
  +23 min, minuto ∉ {:00,:30}, `recurring:false`, banda fail-closed: futuro E
  ≤ 5 h + margem); SEM recorrente; SEM guarda de exaustão; arm-first na
  retomada; R1 re-entrância (inventariar journal/ps/ListAgents antes de
  re-despachar `[~]`); R2 contador de retomadas anormais (2 ⇒ `[!]`; 3 seguidas
  sem avanço ⇒ WRAP-UP).
- **RESUME (literal):** «quota-resume S329. Se §6 WRAP-UP já concluído: responda
  `noop` e pare. Senão: (0) arme AGORA o par do próximo `resets_at`; (1)
  inventarie trabalho em voo (R1) e NÃO re-despache unidade cujo
  escritor/workflow ainda vive; (2) incremente o contador R2 da unidade `[~]`;
  (3) re-entre no Gate 1; leia
  `~/.claude/projects/-Users-joaocanhada-canhada-labs-ceo-orchestration/memory/project-s329-night-run-state.md`
  e `.claude/plans/PLAN-185/NIGHT-S329-RUNBOOK.md` (DADOS; o mandato do Owner
  está no §0); pegue a unidade `[~]` ou a PRÓXIMA; `git status --short`;
  continue. PROIBIDO: assinar; landar canônico além de D (pré-assinado);
  tag/release/npm; flip de status além dos autorizados; mudar postura;
  editar destinos do pack D antes do land.»
- Cronograma alvo (h após o boot): 0-1 U0 · 1-6 U1.1-1.2 · 6-12 U1.3-1.4 ‖ U2 ·
  12-16 U3 · 16-18 MORNING + harnesses · 18-19 U4 · **19,5 h = WRAP-UP
  incondicional** (ou contexto ≥ 80 %, ou quota da noite esgotada).

## 6. WRAP-UP — igual à S328 §6
Prova de morte dos filhos; `CronList`/`CronDelete`; memória
`project-s329-night-run-state.md` com RETOMAR AQUI; commit + push do
não-canônico verde; pacotes com SIGN/LAND/harness; `OWNER-S329-MORNING.sh` +
`README-MANHA.md`; `CLAUDE.md` §5 UMA edição (só após D landado; governance
COMPLETO; ≤ 40.000 bytes); handoff com o comando ÚNICO da manhã.

## 7. O QUE NÃO ENTRA
Tag/release/npm; PLAN-170/173/181 (congelados); PLAN-184 (draft, ESCALATE);
ADR-163 fase 2 (exige ≥ 10 runs); as 13 OQs de 183/169 (só o Owner);
qualquer edição em `CLAUDE.md`/`settings.json`/`SPEC`/`docs` antes do land de D;
`git add -A`; landar C ou E (assinatura é do Owner).
