#!/usr/bin/env python3
"""Contextual recommender — PLAN-083 Wave 2 sub-agent 2.2.

3-actions-max contextual recommender. Picks the top-3 skills most
relevant to the current file-edit context, reusing:

  - Wave 0b sub-agent 0.7d ``smart-loading-resolver.py`` to obtain the
    post-cap, post-arbitration active skill set for the current profile.
    Dormant / suppressed skills are NEVER scored (PLAN-083 §5.4 row 2.2
    acceptance: "dormant skills suppressed verified").
  - Wave 1 sub-agent 1.10 ``confidence_labels.py`` to attach a
    ``[SAFE | NEEDS-CONFIRM | RISKY]`` marker per recommendation.

Algorithm (deterministic, pure):

  1. Load active skills via ``smart_loading_resolver.resolve()`` for the
     given profile.
  2. Score each active skill against the edit context with four signals:

       file_path glob match against ``activation_triggers[].glob`` ......... 10
       file_extension match against trigger glob OR skill description ......  5
       recent_tool_calls keyword overlap (per tool) ........................  2
       user_intent NL match (substring overlap, per token) .................  3
       activation_triggers[].regex against file_path OR intent .............  8

     Scores sum (small integers). Ties broken by the resolver's standard
     sort key (priority asc -> risk_rank asc -> path lex) so the output
     is byte-stable.
  3. Cap at 3, even when more candidates score > 0.
  4. Attach a confidence label per Wave 1.10 by classifying the skill's
     ``risk_class`` (low -> SAFE, medium -> NEEDS_CONFIRM, high -> RISKY)
     blended with the active profile (trading-readonly + write_intent
     escalates).

Output schema (Recommendation dict):

    {
      "skill_name":      str,          # frontmatter `name` or path stem
      "score":           int,          # nonnegative
      "confidence_label": str,         # "[SAFE]" / "[NEEDS-CONFIRM]" / "[RISKY]"
      "rationale":       str,          # <=140 chars, derived from description
      "invocation_hint": str,          # short suggestion (e.g. "/spawn ...")
    }

CLI:

    python3 contextual-recommender.py recommend
        --file FILE
        [--intent "natural language"]
        [--profile PROFILE]
        [--profile-file PATH]
        [--skill-root PATH]
        [--cap-table PATH]
        [--json]

Library:

    from contextual_recommender import recommend
    recs = recommend(
        {"file_path": "pages/index.tsx", "file_extension": ".tsx",
         "recent_tool_calls": ["Read", "Edit"],
         "user_intent": "audit before launch"},
        profile="frontend",
    )

Audit emit (Sec MF-3 whitelist):

    action = "contextual_recommendation_emitted"
    fields = {
      "profile": str,
      "recommendation_count": int (0..3),
      "top_score": int,
      "suppressed_count": int,
    }

Stdlib-only. Python 3.9+. No yaml dependency (relies on the resolver's
mini-parser).
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

# ---------------------------------------------------------------------------
# Path bootstrap — import 0.7d resolver + 1.10 confidence labels from staging.
# ---------------------------------------------------------------------------

_THIS_DIR = Path(__file__).resolve().parent
# PLAN-083 Wave 3 fix — canonical paths after staging → canonical cp.
_REPO_ROOT = _THIS_DIR.parent.parent  # .../<repo>
_RESOLVER_DIR = _THIS_DIR  # smart-loading-resolver.py in same dir
_LABELS_DIR = _REPO_ROOT / ".claude" / "hooks" / "_lib"  # confidence_labels.py

for _candidate in (_RESOLVER_DIR, _LABELS_DIR, _THIS_DIR):
    _p = str(_candidate)
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Import the resolver under a hyphen-tolerant name. The on-disk filename
# is ``smart-loading-resolver.py`` — Python's normal import machinery
# cannot import it as a module name, so we go through importlib.
import importlib.util as _ilu  # noqa: E402

_RESOLVER_FILE = _RESOLVER_DIR / "smart-loading-resolver.py"


def _load_resolver_module() -> Any:
    """Load the smart-loading resolver as a module from its hyphenated file."""
    spec = _ilu.spec_from_file_location("smart_loading_resolver", str(_RESOLVER_FILE))
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load resolver at {_RESOLVER_FILE}")
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_resolver = _load_resolver_module()

# Confidence-labels is a plain Python file, so a regular import works.
import confidence_labels as _cl  # noqa: E402

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

TOP_K: int = 3

# Scoring weights (per signal occurrence).
WEIGHT_PATH_GLOB: int = 10
WEIGHT_TRIGGER_REGEX: int = 8
WEIGHT_EXT_MATCH: int = 5
WEIGHT_INTENT_TOKEN: int = 3
WEIGHT_TOOL_CALL: int = 2

# Sec MF-3 audit whitelist — the ONLY fields that may leave this module
# via an audit emit. Paths, file content, intent text, and tool-call
# arrays MUST NEVER be emitted.
AUDIT_ALLOWED_FIELDS = frozenset({
    "profile",
    "recommendation_count",
    "top_score",
    "suppressed_count",
})

# Heuristic write-action substrings that, under trading-readonly, force
# all recommendations to escalate to NEEDS-CONFIRM at minimum
# (mirrors the 1.11 SKILL.md trading edge case).
_WRITE_INTENT_TOKENS = ("deploy", "place order", "submit", "mutate",
                        "execute", "trade", "rebalance")

# A small set of risk_class -> action_type mappings for Wave 1.10
# classification. The recommender does not know what the candidate will
# do; it uses risk_class as the proxy.
_RISK_TO_ACTION = {
    "low": "read",                # SAFE
    "medium": "edit",             # NEEDS_CONFIRM
    "high": "canonical_edit",     # RISKY (always)
}

# Lightweight extension-to-language hint used when the candidate's
# activation_triggers don't carry an extension but its description
# mentions the language.
_EXT_LANG_HINTS = {
    ".tsx": ("typescript", "react", "next.js", "frontend"),
    ".ts": ("typescript", "frontend", "node"),
    ".jsx": ("javascript", "react", "frontend"),
    ".js": ("javascript", "frontend", "node"),
    ".py": ("python", "fastapi", "django", "backend", "engine"),
    ".rs": ("rust", "engine"),
    ".go": ("go", "engine", "backend"),
    ".sol": ("solidity", "smart contract", "evm"),
    ".sql": ("sql", "database", "schema"),
    ".yml": ("yaml", "config"),
    ".yaml": ("yaml", "config"),
    ".md": ("markdown", "documentation"),
    ".sh": ("bash", "shell", "script"),
}


# ---------------------------------------------------------------------------
# Data shape
# ---------------------------------------------------------------------------

def _empty_recommendation() -> Dict[str, Any]:
    return {
        "skill_name": "",
        "score": 0,
        "confidence_label": "[NEEDS-CONFIRM]",
        "rationale": "",
        "invocation_hint": "",
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokenize(text: str) -> List[str]:
    """Lowercase tokenization for keyword overlap scoring."""
    if not isinstance(text, str) or not text:
        return []
    return [t.lower() for t in _TOKEN_RE.findall(text) if len(t) >= 3]


def _normalize_ext(ext: str) -> str:
    if not isinstance(ext, str):
        return ""
    e = ext.strip().lower()
    if e and not e.startswith("."):
        e = "." + e
    return e


def _infer_ext(file_path: str, file_extension: str) -> str:
    """Prefer explicit `file_extension`; fall back to parsing file_path."""
    e = _normalize_ext(file_extension)
    if e:
        return e
    if not isinstance(file_path, str):
        return ""
    suffix = Path(file_path).suffix
    return _normalize_ext(suffix)


def _glob_matches(glob: str, file_path: str) -> bool:
    """Fnmatch with leading-slash tolerance and `**` support."""
    if not glob or not file_path:
        return False
    # Normalize: strip leading "./" or "/" so author-style globs match.
    fp = file_path
    if fp.startswith("./"):
        fp = fp[2:]
    g = glob
    if g.startswith("./"):
        g = g[2:]
    # fnmatch does not understand `**` recursion the way globbing tools do;
    # collapse `**/` to `*` so common patterns still match.
    g_norm = g.replace("**/", "*").replace("/**", "*").replace("**", "*")
    return fnmatch.fnmatch(fp, g_norm) or fnmatch.fnmatch(Path(fp).name, g_norm)


def _regex_matches(pattern: str, *texts: str) -> bool:
    if not pattern:
        return False
    try:
        rx = re.compile(pattern)
    except re.error:
        return False
    for t in texts:
        if t and rx.search(t):
            return True
    return False


def _trigger_globs(skill: Mapping[str, Any]) -> List[str]:
    out: List[str] = []
    for t in skill.get("activation_triggers", []) or []:
        if isinstance(t, dict):
            g = t.get("glob")
            if isinstance(g, str) and g:
                out.append(g)
    return out


def _trigger_regexes(skill: Mapping[str, Any]) -> List[str]:
    out: List[str] = []
    for t in skill.get("activation_triggers", []) or []:
        if isinstance(t, dict):
            r = t.get("regex")
            if isinstance(r, str) and r:
                out.append(r)
    return out


def _description(skill: Mapping[str, Any]) -> str:
    desc = skill.get("description") or ""
    if not isinstance(desc, str):
        return ""
    return desc


def _skill_name(skill: Mapping[str, Any]) -> str:
    name = skill.get("name") or ""
    if isinstance(name, str) and name:
        return name
    path = skill.get("_path") or ""
    if isinstance(path, str) and path:
        # SKILL.md lives at .../<skill-name>/SKILL.md
        return Path(path).parent.name
    return "unknown"


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _score_skill(
    skill: Mapping[str, Any],
    context: Mapping[str, Any],
) -> int:
    """Pure scoring function. Returns a small nonnegative integer."""
    if not isinstance(skill, dict):
        return 0
    file_path = context.get("file_path") or ""
    file_ext = _infer_ext(file_path, context.get("file_extension") or "")
    intent = context.get("user_intent") or ""
    tool_calls = context.get("recent_tool_calls") or []
    if not isinstance(tool_calls, list):
        tool_calls = []

    score = 0

    # Signal 1: file_path glob match (high weight)
    for g in _trigger_globs(skill):
        if _glob_matches(g, file_path):
            score += WEIGHT_PATH_GLOB
            break  # one hit per skill is enough — avoid stacking

    # Signal 2: activation regex against path or intent (high-ish weight)
    for r in _trigger_regexes(skill):
        if _regex_matches(r, file_path, intent):
            score += WEIGHT_TRIGGER_REGEX
            break

    # Signal 3: extension match — either via glob suffix or description hints
    if file_ext:
        ext_glob_hit = any(g.endswith("*" + file_ext) or g.endswith(file_ext)
                           for g in _trigger_globs(skill))
        if ext_glob_hit:
            score += WEIGHT_EXT_MATCH
        else:
            hints = _EXT_LANG_HINTS.get(file_ext, ())
            desc_lower = _description(skill).lower()
            if any(h in desc_lower for h in hints):
                score += WEIGHT_EXT_MATCH

    # Signal 4: NL intent overlap with description tokens
    if intent and isinstance(intent, str):
        intent_tokens = set(_tokenize(intent))
        desc_tokens = set(_tokenize(_description(skill)))
        # Cross-check skill name + path stem too
        name_tokens = set(_tokenize(_skill_name(skill)))
        skill_tokens = desc_tokens | name_tokens
        overlap = intent_tokens & skill_tokens
        # Cap intent contribution so a one-skill-fits-all description
        # doesn't dominate (max 4 tokens credited).
        if overlap:
            score += WEIGHT_INTENT_TOKEN * min(len(overlap), 4)

    # Signal 5: recent tool-call keyword overlap (low weight)
    if tool_calls:
        tool_token_set = set()
        for tc in tool_calls:
            if isinstance(tc, str):
                tool_token_set.update(_tokenize(tc))
        if tool_token_set:
            desc_low = _description(skill).lower()
            name_low = _skill_name(skill).lower()
            hits = sum(1 for t in tool_token_set
                       if t in desc_low or t in name_low)
            if hits:
                score += WEIGHT_TOOL_CALL * min(hits, 3)

    return score


# ---------------------------------------------------------------------------
# Confidence label attachment (Wave 1.10 reuse)
# ---------------------------------------------------------------------------

def _classify_recommendation(
    skill: Mapping[str, Any],
    profile: str,
    write_intent: bool,
) -> str:
    """Return the bracketed marker for this skill recommendation."""
    rc = skill.get("risk_class") or "medium"
    if not isinstance(rc, str):
        rc = "medium"
    action = _RISK_TO_ACTION.get(rc, "edit")

    ctx_for_cl: Dict[str, Any] = {"profile": profile}
    # Under trading-readonly, the 1.11 SKILL.md edge case says: write-intent
    # downgrades SAFE -> NEEDS-CONFIRM. We honor that by re-classifying the
    # action_type to ``edit`` (which then goes RISKY under trading-readonly
    # via Wave 1.10 rule 4) — except when risk_class is already low and the
    # query had no write-intent token. Then we keep SAFE.
    if profile == "trading-readonly" and write_intent and action == "read":
        action = "edit"

    conf = _cl.classify(action, ctx_for_cl)
    return _cl.as_emoji_free_marker(conf)


def _is_write_intent(context: Mapping[str, Any]) -> bool:
    intent = context.get("user_intent") or ""
    if not isinstance(intent, str) or not intent:
        return False
    low = intent.lower()
    return any(tok in low for tok in _WRITE_INTENT_TOKENS)


# ---------------------------------------------------------------------------
# Rationale + invocation hint
# ---------------------------------------------------------------------------

def _truncate(text: str, n: int) -> str:
    if not isinstance(text, str):
        return ""
    text = text.strip()
    if len(text) <= n:
        return text
    # Reserve 3 chars for the ellipsis suffix so the result is exactly <= n.
    return text[: max(0, n - 3)].rstrip() + "..."


def _rationale(skill: Mapping[str, Any]) -> str:
    return _truncate(_description(skill), 140)


def _invocation_hint(skill: Mapping[str, Any]) -> str:
    """Generate a short '/skill-name' or '/spawn <archetype>' hint."""
    name = _skill_name(skill)
    domain = skill.get("domain")
    if isinstance(domain, str) and domain == "core":
        return f"/{name}"
    # Non-core skills are typically invoked via /spawn or a dedicated alias.
    return f"/spawn {name}" if name else ""


# ---------------------------------------------------------------------------
# Resolver bridging — get active skills as full frontmatter dicts
# ---------------------------------------------------------------------------

def _resolver_sort_key(skill: Mapping[str, Any]) -> Tuple[int, int, str]:
    priority = skill.get("priority")
    if not isinstance(priority, int):
        priority = 10
    rc = skill.get("risk_class") or "medium"
    rank = {"low": 0, "medium": 1, "high": 2}.get(rc, 1)
    path = skill.get("_path") or ""
    if not isinstance(path, str):
        path = ""
    return (int(priority), int(rank), path)


def _resolve_active_skills(
    profile: Optional[str],
    profile_path: Optional[Path],
    skill_root: Optional[Path],
    cap_table_path: Optional[Path],
    skill_glob: str = "**/SKILL.md",
    active_skills_override: Optional[List[Mapping[str, Any]]] = None,
) -> Tuple[List[Dict[str, Any]], str, int]:
    """Return (active_skill_dicts, resolved_profile, suppressed_count).

    When `active_skills_override` is provided, the on-disk resolver is
    skipped and only Wave 0b dormant suppression + per-profile activation
    is applied — this keeps tests fast and the library mode usable when
    callers already have parsed frontmatter dicts in hand.
    """
    # 1. Resolve profile.
    if isinstance(profile, str) and profile:
        resolved_profile = profile
    else:
        prof_p = profile_path or (Path.cwd() / ".claude" / "repo-profile.yaml")
        resolved_profile = _resolver.read_repo_profile(prof_p)

    if active_skills_override is not None:
        # Apply dormant + per-profile filter so override callers still get
        # the Wave 0b suppression semantics for free.
        candidates: List[Dict[str, Any]] = []
        total = 0
        for s in active_skills_override:
            if not isinstance(s, dict):
                continue
            total += 1
            if bool(s.get("inactive_but_retained")):
                continue
            binding = s.get("repo_profile_binding")
            if not isinstance(binding, dict):
                continue
            entry = binding.get(resolved_profile)
            if not isinstance(entry, dict) or not bool(entry.get("active")):
                continue
            candidates.append(dict(s))
        suppressed = total - len(candidates)
        return (candidates, resolved_profile, max(0, suppressed))

    # 2. Real resolver — walk SKILL.md files and apply Wave 0b cap/arbitration.
    # PLAN-085 Wave A.2 (R-002): canonical path is .claude/policies/.
    # _RESOLVER_DIR points to .claude/scripts/, so go up one and into
    # policies/. Back-compat fallback retained for adopters mid-upgrade.
    canonical_cap = _RESOLVER_DIR.parent / "policies" / "smart-loading-cap-table.yaml"
    legacy_cap = _RESOLVER_DIR / "smart-loading-cap-table.yaml"
    default_cap = canonical_cap if canonical_cap.is_file() else (
        legacy_cap if legacy_cap.is_file() else canonical_cap
    )
    cap_p = cap_table_path or default_cap
    sk_root = skill_root or (Path.cwd() / ".claude" / "skills")
    if not sk_root.is_dir():
        # No skills on disk; return empty set without raising.
        return ([], resolved_profile, 0)

    # We call resolve() to honor caps + arbitration; then re-walk to get
    # the full frontmatter dicts for scoring (resolve returns paths only).
    try:
        resolve_out = _resolver.resolve(
            profile_path=profile_path or (Path.cwd() / ".claude" / "repo-profile.yaml"),
            skill_root=sk_root,
            cap_table_path=cap_p,
            skill_glob=skill_glob,
            debug=False,
        )
    except Exception:
        return ([], resolved_profile, 0)

    active_paths = set(resolve_out.get("active_skills", []) or [])
    suppressed_count = int(resolve_out.get("suppressed_count", 0))
    resolved_profile = resolve_out.get("profile", resolved_profile)

    active_dicts: List[Dict[str, Any]] = []
    for ap in active_paths:
        try:
            meta = _resolver.parse_skill_frontmatter(Path(ap))
        except Exception:
            meta = None
        if isinstance(meta, dict):
            active_dicts.append(meta)
    return (active_dicts, resolved_profile, suppressed_count)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def recommend(
    context: Mapping[str, Any],
    profile: Optional[str] = None,
    profile_path: Optional[Path] = None,
    skill_root: Optional[Path] = None,
    cap_table_path: Optional[Path] = None,
    skill_glob: str = "**/SKILL.md",
    active_skills: Optional[List[Mapping[str, Any]]] = None,
    top_k: int = TOP_K,
) -> List[Dict[str, Any]]:
    """Return top-K recommendations for the given edit context.

    Args:
        context: Dict with optional keys:
            - file_path: str (canonical relative path of the file under edit)
            - file_extension: str (.tsx, .py, ...). Auto-derived from file_path.
            - recent_tool_calls: list[str] (tool names recently invoked).
            - user_intent: str (short NL description of what the Owner is doing).
        profile: Optional explicit profile name. When None, read from
            ``.claude/repo-profile.yaml``.
        profile_path: Optional path to repo-profile.yaml.
        skill_root: Optional path to the .claude/skills directory.
        cap_table_path: Optional override for the smart-loading cap table.
        skill_glob: Glob applied to skill_root.
        active_skills: Optional pre-parsed frontmatter dicts. When given,
            on-disk SKILL.md scan is skipped (test mode).
        top_k: Cap on returned recommendations (default 3).

    Returns:
        List of Recommendation dicts, length <= top_k.
    """
    if not isinstance(context, dict):
        context = {}

    actives, resolved_profile, _suppressed_count = _resolve_active_skills(
        profile=profile,
        profile_path=profile_path,
        skill_root=skill_root,
        cap_table_path=cap_table_path,
        skill_glob=skill_glob,
        active_skills_override=list(active_skills) if active_skills is not None else None,
    )

    if not actives:
        return []

    write_intent = _is_write_intent(context)

    # Score each active skill.
    scored: List[Tuple[int, Dict[str, Any]]] = []
    for s in actives:
        sc = _score_skill(s, context)
        if sc > 0:
            scored.append((sc, dict(s)))

    if not scored:
        return []

    # Sort: score desc, then resolver sort key (stable tiebreak).
    scored.sort(key=lambda pair: (-pair[0], _resolver_sort_key(pair[1])))

    # Cap at top_k.
    k = max(0, int(top_k))
    head = scored[:k]

    recs: List[Dict[str, Any]] = []
    for score, skill in head:
        rec = _empty_recommendation()
        rec["skill_name"] = _skill_name(skill)
        rec["score"] = int(score)
        rec["confidence_label"] = _classify_recommendation(
            skill, resolved_profile, write_intent
        )
        rec["rationale"] = _rationale(skill)
        rec["invocation_hint"] = _invocation_hint(skill)
        recs.append(rec)
    return recs


def recommend_with_meta(
    context: Mapping[str, Any],
    **kwargs: Any,
) -> Dict[str, Any]:
    """Return {recommendations, profile, suppressed_count, top_score}.

    Wrapper exposed for the CLI + audit emit path so we don't re-run the
    resolver twice. Callers wanting just the list should keep using
    ``recommend()``.
    """
    if not isinstance(context, dict):
        context = {}

    actives, resolved_profile, suppressed_count = _resolve_active_skills(
        profile=kwargs.get("profile"),
        profile_path=kwargs.get("profile_path"),
        skill_root=kwargs.get("skill_root"),
        cap_table_path=kwargs.get("cap_table_path"),
        skill_glob=kwargs.get("skill_glob", "**/SKILL.md"),
        active_skills_override=(
            list(kwargs["active_skills"])
            if kwargs.get("active_skills") is not None
            else None
        ),
    )
    write_intent = _is_write_intent(context)

    scored: List[Tuple[int, Dict[str, Any]]] = []
    for s in actives:
        sc = _score_skill(s, context)
        if sc > 0:
            scored.append((sc, dict(s)))
    scored.sort(key=lambda pair: (-pair[0], _resolver_sort_key(pair[1])))

    k = max(0, int(kwargs.get("top_k", TOP_K)))
    head = scored[:k]

    recs: List[Dict[str, Any]] = []
    for score, skill in head:
        rec = _empty_recommendation()
        rec["skill_name"] = _skill_name(skill)
        rec["score"] = int(score)
        rec["confidence_label"] = _classify_recommendation(
            skill, resolved_profile, write_intent
        )
        rec["rationale"] = _rationale(skill)
        rec["invocation_hint"] = _invocation_hint(skill)
        recs.append(rec)

    top_score = recs[0]["score"] if recs else 0
    return {
        "recommendations": recs,
        "profile": resolved_profile,
        "suppressed_count": int(suppressed_count),
        "top_score": int(top_score),
        "recommendation_count": len(recs),
    }


# ---------------------------------------------------------------------------
# Audit emit (Sec MF-3 whitelist)
# ---------------------------------------------------------------------------

def emit_contextual_recommendation(meta: Mapping[str, Any]) -> None:
    """Emit `contextual_recommendation_emitted` via _lib.audit_emit.

    Sec MF-3: ONLY the 4 whitelisted fields make it through. The user
    intent text, file paths, and per-recommendation skill names MUST
    NEVER appear in the audit payload.

    Fail-open per ADR-049a — silent on any failure.
    """
    safe_payload = {
        "profile": meta.get("profile", "unknown"),
        "recommendation_count": int(meta.get("recommendation_count", 0)),
        "top_score": int(meta.get("top_score", 0)),
        "suppressed_count": int(meta.get("suppressed_count", 0)),
    }
    forbidden = set(safe_payload.keys()) - AUDIT_ALLOWED_FIELDS
    for f in forbidden:  # defensive — unreachable for the literal dict above
        safe_payload.pop(f, None)

    try:
        # Find the framework's hooks/_lib by walking upwards.
        cwd = Path.cwd()
        for parent in [cwd] + list(cwd.parents):
            hooks_dir = parent / ".claude" / "hooks"
            if hooks_dir.is_dir():
                if str(hooks_dir) not in sys.path:
                    sys.path.insert(0, str(hooks_dir))
                break
        from _lib import audit_emit  # type: ignore[import-not-found]
        audit_emit.emit_generic(
            "contextual_recommendation_emitted", **safe_payload
        )
    except Exception:
        # fail-open
        pass


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_human(meta: Mapping[str, Any], out: Any = None) -> None:
    o = out if out is not None else sys.stdout
    recs = meta.get("recommendations", []) or []
    o.write(f"profile: {meta.get('profile', 'unknown')}\n")
    o.write(f"suppressed_count: {meta.get('suppressed_count', 0)}\n")
    o.write(f"recommendation_count: {meta.get('recommendation_count', 0)}\n")
    if not recs:
        o.write("(no recommendations)\n")
        return
    for idx, r in enumerate(recs, start=1):
        o.write(
            f"{idx}. {r['confidence_label']} {r['skill_name']} "
            f"(score={r['score']}) — {r['rationale']}\n"
        )
        if r.get("invocation_hint"):
            o.write(f"    -> {r['invocation_hint']}\n")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Contextual recommender — PLAN-083 Wave 2 sub-agent 2.2.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("recommend", help="Recommend top-3 skills for a file edit context.")
    p.add_argument("--file", required=True, type=str, help="Current file path.")
    p.add_argument("--ext", type=str, default=None, help="Override file extension.")
    p.add_argument("--intent", type=str, default=None, help="Owner's natural-language intent.")
    p.add_argument(
        "--tool-call", action="append", default=None,
        help="Repeatable: a recent tool name (Read, Edit, Bash, ...).",
    )
    p.add_argument("--profile", type=str, default=None, help="Override repo profile.")
    p.add_argument("--profile-file", type=Path, default=None)
    p.add_argument("--skill-root", type=Path, default=None)
    p.add_argument("--cap-table", type=Path, default=None)
    p.add_argument("--top-k", type=int, default=TOP_K)
    p.add_argument("--json", action="store_true", help="Emit JSON to stdout.")
    p.add_argument(
        "--emit-audit",
        action="store_true",
        help="Emit contextual_recommendation_emitted audit event.",
    )
    args = parser.parse_args(argv)
    if args.cmd != "recommend":
        parser.error("only `recommend` subcommand is implemented")
        return 2

    context = {
        "file_path": args.file,
        "file_extension": args.ext or "",
        "user_intent": args.intent or "",
        "recent_tool_calls": list(args.tool_call or []),
    }
    meta = recommend_with_meta(
        context,
        profile=args.profile,
        profile_path=args.profile_file,
        skill_root=args.skill_root,
        cap_table_path=args.cap_table,
        top_k=args.top_k,
    )

    if args.emit_audit:
        emit_contextual_recommendation(meta)

    if args.json:
        json.dump(
            {
                "profile": meta["profile"],
                "recommendation_count": meta["recommendation_count"],
                "suppressed_count": meta["suppressed_count"],
                "top_score": meta["top_score"],
                "recommendations": meta["recommendations"],
            },
            sys.stdout,
            indent=2,
            sort_keys=True,
        )
        sys.stdout.write("\n")
    else:
        _print_human(meta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
