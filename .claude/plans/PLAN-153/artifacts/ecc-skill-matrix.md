# Matriz completa — 277 skills do ecc (affaan-m/ecc @ MIT) vs ceo-orchestration
# Gerada pelo workflow wf_c555404e-093 (34 agentes read-only, 2026-07-03)
# formato: nome | verdict | quality | categoria | overlap | racional

accessibility | INSPIRE | q4 | engenharia-pratica | partial:frontend/accessibility-and-wcag; frontend/frontend-accessibility; government/accessibility-section-508 | Delta WCAG 2.2 (SC 2.5.8/2.4.11) + traits nativos iOS/Android p/ atualizar nossa 2.1
agent-architecture-audit | ADAPT | q5 | agentes-meta | partial:workflow audit-fanout; core/ai-llm-orchestration | Taxonomia 12-layer de falhas de agente (wrapper regression, repair loops) é única e densa
agent-eval | SKIP | q3 | agentes-meta | partial:workflow eval-baseline-n20 | Doc de CLI externo a instalar; nosso harness N=20 já cobre eval reprodutível
agent-harness-construction | ADAPT | q4 | agentes-meta | partial:core/mcp-server-authoring | Regras densas de action-space/observation/tool granularity; complementa mcp-authoring
agent-introspection-debugging | ADAPT | q4 | agentes-meta | none | Loop 4-fases capture-diagnose-recover-report p/ agente travado; sem equivalente nosso
agent-payment-x402 | SKIP | q3 | dominio-negocio | none | SDKs cripto vendor-specific (OKX/Base/x402); fora do escopo de governança de agentes
agent-self-evaluation | ADAPT | q4 | agentes-meta | none | Scorecard 5 eixos c/ evidence rule + hook Stop + scripts; advisory junto ao pair-rail
agent-sort | INSPIRE | q4 | agentes-meta | partial:core/agent-architect; skill squad-install | Ideia DAILY vs LIBRARY c/ evidência grep p/ trimar nossa lib de 151 skills por repo
agentic-engineering | SKIP | q3 | agentes-meta | partial:core/llm-routing-and-finops; core/parallelization-by-default | 64 linhas de princípios rasos; routing/custo/decomposição já cobertos nos nossos
agentic-os | INSPIRE | q4 | agentes-meta | partial:core/ceo-orchestration | Kernel/roteamento duplica nosso CEO; só a camada de daemons/cron agendados agrega
ai-first-engineering | SKIP | q2 | engenharia-pratica | partial:core/testing-strategy; core/code-review-checklist | Casca de princípios genéricos em 52 linhas; nada acionável novo
ai-regression-testing | ADAPT | q4 | engenharia-pratica | partial:core/testing-strategy; core/evidence-based-qa | Blind-spot mesmo-modelo = racional do nosso pair-rail; padrões sandbox-path concretos
android-clean-architecture | ADAPT | q4 | linguagem-framework | partial:domains/mobile/skills/mobile-app-builder | Denso (módulos, DI, Room/Ktor, código real); aprofunda mobile além do builder genérico
angular-developer | ADOPT | q5 | linguagem-framework | none | 155 linhas + 35 references versionadas (signals, SSR, forms); lacuna Angular na lib
api-connector-builder | ADAPT | q4 | engenharia-pratica | none | Doutrina 'siga o padrão do repo, não invente 2a arquitetura' c/ workflow e guardrails
api-design | SKIP | q4 | engenharia-pratica | full:core/public-api-design | REST patterns sólidos (524 linhas) mas já cobertos por public-api-design nosso
architecture-decision-records | SKIP | q4 | engenharia-pratica | full:core/architecture-decisions | Nosso sistema ADR (172 ADRs + schema + gates) já supera o formato Nygard básico
article-writing | INSPIRE | q4 | escrita-conteudo | partial:core/technical-writing; marketing-global/content-creator | Banned patterns anti-slop e 'proof antes de adjetivo' valem; resto duplica os nossos
automation-audit-ops | INSPIRE | q4 | agentes-meta | partial:workflow nightly-hygiene; workflow audit-fanout | Taxonomia configured/authenticated/verified/stale p/ enriquecer nightly-hygiene
autonomous-agent-harness | SKIP | q4 | agentes-meta | partial:core/ceo-orchestration | Operação autônoma contínua conflita com nossa doutrina advisory/Owner-confirm
autonomous-loops | ADAPT | q5 | agentes-meta | partial:core/parallelization-by-default; skill fan-plan | Catálogo denso de 6 padrões de loop (611 l); alias deprecated de continuous-agent-loop
backend-patterns | SKIP | q4 | linguagem-framework | partial:core/public-api-design; core/data-schema-design; core/performance-engineering | Node/Next patterns bons (562 l) mas fatiados entre 3 skills core nossas
benchmark | SKIP | q3 | engenharia-pratica | partial:core/performance-engineering; frontend/frontend-performance-optimization | Checklist raso de CWV/p95/build; nossos perf skills cobrem mais fundo
benchmark-methodology | ADAPT | q4 | dominio-negocio | none | Rubrica 1-5 em 9 dimensões p/ análise competitiva; depende de 2 skills irmãs da cadeia
benchmark-optimization-loop | ADAPT | q4 | engenharia-pratica | partial:core/performance-engineering | Loop medido bounded (baseline+gate de correção+ledger); complementa perf-engineering
blender-motion-state-inspection | SKIP | q4 | outro | none | Método sólido mas nicho 3D/Blender; fora do escopo do framework
blueprint | INSPIRE | q4 | agentes-meta | partial:core/pre-plan-brainstorm + protocolo PLAN/fan-plan | Ideia forte: context brief autocontido por step p/ agente frio; resto duplica PLANs
brand-discovery | ADAPT | q4 | dominio-negocio | none | Entrevista de marca multi-sessão c/ laddering; adequar persistência ao nosso padrão
brand-voice | ADAPT | q4 | escrita-conteudo | partial:domains/marketing-global/content-creator | Voice profile reutilizável de fontes reais; remover refs ECC, portar p/ marketing
browser-qa | ADAPT | q4 | engenharia-pratica | partial:audit-page (skill) + frontend/* | QA de browser pós-deploy c/ blast-radius read-only e INCONCLUSIVE explícito
bun-runtime | SKIP | q3 | linguagem-framework | none | Referência de runtime que reescreve docs do Bun; fora do escopo de governança
canary-watch | ADAPT | q4 | devops-infra | partial:core/observability-and-ops + core/devops-ci-cd | Verificação pós-deploy (HTTP/SSE/assets/perf) c/ modos e thresholds concretos
carrier-relationship-management | ADAPT | q5 | dominio-negocio | partial:domains/supply-chain/supply-chain-strategist | Conhecimento denso de frete (RFP, scorecard, FMCSA); enriquece domains/supply-chain
cisco-ios-patterns | ADAPT | q4 | devops-infra | none | Padrões IOS seguros p/ change-window; exigiria criar domain networking (squad novo)
ck | SKIP | q4 | agentes-meta | full:auto-memory ~/.claude/projects + memory-scratchpad | Memória por projeto redundante c/ nosso auto-memory; scripts Node ferem stdlib-only
claude-devfleet | SKIP | q3 | agentes-meta | partial:core/ceo-orchestration + spawn/fan-plan | Orquestra via servidor MCP externo; compete c/ nosso spawn e adiciona dependência
click-path-audit | ADAPT | q4 | engenharia-pratica | partial:audit-page (skill) | Traça efeitos colaterais de estado que review estático perde; bom p/ frontend-team
clickhouse-io | SKIP | q3 | dados-ml | partial:core/data-schema-design | Padrões de um DB específico; data-schema-design cobre a camada de doutrina
code-tour | INSPIRE | q4 | engenharia-pratica | partial:onboard (skill) + core/codebase-onboarding | Artefato .tour persona-targeted c/ âncoras file:line; ideia p/ enriquecer /onboard
codebase-onboarding | SKIP | q4 | engenharia-pratica | full:core/codebase-onboarding + onboard (skill) | Duplica nosso core/codebase-onboarding e /onboard quase 1:1
codehealth-mcp | INSPIRE | q4 | engenharia-pratica | partial:core/code-review-checklist + veto-check | Depende de MCP externo+token; vale só a postura fail-honest (nunca inventar score)
coding-standards | SKIP | q2 | engenharia-pratica | partial:core/code-review-checklist + core/minimal-change-discipline | Princípios genéricos KISS/DRY/YAGNI; nossos skills de review já cobrem
competitive-platform-analysis | ADAPT | q4 | dominio-negocio | none | Scoping de competidores c/ tiers e positioning brief; caberia em marketing-global
competitive-report-structure | ADAPT | q4 | dominio-negocio | partial:domains/business-support/executive-summary | Relatório decision-grade c/ white-space; fecha o pipeline competitivo de 3 skills
compose-multiplatform-patterns | SKIP | q3 | linguagem-framework | partial:domains/mobile/mobile-app-builder | Padrões Compose/KMP específicos de framework; mobile-app-builder cobre o domínio
config-gc | ADAPT | q5 | agentes-meta | partial:nightly-hygiene (workflow) | GC de config c/ human-in-loop, soft-delete e log de undo; casa c/ nossa governança
configure-ecc | INSPIRE | q3 | agentes-meta | partial:scripts/install.sh + squad-install (skill) | ECC-específico; ideia do wizard interativo via AskUserQuestion p/ nosso install.sh
connections-optimizer | SKIP | q3 | dominio-negocio | partial:domains/marketing-global/twitter-engager + linkedin-content-creator | Gestão de grafo social pessoal dependente de x-api; marginal p/ o framework
content-engine | SKIP | q4 | escrita-conteudo | partial:domains/marketing-global/skills/content-creator (+ social-media-strategist) | Squad marketing-global já cobre conteúdo por plataforma; hard-bans de slop é o único plus
content-hash-cache-pattern | INSPIRE | q4 | engenharia-pratica | none | Padrão único e estreito (cache SHA-256); vale 1 seção em skill de perf, não skill inteira
context-budget | ADAPT | q4 | agentes-meta | partial:audit-tokens + agent-budget (comandos nossos, fora das 151 listadas) | Auditoria ESTÁTICA de overhead de contexto complementa nosso audit-tokens (runtime)
continuous-agent-loop | SKIP | q2 | agentes-meta | none | Stub de roteamento de 46 linhas apontando p/ skills ECC que não temos
continuous-learning | SKIP | q2 | agentes-meta | none | DEPRECATED pelo próprio ECC em favor do continuous-learning-v2
continuous-learning-v2 | ADAPT | q5 | agentes-meta | partial:nosso sistema lesson-review/memória (fora das 151 listadas) | Instintos atômicos c/ confiança e escopo-projeto; infra real; reescrever em stdlib
cost-aware-llm-pipeline | SKIP | q4 | dados-ml | partial:core/llm-routing-and-finops (+ core/ai-llm-orchestration) | Doutrina já coberta por llm-routing-and-finops; código-exemplo é o único extra
cost-tracking | SKIP | q3 | agentes-meta | partial:agent-budget (comando nosso, fora das 151 listadas) | Acoplado ao hook cost-tracker do ECC; nosso agent-budget cobre o caso de uso
council | INSPIRE | q4 | agentes-meta | partial:/debate + PROTOCOL.md (Plan→Debate→Execute) e core/architecture-decisions | Anti-anchoring (subagentes frescos só c/ a pergunta) vale importar p/ o /debate
cpp-coding-standards | ADOPT | q5 | linguagem-framework | none | C++ Core Guidelines destiladas em 724 linhas densas; lacuna real (embedded sem C++)
cpp-testing | ADOPT | q4 | linguagem-framework | none | GoogleTest/CTest/sanitizers acionável; par natural do cpp-coding-standards
crosspost | SKIP | q3 | escrita-conteudo | partial:domains/marketing-global/skills/social-media-strategist (+ twitter/linkedin) | Redundante c/ squad marketing; depende de brand-voice/content-engine do ECC
csharp-testing | ADOPT | q4 | linguagem-framework | none | xUnit/FluentAssertions/Testcontainers c/ código real; lacuna .NET no catálogo
customer-billing-ops | ADAPT | q4 | dominio-negocio | partial:core/monetization-and-billing | OPERAÇÃO de billing (refund/churn triage) complementa nossa skill de implementação
customs-trade-compliance | ADAPT | q4 | dominio-negocio | partial:domains/supply-chain/skills/supply-chain-strategist | Domínio real (GRI/HS, FTA, denied-party screening); encaixa no squad supply-chain
dart-flutter-patterns | ADAPT | q4 | linguagem-framework | partial:domains/mobile/skills/mobile-app-builder | Padrões Flutter densos e copy-paste (BLoC/Riverpod/GoRouter); aprofunda nosso mobile
dashboard-builder | INSPIRE | q3 | devops-infra | partial:core/observability-and-ops | Só a doutrina 'perguntas de operador primeiro' vale; resto coberto por observability
data-scraper-agent | SKIP | q4 | dados-ml | none | Receita de produto (scraper Gemini+Actions grátis); fora do escopo de governança
data-throughput-accelerator | INSPIRE | q3 | dados-ml | none | Heurísticas ETL ok e bloco de accounting bom, mas 73 linhas rasas p/ skill própria
database-migrations | ADAPT | q5 | engenharia-pratica | partial:core/data-schema-design (inclui migration strategy) | Checklist zero-downtime + SQL bom/ruim por ORM, mais fundo que nossa cobertura atual
deep-research | SKIP | q3 | agentes-meta | full:deep-research (nosso harness c/ verificação adversarial, fora das 151) | Já temos harness deep-research superior; este é acoplado a firecrawl/exa MCPs
defi-amm-security | SKIP | q4 | seguranca | full:domains/fintech/skills/blockchain-security-audit (+ solidity-smart-contracts) | blockchain-security-audit + solidity-smart-contracts já cobrem AMM/DeFi/CEI
delivery-gate | INSPIRE | q4 | agentes-meta | partial:nossa suíte de 53 hooks (Stop hooks de governança, fora das 151) | Detector regex de racionalização no Stop hook é boa ideia p/ nossa suíte de hooks
deployment-patterns | SKIP | q4 | devops-infra | full:core/devops-ci-cd | Textbook genérico; devops-ci-cd já cobre CI/CD, Docker e estratégias de deploy
design-system | INSPIRE | q3 | engenharia-pratica | partial:frontend/design-system-and-components + audit-page (harness) | Modo AI-slop-detection e score 10-dim valem; auditoria visual ja coberta
django-celery | SKIP | q4 | linguagem-framework | none | Cookbook Celery solido mas stack-especifico; fora do escopo de governanca
django-patterns | SKIP | q4 | linguagem-framework | none | Cookbook Django/DRF denso porem commodity de stack; fora de escopo
django-security | SKIP | q4 | seguranca | partial:core/security-and-auth | Checklist Django util mas security-and-auth cobre a doutrina; resto commodity
django-tdd | SKIP | q4 | linguagem-framework | partial:core/testing-strategy | pytest-django/factory_boy bem feito; doutrina ja em testing-strategy
django-verification | SKIP | q3 | engenharia-pratica | partial:core/evidence-based-qa | Pipeline de verificacao por fases ok; evidence-based-qa cobre o metodo
dmux-workflows | SKIP | q3 | agentes-meta | partial:core/parallelization-by-default + core/ceo-orchestration | Preso a ferramenta dmux/tmux; nosso substrato de paralelismo e spawn/Task nativo
docker-patterns | SKIP | q4 | devops-infra | partial:core/devops-ci-cd | Compose/healthcheck bons mas devops-ci-cd ja cobre Docker; commodity
documentation-lookup | ADAPT | q3 | agentes-meta | none | Doutrina docs-vivas > training-data com teto de 3 calls; reescrever MCP-agnostica
dotnet-patterns | SKIP | q4 | linguagem-framework | none | C#/.NET idiomatico decente; cookbook de stack fora do escopo de governanca
dynamic-workflow-mode | ADOPT | q4 | agentes-meta | none | Contrato harness-por-tarefa + arvore de quando extrair skill; governanca pura
e2e-testing | SKIP | q4 | engenharia-pratica | partial:core/testing-strategy + frontend/frontend-patterns | Playwright/POM solido mas commodity; doutrina ja em testing-strategy
ecc-guide | SKIP | q3 | outro | partial:core/help-me | Navegacao do proprio repo ECC; help-me + verify-counts ja cobrem o principio
ecc-recipes | INSPIRE | q3 | agentes-meta | partial:core/help-me + goap (harness) | Camada familia+run-order+stop-condition sobre comandos; evoluir help-me/goap
ecc-tools-cost-audit | SKIP | q3 | outro | partial:agent-budget + audit-tokens (harness) | Workflow amarrado ao repo irmao ECC-Tools; custo ja tem agent-budget/audit-tokens
email-ops | INSPIRE | q3 | dominio-negocio | partial:domains/business-support/skills/support-responder | Guardrails draft-first + prova no Sent valem como secao; resto e operador mailbox
energy-procurement | ADOPT | q5 | dominio-negocio | none | Expertise densa com numeros reais (tarifas, demand charge, PPA); dominio novo
enterprise-agent-ops | SKIP | q2 | agentes-meta | partial:core/observability-and-ops + core/incident-management | Casca de bullets genericos em 51 linhas; nossos skills de ops cobrem melhor
error-handling | SKIP | q4 | engenharia-pratica | partial:core/chaos-and-resilience | Principios bons mas commodity; retry/circuit-breaker ja em chaos-and-resilience
eval-harness | ADAPT | q4 | agentes-meta | partial:domains/community/skills/agent-evaluation + advanced-evaluation | EDD com pass@k + taxonomia de graders; fundir com agent-evaluation
evm-token-decimals | ADAPT | q4 | dominio-negocio | partial:domains/fintech/skills/financial-correctness-and-math | Classe de bug afiada (decimals por chain/bridge); fundir no squad fintech
exa-search | SKIP | q3 | outro | none | Doc de MCP de vendor, drift-prone por confissao propria; fora de escopo
fal-ai-media | SKIP | q3 | outro | none | Guia de vendor MCP p/ midia generativa; fora do escopo de governanca
fastapi-patterns | SKIP | q4 | linguagem-framework | none | Cookbook FastAPI/Pydantic v2 forte, mas stack-especifico fora de escopo
finance-billing-ops | SKIP | q3 | dominio-negocio | partial:core/monetization-and-billing | Workflow operador ECC-especifico (Stripe/seat-truth); depende de skills irmas ECC
flox-environments | SKIP | q4 | devops-infra | none | Doc vendor (origin: Flox) denso mas fora do escopo de governanca; e manual de produto
flutter-dart-code-review | ADAPT | q4 | linguagem-framework | partial:domains/mobile/skills/mobile-app-builder + core/code-review-checklist | Checklist denso e acionavel (436L); dobrar no dominio mobile como review Flutter
foundation-models-on-device | SKIP | q4 | linguagem-framework | none | Snapshot de API Apple iOS 26; nicho, perecivel, sem demanda na nossa biblioteca
frontend-a11y | SKIP | q4 | linguagem-framework | full:frontend/accessibility-and-wcag + frontend/frontend-accessibility | Bom conteudo React a11y mas cobrimos WCAG/ARIA em duas skills proprias
frontend-design-direction | SKIP | q2 | linguagem-framework | partial:frontend/ux-and-user-journeys + frontend/design-system-and-components | Casca de 93L salvada de PR stale; remete a skill oficial Anthropic; pouco metodo
frontend-patterns | SKIP | q4 | linguagem-framework | full:frontend/frontend-patterns | React/Next patterns densos (657L) mas mesmo territorio da nossa frontend-patterns
frontend-slides | ADOPT | q4 | escrita-conteudo | none | Auto-contido: presets+CSS base+scripts (export-pdf.sh, extract-pptx.py); lacuna real
fsharp-testing | SKIP | q4 | linguagem-framework | partial:core/testing-strategy | Denso (xUnit/FsCheck) mas F# e nicho sem demanda no nosso ecossistema
gan-style-harness | ADAPT | q4 | agentes-meta | partial:core/cross-llm-pair-review (avaliador separado ~ pair-rail) | Loop gerador-avaliador adversarial c/ rubrica; complementa pair-rail como squad
gateguard | ADAPT | q4 | agentes-meta | partial:core/evidence-based-qa (doutrina investigue-antes) + nossos hooks PreToolUse | Gate deny-force-allow pre-edit com A/B (+2.25); reimplementar como hook stdlib nosso
generating-python-installer | SKIP | q3 | devops-infra | none | Nuitka/Inno Setup Windows, metade em chines; nicho fora do escopo do framework
git-workflow | SKIP | q4 | engenharia-pratica | full:core/git-workflow-discipline | 716L de branching/commits genericos; ja temos disciplina git propria
github-ops | ADAPT | q4 | devops-infra | partial:core/devops-ci-cd + core/git-workflow-discipline | Playbook gh CLI (triage/PR/release/security) util p/ operar nosso repo OSS
golang-patterns | ADOPT | q4 | linguagem-framework | none | Go idiomatico denso (675L, codigo real); lacuna de linguagem na biblioteca
golang-testing | ADAPT | q4 | linguagem-framework | partial:core/testing-strategy (estrategia generica; sem detalhe Go) | Table-driven/fuzz/bench densos (721L); portar como par da golang-patterns
google-workspace-ops | SKIP | q2 | outro | none | 96L de workflow raso preso a superficie de tools Google; sem metodo denso
growth-log | ADAPT | q4 | agentes-meta | partial:subsistema de lessons do framework (/lesson-review, fora das 151) | 3 regras fortes (falha>sucesso, merge por causa-raiz, transferibilidade) p/ lessons
healthcare-cdss-patterns | ADOPT | q4 | dominio-negocio | none | CDSS puro-funcional c/ modelos de dados reais (interacao/dose/NEWS2); lacuna healthcare
healthcare-emr-patterns | ADOPT | q4 | dominio-negocio | none | EMR safety-first c/ fluxo de encontro concreto; nosso healthcare so tem CS/marketing
healthcare-eval-harness | ADOPT | q4 | dominio-negocio | none | Harness que BLOQUEIA deploy em falha CRITICAL (100%/95% gates); casa com nossa filosofia
healthcare-phi-compliance | ADAPT | q4 | seguranca | partial:core/pii-data-flow + core/compliance-lgpd (LGPD generico, nao PHI/RLS) | Classificacao PHI + RLS SQL + audit insert-only; fundir na familia privacy/healthcare
hermes-imports | INSPIRE | q3 | agentes-meta | none | So o checklist de sanitizacao pre-publicacao vale; resto e plumbing ECC-interno
hexagonal-architecture | ADOPT | q4 | engenharia-pratica | none | Ports&Adapters multi-linguagem c/ metodo passo-a-passo; lacuna de arquitetura
hipaa-compliance | ADAPT | q3 | seguranca | partial:core/compliance-lgpd + domains/healthcare/* | Overlay HIPAA p/ squad healthcare; guardrails reais mas refs a skills ecc ausentes
homelab-network-readiness | SKIP | q4 | devops-infra | none | Checklist sólido, mas homelab hobbyista está fora da missão de governança
homelab-network-setup | SKIP | q3 | devops-infra | none | Planejamento de rede caseira; fora de escopo do framework
homelab-pihole-dns | SKIP | q4 | devops-infra | none | Denso e prático (Docker/DoH), mas domínio homelab não serve repos-alvo
homelab-vlan-segmentation | SKIP | q4 | devops-infra | none | Config VLAN concreta e boa, porém domínio homelab fora de escopo
homelab-wireguard-vpn | SKIP | q4 | devops-infra | none | Configs WireGuard reais, porém domínio homelab fora de escopo
hookify-rules | INSPIRE | q4 | agentes-meta | none | Regras declarativas .md->hook: ideia boa sobre nossos 53 hooks; engine hookify ausente
inherit-legacy-style | ADAPT | q5 | engenharia-pratica | partial:core/codebase-onboarding | Anti style-drift: grilling protocol + enforcement hook; casa com nossa governança
intent-driven-development | ADAPT | q5 | engenharia-pratica | partial:core/spec-clarify + core/requirement-quality-checklist | AC-NNN observável (must-not+verificação+revisão) enriquece spec-clarify; fundir
inventory-demand-planning | ADAPT | q4 | dominio-negocio | partial:domains/supply-chain/skills/supply-chain-strategist | Conhecimento denso de demand planning; encaixa em squad retail/supply-chain
investor-materials | ADAPT | q3 | dominio-negocio | none | Método 'fonte única entre assets' é real; caberia em squad founder/fundraising
investor-outreach | INSPIRE | q3 | escrita-conteudo | partial:domains/sales/skills/sales-outreach | Hard-bans e ask-discipline valem; craft outbound já coberto por sales-outreach
ios-icon-gen | SKIP | q4 | linguagem-framework | partial:domains/mobile/skills/mobile-app-builder | Utilitário nicho de assets Xcode (tem scripts/); fora da missão de governança
iterative-retrieval | ADAPT | q4 | agentes-meta | partial:core/parallelization-by-default | Loop DISPATCH-EVALUATE-REFINE (teto 3 ciclos) ataca o context-problem dos fan-outs
ito-basket-compare | SKIP | q2 | dominio-negocio | partial:domains/fintech/skills/prediction-markets | Teaser vendor Itô, 64 linhas; prediction-markets nosso cobre o domínio
ito-data-atlas-agent | SKIP | q3 | agentes-meta | partial:domains/fintech/skills/prediction-markets | 4-lanes HITL raso e vendor-tied; nosso advisory-gating já institucionaliza isso
ito-market-intelligence | SKIP | q2 | dominio-negocio | partial:domains/fintech/skills/prediction-markets | Teaser Itô de 61 linhas; workflow genérico sem método próprio
ito-trade-planner | SKIP | q3 | dominio-negocio | partial:domains/fintech/skills/trading-execution | Worksheet não-executório vendor-tied; guardrails já são política do framework
java-coding-standards | ADOPT | q4 | linguagem-framework | none | 384 linhas PASS/FAIL + detecção Spring/Quarkus; preenche lacuna JVM da biblioteca
jira-integration | ADAPT | q4 | devops-infra | none | Útil p/ repos-alvo com Jira; reescrever credenciais/pin de versão MCP no nosso padrão
jpa-patterns | ADAPT | q4 | linguagem-framework | partial:core/data-schema-design (índices/migrações) | N+1, fetch, HikariCP concretos; par do java-coding-standards; alinhar camadas
knowledge-ops | INSPIRE | q3 | agentes-meta | partial:sistema de memória do framework (memory-scratchpad, fora das 151) | Roteamento entre camadas de memória inspira; stack (Supabase/Linear) não transfere
kotlin-coroutines-flows | ADAPT | q4 | linguagem-framework | partial:domains/mobile/skills/mobile-app-builder | BAD/GOOD densos de concorrência estruturada; integrar a squad mobile/JVM
kotlin-exposed-patterns | ADAPT | q4 | linguagem-framework | partial:core/data-schema-design (índices/migrações) | Denso (720 linhas: DSL/DAO/Hikari/Flyway); nicho Exposed — só se houver squad JVM
kotlin-ktor-patterns | SKIP | q4 | linguagem-framework | none | Ktor textbook denso (690 ln) mas conteudo que o modelo ja sabe; stack fora do nosso alvo
kotlin-patterns | SKIP | q3 | linguagem-framework | none | Kotlin idiomatico generico; conhecimento base do modelo, sem metodo proprio
kotlin-testing | SKIP | q4 | linguagem-framework | partial:core/testing-strategy | Kotest/MockK denso porem textbook; nossa testing-strategy cobre a doutrina
kubernetes-patterns | ADAPT | q4 | devops-infra | partial:core/devops-ci-cd | YAML prod + kubectl debug copy-paste + tabelas de decisao; complementa devops-ci-cd
laravel-patterns | SKIP | q3 | linguagem-framework | partial:domains/saas-platforms/skills/filament-specialist | Laravel generico; filament-specialist ja cobre nosso nicho Laravel
laravel-plugin-discovery | SKIP | q3 | linguagem-framework | none | Amarrado ao MCP LaraPlugins.io; vendor-specific, fora de escopo
laravel-security | SKIP | q4 | seguranca | partial:core/security-and-auth | 948 ln densas mas stack-specific; security-and-auth cobre a doutrina geral
laravel-tdd | SKIP | q4 | linguagem-framework | partial:core/testing-strategy | TDD Laravel textbook runnable; testing-strategy nossa cobre o metodo
laravel-verification | INSPIRE | q3 | engenharia-pratica | partial:core/evidence-based-qa | Ideia de verification-loop faseado por stack (gates sequenciais) vale; conteudo raso
latency-critical-systems | SKIP | q4 | engenharia-pratica | partial:domains/trading-hft/skills/latency-budgets | Boa ordem de otimizacao mas latency-budgets + performance-engineering ja cobrem
lead-intelligence | ADAPT | q4 | dominio-negocio | partial:domains/sales/skills/outbound-strategist | Pipeline lead-gen c/ scoring ponderado (tem agents/); reescrever tool-agnostic p/ sales
liquid-glass-design | ADAPT | q4 | linguagem-framework | partial:domains/mobile/skills/mobile-app-builder | API iOS 26 pos-cutoff c/ codigo concreto; enriquece mobile-app-builder
llm-trading-agent-security | ADAPT | q4 | seguranca | partial:domains/trading-hft/skills/kill-switches | Injection=ataque financeiro, spend limits, simulacao; forte fit fintech+governanca
logistics-exception-management | ADAPT | q4 | dominio-negocio | partial:domains/supply-chain/skills/supply-chain-strategist | Expertise real (Carmack window, detention, claims); adiciona ao squad supply-chain
loop-design-check | ADOPT | q5 | agentes-meta | none | Metas decidiveis + anti-Goodhart + 5 modos de falha; governanca de loop pura, gap nosso
mailtrap-email-integration | SKIP | q3 | outro | none | How-to de vendor de e-mail; fora de escopo do framework
make-interfaces-feel-better | ADAPT | q4 | engenharia-pratica | partial:frontend/design-system-and-components | Formulas concretas (radius concentrico, optical align, text-wrap); enriquece frontend
manim-video | SKIP | q3 | escrita-conteudo | none | Workflow ok (tem assets/) mas nicho de producao de video; fora de escopo
market-research | SKIP | q3 | dominio-negocio | none | Checklist raso; nosso harness deep-research ja cobre pesquisa verificada
marketing-campaign | ADAPT | q3 | dominio-negocio | partial:domains/marketing-global/* (squad inteiro) | Camada de orquestracao multi-canal faseada que falta ao squad marketing-global
mcp-server-patterns | SKIP | q3 | agentes-meta | full:core/mcp-server-authoring | Redundante: mcp-server-authoring nosso cobre o mesmo com mais profundidade
messages-ops | SKIP | q2 | outro | none | Recuperacao de DMs/iMessage pessoal; fora de escopo de governanca
ml-adoption-playbook | ADAPT | q3 | dados-ml | none | Fases sensatas p/ ML em codebase nao-ML; seed de squad dados-ml, reescrever
mle-workflow | ADAPT | q4 | dados-ml | none | Denso, scope-calibration maduro; cross-refs a skills ECC exigem reescrita no padrao
motion-advanced | ADOPT | q5 | linguagem-framework | none | 596 linhas densas: gestures, SVG, useAnimate, cleanup rules; nada nosso cobre motion
motion-foundations | ADAPT | q5 | linguagem-framework | partial:frontend/design-system-and-components (token governance) | Base do trio motion: tokens, springs, a11y, SSR-safety; alinhar ao token governance
motion-patterns | ADOPT | q4 | linguagem-framework | none | Padroes copy-paste (modal, stagger, page transition) com regras numericas nao-genericas
motion-ui | SKIP | q4 | linguagem-framework | none | Monolito v4.2 antigo; o trio motion-foundations/patterns/advanced cobre o mesmo melhor
mysql-patterns | ADAPT | q4 | linguagem-framework | partial:core/data-schema-design (PostgreSQL) | SQL concreto + divergencias MySQL/MariaDB; complementa nosso schema-design que e PG-only
nanoclaw-repl | SKIP | q2 | agentes-meta | none | 34 linhas; doc de ferramenta interna do ecc (scripts/claw.js), inutil fora de la
nestjs-patterns | ADOPT | q4 | linguagem-framework | none | Modulos, DTO/guards/interceptors, config; backend TS que nao temos
netmiko-ssh-automation | ADOPT | q4 | devops-infra | none | Read-only por default, timeouts, flag explicita p/ config — etos de governanca compativel
network-bgp-diagnostics | ADOPT | q4 | devops-infra | none | Triage read-only c/ tabela de estados e comandos; candidato a squad network-ops nova
network-config-validation | ADOPT | q4 | devops-infra | none | Pre-flight em camadas c/ codigo Python real de deteccao de comandos perigosos
network-interface-health | ADOPT | q4 | devops-infra | none | Metodo baseline-trend + tabela de contadores; diagnostico acionavel, dominio que nao temos
nextjs-turbopack | INSPIRE | q3 | linguagem-framework | none | Version-pinned, apodrece; so o footgun proxy.ts vs middleware.ts vale como pitfall
nodejs-keccak256 | ADAPT | q4 | dominio-negocio | partial:domains/fintech/skills/blockchain-security-audit | Footgun real (sha3-256 NIST != Keccak) c/ prova executavel; dobrar no dominio fintech
nutrient-document-processing | SKIP | q3 | outro | none | Cookbook de API comercial de vendor; fora de escopo de framework de governanca
nuxt4-patterns | ADOPT | q4 | linguagem-framework | none | Hydration/useFetch/routeRules especificos; framework frontend sem cobertura nossa
openclaw-persona-forge | SKIP | q3 | agentes-meta | none | Gacha de personas-lagosta p/ plataforma OpenClaw, em chines; fora de escopo total
opensource-pipeline | ADAPT | q4 | seguranca | none | Fork->sanitize->package c/ gates PASS/FAIL; espelha nosso de-id vivido mas cita agents ecc
orch-add-feature | SKIP | q3 | agentes-meta | partial:core/ceo-orchestration | Wrapper fino de 45 linhas sobre orch-pipeline; nosso Plan->Debate->Execute ja cobre
orch-build-mvp | SKIP | q3 | agentes-meta | partial:core/pre-plan-brainstorm | Depende de gan-harness/comandos ecc inexistentes aqui; slicing vertical ja e pratica nossa
orch-change-feature | SKIP | q3 | agentes-meta | partial:core/ceo-orchestration | Wrapper fino; distincao tweak-vs-fix (mudar testes primeiro) e o unico insight
orch-fix-defect | SKIP | q3 | agentes-meta | partial:core/testing-strategy | Regressao-como-teste-vermelho primeiro; doutrina ja coberta por testing/evidence-based-qa
orch-pipeline | INSPIRE | q4 | agentes-meta | partial:core/ceo-orchestration (Plan->Debate->Execute, niveis L1-L3) | Classificador de tamanho (3 sinais, maior tier vence) pode refinar nossa rubrica L1-L3
orch-refine-code | SKIP | q3 | agentes-meta | partial:core/incremental-refactoring | Characterization tests + passos pequenos ja estao em incremental-refactoring nosso
parallel-execution-optimizer | INSPIRE | q3 | agentes-meta | partial:core/parallelization-by-default | Lane matrix c/ checagem de colisao de write-surface vale dobrar no nosso parallelization
perl-patterns | SKIP | q4 | linguagem-framework | none | Denso (Perl 5.36+ idioms) mas stack legado de baixa demanda p/ a biblioteca
perl-security | SKIP | q4 | seguranca | none | Taint mode/DBI/untaint solidos, porem acoplado a Perl; mesma baixa demanda
perl-testing | SKIP | q4 | linguagem-framework | none | Test2::V0/prove/TDD denso, mas so util se uma squad Perl existisse
plan-orchestrate | INSPIRE | q4 | agentes-meta | partial:fan-plan/goap (bridges advisory plano->spawn no repo, fora das 151) | fan-plan ja cobre; vale a ideia de chain por step + reviewer por linguagem
plankton-code-quality | INSPIRE | q4 | agentes-meta | none | Anti rule-gaming de config de linter casa com nossos guards; depende de tool externa
postgres-patterns | ADAPT | q4 | linguagem-framework | partial:core/data-schema-design | Cheat-sheets de indice/tipos/RLS complementam nosso data-schema-design
prediction-market-oracle-research | INSPIRE | q3 | dominio-negocio | partial:domains/fintech/skills/prediction-markets | Checklist de qualidade de sinal (liquidez/spread/resolucao) enriquece nossa skill
prediction-market-risk-review | INSPIRE | q3 | seguranca | partial:domains/fintech/skills/prediction-markets | Gates de risco (advice/venue/privacy) uteis; mencoes a Ito = ECC-especifico
prisma-patterns | ADOPT | q5 | linguagem-framework | none | Traps nao-obvios reais (updateMany count, migrate reset); porta quase como esta
product-capability | ADAPT | q4 | dominio-negocio | partial:core/pre-plan-brainstorm + core/spec-clarify | Contrato de capability (invariantes/interfaces/aberturas) complementa pre-plan
product-lens | INSPIRE | q3 | dominio-negocio | partial:core/pre-plan-brainstorm + core/product-conversion-readiness | Diagnostico 'why before build' (7 perguntas YC) util; raso p/ portar inteiro
production-audit | ADAPT | q4 | engenharia-pratica | partial:core/evidence-based-qa + workflow audit-fanout | Lens de prontidao p/ prod com evidencia local; reescrever no nosso padrao
production-scheduling | ADOPT | q5 | dominio-negocio | none | Expertise densa (TOC/DBR, SMED, OEE, frozen window); semeia squad manufacturing
project-flow-ops | INSPIRE | q3 | engenharia-pratica | partial:domains/project-management/* (project-shepherd, studio-operations) | Classificacao merge/port/close/park p/ triage de PRs e boa; acoplado a Linear
prompt-optimizer | ADAPT | q4 | agentes-meta | partial:core/help-me | Pipeline advisory de reescrita de prompt + match de componentes complementa help-me
python-patterns | ADAPT | q4 | linguagem-framework | none | Util p/ dev de hooks, mas precisa alinhar a py>=3.9 + stdlib-only do repo
python-testing | ADAPT | q4 | linguagem-framework | partial:core/testing-strategy | Pytest/fixtures/parametrize denso; alinhar a TestEnvContext e gates de CI
pytorch-patterns | ADOPT | q4 | dados-ml | none | Padroes reais (device-agnostic, seeds, shapes explicitas); semearia dominio ML
quality-nonconformance | ADOPT | q5 | dominio-negocio | none | NCR/CAPA/SPC denso e regulado (FDA/IATF/AS9100); par de production-scheduling
quarkus-patterns | ADAPT | q4 | linguagem-framework | none | Denso mas acoplado a Camel/RabbitMQ/Lombok; generalizar se criar squad Java
quarkus-security | ADAPT | q4 | seguranca | partial:core/security-and-auth | JWT/OIDC/RBAC concreto em Quarkus; so faz sentido junto de uma squad Java
quarkus-tdd | ADAPT | q4 | linguagem-framework | partial:core/testing-strategy | JUnit5/Mockito/RESTAssured/JaCoCo denso; portar so com a squad Java completa
quarkus-verification | ADAPT | q4 | devops-infra | partial:core/devops-ci-cd | Loop build->lint->test->scan->native e checklist util; stack-especifico
ralphinho-rfc-pipeline | SKIP | q2 | agentes-meta | partial:core/ceo-orchestration (Plan->Debate->Execute + waves) | Casca de listas sem metodo; nosso pipeline de plano/waves ja cobre com rigor
react-native-patterns | ADAPT | q4 | linguagem-framework | partial:domains/mobile/skills/mobile-app-builder | RN/Expo denso e acionável; complementa mobile-app-builder iOS/Swift-first
react-patterns | ADAPT | q4 | linguagem-framework | partial:frontend/frontend-patterns | Hooks/RSC/forms React 18-19 densos; enriquece nosso frontend-patterns
react-performance | ADAPT | q5 | linguagem-framework | partial:frontend/frontend-performance-optimization | 70+ regras priorizadas (base Vercel MIT); merge no frontend-performance-optimization
react-testing | ADAPT | q4 | linguagem-framework | partial:core/testing-strategy | RTL/MSW/axe + fronteira unit-vs-E2E; gap real no nosso time frontend
recsys-pipeline-architect | ADOPT | q4 | dados-ml | none | Framework 6 estágios claro + workflow de 8 passos; autocontido, domínio novo
recursive-decision-ledger | INSPIRE | q3 | agentes-meta | none | Ledger append-only + promotion gate p/ rollouts vale; texto curto e esotérico
redis-patterns | ADAPT | q4 | linguagem-framework | partial:core/performance-engineering | Cache/locks/rate-limit sólidos; anexar como par do performance-engineering
regex-vs-llm-structured-text | ADAPT | q4 | dados-ml | partial:core/llm-routing-and-finops | Pipeline híbrido regex→LLM c/ confidence scoring; casa com llm-routing-and-finops
remotion-video-creation | SKIP | q4 | linguagem-framework | none | 29 rule-files Remotion úteis mas nicho tool-specific fora do escopo
repo-scan | SKIP | q2 | engenharia-pratica | partial:core/codebase-onboarding | SKILL.md é instalador de tool externa via git clone; /onboard já cobre
research-ops | INSPIRE | q3 | agentes-meta | partial:deep-research (slash skill) | Guardrails fato/evidência/inferência bons; acoplado ao stack ECC (exa, market)
returns-reverse-logistics | ADAPT | q4 | dominio-negocio | partial:domains/retail/skills/customer-returns | Grading, disposição, fraude e RTV enriquecem nosso retail/customer-returns
rules-distill | ADAPT | q4 | agentes-meta | none | Coleta determinística + veredito LLM bom p/ manter 151 skills; rules/ é deles
rust-patterns | SKIP | q4 | linguagem-framework | none | Denso porém commodity; nenhum archetype nosso é Rust
rust-testing | SKIP | q4 | linguagem-framework | partial:core/testing-strategy | TDD Rust sólido mas stack fora dos nossos archetypes
safety-guard | SKIP | q3 | seguranca | full:check_bash_safety.py + canonical-edit guard | Nossos hooks fail-closed já superam; skill é prosa sem código de hook
santa-method | ADAPT | q4 | agentes-meta | partial:core/cross-llm-pair-review | Dual-review independente + loop de convergência complementa o pair-rail
scientific-db-pubmed-database | ADOPT | q4 | outro | none | Sintaxe MeSH/E-utilities concreta e não-óbvia; base p/ squad de research
scientific-db-uspto-database | ADOPT | q4 | outro | none | Fontes oficiais USPTO + logs reproduzíveis; útil p/ squad legal/IP
scientific-pkg-gget | SKIP | q3 | outro | none | Wrapper de CLI genômica; nicho demais p/ nossos domínios atuais
scientific-thinking-literature-review | ADAPT | q4 | outro | partial:deep-research (slash skill) | PICO + screening sistemático + tipos de review enriquecem o deep-research
scientific-thinking-scholar-evaluation | ADAPT | q3 | outro | none | Rubrica 1-5 por dimensão útil p/ squad academic-humanities; resto é casca
search-first | ADAPT | q4 | engenharia-pratica | none | Anti-NIH c/ matriz adopt/extend/build; referencia agente researcher deles
security-bounty-hunter | ADAPT | q4 | seguranca | partial:core/security-and-auth + /security-review | Lente explorável/pagável + skip-list de ruído somam ao security-review
security-review | ADAPT | q4 | seguranca | partial:core/security-and-auth | Checklist FAIL/PASS denso p/ web/TS (504 linhas + anexo cloud); complementa o nosso
security-scan | INSPIRE | q3 | seguranca | partial:core self-test (guard self-test) | Ideia otima — scan de .claude/ p/ injection/misconfig — mas e wrapper de npm externo
seo | SKIP | q4 | dominio-negocio | full:domains/marketing-global/skills/seo-specialist | Redundante: nosso seo-specialist ja cobre CWV, schema.org, sitemap/robots
skill-comply | ADAPT | q5 | agentes-meta | partial:self-test + eval-baseline-n20 (medem guards/modelo, não compliance de skill) | Mede se skills/rules sao SEGUIDAS em 3 niveis de prompt; ouro p/ governanca; tirar uv
skill-scout | ADAPT | q3 | agentes-meta | none | Busca dedup (local+marketplace+GitHub) antes de criar skill; encaixa na cerimonia SP-NNN
skill-stocktake | ADAPT | q4 | agentes-meta | partial:skill-review + nightly-hygiene | Auditoria de qualidade da biblioteca c/ cache + quick-diff; util p/ nossas 151
social-graph-ranker | ADAPT | q4 | dominio-negocio | none | Math real de bridge-score p/ warm intros; referencia skills ecc ausentes, reescrever refs
social-publisher | SKIP | q2 | dominio-negocio | none | Wrapper de SaaS pago (SocialClaw, API key); vendor lock, fora de escopo
springboot-patterns | ADOPT | q4 | linguagem-framework | none | 315 linhas de padroes Spring densos e portaveis; zero cobertura Java nas nossas 151
springboot-security | ADAPT | q4 | linguagem-framework | partial:core/security-and-auth | Spring Security concreto (JWT filter, @PreAuthorize); sobrepoe parte do generico nosso
springboot-tdd | ADAPT | q3 | linguagem-framework | partial:core/testing-strategy | JUnit5/Mockito/Testcontainers ok mas curto; fundir num squad springboot se portar
springboot-verification | ADAPT | q3 | linguagem-framework | partial:core/evidence-based-qa | Loop build-lint-test-scan com comandos mvn/gradle reais; shape util p/ squad Java
strategic-compact | ADAPT | q4 | agentes-meta | none | Compact em fronteira logica c/ sinal real (usage do transcript); hook e node, portar p/ py
swift-actor-persistence | INSPIRE | q4 | linguagem-framework | partial:domains/mobile/skills/mobile-app-builder | Um unico padrao (actor repository); estreito demais p/ skill propria
swift-concurrency-6-2 | ADAPT | q4 | linguagem-framework | partial:domains/mobile/skills/mobile-app-builder | Migracao Swift 6.2 atual, exemplos erro-vs-fix; nucleo de um eventual squad iOS
swift-protocol-di-testing | INSPIRE | q4 | linguagem-framework | partial:domains/mobile/skills/mobile-app-builder | DI por protocolos focados e bom mas e 1 padrao; secao p/ squad iOS
swiftui-patterns | ADAPT | q4 | linguagem-framework | partial:domains/mobile/skills/mobile-app-builder | Tabela @Observable/property-wrappers acionavel; melhor peca de um squad iOS
taste | SKIP | q4 | escrita-conteudo | none | Direcao criativa angelcore p/ music video; depende de skills de video ecc; fora de escopo
tdd-workflow | ADAPT | q4 | engenharia-pratica | partial:core/testing-strategy + core/evidence-based-qa | Secao plan-handoff trata *.plan.md como input NAO-confiavel (anti-injection); vale portar
team-agent-orchestration | INSPIRE | q3 | agentes-meta | partial:core/ceo-orchestration + core/parallelization-by-default | Nosso CEO protocol ja cobre; schema JSON de card Kanban c/ merge_gate e a ideia nova
team-builder | SKIP | q3 | agentes-meta | partial:spawn (comando) + core/agent-architect + routing table team.md | Picker interativo de agentes; redundante c/ nosso spawn + routing table
terminal-ops | SKIP | q3 | engenharia-pratica | partial:core/evidence-based-qa + core/git-workflow-discipline | Guardrails genericos (inspect-first, provar antes de alegar) ja cobertos pelos nossos
tinystruct-patterns | SKIP | q4 | linguagem-framework | none | Denso (279 linhas + references) mas framework Java de nicho; demanda ~zero
token-budget-advisor | SKIP | q3 | agentes-meta | partial:core/terse-mode + agent-budget | terse-mode + agent-budget ja cobrem economia; heuristica de multiplicadores e fragil
ui-demo | ADOPT | q4 | engenharia-pratica | none | Metodo Discover-Rehearse-Record denso p/ videos demo Playwright; util p/ devrel/launch
ui-to-vue | SKIP | q2 | linguagem-framework | none | Nicho: screenshots->Vue3 via CLI externa (DASHSCOPE_API_KEY); fora de escopo
uncloud | SKIP | q3 | devops-infra | none | Referencia CLI de plataforma self-host de nicho (uc); irrelevante p/ governanca
unified-notifications-ops | INSPIRE | q3 | agentes-meta | none | Ideia boa: lane unica de notificacao do operador, digest-first; texto ECC-branded
verification-loop | SKIP | q2 | engenharia-pratica | partial:core/evidence-based-qa + core/testing-strategy (+ builtin /verify) | Checklist generico build/type/lint/test; ja coberto por QA doctrine e /verify
video-editing | INSPIRE | q3 | escrita-conteudo | partial:domains/marketing-global/video-optimization-specialist | Pipeline em camadas (FFmpeg/Remotion/ElevenLabs) e boa ideia; tool-heavy e drift-prone
videodb | SKIP | q3 | outro | none | Skill vendor-specific (SaaS VideoDB, API deles); plug de produto, fora de escopo
visa-doc-translate | SKIP | q2 | outro | none | Workflow pessoal (docs chineses de visto, OCR macOS); nicho demais
vite-patterns | ADAPT | q4 | linguagem-framework | partial:frontend/frontend-performance-optimization | Denso: pre-bundling, env inlining, lib mode, pitfalls; candidato a squad frontend
vue-patterns | ADAPT | q4 | linguagem-framework | partial:frontend/frontend-patterns (universal) | Guia Vue3/Pinia/Nuxt solido; nossos frontend sao universais — caberia como squad vue
windows-desktop-e2e | ADOPT | q5 | engenharia-pratica | none | 888 linhas: pywinauto/UIA, tabelas por framework, Qt, CI; nada equivalente nosso
workspace-surface-audit | ADAPT | q4 | agentes-meta | partial:core/codebase-onboarding + /ceo-info + /ceo-boot | Audit read-only de MCP/plugins/env do harness; complementa ceo-info; reescrever ECC->nosso
x-api | SKIP | q3 | outro | partial:domains/marketing-global/twitter-engager | Ref de API X drift-prone (o proprio skill avisa); custo de manutencao alto
