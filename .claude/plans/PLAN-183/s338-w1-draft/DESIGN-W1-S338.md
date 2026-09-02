# DESIGN — PLAN-183 W1 «Ponteiro portátil e retroativo (A1)» (draft S338, night-run)

> **Status:** DRAFT de desenho + derivação executável + evidência. **É INPUT do
> `/debate`** (a W1 é L3: toca três arquivos canônicos e reabre superfícies dos
> PLAN-167/168). Nada aqui foi landado; a sombra e o script são a prova de que o
> desenho é executável, não a execução da wave. **SIGN/LAND não foram escritos.**
>
> **Base do pack:** `HEAD` no momento da derivação final = `f0e98de` **+**
> `wave-fable51` (`.claude/plans/PLAN-169/s338-ceremony-fable51/apply-fable51-edits.py`
> commitado DENTRO da sombra), porque a W1 e a fable51 tocam `scripts/upgrade.sh`
> (hunks textualmente disjuntos — as 34 âncoras casam 1× nas duas bases medidas,
> `dc72bf1` e `f0e98de`). O `HEAD` andou DUAS vezes durante a noite
> (`dc72bf1` → `6160578` → `f0e98de`); a sombra foi re-derivada na base nova e a
> bateria final é a da base nova (EVIDENCE.md).
>
> **Pack:** `.claude/plans/PLAN-183/s338-w1-draft/` — este desenho,
> `apply-w1-edits.py` (a derivação: 36 edições em 12 paths, `--check-only`,
> `--list-paths`, `--control-no-cure`), `EVIDENCE.md`, `codex-r1..3.txt` +
> `rail-round-1..3.md` (3 rodadas, teto: 1 P1 + 3 P2 → 2 P1 + 1 P2 → 1 P1 +
> 2 P2; 10 achados reais, 7 curados na sombra, 1 deferido = OQ-3, 2 ABERTOS com
> cura escrita — **último veredito: CHANGES-REQUESTED**, nenhuma rodada limpa).
> Sombra final: ver EVIDENCE.md §0.

---

## 0. O que a W1 fecha, em uma frase por item

| # | Item aberto do plano (§W1) | Mecanismo (verbatim) | Estado no draft |
|---|---|---|---|
| 1 | `[P0]` relativização DENTRO de `_render_protocol_pointer` | ramo `*)` → `_rpp_relpath "$_rpp_target" "$_rpp_psource"` → `_render_protocol_pointer_portable` | **PROVADO** (R10, R13, P1a/P1b, P2a) |
| 2 | `[P0]` remediação retroativa («absoluto legado») | `_render_protocol_pointer_legacy` (CONGELADO) + `_protocol_pointer_legacy_source` + `live_content=legacy_absolute` → `REFRESH HASH_CANONICAL_POINTER` com backup em `$BAK_DIR` | **PROVADO** (L5/L5b, P3a–P3e com a release REAL `v1.3.0`, R11, R12) |
| 3 | `[x]` interface existente `--protocol-source`/`CEO_PROTOCOL_SOURCE` | **descoberta:** `upgrade.sh` NÃO aceitava o par; o reparo não existia. Draft: precedência 0 + persistência em `request.placeholders.PROTOCOL_SOURCE` | **PROVADO** (P2f, P2g); **decisão de escopo para o debate** (OQ-2, OQ-4) |
| 4 | `[P0]` o corpo NOMEIA a interface | template portátil carrega a receita `rm PROTOCOL.md && <ceo-orchestration>/scripts/upgrade.sh . --protocol-source <ceo-orchestration>` | **PROVADO** (R10, P2c) |
| 5 | `[P1]` preservação AVISADA | `_ptr_warn_portability` — (a) path ABSOLUTO no corpo, (b) checkout nomeado NÃO resolve; chamado nos ramos `PRESERVE_OWNED` (editado e carried-forward) e depois de `DELIVER\|REFRESH` | **PROVADO** (P4a/P4b, P2e; controle negativo P1d) |
| 6 | `[P0]` INV-4 preservado | `assert_sound()` passa a exigir RESOLUÇÃO por caminho RELATIVO a partir do target (o path absoluto vira FALHA); L5 novo | **PROVADO** 5/5; controle pré-cura VERMELHO |

Bateria final na sombra e controles positivos: **EVIDENCE.md**. Números da
sombra na base `f0e98de`+fable51 (derivação r5, pós-rail r2): render **18/18**,
`test-ownership-verdict-unit.sh` **66/0** (2 skips de fault, pré-existentes),
INV-4 e e2e portátil: EVIDENCE §5 (r4 media 5/5 e 20/20 em 324 s),
`shellcheck -S warning` **0** nos 7 `.sh` tocados, YAML dos 2 workflows
parseia, censo PLAN-185 **rc 0** com o baseline re-gerado pelo próprio censo.
Controle positivo (árvore sem cura): render 4 RED (incl. R15), unit 1 RED
(`OWN-0096`), INV-4 4 legs RED, e2e 11 RED.

---

## 1. O problema, redito com o que se mediu

O corpo fora-do-target do ponteiro (`_render_protocol_pointer`, ramo `*)`) era
`degraded | sed s|{{PROTOCOL_SOURCE}}|<valor>|g`, e o valor era o `$SOURCE_DIR`
ABSOLUTO do install (`install.sh` :701 `PH_PROTOCOL_SOURCE="$SOURCE_DIR"`). Três
consequências, todas verificadas na sombra:

1. **Morte por mudança de casa.** `mv /home/alice /home/bob` mata o ponteiro
   (P1b pré-cura: não resolve). A relação entre os dois diretórios era a única
   coisa portátil e não estava codificada.
2. **Contaminação (o gatilho do A1).** O path absoluto embarca o `$HOME` do
   mantenedor em toda árvore de adopter — o `Contamination check` estava CERTO.
3. **Corpo que mente.** Depois da substituição a linha «Edit
   `{{PROTOCOL_SOURCE}}` to point at your checkout» virava «Edit
   /Users/x/ceo-orchestration to point at…» — instrução sem sentido e sem a
   flag que já existia (`grep -- --protocol-source` no corpo = 0, medido S328).

E uma consequência que o plano NÃO nomeava e que o draft mediu: **o reparo não
existia.** `install.sh` faz early-return se `$TARGET/PROTOCOL.md` existe
(`install_protocol_pointer`, `if [[ -e "$TARGET/PROTOCOL.md" ]]; then return 0`),
e `upgrade.sh` não aceitava `--protocol-source` nem `CEO_PROTOCOL_SOURCE` (0
ocorrências em `scripts/upgrade.sh` no HEAD; só a CHAVE `PROTOCOL_SOURCE` lida do
install-state). Logo «nomear a interface no corpo» (item 4) exigia CRIAR a
metade que faltava da interface no upgrade — ou o corpo nomearia uma flag que
não existe para o comando que ele recomenda. É a maior descoberta do draft e a
principal decisão que o debate precisa ratificar (OQ-2/OQ-4).

---

## 2. Mecanismo, item a item

### 2.1 Relativização DENTRO de `_render_protocol_pointer` (item 1)

**Onde:** `scripts/_framework_manifest_set.sh`, ramo `*)` de
`_render_protocol_pointer SOURCE_DIR TARGET PROFILE STACK PROTOCOL_SOURCE`.
O ramo dentro-do-target (`"$_rpp_target"/*`, chaveado por `$1=SOURCE_DIR`) fica
**INTACTO** — já era relativo (`./vendor/ceo`).

**O que muda:**

```sh
*)
  case "$_rpp_psource" in
    *"$_RPP_NL"*)   _render_protocol_pointer_degraded "$_rpp_target" "$_rpp_profile" "$_rpp_stack" ;;   # guarda W3.1 mantida
    *)
      if _rpp_rel="$( _rpp_relpath "$_rpp_target" "$_rpp_psource" )"; then
        _render_protocol_pointer_portable "$_rpp_rel" "$_rpp_profile" "$_rpp_stack"
      else
        _render_protocol_pointer_portable "$_rpp_psource" "$_rpp_profile" "$_rpp_stack"   # VERBATIM
      fi ;;
  esac ;;
```

**`_rpp_relpath FROM TO`** — função PURA e LEXICAL (zero acesso a filesystem, o
render continua função só dos inputs). Aceita só absolutos e lexicalmente limpos
(sem `.`/`..`, sem `//`, sem a raiz; uma barra final é tolerada); qualquer outra
coisa ⇒ `rc=1` e o chamador mantém o valor **VERBATIM** — a forma antiga,
sempre correta em casa (falha para o comportamento seguro, não para um render
errado). Casos pinados em R13: irmão `../ceo`, aninhado `./vendor/ceo`,
`/a/app`→`/a/app2` = `../app2` (a barra final impede o falso prefixo), não
relacionado `../../../../opt/ceo`, mesmo dir `.`, e cinco recusas (relativo,
`~`, `..`, `//`, vazio). Provado em bash 3.2 (`/bin/bash` do macOS), bash 5 e
`sh`.

**Por que a fonte relativa vira VERBATIM e não é recusada:** `--protocol-source
../ceo` ou `~/src/ceo` é escolha do adopter e já é portátil no sentido que ele
quis; `~` inclusive viaja de usuário para usuário. Só o ABSOLUTO é re-escrito.

**Normalização — o achado do rail r2 (P1), e a regra que fica.** `install.sh`
(:682) e `upgrade.sh` (:732) normalizam `TARGET` com `pwd` LÓGICO; mas os `..`
que o ponteiro emite são resolvidos FISICAMENTE pelo kernel a partir do
diretório REAL do arquivo. Um target alcançado por symlink que muda a
profundidade (`/tmp/x/s -> /tmp/x/deep/root`) recebia de um relpath lexical
`../../deep/root/ceo` — morto do diretório físico; e no macOS `install.sh
/tmp/app` a partir de `/Users/me/ceo` daria `../../Users/me/ceo` ⇒
`/private/Users/me/ceo` — morto no caso mais comum. Reproduzido com a própria
função (EVIDENCE §1). Regra: para fonte ABSOLUTA, os DOIS lados são levados a
FÍSICO (`cd … && pwd -P`) antes de `_rpp_relpath`; fonte relativa/`~` fica
verbatim (um `cd` a resolveria contra o diretório errado); lado inexistente ⇒
fonte VERBATIM (absoluta, sempre correta em casa). `_rpp_relpath` segue pura;
a normalização vive no ramo `*)` do gerador. R15 pina o caso (symlink de
profundidade ⇒ `../ceo`, resolve); `cd`/`pwd` são read-only para o censo.
Consequência boa: com os dois lados físicos, o relpath é o mais CURTO possível
(`../ceo` em vez de `../../private/tmp/ceo`) — mais portátil, não menos.

**A descoberta que muda o escopo: `install.sh` tem de mudar.** Hoje o install
escreve o corpo DEGRADADO (`_render_protocol_pointer_degraded`) e deixa o pass de
placeholders (`_add_sub "PROTOCOL_SOURCE" "$PH_PROTOCOL_SOURCE"`, :2743) fazer a
substituição — isso só produzia o MESMO byte que o upgrade porque valia a
identidade R2 (`degraded | sed == healthy`). A relativização quebra a identidade
por construção (o plano já dizia isso em §7.1 #1). Sem tocar o install, INV-4 L1
fica VERMELHO (install absoluto ≠ upgrade relativo). Cura: UMA chamada,

```sh
_render_protocol_pointer "$SOURCE_DIR" "$TARGET" "$PROFILE" "$STACK" "$PH_PROTOCOL_SOURCE" > "$TARGET/PROTOCOL.md"
```

e o pass de placeholders não encontra mais token nesse arquivo (o arquivo segue
na lista, :2820/:2911 — no-op). É exatamente «o gerador decide, o call-site não»
— e o `case` que o install tinha ERA um call-site decidindo. R1 (render ==
saída real do install) e INV-4 L1/L2 provam a identidade nova. **Consequência de
cerimônia:** `scripts/install.sh` é canônico (oráculo `1`) e entra no escopo
GPG junto com `upgrade.sh` e `_framework_manifest_set.sh` (OQ-4).

### 2.2 O template portátil e o corpo que nomeia a interface (item 4)

`_render_protocol_pointer_portable REL PROFILE STACK` — `printf` puro (sem
`sed`, sem classe de escaping), ASCII puro (vai para o arquivo do adopter):

```
# Protocol reference

The full CEO orchestration protocol lives at:
<REL>/PROTOCOL.md

If that path stops resolving (this project or the framework checkout
moved), re-point it from this directory; the flag is the one install.sh
takes:
  rm PROTOCOL.md && <ceo-orchestration>/scripts/upgrade.sh . --protocol-source <ceo-orchestration>

To pull updates:
  ( cd <REL> && git pull )
  <REL>/scripts/upgrade.sh . --profile <PROFILE> --stack <STACK>
```

Três escolhas deliberadas, cada uma com razão:

- **`.` no lugar de `$TARGET` na linha de upgrade.** O template antigo embarcava
  o TARGET ABSOLUTO (`{{PROTOCOL_SOURCE}}/scripts/upgrade.sh $_rppd_target …`) —
  a receita «pull updates» morria junto com a mudança de casa, e o corpo
  continuava carregando path de máquina. O ramo dentro-do-target já usava `.`
  com a mesma premissa (cwd = diretório do ponteiro, como o `cd <REL>` da linha
  anterior exige). Resultado: **zero paths absolutos no corpo** (R10, P1a, P2a,
  P3c asseridos por `grep -Eq '(^|[[:space:]])/[^[:space:]]'`).
- **A receita com `rm PROTOCOL.md`.** É a ÚNICA receita verdadeira sob a
  doutrina D3 do PLAN-168 («never silently rename a sound pointer»): um ponteiro
  com a forma do framework mas relação quebrada classifica como `edited` e é
  PRESERVADO; o reparo passa por `absent` ⇒ `DELIVER HASH_CANONICAL_POINTER`
  (Stage C de `_ownership_verdict`, sem branch novo). P2f executa a receita
  literalmente (`cd $X2 && rm PROTOCOL.md && upgrade.sh . --protocol-source …`)
  e o ponteiro volta a resolver. A alternativa sem `rm` exige uma classe
  `stale_render` que muda PRESERVE→REFRESH — reabre S238 e é decisão de debate
  (OQ-2).
- **`<ceo-orchestration>` como placeholder de prosa** (convenção de doc de CLI),
  nunca um path real — o corpo não pode voltar a carregar máquina.

O ramo dentro-do-target NÃO ganha o parágrafo de reparo (não pode quebrar por
mudança de casa; população ~0; unificar exigiria reconhecedor da forma antiga
dentro-do-target — OQ-6).

### 2.3 Remediação retroativa: «absoluto legado» (item 2)

**Template CONGELADO.** `_render_protocol_pointer_legacy PROTOCOL_SOURCE TARGET
PROFILE STACK` = exatamente `degraded | sed` — o corpo que o ramo `*)` produzia
antes da W1 e que o pass de placeholders do install produziu de v1.0.1 a v1.3.0
(o cabeçalho da lib já registra o template idêntico nas quatro versões). R2 deixa
de pinar «degraded|sed == healthy» (agora FALSO por desenho) e passa a pinar
«degraded|sed == legacy» — a identidade sobrevive como DEFINIÇÃO do legado, e
R2b pina a outra metade (healthy ≠ legacy). **P3b é a prova de campo:** a
saída REAL do `install.sh` de `v1.3.0` (`git archive` da tag, install de
verdade) é aceita byte-a-byte pelo reconhecedor — o template congelado é o que
foi shipado, não uma aproximação.

**Reconhecedor.** `_protocol_pointer_legacy_source FILE` — `rc=0` **e imprime o
checkout que o arquivo nomeia** iff FILE é byte-idêntico a um render legado cujos
valores vêm TODOS do próprio arquivo: fonte da 4ª linha (`^(..*)/PROTOCOL\.md$`),
`TARGET/PROFILE/STACK` da linha de upgrade (`<fonte>/scripts/upgrade.sh <T>
--profile <P> --stack <S>`) por split **ancorado à direita** em expansão de
parâmetro (`##* --stack `, `% --stack *`, `##* --profile `, `% --profile *`) —
checkout e TARGET podem conter ESPAÇOS, porque o install antigo os escrevia
verbatim (rail r1 P2; R11d); reconstrução via `_render_protocol_pointer_legacy`
canalizada para `cmp -s -` — **sem arquivo temporário** (rail r1 P2: um `TMPDIR`
dentro do `$TARGET` poria scratch no repo do adopter, `--dry-run` incluído; o
irmão `_protocol_pointer_is_degraded` ainda usa `mktemp` — FU, fora do escopo).
Mesma disciplina do degradado: qualquer falha de parse, qualquer edição ⇒
`rc=1` (R12; P4c) — falha para PRESERVAÇÃO. Um corpo com o token literal é
`degraded`, nunca legado (R11c; o chamador checa `degraded` primeiro). Um corpo
portátil não é legado (R11b — sem isso o framework re-renderizaria para sempre).

**Regra de consistência (rail r1 P1).** O reconhecedor roda UMA vez em
`_refresh_protocol_pointer` (guardando `_ptr_leg` e `_ptr_leg_ok` =
`_ptr_source_value_ok "$_ptr_leg"`), e o OBSERVE só classifica
`legacy_absolute` quando o valor que SERÁ renderizado é o do próprio arquivo
(`_ptr_leg_ok`) ou o explícito aceito (`_ptr_explicit_ok`). Sem isso, um legado
byte-exato cujo checkout tem `+`, `@`, `:` ou não-ASCII (recusado pelo allowlist
R-SEC8) era reconhecido no OBSERVE mas descartado na resolução, caía em
`$SOURCE_DIR` e a «cura» re-apontava o ponteiro para OUTRO checkout. Agora:
valor não representável e sem flag ⇒ `edited` ⇒ PRESERVED + WARNING (a) —
nunca re-point por fallback.

**Definição da classe (decisão do draft, OQ-1):** «legado» é a FORMA (template
pré-W1, reconhecível pelo TARGET absoluto na própria linha de upgrade), qualquer
que seja o valor da fonte. A população shipada é toda absoluta (o default era
`$SOURCE_DIR`), daí o nome do plano; um `--protocol-source ../x` passado ao
install antigo também produzia essa forma e também merece a migração de forma.

**Rota e precedência.** Em `_refresh_protocol_pointer`:

- OBSERVE: `degraded` → **`legacy_absolute`** (novo `elif
  _protocol_pointer_legacy_source "$pointer" >/dev/null`) → `pristine` →
  `edited`. Só é alcançado quando `_lt = regular` (o `if [ "$_lt" != "regular" ]`
  vem antes) — nunca lê através de symlink.
- DECIDE: `_ownership_verdict … legacy_absolute …` — Stage B ganha
  `|| [ "$_ov_lcontent" = "legacy_absolute" ]` no `elif` de `degraded`
  (owned mesmo sem registro, doutrina content-proven; controle positivo:
  sem a edição `OWN-0096` sai `PRESERVE_UNOWNED HASH_NONE`, medido).
  Nenhuma outra linha da função muda: prior=`hash` já era owned, Stage C já
  dava `REFRESH HASH_CANONICAL_POINTER`, A2 (user) já dava
  `PRESERVE_OWNED HASH_PRIOR_RECORD`.
- EXECUTE: o ramo `DELIVER|REFRESH` existente (backup-always em `$BAK_DIR`,
  `printf '%s\n' "$_ptr_full" > "$pointer"`) — **nenhum sítio de escrita novo**;
  mensagem própria `CURED: PROTOCOL.md pointer was the pre-PLAN-183 absolute form
  — re-rendered in the portable form …` (L5, P3d asserem a ROTA, não só os
  bytes; L5b/P3e asserem o backup byte-exato).
- **Precedência 0.5 (a decisão de VALOR):** o legado mantém o checkout que ELE
  nomeia — `_ptr_psource="$( _protocol_pointer_legacy_source "$pointer" )"`
  (quando passa o allowlist) vem ANTES do install-state. Só a FORMA migra.
  Re-renderizar pelo valor gravado transformaria migração de forma em re-point
  silencioso (S238) no caso em que arquivo e state discordam. Na população
  shipada eles concordam (o install gravou os dois), então o efeito prático é
  nulo e a proteção é para o caso raro. P3c: pós-upgrade o ponteiro nomeia o
  MESMO checkout (a árvore `v1.3.0`), agora relativo.

**Check do plano («instalação com a versão ANTERIOR → upgrade → relativo»):**
P3 é literalmente isso, com a release derivada (`git tag --sort=-v:refname`,
sem `-rc`), nunca hardcoded; checkout sem tags ⇒ `exit 2` (erro de harness),
nunca verde.

### 2.4 A interface no upgrade (item 3 — o que faltava)

`scripts/upgrade.sh` ganha o MESMO par do install: `--protocol-source <path>`
(arg-parser, antes de `--pin`) e `CEO_PROTOCOL_SOURCE` (default de
`PROTOCOL_SOURCE_FLAG`), documentados no `--help`. Semântica:

- **Precedência 0** em `_refresh_protocol_pointer`, acima do install-state;
  filtrada por `_ptr_source_value_ok` — o gêmeo bash do allowlist POSITIVO do
  filtro python do install-state (R-SEC8: `[A-Za-z0-9._/ ~-]{1,512}`, sem `{{`,
  sem newline). Valor rejeitado ⇒ WARNING nomeado e cai na precedência gravada
  (nunca silêncio, nunca abort).
- **Persistência** em `request.placeholders.PROTOCOL_SOURCE` via
  `_write_upgrade_state` (par `protocol_source` + 6 linhas no python inline),
  SÓ quando explícito e aceito (`_PTR_SOURCE_PERSIST`); nunca o valor inferido.
  P2g lê o JSON de volta. Sem isso, o upgrade seguinte voltaria ao valor velho.
- **Não é env nova** — é a metade que faltava do par que o item 3 manda reusar;
  o Check por propriedade («nenhuma env alternativa em `scripts/`») segue
  verdadeiro por construção.
- **SPEC/v1/install-cli.md** enumera os flags do `upgrade.sh` (`--pin`,
  `--dry-run`, `--skip`, `--purge-misinstalled`) e é canônica com deny-edit —
  a linha do flag novo entra na MESMA cerimônia ou o contrato publicado
  diverge do binário (OQ-9). Não está no draft.

### 2.5 Preservação AVISADA (item 5)

`_ptr_warn_portability FILE` (definida antes de `_refresh_protocol_pointer`),
ADVISORY, read-only, nunca muda veredito; recusa symlink/não-regular antes de
ler (`[ -L ] || [ ! -f ] ⇒ return 0`). Duas condições NOMEADAS, cada uma com a
receita de reparo:

- **(a)** o corpo carrega path ABSOLUTO (`grep -Eq '(^|[[:space:]])/[^[:space:]]'`)
  ⇒ «will not survive moving this project to another home or user» + receita
  (P4b; o corpo portátil nunca dispara — P1d/P2a/P3c).
- **(b)** o checkout nomeado NÃO resolve a partir do target (relativo ⇒
  `$TARGET/<named>/PROTOCOL.md`; absoluto ⇒ `<named>/PROTOCOL.md`; `~`/token
  ⇒ não sonda) ⇒ «moved alone … re-point it with» + receita (P2e). É o «erro
  NOMEADO que conduz ao reparo» do plano — o framework não adivinha para onde o
  checkout foi. O valor nomeado NUNCA é ecoado (texto de arquivo do adopter).

Chamada em três pontos: `PRESERVE_OWNED` editado (depois do `PRESERVED (root
PROTOCOL.md is adopter-customised …)` — a string preservada intacta, nenhum
consumidor quebra), `PRESERVE_OWNED` carried-forward (`SKIP … ownership carried
forward` — um ponteiro pristine cuja FONTE se mudou sozinha também é avisado),
e depois da escrita em `DELIVER|REFRESH`. Nunca em `--dry-run` de escrita
(o ramo retorna antes) e nunca nos ramos `PRESERVE_UNOWNED`.

### 2.6 INV-4 preservado (item 6)

`test-protocol-pointer-inv4.sh::assert_sound()` exigia `grep -F -q
"$REPO_ROOT/PROTOCOL.md"` — o path ABSOLUTO PRESENTE (o plano §7.1 #2 já
media: «o Check é insatisfazível como escrito»). Passa a: token ausente; a 4ª
linha nomeia `<checkout>/PROTOCOL.md`; o valor NÃO é absoluto (absoluto ⇒
FAIL nomeado «pre-W1 form — not portable»); `$T/<named>/PROTOCOL.md` existe e
`pwd -P` dele == `pwd -P` do `$REPO_ROOT`. Resolução é o invariante,
absolutez é o defeito. L1–L4 intactos na semântica (byte-identidade,
idempotência, cura do degradado com backup, preservação do editado); **L5**
planta `_render_protocol_pointer_legacy "$REPO_ROOT" "$T" core generic` e
exige cura pela rota legada + backup byte-exato. Controle positivo (árvore
sem cura): L1 falha em `assert_sound` (absoluto), L5 falha «NOT cured».

---

## 3. Os testes que os Checks exigem — onde vivem

| Check (plano) | Teste / leg | Resultado sombra | Controle sem cura |
|---|---|---|---|
| e2e move source+target JUNTOS ⇒ resolve | `test-protocol-pointer-portable.sh` P1a–P1d | PASS | P1a/P1b RED |
| e2e move target SOZINHO ⇒ corpo conduz ao reparo nomeando `--protocol-source` | P2a2 (valor gravado = checkout do install), P2b, P2c, P2d, P2e, **P2f (executa a receita)**, P2g (valor persistido MUDOU) — o P2 instala a partir da CÓPIA MOVIDA do P1 para que o reparo aponte a um checkout DIFERENTE do gravado; sem isso P2g era vácuo (achado do controle) | PASS | P2c/P2e/P2f/P2g RED (`--protocol-source` desconhecido no upgrade antigo) |
| install com versão ANTERIOR → upgrade ⇒ relativo | P3a–P3e (`v1.3.0` real) | PASS | P3c/P3d RED |
| corpo contém `--protocol-source` | render R10; P2c | PASS | RED |
| ponteiro absoluto editado sobrevive E WARNING aparece | P4a, P4b, P4c | PASS | P4b RED |
| `test-protocol-pointer-inv4.sh` verde | L1–L5b | 5/5 | L1/L5 RED |
| um template (agora: template LEGADO congelado) | render R2, R2b | PASS | R2b RED |
| reconhecedor disjunto / falha para preservação | R11a–c, R12 | PASS | R11b RED |
| decisão da tabela | `test-ownership-verdict-unit.sh` 66/0 | PASS | `OWN-0096` RED |

Duração medida do e2e novo: **316–327 s** (macOS, 4 installs + 5 upgrades +
1 cópia do checkout sem `.git`/`.claude/plans` ≈ 60 MB, concorrente com o
INV-4 e com o rail). Fiado no `ownership-nightly.yml` (r5); promoção a per-PR
é residual da OQ-5. A fixture da «release anterior» é DERIVADA por conteúdo
(tag não-rc mais nova cujo gerador ainda não tem `_render_protocol_pointer_portable`)
— sobrevive à própria release da W1 (rail r2 P2); a `v1.2.0` real, única tag que
o nightly busca, produz corpo aceito byte-exato pelo reconhecedor (sondado).

| Check (plano) | Teste / leg | Resultado sombra | Controle sem cura |
|---|---|---|---|
| target através de SYMLINK de profundidade ⇒ o render resolve (rail r2 P1) | render R15 | PASS (`../ceo`) | RED (também RED na lógica lexical do r4, reproduzido com a própria função) |

**Consumidores de string verificados** (grep em `scripts/tests/`,
`.claude/scripts/tests/`, `.claude/hooks/tests/`): só `inv4:104` casa `CURED:
PROTOCOL.md` — preservado (o legado tem prefixo igual e sufixo próprio; L5/P3d
casam o sufixo). `_parity_classify.py:144-150` declara a classe «PROTOCOL.md
body-only divergence» com TEXTO pré-PLAN-168 (fala do token literal) — com a W1
install e upgrade produzem o MESMO byte; a declaração fica stale mas não é gate
(OQ-8).

---

## 4. A tríade de ownership (artefatos 3–7 do §7.1)

| Artefato | Mudança | Oráculo |
|---|---|---|
| `scripts/tests/ownership_table.tsv` | +3 linhas espelhando `OWN-0092/0093/0094`: `OWN-0095` (hash, maintainer, upgrade ⇒ `REFRESH HASH_CANONICAL_POINTER`), `OWN-0096` (none, maintainer, upgrade ⇒ `REFRESH HASH_CANONICAL_POINTER` — takeover content-proven), `OWN-0097` (hash, user, upgrade ⇒ `PRESERVE_OWNED HASH_PRIOR_RECORD`, WS4). `note` só prosa, sem apóstrofo, origin `plan-183` | 0 |
| `docs/ownership-decision-table.md` | enum §2.4 ganha `legacy_absolute`; parágrafo de doutrina (terceira aplicação da reconstrução por template); **R-04c** `live_content=legacy_absolute ⇒ surface=protocol`, irmã de R-04b — sem a regra a linha seria ILEGAL pela §4 | 0 |
| `scripts/tests/test-ownership-table.sh` | pré-check de `_render_protocol_pointer_legacy`; ramo `legacy_absolute)` em `_mutate_surface` renderizando `_render_protocol_pointer_legacy "$src_root" "$T" core generic` (o gerador CONGELADO, nunca fixture à mão; valor = a fonte desta corrida, como um install antigo gravaria) | 0 |
| `scripts/_framework_manifest_set.sh::_ownership_verdict` | Stage B: `degraded \|\| legacy_absolute` (uma condição, comentário R-04c) | **1** |
| `scripts/tests/ownership-baseline-map.txt` | **NÃO re-gravado.** Exige a corrida de ~25 min (`test-ownership-table.sh --stable-header`), que este draft NÃO executou — deliberadamente, e dito aqui: o mapa deriva em silêncio até a corrida real; as 3 linhas novas aparecerão nele | 0 |
| `scripts/tests/ownership-expected-reds.txt` | **NÃO editado.** Previsão: inalterado (`OWN-0016/0024/0027`); as linhas novas devem sair GREEN — o oráculo de DECISÃO já as prova (66/0) e o harness tem o ramo. Se a nightly mostrar QUALQUER diferença (linha nova vermelha, ou o reconhecedor fechando `OWN-0016` por acidente — impossível por surface, mas é o que se re-verifica), a edição entra no MESMO commit; corrida toda-verde ⇒ PARAR (CLAUDE.md §4) | 0 |

`OWN-0011/0014/0071/0072` não viram: o harness define `pristine` do `protocol`
como «a própria saída do install base» e não toca o arquivo (`:374-380`) —
como o §7.1 #3 previa. Nenhum digest fixado no TSV (medido no §7.1).

---

## 5. Classificação canônica dos paths tocados (oráculo `check_canonical_edit.py --is-canonical`)

| Path | Oráculo | Nota |
|---|---|---|
| `scripts/_framework_manifest_set.sh` | **1** | gerador, relpath, template legado, reconhecedor, Stage B |
| `scripts/upgrade.sh` | **1** | flag/env, precedências 0 e 0.5, OBSERVE, avisos, persistência |
| `scripts/install.sh` | **1** | UMA chamada ao gerador (INV-4) — **fora do brief, exigido pela identidade R2** |
| `scripts/tests/test-protocol-pointer-render.sh` | 0 | R2/R2b, R10–R13, contagem `$PASSES` |
| `scripts/tests/test-protocol-pointer-inv4.sh` | 0 | `assert_sound`, L5 |
| `scripts/tests/test-protocol-pointer-portable.sh` | 0 | **NOVO**, modo 0755 como os irmãos |
| `scripts/tests/ownership_table.tsv` | 0 | +3 linhas |
| `scripts/tests/test-ownership-table.sh` | 0 | ramo novo |
| `docs/ownership-decision-table.md` | 0 | enum + R-04c |
| `.claude/scripts/data/installer-write-safety-baseline.txt` | 0 | RE-GERADO pelo censo (pós-passo do script) |
| `.github/workflows/ownership-nightly.yml` | **1** | step «Protocol pointer portable e2e (PLAN-183 W1)» após o INV-4 (rail r2 P1: «unwired = no test») |
| `.github/workflows/smoke-install.yml` | **1** | só os dois `paths:` filters (espelho da linha do INV-4); nenhum step — a promoção a per-PR é o residual da OQ-5 |
| `SPEC/v1/install-cli.md` | 1 | **NÃO tocado** — documentar o flag é OQ-9 |

**Cinco canônicos** ⇒ cerimônia GPG (SIGN/LAND) do Owner, não escrita neste
pack. (O brief nomeava dois; a identidade R2 trouxe o `install.sh`, e a regra
«unwired = no test» do próprio `smoke-install.yml:30-34` trouxe os dois
workflows — OQ-4.)

**Ratchet PLAN-185 (censo):** o baseline é chaveado por NÚMERO DE LINHA, e a W1
desloca `install.sh`, `upgrade.sh` e `_framework_manifest_set.sh` ⇒ re-geração
inteira (mesmo patch, pelo próprio censo, `--write-baseline`, no pós-passo do
`apply-w1-edits.py` — nunca à mão). Delta por CONTEÚDO (ignorando linha), r4:
676 → 681 entradas. `install.sh` −2 sítios (`:2639`/`:2642` `desguardado`) +1
(a chamada única, mesma classe — dominada por `_dst_refuses`, ponto cego FU-1
do censo); `_framework_manifest_set.sh` +3, todos no reconhecedor legado: o
`[ -f ]` e a linha do pipeline `_render_protocol_pointer_legacy … | cmp -s -`
(contada 2× pelo censo, `indeterminado`) — **sem `mktemp` nem `> "$tmp"`**
depois do rail r1; `upgrade.sh` +4/−1: os `-f` das precedências e da função de
aviso (todos precedidos de `! -L` na mesma expressão — o censo não modela o
`&&` como guarda, classe FU-1) e a linha do install-state que ganhou o
`[ -z "$_ptr_psource" ]`. **Nenhum sítio novo escreve no `$TARGET`** e nenhum
escreve scratch em lugar nenhum; a única escrita no target continua sendo a
linha `printf '%s\n' "$_ptr_full" > "$pointer"` pré-existente.

---

## 6. Riscos (o que a cura pode reabrir) e como o draft os fecha

| Risco | Mitigação medida | Residual |
|---|---|---|
| **Reabrir INV-4** (PLAN-168): install ≠ upgrade | `install.sh` chama o gerador; R1 (render == install real) + L1/L2 | nenhum medido |
| **S238 clobber** via falso-positivo do reconhecedor legado | reconstrução byte-exata; R12 (1 char ⇒ preservado), P4a/P4c (editado ⇒ PRESERVED); espaços em checkout/target parseiam (R11d) | valor nomeado fora do allowlist R-SEC8 ⇒ `edited` ⇒ PRESERVED + WARNING, sem cura automática (OQ-7) |
| **Re-point silencioso** pela cura legada (rail r1 P1) | `legacy_absolute` só quando o valor a renderizar é o do arquivo ou o explícito; nunca `$SOURCE_DIR` por fallback | nenhum medido |
| **Reabrir a decisão D3** (precedência Owner) | só a precedência 0 (explícita) e a 0.5 (legado byte-exato, valor do PRÓPRIO arquivo) entram; state → sound → SOURCE_DIR inalterados | OQ-3 (state absoluto pós-move) |
| **`set -e` mid-upgrade** (classe W3.1) | novos `$( )` só em contexto de condição; allowlist antes de qualquer uso; `sed` só no template legado CONGELADO com o escaping antigo | nenhum medido |
| **Escrita fora do `$TARGET`** (PLAN-185) | zero sítios novos no target; helpers recusam `-L` antes de ler; censo rc 0 | ratchet re-gerado (dito acima) |
| **Corpo do adopter com `rm`** | é o ponteiro gerado, re-entregue pelo framework; alternativa é OQ-2 | decisão de UX para o debate |
| **Allowlist ASCII-only** (herdada do R-SEC8) | `--protocol-source /Users/joão/…` ⇒ WARNING nomeado + precedência gravada | mesma classe que o filtro do state já tinha (OQ-7) |
| **Ownership e2e (25 min) não rodado** | oráculo de decisão 66/0 + ramo do harness + P3 real | mapa-baseline e expected-reds só fecham na nightly (§4) |
| **CI não fiado** | e2e novo roda local (5 min) | OQ-5 |
| **Texto stale** em `_parity_classify.py` | não é gate | OQ-8 |

---

## 7. Orçamento (declarado)

- **Já gasto no draft (esta noite):** 1 sessão autônoma; ~4 derivações da
  sombra; 2 bases (`HEAD` andou); bateria local ≈ 12 min por rodada (e2e novo
  5 min + INV-4 4 min + render/unit/censo < 1 min, em paralelo); 1+ rodada de
  pair-rail (EVIDENCE.md). Tokens: leitura dirigida ≈ 30k (§7.2 previa 12–18k
  por iteração + 28k de superfície SETE — coerente).
- **Para a wave real (depois do debate):** 1 cerimônia GPG com **5 canônicos**
  (`_framework_manifest_set.sh`, `upgrade.sh`, `install.sh`,
  `ownership-nightly.yml`, `smoke-install.yml`; + `SPEC/v1/install-cli.md` se
  OQ-9 for SIM ⇒ 6); **1 corrida nightly de ownership (~25 min) obrigatória** para re-gravar
  `ownership-baseline-map.txt` e re-verificar `ownership-expected-reds.txt` —
  local, como pré-condição (§7.2: «`budget_sessions: 3-5` só se sustenta se o
  e2e rodar LOCAL»); 2–4 rodadas de rail sobre a sombra re-derivada
  (regra S329: sombra re-derivada ganha o rail inteiro). Estimativa honesta:
  **90–150k tokens, 2–3 sessões**, dentro do frontmatter re-declarado da W1.
- **O que NÃO entra:** unificar o ramo dentro-do-target (OQ-6), `stale_render`
  (OQ-2), gravar relativo no install-state (OQ-3), UTF-8 no allowlist (OQ-7).

---

## 8. Open questions — a agenda do `/debate` (L3)

- **OQ-1 — Nome e extensão da classe.** `legacy_absolute` por FORMA (template
  pré-W1, qualquer valor de fonte — recomendação do draft) **ou** exigir fonte
  absoluta (classe mais estreita; deixa fora a população que passou
  `--protocol-source` relativo ao install antigo, que ficaria `edited` +
  WARNING (a) para sempre por causa do TARGET absoluto na linha de upgrade).
- **OQ-2 — Receita de reparo com `rm` vs classe `stale_render`.** Sob D3 um
  ponteiro com a forma do framework e relação quebrada é `edited` ⇒ PRESERVE; o
  reparo passa por `absent ⇒ DELIVER`. A alternativa — `stale_render` (forma
  corrente, valores ≠ canônico) ⇒ REFRESH quando `--protocol-source` explícito
  — dá reparo sem `rm`, mas acrescenta ou uma dimensão («fonte asserida») ao
  espaço de ownership ou um veredito PRESERVE→REFRESH que reabre S238.
  Recomendação: `rm` na W1; `stale_render` como wave própria se o Owner quiser.
- **OQ-3 — Install-state ABSOLUTO depois de mover os dois juntos (o rail r3
  confirmou como P1).** Medido em P1c/P1d: o upgrade a partir do checkout
  movido renderiza pelo state velho (relação diferente), classifica o ponteiro
  CORRETO como `edited`, imprime «PRESERVED (adopter-customised)», rc 0,
  byte-idêntico, sem WARNING falso. Seguro (nenhum dado se perde), mas a
  mensagem engana, cada upgrade faz backup, o digest canônico gravado é o
  errado e o ponteiro sai da manutenção do framework (mudanças futuras do
  template não chegam). Opções: (a) install grava o valor RELATIVO em
  `request.placeholders` (muda o contrato do state e `ph.PROTOCOL_SOURCE`); (b)
  precedência «ponteiro são que RESOLVE vence state contradito» (emenda
  explícita à ordem D3 do Owner — o codex recomenda esta ou o re-base do
  state); (c) aceitar. Recomendação: (b), ratificada no debate e executada NA
  W1 (não em wave própria, dado o P1): a W1 fecha os Checks sem ela, mas
  entrega um ponteiro que o framework deixa de manter depois da própria
  mudança de casa que o motivou.
- **Achados ABERTOS do rail r3 (P2, cura escrita em `rail-round-3.md`, não
  aplicados pelo teto de rodadas):** (i) `_ptr_warn_portability` tem UMA
  atribuição `$( sed … | sed … )` sem guarda sob `set -e`+`pipefail` — um
  `PROTOCOL.md` regular ilegível abortaria o upgrade no meio; cura `|| _pwp_named=""`
  + teste `chmod 000`. (ii) O aviso não roda no ramo `PRESERVE_UNOWNED`
  (ponteiro `edited` SEM registro — install histórico sem linha no manifesto, ou
  ponteiro pré-existente do adopter): chamar o helper para `_lt = regular` antes
  do `return 0`; e corrigir a mensagem `SKIP … recorded --ceremony user install`
  desse ramo, que hoje fala só do caso `user`. Entram na próxima derivação com
  controle vermelho primeiro.
- **OQ-4 — Escopo canônico.** O brief nomeava `upgrade.sh`/`_framework_manifest_set.sh`;
  a identidade R2 obriga `install.sh`; a regra «unwired = no test» trouxe
  `ownership-nightly.yml` + `smoke-install.yml`. Ratificar **5 canônicos**
  (+1 se OQ-9).
- **OQ-5 — Onde o e2e novo roda (RESOLVIDA no draft como NIGHTLY; residual: promoção a per-PR).**
  O r5 fia `test-protocol-pointer-portable.sh` no `ownership-nightly.yml`, logo
  após o INV-4 — mesma classe de custo (installs reais + upgrades + `git
  archive`), o workflow já busca a tag legada que o P3 precisa, `timeout-minutes:
  150` com margem; e nos dois `paths:` filters do `smoke-install.yml`. Medido
  local: 316–327 s. Promover a per-PR (step no `smoke-install.yml` ao lado do
  render control, `timeout-minutes` 126 → medir p95 no CI primeiro — o Owner já
  tem o bump 126→150 DIFERIDO com gatilho «carona em wave de CI») é decisão do
  debate.
- **OQ-6 — Unificar o ramo dentro-do-target** com o template portátil (ganharia
  o parágrafo de reparo; exige reconhecedor da forma antiga dentro-do-target;
  população ~0). Recomendação: não nesta wave.
- **OQ-7 — Allowlist ASCII-only** (R-SEC8) rejeita paths com acento no flag
  novo, como já rejeitava no state. Ampliar é decisão de segurança separada.
- **OQ-8 — `_parity_classify.py:144-150`** (texto stale sobre o ponteiro): curar
  na wave (não canônico) ou FU.
- **OQ-9 — `SPEC/v1/install-cli.md`** (canônico, deny-edit): adicionar a linha
  `--protocol-source` (upgrade.sh) na mesma cerimônia — o contrato publicado
  enumera os flags do upgrade.
- **OQ-10 — `INSTALL.md`** (livre): documentar a receita de reparo e a
  portabilidade. Nice-to-have, sem gate.
- **FU (não OQ) — `_protocol_pointer_is_degraded` usa `mktemp` em `$TMPDIR`**
  (PLAN-168): a mesma classe que o rail r1 apontou no reconhecedor legado e
  que este draft curou canalizando para `cmp -s -`. O irmão degradado fica como
  está (fora do escopo da W1); um FU de uma linha o alinha.

---

## 9. Sequência que o Owner executa (não escrita neste pack)

1. `/debate start PLAN-183 "W1 ponteiro portátil — DESIGN-W1-S338.md"` com as
   OQs acima; decisões viram linhas no plano (Check reescritos onde mudar).
2. Sombra = `HEAD-do-dia` + fable51 (se ainda não landada) + `apply-w1-edits.py`;
   `--check-only` primeiro. Bateria (EVIDENCE.md §2) + **corrida nightly local
   de ownership (~25 min)** ⇒ re-gravar `ownership-baseline-map.txt`
   (`--stable-header`) e re-verificar `ownership-expected-reds.txt`.
3. Rail sobre a sombra re-derivada até rodada limpa (regra S329).
4. SIGN (sentinel com Anchor/Scope = os paths do `--list-paths` + o mapa) →
   LAND (`touched − scope = ∅`, V-block com o smoke) → commit → push.
