"""MCP handlers — 7 modules per ADR-042 §Auth.2 ACL allowlist.

Each handler module exports a single `handle(request: dict) -> dict`
function returning a JSON-RPC 2.0-compliant result dict. Auth + ACL +
rate-limit enforcement happens in server.py BEFORE handler entry;
handlers MAY assume they run inside an authorized context.

Handler names (mirror ADR-042 §Auth.2):
- list_skills
- get_skill
- list_agents
- list_pitfalls
- get_audit_log
- spawn_agent           (governance passthrough MANDATORY — §Auth + §Cost)
- server.capabilities   (7th handler per PLAN-013 consensus §S4)
"""
