---
plan: PLAN-186
round: 3
rounds_completed: 3
final_verdict: PROCEED
synthesized_at: 2026-09-02T23:00:00Z
synthesized_by: CEO via Technical Writer
---

## 3-round arc summary

- **Round 1** — 3 críticos anonimizados (DevOps Engineer, LLM FinOps Architect, VP
  Engineering), 3× `ADJUST`, 26 must-fix. 9 consensus findings (C1-C9): o eixo da matriz
  §2b estava errado (blast radius → natureza do artefato), o orçamento era insatisfazível
  no próprio piso (850k < 9 × 97k de gate-boot), e «`.github/workflows/**` é livre por
  cerimônia» era falso em disco. 17 insights de agente único mantidos após verificação, 6
  rejeitados ou deferidos com razão escrita. Verdict `RUN-ANOTHER-ROUND`.
- **Round 2** — 3× `ADJUST`; dos 26 must-fix do round 1: 20 resolvidos, 6 parciais, 0
  abertos; 13 novos (12 após dedup), todos aplicados. 3 consensus findings (D1: o
  derivador em disco da W1 classifica sob o eixo antigo, é insumo, não entregável; D2: o
  orçamento se refuta com a própria aritmética, corrigido para três campos — trabalho,
  gate-boot, total; D3: a partição §2b não era total, faltava a linha de
  pesquisa/leitura). Achado material: W1 e W4 tocam paths canônicos e são cerimônia GPG.
  Verdict `PROCEED`.
- **Round 3** — 3× `ACCEPT`, **zero must-fix**. Os três críticos confirmaram em disco que
  os 7 must-fix do round 2 (MF1-MF7) e os riscos residuais (R-DEV16-20, R-FIN15-18,
  R-VP22-23) estavam resolvidos, sem achado novo de escopo. Dois nice-to-have advisory
  (não bloqueantes): registrar os `[DÚVIDA]` do derivador antigo como decisões TOMADAS sob
  §2b quando a tabela por sítio for publicada; lembrete no Progress log para re-ancorar
  AC-11 se o PLAN-184 fechar antes da W4. Plano `design-coherent`.

## Final plan deltas

Aplicadas as 7 decisões do Owner (S339, AskUserQuestion) sobre o plano que saiu do round 3:

- **Frontmatter** — `budget_tokens`/`budget_tokens_gateboot`/`budget_tokens_total`
  re-somados (W2 removida, W1+W3 fundidas, +W-ROTA): 1,06M-1,84M trabalho + 1,36M-1,75M
  boot = 2,42M-3,59M total; `budget_sessions` 15-18 → 14-18; `tier_mix_estimate` perde o
  A/B (`seat_w2`/`seat_resto` → `seat_pre_w1`/`seat_post_w1`) e o mix de subagente sobe
  Opus 5 (0,45→0,55) e desce Sonnet 5 (0,50→0,40) pelo discriminante de artefato (OQ-3);
  `external_wait`/`eta_calendar` perdem os 14 dias da W2. Comentário `# UNIDADE` marca
  `budget_tokens`/`budget_tokens_gateboot` como unidade LEGADA agora que OQ-6 fechou a
  normativa repo-wide nos faturáveis.
- **§2 item 1** — pin do assento decidido (OQ-1): fixa `claude-fable-5-1` na cerimônia de
  roteamento, sem A/B.
- **§2b (matriz)** — nova linha discrimina EXECUTA-texto (Sonnet 5) de EXECUTA-código/config
  (Opus 5, mesmo com pergunta fixada); assento vira `claude-fable-5-1` fixo; nota de
  ratificação da OQ-3 adicionada.
- **§3 Waves** — W2 (A/B do assento) removida. W1 (herança explícita) e W3 (camada T)
  fundidas em **W1 — Cerimônia de roteamento** (OQ-9), com o pin do settings.json
  (OQ-1) e a rota (a) do ADR-149 + migração dos agents (OQ-2) incorporados. Nova wave
  **W-ROTA** (OQ-7) para a tabela fonte-única papel→model id, posicionada depois da W1.
- **Acceptance criteria** — AC-4 (A/B da W2) removido; AC-5 relabelado (W3) → (W1); novo
  AC-17 (W-ROTA) para a tabela fonte-única.
- **Open questions** — OQ-1, 2, 3, 6, 7, 8, 9 marcadas `Decidida 2026-09-02` com o texto
  verbatim da opção escolhida pelo Owner; OQ-4 e OQ-5 permanecem como medição.
- **Riscos** — bullet das waves canônicas atualizado de "três de sete" para "duas de
  seis"; Progress log ganha a entrada do round 3.

## Lessons for the debate process itself

- **Rotular uma wave sem consultar o oráculo `--is-canonical` custou um CRITICAL no round
  1** — a frase «`.github/workflows/**` é livre por cerimônia» só foi refutada porque um
  crítico rodou `check_canonical_edit.py` contra o disco em vez de confiar na memória do
  domínio. Doutrina para debates futuros: toda claim de canonicidade/gate se verifica
  contra o script, nunca se assume.
- **Contagem de sítios por `grep` errou 17 vs 10** no censo dos `agent()` sem `model:` (05
  §4.3): 7 das 17 ocorrências textuais eram comentários. Contagem sobre superfície viva
  exige filtrar por AST/execução, não por padrão textual — a mesma classe que a
  memória do repo já registra como `feedback-grep-counts-are-wrong-derive-behaviorally`.
- **Partição que não cobre o domínio não classifica** (D3, round 2): a matriz §2b original
  não tinha casa para «pesquisa/leitura sob pergunta fixada» e por isso `censo` inteiro
  caía em DEFINE, o que teria condenado retroativamente os pesquisadores em Sonnet 5 cuja
  citação sustenta a própria matriz. Uma matriz de roteamento tem de ser auditada como
  PARTIÇÃO TOTAL, com eixo declarado, antes de virar norma.
- **O sintetizador refutou 4 claims de críticos com evidência em disco** ao longo dos três
  rounds: a contagem de 3 sítios do censo do W4 (K16, cresceu para 5+), a alegação de que
  `orçamento` cabia no piso antigo (D2), a frase sobre workflows livres por cerimônia (C1),
  e a suposição de que «censo mecânico» inteiro era seguro em Sonnet 5 até a OQ-3
  restringir por tipo de artefato. Em cada caso, a refutação exigiu rodar o comando ou ler
  o arquivo citado — nunca aceitar a citação por autoridade do arquétipo.
