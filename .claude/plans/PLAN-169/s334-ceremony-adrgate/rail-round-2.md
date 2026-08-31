# wave-adrgate — rail codex rodada 2 (sombra RE-DERIVADA da base 2858924, S334)

Rail-Verdict: APPROVE

Comando: `codex exec review --uncommitted --skip-git-repo-check -c sandbox_mode="workspace-write"`,
do diretório da sombra, stdin redirecionado de /dev/null. Saída bruta:
`<scratchpad S334>/adrgate-r2.txt`. Snapshot sha256 dos 4 paths
antes/depois: **TREE INTACT** (shasum -c verde).

## Doutrina cumprida

A sombra da r1 foi DESCARTADA e re-derivada da base que já contém a cura
r1 (`2858924`) — sombra re-derivada ganha o rail inteiro, não um diff da
cura (regra paga no pacote E, S329).

## O que o revisor fez (verificação ativa, não leitura)

- Contou os steps do job de governança do `validate.yml` da sombra por
  parse próprio e conferiu a posição dos 2 steps novos (após o
  check-agents-md, antes do check-doc-skill-paths).
- Rodou o corpus real contra o checker: PASS clean.
- Validou o índice regenerado e a sintaxe do workflow.
- Rodou os testes alvo.

## Veredito verbatim

> The declared exemptions match the checker's mandatory-fire semantics,
> and the ADR corpus, generated index, workflow syntax, and targeted
> tests all validate successfully.

Zero achados (nenhum bloco de review comments). Rodada limpa sobre a
superfície FINAL do patch — o critério de parada do rail do PATCH está
satisfeito (r1: 1 P2 real curado com arquitetura; r2: limpa na sombra
re-derivada). Os SCRIPTS da cerimônia (finalize/SIGN/LAND/harness)
ganham rail próprio (rail-materials-round-N.md) quando prontos —
rodada limpa do patch não os cobre.
