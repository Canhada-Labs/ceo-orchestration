# PLAN-185 W0 (4ª passada, commit 843eb57) — rail codex rodada 1 (2026-08-26T21:00:29Z)

Rail-Verdict: REJECT — 15 P1 + 1 P2, TODOS da classe «forma não modelada ⇒ fail-open» (5ª leva da mesma classe). Decisão do CEO: última passada da noite com ARQUITETURA de descoberta fail-closed (ver §12 do w0-censo-S329.md); se a classe persistir, W0 vira advisory com limites declarados + OQ ao Owner.

Full review comments:

- [P1] Block unsupported file-test forms — .claude/scripts/check-installer-write-safety.py:1202-1206
  When a script uses a valid dereferencing form such as `test -a "$dst"` or a path-qualified `test`, `_scan_tests` records no site at all. In the real multi-file corpus the global zero-site check still passes, so a subsequent write through `$dst` is invisible rather than indeterminate; unsupported test syntax must emit a blocking site per the fail-closed matcher rule ([AGENTS.md:23](AGENTS.md#L23)).

- [P1] Detect path-qualified stream editors — .claude/scripts/check-installer-write-safety.py:2416-2418
  A command such as `/usr/bin/sed "s|x|$value|g"` is skipped because only the exact bare command name is accepted. Since other files already produce sites, this unsafe interpolation does not trigger the zero-site failure and the baseline remains green; normalize supported editor paths or emit an indeterminate site instead of continuing ([AGENTS.md:23](AGENTS.md#L23)).

- [P1] Recognize positional and special shell expansions — .claude/scripts/check-installer-write-safety.py:1948-1950
  The expansion parser only accepts identifier-style names, so scripts containing `$1`, `${1}`, `$@`, or `$*` are reported as `n0-no-interpolation`. For example, `sed "s|x|$1|g"` receives a non-blocking verdict even though an operator-controlled positional argument can inject the delimiter; these forms must be tracked or conservatively marked indeterminate ([AGENTS.md:23](AGENTS.md#L23)).

- [P1] Reject bracket-internal negation as a nofollow guard — .claude/scripts/check-installer-write-safety.py:1525-1525
  With `[ ! -L "$dst" ] && return 1` before a tested write, `cmd.negated` remains false and this predicate is accepted because the `!` is a word rather than the tokenized `&&` checked here. The symlink case is precisely the path that continues, yet the write is reported `guardado`; test polarity and legacy conjunctions such as `-a` must be modeled or blocked ([AGENTS.md:23](AGENTS.md#L23)).

- [P1] Bind nofollow evidence to its actual command — .claude/scripts/check-installer-write-safety.py:1543-1544
  `split_commands` creates new `Command` objects, so `c is t.cmd` cannot succeed and the operand-text fallback may select an earlier command on the same line. For `[ -e "$dst" ] && return 1; [ -L "$dst" ]` followed by `cp ... "$dst"`, the abort attached to `-e` is incorrectly credited to the standalone `-L`, producing `guardado` while a dangling symlink reaches the copy ([AGENTS.md:23](AGENTS.md#L23)).

- [P1] Invalidate nofollow guards after path reassignment — .claude/scripts/check-installer-write-safety.py:1711-1712
  Control-flow dominance does not prove that the guarded value is still current. For `dst=/safe; [ -L "$dst" ] && return; dst="$1"; [ -e "$dst" ]; cp src "$dst"`, this check reports `guardado` even though the operator-controlled value was assigned after the guard; intervening reaching definitions must invalidate the proof ([AGENTS.md:23](AGENTS.md#L23)).

- [P1] Treat redirect-to-file >& as a write — .claude/scripts/check-installer-write-safety.py:865-866
  Bash's `command >& "$dst"` opens `$dst` for output, but this branch always treats `>&` as descriptor duplication and discards its operand. A preceding `[ -e "$dst" ]` is consequently classified `a3-no-write-to-operand`; distinguish numeric descriptor operands from filename operands so this write blocks ([AGENTS.md:23](AGENTS.md#L23)).

- [P1] Remove write-capable commands from the readonly set — .claude/scripts/check-installer-write-safety.py:705-709
  Several commands listed as unconditionally readonly have output modes: `sort -o "$dst"`, `uniq input "$dst"`, and `yq -i "$dst"` all write their operand. A tested `$dst` is therefore recorded only as a read and incorrectly receives `a3-no-write-to-operand`; these commands need option-aware classification or must default to unknown ([AGENTS.md:23](AGENTS.md#L23)).

- [P1] Associate attached destination options with their value — .claude/scripts/check-installer-write-safety.py:1008-1008
  For `cp --target-directory="$dst" src`, quoting the option value marks the whole token quoted, so it bypasses option parsing and `src` is treated as the destination. The occurrence key is `--target-directory=$dst`, not `$dst`, causing a preceding `-d "$dst"` site to be declared `a3-no-write-to-operand`; extract attached option values or conservatively link embedded variable references ([AGENTS.md:23](AGENTS.md#L23)).

- [P1] Require a reaching literal assignment for b3 — .claude/scripts/check-installer-write-safety.py:2317-2319
  `all_literal_safe` does not require any safe assignment to dominate the editor use. Thus `sed "s|x|$v|g" ...` followed later by `v=safe`, or a safe assignment in a branch that may not run, is classified `b3-literal-only` even when `$v` came from the environment or caller; require a reaching assignment on every path ([AGENTS.md:23](AGENTS.md#L23)).

- [P1] Require a real sed escaping replacement — .claude/scripts/check-installer-write-safety.py:2160-2160
  Accepting any replacement beginning with one backslash treats `sed 's/[|&\\]/\&/g'` as an escape. In sed, `\&` produces a literal ampersand rather than a backslash plus the matched character, leaving an unsafe `&` for an outer replacement; the proof must require syntax that actually emits the escaping backslash ([AGENTS.md:23](AGENTS.md#L23)).

- [P1] Reject extra output around inline escape pipelines — .claude/scripts/check-installer-write-safety.py:2171-2174
  The outer `$(...)` check does not ensure that the escaping sed pipeline is the substitution's only producer. A substitution such as `$(printf ... | sed 'safe-escape'; printf %s "$raw")` is accepted as b4 even though the final command appends the raw value; parse the complete substitution or mark any additional shell structure indeterminate ([AGENTS.md:23](AGENTS.md#L23)).

- [P1] Match charset validation to the exact variable — .claude/scripts/check-installer-write-safety.py:2217-2218
  The substring test makes `$v` match a validation of `$value`. Consequently `[[ "$value" =~ ^[A-Za-z]+$ ]] || die` causes a later raw interpolation of `$v` to be reported `b2-closed-charset-validated`; inspect the validation command's exact operand token rather than searching the logical-line text ([AGENTS.md:23](AGENTS.md#L23)).

- [P1] Require the charset validation to be start-anchored — .claude/scripts/check-installer-write-safety.py:2219-2219
  The optional `^` permits suffix-only validation such as `[[ "$v" =~ [A-Za-z]+$ ]] || die`. A value like `|safe` passes that test while retaining the sed delimiter, yet the interpolation receives a guarded b2 verdict; require the full anchored shape promised by the allowlist ([AGENTS.md:23](AGENTS.md#L23)).

- [P1] Bind the abort directly to the validation command — .claude/scripts/check-installer-write-safety.py:2222-2227
  This loop accepts any later `|| abort` pair on the same logical line, not necessarily one connected to the regex test. For `[[ "$v" =~ ^[A-Za-z]+$ ]]; true || die`, the unsafe value reaches the editor because `die` is skipped, but the matcher still returns b2; verify that the validation command itself is immediately guarded by the abort ([AGENTS.md:23](AGENTS.md#L23)).

- [P2] List every scanned shell file in the output — .claude/scripts/check-installer-write-safety.py:2704-2704
  The output only lists files that produced sites, so a discovered file with zero sites remains indistinguishable from a file omitted by discovery. This leaves the explicit PLAN-185 acceptance condition for `doctor.sh` unsatisfied; include the complete discovered-file list, including zero-site files, in both human and JSON output ([PLAN-185:167-173](.claude/plans/PLAN-185-installer-write-safety.md#L167-L173)).
The new security census emits non-blocking verdicts for numerous unsafe but valid shell forms, contradicting its fail-closed contract. It also does not report the complete scanned-file scope required by PLAN-185.

