# Pair-rail — wave-s328-B, rodada 5 (ÚLTIMA) — critério de parada

Comando: `codex exec review --uncommitted` na árvore-sombra
`<scratchpad>/shadow-163` (base `560dad0`), saída em `pkgB-rail-5.txt`.
`codex-cli 0.147.0`, rc 0, saída não-vazia.

**Veredito da rodada:** REJECT — **1 × P1, 0 × P2**.

---

## O veredito literal NÃO é `VERDICT: APPROVE`, e o motivo é declarado

O critério de parada desta cerimônia era «rodada limpa = rc 0 **E**
`VERDICT: APPROVE` literal». **Ele não foi alcançado**, e a honestidade aqui
vale mais do que o carimbo: registro o veredito real, não uma leitura
complacente de um REJECT.

O que restou é **um único achado**, o mesmo desde a rodada 1:

> `[P1] Add the profiler options before using them` — «`profile-opus-4-7.py`
> rejects both options as unrecognized because its parser registers neither
> `--exec-reference` nor `--relative-advisory`.»

## Por que ele não pode fechar nesta sombra

Ele é **estruturalmente inevitável** e foi **provado empiricamente pelo próprio
revisor**: o log desta rodada (`pkgB-rail-5.log`) mostra o codex EXECUTANDO o
comando na sombra e recebendo, em bytes,

```
profile-opus-4-7.py: error: unrecognized arguments: --exec-reference --relative-advisory
```

Isso não é inferência do revisor — é a medição. E ela está **correta para a
árvore que ele leu**, porque o `HEAD` vivo (`560dad0`) ainda não carrega a
metade não-canônica: o profiler curado (`+794/−17`) e
`test_hook_latency_relative_gate.py` seguem como modificação de árvore de
trabalho, à espera do commit comum do CEO.

Fazer o achado desaparecer exigiria uma de duas coisas, e **nenhuma é minha**:

1. commitar a metade não-canônica no `main` — fora do meu FILE ASSIGNMENT e
   fora das minhas restrições (sem `git commit` no checkout vivo); ou
2. mover ~800 linhas de código não-canônico para dentro do patch assinável —
   o desenho que a síntese dos três críticos rejeitou explicitamente
   (`canonical_diff_minimal`: «validate.yml ONLY, 3 functional lines»), e que
   faria o Owner assinar código que não precisa de assinatura.

## O que a série de 5 rodadas PROVOU

O rail não foi decorativo. Ele encontrou e fechou **dois defeitos reais de
conteúdo**, ambos da mesma classe — *texto canônico afirmando uma propriedade
que o código não tem*:

| rodada | achado | verificação | fechou em |
|---|---|---|---|
| 1 | o auto-cap «removia» o rótulo errado do wrapper para rc 124 | FALSO: ele RENOMEIA o caso para rc 5, que cai no mesmo `else` e sai sob a mesma mensagem «real regression» | rodada 2 |
| 3 | a cota de admissibilidade `<=` «preservava» a detecção | FALSO: em `K_e = cota` o controle de +150 ms tem `rel_ok` VERDADEIRO e **passa** | rodada 4 |

E a convergência é medível:

| rodada | P1 | P2 | achados de conteúdo |
|---|---|---|---|
| 1 | 3 | 1 | 1 (auto-cap) |
| 2 | 1 | 0 | 0 |
| 3 | 1 | 2 | 1 (cota) |
| 4 | 2 | 1 | 0 |
| 5 | **1** | **0** | **0** |

Duas rodadas consecutivas (4 e 5) sem nenhum achado de conteúdo, e a rodada 5
com o conjunto reduzido ao mínimo irredutível — só a dependência entre pacotes.

## O que fica no lugar do carimbo

O achado não é ignorado; ele é **convertido em gate**. Três scripts leem
`git show HEAD:` e abortam nomeando:

- `OWNER-S328-B-SIGN.sh` — **antes de assinar**, de propósito: commitar o
  profiler depois da assinatura moveria o `HEAD` e invalidaria o `Anchor-SHA`;
- `OWNER-S328-B-LAND.sh` — `G-PRE`, antes de qualquer mutação;
- `finalize-B.sh` — antes sequer de re-gerar o patch.

E o harness tem o controle POSITIVO (`T8`), na forma ADVERSARIAL: renomeia a
flag com um SUFIXO (`--exec-reference-DISABLED-BY-SELFTEST`) e commita o
plant, depois exige o land vermelho com a razão nomeada. O sufixo é o ponto:
um `grep -c -- "--exec-reference"` de substring casaria o nome adulterado e o
gate ficaria VERDE com o profiler quebrado — medido nesta sessão, foi o modo
de falha da primeira versão do `G-PRE`. A checagem passou a ser ancorada por
fronteira de palavra (`grep -cE`), e o T8 é o controle dessa ancoragem. Sem
esse caso, o `G-PRE` seria uma afirmação; com ele, é um gate provado.

**Consequência operacional, escrita para quem for landar:** se a metade
não-canônica não estiver em `HEAD`, os três scripts param sozinhos. O pacote
não pode ser assinado nem landado num estado em que este achado seria real.

---

## Adendo pós-rodada 5 — um dos achados estruturais fechou sozinho

Depois da rodada 5, o CEO commitou `a59da85` («OQ-5..11 do PLAN-183 e
OQ-7..12 do PLAN-169 registradas…») e `8a28555`. Medido no `HEAD` novo
(`8a28555`):

| pré-condição do `G-PRE` | em `560dad0` | em `8a28555` |
|---|---|---|
| `OQ-(7\|8\|9\|10\|11\|12)` no `PLAN-169-…md` | 0 | **7** |
| `--exec-reference` no profiler (fronteira de palavra) | 0 | 0 |
| `test_hook_latency_relative_gate.py` | ausente | ausente |

O **P2-B fechou** — as perguntas que as duas emendas citam existem agora no
commit. Restam as duas pernas do profiler, e é exatamente por isso que o
`G-PRE` checa as três de forma independente: o estado parcial de hoje passaria
num gate que perguntasse «a metade não-canônica chegou?» como pergunta única.

**Estado da base do patch.** `Patch-base` = `560dad0`, que é **ancestral** de
`8a28555`, e nenhum dos 3 paths tocados derivou entre os dois — `git apply
--check` sai **0** contra o `HEAD` novo. É precisamente a forma que o `SIGN`
(P1) e o `LAND` (G4) exigem, então **nada precisa ser re-gerado agora**. O
re-base fica para o `finalize-B.sh` da manhã, que só roda depois do `G-PRE`
passar — um pacote cuja pré-condição não está satisfeita não deve nem ser
re-finalizado.
