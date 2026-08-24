---
id: PLAN-175
title: Skills — descoberta antes de poda: unknown-ratio <0.10, core 42→~25, domain-packs opt-in, contagem derivada
status: reviewed
reviewed_at: 2026-08-11
reviewed_by: "Owner - ratificacao S302f via OWNER-RATIFY-S302.sh: ratifico os 6 planos na v2.6 (rail Codex 7 rounds, r7 APPROVE, commits ab45f56..0c90174)"
created: 2026-08-11
owner: CEO
depends_on: [PLAN-171]
budget_tokens: 150-300k (firmado S302e; passo 3 migração é o grosso)
budget_sessions: 2-4 (passo 1 = 1; passos 2-3 = 1-2; passo 5 = 1)
context_risk: low
external_wait: "gatilho: pós-GA v1.3.0; W1c do PLAN-171 (fronteira de ownership) primeiro"
tags: [skills, telemetry, pruning, seed]
---

# PLAN-175 — Skills: fechar a distância entre claim e realidade

> **SEMENTE (S302, 2026-08-11).** Da auditoria total: telemetria do
> skill-health sobre TODO o histórico mostra **157/164 skills com
> zero invocações (96%)** e **43,4% dos spawns nem resolvem para o
> catálogo** (labels ad-hoc). "166 skills ready-made" é a maior
> distância entre claim e realidade do repo. Não é gargalo de
> velocidade (reference-mode já evita custo por sessão) — é
> honestidade de catálogo e qualidade de roteamento.

## 1. Ordem de ataque (a ordem IMPORTA)

1. **Descoberta ANTES de poda — em duas fases (Codex r1: decisão
   tomada, não deixada em aberto):** Fase 1 = SUGESTÃO advisory
   (auto-suggest top-3 via skill-retrieve tf-idf) por 30 dias; Fase 2
   = fail-high APENAS para spawns que não declaram skill NENHUMA,
   **ativada se após a re-medição da Fase 1 o unknown-ratio ainda
   for ≥ 0,10 (critério pela META, não por queda relativa — r2:
   queda de 50% pararia em ~0,21 e mascararia o alvo).**
   **Telemetria: janela = 90d de audit log, N mínimo = 100 spawns;
   re-medição 30d após cada fase.** Meta: unknown-ratio 0,43 → <0,10.
2. **Podar o core por telemetria — regra DETERMINÍSTICA:** arquivar
   skill core com 0 invocações em ≥90d E ausente do SKILL MAP;
   rollback = `archive/` restaurável + superfícies de contagem
   derivadas (nunca editadas à mão). 42 → ~25 (SKILL MAP + as usadas);
   ARQUIVAR, não deletar; consolidar sobreposições (lgpd×4 → 1;
   accessibility duplicada; 2 pares de basename duplicado que quebram
   atribuição de telemetria).
3. **Mover os 116 domain skills para squad-packs opt-in** via
   squad-install (tarball assinado — mecanismo já existe); manter 1-2
   domínios de referência em-tree. O repo recupera identidade de
   framework de governança; CI/soak param de vigiar prosa de domínio.
   Depende da fronteira de ownership (PLAN-171 W1c).
4. **Sweep de atualidade — EXECUTA no W-IM do PLAN-172 (dono único;
   r2 P1: sem rota dupla).** Este plano fica com a REGRA permanente:
   skills core citando modelos mortos (gemini-1.5-pro, gpt-4-turbo,
   claude-3-opus) e codebase fantasma; apontar
   check-model-deprecations do nightly para `.claude/skills/`.
5. **Despinar o "166":** contagem DERIVADA ("N core + M frontend +
   packs opt-in") nas superfícies de claim — remove o incentivo
   estrutural anti-poda (hoje podar exige cascata de claims +
   cerimônia, então ninguém poda).

## 2. Guard-rails

- Poda passa pelo processo SP-NNN/soak existente — o gate de skills
  não é contornado, é usado a favor.
- Superfícies de contagem (CLAUDE.md, README, npm) mudam por
  derivação + verify-counts, nunca à mão (classe doc-count-drift é
  recidiva: 4/8 achados do último NO-GO).
- Telemetria continua ligada pós-poda: se unknown-ratio não cair com
  a descoberta (passo 1), o problema é o INJECTOR, não o catálogo —
  reavaliar antes do passo 2.

## 3. Pronto-para-execução (S302e)

**ACs por passo:** P1 = mecanismo de sugestão vivo com positive
control (spawn sem skill ⇒ sugestão aparece no transcript) + baseline
do unknown-ratio publicado com inputs (janela 90d, N≥100) **+ (r4) a
re-medição obrigatória aos 30d publicada E a decisão de Fase 2
APLICADA pela regra do §1 (ratio ≥0,10 ⇒ fail-high ativado; <0,10 ⇒
registrado como atingido) — P1 não fecha no baseline.** P2 = lista
de arquivamento DERIVADA pela regra determinística (nunca curada à
mão) + `archive/` restaurável testado (1 skill arquivada e restaurada
no mesmo PR de teste). P3 = 116 domain movidos p/ packs assinados
(squad-install), 1-2 domínios de referência em-tree, CI verde sem os
packs; AC-mestre: install/upgrade de adopter SEM packs funciona
(smoke). P5 = superfícies de claim derivadas ("N core + M frontend +
packs opt-in"); AC: `check-claude-md-claims` verde com tolerance=0
após a mudança.

**Dependências verificadas:** PLAN-171 W1c (contrato de fronteira)
antes do P3; sweep de atualidade EXECUTA no W-IM/172 (dono único).

**Runbook sessão 1:** ligar telemetria/sugestão (P1) + medir
baseline. Nada de poda na sessão 1 — por design.

**Debate:** Codex r1→r3 (GO no r3); `/debate start PLAN-175` no
início da execução; a poda em si passa pelo processo SP-NNN/soak.

### 3.1 Medição S322 — o P1 se apoiava num mecanismo MORTO, e vivo ele é dependente de IDIOMA

Sonda reproduzível: `.claude/plans/PLAN-175/p1/probe-retrieval-language-gap.py`
(N=8 pares EN/PT, alvo esperado derivado à mão da ROUTING TABLE).

**Achado 1 — o índice nunca existiu.** `skill-retrieve.py` respondia
`mode=static-fallback` com `base_cosine=0.0` em TODOS os resultados,
porque `~/.claude/projects/<slug>/skill-index.sqlite` **não existia**.
`skill-index-build.py` cura em um comando (`OK: indexed 166 skills,
7472 idf terms`), mas **não há bootstrap automático**: o censo
`grep -rln skill-index-build` sobre `.claude/hooks/`, `.github/workflows/`
e `scripts/` devolve apenas o próprio build, o retrieve e os testes —
**nenhum hook, nenhum step de CI, nenhuma rota de install**. O índice
mora FORA do repo, então não é commitável: ele nasce morto em toda
máquina nova e em todo adopter. O AC do P1 ("mecanismo de sugestão
vivo com positive control") era insatisfazível sem isso, e o
`positive control` teria passado a medir o fallback.

**Achado 2 — vivo, o recall depende do IDIOMA da consulta.**
Controle validado (índice inválido ⇒ `mode=static-fallback`, medido):

| modo | recall@5 (N=8) |
|---|---|
| tf-idf, consulta em **inglês** | **6/8** |
| static-fallback (índice morto) | 4/8 |
| tf-idf, consulta em **português** | **2/8** |

O corpus de `SKILL.md` é em inglês; consultas em português colapsam
num atrator de idioma — `dpo-reporting` é top-1 em **4 das 8** queries
PT (é uma das poucas skills com massa de vocabulário PT/LGPD). Não é
efeito de comprimento: `dpo-reporting` tem 8.311 bytes contra 20.980
do `devops-ci-cd`, e o ranker usa cosine normalizado
(`skill-retrieve.py:271`).

**Consequência para este plano:** o `CLAUDE.md` deste projeto manda
operar em português, então **o caminho REAL de uso é exatamente o ramo
degradado** — o único em que ligar o índice PIORA o resultado
(2/8 contra os 4/8 de não ligar). O P1 não pode fechar declarando
"mecanismo vivo": ele precisa (a) uma rota de bootstrap do índice que
sobreviva a máquina nova e a adopter, e (b) uma decisão explícita
sobre o gap de idioma — indexar PT, normalizar a query, ou declarar a
limitação e manter o fallback como caminho primário. Enquanto (b) não
existir, ligar a sugestão por tf-idf em sessão PT é uma regressão
medida, não uma melhoria.

**Honestidade da amostra:** N=8, ground truth manual, uma única
tentativa por consulta. Basta para mostrar a DIREÇÃO e o atrator
(4/8 no mesmo slug não é ruído), não para fixar a magnitude. O P1
deve re-medir com N≥30 antes de decidir (b).

> **⚠️ O pré-requisito N≥30 é INEXECUTÁVEL sob demanda — medido na S325.**
> A re-medição precisa de spawns REAIS de arquétipo para ter denominador, e
> o instrumento do próprio repo reporta ZERO: `skill_unknown_ratio` do
> `/ceo-boot` sai `no custom-archetype spawns (0 general-purpose, 0
> test-pollution)`. Não há sinal a medir hoje, então N≥30 só se acumula ao
> longo de uma JANELA de uso normal — não é trabalho que uma sessão possa
> executar, é tempo de exposição. Tentar rodar a medição agora cai na classe
> `feedback-probe-window-must-exceed-signal-period`: sonda com janela menor
> que o período do sinal é estruturalmente morta, e produziria um
> unknown-ratio calculado sobre denominador zero.
>
> ⇒ **Consequência de sequenciamento:** este item NÃO é um gate que uma
> sessão abre; ele é um gate que o CALENDÁRIO abre. Quem for executar a
> Fase 1 deve tratá-lo como `external_wait` (o mesmo padrão do PLAN-170,
> cujo gatilho é a tag `v1.4.0-rc.1`), não como trabalho pendente.

## 4. Anexo S305 — reframe context-engineering (advisory)

A pesquisa S305 (linha 7 de `PLAN-178/research-S305.md`) reposiciona
este plano: a poda não é só honestidade de catálogo — a literatura de
context engineering documenta ganho de PERFORMANCE ao reduzir a
superfície de contexto carregada por sessão (context rot; compaction).
Nenhum passo muda. Leitura ADICIONAL (advisory) no AC do P5: medir com
a skill `context-budget` o delta de tokens do catálogo pré/pós-poda e
publicar junto das superfícies derivadas — transforma a poda em ganho
medido, não só em contagem honesta.
