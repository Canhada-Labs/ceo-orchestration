#!/usr/bin/env python3
"""approval_gate.py — compute an approval decision BY CODE from typed evidence (PLAN-190 W3).

Why
---
A consumer's pipeline declared three slices "green" while the cross-model
reviewer had scored them below the bar, because the script only looked at
P0/P1 findings; a severity written in prose ("alta, mas aceitável") fabricated
a wrong verdict; nine false "proofs incomplete" came from comparing function
names with file paths. The order (2026-09-17) requires: "O estado de aprovação
deve ser calculado por código conforme a política vigente, incluindo nota
mínima, severidades impeditivas e cobertura da versão final. Resposta ausente,
ambígua ou inválida não pode virar verde."

Contract
--------
``decide(policy, evidence)`` returns ``{"decision": "APPROVED"|"REJECTED",
"reasons": [...]}``. It is APPROVED only when EVERY rule passes; anything
missing, ambiguous (a severity outside the closed enum, a score that is not
a number), or inconsistent (review of a revision that is not the final one,
a failing gate command) is REJECTED with the rule named. There is no third
state and no default-green path.

Policy (JSON, closed schema ``ceo.approval-policy/v1``)::

    {"schema": "ceo.approval-policy/v1",
     "score": {"min": 7, "max": 10},
     "severities": {"enum": ["P0", "P1", "P2"], "blocking": ["P0"], "max_open": {"P1": 0}},
     "require_reviewed_equals_final": true,
     "require_gate_green": true,
     "require_review_ran": true}

Evidence (JSON, ``ceo.approval-evidence/v1``)::

    {"schema": "ceo.approval-evidence/v1",
     "final_rev": "<git sha of the bytes being approved>",
     "review": {"ran": true, "reviewed_rev": "<sha the reviewer saw>", "score": 8,
                "findings": [{"severity": "P1", "where": "file:line", "text": "..."}]},
     "gate": [{"cmd": "pytest ...", "rc": 0, "failed": 0}]}

CLI::

    approval_gate.py decide --policy policy.json --evidence evidence.json [--json]
      rc 0 APPROVED · rc 3 REJECTED · rc 2 unreadable input (also a rejection)

Stdlib only, Python >= 3.9. Pure: no I/O besides the two files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

POLICY_SCHEMA = "ceo.approval-policy/v1"
EVIDENCE_SCHEMA = "ceo.approval-evidence/v1"


def _sha(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def _is_int_like(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _number(v: Any) -> Optional[float]:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().replace(",", ".")
        # accept "8/10" and "8" — nothing else; prose is ambiguous by definition
        if "/" in s:
            a, b = s.split("/", 1)
            try:
                num, den = float(a), float(b)
            except ValueError:
                return None
            return num if den == 0 else num  # the denominator is validated against policy.max by the caller
        try:
            return float(s)
        except ValueError:
            return None
    return None


def validate_policy(policy: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    if policy.get("schema") != POLICY_SCHEMA:
        errs.append("policy.schema must be %s" % POLICY_SCHEMA)
    sc = policy.get("score")
    if not isinstance(sc, dict) or not _is_int_like(sc.get("min")) or not _is_int_like(sc.get("max")) or sc["min"] > sc["max"]:
        errs.append("policy.score must be {min:int, max:int} with min <= max")
    sv = policy.get("severities")
    if not isinstance(sv, dict) or not isinstance(sv.get("enum"), list) or not sv["enum"] or not all(isinstance(x, str) for x in sv["enum"]):
        errs.append("policy.severities.enum must be a non-empty list of strings")
    else:
        enum = set(sv["enum"])
        blocking = sv.get("blocking", [])
        if not isinstance(blocking, list) or not set(blocking) <= enum:
            errs.append("policy.severities.blocking must be a subset of enum")
        max_open = sv.get("max_open", {})
        if not isinstance(max_open, dict) or not set(max_open) <= enum or not all(_is_int_like(v) and v >= 0 for v in max_open.values()):
            errs.append("policy.severities.max_open must map enum members to non-negative ints")
    for flag in ("require_reviewed_equals_final", "require_gate_green", "require_review_ran"):
        if not isinstance(policy.get(flag), bool):
            errs.append("policy.%s must be a boolean" % flag)
    return errs


def decide(policy: Dict[str, Any], evidence: Dict[str, Any]) -> Dict[str, Any]:
    reasons: List[str] = []
    perr = validate_policy(policy)
    if perr:
        return {"decision": "REJECTED", "reasons": ["invalid policy: " + e for e in perr], "policy_sha256": _sha(policy), "evidence_sha256": _sha(evidence)}
    if evidence.get("schema") != EVIDENCE_SCHEMA:
        reasons.append("evidence.schema must be %s" % EVIDENCE_SCHEMA)

    final_rev = evidence.get("final_rev")
    if not isinstance(final_rev, str) or not final_rev.strip():
        reasons.append("evidence.final_rev missing")

    review = evidence.get("review")
    if not isinstance(review, dict):
        reasons.append("evidence.review missing")
        review = {}

    if policy["require_review_ran"] and review.get("ran") is not True:
        reasons.append("review did not run (review.ran != true)")

    # score: numeric, on the policy scale, at or above the minimum
    smin, smax = policy["score"]["min"], policy["score"]["max"]
    raw_score = review.get("score")
    score = _number(raw_score)
    if score is None:
        reasons.append("review.score missing or not numeric (%r)" % (raw_score,))
    else:
        if isinstance(raw_score, str) and "/" in raw_score:
            try:
                den = float(raw_score.split("/", 1)[1])
                if den != smax:
                    reasons.append("review.score denominator %s != policy scale %d" % (den, smax))
            except ValueError:
                reasons.append("review.score malformed (%r)" % (raw_score,))
        if score < smin:
            reasons.append("review.score %s below minimum %d" % (score, smin))
        if score > smax:
            reasons.append("review.score %s above scale %d (ambiguous)" % (score, smax))

    # findings: closed enum, blocking severities, per-severity caps
    enum = policy["severities"]["enum"]
    blocking = set(policy["severities"].get("blocking", []))
    max_open = policy["severities"].get("max_open", {})
    findings = review.get("findings")
    if findings is None:
        reasons.append("review.findings missing (an empty list is required to mean 'none')")
        findings = []
    elif not isinstance(findings, list):
        reasons.append("review.findings must be a list")
        findings = []
    counts: Dict[str, int] = {}
    for i, f in enumerate(findings):
        sev = f.get("severity") if isinstance(f, dict) else None
        if not isinstance(sev, str) or sev not in enum:
            reasons.append("finding[%d].severity %r not in enum %s (ambiguous)" % (i, sev, enum))
            continue
        counts[sev] = counts.get(sev, 0) + 1
        if sev in blocking:
            reasons.append("finding[%d] has blocking severity %s: %s" % (i, sev, str(f.get("where", ""))[:80]))
    for sev, cap in max_open.items():
        if counts.get(sev, 0) > cap:
            reasons.append("%d finding(s) of severity %s exceed max_open %d" % (counts[sev], sev, cap))

    # coverage of the final revision
    if policy["require_reviewed_equals_final"]:
        rr = review.get("reviewed_rev")
        if not isinstance(rr, str) or not rr.strip():
            reasons.append("review.reviewed_rev missing")
        elif isinstance(final_rev, str) and rr.strip() != final_rev.strip():
            reasons.append("review covered %s but the final revision is %s" % (rr[:12], final_rev[:12]))

    # gate
    if policy["require_gate_green"]:
        gate = evidence.get("gate")
        if not isinstance(gate, list) or not gate:
            reasons.append("evidence.gate missing or empty")
        else:
            for i, g in enumerate(gate):
                if not isinstance(g, dict):
                    reasons.append("gate[%d] not an object" % i)
                    continue
                rc = g.get("rc")
                failed = g.get("failed")
                if not _is_int_like(rc):
                    reasons.append("gate[%d].rc missing or not int" % i)
                elif rc != 0:
                    reasons.append("gate[%d] rc=%d (%s)" % (i, rc, str(g.get("cmd", ""))[:60]))
                if failed is not None and (not _is_int_like(failed) or failed > 0):
                    reasons.append("gate[%d] failed=%r (%s)" % (i, failed, str(g.get("cmd", ""))[:60]))

    return {
        "decision": "APPROVED" if not reasons else "REJECTED",
        "reasons": reasons,
        "policy_sha256": _sha(policy),
        "evidence_sha256": _sha(evidence),
    }


def _load(path: str) -> Any:
    with open(Path(path).expanduser(), encoding="utf-8") as fh:
        return json.load(fh)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("decide")
    p.add_argument("--policy", required=True)
    p.add_argument("--evidence", required=True)
    p.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        policy = _load(args.policy)
        evidence = _load(args.evidence)
    except (OSError, ValueError) as exc:
        out = {"decision": "REJECTED", "reasons": ["unreadable input: %s" % exc]}
        print(json.dumps(out, ensure_ascii=False) if args.json else "REJECTED: unreadable input: %s" % exc)
        return 2
    if not isinstance(policy, dict) or not isinstance(evidence, dict):
        print("REJECTED: policy and evidence must be JSON objects")
        return 2
    out = decide(policy, evidence)
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        print(out["decision"])
        for r in out["reasons"]:
            print("  - " + r)
    return 0 if out["decision"] == "APPROVED" else 3


if __name__ == "__main__":
    sys.exit(main())
