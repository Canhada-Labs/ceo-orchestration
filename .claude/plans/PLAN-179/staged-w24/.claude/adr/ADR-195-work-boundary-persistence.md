---
adr_id: ADR-195
title: Persistência em fronteira de trabalho — ledger de plano com obrigação derivada, e por que ele NÃO é derivado do audit log
status: PROPOSED
proposed_at: 2026-08-18
proposed_by: CEO (S313 — PLAN-179 W2/US9; staged em `.claude/plans/PLAN-179/staged-w24/`)
decided_by: Owner (PENDENTE — assinatura GPG da cerimônia W1+W2 do PLAN-179; ordem obrigatória: ADR-153-AMEND-1 primeiro, este depois — emenda 8.2/C8)
risk_tier: A
debate_required: true
debate: ".claude/plans/PLAN-179/debate/round-1/consensus.md (round 1, PROCEED, 3× ADJUST, 0 REJECT). A matriz do §2 existe por exigência da emenda 8.5 (achado A-U2); os critérios de morte do §3.2 vêm de A-U1/A-U3/A-U4."
numbering_note: "O §7 do PLAN-179 reservava `ADR-193` para esta doutrina. O número foi consumido pelo break-glass do PLAN-169 (pack W3, S312). Alocado 195 no momento da escrita: o número 194 foi por sua vez consumido pelo ADR de resolução de rota de entrega do PLAN-183 (slug `delivery-route-resolution`, landado em 6304f66), e 195 era o próximo livre medido na S328. Conforme a própria emenda 8.2 (\"números de ADR alocados NO MOMENTO da escrita; nada de reservar no draft\")."
related_plans: [PLAN-179, PLAN-175, PLAN-135, PLAN-169]
related_adrs: [ADR-153, ADR-027, ADR-034, ADR-055, ADR-191]
---

# ADR-195 — Persistência em fronteira de trabalho

## §1 Contexto — a falha está MEDIDA, não argumentada

Três medições, todas re-verificadas contra o disco nesta sessão (S313,
2026-08-18). Nenhuma linha deste ADR depende de retórica.

**(1) O ADR-153 disparou no evento para o qual foi construído e entregou
nada.** O autocompact real de 2026-08-16T09:34Z emitiu os dois eventos
previstos. Verbatim do log rotacionado
`~/.claude/projects/ceo-orchestration/audit-log-2026-08-8.jsonl:11199`
e `:11203`:

```
action=compaction_continuity_snapshot  ts=2026-08-16T09:34:22Z
    trigger=auto  plan_id=unknown  chain_length=11179
    snapshot_outcome=scratchpad_unavailable
action=compaction_context_reinjected   ts=2026-08-16T09:36:29Z
    plan_id=unknown  snapshot_found=false  snapshot_age_s=0
    pointer_count=1
```

O snapshot nunca foi escrito; a reinjeção devolveu 1 ponteiro (o
lembrete genérico de Gate-1) e zero estado de governança. O
*fires-proof* que o ADR-153 declarava `PENDING-LIVE` agora existe e é
**negativo**: os eventos disparam, o mecanismo não entrega.

**(2) A causa-raiz é mais dura do que o PLAN-179 §1 E2 supunha —
`resolve_plan_id` é INSATISFAZÍVEL por construção, não apenas
anti-correlacionada.** `scratchpad_lib.resolve_plan_id`
(`.claude/hooks/_lib/scratchpad_lib.py:103`) só aceita eventos
`plan_transition` cujo `session_id` case com o da sessão corrente. Censo
de hoje sobre o log vivo — `~/.claude/projects/ceo-orchestration/audit-log.jsonl`,
8.486 linhas / 21 ações distintas na passada de 2026-08-18T15:2xZ; o
arquivo é append-only e cresce durante a leitura, então o N é o da
passada, não uma constante:

| Ação | eventos c/ `session_id` | eventos c/ `session_id` VAZIO |
|---|---:|---:|
| `tool_call_lifecycle_recorded` | 3.563 | 0 |
| `prompt_submitted` | 21 | 0 |
| `session_stop` | 11 | 0 |
| **`plan_transition`** | **0** | **10** |

Os 10 `plan_transition` do log vivo carregam `session_id: ""`. A causa é
o único caller de produção: `.claude/hooks/check_plan_edit.py:171-178`
chama `emit_plan_transition(...)` passando `plan_id`, `from_status`,
`to_status`, `file_path`, `editor_tool` e `project` — e **omite
`session_id`**, cujo default é `""` (`.claude/hooks/_lib/audit_emit.py:2939`).
`_write_event` não injeta o campo (`audit_emit.py:2643-2688`). Logo o
filtro `event_sid != sid` descarta **100%** dos eventos para **qualquer**
sessão, inclusive uma que acabe de transicionar um plano. O censo da S309
("2 eventos em 12.515 linhas, ambos de outra sessão") subdiagnosticou: o
filtro os rejeitaria mesmo se a sessão casasse.

Consequência direta e citável: `check_precompact_continuity.py:302-306`
devolve `scratchpad_unavailable` sempre que `plan_id == "unknown"` — que
é sempre. **O scratchpad plan-scoped é inalcançável hoje.**

**(3) Nada no framework ESCREVE memória.** `.claude/hooks/SessionEnd.py:77-95`
(`_memory_dir_state`) apenas executa `os.access(memory_dir, os.W_OK)` e
`(memory_dir / "MEMORY.md").is_file()`, e propaga dois booleanos para o
evento (`SessionEnd.py:117-118`). Verifica gravabilidade; não grava. A
persistência é 100% discricionária do modelo, num closeout que uma sessão
morta por contexto nunca alcança.

**A tese deste ADR nasce de (3), não de (1).** A memória não drifta por
bug: drifta porque a escrita é discricionária e acontece num evento
terminal. O ledger só vale a pena se atacar exatamente isso.

---

## §2 Matriz de decisão (emenda 8.5 — VINCULANTE)

### 2.1 Opções avaliadas

- **(A) Ledger como superfície NOVA de escrita discricionária** —
  `.claude/plans/PLAN-NNN/LEDGER.md` versionado em git, escrito pelo
  modelo em fronteira de unidade, com hook advisory verificando a
  atualização no mesmo commit.
- **(B) Ledger como PROJEÇÃO do scratchpad do plano** — sem arquivo novo:
  o estado já vive no store (ADR-027/ADR-034) e o "ledger" é uma vista
  renderizada dele sob demanda.
- **(C) Ledger DERIVADO do audit log** — nada é escrito discricionariamente;
  o ledger é reconstruído mecanicamente dos eventos HMAC-encadeados. Elimina
  a escrita discricionária, que é a causa de (3).
- **(D) Nulo — status quo** (controle obrigatório: manter memória nativa +
  closeout manual).

### 2.2 Tabela

| | **(A) superfície nova** | **(B) projeção do scratchpad** | **(C) derivado do audit log** | **(D) nulo** |
|---|---|---|---|---|
| **Exige escrita discricionária?** | **Sim** — é o defeito, assumido de olhos abertos | **Sim** — só muda ONDE se escreve, não SE se escreve | **Não** — zero discrição | Sim (memória + closeout) |
| **Sobrevive a sessão morta?** | **Sim** — está em git; sobrevive a máquina, clone e ao próprio repo | **Não hoje**: o store é plan-scoped por `resolve_plan_id`, insatisfazível (§1.2); mesmo após a cura da W1 vive em `$HOME`, gitignored, invisível a review e não viaja em `git clone` | **Sim** — o log é append-only e HMAC-encadeado (ADR-055) | **Não** — medido: 3 sessões de curas do PLAN-177 sem memória escrita (PLAN-179 §2) |
| **Custo somado ao piso `F`** (estimativa chars/4 do `context-budget.py`, **não** o tokenizer da Anthropic) | **+~60 tok permanentes** (1 ponteiro no payload de reinjeção) + **≤2k sob demanda** quando o modelo abre o arquivo (teto A-U3) | +~60 tok (mesmo ponteiro); corpo fora do contexto | **+200–600 tok** se o derivado for injetado no boot — e o conteúdo é pobre (§2.3) | **+0 no `F`** — o custo é pago em SESSÕES de arqueologia, não em tokens de piso |
| **Reversibilidade** | *Embedded* — hook + registro em `settings.json` + a W2/US7 passa a apontar para o ledger ⇒ **exige exit strategy escrita (§4.2)** | **Pior**: acopla o ledger ao rail do scratchpad que a W1 está curando na MESMA cerimônia; reverter mexe em duas curas simultâneas | Leitor puro = trivial de remover; **mas** torná-lo útil exigiria evento novo em `_KNOWN_ACTIONS` + allowlist + bump de SPEC, e registro de auditoria é append-only (ADR-055) — essa parte é quase irreversível | Trivial (é o estado atual) |
| **COMO FALHA** | Por **omissão**: ninguém escreve — exatamente o E3. Falha secundária pior: entrada ERRADA, que o leitor consome com confiança (A-U4) | **Silenciosamente**: a projeção SUCEDE vazia. Fonte não escrita e fonte ilegível produzem a mesma saída — é o `snapshot_found=false` do §1.1 outra vez | Por **pobreza**: nunca está ausente, logo **parece cobertura**. É a classe "instrumento verde cuja pergunta envelheceu" | Como já falhou: arqueologia de git, redescoberta a cada sessão |
| **Que evidência FALSIFICA a escolha** | Na janela measure-first: omissão > **33%** dos commits em escopo, **ou** > **10%** das entradas cujo verificador nomeado sai ≠ 0 (§3.2) | Uma medição pós-W1 mostrando leitura bem-sucedida do scratchpad ≥ 95% em sessões que MORREM (não em sessões saudáveis) ⇒ B volta a competir, por dispensar arquivo novo | Um censo mostrando ≥ 1 campo de DECISÃO por unidade de trabalho no log. Hoje: **zero** — `tool_call_lifecycle_recorded` carrega `tool_name_enum`, `duration_bucket`, `success` e **nenhum path e nenhum argumento** | Já falsificada por §1.1 e §1.3 |

### 2.3 Por que (C) morre na medição — e o que dela SOBREVIVE

(C) é a opção intelectualmente correta: elimina a escrita discricionária,
que é a causa nomeada em §1.3. Ela morre por uma medição, não por
preferência.

Censo do log vivo (8.486 linhas): **88% das linhas são ruído de
varredura** (`output_scan_finding_suppressed` 3.921 +
`tool_call_lifecycle_recorded` 3.550). E o evento mais informativo do
conjunto, `tool_call_lifecycle_recorded`, tem exatamente estes campos
semânticos: `tool_name_enum`, `duration_bucket`, `success`, `orphan`.
**Não há path, não há argumento, não há resultado.**

Um ledger derivado do log de hoje pode dizer *"a sessão X chamou 240
ferramentas, 3 vetos, terminou em `session_stop reason=...`"*. Não pode
dizer *qual arquivo foi editado*, *qual decisão foi tomada*, *qual
bloqueio está aberto*, nem *qual AC foi verificada e por qual comando*.
Ou seja: **não consegue produzir o artefato cuja ausência causou a
falha.** E a razão pela qual não consegue é a própria doutrina de
auditoria deste repo — enums fechados e inteiros, nunca texto livre,
nunca path (CLAUDE.md §4). Escolher (C) seria escolher revogar essa
doutrina; o custo de segurança e o de auditabilidade são maiores que o
benefício.

**O que sobrevive de (C) e é incorporado à decisão:** a parte derivável
deve ser derivada. Concretamente — o *gatilho* da obrigação de escrever
não é discricionário, é mecânico e derivado dos PATHS do commit (emenda
C6). É essa transposição que impede a decisão de ser (A)-por-hábito.

---

## §3 Decisão

**Adotamos (A), com o mecanismo de (C) aplicado à OBRIGAÇÃO em vez de ao
CONTEÚDO.**

1. **Conteúdo discricionário, momento obrigatório.** O corpo do
   `.claude/plans/PLAN-NNN/LEDGER.md` é escrito pelo modelo — só ele tem
   a semântica (decisão, bloqueio, unidade). O *dever* de tê-lo escrito é
   derivado mecanicamente: `check_ledger_checkpoint.py` deriva o escopo
   dos **PATHS do commit** (`.claude/plans/PLAN-NNN/**` ou path listado
   numa AC `[P?][USn][path]`) e **NUNCA** de `resolve_plan_id` — se
   derivasse, a W2 re-herdaria a causa-raiz do §1.2 e nasceria morta pelo
   mesmo motivo que o ADR-153 morreu (emenda C6).
2. **Fronteira de UNIDADE, não morte de sessão.** A escrita acontece no
   momento de pressão máxima, e por isso a entrada precisa ser barata:
   só identificadores verbatim (paths absolutos, SHAs, `PLAN-`/`ADR-`
   ids). Corpo ou excerto de transcript é **proibido** — o repo é público
   (`check-contamination` cobre o path novo).
3. **Entrada errada é pior que entrada ausente.** Cada linha de "AC com
   estado verificado" carrega um **verificador nomeado** (comando +
   exit code esperado). Sem verificador, a entrada é prosa e o leitor a
   consome com confiança injustificada (A-U4).
4. **Advisory primeiro, com janela measure-first.** O hook nasce
   ADVISORY, precedente ADR-191 (`CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED`
   permanece UNSET durante a janela). O flip para enforce é cerimônia
   FUTURA, gated em ≥30 dias **ou** ≥20 sessões, com tabela
   would-block/TP-FP. Commit fora de escopo emite
   `ledger_checkpoint_skipped` com razão em enum fechado — **a omissão
   fica visível**, que é precisamente o que não existe hoje para a
   memória (§1.3).
5. **Teto de tamanho.** ≤2k tokens por `LEDGER.md`, seções antigas
   arquivadas. Sem teto, a W2 soma ao piso `F` o que a W3/PLAN-175
   tentam remover — o conflito é declarado, não escondido (A-U3).

### 3.1 O que esta decisão NÃO é

- **Não** elimina escrita discricionária. Realoca a obrigação. Quem
  quiser zero discrição precisa de (C), e o teto de (C) está medido em
  §2.3.
- **Não** conserta o §1.3. A W2/US8 faz o `SessionEnd` emitir o *delta
  candidato* de memória (contagem + paths, nunca corpo) para ratificação;
  escrever memória continua decisão do modelo/Owner. O hook torna a
  omissão VISÍVEL — não escreve por conta própria. Qualquer claim mais
  forte que isto é falsa.
- **Não** depende do veredito da W0-1 (canal `additionalContext` em
  PostCompact). O ledger é um arquivo em git; é lido por leitura de
  arquivo, não por injeção.
- **Não** conserta o defeito de `session_id` do §1.2. Esse é item da W1
  (ou de um follow-up nomeado); registrá-lo aqui é obrigação de honestidade,
  não escopo desta decisão.

### 3.2 O que me faria REVERTER (critério de morte — com números)

O ledger morre, e morre por REMOÇÃO, se ao fim da janela measure-first
qualquer um destes disparar:

- **M1 — omissão > 33% dos commits em escopo.** Justificativa do número:
  um ledger escrito em menos de dois terços das fronteiras é um ledger em
  que a próxima sessão não pode confiar, e um ledger não-confiável é
  **pior** que nenhum, porque desliga a arqueologia de git sem substituí-la.
- **M2 — > 10% das entradas cujo verificador nomeado sai ≠ 0.** É o
  fracasso do §1.3 com confiança adicionada: checkpoint presente e falso.
- **M3 — custo medido do ledger no piso `F` acima do teto** (≤2k por plano
  + ~60 tok de ponteiro), após a medição de `F` da W0.

Dois números (M1, M2) são **novos** — o plano deixou o limiar como "X%"
(A-U1). Eles são proposta do CEO e precisam de ratificação explícita do
Owner na cerimônia; até lá, tratá-los como não-decididos.

A tabela TP/FP da janela **deve** reportar também a taxa de commits **não
observados** — o Owner commita com `!` fora do hook, e esse universo
censurado declarado é parte do resultado, não uma nota de rodapé
(precedente: medição que não lista seus inputs não sustenta decisão).

**Morte significa REMOÇÃO, não "advisory para sempre".** Manter um hook
advisory que já falhou seu critério é exatamente a dívida que parece
cobertura — a mesma classe das sondas órfãs de `context-budget.py`
(`--compact-decision`/`--summarize-decision`/`--middle-out-decision`, que
não têm consumidor algum no repo).

---

## §4 Reversibilidade por wave (emenda 8.5, 2ª metade)

### 4.1 Classificação

| Wave | Classe | Rota de reversão |
|---|---|---|
| W0 (sonda + medição) | **Trivial** | Sonda é operator/local-only, read-only; apagar o arquivo. O evento `context_pressure_observed` já registrado permanece (append-only) |
| W1 (cura do snapshot) | **Reversível por revert** | Reverter o commit da cerimônia; o enum volta a 3 valores e o SPEC regride de bump |
| W1-b (Constraint Pinning) | **Reversível por revert, com bump de SPEC** | Conjunto fixado é constante de código em `_lib/`; remover a constante + o canal. `pointer_count` muda de semântica ⇒ SPEC bumpa nos dois sentidos |
| **W2 (ledger)** | **EMBEDDED** | **Exige a exit strategy do §4.2** |
| W3 (piso `F`, doutrina, sondas órfãs) | **Doutrina/docs** | Reverter texto; a poda em si é do PLAN-175 |
| W4 (proveniência + write-gate) | **Morre com a W2** | Dependência declarada: `ledger_provenance.py` e o write-gate não têm razão de existir sem ledger |

### 4.2 EXIT STRATEGY da W2 (obrigatória — a W2 é *Embedded*)

A W2 é *Embedded* porque outras coisas passam a depender dela: o hook
entra em `.claude/settings.json`, a W4 é construída em cima, e — o ponto
de embutimento concreto — a **W2/US7 faz o snapshot do `PreCompact`
deixar de ser cópia de estado e virar ÍNDICE que aponta para o ledger**.
Remover o ledger sem desfazer a US7 deixa um snapshot apontando para
nada: a falha do §1.1 restaurada com outra causa.

**Ordem de saída, exatamente:**

1. **Gatilho.** M1, M2 ou M3 do §3.2 dispara ao fim da janela, ou o Owner
   decide encerrar. O disparo é registrado no plano ativo com o número
   medido — nunca "achamos que não pegou".
2. **Desarme imediato (segundos, sem cerimônia).**
   `CEO_LEDGER_CHECKPOINT=0` desliga o hook de fronteira;
   `CEO_SOTA_DISABLE=1` é a precedência mestre que força tudo advisory.
   **Desarme não é remoção** — é a rota de recuperação enquanto a
   cerimônia é montada, e sua ativação segue a doutrina de break-glass do
   ADR-193 (quem, quando, registro, TTL, reversão).
3. **Remoção (cerimônia GPG, um sentinel, nesta ordem).**
   (a) reverter a W2/US7 primeiro — `check_precompact_continuity.py`
   volta a snapshot-de-estado, para que nenhum instante exista com
   índice apontando para ledger inexistente;
   (b) remover o registro do hook em `.claude/settings.json`;
   (c) apagar `.claude/hooks/check_ledger_checkpoint.py` e seus testes;
   (d) apagar `.claude/hooks/_lib/ledger_provenance.py` e o write-gate da
   W4 (dependência declarada em §4.1);
   (e) marcar este ADR `SUPERSEDED` com o número medido que o matou, e
   regenerar as contagens derivadas (§5).
4. **O que é DESCARTADO.** O mecanismo: hook, registro, write-gate, tag de
   proveniência, e o *contrato* segundo o qual o `LEDGER.md` significa
   algo para a máquina. Descartada também a emissão FUTURA dos eventos de
   checkpoint.
5. **O que SOBREVIVE — e é deliberado.**
   - **Os arquivos `LEDGER.md` permanecem em git**, como prosa comum num
     diretório de plano. Remover o mecanismo **nunca** apaga conteúdo
     histórico: são o registro de como o trabalho aconteceu, e nenhum
     hook depende deles depois de (3c).
   - **Os eventos de auditoria já emitidos permanecem.** O log é
     append-only e HMAC-encadeado (ADR-055); apagá-los quebraria a
     cadeia. São a evidência de que o experimento rodou e de por que
     morreu.
   - **A linha de SPEC dos eventos é APOSENTADA, não deletada** — o
     histórico do `SPEC/v1/audit-log.schema.md` é aditivo.
   - **A cura da W1 sobrevive inteira.** O snapshot com escopo de sessão
     não depende do ledger; é uma correção do §1.1/§1.2 que continua
     válida com ou sem W2.
   - **As medições da W0 sobrevivem** (`F`, `T`, taxa de `plan_id=unknown`,
     taxa de omissão). São o resultado do experimento, e o resultado
     negativo é entregável.
6. **Contra-indicação explícita.** Não converter o hook em "advisory
   permanente" para evitar a cerimônia de remoção. Ver §3.2, último
   parágrafo.

---

## §5 Consequências

- **Contagens derivadas se movem, tolerance=0.** Este ADR leva o
  diretório de 194 para 195 ADRs; o `check_ledger_checkpoint.py` move as
  contagens de hooks (hoje 57 em disco / 46 wired / 48 registros de
  evento, CLAUDE.md §1). Regenerar as superfícies derivadas e rodar
  `.claude/scripts/local/verify-counts.sh` no closeout — inclusive as
  superfícies que o verify-counts **não** cobre (ARCHITECTURE, GUIA, FAQ,
  README do npm), onde o drift é silencioso.
- **Uma superfície a mais para manter.** Se ninguém escrever, o ledger
  degrada exatamente como a memória degradou (§1.3). O hook advisory
  torna a omissão visível; isso é mitigação, não garantia — e é por isso
  que o §3.2 tem números e não intenções.
- **Conflito declarado W2 × W3.** A W2 adiciona ao piso `F` (ponteiro
  permanente + leitura sob demanda) o que a W3/PLAN-175 tentam remover. O
  teto de 2k é o que mantém o saldo positivo; sem a medição de `F` da W0
  ele é estimativa.
- **Dogfood assumido.** O `.claude/plans/PLAN-179/LEDGER.md` já está em
  uso nesta sessão (S313) — o instrumento foi usado antes de ratificado, o
  que é deliberado (`context_risk: high`: um plano sobre continuidade
  executado numa sessão que compacta é o seu próprio teste). Registrado
  aqui para que ninguém leia o uso prévio como aprovação prévia.
- **Escopo real da cerimônia** (emenda 8.2/C8): o sentinel cobre TODOS os
  paths tocados — `check_ledger_checkpoint.py` (novo) + seu registro em
  `.claude/settings.json`, `check_precompact_continuity.py` (US7),
  `SessionEnd.py` (US8), `ledger_provenance.py`, `audit_emit.py` e o bump
  de `SPEC/**` — não apenas os dois ADRs. **Dois ADRs, UMA cerimônia**;
  ADR-153-AMEND-1 primeiro (fecha o registro falsificado), este depois.

## §6 Fronteiras honestas (residuais nomeados)

1. **Universo censurado.** O hook não observa commits feitos fora do
   harness (o Owner commita com prefixo `!`). A taxa de commits não
   observados entra na tabela da janela como número, não como ressalva.
2. **`session_id` vazio em `plan_transition` é defeito ABERTO.** §1.2 o
   mede e o localiza (`check_plan_edit.py:171-178`); esta decisão não o
   conserta e **não depende** dele — é o motivo de o gatilho derivar de
   PATHS. Enquanto não for curado, qualquer código novo que chame
   `resolve_plan_id` nasce inoperante.
3. **A ausência de veredito da W0-1 não bloqueia esta decisão**, mas
   bloqueia a leitura de que "o ledger é reinjetado após compactação". Ele
   não é reinjetado: é apontado. A distinção é a lição de que sonda de
   EVENTO não é sonda de CANAL.
4. **Os limiares M1/M2 são propostos, não decididos** (§3.2). Um ADR que
   fingisse tê-los ratificados repetiria a classe que o §1.1 documenta:
   registro que promete mais do que o mecanismo entrega.
5. **A opção (C) fica formalmente REGISTRADA como reabrível.** O gatilho
   de reabertura está escrito na coluna de falsificação do §2.2: o dia em
   que o audit log carregar ≥ 1 campo de decisão por unidade de trabalho,
   (C) passa a dominar (A) em todas as colunas exceto reversibilidade — e
   esta decisão deve ser revista, não defendida.
