# Curas do round 1 do pair-rail — 2026-08-19

Os 9 achados foram tratados. Nenhum foi descartado como "não se aplica".

| # | achado | cura | prova |
|---|---|---|---|
| P1 | `upgrade.sh` nunca registra o hook novo | 6ª cláusula `_reg` no merge de lifecycle + loop do dry-run + textos de saída | **controle negativo**: no script NÃO-corrigido o achado reproduz (0 registros); com o pack, 1. Idempotência provada com `cmp` byte-a-byte entre run 1 e run 2. Adopter customizado preserva chave própria e hook próprio. |
| P2 | histerese de pressão global | marcador por SESSÃO, id vindo do input do hook (nunca de env), whitelist ASCII explícita + fallback sha256, temp path também por sessão | duas sessões não se suprimem; id hostil não escapa de `.claude/state/` nem colide |
| P2 | `gc_orphan_session_stores()` sem chamador | chamador de produção fail-open, com teto por execução | GC remove os arquivos; falha de GC não altera o `snapshot_outcome` |
| P2 | `event_source` não-hashável levanta `TypeError` | type-check antes do `in frozenset`, no formato dos branches irmãos | list/dict não levanta e cai no sentinel seguro |
| P2 | 12 violações do `check-test-env-hygiene` | `mock.patch.dict` + herança da base de isolamento | 12 → 0, e o teste que prova a RECUSA do id vindo de env continua setando a variável e continua asserindo a recusa |
| P2 | guia do adopter dizia "staged, não rodando" e prometia HALT | reescrito para o que ship: observa e notifica; o PreCompact não tem canal de deny | — |
| P2 | SPEC v2.56 declarava `constraint_count` ausente | linha corrigida no artefato do pack (`spec-v1-audit-log.schema.md`) | 43 linhas de versão parseadas, máx v2.56 > v2.55 |
| P3 | implicação de *throughput* num comentário | linguagem operacional neutra | — |

## Verificação pós-cura (feita por mim, não delegada)

Clone limpo + pack de 32 paths aplicado pelo manifesto honrando o `PACKMAP`:

| gate | resultado |
|---|---|
| `py_compile` (7 módulos) | OK |
| `settings.json` parseia | OK |
| `bash -n` + `shellcheck` do `upgrade.sh` | OK |
| `check-test-env-hygiene.py` | OK |
| manifesto de gate-scripts | OK |
| `validate-governance.sh` | PASS |
| `verify-counts.sh` | OK |
| `check-claude-md-claims.py` | OK |
| suíte completa de hooks | **7112 passed, 1 failed** |

**A única falha é ambiental e foi provada como tal:**
`test_live_audit_isolation::test_subprocess_write_event_cannot_reach_live_even_with_carriers_unset`
tira um snapshot do audit log VIVO e exige que ele não mude durante o teste.
Minha própria sessão escreve nesse log a cada tool call, então rodar a suíte
enquanto trabalho o derruba. **Isolado: 16 passed, 1 skipped, rc=0.** É a mesma
família que flakou na noite anterior, em outro teste dela.

## Bônus: um vermelho no VIVO que ninguém tinha visto

A mesma verificação pegou que o land do W3-K (`c34e8e3`) deixou um
`bare-testcase` que o `check-test-env-hygiene.py` reprova. Passou porque o job
`Validate` daquele commit foi **cancelado** por um push superseder — o gate
nunca falou. Curado em `9179ef2`.
