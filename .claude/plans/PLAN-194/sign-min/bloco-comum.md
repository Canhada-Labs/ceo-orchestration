## O SIGN deste pacote (bloco comum a todos os pacotes do molde sign-min)

Este texto é assinado pelo arquivo citado em `Molde:`, que executa o núcleo `.claude/plans/PLAN-194/sign-min/sign_min.py`, com os dados do arquivo citado em `Dados:`; os três estão no commit `Anchor-SHA`.

**Antes de escrever qualquer coisa no clone**, o SIGN confere, só por leitura, e recusa com o fato medido e rc 1, sem criar nem alterar arquivo na árvore nem no `.git` do clone (inclusive os bytes do `.git/index`):
- a entrada foi chamada por um caminho com «/», o PATH só tem diretórios absolutos, o `python3` está no PATH e o núcleo tem o sha256 informado pelo roteiro;
- o ambiente recebido pelo núcleo só tem nomes da lista do molde ou os 6 nomes que o `python3` do sistema acrescenta;
- o diretório atual é a raiz do clone, com um `.git` próprio;
- no modo real, a entrada padrão é um terminal e `GPG_TTY` é esse terminal;
- `git`, `gpg` e `bash` estão no PATH; o SIGN fixa o caminho absoluto e o sha256 do arquivo de `git` e do de `gpg`, e daí em diante executa `git` e `gpg` só por esses caminhos;
- `core.hooksPath` tem um único valor, `/dev/null`, e `core.fsmonitor` um único valor, falso, ambos vindos do `.git/config` do clone;
- a identidade do commit vem só da configuração do git;
- não há arquivo `*.lock` sob `.git`;
- `HEAD` é `refs/heads/main` e aponta para o mesmo commit que `refs/remotes/origin/main` do clone; esse commit é o `Anchor-SHA`;
- nenhum caminho rastreado tem atributo `filter`;
- `git status` não lista nada, nem arquivo não rastreado ou ignorado;
- cada arquivo rastreado tem na árvore os bytes e o bit de execução do índice, e todo modo do índice é 100644 ou 100755;
- os dados seguem a gramática do molde; o patch só cria, modifica ou remove arquivos, sem renomear, sem mudar modo, sem tocar `.gitattributes` nem o diretório do molde; cada pré-imagem é a do `Anchor-SHA`; e o patch aplica;
- este texto tem os 4 campos por preencher, este bloco igual ao `bloco-comum.md` do molde, e o `Scope` igual aos caminhos do patch;
- a `.asc` deste texto não existe no `Anchor-SHA`;
- o registro do rail citado nos dados traz o sha256 do patch, deste texto com os campos por preencher e dos dados, e o veredito APPROVE ou DECLARED-P2;
- os caminhos canônicos do patch, segundo o oráculo `--is-canonical`, são os declarados nos dados, e nenhum caminho do patch é do kernel;
- `python3` importa `pytest` e `xdist`; o allowlist `.claude/sentinel-signers.txt` do `Anchor-SHA` carrega sem erro e não está vazio; e o gpg tem uma chave secreta dele.

**Depois disso, nesta ordem**, o SIGN: cria um diretório temporário sob `/tmp` para os logs; aplica o patch ao índice e à árvore; confere que o índice difere do `Anchor-SHA` exatamente nas linhas `index` do patch (caminhos, modos e blobs) e que cada arquivo rastreado tem na árvore os bytes e o bit de execução do índice; roda cada comando `hard` dos dados, que tem de sair com rc 0 e, quando é `python3 -m pytest`, terminar com um resumo só de testes aprovados; roda o pytest sobre as raízes do `testpaths` do `pytest.ini`, nas duas passadas da divisão de marcadores do CI (`not serial` com `-n auto`, e `serial`), conta erro de coleta como falha, repete isolado até 3 vezes cada teste que falhou numa passada e conta como falha o que não terminou, em nenhuma repetição, com resumo só de aprovados; roda os gates de corpus (check-test-env-hygiene, env-inventory-check, check-active-hooks-executable, check-contamination, build-plugin --check, gen-command-skill-hook-map --check, check-docs-freshness, check-docs-drift, verify-counts --no-tests, check-claude-md-claims, check-ceremony-script, check-staleness e validate-governance), cada um com rc 0, sobre a árvore com o patch e com este texto ainda com os campos por preencher; os comandos `hard`, o pytest e os gates recebem um `GNUPGHOME` vazio, um `TMPDIR` com o caminho real, sem link simbólico, de um diretório da bateria criado dentro do diretório temporário, e nenhum `GPG_TTY`, cada um roda num grupo de processos próprio, e o SIGN falha se esse grupo ainda tem processo vivo 10 s depois de o comando terminar; confere de novo que a configuração efetiva do git é a lida no início, que `HEAD`, `refs/heads/main` e `refs/remotes/origin/main` são os lidos no início, que nenhum caminho rastreado tem atributo `filter`, o índice e a árvore, e que `git` e `gpg` resolvem no PATH para os mesmos caminhos, com o mesmo sha256 do início; preenche os 4 campos; assina este texto com a chave escolhida e verifica a assinatura com o `gpg_verify` e o allowlist lidos do `Anchor-SHA` antes da bateria, executando o `gpg` pelo caminho fixado; grava este texto e a `.asc` no índice pelos bytes assinados, sem filtro, e confere o índice e a árvore; faz um `git commit` sem editor, sem hooks e sem assinatura do git; e confere o commit. Depois da assinatura, o SIGN não inicia nenhum programa lido da árvore com o patch; um descendente da bateria que tenha saído do próprio grupo de processos não é conferido e pode continuar rodando.

**O que o SIGN entrega, e só com rc 0:** um commit em `refs/heads/main` deste clone cujo único pai é o `Anchor-SHA`, que difere dele exatamente nos caminhos do patch (com os blobs e modos das linhas `index`), neste texto e na `.asc`, com os bytes assinados; a `.asc` lida desse commit verifica com a mesma chave; autor e committer são a identidade conferida. Com qualquer outro rc, o SIGN não afirma nada: cada linha impressa antes vale só para o passo que ela relata.

**Requisitos** (o que o SIGN precisa encontrar; ele não diz de onde vêm):
- o bash começa com o ambiente montado por `env -i`: sem `BASH_ENV`, sem `ENV` e sem função importada;
- nenhum processo além do SIGN e dos comandos que ele inicia escreve no clone nem no diretório temporário durante a execução;
- a configuração efetiva do git no clone, no início, não define programa que o git execute além do que o SIGN confere acima;
- `/tmp` gravável; no PATH, `git`, `gpg`, `bash` e `python3`;
- nada troca, durante a execução, o que o `git` e o `gpg` carregam ou executam (bibliotecas, o programa para o qual um executável delega, o gpg-agent e o pinentry): o SIGN confere só o sha256 dos dois executáveis;
- no modo real, a chave do allowlist utilizável pelo gpg, com pinentry no terminal, o gpg-agent iniciado sem a senha em cache e a senha não guardada no chaveiro do sistema;
- um `HOME` gravável pelos testes da bateria.

**Publicação:** o Owner publica o commit no `main` do origin, sem force, pelo roteiro; o SIGN não faz push nem fetch.

**Fora do estado esperado:** o SIGN não diagnostica execução anterior, não desfaz e não apaga nada; recusa ou falha com o fato medido, e o clone e o diretório temporário ficam como estiverem. Depois que o núcleo restaura a disposição padrão dos sinais (nas suas primeiras instruções), um sinal INT, PIPE, TERM ou KILL encerra o SIGN sem linha nova dele.
