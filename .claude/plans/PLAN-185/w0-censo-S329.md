# PLAN-185 W0 — censo da CLASSE, 4ª passada (REGRA INVERTIDA)

> **Sessão:** S329 · **Data:** 2026-08-26 · **Escopo:** read-only sobre o alvo.
> Nenhum arquivo fora do FILE ASSIGNMENT foi editado.
>
> **Instrumento:** `.claude/scripts/check-installer-write-safety.py` (2.737 linhas)
> **Baseline:** `.claude/scripts/data/installer-write-safety-baseline.txt` (144 entradas)
> **Oráculo:** `.claude/scripts/tests/test_check_installer_write_safety.py` (1.155 linhas, 68 testes)
>
> **O que esta passada é.** A decisão do Owner de 2026-08-25 (`PLAN-185` §4,
> verbatim: «4ª passada INVERTIDA + W1/W2 em pacote») autoriza reescrever o
> matcher com a regra invertida: enumerar as formas **PROVADAS seguras**, cada
> uma com controle positivo, e classificar todo o resto como `indeterminado`.
> Este documento registra a reescrita, os números que ela produz, a prova de
> cada forma da allowlist e o mapa achado→fixture.
>
> Todo número abaixo veio da EXECUÇÃO do instrumento. O comando está ao lado.
> Nenhum veio de `grep`.

---

## 1. Por que a arquitetura mudou, e não só as regras

As passadas 1–3 funcionavam por **denylist implícita**: o matcher enumerava as
formas que sabia reconhecer e creditava `guardado`/`nao-aplicavel` a tudo que
não casava. Cada rodada de revisão achava mais uma forma não enumerada —
**8 → 7 → 9 → 10 → 16 achados**, todos de uma classe só: *"forma que o parser
não modela sai segura"*. Classe que regenera rodada após rodada não é cauda de
casos de borda; é a arquitetura (PROTOCOL anti-padrão 6,
[[feedback-fix-of-fix-means-change-the-cure-architecture]]).

A inversão tem duas consequências estruturais, e as duas são deliberadas.

### 1.1 A análise de alcançabilidade sumiu — e a pergunta dela estava errada

O matcher antigo gastava ~600 linhas (`reaches_write_on_dangling`,
`same_line_reach`, `flow_is_cut`, `branch_of_write`, `guard_aborts`,
`MAX_WRITE_CANDIDATES`) perguntando *"a escrita é alcançável quando o link
está pendente?"*, e respondia `nao-aplicavel` sempre que não conseguia decidir.

**Essa pergunta nunca decidiu segurança.** O threat model do próprio
`PLAN-185` W1 cobre os DOIS casos — o link **pendente** (`-e` falso, o ramo
"ainda não existe" é tomado, o `cp` CRIA fora do target) e o link
**resolvido** (`-e` verdadeiro, o `cp` escreve ATRAVÉS dele, sobrescrevendo
fora do target). O check da W1 diz isso literalmente: *"fixture com symlink
RESOLVIDO para fora ⇒ mesma recusa"*. Logo o ramo que um link pendente
por acaso toma é irrelevante: **os dois ramos são perigosos**.

Daí a regra nova: um argumento sobre fluxo de controle só pode tornar um
sítio MAIS perigoso, nunca seguro — então nenhum argumento desse tipo pode
produzir veredito não-bloqueante. Segurança vem de uma guarda `-L` que DOMINA
a escrita, ou de não haver escrita nenhuma. Mais nada.

Isso mata de uma vez, por construção e não por remendo, **onze** dos achados
do rail: cap de candidatos, negação em nível de comando (`! [`), negação por
`test`, jump aninhado, escritas na mesma linha, prefixos de comando, e a
família toda de "o ramo não é alcançável".

### 1.2 O parse é fail-closed

A análise roda sobre um lexer de shell de verdade (aspas, `$( )`, `${ }`,
crases, heredocs, continuação de linha, `[[ ]]`, `((...))`, substituição de
processo, literais de array) e uma **pilha de escopos** onde cada braço de
`if`, cada arm de `case`, cada corpo de laço, função e grupo é um id distinto.
Dominância deixa de ser indentação e passa a ser *"o caminho de escopo de G é
prefixo do de W, e G vem antes"*.

Se qualquer coisa não fecha — aspas, heredoc, pilha de blocos, arquivo
ilegível, `.sh` que é symlink — o arquivo INTEIRO é inutilizável: emite um
sítio `parse` bloqueante e todo sítio nele é `indeterminado`.

---

## 2. Totais

```
python3 .claude/scripts/check-installer-write-safety.py --json
```

| Métrica | 4ª passada (S329) | 3ª passada (S326) |
|---|---|---|
| Arquivos varridos (`scripts/**/*.sh` − `scripts/tests/`) | **21** | 21 |
| Sítios totais | **341** | 273 |
| — `symlink-follow` | 281 | 269 |
| — `sed-interp` | 60 | 4 |
| **`desguardado`** | **68** | 12 |
| **`indeterminado`** | **76** | 15 |
| **BLOQUEANTES** | **144** | 27 |
| `guardado` | 8 | 3 |
| `nao-aplicavel` | 189 | 243 |

Dois arquivos não produzem sítio nenhum e isso é correto — não têm teste de
existência nem editor de fluxo: `scripts/local/historical/plan-093-kernel-override-restart.sh`
e `.../plan-093-ship-v1.26.0.sh`.

Matriz classe × veredito:

| Classe | `desguardado` | `indeterminado` | `guardado` | `nao-aplicavel` |
|---|---|---|---|---|
| `symlink-follow` | **62** | **75** | 7 | 137 |
| `sed-interp` | **6** | **1** | 1 | 52 |

Bloqueantes por arquivo: `upgrade.sh` **63**, `install.sh` **37**,
`_codex_harness.sh` 11, `OWNER-CEREMONY-S82-V1120.sh` 6, `uninstall.sh` 5,
`_grok_harness.sh` 4, `doctor.sh` 4, `_framework_manifest_set.sh` 3,
`OWNER-CEREMONY-PLAN-094-WAVE-A.sh` 3, `install-npm.sh` 2,
`trading-readonly-escape-hatch.sh` 2, e 1 cada em `codex-exec-wrapper.sh`,
`smoke-install-parity.sh`, `measure-repo-size.sh`, `publish-plugin.sh`.

**A subida de 27 → 144 é o resultado correto, não uma regressão.** É o que a
§7-quater da S326 previu e aceitou por escrito: as formas antes creditadas em
silêncio agora aparecem. O que MUDOU de natureza é o significado de
`nao-aplicavel`: antes era *"não consegui provar que a escrita é alcançável"*;
agora é *"PROVEI que nada escreve este caminho"*, com a prova nomeada.

### 2.1 O instrumento continua discriminando

Um censo que bloqueasse tudo passaria em todo controle positivo e não serviria
para nada (o anti-padrão "regra ruidosa treina o time a ignorar o canal"). Ele
não bloqueia tudo: **189 sítios saem `nao-aplicavel` com prova nomeada e 8
saem `guardado`** — 58% do corpus é liberado por teorema, não por omissão.
`TestLiveCorpus::test_the_corpus_still_proves_some_sites_safe` guarda esse
piso.

---

## 3. A allowlist — cada forma e a sua prova

`python3 .claude/scripts/check-installer-write-safety.py --rules` imprime esta
lista. Cada id tem controle positivo (guarda intacta ⇒ não-bloqueante, com o
id da forma) e mutação (guarda removida/enfraquecida/renomeada ⇒ bloqueante,
NOMEANDO o path plantado).

| Forma | O que prova | Uso vivo | Teste do controle positivo |
|---|---|---|---|
| `a1-nofollow-test-dominates` | Um teste `-L`/`-h` no MESMO caminho cujo ramo tomado aborta **no nível do próprio ramo**, em linha lógica anterior cujo escopo é prefixo do escopo de toda escrita. | 5 | `TestFormA1NofollowTestDominates::test_guard_present_is_proven_safe` |
| `a2-nofollow-helper-dominates` | Chamada a helper **definido no mesmo arquivo** cujo CORPO satisfaz a1 para `$1` e cujo ramo de symlink retorna literal NÃO-ZERO, chamado como `helper <path> \|\| <abort>`. O nome nunca é evidência. | 2 | `TestFormA2NofollowHelperDominates::test_real_helper_is_proven_safe` |
| `a3-no-write-to-operand` | Toda ocorrência do caminho testado (e dos seus aliases de um nível) está em posição provada não-escrevente. UMA ocorrência que o modelo não situa anula a prova. | 137 | `TestFormA3NoWriteToOperand::test_no_write_is_proven_not_assumed` |
| `b1-delimiter-escape-dominates` | TODA atribuição à variável interpolada escapa o delimitador **desta** substituição (mais `&` e `\` do lado de replacement) com replacement que de fato insere barra invertida, e pelo menos uma domina o uso. | 0 | `TestFormB1DelimiterEscapeDominates::test_real_escape_is_proven_safe` |
| `b2-closed-charset-validated` | Validação dominante que aborta salvo se o valor casa classe fechada literal excluindo delimitador, `&`, `\` e newline. Duas formas: `[[ =~ ^[...]+$ ]] \|\| die` e `case ... in *[!...]*) die ;; esac`. | 0 | `TestFormB2ClosedCharsetValidated::{test_case_validation,test_regex_validation}_is_proven_safe` |
| `b3-literal-only` | Toda atribuição à variável é literal livre de delimitador, `&` e `\`. | 0 | `TestFormB3LiteralOnly::test_safe_literal_is_proven_safe` |
| `b4-inline-escape-substitution` | A interpolação é UMA substituição de comando que escapa o delimitador desta substituição em linha. | 1 | `TestFormB4InlineEscapeSubstitution::test_inline_escape_is_proven_safe` |
| `n0-no-interpolation` | O script do editor é literal e nenhuma substituição carrega expansão. Distingue o `$` do próprio `sed` (endereço de última linha, dentro de aspas simples) de `$VAR` do shell. | 52 | `TestFormN0NoInterpolation::{test_literal_script,test_sed_dollar_inside_single_quotes}_...` |

`b1`, `b2` e `b3` têm **zero** uso vivo hoje — são exatamente as formas que a
W2 vai introduzir como cura de F2. Estão modeladas de antemão para que a cura
aterrisse `guardado` e o baseline encolha mecanicamente, sem editar o
instrumento junto com o produto.

Razões de `indeterminado` (`--rules` também as lista):
`i-parse-failed`, `i-file-unreadable`, `i-unmodeled-occurrence`,
`i-guard-not-dominating`, `i-script-not-literal`, `i-script-unparsed`,
`i-command-substitution`, `i-awk-program-interpolated`, `i-escape-unproven`.

Distribuição real: `i-unmodeled-occurrence` **73**, `i-guard-not-dominating`
**2**, `i-script-not-literal` **1**. Zero `i-parse-failed` — os 21 arquivos do
corpus parseiam.

---

## 4. Os sítios que o plano nomeia

Todos continuam encontrados, e todos saem **`desguardado`** (provado
perigoso), não `indeterminado`:

| Sítio (linha VIVA) | Classe | Veredito | Função | Nota |
|---|---|---|---|---|
| `install.sh:1506` | A | desguardado | `install_docs_template` | ramo dry-run do F1 |
| `install.sh:1514` | A | desguardado | `install_docs_template` | **F1 reportado** (era `:1466`) |
| `install.sh:1621` | A | desguardado | `install_github_templates` | |
| `install.sh:1626` | A | desguardado | `install_github_templates` | |
| `install.sh:1635` | B | desguardado | `install_github_templates` | sonda do CODEOWNERS |
| `install.sh:1643` | B | desguardado | `install_github_templates` | **F2 reportado** (era `:1508`) |

**As linhas do plano DERIVARAM** — `PLAN-185` §1 cita `:1466` e `:1508`; a
árvore viva tem `:1514` e `:1643`. Números derivados por execução, não
copiados do plano.

Classe B `desguardado`, todos os seis:

```
scripts/_grok_harness.sh:112   $PH_PROJECT_PATH cru no replacement de s|...|
scripts/install.sh:1635        $GITHUB_OWNER    cru no replacement de s/.../
scripts/install.sh:1643        $GITHUB_OWNER    cru no replacement de s/.../
scripts/measure-repo-size.sh:39 $REPO_DIR       cru no replacement de s|...|
scripts/upgrade.sh:3726        $_utg_handle     cru no replacement de s/.../
scripts/upgrade.sh:4488        $_UP_GH_OWNER    cru no replacement de s/.../
```

Dois desses são achados do rail que a 3ª passada NÃO via, e a razão de cada um
está na §5: `_grok_harness.sh:112` (continuação de linha) e `upgrade.sh:3726`
(o `sed` vive dentro de `$( ... )`).

---

## 5. Mapa achado → fixture

**36 achados cobertos por 22 fixtures**, agrupados por FORMA. Ids: `Q*` =
`PLAN-185/w0-censo-S326.md` §7-quater; `M*` =
`PLAN-183/w5-ceremony/rail-materials-round-1.md`; `N*` = rodadas 1–5 do rail
do main na S328.

| Forma | Achados | Fixture (`TestRailRegressions::…`) | Como a inversão fecha |
|---|---|---|---|
| Cap de escritas candidatas | Q1, M2, N5, N16 | `test_write_candidate_cap_is_gone` | Não existe cap: a prova é "nenhuma escrita na região", que truncamento não satisfaz. |
| Negação em nível de comando `! [` | N2 | `test_command_level_negation_with_brackets` | Não há mais análise de ramo; a escrita existe ⇒ bloqueia. |
| Negação por `! test -e` | Q2, M5, N8 | `test_negated_test_command_form` | idem. |
| Jump aninhado | Q3, M6, N9 | `test_nested_jump_is_not_an_unconditional_abort` | Abort só conta no nível do PRÓPRIO ramo. |
| Dominância da guarda | Q4, M7, N10 | `test_guard_must_dominate_the_write` | Pilha de escopos: prefixo estrito. Sai `i-guard-not-dominating`. |
| Dominância cruzando função | *(achado meu, ao curar Q4)* | `test_guard_does_not_dominate_across_a_function_boundary` | Guarda no topo tem escopo `()`, prefixo de TUDO. Corpos de função não rodam em ordem de fonte. |
| Helper creditado pelo NOME | Q5, M8, N3, N11 | `test_name_alone_is_never_evidence`, `test_helper_whose_refusal_is_ignored_is_not_a_guard` | O corpo é inspecionado; o regex de nome sumiu. |
| `sed` com continuação de linha | Q6, M1, N4 | `test_sed_with_a_line_continuation_is_seen` | Linhas lógicas são montadas antes do lex. |
| Escritas na mesma linha | M3, N6 | `test_every_same_line_write_is_evaluated` | Todas as escritas entram no conjunto. |
| Prefixos de comando | M4, N7 | `test_command_prefix_before_a_writer`, `test_unmodelled_prefix_option_blocks` | Prefixos modelados com aridade EXPLÍCITA; opção desconhecida ⇒ comando desconhecido. |
| Replacement `&` cru no escape | Q7, M9, N12 | `TestFormB1…::test_noop_replacement_is_not_an_escape` | O replacement precisa inserir barra invertida. |
| Delimitador POR substituição | Q8, M10, N13 | `test_delimiter_is_bound_to_its_own_substitution` | Cada interpolação é provada contra a SUA `Subst`. |
| Escape só num RAMO | Q9, M11, N14 | `test_escape_on_only_one_branch_is_not_reaching` | Exige que TODAS as atribuições escapem e uma domine. |
| Baseline sem a entrada viva de `upgrade.sh` | N1, N15 | `test_sed_inside_a_command_substitution_is_seen` + `TestLiveCorpus::test_the_upgrade_sed_site_is_recorded` | **Causa raiz achada:** o `sed` está dentro de `$( ... )`, e nenhuma passada descia ali. O instrumento agora extrai comandos de substituição recursivamente. |

**Nada ficou de fora.** Os únicos achados das rodadas do rail que não viram
fixture aqui são os que não são sobre este instrumento (`check_contamination.py`,
`profile-opus-4-7.py`, `check_ledger_checkpoint.py`, `OWNER-S328-MORNING.sh`,
`settings.json`, `audit_emit.py`) — fora do FILE ASSIGNMENT desta unidade.

### 5.1 Achados NOVOS, encontrados pela auto-revisão adversarial (Pass 2)

Reler o instrumento novo procurando caminhos "forma não modelada ⇒ não
bloqueia" devolveu **nove**, todos curados com controle
(`TestPassTwoSelfReview`, e dois dentro de `TestFormA*`):

1. **`quoted` matava o índice de atribuições.** `esc="$( … )"` tem segmento
   entre aspas, e a condição exigia `not cmd.toks[0].quoted` — então
   `fm.assigns` vivia praticamente VAZIO, e as provas `b1`/`b3` e a análise de
   alias nunca disparavam. Pego pelo controle positivo de b1, que foi vermelho
   até a cura.
2. **Dominância cruzando fronteira de função** (na tabela acima).
3. **`sed --in-place`** não casava o padrão de flag curta ⇒ editor que
   reescreve o operando saía leitura. → `test_sed_long_in_place_flag_is_a_write`.
4. **`find` com primária que age** (`-delete`, `-exec`, …) estava em
   `KNOWN_READONLY`. → `test_find_with_an_acting_primary_is_not_read_only`
   (+ controle negativo com `-print`).
5. **`awk` estava em `KNOWN_READONLY`**, testado ANTES do ramo de editor, então
   `awk -i inplace` nunca chegava ao código que o chamaria de escritor.
6. **`perl`/`ruby` sem `-i` saíam leitura** — um one-liner escreve o que quiser.
   Agora caem em `unknown`, que bloqueia.
7. **Guarda `-L` conjugada por `&&` dentro de `[[ ]]`.**
   `[[ -f "$d" && -L "$d" ]] && return 1` recusa um symlink que TAMBÉM é
   arquivo regular e deixa passar um PENDENTE — a forma exata que este censo
   existe para pegar. → `test_conjoined_nofollow_test_is_not_a_guard`
   (+ controle negativo com `||`, que é inclusivo e continua valendo).
8. **Só o primeiro script `-e` era julgado.** `sed -e A -e B` roda os dois. →
   `test_a_raw_interpolation_in_a_second_e_script_is_judged`.
9. **`.sh` que é symlink era pulado em silêncio** na descoberta — um buraco do
   tamanho de um `ln -s`. Agora emite sítio bloqueante. →
   `test_a_symlinked_shell_file_blocks_instead_of_being_skipped`.

Mais dois defeitos de instrumento (não fail-open, mas fatais para um gate):

10. **Colisão de fingerprint.** Sítios byte-idênticos em funções diferentes
    colapsavam numa entrada de baseline, então um QUARTO defeito idêntico
    casaria entrada existente e o gate ficaria verde. Curado com função
    enclosante + ordinal no payload. → `test_identical_sites_get_distinct_fingerprints`.
11. **Saída não-determinística.** `alias_set` devolve `set`, e iterar cru fazia
    o sítio REPORTADO variar entre execuções sob randomização de hash. Curado
    com ordenação; verificado com 5 execuções e um único sha256.

---

## 6. Baseline

144 entradas, formato `path:line:class:verdict:form-or-reason:fingerprint`,
casamento por `(path, class, fingerprint)`; a linha é informativa e é
atualizada a cada run (drift de linha é reportado, nunca fatal).

```
python3 .claude/scripts/check-installer-write-safety.py --write-baseline
```

Contratos que o oráculo prende:

- **Contagem 0 REPROVA com exit 2**, e o cheque de zero roda ANTES de
  `--write-baseline`, senão gravar-se-ia um baseline vazio abençoando o estado
  quebrado (`test_zero_sites_fails_with_exit_2`).
- **Sítio bloqueante novo ⇒ exit 1**, nomeando o path
  (`test_a_new_blocking_site_fails_with_exit_1`).
- **Entrada morta ⇒ exit 1** (rot; `test_a_dead_baseline_entry_fails`).
- **Linha malformada ⇒ exit 1.** Uma linha que o loader não lê não isenta nada
  e não reporta nada; engoli-la deixaria um baseline corrompido parecer sadio
  (`test_a_malformed_baseline_row_fails_the_gate`).
- **`--write-baseline` nunca roda implicitamente**
  (`test_baseline_is_never_regenerated_implicitly`).
- **`--strict` não deixa o baseline isentar `indeterminado`** — sob `--strict`
  as 76 indeterminações bloqueiam mesmo registradas
  (`test_strict_does_not_let_the_baseline_waive_indeterminate`).

Estar no baseline significa que **um humano OLHOU** aquele sítio. NÃO significa
que a forma é segura: `indeterminado` é "o matcher não consegue provar
segurança", que é o default fail-closed da regra invertida.

---

## 7. Wiring de CI — a linha que a cerimônia deve acrescentar

**Não fiz este wiring:** `.github/workflows/validate.yml` é canônico e está
fora do meu FILE ASSIGNMENT. Registro a linha para quem tiver a assinatura.

`validate.yml` não tem filtro `paths:` (roda em todo `pull_request` e todo
`push` para `main`), então não há a armadilha de "gate que a mudança não
dispara" que a S325 encontrou no `smoke-install.yml`. Passo a acrescentar no
job `validate`, seguindo a convenção dos vizinhos:

```yaml
      # PLAN-185 W0 AC-3 — censo da CLASSE de escrita insegura do installer.
      # Exit 1 = sitio bloqueante NOVO, entrada de baseline morta, ou linha
      # de baseline malformada; exit 2 = contagem ZERO, que REPROVA por
      # desenho (padrao de busca quebrado, nao repo limpo).
      - name: Run check-installer-write-safety.py (PLAN-185 W0)
        run: |
          python3 .claude/scripts/check-installer-write-safety.py
```

Sem `|| true`, sem `continue-on-error` — fail-closed nos dois códigos.

**A invocação é a de ratchet, NÃO `--strict`.** Isso é deliberado e é OQ-1
abaixo: `--strict` hoje sai `rc=1` com 76 indeterminações, ou seja, um gate
`--strict` nasceria vermelho e ninguém conseguiria mergear. O ratchet trava o
conjunto atual e falha em qualquer sítio novo — que é o que a AC-3 pede
("falha se um sítio desguardado novo aparecer"). `--strict` é o estado-alvo
depois que W1/W2 e a triagem dos 76 reduzirem o conjunto.

---

## 8. Comandos executados

| Comando | Resultado |
|---|---|
| `python3 .claude/scripts/check-installer-write-safety.py` | exit **0** — 341 sítios, 144 bloqueantes, todos no baseline |
| `python3 .claude/scripts/check-installer-write-safety.py --json` | exit **0** — payload válido |
| `python3 .claude/scripts/check-installer-write-safety.py --rules` | exit **0** — 8 formas da allowlist + 9 razões de indeterminado |
| `python3 .claude/scripts/check-installer-write-safety.py --strict` | exit **1** — 76 indeterminados bloqueiam (esperado; ver OQ-1) |
| `python3 .claude/scripts/check-installer-write-safety.py --write-baseline` | exit **0** — 144 entradas (invocação EXPLÍCITA, sobre censo não-vazio) |
| `python3 -m pytest .claude/scripts/tests/test_check_installer_write_safety.py -q -p no:cacheprovider` | **68 passed** |
| `python3 .claude/scripts/check-test-env-hygiene.py` | exit **0** — *"337 flagged files, all allowlisted"*; o arquivo de teste NÃO está no allowlist (limpo, não herdado), e o allowlist não foi tocado |
| `python3 -m py_compile .claude/scripts/check-installer-write-safety.py` | exit **0** |
| 5× `--json \| shasum -a 256` | **um único hash** — saída byte-estável |

### 8.1 O verde do env-hygiene tem controle positivo

`CensusCase` e `TestLiveCorpus` herdam de `TestEnvContext`
(`.claude/hooks/_lib/testing.py`), não de `unittest.TestCase` — isolamento de
`HOME`, `CLAUDE_PROJECT_DIR`, env e `sys.path`, que aqui não é opcional: toda
asserção invoca o censo por subprocesso, e uma variável vazada deixaria o teste
ler ou escrever estado da sessão real. As demais 12 classes herdam de
`CensusCase`.

Guarda verde só é evidência se ela VÊ o alvo
([[feedback-guard-green-because-files-are-untracked]]), então o verde foi
provado por controle positivo em vez de afirmado:

| Passo | Resultado |
|---|---|
| guard sobre a árvore como entregue | `rc=0` — *"337 flagged files, all allowlisted"* |
| planta `class _PlantedBareCase(unittest.TestCase)` no fim do arquivo | `rc=1`, *"NEW violations: 1"*, nomeando `…/test_check_installer_write_safety.py:1158: bare-testcase` |
| restaura do backup em scratchpad (`cmp` byte-idêntico) | `rc=0` de novo |

O allowlist (`.claude/scripts/test-env-hygiene-allowlist.yaml`) **não foi
tocado** — `git status` sobre ele sai vazio. A cura é estrutural, não isenção.

**Gates de corpus NÃO rodados, e por quê.** `verify-counts.sh` e a bateria
completa ficaram fora por instrução explícita da unidade ("não rode suítes
longas do repo inteiro"). Além disso, `verify-counts.sh` invoca
`pytest --collect-only`, que a S326 mediu escrevendo **124 elos
não-atribuíveis por run** na cadeia HMAC viva. Quem for commitar estes
arquivos precisa rodar a bateria de corpus DEPOIS da última edição e ANTES do
commit, na ordem do `CLAUDE.md` §4 (`git add -A` → gates sobre a árvore
staged → `git commit`).

---

## 9. Limites declarados

Cada um destes é uma fronteira do modelo, não um descuido. Onde o limite
morde, o veredito é `indeterminado` (bloqueia) — nunca um "seguro" silencioso.

1. **Alias de UM nível.** `alias_set` propaga em ambas as direções uma vez, sem
   fecho transitivo. `a="$dst"; b="$a"; > "$b"` não é seguido a partir de
   `$dst`. Duas atribuições encadeadas passam despercebidas.
2. **Interprocedural de UM nível.** Um helper local que repassa o parâmetro a
   OUTRO helper local aparece como ocorrência desconhecida dentro do callee e
   propaga como `unknown` (bloqueia). Callee que usa `$@`, `$*` ou `shift`
   quebra o mapeamento posição→parâmetro e vira `unknown`.
3. **Corpos de `$( … )` não têm fluxo de controle modelado.** Comandos ali
   contribuem ocorrências de escrita/leitura/desconhecido e sítios de classe B,
   mas TESTES ali dentro **não** são registrados: não viram sítio de classe A e
   nunca são creditados como guarda. Creditar guarda num subshell cujo fluxo não
   modelo seria fail-open; enumerar sítio ali produziria veredito calculado com
   escopo que não é o real. Escrita dentro de `$( )` continua envenenando a
   prova do operando de fora, que é a direção que importa.
4. **`awk -v var="$X"` sai `n0`.** O PROGRAMA é literal e o valor entra como
   dado, não como texto de programa — é a forma correta de passar valor ao awk.
   Fica declarado que `-v` processa sequências de escape, então uma barra
   invertida no valor é uma superfície ESTREITA e de outra classe (injeção em
   programa awk), fora do escopo de `sed-interp`.
5. **`sudo` e `xargs` são sempre `unknown`.** Modelar a aridade de opções deles
   seria adivinhar; adivinhar é o que esta passada remove.
6. **`mkdir`/`rmdir` são declarados benignos** para a classe A: `mkdir -p` num
   link pendente falha e num link resolvido para diretório é no-op — não
   escreve ATRAVÉS. `rm`/`unlink` removem o LINK, não o alvo, exceto com barra
   final no operando, caso em que são tratados como escrita.
7. **Escopo de região.** É o corpo da função quando a variável é `local` ali; o
   arquivo inteiro caso contrário. Uma global com o mesmo nome usada em duas
   funções é analisada sobre o arquivo todo (mais bloqueio, direção segura).
8. **O corpus inclui `scripts/local/historical/`.** São scripts de cerimônia
   antigos, e 9 dos 144 bloqueantes vêm dali. Não os excluí porque exclusão de
   escopo é decisão de dono, não de instrumento — ver OQ-2.

---

## 10. Open questions para o Owner

Nenhuma bloqueou esta unidade; em todas segui a opção conservadora
(fail-closed), como a unidade manda.

**OQ-1 — `--strict` no CI, quando?** A linha proposta na §7 é o ratchet. Um
gate `--strict` hoje sai vermelho (76 indeterminados). Opções: (a) landar o
ratchet agora e abrir `--strict` como item da wave seguinte, depois de W1/W2
reduzirem o conjunto; (b) landar `--strict` já e triar os 76 antes. Segui (a)
por ser a única que pode mergear no dia. *Decisão do Owner.*

**OQ-2 — `scripts/local/historical/` entra no corpus?** 9 dos 144 bloqueantes
são scripts de cerimônia históricos que ninguém executa mais. Mantê-los infla
o baseline; excluí-los é um recorte de escopo que só o dono pode autorizar
(e a S325 já pagou por "mover artefato para fora do gate cria verde falso" —
[[feedback-moving-a-file-out-of-a-gate-creates-false-green]]). Mantive TODOS.
*Decisão do Owner.*

**OQ-3 — os 73 `i-unmodeled-occurrence` são triagem de quem?** São sítios cujo
caminho testado chega a um comando que o modelo não cobre (`python3`, `gpg`,
`git` com subcomando de escrita, `tar`, `npm`). Cada um é uma decisão humana
de "isto escreve o caminho ou não". Como cada resposta vira ou uma entrada em
`KNOWN_READONLY` ou um escritor modelado, a triagem MELHORA o instrumento de
forma permanente. Não a fiz: 73 julgamentos sobre `scripts/*.sh` canônicos são
material de wave, não de unidade de censo. *Decisão do Owner sobre onde alocar.*

---

## 11. O que a W1/W2 herda

- Os sítios de F1 e F2 estão no censo, **bloqueantes e provados perigosos**
  (`desguardado`, não `indeterminado`) — a cura pode ser verificada
  mecanicamente: uma guarda compartilhada que aborte flipa o veredito para
  `a2-nofollow-helper-dominates` e a entrada sai do baseline.
- **F1 não tem um sítio, tem vários.** `install.sh` sozinho tem 37
  bloqueantes; curar só o `:1514` deixa as cópias vivas. A forma
  `a2-nofollow-helper-dominates` já está modelada e testada, então a cura por
  função COMPARTILHADA que a W1 `[P1]` exige aterrissa `guardado` sem tocar o
  instrumento.
- **F2 tem seis sítios de interpolação crua**, não um — incluindo dois em
  `upgrade.sh` que o plano não conhecia. As formas `b2-closed-charset-validated`
  (validação contra conjunto fechado) e `b1`/`b3` já estão modeladas: a cura
  que a W2 `[P0]` descreve — "valor validado contra um conjunto fechado de
  caracteres de handle antes de qualquer escrita" — sai `guardado` por `b2`
  assim que existir.

---

## 12. 5ª passada — descoberta fail-closed (S329)

A 4ª passada inverteu a regra do **veredito**. A 5ª rodada do pair-rail sobre
`843eb57` devolveu **15 P1 + 1 P2, todos da mesma classe outra vez**. Ler os 16
como uma lista de defeitos seria o erro: inverter o veredito fechou metade do
problema, e a metade aberta é a que importa mais.

**A DESCOBERTA continuava sendo denylist.** Um sítio só nascia onde
`_scan_tests` reconhecia um operador de teste, ou onde um nome nu `sed`/`awk`
aparecia. Consequência: `test -a "$dst"`, `/usr/bin/sed`, `$1`, `>& "$dst"` e
`sort -o "$dst"` não produziam veredito frouxo — **não produziam sítio
NENHUM**. Um sítio invisível é pior que um mal-absolvido: no mal-absolvido a
linha aparece no relatório com um veredito discutível; no invisível não há
linha, e a contagem global de zero sítios (o guard que existe para detectar
busca quebrada) continua passando porque OUTROS arquivos produziram sítios.

Esta passada torna a descoberta fail-closed. A regra tem uma frase:

> Um comando só é PULADO se o seu nome está na allowlist de PROVADOS
> somente-leitura **e** ele não abre nenhum arquivo para escrita. Todo o resto
> cujos operandos ou redireções contenham QUALQUER expansão é um **candidato a
> escrita** (`write-candidate`), que precisa ser provado seguro como qualquer
> outro sítio.

### 12.1 A allowlist de somente-leitura, com a razão de cada entrada

Vinte e cinco nomes. O critério de admissão é único e falsificável: *nenhuma
opção deste comando transforma um operando de caminho em destino*. Quando não
consegui afirmar isso, o nome ficou de fora — "provavelmente não escreve" é
exatamente a afirmação sem prova que esta passada parou de fazer.

| Nome | Razão |
|---|---|
| `[`, `[[`, `test` | Avaliam predicados; não têm modo de saída. |
| `echo`, `printf` | Escrevem só em stdout. Uma redireção anexa é destino e é tratada separadamente. (`printf -v` liga uma VARIÁVEL — registrado no índice de rebind, não é escrita de caminho.) |
| `true`, `false`, `:` | Não usam operandos. |
| `return`, `break`, `continue`, `exit` | Controle de fluxo. |
| `basename`, `dirname` | Transformações de string puras, stdout. |
| `grep`, `egrep`, `fgrep` | Nenhuma opção do POSIX ou do GNU nomeia arquivo de saída (`-o` é *only-matching*). |
| `local`, `declare`, `typeset`, `export`, `readonly` | Ligam variáveis. **Com** substituição de comando no valor saem da allowlist: os comandos de dentro são varridos à parte, e o custo de ser conservador aqui é um sítio. |
| `read` | Lê de stdin para variáveis. Registra rebind (crítico para R5-06). |
| `shift` | Move posicionais. Registra rebind de `$1..$9`, `$@`, `$*`. |
| `unset` | Remove ligação de variável. |
| `cd`, `pwd` | Mudam/imprimem diretório de trabalho. |
| `umask` | Recebe um modo, nunca um caminho. |

**Saíram da lista da 4ª passada, e por quê.** Três porque a afirmação era
FALSA (rail R5-08): `sort -o FILE`, `uniq IN OUT` e `yq -i FILE` escrevem um
operando. Uns quarenta porque a afirmação, provavelmente verdadeira, não tinha
prova: `cat`, `head`, `tail`, `wc`, `cut`, `tr`, `nl`, `find`, `stat`, `file`,
`ls`, `du`, `df`, `realpath`, `readlink`, `jq`, `date`, `seq`, `diff`, `cmp`,
`comm`, `join`, `paste`, `od`, `xxd`, `shasum`, `md5sum`, `column`, `fold`,
`getopt`, `printenv`, `tput`, `uname`, `id`, `whoami`, `hostname`, `sleep`,
`expr`, `wait`, `set`, `shopt`, `trap`, `hash`, `type`, `source`, `.`, `eval`.
E `die`, `log`, `info`, `warn`, `note`, `err`, `error`, `usage`, `help`,
`version` por uma terceira razão: **são funções locais deste corpus**, e
creditá-las pelo NOME é a evidência-por-vocabulário que a forma `a2` existe
para recusar.

Não saíram por regra de nome, mas por **evidência ciente de opção** (a cura
que o R5-08 pede): `sort`, `uniq`, `yq`, `jq`, `tee`, `tar`, `curl`, `wget`,
`gpg`, `openssl`, `patch`, `split`, `csplit`, `zip`, `unzip`, mais os
escritores já modelados (`cp`, `mv`, `install`, `ln`, `rsync`, `touch`,
`truncate`, `chmod`, `chown`, `chgrp`, `mkdir`, `dd`). Para cada um, a opção de
destino é dado, não folclore; uma opção não modelada torna o comando
DESCONHECIDO em vez de somente-leitura. O controle negativo está no teste
`test_r5_08_sort_without_an_output_option_still_reads`: `sort "$dst"` sem `-o`
continua provadamente seguro, o que impede a regra de degenerar em "bloqueie
tudo".

**Formas que também viraram sítio, nunca omissão:** uma expressão de teste que
o modelo não consegue percorrer até o fim (`i-unmodeled-test-form`);
`eval`/`source`/`.`/`exec` (`i-opaque-command`); um arquivo que não fecha
aspas, heredoc ou blocos (`i-parse-failed`); um `.sh` que é symlink
(`i-file-unreadable`).

### 12.2 Evidência ligada à operação exata

| Regra | O que mudou |
|---|---|
| Identidade do comando | `Command.pos` + `fm.line_cmds`: a lista de comandos de cada linha lógica é construída UMA vez e endereçada por índice. Antes cada consumidor re-splitava a linha, `c is t.cmd` nunca casava, e o fallback por texto de operando creditava o primeiro comando que MENCIONASSE o caminho (R5-05). |
| Polaridade | `!` interno aos colchetes conta como negação (`has_negation`), `-a` legado e `&&` contam como conjunção (`has_conjunction`). Guarda com qualquer um dos dois não prova nada. `||`/`-o` continuam válidos: a disjunção aborta para TODO symlink (R5-04). |
| Definições alcançantes | `rebound_between()`: qualquer religação do nome entre a guarda e a escrita invalida a prova — atribuição, `local`/`export`, `read`, variável de `for`/`select`, `getopts`, `printf -v`, `shift` para posicionais (R5-06). |
| Ligação do abort | `_inline_abort_after` exige adjacência (`pos+1`) e `_is_abort_command` inspeciona o CORPO de `die`/`_die`/`fatal` quando são funções locais; se não estiverem definidas no arquivo, não são abort. Em b2 o abort tem de pertencer ao PRÓPRIO comando de validação, não a qualquer `\|\| die` posterior na linha (R5-15). |
| Variável exata | `_regex_validation_matches` compara TOKENS: o operando à esquerda de `=~` tem de ser o token exato. O teste por substring fazia uma validação de `$value` cobrir `$v` (R5-13). |
| Ancoragem | `_RE_ANCHORED_CLASS` exige `^` **e** `$`. Com `^` opcional, `[[ "$v" =~ [A-Za-z]+$ ]]` absolvia `\|safe`, que ainda carrega o delimitador (R5-14). |
| Escape real do sed | `_repl_emits_backslash`: só `\\&` emite barra invertida antes do casamento. `\&` produz um `&` LITERAL — escapa nada (R5-11). |
| b4 produtor único | `_sole_pipeline_producer` exige que a substituição seja exatamente um `$( … )`, que o corpo seja um único pipeline e que o último estágio seja o `sed` de escape. `$(printf … \| sed 'safe'; printf %s "$raw")` deixa de ser aceito (R5-12). |
| b3 alcançante | Além de "toda atribuição é literal segura", exige que UMA delas domine o uso e que não haja rebind na região. Antes, `v=safe` DEPOIS do uso provava o uso (R5-10). |
| Redireção `>&` | Operando numérico (ou `-`) é dup de descritor; qualquer outro é arquivo (R5-07). |
| Valor de opção anexado | Opção é decidida pelo texto CANÔNICO, e `--target-directory="$dst"` tem o valor extraído como destino. Antes o token inteiro contava como aspado, virava posicional, e a FONTE virava destino (R5-09). |
| Nome com caminho | `command_basename()`: `/usr/bin/sed` é `sed`; `"$CP"` (nome que é expansão) é DESCONHECIDO, nunca pulado (R5-02). |
| Modelo de expansão | `_RE_EXPANSION` cobre `${…}` em qualquer forma, `$1..$9`, `${10}`, `$@`, `$*`, `$#`, `$?`, `$$`, `$!`, `$-`, `$(…)`, crase, glob e `~` (R5-03). |

### 12.3 Mapa achado → fixture (16/16)

Todos em `TestRailRoundFive`, mais os controles negativos que impedem a cura de
virar "bloqueie tudo".

| Id | Achado | Fixture |
|---|---|---|
| R5-01 | Formas de teste não suportadas não emitiam sítio | `test_r5_01_unsupported_file_test_form_blocks`, `test_r5_01_path_qualified_test_is_a_test`, `test_r5_01_unmodelled_test_operator_is_a_site` (+ controle negativo `test_r5_01_a_redirection_on_a_test_is_not_unmodelled`) |
| R5-02 | Editor de fluxo com caminho qualificado | `test_r5_02_path_qualified_stream_editor_is_judged` |
| R5-03 | Posicionais e parâmetros especiais | `test_r5_03_positional_expansion_is_an_expansion`, `test_r5_03_special_parameters_too`, `test_r5_03_literal_only_proof_sees_positionals` |
| R5-04 | Negação interna aos colchetes | `test_r5_04_bracket_internal_negation_is_not_a_guard`, `test_r5_04_legacy_conjunction_is_not_a_guard` |
| R5-05 | Evidência ligada ao comando errado | `test_r5_05_abort_is_credited_to_its_own_command` |
| R5-06 | Guarda invalidada por reatribuição | `test_r5_06_guard_is_invalidated_by_a_reassignment`, `test_r5_06_a_read_rebinds_too` (+ controle negativo `test_r5_06_without_the_reassignment_the_guard_holds`) |
| R5-07 | `>&` para arquivo | `test_r5_07_redirect_to_a_filename_is_a_write` (+ controle negativo `test_r5_07_numeric_descriptor_is_still_a_dup`) |
| R5-08 | Somente-leitura com modo de saída | `test_r5_08_sort_o_writes_its_operand`, `test_r5_08_uniq_second_operand_writes`, `test_r5_08_yq_in_place_writes` (+ controle negativo `test_r5_08_sort_without_an_output_option_still_reads`) |
| R5-09 | Valor de opção anexado | `test_r5_09_attached_target_directory_is_the_destination` |
| R5-10 | b3 sem atribuição alcançante | `test_r5_10_b3_needs_a_reaching_assignment` |
| R5-11 | `\&` tratado como escape | `test_r5_11_backslash_ampersand_is_not_an_escape` |
| R5-12 | b4 com produtor extra | `test_r5_12_b4_requires_the_sole_producer` |
| R5-13 | Validação casada por substring | `test_r5_13_validation_must_name_the_exact_variable` |
| R5-14 | Validação sem âncora inicial | `test_r5_14_validation_must_be_start_anchored` |
| R5-15 | Abort não ligado à validação | `test_r5_15_abort_must_be_bound_to_the_validation` (+ controle negativo `test_r5_15_a_bound_abort_is_still_a_proof`) |
| R5-16 | Arquivos sem sítio não apareciam | `test_r5_16_every_discovered_file_is_listed`, `test_r5_16_the_file_list_reaches_the_text_output_too` |

**Controle nos dois sentidos, medido.** Trocando o instrumento pela versão de
`843eb57` e rodando só as classes novas: **31 failed, 9 passed**. Os 31 são
todos os fixtures R5 e de descoberta; os 9 que passam são exatamente os
controles NEGATIVOS, que têm de ficar verdes nas duas versões. Contra o
instrumento desta passada: **111 passed**.

### 12.4 Baseline novo

```
python3 .claude/scripts/check-installer-write-safety.py --write-baseline
# wrote 613 blocking entries
```

| classe | desguardado | indeterminado | guardado | nao-aplicavel | total |
|---|---|---|---|---|---|
| `symlink-follow` | 64 | 102 | 7 | 108 | 281 |
| `sed-interp` | 6 | 1 | 1 | 52 | 60 |
| `write-candidate` | 150 | 290 | 18 | 0 | 458 |
| **total** | **220** | **393** | **26** | **160** | **799** |

De 341 sítios / 144 bloqueantes para **799 / 613**, sobre 21 arquivos e 15.449
linhas. O aumento é a medida da cura, não um efeito colateral dela: 458 dos
sítios novos são `write-candidate`, a classe que não existia — escritas que
nenhum teste apontava e que, por isso, não tinham sítio nenhum.

**O que a linha no baseline significa, dito honestamente.** É uma entrada de
CATRACA: o sítio é conhecido, e nenhum NOVO pode aparecer sem decisão. **Não**
é revisão humana por sítio — são 613, e afirmar que cada um foi lido seria
falso. O cabeçalho do arquivo foi reescrito para dizer isso; a redação
anterior ("uma linha aqui significa que um humano OLHOU") era verdadeira com
144 entradas e deixou de ser. Transformar sítios reais em `guardado` é o
trabalho da W1/W2, e a contagem CAINDO é como esse trabalho aparece aqui.

### 12.5 Expectativas anteriores que mudaram

Duas, ambas porque o censo passou a enxergar MAIS:

1. `test_identical_sites_get_distinct_fingerprints` esperava 3 bloqueantes;
   agora são **6** (3 `symlink-follow` + 3 `write-candidate`), porque cada `cp`
   é candidato por direito próprio. A afirmação que o teste existe para fazer —
   fingerprints distintos — foi reforçada, não relaxada: agora são 6 distintos,
   e há asserção por classe.
2. O helper `Census.at()` ganhou parâmetro `cls`. Quando uma asserção não nomeia
   classe e há empate, ele prefere a classe ESPECÍFICA (`symlink-follow` /
   `sed-interp`), porque essa era a pergunta que a asserção antiga fazia. A
   classe nova tem asserções próprias em `TestFailClosedDiscovery`. Nenhuma
   expectativa foi afrouxada — nenhum `assertBlocks` virou `assertSafe`.

### 12.6 Auto-auditoria (passe 2): todo ramo que ainda absolve

Nove vereditos não-bloqueantes e quatro saídas sem sítio. Para cada um, a
cadeia de evidência:

| Ramo | Cadeia de evidência |
|---|---|
| `a3-no-write-to-operand` | Toda ocorrência do caminho e dos seus aliases de um nível, na região, é teste, leitura, argumento de comando PROVADO somente-leitura, ou operando-fonte de escritor modelado. **Uma** ocorrência que o modelo não consiga colocar anula a prova (`i-unmodeled-occurrence`, 99 sítios no corpus vivo). |
| `a1` (classe A e C) | Teste `-L`/`-h` no mesmo caminho, sem negação e sem conjunção internas, cujo ramo aborta no NÍVEL do próprio ramo, dominando por prefixo estrito de escopo **dentro da mesma função**, sem religação do valor entre guarda e escrita. |
| `a2` | Idem, com o corpo do helper inspecionado: o ramo do symlink tem de sair com status não-zero literal, e o call-site tem de abortar quando o helper recusa. |
| `n0` (awk) | O programa awk não contém nenhuma expansão que o SHELL faça (decidido no token cru: aspas simples não expandem). |
| `n0` (sed) | Toda expansão do shell foi coberta por alguma substituição modelada, e nenhuma delas tem expansão dentro. Sobra não coberta ⇒ `i-script-unparsed`. |
| `b1` | Toda atribuição ao nome escapa ESTE delimitador (+ `&` e barra do lado do replacement) com replacement que realmente emite barra, uma delas domina o uso, e não há rebind na região. |
| `b2` | Validação por classe fechada, ancorada nas duas pontas, casada por token exato, com abort ligado ao próprio comando, dominando o uso, sem rebind entre os dois. |
| `b3` | Toda atribuição é literal livre de delimitador/`&`/barra **e** uma delas domina o uso **e** não há rebind. |
| `b4` | A interpolação é exatamente um `$( … )`, o corpo é um único pipeline, e o último estágio é um `sed` cuja classe cobre este delimitador com replacement que emite barra. |
| *(sem sítio)* definição de função | `_RE_FUNC_DEF` casa e `{`/`}` agora separam comandos, então o CORPO é analisado como comandos próprios. Corpo em subshell (`f() ( … )`) não fecha a pilha de blocos ⇒ `i-parse-failed`, verificado. |
| *(sem sítio)* cabeçalho `for`/`select`/`case` | É lista de PALAVRAS, não comando. Substituições dentro dela já foram lexadas em `fm.subst_commands` e são analisadas. |
| *(sem sítio)* somente-leitura provado | Nome na allowlist de §12.1 e nenhuma redireção de saída. |
| *(sem sítio)* nenhuma expansão | Único estreitamento da descoberta, e é o do modelo de ameaça do PLAN-185: um destino totalmente literal é escolhido pelo script, não por quem opera o installer. |

**Um furo achado por esta auto-auditoria e curado.** `mkdir`/`rmdir` estavam
declarados benignos porque "não escrevem ATRAVÉS de um link". Isso vale para o
componente FINAL apenas: `mkdir -p "$dst/sub"` resolve `$dst` e cria `sub` do
outro lado dele — exatamente a fuga que este censo existe para achar. A sonda
devolveu **NENHUM SÍTIO** para essa linha. `mkdir` virou escritor; `rmdir`
passou para a regra de operando de `rm` (perigoso só com barra final). Fixtures
`test_mkdir_p_writes_through_a_symlinked_component`,
`test_a_guarded_mkdir_is_still_proven_safe`,
`test_rmdir_is_decided_by_the_operand_not_the_name`.

**Um segundo furo, achado pelo controle POSITIVO e não pelo rail.** Ao sondar
R5-13/14/15 os três saíam `b3-literal-only` — passavam pelo motivo errado.
Causa: `_RE_HAS_EXPANSION` ainda era `\$[A-Za-z_{(]|\``, que não reconhece `$1`,
então `local v="$1"` era lido como LITERAL SEGURO e um valor controlado pelo
chamador era provado seguro por b3. É o R5-03 sobrevivendo dentro da prova b3
depois de a descoberta ter sido curada. Agora `_RE_HAS_EXPANSION` **é**
`_RE_EXPANSION`. Fixture `test_r5_03_literal_only_proof_sees_positionals`.

### 12.7 Residual — o que continua fora do parser, e como aparece

Tudo abaixo aparece como `indeterminado` (bloqueia) ou como `i-parse-failed`
para o arquivo inteiro. Nenhum vira ausência.

- **Aliases de um nível só.** `alias_set` propaga constantes em uma profundidade.
  Uma cadeia `a=$b; b=$c; c=$1` não é seguida; as ocorrências intermediárias
  viram `i-unmodeled-occurrence`.
- **Interprocedural de profundidade um.** Um callee que passa o parâmetro a
  outra função devolve `unknown`, que propaga.
- **`git` por subcomando.** `_GIT_READONLY_SUBCMDS` é uma lista de nomes com a
  mesma forma de afirmação que esta passada retirou de `cat` e companhia. A
  afirmação é mais estreita (nenhum desses subcomandos escreve um operando de
  CAMINHO) mas não tem controle positivo. **Dívida declarada.**
- **Globs.** `rm -rf "$dst"/*` tem canon terminando em `*`, não em `/`, então a
  regra de barra final de `_LINK_LOCAL_DELETE` não dispara. Vira candidato
  porque `rm` não é somente-leitura provado, mas o veredito não é `desguardado`.
- **`sed` com comando `w FILE` no script.** `parse_sed_script` recusa (`r/R/w/W`
  não são modelados) ⇒ `i-script-unparsed`. Coberto, mas pela porta do parser
  de sed e não pela de escritores.
- **Escopo do corpus.** Só `scripts/**/*.sh`, excluindo `scripts/tests/`. Um
  script sem extensão `.sh` não é varrido. `rglob` pode ou não seguir
  diretórios symlinkados conforme a versão do Python; `.sh` que SEJA symlink é
  reportado (`i-file-unreadable`).
- **`--strict` é vermelho por desenho, e vai continuar.** Ele pergunta "existe
  algum sítio não provado?" e a resposta honesta hoje é 393. O enunciado da
  unidade pedia `--strict` rc 0; isso só seria possível relaxando a semântica
  do flag, que é o oposto do que esta passada faz. O que a catraca precisa está
  provado no modo PADRÃO: rc 0 contra o baseline regenerado, rc 1 nomeando o
  path quando uma linha é removida. `--strict` é o medidor de progresso da
  W1/W2.

### 12.8 Comandos executados

```
python3 -m pytest .claude/scripts/tests/test_check_installer_write_safety.py \
    -q -p no:cacheprovider                              # 111 passed
python3 .claude/scripts/check-test-env-hygiene.py       # rc 0
python3 .claude/scripts/check-installer-write-safety.py --write-baseline
python3 .claude/scripts/check-installer-write-safety.py # rc 0
python3 .claude/scripts/check-installer-write-safety.py --strict
                                                        # rc 1, 393 indeterminados
# controle negativo da catraca
grep -vxF 'scripts/install.sh:220:write-candidate:indeterminado:i-write-candidate-unproven:3b166865e8f44649' \
    .claude/scripts/data/installer-write-safety-baseline.txt > /tmp/b && \
    mv /tmp/b .claude/scripts/data/installer-write-safety-baseline.txt
python3 .claude/scripts/check-installer-write-safety.py # rc 1, nomeia install.sh:220
# (baseline restaurado; rc volta a 0)
```
