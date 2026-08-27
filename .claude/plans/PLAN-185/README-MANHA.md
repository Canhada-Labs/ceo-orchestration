# A manhã da S329 — um comando

> **Você não digita `git` em momento nenhum.** Os scripts commitam e empurram
> sozinhos. Nenhum editor abre. Se um abrir mesmo assim: aperte **Esc**, digite
> `:q!` e dê **Enter** (sai sem salvar, nada se perde) — e chame o CEO.

---

## O comando

Copie e cole a linha inteira no terminal:

```
cd /Users/joaocanhada/canhada-labs/ceo-orchestration && bash .claude/plans/PLAN-185/OWNER-S329-MORNING.sh
```

Só isso. Ele faz o resto. Com os **dois** pacotes leva cerca de **25 minutos**;
com um só, cerca de metade disso. Quase todo esse tempo é um único passo de
cada pacote — o que roda instalações e upgrades de verdade (§ *O passo 5/5
demora*).

Se quiser **ver o que aconteceria sem fazer nada** antes de valer, rode a mesma
linha com `--dry-run` no fim. É seguro: nada é assinado, aplicado ou empurrado.

```
cd /Users/joaocanhada/canhada-labs/ceo-orchestration && bash .claude/plans/PLAN-185/OWNER-S329-MORNING.sh --dry-run
```

---

## O que ele faz

A noite montou até dois **pacotes** de mudanças. Cada pacote precisa da sua
assinatura GPG para entrar no repositório. O script roda os dois na ordem certa,
**pula** o que não estiver pronto (avisando alto) e **para** no primeiro
problema de verdade.

| | Pacote | O que ele muda |
|---|---|---|
| 1º | **C** (PLAN-185) | Impede o instalador de escrever fora do diretório de destino quando encontra um atalho (*symlink*) apontando para fora, e valida o nome de usuário do GitHub antes de gravá-lo no arquivo de donos do código. |
| 2º | **E** (PLAN-169) | O `upgrade.sh` carregava, dentro dele mesmo, uma lista escrita à mão com **6** registros de hook — o arquivo de referência tem **47**. Projetos que atualizavam nunca recebiam os outros 41, e 5 das 6 cópias já estavam desatualizadas: o upgrade chegava num projeto certo e o deixava errado. Agora ele **lê** o arquivo de referência. |

**O pacote D não está nesta lista.** Ele foi assinado por você ontem e a
própria noite o landou (`b07be9b`). Não há o que fazer com ele.

**A ordem C → E não é uma dependência**, é economia: o passo 1 de cada pacote
encaixa as mudanças no estado atual do repositório, e rodar o C primeiro faz o
E já nascer encaixado no resultado dele.

**Pacote que não existir é pulado com um aviso grande.** A noite pode não ter
chegado nos dois. Isso é normal, não é erro, e não é culpa sua.

### Quando ele pula um pacote (aviso `ATENÇÃO`, e ele segue em frente)

Três situações fazem o script **pular** um pacote em vez de parar a manhã. Nas
três ele imprime um aviso grande, dizendo qual pacote e por quê, e **continua
para o outro** — um pacote que não pode entrar hoje não segura o que pode.

| O aviso diz | O que significa |
|---|---|
| `pacote X AUSENTE` | a noite não chegou a montá-lo |
| `pacote X INCOMPLETO` | a noite começou e não terminou |
| `a revisão cruzada NÃO aprovou` | um segundo modelo revisa cada pacote antes de você assinar, e a última rodada registrada não aprovou |

Nos três casos: **você não faz nada e não tenta de novo.** Repetir o comando
bate na mesma parede, porque o que falta é trabalho, não sorte. **Avise o CEO**
e siga com o resto normalmente. No fim, o `RESUMO` diz o que aconteceu com cada
pacote, e o script termina com o código `7` — que quer dizer exatamente isto:
"nada deu errado, mas nem tudo entrou".

---

## O que você vai ver, na ordem

1. **`S329 — CERIMÔNIA DA MANHÃ`** — a data, em que commit o repositório está,
   e a ordem.

2. **`EM DIA COM O GITHUB?`** — confere que ninguém empurrou nada que este
   computador ainda não tem. Se tiver, ele para: landar por cima daria um
   *push* recusado depois de gastar a sua assinatura à toa.

3. **`CHAVE DE ASSINATURA (GPG)`** — confere que a sua chave está acessível
   **antes** de começar, e não no meio.

4. **`PACOTES ENCONTRADOS`** — pacote com `✓` existe; com `—` está ausente.

5. **`ÁRVORE DE TRABALHO`** — confere que ninguém deixou arquivo modificado
   pela metade. Linhas soltas com nomes de arquivo novos (`untracked`) são
   normais e não entram em commit nenhum.

6. **Para cada pacote, cinco passos numerados:**

   | Passo | O que é | Quanto demora |
   |---|---|---|
   | 1/5 estado da árvore | confere que dá para assinar | instantâneo |
   | 2/5 re-base (`finalize`) | encaixa o pacote no estado atual do repositório | ~30 s |
   | 3/5 assinatura | **pede a senha da sua chave GPG** | você digita |
   | 4/5 ensaio (`--dry-run`) | roda os portões e desfaz tudo — é o ensaio geral | menos de 1 min |
   | 5/5 land | aplica, commita e empurra de verdade | **veja abaixo** |

   Depois do 5/5 ele confere que o commit chegou no GitHub e imprime o hash.

7. **`CI — O QUE ESPERAR AGORA`** — a lista dos últimos runs e o que deve ficar
   verde. Leia esta parte: ela diz o que é normal e o que não é.

8. **`RESUMO`** — uma linha por pacote, dizendo o que aconteceu com cada um.

### O passo 5/5 demora — e isso não é travamento

| Pacote | Quanto o 5/5 leva | Por quê |
|---|---|---|
| **C** | ~7 min | roda instalações de verdade contra atalhos maliciosos e nomes de usuário deformados — 50 verificações |
| **E** | ~10 min | roda uma instalação e dez upgrades de verdade — 36 verificações |

São números **medidos**, declarados pelos próprios pacotes (nos arquivos
`EXPECTED-BASELINE.txt`), não estimativas. O terminal pode ficar minutos sem
imprimir nada. **Deixe rodando** — interromper no meio é o único jeito de fazer
estrago. Se quiser conferir que ainda está vivo, abra outro terminal e olhe o
arquivo de log (§ *Onde estão os logs*).

---

## Se der vermelho

O script **para no primeiro problema** e imprime três coisas: o diagnóstico, o
que fazer, e **o comando exato para retomar de onde parou**. Nada do que já foi
landado se perde — você retoma, não recomeça.

O comando de retomada tem sempre esta cara (o script imprime o certo, com o
pacote certo — copie o dele, não este):

```
bash /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-185/OWNER-S329-MORNING.sh --from E
```

### Os vermelhos conhecidos

**1. `No pinentry` na hora de assinar.**
É o problema mais comum desta máquina: o programa que pede a senha da chave GPG
não subiu. **O script já tenta se recuperar sozinho uma vez.** Se ainda assim
falhar, rode você mesmo, no terminal:

```
export GPG_TTY=$(tty); gpgconf --kill gpg-agent
```

e depois o comando de retomada que ele imprimiu. Nada foi assinado, nada foi
aplicado — o script restaura o sentinel antes de sair.

**2. `não vou conseguir assinar`.**
Ele não encontrou a sua chave GPG. Confira no terminal com
`gpg --list-secret-keys`. Ele avisa disso **logo no começo** e para **antes** de
mexer em qualquer arquivo, de propósito.

**3. `o C.patch NÃO re-aplica` (ou `E.patch`) no passo 2/5.**
Quer dizer que os arquivos daquele pacote mudaram depois que ele foi montado.
**Não force nada, não tente de novo.** Copie a saída inteira e mande para o CEO.

**4. O ensaio (4/5) reprova.**
É exatamente para isso que o ensaio existe: ele reprovou antes de mexer em
nada. Se a mensagem falar em **`RESTAURAÇÃO INCOMPLETA`**, pare tudo e chame o
CEO — nesse caso pode ter ficado sujeira na árvore.

**5. `docs/threat-model.md estava modificado e eu REVERTI`.**
**Não é problema e você não precisa fazer nada.** Esse arquivo fica sujo
sozinho: o verificador de frescor do modelo de ameaças
(`.claude/scripts/check-threat-model-freshness.py`) troca a linha
`**Status:** accepted` por `**Status:** stale` como **efeito colateral de ser
executado** — ninguém editou nada. Como a assinatura exige árvore limpa, isso
travaria a cerimônia acusando um arquivo intocado.

O script confere que a diferença é **exatamente** essa troca de uma linha, e
nada mais, e só então reverte. Se a diferença for outra, ele **não reverte** —
para e mostra qual é, porque aí pode haver trabalho de verdade ali.

**6. `há modificações RASTREADAS na árvore` logo no começo.**
Alguém (ou algum processo da noite) deixou arquivo modificado sem commitar.
Não é para você resolver: mande a lista que ele imprimiu para o CEO.
A única exceção que ele resolve sozinho é a do item 5 acima.

**7. `este checkout está N commits ATRÁS do origin/main`.**
Alguém empurrou algo que este computador ainda não tem. **Não force.** Chame o
CEO — ele decide entre atualizar e refazer o pacote.

**8. `o commit foi criado mas NÃO chegou no origin`.**
O commit existe aqui, mas o push falhou (rede, ou alguém empurrou antes).
**Não force.** Chame o CEO.

---

## Como saber que deu certo

No fim, o script imprime o baseline esperado do CI. O certo é:

- **`Validate` pode continuar vermelho — e isso é esperado.** O portão de
  latência de hooks mede a velocidade do servidor do CI, não o seu código.
  Desde a S328 ele está em fase *advisory*: publica a medida e mantém os
  vereditos de hoje. **Nada nesta manhã deixa o `Validate` verde.** Quem faz
  isso é o **rerun de madrugada (03:03)**, ou a fase 2 do portão, depois de dez
  execuções darem dados para calibrar o limiar. Vermelho por essa razão não é
  problema novo nem regressão do que você landou.
- **`Smoke Install`**: se o pacote E entrou, esse run passa a demorar **bem
  mais** — ele ganhou um teste de ponta a ponta, e o tempo-limite do job subiu
  para 96 minutos. **Esse 96 é uma estimativa, não uma medida.** Veja quanto o
  **primeiro** run real leva e conte ao CEO: um tempo-limite curto demais corta
  um run que estava verde e reporta o erro num passo inocente.
- **Robô noturno de ownership**: falha em **exatamente** três casos —
  `OWN-0016`, `OWN-0024` e `OWN-0027`. Isso é por desenho.
  **Um resultado todo verde ali é motivo de parada, não de comemoração**:
  significa que a tabela de referência mudou sem ninguém ter decidido. Se isso
  acontecer, avise o CEO.

O CI roda sozinho a partir do push. Você não precisa disparar nada nem ficar
olhando: se algo reprovar, fica registrado e o CEO vê depois.

---

## Onde estão os logs

Tudo o que apareceu na tela fica salvo, com data e hora, em:

```
/Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-185/s329-ceremony-main/
```

- `morning-<data>-<hora>.log` — a execução inteira.
- `step-<pacote>-<etapa>.log` — a saída de cada passo, separada. É este que o
  CEO vai pedir quando algo der errado.

O caminho do log aparece na primeira linha da execução e de novo no fim.

---

## O que **não** fazer

- Não rode `git` — nem `add`, nem `commit`, nem `push`. Os scripts fazem.
- Não rode `git add -A` em hipótese nenhuma.
- Não abra editor nenhum, e não edite arquivo do repositório.
- Não commite nada **depois** de assinar: qualquer commit invalida a assinatura
  e o land para.
- Não interrompa o passo 5/5 porque "está demorando" — ele demora mesmo.

---

## Opções (só se o CEO pedir)

| Opção | Para que serve |
|---|---|
| `--dry-run` | Ensaio: mostra o que faria, sem fazer nada. |
| `--from C\|E` | Retoma a partir daquele pacote. |
| `--only C\|E` | Roda **só** aquele pacote. |
| `--ownership-e2e=run` | Roda na hora o teste longo de ownership, se o pacote pedir, em vez de adiar. |
| `--help` | Mostra tudo isso resumido no terminal. |

**Códigos de saída** (o número no fim diz onde parou, se você precisar reportar):
`0` tudo landado · `2` erro de digitação no comando · `3` pré-condição do
repositório · `7` terminou sem vermelho, mas algum pacote não existia ·
`1X` pacote C · `2X` pacote E — onde o segundo dígito é o passo (`1` re-base,
`2` assinatura, `3` ensaio, `4` land, `5` push, `6` estado do pacote,
`7` revisão cruzada não aprovada).
