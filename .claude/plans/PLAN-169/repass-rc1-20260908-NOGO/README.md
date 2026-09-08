# Re-pass do candidato v1.4.0-rc.1 — rodada 1 (2026-09-08, NO-GO)

Registro da PRIMEIRA rodada do re-pass de release sobre o candidato `4a1b448`
(codex-cli PINADO 0.147.0 via `npx`, modelo `gpt-5.6-sol` — a config global do
maintainer pede `gpt-6-astra`, fora do alcance da CLI pinada; ver
`repass-rc1/run-rc1-repass.sh`). Seis partes, ordenadas por raio de dano ao
adopter (`repass-rc1/README-rc1.md` §2).

| parte | escopo | veredito |
|-------|--------|----------|
| 1 | `scripts/upgrade.sh` | NO-GO (4 P1, 3 P2) |
| 2 | `install.sh` + `_framework_manifest_set.sh` + `delivery-routes.tsv` | GO-WITH-CONDITIONS (3 P1, 1 P2) |
| 3 | `doctor.sh` + `uninstall.sh` + `templates/**` | NO-GO (6 P1) |
| 4 | `SPEC/**` + npm README + CHANGELOG + settings + workflows | GO-WITH-CONDITIONS (2 P1, 1 P2) |
| 5 | hooks da família de continuidade de compaction | NO-GO (3 P1, 2 P2) |
| 6 | núcleo de cadeia e auditoria em `_lib/` | NO-GO (5 P1, 2 P2) |

Os vereditos completos estão em `verdict-rc1-N.txt`; as linhas de proveniência
em `PROVENANCE-rc1.md` (o agregado `RUNNER-OVERALL` e o `MANIFEST-rc1.sha256`
NÃO existem: o runner foi editado enquanto executava — bash lê o script
incrementalmente — e morreu com erro de sintaxe logo depois da parte 6; as seis
partes já tinham sido revisadas com o prompt ORIGINAL). Os `paths-rc1-N.manifest.txt`
são os DERIVADOS desta rodada (o da parte 4 difere do placeholder commitado).

## Triagem

Cada achado foi verificado adversarialmente contra o código no HEAD e os textos
ratificados por um agente `security-engineer` read-only, com reproduções em clone
descartável (`verification-partN.md`; as partes 2 e 4 foram triadas pelo CEO). Regra
aplicada: só arquivos LIVRES pelo oráculo (`check_canonical_edit.py --is-canonical`,
lido pelo STDOUT) recebem cura na mesma noite; o resto vira CONDIÇÃO declarada do
envelope (`repass-rc1/CONDITIONS-rc1.md`) ou cura assinada antes do GA.

Curas livres landadas antes da rodada 2: `templates/.github/workflows/validate.yml.template`
(checksum do actionlint; gate YAML fail-closed), `scripts/uninstall.sh` (uninstall
INCOMPLETO sai 5/6, cabeçalho honesto), `CHANGELOG.md` (duas claims estreitadas para o
que o binário faz), `docs/BRANCH-PROTECTION.md` (checks obrigatórios cobrem as suítes),
harness e2e (asserção U.4 alinhada ao fail-closed).

A rodada 2 recebe as condições declaradas como DATA a julgar (honestas e suficientes
para uma PRÉ-release ⇒ GO-WITH-CONDITIONS; senão NO-GO).
