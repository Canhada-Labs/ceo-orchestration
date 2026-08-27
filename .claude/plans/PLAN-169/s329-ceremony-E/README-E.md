# Pacote E — o que você faz de manhã (4 comandos, nenhum editor)

Este pacote muda **cinco arquivos**, dois dos quais exigem a sua assinatura.
Você não digita `git` em momento nenhum. Se algum editor abrir (tela azul/preta
com texto), aperte **Esc**, digite **`:q!`** e **Enter** — sai sem salvar, nada
se perde.

---

## Antes de começar: uma coisa que este pacote NÃO precisa

Ao contrário do pacote B, aqui **não existe uma "outra metade"** a commitar
antes. O patch é atômico: a cura, os dois testes que a vigiam e o registro de
desenho entram juntos. Se eles entrassem em commits separados, haveria uma
janela em que a cura estaria no repositório sem nada que a proteja.

O que os scripts **verificam sozinhos** antes de deixar você assinar: que o
`jq` desta máquina aceita a flag `--slurpfile` (a cura depende dela), e que a
última rodada de revisão cruzada registrada terminou em **APPROVE**. Se algo
faltar, eles param e dizem exatamente o quê. **Não force nada** — chame o CEO.

---

## Os 4 comandos, em ordem

Copie e cole cada linha inteira, uma de cada vez, e espere terminar antes da
seguinte.

### 1. Montar o pacote sobre o estado atual do repositório

```
bash .claude/plans/PLAN-169/s329-ceremony-E/finalize-E.sh
```

O trabalho foi feito numa cópia separada do repositório, e o repositório andou
desde então. Este passo alinha os dois e roda uma bateria curta (uns 30 s). Se
ele disser **«NADA a fazer»**, ótimo — está tudo alinhado, siga para o passo 2.

### 2. Assinar

```
bash .claude/plans/PLAN-169/OWNER-S329-E-SIGN.sh
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
bash .claude/plans/PLAN-169/OWNER-S329-E-LAND.sh --dry-run
```

Roda os portões rápidos e **desfaz tudo** no fim. Leva menos de um minuto. Se
algo estiver errado, ele para aqui, com o motivo escrito. Só siga para o 4 se
este terminar verde.

### 4. Aplicar de verdade (commita e empurra)

```
bash .claude/plans/PLAN-169/OWNER-S329-E-LAND.sh
```

**Este demora cerca de 12 minutos** — ele roda uma instalação e dez upgrades
de verdade, que é a única prova de que a cura funciona de ponta a ponta. Deixe
rodando. No fim ele mostra o commit criado, empurra para o `main` e lista os
últimos runs de CI.

---

## O que este pacote faz

Quando você atualiza o framework num projeto que já o usa, o `upgrade.sh`
precisa registrar os "hooks" — os pequenos programas de governança que rodam
automaticamente. Até hoje ele carregava, **dentro dele mesmo**, uma lista
escrita à mão com **6** desses registros. O arquivo de referência do framework
tem **47** — e o perfil `--ceremony user`, que omite de propósito os hooks que
bloqueiam ou exigem GPG, tem o seu próprio arquivo com **20**. O upgrade passa a
usar o arquivo da cerimônia do projeto (a revisão cruzada da manhã pegou que ele
usava sempre o de 47, o que transformaria um projeto `user` em `maintainer`).

Consequências medidas:

- Um projeto instalado numa versão antiga **nunca recebia** nenhum hook novo
  que não fosse um dos seis. O caso que revelou isso foi o
  `check_ledger_checkpoint.py`, que nenhum upgrade jamais registrou.
- Pior: **5 das 6 cópias já estavam desatualizadas** em relação ao original. E
  como o código *sobrescrevia* o que encontrava, o upgrade chegava num projeto
  correto e o deixava errado.

A cura tira a lista de dentro do programa: ele passa a **ler o arquivo de
referência** e registrar o que estiver lá. E muda a regra de sobrescrever para
**acrescentar**: o que já existe é preservado exatamente como está — se você
customizou um registro, ele fica.

Junto vai o teste que vigia isso (e a linha no CI que o faz rodar — sem ela o
teste existiria e nunca executaria) e um segundo teste que fica **vermelho se
alguém puser um nome de hook de volta dentro daquela função**. É essa segunda
peça que impede o problema de voltar.

## O que este pacote NÃO faz

- **Quem removeu um hook de propósito vai recebê-lo de volta** no próximo
  upgrade. Hoje o único jeito de recusar é desligar o merge inteiro. Se você
  quiser um jeito de recusar hook por hook, isso é uma decisão sua e vira uma
  wave própria — está registrado como **OQ-E1**.
- **Ninguém conserta um registro deformado.** Se um projeto deformou um
  registro, ele fica deformado: o `doctor.sh` hoje não repara registros de
  hook. Não é uma piora (antes só 6 de 47 eram tocados), mas também não é uma
  solução — está registrado como **OQ-E6**.

## Depois do land

O `Smoke Install` passa a rodar um teste a mais. O tempo-limite do job foi de
83 para 126 minutos, e esse 126 é uma **estimativa**: veja quanto o primeiro run
real leva e ajuste em cima desse número, nunca em cima de uma conta. Um
tempo-limite curto demais corta um run que estava verde e reporta o erro num
passo inocente.

---

## Se algo der errado

| o que aconteceu | o que fazer |
|---|---|
| um editor abriu | Esc, `:q!`, Enter |
| «No pinentry» | `export GPG_TTY=$(tty); gpgconf --kill gpg-agent` e repita o passo 2 |
| o passo 1 parou dizendo que um arquivo do pacote «mudou no HEAD vivo» | chame o CEO — alguém editou um destino enquanto o pacote esperava; a correção é re-derivar, nunca forçar |
| o passo 2 parou dizendo que o último rail não é APPROVE | chame o CEO — falta uma rodada de revisão |
| o passo 3 parou com outro motivo | **não** rode o passo 4; mande a saída inteira para o CEO |
| o passo 4 parou depois do commit | o commit está salvo localmente; a mensagem diz o comando exato para reempurrar |

Nenhum passo é destrutivo antes de todos os portões passarem, e o ensaio
(passo 3) restaura a árvore byte a byte.

---

## Arquivos deste pacote (para o CEO)

| arquivo | papel |
|---|---|
| `E.patch` | o diff assinável (5 paths, 2 canônicos) |
| `BASE-SHA.txt` | o commit contra o qual o patch foi gerado |
| `DESIGN-E.md` | o registro de desenho: antes/depois, achados, OQs, rodada de rail |
| `PROPOSED-PATCH.md` | o registro que a revisão leu (o quê, por quê, medições) |
| `EXPECTED-BASELINE.txt` | os números DECLARADOS contra os quais o V-block compara |
| `COMMIT-MSG-E.txt` | a mensagem de commit (usada com `-F`, sem editor) |
| `rail-round-*.md` | as rodadas de pair-rail, com claim → verificação → cura/pushback |
| `finalize-E.sh` | deriva o patch da sombra e o baseia no HEAD vivo |
| `test-ceremony-scripts-E.sh` | harness: planta divergências e exige vermelho nomeado |
| `../OWNER-S329-E-SIGN.sh` | assinatura |
| `../OWNER-S329-E-LAND.sh` | land (G-PRE + G0..G5 + V1..V7 + commit + push) |
| `../wave-s329-E-approved.md` | o sentinel (Scope DERIVADO, nunca escrito à mão) |
