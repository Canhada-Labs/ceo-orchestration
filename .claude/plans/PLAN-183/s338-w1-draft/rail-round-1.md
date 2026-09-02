Rail-Verdict: CHANGES-REQUESTED (1 P1 + 3 P2; 3 curados no r4, 1 P2 DEFERIDO para o /debate — OQ-5)

# Pair-rail — rodada 1 (codex exec review --uncommitted, dentro da sombra)

- Sombra revisada: `…/scratchpad/shadow-183w1` em BASE `f0e98de`+fable51 (commit
  interno `81edc0f`) + `apply-w1-edits.py` (estado r3).
- Comando: `codex exec review --uncommitted --skip-git-repo-check -c sandbox_mode="workspace-write" </dev/null > codex-r1.txt 2>&1`
  (rc 0; saída bruta em `codex-r1.txt` [saída bruta, NÃO versionada — scratchpad S338 `codex-logs/s338-w1-draft/`], 451 KB — o codex leu CLAUDE.md, os
  testes, o censo, o gate nightly, e sondou paths com espaços na sombra).
- `git diff | shasum -a 256` ANTES = DEPOIS =
  `f1375a5233e8704d3b04a431c573adee4635d49600b0c9bd306cb5fb47de4757` ⇒
  **TREE-INTACT** (`git status --short` idêntico: 9 M + 1 ??).
- Resumo do codex (verbatim): «The main path works, but valid legacy
  installations can be preserved incorrectly or re-pointed to the wrong
  checkout, and the recognizer violates dry-run confinement under supported
  environment configurations. The dedicated portability regression test is
  also not executed by CI.»

## Achados

| # | Sev | Achado (codex) | Verificado | Disposição |
|---|---|---|---|---|
| 1 | **P1** | `upgrade.sh` precedência 0.5: um corpo legado byte-exato cujo checkout tem `+`, `@`, `:` ou não-ASCII passa no reconhecedor mas é DESCARTADO por `_ptr_source_value_ok`; o valor gravado cai no mesmo filtro; a resolução cai em `$SOURCE_DIR` e o OBSERVE ainda classifica `legacy_absolute` ⇒ REFRESH re-aponta para OUTRO checkout — quebra a promessa «mesmo checkout, só a forma migra». | **REAL** — por leitura: o OBSERVE chamava o reconhecedor sem o allowlist; a resolução aplicava o allowlist. Inconsistência entre as duas metades. | **CURADO (r4):** o reconhecedor roda UMA vez na resolução e guarda `_ptr_leg` + `_ptr_leg_ok`; o OBSERVE só classifica `legacy_absolute` quando o valor que SERÁ renderizado é o do próprio arquivo (`_ptr_leg_ok`) ou o explícito aceito (`_ptr_explicit_ok`). Valor não representável sem flag ⇒ `edited` ⇒ PRESERVED + WARNING (a). Nunca `$SOURCE_DIR` por fallback. |
| 2 | P2 | `_protocol_pointer_legacy_source`: o regex exigia TARGET de um token; um install antigo em `/tmp/my app` gerou a linha com espaços verbatim ⇒ corpo do framework classificado `edited`, sem cura. | **REAL** — o codex reproduziu na sombra (`/tmp/source tree` ⇒ «rejected»). | **CURADO (r4):** split ANCORADO À DIREITA por expansão de parâmetro (`##* --stack `, `% --stack *`, `##* --profile `, `% --profile *`); checkout e target podem ter espaços; o `cmp` byte-exato segue sendo o gate. Teste novo **R11d** (checkout E target com espaços ⇒ reconhecido, fonte verbatim). O residual R7 do reconhecedor `degraded` (PLAN-168) NÃO é tocado — fora do escopo. |
| 3 | P2 | `mktemp "${TMPDIR:-/tmp}/ceo-ptr-legacy.XXXXXX"`: com `TMPDIR` dentro de `$TARGET` o scratch nasce dentro do repo do adopter, inclusive em `--dry-run`; `upgrade.sh` tem `_up_tmpbase` para essa classe. | **REAL** — mesma classe do rail round-5 F3 do PLAN-161; o irmão `_protocol_pointer_is_degraded` tem o MESMO defeito (pré-existente, PLAN-168 — não tocado aqui, anotado como FU). | **CURADO (r4):** sem arquivo temporário: a reconstrução é canalizada para `cmp -s -` (o mesmo padrão que `_refresh_protocol_pointer` já usa na rota 2). Zero scratch, em qualquer `TMPDIR`. Colateral: −2 sítios do censo (`mktemp`, `> "$tmp"`). |
| 4 | P2 | `test-protocol-pointer-portable.sh` não é referenciado por workflow nem runner; o render roda per-PR em `smoke-install.yml:480`, o INV-4 no nightly; o e2e novo pode regredir com tudo verde. | **REAL** — já era a OQ-5 do DESIGN; medido: 316–327 s local. | **DEFERIDO ao /debate (OQ-5), NÃO curado neste draft:** o wire é um `run:` novo em `.github/workflows/smoke-install.yml` (canônico, oráculo 1) ao lado do step «Protocol pointer render control» (`:477-480`), mais a linha nos `paths:` filters (`:95-96`/`:169-170`), e um bump de `timeout-minutes` medido — decisão de escopo canônico + orçamento que o brief reserva ao Owner. Recomendação registrada no DESIGN §8 (per-PR ao lado do render; +5 min). |

## O que muda no r4 (todo via `apply-w1-edits.py`, sombra re-derivada do zero)

- `scripts/upgrade.sh`: resolução/OBSERVE conforme #1.
- `scripts/_framework_manifest_set.sh`: `_protocol_pointer_legacy_source` conforme #2 e #3; cabeçalho atualizado.
- `scripts/tests/test-protocol-pointer-render.sh`: **R11d** novo (#2).
- `scripts/tests/test-protocol-pointer-portable.sh`: P2 re-fonteado (install a partir da CÓPIA MOVIDA do P1; `P2a2` lê o valor gravado; `P2g` exige valor persistido ≠ gravado) — achado do CONTROLE POSITIVO, não do codex: `P2g` passava na árvore sem cura porque o valor de reparo coincidia com o do install.
- Baseline do censo re-gerado pelo pós-passo (as linhas mudam de número).
