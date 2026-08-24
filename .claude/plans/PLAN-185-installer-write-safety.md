---
id: PLAN-185
title: "Seguranca de escrita do installer: symlink pendente escreve FORA do target, e --github-owner corrompe CODEOWNERS para sempre"
status: draft
created: 2026-08-24
owner: CEO
depends_on: []
level: L3
budget_tokens: 60-120k (W0 10-20k; W1 30-60k; W2 20-40k)
budget_sessions: 1-2
context_risk: low
external_wait: "nenhum. Os dois defeitos estao REPRODUZIDOS; nao ha janela de dados nem decisao de terceiro a esperar."
eta_calendar: "W0 mesmo-dia (read-only). W1/W2 dependem de UMA cerimonia GPG do Owner (`scripts/install.sh` = canonico, oraculo = 1)."
tags: [seguranca, installer, symlink, escrita-fora-do-target, adopter, canonico]
---

# PLAN-185 — Seguranca de escrita do installer

> **Por que este plano existe separado.** Os dois defeitos abaixo foram
> reproduzidos em installs REAIS durante a S325 e estao registrados no
> `PLAN-183` §9.1/§9.2, que os classificou como "plano proprio, classe
> seguranca". O Owner ratificou essa disposicao em 2026-08-24. A razao de nao
> serem uma wave do PLAN-183: aquele plano esta travado em tres OQs abertas, e
> subordinar correcao de escrita-fora-do-target a uma fila bloqueada e o
> oposto de tratar seguranca como seguranca.

## 1. Os dois defeitos, com a reproducao

### F1 — escrita FORA do `$TARGET` via symlink pendente (GRAVE)

`install_docs_template` guarda o destino com `[[ -e "$dst" ]]`
(`scripts/install.sh:1466-1472`). O teste `-e` **segue** o symlink: um link
**pendente** faz `-e` dar FALSO, e o `cp` seguinte escreve **atraves** do
link — fora da arvore do target.

**Reproduzido:** plantar um symlink pendente de `docs/rotation-log.md`
apontando para `/tmp/<dir>/pwned.md` num target limpo e rodar o install em
modo `maintainer` ⇒ `exit 0`, log `COPIED:`, e o arquivo escrito FORA do
target. O installer reporta sucesso.

**A defesa ja existe no MESMO arquivo, para outra arvore**
(`install.sh:2139-2159`) e esta ausente aqui. Isso importa para o desenho da
cura: nao e mecanismo novo, e a mesma guarda deixando de ser aplicada num
segundo sitio — a classe "ramo local" que o `CLAUDE.md` §4 proibe, na sua
forma por OMISSAO.

### F2 — `--github-owner` com `/` aborta e deixa CODEOWNERS de 0 bytes, para sempre (GRAVE)

O `sed` de `install.sh:1508` interpola o valor da flag **sem escapar o
delimitador**:

```
sed "s/{{OWNER_HANDLE}}/$GITHUB_OWNER/g" "$codeowners_src" > "$dst"
```

**Reproduzido:** um valor contendo `/` ⇒ `exit 1`,
`sed: bad flag in substitute command`, e o destino com **0 bytes**. O
redirecionamento `>` cria o arquivo ANTES do `sed` falhar, entao o vazio
sobrevive ao aborto.

O que transforma isso de erro de uso em defeito permanente: o arquivo de 0
bytes passa a ser **EXISTS-skipped para sempre** (`:1504`) — nenhum install
ou upgrade posterior o corrige, e o adopter fica com um CODEOWNERS vazio que
o GitHub trata como "sem donos".

## 2. Escopo, e o que fica FORA

Dentro: as duas curas em `scripts/install.sh`, os testes que as provam, e o
censo da CLASSE (nao so dos dois sitios).

Fora, declarado:
- **F3** (os dois ramos do CODEOWNERS nao serem exclusivos no tempo) fica no
  `PLAN-183` §9.3 — e defeito de paridade, nao de escrita.
- Qualquer coisa que dependa das tres OQs do `PLAN-183`. Este plano nao toca
  a wave de paridade.

## 3. Waves

### W0 — censo da CLASSE antes de curar um sitio (read-only, sem cerimonia)

A licao que este repo ja pagou duas vezes (PLAN-182: 16 modulos; PLAN-167:
`_ownership_verdict`): curar os dois sitios reportados e deixar a classe viva
converte defeito latente em defeito vivo na proxima wave que alargar o
dominio de entrada.

- [ ] `[P0]` Censo de TODOS os sitios que decidem escrita por teste de
      existencia que segue symlink (`-e`, `-f`, `-d` sem `-L`), em
      `scripts/*.sh`, com o veredito por sitio: guardado / desguardado /
      nao-aplicavel.
      Check: o censo e um SCRIPT versionado, nao uma medicao de sessao, e
      roda em CI; ele lista >= 2 sitios (os dois conhecidos) e falha se um
      sitio desguardado novo aparecer. Contagem 0 REPROVA — significa que o
      padrao de busca esta errado, nao que o repo esta limpo.
- [ ] `[P0]` Censo de toda interpolacao de valor de flag em `sed`/`awk` sem
      escape de delimitador, mesmo escopo.
      Check: idem — script versionado, >= 1 sitio (o `:1508`), e um controle
      POSITIVO que planta uma interpolacao insegura numa arvore-sombra e
      exige VERMELHO.

### W1 — a cura de F1 (canonico: exige cerimonia)

- [ ] `[P0]` `install_docs_template` passa a recusar destino que seja
      symlink, pendente ou nao, reusando a guarda que `install.sh:2139-2159`
      ja aplica na outra arvore — nao uma guarda nova e paralela.
      Check: fixture com symlink PENDENTE para fora do target ⇒ o install
      FALHA de forma nomeada e o arquivo externo **nao existe** apos o run
      (assercao nos BYTES do alvo externo, nao no exit code — o defeito
      atual sai `exit 0`); fixture com symlink RESOLVIDO para fora ⇒ mesma
      recusa; fixture sem symlink ⇒ install inalterado (controle de
      nao-regressao). O teste fica VERMELHO com a guarda revertida.
- [ ] `[P1]` A guarda e aplicada por UMA funcao compartilhada, e o censo da
      W0 passa a ter zero sitios desguardados.
      Check: `grep` prova que os dois sitios chamam a MESMA funcao; e a prova
      de uso e comportamental — reverter a funcao deixa AMBOS os testes
      vermelhos, nao apenas um.

### W2 — a cura de F2 (canonico: mesma cerimonia)

- [ ] `[P0]` A substituicao do handle deixa de ser `sed` com delimitador
      interpolavel: valor validado contra um conjunto fechado de caracteres
      de handle antes de qualquer escrita, e a escrita e ATOMICA (arquivo
      temporario + `mv`), para que um aborto nao deixe destino de 0 bytes.
      Check: TRES fixtures — (a) `--github-owner 'a/b'` ⇒ falha nomeada e
      **nenhum** `.github/CODEOWNERS` criado (contagem de bytes do path
      inexistente, nao so o exit); (b) `--github-owner` valido ⇒ arquivo com
      1442 bytes, 33 linhas, o handle presente >= 1 vez, e SO DEPOIS
      `grep -c '{{OWNER_HANDLE}}' == 0` (a negativa sozinha e satisfeita por
      um arquivo vazio — convergencia C2 do debate da W5-b); (c) um destino
      de 0 bytes pre-existente ⇒ o install NAO o trata como EXISTS-skip, e o
      corrige. As tres ficam VERMELHAS com a cura revertida.

## Acceptance criteria

- [ ] AC-1 `[P0]` F1 nao reproduz: a reproducao documentada em §1 sai com
      falha nomeada e zero bytes escritos fora do target.
      Check: o teste da W1 roda verde, e roda VERMELHO com a guarda
      revertida por `git stash` do plant.
- [ ] AC-2 `[P0]` F2 nao reproduz, e o estado corrompido e RECUPERAVEL: um
      target que ja tenha um CODEOWNERS de 0 bytes e curado por um install
      subsequente.
      Check: as tres fixtures da W2 verdes; a (c) e a que prova a
      recuperabilidade e e a que falta hoje.
- [ ] AC-3 `[P0]` A CLASSE esta fechada, nao os dois sitios: o censo da W0
      esta em CI e sai zero sitios desguardados.
      Check: o censo roda no per-PR; plantar um sitio desguardado numa
      arvore-sombra o deixa VERMELHO nomeando o path.
- [ ] AC-4 `[P1]` A cerimonia foi UMA, cobrindo W1+W2: sentinel na forma
      VIVA, Scope DERIVADO do patch (nunca enumerado a mao — a S324 errou
      isso duas vezes), e `touched − scope = ∅` verificado antes do commit.
      Check: `_sentinel_grants_path` devolve True para cada path canonico
      tocado, e o gate de escopo do land sai zero.

## 4. Cerimonia

`scripts/install.sh` e **CANONICO** (oraculo `--is-canonical` = 1), logo W1 e
W2 exigem sentinel assinado pelo Owner. A W0 e read-only e nao exige nada.

Recomendacao do CEO: **uma** cerimonia cobrindo W1+W2, porque tocam a mesma
funcao e a mesma superficie — duas cerimonias pagariam o custo em dobro para
o mesmo Scope.

## 5. Limitacao honesta

Os dois defeitos foram reproduzidos por mim em installs reais, mas **nao ha
evidencia de exploracao**. F1 exige que algo plante um symlink no target
antes do install — num fluxo normal o adopter e quem controla o target, entao
o vetor realista e um target compartilhado ou um repositorio clonado de
terceiro, nao um ataque remoto. Isso nao reduz a gravidade da cura (o
installer nao deve escrever fora do diretorio que recebeu), mas situa a
urgencia: e correcao de robustez com blast radius alto, nao incidente.
