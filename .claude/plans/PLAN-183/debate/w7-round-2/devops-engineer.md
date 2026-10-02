---
round: 2
archetype: DevOps Engineer
skill: devops-ci-cd
agent_persona: "DevOps Engineer (Principal) — entrega install/upgrade, e2e longos, orçamento de CI"
served_model_id: claude-opus-5-5
generated_at: 2026-10-02T09:50:00Z
plan: PLAN-183
plan_commit: e8ac8aba
wave_in_scope: [W7b]
wave_verdict:
  W7b: PROCEED
p0_found: false
inputs:
  - .claude/plans/PLAN-183/debate/w7-round-2/proposal.md
  - .claude/plans/PLAN-183/debate/w7-round-1/consensus.md
  - .claude/plans/PLAN-183-adopter-fitness.md (W7b, :2500-2565; HEAD e8ac8aba)
---

> **Legenda.** [disco] = conferido por mim no HEAD `e8ac8aba`. [P:n] = PLAN-183, linha n. [inferência] =
> dedução minha, não executada. Estimativas em tokens e sessões (ADR-081). Nenhum conteúdo lido trouxe
> instrução dirigida a mim. Mudo duas posições da rodada 1 (R2-2 e R2-3), com a razão abaixo.

## Verdict

**ACCEPT** — W7b: **PROCEED** (`design-coherent`), sem P0.
**R2-1 (a)**, predicado em `check-rule-invariants.py`, no manifesto; **R2-2**, FAIL nomeado, nunca pula, sem
literal; **R2-3 (b)**, raiz explícita no `.py`, passada pelo chamador; **R2-4**, 3 pernas novas e 1 asserção,
com o esperado escrito. ~7 paths no total.

Uma afirmação do plano é falsa (`:2525-2526`). Ela sustenta só a opção (b) da R2-1, que não escolho, então
não impede o PROCEED.

## Summary (≤ 3 bullets)

- **Fecha a W7b:** um predicado com um único dono; falha sempre ruidosa; cura do cwd no próprio script (2.ª
  ocorrência da classe); matriz do e2e que diz o que sai PURGED e o que fica KEPT.
- **Forte:** o predicado já existe e é estável (`check-rule-invariants.py:163,212-217`, 1 commit no histórico
  inteiro do arquivo [disco]). O purge é por hash e faz backup (`upgrade.sh:4186-4230`).
- **Fraco:** um CLI que responda «não é o repo-fonte» com rc 1 colide com o rc 1 de exceção Python. Um
  módulo novo em `_lib/` muda uma contagem exata que o plano não conta.

## Risks

- R-DO-R2-1 HIGH — W7b — um CLI que responda «não é o repo-fonte» com rc 1 colide com o rc 1 de erro de import ou de exceção Python (sondado [disco]; argparse sai com rc 2): o erro vira «adopter» e o bloco PLAN-119 é PULADO em silêncio no repo-fonte. → MF-DEVOPS-R2-2.
- R-DO-R2-2 MEDIUM — W7b — um módulo NOVO em `_lib/` muda a contagem exata de `_lib`, de 72 para 73 (`verify-counts.sh:202`, regra «lib» exact `:674-678`), citada em `CLAUDE.md:53`, `CHANGELOG.md:12`, `INSTALL.md:213,581` e `docs/ARCHITECTURE.md:47`; o `INSTALL.md` está fora da 4.ª exceção e entra na fila W6 (PLAN-194) → W8. → R2-1 (a).
- R-DO-R2-3 MEDIUM — W7b — curar o cwd só no chamador deixa o script dependente do cwd para qualquer outro chamador, e o `.sh` não vê quantos arquivos o `.py` varreu (`check-test-audit-isolation.py:599-612`); o verde no vácuo já aconteceu uma vez (`test_check_test_audit_isolation.py:303-306`). → MF-DEVOPS-R2-4.
- R-DO-R2-4 MEDIUM — W7b — o bloco de invariantes é armado por `[ -x … ]` (`validate-governance.sh:997`): sem o bit ou sem o arquivo, ele some sem WARN, e pela (a) esse mesmo arquivo passa a hospedar o predicado. → MF-DEVOPS-R2-3.
- R-DO-R2-5 MEDIUM — W7b — sem o esperado escrito, o Check «o purge também sai verde» [P:2551-2552] passa com as fixtures antigas ficando para sempre no alvo: depois da W7a a fonte não tem mais o relpath, e a autorização só pode vir do digest do baseline (`upgrade.sh:4194-4207`). → MF-DEVOPS-R2-6.
- R-DO-R2-6 LOW — W7b/W8 — orçamento do job `smoke`: o máximo medido é 92m32s (`smoke-install.yml:302-314`); com +8–12 min das pernas novas [inferência], fica perto dos 120 min da C38, e as pernas da W8 vêm depois. → MF-DEVOPS-R2-7.

## Must-fix (blocking)

Nenhuma condição bloqueia o PROCEED. São condições de execução, cada uma com o seu controle vermelho.

1. **MF-DEVOPS-R2-1 [R2-1]** — O `check-rule-invariants.py` hospeda o predicado e entra no manifesto
   ADR-192 no MESMO pacote. Ganha um modo que só responde se o diretório é o repo-fonte, com
   `_is_framework_repo` (`:212-217`) como a ÚNICA implementação. A linha dele na tabela [P:2507] deixa de
   ser condicional.
2. **MF-DEVOPS-R2-2 [R2-2]** — Contrato do CLI: resposta no STDOUT, num token exato (`framework` ou
   `adopter`), sempre com rc 0, como no oráculo `--is-canonical`. Qualquer outra combinação de rc e stdout dá
   1 ERROR nomeado com a classe, no repo-fonte e no adopter. Nenhum literal do marcador no bash: o fallback
   que defendi na rodada 1 sai, porque re-deriva o marcador (choca com a C12) e é paridade fail-open.
3. **MF-DEVOPS-R2-3 [R2-2, L9]** — Os dois blocos (PLAN-119 e invariantes, `:997`) chamam por
   `python3 "<caminho>"`, o que elimina a classe «sem bit de execução». Script ausente dá ERROR nomeado: ele é
   entregue (`_framework_manifest_set.sh:180`), então a ausência é instalação quebrada. Controles em cópia
   descartável: com `chmod -x` o bloco continua armando; com o arquivo removido, sai 1 ERROR nomeado.
4. **MF-DEVOPS-R2-4 [R2-3]** — O `check-test-audit-isolation.py` ganha `--repo-root`. Sem o argumento, o
   padrão é a raiz derivada do próprio arquivo, e contra ela se resolvem as TRÊS leituras de cwd: o
   `pytest.ini` (`:600`), as raízes relativas (`:575/:591`, resolvidas em `:603`) e o WS-D2 (`:610`). Zero
   raízes existentes ou zero `test_*.py` varridos dão FAIL. O `.sh` passa `--repo-root "$REPO_ROOT"`, e o
   script ausente no repo-fonte passa de WARN a ERROR (`:1201-1203`). Controles: os dois da C11, rodados de
   OUTRO cwd, mais um de vácuo.
5. **MF-DEVOPS-R2-5 [C12, L8]** — O teste-censo mora no arquivo NOVO `test_adopter_dogfood_boundary.py`,
   junto dos testes do CLI e do vácuo: nenhum path a mais.
6. **MF-DEVOPS-R2-6 [R2-4]** — Matriz com o esperado escrito (detalhe na R2-4).
7. **MF-DEVOPS-R2-7 [C38]** — As pernas B e C reaproveitam o alvo A (`cp -a`), sem reinstalar. O tempo é
   medido na abertura. Se o p95 previsto do job passar de 120 min, o e2e histórico vai a um job próprio já
   na W7b. O registro diz quanto sobra para a W8.
8. **MF-DEVOPS-R2-8 [texto, L5]** — Em `PLAN-183:2546-2547`, sai «o WS-C recebe as raízes a partir do
   `REPO_ROOT`»; entra «o checker resolve as três leituras pela raiz explícita». Na mesma edição, corrige a
   `:2525-2526` (abaixo).

## Nice-to-have (advisory)

1. Os controles vermelhos rodam UMA vez, no material da cerimônia, contra o pai do commit de cada cura; a CI
   permanente roda só as pernas verdes.
2. A perna do purge registra no material o par PURGED/KEPT medido no ensaio, para o rail comparar com a CI.

## Unseen by the original plan

1. O rc 1 do CLI colide com o rc 1 de exceção Python (R-DO-R2-1).
2. Na opção (b), a contagem exata de `_lib` arrasta o `INSTALL.md` (R-DO-R2-2).
3. Na `v1.1.0`, o manifesto do baseline andava pela árvore do ALVO sem exclusão (`_framework_manifest_files`
   da tag) [disco]. Quem parou na `v1.1.0` tem digests de `.claude/hooks/tests/**`, e o purge os autoriza;
   quem subiu para a `v1.2.0` ou depois não tem [o efeito sobre adopters reais é inferência].

## What I would NOT change

- O marcador ADR-001, nunca `conftest.py`; o uso MONÓTONO no ADR (C13).
- A tag DERIVADA, no molde do H.14 (`test-upgrade-historical-adopter.sh:895-923`).
- O purge só por hash, com backup e KEPT por padrão (`upgrade.sh:4194-4230`): a W7b o exercita, não o muda.
- O ADR novo (C14), com `check-claude-md-claims.py` na bateria; o script existe [disco].

## Respostas R2-1 a R2-4

**R2-1 — (a), com o manifesto ADR-192 no mesmo pacote.**
- O VETO condicional (MF-C-5) aceita essa forma, e o código já mora lá: a C12 sai sem mover nada.
- Conta de paths: a (a) com a R2-3 (b) dá 7; a (b) com a R2-3 (b) dá 8, mais o `INSTALL.md` (R-DO-R2-2).
  Estoura o teto e colide com a fila do `INSTALL.md`.
- O arquivo é ele mesmo um gate fail-closed do validador e mudou 1 vez desde a `v1.0.0` [disco]: entrar no
  manifesto custa quase zero de cerimônia.
- Fica com a MESMA proteção do único chamador bash, o `validate-governance.sh` (oráculo 0, membro do
  manifesto; `shasum -c` em `smoke-install.yml:355-362`).

**R2-2 — FAIL nomeado (1 ERROR); nunca pula; sem literal.**
- Script ausente, erro de import ou exceção, rc ≠ 0, stdout fora de {`framework`, `adopter`}: todos dão
  ERROR nomeado, no repo-fonte e no adopter.
- «Sem bit de execução» deixa de existir como classe.
- ARMAR por erro foi descartado: no adopter daria ≥ 3 FAIL indiretos (`validate-governance.sh:1169-1178`;
  `test_isolation.py` não é entregue, `_framework_manifest_set.sh:101`). Nenhuma das duas formas relaxa
  guarda (C13).

**R2-3 — (b), com o chamador passando `--repo-root`. Mudo da (c) da rodada 1:** é a 2.ª ocorrência do
«verde no vácuo», e `CLAUDE.md` §4 pede cura estrutural; a (c) não implementa «zero arquivo ⇒ FAIL» (o
`.sh` não vê o que o `.py` varreu) e cura um chamador só. O FAIL no vácuo fica ADOTADO; sobra 1 path de folga.

**R2-4 — 3 pernas novas e 1 asserção; tags DERIVADAS.**
- **A — classificada** (todo adopter atual). Install na release mais nova sem `_lib/harness_replay/` (hoje
  `v1.4.2`) → upgrade ao HEAD. Esperado: `check_harness_config.py --replay` rc 0, zero RED. Vermelho: fonte
  = pai da W7a ⇒ `FAIL: 3 RED`.
- **B — resíduo herdado** (quem fez upgrade pela `v1.1.0`, e fixtures feitas à mão). Cópia do alvo A com
  `git archive <tag> -- .claude/hooks/tests` plantado. A tag é derivada: a release mais nova que NÃO contém
  `e718cd89` e traz as fixtures (hoje `v1.1.0`, 549 arquivos [P:2553]). Uma fixture é editada à mão;
  upgrade SEM purge. Esperado: resíduo `cmp`-intacto; gate rc 0; validador completo do alvo com zero linhas
  PLAN-119 e a linha de resumo (C13). Vermelho: fonte = pai da W7b ⇒ o PLAN-119 arma e dá FAIL.
- **C — purge** (o caminho do 42ledger-core). O mesmo plantio, com `--purge-misinstalled`. Pela regra de
  `upgrade.sh:4194-4207`, com o baseline da tag da perna A (sem digests de árvore excluída):
  - PURGED, com backup: exatamente o que tem sha256 igual ao do MESMO relpath no HEAD;
  - KEPT nomeado: o resto, inclusive as 3 fixtures antigas (a W7a apagou o relpath) e o arquivo editado;
  - gate rc 0; asserção conjunto contra conjunto, derivada no teste; o KEPT fica declarado no ADR, pela
    forma.
- **D — sem baseline.** A asserção do gate rc 0 entra numa perna existente sem
  `.claude/.install-manifest.sha256`, se houver [não verificado]; senão, uma 4.ª perna. O ramo legado
  (`upgrade.sh:1940-1945`) entrega a pasta.
- **Orçamento:** ~2 min por install (34 min / 17 installs) mais o validador no alvo B dão +8–12 min
  [inferência]. Sobre o máximo de 92m32s do job, ~105 min, abaixo de 120: cabe, com folga curta, medido na
  abertura (MF-DEVOPS-R2-7).

## C11–C14, ajuste 1 e lacunas

- **C11** confirmo, com a 3.ª leitura de cwd (`:603`). **C12** confirmo, sob a (a). **C13** confirmo, mais o
  L9. **C14** confirmo.
- **Ajuste 1** confirmo: `PLAN-183:2130` diz agora «nenhuma INSTALAÇÃO nova entregou… até `e718cd89`»
  [disco].
- **L1, L3, L4:** procedem, fora da minha lente; para a L4, os riscos vão em linhas `- `.
- **L2:** procede; comparar o recorte da W7b com o da W7b.
- **L5:** procede (MF-DEVOPS-R2-8).
- **L6:** procede. O marcador plantado em tmp é perna EXTRA permitida, que prova o chaveamento; nunca o
  controle da C13.
- **L7:** procede e se dissolve: com a (a) e sem literal, a C12 não custa path nem isenção.
- **L8:** procede.
  - «Re-derivar» = código executável (`.py`, `.sh`, `run:` de workflow) que testa a existência do caminho
    do marcador para decidir identidade.
  - Ficam fora: os docs (`.claude/adr/README.md:254`); os testes que PLANTAM o marcador em tmp
    (`test_check_rule_invariants.py:72,145,173`, `test_bash_canonical_interceptor.py:47-50`), isentos por
    comentário marcado no molde `# rp-allow:` (`SessionEnd.py:92`); e a implementação única.
- **L9:** procede (MF-DEVOPS-R2-3).
- **L10:** procede, respondida na perna C.

## P0 e afirmações falsas (os únicos motivos para não dar PROCEED)

- **P0:** nenhum.
- **Afirmação falsa:** `PLAN-183:2525-2526` diz que o módulo novo em `_lib/` «somaria 1 path».
  - Pela C12, soma 2.
  - A contagem exata de `_lib` ainda arrasta o `INSTALL.md` (R-DO-R2-2).
  - Sustenta só a opção (b): com a (a) eleita, não sustenta decisão e não impede o PROCEED.

**Esforço (ADR-081, estimado):** ~180–280k tokens, 1–2 sessões, mais o rail com parada pré-registrada. O e2e
roda destacado, com timeout explícito de até 2 h e piso de `df` (regras comuns 9 e 12).
