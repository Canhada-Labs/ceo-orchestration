---
plan: PLAN-169
round: 4
archetype: VP Engineering
created_at: 2026-08-08
---

# VP Engineering — round 4 (PLAN-169): estabilização final

## Verdict

**ACCEPT** — a única mudança desde o meu round 3 são os dois controles negativos
do W4.1 (`:374-375`), que endurecem o aceite sem tocar nada do meu domínio; meu
conjunto de riscos é o mesmo e nenhum vira bloqueio.

## Summary

- **Verificado, não aceito de palavra:** `:374-375` acrescenta (a) assinatura
  ausente/inválida ⇒ modo advisory, NÃO arma — inclusive com
  `CEO_AUDIT_HMAC_DISABLE` setado — e (b) `resets_at` fora da banda ⇒ não arma.
  São os dois controles fail-closed que faltavam para o aceite end-to-end do
  MF-C ter contrapartida negativa.
- **Must-fix segue vazio desde o round 3.** MF-A (`:544-557`), MF-B (`:229`) e
  MF-C (`:320-323`) permanecem aplicados e intocados.
- **Conjunto de riscos idêntico ao round 3: R-1, R-6, R-8** — nada foi resolvido
  no meu domínio, nada novo apareceu. Estabilizado em 3 por duas rodadas.

## Risks

- **R-1 (VIVO, agora com evidência) — inchaço de pack por omissão de
  classificação; a lição-mãe da S296 reaparece por construção.** Entre a v2 e a
  v2.2, **W3 foi de "3-5 itens fechados" para 7 + 2 inclusões condicionais**
  (`:762-766`) e **W4-C foi de 7 para 8 itens**, com o item 3 virando quatro
  superfícies + rota de migração + testes (`:478-489`) e o item 6 ganhando uma
  decisão de piso de CLI + `SUPPORT.md` (`:494-501`). Ambos cresceram numa única
  passada de rail. A regra "item novo = wave nova, nunca inchaço de pack" está
  escrita e é a mitigação certa; o risco é que ela seja aplicada ao *item* e não
  ao *arquivo* (ver MF-A).
- **R-6 (NOVO) — a janela de congelamento do main não tem custo de saída
  declarado.** `:130-133` proíbe qualquer commit em main do corte da rc.2 até o
  GA, e `:634-635` diz que se `main` avançar vira rc.3 com hold reiniciado. A rota
  existe; o que falta é dizer o que acontece se um CI vermelho legítimo aparecer
  **durante** o hold — hoje a escolha implícita é entre quebrar o freeze e esperar
  24h com vermelho na janela.
- **R-8 (NOVO) — `scripts/upgrade.sh` é tocado por DOIS packs em sequência.** W3
  item 1 edita `:1564-1577` (B.a) e W4-C item 3(d) edita a migração em
  `:2235-2252`, com o trem v1.3.0 e o freeze entre os dois. Se o staged do W4-C
  for preparado antes do W3 landar, o `shasum -c` bate em conteúdo velho — e é
  exatamente a classe que o rail r1 acabou de pegar no script do 167 (staged stale
  que reverteria um plano posterior).

> Os três bullets são byte-idênticos aos do round 3 (e ao round 2), rótulos e
> anchors do v2.2 preservados de propósito: o comparador mede identidade de
> conjunto, e perturbar o texto por cosmética leria mudança onde não houve.
> Nenhum retirado, nenhum novo.

## Must-fix (blocking)

*(vazio — endosso a execução como está.)*

## Nice-to-have

Inalterados do round 3, todos não-bloqueantes: nomear já o controle RECORRENTE em
CI do W4.4 (`validate.yml` é CANONICAL e o W3 fecha antes de o W4.4 decidir) e o
alvo de doc do W2.9(ii) (`DEBATE-SCHEMA.md` free vs `skills/core/debate/SKILL.md`
canônico); uma linha fechando o R-8 ("staged do W4-C montado DEPOIS do W3
landar"); e enumerar os ≥8 atos Owner-only no checklist de retorno.

## Unseen

Inalterados do round 3: o critério verificável da exceção
"operador-supervisionado" no W4-C item 8 (o plano recomenda aos adopters desligar
a ferramenta com que ele próprio se executa); a regra de decisão do W4-C se o
probe W4.2.0 vier ambíguo; e o controle positivo do próprio W2.9 — um fixture com
`## Risks` sem bullets tem de deixar o comparador vermelho e barulhento.

## What I would NOT change

- **Os dois controles negativos novos** (`:374-375`) — é a forma certa: o aceite
  positivo do MF-C ganhou o par negativo, e "`CEO_AUDIT_HMAC_DISABLE` setado ⇒
  advisory, nunca arma" fecha a rota de desarme silencioso.
- **Tudo que endossei no round 3**, sem resíduo: a lista de ARQUIVOS do W4-C, o
  W2.9 existir, a ordem de execução `W0→W1→W2→W6.1→W3→…`, o W1.7-CI fora do gate
  62/3, o controle transitório do W2.6, e a bateria E1-E4 no PLAN-170 com gatilho
  e orçamento próprios.
- **Manter R-1/R-6/R-8 abertos sem virar must-fix.** São propriedades conhecidas e
  aceitas de um plano desta forma; convertê-las em bloqueio na quarta rodada
  adiaria a execução sem reduzir risco real — e a evidência que este próprio
  debate produziu é que rodadas de convergência têm rendimento decrescente.
