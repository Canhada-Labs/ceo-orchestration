---
plan: PLAN-169
round: 4
archetype: DevOps Engineer
---

## Verdict

ACCEPT — final. A única mudança desde o round 3 (2 controles negativos
fail-closed no W4.1) fica fora do meu domínio; nada a reavaliar.

## Summary

- Meu domínio (release/CI/versão) não mudou desde o round 3.
- Os 2 riscos duráveis do round 3 persistem sem alteração de texto.

## Risks

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

(vazio)

## Nice-to-have

(sem novidade — ver rounds 1-3 para os itens ainda abertos, todos
opcionais e não-bloqueantes)

## Unseen

(nada novo do meu domínio)

## What I would NOT change

Nada — a v2.3/v4 segue correta para o meu domínio em tudo que já
endossei nos rounds 1-3 (fix do W1, gate do nightly, ordem de execução
dos trens, npm trusted publishing).
