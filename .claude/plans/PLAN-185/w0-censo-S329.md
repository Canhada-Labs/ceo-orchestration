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
