---
id: PLAN-175-FOLLOWUP-fase2-remedicao
parent: PLAN-175
title: "Fase 2 do PLAN-175: re-medir o unknown-ratio depois do injetor e decidir, pela regra estrita, se a recusa de spawn sem skill liga"
status: draft
created: 2026-10-12
owner: CEO
depends_on: [PLAN-175]
gatilho: "W1b do PLAN-175 landada (AC-1.5 e AC-1.6 marcadas) E pelo menos 30 eventos agent_spawn na família de auditoria do projeto com instante posterior ao commit de land da W1b"
level: L2
budget_tokens: "20-60k (estimado em 2026-10-12, S363, sem medição): uma leitura do leitor nomeado, um arquivo gerado e um registro de decisão. Se a decisão for ligar a Fase 2, o hook é pacote próprio, fora deste orçamento"
budget_sessions: 1
context_risk: low
external_wait: "o gatilho: land da W1b do PLAN-175 e 30 agent_spawn observados depois dele"
eta_calendar: "sem data: depende do gatilho e, pelo PLAN-SCHEMA §1.4, de o PLAN-175 chegar a done"
tags: [skills, telemetry, followup, fase2]
---

# PLAN-175-FOLLOWUP-fase2-remedicao — re-medição e decisão da Fase 2

> **Linhagem (PLAN-SCHEMA §1.4).** A AC-1.7 do PLAN-175 manda a Fase 1 FECHAR no baseline,
> porque o `external_wait: none` do pai foi ratificado pelo Owner em 2026-09-06. A re-medição
> posterior e a decisão de ligar ou não a Fase 2 saem do pai e vivem aqui, com o gatilho escrito
> no frontmatter. Este arquivo nasce `draft`; o flip para `reviewed` é do Owner.

## Context

- **Fase 1** = sugestão consultiva de skill no spawn (o injetor da W1b do pai, AC-1.5 e AC-1.6).
  **Fase 2** = recusar spawn que não declara skill nenhuma. A regra de ativação é do pai (§1,
  passo 1): liga se a re-medição deixar o unknown-ratio ACIMA de 0,10, comparação estrita; 0,10
  exato não liga. O instrumento de referência é `ceo-boot.py:814` (`ratio > 0.10`).
- **Baseline gerado** (AC-1.1 do pai): `.claude/plans/PLAN-175/evidence/unknown-ratio-baseline-2026-10-12.json`,
  lido em 2026-10-12T16:09:20Z pelo leitor nomeado: 32 spawns sem skill em 288, ratio 0,111
  (o leitor arredonda para três casas, `skill-health.py:517`), cadeia do log primário íntegra.
- **A queda já aconteceu SEM injetor.** Em 2026-09-07 o pai mediu 28 em 114, ratio 0,246 (§4.1
  do pai). Nenhum injetor existe hoje (`evidence/query-language-fraction.json`). Logo, uma queda
  medida depois da W1b não prova sozinha efeito do injetor. A regra continua pela META absoluta,
  não pela queda relativa, e é por isso que este follow-up não compara antes com depois para
  decidir: compara a re-medição com 0,10.
- **N mínimo.** O pai pede N ≥ 30 spawns na re-medição (§4.1 do pai, «N ≥ 30 na re-medição»).
  O gatilho usa esse número. Se o Owner fixar outro, o gatilho muda junto.

## Goal

Publicar a re-medição do unknown-ratio sobre os spawns posteriores à W1b e aplicar a regra
estrita do pai, registrando a decisão (liga ou atingido) com os números que a produziram.

## Approach

- **Leitor e janela.** O mesmo leitor do baseline, com a janela começando no instante do commit
  de land da W1b: `python3 .claude/scripts/skill-health.py --include-rotated --since <ISO-8601 do land> --json`
  (o leitor aceita ISO-8601 em `--since`, `skill-health.py:257-279`). O arquivo gerado leva o
  SHA do land em `since_commit`.
- **Decisão sem arredondamento.** A decisão usa as contagens, não o ratio arredondado:
  liga se `10 × unknown_invocation_count > total_invocations`. Assim um ratio de 0,1004 não vira
  «0,1» e deixa de ligar por arredondamento.
- **Cadeia.** A re-medição imprime `chain_status` e o escopo dele: o leitor verifica só o log
  primário (`skill-health.py:538`). A posição sobre cadeia não íntegra segue a OQ-3 do pai; este
  follow-up não a decide.
- **Se a decisão for «liga».** Recusar spawn sem skill é um hook sob `.claude/hooks/` (oráculo 1,
  §6 do pai), logo pacote canônico com assinatura do Owner, aberto à parte. Este follow-up só
  registra a decisão.

## Items

- [ ] **Item 1** — re-medição publicada como arquivo GERADO pelo leitor, com a invocação literal,
  a janela, `since_commit`, `chain_status`, o bloco `discovery_health` e a data de geração, e com
  pelo menos 30 spawns na janela.
  Check: `python3 -c "import glob,json,sys;p=sorted(glob.glob('.claude/plans/PLAN-175/evidence/unknown-ratio-remeasure-*.json'));d=json.load(open(p[-1])) if p else {};f=[k for k in ('reader_invocation','window','since_commit','chain_status','discovery_health','generated_at') if k not in d];n=(d.get('discovery_health') or {}).get('total_invocations') or 0;print(p[-1:],f,n);sys.exit(0 if p and not f and n>=30 and d.get('window')!='all' else 1)"` — vermelho hoje: nenhum arquivo de re-medição existe.
- [ ] **Item 2** — decisão aplicada pela regra estrita e registrada em
  `.claude/plans/PLAN-175/decisions/fase2-ativacao.md`, com uma linha `decisao: liga` ou
  `decisao: atingido` coerente com as contagens da re-medição.
  Check: `python3 -c "import glob,json,re,sys;p=sorted(glob.glob('.claude/plans/PLAN-175/evidence/unknown-ratio-remeasure-*.json'));h=json.load(open(p[-1]))['discovery_health'];t=open('.claude/plans/PLAN-175/decisions/fase2-ativacao.md').read();m=re.search(r'^decisao: (liga|atingido)$',t,re.M);liga=10*h['unknown_invocation_count']>h['total_invocations'];print(h['unknown_invocation_count'],h['total_invocations'],m and m.group(1));sys.exit(0 if m and (m.group(1)=='liga')==liga else 1)"` — vermelho hoje: os dois arquivos não existem.

## Open questions

- **Para o Owner (não respondida aqui).** Pelo PLAN-SCHEMA §1.4, este follow-up não entra em
  `executing` antes de o PLAN-175 estar `done`, e o pai só fecha depois da W2 e da W3. O gatilho
  pode ficar satisfeito muito antes disso. O Owner quer que a re-medição espere o pai fechar, ou
  prefere trazê-la de volta como perna da W1 do pai?

## How to continue

«Leia o PLAN-175-FOLLOWUP-fase2-remedicao. Confira o gatilho: a W1b do PLAN-175 landou e há
pelo menos 30 `agent_spawn` depois do commit de land? Se sim, e se o pai já estiver `done`, gere
a re-medição pelo leitor nomeado (Item 1) e aplique a regra estrita (Item 2).»

## Success criteria

- Os dois Checks dos Items saem 0.
- A decisão registrada é a que as contagens mandam, sem arredondamento.
- Se a decisão for «liga», existe um pacote canônico nomeado para o hook, com assinatura pendente
  do Owner.
