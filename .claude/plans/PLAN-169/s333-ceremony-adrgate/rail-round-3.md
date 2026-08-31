# wave-adrgate — rail codex rodada 3 (sombra curada da r2, 2026-08-31 ~05:5x -03)

Rail-Verdict: CHANGES-REQUESTED (0 P1, 4 P2 — todos REAIS; **NÃO curados**, e a
razão de não curar é a disposição desta rodada)

Comando: `codex exec review --uncommitted --skip-git-repo-check -c sandbox_mode="workspace-write"`,
via `rail_round.sh`. Substrato: codex-cli 0.147.0. Saída bruta:
`<scratchpad 889bc1bd>/adrgate-r3.txt`. Wrapper: **TREE INTACT**.

## Os quatro achados (terceira rodada da MESMA classe)

1. **Status lido do documento inteiro.** Um exemplo cercado ou um checklist
   com `- **Status:** ACCEPTED` no corpo de um ADR *sem* metadado vira o status
   canônico — e o gerador de índice varre os primeiros 4 KB, então os DOIS
   gates concordariam sobre um status falso.
2. **Qualificador aceita indentação arbitrária dentro do frontmatter.** Um
   bloco escalar (`notes: |`) cujo exemplo indentado menciona `original_id:` e
   `rename_source:` é tratado como metadado vivo.
3. **`rename_source` com id nu.** `rename_source: ADR-111` passa no teste de
   nome e a sonda procura `ADR-111.md` — que a própria gramática de nome de
   arquivo deste checker torna **impossível** de existir. A ausência é
   garantida, então o waiver é sempre concedido.
4. **Id do declarante AMEND não normalizado.** Um `ADR-NNN-AMEND-K-<slug>.md`
   entra no teste com o stem COMPLETO enquanto o `amended_by` do alvo guarda o
   stem curto — a pertinência nunca casa, e um arquivo AMEND normal **jamais**
   consegue reivindicar a isenção que a wave criou para ele.

## Disposição: cortar o escopo, não remendar a quarta vez

Esta é a **terceira rodada consecutiva** em que o revisor acha furos
fail-open no MESMO mecanismo — a isenção de qualificador é mais frouxa do que
a semântica que ela declara, e cada cura revelou a próxima borda (r1: 1 furo;
r2: 4; r3: 4). A doutrina do repositório é explícita para este padrão: *classe
que repete no rail = trocar a ARQUITETURA da cura, enumerando o que MANTER, e
nos DOIS lados da fronteira* — não emendar ramo a ramo (anti-padrão S296).

Então o pacote foi **partido pela linha que a evidência sustenta**:

* **Landou** (`f348ee9`, caminho LIVRE, sem cerimônia): a cura de **âncora**,
  que fecha **9 dos 11** erros, é cirúrgica (censo: move exatamente nove, não
  altera nenhum status já lido), tem sete testes e sobreviveu às três rodadas —
  os achados da r1/r2 sobre ela (bullet exige espaço, bold é dois asteriscos,
  classe horizontal-only) foram curados e viraram teste.
* **NÃO landou**: o mecanismo de isenção de qualificador e o wire dos dois
  gates no `validate.yml`. Um gate que se liga junto com uma isenção que o
  revisor ainda está furando não é enforcement — é uma porta com fechadura
  nova e a janela aberta ao lado.

## A rota proposta para a wave seguinte (não executada aqui)

Parar de **inferir** a isenção a partir de chaves de frontmatter e passar a
**declarar** os dois pares, no molde que o próprio checker já lê para outra
coisa (`_load_known_chain_gaps`, seção `## Known amendment chain gaps` do
`.claude/adr/README.md`): um ledger `(declarante, alvo, razão)` com
**mandatory-fire** — uma entrada que não casa nada é ERRO, porque o ledger não
pode sobreviver ao bug que ele nomeia.

Isso troca uma superfície de gramática (que a r1–r3 provaram larga) por **duas
linhas de dado revisadas**, mata os quatro achados desta rodada por construção
e mantém a propriedade que o repositório valoriza: a exceção é visível, tem
razão escrita e morre sozinha quando deixa de ser necessária. O `README.md` dos
ADRs é canônico, então essa wave é de cerimônia — junto com o wire do CI, que
é o outro path canônico.

## Estado medido ao fim da rodada

Na árvore que landou: `check-adr-chain.py` **2 erros** (os dois qualificadores,
ambos citando ADR-111, fixados por teste); `generate-adr-index.py --check`
rc 0; `test_check_adr_chain.py` **39** casos; `verify-counts.sh` rc 0;
`validate-governance.sh --fast` 0 erros; ceremony-lint blocking 0;
`CLAUDE.md` 39.944 B.
