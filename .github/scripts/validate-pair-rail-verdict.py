#!/usr/bin/env python3
"""validate-pair-rail-verdict.py — PLAN-081 Phase 6 release.yml step 15.

Validates a Pair-Rail verdict artifact (`.claude/governance/
pair-rail-verdict-<release-tag>.md`) per R1 S-Sec-3 replay defense +
R1 S-Sec-4 inputs_hash determinism + R1 C5 Codex CLI pin enforcement
+ R1 S-QA-Unseen-2 distinct VERDICT_EXPIRED exit code.

## Usage

    python3 .github/scripts/validate-pair-rail-verdict.py \\
      --verdict-file .claude/governance/pair-rail-verdict-${GITHUB_REF_NAME}.md \\
      --parent-sha ${PARENT_SHA} \\
      --release-tag ${GITHUB_REF_NAME} \\
      --max-age-hours 24 \\
      --recompute-inputs-hash \\
      --codex-cli-pin-file .claude/governance/codex-cli-pin.txt \\
      --codex-pin-manifest-file .claude/governance/codex-cli-pin-manifest.json \\
      --inputs-hash-paths-file .claude/governance/pair-rail-inputs-hash-manifest.txt

## ADR-182 payload pin (PLAN-163 T5.2)

`--codex-pin-manifest-file` enforces the payload pin: the verdict
envelope MUST declare `tool_versions.codex_target_triple` (the platform
triple of the run that generated the verdict) and
`tool_versions.codex_payload_sha256` (sha256 of the NATIVE codex
payload for that triple — NOT the npm JS launcher). The validator
compares the declared sha against
`manifest.payloads[<triple>].sha256`. Fail-CLOSED: missing fields,
triple absent from the manifest, malformed entry, or sha mismatch →
VERDICT_INVALID (3). Manifest file unreadable → infra (1). The legacy
`--codex-cli-binary-sha256-file` launcher-hash pin is retained only for
pre-ADR-182 tags; the live pin file is a comment-only tombstone, which
that legacy path treats as "no pin" (skip).

## parent_sha vs commit_sha (S104 redesign)

The legacy `--commit-sha` arg + verdict `commit_sha:` field bound the
verdict to a SHA the verdict commit itself produced — an unsolvable
self-reference (`pair-rail-verdict-vX.md` cannot declare its own commit
SHA because that SHA is only known AFTER the verdict file is committed).
The v1.16.0 GA ceremony bridged this via `CEO_PAIR_RAIL_VERDICT_OPTIONAL=1`
transition mode, which silently disabled the bind.

`parent_sha:` solves it cleanly. The verdict declares the commit it was
generated AGAINST (the parent of the verdict-file commit). That value is
known when the verdict is authored (it's `git rev-parse HEAD` before the
verdict commit). Step 15 validates against `git log -n1 --format=%H --
<verdict-file>` parent, which is observable + immutable.

Backward-compat: when only `commit_sha:` (legacy) is present and
`--parent-sha` is empty, the bind is skipped with an ADVISORY (matches
prior CEO_PAIR_RAIL_VERDICT_OPTIONAL=1 behavior). Legacy verdicts for
already-shipped tags (v1.16.0 etc.) keep their existing semantics; new
verdicts use `parent_sha:`.

## Exit codes

- 0: verdict valid; release proceeds.
- 1: infra error (file missing / unparseable / etc.); release.yml
     decides based on CEO_PAIR_RAIL_VERDICT_OPTIONAL.
- 2: VERDICT_EXPIRED — distinct from infra-error per R1 S-QA-Unseen-2.
     Release.yml can route this to a "verdict regen" branch.
- 3: VERDICT_INVALID — decision not authorizing (PLAN-177 W0.1) /
     non-canonical top-level key syntax, i.e. a spelling this reader and
     the local tag guard resolve differently (PLAN-177 t2) /
     release_tag mismatch / parent_sha mismatch / inputs_hash mismatch /
     pin mismatch / signature missing. Release MUST stop here.

stdlib only. Python ≥3.9.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

EXIT_OK = 0
EXIT_INFRA_ERROR = 1
EXIT_VERDICT_EXPIRED = 2
EXIT_VERDICT_INVALID = 3

# PLAN-177 W0.1 (P1-4). The decisions that AUTHORIZE a release. Every other
# value — NO-GO, absent, empty, malformed, or simply unknown — is
# non-authorizing and stops the release. Spelling is the template's
# (.claude/governance/pair-rail-verdict-template.md:
# `verdict: GO | NO-GO | GO-WITH-CONDITIONS`); membership is tested by EXACT
# equality on purpose — case folding or a substring/prefix rule would read
# NO-GO as authorizing because it CONTAINS GO.
ACCEPTED_DECISIONS = ("GO", "GO-WITH-CONDITIONS")


_YAML_BLOCK_RE = re.compile(r"```yaml\s*\n(.*?)```", re.DOTALL)


def _strip_comment(raw: str) -> str:
    """The comment/whitespace rule of the reader below, in ONE place."""
    return raw.split("#", 1)[0].rstrip() if "#" in raw else raw.rstrip()


# PLAN-177 t2 (re-pass rc.4 P1-a). The CANONICAL top-level declaration.
# Two readers of the same signed file must not disagree about what a key
# IS: this validator counted `verdict : NO-GO` as a declaration of
# `verdict` (it strips the key), while the local tag guard's regex demanded
# the colon immediately after the name and skipped the line entirely. The
# valid-YAML pair
#
#     verdict : NO-GO
#     verdict: GO
#
# is therefore two declarations here and ONE (=GO) there — a last-wins
# override that the rail enforcing in every mode never saw.
#
# The semantics chosen for BOTH rails, and the reason: NON-CANONICAL
# top-level syntax is REJECTED, fail-closed. Trimming the key in both
# readers would also close the divergence, but it widens the grammar of a
# SIGNED artifact to shapes no author writes and no template emits — every
# new accepted spelling is another chance for the next reader to disagree.
# Refusing the shape is a smaller surface and is the one behaviour that
# cannot silently prefer a value. A top-level line is canonical iff it is
# `name:` with no whitespace before the colon, or a `- ` list item.
_CANONICAL_TOP_LEVEL_KEY_RE = re.compile(r"\A[A-Za-z0-9_]+:")


def noncanonical_top_level_lines(text: str) -> List[str]:
    """Top-level lines of the yaml block that are not canonical declarations.

    Byte-for-byte twin of `_noncanonical_top_level_lines` in
    `.claude/scripts/local/_release_tag_guard.py` (separate processes on
    separate machines; neither may import the other — keep them identical).
    Empty list == the block speaks the grammar both readers assume.
    """
    m = _YAML_BLOCK_RE.search(text)
    if not m:
        return []
    bad: List[str] = []
    prev_scalar_decl = False
    for raw in m.group(1).splitlines():
        line = _strip_comment(raw)
        if not line.strip():
            continue
        if line[0] in (" ", "\t"):
            # Sub-level line. Legitimate ONLY under a parent declared as a
            # bare `key:` (mapping/list). After a SCALAR `key: value`, an
            # indented non-comment line is a YAML CONTINUATION that changes
            # the scalar's value (`verdict: GO` + `  NO-GO` == "GO NO-GO")
            # while this minimal reader still saw `GO` — reject fail-closed
            # (re-pass rc.4 t2 P1).
            if prev_scalar_decl:
                bad.append(line)
            continue
        if _CANONICAL_TOP_LEVEL_KEY_RE.match(line):
            _key, _, _val = line.partition(":")
            prev_scalar_decl = bool(_val.strip())
            continue
        if line.startswith("- "):  # top-level list item
            prev_scalar_decl = False
            continue
        bad.append(line)
        prev_scalar_decl = False
    return bad


def count_top_level_key(text: str, key: str) -> int:
    """How many times `key:` is declared at the top level of the block.

    Both readers of this signed file are LAST-WINS, so a second
    `verdict:` silently overrides the first: NO-GO followed by GO parses
    as GO. Callers require exactly one.

    Only meaningful once `noncanonical_top_level_lines` is empty: this
    counter strips the key, so it sees `verdict : X` as a declaration and
    the twin counter in the tag guard does not. Callers run the shape
    check FIRST.
    """
    m = _YAML_BLOCK_RE.search(text)
    if not m:
        return 0
    seen = 0
    for raw in m.group(1).splitlines():
        line = _strip_comment(raw)
        if not line.strip() or line[0] in (" ", "\t"):
            continue
        if line.partition(":")[0].strip() == key:
            seen += 1
    return seen


def parse_verdict_text(text: str) -> Dict[str, Any]:
    """Parse YAML frontmatter from verdict TEXT. Returns dict."""
    m = _YAML_BLOCK_RE.search(text)
    if not m:
        raise ValueError("verdict file missing yaml frontmatter block")
    yaml_body = m.group(1)
    # Inline minimal YAML parse (stdlib only)
    out: Dict[str, Any] = {}
    current_key: Optional[str] = None
    for raw in yaml_body.splitlines():
        line = _strip_comment(raw)
        if not line.strip():
            continue
        if line[0] not in (" ", "\t"):
            if ":" in line:
                k, _, v = line.partition(":")
                v = v.strip()
                if v:
                    out[k.strip()] = v
                else:
                    out[k.strip()] = {}
                    current_key = k.strip()
        elif current_key and ":" in line:
            sub_k, _, sub_v = line.partition(":")
            if isinstance(out[current_key], dict):
                out[current_key][sub_k.strip()] = sub_v.strip()
    return out


def parse_verdict_file(path: Path) -> Dict[str, Any]:
    """Path wrapper over parse_verdict_text (published entry point)."""
    if not path.exists():
        raise FileNotFoundError(f"verdict file: {path}")
    return parse_verdict_text(path.read_text(encoding="utf-8"))


def compute_inputs_hash(repo_root: Path, manifest_path: Path) -> str:
    """Compute inputs_hash via git hash-object + canonical_json (R1 S-Sec-4)."""
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest: {manifest_path}")
    paths = []
    for line in manifest_path.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            paths.append(line)
    paths.sort()
    hashes = {}
    for p in paths:
        result = subprocess.run(
            ["git", "hash-object", p],
            capture_output=True, text=True, cwd=str(repo_root), timeout=10,
        )
        if result.returncode != 0:
            raise ValueError(f"git hash-object failed for {p}: {result.stderr}")
        hashes[p] = result.stdout.strip()
    canon = json.dumps(hashes, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def parse_pin_range(pin_file: Path) -> Tuple[Optional[str], Optional[str]]:
    """Parse pin range like '>=0.128.0,<0.130.0'. Returns (min, max)."""
    if not pin_file.exists():
        return None, None
    for line in pin_file.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        # parse `>=X.Y.Z,<A.B.C` shape
        m = re.search(r">=\s*([\d.]+(?:[-+][\w.]+)?)\s*,\s*<\s*([\d.]+(?:[-+][\w.]+)?)", line)
        if m:
            return m.group(1), m.group(2)
    return None, None


def parse_semver(s: str) -> Tuple[int, int, int]:
    m = re.match(r"(\d+)\.(\d+)\.(\d+)", s.strip())
    if not m:
        raise ValueError(f"unparseable semver: {s!r}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def semver_in_range(version: str, min_v: str, max_v: str) -> bool:
    try:
        v = parse_semver(version)
        lo = parse_semver(min_v)
        hi = parse_semver(max_v)
        return lo <= v < hi
    except ValueError:
        return False


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verdict-file", required=True)
    parser.add_argument(
        "--parent-sha",
        default="",
        help=(
            "Expected verdict.parent_sha — the commit the verdict was "
            "generated against (parent of the verdict-file commit). "
            "Resolves the self-reference problem the legacy --commit-sha "
            "bind had with PLAN-081 v1.16.0 GA. Empty string = skip bind."
        ),
    )
    parser.add_argument(
        "--commit-sha",
        default="",
        help=(
            "DEPRECATED legacy bind. Retained for backward-compat with "
            "v1.16.0-era verdicts that ship `commit_sha:` field. "
            "Mutually exclusive with --parent-sha; if both passed, "
            "--parent-sha wins."
        ),
    )
    parser.add_argument("--release-tag", required=True)
    parser.add_argument("--max-age-hours", type=int, default=24)
    parser.add_argument("--recompute-inputs-hash", action="store_true")
    parser.add_argument("--codex-cli-pin-file", default="")
    parser.add_argument("--codex-cli-binary-sha256-file", default="")
    parser.add_argument(
        "--codex-pin-manifest-file",
        default="",
        help=(
            "ADR-182 payload-pin manifest (codex-cli-pin-manifest.json). "
            "When passed, verdict.tool_versions.codex_target_triple + "
            ".codex_payload_sha256 MUST match the manifest entry "
            "(fail-CLOSED — VERDICT_INVALID on any miss)."
        ),
    )
    parser.add_argument("--inputs-hash-paths-file", default="")
    args = parser.parse_args(argv)

    verdict_path = Path(args.verdict_file)
    repo_root = Path.cwd()

    # Parse verdict. The TEXT is kept: the duplicate-key check below reads
    # the same bytes the parse consumed (a second read could disagree).
    try:
        verdict_text = verdict_path.read_text(encoding="utf-8")
        verdict = parse_verdict_text(verdict_text)
    except FileNotFoundError as e:
        print(f"INFRA: verdict file not found: {e}", file=sys.stderr)
        return EXIT_INFRA_ERROR
    except OSError as e:
        print(f"INFRA: verdict file unreadable: {e}", file=sys.stderr)
        return EXIT_INFRA_ERROR
    except ValueError as e:
        print(f"INFRA: verdict parse error: {e}", file=sys.stderr)
        return EXIT_INFRA_ERROR

    # PLAN-177 W0.1 (P1-4): the DECISION gate. Until this block existed
    # the validator read pinning, TTL and signature presence but never the
    # verdict itself: a cross-model NO-GO returned OK / exit 0.
    #
    # CF-3 ASYMMETRY (stated in BOTH rails, where it can be acted on):
    # this step carries `continue-on-error` when
    # CEO_PAIR_RAIL_VERDICT_OPTIONAL=1 (release.yml:689), so the gate HERE
    # is defence in depth; the rail that enforces in EVERY mode is
    # `.claude/scripts/local/_release_tag_guard.py delta`, invoked by a
    # step with no escape hatch. Neither may be dropped for the other.
    #
    # Fail-CLOSED on SHAPE as well as value (CF-1): the reader above
    # returns a dict for an empty `verdict:` line, so the type check
    # precedes the compare and a malformed decision exits 3 (INVALID),
    # never 1 (INFRA) -- which the transition mode is allowed to wave
    # through. Same precedent as the tool_versions dict check below.
    # PLAN-177 t2 (P1-a): SHAPE BEFORE VALUE. The counter below and the tag
    # guard's counter only agree on a canonical block; a non-canonical
    # top-level line is refused here rather than parsed by two grammars.
    # INVALID (3), never INFRA (1): the transition mode may wave INFRA
    # through, and this is a property of the SIGNED bytes, not of the runner.
    noncanonical = noncanonical_top_level_lines(verdict_text)
    if noncanonical:
        print(
            f"INVALID: non-canonical top-level key syntax in the verdict "
            f"block: {noncanonical!r} -- a top-level line must be `name:` "
            f"with no whitespace before the colon (or a `- ` list item). "
            f"The two release rails read this file with different "
            f"grammars, so `verdict : NO-GO` followed by `verdict: GO` "
            f"counts as two declarations here and one there; the shape is "
            f"refused instead of guessed.",
            file=sys.stderr,
        )
        return EXIT_VERDICT_INVALID

    decisions_declared = count_top_level_key(verdict_text, "verdict")
    if decisions_declared > 1:
        print(
            f"INVALID: verdict decision declared more than once "
            f"(x{decisions_declared}) -- the reader is last-wins, so a "
            f"duplicated `verdict:` silently overrides the first; exactly "
            f"one is required.",
            file=sys.stderr,
        )
        return EXIT_VERDICT_INVALID
    raw_decision = verdict.get("verdict")
    if raw_decision is None:
        shown = "<absent>"
    elif not isinstance(raw_decision, str):
        shown = "<non-string:%s>" % type(raw_decision).__name__
    else:
        shown = raw_decision.strip()
    if shown not in ACCEPTED_DECISIONS:
        accepted = "{%s}" % ", ".join(ACCEPTED_DECISIONS)
        print(
            f"INVALID: verdict decision '{shown}' not in {accepted} -- a "
            f"release requires an explicit authorizing decision from the "
            f"pair-rail. Exact match: no case folding, no substring rule "
            f"(NO-GO contains GO).",
            file=sys.stderr,
        )
        return EXIT_VERDICT_INVALID

    # R1 S-Sec-3: release_tag bind
    declared_tag = verdict.get("release_tag", "").strip()
    if declared_tag != args.release_tag:
        print(
            f"INVALID: verdict release_tag mismatch — "
            f"declared='{declared_tag}', argv='{args.release_tag}'",
            file=sys.stderr,
        )
        return EXIT_VERDICT_INVALID

    # parent_sha / commit_sha bind (S104 redesign — see docstring).
    # Precedence: --parent-sha (canonical, post-S104) wins. Falls back to
    # legacy --commit-sha for v1.16.0-era verdicts that still ship the old
    # field.
    if args.parent_sha:
        declared_parent = verdict.get("parent_sha", "").strip()
        if not declared_parent:
            # New-style validation requested but verdict lacks the field.
            # Could be a stale verdict generated before the redesign. Fall
            # back to legacy commit_sha if available; else hard-fail.
            legacy_sha = verdict.get("commit_sha", "").strip()
            if legacy_sha:
                print(
                    f"ADVISORY: verdict ships legacy commit_sha "
                    f"(='{legacy_sha[:12]}'); --parent-sha bind skipped. "
                    f"Re-author verdict with parent_sha for full S104 "
                    f"bind enforcement.",
                    file=sys.stderr,
                )
            else:
                print(
                    f"INVALID: verdict missing parent_sha field "
                    f"(--parent-sha='{args.parent_sha[:12]}' requested bind)",
                    file=sys.stderr,
                )
                return EXIT_VERDICT_INVALID
        elif declared_parent != args.parent_sha:
            print(
                f"INVALID: verdict parent_sha mismatch — "
                f"declared='{declared_parent[:12]}', "
                f"argv='{args.parent_sha[:12]}'",
                file=sys.stderr,
            )
            return EXIT_VERDICT_INVALID
    elif args.commit_sha:
        # Legacy path — only used when --parent-sha not passed (e.g.
        # bridging older release.yml invocations against new validator).
        declared_sha = verdict.get("commit_sha", "").strip()
        if declared_sha != args.commit_sha:
            print(
                f"INVALID: verdict commit_sha mismatch — "
                f"declared='{declared_sha[:12]}', argv='{args.commit_sha[:12]}'",
                file=sys.stderr,
            )
            return EXIT_VERDICT_INVALID

    # R1 S-QA-Unseen-2: VERDICT_EXPIRED distinct exit code
    generated_at = verdict.get("generated_at", "")
    if generated_at:
        try:
            ts = datetime.fromisoformat(generated_at.rstrip("Z"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            age_hours = (now - ts).total_seconds() / 3600.0
            if age_hours > args.max_age_hours:
                print(
                    f"EXPIRED: verdict {age_hours:.1f}h old "
                    f"(max {args.max_age_hours}h)",
                    file=sys.stderr,
                )
                return EXIT_VERDICT_EXPIRED
        except (TypeError, ValueError):
            print(f"INFRA: unparseable generated_at: {generated_at!r}", file=sys.stderr)
            return EXIT_INFRA_ERROR

    # R1 S-Sec-4: inputs_hash recompute
    if args.recompute_inputs_hash and args.inputs_hash_paths_file:
        try:
            actual_hash = compute_inputs_hash(
                repo_root, Path(args.inputs_hash_paths_file)
            )
        except (FileNotFoundError, ValueError) as e:
            print(f"INFRA: inputs_hash recompute failed: {e}", file=sys.stderr)
            return EXIT_INFRA_ERROR
        declared_hash = verdict.get("inputs_hash", "").strip()
        if declared_hash != actual_hash:
            print(
                f"INVALID: inputs_hash mismatch — "
                f"declared='{declared_hash[:16]}', actual='{actual_hash[:16]}'",
                file=sys.stderr,
            )
            return EXIT_VERDICT_INVALID

    # R1 C5: Codex CLI pin enforcement
    if args.codex_cli_pin_file:
        min_v, max_v = parse_pin_range(Path(args.codex_cli_pin_file))
        if min_v and max_v:
            tool_versions = verdict.get("tool_versions", {})
            if not isinstance(tool_versions, dict):
                # Codex iter-6 P1 fix — malformed tool_versions (scalar /
                # non-dict) previously bypassed both semver + binary-SHA
                # checks. Now hard-fail.
                print(
                    f"INVALID: tool_versions field must be a dict, got "
                    f"{type(tool_versions).__name__}: {tool_versions!r}",
                    file=sys.stderr,
                )
                return EXIT_VERDICT_INVALID
            cli_v = tool_versions.get("codex_cli", "")
            if not semver_in_range(cli_v, min_v, max_v):
                print(
                    f"INVALID: codex_cli version {cli_v!r} not in pin "
                    f"range >={min_v},<{max_v}",
                    file=sys.stderr,
                )
                return EXIT_VERDICT_INVALID

    # PLAN-081 Phase 6-bis / T-8: Codex CLI binary SHA-256 pin enforcement
    if args.codex_cli_binary_sha256_file:
        pin_path = Path(args.codex_cli_binary_sha256_file)
        if not pin_path.exists():
            # ADVISORY skip per Codex iter-1 P1 — missing pin file is a
            # rollout state (e.g. legacy verdicts pre-Phase-6-bis); do NOT
            # hard-fail. release.yml step 15 still gates on the codex_cli
            # semver pin (R1 C5) which is mandatory.
            print(
                f"ADVISORY: codex-cli-binary-sha256-file not found at {pin_path}; "
                f"skipping T-8 binary-SHA pin check (semver pin still enforced)",
                file=sys.stderr,
            )
            expected_sha = ""
        else:
            expected_sha = ""
            for line in pin_path.read_text().splitlines():
                line = line.split("#", 1)[0].strip()
                if line:
                    expected_sha = line
                    break
        if expected_sha and len(expected_sha) == 64:
            tool_versions = verdict.get("tool_versions", {})
            if not isinstance(tool_versions, dict):
                # Codex iter-7 P1 fix — scalar/non-dict tool_versions
                # previously silently skipped binary-SHA check (only the
                # semver pin path enforced dict shape). Hard-fail
                # consistently regardless of which pin is being checked.
                print(
                    f"INVALID: tool_versions field must be a dict for binary-SHA "
                    f"check, got {type(tool_versions).__name__}: {tool_versions!r}",
                    file=sys.stderr,
                )
                return EXIT_VERDICT_INVALID
            declared_binary_sha = tool_versions.get(
                "codex_cli_binary_sha256", ""
            ).strip()
            if not declared_binary_sha:
                # When the pin file exists + is non-empty, verdict
                # envelope MUST carry the binary SHA — missing field is
                # a regression / pre-rollout legacy state. Per Codex
                # iter-5 P1 finding, this is hard-fail when pin file
                # provides authoritative SHA.
                print(
                    f"INVALID: codex-cli-binary-sha256-file pin '{pin_path}' "
                    f"exists + non-empty (sha='{expected_sha[:16]}'), but "
                    f"verdict envelope lacks tool_versions.codex_cli_binary_sha256",
                    file=sys.stderr,
                )
                return EXIT_VERDICT_INVALID
            if declared_binary_sha != expected_sha:
                print(
                    f"INVALID: codex_cli_binary_sha256 mismatch — "
                    f"declared='{declared_binary_sha[:16]}', "
                    f"pin='{expected_sha[:16]}'",
                    file=sys.stderr,
                )
                return EXIT_VERDICT_INVALID

    # ADR-182 (PLAN-163 T5.2): payload-pin manifest enforcement. The
    # verdict envelope carries the sha256 of the NATIVE codex payload
    # for the platform triple of the generating run (wire-shape defined
    # in ADR-182: scalar `tool_versions.codex_payload_sha256` + scalar
    # `tool_versions.codex_target_triple`); the validator compares it
    # against `payloads[<triple>].sha256` in the manifest. Fail-CLOSED
    # on everything except an unreadable manifest file (infra).
    if args.codex_pin_manifest_file:
        manifest_path = Path(args.codex_pin_manifest_file)
        try:
            manifest_raw = manifest_path.read_text(encoding="utf-8")
        except OSError as e:
            print(
                f"INFRA: codex-pin-manifest-file unreadable at "
                f"{manifest_path}: {e}",
                file=sys.stderr,
            )
            return EXIT_INFRA_ERROR
        try:
            manifest = json.loads(manifest_raw)
        except ValueError as e:
            print(
                f"INVALID: codex-pin-manifest-file is not valid JSON "
                f"({e}) — fail-CLOSED per ADR-182",
                file=sys.stderr,
            )
            return EXIT_VERDICT_INVALID
        if (
            not isinstance(manifest, dict)
            or manifest.get("schema") != 1
            or not isinstance(manifest.get("payloads"), dict)
        ):
            print(
                "INVALID: codex-pin-manifest-file schema violation "
                "(expected schema=1 + payloads dict) — fail-CLOSED per "
                "ADR-182",
                file=sys.stderr,
            )
            return EXIT_VERDICT_INVALID
        tool_versions = verdict.get("tool_versions", {})
        if not isinstance(tool_versions, dict):
            print(
                f"INVALID: tool_versions field must be a dict for "
                f"payload-pin check, got "
                f"{type(tool_versions).__name__}: {tool_versions!r}",
                file=sys.stderr,
            )
            return EXIT_VERDICT_INVALID
        declared_triple = str(
            tool_versions.get("codex_target_triple", "")
        ).strip()
        declared_payload_sha = str(
            tool_versions.get("codex_payload_sha256", "")
        ).strip()
        if not declared_triple or not declared_payload_sha:
            print(
                "INVALID: ADR-182 payload pin requested "
                f"(manifest='{manifest_path}') but verdict envelope "
                "lacks tool_versions.codex_target_triple and/or "
                "tool_versions.codex_payload_sha256",
                file=sys.stderr,
            )
            return EXIT_VERDICT_INVALID
        entry = manifest["payloads"].get(declared_triple)
        if not isinstance(entry, dict):
            print(
                f"INVALID: targetTriple '{declared_triple}' absent from "
                f"codex-pin-manifest payloads — fail-CLOSED per ADR-182",
                file=sys.stderr,
            )
            return EXIT_VERDICT_INVALID
        expected_payload_sha = str(entry.get("sha256", "")).strip()
        if not re.match(r"^[0-9a-f]{64}$", expected_payload_sha):
            print(
                f"INVALID: manifest entry for '{declared_triple}' has "
                f"malformed sha256 — fail-CLOSED per ADR-182",
                file=sys.stderr,
            )
            return EXIT_VERDICT_INVALID
        if declared_payload_sha != expected_payload_sha:
            print(
                f"INVALID: codex_payload_sha256 mismatch for "
                f"'{declared_triple}' — "
                f"declared='{declared_payload_sha[:16]}', "
                f"pin='{expected_payload_sha[:16]}'",
                file=sys.stderr,
            )
            return EXIT_VERDICT_INVALID

    # GPG signature presence (verifies via separate `git verify-tag` in
    # release.yml; here we just assert the field is present + non-empty)
    sig = verdict.get("gpg_signature", "")
    if not sig or sig.strip() == "":
        print("INVALID: gpg_signature field empty", file=sys.stderr)
        return EXIT_VERDICT_INVALID

    print(f"OK: verdict {args.release_tag} valid", file=sys.stdout)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
