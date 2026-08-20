# PLAN-182 W0 — Anexo 2: censo comportamental da família (US1/US2/US4, S316)

> Gerado por derive-audit-family.py (ferramenta do carve-out da W0). Comandos e saídas brutas.

## US1 — censo (`derive-audit-family.py`)
```
família derivada: 588 arquivos — {'test': 235, 'script': 122, 'hook': 100, 'dist': 92, 'doc': 16, 'spec': 9, 'template': 8, 'ci': 4, 'installer': 2}
no conjunto de cura da W1: 563
(allowlist explícita: spec/doc/plan mantêm o literal legitimamente e ficam fora da cura)
```

## Gate futuro da W1 (`--assert-migrated` — VERMELHO por design hoje)
```
assert-migrated: 102 módulo(s) runtime ainda constroem o caminho literal
exit: 1 (esperado)
```

## US2 — matriz artefato × env (`--matrix`; células assertadas em tests/test_derive_audit_family.py)
```json
{
 "audit_emit._audit_dir": {
  "sem-env": "/var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/tmp291k_c_n/.claude/projects/ceo-orchestration",
  "CLAUDE_PROJECT_DIR": "/var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/tmp291k_c_n/.claude/projects/ceo-orchestration",
  "CEO_STATE_ROOT": "/var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/tmp291k_c_n/.claude/projects/ceo-orchestration",
  "CEO_PROJECT_NAME": "/var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/tmp291k_c_n/.claude/projects/ceo-orchestration",
  "CEO_AUDIT_LOG_DIR": "/tmp/fake-audit"
 },
 "state_store._state_root": {
  "sem-env": "/var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/tmp291k_c_n/.claude/projects/ceo-orchestration/state",
  "CLAUDE_PROJECT_DIR": "/var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/tmp291k_c_n/.claude/projects/ceo-orchestration/state",
  "CEO_STATE_ROOT": "/tmp/fake-state-root",
  "CEO_PROJECT_NAME": "/var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/tmp291k_c_n/.claude/projects/outro-projeto/state",
  "CEO_AUDIT_LOG_DIR": "/var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/tmp291k_c_n/.claude/projects/ceo-orchestration/state"
 },
 "injection_salt(dir do salt)": {
  "sem-env": "/var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/tmp291k_c_n/.claude/projects/ceo-orchestration/.salt",
  "CLAUDE_PROJECT_DIR": "/var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/tmp291k_c_n/.claude/projects/ceo-orchestration/.salt",
  "CEO_STATE_ROOT": "/var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/tmp291k_c_n/.claude/projects/ceo-orchestration/.salt",
  "CEO_PROJECT_NAME": "/var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/tmp291k_c_n/.claude/projects/ceo-orchestration/.salt",
  "CEO_AUDIT_LOG_DIR": "/var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/tmp291k_c_n/.claude/projects/ceo-orchestration/.salt"
 }
}
```

## US4 — superfícies de entrega (`--surfaces`)
```
templates (34 arquivo(s))
templates/settings/settings.base.json (1 arquivo(s))
dist/ceo-plugin/hooks (167 arquivo(s))
```

## Distribuição por artefato (do censo --json)
| artefato | n |
|---|---|
| test | 235 |
| script | 122 |
| hook | 100 |
| dist | 92 |
| doc | 16 |
| spec | 9 |
| template | 8 |
| ci | 4 |
| installer | 2 |

**Total: 588 | na cura W1: 563**
