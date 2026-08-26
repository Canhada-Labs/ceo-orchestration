# PACOTE D — PLAN-179 W2+W4 (ledger de trabalho + governança do estado durável)

> **Para o Owner.** Três comandos, nesta ordem, copiando e colando inteiros.
> Nenhum deles abre editor. Você não digita `git` em momento nenhum.
> Se um editor abrir por qualquer motivo: **Esc**, depois `:q!`, depois Enter.

---

## Antes de começar (30 segundos)

**Passo zero, uma vez só:** abra o terminal e entre na pasta do projeto.
Os três comandos abaixo são relativos a ela.

```
cd ~/canhada-labs/ceo-orchestration
```

(Se o seu checkout estiver noutro lugar, use o caminho dele. Os scripts
resolvem a raiz do repositório sozinhos a partir da própria localização, e
cada um imprime o comando seguinte já pronto para copiar.)

Este pacote é o **último** da fila da manhã (ordem **B → A → C → D**). Ele só
deve rodar depois que B, A e C tiverem landado e sido pushados. Se você está
usando o `OWNER-S328-MORNING.sh`, ele já faz essa ordem sozinho e chama os
três comandos abaixo por você — neste caso **não rode nada daqui**, é só
referência.

O pacote muda 27 arquivos. O que ele entrega, em uma frase: o hook de ledger
de trabalho, o módulo de proveniência, o ADR-195 e as **três** ações novas de
auditoria que você decidiu em 2026-08-25 (`ledger_checkpoint_recorded`,
`ledger_checkpoint_skipped`, `ledger_entry_rejected`).

---

## Comando 1 — assinar

```
bash .claude/plans/PLAN-179/OWNER-W179-W24-SIGN.sh
```

O que ele faz: confere que a árvore está limpa e que o pacote está fresco,
preenche a data e a âncora no sentinel, e pede a sua senha do GPG.

**Se ele reclamar de "material NÃO commitado"**: os arquivos do pacote ainda
não foram commitados. Ele imprime o comando exato para resolver — cole aquele
comando, depois rode o Comando 1 de novo.

**Se der "No pinentry"**: é o modo de falha conhecido desta máquina. Rode, no
seu terminal:

```
export GPG_TTY=$(tty); gpgconf --kill gpg-agent
```

e repita o Comando 1 do zero. O script já desfaz sozinho o que tinha começado.

---

## Comando 2 — ensaio (não muda nada de forma permanente)

```
bash .claude/plans/PLAN-179/OWNER-W179-W24-LAND.sh --dry-run
```

Este é o ensaio completo: ele aplica o pacote, roda a bateria inteira de
testes contra os números declarados e **desfaz tudo no fim**, deixando a
árvore byte a byte como estava. Ele imprime `restaurados byte a byte` quando
termina bem.

**Isto demora, e sabemos quanto.** A suíte de hooks roda em quatro passadas (o
mesmo formato que o CI usa). Na simulação desta madrugada, a passada mais
longa levou **21 min 47 s** sozinha (6.828 testes), com a máquina ocupada com
outras coisas. Conte **~25 a 35 minutos** para o Comando 2 inteiro, e o mesmo
de novo para o Comando 3.

Não interrompa. Se você interromper com Ctrl-C, o script ainda desfaz o que
aplicou — mas é melhor deixar terminar.

Se ele terminar em vermelho, **pare aqui** e chame o CEO. A mensagem de erro
diz qual verificação falhou e qual número não bateu.

---

## Comando 3 — landar de verdade

```
bash .claude/plans/PLAN-179/OWNER-W179-W24-LAND.sh
```

Mesma bateria, e no fim ele aplica, commita e **empurra para o `main`**
sozinho. Termina imprimindo o commit criado e os últimos 5 runs do CI.

---

## Como saber que deu certo

O Comando 3 termina com um bloco `LAND OK` mostrando o commit e a quantidade
de paths. Depois disso, o CI:

- **Validate** deve ficar verde.
- Se o **único** vermelho for o gate de latência de hook, isso é o drift de
  runner já conhecido desde a S327 — **não** é este pacote. Não mexa; um
  re-run resolve.

---

## Se alguma coisa der errado

| o que apareceu | o que fazer |
|---|---|
| `modificacoes RASTREADAS na arvore` | Alguém editou arquivos e não commitou. Chame o CEO. |
| `o main andou depois da montagem do pack` | O pacote ficou velho. Ele precisa ser re-montado e re-revisado — chame o CEO, **não** force. |
| `anchor != HEAD` | Algum commit entrou entre assinar e landar. Rode o Comando 1 de novo (re-assinar) e siga. |
| `observado X, DECLARADO Y` | Uma contagem não bateu com o que foi medido e assinado. **Não afrouxe o número.** Chame o CEO. |
| `o push falhou` | O commit está salvo localmente, nada se perdeu. A própria mensagem traz o comando para tentar de novo. |
| um editor abriu | **Esc**, `:q!`, Enter. Nada se perde. |

---

## Para o CEO (não é preciso ler para operar)

- **Escopo assinado**: 27 paths, derivados do `MANIFEST.sha256` do pack. O gate
  G2b compara o bloco `## Scope` do sentinel com o manifesto e aborta em
  qualquer divergência, nos dois sentidos.
- **V-block contra conjuntos DECLARADOS** em `EXPECTED-BASELINE.txt`
  (`len(_KNOWN_ACTIONS)`, linhas do golden, `hook_py`, `registered`,
  `registrations`, `lib`, `adrs`, linha de histórico do SPEC). Nunca contra
  zero — essa foi a lição 1 da S327.
- **`--dry-run` aplica de verdade** e restaura por trap com verificação de
  fingerprint (`git status` + `git diff HEAD` + índice). Um abort em qualquer
  ponto do V-block restaura do mesmo jeito.
- **Modos de arquivo**: o `chmod +x` cego do molde anterior (`case` com
  `.claude/hooks/*.py`, onde o `*` atravessa `/`) tornaria `_lib/audit_emit.py`
  755. Aqui o modo é derivado do índice para destino existente, e para destino
  novo é 755 só em hook de profundidade 1. O passo S aborta se qualquer
  mudança de modo aparecer no índice.
- **Prova**: `land-sim.log` (tabela comando → rc), `rail-round-*.md` (pair-rail
  até APPROVE) e `test-ceremony-scripts-w24.sh` (harness com controle positivo
  em cada gate).
- Rodar o harness: `bash .claude/plans/PLAN-179/s328-ceremony-D/test-ceremony-scripts-w24.sh`
  — clone descartável, sem GPG, sem push.
