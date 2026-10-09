# rail-round-1 — W4 do PLAN-194 (rail oficial, rodada 1 de no máximo 3)

Rail-Round: 1
Rail-Subject: .claude/plans/PLAN-194/w4/w4.patch
Rail-Subject-sha256: ae76d066e9eaf00f9bfaa42c9f64b616f3c25f7c138f6145b1bf6d7afaa26c0c
Rail-Subject-patch-id: e869026b17c324a8c411c93ac7cff901ae93b992
Rail-Sentinel-sha256: 6538e1f4bdc3e7d6706727591c8c1cb30e719885611d5d1225af02e218919c64
Rail-Control: classe Plan194W4PublishToolchainTest (dentro do patch): 17 failed contra os canônicos de a953a08204d4, 17 passed com o patch (w4/red-control.txt)
Rail-Reviewer: codex-cli 0.160.0 (pin assinado 4a1eec73), exec --sandbox read-only, modelo do config do usuário (gpt-6-astra, model_reasoning_effort xhigh), config sha256 9af51fe781bf86c1…, memories e chronicle desligados; refutadores Claude r-w4-a (DevOps) e r-w4-b (Security), modelo fable
Rail-Prompt: fora do repositório (prompt da rodada na sessão S363, 2026-10-09; critérios resumidos na triagem)
Rail-Reviewer-Verdict: GO
Rail-Verdict: APPROVE
Rail-Findings: P0=0 P1=0 P2=0

Sujeito da rodada: `git diff a953a08204d4..4672153e8ed9` na sombra da W4 (2 commits: dbf2d7ef, publish em Node 24
com npm 11.20.0 exato e o job da rc; 4672153e, curas dos 3 P2 da pré-revisão), 5 caminhos — 2 canônicos
(`.github/workflows/npm-publish.yml`, `.claude/governance/npm-trusted-publisher.txt`) e 3 livres
(`.claude/scripts/tests/test_release_workflow_asserts.py`, `docs/actions-versions.md`, `npm/INTEGRITY.md`).
O `w4.patch` é `git diff --full-index a953a08204d4 4672153e8ed9` gerado na mesma sombra; o patch-id dele
(`git patch-id --stable`) é o da linha Rail-Subject-patch-id, o mesmo do sujeito revisado.

## Saída do revisor

```text
NENHUM ACHADO

VERDICT: GO
```

## Triagem

- Codex 0.160.0 (read-only, preflight 2026-10-09T00:51:02Z, rc 0): «NENHUM ACHADO», GO (saída final
  acima, verbatim). No log da rodada o revisor rodou o controle (as verificações do workflow falham na
  base e passam no HEAD), mutantes de Node/npm divergentes e de pack removido (rejeitados), a checagem
  bash do passo do npm com comandos falsos (Node 20 ou npm diferente do pinado ⇒ exit 1) e o rollback
  dormente (preserva o job da rc e só acrescenta o token ao passo de publish).
- Refutador Claude r-w4-a (DevOps; lente correção do workflow e afirmações): GO, só P3 — P3-1:
  `docs/BRANCH-PROTECTION.md:447-457` (livre) repete o bump para Node 24 que a W4 corrigiu em
  `docs/actions-versions.md`; P3-2: quatro mutantes verdes no teste novo (remoção das conferências de
  versão do passo do npm; `id-token: write` apagado do workflow, pré-existente; `workflow_dispatch` no
  `on:`, pré-existente; `npm pack` real no passo «Pack dry-run»). Reproduziu: 84 passed; controle 17
  failed / 0 passed na base; actionlint limpo; rollback aplica; 190 passed nos 3 oráculos vizinhos;
  identidade dos 10 passos partilhados por PyYAML e por bytes.
- Refutador Claude r-w4-b (Security; lente supply chain e publicação): GO, só P3 — P3-1: a lane de
  texto não exige o bloco `permissions:` da rc (só a lane YAML o pega); P3-2: o teste antigo da
  exclusão de rc casa o texto também no comentário do cabeçalho (pré-existente); P3-3: nenhuma lane pina
  o `on:` (pré-existente); P3-4: npm por versão exata sem hash no repositório (endurecimento opcional).
  Reproduziu: 84 passed; controle 17 failed / 67 deselected na base; actionlint 1.7.12 rc 0; rollback
  rc 0 na base e com o patch; 21 mutantes.
- Disposição: nenhum P0/P1/P2 ⇒ APPROVE. Os P3 das duas lanes Claude e o `SPEC/v1/npm-shim.md:61`
  (desatualizado por contrato) ficam DECLARADOS no texto assinável (seção «Residual declarado») e viram
  pacote LIVRE depois do LAND.
- O que a rodada 1 NÃO revisou: o texto do sentinel `w4-approved.md`, o `OWNER-W4-SIGN.sh` e o harness
  `test-ceremony-w4.sh`, escritos depois dela (materiais da cerimônia, S363). A linha
  Rail-Sentinel-sha256 prende este registro ao texto commitado — o SIGN recusa se ele mudar —, mas não
  afirma que o rail o revisou.

## Saídas das lanes Claude (verbatim; o SIGN não lê esta seção)

### r-w4-a

```text
RAIL r1 — PLAN-194 W4 — refutador r-w4-a (lente correção do workflow e afirmações; DevOps Engineer; model fable). Recebido 2026-10-09 ~01:10Z (3 mensagens; a 1.ª truncada pelo transporte, completada a pedido sem refazer verificação). Sujeito: a953a08204d4..4672153e8ed9 na sombra shadows/w4/wt (porcelain 0 antes e depois). Reproduções em cópia descartável (git archive → work/r-w4-a), apagada.

REPRODUZIDO:
- pytest test_release_workflow_asserts.py na cópia HEAD: 84 passed (classe W4: 17 passed).
- Controle vermelho: teste HEAD sobre a árvore base a953a082 (Node "20", npm@^11.5.1): 17 failed / 0 passed na classe Plan194W4PublishToolchainTest.
- actionlint npm-publish.yml: limpo.
- git apply --check do rollback-oidc-to-token.patch: OK; aplicado numa cópia: 84 passed + actionlint limpo.
- Oráculos vizinhos que leem npm-publish.yml (test_install_sh_self_sha.py, test_await_release_gate.py, test_release_bump_sites.py): 190 passed.
- Identidade dos 10 passos partilhados, independente do teste (PyYAML dict-equal + bytes crus): 10/10.
- Gatilhos: on: {push: {tags: [v*]}} só; publish.if = "!contains(github.ref, '-rc.')", rc.if = "contains(github.ref, '-rc.')"; rc.permissions = {contents: read}, sem needs, sem environment, timeout 8.
- Texto do job rc: secrets, id-token, environment, npm publish, NODE_AUTH_TOKEN ausentes.
- gh api: setup-node v6.4.0 → commit 48b55a01; os 4 SHAs da tabela = node24; setup-node token default = github.token.
- git log -S'node-version: "24"' vazio; "20" desde 9777a8de até dbf2d7ef; 39370e39 nunca existiu em .github/workflows/.
- Log do run 36719886734: Node 20.20.2, npm@^11.5.1 → OK: npm 11.20.0.
- docs.npmjs.com/trusted-publishers lido hoje: textos de npm-trusted-publisher.txt:34-46 e do comentário :7-8 fiéis.
- git ls-remote anônimo de refs/tags/v1.4.2: resolve (b55084da) — persist-credentials:false não quebra.
- release.yml:87-102 usa o mesmo strip ${EXPECTED%-rc.[0-9]*}.

MUTANTES (suíte inteira de 84): VERMELHOS — M2 registry-url só na cópia rc; M3 if do publish afrouxado; M4 environment no rc; M5 env flow-style redefinindo PUBLISH_*; M7 if … || true; M8 node-version "24" literal na cópia rc; M9 range no install da cópia rc; M12 permissions do rc removido; M14 fetch-depth só na cópia rc; M16 PUBLISH_NODE_MAJOR "22". VERDES — M10 NODE_AUTH_TOKEN no Publish (forma do rollback; esperado); M11 npm pack real no passo «Pack dry-run» (P3-2 iv); M13 timeout 60 no rc (fora do contrato); M15 id-token apagado do topo (P3-2 ii); M1 remoção dos asserts de versão (P3-2 i); M6 workflow_dispatch no on: (P3-2 iii).

ACHADOS:
P3-1 — docs/BRANCH-PROTECTION.md:453 (livre, oráculo 0) carrega a afirmação falsa que a W4 corrigiu em docs/actions-versions.md:44 («npm-publish.yml bumped to node-version: 24» em 2026-04-13); vizinhos :447-449 (upload-artifact node20 — o SHA pinado declara node24) e :457 (setup-node v4→v5 deferido — moot). Cura livre no mesmo push ou logo depois: :453 → ❌ com a nota de actions-versions.md:44-46; :457 riscado; :447-449 corrigido.
P3-2 — test_release_workflow_asserts.py (livre): quatro mutantes VERDES: (i) M1 remover os asserts case "${NODE_V}" / NPM_V != PUBLISH_NPM_VERSION (:300-310, :624-634) — o comentário :286-289 promete «asserts BOTH versions»; (ii) M15 apagar id-token: write de :99 (o GA morreria ENEEDAUTH sem teste vermelho; pré-existente); (iii) M6 workflow_dispatch no on: (:20 diz «no workflow_dispatch by design»; pré-existente); (iv) M11 npm pack real no passo «Pack dry-run». Cura: data["permissions"] == {"contents": "read", "id-token": "write"} e "permissions" not in pub; data[True] == {"push": {"tags": ["v*"]}}; o run do passo «Pin npm CLI…» contém `"v${PUBLISH_NODE_MAJOR}".*)` e `!= "${PUBLISH_NPM_VERSION}"`; opcional pinar o corpo do passo «Pack dry-run».

OBSERVAÇÕES (sem severidade): pin de Node é da LINHA 24 (build exato do tool cache/manifesto no dia; D-12; dito em :103-105); contains() do GitHub é case-insensitive (-RC. cai no job rc, onde o strip -rc.[0-9]* é case-sensitive e falha fechado, igual a release.yml) — sem caminho de publish; o comentário :104-105 omite o fallback a nodejs.org do setup-node (incompleto, não falso).

Achado acima de P3: NÃO (só P3-1 doc livre e P3-2 lacunas do teste livre; nenhum toca os dois canônicos).

VERDICT: GO
```

### r-w4-b

```text
RAIL r1 — PLAN-194 W4 — refutador r-w4-b (lente supply chain e publicação; Security Engineer; model fable). Recebido 2026-10-09 ~01:20Z. Sujeito: a953a082..4672153e na sombra shadows/w4/wt.

CHECKS DO CONTRATO (todos verdes, reproduzidos):
- pytest test_release_workflow_asserts.py na sombra: 84 passed (0.81 s).
- actionlint 1.7.12 sobre npm-publish.yml: rc=0.
- git apply --check do rollback dormente: rc=0 no vivo (a953a082) E na árvore W4 (hunk aplica com offset 254 → linha 542). Aplicado NA CÓPIA sobre a árvore W4: 84 passed + actionlint rc=0.
- Controle vermelho→verde: classe Plan194W4PublishToolchainTest contra o workflow de a953a082 = 17 failed / 67 deselected; 4672153e = 84 passed.
- 21 mutantes (M0–M21): todos os que tocam credencial/publish/toolchain pegos por pelo menos uma lane. Exceções = P3 abaixo.

AFIRMAÇÕES EXTERNAS VERIFICADAS: 48b55a01 = setup-node v6.4.0 (node24); de0fac2e = checkout v6.0.2; a309ff8b = setup-python v6.2.0; 043fb46d = upload-artifact v7.0.1 — todos node24. docs.npmjs.com/trusted-publishers lido hoje (npm ≥ 11.5.1, Node ≥ 22.14.0; registros antes de 2026-09-03 exigem selecionar ação permitida — o registro deste repo é de 2026-07-13). Run 36719886734: node v20.20.2, npm 11.20.0. ls-remote anônimo da tag v1.4.2 rc=0. Gatilho só `push: tags: v*`; rc-toolchain-proof só contents:read.

ACHADOS (nenhum P0/P1/P2):
P3-1 — test_release_workflow_asserts.py:1585-1600 (_w4_text_offenders, lane de texto) não exige o bloco permissions: da rc; mutantes M1/M3 só pegos pela lane YAML (skipTest sem PyYAML; CI instala PyYAML). Docstring :1551 sobreclama. Cura livre: exigir "\n    permissions:\n      contents: read\n" in rc e rc.count("permissions:") == 1, controle positivo M1.
P3-2 — pré-existente: test_rc_exclusion_present (:314-319) e _precedes_publish_command (:321-328) casam `!contains(github.ref, '-rc.')` no COMENTÁRIO de cabeçalho (npm-publish.yml:32). Cura: ancorar no `if:` dentro de _w4_job_text(source, "publish").
P3-3 — pré-existente: nenhuma lane pina a superfície `on:` (mutante workflow_dispatch passa; cabeçalho :20 diz «no workflow_dispatch by design»). Cura: asserção textual do bloco on:.
P3-4 — endurecimento opcional: npm por versão exata sem hash no repo (:295, :622); cura opcional PUBLISH_NPM_SHA256 + npm pack + sha256sum -c.

OBSERVAÇÕES: patch do Node 24 resolvido em execução (contrato honesto); SPEC/v1/npm-shim.md:61 fica desatualizado por contrato — o sentinel deve declarar o resíduo; oidc-failure-playbook.md:17 cosmético; tier-policy.yml/mutation-gate.yml ainda com actions Node 20 (fora do sujeito).

VERDICT: GO
```
