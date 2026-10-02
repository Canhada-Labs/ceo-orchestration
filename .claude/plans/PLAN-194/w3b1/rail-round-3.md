# rail-round-3 — W3b.1 do PLAN-194 (FINAL, com anexo)

Rail-Round: 3
Rail-Subject: .claude/plans/PLAN-194/w3b1/w3b1.patch
Rail-Subject-sha256: 7dccad8354cc4fe0b59abf545893f6e923f19d07a08c7c5bbedad7cbe1f09773
Rail-Sentinel-sha256: fad1cdc4f0431aae4b463702d138910d552a582b4ce708d0c9da6dc9204e6c27
Rail-Reviewer: codex-cli 0.156.1, exec read-only, modelo do config do usuário (gpt-6-astra), memories e chronicle desligados
Rail-Prompt: .claude/plans/PLAN-194/w3b1/rail-prompt.md
Rail-Reviewer-Verdict: GO
Rail-Verdict: DECLARED-P2
Rail-Findings: P0=0 P1=0 P2=4

## Saída do revisor

```text
NENHUM ACHADO no anexo. As duas curas são reais, inclusive para troca somente da `.asc`; nenhum defeito novo identificado. As frases alteradas do sentinel conferem. Worktree inalterado.

VERDICT: GO
```

## Triagem

- Rodada 3, Codex: NO-GO — P1: a conferência pós-commit não conferia a `.asc`; P1: a normalização da raiz escondia diagnóstico diferente.
- Rodada 3, refutadores Claude (texto e mecânica): 1 P1 cada, na mesma normalização (no macOS com TMPDIR padrão ela nem normalizava a base), e P2.
- Anexo: normalização REMOVIDA (comparação igual à da W1; ruído de caminho absoluto com base vermelha declarado como falha fechada); pós-commit por igualdade da árvore do índice com HEAD^{tree} e pai = Anchor-SHA (T28: troca só da `.asc` reprova); P2 de texto. Codex, checagem final estreita: GO (saída acima).

## P2 declarados

- Comparação do validate-governance: as linhas de CONTINUAÇÃO de dois avisos do produtor (sem o prefixo de aviso) ficam no multiconjunto — com a base vermelha, só podem reprovar (falha fechada).
- «Chegou ao resumo» usa `grep -q 'Errors:'` sem âncora; o «detalhe de cada violação» vai até onde o próprio produtor o imprime (`head -20` nas invariantes, `tail -25` no oráculo de hooks).
- Gramática do bloco verbatim: a W3b.1 tira `[ \t]+` antes de reconhecer cerca e a W1 tira `[[:space:]]+` (diferença só para \r, \v ou \f no início da linha); o T6-unclosed confere a mensagem genérica «registro recusado —»; não há cenário para seção ausente ou repetida nem para bloco sem VERDICT.
- Com a base vermelha no validate-governance, um detalhe com caminho absoluto da árvore reprova por ruído (falha FECHADA): a comparação não normaliza caminhos (declarado também no texto assinável).
