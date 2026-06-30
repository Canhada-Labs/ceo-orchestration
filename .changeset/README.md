# `.changeset/` — user-visible release notes

## Convention

Each PR that adds a user-visible change drops a single Markdown file in
this directory:

```
.changeset/<random-slug>.md
```

The slug is free-form (e.g. `add-snapshot-helper.md`). Two PRs landing
the same week MUST NOT collide; pick a unique slug.

## File format

Frontmatter (single line) declares the SemVer bump:

```
---
type: <patch|minor|major>
---
<one-line user-visible description>
```

Rules:

- Frontmatter is exactly `type: <patch|minor|major>`. No nesting, no
  arrays, no other keys (the production aggregator fails CLOSED on
  anything else).
- Body is a single line of Markdown describing the change as an adopter
  would read it (not as governance narrative).
- Multi-doc YAML (a second `---` fence inside the body) is forbidden;
  the aggregator fails CLOSED on it (PoC §5 risk #4 — safe default).

## Aggregation at closeout

At each tag-cut the maintainer runs LOCALLY (never in CI):

```
python3 .claude/scripts/aggregate-changesets.py \
    --version <X.Y.Z> --date <YYYY-MM-DD>
```

The aggregator:

1. Lists `.changeset/*.md` (excluding this `README.md` and any
   `config.json`).
2. Parses each frontmatter block; fails CLOSED on any malformed input.
3. Renders a `## [<version>] - <date>` block GROUPED by
   `### Major` / `### Minor` / `### Patch` buckets in that order, with
   entries WITHIN each bucket sorted by `(mtime, name)` ascending —
   deterministic on coarse-mtime filesystems. **Note:** global
   `(mtime, name)` order is preserved within each bucket, NOT across
   buckets — a `patch` authored before a `minor` still renders below
   the `minor` block (Codex re-pass P3-1 documented this).
4. Inserts the block ABOVE the latest existing tagged version block in
   `CHANGELOG.md`.
5. Deletes the consumed `.changeset/*.md` files.
6. Idempotent: re-running with a version already present in CHANGELOG
   is a no-op.

`--dry-run` prints the would-be block without mutating CHANGELOG or
deleting any file.

## CI orphan guard

Run this in CI (advisory, non-blocking unless a separate ceremony wires
it as a hard gate):

```
python3 .claude/scripts/aggregate-changesets.py --check
```

Returns rc=1 if any `.changeset/*.md` are present (orphans not yet
aggregated); rc=0 if the directory is clean. Use this to remind PR
authors to drop a changeset before tagging.

## LOCAL-ONLY by design

The aggregator runs at the maintainer's workstation during the closeout
ceremony, alongside `VERSION` bump and `git tag`. CI does not run it in
write mode. If `CI=true` is set when invoked, the aggregator emits a
single stderr warning but still runs (so `--dry-run` and `--check` can
be safely smoke-tested in CI).

The release pipeline (`.github/workflows/release.yml:133`) reads
`CHANGELOG.md` via the literal grep `^## \[VERSION\]`. The aggregator's
`make_version_regex(version)` is byte-equivalent to that grep — see
`bench-results.md` regex contract probes R-A through R-D for the
empirical evidence.

## ADR reference

The convention is documented in **ADR-099** (PLAN-068 Phase 2; drafted
next). This README is the in-tree quick-reference; ADR-099 is the
authoritative rationale and decisions record.
