# W6 — `scripts/doctor.sh` vira o QUARTO consumidor do leitor único

**S327** · `scripts/doctor.sh` (+140/−63), `scripts/tests/test-doctor-delivery-route.sh`
(+407/−22). `doctor.sh` **não é canônico** (`--is-canonical` = 0) mas ENTRA no Scope
assinado: o G4 do LAND compara todos os paths tocados, sem filtro de canonicidade.

## O que mudou

1. **O parser privado morreu.** `_route_source` (31 linhas) REMOVIDO; as três consultas
   (`:529` `_restore_file`, `:654` MISSING, `:708` DRIFT) chamam `_wbm_route_src`, o
   mesmo leitor de `install.sh`, `upgrade.sh` e `_parity_classify.py`. Sem wrapper — um
   segundo NOME para o mesmo leitor é a próxima cópia esperando para divergir.
2. **`_framework_manifest_set.sh` agora é OBRIGATÓRIO** (`:188`, fail-closed rc=2 como
   `_hash_lib.sh`) — e presença do ARQUIVO não é presença do CONTRATO: as três funções
   são asseridas POR NOME (`:207`), então rename a montante falha ali, alto, em vez de
   cair no fallback identity — que É o D4 voltando. `HAVE_FMS=0` e o "orphan scan
   skipped" ficaram inalcançáveis e foram REMOVIDOS, não silenciados.
3. **Um override só.** `DELIVERY_ROUTES_TSV` APOSENTADO; vale `FMS_DELIVERY_ROUTES_TSV`,
   a do leitor. Duas variáveis com uma ignorada é pior que nenhuma — envenena-se uma
   tabela que ninguém lê e o run sai verde. Teste prova a velha INERTE.
4. **Guarda no sítio de ESCRITA** (`_restore_refuses`, `:473`; invocada em `:540` ANTES
   do `mkdir -p`, que de destino escapante já cria diretório fora). Polaridade espelha
   `upgrade.sh:_up_tpl_confined_refuses` (0 = RECUSAR). Camadas: léxica (o predicado do
   leitor, no destino E na fonte), symlink (folha e todo ancestral) e física (`cd -P` do
   ancestral existente mais profundo contra o `$TARGET` resolvido).

**Contrato, inalterado e agora com dono único:** `rc 0` rota identity (fonte no stdout) ·
`rc 1` sem linha, identity aplica · `rc 2` RENDERIZADA, malformada **ou hostil** —
fail-CLOSED. `rc=2` nunca pode virar `rc=1`: `rc=1` é respondido pelo fallback identity.

## Antes/depois — executado, não inferido

| controle | RED (pré) | GREEN (pós) |
|---|---|---|
| R.6 parser aposentado (de `git HEAD`) × `src=../../…/etc/hosts` | aceita `rc=0`; **287 bytes copiados de FORA do checkout** | `rc=2`, **0 bytes** |
| R.7 pai do destino é symlink para fora | sem guarda: **536 bytes fora do `$TARGET`** | recusa nomeada, nada fora |
| R.5 e2e, `src` hostil na tabela | — | destino não escrito, recusa nomeada, nenhum arquivo do alvo com os bytes estranhos |

**Escopo honesto do symlink:** num run COMPLETO o HEAD já recusava (`_relpath_unsafe`
descarta no INGEST o registro cujo ancestral é link). A guarda cobre a janela que ele não
vê — roda uma vez, antes do laço; a cópia vem depois (TOCTOU) — e call-sites futuros. O
vetor REAL de escape do doctor era a coluna `src`: esse é o R.6.

## Verificação

`bash -n` OK · `shellcheck -S warning -x` **0 achados, delta 0** vs HEAD · `--help` OK ·
`test-doctor-delivery-route.sh` **59/0** (baseline nesta árvore 22/3) ·
`test-manifest-delivery-route.sh` **34/0**, intocado.

**Os 3 vermelhos do baseline eram FIXTURE, não produto** — e o teste pedira a revisão
("If a future change starts recording it, this fixture is redundant"). A cura do W5
passou a REGISTRAR as rotas; o fixture seguia anexando um segundo registro do mesmo
relpath, doctor trata duplicata como ambígua e derruba OS DOIS, e o path saía do run:
528 registros, Missing 0, rc=0 — com o R.3 verde por vacuidade. Agora só supre quando
ausente e, quando presente, assere que o digest gravado é o do **template** (a promessa
do próprio D3/D1), mais uma perna de não-vacuidade no R.3.
**Custo de CI:** 3 → 5 installs reais (R.3-b e R.5), ~11 min locais; se apertar, R.3-b sai.

**Colateral (NÃO curado — fora do FILE ASSIGNMENT):** `upgrade.sh:3730` e `:3742` fazem
`_utc_tgt="$( cd -P "$TARGET" … && pwd -P )"` sem `|| true`; sob `set -e` a falha do
`cd -P` **aborta o script** em vez de imprimir a recusa nomeada — medido: o ramo
`[ -z "$_utc_tgt" ]` é inalcançável. A versão do doctor leva `|| true`. Vale alinhar.
