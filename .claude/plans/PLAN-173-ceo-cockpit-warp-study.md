---
id: PLAN-173
title: CEO cockpit — estudo Warp (MCP primeiro, fork AGPL adiado), memória única e multi-model como geradores de input não-confiável
status: reviewed
reviewed_at: 2026-08-11
reviewed_by: "Owner - ratificacao S302f via OWNER-RATIFY-S302.sh: ratifico os 6 planos na v2.6 (rail Codex 7 rounds, r7 APPROVE, commits ab45f56..0c90174)"
created: 2026-08-11
owner: CEO
depends_on: [PLAN-171, PLAN-172]
budget_tokens: 250-400k (estudo completo; spike W1 ≤200k dentro disso; firmado S302e). Build FORA deste plano (L3+ com ADR e budget próprios)
budget_sessions: 3-4 (spike ≤2 por AC; W2-W4 1-2)
context_risk: medium
external_wait: "gated: resultados do PLAN-172 (E0b/E5/E6) + gate retrospectivo dos NO-GOs para best-of-N"
tags: [cockpit, warp, mcp, vision, seed]
---

# PLAN-173 — CEO cockpit: o terminal como superfície, não como produto

> **SEMENTE (S302, 2026-08-11).** Visão de longo prazo pedida pelo
> Owner; deliberadamente a ÚLTIMA do trio 171→172→173 e gated nos
> resultados do 172. Qualquer passo que mude a identidade do framework
> ("não é um produto, não tem UI" — CLAUDE.md §2) exige ADR + debate
> L3+; este plano em si é ESTUDO, não build.

## 0. Fatos de base (verificados S302)

- **Warp abriu o código do cliente em 2026-04-30**: repo
  `warpdotdev/warp`, licença dupla — MIT para o framework de UI
  (`warpui_core`/`warpui`), **AGPL v3 para o resto**. A nuvem de IA
  deles (agentes, Warp Drive) permanece proprietária e não
  self-hostável.
- Para um projeto free/open como este, AGPL é compatível. Condições:
  (a) derivado permanece AGPL com fonte disponível; (b) ZERO uso da
  marca "Warp"; (c) código AGPL em **repo separado** — nunca dentro do
  `ceo-orchestration` (contaminaria a licença do framework).

## 1. Escopo do estudo

### W1 — Integração MCP com o Warp (o degrau barato; o Owner já usa Warp)
Expor um **MCP server de governança read-only** consumível pelo Warp:
estado dos plans, fila de aprovação, últimos verditos, saúde do audit
log (via `check-audit-hmac-null.py`), fleet view. Read-only por
construção — o MCP server NUNCA é caminho de mutação (mutação
continua exclusiva do rail governado). Runtime: avaliar se stdlib-only
aguenta (servidor MCP stdio simples) ou se vira componente opcional
fora do core. **Time-box (Codex r1): spike ≤2 sessões; AC = servidor
read-only respondendo 3 queries (plans, verditos, saúde HMAC) em demo
local; kill = stdlib-only inviável em 2 sessões ⇒ componente opcional
fora do core OU morre.** Entregável: spike + ADR de viabilidade.

### W2 — Fork AGPL: documentar como viável-mas-ADIADO
Registrar a análise legal (AGPL/MIT dual, marca, repo separado) e o
custo real: manter um terminal Rust GUI contra bus factor 1. Decisão
default: NÃO forkar enquanto a integração MCP (W1) não esgotar o
valor. Revisitar apenas com evidência de demanda que o MCP não cobre.

### W3 — Memória única / living docs como espinha do cockpit
O cockpit lê a materialização do PLAN-171 W4 (living docs local-only)
+ memória por-projeto existente. Nenhum armazenamento novo; nenhuma
nuvem; o cockpit é VIEW, a verdade continua no repo + audit log.

### W4 — Multi-model como GERADORES de variantes (não autores)
Herda o verdito do PLAN-172 §2: multi-model authors como rota de
throughput está morto (3 formalismos). O que PODE sobreviver, gated:
Codex/Grok gerando variantes de CURA para defeitos com **oráculo
executável** (best-of-N com verificador real), entrando SEMPRE como
input não-confiável pelo rail governado (Claude aplica sob hooks;
review cruzado preservado — autor≠revisor mantido por construção).
**Pré-gate obrigatório (do verdito §2):** classificação retrospectiva
dos achados dos NO-GOs históricos; se <30% seriam detectáveis por
gates locais sobre N variantes, W4 morre sem experimento.

## 2. Não-escopo

- Vender, hospedar ou cobrar qualquer coisa (o framework segue free).
- Fork do Warp neste plano (só documentação da rota).
- Qualquer caminho de escrita fora dos hooks (inclusive via MCP).
- "Cérebro local" (modelo open-source local como orquestrador):
  abaixo da barra de qualidade p/ governança hoje e runtime pesado
  contra o ethos stdlib-only — reavaliar apenas em plano futuro com
  evidência nova.

## 3. Riscos nomeados

- Identity drift: cockpit é evolução de SUPERFÍCIE; o valor declarado
  (governança + auditabilidade) não muda. Guard: ADR de visão antes
  de qualquer build.
- MCP server vira canal de exfiltração se crescer além de read-only —
  escopo congelado por schema; qualquer método novo passa por debate.
- Dependência visual do Warp (produto de terceiro que muda rápido) —
  a integração deve degradar para CLI pura sem perda de função.

## 4. Revisão v2 — auditoria total S302

- **Critério de kill adicionado:** se o E0b (PLAN-172) mostrar que o
  tempo-morto dominante é quota/capacidade (não fricção de
  superfície), este plano é DESCARTADO sem build.
- **Reordenado:** ganha valor DEPOIS do E5 (sessões que já conversam
  via cross-session SendMessage são o substrato natural do cockpit).
- **Vendors novos (da lane meta-gemini + consenso 4 lanes):**
  - **Gemini** entra SOMENTE quando o E3 (single-pass k revisores
    cegos paralelos) existir — nunca no rail serial bloqueante. Único
    candidato com diversidade frontier real + CLI maduro + custo
    baixo; sob containment do /council (read-only, redactor ADR-114).
  - **Agente de código da Meta: watchlist, depois do previsto.** 3
    gates de entrada QUANTIFICADOS (Codex r1): sair de beta;
    benchmark verificado independente dentro de 2 pontos do
    publicado; alucinação <5% num piloto advisory de 30 achados
    (review que alucina achados é a pior propriedade possível — cada
    achado falso custa rounds). Se pilotar: só tier que NÃO treina em
    prompts (postura de egress ADR-114). Gemini: fica no E3 apenas
    com unique-finding-rate ≥15% por lane instrumentada.
  - Revisores BLOQUEANTES congelados em 2 (Claude autor + Codex):
    formalização no PLAN-171 W1b.

## 5. Pronto-para-execução (S302e)

**ACs por wave:** W1 = os do §1 (3 queries em demo local, ≤2
sessões, kill explícito). W2 = documento de decisão fork-adiado com
análise legal (AGPL/MIT/marca/repo-separado) versionado — AC: um
leitor externo consegue reproduzir a decisão sem esta conversa. W3 =
demo do cockpit lendo living-docs do PLAN-171 W4 (se W4 já landou;
senão, lê memória por-projeto) — AC: zero armazenamento novo. W4 =
verdito do pré-gate retrospectivo dos NO-GOs (corte <30% detectável
por gates locais ⇒ W4 morre) ANTES de qualquer piloto.

**Runbook sessão 1:** rodar o gate retrospectivo do W4 (barato,
read-only, pode matar a wave inteira) + spike W1 (MCP stdio mínimo).

### ✅ Pré-gate da W4 — EXECUTADO (S325). Veredito: **W4 VIVE**, com uma ressalva que muda o piloto.

Medição read-only, 4 lanes (vereditos de rail, achados de debate, inventário
dos gates locais existentes) + síntese. **N=76 achados classificados** de um
universo de 212–293 candidatos (**cobertura ~26–36%**, não o corpus inteiro).

Classificação: **LOCAL-DETECTABLE 56 / MODEL-ONLY 14 / AMBIGUOUS 6.**

| leitura | fração | veredito (corte 30%) |
|---|---:|---|
| AMBIGUOUS → model-only | **73,7%** | VIVE |
| AMBIGUOUS excluídos | 80,0% | VIVE |
| AMBIGUOUS → local | 81,6% | VIVE |
| **piso HOSTIL** (toda deflação de todas as lanes aplicada de uma vez) | **51,4%** | VIVE |

A faixa **não** encosta em 30% — clareia por 20+ pontos até no piso hostil.
O critério está satisfeito de forma NÃO-marginal.

**⚠️ A ressalva, e ela é operacional, não estatística.** Existe UMA
sub-população no corpus que REPROVA o critério: o cluster de
resume/remote-state (`PLAN-174` r1 F6) mede **~23%** de lintabilidade sobre 5
NO-GOs consecutivos, e ~34% sobre 6 classes nomeadas. ⇒ **Se o piloto da W4
mirar esse cluster, ele falha o próprio pré-gate.** O veredito VIVE é sobre o
corpus TODO; escolher o alvo do piloto dentro daquele cluster inverteria o
resultado. Isso é decisão de escopo do piloto, e fica aqui declarada.

**Limites, declarados porque mudam o que o número licencia:**

1. **Hindsight conditioning — a maior inflação.** Em 11 de 16 LOCAL-DETECTABLE
   de uma das lanes, o "gate local que teria pegado" é um check que o PRÓPRIO
   debate inventou. Um pré-gate honesto exige que o check já EXISTA. Por isso
   o número a planejar contra é o piso (51,4%), não o teto.
2. **Amostragem.** 76 de 212–293. A cauda não foi classificada; os 76 são os
   recentes e bem documentados — enviesados para o período em que o repo já
   tinha gates.
3. **Viés de seleção em DUAS direções.** NO-GOs são registrados; passes
   silenciosos não deixam artefato, logo o denominador verdadeiro é
   inobservável.
4. **Sobreposição entre lanes** não deduplicada: alguns defeitos do
   `PLAN-183` W5-b round-1 aparecem em duas lanes com ids diferentes.
5. **Natureza da evidência:** ADVISORY. Foi produzida por agentes read-only,
   não por um instrumento determinístico — vale como base de decisão do Owner,
   não como gate mecânico. As três provas mais fortes de cada lado estão no
   relatório da sessão.

**Três LOCAL-DETECTABLE mais fortes** (existiam gates, não foram rodados):
`179` r1#5 (teste novo com 11 violações de env-write — `check-test-env-hygiene.py`
já existia e estava verde, só não foi re-rodado após a última edição);
`179` r1#1 (`upgrade.sh` nunca adiciona o hook que `install.sh` adiciona —
oráculo de paridade install/upgrade, a MESMA classe do D1 vivo); `183` W5-b
B-1 (rodar install DUAS vezes derruba os registros, e nenhum Check roda
install duas vezes).

**Três MODEL-ONLY mais fortes** (justificam manter o segundo modelo):
`184` r2 (a A0 — matriz 4→2 — nunca foi enumerada: gerar uma alternativa mais
barata não proposta não é lint); `183` W5-b ("a rota (ii) é a rota (iii)
disfarçada" — o censo dá a evidência, mas o veredito de que população de
fixture ≠ população de campo é trabalho de modelo, e derrubou uma decisão do
Owner); `166` r1 C2 (AC auto-anulável: RC e GA compartilham um SHA, então o
poll por `head_sha` encontra o run do RC).


**Gates de entrada (herdados, verificar antes de abrir):** E0b
respondido (kill criterion do §4: quota-dominante ⇒ descarta sem
build) + E5 substrato existente (cross-session).

**Debate:** Codex r1→r3 GO desde o r2; `/debate start PLAN-173` no
início da execução (Gate 3).
