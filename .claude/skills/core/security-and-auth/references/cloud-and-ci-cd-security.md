<!-- PLAN-153 Wave G ADAPT-merge enrichment (rides SP-034 via /skill-review). NOT a verbatim Wave-C extraction — this is net-new knowledge ported clean-room and rewritten in house voice. Provenance is recorded in the parent SKILL.md `inspired_by:` frontmatter (MIT). Edit only via a new SP-034 that bumps the parent SKILL.md version. -->

## Cloud, Infrastructure, and CI/CD Security

The rest of this skill hardens the code inside the process — auth, input
validation, RLS, transport. This reference extends the **same fail-fast and
least-privilege posture to the deploy substrate**: the IAM identities that run
the code, the secrets store it reads, the network it sits on, the pipeline that
ships it, and the edge that fronts it. A perfectly-authorized route behind a
wildcard IAM role or a publicly-reachable database is still fully compromised.

> **Template-posture scope.** This skill's baseline targets a
> Node/Hono + Supabase + Vercel/Cloudflare (and adjacent AWS) deployment, so
> the provider examples below use that stack. The **CI/CD, OIDC-federation, and
> commit/tag-signing rows apply directly to this framework's own release
> pipeline** (GitHub Actions with trusted-publishing OIDC, SBOM emission, signed
> tags — see `release.yml`); the cloud-provider rows are guidance for adopter
> repos that deploy real infrastructure. Read provider-specific lines as
> *pattern*, not *mandate*, for a stdlib-only repo.

### 1. Identity and access — least privilege by default

An IAM role or service identity gets exactly the actions and exactly the
resources it needs, and nothing wider. A wildcard (`s3:*`, `Resource: "*"`) is
a finding, not a convenience.

- Scope every policy to specific **actions** *and* specific **resource ARNs**.
- No human uses the root/owner account for routine production work; break-glass
  only, MFA-gated, and audited when used.
- Service identities assume **short-lived roles**, never carry long-lived
  static keys. A long-lived cloud key checked into anything is a critical.
- MFA on every privileged human account; periodic access review removes
  credentials and grants that stopped being needed.

### 2. Secrets at the infrastructure layer

Environment variables are the **floor**, not the ceiling. `process.env.X` is
un-rotated, un-audited, and readable by anything in the process.

- Prefer a managed secrets store (cloud secrets manager / platform secret
  binding) that gives you **rotation on a schedule** and an **access audit
  trail**.
- Rotate database credentials and API keys on a fixed cadence, automated where
  the platform supports it.
- A secret must never land in an image layer, a CI log line, an error message,
  or a stack trace. (This is the infra-side mirror of the app-side
  "never log secrets" rule in `auth-and-credentials.md`.)

### 3. Network posture

- Stateful stores (databases, caches, queues) are **never publicly reachable**.
  `publicly_accessible = true` on a managed DB is a critical misconfiguration.
- Ingress is allowlisted to the smallest CIDR that works — internal VPC ranges,
  not `0.0.0.0/0`; a security group open on all ports to all IPs is a finding.
- Admin surfaces (SSH/RDP/DB consoles) sit behind a VPN or bastion, never on
  the open internet.
- Constrain egress and turn on flow logs so exfiltration paths are observable.

### 4. CI/CD is a production attack surface

A pipeline that can deploy to production, read secrets, and assume cloud roles
has production-level blast radius. Treat it like one.

- **Federate, don't store.** Use OIDC / short-lived assumed roles for
  cloud access from CI; do not park long-lived cloud keys in CI secrets.
- **Gate on scanning.** Secret scanning and dependency-vulnerability audit run
  as pipeline gates, not afterthoughts.
- **Reproducible installs.** Commit lockfiles; use the locked/`ci` install path
  (`npm ci`, `pip install -r` against a pinned set) so builds are deterministic.
- **Minimal workflow permissions.** Default the pipeline token to
  `contents: read` and widen only per-job, per-need.
- **Provenance at merge and tag.** Branch protection, required review, and
  signed commits/tags — the same posture this framework applies to its own
  releases (signed tag, SBOM, trusted-publishing OIDC).

### 5. Edge and CDN

- A managed WAF ruleset (OWASP core ruleset + provider-managed rules) in front
  of the origin, with rate limiting applied **at the edge** so abuse never
  reaches compute.
- Response security headers set at the edge or origin: `X-Frame-Options`,
  `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`
  (deny geolocation/microphone/etc. by default). This complements — does not
  replace — the CSP guidance in `owasp.md`.
- Strict TLS mode; no plaintext fallbacks.

### 6. Backup and recovery

- Automated backups with retention that meets the compliance floor for the data
  class; deletion protection on stateful resources.
- **Test the restore** — an untested backup is a hypothesis. Define RPO and RTO
  and prove them on a schedule.

### Common infrastructure misconfigurations to reject

| Anti-Pattern | Why It's Wrong | Correct Approach |
|---|---|---|
| Wildcard IAM (`s3:*`, `Resource:"*"`) | One compromised identity owns everything | Scope to specific actions + resource ARNs |
| Long-lived cloud key in CI secrets | Never rotated, high-value theft target | OIDC / short-lived assumed role |
| `publicly_accessible = true` on a DB | Database reachable from the internet | Private subnet + security-group allowlist |
| Security group `0.0.0.0/0` all ports | Full exposure of the host | Smallest CIDR, only the ports in use |
| Secret in image layer or CI log | Leak via registry pull or log access | Managed secrets store; scrub logs |
| No lockfile / `install` in CI | Non-reproducible build, drift-in supply chain | Commit lockfile; locked/`ci` install |
| Public bucket ACL (`public-read`) | Data exposure, the classic breach | Private ACL + explicit bucket policy |
| Untested backup | "Recoverable" is unproven until restored | Scheduled restore drill; RPO/RTO tested |

### Consolidated pre-deployment security gate

Before any production deploy, walk one go/no-go list that spans both the
application layer (covered elsewhere in this skill) and the infrastructure
layer (this reference). Treat an unchecked box as a blocking finding, not a
warning:

- **Secrets** — none hardcoded; all in a managed store; rotation on.
- **Identity** — no root/admin in prod; MFA on privileged accounts; least-privilege IAM.
- **Input & injection** — all input schema-validated; all queries parameterized; user HTML sanitized.
- **AuthN/AuthZ** — tokens in httpOnly cookies (not `localStorage`); authorization checked before every sensitive op; RLS enabled.
- **Network** — no public data stores; ingress allowlisted; admin ports gated.
- **Transport & edge** — HTTPS enforced; strict TLS; WAF + edge rate limiting; security headers set.
- **Pipeline** — OIDC (not stored keys); secret + dependency scanning gates; lockfiles committed; minimal token perms; signed commits/tags.
- **Observability** — auth failures and admin actions logged; no sensitive data in logs; alerts on anomalies; retention meets compliance.
- **Recovery** — automated backups with a *tested* restore; deletion protection on stateful resources.

### Honesty residuals

- The provider-specific mechanics (AWS/Vercel/Cloudflare/Supabase) are template
  guidance; a stdlib-only adopter maps only the CI/CD, OIDC, signing, and
  observability rows onto real infrastructure it operates.
- "Compliance floor" (GDPR/HIPAA/PCI retention, RPO/RTO targets) is
  jurisdiction- and data-class-specific — this reference gives the *shape* of
  the control, not the numeric obligation. Confirm the real floor per program.
- These are **prevention/verification** controls. Detection of an *active*
  compromise lives in `detection-as-code.md`; grading and reporting a concrete
  finding lives in `proof-of-exploitability.md`.
