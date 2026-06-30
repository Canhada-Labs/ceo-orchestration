# SPEC/v1/rag-sidecar.schema.md

> **Normative source:** SELF (self-authoritative — see ADR-007
> §Self-authoritative pattern). Paired-ADR: ADR-062 (LightRAG
> sidecar opt-in).
>
> **Version:** v1.0 (PLAN-041 / ADR-062) — protocol contract between
> the framework's stdlib bridge (`.claude/hooks/_lib/rag_bridge.py`)
> and the LightRAG sidecar process.
>
> **Stability:** additive. Breaking changes require SPEC bump +
> ADR amendment. LightRAG version drift is detected by the bridge
> against `lightrag_mcp_version` field in the response envelope.

## Transport

- **Primary:** Unix domain socket at
  `~/.ceo-orchestration/rag/sidecar.sock` (mode `0600`).
- **Windows fallback:** Named Pipe with DACL-restricted ACL.
- **TCP last-resort (Windows/WSL only):** loopback `127.0.0.1:<port>`
  with 256-bit bearer token — gated by env `CEO_RAG_SIDECAR_TRANSPORT=tcp`
  + `CEO_RAG_TCP_ACK=I-UNDERSTAND-LOOPBACK-IS-NOT-AUTH`.

## Framing

LSP-style (MCP-compatible):

```
Content-Length: <N>\r\n
\r\n
<N-byte UTF-8 JSON body>
```

Max response body: 4 MiB (bridge enforces `_MAX_RESPONSE_BYTES`).
Longer bodies are truncated → bridge returns `None` + `rag_query_fallback`.

## JSON-RPC 2.0 envelope

### Request

```json
{
  "jsonrpc": "2.0",
  "id": "<uuid4-string>",
  "method": "<method-name>",
  "params": { ... }
}
```

### Success response

```json
{
  "jsonrpc": "2.0",
  "id": "<matches-request>",
  "result": <method-specific>
}
```

### Error response

```json
{
  "jsonrpc": "2.0",
  "id": "<matches-request>",
  "error": {
    "code": <int>,
    "message": "<human-readable>",
    "data": { ... }
  }
}
```

Bridge treats any response with `"error"` as a failure → returns None.
Standard JSON-RPC error codes expected: `-32601` method not found,
`-32602` invalid params, `-32603` internal error, `-32000..-32099`
sidecar-specific (e.g. `-32001` index not ready, `-32002` model load
failed).

## Methods

### `rag.search`

Semantic search across the indexed corpus.

**Request params:**
```json
{"query": "<string, non-empty>", "top_k": <int, 1-100>}
```

**Success result:** array of chunk objects:
```json
[
  {
    "file": "<repo-relative path>",
    "line": <int, 1-based>,
    "score": <float, 0.0-1.0>,
    "snippet": "<string, <=8 KiB>",
    "id": "<opaque for rag.get_observations>"
  }
]
```

Empty array (`[]`) is valid. Wrong type → bridge returns None.

**Post-processing by bridge:**
1. Drop non-dict entries.
2. Scan `snippet` (fallback: `content`, `text`, `body`) via
   `_lib.output_scan.scan()`. LLM01 / LLM02 / LLM10 hit, OR vector
   `tag_character` / `homoglyph` → drop + `rag_query_redacted`.
3. Return surviving list.

### `rag.timeline`

Temporal view of symbol evolution.

**Request params:**
```json
{"symbol": "<string, non-empty>"}
```

**Success result:** array of event objects:
```json
[
  {
    "ts": <unix timestamp>,
    "symbol": "<string>",
    "kind": "<'defined' | 'modified' | 'referenced'>",
    "commit": "<git sha>",
    "snippet": "<string>"
  }
]
```

Same post-processing as `rag.search`.

### `rag.get_observations`

Full content retrieval by opaque id.

**Request params:**
```json
{"id": "<opaque non-empty string>"}
```

**Success result:** single string, ≤8 KiB. Not a list / dict.

Bridge wraps the string in a 1-element chunk list for uniform scan.
Dropped wrapping → returns None.

### `rag.health`

Non-invasive probe. p99 < 200 ms.

**Request params:** `{}`

**Success result:**
```json
{
  "ok": <bool>,
  "lightrag_mcp_version": "<semver or commit-sha>",
  "last_indexed_commit": "<git sha>",
  "chunks_total": <int>,
  "chunks_redacted": <int>
}
```

Bridge only consumes `"ok"`. Other fields are advisory for
observability (`ceo-health.py`, audit-dashboard).

## Bridge-side invariants

1. **Fail-open:** every method returns `Optional[...]`. Never raises.
2. **Single socket per call:** no pooling.
3. **Deadline-driven:** socket timeouts updated each recv based on
   remaining budget. Total wall ≤ `timeout_ms`.
4. **Framing verification:** `Content-Length` required; > 4 MiB →
   reject; body short of declared length → None.
5. **Envelope verification:** `"error"` key → fail; `"result"` →
   deliver (post-scan).
6. **Audit stamp:** exactly one `rag_query_issued` → followed by EITHER
   `rag_query_returned` OR `rag_query_fallback` per call.
   `rag_query_redacted` zero-to-many per call.

## Sidecar-side invariants

1. Unix socket `0600`; parent dir `0700`.
2. `rag.health` responds even with empty / rebuilding index.
3. `rag.search` returns `[]` on empty index, not error.
4. Sidecar logs JSON to `~/.ceo-orchestration/rag/sidecar.log`, NEVER
   to MCP response body.
5. Sidecar does NOT write audit log directly — bridge stamps HMAC
   (security-engineer Round 1 P1-2: sidecar does not hold HMAC key).

## Versioning

- SPEC `v1` is this file. Method signatures may extend fields
  (adopter-side tolerates unknown). Removing / renaming = SPEC v2 +
  ADR amendment.
- `lightrag_mcp_version` in `rag.health` lets `ceo-health.py` detect
  drift between installed LightRAG and the committed contract
  fixture. Drift → warning; breaking drift → CI fail via future
  `check-rag-contract-drift.py`.

## Golden contract fixture

Consumer-driven contract test at
`.claude/rag/tests/fixtures/mcp_contract_v1.json` (future Phase 6
deliverable — shipped by adopter when pinning LightRAG version).

Each fixture entry:
- Request shape
- Expected success response shape
- Expected empty response shape
- Expected error response shape (one representative code)
- `lightrag_mcp_version` at capture (drift sentinel)

## Change log

- **v1.0 (2026-04-19)** — initial SPEC. 3 tools + health probe +
  JSON-RPC 2.0 + LSP framing. Shipped with PLAN-041 Phase 6 /
  ADR-062 PROPOSED. Awaits PROPOSED → ACCEPTED at Phase 7.
