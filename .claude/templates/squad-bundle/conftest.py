"""
conftest.py -- Squad-bundle templates directory.

Purpose (PLAN-080 Phase 0b S2 finding):
  Template files (*.template) are not valid Python modules and must not be
  collected by pytest as test sources. Without this exclusion, pytest's
  default collection descends into the templates/ directory and raises
  ImportError or CollectError on files like team-personas.md.template,
  which contain neither Python syntax nor valid test names.

  The examples/*.template glob is included because the examples/
  subdirectory also contains .template files that are similarly unparseable.

collect_ignore_glob prevents pytest from attempting to import or collect
any matching path, regardless of whether those paths contain Python-like
names. This is distinct from conftest.ini-based filtering; the glob is
evaluated relative to the directory containing this conftest.py.

Reference: pytest docs "Customizing Test Collection" > collect_ignore_glob.
"""

from __future__ import annotations

collect_ignore_glob: list[str] = [
    "*.template",
    "examples/*.template",
]
