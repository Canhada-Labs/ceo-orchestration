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
> 2026-08-10) via workflow de 5 agentes + análise de fit. **Gatilho por
> MILESTONE (correção do debate Codex r1): W0 pode iniciar após GA
> v1.3.0 + land de W3/W4 do PLAN-169 — este plano NÃO espera o trem
> v1.4.0 inteiro.** Refinamento + debate L3 antes de `reviewed`.

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
o prompt egresso contra o manifesto: a **allowlist-por-proveniência
entra como CAMADA ADICIONAL sobre a blocklist-por-classe do ADR-114 —
a blocklist nunca é removida** (Codex r1: layer, não replace). Honestidade
de fronteira: leituras de lanes fora do harness (`codex exec`) são
INVISÍVEIS — documentar como limite, não vender cobertura total.

### W3 — FILE ASSIGNMENT enforcado em write-time
Hook PreToolUse(Edit/Write) que bloqueia escrita de agente nomeado fora
do `## FILE ASSIGNMENT` declarado no spawn. Converte declaração
advisory em invariante mecânica. **Classificação corrigida (Codex r1,
P1): FILE ASSIGNMENT malformado é INPUT de segurança não-parseável =
fail-CLOSED (block)** — doutrina §4 fail-closed-on-input; infra real
(hook ausente, timeout) segue fail-open com breadcrumb. É
defense-in-depth ("Bash escapa"), não fronteira — escrever a claim no
tamanho do enforcement.

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

## 5. Revisão v2 — auditoria total S302 (workflow framework-total-audit, 14 agentes, 12 lanes ok)

**Re-escopo: este plano fica MENOR e ganha um W0 bloqueante.**

- **W0 (NOVO, bloqueante, pré-tudo): censo de gates com positive
  control.** Nenhum gate entra em settings.json/CI sem controle
  positivo que FALHA quando o enforcement é removido + registro de
  qual workflow o executa; aplicado retroativamente aos 57 hooks.
  Quitar aqui as 3 dívidas de enforcement abertas desde S294
  (pair-rail-gate.sh inexecutável, injector persona fuzzy,
  overhead-ack não cobre Write). Racional: F4 do PLAN-166 é a 5ª
  instância nomeada da classe "gate vermelho invisível" — não se
  importa governança nova sobre camada de enforcement com dívida.
- **W1 (mantido, ampliado):** batch-approval + formato de verdito com
  pin único `delta_manifest` (em vez de allowlist enumerada — fecha o
  loop evidência-de-evidência da S301).
- **NOVO W1b:** ADR curto formalizando a economia de revisores:
  **Codex = único revisor bloqueante do rail; Grok = gatilho**
  (desacordo Claude↔Codex, L4/SPEC/release, auditorias periódicas).
  A auditoria constatou que `grok.py` é host-adapter de papel único —
  o claim "dois revisores externos" não corresponde ao enforcement.
- **NOVO W1c:** fronteira de ownership dos domain-packs (116 domain
  skills → squad-packs opt-in via squad-install; 1-2 domínios de
  referência em-tree) — pré-trabalho do PLAN-175.
- **NOVO W1d:** fixes de doc-drift baratos: spawn.md (manda injetar
  SKILL.md inteiro; default é reference-mode desde ADR-090 — ~9-16k
  tok/spawn desperdiçados se seguido literalmente) + propagação do
  cap G12 (skill de parallelization manda 6; ratificado é 8
  read-only).
- **ADIADO:** W2 (proveniência de leituras/observation log) e W3
  (FILE ASSIGNMENT write-time) só DEPOIS do W0 fechar — mesma lógica:
  primeiro provar vivo o que existe, depois adicionar.
- W4 (living docs) e W5 (higiene worktree) mantidos; W5 continua
  pré-requisito do E5 (PLAN-172).

## 6. Debate Codex r1 (S302) — curas incorporadas + ACs

Verdito r1: NO-GO com 4 P1 — todos aceitos e curados nesta v2.1:
1. **Milestone, não trem inteiro** (§seed corrigido).
2. **W0 não re-clama os débitos do AC-9 do PLAN-169**: os 3 débitos
   de enforcement PERTENCEM ao 169 (AC-9, parcialmente executado). O
   W0 os AUDITA e herda apenas o que o fechamento do 169 declarar
   não-feito — coordenação por registro de entrega, sem dupla posse.
3. **W1c é contract-only**: define a fronteira de ownership dos
   domain-packs; a MIGRAÇÃO é do PLAN-175 (passo 3).
4. **W3 fail-CLOSED em input malformado** (corrigido acima).

ACs mínimos (anti-churn de rail):
- W0: censo em lotes de ~10 hooks/sessão; AC = 100% dos hooks com
  {positive control OU registro "sem-controle-por-design" justificado};
  kill = lote sem fechar em 2 sessões ⇒ re-escopo antes de continuar.
- W2 (quando destravar): piloto em sidecar com kill numérico —
  overhead p95 do PostToolUse acima do teto do perf-gate vigente ⇒
  redesenho; medição imprime inputs.
- Budget firmado no refinamento pré-`reviewed`; nada de TBD ao entrar
  em execução.
