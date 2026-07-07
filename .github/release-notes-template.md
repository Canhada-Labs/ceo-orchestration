ceo-orchestration {{TAG}}

See the `## [{{BASE_VERSION}}]` section of `CHANGELOG.md` (at the {{TAG}} tag) for what changed.

**Verify before running:** check `install.sh` against the attached `install.sh.sha256`. The attached `sbom.cyclonedx.json` is the CycloneDX SBOM for this release.

<!--
  Release-notes template (PLAN-153 Wave B item 5 (d); closes PLAN-152
  Deferred release-notes-hardcoded-first-release: no release-specific
  hardcoded sentences — everything ships from this template via
  interpolation).

  Rendered by .github/workflows/release.yml step "Render release notes
  from template" via sed interpolation. Placeholders (each written as a
  double-brace token in the body above; do NOT write any other
  double-brace token here, the workflow fails closed on any unrendered
  one):
    TAG          - the pushed git tag (e.g. v1.0.2 or v1.0.2-rc.1)
    VERSION      - TAG without the leading v (e.g. 1.0.2-rc.1)
    BASE_VERSION - VERSION with any -rc.N suffix stripped (e.g. 1.0.2);
                   CHANGELOG sections are GA-versioned, so RC notes
                   point at the GA section.
  This file is NOT canonical-guarded (only .github/workflows/*.yml is);
  it is inert until the PLAN-153 Wave B release.yml lands.
-->
