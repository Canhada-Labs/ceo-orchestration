# A manhã da S328 — um comando

> **Você não digita `git` em momento nenhum.** Os scripts commitam e empurram
> sozinhos. Nenhum editor abre. Se um abrir mesmo assim: aperte **Esc**, digite
> `:q!` e dê **Enter** (sai sem salvar, nada se perde) — e chame o CEO.

---

## O comando

Copie e cole a linha inteira no terminal:

```
cd /Users/joaocanhada/canhada-labs/ceo-orchestration && bash .claude/plans/PLAN-183/OWNER-S328-MORNING.sh
```

Só isso. Ele faz o resto e leva de **10 a 40 minutos**, dependendo de quantos
pacotes a noite conseguiu montar.

Se quiser **ver o que aconteceria sem fazer nada** antes de valer, rode a mesma
linha com `--dry-run` no fim. É seguro: nada é assinado, aplicado ou empurrado.

```
cd /Users/joaocanhada/canhada-labs/ceo-orchestration && bash .claude/plans/PLAN-183/OWNER-S328-MORNING.sh --dry-run
```

---

## O que ele faz

A noite montou até quatro **pacotes** de mudanças. Cada pacote precisa da sua
assinatura GPG para entrar no repositório. O script roda os quatro na ordem
certa e para no primeiro problema.

| | Pacote | O que ele muda |
|---|---|---|
| 1º | **B** (PLAN-169) | Passa a **medir** a velocidade dos hooks contra uma tarefa de referência na mesma máquina, para distinguir "servidor do CI lento" de "regressão de verdade". Nesta primeira fase a medida é só **publicada**: não muda veredito nenhum — e portanto **não deixa o CI verde** (é o que o próprio pacote diz, em `s328-ceremony-B/README-B.md`). |
| 2º | **A** (PLAN-183) | Fecha a W5-b: marca o ADR-194 como aceito e conserta uma comparação que confundia `.github/CODEOWNERS` com `.github/CODEOWNERS.template`. |
| 3º | **C** (PLAN-185) | Impede o instalador de escrever fora do diretório de destino e valida o handle do GitHub antes de gravar. |
| 4º | **D** (PLAN-179) | Registro de checkpoint de trabalho (ledger) — três ações novas de auditoria. |

**A ordem importa e o script cuida disso.** O B vem primeiro porque é o menor
e o mais independente. O C mexe nos mesmos arquivos do A e do B, então só entra
depois dos dois — **se A ou B não existirem, o C não roda**, e o script diz
isso com todas as letras em vez de tentar e quebrar.

**Pacote que não existir é pulado com um aviso.** A noite pode não ter chegado
em todos. Isso é normal e não é erro.

---

## O que você vai ver, na ordem

1. **`PLANO DA MANHÃ`** — a data, em que commit o repositório está, e a lista
   dos pacotes encontrados. Pacote com `✓` existe; com `—` está ausente.

2. **`ÁRVORE DE TRABALHO`** — confere que ninguém deixou arquivo modificado
   pela metade. Linhas soltas com nomes de arquivo novos (`untracked`) são
   normais e não entram em commit nenhum.

3. **Para cada pacote, cinco passos numerados:**

   | Passo | O que é | Quanto demora |
   |---|---|---|
   | 1/5 estado da árvore | confere que dá para assinar | instantâneo |
   | 2/5 re-base (`finalize`) | encaixa o pacote no estado atual do repositório | segundos a 2 min |
   | 3/5 assinatura | **pede a senha da sua chave GPG** | você digita |
   | 4/5 ensaio (`--dry-run`) | roda tudo e desfaz — é o ensaio geral | 1 a 10 min |
   | 5/5 land | aplica, commita e empurra de verdade | 1 a 10 min |

   Depois do 5/5 ele confere que o commit chegou no GitHub e imprime o hash.

4. **`CI — O QUE ESPERAR AGORA`** — a lista dos últimos runs e o que deve ficar
   verde. Leia esta parte: ela diz o que é normal e o que não é.

5. **`RESUMO`** — uma linha por pacote, dizendo o que aconteceu com cada um.

---

## Se der vermelho

O script **para no primeiro problema** e imprime três coisas: o diagnóstico, o
que fazer, e **o comando exato para retomar de onde parou**. Nada do que já foi
landado se perde — você retoma, não recomeça.

O comando de retomada tem sempre esta cara (o script imprime o certo):

```
bash /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-183/OWNER-S328-MORNING.sh --from A
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

**2. `o A.patch NAO re-aplica` (ou `B.patch`, `C.patch`) no passo 2/5.**
Quer dizer que os arquivos daquele pacote mudaram depois que ele foi montado.
**Não force nada, não tente de novo.** Copie a saída inteira e mande para o CEO.

**3. O ensaio (4/5) reprova.**
É exatamente para isso que o ensaio existe: ele reprovou antes de mexer em
nada. Se a mensagem falar em **`RESTAURAÇÃO INCOMPLETA`**, pare tudo e chame o
CEO — nesse caso pode ter ficado sujeira na árvore.

**4. `docs/threat-model.md estava modificado e eu REVERTI`.**
**Não é problema e você não precisa fazer nada.** Esse arquivo fica sujo
sozinho: o verificador de frescor do modelo de ameaças
(`.claude/scripts/check-threat-model-freshness.py`) troca a linha
`**Status:** accepted` por `**Status:** stale` como **efeito colateral de ser
executado** — ninguém editou nada. Como a assinatura exige árvore limpa, isso
travaria a cerimônia acusando um arquivo intocado.

O MORNING confere que a diferença é **exatamente** essa troca de uma linha, e
nada mais, e só então reverte. Se a diferença for outra, ele **não reverte** —
para e mostra qual é, porque aí pode haver trabalho de verdade ali.

**5. `há modificações RASTREADAS na árvore` logo no começo.**
Alguém (ou algum processo da noite) deixou arquivo modificado sem commitar.
Não é para você resolver: mande a lista que ele imprimiu para o CEO.
A única exceção que ele resolve sozinho é a do item 4 acima.

**5. `o commit foi criado mas NÃO chegou no origin`.**
O commit existe aqui, mas o push falhou (rede, ou alguém empurrou antes).
**Não force.** Chame o CEO.

---

## O teste longo de ownership

O pacote A traz um teste que demora cerca de **25 minutos**. Por padrão o
script **adia** esse teste (`defer`): quem confirma o resultado é o robô noturno
do CI, que roda por volta das 04h (horário de Brasília) do dia seguinte e
compara o conjunto exato de falhas esperadas.

Isso é seguro e é o padrão. Se o CEO pedir para rodar na hora, use:

```
bash /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-183/OWNER-S328-MORNING.sh --ownership-e2e=run
```

---

## Como saber que deu certo

No fim, o script imprime o baseline esperado do CI. O certo é:

- **`Validate` pode continuar vermelho — e isso é esperado, com ou sem o
  pacote B.** O B entra em fase advisory: publica a medida nova e mantém os
  vereditos de hoje. **Ele não deixa o CI verde**, e o script diz isso na
  cara. Quem deixa é o **rerun de madrugada (03:03)**, ou a fase 2 do gate,
  depois de dez execuções darem dados para calibrar o limiar. Vermelho por
  essa razão não é problema novo nem regressão do land.
- **`Smoke Install` verde.**
- **Robô noturno de ownership**: falha em **exatamente** três casos —
  `OWN-0016`, `OWN-0024` e `OWN-0027`. Isso é por desenho.
  **Um resultado todo verde ali é motivo de parada, não de comemoração**:
  significa que a tabela de referência mudou sem ninguém ter decidido. Se isso
  acontecer, avise o CEO.

---

## Onde estão os logs

Tudo o que apareceu na tela fica salvo, com data e hora, em:

```
/Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-183/s328-ceremony-main/
```

- `morning-<data>-<hora>.log` — a execução inteira.
- `step-<pacote>-<etapa>.log` — a saída de cada passo, separada. É este que o
  CEO vai pedir quando algo der errado.

O caminho do log aparece na primeira linha da execução e de novo no fim.

---

## Opções (só se o CEO pedir)

| Opção | Para que serve |
|---|---|
| `--dry-run` | Ensaio: mostra o que faria, sem fazer nada. |
| `--from B\|A\|C\|D` | Retoma a partir daquele pacote. |
| `--only B\|A\|C\|D` | Roda **só** aquele pacote. |
| `--ownership-e2e=run` | Roda o teste de 25 min dentro do land, em vez de adiar. |
| `--help` | Mostra tudo isso resumido no terminal. |

**Códigos de saída** (o número no fim diz onde parou, se você precisar reportar):
`0` tudo landado · `2` erro de digitação no comando · `3` pré-condição do
repositório · `7` terminou sem vermelho, mas algum pacote não existia ·
`1X` pacote B · `2X` pacote A · `3X` pacote C · `4X` pacote D — onde o segundo
dígito é o passo (`1` re-base, `2` assinatura, `3` ensaio, `4` land, `5` push).
