"""MCP Server package — Model Context Protocol over JSON-RPC 2.0.

See ADR-042 (MCP Server Contract) + SPEC/v1/mcp-server.schema.md.
Implementation target: stdlib-only per ADR-002 + A.0 spike verdict
(docs/research/mcp-sdk-vs-stdlib.md — stdlib UPHELD 2026-04-15).

Phase A deliverables (PLAN-013):
- server.py         — entry point + JSON-RPC 2.0 transport + 7 handlers
- auth.py           — HMAC bearer + ACL + CORS (ADR-042 §Auth)
- rate_limit.py     — token-bucket per client (ADR-042 §Auth.3)
- cost.py           — LiveCallPolicy inheritance (ADR-042 §Cost)
- handlers/         — one module per MCP handler

Zero top-level imports at package level — consumers import submodules
explicitly (stdlib discipline; pay-for-what-you-use).
"""
