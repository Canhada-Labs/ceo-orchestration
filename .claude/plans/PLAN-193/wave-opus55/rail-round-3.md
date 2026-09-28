# wave-opus55 — rail codex rodada 3 (contada; sombra 19771fa1 + WOPUS55.patch re-derivado r15d, 2026-09-25T02Z S357)

Rail-Verdict: REJECT

## Sujeito revisado

- Patch: `.claude/plans/PLAN-193/wave-opus55/WOPUS55.patch`, sha256
  `e0f2aa33076ca3daedfcad5263feb073880c10a5c2f9fb2841f724c75c2cb625`
  (446.255 bytes; igual byte a byte ao blob commitado em `eeaccd728ebe`,
  a r15d que re-derivou o patch depois da fix round r15, e ao blob do
  HEAD `b280b9fce386`; é o sha256 pinado em `Patch-sha256:` no sentinel
  e no `PROPOSED-PATCH.md`).
- Base: `19771fa18257` (HEAD da sombra, destacado).
- Sombra: `git worktree add --detach <shadow-r3> 19771fa18257` +
  `git -C <shadow-r3> apply WOPUS55.patch` (não commitado) ⇒ 76 arquivos
  modificados, `4946 insertions(+), 616 deletions(-)`, nenhum untracked.
  Removida ao fim.
- `<shadow-r3>` = `<scratchpad S357>/converge/shadow-r3` (o prefixo
  absoluto do scratchpad foi trocado pelo marcador neste registro; no
  resto, o achado está verbatim).

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
`</dev/null`, watchdog de 3.600 s (não disparou). Início
2026-09-25T02:02:10Z, fim 02:09:59Z, rc 0. Saída bruta:
`<scratchpad S357>/converge/rail-r3.txt` (10.027 linhas, sha256
`b009a99f7227d78c36832f0834cf484bb0dda225ed2083215c43af91b7f63f34`).
Snapshot sha256 de (`git diff --binary` + `status --porcelain -z
--untracked-files=all`) antes/depois:
`2e34846f25923f6b44f65b31af4a04fc78235a0a41eec150d12b5c5137340a59` nos
dois lados ⇒ TREE-INTACT.

## Tentativa anterior sem veredito (não é rodada)

Uma execução anterior do mesmo comando começou em
2026-09-24T10:36:50Z sobre a MESMA árvore (snapshot antes idêntico,
`2e34846f…`). Ela foi morta de fora cerca de 4 minutos depois (última
escrita da saída 10:41:09Z), sem arquivo de rc, de fim ou de watchdog.
A saída termina com o codex ainda lendo contexto: nenhum bloco
`Review comment`, nenhum item `[P0]`–`[P3]` e nenhum veredito. Ela não
produziu resultado, então não gerou registro e não conta no teto. Os
bytes estão preservados em
`<scratchpad S357>/converge/rail-r3-aborted-1.txt` (8.792 linhas, sha256
`b38128d778e7fb7774d72a221632c8aba33c96460c96a345922001c471da0ecd`). A
rodada registrada aqui é a segunda execução, lançada destacada do
processo que a chamou.

## Veredito do codex, verbatim

(O codex imprime o bloco final duas vezes, idênticas; transcrito uma vez.)

```
REJECT: migration-failure recovery drops the newly introduced options and can persist an unintended effort setting. The 442 targeted tests passed, but a separate reproduction confirmed this recovery-path defect.

Review comment:

- [P2] Reuse the flag-preserving retry for helper failures — <shadow-r3>/scripts/upgrade.sh:3603-3605
  When `--adopt-setting effortLevel` is supplied and settings parsing or the atomic write fails, the later error handler still prints a retry without that flag. Following it after repairing an existing Opus 5 install writes `high` instead of the requested `xhigh`; another retry with the flag cannot correct this because present effort values are preserved. Reuse this option-preserving retry command for that failure path too, including `--allow-old-claude-code`.
```

Achados: 1 (P2). Nenhum P0/P1. Os achados das rodadas 1 (direção do
owner-sign do `tier_policy_cli`) e 2 (harness do instalador que herda o
`claude` do host) não aparecem no veredito desta rodada.

## Conferência do achado na sombra (verificador, não o codex)

- CONFIRMADO por leitura da sombra. A reprodução do codex (reparar o
  JSON e seguir a dica) NÃO foi re-executada aqui.
- A migração T5.4 do `scripts/upgrade.sh` tem duas saídas que pulam a
  escrita e imprimem um comando de re-execução:
  - backup impossível, `:3600-3615`: monta `_t54_rerun` com cada
    `--adopt-setting <key>` de `ADOPT_SETTINGS` e com
    `--allow-old-claude-code` quando `ALLOW_OLD_CLAUDE_CODE=1`
    (comentário `:3601-3602`: «The re-run keeps the flags that change
    what this migration writes»);
  - falha do helper (JSON ilegível ou escrita atômica falha, exit 3),
    `:4081-4093`: imprime `scripts/upgrade.sh "$TARGET"
    --settings-migrate-only` em `:4091`, SEM essas flags.
- As duas flags são novas no patch. Na base `19771fa1` não existem
  `ADOPT_SETTINGS`, `--adopt-setting` nem `--allow-old-claude-code`, e
  a linha da dica é a mesma (`:3736` da base). O hunk `+4078,3` do patch
  passa `"$ADOPT_SETTINGS"` ao helper em `:4080`, e o tratamento da
  falha, onze linhas abaixo, fica como estava na base.
- A consequência vem do próprio texto do script na sombra.
  `:494-497`: quando o pin sai de `claude-opus-5` num arquivo sem
  `effortLevel`, «the migration writes high instead (the Opus 5
  default) unless you pass this flag». `:493-494` e a
  `on_migrate_note` em `:217`: um valor presente nunca é sobrescrito,
  com flag ou sem. Então quem segue a dica de `:4091` depois de reparar
  o JSON grava `high`, e uma nova re-execução com
  `--adopt-setting effortLevel` não leva a `xhigh`. Sem
  `--allow-old-claude-code`, a re-execução num host abaixo do piso é
  recusada em vez de migrar.
- Censo da classe na sombra: os comandos impressos na forma
  `scripts/upgrade.sh "$TARGET" …` em `scripts/upgrade.sh` e
  `scripts/install.sh` são só esses dois (`:3603` e `:4091`), e um deles
  leva as flags. As dicas genéricas de «re-run» sem comando
  (`upgrade.sh:3449`, `:6064`, `:6098`) não foram avaliadas aqui. Pela
  regra «cure a CLASSE» (CLAUDE.md §4), a cura é UM construtor do
  comando de re-execução usado pelas DUAS saídas da migração, com um
  teste que força a falha do helper (settings.json ilegível) com
  `--adopt-setting effortLevel` e `--allow-old-claude-code` e confere a
  dica. A cura passa pelos módulos do derivador (`edits_core.py` /
  `edits_pricing.py`) e pela re-derivação, nunca pelo patch à mão.

## Consequência para a cerimônia

- Esta rodada NÃO autoriza assinatura. O P0-e do `OWNER-OPUS55-SIGN.sh`
  exige `Rail-Verdict: APPROVE` por igualdade exata no último registro da
  família `rail-round` (`:387-392`).
- Contagem da família `rail-round`: 3 de 3 (`RAIL_MAX_ROUNDS=3`, regra de
  parada pré-registrada). O teto foi atingido. Com este registro como o
  último, o SIGN aborta no veredito (`:388`). Um `rail-round-4.md` faria
  a contagem passar do teto, e o SIGN aborta em `:370` («regra de
  parada»), qualquer que seja o veredito dele. A decisão volta ao Owner.
  Uma rodada a mais não é o próximo passo.
- A classe deste achado (dica de re-execução de uma saída de falha que
  perde as flags do operador) é diferente das classes das rodadas 1
  (ordem da tupla no caminho de assinatura) e 2 (harness de teste que
  herda o ambiente do host). O teto humano de 2 rodadas por CLASSE não
  foi atingido por nenhuma das três.
- O achado é sobre bytes do patch (`scripts/upgrade.sh` está entre os 76
  paths), não sobre material ⇒ o veredito de ANEXO não se aplica (só
  vale na família `rail-materials-round`).
