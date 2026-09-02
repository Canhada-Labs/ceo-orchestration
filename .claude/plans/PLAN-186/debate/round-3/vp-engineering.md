---
round: 3
archetype: VP Engineering
skill: architecture-decisions
agent_persona: (nenhuma — arquétipo sem bloco de persona em `team.md`; perfil sintetizado da linha do SKILL MAP)
generated_at: 2026-09-02T22:15:00Z
---

## Verdict

ACCEPT

## Summary (≤ 3 bullets)

- **Os 7 must-fix do round 2 estão RESOLVIDOS**, verificados em disco no plano de 280 linhas: MF1 §frontmatter `external_wait`/`eta_calendar` + headers de W1 (`:125`) e W4 (`:163`); MF2 §3 W1 («o derivador em disco é INSUMO, não entregável» + tabela por sítio antes da cerimônia); MF3 §2b (terceira linha PESQUISA/LEITURA + censo partido em DESENHO vs MECÂNICO); MF4 §2b `:111` (normativa já na W1, lista nomeada de 13 decisões, classificador REFINA); MF5 §3 W4 `:172` (censo por comando `grep`, ≥5 sítios incluindo `RELEASE.md:258`); MF6 §3 W1 blockquote (pré-requisito OQ-7, mesma forma do gate da W3, com dívida aceita e follow-up nomeado); MF7 AC-13, AC-14, AC-15.
- **Os dois advisory também foram atendidos**, e melhor do que pedi: o orçamento virou decomposição de três campos (`budget_tokens` trabalho, `budget_tokens_gateboot`, `budget_tokens_total`), com a objeção «850k < 9 × 97k» citada verbatim no comentário `:10`; os ACs foram reagrupados por wave.
- **Nada novo de escopo.** Verifiquei os dois discriminantes que sustentam o eixo — `check_canonical_edit.py:183-185` e `:329-331` — e a correção do §2b bate com o disco.

## Risks

Nenhum risco novo. Os dois que eu manteria sob observação já estão nomeados pelo próprio plano e não são bloqueantes:

- **R-VP22 — LOW — a tabela por sítio da W1 ainda não existe.** §3 W1 promete publicá-la ANTES da cerimônia e o AC-3a a torna vinculante em segunda perna; até lá o único artefato em disco (`w1/apply-w1-explicit-model.py`) segue com o eixo antigo, agora corretamente rotulado insumo. *Mitigação:* já é o AC-3a; nada a mudar no plano.
- **R-VP23 — LOW — o discriminante «quem escolhe o predicado» é texto até o AC-14.** É a forma certa e o classificador está gated; o risco residual é apenas de ordem, e o §2b `:111` já declara como a W1 opera enquanto isso.

## Must-fix (blocking)

Nenhum.

## Nice-to-have (advisory)

1. Quando a W1 publicar a tabela por sítio, registrar também os dois `[DÚVIDA]` que o derivador carrega (`lane:${vendor}` e `eval:...batch`) como decisões TOMADAS sob §2b, não herdadas — são os dois sítios onde o eixo novo pode divergir do antigo sem que o diff mostre.
2. `AC-11` deixou de ancorar no teto do PLAN-184 com razão escrita (dois `[P0]` abertos). Vale um lembrete no Progress log de re-ancorar se o PLAN-184 fechar antes da W4.

## Unseen by the original plan

Nada. As cinco lacunas que apontei no round 2 estão todas endereçadas por §, e a mais cara — as duas árvores de workflow serem canônicas — propagou para os quatro lugares certos (headers das duas waves, `external_wait`, `eta_calendar` e a correção da frase do §2b), não só para o header.

## What I would NOT change

- **A terceira linha do §2b com o discriminante «quem escolhe o predicado».** É mais forte do que eu pedi: em vez de mover «censo» inteiro, partiu a classe pelo que de fato decide o risco. O exemplo das 9 dimensões do `nightly-hygiene` (executar script nomeado = linha 2; escrever a dimensão nova = linha 1) é o que torna a regra aplicável.
- **«A W1 é wave de CORREÇÃO DE ROTEAMENTO, não de economia».** O plano abriu mão do número que o motivava assim que o eixo mudou, em vez de defendê-lo. Não restaurar a promessa de retorno antes do C2 re-derivado.
- **A decomposição do orçamento em três campos em vez de um número maior.** Um total só teria escondido a mesma ambiguidade que a OQ-6 persegue; três campos nomeados a tornam auditável.
- **O gate da W1 na OQ-7 com dívida ACEITA como alternativa escrita.** Gate que só sabe bloquear vira gate que se contorna; este declara as duas saídas e nomeia o follow-up.
- **`RELEASE.md` dentro do conjunto derivado, e o conjunto definido por COMANDO.** Trocar a lista lembrada por uma derivação é a cura da classe, não do caso.
