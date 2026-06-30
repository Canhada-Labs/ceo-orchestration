<!--
PLAN-133 E1 — Adversary local-rules ruleset (LOCAL-RULES-ONLY, default-OFF).

This file is the DATA source for the `check_adversary.py` PreToolUse hook. The hook
is a DETERMINISTIC local-rules deny/ask gate — it makes NO live per-op model call
(the rite REJECTED sync Codex on the Bash hot path: sync Codex is a measured 40x-600x
p99 regression vs the ~5ms warm hook floor, and real adversarial depth already lives
in the canonical/L3 Codex pair-rail). See PLAN-133 §E [E1] + §DO-NOT-BUILD.

ENABLEMENT (doctrine #1 — default-OFF + measure-first):
  CEO_ADVERSARY=0   (default) -> hook DETECTS + emits the advisory breadcrumb, ALLOWS.
  CEO_ADVERSARY=1            -> hook ENFORCES: a `deny` rule blocks, an `ask` rule asks.
  Publish p50/p95/p99 + per-session-cap stats before any default-on flip.

SECURITY INVARIANTS (enforced in the hook, NOT here — this file is untrusted data):
  - This file is read from inside CLAUDE_PROJECT_DIR only (never env-text), with a hard
    size cap. A malformed/oversize/missing file -> the hook fails OPEN (advisory, allow).
  - The ruleset is DATA. The hook never executes anything from it. A rule's `match` is a
    plain substring or an anchored, length-bounded regex compiled with a step budget.
  - No value-echo: the audit breadcrumb carries ONLY the closed-enum decision + the
    rule_id + a rule_class. It NEVER carries the matched command text, the matched
    substring, or any environment value.
  - SECRET FAIL-CLOSED: independent of these rules, if a live-credential pattern matches
    inside the proposed command, the gate DENIES (CEO_ADVERSARY=1) / flags (default-OFF)
    and the command is NEVER transmitted anywhere. This is hardcoded in the hook via the
    canonical secret_patterns bank — it does not depend on a rule below.

RULE FORMAT (one rule per fenced `adversary-rule` block; fields are `key: value` lines):
  id:      stable snake_case identifier (unique). Surfaced in the audit breadcrumb.
  class:   closed enum — one of: destructive | exfiltration | privilege | tampering | other
  action:  deny | ask        (only honored when CEO_ADVERSARY=1; advisory otherwise)
  match:   substring         (default) OR
  regex:   anchored regex    (use EITHER match OR regex, not both)
  why:     short operator-facing rationale (shown to the Owner; never to a model prompt)

Unknown keys are ignored. A rule missing `id`/`class`/`action`/(`match`|`regex`) is
SKIPPED (the hook logs a parse breadcrumb and continues — fail-open per rule).
-->

# Adversary local rules (PLAN-133 E1)

These are conservative, deterministic patterns for Bash commands that an adversarial
or compromised actor would run. They are intentionally narrow (low false-positive) and
are advisory until `CEO_ADVERSARY=1`.

```adversary-rule
id: exfil_curl_pipe_shell
class: exfiltration
action: ask
regex: ^.*\bcurl\b.{0,200}\|\s*(ba)?sh\b.*$
why: Piping a remote download straight into a shell runs unreviewed remote code.
```

```adversary-rule
id: exfil_wget_pipe_shell
class: exfiltration
action: ask
regex: ^.*\bwget\b.{0,200}\|\s*(ba)?sh\b.*$
why: Piping a remote download straight into a shell runs unreviewed remote code.
```

```adversary-rule
id: exfil_reverse_shell_bash_dev_tcp
class: exfiltration
action: deny
match: /dev/tcp/
why: bash /dev/tcp redirection is a classic reverse-shell / data-exfil channel.
```

```adversary-rule
id: exfil_nc_listen
class: exfiltration
action: ask
regex: ^.*\bnc\b.{0,80}\s-[a-zA-Z]*l[a-zA-Z]*\b.*$
why: A netcat listener is a common exfil / backdoor primitive.
```

```adversary-rule
id: tamper_disable_history
class: tampering
action: ask
regex: ^.*\bunset\s+HIST(FILE|SIZE|FILESIZE)\b.*$
why: Disabling shell history is a common anti-forensics step.
```

```adversary-rule
id: tamper_truncate_audit_log
class: tampering
action: deny
regex: ^.*audit-log\.jsonl.{0,40}(>|truncate|shred|rm\b).*$
why: Direct mutation of the HMAC audit chain breaks tamper-evidence.
```

```adversary-rule
id: privilege_curl_to_sudo
class: privilege
action: ask
regex: ^.*\bcurl\b.{0,200}\|\s*sudo\b.*$
why: Downloaded content piped to sudo escalates unreviewed remote code to root.
```

```adversary-rule
id: privilege_chmod_4755_setuid
class: privilege
action: ask
regex: ^.*\bchmod\b\s+[0-7]*[4-7][0-7]{3}\b.*$
why: Setting a setuid/setgid bit is a privilege-escalation persistence pattern.
```

```adversary-rule
id: destructive_rm_rf_root
class: destructive
action: deny
regex: ^.*\brm\b\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+(/|/\*|~|\$HOME)\s*$
why: Recursive force-delete of a filesystem root or home is unrecoverable.
```
