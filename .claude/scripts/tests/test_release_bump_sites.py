#!/usr/bin/env python3
"""PLAN-166 W0 / F2 + F6 — the release driver, its site table and its tag guards.

What is being pinned here, and why each pin exists:

* **AC-1 (F2).** `bump --stable` on a tree already at the target must write
  NOTHING. Not "must not commit" — must not WRITE. The old behaviour re-dated
  four `last-reviewed:` stamps with `date.today()`, so on D+1 of the ADR-103
  hold the phase dirtied the tree, committed AFTER the preflight had proved CI
  green for a different SHA, and `tag()` signed that commit. `--today` is
  passed EXPLICITLY as D and D+1 at both layers (module and driver), because a
  test that lets the code pick the date cannot see the bug.
* The escape hatch for a real re-review (`--restamp`) must survive the fast
  path, and must refuse to move a review stamp without the review ack.
* The `--dry-run` restore list must be DERIVED from the site table. The
  regression is concrete and has happened (S273): the writer grows a site, the
  hand-kept restore list does not, and the dry-run leaves debris. It is proven
  by GROWING the table in the fixture repo and checking the dry-run still
  restores cleanly.
* The tag guards must run for RC **and** stable, and must distinguish "could
  not talk to origin" from "HEAD is not on main" — a single merged message
  would let an offline operator read a network error as a governance verdict.

Every fixture repo is a throwaway git repo under pytest's tmp_path with its
own HOME/GNUPGHOME in the SUBPROCESS environment only; `os.environ` of the
test process is never mutated and the real repo is never touched.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
LOCAL = REPO_ROOT / ".claude" / "scripts" / "local"
DRIVER_SRC = LOCAL / "release.sh"
SITES_SRC = LOCAL / "_release_bump_sites.py"
GUARD_SRC = LOCAL / "_release_tag_guard.py"
VALIDATOR_SRC = REPO_ROOT / ".github" / "scripts" / "validate-pair-rail-verdict.py"
GOVERNANCE = REPO_ROOT / ".claude" / "governance"

D0 = "2026-08-04"
D1 = "2026-08-05"  # D+1 — the ADR-103 hold guarantees this scenario
D2 = "2026-08-06"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    assert spec and spec.loader, path
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bump_sites = _load(SITES_SRC, "_release_bump_sites_under_test")
tag_guard = _load(GUARD_SRC, "_release_tag_guard_under_test")
validator = _load(
    VALIDATOR_SRC, "_validate_pair_rail_verdict_under_test"
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _env(home: Path) -> Dict[str, str]:
    """A subprocess environment that cannot reach the real HOME or repo."""
    env = dict(os.environ)
    for key in ("CLAUDE_PROJECT_DIR", "GIT_DIR", "GIT_WORK_TREE"):
        env.pop(key, None)
    env.update(
        {
            "HOME": str(home),
            "GNUPGHOME": str(home / "gnupg"),
            "GIT_CONFIG_GLOBAL": str(home / "gitconfig"),
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_AUTHOR_NAME": "Release Test",
            "GIT_AUTHOR_EMAIL": "release-test@example.invalid",
            "GIT_COMMITTER_NAME": "Release Test",
            "GIT_COMMITTER_EMAIL": "release-test@example.invalid",
            "LC_ALL": "C",
        }
    )
    return env


def run(args: Sequence[str], cwd: Path, env: Dict[str, str]):
    return subprocess.run(
        list(args),
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )


def git(repo: Path, env: Dict[str, str], *args: str) -> str:
    proc = run(["git"] + list(args), repo, env)
    assert proc.returncode == 0, "git %s failed: %s%s" % (
        " ".join(args),
        proc.stdout,
        proc.stderr,
    )
    return proc.stdout.strip()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_fingerprint(repo: Path) -> Dict[str, str]:
    """Content hash of every file the bump may touch (writes are visible here
    even when they are later committed, unlike `git status`)."""
    out: Dict[str, str] = {}
    for rel in bump_sites.site_paths(include_generated=True):
        full = repo / rel
        if full.is_file():
            out[rel] = sha256_file(full)
    return out


def index_and_worktree_clean(repo: Path, env: Dict[str, str]) -> None:
    porcelain = git(repo, env, "status", "--porcelain")
    assert porcelain == "", "working tree not clean:\n%s" % porcelain
    staged = run(["git", "diff", "--cached", "--quiet"], repo, env)
    assert staged.returncode == 0, "index not clean:\n%s" % git(
        repo, env, "diff", "--cached", "--name-only"
    )


# --- fixture repo -----------------------------------------------------------
STUB_VERIFY_COUNTS = """#!/usr/bin/env bash
# Fixture stand-in for verify-counts.sh: version equality across the watched
# doc/package sites. Deliberately simple — the real oracle is exercised by the
# real repo, this one only has to be RIGHT about same-tree vs drifted-tree.
#
# It DOES model the support-window family (VERSION_SITES modes "minor" and
# "prev_minor" on SECURITY.md/VERSIONING.md, added S293): the re-pass F-sites
# finding was a fixture oracle WITHOUT these modes staying green over a writer
# that never wrote them — the exact fixture!=live class. Derivation mirrors
# the live oracle: prev = minor-1, empty (value-check skipped) at X.0.
set -eu
version="$(tr -d ' \\n' < VERSION)"
minor="${version%.*}"
maj="${minor%%.*}"
min="${minor##*.}"
prev=""
if [ "$min" -gt 0 ]; then prev="${maj}.$((min - 1))"; fi
rc=0
for f in npm/package.json pyproject.toml INSTALL.md docs/ARCHITECTURE.md npm/README.md; do
  [ -f "$f" ] || continue
  if ! grep -q "$version" "$f"; then rc=1; fi
done
# repass-r2 part-d P2: the marker is a bump site (W2.6) — a fixture oracle
# that ignores it stays green over a writer that skipped it (fixture!=live).
if [ -f .claude/.framework-version ]; then
  marker="$(tr -d ' \\n' < .claude/.framework-version)"
  [ "$marker" = "$version" ] || rc=1
fi
for f in SECURITY.md VERSIONING.md; do
  [ -f "$f" ] || continue
  cur_line="$(grep 'Current MINOR' "$f" || true)"
  case "$cur_line" in
    "") ;;
    *"v${minor}.x"*) ;;
    *) rc=1 ;;
  esac
  if [ -n "$prev" ]; then
    prev_line="$(grep 'Previous MINOR' "$f" || true)"
    case "$prev_line" in
      "") ;;
      *"v${prev}.x"*) ;;
      *) rc=1 ;;
    esac
  fi
done
exit "$rc"
"""

STUB_BUILD_PLUGIN = '''#!/usr/bin/env python3
import json, os, sys

TARGETS = [".claude-plugin/plugin.json", ".claude-plugin/marketplace.json"]
version = open("VERSION").read().strip()
mode = sys.argv[1] if len(sys.argv) > 1 else "--check"
if mode == "--write-manifests":
    for t in TARGETS:
        os.makedirs(os.path.dirname(t), exist_ok=True)
        with open(t, "w") as fh:
            json.dump({"version": version}, fh, indent=2)
            fh.write("\\n")
    sys.exit(0)
if mode == "--check":
    for t in TARGETS:
        try:
            with open(t) as fh:
                data = json.load(fh)
        except Exception:
            sys.exit(1)
        if data.get("version") != version:
            sys.exit(1)
    sys.exit(0)
sys.exit(2)
'''

STUB_FRESHNESS = '''#!/usr/bin/env python3
"""Fixture stand-in for check-canonical-doc-freshness.py.

Mirrors the property that matters: the gate judges the VERSION on the stamp,
never the date. That is what makes freezing the date safe.
"""
import os, re, sys

version = open("VERSION").read().strip()
bad = []
for path in ("npm/README.md", "SBOM.md", "SECURITY.md", "VERSIONING.md"):
    if not os.path.exists(path):
        continue
    m = re.search(r"last-reviewed: \\d{4}-\\d{2}-\\d{2} v(\\d+\\.\\d+\\.\\d+)",
                  open(path).read())
    if not m or m.group(1) != version:
        bad.append(path)
for path in bad:
    print("  !!  stale stamp: %s" % path)
sys.exit(1 if bad else 0)
'''


def _support_window(version: str):
    """(current_minor, previous_minor) the way the live oracle derives them:
    prev = minor-1, None (not derivable) at X.0."""
    maj, mnr = (int(x) for x in version.split(".")[:2])
    prev = "%d.%d" % (maj, mnr - 1) if mnr > 0 else None
    return "%d.%d" % (maj, mnr), prev


def write_sites(repo: Path, version: str, stamp_date: str) -> None:
    (repo / "npm").mkdir(exist_ok=True)
    (repo / "docs").mkdir(exist_ok=True)
    stamp = "<!-- last-reviewed: %s v%s -->" % (stamp_date, version)
    cur_minor, prev_minor = _support_window(version)
    prev_sec = (
        "- **Previous MINOR** (`v%s.x`) — security-only patches.\n" % prev_minor
        if prev_minor
        else ""
    )
    prev_ver = (
        "| Previous MINOR (`v%s.x`) | Security-only patches |\n" % prev_minor
        if prev_minor
        else ""
    )
    (repo / "VERSION").write_text(version + "\n", encoding="utf-8")
    # repass-r2 part-d P2: the marker site (W2.6) exists in the fixture so
    # the e2e bump exercises the writer AND the stub oracle checks it.
    (repo / ".claude").mkdir(exist_ok=True)
    (repo / ".claude" / ".framework-version").write_text(
        version + "\n", encoding="utf-8"
    )
    (repo / "npm" / "package.json").write_text(
        json.dumps({"name": "fixture", "version": version}, indent=2) + "\n",
        encoding="utf-8",
    )
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "%s"\n' % version, encoding="utf-8"
    )
    (repo / "INSTALL.md").write_text(
        "bash install.sh --pin v%s\n" % version, encoding="utf-8"
    )
    (repo / "docs" / "ARCHITECTURE.md").write_text(
        "The framework is currently v%s, aligned with the repo VERSION.\n" % version,
        encoding="utf-8",
    )
    (repo / "npm" / "README.md").write_text(
        "# fixture\n\n%s\n" % stamp, encoding="utf-8"
    )
    (repo / "README.md").write_text("VERSION=%s\n" % version, encoding="utf-8")
    (repo / "SBOM.md").write_text(
        "%s\n\n**Version:** `%s` (tracks repo-root VERSION)\n" % (stamp, version),
        encoding="utf-8",
    )
    (repo / "SECURITY.md").write_text(
        "%s\n\n# Security\n\n"
        "- **Current MINOR** (`v%s.x`) — full security support.\n"
        "%s" % (stamp, cur_minor, prev_sec),
        encoding="utf-8",
    )
    (repo / "VERSIONING.md").write_text(
        "%s\n\n# Versioning\n\n"
        "| Current MINOR (`v%s.x`) | Full support |\n"
        "%s" % (stamp, cur_minor, prev_ver),
        encoding="utf-8",
    )
    (repo / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [1.3.0]\n\n- fixture\n", encoding="utf-8"
    )


@pytest.fixture()
def synth(tmp_path):
    """A throwaway repo shaped like this one: real driver, real site module,
    real tag guard, and stand-in oracles at the exact paths the driver calls."""
    home = tmp_path / "home"
    (home / "gnupg").mkdir(parents=True)
    env = _env(home)
    repo = tmp_path / "repo"
    (repo / ".claude" / "scripts" / "local").mkdir(parents=True)
    (repo / "scripts").mkdir(parents=True)
    (repo / ".claude-plugin").mkdir(parents=True)

    for src, dst in (
        (DRIVER_SRC, repo / ".claude/scripts/local/release.sh"),
        (SITES_SRC, repo / ".claude/scripts/local/_release_bump_sites.py"),
        (GUARD_SRC, repo / ".claude/scripts/local/_release_tag_guard.py"),
    ):
        shutil.copy2(str(src), str(dst))

    (repo / ".claude/scripts/local/verify-counts.sh").write_text(
        STUB_VERIFY_COUNTS, encoding="utf-8"
    )
    (repo / "scripts/build-plugin.py").write_text(STUB_BUILD_PLUGIN, encoding="utf-8")
    (repo / ".claude/scripts/check-canonical-doc-freshness.py").write_text(
        STUB_FRESHNESS, encoding="utf-8"
    )

    write_sites(repo, "1.3.0", D0)
    run([sys.executable, "scripts/build-plugin.py", "--write-manifests"], repo, env)

    git(repo, env, "init", "-q")
    git(repo, env, "symbolic-ref", "HEAD", "refs/heads/main")
    git(repo, env, "config", "commit.gpgsign", "false")
    git(repo, env, "config", "tag.gpgsign", "false")
    git(repo, env, "add", "-A")
    git(repo, env, "commit", "-q", "-m", "fixture: tree at 1.3.0")

    origin = tmp_path / "origin.git"
    git(repo, env, "init", "-q", "--bare", str(origin))
    git(repo, env, "remote", "add", "origin", str(origin))
    git(repo, env, "push", "-q", "origin", "main")
    git(repo, env, "fetch", "-q", "origin", "main")

    return {"repo": repo, "env": env, "origin": origin, "home": home}


def driver(synth, *args: str):
    return run(
        ["bash", ".claude/scripts/local/release.sh"] + list(args),
        synth["repo"],
        synth["env"],
    )


def module(synth, *args: str):
    return run(
        [sys.executable, ".claude/scripts/local/_release_bump_sites.py"] + list(args),
        synth["repo"],
        synth["env"],
    )


def guard(synth, *args: str):
    return run(
        [sys.executable, ".claude/scripts/local/_release_tag_guard.py"] + list(args),
        synth["repo"],
        synth["env"],
    )


# ===========================================================================
# the site table is a single source
# ===========================================================================
def test_print_sites_enumerates_the_table_and_the_generated_manifests():
    own = bump_sites.site_paths()
    both = bump_sites.site_paths(include_generated=True)
    for stamp_site in ("npm/README.md", "SBOM.md", "SECURITY.md", "VERSIONING.md"):
        assert stamp_site in own
    assert "VERSION" in own
    assert own == both[: len(own)]
    assert both[len(own):] == bump_sites.GENERATED_BY_BUMP
    # the manifests are NOT written by this module; they must not be silently
    # folded into the writer's own list
    assert ".claude-plugin/plugin.json" not in own


def test_today_is_a_required_parameter_with_no_default(synth):
    proc = module(synth, "bump", "--target", "1.3.0")
    assert proc.returncode != 0
    assert "--today" in proc.stderr
    assert "required" in proc.stderr


# ===========================================================================
# AC-1 — the writer, at the module layer, with D and D+1 explicit
# ===========================================================================
@pytest.mark.parametrize("today", [D0, D1])
def test_stamps_are_frozen_when_the_version_already_matches(synth, today):
    before = tree_fingerprint(synth["repo"])
    proc = module(synth, "bump", "--target", "1.3.0", "--today", today)
    assert proc.returncode == 0, proc.stderr
    assert tree_fingerprint(synth["repo"]) == before, (
        "a stamp moved on --today=%s with the version unchanged" % today
    )
    assert "line untouched" in proc.stdout or "already at" in proc.stdout


def test_a_real_version_change_still_writes_every_site(synth):
    repo = synth["repo"]
    write_sites(repo, "1.2.0", D0)
    proc = module(synth, "bump", "--target", "1.3.0", "--today", D1)
    assert proc.returncode == 0, proc.stderr
    assert (repo / "VERSION").read_text() == "1.3.0\n"
    assert '"version": "1.3.0"' in (repo / "npm/package.json").read_text()
    assert 'version = "1.3.0"' in (repo / "pyproject.toml").read_text()
    assert "--pin v1.3.0" in (repo / "INSTALL.md").read_text()
    assert "currently v1.3.0, aligned" in (repo / "docs/ARCHITECTURE.md").read_text()
    # README.md is NOT a version site: `VERSION=` never existed there
    # (verify-counts removed its dead rule in S291 with the archaeology in a
    # comment; the release checklist says the same). The fixture PLANTS the
    # literal so this asserts the writer leaves it alone — a writer row for a
    # site no oracle watches would rewrite a file every other surface
    # declares out of scope.
    assert (repo / "README.md").read_text() == "VERSION=1.2.0\n"
    for stamped in ("npm/README.md", "SBOM.md", "SECURITY.md", "VERSIONING.md"):
        text = (repo / stamped).read_text()
        assert "last-reviewed: %s v1.3.0" % D1 in text, stamped
    # the support window moved with the version: Current <- target minor,
    # Previous <- the minor before it (the oracle's own derivation)
    for doc in ("SECURITY.md", "VERSIONING.md"):
        text = (repo / doc).read_text()
        assert "v1.3.x" in text, doc
        assert "v1.2.x" in text, doc
        assert "v1.1.x" not in text, doc


# ===========================================================================
# the support window (re-pass F-sites P1): minor/prev_minor are ORACLE modes
# (verify-counts VERSION_SITES, S293) — a writer without them dies MID-PHASE
# at the driver's own verify-counts call on the next MINOR bump, outside
# --dry-run, with no restore trap: a half-bumped dirty tree.
# ===========================================================================
def test_minor_bump_rewrites_the_support_window_sites(synth):
    repo = synth["repo"]
    proc = module(synth, "bump", "--target", "1.4.0", "--today", D2)
    assert proc.returncode == 0, proc.stderr
    for doc in ("SECURITY.md", "VERSIONING.md"):
        text = (repo / doc).read_text()
        assert "v1.4.x" in text, doc  # Current shifted to the target minor
        assert "v1.3.x" in text, doc  # Previous = the old Current
        assert "v1.2.x" not in text, doc  # the stale window is GONE


def test_major_bump_shifts_current_and_leaves_previous_to_judgment(synth):
    """X.0.0: Previous MINOR is NOT derivable from the target alone, and the
    live oracle skips value-checking it there too (it derives prev="" at X.0).
    The writer must neither guess nor die half-written: Current shifts,
    Previous is left byte-identical, and the skip is ANNOUNCED — a silent
    stale support window is the unwatched-doc class wearing a new hat."""
    repo = synth["repo"]
    proc = module(synth, "bump", "--target", "2.0.0", "--today", D2)
    assert proc.returncode == 0, proc.stderr
    for doc in ("SECURITY.md", "VERSIONING.md"):
        text = (repo / doc).read_text()
        assert "v2.0.x" in text, doc
        assert "v1.2.x" in text, doc  # the old Previous, untouched
    assert "release-train judgment" in proc.stdout, proc.stdout


def test_minor_bump_survives_the_drivers_own_oracle_end_to_end(synth):
    """The exact death the finding describes, end-to-end: TARGET_BASE moved to
    the next MINOR, tree at the previous one. Before the fix the phase wrote
    ten sites and then DIED at its own verify-counts call ("a site is
    unpatched") — this asserts it reaches its commit with a clean tree."""
    repo, env = synth["repo"], synth["env"]
    drv = repo / ".claude/scripts/local/release.sh"
    src = drv.read_text(encoding="utf-8")
    m = re.search(r'(?m)^TARGET_BASE="(\d+\.\d+\.\d+)"$', src)
    assert m, "driver has no bare-semver TARGET_BASE"
    drv.write_text(
        src.replace(m.group(0), 'TARGET_BASE="1.4.0"'), encoding="utf-8"
    )
    git(repo, env, "add", "-A")
    git(repo, env, "commit", "-q", "-m", "fixture: retarget driver to 1.4.0")
    head_before = git(repo, env, "rev-parse", "HEAD")

    proc = driver(synth, "bump", "--stable", "--npm-readme-reviewed", "--today", D2)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "a site is unpatched" not in proc.stderr, proc.stderr
    assert git(repo, env, "rev-parse", "HEAD") != head_before, "no commit made"
    index_and_worktree_clean(repo, env)
    assert (repo / "VERSION").read_text() == "1.4.0\n"
    for doc in ("SECURITY.md", "VERSIONING.md"):
        text = (repo / doc).read_text()
        assert "v1.4.x" in text and "v1.3.x" in text, doc


def test_writer_table_covers_every_mode_of_the_live_oracle():
    """Structural closure of the F-sites class: every (doc, mode) pair in the
    LIVE verify-counts VERSION_SITES must have a writer site — derived from
    the authority's own source, never recalled (closed-set lesson). A pair
    added to the oracle without a writer is a mid-bump death deferred to the
    next bump that moves that mode."""
    text = (LOCAL / "verify-counts.sh").read_text(encoding="utf-8")
    entries = re.findall(
        r'\(\s*"([^"]+)",\s*r\'[^\']*\',\s*"(full|minor|prev_minor)"\s*\)', text
    )
    modes = {mode for _doc, mode in entries}
    # parser liveness first: all three modes must be found, or the regex above
    # went stale and "nothing missing" would mean nothing at all
    assert {"full", "minor", "prev_minor"} <= modes, entries
    writer = {(path, kind) for path, kind, _rx in bump_sites._SITES}
    writer_paths = {path for path, _kind in writer}
    missing = []
    for doc, mode in entries:
        covered = doc in writer_paths if mode == "full" else (doc, mode) in writer
        if not covered:
            missing.append((doc, mode))
    assert not missing, (
        "verify-counts VERSION_SITES entries with NO writer site (the next "
        "bump that moves these modes dies mid-phase): %s" % missing
    )


def test_restamp_moves_the_stamps_at_an_unchanged_version(synth):
    repo = synth["repo"]
    proc = module(synth, "bump", "--target", "1.3.0", "--today", D1, "--restamp")
    assert proc.returncode == 0, proc.stderr
    for stamped in ("npm/README.md", "SBOM.md", "SECURITY.md", "VERSIONING.md"):
        assert "last-reviewed: %s v1.3.0" % D1 in (repo / stamped).read_text()


# ===========================================================================
# AC-1 — the same invariant at the DRIVER layer (the surface the Owner runs)
# ===========================================================================
@pytest.mark.parametrize("today", [D0, D1])
def test_ac1_bump_stable_on_an_already_target_tree_writes_nothing(synth, today):
    repo, env = synth["repo"], synth["env"]
    head_before = git(repo, env, "rev-parse", "HEAD")
    fp_before = tree_fingerprint(repo)

    proc = driver(synth, "bump", "--stable", "--npm-readme-reviewed", "--today", today)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "no-op" in proc.stdout

    assert git(repo, env, "rev-parse", "HEAD") == head_before, "a commit was made"
    index_and_worktree_clean(repo, env)
    assert tree_fingerprint(repo) == fp_before, "a file was written"
    # the four oracles must have actually been consulted, and said so
    for label in ("oracle 1/4", "oracle 2/4", "oracle 3/4", "oracle 4/4"):
        assert label in proc.stdout, proc.stdout


def test_the_noop_path_does_not_demand_the_npm_readme_ack(synth):
    """A run that writes nothing asserts nothing: requiring the review ack
    there would be asking the Owner to certify a review that is not happening."""
    proc = driver(synth, "bump", "--stable", "--today", D1)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "no-op" in proc.stdout
    index_and_worktree_clean(synth["repo"], synth["env"])


def test_a_real_bump_still_commits(synth):
    repo, env = synth["repo"], synth["env"]
    write_sites(repo, "1.2.0", D0)
    run([sys.executable, "scripts/build-plugin.py", "--write-manifests"], repo, env)
    git(repo, env, "add", "-A")
    git(repo, env, "commit", "-q", "-m", "fixture: back to 1.2.0")
    head_before = git(repo, env, "rev-parse", "HEAD")

    proc = driver(synth, "bump", "--stable", "--npm-readme-reviewed", "--today", D1)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert git(repo, env, "rev-parse", "HEAD") != head_before
    assert (repo / "VERSION").read_text() == "1.3.0\n"
    index_and_worktree_clean(repo, env)
    # and it warns that the tag phase will now require a push
    assert "ancestry guard" in proc.stderr


def test_restamp_requires_the_review_ack(synth):
    proc = driver(synth, "bump", "--stable", "--restamp", "--today", D1)
    assert proc.returncode != 0
    assert "--npm-readme-reviewed" in proc.stderr
    index_and_worktree_clean(synth["repo"], synth["env"])


def test_restamp_survives_the_noop_fast_path(synth):
    """Regression for the r14 hole: with the same version and four clean
    oracles the predicate would return BEFORE any substitution, and --restamp
    would be dead letter."""
    repo, env = synth["repo"], synth["env"]
    head_before = git(repo, env, "rev-parse", "HEAD")
    proc = driver(
        synth, "bump", "--stable", "--npm-readme-reviewed", "--restamp", "--today", D2
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "no-op fast path DISABLED" in proc.stdout
    assert "no-op: tree is already at" not in proc.stdout
    assert git(repo, env, "rev-parse", "HEAD") != head_before
    for stamped in ("npm/README.md", "SBOM.md", "SECURITY.md", "VERSIONING.md"):
        assert "last-reviewed: %s v1.3.0" % D2 in (repo / stamped).read_text()


# ===========================================================================
# dry-run: index AND worktree clean, with a DERIVED restore list
# ===========================================================================
def test_dry_run_leaves_index_and_worktree_clean(synth):
    repo, env = synth["repo"], synth["env"]
    write_sites(repo, "1.2.0", D0)
    run([sys.executable, "scripts/build-plugin.py", "--write-manifests"], repo, env)
    git(repo, env, "add", "-A")
    git(repo, env, "commit", "-q", "-m", "fixture: back to 1.2.0")
    head_before = git(repo, env, "rev-parse", "HEAD")

    proc = driver(
        synth, "bump", "--stable", "--npm-readme-reviewed", "--dry-run", "--today", D1
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "restored to HEAD" in proc.stdout
    assert git(repo, env, "rev-parse", "HEAD") == head_before
    index_and_worktree_clean(repo, env)
    assert (repo / "VERSION").read_text() == "1.2.0\n"


def test_dry_run_restores_a_site_the_table_grew(synth):
    """S273 class, closed by derivation. The restore list is not typed: growing
    the site table must automatically grow what the dry-run puts back."""
    repo, env = synth["repo"], synth["env"]
    (repo / "EXTRA.md").write_text("pinned v1.2.0\n", encoding="utf-8")
    mod = repo / ".claude/scripts/local/_release_bump_sites.py"
    marker = 'if __name__ == "__main__":'
    src = mod.read_text(encoding="utf-8")
    assert marker in src
    mod.write_text(
        src.replace(
            marker,
            '_SITES.append(("EXTRA.md", PLAIN, r"(pinned v)" + SEMVER))\n\n' + marker,
        ),
        encoding="utf-8",
    )
    write_sites(repo, "1.2.0", D0)
    run([sys.executable, "scripts/build-plugin.py", "--write-manifests"], repo, env)
    git(repo, env, "add", "-A")
    git(repo, env, "commit", "-q", "-m", "fixture: extra site")

    listed = module(synth, "print-sites", "--include-generated")
    assert "EXTRA.md" in listed.stdout.split(), listed.stdout

    proc = driver(
        synth, "bump", "--stable", "--npm-readme-reviewed", "--dry-run", "--today", D1
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    index_and_worktree_clean(repo, env)
    assert (repo / "EXTRA.md").read_text() == "pinned v1.2.0\n"


def test_dry_run_restores_when_a_derived_site_is_absent_from_head(synth):
    """W0 re-pass r2 P1: `git checkout -- <all paths>` is ATOMIC — one path
    absent from HEAD (a file the bump CREATED, e.g. a plugin manifest on its
    first appearance) aborts the whole restore, `|| true` swallowed the error,
    and the trap still printed "restored to HEAD" over a fully dirty tree.
    The restore must be per-path (checkout what HEAD has, remove what the
    bump created) and the trap must ASSERT the postcondition, not the
    attempt."""
    repo, env = synth["repo"], synth["env"]
    write_sites(repo, "1.2.0", D0)
    git(repo, env, "rm", "-q", "-r", ".claude-plugin")
    git(repo, env, "add", "-A")
    git(repo, env, "commit", "-q", "-m", "fixture: 1.2.0 tree, no plugin manifests in HEAD")
    head_before = git(repo, env, "rev-parse", "HEAD")

    proc = driver(
        synth, "bump", "--stable", "--npm-readme-reviewed", "--dry-run", "--today", D1
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "restored to HEAD" in proc.stdout
    assert git(repo, env, "rev-parse", "HEAD") == head_before
    index_and_worktree_clean(repo, env)
    assert (repo / "VERSION").read_text() == "1.2.0\n"
    # the files the bump CREATED (not in HEAD) are gone again, not debris
    assert not (repo / ".claude-plugin" / "plugin.json").exists()
    assert not (repo / ".claude-plugin" / "marketplace.json").exists()


# ===========================================================================
# tag guard — ancestry
# ===========================================================================
def test_fetch_failure_and_non_ancestor_are_DISTINCT(synth):
    repo, env = synth["repo"], synth["env"]

    # (1) origin unreachable — the check did NOT run; this is not a verdict
    git(repo, env, "remote", "set-url", "origin", str(repo.parent / "does-not-exist"))
    broken = guard(synth, "ancestry", "--repo", str(repo))
    assert broken.returncode == tag_guard.E_FETCH, broken.stderr
    assert "could not talk to origin" in broken.stderr
    assert "--offline-ack" in broken.stderr

    # (2) origin reachable, HEAD unpushed — a real governance stop
    git(repo, env, "remote", "set-url", "origin", str(synth["origin"]))
    (repo / "late.txt").write_text("landed after CI\n", encoding="utf-8")
    git(repo, env, "add", "late.txt")
    git(repo, env, "commit", "-q", "-m", "unpushed")
    stop = guard(synth, "ancestry", "--repo", str(repo))
    assert stop.returncode == tag_guard.E_NOT_ANCESTOR, stop.stderr
    assert "not an ancestor" in stop.stderr
    assert "could not talk to origin" not in stop.stderr

    # the two failures do not share an exit code — the MODE is distinguishable
    assert tag_guard.E_FETCH != tag_guard.E_NOT_ANCESTOR


def test_ancestry_passes_when_head_is_pushed(synth):
    proc = guard(synth, "ancestry", "--repo", str(synth["repo"]))
    assert proc.returncode == 0, proc.stderr
    assert "ancestor" in proc.stdout


def test_offline_ack_is_named_and_announced(synth):
    repo, env = synth["repo"], synth["env"]
    git(repo, env, "remote", "set-url", "origin", str(repo.parent / "gone"))
    proc = guard(synth, "ancestry", "--repo", str(repo), "--offline-ack")
    assert proc.returncode == 0, proc.stderr
    assert "STALE" in proc.stdout


# ===========================================================================
# tag guard — restricted delta
# ===========================================================================
def make_repass(repo: Path, slug: str, artifacts: Dict[str, str]) -> Dict[str, str]:
    directory = repo / ".claude/plans/PLAN-166" / slug
    directory.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    for name, body in sorted(artifacts.items()):
        (directory / name).write_text(body, encoding="utf-8")
        lines.append("%s  %s" % (sha256_file(directory / name), name))
    manifest = directory / "MANIFEST.sha256"
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    rel = ".claude/plans/PLAN-166/%s" % slug
    return {
        "dir": rel,
        "manifest_rel": "%s/MANIFEST.sha256" % rel,
        "manifest_sha": sha256_file(manifest),
        "artifact_rels": ["%s/%s" % (rel, n) for n in sorted(artifacts)],
    }


def _decision_line(item) -> str:
    """One `verdict` line, canonical or with a LITERAL key spelling.

    `item` is either the value (canonical `verdict: <value>`) or a
    `(key_text, value)` pair whose key_text is emitted verbatim before the
    colon — `("verdict ", "NO-GO")` writes `verdict : NO-GO`, the valid YAML
    that the two rails parsed with two different grammars (PLAN-177 t2 P1-a).
    """
    if isinstance(item, tuple):
        key, value = item
        return "%s: %s\n" % (key, value)
    return "verdict: %s\n" % item


def write_verdict(
    repo: Path,
    tag: str,
    parent: str,
    allowlist: Sequence[str],
    manifest_rel: str,
    manifest_sha: str,
    verdict=("GO",),
) -> str:
    """`verdict` accepts a str, None, or a SEQUENCE of decision lines.

    The three shapes the PLAN-177 gate must separate: one line (normal),
    zero lines (an author who never filled the template field in), two
    lines (the last-wins override, where NO-GO followed by GO parses as
    GO).

    PLAN-177 t2 (P1-a): a sequence item may also be a `(key_text, value)`
    pair, where `key_text` is the LITERAL spelling emitted before the colon
    (`"verdict "`, `"verdict\\t"`). That is the only way to express the
    grammar divergence the two rails had — writing `"verdict: %s"` for every
    line can only produce canonical keys, which is precisely why the first
    round of controls could not see the defect.
    """
    rel = ".claude/governance/pair-rail-verdict-%s.md" % tag
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    entries = "\n".join("  - %s" % e for e in allowlist)
    if verdict is None:
        decisions = []
    elif isinstance(verdict, str):
        decisions = [verdict]
    else:
        decisions = list(verdict)
    decision = "".join(_decision_line(d) for d in decisions)
    path.write_text(
        "# Pair-Rail Verdict \u2014 %s\n\n```yaml\n%srelease_tag: %s\n"
        "parent_sha: %s\ndelta_allowlist:\n%s\ndelta_manifest: %s\n"
        "delta_manifest_sha256: %s\n```\n" % (
            tag, decision, tag, parent, entries, manifest_rel, manifest_sha,
        ),
        encoding="utf-8",
    )
    return rel


def arm_verdict(
    synth,
    tag: str,
    slug: str = "repass-r2",
    extra_allow=(),
    verdict=("GO",),
):
    """Commit a re-pass + verdict for `tag`, anchored at the pre-verdict HEAD."""
    repo, env = synth["repo"], synth["env"]
    parent = git(repo, env, "rev-parse", "HEAD")
    ev = make_repass(
        repo, slug, {"verdict-r1.txt": "GO\n", "transcript-r1.log": "rounds: 3\n"}
    )
    verdict_rel = ".claude/governance/pair-rail-verdict-%s.md" % tag
    allow = [verdict_rel, ev["manifest_rel"]] + ev["artifact_rels"] + list(extra_allow)
    write_verdict(
        repo, tag, parent, allow, ev["manifest_rel"],
        ev["manifest_sha"], verdict=verdict,
    )
    git(repo, env, "add", "-A")
    git(repo, env, "commit", "-q", "-m", "governance: verdict %s" % tag)
    git(repo, env, "push", "-q", "origin", "main")
    git(repo, env, "fetch", "-q", "origin", "main")
    return {"parent": parent, "verdict_rel": verdict_rel, "ev": ev}


def test_delta_accepts_exactly_the_verdict_and_its_pinned_evidence(synth):
    arm_verdict(synth, "v1.3.0-rc.2")
    proc = guard(synth, "delta", "--repo", str(synth["repo"]), "--tag", "v1.3.0-rc.2")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "closed allowlist" in proc.stdout
    assert "shasum" in proc.stdout


@pytest.mark.parametrize("tag", ["v1.3.0-rc.2", "v1.3.0"])
def test_delta_blocks_a_file_that_landed_after_the_review(synth, tag):
    """Unconditional by design: scoping this to --stable would let an rc.N ship
    a post-review commit and become the unreviewed baseline of the GA."""
    repo, env = synth["repo"], synth["env"]
    arm_verdict(synth, tag)
    (repo / "sneaky.py").write_text("print('landed after the review')\n", encoding="utf-8")
    git(repo, env, "add", "sneaky.py")
    git(repo, env, "commit", "-q", "-m", "post-review change")
    git(repo, env, "push", "-q", "origin", "main")

    proc = guard(synth, "delta", "--repo", str(repo), "--tag", tag)
    assert proc.returncode == tag_guard.E_DELTA, proc.stdout + proc.stderr
    assert "sneaky.py" in proc.stderr


def test_delta_blocks_a_fabricated_parent_outside_head_history(synth):
    """W0 re-pass r2 P1: `cat-file -e` proves the anchor EXISTS, not that it
    is in the history this tag signs. A fabricated commit over HEAD's own
    tree (`git commit-tree`, parented off an older commit, on no branch)
    makes diff(parent..HEAD) contain ONLY the verdict + evidence while an
    unreviewed file sits on main — every downstream check (allowlist,
    manifest pin, set equality, vacuity) then passes and the guard prints
    "all inside the verdict's closed allowlist" over an unreviewed tree."""
    repo, env = synth["repo"], synth["env"]
    h0 = git(repo, env, "rev-parse", "HEAD")

    # unreviewed work lands on main
    (repo / "unreviewed.py").write_text("print('never reviewed')\n", encoding="utf-8")
    git(repo, env, "add", "unreviewed.py")
    git(repo, env, "commit", "-q", "-m", "unreviewed change")
    m2_tree = git(repo, env, "rev-parse", "HEAD^{tree}")

    # fabricated anchor: HEAD's exact tree, parented off h0, on NO branch —
    # it exists in the object store but HEAD does not descend from it
    orphan = git(repo, env, "commit-tree", m2_tree, "-p", h0, "-m", "fabricated anchor")
    not_anc = run(["git", "merge-base", "--is-ancestor", orphan, "HEAD"], repo, env)
    assert not_anc.returncode == 1, "fixture broke: orphan IS an ancestor"

    ev = make_repass(repo, "repass-r2", {"verdict-r1.txt": "GO\n"})
    verdict_rel = ".claude/governance/pair-rail-verdict-v1.3.0-rc.2.md"
    write_verdict(
        repo,
        "v1.3.0-rc.2",
        orphan,
        [verdict_rel, ev["manifest_rel"]] + ev["artifact_rels"],
        ev["manifest_rel"],
        ev["manifest_sha"],
    )
    git(repo, env, "add", "-A")
    git(repo, env, "commit", "-q", "-m", "verdict anchored on the fabricated commit")

    proc = guard(synth, "delta", "--repo", str(repo), "--tag", "v1.3.0-rc.2")
    assert proc.returncode == tag_guard.E_PARENT_NOT_ANCESTOR, (
        proc.stdout + proc.stderr
    )
    assert "ancestor" in proc.stderr
    # and it is a DISTINCT mode from both "bad verdict" and "delta outside"
    assert tag_guard.E_PARENT_NOT_ANCESTOR != tag_guard.E_VERDICT
    assert tag_guard.E_PARENT_NOT_ANCESTOR != tag_guard.E_DELTA


def test_delta_rejects_a_wildcard_verdict_entry(synth):
    repo, env = synth["repo"], synth["env"]
    parent = git(repo, env, "rev-parse", "HEAD")
    ev = make_repass(repo, "repass-r2", {"verdict-r1.txt": "GO\n"})
    verdict_rel = ".claude/governance/pair-rail-verdict-v1.3.0-rc.2.md"
    write_verdict(
        repo,
        "v1.3.0-rc.2",
        parent,
        [
            verdict_rel,
            ".claude/governance/pair-rail-verdict-*.md",  # the hole
            ev["manifest_rel"],
        ] + ev["artifact_rels"],
        ev["manifest_rel"],
        ev["manifest_sha"],
    )
    git(repo, env, "add", "-A")
    git(repo, env, "commit", "-q", "-m", "wildcard allowlist")
    proc = guard(synth, "delta", "--repo", str(repo), "--tag", "v1.3.0-rc.2")
    assert proc.returncode == tag_guard.E_VERDICT, proc.stdout + proc.stderr
    assert "glob metacharacter" in proc.stderr


def test_delta_rejects_another_tags_verdict_in_the_allowlist(synth):
    repo, env = synth["repo"], synth["env"]
    parent = git(repo, env, "rev-parse", "HEAD")
    ev = make_repass(repo, "repass-r2", {"verdict-r1.txt": "GO\n"})
    verdict_rel = ".claude/governance/pair-rail-verdict-v1.3.0-rc.2.md"
    write_verdict(
        repo,
        "v1.3.0-rc.2",
        parent,
        [
            verdict_rel,
            ".claude/governance/pair-rail-verdict-v1.2.0.md",  # historical
            ev["manifest_rel"],
        ] + ev["artifact_rels"],
        ev["manifest_rel"],
        ev["manifest_sha"],
    )
    git(repo, env, "add", "-A")
    git(repo, env, "commit", "-q", "-m", "historical verdict in allowlist")
    proc = guard(synth, "delta", "--repo", str(repo), "--tag", "v1.3.0-rc.2")
    assert proc.returncode == tag_guard.E_VERDICT, proc.stdout + proc.stderr
    assert "another tag" in proc.stderr


def test_delta_refuses_a_verdict_written_for_a_different_tag(synth):
    arm_verdict(synth, "v1.3.0-rc.2")
    repo = synth["repo"]
    shutil.copy2(
        str(repo / ".claude/governance/pair-rail-verdict-v1.3.0-rc.2.md"),
        str(repo / ".claude/governance/pair-rail-verdict-v1.3.0.md"),
    )
    proc = guard(synth, "delta", "--repo", str(repo), "--tag", "v1.3.0")
    assert proc.returncode == tag_guard.E_VERDICT, proc.stdout + proc.stderr
    assert "release_tag" in proc.stderr


def test_delta_requires_a_verdict_at_all(synth):
    proc = guard(synth, "delta", "--repo", str(synth["repo"]), "--tag", "v1.3.0-rc.9")
    assert proc.returncode == tag_guard.E_VERDICT
    assert "no signed verdict" in proc.stderr


def test_delta_catches_a_tampered_artifact_and_a_tampered_manifest(synth):
    repo, env = synth["repo"], synth["env"]
    armed = arm_verdict(synth, "v1.3.0-rc.2")
    artifact = repo / armed["ev"]["artifact_rels"][0]

    # (1) content changed, manifest untouched -> shasum -c fails
    artifact.write_text("GO (edited after the review)\n", encoding="utf-8")
    git(repo, env, "add", "-A")
    git(repo, env, "commit", "-q", "-m", "tamper artifact")
    proc = guard(synth, "delta", "--repo", str(repo), "--tag", "v1.3.0-rc.2")
    assert proc.returncode == tag_guard.E_MANIFEST_CONTENT, proc.stdout + proc.stderr

    # (2) manifest re-generated to cover the tamper -> the sha PIN in the
    #     signed verdict no longer matches
    manifest = repo / armed["ev"]["manifest_rel"]
    lines = []
    for rel in armed["ev"]["artifact_rels"]:
        full = repo / rel
        lines.append("%s  %s" % (sha256_file(full), full.name))
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    git(repo, env, "add", "-A")
    git(repo, env, "commit", "-q", "-m", "tamper manifest")
    proc = guard(synth, "delta", "--repo", str(repo), "--tag", "v1.3.0-rc.2")
    assert proc.returncode == tag_guard.E_MANIFEST_PIN, proc.stdout + proc.stderr


def test_delta_rejects_an_unlisted_file_smuggled_into_the_repass_dir(synth):
    """`repass-<N>/**` as a wildcard was the r14 hole: the set closes by NAME
    against the manifest, so an extra allowlisted path in that directory is a
    set violation even before its content is considered."""
    repo, env = synth["repo"], synth["env"]
    parent = git(repo, env, "rev-parse", "HEAD")
    ev = make_repass(repo, "repass-r2", {"verdict-r1.txt": "GO\n"})
    (repo / ev["dir"] / "smuggled.sh").write_text("echo hi\n", encoding="utf-8")
    verdict_rel = ".claude/governance/pair-rail-verdict-v1.3.0-rc.2.md"
    write_verdict(
        repo,
        "v1.3.0-rc.2",
        parent,
        [verdict_rel, ev["manifest_rel"], "%s/smuggled.sh" % ev["dir"]]
        + ev["artifact_rels"],
        ev["manifest_rel"],
        ev["manifest_sha"],
    )
    git(repo, env, "add", "-A")
    git(repo, env, "commit", "-q", "-m", "smuggle")
    proc = guard(synth, "delta", "--repo", str(repo), "--tag", "v1.3.0-rc.2")
    assert proc.returncode == tag_guard.E_MANIFEST_SET, proc.stdout + proc.stderr
    assert "smuggled.sh" in proc.stderr


def test_delta_rejects_an_allowlist_entry_that_is_not_evidence(synth):
    """Wildcard-free is not enough — the allowlist must also be EXHAUSTIVE.
    A verdict that allowlists `VERSION` would wave through exactly the
    post-review bump commit that F2 is about, and every check below it would
    still report green. The refusal has to land on the allowlist itself."""
    repo, env = synth["repo"], synth["env"]
    parent = git(repo, env, "rev-parse", "HEAD")
    ev = make_repass(repo, "repass-r2", {"verdict-r1.txt": "GO\n"})
    verdict_rel = ".claude/governance/pair-rail-verdict-v1.3.0-rc.2.md"
    write_verdict(
        repo,
        "v1.3.0-rc.2",
        parent,
        [verdict_rel, ev["manifest_rel"], "VERSION"] + ev["artifact_rels"],
        ev["manifest_rel"],
        ev["manifest_sha"],
    )
    git(repo, env, "add", "-A")
    git(repo, env, "commit", "-q", "-m", "allowlist a version site")
    proc = guard(synth, "delta", "--repo", str(repo), "--tag", "v1.3.0-rc.2")
    assert proc.returncode == tag_guard.E_VERDICT, proc.stdout + proc.stderr
    assert "EXHAUSTIVE" in proc.stderr
    assert "'VERSION'" in proc.stderr


@pytest.mark.parametrize(
    "entry",
    [
        # the plan file itself — post-review edits would ride the tag
        ".claude/plans/PLAN-166-release-hold-findings-closure.md",
        # ANOTHER tag's verdict-fields — stale evidence smuggled by name
        ".claude/plans/PLAN-166/verdict-fields-v1.2.0.md",
        # immutable historical evidence outside the pinned manifest dir
        ".claude/plans/PLAN-166/repass-r1/old-evidence.txt",
        # W0 re-pass r2 P2: the RIGHT basename in the WRONG directory — a
        # basename-only rule admits any number of look-alikes anywhere under
        # .claude/plans/; the file must sit at its canonical path (the plan
        # directory that CONTAINS the manifest dir)
        ".claude/plans/archive/verdict-fields-v1.3.0-rc.2.md",
        ".claude/plans/PLAN-166/repass-r1/verdict-fields-v1.3.0-rc.2.md",
    ],
)
def test_delta_rejects_plan_paths_outside_the_manifest_dir(synth, entry):
    """Re-pass P2: `.claude/plans/` entries OUTSIDE the manifest directory
    used to close by NAME alone — no content pin, no manifest coverage, no
    tag specificity — while the same guard rejected `VERSION` as
    non-EXHAUSTIVE. Only `verdict-fields-<THIS TAG>.md` at its CANONICAL
    path (directly inside the plan directory holding the manifest dir) may
    live outside the content-pinned manifest directory; everything else —
    including same-basename look-alikes elsewhere — must be IN it."""
    arm_verdict(synth, "v1.3.0-rc.2", extra_allow=[entry])
    proc = guard(synth, "delta", "--repo", str(synth["repo"]), "--tag", "v1.3.0-rc.2")
    assert proc.returncode == tag_guard.E_VERDICT, proc.stdout + proc.stderr
    assert "verdict-fields" in proc.stderr, proc.stderr


def test_delta_accepts_this_tags_verdict_fields_outside_the_manifest_dir(synth):
    """The one plan-side file the plan PROMISES outside the manifest dir: the
    verdict-fields carrying the literal target tag in its name."""
    repo = synth["repo"]
    vf_rel = ".claude/plans/PLAN-166/verdict-fields-v1.3.0-rc.2.md"
    vf = repo / vf_rel
    vf.parent.mkdir(parents=True, exist_ok=True)
    vf.write_text("inputs_hash fields for v1.3.0-rc.2\n", encoding="utf-8")
    arm_verdict(synth, "v1.3.0-rc.2", extra_allow=[vf_rel])
    proc = guard(synth, "delta", "--repo", str(repo), "--tag", "v1.3.0-rc.2")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_guard_selects_the_yaml_block_like_the_step15_reader(synth):
    """Re-pass P2 (reader parity): the step-15 validator selects the FIRST
    ```yaml fence specifically (validate-pair-rail-verdict.py); the guard used
    to enter the first fence of ANY language, so a verdict with a leading
    non-yaml fence (a quoted transcript, say) parsed as EMPTY here while the
    validator read it fine — two readers of the same signed file disagreeing,
    fail-closed direction but still a disagreement."""
    repo, env = synth["repo"], synth["env"]
    armed = arm_verdict(synth, "v1.3.0-rc.2")
    path = repo / armed["verdict_rel"]
    text = path.read_text(encoding="utf-8")
    assert text.count("```yaml") == 1
    path.write_text(
        text.replace(
            "```yaml", "```text\ncodex transcript: GO\n```\n\n```yaml", 1
        ),
        encoding="utf-8",
    )
    git(repo, env, "add", "-A")
    git(repo, env, "commit", "-q", "-m", "verdict prose gains a quoted fence")
    git(repo, env, "push", "-q", "origin", "main")
    proc = guard(synth, "delta", "--repo", str(repo), "--tag", "v1.3.0-rc.2")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_delta_refuses_to_pass_vacuously_when_the_verdict_anchors_itself(synth):
    """An anchor at (or after) the verdict makes every assert above trivially
    true: the delta is empty, and "all changed files are allowlisted" is a
    statement about nothing. That is the v1.16.0 self-reference bug wearing a
    new hat, and it is the vacuous-gate class this repo keeps paying for.

    The guard reads the verdict from the working tree, which is what makes the
    fixture possible; the driver's own clean-tree check blocks this route
    locally, but the server-side port in release.yml reads a tree it did not
    produce, so the assert has to prove it actually saw the verdict move."""
    repo, env = synth["repo"], synth["env"]
    armed = arm_verdict(synth, "v1.3.0-rc.2")
    head = git(repo, env, "rev-parse", "HEAD")
    write_verdict(
        repo,
        "v1.3.0-rc.2",
        head,  # the commit that ALREADY contains this verdict
        [armed["verdict_rel"], armed["ev"]["manifest_rel"]]
        + armed["ev"]["artifact_rels"],
        armed["ev"]["manifest_rel"],
        armed["ev"]["manifest_sha"],
    )
    proc = guard(synth, "delta", "--repo", str(repo), "--tag", "v1.3.0-rc.2")
    assert proc.returncode == tag_guard.E_VACUOUS, proc.stdout + proc.stderr
    assert "VACUOUSLY" in proc.stderr
    # and it is a DISTINCT mode from "a file landed outside the allowlist"
    assert tag_guard.E_VACUOUS != tag_guard.E_DELTA


# ===========================================================================
# the guards are wired into the DRIVER, for both invocations
# ===========================================================================
@pytest.mark.parametrize(
    "tag,flags",
    [("v1.3.0-rc.2", ["--rc", "2"]), ("v1.3.0", ["--stable"])],
)
def test_tag_phase_runs_both_guards_for_rc_and_stable(synth, tag, flags):
    repo, env = synth["repo"], synth["env"]
    arm_verdict(synth, tag)

    happy = driver(synth, "tag", *(flags + ["--dry-run"]))
    assert happy.returncode == 0, happy.stdout + happy.stderr
    assert "ancestor" in happy.stdout
    assert "closed allowlist" in happy.stdout
    assert "dry-run: tag NOT created" in happy.stdout

    (repo / "post-review.txt").write_text("nope\n", encoding="utf-8")
    git(repo, env, "add", "-A")
    git(repo, env, "commit", "-q", "-m", "post review")
    git(repo, env, "push", "-q", "origin", "main")

    blocked = driver(synth, "tag", *(flags + ["--dry-run"]))
    assert blocked.returncode != 0, blocked.stdout
    assert "restricted-delta guard refused the tag" in blocked.stderr
    assert "post-review.txt" in blocked.stderr


def test_tag_annotation_carries_the_whole_train_and_no_stale_release(synth):
    arm_verdict(synth, "v1.3.0")
    proc = driver(synth, "tag", "--stable", "--dry-run")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    # repass-r2 part-d P1: the expectation must track the LIVE train scope —
    # pinning the rc.1-era string here blessed a stale signed-tag annotation.
    assert (
        "PLAN-162 / PLAN-165 / PLAN-166 / PLAN-167 / PLAN-168 / "
        "PLAN-169 W0-W2 (ADRs 184 -> 190)" in proc.stdout
    )
    assert "v1.3.0 —" in proc.stdout


# ===========================================================================
# F6 — the name was the root of the class; the literals go with it
# ===========================================================================
SEMVER_RX = re.compile(r"\b\d+\.\d+\.\d+\b")
# "<number> [word] site(s)" — a census in a comment has no oracle behind it.
# repass-r2 part-d P2: ordinals count too — "12th site" is as much an
# oracle-less census claim as "12 sites"; the guard missed the suffix.
SITE_COUNT_RX = re.compile(
    r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|"
    r"\d+(?:st|nd|rd|th)?)\s+"
    r"(?:\w+\s+)?sites?\b",
    re.IGNORECASE,
)
# Assembled at RUNTIME, never as a literal: a control whose own file is a hit
# has to exempt itself, and an exemption is how a control stops controlling.
# (`"a" "b"` and `"a" + "b"` are both folded by the compiler and would land in
# this module's .pyc verbatim; str.join is not folded.)
OLD_DRIVER_STEM = "-".join(("release", "v1", "2", "0"))
# PLAN-177 W0 item 2 (P1-2): the npm docs joined the roots because they were
# the one published surface no scanner could see — `npm/INTEGRITY.md` carried
# a hardcoded version through several releases and every gate stayed green.
# They are listed as FILES, never as the `npm` directory: `npm/` receives a
# mirrored copy of `.claude/**` + `scripts/**` (the publish staging rsync, and
# any local `install-npm.sh` run), so a directory root would have the scanner
# auditing clones of this repo — slow, and every hit a duplicate of a hit it
# already reported. `RELEASE.md` is the precedent: this tuple takes files.
SCAN_ROOTS = (
    ".github",
    "RELEASE.md",
    ".claude/scripts",
    "scripts",
    "npm/INTEGRITY.md",
    "npm/README.md",
)


def scan_live_surfaces(needle: str):
    """grep, in Python. The local `grep` is ugrep and disagrees with GNU grep
    about binary files, so a subprocess control would not mean the same thing
    here and in CI. Returns (files_scanned, hits)."""
    hits: List[str] = []
    scanned = 0
    for root in SCAN_ROOTS:
        base = REPO_ROOT / root
        if not base.exists():
            continue
        paths = [base] if base.is_file() else sorted(base.rglob("*"))
        for path in paths:
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            try:
                body = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue  # binary artifact: not a live text surface
            scanned += 1
            for num, line in enumerate(body.splitlines(), 1):
                if needle in line:
                    hits.append(
                        "%s:%d: %s"
                        % (path.relative_to(REPO_ROOT), num, line.strip())
                    )
    return scanned, hits


def test_driver_derives_every_version_string_from_target_base():
    """Zero stale literals — and deliberately NO coupling to the repo's current
    VERSION file. Pinning the driver to VERSION would go red in the one window
    where the driver MUST be ahead of it: the moment TARGET_BASE is set for the
    next release and `bump` has not run yet. A gate that blocks the documented
    path is the failure mode this plan exists to close, not a new instance."""
    text = DRIVER_SRC.read_text(encoding="utf-8")
    m = re.search(r'(?m)^TARGET_BASE="(\d+\.\d+\.\d+)"$', text)
    assert m, "TARGET_BASE is not a bare-semver assignment"
    target = m.group(1)
    offenders = []
    for num, line in enumerate(text.splitlines(), 1):
        if line.strip() == 'TARGET_BASE="%s"' % target:
            continue
        for hit in SEMVER_RX.findall(line):
            # tolerated: a reference to a PAST incident. It is a historical
            # fact and cannot be derived from TARGET_BASE.
            if re.search(r"v%s-rc\.\d+" % re.escape(hit), line):
                continue
            offenders.append("%d: %s" % (num, line.strip()))
    assert not offenders, "version literals not derived from TARGET_BASE:\n%s" % (
        "\n".join(offenders)
    )


@pytest.mark.parametrize(
    "src", [DRIVER_SRC, SITES_SRC], ids=["driver", "site-module"]
)
def test_release_surfaces_make_no_site_count_claim_in_comments(src):
    """The rule is DELETE the count, never correct it: a corrected count is a
    count that goes stale again the next time the table grows. W0 re-pass r2:
    the control scanned only the DRIVER while the site MODULE — the file the
    table actually lives in — had reintroduced counted comments."""
    text = src.read_text(encoding="utf-8")
    offenders = [
        "%d: %s" % (num, line.strip())
        for num, line in enumerate(text.splitlines(), 1)
        if SITE_COUNT_RX.search(line)
    ]
    assert not offenders, "site-count claim in %s:\n%s" % (
        src.name,
        "\n".join(offenders),
    )


def test_driver_attributes_the_publish_to_the_publishing_workflow():
    """Both occurrences. Positional, not a word count: for every "publishes to
    npm" claim the LAST workflow named before it must be npm-publish.yml —
    release.yml is the gate and publishes nothing."""
    text = DRIVER_SRC.read_text(encoding="utf-8")
    claims = list(re.finditer(r"publishes to npm", text))
    assert len(claims) >= 2, (
        "expected the publish claim at both sites, found %d" % len(claims)
    )
    for m in claims:
        before = text[max(0, m.start() - 200):m.start()]
        named = re.findall(r"(npm-publish\.yml|release\.yml)", before)
        assert named, "publish claim names no workflow: ...%s" % before[-100:]
        assert named[-1] == "npm-publish.yml", (
            "publish attributed to %s: ...%s" % (named[-1], before[-140:])
        )


def test_old_driver_name_is_gone_from_live_surfaces():
    """AC-6 control, widened to every live surface that could still point at
    the old driver. Plan evidence (`.claude/plans/PLAN-166/repass-r1/**`,
    `.../debate/**`) is IMMUTABLE and deliberately OUT of scope: a sed there
    would break MANIFEST.sha256 and invalidate the re-pass."""
    # positive control for the instrument itself, first: a needle that IS
    # present must be found, or "no hits" means nothing.
    control_scanned, control_hits = scan_live_surfaces("release.sh")
    assert control_hits, (
        "the scanner found 0 hits for a needle that is definitely present — "
        "it scanned %d files under %s" % (control_scanned, SCAN_ROOTS)
    )

    scanned, hits = scan_live_surfaces(OLD_DRIVER_STEM)
    print(
        "AC-6 control: %d text files scanned under %s; positive control %d hits"
        % (scanned, ", ".join(SCAN_ROOTS), len(control_hits))
    )
    assert not hits, "old driver name on a live surface:\n%s" % "\n".join(hits)
    assert not (LOCAL / (OLD_DRIVER_STEM + ".sh")).exists()
    assert DRIVER_SRC.exists() and os.access(str(DRIVER_SRC), os.X_OK)


# ===========================================================================
# PLAN-177 W0 — the npm/ surfaces: a version nobody watched (P1-2) and an
# "enforced today" guarantee with no step behind it (P1-3).
# ===========================================================================

# The npm docs are DERIVED from SCAN_ROOTS, not re-typed: adding a third npm
# surface up there extends this rule too, and the two lists cannot drift.
# What stays out, and why the predicate is narrow ON PURPOSE:
#   * `npm/SHA256SUMS.txt` records tarball FILENAMES
#     (`ceo-orchestration-<version>.tgz`) — historical data about a build that
#     happened, not a claim about the current release. Flagging it would train
#     whoever hits the red to add an exemption, and an exemption is how a
#     control stops controlling.
#   * `npm/.npmignore` cites past packaging incidents by the version they
#     happened in — same category.
#   * `npm/package.json` is a real bump site with a real oracle
#     (`_release_bump_sites.py` + verify-counts); it is written, not stale.
# Prose in a shipped `.md` is the only one that can go stale silently, which
# is exactly what happened.
NPM_DOC_SURFACES = tuple(
    root for root in SCAN_ROOTS if root.startswith("npm/") and root.endswith(".md")
)
# The one legitimate version literal in an npm doc: the review stamp, itself a
# bump site (`("npm/README.md", STAMP, STAMP_RX)`), so it has an oracle.
_STAMP_LINE_RX = re.compile(r"last-reviewed:\s*\d{4}-\d{2}-\d{2}\s+v\d+\.\d+\.\d+")


def _bare_version_offenders_in_npm_docs(repo_root: Path) -> List[str]:
    """Bare `X.Y.Z` in a scanned npm doc, outside a review stamp. Takes the
    root as an ARGUMENT so the positive control can plant the defect in a tmp
    tree and never write into the repo under test."""
    offenders: List[str] = []
    for rel in NPM_DOC_SURFACES:
        path = repo_root / rel
        if not path.is_file():
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for num, line in enumerate(body.splitlines(), 1):
            if _STAMP_LINE_RX.search(line):
                continue
            for hit in SEMVER_RX.findall(line):
                offenders.append("%s:%d: %s (%s)" % (rel, num, line.strip(), hit))
    return offenders


def test_npm_docs_carry_no_bare_version_literal(tmp_path):
    """P1-2. `npm/INTEGRITY.md` declared its own version and drifted three
    minors behind `VERSION` while `bump --stable` correctly reported a no-op:
    the file is not a bump site and — until this commit — not a scanned
    surface either. The cure is version-NEUTRAL prose, not a new writer row
    (a writer with no oracle is the dead rule `_release_bump_sites.py`
    already refuses to reintroduce)."""
    assert NPM_DOC_SURFACES, "no npm doc is scanned — the P1-2 surface is unwatched"

    # Positive control FIRST, in a throwaway tree, and planted in the SAME
    # relative paths the real scan uses: this proves the SURFACE is covered,
    # not merely that the regex can match a version somewhere. The stamped
    # file rides along because an over-firing control gets exempted away
    # within a release.
    for rel in NPM_DOC_SURFACES:
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "> built and versioned (`VERSION` / `package.json`, "
            "currently 1.0.1).\n"
            "<!-- last-reviewed: 2026-08-05 v1.3.0 -->\n",
            encoding="utf-8",
        )
    planted = _bare_version_offenders_in_npm_docs(tmp_path)
    assert len(planted) == len(NPM_DOC_SURFACES), (
        "positive control did not flag every scanned npm doc exactly once "
        "(stamp line must stay exempt): %s" % planted
    )
    for rel in NPM_DOC_SURFACES:
        assert any(o.startswith(rel + ":") for o in planted), (
            "%s is in SCAN_ROOTS but the planted literal there was not "
            "reported: %s" % (rel, planted)
        )

    offenders = _bare_version_offenders_in_npm_docs(REPO_ROOT)
    assert not offenders, (
        "bare version literal in an npm doc (VERSION is the only authority; "
        "make the prose version-neutral):\n%s" % "\n".join(offenders)
    )


INTEGRITY_DOC = REPO_ROOT / "npm" / "INTEGRITY.md"
# Closed set. A row whose Status is anything else is a red — fail-closed on
# unknown vocabulary, because the way this table decayed the first time was a
# cell that READ like enforcement ("(to-add)", "Release script (Sprint 17
# scope)") without ever being it.
_CONTRACT_STATUSES = ("enforced", "deferred", "operator")
# `<workflow>.yml` in backticks, then the step name in straight quotes. Both
# delimiters are load-bearing: they are what makes the claim parseable at all.
_ENFORCED_RX = re.compile(r'`([^`]+\.yml)`\s+step\s+"([^"]+)"')
# Without a floor, a parser that suddenly matches nothing reports zero
# offenders and the gate passes having checked NOTHING. Two is the smallest
# floor that also keeps a one-row table from satisfying it by accident.
_MIN_ENFORCED_PAIRS = 2


def _yaml_step_names(path: Path) -> List[str]:
    """Every `- name:` in a workflow, unquoted. Compared by EQUALITY at the
    call site: a substring match would accept "Verify VERSION" for a step
    actually called "Verify VERSION matches tag", and substring-vs-exact has
    already cost this repo three incidents in one session."""
    text = path.read_text(encoding="utf-8")
    names = []
    for m in re.finditer(r"(?m)^\s*-\s+name:\s*(.+?)\s*$", text):
        name = m.group(1)
        if len(name) >= 2 and name[0] == name[-1] and name[0] in "\"'":
            name = name[1:-1]
        names.append(name)
    return names


def _contract_rows(doc_text: str) -> List[List[str]]:
    """The `## Contract` table as [control, mechanism, status, where]."""
    m = re.search(r"(?ms)^## Contract\b.*?(?=^## |\Z)", doc_text)
    assert m, "npm/INTEGRITY.md has no `## Contract` section"
    rows = []
    for line in m.group(0).splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 4:
            continue
        if cells[0] == "Control" or set(cells[0]) <= set("- :"):
            continue
        rows.append(cells)
    return rows


def _integrity_enforced_pairs(doc_text: str) -> List[List[str]]:
    """[control, workflow, step] for every `enforced` row. Rows with any other
    Status are not read — a row that claims no enforcement makes no claim to
    check."""
    out: List[List[str]] = []
    for control, _mechanism, status, where in _contract_rows(doc_text):
        if status != "enforced":
            continue
        for workflow, step in _ENFORCED_RX.findall(where):
            out.append([control, workflow, step])
    return out


def _integrity_contract_offenders(doc_text: str, repo_root: Path) -> List[str]:
    """Closed-set Status, plus: every `enforced` row names a workflow that
    exists and a step that exists in it, by exact equality."""
    offenders: List[str] = []
    for control, _mechanism, status, where in _contract_rows(doc_text):
        if status not in _CONTRACT_STATUSES:
            offenders.append(
                "%s: Status %r is outside the closed set %s"
                % (control, status, list(_CONTRACT_STATUSES))
            )
            continue
        if status != "enforced":
            continue
        pairs = _ENFORCED_RX.findall(where)
        if not pairs:
            offenders.append(
                "%s: Status is enforced but `Where enforced` names no "
                "workflow+step in the parseable form — %r" % (control, where)
            )
            continue
        for workflow, step in pairs:
            wf = repo_root / workflow
            if not wf.is_file():
                offenders.append(
                    "%s: names workflow %s, which does not exist"
                    % (control, workflow)
                )
                continue
            if step not in _yaml_step_names(wf):
                offenders.append(
                    "%s: names step %r in %s, which has no such step"
                    % (control, step, workflow)
                )
    return offenders


def test_integrity_contract_rows_name_a_live_step():
    """P1-3. The contract claimed a per-tarball SHA-256 manifest was
    "enforced today" and pointed at `validate.yml (to-add)`: a guarantee whose
    alleged gate could not fail because it did not exist. A row now declares a
    Status from a closed set, and an `enforced` one must name a step that is
    really in the YAML."""
    doc = INTEGRITY_DOC.read_text(encoding="utf-8")
    rows = _contract_rows(doc)
    assert len(rows) >= 5, "Contract table parsed as %d rows" % len(rows)

    pairs = _integrity_enforced_pairs(doc)
    assert len(pairs) >= _MIN_ENFORCED_PAIRS, (
        "only %d enforced (workflow, step) claims parsed — below the floor of "
        "%d. Either the table stopped documenting enforcement, or its format "
        "changed and this gate is now checking nothing."
        % (len(pairs), _MIN_ENFORCED_PAIRS)
    )

    # (a) a renamed step must go red. The fixture is DERIVED from the parsed
    # table, never a hand-typed row literal: an anchor typed here stops
    # matching the day that row is edited, and the control dies quietly.
    step = pairs[0][2]
    renamed = doc.replace('step "%s"' % step, 'step "%s renamed"' % step, 1)
    assert renamed != doc, "rename fixture did not patch the doc"
    renamed_offenders = _integrity_contract_offenders(renamed, REPO_ROOT)
    assert any("renamed" in o for o in renamed_offenders), (
        "control did not flag a row naming a nonexistent step: %s"
        % renamed_offenders
    )

    # (b) a table with NO parseable step claim must go red on the COUNT, not
    # report zero offenders. That is the vacuity failure itself.
    stripped = doc.replace('step "', "step ")
    assert len(_integrity_enforced_pairs(stripped)) < _MIN_ENFORCED_PAIRS, (
        "a table with no parseable step claim still met the floor — the count "
        "check cannot detect vacuity"
    )

    # (c) unknown Status vocabulary must go red, not be waved through.
    unknown = doc.replace("| enforced |", "| mostly enforced |", 1)
    assert unknown != doc, "status fixture did not patch the doc"
    assert any(
        "outside the closed set" in o
        for o in _integrity_contract_offenders(unknown, REPO_ROOT)
    ), "an unknown Status was accepted"

    offenders = _integrity_contract_offenders(doc, REPO_ROOT)
    assert not offenders, "npm/INTEGRITY.md contract row without a live step:\n%s" % (
        "\n".join(offenders)
    )


def test_integrity_unenforced_rows_are_restated_where_the_reader_looks():
    """The escape hatch a closed set alone leaves open: mark everything
    `deferred` and list it nowhere. Every non-enforced row must repeat its
    control name, verbatim and bold, under §Not yet automated — the section a
    reader actually reads."""
    doc = INTEGRITY_DOC.read_text(encoding="utf-8")
    section = re.search(r"(?ms)^## Not yet automated\b.*?(?=^## |\Z)", doc)
    assert section, "npm/INTEGRITY.md has no §Not yet automated section"
    body = section.group(0)
    unenforced = [
        control
        for control, _m, status, _w in _contract_rows(doc)
        if status in ("deferred", "operator")
    ]
    assert unenforced, (
        "no un-enforced row parsed — the honest half of the table is missing, "
        "or the Status column stopped parsing"
    )
    unlisted = [c for c in unenforced if ("**%s**" % c) not in body]
    assert not unlisted, (
        "control(s) marked un-enforced in the table but absent from "
        "§Not yet automated: %s" % unlisted
    )
    # falsifiable: unbolding one bullet must break the match this test makes
    victim = unenforced[0]
    assert ("**%s**" % victim) not in body.replace("**%s**" % victim, victim, 1)


def test_integrity_doc_makes_no_enforced_claim_for_the_tarball_checksum():
    """The narrower half of P1-3, plus the whole-file sweep that followed it.
    `SHA256SUMS.txt` is written by a LOCAL `scripts/install-npm.sh` run, is
    excluded from the package `files:` array, and no workflow materialises a
    `.tgz` to hash — so the consumer recipe this file used to publish was
    impossible, and is REMOVED rather than caveated."""
    doc = INTEGRITY_DOC.read_text(encoding="utf-8")
    header = doc.split("## Contract", 1)[0]
    assert "no** per-tarball" in header or "no per-tarball" in header, (
        "header no longer states that the tarball checksum is absent"
    )
    assert "scripts/install-npm.sh" in doc, (
        "the doc does not attribute SHA256SUMS.txt to its real, local writer"
    )
    assert "sha256sum -c SHA256SUMS.txt" not in doc, (
        "the impossible consumer recipe is back — it cannot run, because "
        "SHA256SUMS.txt is not inside the published package"
    )

    # --- sweep findings: three promises whose referent does not exist ---
    assert not re.search(r"rotation-log\.md`?\s*§\s*NPM", doc), (
        "the doc again points at a rotation-log section that does not exist"
    )
    assert ".well-known/gpg.asc" not in doc, (
        "the doc again advertises a key distribution point this project does "
        "not serve"
    )
    assert not (REPO_ROOT / ".well-known").exists(), (
        "`.well-known/` now exists — re-open the signing-key section"
    )
    for name in ("docs/rotation-log.md", ".claude/trust/owner.asc"):
        if name in doc:
            assert (REPO_ROOT / name).exists(), "doc points at missing %s" % name
    # the reproducible-build row is `deferred` because NO workflow sets the
    # variable. If one ever does, this red is the reminder to re-read the row.
    for workflow in (
        ".github/workflows/validate.yml",
        ".github/workflows/npm-publish.yml",
    ):
        body = (REPO_ROOT / workflow).read_text(encoding="utf-8")
        assert "SOURCE_DATE_EPOCH" not in body, (
            "%s now sets SOURCE_DATE_EPOCH — the reproducible-build row may "
            "have become real" % workflow
        )
    assert "npm packlist gate" in doc, (
        "the doc no longer names the packlist gate that actually runs"
    )

    # the sibling promise, on the manifest itself
    sums = (REPO_ROOT / "npm" / "SHA256SUMS.txt").read_text(encoding="utf-8")
    assert "NOT generated by CI" in sums
    assert "Generated by `.github/workflows/npm-publish.yml`" not in sums

    # PLAN-177 t2 (re-pass rc.4 P2-c): the REGENERATION RECIPE must be able to
    # regenerate. The recipe this file shipped extracted `npm pack --json`'s
    # `.shasum`, which is npm's legacy SHA-1 and carries no filename -- it
    # produces neither the algorithm nor the `<sha256>  <name>` format of the
    # lines below, and under `--dry-run` there is no tarball to hash at all.
    # An operator following it would have written invalid evidence.
    #
    # Command lines are the ones indented as a block (`#` + 3 spaces); prose
    # that NAMES the rejected recipe is deliberately left readable, so the
    # gate reads commands, not the whole file.
    recipe = [
        line for line in sums.splitlines()
        if line.startswith("#") and line[1:].startswith("   ")
    ]
    assert recipe, "the manifest no longer documents any regeneration command"
    assert not any(".shasum" in line for line in recipe), (
        "a regeneration command extracts npm's `.shasum` again -- that is "
        "SHA-1, not SHA-256, and it emits no filename: %s" % recipe
    )
    assert not any("--dry-run" in line for line in recipe), (
        "a regeneration command runs `npm pack --dry-run` -- it writes no "
        "tarball, so there is nothing to hash: %s" % recipe
    )
    assert any(
        ("sha256sum" in line or "shasum -a 256" in line) for line in recipe
    ), "no recipe line names a SHA-256 hasher: %s" % recipe
    assert any(
        ("$TARBALL" in line or '"filename"' in line) for line in recipe
    ), (
        "the recipe never materialises the tarball NAME -- the manifest "
        "format is `<sha256>  <filename>`: %s" % recipe
    )
    # the writer the file attributes itself to must exist AND hash with the
    # algorithm the filename promises (attribution is checked, not trusted).
    writer = REPO_ROOT / "scripts" / "install-npm.sh"
    assert any("install-npm.sh" in line for line in recipe), (
        "the recipe no longer points at the real local writer: %s" % recipe
    )
    assert writer.exists(), "SHA256SUMS.txt names a writer that is not there"
    writer_body = writer.read_text(encoding="utf-8")
    assert "sha256sum" in writer_body or "shasum -a 256" in writer_body, (
        "install-npm.sh no longer computes a SHA-256 -- the attribution in "
        "SHA256SUMS.txt has gone stale"
    )
    # `files:` really does exclude it — the claim above is checked, not trusted
    pkg = json.loads((REPO_ROOT / "npm" / "package.json").read_text(encoding="utf-8"))
    assert not any("SHA256SUMS" in entry for entry in pkg["files"]), (
        "SHA256SUMS.txt now ships in the tarball — re-open the doc, the "
        "un-automated control may have become real"
    )


# ---------------------------------------------------------------------------
# PLAN-177 W0.3 delta (codex P1-4 of the v4 round) — the generic sweep.
#
# The gates above are SUBJECT-BOUND: the table gate checks rows, and the
# checksum gate anchors three named phantom referents. A NEW enforcement
# promise, about some other subject, written into a section nobody watches,
# passes all of them. The original defect is the proof that this is not
# hypothetical: "(3) a per-tarball SHA-256 manifest ... recorded by
# npm-publish.yml at tag cut" was written in the INTRODUCTION, not in a row.
#
# Rule: a claim that a mechanism runs may live in exactly two places — a
# Contract table row (machine-checked by
# test_integrity_contract_rows_name_a_live_step) or §Not yet automated (tied
# to the table's un-enforced rows by
# test_integrity_unenforced_rows_are_restated_where_the_reader_looks).
# Anywhere else it is answerable to nothing, and is a red.
#
# PREDICATE CHOICE (the honest part). This is a closed VOCABULARY list with
# NO negation exemption, and both halves were chosen from evidence, not taste:
#
#   * An earlier draft tolerated a phrase when a negation appeared within ~120
#     chars. Probing the real file showed that exemption firing by ACCIDENT —
#     "MUST satisfy" was excused by a "not" belonging to the next paragraph,
#     and "fail-closes" by the "not" inside "does not verify". An exemption
#     that triggers on unrelated words is not an exemption, it is a hole. So
#     the prose was cured instead (PLAN-177 W0.3 delta: the intro now points
#     at the table rather than enumerating mechanisms, and the tag-signing
#     paragraph cites SECURITY.md as the authority instead of restating the
#     gate), and the rule became absolute. Zero occurrences today: the sweep
#     needs no exemption, so it has none.
#   * The list is deliberately NARROW: phrases that assert a mechanism is in
#     force. Bare "verify" is absent on purpose — the file legitimately tells
#     a reader to `Verify locally with gpg --import ...`, an instruction, not
#     a claim about the pipeline. "verifies"/"is verified" ARE listed: those
#     are the file speaking about what the pipeline does.
#     A broad list that has to be switched off is worth less than a narrow
#     one that stays on.
#
# Matching is on word boundaries after normalization. Substring matching was
# tried first and reported "asserted by" inside "asserted byte-for-byte" — the
# substring-vs-exact class, for the fourth time in this plan.
_ENFORCEMENT_VOCAB = (
    "enforced today",
    "is enforced",
    "are enforced",
    "enforced by",
    "enforced at",
    "every tag publish",
    "recorded by",
    "is verified",
    "are verified",
    "verifies",
    "must satisfy",
    "guarantees",
    "is guaranteed",
    "are guaranteed",
    "asserted by",
    "checked by",
    "gated by",
    "fails closed",
    "fail closes",
    "asserts",
    "ensures",
    "is signed",
    "are signed",
)


def _normalize_prose(text: str) -> str:
    """Lowercase; drop markdown emphasis and code ticks; hyphens to spaces;
    collapse whitespace. `**Fails Closed**`, `fails-closed` and `fails closed`
    normalize the same way, so a claim cannot hide behind formatting."""
    text = text.lower()
    for ch in ("*", "`", "_"):
        text = text.replace(ch, "")
    text = text.replace("-", " ")
    return re.sub(r"\s+", " ", text)


def _prose_outside_the_declared_zones(doc_text: str) -> str:
    """Everything that is neither a Contract table row nor §Not yet
    automated — the surfaces where a mechanism claim answers to nothing."""
    body = re.sub(r"(?ms)^## Not yet automated\b.*?(?=^## |\Z)", "", doc_text)
    return "\n".join(
        line for line in body.splitlines() if not line.strip().startswith("|")
    )


def _enforcement_vocabulary_offenders(doc_text: str) -> List[str]:
    norm = _normalize_prose(_prose_outside_the_declared_zones(doc_text))
    offenders = []
    for phrase in _ENFORCEMENT_VOCAB:
        for m in re.finditer(r"\b%s\b" % re.escape(phrase), norm):
            offenders.append(
                "%r outside the declared zones: ...%s..."
                % (phrase, norm[max(0, m.start() - 70) : m.end() + 70])
            )
    return offenders


def test_integrity_prose_states_no_mechanism_outside_the_declared_zones():
    """Generic negative sweep: no enforcement vocabulary anywhere in
    npm/INTEGRITY.md except a Contract table row or §Not yet automated. Where
    the earlier gates ask "is this row honest?", this one asks "is this claim
    even standing somewhere that can be checked?" — the question the file
    failed on the day it shipped."""
    doc = INTEGRITY_DOC.read_text(encoding="utf-8")
    assert _ENFORCEMENT_VOCAB, "the vocabulary is empty; the sweep checks nothing"

    # The sweep must be looking at the right text: intro present, table absent.
    swept = _prose_outside_the_declared_zones(doc)
    assert "Integrity contract for the" in swept, (
        "the introduction fell out of the swept zone — zone-stripping is eating "
        "the prose it exists to watch"
    )
    assert "| enforced |" not in swept, "the Contract table was not stripped"
    assert len(swept) > len(doc) // 3, (
        "swept prose is %d chars of a %d-char file — the zones swallowed it"
        % (len(swept), len(doc))
    )

    # (a) NEGATIVE control FIRST, deliberately: today's text passes on its own
    # merits. The order matters and was learned the hard way — the controls
    # below build their fixtures FROM the live file, so when the file itself
    # carries a planted defect they fail first and the red names the fixture
    # instead of the defect. Asserting cleanliness up front means a dirty file
    # always reds on the assertion that describes what is actually wrong.
    # Vacuity is not the risk here: (b) proves the instrument can still fail.
    offenders = _enforcement_vocabulary_offenders(doc)
    assert not offenders, (
        "npm/INTEGRITY.md states a mechanism outside the Contract table and "
        "§Not yet automated. Move the claim into a table row (with a step the "
        "YAML really has) or into §Not yet automated:\n%s" % "\n".join(offenders)
    )

    # (b) positive control: the historical claim restored to the introduction.
    # The fixture INSERTS a paragraph after the title rather than rewriting
    # today's wording — an anchor on current prose stops matching the moment
    # that prose is edited, and then the control fails for the wrong reason.
    title, _, rest = doc.partition("\n")
    claim = (
        "The integrity controls enforced today are: (1) the `install.sh` "
        "self-SHA trailer, and (2) a per-tarball SHA-256 manifest "
        "(`npm/SHA256SUMS.txt`) recorded by `npm-publish.yml` at tag cut."
    )
    relapse = "%s\n\n%s\n%s" % (title, claim, rest)
    assert relapse != doc, "relapse fixture did not patch the doc"
    relapse_offenders = _enforcement_vocabulary_offenders(relapse)
    assert any("enforced today" in o for o in relapse_offenders), (
        "an enforcement claim in the introduction went unseen: %s"
        % relapse_offenders
    )
    assert any("recorded by" in o for o in relapse_offenders), (
        "the attribution half of the claim went unseen: %s" % relapse_offenders
    )

    # (c) scope control: the SAME sentence inside §Not yet automated is NOT an
    # offender. This is the predicate as documented, not a global grep — that
    # section is where honest prose about absence has to be able to use these
    # words. Its own honesty is held by the restatement test above; a claim
    # parked there is the residual gap, and it is a narrow, watched one.
    marker = "## Not yet automated"
    assert marker in doc
    parked = doc.replace(marker, "%s\n\n%s" % (marker, claim), 1)
    assert not _enforcement_vocabulary_offenders(parked), (
        "the sweep is a global grep, not a zone rule — it flagged text inside "
        "a declared zone"
    )


# --------------------------------------------------------------------------
# Supply-chain honesty: the two claims that survive being corrected in one file
#
# The previous revision of the SLSA gate read `README.md` and nothing else. It
# was green while `npm/README.md` — the README an npm consumer actually
# RECEIVES, it is in package.json `files` — still promised "SLSA 3 provenance",
# and while README.pt-BR, INSTALL.md and both QUICKSTARTs repeated Level 3 and
# a checksum coverage the release does not have (repass-rc4 part 2, P1 §2).
# A single-file gate cannot see that class, so the surface list below is
# EXPLICIT, and `_live_doc_surfaces()` re-derives the population from the repo
# so a NEW document carrying either claim also lands in front of the gate.
#
# `.claude/**` is deliberately outside the population: plans, debates and
# archived verdicts are historical records, and they have to be able to quote a
# false claim verbatim without turning this gate red.
# --------------------------------------------------------------------------

SUPPLY_CHAIN_HONESTY_SURFACES = (
    "README.md",
    "README.pt-BR.md",
    "npm/README.md",
    "npm/INTEGRITY.md",
    "INSTALL.md",
    "SECURITY.md",
    "SUPPORT.md",
    "SBOM.md",
    "docs/QUICKSTART.md",
    "docs/QUICKSTART.pt-BR.md",
    "docs/CTO-GUIDE.md",
    "docs/threat-model.md",
)

# "SLSA 3", "SLSA-3", "SLSA Level 3", "SLSA L3", "SLSA provenance L3" and
# "provenance (SLSA L3)" all normalise to the same false claim. The earlier
# pattern only caught the first three, which is why `SBOM.md` ("SLSA L3") and
# `docs/QUICKSTART.md` ("SLSA provenance L3") were invisible to it.
_SLSA_LEVEL3_CLAIM = re.compile(
    r"SLSA[\s\-]*(?:provenance[\s\-]*)?(?:Level[\s\-]*|L)?3\b"
    r"|(?:provenance|attestation)[\s\-]*(?:Level[\s\-]*|L)3\b",
    re.IGNORECASE,
)

# Plural = aggregate. Release checksum coverage is `install.sh` alone
# (SECURITY.md §How to verify what you install); "ships SHA-256 checksums"
# promises a SHA256SUMS that no workflow produces.
_CHECKSUM_AGGREGATE_CLAIM = re.compile(
    r"SHA-?256\s+checksums|checksums\s+SHA-?256", re.IGNORECASE
)


def _live_doc_surfaces() -> List[Path]:
    """Root-level, `docs/` and `npm/` markdown — every document a reader or an
    npm consumer meets. Deliberately NOT `.claude/**` (see the block comment)."""
    found = sorted(REPO_ROOT.glob("*.md"))
    for sub in ("docs", "npm"):
        base = REPO_ROOT / sub
        if base.exists():
            found += sorted(base.rglob("*.md"))
    return found


def test_slsa_and_checksum_claims_are_true_on_every_shipped_surface():
    """The npm consumer reads `npm/README.md`; the Portuguese reader reads
    `README.pt-BR.md`. Correcting the root README alone left both promising a
    Level the pipeline never reaches. The gate now runs over an explicit list
    AND over every live doc, so neither a missed translation nor a new file can
    carry the claim silently."""
    surfaces = {p.relative_to(REPO_ROOT).as_posix(): p for p in _live_doc_surfaces()}

    # (a) The explicit list is not allowed to name a file that stopped
    # existing: a surface silently dropped from the repo is a gate that
    # quietly narrows.
    missing = [s for s in SUPPLY_CHAIN_HONESTY_SURFACES if s not in surfaces]
    assert not missing, "declared honesty surfaces that no longer exist: %s" % missing

    offenders: List[str] = []
    for rel, path in surfaces.items():
        text = path.read_text(encoding="utf-8")
        for m in _SLSA_LEVEL3_CLAIM.finditer(text):
            # Tolerance is scoped to what FOLLOWS the mention, never to the
            # line: the honest sentence names Level 2 and disclaims Level 3 in
            # one breath, so a line-wide exemption would let the false claim
            # ride along beside its own disclaimer. The window is 120 chars
            # because the live disclaimer parenthesises its reason
            # ("(hermetic build + two-party review) is out of scope") — at the
            # old width of 40 the only honest Level-3 sentence in the repo
            # would have been the gate's first false positive.
            tail = text[m.end():m.end() + 120]
            if "out of scope" in tail or "fora de escopo" in tail:
                continue
            offenders.append(
                "%s: ...%s..."
                % (rel, text[max(0, m.start() - 60):m.end() + 40].strip().replace("\n", " "))
            )
        for m in _CHECKSUM_AGGREGATE_CLAIM.finditer(text):
            offenders.append(
                "%s: ...%s..."
                % (rel, text[max(0, m.start() - 70):m.end() + 30].strip().replace("\n", " "))
            )

    assert not offenders, (
        "shipped docs claim SLSA Level 3 and/or aggregate release checksums; "
        "the pipeline reaches Level 2 (`npm publish --provenance`) and the "
        "release checksum covers `install.sh` only:\n%s" % "\n".join(offenders)
    )

    # (b) Positive statement, on the two most-read surfaces: silence about the
    # level is not honesty either. The npm README is named explicitly because
    # it is the one that travels inside the tarball.
    for rel in ("README.md", "npm/README.md"):
        text = surfaces[rel].read_text(encoding="utf-8")
        assert "SLSA **Level 2**" in text or "SLSA Level 2" in text, (
            "%s no longer states the level the pipeline reaches" % rel
        )


# --------------------------------------------------------------------------
# The npm signature recipe has to audit the thing the reader just installed
#
# `npm audit signatures` reads the CURRENT project's dependency tree. It takes
# no package-selecting positional (a trailing package name is ignored), and it
# refuses global installs outright with EAUDITGLOBAL. So the documented pairing
# of `npm install -g` (or `npm exec` / `npx`, which leave no dependency behind)
# with `npm audit signatures` verified nothing the reader had just installed —
# it audited whatever directory they happened to be standing in, and could
# return a confident green having examined a different tree entirely.
# Both behaviours were observed directly against npm 11.16.0 (repass-rc4
# part 2, P1 §3); the honest routes are the npm provenance panel, or a local
# project install followed by a BARE `npm audit signatures`.
# --------------------------------------------------------------------------

_AUDIT_SIGNATURES = re.compile(r"npm\s+audit\s+signatures")
# Installs that `npm audit signatures` cannot reach: global, or exec/npx
# (ephemeral — nothing is left in a dependency tree to audit).
_UNAUDITABLE_INSTALL = re.compile(
    r"npm\s+(?:i|install)\b[^\n]*?(?:\s-g\b|\s--global\b)|npm\s+exec\b|\bnpx\b"
)
# A trailing token that is neither a comment nor a flag: npm ignores it, and
# the reader believes it selected a package. `#` is excluded so the honest
# recipes may explain themselves in a trailing comment; `-` is excluded so a
# flag is diagnosed by the flag rule below and not mislabelled a positional.
_AUDIT_POSITIONAL = re.compile(r"npm\s+audit\s+signatures\s+(?![#-])([^\s`|#\n]+)")
_AUDIT_GLOBAL_FLAG = re.compile(
    r"npm\s+audit\s+signatures[^\n]*(?:\s-g\b|\s--global\b)"
)


def _recipe_units(text: str) -> List[tuple]:
    """(label, body) for each fenced code block, and for each line outside one.

    A recipe is what a reader copies, and they copy a whole code block — so the
    block, not the line, is the unit in which "install here, audit there" has
    to be judged. Prose lines are units of their own so a one-line table row
    (the shape `SUPPORT.md` used) is still examined."""
    units: List[tuple] = []
    block: Optional[List] = None
    for num, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith("```"):
            if block is None:
                block = [num, []]
            else:
                units.append(("block@%d" % block[0], "\n".join(block[1])))
                block = None
            continue
        if block is not None:
            block[1].append(line)
        else:
            units.append(("line@%d" % num, line))
    if block is not None:  # unterminated fence: judge what we collected
        units.append(("block@%d" % block[0], "\n".join(block[1])))
    return units


def test_documented_npm_signature_recipe_matches_what_npm_audits():
    """Every documented `npm audit signatures` has to be reachable by npm.

    A recipe offends when its unit pairs the command with an install npm cannot
    audit, passes a positional npm ignores, or passes `--global`, which npm
    rejects. Naming `EAUDITGLOBAL` in the unit is the tolerance: a document is
    free — and encouraged — to put the global install next to the command in
    order to say that the command does NOT reach it."""
    offenders: List[str] = []
    units_examined = 0
    for path in _live_doc_surfaces():
        rel = path.relative_to(REPO_ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        if not _AUDIT_SIGNATURES.search(text):
            continue
        for label, unit in _recipe_units(text):
            if not _AUDIT_SIGNATURES.search(unit):
                continue
            units_examined += 1
            faults = []
            if _UNAUDITABLE_INSTALL.search(unit) and "EAUDITGLOBAL" not in unit:
                faults.append(
                    "pairs the audit with an install npm cannot audit "
                    "(global, or exec/npx leaving no dependency behind)"
                )
            positional = _AUDIT_POSITIONAL.search(unit)
            if positional:
                faults.append(
                    "passes the positional %r, which npm ignores — the audit "
                    "still reads the current project" % positional.group(1)
                )
            if _AUDIT_GLOBAL_FLAG.search(unit):
                faults.append("passes --global, which npm rejects (EAUDITGLOBAL)")
            if faults:
                offenders.append(
                    "%s %s: %s\n    %s"
                    % (rel, label, "; ".join(faults), unit.strip()[:160])
                )

    # Vacuity guard: the sweep is worthless if it found no recipe to judge.
    assert units_examined >= 5, (
        "only %d recipe units examined — the sweep lost sight of the docs it "
        "exists to watch" % units_examined
    )
    assert not offenders, (
        "documented `npm audit signatures` recipes do not audit what the "
        "reader installed:\n%s" % "\n\n".join(offenders)
    )


def test_checklist_attributes_repo_exhaustiveness_to_the_scanner():
    """The checklist read as a census OF THE REPOSITORY while it was a census
    of the driver's TABLE — which is why `npm/INTEGRITY.md` could hold a stale
    version and the checklist still be, on its own terms, true. It now says
    which instrument answers for the repo, and names the roots that
    instrument scans; adding a root without documenting it goes red here."""
    text = (REPO_ROOT / ".github/release-checklist.md").read_text(encoding="utf-8")
    assert "SCAN_ROOTS" in text, "the checklist names no repo-wide instrument"
    missing = [root for root in SCAN_ROOTS if root not in text]
    assert not missing, "SCAN_ROOTS entries undocumented in the checklist: %s" % missing
    # the assertion above can only mean something if it is falsifiable — a root
    # that is NOT in the tuple must be absent from the prose.
    assert "docs/formal-verification" not in text


def test_checklist_documents_the_new_driver_and_the_await_gate_recovery():
    text = (REPO_ROOT / ".github/release-checklist.md").read_text(encoding="utf-8")
    for phase in ("preflight", "bump", "tag"):
        assert "release.sh %s" % phase in text, phase
    assert "await-release-gate" in text
    # the recovery route is a re-run, explicitly NOT a delete + re-tag
    assert "re-rodar o job" in text
    assert "deletar/re-criar a tag" in text
    # and the manual approval is the last human chance, not a second opinion
    assert "última chance" in text


def test_checklist_enumerates_the_verdict_fields_the_tag_guard_requires():
    """The tag guard enforces FOUR verdict fields; the canonical template
    (.claude/governance/pair-rail-verdict-template.md, W1 ceremony scope)
    still documents only parent_sha. Until that patch lands, the checklist is
    the authoring surface — a contract enforced by code but documented on no
    authoring surface is how the first rc.2 verdict dies at E_VERDICT."""
    text = (REPO_ROOT / ".github/release-checklist.md").read_text(encoding="utf-8")
    for field in (
        "parent_sha",
        "delta_allowlist",
        "delta_manifest",
        "delta_manifest_sha256",
    ):
        assert field in text, "checklist does not name the %r field" % field


def test_install_md_describes_the_current_pair_rail_migration():
    text = (REPO_ROOT / "INSTALL.md").read_text(encoding="utf-8")
    assert "150 → 210 s, ADR-110-AMEND-2" in text
    assert "ADR-110-AMEND-1" not in text


# ===========================================================================
# PLAN-177 W0.1 (P1-4) -- the pair-rail DECISION gate
# ===========================================================================
# The re-pass of 2026-08-12 found that BOTH release rails read the verdict
# envelope for pinning, TTL, anchor and delta, and NEITHER read the decision:
# a cross-model NO-GO returned "OK: verdict ... valid" / exit 0 from the
# server-side validator, release-gate went green, and only the Owner running
# OWNER-GA-CUT.sh stood between a negative review and an irreversible publish.
#
# CF-3 asymmetry, restated here because it decides what each control PROVES:
# step 15 carries continue-on-error under CEO_PAIR_RAIL_VERDICT_OPTIONAL=1, so
# the validator control is a UNIT control over defence in depth; the control
# that stands for enforcement in every mode is the tag-guard one below.
_VALIDATOR_INPUTS_HASH_CACHE = {}

# Anchors on the DIAGNOSTIC, not just the exit code: a gate that fires for the
# wrong reason is a dead probe wearing a green badge (S-lesson: a control that
# cannot fail proves nothing).
_ACCEPTED_SET_TEXT = "{GO, GO-WITH-CONDITIONS}"
_DECISION_REFUSED = "not in " + _ACCEPTED_SET_TEXT
_CI_DUPLICATE_DIAGNOSTIC = "verdict decision declared more than once"
_GUARD_DUPLICATE_DIAGNOSTIC = "declares the decision"

# Value-shaped refusals. `GO | NO-GO | GO-WITH-CONDITIONS` is the LITERAL of
# pair-rail-verdict-template.md:13 -- an envelope copied from the template
# without filling the field in.
_REFUSED_DECISIONS = [
    ["NO-GO"],
    [],
    ["MAYBE"],
    [""],
    ["go"],
    ["no-go"],
    ["GO WITH CONDITIONS"],
    ["GO | NO-GO | GO-WITH-CONDITIONS"],
    # Re-pass rc.4 t3 P1: `#` WITHOUT preceding whitespace is NOT a YAML
    # comment — these are single unknown values, not GO + comment.
    ["GO#NO-GO"],
    ["GO-WITH-CONDITIONS#NO-GO"],
    # Re-pass rc.4 t5 P1: Unicode whitespace must stay attached to the
    # VALUE — `GO<U+00A0>` is not the exact authorizing token.
    ["GO\u00a0"],
    ["\u00a0GO"],
    ["GO-WITH-CONDITIONS\u00a0"],
]
_REFUSED_IDS = [
    "no-go", "absent", "unknown", "empty", "lowercase", "lower-no-go",
    "spaced", "template-literal",
    "hash-glued-no-go", "hash-glued-gwc",
    "trailing-nbsp", "leading-nbsp", "gwc-trailing-nbsp",
]


@pytest.fixture()
def ci_env(tmp_path):
    """Subprocess env for the server-side validator runs.

    Built fresh per test and never by mutating os.environ, so xdist workers
    cannot leak steering vars into one another -- the same rule the rest of
    this file follows through _env().
    """
    home = tmp_path / "vhome"
    (home / "gnupg").mkdir(parents=True, exist_ok=True)
    return _env(home)


def _repo_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(REPO_ROOT), stdout=subprocess.PIPE, universal_newlines=True,
    ).stdout.strip()


def _live_inputs_hash() -> str:
    """Recompute inputs_hash in THIS checkout, with the validator own manifest.

    Never copied from a real envelope (codex P2-2): the validator is itself
    listed in pair-rail-inputs-hash-manifest.txt, so the P1-4 cure CHANGES the
    expected hash. A hardcoded hex would make the green cases fail on
    inputs_hash and the test would prove nothing about the decision.
    """
    key = "inputs_hash"
    if key not in _VALIDATOR_INPUTS_HASH_CACHE:
        _VALIDATOR_INPUTS_HASH_CACHE[key] = validator.compute_inputs_hash(
            REPO_ROOT, GOVERNANCE / "pair-rail-inputs-hash-manifest.txt"
        )
    return _VALIDATOR_INPUTS_HASH_CACHE[key]


def _live_tool_versions() -> Dict[str, str]:
    """codex pins read from the LIVE governance files, not from memory.

    Both pins drift by ceremony (the semver range has been widened four times);
    deriving them keeps this control testing the decision instead of decaying
    into a pin-drift alarm.
    """
    min_v, _max_v = validator.parse_pin_range(GOVERNANCE / "codex-cli-pin.txt")
    assert min_v, "fixture broke: no semver range in codex-cli-pin.txt"
    manifest = json.loads(
        (GOVERNANCE / "codex-cli-pin-manifest.json").read_text(encoding="utf-8")
    )
    triple = sorted(manifest["payloads"])[0]
    return {
        "codex_cli": min_v,
        "codex_target_triple": triple,
        "codex_payload_sha256": manifest["payloads"][triple]["sha256"],
    }


def _write_live_shaped_verdict(
    path: Path, tag: str, decisions: Sequence[str], parent: str
) -> None:
    """A verdict envelope the LIVE governance files accept end to end.

    `decisions` is a SEQUENCE so the fixture can express the three shapes the
    gate must separate: zero lines (absent), one line (normal), two lines (the
    last-wins override). Values are written verbatim -- a malformed or unknown
    token reaches the validator exactly as authored.
    """
    tv = _live_tool_versions()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    lines = ["# Pair-Rail Verdict -- fixture", "", "```yaml"]
    lines += [_decision_line(d).rstrip("\n") for d in decisions]
    lines += [
        "generated_at: %sZ" % now,
        "ttl_hours: 24",
        "parent_sha: %s" % parent,
        "release_tag: %s" % tag,
        "inputs_hash: %s" % _live_inputs_hash(),
        "tool_versions:",
        "  codex_cli: %s" % tv["codex_cli"],
        "  codex_target_triple: %s" % tv["codex_target_triple"],
        "  codex_payload_sha256: %s" % tv["codex_payload_sha256"],
        "gpg_signature: -----BEGIN PGP SIGNATURE----- fixture-not-a-signature",
        "```",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _run_ci_validator(tmp_path, env, decisions: Sequence[str], bind_parent: bool):
    """Run the server-side validator with the LITERAL step-15 argv.

    Source of the argv: .github/workflows/release.yml, job release-gate.

    bind_parent=False is the --parent-sha "" shape of
    CEO_PAIR_RAIL_VERDICT_OPTIONAL=1. In THAT mode the step also carries
    continue-on-error, so this variant is a UNIT test of the validator, not a
    claim about the pipeline: what blocks a release in transition mode is
    _release_tag_guard.py delta (see the tag-guard controls below).
    """
    tag = "v0.0.0-plan177-decision-gate"
    parent = _repo_head()
    verdict_file = tmp_path / "pair-rail-verdict-fixture.md"
    _write_live_shaped_verdict(verdict_file, tag, decisions, parent)
    argv = [
        sys.executable, str(VALIDATOR_SRC),
        "--verdict-file", str(verdict_file),
        "--parent-sha", parent if bind_parent else "",
        "--release-tag", tag,
        "--max-age-hours", "24",
        "--recompute-inputs-hash",
        "--codex-cli-pin-file", ".claude/governance/codex-cli-pin.txt",
        "--codex-cli-binary-sha256-file",
        ".claude/governance/codex-cli-binary-sha256.txt",
        "--codex-pin-manifest-file",
        ".claude/governance/codex-cli-pin-manifest.json",
        "--inputs-hash-paths-file",
        ".claude/governance/pair-rail-inputs-hash-manifest.txt",
    ]
    return run(argv, REPO_ROOT, env)


@pytest.mark.parametrize("bind_parent", [True, False], ids=["bound", "unbound"])
@pytest.mark.parametrize("decisions", _REFUSED_DECISIONS, ids=_REFUSED_IDS)
def test_ci_validator_stops_a_non_authorizing_decision(
    tmp_path, ci_env, decisions, bind_parent
):
    proc = _run_ci_validator(tmp_path, ci_env, decisions, bind_parent)
    assert proc.returncode == validator.EXIT_VERDICT_INVALID, (
        "step-15 argv + decision=%r returned %d -- this is the P1: the "
        "server-side validator authorised a release it never judged.\n%s%s"
        % (decisions, proc.returncode, proc.stdout, proc.stderr)
    )
    assert _DECISION_REFUSED in proc.stderr, (
        "red for the wrong reason -- the failure must name the DECISION and "
        "the accepted set, not a downstream mismatch: %s" % proc.stderr
    )
    # ASCII-only trim, mirroring the reader (t5 P1): a Unicode strip() here
    # would normalize the NBSP the diagnostic is REQUIRED to quote.
    observed = decisions[0].strip(" \t") if decisions else "<absent>"
    if decisions and not decisions[0].strip():
        observed = "<non-string:dict>"
    assert "'%s'" % observed in proc.stderr, (
        "the diagnostic must quote the value it OBSERVED (%r): %s"
        % (observed, proc.stderr)
    )
    assert "OK: verdict" not in proc.stdout


@pytest.mark.parametrize("bind_parent", [True, False], ids=["bound", "unbound"])
def test_ci_validator_stops_a_duplicated_decision_key(tmp_path, ci_env, bind_parent):
    """Both readers are last-wins: NO-GO followed by GO parses as GO. An
    envelope with two decision lines is not a verdict, it is an override."""
    proc = _run_ci_validator(tmp_path, ci_env, ["NO-GO", "GO"], bind_parent)
    assert proc.returncode == validator.EXIT_VERDICT_INVALID, (
        "a duplicated verdict key was accepted -- last-wins parsing turned a "
        "NO-GO into a GO.\n%s%s" % (proc.stdout, proc.stderr)
    )
    assert _CI_DUPLICATE_DIAGNOSTIC in proc.stderr, proc.stderr
    assert "OK: verdict" not in proc.stdout


# PLAN-177 t2 (re-pass rc.4 P1-a) -- the GRAMMAR the two rails share.
#
# `verdict : NO-GO` is valid YAML and last-wins under a real parser. The
# server validator strips the key, so it counted TWO declarations; the local
# tag guard's regex required the colon immediately after the name, so it
# counted ONE and parsed GO -- and the local guard is the rail with no escape
# hatch. The first round of controls could not see this: every fixture line
# was built as `"verdict: %s"`, which can only produce canonical keys.
#
# Cured semantics (identical in both files): non-canonical top-level syntax
# is REFUSED. So the duplicate variants are red for the SHAPE, and the single
# non-canonical key is red too -- an authorizing decision must be spelled the
# one way the template spells it.
_NONCANONICAL_DIAGNOSTIC = "non-canonical top-level key syntax"
_NONCANONICAL_DECISIONS = [
    [("verdict ", "NO-GO"), "GO"],
    [("verdict\t", "NO-GO"), "GO"],
    [("verdict ", "GO")],
    [("verdict\t", "GO")],
    # Re-pass rc.4 t2 P1: an INDENTED CONTINUATION line after the scalar —
    # valid YAML resolving to the non-authorizing scalar "GO NO-GO", which
    # both minimal readers previously read as `GO` (indented lines were
    # unconditionally skipped). Written verbatim by _decision_line.
    ["GO\n  NO-GO"],
]
_NONCANONICAL_IDS = [
    "space-before-colon-duplicate", "tab-before-colon-duplicate",
    "space-before-colon-alone", "tab-before-colon-alone",
    "indented-continuation",
]


@pytest.mark.parametrize("bind_parent", [True, False], ids=["bound", "unbound"])
@pytest.mark.parametrize("decisions", _NONCANONICAL_DECISIONS, ids=_NONCANONICAL_IDS)
def test_ci_validator_refuses_a_noncanonical_decision_key(
    tmp_path, ci_env, decisions, bind_parent
):
    proc = _run_ci_validator(tmp_path, ci_env, decisions, bind_parent)
    assert proc.returncode == validator.EXIT_VERDICT_INVALID, (
        "non-canonical key %r returned %d -- the two rails parse this file "
        "with different grammars, so any shape they can read differently "
        "must be refused, not guessed.\n%s%s"
        % (decisions, proc.returncode, proc.stdout, proc.stderr)
    )
    assert _NONCANONICAL_DIAGNOSTIC in proc.stderr, (
        "red for the wrong reason -- the refusal must name the SHAPE: %s"
        % proc.stderr
    )
    assert proc.returncode != validator.EXIT_INFRA_ERROR
    assert "Traceback" not in proc.stderr, proc.stderr
    assert "OK: verdict" not in proc.stdout


@pytest.mark.parametrize("bind_parent", [True, False], ids=["bound", "unbound"])
@pytest.mark.parametrize("decision", ["GO", "GO-WITH-CONDITIONS"])
def test_ci_validator_admits_an_authorizing_decision(
    tmp_path, ci_env, decision, bind_parent
):
    proc = _run_ci_validator(tmp_path, ci_env, [decision], bind_parent)
    assert _DECISION_REFUSED not in proc.stderr, (
        "an authorizing decision was stopped BY THE DECISION GATE -- the "
        "closed set is wrong: %s" % proc.stderr
    )
    assert _CI_DUPLICATE_DIAGNOSTIC not in proc.stderr, proc.stderr
    assert proc.returncode == validator.EXIT_OK, (
        "decision %r passed the DECISION gate but the run failed a LATER "
        "check -- that is fixture drift (pins, TTL, inputs_hash), not the "
        "gate under test.\n%s%s" % (decision, proc.stdout, proc.stderr)
    )


def test_a_malformed_decision_is_invalid_never_infra(tmp_path, ci_env):
    """CF-1: exit 3 (INVALID), never 1 (INFRA) and never a traceback.

    The distinction is load-bearing: release.yml routes INFRA through
    CEO_PAIR_RAIL_VERDICT_OPTIONAL, so a malformed decision leaving by the
    infra door would be waivable by a repository variable.
    """
    for decisions in ([""], [], ["NO-GO", "GO"]):
        proc = _run_ci_validator(tmp_path, ci_env, decisions, True)
        assert proc.returncode == validator.EXIT_VERDICT_INVALID, (
            "%r left by the wrong door (exit %d): %s"
            % (decisions, proc.returncode, proc.stderr)
        )
        assert proc.returncode != validator.EXIT_INFRA_ERROR
        assert "Traceback" not in proc.stderr, proc.stderr


def test_the_two_rails_share_one_closed_set_of_decisions():
    """The tuple is duplicated on purpose (separate processes, separate
    machines, neither a dependency of the other); this is the gate that keeps
    the two copies literally identical."""
    assert validator.ACCEPTED_DECISIONS == ("GO", "GO-WITH-CONDITIONS")
    assert tag_guard.ACCEPTED_DECISIONS == validator.ACCEPTED_DECISIONS
    assert (
        "{%s}" % ", ".join(validator.ACCEPTED_DECISIONS) == _ACCEPTED_SET_TEXT
    )
    for refused in ("NO-GO", "no-go", "go", "GO ", "", "MAYBE"):
        assert refused not in validator.ACCEPTED_DECISIONS


@pytest.mark.parametrize("decisions", _REFUSED_DECISIONS, ids=_REFUSED_IDS)
@pytest.mark.parametrize("tag", ["v1.3.0-rc.2", "v1.3.0"])
def test_delta_refuses_to_cut_a_tag_on_a_non_authorizing_verdict(synth, tag, decisions):
    """The rail that enforces in EVERY mode (CF-3). Unconditional across rc and
    stable, like the post-review-file assert: an rc cut on a NO-GO becomes the
    unreviewed baseline of the GA."""
    arm_verdict(synth, tag, verdict=decisions)
    proc = guard(synth, "delta", "--repo", str(synth["repo"]), "--tag", tag)
    assert proc.returncode == tag_guard.E_DECISION, proc.stdout + proc.stderr
    assert _DECISION_REFUSED in proc.stderr, proc.stderr
    assert tag_guard.E_DECISION not in (
        0, tag_guard.E_VERDICT, tag_guard.E_DELTA, tag_guard.E_PARENT_NOT_ANCESTOR,
    )


@pytest.mark.parametrize("tag", ["v1.3.0-rc.2", "v1.3.0"])
def test_delta_refuses_a_duplicated_decision_key(synth, tag):
    arm_verdict(synth, tag, verdict=["NO-GO", "GO"])
    proc = guard(synth, "delta", "--repo", str(synth["repo"]), "--tag", tag)
    assert proc.returncode == tag_guard.E_DECISION, proc.stdout + proc.stderr
    assert _GUARD_DUPLICATE_DIAGNOSTIC in proc.stderr, proc.stderr


@pytest.mark.parametrize("decisions", _NONCANONICAL_DECISIONS, ids=_NONCANONICAL_IDS)
@pytest.mark.parametrize("tag", ["v1.3.0-rc.2", "v1.3.0"])
def test_delta_refuses_a_noncanonical_decision_key(synth, tag, decisions):
    """The rail with no escape hatch, on the exact shape that slipped past it:
    `verdict : NO-GO` was invisible to this reader's regex, so the following
    `verdict: GO` was the only declaration it saw."""
    arm_verdict(synth, tag, verdict=decisions)
    proc = guard(synth, "delta", "--repo", str(synth["repo"]), "--tag", tag)
    assert proc.returncode == tag_guard.E_DECISION, (
        "non-canonical key %r cut a tag (exit %d) -- this is the P1: the "
        "grammar divergence let a NO-GO through.\n%s%s"
        % (decisions, proc.returncode, proc.stdout, proc.stderr)
    )
    assert _NONCANONICAL_DIAGNOSTIC in proc.stderr, proc.stderr
    assert "closed allowlist" not in proc.stdout


def test_integrity_md_names_the_real_packlist_exceptions():
    """Re-pass rc.4 t5 P1 (npm honesty): INTEGRITY.md's packlist claim must
    name the SHIPPED exceptions that npm-publish.yml actually ships — a
    blanket "no tests, fixtures or plan material" line was false."""
    integrity = (REPO_ROOT / "npm" / "INTEGRITY.md").read_text(encoding="utf-8")
    publish = (REPO_ROOT / ".github" / "workflows" / "npm-publish.yml").read_text(
        encoding="utf-8"
    )
    for exc in (".claude/policies/fixtures/", "templates/oidc-proxy/tests/"):
        assert exc in publish, (
            "fixture drifted: %r no longer shipped by npm-publish.yml -- "
            "update INTEGRITY.md AND this test together" % exc
        )
        assert exc in integrity, (
            "INTEGRITY.md packlist claim omits the SHIPPED exception %r" % exc
        )
    assert "PLAN-N" in integrity, (
        "INTEGRITY.md must state the real predicate (numbered PLAN-N "
        "artifacts excluded), not a blanket no-plan-material claim"
    )


def test_both_rails_answer_identically_on_every_key_shape():
    """The instrument that would have caught P1-a: ONE question, two readers.

    A divergence is only visible when the same bytes are put to both. For any
    block both accept, they must also agree on how many decisions it declares
    and on which one wins -- otherwise the pair `NO-GO`/`GO` means different
    things on the two machines that gate a release.
    """
    def block(body: str) -> str:
        return "# fixture\n\n```yaml\n%s```\n" % body

    canonical_shapes = [
        "verdict: GO\nrelease_tag: v1.2.3\n",
        "verdict: NO-GO\nverdict: GO\n",
        "verdict: GO\ndelta_allowlist:\n  - a/b.md\n  - c/d.md\n",
        "verdict: GO\ntool_versions:\n  codex_cli: 0.144.6\n",
        "verdict: GO  # inline comment\n",
        "verdict: GO#NO-GO\nrelease_tag: v1.2.3\n",
        "# verdict: NO-GO\nverdict: GO\n",
    ]
    noncanonical_shapes = [
        "verdict:GO\n",
        "verdict: GO\n  NO-GO\nrelease_tag: v1.2.3\n",
        "verdict : NO-GO\nverdict: GO\n",
        "verdict\t: NO-GO\nverdict: GO\n",
        "verdict : GO\n",
        '"verdict": GO\n',
        "verdict :GO\n",
    ]
    for body in canonical_shapes:
        text = block(body)
        assert validator.noncanonical_top_level_lines(text) == [], body
        assert tag_guard._noncanonical_top_level_lines(text) == [], body
        assert validator.count_top_level_key(
            text, "verdict"
        ) == tag_guard._count_top_level_key(text, "verdict"), (
            "the two rails disagree on how many decisions %r declares" % body
        )
        assert validator.parse_verdict_text(text).get(
            "verdict"
        ) == tag_guard._parse_verdict(text).get("verdict"), (
            "the two rails disagree on WHICH decision wins in %r" % body
        )
    for body in noncanonical_shapes:
        text = block(body)
        assert validator.noncanonical_top_level_lines(text) != [], body
        assert (
            tag_guard._noncanonical_top_level_lines(text)
            == validator.noncanonical_top_level_lines(text)
        ), "the two shape gates disagree about %r" % body


@pytest.mark.parametrize("decision", ["GO", "GO-WITH-CONDITIONS"])
def test_delta_still_cuts_a_tag_on_an_authorizing_verdict(synth, decision):
    arm_verdict(synth, "v1.3.0-rc.2", verdict=decision)
    proc = guard(synth, "delta", "--repo", str(synth["repo"]), "--tag", "v1.3.0-rc.2")
    assert _DECISION_REFUSED not in proc.stderr, proc.stderr
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "closed allowlist" in proc.stdout
