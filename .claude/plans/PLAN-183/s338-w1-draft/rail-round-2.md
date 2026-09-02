Rail-Verdict: CHANGES-REQUESTED (2 P1 + 1 P2, todos REAIS, todos curados no r5)

# Pair-rail — rodada 2 (codex exec review --uncommitted, dentro da sombra)

- Sombra revisada: `…/scratchpad/shadow-183w1` em BASE `f0e98de`+fable51 (commit
  interno `66344c4`) + `apply-w1-edits.py` (estado r4 = r3 + curas do r1 + P2
  re-fonteado).
- Comando: `codex exec review --uncommitted --skip-git-repo-check -c sandbox_mode="workspace-write" </dev/null > codex-r2.txt 2>&1`
  (rc 0; saída bruta em `codex-r2.txt` [saída bruta, NÃO versionada — scratchpad S338 `codex-logs/s338-w1-draft/`], 287 KB).
- `git diff | shasum -a 256` ANTES = DEPOIS =
  `71f684ca18541bf48ad91b0ecd48388b0fa5454806d2498634daf3a1f0430075` ⇒
  **TREE-INTACT** (`git status --short` idêntico: 9 M + 1 ??).
- Resumo do codex (verbatim): «The new lexical relativization can create
  immediately broken pointers for targets reached through symlinked paths. The
  primary end-to-end test is also unwired and will select an invalid fixture
  after the next release tag.»

## Achados

| # | Sev | Achado (codex) | Verificado | Disposição |
|---|---|---|---|---|
| 1 | **P1** | `_rpp_relpath` é LEXICAL, mas o kernel resolve os `..` emitidos FISICAMENTE a partir do diretório REAL do ponteiro; os chamadores normalizam `TARGET` com `pwd` LÓGICO. Target através de symlink que muda a profundidade (`/tmp/x/s -> /tmp/x/deep/root`, target `/tmp/x/s/app`, fonte `/tmp/x/deep/root/ceo`) ⇒ `../../deep/root/ceo`, morto do diretório físico. | **REAL — reproduzido** com a própria função: relpath lexical do target lógico limpo = `../../deep/root/ceo`; `[ -f "$target/$rel/PROTOCOL.md" ]` FALSO (kernel). Pior do que o exemplo do codex: no macOS `install.sh /tmp/app` a partir de `/Users/me/ceo` daria `../../Users/me/ceo` ⇒ `/private/Users/me/ceo` — morto no caso mais comum da plataforma do mantenedor. (A minha 1ª sonda não reproduziu porque `$TMPDIR` do macOS termina em `/` e o `//` resultante caía na recusa lexical ⇒ verbatim absoluto; a sonda foi refeita com base `pwd -P`.) | **CURADO (r5):** no ramo `*)`, para fonte ABSOLUTA, os dois lados são levados a FÍSICO (`cd … && pwd -P`) ANTES do relpath; fonte relativa/`~` fica verbatim (um `cd` a resolveria contra o diretório errado); lado inexistente ⇒ fonte VERBATIM (absoluta, sempre correta em casa). `cd`/`pwd` são read-only para o censo (0 sítios novos). Teste **R15** (symlink que muda profundidade ⇒ o render RESOLVE do diretório físico; `../ceo` medido) — controle positivo RED na árvore sem cura e na lógica lexical. |
| 2 | **P1** | O e2e novo não é referenciado por nenhum workflow/runner; `smoke-install.yml:30-34` declara «unwired = no test». | **REAL** (era a OQ-5; o r1 tinha deferido como P2 — o codex escalou para P1 citando a regra do próprio repo). | **CURADO (r5), com decisão de desenho registrada:** step novo em `.github/workflows/ownership-nightly.yml` logo após o INV-4 (o irmão da mesma classe de custo — installs reais + upgrades + `git archive`; o workflow já busca a tag legada que o P3 precisa; `timeout-minutes: 150` com margem) e a linha nos DOIS `paths:` filters de `smoke-install.yml` (espelhando o INV-4). YAML validado com PyYAML. **Dois canônicos a mais** no escopo da cerimônia (`.github/workflows/*.yml`, oráculo 1); a promoção a per-PR fica como residual da OQ-5 (medir o p95 no CI primeiro). |
| 3 | P2 | `PREV_TAG` = tag não-rc mais nova: depois da release da W1 selecionaria uma release PORTÁTIL e P3a/P3b falhariam pela razão errada. | **REAL.** | **CURADO (r5):** derivação por CONTEÚDO — a tag não-rc mais nova cujo `scripts/_framework_manifest_set.sh` NÃO contém `_render_protocol_pointer_portable` (loop sobre `git tag --sort=-v:refname`); nenhuma ⇒ `exit 2`. Verificado que a `v1.2.0` REAL (a única tag que o nightly busca) também produz corpo aceito byte-exato pelo reconhecedor (sonda: install `v1.2.0` ⇒ «RECOGNIZED as legacy»). |

## O que muda no r5 (todo via `apply-w1-edits.py`, sombra re-derivada do zero)

- `scripts/_framework_manifest_set.sh`: normalização física no ramo `*)`; cabeçalho.
- `scripts/tests/test-protocol-pointer-render.sh`: **R15** (base `pwd -P` + symlink de profundidade).
- `scripts/tests/test-protocol-pointer-portable.sh`: `PREV_TAG` por conteúdo.
- `.github/workflows/ownership-nightly.yml`: step «Protocol pointer portable e2e (PLAN-183 W1)» após o INV-4 (nome do INV-4 atualizado para «5 legs»).
- `.github/workflows/smoke-install.yml`: `- "scripts/tests/test-protocol-pointer-portable.sh"` nos dois filtros (2 ocorrências, contadas).
- Baseline do censo re-gerado pelo pós-passo (delta por conteúdo idêntico ao r4: `cd`/`pwd` são read-only).
