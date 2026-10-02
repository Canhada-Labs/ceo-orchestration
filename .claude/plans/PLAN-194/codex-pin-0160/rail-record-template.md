# rail-round-N — re-pin do Codex 0.156.1 → 0.160.0 (PLAN-194, pack `codex-pin-0160`)

Rail-Round: N
Rail-Subject: .claude/plans/PLAN-194/codex-pin-0160/ (os seis arquivos do pack)
Rail-Subject-Commit: <sha do commit de materiais revisto>
Rail-Subject-sha256:
    OWNER-PIN-SIGN.sh                 <sha256>
    README.md                         <sha256>
    codex-cli-pin-manifest.json.new   <sha256>
    codex-cli-pin.txt.new             <sha256>
    pin-0160-approved.md              <sha256 de `git show <commit>:…/pin-0160-approved.md` — Anchor-SHA e Data por preencher>
    rehearse-pin-0160.sh              <sha256>
Rail-Reviewer: <codex-cli versão, `--verify-codex-pin` = verified, modo read-only, modelo e esforço SERVIDOS>
Rail-Codex-Config-sha256: <sha256 do ~/.codex/config.toml do Owner tirado ANTES desta rodada>
Rail-Prompt: .claude/plans/PLAN-194/codex-pin-0160/rail-prompt.md
Rail-Rehearsal: <PASS/FAIL do placar do rehearse-pin-0160.sh sobre estes bytes, com a data>
Rail-Reviewer-Verdict: <GO | GO-WITH-CONDITIONS | NO-GO — igual ao valor da ÚLTIMA linha `VERDICT: ` do bloco verbatim>
Rail-Verdict: <APPROVE | DECLARED-P2 | FINDINGS>
Rail-Findings: P0=<n> P1=<n> P2=<n>

O `OWNER-PIN-SIGN.sh` deste pack NÃO lê este registro: o molde 0156, de que ele é gerado, não tem gate
de rail. O registro é a trilha de auditoria da série, e o CEO só entrega o pack ao Owner com o último
registro em APPROVE ou DECLARED-P2. Mesmo assim, ele segue a gramática da W3b.1
(`.claude/plans/PLAN-194/w3b1/rail-record-template.md`), para que um gate futuro o leia sem conversão:

- cada campo acima aparece UMA vez (`Campo: valor`, no início da linha);
- exatamente UMA linha igual a `## Saída do revisor`;
- nessa seção, exatamente UM bloco verbatim: abre com uma linha IGUAL a ```` ```text ```` e fecha com a
  próxima linha IGUAL a ```` ``` ````; uma linha `## …` dentro dele é saída do revisor, não encerra a
  seção;
- dentro do bloco, nenhuma OUTRA linha pode ser cerca (sem os espaços e tabs iniciais, começar com
  ```` ``` ```` é recusa — indentar não é rota); ao copiar a saída do revisor, troque as crases dessas
  linhas por outro marcador e declare a troca na triagem;
- o veredito do revisor é o valor da ÚLTIMA linha do bloco que começa com `VERDICT: ` (GO,
  GO-WITH-CONDITIONS ou NO-GO), e precisa ser igual a `Rail-Reviewer-Verdict`;
- APPROVE ⇒ revisor GO e `P0=0 P1=0 P2=0`; DECLARED-P2 ⇒ revisor GO ou GO-WITH-CONDITIONS,
  `P0=0 P1=0 P2=<n>` com n > 0 e itens na seção `## P2 declarados`.

Os achados das lanes Claude (2 refutadores, na MESMA rodada do Codex) entram na triagem e no
Rail-Verdict/Rail-Findings agregados; a linha `VERDICT:` literal conferida é a do Codex. Os registros de
1 a N são contíguos e commitados antes da sentada do Owner (materiais = último land).

## Saída do revisor

```text
<saída verbatim do Codex, caminhos locais redigidos; linhas que comecem com três crases têm as crases trocadas>
VERDICT: <GO | GO-WITH-CONDITIONS | NO-GO>
```

## Triagem

- <lane Codex e lanes Claude: achado, severidade, cura (regenerar o pack, se o achado for em arquivo gerado) ou declaração>

## P2 declarados

- <só com DECLARED-P2>
