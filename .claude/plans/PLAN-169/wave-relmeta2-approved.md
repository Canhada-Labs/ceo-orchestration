# wave-relmeta2 — sentinel de aprovação (DRAFT: o SIGN preenche Data / Anchor-SHA / Approved-By e assina)

> Caminho casa `PLAN-*/wave-*-approved.md` (união fechada de padrões em
> `check_canonical_edit.py`). O binding é o `Patch-sha256` — land por PATCH.
> O bloco `Scope:` é **DERIVADO** por
> `s349-ceremony-relmeta2/finalize-relmeta2.sh` a partir de
> `git apply --numstat`, nunca escrito à mão, e o `OWNER-RC1-META2-SIGN.sh`
> **regenera e compara byte a byte antes de pedir a assinatura** (a classe
> CM-10 do corpus S348: hoje só o LAND confere, e isso é depois de o Owner
> já ter assinado). O `Anchor-SHA` é preenchido no momento da assinatura; o
> `OWNER-RC1-META2-LAND.sh` aborta se o HEAD tiver andado. Reescrever um byte
> deste arquivo depois de assinar invalida o `.asc`.

Plans: PLAN-169
Wave: wave-relmeta2 (PLAN-169 — destrava o corte da **v1.4.0-rc.1**)
Patch: .claude/plans/PLAN-169/s349-ceremony-relmeta2/RELMETA2.patch
Patch-sha256: 804621be8142041af3c5612f11d1c7f4e5ade246353f332cf04deb6605264be1
Patch-base: 22755b12b2efeb9a4404aa1dbd821763b9f9f444
Anchor-SHA: 22755b12b2efeb9a4404aa1dbd821763b9f9f444
Data: 2026-09-08
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74

## Por que esta wave existe

O land da wave-relmeta (`511fdc2`) pos `TARGET_BASE="1.4.0"` no driver — o que
e correto — e com isso abriu uma janela **estruturalmente vermelha**: a suite
`test_release_bump_sites.py` monta um repositorio sintetico pinado em 1.3.0 e
copia o `release.sh` VIVO para dentro dele. Fixture e driver passaram a
discordar, e nove testes reprovaram no Validate. Um decimo reprovou por um
literal de versao que sobrou num comentario.

Medido em tres arvores: o pai da wave da **153 passed / 0 failed**; o
`511fdc2` da **10 failed**; e — este e o ponto — aplicar so o bump conserta
**zero** testes, porque a suite nunca le o `VERSION` vivo.

Esta cerimonia fecha a janela por **fix-forward, num patch so**, porque
metade da cura nao faz sentido sem a outra metade.

## O que entra

1. **`.claude/scripts/local/release.sh`** — o literal de versao sai do
   comentario do bloco `PER-RELEASE`, e o aplicador RE-RODA o predicado do
   proprio teste sobre o resultado.
2. **Os sitios de versao**, escritos pelo ESCRITOR UNICO
   (`_release_bump_sites.py bump --restamp`) e os manifestos de plugin pelo
   GERADOR. `VERSION` recebe o semver **nu** (`1.4.0`), nao `1.4.0-rc.1`: e o
   contrato do driver, e a fase `tag` compara `VERSION` com `TARGET_BASE`.
3. **`.claude/governance/gate-scripts-manifest.txt`** (CANONICO) — re-pin do
   sha de `release.sh` depois da edicao 1.
4. **`.claude/scripts/tests/test_release_bump_sites.py`** — o mundo sintetico
   passa a DERIVAR a sua escada de versoes do `TARGET_BASE` do driver
   (`SYNTH_BASE`/`PREV`/`PREV2`/`NEXT`, janelas de suporte e tags). Um teste
   fica DELIBERADAMENTE pinado e re-pinado no trem 1.4.0: o da anotacao da
   tag, porque derivar o escopo do proprio driver o tornaria tautologico.
5. **`SUPPORT.md`** e **`.claude/adr/README.md`** — relidos e re-carimbados,
   sem o que o gate de frescor mantem o `bump` fora do caminho no-op.

## O que esta cerimonia NAO e

Nao e uma wave de produto: e **cerimonia de release**. O teto de paths do
modelo v2 nao se aplica — os sitios de versao sao quinze arquivos de uma
linha cada, escritos por um modulo, e separa-los criaria exatamente a janela
vermelha que esta cerimonia fecha.

Nao toca no `CHANGELOG.md`: a secao `[1.4.0]` veio do pacote de docs e o
aplicador apenas a confere.

## Evidencia

- suite do driver na arvore patchada: **153 passed, 0 failed**; nas duas
  invocacoes do preflight: **217 passed** (paralela) e **3 passed** (serial).
- a MESMA suite sobre um driver em 1.3.0 (`875ac92`): 152 passed, e a unica
  falha e o teste deliberadamente pinado — prova de que ela DERIVA em vez de
  ter ganhado um pin novo, e de que o pinado e genuinamente pinado.
- defeito plantado no escritor de sitios: **6 failed** — prova de que a suite
  nao virou vacua.

## Recuperacao

Se o LAND abortar depois de aplicar o patch, ele reverte os alvos pelo
`EXPECTED-BASELINE.txt` e sai nao-zero com o motivo nomeado. Depois do commit
local, nada foi empurrado.

Scope:
  - .claude-plugin/marketplace.json
  - .claude-plugin/plugin.json
  - .claude/.framework-version
  - .claude/adr/README.md
  - .claude/governance/gate-scripts-manifest.txt
  - .claude/scripts/local/release.sh
  - .claude/scripts/tests/test_release_bump_sites.py
  - INSTALL.md
  - SBOM.md
  - SECURITY.md
  - VERSION
  - VERSIONING.md
  - docs/ARCHITECTURE.md
  - npm/README.md
  - npm/package.json
  - pyproject.toml
