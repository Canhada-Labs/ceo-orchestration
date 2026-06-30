"""Deterministic fuzzer for bash-safety byte-identity — PLAN-014 A.5.

Emits ≥500 synthetic Bash tool-call inputs covering the safe-command,
subcommand-chain, rm-with-flags, git destructive/safe, quoted-string,
credential-shaped, and edge-case buckets specified by the A.5 task.

All randomness is seeded (default 42) so the corpus is reproducible.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Token banks
# ---------------------------------------------------------------------------

_SAFE_TEMPLATES = [
    "ls", "ls -la", "ls -la {path}",
    "cat {path}", "cat -n {path}",
    "echo {literal}", "echo \"hello world\"", "printf '%s\\n' {literal}",
    "grep -r {literal} src/", "grep -n {literal} {path}",
    "find {path} -name '*.py'", "wc -l {path}",
    "python3 --version", "git status", "git log --oneline -5",
    "pwd", "whoami", "date",
    "head -n 10 {path}", "tail -n 20 {path}",
    "du -sh {path}", "df -h",
    "ps aux", "env | grep PATH",
    "mkdir -p {path}", "touch {path}",
    "diff {path} {path}", "sort {path}",
    "uniq -c {path}", "awk '{print $1}' {path}",
    "sed -n '1,10p' {path}",
    "tar -tvf archive.tar",
    "curl https://example.com -I",
]
_PATHS = [
    "/tmp/foo", "src/lib/x.py", "README.md", "./config.yaml",
    "~/notes.txt", "../relative/path", "dir/sub/file.txt",
    "a/b/c/d.md", "build/output.log",
]
_LITERALS = [
    "hello", "world", "\"quoted string\"", "'single quoted'",
    "no-hyphen", "$VAR", "with spaces", "UPPER", "mixed-Case-123",
]

_SUBCMD_SEPS = ["&&", "||", ";", "|"]

_RM_PATTERNS = [
    "rm {path}",                       # safe — no -r
    "rm -f {path}",                    # safe — no -r
    "rm -i {path}",                    # safe
    "rm -v {path}",                    # safe
    "rm -rf {path}",                   # DENY
    "rm -fr {path}",                   # DENY
    "rm -r -f {path}",                 # DENY
    "rm -f -r {path}",                 # DENY
    "rm -Rf {path}",                   # DENY
    "rm -rF {path}",                   # DENY (case-insensitive per _check_rm_rf)
    "rm -rfv {path}",                  # DENY
    "rm -R {path}",                    # safe (no -f)
    "rm -r {path}",                    # safe (no -f)
    "rm --force {path}",               # safe (long option; .py ignores long opts)
    "rm --recursive {path}",           # safe (long option)
    "rm --recursive --force {path}",   # safe per current impl
    "rm -- {path}",                    # safe
    "rm -f --verbose {path}",          # safe
]

_GIT_PATTERNS = [
    "git reset --hard",                       # DENY
    "git reset --hard HEAD~1",                # DENY
    "git reset --hard origin/main",           # DENY
    "git reset --soft HEAD~1",                # safe
    "git reset HEAD",                         # safe
    "git reset --mixed",                      # safe
    "git reset --hard {sha}",                 # DENY
    "git push --force",                       # DENY
    "git push -f",                            # DENY
    "git push origin main --force",           # DENY
    "git push -f origin feature",             # DENY
    "git push --force-with-lease",            # safe
    "git push --force-with-lease origin main",# safe
    "git push origin main",                   # safe
    "git push",                               # safe (insufficient tokens)
    "git push --tags",                        # safe
    "git status",                             # safe
    "git log --oneline",                      # safe
    "git diff HEAD",                          # safe
    "git stash",                              # safe
]

_QUOTED_SAFE = [
    'echo "rm -rf /tmp/foo"',                 # ALLOW (echo is first token)
    "echo 'git reset --hard'",                 # ALLOW
    'grep "git push --force" Makefile',        # ALLOW (grep is first token)
    'printf "%s" "rm -rf"',                   # ALLOW
    'cat <<EOF\nrm -rf\nEOF',                 # ALLOW (shlex heredoc odd — may fail tokenize)
    'echo "\\"nested quotes rm -rf\\""',      # ALLOW (nested escapes)
]

# Credential-shaped — EXACTLY the shapes the `.py` credential detector recognizes
# when is_likely_real_key returns True. We plant clearly-synthetic shapes
# (anthropic/openai/google/aws prefixes with long tails).
_CRED_POSITIVE = [
    # Strictly: the detector checks entropy + known-prefix patterns.
    # We generate synthetic-BUT-detector-valid strings. These may or may not
    # trip detect_keys on all hardware; harness allows for that.
    "export ANTHROPIC_API_KEY=sk-ant-api03-{entropy1}-{entropy2}",
    "curl -H \"x-api-key: sk-ant-api03-{entropy1}\"",
    "OPENAI_API_KEY=sk-proj-{entropy1}{entropy2}",
    "export GOOGLE_API_KEY=AIza{entropy1}{entropy2}",
    "aws configure set aws_access_key_id AKIA{entropy1}",
]
_CRED_NEGATIVE = [
    "echo $SECRET",                                    # no literal key
    "export FOO=bar",
    "export ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}",  # env ref
    "curl -H \"x-api-key: $KEY\" https://x.com",      # env ref
    "echo 'sk-ant-api03-FAKE-NOT-REAL-SHORT'",        # too short / low entropy
    "grep sk-ant- config.yaml",                        # search, not use
]


def _mk_entropy(rng: random.Random, n: int) -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(rng.choice(alphabet) for _ in range(n))


def _pick(rng: random.Random, items: List[str]) -> str:
    return items[rng.randrange(len(items))]


def _render(rng: random.Random, template: str) -> str:
    out = template
    for _ in range(4):  # up to 4 substitutions
        if "{path}" in out:
            out = out.replace("{path}", _pick(rng, _PATHS), 1)
        if "{literal}" in out:
            out = out.replace("{literal}", _pick(rng, _LITERALS), 1)
        if "{sha}" in out:
            out = out.replace("{sha}", _mk_entropy(rng, 7), 1)
        if "{entropy1}" in out:
            out = out.replace("{entropy1}", _mk_entropy(rng, 24), 1)
        if "{entropy2}" in out:
            out = out.replace("{entropy2}", _mk_entropy(rng, 16), 1)
    return out


def _mk_chain(rng: random.Random, parts: List[str]) -> str:
    out = parts[0]
    for p in parts[1:]:
        sep = _pick(rng, _SUBCMD_SEPS)
        out = f"{out} {sep} {p}"
    return out


# ---------------------------------------------------------------------------
# Buckets
# ---------------------------------------------------------------------------


def _bucket_safe_simple(rng: random.Random, count: int) -> List[str]:
    out = []
    for _ in range(count):
        out.append(_render(rng, _pick(rng, _SAFE_TEMPLATES)))
    return out


def _bucket_subcommand_chains(rng: random.Random, count: int) -> List[str]:
    out = []
    for _ in range(count):
        n = rng.randint(2, 4)
        parts = [_render(rng, _pick(rng, _SAFE_TEMPLATES)) for _ in range(n)]
        out.append(_mk_chain(rng, parts))
    return out


def _bucket_rm_flags(rng: random.Random, count: int) -> List[str]:
    out = []
    for _ in range(count):
        out.append(_render(rng, _pick(rng, _RM_PATTERNS)))
    return out


def _bucket_git(rng: random.Random, count: int) -> List[str]:
    out = []
    for _ in range(count):
        out.append(_render(rng, _pick(rng, _GIT_PATTERNS)))
    return out


def _bucket_quoted_safe(rng: random.Random, count: int) -> List[str]:
    out = []
    for _ in range(count):
        out.append(_pick(rng, _QUOTED_SAFE))
    return out


def _bucket_credential_positive(rng: random.Random, count: int) -> List[str]:
    out = []
    for _ in range(count):
        out.append(_render(rng, _pick(rng, _CRED_POSITIVE)))
    return out


def _bucket_credential_negative(rng: random.Random, count: int) -> List[str]:
    out = []
    for _ in range(count):
        out.append(_pick(rng, _CRED_NEGATIVE))
    return out


def _bucket_edge(rng: random.Random, count: int) -> List[str]:
    out: List[str] = []
    edges = [
        "",
        "   ",
        "\t\n",
        "x",
        "ls\n\n",
        "echo  Hello  World",
        # UTF-8 multi-byte
        "echo café", "cat páginas.md", "grep naïve x",
        "echo 日本語",
        # 1000-char echo
        "echo " + ("a" * 1000),
        # Command with semicolons inside quoted args
        'echo "a; b; c"',
        'echo "x && y || z"',
        # Pipeline with long tails
        "ls -la | wc -l",
        "grep foo * | head -n 5",
        # sequences of separators
        "ls ; ;",
        "echo a && ; b",
    ]
    for _ in range(count):
        out.append(_pick(rng, edges))
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate(n: int = 500, seed: int = 42) -> List[Dict[str, Any]]:
    """Return ``n`` bash-command tool-call events (deterministic for seed).

    Distribution (for default n=500):
        safe_simple            100
        subcommand_chains       75
        rm_flags                80
        git                     80
        quoted_safe             50
        credential_positive     25
        credential_negative     25
        edge                    65
                               ----
                               500
    """
    rng = random.Random(seed)
    buckets = [
        _bucket_safe_simple(rng, 100),
        _bucket_subcommand_chains(rng, 75),
        _bucket_rm_flags(rng, 80),
        _bucket_git(rng, 80),
        _bucket_quoted_safe(rng, 50),
        _bucket_credential_positive(rng, 25),
        _bucket_credential_negative(rng, 25),
        _bucket_edge(rng, 65),
    ]
    flat: List[str] = []
    for b in buckets:
        flat.extend(b)
    # If n > 500 requested, pad via repeated draws from the combined bank
    # (reproducible per-seed).
    while len(flat) < n:
        flat.append(_render(rng, _pick(rng, _SAFE_TEMPLATES)))
    flat = flat[:n]
    # Wrap as tool-call events
    return [{"tool": "Bash", "tool_input": {"command": cmd}} for cmd in flat]


__all__ = ["generate"]
