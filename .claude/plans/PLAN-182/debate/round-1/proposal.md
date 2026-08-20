---
plan: PLAN-182
round: 1
created_at: 2026-08-20
---

# PLAN-182 — proposta levada ao round 1

> Destilacao do plano no momento do despacho. O plano FOI alterado
> pelos ajustes do consenso; este arquivo preserva o que os criticos
> receberam, nao o estado atual.

## Isolamento de runtime state por projeto

O diretorio de runtime state resolve, sem env, para o literal
`$HOME/.claude/projects/ceo-orchestration`. Todo projeto com o framework
instalado compartilha log, chave HMAC, salt, locks e state.

**Tese:** isto NAO e decisao em aberto. O ADR-001 esta ACCEPTED desde
2026-04-11 e define o caminho com `<project-slug>`, nao literal; a
variavel `CLAUDE_PROJECT_DIR_NATIVE` que ele especifica e consumida por
ZERO arquivos. O plano implementa uma decisao adiada ha quatro meses.

**Escopo:** W0 levantamento (familia comportamental, matriz de
precedencia por artefato, inventario do diretorio, atribuibilidade,
reconciliacao dos resolvedores ja shipados) -> W1 resolvedor unico ->
W2 decisao sobre o log historico -> W3 installer e adopters.

**Decisoes em aberto levadas ao debate:** namespace de escrita; semantica
de per-installation no ADR-079; ordem de execucao; o que fazer com ~68%
do log que nao e atribuivel a projeto nenhum.
