"""PLAN-099 Federation cross-machine MVP — stdlib ssl mTLS, loopback-default,
read-only allowlist FIRST; write-mode WIRE (default-OFF) per
PLAN-112-FOLLOWUP-federation-wire-or-delete.

This package implements the federation surface under ADR-129 (C1 crypto
capability class) + ADR-135 (federation contract MVP) + ADR-135-AMEND-1
(write-mode trust boundary, activated default-OFF).
Stdlib-only per ADR-126 §Part 6.

Tier-C per ADR-125: default-OFF, Owner-GPG sentinel pair required to
enable, additional pair required for non-loopback bind. Write endpoints
are present and functional but reachable ONLY when BOTH Layer 0a
(``CEO_FEDERATION_WRITE_ENABLED=1``) AND Layer 0b (the write-enable GPG
sentinel pair) pass. ``ALLOWED_HTTP_METHODS`` stays GET-only as the
module constant — POST is admitted per-request by the dispatcher's
write-mode gate, NOT by a static constant flip (default-OFF invariant).
"""

from __future__ import annotations

__all__ = [
    "FEDERATION_KILL_SWITCH_ENV",
    "FEDERATION_WRITE_KILL_SWITCH_ENV",
    "DEFAULT_BIND",
    "DEFAULT_PORT",
    "MAX_CLOCK_SKEW_SECONDS",
    "MIN_TLS_VERSION_NAME",
    "OWNER_GPG_FPR",
    "ENABLED_SENTINEL_REL",
    "ENABLED_SENTINEL_ASC_REL",
    "LAN_ENABLED_SENTINEL_REL",
    "LAN_ENABLED_SENTINEL_ASC_REL",
    "WRITE_ENABLED_SENTINEL_REL",
    "WRITE_ENABLED_SENTINEL_ASC_REL",
    "PEERS_YAML_REL",
    "PEERS_FILE_DEFAULT",
    "FEDERATION_DATA_DIR_REL",
    "ALLOWED_HTTP_METHODS",
    "WRITE_ALLOWED_HTTP_METHODS",
    "MAX_CERT_VALIDITY_DAYS",
    "CERT_EXPIRY_WARN_DAYS",
    "AUDIT_SUMMARY_RATE_PER_MIN",
    "HANDSHAKE_TIMEOUT_SECONDS",
    "PEER_RELOAD_MIN_INTERVAL_SECONDS",
]

# Master kill-switch env (AC12 layer 1 — read-mode).
FEDERATION_KILL_SWITCH_ENV = "CEO_FEDERATION_ENABLED"

# PLAN-112-FOLLOWUP W1 — write-mode master switch (Layer 0a). The ONLY
# truthy value is the exact string "1" (see
# server.write_mode_enabled_from_env). Default-OFF.
FEDERATION_WRITE_KILL_SWITCH_ENV = "CEO_FEDERATION_WRITE_ENABLED"

# Loopback-default bind (AC3).
DEFAULT_BIND = "127.0.0.1"
DEFAULT_PORT = 8843

# AC13 freshness primitive.
MAX_CLOCK_SKEW_SECONDS = 30

# AC1 (waiver) — TLSv1.3 minimum enforced via SSLContext.minimum_version.
MIN_TLS_VERSION_NAME = "TLSv1_3"

# Owner GPG fingerprint allowlist for sentinel verification.
OWNER_GPG_FPR = "0000000000000000000000000000000000000000"

# In-repo federation kernel paths.
FEDERATION_DATA_DIR_REL = ".claude/data/federation"
PEERS_YAML_REL = ".claude/data/federation/peers.yaml"
PEERS_FILE_DEFAULT = ".claude/data/federation/peers.yaml"
ENABLED_SENTINEL_REL = ".claude/data/federation/enabled.md"
ENABLED_SENTINEL_ASC_REL = ".claude/data/federation/enabled.md.asc"
LAN_ENABLED_SENTINEL_REL = ".claude/data/federation/lan-enabled.md"
LAN_ENABLED_SENTINEL_ASC_REL = ".claude/data/federation/lan-enabled.md.asc"
# PLAN-112-FOLLOWUP W1 — Layer 0b write-enable sentinel pair (third pair).
WRITE_ENABLED_SENTINEL_REL = ".claude/data/federation/write-enabled.md"
WRITE_ENABLED_SENTINEL_ASC_REL = ".claude/data/federation/write-enabled.md.asc"

# AC15 — mechanical method allowlist; everything else → 405.
# CRITICAL (default-OFF, AC1/AC7): this constant stays GET-only. POST is
# admitted per-request by the dispatcher's _write_mode_active() gate
# (Layer 0a env AND Layer 0b sentinel) — NOT by flipping this constant.
# WRITE_ALLOWED_HTTP_METHODS documents the effective set WHEN write-mode
# is active (used only for the Allow header advertisement).
ALLOWED_HTTP_METHODS = frozenset(("GET",))
WRITE_ALLOWED_HTTP_METHODS = frozenset(("GET", "POST"))

# AC11 — cert rotation discipline.
MAX_CERT_VALIDITY_DAYS = 90
CERT_EXPIRY_WARN_DAYS = 14

# AC17 — joint-key rate limit on /audit-summary (10/min/peer).
AUDIT_SUMMARY_RATE_PER_MIN = 10

# AC16 — fail-fast handshake timeout.
HANDSHAKE_TIMEOUT_SECONDS = 5.0

# PLAN-112-FOLLOWUP W3 — peer-list reload debounce. The reload-watcher
# stat+hashes peers.yaml at most once per this interval per request path
# so a high-QPS write load doesn't re-hash on every request. The 5s poll
# thread bounds the worst-case propagation under zero traffic; combined
# the <60s SLO holds with a wide margin.
PEER_RELOAD_MIN_INTERVAL_SECONDS = 1.0
