# Manifesto de evidência — pesquisa S298 (PLAN-169)

> Papel deste arquivo (codex r6-P2): tornar a base factual do plano
> verificável a partir do repositório, SEM reintroduzir os números de
> desempenho que a doutrina no-speed-claim mantém fora daqui. Os dois
> relatórios originais estão no archive privado do maintainer; a
> integridade é atestada pelos sha256 abaixo e as FONTES são públicas.

## Integridade dos originais arquivados

```
c39834be64dd330684770e8b3ba5e25ef7a3de3ef23a990177f09f6ad829736b  research-academia.md
c6084ee168823a0c849f1ef87550d5737877a0965aff69dd92eb6117d2aa895e  research-claude-updates.md
```

(Citações de linha nos registros de debate — ex. `research-academia.md:250`
— referem-se a ESTES arquivos, verificáveis por hash junto ao maintainer.)

## Fontes do relatório de substrato (todas oficiais salvo indicado)

- code.claude.com/docs/en/changelog (lido integralmente na janela jun→ago/2026)
- code.claude.com/docs/en/cross-session-messaging · /settings · /permission-modes
- code.claude.com/docs/en/hooks · /agent-teams · /sub-agents · /tools-reference · /channels
- Agent SDK TypeScript reference (docs oficiais)
- Terciárias (rotuladas no original): releasebot.io, dev.classmethod.jp, explainx.ai, 9to5mac

## Bibliografia do relatório acadêmico (com nível de confiança no original)

- When Parallelism Pays Off / Co-Coder — arXiv:2606.00953
- Anthropic — When to use multi-agent systems (and when not to) — claude.com/blog
- Anthropic — How we built our multi-agent research system — anthropic.com/engineering
- METR — Upper-bounding productivity gains from coding agents (fev/2026) — metr.org/notes
- METR — Early-2025 AI impact on experienced OSS developers (RCT) — arXiv:2507.09089
- Why Do Multi-Agent LLM Systems Fail? (MAST) — arXiv:2503.13657 · NeurIPS 2025 D&B
- When More Agents Hurt: Generalized Amdahl — TechRxiv 10.36227/techrxiv.177220351.10957097
- Amdahl's Law for AI Agents — electric.ax (blog, 2026-02-19)
- Multi-LLM-Agents Debate: Performance, Efficiency, Scaling — ICLR 2025 Blogposts
- The Deliberative Illusion — arXiv:2606.03032
- Can LLM Agents Really Debate? — arXiv:2511.07784
- AgentArk — arXiv:2602.03955
- GoAgent — arXiv:2603.19677
- MOC: Multi-Order Communication — arXiv:2606.02359
- CIA: Inferring Communication Topology — arXiv:2604.12461
- Coordination as an Architectural Layer — arXiv:2605.03310
- Language Model Teams as Distributed Systems — arXiv:2603.12229
- Multi-Agent Verification (MAV/AVR) — arXiv:2502.20379
- AI21 Maestro — Test-Time Compute for SWE-bench — ai21.com/blog
- Agentless — arXiv:2407.01489
- ParallelMuse — arXiv:2510.24698
- Search-Time Contamination in Deep Research Agents — arXiv:2606.05241
- ReliabilityBench — arXiv:2601.06112
- Efficient Evaluation with Statistical Guarantees — arXiv:2601.20251
- Code Benchmarks Should Prioritize Rigor, Reliability, Reproducibility — arXiv:2501.10711
- RigorBench — arXiv:2606.22678
- Security Threat Modeling for AI-Agent Protocols — arXiv:2602.11327
- Beyond Message Passing: Semantic View of Agent Communication Protocols — arXiv:2604.02369
- AIOS (COLM 2025) · AgentOS — arXiv:2603.08938
- CloudZero — Claude Code Agents in 2026 (blog)
- Faros AI — The AI Productivity Paradox (blog)
- The Six Sigma Agent — arXiv:2601.22290 (marcado NÃO-CONFIÁVEL no original)

## Mapa das claims citadas nos registros de debate (codex r11-P2)

> As citações `research-*.md:N` nos debates usam a numeração dos
> ORIGINAIS lidos pelos críticos (anteriores aos headers de aviso
> adicionados no arquivamento — offset de algumas linhas). Mapa
> sanitizado (sem números de desempenho) por seção, revisável
> localmente:

| Citação | Seção no original | Claim (sanitizada) |
|---|---|---|
| academia:~37 | §1 Tier-1, entrada METR fev/2026 | análise de transcripts é upper-bound autodeclarado; juiz validado em poucas dezenas de labels |
| academia:~134 | §2 "onde entrega ganho real" | condições conjuntas para ganho: read-mostly, contexto agregado > janela, verificador barato, decomposição por grafo, topologia star, moeda declarada |
| academia:~188-194 | §3 E0 | pergunta do teto de Amdahl; H medido do audit log (o plano ESTENDE para S com tempo-morto — correção codex r4) |
| academia:~250 | §3 bloco metodológico comum + E4 | pré-registro assinado; 3 braços; N do E4 e contagem de invocações que fundamentou o MF-3 do debate |
| updates:~70-92 | §2.1 cross-session | tabela de transporte; exceção own-child (macOS só com processo vivo; PID-1 nunca); `refuse` invisível ao emissor; guardrails são modelo+classifier |
| updates:~133-195 | §2.2-2.6 | task tools sem permissão; Workflow caps; eventos de hook novos (lista §2.6); settings que desligam governança |
| updates:~237-247 | §3 riscos de drift | 2.1.195 matchers hifenizados exact-match; inversões 2.1.214/191/176 |
| updates:~339-341 | §Discrepâncias | doc vs changelog no cross-machine send; `UserPromptSubmit`×peer NÃO verificado (probe (a) do plano) |

## Débitos de verificação declarados no original (inalterados)

1. Frequências do MAST — duas extrações discordaram; conferir na camera-ready.
2. "When More Agents Hurt" — fetch 403; teorema conhecido só por snippet.
3. Números extraídos de PDF marcados [B] no original — re-checar antes de citar.
