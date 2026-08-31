# PROPOSED-PATCH — wave-adrgate (S334)

Patch: `ADRGATE.patch` (derivado da sombra `shadow-adrgate` pelo
`finalize-adrgate.sh`; base declarada em `BASE-SHA.txt`).
Patch-sha256:

## Por path

| path | oráculo | o que muda |
|---|---|---|
| `.claude/adr/README.md` | CANÔNICO | seção `Declared supersession exemptions` (2 entradas revisadas) + tabela ADR-INDEX regenerada (linha do ADR-197) |
| `.claude/adr/ADR-197-user-profile-derivation.md` | CANÔNICO | `status: PROPOSED` → `ACCEPTED` + `accepted_at: 2026-08-31` + `decided_by` reescrito citando o `.asc` de `303ae55` |
| `.github/workflows/validate.yml` | CANÔNICO (KERNEL) | 2 steps no job de governança: `ADR chain integrity (declared-exemption ledger)` e `ADR index drift (generate-adr-index --check)` |
| `.claude/scripts/tests/test_check_adr_chain.py` | livre | fixture de corpus: `2 erros ADR-111` → `limpo + 2 entradas firing` (asserção bilateral) |

## O que este patch NÃO faz

- Não adiciona ADR (198 antes e depois; `check-claude-md-claims.py` rc 0
  sem tocar contagens).
- Não toca `scripts/` (ratchet do PLAN-185 não regenera).
- Não unifica a gramática de `Status:` (FU-ADR-GRAMMAR) nem cura o seed
  do README no adopter (FU-ADR-README-SEED) — decisões do Owner.

## Evidência pré-assinatura (S334, sombra base 5df5c48)

- `check-adr-chain.py`: FAIL 2 → **PASS 0** (rc 0).
- `generate-adr-index.py --check`: **rc 0** (após regenerar no patch; a
  primeira bateria da sombra REPROVOU aqui porque o flip do 197 muda a
  linha da tabela — o gate novo pegou o próprio patch, prova viva de valor).
- pytest (chain 49 + index 10 + frozen-subset 7): **66 passed**.
- `verify-counts.sh` na sombra: rc 0. `validate-governance.sh --fast`: 0.
- Controle negativo mandatory-fire (cópia descartável, entrada órfã):
  rc 1 com `did not fire` — o ledger não aceita entrada morta.
