"""Task: fix a SQL-injection-shaped string-format query into a parameterized one.

The verifier cannot run a real DB, so it checks the candidate's
``build_query(user_id)`` returns the SAFE two-tuple ``(sql_with_placeholder,
params)`` rather than an interpolated string — a security-relevant transform we
can verify structurally + deterministically.
"""

from __future__ import annotations

from pathlib import Path

from . import clamp_reward, read_text, run_python, _VERIFY_ERROR

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
    # 0.5 — the dangerous user string must NOT appear in the SQL text.
    if "5 OR 1=1" not in sql and "OR 1=1" not in sql:
        score += 0.5
    # 0.3 — a placeholder must be present.
    if "%s" in sql or "?" in sql or ":" in sql:
        score += 0.3
    # 0.2 — params must carry the value, not the SQL.
    try:
        if "5 OR 1=1" in tuple(params) or "5 OR 1=1" in list(params):
            score += 0.2
    except TypeError:
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
