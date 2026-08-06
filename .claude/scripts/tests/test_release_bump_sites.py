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
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
LOCAL = REPO_ROOT / ".claude" / "scripts" / "local"
DRIVER_SRC = LOCAL / "release.sh"
SITES_SRC = LOCAL / "_release_bump_sites.py"
GUARD_SRC = LOCAL / "_release_tag_guard.py"

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


def write_verdict(
    repo: Path,
    tag: str,
    parent: str,
    allowlist: Sequence[str],
    manifest_rel: str,
    manifest_sha: str,
) -> str:
    rel = ".claude/governance/pair-rail-verdict-%s.md" % tag
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    entries = "\n".join("  - %s" % e for e in allowlist)
    path.write_text(
        "# Pair-Rail Verdict — %s\n\n```yaml\nverdict: GO\nrelease_tag: %s\n"
        "parent_sha: %s\ndelta_allowlist:\n%s\ndelta_manifest: %s\n"
        "delta_manifest_sha256: %s\n```\n" % (
            tag, tag, parent, entries, manifest_rel, manifest_sha,
        ),
        encoding="utf-8",
    )
    return rel


def arm_verdict(synth, tag: str, slug: str = "repass-r2", extra_allow=()):
    """Commit a re-pass + verdict for `tag`, anchored at the pre-verdict HEAD."""
    repo, env = synth["repo"], synth["env"]
    parent = git(repo, env, "rev-parse", "HEAD")
    ev = make_repass(
        repo, slug, {"verdict-r1.txt": "GO\n", "transcript-r1.log": "rounds: 3\n"}
    )
    verdict_rel = ".claude/governance/pair-rail-verdict-%s.md" % tag
    allow = [verdict_rel, ev["manifest_rel"]] + ev["artifact_rels"] + list(extra_allow)
    write_verdict(repo, tag, parent, allow, ev["manifest_rel"], ev["manifest_sha"])
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
    ],
)
def test_delta_rejects_plan_paths_outside_the_manifest_dir(synth, entry):
    """Re-pass P2: `.claude/plans/` entries OUTSIDE the manifest directory
    used to close by NAME alone — no content pin, no manifest coverage, no
    tag specificity — while the same guard rejected `VERSION` as
    non-EXHAUSTIVE. Only `verdict-fields-<THIS TAG>.md` may live outside the
    content-pinned manifest directory; everything else must be IN it."""
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
    assert "PLAN-162 / PLAN-165 / PLAN-166 (ADRs 184 -> 189)" in proc.stdout
    assert "v1.3.0 —" in proc.stdout


# ===========================================================================
# F6 — the name was the root of the class; the literals go with it
# ===========================================================================
SEMVER_RX = re.compile(r"\b\d+\.\d+\.\d+\b")
# "<number> [word] site(s)" — a census in a comment has no oracle behind it.
SITE_COUNT_RX = re.compile(
    r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+"
    r"(?:\w+\s+)?sites?\b",
    re.IGNORECASE,
)
# Assembled at RUNTIME, never as a literal: a control whose own file is a hit
# has to exempt itself, and an exemption is how a control stops controlling.
# (`"a" "b"` and `"a" + "b"` are both folded by the compiler and would land in
# this module's .pyc verbatim; str.join is not folded.)
OLD_DRIVER_STEM = "-".join(("release", "v1", "2", "0"))
SCAN_ROOTS = (".github", "RELEASE.md", ".claude/scripts", "scripts")


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


def test_driver_makes_no_site_count_claim_in_comments():
    """The rule is DELETE the count, never correct it: a corrected count is a
    count that goes stale again the next time the table grows."""
    text = DRIVER_SRC.read_text(encoding="utf-8")
    offenders = [
        "%d: %s" % (num, line.strip())
        for num, line in enumerate(text.splitlines(), 1)
        if SITE_COUNT_RX.search(line)
    ]
    assert not offenders, "site-count claim in the driver:\n%s" % "\n".join(offenders)


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
