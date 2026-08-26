# Pair-rail — PACOTE D (PLAN-179 W2+W4), rodada 3

**Instrumento:** `codex exec review --uncommitted` (codex-cli 0.147.0), clone
novo do HEAD `560dad0` com o pack **curado pelas rodadas 1 e 2** aplicado pelo
MANIFESTO + os materiais de cerimônia.

**Resultado:** `rc=0`, veredito **REJECT** — 4 P1 + 3 P2.
Rail-Verdict: REJECT
**Artefato bruto:** `<scratchpad>/pkgD-rail-3.txt` (3.789 bytes).

Sequência das rodadas: **9 → 4 → 7**. A subida não é regressão: dois dos
achados novos são superfícies que só ficaram alcançáveis DEPOIS das curas
anteriores, e **um é um bloqueante que a minha própria cura da rodada 2
introduziu** — a razão pela qual o rail roda de novo depois de cada cura, e
não uma vez no fim.

---

## P1-1 — pins de paridade 49/46 → 50/47 — **BLOQUEANTE, FORA DO MEU GRANT**

> `.claude/settings.json:353-355` — a registração nova sobe as contagens
> dogfood/template para 50/47, mas `test_template_dogfood_parity.py` ainda
> pina 49/46. O `test_registration_counts` falha deterministicamente e a
> suíte completa do V4 não passa enquanto o contrato não entrar no pack.

**VERIFICADO — e já era conhecido**: foi o que a simulação de land mediu
(6.828 passed, **1 failed**, `AssertionError: 50 != 49`). O rail chegou à
mesma conclusão por leitura estática, o que é confirmação independente.

**Disposição: reportado, NÃO curado — `test_template_dogfood_parity.py` não
está no meu FILE ASSIGNMENT.** Diff exato (3 sítios) entregue ao team-lead e
ao autor do pack. Remédio **verificado por mim em clone**: com os pins em
50/47 e o comentário `50 == 47 + 1 + 2`, o arquivo sai **14 passed**.

---

## P1-2 — a MINHA classe de teste nova quebrava o V6d — **CURADO**

> `test_check_ledger_checkpoint.py:652` — `check-test-env-hygiene.py` reporta
> esta classe como violação `bare-testcase` e sai 1; o
> `OWNER-W179-W24-LAND.sh` roda esse checker no V6d, então todo dry-run
> abortaria antes do staging.

**VERIFICADO — e é o achado mais instrutivo da noite.** Reproduzido:

```
.claude/hooks/tests/test_check_ledger_checkpoint.py:652: bare-testcase —
  class TestDeathCriterionAgreesWithTheADR(unittest.TestCase)
```

A classe é a que EU escrevi na rodada 2 para curar o P2-3 da rodada 1. Curei
um achado e introduzi um bloqueante do mesmo tipo do P1-4 da rodada 1 — o
mesmo gate, o mesmo script de land, a mesma consequência. Uma rodada de rail
depois da cura não é zelo excessivo; foi o que pegou.

**CURA:** a classe passa a herdar de `TestEnvContext`, com a razão escrita no
docstring para o próximo leitor não "simplificar" de volta. Depois:
`check-test-env-hygiene.py` **rc=0**, e a suíte dos dois arquivos do pack sai
**132 passed** em clone fresco.

---

## P1-3 — catálogo que compilou para NADA passava por utilizável — **CURADO**

> `ledger_provenance.py:480-484` — quando a compilação das regex do scanner
> falha ou não produz padrão nenhum, `family_names()` ainda devolve a lista de
> famílias de ORIGEM, então a função reporta o scanner como usável.
> `scan_harness_mimicry()` devolve `matched=False` com `bytes_scanned` não-zero
> e `evaluate_entry` aceita conteúdo externo hostil como limpo.

**VERIFICADO — fail-open real num matcher de segurança, com a discrepância
localizada nos dois lados:**

- `injection_patterns.family_names()` (`:242-244`) deriva de `_PATTERNS`, a
  lista de ORIGEM;
- `injection_patterns._compiled_patterns()` (`:161-172`) monta o conjunto de
  trabalho com `except re.error: continue` — **um padrão que não compila é
  descartado em silêncio**.

Os dois discordam exatamente no caso que importa. E o docstring do próprio
módulo (`:29`) já dizia que "catalogue compiled to nothing" deve ser um HIT —
a intenção estava escrita, a verificação não a implementava.

**CURA:** `_compiled_pattern_count()` pergunta ao lado COMPILADO; quando a
resposta existe, **ela decide**. Residual DECLARADO no docstring em vez de
assumido: um scanner que não exponha como perguntar cai de volta nas famílias
de origem — é API privada do módulo de referência, e por isso o fallback está
nomeado e coberto por teste.

**CONTROLE POSITIVO (provado vermelho→verde):** stub
`_CompiledToNothingScanner` (famílias de origem intactas, conjunto compilado
vazio). Com a forma pré-cura:

```
FAILED test_catalogue_that_compiled_to_nothing_is_a_reject
AssertionError: 'accept' != 'reject'
FAILED test_compiled_catalogue_decides_over_the_source_list
AssertionError: True is not false
```

`'accept' != 'reject'` é literalmente conteúdo hostil aceito como limpo. Com a
cura: **69 passed**.

---

## P1-4 — o adopter que faz UPGRADE recebe o hook DESLIGADO — **FORA DO MEU GRANT**

> `templates/settings/settings.base.json:214-217` — a registração no template
> só alcança instalações NOVAS. Para um adopter existente,
> `scripts/upgrade.sh:_merge_lifecycle_hooks_into_settings` preserva o
> `settings.json` atual e **hard-codeia seis** hooks de ciclo de vida, sem
> entrada para `check_ledger_checkpoint.py` — o upgrade instala o script e o
> deixa sem fio, e a telemetria de checkpoint nunca roda.

**VERIFICADO por leitura de `scripts/upgrade.sh` — verdadeiro.**

Este é o achado de maior alcance da noite, e é da MESMA FORMA que o PLAN-183
passou cinco sessões curando: **a entrega ao adopter não acompanha o que o
repo dogfood ganha.** O espelho no template resolve o adopter NOVO e é
verificado por `test_template_dogfood_parity`; o adopter EXISTENTE depende de
uma lista escrita à mão dentro do `upgrade.sh`, que nenhum gate compara com o
conjunto real de hooks de ciclo de vida.

**Disposição: reportado, NÃO curado.** `scripts/upgrade.sh` está fora do meu
FILE ASSIGNMENT, e a cura certa não é acrescentar uma sétima entrada à lista
— é fazer a lista DERIVAR do template (a mesma classe de cura que o PLAN-183
aplicou com `delivery-routes.tsv`: um dado com leitores, não seis literais).
Isso é wave própria.

Consequência honesta se o pacote landar como está: o hook funciona neste repo
e em instalações novas; adopters que fizerem upgrade recebem o arquivo e não
recebem a registração. Como o rail é ADVISORY, o efeito é telemetria ausente,
não quebra.

---

## P2-1 — `--pathspec-from-file` não marca a invocação como dirigida por path

> `check_ledger_checkpoint.py:399-403` — a opção FORNECE os paths que o commit
> vai incluir; listá-la como opção de valor comum consome o nome do arquivo
> sem marcar a invocação como pathspec-driven, e as duas formas passam a
> inspecionar o conjunto staged.

**VERIFICADO — verdadeiro, e é consequência direta da minha cura do P2-2 da
rodada 1.** Ao consumir o valor, tirei o efeito colateral que ACIDENTALMENTE
marcava a invocação como pathspec-driven.

**Disposição: ACEITO, DEFERIDO.** A cura correta é tratar
`--pathspec-from-file` como seletor de path (as duas formas), não como opção
de valor — mas isso muda a CLASSIFICAÇÃO de commits, e classificação alimenta
os números da janela measure-first. Mesmo raciocínio do P2-1 da rodada 1: não
é escolha do agente de cerimônia na véspera da assinatura. Fica nomeado aqui,
com o mecanismo escrito.

Exposição: baixa — `--pathspec-from-file` é raro em uso interativo, e o
resultado é uma classificação imprecisa, não silêncio.

---

## P2-2 — estado de observação ilegível é reportado como `fresh`

> `check_ledger_checkpoint.py:684-688` — se o arquivo de estado existe mas tem
> JSON malformado ou não pode ser lido, a exceção só emite breadcrumb e `kind`
> fica `fresh`. A linha de auditoria afirma uma primeira observação normal em
> vez de `unavailable`, escondendo a perda da âncora.

**VERIFICADO — verdadeiro, e o próprio módulo documenta por que importa:**
`state_kind` existe para nomear a confiança do contador, e o docstring diz
que `fresh` significa "sem âncora anterior, o 0 é ESTRUTURAL e NÃO deve ser
lido como zero commits não-observados". Reportar `fresh` para um estado
CORROMPIDO faz a linha mentir exatamente onde ela deveria avisar.

**Disposição: ACEITO, DEFERIDO** — pela mesma razão dos outros: `state_kind`
é entrada do estimador de censura da janela, e `unavailable` vs `fresh` muda
o denominador publicado. Mecanismo escrito; decisão de quem é dono dos
números.

---

## P2-3 — inspeciona a árvore de trabalho, não a versão que será commitada

> `check_ledger_checkpoint.py:852-861` — o conjunto de paths vem do índice,
> mas o tamanho do ledger e a checagem de verificadores leem o arquivo da
> árvore de trabalho. Depois de staging parcial, o ledger commitado pode ter
> conteúdo acima do teto ou não-verificável enquanto o hook inspeciona uma
> cópia limpa.

**VERIFICADO — verdadeiro.** É a mesma família do P2-1 da rodada 1 (índice vs
árvore) e a cura seria ler o blob staged (`git show :<path>`).

**Disposição: ACEITO, DEFERIDO.** Custo: uma chamada git a mais por commit,
dentro de um budget de tempo já declarado; benefício: o advisory descreve os
bytes que serão commitados. Cabe na wave que fizer o conjunto índice-vs-árvore
de uma vez — fazer só um lado agora deixaria o módulo inconsistente consigo
mesmo.

---

## Resumo da rodada 3

| # | sev | disposição |
|---|---|---|
| P1-1 pins de paridade 49/46 | P1 | **fora do grant** — diff entregue, remédio verificado (14 passed) |
| P1-2 `bare-testcase` da minha classe | P1 | **curado** (era bloqueante do V6d) |
| P1-3 catálogo compilado vazio aceito | P1 | **curado** + controle positivo |
| P1-4 upgrade não liga o hook no adopter | P1 | **fora do grant** — reportado, cura é wave própria |
| P2-1 `--pathspec-from-file` | P2 | **aceito, deferido** |
| P2-2 estado ilegível vira `fresh` | P2 | **aceito, deferido** |
| P2-3 inspeciona worktree, não índice | P2 | **aceito, deferido** |

**2 curados (um deles um bloqueante que eu mesmo criei na rodada anterior),
2 fora do grant com diff pronto e verificado, 3 deferidos com mecanismo
escrito.** Os três deferidos são a mesma fronteira: todos mexem em números ou
classificações que alimentam a janela measure-first, e o dono desses números é
o dono do plano, não o agente de cerimônia.
