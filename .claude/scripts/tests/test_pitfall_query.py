"""Unit tests for pitfall-query.py (PLAN-010 Phase 5).

Covers:
- Parsing the universal catalog
- Parsing a domain catalog
- Unknown-domain graceful error (exit 2 + available list)
- text + json output formats
- Quoted-string and flow-list parsing edge cases
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
_MODULE_PATH = _SCRIPTS_DIR / "pitfall-query.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("pitfall_query", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


pq = _load_module()


class TestYamlParser(unittest.TestCase):
    def test_parses_well_formed_entries(self) -> None:
        sample = (
            "pitfalls:\n"
            '  - id: FOO-001\n'
            '    rule: "first rule"\n'
            '    whenToUse: "always"\n'
            '    agents: [Alice, Bob]\n'
            "  - id: FOO-002\n"
            '    rule: "second rule"\n'
            '    agents: [Carol]\n'
        )
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "pitfalls.yaml"
            p.write_text(sample, encoding="utf-8")
            out = pq.parse_pitfalls_yaml(p)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["id"], "FOO-001")
        self.assertEqual(out[0]["rule"], "first rule")
        self.assertEqual(out[0]["agents"], ["Alice", "Bob"])
        self.assertEqual(out[1]["id"], "FOO-002")
        self.assertEqual(out[1]["agents"], ["Carol"])

    def test_strips_comments_outside_quotes(self) -> None:
        sample = (
            "pitfalls:\n"
            "  # a comment line\n"
            '  - id: BAR-001   # inline comment\n'
            '    rule: "uses # inside quotes"\n'
            '    agents: []\n'
        )
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "pitfalls.yaml"
            p.write_text(sample, encoding="utf-8")
            out = pq.parse_pitfalls_yaml(p)
        self.assertEqual(out[0]["rule"], "uses # inside quotes")
        self.assertEqual(out[0]["agents"], [])

    def test_missing_file_returns_empty(self) -> None:
        out = pq.parse_pitfalls_yaml(Path("/nonexistent/path/pitfalls.yaml"))
        self.assertEqual(out, [])


class TestRepoCatalogs(unittest.TestCase):
    def test_universal_catalog_parses(self) -> None:
        out = pq.parse_pitfalls_yaml(pq.UNIVERSAL_CATALOG)
        self.assertGreater(len(out), 5)
        for p in out:
            self.assertIn("id", p)
            self.assertIn("rule", p)

    def test_list_available_domains_includes_fintech(self) -> None:
        available = pq.list_available_domains()
        self.assertIn("fintech", available)


class TestCollect(unittest.TestCase):
    def test_collect_without_domain(self) -> None:
        data = pq.collect(None)
        self.assertIsNone(data["domain"])
        self.assertEqual(data["domain_pitfalls"], [])
        self.assertGreater(len(data["universal"]), 0)

    def test_collect_with_known_domain(self) -> None:
        data = pq.collect("fintech")
        self.assertEqual(data["domain"], "fintech")
        self.assertGreater(len(data["domain_pitfalls"]), 0)

    def test_collect_unknown_domain_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            pq.collect("no-such-domain-zzz")


class TestCli(unittest.TestCase):
    def test_text_output_default(self) -> None:
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = pq.main([])
        self.assertEqual(rc, 0)
        self.assertIn("Universal pitfalls", buf.getvalue())

    def test_json_output(self) -> None:
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = pq.main(["--format", "json"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertIn("universal", payload)
        self.assertIsNone(payload["domain"])

    def test_unknown_domain_exits_2(self) -> None:
        err = io.StringIO()
        with patch("sys.stderr", err):
            rc = pq.main(["--domain", "no-such-domain-zzz"])
        self.assertEqual(rc, 2)
        self.assertIn("unknown domain", err.getvalue())
        # available list present (may list real domains OR be "(none)")
        self.assertIn("Available:", err.getvalue())

    def test_known_domain_json(self) -> None:
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = pq.main(["--domain", "fintech", "--format", "json"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["domain"], "fintech")
        self.assertGreater(len(payload["domain_pitfalls"]), 0)


if __name__ == "__main__":
    unittest.main()
