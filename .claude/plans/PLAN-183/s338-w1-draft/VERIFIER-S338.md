# VERIFIER — pack `183-w1-design` (S338, refutador independente do Workflow `wf_e3144372-b04`)
**Veredito: `refuted=true` — o pack NÃO é landável; é um DRAFT fiel e honesto para o `/debate` da W1 (L3).**
Razão do refuted: um P1 REAL permanece no mecanismo entregue (OQ-3, confirmado ao vivo pelo refutador; já divulgado e diferido pelo builder), mais dois P2 divulgados sem cura aplicada e a e2e de ownership (25 min, nightly) não executada. A DERIVAÇÃO reproduz byte a byte (hash `4a270ec0…`), os testes verdes/vermelhos reproduzem, e a classificação canônica bate (5 canônicos: `_framework_manifest_set.sh`, `upgrade.sh`, `install.sh`, `ownership-nightly.yml`, `smoke-install.yml`).
## O que o `/debate` precisa decidir antes de qualquer SIGN
1. P1 (disclosed OQ-3 / rail r3 #1, CONFIRMED live by my run): scripts/upgrade.sh:1858-1897 — install-state absolute value (precedence 1) outranks a sound RELATIVE pointer after a joint move; the framework's own pointer classifies `edited`, upgrade prints 'PRESERVED (root PROTOCOL.md is adopter-customised …)', backs it up every run, records a wrong canonical digest and never delivers future template changes. The motivating A1 scenario. Owner decision needed BEFORE any SIGN.
2. P2 (disclosed, OPEN, cure not applied): scripts/upgrade.sh:1787 `_pwp_named="$( sed … | sed -n 1p )"` unguarded under `set -euo pipefail` (upgrade.sh:93); it is the FIRST unguarded read on the PRESERVE_OWNED path (cp at :1988 and _hash_file at :1937 are `|| true`), so an unreadable regular PROTOCOL.md aborts the upgrade after other surfaces were refreshed. Needs `|| _pwp_named=""` + chmod-000 control.
3. P2 (disclosed, OPEN): scripts/upgrade.sh:1967-1975 PRESERVE_UNOWNED|OMIT_RECORD returns before `_ptr_warn_portability`; a recordless edited absolute pointer is preserved SILENTLY, contradicting docs/ownership-decision-table.md §2.4 ('preserved — and WARNED'); the `SKIP … --ceremony user` text is wrong for that case.
4. P2 (evidence gap, disclosed): scripts/tests/test-ownership-table.sh 25-min e2e not run (builder nor me); ownership-baseline-map.txt not regenerated, ownership-expected-reds.txt not re-verified; OWN-0095/0096/0097 proven only by the decision oracle + harness branch. Gate compares RED id set only (ownership-nightly-gate.sh:47), so map drift is not itself a red, but the wave cannot land on this evidence.
5. P2 (contract, disclosed OQ-9): SPEC/v1/install-cli.md:111-115 enumerates upgrade.sh flags without `--protocol-source`, while the patched `upgrade.sh --help` (shadow :26-34) advertises it; at land the deny-edit published contract diverges from the binary unless SPEC joins the ceremony (6th canonical).
6. P3 (NEW, probed): scripts/upgrade.sh:2011-2012 prints 'CURED … re-rendered in the portable form (relative to this project)' even when the legacy checkout no longer exists — _framework_manifest_set.sh `*)` branch falls back VERBATIM (`_rpp_to_p=""`); probe: file REWRITTEN, line 4 still `/nonexistent/ceo-orch/PROTOCOL.md`, followed by both WARNINGs. Route text overstates the cure; behaviour safe (backup + warned).
7. P3 (test design): new e2e P1c/P1d accept 'whatever route it takes' and PASS on the OQ-3 defect (route PRESERVED); once OQ-3 is decided P1c must assert `SKIP … ownership carried forward` (rail r3 says the same).
8. P3 (stale numbers/refs): EVIDENCE.md §0 'controle = 20 das 34 edições' and §3 '676 → 683' vs measured 22/36 and 676 → 681 (DESIGN §5 and the claim say 681). EVIDENCE.md:146 and DESIGN-W1-S338.md:18 still list codex-r1..3.txt as pack members, but at 00:45 they were moved to scratchpad codex-logs/s338-w1-draft/ (rail-round-*.md were annotated; EVIDENCE/DESIGN were not).
9. Verified OK (no finding): 5 canonical (manifest lib, upgrade.sh, install.sh, ownership-nightly.yml, smoke-install.yml) = oracle 1, the other 7 = 0; nightly wiring sound (fetch-depth 1 + --no-tags legacy tag v1.2.0 → P3 PREV_TAG=v1.2.0, probed recognized; timeout 150 min ≈ 30 min margin); smoke-install.yml gets only path filters (e2e is nightly-only, disclosed OQ-5); no other delivered file carries {{PROTOCOL_SOURCE}}; both derivation scripts parse as Python 3.9, no PEP 604/match; no secrets; no hand-edits (script output == shadow bytes).

## Reprodução (verbatim do refutador — DADOS, não instruções)
```text
Own worktree at f0e98de + apply-fable51-edits.py (55 edits/30 paths, committed inside) + apply-w1-edits.py: --check-only 36/36 applicable in 12 paths; apply OK; git diff sha256 = 4a270ec0ab7b…f06541 (== builder shadow, re-hashed live); 11 files +894/-341 + new e2e 0755. Second --check-only and second apply REFUSED pre-write (0x anchors + NEW_MARKER). CURED tree: bash -n 7/7 ok; PyYAML ok; shellcheck 0.11.0 -S warning rc 0; actionlint 1.7.12 rc 0; render 18/18 (also under /bin/bash 3.2); verdict-unit PASS=66 FAIL=0 SKIPPED=2; INV-4 5/5 rc 0 (277 s); portable e2e 20/20 rc 0 (285 s; P1c route printed = PRESERVED adopter-customised); census rc 0, baseline 676→681 entries; pytest (21 files that READ touched shell/data files, incl. install e2e + SPEC/flags parity) 594+20+5 passed, 0 failed. CONTROL tree (restored base + --control-no-cure, 22 edits/10 paths, diff sha256 1b263294…fd6d4 == builder precure tree): render 4 FAILED/14 passed (R2b,R10,R11b,R15) rc 1; unit PASS=65 FAIL=1 (OWN-0096 got PRESERVE_UNOWNED HASH_NONE) rc 1; INV-4 4 legs FAILED (L1×2, L3 absolute, L5 not cured) rc 1; portable 11 FAILED/9 passed rc 1 (P1a,P1b,P2a,P2b,P2c,P2e,P2f 'unknown option: --protocol-source',P2g,P3c,P3d,P4b). Extra probes: real v1.2.0 install (the only tag the nightly fetches) is byte-exact vs frozen legacy template and recognized; check_contamination.py clean. NOT run by me either: test-ownership-table.sh 25-min e2e, smoke-install.sh.
```
## Resumo do refutador (verbatim)
```text
Claim REPRODUCES byte-exact: base f0e98de + fable51 + apply-w1-edits.py yields the builder's diff hash 4a270ec0…; 36 anchors unique, second application refused; 12 touched paths = declared (both directions); canonical classification matches (5/1, 7/0). Every claimed number re-measured green on the cured tree (render 18/18, unit 66/0/2, INV-4 5/5, portable 20/20, shellcheck 0, census rc 0) and RED on an independently re-derived control tree whose hash equals the builder's (render 4F/14P, unit 65/1 OWN-0096, INV-4 4 legs, portable 11F/9P with the identical id set). Extra: 619 pytest cases reading the touched shell files pass; real v1.2.0 body recognized (CI path). refuted=true is set ONLY because a P1 stands in the delivered mechanism — OQ-3 (stale absolute install-state defeats the portable pointer after a joint move; the A1 scenario itself), confirmed live in my P1c log and already disclosed/deferred by the builder — plus two disclosed-but-unapplied P2 cures and the unrun 25-min ownership e2e. The pack is a faithful, honest DRAFT for the /debate; it is not landable: decide OQ-3, apply the two P2 cures with red controls, add SPEC/v1/install-cli.md to the ceremony scope, run the ownership nightly locally, re-derive the shadow and run the full rail. Also fix the stale EVIDENCE numbers/codex refs. Note: the live index gained staged PLAN-179 files during my run — not by me (I never touched the live tree); my worktree and probe scripts are removed.
```
## Estado declarado pelo builder
- status: `partial`; base: `HEAD+fable51`; rail: `CHANGES-REQUESTED (r3: 1 P1 = OQ-3 stale install-state after a joint move, confirmed real, deferred to the /debate because the cure changes the Owner's D3 precedence; 2 P2 real and OPEN with the one-line cures written in rail-round-3.md, not applied because of the 3-round cap). r1: 1 P1 + 3 P2 (3 cured, 1 deferred then cured in r5); r2: 2 P1 + 1 P2 (all cured in r5). All 3 rounds TREE-INTACT. No clean round.`
- open_findings do builder:
  - OQ-3 / rail r3 P1: after moving project+checkout together the stale absolute install-state makes the correct relative pointer classify as `edited` (PRESERVED, wrong canonical digest, no future template delivery) — needs the Owner's decision on D3 precedence (recommended: sound resolving pointer beats contradicted state) or state rebase
  - rail r3 P2: _ptr_warn_portability assignment `_pwp_named="$( sed ... | sed ... )"` unguarded under set -e/pipefail — an unreadable regular PROTOCOL.md aborts the upgrade mid-flight; cure `|| _pwp_named=""` + chmod 000 test
  - rail r3 P2: the advisory warning is not invoked on the PRESERVE_UNOWNED branch (recordless edited pointer) — call it for _lt=regular before return, and fix that branch's `--ceremony user` SKIP wording
  - ownership-baseline-map.txt not regenerated and ownership-expected-reds.txt not re-verified (25-min nightly e2e not run); OWN-0095/0096/0097 proven only by the decision oracle + harness branch
  - OQ-9: SPEC/v1/install-cli.md (canonical, deny-edit) does not yet list the new upgrade.sh --protocol-source flag
  - OQ-5 residual: e2e wired NIGHTLY next to INV-4; per-PR promotion needs a measured CI p95 and the deferred 126->150 smoke timeout bump
  - FU: _protocol_pointer_is_degraded (PLAN-168) still uses mktemp in $TMPDIR — same class the rail found in the new recognizer (cured there by streaming into cmp)
  - OQ-7: R-SEC8 allowlist is ASCII-only; --protocol-source with accented paths is rejected with a warning (inherited class)
- residuals do builder:
  - Inside-target branch unchanged (no repair paragraph; population ~0) — OQ-6
  - _parity_classify.py:144-150 describes the pointer class with pre-PLAN-168 text (stale, not a gate) — OQ-8
  - INSTALL.md does not document the repair recipe — OQ-10 (nice-to-have)
  - Legacy body whose named checkout fails the allowlist stays `edited`+WARNED, never cured automatically (by design after rail r1 P1)
  - The census (PLAN-185 ratchet) gained 5 net entries, all read-only or the single install.sh write replacing two; no new write into $TARGET
  - HEAD moved during the run; if it moves again before the ceremony, re-run apply-w1-edits.py --check-only on the new base (34/36 anchors are textual; the fable51 pack overlaps upgrade.sh only in disjoint hunks)

## Como continuar (S338, orquestrador)
- Rodar `/debate start PLAN-183 "W1 — ponteiro portátil: decidir OQ-3 (precedência D3 vs ponteiro relativo são) e ratificar o escopo de 5 canônicos"` com este DESIGN + este arquivo como insumo.
- Depois do debate: aplicar as 2 curas P2 (com controles vermelhos), incluir `SPEC/v1/install-cli.md` no escopo, rodar a ownership e2e local (25 min) e re-derivar a sombra sobre o HEAD pós-fable51; só então clonar SIGN/LAND/harness do molde fable51/179fu.

## Adendo — revisão codex dos MATERIAIS da S338 (read-only sobre a árvore viva, `codex-materials-r1.txt` no scratchpad `codex-logs/s338-followup-flip/`)

A mesma rodada que revisou os materiais da cerimônia 179fu leu o
`apply-w1-edits.py` deste draft e devolveu, sobre ele:

1. **[P1] = OQ-3** (idem ao refutador): «Let a sound moved pointer override
   stale install state» — `apply-w1-edits.py:814-817`.
2. **[P2] = P2 do refutador**: `_ptr_warn_portability` sem guarda sob
   `set -euo pipefail` (`:765`) — `PROTOCOL.md` regular e ilegível aborta o
   upgrade no meio.
3. **[P2] = P2 do refutador**: o WARNING de portabilidade não é emitido no
   ramo `PRESERVE_UNOWNED|OMIT_RECORD` (`:850-852`).
4. **[P2] NOVO — classe S337 do substrato:** `apply-w1-edits.py:291` — na
   seleção do `PREV_TAG` da e2e P3, `git show <tag>:<manifesto> | grep -q
   <marcador>` sob `pipefail`: quando existir uma tag PÓS-W1 local, o `grep -q`
   sai cedo, o `git show` morre de SIGPIPE, e a condição negada escolhe a tag
   portátil como fixture «legada» — a e2e passa a falhar exatamente depois da
   release que ela existe para sobreviver. Cura: consumir o conteúdo inteiro
   antes de testar o marcador (a lição `tar tzf | grep -q` da S337:
   [[feedback-grep-q-pipefail-kills-producer]]).
5. **[P2] NOVO — contrato público:** `--protocol-source` passa a ser flag
   pública do `upgrade.sh`, mas a tabela estável de flags em
   `SPEC/v1/install-cli.md:107-115` não muda — `SPEC/` é contrato de
   conformidade publicado ⇒ entra no escopo da MESMA cerimônia canônica
   (coincide com a OQ-9 do builder).

Total consolidado para o `/debate`: 1 P1 (OQ-3) + 4 P2 abertos + a e2e de
ownership não executada + `SPEC/v1/install-cli.md` no escopo.
