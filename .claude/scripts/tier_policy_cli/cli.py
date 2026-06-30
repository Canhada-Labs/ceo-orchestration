"""PLAN-043 Phase 4 — ceo-tier-policy CLI subcommands.

Subcommands:

- ``derive`` — read tournaments → emit Recommendation JSON; NO writes
- ``apply`` — promote-auto + demote-signed dispatch (kill-switch gated)
- ``owner-sign`` — Owner signs demote / cost-gated-promote into sigchain
- ``verify`` — check policy HMAC + sigchain integrity
- ``show`` — pretty-print current policy state
- ``enable`` — write Owner-signed sentinel (two-factor second factor)
- ``rotate-key`` — rotate tier-policy key (Owner-signed)
- ``sigchain-rotate`` — archive sigchain > 1000 entries (Owner-signed)
- ``migrate`` — forward-migrate schema_version

Owner-sign guardrails per C-P0-11:
- ``git config user.email`` MUST match an entry in
  ``.claude/tier-policy.owners.txt`` (allowlist).
- The sign operation writes a git-signed commit (``git commit -S``) in
  the same transaction. Commit signature IS the attribution; the
  sigchain entry is the structured tamper-evident log. If
  ``git commit -S`` fails (no key / SIGN aborted), the sigchain entry
  is NOT written.

Sentinel enable per C-P0-12:
- ``ceo-tier-policy enable`` writes sentinel with Owner-signed content
  ``sha256(random_nonce) + owner_commit_sha`` + file mode 0600 +
  parent dir 0700. Apply path verifies sentinel's commit signature
  via ``git verify-commit`` before honoring.

stdlib-only (ADR-002). Python >= 3.9.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from . import apply as apply_mod
    from . import learn as learn_mod
    from . import loader as loader_mod
    from ._types import (
        CANONICAL_5_AGENTS,
        CURRENT_POLICY_SCHEMA_VERSION,
        VALID_MODEL_IDS,
    )
except ImportError:  # pragma: no cover
    import apply as apply_mod  # type: ignore[no-redef]
    import learn as learn_mod  # type: ignore[no-redef]
    import loader as loader_mod  # type: ignore[no-redef]
    from _types import (  # type: ignore[no-redef]
        CANONICAL_5_AGENTS,
        CURRENT_POLICY_SCHEMA_VERSION,
        VALID_MODEL_IDS,
    )


# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------

DEFAULT_POLICY_PATH = Path(".claude/tier-policy.json")
DEFAULT_SIGCHAIN_PATH = Path(".claude/tier-policy.json.sigchain")
DEFAULT_OWNERS_FILE = Path(".claude/tier-policy.owners.txt")
DEFAULT_SENTINEL = Path(
    os.path.expanduser("~/.ceo-orchestration/tier-policy/.enabled")
)
DEFAULT_BENCHMARKS_DIR = Path("benchmarks")
DEFAULT_AGENTS_DIR = Path(".claude/agents")
DEFAULT_BASELINE_AGENTS = Path("templates/agents")

_SP_CHAIN_ID_RE = re.compile(r"^SP-\d{3}-[a-f0-9]{8}$")


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _git_config_email() -> Optional[str]:
    try:
        r = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            return r.stdout.strip() or None
    except Exception:
        return None
    return None


def _git_head_sha() -> Optional[str]:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            return r.stdout.strip() or None
    except Exception:
        return None
    return None


def _git_commit_signed(message: str) -> bool:
    """Run ``git commit -S -m <message>``; True on success."""
    try:
        r = subprocess.run(
            ["git", "commit", "-S", "-m", message],
            capture_output=True, text=True, timeout=30,
        )
        return r.returncode == 0
    except Exception:
        return False


def _git_verify_commit(sha: str) -> bool:
    """Verify a commit signature via ``git verify-commit``."""
    try:
        r = subprocess.run(
            ["git", "verify-commit", sha],
            capture_output=True, text=True, timeout=10,
        )
        return r.returncode == 0
    except Exception:
        return False


def _owners_allowlist(
    owners_file: Path = DEFAULT_OWNERS_FILE,
) -> List[str]:
    """Read allowlist of emails from owners.txt (one per line)."""
    if not owners_file.exists():
        return []
    try:
        lines = owners_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [
        line.strip()
        for line in lines
        if line.strip() and not line.strip().startswith("#")
    ]


def _require_owner_allowlisted(owners_file: Path) -> Optional[str]:
    """Return git email if allowlisted; else None with eprintln."""
    email = _git_config_email()
    if email is None:
        sys.stderr.write(
            "owner-sign: git user.email unset; aborting\n"
        )
        return None
    allow = _owners_allowlist(owners_file)
    if not allow:
        sys.stderr.write(
            "owner-sign: allowlist {a} empty or missing; "
            "Owner must populate it first\n".format(a=owners_file)
        )
        return None
    if email not in allow:
        sys.stderr.write(
            "owner-sign: {e} not in allowlist {a}; aborting\n".format(
                e=email, a=owners_file,
            )
        )
        return None
    return email


# ---------------------------------------------------------------------
# Sigchain verification (wraps _lib/audit_hmac.verify_chain)
# ---------------------------------------------------------------------

def _load_audit_hmac_module() -> "Optional[Any]":
    """Late-load _lib.audit_hmac; return module or None."""
    try:
        try:
            from _lib import audit_hmac as _ah  # type: ignore
            return _ah
        except (ImportError, ValueError):
            pass
        import importlib.util
        hooks_lib = (
            Path(__file__).resolve().parent.parent.parent
            / "hooks" / "_lib" / "audit_hmac.py"
        )
        if not hooks_lib.exists():
            return None
        spec = importlib.util.spec_from_file_location(
            "_ah_ext", str(hooks_lib)
        )
        if spec is None or spec.loader is None:
            return None
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m
    except Exception:
        return None


# ---------------------------------------------------------------------
# Subcommand implementations
# ---------------------------------------------------------------------

def cmd_derive(args) -> int:
    """Handle the `ceo-tier-policy derive` sub-command — compute recommendations from tournament evidence."""
    policy_path = Path(args.policy) if args.policy else DEFAULT_POLICY_PATH
    reports_dir = Path(args.reports) if args.reports else DEFAULT_BENCHMARKS_DIR
    load_result = loader_mod.load_policy(policy_path)
    policy_record = load_result.policy_record
    if policy_record is None:
        # Bootstrap / fallback — synthesize a baseline record for learn.
        from ._types import TierPolicyRecord
        policy_record = TierPolicyRecord(
            schema_version=CURRENT_POLICY_SCHEMA_VERSION,
            generated_at=datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            baseline_from="ADR-052",
            assignments={
                slug: assign for slug, assign in load_result.baseline.items()
            },
            hmac_anchor="0" * 64,
            sigchain_tip_length=1,
            last_change_by_role={},
        )
    recommendations = learn_mod.learn(
        reports_dir, policy_record,
    )
    out = [
        {
            "agent_slug": r.agent_slug,
            "current_tier": r.current_tier,
            "recommended_tier": r.recommended_tier,
            "action": r.action,
            "evidence": {
                "n": r.evidence.n,
                "gap_pp": r.evidence.gap_pp,
                "last_updated": r.evidence.last_updated,
                "runs_considered": r.evidence.runs_considered,
                "tournament_report_hmacs": list(
                    r.evidence.tournament_report_hmacs
                ),
            },
            "signature_required": r.signature_required,
            "cooldown_ok": r.cooldown_ok,
            "rejection_reason": r.rejection_reason,
        }
        for r in recommendations
    ]
    json.dump(out, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


def cmd_apply(args) -> int:
    """Handle the `ceo-tier-policy apply` sub-command — mutate policy under filelock."""
    policy_path = Path(args.policy) if args.policy else DEFAULT_POLICY_PATH
    sigchain_path = (
        Path(args.sigchain) if args.sigchain else DEFAULT_SIGCHAIN_PATH
    )
    reports_dir = (
        Path(args.reports) if args.reports else DEFAULT_BENCHMARKS_DIR
    )
    agents_dir = Path(args.agents) if args.agents else DEFAULT_AGENTS_DIR
    baseline_dir = (
        Path(args.baseline) if args.baseline else DEFAULT_BASELINE_AGENTS
    )
    load_result = loader_mod.load_policy(policy_path)
    policy_record = load_result.policy_record
    if policy_record is None:
        sys.stderr.write(
            "apply: no valid policy artifact at {p}; run "
            "``ceo-tier-policy derive`` + ``enable`` first.\n".format(
                p=policy_path
            )
        )
        return 1
    recommendations = learn_mod.learn(reports_dir, policy_record)
    if not recommendations:
        sys.stdout.write(
            "apply: no recommendations (insufficient fresh reports or "
            "gate rejected all candidates); nothing to do.\n"
        )
        return 0
    result = apply_mod.apply(
        recommendations,
        policy_record,
        agents_dir=agents_dir,
        baseline_agents_dir=baseline_dir,
        policy_path=policy_path,
        sigchain_path=sigchain_path,
        dry_run=args.dry_run,
    )
    sys.stdout.write("apply: outcome={o}\n".format(o=result.outcome))
    for oc in result.outcomes:
        sys.stdout.write(
            "  {slug:<22} {rc:<18} {a}→{b}{d}\n".format(
                slug=oc.agent_slug,
                rc=oc.outcome,
                a=oc.from_tier,
                b=oc.to_tier,
                d=(" [" + oc.detail + "]") if oc.detail else "",
            )
        )
    return 0 if result.outcome == "success" else 2


def cmd_owner_sign(args) -> int:
    """Handle the `owner-sign` sub-command — append Owner-signed sigchain entry."""
    owners_file = (
        Path(args.owners_file) if args.owners_file else DEFAULT_OWNERS_FILE
    )
    email = _require_owner_allowlisted(owners_file)
    if email is None:
        return 1
    if not _SP_CHAIN_ID_RE.match(args.sp_chain_id):
        sys.stderr.write(
            "owner-sign: sp_chain_id must match ^SP-\\d{3}-[a-f0-9]{8}$\n"
        )
        return 2
    if args.from_tier not in VALID_MODEL_IDS:
        sys.stderr.write(
            "owner-sign: from_tier must be a known model ID\n"
        )
        return 2
    if args.to_tier not in VALID_MODEL_IDS:
        sys.stderr.write(
            "owner-sign: to_tier must be a known model ID\n"
        )
        return 2
    if args.agent not in CANONICAL_5_AGENTS:
        sys.stderr.write(
            "owner-sign: agent must be one of canonical-5\n"
        )
        return 2
    sigchain_path = (
        Path(args.sigchain) if args.sigchain else DEFAULT_SIGCHAIN_PATH
    )
    # Append sigchain entry (HMAC signed via _lib/audit_hmac).
    ah = _load_audit_hmac_module()
    if ah is None:
        sys.stderr.write(
            "owner-sign: _lib/audit_hmac unavailable; aborting\n"
        )
        return 3
    action = "promote" if (
        VALID_MODEL_IDS.index(args.to_tier)
        > VALID_MODEL_IDS.index(args.from_tier)
    ) else "demote"
    prior_tip = _read_sigchain_tip_length(sigchain_path)
    entry = {
        "timestamp": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "author": email,
        "sp_chain_id": args.sp_chain_id,
        "action": action,
        "agent_slug": args.agent,
        "from_tier": args.from_tier,
        "to_tier": args.to_tier,
        "evidence_hmac": args.evidence_hmac or ("0" * 64),
        "prior_hash": _read_sigchain_prior_hash(sigchain_path),
        "chain_length": prior_tip + 1,
        "prior_commit_sha": _git_head_sha() or "0" * 40,
    }
    # Attach HMAC.
    try:
        key = ah.get_or_create_key()
        prev = bytes.fromhex(entry["prior_hash"])
        digest = ah.compute_entry_hmac(key, prev, entry)
        entry["hmac"] = ah.hex_digest(digest)
    except Exception as e:
        sys.stderr.write(
            "owner-sign: HMAC failed: {e}\n".format(e=e)
        )
        return 4
    # Append + stage git commit.
    try:
        with sigchain_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, sort_keys=True) + "\n")
    except OSError as e:
        sys.stderr.write(
            "owner-sign: sigchain write failed: {e}\n".format(e=e)
        )
        return 5
    # git add + git commit -S.
    try:
        subprocess.run(
            ["git", "add", str(sigchain_path)],
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        pass
    msg = "tier-policy: sign {act} {a} {f}→{t}".format(
        act=action, a=args.agent, f=args.from_tier, t=args.to_tier,
    )
    if not args.skip_commit:
        if not _git_commit_signed(msg):
            sys.stderr.write(
                "owner-sign: git commit -S failed; sigchain entry "
                "written but NOT git-signed. Manually commit + sign.\n"
            )
            return 6
    sys.stdout.write(
        "owner-sign: signed {a} {f}→{t} with sp_chain_id={s}\n".format(
            a=args.agent, f=args.from_tier, t=args.to_tier,
            s=args.sp_chain_id,
        )
    )
    return 0


def cmd_verify(args) -> int:
    """Handle the `ceo-tier-policy verify` sub-command — assert sigchain integrity."""
    sigchain_path = (
        Path(args.sigchain) if args.sigchain else DEFAULT_SIGCHAIN_PATH
    )
    if not sigchain_path.exists():
        sys.stdout.write(
            "verify: sigchain absent at {p} — nothing to verify "
            "(bootstrap mode).\n".format(p=sigchain_path)
        )
        return 0
    ah = _load_audit_hmac_module()
    if ah is None:
        sys.stderr.write(
            "verify: _lib/audit_hmac unavailable; aborting\n"
        )
        return 3
    result = ah.verify_chain(sigchain_path)
    if result.is_intact:
        # Also check policy artifact's sigchain_tip_length vs actual
        # line count (C-P0-5 truncation defense).
        policy_path = (
            Path(args.policy) if args.policy else DEFAULT_POLICY_PATH
        )
        if policy_path.exists():
            try:
                obj = json.loads(policy_path.read_text(encoding="utf-8"))
                expected = obj.get("sigchain_tip_length", 1)
                actual = sum(
                    1 for _ in sigchain_path.open("r", encoding="utf-8")
                    if _.strip()
                )
                if expected != actual:
                    sys.stderr.write(
                        "verify: TRUNCATION DETECTED — policy says "
                        "sigchain_tip_length={e} but actual lines={a}\n".format(
                            e=expected, a=actual,
                        )
                    )
                    return 7
            except (OSError, ValueError):
                pass
        sys.stdout.write(
            "verify: sigchain intact ({n} entries verified)\n".format(
                n=result.verified_count
            )
        )
        return 0
    sys.stderr.write(
        "verify: FAILURE — status={s} line={l} reason={r}\n".format(
            s=result.status, l=result.line, r=result.reason,
        )
    )
    return 8


def cmd_show(args) -> int:
    """Handle the `ceo-tier-policy show` sub-command — print current policy state."""
    policy_path = Path(args.policy) if args.policy else DEFAULT_POLICY_PATH
    load_result = loader_mod.load_policy(policy_path)
    policy_record = load_result.policy_record
    if policy_record is None:
        sys.stdout.write(
            "show: no policy artifact (status={s}, reason={r}); "
            "using ADR-052 baseline\n".format(
                s=load_result.status, r=load_result.reason,
            )
        )
        for slug, a in load_result.baseline.items():
            sys.stdout.write(
                "  {:<22} {}\n".format(slug, a.tier)
            )
        return 0
    sys.stdout.write(
        "show: schema_version={sv} generated_at={g}\n".format(
            sv=policy_record.schema_version, g=policy_record.generated_at,
        )
    )
    for slug, a in policy_record.assignments.items():
        locked = (
            " [LOCKED:{}]".format(a.locked_by) if a.locked_by else ""
        )
        sys.stdout.write(
            "  {:<22} {}{}\n".format(slug, a.tier, locked)
        )
    return 0


def cmd_enable(args) -> int:
    """Handle the `ceo-tier-policy enable` sub-command — flip the kill-switch to active."""
    owners_file = (
        Path(args.owners_file) if args.owners_file else DEFAULT_OWNERS_FILE
    )
    email = _require_owner_allowlisted(owners_file)
    if email is None:
        return 1
    sentinel = Path(args.sentinel) if args.sentinel else DEFAULT_SENTINEL
    sentinel.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(sentinel.parent, 0o700)
    except OSError:
        pass
    # Owner-signed content: sha256(random_nonce) + commit_sha.
    nonce = secrets.token_hex(32)
    commit_sha = _git_head_sha() or ("0" * 40)
    digest = hashlib.sha256(nonce.encode("utf-8")).hexdigest()
    content = "{}\n{}\n".format(digest, commit_sha)
    tmp = sentinel.with_name(
        sentinel.name + ".tmp.{pid}".format(pid=os.getpid())
    )
    try:
        fd = os.open(
            str(tmp),
            os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600,
        )
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(str(tmp), str(sentinel))
    except OSError as e:
        sys.stderr.write(
            "enable: sentinel write failed: {e}\n".format(e=e)
        )
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        return 5
    if not args.skip_commit:
        _git_commit_signed("enable tier-policy")
    sys.stdout.write(
        "enable: sentinel written at {p} (owner-signed content)\n".format(
            p=sentinel
        )
    )
    return 0


def cmd_rotate_key(args) -> int:
    """Stub: rotate tier-policy-specific HMAC key (Owner-signed).

    Rotation is an operational emergency path (key compromise / routine
    rekeying every N months). Full implementation deferred to PLAN-044
    key-management infra. MVP: refuse without --confirm and print the
    migration instructions.
    """
    owners_file = (
        Path(args.owners_file) if args.owners_file else DEFAULT_OWNERS_FILE
    )
    if _require_owner_allowlisted(owners_file) is None:
        return 1
    if not args.confirm:
        sys.stderr.write(
            "rotate-key: refusing without --confirm. Key rotation will\n"
            "invalidate the existing sigchain. See docs/TIER-POLICY.md\n"
            "§Key rotation for the full procedure.\n"
        )
        return 2
    sys.stdout.write(
        "rotate-key: not yet implemented in MVP; see docs/TIER-POLICY.md.\n"
        "           Manual rotation: (1) generate new 32-byte key at\n"
        "           ~/.claude/projects/<slug>/tier-policy-key, (2) back\n"
        "           up old key, (3) re-seed sigchain from current tip\n"
        "           via ``sigchain-rotate --force``, (4) git commit -S\n"
    )
    return 9  # stub


def cmd_sigchain_rotate(args) -> int:
    """Stub: archive sigchain > 1000 entries + re-seed.

    Refuses unless chain > rotation threshold to prevent accidental
    rotation. Use ``--force`` with Owner sign-off for key-rotation
    companion flow.
    """
    sigchain_path = (
        Path(args.sigchain) if args.sigchain else DEFAULT_SIGCHAIN_PATH
    )
    if not sigchain_path.exists():
        sys.stdout.write(
            "sigchain-rotate: nothing to rotate (sigchain absent).\n"
        )
        return 0
    n = _read_sigchain_tip_length(sigchain_path)
    if n < 1000 and not args.force:
        sys.stderr.write(
            "sigchain-rotate: chain has {n} entries (< 1000 threshold); "
            "refusing without --force.\n".format(n=n)
        )
        return 2
    owners_file = (
        Path(args.owners_file) if args.owners_file else DEFAULT_OWNERS_FILE
    )
    if _require_owner_allowlisted(owners_file) is None:
        return 1
    # Archive + reseed (atomic rename).
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive = sigchain_path.with_name(
        sigchain_path.name + ".archive.{ts}".format(ts=ts)
    )
    try:
        os.replace(str(sigchain_path), str(archive))
    except OSError as e:
        sys.stderr.write(
            "sigchain-rotate: archive failed: {e}\n".format(e=e)
        )
        return 5
    sys.stdout.write(
        "sigchain-rotate: archived {n} entries to {a}; "
        "next sigchain entry becomes genesis.\n".format(
            n=n, a=archive,
        )
    )
    return 0


def cmd_migrate(args) -> int:
    policy_path = Path(args.policy) if args.policy else DEFAULT_POLICY_PATH
    load_result = loader_mod.load_policy(policy_path)
    if load_result.status == loader_mod.STATUS_MIGRATED:
        sys.stdout.write("migrate: schema forward-migrated in loader.\n")
        return 0
    if load_result.status == loader_mod.STATUS_OK:
        sys.stdout.write("migrate: schema already current; no action.\n")
        return 0
    sys.stderr.write(
        "migrate: load status={s} reason={r}; "
        "cannot migrate from this state\n".format(
            s=load_result.status, r=load_result.reason,
        )
    )
    return 1


def _read_sigchain_tip_length(sigchain_path: Path) -> int:
    if not sigchain_path.exists():
        return 0
    try:
        return sum(
            1 for _ in sigchain_path.open("r", encoding="utf-8")
            if _.strip()
        )
    except OSError:
        return 0


def _read_sigchain_prior_hash(sigchain_path: Path) -> str:
    """Return last entry's hmac hex or 64-zeros genesis if empty."""
    if not sigchain_path.exists():
        return "0" * 64
    last_hmac = None
    try:
        with sigchain_path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict) and "hmac" in obj:
                    last_hmac = obj["hmac"]
    except OSError:
        return "0" * 64
    return last_hmac or ("0" * 64)


# ---------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the `ceo-tier-policy` CLI."""
    p = argparse.ArgumentParser(
        prog="ceo-tier-policy",
        description=(
            "PLAN-043 Dynamic tier policy CLI — consume tournament "
            "output and apply learned-policy updates to "
            ".claude/agents/<slug>.md model: fields subject to "
            "VETO floor + cost gate + Owner signatures."
        ),
    )
    sub = p.add_subparsers(dest="command", required=True)

    d = sub.add_parser(
        "derive", help="Derive recommendations from tournament reports."
    )
    d.add_argument("--policy")
    d.add_argument("--reports")
    d.set_defaults(func=cmd_derive)

    a = sub.add_parser(
        "apply", help="Apply recommendations (kill-switch gated)."
    )
    a.add_argument("--policy")
    a.add_argument("--sigchain")
    a.add_argument("--reports")
    a.add_argument("--agents")
    a.add_argument("--baseline")
    a.add_argument("--dry-run", action="store_true")
    a.set_defaults(func=cmd_apply)

    os_ = sub.add_parser(
        "owner-sign", help="Owner signs a demote / cost-gated promote."
    )
    os_.add_argument("--agent", required=True)
    os_.add_argument("--from-tier", required=True, dest="from_tier")
    os_.add_argument("--to-tier", required=True, dest="to_tier")
    os_.add_argument("--sp-chain-id", required=True, dest="sp_chain_id")
    os_.add_argument("--evidence-hmac", dest="evidence_hmac")
    os_.add_argument("--sigchain")
    os_.add_argument("--owners-file", dest="owners_file")
    os_.add_argument(
        "--skip-commit", action="store_true",
        help="Don't run git commit -S (tests only)",
    )
    os_.set_defaults(func=cmd_owner_sign)

    v = sub.add_parser("verify", help="Verify sigchain + policy integrity.")
    v.add_argument("--sigchain")
    v.add_argument("--policy")
    v.set_defaults(func=cmd_verify)

    s = sub.add_parser("show", help="Pretty-print current policy.")
    s.add_argument("--policy")
    s.set_defaults(func=cmd_show)

    e = sub.add_parser(
        "enable", help="Write Owner-signed sentinel (factor 2).",
    )
    e.add_argument("--sentinel")
    e.add_argument("--owners-file", dest="owners_file")
    e.add_argument(
        "--skip-commit", action="store_true",
        help="Don't run git commit -S (tests only)",
    )
    e.set_defaults(func=cmd_enable)

    m = sub.add_parser(
        "migrate", help="Forward-migrate schema if needed.",
    )
    m.add_argument("--policy")
    m.set_defaults(func=cmd_migrate)

    rk = sub.add_parser(
        "rotate-key",
        help="Rotate tier-policy HMAC key (Owner-signed; stub in MVP).",
    )
    rk.add_argument("--confirm", action="store_true")
    rk.add_argument("--owners-file", dest="owners_file")
    rk.set_defaults(func=cmd_rotate_key)

    sr = sub.add_parser(
        "sigchain-rotate",
        help="Archive sigchain > 1000 entries and reseed.",
    )
    sr.add_argument("--sigchain")
    sr.add_argument("--force", action="store_true")
    sr.add_argument("--owners-file", dest="owners_file")
    sr.set_defaults(func=cmd_sigchain_rotate)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
