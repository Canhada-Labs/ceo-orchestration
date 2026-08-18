# LEDGER — PLAN-179 (+ PLAN-169) · sessão S313

> Dogfood da própria W2 do PLAN-179: escrita em FRONTEIRA DE UNIDADE, não
> na morte da sessão. Só identificadores verbatim (paths, SHAs, ids) —
> nunca corpo de transcript. Teto ≤2k tokens; seções antigas arquivadas.

## Unidade corrente

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
