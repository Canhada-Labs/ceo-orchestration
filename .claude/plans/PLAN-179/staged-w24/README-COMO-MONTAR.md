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

## O que a cerimônia AINDA DEVE (reportado pelos próprios agentes)

1. **`audit_emit.py`**: registrar `ledger_checkpoint_recorded` e
   `ledger_checkpoint_skipped` em `_KNOWN_ACTIONS`, cada um com allowlist
   deny-by-default + branch de scrub. **Nunca** em `_EMIT_GENERIC_PASSTHROUGH`.
   Os campos e enums fechados estão listados no retorno do agente do hook.
2. **`SPEC/v1/audit-log.schema.md`**: duas linhas novas. O `staged-w01` toma a
   **v2.56**, então este é **v2.57**. Lembrar do `PACKMAP.txt` — o artefato do
   pack tem nome plano porque `Edit(SPEC/**)` nega até dentro do pack.
3. **`.claude/settings.json`**: a registração do hook (JSON exato no retorno do
   agente) — e o espelho em `templates/settings/settings.base.json`, senão o
   adopter recebe o arquivo sem a registração. **Foi exatamente esse o buraco
   que a suíte completa pegou no w01**; o teste de paridade template/dogfood é
   quem o denuncia.
4. **Pins de contagem irmãos**: somar 2 ações move `_KNOWN_ACTIONS` de 325 para
   327 e quebra **cinco** arquivos de teste que pinam esse global
   (`test_audit_emit_api_contract` — o único que legitimamente é dono do
   contrato, com o digest — mais `plan163_lifecycle_actions`,
   `codex_egress_proof_telemetry`, `git_bypass_guard`, `w5_scrub_enforcement`).
5. **Contagens derivadas**: 1 hook + 1 módulo `_lib` novos ⇒ hooks 58→59,
   ligados 47→48, registros 49→50, `_lib` 69→70. **Derive as superfícies do
   `verify-counts.sh`, nunca de memória** — e lembre dos 5 sites de PROSA que
   nenhuma regra vigia (documentados no sentinel do w01).
6. **`check-contamination`** precisa cobrir a classe de path `LEDGER.md` (o
   repo é público).

## Como montar, quando chegar a hora

```bash
# 1. o w01 já landou e foi pushado; árvore limpa
python3 <scratchpad>/assemble_pack.py .claude/plans/PLAN-179/staged-w24
# 2. gerar o bloco ## Scope do draft a partir do MANIFEST (o gate G2b compara)
# 3. simular o land num clone: py_compile, testes, validate-governance,
#    verify-counts, claims — rc AGREGADO por comando
# 4. suíte COMPLETA de hooks no clone, com PYTHONDONTWRITEBYTECODE=1
# 5. só então assinar
```

O land script do w01 (`OWNER-W179-LAND.sh`) serve de molde: os gates G0-G7,
o G2b (escopo do sentinel == manifesto) e o suporte a `PACKMAP` já estão lá.
