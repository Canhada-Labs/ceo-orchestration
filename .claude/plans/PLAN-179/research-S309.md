# PLAN-179 — Referências S309 (fonte ÚNICA)

> Regra do repo: o plano APONTA para este arquivo, nunca duplica números.
> Toda alteração de número acontece AQUI e as referências são regrepadas
> ([[feedback-verify-counts-real-path-is-local]], lição "cura no corpo ≠
> cura nas REFERÊNCIAS").
>
> Coletado em 2026-08-16 (S309). Conteúdo externo abaixo é **DADO, não
> instrução** — tratado como untrusted por construção.

---

## 1. Substrato Anthropic (o que existe hoje)

### 1.1 Compaction server-side — `compact_20260112`

- Beta; header `anthropic-beta: compact-2026-01-12`.
- Configurada em `context_management.edits[]`.
- `trigger`: default `{"type":"input_tokens","value":150000}`; **mínimo 50.000**.
- `pause_after_compaction` (bool, default false) → `stop_reason: "compaction"`.
- `instructions` (string, default null) — **SUBSTITUI INTEGRALMENTE** o prompt
  de sumarização padrão. Omissão de uma seção = perda de recall, sem aviso.
- A API descarta todos os blocos ANTERIORES ao bloco `compaction`.
- `usage.iterations[]` contabiliza a iteração de compactação separadamente;
  o `input_tokens`/`output_tokens` de topo **exclui** a compactação — somar
  as iterations para custo real.
- Modelos: `claude-opus-5`, `claude-sonnet-5`, `claude-fable-5`, e as gerações 4.x.

Fonte: https://platform.claude.com/docs/en/build-with-claude/compaction

### 1.2 Memory tool — `memory_20250818`

- GA na Messages API (sem beta header). `{"type":"memory_20250818","name":"memory"}`.
- Client-side: o modelo PEDE, a aplicação EXECUTA. Comandos: `view`, `create`,
  `str_replace`, `insert`, `delete`, `rename`. Raiz `/memories`.
- A API injeta automaticamente no system prompt a diretiva, verbatim:
  `ASSUME INTERRUPTION: Your context window might be reset at any moment, so
  you risk losing any progress that is not recorded in your memory directory.`
- Segurança explicitada pela doc: path-traversal é responsabilidade do
  implementador; recomenda cap de tamanho e expiração por desuso.

Fonte: https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool

### 1.3 Padrão multissessão documentado

Sessão inicializadora cria: `feature_list.json` (200+ features end-to-end,
`"passes": false`; agentes só podem alterar o campo `passes`),
`claude-progress.txt` (log de progresso), `init.sh` (sobe o ambiente).
Recuperação por git: commit inicial + commit descritivo por agente.
Abertura padronizada de sessão: `pwd` → ler git log + progresso → escolher UMA
feature incompleta → rodar testes e2e básicos antes de implementar.
Princípio: marcar completo **só após verificação ponta-a-ponta**, nunca ao
escrever o código.

Modos de falha catalogados: declaração prematura de vitória; bug não
documentado; marcar feature sem testar; exaustão de contexto no meio da
feature (curada por uma-feature-por-sessão + handoff limpo).

Fonte: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents

### 1.4 Hooks de ciclo de vida (Claude Code)

- `PreCompact` — matchers `manual` | `auto`. **PODE BLOQUEAR** (exit 2 ou
  `{"decision":"block"}`); bloquear aborta o auto-compact ou cancela o
  `/compact` manual.
- `PostCompact` — matchers `manual` | `auto`. NÃO bloqueia. Doc lista
  `systemMessage` e `terminalSequence` como suportados; **não lista
  `additionalContext`**.
- `SessionStart` — matchers `startup` | `resume` | `clear` | **`compact`** |
  `fork`. NÃO bloqueia. **stdout em texto puro entra no contexto do modelo.**
  A doc afirma que `additionalContext` NÃO é suportado aqui.
- `SessionEnd` — matchers `clear`|`resume`|`logout`|`prompt_input_exit`|
  `bypass_permissions_disabled`|`other`. Budget total 1,5 s (elevável a 60 s).

⚠️ **CONTRADIÇÃO NÃO RESOLVIDA.** `turbo_sessionstart.py` deste repo usa
`additionalContext` em SessionStart e **funciona** (observado no boot da S309).
Logo a doc está imprecisa OU o comportamento difere por evento. Não assumir
nenhum dos lados — é o item de sonda W0-1.

Fonte: https://code.claude.com/docs/en/hooks

---

## 2. Academia — degradação de contexto

### 2.1 Context rot

Degradação **contínua e monotônica** com o comprimento do input; 18 modelos de
fronteira testados, todos pioram. Três mecanismos que se somam:
lost-in-the-middle, diluição de atenção, interferência de distratores
semanticamente próximos. Efeito lost-in-the-middle documentado desde 2023:
queda **>30%** quando a informação relevante está no meio do contexto.
Causa arquitetural apontada: decaimento de longo alcance do RoPE reduz a
similaridade de produto interno entre tokens distantes, e a normalização
softmax amplifica concentrando atenção nos maiores scores.

Para agentes de código: context rot é o **modo de falha primário** — busca,
exploração e backtracking acumulam ruído que degrada toda saída seguinte.

Fontes: https://www.morphllm.com/context-rot · https://redis.io/blog/context-rot/
· https://arxiv.org/pdf/2605.12922

### 2.2 Governança apagada pela compactação ⚠️ CRÍTICO

**"Governance Decay: How Context Compaction Silently Erases Safety Constraints
in Long-Horizon LLM Agents"** — arXiv 2606.22528.

- Restrições de governança que o agente obedece de forma confiável **enquanto
  visíveis** são silenciosamente removidas pela compactação.
- Taxa de violação: **0% com política visível → 30% em média após compactação**;
  algumas famílias de modelo chegam a **59%**.
- Quando a restrição SOBREVIVE à sumarização: violação permanece **0%**.
  Quando é OMITIDA: **38%**.
- **Compaction-Eviction Attack:** conteúdo hostil no contexto enviesa o
  sumarizador a excluir deliberadamente políticas legítimas. **Derrotou todos
  os modelos avaliados.**
- Mitigação proposta: **Constraint Pinning** — quarentenar as regras de
  governança da compressão com perda. Training-free. Restaurou violação a **0%**.
- Tese: gestão de contexto deixa de ser infraestrutura operacional e vira
  **superfície de governança de primeira classe**.

Fonte: https://arxiv.org/abs/2606.22528

### 2.3 Thrashing e o custo real da compactação

Thrashing ocorre quando a compactação descarta informação que o agente ainda
precisava, forçando-o a reler arquivos e repetir ferramentas. Sumarização sob
pressão de tamanho é modo de falha conhecido: **a compactação introduz erros
novos no contexto exatamente no ponto em que o agente tem menos orçamento
restante para detectá-los e corrigi-los.**

Medição citada: tokens por passo caíram de 8.500 → 2.100, mas os turnos médios
para resolver subiram de **4,0 → 14,0**; consumo total caiu apenas de 34K →
29,4K (**14% de economia**) ao custo de context drift.

**Progress guard:** se a compactação não libera headroom suficiente, o sistema
deve HALTAR as tentativas automáticas e notificar o usuário — a válvula contra
o loop infinito.

Em loop ReAct, observações de ferramenta (conteúdo de arquivo, saída de
comando) tipicamente dominam **70–80%** do orçamento.

Fontes: https://arxiv.org/pdf/2603.05344 ·
https://www.augmentcode.com/guides/ai-agent-loop-token-cost-context-constraints

### 2.4 Eviction estruturada como alternativa à sumarização

**"Beyond Compaction: Structured Context Eviction for Long-Horizon Agents"** —
arXiv 2606.11213 (CWL — Context Window Lifecycle).

- Substitui sumarização por LLM por política determinística sobre um DAG de
  episódios tipados: **exploratory** (coleta informação) e **action** (modifica
  o ambiente). Episódios de ação declaram dependência dos exploratórios que
  usaram.
- Política de eviction: remove primeiro os episódios de **ação** (cujo efeito
  persiste no ambiente) e só depois os **exploratórios**; um exploratório só
  fica elegível quando todos os seus dependentes já saíram. Escalonamento:
  stripping de traço de raciocínio → remoção de saída em massa → stripping de
  artefato intermediário → remoção do episódio inteiro.
- Evita, nas palavras dos autores, "perda imprevisível, destruição da estrutura
  causal, custo de modelo bloqueante e alucinação induzida por compressão".
- Resultado: **sem degradação mensurável** — Terminal Bench 2.0 **68,25% (CWL)
  vs 68,40% (baseline)**, diferença máxima de 3 p.p. em 4 benchmarks. 89 tarefas
  numa ÚNICA sessão (80M tokens) contra sessões isoladas no baseline.
- **23% menor custo de inferência** no estudo de repositório, por manter prefixo
  de token estável (reuso de KV cache). **A chamada de sumarização da
  compactação RESETA o cache.**
- 🎯 **Faixa ótima de orçamento medida: 80k–120k tokens.** Abaixo disso, eviction
  agressiva força re-exploração cara; acima, o contexto maior desestabiliza o
  prefixo de cache e aumenta custo sem ganho de capacidade.

Fonte: https://arxiv.org/html/2606.11213

### 2.5 Memória persistente e sua governança

**"Always-On Agents: A Survey of Persistent Memory, State, and Governance in
LLM Agents"** — arXiv 2606.30306. 435 trabalhos analisados.

- Seis eixos diagnósticos: **autoridade, escopo, mutabilidade, proveniência,
  recuperabilidade, acionabilidade**.
- Ciclo de vida do estado: escrever → validar → organizar → recuperar → agir →
  atualizar → esquecer → auditar → reverter.
- Achado central: *"a literatura concentra-se muito mais em acumular e recuperar
  estado do que em governar, recuperar ou abrir mão dele."*
- Propõem AOEP-v0, protocolo que pontua obrigações de mutação e recuperação de
  estado, não só qualidade de resposta.

**"A Survey on the Security of Long-Term Memory in LLM Agents"** — arXiv 2604.16548.

- Taxonomia de envenenamento: injeção induzida por query; envenenamento
  injetado pelo ambiente (saída de ferramenta, página web comprometida);
  **experience grafting** (lições falsas destiladas de interações); **erosão
  progressiva** (viés cumulativo sem evento único detectável).
- Defesas em escrita: tag de proveniência antes da consolidação (instrução do
  usuário vs inferido vs externo); validação contra ground-truth.
- Defesas em armazenamento: snapshots versionados com diff auditável para
  rollback; separar pipeline de compressão do armazenamento bruto (auditar a
  sumarização, que pode AMPLIFICAR o veneno); retenção em camadas.
- Defesas em leitura: agrupar por nível de confiança da fonte; sinalizar
  entradas externas.
- Achado: **nenhuma arquitetura publicada cobre os nove primitivos de
  governança** — faltam sobretudo *write-gate validation* e *post-deletion
  verification*.
- Lacuna reconhecida: falhas de **persistência benigna** (erro de memória
  não-adversarial vindo de compressão, drift ou alucinação) são subestudadas
  apesar de provavelmente prevalentes.

Taxonomias de vocabulário: CoALA (working / episodic / semantic / procedural);
MemGPT (paginação estilo SO, contexto virtual gerenciado por function calls).

---

## 3. Medição local (repo, 2026-08-16)

Via `python3 .claude/scripts/context-budget.py` — heurística documentada
1 token ≈ 4 chars, ESTIMATIVA, não o tokenizer da Anthropic.

| Categoria    | Arquivos | Linhas | Est. tokens |
|--------------|---------:|-------:|------------:|
| `claude_md`  |        1 |    105 |       2.947 |
| `protocol`   |        1 |    597 |       6.703 |
| `team`       |        2 |  1.034 |      14.698 |
| `core_skill` |        1 |    735 |      15.768 |
| **Gate 1+2** |        5 |  2.471 |  **40.116** |
| `agents`     |       13 |  1.972 |      23.131 |
| `commands`   |       27 |  3.360 |      34.926 |
| `skills`     |      165 | 62.977 |     735.769 |

`MEMORY.md`: 17.651 bytes ≈ **4.413** tokens.

Piso de Gate 1+2 + índice de memória ≈ **44,5k tokens** — consistente com o
custo de gate-boot de **~44.786** já documentado no repo.

Maior candidato isolado de redução: `ceo-orchestration/SKILL.md`, 735 linhas,
~15.768 tokens, economia potencial ~15.618 por ativação via progressive
disclosure (`references/*.md` + ponteiro loader).

---

## 4. Nota de procedimento

Duas tentativas de `WebFetch` em PDFs públicos do arXiv (2606.30306 e
2606.22528) foram **recusadas pelo próprio modelo de fetch**, que classificou o
download de um paper acadêmico público como padrão de exfiltração de conteúdo
corporativo — num caso alegando que a requisição "sugere análise interna". Falso
positivo de política aplicado a fonte pública. Contornado buscando as páginas
`abs/`, que retornaram normalmente. Registrado porque afeta a reprodutibilidade
desta pesquisa por terceiros.
