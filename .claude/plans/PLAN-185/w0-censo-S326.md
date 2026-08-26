# PLAN-185 W0 — censo da CLASSE de escrita insegura do installer

> **Sessão:** S326 · **Data:** 2026-08-24 · **Escopo:** read-only sobre o alvo.
> Nenhum arquivo existente foi editado. Três arquivos NOVOS entregues.
>
> **Instrumento:** `.claude/scripts/check-installer-write-safety.py`
> **Baseline:** `.claude/scripts/data/installer-write-safety-baseline.txt`
> **Oráculo:** `.claude/scripts/tests/test_check_installer_write_safety.py`
>
> **Três passadas, e uma quarta recusada por doutrina.** A 1ª entregou o
> censo; a 2ª curou 8 achados do pair-rail cross-model; a 3ª curou mais 7,
> todos da classe fail-open. A rodada 3 do rail devolveu mais **9 da mesma
> classe**, e a decisão foi PARAR: o alvo da correção é a ARQUITETURA do
> matcher, não os sítios — ver §7-quater. Os números desta página são os da
> 3ª passada. §11 guarda os das anteriores.
>
> Todo número abaixo é derivado do script. O comando que o produz está ao lado.
> Nenhum número desta página veio de `grep` manual — o `grep` foi usado apenas
> para CALIBRAR as regras, e a §7 documenta o caso medido em que ele teria
> mentido.

---

## 1. O que o censo mede, e por quê é um censo de CLASSE

O `PLAN-185` §1 reporta dois defeitos. A §3 do plano exige o censo da CLASSE
antes da cura, com a razão explícita: este repositório já pagou duas vezes por
curar sítios e deixar a forma viva (`PLAN-182`: 16 módulos re-derivando o slug;
`PLAN-167`: ownership decidido por ramo local).

O censo cobre duas classes:

| Classe | Pergunta | CWE |
|---|---|---|
| `symlink-follow` | Uma escrita é decidida por predicado de existência que DEREFERENCIA (`-e`/`-f`/`-d`/... — tudo menos `-L`/`-h`)? Um link **pendente** torna `-e` falso, o ramo "ainda não existe" é tomado, e o `cp`/`>` seguinte escreve ATRAVÉS do link, fora do `$TARGET`. | CWE-59 / CWE-61 |
| `sed-interp` | Um valor controlado pelo operador é interpolado em substituição `sed`/`awk` sem escapar o delimitador (e `&`/`\`)? O valor com o delimitador aborta o comando; como `>` cria o destino ANTES, o aborto deixa 0 bytes que o ramo EXISTS-skip passa a tratar como instalado para sempre. | CWE-78-adjacente |

**A forma é a mesma nas duas, e é ela que justifica o plano:** a defesa **já
existe no MESMO arquivo**, aplicada a outra árvore, e um segundo sítio deixou
de chamá-la.

- Classe A — a guarda existe em `scripts/install.sh:2148` (`if [[ -L "$f" ]]`
  → recusa substituir através de link pré-existente).
- Classe B — a guarda existe em `scripts/install.sh:2043` (`_add_sub` escapa
  `[|&\]` antes de montar o script) **e escapa exatamente a mesma variável** em
  `:2048` (`_add_sub "OWNER_HANDLE" "$GITHUB_OWNER"`).

Ou seja: `$GITHUB_OWNER` é interpolado em DOIS lugares do mesmo arquivo — com
escape em `:2048`, sem escape em `:1508`. Não é mecanismo ausente; é mecanismo
presente e não chamado. É a classe "ramo local" que o `CLAUDE.md` §4 proíbe, na
sua forma por OMISSÃO.

---

## 2. Totais (RE-DERIVADOS após a segunda passada do rail)

> Os números da primeira passada estão preservados na §11 para comparação. Os
> desta seção são os que valem, medidos depois de curar os 8 achados.

```
python3 .claude/scripts/check-installer-write-safety.py
```

| Métrica | Valor |
|---|---|
| Arquivos varridos (`scripts/**/*.sh`, menos `scripts/tests/`) | **21** |
| Sítios totais | **273** |
| — classe `symlink-follow` | 269 |
| — classe `sed-interp` | 4 |
| **`desguardado`** | **12** |
| **`indeterminado`** (bloqueia) | **15** |
| **BLOQUEANTES** (soma dos dois) | **27** |
| `guardado` | 3 |
| `nao-aplicavel` | 243 |
| Adjacente (`rm` com barra final — informativo, NÃO bloqueia) | 0 |

Matriz classe × veredito:

```
python3 .claude/scripts/check-installer-write-safety.py --json \
  | python3 -c "import json,sys,collections; d=json.load(sys.stdin); \
     m=collections.Counter((s['class'],s['verdict']) for s in d['sites']); \
     [print('%-16s %-14s %d'%(k[0],k[1],m[k])) for k in sorted(m)]"
```

| Classe | `desguardado` | `indeterminado` | `guardado` | `nao-aplicavel` |
|---|---|---|---|---|
| `symlink-follow` | **10** | **14** | 2 | 243 |
| `sed-interp` | **2** | **1** | 1 | 0 |

Bloqueantes por arquivo: `upgrade.sh` **10**, `install.sh` **9**,
`_codex_harness.sh` 4, `_framework_manifest_set.sh` 2, `install-npm.sh` 1,
`measure-repo-size.sh` 1.

**O veredito `indeterminado` é novo e existe por causa do rail.** Um matcher de
SEGURANÇA falha FECHADO: uma forma que ele não consegue decidir é bloqueio
NOMEADO, nunca `nao-aplicavel` silencioso. Ele entra no baseline como o
`desguardado` — estar lá significa que um humano OLHOU, não que a forma é
tolerada.

**Contagem 0 REPROVA com exit 2**, por desenho: zero sítios significa que o
padrão de busca quebrou, não que o repositório está limpo. E o cheque de zero
roda **antes** de `--write-baseline` (achado P2-8), senão gravar um baseline
vazio abençoaria o próprio estado quebrado.

Os três sítios que o `PLAN-185` §1 nomeia continuam encontrados e bloqueantes
após todas as curas:

| Sítio | Classe | Veredito | Função |
|---|---|---|---|
| `install.sh:1466` | `symlink-follow` | `desguardado` | `install_docs_template` |
| `install.sh:1504` | `symlink-follow` | `desguardado` | `install_github_templates` |
| `install.sh:1508` | `sed-interp` | `desguardado` | `install_github_templates` |

---

## 3. Os 27 sítios BLOQUEANTES — a tabela

Por arquivo:

| Arquivo | bloqueantes |
|---|---|
| `scripts/upgrade.sh` | **10** |
| `scripts/install.sh` | **9** |
| `scripts/_codex_harness.sh` | 4 |
| `scripts/_framework_manifest_set.sh` | 2 |
| `scripts/install-npm.sh` | 1 |
| `scripts/measure-repo-size.sh` | 1 |

Detalhe (`A` = `symlink-follow`, `B` = `sed-interp`):

| Sítio | Função | Classe | Veredito |
|---|---|---|---|
| `_codex_harness.sh:178` | `_codex_emit_file` | A | desguardado |
| `_codex_harness.sh:221` | `_codex_write_manifest` | A | desguardado |
| `_codex_harness.sh:355` | `_codex_emit_managed_requirements` | A | indeterminado |
| `_codex_harness.sh:360` | `_codex_emit_managed_requirements` | A | indeterminado |
| `_framework_manifest_set.sh:1014` | `_apply_claude_dir_gitignore` | A | indeterminado |
| `_framework_manifest_set.sh:1030` | `_apply_claude_dir_gitignore` | A | indeterminado |
| `install-npm.sh:249` | — | A | desguardado |
| `install.sh:898` | `install_one` | A | indeterminado |
| `install.sh:944` | `install_template` | A | **desguardado — mesma forma do F1** |
| `install.sh:1431` | `install_reference_personas` | A | **desguardado — mesma forma do F1** |
| `install.sh:1466` | `install_docs_template` | A | **desguardado — F1 reportado** |
| `install.sh:1504` | `install_github_templates` | A | **desguardado — F1 reportado (2º)** |
| `install.sh:1508` | `install_github_templates` | B | **desguardado — F2 reportado** |
| `install.sh:1575` | `build_settings` | A | indeterminado |
| `install.sh:1968` | `install_protocol_pointer` | A | indeterminado |
| `install.sh:2030` | `portable_sed_inplace` | B | indeterminado (script dinâmico — §7-bis) |
| `measure-repo-size.sh:40` | — | B | desguardado |
| `upgrade.sh:1211` | `_apply_single_file` | A | desguardado |
| `upgrade.sh:1383` | `backup_and_replace` | A | indeterminado |
| `upgrade.sh:1397` | `backup_and_replace` | A | indeterminado |
| `upgrade.sh:1425` | `backup_and_replace` | A | indeterminado |
| `upgrade.sh:1486` | `backup_and_replace` | A | indeterminado |
| `upgrade.sh:1490` | `backup_and_replace` | A | indeterminado |
| `upgrade.sh:1640` | `_refresh_protocol_pointer` | A | indeterminado |
| `upgrade.sh:1745` | `_refresh_protocol_pointer` | A | desguardado |
| `upgrade.sh:3153` | `_refresh_schema_doc` | A | indeterminado |
| `upgrade.sh:3264` | `upgrade_agents_canonical_only` | A | desguardado |

Os cinco `indeterminado` de `backup_and_replace` compartilham uma causa: a
função tem **253 linhas**, e depois do `fi` do predicado há outro controle de
fluxo antes da escrita. O modelo de indentação não consegue situar a escrita, e
a postura fail-closed manda bloquear em vez de afirmar. `_refresh_protocol_pointer`
(177 linhas) é o mesmo caso.

### 3.1 O achado que muda o desenho da cura

**Os defeitos F1 e F2 não têm dois sítios — têm nove só em `install.sh`.** As
linhas `:944` e `:1431` **não estavam reportadas** no `PLAN-185` §1 e são
textualmente idênticas ao F1:

```
  if [[ -e "$dst" ]]; then
    echo "    EXISTS (skipping): ..."
    return
  fi
  ...
  cp "$src" "$dst"
```

`install.sh:944` (`install_template`), `install.sh:1431`
(`install_reference_personas`) e `install.sh:1466` (`install_docs_template`)
são **byte-idênticos no predicado e na escrita**, diferindo só pela função.
`install.sh:1575` (`build_settings`) é a mesma forma sobre
`.claude/settings.json`, e sai `indeterminado` apenas porque outro `if`
intervém antes do `cp`.

Isto é exatamente o que a W0 existe para descobrir: curar só o `:1466` deixaria
quatro cópias vivas do mesmo defeito no mesmo arquivo.

## 4. Os 3 sítios `guardado` — o corpus já sabe fazer certo

| Sítio | Guarda | Forma |
|---|---|---|
| `_framework_manifest_set.sh:705` | escape para o delimitador ativo `\|` | classe B, inline |
| `_framework_manifest_set.sh:837` | `_root_gitignore_symlink_guard()` em `:835` | **função compartilhada** |
| `_framework_manifest_set.sh:950` | `_root_gitignore_symlink_guard()` em `:948` | **função compartilhada** |

**`_root_gitignore_symlink_guard` (`_framework_manifest_set.sh:869`) é o
protótipo exato do que a W1 [P1] pede**: uma função de 7 linhas
(`[ -L "$1" ] && return 1`), chamada de dois sítios, escrita pela mesma razão
("*a root .gitignore symlink must never route framework appends elsewhere*",
comentário em `:833-834`). A W1 não precisa inventar mecanismo — precisa
**generalizar este**.

**Caiu de 5 para 3 na terceira passada, e por dois motivos distintos:**

1. A exigência de **polaridade** (achado R3): um `|| return` sobre um teste
   `-L` faz o OPOSTO de guardar. Nenhum sítio vivo usava a forma invertida,
   mas o crédito era fail-open.
2. A regra de **todas as escritas** (achado R6): `fms:1014` e `upgrade.sh:3153`
   têm uma guarda REAL sobre a primeira escrita e uma SEGUNDA escrita que o
   modelo não situa. O veredito mais severo vence, então o sítio lê
   `indeterminado`. É "block mixed shapes", exatamente como o revisor pediu.

O mecanismo de creditar teste `-L` continua vivo e provado — em árvore-sombra,
por `test_p1_3_aborting_guard_is_still_credited` e
`test_r3_correct_short_circuit_guard_is_credited`. O que a corpus viva deixou
de exibir é o *sítio*, não o *mecanismo*.

Consequência de instrumento: o censo credita a CHAMADA de uma função-guarda
(regra A5) **e exige que ela aborte, com a polaridade certa**. Sem isso, a cura
da W1 landaria e o número não se moveria — o `[P1]` seria inobservável.

## 5. O que a classe tem além dos dois sítios reportados

Três sub-populações, com tratamentos diferentes:

**(a) Entrega do installer — `install.sh` + `upgrade.sh`: 9 sítios.**
É a superfície que o `PLAN-185` §1 descreve: o adopter controla o `$TARGET`, e
um link plantado ali redireciona a escrita. Os 9 são a população da cura.

**(b) Harnesses de vendor — `_codex_harness.sh`, `_grok_harness.sh`: 5 sítios.**
Mesma forma mecânica, superfície diferente: escrevem templates de harness no
target. Herdam o vetor (o target é do adopter), mas não estão no escopo
declarado da W1/W2.

**(c) Ferramentas locais — `install-npm.sh`, `measure-repo-size.sh`: 2 sítios.**
`measure-repo-size.sh:40` é classe B genuína (`$REPO_DIR` vem de `$1` sem
escape do delimitador `|`), mas o script é uma ferramenta de medição local, não
parte da entrega.

### 5.1 A W1 `[P1]` como escrita é INALCANÇÁVEL — recomendação de emenda

O `PLAN-185` W1 `[P1]` diz:

> *"A guarda e aplicada por UMA funcao compartilhada, e o censo da W0 passa a
> ter zero sitios desguardados."*

**Medido: zero é inalcançável dentro do escopo da W1.** A W1 cura
`install_docs_template`. Para o censo chegar a zero seria preciso curar os **24
sítios bloqueantes de classe A** em 5 arquivos (10 `desguardado` + 14
`indeterminado`), incluindo o harness de vendor — que a §2 do plano não coloca
em escopo — e os **3 de classe B**.

Duas rotas, e a decisão é do Owner:

- **(i)** Estreitar o Check do `[P1]` para a população que a wave cura:
  *"zero sítios BLOQUEANTES de classe A em `install.sh` e `upgrade.sh`"*
  (**19 → 0**), mantendo os 5 restantes no baseline com a razão registrada.
- **(ii)** Alargar o escopo da W1 para os 24. Custo maior, e mistura entrega
  com harness de vendor.

**Nota das passadas 2 e 3:** 14 dos 24 são `indeterminado`, não
`desguardado` — o matcher não consegue situar a escrita dentro de funções de
177–253 linhas. Para vários deles a cura provavelmente não é "adicionar uma
guarda" e sim **encurtar a função**, e essa é uma conversa de refatoração que a
W1 não abre. A rota (i) também isola esse problema.

**Recomendação do CEO: (i).** A razão não é economia — é que o `[P1]` como está
transforma um critério de aceite em algo que só passa alargando o escopo da
wave, e um AC que força scope creep é um AC que será relaxado sob pressão. A
rota (i) mantém o critério MECÂNICO (o censo continua sendo o oráculo) e
declara os 5 restantes como população conhecida, vigiada pelo baseline com
anti-rot.

**Isto NÃO é decisão minha e nada foi alterado no plano.** Fica registrado aqui
como pergunta aberta da W0.

### 5.2 O que a classe NÃO tem

**Zero** deletes com barra final sobre operando variável (`rm -rf "$d/"`) — a
única forma de delete que dereferencia. Medido, não assumido: o detector tem
controle positivo (planta `rm -rf "$d/"` e o vê), e o corpus real dá 0.

```
python3 .claude/scripts/check-installer-write-safety.py --json \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['adjacent_trailing_slash_deletes'])"
# => []
```

Deletes comuns (`rm`/`unlink` sem barra) estão FORA do conjunto de escrita por
decisão declarada: não dereferenciam o último componente, então remover um link
pendente remove o LINK. Incluí-los na primeira rodada fez arquivos de `mktemp`
dominarem a população (medido: 6 de 36).

---

## 6. Consequências para W1 e W2

### W1 — a cura de F1

1. **Uma função compartilhada, modelada em `_root_gitignore_symlink_guard`.**
   Assinatura sugerida: recebe o destino, recusa se `[ -L "$dst" ]`, mensagem
   nomeada, `return 1`. Não é mecanismo novo — é o de `:869` generalizado.
2. **Cinco sítios em `install.sh`, não um.** `:944`, `:1431`, `:1466`, `:1504`,
   `:1575`. Curar só o `:1466` deixa quatro cópias vivas.
3. **A prova de uso tem de ser comportamental.** O `[P1]` já pede: reverter a
   função deixa AMBOS os testes vermelhos, não apenas um. O censo credita a
   chamada da função-guarda, então o veredito flipa mecanicamente de
   `desguardado` para `guardado` — e o baseline tem de perder a linha NO MESMO
   commit, senão o gate vai vermelho por rot (anti-rot é por desenho).
4. **O `-e` sozinho não basta como cura.** Trocar `-e` por `-L`-primeiro
   resolve o link pendente, mas o Check da W1 exige asserção nos BYTES do alvo
   externo, não no exit code — o defeito atual sai `exit 0`.

### W2 — a cura de F2

1. **O escape sozinho NÃO cura o defeito de 0 bytes.** Escapar `$GITHUB_OWNER`
   impede o aborto do `sed`, mas o `>` continua truncando o destino ANTES do
   comando rodar. Qualquer outro aborto (template ilegível, disco cheio) volta
   a deixar 0 bytes EXISTS-skipped para sempre. A W2 está certa em pedir
   **validação + escrita ATÔMICA** (`tmp` + `mv`), e as duas coisas são
   necessárias, não alternativas.
2. **Armadilha de observabilidade — nomeada.** O censo mede o ESCAPE, não a
   VALIDAÇÃO. Se a W2 curar validando `$GITHUB_OWNER` a montante mas mantiver
   `sed "s/{{OWNER_HANDLE}}/$GITHUB_OWNER/g"`, o veredito continua
   `desguardado` e o baseline continua verde — cura invisível ao instrumento.
   **Recomendação: rotear a substituição pelo idioma de escape que já existe**
   (o `_add_sub` de `:2036-2049`, ou um `_sed_escape_replacement()` extraído
   dele), para que o flip de veredito seja mecânico e o `[P0]` da W2 seja
   observável pelo mesmo oráculo que a W0 instalou.
3. **A fixture (c) do plano continua sendo a que falta.** Um destino de 0 bytes
   pré-existente tem de ser CORRIGIDO por um install subsequente. Nenhuma das
   duas curas acima faz isso sozinha: exige que o ramo EXISTS-skip (`:1504`)
   pare de tratar tamanho 0 como "instalado".
4. **`measure-repo-size.sh:40` é o segundo sítio de classe B.** Fora do escopo
   da W2 (não é entrega), mas deve permanecer no baseline com a razão
   registrada, não ser silenciado.

### Cerimônia

`scripts/install.sh` e `scripts/upgrade.sh` são **canônicos**. A W1 toca 5
sítios em `install.sh`; se a rota (i) da §5.1 for adotada, toca também
`upgrade.sh` (3 sítios). A recomendação do plano — **UMA** cerimônia cobrindo
W1+W2 — continua válida e fica mais forte com o censo: é a mesma função
compartilhada e a mesma superfície.

**Nada nesta W0 exige assinatura.** Os três arquivos entregues são novos e
não-canônicos (verificar com `check_canonical_edit.py --is-canonical`).

---

## 7. Disciplina do instrumento — o que foi medido, não assumido

Esta seção existe porque a lição
[[feedback-instrument-needs-same-scrutiny-as-subject]] diz que num censo o
INSTRUMENTO precisa do mesmo escrutínio adversarial que o sujeito.

**Cinco defeitos do próprio censo foram encontrados e curados durante a W0:**

1. **Falso-verde por colisão de fingerprint (o mais grave).** `install.sh:944`,
   `:1431` e `:1466` são textualmente idênticos, e com o fingerprint derivado
   de `(path, class, operand, snippet)` os três colapsavam em **UMA** chave de
   baseline. Consequência: um QUARTO sítio idêntico casaria com a entrada
   existente e **o gate ficaria verde sobre um defeito novo**. Curado pondo a
   função envolvente e um ordinal de ocorrência no payload. Regressão coberta
   por `TestFingerprintCollision`, incluindo a metade COMPORTAMENTAL (baselinar
   um gêmeo e exigir que o outro ainda fique vermelho) — hashes distintos só
   interessam se o gate de fato dispara.
2. **Guarda na MESMA linha era ignorada.** `upgrade.sh:1540` é
   `[[ -L "$p" || -f "$p" ]]` — a forma correta, com comentário do autor
   dizendo "*-L before -f (lstat-first; -f alone would follow a link)*" — e
   saía `desguardado`. A varredura de guardas pulava a própria linha do
   predicado.
3. **Semântica de negação ausente (regra A8).** `[ ! -e "$f" ]` e
   `[[ -f "$x" ]] || continue` fazem o link PENDENTE tomar o ramo SEGURO. Sem a
   regra, o censo reportava 36 desguardados, dos quais as formas negadas eram
   falsos positivos na direção que importa: afirmavam defeito onde não há. A
   tabela-verdade tem 4 células e as 4 são testadas.
4. **Classe B casava qualquer aspa numa linha com `sed`.** `publish-plugin.sh:29`
   e `upgrade.sh:1646` saíam `desguardado`; nos dois, a corrida entre aspas era
   uma substituição de comando envolvendo um `sed` cujo script era
   single-quoted — seguro. Curado escopando aos ARGUMENTOS do comando `sed`, com
   expansão recursiva de `$( )` (necessária porque o ÚNICO escape correto do
   corpus, `_framework_manifest_set.sh:705`, vive dentro de `$( )`).
5. **Corpos de heredoc lidos como shell.** `import json, sys` virou operando em
   `publish-plugin.sh:55`. Mascarado.

**O `grep` teria mentido, e isso foi medido.** Uma sondagem por
`grep -cE '(\[\[?|test)[^]]*-(e|f|d)'` dá 74 ocorrências em `install.sh`; o
censo classifica 269 sítios de classe A no corpus e reprova 14. Os dois números
respondem perguntas diferentes: o `grep` conta APARIÇÕES do padrão; o censo
responde se o predicado DECIDE uma escrita e se há guarda. Publicar o número do
`grep` como "sítios do defeito" teria inflado a população em ~5× e escondido a
distinção `guardado`/`nao-aplicavel` que é justamente o resultado.

### Limitações declaradas (não curadas)

- **Identidade de operando é TEXTUAL.** Um alias (`local d="$dst"`) quebra a
  ligação predicado↔escrita. Corrigir exigiria alias analysis. A escolha é
  deliberada: um censo que erra para o lado de NÃO reportar é pior que um que
  erra para o lado de reportar.
- **Corte de fluxo é aproximado por indentação, não um CFG.** As regras R1/R2
  estão impressas em `--rules` e foram validadas contra os quatro predicados
  conhecidos de `install.sh` (`:1458`, `:1466`, `:1499`, `:1504`), separando
  corretamente o preview do dry-run da decisão viva nos quatro.
- ~~**Escrita na MESMA linha do teste** não é atribuída.~~ **CURADO na 2ª
  passada** (achado P1-1): `same_line_reach()` analisa
  `[[ -e "$x" ]] || cp ...` e classifica pelo conector; conector não
  classificável BLOQUEIA. Manter isso como "limitação declarada" era o erro
  que o revisor apontou — num matcher de segurança, forma não suportada é
  bloqueio, não nota de rodapé.
- ~~**Janela de 25 linhas.**~~ **CURADO** (P1-1): o corpo INTEIRO da função é
  varrido. Em troca, o modelo passou a BLOQUEAR (`indeterminado`) quando não
  consegue situar a escrita, em vez de afirmar um veredito sobre 135 linhas de
  distância.
- **`scripts/tests/` está fora do escopo** por decisão: são os oráculos que
  plantam fixtures inseguras de propósito. Toda outra `.sh` sob `scripts/`
  (inclusive `scripts/local/`) está dentro.
- **Escrita cross-função ainda não é rastreada.** Se a função A testa e a
  função B escreve, o censo não liga as duas. É a mesma raiz da identidade
  textual de operando.
- **A sondagem de `mv` é same-device.** Um `mv` cross-device degrada para
  cópia e PODE seguir o link. O envelope medido é same-device; alvo de install
  em outro dispositivo está fora dele.
- **A W1 [P1] pede "zero desguardados"** e o censo mede **25 bloqueantes** —
  ver §5.1.

### Desvio de formato do baseline, declarado

O `PLAN-185` W0 sugere `arquivo:linha:classe:veredito`. O entregue é um
**superconjunto**: `arquivo:linha:classe:veredito:fingerprint`, com o
casamento feito por `(arquivo, classe, fingerprint)` e a linha carregada apenas
para leitura humana.

**Razão:** `scripts/install.sh` tem 3020 linhas e é canônico. Um baseline
chaveado por número de linha ficaria vermelho a cada edição não relacionada
acima de um sítio, e um gate que apita por ruído é um gate que será desligado.
Deriva de linha isolada é REPORTADA, nunca fatal.

---

## 7-bis. Segunda passada — os 8 achados do pair-rail cross-model (S326)

O revisor cross-model (codex) devolveu 8 achados sobre
`check-installer-write-safety.py`. Cada um foi verificado contra o código antes
de ser aceito. **Os 8 estão CONFIRMADOS e curados** — nenhum foi refutado, e um
deles (P1-2) era um falso-NEGATIVO sobre defeito real, a pior categoria possível
num instrumento de segurança.

| # | Achado | Disposição | Evidência |
|---|---|---|---|
| P1-1 | Varrer o escopo predicado→escrita inteiro | **CONFIRMADO** | `scan_end = min(fn[2], idx + 25)` capava em 25 linhas **contradizendo a regra A4 impressa**, que promete o corpo inteiro da função; e o laço começava em `idx+1`, então `[[ -e "$dst" ]] \|\| cp ...` nunca era inspecionado |
| P1-2 | Derivar alcançabilidade do RAMO real | **CONFIRMADO — o mais grave** | A docstring afirmava *"the attributed write is always on the condition-FALSE path"*; falso para escrita no ramo `then`. `upgrade.sh:3153` (`if [ ! -e ]; then cp`) é instância VIVA: saía `nao-aplicavel` sendo defeito real |
| P1-3 | Guarda precisa NEUTRALIZAR a escrita | **CONFIRMADO** | `guards_on_line` creditava qualquer `-L`/`readlink`/helper textual sem exigir aborto. Nenhum veredito vivo estava errado (as 6 guardas do corpus abortam), mas o buraco era real — e **reapareceu no lado da guarda** depois de eu curar o lado da escrita: 5 falsos `guardado` em `upgrade.sh` creditados a um `rm -f` 27 linhas antes |
| P1-4 | Montar o argumento sed/awk completo | **CONFIRMADO** | `arg_blob = " ".join(toks)` + `_quoted_spans` via corridas isoladas: `sed 's/x/'"$V"'/g'` nunca aparecia inteiro; script SEM aspas era invisível |
| P1-5 | Provar o escape ALCANÇANTE p/ o delimitador ativo | **CONFIRMADO** | `_var_escaped_upstream` retornava na PRIMEIRA atribuição escapada (não na última) e nunca recebia `delim`. Controle: a classe `[\|&\\]` cobre `\|`=True, `/`=False |
| P1-6 | Falhar FECHADO em arquivo ilegível | **CONFIRMADO** | `errors="replace"` + `continue` num `OSError`: um `.sh` novo ilegível saía do censo em silêncio e o resto ainda podia sair 0 |
| P2-7 | Tirar `mv` do conjunto de escritores | **CONFIRMADO por medição** | Sondagem em link pendente: `cp`/`>`/`>>`/`tee`/`touch`/`truncate` **escrevem através**; `mv`/`install`/`rsync`/`ln -sf` **substituem o link**; `sed -i` recusa. **Ressalva ao achado:** ele dizia que isso baselinava DOIS sítios; só um (`_grok_harness.sh:138`) saiu — `install-npm.sh:249` permanece por um `redirect` independente em `:261` |
| P2-8 | Rejeitar varredura vazia antes de gravar baseline | **CONFIRMADO** | O ramo `--write-baseline` vinha **antes** do cheque de zero em `main()` |

### O que cada cura mudou nos números

| | Antes (1ª passada) | Depois (2ª passada) |
|---|---|---|
| Sítios totais | 286 | 273 |
| `desguardado` | 16 | 13 |
| `indeterminado` | — (não existia) | 12 |
| **Bloqueantes** | 16 | **25** |
| `guardado` | 6 | 5 |

O total de bloqueantes SUBIU (16 → 25) apesar de `desguardado` ter caído. É o
efeito esperado de trocar silêncio por bloqueio nomeado: formas que o matcher
não decide passavam como `nao-aplicavel` e agora reprovam.

### Regressões — cada cura tem controle, e cada controle foi sabotado

`TestRailFindingsS326` tem **16 testes**, um par por achado onde a polaridade
importa (positivo + negativo). Exemplos do par:

- P1-2: `if [ ! -e "$d" ]; then cp` ⇒ `desguardado`; `if [ -e "$d" ]; then cp`
  ⇒ `nao-aplicavel`. Os dois sentidos do erro antigo.
- P1-3: guarda que só avisa ⇒ NÃO creditada; guarda que aborta ⇒ ainda
  creditada (senão a cura quebraria os bons exemplos do corpus).
- P2-7: `mv` ⇒ `nao-aplicavel`; `cp` ⇒ `desguardado`.
- P1-4: script costurado E script sem aspas ⇒ vistos; `$src`/`$dst` (ARQUIVOS)
  ⇒ NÃO viram veredito.

**Prova de que as curas são load-bearing** (não basta o verde):

| Sabotagem | Resultado |
|---|---|
| Reintroduzir `mv` em `_LAST_ARG_WRITERS` | `1 failed` |
| Creditar guarda sem `guard_aborts()` | `1 failed` |
| `_escape_class_covers` retornar `True` sempre | `1 failed` |
| Restaurar | **42 passed** (contagem da 2ª passada; hoje são 56) |

### Duas regressões que EU introduzi ao curar, e que a medição pegou

Registradas porque são o custo real de aplicar um achado sem medir o efeito:

1. **Argumentos de ARQUIVO tratados como script.** Ao aplicar P1-4 passei a
   examinar todo token não-flag, e o censo emitiu veredito sobre
   `$codeowners_src`, `$dst`, `$tmp`, `$file` — nomes de arquivo, não scripts.
   Curado com `script_operands()`, que sabe que `-e` toma script e `-f`/`-v`
   não, e que só o primeiro posicional é programa.
2. **Programa `awk` multi-linha lido como aspas desbalanceadas.** A regra
   fail-closed transformaria 4 sítios benignos em ruído permanente. Curado
   JUNTANDO linhas de continuação (`logical_line`) — cobertura ganha, não ruído
   adicionado. Aspas que nunca fecham continuam bloqueando.

### O custo declarado do fail-closed

`install.sh:2030` (`sed "$script" "$file" > "$tmp"`) sai `indeterminado`: o
script é construído em `build_sed_script` e o delimitador não é legível NAQUELE
sítio. O escape existe e está correto (`:2043`). Bloquear ali é o preço de não
dizer "sem delimitador em risco" sobre uma substituição que o matcher não leu —
fail-OPEN seria a alternativa. Fica no baseline com a razão registrada.

## 7-ter. Terceira passada — os 7 achados fail-open do rail (rodada 2)

A rodada 2 do pair-rail devolveu 7 achados NOVOS, todos da mesma classe: o
matcher classificava `nao-aplicavel` ou `guardado` onde deveria bloquear.
**Os 7 estão CONFIRMADOS e curados.** Três eram falsos-NEGATIVOS sobre defeito
real (R1, R6, R7); dois eram falsos `guardado` (R3, R4); um era semântica de
ferramenta errada, verificada por medição (R5).

| # | Achado | Disposição | Evidência |
|---|---|---|---|
| R1 | Negação em predicado de uma linha | **CONFIRMADO** | `negated_pos = body[:op_end]` **inclui o operando**, e o regex `!\s*-[A-Za-z]+\s*$` exige terminar em `-e` ⇒ **estruturalmente inatingível**, `negated` era SEMPRE False. `[[ ! -e "$dst" ]] && cp ...` saía `nao-aplicavel` |
| R2 | Condição composta | **CONFIRMADO** | `cond_true = negated` trata o teste de arquivo como a condição inteira. Em `[[ "$force" == 1 \|\| -e "$dst" ]]` o link pendente ainda alcança o `cp` com `force=1`. Dois sítios vivos são compostos (`_codex_harness.sh:355`, `install.sh:898`) |
| R3 | Polaridade da guarda | **CONFIRMADO** | `if _RE_OR_JUMP.search(body): return True` creditava qualquer `\|\| return`. Mas `[ -L "$d" ] \|\| return` faz o **oposto**: o teste tem SUCESSO no symlink, o salto não dispara, a escrita prossegue. E a polaridade **depende do tipo**: teste aborta em `&&`, função-guarda aborta em `\|\|` |
| R4 | Dominância da remoção | **CONFIRMADO** | `if "rm/unlink" in guard_kind: return True` — incondicional. Em `if [[ -e "$dst" ]]; then rm "$dst"; fi; cp ...` o link pendente PULA o `rm` e o `cp` escreve através |
| R5 | `cp -P` não é guarda de destino | **CONFIRMADO por medição** | Sonda: `cp -P src dangling_link` **escreveu ATRAVÉS**, idêntico a `cp` puro. `-P`/`-h`/`--no-dereference` governam a FONTE. Só `--remove-destination` age no destino (GNU-only ⇒ **não medível neste host**, mantido por semântica e declarado) |
| R6 | Avaliar toda escrita candidata | **CONFIRMADO** | A varredura parava na primeira escrita alcançável. Com uma escrita SEGURA no `then` seguida de uma INCONDICIONAL ao mesmo operando, só a segura era analisada ⇒ `nao-aplicavel` |
| R7 | Opções `-e` anexadas | **CONFIRMADO** | `sed -e"s\|x\|$OWNER\|g" f` e `--expression="..."` caíam no ramo genérico "começa com `-`". Com nome de arquivo literal, **nenhum sítio era emitido** ⇒ interpolação crua passava batido pelo baseline |

### O que as sete curas mudaram

| | 2ª passada | 3ª passada |
|---|---|---|
| `desguardado` | 13 | **12** |
| `indeterminado` | 12 | **15** |
| **Bloqueantes** | 25 | **27** |
| `guardado` | 5 | **3** |
| Testes | 42 | **56** |

Bloqueantes subiram de novo (25 → 27) e `guardado` caiu (5 → 3). É o padrão das
duas passadas: cada correção fail-open converte silêncio ou crédito indevido em
bloqueio nomeado.

### Controles — 14 plantas novas, 7 sabotagens

`TestRailRound2S326` tem **14 testes**, em pares de polaridade onde ela importa:

- R1: `[[ ! -e ]] && cp` ⇒ bloqueia; `[[ -e ]] && cp` ⇒ `nao-aplicavel`.
- R2: composta ⇒ `indeterminado`; simples ⇒ ainda decide `desguardado`
  (não-vacuidade: a regra não pode engolir todo veredito).
- R3: **três** controles, porque a polaridade é a armadilha — `[ -L ] || return`
  não credita, `[ -L ] && return` credita, e `helper || return` credita (a
  polaridade INVERSA, que tem de estar certa ao mesmo tempo).
- R4: remoção condicional ⇒ não credita; incondicional ⇒ credita.
- R6: a escrita perigosa depois da segura é encontrada, e o motivo tem de dizer
  quantas candidatas foram pesadas.
- R7: `-e"..."` anexado, `--expression="..."`, e o `-e "..."` destacado
  (não-regressão da forma que já funcionava).

**Cada uma das 7 curas é load-bearing** (reverter ⇒ o controle fica vermelho):

| Sabotagem | Resultado |
|---|---|
| R1 negação volta a `body[:op_end]` | `1 failed` |
| R2 composta deixa de bloquear (2 sítios) | `1 failed` |
| R3 polaridade volta a "`\|\|` sempre aborta" | `1 failed` |
| R4 `rm` creditado sem dominância | `1 failed` |
| R5 `-P` volta ao conjunto de guardas | `1 failed` |
| R6 para na primeira escrita | `1 failed` |
| R7 `-e` anexado volta a ser ignorado | `1 failed` |
| Restaurar | **56 passed** |

### Um erro meu, grave, pego por diff de AST

Ao aplicar R3/R4 substituí um bloco delimitado por um marcador errado e
**apaguei três funções e uma constante** (`flow_is_cut`, `write_destinations`,
`guards_on_line`, `_RE_BLOCK_CLOSE`). O censo quebrou com `NameError` — barulho,
não silêncio, o que é a falha boa. Restaurei do backup pré-patch comparando por
AST contra a cópia anterior.

**A lição que fica registrada:** o primeiro diff só comparou `FunctionDef`/
`ClassDef` e disse "perdidas: nenhuma" — o `_RE_BLOCK_CLOSE`, que é uma
atribuição module-level, passou batido e o censo quebrou de novo na execução
seguinte. Um diff de completude que não enumera TODAS as formas de nome de topo
dá falso-verde. O segundo diff, incluindo `Assign`/`AnnAssign`, achou o que
faltava.

## 7-quater. Rodada 3 do rail — 9 achados ABERTOS, e a decisão de PARAR

A rodada 3 do pair-rail devolveu mais **9 achados P1 da mesma classe fail-open**.
**Nenhum foi verificado por mim, nenhum foi curado, e nenhum tem controle.**
Ficam registrados aqui como ABERTOS, exatamente como chegaram:

| # | Achado (verbatim resumido) | Estado |
|---|---|---|
| Q1 | Cap de 10 escritas candidatas (`MAX_WRITE_CANDIDATES`) — atingir o teto não bloqueia | **ABERTO** |
| Q2 | `if ! test -e ...` — a forma `test` com negação não é reconhecida | **ABERTO** |
| Q3 | Jump aninhado — `then_jumps` não vê um `return` dentro de um sub-bloco | **ABERTO** |
| Q4 | Dominância da guarda `-L` — o mesmo problema do `rm`, agora no teste | **ABERTO** |
| Q5 | Helper creditado pelo NOME — `_RE_GUARD_HELPER` casa por regex de nome, sem ler o corpo | **ABERTO** |
| Q6 | `sed` com continuação de linha `\` — script quebrado por `\` no fim da linha | **ABERTO** |
| Q7 | Replacement `&` cru no escape — `&` no valor reinsere o casamento | **ABERTO** |
| Q8 | Delimitador POR SUBSTITUIÇÃO — um script com dois `s///` de delimitadores diferentes usa só o primeiro | **ABERTO** |
| Q9 | Definição escapada só num RAMO — a "última atribuição alcançante" ignora ramificação | **ABERTO** |

### Por que a W0 PARA aqui em vez de fazer uma quarta passada

Decisão do CEO, e ela segue a doutrina que este repositório já pagou para
aprender ([[feedback-fix-of-fix-means-change-the-cure-architecture]]): **quando
a classe reaparece rodada após rodada, o alvo da correção está errado.**

Três passadas, 15 achados curados, e a rodada seguinte devolve mais 9 da MESMA
classe. Isso não é uma cauda de casos de borda — é uma propriedade da
**arquitetura do matcher**, que hoje funciona por *denylist implícita*: ele
enumera as formas que sabe reconhecer e credita `guardado`/`nao-aplicavel` a
tudo o que não casa. Toda forma que ninguém pensou nasce fail-OPEN, então cada
rodada de revisão encontra mais uma — indefinidamente.

**A inversão que a cura futura exige:** enumerar as poucas formas **PROVADAS
seguras**, cada uma com controle positivo, e classificar **todo o resto** como
`indeterminado`. Isso troca uma denylist infinita por uma allowlist finita, e
faz o custo de uma forma nova recair sobre quem a introduz — que é onde ele
pertence num matcher de segurança.

Consequência prevista e aceita: o número de bloqueantes SOBE bastante na
primeira execução da versão invertida, porque as formas hoje creditadas em
silêncio passam a aparecer. Esse aumento é o resultado correto, não uma
regressão — é a mesma direção que as passadas 2 e 3 já mostraram (16 → 25 → 27).

**O que isto NÃO invalida.** O censo entregue continua cumprindo o que a W0 do
`PLAN-185` pede: encontra os três sítios nomeados no §1 do plano, encontra
outros que o plano não conhecia, roda como gate versionado com baseline
anti-rot, e reprova em contagem zero. O que ele NÃO é: um matcher completo. A
§7 e esta seção declaram o limite em vez de escondê-lo, e é por isso que o
veredito de entrega é **DONE_WITH_CONCERNS**, não `DONE`.

**Recomendação de sequenciamento:** a inversão é trabalho de instrumento, não
de wave de produto. Ela NÃO deve bloquear W1/W2 — o censo atual já é suficiente
para provar as duas curas (os sítios de F1 e F2 estão nele, bloqueantes, e uma
guarda compartilhada que aborte flipa o veredito mecanicamente). Fazer a
inversão primeiro adia a correção de um defeito de escrita-fora-do-target por
causa de precisão de medição, o que inverte as prioridades que o próprio
`PLAN-185` estabelece ao existir separado.

## 8. Wiring de CI — a linha exata que a cerimônia deve acrescentar

**Não fiz este wiring:** `.github/workflows/validate.yml` é canônico e está
fora do meu FILE ASSIGNMENT. Registro a linha para quem tiver a assinatura.

`validate.yml` não tem filtro `paths:` (roda em todo `pull_request` e todo
`push` para `main`), então não há a armadilha de "gate que a mudança não
dispara" que a S325 encontrou no `smoke-install.yml`. Passo a acrescentar no
job `validate`, seguindo a convenção dos passos vizinhos (`:73-76`, `:89-92`):

```yaml
      # PLAN-185 W0 AC-3 — censo da CLASSE de escrita insegura do installer.
      # Exit 1 = sitio desguardado NOVO (ou entrada de baseline morta);
      # exit 2 = contagem ZERO, que REPROVA por desenho (padrao de busca
      # quebrado, nao repo limpo).
      - name: Run check-installer-write-safety.py (PLAN-185 W0)
        run: |
          python3 .claude/scripts/check-installer-write-safety.py
```

Sem `|| true`, sem `continue-on-error` — o gate é fail-closed nos dois códigos.

---

## 9. Comandos executados nesta W0

| Comando | Resultado |
|---|---|
| `python3 .claude/scripts/check-installer-write-safety.py` | exit **0** — 273 sítios, 27 bloqueantes, todos no baseline |
| `python3 .claude/scripts/check-installer-write-safety.py --json` | exit **0** — payload válido |
| `python3 .claude/scripts/check-installer-write-safety.py --rules` | exit **0** — regras A1–A10, B1–B5, adjacente, vereditos, exit codes |
| `python3 -m pytest .claude/scripts/tests/test_check_installer_write_safety.py -q -p no:cacheprovider` | **56 passed** (24 da 1ª + 18 da 2ª + 14 da 3ª) |
| `python3 .claude/scripts/check-installer-write-safety.py --write-baseline` | exit **0** — 27 entradas bloqueantes (invocação EXPLÍCITA, sobre censo não-vazio) |
| `python3 .claude/scripts/check-test-env-hygiene.py` | exit **0** — *"337 flagged files, all allowlisted"*; o arquivo novo NÃO está no allowlist (limpo, não herdado) |
| `python3 .claude/scripts/check-test-audit-isolation.py` | exit **0** |
| `bash .claude/scripts/local/verify-counts.sh` | exit **0** — sem drift |
| `python3 .claude/scripts/check-staleness.py` | exit **0** |
| `python3 .claude/scripts/check-ceremony-script.py` | exit **0** — *"blocking não-waivado: 0"* |

## 10. Estado dos gates de corpus

Rodados APÓS a última edição, na ordem que o `CLAUDE.md` §4 exige (a bateria
tirada antes do último arquivo criado é verdadeira para a árvore anterior, não
para esta). **Nove invocações, todas exit 0** — tabela na §9. Re-rodadas na
íntegra depois da segunda passada do rail.

Verificações complementares:

| Verificação | Resultado |
|---|---|
| `git status --porcelain` | Nenhum arquivo existente modificado — só entradas `??` novas |
| Canonicidade dos 4 entregáveis (`check_canonical_edit.py --is-canonical`) | **0** nos quatro (não-canônicos ⇒ **dispensam cerimônia**) |
| Controle positivo do mesmo oráculo | `scripts/install.sh` ⇒ **1** (canônico) — o oráculo não está morto |
| ADR-002 (Python ≥ 3.9) | `from __future__ import annotations` presente nos dois `.py`; zero `match`; zero PEP 604 em runtime (verificado por AST, não por `grep`) |
| Determinismo | Dois runs consecutivos ⇒ conjunto de fingerprints byte-idêntico (`2f62e1b01b3f9c9d` após a 2ª passada) |
| Curas load-bearing (2ª passada) | Três sabotagens ⇒ **1 failed cada** |
| Curas load-bearing (3ª passada) | **Sete** sabotagens, uma por achado ⇒ **1 failed cada**; restaurar ⇒ **56 passed** |
| Independência de `cwd` | Invocado de `/tmp` ⇒ exit 0 (raiz resolvida por `__file__`) |

**Nada aqui exige assinatura do Owner.** Os quatro entregáveis são novos e
não-canônicos. O único item que exigirá cerimônia é o wiring de CI da §8
(`validate.yml` é canônico) e, depois, as curas W1/W2 em `scripts/install.sh`.

---

## 11. Números da PRIMEIRA passada (preservados)

Guardados para que a §7-bis possa ser auditada contra algo, em vez de pedir
confiança. Estes números estão **superados** — a §2 tem os que valem.

| Métrica | 1ª passada | 2ª passada | 3ª passada (vale) |
|---|---|---|---|
| Sítios totais | 286 | 273 | **273** |
| `symlink-follow` | 269 | 269 | 269 |
| `sed-interp` | 17 | 4 | 4 |
| `desguardado` | 16 | 13 | **12** |
| `indeterminado` | — | 12 | **15** |
| Bloqueantes | 16 | 25 | **27** |
| `guardado` | 6 | 5 | **3** |
| `nao-aplicavel` | 264 | 243 | 243 |
| Testes | 24 | 42 | **56** |
| Achados de rail curados | — | 8 | **8 + 7 = 15** |

Por que `sed-interp` caiu de 17 para 4: a primeira passada emitia um registro
por interpolação em **cada corrida entre aspas** de qualquer linha com `sed`,
incluindo nomes de arquivo. A segunda só examina os **operandos de script**
reais. Menos registros, mesma cobertura dos dois sítios que importam — ambos
seguem `desguardado`.

Por que bloqueantes SUBIU de 16 para 27 ao longo das três passadas: formas
que o matcher não decide passavam como `nao-aplicavel` e agora reprovam como
`indeterminado`. Trocar silêncio por bloqueio nomeado aumenta a contagem; é o
objetivo, não um efeito colateral.

**A tendência é o resultado mais informativo desta W0.** Quinze achados de rail
em duas rodadas, todos confirmados, e **nenhum** deles era sobre o alvo — todos
eram sobre o INSTRUMENTO. A cada rodada o censo ficava menos confiante e mais
correto. É a evidência prática da lição
[[feedback-instrument-needs-same-scrutiny-as-subject]]: num espaço cartesiano o
instrumento precisa do mesmo escrutínio adversarial que o sujeito, e um censo
escrito numa passada só teria embarcado com pelo menos três falsos-negativos
sobre defeitos reais.
