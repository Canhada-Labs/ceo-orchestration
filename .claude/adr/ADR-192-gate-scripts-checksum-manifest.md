---
status: ACCEPTED
date: 2026-08-09
accepted: 2026-08-18 (Owner ratificou a rota (b)-narrow — decisão estruturada S312, registrada no PLAN-169 §OQ)
plan: PLAN-169 (W2.8; decisão do Owner por delegação explícita S300; pack W3)
---

# ADR-192 — Manifesto checksum dos gate-scripts (rota (b)-estreita)

## Context

As superfícies que DECIDEM release/CI (`release.yml`, `validate.yml`,
`smoke-install.yml`, `ownership-nightly.yml`, `release.sh`, pre-push)
são canônicas/kernel — editá-las exige cerimônia. Mas o corpo da
decisão vive nos scripts que elas invocam, e o censo W2.8 (S299,
extração mecânica com `_matches_canonical_guard` como autoridade)
achou **~50 scripts FREE nessa posição**: um edit livre em qualquer um
muda o que o gate decide, sem cerimônia e sem review cross-model — a
fronteira assinada delega para fora da fronteira.

Duas formas puras foram avaliadas (PLAN-169
`W2.8-free-script-gate-family.md`): (a) canonical-guard por membro
fecha o buraco por construção mas converte TODA iteração dos ~50 em
cerimônia — o harness e2e é iterado em loop L2 e a experiência S296
mostra que fricção alta em superfície de teste induz contorno; (b)
checksum-no-gate devolve a decisão "qual código o gate executa" para
dentro da fronteira assinada sem congelar a iteração fora do gate.

## Decision

**Rota (b)-estreita:** manifesto sha256 canônico
(`.claude/governance/gate-scripts-manifest.txt` — atualizá-lo = cerimônia)
SOMENTE para o subconjunto release-crítico cujo veredito gateia
diretamente tag/publish — **9 membros** (os 6 do censo W2.8 §3 + 2 helpers + 1 dado
adicionados pelas rodadas 2-3 do pair-rail S300):

| Membro | Superfície que o executa |
|---|---|
| `.claude/scripts/local/verify-counts.sh` | validate.yml, release.sh |
| `.claude/scripts/validate-governance.sh` | release.yml, validate.yml, smoke-install.yml, release.sh |
| `.claude/scripts/local/_release_tag_guard.py` | release.yml (3 modos), release.sh |
| `.claude/scripts/check-canonical-doc-freshness.py` | release.yml, release.sh |
| `scripts/tests/ownership-nightly-gate.sh` | ownership-nightly.yml |
| `scripts/tests/ownership-expected-reds.txt` | dado que o gate acima compara (par script+dados pinado; r11) |
| `.claude/scripts/local/release.sh` | driver do operador (sem superfície CI) |
| `.github/scripts/validate-pair-rail-verdict.py` | release.yml (step 15 — decide se um verdito inválido passa) |
| `.claude/scripts/await_release_gate.py` | npm-publish.yml (autoriza o publish) |

Verificação `shasum -a 256 -c`, fail-closed e ANTES de qualquer membro
ser invocado, em **4 superfícies** (este pack): `release.yml`,
`smoke-install.yml`, `ownership-nightly.yml` e `npm-publish.yml` (no
job do await-gate, ANTES de o script de espera rodar). Drift = FAIL
loud com instrução de rota (cerimônia).

Os demais ~42 scripts ficam FREE, cobertos por (i) conjuntos esperados
COMMITADOS (ex.: `ownership-expected-reds.txt` rastreado + o gate
script no manifesto fecha o par script+dados) e (ii) a dimensão
fleet-currency do W4.3 quando aplicável. Revisão anual do censo (mesmo
comando do §4 do doc W2.8).

## Consequences

- Cada edit legítimo num membro passa a exigir a cerimônia que atualiza
  o manifesto — custo aceito para 9 arquivos de cadência baixa.
- **Residuais nomeados:**
  1. `validate.yml` é KERNEL — o passo de verificação lá entra na
     cerimônia de kernel W4-C, não neste pack. Até lá, drift de
     `verify-counts.sh` num PR é pego só no release/preflight.
  2. `release.sh` não tem superfície CI que o execute — sua entrada no
     manifesto é verificação post-hoc (release.yml checa a árvore
     taggeada) + os runbooks OWNER-*.sh; um drift local rodaria o
     preflight uma vez antes de ser pego no gate da tag.
  3. `smoke-install.yml` executa a CÓPIA INSTALADA de
     `validate-governance.sh` dentro do target — essa cópia é entregue
     pela própria run a partir do repo verificado; o manifesto cobre o
     origem, não o artefato instalado.
  4. ~~npm-publish.yml sem passo próprio~~ — FECHADO na rodada 3 do
     pair-rail S300: o argumento "release.yml verifica em paralelo" era
     insuficiente porque o programa que ESPERA o release gate
     (`await_release_gate.py`) rodava antes de qualquer verificação —
     um drift fake-GRANT alcançaria a aprovação `production-npm` com o
     release.yml vermelho em paralelo. `npm-publish.yml` agora carrega
     o passo de verificação ANTES de invocar o await-gate (alvo do
     pack).
  5. **Bypass transitivo do nightly por harness livre (rodada 11 do
     pair-rail S300, residual ACEITO com causa):** o gate
     `ownership-nightly-gate.sh` e o dado `ownership-expected-reds.txt`
     estão pinados, mas o HARNESS (`test-ownership-table.sh`) que o
     gate executa segue LIVRE — um harness substituído que emita
     exatamente os 3 REDs esperados deixaria o nightly verde. Fica
     livre POR DECISÃO: o harness é iterado em loop L2 (pinar =
     cerimônia a cada iteração, o custo que a rota (a) foi rejeitada
     por ter) e o nightly é superfície de DETECÇÃO — não gateia
     tag/publish (release.yml e npm-publish.yml não o consomem), então
     o bypass engana o alarme, não embarca release. Mitigações: o
     harness é rastreado (review de PR), censo anual, e a dimensão
     manifest/fleet do W4.3.
- Adicionar um ramo local que decida integridade fora do manifesto
  reabre a classe que esta decisão fecha (mesma doutrina do
  `_ownership_verdict`, PLAN-167).
