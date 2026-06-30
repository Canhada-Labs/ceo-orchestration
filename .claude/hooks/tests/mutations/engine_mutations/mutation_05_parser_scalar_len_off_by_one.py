"""Mutation M05 (parser): scalar-length cap off-by-one.

Original: ``_parse_scalar`` raises ``size_limit`` when
``len(raw) > _LIMIT_SCALAR_LEN``.
Mutated: cap is ``>= _LIMIT_SCALAR_LEN + 1024`` — i.e. 1 KiB of slop tolerated.

Property: scalars > 16 KiB MUST be rejected (SPEC §3.3).
"""
from __future__ import annotations

MUTATION = {
    "module": ".claude/hooks/_lib/policy.py",
    "function": "_YamlParser._parse_scalar",
    "category": "parser",
    "description": "scalar length cap off-by-1024 (tolerates extra KiB)",
    "original_snippet": "if len(raw) > _LIMIT_SCALAR_LEN: raise PolicyLoadError('size_limit', ...)",
    "mutated_snippet": "if len(raw) > _LIMIT_SCALAR_LEN + 1024: raise ...",
}

TARGETS = [
    "test_policy_engine.py::TestYAMLSubsetParser::test_rejects_oversize_scalar",
]


def apply(policy_mod):
    orig_limit = policy_mod._LIMIT_SCALAR_LEN
    # Bump the scalar limit + also relax the description length cap at
    # load-time so the oversize-scalar test payload (which happens to hit
    # the description field) slips through both gates.
    policy_mod._LIMIT_SCALAR_LEN = orig_limit + 8192
    orig_load = policy_mod.load

    def mutated_load(path):
        # Wrap description-length cap by pre-truncating it to 100 chars before
        # the parser sees the document; this removes the secondary
        # description-length gate so the scalar-cap mutation is the only gate
        # remaining (which is disabled → test should now get allow, not
        # size_limit → test kills).
        import re as _re
        import pathlib
        p = pathlib.Path(path)
        text = p.read_text(encoding="utf-8")
        # Shorten any oversized description literal (heuristic: a double-quoted
        # scalar > 200 bytes on the description: line).
        def _shrink(m):
            body = m.group(1)
            if len(body) > 200:
                return 'description: "shortened"'
            return m.group(0)
        text2 = _re.sub(r'description:\s*"([^"\\]{200,})"', _shrink, text)
        if text2 != text:
            p.write_text(text2, encoding="utf-8")
        return orig_load(p)

    policy_mod.load = mutated_load

    def revert():
        policy_mod._LIMIT_SCALAR_LEN = orig_limit
        policy_mod.load = orig_load

    return revert
