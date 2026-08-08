---
plan: PLAN-169
round: 3
archetype: DevOps Engineer
---

## Verdict

ACCEPT — v2.3 preserva tudo que eu tinha fechado no round 2 e, de
bônus, endurece exatamente a classe de perigo (estado transitório de
repo colidindo com um cron exato) que venho nomeando desde o round 1.

## Summary

- Nada do meu domínio regrediu: os itens que eu já marcava FECHADO no
  round 2 (delta-gate/sequenciamento, validação via `workflow_dispatch`)
  continuam fechados na v2.3 — não houve mudança de texto que os
  reabrisse.
- Item novo relevante ao meu domínio: **W2.6** ganhou uma cláusula
  TRANSITÓRIA (`VP r2-MF-B`) que proíbe o controle positivo do marcador
  de atravessar a janela do MESMO cron (`43 6 * * *`) que eu já citava
  em D3, e proíbe o controle de existir no HEAD candidato da rc.2 — é
  exatamente a classe "estado transitório de repo vs. gate exato" que
  eu vinha nomeando, agora fechada num lugar que eu não tinha olhado.
- **W4-C** ganhou escopo em ARQUIVOS byte-exato (`touched−scope=∅`
  agora lista os 3 arquivos novos arrastados pelo checklist HMAC:
  `audit_emit.py`, `SPEC/v1/audit-log.schema.md`,
  `check_config_change.py`) — reduz o risco de um mismatch de escopo
  canônico na cerimônia, mas isso é mais domínio do VP/Security do que
  meu; só registro que não introduz nada que me preocupe.
- Meus dois riscos ainda vivos do round 2 (hold disciplinar/reativo;
  risco de produto do B.a) não foram tocados pela v2.3 — persistem com
  o mesmo texto.

## Risks

Reafirmando (verbatim) os que persistem do round 2; removi os que já
estavam genuinamente fechados desde então (delta-gate/sequenciamento e
a espera pelo cron), porque nada na v2.3 os reabriu:

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

## Must-fix restantes

(vazio — nenhum item do meu domínio bloqueia a v2.3)

## Nice-to-have

- **W2.6 transitório** — o texto diz "planta, observa o vermelho e
  DESPLANTA no MESMO commit". Vale uma frase explícita confirmando que
  isso é um controle HERMÉTICO de teste (fixture tipo `TestEnvContext`
  simulando o marcador dessincronizado em memória/tmp), não uma edição
  real do `.claude/.framework-version` em disco seguida de revert — a
  primeira leitura é inequivocamente segura quanto à janela do cron; a
  segunda dependeria de nunca fazer push do estado intermediário, o que
  é mais frágil de garantir. Provavelmente já é a intenção; só falta a
  palavra "hermético"/"em memória" no texto para fechar a ambiguidade.
- Os nice-to-have dos rounds 1-2 que seguem fora do texto (higiene do
  `NPM_TOKEN` de rollback do PLAN-158; comentário de estimativa
  duplicado em `smoke-install.yml`; citar o nome do padrão
  `_T34_VERSION_FLOOR_PROBE_PASSED` explicitamente no W4-C item 6)
  continuam opcionais, sem custo de bloquear.

## Unseen

Nada novo do meu domínio além do que os rounds anteriores e este já
cobriram. W2.9 (defeitos do próprio `debate-converge.py`) é meta-
instrumento do processo de debate, não superfície de release/CI/
versão — fora do meu escopo de crítica, só registro que é a razão
pela qual meus rounds 2/3 mudaram de formato.

## What I would NOT change

- A ordem de execução (`W0→W1→W2→W6.1 completo→W3→W3-K→W4→W4-C→W5→
  W6.2`) — segue estritamente correta para o meu domínio.
- A cláusula transitória nova do W2.6 — fecha exatamente a classe de
  risco que eu nomeava; não mexeria no design, só sugiro a palavra
  "hermético" (nice-to-have acima, não bloqueante).
- O escopo em arquivos do W4-C — mais preciso que a v2.2, sem
  introduzir nada preocupante ao meu domínio.
- Tudo que já endossei nos rounds 1 e 2 sobre o fix do W1, o gate do
  nightly e a infraestrutura de npm trusted publishing continua válido
  e não mudou na v2.3.
