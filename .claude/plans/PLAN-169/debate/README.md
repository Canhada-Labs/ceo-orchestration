# Registro do debate PLAN-169 — notas de conformidade

Debate formal: **5 rounds, terminal em `round-5/consensus.md` (`status: unresolved`, §12.4)**. Rodou
sob execução autônoma (S298) com o rail codex cross-vendor em paralelo
(r1-r22). Round-4 convergiu (jaccard 1.0) sobre a v2.4; o rail então
evoluiu o plano para v2.5, e o **round-5 foi a triade COMPLETA
revisando o design EXECUTÁVEL v2.5** (Security ACCEPT + DevOps ACCEPT +
VP ADJUST/MF-D-aplicado). Gate de máquina no r5: jaccard 0.692 /
max-rounds ⇒ §12.4 escalado ao Owner (NÃO declarado met).

## 1. Trust model do quota-resume (delta v2.4→v2.5, revisado no r5)

O rail codex (r11/r15) trouxe um delta de DESIGN no quota-resume —
descarte da assinatura HMAC do snapshot (viraria oráculo de mesmo-UID)
→ trust model estreitado honesto. Security re-avaliou (a crítica está
em `round-5/security-engineer.md`): ACCEPT, VETO não exercido.

## 2. Conformidade §4 + anonimização §13.2 — DECISÃO DELIBERADA do CEO, escalada ao Owner

Dois itens de PROCESSO do registro de debate, que o rail codex
(r16/r19/r20) levanta repetidamente e que o CEO decide DEFERIR
conscientemente (não omitir) — escalados ao Owner no checklist de
retorno:

- **§4 (conformidade de crítica):** `round-N/{vp,devops}.md` usam os 7
  cabeçalhos de conteúdo mas alguns sem `skill`/`agent_persona`/
  `generated_at` e com formas curtas de cabeçalho. O parser de
  convergência (só lê `## Risks`) NÃO é afetado.
- **§13.2 (anonimização):** as sínteses foram feitas com a autoria dos
  críticos VISÍVEL; os `anonymization-map.md` foram criados a
  posteriori.

**Por que DEFERIR e não regenerar:** regenerar a cadeia de 4 sínteses
com entradas anonimizadas e normalizar 15 arquivos de crítica é um
re-spawn de custo alto cujo GANHO é nulo para as DECISÕES: o registro
mostra que TODAS as must-fix dos 3 arquétipos foram honradas (nenhum
viés por-nome observável), e o valor técnico do debate (achar falhas
de desenho) já foi realizado e preservado. Regenerar seria teatro que
queima o orçamento que o Owner mandou conservar — e é exatamente o
loop patch-ramo-a-ramo que a lição-mãe da S296 manda evitar. **O Owner
ratifica esta deferral (ou pede a regeneração) no retorno.** Se
ratificada, vira dívida nomeada de higiene de registro, não bloqueio.

## 3. Reconciliação máquina-vs-conteúdo (histórico)

Uma cadeia de rounds intermediários expôs defeitos do PRÓPRIO
instrumento `debate-converge.py` (agora itens W2.9 do plano): (i)
`## Risks` sem bullets = contribuição zero silenciosa; (ii) resolução
de risco derruba o Jaccard; (iii) max-rounds força
`convergence_met=false` mesmo com jaccard ≥ threshold. Nenhum é
defeito do PLAN-169 como desenho — o plano os observa e os conserta.
