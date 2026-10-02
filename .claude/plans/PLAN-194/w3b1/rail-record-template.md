# rail-round-N — W3b.1 do PLAN-194 (modelo do registro que o OWNER-W3B1-SIGN.sh aceita)

Rail-Round: N
Rail-Subject: .claude/plans/PLAN-194/w3b1/w3b1.patch
Rail-Subject-sha256: <sha256 do w3b1.patch>
Rail-Sentinel-sha256: <sha256 de `git show HEAD:.claude/plans/PLAN-194/w3b1-approved.md` — o texto com os 4 campos por preencher>
Rail-Reviewer: <codex-cli versão, modo, modelo>
Rail-Prompt: .claude/plans/PLAN-194/w3b1/rail-prompt.md
Rail-Reviewer-Verdict: <GO | GO-WITH-CONDITIONS | NO-GO — igual ao valor da ÚLTIMA linha `VERDICT: ` do bloco verbatim>
Rail-Verdict: <APPROVE | DECLARED-P2 | FINDINGS>
Rail-Findings: P0=<n> P1=<n> P2=<n>

Gramática que o SIGN confere no P0 (a mesma da W1; sem arquivo de controle próprio neste pacote, não há
linha Rail-Control-sha256 — o controle é `check-model-deprecations.py`, do repositório, conferido pelo
SIGN no HEAD e com o patch):

- cada campo acima que o SIGN lê aparece UMA vez (`Campo: valor`, no início da linha); os dois sha256
  batem com o HEAD;
- exatamente UMA linha igual a `## Saída do revisor`;
- nessa seção, exatamente UM bloco verbatim: abre com uma linha IGUAL a ```` ```text ```` e fecha com a
  próxima linha IGUAL a ```` ``` ````. O bloco é lido INTEIRO até o fechamento: uma linha `## …`
  dentro dele é saída do revisor, não encerra a seção;
- dentro do bloco, nenhuma OUTRA linha pode ser cerca: uma linha que, sem os espaços e tabs iniciais,
  começa com ```` ``` ```` é recusada — INDENTAR NÃO É ROTA; ao copiar a saída do revisor, troque as
  crases dessas linhas por outro marcador e declare a troca na triagem; fora do bloco, na mesma seção,
  idem;
- o veredito do revisor é o valor da ÚLTIMA linha do bloco que começa com `VERDICT: ` (GO,
  GO-WITH-CONDITIONS ou NO-GO), e precisa ser igual a `Rail-Reviewer-Verdict`;
- recusa: seção ausente ou repetida; cerca ausente, duplicada, mal formada (abertura diferente de
  ```` ```text ````, outra linha de cerca dentro do bloco, cerca indentada) ou não fechada; bloco sem
  linha `VERDICT: `;
- APPROVE ⇒ revisor GO e `P0=0 P1=0 P2=0`; DECLARED-P2 ⇒ revisor GO ou GO-WITH-CONDITIONS,
  `P0=0 P1=0 P2=<n>` com n > 0 e itens na seção `## P2 declarados`.

Os achados das lanes Claude (refutadores) entram na triagem e no Rail-Verdict/Rail-Findings agregados;
a linha `VERDICT:` literal conferida é a do Codex. Os registros de 1 a N precisam ser contíguos e
commitados.

## Saída do revisor

```text
<saída verbatim do Codex, caminhos locais redigidos; linhas que comecem com três crases têm as crases trocadas>
VERDICT: <GO | GO-WITH-CONDITIONS | NO-GO>
```

## Triagem

- <lane Codex e lanes Claude: achado, severidade, cura ou declaração>

## P2 declarados

- <só com DECLARED-P2>
