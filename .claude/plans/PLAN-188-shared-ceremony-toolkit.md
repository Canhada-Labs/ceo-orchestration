---
id: PLAN-188
title: "Cerimônia compartilhada — scripts de assinatura e land por manifesto"
status: draft
created: 2026-09-05
owner: CEO
depends_on: []
level: L3
tags: [cerimonia, assinatura, land, manifesto, rail, governanca]
---

# PLAN-188 — Cerimônia compartilhada (SIGN / LAND / finalize / harness por manifesto)

> **Nível L3 — debate antes de executar.** Os scripts são o GATE da assinatura
> do Owner: um defeito neles não é um bug de produto, é uma assinatura sobre o
> conteúdo errado. `/debate start PLAN-188 "<proposta>"` precede qualquer wave.
>
> **Relacionados (leitura, não dependência):** PLAN-186 (pacotes canônicos em
> voo), PLAN-185, PLAN-183, ADR-010 (sentinel de edição canônica — é ELE que
> define o contrato `Scope:` + `check_canonical_edit.py` que este toolkit
> consome; o rascunho atribuía esse contrato ao ADR-031 e a OQ-1 registra a
> correção — o ADR-031 é «Self-improving skills» e está FORA do escopo deste
> toolkit),
> ADR-192 (manifesto de scripts de gate).

## Context

Cada pacote canônico carrega os próprios `OWNER-*-SIGN.sh`, `OWNER-*-LAND.sh`,
`finalize-*.sh` e `test-ceremony-scripts-*.sh`, clonados de um molde. O rail
de pares (codex) revisa cada clone e encontra as MESMAS classes em cada um:

| Classe (achada pelo rail; packs onde apareceu) | Packs | Consequência se assinado |
|---|---|---|
| SIGN gateia UMA família de rail (`RAIL_GLOB=rail-round-*`) | p169, w-rota | um registro de MATERIAIS `REJECT` não pára a assinatura |
| Trailer `Pair-Rail-Reviewed:` checado só como «não TO-FILL» (w6: só o índice MÁXIMO) | todos | commit reivindica 25 rodadas com 23 registros |
| Path absoluto pessoal em material assinado, sem guard em SIGN/LAND/harness | w4b (1 hit) | home do mantenedor commitado e assinado |
| Runner de controles que não roda de onde landa; instrumento que lê a prosa, não o runner | w4b | citações provadas por cópia cujo gêmeo committed está quebrado |
| Baseline (`EXPECTED-BASELINE`) editado à mão depois do finalize | w4b | finalize abortaria na assinatura; «bateria antes da última edição» |
| Escopo do sentinel digitado, diferente do diff | w6 | Owner assina escopo menor que o diff |
| Harness planta `Rail-Verdict: APPROVE` sintético | p169, w1, w4b, w6 | verde do harness lido como evidência de rail |

A coluna «Packs» lista os pacotes onde o rail nomeou a classe: três linhas
nomeiam dois ou mais pacotes, quatro nomeiam um só (as três de `w4b` e a de
`w6`). Uma classe vista em UM pacote entra na tabela porque o custo de
assinatura é o mesmo em qualquer clone, não porque já tenha repetido.

A cifra «25 rodadas com 23 registros» da linha 2 tem fonte, e ela é datada
(o conjunto de registros mudou depois): no pacote `w6-adapter`, o trailer
`Pair-Rail-Reviewed` afirmava «SUJEITO rodadas 1-14, MATERIAIS rodadas 1-11»
(14 + 11 = 25) enquanto `rail-round-12.md` e `rail-materials-round-9.md` não
existiam (13 + 10 = 23) — apurado em `rail-materials-round-12.md` daquele
pacote e em `STATE.md` F16. Os dois registros ausentes foram escritos depois,
então HOJE o conjunto está completo; o que a linha mede é o instante em que o
trailer teria entrado num commit assinado. Os pacotes citados na tabela ficam
fora do repo (área de trabalho da noite S345), por isso a cifra viaja com a
sua apuração, não com um comando reproduzível num checkout.

**Fração medida (medição S345).** Instrumento e saída viajam RASTREADOS com
este plano: `.claude/plans/PLAN-188/measure-rail-classes-v2.py` (o comando) e
`.claude/plans/PLAN-188/s345-rail-classes.txt` (a saída congelada). O arquivo
rastreado É a reprodução integral dessa saída; a evidência da wave mostra as
últimas 20 linhas dele. O bloco abaixo é o começo dessa saída.
Snapshot congelado da noite de 04→05/09/2026, corpus de
**528 blocos de achado em 168 registros de rail de 12 pacotes**:

```
ALL findings by class:      docs 132 25.0% | ceremony 122 23.1% | unknown 102 19.3%
                            instrument 63 11.9% | product 62 11.7% | ...
HIGH (P0/P1/BLOCKER/HIGH) by class: total=215
                            ceremony 60 27.9% | unknown 58 27.0% | docs 45 20.9% | product 28 13.0%
```

Ou seja: **cerimônia é 23,1 % de todos os achados de rail da noite e 27,9 %
dos de alta severidade** — a maior classe entre as de severidade alta —,
contra 25,0 % da classe `docs` e 11,7 % da classe `product`. As classes são as
do classificador do instrumento (por path e por palavra-chave); ele não julga
se o texto foi escrito à mão. O rascunho desta wave citava 22 % de uma execução
ANTERIOR do mesmo comando, na mesma noite (o closeout `e6b270c` registra
«medição das classes de rail 25/22/12/11 %»; a fração de ALTA severidade
daquela execução não ficou registrada em lugar nenhum). A medição é um SNAPSHOT:
o comando roda sobre os pacotes da noite S345 e o corpus cresce enquanto a
noite corre — a saída congelada acima é a fonte desta seção.

Cada pacote paga o rail de materiais do zero: em w6 o índice de rodada de
materiais chegou a 12 e em p169 a 11 (índices MÁXIMOS dos registros
`rail-materials-round-*.md`; NO INSTANTE MEDIDO da noite S345 a contagem de
registros EXISTENTES era menor que esses indices — exatamente a classe
«teto ≠ conjunto» da linha 2 da tabela. A nota da tabela acima registra que os
dois registros ausentes foram escritos depois, entao o conjunto daquele pacote
esta completo HOJE: o que estas cifras medem e o instante, nao o estado atual).
Para uma CONTAGEM,
rode `ls <pack>/rail-materials-round-*.md | wc -l` e cite o comando ao lado do
número.

## Goal

Que a assinatura do Owner passe por UM conjunto rastreado de scripts de
cerimônia, parametrizado por um manifesto por pacote, de modo que cada classe
de defeito da tabela acima seja fechada UMA vez, com controle vermelho, em vez
de ser reencontrada pelo rail em cada clone.

## Approach

UM conjunto rastreado de scripts em `.claude/scripts/ceremony/`
(`sign.sh`, `land.sh`, `finalize.sh`, `harness.sh`, `lib.sh`), parametrizado
por um manifesto por pacote, `ceremony.toml`, gerado pelo derivador:

```toml
key = "w6a"
plan = "PLAN-186"
anchor = "<sha do HEAD que o Owner assina>"
paths = [".claude/hooks/_lib/adapters/live/claude.py", "..."]
sentinel = ".claude/plans/PLAN-186/wave-s345-w6a-approved.md"
rail_records = { subject = ["rail-round-1.md", "..."], materials = ["rail-materials-round-1.md", "..."] }
baseline = "s345-ceremony-w6a/EXPECTED-BASELINE.txt"   # escrito SÓ pelo finalize
scope_generated_from = "apply-w6a.py --describe"         # o sentinel imprime isto, nunca texto digitado
```

Invariantes fechadas UMA vez, com controle vermelho cada:
1. Gate das DUAS famílias de rail: o registro LISTADO de maior número de cada
   família lê exatamente `Rail-Verdict: APPROVE`; registro em disco fora da
   lista ⇒ recusa nomeada.
2. Trailer de proveniência GERADO do conjunto de registros; `land.sh` compara
   CONJUNTOS nos dois sentidos.
3. Guard de path absoluto fora do repo em qualquer material (único allow por
   regex: o glob de self-test `claude-501/*/scratchpad`), em `sign.sh` P0, no
   finalize e no harness; o guard se auto-escaneia.
4. `EXPECTED-BASELINE` e `BASE-SHA` escritos SÓ pelo finalize; `sign.sh`
   regenera e compara byte a byte (edição manual ⇒ recusa).
5. Escopo do sentinel e `PROPOSED-PATCH` gerados de `apply-<key>.py --describe`
   (ops por path); `sign.sh` regenera e compara.
6. `land.sh` liga o `NEW_SHA` empurrado ao índice aprovado (parent, conjunto
   de paths, blob ids e modos, mensagem byte-igual), verifica a TREE antes do
   push e pina o push ao `NEW_SHA`.
7. Runner de controles auto-resolvente (`git rev-parse --git-dir`, funciona
   em worktree) e EXECUTADO pelo harness a partir da posição landada.
8. Harness NUNCA planta `APPROVE`: copia os registros reais; sem APPROVE, o
   verde esperado é «SIGN recusa».
9. Liveness de rodada de texto: `VERDICT:` próprio + `tokens used` diferente
   de toda rodada anterior + âncoras na revisão atual.

### Riscos e o que NÃO muda

- Os scripts são GATE de assinatura ⇒ a wave é L3: debate antes de executar;
  o toolkit landa por cerimônia própria (a última assinatura «à moda antiga»).
- Nada muda no `check_canonical_edit.py` nem no formato do sentinel assinado
  (ADR-010): o toolkit consome o mesmo `.asc`.
- Pacotes já em voo terminam nos scripts clonados COM as notas de classe
  aplicadas; a migração é por manifesto, sem re-derivar o patch.

## Items

| Wave | Entrega | Gate |
|---|---|---|
| W0 | `ceremony.toml` schema + `lib.sh` + os 9 controles vermelhos (sem consumidor) | livre (scripts novos, oráculo 0 até serem referenciados por SIGN) |
| W1 | `sign.sh`/`land.sh`/`finalize.sh`/`harness.sh` + piloto W6a | canônico (cerimônia) |
| W2 | migração dos 5 packs + remoção dos clones | canônico |
| W3 | medição AC-4 + ADR aceito | docs |

## Acceptance criteria

- [ ] AC-1 Os 5 scripts existem, `bash -n` + shellcheck limpos, sem path
      pessoal, com ≥ 1 controle VERMELHO por invariante (9 controles) e o
      harness rodando a partir de um clone descartável em worktree.
      Check: `bash -n` + `shellcheck` nos 5 scripts + o runner de controles
      imprime 9/9 VERMELHO-antes / VERDE-depois; falha = qualquer controle
      que passe com a invariante removida.
- [ ] AC-2 Um pacote piloto (W6a) migra para o manifesto e assina/landa por
      `ceremony/sign.sh` + `land.sh` sem script próprio.
      Check: o commit landado do piloto não referencia nenhum `OWNER-*-{SIGN,LAND}.sh`
      próprio e o `.asc` verifica; falha = o piloto precisar de um script clonado.
- [ ] AC-3 Os 5 packs restantes (W4b, W5a, W1a, SF, WR) migram por manifesto;
      `OWNER-*-{SIGN,LAND}.sh` por pacote deixam de existir.
      Check: `git ls-files` não lista nenhum `OWNER-*-{SIGN,LAND}.sh` para os
      6 pacotes; falha = qualquer um sobreviver rastreado.
- [ ] AC-4 Medição: fração «cerimônia» dos achados de rail nas 3 assinaturas
      seguintes < 5 % (era 23,1 % — medição S345 congelada em
      `.claude/plans/PLAN-188/s345-rail-classes.txt`).
      Check: `python3 .claude/plans/PLAN-188/measure-rail-classes-v2.py --pack-dir <árvore
      dos pacotes das 3 assinaturas>` imprime `ceremony` < 5 %; falha = ≥ 5 %, e o
      plano diz o porquê.
- [ ] AC-5 ADR próprio (`ADR-2xx-shared-ceremony-toolkit`) ACEITO pelo Owner;
      ADR-010 emendado para apontar o toolkit como implementação canônica da
      disciplina de sentinel.
      Check: o ADR existe com `Status: ACCEPTED` e um `.asc` do Owner sobre o
      sentinel da wave; falha = status flipado sem assinatura rastreada.

## Open questions

- OQ-1 — **Resolvida (CEO, S347)**: o alvo da emenda do AC-5 é o **ADR-010**
  («Canonical-edit sentinel for meta-agent drafts»), que define o contrato
  `Scope:` + `check_canonical_edit.py` consumido por este toolkit; o **ADR-031**
  («Self-improving skills, Owner-gated, shadow-mode») está FORA do escopo e não
  é emendado. O rascunho de origem atribuía o formato do sentinel ao ADR-031
  (achado pelo rail de mecanismo desta wave); a atribuição foi corrigida em
  todos os sítios deste arquivo. Aberto para o debate: qual número `ADR-2xx`
  recebe o ADR próprio e em que wave a emenda ao ADR-010 entra.
- OQ-2 (Owner): a ordem de migração dos 5 packs do AC-3 (o rascunho não a fixa)
  e a janela de assinatura de cada um.
- OQ-3: COMO ler o `ceremony.toml` a partir do bash — não há parser TOML na
  stdlib de shell. Decidir no debate; o formato do manifesto é o do §Approach.
- OQ-4: as cinco chaves de orçamento do molde `PLAN-187` que este frontmatter
  omite (`budget_tokens`, `budget_sessions`, `context_risk`, `external_wait` —
  ADR-081; `eta_calendar` — PLAN-180) ficam em aberto: o rascunho não estimou e
  este arquivo não inventa números.
- OQ-5: o instrumento tem SEIS limites conhecidos, achados pelas rodadas
  de mecanismo desta wave sobre os bytes landados e reproduzidos no código:
  (i) todo cabeçalho `#` fecha bloco (`measure-rail-classes-v2.py:90-93`), então
  um achado anunciado por `## Achado P1 …` perde a severidade e o corpo;
  (ii) linhas de tabela consecutivas se FUNDEM num bloco só
  (`:94-99`, `START_RE` não casa o `|` inicial e `and not cur` só deixa a
  primeira linha abrir bloco); (iii) qualquer bloco com path entra no
  denominador (`:131-134`), inclusive bullets de proveniência — a classe
  `other-path` da saída congelada contém exatamente isso;
  (iv) um pacote cujas rodadas são todas limpas nunca entra em `per_pack`
  (`:126-129`), então some da contagem de pacotes — um registro `APPROVE` sem
  achado dá `records=1 packs=0`; (v) `nh = sum(high.values()) or 1` (`:147-148`)
  imprime `HIGH ... total=1` quando NÃO há achado de alta severidade — a
  proteção contra divisão por zero sai como se fosse medida; (vi) um path na
  RAIZ do repo sob `tests/` não é reconhecido por `PATH_RE` (`:33` — `tests`
  não está entre as raízes e o lookbehind `(?<![\w/])` impede casar o basename
  depois de `/`), então o achado cai na classificação por palavra-chave e um
  bloco como `[P1] tests/integration/test_install_npm_smoke.py fails to check
  the sentinel` sai `ceremony` em vez de `tests` — inflando justamente a
  fração que o AC-4 compara. Consequência: o
  23,1 % é a fração DESTE classificador, não uma contagem canônica de defeitos,
  e a comparação do AC-4 só é honesta se as 3 assinaturas seguintes forem
  medidas pelo MESMO binário. Decidir no debate: corrigir o classificador e
  re-medir a linha de base, ou congelar o instrumento como está e comparar
  igual-com-igual.

## How to continue

Primeira mensagem de uma sessão futura: «Leia `.claude/plans/PLAN-188-shared-ceremony-toolkit.md`
e o resultado do `/debate start PLAN-188`. Se o debate ainda não rodou, rode-o
(L3). Se rodou e o Owner marcou o plano `reviewed`, execute a W0 (`lib.sh` +
os 9 controles vermelhos, oráculo 0 — pacote livre) e só então proponha a W1.»

## Success criteria

- AC-1 a AC-5 marcados, cada um com a evidência do seu `Check:` citada.
- O plano só sai de `draft` por decisão do Owner após o `/debate`.

## Progress log

- 2026-09-05 (S345): plano criado como rascunho a partir da medição da noite
  (`.claude/plans/PLAN-188/measure-rail-classes-v2.py`, saída congelada em
  `.claude/plans/PLAN-188/s345-rail-classes.txt`). Debate L3 devido.
