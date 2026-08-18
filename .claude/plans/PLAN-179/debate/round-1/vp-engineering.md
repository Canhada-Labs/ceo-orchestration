# VP Engineering — PLAN-179 round 1

## Verdict

**ADJUST** — o diagnóstico está correto e verifiquei E1–E4 contra o disco, mas
três decisões arquiteturais estão erradas como escritas: o fallback de sessão
quebra o invariante de um primitivo COMPARTILHADO, o hook de W2 é desenhado em
cima da mesma derivação que o E2 provou quebrada, e a wave de pinning entrega
pelo canal ainda não provado.

## Summary

Confirmei no código: `_write_snapshot` retorna `scratchpad_unavailable` por
`plan_id == "unknown"` antes de qualquer I/O
(`check_precompact_continuity.py:302-306`) — o E1 não é falha de disco, é o
caminho normal; `resolve_plan_id` filtra `plan_transition` por `session_id`
(`scratchpad_lib.py:144-152`) e levanta se não achar (`:153-164`); o PostCompact
desiste do snapshot para escopo não-PLAN (`check_postcompact_reinject.py:96-97`);
`SessionEnd._memory_dir_state` só testa `os.access(..., W_OK)` — nada escreve
memória. A tese ("problema de momento da escrita") sobrevive à verificação.

O que não sobrevive é o DESENHO de W1/W2. O plano cura o sintoma do E2 em dois
hooks e depois constrói um hook novo (W2) que precisa da mesma resposta —
"qual é o plano ativo?" — pela mesma rota. E o ledger é adicionado como QUARTA
superfície durável sem que nenhuma alternativa de consolidação seja avaliada,
sem teto de tamanho e sem critério de morte, o que contradiz o próprio E3 do
plano (superfície durável degrada quando a escrita é discricionária).

## Risks

1. **[P0] W2 herda a causa-raiz do E2** — `check_ledger_checkpoint.py` dispara
   "em fronteira de unidade (commit tocando um path do **plano ativo**)". A única
   derivação não-spoofable de plano ativo hoje é `resolve_plan_id`
   (`scratchpad_lib.py:103`), que é exatamente o mecanismo que falhou (2 eventos
   em 12.515 linhas). O plano curaria o sintoma em W1 e reintroduziria a causa
   em W2. Mesma classe de [[feedback-instrument-green-with-stale-question]]:
   instrumento novo, pergunta velha.

2. **[P0] Escopo de sessão smuggled no campo `plan_id`** — `_validate_plan_id`
   aceita `[A-Za-z0-9_.-]` até 64 chars (`state_store.py:145-159`), então
   `SESSION-<uuid>` PASSA mecanicamente. Mas o store é documentado com o
   invariante *plan isolation* (`scratchpad_lib.py:37-41`), o audit do store
   emite `plan_id_hash=_plan_id_hash(self.plan_id)` (`state_store.py:439`) —
   que passaria a hashear um session-id — e todo consumidor (`/memory-scratchpad`,
   handoff inter-agente) passa a ver escopos que não são planos. É violação de
   linguagem ubíqua: um campo, dois significados. Blast radius não é 2 hooks; é
   o primitivo compartilhado.

3. **[P1] OQ-1 respondida: SIM acumula, e não existe rota de remoção.** Cada
   escopo materializa `<id>.sqlite` + `<id>.sqlite.lock` sob
   `$HOME/.claude/projects/<project>/state/<store>/` (`state_store.py:114-126`,
   `:207-209`). O PreCompact escreve `store.set(KEY, payload)` **sem**
   `ttl_seconds` (`check_precompact_continuity.py:319`; default `None` = sem
   expiry, `state_store.py:276`), e `prune_expired` poda CHAVES, nunca o arquivo.
   Com escopo por sessão isso vira 2 arquivos por sessão compactada, para
   sempre, no HOME do adopter. Não é hipótese — é o comportamento do código.

4. **[P1] W1-b entrega pelo canal NÃO provado, e é a wave que menos pode.** As
   restrições fixadas sairiam por `additionalContext` do PostCompact
   (`check_postcompact_reinject.py:236-238`) — precisamente o canal do E5. O repo
   tem um canal com evidência POSITIVA local: `additionalContext` em SessionStart
   (`turbo_sessionstart.py:166-167`), e o SessionStart está wired com
   `"matcher": ""` (`settings.json:521-545`), portanto já dispara no matcher
   `compact`. Pinning de governança é o item de maior consequência do plano e
   está pendurado no canal de menor evidência.

5. **[P1] O cap de 9 é orçamento COMPARTILHADO que o plano não divide.**
   `_build_pointers` retorna `pointers[:9]` (`check_postcompact_reinject.py:193`)
   e o audit declara `pointer_count` 0..9 (docstring `:30`). Quando W1 passa a
   entregar snapshot — o caso de SUCESSO — os ponteiros crescem e as restrições
   fixadas de W1-b são o que trunca. A governança sai primeiro exatamente na
   sessão mais rica, que é o cenário do paper. Além disso o enum 0..9 muda de
   significado, o que exige bump de SPEC — não mencionado.

6. **[P2] "Commit" não é um evento de hook.** O detector disponível é PostToolUse
   sobre Bash casando `git commit` — e o Owner commita com `!` ou fora da sessão.
   O repo já tem a doutrina de que gate por FERRAMENTA é teatro porque Bash
   escapa. O hook advisory de W2 nasce com buraco de cobertura conhecido; a
   tabela TP/FP da janela measure-first mediria um universo censurado se não
   reportar a taxa de commits NÃO observados
   ([[feedback-measurement-must-list-its-inputs]]).

7. **[P2] `context_pressure_observed` e o float.** Campo float em evento coberto
   por HMAC descarta o evento inteiro (lição do repo). `used_bucket` precisa ser
   int com unidade no nome e ter teste de emissão+releitura, senão a métrica que
   dimensiona W0 nasce vazia.

8. **[P2] ADR-193 é reserva forward.** Maior id no disco é `ADR-191`; `ADR-192`
   está reservado ao PLAN-169. Se 169 não landar antes, 193 abre buraco na
   sequência. Alocar o número no momento da escrita, não na redação do draft.

## Must-fix

- **M1 (R1):** o gatilho de W2 deriva o escopo dos **PATHS do commit**
  (`.claude/plans/PLAN-NNN/**` ou path listado numa AC `[P?][USn][path]`), nunca
  de `resolve_plan_id`. É session-independent por construção. Escrever como AC
  explícita e como não-objetivo ("o ledger NÃO depende de `plan_transition`").
- **M2 (R2):** não sobrecarregar `plan_id`. Usar `store_name` distinto
  (`_validate_store_name` aceita kebab/underscore, `state_store.py:129-143`) +
  um campo `scope_kind` no blob. O invariante de isolamento de plano permanece
  intacto e o audit continua honesto.
- **M3 (R3):** TTL explícito no `set` do snapshot + item de GC de arquivos
  órfãos, dimensionado pelo N de compactações/semana que W0 vai medir.
- **M4 (R4):** o pinning nasce no `SessionStart(matcher=compact)` — canal com
  precedente local — e o PostCompact vira reforço. Assim W1-b deixa de ser
  refém do veredito de W0-1.
- **M5 (R5):** orçamentos separados para RESTRIÇÃO e PONTEIRO, restrições
  emitidas PRIMEIRO, nova dimensão de audit e bump de SPEC declarados na wave.
- **M6 (W0, custo):** a sonda deve carregar **dois canários numa única
  compactação paga** (PostCompact e SessionStart-compact). Como escrito, um
  resultado negativo obriga a uma segunda compactação paga para validar o
  fallback — e foi exatamente o custo do fires-proof que manteve o ADR-153 em
  `PENDING-LIVE`. Um experimento, três resultados possíveis.

## Nice-to-have

- Teto de tamanho do `LEDGER.md` (ex.: ≤2k tokens) com arquivamento de seções
  antigas — ver U3.
- Registrar reversibilidade por wave no ADR-193 (tier + exit strategy) — ver U5.
- `context_pressure_observed` emitido só na TRANSIÇÃO de bucket (responde OQ-4
  sem sampling: limita a poucos eventos por sessão e preserva a série).

## Unseen

- **U1 — falta critério de MORTE do ledger.** O plano admite na fronteira
  honesta que o ledger pode degradar como a memória (E3), mas uma janela
  measure-first só tem duas saídas escritas: enforce ou dívida silenciosa. Falta
  a terceira: *se a taxa de checkpoints omitidos > X% ao fim da janela, o ledger
  é REMOVIDO*. Sem isso o repo repete skills 157/164 (zero uso, mantidas).
- **U2 — nenhuma alternativa de consolidação foi avaliada.** Já existem três
  superfícies duráveis (scratchpad sqlite, memória nativa, audit-log) e o plano
  cria a quarta. Opções não consideradas: ledger como PROJEÇÃO legível do
  scratchpad; memória gerada do ledger; ledger DERIVADO do audit-log — este
  último eliminaria a escrita discricionária, que é a causa do E3. A skill exige
  matriz de trade-off com 2+ opções; o ADR-193 nasceria com uma só.
- **U3 — W2 e W3 empurram em direções opostas no mesmo orçamento.** §2.1 conclui
  que a alavanca é `F`. O ledger é conteúdo novo que a próxima sessão TEM de ler
  para recuperar estado: W2 adiciona ao working-set pós-boot exatamente o que W3
  tenta remover. Sem teto, o ledger de um plano longo cresce sem limite e a cura
  de continuidade PIORA o thrashing que o plano diagnostica.
- **U4 — a fronteira de trabalho é o momento de MAIOR pressão de contexto.** A
  doutrina troca escrita terminal por escrita em fronteira, mas a fronteira
  ocorre DENTRO da sessão saturada: quem escreve o checkpoint é o modelo já
  degradado por context rot. **Entrada de ledger errada é pior que entrada
  ausente**, porque a próxima sessão confia nela e pula a arqueologia. US6 diz
  "ACs com estado verificado" sem dizer QUEM verifica nem como se prova — e a
  fonte citada em `research-S309.md §1.3` lista "declaração prematura de vitória"
  e "marcar feature sem testar" entre os modos de falha do padrão que o plano
  está adotando. O ledger é a superfície ideal para eles.
- **U5 — reversibilidade não declarada.** W0/W1 são reversíveis (kill switch +
  revert). W2 não é: com ledgers em N planos e citados por outros artefatos,
  remover a doutrina fica caro. Isso classifica W2 como *Embedded* pela rubrica
  da skill, o que exige exit strategy escrita no ADR-193. "Vemos depois" não é
  exit strategy.

## What I would NOT change

- **W0 como gate absoluto.** Barato, read-only e a distinção "sonda de EVENTO ≠
  sonda de CANAL" é o achado de maior valor do plano. Manter, com M6.
- **Pointers-only do ADR-153 §Decision-2 intocado.** O comentário em
  `check_postcompact_reinject.py:148-159` documenta por que o LABEL do checkbox
  não é reinjetado (sanitização de control-char ≠ neutralização semântica). Essa
  fronteira está bem desenhada; o ledger NÃO deve reabri-la.
- **Advisory-first com janela measure-first** (precedente ADR-191) e os três kill
  switches com precedência de `CEO_SOTA_DISABLE`.
- **Delegar a poda de `F` ao PLAN-175**, definindo aqui só alvo e critério de
  aceite. Separação de responsabilidade correta.
- **Declarar a tabela η como estimativa até W0 medir.** Honestidade que a maioria
  dos planos não tem.
- **A recusa a RAG/vetor/embedding.** Coerente com stdlib-only; recuperação por
  ponteiro e path é a decisão certa neste substrato.

---

### Respostas às OQ

- **OQ-1 (snapshot órfão / GC):** sim, acumula, e hoje NÃO há rota de remoção —
  evidência em R3. Precisa de TTL no `set` + GC de arquivo, dimensionados pelo
  N medido em W0.
- **OQ-3 (trabalho sem plano ativo):** o gatilho não deve ser "plano ativo" —
  deve ser derivado dos PATHS do commit (M1). Commit que não toca path de plano
  fica FORA de escopo, com evento de skip nomeado (`ledger_checkpoint_skipped`,
  razão em enum fechado) para que a omissão continue visível. Isso resolve
  hotfix e sessão exploratória sem inventar plano nem re-herdar o E2.
- **OQ-4 (inflar o audit-log):** não usar sampling — sampling destrói a
  contagem que justifica a wave. Emitir só na TRANSIÇÃO de bucket, com o valor
  como int com unidade no nome (R7).
- **OQ-5 (colapsar as duas cerimônias):** manter **DOIS ADRs, UMA cerimônia**.
  São registros com lifecycles diferentes — o AMEND-1 fecha um registro ACCEPTED
  cuja prova voltou NEGATIVA (fato histórico que não pode ser reescrito num ADR
  novo), o 193 cria doutrina. Colapsar apagaria o registro do erro, que é o ativo
  mais caro desta investigação. O custo real é o pinentry, não o número de
  registros: um sentinel com os dois paths no Scope. Ordem obrigatória: AMEND-1
  primeiro (fecha o falsificado), 193 depois — o 193 só faz sentido se W1 provou
  o canal.
