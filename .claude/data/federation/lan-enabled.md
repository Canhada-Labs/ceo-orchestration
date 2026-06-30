# Federation LAN-bind sentinel — Owner-signed cleartext

I, the Owner of this ceo-orchestration deployment, authorize the
federation server to bind to a NON-LOOPBACK interface, accepting that
this expands the trust boundary from this host to any reachable
network neighbour presenting a pinned client cert from
`peers.yaml`.

This sentinel pair (this `.md` + co-located `.asc`) is REQUIRED in
addition to the master `enabled.md{,.asc}` pair WHENEVER the bind is
not a loopback address.

The `ipaddress.ip_address(bind).is_loopback` test (per ADR-135 §Part 5)
covers ALL non-loopback shapes:

- `0.0.0.0` / `::` / `::0` (unspecified / bind-all)
- LAN literals (`192.168.x.y`, `10.x.x.x`, `172.16.x.y`)
- Hostnames resolving to non-loopback addresses

## Owner fingerprint

`0000000000000000000000000000000000000000`

## Date

2026-05-17

## Notes

- This file is kernel-guarded (ADR-129 §Part 4 + ADR-135 §Part 5 +
  PLAN-089 W-A.4 pattern). Edits require an Owner-signed canonical
  sentinel with this path in Scope.
- When the file is missing, non-loopback bind is rejected with
  `federation_lan_bind_denied:signed_file_missing`.
- Sign with:

      gpg --detach-sign --armor -u 0000000000000000000000000000000000000000 \
          -o lan-enabled.md.asc lan-enabled.md
