---
round: 1
archetype: DevOps Engineer
skill: devops-ci-cd
agent_persona: "DevOps Engineer (Principal) — entrega install/upgrade, canais npm e plugin, CI e e2e longos"
served_model_id: claude-opus-5-5
generated_at: 2026-10-02T06:10:00Z
plan: PLAN-183
plan_commit: 304ec47805e5
waves_in_scope: [W7a, W7b, W8, W9, W10]
wave_verdict:
  W7a: PROCEED
  W7b: PROCEED
  W8: PROCEED
  W9: PROCEED
  W10: PROCEED
p0_found: false
inputs:
  - .claude/plans/PLAN-183/debate/w7-round-1/proposal.md
  - .claude/plans/PLAN-183-adopter-fitness.md (seção «Waves S359», :2036-2903)
---

> **Legenda.** [disco] = conferido por mim no HEAD `304ec478` (o diff `092377af..304ec478` não toca o
> PLAN-183 nem a proposta). [plano :N] = PLAN-183. [inferência] = dedução minha. [não verificado] = não
> conferi. Estimativas em tokens e sessões (ADR-081). Nenhum conteúdo lido trouxe instrução dirigida a mim.
> Regra aplicada: RUN-ANOTHER-ROUND só por P0 ou afirmação FALSA que sustente decisão da onda.

## Verdict

**ADJUST**: as cinco ondas recebem **PROCEED** (`design-coherent`), todas com condições de execução. Não
achei P0.

**W7a (prioritária, veredito autônomo): PROCEED.**
- Divisão 8+1, código primeiro e ADR-158 depois, na mesma vaga (Q7a.1, opção (a)).
- A entrega do caminho novo está correta no código [disco]: install (`install.sh:1520-1550`, `cp -R` em
  `:1364-1368`); upgrade com baseline (`ADDED`, `upgrade.sh:1787-1815`) e sem baseline (ramo legado,
  `:1997-2010`). npm e plugin excluem por NOME de segmento (`npm-publish.yml:322`, `install-npm.sh:121`,
  `build-plugin.py:342-343`), e `harness_replay` não casa.
- Nenhuma afirmação falsa sustenta decisão da W7a. Viram condição: a asserção testa «não excluído», não
  «entregue» (MF-DEVOPS-2); a 1.4.3 leva a W7a sem a W7b (`PLAN-194:138-139`), com o upgrade só LIDO
  (MF-DEVOPS-4).

**W7b: PROCEED.** O predicado mora em `check-rule-invariants.py` (Q7b.1 (a)). A cura do cwd é um
subshell no chamador, que cobre as DUAS leituras de cwd (`check-test-audit-isolation.py:600`, `:610`).

**W8: PROCEED, com o maior lote de condições (MF-DEVOPS-9..13):** o gerador do `_dispatch.md` resolve a
raiz por `CLAUDE_PROJECT_DIR` ou cwd (`generate-dispatch.py:46-50`), e o precedente do hash-gate não serve
ao `.mcp.json` como está.

**W9: PROCEED** na minha lente (custo do Stop hook, estado). O mérito do P4 é de Security e de Threat Detection.

**W10: PROCEED** (L2), sem fundir na W7b.

## Summary (≤ 3 bullets)

- **O que o plano faz:** fixtures num caminho ENTREGUE (W7a); um predicado de repo-fonte e upgrade
  provado desde versão antiga (W7b); aposentar semeados (W8); hooks mais baratos (W9); validador (W10).
- **Forte:** `_lib/harness_replay/` dispensa mexer no instalador; `--no-renames` tem precedente
  (`OWNER-GA-CUT.sh:1577`, `OWNER-RC1-CUT.sh:1140`), e o passo S do molde S326 enumera sem a flag
  (`OWNER-S326-LAND.sh:292`) [disco]; o hash do `.mcp.json` prova a origem (2 gerações em 20 tags,
  1.204 bytes, zero `{{`, copiado sem alteração).
- **Fraco:** upgrade e canais só LIDOS; o caminho PADRÃO do replay não tem teste unitário; duas escritas
  novas do upgrade nascem fora do predicado de confinamento.

## Risks

1. **R-DO1 — HIGH — W8 — o `_dispatch.md` pode ser escrito FORA do alvo.** O gerador usa
   `CLAUDE_PROJECT_DIR` ou o cwd (`:46-50`), cria o diretório (`:394`) e grava com `write_text` (`:395`),
   que segue symlink e hardlink. Rodado numa sessão do Claude Code de OUTRO projeto, o upgrade regenera o
   arquivo desse projeto; o alvo fica sem nada, e o e2e da CI (sem a variável) sai verde. → MF-DEVOPS-10.
2. **R-DO2 — MEDIUM — W7a — a 1.4.3 leva a cura do A1 com o upgrade não executado.** Os adopters
   ≥ v1.1.0 recebem a cura pelo UPGRADE; o plano só o prova na W7b [plano :2349-2351], fora do núcleo da
   1.4.3 (`PLAN-194:138-139`). → MF-DEVOPS-4.
3. **R-DO3 — MEDIUM — W7a — a asserção e a emenda prometem mais do que testam.**
   - `_framework_path_excluded` (`_framework_manifest_set.sh:95-107`) responde só «não excluído».
   - O MESMO hook lê por padrão `templates/settings/settings.base.json` (`check_harness_config.py:168-171`,
     `:897`). `templates/` não é entrada entregue (`_framework_manifest_set.sh:112-200`), mas o predicado o
     dá como «não excluído». Ausente, ele dá WARN (`:620-623`), com rc 0 (`:918-929`).
   - Uma emenda que diga, sem exceção, que o gate só lê caminho entregue sai falsa no dia do land.
     → MF-DEVOPS-2 e MF-DEVOPS-3.
4. **R-DO4 — MEDIUM — W8 — copiar o `_refresh_schema_doc` (`upgrade.sh:4379-4456`) como está erra três
   vezes:** instala o ausente (`:4416-4421`); registra a entrega (`_rsd_mark_delivered`); não recusa
   hardlink, embora a primitiva exista (`_up_tpl_multilink_refuses`, `:4983`). → MF-DEVOPS-9.
5. **R-DO5 — MEDIUM — W7b/W8 — orçamento do job `smoke`.** Máximo medido 92m32s
   (`smoke-install.yml:302-314`); o run de 29/09 durou 1h36 [plano :2200-2204]; a regra da casa é 20% de
   folga sobre 150 min (`:326`). W7b + W8 somam ≥ 6 pernas, a ~2 min cada (34 min / 17 installs)
   [inferência]. → MF-DEVOPS-8.
6. **R-DO6 — LOW — W7b — cura do cwd pela metade passa por vácuo.** O WS-D2 lê `Path(".")` (`:610`) e
   devolve `[]` quando o cwd não tem `.claude` (`:545-547`). → MF-DEVOPS-6.
7. **R-DO7 — LOW — W9 — numa worktree, o estado do dedup cai na raiz do working tree.** Com `.git`
   arquivo, `_state_path` cai no cwd (`codex_review_user_code.py:140-143`) e o estado entra no
   `ls-files --others` (`:79`). → MF-DEVOPS-14.

## Must-fix (blocking)

Nenhuma bloqueia o PROCEED. São condições de execução, com onda e momento.

1. **MF-DEVOPS-1 [W7a, abertura] — Ordem e assinatura.** O pacote do ADR-158 é derivado DEPOIS que o rail
   do código converge (cita a forma e o caminho landados). Os dois sentinels podem ser assinados na MESMA
   sessão do Owner (o land do código não muda a base do ADR); ordem: LAND do código, depois LAND do ADR. A
   emenda não toca título nem `**Status:**`; bateria com `generate-adr-index.py --check` rc 0 e contagem
   de `ADR-*.md` igual.
2. **MF-DEVOPS-2 [W7a, teste] — A asserção testa «ENTREGUE».**
   - Entregue = coberto por uma entrada de `_framework_target_entries` e não excluído, por chamada REAL ao
     bash.
   - Cobre os padrões do hook (`REPLAY_FIXTURES_REL` e `DEFAULT_SETTINGS_REL`): o padrão cuja AUSÊNCIA dá
     RED tem de ser entregue; o que só dá WARN fica numa lista declarada.
   - Controles vermelhos: um caminho em `templates/` e o caminho antigo.
   - Proíbe segmento `tests` ou `fixtures` no caminho do replay, como espelho DECLARADO dos canais.
3. **MF-DEVOPS-3 [W7a, emenda] — A regra vai pela FORMA, com a exceção declarada.**
   - Regra: «padrão de leitura cuja ausência deixa o gate VERMELHO pertence ao conjunto entregue».
   - Exceção: o insumo só do repo-fonte cai em WARN.
   - O AC-11 lê «rc 0, zero RED» (no adopter sobra o WARN do template).
4. **MF-DEVOPS-4 [W7a → W7b, antes da rc.1 da 1.4.3] — Prova do upgrade antes do corte.**
   - As pernas «v1.4.2 → upgrade ao HEAD → `check_harness_config.py --replay` rc 0» e «install do zero →
     gate rc 0» landam como commit LIVRE logo depois da W7a.
   - O arquivo é `scripts/tests/test-upgrade-historical-adopter.sh` (oráculo 0, fora do manifesto ADR-192)
     [disco], e o commit livre não ocupa vaga.
   - Se não landar antes da rc.1, o CHANGELOG diz que a cura via upgrade segue NÃO provada.
5. **MF-DEVOPS-5 [W7a, bateria do LAND] — Presença nos canais por build REAL.**
   - npm: `bash scripts/install-npm.sh` (tarball local, sem publicar) e `tar -tzf` com os 3 `.json`.
   - plugin: depois do `build-plugin.py`, `cmp` dos 3 arquivos em `dist/ceo-plugin/hooks/_lib/harness_replay/`.
   - O espelho do `npm-rebuild.sh` NÃO prova o canal: o rsync dele não tem as exclusões
     (`npm-rebuild.sh:64-66`).
   - A presença no packlist gate (`npm-publish.yml:398`, oráculo 1) vira FU.
6. **MF-DEVOPS-6 [W7b] — Cura do cwd.** O `validate-governance.sh` roda o `check-test-audit-isolation.py`
   num subshell com cwd = `REPO_ROOT`, e o `.py` sai da tabela. Controle: de outro cwd, uma cópia velha de
   `audit_emit.py` plantada em `REPO_ROOT/.claude` segue acusada.
7. **MF-DEVOPS-7 [W7b] — Predicado com CLI.**
   - O `check-rule-invariants.py` ganha um modo que só responde `_is_framework_repo`.
   - rc inesperado (falha de infraestrutura) cai num teste de arquivo em bash, declarado como fallback
     (molde `install.sh:1530-1537`), com aviso. Um teste de paridade garante que o literal do bash é igual
     a `_PRIMARY_MARKER` (`:163`).
   - O controle positivo roda contra o repo REAL, em CI: renomear o ADR-001 deixa a CI vermelha (Q7b.2).
8. **MF-DEVOPS-8 [W7b e W8, abertura] — Medir antes de somar pernas.**
   - Se o p95 previsto do job `smoke` passar de 120 min, o e2e histórico vai a um job PRÓPRIO, em paralelo;
     subir o timeout não resolve.
   - A tag da perna é DERIVADA, como no H.14 (`test-upgrade-historical-adopter.sh:898-922`); a CI já busca
     `refs/tags/v*` (`smoke-install.yml:380`).
9. **MF-DEVOPS-9 [W8, `.mcp.json`] — Função própria.**
   - Destino ausente ⇒ nada.
   - Symlink (no arquivo ou num ancestral), hardlink ou ancestral que não é diretório ⇒ recusa nomeada.
   - Escrita atômica, com backup em `$BAK_DIR/.mcp.json` (`upgrade.sh:1400`).
   - SEM registro de entrega e sem gate por cerimônia: a prova é o conteúdo.
   - O teste de pins aprende o mapeamento fonte ≠ destino (`test-schema-generation-pins-unit.sh:80,125-126`
     assume os dois iguais).
   - Controles: destino ausente continua ausente; hardlink com o hash antigo fica intocado.
10. **MF-DEVOPS-10 [W8, `_dispatch.md`] — Raiz e confinamento.**
    - Roda o gerador do ALVO (atualizado em `upgrade.sh:4354`) com `CLAUDE_PROJECT_DIR="$TARGET"` explícito
      e cwd = alvo.
    - Antes, o bash checa no destino symlink, hardlink e ancestral.
    - Só escreve quando `--check` falha, com backup; `--dry-run` não escreve.
    - Falha do filho ⇒ WARN, nunca aborto sob `set -e`: `read_text` (`:199`) só captura `OSError`, e um
      agente não UTF-8 levanta exceção.
    - Controle VERMELHO: cwd e `CLAUDE_PROJECT_DIR` de outro projeto ⇒ esse projeto fica `cmp`-idêntico.
    - Resíduo declarado: a escrita pelo filho Python fica fora do censo bash do PLAN-185.
11. **MF-DEVOPS-11 [W8, `VERSION`] — Condição do NOTE.**
    - O NOTE dispara quando o conteúdo é uma versão de RELEASE do framework (lista pinada do git, mesmo
      mecanismo do MF-DEVOPS-9) e difere do marcador; o texto diz «pode ter sido semeado».
    - Controle novo: `VERSION=7.7.7` ⇒ sem NOTE.
    - Sem o filtro, o NOTE dispara em todo upgrade de quem versiona o próprio `VERSION`
      (`ADR-155-AMEND-1:52-54`).
12. **MF-DEVOPS-12 [W8, L9] — Sem sonda do Codex.** A troca é função só dos bytes: sondar `codex --version`
    faz o upgrade depender do host, e na CI o binário falta. Uma linha de NOTE explica como re-registrar o
    servidor. O `_comment` do template e o `INSTALL.md` («never overwritten») mudam no MESMO patch.
13. **MF-DEVOPS-13 [W8] — Baseline e bateria.** `doctor.sh` + `upgrade.sh` regeneram o baseline do
    PLAN-185 no mesmo patch, e a bateria roda os oráculos de CI que fazem grep nos dois (lição `adb6e84`).
14. **MF-DEVOPS-14 [W9] — Stop hook.** A chave (path, hash) sai dos MESMOS diffs de `risky_diff`
    (`:107-117`), sem segunda passada de `git`. O Check mede a parede com ≥ 1.000 arquivos contra o
    `timeout: 130` (`settings.base.json:519`). O estado resolve o gitdir por `git rev-parse --git-dir`, e o
    estado antigo migra sem reavisar a lista inteira.

## Nice-to-have (advisory)

1. **[W7a]** Um teste chama `run_replay(_REPO, None)`, o caminho PADRÃO. Hoje todos passam o diretório
   explícito (`test_check_harness_config.py:51-53,264-266,288,297`): foi assim que o defeito escapou.
2. **[W7a]** O docstring `test_check_harness_config.py:7` cita o caminho velho e entra no mesmo pacote,
   junto do `check_harness_config.py:56` (L4).
3. **[W9, Q9.5]** Um pacote só; se depois da 2.ª rodada do rail uma metade ainda tiver P1, divide em
   W9a/W9b.
4. **[FU]** Há cinco codificações de «interno do framework» (o predicado bash, `npm-publish.yml:317-329`,
   `install-npm.sh:116-130`, `build-plugin.py:342-345` e o `npm-rebuild.sh`, que não exclui nada). É a
   classe do A1-F4/F5.

## Unseen by the original plan

1. O `_dispatch.md` resolvido por `CLAUDE_PROJECT_DIR` ou cwd, com `mkdir` (R-DO1).
2. O precedente do hash-gate instala o ausente, registra a entrega e não recusa hardlink (R-DO4).
3. A 1.4.3 leva a W7a sem a W7b (R-DO2).
4. Um segundo padrão não entregue no mesmo hook, que contradiz a emenda como escrita (R-DO3).
5. Duas leituras de cwd no `check-test-audit-isolation.py` (R-DO6); nenhum teste unitário do caminho
   padrão (NTH 1); o estado do RISKY DIFF fora do lugar numa worktree (R-DO7).

## What I would NOT change

- A pasta de dados SEM `__init__.py`, que o install copia inteira (`install.sh:1364-1368`).
- `--no-renames` em TODA listagem do LAND, com ensaio completo em árvore descartável.
- A recodificação do marcador em vez da isenção, que calaria o teste e deixaria o grep do
  `install.sh:3818-3846` acusando.
- O marcador ADR-001, nunca `conftest.py`.
- A troca do `.mcp.json` só por hash de geração ENTREGUE, com a lista derivada do git.
- O `VERSION` sem escrita (ADR-155-AMEND-1 §2).
- Os e2e longos destacados, com timeout explícito e piso de `df`.

## Respostas às perguntas (minha lente)

- **Q7a.1:** (a), 8+1, código primeiro (MF-DEVOPS-1). Recuso a (c): exigiria uma exceção de WIP nova sem
  ganho de risco [plano :2862].
- **Q7a.3:** ZERO `{{` nos `.json` entregues (`grep -RIl '{{'` vazio no alvo), critério mais forte que as
  duas regex. A de arquétipo só afirma sobrevivência (`test_install_sh_placeholders.py:224-237`). O hook
  aceita só a forma nova.
- **Q7a.4:** (i) a prova do upgrade condiciona o corte, não o PROCEED (MF-DEVOPS-4); (ii) presença por
  build real (MF-DEVOPS-5); (iii) sim, a asserção proíbe `tests|fixtures` (MF-DEVOPS-2).
- **Q7a.5:** os padrões do hook, com o predicado «entregue»; o censo dos outros gates vai a FU.
- **Q7a.6:** aceitável com registro. O `check_bash_safety.py`, já entregue, traz o mesmo literal 12 vezes, e
  a fixture tem 466 bytes [disco]. A exclusão de `fixtures/` do plugin é por heurística de compressão
  (`build-plugin.py:338-341`), que JSON pequeno não aciona [inferência].
- **Q7b.1:** (a), com CLI (MF-DEVOPS-7). **Q7b.2:** o controle positivo no repo real cobre a remoção
  futura. **Q7b.3:** no chamador, por cwd (MF-DEVOPS-6).
- **Q7b.4:** manter o ADR novo; o MF-DEVOPS-4 tira da fila de ADR o que é urgente para os adopters.
- **Q7b.5:** perna normal na tag derivada; perna do purge com a árvore antiga plantada a partir dos BYTES
  da tag (`git archive v1.1.0 -- .claude/hooks/tests`), porque o purge é por hash; nada de install extra
  de versão antiga.
- **Q8.1:** trocar. Não reabre o `_ownership_verdict()`: não decide posse das 3 superfícies dele, é função
  de UMA dimensão (hash ∈ lista pinada do git) e não cria registro. Segue a semântica dos schema docs
  (`upgrade.sh:4444-4453`). Sem sonda (MF-DEVOPS-12).
- **Q8.2:** premissa da proposta FALSA: `--write` NÃO valida; o que valida é o `--validate`
  (`validate-governance.sh:800`). No `--write`, agente malformado é PULADO em silêncio
  (`generate-dispatch.py:196-210`), e arquivo não UTF-8 levanta exceção. O arquivo manual é sobrescrito
  com backup, só quando `--check` falha. Manifesto e install ficam para onda própria.
- **Q8.3:** só o NOTE, com filtro (MF-DEVOPS-11).
- **Q8.4:** sim, para os dois destinos; o backup de raiz fica em `$TARGET/.claude.bak/<ts>/`.
- **Q9.4:** N = 20; o teto de 2.048 bytes manda.
- **Q10.1:** NÃO fundir. Com o modo do parser (+2 paths), W7b + W10 passam de 8, e prenderia um L2 à fila
  de ADR.
- **Q10.3:** o parser ganha o modo da política (os mesmos 5 membros do yaml depreciado [disco]); a razão
  impressa é `policy:grandfather-cap`.

## (a) P0 ou afirmação FALSA

- **P0:** nenhum.
- **Afirmação falsa no plano, sem decisão da W7a que dependa dela (L1 procede):** «nenhuma versão
  entregou as fixtures» [plano :2130]. A `v1.1.0` traz as 3 fixtures, e o `upgrade.sh` dela substitui
  `.claude/hooks` inteiro (linha 1348 da tag); o `e718cd89` não está em `v1.0.0`..`v1.1.0` e está em
  todas as tags a partir de `v1.2.0-rc.1` [disco]. Afeta só a matriz da W7b (Q7b.5).
- **Afirmação falsa na PROPOSTA (Q8.2):** «`--write` valida o frontmatter».

## (c) Ajustes de texto

1. [plano :2130] Trocar por: «nenhuma INSTALAÇÃO nova entregou; o upgrade da v1.1.0 entregava a árvore».
2. [plano :2801-2803] AC-11: «rc 0, zero RED, com o padrão que dá RED na ausência entregue».
3. [plano :2436-2438] O `check-test-audit-isolation.py` sai da tabela da W7b.
4. [plano :2761-2772] Orçamento da W7a com dois pacotes: 140–240k tokens, 1–2 sessões (1, se os sentinels
   forem assinados juntos). As condições somam ~60–110k tokens nas cinco ondas, dentro das faixas.
5. L10: fixar «no máximo 2 rodadas; sem PROCEED na 2.ª, ESCALATE» também para W7b, W8, W9 e W10.

**Lacunas (minha lente):** procedem L1, L3, L4, L5 (superada pelo critério de zero `{{`), L6, L9, L10 e
L12. Oráculo re-rodado no `304ec478`: hook e ADR-158 = 1; `.json` novo = 0; `__init__.py` = 1; teste = 0;
`upgrade.sh` = 1; `doctor.sh`, `check-rule-invariants.py`, `check-test-audit-isolation.py` e
`generate-dispatch.py` = 0. Fora da minha lente: L2, L7, L8 e L11.
