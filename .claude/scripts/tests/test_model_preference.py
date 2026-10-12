"""test_model_preference.py — PLAN-176 W1a, half 1: the P (preference) layer.

``.claude/data/models-preference.json`` maps stable aliases to concrete model
ids. The ceiling is the T layer: every value must be a member of
``AVAILABLE_MODELS_WORKING_SET`` in ADR-149 (PLAN-176 §3.1 — non-VETO
surfaces). This test READS that block through the W0a reader
(``read_adr_blocks`` of ``check-model-currency.py``, AST over the fenced
blocks, fail-closed on ambiguity); it never types a model id, so a working-set
change (e.g. a new id added by an ADR-149 amendment) needs no edit here.

The closed schema lives HERE until the W1b resolver (canonical) moves it into
the T registry; the file is inert until then (no code reads it).

Cases — each with a RED control, so a green run is evidence:
  1. preference_layer_validates_and_resolves_an_alias  (the W1a AC)
  2. alias_outside_working_set_is_a_named_failure
  3. working_set_is_read_from_adr149_not_typed  (disposable ADR copy)
  4. closed_schema_names_each_violation  (one mutant per rule)
"""
from __future__ import annotations

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
    """Load the W0a detector (hyphenated file) under a private module name."""
    name = "_p176_w1a_adr149_reader"
    spec = importlib.util.spec_from_file_location(name, DETECTOR)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


READER = _load_reader()


def trust_sets(adr_path=ADR_149):
    # type: (Path) -> Dict[str, List[str]]
    """The two ADR-149 blocks, read (never typed)."""
    return READER.read_adr_blocks(adr_path)


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
        blocks = trust_sets()
        self.ws = blocks["AVAILABLE_MODELS_WORKING_SET"]
        self.trust = sorted(set(self.ws) | set(blocks["VETO_FLOOR_ALLOWED"]))
        self.text = PREFERENCE_FILE.read_text(encoding="utf-8")
        self.doc = json.loads(self.text)  # type: Dict[str, Any]

    def check(self, doc_or_text, ws=None):
        text = (doc_or_text if isinstance(doc_or_text, str)
                else json.dumps(doc_or_text))
        return violations(text, self.ws if ws is None else ws, self.trust)


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
        text = ADR_149.read_text(encoding="utf-8")
        heads = [m.start() for m in re.finditer(
            r"^AVAILABLE_MODELS_WORKING_SET\b", text, re.M)]
        self.assertEqual(len(heads), 1, "block definition not unique")
        start = heads[0]
        end = text.index("```", start)
        line_re = re.compile(r'^[ \t]*"%s",[^\n]*\n' % re.escape(target), re.M)
        block, hits = line_re.subn("", text[start:end])
        self.assertEqual(hits, 1, "target %s not exactly once in the block"
                         % target)
        copy = self.project_dir / "ADR-149-copy.md"
        copy.write_text(text[:start] + block + text[end:], encoding="utf-8")
        blocks = trust_sets(copy)
        self.assertNotIn(target, blocks["AVAILABLE_MODELS_WORKING_SET"])
        self.assertEqual(blocks["VETO_FLOOR_ALLOWED"],
                         trust_sets()["VETO_FLOOR_ALLOWED"])  # one block only
        self.assertIn("alias-outside-working-set: %s -> %s" % (alias, target),
                      self.check(self.text,
                                 ws=blocks["AVAILABLE_MODELS_WORKING_SET"]))

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
