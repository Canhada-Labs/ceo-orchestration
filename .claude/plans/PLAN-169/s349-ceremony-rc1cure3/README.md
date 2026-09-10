# Cerimônia `wave-rc1cure3` — instância do molde `rc1cure2` para o pacote do Codex (ensaio: ver o fim)

Sete arquivos, todos aqui, nenhum na árvore viva:

```
OWNER-RC1-CURE3-SIGN.sh                        pinentry do Owner
OWNER-RC1-CURE3-LAND.sh                        aplica, verifica, commita, empurra
wave-rc1cure3-approved-draft.md                draft do sentinel
s349-ceremony-rc1cure3/bind-patch.sh           congela o pack como material
s349-ceremony-rc1cure3/finalize-rc1cure3.sh     prova a decomposição por item
s349-ceremony-rc1cure3/_restore_targets.py     restauração por bytes (CM-13)
rehearse.sh                                   o ensaio inteiro, num clone
```

## Cerimônia por PATCH, não por derivador

A `relmeta2` derivava o patch de um script e o V1 provava
`HEAD + script == patch`. Aqui o patch é **dado** pelo agente que construiu as
curas, então a pergunta muda. O que estes scripts provam:

1. o patch **aplica** em HEAD;
2. ele toca **exatamente** o escopo assinado — derivado de
   `git apply --numstat` e cruzado com o `SCOPE.txt` que o pack declarou;
   divergência entre os dois **aborta o bind**;
3. a **decomposição por item** (`git apply --include=<path>`, que é como o
   LAND aplica, para nenhum hunk fora do escopo entrar de carona) reproduz o
   patch inteiro byte a byte;
4. os alvos ainda estão no estado **PRÉ-edição** do baseline.

## Os quatro comandos do Owner

Depois de o CEO rodar o `bind-patch.sh` e landar os materiais:

```
bash .claude/plans/PLAN-169/s349-ceremony-rc1cure3/finalize-rc1cure3.sh
bash .claude/plans/PLAN-169/OWNER-RC1-CURE3-SIGN.sh          # pinentry
bash .claude/plans/PLAN-169/OWNER-RC1-CURE3-LAND.sh --dry-run
bash .claude/plans/PLAN-169/OWNER-RC1-CURE3-LAND.sh
```

## Ensaio: 13 PASS, 0 FAIL

Rodado com um pack **sintético** (o patch real ainda não existe), num
`git clone --local` — **nunca** num worktree, porque worktrees compartilham a
`.git/config` e foi assim que o `origin` do repositório vivo foi trocado na
S348. O ensaio prova isso explicitamente, checando que o clone tem config
própria.

O ensaio cobre: bind, **land e push dos materiais** (o HEAD anda sem tocar
alvo), finalize, SIGN em auto-teste, chave GPG descartável em `GNUPGHOME`
curto, LAND `--dry-run` com **DRY-RUN VERDE**, **LAND real** com commit e push
ao bare do próprio clone, e o controle de falha (patch adulterado ⇒ rc≠0 e
árvore limpa).

## Três defeitos que o ensaio pegou, e não o `bash -n`

1. **`$APPLY` órfão no SIGN.** A adaptação trocou a atribuição mas deixou a
   referência: `unbound variable` na primeira linha executada.
2. **`BASE-HEAD` como invariante enforçado.** O fluxo real é bind → o CEO
   landa os materiais → o Owner assina, e esse land **move o HEAD** sem tocar
   alvo nenhum. Exigir `BASE-HEAD == HEAD` mataria a cerimônia na manhã do
   Owner. Passou a ser fato **registrado**; quem decide são os hashes PRE por
   alvo e um `git apply --check`. O `Anchor-SHA` do sentinel, esse sim,
   continua exigido — ele descreve a árvore que o Owner assinou.
3. **O ensaio não empurrava os materiais.** O guard de push do LAND exige
   `origin/main == Anchor-SHA`, e com razão. Sem o push no ensaio, ele media
   uma situação que não vai existir.

## Regras da S348 honradas

- Ensaio de push só em `git clone --local`; zero `git remote`/`git config`
  dentro de worktree.
- Staging derivado do `MATERIALS.sha256` e do `PAYLOAD.sha256`, nunca
  `git add` de diretório.
- `TODAY` pinado pelo bind no baseline, lido pelo SIGN — sem rollover UTC.
- O finalize restaura os alvos rastreados em qualquer falha, por escrita
  Python num trap.
- O manifesto ADR-192 só entra se algum membro for tocado; se for tocado e o
  manifesto ficar fora do escopo, o bind **aborta**.
- `check-ceremony-script.py`: **zero BLOCKING** nos quatro scripts.

## Pendente

`bind-patch.sh` precisa do pack final (`rc1-cure.patch` + `SCOPE.txt`). Quando
o `CLAIM.md` do `rc1-cure` aparecer, o bind roda sobre o patch real e o ensaio
se repete com ele — o `payload/` nasce vazio por desenho, porque todo o
conteúdo novo vem do próprio patch.

## Ensaio desta instância (09/09/2026, 20:47): 13 PASS, 0 FAIL

Rodado com o pack REAL (`rc1-cure-3.patch`, 19 arquivos, 7 canônicos; sha256
`c2d4779a54348d3ea3e08ea4ececd3126f490c5364a3bdca68031851fff72cf2`) num `git clone --local`
do repositório vivo, nunca num worktree: bind, land dos materiais (o HEAD anda sem tocar alvo),
finalize (aplicação por item == patch, árvore restaurada), SIGN em auto-teste, chave GPG
descartável em GNUPGHOME curto, LAND `--dry-run` com **DRY-RUN VERDE**, LAND real com commit e
push ao bare do clone, e o controle de falha (patch adulterado ⇒ `MATERIALS.sha256 nao confere`,
rc 1, árvore limpa). Harness: `<PK>/rc1-cure-3/ceremony/rehearse.sh <repo-vivo> <pack-dir>`.

## Versão 3 do patch (09/09/2026, ~22:00) — revisão Codex dos bytes finais absorvida

A revisão read-only do Codex sobre os bytes finais do patch v2 (21:24–21:34) devolveu
NO-GO com 2 P1 + 2 P2, todos verificados no código: o helper de ancestral excluía
symlinks (`SPEC -> arquivo` passava as duas preflights e o `mkdir` abortava depois das
escritas); a preflight do `upgrade.sh` saía com `exit 3` antes de persistir
`upgrade_succeeded: false` e do sumário `routes=0` — o e2e histórico no v2 reprovou
EXATAMENTE H.15e4 e H.15f3 (controle positivo); `--skip 'SPEC/v1/*'` com `SPEC`
arquivo (declarado no item 60); o kit escrevia no `~/.rc2-backup` real. A v3 cura os dois
P1 no código, declara o P2 de skip e isola o HOME do kit; e2e R12 ganha as formas
symlink-para-arquivo e pendente (rotas e `SPEC/v1`, nos dois scripts) e o controle positivo
symlink-para-diretório; o baseline do censo write-safety (ratchet) é regenerado no mesmo
pack. Segunda passagem do Codex sobre a v3: `NO-GO: 1 P1 (baseline do censo, regenerado no proprio pack) + 2 P2 de texto, absorvidos na v4` — a v4 (este patch, sha256
`3e3ef2a807a968a4076109dbf4af620f40904db0758d07b98a6ad3d889ceeebc`) absorve os dois P2 de texto (47 e 18; `CONDITIONS-history.md` v54 e v55).
Mesmos 19 caminhos, 7 canônicos. Provas nos bytes finais: e2e write-safety e e2e histórico
(v3 de código = v4), ensaio da cerimônia num clone (12/13 — a única falha é do harness:
o controle de falha re-binda num clone onde os materiais já são rastreados e o finalize
recusa por «árvore suja» antes de ver o patch adulterado). O rebind repete o
`bind-patch.sh` com `--today 2026-09-09`; `BASE-HEAD` passa a ser o commit dos materiais
v2 (`8c05842`), o que finalize/SIGN/LAND toleram por desenho (os hashes PRE decidem).

**Abreviação de hash pinada.** As linhas `index a..b` do `git diff` usam abreviação
automática pelo número de objetos EMPACOTADOS e o repositório está na fronteira de 16.384
(um clone `--no-hardlinks` já produz 8 hex; o vivo, 7) — o patch congelado deixaria de
reproduzir byte a byte no V1 do finalize/LAND, e esse erro morre em silêncio (`diff|sed` sob
`set -e -o pipefail` antes do `die`). Cura: `git config core.abbrev 12` no repositório
vivo (feito em 09/09 22:04; só afeta exibição) e o patch gerado com o mesmo pino; o ensaio
injeta o pino por `GIT_CONFIG_COUNT/KEY_0/VALUE_0`.
