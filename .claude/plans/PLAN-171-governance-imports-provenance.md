---
id: PLAN-171
title: Imports de governança (cloudflare-os/xirp) — batch-approval, proveniência de leituras, FILE ASSIGNMENT write-time, living docs local
status: draft
created: 2026-08-11
owner: CEO
depends_on: [PLAN-169]
budget_tokens: TBD no refinamento (estimativa grosseira 300-600k)
budget_sessions: 4-7
context_risk: medium
external_wait: nenhum
tags: [governance, audit, provenance, seed]
---

# PLAN-171 — Imports de governança: proveniência e cerimônia de lote

> **SEMENTE (S302, 2026-08-11).** Registrada pelo CEO a pedido do Owner
> após estudo de dois sistemas externos (cloudflare-os da Cloudflare,
> Apache 2.0, aberto 2026-08-05; xirp do Spotify, proprietário, beta
> 2026-08-10) via workflow de 5 agentes + análise de fit. Nada deste
> plano executa antes do trem em voo (rc.3 → GA v1.3.0 → W3/W4 →
> v1.4.0). Refinamento + debate L3 obrigatórios antes de `reviewed`.

## 0. Papel no roadmap

Este plano é o **habilitador de governança do PLAN-172 (E5/WIP=2)**,
não uma trilha independente (verdito da síntese speed-research-r2,
S302): FILE ASSIGNMENT em write-time e proveniência de leituras são o
que torna duas unidades em voo AUDITÁVEIS (colisão de sentinel-scope é
o risco de governança nomeado do E5); batch-approval é o pré-requisito
do mecanismo "batching L1-L2" do 172. Priorizar os itens pelo caminho
crítico do 172.

## 1. Contexto (o que os externos validaram)

- **cloudflare-os** opera com Gatekeepers (brokers de credencial por
  serviço), capabilities zero-by-default e um **observation log**: toda
  leitura do agente é registrada e anexada aos artefatos produzidos;
  visualização é validada contra o log. A política de contribuição
  deles ("o gargalo é revisar, não escrever") ecoa a tese deste
  framework. Validação externa da direção; o runtime deles (Workers,
  Durable Objects) é categoricamente incompatível com este layer
  stdlib-only — importamos IDEIAS, zero código.
- **xirp** persiste contexto entre sessões/engenheiros e gera "living
  documentation" das sessões — mas faz upload de transcripts sem
  redação de segredos para cloud proprietária. Importamos a ideia,
  invertendo a postura: tudo LOCAL, egress zero por default.

## 2. Escopo (itens, em ordem de prioridade)

### W1 — Cerimônia de aprovação em lote (batch-approval) formalizada
A prática já existe (packs staged + dry-run em clone + `OWNER-*-CUT.sh`
com UMA assinatura GPG sobre manifesto sha256; commit-por-manifesto
validado na S301). Falta codificar: schema do approval-queue, corpo da
cerimônia em PROTOCOL/skill, e o invariante anti-lote-parcial — o gate
DEVE recusar conjunto ≠ manifesto (lição do fix-forward `8a178f5`:
gate que aceita run parcial é vácuo). Cada item do lote carrega
evidência de dry-run individual; lote não dilui o escrutínio V3.

### W2 — Manifesto de proveniência de LEITURAS (observation log local)
Estender o audit HMAC (PostToolUse em Read/Grep/Glob/WebFetch) para
registrar digests/paths do que cada agente LEU, em **sidecar
encadeado** (nunca inflar a cadeia principal — perf-gate p99 e o
histórico float-em-HMAC proíbem). Anexar o manifesto aos artefatos
decisórios (verditos de debate/council, packs). No `/council`, validar
o prompt egresso contra o manifesto: o redactor ADR-114 evolui de
blocklist-por-classe para **allowlist-por-proveniência**. Honestidade
de fronteira: leituras de lanes fora do harness (`codex exec`) são
INVISÍVEIS — documentar como limite, não vender cobertura total.

### W3 — FILE ASSIGNMENT enforcado em write-time
Hook PreToolUse(Edit/Write) que bloqueia escrita de agente nomeado fora
do `## FILE ASSIGNMENT` declarado no spawn. Converte declaração
advisory em invariante mecânica. Classificação §4 do CLAUDE.md:
parse-failure do assignment = infra = allow com breadcrumb; arquivo
fora do escopo = input = block. É defense-in-depth ("Bash escapa"),
não fronteira — escrever a claim no tamanho do enforcement.

### W4 — Living documentation LOCAL-ONLY
Gerador stdlib que materializa docs navegáveis ("o que aconteceu e por
quê") a partir do audit log + closeouts. Tudo local e advisory; log
renderizado como untrusted data; de-id por CLASSES (não por-nome)
antes de qualquer materialização; qualquer versão que saia do disco
passa pelo redactor ADR-114 ou não existe.

### W5 — Higiene de worktree para paralelismo (pré-requisito E5)
Audit log e memória são keyed por cwd-slug: N worktrees fragmentam a
cadeia. Definir convenção de log ÚNICO no repo principal (worktrees
anotam `worktree_id` no evento) ANTES de qualquer execução WIP=2 do
PLAN-172. Sem isso, E5 não roda.

## 3. Não-escopo (decidido no estudo, não re-litigar sem dado novo)

- Code Mode (ações dentro de código autorado pelo agente) — alarga a
  superfície não-auditada de propósito.
- Runtime residente de qualquer espécie (Workers/daemons/brokers).
- Upload de transcripts / workspace cloud.
- Metade viewer-side do observation log (sem ponto de mediação no
  consumo de artefatos git — enforce só no egress).

## 4. Riscos nomeados

- W2 é o item de maior valor E maior risco de perf — pilotar em
  sidecar com medição que imprime seus inputs (lição S285).
- W3 pode colidir com spawns legítimos multi-arquivo — janela de
  exceção via assignment glob, nunca via desligar o hook.
- Todos os itens tocam superfície de hooks → cerimônia canonical-edit
  + pair-rail por item; L3 com debate.
