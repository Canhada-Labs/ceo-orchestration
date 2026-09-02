# Sonda de concorrência — PLAN-186 W0-US2 (S339, 2026-09-02)

**Método:** Workflow `concurrency-probe-s339` (run `wf_ff29ec9c-69a`), 4 rodadas com barreira (N = 4, 8, 12, 16), agentes `general-purpose` em `model: sonnet` (servido `claude-sonnet-5`), `effort: low`, tarefa fixa de 3 comandos Bash (`date`, `wc -l < SBOM.md`, `date`), schema estruturado. `t0`/`t1` = epoch medido DENTRO do agente; skew = spread dos `t0` na rodada (fila de despacho); span = último `t1` − primeiro `t0`. Máquina: 16 threads ⇒ cap do substrato = min(16, CPUs−2) = **14** concorrentes por workflow (skill `workflow-authoring`). Uma repetição por N (n=1 por célula — indicativo, não p95 de verdade).

| N | devolvidos | erros/rate-limit | skew despacho (s) | span rodada (s) | dur p50 (s) | dur p95 (s) | dur max (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4 | 4 | 0 | 3.6 | 8.5 | 5.1 | 5.7 | 5.8 |
| 8 | 8 | 0 | 4.1 | 11.6 | 7.6 | 8.5 | 8.7 |
| 12 | 12 | 0 | 5.5 | 13.4 | 8.6 | 10.3 | 11.1 |
| 16 | 16 | 0 | 23.3 | 28.0 | 11.3 | 13.8 | 14.3 |

**N=16:** os 14 primeiros `t0` cabem em 6.3 s; o 15º começa 16.5 s depois do 14º — a fila do cap de 14 é visível: 2 agentes esperaram um slot e rodaram em ~4,7 s cada (a tarefa mais curta da sonda, sem contenção). Agrupamento por ORDEM no journal (rodadas com barreira, sem sobreposição); o journal não registra label.


## Leitura

1. **Nenhum 429 / rate limit / overload em 40 agentes**, até 14 concorrentes reais. O limite observado NÃO é da API: é o cap local do Workflow (14 nesta máquina) — acima dele o excedente enfileira, não falha.
2. **Contenção suave:** a duração da mesma tarefa sobe com N (p50 ≈ 5 s em N=4 → ≈ 11 s em N=16). Provável mistura de latência de API sob carga e CPU local (16 threads compartilhadas com o assento). Não é rate limit; é fila.
3. **Custo de contexto por agente:** o workflow reportou 3,79 M «subagent_tokens» para 40 agentes triviais ≈ **95 k tokens de contexto por spawn** (prefixo do harness + CLAUDE.md + skills), quase todo cache-read. Confirma o relatório 05 §P1-2: esse contador é pico de contexto, não fatura. Em Sonnet 5 (cache-read $0,20/MTok) a sonda inteira custou da ordem de US$ 1.
4. **Resposta à pergunta do Owner («máximo de workflows em paralelo sem rate limit»):** para assinatura não há teto publicado; a sonda não encontrou teto de API até 14 concorrentes. O teto prático é (a) o cap local de 14 por workflow e (b) a janela de 5 h, que cada agente consome — 95 k de contexto por spawn é o custo fixo que faz «mais agentes» virar «menos minutos de janela».

## Limitações

- n=1 por N; sem repetições, os percentis são indicativos. Repetir 3× antes de citar p95 como fato (AC-2 do plano exige 3/3).
- Tarefa trivial (3 comandos): não mede contenção de OUTPUT tokens, só de despacho e latência de turno.
- Não testado: dois workflows simultâneos em terminais distintos (o cap é por workflow; a janela é por conta).

