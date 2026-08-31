# wave-adrgate — desenho (FU-F-ADRGATE, night-run S333)

> Follow-up NOMEADO pela wave-s330-F (`CLAUDE.md` §5, `rail-round-7`/`README-F`).
> Escopo ratificado pelo Owner em 2026-08-30 («A+B», AskUserQuestion).

## 1. O que a wave-F deixou aberto, e o que a medição mudou

A wave-F registrou: *«`check-adr-chain.py` e `generate-adr-index.py` **não
rodam em CI** — índice congelado em 170 ADRs com 198 no disco; cadeia rc 1 com
11 erros pré-existentes»*. O plano da noite (runbook S333 §1) traduzia isso em
**editar dado**: dar `Status:` a nove ADRs e flipar o ADR-111 para `SUPERSEDED`.

**A recon mediu e refutou as duas premissas.** O que existe de fato:

| Premissa do plano | Medição |
|---|---|
| «9 ADRs sem `Status:`» | Os nove **têm** o campo, escrito como item de lista: `- **Status:** VALUE`. O parser ancorava em `^[#\s]*`, que não aceita bullet — o campo era invisível para o LEITOR. Censo do corpus: 96 usam frontmatter `status:`, ~80 usam `**Status:**` sem bullet, 12 usam bullet (9 falham; ADR-153/154/155 escapam por carregarem TAMBÉM frontmatter). |
| «ADR-111 vira `SUPERSEDED`» | Flipar **re-introduziria um bug de ledger já reparado**. `ADR-111:20-31` é uma errata explícita: de 2026-05-12 até o PLAN-163 T5.2 o frontmatter dizia falsamente `status: SUPERSEDED`; o reparo registra que o ADR-120 «contains none of this locked-corpus substance and never superseded this decision». `README.md:27-29` repete, `ADR-182:193-194` afirma que a substância **não** é superseded, e um consumidor VIVO (`SPEC/v1/audit-log.schema.md:329`) fala em «ADR-111 ACCEPTED gate». |

**Consequência:** o objetivo ratificado (cadeia sai 0, os dois gates em CI)
fica de pé; o MECANISMO muda de «editar 10 arquivos canônicos de dado» para
«curar o leitor». A wave passa a tocar **zero** ADRs.

## 2. As três curas, e por que cada uma é de LEITOR

### 2.1 A âncora de início-de-linha (9 dos 11 erros)

`_STATUS_INLINE_RE`, `SUPERSEDED_BY_RE` e `SUPERSEDES_RE` aceitavam apenas `#`
e espaço antes do campo. A classe passa a aceitar bullet (`-`/`*`) nas três —
**uma gramática, três leitores**. Medido com censo antes/depois sobre os 198
ADRs: a mudança move **exatamente 9** registros de «sem status» para o valor
declarado e **não altera nenhum status já lido** (o risco real de alargar uma
âncora é capturar uma menção em prosa antes do campo verdadeiro; não ocorre).

### 2.2 Rename completado ≠ supersessão (1 erro)

`ADR-120` declara `supersedes: - rename_source: ADR-111-pii-core-promotion`.
O próprio frontmatter dele diz `original_id: ADR-111`, `renamed_at`,
`renamed_via`, `rename_driver`, e o título diz «(renamed from ADR-111)»:
**ADR-120 É o registro ADR-111, renomeado** pela doutrina do ADR-117. Não há um
segundo registro para estar SUPERSEDED.

O skip exige **as DUAS pernas**, e cada uma exclui um erro diferente:

* o declarante tem de **dizer** (`original_id: <alvo>`) — o skip repousa na
  declaração do autor, não no palpite do checker a partir de um nome de chave;
* nenhum arquivo pode ainda carregar um `rename_source:` declarado. Se o
  registro antigo sobrevive como arquivo próprio, o rename **não** completou e
  a aresta é real — que é exatamente a forma que
  `test_yaml_supersedes_block_sequence_primary_ref_only` fixa (a fixture dela
  entrega `ADR-111-old.md` no disco).

### 2.3 Supersessão de CLÁUSULA ≠ aposentadoria (1 erro)

`ADR-182` declara `supersedes: "ADR-111 §pin clauses + ..."`. O alvo declara a
contraparte: `ADR-111` tem `amended_by: ADR-182`. O skip é keyed por
**(declarante, alvo)** — um registro emendado por OUTRO ADR continua sendo
aposentado por este se este disser que aposenta.

**O `§` NÃO é usado como marcador**, deliberadamente: o próprio corpus de teste
(`test_supersedes_parenthetical_qualifier_parsed`) fixa uma supersessão
legítima que carrega um `§`. Inferir de formatação quebraria esse teste — e
seria a mesma classe de defeito que esta wave cura.

## 3. O escopo B: o índice publica a mesma mentira

`generate-adr-index.py` tem `_MD_STATUS_RE` com a **mesma** âncora estreita, e
por isso o índice que o repositório shipa publicava `(UNKNOWN)` no status de
exatamente os mesmos 9 ADRs. Wire de um gate «índice em dia» sobre um índice
que publica nove statuses errados seria um gate vacuoso.

Cura: a primeira alternativa do regex aceita bullet opcional; `--write`
regenera. Medido: o diff do `README.md` é de **9 linhas**, todas células de
status `(UNKNOWN) → <valor>`; a seção `## Known amendment chain gaps` — que o
**próprio** `check-adr-chain.py` lê (`_load_known_chain_gaps`) — sobrevive
byte-a-byte (verificado: linha 46 antes e depois).

## 4. O wire (o ponto da wave)

Dois steps novos no `validate.yml`, no job `validate`, ao lado dos gates de
idempotência de gerador que já existiam. Medido antes: `grep -rn
'check-adr-chain\|generate-adr-index' .github/` = **zero**, e o mesmo grep em
`validate-governance.sh` = zero. Um gate que ninguém roda é o mesmo que gate
nenhum — foi assim que 11 erros e 9 statuses errados sobreviveram meses.

## 5. Controles vermelhos (o que prova que a cura é a razão do verde)

`s333-ceremony-adrgate/redctl-adrgate.sh`, cada caso numa CÓPIA descartável da
árvore de ADRs (nunca a árvore do repositório — lição da r3 da wave-F):

| controle | perna removida | resultado exigido | medido |
|---|---|---|---|
| baseline | — | 0 erros | ✅ 0 |
| RC-1 | o slug antigo VOLTA ao disco | a aresta de rename volta | ✅ 2 erros |
| RC-2 | `amended_by` sai do alvo | a aresta de cláusula volta | ✅ 1 erro |
| RC-3 | o campo `Status:` sai de um ADR bullet | «missing Status» volta | ✅ 1 erro |

Mais dez testes de regressão em `test_check_adr_chain.py` (32 → 42), incluindo
os dois casos que fixam as pernas isoladas (`original_id` ausente ⇒ aresta
mantida; arquivo do slug presente ⇒ aresta mantida) e o
`test_the_shipped_corpus_is_clean`, que afirma o ESTADO FINAL sobre o corpus
real — um ADR futuro que quebre a cadeia fica vermelho aqui primeiro.

## 6. Limites declarados

* **O `function-length` não foi tocado e não precisa ser.** O verificador
  adversarial levantou que `parse_adr` e `validate_chain` estão pinados por
  sha256 de corpo em `.claude/governance/function-length-grandfather.yaml`, e
  que editá-los quebraria a isenção. **Medido: não quebra o gate** —
  `check-function-length.py` é ADVISORY (sai `WARN` e rc 0; hoje reporta 1144
  funções acima de 50 LoC no repositório inteiro). A isenção fica desatualizada
  como DADO, e isso é dívida declarada aqui, não curada.
* **O corpus tem três gramáticas para o mesmo campo** e três leitores com
  regras diferentes: `check-adr-chain.py` (agora inclusivo),
  `generate-adr-index.py` (idem) e `validate-governance.sh:844`, que lê apenas
  `^\*\*Status:\*\*`. Esta wave NÃO unifica a gramática — seria uma wave de
  dado sobre 198 arquivos canônicos. Fica como follow-up **FU-ADR-GRAMMAR**.
* **`FU-ADR-README-SEED`** (aberto na mesma noite, Bloco 0): o `install.sh`
  semeia este `README.md` — com o índice dos 198 ADRs do FRAMEWORK — dentro da
  árvore do adopter. Família A7 de contaminação, cura canônica, decisão do Owner.
