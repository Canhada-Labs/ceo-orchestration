# wave-w5 — sentinel de aprovação (DRAFT: o SIGN preenche Data / Anchor-SHA / Approved-By e assina)

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
Wave: wave-w5 (D3 — terceiro leitor de `delivery-routes.tsv`; D1 — entrega de `docs/` e `.github/` no upgrade; emenda da OQ-5)
Patch: .claude/plans/PLAN-183/w5-ceremony/S327-W5-DELIVERY.patch
Patch-sha256: eaba627e0faa74b33e0ab047cc46eeefdf6ec8b40cb0c26f9975fec8fe8be45f
Patch-base: 56f050c9a0c4630fae958d94c3e628a24825accd
Anchor-SHA: ca0297ca0ef05a7151edf1c8ed0adf18901fb53a
Data: 2026-08-25

## O que esta wave entrega

**D3 — o terceiro leitor da tabela de rotas (canônico).** `scripts/delivery-routes.tsv`
já é lido por dois consumidores (`scripts/tests/_parity_classify.py` e
`scripts/doctor.sh`); o gerador do manifesto de baseline
(`scripts/_framework_manifest_set.sh`) resolvia `$FMS_HASH_ROOT/$rel` **sem
fallback** — `docs/*` gravaria o hash do homônimo da raiz e `.github/*.template`
cairia no `continue`, sumindo do baseline em silêncio. A wave fecha isso com o
mesmo idioma de varredura linear do `doctor.sh` (piso bash 3.2: sem `declare -A`),
mantendo `${_rs_transform:-}` com default **vazio** — `${_rs_transform:-identity}`
foi o achado de fail-OPEN do rail que reabriu um vazamento real de contaminação.
D3 vem **estritamente antes** de D1: o mapeamento de origem precisa existir antes
de a enumeração alargar, senão ~25 sítios latentes viram vivos de uma vez.

**D1 — `upgrade.sh` entrega `docs/` e `.github/` (canônico).** Medido: `grep -c
'github' scripts/upgrade.sh` = 0 e os 3 hits de `docs` são comentários. O install
entrega as duas árvores (`install_docs_templates`, `install_github_templates`),
o upgrade nunca entregou — daí a assinatura `maintainer:1 user:0` e o `STALE`
persistente da paridade.

**OQ-5 — emenda ratificada.** Sem install-state legível **mas com
`.claude/.framework-version` presente**, tratar como adopter e ENTREGAR. O
marcador é a evidência de que o diretório já é adopter — exatamente a distinção
que o fail-safe `CEREMONY_EFFECTIVE="user"` perde, e que deixava a população
histórica (a que a rota existe para curar) sem receber nada. O default de um
diretório que nunca recebeu install **não muda**, e a resolução inferida **não**
persiste (`_CEREMONY_PERSIST` continua 0): persistir uma inferência tornaria
permanente uma migração perdida.

**OQ-4 — a assinatura do Owner É a ratificação.** A OQ-4 (declarar
`HASH_SOURCE` para as rotas novas) não foi ratificada na S325: o Owner decidiu
MEDIR a pista do gerador primeiro. O experimento de braços A/B/C está registrado
em `w5-oq4-measurement-S327.md` (medido na S327: braços indistinguíveis nos oráculos de regressão; pista MISTA recomendada; 0 linhas no TSV de ownership); a pista escolhida e o residual de desenho estão no `PROPOSED-PATCH.md` §6. **Assinar este
sentinel ratifica essa escolha** — não há um segundo ato de aprovação. Se a
medição não sustentar a pista, NÃO assine.

## Base de CI esperada após o land (o `main` está VERMELHO hoje por desenho)

- **Smoke Install / paridade `--mode maintainer`:** hoje `STALE 3` (fatal), causa
  única = D1 aberto. Esperado após o land: `STALE 0`. Os números exatos que o
  land compara vivem em `w5-ceremony/EXPECTED-BASELINE.txt` — o
  `OWNER-S327-LAND.sh` **aborta se esse arquivo faltar** (um V-block sem
  baseline declarada é ruído, não verificação).
- **Paridade `--mode user`:** 0 fatais, antes e depois. Qualquer movimento aqui
  é regressão.
- **Ownership nightly:** conjunto RED **inalterado** = `{OWN-0016, OWN-0024,
  OWN-0027}`. Encolher é FALHA, não sucesso: o gate reprova qualquer diferença,
  e all-green significa que a tabela-verdade mudou.
- **Oráculo unitário de ownership:** `FAIL=0`.

## Autorização de governança

- **Owner, 2026-08-24:** OQ-5 = rota (ii) **com emenda** (`.framework-version`
  presente ⇒ tratar como adopter e ENTREGAR; o Check roda num e2e **sem** o pin
  `v1.2.0`, senão continua cego pela mesma razão de hoje).
- **Owner, 2026-08-24:** OQ-4 **não** ratificada por antecipação — medir a pista
  do gerador primeiro. A medição está no pacote; esta assinatura a ratifica.
- **Debate L3 `w5-round-1`:** ESCALATE / ESCALATE / PROCEED-WITH-CONDITIONS, 24
  achados. As duas escalações foram decididas pelo Owner (acima).
- **Pair-rail (V2 do PROTOCOL):** rodadas registradas em
  `w5-ceremony/rail-round-*.md`; a última rodada sem achado P0/P1 é a condição
  de assinatura.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Plans: PLAN-183
Scope:
  - .claude/adr/ADR-194-delivery-route-resolution.md
  - .github/workflows/ownership-nightly.yml
  - .github/workflows/smoke-install.yml
  - CHANGELOG.md
  - CLAUDE.md
  - README.md
  - README.pt-BR.md
  - docs/ARCHITECTURE.md
  - docs/CTO-GUIDE.md
  - docs/FAQ.md
  - docs/GUIA-COMPLETO.md
  - docs/README.md
  - npm/README.md
  - scripts/_framework_manifest_set.sh
  - scripts/doctor.sh
  - scripts/install.sh
  - scripts/tests/test-doctor-delivery-route.sh
  - scripts/tests/test-install-upgrade-parity-e2e.sh
  - scripts/tests/test-manifest-delivery-route.sh
  - scripts/tests/test-upgrade-historical-adopter.sh
  - scripts/tests/test_install_baseline_manifest.sh
  - scripts/upgrade.sh
<!-- END SIGNED SCOPE -->

## Residual declarado

- O `main` continua vermelho se D1 não curar as três divergências: a paridade
  trata `STALE` como fatal e `templates/docs/BRANCH-PROTECTION.md` divergiu entre
  `v1.2.0` (`61025a16`) e HEAD (`966e0571`). D2 (`b6de7cf`) comprou diagnóstico
  honesto, não o verde — **D1 é load-bearing**.
- O e2e de ownership **não observa** as rotas novas: `_relpath_for`
  (`scripts/tests/test-ownership-table.sh:117-123`) conhece apenas
  `spec|protocol|marker`. Ele é o detector de regressão das 3 superfícies
  existentes; os observadores das rotas novas são
  `test-install-upgrade-parity-e2e.sh` e `test_install_baseline_manifest.sh`.
- `scripts/delivery-routes.tsv` estava ausente das duas listas `paths:` do
  `smoke-install.yml`: um typo confinado à tabela não disparava o e2e que a
  consome. Uma vez que um script CANÔNICO a lê, essa dívida de cerimônia fecha
  no mesmo commit.
- `.github/CODEOWNERS` e `.github/CODEOWNERS.template` são mutuamente exclusivos
  por execução (`install.sh:1496` elif vs `:1511` else): a enumeração não pode
  emitir os dois, ou um vira falta espúria garantida.
