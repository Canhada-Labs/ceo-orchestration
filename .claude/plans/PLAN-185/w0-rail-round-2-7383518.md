# PLAN-185 W0 (5ª passada, commit 7383518) — rail codex rodada 2 (2026-08-26T22:17:10Z)

Rail-Verdict: REJECT — 6 P1 + 1 P2. A ARQUITETURA de descoberta fail-closed está no lugar; os achados são caminhos ESPECÍFICOS que a contornam (basename de executável não confiável; comandos com destino POSICIONAL; expansões aninhadas `${a:-$b}`; comandos opacos filtrados antes de emitir; RHS de `=~` entre aspas aceito como regex; chave `{`/`}` tratada como sintaxe fora da posição de comando; `patch -i` como escrita). Disposição do CEO (19:20): UMA passada final (6ª) com os 7 como fixtures R6-01..07; independentemente do resultado, o W0 entra no CI como RATCHET com pontos cegos DECLARADOS (OQ-1/OQ-2 do relatório) — `--strict` e a modelagem completa ficam para wave própria. W1/W2 (pacote C) não dependem disto.

Full review comments:

- [P1] Do not trust arbitrary executables by basename — .claude/scripts/check-installer-write-safety.py:992-994
  For path-qualified commands such as `./grep` or `/tmp/printf`, the shell executes that specific file, whose behavior is not proven by the basename allowlist. A custom `./grep --output "$dst"` now changes from indeterminate in the parent to `a3-no-write-to-operand`, with no write candidate. Only normalize explicitly trusted paths; otherwise keep path-qualified commands unknown. This violates the fail-closed matcher rule in `AGENTS.md:23`.

- [P1] Preserve positional-output commands as writers — .claude/scripts/check-installer-write-safety.py:1387-1388
  When no modeled output option is present, this fallback marks every remaining output-mode command read-only, but valid forms such as `zip "$dst" "$src"`, `split "$src" "$prefix"`, `patch "$dst" "$diff"`, and traditional `tar cf "$dst" ...` write positional destinations. These regress from indeterminate in the parent to no candidate or `a3-no-write-to-operand`; model each command's positional semantics or leave it unknown. This violates `AGENTS.md:23`.

- [P1] Recurse into nested parameter expansions — .claude/scripts/check-installer-write-safety.py:894-896
  The braced alternative consumes `${...}` as one token and advances past nested expansions. With `safe=` and `sed "s|x|${safe:-$RAW}|g"`, only `safe` is analyzed and b3 proves the interpolation guarded, although the shell substitutes attacker-controlled `RAW` because `safe` is null; the parent correctly blocked this case. Nested parameters and command substitutions must also be collected, per `AGENTS.md:23`.

- [P1] Emit opaque-command sites before expansion filtering — .claude/scripts/check-installer-write-safety.py:1986-1988
  Opaque commands are documented as candidates with or without an expansion, but their operands are still filtered through `_token_is_expanded` and the command is dropped when that list is empty. For example, `eval 'cp "$SRC" "$DST"'` has no outer-shell expansion, yet `eval` subsequently expands both variables and the census emits no opaque site; literal `source` operands have the same omission. Handle opaque commands before this filter to satisfy `AGENTS.md:23`.

- [P1] Reject quoted regex operands as validation evidence — .claude/scripts/check-installer-write-safety.py:3095-3098
  `canon_operand` removes quotes from the right side of `=~`, but Bash treats a quoted RHS as a literal string rather than a regex. Thus `[[ "$V" =~ "^[A-Za-z]+$" ]] || exit` is credited as a closed-class validation even though it accepts only the literal regex text; that text can contain the selected sed delimiter, such as `[` in `sed "s[x[$V[g"`. Require an unquoted RHS or block it under `AGENTS.md:23`.

- [P1] Split braces only when they are shell syntax — .claude/scripts/check-installer-write-safety.py:738-744
  An unquoted `{` or `}` is a reserved word only in command position; it can otherwise be an ordinary argument. The valid command `printf data | tee { "$dst"` writes both files, but this split turns `tee` and `"$dst"` into separate commands, so the destination disappears and a preceding existence test is reported `a3-no-write-to-operand`. Track command position before treating braces as separators, as required by `AGENTS.md:23`.

- [P2] Treat patch input options as reads — .claude/scripts/check-installer-write-safety.py:798-798
  `patch -i FILE` and `patch --input FILE` read the patch document; they do not write that operand. Listing them as destination options causes commands such as `patch -i "$patchfile" /fixed/target` to report `$patchfile` as an unguarded write and creates a blocking false positive. These options should be modeled as input-bearing options instead.
Several newly introduced parsing and classification paths turn real writes or unsafe interpolations into guarded or absent sites, violating the matcher's fail-closed contract. The output-mode table also contains a concrete destination-role error.

