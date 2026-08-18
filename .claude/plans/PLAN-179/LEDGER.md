# LEDGER — PLAN-179 (+ PLAN-169) · sessão S313

> Dogfood da própria W2 do PLAN-179: escrita em FRONTEIRA DE UNIDADE, não
> na morte da sessão. Só identificadores verbatim (paths, SHAs, ids) —
> nunca corpo de transcript. Teto ≤2k tokens; seções antigas arquivadas.

## Estado final da sessão autônoma (16:13)

**PRONTO PARA O OWNER — duas cerimônias, nesta ordem:**
1. `! bash ~/canhada-labs/OWNER-W3K-SIGN.sh` — PLAN-169 W3-K (kernel).
   **SESSÃO DEDICADA** (U-3): o script recusa rodar se o override já estiver no
   ambiente, arma no menor escopo, desarma e tem trap EXIT.
2. `! bash ~/canhada-labs/OWNER-W179-SIGN.sh` — PLAN-179 W0+W1+W1-b.
   24 paths; simulação de land em clone **8/8 verde, rc agregado 0**.
3. (depois) `staged-w24` (W2+W4) — montar o BASELINE só DEPOIS que o w01 landar,
   porque toca `audit_emit.py`/`settings.json` que o w01 move.

**Landado hoje (superfície livre, sem cerimônia):** higiene de lifecycle (5
planos → done, 2 → reviewed), ledger final do 169 (62 itens), evidência E0
verificada contra o hash pinado, PLAN-170 autorado, W3 do 179 inteira
(floor-reduction com F MEDIDO, veredito de eviction, template de compactação,
sondas órfãs, guia do adopter), threat model do estado durável, correção da
premissa falsificada do W3-K no corpo do plano.

**NÃO fecha hoje, com razão mecânica (não é falta de tempo):**
- GA v1.4.0: hold de 24h ENFORÇADO em `release.yml:292-352`.
- Corte rc.1: o conteúdo da 1.4.0 É a W4+W4-C (~900k, abertas) — cortar hoje
  shipparia uma 1.4.0 sem features; e o retarget de `release.sh` virou
  checksum-pinado pelo ADR-192 que landou hoje de manhã.
- W4/W4-C do 169: bloqueadas em 3 conjuntos de probes não rodados, 2 dos quais
  podem invalidar o próprio item.

## Unidade corrente (atualizado 15:25)

**U5 — dois packs em construção + 1 cerimônia de kernel.**
- `staged-w01` (W0+W1+W1-b): 4 implementadores voltaram; integração em voo
  (`wf_337e72f2-2ce`) curando os defeitos que o paralelismo criou.
- `staged-w24` (W2+W4): 4 implementadores em voo (`wf_579e41a3-d3c`).
- `staged-w3k` (169 W3-K): fix + teste positivo em voo (`wf_d0896846-177`).
- W3 do 179 (superfície livre): em voo (`wf_9fc81c68-035`).
- Landado e pushado: ledger final do 169 (62 itens), E0 verificado, PLAN-170
  autorado, land script + draft do sentinel (`1e3ffaa`, `4f0ceb5`).

### Defeitos de processo achados (valem mais que o código)
1. **Paralelismo sem barreira gera integração falsa-verde.** Os 4 agentes do
   W0/W1 rodaram concorrentes e nenhum viu os arquivos dos outros: cada um
   sondou o símbolo do irmão com `getattr`, não achou, e **degradou com
   breadcrumb**. Compilava, testava, e a cura não existia. Caso concreto:
   `check_precompact_continuity` procura `audit_emit.edge_trigger_should_emit`,
   mas o símbolo shipado chama-se `should_emit_context_pressure` ⇒ progress
   guard **nunca dispararia**. Regra: fan-out que compartilha API precisa de
   PIPELINE (stage 2 lê o stage 1), ou de um passe de integração obrigatório.
2. **`Edit(SPEC/**)` casa até no path do PACK.** O agente do audit bateu no
   deny e **recusou contornar** — julgamento correto. Cura sem evasão: o
   artefato do pack ganha nome plano (`spec-v1-audit-log.schema.md`) + um
   `PACKMAP.txt` que o land script honra; o SPEC vivo continua escrito só pela
   cerimônia assinada.

## Unidade anterior

**U1 — censo read-only de PLAN-169 (W3-K/W4/W4-C/W5/W6) e PLAN-179 (W0-W4).**
Workflow `wf_584a3a45-36c` (4 agentes, effort high, read-only).
Run anterior `wf_10e177fb-d5f` morreu inteiro (limite de sessão, 0/4) —
nada perdido. Sonda de capacidade `wf_dc2721d5-130` = OK antes de re-despachar.

## Fatos estabelecidos nesta sessão (verificados, não inferidos)

- HEAD ao abrir U1: `a71229e`. Árvore limpa. CI verde (smoke-install verde
  desde `4b7efee`; perf-gate = flake I/O do runner, rerun verde).
- **Mapa canônico** (oráculo oficial `check_canonical_edit.py --is-canonical`,
  com controle positivo em `check_precompact_continuity.py` = CANONICAL):
  - CANONICAL (exigem cerimônia GPG): `.claude/hooks/*.py`,
    `.claude/hooks/_lib/*.py`, `SPEC/v1/audit-log.schema.md`,
    `.claude/adr/ADR-*.md`, `.claude/settings.json`,
    **`.claude/settings.local.json`** (canônico mesmo sendo gitignored).
  - LIVRES (landam por commit normal): `.claude/scripts/probes/**`,
    `.claude/plans/PLAN-179/**`, `.claude/hooks/tests/**`,
    `docs/threat-model.md`, `templates/compaction.md`,
    `.claude/scripts/context-budget.py`.
- **Debate L3 do PLAN-179 = SATISFEITO** — `PLAN-179/debate/round-1/consensus.md`
  existe (S312, PROCEED, 3× ADJUST). W1+ liberado sem novo debate.
- **PLAN-169 AC-6 (pré-registro E7 assinado)** — `PLAN-169/W5-preregistration.md`
  + `.asc` existem e foram commitados em `fcac12d`. Verificar no censo.
- **Canal SessionStart PROVADO entregando**: a linha `⚡ turbo: verify=✓ …`
  aparece no topo desta sessão = `SessionStart` additionalContext chega ao
  contexto. Pergunta aberta de W0-1 é só se dispara com `matcher=compact`.
- **PostCompact JÁ registrado** (`settings.json:653`) lendo o snapshot do
  scratchpad e reinjetando ponteiros via `additionalContext`.
  ⇒ A sonda W0-1 NÃO precisa instalar hooks (settings é canônico): semeia o
  store e usa o canal de PRODUÇÃO. Dois canários numa compactação paga:
  (A) token único semeado no ponteiro; (B) reaparecimento da linha turbo.

## U1 — censo: ENTREGUE (2/4 escopos; 2 morreram em 529 Overloaded, resumidos)

Achados que MUDAM o plano (verbatim do censo, evidência citada):
- **W0 NÃO é read-only** (§7 do plano está errado): `audit_emit.py` (US2) e o
  progress-guard (US2b) são canônicos ⇒ W0 pega carona na cerimônia da W1
  (emenda 8.2 já lista `audit_emit.py`).
- **US2b premissa caída:** `check_precompact_continuity.gate()` retorna `{}`
  por contrato — PreCompact **não tem canal de deny**. "HALTAR" não é
  implementável como retorno de hook ⇒ vira **observe+notify** (breadcrumb +
  evento), e piso numérico só depois de `F` medido.
- **8.3 confirmada:** `state_store.py:297-306` só redige `str`; o snapshot
  grava `bytes` ⇒ claim "secrets-redacted" é FALSA hoje. Cura = passar `str`.
- **Baselines pinados que quebram** ao somar `context_pressure_observed`:
  `test_audit_emit_api_contract.py` `_EXPECTED_KNOWN_ACTIONS_SHA256` (:724) e
  contagem 324→325 (:777); SPEC v2.55 → **v2.56**.
- `.claude/state/` é gitignored (`.gitignore:77`) ⇒ estado da sonda vai lá.
- SessionStart expõe `source ∈ [startup,resume,clear,compact,fork]`
  (`PLAN-163/probes/schema-diff-2.1.202-to-2.1.220.md:15`) — matcher=compact
  é documentado mas **nunca exercitado localmente**: tratar como não-provado.
- Hook novo move contagens derivadas (57/46/48) com tolerance=0.

## U1b — censo PLAN-169 (W4-C/W5/W6 + AC-1..AC-9): ENTREGUE

- **SATISFEITOS:** AC-2 (nightly 62/3, run 31286301110), AC-3 (GA v1.3.0 +
  166 done), W5.prereg (assinado, `fcac12d`, IMUTÁVEL), W6.1.
- **Fecháveis hoje, superfície LIVRE:** AC-1 (§-final do 169 — o Progress log
  para em 2026-08-09/S299 e não registra `e5ce982`/`874117c`/E0-S300),
  AC-6 restante (commitar `~/.rc2-backup/e0-report-s300.txt` conferindo o
  sha `d07935b3…` + **criar PLAN-170**), AC-9 (rol de evidência das 4 dívidas C.*).
- **E0 já rodou (S300) e DEFUNDOU E1/E2:** S=1.000 conservador (piso 0.785)
  contra a regra pré-registrada S≥0.40 ⇒ o escopo do PLAN-170 encolheu para
  E3+E4. O budget original (6-20M) está STALE.
- **NÃO fecha hoje, com razão mecânica:**
  - **AC-8 (GA v1.4.0):** hold de 24h é ENFORÇADO em
    `release.yml:292-352` (delta < 86400s ⇒ erro). Impossível hoje por construção.
  - **W6.2 (corte rc.1):** o conteúdo da 1.4.0 É a W4+W4-C, que estão
    INTEIRAS abertas (~900k). Cortar rc.1 hoje shipparia uma 1.4.0 sem
    features. Além disso o retarget `TARGET_BASE` em `release.sh:74` agora
    arrasta cerimônia canônica — o script virou **checksum-pinado** pelo
    manifesto que eu mesmo landei hoje (`874117c`, ADR-192). Mesma classe do
    G4 que abortou a W2.8.
  - **AC-4/AC-5 (W4.1/W4.2):** bloqueados em 3 conjuntos de PROBES não
    rodados; 2 deles podem invalidar o item (o evento pode não existir no
    CLI 2.0, e registrar evento inexistente pode invalidar o settings.json).
- **U-3 confirmado:** W3-K e W4-C têm posturas de override de kernel
  DIFERENTES ⇒ nunca na mesma sessão (um `export` sobrevive).

## U4 — W3-K (169): DIAGNÓSTICO EMPÍRICO DERRUBOU A PREMISSA DO PLANO

Reproduzido em harness hermético (`reproduced=true`, `event_emitted=true`):
- `kernel_extension_landed` **NÃO é engolido**: está em `_EMIT_GENERIC_PASSTHROUGH`
  (`audit_emit.py:1751`), `emit_kernel_extension_landed` só faz `ceremony_sha[:64]`
  sem validar formato. O evento LANDA com o path dentro de `ceremony_sha`
  (`hmac_error: null`, `audit-log.errors` vazio). O `except Exception: pass`
  nunca dispara.
- **O bug REAL é outro evento e outro mecanismo:** `veto_triggered
  reason_code=kernel_override_used` nunca é emitido porque o branch em
  `check_arbitration_kernel.py:696` testa `decision == "allow"`, e `decision`
  vem de `json.loads` da saída do próprio `_emit_allow()`, que **nunca escreve
  a chave `decision`** (o comentário dele diz que "allow" no topo é inválido).
  `git log -S'"decision": "allow"'` volta VAZIO ⇒ **branch nasceu morto**, não
  regrediu. O systemMessage do hook (:459-462) e o docstring do módulo (:34-36)
  mandam o operador procurar exatamente o evento que nunca é escrito.
- Consequência de governança: **uso de override de kernel não é auditado pelo
  canal que a documentação promete**.
- Cura: reviver o branch por AUSÊNCIA de block (`decision is None` + override +
  kernel path), ou melhor, `decide()` devolver o fato do grant a `main()` para o
  audit não depender de parsear a própria saída. NÃO mexer nos kwargs — estão OK.
- Lição: a premissa "emit engolido / ceremony_sha inválido" era plausível e
  ERRADA. Só a reprodução hermética separou as duas.

## Decisões tomadas

- **D1** — Trabalho canônico vai para pack staged (`staged-*/`) + UMA cerimônia
  GPG do Owner; trabalho livre landa por commit direto. Padrão dos packs
  W2.8/S313 (provado 2× hoje).
- **D2** — Agentes de implementação escrevem SÓ em paths livres ou dentro do
  pack staged; nunca no path canônico vivo.
- **D3** — GA da v1.4.0 (169 W6.2) NÃO fecha hoje: hold ADR-103 de 24h entre
  tag e GA é obrigatório. Máximo hoje = corte da rc.

## Bloqueios abertos

- Limite de sessão bateu 1× às ~13:2x (reset 15:30 -03). Se reincidir,
  re-despachar por `scriptPath` (script persiste em disco).

## Próximas unidades (ordem)

U2 = implementação livre (sonda W0-1, medição W0, testes) ·
U3 = pack canônico staged (hooks 179 W1/W1-b, ADRs, SPEC) ·
U4 = 169 W3-K (kernel, cerimônia própria) · U5 = 169 W4/W4-C ·
U6 = cerimônia(s) do Owner · U7 = 169 W5/W6.2 (corte rc v1.4.0).
