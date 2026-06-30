# Claim fixtures (ADR-018)

Regression fixtures per claim kind. Each kind ships:

- ≥3 positive fixtures (valid token → verifier returns True)
- ≥2 negative fixtures (valid token → verifier returns False)
- ≥1 fixture showing a token inside a fenced code block (extractor MUST skip)
- ≥1 fixture showing a quoted arg (extractor MUST recognize)

Fixtures are plain text files named:

```
pos-<description>.txt  (expected: verifier passes)
neg-<description>.txt  (expected: verifier fails)
codeblock-<description>.txt  (expected: extractor skips all tokens inside)
quoted-<description>.txt  (expected: extractor recognizes backtick-quoted args)
```

These fixtures support the Sprint 9 decision on whether to enforce
the confidence gate. False-positive rate (FPR) measured against this
corpus sets the baseline.
