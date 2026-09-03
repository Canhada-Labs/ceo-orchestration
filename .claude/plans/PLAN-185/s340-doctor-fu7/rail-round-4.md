Rail-Verdict: CHANGES-REQUESTED (r4 no land, S340: 1 P1 + 1 P2 REAIS — curados na v4 do derivador; r5 a seguir)

# Rail round 4 — land do pack `doctor-fu7`, árvore re-derivada v3 (S340, 2026-09-03)

Rodada sobre a árvore viva staged após a v3 (`codex exec review --uncommitted`, gpt-5.6-sol,
~9,5 min; TREE-INTACT `fb1d1cc3…`). Dois achados, verificados e curados.

| # | sev | sítio | achado (codex) | verificação | cura |
|---|---|---|---|---|---|
| 1 | P1 | `scripts/doctor.sh` (loop de ingest) | `read -r` descarta (ou, no Bash 3.2, trunca em) um byte NUL ANTES de qualquer check por campo: `<sha>  victim\0ignored` é lido como `victim`; com digest batendo, doctor imprime OK e sai 0 sem `Dropped` | REAL: o predicado de bytes de controle só vê o que `read` entrega; NUL nunca chega a ele | E15: antes do loop, o manifesto CRU é contado com `LC_ALL=C tr -cd '\000'`; qualquer NUL ⇒ ERROR nomeado («unparseable — corrupted or tampered») e `exit 2`, a mesma classe do manifesto vazio/corrompido — input inparseável falha FECHADO. E16 = perna e2e D.9 (fixture com exatamente 1 NUL; asserta a recusa nomeada e rc≠0) |
| 2 | P2 | `EVIDENCE.md:5-6`, `baseline-diff.txt`, `regen-baseline.txt` | o sha do diff e a transcrição de 9 edições descreviam a v1; o baseline staged tem 2 fingerprints novos (iconv) ausentes dos dois artefatos — a evidência de reprodutibilidade atestava bytes diferentes do patch entregue | REAL: os três artefatos eram os da sombra do builder | `baseline-diff.txt` regenerado (HEAD × final), `regen-baseline.txt` = cópia do baseline final (com os 2 sítios declarados), EVIDENCE com banner de versão e a seção «Land — S340» descrevendo a v4 |

Colateral do próprio land (não do codex): a regeneração do bloco `EDITS` por `repr()` na v3 gerou
linhas de >5 000 chars com «—», que disparam o bug do tokenizer C do CPython ao EXECUTAR o script
(«Non-UTF-8 code … no encoding declared»; `py_compile`/import passam por outro caminho). A v4
reescreve o bloco em literais por linha (≤156 chars) e declara `# -*- coding: utf-8 -*-`.

Controle positivo (E16 = D.9): árvore HEAD + derivador v3 + e2e v4 → D.9 vermelho em «sem recusa
de NUL»; D.7/D.8 verdes nessa árvore. Fora do escopo: nada. A r5 corre sobre a árvore v4.
