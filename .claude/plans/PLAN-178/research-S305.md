# Pesquisa S305 — academia vs. framework (fonte única de referências)

> **Natureza:** levantamento ADVISORY (2 rodadas, S304+S305). Números
> abaixo são CLAIMS DE LITERATURA, não medições nossas — nenhum deles
> pode migrar para superfície pública de doc (doutrina §3/PLAN-172 e
> research-README/PLAN-169). Este arquivo é a ÚNICA autoridade das
> referências; planos apontam para cá, nunca duplicam números.

## 1. Famílias arquiteturais mapeadas e veredito

| # | Família | Fonte-chave | Claim central da literatura | Veredito p/ nós |
|---|---------|------------|------------------------------|-----------------|
| 1 | Orchestrator-worker | [Anthropic multi-agent research](https://www.anthropic.com/engineering/multi-agent-research-system) | agente ≈4× tokens de chat; multi-agente ≈15×; vale só p/ fan-out de leitura paralelizável; "upgrade de modelo > dobrar budget" | JÁ SOMOS; economics confirmam "no speed claim" |
| 2 | Taxonomia de falhas MAST | [arXiv 2503.13657](https://arxiv.org/abs/2503.13657) | 14 modos de falha, 3 categorias; spec-ambiguity + coordenação = 79% das quebras; problema é ARQUITETURAL | **Adotar como checklist de auditoria** (PLAN-178 W0) |
| 3 | Pipeline-first (Agentless) | [FSE 2025](https://lingming.cs.illinois.edu/publications/fse2025.pdf) | pipeline fixo localizar→reparar→validar competitivo com agentes autônomos a ~$0,70/issue | **Adotar parcial**: Workflow determinístico p/ fan-outs recorrentes (PLAN-178 W1) |
| 4 | Test-time compute / verificadores | [BoN-MAV 2502.20379](https://arxiv.org/pdf/2502.20379), [GenPRM](https://ojs.aaai.org/index.php/AAAI/article/view/40797/44758) | escalar VERIFICADORES (não builders) escala melhor que self-consistency | Fundamentação do gate barato §2/PLAN-172 (execução mora lá) |
| 5 | Cascata/roteamento | [RouteLLM/FrugalGPT](https://www.tmls.nyc/research/model-routing-cascades), [Cluster-Route-Escalate 2606.27457](https://arxiv.org/pdf/2606.27457) | −85% custo mantendo ~95% qualidade; só ~14% das queries ao modelo forte | Fundamenta E6/PLAN-172 e camadas T/P do PLAN-176 |
| 6 | Long-horizon (MEA) | [LongHorizon-Harness 2608.01964](https://www.alphaxiv.org/overview/2608.01964), [Horizon Gap 2608.06663](https://arxiv.org/html/2608.06663) | erros compõem autoregressivamente; Manage-Execute-Audit com estado auditável + subtarefas bounded | JÁ SOMOS (Plan→Execute→Verify + HMAC); citar como validação externa |
| 7 | Context engineering | [Sourcegraph/Anthropic](https://sourcegraph.com/blog/context-engineering), [Context rot 2606.29718](https://arxiv.org/pdf/2606.29718) | context editing +29%; +memory tool +39%; −84% tokens em workflow longo; retorno de subagente condensado 1-2k tokens | Reframe do PLAN-175 (poda = performance); shard ADR-141 já é o padrão certo |
| 8 | Self-correction intrínseca | [2310.01798](https://arxiv.org/abs/2310.01798) | LLM não se auto-corrige sem feedback externo; às vezes piora | Valida pair-rail; NUNCA aceitar self-review como gate |
| 9 | Self-preference (LLM-as-judge) | [2410.21819](https://arxiv.org/abs/2410.21819) | juiz mesmo-modelo favorece o próprio output (perplexidade) | Valida cross-VENDOR > fresh-context same-model |
| 10 | Cross-context review | [2603.12123](https://arxiv.org/pdf/2603.12123) | revisor sem contexto de produção: +10-15% acurácia (anchoring/commitment) | **Adotar parcial**: critic fresco por retry (PLAN-178 W2) |
| 11 | Multi-agent debate (MAD) | [ICLR blogpost MAD](https://d2jud02ci9yv69.cloudfront.net/2025-04-28-mad-159/blog/mad/), [2510.12697](https://arxiv.org/html/2510.12697v1) | ~2 rodadas capturam quase todo o ganho; amostragem dependente afunila na resposta errada | Confirma lição S296 e o circuit-breaker do tiering §4/PLAN-172 |
| 12 | Gauntlet-loop | [origem](https://x.com/mattshumer_/status/2081830214384886228); análise S304 em `memory/reference-gauntlet-loop-research.md` | builder ≠ juiz; critic fresco; barra por exemplar | NÃO adotar em escala; 2 regras extraíveis (PLAN-178 W2) |
| 13 | Skills auto-evolutivas | [Voyager-linha](https://beancount.io/bean-labs/research-logs/2026/05/08/voyager-open-ended-embodied-agent-lifelong-learning), [CODESKILL 2605.25430](https://arxiv.org/html/2605.25430), [SoK Agentic Skills 2602.20867](https://arxiv.org/pdf/2602.20867) | curriculum + skill library + self-verification = template dominante de lifelong learning | JÁ TEMOS (PLAN-154 gated learning, default-OFF); estudo de ativação no PLAN-178 W3 |
| 14 | Segurança inter-agente | [Prompt-infection LLM-to-LLM](https://www.prompthalo.ai/feeds/blog/prompt-infection-llm-to-llm-multi-agent-systems), [SoK Trust-Authorization Mismatch 2512.06914](https://arxiv.org/pdf/2512.06914), [contagion multiplex](https://link.springer.com/article/10.1186/s42400-026-00628-w) | agente intermediário = confused deputy; modelos com 0% de injeção direta caem em 100% via pedido de agente-par "confiável"; escalada de privilégio por trust inter-agente | **Adotar como classe de auditoria** (PLAN-178 W0, junto do MAST) |
| 15 | Substrato Claude Code 2026 | [changelog/releases](https://releasebot.io/updates/anthropic/claude-code) | nested subagents (3 níveis), scoped permissions, cost-attribution por agente, agent teams, dreaming (curadoria de memória agendada), background review | Triage no PLAN-178 W1; teams full-mesh NÃO (MAST + lição S284 clobber) |

## 2. A doutrina-síntese (candidata, não claim)

**Escalada-sob-gatilho, verificação-primeiro:** trabalho nasce solo em
pipeline determinístico; escala para multi-agente APENAS sob gatilho
medido (fan-out de leitura, contexto que não cabe, verificação
reprovada); compute extra vai primeiro para VERIFICADORES cross-vendor;
rodadas com teto e troca de alvo; estado sempre auditável. Velocidade
esperada vem de: cascata, pipeline determinístico, paralelizar SÓ
leitura, upgrade de modelo. Nada disso autoriza claim de velocidade —
tudo passa pelos pré-registros do PLAN-172.

## 3. O que a pesquisa NÃO achou

- Nenhuma evidência de que mais autores em paralelo ganhem em código
  com contexto compartilhado (confirma E0/Amdahl do PLAN-172 §0).
- Nenhum framework acadêmico com trilha de auditoria tamper-evident +
  gating humano fail-closed — nosso diferencial segue sem par direto;
  a lacuna da literatura é a NOSSA tese (MAST §conclusão: "orquestração
  melhor, não mais tokens").
