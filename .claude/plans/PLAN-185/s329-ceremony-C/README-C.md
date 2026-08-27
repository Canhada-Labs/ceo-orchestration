# Pacote C — o que você faz de manhã (4 comandos, nenhum editor)

Este pacote conserta **dois jeitos de o instalador estragar a máquina de quem o
usa**. Você não digita `git` em momento nenhum. Se algum editor abrir (tela
azul/preta com texto), aperte **Esc**, digite **`:q!`** e **Enter** — sai sem
salvar, nada se perde.

---

## Antes de começar: duas coisas que os scripts verificam sozinhos

1. **Que o pacote está inteiro.** Ele tem duas metades escritas em paralelo: a
   do código e a do CI/documentação. O passo 1 **para e diz qual arquivo falta**
   se alguma delas não entrou. Não tente destravar removendo o arquivo da lista
   — um teste sem a linha de CI é um teste que nunca roda.
2. **Que a régua de medição não trocou.** Um dos gates conta "quantos lugares do
   instalador ainda escrevem sem proteção". Esse contador é um programa que
   estava sendo reescrito na mesma noite, e o mesmo código medido por duas
   versões dele dá números diferentes. Por isso a versão fica **travada por
   impressão digital**: se ela mudar, o script para em vez de comparar números
   que não se comparam.

3. **Que o pacote não vai deixar o CI vermelho.** Este pacote instala, ele
   mesmo, um novo gate de CI que roda esse contador e **falha se ele acusar
   diferença**. A correção mexe em muito código, então o contador precisa ter a
   sua lista de referência regerada no mesmo pacote. Os scripts **param** se
   isso não tiver sido feito — de propósito: landar sem isso deixaria o
   `Validate` vermelho no `main` já no primeiro push, por um gate que o próprio
   pacote acabou de instalar. Foi assim que o `main` ficou vermelho por cinco
   sessões seguidas neste ano.

Se algo faltar, eles param e dizem exatamente o quê. **Não force nada** — chame
o CEO.

---

## Os 4 comandos, em ordem

Copie e cole cada linha inteira, uma de cada vez, e espere terminar antes da
seguinte.

### 1. Montar o pacote sobre o estado atual do repositório

```
bash .claude/plans/PLAN-185/s329-ceremony-C/finalize-C.sh
```

O trabalho foi feito numa cópia separada do repositório, e o repositório andou
desde então. Este passo alinha os dois e roda uma bateria curta (menos de um
minuto). Se ele disser **«NADA a fazer»**, ótimo — está tudo alinhado, siga para
o passo 2.

### 2. Assinar

```
bash .claude/plans/PLAN-185/OWNER-S329-C-SIGN.sh
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
bash .claude/plans/PLAN-185/OWNER-S329-C-LAND.sh --dry-run
```

Roda os portões rápidos e **desfaz tudo** no fim. Leva um ou dois minutos. Se
algo estiver errado, ele para aqui, com o motivo escrito. Só siga para o 4 se
este terminar verde.

### 4. Aplicar de verdade (commita e empurra)

```
bash .claude/plans/PLAN-185/OWNER-S329-C-LAND.sh
```

**Este demora cerca de 20 minutos.** Ele roda duas baterias caras que não têm
substituto barato: uma que instala o framework treze vezes em pastas de mentira
com armadilhas plantadas (~7 min), e outra que faz uma instalação de verdade
para confirmar que a correção não quebrou o instalador. Deixe rodando. No fim
ele mostra o commit criado, empurra para o `main` e lista os últimos runs de CI.

---

## O que este pacote conserta

### Problema 1 — o instalador escrevia FORA da pasta que você deu a ele

Antes de escrever um arquivo, o instalador perguntava "já existe alguma coisa
aqui?". Essa pergunta **atravessa atalhos**: se alguém tivesse deixado, no lugar
do arquivo, um atalho apontando para outra pasta do sistema, a resposta era
"não tem nada aqui" — e o instalador escrevia **do outro lado do atalho**, fora
do alvo, dizendo que tinha copiado, e saindo com sucesso.

Medimos: **536 bytes foram parar num caminho fora da pasta**, com a execução
reportando tudo certo. O modo "só me mostre o que você faria" mentia igual.

A cura põe **uma única função** que responde "esse destino é seguro?" — e todos
os sete lugares que escrevem passam a perguntar a ela. Ela olha cada pedaço do
caminho, inclusive o último, inclusive quando o atalho aponta para o nada
(que é justamente o caso que enganava a pergunta antiga), e inclusive o caso em
que o mesmo arquivo tem dois nomes — que nenhuma checagem de caminho enxerga.

Detalhe importante: a função foi posta numa **biblioteca compartilhada**, e não
dentro do instalador. Se ela morasse dentro do instalador, o programa de
atualização precisaria de uma cópia — e cópias divergem. Foi exatamente isso que
deixou o `main` vermelho durante cinco sessões seguidas neste ano.

### Problema 2 — um nome de dono com barra apagava o arquivo de donos

Ao instalar com `--github-owner`, o nome era colado dentro de um comando de
substituição de texto. Um nome contendo `/` **quebrava o comando pela metade** —
mas só *depois* de o arquivo de destino já ter sido esvaziado. Resultado: o
`.github/CODEOWNERS` ficava com **zero bytes**, para sempre (as execuções
seguintes viam que o arquivo "existe" e pulavam), fora do alcance do desfazer, e
o GitHub lia isso como "esse projeto não tem donos de revisão".

A cura tira o nome de dentro do comando: ele passa a ser só texto trocado por
texto, sem poder mudar o que o programa faz. E a escrita virou **atômica** —
escreve num arquivo temporário e só troca no fim, então qualquer falha deixa o
destino exatamente como estava, inclusive inexistente.

Se o arquivo já estiver com zero bytes de um estrago anterior, o instalador só o
reconstrói **com prova** de que foi ele quem o criou. Sem prova, ele avisa e não
toca: um arquivo de donos vazio também é um jeito legítimo de alguém desligar a
revisão obrigatória, e adivinhar destruiria essa escolha.

## O que este pacote NÃO faz

- **A janela não fecha, ela estreita.** Entre a pergunta "esse destino é seguro?"
  e a escrita, nada impede alguém de transformar o destino num atalho naquele
  instante. Fechar isso de vez exigiria recursos que a linguagem em que o
  instalador é escrito não oferece. Está declarado.
- **O `doctor.sh` não foi convertido.** Ele é o terceiro programa que deveria
  usar a mesma função. Enquanto não for, o problema continua aberto lá dentro.
- **O contador de "lugares desprotegidos" não vai mostrar a melhora inteira.**
  Ele só reconhece a proteção quando ela está escrita *dentro do mesmo arquivo*
  — e o plano mandou, de propósito, pô-la numa biblioteca. Ensinar o contador a
  reconhecer essa forma é um trabalho à parte. Enquanto isso, o número cai
  menos do que a correção real: de 220 para 217 no total, e de 57 para 54 no
  instalador.

## Depois do land

O `Smoke Install` passa a rodar uma bateria a mais (~7 min locais). O
tempo-limite do job é uma **estimativa**: veja quanto o primeiro run real leva e
ajuste em cima desse número, nunca em cima de uma conta. Um tempo-limite curto
demais corta um run que estava verde e reporta o erro num passo inocente.

---

## Se algo der errado

| o que aconteceu | o que fazer |
|---|---|
| um editor abriu | Esc, `:q!`, Enter |
| «No pinentry» | `export GPG_TTY=$(tty); gpgconf --kill gpg-agent` e repita o passo 2 |
| o passo 1 parou dizendo que falta um arquivo OBRIGATÓRIO | chame o CEO — a metade de CI/docs não entrou; **não** remova o arquivo da lista |
| o passo 1 parou dizendo que um arquivo «mudou no HEAD vivo» | chame o CEO — alguém editou um destino enquanto o pacote esperava; a correção é re-derivar, nunca forçar |
| o passo 1 ou 2 parou dizendo que «o instrumento do censo MUDOU» | chame o CEO — a régua trocou; rodar o passo 1 de novo re-mede e diz o que atualizar |
| o passo 1 ou 3 parou dizendo que «o RATCHET do censo está sujo» | chame o CEO — falta regerar a lista de referência do contador; a mensagem traz o comando exato |
| o passo 2 parou dizendo que o último rail não é APPROVE | chame o CEO — falta uma rodada de revisão |
| o passo 3 parou com outro motivo | **não** rode o passo 4; mande a saída inteira para o CEO |
| o passo 4 parou depois do commit | o commit está salvo localmente; a mensagem diz o comando exato para reempurrar |

Nenhum passo é destrutivo antes de todos os portões passarem, e o ensaio
(passo 3) restaura a árvore byte a byte.

---

## Arquivos deste pacote (para o CEO)

| arquivo | papel |
|---|---|
| `C.patch` | o diff assinável (6 canônicos + 3 não-canônicos + docs de contagem) |
| `BASE-SHA.txt` | o commit contra o qual o patch foi gerado |
| `DESIGN-C.md` | o registro de desenho: contrato do predicado, gramática, escrita atômica, regra de evidência, censo, OQs |
| `PROPOSED-PATCH.md` | o registro que a revisão leu (o quê, por quê, medições) |
| `EXPECTED-BASELINE.txt` | os números DECLARADOS contra os quais o V-block compara, mais a fronteira de paths e o bloco AUTO derivado pelo finalize |
| `COMMIT-MSG-C.txt` | a mensagem de commit (usada com `-F`, sem editor) |
| `rail-round-*.md` | as rodadas de pair-rail, com claim → verificação → cura/pushback |
| `finalize-C.sh` | deriva o patch da sombra, re-baseia no HEAD vivo e escreve o bloco AUTO |
| `test-ceremony-scripts-C.sh` | harness: planta divergências e exige vermelho nomeado |
| `../OWNER-S329-C-SIGN.sh` | assinatura |
| `../OWNER-S329-C-LAND.sh` | land (G-PRE + G0..G5 + V1..V7 + commit + push) |
| `../wave-s329-C-approved.md` | o sentinel (Scope DERIVADO, nunca escrito à mão) |
