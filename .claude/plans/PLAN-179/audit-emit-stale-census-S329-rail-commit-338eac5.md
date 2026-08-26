# U2 fase 1 — rail codex sobre o commit 338eac5 (2026-08-26T20:16:12Z)

Rail-Verdict: REJECT (1 P1 + 3 P2 no instrumento; curas despachadas ao agente u2-stale-patch-census-writer)

Full review comments:

- [P1] Scope setup rebinds to the owning test class — .claude/scripts/check-stale-module-patch.py:495-498
  When a file has multiple test classes, this applies the first method named `setUp` to every site in the file because `live_rebinds` records no class ownership. In `test_spool_drain_rotation_race.py`, the live rebind at L68 belongs to the first class, while the second class's reload at L259 can run alone or on another xdist worker; it can therefore receive a stale alias and raise even though the census reports `LOOKUP-VIVO` and omits it from the cure list. Associate rebinds with their class and alias before downgrading a site.

- [P2] Verify consumer ownership before returning SEGURO — .claude/scripts/check-stale-module-patch.py:409-413
  Any attribute expression ending in `audit_emit` is classified as a consumer alias without checking that its base is the module under test. For example, if `holder._audit_emit` captured the module-level emitter and the real consumer re-resolves it at call time, patching `holder._audit_emit` still lands on the stale object, but this branch returns `SEGURO`. Require evidence that the base is the inferred consumer holding an import-time alias; otherwise classify the form as indeterminate.

- [P2] Execute the runtime hazard in the positive control — .claude/scripts/tests/test_check_stale_module_patch.py:282-290
  The purported incident control only writes source strings and asks the classifier for its own verdict; it never imports the shadow modules, executes the consumer, or performs the motivating `sys.modules.pop` + package-attribute deletion + re-import. Consequently, both legs can remain green when the classifier's runtime model is wrong, as with the cross-class setup case. Add a same-process runtime red/green control instead of relying solely on expected AST labels.

- [P2] Reject census roots with no test directories — .claude/scripts/check-stale-module-patch.py:640-642
  If `.claude/hooks` exists but neither expected test directory exists, both iterations silently continue, producing a zero-file census that `main()` returns as success. This contradicts the documented exit code 2 for “no test root found” and makes an incomplete checkout appear clean. Validate that at least one census root exists before scanning.
The census can issue false-safe `LOOKUP-VIVO` and `SEGURO` verdicts, including for a site in the current tree under xdist or isolated execution. Its automated controls do not execute the claimed hazard, and incomplete inputs can still return a successful empty census.

