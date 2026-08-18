---
status: ACCEPTED
date: 2026-08-09
accepted: 2026-08-18 (Owner aceitou com renumeração — decisão estruturada S312; o número 191 foi tomado pelo spawn-acceptance-contract-v2 do PLAN-178 Lote B)
plan: PLAN-169 (W0.9/OQ-3 aceito pelo Owner; pack W3)
---

# ADR-193 — Break-glass: doutrina para kill-switches de repositório

## Context

Dois kill-switches vivem como variáveis de repositório e desligam
camadas de governança inteiras: `CEO_SOTA_DISABLE` (desliga jobs de CI
gateados) e `CEO_PAIR_RAIL_VERDICT_OPTIONAL` (rebaixa o gate de verdito
do pair-rail no release). Nenhum tinha doutrina: quem pode virar a
chave, quando, por quanto tempo, com que registro. Um kill-switch sem
doutrina + um gate que o recusa = caminho de incidente DURANTE a janela
de release (ledger E.5/A.0.5 do PLAN-169) — exatamente quando a pressão
para "resolver rápido" é máxima e o custo de um erro é público.

## Decision

1. **Quem:** só o Owner vira qualquer chave break-glass (são variáveis
   de repositório — já exigem permissão de admin; esta linha torna a
   regra explícita, não delegável ao CEO/agentes).
2. **Quando:** exclusivamente para destravar um incidente ATIVO em que
   o gate protegido é o próprio bloqueio E a causa-raiz já está
   compreendida. Nunca para "andar mais rápido"; nunca preventivo.
3. **Registro obrigatório (trilha):** virar a chave exige, no MESMO
   dia: (a) linha no log de auditoria (evento `config_change` já
   existente para vars vigiadas) ou, na indisponibilidade, entrada no
   plano ativo com timestamp; (b) issue/plano nomeando causa e
   gatilho de reversão.
4. **TTL:** toda ativação nasce com prazo declarado (default: 24h).
   Chave ainda ativa após o prazo = incidente novo, não extensão
   tácita.
5. **Reversão:** a chave volta ao default no fechamento do incidente;
   o fechamento CITA a reversão (checklist do incidente).
6. **Inventário:** `CEO_SOTA_DISABLE`, `CEO_PAIR_RAIL_VERDICT_OPTIONAL`
   e qualquer futura variável cujo efeito seja desligar/rebaixar um
   gate de release ou CI. Adicionar uma chave nova ⇒ emendar este ADR
   (a lista fechada é parte da decisão).

## Consequences

- A janela de release ganha uma rota de emergência LEGAL e auditada —
  a alternativa real observada era pressão para contornar o gate ou
  edição ad-hoc de workflow, ambas piores.
- Custo assumido: fricção deliberada (registro + TTL) exatamente no
  momento de pressa; é o ponto.
- O gate novo do pair-rail (quando landar) DEVE aceitar a chave com
  doutrina em vez de recusá-la às cegas: recusar um break-glass legal
  re-cria o caminho de incidente que este ADR fecha.
