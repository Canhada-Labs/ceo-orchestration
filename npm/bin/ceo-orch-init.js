#!/usr/bin/env node
// @ceo-orch/init — pass-through shim around scripts/install.sh.
//
// Sprint 5 Phase 4. The bundle ships everything install.sh needs (the
// full source tree at publish time). This binary locates the bundled
// scripts/install.sh via __dirname, spawns bash with the user's
// arguments, and proxies the exit code. Zero runtime dependencies —
// the package.json `dependencies` map is intentionally empty and CI
// asserts it.
//
// Usage:
//   npx @ceo-orch/init <target-repo-path> [--profile core,frontend] [--stack node]
//   ceo-orch-init <target-repo-path> [--profile ...]
//
// Behavior contract (SPEC/v1/npm-shim.md):
//   - Locates install.sh relative to __dirname (no PATH lookup, no env).
//   - Forwards every argv[2..] argument unchanged to bash install.sh.
//   - Inherits stdio (live progress visible to the caller).
//   - Exits with the same code as install.sh.
//   - On install.sh missing: exit 2 with a clear message (likely a
//     packaging bug, not user error).

'use strict';

const path = require('path');
const fs = require('fs');
const { spawnSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const INSTALL = path.join(ROOT, 'scripts', 'install.sh');

if (!fs.existsSync(INSTALL)) {
  process.stderr.write(
    `[ceo-orch/init] FATAL: bundled install.sh missing at ${INSTALL}\n` +
    `This is a packaging bug. Please file an issue at\n` +
    `  https://github.com/Canhada-Labs/ceo-orchestration/issues\n`
  );
  process.exit(2);
}

const args = process.argv.slice(2);

const result = spawnSync('bash', [INSTALL, ...args], {
  stdio: 'inherit',
  cwd: process.cwd(),
});

if (result.error) {
  process.stderr.write(
    `[ceo-orch/init] FATAL: failed to spawn bash: ${result.error.message}\n`
  );
  process.exit(2);
}

process.exit(result.status === null ? 1 : result.status);
