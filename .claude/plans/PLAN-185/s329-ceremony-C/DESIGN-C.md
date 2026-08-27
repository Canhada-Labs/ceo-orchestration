# PLAN-185 W1+W2 — DESIGN-C (pacote C, S329)

> Estado: patch pronto na sombra, **não commitado**, aguardando a cerimônia GPG
> do Owner. Base: `f569c9a`. Escopo tocado: 3 canônicos + 1 teste novo.
> Nada do repositório vivo foi alterado por esta unidade.

```
 scripts/_framework_manifest_set.sh | 177 ++++++
 scripts/install.sh                 | 477 +++++++++++++++++++++++++++-----
 scripts/upgrade.sh                 |  60 ++--
 scripts/tests/test-installer-write-safety-e2e.sh   (NOVO, 773 linhas)
```

---

## 1. O que mudou, por arquivo

### `scripts/_framework_manifest_set.sh` (+177, bloco único após `_wbm_source_confined`)

| Linha | Função | Papel |
|---|---|---|
| `:683` | `_wbm_nlink` | contagem de links do inode, ou VAZIO quando não dá para ler. **Movida** de `upgrade.sh:_up_tpl_nlink`, que agora a consome. |
| `:743` | `_wbm_dst_refuses` | o predicado de confinamento de DESTINO. `rc 0 = RECUSAR`, motivo em `_WBM_DST_REFUSE_WHY`. |
| `:837` | `_wbm_github_handle_ok` | a gramática de handle, adotada **verbatim** da regex que `upgrade.sh:3700` já aplicava. |

### `scripts/install.sh` (+477/−40, 26 hunks)

> **Âncoras conferidas no estado FINAL** (pós-curas do rail round-1, §12 — o
> bloco de política subiu de lugar e deslocou tudo abaixo dele). O NOME é a
> referência estável; a linha é conveniência e apodrece.

| Linha | Símbolo | Papel |
|---|---|---|
| `:477` | `_assert_github_owner_grammar` | valida no PARSE; `exit 2` (código já usado para valor de flag rejeitado). |
| `:512` | `--github-owner` | chama a validação no parse. |
| `:771` | `cleanup_on_failure` | trap remove `_ATOMIC_TMP_PENDING` (staging de escrita atômica em voo). |
| `:881`–`:978` | `_dst_record_refusal` `:900`, `_dst_refuses` `:915`, `_dst_preflight` `:933`, `_dst_refusal_verdict` `:947` | a POLÍTICA do lado do install — **acima de tudo que escreve** (§12 P1-1). |
| `:981` / `:1014` | `_dst_global_preflight` + a chamada | PRÉ-VOO GLOBAL, antes do `mkdir -p "$TARGET/.claude"` (`:1033`). |
| `:1070` | `_assert_no_symlink_parents` | o `for` **sem aspas** sobre `IFS='/'` virou `case` (a forma antiga pedia word splitting e ganhava PATHNAME expansion junto: um componente com `*` era trocado pelo que casasse no cwd). |
| `:1161` | `install_template` | escritor 1/7 |
| `:1659` | `install_reference_personas` | escritor 2/7 |
| `:1716` | `install_docs_template` | escritor 3/7 |
| `:1829` | `install_docs_templates` | PRÉ-VOO do grupo `docs/` |
| `:1862` | `_render_owner_handle` | render sem linguagem de substituição |
| `:1884` | `_write_rendered_codeowners` | escrita atômica |
| `:1945` | `_codeowners_provenance` | evidência de ENTREGA, e só ela (OQ-1 + §12 P1-2) |
| `:1955` | `install_github_templates` | escritor 4/7 + PRÉ-VOO do grupo `.github/` + os DOIS `sed` removidos |
| `:2082` / `:2096` | `_SETTINGS_DST_REFUSED` / `build_settings` | escritor 5/7 — veredito único, três consumidores |
| `:2257` | `apply_deny_baseline` | 3º consumidor do veredito de settings |
| `:2532` | `install_protocol_pointer` | escritor 6/7 |
| `:2602` | `_file_mode` | modo octal, GNU-first com saída VALIDADA |
| `:2612` | `portable_sed_inplace` | escritor 7/7 — temporário com nome IMPREVISÍVEL |
| `:3278` | `_write_install_state` | valida ANTES de persistir |
| (fecho da run) | `_dst_refusal_verdict` | → `exit 1`, antes do manifesto |
| — | `_read_target_install_state_github_owner` | **REMOVIDA** (§12 P1-2): owner registrado é evidência de PEDIDO, nunca de entrega. |

> Os três pontos de validação do handle: parse (`:512`), antes de RENDERIZAR
> (dentro de `install_github_templates`), antes de PERSISTIR
> (`_write_install_state`). Definição em `:477`.

### `scripts/upgrade.sh` (+60/−40) — vira CONSUMIDOR

| Linha | Símbolo | Papel |
|---|---|---|
| `:3692` | `_read_install_state_github_owner` | python3 segue fazendo o trabalho de JSON (schema, tipos, presença); o **conjunto de caracteres** agora é respondido por `_wbm_github_handle_ok`. Predicado ausente ⇒ `rc 3`, nunca re-implementação local. |
| `:3867` | `_up_tpl_nlink` | delega a `_wbm_nlink`. Biblioteca ausente ⇒ WARNING nomeado + resposta vazia (fail-open em INFRAESTRUTURA, `CLAUDE.md` §4), que é a semântica que o chamador já tinha. |

---

## 2. Contrato do predicado — `_wbm_dst_refuses <target_root> <rel_path>`

`rc 0` = **recusar**, motivo legível em `_WBM_DST_REFUSE_WHY`. `rc 1` = confinado.
Sem `echo`, sem `exit`. A polaridade é a que `_install_src_refuses` e
`_up_tpl_multilink_refuses` já usam: a função tem o nome do que o `0` SIGNIFICA.

Recusa, em ordem:

1. **raiz ou relpath vazios**
2. **relpath não confinado** — via o mesmo `_wbm_route_relpath_ok` que todo path
   confinado desta biblioteca já atravessa (absoluto, `..`, segmento vazio,
   metacaractere de glob, espaço em branco).
3. **componente symlink** — cada componente sob a raiz FÍSICA testado com `-L`,
   **folha incluída**. `-L` é verdadeiro para link PENDENTE, que é exatamente a
   forma cega ao `-e`. A mensagem distingue pendente de resolvido.
4. **contenção física** — o ancestral existente mais profundo tem de resolver
   (`cd -P`/`pwd -P`; o piso bash 3.2 não tem `realpath`) sob a raiz resolvida.
5. **tipo da folha** — se existe, tem de ser arquivo regular ou diretório. Recusar
   todo OUTRO tipo é a inversão da W0 aplicada aqui: um fifo ou device node num
   destino é recusa NOMEADA, não forma que ninguém modelou.
6. **hard link** — `nlink > 1` na folha regular. `-L` não vê um segundo nome do
   mesmo inode; nenhuma caminhada de path vê.

**Política é do CHAMADOR** (debate C5). `install_one` preserva o SKIP que os
testes atuais fixam; os escritores de entrega ACUMULAM recusa nomeada e a **RUN
falha no fim** (`_dst_refusal_verdict` → `exit 1`), antes de o manifesto e o
install-state registrarem qualquer coisa — um destino recusado nunca pode ser
inventariado como entrega do framework, ou a recusa de hoje vira o
`PRESERVED (unclaimed)` silencioso do próximo upgrade.

**Por que ACUMULAR e não `exit 1` no sítio** (OQ-4, default do plano): o snapshot
de rollback cobre **só** `$TARGET/.claude`; `docs/` e `.github/` não têm rota de
restauração. Abortar no meio da entrega deixa o alvo MISTO em permanência. Daí
também o **PRÉ-VOO**: todos os destinos de um grupo são respondidos ANTES da
primeira escrita do grupo.

---

## 3. Gramática de handle

Adotada verbatim da regex viva `^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$`: 1–39
caracteres, primeiro alfanumérico, resto alfanumérico ou hífen.

Os conjuntos são **ENUMERADOS** (`[!ABC…z0123456789]`) em vez de faixas
`[A-Za-z0-9]`, porque uma faixa no shell é resolvida pela sequência de
collating da locale, e numa locale UTF-8 pode admitir caracteres que as faixas
de codepoint do Python nunca casam — uma gramática que responde diferente em
duas locales não é uma gramática só.

O que o conjunto fechado compra: o valor não pode conter `/` (o delimitador do
`sed` que produziu o CODEOWNERS de 0 bytes), `&` nem `\` (metacaracteres do lado
de substituição), newline, espaço, nem metacaractere de shell.

**Três pontos de validação**, porque `GITHUB_OWNER` é global e o parse não é o
único caminho até ele: `--github-owner` no parse (`:512`), antes de RENDERIZAR
(`:1925`), e antes de PERSISTIR no install-state (`:3229`).

**OQ-2, default conservador mantido:** `org/team` é sintaxe VÁLIDA de CODEOWNERS
(o template é `@{{OWNER_HANDLE}}`, logo `@org/team` nomeia um TIME) e esta
gramática o rejeita. A mensagem de erro **diz isso** e aponta a edição manual,
em vez de corromper o arquivo. Suportar time exige trocar o delimitador em todos
os consumidores — wave própria.

---

## 4. Substituição segura + escrita atômica

**Os dois `sed` sumiram — não foram escapados.** O `s/{{OWNER_HANDLE}}/$X/g`
punha o valor dentro de um PROGRAMA sed. `_render_owner_handle` (`:1788`) usa
expansão de parâmetro do bash por linha (`${line//$marker/$handle}`): o marcador
é literal, `{` e `}` não são metacaracteres de padrão do bash, e o lado de
substituição de `${//}` não tem caractere ativo nenhum. Nenhum valor pode mudar
o que o programa FAZ — só o que ele escreve. É por isso que o censo deixa de ver
um sítio de interpolação de `sed` aqui: o sítio não existe mais.

`|| [[ -n "$line" ]]` preserva uma última linha sem newline final.

**Sequência atômica** (`_write_rendered_codeowners`, `:1810`):

1. `mkdir -p` do diretório de destino (falha ⇒ recusa registrada, `rc 1`);
2. `mktemp "$dir/.ceo-codeowners.XXXXXX"` — **no diretório de DESTINO**, nome
   imprevisível. Mesmo filesystem é requisito, não preferência: `rename(2)` não
   cruza filesystem, então estagiar em `$TMPDIR` (o que a sonda pré-cura fazia)
   degrada `mv` para copy+unlink e reabre a janela de 0 byte que esta wave existe
   para fechar;
3. `_ATOMIC_TMP_PENDING` publicado para o `trap` (`cleanup_on_failure:776`);
4. render para o temporário; falha ⇒ `rm -f`, destino **NÃO tocado**;
5. `chmod 0644` explícito — `mktemp` cria `0600`, e um CODEOWNERS que o time não
   consegue ler é regressão que bytes e linhas não pegam;
6. `mv -f` para o destino. O destino só é tocado pelo rename, então **toda** rota
   de falha o deixa exatamente como estava — inclusive inexistente.

`mv` sobre um destino que é symlink é impossível de alcançar: a W1 recusa antes
(o segundo residual do plano §5 fica coberto, não reintroduzido).

`portable_sed_inplace` (`:2548`) recebeu o mesmo tratamento: o nome fixo
`${file}.ceo-sed-tmp` era um path que um atacante pode pré-plantar como symlink,
e o `>` escrevia ATRAVÉS dele antes de o `mv` rodar. Agora `mktemp` no diretório
do próprio arquivo, com o modo ORIGINAL carregado (`_file_mode`, `:2538`) — que
é o que `sed -i` faz, e o que mantém o resultado idêntico ao da forma antiga
derivada de umask (**medido: modos idênticos em 567 arquivos**).

---

## 5. Recuperação do CODEOWNERS de 0 bytes — regra de EVIDÊNCIA (OQ-1, default)

0 byte não distingue "o `sed` abortou" de "o adopter esvaziou de propósito", e
truncar para zero é um jeito real de DESLIGAR roteamento de revisão obrigatória
sem apagar o path. Tamanho, portanto, não decide. **Proveniência decide:**

`_codeowners_provenance` (`:1945`) responde SIM com **exatamente uma** evidência,
e IMPRIME que foi ela que disparou:

1. o manifesto baseline (`.claude/.install-manifest.sha256`) registra
   `.github/CODEOWNERS` como **entrega** do framework — a linha só existe quando
   um escritor realmente renderizou o arquivo (`_append_delivered_template` →
   `FMS_DELIVERED_TEMPLATES` → manifesto). Medido nas duas direções: 1 linha
   depois de uma entrega real, 0 depois de um EXISTS-skip.

**Um `github_owner` persistido NÃO é evidência, e a segunda perna foi REMOVIDA
no rail round-1** (`install.sh:1914` guarda a nota; a leitora
`_read_target_install_state_github_owner` foi APAGADA em vez de deixada como
código morto, porque código morto ali é convite para religá-la). O handle
registrado prova um PEDIDO, não autoria, e as duas coisas se separam num caso
ordinário — REPRODUZIDO: o adopter tem o seu CODEOWNERS não-vazio, roda o
installer com `--github-owner`, o arquivo é PULADO (bytes dele preservados,
corretamente) mas o owner é persistido; depois ele esvazia o arquivo de
propósito — que é como se desliga roteamento de revisão sem apagar o path — e o
install seguinte lia o owner como prova de autoria e re-renderizava 1409 bytes
de template por cima, re-ligando revisão obrigatória num repositório que este
framework nunca escreveu. Perguntar "nós PEDIMOS isto?" em vez de "nós
ESCREVEMOS isto?" reintroduz a classe D4 uma pergunta antes. Fixado pela perna
**F2.8** do e2e ("a recorded owner is NOT a delivery record"). O handle continua
validado onde é de fato necessário: no parse, antes do render e antes de
persistir.

Com prova ⇒ re-render RUIDOSO (`RECOVERED:` nomeando a evidência +
`_state_record_op` + `_append_delivered_template`). Sem prova ⇒ `WARNING`
nomeado que aponta `scripts/doctor.sh` e a edição manual, e **o arquivo não é
tocado**. Reescrever sem prova é re-ligar donos num repositório de terceiro —
a classe D4 do PLAN-183, que já custou uma sessão.

---

## 6. Testes e resultados

Instrumento: `scripts/tests/test-installer-write-safety-e2e.sh` — uma seção **F0**
de unidade sobre o predicado (uma perna por FORMA recusada, cada uma com
controle de REMOÇÃO DE CLÁUSULA) mais 19 fixtures e2e; **80 asserções** no total
(63 antes das curas do rail round-1, §12). Toda asserção F1 é sobre o **caminho
EXTERNO** — nunca só sobre o exit code, porque o defeito pré-cura sai `0`.

| Comando | Resultado |
|---|---|
| `bash scripts/tests/test-installer-write-safety-e2e.sh` (sombra curada) | **105 passed / 0 failed, rc 0** |
| idem contra a árvore PRÉ-CURA do MESMO commit (controle positivo) | **40 passed / 62 failed, rc 1** |
| `python3 -m pytest .claude/scripts/tests/test_check_installer_write_safety.py` (sombra) | **111 passed** |
| `bash -n` nos 3 scripts + no teste | OK |
| `shellcheck -S warning` nos 3 scripts + no teste | limpo |
| smoke do upgrade (conversão a consumidor) | **7/7** |
| sonda das 3 falhas do rail (`rail-probe.sh`), antes → depois | 3 reproduzidas → 3 curadas |

**Os controles de cláusula (F0) acharam coisa.** A perna do relpath que escapa
(`../escape.md`) continuou sendo recusada **depois** de a cláusula léxica ser
removida da cópia mutada — porque a contenção FÍSICA a pega independentemente.
A asserção original ("removida a cláusula, deixa de recusar") era, portanto,
falsa por um bom motivo, e exigi-la seria exigir que a guarda **não** tivesse
profundidade. O controle passou a assertar sobre o MOTIVO: removida a cláusula,
aquele motivo específico some — o que é a afirmação estreita e verdadeira de
que *esta linha é a que produz esta recusa*. Duas pernas relatam isso
distintamente ("some por completo" vs "uma parede mais funda ainda recusa").

Duas armadilhas de harness fechadas no mesmo passo, porque as duas leriam VERDE
por ausência: o mutante é verificado com `cmp` (mudou mesmo?) e `bash -n` (ainda
carrega?), senão "não recusa mais" teria explicação em erro de sintaxe; e o F0
agora exige que `_wbm_dst_refuses` **exista** na biblioteca sob teste — sem essa
perna, uma biblioteca que nunca define o predicado faz todo "não recusou" passar
por aceitação (é a falha nº 1 do controle positivo, e ela aparece nomeada lá).

**O controle positivo NOMEIA o defeito**, com bytes:

```
FAIL F1.1 — 536 bytes were written OUTSIDE the target at .../f1-dangling/outside/pwned.md
FAIL F1.3 — 8468 bytes were written OUTSIDE the target at .../outside/docs-real/BRANCH-PROTECTION.md
FAIL F1.6 — 454 bytes were written OUTSIDE the target at .../outside/protocol-escape.md
FAIL F1.7 — 48708 bytes were written OUTSIDE the target at .../outside/settings-escape.json
FAIL F1.5 — the FIRST destination was written before the group was refused
FAIL F2.1 — .github/CODEOWNERS was created (0 bytes)
FAIL F2.2 — accepted (rc=0) or wrote CODEOWNERS: leading-hyphen | forty-chars | embedded-space | ampersand | backslash
```

Como reproduzir o controle (a receita está no cabeçalho do próprio teste):

```bash
CTRL="$(mktemp -d)"; git -C <sombra> archive HEAD | tar -x -C "$CTRL"
cp scripts/tests/test-installer-write-safety-e2e.sh "$CTRL/scripts/tests/"
bash "$CTRL/scripts/tests/test-installer-write-safety-e2e.sh" "$CTRL"   # rc 1
```

### Não-regressão, medida (não afirmada)

Install a partir da árvore PRÉ-CURA e da CURADA **no MESMO path de destino** (o
mesmo path é obrigatório: o installer substitui `{{PROJECT_PATH}}` e
`{{PROJECT_NAME}}` em `CLAUDE.md`, `PROTOCOL.md`, `team.md` e ~30 `SKILL.md`, então
alvos com nomes diferentes divergem por desenho):

* **566 arquivos comparados por sha256 — idênticos**, exceto `PROTOCOL.md` e o
  `.install-manifest.sha256` que o hasheia. O diff de `PROTOCOL.md` é 100% o
  PATH do checkout do framework embutido no ponteiro (as duas árvores vivem em
  paths diferentes por construção), verificável linha a linha.
* **Modos: idênticos em 567 arquivos.** Medido separadamente porque `sha256` não
  vê modo, e esta wave reescreve o caminho de escrita estagiada.
* `.install-state.json` excluído: carrega `written_at`/`first_recorded_at` de
  relógio de parede, logo nunca é byte-idêntico entre duas runs.

### Dry-run (W1 `[P2]`)

Pré-cura, sobre um link pendente: `rc 0` e `(dry-run) would COPY:` — o preview
MENTIA, e é com ele que o adopter decide. Curado: `REFUSED (nothing written)` +
`PRE-FLIGHT` + `rc 1`, sem criar nada.

---

## 7. Censo — e por que os números NÃO mostram a cura

**Aviso de método:** o instrumento estava sendo REESCRITO no repositório vivo
durante esta unidade (a unidade U1.1 da mesma noite; `mtime` mudou entre duas
leituras minhas, e o mesmo `scripts/` byte-idêntico devolveu 341 e depois 832
sítios). Os números abaixo foram tomados com uma **cópia congelada**,
`sha256=283a77f9e2e0bd028767134b51b6f0519feeec276d8c2b17766fd218c6025b3b`, nas
duas árvores em sequência imediata. Qualquer número de censo publicado sem o
sha do instrumento hoje não é reprodutível.

| arquivo | veredito | PRÉ | PÓS |
|---|---|---:|---:|
| `install.sh` | desguardado | 47 | **44** |
| `install.sh` | indeterminado | 86 | **115** |
| `install.sh` | guardado | 5 | 5 |
| `upgrade.sh` | desguardado | 56 | 56 |
| `_framework_manifest_set.sh` | indeterminado | 14 | 23 |

**O censo não enxerga o predicado compartilhado, e isso é estrutural.** As formas
provadas seguras do instrumento (`--rules`) exigem, para a família symlink:

* `a1` — um teste `-L` **no mesmo path**, dominando a escrita; ou
* `a2` — um helper **DEFINIDO NO MESMO ARQUIVO** cujo corpo satisfaz `a1` para
  `$1` e cujo ramo de symlink retorna literal NÃO-ZERO, chamado como
  `helper <path> || <abort>`.

A cura viola `a2` em duas dimensões, **as duas por decisão do plano**: o corpo
com o `-L` vive em OUTRO arquivo (W1 `[P0]`: "a função vive em
`scripts/_framework_manifest_set.sh`" — pôr no `install.sh` fecharia a porta
para `upgrade.sh` e `doctor.sh` e recriaria a classe das cópias divergentes), e
a polaridade é de RECUSA (`rc 0 = recusar`), não `|| abort`.

Reformar a cura para caber no instrumento seria deixar o instrumento ditar a
arquitetura — exatamente o inverso da ordem certa. **A cura é o fato; o
instrumento é que precisa aprender a forma.** Ver follow-up FU-1.

Consequência direta e declarada: **AC-3 como está escrito ("zero sítios
BLOQUEANTES de classe A em `install.sh` e `upgrade.sh` — 19 → 0") NÃO é
satisfeito por este pacote**, e não por falta de cura. Ver OQ-6.

---

## 8. Residuais declarados

1. **TOCTOU.** Entre o predicado e a escrita nada impede o destino de VIRAR
   symlink. Bash não oferece `openat`/`O_NOFOLLOW`; a janela é irredutível. A
   guarda **estreita** a janela, não a fecha. O cenário onde isso importa é o
   mesmo do §5 do plano: alvo compartilhado ou clone de terceiro.
2. **`install_one` continua PULANDO** (não recusando) por decisão do plano — os
   testes atuais fixam esse comportamento. O predicado é consultado, a política é
   a antiga, deliberadamente.
3. **`install_mcp_secrets_dir` (`:2275` pré-cura, `chmod` sobre `$secrets_dir`)
   NÃO foi guardado.** Não está entre os sete escritores que o plano enumera, e
   alargar o conjunto no meio de um pacote assinado é como o Scope estoura.
   Fica registrado como sítio conhecido, não curado.
4. **F1.2 e F1.4 passam a asserção de BYTES já na árvore pré-cura** (o código
   antigo pegava o ramo EXISTS e pulava): nessas duas pernas o vermelho do
   controle vem da asserção de "recusa NOMEADA", não de um escape vivo. Dito
   aqui para que ninguém leia as 62 falhas do controle como 62 escapes — os
   escapes VIVOS medidos são quatro, e vêm com bytes (536, 8468, 454, 48708).
5. **A suíte roda ~7 min** (≈13 installs reais de 27 s). É e2e, não unitário; a
   seção F0 é instantânea e não depende de install.

---

## 9. Follow-ups para quem escreve CI/docs (fora do meu FILE ASSIGNMENT)

> **Estado observado ao fechar esta unidade.** Um segundo agente estava
> trabalhando na MESMA sombra e já havia tocado
> `.github/workflows/{validate,smoke-install}.yml`, `docs/threat-model.md`,
> `.claude/adr/ADR-196-installer-write-confinement.md` e as superfícies
> derivadas (`CHANGELOG.md`, `README*`, `docs/*`), além de ter feito `git add`
> dos meus três scripts. Meu conteúdo está intacto (diff staged = 674 inserções
> / 40 remoções, sem drift entre worktree e index). Portanto **FU-2, FU-3, FU-5
> e FU-6 abaixo podem já estar cumpridos** — conferir o patch final antes de
> refazer. FU-1, FU-4 e FU-7 eu não vi ninguém pegar.

* **FU-1 `.claude/scripts/check-installer-write-safety.py` — forma nova.**
  Adicionar ao allowlist uma forma `a4-confinement-predicate-dominates`: chamada
  dominante a um predicado de confinamento **de outro arquivo do mesmo repo**,
  cujo corpo satisfaz `a1` para o par `(raiz, relpath)` e cuja polaridade é de
  RECUSA. O instrumento tem de INSPECIONAR o corpo de `_wbm_dst_refuses` — o
  NOME nunca é evidência, doutrina do próprio instrumento. Sem isso os sete
  escritores curados seguem contados como `desguardado`/`indeterminado`.
  Coordenar com a unidade U1.1, que está reescrevendo o arquivo esta noite.
* **FU-2 `.github/workflows/smoke-install.yml`** — o e2e novo entra nas **DUAS**
  listas `paths:` (`:5` e `:108`, que o arquivo manda manter idênticas) **e**
  ganha step invocador **e** controle NEGATIVO (renomear o e2e ⇒ o step falha
  por arquivo ausente, nunca passa calado). AC-3 Check (d).
* **FU-3 `.github/workflows/validate.yml`** — a linha do censo (o `validate.yml`
  **não** tem filtro `paths:`, então não há a armadilha de "gate que a mudança
  não dispara"). Polaridade conforme OQ-3: per-PR bloqueia só desguardado NOVO
  (delta contra baseline) + `exit 2` de contagem-zero; `indeterminado` é contado,
  IMPRESSO e vira ratchet no `ownership-nightly.yml`.
* **FU-4 shellcheck não cobre `scripts/`.** O step do `validate.yml` (`:306-324`)
  varre só `.claude/scripts` e `.claude/hooks`. Rodei `shellcheck -S warning`
  à mão nos três (limpo), mas o CI não o faria. Estender o `find` é uma linha, e
  a sombra prova que o corpus passa hoje.
* **FU-5 `docs/threat-model.md`** — a superfície de escrita de destino do
  installer não está no contrato (hoje só T-004, extração de tarball). W3 do
  plano. **Aviso operacional:** `check-threat-model-freshness.py` REESCREVE esse
  arquivo (`accepted → stale`) e derruba o P0 de qualquer SIGN — reverter esse
  flip entra no roteiro do pacote.
* **FU-6 ADR-196** — registrar "predicado na biblioteca, política no chamador",
  com os três consumidores previstos (`install.sh`, `upgrade.sh`, `doctor.sh`).
  W3 `[P1]`.
* **FU-7 `scripts/doctor.sh`** é o terceiro consumidor previsto e **não** foi
  convertido (fora do meu escopo). Enquanto não for, a classe segue aberta lá.

---

## 10. OQs

Decididas pelo **default conservador** do plano §6, todas implementadas:

| OQ | Default aplicado |
|---|---|
| OQ-1 | recuperar 0 byte **só com evidência**; ruidoso com prova, `WARNING` nomeado sem prova |
| OQ-2 | gramática estreita; `org/team` recusado **com a mensagem explicando** |
| OQ-3 | (é de CI — implementado como FU-3, não no código) |
| OQ-4 | **pré-voo**, sem mexer na semântica de rollback |
| OQ-5 | **SIM**, `upgrade.sh` convertido a consumidor no MESMO patch |

**NOVA — OQ-6, para o Owner (não tem resposta na noite).**
AC-3 exige "zero sítios BLOQUEANTES de classe A em `install.sh` e `upgrade.sh`
— 19 → 0", número derivado do baseline de 27 entradas da S326. A 4ª passada
INVERTIDA mudou a régua: com o instrumento congelado deste pacote, `install.sh`
sozinho tem 47 `desguardado` PRÉ-cura e `upgrade.sh` 56, e a cura os leva a 44 e
56 — porque o instrumento **não reconhece** a forma que o próprio plano mandou
construir (§7). As opções, e nenhuma é minha para escolher:

* **(a)** FU-1 primeiro (ensinar a forma ao censo), medir de novo, e só então
  julgar o AC-3 — é a que preserva o AC como critério;
* **(b)** re-escrever o AC-3 sobre o teste de FORMA da W1 `[P1]` (que o plano já
  chama de "o que fecha a classe") e rebaixar a contagem a evidência secundária,
  que é o que o próprio AC-3 Check (c) diz;
* **(c)** alargar a wave até `upgrade.sh` e `doctor.sh` inteiros — cresce o Scope
  assinado e reabre a janela que o pacote fecha.

Recomendação do implementador: **(a) seguida de (b)** — FU-1 é pequeno e
coordenável com U1.1 ainda esta noite; (b) alinha o AC com o que o plano já diz
em duas frases sobre contagem ser evidência secundária.

---

## 11. CI / docs / ADR (S329)

Metade de CI/docs do pacote C, cobrindo FU-2, FU-3, FU-5 e FU-6 da §9. Nada de
`scripts/**` foi tocado — a metade de código continua sendo a das §§1–8.

### 11.1 Wiring — o que entrou, e onde

**`.github/workflows/smoke-install.yml`** (FU-2, AC-3 Check (d)):

| Linha | O que |
|---|---|
| `:54` | `scripts/tests/test-installer-write-safety-e2e.sh` na lista `paths:` do `pull_request` |
| `:136` | o MESMO path na lista do `push`, no mesmo lugar relativo — o arquivo manda mantê-las idênticas, e agora dá para conferir por leitura |
| `:254` | `timeout-minutes` **68 → 78** |
| `:611` | step `Installer write-confinement e2e (F1 symlink/hardlink, F2 CODEOWNERS)` |

O step segue a forma dos vizinhos — `if: always()` pela razão do PLAN-183 §9.8
(oráculo de segurança não pode reportar `skipped` porque algo antes ficou
vermelho), que **sete** steps deste job já carregam, contados por parse;
`set -euo pipefail`; sem `continue-on-error` — e carrega o
**controle NEGATIVO** que o consenso C12 exige: o path é provado presente com
`[[ -f ]]` e a ausência sai `::error::` nomeado + `exit 1`. Renomear ou remover
o e2e é exatamente o drift que o step existe para pegar; um step que passa
porque não rodou nada é a classe "red gate nobody runs", a sexta instância neste
arquivo.

As duas listas ficaram com **37 entradas cada e conjuntos idênticos** (verificado
por parse YAML, não por leitura). Os três canônicos que o e2e exercita
(`install.sh`, `upgrade.sh`, `_framework_manifest_set.sh`) já estavam nas duas.

**A bump de timeout é MEDIDA, não aritmética** — e corrige a §8 residual 5 deste
próprio documento ("a suíte roda ~7 min"): não reproduz. Medido hoje na sombra
curada, **duas vezes**, porque a primeira run não é um p50 e dizer isso vale mais
que um número redondo:

```
run 1  passed 62 / failed 0 / rc 0    2m49.10s wall   87% CPU
run 2  passed 63 / failed 0 / rc 0    4m42.16s wall   55% CPU
       sha256=83e8ed3cd0ffa4ebe8ec5fea2a4c4c2e24e4378f853d9c19e3bfce2a0e37fbc7
```

Mesma suíte, **spread de 1,7×**: é a máquina, não o teste — as duas runs tiveram
outra pista da night-run fazendo installs em paralelo, e a queda de 87% para 55%
de CPU é a contenção aparecendo. Dimensionei pelo limite SUPERIOR: 282 s × o
fator 2–3× de runner com que este arquivo já se dimensiona = 9–14 min de CI
novos ⇒ **+15** (68 → 83) com a margem anti-flake que a doutrina do arquivo pede
(um timeout que corta uma run VERDE aparece como `cancelled` num passo inocente).

> **Aviso de método, o mesmo da §7 e agora aplicado a mim.** O e2e foi
> REESCRITO durante esta unidade: a run 1 pegou a versão de 31.898 bytes (62
> asserções) e a run 2 a de 32.509 bytes (63, com a seção F0 que a §6 agora
> descreve). Por isso o sha do arquivo sob teste está publicado acima. Qualquer
> número de wall time desta suíte sem o sha do arquivo não é reprodutível.

**`.github/workflows/validate.yml`** (FU-3): step
`Run check-installer-write-safety.py (PLAN-185 W0)` em `:327-368` (nome em
`:365`), logo depois do
`Shellcheck hooks and scripts` — o vizinho certo, porque é a mesma pergunta sobre
o mesmo corpus, na classe que o shellcheck não enxerga. `validate.yml` **não tem
filtro `paths:`** (confirmado por parse, não por leitura), então não há a
armadilha do "gate que a mudança não dispara". Fail-closed nos dois códigos, sem
`|| true` e sem `continue-on-error`. Nada mais no arquivo foi tocado.

> **Ratchet, não `--strict` — e o número que a §7 publica já envelheceu.**
> O gate bloqueante é a invocação nua. Medido hoje contra a árvore viva com o
> instrumento `sha256=25d6dcf396ac8c98961f362bae56463600cca359635f2803d834cea3a2c539f3`:
> ratchet `rc 0`, `--strict` `rc 1` sobre **424 indeterminados** — não os 76
> que a §7 e a OQ-1 citam. Os 76 são de uma GERAÇÃO ANTERIOR do instrumento,
> que foi reescrito esta noite pela U1.1; a mesma árvore responde números
> diferentes conforme a passada. Um gate `--strict` nasceria vermelho e nada
> mergearia — o anti-padrão que este wiring existe para evitar. O comentário do
> step publica o 424 COM o sha e a data, e diz explicitamente que o número se
> move com o instrumento. **OQ-1 do censo continua do Owner.**

**Step ADVISORY do `--strict`** (`validate.yml:380-389`), logo depois do gate:
`continue-on-error: true`, rotulado `--strict (advisory, OQ-1)`. Existe porque o
ratchet é cego a UMA coisa por desenho — o baseline isenta `indeterminado`, logo
esse conjunto pode CRESCER sem deixar nada vermelho. O step é o extrato dessa
dívida, visível por PR enquanto a OQ-1 estiver aberta.

Duas decisões de forma, as duas com lição do repo por trás:

* **Saída LIMITADA.** `--strict` lista os 424 sítios; um muro de 424 linhas por
  PR é output que ninguém lê. O step imprime a linha de sumário
  (`--strict: NNN indeterminate site(s) block:`) mais 15 linhas de cauda, lidas
  de um ARQUIVO — nunca `| head` a partir do produtor, que sob `pipefail` mata o
  produtor com SIGPIPE.
* **O rc é capturado na hora** (`cmd > log; RC=$?`), nunca `cmd || true`, que
  reportaria sucesso para qualquer desfecho — é a lição "o ÚLTIMO comando
  determina o exit". Executei o bloco verbatim: imprime `rc=1`, a linha de
  sumário e a cauda, e o shell do step sai **0**.

**O teste unitário do instrumento não precisa de step próprio:** o passo
`Run Python script unit tests` (`validate.yml:469`) roda
`python3 -m pytest .claude/scripts/tests/ …` — o diretório INTEIRO. O teste está
ligado por pertencimento ao diretório, e um step extra seria execução dupla — o
que o próprio arquivo já manda evitar em `:291-295` ("is ALREADY collected by
'Run Python script unit tests' below … do NOT re-list them as paths"). Verificado
lendo o passo, não presumido.

**E é justamente por já estar ligado que ele importa aqui:** esse step é o
SEGUNDO dos três que o patch de C deixa vermelhos até o baseline e as asserções
de `TestLiveCorpus` serem re-apontados. Medido no alvo de merge — ver §11.6.

### 11.1-bis Proveniência: alinhado a REGISTRO DE ENTREGA (rail r2, P2)

O rail r2 achou que o ADR-196 §6 descrevia uma segunda evidência — um
`github_owner` persistido — que o código **não** implementa. Verifiquei no
disco antes de editar, e o achado está certo e é mais estreito do que parecia:
`_codeowners_provenance` (`install.sh:1945`) tem **uma** perna, o registro de
entrega no manifesto, e a leitora do install-state foi **APAGADA** no rail r1
(nota em `install.sh:1914`) em vez de deixada como código morto. A perna F2.8 do
e2e prende o caso ("a recorded owner is NOT a delivery record").

Três superfícies alinhadas para «delivery-record-only»: **ADR-196 §6** (Decision
item 6), **DESIGN-C §5** (que ainda listava as duas evidências e apontava o
anchor velho `:1877`) e o item **T-008** do threat-model. O texto novo diz por
que a segunda perna é errada, não só que ela saiu: owner registrado prova um
PEDIDO, e a diferença aparece num caso ordinário — CODEOWNERS do adopter
EXISTS-skipado, owner persistido de todo jeito, arquivo esvaziado de propósito
depois; ler o owner como autoria re-liga revisão obrigatória num repositório que
o framework nunca escreveu.

### 11.2 ADR-196 (FU-6)

`.claude/adr/ADR-196-installer-write-confinement.md`, 166 linhas, `status:
PROPOSED` com `decided_by: Owner (PENDENTE)` — a assinatura GPG do sentinel É a
ratificação, e o flip textual para `ACCEPTED` chega por cerimônia própria,
exatamente como o ADR-194 registrou. Forma copiada do ADR-194 (H2 em inglês,
corpo em PT-BR): Context / Options considered / Decision / Consequences / Blast
radius / Verification / References.

A decisão registrada é **"predicado na biblioteca, política no chamador"**, com
os três consumidores previstos (`install.sh` e `upgrade.sh` convertidos,
`doctor.sh` **não** — declarado no Blast radius para que ninguém leia o ADR como
"fechado em todo lugar"). Contrato do predicado, gramática, escrita atômica e a
regra de evidência vêm das §§2–5 acima; os residuais (TOCTOU irredutível,
`install_one` que pula, `install_mcp_secrets_dir`) vêm da §8.

Todas as âncoras de linha citadas foram **re-verificadas contra a árvore curada**
antes de entrar no texto (`grep -n` por definição de função), porque âncoras
mortas foram o achado C1 do consenso e já custaram uma rodada.

### 11.3 `docs/threat-model.md` (FU-5)

Cenário **T-008** em `:713`, na secção Tampering, na forma exata dos sete
vizinhos (`Vector` / `Evidence` / `Mitigations` / `Residual risk` / `Test`).
Cobre as seis formas da superfície: componente symlink, link PENDENTE, hard
link, escape por `..`/absoluto, valor de flag não validado interpolado num
programa editor, e escrita parcial no abort. Controle = ADR-196; residual =
TOCTOU, mais os três sítios não cobertos. Contadores acompanhados:
`### Tampering (7 → 8)` e `## STRIDE scenarios (33 → 34 total)`. Antes de mexer,
`grep -rn "33 total"` no repo devolvia **1 ocorrência** — a própria linha — então
o total não é afirmado em nenhum outro documento. O teste de integração usa piso
(`>= 33`), não igualdade, logo acrescentar cenário é seguro por construção.

**Freshness — o que fiz e por quê.** `check-threat-model-freshness.py` **reescreve
o arquivo** (`accepted → stale`) e derruba o P0 de qualquer SIGN. Medido hoje:

| Invocação | Resultado |
|---|---|
| `--dry-run --verbose` na sombra | `rc 1`, "196 new ADR(s) since 2026-06-12" |
| `--dry-run --verbose` no checkout vivo | `rc 1`, **195** — o +1 da sombra é o ADR-196 untracked, que o script conta como novo pela sua própria regra conservadora |
| execução NUA na sombra (para provar o efeito) | `rc 1`, `STATUS FLIPPED: accepted -> stale`, 1 linha alterada |
| reversão da linha e `shasum -a 256` | **byte-idêntico ao estado anterior** |

**Não movi `Last updated`.** Mover silenciaria o script, mas seria a afirmação de
que 196 ADRs foram re-revisados — que não aconteceu. O próprio cabeçalho já
recusou esse atalho em 2026-08-18 (PLAN-179 W4) e a razão não mudou; `stale`
ainda reprova `tests/integration/test_threat_model_coverage.py::test_status_is_accepted`.
Segui o precedente ao pé da letra: `Status: accepted`, e o que FOI revisado está
declarado com escopo (a superfície de escrita de destino ⇒ T-008).

**Achado colateral que muda o follow-up nomeado do cabeçalho:** a lista do script
começa em `ADR-001`, um registro de 2026-04. Ele data cada ADR por
`git log --diff-filter=A --follow`, isto é, pelo último commit que ADICIONOU
aquele path — então um move de diretório re-data o corpus inteiro. O número não é
"N ADRs sem revisão", é um **censo datado por rename**. Está escrito no cabeçalho:
consertar a regra de datação vem ANTES de alguém re-revisar 196 registros.

**Nenhum workflow invoca o script** (`grep -rl` em `.github/`, `.claude/scripts/`,
`.claude/hooks/`, `Makefile` ⇒ só o próprio script, o teste dele, o CODEOWNERS e
um comentário no `audit_emit.py`). Logo este wiring **não** cria gate vermelho por
essa via; a exposição é só a preflight da cerimônia, e o cabeçalho agora manda
usar `--dry-run` ou reverter o flip.

### 11.4 Contagens

`verify-counts.sh` nomeou 15 sítios de `adrs=196, live=197` em 9 arquivos. Apliquei
196 → 197 em **16 sítios / 10 arquivos** — os 15 nomeados mais dois que ele NÃO
nomeia mas que afirmam o mesmo número:

* `docs/ARCHITECTURE.md:56` (a legenda da árvore, `# 196 architecture decision
  records`; o gate só vigia a linha 71 da tabela) — corrigir a tabela e deixar a
  legenda produz documento auto-contraditório;
* `CLAUDE.md:54` (`**196 ADRs**`) — fora do escopo do `verify-counts`, mas dentro
  do do `validate-governance.sh`, que agora diz `OK: CLAUDE.md prose counts match
  disk (ADRs=197 …)`.

Nenhuma outra linha desses arquivos foi tocada. A troca foi feita com anchor por
linha E conteúdo esperado, abortando se a linha não casasse ou tivesse mais de
uma ocorrência do número.

`CLAUDE.md` = **37.485 bytes**, dentro do limite de 40.000 (a lição S327 #4: o
`--fast` não checa o limite, então rodei o governance COMPLETO).

### 11.5 Gates — todos rodados DEPOIS da última edição

| Gate | Resultado |
|---|---|
| `bash .claude/scripts/local/verify-counts.sh` | **rc 0** — "no drift detected" (antes: rc 1, 15 drifts) |
| `python3 .claude/scripts/check-claude-md-claims.py` | **rc 0** |
| `bash .claude/scripts/validate-governance.sh --fast` | **rc 0** — PASS, 0 erros, 0 warnings |
| `bash .claude/scripts/validate-governance.sh` (completo) | **rc 0** — PASS, 0 erros, 65 warnings (baseline pré-existente; nenhum nomeia arquivo meu) |
| `python3 .claude/scripts/check-staleness.py` | **rc 0** (achados advisory sobre PLAN-176/181, pré-existentes) |
| `python3 -m pytest tests/integration/test_threat_model_coverage.py` | **22 passed** — inclui `test_all_file_references_resolve` e `test_status_is_accepted` |
| `python3 .claude/scripts/check-test-env-hygiene.py` | **rc 0** — "337 flagged files, all allowlisted" |
| `actionlint` nos dois workflows | **limpo** |
| parse YAML dos dois workflows | OK; `paths:` 37/37 com conjuntos idênticos; `validate.yml` sem filtro `paths:`; 8 steps com `if: always()` |
| `bash scripts/tests/test-installer-write-safety-e2e.sh` | **105 passed / 0 failed, rc 0** — 63 antes do rail r1 (§12), 80 depois dele, 98 depois do r2 (§13), 105 depois do r4 (§14); ver §11.1 para as duas runs e o sha |
| controle NEGATIVO do step, as duas pernas | arquivo ausente ⇒ **rc 1** + `::error::` nomeado; arquivo presente ⇒ **rc 0** e o teste roda. Executado com a lógica EXATA do step numa árvore isolada, não afirmado |
| gate do censo, ratchet (a invocação que o step roda) | **rc 0** na árvore viva |
| step advisory `--strict`, bloco executado verbatim | imprime `rc=1` + `--strict: 424 indeterminate site(s) block:` + 15 linhas de cauda; **o shell do step sai 0** |
| **no alvo de merge** (`git clone --local` de `8dde6f7` + `git apply` do patch) | patch **aplica limpo**; o instrumento **existe**; censo **rc 1**; suíte do instrumento **3 failed / 108 passed** — contra **rc 0 / 111 passed** no main sem o patch (controle). Ver §11.6 |

### 11.6 Bloqueantes para a montagem do pacote — os dois são MEDIDOS

Os dois foram re-medidos **no alvo de merge REAL**, não na sombra. Método
(reprodutível): `git -C <sombra> diff HEAD > C.patch`, `git clone --local` do
checkout vivo (HEAD `8dde6f7`), `git apply` do patch, e então os comandos EXATOS
dos steps. Isto responde a pergunta que a sombra não pode responder, porque ela
bifurcou em `f569c9a` — antes de o bundle do censo existir.

**B2 — RESOLVIDO, e o step fica INCONDICIONAL.** O instrumento, o baseline e o
teste dele estão em `main`, commitados em **`7383518`** (PLAN-185 W0, 5ª passada)
e presentes em `8dde6f7` como arquivos RASTREADOS. Medido no clone re-baseado:
`git apply --check` **aplica limpo**, e o arquivo que o step invoca **existe**. O
"can't open file" é artefato do ponto de fork da sombra, não do wiring: o patch
de C **não deve** carregar o bundle, e não carrega.

Considerei e **REJEITEI** a rota defensiva (`if [ -f … ]; then …; else notice`):
ela transforma um gate BLOQUEANTE num que reporta sucesso quando não rodou nada
— exatamente a classe que o controle negativo do `smoke-install.yml` existe para
impedir, na mesma unidade. Se o instrumento faltar, VERMELHO é a resposta certa:
significa que o bundle não landou. A razão está no comentário do step, para que a
próxima rodada de rail não a re-levante.

**Os três arquivos, portanto, NÃO entram no Scope de C** — já estão no main. Isso
ENCOLHE o Scope assinado em relação ao que o consenso C11 previa.

**B1 — CONFIRMADO no alvo de merge, e é maior do que eu media: TRÊS checks ficam
vermelhos.** Com o patch aplicado sobre `8dde6f7`:

| Check | Sem o patch (controle) | Com o patch |
|---|---|---|
| censo, ratchet (o step que wirei) | **rc 0** | **rc 1** — 15 entradas MORTAS + 45 sítios bloqueantes novos (34 `install.sh`, 8 `_framework_manifest_set.sh`, 3 `upgrade.sh`) |
| `Run Python script unit tests` (step JÁ existente) | **111 passed** | **3 failed / 108 passed** |

As três falhas são todas de `TestLiveCorpus`, e todas encodam fatos PRÉ-cura:

```
TestLiveCorpus::test_census_is_green_against_the_tracked_baseline
TestLiveCorpus::test_every_blocking_site_is_in_the_tracked_baseline
TestLiveCorpus::test_f2_the_reported_sed_site_is_unguarded
```

As duas primeiras são a mesma raiz do baseline. **A terceira é de outra natureza
e é a mais interessante: ela assere que o sítio da F2 ESTÁ desguardado** — um
teste cuja verdade é a EXISTÊNCIA do defeito. Curar o defeito TEM de inverter
essa asserção no mesmo commit, ou o pacote entrega uma cura e um teste que exige
o defeito de volta.

Logo o pacote C precisa, no MESMO commit e em arquivos que **não estão no meu
FILE ASSIGNMENT** (`.claude/scripts/**`, unidade U1.1):

1. **regenerar o baseline** (`--write-baseline`, invocação EXPLÍCITA) sobre a
   árvore curada — as 15 entradas mortas são a prova mecânica de que a cura
   funcionou (a §7 já dizia que "remover uma linha é como uma cura é
   registrada"), e os 45 novos são os helpers da própria cura, que o instrumento
   ainda não reconhece (§7 + FU-1);
2. **re-apontar as três asserções de `TestLiveCorpus`** — em especial a F2, que
   precisa passar a asserir que o sítio está GUARDADO.

Nada disso é defeito do wiring: é a consequência mecânica, agora MEDIDA, de curar
o corpus que o instrumento descreve.

### 11.7 OQs e o que deliberadamente NÃO fiz

* **OQ-7 — FECHADA na sessão.** O ratchet é o gate; o `--strict` entrou como
  step ADVISORY separado, `continue-on-error: true`. Decisão do CEO, alinhada
  com a §7 e com a medição. O que continua aberto é a OQ-1 do censo: QUANDO (e
  se) o `--strict` vira gate — e a resposta depende de a triagem reduzir os 424,
  não de trocar uma flag.
* **OQ-9 (nova) — a §7 e a OQ-1 do censo citam 76 indeterminados; hoje são 424.**
  Não é regressão: o instrumento foi reescrito esta noite (U1.1) e a régua mudou
  com ele. Mas os dois documentos ficam com um número que não reproduz, e a OQ-1
  é decidida sobre esse número. Ou a §7 é re-medida antes de o Owner decidir, ou
  a OQ-1 passa a citar "o conjunto que o instrumento da versão X reporta". O
  número no comentário do `validate.yml` já vai com sha e data, exatamente para
  não repetir o problema.
* **OQ-8 (nova) — o threat-model não cita o instrumento do censo por path.**
  `test_all_file_references_resolve` exige que todo path citado numa linha
  `**Evidence:**`/`**Mitigations:**` EXISTA na árvore, e o instrumento não existe
  nesta sombra. Citei o `validate.yml` (que existe) e descrevi o censo pelo nome.
  Depois de B2 resolvido, acrescentar o path é uma linha — e aí o teste passa a
  vigiá-lo.
* **FU-4 (shellcheck não cobre `scripts/`) NÃO foi feito**, por instrução
  explícita de não mexer em mais nada no `validate.yml`. Continua verdade e
  re-verificado hoje: o `find` do step `Shellcheck hooks and scripts` (`:305`,
  `find` em `:316`) varre só `.claude/scripts` e `.claude/hooks`, então os três
  canônicos desta wave não passam por shellcheck em CI nenhum. É uma linha de
  `find`, e a sombra prova que o corpus passa hoje. Recomendo entrar no MESMO
  pacote, com o Scope já aberto no arquivo.
* **A tabela per-ADR do threat-model não recebeu linha para o ADR-196**, por
  consistência com o ADR-194 e o ADR-195, que também não têm: aquela tabela
  parou nos ADR-0xx e o rodapé dela declara um inventário de 45 slots. Reabri-la
  é wave própria.
* **Aviso de montagem (a lição do pacote D, S329) — verificado hoje, e HOJE está
  limpo.** Enquanto este pacote esperar assinatura, os contadores de doc que
  toquei são hashes de arquivos VIVOS. Medido contra `8dde6f7`:
  `git diff --stat f569c9a..HEAD` sobre os **13** arquivos que eu toco (os dois
  workflows, o threat-model, `CLAUDE.md`, `CHANGELOG.md` e os 8 docs de contagem)
  devolve **VAZIO** — nenhum deles mudou no main desde o fork da sombra, e o main
  segue com **196** ADRs, então o 196 → 197 continua correto no alvo real. Se
  outro pacote landar antes e mexer nesses arquivos, as 16 linhas de contagem têm
  de ser **re-derivadas POR ITEM sobre o vivo novo** antes do SIGN — nunca
  aplicadas como estão, ou o land reverte a linha do outro pacote.

---

## 12. Rail round 1 — achados e curas

O pair-rail (codex, `gpt-5.6-sol`, read-only, xhigh) leu a sombra no estado das
18:34 e devolveu **2 P1 + 1 P2**. Os três eram REAIS e os três foram
REPRODUZIDOS antes de qualquer cura (`scratchpad/rail-probe.sh`) — um relatório
é uma alegação; a medição é o que autoriza mexer.

### P1-1 — a recusa diferida deixava instalação PARCIAL no alvo

**Reproduzido.** Alvo NOVO com `docs/rotation-log.md` symlink pendente: a run
terminava `rc 1`, com a recusa NOMEADA e **zero bytes fora** do alvo — e
**563 arquivos DENTRO dele**, incluindo o ponteiro de protocolo e `.github/`,
**sem manifesto e sem install-state**. O rollback não alcança: `BACKUP_DIR` está
vazio em alvo novo (não havia `.claude` para snapshotar) e, mesmo em alvo
existente, restaura só `.claude`. O adopter ficava com um framework
meio-instalado que nada registra — exatamente o estado parcial que a política
"acumula e falha no fim" existe para evitar, entrando pela porta que essa
política deixou aberta.

**Cura.** `_dst_global_preflight` responde por TODOS os destinos de relpath
conhecido antes da entrega, e o bloco de POLÍTICA (`_dst_refuses` e irmãs) subiu
para logo depois do `trap cleanup_on_failure EXIT` — porque a primeira coisa que
toca o alvo é o `mkdir -p "$TARGET/.claude"`, e um pré-voo depois dele já chega
tarde. Em modo real: lista completa + `exit 1` com o alvo **intocado**. Em
`--dry-run`: aviso nomeado e o preview SEGUE (truncá-lo esconderia justamente o
que o adopter pediu para ver).

**Medido depois:** 563 arquivos → **0**, e `.claude` deixa de ser criado.
Fixture nova **F1.9**, que assere o forte (zero arquivos regulares no alvo,
`.claude` ausente, ponteiro/`.github`/manifesto/install-state ausentes) — porque
"a recusa foi nomeada" já era VERDADE enquanto o adopter recebia meio framework.

### P1-2 — `github_owner` registrado NÃO é prova de entrega

**Reproduzido, e este era o mais sério: eu reintroduzi a classe D4 que o §5
deste documento diz existir para prevenir.** Adopter com `.github/CODEOWNERS`
próprio e não-vazio roda o installer com `--github-owner`: o arquivo é PULADO
(os bytes dele sobrevivem, corretamente) mas o owner é persistido assim mesmo —
ele registra o PEDIDO. O adopter depois esvazia o arquivo de propósito (é assim
que se desliga roteamento de revisão obrigatória sem apagar o path), e o install
seguinte lia o owner persistido como prova de autoria e **re-renderizava 1409
bytes** de template por cima, re-ligando roteamento em silêncio num repositório
que o framework nunca escreveu.

**Cura.** `_codeowners_provenance` aceita **uma única** evidência: o REGISTRO DE
ENTREGA no manifesto baseline (medido: 1 linha após entrega real, 0 após
EXISTS-skip). O leitor `_read_target_install_state_github_owner` foi **REMOVIDO**,
não apenas deixado sem uso — código morto que responde à pergunta errada é
convite a religá-lo. O handle continua validado onde importa: parse, render,
persistência. Fixture nova **F2.8**.

> **Limite honesto do controle de F2.8.** Ela NÃO fica vermelha na árvore
> pré-cura, porque aquela árvore não tem ramo de recuperação nenhum — o
> EXISTS-skip preserva o arquivo por outro motivo. O vermelho de F2.8 foi
> demonstrado contra a implementação INTERMEDIÁRIA (a que o rail pegou), medido
> em 1409 bytes sobrescritos. É guarda de REGRESSÃO da cura, não do defeito
> original, e está dito aqui para que ninguém leia o verde dela como prova de
> algo que ela não mede.

### P2 — o dry-run contra alvo INEXISTENTE regredia

**Reproduzido:** `--dry-run` num alvo que ainda não existe (comportamento
SUPORTADO: prever sem criar) fazia `cd -P` falhar necessariamente, e **12
destinos** saíam "does not resolve" com a run em `rc 1`, tendo previsto nada.

**Cura, com a política dita em voz alta:** raiz AUSENTE não é recusa — nada
existe sob um diretório que não existe, então não há componente a seguir e a
parede léxica já fez o único trabalho disponível. Raiz que é SYMLINK continua
recusa (o link existe, e toda escrita sob ele segue o link), com a pendente
nomeada à parte. **Medido depois:** `rc 0`, 0 recusas, alvo não criado.
Fixtures novas **F3** (alvo ausente ⇒ rc 0 e nada criado; link pendente em
dry-run ⇒ recusa NOMEADA, sem "would COPY").

### Achado colateral, medido e não curado (fica declarado)

`mkdir -p "$TARGET/.claude"` sobre um `.claude` que é **symlink pendente** falha
com `No such file or directory` (macOS), `rc 1`, alvo intocado e nada criado
fora. É fail-CLOSED por semântica do SO, não por guarda nossa, e a mensagem é o
erro cru do `mkdir`, não uma recusa nomeada. Não regride nada e não escapa; está
aqui porque um SO que se comportasse diferente mudaria a conclusão.

---

## 13. Rail round 2 — achados e curas (2 P1)

### R2-A — o pré-voo global ignorava os templates FIXOS de projeto

`CLAUDE.md`, `MEMORY.md` e `.mcp.json` são entregues pelo ÚLTIMO escritor da
run, muito depois de `.claude/`, `docs/` e `.github/` estarem populados; o
pré-voo global da rodada 1 listava só os grupos anteriores. **Reproduzido** com
`CLAUDE.md` plantado como symlink pendente num alvo maintainer novo: na árvore
pré-cura (sem cura nenhuma) o framework inteiro foi entregue — 566 arquivos — e
**4504 bytes foram escritos ATRAVÉS do link**. Na árvore da rodada 1 o escape
não acontecia (a guarda por-escritor pega), mas restava a instalação PARCIAL
que o pré-voo existe para impedir, num alvo novo sem `BACKUP_DIR`.

**Cura, na forma que o rail pediu — DERIVAR, não duplicar.** As linhas
`origem|destino` viram DADO em duas listas (`_FIXED_TEMPLATES_ALL_CEREMONIES`
para o par tier-policy, que entra em toda cerimônia por viver dentro de
`.claude/`; `_FIXED_TEMPLATES_MAINTAINER` para os três da raiz), e os DOIS lados
leem as mesmas linhas: o pré-voo pega as metades de DESTINO
(`_fixed_template_dests`), os escritores pegam as linhas inteiras
(`_install_fixed_templates`). Um destino não pode mais estar num lado e faltar
no outro. Medido: `grep` acusa exatamente dois leitores por lista.

Escopo alargado por disciplina de irmãos: o rail nomeou os três da raiz, mas
`install_tier_policy` chama o MESMO escritor com destinos fixos e cai na mesma
classe — guardar um sítio e deixar o irmão aberto é o anti-padrão que este plano
inteiro combate. Fixture **F1.10**; controle positivo vermelho na pré-cura
nomeando os 4504 bytes.

### R2-B — raiz do alvo que é symlink RESOLVIDO

O root era testado com `! -e` primeiro, então só uma raiz PENDENTE chegava ao
`-L`: uma raiz symlink RESOLVIDA respondia `-e` verdadeiro, caía no `cd -P` e
movia a BASE de confinamento para o referente, calada. **Medido:** o install
rodou até o fim e 567 arquivos aterrissaram sob o referente — **zero fora
dele**. Ou seja: contenção NÃO foi violada; o defeito era o comentário afirmar
uma recusa que o código não fazia, e o `install.sh` resolver o alvo com `cd`/
`pwd` sem `-P` (caminho LÓGICO, symlink preservado), o que torna o caso
alcançável em todo install real.

**Cura: recusa NOMEADA com a rota de recuperação embutida.** A mensagem imprime
o referente e diz para re-rodar contra ele. Escolhi recusar em vez de aceitar-e-
avisar porque o gate fica fail-closed e o custo para um diretório de projeto
legitimamente symlinkado é UMA re-execução com o caminho que a própria mensagem
imprime — e `CLAUDE.md` §4 exige justamente que um gate fail-closed tenha rota
de recuperação. `-L` testa só o ÚLTIMO componente, então um caminho que apenas
atravessa um ancestral symlinkado (`/tmp` → `/private/tmp` no macOS) não é
afetado. Fixture **F1.11** + **controle** (diretório real ⇒ instala, com os
cinco templates fixos presentes) — o controle fica VERDE também na árvore
pré-cura, que é o que prova que ele não está só herdando a recusa.

---

## 14. Rail round 4 — achados e curas (2 P1 + 1 P2)

### R4-1 — variável herdada do ambiente virava DELEÇÃO ARBITRÁRIA `[P1]`

Meu próprio defeito, introduzido na rodada 1. O trap de saída roda `rm -f` em
`_STATE_OPS_FILE` e `_ATOMIC_TMP_PENDING` e `rm -rf` em `BACKUP_DIR`. Só o
terceiro era inicializado antes do `trap`: `_ATOMIC_TMP_PENDING` só recebia
valor DENTRO do escritor atômico (que o `--dry-run` nunca chama) e
`_STATE_OPS_FILE` dez linhas ABAIXO do `trap`. Qualquer uma exportada pelo
chamador era um caminho arbitrário que o trap apagava em qualquer saída.

**Reproduzido:**

```
env _ATOMIC_TMP_PENDING=<arquivo-qualquer> install.sh <alvo> --dry-run
  => rc 0, e o arquivo-qualquer SUMIU
```

`rc 0`, com a promessa de "nenhum arquivo modificado" no rótulo. **Cura:**
`_ATOMIC_TMP_PENDING=""` e `_STATE_OPS_FILE=""` explicitamente ANTES de
registrar o trap. Escopo alargado outra vez por disciplina de irmãos: o rail
nomeou uma variável, o censo do trap achou duas. Mesma classe que o arquivo já
documentava para `_DELIVERED_TEMPLATES` (`:841`) — uma variável que o script só
ESCREVE ainda é uma variável que o ambiente pode semear. Fixture **F4.1**, duas
pernas, asserção nos BYTES da vítima.

### R4-2 — o teste vivo exigia o sítio F2 DESGUARDADO `[P1]`

`TestLiveCorpus::test_f2_the_reported_sed_site_is_unguarded` exigia um sítio
`sed-interp` desguardado em `install_github_templates`. A cura da W2 não
escapou o `sed` — ela o REMOVEU —, então o teste falharia em todo run de CI
depois do land. **Medido na sombra antes da cura: 1 failed, 7 passed.**

**Cura:** a asserção INVERTE (nenhum sítio `sed-interp` desguardado pode restar)
**mais um controle** que exige que o censo ainda DESCUBRA a função — sem essa
segunda perna, "nenhum sítio desguardado aqui" é satisfeito igualmente por um
matcher que parou de enxergar `install_github_templates`, que é o verde-por-
cegueira que este censo existe para recusar. Medido: a função segue com 10
sítios descobertos, 0 deles `sed-interp`.

Renomeei o método para `test_f2_the_reported_sed_site_is_cured` — um teste cujo
NOME afirma o contrário da sua asserção é uma armadilha para o próximo leitor, e
o nome não é referenciado por nenhum seletor de CI (verificado nos dois repos).

**Prova de acoplamento patch↔teste, nas DUAS direções:**

| | corpus pré-patch | corpus curado |
|---|---|---|
| asserção ANTIGA | passa | **falha** (medido: 1 failed / 7 passed) |
| asserção NOVA | **falha** (medido: rc 1, `AssertionError: [] != [...]`) | passa (111 passed) |

**Aviso de montagem, importante.** A sombra está na **5ª passada** do censo
(`7383518`) e o repo VIVO já está na **6ª** (`f31e1b1`); o arquivo de teste
difere em 22 KB entre os dois. O corpo deste teste, porém, é **byte-idêntico**
nas duas versões (só muda a linha absoluta: 1748 na sombra, 2386 no vivo), então
um hunk com contexto aplica nos dois. **Se o C.patch for montado como diff de
contexto isso é seguro; montado por número de linha, reverte a 6ª passada.**
`--write-baseline` NÃO foi necessário: o censo da sombra sai `rc 0` com
`new_blocking: 0` e `dead_baseline_entries: 0`.

### R4-3 — owner validado DEPOIS de um transporte lossy `[P2]`

`upgrade.sh` lê `github_owner` do install-state por substituição de comando, e
esse transporte é lossy de dois jeitos específicos: bash não consegue guardar
NUL numa variável (é descartado em silêncio) e `$( )` tira newlines finais. O
shell validava, portanto, uma string DIFERENTE da registrada. **Reproduzido
contra o leitor EXTRAÍDO do `upgrade.sh` shipado** (nunca uma cópia — cópia só
concorda consigo mesma):

```
owner "ali\0ce"   => ACEITO como "alice"
owner "alice\n\n"     => ACEITO como "alice"
owner "alice\r"       => recusado pela gramática (CR sobrevive ao transporte)
```

**Cura onde os bytes ainda estão íntegros:** o leitor python recusa NUL/CR/LF e
sai `3`. Isso é **integridade de transporte, não gramática** — a pergunta "este
valor sobrevive ao transporte?" é outra pergunta que "este valor é um handle?",
e restaurar o charset no python reconstruiria a segunda cópia que a rodada 1
apagou. `_wbm_github_handle_ok` segue dono único da gramática. Depois: os três
recusados, `acme-platform` aceito. Fixture **F4.2**, com o leitor extraído e um
controle de handle limpo.

### Limite honesto dos controles de F4.1 e F4.2

Nenhuma das duas fica vermelha na árvore pré-patch, e por razões diferentes:

* **F4.1** passa lá porque aquela árvore não tem a linha de trap que eu
  introduzi — é guarda de REGRESSÃO da minha própria cura, e o vermelho dela foi
  medido contra a implementação intermediária (`>>> victim DELETED`);
* **F4.2** não consegue nem rodar lá: o leitor pré-patch tem outra FORMA (sem
  `_riso_h`) e a âncora de extração não casa. A perna reporta
  «could not extract the reader — this leg is dead, not passing», que é o
  comportamento certo de um instrumento cuja âncora sumiu, e conta como FALHA em
  vez de passar calada.

Está dito aqui para que ninguém leia o verde delas no controle como prova de
algo que elas não medem.
