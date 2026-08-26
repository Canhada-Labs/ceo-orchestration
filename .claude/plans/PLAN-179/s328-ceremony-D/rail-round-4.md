# Pair-rail — PACOTE D, rodada 4 (achados vindos do rail do MAIN)

**Origem diferente das rodadas 1-3:** estes três achados não vieram de uma
rodada minha sobre o pack, e sim do **pair-rail do `main`** (rodada 2,
`<scratchpad>/railmain-2.txt`), repassados pelo team-lead. Ou seja: um rail
que estava olhando OUTRA árvore, com outro escopo, encontrou coisas nos meus
arquivos. Tratados como CLAIMS a verificar, nunca como ordens.

**Resultado:** 1 refutado (stale), 2 confirmados e **CURADOS**.
Rail-Verdict: REJECT

> O veredito segue REJECT porque os dois bloqueantes fora do meu grant
> (`CHANGELOG.md` e `test_template_dogfood_parity.py`) continuam abertos —
> nada nesta rodada os fecha. Ver o §Estado no fim.

---

## [P1] "Match the test expectation to the staged ledger state" — **REFUTADO (stale)**

> `test_check_ledger_checkpoint.py:570` — a fixture cria um ledger mas
> stageia só `notes.md`, então o hook emite `ledger_missing`, não
> `ledger_updated`. A asserção falha deterministicamente e o land não passa.

**A ANÁLISE está certa; o ESTADO do arquivo, não.** O rail do main leu uma
versão anterior do arquivo — este é exatamente o defeito que eu já tinha
encontrado e corrigido horas antes, na mesma sessão. O que está no disco AGORA:

```python
        # The discriminating value: `ledger_missing` means the ledger was
        # FOUND on disk and simply not updated by this commit.
        # `ledger_absent_from_plan` is the BUG's signature — it is what you
        # get when the lookup happened under the subdirectory.
        self.assertEqual(
            recorded[0]["outcome"], "ledger_missing",
```

E o caso `ledger_updated` ganhou teste PRÓPRIO
(`test_ledger_staged_from_a_subdirectory_reads_as_updated`), que stageia o
`LEDGER.md` — as duas metades cobertas, em vez de uma asserção ambígua.

**Prova:** `pytest test_check_ledger_checkpoint.py` = **65 passed**, e a
suíte dos dois arquivos do pack = **132 passed** em clone fresco. Nenhuma
falha determinística.

**Disposição: pushback.** Nada a curar. Registro a lição, que é sobre
instrumentos e não sobre este bug: **um rail que lê uma árvore diferente da
que está sendo curada devolve achados com data de validade.** O achado não é
ruído — a análise dele estava correta e teria pegado o defeito se eu não
tivesse pego antes.

---

## [P2] "Parse wrapper options before looking for git" — **CONFIRMADO e CURADO**

> `check_ledger_checkpoint.py:470-472` — `env -i FOO=1 git commit`,
> `command -- git commit` e `stdbuf -oL git commit` pulam o token do wrapper
> mas depois tratam a OPÇÃO dele como outro comando, limpando a posição antes
> de chegar ao `git`. Esses commits reais devolvem `is_commit=false` e não
> produzem evento nenhum.

**VERIFICADO — verdadeiro, e é um buraco na MINHA cura da rodada 2.** Eu
consumia o NOME do wrapper e parava aí; a opção seguinte (`-i`, `--`, `-oL`)
caía no ramo genérico e fazia `at_command_position = False`. A cura anterior
restaurou a invariante "todo commit real é observado" para
`GIT_EDITOR=true git commit` e a deixou quebrada para `env -i git commit`.

**CURA:** depois do wrapper, consumir também suas opções e atribuições até o
primeiro token que não seja nenhum dos dois. `env -u NAME` tem tratamento
próprio (leva o valor num token separado); as demais opções da lista curta ou
são booleanas (`-i`, `--`) ou carregam o valor coladas (`-oL`).

**CONTROLE POSITIVO (provado vermelho→verde).** O teste cobre agora 8 formas;
com o parser pré-cura:

```
FAILED TestEnvPrefixedCommitsAreSeen::test_assignment_and_wrapper_prefixes_still_trigger
AssertionError: 0 != 1 : the commit vanished from the observed universe:
env -i FOO=1 git commit -m "feat: work"
```

Com a cura: **65 passed**. O controle inverso segue lá:
`GIT_EDITOR=true echo hello` continua totalmente silencioso.

---

## [P2] "Redirect py_compile output away from the live environment" — **CONFIRMADO e CURADO**

> `OWNER-W179-W24-LAND.sh:462-465` — `PYTHONDONTWRITEBYTECODE` não suprime o
> bytecode produzido explicitamente por `py_compile`. No Linux isso cria
> `__pycache__` na árvore aplicada; no macOS padrão pode escrever no cache
> global do usuário. Nenhum dos dois é preservado pelo `_restore` nem coberto
> pelo fingerprint dele, então um dry-run pode reportar restauração byte a
> byte depois de ter mutado o sistema de arquivos.

**VERIFICADO por medição A/B, e o resultado é pior do que a leitura estática
sugeria.** Duas execuções lado a lado, uma com a env var e outra sem:

```
sys.dont_write_bytecode COM env : True      <-- a env var FUNCIONA
~/Library/Caches/com.apple.python/.../withenv.cpython-39.pyc   <-- e AINDA assim escreveu
~/Library/Caches/com.apple.python/.../noenv.cpython-39.pyc
```

Os DOIS `.pyc` existem. `sys.dont_write_bytecode` é `True` e `py_compile`
grava mesmo assim — a variável governa a escrita do IMPORTADOR, não a
compilação explícita. Neste setup o destino é o cache global do usuário,
**fora do repositório**.

Por que isso derruba uma garantia e não só suja o disco: o `_restore`
anuncia "restaurados byte a byte" com base num fingerprint que é
`git status --porcelain --untracked-files=all` + `git diff HEAD`. Esse
fingerprint **não vê arquivo ignorado e não vê nada fora do repo**. Então a
frase que o `--dry-run` imprime ao Owner era mais forte do que a evidência
que a sustentava — a classe "instrumento verde cuja pergunta é estreita
demais", desta vez no meu próprio script.

**CURA:** o V1 troca `py_compile` pela builtin `compile()`, que responde a
MESMA pergunta (a sintaxe é válida?) e não escreve nada.

**CONTROLE:** `.pyc` no cache global **antes=40, depois=40, delta=0**.

O `py_compile` do G4 fica como está de propósito: aquele roda dentro do clone
descartável, que é apagado no fim, e ali exercitar o caminho real de
compilação tem valor.

---

## Verificação depois destas curas

| comando (clone fresco, pack aplicado) | rc |
|---|---|
| `pytest` dos 2 arquivos de teste do pack | **0** (132 passed) |
| `check-test-env-hygiene.py` | **0** |
| `check-audit-registry-coverage.py --check` | **0** |
| `validate_governance_fast.py` | **0** |
| `validate-governance.sh` (COMPLETO) | **0** |
| `bash -n` + `shellcheck` + `check-ceremony-script.py` nos 3 scripts | **0 BLOCKING** |
| `assemble_pack.py` | 25 entradas, MANIFEST confere, 0 IDENTICAL |

## Estado

Somando as quatro rodadas: **10 achados curados** (8 com controle positivo),
2 pushbacks fundamentados, 4 deferidos com mecanismo escrito, 1 refutado por
staleness, 2 bloqueantes fora do meu FILE ASSIGNMENT.

O `Rail-Verdict` continua **REJECT** e o SIGN vai recusar assinar — o que é o
comportamento correto enquanto `CHANGELOG.md` e
`test_template_dogfood_parity.py` não entrarem no pack.
