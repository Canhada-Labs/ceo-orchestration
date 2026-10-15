"""Task: fix a SQL-injection-shaped string-format query into a parameterized one.

The verifier cannot run a real DB, so it checks the candidate's
``build_query(user_id)`` returns the SAFE two-tuple ``(sql_with_placeholder,
params)`` rather than an interpolated string — a security-relevant transform we
can verify structurally + deterministically.

PLAN-191 W0-pre: the SQL must keep the query's SHAPE (select ... from users
where ...) and the placeholder must be the value compared to ``id`` — a lone
``'?'`` with the value in params used to score 1.0. Mapping params (named
placeholders such as ``:id``) carry the value in their values.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import clamp_reward, read_text, run_python, _VERIFY_ERROR

_SHAPE = re.compile(r"\bselect\b.+\bfrom\s+users\b.*\bwhere\b", re.I | re.S)
_ID_PLACEHOLDER = re.compile(
    r"\bwhere\s+(?:\w+\.)?id\s*=\s*(?:%s|\?|:[a-z_]\w*|%\([a-z_]\w*\)s|\$\d+)", re.I
)

_VULN = '''\
def build_query(user_id):
    """Return (sql, params) for selecting a user by id, SAFE from SQL injection.
    Use a parameter placeholder; do NOT interpolate user_id into the SQL string.
    """
    # VULNERABLE starting point — interpolates directly.
    sql = "SELECT * FROM users WHERE id = %s" % user_id
    return (sql, ())
'''


def setup(workdir: Path) -> None:
    (workdir / "solution.py").write_text(_VULN, encoding="utf-8")


def verify(workdir: Path) -> float:
    score = 0.0
    got = run_python(workdir, "solution.py", func="build_query", args=("5 OR 1=1",))
    if got is _VERIFY_ERROR or not (isinstance(got, tuple) and len(got) == 2):
        return 0.0
    sql, params = got
    sql = str(sql)
    # 0.5 — still the users-by-id query, without the dangerous user string.
    if "OR 1=1" not in sql and _SHAPE.search(sql):
        score += 0.5
    # 0.3 — the placeholder is the value compared to id.
    if _ID_PLACEHOLDER.search(sql):
        score += 0.3
    # 0.2 — params must carry the value, not the SQL.
    try:
        values = list(params.values()) if isinstance(params, dict) else list(params)
        if "5 OR 1=1" in values:
            score += 0.2
    except Exception:
        pass
    # Guard: if the source still uses `%` / f-string interpolation of user_id, cap.
    src = read_text(workdir, "solution.py")
    if '% user_id' in src or 'f"SELECT' in src or "f'SELECT" in src:
        score = min(score, 0.3)
    return clamp_reward(score)


TASK = {
    "id": "t07-sql-param-fix",
    "title": "Convert interpolated SQL to parameterized query",
    "category": "bugfix",
    "difficulty": "hard",
    "setup": setup,
    "instruction": (
        "build_query(user_id) in solution.py currently interpolates user_id into "
        "the SQL string (SQL-injection risk). Fix it to return "
        "(sql_with_placeholder, params) where the SQL uses a placeholder and the "
        "value travels in params."
    ),
    "verify": verify,
}
