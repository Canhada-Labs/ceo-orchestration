# PLAN-163 T5.2a/b — payload-sha probe evidence (S283+, 2026-07-28)

## 1. Launcher resolution algorithm (transcribed from installed launcher)

Source: `/opt/homebrew/lib/node_modules/@openai/codex/bin/codex.js` (package `@openai/codex` 0.144.6; this file IS the `which codex` symlink target `/opt/homebrew/bin/codex`).

- `bin/codex.js:16-23` — `PLATFORM_PACKAGE_BY_TARGET` map; `"aarch64-apple-darwin": "@openai/codex-darwin-arm64"`.
- `bin/codex.js:27-68` — targetTriple from `process.platform`/`process.arch`; `darwin`+`arm64` -> `aarch64-apple-darwin` (line 48).
- `bin/codex.js:79-108` — `findCodexExecutable()`:
  - line 82: `require.resolve("@openai/codex-darwin-arm64/package.json")` -> vendorRoot = `<pkg-dir>/vendor` (line 83); fallback `__dirname/../vendor` (line 85).
  - lines 88-93: executable = `path.join(vendorRoot, targetTriple, "bin", "codex")` (`.exe` on win32).
  - line 94-96: `existsSync` -> return; else throws "Missing optional dependency" (lines 98-107).
- `bin/codex.js:110` — `const binaryPath = findCodexExecutable();` then async `spawn` of the NATIVE binary.

Optional-dep alias (parent `package.json`): `"@openai/codex-darwin-arm64": "npm:@openai/codex@0.144.6-darwin-arm64"` — i.e., the registry artifact is `@openai/codex@0.144.6-darwin-arm64` installed under the `codex-darwin-arm64` name (a bare `npm view @openai/codex-darwin-arm64` 404s; the alias must be dereferenced).

## 2. Hashes (Owner machine, 2026-07-28)

Resolved payload path (via the launchers own require.resolve algorithm):
`/opt/homebrew/lib/node_modules/@openai/codex/node_modules/@openai/codex-darwin-arm64/vendor/aarch64-apple-darwin/bin/codex` (260,472,144 bytes, mtime Jul 20 20:33)

| artifact | sha256 |
|---|---|
| native payload (aarch64-apple-darwin) | `80a3933d11a9d13ef806aa24f7bb8afc9169cfe4e9b09d6da6a92922cbde9cff` |
| launcher `bin/codex.js` | `134063e133f0b4244fa3b251acf973d4fe4b4aeeacbdc135211bf480f59f1477` |

- `codex --version` -> `codex-cli 0.144.6`
- npm `package_version` -> `0.144.6`; platform pkg version `0.144.6-darwin-arm64`
- npm integrity (registry `npm view @openai/codex@0.144.6-darwin-arm64 dist.integrity`):
  `sha512-6zgvh70MzBNSeT17HEhSOrmmGGZGAKzSC7x6JAq+edkJkdPYA9P0I1tG7aJ49GlBkBxuC+MKBH1qm6+2Cghcww==`
  (not present in local cache index; fetched from registry.npmjs.org)

## 3. Proof payload != launcher / pin attests the LAUNCHER

The current pin file `.claude/governance/codex-cli-binary-sha256.txt` pins
`134063e133f0b4244fa3b251acf973d4fe4b4aeeacbdc135211bf480f59f1477` — byte-identical
to the sha256 of `bin/codex.js` computed today, and DIFFERENT from the native payload
sha (`80a3933d...`). `shasum -a 256 $(which codex)` follows the npm symlink to the
JS launcher, never touching the 260 MB native Rust binary that actually executes.
Confirming T5.2a: the pin was minted for codex-cli **0.144.1** (SENT-CX-PIN, S269)
yet still matches under **0.144.6** because the launcher JS is version-stable — the
native payload changed across the 0.144.1 -> 0.144.6 bump WITHOUT any gate trip.

## 4. Current pin file content (verbatim tail, non-comment line)

`.claude/governance/codex-cli-binary-sha256.txt` (header comments describe launcher-hash
procedure `shasum -a 256 $(which codex)`; PLAN-156 re-pin S269 for 0.144.1):

```
134063e133f0b4244fa3b251acf973d4fe4b4aeeacbdc135211bf480f59f1477
```

Semver pin `.claude/governance/codex-cli-pin.txt`: `>=0.128.0,<0.145.0` (installed 0.144.6 in-range).

## 5. BONUS — grok ledger entry

- `which grok` -> `/Users/joaocanhada/.grok/bin/grok` (symlink -> `~/.grok/downloads/grok-0.2.106-macos-aarch64`)
- `grok --version` -> `grok 0.2.106 (bde89716f679) [stable]` (vs governance pin 0.2.93 — drift already flagged in PLAN-163)
- sha256(payload) = `7229f5e2a69b05832c86db82bebda541e92b5c24958fbfacf5c8f463394d3027`

## 6. Manifest draft

Written to `.claude/plans/PLAN-163/probes/pin-manifest-draft.json` (schema 1, validated with `python3 -m json.tool`).
