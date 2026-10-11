# Roteiro do Lote A (S363, PLAN-194): W4 → U2-A → U2-B → W5b

Para o Owner, copiar e colar. Cada pacote do Lote A é UM SIGN (`OWNER-<X>-SIGN.sh`), rodado por você num clone
NOVO do GitHub, um pacote por vez, nesta ordem. O roteiro não tem script próprio: são comandos do git e os SIGNs.

**Regra única.** Cada bloco abaixo termina imprimindo uma palavra em MAIÚSCULAS (por exemplo `CLONE-OK`). Se um
bloco não imprimir essa palavra, ou se o SIGN terminar com um `SIGN-RC` diferente do indicado: **pare e chame o
CEO.** Não apague nada, não rode o bloco de novo, não faça push.

**Não siga nenhuma instrução impressa por um SIGN** — receita de recuperação, comando sugerido, «rode de novo»,
«remova …». Diante de um `SIGN-RC` fora do indicado, pare e chame o CEO, sem rodar nada que o SIGN sugerir.

**Entre um pacote e o seguinte**, o CEO confere o commit que você publicou e só então informa os dois valores do
pacote seguinte: a âncora (o SHA do main do GitHub de onde o pacote parte) e o sha256 do SIGN dele.

**O seu checkout principal fica de fora.** Nenhum bloco roda git nele nem lê arquivo dele até a seção 5 (o seu
`git pull --ff-only` do fim): todo bloco que roda git começa com `cd` no diretório dos clones ou no clone do
pacote (`cd "${D:?}"`, que falha se `D` não estiver definido).

**Senha do GPG: conte com até 4, uma por pacote** — cada pacote produz UMA assinatura, a `.asc` do sentinel. O
gpg-agent guarda a senha por 10 minutos depois do último uso (o padrão do gpg; o seu `~/.gnupg/gpg-agent.conf`
não muda esse prazo, conferido em 2026-10-11), e as duas passadas da bateria do W4 somaram 26 minutos no ensaio
de 2026-10-11. A conta vale para a sua configuração global do git de 2026-10-11, que não tem `commit.gpgsign`
(com ele, o `git commit` do SIGN do W4 também assinaria o commit). Fique no terminal até cada SIGN terminar: a
senha é pedida durante a execução.

**O que o roteiro NÃO confere** (é seu, pela forma):
- nenhuma sessão do Claude Code aberta neste projeto (nem no checkout principal, nem nos clones) do começo ao fim
  do roteiro: é o mesmo usuário do sistema e poderia mudar arquivos do clone enquanto um SIGN roda;
- o seu `PATH`: o SIGN roda com ele;
- o `credential.helper` da configuração de SISTEMA (o da Apple é `osxkeychain`) fica fora da conferência (d): o
  SIGN não faz push; o push (g) roda no seu terminal, com as suas credenciais;
- o `~/.config/git/ignore`: o roteiro só olha o status completo em (b) e (c), num clone novo.

## 0. Uma vez, antes do W4

Feche todas as sessões do Claude Code deste projeto. Num terminal NOVO (Terminal.app), fora do Claude Code. O
primeiro bloco não pode imprimir nenhuma variável:

```bash
env | grep -E '^(GIT_|CEO_|CLAUDE_PROJECT_DIR|BASH_ENV=|BASH_FUNC_|GNUPGHOME=|XDG_CONFIG_HOME=)' || echo AMBIENTE-OK
```

```bash
case "${TMPDIR:-/tmp}" in /*) case "${TMPDIR:-/tmp}/" in "$HOME/canhada-labs/ceo-orchestration/"*|"$HOME/lote-a-s363/"*) ;; *) echo TMPDIR-OK ;; esac ;; esac
```

```bash
[ "$(df -Pk "$HOME" /tmp | awk 'NR > 1 && $4 >= 30 * 1024 * 1024 {n++} END {print n + 0}')" = 2 ] && echo DISCO-OK
```

```bash
URL=https://github.com/Canhada-Labs/ceo-orchestration.git
mkdir -p "$HOME/lote-a-s363" && echo PREPARO-OK
```

A configuração GLOBAL do git (os dois arquivos que ela pode ter) sem chave que executa programa ou muda bytes:

```bash
cd "$HOME/lote-a-s363" && M="$( { for f in "$HOME/.gitconfig" "$HOME/.config/git/config"; do [ ! -e "$f" ] || git config --file "$f" --list || echo "ilegível: $f"; done; } | grep -Ei 'ilegível|fsmonitor|hookspath|filter\.|\.vcs=|include|credential|gpg\.program|pager|external|sshcommand|attributesfile|askpass|gitproxy|insteadof' || :)" && [ -z "$M" ] && echo CONFIG-GLOBAL-OK
[ -z "$M" ] || printf '%s\n' "$M"
```

O piso de disco da casa é 30 GB livres (no volume do `$HOME` e no do `/tmp`: o SIGN roda sem `TMPDIR`, e o
padrão do sistema para temporários, então, é `/tmp`). O `TMPDIR-OK` confere o `TMPDIR` do seu terminal pelo texto do caminho:
absoluto e fora do checkout principal e dos clones. Cada clone ocupa cerca de 240 MB (medido em 2026-10-11:
235 MB).

## Pré-condições: o roteiro garante, sem depender das conferências dos SIGNs

| pré-condição | onde |
|---|---|
| ambiente sem `GIT_*`, `CEO_*`, `CLAUDE_PROJECT_DIR*`, `BASH_ENV`, `BASH_FUNC_*`, `GNUPGHOME`, `XDG_CONFIG_HOME` | seção 0 e (d); o SIGN roda com `env -i` (e) |
| `TMPDIR` absoluto e fora do checkout principal e dos clones | seção 0; o SIGN não recebe `TMPDIR` |
| 30 GB livres no volume do `$HOME` e no do `/tmp` | seção 0 |
| configuração global sem chave que executa programa ou muda bytes | seção 0 (`CONFIG-GLOBAL-OK`); a configuração não-local efetiva (global, XDG e sistema), menos o `credential.helper`, de novo em (d) |
| nenhum `~/.config/git/attributes` | (d) |
| main do GitHub = âncora antes do clone; clone NOVO; HEAD = âncora; árvore limpa | (a), (b) |
| identidade dos commits (`user.name` e `user.email` efetivos, lidos no clone) | (b) |
| hooks, fsmonitor e cache de não rastreados desligados na configuração local do clone; `core.fsmonitor` e `core.hooksPath` com UM valor só, do `.git/config` do clone | (a), (d) |
| sha256 do SIGN = o informado pelo CEO | (d) |
| insumo do W4: o blob rastreado copiado para o caminho que o SIGN lê, com sha256 conferido | (c) |
| land apurado pela ref; push do SHA conferido; main do GitHub = esse SHA | (f), (g), (h) |
| nenhuma sessão do Claude Code; o `PATH`; o `credential.helper` do sistema; o `~/.config/git/ignore` | declarado, não conferido |

Por que: um SIGN pode rodar git que dispara hooks (`git commit`, `git fetch`, `git worktree add`) e pode calcular
blobs aplicando atributos; o roteiro desliga hooks e fsmonitor no clone e exige que não haja atributos globais, sem
depender de o SIGN conferir isso. O que cada SIGN confere a mais é dele. O SIGN do W4 (`14532746`, que não será
reaberto) commita com `git commit`, não confere hooks nem fsmonitor, remove worktrees de uma execução interrompida
em vez de recusar e imprime receitas de recuperação. O patch do U2-B parte da pós-imagem do U2-A: por isso a ordem.

**Por que o SIGN roda com `env -i`** (passo e): o ambiente do SIGN passa a ser uma lista FIXA — `PATH`, `HOME`,
`USER`, `LOGNAME`, `SHELL`, `TERM`, `LANG`, `PAGER=cat` e `GPG_TTY` (o pinentry precisa dele). Tudo o mais sai
por construção: `GIT_*`, `BASH_ENV`, `BASH_FUNC_*`, `PYTHON*`, `DYLD_*`, `CEO_*`, `CLAUDE_*` e o `TMPDIR`.

## 1. W4 (pacote 1 de 4)

(a) Confira a âncora no GitHub e faça o clone novo. Nas duas primeiras linhas, troque o texto depois do `=` pelos
valores que o CEO informou (em todos os pacotes).

```bash
ANCORA=COLE-AQUI-O-SHA-DO-CEO
SIGN_SHA=COLE-AQUI-O-SHA256-DO-SIGN
D="$HOME/lote-a-s363/w4"
cd "$HOME/lote-a-s363" && [ ! -e "${D:?}" ] && [ "$(git ls-remote "${URL:?}" refs/heads/main | cut -f1)" = "$ANCORA" ] && echo ORIGEM-OK
```

```bash
cd "$HOME/lote-a-s363" && git -c core.hooksPath=/dev/null -c core.fsmonitor=false clone --template= --no-checkout --single-branch --branch main "${URL:?}" "${D:?}" && cd "$D" && git config core.hooksPath /dev/null && git config core.fsmonitor false && git config core.untrackedCache false && git checkout main && echo CLONE-OK
```

(b) O HEAD é a âncora, a árvore está limpa e a identidade dos commits existe (depois de `ANCORA-OK`, duas linhas
mostram de qual arquivo ela vem).

```bash
cd "${D:?}" && [ "$(git rev-parse HEAD)" = "$ANCORA" ] && [ -z "$(git status --porcelain)" ] && [ -n "$(git config --get user.name)" ] && [ -n "$(git config --get user.email)" ] && echo ANCORA-OK && git config --show-origin --get-all user.name && git config --show-origin --get-all user.email
```

(c) Só no W4: o insumo não rastreado, copiado do blob rastreado na âncora para o caminho que o SIGN lê. O destino
é ignorado (`.gitignore`: `staged/`), então a árvore continua limpa. O P0 do SIGN confere de novo tamanho,
sha256 e se ele aplica no HEAD.

```bash
set -o noglob
cd "${D:?}" && mkdir -p .claude/plans/PLAN-158/staged/wave1 && [ ! -L .claude/plans/PLAN-158 ] && [ ! -L .claude/plans/PLAN-158/staged ] && [ ! -L .claude/plans/PLAN-158/staged/wave1 ] && git cat-file blob HEAD:.claude/plans/PLAN-194/w4/insumos/rollback-oidc-to-token.patch > .claude/plans/PLAN-158/staged/wave1/rollback-oidc-to-token.patch && [ "$(shasum -a 256 < .claude/plans/PLAN-158/staged/wave1/rollback-oidc-to-token.patch | cut -d' ' -f1)" = e68a508c86ebe2ac6c2eac444530934e4aa91fe05186f98b6a490d391a845b6a ] && [ -z "$(git status --porcelain)" ] && echo INSUMO-OK
set +o noglob
```

(d) Conferências antes do SIGN.

```bash
S=.claude/plans/PLAN-194/w4/OWNER-W4-SIGN.sh
cd "${D:?}" && [ "$(shasum -a 256 < "$S" | cut -d' ' -f1)" = "$SIGN_SHA" ] && [ "$(git config --show-origin --get-all core.fsmonitor)" = "$(printf 'file:.git/config\tfalse')" ] && [ "$(git config --show-origin --get-all core.hooksPath)" = "$(printf 'file:.git/config\t/dev/null')" ] && [ -z "$(git config --list --show-origin | awk -F'\t' '$1 != "file:.git/config"' | grep -Ei 'fsmonitor|hookspath|filter\.|\.vcs=|include|gpg\.program|pager|external|sshcommand|attributesfile|askpass|gitproxy|insteadof')" ] && [ ! -e "$HOME/.config/git/attributes" ] && [ -z "$(env | grep -E '^(GIT_|CEO_|CLAUDE_PROJECT_DIR|BASH_ENV=|BASH_FUNC_|GNUPGHOME=|XDG_CONFIG_HOME=)')" ] && echo PRE-SIGN-OK
```

(e) O SIGN, a partir da raiz do clone: bateria, depois a senha do GPG, depois o commit no `main` deste clone. Ele
não faz push.

**Atenção, W4: este SIGN ainda imprime receitas de recuperação e comandos sugeridos** (por exemplo `git reset`,
`git apply -R`, `git checkout HEAD -- …`, `rm`, `git worktree remove`, «rode de novo»). **Não rode nenhum deles.**

```bash
cd "${D:?}" && env -i PATH="$PATH" HOME="$HOME" USER="$USER" LOGNAME="$LOGNAME" SHELL="$SHELL" TERM="$TERM" LANG="$LANG" PAGER=cat GPG_TTY="$(tty)" bash .claude/plans/PLAN-194/w4/OWNER-W4-SIGN.sh; echo "SIGN-RC=$?"
```

`SIGN-RC=0`: siga para (f). Qualquer outro: pare e chame o CEO, sem rodar nada que o SIGN sugerir.

(f) O land, apurado pela REF (nunca pelo texto): o main do clone é filho único da âncora e toca exatamente o
patch, o sentinel e a `.asc`.

```bash
P=.claude/plans/PLAN-194/w4/w4.patch
SE=.claude/plans/PLAN-194/w4-approved.md
cd "${D:?}" && [ "$(git rev-list --parents -n 1 refs/heads/main)" = "$(git rev-parse refs/heads/main) $ANCORA" ] && [ "$(git diff-tree -r --no-renames --name-only "$ANCORA" refs/heads/main | LC_ALL=C sort)" = "$( { git show "$ANCORA:$P" | awk '/^diff --git a\//{p=$3; sub(/^a\//, "", p); print p}'; printf '%s\n%s\n' "$SE" "$SE.asc"; } | LC_ALL=C sort)" ] && echo LAND-OK
```

(g) Push do SHA conferido, sem force (um push sem force é recusado se não for avanço rápido).

```bash
cd "${D:?}" && SHA=$(git rev-parse refs/heads/main) && git -c core.hooksPath=/dev/null -c core.fsmonitor=false push origin "$SHA:refs/heads/main" && echo PUSH-OK
```

(h) O main do GitHub ficou nesse SHA.

```bash
cd "${D:?}" && [ "$(git ls-remote origin refs/heads/main | cut -f1)" = "$SHA" ] && echo PUBLICADO-OK && echo "$SHA"
```

Mande ao CEO: `W4: SIGN-RC=<n>, PUBLICADO-OK <sha>`. Espere os valores do U2-A.

## 2. U2-A (pacote 2 de 4)

(a)

```bash
ANCORA=COLE-AQUI-O-SHA-DO-CEO
SIGN_SHA=COLE-AQUI-O-SHA256-DO-SIGN
D="$HOME/lote-a-s363/u2a"
cd "$HOME/lote-a-s363" && [ ! -e "${D:?}" ] && [ "$(git ls-remote "${URL:?}" refs/heads/main | cut -f1)" = "$ANCORA" ] && echo ORIGEM-OK
```

```bash
cd "$HOME/lote-a-s363" && git -c core.hooksPath=/dev/null -c core.fsmonitor=false clone --template= --no-checkout --single-branch --branch main "${URL:?}" "${D:?}" && cd "$D" && git config core.hooksPath /dev/null && git config core.fsmonitor false && git config core.untrackedCache false && git checkout main && echo CLONE-OK
```

(b)

```bash
cd "${D:?}" && [ "$(git rev-parse HEAD)" = "$ANCORA" ] && [ -z "$(git status --porcelain)" ] && [ -n "$(git config --get user.name)" ] && [ -n "$(git config --get user.email)" ] && echo ANCORA-OK && git config --show-origin --get-all user.name && git config --show-origin --get-all user.email
```

(c) Sem insumo.

(d)

```bash
S=.claude/plans/PLAN-194/w2a/OWNER-W2A-SIGN.sh
cd "${D:?}" && [ "$(shasum -a 256 < "$S" | cut -d' ' -f1)" = "$SIGN_SHA" ] && [ "$(git config --show-origin --get-all core.fsmonitor)" = "$(printf 'file:.git/config\tfalse')" ] && [ "$(git config --show-origin --get-all core.hooksPath)" = "$(printf 'file:.git/config\t/dev/null')" ] && [ -z "$(git config --list --show-origin | awk -F'\t' '$1 != "file:.git/config"' | grep -Ei 'fsmonitor|hookspath|filter\.|\.vcs=|include|gpg\.program|pager|external|sshcommand|attributesfile|askpass|gitproxy|insteadof')" ] && [ ! -e "$HOME/.config/git/attributes" ] && [ -z "$(env | grep -E '^(GIT_|CEO_|CLAUDE_PROJECT_DIR|BASH_ENV=|BASH_FUNC_|GNUPGHOME=|XDG_CONFIG_HOME=)')" ] && echo PRE-SIGN-OK
```

(e)

```bash
cd "${D:?}" && env -i PATH="$PATH" HOME="$HOME" USER="$USER" LOGNAME="$LOGNAME" SHELL="$SHELL" TERM="$TERM" LANG="$LANG" PAGER=cat GPG_TTY="$(tty)" bash .claude/plans/PLAN-194/w2a/OWNER-W2A-SIGN.sh; echo "SIGN-RC=$?"
```

`SIGN-RC=0`: siga para (f). `SIGN-RC=3`: pela especificação comum dos SIGNs, o SIGN publicou o commit no `main`
deste clone e não sincronizou o índice e a árvore. Siga para (f) também (a conferência e o push leem a ref, não o
índice; não mexa no índice) e diga ao CEO que foi 3. Qualquer outro: pare e chame o CEO, sem rodar nada que o
SIGN sugerir.

(f)

```bash
P=.claude/plans/PLAN-194/w2a/w2a.patch
SE=.claude/plans/PLAN-194/w2a-approved.md
cd "${D:?}" && [ "$(git rev-list --parents -n 1 refs/heads/main)" = "$(git rev-parse refs/heads/main) $ANCORA" ] && [ "$(git diff-tree -r --no-renames --name-only "$ANCORA" refs/heads/main | LC_ALL=C sort)" = "$( { git show "$ANCORA:$P" | awk '/^diff --git a\//{p=$3; sub(/^a\//, "", p); print p}'; printf '%s\n%s\n' "$SE" "$SE.asc"; } | LC_ALL=C sort)" ] && echo LAND-OK
```

(g)

```bash
cd "${D:?}" && SHA=$(git rev-parse refs/heads/main) && git -c core.hooksPath=/dev/null -c core.fsmonitor=false push origin "$SHA:refs/heads/main" && echo PUSH-OK
```

(h)

```bash
cd "${D:?}" && [ "$(git ls-remote origin refs/heads/main | cut -f1)" = "$SHA" ] && echo PUBLICADO-OK && echo "$SHA"
```

Mande ao CEO: `U2-A: SIGN-RC=<n>, PUBLICADO-OK <sha>`. Espere os valores do U2-B.

## 3. U2-B (pacote 3 de 4)

(a)

```bash
ANCORA=COLE-AQUI-O-SHA-DO-CEO
SIGN_SHA=COLE-AQUI-O-SHA256-DO-SIGN
D="$HOME/lote-a-s363/u2b"
cd "$HOME/lote-a-s363" && [ ! -e "${D:?}" ] && [ "$(git ls-remote "${URL:?}" refs/heads/main | cut -f1)" = "$ANCORA" ] && echo ORIGEM-OK
```

```bash
cd "$HOME/lote-a-s363" && git -c core.hooksPath=/dev/null -c core.fsmonitor=false clone --template= --no-checkout --single-branch --branch main "${URL:?}" "${D:?}" && cd "$D" && git config core.hooksPath /dev/null && git config core.fsmonitor false && git config core.untrackedCache false && git checkout main && echo CLONE-OK
```

(b)

```bash
cd "${D:?}" && [ "$(git rev-parse HEAD)" = "$ANCORA" ] && [ -z "$(git status --porcelain)" ] && [ -n "$(git config --get user.name)" ] && [ -n "$(git config --get user.email)" ] && echo ANCORA-OK && git config --show-origin --get-all user.name && git config --show-origin --get-all user.email
```

(c) Sem insumo.

(d)

```bash
S=.claude/plans/PLAN-194/w2b/OWNER-W2B-SIGN.sh
cd "${D:?}" && [ "$(shasum -a 256 < "$S" | cut -d' ' -f1)" = "$SIGN_SHA" ] && [ "$(git config --show-origin --get-all core.fsmonitor)" = "$(printf 'file:.git/config\tfalse')" ] && [ "$(git config --show-origin --get-all core.hooksPath)" = "$(printf 'file:.git/config\t/dev/null')" ] && [ -z "$(git config --list --show-origin | awk -F'\t' '$1 != "file:.git/config"' | grep -Ei 'fsmonitor|hookspath|filter\.|\.vcs=|include|gpg\.program|pager|external|sshcommand|attributesfile|askpass|gitproxy|insteadof')" ] && [ ! -e "$HOME/.config/git/attributes" ] && [ -z "$(env | grep -E '^(GIT_|CEO_|CLAUDE_PROJECT_DIR|BASH_ENV=|BASH_FUNC_|GNUPGHOME=|XDG_CONFIG_HOME=)')" ] && echo PRE-SIGN-OK
```

(e)

```bash
cd "${D:?}" && env -i PATH="$PATH" HOME="$HOME" USER="$USER" LOGNAME="$LOGNAME" SHELL="$SHELL" TERM="$TERM" LANG="$LANG" PAGER=cat GPG_TTY="$(tty)" bash .claude/plans/PLAN-194/w2b/OWNER-W2B-SIGN.sh; echo "SIGN-RC=$?"
```

`SIGN-RC=0` ou `SIGN-RC=3` (como no U2-A): siga para (f) e diga ao CEO qual foi. Qualquer outro: pare e chame o
CEO, sem rodar nada que o SIGN sugerir.

(f)

```bash
P=.claude/plans/PLAN-194/w2b/w2b.patch
SE=.claude/plans/PLAN-194/w2b-approved.md
cd "${D:?}" && [ "$(git rev-list --parents -n 1 refs/heads/main)" = "$(git rev-parse refs/heads/main) $ANCORA" ] && [ "$(git diff-tree -r --no-renames --name-only "$ANCORA" refs/heads/main | LC_ALL=C sort)" = "$( { git show "$ANCORA:$P" | awk '/^diff --git a\//{p=$3; sub(/^a\//, "", p); print p}'; printf '%s\n%s\n' "$SE" "$SE.asc"; } | LC_ALL=C sort)" ] && echo LAND-OK
```

(g)

```bash
cd "${D:?}" && SHA=$(git rev-parse refs/heads/main) && git -c core.hooksPath=/dev/null -c core.fsmonitor=false push origin "$SHA:refs/heads/main" && echo PUSH-OK
```

(h)

```bash
cd "${D:?}" && [ "$(git ls-remote origin refs/heads/main | cut -f1)" = "$SHA" ] && echo PUBLICADO-OK && echo "$SHA"
```

Mande ao CEO: `U2-B: SIGN-RC=<n>, PUBLICADO-OK <sha>`. Espere os valores da W5b.

## 4. W5b (pacote 4 de 4)

(a)

```bash
ANCORA=COLE-AQUI-O-SHA-DO-CEO
SIGN_SHA=COLE-AQUI-O-SHA256-DO-SIGN
D="$HOME/lote-a-s363/w5b"
cd "$HOME/lote-a-s363" && [ ! -e "${D:?}" ] && [ "$(git ls-remote "${URL:?}" refs/heads/main | cut -f1)" = "$ANCORA" ] && echo ORIGEM-OK
```

```bash
cd "$HOME/lote-a-s363" && git -c core.hooksPath=/dev/null -c core.fsmonitor=false clone --template= --no-checkout --single-branch --branch main "${URL:?}" "${D:?}" && cd "$D" && git config core.hooksPath /dev/null && git config core.fsmonitor false && git config core.untrackedCache false && git checkout main && echo CLONE-OK
```

(b)

```bash
cd "${D:?}" && [ "$(git rev-parse HEAD)" = "$ANCORA" ] && [ -z "$(git status --porcelain)" ] && [ -n "$(git config --get user.name)" ] && [ -n "$(git config --get user.email)" ] && echo ANCORA-OK && git config --show-origin --get-all user.name && git config --show-origin --get-all user.email
```

(c) Sem insumo.

(d)

```bash
S=.claude/plans/PLAN-194/w5b/OWNER-W5B-SIGN.sh
cd "${D:?}" && [ "$(shasum -a 256 < "$S" | cut -d' ' -f1)" = "$SIGN_SHA" ] && [ "$(git config --show-origin --get-all core.fsmonitor)" = "$(printf 'file:.git/config\tfalse')" ] && [ "$(git config --show-origin --get-all core.hooksPath)" = "$(printf 'file:.git/config\t/dev/null')" ] && [ -z "$(git config --list --show-origin | awk -F'\t' '$1 != "file:.git/config"' | grep -Ei 'fsmonitor|hookspath|filter\.|\.vcs=|include|gpg\.program|pager|external|sshcommand|attributesfile|askpass|gitproxy|insteadof')" ] && [ ! -e "$HOME/.config/git/attributes" ] && [ -z "$(env | grep -E '^(GIT_|CEO_|CLAUDE_PROJECT_DIR|BASH_ENV=|BASH_FUNC_|GNUPGHOME=|XDG_CONFIG_HOME=)')" ] && echo PRE-SIGN-OK
```

(e)

```bash
cd "${D:?}" && env -i PATH="$PATH" HOME="$HOME" USER="$USER" LOGNAME="$LOGNAME" SHELL="$SHELL" TERM="$TERM" LANG="$LANG" PAGER=cat GPG_TTY="$(tty)" bash .claude/plans/PLAN-194/w5b/OWNER-W5B-SIGN.sh; echo "SIGN-RC=$?"
```

`SIGN-RC=0` ou `SIGN-RC=3` (como no U2-A): siga para (f) e diga ao CEO qual foi. Qualquer outro: pare e chame o
CEO, sem rodar nada que o SIGN sugerir.

(f)

```bash
P=.claude/plans/PLAN-194/w5b/w5b.patch
SE=.claude/plans/PLAN-194/w5b-approved.md
cd "${D:?}" && [ "$(git rev-list --parents -n 1 refs/heads/main)" = "$(git rev-parse refs/heads/main) $ANCORA" ] && [ "$(git diff-tree -r --no-renames --name-only "$ANCORA" refs/heads/main | LC_ALL=C sort)" = "$( { git show "$ANCORA:$P" | awk '/^diff --git a\//{p=$3; sub(/^a\//, "", p); print p}'; printf '%s\n%s\n' "$SE" "$SE.asc"; } | LC_ALL=C sort)" ] && echo LAND-OK
```

(g)

```bash
cd "${D:?}" && SHA=$(git rev-parse refs/heads/main) && git -c core.hooksPath=/dev/null -c core.fsmonitor=false push origin "$SHA:refs/heads/main" && echo PUSH-OK
```

(h)

```bash
cd "${D:?}" && [ "$(git ls-remote origin refs/heads/main | cut -f1)" = "$SHA" ] && echo PUBLICADO-OK && echo "$SHA"
```

Mande ao CEO: `W5b: SIGN-RC=<n>, PUBLICADO-OK <sha>`. O Lote A termina quando o CEO confirmar este último commit.

## 5. Depois do Lote A

Só depois que o CEO confirmar a W5b. É o primeiro git no seu checkout principal desde o início do roteiro:

```bash
cd "$HOME/canhada-labs/ceo-orchestration" && git pull --ff-only && echo PULL-OK
```

Os clones em `$HOME/lote-a-s363` ficam até o CEO dizer que podem ser apagados.
