# anonymization-map — W5-b round-1 aditivo

> Registrado para auditoria (`PROTOCOL.md` §Debate regra 5 +
> `DEBATE-SCHEMA.md` §13.2). Apenas a SÍNTESE consumiu os textos
> anonimizados; este mapa existe para o Owner poder rastrear depois.

| rótulo | lente forçada | veredito | achados |
|---|---|---|---|
| Critic-A | QA / estratégia de teste e poder de detecção — o que cada Check PROVA vs. o que parece provar (teste vacuoso, controle positivo que reproduz o MECANISMO, fixture que envelhece, verde ≠ verificado) | `ESCALATE` | 10 |
| Critic-B | DevOps / CI-CD e superficie de distribuicao (install/upgrade/doctor/uninstall, manifesto de baseline, adopter em campo) | `ESCALATE` | 8 |
| Critic-C | Segurança e raio de dano — o que um erro CUSTA: posse indevida (under-claim), escrita fora do perímetro, deleção, confusão "entregue por nós" vs "do adopter", e decisão de destino a partir de dado ausente/não-confiável. | `PROCEED-WITH-CONDITIONS` | 6 |

**Ordem dos rótulos:** determinística por `sha256(lente)`, não por ordem
de retorno — a ordem de retorno correlaciona com a lente e vazaria a
identidade que a anonimização existe para remover.
