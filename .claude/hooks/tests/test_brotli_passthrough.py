"""PLAN-046 Cluster 1.1 — brotli_passthrough tests.

Imports the staged scaffold from
``.claude/plans/PLAN-046/staged-code/brotli_passthrough.py`` (non-
canonical path). When the scaffold is promoted to
``.claude/hooks/_lib/brotli_passthrough.py``, switch the import to
``from _lib import brotli_passthrough`` and drop the path shim.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_SCAFFOLD = (
    _REPO_ROOT / "tests" / "fixtures" / "staged_scaffold"
    / "brotli_passthrough.py"
)


def _load_scaffold():
    spec = importlib.util.spec_from_file_location(
        "brotli_passthrough_staged", _SCAFFOLD
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_HOOKS_DIR = Path(__file__).resolve().parent.parent
from _lib.testing import TestEnvContext  # noqa: E402

try:
    import brotli as _brotli  # type: ignore[import-not-found]

    _HAS_BROTLI = True
except ImportError:
    _HAS_BROTLI = False


class BrotliPassthroughTest(TestEnvContext):
    """Round-trip + fail-open coverage for the staged scaffold."""

    def setUp(self) -> None:
        super().setUp()
        self.mod = _load_scaffold()

    def _set_backend(self, backend: str) -> None:
        os.environ["CEO_CONTEXT_COMPRESS"] = backend

    def test_roundtrip_zlib_default(self) -> None:
        self._set_backend("zlib")
        data = b"hello " * 100
        cz = self.mod.compress(data)
        self.assertLess(len(cz), len(data))
        self.assertEqual(self.mod.decompress(cz), data)

    @unittest.skipUnless(_HAS_BROTLI, "brotli not installed")
    def test_roundtrip_brotli(self) -> None:
        self._set_backend("brotli")
        data = b"brotli " * 200
        cb = self.mod.compress(data)
        self.assertLess(len(cb), len(data))
        self.assertEqual(self.mod.decompress(cb), data)

    def test_off_backend_passthrough(self) -> None:
        self._set_backend("off")
        data = b"unchanged"
        self.assertEqual(self.mod.compress(data), data)
        self.assertEqual(self.mod.decompress(data), data)

    def test_decompress_autodetects_zlib_framing(self) -> None:
        """A zlib payload decompresses regardless of current backend."""
        self._set_backend("zlib")
        import zlib
        raw = b"auto-detect me " * 50
        payload = zlib.compress(raw, 9)
        self._set_backend("brotli")  # switch backend mid-life
        self.assertEqual(self.mod.decompress(payload), raw)

    @unittest.skipUnless(_HAS_BROTLI, "brotli not installed")
    def test_decompress_autodetects_brotli_framing(self) -> None:
        self._set_backend("brotli")
        raw = b"brotli-framed " * 50
        payload = _brotli.compress(raw)
        self.assertEqual(self.mod.decompress(payload), raw)

    def test_fail_open_on_corrupt_decompress(self) -> None:
        """Random non-compressed bytes pass through unchanged."""
        self._set_backend("zlib")
        garbage = b"\x00\x01\x02\x03not-compressed\xff\xfe"
        self.assertEqual(self.mod.decompress(garbage), garbage)

    def test_empty_bytes_round_trip(self) -> None:
        self._set_backend("zlib")
        self.assertEqual(self.mod.compress(b""), b"")
        self.assertEqual(self.mod.decompress(b""), b"")

    def test_large_data_roundtrip(self) -> None:
        self._set_backend("zlib")
        data = (b"word " * 200_000)  # ~1 MiB
        cz = self.mod.compress(data)
        self.assertLess(len(cz), len(data) // 2)
        self.assertEqual(self.mod.decompress(cz), data)

    def test_level_clamped_to_zlib_range(self) -> None:
        self._set_backend("zlib")
        data = b"clamp-test"
        for level in (-3, 0, 9, 42):
            payload = self.mod.compress(data, level=level)
            self.assertEqual(self.mod.decompress(payload), data)

    def test_invalid_backend_silently_uses_zlib(self) -> None:
        self._set_backend("magical")
        data = b"fallback path " * 10
        payload = self.mod.compress(data)
        self.assertNotEqual(payload, data)
        self.assertEqual(self.mod.decompress(payload), data)

    def test_brotli_import_error_falls_back_to_zlib(self) -> None:
        """Monkey-patch _try_brotli_compress to force ImportError."""
        self._set_backend("brotli")
        original = self.mod._try_brotli_compress
        self.mod._try_brotli_compress = lambda d, lvl: None
        try:
            data = b"force-zlib-fallback " * 20
            payload = self.mod.compress(data)
            self.assertEqual(self.mod.decompress(payload), data)
        finally:
            self.mod._try_brotli_compress = original

    def test_type_error_on_non_bytes(self) -> None:
        self._set_backend("zlib")
        with self.assertRaises(TypeError):
            self.mod.compress("string not bytes")  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            self.mod.decompress("string not bytes")  # type: ignore[arg-type]


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
