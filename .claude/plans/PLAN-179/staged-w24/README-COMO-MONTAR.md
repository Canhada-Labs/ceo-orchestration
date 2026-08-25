# staged-w24 — pack do PLAN-179 W2 (ledger) + W4 (governança do estado durável)

> **Este pack está IMPLEMENTADO mas NÃO MONTADO de propósito.** Ele toca
> `audit_emit.py` e `settings.json`, que o pack `staged-w01` também move. O
> BASELINE de um pack é o hash dos arquivos VIVOS: gerá-lo agora congelaria o
> estado pré-w01 e o gate anti-stale (G1) abortaria — corretamente — no
> primeiro segundo do land. **Monte só depois que o `staged-w01` tiver landado
> e sido pushado.**

## O que já está pronto aqui

| arquivo | o que é |
|---|---|
| `.claude/hooks/check_ledger_checkpoint.py` | hook novo (PreToolUse/Bash), ADVISORY por construção — não existe braço de deny no módulo |
| `.claude/hooks/tests/test_check_ledger_checkpoint.py` | 37 testes, incluindo um teste de nível AST que PROÍBE o hook de chamar `resolve_plan_id` (emenda r1-C6: o gatilho deriva de PATHS, senão a W2 re-herda a causa-raiz que o plano cura) |
| `.claude/hooks/_lib/ledger_provenance.py` | tags de proveniência + write-gate fail-CLOSED + verificação pós-deleção |
| `.claude/hooks/tests/test_ledger_provenance.py` | testes do acima |
| `.claude/adr/ADR-194-work-boundary-persistence.md` | ADR de doutrina, abrindo com matriz de 3 opções (emenda 8.5) e com estratégia de saída escrita (W2 é *Embedded*) |
| `SESSIONEND-NOTE.md` | especificação do US8 (SessionEnd emite o delta candidato de memória) para a cerimônia que tocar `SessionEnd.py` |

## O que a cerimônia AINDA DEVE (números RE-MEDIDOS em 2026-08-22 — a redação anterior citava quatro que morreram)

> Todo número abaixo foi derivado do gate, não de memória:
> `bash .claude/scripts/local/verify-counts.sh --no-tests --json` e
> `len(_KNOWN_ACTIONS)` carregando `audit_emit.py`. Re-meça antes de assinar.

1. **`audit_emit.py`**: registrar `ledger_checkpoint_recorded` e
   `ledger_checkpoint_skipped` em `_KNOWN_ACTIONS`, cada um com allowlist
   deny-by-default + branch de scrub. **Nunca** em `_EMIT_GENERIC_PASSTHROUGH`.
   Os campos e enums fechados estão listados no retorno do agente do hook.
   **DECISÃO PENDENTE — 2 ou 3 ações.** `_lib/ledger_provenance.py:613`
   procura `emit_ledger_entry_rejected` e a linha 645 declara
   `ledger_entry_rejected` como *não registrada, cerimônia W4 pendente*.
   Medido: nem o emitter nem a ação existem vivos. O degrade é gracioso — o
   fallback `emit_prompt_injection_detected` existe e sua assinatura casa a
   chamada de :626-634 — mas só para `reason="scanner_hit"`;
   `scanner_unavailable`/`oversize`/`malformed_input` ficam breadcrumb-only.
   Decida EXPLICITAMENTE: registrar a terceira (327 → 330) ou shipar 2
   (327 → 329) e NOMEAR o breadcrumb como residual no sentinel.
   **DECIDIDO 2026-08-25 pelo Owner (S328, AskUserQuestion, verbatim): «3 ações
   — registra ledger_entry_rejected (Recomendado)».** Logo: `_KNOWN_ACTIONS`
   327 → 330 (re-medir com `len(_KNOWN_ACTIONS)` antes de assinar), o item 2
   sai com **3** linhas no SPEC v2.59, e `ledger_entry_rejected` ganha emitter
   próprio (`emit_ledger_entry_rejected`, allowlist deny-by-default + scrub,
   nunca em `_EMIT_GENERIC_PASSTHROUGH`) — o breadcrumb-only de
   `scanner_unavailable`/`oversize`/`malformed_input` deixa de ser residual.
   Atenção ao NÚMERO do ADR deste pack: `ADR-194` foi tomado pelo PLAN-183
   (`ADR-194-delivery-route-resolution.md`, landado em `6304f66`); o ADR do
   pack renumera para **ADR-195** (próximo livre, medido S328; contagem de
   ADRs 195 → 196) e toda referência interna (hook, testes, ADR) acompanha.
2. **`SPEC/v1/audit-log.schema.md`**: linhas novas (**3** — decidido no item 1).
   **A versão é v2.59**, não v2.57: o SPEC vivo já tem v2.56 (linha 583, este
   plano), v2.57 (584, PLAN-174/SENT-S318) e v2.58 (585, PLAN-182/SENT-S319).
   Lembrar do `PACKMAP.txt` — o artefato do pack tem nome plano porque
   `Edit(SPEC/**)` (`.claude/settings.json:784`) nega até dentro do pack.
3. **`.claude/settings.json`**: a registração do hook (JSON exato no retorno do
   agente) — e o espelho em `templates/settings/settings.base.json`, senão o
   adopter recebe o arquivo sem a registração. **Foi exatamente esse o buraco
   que a suíte completa pegou no w01**; o teste de paridade template/dogfood é
   quem o denuncia.
4. **Pins de contagem irmãos**: somar as ações move `_KNOWN_ACTIONS` de
   **327** (medido) para 329 (2 ações) ou 330 (3) e quebra **cinco** arquivos
   de teste que pinam esse global — lista CONFIRMADA por grep do literal:
   `test_audit_emit_api_contract.py:820` e `:839` (o único dono legítimo do
   contrato, e também o dono do digest `_EXPECTED_KNOWN_ACTIONS_SHA256` na
   linha 518 — RE-DERIVE o sha, nunca edite à mão),
   `test_audit_emit_plan163_lifecycle_actions.py:171`,
   `test_codex_egress_proof_telemetry.py:123`,
   `test_git_bypass_guard.py:885`, `test_w5_scrub_enforcement.py:95`.
5. **`.claude/data/audit-registry.golden.txt`** (ITEM NOVO — faltava nesta
   lista). `check-audit-registry-coverage.py --check` regenera o golden em
   memória e compara com o arquivo em disco (hoje 331 linhas, verde). Somar
   ação sem regenerar deixa o gate VERMELHO. Regenerar com `--write-golden`
   no MESMO commit. É não-canônico por `_is_canonical`, mas o `staged-w01` o
   levou no Scope assinado (`W179-approved.md:25`) — leve também.
6. **Contagens derivadas**: 1 hook + 1 módulo `_lib` + 1 ADR novos ⇒
   hooks **58→59**, ligados **47→48**, registros **49→50**,
   `_lib` **70→71** (NÃO 69→70 — vivo já é 70), ADRs **194→195** (esta
   quarta contagem faltava aqui). **Derive as superfícies do
   `verify-counts.sh`, nunca de memória** — ele vigia 11 docs
   (`CLAUDE.md README.md README.pt-BR.md INSTALL.md docs/ARCHITECTURE.md
   docs/GUIA-COMPLETO.md docs/FAQ.md docs/README.md docs/WHAT-WE-ARE.md
   docs/CTO-GUIDE.md npm/README.md`, linhas 548-551) e mesmo assim deixa
   sites de PROSA cegos: o sentinel do w01 (`W179-approved.md:132-133`)
   nomeia `README.md:62`, `npm/README.md:62`, `docs/ARCHITECTURE.md:76-77`
   e `CLAUDE.md:53`, e a varredura de hoje achou também
   `docs/CTO-GUIDE.md:49`, `docs/README.md:79` e `:86`,
   `docs/ARCHITECTURE.md:47` e `:68`. Varra por número, não por regra.
7. **`check_contamination.py` — a premissa está INVERTIDA.** O texto anterior
   e o próprio plano (linha 448-449) diziam que a contaminação "cobre o path
   novo". FALSO, medido: `.claude/scripts/check_contamination.py:240` tem
   `".claude/plans/*"` em `_ALLOWLIST_GLOBS` e o comentário :232-234 declara
   que aqui o fnmatch `*` ATRAVESSA `/`. Teste de fnmatch:
   `.claude/plans/PLAN-NNN/LEDGER.md` casa esse glob. A árvore de planos
   INTEIRA está ISENTA. A cura é uma EXCEÇÃO NEGATIVA para a classe
   `LEDGER.md`, não "adicionar cobertura" (o repo é público). O script é
   NÃO-canônico — cabe fora da cerimônia.

## Como montar, quando chegar a hora

```bash
# 0. PRE-CHECK obrigatório: assemble_pack mapeia pack-path -> destino 1:1.
#    Os dois DOCS deste pack (README-COMO-MONTAR.md, SESSIONEND-NOTE.md) NÃO
#    têm destino no repo. Sem o skip de PACK-DOC em assemble_pack.py:65-70
#    eles entram no MANIFEST como NEW na RAIZ e o G5 do land os copia para
#    lá, dentro do Scope ASSINADO. Confira que o manifesto sai com 5
#    entradas, não 7, e que nenhuma linha é um path de raiz.
# 1. o w01 JÁ LANDOU (verificado: check_compact_pinning.py,
#    check_precompact_continuity.py, check_postcompact_reinject.py,
#    _lib/pinned_constraints.py e _lib/state_store.py presentes vivos;
#    SPEC vivo com a linha v2.56). Árvore limpa.
python3 .claude/plans/PLAN-179/assemble_pack.py .claude/plans/PLAN-179/staged-w24
# 1b. MANIFEST/BASELINE têm de ser COMMITADOS: staged-w24/ NÃO é gitignored
#     (git check-ignore rc=1; a regra .gitignore:17 é `staged/`, que casa só
#     diretório com esse nome literal). git add dos dois arquivos gerados.
# 2. gerar o bloco ## Scope do draft a partir do MANIFEST (o gate G2b compara)
# 3. simular o land num clone: py_compile, testes, validate-governance,
#    verify-counts, claims — rc AGREGADO por comando
# 4. suíte COMPLETA de hooks no clone, com PYTHONDONTWRITEBYTECODE=1
# 5. só então assinar
```

O land script já existe: `.claude/plans/PLAN-179/OWNER-W179-W24-LAND.sh`
(copiado do molde do w01 — `OWNER-W179-LAND.sh` — com `ST` apontando para
`staged-w24`, o prompt do G0 e a bateria G4 trocados para os artefatos deste
pack). Os gates G0-G7, o G2b (escopo do sentinel == manifesto) e o suporte a
`PACKMAP` já estão lá. A mensagem de commit em G7 é um PLACEHOLDER — a
cerimônia preenche com a decisão real do item 1 (**3 ações** — decidido pelo
Owner em 2026-08-25) antes de assinar.
