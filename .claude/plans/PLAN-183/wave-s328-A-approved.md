# wave-s328-A — sentinel de aprovação (DRAFT: o SIGN preenche Data / Anchor-SHA / Approved-By e assina)

> Caminho casa `PLAN-*/wave-*-approved.md` (união fechada de padrões em
> `check_canonical_edit.py`). O binding é o `Patch-sha256` (land por PATCH, sem
> `MANIFEST-*`). O bloco `Scope:` é **DERIVADO** por
> `w5-ceremony/finalize_patch.py` a partir de `git apply --numstat` — nunca
> escrito à mão (foi corrigido duas vezes neste plano e continuou incompleto nas
> duas). O `Anchor-SHA` é preenchido pelo `OWNER-S328-A-SIGN.sh` com
> `git rev-parse HEAD` no momento da assinatura; o `OWNER-S328-A-LAND.sh` aborta
> no G1 se não casar. Reescrever um byte deste arquivo depois de assinar
> invalida o `.asc`.

Plans: PLAN-183
Wave: wave-s328-A (W5-b FECHAMENTO — ADR-194 PROPOSED→ACCEPTED com a §7 de ratificação da OQ-4, a mesma correção na linha 102 do `CLAUDE.md`, e o discriminante line-exact do `hash_source` do `.github/CODEOWNERS` em `install.sh`)
Patch: .claude/plans/PLAN-183/s328-ceremony-A/A.patch
Patch-sha256: 2d9326a28ff1d8e51078f7a059e0b90a3b38b720e7296addf15ab9b95f47f05d
Patch-base: 4bd7def0ee0710bce4c04858a84b9ba88ef411d4
Anchor-SHA: TO-FILL-AT-SIGN
Data: TO-FILL-AT-SIGN

## O que esta wave entrega

**Dois arquivos canônicos, o contrato-raiz e um teste que viaja com eles.** Nada de produto muda
de comportamento em nenhuma execução que exista hoje — a cura do `install.sh` é
de FORMA, sobre um ramo comprovadamente INERTE (nenhum escritor de
`_CONTINUITY_PATHS` acrescenta path de `.github/`), e por isso vem acompanhada
de um controle positivo que reproduz o defeito.

1. **`.claude/adr/ADR-194-delivery-route-resolution.md`** (canônico) —
   `status: PROPOSED → ACCEPTED`, com o frontmatter e o cabeçalho reescritos
   para dizer QUEM ratificou e QUANDO: a assinatura GPG do Owner sobre
   `PLAN-183/wave-w5-approved.md` (land `6304f66`) mais a decisão verbatim de
   2026-08-25 «Pista MISTA — braço C (Recomendado)». Seção nova **§7
   Ratificação da OQ-4**, que descreve a pista mista como DECIDIDA e é
   explicitamente RETROATIVA (o braço C já é o conteúdo de `6304f66` — nenhuma
   linha de código muda por causa dela), fixa as quatro consequências da
   ratificação (pista mista; custo ZERO linhas no `ownership_table.tsv`; posse
   das duas árvores = hash-gate da entrega + `hash_source` do `CODEOWNERS`, não
   superfície nova em `_ownership_verdict()`; estender às duas árvores é wave
   própria) e registra a lição do checkout raso — `PRESERVED` é a direção
   SEGURA do erro, e foi ela que tornou o histórico incompleto VISÍVEL como
   `STALE 3` em vez de sobrescrever bytes do adopter em silêncio (cura em
   `738007e`).

2. **`scripts/install.sh`** (canônico) — o discriminante que decide
   `FMS_HASH_SOURCE_CODEOWNERS` a partir de `$_CONTINUITY_PATHS` passa a ser
   **line-exact**, no lugar do `case` por substring que os vizinhos
   (`SPEC/v1`, `PROTOCOL.md`, `.framework-version`) usam. O `case` é seguro
   para os vizinhos e NÃO é seguro aqui: `.github/CODEOWNERS` é PREFIXO de
   `.github/CODEOWNERS.template`, os dois coexistem no domínio de entrega e são
   mutuamente exclusivos por execução — uma continuidade carregando só o irmão
   `.template` respondia `HASH_PRIOR_RECORD`, isto é, gravava o digest ANTERIOR
   como baseline de um arquivo que a execução acabara de RENDERIZAR. Mesma
   forma que `upgrade.sh` já usa no sítio equivalente.

3. **`CLAUDE.md`** (contrato-raiz, não-canônico pelo oráculo) — uma linha, duas
   frases, **+111 bytes**. Enquanto o ADR vira `ACCEPTED`, a linha 102 dizia
   *"status textual `PROPOSED`"* e *"OQ-4 … não decidida"*. Como o `CLAUDE.md` é
   lido no **Gate 1 de toda sessão**, landar o flip sem esta linha entregaria
   governança contraditória no boot, por padrão. `git diff --stat` = 1
   insertion, 1 deletion; nada mais no arquivo muda. Validado com
   `validate-governance.sh` COMPLETO na sombra: rc 0, 22 gates, 0 erros,
   `OK: CLAUDE.md is 32152 bytes (limit 40000)`. O closeout desta noite **não
   toca a linha 102** (só acrescenta bullet novo em §5), e o `finalize-A.sh`
   re-aplica com `git apply --3way` — hunks disjuntos aplicam, conflito aborta.

4. **`scripts/tests/test-manifest-delivery-route.sh`** (não-canônico; viaja no
   pacote porque sem a cura ele fica VERMELHO) — bloco **S.17** com 5
   asserções e **S.17-control**, um controle POSITIVO que carrega a forma
   pré-cura verbatim e prova que ela responde `HASH_PRIOR_RECORD` no MESMO
   input em que a cura responde `HASH_TARGET`. O plant é escrito no próprio
   teste, não lido do histórico: uma vez commitada a cura, um controle baseado
   em git history se inverteria em vermelho permanente.

## O que esta wave NÃO entrega (e por quê)

As **sete** obrigações residuais da W5-b que exigem decisão de produto
continuam ABERTAS e nomeadas em `PLAN-183` §Open questions itens 5–11
(uninstall de `.github/CODEOWNERS` renderizado; F4 dos scanners de placeholder;
o par install-side; o literal de fonte em `_register_delivered_template`; a
rota renderizada que o `_parity_classify.py` resolve para `None`; o órfão
`docs/deny-baseline.md`; a disposição do STALE ×2 do `SPEC/`). Três obrigações
foram verificadas **já ENTREGUES** e retiradas da lista: @815
(`upgrade.sh:4457` + H.12/b/c/d/e), @733 (`_WBM_ROUTES_TSV` e seus leitores) e
§9.8 (`if: always()` em 7 steps do `smoke-install.yml`).

## Base de CI esperada após o land

Inalterada em toda dimensão medida — este pacote não muda comportamento de
execução existente. `Smoke Install` verde (paridade `maintainer` e `user`
`STALE 0`); `ownership nightly` com o RED set de sempre
`{OWN-0016, OWN-0024, OWN-0027}`; `test_install_baseline_manifest.sh` 33/1 com
o known-open EXATO `C.6.2`. Um `ownership nightly` TODO VERDE é sinal de
PARADA, não de sucesso.

## Autorização de governança

- Decisão do Owner de 2026-08-25 (S328), verbatim: «Pista MISTA — braço C
  (Recomendado)», registrada em `PLAN-183` §Open questions item 4. Este pacote
  é o FECHAMENTO textual dessa decisão em arquivo canônico — o ato que ratifica
  a OQ-4 foi a assinatura anterior, não este commit.
- Pair-rail: registros em `.claude/plans/PLAN-183/s328-ceremony-A/rail-round-*.md`.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs TO-FILL-AT-SIGN
Plans: PLAN-183
Scope:
  - .claude/adr/ADR-194-delivery-route-resolution.md
  - CLAUDE.md
  - scripts/install.sh
  - scripts/tests/test-manifest-delivery-route.sh
<!-- END SIGNED SCOPE -->

## Residual declarado

- O ramo curado no `install.sh` é INERTE hoje: nenhum escritor de
  `_CONTINUITY_PATHS` acrescenta path de `.github/`. A cura é de FORMA — os
  dois entrypoints deixam de discordar ANTES de existir um escritor. A prova de
  que a asserção não é vácua é o `S.17-control`, não a execução em produção.
- O `status:` textual do ADR-194 e o ato de ratificação são coisas SEPARADAS.
  Este patch move o texto; a autoridade continua sendo o `.asc` commitado sobre
  `wave-w5-approved.md`.
