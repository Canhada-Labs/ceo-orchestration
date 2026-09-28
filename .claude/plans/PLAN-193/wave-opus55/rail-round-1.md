# wave-opus55 — rail codex rodada 1 (contada; sombra 19771fa1 + WOPUS55.patch, 2026-09-24 S357)

Rail-Verdict: REJECT

## Sujeito revisado

- Patch: `.claude/plans/PLAN-193/wave-opus55/WOPUS55.patch`, sha256
  `587df9f48db274e896b03ca82aebe68f1ca07eec124d73af0ee93891cbab1291`
  (362.151 bytes; igual byte a byte ao blob commitado em `4d9feebc17a7`).
- Base: `19771fa18257` (HEAD da sombra, destacado).
- Sombra: `git worktree add --detach <shadow-r1> 19771fa18257` +
  `git -C <shadow-r1> apply WOPUS55.patch` (não commitado) ⇒ 49 arquivos
  modificados, `3632 insertions(+), 612 deletions(-)`. Removida ao fim.
- `<shadow-r1>` = `<scratchpad S357>/converge/shadow-r1` (o prefixo
  absoluto do scratchpad foi trocado pelo marcador neste registro; no
  resto, os achados estão verbatim).

## Substrato

- `codex --version` = `codex-cli 0.156.1` (launcher npm global
  `@openai/codex` 0.156.1).
- Payload nativo resolvido pelo launcher,
  `@openai/codex-darwin-arm64/vendor/aarch64-apple-darwin/bin/codex`
  (238.138.912 bytes), sha256
  `0196e89fe5a7598f816ee54232c3d7c26d75e502ab5cfe2c9240e81d90f7255a`.
- Cabeçalho da sessão: `model: gpt-6-astra`, `reasoning effort: max`,
  `sandbox: workspace-write`, `approval: on-request`.
- Nota de substrato: 0.156.1 é a versão que o pacote W2 de re-pin
  (branch `s357/codex-pin`) pina. O manifesto vivo em `19771fa1` ainda
  pina 0.155.0, e o pacote W2 é landado ANTES de esta wave ser assinada.
  Esta rodada, portanto, roda no revisor que estará pinado na
  assinatura, não no pin da base.

## Comando

`codex exec review --uncommitted --skip-git-repo-check
-c sandbox_mode="workspace-write"`, do diretório da sombra, stdin
`</dev/null`. Início 2026-09-24T07:28:41Z, fim 07:36:01Z, rc 0. Saída
bruta: `<scratchpad S357>/converge/rail-r1.txt` (9.571 linhas).
Snapshot sha256 de (`git diff --binary` + `status --porcelain -z
--untracked-files=all`) antes/depois:
`0ead1d2f7a7f88321e270c239576622bd2da8023618dcc58c113e68568556d13` nos
dois lados ⇒ TREE-INTACT.

## Veredito do codex, verbatim

(O codex imprime o bloco final duas vezes, idênticas; transcrito uma vez.)

```
REJECT: newly supported Opus 5.5 transitions can be signed with an inverted promotion/demotion label. The 398 focused tests pass, but do not cover this signing-path inconsistency.

Review comment:

- [P2] Align owner-sign with the new model's tier ordering — <shadow-r1>/.claude/scripts/tier_policy_cli/_types.py:44-46
  For the newly accepted Fable 5.1 → Opus 5.5 transition, `tier_policy_cli/cli.py:357–360` still determines the signed action using `VALID_MODEL_IDS.index()`. Appending Opus 5.5 after both Fable entries therefore produces `action="promote"`, whereas `learn._direction()` correctly returns `"demote"`; the reverse transition is also mislabeled. This records the opposite operation in the Owner-signed audit chain. Have `cmd_owner_sign()` use the same tier-ranking logic and test the signing path.
```

Achados: 1 (P2). Nenhum P0/P1.

## Conferência do achado na sombra (verificador, não o codex)

- CONFIRMADO. Na sombra, `VALID_MODEL_IDS` (`_types.py`) termina em
  `claude-fable-5-1` (índice 6) e `claude-opus-5-5` (índice 7).
  `cli.py:357-360` decide
  `action = "promote" if index(to) > index(from) else "demote"`. Já
  `learn._tier_rank` dá `claude-opus-5-5 = 6` e `claude-fable-5-1 = 8`.
  Resultado: `fable-5-1 → opus-5-5` é assinado como `promote`, e
  `_direction` diz `demote`; o sentido inverso também sai trocado.
- `cli.py` NÃO está entre os 49 paths do patch: o patch mexe só em
  `_types.py`, `learn.py`, `tests/test_learn_mutation.py` e
  `tests/test_types.py` dentro de `tier_policy_cli/`.
- A CLASSE é anterior ao patch. Na base `19771fa1` a tupla já não segue
  a ordem de tier (`claude-fable-5` no índice 0, `claude-opus-4-8` no 1).
  Pelo `index()`, `fable-5 → opus-5` já saía assinado como `promote`
  antes do patch. O patch estende a classe ao id novo. Pela regra «cure a
  CLASSE» (CLAUDE.md §4), a cura é o `cmd_owner_sign()` deixar de ler a
  ordem da tupla e usar a mesma autoridade de ranking do `learn`, com um
  teste do caminho de assinatura. Acrescentar o id em outra posição da
  tupla não é cura.

## Consequência para a cerimônia

- Esta rodada NÃO autoriza assinatura. O P0-e do `OWNER-OPUS55-SIGN.sh`
  exige `Rail-Verdict: APPROVE` por igualdade exata no último registro da
  família `rail-round`.
- Contagem da família `rail-round`: 1 de 3 (`RAIL_MAX_ROUNDS=3`, regra de
  parada pré-registrada). A próxima rodada vira `rail-round-2.md`, sobre
  o patch RE-DERIVADO pelos módulos do derivador (`edits_core.py`), nunca
  editado à mão.
- O achado é sobre bytes canônicos do patch (caminho de assinatura do
  Owner, na cadeia de auditoria), não sobre material ⇒ o veredito de
  ANEXO não se aplica (só vale na família `rail-materials-round`).
