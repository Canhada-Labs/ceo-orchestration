---
round: 1
archetype: DevOps & Platform Engineer
skill: devops-ci-cd
agent_persona: DevOps & Platform Engineer
generated_at: 2026-08-13T00:00:00Z
---

## Verdict

ADJUST

## Summary

- W1 é bem desenhado no princípio (probe live-fire antes de qualquer
  wiring, fail-closed se o gap aparecer, duas fontes lado a lado antes
  de qualquer switch) — a disciplina de evidência-antes-de-doc está
  correta e eu não mexeria nela.
- OQ-3 erra o candidato: o "re-pass de release" que o proposal chama de
  "script + agentes ad-hoc" NÃO é um fan-out de Task tool — é um script
  bash que invoca `codex exec` em subprocesso, num worktree detached com
  pin de tag GPG + verificação remota (evidência abaixo). Migrar isso
  para Workflow troca o pipeline de supply-chain mais crítico do repo
  por um mecanismo novo, e o positive control de `check_agent_spawn` no
  "caminho Workflow" nem se aplica a ele — não há spawn de Task tool
  nesse pipeline hoje para o hook interceptar.
- W1.2 (cost-attribution) tem um precedente vivo e correto que o plano
  não cita — `/agent-budget` Step 3b já implementa exatamente o padrão
  "duas fontes lado a lado, nunca substituição silenciosa" contra a
  Admin API. O plano deveria estender esse padrão, não inventar um
  paralelo, e precisa de parâmetros concretos (o que imprimir, duração
  mínima, critério de switch por CATEGORIA, não só agregado).

## Risks

1. **R-DEVOPS-1 — HIGH.** Pilotar W1.1 no re-pass de release aposta o
   pipeline de maior blast radius do repo (o único que verifica GPG de
   tag + `ls-remote` remoto + `merge-base --is-ancestor` antes de rodar
   `codex exec --sandbox read-only` num worktree detached e faz
   quarentena de payload no cleanup — `run-rc4-repass.sh:20-53,174,222`)
   num mecanismo de fan-out (Workflow `agent()`/`parallel()`) que nunca
   rodou esse tipo de subprocesso externo pinado. Se o piloto quebrar,
   quebra o gate que autoriza tag — não um audit read-only advisory.
   Mitigação: escolher piloto de blast radius baixo (ver Must-fix 1).
2. **R-DEVOPS-2 — MEDIUM.** Custo de manter DOIS caminhos não é só
   "rodar os dois" — `workflows/README.md:35-46` documenta que
   `opts.model` é INERTE no Workflow: todo agente de Workflow roda no
   preço do modelo da sessão, nunca num modelo mais barato via
   subprocesso. Um fan-out que hoje usa `claude -p --model <barato>`
   (como o próprio `eval-baseline-n20` faz para o alvo, não para o
   orquestrador) fica estruturalmente MAIS CARO se migrado ingenuamente
   para Workflow puro. Isso muda a economics do piloto e não está no
   plano.
3. **R-DEVOPS-3 — MEDIUM.** `env-inventory-check.py --check` roda em
   CI (`validate.yml:140-144`) mas só emite `::warning` — não bloqueia.
   O guard-rail do plano ("Toda env nova... no mesmo commit — R-SEC12")
   não tem dente nenhum hoje. W1 introduz candidatos reais de env nova
   (flags de C5 para armar/desarmar detectores, possível toggle de
   cost-attribution nativa, possível flag de scoped-permissions em
   W1.3) — nada impede merge sem atualizar o inventário.
4. **R-DEVOPS-4 — LOW.** C3 (lint de vacuidade) como gate de CI precisa
   de um critério estático que não é trivial de acertar de primeira: o
   próprio `check_tier_a_spec_version_drift` tem docstring
   `"(informational)"` (ceo-boot.py:1017) — ou seja, o autor original
   pode ter querido um check decorativo por design, e não um bug. Um
   lint que trata "sempre-verde" como violação sem mecanismo de
   allowlist gera falso-positivo exatamente na classe de check que é
   legitimamente sempre-verde.

## Must-fix (blocking)

1. **Trocar o piloto W1.1.** O re-pass de release não é candidato —
   não há Task-tool spawn nesse pipeline hoje (confirmado: `grep -n
   "codex exec\|claude -p\|Task\|agent(" run-rc4-repass.sh` só acha
   `codex exec` em subprocesso bash, nunca uma chamada de Agent/Task).
   `audit-fanout.js` e `nightly-hygiene.js` já SÃO Workflow (o próprio
   proposal admite isso na OQ-3). Candidato correto: um fan-out
   Claude-nativo que HOJE é Task tool ad hoc, de blast radius baixo
   (advisory), com frequência suficiente para gerar sinal — o próprio
   `/debate` (DEBATE-SCHEMA §7/§8: CEO spawna 3-6 agentes via Task tool
   a cada rodada, "Debate spawns are no exception to the hook") ou o
   fan-out de auditores do W0 deste mesmo plano (4 auditores ad hoc,
   mesma forma de `audit-fanout.js`). Qualquer um dos dois já tem a
   expectativa de `check_agent_spawn` documentada em texto
   (DEBATE-SCHEMA §8), o que torna o positive control uma CONFIRMAÇÃO
   barata, não uma exploração cara.
2. **W1.2 — citar e estender o precedente, não duplicar.**
   `agent-budget.md` Step 3b (O3) já roda audit-log vs Admin API
   `estimated_cost` lado a lado e documenta a doutrina certa:
   "Treat the two numbers as cross-check, not authority-swap... Never
   silently replace one with the other". W1.2 deve apontar para esse
   padrão como precedente ao invés de reinventar. Parâmetros concretos
   que faltam no plano:
   - **O que imprimir:** total agregado das duas fontes NÃO basta —
     erros compensatórios (ex.: +5% num spawn, −5% noutro) escondem
     divergência real no agregado. Exigir breakdown por spawn/tipo de
     evento, não só soma.
   - **Duração da janela:** "1 janela" é subespecificado. Amarrar a
     um piso de CONTAGEM de eventos (ex.: N≥50 spawns cobrindo pelo
     menos Task-tool E Workflow-tool, o que vier depois no tempo), não
     a dias corridos — sessão de baixo volume pode fechar a janela sem
     nunca ter exercitado o caminho Workflow (que, por R-DEVOPS-2,
     tem economics DIFERENTE do caminho Task).
   - **Critério de switch:** <10% no agregado é fraco pela razão acima
     — gatear também por divergência MÁXIMA por categoria, e fazer o
     próprio switch ser um diff revisado (flip de env var/default), não
     um cutover silencioso quando o teste passar.
3. **Dar dente ao guard-rail de env-inventory ou rebaixar a linguagem.**
   Duas opções, qualquer uma resolve: (a) escalar
   `env-inventory-check.py --check` de `::warning` para bloqueante
   quando o diff introduz token `CLAUDE_*|ANTHROPIC_*|CEO_*` novo SEM
   diff correspondente em `env-inventory.json` no mesmo commit (escopo
   no diff evita quebrar PRs não relacionados); (b) se não há apetite
   para isso agora, trocar "Toda env nova... no mesmo commit" por
   "deveria" no guard-rail do PLAN-178, porque hoje é honra, não gate.
4. **C3 — anexar mecanismo de allowlist ao lint de vacuidade.** Seguir
   o padrão já existente no repo para exceção auto-declarada (o
   marcador `# CEO-DEBT:` da dimensão viii de `nightly-hygiene`):
   qualquer `check_*` que queira ser legitimamente sempre-verde precisa
   de um comentário `# CEO-INFORMATIONAL-ONLY: sem caminho red por
   design` acima da def, ou o lint marca vermelho. Sem isso, o lint
   ou falso-positiva em checks decorativos por design, ou vira
   subjetivo demais para rodar sem revisão humana por achado — o que
   mata o caso de uso "CI gate".

## Nice-to-have

1. Anexar ao probe de W1.1 a mesma disciplina de "1 controle positivo +
   1 negativo" que o W0 já usou com sucesso (AC-1 da tabela MAST) —
   provar que o hook dispara E provar um caso onde não deveria disparar
   mas o Workflow tenta passar por baixo (ex.: spawn sem `## SKILL
   CONTENT`). Confirmar disparo sozinho não discrimina se o disparo é
   MEANINGFUL no caminho novo.
2. C3 pode nascer como passo advisory em `validate.yml` (mesmo padrão
   dos ~40 steps já lá, ex. "SBOM sidecar-dependency sync gate",
   "Flip-criteria drift check") antes de virar bloqueante — reduz o
   risco de travar CI com falso-positivo enquanto o allowlist do Must-
   fix 4 ainda está sendo populado.
3. Publicar o output do W1.2 (as duas fontes lado a lado) como mais uma
   seção do `/agent-budget`, em vez de um relatório novo — o comando já
   tem a seção "Analytics cross-check"; cost-attribution nativa é um
   terceiro cross-check natural no mesmo lugar que o operador já olha.

## Unseen by the original plan

1. `workflows/README.md:30-33` (§4.2, "S185 lesson") já documenta que
   "Workflow subagents share the parent session's live hook rail" —
   isso é evidência PARCIAL pré-existente a favor de AC-2 (hooks
   provavelmente disparam no caminho Workflow), mas é sobre
   `audit_emit` poluir a cadeia canônica, não necessariamente sobre a
   decisão de bloqueio do `check_agent_spawn` disparar idêntica dentro
   de `agent()`/`parallel()`. O plano deveria citar essa linha
   explicitamente no desenho do probe (constrói em cima da evidência
   existente) em vez de tratar AC-2 como pergunta totalmente aberta.
2. Nenhum dos 4 workflows existentes (`audit-fanout`, `council-audit`,
   `eval-baseline-n20`, `nightly-hygiene`) tem hoje um mecanismo de
   `--resume` ou budget circuit-breaker documentado no README além do
   cap por-batch do `eval-baseline-n20` ($7/batch). Se W1.1 migra um
   fan-out recorrente para Workflow, "pipeline determinístico com
   resume/budget" (a promessa do W1 item 1) precisa desse mecanismo
   ANTES do piloto — hoje só um dos quatro workflows tem budget-stop
   explícito.

## What I would NOT change

- O gate de governança "positive control ANTES da migração, fail-closed
  se gap" em W1.1 — a sequência está certa, só o alvo do piloto está
  errado (Must-fix 1).
- A doutrina "duas fontes impressas, nunca substituição silenciosa" em
  W1.2 — é exatamente a doutrina certa (e já tem precedente vivo); não
  enfraquecer isso para um switch automático.
- Probe-primeiro em W1.3 antes de qualquer desenho de scoped
  permissions — certo não gastar ciclo de design em cima de uma
  feature nativa sem saber o que ela realmente bloqueia vs os hooks
  atuais.
- Teams full-mesh fora do escopo (W1.4) — concordo pela lente DevOps
  também: coordenação full-mesh multiplicaria a superfície de
  telemetria de custo e hook-rail que ainda nem está madura para 1
  agente por vez (R-DEVOPS-2, R-DEVOPS-3).
