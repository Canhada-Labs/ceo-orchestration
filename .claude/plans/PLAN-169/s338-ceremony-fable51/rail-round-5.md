# wave-fable51 — rail codex rodada 5 (sombra re-derivada pós-r4, base dc72bf1, 2026-09-01 S338)

Rail-Verdict: APPROVE

Comando: `codex exec review --uncommitted --skip-git-repo-check
-c sandbox_mode="workspace-write"`, do diretório da sombra, stdin
`</dev/null`. Saída bruta: `<scratchpad S338>/fable51-r5.txt` (12.186
linhas). Snapshot sha256 do diff antes/depois: TREE-INTACT.

## Veredito do codex, verbatim no que importa

«The functional changes and targeted tests pass, but the patch modifies
canonical-guarded files without the mandatory Owner-signed sentinel
evidence.» Um único item: **[P1] Add the referenced Owner-signed sentinel**.

## Por que isto é APPROVE do PATCH

- **Zero achados de código, teste ou doc.** As curas das r1–r4 (rank do
  `_tier_rank`, multiplicador de cache-read por modelo, alias bare
  ambíguo → transcript, `price_for` só pin datado, espelho do
  `success-receipt`, coerência doc↔teste A4) não foram reabertas, e o
  codex afirma explicitamente que os testes direcionados passam.
- **O item restante é o artefato que a CERIMÔNIA produz, não um defeito
  do patch.** O sentinel `wave-fable51-approved.md` e o `.asc` vivem na
  árvore viva (materiais commitados ANTES do SIGN, P0-d) e NÃO podem
  existir na sombra por construção — o `finalize-fable51.sh` RECUSA
  qualquer path fora do EXPECTED (passo 1). A autorização de cada um dos
  5 paths canônicos é provada no LAND (G5) pela MESMA função que o hook
  usa, `_sentinel_grants_path`, contra a assinatura GPG do Owner (G1), e
  o KERNEL (`settings.json`) pelo override de menor escopo com par
  reason-SLUG + `I-ACCEPT` validado vivo (harness T20e). O rail revisa o
  TEXTO do patch; a autorização é o que o SIGN/LAND acrescentam.
- A mesma leitura foi feita e registrada nas r1–r4 (item «PROCESSO»);
  aqui ela é o ÚNICO item, logo a rodada é limpa quanto ao entregável.

## Critério de parada (explícito, não «rodada limpa = prova»)

Cinco rodadas; 7 achados REAIS curados (3 P1 + 4 P2) em quatro rodadas
consecutivas com re-derivação completa da sombra a cada cura; a quinta
não abriu classe nova. O que o rail NÃO cobre segue declarado no
PROPOSED («O que este patch NÃO faz») e nos residuais do sentinel; a
prova de reprodutibilidade (HEAD + derivador == patch, byte a byte) e a
bateria completa são do LAND, não do rail.
