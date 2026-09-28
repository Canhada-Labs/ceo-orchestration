# wave-opus55 — rail codex rodada 4 (contada, a FINAL; sombra 19771fa1 + WOPUS55.patch re-derivado r16d, 2026-09-25T03Z S357)

Rail-Verdict: APPROVE

## Sujeito revisado

- Patch: `.claude/plans/PLAN-193/wave-opus55/WOPUS55.patch`, sha256
  `ed3dd91435608e54b6dd88396f4b16071bab3f81b0dff2c107df4797597cb6df`
  (457.706 bytes). É igual byte a byte ao blob commitado em
  `5d6c9dc532b7`, a r16d que re-derivou o patch depois da fix round r16,
  e ao blob do HEAD `d9aa1e2264fc`. É o sha256 pinado em `Patch-sha256:`
  no sentinel (`wave-opus55-approved.md`) e no `PROPOSED-PATCH.md`.
- Base: `19771fa18257` (HEAD da sombra, destacado).
- Sombra: `git worktree add --detach <shadow-r4> 19771fa18257` +
  `git -C <shadow-r4> apply WOPUS55.patch` (não commitado) ⇒ 76 arquivos
  modificados, `5129 insertions(+), 618 deletions(-)`, nenhum untracked.
  Removida ao fim com `git worktree remove --force <shadow-r4>`.
- `<shadow-r4>` = `<scratchpad S357>/r4/shadow`. O prefixo absoluto do
  scratchpad foi trocado pelo marcador neste registro. O veredito abaixo
  não cita nenhum path e está verbatim.

## Substrato

- `codex --version` = `codex-cli 0.156.1` (launcher npm global
  `@openai/codex` 0.156.1, `/opt/homebrew/bin/codex` →
  `../lib/node_modules/@openai/codex/bin/codex.js`).
- Payload nativo resolvido pelo launcher,
  `@openai/codex-darwin-arm64/vendor/aarch64-apple-darwin/bin/codex`
  (238.138.912 bytes), sha256
  `0196e89fe5a7598f816ee54232c3d7c26d75e502ab5cfe2c9240e81d90f7255a`.
  É o mesmo payload das rodadas 2 e 3.
- Cabeçalho da sessão: `model: gpt-6-astra`, `reasoning effort: max`,
  `sandbox: workspace-write [workdir, /tmp, $TMPDIR]`,
  `approval: on-request`, session id
  `01a0d6ad-117e-7952-9dbd-bfe25cec0b5c`.
- Nota de substrato (igual às rodadas 2 e 3): 0.156.1 é a versão que o
  pacote W2 de re-pin (branch `s357/codex-pin`) pina. O manifesto vivo em
  `19771fa1` ainda pina 0.155.0, e o pacote W2 é landado ANTES de esta
  wave ser assinada. Esta rodada roda no revisor que estará pinado na
  assinatura, não no pin da base.

## Comando

`codex exec review --uncommitted --skip-git-repo-check
-c sandbox_mode="workspace-write"`, do diretório da sombra, stdin
`</dev/null`, watchdog de 3.600 s (`perl alarm` + `exec`; não disparou).
Lançado destacado do processo que o chamou. Início
2026-09-25T03:47:41Z, fim 03:54:38Z, rc 0. Saída bruta:
`<scratchpad S357>/r4/rail-r4.txt` (10.649 linhas, 606.158 bytes, sha256
`77c599f6488df09525874f1594dfcd0e5c01bc251940da1ba640bad195571d71`).
Snapshot sha256 de (`git diff --binary` + `status --porcelain -z
--untracked-files=all`) antes/depois:
`a4a36e7dc1c5026dbca58db12a2576149709b84077fed0f29014418fe55bc6f9` nos
dois lados ⇒ TREE-INTACT.

Houve uma única execução. Nenhuma tentativa sem veredito precedeu esta
rodada.

## Veredito do codex, verbatim

(O codex imprime a linha final duas vezes, idênticas; transcrita uma vez.)

```
APPROVE: No actionable regressions found. Focused tests and model-generation, environment-hygiene, and installer-safety checks passed.
```

Achados: 0. A saída não tem nenhum bloco `Review comment` /
`Full review comments` e nenhum item `[P0]`–`[P3]` (`grep -c
'\[P[0-3]\]'` = 0 nas 10.649 linhas). O P2 da rodada 3 (dica de
re-execução da saída de falha do helper T5.4 sem as flags do operador)
e os achados das rodadas 1 e 2 não aparecem no veredito.

## Conferência na sombra (verificador, não o codex)

- Não há achado a confirmar. O que segue confere o que o codex executou
  e a cura da rodada 3, lendo a sombra.
- Execuções do codex registradas na saída:
  - um lote pytest com 414 testes, `414 passed in 53.84s`;
  - `check-test-env-hygiene.py` (`OK: test-env hygiene clean (337
    flagged files, all allowlisted)`), `generate-available-models.py
    --check` (`CHECK availableModels: MATCH (8 ids, ADR order
    preserved)`) e `check-installer-write-safety.py --json` (`"ok":
    true`, `new_blocking: []`, `dead_baseline_entries: []`,
    `malformed_baseline_rows: []`);
  - um segundo lote pytest, `1 failed, 627 passed, 2 skipped in
    12.62s`. A falha é
    `test_gen_settings_user_template.py::GeneratorRuntimeContract::test_compiles`,
    com `PermissionError: [Errno 1] Operation not permitted` no
    `os.makedirs` que o `py_compile.compile` faz para gravar o `.pyc` em
    `~/Library/Caches/com.apple.python/<path da sombra>`. Esse diretório
    fica fora das raízes graváveis do sandbox do codex
    (`[workdir, /tmp, $TMPDIR]`). O codex re-executou o mesmo teste com
    `-X pycache_prefix=<mktemp em /private/tmp>` e obteve `1 passed in
    0.35s`.
- A falha é do sandbox do revisor, não do patch. Conferência
  independente: `python3 -X pycache_prefix=<scratchpad S357>/r4/pyc-check
  -m py_compile <shadow-r4>/.claude/scripts/gen-settings-user-template.py`
  ⇒ rc 0. O gerador (`gen-settings-user-template.py`) não está entre os
  76 paths do patch. O teste `test_compiles` já existe na base
  `19771fa1` (`:1937`). O patch toca o arquivo de teste em 5 linhas
  (`+5 −1`), fora desse teste.
- A cura da rodada 3 está na sombra: a rotina única `_t54_rerun_cmd`
  (`scripts/upgrade.sh:3576-3592`) monta o comando com
  `--adopt-setting <key>` para cada chave de `ADOPT_SETTINGS`,
  `--allow-old-claude-code`, `--pin` (citado com `printf %q`) e
  `--dry-run`, e cita o alvo com `printf %q`. As três saídas da migração
  que deixam o `settings.json` sem migrar a usam: python3 ausente
  (`:3604`), backup impossível (`:3635`) e falha do helper, exit 3
  (`:4113`). Nenhuma delas monta o comando à mão.
- A saída do codex foi varrida por instruções embutidas (padrões
  `ignore previous`, `disregard`, `Rail-Verdict:`): nenhuma ocorrência.

## Decisão do Owner que rege esta rodada (OQ-10)

Registrada no plano
`PLAN-193-release-v1-4-2-opus55-fasttrack.md` (cópia de hold do Owner,
`:159-164`), verbatim:

> OQ-10 (rail W3 esgotou as 3 rodadas; r1–r3 REJECT, cada uma com UM P2
> de classe diferente, nenhum P0/P1): **RESOLVIDA 2026-09-24,
> verbatim:** «Corrigir + rodada 4 final c/ anexo (Recomendado)» — cura
> do P2 da r3 pela classe (uma rotina única monta o «rode de novo»
> preservando as flags do operador em todas as saídas de falha da
> migração) e UMA rodada 4, a última: limpa ⇒ APPROVE; só P2 ⇒
> `APPROVE-WITH-ANNEX` com anexo rastreado e assinado; P0/P1 ⇒ REJECT e
> volta ao Owner. Mesma regra «rodada final com anexo» dos cortes de
> release.

Aplicação: a rodada é limpa (zero achados, nenhum P0/P1/P2) ⇒ o
veredito é APPROVE, sem anexo. Nenhum rótulo do codex foi reclassificado.
Não se cria `rail-round-4-annex.md`.

## Consequência para a cerimônia

- Contagem da família `rail-round`: 4 de 4 (`RAIL_MAX_ROUNDS=4` no
  `OWNER-OPUS55-SIGN.sh`, `:104`). Esta é a última rodada. Um
  `rail-round-5.md` é recusado pelo NOME (`:380`), qualquer que seja o
  veredito dele.
- O P0-e do SIGN lê o `Rail-Verdict:` do último registro da família
  (`:402`) e exige `APPROVE` por igualdade exata (`:427`). Este registro
  o satisfaz, desde que commitado (`:384-385`). Não há registro na
  família `rail-materials-round`.
- O veredito vale só para o sujeito revisado: o `WOPUS55.patch` de sha256
  `ed3dd914…cb6df` sobre `19771fa1`. Qualquer re-derivação do patch
  depois deste registro muda o sujeito, e não há rodada 5 para cobri-la:
  a decisão volta ao Owner.
- O trailer da mensagem de commit ainda está
  `Pair-Rail-Reviewed: TO-FILL-AFTER-LAST-RAIL-ROUND`
  (`COMMIT-MSG-OPUS55.txt:211`), e o P0-g do SIGN recusa qualquer
  `TO-FILL`. O CEO o preenche depois deste registro. Esta rodada não o
  preenche.
