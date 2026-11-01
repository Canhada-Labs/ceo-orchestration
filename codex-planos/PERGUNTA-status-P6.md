# P6 — W6f: helpers de PLAN-188, PLAN-183, PLAN-175 e PLAN-191

Branch `tracks/ceo-w6f-pending-plans`; base `4d46f3ca`; 2026-11-01.

**Entrega:** três pacotes stdlib em `hooks/_lib`: preparo de cerimônia com
escopo exato, hashes recalculados e GPG; censo de imports versus entrega
seletiva; resolução de skills relativos/symlinks e cascata consultiva por
complexidade. Orçamento inválido bloqueia a cascata; custo desconhecido
permanece `None`. Nenhuma assinatura, publicação ou chamada de modelo feita.

Os nomes de planos do roteiro não existem. A etapa dos helpers foi registrada
como concluída no PLAN-196; os quatro planos históricos seguem `superseded`,
sem afirmar conclusão do escopo amplo herdado. O censo aponta dois gaps
preexistentes: `scripts/detectors` e `scripts/optimizer`, ainda não entregues
pelo instalador. O censo informa esse resultado, sem produzir sucesso falso.

**Casos:** os três arquivos exigidos executaram integralmente, 55 nodeids.
Exemplos de casos e artefatos acusadores (prefixo `.claude/`):

- `scripts/tests/test_plan188_ceremony_toolkit.py::test_sha256_pins_remeasured_after_content_change`
  e `::test_detached_gpg_signature_validates_real_bytes`: hash e GPG sobre
  bytes históricos SP-042, chave pública em chaveiro temporário isolado.
- `scripts/tests/test_plan183_shipped_path_census.py::test_new_scripts_subpackage_not_shipped_by_top_level_glob`
  e `::test_empty_root_is_unproven`: payload de pacote omitido e fonte ausente.
- `hooks/tests/test_plan175_191_telemetry_and_cascade.py::test_symlink_alias_uses_target_slug`
  e `::test_invalid_budget_blocks_all_tiers`: caminho real e payload bloqueado;
  inclui todas as parametrizações de layouts, orçamento e tiers.

**Mutantes:** 16/16 cerimônia, 10/10 censo e 29/29 discovery/cascata; um
isolado por nodeid. Remoção de guardas de escopo/hash/assinatura, falso
positivo de entrega/raiz vazia, slug inventado, orçamento inválido aceito e
tier incorreto foram detectados por asserções. Restauração por `cp` e
comparação de bytes a cada execução; erros de coleta não contados.

Linhas finais literais dos testes focais e vizinhos diretos:

```text
55 passed, 1 warning in 0.99s
1 failed, 103 passed, 1 skipped in 12.85s
1 passed in 0.59s
```

O único erro de vizinho era o controle de corpus exigindo o índice Git que
não existe na cópia de teste. O mesmo nodeid passou usando o índice real em
somente leitura via `GIT_DIR`; pytest permaneceu no palco. O aviso é um
`SyntaxWarning` preexistente em `architect-bundle-validate.py`; o skip é do
vizinho GPG existente. Os 55 casos novos não tiveram skips.

**Pré-checagem: ok** nos comportamentos medidos. Contagem de `_lib` rederivada
do disco: 76 módulos no topo, 211 arquivos Python recursivos. Palco separado
e temporários em tmpfs, fora de repositório reconhecido pelo Git (o sandbox
cria diretórios `.git` vazios nos pais). Nenhum banco de produção utilizado.

Limitações de ferramenta: `autobahnctl pre-juiz` indisponível; não se afirma
zero órfãs/duplicatas/pitfalls sem medição. `gh` sem autenticação impede ler
comentários remotos; a implementação segue o roteiro local do CEO.

Roteiro removido após execução. Nenhuma outra fatia liberada nesta pista;
commit local para revisão e integração pelo CEO, sem push ou abertura de PR.
