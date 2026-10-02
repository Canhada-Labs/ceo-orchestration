---
plan: PLAN-183
round: 2
created_at: 2026-10-02T09:16:34Z
debate_dir: .claude/plans/PLAN-183/debate/w7-round-2/
previous_round: .claude/plans/PLAN-183/debate/w7-round-1/
scope: "só a onda W7b: R2-1 a R2-4; confirmar C11 a C14 e o ajuste 1"
plan_file: .claude/plans/PLAN-183-adopter-fitness.md
checked_at_head: e8ac8abaca1f
critics: [Critic-A, Critic-B, Critic-C]
veto_holder: "Critic-C (ADR-052, escopo de segurança); VETO CONDICIONAL ao local do predicado (MF-C-5)"
stop_rule: "C37: no máximo 2 rodadas por onda; sem PROCEED nesta rodada, ESCALATE-TO-OWNER"
red_team: "obrigatório se Jaccard(w7-round-1, w7-round-2) >= 0,7 (DEBATE-SCHEMA.md:410); a medida tem lacunas (§4, L1 a L3)"
budget_estimate: "60-100k tokens, até 1 sessão (estimativa de um crítico da rodada 1; ADR-081)"
---

# Proposta — PLAN-183, debate L3 da W7b, rodada 2

Esta rodada trata SÓ a W7b (UM predicado de repo-fonte + e2e de versão antiga), que o consenso da
`w7-round-1/` mandou a RUN-ANOTHER-ROUND. O veredito certifica só coerência de desenho (DEBATE-SCHEMA §13.1);
publicar segue a cascata V0 a V3. Repositório público: só classes e invariantes, nenhuma receita de contorno.

**Marcas.** `[V]` = verificado nesta edição no HEAD `e8ac8abaca1f`, 02/10/2026, com arquivo:linha. `[P:n]` =
lido no plano, linha n. `[C]` = afirmado por crítico ou pelo consenso, não re-executado. `[I]` = inferência
por leitura, não executada. De `399efbaa` (HEAD do consenso) a este HEAD só mudaram planos e docs [V].

**Formato.** As 7 seções do DEBATE-SCHEMA §4; em `## Risks`, UM risco por linha iniciada por `- `, única forma
que a medida lê (`DEBATE-SCHEMA.md:399`; §4 L1, L4). Responda R2-1 a R2-4 com opção e razão; confirme C11–C14.

## 1. O que já está decidido (fora do debate)

**Decisões do Owner** (não reabrem, consenso §5; discordância vira nota ao Owner, não Must-fix):
1. **Ordem.** A W7b segue logo depois da W7a, sem esperar a W1 do PLAN-183 (OQ-21, decisão 1) [P:2538-2540].
   Ela depende da W7a landada [P:2534]. [V] A W7a não landou: as fixtures seguem no caminho antigo e
   `.claude/hooks/_lib/harness_replay/` não existe (`check_harness_config.py:156`).
2. **Pacote que cria ADR.** Índice e contagens fora do teto de 8 paths, re-derivados no LAND; `CLAUDE.md:54`
   no pacote; um pacote de ADR por vez [P:2217-2237]. [V] `CLAUDE.md` = 39.912 bytes; 198 ADRs, último ADR-197.
3. **Gerais.** Patch sem rename; nenhum Check com medição paga; nenhuma data prometida (proposta da rodada 1, §1).

**Saíram PROCEED na rodada 1 e não reabrem:** W7a (C1–C10), W8 (C15–C22), W9 em W9a e W9b (C23–C32) e
W10 (C33–C36). Uma delas só reabre se um crítico mostrar um ajuste da §4 do consenso aplicado diferente do
texto. A C10 é da W7a: ela abre o FU do censo POR FORMA de «componente entregue lê por padrão caminho
excluído». O ADR da W7b declara esse resíduo pela forma, sem enumerar sítios [P:2554-2556].

**Condições convergentes da W7b.** Valem nesta rodada; o crítico confirma ou aponta defeito.
- **C11 — Cura do cwd completa** (`:600` E `:610`; a opção (a) pura saiu). Dois controles de OUTRO cwd: (i)
  semeado, acha antes e não depois; (ii) positivo, cópia velha de `audit_emit.py` em `REPO_ROOT/.claude`.
- **C12 — Predicado único.** Uma implementação, com CLI para o chamador bash. Teste-censo: nenhum outro
  arquivo re-deriva o marcador.
- **C13 — Controles no checkout REAL.** Predicado verdadeiro na raiz; cabeçalho PLAN-119 exatamente 1 vez no
  validador completo; renomear ou apagar o ADR-001 deixa a CI vermelha, também no `check-rule-invariants`;
  «0 linhas PLAN-119» no adopter exige a linha de resumo final; forma dogfood sem marcador dá WARN nomeado;
  o ADR declara o uso MONÓTONO (o predicado só ARMA verificações).
- **C14 — ADR novo.** `check-claude-md-claims.py` entra na bateria ([V] o script existe).
- **C37 e C38.** Parada por onda (§3). Medir antes de somar pernas: p95 previsto do job acima de 120 min
  manda o e2e histórico a um job próprio; subir o timeout não resolve.
- **Convergido sem número.** Marcador ADR-001, nunca `conftest.py` (3 de 3) [P:2319-2325].
- **Ajuste 1 aplicado.** [V] `PLAN-183:2130` diz agora que nenhuma INSTALAÇÃO nova entregou as fixtures e que
  o `upgrade.sh` da `v1.1.0` copiava `.claude/hooks` inteiro até `e718cd89`. Confirme o texto.

## 2. Questões abertas

### R2-1 — Onde mora o predicado (Q7b.1)

**Opções.** (a) `check-rule-invariants.py`, que entra no manifesto ADR-192 no MESMO pacote. Na rodada 1,
Critic-A escolheu (a) SEM o manifesto: essa forma dispara o VETO condicional (consenso, `:124-125`).
(b) Módulo novo em `.claude/hooks/_lib/`, preferido por Critic-C, portador de VETO. Critic-B é indiferente
ao local e exige a C12. O VETO condicional (MF-C-5) aceita as duas formas como escritas aqui.

**Fatos.**
- [V] O predicado já existe: `_PRIMARY_MARKER` em `check-rule-invariants.py:163` e `_is_framework_repo` em
  `:212-217` (`is_file()`). Marcador ausente devolve `skipped` com `ok: True` (`:242-252`).
- [V] O validador chama esse script só se ele for executável: `[ -x … ]` em `validate-governance.sh:997`.
  Sem o bit, o bloco inteiro some sem WARN. O modo rastreado hoje é 100755.
- [V] O manifesto tem 9 membros e não lista o `check-rule-invariants.py`. Quem o confere é `shasum -c` na CI
  (`smoke-install.yml:355-362`; também `release.yml`, `npm-publish.yml` e `ownership-nightly.yml`). Nenhum
  hook o lê, e nenhum teste fixa a contagem de membros.
- [V] O guard canônico cobre `.claude/hooks/_lib/*.py` (`check_canonical_edit.py:142`). Nenhum padrão da
  lista cobre `check-rule-invariants.py`. Lido na lista de padrões; o oráculo não foi re-rodado.
- [V] Há precedente de módulo `_lib/` com CLI chamado por bash: `_lib/runtime_paths.py:275` (`__main__`),
  usado em `templates/codex/pre-push-review-gate.sh:110`.
- [V] `.claude/hooks` e `.claude/scripts` são entregues (`_framework_manifest_set.sh:179-180`). Nas duas
  opções, o código do predicado chega ao adopter.
- [I] **Conta de paths.** Sob (b), a C12 obriga o `check-rule-invariants.py` a consumir o módulo, porque ele
  re-deriva o marcador em `:163`: são +2 paths, não +1 [P:2525-2526]. Totais estimados: (a) = 6;
  (a) com R2-3 (b) = 7; (b) = 7; (b) com R2-3 (b) = 8, no teto, sem folga para um arquivo de teste a mais.

**Critério de PROCEED.** Uma opção, com a razão de cada crítico. O portador de VETO declara o VETO fechado
para a opção eleita. A tabela de paths da W7b fecha em ≤ 8 com a combinação R2-1 × R2-3 escolhida.

### R2-2 — Falha ao avaliar o predicado

**Opções.** Critic-A: rc inesperado cai num teste de arquivo em bash, declarado como fallback, com aviso e
teste de paridade do literal (molde `install.sh:1527-1537`). Critic-C: erro ao avaliar ARMA o bloco ou dá
FAIL nomeado; nunca pula. Critic-B: sem posição na rodada 1.

**Fatos.**
- [V] O validador roda sob `set -euo pipefail` (`validate-governance.sh:2`). O bloco PLAN-119 chama Python
  entre `set +e` e `set -e` (`:1191-1194`). O validador invoca `python3` 18 vezes, sem checar se existe.
- [V] O molde de Critic-A é a cópia literal do predicado de entrega para checkout parcial, que o próprio
  comentário chama de «fail-open parity» (`install.sh:1527-1537`).
- [V] **Choque com a C12.** O literal do fallback re-deriva o marcador. Há precedente de censo com isenção
  marcada no código: `# rp-allow: partial-upgrade-fallback` (`SessionEnd.py:92`, `Stop.py:57`).
- [V] ARMAR num adopter dá ao menos 3 FAIL certos: o bloco exige `_lib/test_isolation.py`, que não é
  entregue (`_framework_manifest_set.sh:101`), e dois conftests de árvores excluídas
  (`validate-governance.sh:1169-1178`). FAIL nomeado dá 1 erro. O fallback de Critic-A dá verde com o
  marcador ausente.
- [I] Sob o uso monótono (C13), armar por erro só acrescenta verificação. Pular por erro relaxa uma guarda no
  repo-fonte.
- [V] `CLAUDE.md` §4 fixa fail-open em infraestrutura e fail-closed em input para hooks e matchers de
  segurança. Nenhuma regra escrita trata o predicado que ARMA um bloco do validador.

**Critério de PROCEED.** Cada classe de falha tem resultado escrito, no repo-fonte e no adopter: script
ausente, sem bit de execução, erro de import, rc fora de {0, 1} e saída ilegível. Nenhuma classe termina em
bloco pulado sem linha nomeada. A escolha é compatível com a C12: isenção marcada com teste de paridade, ou
nenhum literal. Cada classe tem controle vermelho.

### R2-3 — Cura do cwd (Q7b.3)

**Opções.** (b) Raiz explícita no `.py` (Critic-C; Critic-B aceita), com FAIL para zero raiz, zero arquivo
varrido e checker ausente no repo-fonte. (c) Subshell com cwd = `REPO_ROOT` e `.py` intacto (Critic-A;
Critic-B recomenda).

**Fatos.**
- [V] **São três leituras de cwd, não duas.** `check-test-audit-isolation.py:600` lê o `pytest.ini` de
  `Path(".")`. As raízes do `testpaths` e as do fallback são relativas (`:575`, `:591`) e se resolvem contra
  o cwd em `:603`. `:610` passa `Path(".")` ao WS-D2. Passar a raiz só ao leitor do ini não cura `:603`.
- [V] Raiz inexistente é pulada sem aviso (`:603-604`).
- [V] `REPO_ROOT` vem do caminho do script (`validate-governance.sh:17`). O arquivo não tem `cd`, e `:1192`
  chama o `.py` sem argumentos.
- [V] Chamadores do `.py` no repositório: só `validate-governance.sh:1192` e
  `test_check_test_audit_isolation.py:315`.
- [V] **2.ª ocorrência da classe.** `test_check_test_audit_isolation.py:303-306` registra que um cwd fora do
  repo fazia o gate varrer zero arquivos e passar no vácuo. Aquela cura foi no TESTE (`os.chdir`,
  `:311-317`), não no script. `CLAUDE.md` §4: 2.ª ocorrência pede cura estrutural.
- [I] «FAIL com zero arquivo varrido» exige mudar o `.py`: o `.sh` não vê o que o `.py` varreu (`:599-612`).
  «Checker ausente vira FAIL» muda o `.sh` (`validate-governance.sh:1201-1203`, hoje WARN) em qualquer opção.

**Critério de PROCEED.** A opção cobre as três leituras. Os controles da C11 saem vermelhos antes e verdes
depois. O FAIL no vácuo fica adotado ou rejeitado com razão escrita. A soma de paths com a R2-1 cabe no teto.

### R2-4 — Matriz do e2e (Q7b.5)

**Opções.** Critic-B, 4 pernas: (1) `v1.4.2`, ramo classificado; (2) árvore `.claude/hooks/tests/` herdada
como a `v1.1.0` a entregava; (3) fixtures criadas à mão no caminho antigo, idênticas e editadas; (4) ramo
legado sem manifesto de baseline. Critic-A: tag derivada + purge sobre os bytes da `v1.1.0`
(`git archive v1.1.0 -- .claude/hooks/tests`). Critic-C: `v1.4.2` + purge, com um arquivo editado que
sobrevive. Os três somam o tempo contra o teto do job.

**Fatos.**
- [V] A `v1.1.0` tem 549 arquivos em `.claude/hooks/tests`, `conftest.py` e as 3 fixtures incluídos. O
  `upgrade.sh` dela faz `backup_and_replace ".claude/hooks"` (linha 1348 da tag). `e718cd89` não é
  ancestral da `v1.1.0`; a 1.ª tag que o contém é a `v1.2.0-rc.1`.
- [V] O e2e não tem perna de `--purge-misinstalled` hoje (0 ocorrências em 2.385 linhas).
- [V] O purge só nomeia árvores excluídas (`upgrade.sh:4241-4242`). Ele autoriza um candidato só se o
  sha256 bate com a fonte ATUAL no MESMO relpath, ou com o digest do baseline; senão, KEPT (`:4194-4207`).
- [I] A W7a apaga as 3 fixtures do caminho antigo [P: tabela da W7a]. Depois dela, fixtures idênticas nesse
  caminho só saem se o baseline do alvo tiver o digest delas; sem ele, ficam KEPT. A perna (3) de Critic-B e
  o Check «o caminho do `--purge-misinstalled` também sai verde» [P:2551-2552] precisam declarar o esperado.
- [V] Sem manifesto de baseline, o upgrade cai no caminho legado de árvore inteira (`upgrade.sh:1940-1945`).
- [V] A tag derivada já existe no H.14 (`test-upgrade-historical-adopter.sh:895-923`). A CI busca
  `refs/tags/v*` com depth 1 (`smoke-install.yml:380`). O job tem `timeout-minutes: 150` (`:337`).
- [P:2202-2212] O e2e leva ~34 min. [C] ~2 min por perna e máximo de 92 min 32 s no job (Critic-A); não
  re-verificado.

**Critério de PROCEED.** Cada perna nomeia a população que representa e o resultado esperado, inclusive
KEPT ou purgado. Cada perna tem controle vermelho contra o HEAD pré-cura. A tag é derivada. O tempo somado é
medido na abertura, e a C38 decide o job próprio. A população da `v1.1.0` fica coberta ou excluída com razão.

## 3. Regra de parada e Red Team

- **Parada (C37).** Esta é a 2.ª e última rodada da W7b. Sem PROCEED, vale ESCALATE-TO-OWNER
  (`AskUserQuestion`, uma opção «(Recomendado)»), mesmo com um só crítico ou o VETO condicional abertos
  [P:2199-2201, 2261-2264].
- **PROCEED exige** zero Must-fix bloqueante e zero VETO aberto; R2-1 a R2-4 respondidas com razão; C11 a C14
  e o ajuste 1 confirmados; cada decisão traduzida em Check com controle vermelho; estimativa em tokens e
  sessões (ADR-081). Escala do veredito: `DEBATE-SCHEMA.md:243`.
- **Red Team (DEBATE-SCHEMA §12.3).** Convergência detectada na rodada N ≤ 2 obriga o Red Team ANTES de
  marcar o consenso (`DEBATE-SCHEMA.md:410-411`). Convergência é Jaccard ≥ 0,7 entre os conjuntos de risco
  de rodadas consecutivas (`:404-405`); aqui, `w7-round-1` × `w7-round-2`. O Red Team ataca o consenso, não
  a proposta, e a crítica dele entra no consenso da W7b. Bloqueio aberto por ele impede o PROCEED e aciona
  a C37. Medir cabe ao CEO, depois de fechar as lacunas L1 a L3 da §4.
- **Artefato terminal.** Quando a W7b fechar, o CEO grava `debate/w7-round-2/approved.md`, cobrindo as cinco
  ondas, com a ratificação do Owner (consenso §7). Nunca sob `architect/`, que é glob de sentinela.

## 4. Lacunas e contradições

- **L1 — A medida de convergência não roda nestes diretórios.** [V] `debate-converge.py:115-116` resolve só
  `debate/round-<N>`. Chamado em modo só leitura sobre `w7-round-1/`, o coletor recusa: uma das três críticas
  traz `## Risks` em parágrafos (`RisksSectionEmptyError`, `:185`, `:223`). As outras duas rendem 3 e 2
  bullets, todos sub-itens, não riscos.
- **L2 — Base de comparação indefinida.** [V] A rodada 1 tem 26 riscos, 6 deles da W7b. Se a rodada 2 repetir
  esses 6, o Jaccard contra o conjunto inteiro fica em 6/26 ≈ 0,23 e o gatilho nunca dispara. O consenso não
  diz se compara o conjunto inteiro ou o recorte da W7b.
- **L3 — Caminho da crítica do Red Team.** `DEBATE-SCHEMA.md:419` manda `round-<N+1>/red-team.md`, ou seja,
  `w7-round-3/`. A C37 para na rodada 2, e o consenso põe essa crítica no consenso desta rodada. Falta fixar
  o arquivo; o coletor ignora `red-team.md` (`debate-converge.py:94`).
- **L4 — O DEBATE-SCHEMA contradiz a si mesmo.** O §4 pede os riscos como «Ordered list» (`:166`); o §12.2 só
  conta linhas `- ` (`:399`). Seguir o §4 deixou uma crítica invisível à medida.
- **L5 — Resto da opção (a) pura no AC.** [V] `PLAN-183:2546-2547` ainda diz «o WS-C recebe as raízes a
  partir do `REPO_ROOT`», a forma que o ajuste 11 tirou.
- **L6 — Marcador plantado.** [V] A tabela diz «o marcador arma» no teste de fronteira (`PLAN-183:2508`); a
  C13 diz «nunca com marcador plantado». Falta dizer se a perna plantada é extra permitida ou proibida.
- **L7 — A C12 pesa sobre R2-1 e R2-2.** Ela soma o `check-rule-invariants.py` à opção (b), que o plano
  conta como +1 path [P:2525-2526]; e o literal do fallback de Critic-A re-deriva o marcador sem isenção prevista.
- **L8 — Escopo do censo da C12.** [V] O nome do arquivo do ADR-001 aparece também em
  `.claude/adr/README.md:254` (entregue ao adopter), em `test_bash_canonical_interceptor.py:47-50` e em
  `test_check_rule_invariants.py:72,145,173` (marcador plantado em tmp). Falta definir o que conta como
  «re-derivar».
- **L9 — Bit de execução.** A C13 cobre renomear ou apagar o ADR-001. Ela não cobre a perda do bit de
  execução nem a remoção do `check-rule-invariants.py`, que hoje somem sem WARN (`validate-governance.sh:997`).
- **L10 — Esperado do purge depois da W7a.** O Check do purge [P:2551-2552] não diz o que acontece com
  fixtures idênticas no caminho antigo depois que a fonte as apaga (§2, R2-4).

## 5. Glossário

**WS-C / WS-D2** — varredura dos testes e busca de cópias velhas de `audit_emit.py` no checker do PLAN-119.
**Manifesto ADR-192** — scripts de gate pinados por sha256; editar um membro passa pela cerimônia.
**Jaccard** — |A ∩ B| / |A ∪ B| entre riscos normalizados de duas rodadas. **Red Team** — arquétipo
contingente que ataca o consenso. **Uso monótono** — o predicado só arma verificações, nunca relaxa guarda.
