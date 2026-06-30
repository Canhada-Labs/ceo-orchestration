# Federation enable sentinel — Owner-signed cleartext

I, the Owner of this ceo-orchestration deployment, authorize the
federation server to start.

This sentinel MUST be co-located with its detached `.asc` signature.
The `verify_detached` + `is_valid_signer` 2-stage protocol at server
startup checks both files; either stage failing → fail-CLOSED with a
`federation_enable_sentinel_invalid` audit emit.

This pair gates ANY federation server start, REGARDLESS of bind
interface. A NON-loopback bind requires the ADDITIONAL sentinel pair
at `.claude/data/federation/lan-enabled.md{,.asc}`.

## Owner fingerprint

`0000000000000000000000000000000000000000`

## Date

2026-05-17

## Notes

- This file is kernel-guarded (ADR-129 §Part 4 + ADR-135 §Part 4 +
  PLAN-089 W-A.4 pattern). Edits require an Owner-signed canonical
  sentinel with this path in Scope.
- The actual GPG signature is at `enabled.md.asc` (alongside this
  file). When the file is missing, the server refuses to start with
  `federation_enable_sentinel_invalid:signature_file_missing`.
- Sign with:

      gpg --detach-sign --armor -u 0000000000000000000000000000000000000000 \
          -o enabled.md.asc enabled.md
