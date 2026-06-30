# PLAN-128 §7 — Protocolo A/B (1 página): medir o ganho honesto dos aceleradores

> O objetivo é UM número honesto de throughput/custo — não uma alegação. Uma semana sozinha dá só **taxas
> brutas**; o **multiplicador** só existe comparando duas janelas (OFF vs ON). Isto é a pré-registração do §7.

## Regra de ouro (a que invalida tudo se ignorada)
**Meça num PROJETO DE APP REAL — não neste framework.** Os aceleradores de qualidade (`verify-after-edit`,
`codex review`, `adequacy`) disparam em código de aplicação (auth, dados, dinheiro). Editar o framework
(planos/hooks/docs) é meta-trabalho e **não os exercita** — é por isso que o `measure-state.sh` aqui dá
catch-rate `0/0/0`. Rode o A/B onde você escreve features de verdade.

## Setup (uma vez, no diretório do app)
O app precisa ter o framework instalado (hooks ativos). Confirme que `measure-state.sh` enxerga o audit log
do app — se necessário, aponte:
```
export CLAUDE_AUDIT_LOG=~/.claude/projects/<slug-do-app>/audit-log.jsonl
```
Declare também o teto de quota semanal (em shadow-$) UMA vez — exportado, ele vale para AS DUAS janelas, e é
o que faz o relatório imprimir `% of weekly quota`. A fonte autoritativa do consumo continua sendo `/usage`;
este teto é o denominador shadow-$ contra o qual o `quota_pct` é calculado:
```
export CEO_WEEKLY_QUOTA_USD=<teto semanal de shadow-$ do seu plano>   # ex.: 100
```

## As duas janelas

### Semana A — BASELINE (aceleradores DESLIGADOS)
No início da semana, no diretório do app:
```
touch .claude/turbo-off
export CEO_VERIFY_AFTER_EDIT=0 CEO_CODEX_USER_REVIEW=0   # CEO_ADEQUACY_GATE já é opt-in (off)
export CEO_WEEKLY_QUOTA_USD=${CEO_WEEKLY_QUOTA_USD:-100}   # teto shadow-$ p/ o quota_pct (mesmo valor na Semana B)
rm -f .git/.ceo_codex_review_state.json .ceo_codex_review_state.json   # dedup limpo
date -u +%Y-%m-%dT%H:%M:%SZ      # ANOTE este timestamp = baseline-since
```
Trabalhe a semana normalmente. No fim:
```
date -u +%Y-%m-%dT%H:%M:%SZ      # ANOTE = baseline-until
```

### Semana B — TREATMENT (aceleradores LIGADOS)
```
rm -f .claude/turbo-off
unset CEO_VERIFY_AFTER_EDIT CEO_CODEX_USER_REVIEW    # verify volta a ON (default)
export CEO_WEEKLY_QUOTA_USD=${CEO_WEEKLY_QUOTA_USD:-100}   # MESMO teto da Semana A (denominador comparável p/ quota%)
rm -f .git/.ceo_codex_review_state.json .ceo_codex_review_state.json   # dedup limpo p/ a janela B
# OPCIONAL — exercitar os eixos opt-in/detect-only (têm CUSTO real):
#   export CEO_ADEQUACY_GATE=1            # roda a suíte de testes por mutante a cada change
#   export CEO_CODEX_USER_REVIEW_AUTO=1   # CHAMA o codex (custo ChatGPT) em vez de só avisar
date -u +%Y-%m-%dT%H:%M:%SZ      # ANOTE = treatment-since
```
Trabalhe a semana. No fim, anote `treatment-until`.

> **Atenção aos defaults (senão o catch-rate sai enviesado):** com os defaults da Semana B só o
> `verify-after-edit` dispara de fato. `adequacy_gate` é **opt-in** (silencioso sem `CEO_ADEQUACY_GATE=1`)
> e `codex_review` é **detect-only** (só recomenda; só CHAMA o codex com `CEO_CODEX_USER_REVIEW_AUTO=1`).
> Se você quer medir esses dois eixos, ligue os opt-ins na Semana B — e saiba que têm custo (suíte de
> testes / chamadas ao codex). Se NÃO ligar, reporte catch-rate só para `verify` e diga isso no veredito.

> Dica: a cada dia você pode rodar `bash .claude/plans/PLAN-128/measure-state.sh 1` pra ver o retrato do dia
> e confirmar que, na semana B, o catch-rate (QUALITY) começou a sair de zero.

## Computar o multiplicador
Com os 4 timestamps (passe o teto de quota — via env já exportado ou explícito com `--weekly-quota-usd`):
```
python3 .claude/plans/PLAN-128/wave1/measure_multiplier.py --ab \
  --baseline-since  <baseline-since>  --baseline-until  <baseline-until> \
  --treatment-since <treatment-since> --treatment-until <treatment-until> \
  --weekly-quota-usd "$CEO_WEEKLY_QUOTA_USD" \
  --report
```
Saída: `quota_efficiency_multiplier` (commits por 1k tokens, ON/OFF) e `autonomy_multiplier` (commits por
toque humano). `>1` = os aceleradores ajudaram naquele eixo. Além do multiplicador, o relatório imprime — por
janela (baseline e treatment) — os **tokens reais** (transcrição: main-loop + subagentes), o **shadow-$** e a
seção **Weekly quota (subscription)** com **`% of weekly quota`** (shadow-$ projetado p/ a semana ÷
`CEO_WEEKLY_QUOTA_USD`). Compare as DUAS janelas por quota%, tokens e shadow-$/commit — NÃO só pelo
multiplicador: a métrica honesta é **quota**, e o multiplicador é derivado dela.

## Os 3 cuidados honestos (sem eles o número é lixo)
1. **Task-mix.** As duas semanas precisam de trabalho **comparável** (mesmo dev, mesmo codebase, proporção
   parecida de feature/refactor/bug). Um mix diferente sozinho move o multiplicador ~2×. **Anote o mix de
   cada janela** e reporte junto do número — senão é ininterpretável.
2. **Aprendizado/ordem.** Duas semanas seguidas no mesmo codebase: na 2ª você já conhece melhor o código →
   isso infla a janela ON injustamente. Se der, **alterne** (A-B-A-B por dias) ou pelo menos **reconheça** o
   viés no relatório. Nunca rode ON primeiro e atribua todo o ganho aos aceleradores.
3. **Honestidade do teto.** O alvo pré-registrado é **~1.4–1.9×** de throughput / **~1.6–2.2×** de
   quota-eficiência. Se sair muito acima disso numa semana, **desconfie do confound** (provavelmente task-mix),
   não comemore. O S201 já provou que ganhos de "velocidade pura" via orquestração são miragem.

## O que cada eixo te diz (do `measure-state.sh`)
| Eixo | Métrica | Ganho = |
|---|---|---|
| **Velocidade/Autonomia** | commits, human-touches/commit | menos toques por commit |
| **Qualidade** | verify/codex/adequacy catches | bugs pegos antes de você ver (na semana B > zero) |
| **Custo** | $/commit, tokens/commit | mesmo output por menos token |
| **Segurança** | audit events, routing | governança operando (não é pra "melhorar", é pra não regredir) |

## Veredito (reframe S217 — Wave-A FinOps)
A pergunta NÃO é "bati 1.4×?". Os aceleradores são **guard-rails de qualidade** (pegam bug), não ferramenta
de velocidade — velocidade-via-orquestração morreu no S201. Então julgue por **dois eixos** primeiro; o
multiplicador de throughput é derivado deles, não a verdade-base:

1. **Catch-rate subiu?** (`verify`/`adequacy`/`codex` events na janela B > 0, e ~0 na A). Reporte **ao lado a
   taxa de falso-positivo por `checker`** — um catch que era flake não conta como valor. Sem esse contexto o
   número é artefato da disciplina-de-teste do codebase, não do acelerador.
2. **Custo/commit caiu** sem perder throughput?

Se SIM nos dois, os aceleradores pagam → ligue por padrão. Se não, **corte** o que não pagou (cada peça tem seu
`CEO_*=0`). Um gap específico (ex: "verify não pegou bug classe X") gera o próximo plano — dirigido por dado.

Reporte tudo **com o task-mix de cada janela ao lado** (§3.1).

> **Honestidade do token:** o `tokens_total` do **audit log** captura **só tokens de spawn de subagent** — o
> gasto do main-loop NÃO chega a hooks; é por isso que `quota_efficiency_multiplier` (que usa o audit) é
> **parcial-por-construção**. O relatório, porém, já traz a contagem **honesta** via transcrição (main-loop +
> subagentes): a seção *Tokens & shadow cost* e a *Weekly quota* com `% of weekly quota`. Use esse quota% (e o
> shadow-$/commit) como a métrica primária da comparação OFF×ON; valide o teto rodando `/usage` no fim de cada
> janela e reporte ao lado (o `/usage` continua sendo a fonte autoritativa do consumo real).
>
> **Caveat adequacy:** se a suíte de testes do app já estiver quebrada, o `adequacy_gate` retorna silêncio
> (não flaga) — um ratio 0/0 em adequacy NÃO significa "código adequado". Inspecione os testes de fato.
