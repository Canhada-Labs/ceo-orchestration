---
id: PLAN-189
title: Rail configuration on measured evidence
status: draft
created: 2026-09-15
owner: CEO
depends_on: []
---

## Context

O trilho de revisão cruzada (Claude autor, Codex revisor) deixou de fechar
trabalho e passou a gerá-lo: 6 rodadas no GA v1.4.0, 20 na rc.1, 27 registros na
wave `179close`. No GA, **quatro das seis rodadas foram NO-GO pela MESMA condição
do envelope**, em redações sucessivas — nenhuma tocou um byte entregue. Em
paralelo, 25 lands livres numa janela de 24 h contra ZERO canônicos assinados.

Na S352 tentei fechar essa questão por análise e **errei**: medi que 5,9% dos
achados HIGH são classificados como «produto» e comparei esse número com o
limiar de 30% de falso positivo (Bessey/CACM 2010) e com os <5% que fizeram o
curl fechar o bug bounty. A comparação é INVÁLIDA — classe temática diz sobre o
que o achado fala, não se ele é verdadeiro. Uma segunda lane de pesquisa (Codex
GPT-6 Astra, prompt FRIO, sem ver as minhas conclusões) refutou seis conclusões
que nunca leu, e a sensibilidade que ela calculou mata o número: 32,2% dos HIGH
são `unknown`; se fossem produto, a fração iria de 5,9% para **38,1%**.

Evidência externa levantada nas duas lanes está em memória
(`reference-rail-configuration-evidence-s352`) — **não re-pesquisar**. O que ela
estabelece: filtrar achados tem custo medido em RECALL (BitsAI-CR/FSE 2025:
45,5%→39,8%); escopo por risco NÃO preserva cobertura (Kamei/TSE 2013: 20% do
esforço pega 35% dos defeitos); cross-vendor se sustenta (Kim/ICML 2025;
Apollo 2026: correlação de erro 0,78 intra-família); 2 e 4 revisores não diferem,
1 é pior (Porter/TSE 1997). E o que ela NÃO estabelece: um número ótimo de
rodadas para revisão de código canônico — a evidência mais próxima
(Chun et al./TOSEM 2026) aponta para parada CONDICIONADA ao estado, não teto fixo.

Conclusão desta fase: **a decisão não pode sair da literatura nem do censo
temático. Tem de sair de medição própria.**

## Goal

Produzir a medição que decide a configuração do trilho — número de rodadas,
critério de promoção de achado e escopo — e só então ratificar um ADR.

## Thesis

O censo temático responde «sobre o que o achado fala». A decisão precisa de
«o achado é verdadeiro?», «tem consequência?» e «é novo?». São perguntas
diferentes e a segunda exige leitura de uma amostra, não agregação.

Duas propriedades tornam isso barato: (a) o corpus já existe e é durável —
**287 arquivos de rodada rastreados em git, com 427 marcas de severidade HIGH**,
cobrindo 8+ cerimônias; (b) as células de resultado podem ser pré-registradas,
de modo que a medição decide sozinha qual cura se aplica, sem nova rodada de
argumentação.

Nota de corpus: a medição S348 (426 registros) usou packs FORA do repo, com
janela de mtime de 3 dias; esses packs não foram localizados e provavelmente não
são reproduzíveis. Este plano mede o corpus in-repo, que é outro universo — os
números não são comparáveis linha a linha, e o plano NÃO deve tentar reconciliá-los.

## Items

### W0 — Extrator e amostra cega  [P0]

- CAN edit: `.claude/plans/PLAN-189/` (novos arquivos)
- Deriva o parser de blocos do instrumento existente
  (`.claude/plans/PLAN-188/measure-rail-classes-v2.py`, 165 linhas) para ler o
  corpus IN-REPO em vez de packs efêmeros.
- Extrai cada bloco HIGH com: id estável (sha do texto), plano, cerimônia, número
  da rodada, texto do achado. **O id é o único campo visível ao classificador.**
- Amostra estratificada por cerimônia, n a definir (OQ-1), com semente fixa
  registrada no plano.
- AC: o extrator é determinístico (mesma semente ⇒ mesma amostra); a amostra
  cobre ≥6 cerimônias distintas; nenhum campo de rodada/fornecedor/plano viaja
  para o arquivo de classificação.

### W1 — Classificação cega em dois eixos  [P0]

- CAN edit: `.claude/plans/PLAN-189/`
- Cada achado da amostra recebe:
  1. **VALIDADE**: verdadeiro / refutado / indeterminado (com a evidência que decide).
  2. **CONSEQUÊNCIA** se não curado: execução indevida | quebra de autorização |
     declaração enganosa ao adopter | perda de auditabilidade | editorial.
  3. **DUPLICAÇÃO**: repete achado já registrado nesta cerimônia? (sim/não)
  4. **PERTINÊNCIA**: precisava ser curado ANTES daquela release? (sim/não)
- Saída: as três taxas que a S352 confundiu — precisão, utilidade, aceitação —
  cada uma com o denominador explícito.
- AC: classificação feita sem acesso a rodada/fornecedor/plano; discordância
  entre lanes registrada, não resolvida por maioria silenciosa.

### W2 — Retorno marginal por rodada  [P1]

- CAN edit: `.claude/plans/PLAN-189/`
- Para cada cerimônia com N rodadas: quantos achados **únicos e válidos** a
  rodada k acrescentou sobre as anteriores. Esta é a medição que a literatura
  não pode dar por nós.
- AC: curva por cerimônia + agregado; declara explicitamente o viés de que
  pacotes que ficam mais tempo no trilho geram mais registros.

### W3 — ADR da configuração  [P1]

- CAN edit: `.claude/adr/` (novo ADR), `PROTOCOL.md` (se a regra mudar)
- **Bloqueado até W0+W1 fecharem.** Redige a decisão a partir da célula de
  resultado que a medição selecionou (ver «Células pré-registradas»).
- AC: cada parâmetro do ADR cita a medição própria que o sustenta ou é declarado
  «sem evidência»; `PROTOCOL.md` é canônico ⇒ cerimônia assinada.

## Células pré-registradas (decidir ANTES de medir)

Qual cura se aplica é função do resultado, fixada aqui para que a medição não
seja lida à luz da narrativa que se quiser contar depois:

| Resultado da amostra | Leitura | Cura que se aplica |
|---|---|---|
| validade ≥80% E consequência material ≥50% | o trilho está SAUDÁVEL; o custo está na cerimônia | priorizar PLAN-188 (toolkit); NÃO mexer no rail |
| validade ≥80% E consequência material <20% | achados verdadeiros mas irrelevantes | gate de promoção por CONSEQUÊNCIA |
| validade <50% | precisão real baixa | aí sim comparável a Bessey; rever prompt e escopo do revisor |
| duplicação >30% | o mesmo achado renasce entre rodadas | dedup por id estável — cura barata, alta alavancagem |
| retorno marginal ~0 após a rodada k | saturação PRÓPRIA medida | teto mecânico em k |

Se duas células acenderem, a de menor custo de implementação vem primeiro.

## Open questions

- **OQ-1.** Tamanho da amostra: 100 (±10 p.p. a 95%) ou 150? Custo sobe linear
  com leitura humana/agente.
- **OQ-2.** Quem classifica? Proposta: **duas lanes cegas** (Claude e Codex) sobre
  a MESMA amostra, medindo concordância — a concordância é o que diz se a
  classificação é confiável. Dobra o custo.
- **OQ-3.** O corpus S348 (packs fora do repo) é dado como perdido? Se sim, o
  plano declara os 5,9% como não reproduzíveis e segue só com o corpus git.
- **OQ-4.** Se a medição disser «o trilho está saudável» (1.ª célula), aceita-se
  que o problema era cerimônia e o rail fica como está?

## How to continue

Primeira mensagem de uma sessão nova:

> Ler `.claude/plans/PLAN-189-rail-configuration-evidence.md` e a memória
> `reference-rail-configuration-evidence-s352` (evidência externa — não
> re-pesquisar) e `feedback-thematic-class-is-not-false-positive` (o erro que
> originou o plano). Responder OQ-1..OQ-4 com o Owner. Executar W0.

## Success criteria

- [ ] W0: extrator determinístico + amostra cega estratificada, semente registrada
- [ ] W1: amostra classificada por validade e consequência, três taxas com denominador
- [ ] W2: curva de retorno marginal por rodada, com viés declarado
- [ ] W3: ADR ratificado citando medição própria por parâmetro (ou «sem evidência»)
- [ ] Nenhum parâmetro do ADR sustentado apenas por literatura transferida
- [ ] Regra de parada honrada: o plano não gera rodada de argumentação sobre texto

## Regra de parada (pré-registrada)

Este plano existe para MATAR um loop; não pode virar um. Se W0+W1 não fecharem
em **duas sessões**, o plano para e entrega o que mediu, com a decisão explícita
de manter a configuração atual do rail até haver dado. Discussão sobre a redação
deste plano não é trabalho: emenda ou segue.
