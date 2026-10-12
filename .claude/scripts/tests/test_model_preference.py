"""test_model_preference.py — PLAN-176 W1a, half 1: the P (preference) layer.

``.claude/data/models-preference.json`` maps stable aliases to concrete model
ids. The ceiling is the T layer: every value must be a member of
``AVAILABLE_MODELS_WORKING_SET`` in ADR-149 (PLAN-176 §3.1 — non-VETO
surfaces). This test READS that block through the W0a reader
(``read_adr_blocks`` of ``check-model-currency.py``, AST over the fenced
blocks, fail-closed on ambiguity); it never types a model id, so a working-set
change (e.g. a new id added by an ADR-149 amendment) needs no edit here.

The closed schema lives HERE until the W1b resolver (canonical) moves it into
the T registry. Until then the file is inert: this test reads it, but no
runtime code uses it to select a model.

The reader is loaded in ``setUp``, inside the TestEnvContext isolation, and is
never registered in ``sys.modules``: importing this module (``--collect-only``
included) does not execute the detector.

Cases — each with a RED control, so a green run is evidence:
  1. preference_layer_validates_and_resolves_an_alias  (the W1a AC)
  2. alias_outside_working_set_is_a_named_failure
  3. working_set_is_read_from_adr149_not_typed  (disposable ADR copy, fed
     through the SAME path setUp uses)
  4. closed_schema_names_each_violation  (one mutant per rule)
"""
from __future__ import annotations

import ast
import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List, Sequence

# TestEnvContext (S79 hygiene lesson — every test uses isolated env)
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
PREFERENCE_FILE = REPO_ROOT / ".claude" / "data" / "models-preference.json"
ADR_149 = REPO_ROOT / ".claude" / "adr" / "ADR-149-model-id-allowlist.md"
DETECTOR = REPO_ROOT / ".claude" / "scripts" / "check-model-currency.py"

#: Closed schema: exactly these top-level keys, and this version.
SCHEMA_KEYS = frozenset({"_note", "schema", "aliases"})
SCHEMA_VERSION = 1
#: The CEO_MODEL_PREFERENCE value grammar of PLAN-176 §3.2 — an alias can
#: travel through that variable. fullmatch, never ``$`` (which admits a
#: trailing newline).
ALIAS_RE = re.compile(r"[a-z0-9][a-z0-9.-]{0,63}")


def _load_reader():
    """Load the W0a detector (hyphenated file) as an UNREGISTERED module."""
    spec = importlib.util.spec_from_file_location(
        "_p176_w1a_adr149_reader", DETECTOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def drop_member(reader, text, block, member):
    # type: (Any, str, str, str) -> str
    """ADR text with ``member`` removed from ``block``, located by AST.

    Uses the reader's own grammar (its fence regex and assignment matcher)
    and rewrites only the literal that holds the elements, so the quote
    style, comments and trailing commas of the ADR do not matter.
    Fail-closed: exactly one definition, holding ``member`` exactly once.
    """
    found = []
    for fence in reader._FENCE_RE.finditer(text):
        try:
            tree = ast.parse(fence.group(1))
        except SyntaxError:
            continue
        found += [(fence, node.value) for node in tree.body
                  if reader._assign_target(node) == block]
    if len(found) != 1:
        raise AssertionError("%s: %d definitions" % (block, len(found)))
    fence, literal = found[0]
    if isinstance(literal, ast.Call):  # frozenset({...})
        literal = literal.args[0]
    kept = [e.value for e in literal.elts if e.value != member]
    if len(kept) != len(literal.elts) - 1:
        raise AssertionError("%s: %s not exactly once" % (block, member))
    raw = fence.group(1).encode("utf-8")  # ast offsets count UTF-8 bytes
    line = [0] + [i + 1 for i, b in enumerate(raw) if b == 0x0A]
    a = line[literal.lineno - 1] + literal.col_offset
    z = line[literal.end_lineno - 1] + literal.end_col_offset
    body = raw[:a] + repr(tuple(kept)).encode("utf-8") + raw[z:]
    return text[:fence.start(1)] + body.decode("utf-8") + text[fence.end(1):]


def violations(text, working_set, trust_ids):
    # type: (str, Sequence[str], Sequence[str]) -> List[str]
    """Every closed-schema violation of a preference document, NAMED."""
    dups = []  # type: List[str]

    def hook(pairs):
        keys = [k for k, _ in pairs]
        dups.extend(sorted({k for k in keys if keys.count(k) > 1}))
        return dict(pairs)

    try:
        doc = json.loads(text, object_pairs_hook=hook)
    except ValueError as exc:
        return ["not-json: %s" % exc]
    out = ["duplicate-key: %s" % k for k in dups]
    if not isinstance(doc, dict):
        return out + ["top-level-not-object"]
    out += ["unknown-key: %s" % k for k in sorted(set(doc) - SCHEMA_KEYS)]
    out += ["missing-key: %s" % k for k in sorted(SCHEMA_KEYS - set(doc))]
    note = doc.get("_note")
    if "_note" in doc and (not isinstance(note, str) or not note.strip()):
        out.append("note-not-text")
    schema = doc.get("schema")
    if "schema" in doc and (type(schema) is not int  # a bool is NOT 1
                            or schema != SCHEMA_VERSION):
        out.append("schema-version: %r (want %d)" % (schema, SCHEMA_VERSION))
    if "aliases" not in doc:
        return out
    aliases = doc["aliases"]
    if not isinstance(aliases, dict) or not aliases:
        return out + ["aliases-not-a-non-empty-object"]
    ws, trust = set(working_set), set(trust_ids)
    for alias in sorted(aliases):
        target = aliases[alias]
        if not ALIAS_RE.fullmatch(alias):
            out.append("alias-grammar: %r" % alias)
        if alias in trust:
            out.append("alias-shadows-trust-id: %s" % alias)
        if not isinstance(target, str):
            out.append("alias-target-not-string: %s" % alias)
        elif target not in ws:
            out.append("alias-outside-working-set: %s -> %s" % (alias, target))
    return out


class _Base(TestEnvContext):
    def setUp(self):
        super().setUp()
        try:
            self.reader = _load_reader()  # inside the isolation, not at import
            self.veto = self.load_trust(ADR_149)["VETO_FLOOR_ALLOWED"]
            self.text = PREFERENCE_FILE.read_text(encoding="utf-8")
            self.doc = json.loads(self.text)  # type: Dict[str, Any]
        except BaseException:
            self.tearDown()  # unittest skips tearDown when setUp raises
            raise

    def load_trust(self, adr_path):
        # type: (Path) -> Dict[str, List[str]]
        """The ONE path from an ADR file to the trust sets: read, never typed."""
        blocks = self.reader.read_adr_blocks(adr_path)
        self.ws = blocks["AVAILABLE_MODELS_WORKING_SET"]
        self.trust = sorted(set(self.ws) | set(blocks["VETO_FLOOR_ALLOWED"]))
        return blocks

    def check(self, doc_or_text):
        text = (doc_or_text if isinstance(doc_or_text, str)
                else json.dumps(doc_or_text))
        return violations(text, self.ws, self.trust)


class TestModelPreferenceLayer(_Base):

    def test_preference_layer_validates_and_resolves_an_alias(self):
        self.assertEqual(self.check(self.text), [],
                         "%s breaks the closed schema" % PREFERENCE_FILE)
        aliases = self.doc["aliases"]
        self.assertGreaterEqual(len(aliases), 1)
        for alias, target in sorted(aliases.items()):
            self.assertIn(target, self.ws,
                          "%s -> %s is outside the ADR-149 working set"
                          % (alias, target))

    def test_alias_outside_working_set_is_a_named_failure(self):
        alias = sorted(self.doc["aliases"])[0]
        outside = max(self.ws, key=len) + "-not-in-working-set"  # derived
        self.assertNotIn(outside, self.ws)
        doc = json.loads(self.text)
        doc["aliases"][alias] = outside
        self.assertEqual(
            self.check(doc),
            ["alias-outside-working-set: %s -> %s" % (alias, outside)])

    def test_working_set_is_read_from_adr149_not_typed(self):
        alias, target = sorted(self.doc["aliases"].items())[0]
        copy = self.project_dir / "ADR-149-copy.md"
        copy.write_text(drop_member(
            self.reader, ADR_149.read_text(encoding="utf-8"),
            "AVAILABLE_MODELS_WORKING_SET", target), encoding="utf-8")
        blocks = self.load_trust(copy)  # the same path setUp takes
        self.assertNotIn(target, self.ws)
        self.assertEqual(blocks["VETO_FLOOR_ALLOWED"], self.veto)  # one block
        self.assertIn("alias-outside-working-set: %s -> %s" % (alias, target),
                      self.check(self.text))

    def test_closed_schema_names_each_violation(self):
        base = json.loads(self.text)
        alias, target = sorted(base["aliases"].items())[0]
        other = sorted(self.ws)[0]

        def with_(key, value):
            doc = json.loads(self.text)
            doc[key] = value
            return doc

        def without(key):
            doc = json.loads(self.text)
            del doc[key]
            return doc

        dup = '{"_note": "x", "schema": 1, "aliases": {%s: %s, %s: %s}}' % (
            json.dumps(alias), json.dumps(target),
            json.dumps(alias), json.dumps(other))
        mutants = [
            ("extra key", with_("ceiling", "VETO_FLOOR_ALLOWED"),
             "unknown-key: ceiling"),
            ("missing note", without("_note"), "missing-key: _note"),
            ("missing schema", without("schema"), "missing-key: schema"),
            ("missing aliases", without("aliases"), "missing-key: aliases"),
            ("empty note", with_("_note", " "), "note-not-text"),
            ("schema 2", with_("schema", 2), "schema-version"),
            ("schema bool", with_("schema", True), "schema-version"),
            ("empty aliases", with_("aliases", {}),
             "aliases-not-a-non-empty-object"),
            ("aliases list", with_("aliases", [target]),
             "aliases-not-a-non-empty-object"),
            ("upper alias", with_("aliases", {alias.upper(): target}),
             "alias-grammar"),
            ("newline alias", with_("aliases", {alias + "\n": target}),
             "alias-grammar"),
            ("path alias", with_("aliases", {"../" + alias: target}),
             "alias-grammar"),
            ("shadowing alias", with_("aliases", {self.trust[0]: target}),
             "alias-shadows-trust-id: %s" % self.trust[0]),
            ("non-string target", with_("aliases", {alias: 1}),
             "alias-target-not-string: %s" % alias),
            ("duplicate key", dup, "duplicate-key: %s" % alias),
            ("not json", self.text.rstrip()[:-1], "not-json"),
            ("top-level list", [base], "top-level-not-object"),
        ]
        self.assertEqual(self.check(base), [])  # the base is clean
        for label, mutant, expected in mutants:
            with self.subTest(mutant=label):
                got = self.check(mutant)
                self.assertTrue(any(v.startswith(expected) for v in got),
                                "%s: want %r in %r" % (label, expected, got))


if __name__ == "__main__":
    unittest.main()
