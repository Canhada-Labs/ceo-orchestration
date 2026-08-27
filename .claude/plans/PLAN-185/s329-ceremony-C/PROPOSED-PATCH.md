# PROPOSED-PATCH — wave-s329-C (PLAN-185 W1+W2): confinamento de escrita do installer

Patch: `.claude/plans/PLAN-185/s329-ceremony-C/C.patch`
Patch-sha256: 32db4a20a9044be59841eaddc2e641f8e118e8344ff889c5ef616e15c6e4aa24
Base: ver `BASE-SHA.txt` (o `finalize_patch.py` recusa uma sombra cuja base não
seja o HEAD vivo, e grava o mesmo sha no `Patch-base:` do sentinel)

---

## 1. O quê

Nove arquivos, **seis canônicos**:

| path | canônico? | papel |
|---|---|---|
| `scripts/_framework_manifest_set.sh` | **sim** | o predicado compartilhado `_wbm_dst_refuses`, a gramática de handle, o dono do `nlink` |
| `scripts/install.sh` | **sim** | os 7 escritores de destino consultam o predicado; substituição segura; escrita atômica; recuperação com evidência |
| `scripts/upgrade.sh` | **sim** | vira CONSUMIDOR do mesmo predicado e da mesma gramática |
| `.github/workflows/smoke-install.yml` | **sim** | 2 entradas de `paths:` + o step que executa o e2e (FU-2) |
| `.github/workflows/validate.yml` | **sim** | a linha do censo de escrita insegura (FU-3) |
| `.claude/adr/ADR-196-installer-write-confinement.md` | **sim** | "predicado na biblioteca, política no chamador" (FU-6) |
| `scripts/tests/test-installer-write-safety-e2e.sh` | não | 15 fixtures, 50 asserções, ~7 min |
| `docs/threat-model.md` | não | a superfície de escrita de destino entra no contrato (FU-5) |
| `.claude/plans/PLAN-185/s329-ceremony-C/DESIGN-C.md` | não | o registro de desenho |

Mais as superfícies de **contagem derivada** que o ADR novo obriga a atualizar
(`CLAUDE.md`, `README*`, `npm/README.md`, `CHANGELOG.md`, `docs/*`), que o
`verify-counts.sh` decide e o `finalize-C.sh` deriva.

> Números de linha do `DESIGN-C.md` são os da sombra no momento em que ele foi
> escrito e **já divergem** (ele publica `install.sh +477/−40` e o `numstat` de
> hoje dá `+457/−20`). A tabela acima é sobre PAPÉIS. Quem decide o conjunto é
> `EXPECTED_PATCH_PATHS` no `EXPECTED-BASELINE.txt`, derivado pelo
> `finalize-C.sh` a partir do patch e comparado pelo G4 do LAND nos dois
> sentidos — não esta tabela, e não o `DESIGN-C.md`.

Os três não-canônicos viajam no MESMO patch de propósito: um teste que landasse
depois da cura seria uma janela em que a classe não tem guarda, e o wiring no
`smoke-install.yml` é canônico — então o teste e o wiring não podem se separar.

## 2. Por quê

**F1 — `-e` segue symlink.** Todo escritor de destino do `install.sh` decidia se
escrevia testando o destino por EXISTÊNCIA. Um link PENDENTE responde falso ao
`-e`, o escritor toma o ramo "ainda não tem nada aí", e `cp`/`>` escrevem
ATRAVÉS do link. Medido pré-cura: **rc 0**, log dizendo `COPIED:`, e **536
bytes** num caminho fora do alvo. Link RESOLVIDO e ANCESTRAL symlink escapam
igual; **hard link** escapa com toda checagem de caminho passando, porque um
segundo nome para um inode não é um link que caminhada nenhuma encontra.

**F2 — `--github-owner` interpolado cru num `sed s`.** Um valor com `/` termina
o comando cedo: o `sed` sai com "bad flag in substitute command" **depois** de o
`>` já ter truncado o destino. O `.github/CODEOWNERS` sobrevive com **0 bytes**
— pulado por EXISTS para sempre, fora do snapshot de rollback (que cobre só
`$TARGET/.claude`), e lido pelo GitHub como "sem donos". Medido: rc 1, 0 bytes.

## 3. Como a cura funciona

| dimensão | antes | depois |
|---|---|---|
| **decisão de escrever** | `-e "$dst"` por escritor, cada um com a sua forma | `_wbm_dst_refuses <raiz> <relpath>` em `scripts/_framework_manifest_set.sh`, consultado pelos 7 escritores. `rc 0` = RECUSAR, motivo em `_WBM_DST_REFUSE_WHY`. Sem `echo`, sem `exit`. |
| **o que o predicado testa** | — | relpath confinado (`_wbm_route_relpath_ok`); **cada componente** sob a raiz FÍSICA por `-L`, folha incluída (`-L` é verdadeiro para link PENDENTE, a forma cega ao `-e`); contenção física por `cd -P`/`pwd -P` (o piso bash 3.2 não tem `realpath`); tipo da folha regular-ou-diretório, todo OUTRO tipo recusado NOMEADO; e `nlink > 1` na folha, que é a única perna que pega hard link. |
| **política** | implícita em cada escritor | **do CHAMADOR**. `install_one` preserva o SKIP que os testes atuais fixam; os escritores de entrega ACUMULAM recusa nomeada e a RUN falha no fim (`_dst_refusal_verdict` → `exit 1`), **antes** de o manifesto e o install-state registrarem qualquer coisa. |
| **por que acumular** | — | o snapshot de rollback cobre **só** `$TARGET/.claude`; `docs/` e `.github/` não têm rota de restauração, e abortar no meio deixaria o alvo MISTO em permanência. Daí também o **PRÉ-VOO**: todos os destinos de um grupo são respondidos ANTES da primeira escrita do grupo. |
| **substituição do handle** | `sed "s/{{OWNER_HANDLE}}/$X/g"` | os dois `sed` **sumiram** — não foram escapados. `_render_owner_handle` usa expansão de parâmetro (`${line//$marker/$handle}`): o marcador é literal, e o lado de substituição de `${//}` não tem caractere ativo nenhum. Nenhum valor pode mudar o que o programa FAZ. |
| **gramática do handle** | nenhuma no install | `_wbm_github_handle_ok`, adotada **verbatim** da regex que `upgrade.sh:3700` já aplicava, com os conjuntos **ENUMERADOS** em vez de faixas `[A-Za-z0-9]` — uma faixa no shell é resolvida pela collating sequence da locale, e uma gramática que responde diferente em duas locales não é uma gramática só. Validada em TRÊS pontos, porque `GITHUB_OWNER` é global: no parse, antes de RENDERIZAR e antes de PERSISTIR. |
| **escrita** | `>` direto no destino | `mktemp` **no diretório de DESTINO** (mesmo filesystem é requisito: `rename(2)` não cruza filesystem, e estagiar em `$TMPDIR` degrada `mv` para copy+unlink e reabre a janela de 0 byte), `_ATOMIC_TMP_PENDING` publicado para o trap, `chmod 0644` explícito (`mktemp` cria `0600`), e `mv -f`. O destino só é tocado pelo rename: **toda** rota de falha o deixa como estava, inclusive inexistente. |
| **recuperação de 0 byte** | não existia | **proveniência decide, não tamanho** — truncar para zero é um jeito real de desligar roteamento de revisão sem apagar o path. `_codeowners_provenance` exige o manifesto baseline registrando o path como entrega do framework, OU um `github_owner` no install-state lido pela MESMA gramática. Com prova ⇒ re-render RUIDOSO nomeando a evidência; sem prova ⇒ `WARNING` nomeado e o arquivo NÃO é tocado. |

## 4. Medições feitas para este pacote

- **e2e:** `50 passed / 0 failed`, rc 0, ~7 min (15 fixtures, ≈13 installs reais).
- **Controle POSITIVO (o mesmo commit, árvore PRÉ-CURA):** `22 passed / 33
  failed`, rc 1 — e as falhas **nomeiam os bytes**: `F1.1 536 bytes written
  OUTSIDE the target`, `F1.3 8468`, `F1.6 454`, `F1.7 48708`, `F1.5 the FIRST
  destination was written before the group was refused`, `F2.1 .github/CODEOWNERS
  was created (0 bytes)`, `F2.2 accepted (rc=0) or wrote CODEOWNERS`. A receita
  está no cabeçalho do próprio teste.
- **Não-regressão, MEDIDA:** install das duas árvores no MESMO path de destino
  (obrigatório: o installer substitui `{{PROJECT_PATH}}`/`{{PROJECT_NAME}}` em
  `CLAUDE.md`, `PROTOCOL.md`, `team.md` e ~30 `SKILL.md`) — **566 arquivos
  idênticos por sha256**, exceto `PROTOCOL.md` (diff 100% o path do checkout no
  ponteiro) e o manifesto que o hasheia; **modos idênticos em 567 arquivos**,
  medido à parte porque `sha256` não vê modo e esta wave reescreve o caminho de
  escrita estagiada.
- **Dry-run:** pré-cura sobre link pendente dizia `(dry-run) would COPY:` com
  rc 0 — o preview MENTIA, e é com ele que o adopter decide. Curado:
  `REFUSED (nothing written)` + `PRE-FLIGHT` + rc 1, sem criar nada.
- **`bash -n`** e **`shellcheck -S warning`**: limpos nos 3 scripts e no teste.
  Nota: o step de shellcheck do `validate.yml` varre só `.claude/scripts` +
  `.claude/hooks`; `scripts/` fica **FORA** (FU-4) — o V1 do LAND é a única rede.
- **Smoke do upgrade** (conversão a consumidor): 7/7.

### Censo de escrita insegura — e por que ele NÃO mostra a cura

O instrumento estava sendo REESCRITO no repositório vivo durante a mesma noite
(unidade U1.1): o mesmo `scripts/` byte-idêntico devolveu 341 e depois 832
sítios em leituras sucessivas. **Número de censo sem o sha do instrumento não é
reproduzível** — por isso o `EXPECTED-BASELINE.txt` **pina** o instrumento por
sha256 e o gate ABORTA quando ele muda, em vez de comparar réguas diferentes.

Isso não é hipótese: **o pin já disparou uma vez nesta noite.** A primeira
finalização mediu contra `e19ca115…` e abortou quando a U1.1 landou a reescrita
(`9067ecfb…`). O mesmo `scripts/` byte-idêntico rende **341 sítios** num e
**799** no outro; `install.sh` desguardado dá **22** num e **57** no outro.
Nenhum está errado — são réguas diferentes.

Com o instrumento de HEAD (`9067ecfb…`), medido nas duas árvores em sequência
imediata:

| | PRÉ | PÓS |
|---|---:|---:|
| `desguardado` (corpus) | 220 | **217** |
| `indeterminado` | 393 | 426 |
| `guardado` | 26 | 26 |
| BLOQUEANTE | 613 | 643 |
| `install.sh` desguardado | 57 | **54** |
| `upgrade.sh` desguardado | 80 | 80 (só vira consumidor) |

O `DESIGN-C.md` §7 publica `install.sh` 47 → 44 com uma terceira cópia,
congelada (`283a77f9…`). Os três estão certos; são instrumentos diferentes. O
comentário do step novo do `validate.yml` cita ainda um quarto (`25d6dcf3…`).

**O censo não enxerga o predicado compartilhado, e isso é estrutural.** As
formas provadas seguras exigem, para a família symlink, um teste `-L` no mesmo
arquivo (`a1`) ou um helper **DEFINIDO NO MESMO ARQUIVO** com polaridade
`|| abort` (`a2`). A cura viola as duas **por decisão do plano**: o corpo com o
`-L` vive em `_framework_manifest_set.sh` (pô-lo no `install.sh` fecharia a
porta para `upgrade.sh` e `doctor.sh` e recriaria a classe das cópias
divergentes), e a polaridade é de RECUSA. Reformar a cura para caber no
instrumento seria deixar o instrumento ditar a arquitetura. **FU-1** é ensinar
a forma ao censo; **OQ-6** é a decisão do Owner sobre o AC-3.

### O ratchet TEM de entrar regenerado — é condição de land, não resíduo

Pós-patch o censo devolve **`new_blocking=45`** e **`dead_baseline_entries=15`**.
Não são 45 escapes novos: são fingerprints. A cura acrescenta 177 linhas à
biblioteca e reescreve 26 hunks, e sob a regra INVERTIDA tudo que não está
provado seguro nasce `indeterminado`. A direção continua boa — `desguardado`
**cai**.

O que torna isso BLOQUEANTE, e não uma nota de rodapé: **o `validate.yml` deste
mesmo patch** instala um step que roda o censo com `set -euo pipefail`, **sem
`|| true` e sem `continue-on-error`** — o comentário do próprio step declara o
fail-closed. Pós-patch esse comando sai **1**. Landar assim deixaria o
`Validate` vermelho no main no primeiro push, por um gate que o próprio pacote
instala: exatamente a classe que manteve o main vermelho da S322 à S327.

Por isso `EXPECTED_CENSUS_NEW_BLOCKING` e `EXPECTED_CENSUS_DEAD_ENTRIES` valem
**0**, e tanto o passo 4f do `finalize-C.sh` quanto o V4 do LAND **abortam**
enquanto o ratchet estiver sujo. A cura é uma linha, na árvore-sombra:

```
python3 .claude/scripts/check-installer-write-safety.py --repo-root <sombra> --write-baseline
```

`.claude/scripts/data/installer-write-safety-baseline.txt` já está em
`ALLOWED_EXTRA_PATCH_PATHS`, então nenhuma outra edição é necessária. Regenerar
**não é silenciar**: o cabeçalho da própria baseline diz que uma linha ali
significa "este sítio é CONHECIDO do censo", explicitamente **não** uma revisão
humana por sítio ("there are hundreds of them"). O que o ratchet impede é um
sítio novo entrar **calado** — e entrar por um commit assinado, nomeado na
mensagem, é o oposto de calado.

## 5. Manifesto ADR-192

**Nenhum** dos paths consta de `.claude/governance/gate-scripts-manifest.txt`
(9 membros). Nenhum bump de sha é devido, e o G5 do LAND prova isso pela mesma
leitura que o hook faz — além de comparar o número de paths CANÔNICOS contra o
valor derivado pelo finalize E contra o piso humano `6`, para que um patch que
perdesse `scripts/install.sh` não passe como "zero canônicos, todos concedidos".

## 6. Rodadas de pair-rail

Registros em `rail-round-*.md` neste diretório. Cada achado é tratado como
CLAIM: verificado contra o disco, curado na sombra quando real, com pushback
escrito quando falso. O `OWNER-S329-C-SIGN.sh` recusa assinar se o registro de
MAIOR número não carregar `Rail-Verdict: APPROVE` na sua primeira linha
`Rail-Verdict:` — contar rodadas não é ler o veredito, e a ordenação é por
INTEIRO (lexicograficamente `rail-round-10` vem antes de `rail-round-2`).

Pair-Rail-Reviewed: ver `rail-round-*.md`
