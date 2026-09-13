---
plan: PLAN-169
release: v1.4.0 (GA)
attempt: repass-ga r2 (2026-09-13, S351)
status: NO-GO (1/7) — triado; condição 63 reescrita como CLASSE; r3 sobre candidato novo
---

# Re-pass do GA v1.4.0 — tentativa r2 (NO-GO na parte 1)

- **Candidato:** `6344f6e45c2f5d1bd9c85f9740864ea78b000f1d` (r1 + emenda da condição 63 «três sítios»).
- **Runner:** 7 partes, `GA_CODEX_JOBS=7`, codex 0.147.0 pinado, modelo `gpt-5.6-sol`; lançado 13:44; `codex rc=0` nas 7; `RUNNER-OVERALL: rc=1`.
- **Evidência completa** arquivada FORA da árvore em `~/.rc2-backup/repass-ga-20260913-NOGO-r2/` (39 arquivos, `MANIFEST-ga.sha256` verificado antes do arquivamento). Aqui: 7 vereditos, proveniência, manifesto, candidato.

## Vereditos

| Parte | Veredito |
|---|---|
| 1 `upgrade.sh` | **NO-GO — condição 63 falsa: «três textos» quando `upgrade.sh:2819-2822` também chama o perfil `user` de «advisory»** |
| 2 | GO-WITH-CONDITIONS (anexos da rc.1 mantidos como known-open) |
| 3 | GO-WITH-CONDITIONS (a parte que deu NO-GO no r1 aceitou a emenda) |
| 4 | GO-WITH-CONDITIONS — 2 P1 novos (anexo 1.4.1: SPEC declara-se v1.9.1; ver r1) |
| 5 | GO-WITH-CONDITIONS |
| 6 | GO-WITH-CONDITIONS |
| 7 | GO-WITH-CONDITIONS |

## Triagem (13/09, 18:4x)

A claim da parte 1 é verdadeira: `scripts/upgrade.sh:2822` diz «the advisory user profile» (e `:2838`, `:2944` falam de «advisory switch»). Duas rodadas caíram pela MESMA forma — a condição 63 enumerava sítios («único» no r1, «três» no r2) e cada revisor, medindo o seu payload, achou mais um. `grep -i` de classe na árvore entregue (13/09) dá **10 linhas** em 6 arquivos (`install.sh:11`, `profiles.json:13,30`, `upgrade.sh:2822,2838,2944`, `build-plugin.py:7`, `settings.user.json:42,230`, `README.md:144`).

**Cura (texto, árvore da rc.1 intacta):** a 63 deixa de contar e passa a declarar a CLASSE — todo texto entregue que chame o perfil `user` de «advisory» é inexato; a lista conhecida é a medida acima; «qualquer outra ocorrência é da mesma classe, igualmente inexata, e não é condição nova». Um 12.º sítio deixa de falsificar a condição. A frase histórica «deixaram de dizer… (arquivos livres)» sai (não era condição) para pagar os bytes (parte 1 do r2: 261.834 B; teto 262.000).

## Regra confirmada (2.ª vez neste trem)

Enumerar variantes não converge; declarar a classe converge (memória `feedback-release-repass-lessons-s349`, `feedback-instrument-that-predicts-code-by-text-never-converges`).
