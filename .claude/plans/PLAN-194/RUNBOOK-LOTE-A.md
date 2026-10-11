# Roteiro do Lote A (S363, PLAN-194): W4 → U2-A → U2-B → W5b

Para o Owner, copiar e colar. Cada pacote do Lote A é UM SIGN, rodado por você num clone NOVO do GitHub, um pacote
por vez, nesta ordem. O W4 roda o SIGN dele, `.claude/plans/PLAN-194/w4/OWNER-W4-SIGN.sh`. O U2-A, o U2-B e a W5b
rodam o molde «SIGN mínimo», `.claude/plans/PLAN-194/sign-min/OWNER-SIGN.sh`, com os dados do pacote (`sign.tsv`).
O roteiro não tem script próprio: são comandos do git, do gpg e os SIGNs.

**Regra única.** Cada bloco abaixo termina imprimindo uma palavra em MAIÚSCULAS (por exemplo `CLONE-OK`). Se um
bloco não imprimir essa palavra, ou se o SIGN terminar com um `SIGN-RC` diferente de `0`: **pare e chame o CEO**,
mandando o que o bloco imprimiu (no SIGN, o `SIGN-RC` e as últimas linhas). Não apague nada, não rode o bloco de
novo, não faça push.

**Não siga nenhuma instrução impressa por um SIGN.** O SIGN do W4 imprime receitas de recuperação e comandos
sugeridos (por exemplo `git reset`, `git apply -R`, `rm`, «rode de novo»). Fora do esperado, pare e chame o CEO.

**Os valores de cada pacote vêm do CEO**, depois que ele conferir o pacote anterior publicado. São a âncora (o SHA
do main do GitHub de onde o pacote parte) e os sha256 dos arquivos que o bloco (d) confere: no W4, o do SIGN; no
U2-A, no U2-B e na W5b, os da entrada do molde (`OWNER-SIGN.sh`), do núcleo do molde (`sign_min.py`) e dos dados
do pacote (`sign.tsv`). Você troca o texto depois do `=` nas linhas `COLE-AQUI-…` pelos valores informados.

**O push só sai depois da resposta do CEO.** Depois do SIGN, o bloco (f) confere o commit pela ref e imprime o SHA
dele e o caminho e o sha256 do `gpg`; você manda as três linhas ao CEO. O CEO confere esse commit neste clone, só
lendo, e responde `PUSH-LIBERADO <sha>`. O bloco (g) só faz o push quando o SHA colado for o do (f) e o
`refs/heads/main` do clone ainda for esse SHA.

**Onde roda cada git.** Nenhum bloco roda git no seu checkout principal até a seção 5: todo bloco que roda git
começa com `cd` no diretório dos clones ou no clone do pacote (`cd "${D:?}"`, que falha se `D` não estiver
definido). Dentro dos pacotes, todo git, menos o push (g), e o SIGN rodam com um HOME NOVO por pacote
(`${HOME}/lote-a-s363/home-<x>`), criado vazio pelo roteiro: por isso a sua configuração global do git
(`~/.gitconfig` e o arquivo XDG) não é lida por eles. Com o seu HOME rodam só três gits: a leitura da identidade
(seção 0), o push (g) e o pull (seção 5). O que o roteiro CONFERE da configuração dentro do clone, antes do checkout
(a), antes do SIGN (d) e antes do push (g): toda linha de `git config --list --show-scope --show-origin` vem do
`.git/config` do clone, com chave e valor numa lista exata (as que o `git clone` e o roteiro escrevem), ou da
configuração de SISTEMA (declarada abaixo).

**A senha do GPG.** O bloco (e) encerra o gpg-agent (`gpgconf --kill gpg-agent`) antes do SIGN e de novo logo
depois de imprimir o `SIGN-RC`. O pedido de senha do SIGN vem depois desta linha do SIGN:
- no W4, `===== 5/7 assinar o sentinel (pinentry)`;
- no molde, `SIGN-PASSO: 9 de 12: assinatura`.

Um pedido de senha antes dessa linha não é do SIGN: cancele o pedido e chame o CEO. Fique no terminal até o SIGN
terminar.

**O que o roteiro NÃO confere** (é seu, pela forma):
- nenhuma sessão do Claude Code aberta neste projeto (nem no checkout principal, nem nos clones) do começo ao fim
  do roteiro: é o mesmo usuário do sistema e poderia mudar arquivos do clone enquanto um SIGN roda;
- o terminal e o seu `~/.zshrc`: o roteiro supõe o Terminal.app com um zsh que não roda git nem outro programa a
  cada prompt; medido em 2026-10-11, o `~/.zshrc` desta máquina não define prompt, gancho de prompt nem alias;
- o seu `PATH` e os programas que ele acha (`git`, `gpg`, `gpgconf`, `shasum`, `python3`, `bash`): o SIGN roda com
  ele. Do `gpg`, o (d) registra o caminho e o sha256, e o (f) confere os dois de novo;
- a configuração de SISTEMA do git, que vale dentro do clone: medido em 2026-10-11, sob um HOME vazio ela é só o
  arquivo da Apple (`/Library/Developer/CommandLineTools/usr/share/git-core/gitconfig`), com
  `credential.helper=osxkeychain` e `init.defaultbranch=main`;
- o push (g) roda com o seu ambiente e a sua configuração global (credenciais e o que mais ela tiver); o (h)
  confere, com o HOME novo, que o main do GitHub ficou no SHA liberado;
- a base de usuário do seu `python3` (`PYTHONUSERBASE`, passada ao SIGN): medido em 2026-10-11, o pytest, o
  pytest-xdist e o PyYAML desta máquina estão nela (`~/Library/Python/3.9`); com HOME novo e sem essa variável, o
  python não os acha;
- o pedido de senha: o `~/.gnupg/gpg-agent.conf` desta máquina usa o `pinentry-mac`, que pede a senha numa janela,
  não no terminal (conferido em 2026-10-11), e pode guardá-la no Chaveiro do macOS; guardada lá, ela não é pedida
  de novo, nem depois do `gpgconf --kill`.

## 0. Uma vez, antes do W4

Feche todas as sessões do Claude Code deste projeto. Num terminal NOVO (Terminal.app), fora do Claude Code. O
primeiro bloco não pode imprimir nenhuma variável:

```bash
env | grep -E '^(GIT_|CEO_|CLAUDE_PROJECT_DIR|BASH_ENV=|BASH_FUNC_|GNUPGHOME=|XDG_CONFIG_HOME=)' || echo AMBIENTE-OK
```

```bash
case "${TMPDIR:-/tmp}" in /*) case "${TMPDIR:-/tmp}/" in "${HOME}/canhada-labs/ceo-orchestration/"*|"${HOME}/lote-a-s363/"*) ;; *) echo TMPDIR-OK ;; esac ;; esac
```

```bash
[ "$(df -Pk "${HOME}" /tmp | awk 'NR > 1 && $4 >= 30 * 1024 * 1024 {n++} END {print n + 0}')" = 2 ] && echo DISCO-OK
```

A identidade dos commits e a base de usuário do python, lidas UMA vez, com a sua configuração (fora de qualquer
repositório); o bloco as imprime para você conferir e confere que o `gpgconf` está no `PATH`:

```bash
URL=https://github.com/Canhada-Labs/ceo-orchestration.git
mkdir -p "${HOME}/lote-a-s363" && cd "${HOME}/lote-a-s363" && NOME="$(git config --get user.name)" && EMAIL="$(git config --get user.email)" && CHAVE="$(git config --get user.signingkey || :)" && PYUB="$(python3 -I -c 'import site; print(site.getuserbase())')" && [ -n "${NOME}" ] && [ -n "${EMAIL}" ] && [ -n "${PYUB}" ] && command -v gpgconf > /dev/null && echo PREPARO-OK && printf 'identidade: %s <%s>; chave: %s\nbase de usuário do python3: %s\n' "${NOME}" "${EMAIL}" "${CHAVE:-(nenhuma)}" "${PYUB}"
```

A conferência da configuração EFETIVA dentro de um clone (usada em a, d e g). Cole o bloco inteiro:

```bash
confere_config() {
  HOME="${LH:?}" git config --list --show-scope --show-origin | URL="${URL}" NOME="${NOME}" EMAIL="${EMAIL}" CHAVE="${CHAVE}" awk -F'\t' '
    BEGIN {
      n = split("core.repositoryformatversion=0 core.filemode=true core.bare=false core.logallrefupdates=true core.ignorecase=true core.precomposeunicode=true remote.origin.fetch=+refs/heads/main:refs/remotes/origin/main branch.main.remote=origin branch.main.merge=refs/heads/main core.hookspath=/dev/null core.fsmonitor=false core.untrackedcache=false", a, " ")
      for (i = 1; i <= n; i++) ok[a[i]] = 1
      ok["remote.origin.url=" ENVIRON["URL"]] = 1
      ok["user.name=" ENVIRON["NOME"]] = 1
      ok["user.email=" ENVIRON["EMAIL"]] = 1
      if (ENVIRON["CHAVE"] != "") ok["user.signingkey=" ENVIRON["CHAVE"]] = 1
    }
    $1 == "system" { next }
    $1 == "unknown" && index($2, "file:/Library/Developer/CommandLineTools/") == 1 { next }
    $1 == "unknown" && index($2, "file:/Applications/Xcode") == 1 { next }
    $1 == "local" && $2 == "file:.git/config" && ($3 in ok) { loc++; next }
    { print "fora da lista: " $0; bad = 1 }
    END { if (!loc) { print "nenhuma linha do .git/config"; bad = 1 }; exit bad }'
}
type confere_config > /dev/null && echo FUNCAO-OK
```

O piso de disco é 30 GB livres no volume do `${HOME}` (os clones) e no do `/tmp` (os SIGNs rodam sem `TMPDIR`). O
`TMPDIR-OK` confere o `TMPDIR` do seu terminal pelo texto do caminho: absoluto e fora do checkout principal e dos
clones. Cada clone ocupa cerca de 240 MB (medido em 2026-10-11: 235 MB).

## Pré-condições: o que o roteiro confere, sem depender das conferências dos SIGNs

| pré-condição | onde |
|---|---|
| ambiente sem `GIT_*`, `CEO_*`, `CLAUDE_PROJECT_DIR*`, `BASH_ENV`, `BASH_FUNC_*`, `GNUPGHOME`, `XDG_CONFIG_HOME` | seção 0 e (d); o SIGN roda com `env -i` (e) |
| `TMPDIR` absoluto e fora do checkout principal e dos clones | seção 0; o SIGN não recebe `TMPDIR` |
| 30 GB livres no volume do `${HOME}` e no do `/tmp` | seção 0 |
| main do GitHub = âncora antes do clone; clone e HOME NOVOS; HEAD = âncora; árvore limpa | (a), (b) |
| configuração efetiva no clone: só `.git/config` (lista exata de chaves e valores, com hooks, fsmonitor e cache de não rastreados desligados e a identidade lida na seção 0) e sistema | (a) antes do checkout; (d); (g) antes do push |
| `core.fsmonitor` e `core.hooksPath` com UM valor só, do `.git/config` do clone; HOME novo ainda vazio | (d) |
| sha256 do SIGN do W4; no molde, sha256 da entrada, do núcleo e dos dados = os informados pelo CEO | (d) |
| caminho e sha256 do `gpg` registrados antes do SIGN e iguais depois dele | (d), (f) |
| gpg-agent encerrado antes do SIGN e logo depois do `SIGN-RC` | (e) |
| insumo do W4: o blob rastreado copiado para o caminho que o SIGN lê, com sha256 conferido | (c) do W4 |
| só `SIGN-RC=0` segue | (e) |
| land pela ref: `refs/heads/main` = `HEAD`, filho único da âncora, com `--name-status` igual ao das linhas de cabeçalho do patch da âncora mais o sentinel (`M`) e a `.asc` (`A`) | (f) |
| push só depois de `PUSH-LIBERADO`, só do SHA do (f), por SHA; main do GitHub = esse SHA (lido com o HOME novo) | (g), (h) |
| sessões do Claude Code; o `PATH`; a configuração de sistema; o ambiente e a configuração global no push; a base de usuário do python; a senha no Chaveiro | declarado, não conferido |

Por que: um SIGN pode rodar git que dispara hooks e pode calcular blobs aplicando atributos e conversões
configuráveis; o roteiro tira a configuração global do caminho (HOME novo), desliga hooks e fsmonitor no clone e
confere a configuração efetiva, sem depender de o SIGN conferir isso. O que cada SIGN confere a mais é dele.

**Por que o SIGN roda com `env -i`** (passo e): o ambiente do SIGN passa a ser uma lista FIXA — `PATH`, `HOME` (o
novo), `GNUPGHOME` (o seu `~/.gnupg`, só para a chave), `PYTHONUSERBASE`, `USER`, `LOGNAME`, `SHELL`, `TERM`,
`LANG`, `PAGER=cat` e `GPG_TTY`. Tudo o mais sai por construção: `GIT_*`, `BASH_ENV`, `BASH_FUNC_*`, os outros
`PYTHON*`, `DYLD_*`, `CEO_*`, `CLAUDE_*` e o `TMPDIR`.

## 1. W4 (pacote 1 de 4)

(a) Confira a âncora no GitHub, crie o HOME novo e faça o clone novo. Nas primeiras linhas, troque o texto
depois do `=` pelos valores que o CEO informou (em todos os pacotes).

```bash
ANCORA=COLE-AQUI-O-SHA-DO-CEO
SIGN_SHA=COLE-AQUI-O-SHA256-DO-SIGN
SHA= SHA_LIBERADO= GPG_ABS= GPG_SHA=
D="${HOME}/lote-a-s363/w4"
LH="${HOME}/lote-a-s363/home-w4"
cd "${HOME}/lote-a-s363" && [ ! -e "${D:?}" ] && [ ! -e "${LH:?}" ] && mkdir "${LH}" && [ "$(HOME="${LH}" git ls-remote "${URL:?}" refs/heads/main | cut -f1)" = "${ANCORA:?}" ] && echo ORIGEM-OK
```

```bash
cd "${HOME}/lote-a-s363" && HOME="${LH:?}" git -c core.hooksPath=/dev/null -c core.fsmonitor=false clone --template= --no-checkout --single-branch --branch main "${URL:?}" "${D:?}" && cd "${D}" && HOME="${LH}" git config core.hooksPath /dev/null && HOME="${LH}" git config core.fsmonitor false && HOME="${LH}" git config core.untrackedCache false && HOME="${LH}" git config user.name "${NOME}" && HOME="${LH}" git config user.email "${EMAIL}" && { [ -z "${CHAVE}" ] || HOME="${LH}" git config user.signingkey "${CHAVE}"; } && echo CLONE-OK
```

A configuração efetiva, ANTES do checkout (se aparecer «fora da lista», pare e chame o CEO), e o checkout:

```bash
cd "${D:?}" && confere_config && HOME="${LH:?}" git checkout main && echo CHECKOUT-OK
```

(b) O HEAD é a âncora e a árvore está limpa.

```bash
cd "${D:?}" && [ "$(HOME="${LH:?}" git rev-parse HEAD)" = "${ANCORA:?}" ] && [ -z "$(HOME="${LH}" git status --porcelain)" ] && echo ANCORA-OK
```

(c) Só no W4: o insumo não rastreado, copiado do blob rastreado na âncora para o caminho que o SIGN lê. O destino
é ignorado (`.gitignore`: `staged/`), então a árvore continua limpa.

```bash
set -o noglob
cd "${D:?}" && mkdir -p .claude/plans/PLAN-158/staged/wave1 && [ ! -L .claude/plans/PLAN-158 ] && [ ! -L .claude/plans/PLAN-158/staged ] && [ ! -L .claude/plans/PLAN-158/staged/wave1 ] && HOME="${LH:?}" git cat-file blob HEAD:.claude/plans/PLAN-194/w4/insumos/rollback-oidc-to-token.patch > .claude/plans/PLAN-158/staged/wave1/rollback-oidc-to-token.patch && [ "$(shasum -a 256 < .claude/plans/PLAN-158/staged/wave1/rollback-oidc-to-token.patch | cut -d' ' -f1)" = e68a508c86ebe2ac6c2eac444530934e4aa91fe05186f98b6a490d391a845b6a ] && [ -z "$(HOME="${LH}" git status --porcelain)" ] && echo INSUMO-OK
set +o noglob
```

(d) Conferências antes do SIGN. O bloco imprime também o caminho e o sha256 do `gpg` que o seu `PATH` acha; o (f)
os confere de novo.

```bash
S=.claude/plans/PLAN-194/w4/OWNER-W4-SIGN.sh
cd "${D:?}" && [ "$(shasum -a 256 < "${S}" | cut -d' ' -f1)" = "${SIGN_SHA:?}" ] && [ "$(HOME="${LH:?}" git config --show-origin --get-all core.fsmonitor)" = "$(printf 'file:.git/config\tfalse')" ] && [ "$(HOME="${LH}" git config --show-origin --get-all core.hooksPath)" = "$(printf 'file:.git/config\t/dev/null')" ] && confere_config && [ -z "$(ls -A "${LH}")" ] && [ -z "$(env | grep -E '^(GIT_|CEO_|CLAUDE_PROJECT_DIR|BASH_ENV=|BASH_FUNC_|GNUPGHOME=|XDG_CONFIG_HOME=)')" ] && GPG_ABS="$(command -v gpg)" && GPG_SHA="$(shasum -a 256 < "${GPG_ABS}" | cut -d' ' -f1)" && [ "${#GPG_SHA}" = 64 ] && echo PRE-SIGN-OK && printf 'gpg: %s %s\n' "${GPG_ABS}" "${GPG_SHA}"
```

(e) O SIGN, a partir da raiz do clone: bateria, depois a senha do GPG, depois o commit no `main` deste clone. Ele
não faz push. O bloco encerra o gpg-agent antes e depois do SIGN.

**Atenção, W4: este SIGN imprime receitas de recuperação e comandos sugeridos** (por exemplo `git reset`,
`git apply -R`, `git checkout HEAD -- …`, `rm`, `git worktree remove`, «rode de novo»). **Não rode nenhum deles.**

```bash
gpgconf --homedir "${HOME}/.gnupg" --kill gpg-agent && cd "${D:?}" && env -i PATH="${PATH}" HOME="${LH:?}" GNUPGHOME="${HOME}/.gnupg" PYTHONUSERBASE="${PYUB:?}" USER="${USER}" LOGNAME="${LOGNAME}" SHELL="${SHELL}" TERM="${TERM}" LANG="${LANG}" PAGER=cat GPG_TTY="$(tty)" bash .claude/plans/PLAN-194/w4/OWNER-W4-SIGN.sh; echo "SIGN-RC=$?"; gpgconf --homedir "${HOME}/.gnupg" --kill gpg-agent
```

`SIGN-RC=0`: siga para (f). Qualquer outro: pare e chame o CEO, sem rodar nada que o SIGN sugerir.

(f) O land, apurado pela REF (nunca pelo texto do SIGN): `HEAD` é `refs/heads/main`, que é filho único da
âncora; a lista de caminhos com o status (`--name-status`) entre a âncora e ele é exatamente a das linhas de
cabeçalho do patch da âncora (`M` modificado, `A` criado, `D` removido), mais o sentinel (`M`) e a `.asc` (`A`); e
o `gpg` do seu `PATH` é o mesmo do (d), com o mesmo sha256.

```bash
P=.claude/plans/PLAN-194/w4/w4.patch
SE=.claude/plans/PLAN-194/w4-approved.md
cd "${D:?}" && SHA="$(HOME="${LH:?}" git rev-parse --verify "refs/heads/main^{commit}")" && [ "$(HOME="${LH}" git symbolic-ref HEAD)" = refs/heads/main ] && [ "$(HOME="${LH}" git rev-parse --verify "HEAD^{commit}")" = "${SHA}" ] && [ "$(HOME="${LH}" git rev-list --parents -n 1 "${SHA}")" = "${SHA} ${ANCORA:?}" ] && [ "$(HOME="${LH}" git diff-tree -r --no-renames --name-status "${ANCORA}" "${SHA}" | LC_ALL=C sort)" = "$( { HOME="${LH}" git cat-file blob "${ANCORA}:${P}" | awk '/^diff --git a\//{if (p != "") print s "\t" p; p = $3; sub(/^a\//, "", p); s = "M"} /^new file mode /{s = "A"} /^deleted file mode /{s = "D"} END {if (p != "") print s "\t" p}'; printf 'M\t%s\nA\t%s.asc\n' "${SE}" "${SE}"; } | LC_ALL=C sort)" ] && [ "$(command -v gpg)" = "${GPG_ABS:?}" ] && [ "$(shasum -a 256 < "${GPG_ABS}" | cut -d' ' -f1)" = "${GPG_SHA:?}" ] && echo LAND-OK && printf '%s\ngpg: %s %s\n' "${SHA}" "${GPG_ABS}" "${GPG_SHA}"
```

(f2) Mande ao CEO `W4: SIGN-RC=0, LAND-OK` e as duas linhas que o (f) imprimiu depois do `LAND-OK` (o SHA e a
linha `gpg:`). Espere a resposta do CEO: `PUSH-LIBERADO <sha>`. Sem ela, não há push.

(g) O push, só depois do `PUSH-LIBERADO`. Na primeira linha, troque o texto depois do `=` pelo SHA da resposta do
CEO. O bloco confere a configuração do clone de novo, que `refs/heads/main` ainda é o SHA do (f) e que o SHA colado
é esse; o push é desse SHA, sem force (um push sem force é recusado se não for avanço rápido) e roda com o seu HOME
(as suas credenciais).

```bash
SHA_LIBERADO=COLE-AQUI-O-SHA-DO-PUSH-LIBERADO
cd "${D:?}" && confere_config && [ "$(HOME="${LH:?}" git rev-parse --verify "refs/heads/main^{commit}")" = "${SHA:?}" ] && [ "${SHA_LIBERADO:?}" = "${SHA}" ] && git -c core.hooksPath=/dev/null -c core.fsmonitor=false push origin "${SHA}:refs/heads/main" && echo PUSH-OK
```

(h) O main do GitHub ficou nesse SHA (lido com o HOME novo).

```bash
cd "${D:?}" && [ "$(HOME="${LH:?}" git ls-remote origin refs/heads/main | cut -f1)" = "${SHA:?}" ] && echo PUBLICADO-OK && echo "${SHA}"
```

Mande ao CEO: `W4: PUBLICADO-OK <sha>`. Espere os valores do U2-A.

## 2. U2-A (pacote 2 de 4)

(a) Troque o texto depois do `=` nas linhas `COLE-AQUI-…` pelos valores que o CEO informou para o U2-A.

```bash
ANCORA=COLE-AQUI-O-SHA-DO-CEO
SIGN_SHA=COLE-AQUI-O-SHA256-DO-SIGN
CORE_SHA=COLE-AQUI-O-SHA256-DO-NUCLEO
DADOS_SHA=COLE-AQUI-O-SHA256-DOS-DADOS
SHA= SHA_LIBERADO= GPG_ABS= GPG_SHA=
D="${HOME}/lote-a-s363/u2a"
LH="${HOME}/lote-a-s363/home-u2a"
cd "${HOME}/lote-a-s363" && [ ! -e "${D:?}" ] && [ ! -e "${LH:?}" ] && mkdir "${LH}" && [ "$(HOME="${LH}" git ls-remote "${URL:?}" refs/heads/main | cut -f1)" = "${ANCORA:?}" ] && echo ORIGEM-OK
```

```bash
cd "${HOME}/lote-a-s363" && HOME="${LH:?}" git -c core.hooksPath=/dev/null -c core.fsmonitor=false clone --template= --no-checkout --single-branch --branch main "${URL:?}" "${D:?}" && cd "${D}" && HOME="${LH}" git config core.hooksPath /dev/null && HOME="${LH}" git config core.fsmonitor false && HOME="${LH}" git config core.untrackedCache false && HOME="${LH}" git config user.name "${NOME}" && HOME="${LH}" git config user.email "${EMAIL}" && { [ -z "${CHAVE}" ] || HOME="${LH}" git config user.signingkey "${CHAVE}"; } && echo CLONE-OK
```

```bash
cd "${D:?}" && confere_config && HOME="${LH:?}" git checkout main && echo CHECKOUT-OK
```

(b)

```bash
cd "${D:?}" && [ "$(HOME="${LH:?}" git rev-parse HEAD)" = "${ANCORA:?}" ] && [ -z "$(HOME="${LH}" git status --porcelain)" ] && echo ANCORA-OK
```

(c) Sem insumo.

(d) Conferências antes do SIGN: o sha256 da entrada do molde, do núcleo e dos dados do pacote são os informados
pelo CEO; o resto é como no W4.

```bash
S=.claude/plans/PLAN-194/sign-min/OWNER-SIGN.sh
N=.claude/plans/PLAN-194/sign-min/sign_min.py
DADOS=.claude/plans/PLAN-194/w2a/sign.tsv
cd "${D:?}" && [ "$(shasum -a 256 < "${S}" | cut -d' ' -f1)" = "${SIGN_SHA:?}" ] && [ "$(shasum -a 256 < "${N}" | cut -d' ' -f1)" = "${CORE_SHA:?}" ] && [ "$(shasum -a 256 < "${DADOS}" | cut -d' ' -f1)" = "${DADOS_SHA:?}" ] && [ "$(HOME="${LH:?}" git config --show-origin --get-all core.fsmonitor)" = "$(printf 'file:.git/config\tfalse')" ] && [ "$(HOME="${LH}" git config --show-origin --get-all core.hooksPath)" = "$(printf 'file:.git/config\t/dev/null')" ] && confere_config && [ -z "$(ls -A "${LH}")" ] && [ -z "$(env | grep -E '^(GIT_|CEO_|CLAUDE_PROJECT_DIR|BASH_ENV=|BASH_FUNC_|GNUPGHOME=|XDG_CONFIG_HOME=)')" ] && GPG_ABS="$(command -v gpg)" && GPG_SHA="$(shasum -a 256 < "${GPG_ABS}" | cut -d' ' -f1)" && [ "${#GPG_SHA}" = 64 ] && echo PRE-SIGN-OK && printf 'gpg: %s %s\n' "${GPG_ABS}" "${GPG_SHA}"
```

(e) O SIGN do molde, a partir da raiz do clone, com o sha256 do núcleo e os dados do pacote. Ele não faz push. O
bloco encerra o gpg-agent antes e depois do SIGN.

```bash
gpgconf --homedir "${HOME}/.gnupg" --kill gpg-agent && cd "${D:?}" && env -i PATH="${PATH}" HOME="${LH:?}" GNUPGHOME="${HOME}/.gnupg" PYTHONUSERBASE="${PYUB:?}" USER="${USER}" LOGNAME="${LOGNAME}" SHELL="${SHELL}" TERM="${TERM}" LANG="${LANG}" PAGER=cat GPG_TTY="$(tty)" bash .claude/plans/PLAN-194/sign-min/OWNER-SIGN.sh --nucleo-sha256="${CORE_SHA:?}" "${DADOS:?}"; echo "SIGN-RC=$?"; gpgconf --homedir "${HOME}/.gnupg" --kill gpg-agent
```

`SIGN-RC=0`: siga para (f). Qualquer outro: pare e chame o CEO, sem rodar nada que o SIGN sugerir.

(f)

```bash
P=.claude/plans/PLAN-194/w2a/w2a.patch
SE=.claude/plans/PLAN-194/w2a-approved.md
cd "${D:?}" && SHA="$(HOME="${LH:?}" git rev-parse --verify "refs/heads/main^{commit}")" && [ "$(HOME="${LH}" git symbolic-ref HEAD)" = refs/heads/main ] && [ "$(HOME="${LH}" git rev-parse --verify "HEAD^{commit}")" = "${SHA}" ] && [ "$(HOME="${LH}" git rev-list --parents -n 1 "${SHA}")" = "${SHA} ${ANCORA:?}" ] && [ "$(HOME="${LH}" git diff-tree -r --no-renames --name-status "${ANCORA}" "${SHA}" | LC_ALL=C sort)" = "$( { HOME="${LH}" git cat-file blob "${ANCORA}:${P}" | awk '/^diff --git a\//{if (p != "") print s "\t" p; p = $3; sub(/^a\//, "", p); s = "M"} /^new file mode /{s = "A"} /^deleted file mode /{s = "D"} END {if (p != "") print s "\t" p}'; printf 'M\t%s\nA\t%s.asc\n' "${SE}" "${SE}"; } | LC_ALL=C sort)" ] && [ "$(command -v gpg)" = "${GPG_ABS:?}" ] && [ "$(shasum -a 256 < "${GPG_ABS}" | cut -d' ' -f1)" = "${GPG_SHA:?}" ] && echo LAND-OK && printf '%s\ngpg: %s %s\n' "${SHA}" "${GPG_ABS}" "${GPG_SHA}"
```

(f2) Mande ao CEO `U2-A: SIGN-RC=0, LAND-OK` e as duas linhas que o (f) imprimiu depois do `LAND-OK` (o SHA e a
linha `gpg:`). Espere a resposta do CEO: `PUSH-LIBERADO <sha>`. Sem ela, não há push.

(g) Só depois do `PUSH-LIBERADO`, com o SHA da resposta do CEO na primeira linha.

```bash
SHA_LIBERADO=COLE-AQUI-O-SHA-DO-PUSH-LIBERADO
cd "${D:?}" && confere_config && [ "$(HOME="${LH:?}" git rev-parse --verify "refs/heads/main^{commit}")" = "${SHA:?}" ] && [ "${SHA_LIBERADO:?}" = "${SHA}" ] && git -c core.hooksPath=/dev/null -c core.fsmonitor=false push origin "${SHA}:refs/heads/main" && echo PUSH-OK
```

(h)

```bash
cd "${D:?}" && [ "$(HOME="${LH:?}" git ls-remote origin refs/heads/main | cut -f1)" = "${SHA:?}" ] && echo PUBLICADO-OK && echo "${SHA}"
```

Mande ao CEO: `U2-A: PUBLICADO-OK <sha>`. Espere os valores do U2-B.

## 3. U2-B (pacote 3 de 4)

(a) Troque o texto depois do `=` nas linhas `COLE-AQUI-…` pelos valores que o CEO informou para o U2-B.

```bash
ANCORA=COLE-AQUI-O-SHA-DO-CEO
SIGN_SHA=COLE-AQUI-O-SHA256-DO-SIGN
CORE_SHA=COLE-AQUI-O-SHA256-DO-NUCLEO
DADOS_SHA=COLE-AQUI-O-SHA256-DOS-DADOS
SHA= SHA_LIBERADO= GPG_ABS= GPG_SHA=
D="${HOME}/lote-a-s363/u2b"
LH="${HOME}/lote-a-s363/home-u2b"
cd "${HOME}/lote-a-s363" && [ ! -e "${D:?}" ] && [ ! -e "${LH:?}" ] && mkdir "${LH}" && [ "$(HOME="${LH}" git ls-remote "${URL:?}" refs/heads/main | cut -f1)" = "${ANCORA:?}" ] && echo ORIGEM-OK
```

```bash
cd "${HOME}/lote-a-s363" && HOME="${LH:?}" git -c core.hooksPath=/dev/null -c core.fsmonitor=false clone --template= --no-checkout --single-branch --branch main "${URL:?}" "${D:?}" && cd "${D}" && HOME="${LH}" git config core.hooksPath /dev/null && HOME="${LH}" git config core.fsmonitor false && HOME="${LH}" git config core.untrackedCache false && HOME="${LH}" git config user.name "${NOME}" && HOME="${LH}" git config user.email "${EMAIL}" && { [ -z "${CHAVE}" ] || HOME="${LH}" git config user.signingkey "${CHAVE}"; } && echo CLONE-OK
```

```bash
cd "${D:?}" && confere_config && HOME="${LH:?}" git checkout main && echo CHECKOUT-OK
```

(b)

```bash
cd "${D:?}" && [ "$(HOME="${LH:?}" git rev-parse HEAD)" = "${ANCORA:?}" ] && [ -z "$(HOME="${LH}" git status --porcelain)" ] && echo ANCORA-OK
```

(c) Sem insumo.

(d)

```bash
S=.claude/plans/PLAN-194/sign-min/OWNER-SIGN.sh
N=.claude/plans/PLAN-194/sign-min/sign_min.py
DADOS=.claude/plans/PLAN-194/w2b/sign.tsv
cd "${D:?}" && [ "$(shasum -a 256 < "${S}" | cut -d' ' -f1)" = "${SIGN_SHA:?}" ] && [ "$(shasum -a 256 < "${N}" | cut -d' ' -f1)" = "${CORE_SHA:?}" ] && [ "$(shasum -a 256 < "${DADOS}" | cut -d' ' -f1)" = "${DADOS_SHA:?}" ] && [ "$(HOME="${LH:?}" git config --show-origin --get-all core.fsmonitor)" = "$(printf 'file:.git/config\tfalse')" ] && [ "$(HOME="${LH}" git config --show-origin --get-all core.hooksPath)" = "$(printf 'file:.git/config\t/dev/null')" ] && confere_config && [ -z "$(ls -A "${LH}")" ] && [ -z "$(env | grep -E '^(GIT_|CEO_|CLAUDE_PROJECT_DIR|BASH_ENV=|BASH_FUNC_|GNUPGHOME=|XDG_CONFIG_HOME=)')" ] && GPG_ABS="$(command -v gpg)" && GPG_SHA="$(shasum -a 256 < "${GPG_ABS}" | cut -d' ' -f1)" && [ "${#GPG_SHA}" = 64 ] && echo PRE-SIGN-OK && printf 'gpg: %s %s\n' "${GPG_ABS}" "${GPG_SHA}"
```

(e)

```bash
gpgconf --homedir "${HOME}/.gnupg" --kill gpg-agent && cd "${D:?}" && env -i PATH="${PATH}" HOME="${LH:?}" GNUPGHOME="${HOME}/.gnupg" PYTHONUSERBASE="${PYUB:?}" USER="${USER}" LOGNAME="${LOGNAME}" SHELL="${SHELL}" TERM="${TERM}" LANG="${LANG}" PAGER=cat GPG_TTY="$(tty)" bash .claude/plans/PLAN-194/sign-min/OWNER-SIGN.sh --nucleo-sha256="${CORE_SHA:?}" "${DADOS:?}"; echo "SIGN-RC=$?"; gpgconf --homedir "${HOME}/.gnupg" --kill gpg-agent
```

`SIGN-RC=0`: siga para (f). Qualquer outro: pare e chame o CEO, sem rodar nada que o SIGN sugerir.

(f)

```bash
P=.claude/plans/PLAN-194/w2b/w2b.patch
SE=.claude/plans/PLAN-194/w2b-approved.md
cd "${D:?}" && SHA="$(HOME="${LH:?}" git rev-parse --verify "refs/heads/main^{commit}")" && [ "$(HOME="${LH}" git symbolic-ref HEAD)" = refs/heads/main ] && [ "$(HOME="${LH}" git rev-parse --verify "HEAD^{commit}")" = "${SHA}" ] && [ "$(HOME="${LH}" git rev-list --parents -n 1 "${SHA}")" = "${SHA} ${ANCORA:?}" ] && [ "$(HOME="${LH}" git diff-tree -r --no-renames --name-status "${ANCORA}" "${SHA}" | LC_ALL=C sort)" = "$( { HOME="${LH}" git cat-file blob "${ANCORA}:${P}" | awk '/^diff --git a\//{if (p != "") print s "\t" p; p = $3; sub(/^a\//, "", p); s = "M"} /^new file mode /{s = "A"} /^deleted file mode /{s = "D"} END {if (p != "") print s "\t" p}'; printf 'M\t%s\nA\t%s.asc\n' "${SE}" "${SE}"; } | LC_ALL=C sort)" ] && [ "$(command -v gpg)" = "${GPG_ABS:?}" ] && [ "$(shasum -a 256 < "${GPG_ABS}" | cut -d' ' -f1)" = "${GPG_SHA:?}" ] && echo LAND-OK && printf '%s\ngpg: %s %s\n' "${SHA}" "${GPG_ABS}" "${GPG_SHA}"
```

(f2) Mande ao CEO `U2-B: SIGN-RC=0, LAND-OK` e as duas linhas que o (f) imprimiu depois do `LAND-OK` (o SHA e a
linha `gpg:`). Espere a resposta do CEO: `PUSH-LIBERADO <sha>`. Sem ela, não há push.

(g) Só depois do `PUSH-LIBERADO`, com o SHA da resposta do CEO na primeira linha.

```bash
SHA_LIBERADO=COLE-AQUI-O-SHA-DO-PUSH-LIBERADO
cd "${D:?}" && confere_config && [ "$(HOME="${LH:?}" git rev-parse --verify "refs/heads/main^{commit}")" = "${SHA:?}" ] && [ "${SHA_LIBERADO:?}" = "${SHA}" ] && git -c core.hooksPath=/dev/null -c core.fsmonitor=false push origin "${SHA}:refs/heads/main" && echo PUSH-OK
```

(h)

```bash
cd "${D:?}" && [ "$(HOME="${LH:?}" git ls-remote origin refs/heads/main | cut -f1)" = "${SHA:?}" ] && echo PUBLICADO-OK && echo "${SHA}"
```

Mande ao CEO: `U2-B: PUBLICADO-OK <sha>`. Espere os valores da W5b.

## 4. W5b (pacote 4 de 4)

(a) Troque o texto depois do `=` nas linhas `COLE-AQUI-…` pelos valores que o CEO informou para o W5b.

```bash
ANCORA=COLE-AQUI-O-SHA-DO-CEO
SIGN_SHA=COLE-AQUI-O-SHA256-DO-SIGN
CORE_SHA=COLE-AQUI-O-SHA256-DO-NUCLEO
DADOS_SHA=COLE-AQUI-O-SHA256-DOS-DADOS
SHA= SHA_LIBERADO= GPG_ABS= GPG_SHA=
D="${HOME}/lote-a-s363/w5b"
LH="${HOME}/lote-a-s363/home-w5b"
cd "${HOME}/lote-a-s363" && [ ! -e "${D:?}" ] && [ ! -e "${LH:?}" ] && mkdir "${LH}" && [ "$(HOME="${LH}" git ls-remote "${URL:?}" refs/heads/main | cut -f1)" = "${ANCORA:?}" ] && echo ORIGEM-OK
```

```bash
cd "${HOME}/lote-a-s363" && HOME="${LH:?}" git -c core.hooksPath=/dev/null -c core.fsmonitor=false clone --template= --no-checkout --single-branch --branch main "${URL:?}" "${D:?}" && cd "${D}" && HOME="${LH}" git config core.hooksPath /dev/null && HOME="${LH}" git config core.fsmonitor false && HOME="${LH}" git config core.untrackedCache false && HOME="${LH}" git config user.name "${NOME}" && HOME="${LH}" git config user.email "${EMAIL}" && { [ -z "${CHAVE}" ] || HOME="${LH}" git config user.signingkey "${CHAVE}"; } && echo CLONE-OK
```

```bash
cd "${D:?}" && confere_config && HOME="${LH:?}" git checkout main && echo CHECKOUT-OK
```

(b)

```bash
cd "${D:?}" && [ "$(HOME="${LH:?}" git rev-parse HEAD)" = "${ANCORA:?}" ] && [ -z "$(HOME="${LH}" git status --porcelain)" ] && echo ANCORA-OK
```

(c) Sem insumo.

(d)

```bash
S=.claude/plans/PLAN-194/sign-min/OWNER-SIGN.sh
N=.claude/plans/PLAN-194/sign-min/sign_min.py
DADOS=.claude/plans/PLAN-194/w5b/sign.tsv
cd "${D:?}" && [ "$(shasum -a 256 < "${S}" | cut -d' ' -f1)" = "${SIGN_SHA:?}" ] && [ "$(shasum -a 256 < "${N}" | cut -d' ' -f1)" = "${CORE_SHA:?}" ] && [ "$(shasum -a 256 < "${DADOS}" | cut -d' ' -f1)" = "${DADOS_SHA:?}" ] && [ "$(HOME="${LH:?}" git config --show-origin --get-all core.fsmonitor)" = "$(printf 'file:.git/config\tfalse')" ] && [ "$(HOME="${LH}" git config --show-origin --get-all core.hooksPath)" = "$(printf 'file:.git/config\t/dev/null')" ] && confere_config && [ -z "$(ls -A "${LH}")" ] && [ -z "$(env | grep -E '^(GIT_|CEO_|CLAUDE_PROJECT_DIR|BASH_ENV=|BASH_FUNC_|GNUPGHOME=|XDG_CONFIG_HOME=)')" ] && GPG_ABS="$(command -v gpg)" && GPG_SHA="$(shasum -a 256 < "${GPG_ABS}" | cut -d' ' -f1)" && [ "${#GPG_SHA}" = 64 ] && echo PRE-SIGN-OK && printf 'gpg: %s %s\n' "${GPG_ABS}" "${GPG_SHA}"
```

(e)

```bash
gpgconf --homedir "${HOME}/.gnupg" --kill gpg-agent && cd "${D:?}" && env -i PATH="${PATH}" HOME="${LH:?}" GNUPGHOME="${HOME}/.gnupg" PYTHONUSERBASE="${PYUB:?}" USER="${USER}" LOGNAME="${LOGNAME}" SHELL="${SHELL}" TERM="${TERM}" LANG="${LANG}" PAGER=cat GPG_TTY="$(tty)" bash .claude/plans/PLAN-194/sign-min/OWNER-SIGN.sh --nucleo-sha256="${CORE_SHA:?}" "${DADOS:?}"; echo "SIGN-RC=$?"; gpgconf --homedir "${HOME}/.gnupg" --kill gpg-agent
```

`SIGN-RC=0`: siga para (f). Qualquer outro: pare e chame o CEO, sem rodar nada que o SIGN sugerir.

(f)

```bash
P=.claude/plans/PLAN-194/w5b/w5b.patch
SE=.claude/plans/PLAN-194/w5b-approved.md
cd "${D:?}" && SHA="$(HOME="${LH:?}" git rev-parse --verify "refs/heads/main^{commit}")" && [ "$(HOME="${LH}" git symbolic-ref HEAD)" = refs/heads/main ] && [ "$(HOME="${LH}" git rev-parse --verify "HEAD^{commit}")" = "${SHA}" ] && [ "$(HOME="${LH}" git rev-list --parents -n 1 "${SHA}")" = "${SHA} ${ANCORA:?}" ] && [ "$(HOME="${LH}" git diff-tree -r --no-renames --name-status "${ANCORA}" "${SHA}" | LC_ALL=C sort)" = "$( { HOME="${LH}" git cat-file blob "${ANCORA}:${P}" | awk '/^diff --git a\//{if (p != "") print s "\t" p; p = $3; sub(/^a\//, "", p); s = "M"} /^new file mode /{s = "A"} /^deleted file mode /{s = "D"} END {if (p != "") print s "\t" p}'; printf 'M\t%s\nA\t%s.asc\n' "${SE}" "${SE}"; } | LC_ALL=C sort)" ] && [ "$(command -v gpg)" = "${GPG_ABS:?}" ] && [ "$(shasum -a 256 < "${GPG_ABS}" | cut -d' ' -f1)" = "${GPG_SHA:?}" ] && echo LAND-OK && printf '%s\ngpg: %s %s\n' "${SHA}" "${GPG_ABS}" "${GPG_SHA}"
```

(f2) Mande ao CEO `W5b: SIGN-RC=0, LAND-OK` e as duas linhas que o (f) imprimiu depois do `LAND-OK` (o SHA e a
linha `gpg:`). Espere a resposta do CEO: `PUSH-LIBERADO <sha>`. Sem ela, não há push.

(g) Só depois do `PUSH-LIBERADO`, com o SHA da resposta do CEO na primeira linha.

```bash
SHA_LIBERADO=COLE-AQUI-O-SHA-DO-PUSH-LIBERADO
cd "${D:?}" && confere_config && [ "$(HOME="${LH:?}" git rev-parse --verify "refs/heads/main^{commit}")" = "${SHA:?}" ] && [ "${SHA_LIBERADO:?}" = "${SHA}" ] && git -c core.hooksPath=/dev/null -c core.fsmonitor=false push origin "${SHA}:refs/heads/main" && echo PUSH-OK
```

(h)

```bash
cd "${D:?}" && [ "$(HOME="${LH:?}" git ls-remote origin refs/heads/main | cut -f1)" = "${SHA:?}" ] && echo PUBLICADO-OK && echo "${SHA}"
```

Mande ao CEO: `W5b: PUBLICADO-OK <sha>`. O Lote A termina quando o CEO confirmar este último commit.

## 5. Depois do Lote A

Só depois que o CEO confirmar a W5b. É o primeiro git no seu checkout principal desde o início do roteiro:

```bash
cd "${HOME}/canhada-labs/ceo-orchestration" && git pull --ff-only && echo PULL-OK
```

Os clones e os HOMEs novos em `${HOME}/lote-a-s363` e os diretórios de logs dos SIGNs sob `/tmp` ficam até o CEO
dizer que podem ser apagados.
