#!/usr/bin/env python3
"""Tests for check-rule-invariants.py (PLAN-139 Wave A).

Drives the checker through synthetic tmp trees via the --repo flag, so the
real $HOME / $CLAUDE_PROJECT_DIR are never touched (env-hygiene gate). No
os.environ mutation anywhere in this module.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load the hyphenated script as a module (import-and-call, preferred path).
# ---------------------------------------------------------------------------
_SCRIPT = Path(__file__).resolve().parent.parent / "check-rule-invariants.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_rule_invariants", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cri = _load_module()


# ---------------------------------------------------------------------------
# Synthetic-tree helpers.
# ---------------------------------------------------------------------------
def _all_phrases_by_file():
    """Return {rel_file: [phrase, ...]} aggregated from the live registry."""
    by_file = {}
    for _inv_id, phrase, files, _rat in cri.INVARIANTS:
        for rel in files:
            by_file.setdefault(rel, []).append(phrase)
    return by_file


def _build_tree(root: Path, *, with_marker: bool = True,
                with_adr_readme: bool = False,
                drop_phrase: str = "",
                drop_from_file: str = "") -> None:
    """Create a synthetic framework tree under ``root``.

    Each tracked doc is populated with every pinned phrase (one per line,
    wrapped in filler prose). Optionally drops one phrase from one file.
    """
    by_file = _all_phrases_by_file()
    for rel, phrases in by_file.items():
        lines = ["# synthetic %s" % rel, "filler header line", ""]
        for ph in phrases:
            if drop_phrase and ph == drop_phrase and rel == drop_from_file:
                lines.append("intentionally-omitted spine line for %s" % rel)
                continue
            lines.append("Spine line containing %s here in prose." % ph)
        lines.append("")
        lines.append("trailing filler")
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("\n".join(lines), encoding="utf-8")

    adr_dir = root / ".claude" / "adr"
    adr_dir.mkdir(parents=True, exist_ok=True)
    if with_marker:
        (adr_dir / "ADR-001-runtime-state-directory.md").write_text(
            "# ADR-001 marker\n", encoding="utf-8"
        )
    if with_adr_readme:
        # install.sh ships this to EVERY adopter — its presence must NOT
        # by itself make the checker treat the tree as a framework repo.
        (adr_dir / "README.md").write_text("# adr index\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. positive — full tree with all phrases + marker → ok / exit 0.
# ---------------------------------------------------------------------------
def test_positive_all_present(tmp_path: Path):
    _build_tree(tmp_path, with_marker=True)
    report = cri.check_invariants(tmp_path)
    assert report["skipped"] is False
    assert report["ok"] is True
    assert report["misses"] == []
    assert report["checked"] == len(cri.INVARIANTS)
    rc = cri._cli(["--repo", str(tmp_path)])
    assert rc == 0


# ---------------------------------------------------------------------------
# 2. negative — delete one pinned phrase → miss / exit 1, names id+file+phrase.
# ---------------------------------------------------------------------------
def test_negative_one_phrase_deleted(tmp_path: Path, capsys):
    # Pick the first CLAUDE.md-only invariant to drop.
    target = next(
        (inv for inv in cri.INVARIANTS if inv[2] == ("CLAUDE.md",)), None
    )
    assert target is not None
    target_id, target_phrase, _files, _rat = target

    _build_tree(
        tmp_path,
        with_marker=True,
        drop_phrase=target_phrase,
        drop_from_file="CLAUDE.md",
    )
    report = cri.check_invariants(tmp_path)
    assert report["ok"] is False
    assert len(report["misses"]) == 1
    miss = report["misses"][0]
    assert miss["id"] == target_id
    assert miss["file"] == "CLAUDE.md"
    assert miss["phrase"] == target_phrase

    rc = cri._cli(["--repo", str(tmp_path)])
    assert rc == 1
    err = capsys.readouterr().err
    # Output must name id + file + phrase of the miss.
    assert target_id in err
    assert "CLAUDE.md" in err
    assert target_phrase in err


# ---------------------------------------------------------------------------
# 3. adopter-skip — README.md present but ADR-001 marker absent → skip / exit 0.
# ---------------------------------------------------------------------------
def test_adopter_skip(tmp_path: Path, capsys):
    # Build docs + adr README (Codex C1 real-adopter shape) but NO ADR-001
    # marker and NO scripts/install.sh.
    _build_tree(
        tmp_path,
        with_marker=False,
        with_adr_readme=True,
        # Also drop a phrase to prove the skip wins over a would-be miss.
        drop_phrase="stdlib only",
        drop_from_file="CLAUDE.md",
    )
    # Sanity: README present, ADR-001 + install.sh absent.
    assert (tmp_path / ".claude" / "adr" / "README.md").is_file()
    assert not (tmp_path / ".claude" / "adr" / "ADR-001-runtime-state-directory.md").exists()
    assert not (tmp_path / "scripts" / "install.sh").exists()

    report = cri.check_invariants(tmp_path)
    assert report["skipped"] is True
    assert report["ok"] is True
    assert report["misses"] == []

    rc = cri._cli(["--repo", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "adopter context: skipping" in out


# ---------------------------------------------------------------------------
# 3b. adopter-skip — adopter ships its OWN scripts/install.sh but lacks the
#     ADR-001 marker → must STILL skip (Codex pair-rail P2). install.sh must
#     never by itself mark a tree as the framework repo.
# ---------------------------------------------------------------------------
def test_adopter_skip_with_own_install_sh(tmp_path: Path):
    _build_tree(tmp_path, with_marker=False, with_adr_readme=True)
    (tmp_path / "scripts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "scripts" / "install.sh").write_text(
        "#!/bin/sh\necho adopter-own-installer\n", encoding="utf-8"
    )
    # Sanity: adopter's own install.sh present, framework ADR-001 marker absent.
    assert (tmp_path / "scripts" / "install.sh").is_file()
    assert not (
        tmp_path / ".claude" / "adr" / "ADR-001-runtime-state-directory.md"
    ).exists()
    report = cri.check_invariants(tmp_path)
    assert report["skipped"] is True
    assert cri._cli(["--repo", str(tmp_path)]) == 0


# ---------------------------------------------------------------------------
# 4. unicode / whitespace reword — NBSP, doubled spaces, mid-phrase newline
#    → still detected as present.
# ---------------------------------------------------------------------------
def test_unicode_and_whitespace_reword_still_present(tmp_path: Path):
    _build_tree(tmp_path, with_marker=True)

    # Rewrite CLAUDE.md so the pinned phrases appear with mangled whitespace
    # but otherwise intact. Use the CLAUDE.md-only phrases.
    claude_phrases = [
        ph for _id, ph, files, _r in cri.INVARIANTS if "CLAUDE.md" in files
    ]
    nbsp = " "
    parts = ["# mangled CLAUDE.md", ""]
    for ph in claude_phrases:
        if " " in ph:
            # Replace the first space with NBSP, add doubled spaces, and a
            # line break in the middle of the phrase.
            toks = ph.split(" ")
            mid = len(toks) // 2 or 1
            head = nbsp.join(toks[:mid])
            tail = "  ".join(toks[mid:])
            mangled = head + "\n   " + tail  # newline + indent in the middle
        else:
            # Single-token phrase — pad with NBSP + doubled spaces around it.
            mangled = nbsp + "  " + ph + "  " + nbsp
        parts.append("prefix %s suffix" % mangled)
    (tmp_path / "CLAUDE.md").write_text("\n".join(parts), encoding="utf-8")

    report = cri.check_invariants(tmp_path)
    # Every CLAUDE.md-only phrase must still be found despite the mangling.
    claude_misses = [m for m in report["misses"] if m["file"] == "CLAUDE.md"]
    assert claude_misses == [], "whitespace/NFKC reword should still match: %r" % claude_misses


def test_fullwidth_nfkc_equivalence(tmp_path: Path):
    """A full-width compatibility variant normalizes equal under NFKC."""
    _build_tree(tmp_path, with_marker=True)
    # "3-strike" written with a full-width digit (U+FF13) + full-width hyphen
    # would NFKC-fold to ASCII. Use full-width digit three.
    fullwidth = "３-strike"  # NFKC -> "3-strike"
    assert cri._normalize(fullwidth) == "3-strike"
    (tmp_path / "PROTOCOL.md").write_text(
        "# protocol\nPlan → Debate → Execute\nThe %s rule applies.\n" % fullwidth,
        encoding="utf-8",
    )
    report = cri.check_invariants(tmp_path)
    proto_misses = [m for m in report["misses"] if m["file"] == "PROTOCOL.md"]
    assert proto_misses == [], "full-width NFKC variant should match: %r" % proto_misses


# ---------------------------------------------------------------------------
# 5. registry self-test — no empty phrase, each == NFKC(itself).
# ---------------------------------------------------------------------------
def test_registry_self_test_passes():
    # Should not raise.
    cri._validate_registry()


def test_registry_phrases_nonempty_and_nfkc():
    import unicodedata
    for inv_id, phrase, files, _rat in cri.INVARIANTS:
        assert cri._normalize(phrase), "empty after normalize: %r" % inv_id
        assert phrase == unicodedata.normalize("NFKC", phrase), (
            "non-NFKC literal: %r" % inv_id
        )
        assert files, "no files listed: %r" % inv_id


def test_registry_self_test_detects_bad_phrase():
    bad = (("bad", "   ", ("CLAUDE.md",), "whitespace-only"),)
    with pytest.raises(ValueError):
        cri._validate_registry(bad)


def test_registry_self_test_detects_non_nfkc():
    # Full-width digit literal is NOT NFKC-normal → must trip the self-test.
    bad = (("bad", "３-strike", ("PROTOCOL.md",), "non-nfkc literal"),)
    with pytest.raises(ValueError):
        cri._validate_registry(bad)


# ---------------------------------------------------------------------------
# missing-file fails CLOSED (a vanished file is a deletion).
# ---------------------------------------------------------------------------
def test_missing_file_fails_closed(tmp_path: Path):
    _build_tree(tmp_path, with_marker=True)
    (tmp_path / "PROTOCOL.md").unlink()
    report = cri.check_invariants(tmp_path)
    assert report["ok"] is False
    proto_misses = [m for m in report["misses"] if m["file"] == "PROTOCOL.md"]
    assert proto_misses, "missing PROTOCOL.md should produce misses"
    assert all("error" in m for m in proto_misses)


# ---------------------------------------------------------------------------
# subprocess smoke — confirm the script runs as an executable via --repo.
# ---------------------------------------------------------------------------
def test_subprocess_positive(tmp_path: Path):
    _build_tree(tmp_path, with_marker=True)
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), "--repo", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr


def test_subprocess_negative_names_miss(tmp_path: Path):
    target = next(inv for inv in cri.INVARIANTS if inv[2] == ("CLAUDE.md",))
    _build_tree(
        tmp_path, with_marker=True,
        drop_phrase=target[1], drop_from_file="CLAUDE.md",
    )
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), "--repo", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 1
    assert target[0] in proc.stderr
    assert target[1] in proc.stderr


def test_repo_root_alias(tmp_path: Path):
    """--repo-root is accepted as an alias for --repo."""
    _build_tree(tmp_path, with_marker=True)
    rc = cri._cli(["--repo-root", str(tmp_path)])
    assert rc == 0


def test_list_flag_exit_zero(capsys):
    rc = cri._cli(["--list"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "rule invariants" in out
    # Every invariant id appears in the listing.
    for inv_id, _ph, _f, _r in cri.INVARIANTS:
        assert inv_id in out


def test_json_flag_shape(tmp_path: Path, capsys):
    import json as _json
    _build_tree(tmp_path, with_marker=True)
    rc = cri._cli(["--repo", str(tmp_path), "--json"])
    assert rc == 0
    payload = _json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["skipped"] is False
    assert payload["checked"] == len(cri.INVARIANTS)
