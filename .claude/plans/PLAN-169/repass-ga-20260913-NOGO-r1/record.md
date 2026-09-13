---
plan: PLAN-169
release: v1.4.0 (GA)
attempt: repass-ga r1 (2026-09-13, S351)
status: NO-GO (1/7) — triado; cura de TEXTO do envelope (condição 63); r2 sobre candidato novo
---

# Re-pass do GA v1.4.0 — tentativa r1 (NO-GO na parte 3)

- **Candidato:** `0205020b6e0df12c268aef32a41431352675b27d` (rc.1 `02ded1b` + cura de calendário `fd84566` + kit do GA `7b2a14d`/`97f25f6`/`0205020`).
- **Runner:** `repass-ga/run-ga-repass.sh` (7 partes, `GA_CODEX_JOBS=7`, codex 0.147.0 pinado por npx, modelo `gpt-5.6-sol`); lançado 10:39, terminado antes de 13:34; `codex rc=0` nas 7 partes; `RUNNER-OVERALL: rc=1`.
- **Evidência completa** (payloads redigidos, diffs, manifestos de paths, transcripts, `CONDITIONS-ga.reviewed.md`) arquivada FORA da árvore em `~/.rc2-backup/repass-ga-20260913-NOGO-r1/` (39 arquivos; `MANIFEST-ga.sha256` copiado aqui pina cada um). Aqui ficam só os 7 vereditos, a proveniência, o manifesto e o `CANDIDATE.sha`.

## Vereditos

| Parte | Escopo | Veredito |
|---|---|---|
| 1 | `upgrade.sh` | GO-WITH-CONDITIONS — sem P1 novo; 2 P2 |
| 2 | `install.sh` + manifesto + rotas | GO-WITH-CONDITIONS — 4 anexos P1 (known-open, 1.4.1) |
| 3 | `doctor.sh` + `uninstall.sh` + `templates/**` | **NO-GO — condição declarada 63 FALSA** |
| 4 | SPEC + npm README + CHANGELOG + settings + smoke-install | GO-WITH-CONDITIONS — 2 anexos P1 novos |
| 5 | hooks de continuidade de compaction | GO-WITH-CONDITIONS — sem P1 novo |
| 6 | núcleo de cadeia/auditoria em `_lib/` | GO-WITH-CONDITIONS — sem P1 novo; 1 P2 |
| 7 | PostCompact + resolvedor + store + isolamento + CI | GO-WITH-CONDITIONS — 7 anexos P1 (known-open, 1.4.1) |

## O achado da parte 3, verificado contra o código (13/09, 13:4x)

A condição 63 (texto herdado da rc.1) afirmava: «o ÚNICO texto que ainda diz «advisory hooks only» é o cabeçalho canônico de `scripts/install.sh` (linha 11)». **Falso:** `scripts/profiles/profiles.json` promete «advisory-only hook surface» para `--ceremony user` nas linhas 13 e 30, e `scripts/` está na allowlist `files` de `npm/package.json` (entregue no pacote). O revisor da rc.1 (parte 3, GWC) não pegou; o do GA pegou e aplicou a regra do corte corretamente (NO-GO só por condição FALSA ou P0).

**Cura (texto, não código — a árvore da rc.1 fica intacta):** a condição 63 passa a declarar os TRÊS sítios (`install.sh:11`, `profiles.json:13` e `:30`) como inexatos até a próxima cerimônia; a cura de código (contrato «sem GPG» no lugar de «advisory» + guarda em `check-install-profiles.py` quando `blocking_inclusions` não é vazia) entra na lista da 1.4.1. Emenda aplicada pelo derivador (`derive-ga-kit.py`, âncora exata `COND63_RC1 → COND63_GA`); r2 roda sobre o candidato que contém esta emenda.

## Regra que esta tentativa confirma

Cada emenda ao envelope vira alvo do rail; uma claim de «único» só sobrevive se foi medida pela CLASSE (aqui: `grep -i`, porque a segunda ocorrência era «Advisory-only» com maiúscula). Ver `feedback-declared-conditions-make-the-rail-audit-the-signed-text` na memória.
