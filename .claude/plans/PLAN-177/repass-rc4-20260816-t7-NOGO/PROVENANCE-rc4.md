# Proveniencia do re-pass do CANDIDATO rc.4 - PLAN-177 W2.2 - 2 partes
- Base: v1.3.0-rc.3 (ef90e9201790ed29a1b3f6f91ab7d357e65c5db0 -> 7362cfca026c1fd6b6cd780ff56329405ac91a25) .. Candidato: 8261acae552a1fe767b7aa34b1b3fc298c21a2b8 (PRE-tag, doutrina r17)
- Worktree detached do CANDIDATO: sim - Pipeline: prompt+diff -> codex_egress_redact --outgoing -> controles -> codex exec --sandbox read-only
- Data: 2026-08-16T10:13:24Z
- parte 1 (P1-4 decision gate in both validators + regression suites): VERDICT: NO-GO — The explicit decision gate exists, but its new shape check still authorizes malformed signed input and requires a P1 fix before rc.4. [codex rc=0]
  - payload-rc4-1.raw.txt NAO commitado; pin sha256: 3e7081a6fb0f8a7bd0d7f811bcdcdf4e9b8518fa14e720331918ac9fd0334e09
- parte 2 (P1-1 gitignore delivery via shared generator + P1-2/P1-3 npm honesty + T-1/T-2 + workflow wiring): VERDICT: NO-GO [codex rc=0]
  - payload-rc4-2.raw.txt NAO commitado; pin sha256: 1563a41265f93f0e6ae46423ff82190efb90e33f1ae086fb3064839b8b4d700e
RUNNER-OVERALL: rc=1
