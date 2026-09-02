# PLAN-186 W1 — `model:` explícito nos `agent()` dos 4 workflows canônicos

**Status: STUDY (S339).** Não aplicado à árvore viva. Insumo do `/debate` e de
uma cerimônia futura. Fonte: `docs/research/orchestrator-operating-model-S339.md`
§4.1 (diagnóstico) + §6.1 (matriz papel×modelo). Derivador: `apply-w1-explicit-model.py`
(mesmo diretório). Evidência: `EVIDENCE-S339.md`.

---

## 1. [DÚVIDA] — a contagem "17 chamadas" não reconcilia com o código

O prompt desta tarefa (ecoando §4.1 do estudo: *"Nenhuma das 17 chamadas `agent()`
passa `model:`"*) cita 17 sítios, quebrados como audit-fanout.js=5, nightly-hygiene.js=4,
council-audit.js=4, eval-baseline-n20.js=4.

Grep + leitura direta dos 4 arquivos canônicos em HEAD `8efe09b` encontra **10**
sítios textuais `agent(assertDispatchable(...))` — não 17: audit-fanout.js=3
(finder-loop, refuter-loop, synth), nightly-hygiene.js=2 (dim-loop, synth),
council-audit.js=3 (lane-loop, verify, reduce), eval-baseline-n20.js=2 (eval-loop,
reconcile). Comando de verificação (reproduzível):

```
grep -c "agent(assertDispatchable" .claude/workflows/{audit-fanout,nightly-hygiene,council-audit,eval-baseline-n20}.js
# => 3 2 3 2  (soma 10)
```

**Hipótese mais provável para o gap 17→10:** o "17" do relatório conta *dispatches
em runtime* somados através de pelo menos um loop (ex.: `audit-fanout.js` sozinho
tem `DIMENSIONS.length=8` finders + até 8 refuters + 1 synth = até 17 chamadas
*NAQUELE ARQUIVO* na pior hipótese), não *sítios de texto*. Se essa hipótese for
certa, a citação do relatório mediu profundidade errada (chamadas-em-execução) para
uma frase sobre `model:` — que é uma propriedade do **sítio de texto**, não da
execução: um `.map()`/loop com UM `agent(...)` textual aplica o MESMO `model:`
a todas as N execuções que dele derivam. Isso não muda o remédio (ainda são
10 edições de texto), mas muda a contagem citada.

**Este derivador usa os 10 sítios VERIFICADOS, não os 17 citados.** Recomendação:
o Owner ou um refutador deveria re-derivar a fonte exata do "17" no relatório 05
(`docs/research/s339-orchestrator-study/05-finops-routing.md`) antes de uma
cerimônia real — se a discrepância for só de framing (dispatch-count vs site-count),
nenhuma ação corretiva é necessária além de citar os dois números explicitamente;
se houver um 11º+ sítio real que este grep não capturou (ex.: um `agent(` sem
`assertDispatchable` — não há nenhum caso hoje, confirmado por
`grep -c "agent(" | grep -v assertDispatchable` nos 4 arquivos = 0 sítios de
dispatch reais fora de comentários), a lista de SITES abaixo precisa crescer.

---

## 2. Classificação dos 10 sítios (file:line | label | papel | modelo | justificativa)

Papéis herdam a matriz §6.1 do estudo: finder/pesquisa/leitura/censo →
`claude-sonnet-5`; refutador adversarial → `claude-opus-5`; síntese/REDUCE →
`claude-fable-5-1`; grader/eval mecânico → `claude-sonnet-5`.

| # | arquivo:linha | label pattern | papel | modelo | justificativa (1 linha) |
|---|---|---|---|---|---|
| 1 | `audit-fanout.js:205` | `find:${d.key}` | finder/pesquisa | `claude-sonnet-5` | 8 finders read-only por dimensão — derivação mecânica e verificável (§6.1 linha 8) |
| 2 | `audit-fanout.js:315` | `refute:${dim}` | refutador adversarial | `claude-opus-5` | REDUCE = re-verificação adversarial de claims dos finders (§6.1 linha 4) |
| 3 | `audit-fanout.js:~384` | `synthesize` | síntese/REDUCE | `claude-fable-5-1` | agrega confirmed/refuted/unverifiable num veredito único — erro aqui contamina tudo (§6.1 linha 5) |
| 4 | `nightly-hygiene.js:276` | `hygiene:${d.key}` | finder/pesquisa/censo | `claude-sonnet-5` | 9 agentes de censo read-only (staleness, verify-counts, CI, etc.) |
| 5 | `nightly-hygiene.js:~350` | `hygiene:synthesize` | síntese/REDUCE | `claude-fable-5-1` | funde os 9 resultados de dimensão em UM relatório |
| 6 | `council-audit.js:477` | `lane:${vendor}` | finder/pesquisa **[DÚVIDA]** | `claude-sonnet-5` | ver nota abaixo — a lane `claude` é revisão in-harness; codex/grok são wrappers de transporte externo |
| 7 | `council-audit.js:610` | `verify` | refutador adversarial | `claude-opus-5` | verificador único, explicitamente "ADVERSARIAL verifier" no prompt |
| 8 | `council-audit.js:~706` | `reduce` | síntese/REDUCE | `claude-fable-5-1` | veredito cross-vendor + superfície de divergência |
| 9 | `eval-baseline-n20.js:387` | `eval:${MODEL}:batch${i+1}` | grader/eval mecânico **[DÚVIDA]** | `claude-sonnet-5` | ver nota abaixo — este `model:` tiera o AGENTE ORQUESTRADOR, não o modelo avaliado |
| 10 | `eval-baseline-n20.js:447` | `eval:${MODEL}:reconcile` | síntese/REDUCE | `claude-fable-5-1` | reconciliador — fecha contagens sobre os 4 batches |

**Contagem por modelo:** `claude-sonnet-5`=4 (#1,4,6,9), `claude-opus-5`=2 (#2,7),
`claude-fable-5-1`=4 (#3,5,8,10).

### Nota [DÚVIDA] item 6 — `lane:${vendor}` (council-audit.js:477)

O mesmo sítio textual dispara para as 3 vendors (`claude`, `codex`, `grok`) via
`REQUESTED_VENDORS.map(...)`. Para a vendor `claude` é literalmente um agente
Claude fazendo auditoria in-harness — papel finder legítimo, `claude-sonnet-5`
é uma escolha defensável. Para `codex`/`grok` o agente Claude despachado por
ESTE sítio não audita nada ele mesmo: seu prompt (`externalLaneOrchestration`)
o instrui a invocar a CLI externa (`codex exec`/`grok -p`) como transporte
redigido (ADR-114) e devolver o resultado — é orquestração/parsing mecânico,
não pesquisa. Um `model:` único aplicado ao sítio inteiro não pode diferenciar
por vendor sem reescrever o call site como dois branches com dois `agent()`
distintos (fora do escopo desta W1 — um derivador anchor-exact que bifurcasse
o call site deixaria de ser "uma edição por sítio" e viraria uma refatoração).
Mantido `claude-sonnet-5` para as 3 vendors por ser a opção mecanicamente mais
barata que ainda cobre com folga o caso mais pesado (a lane `claude`); um
refutador pode discordar e pedir Haiku para os 2 branches de transporte puro.

### Nota [DÚVIDA] item 9 — `eval:${MODEL}:batch${i+1}` (eval-baseline-n20.js:387)

`docs/research/s339-orchestrator-study/03-claude-code-substrate.md` §3 e o
próprio `eval-baseline-n20.js:3,284,547` documentam que o `MODEL` avaliado
roda via subprocesso `claude -p --model <MODEL>` — desenho deliberado (isolamento
de config + billing ground-truth), não uma limitação de `opts.model` do Workflow
(essa citação de "INERTE" nos 2 sítios legados está desatualizada, per §3 do
estudo — ADR-144 emenda). Logo `opts.model` **deste** `agent()` tiera só o
agente-wrapper que dispara o subprocesso e faz o parsing do batch — nunca o
modelo sob avaliação. Classificar esse wrapper como "grader/eval mecânico"
(linha 8 da matriz §6.1) e apontar para `claude-sonnet-5` é a leitura mais
barata e consistente com a doutrina "derivação mecânica → Sonnet 5"; a
alternativa seria deixar OMITIDO (herda o assento) já que o custo do wrapper é
marginal frente ao custo dos 4 batches × subprocessos reais. Ambas são
defensáveis — marcado DÚVIDA para o refutador decidir.

---

## 3. Como o LAND futuro provaria `HEAD + derivador == patch`

Molde: `OWNER-S338-FABLE51-LAND.sh` V3 (mesma família da cerimônia `wave-fable51`,
`f0e98de`). Adaptação para esta W1:

1. `git worktree add --detach <scratch> <ANCHOR_SHA>` — `<ANCHOR_SHA>` é o commit
   que o SIGN declara como base (hoje `8efe09b`, mas a cerimônia real re-resolve
   no momento do LAND, não usa este valor fixo).
2. `python3 .claude/plans/PLAN-186/w1/apply-w1-explicit-model.py --check --root <scratch>`
   — deve dar `rc 0` (pré-condição: os 10 sítios existem, nenhum já tem `model:`).
3. `python3 .claude/plans/PLAN-186/w1/apply-w1-explicit-model.py --apply --root <scratch>`
   — deve dar `rc 0` e imprimir `10 edicoes em 4 arquivos`.
4. `git -C <scratch> diff > /tmp/derived.patch` — o diff PRODUZIDO agora pelo
   derivador sobre o `HEAD` real do momento do LAND.
5. `sha256sum /tmp/derived.patch` comparado contra o sha256 do patch assinado
   pelo Owner no sentinel (`EVIDENCE-S339.md` tem o sha256 do patch candidato
   desta sessão: **ver arquivo** — mas ele NÃO é o patch a assinar; ele é só a
   prova de que o derivador funciona hoje. O sentinel real re-executa o
   derivador contra o `ANCHOR_SHA` do dia do LAND e assina O QUE SAIR daquela
   execução, nunca um patch congelado à mão — lição
   `feedback-frozen-evidence-needs-explicit-parameters.md`).
6. `V4`-equivalente: `git -C <scratch> diff --stat` deve bater exatamente com
   `touched = {audit-fanout.js, council-audit.js, eval-baseline-n20.js, nightly-hygiene.js}`
   (escopo do plano) — `touched − scope = ∅`.
7. Gate adicional específico a scripts de workflow: `node --check` nos 4
   arquivos pós-`--apply` (sintaxe), MAIS uma re-execução real (não simulada)
   de pelo menos 1 workflow barato (`nightly-hygiene` é o candidato mais barato,
   2 sítios) com o patch aplicado, para confirmar que `opts.model` é de fato
   HONRADO na versão do substrato do dia do LAND — per §3 do estudo, a doutrina
   pede **verificar via o campo `model` da resposta, nunca assumir** (ADR-144:
   *"no forward guarantee"*). Sem essa prova ao vivo, o LAND estaria assinando
   uma mudança de texto sem prova de que ela FAZ algo no substrato corrente.

## 4. Critério de morte

**Dois P1 reais consecutivos que o refutador (Codex/pair-rail) não pegue** na
revisão deste patch (ou de uma extensão dele) ⇒ reverter a política de builder
desta classe de tarefa (derivação anchor-exact mecânica) de volta para
`claude-opus-5`, e reabrir a pergunta de se `claude-sonnet-5` é forte o
suficiente para derivadores anchor-exact sobre arquivos `.js` de workflow —
que têm uma gramática de validação pré-despacho (`assertDispatchable`) mais
intrincada que a maioria dos alvos Python já cobertos por esse padrão
(precedente: `wave-fable51`, 30 paths, script único, 5 rodadas de rail, 7
achados reais — nenhum P1 que o rail não pegasse). Este patch em si (S339) NÃO
passou por pair-rail ainda — é material cru para o `/debate`, não uma
cerimônia; o critério acima só se aplica a partir do primeiro rail real.

**Atualização (rodada de revisão Codex V2):** o instrumento (`--check`) TEVE
um defeito real pego pelo refutador — ver `EVIDENCE-S339.md` §10. Classificado
como P2 (falso-verde do gate de verificação, não do PATCH que ele verifica —
`--apply` já recusava os dois cenários independentemente), curado na mesma
rodada com reprodução vermelho→verde em sombra descartável. Não conta como um
P1 para o critério de morte acima, mas é o primeiro dado real de que este
sítio (o próprio derivador, não só o patch alvo) também precisa de revisão
adversarial — reforça a recomendação §3.7 de não assinar cerimônia real sem
pelo menos uma rodada de rail sobre o SCRIPT, não só sobre o diff que ele
produz.

## 5. Efeito esperado no bloco COMMON / validador ADR-191

Confirmado por leitura direta: `assertDispatchable` (definido em cada um dos
4 arquivos, ex. `audit-fanout.js:76-138`) valida SOMENTE 3 coisas — contagem de
bullets em `PROMPT DEFENSE` (≥6), presença de uma linha `CAN edit` parseável em
`FILE ASSIGNMENT`, e a presença do `RULES_MARKER` do arquivo. **Não inspeciona
`opts.model` nem qualquer coisa fora do texto do PROMPT** — `model` vive no
segundo argumento de `agent(prompt, opts)`, um objeto JS totalmente fora do
alcance de um validador que só enxerga a STRING do prompt. Logo esta mudança
é invisível ao validador hoje, em ambas as direções: um `model:` ausente,
presente, ou até um valor inválido (typo num model id) NUNCA dispara
`assertDispatchable` — passaria despercebido até o `agent()` real falhar (ou
pior, silenciosamente cair no fallback do dispatcher).

**Deveria checar?** Recomendação: SIM, mas como um gate SEPARADO, não dentro
de `assertDispatchable` (que é deliberadamente "reduced grammar" sobre o
PROMPT — ADR-191, comentário de linha 73-75 do próprio arquivo). Um checador
de nível de arquivo (`node --check` já cobre sintaxe; falta um linter simples
que confirme, por sítio conhecido, que `model` é uma das 3 strings válidas do
ADR-149 working set: `claude-sonnet-5`, `claude-opus-5`, `claude-fable-5-1`,
mais o fallback documentado) evitaria a classe "typo de model id silenciosamente
ignorado" — mas isso é uma FOLLOW-UP, não parte do W1 conforme escopo
autorizado (ver `## FILE ASSIGNMENT` do spawn: só os 3 arquivos deste diretório).
Nomear como `PLAN-186-FOLLOWUP-model-id-lint.md` se o Owner aprovar a rota.

---

## 6. Efeito colateral verificado: nenhum

O `--check` sobre a árvore VIVA (nunca tocada por esta sessão) deu `rc 0` sem
qualquer escrita — ver `EVIDENCE-S339.md` §1. Todo o `--apply` rodou exclusivamente
dentro do worktree descartável (`git worktree add --detach`), removido ao final
desta tarefa.

## 7. Regra de exclusividade OLD/NEW no `--check` (Codex P2, ver EVIDENCE §10)

Por sítio, `--check` exige EXATAMENTE um de dois estados mutuamente exclusivos
— `(OLD=1, NEW=0)` pendente XOR `(OLD=0, NEW=1)` já aplicado — e trata qualquer
outra combinação (ambos zero, ambos presentes, ou qualquer contagem >1) como
`CHECK FAILED` nomeado por sítio; a versão anterior aceitava `NEW≥1` sem checar
duplicata e ignorava `NEW` inteiramente quando `OLD==1`, produzindo `CHECK OK`
sobre uma árvore com drift ou aplicação parcial.
