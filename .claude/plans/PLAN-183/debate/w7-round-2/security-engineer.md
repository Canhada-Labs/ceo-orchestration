---
round: 2
archetype: Security Engineer
skill: security-and-auth
agent_persona: Security Engineer (Principal, auth/crypto VETO holder — ADR-052; tamper-evidence, fail-closed gates)
generated_at: 2026-10-02T09:50:00Z
served_model_id: claude-opus-5-5
plan: PLAN-183
plan_commit: e8ac8aba
wave_in_scope: [W7b]
final_round: true
inputs:
  - .claude/plans/PLAN-183/debate/w7-round-2/proposal.md
  - .claude/plans/PLAN-183/debate/w7-round-1/consensus.md (C11–C14, MF-C-5)
  - .claude/plans/PLAN-183-adopter-fitness.md, seção W7b (:2500-2565, HEAD e8ac8aba)
wave_verdict:
  W7b: PROCEED
p0_found: false
false_claims_found: "nenhuma que sustente decisão; 2 textos defasados pela C11/C12 (:2525-2526 «somaria 1 path», :2546-2547 «o WS-C recebe as raízes») ⇒ ajustes T-1 e T-2"
choices:
  R2-1: "(b) módulo em .claude/hooks/_lib/ (oráculo 1), consumido pelo check-rule-invariants.py"
  R2-2: "FAIL nomeado, nunca pular; sem fallback literal; contrato rc 0 + token exato em stdout (crash do Python = rc 1 ⇒ um contrato {0,1} lê crash como «adopter»)"
  R2-3: "(b) raiz explícita no .py, as três leituras de cwd curadas, FAIL no vácuo"
  R2-4: "4 pernas de Critic-B; a (2) com os bytes da v1.1.0 por git archive (Critic-A); a (3) sob --purge-misinstalled, com o esperado KEPT/purgado declarado (Critic-C)"
veto:
  W7b: "RETIRADO para a combinação eleita (R2-1 b, ou a com manifesto se a abertura medir 9 paths; R2-2 FAIL nomeado). Volta a LEVANTADO no rail se o predicado sair de arquivo canônico e fora do manifesto ADR-192, OU se alguma classe de falha terminar em bloco pulado — em especial crash do interpretador lido como «não é repo-fonte»"
---

# PLAN-183, debate L3 w7-round-2 (final, só W7b): crítica do Security Engineer

> `[sonda]` = medido por mim, fora do repositório. Todo arquivo:linha abaixo foi lido no HEAD `e8ac8aba`; o marcado `[lido]` não foi executado.

## Verdict

**ACCEPT** (posição geral). **W7b: PROCEED** (`design-coherent`).

- Nenhum P0 e nenhuma afirmação falsa que sustente decisão.
- **VETO RETIRADO** para a combinação eleita. As condições MF-SEC-R2-1 a MF-SEC-R2-8 são de execução: reprovam o SIGN da W7b, não o debate.
- Escolhas: R2-1 = (b); R2-2 = FAIL nomeado com contrato por token; R2-3 = (b); R2-4 = 4 pernas. Paths: 8, no teto.

## Summary (≤ 3 bullets)

- **O que a rodada fecha:** onde mora o predicado que ARMA o PLAN-119, como ele falha, como o checker deixa o cwd, e quais populações de adopter o e2e prova.
- **Ponto forte:** C11–C14 estão certas; o ajuste 1 está aplicado com o texto correto (`PLAN-183:2130`, alinhado com `resposta-ao-campo-1.4.2.md:396-399`).
- **Ponto fraco:** um defeito que nenhuma opção nomeou. Um contrato de saída {0, 1} confunde «não é repo-fonte» com o rc 1 de qualquer crash do Python [sonda: `import` inexistente e `SystemExit('x')` saem com 1]. No repo-fonte isso DESARMA o gate em silêncio, exatamente o que o MF-C-5 proíbe.

## Risks

- R2-SEC1 [W7b] HIGH: com o contrato «rc 0 = repo-fonte, rc 1 = adopter», qualquer crash do interpretador (import, sintaxe, exceção; rc 1, sonda) faz o validador do repo-fonte pular o PLAN-119 sem linha nomeada; mitigação MF-SEC-R2-1 (token exato em stdout + rc 0, molde do oráculo `--is-canonical`, `check_canonical_edit.py:2747-2767`).
- R2-SEC2 [W7b] MEDIUM: um predicado que infira a raiz do PRÓPRIO caminho arma o PLAN-119 num adopter em modo link, porque `install_lib_selective` instala cada entrada de `_lib/` por `install_one` (`install.sh:1541`), que faz `ln -s` para a fonte (`:1354`) e `resolve()` cai no checkout do framework, onde o marcador existe [lido]; mitigação MF-SEC-R2-1.
- R2-SEC3 [W7b] MEDIUM: sob (a), a deriva de um membro do manifesto em `.claude/scripts/` só é vista no nightly e no release (`ownership-nightly.yml:62`, `release.yml:58`): o único `shasum -c` de PR (`smoke-install.yml:355-362`) dispara em `.claude/hooks/**` (`:120`), não em `.claude/scripts/**`, e o `validate.yml` não confere o manifesto (0 ocorrências).
- R2-SEC4 [W7b] MEDIUM: verde no vácuo é a 2.ª ocorrência (`test_check_test_audit_isolation.py:303-306`); a 1.ª cura foi no teste (`:311-317`), não no script; mitigação MF-SEC-R2-4.
- R2-SEC5 [W7b] LOW-MEDIUM: o bloco do `check-rule-invariants` some sem WARN se o script perder o bit de execução (`validate-governance.sh:997`, `[ -x ]`): uma guarda do repo-fonte desarmada (L9); mitigação MF-SEC-R2-5.
- R2-SEC6 [W7b] LOW: na população da `v1.1.0`, o purge só remove arquivo com sha igual ao da fonte ATUAL ou do baseline (`upgrade.sh:4194-4207`); os testes mudados desde então ficam KEPT e o WARN «forma dogfood sem marcador» (C13) vira ruído permanente; mitigação MF-SEC-R2-6.

## Must-fix (blocking)

Nenhum must-fix bloqueante de DESENHO. Condições de **execução**, conferidas no rail; reprovam o SIGN da W7b se não cumpridas.

1. **MF-SEC-R2-1 (R2-1, R2-2): o módulo do predicado.**
   - Stdlib-only, Python ≥ 3.9, sem importar outro módulo de `_lib/`.
   - A CLI exige `--repo <raiz>` explícito e nunca infere a raiz do próprio caminho nem do cwd (R2-SEC2). Molde: o `--repo "$REPO_ROOT"` que o validador já passa ao `check-rule-invariants` (`validate-governance.sh:1000`).
   - Contrato: rc 0 + UM token exato no stdout (`framework` | `adopter`). O bash aceita só rc 0 com o token no conjunto; qualquer outra saída é FAIL nomeado, 1 erro com a classe.
   - Invocação por `python3 <caminho>`.
   - Controle vermelho por classe, no repo-fonte e no alvo de adopter: módulo ausente, import quebrado plantado, rc ≠ 0, token fora do conjunto, linha extra.
2. **MF-SEC-R2-2 (C12).** O `check-rule-invariants.py` IMPORTA o predicado (molde de import de `_lib/` por script: `ceo-boot.py:176`); `:163` e `:212-217` deixam de re-derivar o marcador. Os testes dele seguem sem edição: plantam o ARQUIVO e não referenciam `_PRIMARY_MARKER` (`test_check_rule_invariants.py:72,145,173`).
3. **MF-SEC-R2-3 (C12, L8): escopo do teste-censo.**
   - RED: literal do nome do arquivo do ADR-001 em código executável não-teste (`.claude/hooks/**`, `.claude/scripts/**`, `scripts/**`), fora do módulo.
   - Não contam: o índice `.claude/adr/README.md:254`, testes que PLANTAM o marcador e a string de comando de `test_bash_canonical_interceptor.py:47-50`.
   - Sem fallback literal, nenhuma isenção `# rp-allow` é necessária.
4. **MF-SEC-R2-4 (R2-3): raiz explícita no `.py`.**
   - O `.py` recebe `--repo-root`, e o `.sh` passa `$REPO_ROOT`.
   - Na ausência da flag, a raiz vem do caminho do script, sem `resolve()`; o cwd nunca entra. Assim `test_check_test_audit_isolation.py:315` passa sem edição (conferir na abertura).
   - As TRÊS leituras usam a raiz: o ini (`:600`), as raízes relativas (`:575`, `:591`, resolvidas em `:603`) e o WS-D2 (`:610`).
   - Zero raiz existente OU zero `test_*.py` varrido ⇒ rc 1 com linha nomeada.
   - Com o predicado verdadeiro, checker ausente ⇒ FAIL (hoje WARN, `validate-governance.sh:1201-1203`).
   - Controles: os dois da C11 e um de vácuo, todos de OUTRO cwd, vermelhos antes e verdes depois.
5. **MF-SEC-R2-5 (L9).** Com o predicado verdadeiro, o bloco de `validate-governance.sh:997` roda por `python3`, e o script ausente dá FAIL nomeado. Nunca `[ -x ]` pulando em silêncio. O arquivo já está no pacote.
6. **MF-SEC-R2-6 (C13, L10).** No adopter, o WARN «forma dogfood sem marcador» é só WARN, nunca ERROR. O texto nomeia a causa (árvore de testes herdada) e a cura manual. As pernas (2) e (3) o declaram como saída ESPERADA.
7. **MF-SEC-R2-7 (R2-4).** Cada perna nomeia população, esperado e controle vermelho contra o HEAD pré-cura.
   - **(1)** `v1.4.2` → HEAD, ramo classificado.
     - População: os adopters atuais.
     - Esperado: gate do harness rc 0; nenhuma linha PLAN-119, com a linha de resumo final.
   - **(2)** `v1.4.2` + a árvore `.claude/hooks/tests` da `v1.1.0` por `git archive` (549 arquivos, `conftest.py` incluído).
     - População: os upgraders da `v1.1.0`, que a arma ANTIGA (`validate-governance.sh:1165`) arma por engano. É a perna de segurança.
     - Esperado: PLAN-119 NÃO arma, e o WARN aparece.
   - **(3)** A (2) sob `--purge-misinstalled`, com fixtures à mão no caminho antigo, uma idêntica e uma editada.
     - Esperado declarado: sha igual ao da fonte atual ⇒ purgado; o resto ⇒ KEPT (`upgrade.sh:4194-4207`).
     - Depois da W7a, as fixtures antigas saem da fonte ⇒ ficam KEPT e inertes; a editada sobrevive.
   - **(4)** Ramo legado sem baseline (`upgrade.sh:1940-1945`).
     - Esperado: as fixtures novas chegam; gate rc 0.
   - Tag derivada no molde H.14 (`test-upgrade-historical-adopter.sh:895-923`). Tempo medido na abertura; a C38 decide o job próprio.
8. **MF-SEC-R2-8 (texto).**
   - **T-1:** `PLAN-183:2525-2526`, (b) soma 2 paths.
   - **T-2:** `:2546-2547`, tirar «o WS-C recebe as raízes a partir do `REPO_ROOT`» (L5).
   - **T-3:** `:2508`, a perna com marcador plantado é EXTRA permitida (prova o uso monótono), nunca substituto do controle no checkout real (L6).

## Nice-to-have (advisory)

1. Listar o módulo também no manifesto ADR-192, que já está no pacote. Junta a prevenção na sessão (guarda canônica, `check_canonical_edit.py:142`) e a detecção no nightly e no release.
2. Em onda própria (arquivo canônico), pôr `.claude/scripts/**` no filtro do `smoke-install.yml`, para o `shasum -c` correr por PR (R2-SEC3).

## Unseen by the original plan

1. **[R2-2]** Crash do Python = rc 1 [sonda]. O critério da proposta enumera «rc fora de {0, 1}» e, com isso, um contrato {0, 1} lê crash como «adopter» (R2-SEC1).
2. **[R2-1]** Modo link: a raiz inferida do próprio caminho aponta para o framework (R2-SEC2).
3. **[R2-1]** A deriva de manifesto em `.claude/scripts/` não é vista por PR (R2-SEC3).
4. **[R2-4]** Na população da `v1.1.0`, o purge deixa a árvore de testes, e o WARN da C13 vira ruído (R2-SEC6).

## What I would NOT change

- ADR-001 como marcador, nunca `conftest.py`.
- O uso MONÓTONO no ADR (C13): marcador plantado só acrescenta verificação.
- Os controles no checkout REAL, inclusive renomear ou apagar o ADR-001 ⇒ CI vermelha também no `check-rule-invariants`.
- A C11 com controles de outro cwd, inclusive o positivo da cópia velha de `audit_emit.py`.
- O texto do ajuste 1.

---

## R2-1 — (b), módulo em `.claude/hooks/_lib/`

As duas formas do MF-C-5 fecham o VETO. Escolho (b) por três razões:

1. **Prevenção, não detecção tardia.** A guarda canônica cobre `_lib/*.py` (`check_canonical_edit.py:142`). Sob (a), o arquivo tem oráculo 0, e o manifesto só detecta, tarde (R2-SEC3).
2. **Menor base confiável.** Protege-se uma função de poucas linhas, não o registro inteiro de invariantes (385 linhas).
3. **A classe «bit de execução» deixa de existir.**

Custo: +2 paths. Se a abertura medir 9, a saída é (a) com o manifesto, e o VETO segue fechado.

## R2-2 — FAIL nomeado, sem fallback literal

ARMAR por erro, no adopter, dá ao menos 3 FAIL de diagnóstico errado: o WS-A exige `_lib/test_isolation.py`, não entregue (`_framework_manifest_set.sh:101`), mais os conftests (`validate-governance.sh:1168-1178`). O FAIL nomeado dá 1 erro com a causa.

O fallback de Critic-A:
- re-deriva o marcador (choca com a C12);
- é «fail-open parity» declarado (`install.sh:1527-1537`);
- cala a falha de infraestrutura num gate de CI, que falha ALTO.

Por classe, igual no fonte e no adopter:
- módulo ausente, erro de import, rc ≠ 0, token ilegível ⇒ FAIL nomeado;
- sem bit de execução ⇒ classe inexistente (invocação por `python3`).

Nenhuma classe pula.

## R2-3 — (b)

A opção (c) cura só este chamador e deixa o script dependente do cwd para o próximo. O FAIL no vácuo só existe no `.py`: o `.sh` não vê o que ele varreu (`check-test-audit-isolation.py:599-617`). Pela 2.ª ocorrência (R2-SEC4), a cura é estrutural. Os chamadores conferidos são só `validate-governance.sh:1192` e o teste `:315`.

## R2-4 — 4 pernas

Síntese: a matriz de Critic-B, os bytes da `v1.1.0` de Critic-A e o purge com o arquivo editado sobrevivente de Critic-C. A população da `v1.1.0` fica COBERTA pela perna (2), a única em que a arma antiga erra. Detalhe no MF-SEC-R2-7.

## C11–C14, ajuste 1 e lacunas

- **Confirmados:** C11 (com o controle de vácuo), C12 (com o escopo do MF-SEC-R2-3), C13 (com MF-SEC-R2-5 e R2-6), C14 e o ajuste 1.
- **Lacunas que procedem:** L4 (cumprida aqui), L5 ⇒ T-2, L6 ⇒ T-3, L7 (+2 paths; sem fallback, sem isenção), L8 ⇒ MF-SEC-R2-3, L9 ⇒ MF-SEC-R2-5, L10 ⇒ esperado da perna (3).
- **L1–L3:** fora da lente; os riscos acima usam o formato de bullets que o coletor lê.

## Paths e esforço (ADR-081)

- **Os 8 paths (oráculo):** `validate-governance.sh` (0, membro ADR-192), `gate-scripts-manifest.txt` (1), `check-test-audit-isolation.py` (0), `check-rule-invariants.py` (0), `_lib/<predicado>.py` novo (1), `test_adopter_dogfood_boundary.py` novo (0; abriga os controles da C11–C13 e os testes do módulo), `test-upgrade-historical-adopter.sh` (0), ADR novo (1).
- **Fora da conta:** índice dos ADR, documentos de contagem e `CLAUDE.md:54` (regra comum 13).
- **Esforço:** W7b ~120–200k tokens, 1–2 sessões; as minhas condições somam ~20–40k dentro disso.
- **Espera externa:** a do e2e (C38).

## Estado do VETO

| onda | veredito | VETO | condição |
|---|---|---|---|
| **W7b** | **PROCEED** | **RETIRADO** | R2-1 (b), ou (a) com o manifesto se medir 9 paths; R2-2 = FAIL nomeado sob contrato por token. Volta a LEVANTADO no rail se o predicado sair de arquivo canônico e fora do manifesto, ou se alguma classe de falha pular o bloco sem linha nomeada |

Nenhum conteúdo lido trouxe instrução dirigida a mim. Nada escrito fora deste arquivo.
