# Roteiro do Lote A (S363, PLAN-194): W4 → U2-A → U2-B → W5b

Para o Owner, copiar e colar. Cada pacote do Lote A é UM SIGN (`OWNER-<X>-SIGN.sh`), rodado por você num clone
NOVO do GitHub, um pacote por vez, nesta ordem. O roteiro não tem script próprio: são comandos do git e os SIGNs.

**Regra única.** Cada bloco abaixo termina imprimindo uma palavra em MAIÚSCULAS (por exemplo `CLONE-OK`). Se um
bloco não imprimir essa palavra, ou se o SIGN terminar com um `SIGN-RC` diferente do indicado: **pare e chame o
CEO.** Não apague nada, não rode o bloco de novo, não faça push.

**Entre um pacote e o seguinte**, o CEO confere o commit que você publicou e só então informa a âncora (o SHA) do
pacote seguinte. Cada pacote começa com essa âncora.

**Senha do GPG: até 4 vezes, uma por pacote.** Cada SIGN faz UMA assinatura (`gpg --detach-sign`), depois da
bateria dele. O gpg-agent guarda a senha por 10 minutos depois do último uso (o padrão do gpg; o seu
`~/.gnupg/gpg-agent.conf` não muda esse prazo, conferido em 2026-10-11), e as duas passadas da bateria do W4
somaram 26 minutos no ensaio de 2026-10-11. Os SIGNs dos outros três pacotes rodam as mesmas suítes. A contagem
vale para a sua configuração global do git de 2026-10-11, que não tem `commit.gpgsign` (com ele, o `git commit` do
W4 também assinaria o commit). Fique no terminal: a senha é pedida DEPOIS da bateria.

## 0. Uma vez, antes do W4

Num terminal NOVO (Terminal.app), fora do Claude Code:

```bash
env | grep -E '^(GIT_|CEO_|CLAUDE_PROJECT_DIR)' || echo AMBIENTE-OK
```

```bash
df -Pk "$HOME" | awk 'NR == 2 && $4 >= 30 * 1024 * 1024 {print "DISCO-OK"}'
```

```bash
[ -n "$(git config --global user.name)" ] && [ -n "$(git config --global user.email)" ] && echo IDENTIDADE-OK
```

```bash
export GPG_TTY=$(tty)
URL=https://github.com/Canhada-Labs/ceo-orchestration.git
VIVO="$HOME/canhada-labs/ceo-orchestration"
mkdir -p "$HOME/lote-a-s363" && echo PREPARO-OK
```

`VIVO` é o seu checkout principal: o roteiro só LÊ um arquivo dele, no W4 (passo c). Cada clone ocupa cerca de
240 MB (a árvore rastreada tem 176 MB). A bateria de cada SIGN cria worktrees temporários no `TMPDIR`. O piso
de disco da casa é 30 GB livres.

## Pré-condições: o que cada SIGN confere sozinho e o que fica com o roteiro

Lidas do P0 de cada SIGN nos heads de 2026-10-11 (W4 `14532746`, U2-A `0dcb147e`, U2-B `62e815b9`, W5b
`7ae6d566`). O CEO confere de novo nos SHAs finais.

| | W4 | U2-A | U2-B | W5b |
|---|---|---|---|---|
| terminal interativo, branch `main`, remote do GitHub, `git fetch` + origin/main contido no HEAD | SIGN | SIGN | SIGN | SIGN |
| árvore rastreada limpa, materiais commitados, sentinel por preencher, chave do allowlist, base pinada | SIGN | SIGN | SIGN | SIGN |
| `core.fsmonitor` desligado | **roteiro** | SIGN | SIGN | SIGN |
| hooks desligados (`core.hooksPath=/dev/null`) | **roteiro** | **roteiro** | **roteiro** | SIGN |
| `core.untrackedCache` desligado | **roteiro** | **roteiro** | **roteiro** | **roteiro** |
| clone NOVO, sem sobra de execução anterior | **roteiro** | SIGN | SIGN | SIGN |
| HEAD = a âncora do CEO (o SIGN só exige o HEAD contendo origin/main) | **roteiro** | **roteiro** | **roteiro** | **roteiro** |
| ambiente sem `GIT_*`, `CEO_*` e `CLAUDE_PROJECT_DIR*` | **roteiro** | **roteiro** | **roteiro** | **roteiro** (o SIGN recusa só `CEO_KERNEL_OVERRIDE*`) |
| 30 GB livres; `user.name`/`user.email` na configuração global | **roteiro** | **roteiro** | **roteiro** | **roteiro** |
| ferramentas: gpg, pytest, pytest-xdist | SIGN | SIGN | SIGN | SIGN |
| ferramentas a mais | actionlint, shellcheck, PyYAML: SIGN | — | mkfifo: SIGN | — |
| insumo não rastreado (patch dormente do PLAN-158: 537 bytes, sha256 pinado, aplica no HEAD) | cópia: **roteiro**; conferência: SIGN | — | — | — |

Por que os hooks importam onde o SIGN não confere: o W4 commita com `git commit` (hooks de commit); todos fazem
`git fetch` (hook `reference-transaction`) e `git worktree add` (hook `post-checkout`). O U2-B só aplica depois do
U2-A publicado (o P0 dele confere a pós-imagem do U2-A).

## 1. W4 (pacote 1 de 4)

(a) Clone novo. Na primeira linha, troque o texto depois de `ANCORA=` pela âncora que o CEO informou (em todos os
pacotes).

```bash
ANCORA=COLE-AQUI-O-SHA-DO-CEO
D="$HOME/lote-a-s363/w4"
cd "$HOME/lote-a-s363" && [ ! -e "$D" ] && echo CLONE-LIVRE
```

```bash
git -c core.hooksPath=/dev/null -c core.fsmonitor=false clone --template= --no-checkout --single-branch --branch main "$URL" "$D" && cd "$D" && git config core.hooksPath /dev/null && git config core.fsmonitor false && git config core.untrackedCache false && git checkout main && echo CLONE-OK
```

(b) O HEAD é a âncora e a árvore está limpa.

```bash
[ "$(git rev-parse HEAD)" = "$ANCORA" ] && [ -z "$(git status --porcelain)" ] && echo ANCORA-OK
```

(c) Só no W4: o insumo não rastreado, copiado do seu checkout para o mesmo caminho no clone. O arquivo é ignorado
(`.gitignore`: `staged/`), então a árvore continua limpa. O P0 do SIGN confere de novo tamanho, sha256 e se ele
aplica no HEAD.

```bash
mkdir -p .claude/plans/PLAN-158/staged/wave1 && cp "$VIVO/.claude/plans/PLAN-158/staged/wave1/rollback-oidc-to-token.patch" .claude/plans/PLAN-158/staged/wave1/ && [ "$(shasum -a 256 < .claude/plans/PLAN-158/staged/wave1/rollback-oidc-to-token.patch | cut -d' ' -f1)" = e68a508c86ebe2ac6c2eac444530934e4aa91fe05186f98b6a490d391a845b6a ] && [ -z "$(git status --porcelain)" ] && echo INSUMO-OK
```

(d) O SIGN: bateria, depois a senha do GPG, depois o commit no `main` deste clone. Ele não faz push.

```bash
bash .claude/plans/PLAN-194/w4/OWNER-W4-SIGN.sh; echo "SIGN-RC=$?"
```

`SIGN-RC=0`: siga para (e). Qualquer outro: pare e chame o CEO.

(e) Push, sem force: o git só aceita se o commit que está no main do GitHub for ancestral do seu (avanço
rápido). O passo (f) confere que o main do GitHub ficou no seu commit.

```bash
git push origin main && echo PUSH-OK
```

(f) Conferência e aviso.

```bash
[ "$(git rev-parse HEAD)" = "$(git ls-remote origin refs/heads/main | cut -f1)" ] && echo PUBLICADO-OK && git rev-parse HEAD
```

Mande ao CEO: `W4: SIGN-RC=<n>, PUBLICADO-OK <sha>`. Espere a âncora do U2-A.

## 2. U2-A (pacote 2 de 4)

(a) Clone novo, com a âncora que o CEO informou.

```bash
ANCORA=COLE-AQUI-O-SHA-DO-CEO
D="$HOME/lote-a-s363/u2a"
cd "$HOME/lote-a-s363" && [ ! -e "$D" ] && echo CLONE-LIVRE
```

```bash
git -c core.hooksPath=/dev/null -c core.fsmonitor=false clone --template= --no-checkout --single-branch --branch main "$URL" "$D" && cd "$D" && git config core.hooksPath /dev/null && git config core.fsmonitor false && git config core.untrackedCache false && git checkout main && echo CLONE-OK
```

(b)

```bash
[ "$(git rev-parse HEAD)" = "$ANCORA" ] && [ -z "$(git status --porcelain)" ] && echo ANCORA-OK
```

(c) Sem insumo.

(d)

```bash
bash .claude/plans/PLAN-194/w2a/OWNER-W2A-SIGN.sh; echo "SIGN-RC=$?"
```

`SIGN-RC=0`: siga para (e). `SIGN-RC=3`: o SIGN publicou o commit no `main` deste clone e não sincronizou o índice
e a árvore. Siga para (e) também (o push leva o commit da ref) e diga ao CEO que foi 3. Qualquer outro: pare e
chame o CEO.

(e)

```bash
git push origin main && echo PUSH-OK
```

(f)

```bash
[ "$(git rev-parse HEAD)" = "$(git ls-remote origin refs/heads/main | cut -f1)" ] && echo PUBLICADO-OK && git rev-parse HEAD
```

Mande ao CEO: `U2-A: SIGN-RC=<n>, PUBLICADO-OK <sha>`. Espere a âncora do U2-B.

## 3. U2-B (pacote 3 de 4)

(a)

```bash
ANCORA=COLE-AQUI-O-SHA-DO-CEO
D="$HOME/lote-a-s363/u2b"
cd "$HOME/lote-a-s363" && [ ! -e "$D" ] && echo CLONE-LIVRE
```

```bash
git -c core.hooksPath=/dev/null -c core.fsmonitor=false clone --template= --no-checkout --single-branch --branch main "$URL" "$D" && cd "$D" && git config core.hooksPath /dev/null && git config core.fsmonitor false && git config core.untrackedCache false && git checkout main && echo CLONE-OK
```

(b)

```bash
[ "$(git rev-parse HEAD)" = "$ANCORA" ] && [ -z "$(git status --porcelain)" ] && echo ANCORA-OK
```

(c) Sem insumo.

(d)

```bash
bash .claude/plans/PLAN-194/w2b/OWNER-W2B-SIGN.sh; echo "SIGN-RC=$?"
```

`SIGN-RC=0` ou `SIGN-RC=3` (como no U2-A): siga para (e) e diga ao CEO qual foi. Qualquer outro: pare e chame o
CEO.

(e)

```bash
git push origin main && echo PUSH-OK
```

(f)

```bash
[ "$(git rev-parse HEAD)" = "$(git ls-remote origin refs/heads/main | cut -f1)" ] && echo PUBLICADO-OK && git rev-parse HEAD
```

Mande ao CEO: `U2-B: SIGN-RC=<n>, PUBLICADO-OK <sha>`. Espere a âncora da W5b.

## 4. W5b (pacote 4 de 4)

(a)

```bash
ANCORA=COLE-AQUI-O-SHA-DO-CEO
D="$HOME/lote-a-s363/w5b"
cd "$HOME/lote-a-s363" && [ ! -e "$D" ] && echo CLONE-LIVRE
```

```bash
git -c core.hooksPath=/dev/null -c core.fsmonitor=false clone --template= --no-checkout --single-branch --branch main "$URL" "$D" && cd "$D" && git config core.hooksPath /dev/null && git config core.fsmonitor false && git config core.untrackedCache false && git checkout main && echo CLONE-OK
```

(b)

```bash
[ "$(git rev-parse HEAD)" = "$ANCORA" ] && [ -z "$(git status --porcelain)" ] && echo ANCORA-OK
```

(c) Sem insumo.

(d)

```bash
bash .claude/plans/PLAN-194/w5b/OWNER-W5B-SIGN.sh; echo "SIGN-RC=$?"
```

`SIGN-RC=0` ou `SIGN-RC=3` (como no U2-A): siga para (e) e diga ao CEO qual foi. Qualquer outro: pare e chame o
CEO.

(e)

```bash
git push origin main && echo PUSH-OK
```

(f)

```bash
[ "$(git rev-parse HEAD)" = "$(git ls-remote origin refs/heads/main | cut -f1)" ] && echo PUBLICADO-OK && git rev-parse HEAD
```

Mande ao CEO: `W5b: SIGN-RC=<n>, PUBLICADO-OK <sha>`. O Lote A termina quando o CEO confirmar este último commit.
Os clones em `$HOME/lote-a-s363` ficam até o CEO dizer que podem ser apagados.
