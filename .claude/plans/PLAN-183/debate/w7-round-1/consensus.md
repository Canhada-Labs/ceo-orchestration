---
plan: PLAN-183
round: 1
debate_dir: .claude/plans/PLAN-183/debate/w7-round-1/
rounds_synthesized: [w7-round-1]
scope: "ondas W7a, W7b, W8, W9 e W10 (seção «Waves S359»)"
critics: [Critic-A, Critic-B, Critic-C]
agents_considered: [Critic-A, Critic-B, Critic-C]
verdicts: [ADJUST, ADJUST, ADJUST]
vetoes: "Critic-C (ADR-052, escopo de segurança). NENHUM VETO levantado nesta rodada. W7a: sem VETO, declarado. VETO CONDICIONAL em três ondas: W7b, local do predicado (MF-C-5); W8, confinamento dos dois destinos novos (MF-C-8 e MF-C-10); W9, trilha forense do P4 (MF-C-11). W10: nenhum. Critic-A e Critic-B não têm VETO."
wave_verdicts:
  W7a: PROCEED
  W7b: RUN-ANOTHER-ROUND
  W8: PROCEED
  W9: PROCEED
  W10: PROCEED
round_verdict: RUN-ANOTHER-ROUND
design_coherent:
  W7a: true
  W7b: false
  W8: true
  W9: true
  W10: true
execution_conditions: 38
round_2_open_items: 4
consensus_adjustments: 24
owner_decisions: 1
codex_review_of_proposal: "7 achados (5 P1, 2 P2), VERDICT REQUEST-CHANGES; os 7 procedem"
decisions_revised_in_plan: "pendente — esta síntese NÃO edita o plano; o CEO aplica a lista «Plan adjustments» num commit livre (regra comum 6)"
checked_at_head: 399efbaad171
synthesized_at: 2026-10-02T05:14:00Z
synthesized_by: CEO (síntese delegada, S361)
revision: "r2 — após revisão cruzada do Codex sobre este consenso (4 P1: Red Team, C11, C27, C28) e varredura de metades perdidas em C1–C38 contra as críticas originais"
synthesized_from: "texto anonimizado das três críticas (cópias no scratchpad da sessão, fora do repositório); revisão cruzada do Codex sobre a proposta; proposta; PLAN-183 no HEAD 399efbaa, idêntico ao commit. Limitações declaradas: (1) os prefixos dos ids de risco e a listagem do diretório do debate deixam inferir os arquétipos; o mapa de anonimização não foi lido, e o estado de VETO veio da tarefa; (2) sondas e medições dos críticos marcadas [medido] ou [sonda] não foram re-executadas; (3) o oráculo --is-canonical não foi re-rodado nesta síntese (só leitura); os valores citados vêm dos críticos. Cada decisão se apoia em fato conferido no disco, não em quem o afirmou."
---

# Consenso — PLAN-183, debate L3 das ondas S359, rodada 1 (W7a, W7b, W8, W9, W10)

> **O que este veredito certifica.** `design-coherent` (DEBATE-SCHEMA §13.1) certifica só a coerência
> interna do desenho entre perspectivas forçadas do MESMO modelo. Não autoriza publicar. Cada pacote segue
> pela cascata V0 → V1 → V2 (rail do Codex) → V3 (GPG do Owner). **Repositório público:** só classes de
> defeito e invariantes; nenhuma receita de contorno de guarda.

## 0. Verificação das afirmações

Conferido no disco, no HEAD `399efbaa`. O diff `092377af..399efbaa` não toca nenhum arquivo citado abaixo.
Legenda: **procede** | **procede em parte** | **não procede** | **não verificado**.

### 0.1 Afirmações decisivas das críticas

| # | afirmação (quem) | evidência | resultado |
|---|---|---|---|
| 1 | `PLAN-183:2130`, «nenhuma versão entregou as fixtures», é FALSA (A, B, C) | `git ls-tree v1.1.0` lista as 3 fixtures; `git show v1.1.0:scripts/upgrade.sh`, linha 1348: `backup_and_replace ".claude/hooks"`; `e718cd89` não é ancestral da `v1.1.0` e a 1.ª tag dele é `v1.2.0-rc.1`; a árvore de testes da `v1.1.0` tem 549 arquivos, `conftest.py` incluído; `resposta-ao-campo-1.4.2.md:59-65,396-399` já estreita | **procede**. A instalação nova nunca entregou (exclusão desde a 1.0.0, `resposta…:58-60`); o upgrade da `v1.1.0` entregava |
| 2 | O checker do PLAN-119 lê o cwd DUAS vezes (A, B, C; Codex) | `check-test-audit-isolation.py:600` (`pytest.ini` do cwd) e `:610` (WS-D2 em `Path(".")`) | **procede** |
| 3 | O validador arma o PLAN-119 pela forma do diretório e chama o checker sem argumentos; checker ausente = WARN (C) | `validate-governance.sh:1165`, `:1192`, `:1202` | **procede** |
| 4 | `check-rule-invariants.py` está fora do manifesto ADR-192; ADR-001 renomeado ⇒ pula com `ok: True` (C) | o manifesto tem 9 membros, o validador na linha 2; `check-rule-invariants.py:242-252` | **procede**; oráculo 0 relatado por A e C, não re-rodado |
| 5 | O gerador do `_dispatch.md` resolve a raiz por `CLAUDE_PROJECT_DIR` ou cwd e grava com `mkdir` + `write_text` (A, C) | `generate-dispatch.py:46-48`, `:394-395` | **procede** |
| 6 | No `--write`, agente malformado é pulado em silêncio; arquivo não UTF-8 levanta exceção (A) | `collect_agents` (`:241-251`) descarta `None`; `parse_agent_file` captura só `OSError` (`:198-201`) | **procede** por leitura, não executado |
| 7 | Gerar o `_dispatch.md` ARMA o `--validate` no adopter (B) | `validate-governance.sh:787-806` só roda com `_dispatch.md` presente; sem ele, WARN em `:810` | **procede** |
| 8 | O precedente `_refresh_schema_doc` instala o ausente, registra a entrega e não recusa hardlink (A, C) | `upgrade.sh:4416-4421`; `_rsd_mark_delivered` em `:4420,4441,4450`; checa symlink e ancestral, não hardlink | **procede** |
| 9 | O hook lê por padrão `templates/settings/settings.base.json`, que o adopter não tem; ausente ⇒ WARN, rc 0 (A) | `check_harness_config.py:168-171`, `:620-623`, `:918-929` | **procede** |
| 10 | Com `CEO_SOTA_DISABLE=1` o replay vira 1 WARN, e o CLI sai rc 0 imprimindo `replay=yes` (B) | `check_harness_config.py:733-740`, `:923-928` | **procede** |
| 11 | Nenhum pytest exercita o caminho PADRÃO do replay (A, B) | `test_check_harness_config.py:51-53`; `run_replay` sempre com pasta explícita (`:251-297`) | **procede** |
| 12 | O replay executa o hook da tabela do gate e lê só `expect` e `payload` (C) | `check_harness_config.py:742-792` | **procede** |
| 13 | Há 4 gramáticas de placeholder; uma reprova a instalação (exit 4) sob `--strict-placeholders` (B) | `install.sh:3066-3090` (ERE só em `*.md`/`*.py`), `:3834` (`grep -RIl`), `test_install_sh_placeholders.py:83-84` | **procede em parte**: o scan estrito não lê `.json`; alcança o hook (`.py`), não as fixtures |
| 14 | A substituição do install exclui `.claude/hooks/*` (C) | `install.sh:2936-2946` | **procede** |
| 15 | npm e plugin excluem por NOME de segmento; o packlist gate só afirma ausência; o `npm-rebuild.sh` não exclui (A, B, C) | `npm-publish.yml:321-322,398`; `install-npm.sh:120-121`; `build-plugin.py:342-345`; `npm-rebuild.sh:64-66` | **procede** |
| 16 | No plugin, as fixtures não têm consumidor (B, C) | `ceo-boot.py` fora de `GUARDED_CLIS` (`build-plugin.py:287-294`); o replay procura os hooks em `repo_root/.claude/hooks` (`:783`) | **procede** por leitura, não executado |
| 17 | O hook entregue já traz o literal destrutivo (A: 12; C: 25) | `check_bash_safety.py`: `grep -c 'rm -rf /'` = 12 linhas; `grep -c 'rm -rf'` = 25; fixture de 466 bytes | **procede**: contagens de padrões diferentes |
| 18 | P4 no Bash sombreia o P5; o override sai antes do ramo de aviso (B, C) | prioridade P1>…>P5 (`check_anti_ceo_overhead.py:494-505`); `skip_p4` só no apply-step (`:696-712`); `:673` antes de `:696` | **procede** |
| 19 | O aviso do apply-step não é auditado, com «named follow-up» (C) | `check_anti_ceo_overhead.py:683-693` | **procede**; o fechamento do FU não foi verificado |
| 20 | O ADR-116-AMEND-1 fixa a dimensão FORENSE do hook; o ADR-127 mede o P4 (C) | `ADR-116-AMEND-1:224-225`, `:326` (linha 43); `ADR-127:158` | **procede** |
| 21 | A lista sem teto aparece em 6 ramos, não só em `:301-303` (B) | `codex_review_user_code.py:303,311,315,322,330,335` | **procede** |
| 22 | **Pré-existente (C, R-SEC1):** no modo AUTO, conteúdo não rastreado vai ao Codex sem redação | AUTO é opt-in (`:291`); o prompt concatena o diff (`:125-128`); 0 ocorrências de `redact` no arquivo; o redator existe (`_lib/codex_egress_redact.py`); `isfile` + `open` seguem symlink (`:99-100`); `route.py:34-38` marca `.env`, `secret`, `credential`, `api_key` como risco | **procede** por leitura; a sonda de symlink de C não foi re-executada; arquivo ignorado pelo `.gitignore` não entra (`--exclude-standard`, `:79`) |
| 23 | CLEAN sobre o diff cortado em `DIFF_CAP` marca `reviewed` e aprova o `review_loop` (C) | `:117`, `:326`, `:334` | **procede** |
| 24 | Numa worktree, o estado cai na raiz; escrita não atômica (A, C) | `_state_path` (`:140-143`); `json.dump(open(...,'w'))` (`:166`) | **procede** |
| 25 | O teste de pins supõe o mesmo path no git e no pin (A, B) | `test-schema-generation-pins-unit.sh:80`, `:125-130` | **procede** |
| 26 | A 1.4.3 leva a W7a sem a W7b (A) | `PLAN-194:135` (HEAD) | **procede** |
| 27 | A população `v1.1.0` já é coberta pelo resíduo plantado do teste de fronteira (C) | o resíduo da `:2473` é a árvore de fixtures + 1 teste de negócio, não a árvore de 549 arquivos com `conftest.py` | **procede em parte** |
| 28 | Replay não vácuo com marcador não substituído; p50 de 0,99 s (B) | sonda do crítico | **não verificado** |

### 0.2 Revisão cruzada da PROPOSTA pelo Codex (7 achados)

| achado | evidência | resultado |
|---|---|---|
| P1 — Q8.2 atribui validação ao `--write` (`proposal.md:152`) | `generate-dispatch.py:370-392` (`--validate`) × `:393-396` (`--write` só grava); `validate-governance.sh:800` chama `--validate` | **procede** (A diz o mesmo) |
| P1 — Q8.4 chama `_wbm_nlink` de predicado (`proposal.md:164`) | `_framework_manifest_set.sh:683` só devolve a contagem de links; o predicado completo é `_wbm_dst_refuses` (`:776`); o `upgrade.sh` usa a contagem só contra hardlink (`:4983`) | **procede** |
| P1 — Q7b.3(a) não cura o cwd (`proposal.md:112-115`) | `check-test-audit-isolation.py:610` | **procede** |
| P1 — Q7a.2 reabre decisão do Owner (`proposal.md:60-65,252`) | o Owner fixou a emenda dentro do arquivo (`PLAN-183:2299`); o mapa de colisões ainda admite arquivo próprio (`:2726`) | **procede**; o debate ficou dentro da decisão (3 de 3: aditiva) |
| P1 — ESCALATE «só» com dois críticos contradiz a parada (`proposal.md:235` × `:243`) | `DEBATE-SCHEMA.md:247-249` dá o conflito de dois críticos como EXEMPLO | **procede**; regra aplicada em §6 |
| P2 — os testes da Q10.1 não rodam o validador (`proposal.md:211`) | `test_skill_grandfather_parser.py:277-285` roda o parser; `test_squad_grandfather_cap.py:372-378` lê o texto do `.sh` | **procede** |
| P2 — não há leitura limitada a 8.000 bytes (`proposal.md:200`) | `codex_review_user_code.py:100` lê o arquivo inteiro e guarda 8.000 CARACTERES | **procede** |

**Nenhuma afirmação decisiva foi marcada «não procede».** Duas procedem só em parte (linhas 13 e 27).

## 1. Veredito por onda

Regra de agregação (DEBATE-SCHEMA §2 e §5; critério comum da proposta): PROCEED exige zero must-fix
bloqueante e zero VETO aberto. Uma onda nunca fica refém de outra. Divergências se resolvem assim: o
portador de VETO prevalece no domínio dele, salvo disco que o refute; fora dele, vale a opção que todos os
críticos aceitam.

| onda | veredito | críticos | VETO (Critic-C) | por quê |
|---|---|---|---|---|
| **W7a** | **PROCEED** (`design-coherent`) | 3 de 3 | sem VETO | Nenhum P0. A afirmação falsa da `:2130` não sustenta decisão da W7a (afeta só a matriz da W7b). Q7a.1–Q7a.5 respondidas; Q7a.6 aceita com registro. Condições C1–C10 |
| **W7b** | **RUN-ANOTHER-ROUND** | A e C: PROCEED; B: bloqueia | CONDICIONAL ao local do predicado (MF-C-5) | B bloqueia com fatos que procedem (§0.1, linhas 1, 2, 27). Ficam abertos o local do predicado, a cura do cwd e a matriz do e2e (R2-1 a R2-4). A W7b depende da W7a landada: a rodada 2 não está no caminho crítico |
| **W8** | **PROCEED** (`design-coherent`) | 3 de 3 | CONDICIONAL: C16 e C19 cumpridas | O ponto obrigatório tem resposta convergente (§3, F13). O gerador sai da FONTE: o portador de VETO prevalece (executar código do alvo no upgrade). Condições C15–C22 |
| **W9** | **PROCEED** (`design-coherent`), dividida em W9a e W9b | 3 de 3 | CONDICIONAL à C25 (decisão 1 do Owner, §5) | Divisão por 2 de 3 críticos, com a razão do portador de VETO (a W9a ganha a cerimônia do `audit_emit`). Condições C23–C32 |
| **W10** | **PROCEED** (`design-coherent`), L2 | 3 de 3 | nenhum | Não funde na W7b (3 de 3). Condições C33–C36 |

**VETO.** Nenhum foi levantado. Os três condicionais, com a condição EXATA:

- **W7b (MF-C-5):** o predicado mora em `_lib/` (oráculo 1), ou em `check-rule-invariants.py` SÓ se este
  entrar no manifesto ADR-192 no MESMO pacote; erro ao avaliar o predicado ARMA o bloco ou dá FAIL
  nomeado, nunca pula.
- **W8 (MF-C-8, MF-C-10):** os dois destinos novos (`.mcp.json` e `_dispatch.md`) passam pelo predicado
  compartilhado de confinamento; o gerador roda da fonte.
- **W9 (MF-C-11):** uma ação auditada de aviso, no Bash e no apply-step, pela cerimônia do `audit_emit`,
  ou uma decisão ESCRITA do Owner, no material assinado, que aceite a perda forense e aposente por texto a
  métrica do `ADR-127:158`. Sem uma das duas, há VETO no rail da W9a.

**A divergência da W7b.** A e C dão PROCEED com condições; B pede rodada 2. Os fatos de B procedem. Pelo
critério da proposta, a matriz (Q7b.5) poderia virar condição do material. Mas as Q7b.1 e Q7b.3, exigidas
para PROCEED, seguem com desenhos divergentes. Na Q7b.1, A escolhe `check-rule-invariants.py` sem o
manifesto; essa é a forma que dispara o VETO condicional de C. Na Q7b.3, A quer o subshell e o `.py`
intacto; C exige a raiz explícita no `.py`, com FAIL no vácuo; B aceita os dois. Fechar isso aqui seria
decidir desenho pelos críticos.

## 2. Condições de execução, por onda (consolidadas e deduplicadas)

Uma condição não cumprida reprova o SIGN do pacote dela, não o debate. Quem confere é o rail (V2).

**W7a — pacote do código (8 paths) + pacote da emenda do ADR-158, na mesma vaga**

1. **C1 — Ordem e assinatura** (MF-A-1; Q7a.1 (a), 3 de 3). Pacote do código primeiro. O pacote do
   ADR-158 é derivado DEPOIS que o rail do código converge. Os dois sentinels podem ser assinados na mesma
   sessão do Owner. Ordem: LAND do código, depois LAND do ADR. A emenda não toca título nem `**Status:**`.
   Bateria do ADR: `generate-adr-index.py --check` rc 0 e 198 `ADR-*.md`.
2. **C2 — Texto da emenda** (B e C na Q7a.2; MF-A-3; MF-B-7). Aditiva, dentro do ADR-158. Declara que
   SUBSTITUI a pasta do item 1 da Decisão (`ADR-158:57-60`), como `:166-167` já faz com texto antigo. A regra
   vai pela FORMA: «padrão de leitura cuja ausência deixa o gate VERMELHO pertence ao conjunto entregue». A
   exceção fica declarada: insumo só do repo-fonte cai em WARN. O resíduo da classe vai só pela forma.
3. **C3 — Invariante de consumo da fixture entregue** (MF-C-1). A emenda declara, pela forma: a fixture é
   lida só por parser JSON; vai por stdin, com argv fixo, sem shell, a um hook escolhido pela tabela do
   gate; nenhum campo dela escolhe programa, argv, env ou cwd; o marcador é trocado em valores já
   parseados. Controle vermelho no `test_check_harness_config.py`: uma fixture com `hook` apontando outro
   script não muda o hook executado.
4. **C4 — Caminho padrão testado** (MF-B-1; A NTH 1). O teste deriva a pasta de `chc.REPLAY_FIXTURES_REL`.
   Ao menos um teste chama `run_replay` sem `fixtures_dir`. Controle vermelho: a constante apontando para
   pasta inexistente deixa esse teste RED.
5. **C5 — Asserção estrutural de ENTREGA** (MF-A-2, MF-B-2, MF-C-2(b)). «Entregue» = coberto por uma
   entrada de `_framework_target_entries` e não excluído por `_framework_path_excluded`, por chamada REAL ao
   bash. O teste confirma que a função existe e exige rc EXATO (0 excluído, 1 entregue; outro rc = falha),
   com controle positivo no mesmo run (o caminho antigo responde excluído). Cobre os dois padrões do hook: o que dá RED na ausência tem de ser entregue; o que
   só dá WARN fica numa lista declarada. Controles vermelhos: um caminho em `templates/` e o caminho antigo.
   Nenhum segmento `tests` ou `fixtures` no caminho do replay.
6. **C6 — Marcador** (A Q7a.3, MF-B-5, MF-C-3). A forma nova não contém `{{` (`grep -RIl '{{'` vazio nos
   `.json` do alvo); isso cobre as 4 gramáticas. O hook aceita SÓ a forma nova: fixture com a forma antiga dá replay RED. A forma nova não colide com chave do
   `build_sed_script` (`install.sh:2866-2900`). Na bateria, os dois scans do install acusam o MESMO conjunto
   de arquivos antes e depois, com o grep sobre `<alvo>/.claude` inteiro.
7. **C7 — Pernas do gate** (MF-B-3, MF-B-4). As pernas verde e vermelha rodam com `CEO_SOTA_DISABLE`
   removido do ambiente. A verde casa a linha inteira com `0 warning(s)`. A vermelha dá exatamente 3 RED,
   todos `MISSING`. O hook entregue roda também no contrato do `/ceo-boot` (cwd = alvo, sem argumentos), e o
   tempo é registrado contra o teto de 2,5 s.
8. **C8 — Canais** (MF-A-5, MF-B-6, MF-C-2(a)(c)). npm: staging real e local, sem publicar
   (`install-npm.sh`), os 3 `.json` no packlist e `cmp` no alvo, com o resultado registrado no material. O espelho do `npm-rebuild.sh` não prova o canal. Plugin: o CEO
   decide na abertura entre (i) excluir `harness_replay` do `build-plugin.py` por commit livre e (ii)
   entregar, com declaração no ADR («sem consumidor») e `cmp` dos 3 arquivos no `dist/`. A asserção
   permanente de PRESENÇA no `npm-publish.yml` vira FU nomeado.
9. **C9 — Prova do upgrade antes do corte** (MF-B-6, MF-A-4). A bateria do LAND roda um smoke barato:
   `v1.4.2` (`git archive`) → `upgrade.sh` curado → `cmp` + gate rc 0. As pernas permanentes «`v1.4.2` → upgrade →
   replay rc 0» e «install do zero → gate rc 0», no `test-upgrade-historical-adopter.sh`, landam como commit
   livre logo depois da W7a e antes da rc.1 da 1.4.3. Se não landarem, o
   CHANGELOG do corte declara a cura via upgrade NÃO provada.
10. **C10 — FU e texto** (MF-B-7, MF-C-4, A NTH 2 e 4). Antes do SIGN da W7a, existem dois FU com dono e
    posição: o censo POR FORMA de «componente entregue lê por padrão caminho excluído» (2.ª ocorrência,
    A1-F4/F5) e a unificação das cópias do predicado de entrega. Os docstrings `check_harness_config.py:56`
    e `test_check_harness_config.py:7` são corrigidos no pacote do código.

**W7b — condições já convergentes (valem na rodada 2; não são PROCEED)**

11. **C11 — Cura do cwd completa** (A, B, C; Codex). A opção (a) pura sai: a cura cobre `:600` E `:610`.
    Dois controles, os dois rodando de OUTRO cwd. (i) Semeado (R2-b): cwd com `pytest.ini`, um teste que o
    checker acusa e uma cópia velha de `audit_emit`; acha antes da cura, não acha depois. (ii) Positivo
    (MF-A-6): uma cópia velha de `audit_emit.py` plantada em `REPO_ROOT/.claude` segue acusada.
12. **C12 — Predicado único** (MF-A-7, R2-d, MF-C-5). Uma implementação, com CLI para o chamador bash.
    Teste-censo: nenhum outro arquivo re-deriva o marcador.
13. **C13 — Controles** (MF-A-7, R2-c, R2-d, MF-C-6). No checkout REAL, nunca com marcador plantado: um
    teste afirma o predicado verdadeiro na raiz, e o cabeçalho `--- PLAN-119 audit-isolation gate` sai
    exatamente 1 vez no validador completo. Renomear ou apagar o ADR-001 deixa a CI vermelha, também para o
    `check-rule-invariants`. No alvo do adopter, o «0 linhas PLAN-119» exige a linha de resumo final do
    validador. Forma dogfood sem marcador ⇒ WARN nomeado. O ADR declara o uso MONÓTONO: o predicado só ARMA
    verificações, e nenhum consumidor relaxa uma guarda quando ele é verdadeiro.
14. **C14 — ADR novo** (A, C; B). Mantido; `check-claude-md-claims.py` entra na bateria.

**Abertos para a rodada 2 (W7b):**

- **R2-1 — Local do predicado (Q7b.1).** (a) `check-rule-invariants.py`, que entra no manifesto ADR-192 no
  mesmo pacote; ou (b) módulo em `_lib/` (oráculo 1, preferido por C). B é indiferente.
- **R2-2 — Falha ao avaliar o predicado.** A: rc inesperado cai num teste de arquivo em bash, declarado
  como fallback, com teste de paridade do literal. C: o erro ARMA o bloco ou dá FAIL nomeado, nunca pula.
- **R2-3 — Cura do cwd (Q7b.3).** (b) raiz explícita no `.py` (C; B aceita), com FAIL para zero raiz,
  zero arquivo e checker ausente no repo-fonte; ou (c) subshell com cwd = `REPO_ROOT` e `.py` intacto (A; B
  recomenda).
- **R2-4 — Matriz do e2e (Q7b.5).** B: 4 pernas (`v1.4.2`; árvore herdada da `v1.1.0`; fixtures à mão,
  idênticas e editadas; ramo legado sem manifesto). A: tag derivada + purge sobre os bytes da `v1.1.0`. C:
  `v1.4.2` + purge, com arquivo editado que sobrevive. Todas com o tempo somado contra os 150 min do job.

**W8**

15. **C15 — `.mcp.json`, desenho** (3 de 3; MF-A-12, MF-C-9). Troca quando o sha256 pertence a uma
    geração ENTREGUE, derivada do git. É incondicional à versão do Codex: nenhum binário do PATH roda no
    upgrade. Um NOTE explica como re-registrar o servidor. O aviso e o `doctor.sh` imprimem só o nome do
    servidor e o comando de remoção, nunca o conteúdo. O backup guarda só bytes de hash conhecido.
16. **C16 — `.mcp.json`, escrita** (MF-A-9, MF-C-8, MF-B-8(iv)). Função própria, que chama o predicado
    compartilhado `_wbm_dst_refuses` ANTES de tudo: symlink no arquivo ou num ancestral, hardlink ou
    ancestral que não é diretório ⇒ PRESERVED nomeado. Não clona o `_refresh_schema_doc`. Destino ausente ⇒
    nada. Hash, backup e troca usam os MESMOS bytes, com re-hash logo antes da troca atômica (temporário no
    mesmo diretório + rename). Backup em `$BAK_DIR/.mcp.json` (`upgrade.sh:1400`), nunca na raiz. Sem
    registro de entrega e sem gate por cerimônia. Resíduo TOCTOU = o do ADR-196.
17. **C17 — `.mcp.json`, pernas** (MF-B-8, MF-A-9). (i) template antigo ⇒ troca + backup `cmp` aos bytes
    antigos; (ii) template atual ⇒ nada, sem backup; (iii) variante CRLF ou sem `\n` final ⇒ aviso, intocado;
    (iv) symlink ou hardlink ⇒ recusa nomeada, arquivo externo `cmp`-idêntico; (v) 2.º upgrade ⇒ nada, sem
    2.º backup; destino ausente segue ausente. O teste de pins aprende o mapeamento fonte ≠ destino e fecha
    nos dois sentidos (hash listado que não é geração ⇒ exit 1).
18. **C18 — Texto** (MF-A-12). O `_comment` do template e o `INSTALL.md` («never overwritten») mudam no
    mesmo patch.
19. **C19 — `_dispatch.md`, raiz e escrita** (MF-C-10; MF-A-10). Roda o gerador da FONTE (`$SOURCE_DIR`),
    nunca a cópia do alvo, com `CLAUDE_PROJECT_DIR="$TARGET"` explícito e cwd = alvo. Preferido: modo
    stdout, com o bash gravando sob `_wbm_dst_refuses`, de forma atômica e com backup; o sítio entra no censo
    do PLAN-185 (baseline na C22). Se o filho Python gravar, o bash checa antes symlink, hardlink e
    ancestral do destino, e o resíduo fica declarado. Só escreve quando `--check` falha; o
    `--dry-run` não escreve.
20. **C20 — `_dispatch.md`, falha e pernas** (MF-A-10, MF-B-10, MF-C-10). Falha do gerador ⇒ WARN nomeado,
    `_dispatch.md` intocado, upgrade segue; nunca aborta sob `set -e`. Pernas: cwd e `CLAUDE_PROJECT_DIR`
    de outro projeto ⇒ esse projeto `cmp`-idêntico (controle vermelho); agente custom malformado; arquivo
    não UTF-8; `_dispatch.md` editado à mão ⇒ sobrescrito com backup; symlink recusado antes do filho. O
    resultado do validador depois da geração fica registrado.
21. **C21 — NOTE do `VERSION`** (MF-A-11, MF-B-9). Dispara só quando o conteúdo é uma versão LANÇADA do
    framework (lista pinada do git) e difere do marcador. O texto diz «pode ter sido semeado». Controle:
    `VERSION` do app (por exemplo `7.7.7`) ⇒ sem NOTE.
22. **C22 — Baseline e bateria** (MF-A-13). `doctor.sh` + `upgrade.sh` regeneram o baseline do PLAN-185 no
    mesmo patch. A bateria roda os oráculos de CI que fazem grep nos dois.

**W9 — dividida**

23. **C23 — Divisão** (Q9.5: B, C). W9a = A4 (`check_anti_ceo_overhead.py`); W9b = A5
    (`codex_review_user_code.py`).
24. **C24 — W9a, sombra do P5** (MF-B-11, MF-C-12). O aviso do P4 no Bash reusa a reavaliação `skip_p4`.
    Controle vermelho: janela com P5 e rajada de P4, evento Bash ⇒ o P5 BLOQUEIA. P1–P3 e P5 seguem
    bloqueando.
25. **C25 — W9a, trilha forense** (MF-C-11; MF-B-12). Ação auditada de aviso no Bash E no apply-step, pela
    cerimônia do `audit_emit`, OU decisão escrita do Owner (§5, decisão 1). O P4 fica como aviso
    permanente. O predicado só sai com essa mesma decisão. Sem a ação, a queda da contagem fica pinada por
    teste (nenhum evento) e declarada, com FU da ação auditada nova.
26. **C26 — W9a, override** (MF-B-12, MF-C-13). O aviso do P4 é avaliado ANTES do override: 0 eventos de
    override para P4. O Check de dedup migra para um predicado que ainda bloqueia (P5); o vermelho pré-cura
    dá N. O dedup falha para o lado de EMITIR: estado ilegível ⇒ emite; o 1.º evento sempre sai;
    `session_id` vazio ⇒ sem dedup; sessões nunca se fundem. Vale para P1–P3 e P5.
27. **C27 — W9b, chave** (MF-C-14, MF-A-14). A chave por path é o hash do conteúdo COMPLETO (não
    rastreado) ou do diff completo (rastreado), nunca da prévia de `PER_FILE_CAP`. Sai da mesma passada que
    gera os diffs, sem segundo `git`: as duas condições cabem juntas porque `:100` já lê o arquivo inteiro.
    Symlink não rastreado nunca é seguido (`lstat`), e o conteúdo da chave é o destino TEXTUAL do link.
28. **C28 — W9b, estado** (MF-B-14, MF-C-14, MF-A-14). Estado antigo, corrompido ou desconhecido ⇒ sem
    exceção, vazio ⇒ UM reaviso, depois silêncio. Pernas para path apagado e para path renomeado. Escrita
    atômica, recusando path de estado em symlink. O gitdir sai de `git rev-parse --git-dir` (worktree).
29. **C29 — W9b, «revisado»** (MF-C-15, MF-B-14). Só vira `reviewed` o que entrou INTEIRO no diff enviado.
    Com truncamento, nada de `_approve_review_loop` para o conjunto.
30. **C30 — W9b, mensagem** (MF-B-13, MF-C-16). No máximo 2.048 bytes, contagens primeiro, no máximo 10
    nomes; o teto vale em BYTES, com paths longos e multibyte no teste. Cada nome é higienizado (sem C0/C1, comprimento limitado). Um formatador único serve os 6 ramos. O
    teste percorre todos com ≥ 1.000 arquivos, em ordem determinística, com `mostrados + K == total`. O
    resíduo «canal de nomes» vai declarado pela FORMA; se o rail achar contorno, o fallback é só contagens.
31. **C31 — W9b, egresso e custo** (MF-C-17, MF-A-14, MF-B-14). A W9 não alarga o egresso: mesmo
    `DIFF_CAP`, nenhum conteúdo novo no prompt. O Check mede a parede com ≥ 1.000 e 1.622 arquivos contra o
    `timeout: 130` (`settings.base.json:519`).
32. **C32 — W9b, FU do egresso AUTO** (MF-C-18). Antes do SIGN da W9b, um FU com dono e posição cobre a
    redação (ADR-114) e o `lstat` no modo AUTO (§0.1, linha 22). Não bloqueia a W9; bloqueia ficar sem dono.

**W10**

33. **C33 — Sem fusão com a W7b** (3 de 3).
34. **C34 — Forma `<nível>/<skill>`** (MF-B-15; C na Q10.2). Vale só quando `<nível>` é o tier de
    `resolve_skill`. Pernas: `core/pii-data-flow` aceita; `frontend/pii-data-flow` segue avisando; nome
    curto aceita; forma de domínio definida. O Check afirma o CONJUNTO exato das 5 linhas.
35. **C35 — Isenções da política** (MF-B-16; A e C na Q10.3). Modo novo do parser (+2 paths: parser e
    teste; W10 = 5 paths), nunca parse inline em bash. Guarda de deriva: membros da política = skills do yaml
    depreciado (5 = 5). Falha de leitura ⇒ zero isenções. A mensagem imprime razão literal fixa, com a fonte.
36. **C36 — Bateria** (B, C; Codex P2). `test_skill_grandfather_parser.py` e `test_squad_grandfather_cap.py`
    entram em todo pacote que toque o `validate-governance.sh`. Eles testam o parser e o texto do `.sh`, não
    o validador: a prova de comportamento é o Check da W10.

**Transversais**

37. **C37 — Regra de parada do debate, por onda** (A ajuste 5, MF-B-17; Codex P1). No máximo 2 rodadas.
    Sem PROCEED na 2.ª ⇒ ESCALATE-TO-OWNER, mesmo com um único crítico bloqueando.
38. **C38 — Medir antes de somar pernas** (MF-A-8; regra comum 12). W7b e W8: se o p95 previsto do job
    `smoke` passar de 120 min, o e2e histórico vai a um job próprio, em paralelo. Subir o timeout não resolve. A tag da
    perna é DERIVADA.

## 3. Consensus findings (2 ou mais críticos)

1. **F1 — `:2130` é falsa** (A, B, C): a instalação nunca entregou; o upgrade da `v1.1.0` sim. → ajuste 1, R2-4.
2. **F2 — W7a em 8+1, código primeiro** (A, B, C). → C1.
3. **F3 — Emenda aditiva, dentro do ADR-158, declarando a substituição** (B, C; A pela C1). → C2, ajuste 9.
4. **F4 — O caminho PADRÃO do replay não tem teste** (A, B). HIGH para B. → C4.
5. **F5 — A asserção tem de testar ENTREGA e proibir `tests|fixtures`** (A, B, C). → C5.
6. **F6 — O hook aceita só a forma nova do marcador** (A, B, C). → C6.
7. **F7 — Presença no npm por staging real; o packlist gate só afirma ausência** (A, B, C). → C8.
8. **F8 — As fixtures não têm consumidor no plugin** (B, C). → C8, decisão do CEO na abertura.
9. **F9 — Entregar a fixture destrutiva é aceitável** (A, C; B sem objeção). → C3, C8.
10. **F10 — O censo da classe é FU obrigatório (2.ª ocorrência)** (A NTH 4, B, C). → C10.
11. **F11 — A Q7b.3(a) deixa o WS-D2 no cwd** (A, B, C; Codex). → C11, R2-3.
12. **F12 — Renomear o ADR-001 desarma em silêncio** (A, B, C). → C13.
13. **F13 — Trocar o `.mcp.json` por hash não reabre o `_ownership_verdict()`** (A, B, C). A troca é função
    de um único fato (sha256 ∈ gerações entregues, derivadas do git). Não decide posse de `PROTOCOL.md`,
    `SPEC/v1` nem `.framework-version`, e não cria registro; o `.mcp.json` está fora das rotas, do manifesto
    e da tabela de posse. O precedente vale para a DECISÃO, não para a escrita (§0.1, 8). → C15, C16, aj. 15.
14. **F14 — Os dois destinos novos passam pelo predicado de confinamento** (A, B, C). → C16, C19.
15. **F15 — `_dispatch.md`: raiz explícita, falha vira WARN** (A, C; pernas de B). → C19, C20.
16. **F16 — O NOTE do `VERSION` só com versão lançada** (A, B). → C21.
17. **F17 — O P4 como aviso sombreia o P5 no Bash** (B, C). → C24.
18. **F18 — A contagem do P4 cairia a zero em silêncio** (B, C). → C25, §5.
19. **F19 — Chave, estado e escrita do RISKY DIFF** (A, B, C). → C27–C29.
20. **F20 — W10: sem fusão, modo do parser, tier exato** (fusão e parser: 3 de 3; tier: B, C). → C33–C35.
21. **F21 — Regra de parada para todas as ondas** (A, B; Codex). → C37.
22. **F22 — `--write` não valida** (A; Codex). → ajuste 13.

**Mantidos de um só crítico:** A — estado na raiz da worktree, exceção do WARN do template, `_comment` e
`INSTALL.md`, orçamento do job; B — vácuo do kill-switch, contrato do `/ceo-boot`, 6 ramos, variante
CRLF, `--validate` armado; C — egresso AUTO (pré-existente), aprovação do `review_loop` sobre diff cortado,
classe do `PER_FILE_CAP`, invariante de consumo, gerador da fonte, uso monótono.

**Rejeitados ou resolvidos contra um crítico:**

- A, «um pacote só na W9» (NTH 3): 2 de 3 dividem, com a razão do portador de VETO.
- A, «estado antigo migra sem reavisar»: B, C e a proposta reavisam uma vez, a direção segura.
- A, «gerador do ALVO»: o portador de VETO prevalece; executar código do alvo no upgrade.
- A, «N = 20»: fica o limite de 10 de C (canal de nomes, R-SEC8), sob o teto de 2.048 bytes de A e B.

**Advisory, sem condição:** C NTH 1 (hook pina o sha256 das 3 fixtures); B NTH 1 (teste da pasta sem
`__init__.py`); C NTH 3 (NOTE não ecoa conteúdo fora de semver); C NTH 4 (só contagens no contexto).

## 4. Plan adjustments (edições no `PLAN-183-adopter-fitness.md`)

O CEO aplica num commit livre (regra comum 6). Não é nova rodada. O rail de cada pacote confere.

1. *`:2130`, linha A1:* «nenhuma INSTALAÇÃO nova entregou as fixtures; o `upgrade.sh` da `v1.1.0` copiava
   `.claude/hooks` inteiro, testes incluídos, até `e718cd89` (1.ª tag `v1.2.0-rc.1`)», como
   `resposta-ao-campo-1.4.2.md:396-399`.
2. *W7a, «Tamanho» (`:2302-2340`), «Nível» (`:2341-2343`) e fase 1 de «Ordem das vagas» (`:2756`):*
   divisão 8+1 confirmada, código primeiro, ADR derivado depois do rail do código, assinaturas na mesma
   sessão (C1). W7a PROCEED em `w7-round-1/`. Sai o «a confirmar no debate».
3. *W7a, «Por que `_lib/harness_replay/` chega» (`:2344-2351`):* canais npm e plugin (C8); smoke de upgrade
   na bateria e pernas livres antes da rc.1 (C9). Os adopters seguem vermelhos até um CORTE levar a W7a; a
   W7b prova o upgrade, não cura.
4. *W7a, item e Check do marcador (`:2389-2392`, `:2421-2424`):* critério «a forma nova não contém `{{`»; o
   hook aceita só a forma nova (C6).
5. *W7a, 1.º Check (`:2413`):* trocar «com os 3 controles exercitados», que a saída não imprime
   (`check_harness_config.py:923-928`), pela C7.
6. *W7a, asserção estrutural (`:2417-2420`):* a forma de C5; o teste do caminho padrão (C4).
7. *W7a, AC da emenda (`:2425-2430`):* C1 a C3.
8. *W7a, «Referências textuais» (`:2400-2407`):* os docstrings `check_harness_config.py:56` e
   `test_check_harness_config.py:7` entram no pacote do código (C10).
9. *Mapa de colisões (`:2726`):* sai a frase «Se o debate mandar a emenda da W7a para arquivo próprio…». O
   debate confirmou a emenda aditiva, dentro do arquivo (3 de 3). Discordância futura é nota ao Owner, não
   saída do debate (Codex P1).
10. *AC-11 (`:2801-2804`):* «rc 0, zero RED, com o padrão que dá RED na ausência entregue».
11. *W7b, tabela e 1.º Check (`:2436-2442`, `:2469-2473`):* «o WS-C recebe as raízes» não cura a `:610`. A
    opção (a) pura sai. As linhas de `check-test-audit-isolation.py` e `check-rule-invariants.py` ficam
    pendentes da rodada 2 (R2-1, R2-3). Entram os dois controles da C11 e os da C12 e C13.
12. *W7b, Check do e2e (`:2474-2478`):* matriz pendente da R2-4; a população de upgraders da `v1.1.0`
    (árvore de 549 arquivos, `conftest.py` incluído) fica registrada.
13. *W8, A6-3 (`:2511-2515`):* o `--write` não valida. O `--validate` (`validate-governance.sh:800`) só
    roda com `_dispatch.md` presente, e gerar o arquivo o arma. Agente malformado é pulado em silêncio;
    arquivo não UTF-8 levanta exceção (Codex P1; C19, C20).
14. *W8, tabela (`:2517-2524`):* `templates/.mcp.json` entra, pela C18 e pela regra comum 2. A troca do
    `_comment` cria uma geração nova, e a derivação pelo git a lista (C17).
15. *W8, «Ponto obrigatório» (`:2527-2535`):* registrar F13. O predicado de confinamento é
    `_wbm_dst_refuses` (`_framework_manifest_set.sh:776`); o `_wbm_nlink` (`:683`) só conta links (Codex
    P1).
16. *W8, Checks (`:2544-2561`) e AC-13:* as pernas das C16 a C21.
17. *W9, «Tamanho» e «Nível» (`:2600-2605`):* divisão em W9a e W9b (C23). Sai o «não lidos»: o
    ADR-116-AMEND-1 fixa a dimensão forense (`:224-225`, `:326`) e o ADR-127 mede o P4 (`:158`). A W9a
    soma o path da cerimônia do `audit_emit`, se a decisão 1 for (i).
18. *W9, texto do A5 (`:2579-2591`):* o `PER_FILE_CAP` guarda 8.000 caracteres depois de ler o arquivo
    inteiro (Codex P2). A lista sem teto aparece em 6 ramos. O egresso AUTO pré-existente vai ao FU (C32).
19. *W9, Checks (`:2610-2619`) e AC-14:* C24, C26, C27, C28 (com as pernas de path apagado e renomeado),
    C30 e C31.
20. *W10, tabela, Check e «Depende de» (`:2637-2653`):* +2 paths (parser e teste; 5 paths), conjunto exato
    das 5 linhas, tier exato; sem fusão com a W7b. Os dois testes do parser não rodam o validador (Codex P2;
    C33–C36).
21. *Regra comum 11 e «Nível» de cada onda:* a parada do debate vale por onda (C37).
22. *«Orçamento» (`:2761-2777`) e `budget_*` do frontmatter:* W7a em 2 pacotes (A: 140–240k tokens, 1–2
    sessões; B: +40–80k no código e 40–80k no ADR, +1 sessão); W9 dividida (+1 rail e +1 GPG; C: W9a +1
    sessão e ~100–160k tokens se a ação auditada for construída); rodada 2 da W7b (B: 60–100k tokens, até 1
    sessão).
23. *«Fora destas ondas» (`:2778-2797`):* os FU nomeados com dono e posição: censo pela forma e unificação
    do predicado de entrega (C10); presença no packlist (C8); egresso AUTO (C32).
24. *«Progress log»:* entrada da S361 com o resultado desta rodada e o link deste arquivo.

## 5. Decisões do Owner

As decisões da §1 da proposta NÃO reabrem: estrutura e ordem, OQ-12, emenda aditiva dentro do ADR-158,
patch sem rename, marcador recodificado e arquivos de ADR fora do teto. O debate confirmou todas.

1. **Trilha forense do P4 (W9a).** Só esta decisão libera o VETO condicional da W9. Prazo: antes do SIGN da
   W9a (fase 3 da ordem interna; não é urgente).
   - **(i) Ação auditada nova (Recomendado).** Uma ação registrada de aviso, no Bash e no apply-step, pela
     cerimônia do `audit_emit`. É a cura da CLASSE (2.ª ocorrência, `CLAUDE.md` §4), o caminho preferido
     pelo portador de VETO e o mesmo alvo do FU que outro crítico pede. Custo: +1 sessão e ~100–160k tokens
     na W9a (estimativa de um crítico).
   - **(ii) Aceitar a perda forense, por escrito.** A decisão vai no material assinado e aposenta por texto
     a métrica «P4 fire count» do `ADR-127:158`. O P4 vira aviso sem evento.

**Para ciência, sem decisão:** a 1.4.3 leva a W7a sem a W7b (`PLAN-194:135`): a cura via upgrade sai do
corte só com a prova da C9. O destino das fixtures no plugin é do CEO (C8); a OQ-18 segue com o Owner.

## 6. Round verdict

**RUN-ANOTHER-ROUND**, restrito à W7b.

- **W7a, W8, W9 e W10:** PROCEED (`design-coherent`); saem do portão do debate. A rodada 2 só as reabre se
  um crítico mostrar um ajuste da §4 aplicado diferente deste texto.
- **W7b:** rodada 2 em `.claude/plans/PLAN-183/debate/w7-round-2/`, conduzida com o diretório nomeado (regra
  comum 11), com os mesmos três arquétipos.
  - Escopo: R2-1 a R2-4; confirmar C11 a C14; o texto corrigido da `:2130` (ajuste 1).
  - Entradas: este consenso, as três críticas da rodada 1 e o plano com os ajustes 1, 11 e 12 aplicados.
- **Regra de parada (C37):** sem PROCEED na `w7-round-2/` ⇒ ESCALATE-TO-OWNER (`AskUserQuestion`, uma opção
  «(Recomendado)»), mesmo com um só crítico ou o VETO de C abertos; resolve `proposal.md:235` × `:243`.
- **Red Team (DEBATE-SCHEMA §12.3) — obrigação condicional.** O portão M1 mede convergência por Jaccard
  entre rodadas consecutivas; não se aplica a esta rodada 1. Na rodada 2 (N = 2 ≤ 2), Jaccard ≥ 0,7 entre
  `w7-round-1` e `w7-round-2` torna o Red Team OBRIGATÓRIO antes de marcar o consenso da W7b
  (`DEBATE-SCHEMA.md:410`); a crítica dele entra nesse consenso. Medir o Jaccard cabe ao CEO (o script pode
  gravar evento). Bloqueio aberto pelo Red Team ⇒ a W7b não sai PROCEED na rodada 2 e vale a C37.

## 7. Artefato terminal (DEBATE-SCHEMA §2 e §6)

**Esta rodada NÃO gera `approved.md`.** O §6 manda a rodada TERMINAL gravar `approved.md` no lugar do
`consensus.md`. Esse arquivo resume o arco e registra a ratificação do Owner. A rodada 1 não é terminal: o
debate cobre as cinco ondas, e a W7b continua.

- **Quando nasce:** quando a W7b fechar (PROCEED na rodada 2, ou o ESCALATE decidido pelo Owner). O CEO
  então grava `debate/w7-round-<N>/approved.md`, cobrindo as cinco ondas, com `rounds_completed`,
  `final_verdict` e as seções do §6.
- **Exige ratificação do Owner:** sim, pelo §6. Também precisa da decisão 1 da §5 escrita, ou adiada
  explicitamente pelo Owner até o SIGN da W9a, e dos ajustes da §4 aplicados.
- **A W7a não espera o `approved.md`.** O PROCEED desta rodada é a condição da proposta para a W7a ocupar a
  vaga da W1 do PLAN-194 (DEBATE-SCHEMA §5: PROCEED ⇒ a execução começa); publicar segue na cascata V1–V3.
- **Cuidado de caminho:** o glob de sentinela é `PLAN-*/architect/round-*/approved.md` (`check_canonical_edit.py:1005`).
  O `debate/w7-round-N/approved.md` NÃO é sentinela; não o crie sob `architect/` por conveniência.
