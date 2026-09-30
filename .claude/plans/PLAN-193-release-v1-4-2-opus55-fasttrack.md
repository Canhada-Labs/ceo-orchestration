---
id: PLAN-193
title: v1.4.2 expressa — Opus 5.5 padrão, Codex 0.156.1 e via expressa de adoção
status: done
reviewed_at: 2026-09-30
completed_at: 2026-09-30
related_commits: [67b844b609e1, 778acf27d1db, b4033b2e3527, a12a32aee2ad, 1c480b442f0b, 36bbe90c370b, 9a486d29a842, fadb5f972387, b55084da6dd8, 80eb46d8f372]
created: 2026-09-22
owner: CEO
depends_on: [PLAN-192]
level: L3
budget_tokens: "levantamento S357 ~4,7 M (18 agentes, feito); kit GA 1.4.1 ~1-2 M; wave-opus55 2-4 M com rail; re-pin codex ~0,3 M; via expressa (livre) ~1-2 M; re-pass rc.1 + GA = cota codex do Owner"
budget_sessions: "1-2 (S357 abre; o GA da 1.4.1 e a rc.1 da 1.4.2 podem cair no mesmo dia se o rail convergir)"
context_risk: high
external_wait: "Owner: corte do GA 1.4.1 (2 pinentry + SIM + npm); PIN-SIGN logo depois do GA (o 0.156.1 já está instalado desde 2026-09-23 — nenhum reinstall); assinaturas do re-pin, da wave-opus55 e da relmeta-142; corte da rc.1 e do GA 1.4.2 (hold ADR-103 de 24 h entre eles). CI: Smoke Install ~1h50 por push que toque templates/hooks/upgrade.sh/.framework-version"
eta_calendar: "GA 1.4.1 em 2026-09-22/23; rc.1 da 1.4.2 em 2026-09-23/24; GA 1.4.2 >= 24 h depois"
tags: [release, model-adoption, opus-5-5, codex-pin, fast-lane, adopters]
---

## Context

**Pedido do Owner (S357, 2026-09-22, verbatim):** «Acabou de lancar o opus 5.5, preciso que ajuste o
modelo, use esforco maximo, maxima pararelizacao, e ajusta os pontos emergenciasi pra gente atualizar
esse modelo e tbm a ultima versao do codex, para os usuarios terem acesso rapido. precisamos evoluir.»
Depois, na mesma sessão: status dos planos começados; «tem como incluir algo tbm agora?»; varrer o que
mudou nos últimos updates do Claude; «já coloca o 5.5 padrão com ultracode no ceo orchestration como
padrão»; «quero max + ultracode juntos, aplica assim, mas antes de aplicar só checa se realmente vale a
pena».

**Medido na S357 (2026-09-22; Claude Code 2.1.280, codex-cli 0.155.0 instalado; HEAD `19771fa1`).**
Levantamento de 9 frentes com verificador adversarial cada (23 fatos refutados e corrigidos antes de
entrar aqui); ids verbatim, sem corpo de transcript.

| fato | valor | fonte |
|---|---|---|
| id do modelo | `claude-opus-5-5` (sem data; é o snapshot); Bedrock `anthropic.claude-opus-5-5` | models overview + migration guide (platform.claude.com) |
| preço | US$ 4 / 20 por MTok; cache read US$ 0,20 = **0,05×** (não 0,1×); batch 2/10 | pricing page |
| esforço padrão | **medium** no Opus 5.5 (os outros: high); suporta low..max | effort doc + catálogo do binário 2.1.280 |
| Claude Code mínimo | **2.1.280** | model-config doc + CHANGELOG 2.1.280 |
| Opus 5 | segue Active (aposentadoria ≥ 2027-07-24); a mudança é ADITIVA | model-deprecations |
| `availableModels` no harness | casa por PREFIXO de segmento: a entrada `claude-opus-5` JÁ libera `claude-opus-5-5` | binário `wS()` + 4 sondas `claude -p` |
| precedência | `settings.local.json` > `settings.json` do projeto; arrays mesclam; `fallbackModel` não mescla | binário `I6()` + sonda R4 |
| ultracode | chave de settings `ultracode: true` = xhigh + orquestração; o lembrete permanente exige esforço efetivo == xhigh | binário + sondas C/F |
| `max` | não persiste em `effortLevel` (só low..xhigh); só via env `CLAUDE_CODE_EFFORT_LEVEL`, que DESLIGA o ultracode permanente | binário + sonda F (com `high`) |
| Codex | **0.156.0 estável publicado hoje** (npm 19:55Z; darwin-arm64 20:02Z); `latest` = 0.156.0, FORA do range `<0.156.0` | `npm view`, `gh api releases` |
| superfície `codex exec` | idêntica entre 0.155.0 e 0.156.0 (`exec --help` e `exec review --help` byte a byte) | binário extraído no scratchpad |
| Codex (2026-09-23) | **0.156.1** (hotfix da 0.156.0) publicado 02:45Z; `latest` = 0.156.1; o Owner o instalou globalmente ⇒ rail fail-CLOSED até o re-pin; `exec --help`/`exec review --help` idênticos aos do 0.155.0 | `npm view`, `npm pack` + sha256, pack `PLAN-193/codex-pin-0156/` |
| upgrade.sh | `_T54_BASELINES_JSON`: arrays têm `superseded` (1 entrada, 6 ids); a folha ESCALAR `model` NÃO tem ⇒ trocar o pin deixa todo adopter v1.2.0–v1.4.1 em `claude-opus-5` com só um WARNING | `scripts/upgrade.sh:165-178, 3447-3518` |
| adapter live | `_ADAPTIVE_ONLY_MODELS` não cobre `claude-opus-5`, `claude-sonnet-5` nem `claude-opus-5-5` ⇒ `/effort` manda `budget_tokens` (HTTP 400) — 2.ª ocorrência da classe | `.claude/hooks/_lib/adapters/live/claude.py:90-150, 710-719` |
| acoplamento de instrumento | `check-model-currency.py` exige a linha de preço no `cost-table.yaml` NO MESMO patch do append no ADR-149 | `test_check_model_currency.py` |
| CLAUDE.md | 39.968 bytes; teto de 40.000 do governance completo ⇒ nenhuma linha nova sem aparar | `validate-governance.sh:632` |
| bomba de calendário | PLAN-190 vira `unhealthy` em 2026-10-18 (lista em bloco lida como vazia) | `check-staleness.py:114-124, 205-209` |

**Decisões do Owner nesta sessão (AskUserQuestion; verbatim das opções escolhidas):**
- Release: «GA 1.4.1 + 1.4.2 expressa».
- Papel do Opus 5.5: «Padrão + piso VETO» (entra no working set, vira o `model` padrão, fica elegível a
  papéis com veto; fallback segue `claude-opus-5`; os agentes de veto seguem em `claude-fable-5` até medir).
- Escopo: «Modelo + Codex + via expressa».
- Commits: «Sim, lands livres» (só não-canônicos, nesta sessão).

## Goal

Adopters com Claude Code ≥ 2.1.280 abrem sessões em Opus 5.5 pelo `upgrade.sh --pin v1.4.2-rc.1` no
mesmo dia da rc e pelo npm no GA; o pair-rail roda no Codex 0.156.1 pinado; e a PRÓXIMA adoção de modelo
ou de Codex é gerada por ferramenta, não reescrita à mão.

## Approach

Três trilhos em paralelo, com UMA ordem obrigatória no meio: **o GA da 1.4.1 sai antes de qualquer
mudança canônica** (o GA promove a árvore da rc.1 e corta no Codex 0.155.0 pinado — o 0.156.1 global não
entra no corte: o runner do re-pass cai na rota do `npx` do 0.155.0).

1. **Agora, sem release (W0).** Override local do Owner (`settings.local.json` é canônico para o guard ⇒
   o Owner aplica com um comando `!`; o script foi revisado e testado em cópia com revert byte a byte).
   Doc para adopters da mesma rota (o harness já libera o 5.5 pelo prefixo). Correção da bomba do PLAN-190.
2. **GA 1.4.1 (PLAN-192).** Kit derivado do kit da rc.1 pelo molde do GA da 1.4.0; re-pass; corte.
3. **1.4.2 expressa.** Re-pin do Codex 0.156.1 → wave-opus55 (ADR-149 Amendment 3) → cura da classe
   adaptive-only → via expressa (ferramentas livres) → relmeta-142 → rc.1 → 24 h → GA → npm → adopters.

Alternativas descartadas (medidas): waiver de `rc_hold` (canônico e «honesto só sem adopters» pelo
próprio arquivo); dobrar o 5.5 no GA da 1.4.1 sem rc.2 (passa no `release.yml` mas quebra «o GA promove
a árvore da rc.1»); rc.2 da 1.4.1 (reinicia o hold e atrasa o GA do guard de Workflow, urgência de 18/09).

## Items

### W0 — agora (sem cerimônia de release)
Check: none (doc-only) para o override local — o Owner confere abrindo uma sessão nova («Ultracode is on» + `/model` = claude-opus-5-5)
- [ ] Owner roda o comando `!` do override local (`model` + `ultracode`; `max` só se o A/B pré-registrado aprovar)
- [ ] PLAN-190: `related_commits` em lista inline (desarma 2026-10-18) — Check: python3 .claude/scripts/check-staleness.py --json
- [ ] doc de adopter: liberar o Opus 5.5 localmente hoje (rota C) — Check: none (doc-only)

### W1 — GA v1.4.1 (executa o PLAN-192 W6)
Check: bash .claude/plans/PLAN-192/test-ga-kit.sh && python3 .claude/plans/PLAN-192/derive-ga-kit-141.py --check
- [ ] kit do GA derivado + harness verde + revisão cruzada + commit livre
- [ ] re-pass do GA (codex 0.155.0 pinado; regra de parada: 2 rodadas; NO-GO só por condição FALSA ou P0)
- [ ] Owner: `OWNER-GA-CUT.sh` com a máquina QUIETA (passo 1 roda testes de p99 absoluto)

### W2 — re-pin do Codex 0.156.1 (depois da tag do GA)
Check: python3 .claude/hooks/check_pair_rail.py --verify-codex-pin "$(command -v codex)"
- [ ] pack `PLAN-193/codex-pin-0156/` clonado de `PLAN-189/codex-pin-0155/` e remontado para o 0.156.1 (2 canônicos: range `<0.157.0` + manifesto; valores medidos por `npm pack` no scratchpad; ensaio verde)
- [ ] Owner, logo depois do GA: pack no checkout vivo, ensaio, commit livre e o SIGN, na ordem do README do pack — o 0.156.1 JÁ está instalado: NÃO reinstale (qualquer outro binário faz o P0 recusar); a janela de rail fechado está aberta desde a instalação (2026-09-23) e fecha no SIGN

### W3 — wave-opus55 (ADR-149 Amendment 3)
Check: python3 .claude/scripts/generate-available-models.py --check && python3 -m pytest .claude/hooks/tests/test_adr149_validator_parity.py .claude/scripts/tests/test_check_model_currency.py -q
- [ ] derivador novo cortado do HEAD (as âncoras do fable51 estão 34/55 velhas) com o censo de 40 espelhos, não os 30 do fable51
- [ ] `upgrade.sh`: `superseded` ganha a lista de 7 ids E a folha escalar `model` ganha ramo `superseded` genérico (cura da classe)
- [ ] VETO floor (`agent_frontmatter.py` + ADR-149) + pin de sessão (`ultracode` fica só no override local do Owner — OQ-6)
- [ ] preços ($4/$20, cache 0,05×) em todas as tabelas (cost-table, budget-summary, ceo-cost-transcripts, success-receipt, docs)
- [ ] rail codex nos bytes canônicos até rodada limpa; sentinel; SIGN/LAND

### W4 — cura da classe adaptive-only
Check: python3 -m pytest .claude/hooks/tests/test_claude_adapter_thinking.py -q
- [ ] a lista de modelos adaptive-only deriva do ADR-149/metadados, não de literal (2.ª ocorrência ⇒ estrutural)

### W4b — cura do ledger de Workflow (FN-04; declarada known-open na condição 23 do GA 1.4.1)
Check: python3 -m pytest .claude/hooks/tests/test_check_workflow_launch.py -q
- [ ] o PreToolUse do Workflow não persiste bytes de `scriptPath` antes da decisão de permissão (confinar ao projeto e/ou gravar só o hash; cerimônia canônica em `launch_ledger.py` + `check_workflow_launch.py`), com controle vermelho do canário S357; sequencial DEPOIS da opção B (mesmos arquivos de teste)

### W5 — via expressa (ferramentas livres, oráculo 0)
Check: python3 -m pytest .claude/scripts/tests -q -k "repin or drift or superseded"
- [ ] `re-pin-codex.py <versão>`: mede integridade + sha256 do payload e emite o pack assinável
- [ ] check de deriva no boot: npm `latest` do Codex e modelo novo da Anthropic × pin/allowlist (sem rede no hook; cache do fetch)
- [ ] derivação dos baselines `superseded` a partir das tags GA (acaba com o literal à mão)
- [ ] (depois) `adopt-model.py <id>`: gera o conjunto de edições do ADR-149 para os espelhos

### W6 — relmeta-142 + rc.1 + GA
Check: bash .claude/scripts/local/release.sh preflight
- [ ] relmeta-142 (inclui `--yes` no probe GPG do preflight e headline verdadeira)
- [ ] rc.1 → adopters no mesmo dia → ≥ 24 h → GA → npm
- [ ] dívida herdada RE-DECLARADA no material assinado (anexo P1 da v1.4.0, Known-open da 1.4.1)

## Open questions

- OQ-1 (Owner): esforço padrão dos ADOPTERS (o Opus 5.5 vem em medium; o Opus 5 vinha em high).
  **RESOLVIDA 2026-09-22 (S357), verbatim:** «xhigh». ⇒ `templates/settings/settings.base.json` (e o
  derivado `settings.user.json`) ganham `effortLevel: "xhigh"` no topo (em escopo de projeto vale para
  todos os modelos) nas instalações NOVAS; adopters existentes por opt-in (OQ-7); o ultracode fica só no
  override local do Owner (OQ-6).
- OQ-2 (Owner): wave-opus55 acima de 8 paths. **RESOLVIDA 2026-09-22, verbatim:** «Exceção declarada
  (Recomendado)» — um pack atômico derivado por script (precedente fable51), exceção registrada aqui.
- OQ-3 (Owner): nome da versão. **RESOLVIDA 2026-09-22, verbatim:** «1.4.2» — o material assinado
  RE-DECLARA que a cura do anexo da v1.4.0 prometida «na 1.4.2» não está nela (Known-open + condição).
- OQ-6 (debate W3, 2 críticos: segurança + FinOps): ultracode no `settings.json` commitado liga xhigh +
  orquestração em todo clone/worktree/night-run e satisfaz em silêncio o opt-in do `/council`.
  **RESOLVIDA 2026-09-23, verbatim:** «Só no override local (Recomendado)» — o dogfood commitado ganha o
  pin `claude-opus-5-5` sem `ultracode`.
- OQ-7 (debate W3, 2 críticos: QA + FinOps): gravar xhigh nos adopters EXISTENTES mascara a escolha de
  esforço do escopo de usuário e sobe o gasto de todos os modelos. **RESOLVIDA 2026-09-23, verbatim:**
  «Instalação nova + opt-in (Recomendado)» — instalações novas saem com `effortLevel: "xhigh"`; o
  `upgrade.sh` não grava `xhigh` em quem já instalou: imprime aviso nomeado com o custo e a flag de opt-in
  (a migração do pin grava `high` quando não há esforço — OQ-8).
- OQ-8 (rail W3 r3, P1): a migração do pin `claude-opus-5` → `claude-opus-5-5` baixaria em silêncio o
  esforço efetivo dos adopters existentes de high (padrão do Opus 5) para medium (padrão do Opus 5.5).
  **RESOLVIDA 2026-09-24, verbatim:** «Migrar gravando 'high' (Recomendado)» — quando o `upgrade.sh` migra o
  pin e o adopter não tem `effortLevel`, grava `"high"` (preserva a profundidade de antes, sem subir o
  gasto); o `xhigh` segue só em instalação nova ou por opt-in (OQ-7). Um `effortLevel` do adopter nunca é
  sobrescrito.
- OQ-9 (rail W3 r3, P1): `effortLevel: "xhigh"` num settings faz Claude Code 2.1.76–2.1.110 descartar o
  arquivo INTEIRO (hooks de governança desligados em silêncio). **RESOLVIDA 2026-09-24, verbatim:** «Exigir
  CC ≥ 2.1.280 (Recomendado)» — a 1.4.2 declara Claude Code 2.1.280 como mínimo (o Opus 5.5 já exige);
  `install.sh` e `upgrade.sh` checam `claude --version` e avisam/recusam abaixo disso.
- OQ-10 (rail W3 esgotou as 3 rodadas; r1–r3 REJECT, cada uma com UM P2 de classe diferente, nenhum
  P0/P1): **RESOLVIDA 2026-09-24, verbatim:** «Corrigir + rodada 4 final c/ anexo (Recomendado)» — cura
  do P2 da r3 pela classe (uma rotina única monta o «rode de novo» preservando as flags do operador em
  todas as saídas de falha da migração) e UMA rodada 4, a última: limpa ⇒ APPROVE; só P2 ⇒
  `APPROVE-WITH-ANNEX` com anexo rastreado e assinado; P0/P1 ⇒ REJECT e volta ao Owner. Mesma regra
  «rodada final com anexo» dos cortes de release.
- Regra de parada do rail da W3 (pré-registrada 2026-09-23, antes da 1.ª rodada): no máximo 3 rodadas;
  achado P1 só em material vira anexo; teto de 2 rodadas por classe de achado; NO-GO só por P0 ou
  condição declarada falsa.
- OQ-4 (Owner): re-pin do Codex e wave-opus55 no MESMO sentinel ou em duas cerimônias. Aberta; padrão do
  CEO: duas cerimônias (precedente 0155; o pack do re-pin tem cerimônia própria — o `npm i -g` do 0.156.1
  já foi feito pelo Owner em 2026-09-23, antes da remontagem).
- OQ-5 (Owner): a opção B do `relaunch --out` embarca na 1.4.2? **RESOLVIDA 2026-09-22, verbatim:** «Sim,
  embarca (Recomendado)».

## How to continue

Ler este plano, o LEDGER do PLAN-192 e a memória `project-owner-decisions-s357-opus55-fasttrack`.
Conferir: `git log --oneline -5`, `gh run list --limit 5`, `npm view @openai/codex dist-tags`,
`codex --version`. Se o GA da 1.4.1 não foi cortado: seguir o W1. Se foi: W2 → W3 na ordem.

## Success criteria

- [ ] GA v1.4.1 publicado (tag assinada, npm `latest=1.4.1`) — Check: npm view ceo-orchestration version
- [ ] `v1.4.2-rc.1` com Opus 5.5 no working set, no piso de veto e como pin; adopter v1.4.x recebe o 8.º id E o pin novo pelo upgrade (e2e) — Check: bash scripts/tests/smoke-install.sh
- [ ] rail no Codex 0.156.1 `verified` — Check: python3 .claude/hooks/check_pair_rail.py --verify-codex-pin "$(command -v codex)"
- [ ] a próxima adoção de modelo/Codex sai de ferramenta (W5) — Check: python3 -m pytest .claude/scripts/tests -q -k "repin or superseded"

## Session history

- S357 (2026-09-22): Opus 5.5 lançado; levantamento de 9 frentes + verificadores; decisões do Owner acima;
  Codex 0.156.0 estável publicado durante a sessão (pego pelo verificador). Plano aberto em `draft`.
- S357 (2026-09-23): Codex 0.156.1 (hotfix) publicado e instalado globalmente pelo Owner; o pack do
  re-pin (W2) foi remontado para o 0.156.1 — nenhum reinstall antes do SIGN.
- S358 (2026-09-29/30): kit do GA derivado (`fadb5f972387`), 3 rodadas de revisão (a 3.ª limpa, 12 P2
  abertos), re-pass GO-WITH-CONDITIONS nas 4 partes; GA v1.4.2 cortado pelo Owner (veredito
  `b55084da6dd8`, tag `v1.4.2` publicada 2026-09-30T14:26:34Z, npm `latest=1.4.2`); closeout `80eb46d8f372`.
- S359 (2026-09-30): plano levado a `done` (draft → reviewed → executing → done, transições do
  PLAN-SCHEMA §4). Conferido: `git tag -v` Good signature em `v1.4.1`, `v1.4.2-rc.1` e `v1.4.2`;
  Releases publicados; npm `latest=1.4.2`; re-pin 0.155.0 → 0.156.1 em `778acf27d1db`; wave-opus55 em
  `b4033b2e3527`. As caixas de Success criteria ficaram sem marcar durante a execução; a evidência está
  nos commits de `related_commits`. Sobras herdadas pelo PLAN-194 (trem de manutenção até a 1.4.3):
  re-pin do Codex para a estável do dia (0.159.2 em 30/09), `adopt-model.py` inexistente, detector de
  drift fora do `/ceo-boot`, os 12 P2 da rodada 3 do kit + o P2 do re-pass (ledger malformado descarta
  drift do Codex), espera do registry no passo 18 curta demais.
