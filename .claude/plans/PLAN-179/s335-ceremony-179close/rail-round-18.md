# wave-179close — rail codex rodada 18 (sombra pós-curas r17, S336 2026-09-01)

Rail-Verdict: CHANGES-REQUESTED (2 P2 — ambos verificados REAIS; curados ANTES da r19)

Forma prompt-only. Saída: `<scratchpad S336>/179close-r18.txt` (8.227
linhas — a mais curta da wave), exit 0. TREE-INTACT: manifest sha256
pré/pós byte-idêntico.

## Os achados (verificação + cura)

1. **[P2] Primeiro match inverificável caía para restart mais novo** —
   VERIFICADO: se o start REAL é uma linha fail-open (`hmac:null`) e um
   restart pós-compact vem assinado depois, o `continue` deixava o
   restart ancorar — janela encolhida ⇒ escrita entre os dois starts
   sumia num `absent` falso, contra o contrato oldest-match. CURA: match
   inverificável ⇒ `(None, "none")` imediato, nunca um candidato mais
   tardio. O teste r2 do forged-anchor JÁ esperava essa semântica (sem
   candidato posterior); os testes de compact-restart e legacy-prefix
   seguem verdes (o oldest assinado verifica). Controle novo:
   `test_unverifiable_oldest_start_never_falls_to_restart`.
2. **[P2] TOCTOU no stat do diretório** — VERIFICADO: com overlap
   suportado, rename/delete entre o stat pré-scan e o `iterdir` escapava
   da flag estrutural. CURA: re-stat do dir PÓS-scan (o mtime é
   pegajoso — bump em qualquer ponto até ali aparece agora); o resíduo
   pós-re-stat é TOCTOU irredutível de observador stat-only, DECLARADO
   em comentário. Controle: `test_dir_mtime_rechecked_after_scan` (stat
   de duas fases no dir — 1ª leitura velha, 2ª na janela ⇒ error).

## Verificação pós-cura

Bateria declarada (9 suítes) na sombra pós-cura: **344/0** (8.02s) —
`EXPECTED_UNIT_PYTEST_PASSED` 342→344 (+2 controles). Curas confinadas a
2 paths do EXPECTED. Refinalize + r19 na sequência.
