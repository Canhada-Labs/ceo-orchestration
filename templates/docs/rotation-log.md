# API key rotation log

> Append-only log of `ANTHROPIC_API_KEY` rotations. See
> `docs/BRANCH-PROTECTION.md` §"API Key Hygiene" for the rotation
> procedure and policy.
>
> **Format per entry:**
> - date (ISO 8601)
> - reason (suspicion / compromise / scheduled / initial setup)
> - rotated_by (handle)
> - outcome (ok / reverted / incident)
>
> NEVER paste a key into this file. The key's presence anywhere in
> version control is itself a rotation trigger.

## Log

(no rotations yet — repository file created in Sprint 2 Item F)
