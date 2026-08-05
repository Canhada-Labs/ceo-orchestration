---
round: 3
archetype: DevOps & Platform Engineer
skill: devops-ci-cd
agent_persona: null
generated_at: 2026-08-05T00:00:00Z
---

## Verdict

ADJUST — a mecânica GHA final é sólida e implementável como escrita; todos
os meus must-fix de round 1 e round 2 fecham no texto v2.1, verificados
contra o código. Sobra UM achado novo, pequeno e mecânico:
`smoke-install.yml` mantém `timeout-minutes: 8` (já esticado de 5→8 só
para os DOIS oráculos de upgrade existentes) e o step novo de F4 (e2e de
duas fixtures × dois modos de cerimônia) entra no MESMO job sem nenhuma
revisão desse orçamento no texto.

## Summary (≤ 3 bullets)

- Verifiquei as 8 mecânicas citadas no pedido de round 3 contra o código
  atual (não contra a prosa do plano): `GH_TOKEN` no await-job é
  necessário e seguido — o repo já tem o MESMO padrão em
  `release.yml:459,782` (`permissions:` sozinho não autentica o `gh` CLI
  hosted); a semântica de candidato (GRANT/WAIT/BLOCK, não-candidatos
  IGNORADOS) fecha exatamente a inconsistência que eu tinha achado no
  round 2; `smoke-install.yml:53` REALMENTE tem `fetch-depth: 1` (a
  fixture `v1.2.0` de fato não resolveria sem o fix); `scripts/doctor.sh`
  REALMENTE não está em nenhuma das duas listas `paths:` do arquivo hoje.
- O único ponto sem cobertura textual explícita: o orçamento de tempo do
  JOB que recebe o novo step e2e de F4.
- O fluxo documentado (verdito → commit → push main → tag → push tag,
  com `preflight --stable` restaurado antes do `bump --stable`) é
  executável por um operador humano sem lacuna sequencial — validei que a
  ordem é FORÇADA pelo próprio gate de ancestralidade novo (tag exige
  HEAD ∈ origin/main, então push main tem que vir antes de tag).

## Risks

- **R-DEVOPS8 — MEDIUM (novo).** `smoke-install.yml`'s job `smoke` tem
  `timeout-minutes: 8`, e o próprio comentário do arquivo (`:43-44`)
  registra que esse valor já foi esticado de 5 para 8 SÓ para os dois
  oráculos de upgrade (`test-upgrade-dryrun-identity.sh` +
  `test-upgrade-exclusions.sh`), cada um descrito como rodando "full
  install + upgrade legs against fixture adopter repos". O step novo de
  F4 (§OQ-4/W1.3) é da MESMA classe de custo — duas fixtures (instalação
  corrente; instalação v1.2.0 pin → upgrade corrente) vezes dois modos de
  cerimônia (maintainer/user) — ou seja, até quatro ciclos adicionais de
  install/upgrade completos no MESMO job, e o texto não revisita o
  orçamento em NENHUM lugar (§OQ-4, §W1 item 3, AC-4). Sob carga real de
  runner (não localmente — a lição já registrada deste repo sobre
  perf-gate/full-suite-load-flake se aplica igual aqui), 8 minutos para
  potencialmente 6 ciclos install/upgrade completos é um candidato real a
  timeout intermitente — e como o job tem `cancel-in-progress: true`
  (linha 36), um timeout nesse step mata o job inteiro, incluindo os
  outros gates que já rodavam ali. Mitigação: bump explícito de
  `timeout-minutes` (proponho 8→15, mesma margem proporcional que o bump
  5→8 anterior deu aos dois oráculos) no MESMO patch canonical que já
  toca `smoke-install.yml` em W1.3 — não é um arquivo novo, é uma linha a
  mais no patch que já está staged para esse arquivo.
- **R-DEVOPS7-R3 — LOW (residual, não bloqueia).** O round 2 pediu um
  orçamento de polling interno menor que os 35min do job, com mensagem
  `::error::` acionável antes do teto do GitHub. O texto final não fez
  isso — em vez disso, deu uma ROTA DE RECUPERAÇÃO operacional (§Riscos:
  "re-rodar o await-release-gate depois que o release-gate ficar verde
  ... run pinado à árvore da tag, re-run seguro"). Aceito essa troca: a
  rota de recuperação resolve o problema real (o operador não fica preso
  sem saída), mesmo sem a mensagem de erro mais cedo — não reabriria isso
  como bloqueante, só registro que ficou parcialmente atendido.

## Must-fix (blocking)

1. **`smoke-install.yml` — revisar `timeout-minutes: 8` no mesmo patch
   canonical de W1.3.** Ver R-DEVOPS8. Se a decisão de design for
   "reutilizar fixtures entre os dois modos de cerimônia para não pagar
   quatro ciclos completos", isso precisa estar ESCRITO no plano (a forma
   como F4 evita o custo), não presumido — do jeito que o texto está hoje
   ("Fixture A ... Fixture B ... POR modo de cerimônia") lê como
   produto cartesiano completo, e o plano não diz qual dos dois
   (aumentar timeout OU compartilhar fixture) resolve o risco.

## Nice-to-have (advisory)

1. Nenhum item novo — os nice-to-have de round 1/2 (permissions
   job-level, mensagem de erro pré-timeout) já foram endereçados ou
   conscientemente trocados por uma rota equivalente (ver Risks acima).

## Unseen by the original plan

1. **Orçamento de `timeout-minutes` do job de `smoke-install.yml` que
   recebe o step novo de F4** — 17 rounds de codex pré-commit mexeram
   extensivamente na SEMÂNTICA de F4 (fixture de 2º upgrade, ceremony-gate
   do protocol pointer, fetch-depth da tag histórica, path de
   `doctor.sh`), mas nenhum desses rounds revisitou o CUSTO DE TEMPO
   agregado de rodar tudo isso no mesmo job de 8 minutos que já estava no
   limite antes de F4 existir. É o tipo de lacuna que só aparece quando
   se soma o texto inteiro (cada achado de codex foi correto e local; o
   agregado de "quantos ciclos install/upgrade completos cabem em 8min"
   nunca foi essa pergunta).

## What I would NOT change

- **A semântica de candidato do AC-2 (GRANT só com candidato exato;
  não-candidatos IGNORADOS; WAIT vs BLOCK por estado).** É exatamente o
  fechamento correto do meu R-DEVOPS2 original — verificado coerente
  contra a lista de fixtures NUNCA-GRANT (head_branch de rc, head_sha de
  outro commit, workflow errado, `event==workflow_dispatch`) e a
  distinção WAIT-dentro-do-prazo vs BLOCK-no-deadline. Não tocaria.
- **O sequenciamento verdito→commit→push-main→tag em W2**, forçado pelo
  próprio gate de ancestralidade que o plano adiciona em `tag()` — é
  autoconsistente: não dá pra assinar uma tag ancestral de `origin/main`
  sem ANTES ter pushado o commit do verdito para `main`. A ordem não é
  arbitrária, é a única que o novo gate permite.
- **O assert de delta-restrito espelhado server-side em `release.yml`,
  ao lado do step 15 existente.** Validei que `release.yml` já usa
  `fetch-depth: 0` no checkout do job `release-gate` (herda todos os
  branches/tags, incluindo `origin/main` como ref resolvível) — o novo
  assert de `merge-base --is-ancestor` não precisa de um fetch adicional,
  reaproveita o checkout que já existe. E o assert é determinístico
  (parent_sha e GITHUB_SHA são fixos por tag) — re-rodar o step em caso
  de flake em OUTRO step não muda o resultado, sem risco de flake próprio.
- **`GH_TOKEN: ${{ github.token }}` explícito no `await-release-gate`.**
  Mesmo padrão já usado duas vezes no repo (`release.yml:459` e `:782`)
  para os mesmos fins (`gh run list`/`gh release`) — não é invenção nova,
  é consistência com o que já funciona.
