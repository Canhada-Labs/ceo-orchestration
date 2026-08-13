---
plan: PLAN-177
round: 1
created_at: 2026-08-13
---

# Proposta — PLAN-177 v3 (rc.4: curas dos 4 P1 do re-pass GA)

Plano completo: `.claude/plans/PLAN-177-rc4-ga-repass-cures.md` (v3).
Evidência: `.claude/plans/PLAN-166/repass-ga/verdict-ga-{1,2}.txt`
(commit `85b4b39`). Recon de precisão: 2 agentes Opus read-only (S304).

## Tese

O GA v1.3.0 deu NO-GO (12/08) com 4 P1 — 3 deles "promessa sem gate"
(16ª instância da classe). A rc.4 cura os 4 com **controle positivo em
cada gate** (teste que prova o gate FALHANDO no cenário do P1). As
correções de texto sem os testes novos seriam a instância 17.

## Decisões já tomadas (a criticar)

1. **P1-4 (verdito NO-GO não barra release):** gate de decisão
   `verdict ∈ {GO, GO-WITH-CONDITIONS}` (igualdade EXATA) nos DOIS
   validadores — `validate-pair-rail-verdict.py` (inserção :230/:231,
   `EXIT_VERDICT_INVALID=3`) e `_release_tag_guard.py` (inserção
   :295/:296, modo novo `E_DECISION=13`). `release.sh` NÃO muda (o
   `|| die` existente propaga). Semântica NÃO unificada com
   `OWNER-GA-CUT.sh` (outra superfície: raw rail, `GO` exato, mais
   estrito — coexistem). Regressão em
   `.claude/scripts/tests/test_release_bump_sites.py` (raiz que RODA
   no CI), validador via subprocesso com args LITERAIS do step-15 em 2
   variantes (parent-sha real e `""`); NUNCA em
   `.github/scripts/tests/` (suíte morta — nunca wirada no CI).
   Nenhum dos dois arquivos é canônico ⇒ sem cerimônia.
2. **P1-1 (night-mode .gitignore não chega pelo upgrade):** texto do
   bloco vive em UM gerador novo em `_framework_manifest_set.sh`
   (precedente INV-4/PLAN-168 — duas cópias do texto foi a classe do
   bug do pointer); `install.sh:1830-1857` passa a chamar o gerador
   com saída BYTE-IDÊNTICA (header por-entry dentro do loop — 
   reimplementar "bonito" quebra parity); `upgrade.sh` entrega entre
   :3128/:3130 com gate `CEREMONY_EFFECTIVE != user` (espelho :3084) +
   `command -v` fail-loud + dry-run + `_up_record_op`; allowlist
   `_parity_classify.py:123-132` REMOVIDA no MESMO commit (entry órfã
   = MANDATORY-FIRE). Sem teste novo: fixture v1.2.0 + controle
   positivo já rodam por-PR (`smoke-install.yml:241-270`).
   Superfícies canônicas ⇒ pack GPG único (W1).
3. **P1-2 (INTEGRITY.md "1.0.1"):** texto version-neutral; NÃO
   adicionar como site de bump (doutrina do módulo: writer sem oráculo
   = dead rule); `"npm"` entra em `SCAN_ROOTS`
   (`test_release_bump_sites.py:1158`) + teste que falha em semver nu
   em `npm/*.md` com controle positivo; checklist :68-71 explicitado.
4. **P1-3 (SHA-256 de tarball prometido sem mecanismo):** rota (ii)
   honestidade — INTEGRITY.md move o controle para "not yet automated"
   (modelo: SECURITY.md:79-81), receita de consumidor corrigida (o
   arquivo nem viaja no tarball); promessas-irmãs corrigidas:
   `SHA256SUMS.txt:3,13`, `SUPPORT.md:155`,
   `scripts/install-npm.sh:182-184` (CANÔNICA, 3 linhas — entra no
   pack W1). Gate anti-reincidência: teste "toda linha Where-enforced
   de INTEGRITY.md nomeia step que EXISTE no npm-publish.yml". Rota
   (i) real (gerar checksum no workflow) = item do trem v1.4.0 — toca
   caminho de publish sob hold, não-verificável sem cortar tag.
5. **T-1 tournament.yml** (working-directory, `apply --check` OK) no
   pack W1. **T-2** já landado (`3842d4f`).
6. **FORA da rc.4:** rota (i), node24, patch de perf (validate.yml =
   KERNEL), wiring da suíte morta `.github/scripts/tests/` (KERNEL),
   W3/W4 do 169 (mecanicamente pós-GA pelo assert de delta).

## Riders conhecidos

- R-1: cura do validador MUDA o inputs_hash (arquivo está no próprio
  manifesto) ⇒ envelope rc.4 declara hash novo (natural).
- R-2: `staged-w3/gate-scripts-manifest.txt` pina sha256 dos DOIS
  validadores ⇒ re-pin CONSCIENTE no W3 pós-cura (re-pin cego regride).
- R-3: suíte morta registrada para v1.4.0.
- R-4: censo dos 11 envelopes vivos — nenhum quebra com o gate.

## Perguntas abertas ao debate

- OQ-1: `E_DECISION=13` novo vs reutilizar `E_VERDICT=10`?
- OQ-2: `install-npm.sh` (3 linhas de comentário) no pack W1 ou dívida
  declarada para o próximo trem?
- OQ-3: o gate "Where enforced ⇒ step existe" é executável de forma
  robusta (parse de markdown vs nomes de steps do YAML) ou vira um
  teste frágil que a próxima edição de INTEGRITY.md quebra por forma?
- OQ-4: sequência W2 — algum furo na ordem verdito→push→CI→preflight→
  tag herdada do 166 quando aplicada à rc.4?
