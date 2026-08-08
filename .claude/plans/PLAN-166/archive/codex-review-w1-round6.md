The new delivery-record handling loses ownership records for legitimate link-mode SPEC and marker installations because those records are discarded before validation.

Review comment:

- [P2] Keep sanitized LINK records available for validation — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1728-1730
  For a `--link` install, `_load_baseline_manifest()` rejects each LINK record because `_baseline_relpath_unsafe()` treats the symlinked leaf as unsafe. Consequently this lookup—and the marker lookup at line 1930—can never find a legitimate recorded target, so both paths are preserved “without ownership” and omitted from the rewritten manifest; marker-based update checks then fall back to the stale root `VERSION`. LINK records need sanitization that permits and validates their leaf symlink before these checks.
