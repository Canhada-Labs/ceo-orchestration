---
round: 1
archetype: DevOps Engineer
skill: devops-ci-cd
agent_persona: (per team.md)
generated_at: 2026-07-27T00:00:00Z
---

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- O plano reconcilia a janela CC 2.1.199→2.1.220 + família Claude 5 em 6 threads com uma cerimônia única — escopo correto, sequência W0→W4 correta, e a evidência-base (changelog verbatim + inventário file:line) é acima da média.
- Forte: a postura red-first declarada (T2 oracle, T4 medição), o respeito à ordem pin→re-record (ADR-111/_DRIFT_RUNBOOKS), e a ausência deliberada de version-gate no install/upgrade (verificado: nenhum gate em `scripts/install.sh`/`scripts/upgrade.sh` — by design).
- Fraco: dois claims centrais não se sustentam como escritos — o Check do G3 nasce VERDE (vacuoso, viola red-first) e o T5 mira o pin errado (o semver range já cobre 0.144.6; o que muda é o SHA binário); além disso T2 e T4 estão subespecificados nos exatos pontos que já nos queimaram (schema source-of-truth em CI; colapso de percentil PLAN-159).

## Risks

1. **R-DEV1 — Severity: HIGH** — T2 oracle sem source-of-truth de schema executável em CI. `validate.yml` não instala nem invoca o binário `claude` (verificado por grep); a re-extração zod é um passo local do operador. Se o oracle "valida contra o schema 2.1.220" sem um artefato commitado, ele ou não roda em CI ou valida contra nada (drift silencioso). Mitigation: commitar o schema extraído como artefato versionado (JSON + stamp `2.1.220` + sha256 + recipe de re-extração); o oracle CI valida contra o snapshot; a extração vira passo documentado de bump.
2. **R-DEV2 — Severity: HIGH** — Check do G3/T1-6 nasce VERDE. O parity está verde no HEAD (`e9d7103`), logo toda ocorrência literal de `claude-opus-4-7` em superfície shipped já está exempted: `audit-telemetry.py:40-42` é rate card histórico S227 (ALLOWLIST_RE, smoke-install-parity.sh:65), `generate-dispatch.py:316-318` é label-mapping de ledger pré-4.8 (allowlisted), `context-budget.py:42,112` referencia o NOME DE ARQUIVO `profile-opus-4-7.py` (nem casa com STALE_RE). "grep de opus-4-7 como default retorna 0 fora da allowlist" passa HOJE sem nenhum fix — oracle vacuoso. O defeito REAL é de PRESENÇA: `_PRICING_PER_MTOK` (audit-telemetry.py:40-46) não tem linha para opus-4-8 NEM fable-5 — o rollup de custo já está cego para os modelos correntes. Mitigation: reescrever o Check como asserções de presença (tabelas de pricing/detecção contêm o set corrente {opus-4-8, fable-5, opus-5, sonnet-5}) — isso nasce vermelho de verdade; manter as linhas 4-7 (replay ADR-142).
3. **R-DEV3 — Severity: MEDIUM-HIGH** — `STALE_RE += claude-opus-4-1` derruba o parity como especificado. Ocorrências grep-verificadas em `model-deprecations.json`, `check-model-deprecations.py` e `.claude/data/canonical_models.json` — carriers by-design (um DB de deprecação PRECISA nomear modelos mortos) que NÃO estão em ALLOWLIST_RE/EXEMPT_PATH_RE. Mitigation: T1-7 enumera os deltas de allowlist no mesmo item, em vez de "avaliar".
4. **R-DEV4 — Severity: MEDIUM** — T5-2 mira o pin errado. `.claude/governance/codex-cli-pin.txt` = `>=0.128.0,<0.145.0` — 0.144.6 JÁ está in-range; o arquivo que muda é `codex-cli-binary-sha256.txt` ("the real supply-chain gate", header do próprio pin), mais re-record de fixtures + eleição run-vs-defer do locked-corpus catch_rate na assinatura. Como escrito, um executor reescreve o semver à toa ou — pior — pula o SHA achando que "pin inalterado = nada a fazer". Mitigation: reword do T5-2 nomeando o arquivo-alvo (SHA) e o escopo real da cerimônia.
5. **R-DEV5 — Severity: MEDIUM** — T4 reproduz a classe PLAN-159. N∈{6,8,12} são níveis de CONCORRÊNCIA; a contagem de AMOSTRAS por nível não está especificada (o root cause do PLAN-159 foi colapso de índice de percentil em N=20 — cura foi N=200), condição de carga/máquina não declarada, e "~50ms@N=8" não diz se é p50 ou p95. Mitigation: pré-registrar o protocolo — ≥200 aquisições por nível, máquina local idle identificada, percentil + threshold exatos, e workload shape igual ao do PLAN-083 (senão os números não são comparáveis e o cap 6→8 vira vontade, não número).
6. **R-DEV6 — Severity: MEDIUM** — Superfícies shipped a adopters sem oracle de upgrade. `availableModels`, rename `defaultMode: manual` e +2 registrations viajam via install/upgrade; os Checks de T3/T5 são probe local + ledger apenas. O PLAN-161 achou os bugs de dry-run/exclusion-parity AO VIVO num upgrade real — a mesma classe se aplica ao merge de settings com enum renomeado (`default`→`manual`) num target que carrega o valor velho. Mitigation: itens de oracle no `smoke-install.yml` (padrão U1-U3, já wired em `e9d7103`): pós-install E pós-upgrade — modelos presentes, defaultMode são, contagem de registrations 48.
7. **R-DEV7 — Severity: LOW** — "44 hooks" hardcoded no T2. T3 move para 46 wired/48 registrations; contagem literal é a doença de drift que verify-counts existe para pegar. Mitigation: o oracle deriva a lista de hooks dinamicamente do settings.json; e nem todo hook tem caminho de block (observers PostToolUse) — classificar por evento e exigir caso de block só onde block existe.

## Must-fix (blocking)

1. **T2**: commitar o schema 2.1.220 extraído como artefato versionado (stamp + sha + recipe) e apontar o oracle CI para ele; rodar como job próprio no `validate.yml` COM `timeout-minutes` explícito E no pre-push (doutrina gates-exatos-do-CI); lista de hooks derivada do settings.json com classificação allow/block por tipo de evento. (R-DEV1, R-DEV7)
2. **T1-6/G3**: reescrever o Check como asserções de PRESENÇA do set de modelos corrente nas tabelas de pricing/custo (`audit-telemetry.py`, `ceo-cost.py`, `cost-table.yaml`, `budget-summary.py`) e nos sets dos detectors — nasce vermelho hoje (fable-5/opus-4-8 ausentes em `_PRICING_PER_MTOK`); proibir explicitamente a remoção das linhas 4-7 (replay ADR-142 / allowlist do parity). (R-DEV2)
3. **T1-7**: enumerar os deltas de ALLOWLIST_RE/EXEMPT necessários ANTES de `STALE_RE += claude-opus-4-1` (mínimo grep-verificado: `model-deprecations.json`, `check-model-deprecations.py`, `.claude/data/canonical_models.json`). (R-DEV3)
4. **T5-2**: reword — semver pin já cobre 0.144.6; escopo da cerimônia = bump do `codex-cli-binary-sha256.txt` + re-record fixtures PLAN-155 W1 + checklist ADR-161 + eleição catch_rate do Owner. Ordem pin→re-record mantida. (R-DEV4)
5. **T4-1**: pré-registrar o protocolo de medição (≥200 amostras/nível, máquina + condição de carga declaradas, percentil e threshold exatos, workload shape PLAN-083) no plano antes do W1. (R-DEV5)
6. **T3/T5**: adicionar itens de oracle no `smoke-install.yml` (padrão PLAN-161 U1-U3) para as superfícies shipped: availableModels, defaultMode, contagem de registrations — pós-install e pós-upgrade. (R-DEV6)

## Nice-to-have (advisory)

1. **OQ1 (fallbackModel)**: manter `claude-opus-4-8` como fallback por uma janela de soak — Opus 5 tem 3 dias de GA e fallback é o caminho degradado; o resto do refresh completo (routing debate/arch, VETO floor) pode ir agora. Revisitar no closeout.
2. Registrar o probe do grok em `_PROBE_ARGV` (`["grok", "--version"]`) — verificado ausente no registry fechado de `check-substrate-watch.py` (o claim G13 "sem probe registrado" SUSTENTA; o ledger tem a entry grok_cli 0.2.93, o que falta é o probe de código).
3. T3 Check: trocar "46/46 (ou recontagem correta)" por números explícitos (46 hooks wired / 48 registrations) — executor não deve adivinhar.
4. T2-4 (MCP auto-background): registrar o resultado do probe mesmo se nulo — o pair-rail principal é subprocess CLI, não MCP; se os matchers `mcp__codex__*` forem dormentes, dizer isso é o achado.
5. Orçar tokens do T2 com prioridade: casos de block artesanais só para os 8 hooks schema-densos; shape-check genérico para o resto — 44×2 subprocessos custam ~1-2min de CI (viável), mas as FIXTURES de block são o long pole de sessão.

## Unseen by the original plan

1. **`detectors/overpowered.py:28` — `_LARGE_MODELS` não contém `claude-fable-5` HOJE.** O modelo-teto dos VETO roles é invisível ao detector de overpowered-spawn desde a adoção do Fable 5; o plano só discute adicionar opus-5/sonnet-5. Adicionar fable-5 (e opus-5) aos sets dos dois detectors dentro do T1.
2. **Acoplamento perf-gate ↔ rename.** O job `opus-4-7-profiler-smoke` (`validate.yml:1178`) e o arquivo `profile-opus-4-7.py` carregam "opus-4-7" no NOME; required checks de branch protection referenciam nomes de job — um executor "consertando 4-7 via grep" no T1-6 pode renomear e quebrar silenciosamente a proteção de branch. O plano corretamente não os toca, mas nada DIZ que estão fora de escopo. Adicionar linha explícita de out-of-scope + follow-up para o rename coordenado.
3. **`enforceAvailableModels` — semântica verificada em 2.1.202, não em 2.1.220.** O comentário no settings.json documenta inclusive um fail-open de harness (managed-policy source com falha de load desliga o enforcement). Todo o T1 se apoia nessa chave; o diff de schema do T2 deve re-verificar explicitamente o comportamento dela em 2.1.220.
4. **Tokenizer +30% do Sonnet 5 atinge budgets SHIPPED, não só routing.** OQ2 cobre o default advisory, mas `budget_tokens` de planos-template e cost-envelope docs que viajam ao adopter ficam mal calibrados no dia em que o adopter mover o tier. Ao menos registrar a nota no doc datado do T6.

## What I would NOT change

1. **Ausência de version-gate no install/upgrade** — verificado: zero gate em `scripts/install.sh`/`scripts/upgrade.sh`; a postura advisory via substrate-watch é a correta. Não deixar o debate "melhorar" isso para um gate hard que quebraria adopters em CLIs mais velhos.
2. **OQ3 draft pin=1** — conservador e correto: `check_agent_spawn` foi projetado para 1 nível auditado; depth-3 sem probe de cobertura do guard em depth≥2 é buraco de governança, não velocidade.
3. **"O número decide" no cap do flock (T4)** — medição antes de doutrina é exatamente a postura certa; meus must-fix apertam o protocolo, não a filosofia.
4. **Cerimônia canônica única (W3)** empacotando settings + hooks novos + ADRs + pin — padrão PLAN-160/161 comprovado; não fragmentar em múltiplas cerimônias.
5. **Ordem pin FIRST → re-record fixtures** no T5 — conforme `_DRIFT_RUNBOOKS`/ADR-111; manter.

---

### Spot-verification record (contrato do round 1 — 3+ claims)

| Claim do plano | Evidência | Sustenta? |
|---|---|---|
| `smoke-install-parity.sh:43,57` ALLOWED_MODELS sem opus-5/sonnet-5 + STALE_RE com 4-7 | linhas 43 e 57 confirmadas byte a byte | SIM |
| Ledger `substrate-watch.json`: claude_code 2.1.198, codex_cli 0.144.1, codex_harness 0.139.0 | entries `last_seen` confirmadas; grok_cli TEM entry (0.2.93) mas NÃO tem probe em `_PROBE_ARGV` | SIM (com a leitura correta de G13 = probe de código) |
| Nenhum version-gate em install.sh/upgrade.sh | grep por padrões de gate: zero matches | SIM |
| G3 "defaults opus-4-7 vivos" em audit-telemetry/generate-dispatch/context-budget | são carriers históricos allowlisted (parity :65) ou referências a filename; o Check proposto nasce verde | **PARCIAL — não sustenta como escrito** (R-DEV2) |
| T5 "pin codex 0.144.1→0.144.6" | semver pin `>=0.128.0,<0.145.0` já cobre 0.144.6; o que muda é o SHA binário | **NÃO como escrito** (R-DEV4) |
| `settings.json:715-720` availableModels sem opus-5/sonnet-5 | linhas 715-720 confirmadas | SIM |
