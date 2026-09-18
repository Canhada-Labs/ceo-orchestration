# PLAN-191 — decisões do Owner (S355, 2026-09-18; AskUserQuestion; rótulos VERBATIM)

| # | pergunta | decisão (rótulo verbatim) | consequência para o próximo terminal |
|---|---|---|---|
| OQ-1 | Egresso para a TypeSafe nos braços Jev (W2-iii, W3) NESTE repositório público? | **«Sim, aqui pode (Recomendado)»** | `CEO_JEV_LANE=1` pode ser ligado aqui; nos adopters privados fica OFF por padrão. Chave em `~/.typesafe-key` (teto US$ 100 no console; o Owner mantém e exclui se vazar — decisão de 18/09). |
| OQ-2 | Quota para W0 (piloto) + W1 (cascata) | **«Duas noites (Recomendado)»** | W0 com Haiku/Sonnet/Opus numa noite; W1 com os três braços na outra; ~60-90 tentativas por noite, `--allow-expensive` sob cap declarado, serial. |
| ordem | «PLAN-189 W0 primeiro» (15/09) × «PLAN-190 implementar» (17/09) | **«Os dois: 189 de madrugada, 190 de dia»** | 189 W0 termina o pacote meio construído e vai à assinatura de madrugada; 190 W1.1 corre de dia. WIP canônico = 2 (dentro do teto 3). |
| OQ-3 | Aplicar os 5 adendos (186, 189, 190, 172, Jaccard)? | **«Aplicar os 5 adendos»** | Só texto nos planos; o do 189 espera o land do W0 dele (pack em voo — não editar a fonte de um pack em rail); a decisão sobre o Jaccard morto (religar ou apagar com a promessa do doc) é do Owner na cerimônia que tocar o hook. |
| OQ-4 | Financiar W0.b (tarefas duras do histórico vermelho→verde)? | **«Financiar W0.b (tarefas duras)»** | W0.b entra no orçamento desde já, não só no caso 0-2 qualificadas; a regra de partição do W0 continua valendo sobre W0 ∪ W0.b. |
| portfólio | Fechar PLAN-170? Cortar W4/W5 do 171? | **«Fechar PLAN-170»**, **«Cortar W4/W5 do PLAN-171»** | 170 → `superseded` pela bateria nativa `claude plugin eval` (frontmatter `superseded_by` conforme PLAN-SCHEMA §11); 171 ganha nota de escopo cortando W4/W5 com a razão (W3 duplica o flip do 178; W5 só servia ao E5 do 172, congelado). |

Pré-condições que continuam valendo antes de rodar W0: consertar ou excluir `t09_readme_doc.verify`
(aceita README só com título — reproduzido 18/09) e testar «resposta mínima» nos outros nove `verify`.
