# Pair-rail prompt — PLAN-194 W3b.1, metade canônica, RODADA 3 — FINAL (Codex read-only + refutadores Claude)

Você é o revisor cruzado (V2 da cascata de verificação — `PROTOCOL.md` §Verification cascade).

**Sujeito desta rodada (e só ele):**
1. o patch `.claude/plans/PLAN-194/w3b1/w3b1.patch` — o MESMO das rodadas 1 e 2 (sha256
   `7dccad8354cc4fe0b59abf545893f6e923f19d07a08c7c5bbedad7cbe1f09773`), JÁ APLICADO nesta árvore: os
   sete arquivos que ele toca estão aqui na pós-imagem; a pré-imagem é o `index` de cada arquivo no
   patch. A cópia `.claude/plans/PLAN-194/w3b1/staged-w3b1/.claude/hooks/_lib/codex_cli_shape.py` é o
   mesmo byte da pós-imagem do arquivo canônico (o SIGN confere);
2. o texto que o Owner vai assinar, `.claude/plans/PLAN-194/w3b1-approved.md`, NOVO nesta rodada (os
   campos `TO-FILL-BY-SIGN` são preenchidos pelo script de assinatura; não são achado). O diff da
   rodada 2 para esta está em `.claude/plans/PLAN-194/w3b1/rail-r2-r3-sentinel.diff` (material de
   apoio, não sujeito).

**Contexto que NÃO é sujeito:** os commits livres já no `main` («fix(PLAN-194 W3b.3): o3-mini e
o4-mini no ledger da OpenAI», «fix(PLAN-194 W3b.1, metade livre)»). O script do SIGN
(`OWNER-W3B1-SIGN.sh`) e o harness (`test-ceremony-w3b1.sh`) também não são sujeito do rail, mas o
texto assinável descreve o SIGN: uma frase do texto que o código do SIGN desminta é afirmação falsa.
Achados fora do sujeito vão numa seção separada e não decidem o veredito.

**O que a rodada 2 achou e como a rodada 3 cura (conferir que a cura é verdadeira):**
- P1 (Codex e refutador de mecânica) — o veredito do revisor não estava preso ao bloco verbatim: o
  parser fechava a seção em qualquer `## ` (inclusive dentro do bloco) e aceitava `VERDICT:` fora da
  cerca. Cura: a gramática estrita da W1 (r3), IDÊNTICA nos dois SIGNs — exatamente uma seção
  `## Saída do revisor`, exatamente um bloco aberto por uma linha igual a três crases + `text` e
  fechado na próxima linha igual a três crases, lido inteiro, nenhuma outra linha de cerca na seção;
  veredito = última `VERDICT: ` do bloco, com valor GO, GO-WITH-CONDITIONS ou NO-GO; cerca ausente,
  duplicada, mal formada (inclusive INDENTADA — indentar não é rota) ou não fechada é recusada com o
  motivo. Ensaio: T6-innerheading, T6-badopen, T6-unclosed, T6-twofences, T6-innerfence,
  T6-afterfence, T6-indentinner, T6-indentafter e o controle positivo T6-headingok.
- P1 (refutador de mecânica) — o `validate-governance` era comparado só pelos cabeçalhos de grupo.
  Cura: a saída INTEIRA (cabeçalho, detalhe de cada violação, contagem), com e sem o patch; as linhas
  de aviso saem pelo PREFIXO com que o validate-governance as emite (`  WARN: `, `  WARNING: `,
  `    WARN (grandfathered): `, `  V<n> WARN [`, `  Warnings: `), nunca por substring, e a linha
  `Repo:` sai, com espaços normalizados; uma execução sem o resumo `Errors:` numa das árvores reprova.
  Ensaio: T26 (violação nova dentro do mesmo grupo, com «status: WARN» no detalhe, mesma contagem ⇒
  reprova).
- P2 curados no SIGN (portados da W1 r3 ou novos): allowlist de signatários e biblioteca de verificação
  lidas do HEAD; o controle exige a linha `SUMMARY: breaks=` com acertos no HEAD e `SUMMARY: breaks=0
  warns=0` + `LIVE-BREAKS-REMAINING: 0` com o patch (T17c: exceção não conta); modos 100644 no índice;
  `--dry-run` só diz «Ensaio OK» com a árvore limpa; conferência do commit depois do `git commit` (um
  hook que stageie algo desfaz o commit com `reset --soft`; T27); preenchimento do sentinel com
  `newline=""`; o comentário do desfazer diz quando o patch é ou não revertido (T13/T13b); T6-reviewer
  escolhe a mensagem pelo Rail-Verdict do registro. Shellcheck não se aplica (o patch não toca
  workflow).
- P2 curados no texto assinável: o parágrafo novo do módulo «diz que um teste a cobra, sem nomeá-lo»;
  o `-luna` como sonda de caracterização; a exceção do `validate-governance` na frase dos gates de
  corpus; residuais novos (a nota `_meta.openai_rows_refreshed` do ledger e o «retired in 2026» do
  comentário do patch, que está congelado desde a rodada 1).

**Anexo da rodada 3 (depois do NO-GO da r3; o patch não mudou):**
- removida a normalização de raiz da comparação do `validate-governance` (as três lanes acharam P1
  nela: escondia diagnóstico com valor igual à raiz e não normalizava a base no macOS); a comparação
  volta a ser a da W1 (saída inteira, avisos pelo prefixo do produtor, linha `Repo:` fora, espaços
  normalizados), o T26b saiu, e o texto declara pela forma: com a base vermelha, um detalhe com caminho
  absoluto reprova por ruído (falha FECHADA);
- pós-commit: a árvore do índice conferido é gravada com `git write-tree` logo antes do commit e o SIGN
  exige `HEAD^{tree}` igual a ela e o pai igual ao Anchor-SHA (cobre a `.asc`, os modos e todo caminho);
  um hook que mude o commit faz o SIGN desfazê-lo com `reset --soft` para o Anchor-SHA. Ensaio: T27
  (hook que stageia um arquivo a mais) e T28 (hook que troca só a `.asc`);
- texto: «retired» declarado pela forma nos três sítios do patch congelado; o residual da nota `_meta`
  aponta para o refresh do ledger da OpenAI com substitutos por faixa (backlog no LEDGER, seção W3b.3);
  «`Repo:` fora, com espaços normalizados» na frase da comparação.
O diff do texto assinável da rodada 3 para o anexo está em
`.claude/plans/PLAN-194/w3b1/rail-r3-anexo-sentinel.diff` (material de apoio, não sujeito).

**Critérios:**
- nenhum membro de `_VALID_MODELS` tem linha (`model_id` ou alias) no ledger; todo id que saiu tem;
- o argv PADRÃO do rail não muda em nenhum dos dois modos (`DEFAULT_MODEL` `None`, sem `--model`);
- `check-model-deprecations.py --check --today 2026-10-13` sai 0 nesta árvore; `check-model-currency.py
  --expected-reds` sai 0 com 6 vermelhos, e a redução 7 → 6 tem causa escrita no arquivo;
- CADA frase do texto assinável é uma afirmação sobre o código ou sobre o SIGN: uma afirmação FALSA é
  motivo de NO-GO; o «Residual declarado» precisa ser verdadeiro e completo; as curas acima precisam ser
  verdadeiras.

**Regra desta rodada:** a regra de parada pré-registrada é de no máximo 3 rodadas; esta é a 3.ª e
FINAL. NO-GO só por P0 ou por afirmação falsa no texto assinável. Relate todo P1/P2 com
`arquivo:linha` e cura concreta. Não proponha JEV nem capacidade não aprovada do fornecedor. Não altere
arquivos (sandbox read-only).

**Saída:** a lista de achados, cada um com severidade `P0 | P1 | P2`, `arquivo:linha` e cura; se não
houver nenhum, escreva exatamente `NENHUM ACHADO`. Termine com UMA linha
`VERDICT: GO | GO-WITH-CONDITIONS | NO-GO`.

**Registro:** o CEO grava `.claude/plans/PLAN-194/w3b1/rail-round-3.md` no formato de
`.claude/plans/PLAN-194/w3b1/rail-record-template.md` (os das rodadas 1 e 2 entram como
`rail-round-1.md` e `rail-round-2.md`; os registros são contíguos e o SIGN lê só o último). Linhas da
saída do revisor que comecem com três crases (mesmo indentadas) têm as crases trocadas por outro
marcador, com a troca declarada na triagem: indentar não é rota.
