# Pair-rail — PACOTE D (PLAN-179 W2+W4), rodada 1

**Instrumento:** `codex exec review --uncommitted` (codex-cli 0.147.0), num clone
`git clone --local` do HEAD `560dad0` com o pack aplicado pelo MANIFESTO
(honrando o `PACKMAP.txt`) **e** os materiais de cerimônia presentes — o rail
revisou o payload e os scripts que o Owner vai rodar, não só o payload.

**Resultado:** `rc=0`, veredito **REJECT** — 5 P1 + 4 P2.
Rail-Verdict: REJECT
**Artefato bruto:** `<scratchpad>/pkgD-rail-1.txt` (5.101 bytes).

Disciplina aplicada a cada achado: **claim → verificar contra o disco → curar
ou pushback escrito**. Nenhum achado foi aceito por autoridade.

---

## P1-1 — `admit_entry` não está ligado a nenhuma escrita de produção

> `ledger_provenance.py:820` — `admit_entry` só é definido e exercitado por
> testes; nenhum escritor ou hook o chama, e o hook novo só observa commits
> via Bash. Um `Edit`/`Write` normal em `PLAN-NNN/LEDGER.md` passa ao largo
> de proveniência, scanner e verificação de deleção.

**VERIFICADO — verdadeiro.** Censo de chamadas no pack e na árvore viva:
`admit_entry` tem zero call-sites de produção. O módulo viaja com testes e
sem consumidor.

**Disposição: PUSHBACK / residual NOMEADO — não curado nesta rodada.**

Ligar um write-gate a escritas de produção **cria uma superfície de
enforcement nova**: exigiria um hook em `Edit`/`Write` com matcher de path,
uma decisão de postura (advisory vs binding) e o seu próprio par
would-block/TP-FP. Isso é uma wave com debate, não uma linha enfiada numa
cerimônia às 3 da manhã — e é exatamente a classe de mudança que o PROTOCOL
manda passar por Plan → Debate → Execute. O achado está CERTO sobre o estado;
está errado sobre o remédio caber aqui.

O residual fica declarado no sentinel: **o módulo de proveniência ship sem
consumidor de produção; a wave que o ligar decide a postura.**

---

## P1-2 — postura padrão devolve a entrada REJEITADA

> `ledger_provenance.py:865-867` — com `CEO_LEDGER_WRITE_GATE_ENFORCE` não
> setado, `binding` é falso e mesmo um veredito `scanner_unavailable`,
> malformado ou com hit devolve a `LedgerEntry` original como admitida.
> Contradiz a regra fail-closed de input.

**VERIFICADO — o comportamento é esse, e é DELIBERADO e documentado.** O
docstring da própria função diz, textualmente: *"In the advisory window (the
shipping default) a reject does not bind: the entry is returned, the verdict
says `would_reject`, and the event is still emitted — that is what makes the
window measurable."*

**Disposição: PUSHBACK fundamentado.**

1. É a forma **measure-first** que este repo já usa e ratificou noutro rail:
   `CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED` está UNSET de propósito, com a mesma
   estrutura (evento emitido, decisão não vinculante, flip futuro gated numa
   janela). Ver `CLAUDE.md §4`, spawn protocol.
2. O chamador **não é enganado**: a função devolve `(entry, verdict)` e
   `verdict.rejected` diz a verdade. Não há veredito escondido.
3. A exposição prática hoje é **zero**, e pelo motivo que o próprio P1-1
   levanta: não existe chamador de produção. Uma postura binding num módulo
   sem consumidor não protegeria nada — só tornaria a janela não-medível.

Residual honesto, e ele é o MESMO do P1-1: **quando a wave de wiring chegar,
ela tem de decidir bind-vs-measure ANTES de ligar o primeiro escritor.** Ligar
o escritor mantendo o default advisory seria aí sim um fail-open real.

---

## P1-3 — eventos de checkpoint sem identidade de sessão — **CURADO**

> `check_ledger_checkpoint.py:1047-1049` — nenhuma das duas emissões passa
> `session_id`, e `_write_event` não sintetiza o campo. Sem ele não dá para
> contar a janela declarada de 20 sessões nem particionar por projeto.

**VERIFICADO — verdadeiro, e o remédio estava a uma linha.** As três
allowlists do `audit_emit.py` **já admitem** `session_id` e `project`
(`_LEDGER_CHECKPOINT_RECORDED_ALLOWLIST:8542`,
`_LEDGER_CHECKPOINT_SKIPPED_ALLOWLIST:8554`,
`_LEDGER_ENTRY_REJECTED_ALLOWLIST:8564`). O esquema estava pronto; só o
chamador não passava.

**CURA:** `_IDENTITY` + `_set_identity(event)` chamado como PRIMEIRA linha de
`gate()`, e `_emit` injeta por `setdefault` — assim um emissor futuro não
consegue esquecer. O id que chega ao registro assinado é **limitado**:
caracteres de identificador apenas, cap de 64.

**`project` NÃO entra, e a razão é local ao módulo:** este rail proíbe path no
wire — invariante que o próprio `test_no_ledger_content_reaches_the_audit_wire`
sustenta afirmando que nenhum valor emitido contém `/` — e a identidade certa
de projeto é o slug do `runtime_paths`, que **não se re-deriva localmente**
(classe M4, fechada pelo PLAN-182). Nada se perde: desde o PLAN-182 W1 o
diretório de auditoria e a chave HMAC já são POR PROJETO, então as linhas são
particionadas por LOCALIZAÇÃO, não por campo.

**Testes novos (5):** id presente em `recorded` e em `skipped`; ausência é um
vazio CONHECIDO (não campo faltando); id sanitizado e limitado; e uma
asserção de ORDEM — `_set_identity` precede o early-return do master-kill, por
leitura do fonte.

---

## P1-4 — escritas diretas em `os.environ` — **CURADO (era bloqueante)**

> `test_check_ledger_checkpoint.py:227` e mais quatro mutam `os.environ`
> direto; `check-test-env-hygiene.py` acusa cinco violações e o V6 do land
> roda esse checker.

**VERIFICADO — e é o achado mais caro da rodada.** Reproduzido no clone com o
pack aplicado:

```
$ python3 .claude/scripts/check-test-env-hygiene.py    → rc=1
  test_check_ledger_checkpoint.py:227: env-write — os.environ[None]
  ...:492  ...:506  ...:519  ...:520
```

As cinco linhas EXATAS que o rail nomeou. O `V6d` do
`OWNER-W179-W24-LAND.sh` roda esse gate, então a cerimônia **abortaria** no
dry-run da manhã.

**CURA:** as cinco viraram `mock.patch.dict(os.environ, {...})`, conforme
`AGENTS.md:24` e `CLAUDE.md §4`. Depois: `check-test-env-hygiene.py` **rc=0**,
e os testes seguem verdes.

---

## P1-5 — leitura truncada certifica deleção que não houve — **CURADO**

> `ledger_provenance.py:937-938` — se uma superfície passa de 1 MiB e o
> marcador está depois do prefixo, `_read_surface` devolve o prefixo como
> leitura BEM-SUCEDIDA e `verify_entry_absent` reporta `verified=True`.

**VERIFICADO — fail-open real, num verificador.** O módulo declara a doutrina
oposta em `DELETION_OUTCOMES`: *"'unreadable' is NOT 'absent': a surface we
could not read has not been verified, and unverified is fail-CLOSED here"*. A
leitura capada violava a própria doutrina. E o teto de tamanho do ledger é
ADVISORY, então nada garante que o arquivo caiba.

**CURA:** lê `cap + 1` bytes; se voltou mais que o cap, o arquivo excede a
janela ⇒ `unreadable`, nunca `present` com prefixo.

**CONTROLE POSITIVO (provado vermelho→verde):** teste novo escreve o marcador
DEPOIS do cap. Com o módulo pré-cura:

```
FAILED test_surface_over_the_read_cap_is_unreadable_not_absent
AssertionError: True is not false : a surface too big to read whole was
certified as verified — that is the fail-open this test exists to catch
```

Com a cura: 67 passed. Um segundo teste fixa a FRONTEIRA (um arquivo que cabe
EXATAMENTE no cap continua sendo leitura completa) — a cura não pode virar um
off-by-one na direção contrária.

---

## P2-1 — deleção staged do ledger conta como `ledger_updated`

> `check_ledger_checkpoint.py:1040-1041` — um ledger staged para DELEÇÃO
> ainda aparece em `git diff --cached --name-only`, então `rel in paths`
> classifica o commit como `ledger_updated` mesmo com `inspect_ledger`
> dizendo que o arquivo não existe. `would_block=0`, sem advisory.

**VERIFICADO — verdadeiro.** O `if rel in paths` tem precedência e nunca
consulta `facts["exists"]`.

**Disposição: ACEITO, DEFERIDO com mecanismo escrito — não curado aqui.**

O remédio correto exige uma decisão de SEMÂNTICA sobre um enum FECHADO que
viaja num schema assinado. As três saídas, com o custo de cada uma:

- **`ledger_deleted` novo** — a mais informativa, e a mais cara: mexe em
  `_OUTCOMES`, no branch de scrub do `audit_emit.py` e numa linha do
  `SPEC/v1` que já está no escopo assinado desta cerimônia (v2.59). Somar
  valor de enum a um schema assinado no meio do land é precisamente o que a
  cerimônia existe para impedir.
- **mapear para `ledger_missing`** — dispara o advisory e põe `would_block=1`,
  fecha o buraco de segurança sem tocar o enum; **mas** muda o que a janela
  conta como "missing", e os números da janela são do dono do plano.
- **deixar cair em `ledger_absent_from_plan`** — natural pela leitura do
  código, e **não resolve nada**: `would_block` continua 0 e o silêncio
  permanece.

Nenhuma das três é uma escolha do agente de cerimônia às vésperas da
assinatura. Fica NOMEADA no sentinel como residual, com este parágrafo como a
análise que a wave seguinte herda. Exposição real hoje: baixa — exige um
commit que delete um `LEDGER.md` staged, e o rail é ADVISORY de qualquer modo.

---

## P2-2 — opções com valor viram pathspec — **CURADO**

> `check_ledger_checkpoint.py:496-498` — `--author Alice` / `--date now`
> pulam só o token da opção, e o VALOR é registrado como pathspec.
> `_committed_paths` devolve `None` e commits válidos saem `unparseable`.

**VERIFICADO — verdadeiro, e o efeito é um VIÉS na medição.** O teste
`test_explicit_pathspecs_are_unparseable` confirma a cadeia: pathspec
explícito ⇒ `unparseable` ⇒ evento de SKIP. Ou seja, todo
`git commit --author X -m msg` sumia do universo OBSERVADO da janela que este
rail existe para medir.

**CURA:** `_COMMIT_VALUE_OPTS_LONG` (12 opções de valor OBRIGATÓRIO) e
`_COMMIT_VALUE_OPTS_SHORT` consomem o token seguinte. Opções de valor
OPCIONAL (`-S`/`--gpg-sign`, `-u`/`--untracked-files`) ficam de fora de
propósito: elas só aceitam valor na forma `=`, e consumir um segundo token
para elas comeria um pathspec real — o erro oposto. A forma `--opt=valor` não
precisa de entrada: é um token só e o branch genérico já a pulava.

**CONTROLE POSITIVO (provado vermelho→verde):** com o parser pré-cura,
`test_value_bearing_options_do_not_become_pathspecs` falha nomeando o comando:
`'unparseable' unexpectedly found in ['unparseable'] : the option VALUE was
read as a pathspec: git commit --author "A U Thor <a@b.invalid>" -m "feat: work"`.
Mais dois testes fecham as bordas: a forma `--author=X` continua funcionando,
e um pathspec REAL continua dando `unparseable` (a cura não pode cegar o hook
para o caso que ele deve pegar).

---

## P2-3 — limiar de morte diverge do ADR — **CURADO**

> Código fixa 30%, ADR-195 §3.2 M1 define M1 como omissão > 33%. Uma taxa
> entre 31% e 33% produz decisões keep/remove OPOSTAS conforme a autoridade
> citada, e o teste só checava 0 < valor < 100.

**VERIFICADO — verdadeiro nos dois lados.** `LEDGER_OMISSION_DEATH_THRESHOLD_PCT = 30`
no hook; `**M1 — omissão > 33% dos commits em escopo.**` no ADR, com
justificativa escrita ("menos de dois terços das fronteiras").

**CURA:** o ADR é a doutrina e o código passou a segui-la — **33**. E a
concordância deixou de depender de vigilância humana: o teste novo **parseia o
ADR-195** (canônico primeiro, staged como fallback) e compara com a constante.

**CONTROLE POSITIVO (provado vermelho→verde):** com o 30 de volta,
`AssertionError: 33 != 30 : ADR-195 M1 says 33% and the code says 30% — a rate
between them decides the ledger's life differently depending on which one the
report quotes`. O teste antigo de faixa foi MANTIDO ao lado — ele responde
outra pergunta (valor sano), e o rail mostrou que ela é insuficiente sozinha.

---

## P2-4 — o harness media a árvore DEPOIS da restauração — **CURADO**

> `test-ceremony-scripts-w24.sh:258-260` — `_run_land t7 G5` faz o
> `_stop_here` sair depois do G5, o que dispara o trap de restauração ANTES
> dos `stat`. O hook novo já foi removido, `NEW_HOOK_MODE` vira `???` e o T7
> falha sempre, mesmo com os modos corretos.

**VERIFICADO — bug do MEU instrumento, não do produto.** A primeira corrida do
harness já tinha registrado exatamente isso: `FAIL T7 modo —
check_ledger_checkpoint.py nasceu ??? (esperado 755)`.

**CURA:** o LAND ganhou um seam de auto-teste — `CEREMONY_SELFTEST_NO_RESTORE`,
honrado **só** sob `CEREMONY_SELFTEST_NO_GPG=1`, que por sua vez só é aceito
em árvore descartável. O harness liga o seam apenas no T7. Fora do auto-teste
os dois são inertes.

Registro honesto: o rail achou no meu instrumento a mesma classe que eu tinha
acabado de achar sozinho. Duas testemunhas independentes do mesmo defeito é o
que o pair-rail existe para produzir.

---

## Resumo da rodada 1

| # | sev | disposição |
|---|---|---|
| P1-1 `admit_entry` sem consumidor | P1 | **pushback** + residual nomeado |
| P1-2 postura advisory devolve rejeitada | P1 | **pushback** fundamentado (measure-first) |
| P1-3 sem `session_id` | P1 | **curado** + 5 testes |
| P1-4 `os.environ` direto | P1 | **curado** (era bloqueante do V6d) |
| P1-5 leitura truncada = verificada | P1 | **curado** + controle positivo |
| P2-1 deleção staged = `ledger_updated` | P2 | **aceito, deferido** com mecanismo escrito |
| P2-2 valor de opção vira pathspec | P2 | **curado** + controle positivo |
| P2-3 limiar 30 vs ADR 33 | P2 | **curado** + teste que parseia o ADR |
| P2-4 T7 media depois do restore | P2 | **curado** (instrumento) |

**4 achados curados com controle positivo ou teste novo; 2 pushbacks escritos;
1 deferido com análise.** Os dois pushbacks e o deferido são a MESMA fronteira:
o módulo de proveniência ainda não tem consumidor de produção, e a wave que o
ligar herda as três decisões juntas.
