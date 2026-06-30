"""PLAN-023 Phase B — _lib.canonical_json unit tests.

Covers:
- Pinned kwargs (sort_keys, separators, ensure_ascii, allow_nan=False).
- NFC normalization of combining-character Unicode.
- Float rejection with actionable error message.
- NaN / Infinity rejection.
- Nested dict sorting (recursive).
- Tuple / set / custom class rejection.
- Bytes output + UTF-8 correctness for non-ASCII.
- Determinism across two calls with same input.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_HOOKS = Path(__file__).resolve().parent.parent

from _lib import canonical_json  # noqa: E402
from _lib.canonical_json import CanonicalJsonError, encode  # noqa: E402


class CanonicalJsonTest(unittest.TestCase):

    # --- Pinned kwargs / basic shape ----------------------------------

    def test_encode_returns_bytes(self):
        self.assertIsInstance(encode({"a": 1}), bytes)

    def test_encode_utf8(self):
        out = encode({"x": "café"})
        self.assertEqual(out, b'{"x":"caf\xc3\xa9"}')

    def test_sort_keys_applied(self):
        # Keys out of insertion order MUST sort alphabetically.
        out = encode({"z": 1, "a": 2, "m": 3})
        self.assertEqual(out, b'{"a":2,"m":3,"z":1}')

    def test_sort_keys_nested(self):
        out = encode({"outer": {"z": 1, "a": 2}})
        self.assertEqual(out, b'{"outer":{"a":2,"z":1}}')

    def test_separators_no_whitespace(self):
        out = encode({"a": 1, "b": 2})
        self.assertNotIn(b" ", out)

    def test_ensure_ascii_false(self):
        # Non-ASCII characters remain as UTF-8 bytes (not \uXXXX escapes).
        out = encode({"k": "日本"})
        self.assertEqual(out, b'{"k":"\xe6\x97\xa5\xe6\x9c\xac"}')

    # --- NFC normalization --------------------------------------------

    def test_nfc_precomposed_vs_decomposed(self):
        # "é" (U+00E9 precomposed) and "e" + "◌́" (U+0065 U+0301)
        # must produce the same canonical bytes.
        pre = "caf\u00e9"
        dec = "cafe\u0301"
        self.assertNotEqual(pre, dec)  # Python still sees them as distinct
        self.assertEqual(encode({"v": pre}), encode({"v": dec}))

    def test_nfc_recursive_through_dict(self):
        pre = "\u00e9"
        dec = "e\u0301"
        self.assertEqual(
            encode({"nested": {"val": pre}}),
            encode({"nested": {"val": dec}}),
        )

    def test_nfc_recursive_through_list(self):
        pre = "\u00e9"
        dec = "e\u0301"
        self.assertEqual(
            encode({"list": [pre, "x"]}),
            encode({"list": [dec, "x"]}),
        )

    # --- Float / NaN / Inf rejection ----------------------------------

    def test_float_rejected_top_level(self):
        with self.assertRaises(CanonicalJsonError) as cm:
            encode({"ratio": 0.5})
        self.assertIn("float", str(cm.exception))
        self.assertIn("$.ratio", str(cm.exception))

    def test_float_rejected_nested(self):
        with self.assertRaises(CanonicalJsonError) as cm:
            encode({"a": {"b": [1, 2, 3.14]}})
        self.assertIn("$.a.b[2]", str(cm.exception))

    def test_bool_accepted(self):
        # bool is a subclass of int; must NOT be treated as float.
        out = encode({"ok": True, "bad": False})
        self.assertEqual(out, b'{"bad":false,"ok":true}')

    def test_int_accepted(self):
        out = encode({"n": 1_000_000})
        self.assertEqual(out, b'{"n":1000000}')

    def test_nan_rejected(self):
        with self.assertRaises(CanonicalJsonError):
            encode({"v": float("nan")})

    def test_inf_rejected(self):
        with self.assertRaises(CanonicalJsonError):
            encode({"v": float("inf")})

    # --- Unsupported types --------------------------------------------

    def test_tuple_rejected(self):
        with self.assertRaises(CanonicalJsonError) as cm:
            encode({"t": (1, 2)})
        self.assertIn("unsupported type tuple", str(cm.exception))

    def test_set_rejected(self):
        with self.assertRaises(CanonicalJsonError):
            encode({"s": {1, 2, 3}})

    def test_custom_object_rejected(self):
        class C:
            pass

        with self.assertRaises(CanonicalJsonError):
            encode({"x": C()})

    # --- Determinism + None + list handling ---------------------------

    def test_null_preserved(self):
        self.assertEqual(encode({"k": None}), b'{"k":null}')

    def test_list_preserves_order(self):
        # Lists are ordered; sort_keys only sorts dict keys, not list
        # elements.
        self.assertEqual(encode([3, 1, 2]), b"[3,1,2]")

    def test_deterministic_across_calls(self):
        obj = {"a": 1, "b": {"x": None, "y": [1, 2, 3]}}
        a = encode(obj)
        b = encode(obj)
        self.assertEqual(a, b)

    def test_empty_dict(self):
        self.assertEqual(encode({}), b"{}")

    def test_empty_list(self):
        self.assertEqual(encode([]), b"[]")


if __name__ == "__main__":
    unittest.main()
