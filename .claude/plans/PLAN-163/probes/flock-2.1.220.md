# PROBE flock-2.1.220 — re-medição do cap de concorrência N<=6 (PLAN-163 T4.1, CF-10)

- **Data:** 2026-07-28
- **Substrato:** Claude Code 2.1.220 (host-side; a medição é de contenção de lock em nível de OS/processo, independente do harness)
- **Máquina:** darwin-arm64 local, 16 logical cores, Python 3.9.6, git 2.50.1 (Apple Git-155)
- **Carga (uptime, sem hostname):** load averages 8.50 / 7.52 / 7.03 no início da bateria, 7.95 / 7.44 / 7.00 no fim — **NÃO idle** (outras sessões ativas no host). Nota de direção: carga de fundo INFLA latências de contenção; resultados verdes sob carga são conservadores no sentido seguro.
- **Artefatos:** script `flock_bench.py` + `flock_bench_results.json` + variante `flock_bench_fsync.py`/`flock_bench_results_fsync.json` no scratchpad da sessão (temporários); números integrais transcritos abaixo.
- **NO-SPEED-CLAIM:** este relatório mede contenção/latência de lock e exatidão de tally. Nada aqui é claim de speedup do framework.

## 0. Proveniência da metodologia original (limitação material)

`PLAN-083*.md` **não existe em disco** — nem no repo público nem no archive
(`~/canhada-labs/ceo-orchestration-archive`; histórico git de ambos sem o
arquivo — pré-clean-room). A única fonte canônica das 3 justificativas e dos
números originais é `.claude/skills/core/parallelization-by-default/SKILL.md`
§"Ceiling enforcement — max 6 parallel sub-agents":

> p95 contention latency rises non-linearly (measured ~50ms at N=6, ~180ms
> at N=8, ~600ms at N=12) [audit-log filelock]; git index lock similarly
> degrades >6; token-budget-guard cannot accurately tally spend across >6
> in-flight sub-agents within the budget-check tick.

Os scripts/threshold/workload originais do PLAN-083 Perf P0-1 **não estão
disponíveis**; o workload shape abaixo foi reconstruído a partir dos
mecanismos VIVOS de hoje (o que a re-medição deve validar de qualquer
forma). Consequência honesta: os números de 2026-07-28 **não são
diretamente comparáveis** aos do PLAN-083 (hardware, substrato e shape
mudaram); eles constituem a nova baseline pré-registrada.

## 1. Protocolo pré-registrado (classe PLAN-159)

Fixado ANTES de rodar (design do probe):

- Níveis: N ∈ {6, 8, 12}; ≥200 amostras por (mecanismo × N). Realizado:
  A=402/400/408, B=216/216/216, C=220 passes de tally por nível (+ os
  mesmos 402/400/408 emits concorrentes).
- `multiprocessing` spawn, barrier de largada comum (contenção simultânea
  real), tudo em scratch — **zero I/O no repo ou no audit-log real**.
- **Mecanismo A — flock do audit-log:** usa o `FileLock` REAL de
  `.claude/hooks/_lib/filelock.py` (import por caminho, read-only; fcntl
  `LOCK_EX|LOCK_NB`, timeout=2.5s, poll=50ms — os mesmos literais de
  `audit_emit._write_event`). Seção crítica fiel à Phase-1 do
  `_write_event`: ler sidecar HMAC → HMAC-SHA256 sobre evento
  canonical-json (~500 B) → append 1 linha JSONL → reescrever sidecar.
  Sem fsync (o caminho real não faz fsync). Sem think-time entre emits
  (burst worst-case). Métrica: latência de ESPERA de aquisição por
  aquisição; secundárias: hold time, `FileLockTimeout` (== queda para o
  fallback path), linhas perdidas.
- **Mecanismo B — git index lock:** 1 repo scratch compartilhado; N
  workers, cada um `git -c gc.auto=0 add <arquivo-próprio>` (contenção
  APENAS no `.git/index.lock`, zero overlap de arquivo, fiel à regra
  anti-colisão). git falha fail-fast em index.lock ⇒ retry loop de 10ms,
  deadline 10s (deadline batido = evento de starvation). Métrica: tempo
  até add bem-sucedido (inclui retries); secundárias: retries, starvation.
- **Mecanismo C — budget-guard tally:** o tally do
  `token-budget-guard.py check` = ler `audit-log.jsonl` inteiro e somar
  `tokens_total`. Reproduzido: 1 leitor em loop (passes contínuos,
  sleep 5ms) ENQUANTO os N emitters do mecanismo A escrevem. Métricas:
  latência por pass; staleness por pass (entradas que chegaram DURANTE o
  pass); exatidão final EXATA (count + soma vs esperado); linhas torn.
- **Thresholds de aceitação (pré-registrados neste probe; os do PLAN-083
  não sobreviveram em disco):**
  - (a) p95 de espera do flock < 250ms (10% do budget de 2.5s do
    `FileLockTimeout`), zero timeouts, zero linhas perdidas/torn;
  - (b) p95 de add-até-sucesso < 1000ms, zero starvation em 10s;
  - (c) exatidão de tally EXATA (soma e contagem), torn=0, p95 de pass
    < 100ms.

## 2. Resultados — p50/p95 por (mecanismo × N)

### A. Flock do audit-log (espera de aquisição, ms) — 402/400/408 amostras

| N | p50 | p95 | max | hold p50 | hold p95 | FileLockTimeouts | linhas (obtidas/esperadas) |
|---|-----|-----|-----|----------|----------|------------------|-----------------------------|
| 6 | 0.03 | **0.06** | 217.26 | 0.119 | 0.184 | 0 | 402/402 |
| 8 | 0.03 | **0.07** | 381.64 | 0.124 | 0.185 | 0 | 400/400 |
| 12 | 0.03 | **32.70** | 373.80 | 0.126 | 0.241 | 0 | 408/408 |

Sensibilidade (variante com `fsync` na seção crítica, mesma bateria só p/
A): p95 = 0.06 / 0.06 / 0.13 ms em N=6/8/12 — fsync sem F_FULLFSYNC é
quase no-op em APFS; a shape fiel (sem fsync) permanece a primária.

### B. Git index lock (add-até-sucesso, ms) — 216 amostras/nível

| N | p50 | p95 | max | retries p50 | retries p95 | retries max | starvation (10s) |
|---|-----|-----|-----|-------------|-------------|-------------|-------------------|
| 6 | 12.26 | **136.01** | 307.19 | 0 | 5.0 | 13 | 0 |
| 8 | 12.51 | **151.93** | 329.96 | 0 | 5.25 | 13 | 0 |
| 12 | 16.29 | **146.93** | 254.95 | 0 | 5.0 | 9 | 0 |

### C. Budget-guard tally (pass de leitura+soma, ms) — 220 passes/nível

| N | p50 | p95 | staleness p95 (entradas) | staleness max | exatidão final | torn | timeouts de emit |
|---|-----|-----|--------------------------|----------------|----------------|------|-------------------|
| 6 | 1.32 | 1.44 | 0 | 9 | EXATA (soma+count) | 0 | 0 |
| 8 | 1.34 | 3.40 | 0 | 10 | EXATA | 0 | 0 |
| 12 | 3.16 | 5.53 | 0 | 8 | EXATA | 0 | 0 |

## 3. Leitura contra os 3 fundamentos do cap (PLAN-083)

1. **Flock do audit-log — NÃO reproduz o blow-up original.** A curva
   ~50/180/600ms de p95 não aparece: p95 fica em 0.06/0.07/32.7ms, todos
   ≥7× abaixo do threshold (250ms) e ~76× abaixo do budget de timeout
   (2.5s); zero `FileLockTimeout` ⇒ zero quedas para o fallback path;
   zero linhas perdidas. **Porém** N=12 exibe o PRIMEIRO joelho: p95
   salta 0.07→32.7ms (quantização do poll de 50ms do FileLock ficando
   visível) e o max cresce com N (217→382→374ms na bateria primária;
   433ms no pior caso da variante fsync). O regime de contenção
   que o cap original guardava começa a aparecer em N=12, ainda que longe
   de qualquer limite operacional.
2. **Git index lock — degrada suave, não catastrófico, mas é o único
   mecanismo com tail de retries.** p95 estável ~136-152ms de 6→12 (sem
   knee), zero starvation. O tail existe (até 13 retries fail-fast em um
   único add) e SÓ é exercitado por workloads que tocam o índice git —
   i.e., staging. Fan-outs read-only nunca tocam este lock.
3. **Budget-guard tally — o claim "não consegue tally exato >6 in-flight"
   NÃO reproduz.** Exatidão EXATA em todos os níveis, torn=0, staleness
   p95=0 entradas (máx 8-10 entradas em-voo durante um pass de ≤5.5ms —
   inerente a qualquer leitor de log append-only, igual em N=6 e N=12).

## 4. Recomendação: **split** — read-only fan-outs até 8; staging mantém 6

`cap-rec=split`, justificada pelos 3 fundamentos re-validados:

- **Por que subir para read-only:** os três fundamentos passam FOLGADOS em
  N=8 (flock p95 0.07ms; git nem se aplica a read-only; tally exato). A
  base empírica que sustentava "6" para fan-outs read-only não existe
  neste substrato/hardware.
- **Por que 8 e não 12:** N=12 mostra o primeiro joelho de contenção no
  flock (p95 0.07→32.7ms, quantização de poll) e a bateria rodou em
  máquina NÃO-idle (load ~7-8.5/16) — verde, mas com menos confiança no
  tail. Certificar 12 exigiria re-rodar em host idle; 8 está limpo em
  todas as células e em ambas as variantes (com/sem fsync).
- **Por que staging mantém 6:** o git index lock é o único mecanismo com
  tail de retries (max 13) e fail-fast exigindo retry-loop no chamador;
  a medição não mostrou colapso até 12, mas o shape real de staging
  (patches maiores, hooks git, `git status` concorrente) é mais pesado
  que o probe (adds de 1 arquivo pequeno). Sem medição do shape pesado,
  manter 6 para qualquer fan-out que toque o índice git é o default
  conservador — exatamente a alternativa pré-autorizada no PLAN-163 T4.1
  ("cap maior escopado a fan-outs READ-ONLY mantendo 6 para staging").
- **Rail de governança do edit da skill:** a mudança em
  `parallelization-by-default/SKILL.md` é edit canônico — segue o rail
  declarado no plano (SP-NNN + soak 7d, ou sentinel com escopo e
  justificativa citando ESTE probe). Este relatório é evidência, não
  autorização (PROTOCOL.md V0-V3 intactos). O texto novo da skill deve
  substituir os números do PLAN-083 pelos desta baseline e declarar o
  split (8 read-only / 6 staging), preservando a regra anti-colisão e o
  batching acima do cap.

## 5. Limitações registradas

- Máquina única, não-idle (load ~7-8.5/16 cores); direção do viés é
  conservadora (latências infladas), mas o tail de N=12 fica sem
  certificação limpa.
- Workload B usa adds de arquivo pequeno; staging real é mais pesado.
- Metodologia original do PLAN-083 indisponível (arquivo fora do disco em
  ambos os repos); comparação com os números históricos é qualitativa.
- O probe valida os 3 fundamentos de LOCK do cap. Interações com os caps
  nativos do substrato (async default 2.1.198, 20/200/depth-3) e com
  capacidade de revisão/verificação humana-CEO estão fora de escopo
  (cobertas por T4.2/T4.3).
