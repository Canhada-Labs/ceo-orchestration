# PLAN-161 W2 pack — codex pair-rail round 7 (2026-07-27)

## Verdict

REJECT

1. [P1] The consumer still accepts non-string review_id values as exact
   pairing keys. `_review_id()` stringifies the raw field before validation,
   so JSON number 1234567890123456 becomes a valid 16-hex token. A completed
   string-ID pair followed by a dead numeric-ID expected row with the same
   value collapses in expected_ids; the older terminal offsets both and can
   produce overall GREEN. Validate isinstance(raw, str) before the regex and
   add a numeric-ID regression. ceo-boot.py:1970

## CEO triage — 1 P1 ACCEPTED (one-line hardening, fixed directly)

- F1: `_review_id()` stringified the raw field before validating, so a JSON
  number 1234567890123456 str()-aliased onto a completed string-id pair's
  exact key -> the old string terminal offset the dead numeric review (false
  green). Fix: `raw = ev.get("review_id"); rid = raw if isinstance(raw, str)
  else ""` (reject non-str BEFORE the regex). Numeric-id regression test
  added; teeth proven (reverting the gate fails it).
