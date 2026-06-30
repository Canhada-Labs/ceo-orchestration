#!/usr/bin/env python3
"""Tests for check-debt-ledger.py (PLAN-139 Wave B).

All trees are built under ``tmp_path`` and the script is driven via the
``--repo`` flag, so ``$HOME`` / ``$CLAUDE_PROJECT_DIR`` are never touched
(satisfies the env-hygiene gate). No ``os.environ`` mutation anywhere.

The marker grammar example string is constructed at runtime from parts so
this test source itself does not contain a line-anchored literal marker
(belt-and-suspenders against accidental self-match if the prune ever
regresses).
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
_SCRIPT_PATH = _SCRIPTS_DIR / "check-debt-ledger.py"

# Build the marker token from parts so this file holds no literal anchored
# marker comment (avoids self-counting if prune logic ever regresses).
_HASH = chr(35)  # "#"
_TOKEN = "CEO" + "-" + "DEBT:"  # the UPPERCASE sentinel, assembled


def _marker(payload: str) -> str:
    """Return a well-formed marker comment line for ``payload``."""
    return "%s %s %s" % (_HASH, _TOKEN, payload)


def _load_module():
    """Import check-debt-ledger.py by file path (hyphenated module name)."""
    spec = importlib.util.spec_from_file_location(
        "check_debt_ledger", str(_SCRIPT_PATH)
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write(root: Path, rel: str, body: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# grammar parse
# ---------------------------------------------------------------------------
def test_two_well_formed_markers_parse_zero_ungoverned(tmp_path: Path) -> None:
    mod = _load_module()
    body = "\n".join(
        [
            "def alpha():",
            "    " + _marker("max 200 lines, when this module exceeds 400 LOC"),
            "    return 1",
            "",
            "def beta():",
            "    " + _marker("inline cache, when hit-rate drops below 0.8"),
            "    return 2",
            "",
        ]
    )
    _write(tmp_path, "src/mod.py", body)
    ledger = mod.build_ledger(tmp_path)
    assert ledger["markers_count"] == 2
    assert ledger["ungoverned_count"] == 0
    assert all(m["governed"] for m in ledger["markers"])
    # Both ceilings + triggers parsed.
    triggers = sorted(m["trigger"] for m in ledger["markers"])
    assert triggers == [
        "when hit-rate drops below 0.8",
        "when this module exceeds 400 LOC",
    ]


# ---------------------------------------------------------------------------
# trigger-less detection
# ---------------------------------------------------------------------------
def test_marker_without_trigger_is_flagged_ungoverned(tmp_path: Path) -> None:
    mod = _load_module()
    body = "\n".join(
        [
            "def gamma():",
            "    " + _marker("cap only"),  # no comma -> ungoverned
            "    return 3",
            "",
        ]
    )
    _write(tmp_path, "pkg/g.py", body)
    ledger = mod.build_ledger(tmp_path)
    assert ledger["markers_count"] == 1
    assert ledger["ungoverned_count"] == 1
    m = ledger["markers"][0]
    assert m["governed"] is False
    assert m["ceiling"] == "cap only"
    assert m["trigger"] == ""


def test_marker_with_empty_trigger_field_is_ungoverned(tmp_path: Path) -> None:
    mod = _load_module()
    # A trailing comma with an empty second field is still ungoverned.
    _write(tmp_path, "e.py", _marker("ceiling here,   ") + "\n")
    ledger = mod.build_ledger(tmp_path)
    assert ledger["markers_count"] == 1
    assert ledger["ungoverned_count"] == 1
    assert ledger["markers"][0]["governed"] is False


# ---------------------------------------------------------------------------
# empty tree
# ---------------------------------------------------------------------------
def test_empty_tree_zero_markers_clean_footer(tmp_path: Path) -> None:
    mod = _load_module()
    _write(tmp_path, "plain.py", "x = 1\n# an ordinary comment\n")
    ledger = mod.build_ledger(tmp_path)
    assert ledger["markers_count"] == 0
    assert ledger["ungoverned_count"] == 0


def test_empty_tree_cli_exit_zero_and_footer(tmp_path: Path) -> None:
    _write(tmp_path, "plain.py", "x = 1\n")
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT_PATH), "--repo", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "0 markers, 0 ungoverned" in proc.stdout


# ---------------------------------------------------------------------------
# prose regression — the WORD ceo-debt in prose is NOT a marker
# ---------------------------------------------------------------------------
def test_prose_mention_is_not_counted(tmp_path: Path) -> None:
    mod = _load_module()
    # All of these mention the word but are NOT a line-anchored marker:
    #  - lowercase token
    #  - the word inside prose, mid-line
    #  - uppercase token but not at a comment line-start
    prose = "\n".join(
        [
            "# we track ceo-debt informally in this module",
            "We discussed CEO-DEBT policy in the meeting.",
            "x = 1  " + _HASH + " trailing CEO-DEBT: not at line start",
            "lower = '" + _HASH + " ceo-debt: lowercase does not match'",
            # Markdown heading form (two hashes) is NOT a code-comment marker.
            _HASH + _HASH + " " + _TOKEN + " heading form, not a marker",
            "",
        ]
    )
    _write(tmp_path, "doc.md", prose)
    ledger = mod.build_ledger(tmp_path)
    assert ledger["markers_count"] == 0, ledger["markers"]
    assert ledger["ungoverned_count"] == 0


# ---------------------------------------------------------------------------
# self-non-match — scanning the live repo never counts the script own examples
# ---------------------------------------------------------------------------
def test_self_non_match_against_live_repo() -> None:
    mod = _load_module()
    repo_root = _SCRIPTS_DIR.parent.parent  # .../ceo-orchestration
    ledger = mod.build_ledger(repo_root)
    # The script docstring, this test file, AND the grammar reference doc
    # all contain grammar examples; NONE must ever be counted. We assert the
    # self-non-match invariant directly (self paths absent) rather than the
    # whole-repo total — the total is allowed to grow once the grammar is
    # legitimately used in real source (Codex pair-rail P2).
    paths = [m["path"] for m in ledger["markers"]]
    assert "check-debt-ledger.py" not in " ".join(paths), paths
    assert not any("test_check_debt_ledger" in p for p in paths), paths
    assert not any("ceo-debt-grammar" in p for p in paths), paths


# ---------------------------------------------------------------------------
# self-non-match across trees — a COPY of the scanner under --repo (a second
# checkout / install target) must not be counted (Codex pair-rail P2).
# ---------------------------------------------------------------------------
def test_repo_local_copy_of_scanner_not_counted(tmp_path: Path) -> None:
    import shutil
    dest = tmp_path / ".claude" / "scripts"
    dest.mkdir(parents=True, exist_ok=True)
    # Copy the real scanner (its docstring carries a line-anchored grammar
    # example) into an otherwise-empty target tree, then scan that tree.
    shutil.copy(str(_SCRIPT_PATH), str(dest / "check-debt-ledger.py"))
    mod = _load_module()
    ledger = mod.build_ledger(tmp_path)
    assert ledger["markers_count"] == 0, [m["path"] for m in ledger["markers"]]


# ---------------------------------------------------------------------------
# prune set — vendored dirs are skipped
# ---------------------------------------------------------------------------
def test_pruned_dirs_are_skipped(tmp_path: Path) -> None:
    mod = _load_module()
    # A marker inside node_modules / npm / dist must NOT be counted.
    _write(tmp_path, "node_modules/pkg/x.js", _marker("vendored, never ours") + "\n")
    _write(tmp_path, "npm/.claude/y.py", _marker("bundled copy, drift") + "\n")
    _write(tmp_path, "dist/z.py", _marker("built artifact, regenerate") + "\n")
    # ... but a marker in real source IS counted.
    _write(tmp_path, "real/a.py", _marker("real, when X happens") + "\n")
    ledger = mod.build_ledger(tmp_path)
    assert ledger["markers_count"] == 1, [m["path"] for m in ledger["markers"]]
    assert ledger["markers"][0]["path"] == "real/a.py"


def test_own_tests_fixtures_dir_pruned(tmp_path: Path) -> None:
    mod = _load_module()
    # A marker placed under the script own tests/ tree of a synthetic repo
    # must be pruned (self-fixture exclusion).
    _write(
        tmp_path,
        ".claude/scripts/tests/fixtures/example.py",
        _marker("fixture example, illustrative only") + "\n",
    )
    _write(tmp_path, ".claude/scripts/real_tool.py", _marker("real, when Y") + "\n")
    ledger = mod.build_ledger(tmp_path)
    paths = [m["path"] for m in ledger["markers"]]
    assert not any("tests/" in p for p in paths), paths
    assert ledger["markers_count"] == 1, paths
