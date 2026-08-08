---
plan: PLAN-169
round: 2
archetype: VP Engineering
created_at: 2026-08-08
---

# VP Engineering — round 2 (PLAN-169 v2.2)

> Alvo: o texto v2.2 atual. Método idêntico ao round 1 — rodei
> `_matches_canonical_guard` (`check_canonical_edit.py:896-915`) contra cada
> superfície NOVA que as curas do rail (r3/r5/r6) trouxeram, em vez de aceitar a
> classificação do texto.

## Verdict

**ADJUST** — tudo do round 1 e do round 2 está respondido; restam **3 must-fix
pequenos e mecânicos**, todos criados pelas próprias curas do rail: o escopo do
W4-C está fechado na unidade errada, o controle plantado do W2.6 agora encosta no
trem, e o aceite do quota-resume mede o hook em vez do arm.

## Summary

- **Round 1 + round 2 fechados no texto:** MF-1 (`:202-207` + W3.2/W3.3), MF-2
  (W4-C `:463-516`), MF-3 (`:518-535` + frontmatter `:10-11`), MF-4/MF-5
  (`:275-336`), MF-6 (`:426-435`, inclusive a contagem exit-2 corrigida para 2),
  MF-7 (W1.7 `:185-195`, W0.10 `:157`), MF-2R (decisão do shellcheck tomada com o
  predicado, `:189-193`), MF-3R (`budget_sessions: 11-14`), U-1..U-4, R-5.
- **As curas do rail alargaram o escopo canônico sem alargar a lista de escopo.**
  W4-C item 3 agora implica `templates/settings/settings.base.json` e
  `settings.user.json` — **ambos CANONICAL** (predicado rodado) — e a rota de
  migração em `scripts/upgrade.sh` (**CANONICAL**), mas o "escopo exaustivo"
  enumera *itens*, e o gate da cerimônia mede *arquivos* (`touched−scope=∅`).
- **A arquitetura do arm mudou de substrato para instrução-ao-modelo** (r6-P1,
  `:292-301`): o hook injeta texto no transcript e o modelo vivo é quem chama
  `CronCreate`. É um caminho legítimo — é o único que alcança o turno autônomo
  longo — mas o teste declarado é fixture sobre o stdout do hook.

## Risks

- **R-1 (VIVO, agora com evidência) — inchaço de pack por omissão de
  classificação; a lição-mãe da S296 reaparece por construção.** Entre a v2 e a
  v2.2, **W3 foi de "3-5 itens fechados" para 7 + 2 inclusões condicionais**
  (`:762-766`) e **W4-C foi de 7 para 8 itens**, com o item 3 virando quatro
  superfícies + rota de migração + testes (`:478-489`) e o item 6 ganhando uma
  decisão de piso de CLI + `SUPPORT.md` (`:494-501`). Ambos cresceram numa única
  passada de rail. A regra "item novo = wave nova, nunca inchaço de pack" está
  escrita e é a mitigação certa; o risco é que ela seja aplicada ao *item* e não
  ao *arquivo* (ver MF-A).
- **R-2 (VIVO, e agravado pela nova ordem) — interação W1 × W2.6 sobre o MESMO
  arquivo.** `.claude/.framework-version` é observado pelo e2e de ownership e
  governado pelo veredito de propriedade (`upgrade.sh:2109-2144`,
  `_framework_manifest_set.sh:141,301`), e o W2.6 planta um controle positivo que
  o dessincroniza (`:215`). Na ordem nova (`W0→W1→W2→W6.1`, `:127-133`) o W2 roda
  **imediatamente antes do corte da rc.2**, e `release.yml:84-97` compara
  `marcador == VERSION` fail-closed. Um controle esquecido na árvore é RED de
  release, e atravessar a janela do nightly (`43 6 * * *`) é RED de ownership com
  causa fabricada.
- **R-6 (NOVO) — a janela de congelamento do main não tem custo de saída
  declarado.** `:130-133` proíbe qualquer commit em main do corte da rc.2 até o
  GA, e `:634-635` diz que se `main` avançar vira rc.3 com hold reiniciado. A rota
  existe; o que falta é dizer o que acontece se um CI vermelho legítimo aparecer
  **durante** o hold — hoje a escolha implícita é entre quebrar o freeze e esperar
  24h com vermelho na janela.
- **R-7 (NOVO) — o arm do quota-resume saiu do substrato e virou
  instrução-ao-modelo.** `:292-301`: o hook "INJETA instrução no transcript" e o
  modelo "a lê entre tool calls e chama CronCreate no mesmo turno". Isso é
  probabilístico por construção — a mesma classe que o repo distingue de
  enforcement — e o teste declarado é *"output do hook contém a instrução"*, que
  prova emissão, não arm (lição livefire ×2: fixture verde ≠ enforcement provado).
- **R-8 (NOVO) — `scripts/upgrade.sh` é tocado por DOIS packs em sequência.** W3
  item 1 edita `:1564-1577` (B.a) e W4-C item 3(d) edita a migração em
  `:2235-2252`, com o trem v1.3.0 e o freeze entre os dois. Se o staged do W4-C
  for preparado antes do W3 landar, o `shasum -c` bate em conteúdo velho — e é
  exatamente a classe que o rail r1 acabou de pegar no script do 167 (staged stale
  que reverteria um plano posterior).

> **Retirados como resolvidos (para o conjunto ser comparável):** R-3 (runbook com
> `\s` executado pelo W6.1) → fechado por W0.10 `:157` + ordem `W0` primeiro;
> R-4 (assimetria probe-first W4.1 vs W4.2) → fechado por W4.1.0 `:281-285`;
> R-5 (contaminação da postura do experimento) → fechado por `:531-535` + rota de
> clone `:386-390`.

## Must-fix (blocking)

**MF-A — O "escopo FECHADO" do W4-C está fechado em ITENS; o gate mede ARQUIVOS.**
O protocolo do pack é `touched−scope=∅` (`:514-516`), verificado por caminho. Mas
o escopo exaustivo (`:472-513`) lista *decisões*, e as curas do rail arrastaram
arquivos canônicos que não aparecem em lugar nenhum como caminho. Predicado
rodado agora:

| Caminho implicado pelo W4-C | Item | Predicado |
|---|---|---|
| `templates/settings/settings.base.json` | 3(b) | **CANONICAL** |
| `templates/settings/settings.user.json` | 3(c) | **CANONICAL** |
| `scripts/upgrade.sh` (migração `:2235-2252`; gate de piso `:189-200`) | 3(d), 6 | **CANONICAL** |
| `.claude/hooks/check_quota_resume.py` (novo) | 1 | **CANONICAL** |
| `SUPPORT.md` (piso de CLI) | 6 | free |
| `env-inventory.json` | W4.1 | free |

Cura: **anexar ao W4-C uma lista de ARQUIVOS** (o escopo do sentinel), derivada
do predicado, antes de assinar — e marcar quais são livres, para que o
`touched−scope` não estoure no meio do land. Sem isso o escopo está fechado na
dimensão em que ninguém mede.

**MF-B — O controle positivo do W2.6 precisa ser declarado TRANSITÓRIO.**
Uma linha no W2.6: plantar o marcador dessincronizado, observar o vermelho e
**despantar no MESMO commit**; proibido atravessar a janela do nightly
(`43 6 * * *`) e proibido existir no HEAD candidato da rc.2. A ordem nova
(`W2` → `W6.1`) transformou um risco de higiene em adjacência direta com o corte
da tag, onde o assert `marcador == VERSION` é fail-closed.

**MF-C — O aceite do quota-resume tem de medir o ARM, não o stdout do hook.**
AC-4 (`:664-670`) pede "simulação (job ÚNICO no horário efetivo)", e o W4.1 pede
fixture do output do hook (`:300-301`). Falta a frase que liga as duas pontas:
o controle end-to-end é **hook dispara ⇒ um job EXISTE, no horário efetivo, e
exatamente um**; o controle negativo é `<90%` ou job já armado ⇒ **nenhum job
novo**. Enquanto o aceite puder ser satisfeito por uma string no stdout, o
mecanismo probabilístico do meio (R-7) fica sem prova.

## Nice-to-have

- **Enumerar os eventos Owner-only no checklist de retorno.** Contando o texto:
  sentinel W3, sentinel W3-K, sentinel W4-C, assinatura do pré-registro do W5
  (`:606`), verdito rc.2, verdito GA v1.3.0, verdito rc.1 e GA v1.4.0, mais as
  tags e a aprovação `production-npm` — **≥8 atos de assinatura**. O Owner deve
  ver a conta antes, não descobrir ato a ato.
- **Declarar o instrumento do E0.** `:562-576` define a métrica (S) e a regra de
  decisão com banda intermediária — o que falta é dizer **com o quê** o wall-clock
  dos 14 planos é decomposto em máquina/humano/morto. Se o audit log não carrega
  os marcos necessários, "custo ~zero" deixa de valer, e o gate que financia o
  PLAN-170 vira o item caro.
- **Nomear `SUPPORT.md` no W4-C item 6.** É livre, mas a decisão de piso de CLI
  altera contrato publicado; melhor estar na lista do que aparecer no `touched`.

## Unseen

- **O plano recomenda aos adopters desligar a ferramenta com que ele próprio se
  executa.** W4-C item 8 põe `disableWorkflows: true` como default de adopter se
  o probe (b) confirmar o bypass do gate de spawn (`:506-513`) — enquanto o
  mandato do Owner é *"use workflow"* (`:42-43`) e o W0.0 mantém Workflow vivo em
  modo read-only. A exceção "operador-supervisionado" precisa de **critério
  verificável** (o que conta como supervisão?), senão o framework publica uma
  postura que ele mesmo não segue e a diferença fica sem justificativa auditável.
- **A rota de clone do fleet (r2-P2, `:386-390`) é ela própria uma superfície de
  governança.** Um clone com `crossSessionInbound` relaxado é um clone onde a
  única alavanca fail-closed nova está desligada; vale declarar no pré-registro
  que o clone não tem GPG, não tem superfície canônica e não é ancestral de
  nenhuma tag — parte está em `:531-535`, mas a proibição de o clone virar origem
  de commit não está escrita.
- **Nada no texto diz o que acontece com o W4-C se o probe W4.2.0 vier
  ambíguo.** Itens 3 e 8 são "pós-resposta U-1" / "SE o probe confirmar"; se o
  probe der resultado parcial (o caso mais provável num substrato de 4 dias), o
  pack não tem regra de decisão e a wave para sem critério.

## What I would NOT change

- **A ordem de execução nova (`W0→W1→W2→W6.1→W3→…`, `:127-133`).** É a melhor
  adição da v2.2 e resolve na raiz a contaminação de trem que o D1 apontou:
  o HEAD candidato da rc.2 passa a ser construtivamente o que a v1.3.0 deve
  conter, em vez de depender de disciplina.
- **W1 como está, com W1.7-CI fora do gate do 62/3** (`:189-195`). A decisão que
  eu pedi no MF-2R foi tomada com o predicado rodado e a consequência de trem
  declarada — inclusive a opção do Owner de puxar o shellcheck para antes da rc.2
  ao custo nomeado de uma cerimônia extra.
- **W4-C existir com escopo enumerado (forma (b)).** Retiro qualquer resíduo da
  minha recomendação (a): com a lista na mesa, a recusa fundamentada no consensus
  §2 é a leitura certa do mandato. Minha objeção restante é de *unidade* de
  escopo (MF-A), não de existência da wave.
- **E0 com S incluindo o tempo-morto e a banda intermediária pré-definida**
  (`:566-576`). Isso é melhor do que a versão que eu endossei no round 1 — excluir
  espera de CI/quota superestimaria o teto, e pré-definir 0,20 < S < 0,40 tira o
  juízo post-hoc da mesa.
- **Bateria → PLAN-170 com orçamento próprio e gatilho nomeado**, e **anexos de
  pesquisa arquivados fora do repo** com ponteiro. Ambos resolvem exatamente o que
  o MF-3 pedia, sem transformar o fechamento em um plano de experimento.
- **`budget_sessions: 11-14` e o orçamento com escopo explícito no frontmatter**
  (`:10-11`). Número que o texto sustenta, com a bateria excluída de forma
  declarada.
