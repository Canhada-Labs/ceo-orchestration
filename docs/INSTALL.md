# INSTALL — bootstrap notes

This document supplements `INSTALL.md` at the repo root. It covers
**hardened bootstrap** for adopters who want checksum-verified
dependencies and a minimal trusted-binary surface when installing the
framework.

## Quick install

```bash
git clone https://github.com/Canhada-Labs/ceo-orchestration
bash ceo-orchestration/scripts/install.sh /path/to/your-project --profile core
```

`install.sh` enforces a **required-deps preflight** (PLAN-019 P2-SEC-F)
— it refuses to start if `sed` or `git` are missing. `jq` is
conditionally required only when `--stack <name>` is explicitly
supplied; the script hard-fails in that case with a clear error.

## Hardened bootstrap (P2-SEC-F)

If you are installing into a security-sensitive environment
(regulated, air-gapped, or CI pipeline), verify your host tools against
published checksums before running `install.sh`. The framework itself
is stdlib-only Python 3.9+, but `install.sh` shells out to:

- **git** — for canonical-edit sentinel detection and fresh-repo init.
- **sed** — for placeholder substitution in templates.
- **jq** (conditional) — for merging `settings.json` stack overlays.
- **bash** ≥ 3.2 — for `install.sh` itself (guarded at the top).

### Recommended checksum verification recipe

On macOS (Homebrew) the versions that ship are typically ahead of
Linux distro packages. For reproducible CI bootstraps, pin to specific
versions and verify SHAs against the upstream project's release page:

```bash
# jq — https://github.com/jqlang/jq/releases
JQ_VERSION=1.7.1
JQ_SHA256=5942c9b0934e510ee61eb3e30273f1b3fe2590df93933a93d7c58b81d19c8ff5

curl -fsSL "https://github.com/jqlang/jq/releases/download/jq-${JQ_VERSION}/jq-linux-amd64" -o /tmp/jq
echo "${JQ_SHA256}  /tmp/jq" | sha256sum --check --
chmod +x /tmp/jq && sudo mv /tmp/jq /usr/local/bin/jq

# git — rely on distro package manager; most Linux distros sign their
# packages via the distro key. Verify by:
apt-get install --assume-no git       # Debian / Ubuntu (show dry-run)
# OR
dnf install --assumeno git            # Fedora / RHEL (show dry-run)
```

The checksums above are illustrative; **always** pull the current SHA
from the upstream release page (jq / git / GNU coreutils) at the time
you provision.

### Why not auto-pin in `install.sh`?

Pinning checksums inside `install.sh` would:

1. Make the script **stale** as upstream tools release security fixes.
2. Couple framework adopters to a specific supply-chain stance that
   may conflict with their enterprise allow-list.
3. Violate the "stdlib-only + bash-portable" invariant — SHA-pinned
   deps typically require network fetch, which `install.sh` avoids
   (adopters can install offline from a checked-out clone).

Instead, `install.sh`:

- Preflights required binaries (`sed`, `git`) and **fails fast** with
  a user-friendly error listing the missing names (P2-SEC-F).
- Hard-fails (exit 3) when `--stack <name>` is explicit and `jq`
  is missing (prevents silent fallback-to-base-only).
- Documents this hardened-bootstrap recipe here for adopters who need
  reproducible provisioning.

## MCP shared-secrets directory (P2-SEC-H)

`install.sh` now creates `state/mcp_client_secrets/` with mode `0700`
and appends it to `.gitignore`. This directory stores per-client HMAC
secrets used by the MCP server (`.claude/scripts/mcp-server/`). File
perms on individual `<client_id>.key` files MUST be `0600` —
`auth.load_secret()` fails-closed otherwise.

**Never commit secret files to VCS.** The `.gitignore` entry is
belt-and-braces; the underlying expectation is that adopters generate
secrets locally and copy them to production out of band.

## MCP transport security (P2-SEC-K)

The MCP server refuses to bind plaintext HTTP on non-loopback
interfaces unless one of the following is true:

1. `CEO_MCP_TLS_CERT` + `CEO_MCP_TLS_KEY` env vars point at a valid
   cert/key pair (server wraps the socket in TLSv1.2+).
2. `CEO_MCP_ALLOW_PLAINTEXT_PUBLIC=1` is explicitly set (opt-in, loud
   stderr banner, LOCAL TESTING ONLY).

Default bind is `127.0.0.1:9000` where plaintext is safe because
packets never leave the host.

## See also

- `docs/threat-model.md` — STRIDE analysis, token replay, off-host exfil.
- `docs/mcp-cursor-setup.md` — concrete client setup walkthrough.
- `docs/soc2-audit-mapping.md` — control-ID → evidence mapping.
- `INSTALL.md` (repo root) — the full installer contract + options.
