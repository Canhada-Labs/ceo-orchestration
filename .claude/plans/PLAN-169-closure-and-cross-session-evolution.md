---
id: PLAN-169
title: Fechamento total + evolução cross-session — publica v1.3.0 e v1.4.0
status: executing
created: 2026-08-08
reviewed_at: 2026-08-08
reviewed_by: "Owner — ratificação explícita em chat (S298): 'ratifica tudo com as recomendações e commita o pack'. Cobre R-A (esta transição), R-B (gate de debate §12.4 aceito como design-coherent), R-C (deferral de higiene de registro), OQ-1..5 e W0.8 conforme as recomendações do checklist."
owner: CEO
depends_on: [PLAN-166, PLAN-167, PLAN-168]
budget_tokens: 500-800k (fechamento + DOIS trens com rodadas de rail; bateria E1-E4 EXCLUÍDA — orçamento próprio no PLAN-170)
budget_sessions: 11-14
context_risk: high
external_wait: ownership-nightly cron (validação do port) + ADR-103 hold 24h ×2 trens (v1.3.0, v1.4.0)
tags: [release, ci, governance, cross-session, quota-resume, experiments]
---

> **v2.5 (2026-08-08, mesma sessão).** Rail codex r8-r15 (7 rodadas
> extras) + round 5 do debate. Curas grandes: escopo do W4-C completado
> em ARQUIVOS (kernel path ⇒ cerimônia de kernel; +install.sh, +3
> hooks, +audit_emit/SPEC/config_change, +superfícies de contagem);
> **trust model do quota-resume REFEITO (r11/r15): assinatura HMAC
> descartada como oráculo de mesmo-UID → fronteira de confiança
> declarada honestamente + controles anti-erro/corrupção (não
> anti-adversário) + evidência de exaustão bound/fresh/single-use com
> janela pós-reset**; quota-resume só "supported" com live-fire GO
> (senão experimental); `StopFailure`/`PostToolBatch`/`TaskCompleted`
> version-gated; E0 fração serial inclui máquina serial do caminho
> crítico; injector com tabela nome→slug + gramática p/ nomes reais;
> OQ-5(a) vira mini-cerimônia de B.a; Agent(model) fechado em duas
> camadas. **Debate: 5 rounds. Round-5 = triade COMPLETA sobre a v2.5
> EXECUTÁVEL (codex r22: a v2.5 evoluiu além do v2.4 do r4 e a triade
> precisava revisar o design final): Security ACCEPT + DevOps ACCEPT
> (zero must-fix) + VP ADJUST com 1 must-fix (MF-D janela do kernel
> override) APLICADO. Gate de máquina: jaccard 0.692 / max-rounds /
> §12.4 ⇒ `status: unresolved` + ESCALAÇÃO ao Owner; o CEO NÃO declara
> o gate met.** Terminal em `round-5/consensus.md`; recomendação do
> CEO = ratificar como design-coherent (base: triade completa na v2.5,
> 2 ACCEPT + 1 ADJUST-resolvido, VETO satisfeito, jaccard a 0.008 do
> threshold, riscos de execução com dono/gate). Waves L3+/kernel
> gateadas por GPG (gate humano mecânico); waves livres W0-W2 esperam
> a decisão do Owner (W0 Passo-0).
>
> **v2.3 (2026-08-08, mesma sessão).** Round 2 REGENERADO no schema de
> máquina (achado codex r6: meu formato curto quebrava o
> debate-converge.py) → 1× APPROVE + 2× ADJUST, todos aplicados (VP
> MF-A/B/C: escopo do W4-C em ARQUIVOS, controle W2.6 transitório,
> aceite do quota-resume mede o ARM; Sec R-SEC13/14/2/15: template
> constante na injeção, PreToolUse SendMessage incondicional, ordem
> dos controles do snapshot, isolamento do fleet). `round_verdict:
> PROCEED` com o output da máquina REGISTRADO e interpretado (jaccard
> 0.0 = defeito de instrumento provado, agora item W2.9).
> Anonymization-maps criados (desvio do round 1 registrado). r6 também
> gerou: research-MANIFEST (integridade+fontes), ponteiro neutro no
> research-README, W4.1 com gatilho real (hook injeta instrução) e
> W2.3 com alvo de resolução real (.claude/agents/).
>
> **v2.2 (2026-08-08, mesma sessão).** Round 2 do debate: 1× APPROVE
> (DevOps) + 2× ADJUST com residuais 100% textuais → aplicados como
> v2.1 (`debate/round-2/consensus.md`). Rail codex: r1 = 3×P1
> (script 167 perigoso → neutralizado; speed-claims → anexos
> arquivados fora do repo com ponteiro; contaminação → varrida por
> classe) e r2 = 2×P1+5×P2 (kill-switch de Workflow no W4-C; rota de
> clone do fleet 170; E0 com tempo-morto na fração serial e M=14;
> exec bit removido; este header). Histórico da v2 abaixo.
>
> **v2 (2026-08-08, mesma sessão).** Round 1 do debate: 3× ADJUST,
> zero VETO. Consensus em `PLAN-169/debate/round-1/consensus.md` —
> 20 decisões aplicadas nesta v2 (as maiores: fronteira canônico/livre
> corrigida em W2.1/W2.4; wave **W4-C** de cerimônia de substrato com
> escopo fechado; bateria E1-E4 movida para PLAN-170 com gatilho
> nomeado, ficando aqui pré-registro+E0; quota-resume re-arquitetado
> probe-first com propriedade comprada declarada; W4.4 re-escopado
> pelo disco; probes W0.0 regem a própria execução autônoma; E.7/E.11
> incluídos). Orçamento re-declarado SEM a bateria (que tem orçamento
> próprio no PLAN-170: estimativa honesta 6-20M tokens).

# PLAN-169 — Fechamento total + evolução cross-session

> **Mandato do Owner (S298, 08/08):** "Preciso de uma solução madura e
> final pra publicar, já contemplando todas as novidades do Claude Code
> e fechando tudo que está pra trás." E, em mensagem ao vivo na mesma
> sessão: **"depois que terminar o plano, autoexecute ele autônomo, use
> workflow e não pare de trabalhar até terminar"** — pré-autorização
> explícita de execução autônoma registrada aqui (a transição
> `draft→reviewed` normalmente exige leitura do Owner; esta execução
> corre sob a instrução literal acima, com TODOS os pontos Owner-only —
> GPG, tags, aprovação npm, decisões OQ — parados num checklist de
> retorno, nunca contornados). Este plano é a resposta única:
> nenhum item pendente fica sem endereço (fecha, defere COM gatilho
> nomeado, ou registra recusa), e as novidades do substrato entram sob
> teste honesto antes de virarem claim.
>
> **Fundamentação:** ledger completo de pendências com evidência
> path:line em `.claude/plans/PLAN-169/ledger-S298.md` (6 varreduras
> read-only paralelas, 65 itens, 15 contradições memória-vs-disco
> resolvidas). Referências `A.*`/`B.*`/`C.*`/`D.*`/`E.*`/`F.*` abaixo
> apontam para esse ledger. Pesquisa de substrato e academia:
> conclusões incorporadas neste texto; originais no archive privado
> (ver `PLAN-169/research-README.md` — doutrina no-speed-claim,
> decisão do rail codex r2).

## Context

- **v1.3.0 está parada na porta:** PLAN-166 W1 landado (`9d3f21d`),
  W2 (re-pass → rc.2 → hold → GA) zerado de progresso material (A.1-A.4).
  O plano 166 segue `executing` e é o veículo do GA — este plano NÃO o
  duplica; fecha as pré-condições (A.0.*) e o executa como W6.1.
- **Um CI vermelho novo com causa única:** o 1º `ownership-nightly` em
  Linux (run 31246426017) deu 27 REDs; forense fechou contabilidade
  célula-a-célula: **1 linha** (`test-ownership-table.sh:162`, sonda
  `stat` BSD-first que no GNU contamina stdout) explica os 24 falsos
  (22 super + 2 sub-detecção); os 3 REDs esperados {0016,0024,0027}
  reproduziram idênticos ao Darwin (B.d). Produto inocentado.
- **Dívidas de infra re-verificadas no disco** (C.*): duas "verdades"
  da memória estavam erradas (overhead-ack JÁ cobre Write — o defeito é
  o canal de entrega; pair-rail-gate tem exec bit — o defeito é exigir
  `OPENAI_API_KEY` sem rota de login). O P0 case-insensitive está
  FECHADO (`6b5dd10`) — não entra.
- **Um P1 com prazo duro embutido:** `.claude/.framework-version` não é
  site de bump (E.1/F.7) — `release.yml:84-97` assere
  `marcador == VERSION` incondicional; passa hoje por coincidência
  (`1.3.0 == 1.3.0`) e **quebra no primeiro bump 1.4.0** — exatamente o
  bump que este plano fará.
- **O substrato mudou:** Claude Code agora tem comunicação
  cross-session entre terminais/máquinas (ListAgents + SendMessage,
  v2.1.224+), Workflow tool de orquestração determinística, agentes
  background nomeados, model/effort por agente, e expõe a quota de 5h
  no statusline (`rate_limits.five_hour.{used_percentage,resets_at}` —
  já parseada por `statusline-ceo.py:25,111`). A linha de honestidade
  do repo permanece a que o CLAUDE.md publica ("no speed claim", após
  os seis experimentos internos) — o que muda é a VARIÁVEL: nenhum
  daqueles experimentos tinha cross-session real (contextos
  verdadeiramente independentes com canal de coordenação). É a
  primeira mudança de substrato que ataca a variável estrutural, não a
  tática — e por isso merece TESTE pré-registrado, não claim.

## Goal

Publicar v1.3.0 (GA via rc.2, PLAN-166 W2) e v1.4.0 (novidades
cross-session + quota-resume + fixes) com **zero pendência herdada sem
endereço**: cada item do ledger fecha neste plano, defere com gatilho
nomeado, ou registra recusa do Owner.

## Thesis

1. **Dois trens, em sequência imediata — não um trem gordo.** v1.3.0
   já tem rc.1, debate fechado (166) e delta-allowlist estrito; injetar
   features novas nela reabriria o debate do 166 e violaria o próprio
   gate de delta que o 166 construiu. v1.4.0 sai na sequência com as
   novidades — e o bump minor é o **controle positivo ao vivo** do fix
   E.1. Publicação "madura e final" = duas tags com o mesmo rigor, dias
   de distância, não uma tag que mistura closure com feature.
2. **Fechar o instrumento antes do trem.** O nightly vermelho (B.d) é
   1 linha + 2 riders; portar ANTES da rc.2 remove o único CI vermelho
   de causa conhecida da janela de release (A.0.2).
3. **Novidade vira claim só depois de teste pré-registrado.** O repo
   mantém "no speed claim" há 6 experimentos. Cross-session muda a
   estrutura (contextos independentes + coordenação explícita), então
   merece o 7º experimento — com desenho pré-registrado, baseline solo
   otimizada e critério de morte. Se não replicar, o "no speed claim"
   fica — e o relatório é publicável do mesmo jeito.
4. **Quota de 5h é problema de continuidade, não de velocidade.** O
   acionador de quota-resume (W4.1) fecha a classe "sessão autônoma
   morre no estouro e o trabalho fica pro próximo dia" — pedido
   explícito do Owner, e o dado já existe no substrato.

## Waves

> **ORDEM DE EXECUÇÃO (codex r4-P1 — difere da numeração temática):**
> `W0 → W1 → W2 → `**`W6.1 (trem v1.3.0 COMPLETO, main congelado do
> corte da rc.2 até o GA)`**` → W3 → W3-K → W4 (probes+livres) → W4-C
> → W5 (pré-reg+E0) → W6.2`. Razão: o HEAD candidato da rc.2 EXCLUI
> W3/W3-K/W4-C (conteúdo v1.4.0) — landá-los antes do GA ou embarcaria
> conteúdo 1.4 na 1.3.0 ou faria o guard de delta/ancestralidade
> rejeitar a tag. Durante o hold de 24h, NENHUM commit em main.

### W0 — Higiene + escrituração (L1-L2, sem cerimônia, 1 sessão)

> **W0.0 — Probes de Workflow ANTES de qualquer execução de escrita
> via Workflow (R-SEC1, rege a execução DESTE plano):** (i)
> `SubagentStart`/gate de spawn dispara para `agent()` de Workflow?
> (evidência parcial S298: NÃO — zero `agent_spawn` para os 7 agents
> do inventário); (ii) `check_canonical_edit.py` bloqueia edit
> canônico executado por agent de Workflow? Até os dois estarem
> respondidos com evidência registrada, **Workflow fica restrito a
> trabalho read-only** (a execução S298 cumpre isso).

| # | Item | Ledger | Ação + aceite |
|---|---|---|---|
| W0.1 | Commitar `PLAN-167/OWNER-PREPARE-TO-SIGN.sh` **NEUTRALIZADO** | D.1 + codex r1-P1 | **Correção do rail (r1):** na árvore pós-168, re-executar o script REVERTERIA o PLAN-168 (staged stale). Cura aplicada: header ⛔ OBSOLETO + `exit 1` no topo (texto original preservado abaixo, inalcançável); commit como `100644` (SEM exec bit — evidência, não executável). Fecha a irreprodutibilidade documental sem criar um reprodutor perigoso |
| W0.2 | Marcar `PLAN-166/OWNER-W1-LAND-step1.sh` OBSOLETO | D.2 | Header `# OBSOLETO — substituído por step1b; re-executar REVERTERIA o PLAN-167` (não remover: evidência) |
| W0.3 | Apagar os 2 tarballs untracked + padrão gitignore | D.3/D.4 | `rm` dos 2 (Owner aprova via review deste plano); `.gitignore` ganha `.claude/plans/*/archive/*.tar.gz` com comentário de causa; NUNCA ignorar `archive/` inteiro |
| W0.4 | Triar `Translations drift` vermelho desde 04/08 | A.0.3 | Investigar o run, registrar causa; curar OU abrir exceção nomeada com gatilho |
| W0.5 | §-final no PLAN-166: subsunção AC-3/AC-4 + ratificação `approx` | A.5.1-A.5.5, F.8, F.14 | Corpo do 166 passa a citar 167/168 e onde cada AC foi provado; ratificação `approx`/collect-errors agendada para o material assinado da rc.2 |
| W0.6 | Memória: `check_tier_a_spec_version_drift` + path `verify-counts` | E.6, F.11 | Escrever as 2 memórias; varrer runbooks vivos por `bash <script> \|\| echo advisory` e trocar por invocação fail-closed (só superfícies vivas — planos landados são evidência imutável) |
| W0.7 | Verificar 2 claims herdadas | E.8, E.9 | (i) grep `ownership_table.tsv` pela transição maintainer→user: existir ⇒ fechar follow-up no log; faltar ⇒ adicionar célula; (ii) controle positivo do scanner FIFO (§5.7) ou registrar aberto |
| W0.8 | Decisão Owner: convenção de ACs de 167/168 | E.12 | Registrar no §9 de cada plano: "AC provado no registro de execução; checkbox não usado" OU marcar checkboxes com evidência |
| W0.9 | Decisão Owner: break-glass ADR (aceite → W3; recusa → registrar) | A.0.5, E.5 | `CEO_PAIR_RAIL_VERDICT_OPTIONAL` sem modo de transição no gate novo é caminho de incidente na janela de release |
| W0.10 | Higiene POSIX nos runbooks vivos | E.11 | Varrer runbooks/checklists vivos por `\s` em `grep -E`/`sed` (BSD não suporta — falso "fora de escopo" já aconteceu na cerimônia do 166) → `[[:space:]]`; planos landados são evidência imutável, ficam fora |

### W1 — Port do harness e2e para Linux (L2, `scripts/tests/` livre, 1 sessão + 1 cron)

1. **Fix da causa-raiz** (`test-ownership-table.sh:162`): inverter para
   GNU-first no padrão já canônico no repo (`install.sh:727-730`) ou
   forma `if/else` (padrão `test-council-grok-artifact.sh:86-91`).
   Nunca `A 2>/dev/null || B` com A de stdout contaminante.
2. **Rider fail-closed:** mtime não-parseável = `HARNESS-ERR`, nunca
   ruído descartável (`:171` hoje descarta silencioso ⇒ sinal morto
   invisível — foi a sub-detecção de 0017/0021). Input-parse falho é
   fail-CLOSED (CLAUDE.md §4).
3. **Rider FALSE-GREEN:** controle positivo de refresh byte-idêntico
   (a classe que cegou `OWN-0073` no Linux); re-verificar 0073
   especificamente pós-port.
4. **Sweep da classe** `A 2>/dev/null || B` no harness inteiro
   (só instrumento; produção já verificada limpa).
5. **Aceite (falsificável):** nightly em Linux = **62 GREEN / 3 RED
   exatos {OWN-0016, OWN-0024, OWN-0027}**; qualquer resíduo = segunda
   suposição de plataforma não achada — parar e investigar, não
   ajustar. **Validação imediata (D3): logo após o commit do fix,
   disparar `gh workflow run ownership-nightly.yml` LONGE do horário
   do cron (`43 6 * * *`; `concurrency: cancel-in-progress: true`) —
   não esperar a janela agendada.**
6. **PROIBIDO:** tocar `ownership_table.tsv` / `ownership-expected-reds.txt`
   para tirar o vermelho. Corrigir o comentário de estimativa
   (`ownership-nightly.yml:34-37`) com o tempo observado no run real
   (ver `31246426017`; **[codex r20-P2] sem publicar o número aqui —
   AGENTS.md no-throughput-claim**); manter `timeout-minutes: 90`.
7. **W1.7 (E.7, MF-7) — shellcheck de CI passa a cobrir
   `scripts/tests/**` e `scripts/*.sh`:** hoje o gate cobre só
   `.claude/{scripts,hooks}` — e a causa-raiz do W1 mora EXATAMENTE no
   diretório sem lint. Controle positivo: violação plantada em
   `scripts/tests/` deixa o job vermelho. **DECISÃO (MF-2R, predicado
   rodado): o wiring é o step `Shellcheck hooks and scripts` em
   `validate.yml:296-315` — e `validate.yml` é KERNEL PATH
   (`check_arbitration_kernel.py:135`) ⇒ o toque de CI entra no pack
   **W4-C (cerimônia de kernel; codex r9)**, conteúdo v1.4.0, e NÃO
   gateia o aceite 62/3 nem o trem v1.3.0.** O que fica no W1: fix da
   causa-raiz + riders + sweep.
   (Owner pode puxar o shellcheck para antes da rc.2 ao custo de uma
   cerimônia extra na janela — escolha consciente, não default.)
8. E.14/E.15 (células 0016/0024/0027) **ficam deferidas** com gatilho:
   plano próprio; fechar célula e encolher expected-reds NO MESMO pack
   (ordem obrigatória, PLAN-168 §W2).

### W2 — Fixes verificados em superfícies LIVRES (L2, 1 sessão; 7 itens, um deles só-docs)

> **Fronteira corrigida pelo round 1 (MF-1):** os antigos W2.1
> (`smoke-install.yml` — CANONICAL, `check_canonical_edit.py:184`) e
> W2.4-hook (`check_anti_ceo_overhead.py` — CANONICAL, `:139`)
> **migraram para o pack W3**. Antes de tocar QUALQUER alvo desta
> wave, rodar `_matches_canonical_guard` no path (10 s) — a lista
> abaixo foi verificada, mas o predicado é a autoridade.

| # | Item | Ledger | Fix + controle |
|---|---|---|---|
| W2.2 | Perf probe Case-A | B.c, F.9 | N 100→200+, índices derivados de n (nunca hardcoded), pré-condição de colapso do ADR-163; reavaliar o switch `on_ci`→mediana (com N alto, gatear p95/p99 real); **fix de CLASSE**: mesmo passe em `test_claim_producer_pair_end_to_end_loop_perf`; a decisão vira emenda ADR-163 (texto no pack W3) |
| W2.3 | Injector: resolução EXATA com alvo real | C.1 + codex r6/r7-P1 | `inject-agent-context.sh:775-795`: **ordem de resolução com alvo existente** — (1) heading EXATO nos team-personas; (2) arquétipo core validado ⇒ **TABELA EXPLÍCITA nome→slug-nativo** para `.claude/agents/*.md` (os slugs NÃO são deriváveis: `DevOps Engineer`→`devops.md`; e `VP Engineering` NÃO TEM arquivo em agents/ — codex r7); (3) papel só-de-tabela (linha no SKILL MAP sem persona nem agents/*.md) ⇒ **perfil sintetizado DA PRÓPRIA LINHA** (nome + skill + autoridade — o que o CEO fez à mão na S298), rotulado como tal; (4) nome fora do SKILL MAP ⇒ **erro fail-closed**. **[codex r12-P2]
A GRAMÁTICA de entrada (`:157`, hoje só `[A-Za-z0-9 _-]`) precisa
aceitar os nomes REAIS do roster (`UI/UX Lead`, `Accessibility & i18n
Engineer`) — estender charset com sanitização OU mapear nome→slug
canônico ANTES da validação; casos de teste com `/` e `&`.** Testes: persona ambígua (`Security Engineer` vs `(AppSec)` — fuzzy entregou "Government Cybersecurity Engineer" no debate deste plano) + `DevOps Engineer`→devops.md via tabela + `VP Engineering`→perfil sintetizado + nome inexistente aborta |
| W2.4 | Overhead-ack: SÓ as docs (parte livre) | C.3, F.4 | Corrigir `docs/TROUBLESHOOTING.md:72` + `.pt-BR.md:73` para prometer exatamente o que o mecanismo entrega HOJE (prefixo Bash, janela do predicado). O canal novo (predicado/`PostToolBatch` como caminho primário — R-SEC6; sentinela só se necessário: TTL ≤ janela, single-use, session-bound, guarda symlink, evento na escrita E no consumo) mexe no hook CANONICAL ⇒ **pack W3** |
| W2.5 | pair-rail-gate: rota de auth | C.2, F.5 | Gate 1 aceita `OPENAI_API_KEY` OU codex autenticado por login (`codex auth status`-equivalente); fail-closed se nenhum; `CEO_PAIR_RAIL_DISABLE` deixa de ser a única saída. **[codex r20-P2] PROPAGAR o método de auth escolhido: o Gate 2 (rotação ≥90d da API key) só se aplica à ROTA API-key — na rota login ele é PULADO (senão o último `OPENAI_API_KEY` de 2026-05-09 reprova o login válido).** Aceite: gate roda até o fim NESTA máquina por AMBAS as rotas (evidência dinâmica — lacuna (i) do ledger) |
| W2.6 | Marcador = 12º site de bump | E.1, F.7, A.0.4 | `.claude/.framework-version` entra em `_release_bump_sites.py` `_SITES` + `VERSION_SITES` do `verify-counts.sh`; controle positivo plantado (marcador dessincronizado ⇒ vermelho) **TRANSITÓRIO [VP r2-MF-B]: planta, observa o vermelho e DESPLANTA no MESMO commit — proibido atravessar a janela do nightly (`43 6 * * *`) e proibido existir no HEAD candidato da rc.2** (a ordem W2→W6.1 pôs este controle adjacente ao corte, onde `marcador == VERSION` é fail-closed); o bump 1.4.0 do W6.2 é o controle ao vivo |
| W2.7 | Matcher GUIA-COMPLETO | E.3 | 2 frases de contagem de ADR vigiadas com controle positivo por rótulo |
| W2.8 | Família "script livre que decide gate" | E.4, D.8 | Inventário da família + proposta de guard (canônico vs checksum no gate); execução de guard canônico, se decidida, entra no pack W3 |
| W2.10 | **Fleet-currency (dados livres)** — model-ids de geração antiga em superfícies FUNCIONAIS | S298 auditoria Fable (`PLAN-169/fleet-currency-audit-S298.md`) | Item de CLASSE, não patches pontuais (anti-padrão S296): a cura é derivar TODO conjunto funcional de model-id da autoridade ADR-149 + oracle de paridade por superfície (padrão `test_adr149_validator_parity.py` já existente). Nesta wave, os fixes de DADOS livres: F2 `_tier_rank` sem gen-5 (direção promote/demote INVERTIDA — contorna o gate de demote), F3 pricing do value-dashboard sem gen-5 (custo da frota corrente invisível), F4 default do stop-review em opus-4-8, F8-F10 + displays D1-D3/D6 + sweep de docs D7. **A parte de DECISÃO (F1 perfis, F5 enum+loader, F6 template, dimensão fleet-currency no nightly, D4/D5 Gate-1/2) vai no W4.3/W4-C** — ver a nota lá. Por que o instrumento existente não pegou: `check-model-deprecations.py` responde "vai quebrar na API?", não "é a frota corrente?" — pin antigo-mas-ativo, display mentiroso e FURO de pricing escapam estruturalmente |
| W2.9 | Instrumento de convergência do debate | S298 (codex r6-P1 + repro) | `debate-converge.py` tem 2 defeitos provados nesta sessão: (i) seção `## Risks` SEM bullets (parágrafos `**R-X**`) parseia para ZERO itens EM SILÊNCIO — família registered-vacuous (o round-1 do Security contribuiu 0 riscos ao conjunto sem ninguém saber); fix: zero bullets numa seção Risks presente ⇒ erro barulhento por crítica, não só `zero_coverage` global; (ii) risco RESOLVIDO entre rounds conta como divergência (sai do conjunto ⇒ Jaccard cai) — documentar a semântica e reportar separadamente `resolved` vs `novel` para o veredito do CEO não depender de um número que pune a cura; **(iii) [codex r17] `compute_convergence` força `convergence_met=false` quando `round_num >= MAX_ROUNDS` MESMO com jaccard ≥ threshold — contra §12.4 (que trata convergência-no-teto como convergência, não impasse); fix: se jaccard ≥ threshold no round-teto ⇒ CONVERGED, não max-rounds-unresolved** |

### W3 — Pack canônico único + cerimônia GPG (L3+, 1 sessão)

1. **B.a — `PROTOCOL_SOURCE` malformado** (repro confirmado): filtro
   python (`upgrade.sh:1564-1577`) com **allowlist POSITIVA de
   charset** (R-SEC8 — não blocklist de control chars) ⇒ rejeição ⇒
   vazio ⇒ fallback D3 (rota já projetada), com **WARNING nomeando a
   chave rejeitada, assertado em teste** (silêncio = mudança
   silenciosa de propriedade do pointer); gerador
   (`_framework_manifest_set.sh:667`) monta replacement com `printf`
   (não sed) OU valida newline; atribuição guardada
   (`if ! _ptr_full=$(...)` ⇒ WARNING + PRESERVE, nunca abortar a meio
   caminho — postura de `upgrade.sh:1547-1550`); caso novo no
   `test-protocol-pointer-render.sh`.
2. **W3.2 (ex-W2.1, MF-1) — Parity: 2º fator causal:**
   `smoke-install.yml:267` → `grep -qF 'positive control: FIRED in
   every mode'` (+ opcional: verdicts por modo `:1` e nenhum
   `:0`/`:2`); fecha a exceção nomeada do AC-4 do 166 — registrar no
   §-final do W0.5. (1 linha de workflow; canônico ⇒ pack.)
3. **W3.3 (ex-W2.4-hook, MF-1+R-SEC6) — canal do overhead-ack:**
   caminho primário = cura pelo PREDICADO (P4 não disparar em
   fan-outs legítimos de investigação; considerar `PostToolBatch`);
   sentinela persistido SÓ se o predicado não bastar, com: TTL ≤
   janela do predicado, single-use, ligado ao `session_id`, guarda
   symlink/traversal, evento HMAC na escrita E no consumo.
4. **E.10** — linha morta do guard ancestral-symlink: apagar se ainda
   existir (verificar antes; promessa do 167 §5.8).
5. **Emenda ADR-163** (decisão do W2.2) + **ADR break-glass** (se W0.9
   aceitar) + **E.17** nota histórica no ADR-186 §5 (resolvido por
   `6b5dd10`).
6. Se W2.8 decidir guard canônico para a família de scripts: incluir.
   **[codex r18] O wiring do shellcheck do W1.7 é `validate.yml` =
   KERNEL PATH ⇒ vai para o W4-C (cerimônia de kernel), NÃO para este
   pack (W3 só tem sentinel comum e bateria no kernel-deny).**
7. Protocolo: staged/ + manifesto sha256 RASTREADO + `shasum -c`
   fail-closed + sentinel GPG inline + touched−scope=∅ + land.

### Registro de execução — W3 LANDADA (S312, 2026-08-18, commit `e5ce982`)

Pack RE-STAGED por item semântico (S312; 17 receitas Workflow
`wf_69229d1b`, merge 3-way live×baseline×staged) e landado por cerimônia
GPG (`W3-approved.md` + `.asc`, anchor `996d72b`): 14 targets + 1 novo
(`test-w3-vcures.sh`). G1-G7 verdes; bateria viva: render 9/9, suíte
completa 7.049 passed. Curas V1/V2/V4/V5 do verdito rc.2 CURADAS.
- 10 staged CONSUMIDOS (`staged-w3/consumed/` — itens já no vivo por
  outra rota; whole-file regrediria curas).
- PENDENTES ⚖️ do Owner (`staged-w3/pending-w28/` + PENDING-DECISIONS.md):
  família W2.8 (item 6 desta wave) e ADR break-glass (W0.9) + RELEASE.md
  (delta família-dependente). Itens 5-6 do plano desta wave ficam
  PARCIAIS até essas decisões.
- Follow-up de gate registrado: o G4 do `OWNER-W3-LAND.sh` roda a
  bateria num subshell `( ... ) || ABORT` — o `set -e` interno é
  desabilitado pela semântica do bash e só o rc do ÚLTIMO comando
  decide o abort (o FAIL R1 ambiental do macOS TMPDIR passou sem
  abortar; inócuo aqui porque o G6 vivo re-roda e deu 9/9, mas é a
  classe "gate que não fala"). Cura: agregar rc por comando; e rodar a
  sim fora do $TMPDIR symlinked.

### OQ — decisões estruturadas do Owner (S312, 2026-08-18, AskUserQuestion)

- **W2.8 (família gate-scripts):** opção selecionada VERBATIM:
  **"Ratificar (b)-narrow (Recomendado)"** — "Fecha a classe 'script
  livre que decide release sem pin'. O trem rc.3→rc.4 mexeu nesses
  scripts 10+ vezes — o custo do re-pin é real mas o fail-loud pega
  exatamente o drift que hoje passa calado. Cerimônia separada, sem
  pressa." Execução: trem `staged-w28/` + `OWNER-W28-LAND.sh` +
  `~/canhada-labs/OWNER-W28-SIGN.sh`.
- **W0.9 (ADR break-glass):** opção selecionada VERBATIM:
  **"Aceitar, renumerado (Recomendado)"** — "O trem rc.4 provou a
  necessidade (triagem GO-WITH-CONDITIONS em janela de release). Entra
  na mesma cerimônia futura da W2.8 ou noutra — 1 pinentry cobre."
  Execução: ADR renumerado 191→193 no mesmo trem staged-w28.

### Registro de execução — W2.8 + W0.9 LANDADOS (S313, 2026-08-18, commit `874117c`)

Cerimônia GPG (`W28-approved.md` + `.asc`, anchor `aa6462b`): 15 targets
+ 2 ADRs novos (192 gate-scripts, 193 break-glass) + manifesto
`.claude/governance/gate-scripts-manifest.txt` (9 membros, REGENERADO do
vivo no G5). 4 workflows ganharam o step fail-loud; RELEASE.md 31→32;
contagem 192→194 nas 10 superfícies do verify-counts. G1-G7 verdes.
Dois abortos ANTES do land, ambos pegos por gate e curados por item:
- G1 (anti-stale) — o pack foi montado ANTES do closeout `c745f02`, que
  editou o CLAUDE.md vivo. Cura: item CLAUDE.md re-staged sobre o vivo
  (delta = só o bump), BASELINE/MANIFEST re-pinados (`fc587ff`).
- G4 (rc agregado — a cura do follow-up do W3 acima, FUNCIONOU) —
  verify-counts vermelho: o bump cobria 7 superfícies, o gate vigia 10
  (faltavam ARCHITECTURE, docs/README, header do CHANGELOG). Cura: 3
  targets + TARGETS/Scope estendidos (`aa6462b`). Classe: conjunto
  fechado escrito de memória — derivar do gate, não recordar.
- Itens 5-6 desta wave saem de PARCIAIS para DONE. `staged-w3/pending-w28/`
  é histórico (o RELEASE.md landou por este trem).

### Registro de execução — W3-K LANDADA (S313→S314, 2026-08-19, commit `c34e8e3`)

Cerimônia de kernel executada em sessão própria (U-3), sentinel
`PLAN-169/W3K-approved.md.asc` assinado 2026-08-19 00:25. O que landou:

- `check_arbitration_kernel.py:540` — `ceremony_sha=_file_sha256(file_path)`
  (o campo recebe o sha256 REAL do arquivo, nunca mais um path truncado);
- `veto_triggered reason_code=kernel_override_used` wired de verdade
  (`:556`, `:609`, `:822`) — a condição que `git log -S` mostrou ter
  nascido morta agora dispara pelo `main()`;
- teste positivo do emit de GRANT em
  `.claude/hooks/tests/test_arbitration_kernel_grant_emit.py`.

Follow-ups do trem: a classe bare-testcase introduzida pelo próprio teste
novo (`AssertionsHaveTeeth` sem `TestEnvContext`) foi pega pelo agendado
`coverage.yml` de 2026-08-19 e curada em `9179ef2` — registro honesto: o
`validate.yml` do push `c34e8e3` foi **cancelled** por `cancel-in-progress`
(trem de pushes), não success; o primeiro gate a executar até o fim foi o
cron do coverage. Ledger E.2 vira CLOSED nesta entrada; E.7 segue como o
único OPEN (W4-C).

### W3-K — Cerimônia de kernel (E.2) (L3+, escopo próprio)

> **CORREÇÃO (S313, 2026-08-18) — a hipótese abaixo foi FALSIFICADA por
> reprodução hermética.** `kernel_extension_landed` **não** é engolido: a ação
> está em `_EMIT_GENERIC_PASSTHROUGH` (`audit_emit.py:1751`) e o evento LANDA
> intacto (`hmac_error: null`). O `except Exception: pass` nunca dispara.
> O defeito REAL é outro evento e outro mecanismo: `veto_triggered
> reason_code=kernel_override_used` nunca foi escrito porque `main()` decide o
> caso do grant com `decision == "allow"`, lendo `decision` do JSON que o
> PRÓPRIO `_emit_allow()` produziu — chave que ele nunca escreve. `git log -S`
> mostra que a condição **nasceu morta**. O teste que parecia cobrir isso
> chama `_audit_block` direto, contornando `main()`. Pack: `staged-w3k/`;
> sentinel: `W3K-approved-draft.md`. Mantido o texto original abaixo como
> registro do que se acreditava.

- ~~Emits do caminho GRANT do `check_arbitration_kernel.py` são
  silenciosos (engolidos por `except Exception: pass`; suspeita:
  `ceremony_sha` recebe PATH, não sha 64-hex).~~ Fix do schema dos
  kwargs + **teste POSITIVO do emit de grant** (hoje só o block é
  provado). Sentinel/escopo separados do W3 — e **SESSÃO SEPARADA do
  W3 (U-3):** editar kernel exige `CEO_KERNEL_OVERRIDE` +
  `CEO_KERNEL_OVERRIDE_ACK` além do sentinel; duas cerimônias com
  posturas de override diferentes na mesma sessão é onde um `export`
  sobra no ambiente (alternativa mínima: assert de ambiente limpo
  entre as duas).

### W4 — Evolução do substrato (1-2 sessões)

> Design fundamentado na pesquisa de substrato S298 (arquivada — ver
> `PLAN-169/research-README.md`);
> os itens abaixo são o compromisso — parâmetros finos podem ajustar
> com o relatório sem mudar escopo.

**W4.1 — Acionador de quota 5h (quota-resume) — pedido explícito do Owner.**
> Re-arquitetado pelo round 1 (MF-4/MF-5 + R-SEC2/3/4).
- **Propriedade COMPRADA (declarada):** *"sessão VIVA e ociosa retoma
  sozinha no reset da quota"* — via cron do harness (session-scoped,
  in-memory). **LIMITAÇÃO DOCUMENTADA:** o job morre com o processo;
  "retomar com terminal fechado" é OUTRO produto (scheduler de SO +
  `claude -p` / routines cloud) e fica FORA da v1.4.0, registrado como
  candidato futuro.
- **W4.1.0 — Probes primeiro (mesma disciplina do W4.2.0):** (i) o
  hook `StopFailure(rate_limit)` dispara de fato no estouro da quota
  de 5h? (ii) o snapshot do sidecar está fresco NAQUELE instante?
  (iii) o que exatamente sobrevive/morre com o terminal? Live-fire
  registrado com evidência ANTES de qualquer doc.
- **Fonte de dados (JÁ EXISTE):**
  `rate_limits.five_hour.{used_percentage, resets_at}` parseado por
  `statusline-ceo.py:25,111`; sidecar atômico em
  `<audit-dir>/state/statusline-snapshot.json` (`statusline-ceo.py:131`,
  wired em `.claude/settings.json:925`). Trabalho novo = consumidor.
- **Arquitetura (quem faz o quê — um hook NÃO cria cron do harness):**
  - **[codex r6-P1] O gatilho que ARMA de verdade:**
    `check_quota_resume.py` é um hook **PostToolUse/PostToolBatch**
    (predicado barato: snapshot lido com cache de mtime) que, ao ver
    quota verificada ≥90% SEM job armado (marker de estado), **INJETA
    instrução no transcript** ("quota ≥90%, resets_at=X verificado —
    agende o one-shot AGORA") — o modelo VIVO a lê entre tool calls e
    chama CronCreate no mesmo turno. É o único caminho que alcança o
    caso "turno autônomo longo cruza o threshold sem turno novo
    depois". **[Sec r2-R-SEC13] O texto injetado é TEMPLATE CONSTANTE
    que interpola SÓ inteiros já validados (percentual, epoch) —
    nenhuma string do snapshot entra na instrução; doutrina no ADR:
    texto injetado por hook é instrução do framework, nunca relay de
    conteúdo externo.** Testes [VP r2-MF-C — o aceite mede o ARM, não
    o stdout]: unit = fixture ≥90% ⇒ output contém a instrução (<90%
    ou job armado ⇒ silêncio); **end-to-end = hook dispara ⇒
    exatamente UM job EXISTE no horário efetivo; controle negativo ⇒
    NENHUM job novo.**
  - **ARM preventivo (o mecanismo real):** o MODELO arma **no
    PRIMEIRO turno em que o snapshot verificado cruza o THRESHOLD
    ÚNICO** (default 90%, `CEO_QUOTA_RESUME_PCT` configurável — um só
    número, decisão OQ-2; sem 2º threshold "obrigatório") — agenda já
    o one-shot provisório para o `resets_at` corrente (re-arma/cancela
    se `resets_at` mudar; idempotente por `resets_at`).
    **[codex r4-P1] Por que cedo:** entre o threshold e a exaustão
    pode NÃO haver outro turno — armar "quando estourar" é armar
    nunca (StopFailure não agenda). **Guard de no-op no prompt de
    retomada:** se ao disparar NÃO houver evidência de exaustão
    (breadcrumb do StopFailure / estado), responder literalmente
    "quota-resume: no-op" e parar — armar cedo não cria turno
    autônomo útil-espúrio. **Propriedade estreitada (declarada):** se
    a quota estourar SEM nenhum turno entre o cruzamento do threshold
    e a exaustão, a retomada automática não terá sido armada — o arm
    aos 90% torna essa janela pequena, não nula. **[codex r3-P1 → REVISTO pelo r11-P1: a rota de
    assinatura foi DESCARTADA — entre processos do MESMO UID não há
    autenticação local confiável; `statusline-ceo.py` aceita stdin
    arbitrário, e assinar na escrita criaria um ORÁCULO (um agente com
    Bash geraria HMAC válido para valores forjados). Fronteira de
    confiança declarada [afinada pelo r15-P1]: entre processos do
    MESMO UID não existe origem inforjável — um adversário com Bash
    pode forjar snapshot E breadcrumb; para ele, o quota-resume não
    adiciona capacidade nova (quem executa Bash já controla a sessão
    e faria o trabalho diretamente). Os controles abaixo defendem
    contra ERRO E CORRUPÇÃO (dado ruim, estado velho, relógio torto),
    não contra adversário local — e o plano NÃO afirma garantia
    anti-adversário nenhuma para este mecanismo.]** Controles, nesta ordem:
    (1) **sanity-check de banda fail-closed DECIDE o horário** —
    `resets_at` futuro E dentro de 5h+margem; fora ⇒ não arma, avisa,
    registra; (2) **no-op guard no DISPARO é o controle load-bearing**
    — o prompt de retomada só trabalha se houver evidência de exaustão
    gravada pelo caminho HARNESS-INVOCADO (breadcrumb do hook
    `StopFailure`), **e a evidência é AMARRADA e CONSUMIDA [codex
    r12-P1]: ligada ao `session_id` e ao `resets_at` corrente, com
    **janela de validade que INCLUI o disparo agendado [codex r13-P1:
    expirar NO reset tornaria a evidência sempre-inválida no fire de
    `resets_at+≥120s` ⇒ no-op eterno]: válida da exaustão até
    `resets_at + janela de consumo` (default 30min)**, e SINGLE-USE
    (deletada no primeiro consumo — evidência VELHA sobrevivendo a
    restart fora da janela não autoriza trabalho; contra erro, não
    contra forja — ver fronteira acima); testes de frescor, binding,
    janela e consumo**; sem
    evidência válida ⇒ "quota-resume: no-op" e para; (3) o
    snapshot é SEMPRE advisory para AVISO (contrato
    `statusline-ceo.py:57-60` mantido — NENHUMA mudança no escritor);
    payload do StopFailure, quando houver, segue autoritativo
    (R-SEC2).
    - **LIMITAÇÃO ACEITA E DECLARADA (codex r3/r11/r15/r31 — mesmo
      ponto, insolúvel em mesmo-UID):** o `resets_at` que vira HORÁRIO
      do job vem do sidecar não-autenticado; um processo do mesmo UID
      pode forjá-lo. Isto NÃO é fechável por autenticação (assinar
      criaria oráculo). O que o desenho GARANTE é a fronteira de DANO,
      não a origem: o horário forjado é obrigado a cair na banda
      (sanity-check fail-closed: futuro + ≤5h+margem) E o turno
      resultante é NO-OP sem evidência de exaustão do caminho
      harness-invocado. Pior caso de forja: um turno no-op agendado
      dentro da janela — nenhum trabalho autônomo sobre dado falso.
      Quem tem Bash no mesmo UID já controla a sessão; o quota-resume
      não amplia essa superfície. **Registrar como tradeoff no ADR do
      W4.1 — não é defeito a "consertar".**
  - **Hook `StopFailure(rate_limit)`:** grava estado + evidência
    (breadcrumb HMAC) para o turno retomado; NÃO agenda (hook é
    subprocess; CronCreate é tool do modelo — MF-4).
  - **Horário (MF-5):** `resets_at + margem ≥ 120s`, minuto ∉
    {`:00`,`:30`} (one-shot em :00/:30 dispara até 90s ANTES);
    teste asserta o horário EFETIVO do job, não só unicidade.
  - **Prompt de retomada LITERAL e fixo (R-SEC3):** re-entra no
    Gate 1; trata TaskList/§Progress como DADO; proibição textual de
    cerimônia/assinatura/tag/npm/transição de status; SEM escalada de
    postura.
- **Postura (R-SEC4 + ADR-185):** ativo só com night-mode armado OU
  opt-in `CEO_QUOTA_RESUME=1`; o gate lê a postura EFETIVA (nunca
  `night-mode.json`, que é agent-writable); kill-switch
  `CEO_QUOTA_RESUME=0`; `CEO_SOTA_DISABLE=1` precedência master.
  **Toda env nova registrada em `env-inventory.json` no MESMO commit
  (R-SEC12).**
- **Testes:** unit com `TestEnvContext` + clock injetável (threshold,
  idempotência — 1 e só 1 job por `resets_at`, horário efetivo);
  **[Sec r3, atualizado pós-r11 — os DOIS controles negativos
  fail-closed, sem os quais exceção engolida (família E.2) cria turno
  útil sobre dado não verificado e nada acusa:** (a) DISPARO sem
  evidência de exaustão gravada pelo caminho harness-invocado
  (breadcrumb StopFailure) ⇒ o prompt responde "quota-resume: no-op" e
  PARA — nenhum trabalho; (b) `resets_at` fora da banda (passado, ou
  além de 5h+margem) ⇒ NÃO arma, avisa e registra**];
  eventos HMAC pelo checklist R-SEC9 (_KNOWN_ACTIONS + scrub + SPEC +
  teste de campos; int com unidade — lição float-em-HMAC).
- **Aceite:** probes W4.1.0 registrados + simulação (job único no
  horário certo) + **live-fire e2e real (StopFailure dispara →
  evidência consumida → trabalho útil retoma). [codex r13-P1] SEM
  live-fire GO, o quota-resume embarca na v1.4.0 como EXPERIMENTAL —
  nunca "supported" (a simulação prova criação de job, não o ciclo);
  o registro falsificável de "por que não" rebaixa o rótulo, não o
  aceite.** Doc promete EXATAMENTE o que o teste provou.

**W4.2 — Governança cross-session (fleet-ready).**
> Fatos do substrato (research §2.1, doc oficial): mensagens = SÓ
> texto plano (nunca history/files); entrega Delivered/Held/Refused;
> guardrails anti-laundering existem mas são modelo+classifier
> (probabilísticos); **o caminho de RECEBIMENTO não tem evento
> DEDICADO de hook — e o caminho GENÉRICO segue NÃO VERIFICADO
> [rebaixado S315 pelo pair-rail r2: a redação anterior dizia "NENHUM
> evento de hook", forte demais; se a mensagem de peer superficiar via
> `UserPromptSubmit`, esta premissa e toda a caracterização de
> proveniência abaixo mudam]** — SE nenhum hook cobrir o caminho,
> inbound pode iniciar turno sem gate e sem registro HMAC (buraco de
> PROVENIÊNCIA, não de autorização — a parede PreToolUse continua
> valendo para o que a mensagem induzir). **Resolvido só pelo probe
> (a), ainda não rodado.**
- **W4.2.0 — Probes empíricos ANTES de qualquer desenho (perguntas de
  maior alavancagem da pesquisa, ~minutos cada):** (a)
  `UserPromptSubmit` dispara para mensagem de peer? (decide se
  `refuse` é mitigação ou ÚNICA defesa); (b) `SubagentStart` dispara
  para `agent()` de Workflow? — **evidência preliminar S298 (audit
  log): os 7 `agent()` do workflow de inventário geraram
  `subagent_lifecycle_observed` (lado Stop, archetype `other`,
  12:31-12:38 UTC) e ZERO `agent_spawn`/`spawn_prompt_defense_gate` —
  o gate de spawn NÃO intercepta o caminho Workflow; resta confirmar o
  evento Start.** Consequência: documentar e recomendar
  `disableWorkflows: true` como default fail-closed PARA ADOPTERS até
  existir gate, com a exceção operador-supervisionado registrada;
  (c) cross-machine send (doc diz reply-only; changelog 2.1.225 diz
  name-first) — testar; **(d) [Sec-U1] `refuse` também recusa
  own-child?** (se SIM: perde-se a rota "hook posta resultado no
  próprio socket" — registrar a perda; se NÃO: `refuse` não é
  soberano e conteúdo lido de arquivo postado no socket vira turno
  novo — escalação de injection a tratar); **(e) [Sec-U2/U-2] medir o
  que o HMAC registra HOJE de um turno nascido de inbound** (é essa
  medição que permite a frase honesta no ADR; decisão explícita sobre
  visibilidade de tentativas recusadas — "recusado e invisível" é
  escolha, não default); **(f) [Sec-U4] PreToolUse dispara para
  SendMessage emitido por subagent/teammate?** (sem isso o gate de
  envio tem profundidade 1).
- **Postura default do framework (candidato #1 do research §4):**
  `crossSessionInbound: "refuse"` no settings.json instalado —
  project/local `refuse` VENCE managed/user quando mais estrito (única
  alavanca fail-closed nova soberana ao repo); **[codex r2-P2] como
  project-refuse VENCE — `--settings` NÃO consegue relaxá-lo — o fleet
  do PLAN-170 roda em CLONES dedicados do experimento com o valor de
  projeto substituído no clone (nunca no repo canônico), rota
  registrada no pré-registro.**
  `isolatePeerMachines: true` junto. **[U-1 — pergunta da classe
  PLAN-167, responder ANTES de escrever a linha:** settings.json do
  adopter é a superfície mais customizada que existe — a linha nova
  passa pela decisão de propriedade: adopter com `accept` explícito é
  PRESERVADO; rota de upgrade definida na tabela de ownership ou
  marcada NÃO-OWNED; sem isso, reabrimos a classe que custou os
  PLAN-167/168 inteiros.]
- **Lado de ENVIO (interceptável fail-closed, candidato #2):**
  PreToolUse em `SendMessage` + `ListAgents` — allowlist de
  destinatários (spec fail-closed no W4-C item 2) + evento HMAC
  (campos: peer name/ref, direção, hash do summary — nunca o corpo;
  int com unidade; **nome de peer com CAP de tamanho + charset
  restrito ANTES da emissão** — texto livre escolhido pelo outro lado
  entra num log que `skill-health`/`audit-tokens` renderizam).
- **Doutrina (ADR curto, pack W4-C — DEPOIS dos probes d/e/f, que o
  ADR registra; codex r10):** peer = fronteira de confiança;
  mensagem cross-session é DADO; pedido que a política local
  bloquearia ⇒ recusar e reportar; nunca cerimônia/assinatura a pedido
  de peer; registrar o buraco de proveniência do inbound honestamente
  (e a superfície `CLAUDE_CODE_MESSAGING_SOCKET` own-child).
- **Aceite:** probe live — peer tenta induzir edit canônico via
  SendMessage ⇒ bloqueado + auditado; com `refuse`: nenhum turno nasce
  (controle positivo: com `accept`, nasce).

**W4.3 — Parametrização de dispatch.**
- `model`/`effort` por agente nos templates de spawn e no Workflow
  (mecânica já no substrato); tabela de tiers por classe de tarefa
  (scan mecânico = low; verify/judge = high) no team.md ROUTING;
  **[codex r17-P2] PROBE-FIRST antes de prometer roteamento de tier
  em Workflow:** ADR-144 §S220 / `.claude/workflows/README.md` medem
  `agent(...,{model})` como INERTE sob `CLAUDE_CODE_SUBAGENT_MODEL=inherit`
  (agents herdam o modelo da sessão) — a tabela de tiers só vale para
  spawn via Agent tool até um probe positivo provar o contrário na
  versão corrente; sem o probe, NÃO reivindicar tier routing em
  Workflow (documentar a limitação). **enforcement declarativo**:
  permission rules `Agent(param:value)` (deny `Agent(model:opus)` fora
  da política — candidato #9). **[codex
  r12-P2] Rule sozinha NÃO fecha a política: chamada SEM `model`
  herda o modelo do main loop (Opus) e nenhuma rule casa com parâmetro
  ausente — o fechamento é DUPLO: a rule para valores explícitos + o
  gate de spawn (`check_agent_spawn.py`) exigindo `model` EXPLÍCITO em
  spawn de arquétipo (omissão ⇒ block, com controles de omissão e
  `inherit` plantados).** A política de tier (ADR-052/064) sai de
  instrução-ao-modelo para substrato fail-closed; audit registra tier
  efetivo (check `tier_policy_misrouting_24h` já existe).
- **Fleet-currency — a parte de DECISÃO (auditoria Fable S298,
  `PLAN-169/fleet-currency-audit-S298.md`; os fixes de DADOS livres
  estão no W2.10):** (i) **F1-P1**: `set-quality-profile.sh` pina os 5
  canônicos em literais 4.x — qualquer invocação (até `max-quality`)
  reverte os VETO holders de fable-5→opus-4-8 SEM nenhum hook disparar
  (downgrade de 2 gerações, legal perante o floor N-1); decisão: alvo
  dos perfis na geração corrente + mapa DERIVADO da autoridade
  ADR-149; (ii) F5: enum `MODEL_ID`+loader do tier-policy REJEITAM
  `claude-opus-5` (contrato do artifact — pack); (iii) F6: baseline do
  template de adopter regenerada na geração corrente; (iv) dimensão
  **fleet-currency** no nightly-hygiene (manifesto de superfícies
  portadoras de model-id + oracle por superfície, padrão
  ADR-149-parity); (v) D4/D5 (team.md e o SKILL.md do próprio FinOps
  ensinam a frota antiga) — Gate-1/2 cache-stable, editar em closeout
  junto do pack W4-C.

**W4.4 — Hardening contra breaking-drift do substrato (research §3,
RE-ESCOPADO PELO DISCO — MF-6; de "wave indefinida" para horas).**
- **P0 (número real): matchers hifenizados = 2** (ambos
  `mcp__codex__codex|mcp__codex__codex-reply`, PreToolUse+PostToolUse
  — o rail cross-model): controle positivo de disparo + **controle
  RECORRENTE em CI** (Sec-Unseen3: a semântica de matcher mudou 3× em
  6 semanas; auditoria one-shot re-apodrece). Classes vírgula e `if:`
  = **vacuosas neste repo (0 ocorrências)** — registrar e não gastar.
  Inversão exit-2 (2.1.214): alvo real = **2 arquivos**
  (`check_harness_config.py` + `_python-hook.sh`; VP r2 verificou:
  `grep -rl 'sys.exit(2)' .claude/hooks/*.py` = 0) — verificar
  direção do veredito em cada um.
- **`ConfigChange`: PROMOVER, não adicionar** — o guard JÁ EXISTE
  (PLAN-135 W2 H2, fail-open advisory-block). Item honesto: decidir e
  executar a promoção advisory→bloqueante (decisão de doutrina
  fail-open-infra vs fail-closed-input embutida); documentar
  `policy_settings` como exceção não-bloqueável.
- **Pinagem de versão do substrato:** `requiredMinimumVersion` /
  `requiredMaximumVersion` (doc para adopters em managed scope; para o
  meta-repo, registro do range testado em `SBOM.md`/substrate-watch) —
  profundidade de aninhamento mudou 3× em 6 semanas; asserção fixa é
  frágil por construção.
- **`--append-subagent-system-prompt`** com o preâmbulo do spawn
  protocol: fecha o gap de governança em subagents aninhados
  (profundidade 2-3) sem depender de cada prompt carregar as 3 seções.
- **`PostToolBatch`** como modernização do overhead-guard (1 hook por
  batch, pode bloquear) — caminho primário do W3.3.
- **`TaskCompleted` hook (exit 2)** ligado a gate: "não marca done com
  gate vermelho" vira substrato (candidato #3).
- **DEFER explícito com causa:** channels (research preview; sender de
  channel em modo relay pode APROVAR tool use — única superfície da
  janela que aprova em vez de pedir; incompatível com o modelo de
  consentimento até gate próprio). Registrar em substrate-watch.
- **Vigiar (substrate-watch, sem ação agora):** `.claude` protected
  path (allow rules não pré-aprovam escrita); tendência do substrato
  de mover config sensível de escopo repo → user/managed (risco
  estratégico para um framework instalado via `.claude/settings.json`);
  `isolation: "remote"` não modelado no gate de spawn.

### Registro de execução — W4 ABERTA: bloco de probes de disco (S315, 2026-08-20)

**Decisão do Owner (AskUserQuestion, S315), verbatim:** "PLAN-169 W4
(Recomendado) — Abre a wave de substrato: W4.1 quota-resume (probes
live-fire primeiro), W4.2 guard SendMessage/ListAgents, W4.3 decisão
fleet-currency. É o gargalo de 170, 174, 176 e 181. L2/L3 — o
enforcement vai para o W4-C com cerimônia GPG sua. Herda explicitamente
o W1.3 (scoped permissions) do 178."

Executado o que o próprio W4 manda executar primeiro (W4.1.0, W4.2.0,
probe-first do W4.3): a fatia verificável em DISCO, read-only, $0.
**Ressalva do W4.3 [pair-rail r3] — FECHADA em S316 (2026-08-20):** o
probe exigido FOI rodado no harness 2.1.237 (`wf_9ddadaab-12f`, 2
agentes): com `opts.model='haiku'` o modelo SERVIDO nos turnos do
transcript foi `claude-haiku-4-5-20251001`; o controle sem override
herdou `claude-fable-5` (evidência: `agent-a3fbe640....jsonl` /
`agent-a8dea319....jsonl` + `.meta.json`, campo model do envelope de
resposta — servido, não pedido). **Veredito: `agent(...,{model}) NÃO é
mais inerte — o rail Workflow ROTEIA modelo na versão corrente.** A
limitação do ADR-144 §S220 envelheceu e precisa de emenda quando o
W4.3 executar (a claim "opts.model é INERTE" citada no AC-3/178 e na
skill eval-baseline-n20 herda esta atualização). Tier routing em
Workflow passa a ser reivindicável APÓS a emenda do ADR-144.
Probes que exigem duas sessões vivas ou estouro real de quota ficam
nomeados abaixo como operador-dependentes — não foram simulados nem
inferidos.

**W4.1.0 — sidecar (probe ii): EVIDÊNCIA DE PRÉ-VOO, não GO.**
**[reclassificado pelo pair-rail r2]** O probe (ii), como definido,
pergunta se o sidecar está fresco **no instante de uma falha real de
quota de 5h**. A medição abaixo foi feita em operação NORMAL, com
`used_pct: 4.0` — prova que o escritor e o schema existem e que o
formato é o esperado, **não** que o snapshot continua atual quando as
requisições começam a falhar. O (ii) só fecha no live-fire de exaustão,
junto com (i) e (iii).
`~/.claude/projects/ceo-orchestration/state/statusline-snapshot.json`,
idade 0,0 min no momento da medição, `rate_limits.five_hour =
{resets_at: "1787238000", used_pct: 4.0}`. O dado que o W4.1 precisa
existe e está fresco.

- **Armadilha de contrato NOMEADA (achado do probe).** O corpo desta
  wave cita `rate_limits.five_hour.{used_percentage, resets_at}`. Isso
  descreve a **ENTRADA** do statusline. A **SAÍDA** do sidecar — que é
  o que o consumidor novo do W4.1 lê — normaliza para **`used_pct`**
  (`statusline-ceo.py:221`), e `resets_at` sai como **str**, não int.
  Um consumidor escrito contra `used_percentage` lê `None`, nunca
  cruza o threshold e **arma nunca**, silenciosamente. O ADR do W4.1
  registra: entrada != saída; derivar do contrato do ESCRITOR, nunca
  do nome citado em prosa. Classe conhecida (conjunto fechado escrito
  de memória).
- Probes (i) `StopFailure(rate_limit)` dispara no estouro real? e
  (iii) o que sobrevive ao fechar o terminal? — **operador-dependentes**
  (exigem estourar a quota de 5h e matar o terminal). Não executados.

**W4.2.0 — substrato e wiring.**
- Enum de eventos (`.claude/data/hook-schema-2.1.220.json`): 31
  eventos. `StopFailure` EXISTE, contrato de entrada `{error: enum,
  error_details?, last_assistant_message?}`. `PostToolBatch` e
  `TaskCompleted` também existem.
- Não há evento **DEDICADO** de recebimento de mensagem cross-session
  no enum. **[REBAIXADO pelo pair-rail codex r1 — INCONCLUSIVO, não
  confirmação]** A primeira redação dizia que isso "confirma por
  construção" o buraco de proveniência do inbound. Não confirma:
  ausência de evento DEDICADO não prova ausência de TODO hook — o
  runtime pode superficiar a mensagem pelo `UserPromptSubmit` genérico,
  que é precisamente o **probe (a) ainda não rodado**. Registrado como
  INCONCLUSIVO até o probe vivo. É a lição já registrada em memória
  ("sonda de EVENTO não é sonda de CANAL") aplicada contra o meu
  próprio resultado.
- Wiring vivo em `.claude/settings.json` — **15 eventos, 49
  registrações, 47 scripts distintos** [contagem corrigida pelo
  pair-rail r4: a redação anterior dizia "47 hooks", colando o número de
  SCRIPTS no lugar do de REGISTRAÇÕES; 49 é o que bate com
  `docs/COMMAND-SKILL-HOOK-MAP.md:132`]:
  `StopFailure` **AUSENTE**, `PostToolBatch` **AUSENTE**,
  `TaskCompleted` **AUSENTE**, `ConfigChange` **PRESENTE** — confirma a
  instrução do W4.4 ("PROMOVER, não adicionar").
- `crossSessionInbound`, `isolatePeerMachines`, `disableWorkflows`:
  **nenhum definido** hoje. A postura default do W4.2 é trabalho novo,
  não ajuste.
- Probe (b) — censo do log vivo (12.085 linhas): `agent_spawn` = 0 e
  `spawn_file_assignment_recorded` = 0. **INCONCLUSIVO POR VACUIDADE**:
  não houve named spawn na janela (ceo-boot mediu 0 dispatches/24h),
  então zero-eventos não distingue "o hook não intercepta" de "não
  houve o que interceptar". A evidência S298 do gap segue valendo; este
  censo NÃO a reforça.
- Probes (a) `UserPromptSubmit` para mensagem de peer, (c) cross-machine
  send, (d) `refuse` recusa own-child?, (f) PreToolUse para SendMessage
  de subagent — **operador-dependentes** (exigem duas sessões vivas).

**W4.4 P0 — os números do plano reconferidos no disco.**
- Matchers hifenizados = **2**, confirmado: `settings.json:291` e
  `:472`, ambos `mcp__codex__codex|mcp__codex__codex-reply`. Número do
  plano bate.
- `grep -rl 'sys.exit(2)' .claude/hooks/*.py` = **0** — medição do VP r2
  reconfirmada.
- **Drift de schema a fechar antes de desenhar:** o enum foi extraído da
  **2.1.220**; o substrato vivo é **2.1.237** (17 patch releases). O W4
  não deve desenhar contra o enum capturado sem re-captura.

**W4.4 — RE-CAPTURA DO ENUM NA 2.1.237: EXECUTADA (S315).** Extraída
do bundle vivo (`~/.local/share/claude/versions/2.1.237`, Mach-O arm64
317 MB, mesmo método do PLAN-163 T2.2: carve do segmento JS, símbolo
`V6`). **Resultado: o enum é IDÊNTICO ao capturado na 2.1.220 — 31
eventos, MESMA ORDEM, zero adições, zero remoções.** Os 17 patch
releases não tocaram o conjunto de eventos. Consequência prática: o
desenho do W4 PODE usar o enum capturado; o drift que o plano temia
não se materializou nesta dimensão. **Isto NÃO se auto-preserva** — a
lição Sec-Unseen3 (a semântica de matcher mudou 3× em 6 semanas) vale
aqui igual: a checagem vira controle RECORRENTE em CI junto com o dos
2 matchers hifenizados, nunca auditoria one-shot.

**W4.1 — TRÊS FATOS DE DESENHO extraídos do bundle vivo (estáticos, sem
precisar estourar a quota).** O disparador do `StopFailure` no binário
2.1.237 é:

```js
let i = e.error ?? "unknown";
let s = {...., hook_event_name:"StopFailure", error:i,
         error_details:e.errorDetails, last_assistant_message:o};
await wU({..., hookInput:s, timeoutMs:r, matchQuery:i})
```

1. **O `matcher` do hook `StopFailure` casa contra o VALOR DE `error`,
   não contra nome de tool** (`matchQuery: i`, onde `i` é o `error`).
   **Crédito onde é devido (autocorreção):** isto NÃO é descoberta
   nova — o snapshot do próprio repo já registrava
   `"StopFailure": "error"` em
   `matcher_semantics.matcher_query_field_by_event_verified`. A
   extração do bundle 2.1.237 é uma **confirmação independente** (dois
   métodos, duas versões, mesmo resultado); o que faltou foi o fato
   VIAJAR do snapshot para o corpo da wave. A registração do W4-C item 1 tem de usar
   `"matcher": "rate_limit"` — um matcher de tool ali nunca dispararia,
   e o modo de falha seria silêncio total.
2. **O valor é `rate_limit`**, confirmado no mapeador de erros
   (`zNv`): `e instanceof Ms && e.status===429` ⇒
   `qd({content:..., error:"rate_limit", quotaLimits: osf(e)})`.
3. **`quotaLimits` NÃO chega ao hook.** O `hookInput` do StopFailure
   copia SOMENTE `error`, `error_details` e `last_assistant_message` —
   o objeto que carrega `quotaLimits` é a MENSAGEM, não o payload do
   hook. Ou seja: **o hook não recebe `resets_at`**. Isso CONFIRMA o
   desenho do plano (o horário vem do sidecar; o payload do
   StopFailure é autoritativo apenas como EVIDÊNCIA DE EXAUSTÃO,
   R-SEC2) — mas por uma razão que o plano não tinha: não é escolha,
   é a única opção.

**FALSO-POSITIVO DE DESENHO descoberto na mesma leitura (cura
obrigatória antes do W4-C item 1).** `error:"rate_limit"` **não é
exclusivo de estouro de quota**: o mesmo valor é emitido quando um
modelo está indisponível — `Pt instanceof Ire && Pt.reason ===
"model_blocked"` ⇒ `qd({content: "<modelo> is currently unavailable.",
error:"rate_limit"})`. Como é o hook `StopFailure` que grava o
breadcrumb de exaustão, um `model_blocked` faria o hook gravar
evidência de exaustão que NUNCA houve — e o turno de retomada acordaria
sobre premissa falsa, exatamente o que o no-op guard existe para
impedir (mas não impede, porque a evidência estaria lá, válida e
fresca). **Cura exigida [endurecida pelo pair-rail codex r1 — a
primeira redação era furada]:** a primeira versão dizia "cruzando com o
sidecar (`used_pct` alto) **e/ou** classificando `error_details`" — o
"e/ou" AUTORIZA o ramo sidecar-só, e é exatamente aí que o falso-positivo
sobrevive: **quando `used_pct` JÁ está acima do threshold, um
`model_blocked` satisfaz o ramo do sidecar**, o hook grava exaustão
falsa e o job armado passa pelo no-op guard. O discriminador tem de ser **INDEPENDENTE do nível
de uso** E **ESPECÍFICO da janela de 5h** [endurecido de novo pelo r2]:
"evidência de 429" NÃO basta — no MESMO bloco `zNv` do 2.1.237, 429
genérico/transitório e falhas de crédito de uso também mapeiam para
`error:"rate_limit"`. Exige-se **identificação POSITIVA de exaustão da
janela de 5h**, com fixture negativa para CADA outro ramo que produz
`rate_limit` (model_blocked, 429 genérico, crédito) — nunca "ou". **E o controle negativo tem de usar snapshot de uso ALTO** —
uma fixture de `model_blocked` com quota baixa passa por acidente e não
prova nada. Sem isso, o W4.1 embarca um gerador de turnos autônomos
espúrios.

**Achado P0 de governança, FORA do escopo do W4 — destino: decisão do Owner.**
O audit dir cai, sem env, num **literal hardcoded**
`$HOME/.claude/projects/ceo-orchestration/` (`_lib/audit_hmac.py:182` e
`_lib/audit_emit.py:2298`). **A precedência de env NÃO é compartilhada**
[corrigido pelo pair-rail r6 — a redação anterior afirmava a cadeia
`LOG_DIR → LOG_PATH → STATE` como se valesse para todos]: só
`audit_hmac._audit_dir_from_env` segue as três; `audit_emit` usa
`LOG_PATH` apenas para o arquivo de log e `LOG_DIR`/`HOME` para dir,
lock e errors — sob `STATE`-only ou `PATH`-only a cadeia única é FALSA e
faria o operador crer que a família inteira está isolada. A matriz por
artefato vive no `PLAN-182` W0-US2. Consequência MEDIDA, não
hipotética: **1.534 eventos de um SEGUNDO projeto do mesmo operador
(identificador redigido)** — que tem o framework instalado — estão
gravados no audit-log DESTE repo, janela
`2026-08-19T21:17Z` -> `2026-08-20T11:58Z` (**ativo agora**). O número
de eventos locais que esta entrada citava (**310**) foi medido de novo e
**não reproduz** — a soma verificada na janela é **302**, e o histograma
completo (cinco rótulos distintos, DOIS tenants estrangeiros, este repo
sob dois rótulos) está no `PLAN-182` §1. Correção do pair-rail r7:
deixar os dois números na história canônica de planejamento tornaria a
evidência forense contraditória consigo mesma.
Inclui eventos de segurança: `env_var_hijack_blocked` (28),
`veto_triggered` (3), `git_hook_bypass_blocked` (1),
`output_scan_finding_suppressed` (841). Duas consequências distintas:
(1) **dogfood** — as métricas de governança deste repo (ceo-boot,
audit-tokens, skill-health) medem uma MISTURA de projetos, e a cadeia
HMAC encadeia eventos de projetos diferentes; (2) **adopters** — dois
adopters no mesmo `$HOME` sem env explícita compartilham o mesmo log E
a mesma chave HMAC. Não tocado nesta sessão: resolução de audit dir é
superfície de governança e a cura precisa de destino declarado (wave
própria aqui, ou plano próprio).


### W4-C — Cerimônia de substrato (L3+, pack GPG próprio, escopo FECHADO — MF-2)

> Todo o ENFORCEMENT do W4 mora em superfície canônica. Este é o slot
> de cerimônia dele — escopo fechado AGORA; item que não está na lista
> abaixo NÃO entra neste pack (vira wave nova ou plano novo). A
> recomendação alternativa do VP (W4 inteiro → PLAN-170) foi
> registrada e recusada no consensus §2: o mandato do Owner é um plano
> que fecha e publica.
>
> **[AMENDADO S315 — decisão do Owner, registrada]** O escopo foi
> ampliado UMA vez, por UM item: **9** (W1.3 scoped permissions,
> herdado do PLAN-178). Uma segunda ampliação foi PROPOSTA e RETIRADA
> na mesma sessão — isolamento do audit dir — quando a varredura
> comportamental mostrou 63 módulos em vez dos 2 que a proposta
> alegava; virou `PLAN-182`. Registro honesto do porquê: a decisão de
> absorver foi tomada sobre um número errado, e o número certo a
> inverteu. "FECHADO" continua valendo para todo o resto.

Escopo exaustivo:
1. Hook novo `check_quota_resume.py` (W4.1) + registração no
   `settings.json`.
2. Hook novo PreToolUse `SendMessage`/`ListAgents` (W4.2, R-SEC5/7:
   default-deny, nome não autentica, não-classificável ⇒ block, infra
   ⇒ `{}`) + registração.
3. Linhas `crossSessionInbound: "refuse"` + `isolatePeerMachines:
   true` em **TODAS as superfícies de entrega [codex r3-P1 + r5-P1]:**
   (a) `.claude/settings.json` do dogfood; (b)
   `templates/settings/settings.base.json` (`install.sh:1503-1558`
   constrói o settings do adopter dele, não do arquivo vivo); (c)
   `templates/settings/settings.user.json` (cerimônia `--ceremony
   user`, `install.sh:1508-1510`); (d) **rota de UPGRADE para
   instalação existente** (install pula settings em
   `install.sh:1548-1550`; a entrega é a migração explícita
   baseline-aware de `upgrade.sh:2235-2252`) — cada superfície com
   teste (paridade template/dogfood + caso de migração). Pós-resposta
   U-1. **[codex r32] DISTINÇÃO: as SETTINGS de postura
   (`crossSessionInbound`/`isolatePeerMachines`) vão a TODAS as
   superfícies incl. `settings.user.json`; mas as REGISTRAÇÕES de hook
   ENFORCING (quota_resume, sendmessage_gate, task_gate, ConfigChange)
   NÃO entram no cerimonial `--ceremony user` (que é o perfil mínimo)
   — vão em base/dogfood + migração de upgrade. Não empurrar hook
   enforcing para o perfil user.**
   **[codex r31] A mudança de postura inbound para instalações
   EXISTENTES é ANUNCIADA:** a migração de upgrade imprime um aviso
   ("crossSessionInbound passou a `refuse` por default — reverta com
   `accept`/`hold` se você usa mensageria cross-session") e o
   CHANGELOG/UPGRADING documenta a mudança — nunca silenciosa (é
   mudança de comportamento observável para quem já usa peers).
4. Rules `Agent(param:value)` de política de tier (W4.3) + tabela de
   tiers no `team.md` ROUTING.
5. Promoção do `ConfigChange` guard advisory→bloqueante (W4.4, se a
   decisão de doutrina aprovar).
6. Registrações `PostToolBatch` (W3.3/W4.4), `TaskCompleted` (W4.4)
   **e `StopFailure` (W4.1) [codex r14-P1 — evento inexistente em CLI
   2.0 pode INVALIDAR o settings inteiro, exatamente a falha que o
   gate evita; sem StopFailure não há evidência de exaustão ⇒ nesses
   clientes o quota-resume degrada para aviso-apenas, documentado]**
   — **[codex r5-P1] condicionadas ao PISO de CLI suportado:** o
   SUPPORT.md declara ≥2.0, e eventos novos não têm tolerância provada
   em clientes velhos; usar o MESMO padrão de gate condicional já
   existente para `DirectoryAdded`/`Notification`
   (`upgrade.sh:189-200`) OU subir e ENFORÇAR o piso mínimo suportado
   na v1.4.0 (decisão registrada no pack + SUPPORT.md + teste do
   gate). **[Sec r2-R-SEC14] Exceção deliberada: o PreToolUse de
   `SendMessage`/`ListAgents` (item 2) é INCONDICIONAL — guard de
   segurança nunca some em silêncio; em CLI sem a tool o matcher
   simplesmente nunca dispara. E TODA registração condicional deste
   pack IMPRIME sua ausência na instalação (nunca omissão muda).**
7. ADR cross-session (doutrina W4.2 + resultado dos probes d/e/f +
   escopo degradado da claim de auditabilidade se aplicável + a frase
   **"nome de peer NÃO autentica"** — é ela que impede o próximo
   leitor de "melhorar" a allowlist para confiar em nomes).
8. **[codex r2-P1] `disableWorkflows: true` como default de ADOPTER**
   no settings.json instalado — SE o probe W4.2.0(b) confirmar o
   bypass do gate de spawn (evidência preliminar diz que sim): a linha
   entra AQUI com rota de propriedade (mesma pergunta U-1) + teste; a
   exceção operador-supervisionado do meta-repo fica documentada no
   ADR. Sem isso, executar o plano ao pé da letra deixaria agents de
   Workflow (acceptEdits, edits auto-aprovados) fora da defesa de
   spawn nos adopters.
9. **Herdado do PLAN-178 — W1.3 scoped permissions (decisão, não
    implementação).** O PLAN-178 (`### Registro de execução —
    fechamento parcial`, S314) nomeou a **abertura do W4-C** como o
    momento de decidir "absorver aqui vs pack próprio". A decisão NÃO
    foi tomada na S315 — o que abriu foi a **W4**, não o W4-C. Fica
    como o PRIMEIRO item a resolver na montagem deste pack, com as duas
    rotas explicitadas e a escolhida registrada. Toca `settings.json`
    ⇒ cerimônia do Owner no ato, qualquer que seja a rota.

**FORA deste pack [S315]:** isolamento do audit dir por projeto — o
fallback literal `ceo-orchestration` alcança **63 módulos** (24 em
`.claude/hooks/`, 39 em `.claude/scripts/`), tamanho incompatível com um
pack de cerimônia de escopo fechado ⇒ **`PLAN-182`**.

**Escopo em ARQUIVOS (VP r2-MF-A — o gate `touched−scope=∅` mede
caminhos, não decisões; lista derivada do predicado, a fechar
byte-exata na montagem do pack):** canônicos — `.claude/settings.json`,
`templates/settings/settings.base.json`,
`templates/settings/settings.user.json`, `scripts/upgrade.sh`
(migração + gate de piso), `.claude/hooks/check_quota_resume.py`
(novo), `.claude/hooks/check_sendmessage_gate.py` (novo),
**`.claude/hooks/check_agent_spawn.py` [codex r14-P1 — é ele que
bloqueia spawn de arquétipo sem `model` explícito no W4.3]**,
**`.claude/hooks/check_task_gate.py` (novo) [codex r14-P2 — o handler
do `TaskCompleted` que o item 6 registra; não existe handler na árvore
para adaptar]**, `.claude/team.md`, ADR novo, **e [codex r7-P1] os arrastados pelo
checklist R-SEC9 e pela promoção do ConfigChange:**
`.claude/hooks/_lib/audit_emit.py` (`_KNOWN_ACTIONS` + scrub),
`SPEC/v1/audit-log.schema.md` (linha do contrato),
`.claude/hooks/check_config_change.py` (advisory→bloqueante),
**[codex r8/r9-P1 → REVISTOS pelo r11-P1: a rota de assinatura foi
DESCARTADA (oráculo de mesmo-UID) — os escritores do snapshot NÃO são
tocados; fica apenas o hardening defensivo:**
`.claude/hooks/check_canonical_edit.py` entra no escopo para
`_CANONICAL_GUARDS += {.claude/scripts/statusline-ceo.py (o writer
DOGFOOD real — codex r18: não há statusline-ceo.py na raiz),
templates/scripts/statusline-ceo.py}` (defesa-em-profundidade contra edição do writer
por sessão acceptEdits — sem valor de autenticação); **[codex r11-P1]
`scripts/install.sh`** — o caminho de FRESH INSTALL das registrações
condicionais (o gate de piso citado vive só no upgrade.sh; install
constrói de templates estáticos — sem tocar o install, adopter novo ou
recebe evento que o CLI velho não parseia ou fica sem o guard; + teste
do caminho fresh); **e o toque de CI do W1.7** —
`.github/workflows/validate.yml` (shellcheck scope; kernel path, ver
protocolo abaixo); **[codex r13-P1, contagem r15-P2] as superfícies de CONTAGEM
DERIVADA que 3 hooks novos (quota_resume, sendmessage_gate, task_gate)
+ 1 ADR mudam** — `README.md`,
`README.pt-BR.md`, `CLAUDE.md` (regenerar via
`check-claude-md-claims.py` + verify-counts, tolerance=0; classificar
cada uma pelo predicado na montagem); livres
(fora do sentinel, mesmo commit) — `SUPPORT.md`,
`.claude/scripts/env-inventory.json`, docs, testes (`.claude/hooks/tests/**`,
`scripts/tests/**` — `hooks/tests/` NÃO é canonical-guarded, `_lib/tests/`
É), e **todas as SUPERFÍCIES DERIVADAS que 3 hooks novos + 1 ADR
regeneram**: o mapa de hooks gerado, o golden do registro de auditoria
(`audit_emit`/SPEC), e as contagens de README/README.pt-BR/CLAUDE.md.

**PRINCÍPIO DE FECHAMENTO DO ESCOPO [codex r26 — a lista acima é
SEMENTE, não closure]:** a completude do escopo NÃO se prova no texto do
plano — prova-se na MONTAGEM, rodando (i) todos os geradores de
superfície derivada (`generate-*.sh`, `check-claude-md-claims.py`,
`verify-counts.sh`) e (ii) o próprio gate `touched−scope=∅` sobre o
pack montado. Qualquer arquivo que o gate acuse fora do escopo é
adicionado ao sentinel ANTES de assinar (canônico) ou commitado junto
(livre) — a AUTORIDADE de completude é o gate, não esta lista.

**Janela do override de kernel [VP r5-MF-D, vale p/ W4-C E W3-K]:** o
pack é montado e `shasum -c` fecha verde ANTES de qualquer override
existir no ambiente; `CEO_KERNEL_OVERRIDE`/`CEO_KERNEL_OVERRIDE_ACK`
são exportados IMEDIATAMENTE ANTES do passo de land e feito `unset`
EXPLÍCITO na linha SEGUINTE ao land (caminho feliz), **com `trap
'... unset ...' EXIT` como BACKSTOP para o caminho de falha** (codex
r30/r32: o unset explícito é imediato; o trap só cobre o land que
aborta ANTES de alcançar o unset explícito — os dois juntos, não o
trap sozinho, que dispararia só no fim do shell) — nunca
atravessam para outro pack/sessão (a fonte da lição "um export sobra no
ambiente", U-3).

**Protocolo [corrigido pelo codex r9-P1]: W4-C é uma CERIMÔNIA DE
KERNEL** — o escopo toca caminhos de `_KERNEL_PATHS`
(`.claude/settings.json`, `.claude/hooks/_lib/audit_emit.py`,
`.github/workflows/validate.yml`; `check_arbitration_kernel.py:90,125,135`),
que o kernel hook bloqueia MESMO com sentinel comum. Logo: staged +
manifesto rastreado + shasum -c + sentinel GPG + touched−scope=∅ **+
`CEO_KERNEL_OVERRIDE`/`CEO_KERNEL_OVERRIDE_ACK` (postura do W3-K)**.
Sessão própria (não misturar com W3 nem W3-K — três posturas de
override distintas, três sessões). Consequência para o W1.7: o toque
de `validate.yml` landa AQUI, não no W3.

### W5 — Bateria E7: PRÉ-REGISTRO + E0 (a execução E1-E4 é o PLAN-170 — MF-3)

> **Re-escopo do round 1 (MF-3):** a bateria completa NÃO cabe no
> orçamento deste plano (só o E4 pré-registrado ≈ até 900 invocações
> de agente ≈ 9-18M tokens). Neste plano ficam: (1) o **pré-registro
> assinado** da bateria inteira (hipóteses, N, braços, kill criteria,
> validação do juiz [U-4], posturas [R-SEC10/R-5]) e (2) a execução do
> **E0** (retrospectivo, custo ~zero, e é ele que gateia E1/E2). A
> execução E1-E4 nasce como **PLAN-170** com orçamento próprio
> declarado (estimativa honesta 6-20M tokens, desenho pilot-first) e
> **gatilho nomeado: abre imediatamente após o corte da v1.4.0-rc.1**.
> v1.4.0 publica com "experimental: fleet patterns (bateria
> pré-registrada; E0 executado)" — nunca claim sem evidência.
> Protocolo de fleet do 170 (R-SEC10 + r2-R-SEC15): PROIBIDO
> `inbound=accept` combinado com acceptEdits/bypass/night-mode;
> sessões de experimento isoladas — **sem GPG, sem remote, sem
> credenciais, guards ATIVOS, nenhum caminho de cerimônia** (clone
> dedicado); o
> pré-registro declara que as constantes medidas valem para a POSTURA
> DO EXPERIMENTO, não a entregue (R-5).

O desenho abaixo é o CONTEÚDO do pré-registro (imutável após
assinatura):

> Desenho derivado da pesquisa acadêmica S298 (arquivada — ver
> `PLAN-169/research-README.md`; 25 fontes,
> níveis de confiança declarados). A literatura 2026 FORTALECE o
> "no speed claim" para código: mediu paralelismo ingênuo por arquivo
> custando mais SEM ganho de qualidade, e coordenação automática de
> agentes DEGRADANDO qualidade versus o sequencial (números e fontes
> no archive — não reproduzidos aqui por doutrina). O desenho abaixo
> encara isso de frente em vez de repetir o 7º experimento ingênuo.

**Bloco metodológico comum (imutável no pré-registro, assinado antes
de qualquer run):** 3 braços sempre — (A) solo otimizado, (B) paralelo
cross-session, **(C) solo token-matched com B** (sem C, resultado
positivo é indistinguível de "gastamos 15× mais tokens" — ~80% da
variância em benchmarks é compute); percentis p50/p95, nunca média
sozinha; ≥3 runs por célula para variância run-to-run ANTES de
comparar braços (σ(A) cobre Δ ⇒ morto na largada, reporta e para);
grading cego; ground truth semeado por nós (nunca issues públicas —
search-time contamination); ordem randomizada, mesmo SHA base em
worktrees separados; registrar modelo/versão/flags/settings efetivos;
negativo publica igual.

**Sequência (cada um gateia o próximo):**
- **E0 — gate-zero (retrospectivo, custo ~zero): medir a fração
  serial.** Sobre o audit log HMAC dos **14 planos M=155→168**
  [codex r2: o range contém 14, não 12 — amostra PINADA], decompor
  wall-clock em tempo-máquina / tempo-humano (review, cerimônias,
  decisões) / tempo-morto (CI, quota). **[codex r2+r14] A fração serial S
  do gate INCLUI o tempo-morto não-paralelizável E a máquina SERIAL do
  caminho crítico** (esperas de CI/quota não aceleram com mais
  agentes; impl→teste→gate dependency-ordered também não — excluir
  qualquer um superestimaria o teto):
  `S = (humano + morto_não_paralelizável + máquina_serial_crítica) / total`,
  com máquina_serial derivada do grafo de dependência dos passos (ou,
  onde irrecuperável do log, o corte conservador: máquina 100% serial
  naquele plano, reportado por plano). **Regra
  pré-registrada: S ≥ 0,40 ⇒ E1/E2 NÃO são financiados** (fração
  serial alta demais para paralelização compensar — orçamento vai
  para redução de S, que é o que o framework já faz ao automatizar
  gates); S ≤ 0,20 ⇒ E1/E2 liberados; **[codex r4-P1] banda
  intermediária 0,20 < S < 0,40 ⇒ resultado PRÉ-DEFINIDO: E1 liberado
  APENAS como piloto (metade do N, mesmo critério de kill) e E2 NÃO
  financiado — nenhuma faixa medível fica para juízo post-hoc.**
- **E4 — fidelidade de handoff (barato, mecânico, roda SEMPRE):**
  cadeias de k hops com spec de 20 restrições atômicas
  máquina-verificáveis; prosa-livre via SendMessage vs artefato
  tipado (shards ADR-141 / memory-scratchpad). Saída: **meia-vida de
  restrições em hops** — constante de design ("nenhuma cadeia >X hops
  sem re-ancoragem em artefato").
- **E3 — paralelismo SÓ na verificação (a aposta forte da
  literatura):** geração solo; review com k∈{1,3,5} revisores
  cross-session **mutuamente cegos** + braço token-matched (k=1 × 3
  rodadas) + braço k=3 COM comunicação (predição pré-registrada da
  deliberative illusion: comunicação REDUZ findings únicos). Critério:
  recall monotônico em k E razão FP/TP ≤ 1,0 em k=5.
- **E1 — audit fan-out read-only vs solo (só se E0 liberar):** recall
  de defeitos semeados; **[codex r5-P2] DOIS estimandos separados no
  pré-registro (as duas restrições não cabem numa comparação só):**
  (i) B vs A a WALL-CLOCK FIXO (mesma deadline, compute livre) e
  (ii) B vs C a COMPUTE IGUAL (mesmos tokens agregados, tempo livre) —
  cada um com sua hipótese; McNemar pareado, kill após 15 snapshots se
  B−C ≤ 0 no estimando (ii).
- **E2 — batch de itens de baixo acoplamento (só se E0 liberar):**
  estratificação pré-registrada por acoplamento (Jaccard de arquivos +
  grafo de import); hipótese pré-registrada como INTERAÇÃO — pergunta
  experimental, NÃO claim: prever que qualquer vantagem de B, se
  existir, apareça só no estrato low, e que B degrade qualidade no
  high; kill se CI-green de B ficar >10pp abaixo de A — o modo
  "rápido-porém-pior" que a literatura descreve (fontes no archive).
- **Kill geral de substrato:** mensagem cross-session perdida/duplicada
  = defeito registrado (substrate-watch) e pausa; defeito ≠ resultado.

**Aceite:** pré-registro assinado (hash commitado) ANTES do 1º run;
relatório com inputs impressos; decisão do claim README registrada.
**O único resultado que o experimento poderia sustentar é sobre
QUALIDADE DE AUDITORIA (recall de defeitos semeados, medido a orçamento
de tempo igualado entre braços) — NUNCA um claim de velocidade/
throughput do framework, que a doutrina no-speed-claim proíbe
(AGENTS.md); "a orçamento de tempo igualado" é condição de controle do
experimento, não afirmação de desempenho.** Bônus de desenho: o
braço anti-debate do E3 alimenta a doutrina do `/debate` (a evidência
sugere que o valor está na diversidade da rodada 1 + rail cross-vendor,
não na convergência de rodadas 3+ — revisitar contagem de rodadas com
o dado em mãos, não por simetria).

### W6 — Trens de publicação

**W6.1 — v1.3.0 GA (executa PLAN-166 W2 como escrito — sem duplicar).**
- Pré-condições fechadas por W0/W1: árvore limpa (W0.1-W0.3), nightly
  verde ou vermelho só-esperado (W1), Translations triado (W0.4),
  A.0.4 provado pelo W2.6.
- **Âncora do re-pass r2 (D1, obrigatória):** o re-pass r2 roda no
  HEAD que JÁ inclui TODAS as pré-condições de v1.3.0 — **W0 + W1 +
  W2 (livres)**; W3/W3-K/W4-C são conteúdo v1.4.0 — e **NUNCA no SHA
  `ad9cc3a` citado como evidência estática do ledger**. **[codex r30]
  A BASELINE do delta do verdito rc.2 é esse mesmo HEAD pós-W0-W2 —
  logo os arquivos que PLAN-169 W0-W2 landaram em main ficam ABAIXO da
  baseline (não entram no delta reviewed-parent→tag), e o assert do
  166 W2 "delta = SÓ os artefatos do verdito" continua válido; se a
  baseline fosse anterior a W0-W2, esses arquivos apareceriam no delta
  e o assert reprovaria.** Revisar o SHA
  errado faz o `bump --rc 2` ser legitimamente rejeitado pelo guard
  de delta que o próprio 166 construiu (exit 6).
- **B.a vs GA (OQ-5):** ver Open questions — default recomendado:
  rota (b), GA com exceção NOMEADA no release-checklist/CHANGELOG.
- Sequência (do 166, ordem PINADA): re-pass r2 de worktree DETACHED
  limpa no SHA candidato até APPROVE → `release.sh bump --rc 2` →
  verdito rc.2 assinado+commitado (delta_allowlist/manifest/sha256) →
  push main → CI verde no commit do verdito → `preflight --rc 2` →
  tag `v1.3.0-rc.2` (Owner) → push tag → pre-release → **hold 24h** →
  re-pass final em worktree DA TAG → assert `origin/main == SHA rc.2`
  (avançou ⇒ rc.3, hold reinicia) → `bump --stable` (no-op provado) →
  verdito GA → push → CI verde → `preflight --stable` → tag `v1.3.0`
  (Owner) → aprovação `production-npm` APÓS gate verde → GA.
- AC-7 do 166 registra as runs reais do await-gate (rc.2 E GA);
  ratificação `approx` no material assinado da rc.2 (W0.5).
- Ao fechar: PLAN-166 `executing → done` com §-final completo.

**W6.2 — v1.4.0 (novidades) na sequência imediata.**
- Conteúdo: W1-W4 (incl. W4-C) landados + pré-registro assinado da
  bateria + resultado do E0 (experimento é evidência, não gate);
  CHANGELOG honesto — **[codex r16-P1] o rótulo do quota-resume é
  CONDICIONAL ao resultado do live-fire do W4.1: GO ⇒ "supported";
  no-GO ou não-executável ⇒ "experimental" (AC-4 permite a rota
  no-GO, então o CHANGELOG não pode hardcodar "supported")**;
  governança cross-session: supported; fleet patterns: experimental
  (bateria em execução no PLAN-170).
- `bump` minor exercita W2.6 ao vivo (controle positivo real do
  marcador). Trem idêntico ao W6.1 em rigor, com a sequência pinada do
  166 (o rail/verdito precede a tag): **`release.sh` RETARGETADO para a
  baseline 1.4.0 (minor bump; mesmo driver do W6.1, novo alvo de
  versão) → `bump --rc 1` → re-pass/rail até APPROVE → verdito rc.1
  assinado+commitado → push → CI verde → preflight → tag v1.4.0-rc.1
  → hold 24h → re-pass final → `bump --stable` → verdito GA → gates →
  tag v1.4.0 → publish**. Deferred E.13 (workflow_call) segue deferido
  — gatilho inalterado.

## Acceptance criteria

- [x] AC-1 [P0] Ledger 100% endereçado: cada item A-F fecha numa wave,
      defere com gatilho nomeado (E.13-E.17 mantidos), ou registra
      recusa do Owner (W0.8/W0.9). Auditável por tabela no §-final.
      **Fechado em 2026-08-18 (S313): tabela em `## Ledger final —
      endereçamento dos itens A-F`, 62 linhas com evidência
      path:line/sha cada.** Leitura honesta do "endereçado" (atualizada
      S314, 2026-08-19 — W3-K landou `c34e8e3` e fechou E.2): 58 CLOSED,
      3 DEFERRED com gatilho inalterado (E.13/E.14/E.15), 1 **OPEN com
      wave nomeada** (E.7 → W4-C) e ZERO recusas do Owner (as duas
      decisões pedidas — W0.8 e W0.9 — foram aceites). O AC mede
      endereço, não fechamento: o OPEN não fecha este AC como "tudo
      pronto", ele fica visível com o defeito ainda no disco.
- [x] AC-2 [P0] Nightly Linux = 62 GREEN / 3 RED exatos
      {OWN-0016,0024,0027} sem tocar tabela/expected-reds; riders
      (FALSE-GREEN 0073 + HARNESS-ERR fail-closed) com controle
      positivo cada.
      **Fechado por medição (reconciliado 2026-08-22, S322): o
      checkbox envelheceu — a prova estava no disco desde a W1.**
      Run mais recente `32558333621` (`schedule`, `main`, SUCCESS,
      2026-08-22T06:58:02Z) imprime literalmente
      `GREEN=62  RED=3  AMBIG=0  HARNESS-ERR=0` e
      `ownership gate: RED set stable (3 expected RED cells, zero
      TIMEOUT/ESCAPE/AMBIG)`. Rider FALSE-GREEN: mecanismo em
      `scripts/tests/test-ownership-table.sh:741-758` (`_selfcheck_mtime`,
      exit 2 antes de qualquer célula). Rider HARNESS-ERR:
      `test-ownership-table.sh:165-182,625,671` (MTIME-ERR ⇒ HARNESS-ERR)
      com controle positivo automatizado — `test-ownership-nightly-gate.sh`
      = 13/13, incluindo `S6 HARNESS-ERR=1 (gate rc=1)` e
      `S3 set shrank (all green) (gate rc=1)`. **Não-toque provado por
      ausência:** `git log 67a4c75..HEAD -- scripts/tests/ownership_table.tsv
      scripts/tests/ownership-expected-reds.txt` = **0 commits** (último
      toque `67a4c75`, 2026-08-07, ANTES da W1).
- [x] AC-3 [P0] v1.3.0 GA publicada pela sequência pinada do 166 W2
      (AC-7 do 166 fechado com runs reais); PLAN-166 `done`.
      **Fechado por medição (reconciliado 2026-08-22, S322): o
      checkbox envelheceu — o §Ledger deste plano já registrava
      A.2/A.3/A.4 CLOSED (linhas 1464-1467) e a entrada S312-S313
      (linhas 1598-1601) já dizia "W6.1 CUMPRIDA".** Provas de runs
      REAIS: `gh release list` ⇒ `v1.3.0  Latest  2026-08-18T01:16:59Z`;
      `git tag -v v1.3.0` ⇒ *Good signature* (João Canhada), objeto
      `d789721c2fd4a11c36c87eda0e1118eab59092e4`; cadeia de pré-releases
      rc.1..rc.4 todas publicadas (2026-08-04 → 08-16). Veredito
      assinado em `.claude/governance/pair-rail-verdict-v1.3.0.md`.
      `PLAN-166` = `status: done`, e o AC-7 dele foi reconciliado no
      MESMO commit que este (a dependência não fica pendurada).
      **Desvio da letra, registrado com honestidade:** o AC-7 do 166
      diz "rc.2 cortada" e o GA andou sobre a **rc.4** — a regra de
      ancestralidade funcionou no sentido caro (ver linha 1466).
      Objetivo cumprido; a letra virou título histórico.
- [ ] AC-4 [P1] Quota-resume: probes W4.1.0 registrados; simulação
      (job ÚNICO no horário efetivo `resets_at+≥120s`, minuto ∉
      {:00,:30}) + live-fire real OU registro falsificável de por que
      não; kill-switches provados (`CEO_QUOTA_RESUME=0`,
      `CEO_SOTA_DISABLE=1`); gate de postura lê postura EFETIVA; doc
      promete exatamente o que o teste provou; envs novas em
      `env-inventory.json` no mesmo commit.
- [ ] AC-5 [P1] Probes W4.2.0 (a-f) registrados com evidência; peer
      tenta induzir edit canônico via SendMessage ⇒ bloqueado + evento
      HMAC com campos whitelisted (checklist R-SEC9); com `refuse`:
      nenhum turno nasce (controle: com `accept`, nasce); doutrina em
      ADR (incl. decisão de visibilidade de tentativas recusadas e,
      se `inbound != refuse`, escopo degradado EXPLÍCITO da claim de
      auditabilidade).
- [ ] AC-6 [P1] Pré-registro da bateria E7 assinado (hash commitado)
      ANTES de qualquer run + **E0 executado** (**S** medido com
      inputs impressos [codex r4: S, não "H" — a fração serial inclui
      tempo-morto], decisão E1/E2/banda-intermediária registrada) +
      PLAN-170 criado com orçamento próprio declarado e gatilho
      nomeado (pós-corte v1.4.0-rc.1).
- [ ] AC-7 [P1] Marcador 12º site: controle plantado vermelho + bump
      1.4.0 real verde (as duas evidências).
- [ ] AC-8 [P1] v1.4.0 GA publicada (trem completo com hold).
- [x] AC-9 [P2] As 4 dívidas C.* fechadas com evidência dinâmica
      (pair-rail-gate roda até o fim NESTA máquina; injector
      fail-closed testado; **overhead: P4 não bloqueia fan-out
      legítimo de investigação — e, SE um canal persistido existir,
      ele cumpre os 5 limites do W3.3** [Sec r2: o AC mede o
      RESULTADO, não o mecanismo]; C.4 só higiene de doc).

## Open questions

> **OQ-6 (Owner, 2026-08-14, S306):** escopo do ciclo — pergunta
> apresentada via AskUserQuestion ("Qual escopo entra neste ciclo,
> antes do release?"); opções: (a) começados + 174 cedo [recomendada],
> (b) só os começados, (c) tudo — os 10 planos.
> **Decisão do Owner: "Tudo — os 10 planos."** Interpretação vinculante
> (redação v2 — a v1 dizia "um único re-pass/tag/hold no fim", claim
> insatisfazível pega pelo rail codex S306: OQ-1 ratificada fixa DOIS
> trens, e o AC-8 deste plano só fecha com corte v1.4.0-rc.1 + hold +
> GA v1.4.0): a decisão é de ESCOPO, não de sequência — os 10 planos
> (166, 169, 171–178) concluem dentro do ciclo, honrando os dois trens
> ratificados. Trem 1 (v1.3.0): emenda-1 do 177 + PLAN-178 (rota-
> SEQUÊNCIA do seu §Freeze: arquivos, incl. Lote B, DENTRO da tag
> rc.4) + re-pass rc.4 — nada além disso embarca nele. Trem 2
> (v1.4.0): TODO o restante (waves restantes de 169, 171–176,
> 173/175/174 nos gates que seus `external_wait` declaram) concentra-se
> num ÚNICO corte v1.4.0 ao final — sem rcs intermediárias além das
> que o protocolo do trem exigir.
> **Cláusula de precedência (rail codex S306, P1×2 — fecha a classe,
> não o ramo):** esta OQ decide ESCOPO; ela NÃO sobrescreve nenhum
> `external_wait`, gate, freeze ou ramo de aborto ratificado nos
> planos individuais — em conflito, o plano individual PREVALECE.
> Consequências já identificadas (exemplos, não lista fechada):
> (i) PLAN-178 pertence ao trem 1 — seu §Freeze rota-SEQUÊNCIA exige
> os arquivos (incl. Lote B) DENTRO da tag rc.4; "nenhum trabalho novo
> no trem 1" lê-se com esta exceção; invariante nada-entre-tag-e-GA
> preservada. (ii) O ramo de aborto D-2 do PLAN-174 segue VÁLIDO: se
> perder o gate, aplica-se o caminho ratificado (cerimônia manual v1.4;
> W4 move para o trem seguinte) e o residual W4 é TRANSFERIDO para
> `PLAN-174-FOLLOWUP-<slug>` (identidade de lineage exigida por
> PLAN-SCHEMA.md, com os campos de lifecycle de follow-up) — o 174
> fecha por transferência registrada, nunca com AC pendente silencioso;
> o corte v1.4.0 não é atrasado por ele.

> **✅ TODAS RATIFICADAS pelo Owner em 2026-08-08 (chat: "ratifica tudo
> com as recomendações") — decisões, conforme as recomendações:**
> OQ-1 = v1.3.0 GA primeiro, v1.4.0 na sequência imediata ·
> OQ-2 = ativo só com night-mode OU opt-in `CEO_QUOTA_RESUME=1`;
> threshold ÚNICO de arme 90% (`CEO_QUOTA_RESUME_PCT`) ·
> OQ-3 = break-glass ADR ACEITO (entra no pack W3) ·
> OQ-4 = W2.8 traz a proposta; viés ratificado = guard canônico
> (checksum verificado pelo próprio decisor é registered-vacuous) ·
> OQ-5 = rota (b): GA v1.3.0 com exceção NOMEADA de B.a no
> release-checklist/CHANGELOG; fix na v1.4.0 via W3 ·
> W0.8 = convenção "AC provado no §registro de execução; checkbox não
> usado" registrada nos §9 de 167/168 (item W0.8 executa isso).
> O texto original das OQs fica abaixo como registro do espaço de
> decisão apresentado.

- **OQ-1 (Owner):** ordem de publicação — recomendação forte:
  v1.3.0 GA primeiro (rc.2 pronta, debate fechado), v1.4.0 na
  sequência imediata. Alternativa (fold tudo em 1.4.0) reabre o debate
  do 166 e o delta-gate; não recomendada.
- **OQ-2 (Owner):** quota-resume — postura default: só com night-mode
  armado, ou sempre-on com opt-out? Threshold de arme (um só, default
  90%, `CEO_QUOTA_RESUME_PCT`)?
- **OQ-3 (Owner):** break-glass ADR — aceitar (entra no W3) ou recusar
  (registro no release-checklist)?
- **OQ-4 (debate):** família "script livre que decide gate" — guard
  canônico ou checksum? (W2.8 traz a proposta.)
- **OQ-5 (Owner, D2):** B.a (bug reproduzido de upgrade sob
  install-state malformado) vs v1.3.0 GA — **(a) [corrigida pelo codex
  r12-P2]: NÃO é "landar o W3 inteiro antes" (violaria a ordem pinada
  e embarcaria conteúdo 1.4 na 1.3.0) — é destacar B.a numa
  MINI-CERIMÔNIA própria pré-rc.2 (só `upgrade.sh` +
  `_framework_manifest_set.sh` + teste), com re-pass cobrindo-a** 
  (adia o GA pelo tempo de uma cerimônia); ou
  **(b) [RECOMENDADA]** GA sai com exceção NOMEADA no
  release-checklist/CHANGELOG (cenário raro: state editado à
  mão/legado; fix já pronto na v1.4.0 via W3). Escolha explícita, não
  omissão.

## How to continue

**Passo 0 — gate humano (codex r3-r24): CUMPRIDO em 2026-08-08.** O
Owner ratificou explicitamente em chat ("ratifica tudo com as
recomendações e commita o pack"): R-A (draft→reviewed), R-B (gate de
debate §12.4 aceito como design-coherent), R-C (deferral da higiene de
registro), OQ-1..5 e W0.8 — todos conforme as recomendações do
checklist. As waves estão LIBERADAS na ordem pinada.
**Além disso, o gate humano das waves perigosas é MECÂNICO, não
prosa:** W3/W3-K/W4-C (todo o conteúdo L3+/kernel) NÃO PODE executar
sem um sentinel GPG que só o Owner assina (e W4-C exige, além disso,
`CEO_KERNEL_OVERRIDE`); os hooks `check_canonical_edit.py` /
`check_arbitration_kernel.py` bloqueiam fisicamente qualquer edição
dessas superfícies sem a assinatura. Logo a ratificação da v2.5 pelo
Owner acontece, de forma inescapável, no ato de assinar cada pack —
não há como as waves de risco rodarem antes do humano. **[VP r5] E
o W6.1 — que publica a v1.3.0 e vem ANTES do W3 na ordem pinada —
também tem gate humano próprio, só que NÃO é GPG: é o verdito rc.2/GA
assinado + a TAG do Owner + a aprovação `production-npm` (nada é
publicado sem esses três atos seus).** W0/W1/W2 são L1-L2 em
superfícies livres, explicitamente autorizadas pela instrução. A
ratificação de 1 linha pedida no checklist é belt-and-suspenders para
as waves livres. `reviewed→executing` no primeiro commit de W0.

Próxima sessão (primeira de execução): ler este plano + ledger; rodar
`/debate status PLAN-169` para confirmar consensus; executar W0 inteiro
(1 sessão, itens independentes — W0.8/W0.9 são perguntas ao Owner no
início); abrir W1 na mesma sessão se sobrar orçamento. Cada wave fecha
com commit referenciando PLAN-169 e atualização do §Progress log.
Nota: as curas exigidas pelo próprio rail sobre o PACK (neutralização
do script do 167; espelho pt-BR do W0.4; scrubs) foram aplicadas na
S298 como integridade do pack, ANTES da execução de waves — os itens
W0 correspondentes viram VERIFICAÇÃO, não re-execução.

## Success criteria

- Duas tags GA publicadas (v1.3.0, v1.4.0) com verdito assinado, hold
  cumprido e await-gate verde em cada uma.
- `ceo-boot` sem vermelhos: nightly 62/3-esperado, zero stranded, zero
  workflow red não-triado.
- README/docs atualizados com **o resultado do E0 + o handoff
  explícito da bateria ao PLAN-170** (codex r3-P2: E0 mede fração
  serial, não recall — o resultado completo da bateria é critério do
  PLAN-170, sucessor declarado, nunca deste plano) e com as novidades
  cross-session/quota-resume como supported OU experimental — nunca
  claim sem evidência.
- Memória e MEMORY.md refletindo o fechamento; nenhum "fica pro
  próximo" sem gatilho nomeado.

## Riscos

- **Substrato jovem:** cross-session messaging é recente no harness;
  flakes de entrega viram defeito registrado (substrate-watch), nunca
  resultado de experimento. Mitigação: kill criteria do W5.
- **Quota-resume depende de comportamento não documentado do harness
  no estouro** — por isso live-fire obrigatório antes de doc (AC-4).
- **Dois trens com hold 24h cada = calendário mínimo ~4-6 dias** para
  as duas GAs; orçamento honesto declarado no frontmatter.
- **Contenção codex** (outra sessão local usa `codex exec`): retry com
  backoff; nunca aceitar transcript truncado.
- **Escopo do W3 crescer:** o pack W3 fecha com seus itens + a inclusão
  condicional do W2.8; **o W1.7-CI (`validate.yml`) NÃO é do W3 — é
  kernel-path e landa no W4-C** (codex r18/r26). Item novo = wave nova
  ou plano novo, não inchaço do pack (lição S296: patch ramo-a-ramo em
  produto
  cartesiano).

## Deferred (herdados, gatilho inalterado)

- E.13 `workflow_call` refactor — gatilho: refactor do release.yml por
  outro motivo.
- E.14/E.15 células 0016/0024/0027 — plano próprio; célula fecha e
  expected-reds encolhe NO MESMO pack.
- E.16 nightly vermelho até W1 landar — causa nomeada, NUNCA silenciar
  pela tabela.
- **Cross-ref S305 (sem mudança de escopo aqui):** os candidatos
  derivados da pesquisa academia-vs-framework — critic fresco por
  retry, barra-por-exemplar, estudo dreaming/curadoria de memória
  (fronteira com PLAN-154), auditoria MAST-14 + injeção inter-agente,
  adoção de substrato 2026 — têm dono ÚNICO no **PLAN-178**
  (`PLAN-178/research-S305.md` = fonte das referências). Este plano
  não os absorve para não emendar escopo assinado.

## Ledger final — endereçamento dos itens A-F

> **O que esta tabela é (AC-1).** Uma linha por item do ledger
> `PLAN-169/ledger-S298.md` (A.0.1–A.5.5, B.a–B.d, C.1–C.4, D.1–D.8,
> E.1–E.17, F.1–F.15 = **62 itens**), com o veredito e a EVIDÊNCIA que
> o sustenta — sha de commit, `path:line` do disco de hoje, ou o
> registro de execução deste plano. Nada aqui é recordado de memória:
> um item que eu não consegui verificar recebe `OPEN` com o motivo,
> nunca um `CLOSED` presumido.
>
> **Não duplica os registros existentes.** Os dois `### Registro de
> execução` deste plano (W3 landada `e5ce982`; W2.8 + W0.9 landados
> `874117c`; W3-K landada `c34e8e3`) e o §Progress log continuam sendo
> a narrativa; esta tabela só aponta para eles.
>
> **Placar:** 58 CLOSED · 3 DEFERRED-with-trigger · 1 OPEN · 0
> REFUSED-by-Owner.
>
> **Fora do ledger (não entram na contagem):** W2.9 (`debate-converge`)
> e W2.10 (fleet-currency) nasceram de auditorias da própria S298, não
> das 6 varreduras — estão executados e registrados no §Progress log
> (S299), mas não são itens A-F.

| item | verdict | wave | evidence | note |
|---|---|---|---|---|
| A.0.1 árvore limpa antes da tag | CLOSED | W0.3 | `.gitignore:25`; `ls .claude/plans/PLAN-166/archive/*.tar.gz` → no matches; tag `v1.3.0` | Os 3 untracked de hoje (`PLAN-169/e0-report-s300.txt`, `PLAN-179/LEDGER.md`, `PLAN-179/staged-w01/`) são artefatos PÓS-GA, não os do ledger |
| A.0.2 decidir o nightly vermelho antes do corte | CLOSED | W1 | run `31286301110` (62/3); nightly `32111138908` success (2026-08-18) | Rota barata escolhida: portar o harness ANTES da rc.2 — foi o que ocorreu |
| A.0.3 `Translations drift` vermelho desde 04/08 | CLOSED | W0.4 | §Progress log 2026-08-08 (S299): drift local 0 + workflow verde no push `57119b3` | Curado, não silenciado |
| A.0.4 `bump` mantém `marcador == VERSION` | CLOSED | W2.6 | `.claude/scripts/local/_release_bump_sites.py:84`; `.github/workflows/release.yml:84-97` | Deixou de passar por coincidência: o marcador virou site de bump. Assert verde nos 4 cortes (rc.2/rc.3/rc.4/GA). Controle AO VIVO do minor = AC-7 (W6.2), ainda aberto |
| A.0.5 ADR de break-glass antes do GA | CLOSED | W0.9 → W2.8 | `.claude/adr/ADR-193-break-glass-repo-kill-switches.md` (`status: ACCEPTED`), commit `874117c` | O GA saiu ANTES do ADR (17/08 vs 18/08): a decisão foi tomada, o risco atravessou a janela nomeado no §OQ |
| A.1 re-pass codex round 2 | CLOSED | W6.1 | `.claude/plans/PLAN-166/repass-r2/VERDICTS-SUMMARY.txt` + `PROVENANCE-r2.md` + `MANIFEST-r2.sha256` | O r2 rodou; a rota que efetivamente chegou ao GA foi a rc.4 do PLAN-177 |
| A.2 corte da rc.2 | CLOSED | W6.1 | tag `v1.3.0-rc.2`; `.claude/governance/pair-rail-verdict-v1.3.0-rc.2.md` | |
| A.3 hold 24h + re-pass final + guard de ancestralidade | CLOSED | W6.1 | tags `v1.3.0-rc.3` e `v1.3.0-rc.4` (`4273d6c`); verdito `d789721` | A regra r18 FUNCIONOU no sentido caro: `main` avançou ⇒ não houve GA sobre a rc.2, cortou-se rc.3 e depois rc.4 |
| A.4 GA v1.3.0 | CLOSED | W6.1 | tag `v1.3.0`; `.claude/governance/pair-rail-verdict-v1.3.0.md` | GA cortado 2026-08-17 |
| A.5.1 AC-3 substantivamente satisfeito, checkbox `[ ]` | CLOSED | W0.5 | `.claude/plans/PLAN-166-…md:728-734` (§-final: subsunção por PLAN-167/168 com evidência) | |
| A.5.2 AC-4 com exceção nomeada | CLOSED | W0.5 + W3.2 | PLAN-166 §-final; `.github/workflows/smoke-install.yml:360` (`grep -qF 'positive control: FIRED in every mode'`, `e5ce982`) | A exceção nomeada fechou quando o 2º fator virou causal |
| A.5.3 subsunção ausente no corpo do 166 | CLOSED | W0.5 | `.claude/plans/PLAN-166-…md:711` `## §-final — Estado de fechamento e subsunção (PLAN-169 W0.5, 2026-08-08)` | |
| A.5.4 ratificação `approx`/collect-errors | CLOSED | W0.5 → W6.1 | `.claude/governance/pair-rail-verdict-v1.3.0-rc.2.md:44,83` | Cumprida onde foi prometida: no material ASSINADO da rc.2, não em prosa de plano |
| A.5.5 frontmatter do 166 / *stranded* | CLOSED | W6.1 + higiene S313 | `PLAN-166` frontmatter `status: done`, `completed_at: 2026-08-17`; commit `a71229e` | `executing→done` só depois do GA, como o item exigia |
| B.a `PROTOCOL_SOURCE` malformado aborta o upgrade | CLOSED | W3.1 | `scripts/upgrade.sh` (allowlist POSITIVA de charset + WARNING nomeando a chave rejeitada) e `scripts/_framework_manifest_set.sh` + caso novo em `scripts/tests/test-protocol-pointer-render.sh`, todos em `e5ce982` | Rota OQ-5(b) honrada: GA saiu com exceção nomeada, fix landou na linha 1.4.0 |
| B.b 2º fator do parity aceita evidência não-causal | CLOSED | W3.2 | `.github/workflows/smoke-install.yml:360` (`e5ce982`) | Fix de 1 linha, como o ledger previu |
| B.c `test_case_a_p99_under_5ms` fora do ADR-163 | CLOSED | W2.2 + W3.5 | §Progress log S299 (N 100→200, índices derivados de n, pré-condição de colapso; mesmo passe no claim-producer); emenda ao `.claude/adr/ADR-163-…md` (+33 linhas, `e5ce982`) | A decisão CI-mediana foi REAVALIADA com o flake real do run 31288404989 e mantida COM evidência |
| B.d nightly Linux — causa-raiz única | CLOSED | W1 | §Progress log 2026-08-08 (S299); run `31286301110` = `GREEN=62 RED=3` exatos {0016,0024,0027} | `ownership_table.tsv` / `ownership-expected-reds.txt` NUNCA tocados |
| C.1 injector resolve persona por match FUZZY | CLOSED | W2.3 | `.claude/scripts/inject-agent-context.sh:798-805` (ladder EXATA, 4 degraus) e `:903` (`exit 3` fail-closed) | |
| C.2 `pair-rail-gate.sh` inexecutável nesta máquina | CLOSED | W2.5 | `.claude/scripts/local/pair-rail-gate.sh:64-83` (Gate 1 = API key OU login; Gate 2 pulado na rota login) | Lacuna (i) do ledger fechada com evidência DINÂMICA: ambas as rotas PASS nesta máquina (§Progress log S299) |
| C.3 `CEO_OVERHEAD_ACK` — defeito é a ENTREGA | CLOSED | W2.4 (docs) + W3.3 (canal) | `docs/TROUBLESHOOTING.md` / `.pt-BR.md` (W2.4); `.claude/hooks/check_anti_ceo_overhead.py` em `e5ce982` (P4 degrada a advisory no apply-step, com re-avaliação `skip_p4` para não sombrear um P5 bloqueante) | Limite honesto declarado NO PRÓPRIO código: o hit advisory NÃO é auditado (exige cerimônia de whitelist de `audit_emit`) — follow-up nomeado na família de auditoria do W4 |
| C.4 P0 case-insensitive (APFS) | CLOSED | W3.5 (via E.17) | Código fechado em `6b5dd10`; resíduo de DOC curado em `.claude/adr/ADR-186-hook-deadline-policy.md` (nota histórica, `e5ce982`) | |
| D.1 `PLAN-167/OWNER-PREPARE-TO-SIGN.sh` untracked | CLOSED | W0.1 | `git ls-files -s` → `100644 a69eeff …/PLAN-167/OWNER-PREPARE-TO-SIGN.sh` | Rastreado NEUTRALIZADO (⛔ + `exit 1`) e SEM exec bit — evidência, não reprodutor perigoso |
| D.2 `step1` obsoleto rastreado | CLOSED | W0.2 | `.claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh:2` (header `OBSOLETO — substituído por step1b; re-executar REVERTERIA o PLAN-167`) | |
| D.3 2 tarballs untracked | CLOSED | W0.3 | `ls .claude/plans/PLAN-166/archive/*.tar.gz` → no matches | |
| D.4 padrão de gitignore para os tarballs | CLOSED | W0.3 | `.gitignore:25` `.claude/plans/*/archive/*.tar.gz` | `archive/` inteiro NÃO foi ignorado (19 arquivos de evidência preservados) |
| D.5 status/frontmatter conformes | CLOSED (no-action) | W0 | frontmatter dos planos; higiene autorizada em `a71229e` | O veredito do ledger era "nenhuma ação"; o `executing→done` do 166 veio pelo caminho legal (pós-GA) |
| D.6 zero planos órfãos ou drafts | CLOSED (no-action) | W0 | `ls .claude/plans/` | Verdadeiro à época; os planos criados depois (171-181) nasceram conformes ao PLAN-SCHEMA |
| D.7 contagens derivadas sem drift | CLOSED (no-action) | W0 | G4 do land `874117c` (verify-counts verde nas 10 superfícies vigiadas) | Contagem viva hoje: `ls .claude/adr \| grep -c '^ADR-[0-9]'` = 194 (o 195º arquivo é `README.md`) |
| D.8 path `.claude/scripts/verify-counts.sh` inexistente + gate vacuoso | CLOSED | W0.6 + W2.8 | memória `feedback-verify-counts-real-path-is-local.md`; `.claude/governance/gate-scripts-manifest.txt` (9 membros) + ADR-192, `874117c` | Sweep de runbooks VIVOS por `\|\| echo advisory` feito na S299; a família inteira ganhou pin de checksum na W2.8 |
| E.1 marcador como 12º site de bump | CLOSED | W2.6 | `_release_bump_sites.py:84`; `verify-counts.sh:1105-1109` | Controle transitório (dessinc ⇒ vermelho) provado e desplantado no MESMO commit; controle AO VIVO = bump 1.4.0 (AC-7 / W6.2), ainda aberto |
| E.2 emits de GRANT do kernel silenciosos | CLOSED | W3-K | `.claude/hooks/check_arbitration_kernel.py:540` → `ceremony_sha=_file_sha256(file_path)`; `kernel_override_used` wired (`:556`/`:609`/`:822`); cerimônia `c34e8e3` + sentinel `W3K-approved.md.asc` | Cerimônia de kernel executada em sessão separada (U-3) em 2026-08-19; teste positivo do emit de GRANT em `test_arbitration_kernel_grant_emit.py`. Ver `### Registro de execução — W3-K LANDADA` |
| E.3 matcher das 2 frases de ADR no GUIA-COMPLETO | CLOSED | W2.7 | `.claude/scripts/local/verify-counts.sh:610` | Drift REAL (GUIA 189 vs disco 190) achado vivo e curado na mesma passagem |
| E.4 família "script livre que decide gate" | CLOSED | W2.8 | ADR-192 + `.claude/governance/gate-scripts-manifest.txt` + step fail-loud em 4 workflows (`874117c`) | Rota **(b)-narrow** ratificada VERBATIM pelo Owner (§OQ). Censo achou ~50 scripts FREE; o pin cobre os 9 release-críticos, o resto segue livre por decisão |
| E.5 ADR de break-glass para kill-switches | CLOSED | W0.9 → W2.8 | `.claude/adr/ADR-193-break-glass-repo-kill-switches.md` `status: ACCEPTED` (`874117c`) | Renumerado 191→193 (191 tomado pelo spawn-contract do PLAN-178 Lote B) |
| E.6 `check_tier_a_spec_version_drift` vacuoso — registrar | CLOSED | W0.6 | memórias `feedback-check-tier-a-spec-version-drift-vacuous.md` e `feedback-verify-counts-real-path-is-local.md` | A promessa era registrar; foi registrado. O check segue vacuoso POR DESIGN documentado, não por esquecimento |
| E.7 shellcheck de CI só cobre `.claude/{scripts,hooks}` | **OPEN** | W4-C | `.github/workflows/validate.yml:296-315` → `find .claude/scripts .claude/hooks -name '*.sh'` | `scripts/tests/**` e `scripts/*.sh` seguem FORA do gate — o diretório onde morava a causa-raiz do W1 continua sem lint. O wiring é KERNEL PATH (`validate.yml`) ⇒ cerimônia W4-C, não executada |
| E.8 fechamento do scanner FIFO (§5.7) | CLOSED | W0.7(ii) | `.claude/scripts/check-model-deprecations.py:207-215` (`os.lstat` + `stat.S_ISREG` antes de abrir); controle positivo com 2 FIFOs plantados registrado no §Progress log S299 | Claim não-verificada do ledger virou claim verificada |
| E.9 célula maintainer→user | CLOSED | W0.7(i) | `scripts/tests/ownership_table.tsv:60` (`OWN-0070`, "maintainer install re-run as user: record must NOT be erased"); `PLAN-166/W1-ceremony-log.md:159-163` | A célula EXISTIA — o follow-up foi fechado no log, sem adicionar célula nova |
| E.10 linha morta no guard ancestral-symlink | CLOSED | W0 (verificação) | §Progress log S299 (fechamento noturno): zero hits de guard ancestral em `scripts/upgrade.sh` | A promessa do 167 §5.8 já estava cumprida — sem patch necessário. Verificação, não re-execução |
| E.11 `\s` em `grep -E`/`sed` nos runbooks | CLOSED | W0.10 | `docs/CTO-GUIDE.md:47,94` (`[[:space:]]`) | Planos landados ficaram fora por serem evidência imutável |
| E.12 higiene de ACs de 167/168 | CLOSED | W0.8 | `.claude/plans/PLAN-167-…md:728,738-739`; `.claude/plans/PLAN-168-…md:368` | Decisão do Owner registrada VERBATIM: "AC provado no registro de execução; checkbox não usado" |
| E.13 refactor `workflow_call` | DEFERRED-with-trigger | — | ledger `PLAN-169/ledger-S298.md:144`; `.github/workflows/npm-publish.yml:71,105-111` | Gatilho INALTERADO: "quando `release.yml` for refatorado por outro motivo". Não puxar agora |
| E.14 `OWN-0016` (defeito de PRODUTO) | DEFERRED-with-trigger | — | `.claude/adr/ADR-190-…md:107-111`; `scripts/tests/ownership-expected-reds.txt` | Gatilho: plano próprio; **fechar a célula e encolher expected-reds NO MESMO pack**. Segue RED por design dentro do nightly verde |
| E.15 `OWN-0024` / `OWN-0027` (defeito do TESTE) | DEFERRED-with-trigger | — | `.claude/adr/ADR-190-…md:112-114`; `scripts/tests/ownership-expected-reds.txt` | Mesmo gatilho e mesma ordem obrigatória do E.14 |
| E.16 nightly vermelho com causa nomeada até o port landar | CLOSED | W1 | nightly `32111138908` (2026-08-18) `success`; antes dele `32006620081`, `31933480267` | O gatilho declarado ("fecha quando B.d landar, aceite 62/3") foi CUMPRIDO; verde recorrente, sem editar a tabela |
| E.17 higiene de leitura do ADR-186 §5 | CLOSED | W3.5 | `.claude/adr/ADR-186-hook-deadline-policy.md` — nota histórica "resolvido e commitado em `6b5dd10`" (`e5ce982`) | |
| F.1 "sweep de portabilidade amplo" vs 1 linha | CLOSED | W1 | ver B.d — run `31286301110` | As 4 suspeitas seguem refutadas; o escopo reduzido foi o correto |
| F.2 "triagem inicial" vs contabilidade 65/65 | CLOSED | W1 | ver B.d | Virou causa-raiz com aceite falsificável, e o aceite foi atingido |
| F.3 `OWN-0073` era FALSE GREEN | CLOSED | W1 | §Progress log S299: rider `_selfcheck_mtime` (controle positivo antes de qualquer célula) + 0073 re-verificado GREEN com `got=REFRESH/HASH_SOURCE` no run `31286301110` | O sinal de mtime está VIVO no Linux — era exatamente o que o falso-verde escondia |
| F.4 `CEO_OVERHEAD_ACK` "não destrava Write" | CLOSED | W2.4 + W3.3 | ver C.3 | A memória estava errada; o fix foi no canal e na doc, NÃO na classificação de tool |
| F.5 `pair-rail-gate.sh` "inexecutável" | CLOSED | W2.5 | ver C.2 | Cura foi rota de auth, não `chmod` |
| F.6 "P0 FS case-insensitive ABERTO" | CLOSED | W3.5 | ver C.4 / E.17 | O que sustentava a leitura era texto histórico do ADR-186 §5 |
| F.7 marcador "é 12º site" (não era) | CLOSED | W2.6 | ver E.1 | O achado de maior valor técnico do lote |
| F.8 AC-3/AC-4 "abertos" = trabalho pendente | CLOSED | W0.5 | ver A.5.1-A.5.3 | Era bookkeeping, não implementação |
| F.9 `5.25 ms` era "flake de cauda p99" | CLOSED | W2.2 | ver B.c | Em CI o teste gateava a MEDIANA; a decisão foi mantida, agora com evidência do run 31288404989 |
| F.10 2º fator do parity não-causal | CLOSED | W3.2 | ver B.b | O harness já tinha a checagem forte; o workflow a desperdiçava |
| F.11 `.claude/scripts/verify-counts.sh` (path inexistente) | CLOSED | W0.6 | ver D.8 | Path correto registrado em memória; sweep do padrão `\|\| echo advisory` feito nas superfícies vivas |
| F.12 `ad9cc3a` "preserva o sentinel" (fechou pela metade) | CLOSED | W0.1 | ver D.1 | |
| F.13 promessa de "registrar em memória" não cumprida | CLOSED | W0.6 | ver E.6 | |
| F.14 ratificação `approx` prometida e ausente | CLOSED | W0.5 → W6.1 | ver A.5.4 — `pair-rail-verdict-v1.3.0-rc.2.md:44,83` | Claim de governança fechada em superfície ASSINADA |
| F.15 temor de estouro do timeout em Linux | CLOSED | W1 + W3 | `.github/workflows/ownership-nightly.yml` — prosa corrigida para 65 células / 3 reds (`e5ce982`); `timeout-minutes: 90` intocado | Runs reais 41-48 min sob teto 90 |

**Os 2 OPEN, ditos sem eufemismo.** E.2 e E.7 não têm patch no disco.
Ambos moram em superfície de KERNEL (`check_arbitration_kernel.py`,
`validate.yml`) e ambos exigem cerimônia com postura de override
própria — E.2 na W3-K (sessão separada por U-3), E.7 no pack W4-C.
Nenhum dos dois foi tocado nas cerimônias W3 (`e5ce982`) ou W2.8
(`874117c`), por escopo fechado declarado nos respectivos sentinels.
Enquanto não fecharem: um `grant` de kernel continua sem evento
auditável, e `scripts/tests/**` continua sem lint em CI.

## Progress log

- 2026-08-25 (S328): **night-run autônoma (~12 h, conta alternativa) —
  moldura e decisões do Owner (AskUserQuestion, verbatim).** Q5, cuja dona
  é este plano: **«Emenda + gate em pacote, e 1 rerun de madrugada
  (Recomendado)»** — autoriza a emenda ao ADR-163 (o gate hook-latency do
  `Validate` reprovou `a16ac96` com `check_output_secrets` p95
  361/425/229 ms contra teto 180 ms, sonda de spawn UNCONTENDED 7,76 ms,
  local 70–77 ms; e `56f050c` 209→435 ms — a sonda mede piso de SPAWN e
  é cega a runner lento-mas-descontendido), o gate relativo / sonda de
  execução em `profile-opus-4-7.py` + step do `validate.yml`, e a emenda
  ao ADR-144 §S220 (`opts.model` NÃO é inerte — W4.3 mediu), tudo em
  pacote de cerimônia próprio (S328-B); e UM rerun
  (`gh run rerun 32866209415 --failed`) às 03:03 de 26/08 por cron
  one-shot. W4.1.0 (probe de quota-resume): oportunista, no 1º estouro
  de quota da noite, saída em `PLAN-169/w4.1-probe-S328.md`. Moldura da
  noite: Q1 conta alternativa com quota integral (semanal 0 % medida no
  boot); Q4 «Push granular + pacotes independentes»; Q7 ordem «183 W5-b →
  179 w24 → ADR-163 → 185 → 169 W4.1 → reconciliação». Q2/Q3/Q6 estão
  registradas nos donos (PLAN-183 OQ-4; PLAN-185 §4; PLAN-179
  `staged-w24/README-COMO-MONTAR.md` item 1).
- 2026-08-20 (S315): **W4 ABERTA pelo bloco de probes de disco** —
  Owner escolheu a W4 como próxima unidade (AskUserQuestion, decisão
  verbatim no `### Registro de execução — W4 ABERTA`). Executada a
  fatia que o próprio W4 manda primeiro (W4.1.0/W4.2.0/probe-first do
  W4.3 — ver ressalva do W4.3 abaixo), read-only e $0. Resultados:
  sidecar presente e fresco em operação normal (`used_pct` 4,0) —
  **evidência de PRÉ-VOO, NÃO um GO**: o probe (ii) pergunta pela
  frescura no INSTANTE da exaustão, e isso só o live-fire responde; `StopFailure`/`PostToolBatch`/`TaskCompleted` existem no
  substrato mas NÃO estão wired; `ConfigChange` já existe (confirma
  "promover, não adicionar"); posturas cross-session inexistentes
  hoje; matchers hifenizados = 2 e `sys.exit(2)` = 0 reconfirmados.
  Três coisas que o probe mudou no desenho: (a) o corpo do W4.1 cita
  `used_percentage`, mas o sidecar entrega `used_pct` — consumidor
  escrito contra o nome citado **arma nunca**, silenciosamente; (b) o enum
  foi **RE-CAPTURADO** do bundle vivo 2.1.237 e é **idêntico** ao da
  2.1.220 (31 eventos, mesma ordem) — o drift temido não existe NESTA
  dimensão, e a checagem vira controle recorrente em CI; (c) o censo de
  `agent_spawn`=0 é **vacuidade** (zero named spawns na janela), não
  prova de gap. **Do bundle vivo saíram ainda 3 fatos de desenho do
  W4.1 que o plano não tinha** — o matcher do `StopFailure` casa contra
  o VALOR de `error` (não contra tool), o valor é `rate_limit`, e
  `quotaLimits` NÃO chega ao hook — **mais um falso-positivo real:
  `error:"rate_limit"` também é emitido em `model_blocked`, o que faria
  o hook gravar evidência de exaustão inexistente.** Detalhe e cura
  exigida no registro da W4. **Achado P0 — RETIRADO do W4-C e promovido a plano próprio
  `PLAN-182` (o item 9 do W4-C é, e segue sendo, APENAS o W1.3 scoped
  permissions herdado do PLAN-178; o W4-C guarda só um ponteiro de uma
  linha para o achado). Corrigido pelo pair-rail r4, que pegou este
  parágrafo ainda chamando o achado de "item 9 mandatório" depois de a
  decisão já ter sido revertida):** o fallback do audit
  dir é o literal `ceo-orchestration`,
  repetido em **63 módulos** (24 em `.claude/hooks/`, 39 em
  `.claude/scripts/`) — a proposta original dizia **2**, e as três
  rodadas de rail mais a varredura comportamental levaram o número a
  4 → 20 → ≥22 → **63**. Há **1.534 eventos de outro projeto gravados
  no log deste repo**, ativos. **Consequência de processo:** o Owner
  havia aprovado absorver isto no W4-C sobre a premissa de 2 arquivos
  em `_lib`; com o número real a decisão foi REVERTIDA na mesma sessão
  e o item virou **`PLAN-182`** (levantamento primeiro, especificação
  depois). O W4-C guarda só um ponteiro de uma linha. Abertos inalterados: W4 (desenho+implementação),
  W4-C, W5 restante, W6.2.

- 2026-08-19 (S314): **W3-K LANDADA (`c34e8e3`) — E.2 CLOSED; ledger
  vira 58/3/1.** Cerimônia de kernel em sessão própria (sentinel
  `W3K-approved.md.asc`, 00:25): `ceremony_sha` recebe sha256 real
  (`check_arbitration_kernel.py:540`), `kernel_override_used` dispara
  pelo `main()`, teste positivo de GRANT no lugar. Duas correções de
  escrituração nesta entrada: (a) a linha E.2 do ledger ainda dizia
  OPEN/"defeito intacto" — a correção nunca tinha descido até a linha;
  (b) a frase "PLAN-170 ainda NÃO existe" era falsa desde o próprio
  commit que a escreveu. Registro honesto de CI: o validate de
  `c34e8e3` foi **cancelled** (`cancel-in-progress` em trem de pushes);
  quem executou o gate até o fim foi o cron do `coverage.yml`, que
  pegou a classe bare-testcase do teste novo — curada em `9179ef2`,
  validate **success** em HEAD. Abertos inalterados: W4, W4-C (E.7),
  W5 restante, W6.2.

- 2026-08-18 (S312-S313): **três landings fecham a parte cerimonial
  deste plano e o §Ledger final fecha o AC-1.** (1) **W3 LANDADA**
  (`e5ce982`) — pack canônico re-staged por item semântico pós-GA,
  14 targets + 1 novo, G1-G7 verdes; detalhe no `### Registro de
  execução — W3 LANDADA` acima, não repetido aqui. (2) **W2.8 + W0.9
  LANDADOS** (`874117c`) — ADR-192 (gate-scripts, rota (b)-narrow) +
  ADR-193 (break-glass renumerado) + manifesto de 9 membros; dois
  abortos de gate ANTES do land, ambos curados por item; detalhe no
  `### Registro de execução — W2.8 + W0.9 LANDADOS` acima. (3) **W6.1
  CUMPRIDA fora deste plano:** o GA v1.3.0 saiu em 2026-08-17 pela
  rota rc.4 do PLAN-177 (tag `v1.3.0`, verdito
  `.claude/governance/pair-rail-verdict-v1.3.0.md`), e o PLAN-166
  fechou `done` na higiene autorizada `a71229e` — o título "via rc.2"
  ficou histórico, o objetivo não. (4) **E0 (W5) executado na S300** e
  registrado onde ele decide financiamento: `PLAN-172:28-36` — S
  conservador = 1,000, tempo-morto 59% de 723h sobre 14 planos, E1/E2
  DESFINANCIADOS pela regra pré-registrada. O pré-registro assinado
  (`PLAN-169/W5-preregistration.md.asc`) foi honrado: o resultado
  negativo publica igual. **PLAN-170 existe como `draft`**
  (`PLAN-170-e7-battery-execution.md`, criado pelo MESMO commit
  `1e3ffaa` desta entrada — a frase original "ainda NÃO existe" estava
  errada; corrigida S314). O que não venceu é o GATILHO de execução
  (pós-corte v1.4.0-rc.1), então o AC-6 segue parcial.
  **Aberto ao fim desta entrada:** W3-K (E.2, sessão separada), W4 +
  W4-C (inclui E.7), W5 restante e W6.2 (bump 1.4.0 = controle vivo do
  AC-7). O plano permanece `executing`.

- 2026-08-09 (S299, fix-forward pós-CI): **O primeiro Validate COMPLETO
  sobre o conteúdo W2 (run 31288404989) veio VERMELHO com 4 achados —
  todos meus, todos reais, todos curados no mesmo ciclo:** (1) meu
  PRÓPRIO teste novo do W2.3 pegou no Linux que a gramática via
  `grep -qE` aceita nome com NEWLINE embutido (grep casa POR LINHA —
  classe per-line-vs-whole-string, prima da substring-vs-exact) ⇒
  validação vira bash `[[ =~ ]]` whole-string; (2) allowlist de
  env-hygiene regenerada (`--init`) para incluir o teste novo (+
  entradas drenadas saíram — aperto na direção certa); (3) **o gate
  p95-on-CI do W2.2 flakou no PRIMEIRO run real (p95=6,31ms vs mediana
  3,83ms)** — runner carregado desloca a distribuição INTEIRA, então
  percentil de cauda precifica o runner, não o código ⇒ MEDIANA
  reavaliada e MANTIDA (agora com evidência, não intuição); N=200 +
  índices derivados + pré-condição FICAM; emenda ADR-163 (draft +
  staged) reescrita nesse sentido; (4) o teste de conformância TLA
  assertava o DEFEITO da implementação, não o spec —
  `MaxRoundsExhausted` no .tla sempre exigiu `jaccard < THRESHOLD`
  para "failed", então o W2.9(iii) trouxe o código À conformidade;
  teste reescrito para o invariante real (S1 = bound de rounds,
  preservado). Suítes locais 43+1+1 (incl. controle CI=1 simulado)
  verdes. Re-pass r2 foi morto (candidato stale) e será relançado
  sobre o HEAD pós-fix.

- 2026-08-09 (S299, fechamento noturno): **Preparação completa da fila
  do Owner.** (1) **Pack W3 STAGED + VALIDADO** em
  `PLAN-169/staged-w3/` — 12 arquivos (11 alvos + ADR-191 novo), 19
  patches por âncora única, MANIFEST.sha256 + BASELINE.sha256
  (pins anti-stale: a lição do step1); validação: bash -n 3/3,
  py_compile 4/4, R9 contra o gerador STAGED nos 2 sentidos (newline ⇒
  degraded sem abort; saudável ⇒ substitui). Bug real do builder pego
  na validação: comentário python com apóstrofo+backticks dentro de
  heredoc-em-$() quebra o parser do bash — bisectado e curado
  (comentário ASCII-safe + nota no próprio arquivo). (2)
  **OWNER-W3-LAND.sh** fail-closed em 7 gates (G0 janela, G1 baseline
  anti-stale, G2 manifest, G3 GPG+anchor==HEAD, G4 simulação em clone,
  G5 apply por tabela, G6 touched−scope=∅ + bateria, G7 commit) +
  **W3-approved-draft.md** (sentinel pronto para assinar, escopo
  fechado, "fora deste pack" explícito). (3) **W5-preregistration-draft.md**
  — desenho E0-E4 imutável pronto para assinatura (execução E1-E4 =
  PLAN-170). (4) **repass-r2/run-repass-r2.sh** — re-pass codex do
  delta rc.1→candidato a partir de worktree detached limpo, pipeline
  do r1 (redactor ADR-114 + controles de estrutura), LANÇADO nesta
  madrugada contra o HEAD final da noite. (5) **OWNER-MORNING.md** —
  fila consolidada: trem GA (1 verdito+2 tags+hold), 1 decisão (W2.8),
  2 assinaturas (W5, W3). E.10 verificado FECHADO (zero hits de
  guard ancestral no upgrade.sh — promessa do 167 §5.8 cumprida, sem
  patch necessário). Fronteiras respeitadas: W3-K/W4/W4-C ficam para
  sessões próprias (kernel + decisões); NADA de conteúdo 1.4 aplicado
  em superfície viva — o HEAD segue candidato rc.2 limpo.

- 2026-08-09 (S299, madrugada): **W2 EXECUTADO INTEIRO (9/9 itens) em
  superfícies confirmadas FREE pelo predicado (rodado em TODOS os alvos
  antes de tocar — 4 correções de fronteira registradas abaixo).**
  **W2.2**: Case-A N=100→200 + claim-producer N_TRIALS=20→40 (índices
  p95/p99 COLAPSADOS — `int(19*.95)==int(19*.99)`, a classe exata do
  ADR-163); índices derivados de n (truncação `_pct_of_sorted`),
  pré-condição de colapso assertada, CI gateia p95 REAL (não mediana);
  emenda ADR-163 DRAFTADA (`PLAN-169/W3-adr163-amendment-draft.md` →
  pack W3); provas: pytest verde (case_a 0.38s; e2e 6.4s, 2+1 xpassed).
  **W2.3**: ladder de resolução EXATA no injector — (1) heading por
  IGUALDADE de componente (mata a classe substring: "security engineer"
  ⊂ "cybersecurity engineer"), (2) tabela explícita nome→slug para
  `.claude/agents/` (DevOps Engineer→devops.md), (3) papel só-de-tabela
  ⇒ perfil sintetizado DA LINHA rotulado (VP Engineering), (4) nome
  fora do mapa ⇒ exit 3 fail-closed; gramática aceita `/` e `&` (UI/UX
  Lead, Accessibility & i18n Engineer) sem abrir traversal (sem `.`);
  rung 2 emite corpo com `## `→`[h2] ` (a demoção `###` ainda continha
  o marcador como SUBSTRING — a mesma classe, pega pelo teste); provas:
  41 passed (6 casos novos + 2 suítes de regressão). **W2.4**: docs
  overhead-ack (EN+pt-BR) agora prometem O QUE EXISTE: prefixo Bash
  por-comando, janela deslizante 5 min, NENHUM canal por-ação para
  Edit/Write, export de sessão auditado; canal novo → W3.3. **W2.5**:
  Gate 1 aceita api-key OU login (fail-closed sem ambos); Gate 2 SÓ na
  rota api-key (r20-P2: a última rotação 2026-05-09 = 91d reprovaria
  login válido); + cura do C.2: `timeout` coreutils não existe no macOS
  → perl alarm; provas DINÂMICAS nesta máquina: rota login PASS
  end-to-end, rota api-key PASS c/ override, controle positivo FAIL
  rc=1 sem override. **W2.6**: `.claude/.framework-version` = 12º site
  (`_SITES` + `VERSION_SITES`, espelhos comentados); controle
  transitório: dessinc 9.9.9 ⇒ rc=1 nomeando o site, restaurado ⇒ rc=0
  (janela do nightly não cruzada; HEAD limpo); 52 bump-tests verdes;
  controle ao vivo = bump 1.4.0 (W6.2). **W2.7**: padrão `N ADRs
  document` vigiado; drift REAL achado vivo (GUIA 189 vs disco 190) e
  curado; expectation-set +`adrs@GUIA`; controle por rótulo: planta 999
  ⇒ `DRIFT: docs/GUIA-COMPLETO.md: cites adrs=999, live=190`,
  desplanta ⇒ 0; 22 tests verdes. **W2.8**: censo mecânico achou **~50
  scripts FREE decidindo gates** (os 2 nomeados eram 2 de 50); proposta
  (b)-estreito: manifesto checksum p/ 6 release-críticos, resto livre —
  `PLAN-169/W2.8-free-script-gate-family.md`; DECISÃO na fila do Owner.
  **W2.9**: converge com 3 curas provadas — (i) Risks presente + zero
  bullets ⇒ `RisksSectionEmptyError`/exit 4 barulhento por crítica,
  (ii) `resolved_count`/`novel_count` reportados separados (Jaccard
  punia cura — documentado), (iii) teto+threshold ⇒ CONVERGED (§12.4;
  terminação preservada); regressão AO VIVO: round-5 real segue exit
  3/unresolved (sem reescrita de história); controles sintéticos: teto
  convergido rc=0, Risks-vazio rc=4; teste que CODIFICAVA o defeito
  reescrito; 57 passed. **W2.10 (parte livre)**: F2 `_tier_rank` ganha
  gen-5 (ladder tier-major; a inversão promote/demote morre), F3
  pricing gen-5 no value-dashboard (frota corrente custava None), F9
  10 replacements do ledger → opus-5/sonnet-5 (registro honesto em
  `_meta`, `fetched` intocado), F10 aliases gen-5 no normalizador, D3
  display do injector sem id de geração, D7 dirigido:
  cost-of-operation ganha as 4 linhas gen-5 + "current flagship" do
  4-8 vira "N-1, active" (provider-pricing/MODEL-ROUTING já eram
  gen-5); 181 tests verdes. **Correções de fronteira (predicado >
  lista da auditoria):** F4 (`check_codex_stop_review.py`), F8+D1
  (`audit_log.py`), D2 (`check_agent_spawn.py`) são CANONICAL ⇒ pack
  W3; D6 (`validate.yml`) é KERNEL ⇒ W4-C; F7 (tournament) é
  model-CHOICE ⇒ W4.3 com F1/F5/F6. Traduções: drift=0 pós-W2.4.

- 2026-08-08 (S299): **W1 EXECUTADO (fix + riders + sweep; validação D3
  disparada).** Causa-raiz confirmada PIOR que "BSD-first": no GNU,
  `stat -f '%m'` SUCEDE imprimindo o MOUNT POINT (stdout contaminante)
  — o fallback nunca rodava e o `continue` silencioso em `_obs_mtime`
  descartava o lixo ⇒ sinal de mtime morto em TODAS as células no
  Linux (REFRESH byte-idêntico invisível; sub-detecção 0017/0021).
  Fix: `_stat_mtime` GNU-first (padrão canônico `install.sh`
  detect_mtime) + validação de output (não-numérico ⇒ `MTIME-ERR`,
  nunca descarte). Rider fail-closed: `MTIME-ERR` em BEFORE/AFTER ⇒
  HARNESS-ERR da célula (stderr + ERR++). Rider FALSE-GREEN:
  `_selfcheck_mtime` — controle positivo ANTES de qualquer célula
  (rewrite byte-idêntico com timestamp bumpado tem de mudar a
  assinatura, arquivo E diretório; falha ⇒ exit 2). PROVAS no Darwin:
  smoke `--only 0001,0017,0021` = 3/3 GREEN ERR=0; shim GNU-simulado
  (stat -c válido, -f devolve mount point) ⇒ selfcheck PASSA; shim
  sinal-morto ⇒ recusa com exit 2 real. Sweep da classe
  `A 2>/dev/null || B` no harness: ÚNICO contaminante era o par stat;
  demais fallbacks (mktemp/git describe/_hash_file sentinelas) têm
  A-sucesso estável entre plataformas; `_hash_*` vêm da lib de
  produção já vetada. **Deferral registrada:** o comentário de
  estimativa em `ownership-nightly.yml` (tempo observado do run
  31246426017; número fora deste plano por AGENTS.md
  no-throughput-claim) foi BLOQUEADO pelo guard canônico
  (`.github/workflows/` exige sentinel, ADR-010) ⇒ entra no pack
  canônico **W3** com o resto; `timeout-minutes: 90` intocado, não
  gateia o aceite 62/3. **VALIDAÇÃO D3 CUMPRIDA (run 31286301110,
  2026-08-09 00:30→01:11 UTC, workflow_dispatch sobre `af192dd`):
  conclusion=SUCCESS — `GREEN=62 RED=3 AMBIG=0 HARNESS-ERR=0`, conjunto
  RED exato {OWN-0016, OWN-0024, OWN-0027} (by-design), zero resíduo de
  plataforma. OWN-0073 re-verificado especificamente: GREEN com
  got=REFRESH/HASH_SOURCE — o sinal de mtime está VIVO no Linux (a
  célula que o sinal morto cegava). Primeiro nightly verde da história
  do workflow. Run saudável ~41 min (vs ~32 do run cego — os walks de
  mtime reais custam; teto 90 mantém folga). W1 FECHADO.**

- 2026-08-08 (S299): **W0 EXECUTADO INTEIRO** (`reviewed→executing`
  neste commit). Pack pushado a `origin/main` (`57119b3`, ff de
  `plan169-pack`); CI do push VERDE — **Translations drift CURADO**
  (vermelho desde 04/08 fechado; A.0.3) + Validate SUCCESS. Debate
  reconfirmado no disco (5 rounds, terminal `round-5/consensus.md`
  unresolved/max-rounds — estado exato que o Owner ratificou em R-B).
  Itens: **W0.1** verificado (header ⛔ + `100644` no pack). **W0.2**
  header OBSOLETO aplicado a `PLAN-166/OWNER-W1-LAND-step1.sh`
  (substituído por step1b; re-executar reverteria o PLAN-167). **W0.3**
  verificado (0 tarballs untracked; padrão em `.gitignore:25` com
  causa). **W0.4** drift local = 0 e workflow verde no push. **W0.5**
  §-final escrito no PLAN-166 (subsunção AC-3/AC-4 com evidência,
  ratificação `approx`/collect-errors AGENDADA para o material assinado
  da rc.2, cura da leitura "stranded"). **W0.6** 2 memórias escritas
  (`feedback-check-tier-a-spec-version-drift-vacuous`,
  `feedback-verify-counts-real-path-is-local`) + sweep `|| echo
  advisory`: superfícies VIVAS limpas (único hit em PLAN-156 landado =
  evidência imutável; `release.sh:375` já fail-closed com path
  correto). **W0.7(i)** transição maintainer→user EXISTE na tabela —
  `OWN-0070` (tsv:60) — follow-up fechado no `W1-ceremony-log.md`;
  **W0.7(ii)** controle positivo do scanner FIFO (§5.7) RODADO: 2
  FIFOs plantados (raiz + subdir), `check-model-deprecations.py
  --check` terminou em 0.0s rc=0 E escaneou o arquivo regular
  (total=1, não-vacuoso); evidência de código `:207-215` (lstat +
  S_ISREG antes de abrir) — fechamento do §5.7 REGISTRADO. **W0.8**
  convenção ratificada registrada no §9 do PLAN-167 (+ registro do
  land `7c0828a` que faltava) e no §4 do PLAN-168. **W0.9** aceite do
  Owner REGISTRADO (OQ-3): ADR break-glass entra no pack W3; até lá
  `CEO_PAIR_RAIL_VERDICT_OPTIONAL` sem doutrina segue risco nomeado da
  janela de release. **W0.10** sweep POSIX: 2 sites curados em
  `docs/CTO-GUIDE.md` (`\s`→`[[:space:]]` em grep -E vivo); demais
  hits = regex Python (válido) ou evidência imutável. **W0.0**: zero
  dispatch de Workflow no W0 (gate read-only honrado; probes seguem
  DEVIDOS antes de qualquer escrita via Workflow em waves futuras).
  Nota operacional: overhead-guard P4 bloqueou Edit legítimo 2× no
  W0 — evidência adicional para C.3.

- 2026-08-08 (S298, closeout): **RATIFICAÇÃO DO OWNER em chat**
  ("ratifica tudo com as recomendações e commita o pack") — R-A
  (`draft→reviewed`), R-B (gate §12.4 aceito), R-C (deferral), OQ-1..5
  e W0.8 conforme recomendações; adendo fleet-currency (auditoria
  Fable) registrado como W2.10 + W4.3; pack commitado em branch
  `plan169-pack`. Waves LIBERADAS na ordem pinada.

- 2026-08-08 (S298): plano criado; ledger de 6 varreduras anexado;
  pesquisa substrato+academia anexada (`PLAN-169/research-*.md`).
- 2026-08-08 (S298): debate round 1 — 3× ADJUST (VP/Sec/DevOps),
  consensus com 20 decisões (`PLAN-169/debate/round-1/consensus.md`);
  v2 aplicada (este texto). Evidências vivas colhidas na própria
  sessão: fuzzy-match do injector (C.1) entregou persona errada no
  spawn do debate; overhead-guard P4 bloqueou Edit em fan-out
  legítimo (C.3) 2×; workflow `agent()` sem `agent_spawn` no audit
  log (probe b, preliminar).
- 2026-08-08 (S298): debate rounds 2-5 — r2/r3 regenerados no schema
  de máquina (v2.1→v2.4); r4 convergiu (jaccard 1.0) sobre a v2.4;
  **r5 = triade COMPLETA sobre a v2.5 EXECUTÁVEL (o rail evoluiu o
  plano além do v2.4): Security+DevOps ACCEPT, VP ADJUST/MF-D
  aplicado; máquina jaccard 0.692/max-rounds ⇒ `status: unresolved` +
  ESCALAÇÃO ao Owner (§12.4), terminal em `round-5/consensus.md`;
  round-4 rebaixado a consensus intermediário.** O CEO NÃO declara o
  gate met — recomenda ratificar como design-coherent.
- 2026-08-08 (S298): rail codex r1 (3×P1: script 167 revertia o 168 →
  neutralizado ⛔+exit; anexos de pesquisa arquivados fora do repo —
  no-speed-claim; contaminação varrida por classe) e r2 (2×P1+5×P2:
  `disableWorkflows` no escopo W4-C; fleet 170 via clone dedicado —
  `--settings` não relaxa project-refuse; E0: fração serial inclui
  tempo-morto, M=14 pinado; exec bit 100644; header v2.2) → v2.2.
  W0.4 triado E curado na sessão (seção night-mode espelhada no
  pt-BR). Transcripts do rail: archive privado da sessão S298.
