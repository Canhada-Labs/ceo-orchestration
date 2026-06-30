#!/usr/bin/env python3
"""PLAN-128 Wave-1 #2 — rule-based risk/cost router ($0, deterministic).

Classifies a change (path + optional diff) into a risk TIER, which drives:
  * which QUALITY gate fires (trivial → none; medium → verify; risky → verify + cross-model Codex review),
  * a recommended EFFORT/model (cheap-first; escalate only where it matters — "economizar pela inteligência").

This is the cost-via-intelligence lever: most edits are trivial/medium and stay on the cheap path; only the
risky ones (auth, money, migrations, crypto, big diffs) pull the expensive Codex review / strong model. It is
ADVISORY logic consumed by other Wave-1 pieces (#3 Codex-review gate, #5 adequacy gate) and surfaced as a
hint; it does not itself change the model (Claude Code can't swap the main model mid-turn) — the model/effort
DEFAULTS are set once in settings (see SETTINGS_DELTA below, applied at the wiring ceremony).

Stdlib only, Python >= 3.9.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

# Settings the wiring ceremony applies (documented here; NOT auto-written — kernel-guarded):
SETTINGS_DELTA = {
    "env": {
        "CLAUDE_CODE_SUBAGENT_MODEL": "inherit",  # normal resolution — per-agent model: frontmatter governs
    },
    "_doctrine": "Main coding: Opus (or opusplan). Subagents: per-agent `model:` frontmatter governs "
                 "(code-review/security=opus, qa/perf=sonnet, devops=haiku) — NEVER a global "
                 "CLAUDE_CODE_SUBAGENT_MODEL override (it is documented to beat explicit model:). "
                 "Effort: high for coding, low for classification. Caching: stable prefix; 1h TTL.",
}

LARGE_DIFF_LINES = 80

_RISKY_PATH = re.compile(
    r"auth|login|signup|logout|token|secret|passwo?rd|credential|crypto|encrypt|decrypt|"
    r"payment|billing|invoice|charge|refund|payout|money|balance|ledger|wallet|tax|"
    r"migrat|schema|\.sql$|rbac|acl|permission|authz|authoriz|session|webhook|api[_-]?key|"
    r"oauth|jwt|signature|hmac|nonce|\.env|security", re.IGNORECASE)
_RISKY_CONTENT = re.compile(
    r"\b(eval|exec|os\.system|subprocess|pickle\.loads|yaml\.load|md5|sha1|verify\s*=\s*False|"
    r"DELETE\s+FROM|DROP\s+TABLE|TRUNCATE|GRANT\s+ALL|ALTER\s+TABLE|chmod|chown|sudo|"
    r"private_key|BEGIN\s+RSA|--dangerously|rm\s+-rf)\b", re.IGNORECASE)
_TRIVIAL_PATH = re.compile(
    r"\.(md|txt|rst|json|ya?ml|toml|lock|cfg|ini|csv|svg|png|jpg|gitignore)$|"
    r"(^|/)(README|CHANGELOG|LICENSE|CONTRIBUTING)|(^|/)docs?/", re.IGNORECASE)
_TEST_PATH = re.compile(
    r"(^|/)(tests?|__tests__|spec|e2e)/|\.(test|spec)\.[a-z]+$|(^|/)test_[^/]+\.py$|[^/]+_test\.(py|go)$",
    re.IGNORECASE)

# Tiers, cheapest → most expensive.
_RECO = {
    "trivial": {"gate": "none",            "effort": "low",  "model": "cheap",  "codex_review": False},
    "medium":  {"gate": "verify",          "effort": "med",  "model": "default", "codex_review": False},
    "risky":   {"gate": "verify+codex",    "effort": "high", "model": "strong", "codex_review": True},
}


def _changed_line_count(diff_text: str) -> int:
    n = 0
    for ln in diff_text.splitlines():
        if (ln.startswith("+") and not ln.startswith("+++")) or (ln.startswith("-") and not ln.startswith("---")):
            n += 1
    return n


def classify(path: str, diff_text: Optional[str] = None) -> Dict:
    """Return {tier, reasons, recommend}. Risk dominates triviality (a risky-named doc is still risky)."""
    reasons: List[str] = []
    risky = False
    if _RISKY_PATH.search(path or ""):
        risky = True; reasons.append("path matches a sensitive area (auth/money/migration/crypto/…)")
    if diff_text:
        if _RISKY_CONTENT.search(diff_text):
            risky = True; reasons.append("diff contains a high-risk construct (exec/SQL-DDL/secret/…)")
        lc = _changed_line_count(diff_text)
        if lc > LARGE_DIFF_LINES:
            risky = True; reasons.append("large diff (%d changed lines > %d)" % (lc, LARGE_DIFF_LINES))
    if risky:
        tier = "risky"
    elif _TRIVIAL_PATH.search(path or "") and not _TEST_PATH.search(path or ""):
        tier = "trivial"; reasons.append("docs/config/non-source")
    elif _TEST_PATH.search(path or ""):
        tier = "medium"; reasons.append("test file (correctness-relevant)")
    else:
        tier = "medium"; reasons.append("ordinary source")
    return {"tier": tier, "reasons": reasons, "recommend": _RECO[tier]}


def needs_codex_review(path: str, diff_text: Optional[str] = None) -> bool:
    return classify(path, diff_text)["recommend"]["codex_review"]


def _selftest() -> None:
    assert classify("src/auth/login.py")["tier"] == "risky"
    assert classify("migrations/0007_add_balance.sql")["tier"] == "risky"
    assert classify("src/utils/format.py")["tier"] == "medium"
    assert classify("README.md")["tier"] == "trivial"
    assert classify("docs/guide.md")["tier"] == "trivial"
    assert classify("tests/test_format.py")["tier"] == "medium"
    # risky CONTENT on an innocuous path
    assert classify("src/util.py", "+ os.system(cmd)\n")["tier"] == "risky"
    assert classify("src/db.py", "+ DELETE FROM users WHERE 1=1\n")["tier"] == "risky"
    # large diff → risky
    big = "".join("+ line %d\n" % i for i in range(LARGE_DIFF_LINES + 5))
    assert classify("src/util.py", big)["tier"] == "risky"
    # a risky-named doc is still risky (risk dominates)
    assert classify("docs/auth.md")["tier"] == "risky"
    # codex-review trigger
    assert needs_codex_review("src/payments/charge.py") is True
    assert needs_codex_review("src/util.py") is False
    print("route.py selftest PASS (risky-path / risky-content / large-diff / trivial / test / dominance)")


if __name__ == "__main__":
    _selftest()
