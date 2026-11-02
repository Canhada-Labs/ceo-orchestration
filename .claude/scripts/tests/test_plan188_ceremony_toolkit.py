"""PLAN-188: ADR-010 scope plus real, isolated GPG detached signatures."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_HOOKS = Path(__file__).resolve().parents[2] / "hooks"
sys.path.insert(0, str(_HOOKS))
from _lib._ceremony_toolkit import (  # noqa: E402
    build_ceremony_summary,
    collect_modified_canonical_paths,
    validate_sentinel_pack,
    verify_detached_signatures,
)
from _subprocess_helpers import run_in_process_group  # noqa: E402


@pytest.fixture
def pack(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    guarded = root / ".claude/team.md"
    guarded.parent.mkdir()
    guarded.write_text("team=original\n", encoding="utf-8")
    sentinel = root / "approved.md"
    sentinel.write_text(
        "---\nplan: PLAN-188\nround: 1\ntype: architect-sentinel\n---\n\n"
        "Approved-By: @owner " + "a" * 40 + "\n"
        "Approved-At: 2026-11-01T10:00:00Z\n"
        "Scope:\n  - .claude/team.md\n",
        encoding="utf-8",
    )
    return root, sentinel, guarded


def _validate(pack, paths=(".claude/team.md",), **kwargs):
    root, sentinel, _ = pack
    return validate_sentinel_pack(
        root, sentinel, paths, canonical_patterns=(".claude/team.md", ".claude/skills/**/SKILL.md"), **kwargs
    )


def test_scope_exact_match(pack):
    result = _validate(pack)
    assert result["valid"] is True
    assert result["canonical_paths"] == (".claude/team.md",)


def test_scope_missing_canonical_change_rejected(pack):
    result = _validate(pack, (".claude/team.md", ".claude/skills/other/SKILL.md"))
    assert result["valid"] is False
    assert result["reason"] == "scope_diff_mismatch"


def test_scope_extra_unmodified_change_rejected(pack):
    root, sentinel, _ = pack
    sentinel.write_text(sentinel.read_text().replace("Scope:\n", "Scope:\n  - .claude/skills/other/SKILL.md\n"))
    result = _validate(pack)
    assert result["valid"] is False
    assert result["reason"] == "scope_diff_mismatch"


def test_missing_approval_line_rejected(pack):
    root, sentinel, _ = pack
    sentinel.write_text(sentinel.read_text().replace("Approved-By:", "Reviewer:"))
    assert _validate(pack)["reason"] == "approved_by_missing_or_ambiguous"


def test_two_separated_scope_blocks_rejected(pack):
    _, sentinel, _ = pack
    sentinel.write_text(sentinel.read_text() + "\nExplanation: unrelated\n\nScope:\n  - .claude/team.md\n")
    result = _validate(pack)
    assert result["valid"] is False
    assert result["reason"] == "duplicate_scope"


def test_traversal_in_diff_rejected(pack):
    result = _validate(pack, ("../.claude/team.md",))
    assert result["valid"] is False
    assert result["reason"] == "unsafe_path"


def test_canonical_segment_matching_not_recursive_single_star(pack):
    root, _, _ = pack
    result = collect_modified_canonical_paths(
        root, ("docs/nope", ".claude/skills/one/two/SKILL.md", ".claude/skills/one/SKILL.md"),
        canonical_patterns=(".claude/skills/*/SKILL.md",),
    )
    assert result == (".claude/skills/one/SKILL.md",)


def test_sha256_pins_remeasured_after_content_change(pack):
    root, _, guarded = pack
    digest = hashlib.sha256(guarded.read_bytes()).hexdigest()
    assert _validate(pack, expected_sha256={".claude/team.md": digest})["valid"]
    guarded.write_text("team=tampered\n")
    result = _validate(pack, expected_sha256={".claude/team.md": digest})
    assert result["valid"] is False
    assert result["reason"] == "sha256_pin_mismatch"
    assert result["sha256"][".claude/team.md"] != digest


def test_summary_cannot_claim_owner_approval_without_signature(pack):
    summary = build_ceremony_summary(_validate(pack), {"valid": False, "fingerprint": "", "reason": "unsigned"})
    assert summary["ready_for_owner_review"] is False
    assert summary["signed_or_landed_by_toolkit"] is False
    assert summary["reason"] == "unsigned"


def test_signature_rejects_empty_allowlist_before_running_gpg(tmp_path):
    home = tmp_path / "keyring"
    home.mkdir()
    signed = tmp_path / "signed.md"
    sig = tmp_path / "signed.md.asc"
    signed.write_text("content")
    sig.write_text("fake gpg signature")
    result = verify_detached_signatures(signed, sig, keyring_home=home, allowed_fingerprints=[])
    assert result["valid"] is False
    assert result["reason"] == "invalid_or_empty_fingerprint_allowlist"


def test_signature_does_not_fallback_to_personal_keyring(tmp_path):
    signed = tmp_path / "signed.md"
    sig = tmp_path / "signed.md.asc"
    signed.write_text("content")
    sig.write_text("fake gpg signature")
    result = verify_detached_signatures(
        signed, sig, keyring_home=tmp_path / "absent", allowed_fingerprints=["A" * 40]
    )
    assert result["valid"] is False
    assert result["reason"] == "explicit_keyring_required"


@pytest.fixture(scope="module")
def signed_fixture(tmp_path_factory):
    binary = shutil.which("gpg")
    if not binary:
        pytest.skip("gpg ausente; verificacao real impossivel")
    root = tmp_path_factory.mktemp("ceremony-gpg")
    home = root / "gnupg"
    home.mkdir(mode=0o700)
    sample = root / "signed.md"
    signature = root / "signed.md.asc"
    # Historic signature fixture, not a new approval or test-generated key.
    # SP-042's tracked bytes verify under .claude/trust/owner.asc; SP-026
    # currently fails GPG (BADSIG), so its presence alone proves nothing.
    claude = Path(__file__).resolve().parents[2]
    proposal = claude / "proposals/SP-042-cross-llm-pair-review-lint-fm-10-2026-07-10.md"
    shutil.copy2(proposal, sample)
    shutil.copy2(Path(str(proposal) + ".asc"), signature)
    public_key = root / "owner.asc"
    shutil.copy2(claude / "trust/owner.asc", public_key)

    def run(*arguments):
        return run_in_process_group(
            [binary, "--no-options", "--no-autostart", "--homedir", str(home), "--batch", *arguments],
            capture_output=True, text=True, check=True, timeout=25,
        )

    run("--import", str(public_key))
    listing = run("--with-colons", "--fingerprint", "--list-keys").stdout
    fingerprint = next(row.split(":")[9] for row in listing.splitlines() if row.startswith("fpr:"))
    return home, sample, signature, fingerprint


def test_detached_gpg_signature_validates_real_bytes(signed_fixture):
    home, sample, signature, fingerprint = signed_fixture
    result = verify_detached_signatures(sample, signature, keyring_home=home, allowed_fingerprints=[fingerprint])
    assert result == {"valid": True, "fingerprint": fingerprint, "reason": ""}


def test_detached_gpg_rejects_tampered_payload(signed_fixture, tmp_path):
    home, sample, signature, fingerprint = signed_fixture
    tampered = tmp_path / "signed.md"
    tampered.write_text(sample.read_text() + "malicious change\n")
    result = verify_detached_signatures(tampered, signature, keyring_home=home, allowed_fingerprints=[fingerprint])
    assert result["valid"] is False
    assert result["reason"] == "gpg_invalid_signature"


def test_detached_gpg_rejects_signer_not_allowlisted(signed_fixture):
    home, sample, signature, _ = signed_fixture
    result = verify_detached_signatures(sample, signature, keyring_home=home, allowed_fingerprints=["F" * 40])
    assert result["valid"] is False
    assert result["reason"] == "signer_not_allowlisted"


def test_detached_gpg_rejects_missing_explicit_keyring(signed_fixture, tmp_path):
    _, sample, signature, fingerprint = signed_fixture
    result = verify_detached_signatures(sample, signature, keyring_home=tmp_path / "missing", allowed_fingerprints=[fingerprint])
    assert result["valid"] is False
    assert result["reason"] == "explicit_keyring_required"


def test_detached_gpg_rejects_symlink_signature(signed_fixture, tmp_path):
    home, sample, signature, fingerprint = signed_fixture
    link = tmp_path / "signature.asc"
    link.symlink_to(signature)
    result = verify_detached_signatures(sample, link, keyring_home=home, allowed_fingerprints=[fingerprint])
    assert result["valid"] is False
    assert result["reason"] == "signed_file_or_signature_missing"
