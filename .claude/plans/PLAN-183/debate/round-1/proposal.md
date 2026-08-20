---
plan: PLAN-183
round: 1
created_at: 2026-08-20
---

# PLAN-183 — proposta levada ao round 1

> Destilacao do plano no momento do despacho. O plano FOI alterado
> pelos ajustes do consenso; este arquivo preserva o que os criticos
> receberam, nao o estado atual.

## Adopter fitness

Um adopter real instalou o framework e reportou o que nao funcionou.
A primeira redacao deste plano dizia que o framework nunca fora
exercitado como adopter.

**Tese (corrigida no proprio round 1):** o instrumento de adopter EXISTE
e roda por-PR (`smoke-install.sh` + `smoke-install.yml`). A causa-raiz e
mais estreita: o escopo dele exclui `.github/`, e ele nunca ATIVA nem
EXECUTA o CI que entrega.

**Escopo:** W0 reproduzir e medir (hipotese aritmetica do timeout; taxa
de censura a direita; estender smoke-install) -> W1 ponteiro portatil e
retroativo -> W2 CI que passa no adopter -> W3 catalogo e a regra de
VETO -> W4 timeout, gateada pela W0.

**Decisoes em aberto levadas ao debate:** destino dos steps de
`unittest discover`; se o repo descartavel vira fixture permanente; e se
o gate de drift template-vs-vivo e diff estrutural ou congelamento.
