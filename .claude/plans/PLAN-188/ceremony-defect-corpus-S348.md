---
plan: PLAN-188
session: S348
date: 2026-09-07
status: corpus
---

# Corpus de defeitos do molde de cerimônia (S348)

## §0 — Resumo

Quatro pacotes canônicos travaram na noite S347→S348 no mesmo lugar: scripts de
cerimônia artesanais (`SIGN` / `LAND` / `finalize` / harness), clonados de um
molde. Este corpus separa o que o rail achou naqueles clones do que **vive hoje**
nos scripts JÁ ASSINADOS do repositório, para que o toolkit do PLAN-188 feche
cada classe uma vez, com controle vermelho, em vez de a reencontrar por clone.

| dimensão | valor |
|---|---|
| classes com ocorrência VIVA no repo (§1) | 12 |
| classes sem ocorrência viva, só nos packs (§2) | 5 |
| classes já curadas no vivo, por clone (§2b) | 2 |
| scripts `OWNER-*.sh` rastreados examinados | 53 |
| harnesses `test-ceremony-*.sh` rastreados | 14 |
| packs de origem dos achados | 4 (`p169-w41-quota-resume`, `p183-w1-pointer`, `w6-adapter`, `w4b-ci-matrix`) |

O achado que dá o tamanho do problema está no registro
`<PK>/p169-w41-quota-resume/rail-materials-round-12.md`: **25 achados, 7 deles
P1, e os sete estão nos gates de assinatura** — o código que decide se uma
assinatura pode prosseguir. O próprio registro escreve a conclusão que este
corpus serve: *«a decisão material que espera o Owner é se os scripts de
cerimônia — 120 KB de bash implementando o seu próprio leitor de registro de
rail, parser de trailer, congelador de mensagem e guard de push — devem
continuar sendo remendados achado a achado, ou substituídos pelo toolkit
compartilhado que o PLAN-188 foi rascunhado para prover.»*

Raiz comum das doze classes de §1: **cada gate implementa o seu próprio leitor**
(de registro de rail, de campo do sentinel, de estado da árvore, de mensagem de
commit), e cada leitor falha PARA CIMA — entrada que ele não consegue ler vira
«tudo bem» em vez de recusa nomeada.

## §1 — Tabela mestra (ocorrência VIVA no repositório)

Todo `file:line` abaixo foi LIDO nesta sessão. Raiz do repo escrita como
`<ROOT>`; diretório dos packs como `<PK>`.

| id | classe | mecanismo | ocorrências vivas (≤3) | achado por | cura no toolkit | controle positivo |
|---|---|---|---|---|---|---|
| **CM-01** | eleição do «último» registro por `-gt` sobre sufixo sem teto | o número vem do basename sem limite de comprimento; `[ "$_n" -gt "$LAST_N" ]` com valor acima do inteiro do shell devolve rc 2, o `if` engole sob `set -e`, e o registro sai da eleição em silêncio | `<ROOT>/.claude/plans/PLAN-186/OWNER-S343-W4A-SIGN.sh:227`; `PLAN-169/OWNER-S338-FABLE51-SIGN.sh:225`; `PLAN-179/OWNER-S335-179CLOSE-SIGN.sh:225` (9 arquivos) | `p183-w1-pointer`, `rail-materials-round-1.md` F1 (reproduzido: «`-gt` disse NÃO (rc=2)») | `lib.sh` limita o comprimento do sufixo ANTES da comparação e `die` nomeado; o conjunto de registros vem PINADO por sha256 do manifesto, não de um glob | um `rail-round-9223372036854775808.md` com `CHANGES-REQUESTED` ao lado de um `rail-round-1.md` com `APPROVE`: o gate tem de RECUSAR, não eleger o `1` |
| **CM-02** | `tr -d '[:space:]'` apaga espaço INTERNO | o normalizador do veredito remove todo espaço, então `Rail-Verdict: AP PROVE` vira `APPROVE` e passa pela «igualdade exata» | `PLAN-186/OWNER-S343-W4A-SIGN.sh:230`; `PLAN-169/OWNER-S338-FABLE51-LAND.sh:389`; `PLAN-185/OWNER-S329-C-SIGN.sh:230` (35 arquivos) | `p183-w1-pointer`, `rail-materials-round-1.md` F2 (`'AP PROVE' -> APPROVE`) | `tr -d '\r'` + aparo só das BORDAS; o espaço interno sobrevive e reprova | três pernas: `AP PROVE` reprova; `APPROVE com ressalvas` reprova; `APPROVE` com CRLF e bordas continua PASSANDO (uma cura que reprova o caso bom é pior que o defeito) |
| **CM-03** | `grep -m1 '^Rail-Verdict:'` lê só o PRIMEIRO veredito | um registro com `APPROVE` seguido de `REJECT` passa; o leitor não rejeita duplicata nem distingue um exemplo citado do veredito | `PLAN-186/OWNER-S343-W4A-SIGN.sh:230`; `PLAN-169/OWNER-S331-F-SIGN.sh:224`; `PLAN-185/OWNER-S329-C-SIGN.sh:230` (10 sítios) | `p169-w41-quota-resume`, `rail-materials-round-12.md` #3; confirmado na nota `S348-p169-r3` do `STATE.md` daquele pack sobre `OWNER-S344-QR-SIGN.sh:364` | a contagem de linhas `^Rail-Verdict:` tem de ser **1** E igual a `APPROVE`; duas linhas ⇒ recusa nomeada | registro com `APPROVE` na linha 3 e `REJECT` na linha 40 ⇒ recusa; registro com uma só linha `APPROVE` ⇒ passa |
| **CM-04** | produtor que morre não chega ao gate | `while … done < <(git status …)`: a falha do produtor não propaga; o laço termina com a variável VAZIA e o gate lê «árvore limpa». Mesma forma em `git status \| grep -c -v '^??' \|\| true`, onde o `\|\| true` apaga a diferença entre «não achou» e «morreu» | `PLAN-186/OWNER-S343-W4A-SIGN.sh:164` e `:117`; `PLAN-169/OWNER-S338-FABLE51-SIGN.sh:163` (30 arquivos com a forma `< <(git status --porcelain=v1 -z)`) | `p183-w1-pointer`, `rail-materials-round-1.md` F3 («laço terminou com DIRTY vazio e rc=0 — VÁCUO») | o `git status` escreve em arquivo temporário cujo **rc é conferido**; o laço lê o arquivo. Um gate que não conseguiu PERGUNTAR não pode responder «está tudo bem» | `git` substituído por stub com rc≠0 no `PATH`: o gate tem de recusar por nome, e hoje ele responde «árvore limpa» |
| **CM-05** | `\| head -N` sob `pipefail` mata o produtor (SIGPIPE 141) | com entrada grande o `head` fecha o pipe antes de o produtor terminar; sob `pipefail` a condição de recusa vira falsa e o detector falha PARA CIMA | `PLAN-186/OWNER-S343-W4A-SIGN.sh:118`; `PLAN-169/OWNER-S328-B-SIGN.sh:89` e `:243`; `PLAN-169/OWNER-S329-E-LAND.sh:115` | `p169`, `rail-materials-round-12.md` #1 (P1, reproduzido com ~1 MiB de padding: «um produtor Git real confirmou exit 141»); nota `S348-p169-r3` sobre `OWNER-S344-QR-SIGN.sh:328` | `sed -n '1,Np'` no lugar do `head`, ou ler para variável antes de filtrar; nunca `\| head \|\| true` num gate | plantar entrada de ~1 MiB com o marcador nas 5 primeiras linhas: o detector tem de continuar disparando. **Limite honesto:** nos 4 sítios vivos os arquivos são pequenos hoje — a classe morde quando a entrada cresce, e é por isso que ela entra no molde compartilhado |
| **CM-06** | o trailer `Pair-Rail-Reviewed:` é checado só como «não TO-FILL» | o `LAND` casa a string `Pair-Rail-Reviewed: TO-FILL` e nada mais; o trailer nunca é ligado ao CONJUNTO de registros, e o estampador conta o MÁXIMO em vez do conjunto | `PLAN-169/OWNER-S338-FABLE51-LAND.sh:953-957` (13 LANDs com a mesma forma); nenhum uso de `git interpret-trailers` em nenhum dos 53 scripts | `w6-adapter`, `rail-materials-round-12.md` F1 (as duas lanes acharam sozinhas: registros `1..11,13,14` e `1..8,10,11` com o trailer afirmando «SUJEITO 1-14, MATERIAIS 1-11»); `p169` r12 #5 (um trailer com espaço antes dos dois-pontos é lido pelo Git e ignorado pelos dois gates) | o trailer é GERADO do conjunto pinado no manifesto; `land.sh` compara CONJUNTOS nos dois sentidos e exige contiguidade `1..LAST_N` | remover `rail-round-7.md` de um conjunto `1..9`: o LAND tem de recusar nomeando o buraco. Segunda perna: trailer com `Pair-Rail-Reviewed : …` (espaço antes do `:`) ⇒ recusa |
| **CM-07** | nenhuma verificação da mensagem DEPOIS do commit | os 14 LANDs que fazem `git commit -F` congelam a mensagem antes e **nunca a releem**; um hook `commit-msg` pode mudar o arquivo e o argumento, e nada re-confere | busca por `%B` e por `commit-msg` nos 14 `OWNER-*LAND.sh` que commitam: **0 ocorrências** — a ausência é a ocorrência | `p169`, `rail-materials-round-12.md` #6 (P1) | depois do commit, `git log -1 --format=%B` é comparado byte a byte com os bytes congelados; divergência ⇒ recusa com o commit ainda local | um hook `commit-msg` que acrescenta uma linha: o LAND tem de recusar em vez de empurrar. Hoje ele empurra |
| **CM-08** | push não pinado ao commit verificado | `git push "$PUSH_REMOTE" "HEAD:$PUSH_BRANCH"` resolve `HEAD` no instante do push, não no da verificação: avançar o HEAD entre os dois entrega um commit que nenhum gate viu | `PLAN-169/OWNER-S338-FABLE51-LAND.sh:977` (verificação em `:965`, push em `:977`); mesma forma em 15 arquivos | `p169`, `rail-materials-round-12.md` #7 (P1) | `git push <remote> "$NEW_SHA:refs/heads/<branch>"`, com remoto e refspec NOMEADOS e `core.hooksPath` verificado — invariante 6 do plano, que já pede o pin ao destino | avançar o HEAD com um commit vazio entre a verificação e o push: o push tem de recusar. Hoje entrega o commit novo |
| **CM-09** | janela entre a verificação GPG e o staging | o `.asc` e o sentinel são verificados no G1 a partir da ÁRVORE DE TRABALHO e re-lidos, sem nenhum digest congelado, no passo de staging — 550 linhas e 15 gates depois, com o patch já APLICADO no meio | `PLAN-169/OWNER-S338-FABLE51-LAND.sh:368` e `:376` (G1) contra `:911` (passo S); o patch é aplicado em `:614`. Único `shasum` do sentinel no arquivo é o de auto-teste (`:485`) | `w6-adapter`, `rail-a-materials-round-2.md` e `rail-materials-round-12.md` (LAND congela hashes DEPOIS do gate de árvore; relê sentinel/`.asc` do worktree) | congelar `git hash-object` do sentinel e do `.asc` no G1 e re-conferir imediatamente antes do `git add`; o `lib.sh` tem UMA função de congelamento e uma de re-conferência | reescrever o sentinel entre G1 e S: o LAND tem de recusar. **Limite declarado:** execução local de operador único torna a exploração improvável; a classe entra porque o toolkit é compartilhado e a janela vira comum a todos os pacotes |
| **CM-10** | o escopo assinado só é conferido DEPOIS da assinatura | o `SIGN` checa apenas que o bloco `Scope` não é placeholder e o imprime; nenhum dos 22 `OWNER-*SIGN.sh` faz `cmp`/`diff` contra um escopo regenerado. O `G4` do LAND confere nos dois sentidos, mas isso é DEPOIS de o Owner ter assinado | `PLAN-186/OWNER-S343-W4A-SIGN.sh:265` (placeholder) e `:400` (impressão); a conferência real em `PLAN-169/OWNER-S338-FABLE51-LAND.sh:423-450`, presente em 13 LANDs | `w6-adapter` (§Context do PLAN-188, linha «Escopo do sentinel digitado, diferente do diff»); invariante 5 do plano | `sign.sh` REGENERA o escopo das ops do pacote e compara byte a byte antes de pedir a assinatura; sem nenhum dos dois braços da OQ-7 ⇒ recusa nomeada | sentinel com um path a mais no `Scope`: o SIGN tem de recusar. Hoje ele passa e só o LAND reprova — a assinatura já foi dada sobre o escopo errado |
| **CM-11** | `EXPECTED-BASELINE.txt` consumido sem regeneração | 12 SIGNs leem chaves do baseline e nenhum o REGENERA para comparar; um valor editado à mão depois do `finalize` é aceito como base declarada | `PLAN-169/OWNER-S338-FABLE51-SIGN.sh:48`; `PLAN-179/OWNER-S335-179CLOSE-SIGN.sh:49`; `PLAN-169/OWNER-S329-E-SIGN.sh:45` (nenhum `cmp`/`diff` em SIGN nenhum) | `w4b-ci-matrix` (§Context do PLAN-188, «baseline editado à mão depois do finalize»); a mesma classe está na memória do repo como «materiais de cerimônia landados cedo + lands livres depois = baseline defasado» | invariante 4: `finalize.sh` é o ÚNICO escritor; `sign.sh` regenera e compara byte a byte, e edição manual é recusa | alterar um valor do baseline à mão e rodar o SIGN: recusa nomeada. Perna negativa: baseline regenerado sem edição continua passando |
| **CM-12** | harness planta `Rail-Verdict: APPROVE` sintético | quando o veredito real não é `APPROVE`, o harness ESCREVE um registro sintético no clone descartável para destravar os casos verdes — e com isso nunca exercita o caminho «SIGN recusa sem APPROVE» | `PLAN-186/s343-ceremony-w4a/test-ceremony-scripts-w4a.sh:180-189`; `PLAN-169/s338-ceremony-fable51/test-ceremony-scripts-fable51.sh:200`; `PLAN-185/s329-ceremony-C/test-ceremony-scripts-C.sh:206` — **11 de 14** harnesses rastreados | §Context do PLAN-188 (a classe apareceu em `p169`, `w1`, `w4b` e `w6`) | invariante 8: o harness COPIA os registros reais; sem `APPROVE`, o verde esperado é «SIGN recusa» | rodar o harness sem nenhum registro `APPROVE`: o caso tem de esperar RECUSA e ficar verde por isso. **Nota justa:** o plant vivo é MARCADO como artefato e confinado ao clone; o defeito não é desonestidade, é que a recusa nunca é testada |

## §2 — Classes sem ocorrência viva no repositório

Estas apareceram nos packs e **não reproduzem** nos 53 scripts assinados. Entram
no corpus porque a cura é no MOLDE: um clone futuro as reintroduz de graça.

- **CM-13 — rollback armado depois do commit.** `RESTORE_ON_EXIT=0` só executado
  após um gate pós-commit faz o `trap` reverter o patch contra um HEAD já
  avançado: árvore suja, commit local, recuperação documentada deixa de ser
  limpa. Achado em `<PK>/w6-adapter/rail-materials-round-12.md` F5 e em
  `<PK>/p169-w41-quota-resume/rail-materials-round-12.md` #11.
  **Medido no vivo:** os LANDs desarmam na linha imediatamente seguinte ao
  `git rev-parse HEAD`, sem gate entre os dois — `PLAN-169/OWNER-S329-E-LAND.sh:903-910`,
  `PLAN-169/OWNER-S331-F-LAND.sh:995-1002`, `PLAN-179/OWNER-S335-179CLOSE-LAND.sh:1043-1050`.
  Cura no toolkit: desarmar ANTES do commit e recuperar por `git reset --hard`
  contra o `NEW_SHA` registrado, nunca por `trap` que reverte arquivos já
  commitados.
- **CM-14 — aprovação ANINHADA eleita por enumeração recursiva.** Enumeração
  recursiva mais casamento por basename elege um `archive/rail-round-2.md`
  `APPROVE` sobre um `rail-round-1.md` `REJECT`
  (`<PK>/p169-w41-quota-resume/rail-materials-round-12.md` #2, P1, reproduzido).
  **Medido no vivo:** `RAIL_GLOB="$CEREMONY_DIR/rail-round-*.md"` é glob de
  shell, não-recursivo, nos 20 sítios que o definem — nenhuma ocorrência.
  Cura: o conjunto é a LISTA PINADA por sha256 do manifesto; arquivo em disco
  fora da lista ⇒ recusa nomeada (invariante 1).
- **CM-15 — path pessoal absoluto em material assinado.** Um hit em
  `w4b-ci-matrix` (§Context do PLAN-188). **Medido no vivo:** zero literais
  `/Users/<usuário>` nos 53 `OWNER-*.sh`. Cura: invariante 3 — guard que se
  auto-escaneia, com a isenção de self-test vindo de um ARGUMENTO explícito
  (`--selftest-fixtures <path>`), nunca de sentinela dentro do material nem de
  variável de ambiente herdada.
- **CM-16 — receita de digest sensível à ORDEM divergindo entre espelhos.** O
  harness inseria um membro por último enquanto SIGN e LAND o inseriam no meio;
  o digest é `shasum` sobre linhas `<sha>  <path>` ORDENADAS, então o harness
  computava outro hash e toda aprovação sintética morria antes de chegar ao
  controle que existia para exercitar
  (`<PK>/w6-adapter/rail-a-materials-round-2.md` #1, P1: harness `:229`/`:292`
  contra SIGN `:92`). Não medido no vivo: o digest de materiais é por pacote e
  os pacotes ficam fora do repo. Cura: UMA receita, no `lib.sh`, com a ordem
  declarada como carga útil e um controle que extrai a lista de membros das
  quatro invocações e as compara.
- **CM-17 — instrumento que aceita falha como sucesso.** Cinco ocorrências num
  só registro (`<PK>/p169-w41-quota-resume/rail-materials-round-12.md`, itens
  13, 15, 18, 19 e 22): oráculo com exit 42 aceito como veredito; gerador que
  embute o que voltou e devolve 0; runner que imprime «reportado, não contado» e
  conta; publicação de duas cópias de EVIDENCE sem transação. Classe de gerador
  de material, não dos `OWNER-*.sh`. Cura: todo gerador do toolkit recusa em
  rc≠0 e a escrita de artefato é atômica (temporário + `rename`).

### §2b — Classes já curadas no vivo, por clone (precedente, não dívida)

Duas classes do mesmo molde já foram fechadas — mas **clone a clone**, que é
exatamente a forma que o PLAN-188 substitui. Ficam registradas porque são a
prova de que a cura por clone funciona e não escala.

- **`git add -u` nunca inclui o `.asc`.** Curado com comentário explicativo e
  staging explícito com prova por `cmp` em
  `PLAN-169/OWNER-S338-FABLE51-LAND.sh:905-927` (5 LANDs carregam o mesmo bloco
  e o mesmo comentário, copiado).
- **Runner que não se auto-resolve.** 48 dos 53 scripts resolvem a raiz por
  `SCRIPT_DIR` + `git rev-parse --show-toplevel`; os 5 que não o fazem são os
  mais antigos (`PLAN-167/OWNER-PREPARE-TO-SIGN.sh`, `PLAN-167/OWNER-W4-LAND.sh`,
  `PLAN-168/OWNER-LAND.sh`, `PLAN-168/OWNER-PREPARE-TO-SIGN.sh`,
  `PLAN-182/OWNER-S319-LAND.sh`). A metade «executado a partir da posição
  landada» da invariante 7 continua aberta.

## §3 — O que o PLAN-188 já cobre e o que este corpus acrescenta

**Já coberto.** A tabela do §Context do plano
(`<ROOT>/.claude/plans/PLAN-188-shared-ceremony-toolkit.md:38`) nomeia sete
classes, e o bloco «Invariantes fechadas UMA vez» (`:485`) as converte em dez
invariantes com controle vermelho. O mapeamento é direto:

| invariante do plano | classes deste corpus |
|---|---|
| 1 (duas famílias de rail, registros pinados) | CM-01, CM-03, CM-14 |
| 2 (trailer gerado do conjunto) | CM-06 |
| 3 (guard de path absoluto com argumento) | CM-15 |
| 4 (`EXPECTED-BASELINE` só do finalize) | CM-11 |
| 5 (escopo gerado, comparado byte a byte) | CM-10 |
| 6 (`NEW_SHA` ligado ao push e ao destino) | CM-07, CM-08 |
| 7 (runner auto-resolvente, executado da posição landada) | §2b |
| 8 (harness nunca planta `APPROVE`) | CM-12 |
| 10 (verificação de signatário) | — (já viva em 33 dos 48 scripts, por medição do próprio plano) |

**O que este corpus acrescenta, e que nenhuma invariante cobre hoje:**

1. **CM-02, CM-04 e CM-05 são uma classe só, e ela não tem invariante.** As três
   são «o leitor falha PARA CIMA»: normalizador que aceita malformado, produtor
   que morre sem chegar ao gate, pipe que mata o produtor. Elas atravessam
   invariantes diferentes (1, 3 e a leitura de árvore) e por isso nenhuma as
   pega. **Proposta:** uma invariante 11 — *nenhum gate lê entrada por pipeline
   cujo rc não seja conferido; toda normalização preserva o interior do valor* —
   com os três controles vermelhos deste corpus. Ela é predicado sobre o
   `lib.sh` sozinho, logo cabe na W0 (§Items, `:709`).
2. **CM-09 (janela entre verificar e usar) não está em invariante nenhuma.** A
   invariante 1 pina os REGISTROS por sha256; nada pina o sentinel e o `.asc`
   entre o G1 e o staging. Cabe na W1 junto da invariante 6, que já trata do
   par «verificar, então usar».
3. **CM-10 muda de severidade quando se lê o par SIGN/LAND junto.** O plano
   trata o escopo como uma invariante; a medição mostra que a verificação
   EXISTE, mas só no LAND — isto é, depois da assinatura. O controle vermelho
   do AC-1 (`:947`) tem de ser do lado do SIGN, senão passa verde sobre o gate
   errado.
4. **CM-12 tem uma nuance que o AC-1 precisa herdar.** O plant vivo é marcado e
   confinado ao clone; o vermelho não é «o harness mente», é «a recusa nunca é
   exercitada». Um controle escrito contra a leitura errada (procurar a string
   `APPROVE` no harness) ficaria verde depois de uma renomeação cosmética.
5. **Números para o AC-4.** Este corpus dá o denominador vivo por classe (35, 30,
   15, 13, 11, 10, 9 sítios), que é contra o que a medição pós-migração compara.

## §4 — Método e limites

- **Padrões grepados** sobre `<ROOT>/.claude/plans/*/OWNER-*.sh` (53 arquivos) e
  sobre os harnesses rastreados: `tr -d '[:space:]'`; `< <(git status`;
  `-gt "$LAST_N"`; `grep -m1 '^Rail-Verdict:'`; `| head -`; `git push`;
  `Pair-Rail-Reviewed`; `interpret-trailers`; `%B`; `RESTORE_ON_EXIT`;
  `git add -u`; `RAIL_GLOB=`; `rev-parse --show-toplevel`; o prefixo de home absoluto (`/Users/<user>/`, escrito aqui como placeholder para não disparar o próprio gate);
  `cmp `/`diff -u`/`diff -q`; `shasum`/`hash-object`; `EXPECTED-BASELINE`;
  `Rail-Verdict: APPROVE`.
- **Arquivos lidos por inteiro ou em blocos citados:** 9 scripts assinados
  (`PLAN-186/OWNER-S343-W4A-SIGN.sh`, `PLAN-169/OWNER-S338-FABLE51-LAND.sh`,
  `PLAN-169/OWNER-S329-E-LAND.sh`, `PLAN-169/OWNER-S331-F-LAND.sh`,
  `PLAN-179/OWNER-S335-179CLOSE-LAND.sh`, `PLAN-169/OWNER-S328-B-SIGN.sh`,
  `PLAN-186/s343-ceremony-w4a/test-ceremony-scripts-w4a.sh`, e trechos de
  `PLAN-169/OWNER-S331-F-SIGN.sh` e `PLAN-185/OWNER-S329-C-SIGN.sh`), mais 6
  registros de rail dos packs e as seções `:32`, `:485`, `:709` e `:947` do
  PLAN-188.
- **Toda linha citada foi lida**, nunca inferida de um `grep -c`. Onde a
  ocorrência é uma AUSÊNCIA (CM-07), a busca que a estabelece está escrita ao
  lado do número.
- **O que NÃO foi verificado:** (i) os packs em `<PK>` não foram executados —
  as reproduções citadas são as dos próprios registros de rail, lidas como
  DADO, não repetidas por mim; (ii) nenhum controle vermelho deste corpus foi
  escrito ou rodado — eles são a especificação do que a W0/W1 tem de entregar;
  (iii) a receita de digest de materiais (CM-16) não foi medida no vivo porque
  não existe no repo; (iv) `w4b-ci-matrix` contribuiu apenas pelas classes já
  registradas no §Context do plano — o pack foi RESCINDIDO na nota `S348-r12`
  do seu `STATE.md` e os seus 26 registros de materiais não foram varridos um a
  um; (v) a severidade de CM-05 e CM-09 depende de condições (entrada grande,
  processo concorrente) que a operação local de um único operador torna
  improváveis hoje — as duas entram pelo custo de compartilhar o molde, e isso
  está escrito na própria linha.
- **Contradição registrada.** O registro `<PK>/p169-w41-quota-resume/rail-materials-round-12.md`
  fecha com a afirmação do revisor de que «nenhum path absoluto pessoal foi
  encontrado nos materiais selecionados para commit», enquanto o §Context do
  PLAN-188 cita um hit em `w4b`. As duas coisas são compatíveis (pacotes
  diferentes, instantes diferentes) e ficam ambas escritas: CM-15 é classe de
  molde, não dívida viva.

## CLAIM

- 17 classes catalogadas: **12 com ocorrência VIVA** no repositório (§1), **5 só
  nos packs** (§2), mais **2 já curadas por clone** (§2b).
- Denominadores vivos medidos, por classe: 35 (`tr -d '[:space:]'`), 30
  (`< <(git status`), 15 (push não pinado), 14 (commit sem releitura da
  mensagem), 13 (trailer só «não TO-FILL»), 13 (G4 pós-assinatura), 12
  (baseline sem regeneração), 11/14 (harness que planta `APPROVE`), 10
  (`grep -m1` do veredito), 9 (`-gt` sem teto), 0 (path pessoal absoluto).
- Os 5 padrões de grep mais produtivos: `grep -m1 '^Rail-Verdict:'`;
  `< <(git status`; `Pair-Rail-Reviewed`; `git push "$PUSH_REMOTE"`;
  `Rail-Verdict: APPROVE` nos harnesses. O grep NEGATIVO mais produtivo foi
  `%B` / `commit-msg` nos LANDs: zero ocorrências, e a ausência É o defeito.
- Quatro acréscimos ao PLAN-188 propostos no §3: uma invariante 11 («o leitor
  falha para cima») cobrindo CM-02/04/05; CM-09 (janela verificar→usar) para a
  W1; o controle vermelho de CM-10 movido para o lado do SIGN; e a nuance de
  CM-12 (o vermelho é «a recusa nunca é exercitada», não «o harness mente»).
- Ficou de fora: execução de qualquer controle, varredura dos 26 registros de
  materiais do pack rescindido, e a medição do digest de materiais no vivo.
