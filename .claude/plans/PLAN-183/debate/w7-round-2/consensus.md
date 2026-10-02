---
plan: PLAN-183
round: 2
debate_dir: .claude/plans/PLAN-183/debate/w7-round-2/
rounds_synthesized: [w7-round-1, w7-round-2]
scope: "só a W7b (R2-1 a R2-4; C11 a C14 e o ajuste 1). W7a, W8, W9 e W10 saíram PROCEED na rodada 1"
critics: [Critic-A, Critic-B, Critic-C]
agents_considered: [Critic-A, Critic-B, Critic-C, red-team]
verdicts: [ACCEPT, ACCEPT, ACCEPT]
red_team: ".claude/plans/PLAN-183/debate/w7-round-3/red-team.md (consensus_survives: true; RT-1 a RT-10; nenhum P0; 1 afirmação falsa neutralizada)"
vetoes: "Critic-C (ADR-052). RETIRADO para R2-1 = (a) com o manifesto, pelo texto do próprio portador («se a abertura medir 9, a saída é (a) com o manifesto, e o VETO segue fechado»). Volta a LEVANTADO no rail se o check-rule-invariants.py ficar fora do manifesto ADR-192 no pacote, ou se alguma classe de falha pular o bloco sem linha nomeada."
wave_verdicts:
  W7b: PROCEED
round_verdict: PROCEED
design_coherent:
  W7b: true
debate_closed: true
decisions:
  R2-1: "(a) check-rule-invariants.py, no manifesto ADR-192 no mesmo pacote"
  R2-2: "FAIL nomeado sob contrato de token; nunca pula, nunca arma; sem literal"
  R2-3: "(b) --repo-root no .py; padrão = raiz do próprio script; FAIL no vácuo"
  R2-4: "4 pernas (E1 a E4), tag pelo predicado de entrega da própria tag"
execution_conditions: "23 novas (C39 a C61); C11 a C14 e C38 seguem valendo, refinadas"
consensus_adjustments: 18
owner_decisions_new: 0
decisions_revised_in_plan: "pendente — esta síntese NÃO edita o plano; o CEO aplica a §4 num commit livre (regra comum 6)"
checked_at_head: 26362b536337
synthesized_at: 2026-10-02T09:55:00Z
synthesized_by: CEO (síntese delegada, S361)
synthesized_from: "texto anonimizado das três críticas da rodada 2 (scratchpad da sessão, fora do repositório); proposta da rodada 2; Red Team; consenso da rodada 1; PLAN-183 no HEAD 26362b53. Limitações: o cabeçalho do mapa de anonimização foi lido e expõe os arquétipos; os prefixos dos ids de risco também os deixam inferir; o oráculo --is-canonical não foi re-rodado. Cada decisão se apoia em fato conferido no disco."
---

# Consenso — PLAN-183, debate L3 da W7b, rodada 2 (final pela C37)

> `design-coherent` (DEBATE-SCHEMA §13.1) certifica só coerência de desenho entre perspectivas do MESMO modelo e
> não autoriza publicar: o pacote segue V0 → V1 → V2 (rail do Codex) → V3 (GPG do Owner). Repositório público:
> só classes de defeito e invariantes, nenhuma receita de contorno de guarda.

## 0. Verificação no disco (HEAD `26362b53`)

O diff `e8ac8aba..26362b53` é 1 commit de materiais do PLAN-194 e não toca nenhum arquivo citado abaixo.

| # | afirmação (quem) | evidência | resultado |
|---|---|---|---|
| 1 | Contagem de `_lib` é EXATA e (b) a muda (A, RT-2) | `verify-counts.sh:202` (exclui `__init__.py`), regra `lib` exata `:674-678`; `ls _lib/*.py` = 73 com `__init__` ⇒ 72; citada em `INSTALL.md:213,581`, `docs/ARCHITECTURE.md:47,69`, `CLAUDE.md:53`, `CHANGELOG.md:12` | **procede** |
| 2 | (b) = 11 paths; (a) = 8 (RT-2) | `docs/ARCHITECTURE.md` já cita a contagem de ADR (`:56`, `:71`), logo já é documento da 4.ª exceção; o `INSTALL.md` não cita | **procede em parte**: (b) ≥ 10 (11 se `ARCHITECTURE.md` contar); nas duas leituras, (b) passa de 8 |
| 3 | «(b) com R2-3 (b) = 8» (proposta [I], MF-B-R2-7, Critic-C) | itens 1, 2 e 4 | **não procede** (a afirmação falsa que o Red Team neutralizou) |
| 4 | `PLAN-183:2525-2526`: o módulo em `_lib/` «somaria 1 path» (A, C) | a C12 faz o `check-rule-invariants.py` consumir o módulo (+2) e o item 1 arrasta o `INSTALL.md` | **não procede** |
| 5 | Uma árvore-fixture copia SÓ o validador e exige rc 0 (RT-1) | `test_plan_schema_enforcement.py:72` (cópia), `:133,158,237` (rc 0); `pytest.ini` coleta `.claude/scripts/tests`; população nomeada em `validate-governance.sh:1163-1164`. Os outros testes que citam o validador instalam alvo real ou usam stub | **procede**; é a única |
| 6 | Crash do Python sai com rc 1 (A, B, C) | medido no Python 3.9.6: import ausente = 1, `SystemExit("x")` = 1, exceção = 1; erro de argparse = 2 | **procede** |
| 7 | `Path.is_file()` engole mais de um errno (RT-6) | `pathlib._IGNORED_ERROS` no 3.9.6 = {ENOENT, EBADF, ENOTDIR, ELOOP} | **procede** |
| 8 | O molde `--is-canonical` vira exceção em token e lê a raiz de env/cwd (RT-6) | `check_canonical_edit.py:2747`, `:2759-2764` | **procede** |
| 9 | Regra de tag de B («a mais nova cujo `upgrade.sh` substitui `.claude/hooks` inteiro») elege a `v1.4.2` (RT-3) | `backup_and_replace ".claude/hooks"` presente no `upgrade.sh` de TODAS as tags `v1.0.0`…`v1.4.2` | **procede**; o sinal de MF-B-R2-10 **não procede** |
| 10 | Com a `v1.4.2`, o purge passa no vácuo; a `v1.1.0` fica 72 % KEPT (RT-3) | árvore `.claude/hooks/tests` idêntica ao HEAD no mesmo relpath (blob por blob, `git ls-tree`, 2026-10-02): `v1.4.2` 578/578; `v1.1.0` **496/549 idênticos, 53 diferentes (9,65 %)** — o «156/549 (393 KEPT)» e os «72 %» do Red Team NÃO procedem (revisão cruzada do Codex, reconferida pelo CEO) | **procede em parte**: a `v1.4.2` dá purge no vácuo (0 KEPT); a `v1.1.0` deixa 53 arquivos KEPT, então a perna do purge tem sinal e a escolha da tag (C55) se mantém |
| 11 | Sinal da RT-3 elege a `v1.1.0` | `scripts/_framework_manifest_set.sh` cita `.claude/hooks/tests` 0× em `v1.0.0` e `v1.1.0` e ≥ 1× a partir da `v1.2.0-rc.1` | **procede** (lido por menção ao caminho no arquivo da tag) |
| 12 | A regra por ancestralidade (A) falha na CI (B) | `smoke-install.yml:380`: tags buscadas com `--depth 1` | **procede**; `git show <tag>:<path>` funciona nessa profundidade |
| 13 | Quem parou na `v1.1.0` tem digests da árvore de testes no baseline (A, RT-3) | `_framework_manifest_files` da `v1.1.0` anda com `find` sem predicado de exclusão (`:108-121` da tag) | **procede** por leitura; efeito em adopter real não medido |
| 14 | O modo atual do `check-rule-invariants.py` tem `--repo` com padrão `"."` e só stdlib (RT-2, C) | `:323-329`; imports em `:60-68` | **procede** |
| 15 | O bloco de invariantes arma por `[ -x ]` e usa arquivo de saída compartilhado (L9, RT-9) | `validate-governance.sh:997`, `:1000-1009` (`.rule-invariants.out` + `rm -f`) | **procede** |
| 16 | OK do PLAN-119 é texto fixo; checker ausente é WARN; resumo `Errors:` (B, RT-8) | `:1199`, `:1202`, `:1317`; ecos de sub-checagem em `:1004`, `:1196` | **procede** |
| 17 | `argv[1:]` vira raiz posicional e raiz inexistente é pulada (RT-4) | `check-test-audit-isolation.py:600`, `:603-604`; leituras de cwd em `:575`, `:591`, `:600`, `:603`, `:610` | **procede** |
| 18 | O teste do gate faz `chdir` ao repo e chama `main` sem raízes (RT-4, B) | `test_check_test_audit_isolation.py:303-317` | **procede**: o padrão «raiz do script» o mantém verde |
| 19 | 2.º predicado com OUTRO marcador (RT-5) | `check-substrate-drift.py:803-808` (pin manifest do Codex OU ADR-149) | **procede** |
| 20 | Modo link instala `_lib` por `ln -s` (C, R2-SEC2) | `install.sh:1353-1354`, `:1541` | **procede** por leitura |
| 21 | Deriva de membro do manifesto em `.claude/scripts/` não é vista por PR (C, R2-SEC3) | filtro do `smoke-install.yml` tem `.claude/hooks/**` (`:120`) e só 2 arquivos de `.claude/scripts/` (`:105`, `:115`); `shasum -c` em `:355-362`; `validate.yml` cita o manifesto 0× | **procede** |
| 22 | O guard canônico cobre `_lib/*.py`, não o `check-rule-invariants.py` (C) | `check_canonical_edit.py:142` | **procede** (padrão lido; oráculo não re-rodado) |
| 23 | O purge autoriza só hash igual à fonte ATUAL no mesmo relpath ou ao digest do baseline (L10) | `upgrade.sh:4194-4207` | **procede** |
| 24 | Linhas do plano apontadas (L5, L6, B) | `PLAN-183:2508` («o marcador arma»), `:2525-2526`, `:2546-2547` (resto da opção (a) pura), `:2553` (vermelho «HEAD pré-cura ⇒ 3 RED», inatingível com a W7a landada) | **procede** |
| 25 | A medida M1 não roda nestes diretórios (L1) | `debate-converge.py:115-116` resolve só `debate/round-<N>`; `red-team.md` é ignorado pelo coletor (`:94`) | **procede** |

## 1. Veredito da W7b

**PROCEED** (`design-coherent`). Três de três críticos ACCEPT/PROCEED; o Red Team conclui `consensus_survives:
true`. Nenhum P0. A única afirmação falsa que sustentava escolha («(b) cabe em 8», §0 itens 2–4) fica neutralizada
pela R2-1 = (a), que tem aceite ESCRITO dos três: Critic-A a escolhe; Critic-B «aceito também R2-1 (a) com
manifesto», sob MF-B-R2-1, 3 e 6; Critic-C a fixa como saída se a abertura medir 9 paths. O disco mede ≥ 10.

- **Critério da proposta (§3), item a item:** zero must-fix bloqueante (os três declaram condições só de execução);
  VETO retirado; R2-1 a R2-4 decididas com razão (§2); C11 a C14 e o ajuste 1 confirmados por 3 de 3; cada decisão
  com Check e controle vermelho (§3); estimativa ADR-081 abaixo; tabela da W7b em 8 paths (C40).
- **Estado do VETO (Critic-C):** RETIRADO. Volta a LEVANTADO no rail em dois casos, nos termos do portador:
  (1) o predicado fora de arquivo canônico E fora do manifesto, ou seja, o `check-rule-invariants.py` sem entrada
  no manifesto ADR-192 no MESMO pacote (C39); (2) qualquer classe de falha que pule o bloco sem linha nomeada
  (C41 a C48).
- **Regra de parada (C37):** cumprida; não há rodada 3 de críticos. O arquivo do Red Team em `w7-round-3/` segue o
  caminho do DEBATE-SCHEMA (`round-<N+1>/red-team.md`) e não abre rodada.
- **Esforço (ADR-081):** W7b com as condições, ~120–280k tokens e 1–2 sessões (faixas dos três críticos); o Red
  Team soma ~25–45k dentro do pacote. Espera externa: a do e2e (C60).

## 2. Decisões R2-1 a R2-4

**R2-1 — (a): o predicado mora no `check-rule-invariants.py`, que entra no manifesto ADR-192 no mesmo pacote.**
Segue a recomendação da RT-2, que o disco sustenta: (b) não fecha em 8 (§0, 1–4), e a C37 não deixa repetir a
rodada para dividir o pacote. A (a) já hospeda a única implementação (`_is_framework_repo`, `:212-217`), então a C12
sai sem mover código; validador e predicado ficam na mesma árvore entregue. **Custos da (a), registrados:** a guarda
na sessão fica só por detecção (o arquivo tem padrão fora de `_CANONICAL_GUARDS`; §0, 22), e a deriva do membro em
`.claude/scripts/` só aparece no nightly e no release (§0, 21; R2-SEC3) — vai a FU (ajuste 15). As razões de B e C
por (b) (importação direta nos testes, prevenção local) cedem à conta de paths; a MF-C-R2-2 (o script importar o
módulo) deixa de se aplicar, porque a implementação não sai do lugar.

**R2-2 — FAIL nomeado sob contrato de token; nunca pula, nunca arma; sem literal (3 de 3).** Critic-A troca o
fallback da rodada 1, que re-derivava o marcador (choque com a C12) e era paridade fail-open. ARMAR por erro dá ≥ 3
FAIL de diagnóstico errado no adopter (`validate-governance.sh:1169-1178`; `test_isolation.py` não entregue); pular
relaxa guarda. O rc 1 do crash do Python (§0, 6) proíbe «rc 1 = não é repo-fonte»: a resposta vai no stdout.

**R2-3 — (b), raiz explícita no `.py` (3 de 3; Critic-A troca a (c) da rodada 1).** É a 2.ª ocorrência do «verde no
vácuo» (`test_check_test_audit_isolation.py:303-306`), e o FAIL no vácuo só existe dentro do `.py`. **Divergência
resolvida — padrão sem a flag:** A e C usam a raiz derivada do caminho do script, sem `resolve()`; B preferia o cwd
para não mudar o teste `:311-317`. Fica a raiz do script (2 de 3; RT-4): o disco mostra que o teste segue verde
com ela (§0, 18), então a exigência de B entra como Check.

**R2-4 — quatro pernas, E1 a E4, com a tag derivada pelo predicado de ENTREGA da própria tag (RT-3).** A matriz
une a de B (populações e bases do vermelho), os bytes da `v1.1.0` de A (`git archive`) e o arquivo editado que
sobrevive de C. A regra de B (MF-B-R2-10) e a de A (ancestralidade) saem: a primeira elege a `v1.4.2` e põe o purge
no vácuo (§0, 9–10); a segunda falha com `--depth 1` (§0, 12). A população da `v1.1.0` fica COBERTA (E2 e E3).

## 3. Condições de execução da W7b

Condição não cumprida reprova o SIGN da W7b, não o debate; quem confere é o rail (V2). **Seguem valendo da rodada
1:** C11 a C14 (refinadas abaixo, cada refino citado), C37 e C38; a C10 (FU do censo pela FORMA) é da W7a.

**R2-1 — local e teto**

1. **C39 — Hospedeiro** (MF-A-R2-1, RT-2; MF-C-5 da r1). O `check-rule-invariants.py` ganha um modo que só responde
   se a raiz é o repo-fonte, com `_is_framework_repo` (`:212-217`) como a ÚNICA implementação. O arquivo entra no
   manifesto ADR-192 no MESMO pacote, e a linha dele na tabela deixa de ser condicional.
2. **C40 — Teto de 8 paths** (RT-2, RT-1, MF-B-R2-7, MF-A-R2-5). `validate-governance.sh`, manifesto,
   `check-test-audit-isolation.py`, `check-rule-invariants.py`, `test_adopter_dogfood_boundary.py` (novo),
   `test_plan_schema_enforcement.py`, `test-upgrade-historical-adopter.sh` e o ADR novo; índice, documentos de
   contagem e `CLAUDE.md:54` fora da conta (regra comum 13). Todo teste novo vai ao `test_adopter_dogfood_boundary.py`;
   o `test_check_rule_invariants.py` não muda. Um 9.º path inevitável ⇒ divisão pelo modelo v2, nunca exceção nova.

**R2-2 — falha ao avaliar o predicado**

3. **C41 — Contrato do CLI** (MF-A-R2-2, MF-B-R2-1, MF-C-R2-1, RT-2). Resposta no STDOUT: UM token exato,
   `framework` ou `adopter`, sempre com rc 0. Qualquer rc ≠ 0 ou stdout fora dos dois tokens, linha extra incluída,
   dá exatamente 1 linha FAIL nomeada com a classe, no repo-fonte e no adopter; nunca pula, nunca arma. O modo
   EXIGE `--repo <raiz>` (hoje o padrão é `"."`) e nunca infere a raiz do próprio caminho nem do cwd (modo link,
   R2-SEC2); o validador passa `"$REPO_ROOT"`. Stdlib-only, Python ≥ 3.9, sem importar módulo de `_lib/`.
4. **C42 — Invocação** (MF-A-R2-3, MF-B-R2-5, MF-C-R2-5; L9). Os blocos PLAN-119 e de invariantes (`:997`) chamam
   por `python3 "<caminho>"` com `[ -f ]`, nunca `[ -x ]`. Script ausente ⇒ FAIL nomeado. Controles em cópia
   descartável: `chmod -x` ⇒ o bloco continua rodando; arquivo removido ⇒ 1 FAIL nomeado.
5. **C43 — Sem literal, sem seam** (MF-A-R2-2, MF-C-R2-3, MF-B-R2-2). Nenhum literal do marcador no bash. Nenhuma
   variável de ambiente troca o predicado: os testes copiam validador e script para árvore descartável, onde o
   `REPO_ROOT` sai do caminho do script (`validate-governance.sh:17`).
6. **C44 — Erro nunca vira token** (RT-6). O CLI não tem `except` que produza token. Só ENOENT e ENOTDIR contam como
   «ausente»; qualquer outra OSError ⇒ rc ≠ 0. Controle: um errno de FS diferente, plantado em tmp ⇒ 1 FAIL nomeado.
7. **C45 — Captura do token** (RT-9). Só por substituição de comando sobre o stdout do predicado; arquivo
   intermediário proibido (o molde `.rule-invariants.out`, `:1000-1009`, não se segue).
8. **C46 — Controles vermelhos por classe** (MF-B-R2-1, MF-C-R2-1). Import quebrado plantado, `raise`,
   `sys.exit("x")`, script ausente, stdout ilegível, token fora do conjunto, linha extra e `python3` fora do PATH ⇒
   1 FAIL nomeado cada, no repo-fonte e no alvo de adopter.
9. **C47 — Árvores-fixture** (RT-1). O construtor do `test_plan_schema_enforcement.py` copia o CLI do predicado. O ADR
   declara que toda árvore que roda o validador carrega o CLI. «Pular quando a árvore não parece instalação» fica
   proibido. Controle: a suíte sem o CLI copiado dá exatamente 1 FAIL nomeado.
10. **C48 — Skew de versão** (RT-10). O ADR declara as duas combinações: validador novo com CLI antigo preservado dá
    rc 2 (argparse) e 1 FAIL nomeado; validador antigo preservado significa que a cura não chega. Um teste unitário
    cobre «CLI sem o modo» e espera 1 FAIL nomeado.

**R2-3 — cura do cwd** (refina a C11)

11. **C49 — Raiz explícita** (MF-A-R2-4, MF-B-R2-6, MF-C-R2-4, RT-4). O `check-test-audit-isolation.py` ganha
    `--repo-root`, reconhecido pelo argparse, nunca caído no argv posicional (`:600`, `:603`). O `.sh` passa
    `--repo-root "$REPO_ROOT"`. Sem a flag, a raiz vem do caminho do script, sem `resolve()`; o cwd nunca entra. As
    TRÊS leituras usam a raiz: ini (`:600`), raízes relativas (`:575`, `:591`, resolvidas em `:603`) e WS-D2
    (`:610`). O `test_check_test_audit_isolation.py:311-317` não muda e segue verde (conferir na abertura).
12. **C50 — Vácuo** (A, B, C). Zero raiz existente OU zero `test_*.py` varrido ⇒ rc 1 com linha nomeada; na chamada
    do repo-fonte, uma raiz do `testpaths` inexistente ⇒ FAIL (B). O `.sh` repassa a linha OK do `.py`, com a
    contagem, no lugar do OK fixo (`:1199`) (B). Com o predicado verdadeiro, checker ausente ⇒ FAIL (hoje WARN, `:1202`).
13. **C51 — Controles de OUTRO cwd** (A, B, C, RT-4). Os dois da C11, um de vácuo e um de raiz inexistente,
    vermelhos antes e verdes depois; `--repo-root` com cwd estranho dá o mesmo resultado que a chamada sem flag.

**C12 e C13 refinadas**

14. **C52 — Censo** (MF-A-R2-5, MF-B-R2-3, MF-C-R2-3, RT-5). Mora no `test_adopter_dogfood_boundary.py`. Conta
    como re-derivar: constante de string em código (AST, fora de docstring) ou token de shell fora de comentário que
    nomeie o arquivo do ADR-001, em `.claude/hooks`, `.claude/scripts`, `scripts` e `.github`. Ficam fora: `tests/`,
    `.claude/plans/`, `*.md` (o índice `.claude/adr/README.md:254` incluído), testes que PLANTAM o marcador e a
    string de `test_bash_canonical_interceptor.py:47-50`. Esperado: exatamente {`check-rule-invariants.py`}.
    Vermelho: re-derivação plantada em cópia temporária. 2.º censo: o `if` do PLAN-119 não testa
    `.claude/hooks/tests` (B). O censo cobre também a FORMA «decisão framework × adopter por existência de arquivo»;
    o sítio `check-substrate-drift.py:803-808` vira FU nomeado, nunca silêncio (RT-5).
15. **C53 — C13 pelo custo** (MF-B-R2-4; L6). No pytest, a cada push: o CLI diz `framework` na raiz REAL (renomear ou
    apagar o ADR-001 ⇒ CI vermelha, também no `check-rule-invariants`), e um teste estrutural confirma que o `if` do
    PLAN-119 chama só o CLI. Na bateria do LAND: cabeçalho PLAN-119 exatamente 1 vez no validador completo (fora do
    pytest, porque o validador grava `.rule-invariants.out` no `REPO_ROOT`). Marcador plantado em tmp é perna EXTRA
    permitida, que prova o chaveamento e o uso monótono; nunca substitui o controle no checkout real (3 de 3).
16. **C54 — WARN da forma dogfood** (MF-C-R2-6, MF-B-R2-12, RT-7). Só WARN, nunca ERROR. Exige assinatura do
    framework (o fixture `_ceo_audit_isolation_session`, `:1174`, ou hash de geração entregue). O texto nomeia a causa
    (árvore de testes herdada) e o remédio: `--purge-misinstalled` e revisão da lista KEPT, com remoção manual do que
    for do framework; nunca «apagar a árvore». Controle: árvore própria sem assinatura ⇒ 0 WARN. E2 e E3 declaram o
    WARN como saída esperada, exatamente 1 vez.

**R2-4 — matriz do e2e.** Cada perna nomeia a população, o esperado e a base do vermelho (MF-C-R2-7, MF-B-R2-8/9).

17. **C55 — Tag** (RT-3). A mais nova cujo `scripts/_framework_manifest_set.sh` NÃO exclui `.claude/hooks/tests`,
    lido por `git show` (funciona com depth 1); hoje, a `v1.1.0`. Sanidade: sem ao menos 1 hash ≠ HEAD no conjunto
    plantado, a perna aborta (molde do scaffold do H.14, `:914`). O esperado PURGED/KEPT é derivado por hash no teste.
18. **C56 — E1, classificada** (C9 da r1, MF-B-R2-9, MF-B-R2-11, MF-C-R2-7(1)). É a perna livre da C9, landada ANTES
    de a W7b derivar o material: `v1.4.2` → HEAD; gate rc 0 com `0 warning(s)`; nenhuma linha PLAN-119, com o resumo.
    Vermelho: base = árvore pré-W7a ⇒ `FAIL: 3 RED`.
19. **C57 — E2, resíduo herdado, sem purge** (MF-A-R2-6, MF-C-R2-7(2), RT-8, MF-B-R2-8). Cópia do alvo E1 + TODAS as
    árvores excluídas que a tag derivada entregava (`_pm_trees`/`_pm_files`, `upgrade.sh:4241-4242`; na `v1.1.0`,
    inclusive `.claude/scripts/tests` e `_lib/test_isolation.py`), dos bytes da tag + fixtures à mão no caminho
    antigo, uma idêntica e uma editada. Esperado: resíduo `cmp`-intacto; gate rc 0 pelo caminho novo; validador
    completo com rc 0, `Errors:   0`, conjunto EXATO de WARN e 0 linhas PLAN-119; o resumo é casado junto do rc,
    nunca por grep solto (o validador ecoa sub-checagens). Vermelho: base = pré-W7b ⇒ o PLAN-119 arma e dá FAIL.
20. **C58 — E3, purge** (MF-A-R2-6, MF-B-R2-8, MF-C-R2-7(3), RT-3; L10). O plantio da E2 sob `--purge-misinstalled`.
    PURGED, com backup: exatamente o que tem sha256 igual ao do HEAD no mesmo relpath ou ao digest do baseline.
    KEPT nomeado: o resto, inclusive as 3 fixtures antigas (a W7a apaga o relpath) e a editada. Gate rc 0; asserção
    conjunto contra conjunto. Controle POSITIVO: arquivo plantado com bytes iguais aos da fonte atual no mesmo relpath
    é purgado. O KEPT vai ao ADR pela forma. A população que parou na `v1.1.0` (digests no baseline) tem esperado
    PURGED, declarado.
21. **C59 — E4, sem baseline** (MF-A-R2-6, MF-B-R2-8 P3, MF-C-R2-7(4)). Ramo legado (`upgrade.sh:1940-1945`):
    `_lib/harness_replay/` `cmp`-igual e gate rc 0; como asserção numa perna sem `.claude/.install-manifest.sha256`,
    se houver, senão 4.ª perna.
22. **C60 — Tempo** (MF-A-R2-7; C38). E2 a E4 reaproveitam o alvo E1 (`cp -a`), sem reinstalar. O total é medido na
    abertura; p95 previsto acima de 120 min ⇒ job próprio já na W7b. O registro diz quanto sobra para a W8.

**ADR**

23. **C61 — Conteúdo do ADR novo** (C13, C14, RT-1, RT-5, RT-10, MF-A-R2-6). Declara: o uso MONÓTONO; que toda árvore
    que roda o validador carrega o CLI; as duas combinações de skew; a forma «decisão framework × adopter por
    existência de arquivo», com o FU; e o KEPT do purge, pela forma. `check-claude-md-claims.py` na bateria (C14).

## 4. Plan adjustments (seção W7b do `PLAN-183-adopter-fitness.md`)

O CEO aplica num commit livre (regra comum 6); o rail do pacote confere.

1. *Tabela, `:2504`:* o validador arma o PLAN-119 pelo CLI do `check-rule-invariants.py` (C41), chama os dois blocos
   por `python3` (C42), passa `--repo-root` (C49) e troca o WARN do checker ausente por FAIL (C50).
2. *`:2505`:* manifesto = bump do sha do validador E entrada nova do `check-rule-invariants.py` (C39).
3. *`:2506`:* `check-test-audit-isolation.py` deixa de ser condicional: `--repo-root`, três leituras, FAIL no vácuo.
4. *`:2507`:* `check-rule-invariants.py` deixa de ser condicional: modo predicado com `--repo` obrigatório (C39, C41).
5. *`:2508` (L6):* o teste novo abriga o CLI, o censo, o vácuo e os controles das C11 a C13; a perna com marcador
   plantado é EXTRA permitida, nunca substituto do controle no checkout real (C53; A, B, C; T-3 de C).
6. *Linha nova:* `.claude/scripts/tests/test_plan_schema_enforcement.py`, oráculo a rodar na abertura (C47).
7. *`:2509`:* o e2e ganha E2, E3 e E4 (C57 a C59); a E1 é a perna livre da C9 (C56).
8. *`:2512` («Tamanho»):* 8 paths, lista da C40; 9.º path ⇒ divisão.
9. *`:2518-2520` («Nível»):* debate fechado, PROCEED na rodada 2, com Red Team.
10. *`:2521-2527` («Desenho»):* R2-1 = (a). A frase «somaria 1 path» (`:2525-2526`) sai: o módulo em `_lib/`
    somaria ao menos 2 paths contados (o módulo e o consumidor da C12) mais o `INSTALL.md`, pela contagem exata de
    `_lib` (A, C; RT-2).
11. *`:2528-2533` («Rodada 2»):* troca pelo resultado (§1, §2).
12. *`:2534-2542` («Depende de»):* a perna livre da C9 landa ANTES de a W7b derivar o material (MF-B-R2-11).
13. *`:2544-2548`, 1.º AC (L5):* sai «o WS-C recebe as raízes a partir do `REPO_ROOT`»; entra «o checker resolve as
    três leituras pela raiz explícita» (MF-A-R2-8, T-2 de C). O Check soma C41 a C54.
14. *`:2549-2553`, AC do e2e:* matriz E1 a E4, tag pela C55, esperado do purge (L10). O vermelho de `:2553` passa a
    ter base por perna: pré-W7a para a entrega do gate, pré-W7b para o PLAN-119 (MF-B-R2-9).
15. *«Fora destas ondas»:* FUs nomeados — o 2.º predicado de `check-substrate-drift.py:803-808` (RT-5); o filtro
    de PR do `smoke-install.yml` sobre `.claude/scripts/**`, para o `shasum -c` (R2-SEC3, C NTH 2); o instrumento de
    convergência do debate, L1 a L4 (MF-B-R2-13); o purge ciente das gerações históricas (B NTH 1).
16. *«Resultado do debate»:* linha da W7b = PROCEED (rodada 2), VETO retirado com os dois gatilhos da §1.
17. *«Orçamento»:* W7b ~120–280k tokens, 1–2 sessões, mais o Red Team dentro do pacote.
18. *«Progress log»:* entrada da S361 com este consenso e o fechamento do debate W7.

## 5. Red Team (`w7-round-3/red-team.md`)

**Resultado:** `consensus_survives: true`, nenhum P0, uma afirmação falsa neutralizada («(b) cabe em 8», §0 2–4).
O Red Team rodou sobre as três críticas da rodada 2. A medida M1 não roda nestes diretórios (§0, 25; L1–L2), e
rodá-lo foi a leitura conservadora da obrigação do §12.3, como pedia a MF-B-R2-13. O arquivo não abre rodada 3.

| RT | ataque | absorção |
|---|---|---|
| RT-1 | árvores-fixture ficam vermelhas com «CLI ausente ⇒ FAIL» | C47; +1 path (C40) |
| RT-2 | (b) = 11 paths; registrar (a) com manifesto | decisão R2-1 (§2); C39, C41 |
| RT-3 | a regra de tag de B põe o purge no vácuo | C55 substitui MF-B-R2-10; sanidade e esperado por hash em C55 e C58 |
| RT-4 | padrão sem flag divergia | C49 (raiz do script; B cede) e controle em C51 |
| RT-5 | 2.º predicado com outro marcador | C52 (censo pela forma), C61 e FU (ajuste 15) |
| RT-6 | erro vira token | C44 |
| RT-7 | WARN mandaria apagar testes do adopter | C54 (assinatura e remédio) |
| RT-8 | perna híbrida sem veredito do validador | C57 (todas as árvores, rc + `Errors:` + WARN exato) |
| RT-9 | token por arquivo compartilhado | C45 |
| RT-10 | skew de versão no upgrade | C48 e C61 |

Os itens que o Red Team deu como «já cobertos» (forja do token sob o mesmo UID, marcador nunca entregue, dois gates
presos a um marcador, modo link, bit de execução, ordem com a W7a, tempo do job) seguem nas C41, C42, C53 e C56–C60.

## 6. Artefato terminal (DEBATE-SCHEMA §6)

**O debate W7 (W7a a W10) TERMINA nesta rodada:** W7a, W8, W9 e W10 saíram PROCEED na rodada 1; a W7b, aqui.

- **Este arquivo NÃO é o `approved.md`.** Ele é a síntese anterior à ratificação. O `approved.md` das cinco ondas
  nasce SÓ depois da ratificação do Owner, em `.claude/plans/PLAN-183/debate/w7-round-2/approved.md`, no formato
  do §6 (`rounds_completed: 2`, `final_verdict`, arco das duas rodadas e do Red Team, deltas do plano, lições).
- **Antes dele:** a ratificação escrita do veredito das cinco ondas; a decisão 1 da rodada 1 (trilha forense do P4,
  W9a) escrita, ou adiada pelo Owner explicitamente até o SIGN da W9a; os ajustes da §4 deste consenso aplicados.
- **Nunca sob `architect/`:** o glob de sentinela é `PLAN-*/architect/round-*/approved.md`
  (`check_canonical_edit.py:1005`); o `approved.md` deste debate não é sentinela de edição canônica.
- **A W7b não espera o `approved.md` para ser construída**, mas espera a W7a landada e a perna livre da C9 (C56).

## 7. Decisões do Owner

**Nenhuma decisão nova.** Seguem com o Owner, da rodada 1: a decisão 1 (trilha forense do P4, W9a; recomendada a
opção (i)) e a ratificação do debate (§6). Para ciência: a R2-1 = (a) troca prevenção na sessão por detecção no
nightly e no release para o membro novo do manifesto; o FU do filtro de PR (ajuste 15) fecha essa janela.
