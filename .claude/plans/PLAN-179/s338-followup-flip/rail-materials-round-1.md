# wave-179fu — rail codex sobre os MATERIAIS da cerimônia, rodada 1 (S338, 2026-09-02)

Rail-Verdict: CHANGES-REQUESTED (1 P1 REAL no LAND gerado — curado e re-provado pelo harness)

> Distinto do rail do PATCH (`rail-round-1..3.md`, que revisa o diff dos 4
> hooks + teste na sombra): esta rodada revisa os SCRIPTS de cerimônia e os
> registros (SIGN, LAND, finalize, harness, sentinel-draft, EXPECTED,
> PROPOSED, COMMIT-MSG), pedida pelo hook de Stop («RISKY DIFF … get a
> cross-model review before committing»). Comando, da árvore VIVA com os
> materiais em `git add -N` (intent-to-add, para o diff mostrá-los):
> `codex exec review --uncommitted --skip-git-repo-check -c sandbox_mode="read-only"`.
> Saída bruta: `codex-materials-r1.txt` [NÃO versionada — scratchpad S338
> `codex-logs/s338-followup-flip/`] (9.901 linhas, rc 0).

## Achados sobre ESTE pack

1. **[P1, REAL] `OWNER-S338-179FU-LAND.sh:838` usava `$VALIDATE_SH` sem
   defini-la.** Ao clonar o molde fable51 eu reescrevi o bloco de constantes
   e deixei a variável de fora; sob `set -u` o land COMPLETO abortaria no
   V9b (governança) — depois do V2 de 7,5 min e ANTES do staging/commit. O
   `--dry-run` não a alcança (corta antes do V-block caro), por isso os
   casos T2–T12 do harness passaram; o T15b (land completo) teria acusado.
   CURA: `VALIDATE_SH=".claude/scripts/validate-governance.sh"` nas
   constantes (gerador `gen-179fu-ceremony.py`, re-gerado); checagem
   MECÂNICA de variáveis referenciadas-e-nunca-atribuídas nos 4 scripts
   (`undef-check.py` no scratchpad) → `none` no LAND; os outros nomes que
   ela lista (`UNTRACKED_OK`, `FAIL`, `SKIP`, `NO_COMMIT`) são atribuídos
   na mesma linha de outra atribuição ou vivem dentro de um regex do awk —
   falsos positivos, verificados um a um. Harness re-rodado do zero (run 3).

## Achado do harness run 1 (não do codex, mas da mesma classe «molde clonado»)

- **G5 vermelho em TODO caso** porque o `CEO_SENTINEL_UNLOCK` do modo
  auto-teste tinha maiúsculas (`PLAN-179-FOLLOWUP-…`): o regex do unlock em
  `check_canonical_edit.py` é `^(ADR-\d{3,4}|PLAN-\d{3})-[a-z0-9-]{3,100}$` —
  o override cai em silêncio para o rail GPG, que recusa o `.asc` sintético.
  Cura: slug minúsculo `PLAN-179-followup-sessionstart-anchor-id` (o
  179close usou `PLAN-179-closure-…`, também minúsculo). Lição: uma
  constante de cerimônia copiada com o CASE errado não é «texto» — é uma
  chave que o hook valida por regex.

## Achados que NÃO são deste pack (registrados no lugar certo)

O mesmo diff revisado incluía o draft `PLAN-183/s338-w1-draft/apply-w1-edits.py`;
o codex devolveu 1 P1 (OQ-3) + 4 P2 sobre ele — dois deles NOVOS (SIGPIPE
sob `pipefail` na seleção do `PREV_TAG`; `--protocol-source` fora do
`SPEC/v1/install-cli.md`). Todos registrados em
`PLAN-183/s338-w1-draft/VERIFIER-S338.md` (adendo), onde pertencem.

## Critério

O P1 é do INSTRUMENTO (o script que landa), não do entregável — e o harness
existe exatamente para isso; a rodada de materiais o pegou antes (mais
barato que os 25 min do T15b). Sem P1 aberto nos materiais do 179fu após a
cura.
