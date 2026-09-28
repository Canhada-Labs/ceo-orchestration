# wave-opus55 — rail codex rodada 2 (contada; sombra 19771fa1 + WOPUS55.patch re-derivado r14, 2026-09-24 S357)

Rail-Verdict: REJECT

## Sujeito revisado

- Patch: `.claude/plans/PLAN-193/wave-opus55/WOPUS55.patch`, sha256
  `378273c9bf554ed0d08ea9ab6c1dffe1f93d95c1738621fc29c61092bebf0d73`
  (370.952 bytes; igual byte a byte ao blob commitado em `3d0b3f525efe`,
  a fix round r14 que curou o P2 da rodada 1 nos módulos do derivador).
- Base: `19771fa18257` (HEAD da sombra, destacado).
- Sombra: `git worktree add --detach <shadow-r2> 19771fa18257` +
  `git -C <shadow-r2> apply WOPUS55.patch` (não commitado) ⇒ 51 arquivos
  modificados, `3794 insertions(+), 616 deletions(-)`, nenhum untracked.
  Removida ao fim.
- `<shadow-r2>` = `<scratchpad S357>/converge/shadow-r2` (o prefixo
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
  pina 0.155.0 (`codex-cli-pin-manifest.json`, payload `b0b14f9c…`), e o
  pacote W2 é landado ANTES de esta wave ser assinada. Esta rodada,
  portanto, roda no revisor que estará pinado na assinatura, não no pin
  da base.

## Comando

`codex exec review --uncommitted --skip-git-repo-check
-c sandbox_mode="workspace-write"`, do diretório da sombra, stdin
`</dev/null`. Início 2026-09-24T08:24:40Z, fim 08:33:42Z, rc 0. Saída
bruta: `<scratchpad S357>/converge/rail-r2.txt` (8.851 linhas).
Snapshot sha256 de (`git diff --binary` + `status --porcelain -z
--untracked-files=all`) antes/depois:
`ea5d550d3db79351f6e31e3982fbd4a83e9accf1cadb263fc32d3d443f109d86` nos
dois lados ⇒ TREE-INTACT.

## Veredito do codex, verbatim

(O codex imprime o bloco final duas vezes, idênticas; transcrito uma vez.)

```
REJECT: the new CLI prerequisite causes reproducible, host-dependent failures in existing installer tests whose harnesses were not updated.

Review comment:

- [P2] Stub the CLI probe across the remaining installer tests — <shadow-r2>/scripts/install.sh:860-861
  When `claude` 2.1.279 is on PATH, existing tests in `test_install_user_no_writes_outside_claude.py` and `tests/integration/test_install_smoke.py` now fail with exit 6 before exercising installation. Reproduced with a fake CLI; the former passes when the fake reports 2.1.280. These harnesses still inherit PATH, unlike the selected suites updated here. Extend the fake-CLI fixture to the remaining installer harnesses without weakening the production check, consistent with the [environment-isolation rule](AGENTS.md#L24).
```

Achados: 1 (P2). Nenhum P0/P1. O achado da rodada 1 (direção do
owner-sign do `tier_policy_cli`) não foi reaberto.

## Conferência do achado na sombra (verificador, não o codex)

- CONFIRMADO. Na sombra, `scripts/install.sh:783` fixa
  `CC_FLOOR_VERSION="2.1.280"`, e `install.sh:860-861` sai com
  `exit 6` quando `_claude_code_floor_check` recusa (execução real, sem
  `--dry-run` e sem `--allow-old-claude-code`). `scripts/upgrade.sh`
  traz o mesmo piso (`:620`, chamada em `:697`).
- Controle executado: um `claude` falso que responde
  `2.1.279 (Claude Code)`, à frente do PATH, e `bash scripts/install.sh`
  da sombra contra um alvo descartável em `<scratchpad S357>/converge/`
  ⇒ `rc=6`, com a mensagem `ERROR: Claude Code 2.1.279 is below
  2.1.280, the minimum of this release (SUPPORT.md): nothing was
  written. …`. O alvo ficou só com o `.git` que o controle criou. O
  snapshot da sombra continuou `ea5d550d…` depois do controle. A perna
  2.1.280 do codex e as duas suítes pytest NÃO foram re-executadas aqui.
- Os dois harnesses citados herdam o PATH do ambiente e NÃO estão entre
  os 51 paths do patch:
  `.claude/scripts/tests/test_install_user_no_writes_outside_claude.py`
  (`_install_env()` = `dict(os.environ)` + duas flags) e
  `tests/integration/test_install_smoke.py` (`subprocess.run` sem
  `env=`). Nesta máquina o `claude` do PATH é `2.1.281`, acima do piso,
  e por isso a falha não aparece aqui. É dependente do host: aparece
  numa máquina de desenvolvimento com `claude` < 2.1.280 no PATH. Sem
  `claude` no PATH (CI) o piso só avisa.
- A CLASSE é mais larga que os dois exemplos. Um grep TEXTUAL por
  `install.sh|upgrade.sh` em arquivos de teste da árvore viva (fora de
  `.claude/plans/` e `tests/fixtures/`) acha 69 arquivos: 4 estão no
  patch e 65 não. É um SUPERCONJUNTO (parte só cita o nome, sem
  executar o instalador), não uma contagem de testes que falham. Pela
  regra «cure a CLASSE» (CLAUDE.md §4), a cura é isolar o `claude` do
  PATH em TODO harness que executa `install.sh`/`upgrade.sh`, de
  preferência num ponto único, com um guard que ache harness novo sem o
  isolamento. Não é cura só acrescentar o fixture aos dois arquivos
  citados, nem relaxar o piso de produção.

## Consequência para a cerimônia

- Esta rodada NÃO autoriza assinatura. O P0-e do `OWNER-OPUS55-SIGN.sh`
  exige `Rail-Verdict: APPROVE` por igualdade exata no último registro da
  família `rail-round`.
- Contagem da família `rail-round`: 2 de 3 (`RAIL_MAX_ROUNDS=3`, regra de
  parada pré-registrada). A próxima rodada, `rail-round-3.md`, é a
  ÚLTIMA dentro do teto. Ela roda sobre o patch RE-DERIVADO pelos
  módulos do derivador (`edits_core.py` / `edits_pricing.py`), nunca
  editado à mão. Se a rodada 3 não for limpa, o SIGN recusa a 4.ª
  (`regra de parada`) e a decisão volta ao Owner.
- A classe deste achado (harness de teste herda o ambiente do host) é
  diferente da classe da rodada 1 (ordem da tupla no caminho de
  assinatura). O teto humano de 2 rodadas por CLASSE ainda não foi
  atingido por nenhuma das duas.
- O achado é sobre bytes canônicos do patch (o piso novo no
  `install.sh` e a suíte que o acompanha), não sobre material ⇒ o
  veredito de ANEXO não se aplica (só vale na família
  `rail-materials-round`).
