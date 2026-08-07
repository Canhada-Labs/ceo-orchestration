# PLAN-167 W4 — land runbook

Every snippet is POSIX. `\s` does NOT exist in BSD `grep -E`/`sed`, and using
it once already produced a false "everything out of scope" that would have
stalled a ceremony. Use `[[:space:]]`.

Run everything from the repo root.

## §0 — preflight (all four must pass before anything is applied)

```sh
git rev-parse HEAD                                  # must equal the signed Anchor-SHA
shasum -c .claude/plans/PLAN-167/staged-manifest.sha256   # rc=0, repo-relative
gpg --verify .claude/plans/PLAN-167/W4-approved.md.asc \
             .claude/plans/PLAN-167/W4-approved.md
test -z "$(git diff --cached --name-only)"          # index must be clean
```

## §1 — apply, by TABLE not by hand

A hand-written file list is how the S296 mirror script covered 2 of 4 files
with no gate noticing. The loop below IS the table: adding a file is one line,
and a file that is staged but absent here fails §3.

```sh
set -eu
STAGED=".claude/plans/PLAN-167/staged"
while IFS='|' read -r src dst; do
  [ -n "$src" ] || continue
  cp "$STAGED/$src" "$dst"
  echo "applied: $dst"
done <<'EOF'
_framework_manifest_set.sh|scripts/_framework_manifest_set.sh
install.sh|scripts/install.sh
upgrade.sh|scripts/upgrade.sh
test-ownership-verdict-unit.sh|scripts/tests/test-ownership-verdict-unit.sh
check-model-deprecations.py|.claude/scripts/check-model-deprecations.py
EOF
chmod +x scripts/tests/test-ownership-verdict-unit.sh
```

## §2 — gates

```sh
bash -n scripts/install.sh
bash -n scripts/upgrade.sh
bash -n scripts/_framework_manifest_set.sh
shellcheck -S warning scripts/install.sh scripts/upgrade.sh \
                      scripts/_framework_manifest_set.sh
python3 -c 'import ast;ast.parse(open(".claude/scripts/check-model-deprecations.py").read())'

./scripts/tests/test-ownership-verdict-unit.sh        # expect 60/60, seconds
./scripts/tests/test-ownership-table.sh               # expect 58 green / 4 red, ~25 min
python3 .claude/scripts/check-docs-freshness.py       # expect 0 broken refs
bash .claude/scripts/validate-governance.sh           # expect Errors: 0
```

**The e2e is expected to end with 4 red.** They are enumerated with named
causes in `W4-approved-draft.md`; two of them are defects in the TEST, not the
product. A run that comes back all-green means the table changed — stop and
find out why.

## §3 — touched − scope must be empty

```sh
git status --porcelain \
  | sed 's/^...//' \
  | grep -v '^[[:space:]]*$' \
  | sort > /tmp/touched.txt

cat > /tmp/scope.txt <<'EOF'
scripts/_framework_manifest_set.sh
scripts/install.sh
scripts/upgrade.sh
scripts/tests/test-ownership-verdict-unit.sh
.claude/scripts/check-model-deprecations.py
EOF
sort -o /tmp/scope.txt /tmp/scope.txt

comm -23 /tmp/touched.txt /tmp/scope.txt
```

The PLAN-166 ceremony files are still dirty in this tree and WILL appear here.
That is expected — they are that ceremony's scope, not this one's. Anything
else appearing is a STOP.

## §4 — commit

```sh
git add scripts/_framework_manifest_set.sh scripts/install.sh scripts/upgrade.sh \
        scripts/tests/test-ownership-verdict-unit.sh \
        .claude/scripts/check-model-deprecations.py
git commit -S -m "feat(PLAN-167): ownership decision table — one function decides, callers execute"
```

Explicit adds only. **Never `git add -A`** — this tree carries another
ceremony's dirty canonical files.

## §5 — after landing

- Push, confirm CI.
- The CI wiring for these oracles is **deliberately not in this pack**
  (canonical workflow surface). It needs its own ceremony, and until it lands
  the new tests do not run in CI on their own.
