# MCP Cursor Setup — ceo-orchestration framework

> Step-by-step guide to wire Cursor IDE to the framework's local MCP
> (Model Context Protocol) server. Estimated time end-to-end:
> 10 minutes on a fresh install.

This guide assumes you have already installed ceo-orchestration into your
project (`scripts/install.sh` ran successfully).
It does NOT assume prior MCP familiarity.
Every command is copy-paste ready after replacing one placeholder:
`/absolute/path/to/your/project` (your project's absolute path on disk).

## 1. What this guide gets you

By the end of this guide, your Cursor IDE will talk to a local JSON-RPC
server shipped with the framework.
Cursor will be able to list, read, and (optionally, per ACL) invoke the
framework's governance surface without you pasting anything into the
chat by hand.
All calls are authenticated, rate-limited, audit-logged, and subject to
the same governance hooks that Claude-native spawns respect.

Three concrete wins:

- See all 52 skills in Cursor's sidebar (one round-trip to `list_skills`).
- Ask Cursor to "show me the `security-and-auth` skill content" and get
  the actual `SKILL.md` body injected into context.
- Have Cursor call `spawn_agent` through the same `check_agent_spawn.py`
  hook Claude-native respects — governance-preserving across clients.

What this guide is NOT:

- Not a tutorial on MCP the protocol (see the upstream spec).
- Not a replacement for Claude Code inside the project.
- Not a way to bypass any framework hook.
  The MCP server re-enters every `PreToolUse` governance path that
  Claude-native invocations do.

## 2. Prerequisites

Before you start, confirm each of these.
If any fails, fix it first.

- Python 3.9 or newer.
  Verify:
  ```bash
  python3 --version
  ```
  Expected output starts with `Python 3.9` through `Python 3.13`.
  If missing on macOS, install via Homebrew: `brew install python@3.11`.

- Cursor 0.42 or newer (MCP support stabilized in Cursor 2024-Q4).
  Verify:
  ```bash
  cursor --version
  ```
  If `cursor` is not in your PATH on macOS, the binary lives at:
  `/Applications/Cursor.app/Contents/Resources/app/bin/cursor`.
  Add that to `PATH` or symlink.
  (verify against Cursor 0.42+ docs for the current binary location)

- ceo-orchestration installed in your project.
  Verify:
  ```bash
  ls /absolute/path/to/your/project/.claude/
  ls /absolute/path/to/your/project/CLAUDE.md
  ```
  Both must exist.
  If not, re-run `scripts/install.sh` per `docs/QUICKSTART.md`.

- `openssl` available in PATH (used for client_id + shared secret).
  Verify:
  ```bash
  openssl version
  ```
  Expected: any OpenSSL 1.1+ or LibreSSL 2.0+ output line.
  Already present on macOS and all mainstream Linux distros.

- macOS (Intel or Apple Silicon) or Linux x86_64/ARM64 primary support.
  Windows WSL2 is secondary support:
  follow the Linux paths inside your WSL distro, not the Windows side.

## 3. One-time setup

Eight atomic, idempotent steps.
Each step ends with a **Verify:** line showing what correct output looks
like.
If a verify step fails, STOP and debug that step before moving on.

### Step 3.1 — Generate client_id and shared secret

Generate a unique client identifier and a 256-bit shared secret.
The secret NEVER leaves your machine and never goes into git.

```bash
cd /absolute/path/to/your/project
mkdir -p state/mcp_client_secrets
chmod 700 state/mcp_client_secrets
CLIENT_ID=$(openssl rand -hex 8)
openssl rand -hex 32 > "state/mcp_client_secrets/${CLIENT_ID}.key"
chmod 600 "state/mcp_client_secrets/${CLIENT_ID}.key"
echo "client_id=${CLIENT_ID}"
echo "secret saved to state/mcp_client_secrets/${CLIENT_ID}.key"
```

Copy the `client_id=<hex16>` line that prints.
You will paste this value into `.claude/settings.json` and into every
manual token you generate in §3.4.

Why this file layout:

- `state/` is the framework's standard per-project writable directory
  and is already in the project's `.gitignore` template.
- `600` perms mean only your OS user can read the secret.
- The `client_id_hex16` format (16 hex chars) matches the token scheme
  in `ADR-042 §Auth.1`.

**Verify:**
```bash
ls -la state/mcp_client_secrets/
```
Expected: one `<CLIENT_ID>.key` file with mode `-rw-------` (600).

**Security footgun:**
never paste the contents of the `.key` file into chat, a bug report, or
a screenshot.
If you leak it, regenerate immediately by repeating this step and
removing the old file.

### Step 3.2 — Register the client in settings.json

Open `.claude/settings.json` in your project and add the
`mcp_client_registry` block.
The registry declares which handlers the client may call.
An empty or missing allowlist denies everything — the framework
default-denies at this layer (`ADR-042 §Auth.2`).

Add this block to the top level of `.claude/settings.json`
(replace `YOUR_CLIENT_ID_HEX16` with the value from §3.1):

```json
{
  "mcp_client_registry": {
    "YOUR_CLIENT_ID_HEX16": {
      "handlers": [
        "list_skills",
        "get_skill",
        "list_agents",
        "list_pitfalls",
        "get_audit_log",
        "server.capabilities"
      ],
      "cors_origins": []
    }
  }
}
```

Note: `spawn_agent` is **deliberately omitted** from the default handler
list for safety.
`spawn_agent` is a write + cost surface; it can burn budget and trigger
LLM calls.
Opt-in separately once you have validated the read-only handlers work
end-to-end.
See §5 for the opt-in procedure.

`cors_origins` is an empty array by default.
This blocks every browser-origin HTTP call.
You only need to populate `cors_origins` if you plan to call the HTTP
transport from a browser-based client; Cursor uses stdio and does not
care about CORS.

**Verify:**
```bash
python3 -c "import json; cfg=json.load(open('.claude/settings.json')); \
  print(list(cfg.get('mcp_client_registry', {}).keys()))"
```
Expected: a list containing your `CLIENT_ID` exactly.

### Step 3.3 — Start the server (smoke test)

The server supports two transports: HTTP (loopback) and stdio.
For smoke testing, use HTTP — curl is easier to debug than a stdio pipe.
Cursor itself will use stdio in §4.

Start HTTP on loopback port 9000 from a dedicated terminal:

```bash
cd /absolute/path/to/your/project
CEO_MCP_TRANSPORT=http CEO_MCP_PORT=9000 python3 .claude/scripts/mcp-server/server.py
```

Leave this terminal running.
The server logs to stderr; stdout stays free for JSON-RPC traffic.
Default bind address is `127.0.0.1` (loopback-only); do NOT bind to
`0.0.0.0` on a multi-user machine.

If you want to stop the server, press `Ctrl+C` in the terminal.
The server exits cleanly.

Kill-switch behavior: set `CEO_SOTA_DISABLE=1` in your environment to
short-circuit the server before it binds any port or opens any pipe.
Useful when you want to pause MCP without uninstalling.

**Verify:**
In a SECOND terminal, run:
```bash
curl -sS http://127.0.0.1:9000/health
```
Expected response (exact shape): `{"status":"ok"}`.
If curl hangs or refuses the connection, the server never bound the
port; check the server terminal for stderr tracebacks.

### Step 3.4 — Manual smoke test with curl

Generate a short-lived token and call `list_skills` through curl to
confirm auth + handler path both work end-to-end.

Token generation — run this in a new terminal (the server terminal from
§3.3 stays busy).
Replace `YOUR_CLIENT_ID_HEX16` with the value from §3.1:

```bash
cd /absolute/path/to/your/project
CLIENT_ID="YOUR_CLIENT_ID_HEX16"
NONCE=$(openssl rand -hex 8)
TS_MS=$(python3 -c 'import time; print(int(time.time()*1000))')
SECRET=$(cat "state/mcp_client_secrets/${CLIENT_ID}.key")
HMAC_INPUT="${CLIENT_ID}${NONCE}${TS_MS}"
MAC=$(printf "%s" "${HMAC_INPUT}" \
  | openssl dgst -sha256 -hmac "${SECRET}" -hex \
  | awk '{print $2}' \
  | cut -c1-32)
TOKEN="v1.${CLIENT_ID}.${NONCE}.${MAC}"
echo "TOKEN=${TOKEN}"
```

The token format is `v1.<client_id_hex16>.<nonce_hex16>.<hmac_hex32>`
per `ADR-042 §Auth.1`.
It is valid for **±60 seconds** from the `TS_MS` timestamp.
Generate a fresh one every time for a clean run; drift past 60 seconds
triggers `timestamp_skew` deny.

Call `list_skills` with curl:

```bash
curl -sS -X POST http://127.0.0.1:9000/rpc \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{"jsonrpc":"2.0","id":1,"method":"list_skills","params":{}}'
```

Expected response shape (truncated for brevity — actual output lists all
48 skills):
```json
{"jsonrpc":"2.0","id":1,"result":{"skills":[{"tier":"core","slug":"ai-llm-orchestration","description":"..."}]}}
```

If you see `{"jsonrpc":"2.0","id":1,"error":{...}}`, skip to §6
Troubleshooting and look up the error reason there.

**Verify:**
Each subsequent curl call you make with a NEW token returns the same
shape.
Tail the audit log to confirm the server recorded the call:
```bash
python3 .claude/scripts/audit-query.py tail --action mcp_handler_invoked --limit 3
```
Expected: at least one row with `action: mcp_handler_invoked` and
`handler: list_skills` within the last minute.

### Step 3.5 — Stop the HTTP server

Once the smoke test passes, stop the HTTP server.
Cursor will spawn its own server subprocess via stdio — you do not need
a long-running HTTP server during normal use.

In the server terminal from §3.3, press `Ctrl+C`.

**Verify:**
```bash
curl -sS http://127.0.0.1:9000/health
```
Expected: `curl: (7) Failed to connect to 127.0.0.1 port 9000` or
similar connection-refused message.

### Step 3.6 — Confirm handler list with `server.capabilities`

Before configuring Cursor, confirm the server reports the handler set
you expect.
This is the sanity check for ACL + protocol version agreement.

Start the server again briefly:
```bash
cd /absolute/path/to/your/project
CEO_MCP_TRANSPORT=http CEO_MCP_PORT=9000 python3 .claude/scripts/mcp-server/server.py &
SERVER_PID=$!
sleep 1
```

Re-generate a token (per §3.4) and call `server.capabilities`:
```bash
CLIENT_ID="YOUR_CLIENT_ID_HEX16"
NONCE=$(openssl rand -hex 8)
TS_MS=$(python3 -c 'import time; print(int(time.time()*1000))')
SECRET=$(cat "state/mcp_client_secrets/${CLIENT_ID}.key")
HMAC_INPUT="${CLIENT_ID}${NONCE}${TS_MS}"
MAC=$(printf "%s" "${HMAC_INPUT}" \
  | openssl dgst -sha256 -hmac "${SECRET}" -hex \
  | awk '{print $2}' \
  | cut -c1-32)
TOKEN="v1.${CLIENT_ID}.${NONCE}.${MAC}"

curl -sS -X POST http://127.0.0.1:9000/rpc \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d '{"jsonrpc":"2.0","id":2,"method":"server.capabilities","params":{}}'
```

Expected response shape:
```json
{"jsonrpc":"2.0","id":2,"result":{"protocol_version":"1.0.0","handlers_enabled":["list_skills","get_skill","list_agents","list_pitfalls","get_audit_log","server.capabilities"],"spawn_agent_enabled":false}}
```

`spawn_agent_enabled: false` confirms your ACL matches §3.2 — the
server will refuse any `spawn_agent` call until you opt in per §5.

Stop the background server:
```bash
kill "${SERVER_PID}"
```

**Verify:**
`ps -p "${SERVER_PID}"` returns no matching row.

### Step 3.7 — Review rate-limit defaults (optional)

The framework ships sensible defaults per `ADR-042 §Auth.3`:

| Handler class | Rate | Burst |
|---|---|---|
| Read-only (skills, agents, pitfalls, capabilities) | 60 req/min | 10 |
| Audit-log read | 30 req/min | 5 |
| `spawn_agent` | 6 req/min | 2 |

These defaults apply per-client.
If you want to raise or lower them for your specific `client_id`, add an
`mcp_rate_limits` block to `.claude/settings.json`:

```json
{
  "mcp_rate_limits": {
    "YOUR_CLIENT_ID_HEX16": {
      "readonly_rpm": 60,
      "readonly_burst": 10,
      "audit_read_rpm": 30,
      "audit_read_burst": 5,
      "spawn_rpm": 6,
      "spawn_burst": 2
    }
  }
}
```

For most adopters, the defaults are fine.
Only bump values if you actually hit `rate_limit` deny rows in the audit
log during normal Cursor use.

**Verify:**
Skip this step if you did not add `mcp_rate_limits`.
Otherwise:
```bash
python3 -c "import json; cfg=json.load(open('.claude/settings.json')); \
  print(cfg.get('mcp_rate_limits', {}))"
```
Expected: your bumped numbers.

### Step 3.8 — Pre-flight the stdio transport

Cursor uses stdio by default.
Before configuring Cursor itself, confirm the stdio transport starts
cleanly and exits when stdin closes.

```bash
cd /absolute/path/to/your/project
echo '{"jsonrpc":"2.0","id":0,"method":"server.capabilities","params":{"authorization":"v1.FAKE.FAKE.FAKE"}}' \
  | CEO_MCP_TRANSPORT=stdio python3 .claude/scripts/mcp-server/server.py
```

Expected: one line of JSON on stdout, an error response complaining
about the malformed token (`auth_hmac_invalid` or similar).
The server should exit 0 within ~1 second because stdin hit EOF.

**Verify:**
The JSON response includes `"error":{...}` with an auth-related
reason string, and the subprocess exits promptly.
If the process hangs, kill it with `Ctrl+C` and check the stderr
for a traceback.

## 4. Configure Cursor

Cursor discovers MCP servers through a dedicated settings file.
The exact path depends on your OS.

- macOS:
  `~/Library/Application Support/Cursor/User/mcp_settings.json`
- Linux:
  `~/.config/Cursor/User/mcp_settings.json`
- Windows (WSL2):
  use the Linux path inside your WSL distro profile, not the Windows
  Roaming directory.
  (verify against Cursor 0.42+ docs for the current Windows path)

Create the file if it does not exist, or merge the block below into the
existing `mcpServers` object.
Replace `/absolute/path/to/your/project` with your project's absolute
path on disk.
Do NOT use a relative path — Cursor expands the command from its own
working directory, not yours.

```json
{
  "mcpServers": {
    "ceo-orchestration": {
      "command": "python3",
      "args": [
        "/absolute/path/to/your/project/.claude/scripts/mcp-server/server.py"
      ],
      "env": {
        "CEO_MCP_TRANSPORT": "stdio",
        "CLAUDE_PROJECT_DIR": "/absolute/path/to/your/project"
      }
    }
  }
}
```

Behavior:

- Cursor spawns `python3 <args...>` as a subprocess when the user opens
  an MCP-backed chat.
- Communication is stdio JSON-RPC per MCP spec.
- `CLAUDE_PROJECT_DIR` tells the framework which project the call is
  scoped to — the server reads hooks config and settings from this path.
- `CEO_MCP_TRANSPORT=stdio` enforces the stdio code path; without it,
  the server would try to bind a port.

Auth token delivery:
the server still requires an HMAC bearer token even over stdio
(`ADR-042 §Auth.1`).
Over stdio, the token travels in the JSON-RPC request body as a param,
not in an HTTP header.
Cursor's MCP client supports this: in Cursor's MCP Settings UI, select
the `ceo-orchestration` entry and add an Auth Header with:

- Type: `bearer`
- Value: your full token including the `v1.` prefix, exactly as
  generated in §3.4

Cursor injects the token as the `authorization` field of each request's
`params` object.

Reminder on token freshness:
the HMAC timestamp skew window is **±60 seconds** per `ADR-042 §Auth.1`.
A token generated 61 seconds ago returns `timestamp_skew` deny.
Two practical strategies:

1. Preferred — have Cursor regenerate the token per-request using a
   helper script (Cursor 0.42+ supports `env`-expanded commands).
   Document: "Cursor regenerates each request" (verify against Cursor
   0.42+ docs for the exact syntax).
2. Fallback — rotate manually by re-running the token-generation block
   in §3.4 and pasting the new value into Cursor's MCP Settings UI.
   Interactive sessions rarely sit idle longer than 60 seconds, so the
   manual path works for light use.

**Verify:**
Restart Cursor (fully quit, not reload).
Open the Cursor chat panel and check the MCP indicator — it should show
`ceo-orchestration` connected with a green dot.
Issue a test prompt such as: "List the available skills via MCP."
Cursor should respond with the framework's 48 skills tagged by tier
(core / frontend / domains).
Tail the audit log:
```bash
python3 .claude/scripts/audit-query.py tail --action mcp_handler_invoked --limit 5
```
Expected: at least one row with `transport: stdio`.

## 5. Enabling spawn_agent (opt-in)

Until now, your ACL allows only read-only handlers.
Enabling `spawn_agent` lets Cursor initiate agent spawns through the
framework.
This is a **write + cost** path.
Governance passthrough ensures each spawn re-enters
`check_agent_spawn.decide()` — the same hook Claude-native respects —
but spawns still cost money.

Safety model (per `ADR-042 §Auth + §Cost`):

- Each `spawn_agent` call is subject to `LiveCallPolicy`:
  - Per-spawn hard cap: $0.50.
  - Per-plan 5-minute window hard cap: $2.00.
  - Debate rounds: max 5 per call.
- Breach of any ceiling → `mcp_handler_denied` with
  `reason=budget_hard_stop_*`.
- `plan_id` is validated against `.claude/plans/` on every call.
  Unknown plan_id → `mcp_handler_denied(reason=plan_id_unknown)`.
- Circuit breaker (`_lib/adapters/live/_breaker.py`) is shared with
  Claude-native live paths.
  Open breaker → spawn fails fast (<50ms) with
  `reason=breaker_open`.

To enable, extend your `.claude/settings.json` block
(replace `YOUR_CLIENT_ID_HEX16`):

```json
{
  "mcp_client_registry": {
    "YOUR_CLIENT_ID_HEX16": {
      "handlers": [
        "list_skills",
        "get_skill",
        "list_agents",
        "list_pitfalls",
        "get_audit_log",
        "server.capabilities",
        "spawn_agent"
      ],
      "cors_origins": []
    }
  },
  "mcp_rate_limits": {
    "YOUR_CLIENT_ID_HEX16": {
      "readonly_rpm": 60,
      "readonly_burst": 10,
      "audit_read_rpm": 30,
      "audit_read_burst": 5,
      "spawn_rpm": 6,
      "spawn_burst": 2
    }
  }
}
```

Restart Cursor so it re-reads the `mcp_settings.json` cache.
Call `server.capabilities` again (§3.6) — the response should now
report `spawn_agent_enabled: true`.

Budget footgun:
a typo in a spawn prompt that expands into 50KB of context can hit the
per-spawn cap quickly.
Watch `audit-query.py tail --action budget_hard_stop` during your first
day of `spawn_agent` use.
If you see repeated hard stops, review prompt construction before
bumping the cap — the cap is deliberately tight.

Rollback:
to revert to read-only, remove `"spawn_agent"` from the `handlers`
array and restart Cursor.
No server restart needed; the server re-reads `settings.json` on each
request.

## 6. Troubleshooting

Errors surface in the MCP JSON-RPC response under `error.reason` or in
the audit log under `action=mcp_handler_denied`.
Grep for the exact string, then apply the matching fix.

| Error (grep for exact string) | Cause | Fix |
|---|---|---|
| `{"decision":"block","reason":"auth_token_malformed"}` | Token shape is wrong; the parser expects exactly `v1.<client_id_hex16>.<nonce_hex16>.<hmac_hex32>` | Regenerate per §3.4; confirm the four dot-separated pieces and that each hex segment matches the declared length. |
| `auth_hmac_invalid` | Wrong secret, wrong `client_id`, expired timestamp, or HMAC computed incorrectly | Regenerate a fresh token (timestamp drift kills it within 60s of generation); verify `state/mcp_client_secrets/<client_id>.key` exists and has perm `600`; verify the `CLIENT_ID` you passed to `openssl dgst` matches §3.1 exactly. |
| `timestamp_skew` | Token is older than ±60 seconds, or system clock has drifted | Regenerate the token; if chronic, check `ntpd` / `chronyd` / `timesyncd` status and confirm your machine is syncing within 1 second of true time. |
| `acl_missing_handler` | Client ACL does not list this handler | Add the handler name to `mcp_client_registry.<client_id>.handlers` in `.claude/settings.json`; restart Cursor to refresh the MCP connection. |
| `cors_default_deny` | HTTP request has an `Origin` header but client has empty `cors_origins` | Add the origin to the `cors_origins` array as an exact string match (no wildcards, no trailing slash); OR switch to stdio transport (Cursor default) which ignores CORS. |
| `rate_limit` | Per-client token bucket is depleted | Wait for the server's `Retry-After: <seconds>` header to elapse; if chronic, bump `mcp_rate_limits.<client_id>.*_rpm` and `*_burst` in `settings.json`. |
| server refuses to start, stderr says `CEO_SOTA_DISABLE=1` | Kill-switch is active in your environment | `unset CEO_SOTA_DISABLE` in the shell where you launch the server (or where Cursor spawns it via `env` block). |
| `plan_id_unknown` (spawn_agent) | The `plan_id` param does not match any file under `.claude/plans/` | Run `ls .claude/plans/PLAN-*.md` to confirm the plan file exists; OR omit the `plan_id` param and let the server auto-derive from the session's audit tail. |
| `budget_hard_stop_per_spawn` | Single spawn exceeds $0.50 cap | Shrink the spawn prompt; `spawn_agent` inherits `ADR-040 LiveCallPolicy`, which is deliberately tight. |
| `budget_hard_stop_per_plan_5min` | Plan's 5-minute spawn budget exceeds $2.00 | Wait five minutes; OR the Owner reviews why the plan is spawning that fast and adjusts workflow. |
| `breaker_open` (spawn_agent) | Live adapter circuit breaker is tripped per `ADR-040 §2` | Wait for the breaker to close (see `audit-query.py tail --action breaker_closed`); investigate `breaker_opened` events to find the root cause. |
| `server.capabilities` returns `spawn_agent_enabled: false` | Client ACL omits `spawn_agent` | Follow §5 to enable the handler. |

If you hit an error that is not in this table, dump the audit log tail
and raise the issue — see §7.

## 7. Auditing your usage

Every MCP call — success or deny — emits an audit event.
The audit log is the single source of truth for what the server did on
your behalf.

Tail recent invocations and denials:
```bash
python3 .claude/scripts/audit-query.py tail --action mcp_handler_invoked --limit 20
python3 .claude/scripts/audit-query.py tail --action mcp_handler_denied --limit 20
```

Each row is a JSON object per `SPEC/v1/audit-log.schema.md` v2.5.
Relevant fields:

- `ts` — ISO-8601 timestamp of the event.
- `action` — `mcp_handler_invoked` or `mcp_handler_denied`.
- `handler` — which MCP method was called.
- `client_id` — hashed to 16 hex chars per `ADR-042 §Auth.5`.
- `transport` — `http` or `stdio`.
- `reason` (deny rows only) — one of the values in §6.

The server NEVER logs the raw token value.
Redaction happens at the handler-parse boundary per `ADR-042 §Auth.6`
and again at `_lib/audit_emit.py` per `ADR-035` double-redaction
precedent.

For summary queries across a day or a plan, see `audit-query.py --help`
and `docs/audit-dashboard.md`.

## 8. Uninstalling or disabling

Three options, from lightest to heaviest.

### 8.1 Temporary kill-switch (recommended first)

Export the kill-switch in the shell where Cursor is launched:
```bash
export CEO_SOTA_DISABLE=1
```
The next MCP server invocation logs `mcp_server_disabled_by_kill_switch`
and exits 0 before binding any port or pipe.
No config changes, no file removals.

Re-enable by unsetting: `unset CEO_SOTA_DISABLE` and restarting Cursor.

### 8.2 Remove the client ACL (keep the server code)

Edit `.claude/settings.json` and delete the `mcp_client_registry.<id>`
block for the client you want to retire.
Also delete `state/mcp_client_secrets/<id>.key`:
```bash
rm state/mcp_client_secrets/YOUR_CLIENT_ID_HEX16.key
```
Restart Cursor; it will report the MCP server disconnected.

### 8.3 Full uninstall

Remove server code, remove client secrets, remove settings blocks, and
remove the Cursor entry:

```bash
cd /absolute/path/to/your/project
rm -rf .claude/scripts/mcp-server/
rm -rf state/mcp_client_secrets/
```

Then edit `.claude/settings.json` and remove both `mcp_client_registry`
and `mcp_rate_limits` top-level keys (if present).

Then edit Cursor's `mcp_settings.json` (path per §4) and delete the
`"ceo-orchestration"` entry from the `mcpServers` object.

Restart Cursor.
The framework itself is unaffected — Claude Code inside the project
continues to work normally; you have only removed the MCP surface.

---

If you hit something not in §6 Troubleshooting, open a
`.claude/plans/ISSUE-*.md` describing the repro steps, the audit log
tail, and the Cursor version, or email the Owner.
