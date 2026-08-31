# wave-adrgate — sentinel de aprovação (DRAFT: o SIGN preenche Data / Anchor-SHA / Approved-By e assina)

> Caminho casa `PLAN-*/wave-*-approved.md` (união fechada de padrões em
> `check_canonical_edit.py`). O binding é o `Patch-sha256` (land por PATCH, sem
> `MANIFEST-*`). O bloco `Scope:` é **DERIVADO** por
> `PLAN-183/w5-ceremony/finalize_patch.py` a partir de `git apply --numstat` —
> nunca escrito à mão. O `Anchor-SHA` é preenchido pelo
> `OWNER-S334-ADRGATE-SIGN.sh` com `git rev-parse HEAD` no momento da
> assinatura; o `OWNER-S334-ADRGATE-LAND.sh` aborta no G1 se não casar.
> Reescrever um byte deste arquivo depois de assinar invalida o `.asc`.

Plans: PLAN-169
Wave: wave-adrgate (PLAN-169 — o ledger DECLARADO de isenção de supersessão vira DADO revisado no `.claude/adr/README.md`, os DOIS gates de ADR entram no `validate.yml`, e o ADR-197 recebe o flip textual PROPOSED → ACCEPTED cuja ratificação real já está commitada)
Patch: .claude/plans/PLAN-169/s334-ceremony-adrgate/ADRGATE.patch
Patch-sha256:
Patch-base: TO-FILL-AT-FINAL-PATCH
Anchor-SHA: ANCHOR-PLACEHOLDER
Data: DATA-PLACEHOLDER

## O que esta wave entrega

**Três arquivos canônicos** e **um não-canônico** que só é verdadeiro junto
com eles. O oráculo `--is-canonical` responde `1` para
`.claude/adr/README.md`, `.claude/adr/ADR-197-user-profile-derivation.md` e
`.github/workflows/validate.yml`; `0` para
`.claude/scripts/tests/test_check_adr_chain.py`. O patch é atômico de
propósito: o fixture que afirma "corpus limpo com 2 entradas firing" é FALSO
sem o dado do README, e um gate ligado sem o dado nasceria vermelho.

1. **`.claude/adr/README.md`** (canônico) — o DADO. Seção nova
   `## Declared supersession exemptions (reviewed data, mandatory-fire)` com
   as DUAS entradas que as três rodadas de rail da S333 provaram legítimas:
   `ADR-120 -> ADR-111` (rename ADR-117 completado; flipar o ADR-111
   re-introduziria o bug de ledger reparado por PLAN-163 T5.2, e
   `SPEC/v1/audit-log.schema.md:329` ainda o lê) e `ADR-182 -> ADR-111`
   (supersessão de cláusula; o alvo declara `amended_by: ADR-182` ele mesmo).
   O parser é o `_load_declared_exemptions` que landou LIVRE em `5df5c48`
   (mandatory-fire; entrada malformada = erro fail-closed; par literal por
   ID-base — zero gramática de qualificador). A tabela ADR-INDEX foi
   regenerada no mesmo patch porque o flip do ADR-197 muda a linha dele
   (o gate novo de índice pegou exatamente isso na primeira bateria da
   sombra — o instrumento funcionou antes de nascer).

2. **`.github/workflows/validate.yml`** (canônico, KERNEL) — o WIRE. Dois
   steps novos no job de governança: `check-adr-chain.py` (a cadeia + o
   ledger) e `generate-adr-index.py --check` (drift do índice). Até aqui
   NENHUM CI rodava qualquer um dos dois (medido: grep = zero) — a cadeia
   quebrada por 28 regenerações não-feitas da tabela foi invisível por
   meses exatamente por isso.

3. **`.claude/adr/ADR-197-user-profile-derivation.md`** (canônico) — o flip
   textual `PROPOSED → ACCEPTED`. A ratificação REAL é o `.asc` sobre
   `wave-s330-F-approved.md` (land `303ae55`, S332); este flip chega por
   cerimônia própria exatamente como ADR-194 e ADR-196 registraram.

4. **`.claude/scripts/tests/test_check_adr_chain.py`** (livre) — o fixture
   de estado do corpus flipa: de "exatamente 2 erros, ambos ADR-111" para
   "corpus LIMPO **e** as duas entradas do ledger presentes e firing" —
   asserção nos DOIS lados para que um ledger vazio passando vácuo não
   se esconda atrás do verde.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: APPROVED-BY-PLACEHOLDER
Plans: PLAN-169
Scope:
  - placeholder-scope-derivado-pelo-finalize
<!-- END SIGNED SCOPE -->

## Fronteiras honestas

- **A gramática do campo `Status:` segue com 3 formas no corpus** (96
  frontmatter / ~80 bold / 12 bullet) e 3 leitores — esta wave liga os gates
  com o leitor CURADO da S333, mas NÃO unifica a gramática
  (`FU-ADR-GRAMMAR`, decisão de escopo do Owner; wave de dado sobre 198
  arquivos canônicos).
- **O seed do `README.md` de ADRs no adopter segue contaminante**
  (`FU-ADR-README-SEED`, família A7): o install semeia o índice dos 198
  ADRs DESTE repo na árvore do adopter. Decisão de produto do Owner,
  fora deste patch.
- **O ledger cobre UMA classe de aresta** (`Supersedes:` → alvo
  não-SUPERSEDED). As outras isenções que a rota r1–r3 tentava inferir por
  gramática (rename_source órfão, AMEND não-normalizado) morreram COM a
  gramática — se um dia uma nova classe legítima aparecer, ela entra como
  entrada nova revisada, nunca como regex nova.
- **`validate.yml` é KERNEL** (`_KERNEL_PATHS`): o LAND exige
  `CEO_KERNEL_OVERRIDE` além do sentinel, no mesmo protocolo da wave-F.
