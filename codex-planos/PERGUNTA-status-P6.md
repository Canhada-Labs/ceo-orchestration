# P6 — Devolução W6a: três achados P1/P2 corrigidos

Branch: `tracks/ceo-w6a-audit-fixes`; base `bdb99699`; 2026-11-01.

**Delivery:** os pacotes `_audit_query`, `_installer_write_safety` e
`_contamination` foram movidos para `hooks/_lib`, entregue recursivamente pelo
instalador. Fachadas, binder, raiz/hash do censo e fixture isolada foram
ajustados. Instalação limpa `--profile core`: os três CLIs executam `--help`
com código 0, sem PYTHONPATH ou dependência da árvore de origem.

**GuardFall:** limites de palavras/alternativas agora vetam por limite de
análise; ranges respeitam direção e magnitude do passo, inclusive passo zero.
Comentários de shell e substituição de processo entre aspas duplas são dados;
substituições executáveis e here-doc não citado continuam analisados.

**Wiring:** `check_harness_config.main()` chama o classificador de carregamento
raiz. Sem fonte completa, informa `root_load_unobservable`. O snapshot JSON
opcional é identificado como fornecido pelo operador, sem afirmar observação
nativa ou completude autenticada. Pino recursivo de `_lib` rederivado do disco:
203 arquivos Python; dois pontos de `docs/ARCHITECTURE.md` atualizados.

Casos novos (prefixos nodeid; todas as parametrizações foram executadas):

- `.claude/scripts/tests/test_installed_script_packages.py::TestInstalledScriptPackages::test_core_install_runs_split_clis_without_source_tree`.
- `.claude/hooks/tests/test_check_bash_safety_indirect_exec.py::TestReviewW6GuardFallRegressions::test_hook_payload_matches_bash_execution_semantics` e `::test_heredoc_data_expansion_reaches_hook_payload` — 9 casos no JSON do hook/veto.
- `.claude/hooks/tests/test_claude_md_excludes.py::TestRootInstructionRuntimeWiring`: `test_runtime_report_loaded_from_complete_snapshot`, `test_runtime_report_absent_from_complete_snapshot`, `test_runtime_rejects_partial_snapshot_as_proof`, `test_runtime_rejects_invalid_entries_as_proof`, `test_runtime_without_observed_source_is_unobservable`, `test_runtime_malformed_json_is_unobservable` — saída real do CLI.

Mutantes isolados mortos: Delivery **3/3** (uma fachada por vez), GuardFall
**9/9**, wiring **6/6**. Todos falharam por asserção do artefato/payload; fontes
restauradas por `cp` e verificadas por `cmp`, sem contar erro de coleta.

Linhas finais literais, em palcos sem `.git` e temporários em RAM:

```text
492 passed, 1 skipped in 13.34s
860 passed, 1 skipped, 3 xfailed in 24.84s
```

A primeira linha é a base; a segunda inclui os quatro arquivos obrigatórios,
vizinhos diretos e o teste da instalação limpa. Sem suíte inteira.

**Pré-checagem funcional: ok.** Casos medem arquivos entregues, JSON e saída do
CLI; fontes incompletas não viram afirmação de carregamento. Testes com ambiente
isolado; sintaxe Python 3.9 e stdlib verificadas. Não há afirmação de conclusão
global do PLAN-195 nem alteração de produção/main.

**Limitações de ferramenta:** `autobahnctl pre-juiz --delta --json` não está
instalado neste ambiente; não afirmo zero órfãs/duplicatas/pitfalls sem essa
medição. Comentários remotos de PR não puderam ser consultados (`gh` sem
autenticação); os três achados foram tratados a partir do roteiro local.

Nenhuma outra fatia está liberada no roteiro desta pista. Commit local para
revisão e integração pelo CEO, sem push ou abertura de PR.
