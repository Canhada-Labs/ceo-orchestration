---
plan: PLAN-169
round: 2
archetype: DevOps Engineer
---

## Verdict

ACCEPT — a v2.2 resolveu meus 3 must-fix do round 1, D1 de forma até
mais forte do que eu tinha pedido; nada novo do meu domínio bloqueia.

## Summary

- D1/D2/D3 do round 1 confirmados resolvidos no texto atual, com D1
  reforçado por uma regra de ORDEM DE EXECUÇÃO inteira (não só a âncora
  do re-pass) que fecha o risco de forma mais ampla do que eu pedi.
- O item novo do rail que toca meu domínio (W4-C item 6, piso de CLI
  para `PostToolBatch`/`TaskCompleted`) reaproveita corretamente um
  padrão já existente e testado do repo — verifiquei no código.
- Fica um risco residual, não-bloqueante, que vale nomear com precisão:
  "durante o hold de 24h, NENHUM commit em main" é disciplina + gate
  REATIVO na hora da tag, não um bloqueio preventivo — e a rota
  recomendada de OQ-5 (b) significa aceitar, conscientemente, que
  v1.3.0 publica com o bug B.a ainda vivo até a v1.4.0.

## Risks

Reafirmando os 3 do round 1, com status atualizado:

- **[FECHADO, além do pedido] Delta-gate rejeitando rc.2 por
  sequenciamento errado.** No round 1 pedi só a âncora certa do
  re-pass r2. A v2.2 vai além: agora existe uma ORDEM DE EXECUÇÃO
  explícita — `W0 → W1 → W2 → W6.1 (trem v1.3.0 COMPLETO, main
  congelado do corte da rc.2 até o GA) → W3 → W3-K → W4 → W4-C → W5 →
  W6.2` (`PLAN-169-....md:127-133`) — que impede por construção que
  W3/W3-K/W4-C (conteúdo v1.4.0) sequer existam como commits antes do
  GA da v1.3.0. Risco original fechado.
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
  só nomear com a precisão que a v2.2 já pratica em outros pontos.
- **[Processo FECHADO, risco de PRODUTO permanece] B.a vs GA.** No
  round 1 pedi decisão nomeada em vez de silêncio; a v2.2 entregou
  OQ-5 com rota recomendada (b) explícita e registrada. O processo de
  decisão está correto. Mas o risco de produto por trás da decisão não
  desaparece por estar bem documentado: se o Owner confirmar (b),
  v1.3.0 GA publica com um bug de abort de upgrade REPRODUZIDO ainda
  vivo em `upgrade.sh`, por uma janela de dias (calendário mínimo
  4-6 dias, dois trens com hold de 24h cada) até a v1.4.0 trazer o
  fix via W3. Trade-off aceitável e nomeado — só reafirmando que o
  risco em si, não o processo de decidi-lo, é o que continua vivo.
- **[FECHADO] Espera de até 24h para validar o W1 pelo cron.** D3
  aplicado (`gh workflow run` logo após o commit), com nota da
  colisão de `concurrency: cancel-in-progress`. Nada residual aqui.

## Must-fix restantes

(vazio — nenhum item do meu domínio bloqueia a v2.2)

## Nice-to-have

- W4-C item 6 (piso de CLI para as novas registrações
  `PostToolBatch`/`TaskCompleted`) reaproveita corretamente o padrão
  `_T34_VERSION_FLOOR_PROBE_PASSED` de `scripts/upgrade.sh:189-200`
  (feature-gate OFF por default até o probe de versão-floor ser
  registrado, com escape hatch `CEO_T34_NEW_EVENT_REGISTRATIONS`) —
  confirmei isso lendo o código. Vale citar esse nome de variável/
  padrão explicitamente no texto do plano, já que é reuso e não desenho
  novo — facilita achar o precedente na hora de implementar.
- Os dois nice-to-have que eu já tinha levantado no round 1 (higiene do
  `NPM_TOKEN` de rollback do PLAN-158; grep do comentário de estimativa
  duplicado em `smoke-install.yml`) continuam fora do texto — seguem
  opcionais, sem custo de bloquear esta v2.2.

## Unseen

Nada novo do meu domínio além do que os rounds anteriores já cobriram;
não encontrei superfície de release/CI/versão adicional na v2.2 que não
tivesse sido tocada pelas curas do rail ou pelos meus próprios rounds.

## What I would NOT change

- A ordem de execução nova (`W0→W1→W2→W6.1 completo→W3→W3-K→W4→W4-C→
  W5→W6.2`) — estritamente mais forte que a v2 para o meu domínio; não
  mexeria em nada aqui.
- W4-C item 6 (piso de CLI) — reuso correto e verificado de um padrão
  já existente e testado; não desenharia diferente.
- Tudo que já endossei nos rounds 1 e 2 sobre o fix do W1, o gate do
  nightly e a infraestrutura de npm trusted publishing continua válido
  e não mudou na v2.2.
