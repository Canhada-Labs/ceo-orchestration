# Sonda 210s — evidência do gate BLOQUEANTE do ADR-110-AMEND-2 §6 (GO)

**Data:** 2026-08-04T14:45:29Z · **Executor:** Owner (terminal, rail humano)
**Instrumento:** `ceremony-2-staged/probe-hook-timeout-210s.sh` na variante
**v3** (scratchpad S293) — mudanças declaradas abaixo. **Veredito: HONRA → GO.**
O land do 180/210 foi autorizado por esta corrida (`4f05eb7` [SENT-S292-C]).

## Inputs (medição imprime seus inputs)

| Input | Valor |
|---|---|
| claude binary / versão | `/Users/joaocanhada/.local/bin/claude` · 2.1.221 |
| uname | Darwin 25.6.0 |
| modelo das chamadas | haiku |
| workspace | `/tmp/hkprobe.Xlkrro` (preservado; cópia dos markers em scratchpad S293) |
| tratamento | sleep 200s sob registro 210s |
| neutralização (v3) | config dir REAL (auth via Keychain) + `--setting-sources ""` (ZERO camadas user/project/local) + `--settings <cfg-da-sonda>` (só o hook dummy) |

### Desvio v3 vs instrumento staged (declarado)

O staged (v1) neutralizava via `CLAUDE_CONFIG_DIR` + HOME neutro — nesta
máquina isso desloga o harness ("Not logged in", 2 corridas mortas no
controle positivo A; o Keychain só é consultado sob o config dir real).
A v3 obtém a MESMA neutralidade de política pela rota de 1ª classe do CLI
(`--setting-sources ""`, que zera user+project+local — mais forte que o
v1, que zerava só a user) sem tocar em credencial. Caveat de camada do
README (§"a camada de registro não muda o tratamento do timeout") vale
igual: o hook passa a entrar pela camada CLI em vez da user.

## Markers crus (workspace preservado)

```
case_a.start 1785854733 · hb 5 beats (…733→…737) · end 1785854738 · tool_ran 1785854738
case_c.start 1785854745 · hb 10 beats (…745→…755) · end AUSENTE   · tool_ran 1785854756
case_b.start 1785854764 · hb 200 beats (…764→…967) · end 1785854968 · tool_ran 1785854968
```

## Interpretação (tabela do README)

- **A (controle positivo): OK** — hook completou (5s sob 210): instrumentação viva.
- **C (controle negativo): OK** — harness MATOU em ~10s (10 hb, `end` ausente):
  o mecanismo de kill existe, o campo `timeout` NÃO está inerte no substrato
  2.1.221, e o heartbeat observa o kill.
- **B (tratamento): HONRA** — bloqueio de ~204s sob registro de 210s, processo
  sobreviveu ao pós-bloqueio (`end` escrito no ponto onde `check_pair_rail.py`
  emitiria `pair_rail_case`).

**§6 bullet 1: SATISFEITO.** §6 bullet 2 (true-orphan count = 0) não é coberto
por esta sonda — re-verificar PÓS-LAND com
`.claude/scripts/local/pair-rail-latency.py` (baseline era 0 na registração 150).
