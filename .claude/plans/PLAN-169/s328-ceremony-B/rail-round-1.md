# Pair-rail — wave-s328-B, rodada 1

Comando: `codex exec review --uncommitted` na árvore-sombra
`<scratchpad>/shadow-163` (base `a16ac96`), saída em `pkgB-rail-1.txt`.
Substrato: `codex-cli 0.147.0`. rc 0, saída não-vazia.

**Veredito da rodada:** REJECT — 3 × P1, 1 × P2.

Resumo do revisor, verbatim: «The workflow unconditionally invokes unsupported
CLI options, causing the latency job to fail on every run. The patch also leaves
infrastructure-result handling inconsistent, references nonexistent Owner
decisions, and lacks required authorization for ADR-144.»

---

## P1-1 — «Add profiler support before passing the new flags» (`validate.yml:1272-1273`)

**Claim.** O profiler não registra `--exec-reference` nem `--relative-advisory`
(`profile-opus-4-7.py:721-801`); a invocação sairia 2 com «unrecognized
arguments» e o job ficaria vermelho em todo push.

**Verificação.** VERDADEIRA sobre a árvore que o revisor leu, FALSA sobre o
estado em que o pacote landa. Medido nas três árvores:

| árvore | `--exec-reference` no profiler |
|---|---|
| sombra (`a16ac96`) | ausente |
| `HEAD` vivo (`560dad0`) | ausente |
| checkout vivo (working tree) | **presente**, +794/−17 não commitado |

No checkout vivo as quatro flags aparecem no `--help`
(`--exec-reference`, `--relative-advisory`, `--relative-k-source`,
`--wall-budget-seconds`) e uma execução real com elas produz relatório válido —
medido nesta sessão, `rc 0` com teto alto, `phase=1-advisory`, as três chaves
por entrada presentes nas 5 entradas.

**Causa.** O trabalho está DELIBERADAMENTE partido: a lógica vive em
`profile-opus-4-7.py` + `test_hook_latency_relative_gate.py`, que são
**não-canônicos** (oráculo `--is-canonical` = 0) e entram no `main` por commit
comum do CEO, fora de cerimônia. Este pacote é só a superfície canônica. Um
patch que carregasse os dois faria assinar 800 linhas de código não-canônico.

**Cura — mecânica, não textual.** O `OWNER-S328-B-LAND.sh` ganhou uma
pré-condição **G-PRE** que aborta nomeando o problema se a metade não-canônica
não estiver em **HEAD** no momento do land. A checagem é contra `git show HEAD:`,
não contra a árvore de trabalho — estritamente mais forte do que `grep` no
working tree, que hoje passaria com a metade ainda por commitar. Cobre as 4
flags e a existência do arquivo de teste.

## P1-2 — «Preserve infrastructure exit 5 in the retry wrapper» (`ADR-163:502-505`)

**Claim.** Quando a validação de referência ou o auto-cap produzem
`infrastructure_contended`/exit 5, o wrapper inalterado trata como falha
qualquer; depois de uma sonda UNCONTENDED, um terceiro rc 5 é registrado como
«real regression» e convertido em exit 1 (`validate.yml:1352-1376`). Logo o
auto-cap **não** torna o rótulo errado inalcançável, como a emenda afirmava.

**Verificação.** **VERDADEIRA — e é defeito de conteúdo do texto que embarca.**
Lido o wrapper em `validate.yml:1352-1376`: os ramos `else` capturam
`rc=$?` sem discriminar valor; o ramo pós-sonda imprime
`::error::…treating as a real regression` e `exit 1` para QUALQUER rc não-zero.
O auto-cap não remove a classe de rótulo errado: ele a **renomeia** de rc 124
para rc 5.

**Escopo do defeito, medido.** O rc 5 é **inalcançável em fase 1**. O próprio
profiler documenta em código «PHASE 1 keeps `exit_class == (0 if passed else 1)`
by construction […] PHASE 2 is the only state that can return 5», e isso é
ASSERÇÃO e não comentário: `test_auto_cap_in_phase1_keeps_a_nonzero_exit`
força `--wall-budget-seconds 0` (o cap mais agressivo disponível) e exige
`rc == 1`. Nada neste diff canônico cria rota para o rótulo errado.

**Cura, na sombra.** O parágrafo «Known defect» da emenda foi reescrito: diz
agora que o auto-cap RENOMEIA em vez de remover, que a redação anterior estava
errada e está corrigida, que a fase 1 é imune por construção (citando o teste
que prova), e que ensinar o wrapper a distinguir rc 5 é **pré-condição NOMEADA
da fase 2**, não faxina opcional. O `wave-s328-B-approved.md` foi reconciliado
no mesmo sentido — um sentinel que contradiz o ADR que ele autoriza é evidência
falsa.

**O que NÃO foi feito.** O wrapper continua intocado. Crescer o diff canônico
para tratar rc 5 hoje seria reverter uma decisão que a síntese dos três críticos
já tomou («ADOPTED zero»), para um caminho que a fase 1 não alcança.

## P1-3 — «Attach Owner-signed sentinel evidence for the guarded edit» (`ADR-144:114`)

**Claim.** Antes de landar a emenda do ADR-144 é preciso um sentinel S328
assinado que escope o arquivo; a árvore de trabalho não tem tal aprovação e
nenhum sentinel confiável existente nomeia o ADR-144.

**Verificação.** VERDADEIRA como descrição do estado da SOMBRA, e é exatamente
a pré-condição que este pacote existe para satisfazer — **PUSHBACK, sem
mudança**. O revisor lê a sombra, onde os materiais de cerimônia não vivem: o
sentinel `.claude/plans/PLAN-169/wave-s328-B-approved.md` está no checkout vivo,
e seu bloco `Scope:` é DERIVADO pelo `finalize_patch.py` a partir de
`git apply --numstat` — os três paths do patch, ADR-144 incluído, entram por
construção, nunca à mão.

A objeção não é vácua e não é ignorada: ela é respondida **mecanicamente** no
land. O **G5** do `OWNER-S328-B-LAND.sh` chama `_sentinel_grants_path` — a
MESMA função que o hook `check_canonical_edit.py` usa — para cada path canônico
tocado, e aborta se algum não for concedido. Assinatura GPG válida que concede
zero paths não autoriza nada (lição S318); é essa a checagem, não a existência
do `.asc`.

## P2-4 — «Add the owner questions referenced by the amendments» (`ADR-163:530`)

**Claim.** O `PLAN-169` define só OQ-1..OQ-6; a emenda cita OQ-7..OQ-12 e o
ADR-144 aponta para a OQ-11, inexistente.

**Verificação.** VERDADEIRA sobre sombra e `HEAD`, FALSA sobre o estado do land.
Contagem de `OQ-(7|8|9|10|11|12)`:

| árvore | ocorrências |
|---|---|
| sombra (`a16ac96`) | 0 |
| `HEAD` vivo (`560dad0`) | 0 |
| checkout vivo (working tree) | **7** (`:1382` e `:1397`..`:1422`) |

Mesma causa e mesma cura do P1-1: o `PLAN-169-…md` está ` M` e entra no commit
não-canônico do CEO. A pré-condição **G-PRE** do LAND também exige
`git show HEAD:` com ≥ 6 ocorrências, e aborta nomeando o que falta.

---

## Balanço

| # | severidade | veredito | ação |
|---|---|---|---|
| P1-1 | P1 | verdadeira sobre a sombra, não sobre o land | cura MECÂNICA: pré-condição G-PRE no LAND |
| P1-2 | P1 | **verdadeira, defeito real de conteúdo** | curado na sombra (ADR-163 + sentinel reconciliado) |
| P1-3 | P1 | descreve a pré-condição da própria cerimônia | pushback escrito; respondida pelo G5 |
| P2-4 | P2 | verdadeira sobre a sombra, não sobre o land | mesma pré-condição G-PRE |

O P1-2 é o achado que pagou a rodada: o rail leu o wrapper que o pacote
deliberadamente NÃO toca e pegou uma afirmação falsa no texto que o pacote
ASSINA. É o padrão conhecido — o rail revisa o TEXTO, e aqui o texto afirmava
uma propriedade do código que o código não tem.
