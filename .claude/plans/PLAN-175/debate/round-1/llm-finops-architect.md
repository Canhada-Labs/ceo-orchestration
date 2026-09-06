---
round: 1
archetype: LLM FinOps Architect
skill: llm-routing-and-finops
agent_persona: LLM FinOps Architect (Principal, advisory — NO VETO)
generated_at: 2026-09-06T04:40:00Z
---

## Verdict

ADJUST — 3 blocking

## Summary (≤ 3 bullets)

- **A janela de telemetria de que o plano depende não existe.** A família de
  audit deste projeto inteira tem **15,8 dias** (medido: 9 arquivos, 133.377
  eventos, `2026-08-21T12:13:43Z` → `2026-09-06T07:27:23Z`), porque a família
  nasceu na migração da W1 do PLAN-182. A regra «0 invocações em ≥ 90 d» é
  avaliada sobre um corpus que não chega a 1/5 da janela — e verdadeira para
  toda skill por construção.
- **A regra determinística, aplicada HOJE com o corpus INTEIRO, entrega 42 → 39,
  não 42 → ~25** (o número do título). E as 3 que ela arquivaria são
  `agent-architect`, `ceo-orchestration` e `terse-mode` — a segunda é a skill que
  o Gate 2 do `CLAUDE.md` manda invocar em TODA sessão. O instrumento é cego ao
  canal dominante de invocação.
- **O gate de calendário do §3.1 está REFUTADO no HEAD:** 102 `agent_spawn` em
  15,8 dias, 11 skills nomeadas distintas, unknown-ratio **0,275**. Tanto o
  N ≥ 100 quanto o N ≥ 30 são satisfeitos por ~duas semanas de uso normal. O P1
  pode abrir como pacote livre esta semana — depois de consertar a regra, não
  antes.

## Risks

### R-FIN1 — P1 — a janela de 90 d não existe; e a invocação default mede 5,5 horas

Medido agora, com o instrumento que o próprio repo publica (varredura de
`<PK>/audit-log*.jsonl`, todos os 9 arquivos, rotacionados inclusive):

| grandeza | valor medido |
|---|---:|
| arquivos da família | 9 |
| eventos | 133.377 |
| evento mais antigo | `2026-08-21T12:13:43Z` |
| evento mais recente | `2026-09-06T07:27:23Z` |
| **profundidade da história** | **15,8 dias** |

A causa é conhecida e está no `CLAUDE.md` §5: a família por projeto foi criada
pela W1 do PLAN-182 (`audit-key` e `.salt` com mtime `2026-08-21 09:13`); tudo
que é anterior está em OUTRA família, arquivada pela W2. Ou seja: **o repo não
tem, e não terá antes de ~2026-11-19, 90 dias de telemetria atribuível a este
projeto.**

Pior, o instrumento default subestima ainda mais: `<ROOT>/.claude/scripts/skill-health.py:704`
tem `--since` default `30d`, e `discover_logs` (`skill-health.py:207-215`) só
agrega os irmãos rotacionados sob `--include-rotated`. O `audit-log.jsonl`
primário no HEAD tem 11.384 linhas cobrindo `2026-09-06T01:58:33Z` →
`2026-09-06T07:26:56Z` — **5,5 horas**. Uma execução `skill-health --since 90d`
sem `--include-rotated` responde sobre 5,5 h de log e reporta zero invocações
para 42 de 42 skills, com convicção. É a classe dominante deste repo:
instrumento verde cuja pergunta envelheceu.

**Mitigação:** a regra do §1.2 passa a citar o comando EXATO
(`skill-health --since all --include-rotated`), o AC do P2 publica a
profundidade REAL do corpus junto do resultado (é uma linha do relatório), e o
limiar deixa de ser «90 d» absoluto para ser «toda a história atribuível, com a
profundidade declarada e ≥ N spawns» — senão o plano espera três meses por uma
janela que a migração de tamper-evidence zerou.

### R-FIN2 — P1 — a regra determinística entrega 42 → 39; o título promete 42 → ~25

Executei a regra do §1.2 como escrita, com o corpus INTEIRO (não os 90 d que
não existem): «0 invocações E ausente do SKILL MAP».

| perna da regra | resultado |
|---|---:|
| core skills no disco | 42 |
| com 0 invocações (`agent_spawn.skill`, família toda) | 31 |
| presentes no texto do SKILL MAP (`team.md` + `frontend-team.md`) | 39 |
| **satisfazendo AS DUAS pernas** | **3** |

O conjunto é `{agent-architect, ceo-orchestration, terse-mode}`. Método: teste
de substring do slug contra o texto dos dois SKILL MAPs — ele ERRA para MAIS
mapeadas, então 3 é um teto, não um piso: a regra real entrega ≤ 3.

O título do plano (linha 3) e o §1.2 (linhas 40-41) prometem **«42 → ~25»**.
As duas afirmações não podem ser verdadeiras ao mesmo tempo: a conjunção com
o SKILL MAP domina, e a telemetria não contribui com nenhuma decisão — 28 das
31 skills sem invocação estão no mapa e sobrevivem. **A poda de 17 skills que o
plano vende não vem da regra que o plano declara.** Ou o número é de outra
regra (curada à mão — exatamente o que o AC do P2 proíbe: «DERIVADA pela regra
determinística, nunca curada à mão», linhas 79-80), ou o número está errado.

**Mitigação:** o plano publica o resultado da regra ANTES de prometer um
tamanho de alvo — «42 → N, N derivado» — ou declara a segunda regra
(consolidação de sobreposições, linhas 42-44) como um passo SEPARADO com
critério próprio, porque é ela, e não a telemetria, que teria de produzir os
outros 14.

### R-FIN3 — P1 — a regra arquivaria a skill que o Gate 2 manda invocar em toda sessão

Das 3 que a regra elege, `ceo-orchestration` é a skill nomeada em
`<ROOT>/CLAUDE.md:26` — «**Invoke the `ceo-orchestration` skill**», passo 4 do
Gate 2, MANDATORY em toda sessão. As outras duas são invocadas por comando:
`<ROOT>/.claude/commands/architect.md` e `<ROOT>/.claude/commands/terse.md`.
Nenhuma das três é «não usada»; as três são usadas por um canal que o
instrumento não observa.

A causa é mecânica e verificável: `skill-health.py:363-367` conta **apenas**
`action == "agent_spawn"` com campo `skill`. O censo de ações da família
inteira (133.377 eventos) devolve **zero** ações cujo nome contenha `skill` —
não existe evento de uso de skill pelo assento nem por slash-command. Logo
«0 invocações» significa «nunca foi passada a um subagente nomeado», que é uma
proposição bem mais estreita do que a que a regra usa para arquivar.

Isso é o defeito de FinOps clássico: otimizar sobre a única linha que o
medidor enxerga. O conjunto de falsos positivos da regra não é aleatório — ele
é exatamente o conjunto das skills de USO DO ASSENTO, que é onde mora o
trabalho de governança do repo.

**Mitigação (uma das duas, pré-registrada):** (a) emitir um evento de invocação
no canal do assento/comando antes de qualquer poda — sem isso a perna de
telemetria é inobservável e deve sair da regra; ou (b) trocar a perna por uma
que o instrumento consegue responder — «0 `agent_spawn` E ausente do SKILL MAP
E ausente de `.claude/commands/` E não citada em `CLAUDE.md`/`team.md`» — e
declarar que o critério é de REFERÊNCIA ESTÁTICA, não de uso. Em ambos os
casos o AC do P2 ganha um controle positivo NEGATIVO: a regra rodada contra
`ceo-orchestration` tem de devolver «manter», ou o instrumento está errado.

### R-FIN4 — P2 — o `external_wait` de calendário está refutado no HEAD (e o baseline 0,434 envelheceu)

O aviso das linhas 147-161 diz que N ≥ 30 é «INEXECUTÁVEL sob demanda»,
que o `/ceo-boot` reporta «0 general-purpose, 0 test-pollution», e conclui que
o item é «um gate que o CALENDÁRIO abre». Medido agora sobre a mesma família:

| grandeza (família inteira, 15,8 d) | valor |
|---|---:|
| eventos `agent_spawn` | **102** |
| com `skill` nomeada | 74 |
| `skill` ausente/`unknown` | 28 |
| **unknown-ratio** | **0,275** |
| skills distintas nomeadas | 11 |

O N ≥ 100 do §1.1 (linha 36) e o N ≥ 30 do §3.1 (linha 145) são ambos
satisfeitos por **16 dias** de uso normal — não por 90. O gate de calendário
custa ao plano ~2,5 meses de espera por uma condição que já está satisfeita.

O corolário é um risco de leitura, não só de agenda: a semente cita
**0,434** (linhas 22-23, história TODA, família antiga) e a meta é < 0,10. O
valor de hoje é **0,275** sem nenhuma intervenção. Se a Fase 1 for medida
contra 0,434, ela vai declarar uma queda de 37 % que ocorreu ANTES de o
mecanismo existir. O baseline tem de ser re-medido na família nova, no mesmo
instrumento e na mesma janela do pós-teste, ou a Fase 1 não é falsificável.

**Mitigação:** trocar `external_wait` por «baseline re-medido na família
pós-2026-08-21, com N e profundidade publicados», e pré-registrar que o
comparador da Fase 1 é ESSE baseline, não o 0,434 da semente.

### R-FIN5 — P2 — o envelope de custo não tem unidade, fonte nem dispersão — e é menor que o piso de boot

`budget_tokens: 150-300k` para `budget_sessions: 2-4` (linhas 10-11) = **50-75 k
tokens por sessão**, sem dizer se são brutos ou descontado cache read, sem
`budget_usd_estimate`, sem `tier_mix_estimate` e sem citar o instrumento que
produziu o número («firmado S302e» é uma data, não uma fonte).

O próprio repo mediu o piso: `F ≈ 97.292` tokens de re-pagamento de gate-boot
na fronteira de uma compactação real, com **spread de 51,7 % da média em n=41**
(`CLAUDE.md` §5, instrumento rastreado em `.claude/plans/PLAN-179/w0/gateboot_repay.py`).
**O orçamento por sessão do plano é menor que o custo fixo de BOOTAR a sessão**,
antes de qualquer trabalho — e o plano tem waves de migração (P3: 116 arquivos)
que são as mais caras do repo em contexto.

Há instrumento no HEAD para consertar isso barato:
`<ROOT>/.claude/scripts/ceo-cost-transcripts.py` deriva tokens e USD por sessão
a partir de `message.usage` dos transcripts, com `--since-at` para janela
reprodutível. Uma execução responde a pergunta.

**Mitigação:** re-declarar o envelope com unidade explícita (bruto e faturável),
`budget_usd_estimate`, `tier_mix_estimate` e a linha de comando que o derivou.
Um plano cujo AC-mestre é «contagem derivada, nunca à mão» não pode ter o
próprio orçamento digitado de memória.

### R-FIN6 — P2 — existe rota mais barata para a MESMA evidência, e o plano confunde dois N distintos

O §3.1 fecha exigindo «re-medir com N ≥ 30 antes de decidir (b)» (linha 145) e o
aviso seguinte transforma isso em espera de calendário. Mas a medição do gap de
idioma **não precisa de spawns**: ela foi feita OFFLINE por
`<ROOT>/.claude/plans/PLAN-175/p1/probe-retrieval-language-gap.py`, N=8 pares
EN/PT com ground truth derivado à mão da ROUTING TABLE. Escalar essa sonda para
N ≥ 30 é gerar 22 pares de consulta e rodar o script — minutos, custo local,
zero espera. O índice sequer precisa ser reconstruído: ele existe nesta máquina
(`<PK>/skill-index.sqlite`, 1.306.624 bytes, `2026-08-22`).

O plano trata dois N como se fossem um: o N do RECALL (offline, barato,
disponível hoje) e o N do UNKNOWN-RATIO (precisa de spawns reais). Só o
segundo é sensível ao tempo — e mesmo ele já está satisfeito (R-FIN4).

**Mitigação:** separar os dois no texto, e mover a decisão (b) do gap de idioma
para ANTES da Fase 1 — porque, pelo próprio §3.1 (linhas 131-140), ligar o
tf-idf numa sessão PT é uma **regressão medida** (2/8 contra 4/8 do fallback).
Ligar primeiro e decidir depois é pagar para piorar.

### R-FIN7 — P2 — o índice não tem invalidação, então o P1 e o P2/P3 brigam

O §3.1 achado 1 (linhas 101-113) afirma que o índice «nunca existiu» e que o
censo `grep -rln skill-index-build` sobre `.claude/hooks/`, `.github/workflows/`
e `scripts/` devolve «apenas o próprio build, o retrieve e os testes». **A
LETRA do censo está desatualizada no HEAD**: `<ROOT>/.claude/hooks/_lib/frontmatter.py:22`
e `<ROOT>/.claude/scripts/env-inventory.json:2776` também casam. Nenhum dos
dois é rota de bootstrap (o primeiro é docstring, o segundo é inventário), então
a CONCLUSÃO sobrevive — mas o número citado como evidência não reproduz, e um
leitor que rodar o censo verá 6 arquivos onde o plano diz 3.

O que o plano NÃO vê é a consequência de ordenação: o índice existe, está
congelado em `2026-08-22`, e continua sem rota de rebuild. Se o P1 ligar a
sugestão e o P2 arquivar skills e o P3 mover 116 domains, **o sugeridor passa a
recomendar skills que não existem mais** — e o custo disso é pago em spawns
mal roteados, exatamente a métrica que o plano quer melhorar.

**Mitigação:** a rota de bootstrap do P1 tem de ser de (re)build com
invalidação — gatilho no mesmo evento que muda `.claude/skills/` — e o AC do
P2/P3 ganha uma perna: «após a poda, `skill-retrieve` não devolve nenhum slug
ausente do disco», com controle positivo (arquivar 1 skill ⇒ ela some do top-k).

### R-FIN8 — P2 — o P3 não é «tornar opt-in» (já é), e a dependência nomeada não está entregue

`<ROOT>/scripts/_framework_manifest_set.sh:185-194` já emite
`.claude/skills/domains/$_fms_part` **por parte de perfil** — domains só
chegam ao adopter se o perfil os pedir. O P3, portanto, não introduz opt-in; ele
REMOVE 116 arquivos da árvore, o que é uma mudança de superfície de ownership
(o `_ownership_verdict()`), de rotas de entrega (`scripts/delivery-routes.tsv`) e
das contagens exatas — três lugares onde este repo já pagou vermelho de main
por 5 sessões (CLAUDE.md §5, defeitos D1-D4).

E a dependência declarada não existe ainda: `PLAN-171` está
`status: executing` (`executing_at: 2026-09-05`) com a W0 no **lote 2 de 6**
(commits `14892ab`, `1e2f657`); a W1c é uma wave descrita em prosa
(`PLAN-171-*.md:143-145, 188-190`), sem entrega. O `external_wait` do PLAN-175
(linha 13) está correto ao apontá-la — o risco é a tentação de abrir o P3 junto
com o P1 «porque o P1 é livre».

**Mitigação:** declarar no plano que P1/P2 e P3 são pacotes SEPARADOS com gates
distintos, e que o P3 não abre antes do contrato da W1c estar escrito e
landado. Sob o modelo de operação v2 (≤ 400 linhas / ≤ 8 paths), o P3 é
inelegível como pacote único de qualquer forma: são 116 arquivos.

### R-FIN9 — P3 — o AC do P5 verifica o estado de HOJE, não a mudança

O AC do P5 (linhas 84-86) pede «`check-claude-md-claims` verde com tolerance=0».
Verificado: `<ROOT>/.claude/scripts/check-claude-md-claims.py:77` já tem
`tolerance: int = 0` como default e `:146` o passa explicitamente; e
`<ROOT>/.claude/scripts/local/verify-counts.sh:31-34` já trata skills como
`exact (166/42/8/116)`. **Esse AC está verde antes da mudança** — ele não pode
ir vermelho pela ausência da derivação, só por um número errado.

O risco real é o outro: o casamento é por lista de regex de PROSA
(`verify-counts.sh:584-598` — `(\d+) reusable skills`, `(\d+) arquivos de skill`,
etc.). Uma superfície reescrita para «N core + M frontend + packs opt-in» deixa
de casar qualquer padrão e passa a **não ser vigiada** — verde por ausência.
É a classe já registrada («mover artefato para fora do gate cria falso verde»).

**Mitigação:** o AC do P5 nomeia as superfícies e exige que o número de sítios
casados NÃO caia (`--json` do `verify-counts` publica a contagem), com controle
positivo: plantar um número errado em cada superfície nova e ver vermelho.

### R-FIN10 — P3 — o P4 delega a execução mas não nomeia o ponteiro

O P4 (linhas 50-54) manda «apontar check-model-deprecations do nightly para
`.claude/skills/`» e delega a EXECUÇÃO ao W-IM do PLAN-172. Verificado: o script
já resolve raízes por precedência `argv > CEO_DEPRECATION_SCAN_ROOTS > repo`
(`<ROOT>/.claude/scripts/check-model-deprecations.py:158, 330`), então o trabalho
é uma linha de configuração no nightly. Mas nem o PLAN-175 nem o
`PLAN-172-honest-speed-e0b-e5-e6.md` nomeiam QUEM edita QUAL arquivo — e a regra
deste repo é que dono único significa path único.

**Mitigação:** citar no P4 o arquivo do nightly e a variável, para que o W-IM
tenha um alvo em vez de uma intenção.

## Must-fix (blocking)

1. **Consertar a janela antes de citar a regra** (R-FIN1): a regra de poda cita
   o comando exato (`--since all --include-rotated`), o AC publica a
   profundidade real do corpus (hoje 15,8 d), e «≥ 90 d» deixa de ser um
   limiar que a migração de 2026-08-21 tornou insatisfazível.
2. **Reconciliar 42 → ~25 com o que a regra devolve** (R-FIN2): a regra
   determinística entrega 3 candidatas, não 17. Ou o alvo vira derivado, ou a
   consolidação de sobreposições vira um passo com critério próprio — mas a
   promessa e a regra não podem continuar se contradizendo no mesmo documento.
3. **Fechar o buraco de canal do instrumento** (R-FIN3): a regra, como escrita,
   arquiva a skill que o Gate 2 do `CLAUDE.md` manda invocar. Ou emitir evento
   de invocação no assento/comando, ou trocar a perna de telemetria por uma de
   referência estática — com controle positivo exigindo «manter» para
   `ceo-orchestration`.

## Nice-to-have (advisory)

1. Re-medir o baseline do unknown-ratio na família nova (0,275 medido) e
   pré-registrar que a Fase 1 compara contra ELE, não contra o 0,434 da semente
   (R-FIN4). Custo: uma execução.
2. Re-declarar o envelope com unidade, USD e `tier_mix_estimate` derivados de
   `ceo-cost-transcripts.py` (R-FIN5).
3. Escalar a sonda de idioma para N ≥ 30 offline e decidir (b) ANTES de ligar a
   sugestão, porque em sessão PT ligar é regressão medida (R-FIN6).
4. Corrigir o número do censo do §3.1 (6 arquivos casam hoje, não 3) ou trocá-lo
   por «nenhum é rota de bootstrap», que é a afirmação que sobrevive (R-FIN7).
5. Nomear no P4 o arquivo do nightly e a variável de raízes (R-FIN10).

## Unseen by the original plan

1. **A poda é uma decisão de ROTEAMENTO, e o roteador não tem invalidação.** O
   plano trata a poda como higiene de catálogo; do ponto de vista de FinOps ela
   muda o espaço de busca de um ranker cujo índice está congelado em
   `2026-08-22` e não tem gatilho de rebuild. Poda sem invalidação não economiza
   contexto — ela cria sugestões para artefatos ausentes.
2. **O instrumento de telemetria mede o canal MINORITÁRIO.** 102 `agent_spawn`
   em 15,8 dias contra uma sessão de assento que invoca skills continuamente e
   não emite nada. Qualquer conclusão de «uso» derivada desse log descreve o
   fan-out, não o trabalho.
3. **A migração de tamper-evidence tem custo de OBSERVABILIDADE que nenhum plano
   contabilizou.** A W1 do PLAN-182 comprou atribuição correta e pagou com o
   reset de toda série histórica por projeto. Todo plano que declara janela
   ≥ 30 d sobre o audit log herda esse débito, e o PLAN-175 é o primeiro a
   tropeçar nele. Vale uma linha no `CLAUDE.md` §5.
4. **O incentivo estrutural que o P5 quer remover é real e mensurável.** As
   contagens são `exact` em `verify-counts.sh` e `tolerance=0` no claims-checker:
   podar UMA skill hoje exige tocar todas as superfícies de prosa. O P5 é, em
   custo de cerimônia, o passo de MAIOR retorno do plano — e está listado por
   último.

## What I would NOT change

1. **A ordem «descoberta antes de poda».** Está certa e o §3.1 a reforça: podar
   com um roteador degradado destrói informação que não volta.
2. **Arquivar em vez de deletar, com `archive/` restaurável testado no mesmo
   PR** (linhas 80-82). É o rollback certo e é barato.
3. **Dono único para o sweep de atualidade** (P4, «sem rota dupla»). A recusa a
   duplicar execução entre planos é a decisão que evita o próximo D1-D4.
4. **A honestidade do §3.1.** Um plano que publica que o próprio mecanismo
   estava morto, e que ligá-lo PIORA o caminho real de uso (PT: 2/8 contra 4/8),
   é o motivo de esta crítica poder ser escrita com números. Mantenha o
   parágrafo «Honestidade da amostra» ao pé da letra.
5. **A recusa a fechar o P1 no baseline** (linhas 76-78: re-medição aos 30 d E
   decisão de Fase 2 APLICADA). É a forma certa de um AC de telemetria: ele
   fecha no efeito, não na instalação.
