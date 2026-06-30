# OIDC → key-broker recipe (template)

> **PLAN-133 item E7 (Wave E).** This directory is an **editable template**
> shipped for adopters — **not** a wired framework hook. Copy it into your
> own broker service and adapt. The framework itself stays stdlib-only and
> does not run this code.
>
> **Provenance / safety (PLAN-133 rite §2):** every line here is a
> from-scratch stdlib re-implementation. Nothing was fetched or executed
> from the `aaif-goose/goose` fork.

## What problem this solves

A workload (a CI job, a spawned agent, a sidecar) needs to call a model
provider, but you do **not** want it to carry your long-lived provider API
key. Instead:

1. The workload obtains a **short-lived OIDC identity token** from a trusted
   issuer it already has (GitHub Actions OIDC, Kubernetes projected
   ServiceAccount token, a cloud workload-identity token, …).
2. It presents that token to a **key broker** you run.
3. The broker **verifies** the token (this recipe), and only then **mints**
   a short-lived, narrowly-scoped provider credential and returns it.

The standing provider key lives **only inside the broker**. A leaked OIDC
token is short-lived, audience-bound, and single-use (replay-protected), so
the blast radius is small.

```
 ┌──────────┐  OIDC id-token   ┌────────────┐  verify (this recipe)  mint
 │ workload │ ───────────────▶ │ key broker │ ─────────────────────▶ short-lived
 │ (CI job) │                  │ (you run)  │      scoped provider creds
 └──────────┘ ◀─────────────── └────────────┘
              scoped creds          │ holds the standing provider key
                                    ▼ (never leaves the broker)
```

## Files

| File | Role |
|---|---|
| `oidc_key_broker.py` | The **verify** step — the trust gate. Pure, stdlib, no network I/O, no provider client constructed. |
| `broker.config.example.json` | Editable config (issuer/audience/subject-allowlist/nonce-TTL). |
| `tests/test_oidc_key_broker.py` | Unit tests (30). Run on demand (see below). |

## The two hardening guarantees (both from ADR-122)

This recipe re-uses the exact bearer/DPoP hardening the framework already
ratified for MCP in **ADR-122**:

- **alg allowlist (ADR-122 §A.1 / §A.3, clause 2).**
  `enforce_alg_allowlist()` accepts **asymmetric algorithms only** and
  rejects `alg=none` and every `alg=HS*` **at parser precedence — BEFORE
  any signature verification**. This closes the classic JWT
  alg-confusion / key-confusion downgrade. The check is case-sensitive
  membership, so `none`, `None`, `hs256`, a missing alg, or a non-string
  alg all DENY.

- **per-jti nonce cache (ADR-122 §A.4 / RFC 9449 §11.1).**
  `NonceCache` makes each `jti` **single-use within its TTL** (TTL ≤ 5 min,
  enforced as a hard ceiling). The cache key is the `(jti, iat)` tuple.
  Eviction is **LRU + TTL only** — never a count-based eviction that could
  drop a still-live nonce to admit a replay (the cache-flush DoS ADR-122
  §A.4 calls out). A replayed proof is **denied**.

## Fail-closed posture

`verify_oidc_token()` has **no fail-open path** — every malformed token,
disallowed alg, replayed jti, missing/expired claim, or issuer/audience
mismatch **raises `VerificationError` and denies**. Fail-open in a broker
would mint a credential for an attacker. (Contrast the framework's *hooks*,
which fail-OPEN on infra so they never block your session — a broker is a
trust gate, not a session hook, so it fails CLOSED.)

`VerificationError.reason` is a **closed enum** (`disallowed_alg`,
`replayed_jti`, `signature_invalid`, `issuer_mismatch`, …) and **never echoes
the token, a claim value, or any secret** — the no-value-echo property is
tested.

## The one thing you MUST wire: the signature verifier

The Python **standard library ships no asymmetric public-key crypto**, and
this framework is stdlib-only, so the recipe **cannot** verify an RS/ES/EdDSA
signature for you. It exposes a `verify_signature` **seam** and ships a
`RejectAllVerifier` default that **denies every token** — an unconfigured
broker mints nothing.

Wire a real verifier backed by your crypto library of choice
(`cryptography`, `PyJWT`, `joserfc`, …) that:

1. fetches + caches the issuer JWKS (`jwks_uri` in the config),
2. selects the key by the token's `kid`,
3. returns `True` iff the signature over `signing_input` validates for the
   given `alg`.

```python
from oidc_key_broker import NonceCache, verify_oidc_token, VerificationError

nonce_cache = NonceCache()  # process-wide; one per broker instance

def verify_signature(alg, signing_input, signature, header):
    pub = jwks.key_for(header.get("kid"))     # your JWKS cache
    return pub.verify(alg, signing_input, signature)  # your crypto lib

try:
    claims = verify_oidc_token(
        token,
        expected_issuer="https://token.actions.githubusercontent.com",
        expected_audience="ceo-key-broker",
        nonce_cache=nonce_cache,
        verify_signature=verify_signature,
        allowed_subjects=frozenset({"repo:OWNER/REPO:ref:refs/heads/main"}),
    )
except VerificationError as exc:
    deny(exc.reason)          # closed enum, safe to log
else:
    creds = mint_scoped_credential(claims["sub"])  # YOUR mint step
    return creds
```

`verify_oidc_token` **never mints** — verify and mint are separated on
purpose. Minting (TTL, scope, provider) is your broker's job; see
`minted_credential` in the config.

## Running the tests

These tests live under `templates/`, which is intentionally **not** in the
framework's pinned `pytest.ini :: testpaths` (templates are adopter
artifacts, not part of the framework's CI collection). Run them on demand:

```bash
python -m pytest templates/oidc-proxy/tests/ -q
# 30 passed
```

## Operational guidance

See [`docs/BRANCH-PROTECTION.md` → "OIDC → key-broker for CI credentials"](../../docs/BRANCH-PROTECTION.md)
for how this fits the repo's CI / secret-hygiene posture (it replaces a
standing `ANTHROPIC_API_KEY` repo secret with broker-minted short-lived
credentials).
