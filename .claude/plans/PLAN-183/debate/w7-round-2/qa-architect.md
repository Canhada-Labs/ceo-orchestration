---
round: 2
archetype: QA Architect
skill: testing-strategy
agent_persona: Principal QA Architect
served_model: claude-opus-5-5
generated_at: 2026-10-02T10:05:00Z
plan: PLAN-183
plan_commit: e8ac8aba
wave_in_scope: [W7b]
wave_verdict:
  W7b: PROCEED
p0_found: false
false_claims_found: 0
choices: {R2-1: "(b) módulo em _lib/", R2-2: "FAIL nomeado; resposta por token no STDOUT", R2-3: "(b) raiz explícita no .py, com FAIL no vácuo", R2-4: "3 pernas novas + a perna da C9, com o esperado escrito"}
inputs: [w7-round-2/proposal.md, w7-round-1/consensus.md, PLAN-183 §W7b @ e8ac8aba]
---

# PLAN-183 W7b — rodada 2 (FINAL) — crítica do QA Architect

> **[disco]** = li no HEAD `e8ac8aba`. **[medido]** = executei num diretório temporário meu, apagado depois;
> nada gravado no repo. Regra da rodada final: só P0 ou afirmação FALSA impedem o PROCEED.

## Verdict

**ACCEPT (com condições) — W7b: PROCEED** (`design-coherent`).

Fui eu quem pediu RUN-ANOTHER-ROUND na rodada 1. Os motivos estão curados: ajuste 1 aplicado (`PLAN-183:2130`),
opção (a) pura fora (C11), matriz do e2e na R2-4. Não achei P0 nem afirmação falsa. **Sim: as condições
MF-QA-R2-1..13 bastam para o meu PROCEED.** Ele não depende de (b)/(b): aceito também R2-1 (a) com manifesto e R2-3
(c), desde que se cumpram MF-QA-R2-1, 3 e 6 e que o resíduo de (c) fique declarado. Nenhuma alternativa é P0; a
divergência entre críticos não leva ao ESCALATE.

## Summary (≤ 3 bullets)

- **Decisivo para a R2-2:** erro de import, exceção não tratada e `sys.exit("msg")` saem com rc 1 em Python
  [medido]. Com «rc 1 = falso», toda queda do predicado DESARMA o PLAN-119 em silêncio.
- **R2-3:** é a 2.ª ocorrência do gate que passa varrendo zero arquivos (`test_check_test_audit_isolation.py:303-306`).
  A cura da classe é o FAIL no vácuo, que exige mudar o `.py`; a (c) cura o chamador, não a classe.
- **Red Team:** o gatilho M1 não consegue disparar como foi escrito (L1, L2). Recomendo rodá-lo sem condição.

## Risks

- R-QA-R2-1 — W7b, HIGH: CLI do predicado com «rc 1 = falso» lê toda queda do Python (rc 1 [medido]) como «não é repo-fonte» e desarma o PLAN-119 em silêncio no repo-fonte; mitigação MF-QA-R2-1.
- R-QA-R2-2 — W7b, HIGH: seam de teste por variável de ambiente para trocar o predicado do validador vira canal de desarme; mitigação MF-QA-R2-2.
- R-QA-R2-3 — W7b, MEDIUM: o checker passa no vácuo (raiz inexistente pulada sem aviso, `check-test-audit-isolation.py:603-604`; zero arquivos ⇒ rc 0) e o validador imprime um OK fixo, alheio ao que foi varrido (`validate-governance.sh:1199`); mitigação MF-QA-R2-6.
- R-QA-R2-4 — W7b, MEDIUM: o vermelho do e2e em `PLAN-183:2553` («HEAD pré-cura sai FAIL: 3 RED») não sai vermelho com a W7a landada, que é dependência da W7b (`:2534`); mitigação MF-QA-R2-9.
- R-QA-R2-5 — W7b, MEDIUM: derivar a tag da população `v1.1.0` por ancestralidade falha na CI, que busca tags com depth 1 (`smoke-install.yml:380`); mitigação MF-QA-R2-10.
- R-QA-R2-6 — W7b, MEDIUM: a perna do purge vira vácuo, pois após a W7a as fixtures antigas ficam KEPT por construção (`upgrade.sh:4194-4207`); mitigação MF-QA-R2-8.
- R-QA-R2-7 — processo, MEDIUM: o gatilho do Red Team não dispara (caminho, parse e casamento exato que pune a cura); mitigação MF-QA-R2-13.

## Must-fix (blocking)

**(a) P0 ou afirmação falsa: nenhum.** O `:2130` corrigido confere: 549 arquivos em `.claude/hooks/tests` na
`v1.1.0`; `e718cd89` não é ancestral dela; a 1.ª tag que o contém é a `v1.2.0-rc.1` [disco]. O `:2553` é Check mal
especificado (sem base definida para «pré-cura»), não afirmação de desenho: vira a MF-QA-R2-9.

**(b) Condições de execução (não bloqueiam o PROCEED; o rail confere no SIGN):**

1. **MF-QA-R2-1 — Protocolo da CLI.** Resposta por token exato no STDOUT, rc 0 (molde do oráculo `--is-canonical`).
   Qualquer rc ≠ 0 ou STDOUT fora dos dois tokens = falha de avaliação ⇒ UMA linha FAIL nomeada, no repo-fonte e no
   adopter; nunca pula, nunca arma. Vermelhos: import quebrado, `raise`, `sys.exit("x")`, módulo ausente, STDOUT
   ilegível, `python3` fora do PATH ⇒ 1 FAIL nomeado cada. O critério «rc fora de {0, 1}» da proposta vira «rc ≠ 0».
2. **MF-QA-R2-2 — Sem seam por variável de ambiente.** Os testes copiam validador e módulo para uma árvore
   descartável; o `REPO_ROOT` sai do caminho do script (`validate-governance.sh:17`), logo a cópia exercita o real.
3. **MF-QA-R2-3 — Censo da C12 (L8).** Re-derivar = constante de string em código (AST, fora de docstring) ou token
   de shell fora de comentário que nomeie o arquivo do ADR-001, em `.claude/hooks`, `.claude/scripts`, `scripts` e
   `.github`, fora `tests/`, `.claude/plans/` e `*.md`. Esperado: exatamente {o módulo}; hoje
   {`check-rule-invariants.py:163`} [disco] (o docstring `:37` fica fora pela regra). Vermelho: re-derivação plantada
   em cópia temporária. Segundo censo: o `if` do PLAN-119 não testa `.claude/hooks/tests`.
4. **MF-QA-R2-4 — C13 dividida pelo custo.** No pytest (CI a cada push): a CLI diz «verdadeiro» na raiz REAL, e um
   teste estrutural confirma que o `if` do PLAN-119 chama só a CLI. Na bateria do LAND: cabeçalho PLAN-119
   exatamente 1 vez no validador completo. Esse não roda em pytest no checkout real, porque o validador grava
   `.rule-invariants.out` no `REPO_ROOT` (`validate-governance.sh:1001-1009`).
5. **MF-QA-R2-5 — L9.** O bloco de invariantes passa a `python3 <script>` com `[ -f ]`, não `[ -x ]` (`:997`); com o
   predicado verdadeiro, script ausente ⇒ FAIL nomeado. Vermelhos: sem bit ⇒ bloco roda; removido ⇒ FAIL.
6. **MF-QA-R2-6 — R2-3 (b).** `--repo-root` resolve `pytest.ini`, raízes do `testpaths` (`:575`, `:591`, `:603`) e
   base do WS-D2 (`:610`); sem a flag o padrão segue no cwd, e `test_check_test_audit_isolation.py:311-317` não muda.
   FAIL quando a chamada do repo-fonte varre zero `test_*.py` ou uma raiz do `testpaths` não existe. O `.sh` repassa
   a linha OK do `.py` (com contagem) no lugar do OK fixo (`:1199`). Checker ausente com predicado verdadeiro ⇒ FAIL
   (hoje WARN, `:1202`). Vermelhos: os dois da C11, raiz inexistente, zero arquivos.
7. **MF-QA-R2-7 — Teto pré-registrado.** (b)+(b) = 8 paths: validador, manifesto, `check-test-audit-isolation.py`,
   `check-rule-invariants.py`, módulo em `_lib`, teste novo, e2e, ADR. Todo teste novo vai para
   `test_adopter_dogfood_boundary.py`; `test_check_rule_invariants.py` não muda (sem uso externo de
   `_PRIMARY_MARKER` nem `_is_framework_repo` [disco]). Um 9.º path inevitável ⇒ divisão pelo modelo v2, nunca
   exceção nova.
8. **MF-QA-R2-8 — Matriz da R2-4** (tabela abaixo): população, montagem, esperado e base do vermelho por perna. A
   perna do purge leva controle POSITIVO: arquivo plantado em árvore excluída, com bytes iguais aos da fonte atual
   no mesmo relpath, tem de ser purgado.
9. **MF-QA-R2-9 — Base do vermelho por perna.** Entrega do gate: árvore pré-W7a (já nas pernas permanentes da C9).
   PLAN-119: árvore pré-W7b. O `PLAN-183:2553` passa a dizer isso.
10. **MF-QA-R2-10 — Tag derivada pelo CONTEÚDO.** A mais nova tag cujo `scripts/upgrade.sh` ainda substitui
    `.claude/hooks` inteiro, lida por `git show <tag>:…`: funciona com depth 1; `--is-ancestor` não.
11. **MF-QA-R2-11 — Sequência.** As pernas livres da C9 landam ANTES de a W7b derivar o material (mesmo
    `test-upgrade-historical-adopter.sh`; lição do baseline que envelhece).
12. **MF-QA-R2-12 — WARN da forma dogfood (C13)** nomeia o remédio: o purge mantém KEPT a maior parte dos 549
    arquivos, logo o remédio é a remoção manual, declarada. A P2 confere o WARN exatamente 1 vez.
13. **MF-QA-R2-13 — Red Team sem condição** sobre o consenso final da W7b, em `w7-round-2/red-team.md`, citado pelo
    consenso; FU do instrumento (L1–L4). Bloqueio do Red Team aciona a C37.

**Matriz (MF-QA-R2-8)** — tempo somado medido na abertura, contra a C38:

| perna | população | montagem | esperado | vermelho (base) |
|---|---|---|---|---|
| P1 (C9) | `v1.4.2`, ramo classificado | livre, landada depois da W7a | gate rc 0, `0 warning(s)` | pré-W7a: 3 RED |
| P2 | upgraders da `v1.1.0` e contornos à mão (42ledger, arbitrage) | `v1.4.2` + `git archive <tag derivada> -- .claude/hooks/tests`; 1 fixture editada; upgrade com `--purge-misinstalled` | gate rc 0 pelo caminho novo; 0 linhas PLAN-119 + resumo; WARN dogfood 1×; controle positivo purgado; 3 fixtures antigas e o resto KEPT nomeados | pré-W7b: PLAN-119 arma ⇒ FAIL |
| P3 | sem manifesto de baseline | `v1.4.2` sem o manifesto ⇒ ramo legado (`upgrade.sh:1945` falso) | `_lib/harness_replay/` com `cmp` igual; gate rc 0 | pré-W7a: 3 RED |

A perna (3) de Critic-B entra na P2; a população da `v1.1.0` fica coberta, sem exclusão.

## Nice-to-have (advisory)

1. Purge que conheça as gerações históricas (hash-gate por tag, como os schema docs): FU fora da W7b (`upgrade.sh` é da W8).
2. Registrar o p95 do job com as pernas novas (n ≥ 3) antes de reapertar o timeout.

## Unseen by the original plan

1. Python sai com rc 1 em qualquer queda [medido]: protocolo por rc confunde «falso» com «quebrado».
2. O OK do PLAN-119 é texto fixo no `.sh` (`:1199`), alheio ao que o checker varreu.
3. O `testpaths` pula raiz inexistente sem aviso (`:603-604`): vácuo parcial mesmo com o cwd certo.
4. Após a W7a, o purge mantém KEPT as fixtures antigas por construção (fonte sem elas, baseline sem digest).
5. O vermelho do e2e como escrito é inatingível depois da W7a.

## What I would NOT change

- Marcador ADR-001, nunca `conftest.py`; uso MONÓTONO (o predicado só ARMA).
- C11 com dois controles de outro cwd; C13 no checkout REAL; ADR novo com `check-claude-md-claims.py` (C14).
- O `:2130` corrigido (ajuste 1), que confirmo.

## Respostas R2-1 a R2-4

- **R2-1 → (b) módulo em `_lib/`**, com `__main__` para o bash (precedente `_lib/runtime_paths.py:275`, chamado em
  `templates/codex/pre-push-review-gate.sh:110`). Razões: importável direto nos testes, enquanto o script com hífen
  exige `importlib` por caminho (`test_check_rule_invariants.py:24-32`); chamada via `python3` elimina a classe do
  bit; guarda local e na CI (`check_canonical_edit.py:142`) contra só `shasum -c` na CI; o
  `check-rule-invariants.py` passa a consumir o módulo (+2 paths, MF-QA-R2-7).
- **R2-2 → FAIL nomeado, com protocolo de token** (MF-QA-R2-1). Armar por erro no adopter dá ≥ 3 FAIL enganosos
  (`_framework_manifest_set.sh:101`; `validate-governance.sh:1169-1178`); pular relaxa a guarda; FAIL nomeado não
  tem literal, compatível com a C12 sem isenção. Classes: ausente ⇒ FAIL; sem bit ⇒ irrelevante (via `python3`);
  import ⇒ FAIL; rc ≠ 0 ⇒ FAIL; STDOUT ilegível ⇒ FAIL; cada uma com vermelho. Aceito o fallback de Critic-A só com
  WARN nomeado a cada uso, teste de paridade por mutação e marca de isenção no censo; não prefiro.
- **R2-3 → (b)** (MF-QA-R2-6). Cobre as três leituras de cwd (`:600`, `:603`, `:610`) e cura a CLASSE «passa
  varrendo zero» (2.ª ocorrência, `CLAUDE.md` §4). FAIL no vácuo ADOTADO. A (c) só é aceitável declarando o
  resíduo: o checker segue passando no vácuo para outro chamador.
- **R2-4 →** a matriz acima, com o esperado de purga/KEPT, controles positivos, tag derivada pelo conteúdo e tempo
  medido (C38).

## Lacunas L1–L10 (lente QA)

- **L1 procede, e é pior.** `_round_dir` resolve só `debate/round-<N>` (`debate-converge.py:115-116`); no PLAN-183
  o `round-1` é o debate da S315. Risks em parágrafos ⇒ `RisksSectionEmptyError` (`:223`); uma delas era a MINHA
  crítica da rodada 1 (esta usa `- `). `_BULLET_RE` conta sub-itens (`:101`).
- **L2 procede: o gatilho não pode disparar como foi escrito.** Casamento por string inteira normalizada
  (`:120-133`, `:249-252`); o docstring admite que o Jaccard «PUNISHES cure» (`:278-283`), e a rodada 2 existe para
  curar; base inteira ≈ 0,23 (proposta). Se medir, base = recorte da W7b dos dois lados; mesmo assim, Red Team sem
  condição (MF-QA-R2-13).
- **L3** procede: `w7-round-2/red-team.md`, citado pelo consenso; o coletor o ignora (`:94`), e está certo.
- **L4** procede: FU no DEBATE-SCHEMA (§4 «Ordered list» × §12.2 `- `).
- **L5** procede (`PLAN-183:2546-2547` [disco]): o texto segue a R2-3.
- **L6:** marcador plantado é permitido como controle UNITÁRIO da lógica, nunca como substituto do checkout real.
- **L7** procede: +2 paths em (b) (MF-QA-R2-7); o FAIL nomeado tira o literal.
- **L8:** MF-QA-R2-3. **L9:** MF-QA-R2-5. **L10:** KEPT por construção + controle positivo de purga (MF-QA-R2-8).

## Esforço (ADR-081)

Construção da W7b com as MF-QA-R2: ~120–200k tokens, 1 sessão. Red Team: ~30–60k tokens, sem sessão extra. Pernas
P2 e P3 destacadas, tempo medido na abertura (C38). Nenhuma injeção observada; não li as outras críticas da rodada 2.
