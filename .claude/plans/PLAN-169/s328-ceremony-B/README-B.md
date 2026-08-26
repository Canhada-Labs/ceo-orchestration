# Pacote B — o que você faz de manhã (4 comandos, nenhum editor)

Este pacote muda **três arquivos** que exigem a sua assinatura. Você não digita
`git` em momento nenhum. Se algum editor abrir (tela azul/preta com texto),
aperte **Esc**, digite **`:q!`** e **Enter** — sai sem salvar, nada se perde.

---

## Antes de começar: uma coisa tem de estar pronta

Este pacote é só a **metade que precisa de assinatura**. A outra metade — o
arquivo `.claude/scripts/profile-opus-4-7.py` e o teste dele — é código comum e
entra no repositório por um commit normal do CEO, **sem** cerimônia.

**Se essa metade não estiver commitada, os scripts abaixo param sozinhos e
dizem exatamente isso.** Eles não deixam você assinar um pacote que quebraria a
CI. Se isso acontecer, chame o CEO — não force nada.

---

## Os 4 comandos, em ordem

Copie e cole cada linha inteira, uma de cada vez, e espere terminar antes da
seguinte.

### 1. Re-basear o pacote no estado atual do repositório

```
bash .claude/plans/PLAN-169/s328-ceremony-B/finalize-B.sh
```

O repositório andou desde que o pacote foi montado. Este passo alinha o pacote
com o estado de agora e roda uma bateria curta. Se ele disser
**«NADA a fazer»**, ótimo — está tudo alinhado, siga para o passo 2.

### 2. Assinar

```
bash .claude/plans/PLAN-169/OWNER-S328-B-SIGN.sh
```

Vai pedir a senha da sua chave GPG. Se aparecer **«No pinentry»**, rode no seu
terminal (não por aqui):

```
export GPG_TTY=$(tty); gpgconf --kill gpg-agent
```

e repita o passo 2 do zero.

> **Depois de assinar, não commite nada.** Qualquer commit invalida a
> assinatura e o passo 4 vai parar.

### 3. Ensaio (não muda nada de verdade)

```
bash .claude/plans/PLAN-169/OWNER-S328-B-LAND.sh --dry-run
```

Roda todos os portões e **desfaz tudo** no fim. Se algo estiver errado, ele
para aqui, com o motivo escrito. Só siga para o 4 se este terminar verde.

### 4. Aplicar de verdade (commita e empurra)

```
bash .claude/plans/PLAN-169/OWNER-S328-B-LAND.sh
```

Este demora alguns minutos — ele roda uma execução real do medidor de latência.
No fim ele mostra o commit criado, empurra para o `main` e lista os últimos
runs de CI.

---

## O que este pacote faz

O portão de latência da CI vinha reprovando o `Validate` **sem que houvesse
regressão nenhuma**: os mesmos bytes que reprovaram tinham passado três horas
antes, e medem 70–77 ms na sua máquina contra 361 ms no runner. A sonda que
existe para detectar «o runner está lento» dizia que estava tudo bem — ela mede
a criação de processo, não o trabalho que o hook realmente faz.

O pacote acrescenta uma **segunda medida**, relativa: quanto o hook demora
*comparado com uma tarefa de referência rodando na mesma máquina, no mesmo
momento*. Um runner lento deixa as duas lentas; uma regressão de verdade deixa
só o hook lento.

**Nesta primeira fase a medida nova só é PUBLICADA, não decide nada.** Os
vereditos continuam exatamente os de hoje. Isso é de propósito: fixar o limiar
antes de ter dados seria inventar um número.

## O que este pacote NÃO faz

**Ele não deixa o `Validate` verde.** Como a fase 1 não muda veredito, uma
execução que hoje reprova continua reprovando. O verde vem do **rerun de
madrugada**, que é a outra metade da sua decisão de 25/08 («Emenda + gate em
pacote, e 1 rerun de madrugada»).

## Depois do land

Cada execução do `Validate` passa a publicar, no resumo do job, o rótulo e os
números da medida nova. **Colete pelo menos 10 execuções verdes ao longo de
pelo menos 3 dias** antes de tentar ligar a fase 2 — é o que está registrado
como pergunta aberta **OQ-9** no `PLAN-169`.

---

## Se algo der errado

| o que aconteceu | o que fazer |
|---|---|
| um editor abriu | Esc, `:q!`, Enter |
| «No pinentry» | `export GPG_TTY=$(tty); gpgconf --kill gpg-agent` e repita o passo 2 |
| o script parou dizendo que falta o profiler em HEAD | chame o CEO — a outra metade não foi commitada |
| o passo 3 parou com outro motivo | **não** rode o passo 4; mande a saída inteira para o CEO |
| o passo 4 parou depois do commit | o commit está salvo localmente; a mensagem diz o comando exato para reempurrar |

Nenhum passo é destrutivo antes de todos os portões passarem, e o ensaio
(passo 3) restaura a árvore byte a byte.

---

## Arquivos deste pacote (para o CEO)

| arquivo | papel |
|---|---|
| `B.patch` | o diff assinável (3 paths canônicos, +281/−0) |
| `BASE-SHA.txt` | o commit contra o qual o patch foi gerado |
| `PROPOSED-PATCH.md` | o registro que a revisão leu (o quê, por quê, medições) |
| `EXPECTED-BASELINE.txt` | os conjuntos DECLARADOS contra os quais o V-block compara |
| `COMMIT-MSG-B.txt` | a mensagem de commit (usada com `-F`, sem editor) |
| `rail-round-*.md` | as rodadas de pair-rail, com claim → verificação → cura/pushback |
| `finalize-B.sh` | re-base do pacote no HEAD vivo |
| `test-ceremony-scripts-B.sh` | harness: planta divergências e exige vermelho nomeado |
| `../OWNER-S328-B-SIGN.sh` | assinatura |
| `../OWNER-S328-B-LAND.sh` | land (G-PRE + G0..G5 + V1..V7 + commit + push) |
| `../wave-s328-B-approved.md` | o sentinel (Scope DERIVADO, nunca escrito à mão) |
