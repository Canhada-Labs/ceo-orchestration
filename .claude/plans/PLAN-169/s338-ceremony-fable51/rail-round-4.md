# wave-fable51 — rail codex rodada 4 (sombra re-derivada pós-r3, base dc72bf1, 2026-09-01 S338)

Rail-Verdict: CHANGES-REQUESTED (1 P1 de PROCESSO — respondido, igual às r1–r3 — + 1 P2 REAL, curado ANTES da r5)

Comando: `codex exec review --uncommitted --skip-git-repo-check
-c sandbox_mode="workspace-write"`, do diretório da sombra, stdin
`</dev/null`. Saída bruta: `<scratchpad S338>/fable51-r4.txt` (8.201
linhas). Snapshot sha256 do diff antes/depois: TREE-INTACT. O próprio
codex abre com «The functional tests pass»; as curas r1–r3 não foram
reabertas (rank, cache-read, alias bare, `price_for`, `success-receipt`).

## Os achados

1. **[P1, PROCESSO — mesmo das r1–r3]** «o sentinel citado não está no
   checkout». Estrutural da sombra (o finalize recusa path fora do EXPECTED;
   sentinel + `.asc` são materiais commitados antes do SIGN; o G5 do LAND
   prova cada path canônico via `_sentinel_grants_path` vivo). Sem cura.
2. **[P2, REAL] `test_a4_pricing_doctrine.py:_EXPECTED_RATES` certificava o
   5.1 como «sem prêmio de long-context a 1M» enquanto a linha que EU
   escrevi em `docs/provider-pricing.md` dizia «Not probed»** — o teste
   afirmava uma evidência que o doc negava (falso-verde por
   incoerência). A evidência EXISTE, mas é DOCUMENTAL, não a sonda viva do
   PLAN-137: a página oficial de pricing (2026-09-01), seção «Long context
   pricing», diz que «Claude 4.6 and later models … include the full 1M
   token context window at standard pricing». CURA: a linha do doc passa a
   «**No** — documentary: …» citando a seção e a data, e nomeando que a
   sonda viva NÃO foi re-rodada; o comentário do `_EXPECTED_RATES` diz o
   mesmo. O 5.1 fica no oráculo A4 com a natureza da evidência declarada —
   retirá-lo deixaria o rate card da frota corrente sem regressão.

## Verificação das claims

`test_a4_pricing_doctrine.py:36-45` lido (docstring: «rates the A4 gate
confirmed carry NO long-context premium at the full 1M window»);
`docs/provider-pricing.md` §"1M window?" lido; página de pricing lida
(seção «Long context pricing»). A correção é de COERÊNCIA doc↔teste, sem
mudar número. Pós-cura: sombra re-derivada do zero, bateria e rail r5.
