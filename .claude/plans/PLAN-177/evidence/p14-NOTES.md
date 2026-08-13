# PLAN-177 W0.1 (P1-4) — decisões de implementação e desvios

**v2 — os 7 ajustes do consenso do debate estão aplicados.** Mapa item a item
abaixo, seguido das decisões originais que sobreviveram.

## Os 7 ajustes

1. **CF-1 — shape antes de valor, INVALID nunca INFRA.** Nos dois arquivos:
   `is None` → `<absent>`; `not isinstance(str)` → `<non-string:dict>` /
   `<non-string:list>`; só então o compare. Nenhum `str()` coercivo (a v1 usava
   `str(...)` no validador — foi removido). Teste dedicado
   `test_a_malformed_decision_is_invalid_never_infra` percorre vazio, ausente e
   duplicado e assere `returncode == 3`, `!= EXIT_INFRA_ERROR` e ausência de
   `Traceback`. A distinção importa porque `release.yml` roteia INFRA por
   `CEO_PAIR_RAIL_VERDICT_OPTIONAL` — um malformado saindo pela porta de infra
   seria dispensável por uma variável de repositório.
2. **CF-2 — chave `verdict:` duplicada.** `count_top_level_key` (validador) /
   `_count_top_level_key` (guard) contam ocorrências top-level DENTRO do bloco
   ```yaml selecionado, com a MESMA seleção de bloco e a MESMA regra de
   comentário do parser respectivo — contar sobre outro texto que não o do
   parse seria contar outra coisa. `> 1` ⇒ INVALID(3)/E_DECISION(13) com
   diagnóstico próprio. `== 0` cai no check de valor e sai como `<absent>`
   (mesma família de mensagem, um só caminho de erro). Prova crua no
   `REPRO.md` §1: pré-cura, `NO-GO` seguido de `GO` retorna OK/0.
   - Efeito colateral necessário: o validador passou a ler o texto UMA vez
     (`parse_verdict_text`) e o guard guarda `verdict_text` — a contagem lê os
     mesmos bytes do parse. `parse_verdict_file(path)` continua existindo como
     wrapper (é o entry point publicado; a suíte morta `.github/scripts/tests/`
     ainda o chama).
3. **CF-3 — assimetria declarada nos DOIS arquivos** (bloco de comentário
   citando `release.yml:689`, `continue-on-error: ${{ vars.CEO_PAIR_RAIL_
   VERDICT_OPTIONAL == '1' }}` — verificado no arquivo vivo). Assert estrutural
   novo `test_gate_step_invokes_the_guard_delta_mode` **dentro da classe
   `W1BReleaseGateDeltaAncestryTest`** (não criei segundo lugar de verdade;
   reusa `_step_block` e `_GUARD_MODULE` da classe). Não assertei "step 15 TEM
   continue-on-error": isso pinaria o hatch como obrigatório e ficaria vermelho
   no dia em que alguém o remover — que é uma melhoria.
4. **CF-4 — exit codes DERIVADOS.** `test_module_exit_codes_are_distinct_
   nonzero` agora monta a tabela de `vars(self.mod)` filtrando `E_*` int:
   não-zero, distintos, `len >= 12`, e `E_DECISION` presente. Substitui a lista
   à mão que apodreceu (omitia `E_PARENT_NOT_ANCESTOR=12`). **Isto revoga o
   desvio D-1 da v1**: não acrescento mais códigos à mão.
5. **Tupla literalmente idêntica** nos dois arquivos:
   `ACCEPTED_DECISIONS = ("GO", "GO-WITH-CONDITIONS")`.
   `test_the_two_rails_share_one_closed_set_of_decisions` importa os dois
   módulos, compara as tuplas, pina o texto renderizado do conjunto e assere
   que `NO-GO`/`no-go`/`go`/`GO `/vazio/`MAYBE` estão fora.
6. **Mensagem com conjunto + valor entre aspas**, mesmo formato nos dois rails:
   `decision 'go' not in {GO, GO-WITH-CONDITIONS}`. Caso vermelho novo
   `template-literal`: o literal `GO | NO-GO | GO-WITH-CONDITIONS` de
   `pair-rail-verdict-template.md:13` — o envelope copiado do template sem
   preencher o campo.
7. **Asserts ancorados em string distintiva do stderr**, não só returncode:
   `_DECISION_REFUSED` (`not in {GO, GO-WITH-CONDITIONS}`, comum aos dois
   rails), `_CI_DUPLICATE_DIAGNOSTIC`, `_GUARD_DUPLICATE_DIAGNOSTIC`, mais o
   assert de que o valor OBSERVADO aparece entre aspas. O docstring de
   `_run_ci_validator` nomeia a variante `--parent-sha ""` como **teste de
   UNIDADE do validador** — naquele modo o step tem `continue-on-error`, então
   quem barra é o guard.

**Higiene:** `tmp_path` em tudo; fixture `ci_env` (por-teste, via `_env()`,
`os.environ` nunca mutado) para os subprocessos do validador; nenhum marker
novo (só `parametrize`); suíte verde também sob `-n 4`. Não fiz o fixture
`autouse`: nada aqui escreve em `os.environ` — que é a classe que o autouse
protege — e um autouse no arquivo inteiro aplicaria o env a testes que já têm
o seu. O cache `_VALIDATOR_INPUTS_HASH_CACHE` é por worker e função pura do
checkout, portanto seguro sob xdist (comprovado).

## Fatos verificados por mim (recon + consenso)

- Argv do step-15: `release.yml:726-735`, job `release-gate`.
  `continue-on-error` do step: `release.yml:689`.
- `release.sh` não muda: `tag()` já faz `python3 "$TAG_GUARD" delta ... || die`
  (:630-631), RC e stable.
- **Nenhum dos dois arquivos é canonical-guarded**: `_CANONICAL_GUARDS` cobre
  `.github/workflows/*.yml` e `.claude/scripts/{lessons,prune-lessons,
  lesson-restore,lesson_ranker}.py`, mas não `.github/scripts/*.py` nem
  `.claude/scripts/local/*`. W0 é superfície livre, sem cerimônia.
- **R-1 confirmado:** o validador ESTÁ em `pair-rail-inputs-hash-manifest.txt`
  ⇒ a cura muda o `inputs_hash` do step-15; o envelope da rc.4 tem de declarar
  o hash novo. `_release_tag_guard.py` está fora do manifesto.
- O `release.yml` vivo carrega `PLAN-166 W1-B`, então a classe W1B roda em CI
  (não skipa) — o assert CF-3 é real, não decorativo.

## Decisões de projeto mantidas da v1

- Gate PRIMEIRO entre as checagens de campo no validador: um `NO-GO` é
  reportado como `NO-GO`, nunca como mismatch downstream.
- Igualdade exata, sem normalização (classe substring-vs-exact, 3× na S299).
- Conjunto duplicado nos dois rails de propósito — processos separados, em
  máquinas separadas, nenhum pode virar dependência do outro; o teste do item 5
  é o gate contra o drift entre as cópias.
- `E_DECISION = 13`, modo próprio. Semântica NÃO unificada com o
  `OWNER-GA-CUT.sh` (outra superfície, mais estrita) — as duas coexistem.
- Fixture auto-consistente (codex P2-2): `inputs_hash` recomputado em runtime;
  pins derivados dos arquivos vivos, nada de hex hardcoded.
- Assert do caso verde distingue "gate" de "fixture": primeiro que o
  diagnóstico da decisão está AUSENTE, depois `returncode == 0` com mensagem
  dizendo que falha aqui é drift de fixture, não o gate sob teste.
- Testes em `.claude/scripts/tests/`, nunca em `.github/scripts/tests/` (suíte
  morta, R-3).
- Os testes não escrevem na árvore do repo: o envelope do validador vive em
  `tmp_path`; só o `cwd` é o repo (necessário para `git hash-object`).

## Desvios em aberto

- **D-1 (v1) REVOGADO** pelo CF-4: a lista à mão virou derivação.
- **D-2 — mais casos vermelhos do que os 3 pedidos originalmente:** 8 valores
  (inclui vazio, `go`, `no-go`, `GO WITH CONDITIONS`, literal do template) +
  duplicata. Custo ~0 (o gate corta antes do recompute de hash) e fecham
  case-folding, substring-vs-exact e last-wins explicitamente.

## O que NÃO fiz (fora do escopo desta task)

- Nada de P1-1 / P1-2 / P1-3 / T-1.
- Não wirei `.github/scripts/tests/` (R-3, trem v1.4.0). **Atenção:** aquela
  suíte morta chama `parse_verdict_file` — mantive o wrapper justamente por
  isso, mas ela NÃO cobre `parse_verdict_text` nem a contagem de chave.
- Não re-pinei `PLAN-169/staged-w3/.claude/governance/gate-scripts-manifest.txt`
  (R-2): os DOIS arquivos curados estão pinados lá por sha256 e os dois
  mudaram. **O pack W3 exige re-pin CONSCIENTE antes de assinar** — o LAND
  aplica com `cp` cego, então um re-pin cego regrediria esta cura.

## Contagem

- `p14-validators.patch`: +181/−14 (validador do CI +102/−13; tag guard
  +79/−1).
- `p14-tests.patch`: +362/−13 (`test_release_bump_sites.py` +314/−4;
  `test_release_workflow_asserts.py` +48/−9).
- `git apply --check` dos DOIS patches contra o repo canônico: OK.
