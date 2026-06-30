# ceo-orchestration — what you get (a note to the CTO)

> A focused one-page note, calibrated for a skeptical CTO. No hype — every
> claim is verifiable.
>
> **Português:** [CEO-ORCHESTRATION-FOR-CTO.pt-BR.md](CEO-ORCHESTRATION-FOR-CTO.pt-BR.md).

**In one line:** this is not an agent accelerator. It is the **governance +
audit layer** that lets you run AI agents in sensitive workflows and **prove
afterward what each one did** — without a speed penalty.

## What you get (concrete)

1. **A tamper-evident audit trail.** Every action of every agent is appended to
   an HMAC-chained log. You can prove — for risk, compliance, or audit — exactly
   what the agent did and in what order; and any later alteration of the record
   **is detectable** (the chain breaks). *Tamper-evident, not tamper-proof: it
   detects tampering, it does not prevent someone with disk access from making
   changes — and that distinction is documented.*

2. **Governance gates that actually block.** Agent spawns, edits to canonical
   files, operation limits — enforced at the tool-call level, as an invariant,
   not as a recommendation. "The agent does not do X without Y" becomes a
   guarantee (with deliberate *fail-open* behavior on infrastructure failure, so
   a bug in the guard itself never stalls the session).

3. **No speed toll.** The governance layer costs **tens of milliseconds per
   call** and runs on top of an ordinary solo agent. Governance and speed are
   **orthogonal** — adopting it does not make you slower. This was measured, not
   assumed.

4. **Safe parallelization when you need coverage.** When it makes sense to spread
   work out, it has been measured **not to corrupt the output** (0/10 probes
   corrupted, quality tied). Fan-out is for *breadth*, not for speed.

## What it explicitly does NOT do (which is why you can trust the rest)

- **It does not make the agent faster.** Orchestration/fan-out is structurally
  ~2-3× more expensive and ties-to-worse against an optimized solo agent. **We
  tested this ourselves across six experiments and buried the speed thesis** —
  and the external literature agrees (one strong agent ≥ several on the same
  budget).
- **It does not replace your CI/tests.** It complements them with provenance and
  governance.

## Evidence (not marketing)

- **12,007 parametrized test cases** across 676 files, including a
  governance/audit core of **6,170** in the hook layer.
- **Six paid experiments that falsified our own speed hypothesis.** The claims
  above are what **survived** the test — not what we would like to sell.

## Cost of adoption

Low. Installable into any repo (`install.sh --ceremony user`, no GPG ceremony),
**Python stdlib-only**, zero infrastructure dependencies. Runtime overhead on the
order of milliseconds.

---

> **Summary:** you are going to run AI agents either way. This is the layer that
> lets you **prove what they did** and **block what they should not** — without
> costing you speed.

**Anticipating the next objection** (*"why not just log everything to a plain
file?"*): a plain log can be edited without a trace; this one cannot — the HMAC
chain breaks on tampering, and that is exactly what an auditor or regulator
requires. A 2-minute demo is available: tamper with a single line of the log and
the HMAC catches it instantly.
