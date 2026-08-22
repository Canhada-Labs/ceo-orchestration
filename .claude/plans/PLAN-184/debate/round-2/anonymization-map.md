# Mapa de anonimização — PLAN-184, round 2

> DEBATE-SCHEMA §13.2. O sintetizador consome os rótulos `Critic-A/B/C`;
> este arquivo existe para auditoria, e é lido DEPOIS da síntese, nunca
> durante. Anti-halo: achado se pesa por conteúdo e evidência, não por
> quem o disse.

| Rótulo | Archetype | Eixo atribuído | Achados | Verdict próprio |
|---|---|---|---|---|
| `Critic-A` | DevOps / Platform Engineer | mecanismo do filtro, required checks, semântica de gatilho, runner, reexecução | 7 | ADJUST_PROCEED |
| `Critic-B` | Principal Security Engineer (VETO) | governança e superfície de ataque; markdown normativo; fail-closed real | 10 | ADJUST_PROCEED |
| `Critic-C` | Principal QA Architect | medição, aritmética, instrumento de aceite | 12 | ADJUST_PROCEED |

**Total: 29 achados.** Todos os três foram despachados em paralelo,
read-only (ADR-136-AMEND-1), cada um com o eixo declarado no prompt e
instruído a NÃO cobrir os eixos dos outros — a diversidade é de
perspectiva, não de redundância.

## Nota de integridade do ingest (a razão de este round existir)

O round 1 sintetizou sobre payload **truncado** — 16 de 23 achados, com
um crítico inteiro perdido, e declarou isso honestamente na própria
síntese. A causa foi mecânica: `.slice()` cru sobre JSON *pretty-printed*
gastou o orçamento de caracteres em indentação e cortou no meio do array,
em silêncio.

No round 2 o instrumento foi corrigido (JSON compacto + truncamento que
ENVENENA o veredito da dimensão dona, em vez de sumir) — e ele **disparou
de novo**: as duas sínteses automáticas receberam payload truncado, e a
do 184 declarou `ingest_complete=false`, `findings_received=11` de 29, e
veredito `RUN-ANOTHER-ROUND`. Foi o comportamento correto: o instrumento
recusou-se a autorizar sobre input parcial.

**Esta síntese não é a automática.** O CEO leu os três retornos ÍNTEGROS
do journal do run (`wf_f2943bd9-c0a`, 29 de 29 achados) e sintetizou
sobre o payload completo. O `consensus.md` declara isso no cabeçalho.
