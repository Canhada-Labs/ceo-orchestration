---
round: 2
archetype: LLM FinOps Architect
skill: llm-routing-and-finops
agent_persona: (crítico de custo, cota e semântica de roteamento; perfil sintetizado da linha do SKILL MAP — sem bloco próprio em `team.md`)
generated_at: 2026-09-07T00:20:00Z
---

## Verdict

ADJUST — 3 itens BLOQUEANTES (R-FIN1, R-FIN3, R-FIN5).

## Summary (≤ 3 bullets)

- **Os must-fix do round 1 que são meus foram CURADOS e re-verifiquei em disco.** MF-16 (aritmética): 60+70+80+90+60+30 = **390**, 90+110+120+140+100+50 = **610** — fecha com o cabeçalho (:10, :412-414). MF-14 («fornecedor ativo»): `cost-table.yaml` tem **12** identificadores, todos `claude-*`, e `grep -ciE 'gpt|gemini|grok'` = **0** ⇒ UMA raia ativa, como o plano afirma (:180-188). MF-10 (ciclos, arquivo, dono) e MF-11 (31 caixas com `Check:`) estão no texto. Os 4 nomes de evento citados como «já existentes» existem: `audit_emit.py:265, 485, 765, 772`.
- **A tese central continua verdadeira e barata.** Re-medi o oráculo nos 10 caminhos do §2 (:69-78): os 6 valores `1` e os 4 valores `0` batem, inclusive `otel_emit.py 1` (:210-211, e o arquivo importa `urllib.error` na linha 61) — o precedente de «módulo de biblioteca com rede sob cerimônia» é real.
- **Onde ainda quebra é FinOps, não arquitetura:** o orçamento contradiz o próprio campo irmão contra o piso MEDIDO deste repo; o comando único que sustenta os 7 critérios de morte não é exercido por nenhuma das 31 caixas; e «ciclo» é unidade sem taxa — todo limiar de morte é infalsificável enquanto a cadência não estiver fixada.

## Risks

**R-FIN1 — CRITICAL (BLOQUEANTE) — `budget_tokens` e `budget_sessions` são incompatíveis contra o piso de gate-boot MEDIDO neste repo.**
Cabeçalho: `budget_tokens: 390-610k` (:10) com `budget_sessions: 5-6` (:11) ⇒ **65k a 102k por sessão**. O `CLAUDE.md:97` publica a medição própria: «`F` (piso re-pago) foi MEDIDO na S322 … **97.292 tokens** na fronteira de uma compactação real», controle cold-F independente em **97.097** (delta 0,20 %), e o piso de thrashing `T ≈ 107k`. Ou seja: 6 sessões × ~97k = **~583k só de re-pagamento da superfície Gate-1/Gate-2**, o que consome o teto inteiro do plano antes de uma linha de trabalho. E o mesmo `CLAUDE.md:97` avisa que `F` **não é constante** (spread de 51,7 % da média, n=41) — reportar um número único engana. Um dos dois campos está errado; o plano declara os dois e não os reconcilia.
*Mitigação:* derivar `budget_tokens` a partir de `budget_sessions × F` com a faixa de `F` (não a média) e um termo de trabalho por onda, ou baixar `budget_sessions` para o que a aritmética suporta. A fonte é o instrumento rastreado `PLAN-179/w0/gateboot_repay.py` — número gerado, nunca digitado.

**R-FIN2 — HIGH — `budget_usd_estimate` e `tier_mix_estimate` respondem coisas diferentes; a mistura de camadas é decorativa.**
O plano deriva o dólar «do preço do Opus 5 … 5,00 de entrada e 25,00 de saída» com `blended_input_share: 0.80` / `blended_output_share: 0.20` ⇒ 9,00/Mtok ⇒ 3,51-5,49 (:415-421). Confirmei as três entradas em disco: `cost-table.yaml:45-46` e `:85-87`. Mas o campo irmão declara **Opus ~70 % / Sonnet 5 ~25 % / Haiku 4.5 ~5 %** (:13). Aplicando ESSA mistura aos preços do mesmo arquivo (`claude-sonnet-5` 2,00/10,00 em `:110-112`; `claude-haiku-4-5` 1,00/5,00 em `:115-117`): 0,70×9,00 + 0,25×3,60 + 0,05×1,80 = **7,29/Mtok** ⇒ **2,84 a 4,45 USD**. Duas células do mesmo cabeçalho, dois números, ~24 % de diferença. O red flag é o padrão, não a magnitude: uma figura de custo cujos insumos declarados contradizem o campo vizinho.
*Mitigação:* uma linha só — ou o dólar é o TETO conservador (e o texto diz «teto, mistura ignorada de propósito»), ou é o valor da mistura declarada. Escolher e imprimir os insumos.

**R-FIN3 — CRITICAL (BLOQUEANTE) — o comando único dos critérios de morte não é exercido por AC nenhuma, e uma AC invoca um arquivo que nenhuma onda cria.**
§4 fixa «Comando de leitura único: `check-model-currency.py --state --json`» (:387). Medido: `grep -n -- '--state'` no plano retorna **exatamente uma linha, a :387** — nenhuma das 31 caixas exerce o comando de que K-1..K-7 dependem. Segunda perna: a caixa `[P1][US4]` (:336) roda `check-model-currency.py --expected-reds .claude/data/model-currency-expected-reds.txt`, e esse arquivo (i) **não existe** em HEAD, (ii) não aparece na lista de caminhos da W0a (:157-159, três arquivos), (iii) não aparece nos «cinco caminhos canônicos» da W1b (:291-296) — onde a caixa mora. É uma dependência sem dono e um caminho fora do pacote cuja assinatura ele pediria.
*Mitigação:* uma AC própria para `--state --json` (o formato do estado é o contrato dos 7 limiares) e o arquivo de vermelhos-esperados listado explicitamente na W0a (é livre, oráculo 0 em `.claude/data/`), nunca na perna canônica.

**R-FIN4 — HIGH — com UMA raia ativa, K-6 desliga o produto inteiro e nenhum critério dispara.**
O próprio plano mede «existe exatamente UMA raia ativa: Anthropic» (:186-187) — confirmado por `cost-table.yaml` (12 ids `claude-*`, zero de outros fornecedores). Nesse regime, K-6 «3 ciclos ⇒ raia desligada com alerta» (:396) **desliga a única raia**, e não existe critério para o estado «zero raias ativas»: a rotina passa a rodar verde e vazia, que é exatamente a assinatura de saúde. Pior, K-5 (o controle de falso-NEGATIVO, a cada 4 ciclos) roda DENTRO da raia — se a raia está morta por K-6, o único detector de morte também parou. O n do experimento não separa «o feed quebrou» de «o fornecedor não lançou nada».
*Mitigação:* K-8 «zero raias ativas ⇒ vermelho fail-closed», e o controle de falso-negativo fora da raia (executor separado), no molde do `ownership-nightly-gate.sh` que compara conjunto EXATO contra arquivo rastreado.

**R-FIN5 — HIGH (BLOQUEANTE) — «ciclo» é unidade sem TAXA: todos os 7 limiares são infalsificáveis como escritos.**
§1 define «Ciclo. Uma execução da rotina de detecção» (:60-61) e §4 exige que todo limiar seja em ciclos (:385). Mas nada no texto fixa a cadência: o identificador de gatilho foi (corretamente) removido pelo must-fix 15 e substituído pela AC `grep -q 'check-model-currency' … nightly-hygiene/SKILL.md` (:381), que prova MENÇÃO, não agendamento. Consequência mecânica: K-3 «feed mais velho que 4 ciclos» e K-6 «3 ciclos cego» (:393, :396) não têm limite de relógio — uma rotina que **para de rodar** nunca cruza limiar nenhum. É a classe que este repo já nomeou («ausência de resultado NÃO é prova de morte»; e a sonda cuja janela é menor que o período do sinal).
*Mitigação:* declarar a cadência no §4 (uma frase: «um ciclo = uma execução da varredura noturna») e dar a K-3/K-6 uma perna de relógio de parede além da perna em ciclos — senão o limiar em ciclos é honesto sobre a unidade e cego sobre a taxa.

**R-FIN6 — MEDIUM — a W0b custa uma cerimônia GPG + 70-110k para uma raia só, e a alternativa mais barata não está precificada.**
A W0b compra a pergunta «o fornecedor lançou algo ausente do repositório?» (:192-194) para os dois destinos de `platform.claude.com` (:217-218) — isto é, para a única raia ativa. O orçamento dá 70-110k à onda, mas **nenhuma linha do breakdown (:412-414) precifica as rodadas de rail e a cerimônia**, apesar de o repo ter medido repetidamente que um pacote canônico custa rodadas: 27 rodadas no PLAN-179, 11 na wave-s330-F, 9 na wave-cli (`CLAUDE.md` §5). O §5 do plano declara o custo cerimonial em prosa (:408-411) e não o leva ao número.
*Mitigação:* precificar as duas pernas canônicas (W0b e W1b) com um termo explícito de rodadas ao teto vigente (regra R2: 2 rodadas por pacote canônico) e comparar, na mesma linha, contra a rota barata: W0a + leitura manual dos dois endereços pelo Owner no momento da cerimônia — custo canônico zero. Se a W0b sobreviver à comparação, ela fica com razão declarada; se não, economiza-se uma assinatura.

**R-FIN7 — MEDIUM — a primeira caixa da W0a aceita vermelho e verde com o mesmo código.**
`Check: python3 .claude/scripts/check-model-currency.py --check; test $? -le 1` (:166) passa tanto quando o detector não acha divergência (0) quanto quando acha (1). A propriedade que a caixa afirma — «divergência sai como achado NOMEADO, nunca como diferença crua» (:164-165) — não é o que o comando mede; só o crash (rc ≥ 2) o derruba. O controle POSITIVO da linha :175 cobre a redness, então isto não é vácuo total, mas a caixa `[P0]` está medindo a existência do script.
*Mitigação:* mover a asserção para o teste (`-k names_the_finding`) e deixar o `--check` como controle de fumaça.

**R-FIN8 — LOW — o §2 apresenta como «medido na árvore de trabalho» uma tabela cujos 8 dos 10 caminhos não existem em HEAD.**
Verifiquei: `check-model-currency.py`, `model-currency-state.json`, `model_feed_fetch.py`, `model_registry.py`, `models-registry.json`, `models-preference.json`, `check-model-literals.py` e o teste do fetcher estão todos **MISSING**. Os números `1`/`0` continuam corretos (o oráculo responde por PADRÃO de caminho, não por arquivo em disco — foi o que reproduzi), então a tese não cai; o que cai é a palavra «medido na árvore de trabalho», que sugere ao leitor que os arquivos existem.
*Mitigação:* trocar por «medido pelo oráculo, que decide por padrão de caminho — 8 destes 10 arquivos ainda não existem». Uma frase, e a tabela para de prometer mais do que mede.

## O que falta antes da execução (OQ para o Owner ratificar)

- **OQ-FIN-A.** Qual dos dois campos manda: `budget_tokens: 390-610k` ou `budget_sessions: 5-6`? (R-FIN1 — o piso medido de gate-boot torna o par impossível.)
- **OQ-FIN-B.** `budget_usd_estimate` é TETO ao preço do Opus 5, ou o valor da mistura declarada? (R-FIN2)
- **OQ-FIN-C.** Um ciclo é uma execução de qual rotina, com qual cadência? (R-FIN5 — sem isto, nenhum critério de morte pode ser cruzado.)
- **OQ-FIN-D.** A W0b (rede + assinatura) sobrevive à comparação com «W0a + leitura manual do Owner», para uma raia só? (R-FIN6)
- **OQ-FIN-E.** O arquivo de vermelhos-esperados entra na W0a (livre) — confirmar, já que a caixa que o invoca hoje mora na perna canônica de 5 caminhos. (R-FIN3)

*Nota de método: nenhuma afirmação acima foi lida de outro agente; cada uma foi re-verificada em `<ROOT>` em HEAD. Nenhum arquivo do repositório foi tocado.*
