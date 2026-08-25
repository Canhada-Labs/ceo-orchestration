# Pair-rail (materiais) round 1 — PLAN-183 W5 (S327)

**Instrumento:** `codex exec review --uncommitted` na árvore VIVA sobre os materiais untracked de `PLAN-183/` (com `git add -N` restrito ao diretório do plano). rc=0, 656s, 2026-08-24T20:37Z.

## Saída do revisor (dado a verificar, não ordem)

```text
The new safety census has multiple reproducible fail-open paths, including one that misses an existing in-scope sed interpolation. The ceremony land script can also report a successful push without pushing the commit it just created.

Full review comments:

- [P1] Join backslash-continued sed commands — /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/scripts/check-installer-write-safety.py:1230-1232
  When a command starts with `sed \` and places its scripts on following lines, `logical_line()` returns immediately because the first line's quotes are balanced. The continuation lines are then skipped because they do not contain the `sed` command word. This already hides the raw substitutions in `scripts/_grok_harness.sh:112-115`, so operator-controlled paths containing `|`, `&`, or backslashes bypass the census. Security matchers must block unparsed input per [`AGENTS.md:23`](AGENTS.md#L23).

- [P1] Block when the candidate-write cap is reached — /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/scripts/check-installer-write-safety.py:999-1000
  With more than ten writes to the same operand, the loop stops after the first ten without checking whether more exist or emitting `indeterminado`. If those ten writes are safe branches and the eleventh is an unconditional `cp`, the site is reported `nao-aplicavel` and bypasses the baseline. This contradicts the comment that hitting the cap is reported and violates [`AGENTS.md:23`](AGENTS.md#L23).

- [P1] Evaluate every same-line write — /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/scripts/check-installer-write-safety.py:608-611
  For a valid chain such as `[[ -e "$d" ]] && cp "$a" "$d" || cp "$b" "$d"`, `same_line_reach()` stops at the first destination. It classifies that first write as unreachable on a dangling link and never examines the second, dangerous write, producing `nao-aplicavel`. Either every write must be evaluated or the mixed connector form must block under [`AGENTS.md:23`](AGENTS.md#L23).

- [P1] Recognize shell command prefixes before writers — /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/scripts/check-installer-write-safety.py:785-789
  A write expressed as `command cp "$src" "$dst"` is valid shell, but this parser treats `command` as the command name and never recognizes the following `cp`. An existence predicate controlling that write is therefore emitted as `nao-aplicavel` rather than blocking. Prefixes such as `command` and `env` must be handled or treated as indeterminate per [`AGENTS.md:23`](AGENTS.md#L23).

- [P1] Recognize negation in the test command form — /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/scripts/check-installer-write-safety.py:570-570
  For `if ! test -e "$dst"; then cp ...; fi`, the text before `-e` ends in `! test`, so the immediate-`!` regex reports the condition as non-negated. The dangerous then branch is consequently classified `nao-aplicavel`, allowing a syntactically valid unsafe form through contrary to [`AGENTS.md:23`](AGENTS.md#L23).

- [P1] Do not treat nested jumps as unconditional — /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/scripts/check-installer-write-safety.py:522-524
  Any nested `return` sets `then_jumps=True`, even when guarded by another condition. In `if [[ ! -e "$d" ]]; then if foo; then return; fi; fi; cp ...`, a dangling link reaches the copy whenever `foo` is false, but the matcher treats the nested return as unconditional and reports `nao-aplicavel`. Unsupported control flow must block under [`AGENTS.md:23`](AGENTS.md#L23).

- [P1] Require symlink guards to dominate the write — /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/scripts/check-installer-write-safety.py:1080-1085
  The guard search scans the entire enclosing function and credits the first syntactically aborting guard without proving its enclosing branches execute. Thus a `[ -L "$dst" ] && return` inside `if optional_mode; then ...; fi` marks a later unconditional write as `guardado`, although the guard is skipped when the mode is false. This must be indeterminate unless dominance is proven, as required by [`AGENTS.md:23`](AGENTS.md#L23).

- [P1] Validate helper behavior before granting guard status — /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/scripts/check-installer-write-safety.py:827-830
  Any command whose name contains `symlink`, `nofollow`, `lstat`, or `deref` is assumed to be a real guard. A helper such as `_symlink_notice "$dst" || return` that only warns and returns success is therefore credited even though the write proceeds through the link. Naming alone cannot prove safety; unresolved helper behavior must block per [`AGENTS.md:23`](AGENTS.md#L23).

- [P1] Verify the replacement side of escape expressions — /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/scripts/check-installer-write-safety.py:1196-1202
  `_escape_class_covers()` only checks that the sed character class mentions the delimiter, `&`, and backslash; it never verifies that the replacement actually adds a backslash. Consequently `sed 's/[|&\\]/&/g'`, which is a no-op because `&` reinserts the match, is accepted as an escape and later raw interpolation is marked `guardado`. This fail-open classification violates [`AGENTS.md:23`](AGENTS.md#L23).

- [P1] Bind each interpolation to its own substitution — /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/scripts/check-installer-write-safety.py:1371-1371
  The parser uses only the first substitution found in a script to choose one delimiter for every interpolation. In `sed "s|x|ok|g; s/x/$B/g"`, `$B` is checked against `|` instead of `/`; a value escaped only for `|` is marked `guardado` even though it can break the second command. Each interpolation needs the delimiter of its containing substitution, or the script must block under [`AGENTS.md:23`](AGENTS.md#L23).

- [P1] Model control flow for reaching escape assignments — /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/scripts/check-installer-write-safety.py:1435-1441
  The latest assignment is selected lexically without considering branches. If a variable is initialized from raw input and escaped only inside an optional `if`, the escaped assignment is lexically last and the later interpolation is marked `guardado`, although the raw value reaches it whenever the branch is false. This unsupported reaching-definition case must block per [`AGENTS.md:23`](AGENTS.md#L23).

- [P1] Push the commit created by the land script — /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-183/OWNER-S327-LAND.sh:715-715
  When the ceremony is run from a feature branch or detached worktree, `git commit` advances the current HEAD but `git push origin main` pushes the separate local `main` ref. That push can return success while the newly created signed commit remains unpushed, after which the script incorrectly reports it as delivered. Require the current branch to be `main` or push `HEAD:main` explicitly.```

## Resposta do CEO (S327)

- **10 dos 11 achados (todos em `.claude/scripts/check-installer-write-safety.py`) estão FORA deste pacote:** o arquivo é o rascunho UNTRACKED do censo W0 do PLAN-185 (S326), que o rail leu porque estava no disco. Eles são a 4ª leva da MESMA classe já registrada na S326 (fail-open por forma não modelada: continuação de linha do `sed`, cap de 10 escritas, cadeias `&& … ||`, prefixos `command`/`env`, `! test -e`, `return` aninhado, dominância de guard, helpers por nome, lado de substituição do escape, delimitador por substituição, reaching-definition) — confirmam a decisão já tomada: a próxima passada INVERTE a arquitetura do matcher (enumerar formas PROVADAS seguras com controle positivo; resto = `indeterminado`). Registrados aqui como evidência para essa passada; nada a curar neste pacote, e os 4 arquivos do censo NÃO entram no commit dos materiais.
- **F-LAND [P1] `OWNER-S327-LAND.sh:715` — ACEITO e curado:** G0 agora exige `HEAD == $PUSH_BRANCH` (aborta com o comando de correção) e o push passou a ser `git push "$PUSH_REMOTE" "HEAD:$PUSH_BRANCH"` (mais a dica de retry). Controle: `bash -n` + shellcheck limpos; harness `test-ceremony-scripts.sh` reexecutado (resultado no relatório da S327).

