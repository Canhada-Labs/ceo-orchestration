# ceo-orchestration — Security

> **Status:** Draft published 2026-04-21 under PLAN-045 round-10 sentinel
> as part of F-14 supply-chain hardening. This file is the authoritative
> SECURITY reference pointed at by `SPEC/v1/install-cli.md` §Release
> verification, the `.github/workflows/release.yml` SBOM block, and
> adopter-facing CTO documentation.
>
> **Session 75 amendment (Codex Finding 5, 2026-04-29):** Sigstore
> backend REMOVED per Owner D2 lock. The transparency-log path was
> never wired in `release.yml` (gated `if: false` STAGED) and adding
> it would carry sigstore-python + cryptography + pyOpenSSL runtime
> deps for adopters indefinitely. GPG-tag verification provides a
> strictly stronger trust anchor (Owner key directly, no third-party
> CA). Adopters needing transparency-log attestations SHOULD use
> OS-level package signing (deb / rpm / brew).

## Scope

- Framework release verification (tarball SHA + GPG-signed tag)
- Vulnerability report intake
- Supply-chain trust boundaries
- Cryptographic identity (Owner GPG key)

This file does NOT cover runtime governance hooks (see `PROTOCOL.md`),
plan audit (see `CLAUDE.md` §6), or in-repo secret handling (see
`.claude/hooks/_lib/pii_patterns.py` + check_output_secrets.py).

## Release verification procedure

Every tagged release (`v*`) ships with the following artifacts:

| Artifact | Purpose |
|---|---|
| `release.tar.gz` | Framework tarball |
| `sbom.cyclonedx.json` | Software Bill of Materials (CycloneDX v1.5) |

The release workflow verifies that the pushed git tag was GPG-signed
by the authorized Owner fingerprint
`0000000000000000000000000000000000000000` (see §Cryptographic identity
below).

### Adopter verification — full procedure

```bash
# 1. Download release artifacts
gh release download v1.X.Y \
  --pattern 'release.tar.gz' \
  --pattern 'sbom.cyclonedx.json'

# 2. Verify the git tag signature (Owner GPG key)
#    Requires importing Owner's public key first — see §Cryptographic identity
git fetch --tags origin
gpg --import .claude/trust/owner.asc
git verify-tag v1.X.Y

# 3. (Optional) re-checksum installed skills against shipped manifest
#    AFTER extraction:
bash install.sh /path/to/target --verify
```

All three steps SHOULD succeed before relying on the install. The
`install.sh --verify` flag re-checksums installed skills against
`.claude/skill-manifest.sha256` if the manifest is shipped (advisory
when absent so older releases don't break adopters).

### Sigstore (out of scope per Owner D2)

Sigstore transparency-log verification was scoped during PLAN-045
F-14 but never wired in `release.yml` (the step is gated `if: false`
STAGED). Session 75 Owner D2 lock removes it from the contract:
GPG-tag verification provides a strictly stronger trust anchor (Owner
key directly, no third-party CA), and adding sigstore-python +
cryptography + pyOpenSSL to the runtime trust surface buys little
beyond what `git verify-tag` already guarantees.

## Cryptographic identity

### Owner GPG key

- **Fingerprint:** `0000000000000000000000000000000000000000`
- **Algorithm:** ed25519
- **Holder:** Framework Owner (configure via `install.sh
  --owner-name=<name> --owner-email=<email>`; current upstream
  fingerprint above is the framework dogfood Owner)
- **Created:** 2026-04-20
- **Backup:** 1Password vault (private key + revocation certificate)
- **Public export:** (adopters pin the fingerprint; download public key
  from `https://keys.openpgp.org/search?q=0x0000000000000000000000000000000000000000`)

This key signs:
- SP-NNN skill-patch proposals (`.claude/proposals/SP-NNN-*.md.asc`)
- Canonical-edit sentinels (`.claude/plans/PLAN-NNN/architect/round-M/approved.md.asc`)
- Release tags (`git tag -s v*`)

<!-- Sigstore OIDC identity REMOVED Session 75 (2026-04-29) per Owner D2
     lock — sigstore backend out of scope; GPG-tag verification is the
     canonical trust anchor (see §Sigstore (out of scope per Owner D2)
     above). -->


## Vulnerability report intake

### Reporting a vulnerability

**Private disclosure preferred.** Email the Owner directly at
`<owner-email>` (adopters configure via `install.sh
--owner-email=<your-email>`) with:

- Affected file(s) / line(s) (or a reproducer)
- Exploit scenario (who can trigger, from what context)
- Suggested fix (if any)
- Your preferred coordinated-disclosure timeline (default: 90 days)

### What NOT to open as a public issue

- Unpatched RCE / privilege escalation in hooks
- Authentication bypass in the installer (`install.sh`)
- Supply-chain tamper (forged SP-NNN, sentinel forgery, SHA-pin drift
  exploitation)

### Public reports OK

- Typos, broken links, outdated docs
- Test failures on specific platforms
- Performance issues without a security dimension
- Governance convention questions

## Supply-chain trust boundaries

### Trusted (framework-maintained)

- `.claude/hooks/` Python files — governance enforcement surface.
  Canonical-edit guard + arbitration-kernel HARD-DENY for primitives
  (see `check_arbitration_kernel.py::_KERNEL_PATHS`).
- `.claude/skills/` SKILL.md files — canonical-edit guard; edits only
  via Owner-signed SP-NNN proposals (ADR-031) + sentinel rounds.
- `.claude/adr/` ADR files — canonical-edit guard; L3+ decisions only.
- `SPEC/` schema files — canonical-edit guard; SemVer contract per ADR-007.
- Release artifacts signed per §Release verification above.

### Partially trusted (adopter-configurable)

- `.claude/scripts/` non-lesson Python files — editable without sentinel
  (lesson family excepted: `lessons.py`, `prune-lessons.py`,
  `lesson-restore.py`, `lesson_ranker.py` are canonical-guarded).
- `.claude/agents/*.md` native subagent references — arbitration-kernel
  HARD-DENY (no sentinel escape; Owner physical-shell only).
- `.claude/plans/` — plan files editable under PLAN-SCHEMA rules.

### Untrusted (user-editable)

- `CLAUDE.md` — edited every session during closeout ceremony.
- `MEMORY.md` — auto-loaded native memory; consumer of hook output.
- Everything outside `.claude/` and `SPEC/`.

### Third-party supply chain

- `actions/checkout@<PINNED-SHA>` — GitHub Actions. SHA-pinned per
  `check-action-sha-drift.py` advisory. Dependabot tracks upstream.
- `actions/setup-python@<PINNED-SHA>` — Python runtime. SHA-pinned.
- No non-stdlib Python deps ship in the runtime (ADR-002). CI-only deps
  (`pytest`, `pyyaml`) are installed explicitly in the workflow and
  not included in the tarball.

## Incident response

If a supply-chain compromise is detected post-release:

1. **Revoke** — Owner revokes GPG key (re-runs workflow from a new
   clean branch with rotated key).
2. **Notify** — public GitHub Security Advisory published with affected
   version range + remediation path.
3. **Re-release** — new tag with fresh GPG signature.
4. **Document** — incident record in `docs/incidents/INC-YYYY-MM-DD.md`
   (create if not exists).

## References

- ADR-007: SPEC v1 SemVer + RC policy
- ADR-031: Skill-patch sentinel (SP-NNN proposal lifecycle)
- ADR-055: HMAC chain audit-log (forgery-resistant audit artifact)
- PLAN-045 F-14: supply-chain hardening roadmap
- `SPEC/v1/install-cli.md` §Release verification: adopter-facing CLI
- `.github/workflows/release.yml`: release-gate implementation
