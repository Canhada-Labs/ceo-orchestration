# PLAN-185 W0 (6ª passada, commit f31e1b1) — rail codex rodada 3 (2026-08-27T03:39:55Z)

Rail-Verdict: REJECT — 5 P1 + 2 P2. **A classe «forma não modelada ⇒ fail-open» regenerou pela 7ª leva, na 3ª arquitetura de regra (denylist → allowlist de formas → descoberta fail-closed). Critério de parada registrado no rail-round-2 DISPARA: o W0 PARA aqui nesta noite (PROTOCOL anti-padrão 6 — não existe 4ª arquitetura barata; a modelagem completa de bash é uma wave própria, não uma madrugada).**

## Disposição do CEO (00:55, 27/08)

- Os 2 P2 (digest ausente do `--json`; digest pinado errado no relatório) eram factuais/mecânicos e foram CURADOS no commit seguinte (digest novo re-pinado; `instrument_sha256` no JSON).
- Os 5 P1 (`patch -d`; `patch -r`/`-B` auxiliares; a4 não alcança `write-candidate`; a4 aceita polaridade descartada em corpo de helper; a4 não liga o parâmetro checado ao argumento) ficam DECLARADOS como pontos cegos do ratchet — enumerados abaixo como fixtures da wave futura, NÃO curados nesta noite.
- O que o W0 ENTREGA e continua valendo: ratchet fail-closed na DESCOBERTA com controle positivo provado (sítio novo bloqueante fora do baseline ⇒ rc=1 nomeando o path), 148 testes, baseline de 620 sítios com fingerprint, digest de reprodutibilidade. Pontos cegos = as formas dos 5 P1 e o residual declarado do §12/§13 do relatório.
- **OQ ao Owner (registrada no PLAN-185 §6):** aceitar o W0 como ratchet-com-pontos-cegos-declarados e wiring no CI pela cerimônia C (recomendado), ou financiar a wave de modelagem completa antes do wiring.

Full review comments:

- [P1] Treat patch -d as a write-affecting path — .claude/scripts/check-installer-write-safety.py:854-854
  With a relative target, `patch -d "$dir" fixed/target "$diff"` writes under `$dir`, but this entry consumes `$dir` only as a read. A check on `$dir` therefore receives `a3-no-write-to-operand`, and no write-candidate is emitted when the positional target is literal. Model the effective destination or keep this option unknown; the current behavior violates the fail-closed matcher rule ([AGENTS.md:23](AGENTS.md#L23)).

- [P1] Preserve patch's target with auxiliary outputs — .claude/scripts/check-installer-write-safety.py:1573-1577
  For `patch -r /tmp/reject "$dst" "$diff"` (similarly `-B`), the earlier `if dests:` return records only the reject/prefix operand and classifies the positional target as a read, so this new target branch is never reached. The command still modifies `$dst`, but its test now becomes non-blocking `a3-no-write-to-operand`; retain the positional target as a destination for auxiliary-output options ([AGENTS.md:23](AGENTS.md#L23)).

- [P1] Apply a4 to the write-candidate verdict — .claude/scripts/check-installer-write-safety.py:2971-2975
  When a write is protected only by the new direct shared predicate, this loop marks the `symlink-follow` site guarded, but the same `cp` also emits a `write-candidate`; `verdict_class_c()` uses `_guard_is_live()`, which still considers only a1/a2 guards, so that site remains `desguardado`. Consequently a4 cannot make a modeled write non-blocking or shrink the baseline as intended ([PLAN-185:559-561](.claude/plans/PLAN-185/w0-censo-S329.md#L559-L561)); thread a4 evidence through class C and assert that positive fixtures have no blocking sites.

- [P1] Tie a4 refusal status to the path check — .claude/scripts/check-installer-write-safety.py:2873-2875
  For `guard() { [ -L "$1" ]; return 0; }` called as `guard "$dst" || return`, these two independent predicates both pass even though the `-L` result is discarded and the helper always allows the following write. Class A is therefore labeled `guardado` for a symlink path; require control-flow evidence that the non-following check selects the caller's modeled refusal polarity ([AGENTS.md:23](AGENTS.md#L23)).

- [P1] Bind a4 checks to the destination argument — .claude/scripts/check-installer-write-safety.py:2813-2815
  For a helper that checks only `$1`, a call such as `guard /known/safe "$dst" || return` passes this any-argument intersection because `$dst` appears as `$2`, even though the checked path is unrelated. This incorrectly credits the destination as guarded; map the checked positional parameter(s) to the corresponding call arguments before accepting coverage ([AGENTS.md:23](AGENTS.md#L23)).

- [P2] Include the instrument digest in JSON — .claude/scripts/check-installer-write-safety.py:4201-4201
  The digest is appended only by `render_table()`, while `--json` bypasses that function and its payload contains no `instrument_sha256` field. This leaves the primary machine-readable output without the reproducibility identifier promised by the documented contract ([PLAN-185:499-502](.claude/plans/PLAN-185/w0-censo-S329.md#L499-L502)).

- [P2] Pin the census to the committed digest — .claude/plans/PLAN-185/w0-censo-S329.md:504-505
  The script committed in `f31e1b1` hashes to `484e65766afc5cb0da00aef30dbd88b936e9349c184c330a68c80e115fc769c4`, not the recorded `a8703ede...` value. The published counts are therefore attributed to a different instrument version, defeating the reproducibility section; regenerate this value after the final script edits.
The patch introduces fail-open classifications for valid `patch` invocations and an a4 proof that is both ineffective for write-candidate sites and unsound in its body/argument checks. Its new reproducibility metadata is also absent from JSON and pinned to the wrong digest.

