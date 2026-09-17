# w1-approved — sentinel da W1 do PLAN-190 (DRAFT — assinar como w1-approved.md)

> Assinatura em um passo: `! bash .claude/plans/PLAN-190/w1/OWNER-190-W1-SIGN.sh`
> (aplica o patch, roda a bateria com as suítes do CI, preenche Anchor-SHA, Patch-sha256 e Data,
> assina, stageia o conjunto EXATO e commita; `--dry-run` ensaia sem assinar nem commitar). Push é
> decisão sua.

Plan: PLAN-190
Wave: W1 — ledger de lançamento de Workflow + guard de retomada
Patch: .claude/plans/PLAN-190/w1/p190-w1.patch
Patch-sha256: 02e8831fa5c0526f80931da85a974cdf7c7987ee2b736ccbfdaa2855c732b3eb
Anchor-SHA: 440a5306ee93b2fbf6fd021151faa2b3395ebcb1
Data: 2026-09-17

## Ratificação (Owner, S354)

Ordem verbatim (17/09/2026): «Quero corrigir o ceo-orchestration para que a execução autônoma seja
utilizável nos repositórios consumidores. […] Tornar lançamentos e progresso recuperáveis. Persistir
antes do despacho: identificação da execução e da fase; versão/hash do script; argumentos exatos,
preservando inclusive campos ausentes; opções efetivas relevantes; revisões de código/spec […]. Não
reconstruir argumentos de memória.»

Decisão do Owner após o rail r4 (17/09/2026, escolha estruturada): «Trocar a arquitetura
(Recomendado)» — o override deixa de ser estado em disco e passa a ser declarado na própria chamada
ou no ambiente; exceção no guard vira inconclusivo registrado; um validador único para o manifesto
lido de volta; o `relaunch` confere o hash do snapshot.

O que esta wave entrega, e nada além: um hook na tool `Workflow` que, no PreToolUse, decide a retomada
a partir desta chamada e do manifesto vinculado e grava o manifesto da chamada (sha256 + snapshot dos
bytes do script — um `scriptPath` só é lido se for arquivo regular de até 8 MiB —, `args` literal com
ausente ≠ null e sem truncamento, `resumeFromRunId`; a revisão git do `cwd` entra DEPOIS, com orçamento
de 1,2 s) e, no PostToolUse, vincula o run id devolvido (por `tool_use_id`; sem ele, só quando há um
único lançamento pendente e não bloqueado na mesma sessão, e nunca um segundo registro da mesma
chamada; o run id vem do rótulo `Run ID:` que o harness imprime no lançamento e na retomada, senão do
único id distinto da resposta; ids ambíguos ou ausentes não vinculam nem registram nada — o
lançamento fica sem vínculo, visível no `list`, e `bind` fecha à mão; um `tool_use_id` desconhecido ou
zero/vários candidatos viram linha `orphan`; nunca palpite). Os `args` são gravados
também na ordem ORIGINAL das chaves (o script vê essa ordem; o `relaunch` a reproduz). O guard
BLOQUEIA a retomada de um run sobre `args` diferentes do manifesto vinculado por `tool_use_id` ou
manual — por chave, ou as mesmas chaves em outra ordem —, com motivo só de contagens (as chaves ficam
no manifesto) que diz exatamente quais fases reexecutam e nomeia a rota da mudança deliberada; o manifesto lido de volta é VALIDADO antes de
virar evidência (`manifest_problem`: esquema, formas de ids, consistência entre `present`/`canonical`/
`literal` e seus hashes, e o `sha256` do script concordando com a ORIGEM — inline ou caminho lido ⇒
hash que os bytes do snapshot reproduzem; caminho ilegível, workflow nomeado ou sem script ⇒ `null`) e
um registro inconsistente é inconclusivo; vínculo heurístico nunca sustenta bloqueio, de args ou de script; script diferente com
`args` iguais é advisory (`CEO_WORKFLOW_SCRIPT_GUARD=enforce` bloqueia); com `args` iguais, hash de
script indisponível é inconclusivo; uma exceção dentro do guard, `args` que não se deixam serializar ou uma falha na
própria construção do registro dão inconclusivo registrado, e a chamada ainda é gravada; falha ao
gravar não desfaz um bloqueio já decidido e deixa breadcrumb. Override
numa rota só, carregada pela chamada ou pelo processo e NUNCA por estado em disco: `description` com o
prefixo exato `CEO_WORKFLOW_RESUME_FORCE:` seguido de motivo não vazio libera AQUELA chamada (a
declaração não é guardada; depois de vinculada, a chamada forçada passa a ser a referência do run:
retomar com as mesmas entradas dá `match` e só uma nova divergência pede nova declaração), ou
`CEO_WORKFLOW_RESUME_FORCE=1` no ambiente do harness; registrado como `mismatch_forced` com origem e
motivo, anunciado sem ecoar o motivo — avisos de chamadas permitidas chegam ao modelo como
`additionalContext` e ao usuário como `systemMessage`. `CEO_WORKFLOW_RESUME_GUARD=0` põe o guard em advisory mantendo o
ledger; `CEO_WORKFLOW_LEDGER=0` desliga. Registros gravados em ASCII escapado; índice com reparo de
fronteira de linha. A CLI de recuperação (`list · show · relaunch · check · bind · orphans · report`;
`relaunch` imprime os args na ordem original, recusa registro inconsistente e não anuncia como exata
uma chamada cujo script era ilegível no lançamento; para um workflow NOMEADO reproduz o nome e os args,
sem verificar o conteúdo salvo sob esse nome; `--out` só cria arquivo novo; `bind` confere o id do registro;
acha o ledger do hook a partir de subdiretório);
testes; o documento do rito; as registrações no settings do framework e no template base entregue aos
consumidores (o `user` deriva por subtração, NÃO exclui este hook e o nomeia em `blocking_inclusions`
com a rota); a lista ratificada do teste do template `user` (+2 registrações); o build do plugin
passando a levar o CLI de recuperação junto com o guard; os inventários derivados (mapa
comando→skill→hook, inventário de variáveis de ambiente, pinos do teste de paridade 52/49) e os bumps
de contagem que o `verify-counts.sh` exige (hooks 59→60, ligados 48→49, registrações 50→52, `_lib`
71→72), mais a entrada `[Unreleased]` do CHANGELOG.

Revisão registrada em `PLAN-190/debate/round-1/` e `PLAN-190/w1/`: debate r1 (3 críticos, ADJUST ×3,
consenso PROCEED como design-coherent); rail Codex r1 NO-GO com 7 achados, r2 NO-GO com 3, r3 NO-GO
com 2, r4 NO-GO com 4 (terceira rodada na classe «estado em disco lido de volta» ⇒ troca de
arquitetura decidida pelo Owner); revisão adversarial multi-lente (5 lentes, 2 refutadores por
achado, crítico de completude) sobre a v5, cujos achados confirmados que sobrevivem à v6 foram curados
na v6.1–v6.3; rail r5 NO-GO com 3 (totalidade da construção, hash ausente, breadcrumb) e as lacunas
do crítico de completude (ordem das chaves, retomada deliberada, contexto do modelo, extração do run
id, leituras e escritas do CLI) curados na v6.4, com fatos do substrato sondados no harness; regressões
e prova por mutação em todas as curas; rail r6 sobre os bytes finais como RODADA FINAL: reprova só
por P0 ou por afirmação falsa neste texto; P1/P2 novos viram anexo declarado e W1.1 (regra «rodada
final com anexo» do Owner, 10/09/2026, aplicada por decisão registrada no plano).

## Scope

- `.claude/hooks/_lib/launch_ledger.py` — biblioteca (canônico, novo)
- `.claude/hooks/check_workflow_launch.py` — hook PreToolUse/PostToolUse `Workflow` (canônico, novo)
- `.claude/settings.json` — 2 registrações `matcher: "Workflow"` (canônico)
- `templates/settings/settings.base.json` — as mesmas 2 registrações (canônico)
- `templates/settings/settings.user.json` — regenerado por `gen-settings-user-template.py --write`, com o hook em `_derivation.blocking_inclusions` e sua rota (canônico, derivado)
- `.claude/scripts/ceo-launches.py` — CLI `list · show · relaunch · check · bind · orphans · report` (novo)
- `.claude/scripts/env-inventory.json` — regenerado por `env-inventory-check.py --generate` (4 variáveis novas + drift pré-existente)
- `.claude/hooks/tests/test_check_workflow_launch.py` — 55 testes e2e (novo)
- `.claude/hooks/tests/test_template_dogfood_parity.py` — pinos 50/47 → 52/49 (relação 52 == 49 + 1 + 2)
- `.claude/scripts/tests/test_gen_settings_user_template.py` — lista ratificada: `RULED_IN` +2 registrações do hook, `EXPECTED_MISSING` 17 → 19
- `tests/unit/test_launch_ledger.py` — 29 testes unitários (novo)
- `scripts/build-plugin.py` — `GUARDED_CLIS` leva `ceo-launches.py` quando o guard é registrado
- `docs/workflow-recovery.md` — rito de recuperação, guard, override na chamada, validação de registros, precondições de distribuição e limitações declaradas (novo)
- `docs/COMMAND-SKILL-HOOK-MAP.md` — regenerado por `gen-command-skill-hook-map.py --write`
- `CHANGELOG.md` — cabeçalho de inventário rotulado «main after v1.4.0» (`_lib` 71→72) e entrada `[Unreleased]` da W1
- `CLAUDE.md` — §1 contagens (60 hooks / 49 ligados / 52 registrações / 72 `_lib`)
- `INSTALL.md` — contagens
- `README.md` — contagens
- `README.pt-BR.md` — contagens
- `docs/ARCHITECTURE.md` — contagens e árvore
- `docs/README.md` — contagens
- `docs/GUIA-COMPLETO.md` — contagens
- `docs/CTO-GUIDE.md` — contagens
- `npm/README.md` — contagens

## Evidência (sombra `wt-p190-w1v6`, branch `p190-w1-v6`, CLI 2.1.274, 17/09/2026)

    python3 -m pytest .claude/hooks/tests/test_check_workflow_launch.py tests/unit/test_launch_ledger.py \
      .claude/hooks/tests/test_template_dogfood_parity.py .claude/scripts/tests/test_gen_command_skill_hook_map.py \
      .claude/scripts/tests/test_gen_settings_user_template.py -q
      -> verde (55 e2e + 29 unit + 14 paridade + 20 mapa + 122 template user)
    prova por mutação (cópias descartáveis): 47 mutantes, um por proteção; todos mortos, exceto 5
      equivalentes declarados — tamanho limitado no fstat E no laço de leitura; proteção contra
      surrogate no hash e no literal (não na forma canônica); comparação por chave coberta pela
      camada defensiva de diferença canônica (e a própria camada, inalcançável com o diff correto);
      contagem de ordem equivalente com o diff correto
    suítes do pytest.ini como o CI (paralela e serial) sobre a v6.4
      -> 2 falhas: test_npm_docs_carry_no_bare_version_literal (na linha de base do main) e um teste
         de latência do planejador na passada serial sob contenção de CPU (passa isolado); nenhuma falha
         nova
    sonda do substrato (CLI 2.1.274): scriptPath com extensão .script aceito; ordem das chaves dos args
      preservada até o script; resposta de lançamento e de retomada com a linha `Run ID: wf_<id>`,
      e a retomada mantém o mesmo id
    python3 .claude/scripts/env-inventory-check.py --check                -> ENV-DRIFT: 0
    python3 .claude/scripts/gen-command-skill-hook-map.py --check        -> in sync
    python3 .claude/scripts/check-test-env-hygiene.py            -> OK (337 arquivos sinalizados, todos na allowlist)
    python3 .claude/scripts/gen-settings-user-template.py --check -> OK (template user bate com a derivação)
    python3 .claude/scripts/check-active-hooks-executable.py     -> OK: 95 referências presentes e executáveis
    python3 scripts/build-plugin.py --check                      -> manifestos em sincronia
    bash .claude/scripts/local/verify-counts.sh                  -> no drift detected
    bash .claude/scripts/check-contamination.sh                  -> ✓ contamination, ✓ personal-path
    git diff --numstat -- .claude/settings.json templates/settings/  -> só adições (24 / 24 / 29 linhas: settings.json, base, user — o user leva também a entrada de blocking_inclusions)
    add-workflow-hook-registration.py numa árvore fresca do main -> os 3 settings byte a byte iguais aos da sombra

Na cerimônia, a bateria roda as mesmas suítes do CI e compara o CONJUNTO EXATO de falhas contra
`suite-baseline.txt` (medido no main por `measure-suite-baseline.sh`); uma falha nova é rerrodada
isolada uma vez e só reprova se falhar de novo.

## Anexo — rail r6 (rodada final, regra «rodada final com anexo»)

O r6 não achou P0. Pela regra (b) apontou quatro frases do texto assinável que o código contradizia;
foram CORRIGIDAS NO TEXTO, sem mudança de comportamento, antes desta assinatura (docstrings de
`launch_ledger.py` e `check_workflow_launch.py`, `docs/workflow-recovery.md`, este sentinel e o plano):
(1) workflow nomeado — `relaunch` reproduz nome e args sem verificar o conteúdo salvo;
(2) ids ambíguos ou ausentes na resposta não geram linha `orphan` — o lançamento fica sem vínculo;
(3) depois de vinculada, a chamada forçada vira a referência do run — retomar com as mesmas entradas dá
`match`; (4) o `report` imprime contagens e a razão da regra de parada é calculada delas.

Declarado para a W1.1 (P2 de implementação, não bloqueia): `relaunch --out` usa um único `os.write` e
não confere escrita parcial — uma escrita curta entregaria cópia truncada com sucesso; cura: laço até
escrever tudo, e em falha remover o arquivo criado pela operação, com regressão.

## Consequência DECLARADA

A partir deste commit, neste repositório, todo lançamento da tool `Workflow` deixa um manifesto em
`<state-dir>/launches/` e uma retomada sobre `args` diferentes do manifesto vinculado por `tool_use_id`
ou manual é recusada por padrão. Nos consumidores, isso vale só depois de um `upgrade.sh` para uma
versão que contenha este commit, e só quando a cerimônia estiver gravada no install-state ou for
passada no upgrade, com `jq` disponível e sem `--no-settings-merge`; sem isso o arquivo do hook chega
sem registração e nada muda. Essa perna ainda não é exercitada pelo smoke-install (PLAN-190 W6,
pendente). O hook não emite evento de auditoria (registrar a ação em `_KNOWN_ACTIONS` + SPEC é
cerimônia do dono do audit — `PLAN-190-FOLLOWUP-audit-actions`); os manifestos são o registro.

## Residual

O guard vê a chamada da tool `Workflow`, não os `agent()` internos, e não impede o harness de
re-chavear o cache de resultados — impede o OPERADOR de retomar sobre entradas diferentes sem saber.
Não há checkpoint dentro de um `agent()` (limite do runner; W2 dá o checkpoint por fase em arquivo).
O run id é extraído da resposta por forma (`wf_<hex8>[-<hex>]`); outra versão da CLI ⇒ `bind` manual.
Adulteração deliberada do diretório de estado pelo mesmo usuário está fora do modelo de ameaça. Um
`scriptPath` num ponto de montagem travado pode segurar o hook até o timeout do harness. O CLI chamado
fora de qualquer projeto, sem `CLAUDE_PROJECT_DIR`, cai no resolvedor padrão pelo diretório corrente.
Declarados em `docs/workflow-recovery.md`: o ledger guarda `args` e snapshots sem poda e o `show`/
`relaunch` os imprimem de volta; lançamento e retomada precisam do mesmo diretório de projeto (outro
worktree ⇒ `no_manifest`); `git status` no `cwd` ainda pode rodar filtros configurados pelo
repositório; o gate de latência de hooks do CI ainda não perfila este hook; a retomada DELIBERADA de
`args` (estilo `args.resume`) exige a declaração na chamada e entra na contagem de forçados; o
`report` imprime as contagens por resultado e a razão da regra de parada é calculada a partir delas.
