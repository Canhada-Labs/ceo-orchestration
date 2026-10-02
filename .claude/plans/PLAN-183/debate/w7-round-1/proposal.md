---
plan: PLAN-183
round: 1
created_at: 2026-10-02T04:23:00Z
debate_dir: .claude/plans/PLAN-183/debate/w7-round-1/
scope: ondas W7a, W7b, W8, W9 e W10 (seção «Waves S359»)
plan_file: .claude/plans/PLAN-183-adopter-fitness.md
checked_at_head: 092377af02b6
---

# Proposta — debate L3 das ondas S359 do PLAN-183 (rodada 1)

Esta proposta destila a seção «Waves S359» de `.claude/plans/PLAN-183-adopter-fitness.md` (linhas
2036-2903) e a resposta ao campo (`.claude/plans/PLAN-183/resposta-ao-campo-1.4.2.md`). O debate mora
em `debate/w7-round-1/`, nunca em `debate/round-1/` (debate da S315; regra comum 11). Ele mede
coerência de desenho (`design-coherent`) e NÃO autoriza ship: só a cascata V1 a V3 autoriza (testes,
rail do Codex, GPG do Owner).

**Marcas de evidência.** `[V]` = verificado nesta edição, HEAD `092377af02b6`, 02/10/2026. `[P:n]` =
lido no plano, linha n, sem nova checagem. `[T]` = triagem de 30/09, evidência privada do Owner, não
re-verificada. «Partida» = posição de partida do CEO, não decisão do Owner. Cada crítico responde, por
número, as perguntas da §2, no formato de 7 seções do `DEBATE-SCHEMA.md` §4.

## 1. O que o Owner já decidiu (fora de debate)

O debate NÃO reabre estes itens. Quem discorda registra nota ao Owner, não Must-fix.

1. **Estrutura e ordem.** A1-A7 são ondas do PLAN-183 e W7-W10 estão aprovadas (30/09/2026); cada onda
   ainda passa por debate (L3), rail e GPG. Decisão 7, «Codex automático, depois adopter
   (Recomendado)»: **a W7a pega a vaga que a W1 do PLAN-194 liberar ao landar**; depois vem a W2 do
   PLAN-194; a W7b segue logo depois da W7a, sem esperar a W1 do PLAN-183. [P:2050-2071,2730-2759]
2. **OQ-12.** Fixtures em `.claude/hooks/_lib/harness_replay/`, SEM `__init__.py` (pasta de dados). Se
   um teste exigir o arquivo, ele vira o 10.º path. [P:2841-2863]
3. **Emenda do ADR-158: ADITIVA, DENTRO do próprio arquivo.** Não cria arquivo de ADR nem de emenda e
   não toca índice, contagens nem `CLAUDE.md:54`. [P:2299,2426-2430]
4. **Patch sem rename:** `git diff --no-renames`; todo conjunto comparado no LAND (staged ou diff)
   usa `--no-renames` ou `-c diff.renames=false`. [P:2302-2340]
5. **Marcador `{{PROJECT_DIR}}` recodificado** na fixture E no hook, sem isentar o caminho no teste de
   placeholders. A forma nova sai na abertura. [P:2368-2399]
6. **Arquivos de ADR.** Índice, contagens e `CLAUDE.md:54` ficam FORA do teto de 8 paths (4.ª exceção
   de WIP do PLAN-194), o LAND os re-deriva e só um pacote de ADR voa por vez. [P:2213-2233]
7. **Fora do debate:** A3 (PLAN-195); OQ-18, purga no adopter (do Owner, no repositório dele); regras
   comuns 1-13 [P:2138-2233]; nenhum Check com medição paga (decisão 5); nenhuma data prometida
   (`resposta-ao-campo-1.4.2.md:270`).

## 2. Perguntas que o debate responde

Responda cada pergunta com a opção escolhida e a razão. «Manter a partida do CEO» vale, com razão.

### 2.1 W7a — fixtures num caminho entregue (A1, forma 1) — L3, PRIORITÁRIA

**Q7a.1 — Divisão em pacotes e ordem.** A tabela tem 9 paths (hook, 3 deletes, 3 adds, teste,
ADR-158); o teto é 8. Partida do plano: pacote do código (8) + pacote separado da emenda do ADR-158,
na MESMA vaga, um depois do outro; o debate confirma divisão e ordem. [P:2289-2340]
- Opções: (a) 8+1, código primeiro; (b) 8+1, ADR primeiro; (c) um pacote de 9 (exige exceção de WIP
  nova; as 4 atuais não cobrem [P:2862]).
- [V] Oráculo = 1 no hook e no ADR-158. `ADR-158:57-60` fixa a pasta antiga na Decisão. O pacote do
  ADR custa +1 sessão, rail e GPG [P:2770].

**Q7a.2 — A emenda é mesmo aditiva?** Owner: sim, dentro do arquivo. O mapa de colisões ainda prevê o
debate mandar a emenda a arquivo próprio, se for semântica; a W7a entraria na fila de ADR [P:2726].
- [V] `adr/README.md:59-64`: reversão semântica ganha arquivo de emenda. Precedente in-file:
  `ADR-158:150-165` (PLAN-161 C1) trocou 7 entradas por 4 e declara o texto antigo «historical».
- Pergunta: a emenda declara que SUBSTITUI a pasta de `:60`? Com o fail-closed intacto (fixture
  ausente = RED), isso basta para chamá-la aditiva?

**Q7a.3 — O critério do marcador cobre o que o install escaneia?** Critério do plano: a forma nova não
casa `\{\{[A-Z_][A-Z0-9_]*\}\}` e hook e teste a leem de volta. [P:2389-2392]
- [V] O hook monta o literal em fragmentos (`check_harness_config.py:158-165`) e o substitui em
  `:674`; `test_check_harness_config.py:231` usa o literal; `install.sh:3818-3846` não tem isenção.
- [V] O teste de placeholders tem OUTRA regex, `\{\{[A-Z][a-zA-Z_]+\}\}`
  (`test_install_sh_placeholders.py:84,224`). `{{PROJECT_DIR}}` casa as duas (L5).
- Pergunta: o critério passa a exigir as duas regex? O hook aceita só a forma nova?

**Q7a.4 — Prova de entrega: upgrade, npm e plugin.** O plano prova o install na W7a e o upgrade na
W7b; a entrega pelo upgrade foi LIDA, não executada. [P:2344-2351]
- [V] `upgrade.sh:1790-1815` anda `find -type f` com o mesmo predicado (só com baseline carregado,
  `:1779-1781`). O staging do npm exclui `**/tests/` e `**/fixtures/` (`npm-publish.yml:321-322`,
  `install-npm.sh:120-121`) e o plugin ignora `tests` e `fixtures` (`build-plugin.py:342-345`):
  `harness_replay` viaja. O packlist gate (`npm-publish.yml:398`) afirma só a AUSÊNCIA de
  `tests|fixtures`, nunca a PRESENÇA das fixtures.
- Pergunta: (i) o PROCEED exige prova de upgrade já na W7a (partida: não, a W7b prova)? (ii) A
  bateria afirma a presença nos canais npm e plugin? (iii) A asserção proíbe nomes `tests|fixtures`?

**Q7a.5 — Profundidade da asserção estrutural.** Plano: o caminho padrão lido por um gate entregue
não é excluído por `_framework_path_excluded` (chamada REAL ao bash); o resíduo vai declarado no ADR e
o censo vai a FU. [P:2417-2420,2796-2797]
- [V] Predicado em `_framework_manifest_set.sh:95-107`. A 2.ª ocorrência de uma classe pede cura da
  CLASSE (`CLAUDE.md` §4, S352); A1-F4 e A1-F5 são da mesma classe, sem pacote [P:2780-2785].
- Pergunta: só `REPLAY_FIXTURES_REL` (partida) ou uma lista declarada dos caminhos padrão de gates?

**Q7a.6 — Entregar a fixture destrutiva.** Sem posição no plano (L6). [V] `bash_safety_destructive.json`
carrega `rm -rf /` como string JSON, só lida por stdin, com `_fixture: INERT TEST DATA`; `ADR-158:57-60`
a chama «inert JSON data». Pergunta (Security): esse literal em todo adopter, tarball e plugin é aceitável?

### 2.2 W7b — UM predicado de repo-fonte + e2e de versão antiga (A1, forma 2) — L3

**Q7b.1 — Onde mora o predicado.** Opções: (a) `check-rule-invariants.py`, que já o implementa
(`_is_framework_repo`, oráculo 0); (b) módulo novo em `.claude/hooks/_lib/` (oráculo 1, +1 path).
[P:2455-2458]
- [V] Há TRÊS respostas hoje: `validate-governance.sh:1165` (`[ -d .claude/hooks/tests ]`),
  `check-rule-invariants.py:163,212-217` (marcador ADR-001), `check-test-audit-isolation.py:600`
  (`pytest.ini` do cwd). O chamador é bash: sem CLI do predicado, o `.sh` vira a 4.ª cópia local.

**Q7b.2 — Marcador ADR-001 e o desarme silencioso.** Partida do CEO (S359): ADR-001, nunca
`conftest.py` (reabriria o skip silencioso do PLAN-119). [P:2273-2275]
- [V] O adopter só recebe `adr/README.md` (`check-rule-invariants.py:158-162`).
  `validate-governance.sh:1160-1164` exige que a arma seja independente do artefato do PLAN-119.
- Pergunta: apagar ou renomear o ADR-001 no repo-fonte desarma o PLAN-119 em silêncio? O controle
  positivo do plano cobre a presença de hoje, não a remoção futura.

**Q7b.3 — Cura do cwd: no chamador ou no script.** [V] `validate-governance.sh:1192` chama
`check-test-audit-isolation.py` SEM argumentos; o default lê o `pytest.ini` do cwd (`:600`); o `grep` de
`:1180-1182` varre `$REPO_ROOT/tests`. Opções: (a) o `.sh` passa as raízes do `REPO_ROOT` e o `.py`
não muda (partida implícita [P:2436]); (b) o `.py` resolve a raiz (o path condicional entra).

**Q7b.4 — ADR novo ou emenda in-file.** A tabela cria um ADR («decisão transversal»), o que dispara
índice, contagens, `CLAUDE.md:54` e a fila de ADR. [P:2442,2213-2233]
- [V] `CLAUDE.md` tem 39.912 de 40.000 bytes (87 de folga). Há 198 `ADR-*.md`; o último é o ADR-197.
  Os números 198 a 200 já são citados nos PLAN-175 e PLAN-176; o 201 é do PLAN-195 (busca em `.claude/plans/`).
- Pergunta: uma emenda aditiva num ADR existente basta e evita a fila? Partida: ADR novo, número a
  partir do 202 após busca na abertura.

**Q7b.5 — Matriz do e2e de versão antiga.** Plano: instalar a `v1.4.2` (sem fixtures), upgrade ao HEAD
curado, gate rc 0; o caminho `--purge-misinstalled` também. [P:2474-2478] [V] O e2e atual leva ~34 min
contra `timeout-minutes: 150` [P:2200-2212]. Pergunta: só a `v1.4.2`, ou também uma versão que ENTREGAVA a
árvore de testes (L1)? A perna do purge parte de um alvo com a pasta criada à mão?

### 2.3 W8 — higiene do upgrade (A7 + A2 + `_dispatch.md` do A6) — L3

**Q8.1 = OQ-13 — O upgrade TROCA o `.mcp.json` ou só AVISA?** Partida: trocar, com backup, só quando o
sha256 é o de um template que o framework entregou; qualquer outro recebe aviso nomeado
(`claude mcp remove codex -s project`). [P:2544-2549,2864-2867]
- [V] Entre 20 tags `v*` há 2 gerações: `5a5bfc40…` (18 tags, `v1.0.0` a `v1.4.1-rc.1`) e `ada8b1e7…`
  (`v1.4.2` e a rc); só o commit `3c2fb8e9` mudou o template. O arquivo antigo tem 1.204 bytes: prova
  de origem forte, ao contrário do `VERSION` de 6 bytes (`ADR-155-AMEND-1:50-69`).
- [V] `upgrade.sh` tem 0 menções a `mcp.json`, `doctor.sh` 0 a `mcp`. O arquivo é semeado por
  `_FIXED_TEMPLATES_MAINTAINER` (`install.sh:1138-1145`) e não consta em `delivery-routes.tsv`,
  `_framework_manifest_set.sh` nem `ownership_table.tsv`: a troca fica FORA do `_ownership_verdict()`.
- Obrigatório [P:2528-2535]: registrar por que a troca por hash segue o precedente (hash-gate dos
  schema docs, `upgrade.sh:4466-4474`, guardado por `test-schema-generation-pins-unit.sh`) e não reabre
  a classe «posse por cascata» (`CLAUDE.md` §4).
- Pergunta adicional (L9): o servidor só morre com Codex >= 0.154.0 (`INSTALL.md:1002-1010`; a pin da
  1.4.1-rc.1 ainda admitia versões antigas). A troca é incondicional ou usa sonda?

**Q8.2 = OQ-14 — `_dispatch.md` entra no manifesto? A instalação nova entrega os 5 agentes?** Partida:
gerar, sim (`generate-dispatch.py --write` depois dos agentes); manifesto e agentes no install ficam para
onda própria (tocam `install.sh` e `_framework_manifest_set.sh`, como a W1). [P:2868-2872]
- [V] `upgrade_agents_canonical_only` em `upgrade.sh:4496`; 0 menções a `_dispatch` no `upgrade.sh`;
  `install.sh` não trata `.claude/agents`. O validador avisa a ausência (`validate-governance.sh:810`)
  e reprova o arquivo velho (`:790`).
- Pergunta adicional (L9): `--write` valida o frontmatter de todos os agentes (`:800`). Agente custom
  malformado do adopter aborta o upgrade ou só avisa? O `_dispatch.md` manual é sobrescrito?

**Q8.3 = OQ-15 — Parar de semear `VERSION` ou só avisar?** Partida: só o aviso agora; parar exige emendar
o ADR-155-AMEND-1. [P:2873-2875,2555-2558]
- [V] `install.sh:1829-1840` semeia só com cerimônia diferente de `user`. Reescrever com bytes
  iguais foi REJEITADO [P:2509-2510]. O ADR diz que a maioria dos repos versiona o próprio `VERSION`
  (`ADR-155-AMEND-1:52-54`): o NOTE «difere de `.framework-version`» dispara em TODO upgrade deles.
- Pergunta: frequência e condição do NOTE (sempre, uma vez, ou só quando o conteúdo coincide com uma
  versão do framework).

**Q8.4 — Confinamento dos destinos novos.** Sem posição no plano (L9). [V] O `upgrade.sh` consome o
predicado único do PLAN-185 (`_wbm_nlink`, ADR-196; `upgrade.sh:4960-4979`). A troca do `.mcp.json`
(raiz) e o `_dispatch.md` (escrito por filho Python, fora do censo bash) são destinos novos. Pergunta:
ambos passam pelo predicado (symlink e hardlink pendente recusados)? Onde mora o backup de um arquivo
de RAIZ?

### 2.4 W9 — dois hooks que custam caro sem pagar (A4 + A5) — L3

**Q9.1 = OQ-16 — O P4 vira só aviso no Bash?** Partida: sim; bloquear por «independência» exigiria
saber se um grep depende do outro, e o hook não sabe. Subir o limiar ou isentar `.claude/**` foi
REJEITADO. [P:2576-2577,2876-2878]
- [V] P4 = 4 ou mais `grep|find|rg|ag` em 5 min (`check_anti_ceo_overhead.py:175,184,198`), comandos
  «distintos» por Jaccard < 0,5 (`:553`), bloqueio em `:712-716`. No apply-step o P4 já é aviso desde
  o PLAN-169 W3.3 (`:683-713`). Neste repo: 1.943 eventos de override em ~30 dias [T].
  `test_anti_ceo_overhead.py:230` hoje espera disparo.
- [V] ADRs que citam o hook, lidos por busca: `ADR-116-AMEND-1:224,326`, `ADR-127:88,158`,
  `ADR-197:38`. Nenhum fixa o P4 como bloqueio; o plano os dava como «não lidos» e prevê +1 path se
  algum fixasse [P:2600-2602].
- Pergunta: com o P4 sem bloqueio, ele fica como aviso permanente ou o predicado sai?

**Q9.2 = OQ-17 — Tirar do escopo do RISKY DIFF o que o framework entregou?** Partida: NÃO nesta onda;
teto + chave completa + delta resolvem o custo, e o registro de entrega não cobre `policies/`,
`dispatcher/` nem `agents/` (A5-3) [T]. [P:2586-2591,2879-2882] [V] `DIFF_CAP = 16000`
(`codex_review_user_code.py:50`) corta só o diff (`:117`); a lista junta tudo (`:301-303`); a dedup usa o
sha256 do diff já cortado (`:117,146,296`).

**Q9.3 — O aviso do P4 é auditado?** Sem posição no plano (L7). O Check diz «a detecção continua» e testa
o aviso, não um evento. [V] `check_anti_ceo_overhead.py:689-693` admite que o aviso do apply-step NÃO é
auditado (auditar pede ação registrada nova, cerimônia do `audit_emit`); `ADR-127:158` usa «P4 fire
count» como métrica. Pergunta: aceitar que a contagem de P4 caia a zero em silêncio, ou abrir item para a
ação nova? O dedup do override vale para qual predicado, se no Bash o P4 deixa de bloquear?

**Q9.4 — Teto, chave de dedup e custo de calcular.** Plano: «N paths + e K outros», < 2 KB
(Check <= 2.048 bytes); chave = conjunto completo de (path, hash), calculada ANTES de truncar.
[P:2586-2589,2615-2619] N não está fixado. «Só o delta» exige gravar hash por path em
`.git/.ceo_codex_review_state.json`; a 1.ª execução pós-upgrade reavisa uma vez. [V] O custo de CALCULAR
não muda: `changed_files` e `_file_diff` (`:70-107`) rodam `git` por arquivo (timeout 20 s) e leem até
8.000 bytes por não rastreado; ninguém mediu a latência do Stop hook com 1.622 arquivos. Pergunta: valor
de N, formato do estado, migração do estado antigo.

**Q9.5 — Dividir em W9a (A4) e W9b (A5)?** Plano: «se o debate pedir». Partida: um pacote (4 paths,
~250-350 linhas). [P:2600-2605]

### 2.5 W10 — validador de skills (A6-1 / A6-2) — L2 com GPG

**Q10.1 — Fundir a W10 na W7b?** Plano: se a W7b fechar com <= 5 paths, a W10 pode entrar nela; decisão do
CEO na abertura da W7b. [P:2646-2649] W7b = 5 paths (+2 condicionais); W10 = 3, dois em comum (validador e
manifesto); 200-300 + 80-120 linhas contra o teto de 400 [P:2444,2643]. [V] `test_skill_grandfather_parser.py`
e `test_squad_grandfather_cap.py` rodam o validador. Pergunta: fundir? Os dois testes entram na bateria?

**Q10.2 — Forma `<nível>/<skill>`.** [V] `validate-governance.sh:200` procura só `` `$skill` ``; o `team.md`
entregue cita `core/pii-data-flow` e outras duas [P:2623-2627]. Plano: «aceitar também `<nível>/<skill>`»,
sem regra de casamento. Pergunta: aceitar QUALQUER prefixo, ou exigir que `<nível>` seja o diretório real da
skill (`resolve_skill`)? O 1.º aceita `frontend/pii-data-flow` para uma skill de `core`.

**Q10.3 — Isenções da política entregue.** Plano: ler `grandfather-cap.policy.yaml`, com o yaml depreciado
como fallback. [P:2628-2634] [V] A política lista `individual_skills.members` (5 nomes, as 2 isenções entre
eles) SEM `reason`. O `skill_grandfather_parser.py` lê só o formato do yaml depreciado e valida `reason` por
enum; o validador consome linhas `skill:reason` (`validate-governance.sh:130-146`). Parser e teste dele
(oráculo 0) não estão na tabela da W10. Pergunta: o parser ganha um modo para a política (+2 paths) ou o
`.sh` lê a lista inline? Que razão a mensagem imprime?

## 3. Critério de PROCEED por onda

Escala do `DEBATE-SCHEMA.md` §5: PROCEED, RUN-ANOTHER-ROUND, ESCALATE-TO-OWNER. O veredito é POR ONDA;
nenhuma onda fica refém de outra. Proposta do CEO, a confirmar pelo debate.

- **Comum.** PROCEED exige: zero Must-fix e zero VETO abertos; cada pergunta da onda com resposta e razão;
  cada lacuna da §5 que toca a onda com disposição; cada decisão traduzida em Check testável com controle
  vermelho; estimativa em tokens e sessões (ADR-081). PROCEED registra `design-coherent`.
- **W7a (prioritária).** PROCEED nesta rodada é a condição para ocupar a vaga da W1 do PLAN-194. Exige
  Q7a.1 a Q7a.5; a Q7a.6 pode ser aceita com registro. Sem PROCEED, a rodada 2 trata SÓ a W7a, em
  `w7-round-2/`. Regra de parada fixada AGORA: no máximo 2 rodadas; sem PROCEED na 2.ª, ESCALATE ao Owner.
- **W7b.** Exige Q7b.1 a Q7b.4; a Q7b.5 pode virar condição do material. O local do predicado precisa
  estar fixado ANTES de o Scope listar paths. Não bloqueia a W7a.
- **W8.** Exige Q8.1 a Q8.4. A Q8.1 carrega o ponto obrigatório (por que a troca por hash não reabre
  `_ownership_verdict()`). Um RUN-ANOTHER-ROUND da W8 não atrasa W7a nem W7b.
- **W9.** Exige Q9.1 a Q9.4 e a decisão da Q9.5. VETO de Security ou Threat Detection sobre o P4 só
  aviso pede razão escrita e condição de retirada.
- **W10.** Exige Q10.2, Q10.3 e a decisão da Q10.1. Sendo L2, o PROCEED pode sair por leitura.
- ESCALATE só quando dois críticos bloqueiam com desenhos exclusivos: o CEO leva o empate ao Owner com
  `AskUserQuestion`, uma opção «(Recomendado)».

## 4. Riscos e colisões

- **R1 — Vaga.** A W7a só ocupa a vaga quando a W1 do PLAN-194 (prazo 19/10) landar; sem PROCEED, a vaga
  vai à W2 do PLAN-194. [P:2739-2742]
- **R2 — Leque de ADR.** Pacotes que CRIAM arquivo de ADR entram em fila (um por vez, junto de um
  fechamento de sessão): W7b, parte A do PLAN-195 (ADR-201), provavelmente W2 e W3 do PLAN-194; a W7 do
  PLAN-194 não voa junto (`CHANGELOG.md`). A W7a só entra na fila se a emenda sair do ADR-158 (Q7a.2).
- **R3 — W7a x parte A do PLAN-195.** Sem path comum; cruzam por teste. A fixture
  `bash_safety_destructive.json` roda contra `check_bash_safety.py`, que a parte A muda. A bateria da W7a
  roda `test_check_bash_safety.py` e `test_check_bash_safety_canonical_matrix.py`; o PLAN-195 põe
  `test_check_harness_config.py` na bateria dele [V PLAN-195:270,523-524]. A quebra vem dos dois lados.
- **R4 — Manifesto ADR-192.** W7b e W10 x W7 do PLAN-194, só se o corte mudar o `release.sh`: fila. [P:2725]
- **R5 — Fila de `scripts/`.** W8 divide `upgrade.sh`, baseline do PLAN-185 e `INSTALL.md`: W5b do
  PLAN-194, W1a/W1b, W8; `INSTALL.md` depois da W6 do PLAN-194. [P:2722-2724]
- **R6 — e2e longo, espelhos e janela.** `test-upgrade-historical-adopter.sh` leva ~34 min e W7b e W8 somam
  pernas (destacado, até 2 h, piso de `df`). `dist/` e `npm/` não são rastreados: rebuild antes da
  bateria [P:2161-2212]. Depois da W7a, os adopters existentes seguem vermelhos até a W7b provar o upgrade.

## 5. Lacunas e contradições do plano

- **L1.** A linha do A1 (`:2130`) diz «nenhuma versão entregou as fixtures»; a resposta ao campo diz que o
  `upgrade.sh` da `v1.1.0` copiava `.claude/hooks` inteiro até `e718cd89` (27/07/2026)
  (`resposta-ao-campo-1.4.2.md:59-65`, nota 2 em `:396-399`). O plano não foi estreitado (Q7b.5).
- **L2.** Decidido x a confirmar: o Owner fixou a emenda in-file; o mapa de colisões (`:2726`) admite
  arquivo próprio (Q7a.2).
- **L3.** «A W7 vai em DOIS pacotes» (`:2279`), mas a W7a pode virar dois: 3 pacotes. A faixa de tokens da
  W7a não foi re-estimada [P:2771-2772].
- **L4.** Referências ao caminho antigo: o plano lista o README das fixtures (`:19`) e `validate.yml:1117`.
  [V] Há também `check_harness_config.py:56` (docstring, no próprio pacote), `ADR-158:60` e
  `docs/BUG-REPORT-adopter-harness-config-replay-fixtures.pt-BR.md:48-52,83,113,196` (fecha na W7b).
- **L5.** A 2.ª regex de placeholder (`test_install_sh_placeholders.py:84,224`) não consta do critério (Q7a.3).
- **L6.** Os canais npm e plugin não aparecem na W7a (Q7a.4); a fixture destrutiva não tem posição (Q7a.6).
- **L7.** O Check do P4 não cobre o evento de auditoria (Q9.3). O plano dava os ADRs como «não lidos»; a
  busca desta edição não achou nenhum que fixe o P4 como bloqueio.
- **L8.** A tabela da W10 não lista o parser de isenções nem o teste dele, e a política não traz `reason`
  (Q10.3).
- **L9.** A W8 não trata: predicado de confinamento nos destinos novos (Q8.4), falha do `--write` com agente
  custom malformado (Q8.2) e condição de versão do Codex na troca do `.mcp.json` (Q8.1).
- **L10.** O plano dá «1 rodada» só à W7a (`:2342`). Nada fixa as rodadas das outras ondas; a «regra de
  parada» da regra comum 8 é do RAIL, não do debate.
- **L11.** `resposta-ao-campo-1.4.2.md:275-282` anuncia 3 decisões em debate (`.mcp.json`, P4, RISKY DIFF);
  o plano envia 5 (OQ-13 a OQ-17, com `_dispatch.md` e `VERSION`).
- **L12.** O plano cita 3 HEADs diferentes. [V] Oráculo re-rodado hoje no `092377af02b6`: os 2 hooks da
  W9, o da W7a, ADR-158 e `upgrade.sh` = 1; `doctor.sh`, `validate-governance.sh`, fixture nova = 0.

## 6. Glossário

- **ADR** — registro de decisão de arquitetura. **Emenda aditiva** — acrescenta seção sem reverter
  comportamento. **Canônico / oráculo** — arquivo protegido; `check_canonical_edit.py --is-canonical
  <path>` responde 1 ou 0. **Cerimônia / GPG** — pacote assinado pelo Owner, depois LAND.
- **L2 / L3** — níveis de risco (L3 exige debate). **Rail** — revisão cruzada do Codex. **e2e** — teste
  ponta a ponta com instalação real. **FU** — follow-up. **WIP / vaga** — pacotes canônicos em voo (máximo 3).
- **Fixture de replay** — JSON que o gate do harness reexecuta contra o hook real. **PLAN-119** — gate do
  validador sobre o isolamento de auditoria nos testes do próprio framework.
