# Sample doc — declares CEO_DETECTOR_1_TEST env var

This document mentions `CEO_DETECTOR_1_TEST` as if it were a real
runtime env var. No `.py` file under `.claude/scripts` or
`.claude/hooks` actually reads it via `os.environ.get` /
`os.getenv` / `subprocess.run(env=...)`. Detector #1 should fire.

The variable `CEO_DETECTOR_1_TEST` should be filtered into the
documented set; AST scan returns 0 reads.
