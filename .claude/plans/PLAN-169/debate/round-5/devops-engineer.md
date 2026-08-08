---
plan: PLAN-169
round: 5
archetype: DevOps Engineer
skill: devops-ci-cd
agent_persona: none (nominal persona unfilled since spawn — operate as core archetype)
generated_at: 2026-08-08
---

## Verdict

ACCEPT — a v2.5 aprofunda exatamente a precisão que eu vinha pedindo
(kernel-path para `validate.yml`, piso de CLI cobrindo `install.sh`,
rótulo do CHANGELOG condicionado a evidência real). Achei só um ponto
onde a doutrina no-throughput-claim foi aplicada além do que ela cobre
— nice-to-have, não bloqueante.

## Summary

- Confirmei no texto os 4 deltas do meu domínio citados para este
  round, todos corretos: ordem de execução inalterada; W1.7/shellcheck
  agora reclassificado como KERNEL PATH (`validate.yml` está em
  `_KERNEL_PATHS`, `check_arbitration_kernel.py:135`) em vez de
  meramente canônico; piso de CLI agora cobre TAMBÉM
  `scripts/install.sh` (fresh install), fechando um buraco real que só
  o `upgrade.sh` cobria antes; rótulo do quota-resume no CHANGELOG do
  W6.2 agora é condicional ao resultado real do live-fire
  (GO=supported, senão experimental), não hardcoded.
- Um item novo, não bloqueante: a supressão do número de duração observado
  no comentário de `ownership-nightly.yml:34-37`, citando
  "AGENTS.md no-throughput-claim" (codex r20-P2), extrapola essa
  doutrina. Li o texto exato em `AGENTS.md:9-11`: "Reject any doc
  change that adds throughput or speedup claims" — a regra existe para
  banir claims de VELOCIDADE DE MULTI-AGENTE (a tese do plano, o
  "no speed claim" de 6 experimentos), não para censurar telemetria
  operacional de UM job de CI usada pra calibrar timeout. Não achei
  nenhum precedente no repo (ADRs, workflows) de aplicar essa doutrina
  a comentários de CI — é extensão nova, não reafirmação de prática
  existente.
- Meus 2 riscos duráveis do round 4 persistem inalterados na v2.5.

## Risks

Reafirmando verbatim os 2 do round 4 (nenhum foi tocado pela v2.5) +
1 novo, minoritário:

- **[RESIDUAL, não-bloqueante] A garantia "NENHUM commit em main"
  durante o hold é disciplinar, não um bloqueio técnico preventivo.**
  O único backstop que verifiquei no código é o guard REATIVO de
  `_release_tag_guard.py` (ancestry + delta) rodado na hora de cortar
  a tag — ele PEGA a violação depois do fato (força rc.3, reinicia o
  hold), não a IMPEDE de acontecer em primeiro lugar (não há branch
  protection nem CI preventivo citado no texto). Dado o bus factor de
  mantenedor único que este repo já declara (CLAUDE.md §5), a chance
  de um commit acidental durante a janela é baixa na prática — mas o
  texto do plano lê como garantia absoluta quando na verdade é
  disciplina + rede de segurança reativa já existente. Não bloqueia;
  só nomear com a precisão que a v2.2/v2.3 já pratica em outros pontos.
- **[Processo FECHADO, risco de PRODUTO permanece] B.a vs GA.** No
  round 1 pedi decisão nomeada em vez de silêncio; a v2.2/v2.3 entregou
  OQ-5 com rota recomendada (b) explícita e registrada, inalterada
  nesta versão. O processo de decisão está correto. Mas o risco de
  produto por trás da decisão não desaparece por estar bem documentado:
  se o Owner confirmar (b), v1.3.0 GA publica com um bug de abort de
  upgrade REPRODUZIDO ainda vivo em `upgrade.sh`, por uma janela de
  dias (calendário mínimo 4-6 dias, dois trens com hold de 24h cada)
  até a v1.4.0 trazer o fix via W3. Trade-off aceitável e nomeado — só
  reafirmando que o risco em si, não o processo de decidi-lo, é o que
  continua vivo.
- **[NOVO, minoritário, não-bloqueante] O no-throughput-claim aplicado
  a um comentário de CI opera contra o próprio objetivo do plano.** O
  W1 item 6 pede "re-apertar [`timeout-minutes: 90`] só com p95 real de
  várias nightlies verdes" — mas se a prática virar "nunca escrever o
  número observado", não sobra baseline nenhuma pra comparar contra.
  Isso não muda o comportamento do gate (`timeout-minutes: 90` segue
  igual), só a qualidade da documentação operacional para quem for
  reapertar essa janela depois.

## Must-fix restantes

(vazio — o achado do no-throughput-claim é nice-to-have, não
bloqueante; nada mais do meu domínio impede a v2.5)

## Nice-to-have

- Sobre o comentário de `ownership-nightly.yml:34-37`: registrar
  apenas o PONTEIRO para o run (`31246426017`) como fonte da telemetria
  de duração, SEM transcrever o tempo medido no repo — AGENTS.md
  proíbe adicionar qualquer número de throughput a doc versionada
  (o número vive no run do CI, consultável, não no arquivo). Isso
  preserva a base para um re-aperto futuro do `timeout-minutes: 90`
  sem violar a doutrina.

## Unseen

Nada além do que já foi coberto acima; não encontrei mais nenhuma
superfície de release/CI/versão nova na v2.5 que os rounds anteriores
não tivessem tocado.

## What I would NOT change

- A reclassificação de `validate.yml`/W1.7 como KERNEL PATH (em vez de
  meramente canônico) — mais precisa e correta; concordo com a exigência
  de sessão própria + `CEO_KERNEL_OVERRIDE` para essa cerimônia.
- O piso de CLI agora cobrindo `scripts/install.sh` além do
  `upgrade.sh` — fecha um buraco real (fresh install sem gate nenhum
  para eventos que o CLI velho não parseia); reuso correto do padrão
  `upgrade.sh:189-200`.
- O rótulo condicional do quota-resume no CHANGELOG do W6.2
  (GO=supported / no-GO=experimental) — exatamente a disciplina de
  "claim só depois de evidência" que o próprio plano defende em outros
  lugares.
- A ordem de execução dos trens — segue estritamente correta para o
  meu domínio, sem mudanças desde o round 3.
