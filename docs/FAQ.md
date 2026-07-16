# FAQ — first-user questions

<!-- last-reviewed: 2026-06-20 v1.0.0 -->

> Short, honest answers to the questions a new user hits in the first hour.
> Deeper material is linked inline. If something here contradicts the code,
> the code wins — please open an issue.

---

### 1. What is this — and what is it *not*?

It is a **governance and auditability layer** for running [Claude Code](https://docs.anthropic.com/en/docs/claude-code) as a structured team of agents. It installs **into** an existing repository and puts a gate and a tamper-evident ledger in front of risky, irreversible changes.

It is **not** a product (no UI, no hosted service), **not** a library you import, **not** a code-completion tool, and **not** a remote controller for other repos. It does not make your agent smarter or faster — it makes failure modes visible and the ceremony on protected paths unavoidable. See [`docs/WHAT-WE-ARE.md`](WHAT-WE-ARE.md) for the long form.

---

### 2. Does it slow me down?

On throughput: **we make no speed claim.** Six internal experiments found no general speedup over an optimized solo Claude Code session — we publish that as a null result rather than dress it up. The value is governance and auditability, which are orthogonal to velocity. See the "No speed claim" section in the [README](../README.md) and [`docs/HONEST-LIMITATIONS.md`](HONEST-LIMITATIONS.md).

On latency: each governed tool call runs the hook chain first, adding **~0.3–1.0s per edit** (see Q5).

---

### 3. A hook just BLOCKED my edit. Now what?

This is the most common first-hour surprise, and it is usually working as intended. The fix depends on the message:

- **`CANONICAL-EDIT-BLOCKED: '<path>' is a canonical governance path`** — you tried to edit a protected file directly. Route the change through `/architect "<what you want changed>"`, or, for a structural framework change, work via a `PLAN-NNN` with an Owner-signed sentinel.
- **`spawn missing ## SKILL CONTENT section`** — you invoked the Agent tool without loading a skill. Use `/spawn` instead of the raw Agent tool.
- **`BLOCKED: 'rm' with -r and -f is destructive`** — destructive bash is denied; do the delete in your own terminal, outside Claude Code.
- **`GOVERNANCE: ... arbitration kernel ... (hard-deny)`** — a kernel path; this needs the stronger `CEO_KERNEL_OVERRIDE` ceremony, not the ordinary sentinel.

Full catalog with fixes: [`docs/TROUBLESHOOTING.md`](TROUBLESHOOTING.md). If you just want a low-friction trial without any of these blocks, install with `--ceremony user` (see Q9).

---

### 4. What if a gate is *wrong* — a false DENY?

Hooks fail **open** on their own infrastructure bugs (a parse error or timeout logs a breadcrumb and allows the action), so an infra glitch will not lock you out. But a *correct* gate can still issue a DENY you disagree with on a protected path. Escalation order:

1. `/architect "<change>"` — routes the edit through review (the normal path).
2. A `PLAN-NNN` with an Owner-signed sentinel — for deliberate framework changes.
3. **Audited override:** the Owner sets `CEO_SENTINEL_UNLOCK=<plan-id>` + `CEO_SENTINEL_UNLOCK_ACK=I-ACCEPT` for that action. The override itself is recorded in the audit log. Kernel hard-denies use `CEO_KERNEL_OVERRIDE=<plan-id>` + `CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` instead.

Never carry an override between sessions — unset it when it is not your current plan.

---

### 5. What's the per-edit overhead?

Roughly **~0.3–1.0s** of added latency per governed tool call on typical hardware — the time to run the hook chain before the action lands. That is the price of the gate. Routine `L1–L2` edits proceed directly; the heavier ceremonies (debate, GPG sentinel) only fire on the risky `L3+` class.

---

### 6. Do I need Codex installed?

**No.** The cross-model pair-rail invokes the [Codex CLI](https://github.com/openai/codex), which is **not** bundled with this framework. On a fresh install with no Codex present, the pair-rail **fails open and contributes nothing** — protected-path edits still pass the GPG ceremony, but no second model reviews them. You only gain the cross-model rung after installing Codex yourself. This is a real limitation, called out in the README §Risks, [`docs/HONEST-LIMITATIONS.md`](HONEST-LIMITATIONS.md), and ADR-145.

---

### 7. Is my code or data sent anywhere?

The framework adds **no telemetry and never calls home.** It uses no API keys beyond the Anthropic key Claude Code already needs. The audit log is a **local** JSONL file written outside your repo; it is not uploaded anywhere. If you install Codex (Q6), the pair-rail sends the *proposed diff* of a protected-path edit to Codex for review — that is the one outbound flow, and it only happens for canonical edits when Codex is present. Runtime dependencies are zero third-party packages (stdlib-only Python ≥ 3.9; see [`SBOM.md`](../SBOM.md)).

---

### 8. What needs my GPG signature?

Only **canonical (protected) path** edits and certain framework-structural changes. When an agent proposes an edit to a guarded path — the skill library, agent personas, ADRs, the `SPEC/`, the governance config, the enforcement-core hooks — the change is staged and requires an Owner-signed **sentinel** (a detached GPG signature over the approved change) before it lands. Routine edits to your own application code need no signature. Kernel paths (the arbitration core) need the stronger `CEO_KERNEL_OVERRIDE` ceremony rather than the ordinary sentinel. See [`PROTOCOL.md`](../PROTOCOL.md) and [`docs/TROUBLESHOOTING.md`](TROUBLESHOOTING.md).

---

### 9. How do I trial it with the least friction?

Install with the advisory mode:

```bash
./scripts/install.sh /path/to/your-app --ceremony user
```

`--ceremony user` runs **advisory hooks only** — no signing ceremonies, and the installer writes only under `.claude/`. You get the audit trail and the spawn/plan structure to feel out, without the GPG friction on protected paths. Switch to the default `--ceremony maintainer` when you want the full gate. See the [README](../README.md) Quick start and [`docs/QUICKSTART.md`](QUICKSTART.md).

---

### 10. How do I uninstall?

A SHA-pinned manifest tracks every file the installer placed, so removal is clean:

```bash
/path/to/ceo-orchestration/scripts/uninstall.sh /path/to/your-app
```

It removes the governance hooks, scripts, and skill profiles it added, leaving your application code untouched. The local audit log lives outside the repo and is yours to keep or delete.

---

### 11. What exactly do I get — how do I verify the numbers?

Don't take the README table on faith. From a clean checkout:

```bash
find .claude/skills -name SKILL.md | wc -l        # 151 skills (42 core + 8 frontend + 101 domain)
ls .claude/commands/*.md | wc -l                  # 22 slash commands
ls .claude/adr | grep -c '^ADR-'                  # 178 ADRs
python3 -m pytest --collect-only -q | tail -1     # ~12,000 collected cases
```

Every count in the README is reproducible this way. See the README "Verifying the numbers" section.

---

### 12. Where do I go deeper?

- [`docs/QUICKSTART.md`](QUICKSTART.md) — install and confirm the layer is live.
- [`docs/DAY-1-CHECKLIST.md`](DAY-1-CHECKLIST.md) — a guided first session.
- [`PROTOCOL.md`](../PROTOCOL.md) — the governance contract (Plan → Debate → Execute, vetoes, three-strike rule).
- [`docs/HONEST-LIMITATIONS.md`](HONEST-LIMITATIONS.md) — every caveat, long-form.
- [`docs/TROUBLESHOOTING.md`](TROUBLESHOOTING.md) — when a hook blocks you.
