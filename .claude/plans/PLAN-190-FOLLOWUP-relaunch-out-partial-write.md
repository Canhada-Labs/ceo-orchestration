---
id: PLAN-190-FOLLOWUP-relaunch-out-partial-write
title: "relaunch --out confere a escrita inteira (escrita parcial entregaria cópia truncada)"
status: draft
created: 2026-09-17
owner: CEO
depends_on: [PLAN-190]
level: L2
tags: [workflow, recovery, cli, followup]
---

## Context

Achado P2 da RODADA FINAL do pair-rail (r6) sobre a W1, declarado no anexo do sentinel assinado
(`.claude/plans/PLAN-190/w1/w1-approved.md`, commit `075beed9`) em vez de abrir outra volta de revisão,
pela regra «rodada final com anexo» que o Owner ratificou em 10/09/2026.

`_write_new_file` em `.claude/scripts/ceo-launches.py` cria o destino com
`O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW` (nunca sobrescreve, nunca segue symlink) e depois faz **um único**
`os.write(fd, data)`. `os.write` pode escrever MENOS bytes do que o buffer; o rail reproduziu injetando
um retorno de 2 para 11 bytes. Hoje isso devolve sucesso e deixa no disco uma cópia TRUNCADA do snapshot
do script — exatamente o material que o rito de recuperação manda passar como `scriptPath`.

## Goal

`relaunch --out` ou entrega o arquivo com os bytes completos, ou falha nomeando o erro e NÃO deixa
arquivo incompleto no disco.

## Items

### W1 — escrita completa ou nada  [P1]  (livre: `.claude/scripts/ceo-launches.py` não é canônico)
- Laço até escrever todos os bytes (ou `os.writev`/`write` repetido), tratando `InterruptedError`.
- Qualquer falha no meio: remover o arquivo que ESTA operação criou (só ele — o `O_EXCL` garante que o
  arquivo é nosso) e devolver rc 2 com o motivo.
- Regressão em `.claude/hooks/tests/test_check_workflow_launch.py`: `os.write` que devolve menos bytes
  (monkeypatch no módulo) ⇒ rc 2, mensagem nomeando a escrita parcial, arquivo AUSENTE ao fim; e o
  caminho feliz continua entregando bytes idênticos ao snapshot.
- Prova por mutação: reverter o laço ⇒ a regressão fica vermelha.

### W2 — cura estrutural («opção B»)  [P1]  (livre: oráculo `--is-canonical` = 0 nos 4 paths)
Forma decidida pelo Owner em 2026-09-18: temporário exclusivo, publicação por `link` sem substituição,
nenhum `unlink` no destino — os três elementos registrados na condição 14 de
`.claude/plans/PLAN-192/repass-rc1/CONDITIONS-rc1.md`. O detalhe «no MESMO diretório» vem do brief da
lane (S357), não da condição 14.
- **Emenda da forma (S357, rodada 2 da sonda Codex — DECISÃO DO OWNER PENDENTE):** o temporário NÃO fica
  solto no diretório do destino; fica dentro de um diretório PRIVADO `.ceo-launches-out-<16 hex>` (modo
  0700) que a chamada cria DENTRO do diretório do destino — mesmo sistema de arquivos por construção, que
  é o que o «MESMO diretório» do brief garante para o `link`. Motivo: a rodada 2 verificou a busca
  case-insensitive nativa e reproduziu, num sistema de arquivos em memória com o sorteio fixado, um
  destino grafado como variante de CAIXA do nome do temporário; a lane reproduziu o caso em APFS
  (case-insensitive, padrão do macOS) e sua sonda reproduziu também a variante de DOBRA (U+017F «ſ» ≡
  «s») — o mesmo inode
  sob outra grafia ⇒ bytes PARCIAIS visíveis no nome do destino durante a escrita, e a limpeza removendo
  esse nome. As duas reproduções FORÇAM o sorteio (`secrets.token_hex` fixado num valor conhecido): com o
  sorteio real de 16 hex, o operador teria de grafar FILE como variante de um nome de 64 bits aleatórios
  gerado na mesma execução — a forma literal falha com probabilidade da ordem de 2^-64. A emenda troca
  esse limite PROBABILÍSTICO por um ESTRUTURAL, ao custo de um `mkdir` a mais e de uma sobra que é um
  diretório em vez de um arquivo. O prefixo reservado comparava GRAFIAS (texto) contra regras de nome do
  sistema de arquivos — classe que não converge; foi REMOVIDO. Com o diretório privado, bytes parciais
  nunca são uma entrada do diretório do destino; ficam só dentro do diretório privado: uma grafia
  equivalente só alcança o diretório privado (nunca um arquivo) e o `link` recusa. Alternativa se o
  Owner exigir a forma literal: temporário no mesmo diretório + checagem de IDENTIDADE logo após criá-lo
  — deixa uma janela em que o nome do destino aponta para um arquivo VAZIO e a limpeza remove essa
  entrada; por isso não foi a escolhida.
- Diretório privado criado com `mkdir(…, 0o700, dir_fd=dfd)`, aberto como o diretório do destino
  (`O_PATH`/`O_SEARCH` onde existem, senão `O_RDONLY`) `| O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC`;
  temporário `snapshot.part` dentro dele com `O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC`, modo 0600; laço até
  o último byte; `fsync` (só do temporário); `close`.
- Publicação: `os.link("snapshot.part", nome, src_dir_fd=pfd, dst_dir_fd=dfd, follow_symlinks=False)`.
  Qualquer entrada no destino (arquivo, symlink, diretório) ⇒ recusa nomeada, rc 2, e o que está lá fica
  intacto: a presente no início é recusada pela checagem prévia, antes de qualquer criação (atalho — e,
  desde a rodada 1 da revisão do build 1.4.2, fixado por teste: nenhum `mkdir`, nenhum byte escrito); a
  que surge durante a escrita, pelo `EEXIST` do próprio `link`. QUALQUER erro do `link` é decidido por
  IDENTIDADE (dispositivo, inode — nunca grafia) do que o destino nomeia em seguida: o próprio
  temporário ⇒ o `link` criou o nome apesar do erro (um LINK retransmitido no NFS pode responder `EEXIST`) ⇒
  publicação, rc 0; senão, no `EEXIST`, o próprio diretório privado sob outra grafia ⇒ recusa «alias» e
  outra coisa ⇒ recusa «tomado»; nos demais erros, falha nomeando o errno, com a dica de hard link para
  EPERM, ENOTSUP/EOPNOTSUPP, EXDEV, EMLINK; destino ILEGÍVEL depois do erro ⇒ recusa que diz não saber
  se o destino guarda a cópia (nunca «nada publicado»). A identidade do temporário (`fstat`) é tomada
  antes do `link`; sem ela, falha antes do `link`. Desde a rodada 2 da revisão do build 1.4.2, o `link`
  que dá CERTO passa pela mesma comparação (o `link` publica o que estiver sob o NOME do temporário
  naquele instante): o destino só é anunciado como cópia (rc 0) se for, por identidade, o objeto cujo
  `fstat` foi tomado pelo descritor em que os bytes foram escritos e `fsync`'ados; outra coisa ⇒ recusa
  «não é o temporário que esta chamada escreveu», rc 2, o destino fica como está (nunca unlink) e não
  deve ser usado; destino ilegível ⇒ recusa «cannot tell».
- `finally`: remove, PELO NOME, só os dois nomes que a chamada criou — o temporário (via descritor do
  diretório privado, e só se o `O_EXCL` DESTA chamada deu certo), depois o diretório privado; o nome do
  destino nunca é passado a unlink/rmdir/rename/replace. Remoção por nome não é remoção de objeto: quem
  escreve no diretório do destino pode pôr outro diretório VAZIO sob o nome do privado, e o `rmdir`
  remove esse (declarado pela forma no doc). Falha dessa remoção DEPOIS de um `link` cuja checagem de identidade passou não é falha da cópia
  (o destino está inteiro; rc inalterado; stderr nomeia o diretório que sobrou); ANTES do `link`, a
  recusa o nomeia.
- Destino cujo último componente não nomeia arquivo (vazio, `.`, `..`, terminado em `/`) ⇒ recusa, rc 2.
  Sem diretório privado (`mkdir` falha), sem `link` ou sem as chamadas relativas a diretório ⇒ recusa,
  rc 2, nunca uma escrita no lugar nem uma que substitua. O diretório do destino é aberto só para BUSCA
  onde o Python expõe `O_PATH` (Linux) ou `O_SEARCH` (macOS): um diretório só de escrita+busca (0300)
  segue aceito como em `19771fa1`; onde nenhuma das duas existe, é recusado, rc 2.
- `cmd_relaunch`: a segunda leitura do snapshot (os bytes impressos e copiados) é conferida contra o
  sha256 registrado — ilegível OU diferente ⇒ rc 7, nada impresso como exato (cura da CLASSE «segunda
  leitura», não só do caso `None`); `--out` sem bytes a copiar ⇒ motivo em stderr e rc ≠ 0 (2 para
  workflow nomeado, 7 para script não registrado no lançamento); `--out ""` explícito é um pedido, não
  omissão (`args.out is not None`) ⇒ recusa (rc 2; rc 7 se o script não foi registrado no
  lançamento).

## Regra de parada
- Se a cura exigir mudar o contrato do `relaunch` (rc, formato de saída) além de uma linha de erro nova,
  parar e tratar como wave própria do PLAN-190 — este follow-up é uma correção de escrita, não um
  redesenho da recuperação.
- **Acionada pela W2 — mudança de contrato DECLARADA, decisão do Owner pendente:** `relaunch --out` de
  workflow NOMEADO passa de rc 0 (o `--out` era ignorado em silêncio) a rc 2; um snapshot que não relê
  igual passa de rc 0 a rc 7. Menor, da mesma classe «`--out` que não cria arquivo nunca sai 0»:
  `--out ""` (antes tratado como omitido, rc 0) passa a rc 2; `--out` de script não registrado segue
  rc 7, agora com uma linha em stderr; `--out` que FALHA para script não registrado cujo manifesto
  (editado à mão — o hook nunca grava snapshot para esse registro) traz snapshot passa de rc 2 a
  rc 7. A FORMA nova também tira do rc 0 uma CLASSE de ambientes em que
  `19771fa1` publicava a cópia inteira — passam a rc 2, recusa nomeada; nada publicado, exceto no
  membro «identidades divergentes» abaixo, em que o `link` publicou e a recusa manda não usar o
  arquivo. A classe, pela forma: todo destino em que a forma de `19771fa1` (criação exclusiva
  simples do arquivo NOVO, escrita, `close`) teria dado certo mas QUALQUER operação que a forma nova
  faz além dela é recusada ou falha — exemplos, não a lista: uma chamada relativa a diretório,
  criar ou abrir o diretório privado, criar o temporário dentro dele, um segundo inode, `fsync`,
  `fstat`, o hard link, a leitura do que o destino nomeia depois dele —, seja quem recusa o
  diretório do destino, seu sistema de arquivos ou plataforma, ou a umask do PROCESSO; ou que devolve, para o mesmo
  arquivo, identidades (dispositivo, inode) diferentes pelo nome do destino e pelo descritor do
  temporário. Exemplos, não a lista: sistema de arquivos sem hard links (MEDIDO na rodada 2 do fix,
  2026-09-23: volume FAT (msdos) de 4 MB no macOS — a lane recusa com `link` `ENOTSUP` e o volume
  fica vazio; a forma de `19771fa1` publica os 5000 bytes no mesmo volume; exFAT e alguns
  compartilhamentos SMB/FUSE não medidos); plataforma sem `dir_fd`; ACL que permite `add_file` mas
  nega `add_subdirectory` (medido no macOS: `19771fa1` publica, a lane recusa); umask que tira do dono o
  bit de escrita ou de busca do 0700 pedido (0177, 0100, 0200 ⇒ recusa, `EACCES`, nos dois sistemas;
  QUAL chamada recusa depende da flag — no macOS (`O_SEARCH`, medido) 0177 e 0100 recusam na
  abertura do diretório privado e 0200 na criação do temporário; no Linux (`O_PATH`, medido em
  contêiner, kernel 6.8, 2026-09-23) a abertura não confere permissão nenhuma no próprio diretório e as
  três recusam na criação do temporário; desde a rodada 2 do fix o diretório
  privado é aberto só para busca, como o do destino, então umask que tira só a LEITURA do dono —
  0400, 0477 — publica, rc 0, onde há `O_PATH`/`O_SEARCH` (medido nos dois), e recusa na abertura
  onde não há nenhuma das duas — fixado por teste que força a flag `O_RDONLY`); cota com um inode livre (não medido); diretório 0300 (escreve e
  percorre mas não LÊ) SÓ onde o Python não expõe nem `O_PATH` nem `O_SEARCH` — no macOS e no Linux
  ele segue aceito, rc 0 (medido nos dois; o Linux em contêiner, 2026-09-23); identidades
  divergentes (não medido em nenhum sistema de arquivos). Fora dessa classe e das
  mudanças nomeadas acima, os demais códigos de saída e a saída de sucesso no stdout (mesmas linhas,
  mesma ordem) ficam iguais. As duas mudanças principais vieram pedidas no brief da lane (S357); cabe ao
  Owner dizer se ficam neste follow-up ou viram wave do PLAN-190, e ratificar a CLASSE.
- **Parada da revisão cruzada, PRÉ-REGISTRADA antes da rodada 3 (S357):** a rodada 3 da sonda Codex é a
  ÚLTIMA desta lane. Achado novo dela é DECLARADO aqui (resíduo com a forma), não abre rodada 4 —
  exceto P0/P1 da classe «o nome do destino passa a nomear bytes parciais, ou some uma entrada que a
  chamada não criou», que para a lane e sobe ao Owner.

## Progresso

- **W1 — LANDADA** em `47870320` (land livre): laço de escrita, falha tratada ⇒ rc 2. A limpeza
  (`lstat` + `unlink` do destino) e os casos (a)–(d) da condição 14 ficaram declarados na v1.4.1.
- **W2 — IMPLEMENTADA na lane `s357/relaunch-optb`, NÃO landada.** Alvo: v1.4.2 segundo o brief da
  S357 — confirmar no ledger do Owner. Precondição de land: DEPOIS da tag GA da 1.4.1 (os dois arquivos
  de código chegam aos adopters). Paths: `.claude/scripts/ceo-launches.py`,
  `.claude/hooks/tests/test_check_workflow_launch.py`, `docs/workflow-recovery.md`, este plano.
  - Evidência (suíte ALVO `.claude/hooks/tests/test_check_workflow_launch.py`, 61 testes em HEAD → 85
    na lane; Python 3.9.6, macOS APFS case-insensitive, 2026-09-23, depois da rodada 1 da revisão do
    build 1.4.2): com o `ceo-launches.py` de HEAD `19771fa1` e os testes da lane ⇒ 23 VERMELHOS, os 23
    por `AssertionError` de comportamento, nenhum por atributo ausente; 62 verdes. Dos 27 testes novos ou
    mexidos, 4 ficam verdes em HEAD por desenho: `test_zero_progress_is_a_failure_not_a_spin` (da W1,
    ganhou asserções de «nada sobra» que HEAD já cumpria) e três que HEAD cumpria por escrever o destino
    no lugar — o diretório 0300 (abria o próprio FILE, sem ler o diretório), o `link` que reporta erro
    depois de criar o nome (não havia `link`) e o symlink no destino desde o início (o `O_EXCL|O_NOFOLLOW`
    recusava). Com a cura ⇒ 85 verdes. (A medição anterior, 2026-09-22 — 78 testes, 19 vermelhos em
    HEAD — fica substituída por esta; e esta, pela da rodada 2 abaixo — 92 testes, 30 vermelhos em
    HEAD.)
  - Reprodução do achado da rodada 2 como teste: `test_structural_an_equivalent_spelling_of_a_created_name_never_exposes_a_partial_file`
    pergunta ao sistema de arquivos (não à grafia) se a variante de caixa e a variante com U+017F nomeiam
    o diretório privado; nesta máquina as duas nomeiam, e o destino só aponta para o DIRETÓRIO durante a
    escrita, com recusa nomeada e nada sobrando. `test_structural_a_destination_spelled_as_the_private_directory_never_names_a_partial_file`
    cobre o mesmo mecanismo em qualquer sistema de arquivos (grafia idêntica, sorteio forçado).
  - Flake AMBIENTAL registrado (não é da lane): `test_manifest_is_on_disk_before_git_runs` falhou nas
    execuções do arquivo inteiro com load average ≈ 10 e passa sozinho. Controle: HEAD PRISTINO (código
    E testes, nenhuma mudança da lane) sob a mesma carga ⇒ o MESMO teste vermelho (1 falho, 60 verdes).
    Ele só dirige o hook em subprocesso (o `git` falso tem 0,6 s por chamada, `GIT_BUDGET_S / 2` em
    `_lib/launch_ledger.py`), que a lane não toca, e roda antes dos testes novos na ordem alfabética.
    Nas execuções finais da medição de 2026-09-22 (load ≈ 6), com 78 testes no arquivo, ele passou:
    78/78.
  - Prova por mutação da forma que a rodada 3 revisou (15 mutações, M1–M16 sem M10, uma por vez,
    bytes restaurados por sha256): 14 vermelhas, cada uma pelos testes que a visam — publicar com
    `replace` por caminho (substitui de verdade; a mutação anterior com `dir_fd` só caía por
    `NotImplementedError` neste Python), tirar o `fsync`, não remover nada no fim, silenciar o `--out`
    sem bytes, não reconferir a segunda leitura (inteira, ou só o hash), temporário sem `O_EXCL`, um único
    `os.write`, tratar `--out ""` como omitido, calar o que sobrou depois do `link`, voltar à forma da
    rodada 2 (temporário solto no diretório do destino), trocar a checagem de identidade por «tomado»,
    não remover o diretório privado, não remover o temporário. A 15.ª — tirar a checagem prévia — ficava
    VERDE por desenho (na corrida é o `link` quem decide o `EEXIST`); a rodada 1 da revisão do build
    1.4.2 a fixou por teste (abaixo).
  - Revisão cruzada (sonda Codex read-only a partir da worktree, consultiva — NÃO é veredito de
    pair-rail): rodada 1 REJECT com 4 P2 (`--out ""` rc 0 em silêncio; colisão do nome do temporário
    com o destino; duas frases do doc falsas sobre a falha de limpeza pós-`link` e sobre quem recusa um
    destino existente) — os 4 curados, cada cura de código com mutação que a mata. Rodada 2 REJECT com
    1 P2 (R2-1: variante de CAIXA — id do Codex: R1-2; a dobra U+017F é da sonda da lane — do nome
    do temporário escapava do prefixo reservado, que
    comparava grafias — bytes parciais visíveis no nome do destino e limpeza removendo essa entrada;
    reproduzido nesta máquina) + a frase do doc que ele desmentia ⇒ curado pela emenda do diretório
    privado (acima). Rodada 3 (a ÚLTIMA, parada pré-registrada): R2-1 CLOSED; nenhum defeito de
    correção, portabilidade Linux/macOS ou integridade do destino; 1 P2 de DOC — «the message names
    it when the removal failed» era falsa quando uma exceção não tratada (Ctrl-C) propaga e a remoção
    também falha (verificado: sobra o diretório privado com o temporário, stderr vazio). Fora da
    classe de exceção da parada ⇒ DECLARADO, sem rodada 4: a frase foi corrigida para dizer a forma
    do limite; nenhuma mudança de código depois da rodada 3.
  - Revisão do build 1.4.2, rodada 1 (2026-09-23; outro instrumento — revisores Claude do workflow
    `v142-build`, não a sonda Codex cuja parada está acima): 6 achados de mecanismo (B-R1-1..6, P2) e 8
    de afirmações (B-CL-1 P1, B-CL-2..8 P2). B-R1-1 tem a FORMA da classe de parada («some uma entrada
    que a chamada não criou»), mas só com adulteração do diretório do destino como precondição e em P2 —
    fora da exceção P0/P1 ⇒ tratado aqui e sinalizado ao Owner. Destino de cada um:
    - B-R1-1 (a) ACEITO: o temporário só é removido se o `O_EXCL` DESTA chamada deu certo (antes, uma
      entrada plantada sob `snapshot.part` era removida mesmo com o `O_EXCL` falhando). (b) REJEITADO —
      conferir dono e modo do diretório privado depois de abri-lo: não compra integridade contra quem
      escreve no diretório do destino, que substitui FILE depois da publicação de qualquer jeito
      (sonda C2: diretório trocado antes da abertura ⇒ os bytes DELE publicados, rc 0; a mesma pessoa
      podia renomear sobre FILE logo depois), e arriscaria uma recusa falsa onde o sistema de arquivos
      não devolve o dono ou o modo pedidos (por exemplo NFS com `all_squash`; não medido). (c) ACEITO:
      o doc declara pela
      FORMA quem pode adulterar (qualquer um que escreva no diretório do destino — mesmo usuário, ou
      outro usuário sem sticky bit) e o que consegue; as três frases absolutas («only the temporary and
      that directory are removed», «Never any other name», «Nothing else is removed») viraram «remove,
      PELO NOME, só os dois nomes que criou», com o limite da remoção por nome declarado.
    - B-R1-2 + B-CL-1 (iii) ACEITO: diretório do destino aberto só para busca (`O_PATH`/`O_SEARCH`).
      Medido no macOS (sonda de `O_SEARCH` num diretório 0300: abrir, `fstatat`, `mkdirat`, `openat`,
      `linkat`, `unlinkat` — todos ok; `O_RDONLY` dá `PermissionError`); a perna Linux (`O_PATH`) segue o
      contrato de `open(2)` e NÃO foi executada aqui (daemon do docker parado; disciplina de CPU) — o
      teste novo a exercita no CI Linux.
    - B-R1-3 + B-CL-3 ACEITOS como CLASSE, não como o exemplo: QUALQUER erro do `link` (não só `EEXIST`)
      é decidido pela identidade do temporário; e o caso duplo — erro do `link` E o destino ilegível em
      seguida — diz «cannot tell whether FILE holds the copy», nunca «nada publicado». A identidade do
      temporário passou a ser pré-condição do `link` (`fstat` que falha ⇒ falha antes do `link`).
    - B-R1-4 ACEITO: `--out ""` de workflow NOMEADO ⇒ rc 2; symlink pendente no destino desde o início ⇒
      recusado pela checagem prévia, zero `mkdir`, zero bytes; abertura do diretório privado com
      `O_NOFOLLOW|O_DIRECTORY` fixada por flag E por comportamento (symlink trocado ali ⇒ recusa, nada
      escrito no alvo). A mutação da checagem prévia (M6) deixou de ser verde por desenho.
    - B-R1-6 ACEITO: falha do `link` nomeia o errno e, para EPERM, ENOTSUP/EOPNOTSUPP, EXDEV, EMLINK,
      diz que o sistema de arquivos pode não ter hard links.
    - B-R1-5, B-CL-2, B-CL-5, B-CL-6, B-CL-7, B-CL-8 ACEITOS (texto: sorteio forçado no Motivo; caso
      não declarado da v1.4.1; sinais de ação padrão que encerram o processo; 15 mutações/14 vermelhas;
      «bytes parciais nunca são entrada do diretório do destino»; atribuições da condição 14 e da
      rodada 2). B-CL-4 ACEITO pela QUALIFICAÇÃO: «o arquivo inteiro ou nenhum» vale enquanto a máquina
      fica de pé; depois de uma queda de energia nada é afirmado (nenhum diretório `fsync`'ado; `fsync(2)`
      no macOS não esvazia o cache do disco; `F_FULLFSYNC` não é usado — adotá-lo fica para o Owner,
      pois sai da forma decidida «write + fsync»).
    - Prova: com os testes desta rodada e o `ceo-launches.py` da lane ANTES dela (sha256 `35b6dad0…`),
      5 dos 34 testes de `relaunch` ficam vermelhos — exatamente os 5 que fixam código mudado nesta
      rodada; com a cura, 85/85. Mutação sobre a forma nova (27, uma por vez, `-k 'relaunch or
      Relaunch'`, bytes restaurados por sha256): 27 vermelhas — as 15 da rodada 3 (anchors atualizados;
      M6 agora vermelha) e 12 novas (MB, MK, MN do revisor; MS; MF e MFE — identidade só no `EEXIST` é o
      exemplo, não a classe; MU; MI; MH, MHA, MW; MD). Sondas das frases novas do doc (C1–C5): diretório
      VAZIO posto sob o nome do privado antes da limpeza é o removido, e o da chamada sobra sem aviso;
      diretório trocado antes da abertura recebe o temporário e o substituto é publicado; symlink ali é
      recusado (`ENOTDIR`) sem nada escrito no alvo; SIGTERM (rc -15) e SIGHUP (rc -1) deixam o
      diretório privado com o temporário e nenhum destino; o módulo não instala handler de sinal nem usa
      `F_FULLFSYNC`.
  - Revisão do build 1.4.2, rodada 2 (2026-09-23; revisores Claude do workflow `v142-build`, lentes de
    mecanismo e de afirmações): 5 achados de mecanismo (B-R2-M1..M5, P2) e 7 de afirmações (B-R2-CL-1
    P1, B-R2-CL-2..7 P2). Nenhum tem a forma da classe de parada: o M1 é «o destino anuncia bytes que a
    chamada não escreveu», só com adulteração como precondição. Destino de cada um:
    - B-R2-M1 ACEITO: o `link` que dá certo também é conferido por identidade (item «Publicação»
      acima). Mensagem pela medida, não pela causa: «after the link, FILE is not the temporary this
      call wrote (compared by device and inode)». A afirmação do revisor de que a cura não traz risco
      novo de recusa falsa é REJEITADA em parte: o risco é o mesmo que o caminho do `EEXIST` já tinha,
      mas agora vale para toda chamada — um sistema de arquivos que devolvesse identidades diferentes
      para o mesmo arquivo pelo nome e pelo descritor recusaria toda cópia (declarado pela forma no doc
      e na «Regra de parada»; nenhum medido). A sonda C2 da rodada 1 (diretório trocado antes da
      abertura ⇒ substituto publicado, rc 0) passa a recusa nomeada quando o substituto é outro objeto
      sob o nome do temporário (sonda D6); a alteração NO LUGAR do temporário (mesmo objeto) segue
      invisível e declarada.
    - B-R2-M2 + B-R2-CL-2 ACEITOS (mesmo defeito): o bloco de uso dizia «nada publicado» para todo
      rc 2; agora diz, pela forma, que as recusas feitas depois do `link` que dizem não saber, ou que o
      destino não é o temporário, podem deixar no destino o que o `link` publicou; a docstring de
      `_write_new_file` diz quando devolve `None` e que um texto de erro pode vir com o destino
      publicado.
    - B-R2-M3 ACEITO: 7 testes novos fixam, por comportamento ou por espião, o `fsync` do temporário que
      vira o destino (X1), o `link` por descritores com nomes nus e `follow_symlinks=False` (X2, X19), a
      identidade tomada do descritor, não do nome (X3), o erro no `close` ⇒ nada publicado (X6), a
      leitura de identidade que não segue symlink (X14: symlink no destino apontando para o temporário
      depois de um `EEXIST` ⇒ recusa «taken», não rc 0 sobre um link que fica pendente), e o M1 (troca
      do temporário antes do `link` que dá certo; destino ilegível depois dele). As falhas de `fsync` e
      de `close` passaram a nomear o errno, como as demais.
    - B-R2-M4 + B-R2-CL-1 ACEITOS (2.ª ocorrência da classe «lista em vez de forma» ⇒ cura estrutural):
      a mudança de contrato da «Regra de parada» agora declara a CLASSE de ambientes que saem do rc 0
      (medidos: ACL que nega `add_subdirectory`; umask 0177) e pede ao Owner a ratificação da classe; o
      doc declara a mesma classe e que 0700/0600 são modos PEDIDOS, sujeitos à umask.
    - B-R2-M5 ACEITO: «privado» nomeia o papel do diretório, não uma garantia de acesso. No macOS uma
      entrada de ACL herdável no diretório do destino é herdada pelo diretório privado, pelo temporário
      e pelo FILE (sonda D1; também com `only_inherit`, entrada que não vale para o próprio diretório do
      destino — D2) e uma entrada allow concede o que nomeia por cima dos bits de modo (sonda D7: modo
      000 + entrada allow ⇒ criação e abertura para escrita admitidas). A formulação do revisor («esse
      ator está dentro de quem escreve o diretório do destino») é REJEITADA: com `only_inherit` o ator
      pode não escrever o diretório do destino; o doc declara o ator pela forma (quem as permissões do
      diretório privado e do temporário admitem) e a asserção do teste passou a dizer «bits de modo
      apenas».
    - B-R2-CL-3 ACEITO: «o arquivo inteiro ou nenhum» e a regra «use só a cópia de uma execução que
      imprimiu snapshot copied to» levam as duas qualificações (máquina de pé; ninguém mais escrevendo o
      diretório do destino ou o que a chamada cria nele) no doc, na docstring e na docstring da classe
      de teste; o parágrafo de adulteração diz que o comando pode então imprimir «snapshot copied to»
      sobre bytes que não são o snapshot. Qualquer CHANGELOG ou headline da 1.4.2 que reuse a frase
      precisa das qualificações — na forma de TRÊS partes fixada na revisão de `6b46e92a` (abaixo);
      só estas duas deixavam de fora quem muda o que um diretório do caminho resolve.
    - B-R2-CL-4 ACEITO: a classe dos sinais passou a ser pela disposição em vigor (ação padrão que
      encerra o processo; o comando não instala handler) — SIGINT vira exceção (limpeza roda; sonda D5:
      rc -2, nada sobra) e SIGPIPE é ignorado (cópia completa, rc 0) — na rodada 2 do fix, pela forma:
      os sinais cuja disposição o próprio Python fixa na partida; SIGXFSZ também é ignorado (write
      além do limite de tamanho ⇒ `EFBIG`, rc 2, nada sobra — medido); SIGQUIT entra na classe (D5:
      rc -3, sobra o diretório privado).
    - B-R2-CL-5, B-R2-CL-6, B-R2-CL-7 ACEITOS (texto): atribuições da rodada 2 do Codex (conferido em
      `codex-review-r2.txt`: «R1-2 OPEN», busca case-insensitive nativa verificada, reprodução em
      sistema de arquivos em memória, nenhuma menção a U+017F); medições antigas datadas; «anything at
      FILE that the command did not create»; `--out ""` de script não registrado sai 7.
    - Prova: com os testes desta rodada e o `ceo-launches.py` da lane ANTES dela (sha256 `f2e83508…`),
      3 dos 41 testes de `relaunch` ficam vermelhos — exatamente os 3 que fixam o M1; os outros 4 novos
      ficam verdes por desenho (fixam comportamento que já existia e nenhum teste fixava). Mutação (uma
      por vez, `-k 'relaunch or Relaunch'`, bytes restaurados por sha256): as 6 sobreviventes do
      revisor (X1, X2, X3, X6, X14, X19, anchors atualizados), a retirada da conferência pós-`link`
      (MP), a divergência aceita (MPF) e o destino ilegível aceito (MPU) ⇒ 9 vermelhas; controle X4
      vermelho. Sondas D1–D7 das frases novas (ACL herdada, `only_inherit`, umask 0177, `deny
      add_subdirectory`, SIGINT/SIGPIPE/SIGQUIT, troca antes do `link`, ACL por cima do modo); a sonda
      C2 da rodada 1, re-executada sobre o código desta rodada, dá a recusa nomeada. Suíte ALVO inteira
      (Python 3.9.6, macOS APFS, 2026-09-23, load ≈ 5): 92 testes na lane, 92 verdes; com o
      `ceo-launches.py` de HEAD `19771fa1` ⇒ 30 vermelhos, todos por `AssertionError` (os 23 da rodada
      1 + os 7 novos), 62 verdes — numa segunda execução, o flake ambiental registrado acima
      (`test_manifest_is_on_disk_before_git_runs`, `FileNotFoundError` do `git` falso; não toca o
      `ceo-launches.py`) somou 1.
  - Resíduos declarados pela FORMA em `docs/workflow-recovery.md` («`relaunch --out` (declared)»):
    fim sem limpeza (sinal ainda na ação padrão que encerra o processo, queda de energia) ou
    interrupção fora do trecho protegido ⇒ sobra o diretório privado, talvez com o temporário dentro
    (nunca um parcial no nome do destino); o diretório do destino é confiado como o do ledger — quem o
    escreve pode trocar o que está sob o nome do diretório privado e fazer a limpeza por nome remover
    um diretório vazio dele; quem as permissões do diretório privado e do temporário admitem (o mesmo
    usuário; no macOS, quem uma ACL herdável nomeia) pode alterar o temporário no lugar, e então o
    comando pode imprimir «snapshot copied to» sobre outros bytes; só o último componente não é
    seguido; a classe de ambientes da «Regra de parada» ⇒ recusa; diretório 0300 recusado só sem
    `O_PATH`/`O_SEARCH`; nada afirmado depois de queda de energia.
    Frases do doc ANTERIOR sondadas contra o código na lane (sonda de 2026-09-22 no scratchpad da
    S357, sobre o doc de antes da rodada 1 da revisão do build: 18/18 verdadeiras — destino presente
    recusado antes de qualquer criação, modos 0700/0600, `fsync` só do temporário, grafia equivalente
    recusada, sem diretório privado ⇒ recusa, falha de remoção pós-`link` ⇒ cópia inteira e sobra
    nomeada, nomes que não nomeiam arquivo recusados, nada sobrando). As frases da rodada 1: sondas
    C1–C5 (acima); as da rodada 2: sondas D1–D7 (acima).
  - **Revisão do build 1.4.2, fix rodada 2 (2026-09-23 ~05:35, antes das 06:00 do Owner):**
    - B-R2-MECH-1 ACEITO (texto; condição do land, não defeito): FAT (msdos) MEDIDO pelo revisor —
      lane recusa com `link` `ENOTSUP`, `19771fa1` publica; registrado na classe acima e no doc. Segue
      pendente a ratificação da CLASSE pelo Owner; a entrada do CHANGELOG 1.4.2 (fora da lane) nomeia a
      classe pela forma.
    - B-R2-MECH-2 ACEITO (doc): sobra depois do `link` é um segundo nome de FILE (mesmo inode) — apagar,
      nunca editar.
    - B-R2-MECH-3 ACEITO (testes): o atalho que não consegue ler o destino recusa «cannot inspect» sem
      criar nada; nenhum descritor fica aberto (contagem em `/dev/fd`). O teste de descritor fica verde
      também no código anterior por desenho (guarda, não reprodução).
    - B-R2-MECH-4 ACEITO (código): o atalho e o laço de escrita nomeiam o errno por `_why` (medido:
      `OSError EFBIG`, `PermissionError EACCES`).
    - B-R2-MECH-5 ACEITO (código): `--out` que falha para script não registrado no lançamento sai 7
      (`2 if exact_script else 7`), como diz o texto de uso; só manifesto editado à mão chega lá.
    - B-R2c-CL-1 ACEITO (código, cura ESTRUTURAL): o diretório privado é aberto como o do destino
      (`_DEST_DIR_FLAGS | O_NOFOLLOW`, só busca onde há `O_PATH`/`O_SEARCH`), então só os bits de
      escrita e busca do dono importam e a forma declarada fica exata; a falha separa «opening the
      private directory» de «creating the temporary». Sonda (`laneB/probe-fix2.txt`, macOS): umask 0400
      e 0477 ⇒ publica inteiro; 0177 e 0100 ⇒ recusa na abertura; 0200 ⇒ recusa na criação; nada sobra
      — o passo que recusa é o do macOS (`O_SEARCH`); no Linux (`O_PATH`) as três recusam na criação do
      temporário (medido na revisão de `6b46e92a`, abaixo). Onde
      nenhuma das duas flags existe, o diretório privado segue aberto para leitura (o mesmo membro do
      diretório 0300).
    - B-R2c-CL-2 ACEITO (texto): sinais pela forma — os que o Python fixa na partida (SIGINT vira
      exceção; SIGPIPE e SIGXFSZ ignorados; medido `EFBIG`, rc 2, nada sobra).
    - B-R2c-CL-3, B-R2c-CL-4, B-R2c-CL-5, B-R2c-CL-6 ACEITOS (texto): mecanismo em vez de absoluto no
      rito; «anything else that can be read»; NFS «can answer»; diretório resolvido UMA vez e todo
      diretório do caminho na qualificação (nesta rodada, só no marcador de limitações do doc; as
      demais frases o ganharam na revisão de `6b46e92a`, abaixo); «link cuja checagem de identidade
      passou» neste plano.
    - Prova: com os testes desta rodada e o `ceo-launches.py` de antes dela, 4 vermelhos de 5 alvo
      (`laneB/red-before-fix2.txt`); com o código novo, arquivo-alvo inteiro 96 verdes
      (`laneB/green-after-fix2.txt`). Dois testes antigos mudaram de expectativa pela cura estrutural
      (symlink sob o nome do diretório privado ⇒ agora «opening the private directory»; umask 0177 ⇒
      recusa, como já declarado).
  - **Revisão do build 1.4.2 sobre `6b46e92a` (2026-09-23; revisores Claude do workflow `v142-build`,
    lentes de mecanismo e de afirmações):** 4 achados de mecanismo (B-R2-MECH-L1 P1, L2..L4 P2) e 8 de
    afirmações (B-RV2-CL-1 e -2 P1, -3..-8 P2). SUJEITO revisado: o commit `6b46e92a` —
    `ceo-launches.py` `56e5d790…`, testes `ab97ec39…`, doc `a185ce49…`, este plano `fc9db4af…`. O
    relato do builder que cita `25f3ecf8…`/`e44184e3…`/«92 passed» é de bytes ANTERIORES e fica
    substituído (B-R2-MECH-L4); veredito ou ratificação que o cite estaria preso ao sujeito errado.
    Nenhum achado tem a forma da classe de parada: o P1 é a expectativa de um teste por plataforma;
    o comportamento (rc 2, nada publicado, nada sobra) é o mesmo nos dois sistemas. Destino de cada um:
    - B-R2-MECH-L1 + B-RV2-CL-2 ACEITOS (o mesmo defeito, MEDIDO): em contêiner Linux (colima, kernel
      6.8, Python 3.9.25 e 3.12.14, uid 1000, ext4; o CI roda o arquivo em Ubuntu não-root) o teste de
      umask de `6b46e92a` fica VERMELHO — 1 falho, 95 verdes, nas duas versões — com «creating the
      temporary: PermissionError EACCES» para 0177. Cura no TESTE: o passo que recusa vem da flag que a
      plataforma expõe (`O_PATH`: nenhuma máscara recusa na abertura; `O_SEARCH`: 0177 e 0100 na
      abertura; fallback `O_RDONLY`: 0400 e 0477 na abertura; o resto das máscaras que tiram escrita
      ou busca, na criação); teste NOVO força a flag `O_RDONLY` e fixa o fallback nos dois sistemas.
      O comentário do código diz que bit cada flag confere; o plano (acima) e o doc dizem o passo por
      plataforma. Sonda por máscara nos dois sistemas (`laneB/probe-fix3-umask-macos.txt`,
      `laneB/probe-fix3-umask-linux.clean.txt`): toda recusa é `EACCES`, nada sobra.
    - B-R2-MECH-L2 ACEITO (texto): a classe que sai do rc 0 é declarada pela FORMA — qualquer operação
      que a forma nova faz além da de `19771fa1` (o `fsync` incluído), recusada ou falhando — na
      «Regra de parada» e no doc; a entrada do CHANGELOG herda essa forma.
    - B-R2-MECH-L3 + B-RV2-CL-7 ACEITOS pela forma do TEXTO, sem código: a janela é «entre uma criação
      e o momento em que o comando a registra, ou dentro da limpeza»; uso e docstring dizem «once this
      call has recorded that its exclusive create succeeded». Fechar a janela com
      `signal.pthread_sigmask` fica REJEITADO nesta rodada: a máscara vale só para a thread que a
      chama e não alcança um SIGINT recebido antes dela (o handler em C do Python já o anotou; a
      exceção sai num ponto posterior do interpretador), então estreitaria a janela sem fechá-la; o
      destino nunca é afetado e a sobra já está declarada.
    - B-R2-MECH-L4 ACEITO: sujeito nomeado acima; `laneB/RESUME-lane-b-S357.txt` ganhou cabeçalho de
      substituição.
    - B-RV2-CL-1 ACEITO (medido pelo revisor, `review/b_r2cl_probe.out` P1: symlink do CAMINHO
      re-apontado para dentro do diretório privado durante a escrita ⇒ o caminho FILE lê 10 de 10000
      bytes e `_write_new_file` devolve sucesso): toda frase do «arquivo inteiro ou nenhum» leva a
      qualificação de TRÊS partes pela forma — ninguém mais escrevendo o diretório do destino como a
      chamada o abriu; mudando o que um diretório do caminho resolve (rename, symlink re-apontado,
      mount); escrevendo o que a chamada cria — no rito e na regra do «snapshot copied to» (doc), na
      docstring de `_write_new_file` e na da classe de teste; o marcador de limitações diz que toda
      outra formulação carrega os mesmos limites.
    - B-RV2-CL-3 ACEITO: «never leaves a file holding part of the copy» passou a valer «while the
      machine stays up, and within the trust the next bullets declare».
    - B-RV2-CL-4 ACEITO: o membro rc 2 → 7 entrou na «Regra de parada»; o doc qualifica «creates no
      file» com «for a record the hook wrote» e diz que todo rc 2 do `--out` é rc 7 para registro cujo
      script não foi registrado no lançamento. A mensagem do commit `6b46e92a` («keeps» 7) fica
      corrigida por este registro; o commit wip é re-mensageado no land.
    - B-RV2-CL-5 ACEITO: o doc lista os casos não declarados da v1.4.1 (`--out` ignorado para
      workflow nomeado; `--out ""` tomado como omitido; segunda leitura que mudou, impressa e copiada —
      todos rc 0), conferidos em `19771fa1`.
    - B-RV2-CL-6 ACEITO: a abertura do diretório privado acima diz as flags reais.
    - B-RV2-CL-8 ACEITO: a recusa é «em vez de escrever FILE no lugar (a forma da v1.4.1, que podia
      deixar parte da cópia sob FILE)» — o `O_EXCL` de `19771fa1` nunca substituía.
    - Prova: com o `ceo-launches.py` de `6b46e92a` e os testes novos, os dois testes mexidos ou novos
      ficam verdes no macOS (`laneB/red-before-fix3.txt`) — a mudança de código é só de comentário e
      docstring, e o defeito era a expectativa no Linux. Linux (contêiner): `6b46e92a` ⇒ 1 falho, 95
      verdes em 3.9 e 3.12 (`laneB/linux-red-before-6b46e92a-py{39,312}.clean.txt`). Mutação
      (`laneB/mut-fix3/`): M-N2 (diretório privado aberto `O_RDONLY` sempre) morta pelo teste de umask
      nos dois sistemas; M-FB (flag do diretório privado que não vem de `_DEST_DIR_FLAGS`) morta pelo
      teste novo do fallback nos dois. Bytes resultantes: `ceo-launches.py` `18ef9bc4…`, testes
      `45544670…`, doc `0be00205…`; sobre eles, arquivo-alvo inteiro 97 verdes no macOS (Python 3.9.6,
      APFS; `laneB/green-after-fix3-final-macos.txt`) e no Linux em 3.9 e 3.12
      (`laneB/green-after-fix3-final-linux-py{39,312}.txt`).
  - Falta: a decisão do Owner sobre a emenda da forma (diretório privado em vez de temporário solto
    no mesmo diretório), sobre as mudanças de rc da «Regra de parada» — incluindo a CLASSE de
    ambientes que saem do rc 0 e o membro rc 2 → 7 —, sobre o B-R1-1 (b) rejeitado e sobre
    `F_FULLFSYNC` (B-CL-4); o CI Linux no land (a perna Linux rodou em contêiner só para o
    arquivo-alvo); a bateria completa (etapa separada); a entrada do CHANGELOG da 1.4.2 (fora desta
    lane; qualquer «o arquivo inteiro ou nenhum» nela leva as TRÊS partes da qualificação: máquina de
    pé; e, durante a chamada, ninguém mais escrevendo o diretório do destino como a chamada o abriu,
    mudando o que um diretório do caminho resolve, ou escrevendo o que a chamada cria); o land,
    depois da tag GA da 1.4.1.

## Ratificação do Owner (S357, 2026-09-28 17:19 -0300)

Registrada pelo `OWNER-S357-MORNING.sh` (etapa 2), com o Owner digitando `RATIFICO` depois de ler,
na tela, as seções «W2 — cura estrutural» e «Regra de parada» deste plano e as seis decisões que a
W2 deixou pendentes, aceitas como estão acima:

1. **Forma:** o temporário fica dentro de um diretório PRIVADO `.ceo-launches-out-<16 hex>` (0700)
   criado dentro do diretório do destino (emenda da rodada 2 da sonda Codex).
2. **Contrato:** `relaunch --out` de workflow NOMEADO passa de rc 0 a rc 2; snapshot que não relê
   igual passa de rc 0 a rc 7; `--out ""` passa de rc 0 a rc 2; e as mudanças menores nomeadas em
   «Regra de parada» (`--out` de script não registrado segue rc 7, com uma linha em stderr; o
   membro rc 2 → rc 7 do manifesto editado à mão).
3. **Classe de ambientes:** ratificada a CLASSE, pela forma, que passa de rc 0 a recusa nomeada
   (rc 2), descrita em «Regra de parada».
4. **Onde fica:** neste follow-up (W2), não numa wave própria do PLAN-190.
5. **B-R1-1 (b):** ratificada a REJEIÇÃO (não conferir dono e modo do diretório privado depois de
   abri-lo), pelos motivos registrados em «Progresso».
6. **`F_FULLFSYNC` (B-CL-4):** não adotado; fica a forma decidida «write + fsync», com a
   qualificação registrada em «Progresso» (nada é afirmado depois de uma queda de energia).

Isto fecha as quatro decisões do Owner listadas em «Falta:» (a emenda da forma; as mudanças de rc
da «Regra de parada», com a CLASSE de ambientes e o membro rc 2 → 7; o B-R1-1 (b) rejeitado; o
`F_FULLFSYNC`) e a pergunta da «Regra de parada» sobre onde a W2 fica (itens 1–6 acima). Os demais
itens de «Falta:» não são decisões do Owner: o CI Linux e a bateria completa ficam com o CI do push
deste commit, a entrada do CHANGELOG da 1.4.2 é do portão 5b da esteira e o land depois da tag GA
da 1.4.1 é este commit.
