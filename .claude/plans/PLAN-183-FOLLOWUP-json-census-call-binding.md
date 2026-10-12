---
id: PLAN-183-FOLLOWUP-json-census-call-binding
parent: PLAN-183
title: "Censo das leituras JSON do gate do harness: seguir a chamada, não o nome do guard"
status: draft
created: 2026-10-12
owner: CEO
depends_on: [PLAN-183]
level: L2
budget_tokens: "60-120k (estimado em 2026-10-12, S363, sem medição: um teste reescrito, mutantes novos e um land livre com Codex + 1 refutador Claude; reestimar na abertura)"
budget_sessions: 1
context_risk: low
external_wait: "land da W7a do PLAN-183 no `main` (o censo a curar vive no patch da W7a, ainda não landado)"
eta_calendar: "mesma sessão depois do land da W7a. Posição: trem da v1.4.4; pelo PLAN-SCHEMA §1.4, só em `executing` com o PLAN-183 `done`"
tags: [harness-config, census, ast, json, followup, w7, classe]
---

# PLAN-183-FOLLOWUP-json-census-call-binding — o censo segue a chamada, não o nome

> **Lineage (PLAN-SCHEMA §1.4 — "parent shipped with explicit deferred AC
> items").** Condição da última conferência do rail do patch da W7a (lane
> `rx-w7a`, conferência r3y, sujeito `d893285d..94483a01` da sombra w7a): um
> P3 no censo AST do teste, com a condição «follow-up nomeado no material do
> SIGN». O sentinel da W7a (`.claude/plans/PLAN-183/w7a-approved.md`, seção
> «Resíduos declarados (pela forma)») cita este arquivo pelo caminho. Este
> rascunho NÃO reabre a W7a nem muda o patch dela.

## Context

O patch da W7a (`.claude/plans/PLAN-183/w7a/w7a.patch`) faz toda leitura JSON
do `.claude/hooks/check_harness_config.py` (canônico) recusar `NaN`,
`Infinity` e `-Infinity` com `parse_constant=_refuse_constant`: as settings,
as fixtures do replay e a decisão de cada hook sob teste. Com o patch
aplicado, as três leituras estão nas linhas `:221`, `:802-806` e `:868`, e a
função `_refuse_constant` está na `:701`.

Para impedir que uma leitura NOVA nasça sem o guard, o teste
`.claude/hooks/tests/test_check_harness_config.py` ganha no mesmo patch um
censo AST (`_json_census`, `:73`; a condição do guard está na `:89`) e o
teste `test_every_json_read_refuses_non_json_constants` (`:388`), que exige
zero sítios ruins e pelo menos 3 leituras guardadas.

A forma do censo mudou duas vezes no rail, e as duas versões olham o TEXTO
da chamada:

- até `d893285d`, o censo exigia só a PRESENÇA de `parse_constant`;
  `parse_constant=None` e `parse_constant=float` passavam (P3 do `rx-w7a` na
  conferência r3x);
- desde `94483a01`, o censo exige que o valor de `parse_constant` seja um
  `ast.Name` com o id `_refuse_constant`. Ele verifica o guard pelo NOME e
  supõe, sem conferir, que esse nome tem uma única ligação no módulo.

O P3 da conferência r3y, verbatim (registro em
`night/rail/w7a-r3y/claude-rx-w7a-verbatim.md` no scratchpad da S363):

> [P3] `tests/test_check_harness_config.py:87-89` (`_json_census`) — o guard
> é verificado pelo NOME: `_refuse_constant = float` no fim do módulo (ou
> sombra local `def f(): _refuse_constant = float; json.loads(s,
> parse_constant=_refuse_constant)`) passa o censo (reads=3, bad=[]); só os
> testes comportamentais pegam, e só nos 3 sítios existentes.

Reproduzido em 2026-10-12 numa cópia descartável da sombra w7a (HEAD
`e6b5839f`, `git archive` + `git apply` do patch), com o `_json_census` do
próprio teste sobre o hook com o patch aplicado:

| Código acrescentado ao fim do hook | `(reads, bad)` |
|---|---|
| nada (hook do patch) | `(3, [])` |
| `_refuse_constant = float` no nível do módulo | `(3, [])` |
| `def f(s):` com `_refuse_constant = float` local e `json.loads(s, parse_constant=_refuse_constant)` | `(4, [])` |
| `def g(s, _refuse_constant=float):` com a mesma chamada | `(4, [])` |

Nos três mutantes o censo fica verde. No primeiro, a religação também troca o
guard das 3 leituras existentes, e os testes de comportamento delas reprovam.
Nos dois últimos, a leitura nova não tem teste de comportamento, e nada
reprova. O parâmetro com valor padrão (último caso) não estava na lista do
rail; é da mesma forma.

**Classe.** É a 2.ª vez que o censo verifica uma propriedade do texto no
lugar da propriedade que importa (1.ª: presença de `parse_constant`; 2.ª:
nome do guard). Pela regra «cure a classe» (S352), a cura é estrutural: o
censo passa a seguir a chamada, isto é, o objeto que cada leitura recebe
como `parse_constant`.

**Fora de escopo** (declarado pelas lanes do rail e no sentinel da W7a):
leitura por `__import__`, `importlib` ou `sys.modules`, e `raw_decode` sobre
um `JSONDecoder` guardado.

## Goal

O teste do censo reprova quando uma leitura JSON do
`check_harness_config.py` recebe como `parse_constant` qualquer objeto que
não seja a função `_refuse_constant` do módulo, inclusive quando o nome
`_refuse_constant` está religado no módulo ou sombreado no escopo da
chamada.

## Approach

Duas formas de seguir a chamada; a escolha é a OQ-1.

- **(a) Espião em tempo de execução.** O teste troca, só no módulo do hook,
  `json.loads` e `json.JSONDecoder` por envoltórios que registram o objeto
  recebido como `parse_constant` e repassam a chamada. Depois de exercitar as
  três leituras (settings, fixtures, decisões do replay), o teste confere
  que cada registro é `chc._refuse_constant` pela identidade (`is`), que essa
  função levanta `ValueError` para `"NaN"`, e que o número de leituras
  observadas é igual ao de leituras contadas pelo AST. Cobre religação e
  sombra porque olha o objeto, não o texto. Limite: só vê as leituras que os
  testes alcançam; o casamento com a contagem do AST fecha esse buraco.
- **(b) Resolução de escopo no AST.** Para cada chamada guardada, o censo
  resolve o nome passado em `parse_constant` pelo escopo da chamada: nenhuma
  ligação local (atribuição, parâmetro, `for`, `with`, `except ... as`,
  import, `global`/`nonlocal`, `:=`, compreensão, `del`) em nenhuma função
  que envolva a chamada, e exatamente uma ligação no módulo, que é um
  `FunctionDef` cujo corpo levanta exceção sempre. Cobre todo sítio sem
  executar nada, mas reimplementa regras de escopo do Python (risco da
  classe «forma não modelada ⇒ verde falso», paga no censo do PLAN-185).

Proposta do CEO: (a) como verificação principal e o AST atual como contagem
cruzada; a ligação única do nome (cura de 1 linha sugerida pelo `rx-w7a`)
entra como asserção adicional barata, sem ser a cura da classe.

**Canônico:** o teste (`.claude/hooks/tests/test_check_harness_config.py`)
responde `0` no oráculo `--is-canonical` (medido em 2026-10-12 na sombra
w7a) ⇒ land livre, com Codex + 1 refutador Claude. O hook
(`.claude/hooks/check_harness_config.py`) responde `1`; esta cura não o
edita. Se a forma escolhida exigir mudar o hook, o item vira pacote canônico
próprio, com SIGN do Owner.

## Items

- [ ] FU-1: reescrever a verificação do guard no teste do censo pela forma
  escolhida na OQ-1, com mutantes que reprovam: `_refuse_constant = float` no
  nível do módulo; sombra por atribuição local; sombra por parâmetro com
  valor padrão; e os mutantes que o censo atual já pega (presença, `None`,
  `float`, `lambda n: float(n)` direto na chamada, alias, `getattr`,
  `import json.decoder`). Controle positivo: o hook do `main` fica
  verde.
  Check: `python3 -m pytest .claude/hooks/tests/test_check_harness_config.py -q -k "census or json_read"` verde, e o mesmo comando vermelho com o teste novo sobre o `_json_census` de `94483a01`.
- [ ] FU-2: registrar no PLAN-183 (seção da W7a) que este follow-up fechou
  o resíduo, com o SHA do land.
  Check: none (doc-only)

## Open questions

- **OQ-1:** forma (a), (b) ou as duas? A proposta do CEO está em «Approach».

## How to continue

1. Confirmar que a W7a está no `main` (`git log --oneline -- .claude/hooks/_lib/harness_replay/`).
2. Reproduzir a tabela do «Context» sobre o `main` com o `_json_census`
   landado.
3. Decidir a OQ-1 com o Owner, implementar o FU-1 numa sombra própria, rail
   livre (Codex + 1 refutador Claude), land livre.

## Success criteria

- [ ] Os três mutantes da tabela do «Context» reprovam o teste do censo.
- [ ] Os mutantes que o censo de `94483a01` já pegava seguem reprovando.
- [ ] O hook do `main` passa o teste novo sem mudança no hook.
