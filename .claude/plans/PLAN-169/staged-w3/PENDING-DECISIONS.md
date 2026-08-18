# staged-w3 — decisões do Owner PENDENTES (re-staging S312, pós-GA v1.3.0)

Re-staging por ITEM semântico executado na S312 (17 receitas, Workflow
`wf_69229d1b`, read-only; aplicação serial no main loop). Estado:

## O que está PRONTO para assinar (fases 1-2)

15 targets + 1 novo (`test-w3-vcures.sh`). BASELINE re-pinado no vivo
pós-GA (`d789721`+3). Conteúdo: curas V1/V2/V4/V5 do verdito rc.2 +
B.a (allowlist PROTOCOL_SOURCE + WARNING D3) + guard de ambiguidade
(`_ov_obs_prior_record`) + `--pin` honesto (ADR-155-AMEND-1) + família
de links V5 do install + parity 2º fator causal (smoke W3.2) +
release.yml `cmp -s` byte-exato (W3.c) + prosa 65/3 do nightly (W3.a) +
spawn-hook sem model-id literal + emenda ADR-163 + nota E.17 ADR-186.

## consumed/ — NÃO aplicar (10 arquivos)

9 docs + npm-publish.yml: TODOS os itens já chegaram ao vivo por outra
rota (bump 190→192 ADRs, SLSA→Level 2, timeout 35→50, assert de tag
remota npm-publish:443). Aplicar whole-file REGREDIRIA o vivo.
Mantidos como evidência do staging original.

## pending-w28/ — DUAS decisões do Owner (⚖️)

> `RELEASE.md` staged também vive aqui: seu único delta ("31→32 steps")
> conta o step W2.8 no release.yml — só faz sentido SE a família landar.



1. **W2.8 — família gate-scripts checksum manifest** (`ADR-192-gate-
   scripts-checksum-manifest.md` + `gate-scripts-manifest.txt` + 4
   steps de workflow que ficaram FORA dos staged regenerados).
   O doc-fonte (`PLAN-169/W2.8-free-script-gate-family.md`) marca:
   "A DECISÃO é do Owner". Se ratificar a rota (b)-narrow:
   (a) landar o ADR via cerimônia canonical; (b) REGERAR o manifesto
   com hashes do vivo (os staged são de S299 — stale por construção);
   (c) inserir os 4 steps num trem próprio. Se recusar: registrar e
   arquivar.
2. **W0.9 — ADR break-glass** (`ADR-191-break-glass-repo-kill-
   switches.md` em pending-w28/). Decisão "aceite → W3; recusa →
   registrar" NUNCA foi tomada. ⚠️ O número 191 foi TOMADO pelo
   spawn-contract (Lote B) — se aceito, o ADR é RENUMERADO para o
   próximo livre no momento da escrita (regra ADR-numbering do debate
   179 §8.2); referências internas idem.

## Como assinar

`bash ~/canhada-labs/OWNER-W3-SIGN.sh` (gera W3-approved.md com
Anchor-SHA do HEAD, assina, roda o land em --dry-run e depois real).
