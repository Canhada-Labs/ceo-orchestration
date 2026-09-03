Rail-Verdict: CHANGES-REQUESTED (r2 no land, S340: 1 P1 + 2 P2 — os três REAIS e CURADOS na v2 do derivador; r3 a seguir)

# Rail round 2 — land do pack `doctor-fu7` na árvore viva (S340, 2026-09-03)

Contexto: a r1 (sombra do builder) foi APPROVE. No land, a rodada sobre a árvore viva staged
(`codex exec review --uncommitted`, gpt-5.6-sol, ~10 min; TREE-INTACT `a17a7c8b…` antes e
depois) devolveu REJECT com três achados. Todos verificados contra os arquivos e curados
re-derivando: os 3 paths voltaram ao HEAD (`git checkout HEAD -- …`) e o derivador v2 foi
aplicado do zero (12 edições/3 paths; `--check-only` recusa a 2ª aplicação).

| # | sev | sítio | achado (codex) | verificação | cura |
|---|---|---|---|---|---|
| 1 | P1 | `scripts/doctor.sh:420-423` (+ `_relpath_unsafe`) | o sanitizador só rejeitava `\n \r \t`; um relpath/alvo com outro byte de controle (ex.: `ESC[2J`) passava, virava MISSING/DRIFT e o nome era interpolado CRU no terminal do operador | REAL: `*[$'\n\r\t']*` nos dois sítios; `_mark_dropped` sanitiza, mas o registro nem chegava lá | E3 alargada e E10: `*[[:cntrl:]]*` nos dois sítios (qualquer byte de controle é inseguro). Controle positivo E12 = perna e2e D.7 (relpath com ESC → DROPPED nomeado, zero ESC cru no log, rc≠0) |
| 2 | P2 | `scripts/doctor.sh:741-745` | com TODOS os registros descartados, `SANITIZED` fica vazio e o exit 2 de «manifesto vazio» dispara ANTES do relatório de descartes — o operador não vê o que foi descartado | REAL: o ramo `if [ ! -s "$SANITIZED" ]` está ~250 linhas antes do relatório | E11: o ramo vazio imprime o relatório (lista capada + `Dropped:`) antes do ERROR |
| 3 | P2 | `apply-doctor-fu7.py:420-425` | a recusa por censo (subprocesso ≠ 0 ou conjunto de sítios mudou) corria DEPOIS de escrever as edições — árvore parcialmente aplicada com «RECUSADO» | REAL: `_apply` escrevia E1–E9 e só então regenerava o baseline | `_apply` faz snapshot de cada arquivo antes da 1ª escrita e rollback em QUALQUER falha; controle positivo: censo sabotado (`exit 1`) em worktree → recusa e porcelain só com o sabotador |

Fora do escopo desta rodada: nada. A r3 corre sobre a árvore viva re-derivada (v2) antes do commit.
