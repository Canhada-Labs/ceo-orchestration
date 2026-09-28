# codex-pin-0156 — re-pin do Codex CLI 0.155.0 → 0.156.1 (PLAN-193 W2)

Pack de cerimônia no molde de `PLAN-189/codex-pin-0155/`: 2 arquivos canônicos,
1 sentinel, 1 pinentry. Quem assina é o Owner; o script NÃO faz push. O nome
do diretório (`0156`) é o do minor: o pack foi montado primeiro para o 0.156.0
(nunca assinado) e remontado para o 0.156.1, que você já instalou.

| arquivo | o que é |
|---|---|
| `codex-cli-pin.txt.new` | o pin vivo + um parágrafo datado + range `>=0.128.0,<0.157.0` |
| `codex-cli-pin-manifest.json.new` | o manifesto vivo com `package_version`, `npm_integrity` (plataforma) e `sha256` do payload do 0.156.1 |
| `pin-0156-approved.md` | sentinel (rascunho: Anchor-SHA e Data são preenchidos pelo SIGN) |
| `OWNER-PIN-SIGN.sh` | a cerimônia (P0 → 7 passos → commit local) |
| `rehearse-pin-0156.sh` | ensaio ponta a ponta numa cópia descartável (não toca neste checkout) |

## Ordem — obrigatória

**Você NÃO precisa reinstalar nada.** O `npm i -g` do 0.156.1 já foi feito
(o payload global confere, byte a byte, com o tarball do registry que este
pack pina). Mantenha-o instalado até o SIGN.

1. **GA da v1.4.1 primeiro** (`PLAN-192/OWNER-GA-CUT.sh`). Não rode este
   SIGN antes: o step 15 do `release.yml` confere o veredito do GA contra o
   manifesto da árvore tagueada, e o SIGN recusa rodar sem a tag `v1.4.1`
   publicada. O re-pass do GA não precisa do 0.155.0 global: quando o global
   não é a versão pinada, o runner do re-pass
   (`PLAN-192/repass-ga/run-ga-repass.sh`) cai na rota do `npx` num cache
   próprio — nada é instalado e o global não é tocado. **Atenção à ordem
   nessa rota** (é do kit do GA, não deste pack): o runner roda
   `npx -y @openai/codex@0.155.0 --version`, que EXECUTA o binário baixado,
   e só DEPOIS confere o hash dele contra o manifesto (a conferência reprova
   o re-pass se não bater). Conferir antes de executar (M4) só vale na rota
   do codex global pinado. Se você quer M4 também no GA, sem mexer no global,
   dê ao GA um `codex` 0.155.0 conferido antes de qualquer execução (opcional;
   medido em 2026-09-23: o `-c true` só materializa o pacote, que não tem
   scripts de instalação, e o payload materializado dá `verified` contra o
   manifesto vivo):

       C=$(mktemp -d) \
         && npm_config_cache="$C" npx -y --package=@openai/codex@0.155.0 -c true \
         && L=$(find "$C/_npx" -path '*/node_modules/.bin/codex') \
         && [ "$(printf '%s\n' "$L" | grep -c .)" = 1 ] \
         && python3 .claude/hooks/check_pair_rail.py --verify-codex-pin "$L" \
         && PATH="$(dirname "$L"):$PATH" bash .claude/plans/PLAN-192/OWNER-GA-CUT.sh

   É UM comando: qualquer passo que falhe (download, zero ou mais de um
   launcher, conferência sem `verified`) para a cadeia e o GA não roda por
   este caminho. Com a conferência verde, o runner cai na rota do global
   pinado, com o hash conferido antes do `--version` (medido em 2026-09-23
   executando o bloco de seleção de rota do runner, tal como está, num clone:
   com esse PATH, rota do global pinado; sem ele, a rota do global reprova no
   hash sem executar o 0.156.1 e o runner seguiria para o `npx`). O global
   0.156.1 segue instalado para o SIGN.
2. Depois do GA (o `main` está congelado até lá), traga o pack para o
   checkout VIVO. Ele foi montado no worktree `wt-pin` (branch
   `s357/codex-pin`, criado a partir do `main` com o kit do GA), justamente
   para o checkout vivo ficar limpo durante o corte — o G0 do GA recusa
   arquivo não rastreado. Na raiz do checkout vivo, em `main`, com o GA já
   publicado:

       PF=.claude/plans/PLAN-193-release-v1-4-2-opus55-fasttrack.md
       PK=.claude/plans/PLAN-193/codex-pin-0156
       WT=$(git worktree list --porcelain | sed -n 's|^worktree \(.*/wt-pin\)$|\1|p') \
         && [ "$(printf '%s\n' "$WT" | grep -c .)" = 1 ] \
         && { [ ! -e "$PK" ] || diff -r -q "$WT/$PK" "$PK"; } \
         && if git ls-files --error-unmatch -- "$PF" >/dev/null 2>&1; then
              SRCPF="$PF"; echo "o plano já está no main: fica o do HEAD"
            elif [ ! -e "$PF" ] || cmp -s "$WT/$PF" "$PF"; then
              SRCPF="$WT/$PF"
            else
              echo "RECUSA: $PF existe fora do índice e difere do worktree"; false
            fi \
         && awk '/npm/ && /@openai\/codex/ &&
                 /(^|[^[:alnum:]_-])(-g|--global|--location[= ]global)([^[:alnum:]_-]|$)/ &&
                 /(^|[^[:alnum:]_-])(i|in|ins|inst|insta|instal|install|isnt|isnta|isntal|isntall|add|up|update|udpate|upgrade)([^[:alnum:]_-]|$)/ {
                   s = $0; gsub(/@openai\/codex@0[.]156[.]1([^0-9.a-z-]|[.]([^0-9]|$)|$)/, "#", s)
                   if (s ~ /@openai\/codex/) { print "RECUSA (instala outro codex) " FNR ": " $0; bad = 1 }
                 }
                 END { exit bad }' "$SRCPF" \
         && { [ "$SRCPF" = "$PF" ] || { cp "$WT/$PF" "$PF" && cmp "$WT/$PF" "$PF"; }; } \
         && mkdir -p .claude/plans/PLAN-193 \
         && cp -R "$WT/$PK" .claude/plans/PLAN-193/ \
         && diff -r "$WT/$PK" "$PK" \
         && shasum -a 256 "$PK"/*

   Qualquer passo que falhe para a cadeia, e as conferências vêm antes de
   qualquer cópia: worktree não achado (ou mais de um), pack já presente no
   checkout vivo e diferente do worktree, plano fora do índice e diferente
   do worktree (nada é sobrescrito), ou um plano com linha de instalação
   GLOBAL de outro codex (a cadeia imprime as linhas culpadas e não copia
   nada). O detector olha cada LINHA do plano que tenha, em qualquer ordem,
   `npm`, um verbo de instalação (`i`, `install`, `add`, `update`, `up`,
   `upgrade` e os apelidos do npm), uma flag global (`-g`, `--global`,
   `--location=global`) e `@openai/codex` — com ou sem versão —, e recusa se
   sobrar alguma ocorrência de `@openai/codex` que não seja exatamente
   `@openai/codex@0.156.1` (`@0.156.10`, `@latest` ou sem versão recusam).
   Fora dessa forma (outra ferramenta — `brew`, `pnpm`, `yarn` — ou um
   comando quebrado em várias linhas) ele não vê: o backstop é o P0 do SIGN,
   que confere o payload instalado por hash antes do pinentry. A recusa é
   de propósito: seguir um plano assim trocaria o binário instalado e o SIGN
   recusaria no P0 — um plano assim volta para o CEO corrigir antes de
   qualquer commit. Rodar a cadeia de novo depois de uma cópia COMPLETA é
   seguro (o que já estiver igual ao worktree é aceito). Se a cópia ficou
   PARCIAL (o `cp` parou no meio), a cadeia passa a recusar por diferença;
   apague só o que ela criou e ainda NÃO está rastreado, e rode a cadeia de
   novo (no mesmo terminal: usa o `PF` e o `PK` do bloco acima; sem eles,
   as duas linhas não apagam nada):

       git ls-files --error-unmatch -- "$PF" >/dev/null 2>&1 || rm -f -- "$PF"
       [ -n "$(git ls-files -- "$PK")" ] || rm -rf -- "$PK"

   A ordem entre este pack e os materiais da wave-opus55
   (que também moram em `PLAN-193/`) não importa: a cadeia olha só para
   `codex-pin-0156/` e aceita o plano que já estiver rastreado, venha de
   onde vier.

   O `shasum` tem de bater com esta tabela (o README não se lista; o
   `diff -r` o cobre):

       OWNER-PIN-SIGN.sh                 68dadd46788c44f14b3b101081b0a25cc4a0ee7496d78f781121d9975238937f
       codex-cli-pin-manifest.json.new   1828a56abf1acec1dadb6484aa271d263faefafe8827a75a4177f778facc933a
       codex-cli-pin.txt.new             11514263cc7c219ca0d40ff8bc294f2d69cd5c837e08f80d1e10e0e73148a6f8
       pin-0156-approved.md              eddc451c636121e7dd9731dbd316e96cbec7d00e190e2f5dab52ad1d3ea31744
       rehearse-pin-0156.sh              f84eb5f0c3d9ae963e10aa5dd88a7a0dc84242f2a993823b8543067558a35999

   O worktree mora na pasta TEMPORÁRIA da sessão, que o macOS pode limpar
   (reboot): o pack não rastreado sumiria com ela. Se o pack tiver sido
   commitado no branch `s357/codex-pin` (o branch vive no `.git` do
   checkout vivo e sobrevive), `git cherry-pick --no-commit <commit>` no
   lugar do bloco acima traz os arquivos daquele commit já staged e SEM
   commit; confira que são só os do pack e, se ele ainda não estiver no
   `main`, o do plano (`git diff --cached --name-only`), rode o mesmo
   `awk` de instalação do bloco acima sobre o plano e o
   `shasum -a 256 .claude/plans/PLAN-193/codex-pin-0156/*` contra a tabela,
   e siga para o passo 3 (um cherry-pick SEM `--no-commit` commitaria antes
   dos gates do passo 4).
3. Ensaie, ainda sem commitar — agora sobre o `main` de verdade, com a tag
   `v1.4.1` real (os ensaios da montagem usaram uma tag FALSA sobre o `main`
   pré-GA, e o GA acrescenta commits ao `main`). O ensaio só LÊ o
   repositório (clona dele) e escreve só na pasta temporária; sai 0 só com
   o placar todo verde:

       bash .claude/plans/PLAN-193/codex-pin-0156/rehearse-pin-0156.sh

4. Commit livre dos materiais — nada aqui é canônico (oráculo
   `--is-canonical` = 0 para o pack e para o plano) —, com os gates de
   corpus rodando DEPOIS do `git add` (eles leem os arquivos da árvore de
   trabalho, os mesmos que o `git add` acabou de stagear), e push:

       PF=.claude/plans/PLAN-193-release-v1-4-2-opus55-fasttrack.md
       PK=.claude/plans/PLAN-193/codex-pin-0156
       git add "$PF" "$PK" \
         && python3 .claude/scripts/check-ceremony-script.py \
         && bash .claude/scripts/validate-governance.sh \
         && python3 .claude/scripts/check_contamination.py \
         && python3 .claude/scripts/check-test-env-hygiene.py \
         && bash .claude/scripts/local/verify-counts.sh --quiet --no-tests \
         && python3 .claude/scripts/check-staleness.py \
         && git commit -m "plan(PLAN-193): materiais do re-pin do codex CLI 0.155.0 -> 0.156.1 (pack codex-pin-0156, ensaiado)" \
         && git push origin main

   O commit leva os 6 arquivos do pack e, se ele ainda não estava no
   `main`, o do plano. Num checkout de um commit sem o plano (o da CI, por
   exemplo), `PLAN-193/` fica órfão e o `validate-governance` reprova;
   localmente, com o plano na árvore mas fora do HEAD, quem recusa é o P0
   do SIGN, que exige o plano rastreado. O SIGN exige o checkout em `main`,
   igual ao `origin/main`, **sem nenhuma modificação rastreada pendente**, e
   roda do checkout VIVO — no worktree ele recusa no P0 (o branch não é
   `main`).
5. **Logo depois**, num terminal normal (o pinentry precisa de TTY), na raiz
   do checkout vivo e SEM `OPENAI_API_KEY` exportada (ver «O que o SIGN
   confere»):

       bash .claude/plans/PLAN-193/codex-pin-0156/OWNER-PIN-SIGN.sh

   (Se quiser ensaiar antes: `--dry-run` no mesmo comando — ele também
   confere o payload instalado e exige uma chave do allowlist de signatários
   no seu GNUPGHOME. Qualquer outro argumento é recusado antes de tudo.)
6. `git push origin main`.

O SIGN exporta `GPG_TTY=$(tty)` sozinho. Se ainda assim o gpg reclamar de
pinentry, a assinatura falha antes de qualquer commit e a árvore é
restaurada: confira o `pinentry-program` do seu `~/.gnupg/gpg-agent.conf` e
rode de novo. Se o gpg ficar parado em «waiting for lock» (trava órfã do
keyring, deixada por um gpg que morreu — o corte do GA, logo antes, também
usa GPG), interrompa com Ctrl-C (no P0 nada mudou ainda; na assinatura, o
SIGN restaura a árvore), remova em `~/.gnupg/public-keys.d/` as travas
`.#lk*` e `pubring.db.lock` de processos que já não rodam (confira com
`ps`) e rode de novo. O ensaio não exercita o pinentry real (a chave
descartável não tem senha).

## A janela de rail fechado — já está aberta

Desde que o 0.156.1 foi instalado, o binário global não bate com o manifesto
vivo (que pina o 0.155.0): o pair-rail está **fail-CLOSED** neste repo — é o
comportamento certo do ADR-182, não defeito (medido em 2026-09-23:
`--verify-codex-pin` → `mismatch payload_sha256_mismatch`). Na prática, até o
SIGN:

- numa sessão do Claude Code neste repo, o hook do pair-rail recusa executar
  o codex não verificado e **bloqueia** as escritas (Edit/Write) em caminhos
  L3+ que ele revisaria;
- o `pair-rail-gate.sh --phase 6` reprova no Gate 4 (pin).

A janela fecha quando o SIGN aplica os dois canônicos no checkout vivo (passo
3/7 dele); na CI, depois do push; nos outros checkouts (o worktree `wt-pin`
inclusive), quando eles receberem o commit. Por isso o SIGN vai logo depois
do GA. Se ele abortar ANTES de o `main` avançar (falha, Ctrl-C, TERM ou
HUP), restaura a árvore (manifesto de 0.155.0) e o rail segue fechado até
você corrigir a causa e rodá-lo de novo. Uma falha DEPOIS do avanço (o commit
já no `main` local) não restaura nada: para com «NÃO faça push» e imprime o
comando para desfazer só o commit. Um `kill -9` ou a queda da máquina não
rodam restauração. O diretório de backup que o SIGN imprime logo no começo
fica na pasta temporária, que um reboot pode apagar — mas os originais
sempre voltam do git, porque o P0 exige a árvore igual ao HEAD. Se o `main`
NÃO avançou (`git log -1` não é o commit da cerimônia):

    git checkout HEAD -- .claude/governance/codex-cli-pin.txt \
      .claude/governance/codex-cli-pin-manifest.json \
      .claude/plans/PLAN-193/codex-pin-0156/pin-0156-approved.md \
      && rm -f .claude/plans/PLAN-193/codex-pin-0156/pin-0156-approved.md.asc

Se o `main` JÁ avançou (a morte veio depois do `update-ref`), não restaure
nada: a árvore tem de bater com o commit; sincronize só o índice
(`git reset -q --` nos dois canônicos, no sentinel e no `.asc`) e confira
`git status` e `git show --stat HEAD` antes do push.

Se precisar do rail aberto ANTES do GA, a saída é voltar ao binário que o
manifesto vivo pina (`npm i -g @openai/codex@0.155.0`) — e reinstalar o
0.156.1 (`npm i -g @openai/codex@0.156.1`) antes do SIGN: com o 0.155.0
instalado, o SIGN aborta no P0 («ainda é o que o manifesto vivo pina»), e com
qualquer outro binário que não seja o 0.156.1 medido, também («NÃO é o
0.156.1 medido no registry»). Não é necessário para o GA.

## O que o SIGN confere

Antes de assinar:

- o argumento: nenhum (run real) ou exatamente `--dry-run` — qualquer outro
  (`--dryrun`, argumento a mais) recusa antes do P0, sem tocar em nada;
- nenhuma variável git herdada que o próprio git declara local ao
  repositório (`git rev-parse --local-env-vars`: `GIT_DIR`, `GIT_INDEX_FILE`,
  `GIT_CONFIG_PARAMETERS`...) — se houver, recusa e diz quais;
- `main` = `origin/main`, árvore rastreada limpa — pelo `git status` E por
  `git diff` contra o HEAD sobre um índice temporário (um bit
  assume-unchanged/skip-worktree no seu índice não esconde edição) —, os 6
  arquivos do pack e o arquivo do plano no HEAD;
- a tag `v1.4.1` existe, é ancestral do HEAD e é o mesmo objeto no remoto;
- os dois canônicos vivos têm o sha256 de quando o pack foi montado, e os
  `.new` têm o sha256 que o script e o sentinel declaram (guard de deriva);
- o payload instalado tem o sha256 do 0.156.1 medido no registry — por hash,
  contra o manifesto VIVO (que tem de dar `mismatch` com exatamente esse
  sha256), sem executar o binário;
- há no seu GNUPGHOME uma chave secreta que passa nas duas pernas de
  signatário do guard canônico (`.claude/sentinel-signers.txt` e o registro
  do ADR-121) — é ela que assina (`--local-user`);
- as rotas de auth que a phase 6 vai exigir depois de aplicar (Gates 1 e 2
  do `pair-rail-gate.sh`), pela mesma regra do gate e sem executar o codex:
  com `OPENAI_API_KEY` no ambiente, a última rotação dela em
  `docs/rotation-log.md` tem de ter menos de 90 dias (ou
  `CEO_CODEX_KEY_ROTATION_OVERRIDE=1`, anunciado e registrado no commit);
  sem ela, `~/.codex/auth.json` não vazio (rota login). A última rotação
  registrada hoje é de 2026-05-09: rode o SIGN SEM `OPENAI_API_KEY`
  exportada — com ela, o P0 recusa e diz o remédio, antes do pinentry;
- no run real, `GPG_TTY` passa a ser o terminal da cerimônia.

Depois de aplicar: semântica do range pela função do próprio validador do
`release.yml`; `--verify-codex-pin` = `verified`; `pair-rail-gate.sh --phase 6`
com `codex-cli 0.156.1`; a bateria (governance, contamination, counts,
ceremony-lint e os testes que leem o pin vivo, com a sonda T2 obrigatoriamente
`PASSED`) num ambiente de allowlist; nenhum arquivo rastreado fora do escopo
alterado e os do escopo iguais às cópias congeladas. O commit é montado por
plumbing a partir das cópias congeladas, conferido em nomes e bytes, e o
`main` só avança por compare-and-swap. Depois: escopo do commit e árvore de
trabalho conferidos; divergência é FALHA com **NÃO faça push** e o comando
para desfazer só o commit.

## Diferenças para o molde (`PLAN-189/codex-pin-0155/OWNER-PIN-SIGN.sh`)

1. Todo literal de versão, digest, tag e coautor vive num bloco de constantes;
   mensagem de commit, checagens e avisos derivam dele (o molde tinha
   `0.154.0 -> 0.155.0` e `<0.155.0 -> <0.156.0` soltos na mensagem). Foi o
   que permitiu remontar o pack de 0.156.0 para 0.156.1 trocando só o bloco.
2. Guard de deriva nos canônicos vivos e nos `.new` (o molde fazia `cp .new`
   por cima do vivo sem conferir — uma edição posterior seria revertida em
   silêncio).
3. Conferência do binário instalado ANTES da assinatura, só por hash (o molde
   só descobria no passo 4, depois de gastar o pinentry).
4. Gate da tag do GA (ordem obrigatória acima).
5. Verificador ancorado em `CLAUDE_PROJECT_DIR=<raiz>` e sem costuras de teste
   herdadas; o JSON é conferido campo a campo (status, detail, sha256,
   expected, manifesto, triple), não só `"status": "verified"`.
6. O SIGN preenche também a `Data` (o pack espera o GA; a data da assinatura
   não é a da montagem). O molde não tinha `Approved-By`; este também não — a
   identidade vem da assinatura, e o fingerprint entra na mensagem do commit.
7. A bateria inclui os testes que leem o pin vivo e a sonda T2 que executa o
   codex — rodada com `-rA`, e a sonda tem de constar `PASSED` (pulada, o rc
   do pytest seria 0 e o molde não veria).
8. O P0 exige o arquivo do plano no HEAD (o molde vivia em `PLAN-189/`, cujo
   plano já estava commitado).
9. O trap de restauração só arma DEPOIS do P0 e nunca mexe no índice. No molde
   ele já estava armado quando o P0 abortava por «modificação rastreada», e o
   `unstage` desfazia o índice de quem rodou nos 4 caminhos do escopo (medido:
   a variante com o trap do molde tira do índice uma mudança staged; este
   SIGN a mantém).
10. INT, TERM e HUP saem pelo mesmo caminho de restauração, com trap próprio
    que sai com 130/143/129. No bash 3.2 do macOS o trap de `EXIT` roda
    nesses sinais, mas num TERM ou HUP com `$?` = 0 (o status do último
    comando concluído), e o cleanup do molde, condicionado a rc≠0, não
    disparava (medido; num Ctrl-C — INT ao grupo — o `$?` já chega 130 e o
    molde restaurava). As mensagens do trap, do restore e do `die` saem por
    um fd salvo no começo com o stderr do terminal (fd 9): um sinal durante
    a bateria do passo 5 — chamadas de FUNÇÃO com a saída redirecionada para
    log — roda o trap ainda dentro desse redirecionamento, e pelo fd 2 o
    «árvore RESTAURADA» ia para o log, não para o terminal (medido; o ensaio
    conta esse caso). O avanço do `main`, o desarme da restauração
    e a sincronização do índice correm com esses sinais IGNORADOS (senão um
    TERM logo depois do `update-ref` restauraria arquivos com o commit já no
    `main`); falha na sincronização vira «NÃO faça push» com o comando exato.
    O P0 recusa `index.lock` pendente (a sincronização é o último passo).
11. Hooks do git desligados nas operações git da PRÓPRIA cerimônia
    (`core.hooksPath=/dev/null` via `GIT_CONFIG_*` — inclusive o
    `reference-transaction`, que roda até em `update-ref`) e nas que o
    verificador e a phase 6 herdam. A bateria do passo 5 roda em ambiente de
    allowlist, SEM essas variáveis: um git que um gate dela rode usa a config
    do repositório (no ensaio, com hooks instalados, nenhum disparou — é
    medição, não construção). E commit por
    plumbing (`hash-object -w --no-filters` → índice temporário →
    `write-tree` → `commit-tree` → `update-ref` com o HEAD antigo como
    compare-and-swap), a partir de cópias CONGELADAS dos `.new`, do sentinel
    assinado e do `.asc`: nenhum filtro/atributo do git troca bytes, e o índice
    de quem rodou só é tocado depois que o `main` avançou. O molde fazia
    `git add` + `git commit` (hooks e filtros no caminho) e conferia só os
    NOMES staged.
12. A chave que assina é escolhida e conferida pelas duas pernas de signatário
    do guard canônico (o molde aceitava qualquer chave padrão do GNUPGHOME).
13. A bateria roda com ambiente de allowlist; a phase 6 e o verificador, com o
    ambiente do Owner menos as costuras de teste (a phase 6 precisa da rota de
    auth do codex). Nada herdado redireciona um gate da bateria (medido: com
    `VERIFY_COUNTS_ROOT` hostil o `verify-counts` reprova, e com
    `PYTEST_ADDOPTS=--collect-only` o pytest sai 0 sem rodar a T2). O override
    de rotação do próprio gate (`CEO_CODEX_KEY_ROTATION_OVERRIDE=1`) segue
    valendo na phase 6 — é o contrato do gate —, mas é anunciado no começo e
    registrado na mensagem do commit; se você não quer esse bypass, rode sem
    ele (e rotacione a chave de API se o Gate 2 pedir).
14. O gate da phase 6 e a sonda T2 executam o payload VERIFICADO pelo caminho
    que o verificador resolveu (um link em `verified-bin/`), como o hook do
    rail — não o launcher do PATH, que o manifesto não pina.
15. Ambiente git herdado: qualquer variável da lista
    `git rev-parse --local-env-vars` presente = recusa antes da primeira
    operação git (medido: um `GIT_CONFIG_PARAMETERS` herdado com
    `core.hooksPath` vence o `GIT_CONFIG_COUNT` e um hook
    `reference-transaction` hostil roda; um `GIT_INDEX_FILE` herdado trocaria
    o índice que o P0 confere). O `core.fsmonitor` também fica desligado.
16. A árvore de trabalho é conferida contra o HEAD por `git diff` sobre um
    índice temporário lido do HEAD, além do `git status` (medido: com bit
    assume-unchanged ou skip-worktree, uma edição some do `git status` — no
    sentinel ela seria assinada — e esse `git diff` a acha, sem falso
    positivo numa árvore limpa).
17. Argumento: no molde, tudo que não fosse exatamente `--dry-run`
    (`--dryrun`, `-n`...) rodava a cerimônia REAL; aqui, só nenhum argumento
    ou exatamente `--dry-run` — o resto recusa antes do P0, sem tocar em nada.
18. As rotas de auth da phase 6 (Gates 1 e 2) são conferidas no P0, antes do
    pinentry. No molde, uma `OPENAI_API_KEY` exportada com rotação vencida
    só reprovava na phase 6, depois da assinatura: restauração e pinentry
    perdido (o molde não tinha ensaio, e o primeiro ensaio deste pack só
    exercitava a rota login).
19. `GPG_TTY` exportado pelo run real (no molde, era só um comentário).
20. Todo comando cuja falha encerraria a cerimônia pelo `set -e` sem mensagem
    própria ganhou um `FAIL:` que diz o que falhou (na primeira montagem
    deste pack, o `git ls-remote`, o plumbing do passo 6 e as cópias caíam
    só com o stderr do comando; no molde, as cópias e o `git add`).

## Ensaio

    bash .claude/plans/PLAN-193/codex-pin-0156/rehearse-pin-0156.sh

Roda de qualquer checkout que tenha o pack — o worktree `wt-pin` inclusive,
antes do GA: só LÊ o repositório (clona dele) e escreve só na pasta
temporária; o checkout vivo não é tocado. Usa o codex GLOBAL do seu PATH (o 0.156.1 instalado) como o codex da
cerimônia — sem instalar nem alterar nada, e confere no fim que ele saiu com os
mesmos bytes. Baixa por `npm pack` (cache npm próprio, nada instalado) o
0.156.1, só para a conferência de bytes (sha512 do tarball de plataforma =
`npm_integrity` pinado; payload = sha256 pinado; payload global byte a byte
igual ao do tarball), e o 0.155.0, conferido contra o manifesto vivo, para o
controle «codex antigo». Recusa rodar com variável git herdada local ao
repositório, e todo git dele roda em ambiente limpo (HOME descartável). Clona
o `main` do repositório (rodado do worktree, o `main` do repositório comum —
depois do GA, já com a tag `v1.4.1`; antes dele, com uma tag FALSA de ensaio)
numa pasta temporária, sobrepõe este pack e o arquivo do plano, usa HOME,
GNUPGHOME, CODEX_HOME e uma chave GPG descartáveis e roda:

- o plano que acompanha o pack não tem linha de instalação global de um
  codex que não seja o 0.156.1 (o mesmo detector da cadeia do passo 2 — um
  plano assim deixa o placar VERMELHO);
- controles de pré-condição, que têm de abortar deixando árvore e índice
  intactos: argumento inválido (`--dryrun` e argumento a mais, recusados
  antes do P0), `OPENAI_API_KEY` com rotação vencida e sem override (recusa
  antes do pinentry, nada assinado), nenhuma rota de auth, chave fora do
  allowlist, chave fora do registro (depois disso a
  chave descartável entra nos dois, só no clone), codex antigo, codex que não
  é nenhum dos pinados (payload falso, que deixaria marcador se fosse
  executado — não pode ser), árvore suja, sem tag do GA, tag divergente do
  remoto, deriva do pin vivo, deriva do manifesto vivo, `.new` editado num
  commit depois dos materiais, sentinel sem um dos digests que o script
  declara, plano fora do HEAD, falha depois da assinatura,
  mudança staged pré-existente, `index.lock` pendente, `GIT_CONFIG_PARAMETERS`
  herdado com hooks hostis (nenhum roda) e `GIT_INDEX_FILE` herdado, edição
  escondida do `git status` por bit do índice (no sentinel com
  assume-unchanged, no allowlist de signatários com skip-worktree);
- controles de sinal e de corrida no run REAL, depois da assinatura: Ctrl-C
  (INT ao grupo de processos da cerimônia) no início da bateria do passo 5 —
  sai 130, restaura sentinel, `.asc` e canônicos, e o «árvore RESTAURADA»
  aparece no TERMINAL —, e um commit que move o HEAD durante a bateria — o
  compare-and-swap do passo 7 recusa, nada é commitado e a árvore é
  restaurada. Esses dois lançam a cerimônia com INT/TERM/HUP em SIG_DFL: um
  `&` de shell não interativo herda o SIGINT IGNORADO, o bash não captura
  sinal ignorado na entrada, e o controle mediria outra coisa (a cerimônia
  seguiria até o commit);
- controles hostis: filtro clean que trocaria o sha256 no manifesto
  (neutralizado — o dry-run completa com a árvore do `.new`), variáveis
  hostis herdadas no dry-run (descartadas; o override de rotação, anunciado,
  com `OPENAI_API_KEY` presente: o P0 deixa passar e a phase 6 roda na rota
  api-key),
  hooks do git instalados no run real — de commit e `reference-transaction`,
  todos sujando o README — (nenhum executa, árvore limpa);
- `--dry-run` e o run real até o commit (nunca o push), com `GPG_TTY`
  exportado.

Sai 0 só com o placar todo verde. Variáveis: `REHEARSE_BASE` (onde criar a
pasta; padrão `$TMPDIR`), `REHEARSE_GLOBAL_CODEX` (o launcher da cerimônia;
padrão `command -v codex`), `REHEARSE_CODEX_PREFIX` e
`REHEARSE_OLD_CODEX_PREFIX` (prefixos npm já montados do novo e do antigo —
evitam baixar ~130 MB cada, mas pulam a conferência do sha512 do tarball),
`REHEARSE_SOCK_BASE` (diretório CURTO para os sockets do gpg-agent; padrão
`$TMPDIR`).

## Se o conteúdo mudar depois de revisado

Qualquer edição num `.new` muda o sha256 que o script (`SRC_*_SHA256`) e o
sentinel («Bytes que esta assinatura cobre») declaram — atualize os dois, a
tabela do passo 2 e rode o ensaio de novo (edição no script ou no sentinel
também muda a tabela). Se um canônico vivo mudar antes da assinatura, o pack
tem de ser remontado a partir do novo vivo (o guard aborta de propósito). Se
sair outro codex e você o instalar antes do SIGN, este pack não serve mais:
o P0 recusa (o payload instalado não é o 0.156.1) e o pack tem de ser
remontado para a versão nova.
