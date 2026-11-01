# P6 — Onda 3: implementação local validada; PLAN-195 ainda aberto

`tracks/ceo-w3-monoblocos-audit-emit-boot`, 2026-11-01.

`audit_emit.py` passou de 14.522 para 3.563 linhas. Os emissores e esquemas
foram extraídos por domínio; funções continuam ligadas ao estado da fachada,
preservando monkeypatch, reload e os 247 corpos originais. Despachante e função
exigida por AST ficaram na fachada. Adaptei os seletores de fonte dos consumidores.

PLAN-195 recebeu scanner aditivo limitado, corpos/substituições/lançadores,
aliases, destinos canônicos computados, correção de A3 e dois switches confiáveis
com telemetria deduplicada. O hook legado continua com 4.237 linhas. ADR-201 está
`PROPOSED`; enums, SPEC, índice e contagens foram atualizados por conteúdo.

Casos novos, relativos a `.claude/hooks/tests/` (classes incluem parametrizações):

- `test_audit_emit_modular_facade.py::test_extracted_emitter_uses_facade_write_event`,
  `::test_extracted_emitter_uses_facade_generic_dispatch`,
  `::test_extracted_emitter_uses_facade_private_helper`,
  `::test_reload_keeps_extracted_emitters_bound_to_current_facade`.
- `test_check_bash_safety_indirect_exec.py::{TestIndirectDestructiveBlocks,TestIndirectLegitAllow,TestIndirectParseLimits,TestReadRefusalMessage,TestIndirectSwitchAndHookPayload}`;
  `test_check_bash_safety_canonical_matrix.py::TestComputedCanonicalTarget`.
- `test_bash_indirect_telemetry.py::TestBashIndirectTelemetry`: payload JSONL,
  deduplicação entre processos/sessões, dois switches, entrada desconhecida,
  falha de armazenamento e sessão ausente.

Mutantes: guard **65/65**, fachada **5/5**, telemetria **6/6** mortos por falha
de asserção. Cada mutação foi isolada e restaurada com `cp`/`cmp`; nenhuma
falha de coleta foi contada. O teste de profundidade foi fortalecido para
não deixar o teto de tamanho mascarar a remoção do teto de profundidade.

Linhas finais literais (palcos sem `.git`, temporários em RAM):

```text
======================== 228 passed, 1 xfailed in 0.84s ========================
================= 921 passed, 5 xfailed, 24 warnings in 24.03s =================
270 passed, 3 xfailed, 1 warning in 0.58s
4 passed in 0.14s
```

O lote conjunto inclui auditoria, `ceo-boot`, todos os `test_check_bash_safety*`,
telemetria e consumidores diretos. Os 270 casos foram repetidos depois do ajuste
final do teste de profundidade. Higiene de ambiente, AST Python 3.9, índice,
claims e `verify-counts.sh --no-tests` passaram. Não executei a suíte inteira.

Espelhos `dist`/`npm` conferidos por `cmp`. `npm-rebuild.sh` termina em código 3:
o npm local devolve JSON indexado pelo nome do pacote, formato não aceito pelo
parser existente. A validação direta do JSON provou 1.946 arquivos, igualdade
`entryCount == len(files)`, teto de 6.000 respeitado e ausência de `.claude/plans`.

**pré-checagem: pendente** — `autobahnctl pre-juiz --delta --json` indisponível
(`command not found`); não afirmo zero órfãs/duplicatas/pitfalls. Comentários de
PR não acessíveis: `gh` sem autenticação. Não abri PR nem publiquei alterações.

**Bloqueio do fechamento:** faltam rascunho externo ADR-201, vocabulário privado
A9/V-1, replay diferencial, medições/decisões P-4/P-5/OQ-10 e gates de revisão,
assinatura e sandbox previstos no plano. Solicitei os caminhos desses materiais.
Proposta: CEO disponibiliza os insumos privados e revisa esta implementação;
PLAN-195 permanece `executing`, sem conclusão ou autorização de LAND simulada.
