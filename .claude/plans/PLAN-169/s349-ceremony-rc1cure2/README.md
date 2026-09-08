# Cerimônia `wave-rc1cure2` — materiais prontos, ensaio 13/0

Sete arquivos, todos aqui, nenhum na árvore viva:

```
OWNER-RC1-CURE2-SIGN.sh                        pinentry do Owner
OWNER-RC1-CURE2-LAND.sh                        aplica, verifica, commita, empurra
wave-rc1cure2-approved-draft.md                draft do sentinel
s349-ceremony-rc1cure2/bind-patch.sh           congela o pack como material
s349-ceremony-rc1cure2/finalize-rc1cure2.sh     prova a decomposição por item
s349-ceremony-rc1cure2/_restore_targets.py     restauração por bytes (CM-13)
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
bash .claude/plans/PLAN-169/s349-ceremony-rc1cure2/finalize-rc1cure2.sh
bash .claude/plans/PLAN-169/OWNER-RC1-CURE2-SIGN.sh          # pinentry
bash .claude/plans/PLAN-169/OWNER-RC1-CURE2-LAND.sh --dry-run
bash .claude/plans/PLAN-169/OWNER-RC1-CURE2-LAND.sh
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
