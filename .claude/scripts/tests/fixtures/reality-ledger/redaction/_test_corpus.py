"""Test corpus for redact_secrets fixture.

Contains a synthetic credential `sk-test-AAAAAAAAAAAAAAAAAAAA` (20+ chars)
that MUST be redacted to `[API_KEY]` in any actual_evidence emission.
"""

API_KEY = "sk-test-AAAAAAAAAAAAAAAAAAAA"  # 20+ chars matches Anthropic-style regex
