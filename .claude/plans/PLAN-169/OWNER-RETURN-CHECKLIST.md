# Checklist de retorno do Owner — PLAN-169 (S298)

> **STATUS: RATIFICADO E COMMITADO (2026-08-08).** O Owner ratificou
> tudo com as recomendações em chat; o plano está `reviewed` e o pack
> commitado (branch `plan169-pack`). Este arquivo permanece como
> REGISTRO das decisões + a fila de assinaturas do §2, que continua
> sendo o roteiro das ações físicas do Owner nos trens/cerimônias.
> (Texto original do briefing preservado abaixo.)

## 1. Ratificações — ✅ TODAS RATIFICADAS (Owner, chat, 2026-08-08)

> "ratifica tudo com as recomendações e commita o pack" — todas as
> linhas abaixo valem com a coluna de recomendação como DECISÃO.
> Consequências imediatas: plano `draft→reviewed`; waves liberadas na
> ordem pinada; break-glass ADR entra no W3; rota (b) para B.a
> (exceção nomeada no release-checklist da v1.3.0); pack commitado
> em branch `plan169-pack` (§4).

| # | O que decidir | Recomendação do CEO (advisory) |
|---|---|---|
| R-A | **Transição `draft→reviewed` do PLAN-169 v2.5** — o plano está em `draft` (a instrução "autoexecute" autorizou o TRABALHO, mas a v2.5 evoluiu além dela; a marcação `reviewed` é SUA). Marcar `reviewed` libera as waves LIVRES (W0-W2). NOTA: as waves de RISCO (W3/W3-K/W4-C) já são gateadas pela sua assinatura GPG — não rodam sem você de qualquer forma | marcar reviewed (rail 24 rodadas; debate design-coherent) |
| R-B | **Gate de debate ESCALADO (§12.4)**: o round-5 (triade completa sobre a v2.5) terminou `status: unresolved` por MAX-ROUNDS — jaccard 0.692 (a 0.008 do threshold 0.7), 2× ACCEPT + 1× ADJUST (MF-D aplicado), VETO de segurança satisfeito. O CEO NÃO declarou o gate met; VOCÊ decide: **(a)** ratificar o estado como design-coherent e liberar (recomendação do CEO — `round-5/consensus.md` tem a base) ou **(b)** pedir round 6 — nesse caso, o `MAX_ROUNDS=5` é CONSTANTE interna do `debate-converge.py` (não há flag CLI); um 6º round exige bumpar essa constante OU interpretar o jaccard do round-6 diretamente (é o defeito W2.9(iii): max-rounds mascara jaccard≥threshold) | ratificar (a) |
| R-C | **Deferral da higiene de registro do debate** (§4 conformidade + §13.2 anonimização a posteriori) — decisão do CEO, ver `debate/README.md` §2 | ratificar a deferral (ou pedir regeneração) |
| OQ-1 | Ordem de publicação | v1.3.0 GA → v1.4.0 imediata |
| OQ-2 | Postura default do quota-resume (2 sub-decisões) | (i) ativação: só com night-mode OU opt-in `CEO_QUOTA_RESUME=1`; (ii) **um** threshold de arme — recomendação: **90%** (`CEO_QUOTA_RESUME_PCT` configurável) |
| OQ-3 | Break-glass ADR | aceitar (entra no pack W3) |
| OQ-4 | Família "script livre que decide gate" | W2.8 traz a proposta (guard canônico vs checksum) |
| OQ-5 | B.a vs GA v1.3.0 | rota (b): GA com exceção nomeada; OU mini-cerimônia pré-rc.2 de B.a |
| W0.8 | Convenção de ACs de 167/168 | "AC provado no §registro; checkbox não usado" |

## 2. Fila de assinaturas/ações físicas (na ORDEM de execução)

Ordem pinada (codex r4/r16): `W0 → W1 → W2 → W6.1 (trem v1.3.0
completo, main CONGELADO do corte da rc.2 até o GA) → W3 → W3-K → W4 →
W4-C → W5 → W6.2`.

1. **v1.3.0 GA** (PLAN-166 W2): re-pass r2 (worktree limpa no HEAD com
   W0+W1+W2-livres, NUNCA `ad9cc3a`) → verdito rc.2 assinado → push →
   CI verde → `preflight --rc 2` → **tag `v1.3.0-rc.2`** → pre-release
   → **hold 24h** → re-pass final (worktree DA TAG) → assert
   `origin/main == SHA rc.2` → verdito GA assinado+commitado → push →
   **CI verde no commit do verdito** → `preflight --stable` → **tag
   `v1.3.0`** → push da tag → aprovação `production-npm` APÓS
   await-gate verde (sequência pinada do PLAN-166 W2 — nenhum gate
   omitido).
2. **Cerimônias GPG (sessões SEPARADAS):** pack W3 → pack W3-K (kernel)
   → pack W4-C (**cerimônia de KERNEL** — toca settings.json/audit_emit/
   validate.yml).
3. **W5 (ANTES do E0, dentro do 169):** assinar o pré-registro da
   bateria E7 → só então executar o E0 (AC-6 exige pré-registro
   assinado ANTES do 1º run; codex r21-P1).
4. **v1.4.0:** rc.1 → rail até limpo → hold 24h → GA (bump minor =
   controle ao vivo do fix do marcador W2.6).
5. **PLAN-170 (após v1.4.0-rc.1):** executar E1-E4 (o pré-registro já
   foi assinado no W5; o 170 NÃO re-assina, só roda a bateria).

## 3. Estado dos vermelhos conhecidos

- `ownership-nightly`: vermelho de CAUSA CONHECIDA (harness Darwin-only)
  até o W1 landar. Aceite = 62 GREEN / 3 RED {0016,0024,0027}. NUNCA
  silenciar pela tabela.
- `Translations drift`: **CURADO nesta sessão** (seção night-mode
  espelhada no pt-BR; drift=0 local) — verde no próximo push.

## 4. O que a S298 entregou (não precisa refazer)
- PLAN-169 completo (v2.5) + ledger de 65 pendências com evidência.
- Debate **5 rounds** — terminal `round-5/consensus.md` (triade
  completa sobre a v2.5; `status: unresolved`/max-rounds, §12.4
  escalado a você; round-4 = intermediário).
- Rail codex **26 rodadas** — todos os P1 de conteúdo executável
  fechados; escopo do W4-C fecha por PRINCÍPIO (o gate `touched−scope`
  é a autoridade de completude, ver W4-C).
- Higiene: script obsoleto do 167 neutralizado; 2 tarballs + anexos de
  pesquisa movidos ao archive privado; `.gitignore` endurecido;
  TROUBLESHOOTING (EN+pt-BR) corrigido; research-MANIFEST com
  integridade+fontes.
- **Working tree tem o pack do 169 (uncommitted).** Para durar entre
  terminais: `git switch -c plan169-pack && git add .claude/plans/PLAN-169* .claude/plans/PLAN-167/OWNER-PREPARE-TO-SIGN.sh docs/TROUBLESHOOTING*.md .gitignore && git commit`
  (não commitei em main sem seu OK — disciplina de git).
