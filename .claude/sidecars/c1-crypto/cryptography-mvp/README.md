# c1-crypto / cryptography-mvp sidecar

**Capability class**: C1 (per ADR-126 §Part 1)
**Authorizing ADR**: ADR-129-AMEND-1 (lifts §Key-floor-waiver)
**Risk tier**: C (per ADR-125 §C — explicit opt-in required)
**Default state**: OFF

This sidecar is the **sole legitimate importer** of the `cryptography`
Python package in the framework, fenced under
`.claude/sidecars/c1-crypto/cryptography-mvp/sidecar_code/` per
ADR-126 §Part 2 sidecar-tree isolation.

## Purpose

PLAN-099 v1.32.0 MVP shipped read-only federation with a programmatic
`§Key-floor-waiver` (stdlib `ssl.SSLContext` does not expose primitives
for cert public-key parameter inspection). This sidecar lifts that
waiver by introducing real PEM x509 parsing:

  - Per-cert RSA bit-count / EC curve / DSA-reject inspection at peer-add
  - SPKI fingerprint extraction (rotation-survives invariant)
  - DER fingerprint extraction (legacy v1.x compat)
  - Weak-signature-algorithm rejection (MD5/SHA1)

## Install

```
export CEO_SIDECAR_C1_CRYPTO_CRYPTOGRAPHY_MVP_ENABLED=1
bash .claude/sidecars/c1-crypto/cryptography-mvp/install.sh
```

The kill-switch is **off by default**. Adopters running federation
read-only with the existing stdlib-ssl-mvp sidecar (PLAN-099 baseline)
do not need to install this one. Adopters opening write-mode (per
PLAN-099-FOLLOWUP v1.39.1) MUST install this sidecar — `cert_inspector`
bridge falls back to openssl-subprocess parse when the sidecar is
disabled or absent, but the bridge cannot reliably extract SPKI on
LibreSSL <3.5, and write-mode AC1 + AC14 invariants require SPKI.

## Boundary verification

```
python3 .claude/sidecars/c1-crypto/cryptography-mvp/boundary_test.py
```

Asserts:

  - `cryptography` is imported ONLY from
    `.claude/sidecars/c1-crypto/cryptography-mvp/sidecar_code/`
  - Core paths (.claude/hooks/, .claude/scripts/, .claude/policies/,
    SPEC/, .github/workflows/) contain ZERO `cryptography` imports
  - The bridge at `.claude/hooks/_lib/federation/cert_inspector.py`
    is stdlib-only (subprocess-invokes this sidecar)

## Co-existence with stdlib-ssl-mvp sidecar

The two C1 sidecars co-exist:

| Sidecar             | Capability                          | Required by               |
|---------------------|-------------------------------------|---------------------------|
| stdlib-ssl-mvp      | Loopback mTLS handshake (read-only) | PLAN-099 v1.32.0 baseline |
| cryptography-mvp    | PEM x509 cert inspection + SPKI     | PLAN-099-FOLLOWUP write   |

An adopter operating in read-only mode with the MVP loopback-only
federation install only stdlib-ssl-mvp. An adopter opening write-mode
installs both.

## Supply chain

`cryptography` is widely attacked (CVE-2023-49083 / CVE-2024-26130).
Mitigations per ADR-129-AMEND-1 §4:

  - Pin floor 42.0 (stable `_utc` accessors; RFC 7958 PEM bundle support)
  - Pin ceiling <44.0 (next major bump via ADR-129-AMEND-2 post-soak)
  - 30-day release-window soak before adopting new major versions
  - SHA-256 model pin tracked in `installed-version.txt` post-install

## Kill switch

```
unset CEO_SIDECAR_C1_CRYPTO_CRYPTOGRAPHY_MVP_ENABLED
# or
export CEO_SIDECAR_C1_CRYPTO_CRYPTOGRAPHY_MVP_ENABLED=0
```

When disabled, the bridge at `_lib/federation/cert_inspector.py` falls
back to openssl-subprocess parse — feature-degraded but functional for
read-mode peers. Write-mode peer-add rejects with
`federation_key_floor_stale` when sidecar disabled (AC14 / Wave B.5).
