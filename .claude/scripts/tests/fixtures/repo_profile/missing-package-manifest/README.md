# missing-package-manifest fixture

Bare Markdown-only repo. No package.json, pyproject.toml, Cargo.toml,
or any directory hints. Detector MUST exit 2 with
`risk_class: unknown-needs-owner-confirmation` (NOT silent `generic`,
NOT silent `trading-readonly` — the absence of ANY signal is
fundamentally different from ambiguity).
