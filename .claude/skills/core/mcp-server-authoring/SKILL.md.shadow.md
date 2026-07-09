---
name: core-mcp-server-authoring
description: Engineering doctrine for building MCP (Model Context Protocol) servers
  within {{PROJECT_NAME}}. Covers server lifecycle, tool registration, schema design,
  error handling, security boundaries (stdin/stdout-only IPC, no shell injection, env-var
  allowlisting), and testing patterns (contract + fuzz + smoke). Use when authoring a
  new MCP server, reviewing an MCP server implementation, extending an existing server
  with new tools, or auditing an MCP server for security or correctness. The MCP
  integration architecture is decided in ADR-042 and ADR-062; this skill is the
  authoring doctrine consulted when implementing.
owner: MCP Builder (archetype)
inspired_by:
  - source: msitarzewski/agency-agents/specialized/specialized-mcp-builder.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: pattern_reference
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
  - source: affaan-m/ecc/skills/agent-harness-construction/SKILL.md@81af40761939056ab3dc54732fd4f562a27309d0
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-07-07
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 6
risk_class: medium
stack: [typescript, node]
context_budget_tokens: 900
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 7}
  engine: {active: true, priority: 5}
  fintech: {active: true, priority: 6}
  trading-readonly: {active: true, priority: 9}
  generic: {active: true, priority: 6}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)mcp|tool.?author"}
source: affaan-m/ecc@81af4076 skills/agent-harness-construction/
license: MIT
---

# MCP Server Authoring

Every tool boundary exposed by an MCP server is an attack surface. The server
receives JSON-RPC requests from an LLM harness that also controls tool selection
— meaning a compromised or malformed tool call can trigger arbitrary server-side
behavior if the server does not validate inputs rigorously. The ONLY trust boundary
is the stdin/stdout channel: everything that enters the server through that channel
is untrusted input until schema-validated. Everything that leaves through stderr is
a diagnostic for the operator, not a JSON-RPC response, and must never carry secrets
or user data that reaches the client.

Build MCP servers as if the caller is adversarial by default. They probably are not,
but the invariants that make the safe case safe also make the adversarial case safe.

## What This Skill Is (and isn't)

This is authoring doctrine for building MCP server implementations — the rules,
patterns, and examples a developer needs when writing a new server or adding a tool
to an existing one. It pairs with `core/security-and-auth` (general boundary-defense
patterns) and `core/observability-and-ops` (diagnostic / audit emission patterns).

This skill is NOT the registry and configuration layer. Which servers are enabled,
how they are registered, and how the framework discovers them at runtime is decided in
ADR-042 (MCP server contract) and ADR-062 (RAG sidecar MCP opt-in). This skill
governs how to build a server that satisfies those ADRs — not how to configure or
deploy one.

When in doubt about whether a concern belongs here or in an ADR: if it is a rule
about how to WRITE server code, it belongs here; if it is a policy about WHICH servers
are allowed, it belongs in an ADR.

## Hard Rules

These rules are non-negotiable. Violations block the MCP server from being
registered in the framework until resolved. The rationale for each is stated
because understanding why a rule exists is the only durable enforcement.

1. **stdin/stdout are the only IPC channels.** The MCP server reads requests
   from stdin and writes responses to stdout. No TCP sockets, Unix domain sockets,
   or HTTP listeners unless the adopter explicitly overrides via ADR amendment and
   the `CEO_MCP_TRANSPORT` env var is set. Rationale: loopback-only stdio is the
   smallest possible network exposure; any network listener expands the auth perimeter.

2. **No `shell=True` in subprocess calls.** Every subprocess invocation passes
   args as a list: `subprocess.run(["git", "log", "--oneline"], ...)`. String
   concatenation into a shell command is injection. Rationale: tool params arrive
   as untrusted strings; shell expansion interprets `; rm -rf /` the same as any
   other token.

3. **Schema validation on every tool input.** Before any handler logic executes,
   validate the incoming params against the tool's declared schema. Reject with a
   JSON-RPC `INVALID_PARAMS` error if validation fails. Rationale: handler logic
   written under the assumption that params match the schema will behave incorrectly
   (at best) or unsafely (at worst) when params are out-of-spec.

4. **Env-var allowlist, not passthrough.** When a tool handler needs an env var,
   declare it in the server's allowlist and read it explicitly: `os.environ.get("FOO")`.
   Never pass `env=os.environ` to subprocess — and **never call `subprocess.run(...)`
   without an explicit `env=` argument either**, because Python's default behavior
   when `env` is omitted is to inherit the parent process's full environment
   (the same risk as `env=os.environ`). Always pass an explicit minimal env dict:
   `env={"PATH": "/usr/bin:/bin", "HOME": safe_home, "FOO": value}`. Rationale:
   the full process env may contain secrets (API keys, session tokens) that must
   not reach child processes that do not need them.

5. **stderr for diagnostics, stdout for JSON-RPC only.** Diagnostic output,
   tracebacks, and log lines go to stderr. stdout carries ONLY well-formed
   JSON-RPC 2.0 messages. A stray `print()` to stdout corrupts the wire framing.
   Rationale: the MCP client parses stdout line-by-line as JSON; a non-JSON line
   produces a parse error on the client side that is hard to diagnose.

6. **Every error path emits a JSON-RPC error envelope.** Uncaught exceptions that
   bubble out of a handler must be caught at the server dispatch loop, logged to
   stderr, and returned as a `{"jsonrpc":"2.0","id":<id>,"error":{"code":-32603,
   "message":"Internal error"}}` envelope. Rationale: a silent hang or a raw
   traceback on stdout breaks the client protocol.

7. **No eval, exec, or dynamic code execution from tool params.** Tool params must
   never be passed to `eval()`, `exec()`, `compile()`, or any template engine that
   evaluates code. Rationale: code injection through tool params is the highest-
   severity class of MCP server vulnerability.

8. **Idempotency markers on mutating tools.** Tools that mutate state declare
   `"idempotent": false` in their schema descriptor. Tools that are safe to retry
   (read-only or genuinely idempotent writes) declare `"idempotent": true`.
   Rationale: the MCP harness may retry on timeout; non-idempotent tools retried
   silently can double-write or double-delete.

9. **Capability advertisement is mandatory.** The server must respond to a
   `server.capabilities` request with its protocol version, list of tool names,
   and feature flags before any tool call is processed. Rationale: clients that
   probe for capabilities before calling are safer than clients that guess; the
   server must make the contract discoverable.

10. **No unbounded reads from stdin.** Cap the maximum line length for incoming
    requests (default: 1 MiB). Reject oversized requests with a JSON-RPC
    `INVALID_REQUEST` error. Rationale: an oversized payload can exhaust memory
    before JSON parsing begins; the cap must be enforced at the read layer, not
    inside the JSON parser.

11. **Secrets are never logged.** Tool params may contain secrets passed by the
    harness. The server must redact known-secret fields before any log emission
    (use `_lib/redact.py` if integrated with the framework). Unknown fields that
    pattern-match secret heuristics (key names containing `token`, `secret`,
    `password`, `key`, `credential`) must be redacted to `<REDACTED>`.
    Rationale: stderr is often piped to log aggregators; accidental secret logging
    propagates through the entire observability stack.

12. **Graceful shutdown on SIGTERM/SIGINT.** The server must register signal
    handlers that flush any in-flight response, emit a shutdown log line to
    stderr, and exit cleanly. Rationale: abrupt exits during a tool call leave
    the client hanging; a clean shutdown allows the client to retry or surface an
    error to the user.

## Tool Schema Design

A tool schema is a contract, not a hint. The server enforces it; the client
depends on it. Ambiguous schemas produce ambiguous implementations.

### Parameter contracts

Declare every parameter with:

- `type` — one of `string`, `integer`, `number`, `boolean`, `array`, `object`,
  `null`. No bare `any` types.
- `description` — one sentence that tells the client what value is expected.
  Include constraints inline: `"description": "Relative path under /workspace;
  no traversal sequences (../)."`.
- `required` — list all required param names at the tool level; do not use
  optional params as a substitute for validation.
- `minLength` / `maxLength` for strings, `minimum` / `maximum` for numbers —
  set explicit bounds wherever the handler will break on out-of-range values.

```python
# CORRECT — schema with explicit constraints
TOOL_SCHEMA = {
    "name": "read_file",
    "description": "Read a file from the workspace. Returns UTF-8 content.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Workspace-relative path; no ../ traversal.",
                "maxLength": 4096,
            }
        },
        "required": ["path"],
        "additionalProperties": False,
    },
    "idempotent": True,
}

# WRONG — unconstrained schema
TOOL_SCHEMA = {
    "name": "read_file",
    "inputSchema": {"type": "object"},  # no constraints, no description
}
```

### Error envelopes

Return JSON-RPC 2.0 error objects for all failure cases:

| Failure class | JSON-RPC code | `message` |
|---|---|---|
| Malformed JSON request | `-32700` | `"Parse error"` |
| Method / tool not found | `-32601` | `"Method not found"` |
| Invalid params (schema fail) | `-32602` | `"Invalid params: <field>: <reason>"` |
| Handler logic error | `-32603` | `"Internal error"` |
| Resource not found | `-32000` | `"Resource not found: <name>"` |
| Permission denied | `-32001` | `"Permission denied"` |
| Rate limit exceeded | `-32002` | `"Rate limit exceeded; retry after <N>s"` |

The `data` field of the error object is optional and should carry only
non-sensitive diagnostic information that is safe to surface to the client.
Never put stack traces in `data`; they go to stderr only.

### Idempotency markers

Clients that retry on timeout need to know whether a retry is safe. The
`idempotent` field in the tool schema is the signal:

```python
{"name": "append_log", "idempotent": False}   # mutating, do not retry
{"name": "get_skill", "idempotent": True}      # safe to retry
```

If the framework client does not read this field, the server should implement
a request-ID deduplication layer: cache the last N responses keyed by
`request.id`; if the same ID arrives twice within the TTL window, return the
cached response without re-executing the handler.

## Designing the Tool Surface for the Calling Agent

The Hard Rules keep the server *safe*. They say nothing about whether the LLM
harness on the other end of the pipe can actually *use* it. A server can be
airtight and still drive the calling agent into retry loops, wrong-tool
selection, and dead ends — because tool names are ambiguous, granularity is
wrong, or responses give the agent nothing to act on. Usability of the tool
surface is a first-class authoring concern, not polish: the consuming harness
picks a tool, fills its params, reads the result, and decides what to do next
*entirely from the text you emit*. Everything below raises the odds it picks
correctly on the first try and recovers cleanly when it does not.

### Action space

- **Name tools for what they do, stably.** A tool name is part of the contract
  the harness reasons over; renaming a tool silently breaks every prompt that
  learned it. Prefer explicit verb-noun names (`read_file`, `append_log`) over
  vague ones (`process`, `handle`, `run`).
- **Keep each input schema narrow and single-purpose.** A tool that does one
  thing with a few well-bounded params is selected correctly far more often than
  a catch-all tool with a mode flag that changes what the other params mean.
  Narrow schemas also shrink the fuzz surface (see Testing Patterns, Layer 2)
  and make the constraints in Tool Schema Design easier to state.
- **Return a deterministic output shape.** The same tool should return the same
  result keys in the same structure on every call, success or failure. A harness
  that has to branch on which fields happen to be present this time makes worse
  decisions than one reading a fixed shape. This is the usability twin of the
  wire-framing rule (Hard Rule 5): stable *shape* is to the agent what stable
  *framing* is to the transport.
- **Avoid catch-all tools unless isolation is genuinely impossible.** One
  `do_everything` tool with a `command` string is both a selection problem for
  the agent and, usually, a `shell=True`-shaped hole (Hard Rule 2). Split it.

### Granularity

Match tool granularity to the blast radius and the round-trip cost:

- **Micro-tools for high-risk operations** — deploy, migration, permission
  change, anything mutating (`"idempotent": false`). One narrow action per tool
  so the agent (and the audit log) can see exactly what was authorized.
- **Medium tools for the common read/edit/search loop** — the everyday verbs
  where round-trip overhead is small relative to the work.
- **Macro-tools only when round-trip overhead dominates** — batch a fixed,
  well-understood sequence when the latency of N calls is the actual bottleneck,
  never to paper over a missing action.

### Observation design — make the response actionable

An error envelope (see the JSON-RPC table above) tells the client that
something failed. It does not tell the *agent* what to do next. For tools whose
results feed further agent decisions, structure the `result` payload so the
model can act without guessing. A useful result carries:

- `status` — `success` / `warning` / `error`, so the agent branches on one field.
- `summary` — a one-line human-readable outcome.
- `next_actions` — concrete follow-ups the agent can take (e.g. "call
  `read_file` on the path in `artifacts[0]`").
- `artifacts` — the file paths / IDs the next step will need, not prose the
  agent must re-parse.

This is additive to — never a replacement for — the JSON-RPC error envelope:
protocol-level failures still return a `-32xxx` error object; `status`-shaped
observations live inside a *successful* `result` where the tool ran but the
outcome needs interpretation.

### Error-recovery contract

Every error a tool can return should give the agent three things, or it will
loop:

1. **A root-cause hint** — what actually went wrong, in the `message` (never a
   raw traceback; those go to stderr per Hard Rule 5).
2. **A safe retry instruction** — whether retrying is safe at all (tie this to
   the `idempotent` marker) and what to change first.
3. **An explicit stop condition** — when the agent should *stop* retrying and
   surface the failure, so a permanent error does not become an infinite loop.

A `-32001 Permission denied` on a path-traversal attempt, for instance, is a
*stop* signal, not a *retry-with-a-different-path* signal — say so.

### Benchmark the surface, not just the latency

Server correctness tests (Testing Patterns) prove the server behaves; they do
not prove the *agent* succeeds through it. When a server is on a hot agent path,
track the harness-level signals that reveal an unusable surface:

- completion rate (did the agent finish the task through these tools?),
- retries per task (a spike points at ambiguous names or thin error messages),
- pass@1 vs. pass@3 (a large gap means the surface is recoverable but not
  first-try clear),
- cost per successful task (macro-tool over-batching and retry loops both show
  up here).

These are diagnostic, not gate criteria — but a regression in retries-per-task
after a tool change is the earliest signal that the surface got harder to use.

## Security Boundaries

### stdin/stdout enforcement

The server process must:

1. Open stdin in binary mode and parse newline-delimited JSON.
2. Write responses to stdout as newline-terminated JSON.
3. Never open listening sockets unless `CEO_MCP_TRANSPORT=tcp` is explicitly
   set AND the adopter has amended ADR-042 for their installation.
4. Close file descriptors 3..N on startup (except stderr) to prevent
   accidental inheriting of parent-process network connections.

```python
# CORRECT — binary stdin, no socket
import sys
import os

def main():
    # close any inherited FDs beyond stderr
    os.closerange(3, 256)
    for line in sys.stdin.buffer:
        handle_request(line)

# WRONG — opens a socket
import socket
srv = socket.socket()
srv.bind(("0.0.0.0", 8080))  # expands attack surface
```

### Env-var allowlist

```python
# CORRECT — explicit allowlist
ALLOWED_ENV = {"WORKSPACE_ROOT", "LOG_LEVEL", "CEO_MCP_TIMEOUT"}

def get_env(name: str) -> Optional[str]:
    if name not in ALLOWED_ENV:
        raise ValueError(f"env var {name!r} not in allowlist")
    return os.environ.get(name)

# CORRECT — subprocess with explicit minimal env (does NOT inherit parent env)
SAFE_PATH = "/usr/bin:/bin"
subprocess.run(
    ["git", "log", "--oneline", "-10"],
    cwd=workspace_root,
    capture_output=True,
    env={"PATH": SAFE_PATH, "HOME": str(workspace_root)},
)

# WRONG — env omitted → Python inherits the parent process's FULL environment
# (same risk as env=os.environ). Common misconception: omitting env ≠ "no env."
subprocess.run(cmd, capture_output=True)  # silent inheritance — leaks secrets

# WRONG — full env passthrough to subprocess
subprocess.run(cmd, env=os.environ)  # leaks all secrets to child process
```

### Path traversal prevention

File-operation tools must canonicalize the incoming path and confirm it
remains inside the workspace root before any I/O:

```python
import pathlib

def safe_path(workspace: str, user_path: str) -> pathlib.Path:
    root = pathlib.Path(workspace).resolve()
    target = (root / user_path).resolve()
    # WRONG (do not do this): `if not str(target).startswith(str(root))`
    # accepts sibling dirs with the same prefix (e.g. /tmp/workspace_evil
    # passes when root=/tmp/workspace). Use path-aware containment instead.
    try:
        target.relative_to(root)  # raises ValueError on escape
    except ValueError as exc:
        raise PermissionError(f"path traversal rejected: {user_path!r}") from exc
    return target
```

Reject the request with a `-32001 Permission denied` error if the resolved
path escapes the root. Log the attempt to stderr with the raw user-supplied
path (not the resolved path, which may not exist and leaks nothing) so the
operator can detect probing.

### No dynamic execution

```python
# WRONG — eval from tool param
result = eval(params["expression"])

# WRONG — template with code execution
template.render(code=params["snippet"])  # if template engine calls exec

# CORRECT — whitelist of safe operations
SAFE_OPS = {"sum", "count", "mean"}
op = params.get("operation")
if op not in SAFE_OPS:
    raise ValueError(f"unsupported operation: {op!r}")
result = dispatch_safe_op(op, params["data"])
```

## Error Handling Patterns

### Dispatch loop structure

```python
def run_server():
    for raw_line in sys.stdin.buffer:
        request_id = None
        try:
            request = json.loads(raw_line)
            request_id = request.get("id")
            response = dispatch(request)
        except json.JSONDecodeError as exc:
            response = error_envelope(None, -32700, "Parse error")
            print(f"[MCP] parse error: {exc}", file=sys.stderr)
        except SchemaValidationError as exc:
            response = error_envelope(request_id, -32602, f"Invalid params: {exc}")
        except PermissionError as exc:
            response = error_envelope(request_id, -32001, "Permission denied")
            print(f"[MCP] permission denied: {exc}", file=sys.stderr)
        except Exception as exc:
            response = error_envelope(request_id, -32603, "Internal error")
            # full traceback to stderr only — never to stdout
            import traceback
            traceback.print_exc(file=sys.stderr)
        finally:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
```

### Diagnostics vs client-visible errors

| Layer | Destination | What goes there |
|---|---|---|
| Operator diagnostics | stderr | Tracebacks, timing, config load events, retry counts |
| Client error | stdout JSON-RPC error `message` | Human-readable one-liner safe to display; no stack trace |
| Client error `data` | stdout JSON-RPC error `data` | Non-sensitive field names, constraint violations; never secrets |
| Audit events | audit-log.jsonl via `_lib/audit_emit.py` | `mcp_handler_denied`, `mcp_tool_called`, `mcp_schema_rejected` |

If the framework's `_lib/audit_emit.py` is available, emit an audit event for
every tool call and every denial. Minimum fields: `ts`, `action`, `tool_name`,
`client_id` (hashed), `outcome` (`allowed` / `denied`), `reason` (on denial).

## Testing Patterns

MCP server tests operate at three layers, each catching a distinct failure class.

### Layer 1 — Contract tests (schema + JSON-RPC envelope)

Contract tests verify that the server honours its declared schema and error
envelopes without executing real I/O. They are fast and can run in the CI gate
on every commit.

```python
# pytest example
def test_invalid_params_returns_32602(server):
    req = {"jsonrpc": "2.0", "id": 1, "method": "read_file",
           "params": {}}  # missing required "path"
    resp = server.send(req)
    assert resp["error"]["code"] == -32602
    assert "path" in resp["error"]["message"]

def test_unknown_method_returns_32601(server):
    req = {"jsonrpc": "2.0", "id": 2, "method": "no_such_tool", "params": {}}
    resp = server.send(req)
    assert resp["error"]["code"] == -32601
```

### Layer 2 — Fuzz tests (adversarial params)

Fuzz tests inject out-of-contract values into every tool and assert the server
returns a well-formed error envelope — never a crash, never a raw exception on
stdout, never a hang.

Fuzz dimensions to cover per tool:
- Empty string, null, integer where string expected
- Very long string (> `maxLength` + 1)
- Path traversal sequences: `../../../etc/passwd`, `..%2F..%2F`
- Shell-injection strings: `; rm -rf /`, `` `id` ``, `$(whoami)`
- Unicode edge cases: NFC vs NFD normalization, null byte `\x00`, surrogate pairs
- Large integer / negative integer where bounded integer expected

```python
@pytest.mark.parametrize("bad_path", [
    "../../etc/passwd",
    "../" * 20 + "etc/shadow",
    "/absolute/escape",
    "a" * 5000,
    "path\x00null",
])
def test_traversal_paths_rejected(server, bad_path):
    req = {"jsonrpc": "2.0", "id": 1, "method": "read_file",
           "params": {"path": bad_path}}
    resp = server.send(req)
    assert "error" in resp
    assert resp["error"]["code"] in (-32602, -32001)
    # must not crash or hang
```

### Layer 3 — Smoke tests (mock client round-trip)

Smoke tests run the server as a subprocess and communicate over its actual
stdin/stdout pipe — the same way the MCP harness communicates with it. They
catch framing bugs (stray prints to stdout, binary output, missing newlines)
that contract tests miss.

```python
import subprocess, json

def test_smoke_capabilities():
    proc = subprocess.Popen(
        ["python3", "mcp_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": "."},  # explicit minimal env
    )
    req = json.dumps({"jsonrpc":"2.0","id":1,
                      "method":"server.capabilities","params":{}}) + "\n"
    proc.stdin.write(req.encode())
    proc.stdin.flush()
    raw = proc.stdout.readline()
    resp = json.loads(raw)
    assert "result" in resp
    assert "tools" in resp["result"]
    proc.terminate()
```

The three layers together catch: schema violations (L1), injection /
boundary attacks (L2), and wire-level framing bugs (L3). A CI gate that
runs all three in under 30 seconds is achievable for any server of
moderate complexity.

## WRONG / CORRECT Examples

### 1. Tool registration — env-var injection

```python
# WRONG — env var injected into shell command
def handle_run_script(params):
    script = params["script_name"]
    os.system(f"bash {script}")  # shell=True via os.system; injection trivial

# CORRECT — args list, no shell, explicit minimal env
def handle_run_script(params):
    script = params["script_name"]
    validate_schema(params, RUN_SCRIPT_SCHEMA)
    safe = safe_path(WORKSPACE_ROOT, script)
    result = subprocess.run(
        ["bash", str(safe)],
        capture_output=True, text=True, timeout=30,
        env={"PATH": "/usr/bin:/bin", "HOME": str(WORKSPACE_ROOT)},  # Hard rule #4
    )
    return {"stdout": result.stdout, "returncode": result.returncode}
```

### 2. Schema validation — missing check

```python
# WRONG — handler assumes params are valid
def handle_get_skill(params):
    name = params["name"]          # KeyError if "name" absent
    return SKILLS[name]            # KeyError if skill absent; unhandled

# CORRECT — validate first, handle missing cleanly
def handle_get_skill(params):
    validate_schema(params, GET_SKILL_SCHEMA)   # raises SchemaValidationError
    name = params["name"]
    skill = SKILLS.get(name)
    if skill is None:
        raise ResourceNotFoundError(f"skill {name!r} not found")
    return {"skill": skill}
```

### 3. Error output — raw exception to stdout

```python
# WRONG — unhandled exception reaches stdout as plain text
def dispatch(request):
    method = request["method"]
    return HANDLERS[method](request["params"])  # KeyError → traceback on stdout

# CORRECT — all exceptions caught at dispatch boundary
def dispatch(request):
    method = request.get("method")
    handler = HANDLERS.get(method)
    if handler is None:
        return error_envelope(request.get("id"), -32601, "Method not found")
    try:
        result = handler(request.get("params", {}))
        return {"jsonrpc": "2.0", "id": request.get("id"), "result": result}
    except SchemaValidationError as exc:
        return error_envelope(request.get("id"), -32602, str(exc))
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)   # diagnostics → stderr
        return error_envelope(request.get("id"), -32603, "Internal error")
```

### 4. Path traversal — no canonicalization

```python
# WRONG — user path used directly
def handle_read_file(params):
    path = params["path"]
    with open(path) as f:           # ../../etc/passwd works
        return f.read()

# CORRECT — canonicalize and confirm inside workspace
def handle_read_file(params):
    validate_schema(params, READ_FILE_SCHEMA)
    safe = safe_path(WORKSPACE_ROOT, params["path"])
    with open(safe) as f:
        return {"content": f.read()}
```

### 5. Subprocess env passthrough

```python
# WRONG — full env to child; leaks ANTHROPIC_API_KEY etc.
subprocess.run(["git", "status"], env=os.environ)

# CORRECT — minimal env with FIXED safe values (do NOT pull from os.environ;
# parent PATH may be malicious or include attacker-controlled directories,
# parent HOME may expose user-config files the child should not read)
minimal_env = {
    "PATH": "/usr/bin:/bin",                # fixed safe value
    "HOME": str(workspace_root),            # isolate to workspace, not real $HOME
}
subprocess.run(["git", "status"], env=minimal_env, cwd=workspace_root)
```

## Anti-Patterns

### Silent error swallowing

```python
try:
    result = handler(params)
except Exception:
    pass   # caller receives no response; client hangs indefinitely
```

Why it fails: the client sent a request with an id and expects a response.
Swallowing the error without writing an error envelope to stdout leaves the
client waiting until its timeout, producing a confusing user-visible error
("server stopped responding") that hides the real cause.

Recovery: wrap every handler invocation in the dispatch loop try/except
pattern described in the Error Handling section. An error envelope is always
better than silence.

### Mixing diagnostic and wire output

```python
print(f"handling {method}")       # stray print to stdout
sys.stdout.write(response + "\n") # wire frame
```

Why it fails: the diagnostic line is not valid JSON; the MCP client parses
it as a malformed message. The downstream error ("unexpected token 'h'") is
hard to trace back to the diagnostic print.

Recovery: use `print(..., file=sys.stderr)` for all diagnostics. Gate any
print statement in MCP server code with a linter rule or grep in CI:
`! git diff HEAD | grep '^\+.*print(' | grep -v 'sys.stderr'`.

### Schema as documentation only

```python
# schema declared but validation skipped
TOOL_SCHEMA = {"name": "write_file", "inputSchema": {...}}

def handle_write_file(params):
    path = params["path"]  # no validation; schema is fiction
```

Why it fails: the schema tells the client what to send; if the server does not
enforce it, adversarial or buggy clients that send out-of-spec values cause
undefined behavior in the handler. The schema contract is bilateral.

Recovery: call `validate_schema(params, TOOL_SCHEMA["inputSchema"])` as the
first line of every handler. Treat a missing schema as a BLOCKER in code review.

### Capabilities endpoint as optional

Skipping `server.capabilities` because "the client already knows what tools
there are."

Why it fails: capability discovery is how clients avoid hard-coding tool
lists that drift out of sync with the server. A server without a capabilities
endpoint couples every client to its current tool list; adding or removing a
tool silently breaks clients.

Recovery: implement `server.capabilities` before any other handler. The
contract is declared in ADR-042 §protocol-capability-discovery.

### Using a global request counter as request ID

```python
_counter = 0
def next_id():
    global _counter
    _counter += 1
    return _counter
```

Why it fails: if the server ever restarts while a client is in-flight, IDs
restart at 1 and collide with in-flight IDs from the previous session.
Idempotency deduplication keyed on request ID silently returns stale cached
responses to new requests.

Recovery: the server does not generate request IDs — the client does. The
server echoes `request["id"]` verbatim in every response. If deduplication
is needed on the server side, key on `(session_id, request_id)` where
`session_id` is a UUID generated at server startup.

## Acceptance Criteria

A new MCP server implementation is ready for registration when ALL of the
following are true:

- [ ] Hard Rules 1-12 satisfied: reviewer has checked each against the code.
- [ ] Tool schemas declare `type`, `description`, `required`, `additionalProperties: false`,
      and numeric/string bounds for every parameter that has a natural bound.
- [ ] `server.capabilities` handler implemented and returns tool list + protocol version.
- [ ] All error paths return a JSON-RPC error envelope; no uncaught exception reaches
      stdout; no raw tracebacks on stdout.
- [ ] stderr carries no secrets (no API keys, tokens, passwords in log output).
- [ ] Layer 1 contract tests: at least one test per tool per error-code class
      (`-32601`, `-32602`, `-32603`, one domain error).
- [ ] Layer 2 fuzz tests: path traversal, shell injection, oversized input, null byte,
      wrong type — all covered for every tool that accepts string input.
- [ ] Layer 3 smoke test: server runs as subprocess, capabilities round-trip succeeds,
      server exits cleanly on SIGTERM.
- [ ] CI gate: all three test layers run on every commit touching the server code.
- [ ] Env-var allowlist documented in the server module docstring.
- [ ] `idempotent` marker set for every tool in the schema descriptor.
- [ ] No `shell=True` anywhere in the server codebase (enforced by grep in CI or
      code review checklist item).

## Related Skills

- `core/security-and-auth` — general boundary defense, timing-safe comparison,
  secret redaction patterns; the MCP server's security boundary is a specialization
  of the principles there.
- `core/observability-and-ops` — audit event emission, structured stderr logging,
  health-check signal design; use when wiring `_lib/audit_emit.py` into the server.
- `core/code-review-checklist` — adversarial framing for reviewing MCP server PRs;
  the tool-introduction scoring matrix applies when a new server is registered.
- `ADR-042` (`.claude/adr/ADR-042-mcp-server-contract.md`) — auth model, rate
  limits, CORS, cost-cap inheritance; the server must satisfy all §Auth invariants.
- `ADR-062` (`.claude/adr/ADR-062-rag-sidecar-mcp-opt-in.md`) — opt-in sidecar
  architecture; the stdlib-only invariant and isolated-venv pattern apply to any
  sidecar server built to this spec.
- `ADR-110` (`.claude/adr/ADR-110-codex-pretool-enforcement.md`) — governance gap
  for MCP tools that bypass the `check_canonical_edit` hook; relevant if the server
  exposes write-capable tools that could be used to modify canonical-guarded files.

## Changelog

- **2026-07-07 (PLAN-153 Wave G, SP-040)**: added "Designing the Tool Surface
  for the Calling Agent" (action space, granularity, actionable observation
  design, the error-recovery contract, and surface-level benchmark signals) —
  porting agent-harness-construction practice so the skill covers whether the
  calling harness can *use* the server, not only whether the server is *safe*.
  Clean-room ADAPT merge; additive only — the security-first Hard Rules are
  unchanged and every new usability rule is cross-referenced back to the Hard
  Rule it complements (stable output shape ↔ wire framing, narrow schema ↔ fuzz
  surface, retry guidance ↔ idempotency markers). No section renumbered.
Skill-Import-Attestation: reviewed-by=AE9B236FDAF0462874060C6BCFCFACF00335DC74; sha256=a53d2b95398fa56f83d51a21a69dfad965358b5063489fb3875f614187357f97
