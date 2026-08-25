# wave-w5fix — sentinel de aprovação (DRAFT: o SIGN preenche Data / Anchor-SHA / Approved-By e assina)

> Caminho casa `PLAN-*/wave-*-approved.md` (união fechada de padrões em
> `check_canonical_edit.py:1012`). O binding é o `Patch-sha256` (land por PATCH,
> sem `MANIFEST-*`). O bloco `Scope:` é **DERIVADO** por
> `w5-ceremony/finalize_patch.py` a partir de `git apply --numstat` — nunca
> escrito à mão (foi corrigido duas vezes neste plano e continuou incompleto nas
> duas). O `Anchor-SHA` é preenchido pelo `OWNER-S327-SIGN.sh` com
> `git rev-parse HEAD` no momento da assinatura; o `OWNER-S327-LAND.sh` aborta no
> G1 se não casar. Reescrever um byte deste arquivo depois de assinar invalida o
> `.asc`.

Plans: PLAN-183
Wave: wave-w5fix (smoke-install.yml — o step 'Deepen git history' passa a rodar ANTES da paridade install/upgrade)
Patch: .claude/plans/PLAN-183/w5-ceremony/S327b-W5FIX.patch
Patch-sha256: 219ec54ef1de73a7d1c60a704cd34b5265d97d14ef3457aa7eb9197fb6a48c9d
Patch-base: 6304f6674a316f84f1e62fda431d59f57013b87a
Anchor-SHA: TO-FILL-AT-SIGN
Data: TO-FILL-AT-SIGN

## O que esta wave entrega

**Uma reordenação de steps em `.github/workflows/smoke-install.yml` (canônico) — nada mais.** O step
`Deepen git history` (introduzido na W5 pela rodada 1 do rail, F3) rodava ANTES do teste do adopter
histórico mas DEPOIS da paridade install/upgrade. Medido no primeiro run pós-land (`6304f66`, run
`32845976930`): a paridade `maintainer` saiu `STALE 3` na CI — exatamente os 3 templates que divergem
entre v1.2.0 e HEAD — enquanto o mesmo conteúdo, com histórico completo (LAND V5 local), mede `STALE 0`.
Causa: o hash-gate do D1 reconhece um arquivo do adopter como framework-owned pelas GERAÇÕES git da
FONTE; com `fetch-depth: 1` a geração v1.2.0 é invisível, os 3 caem em PRESERVED (seguro — nunca
bytes errados — mas o classificador acusa STALE). A cura move o deepen (com `if: always()` mantido)
para logo depois do fetch do pin, antes do controle do ponteiro e da paridade; o título do step passa
a nomear os dois consumidores. Reprodução local: clone `--depth 1` como fonte ⇒ `STALE 3`; `--unshallow`
⇒ `STALE 0`.

## Base de CI esperada após o land

- **Smoke Install / paridade `maintainer`:** `STALE 0` (verde pela primeira vez desde a S323).
- **Paridade `user`:** 0 fatais (inalterado). **Ownership nightly:** RED set inalterado
  `{OWN-0016, OWN-0024, OWN-0027}`. **Validate:** verde (já está).

## Autorização de governança

- Mesma autorização da wave-w5 (Owner, 2026-08-24/25); este patch é a correção do instrumento de CI
  daquela wave, sem tocar em `scripts/`. Pair-rail: `w5-ceremony/rail-round-w5fix-1.md`.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs TO-FILL-AT-SIGN
Plans: PLAN-183
Scope:
  - .github/workflows/smoke-install.yml
<!-- END SIGNED SCOPE -->

## Residual declarado

- Um adopter que rode `upgrade.sh` a partir de um checkout RASO do framework fica com os templates PRESERVED (não refrescados) até usar um clone completo — comportamento seguro e nomeado por path; documentar no ADR-194 na próxima cerimônia que toque o ADR.
