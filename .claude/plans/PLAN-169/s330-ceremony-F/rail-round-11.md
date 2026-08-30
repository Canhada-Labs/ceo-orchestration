# Pacote F — rail codex rodada 11 (sombra rebaseada em `6961a23`, 2026-08-30 ~18:1x -03)

Rail-Verdict: APPROVE

Rodada LIMPA — zero achados acionáveis. (A linha acima fica nua de
propósito: o parser do SIGN normaliza espaços e exige igualdade exata
com `APPROVE` — qualquer qualificação na mesma linha vira recusa.)

Comando: `codex exec review --uncommitted --skip-git-repo-check -c sandbox_mode="workspace-write"`,
via `rail_round.sh` (snapshot sha256 de cada path staged antes/depois).
Substrato: codex-cli 0.147.0. Saída bruta: `<scratchpad 889bc1bd>/r11.txt`.
Wrapper: **TREE INTACT**.

## O veredito, lido do FIM da saída (regra da S331)

> «No actionable patch-introduced defects were identified. The focused
> generator, installation, and upgrade tests and relevant repository gates
> passed.»

Sem bloco de review comments; o transcript mostra o revisor executando a suíte
focada, os gates de contaminação e stdlib-only, e inspecionando os
`env_overrides` contra a base — tudo verde. Nenhum achado das rodadas 1–10
reapareceu.

## O que esta rodada aprovou

A árvore CONSISTENTE em `6961a23`: os 20 paths do patch com a decisão do Owner
aplicada (roster 29/28), as curas das rodadas 8–10 (sincronização de materiais;
`generator` por VALOR; override NO-OP rejeitado; chave computada sobrevivendo a
base sem a gêmea; numerais do `CLAUDE.md` §5 delta-zero) e os materiais de
cerimônia re-medidos (EXPECTED 277/2, plugin 29/0). O patch está CONGELADO a
partir deste veredito — nenhuma edição nos 20 paths sem nova rodada.

## Fechamento narrativo pós-veredito (declarado, para o auditor)

Após este APPROVE, os materiais NARRATIVOS (fora do patch) foram fechados com
os números que o próprio veredito produziu — `COMMIT-MSG-F.txt` (11 rodadas,
15 defeitos reais, bateria 277, Pair-Rail-Reviewed preenchido), `README-F.md`
(r11 como rodada final) e o sentinel (122 casos no arquivo nuclear). São
correções de contagem pós-facto em material não-assinado e não-revisado pelo
diff; o que o SIGN/LAND validam mecanicamente (EXPECTED-BASELINE) já estava
correto NA árvore aprovada. Nenhum dos 20 paths do patch foi tocado.

## Placar final do rail desta wave

11 rodadas; **15 defeitos REAIS curados com controle vermelho→verde** (11 até
a r7; 2 na r9; 2 na r10), 1 P1 de sincronização de materiais (r8, cura
estrutural commit+rebase), 1 P1 refutado com fundamento (r9, descrevia o fluxo
pré-assinatura), e 1 decisão de produto do Owner (r7 → EXCLUIR, aplicada como
DADO no spec). Bateria 218 → **277 passed / 2 skipped**; arquivo nuclear
61 → **122 casos**.

## Disposição

APPROVE. O pacote segue para `finalize-F.sh` → `OWNER-S331-F-SIGN.sh` →
`OWNER-S331-F-LAND.sh --dry-run` → `OWNER-S331-F-LAND.sh`. A assinatura é do
Owner, por desenho.
