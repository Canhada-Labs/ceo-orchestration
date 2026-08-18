---
plan: PLAN-179
round: 1
created_at: 2026-08-17T22:45:00-03:00
---

# PLAN-179 — Proposta para debate (round 1)

> Plano completo: `.claude/plans/PLAN-179-context-continuity-durable-state.md`
> Pesquisa (fonte única dos números): `.claude/plans/PLAN-179/research-S309.md`

## Tese

O repo não tem um problema de *memória*; tem um problema de **momento da
escrita**. Todo estado durável (scratchpad de continuidade, memória nativa,
`MEMORY.md`) é escrito em eventos TERMINAIS (`Stop`, closeout, `PreCompact`)
— exatamente os eventos que uma sessão morrendo por contexto não alcança ou
alcança degradada. A cura é mover a escrita para **fronteira de unidade de
trabalho** e proteger a governança da compressão com perda.

## Evidência (medida em 2026-08-16, não inferida)

- **E1:** o autocompact real de 09:34Z disparou os DOIS hooks do ADR-153 e
  entregou NADA: `snapshot_outcome=scratchpad_unavailable`, `plan_id=unknown`,
  `snapshot_found=false`, `pointer_count=1`. Fires-proof cumprido e NEGATIVO.
- **E2 (causa estrutural):** `resolve_plan_id()` exige `plan_transition` da
  PRÓPRIA sessão; transição só ocorre em mudança de status de plano. Censo:
  2 eventos em 12.515 linhas, ambos de outra sessão. O mecanismo funciona só
  em sessões curtas — anti-correlacionado com o caso de uso.
- **E3:** `SessionEnd.py` só VERIFICA gravabilidade; ninguém escreve memória.
  A memória drifta porque ninguém a escreve, não por bug.
- **E4:** `context-budget.py` expõe D1/D2/D5 que nenhum consumidor lê (sondas
  órfãs).
- **E5 (NÃO confirmado — vira sonda W0-1):** `additionalContext` em PostCompact
  pode ser canal inerte (doc ambígua; `turbo_sessionstart.py` contradiz a doc
  em SessionStart). Sonda de EVENTO ≠ sonda de CANAL.
- **η (thrashing):** piso re-pago `F` ≈ 45–55k (Gate 1+2 40.116 tok medidos +
  índice 4.413). η = (T−F−S)/T ⇒ piso de thrashing deste repo é T≈60k, ACIMA
  do mínimo da API (50k). A alavanca é `F` (PLAN-175), não `T`.
- **Governance Decay (paper, outro setup):** restrições visíveis 0% de
  violação; pós-compactação 30–59%; com Constraint Pinning volta a 0%.
  Existe ataque nomeado (Compaction-Eviction) que derrotou todos os modelos.

## Decisões propostas (o que o debate deve atacar)

1. **W0 (sonda/medição, read-only, gate de tudo):** sonda viva do canal
   PostCompact com controle positivo; medir `F` e `T` reais; ação de audit
   `context_pressure_observed` (enum fechado); progress guard (halt se
   compactar não liberar headroom — válvula anti-loop).
2. **W1 (cura do snapshot vazio):** fallback de escopo por SESSÃO quando
   `PlanIdDerivationError` (a escrita NUNCA é pulada); enum
   `snapshot_outcome` ganha `written_session_scope`; ADR-153-AMEND-1
   (cerimônia GPG); teste que replica E1 e FALHA contra o código de hoje.
3. **W1-b (Constraint Pinning):** separar PONTEIRO (onde olhar) de RESTRIÇÃO
   FIXADA (a regra em si) — conjunto FECHADO, versionado no repo, não
   derivado de disco em runtime (imune ao Compaction-Eviction por
   construção); controle ADVERSARIAL obrigatório (transcript hostil ⇒
   restrições ainda aparecem).
4. **W2 (ledger de fronteira — mudança de doutrina):** `PLAN-NNN/LEDGER.md`
   por plano (unidade corrente, ACs verificados, SHAs verbatim); hook
   `check_ledger_checkpoint.py` ADVISORY (measure-first, como ADR-191);
   PreCompact passa a apontar para o ledger; SessionEnd emite delta candidato
   de memória (contagem+paths, nunca corpo); ADR-193 (cerimônia).
5. **W3 (baixar o piso):** definir alvo de redução de `F` (~50k→~20k; dono da
   poda é o PLAN-175); ligar template de compactação (PLAN-133 D4); decidir
   destino das sondas órfãs D1/D2/D5; guia do adopter.
6. **W4 (governança do ledger):** proveniência por entrada (owner-instruction/
   ceo-derived/agent-returned/external-tool; origem externa nunca relida como
   instrução); write-gate com scanner harness-mimicry (hit ⇒ DESCARTA);
   threat model nos 6 eixos + 2 classes novas (Compaction-Eviction,
   experience grafting vs rail de lições A6); post-deletion verification.

## Não-objetivos (fechados)

Sem compactação própria; sem RAG/vetor/embedding (stdlib-only); pointers-only
do ADR-153 §Decision-2 intocado (corpo de arquivo em additionalContext segue
proibido); sem Agent Teams; canônico só com cerimônia.

## Kill switches

`CEO_COMPACTION_CONTINUITY=0` (existente) · `CEO_LEDGER_CHECKPOINT=0` (novo,
W2) · `CEO_SOTA_DISABLE=1` (precedência mestre).

## Fronteiras honestas já declaradas

W0-1 pode invalidar o desenho de W1 (canal inerte ⇒ migra p/
`SessionStart(matcher=compact)`); ledger é superfície nova que pode degradar
como a memória (mitigação = omissão VISÍVEL, não garantia); advisory ≠
enforcement (flip é cerimônia futura); η depende do PLAN-175; números de
pinning vêm do paper — evidência LOCAL sai do controle US5d; tabela η é
estimativa até W0 medir.

## Perguntas abertas para os críticos

- OQ-1: o fallback de escopo-sessão (W1) cria risco de snapshot órfão
  acumulando em `~/.claude`? Precisa de GC/TTL?
- OQ-2: o conjunto de restrições fixadas (US5c) — qual é o critério de corte
  para "mínimo"? Quem pode mudá-lo (cerimônia ou PR normal)?
- OQ-3: o hook advisory de W2 dispara por commit tocando path do plano ativo —
  e trabalho sem plano ativo (hotfix, sessão exploratória)?
- OQ-4: `context_pressure_observed` em toda pressão de contexto pode inflar o
  audit-log (2,1 MB hoje)? Sampling?
- OQ-5: ADR-193 e ADR-153-AMEND-1 são duas cerimônias — colapsar numa?
