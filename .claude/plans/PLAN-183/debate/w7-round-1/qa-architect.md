---
round: 1
archetype: QA Architect
skill: testing-strategy
agent_persona: Principal QA Architect
served_model: claude-opus-5-5
generated_at: 2026-10-02T06:10:00Z
plan: PLAN-183
plan_commit: 304ec47805e5
waves_in_scope: [W7a, W7b, W8, W9, W10]
wave_verdict:
  W7a: PROCEED
  W7b: RUN-ANOTHER-ROUND
  W8: PROCEED
  W9: PROCEED
  W10: PROCEED
p0_found: false
false_claims_found: 1
inputs: [w7-round-1/proposal.md, PLAN-183 §«Waves S359» @ 304ec478 (idêntico ao 092377af), DEBATE-SCHEMA.md §4]
---

# PLAN-183 W7a–W10 — rodada 1 — crítica do QA Architect

> **Legenda.** **[disco]** li no HEAD `304ec478`. **[medido]** sonda minha, em diretório temporário meu, com o
> ambiente hermético do próprio gate (HOME e sink de auditoria temporários); `git status` igual antes e depois;
> nada gravado no repo. **[não verificado]** não conferi.

## Verdict

**ADJUST** — W7a **PROCEED** (`design-coherent`) com MF-QA-1..7. W7b **RUN-ANOTHER-ROUND** (1 afirmação FALSA
que sustenta a matriz do e2e, e a partida da Q7b.3 incompleta). W8, W9 e W10 **PROCEED** com condições.
Nenhum P0. Nenhuma onda fica refém de outra: a W7a não depende de nada do que reprovo na W7b.

## Summary (≤ 3 bullets)

- **Forte.** A W7a tem controles vermelhos reais. Medi que o replay É controle não vácuo da leitura do
  marcador: com o marcador NÃO substituído, `check_canonical_edit.py` devolve `{}` e o replay fica RED
  [medido, 3 variantes]. O delete+add com `--no-renames` e o vermelho do passo S estão certos.
- **Fraco.** Três vácuos nos Checks da W7a: (1) o pytest do hook NUNCA exercita o caminho padrão
  (`test_check_harness_config.py:51-53` fixa a pasta e todo teste a passa explícita, `:248-303`); (2) com
  `CEO_SOTA_DISABLE=1` o gate pula o replay e sai rc 0 imprimindo `replay=yes` (`check_harness_config.py:733-740`,
  `:923-928`); (3) uma chamada ao predicado bash que falha ao carregar lê-se como «não excluído».
- **Classe maior que o exemplo.** Há 4 gramáticas de placeholder (não 2), 4 cópias do predicado de entrega
  (npm ×2, plugin, purge) e ≥3 outros componentes entregues que leem por padrão árvore excluída.

## Risks

**R-QA1 — W7a, HIGH. Caminho padrão sem teste no pytest.** `_REPLAY_FIXTURES` é literal (`test:51-53`) e
`run_replay` sempre recebe a pasta (`test:251,288,297`). Um `REPLAY_FIXTURES_REL` errado passa no pytest; só o
gate sem argumentos (CI `validate.yml:1146`, `/ceo-boot`) o vê. Mitigação: MF-QA-1.

**R-QA2 — W7a, HIGH. Verde no vácuo pelo kill-switch.** `run_replay` devolve 1 WARN sob `CEO_SOTA_DISABLE=1`
(`:733-740`); o CLI sai 0 com `replay=yes` (`:923-928`). O Check «rc 0 com os 3 controles exercitados» passa
sem exercitar nada se a variável vazar para a bateria (é a rota de recuperação documentada). Mitigação: MF-QA-3.

**R-QA3 — W7a, MEDIUM. Asserção estrutural que lê falha de carga como «entregue».** Se o `source` de
`_framework_manifest_set.sh` falhar, a função não existe, o rc é 127 e um `if` ingênuo responde «não
excluído». O próprio `install.sh:1532-1537` mostra o fallback quando a função falta. Mitigação: MF-QA-2.

**R-QA4 — W7b, HIGH. Matriz do e2e apoiada em afirmação FALSA.** `PLAN-183:2130` diz «nenhuma versão entregou
as fixtures». O `upgrade.sh` da `v1.1.0` faz `backup_and_replace ".claude/hooks"` (`git show v1.1.0:scripts/upgrade.sh`,
linha 1348) e a `v1.1.0` tem as 3 fixtures em `tests/` (`git ls-tree v1.1.0`) [disco]. Existe uma população com
a árvore de testes INTEIRA herdada (conftest incluído), que a perna só-`v1.4.2` não cobre. Mitigação: R2-a.

**R-QA5 — W7b, MEDIUM. A partida (a) da Q7b.3 deixa o WS-D2 preso ao cwd.** `check-test-audit-isolation.py:610`
chama `check_stale_audit_emit_copies(Path("."))`; passar raízes só cura `:600`. E passar as 3 raízes de fallback
regride o P1 do Codex de `:569-572` (menos raízes que o pytest). Mitigação: R2-b.

**R-QA6 — W9, HIGH. P4 aviso no Bash pode sombrear o P5.** `_eval_predicates` devolve o 1.º que dispara
(P1>…>P4>P5, `:499`); o caminho do apply-step re-avalia com `skip_p4=True` (`:696-708`, lição r17). O plano
não pede o mesmo no Bash, e o Check do US6 não testaria o sombreamento. Mitigação: MF-QA-11.

**R-QA7 — W9, MEDIUM. Ordem do override.** `if override_env` (`:673`) vem ANTES do ramo de aviso (`:696`):
com ACK, o evento de override sai até para P4 que não bloquearia. O Check «exatamente 1 evento» supõe essa
ordem e audita um override de algo que não é mais bloqueio. Mitigação: MF-QA-12.

**R-QA8 — W9, MEDIUM. Teto só na mensagem de detecção.** `", ".join(files)` aparece em 6 ramos
(`codex_review_user_code.py:303,311,315,322,330,335`); o plano cita só `:301-303`. Mitigação: MF-QA-13.

**R-QA9 — W8, MEDIUM. NOTE do `VERSION` vira ruído.** O Check não tem a perna «`VERSION` do app» (a população
majoritária, `ADR-155-AMEND-1:52-54` segundo a proposta [não verificado]). Mitigação: MF-QA-9.

## Must-fix (blocking)

**(a) P0 / afirmação FALSA — bloqueiam só a W7b.**

1. **R2-a [W7b] Corrigir `:2130` e refazer a matriz (Q7b.5).** Pernas: (1) `v1.4.2` (ramo classificado,
   `upgrade.sh:1945`); (2) alvo com a árvore `.claude/hooks/tests/` herdada como a `v1.1.0` a entregava ⇒ PLAN-119
   desarmado, gate verde, purge remove só o que bate hash; (3) fixtures criadas à mão no caminho antigo: bytes
   idênticos ⇒ purge remove, editadas ⇒ preservadas; (4) ramo legado sem manifesto de baseline. Medir o tempo
   somado contra os 150 min do job (regra comum 12).
2. **R2-b [W7b] Q7b.3: fixar (c) ou (b), nunca (a) puro.** Recomendo (c): o `.sh` invoca o `.py` com cwd =
   `REPO_ROOT` (subshell), `.py` intacto, cura `:600` e `:610` sem copiar o parser do `pytest.ini`. O controle
   «outro cwd» tem de ser SEMEADO (cwd com `pytest.ini` → teste que o checker acusa + cópia velha de
   `audit_emit`): pré-cura acha, pós-cura não. Sem semente, «mesmo resultado» é vácuo.
3. **R2-c [W7b] Q7b.2: controle «armado no repo-fonte».** Teste da suíte do repo-fonte afirma predicado = True
   no `REPO`, e o CI afirma que a linha `--- PLAN-119 audit-isolation gate` sai exatamente 1 vez no validador
   completo. Apagar ou renomear o ADR-001 ⇒ vermelho (é a intenção de `validate-governance.sh:1159-1164`).
4. **R2-d [W7b] Q7b.1 fechado antes do Scope:** uma implementação, CLI para o `.sh`, e teste-censo de que
   nenhum outro arquivo re-deriva o marcador (molde M4 do ADR-001). O Check «0 linhas PLAN-119» exige também a
   linha de resumo final do validador (ausência só prova algo se o validador chegou ao fim).

**(b) Condições de execução (não bloqueiam o PROCEED da onda).**

- **MF-QA-1 [W7a; builder]** O teste deriva a pasta de `chc.REPLAY_FIXTURES_REL` (fonte única) e ≥1 teste chama
  `run_replay(_REPO)` sem `fixtures_dir`. Vermelho: constante apontando para pasta inexistente ⇒ esse teste RED.
- **MF-QA-2 [W7a; builder]** Asserção estrutural: confirma que a função existe; rc EXATO (0 excluído, 1
  entregue; qualquer outro = falha do teste); controle positivo no mesmo run (caminho antigo ⇒ rc 0).
- **MF-QA-3 [W7a; CEO no LAND]** As duas pernas (verde e vermelha) rodam com `CEO_SOTA_DISABLE` removido do
  ambiente; verde casa a linha inteira com `0 warning(s)`; vermelha = exatamente 3 RED, todos `MISSING`.
- **MF-QA-4 [W7a; CEO no LAND]** Além do comando do plano (que roda o hook da FONTE contra o alvo), rodar o hook
  ENTREGUE no contrato do `/ceo-boot`: cwd = alvo, sem argumentos (`ceo-boot.py:2559-2563`). Registrar o tempo
  contra o teto de 2,5 s (`:2518`); medi o replay sozinho em p50 0,99 s (n=5, este Mac, 02/10) [medido].
- **MF-QA-5 [W7a; builder]** Critério do marcador = nenhuma gramática da família que varre o entregue:
  `install.sh:3067-3073` (ERE, `.md`/`.py`, exit 4 sob `--strict-placeholders`), `:3834` (BRE, todo arquivo),
  `test_install_sh_placeholders.py:83-84` (duas). Critério de classe mais simples: a forma nova não contém `{{`.
  O hook aceita SÓ a forma nova; teste: fixture com a forma antiga ⇒ replay RED. Na bateria, o conjunto de
  arquivos acusados pelos dois scans do install é IGUAL antes e depois, e o grep cobre `<alvo>/.claude` inteiro.
- **MF-QA-6 [W7a; CEO no LAND]** Canais (Q7a.4): npm = `bash scripts/install-npm.sh --smoke --keep` na bateria,
  os 3 paths no packlist e `cmp` no alvo do smoke (rede do `npx` [não verificado]); plugin = declarar «inerte, sem
  consumidor» (abaixo); upgrade = smoke barato `v1.4.2` (`git archive`) → `upgrade.sh` curado → `cmp` + gate rc 0
  (minutos, não o e2e de 34 min; o e2e permanente fica na W7b).
- **MF-QA-7 [W7a; CEO]** Dois FU nomeados ANTES do fechamento da W7a (não «se valer»): censo POR FORMA de
  «entregue lê por padrão caminho excluído» e unificação do «predicado de entrega copiado». O ADR declara só a forma.
- **MF-QA-8 [W8; builder]** `.mcp.json`: (i) template antigo ⇒ troca + backup `cmp` aos bytes antigos; (ii)
  template atual ⇒ no-op sem backup; (iii) variante CRLF ou sem `\n` final do antigo ⇒ aviso, intocado; (iv)
  symlink e hardlink ⇒ recusa nomeada, arquivo externo `cmp`-idêntico (Q8.4); (v) 2.º upgrade ⇒ no-op, sem 2.º
  backup. O teste de pins fecha nos DOIS sentidos (hash listado que não é geração ⇒ exit 1); o de schema hoje só
  acusa a falta [disco: nenhuma checagem reversa em `test-schema-generation-pins-unit.sh`].
- **MF-QA-9 [W8; builder]** NOTE só quando o `VERSION` é igual a uma versão LANÇADA do framework e difere de
  `.framework-version`. Perna nova: `VERSION` do app ⇒ sem NOTE.
- **MF-QA-10 [W8; builder]** `_dispatch.md`: gerar o arquivo ARMA o `--validate` no adopter
  (`validate-governance.sh:800-806`; sem ele, só WARN em `:810`). Pernas: agente custom malformado ⇒
  upgrade não aborta, aviso nomeado, resultado do validador registrado; `_dispatch.md` editado à mão ⇒ política
  escolhida e testada; `_dispatch.md` symlink ⇒ recusado ANTES do filho Python (fora do censo bash).
- **MF-QA-11 [W9; builder]** No Bash, o ramo de aviso do P4 re-avalia com `skip_p4=True`. Teste: janela com
  condição de P5 + rajada de grep, chamada Bash ⇒ BLOCK por P5; P1–P3 e P5 seguem bloqueando no Bash.
- **MF-QA-12 [W9; CEO no desenho]** Aviso do P4 avaliado ANTES do override ⇒ 0 eventos de override para P4; o
  Check de dedup migra para um predicado que ainda bloqueia (P5), vermelho pré-cura = N. A queda da contagem de P4
  (`ADR-127:158`) fica PINADA por teste (nenhum evento) e declarada, com FU da ação auditada nova (Q9.3).
- **MF-QA-13 [W9; builder]** Teto por BYTES, não por N (paths longos e multibyte); um formatador único para os 6
  ramos; teste percorre todos os ramos com ≥1.000 arquivos; ordem determinística; `mostrados + K == total`.
- **MF-QA-14 [W9; builder]** Estado: arquivo no formato antigo ⇒ sem exceção, 1 reaviso, depois silêncio;
  escrita atômica; path apagado ou renomeado. Modo AUTO: arquivo além do `DIFF_CAP` (`:117`) não vira «reviewed»
  sem ter sido enviado. Latência do Stop com 1.000 e 1.622 arquivos contra o timeout de 130 s
  (`templates/settings/settings.base.json:519`): morte por timeout = falha aberta silenciosa.
- **MF-QA-15 [W10; builder]** `<nível>/<skill>` vale só quando `<nível>` é o tier de `resolve_skill`. Pernas:
  `core/pii-data-flow` aceita, `frontend/pii-data-flow` segue avisando, nome curto aceita, forma de domínio
  definida. O Check afirma o CONJUNTO exato das 5 linhas de aviso, não a contagem.
- **MF-QA-16 [W10; builder]** Política lida por modo novo do parser (+2 paths: parser e teste; W10 = 5), nunca
  por parse inline em bash. Guarda de deriva: membros da política == skills do yaml depreciado (hoje 5 = 5
  [disco]). Mensagem com razão literal fixa.
- **MF-QA-17 [todas; CEO]** Regra de parada do DEBATE por onda, fixada agora: no máximo 2 rodadas; sem PROCEED na
  2.ª, ESCALATE (L10). Vale para a W7b já.

## Nice-to-have (advisory)

1. Teste que fixa a OQ-12: `_lib/harness_replay/` só com `.json` e sem `__init__.py`. Um `__init__.py` mexeria
   na contagem recursiva de `_lib/**/*.py` (`.claude/scripts/local/verify-counts.sh:203-206`).
2. Dividir a W9 em W9a (A4) e W9b (A5): achados de desenho independentes; o rail de uma não segura a outra.
3. Plugin: Security avalia excluir `harness_replay` do `build-plugin.py` (sem consumidor; o comentário de
   `:338-341` já exclui `fixtures` por heurística de instalação). Seria path novo ⇒ FU, não W7a.

## Unseen by the original plan

1. Nenhum pytest exercita `REPLAY_FIXTURES_REL` (R-QA1); replay pulado sai rc 0 com `replay=yes` (R-QA2).
2. São 4 gramáticas de placeholder, e uma delas reprova a instalação (exit 4) sob `--strict-placeholders`.
3. O canal plugin não tem consumidor das fixtures: o `/ceo-boot` roda `.claude/scripts/ceo-boot.py`
   (`.claude/commands/ceo-boot.md:39`), que o plugin não entrega (`build-plugin.py:456-470`), e o gate procura os
   hooks em `repo_root/.claude/hooks` (`check_harness_config.py:783`).
4. O predicado de entrega tem cópias: `npm-publish.yml:317-330`, `install-npm.sh:116-130`, `build-plugin.py:342-345`,
   purge `upgrade.sh:4241-4242` (A1-F4). «UM predicado» vale só para install e upgrade.
5. Outros membros da classe da W7: `hook-profiler.py:39,115`, `ceo-diagnose.py:296`,
   `check-test-env-hygiene.py:58-59` [disco, grep; consequência no adopter não medida].
6. `check-test-audit-isolation.py:610` também lê o cwd (R-QA5). O sombreamento do P5 e a ordem do override no
   anti-overhead (R-QA6, R-QA7). Os 6 ramos sem teto e a semântica do modo AUTO no RISKY DIFF (R-QA8, MF-QA-14).
7. Gerar `_dispatch.md` arma o `--validate` no adopter (MF-QA-10).

## What I would NOT change

- Delete+add com `--no-renames` em TODA listagem que compara conjuntos, com o vermelho do passo S e o ensaio do
  LAND completo (não `--dry-run`).
- Fixtures no caminho entregue, fail-closed intacto, sem `__init__.py`; recodificar o marcador em vez de isentar o
  caminho no teste.
- A bateria da W7a com os testes do `check_bash_safety.py` (R3 da proposta) e o `test_install_sh_placeholders.py`
  com vermelho demonstrado.
- Gerações do `.mcp.json` derivadas do git com controle de mutação; `VERSION` sem escrita; P4 vira aviso em vez de
  limiar maior; chave de dedup calculada antes de truncar.

## Respostas às perguntas (lente QA)

- **Q7a.1** (a) 8+1, código primeiro: a emenda cita o vermelho→verde já registrado; ADR primeiro descreveria
  estado inexistente se o código cair no rail.
- **Q7a.2** Aditiva do ponto de vista do comportamento testado: conjunto de controles e fail-closed intactos
  (`test:248-292` seguem). Condição de texto: declarar `:60` superado, como `ADR-158:167` faz.
- **Q7a.3** Não basta: são 4 gramáticas (MF-QA-5). O hook aceita SÓ a forma nova. Medi que o replay é controle
  não vácuo da leitura: marcador não substituído ou fora da raiz ⇒ `{}` ⇒ RED [medido].
- **Q7a.4** (i) O PROCEED não exige; a bateria exige o smoke barato de upgrade (MF-QA-6), porque a população do
  campo é de upgraders e a entrega foi só LIDA. (ii) npm sim, plugin só declarado. (iii) Sim, mas como prova de
  canal (staging real), não cópia do padrão. O `_framework_path_excluded` não representa npm nem plugin.
- **Q7a.5** Na W7a, `REPLAY_FIXTURES_REL` com helper reutilizável (MF-QA-2). Medi ≥3 outros membros (Unseen 5):
  é 2.ª ocorrência e o censo POR FORMA vira FU obrigatório (MF-QA-7). Lista declarada à mão envelhece.
- **Q7a.6** Lente de Security. QA: sem objeção técnica; o plugin não tem consumidor (Nice 3).
- **Q7b.1** Indiferente o arquivo; exijo uma implementação, CLI e censo anti-recópia (R2-d). **Q7b.2** Sim,
  desarma em silêncio hoje; controle em R2-c. **Q7b.3** (c) ou (b), nunca (a) puro (R2-b). **Q7b.4** Fora da
  lente; `check-claude-md-claims.py` na bateria se o ADR for novo. **Q7b.5** Matriz em R2-a.
- **Q8.1** Trocar por hash: determinístico e testável (MF-QA-8). Prefiro incondicional à sonda de versão; com
  sonda, `codex` falso no PATH nos dois ramos. **Q8.2** MF-QA-10. **Q8.3** Só aviso, com a condição de MF-QA-9.
  **Q8.4** Sim, os dois pelo predicado, com perna em bytes; backup de raiz no diretório de backup do upgrade.
- **Q9.1** Aviso permanente, com detecção pinada por teste. **Q9.2** Manter a partida. **Q9.3** MF-QA-12.
  **Q9.4** Teto por bytes; estado `{path: sha256}`; formato antigo = vazio (MF-QA-13, MF-QA-14). **Q9.5** Dividir.
- **Q10.1** Não fundir por padrão: os tetos somam 300 + 120 = 420 > 400. Fundir só com soma medida ≤ 400. Os dois
  testes do validador entram na bateria de TODO pacote que toque `validate-governance.sh`. **Q10.2** Tier exato
  (MF-QA-15). **Q10.3** Modo do parser (MF-QA-16).

## Lacunas L1–L12 (lente QA)

L1 **procede, FALSA** (R-QA4). L2 procede: só texto, comportamento aditivo. L3 procede: re-estimar abaixo. L4
procede, mais `test_check_harness_config.py:7,51-53` (já no pacote). L5 procede em parte: a 2.ª regex não reprova
nenhum teste (o teste de arquétipo só exige ocorrências), mas há 4 gramáticas no total. L6 procede (MF-QA-6). L7
procede e é maior (R-QA6, R-QA7). L8 procede; a política não alarga o conjunto (5 = 5). L9 procede (MF-QA-8,
MF-QA-10). L10 procede (MF-QA-17). L11 e L12: fora da lente.

## Checks: vermelho antes, verde depois? (`304ec478`)

| onda | Check | antes | depois | não vácuo? |
|---|---|---|---|---|
| W7a | pytest do hook | verde | verde | **não** para o caminho padrão (MF-QA-1) |
| W7a | gate no alvo instalado | 3 RED | rc 0 | sim, com MF-QA-3 e MF-QA-4 |
| W7a | entrega exata, sem `__init__.py` | pasta ausente | 3 `.json` `cmp` | sim |
| W7a | asserção estrutural | — | verde | sim, com MF-QA-2 |
| W7a | placeholders | reprova (lido, não executado) | verde | sim, com MF-QA-5 |
| W7a | ADR-158 | — | oráculo 1, 198 ADR | só forma; texto via Q7a.2 |
| W7b | dogfood boundary | FAIL PLAN-119 | 0 linhas | só com R2-b, R2-c, R2-d |
| W7b | e2e de versão antiga | 3 RED | verde | incompleto (R2-a) |
| W8 | pernas do `.mcp.json`, `VERSION`, `_dispatch.md` | vermelho | verde | sim, com MF-QA-8..10 |
| W9 | P4 aviso; dedup | block; N | aviso; 1 | P5 não testado; dedup mal posto (MF-QA-11, 12) |
| W9 | teto; delta | > 80 KB; silêncio | ≤ 2.048; aviso | só 1 de 6 ramos (MF-QA-13, 14) |
| W10 | 5 avisos | 5 | 0 | sim, se por conjunto (MF-QA-15) |

## Ajustes de texto (c)

1. `:2130`: estreitar como em `resposta-ao-campo-1.4.2.md:396-399` (é o item FALSO de (a)).
2. Proposta R6: os adopters ficam vermelhos até um CORTE levar a W7a; a W7b prova, não cura.
3. `:2413`: «3 controles exercitados» não aparece na saída (`:923-928`); dizer «sem RED, `0 warning(s)`».
4. `:2419`: «rc exato, com controle positivo no mesmo run». `:2302`, `:2771-2772`: re-estimar a W7a (2 pacotes).

## Esforço (ADR-081)

| item | esforço |
|---|---|
| MF-QA-1..7 (W7a) | +40–80k tokens no pacote de código; smoke npm e upgrade = minutos de máquina; sem sessão extra |
| pacote da emenda ADR-158 | 40–80k tokens, +1 sessão (rail + GPG) |
| W7b rodada 2 (R2-a..d) | 60–100k tokens, ≤ 1 sessão; e2e com pernas novas destacado, até 2 h |
| MF-QA-8..10 (W8) | +60–100k tokens |
| MF-QA-11..14 (W9) | +40–80k tokens; dividir = +1 rail e +1 GPG |
| MF-QA-15..16 (W10) | +20–40k tokens, +2 paths |

Sem espera externa nova; nenhuma injeção observada; não li outras críticas; predicado bash lido, não executado.
