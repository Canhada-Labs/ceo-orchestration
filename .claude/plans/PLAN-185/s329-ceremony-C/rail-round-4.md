# Pacote C — rail codex rodada 4 (shadow-185 avançada p/ 8dde6f7 + baseline regenerado, 2026-08-27T03:35:37Z)

Rail-Verdict: REJECT
Comando: `codex exec review --uncommitted --skip-git-repo-check`. NOTA de leitura: o output cita verbatim os registros rail-round-1/2.md que o `pull --ff-only` trouxe para a sombra — os 4 primeiros achados do arquivo são CITAÇÕES (curas r2 aceitas); o bloco REAL é o último (2 P1 + 1 P2 novos, abaixo). Curas despachadas ao u1-3-w1w2-cure-writer-r2 (00:40).

Full review comments:

- [P1] Reset the inherited atomic-temp cleanup path — scripts/install.sh:780-780
  When `_ATOMIC_TMP_PENDING` is exported by the caller, this trap is registered before the script assigns or clears it, so an early exit—or any `--dry-run`, which never invokes the atomic writers—executes `rm -f` on the inherited path. Thus `env _ATOMIC_TMP_PENDING=/path/to/file ... --dry-run` can delete any file writable by the installer user despite the no-write promise; initialize this variable before installing the trap.

- [P1] Update the live-corpus test after removing sed — scripts/install.sh:2082-2082
  Every validate job runs `.claude/scripts/tests/`, but `TestLiveCorpus::test_f2_the_reported_sed_site_is_unguarded` at `.claude/scripts/tests/test_check_installer_write_safety.py:1748-1753` still requires an unguarded `sed-interp` hit inside `install_github_templates`. These changes remove that sed site entirely, so the census returns no matching hit and the test now fails on every CI run; update the assertion to the new guarded/rendered form in this patch.

- [P2] Validate the raw owner before command substitution — scripts/upgrade.sh:3696-3696
  When the target-side install state contains an owner such as `"ali\u0000ce"` or one ending in multiple newlines, Python emits those raw characters into `$(...)`, but Bash removes NUL bytes and strips trailing newlines before `_wbm_github_handle_ok` sees the value. The malformed input is therefore normalized to `alice` and accepted, potentially selecting and rendering the CODEOWNERS route instead of failing closed; validate before this lossy shell transport, as required by [AGENTS.md:23](AGENTS.md#L23).
The patch leaves a live-corpus test universally failing in CI. It also introduces an inherited-path arbitrary deletion risk and validates untrusted owner data only after lossy command substitution.
