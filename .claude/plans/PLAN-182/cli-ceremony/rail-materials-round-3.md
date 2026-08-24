# Pair-rail — materiais de cerimônia (árvore viva), rodada 3 (S326, 2026-08-24 17:03–17:1xZ)

**Instrumento:** `codex exec review --uncommitted` na árvore VIVA sobre o conjunto FINAL a commitar:
`OWNER-S326-SIGN.sh` (P0 novo: modificação rastreada aborta; untracked tolerado só com oráculo=0),
`OWNER-S326-LAND.sh` (G0 por oráculo + porcelain `-z`; passo S de staging exato), sentinel-draft com
`Patch-sha256 71c8c78b…`, o patch, os registros de rail — e o censo da W0 do PLAN-185 após a 3ª passada.

**Resumo do revisor (verbatim):** *"The new security census has multiple reproducible fail-open
paths that classify unsafe symlink writes and raw sed interpolation as guarded, non-applicable, or
absent."*

## Materiais da cerimônia (este pacote)

**Nenhum achado.** Os 9 comentários do revisor são todos sobre `check-installer-write-safety.py`.

## Censo da W0 do PLAN-185 — decisão: NÃO commita nesta sessão

Nove P1 novos, mesma classe das duas rodadas anteriores (fail-open por forma não modelada): cap de
10 escritas candidatas; `if ! test -e` / `if ! [ -e ]`; jump condicional aninhado creditado como
saída do ramo; guarda `-L` sob condição alheia creditada; helper creditado pelo NOME (`symlink`,
`nofollow`, `lstat`, `deref`); `sed` com script em linha de continuação `\`; substituição de escape
com replacement `&` cru; delimitador da primeira substituição reusado; definição escapada só num
ramo. Após três passadas (8 → 7 → 9 achados) a classe **regenera** — é o sinal de "fix-of-fix"
(PROTOCOL anti-padrão 6): a arquitetura do matcher está errada, não os sítios. A próxima passada
tem de INVERTER a regra: enumerar as poucas formas PROVADAS seguras (cada uma com controle
positivo) e classificar TODO o resto como `indeterminado` (bloqueante) — "enumerar o que MANTER,
não o que remover" ([[feedback-fix-of-fix-means-change-the-cure-architecture]]).

Consequência prática: os 4 arquivos da W0 ficam no disco como RASCUNHO não-commitado (untracked,
não-canônicos — tolerados pelo P0 do SIGN e excluídos do staging exato do LAND); a decisão sobre
destino (rascunho em `PLAN-185/`, ou 4ª passada com a arquitetura invertida) é do closeout.
