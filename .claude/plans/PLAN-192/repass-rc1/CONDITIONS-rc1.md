# Condições do envelope — v1.4.1-rc.1 (patch fora de ordem: ledger + guard de retomada da tool Workflow)

Este arquivo propõe condições; não é aprovação nem assinatura. O envelope vincula o snapshot
bruto e os payloads redigidos das três partes; um `NO-GO` exige triagem e novo re-pass.
Regra do corte (a que o Owner ratificou para a v1.4.0 em 10/09 e 13/09/2026): `NO-GO` só por
condição declarada FALSA contra o código ou por P0; um P1 não declarado vai ao veredito sob
«NEW FINDINGS (annex)» como ANEXO assinado. O envelope do GA dirá, item a item, o que foi
curado e o que fica known-open — este texto NÃO promete uma versão para a cura.
Adopters: os repositórios do maintainer, subindo da v1.4.0 (ou da v1.3.0) por `upgrade.sh`.

## A. Condições DURAS (o texto da release foi escrito para dizer isto)

1. **O anexo P1 da v1.4.0 NÃO é curado nesta release.** As `conditions:` do envelope assinado
   `.claude/governance/pair-rail-verdict-v1.4.0.md` dizem que os anexos P1 dos vereditos da
   rc.1 e do GA ficavam «known-open no GA, cura na 1.4.1». Esta 1.4.1 é um patch FORA DE ORDEM
   que entrega o guard de Workflow aos adopters; por decisão do Owner (2026-09-18, PLAN-192
   OQ-1, «Declarar e seguir») ela NÃO cura nenhum daqueles achados. O anexo segue aberto, sem
   mudança, com a cura re-alvejada para a 1.4.2. Os itens são as seções «NEW FINDINGS
   (annex)» dos vereditos em `.claude/plans/PLAN-169/repass-rc1/` e
   `.claude/plans/PLAN-169/repass-ga/`, mais as condições daquele envelope. A entrada
   `[1.4.1]` do CHANGELOG e a anotação assinada da tag dizem o mesmo. Quatro arquivos citados
   por aqueles vereditos MUDAM nesta faixa (`CHANGELOG.md`, `CLAUDE.md`, `npm/README.md`,
   `templates/settings/settings.user.json`), e em nenhum deles a mudança toca o achado citado.
2. **O guard PODE BLOQUEAR, e o perfil `user` o mantém.** `check_workflow_launch.py` recusa uma
   retomada (`resumeFromRunId`) cujos `args` diferem do lançamento registrado, quando o vínculo
   do run é forte (por `tool_use_id` ou manual). A registração está em
   `templates/settings/settings.base.json` e em `templates/settings/settings.user.json`. Isto
   ESTENDE a condição 63 do envelope da v1.4.0: a superfície de hooks do perfil `user` não é
   advisory-only. Saídas: `CEO_WORKFLOW_RESUME_GUARD=0` (só aviso, ledger mantido),
   `CEO_WORKFLOW_LEDGER=0` (desligado), ou a declaração na própria chamada — uma `description`
   que começa por `CEO_WORKFLOW_RESUME_FORCE: <motivo>` — registrada como `mismatch_forced`.
3. **Num adopter o hook só passa a valer sob quatro condições juntas:** um `upgrade.sh` para uma
   versão que o contenha; a cerimônia de instalação gravada no install-state ou passada ao
   upgrade; `jq` disponível; e sem `--no-settings-merge`. Faltando uma, o arquivo do hook
   chega SEM registração e nada muda. Essa perna não é exercitada pelo smoke-install
   (PLAN-190 W6, pendente).
4. **O hook não emite evento de auditoria.** Os manifestos em `<state-dir>/launches/` são o
   registro; registrar a ação em `_KNOWN_ACTIONS` e no SPEC é cerimônia própria
   (`PLAN-190-FOLLOWUP-audit-actions`).
5. **As cinco CLIs de recuperação e aprovação não têm hook que as imponha.**
   `approval_gate.py`, `test_refs.py`, `mutant_sandbox.py`, `worktree_lock.py` e
   `phase_checkpoint.py` são chamadas por uma fase de workflow, por um rito de recuperação ou
   por uma pessoa. `worktree_lock.py` é um lock COOPERATIVO: um escritor que não o chama não é
   impedido. Elas landaram como scripts livres, com testes, e este re-pass é a primeira
   revisão cruzada delas.

## B. Limites declarados do guard (residual do texto assinado da W1, `075beed9`)

6. O guard vê a chamada da tool `Workflow`, não os `agent()` internos, e não impede o harness
   de re-chavear o cache de resultados: impede o OPERADOR de retomar sobre entradas diferentes
   sem saber. Não há checkpoint dentro de um `agent()` (limite do runner).
7. O run id é extraído da resposta por forma (`wf_<hex8>[-<hex>]`, a partir do rótulo
   `Run ID:`); outra versão da CLI pode exigir `ceo-launches.py bind` manual. Ids ambíguos ou
   ausentes na resposta deixam o lançamento sem vínculo, e sem vínculo forte não há bloqueio.
8. Um resume sobre um SCRIPT diferente com os mesmos `args` é só aviso por padrão
   (`CEO_WORKFLOW_SCRIPT_GUARD=enforce` para bloquear). Para um workflow NOMEADO, `relaunch`
   reproduz o nome e os `args` sem verificar o conteúdo salvo sob aquele nome.
9. Adulteração deliberada do diretório de estado pelo mesmo usuário está fora do modelo de
   ameaça. Um registro inconsistente (hash dos args, hash do script contra o snapshot, forma
   dos ids) é INCONCLUSIVO para o guard — nunca match, nunca bloqueio — e recusado como
   «exato» pelo `relaunch` (rc 7).
10. Um `scriptPath` é lido só como arquivo regular de até 8 MiB; num ponto de montagem travado
    a leitura pode segurar o hook até o timeout do harness. Falha de infraestrutura (arquivo
    ausente, import, timeout) é fail-OPEN: breadcrumb e `{}`.
11. O ledger guarda `args` e snapshots de script SEM poda, e `show`/`relaunch` os imprimem de
    volta: o que o operador passou em `args` fica em disco no diretório de estado do projeto.
12. Lançamento e retomada precisam do MESMO diretório de projeto (outro worktree ⇒
    `no_manifest`, só aviso); o CLI sem `CLAUDE_PROJECT_DIR` sobe do diretório corrente até o
    projeto que contém `.claude/`, excluindo o `$HOME`.
13. `git status` no `cwd`, usado para registrar a revisão do código, ainda pode rodar filtros
    configurados pelo repositório; o gate de latência de hooks do CI não perfila este hook.
14. `relaunch --out` cria sempre um arquivo NOVO (`O_EXCL`, nunca segue symlink) e, a partir
    desta release, entrega o arquivo inteiro ou nenhum arquivo (PLAN-190 W1.1).

## C. Escopo deste re-pass

15. Três partes, por raio de dano ao adopter, sobre o delta `v1.4.0..candidato`; o que fica de
    fora está declarado, com o motivo, em `.claude/plans/PLAN-192/repass-rc1/README-rc1.md`:
    testes e fixtures; `.claude/plans/**` e `docs/research/**`; `CLAUDE.md`; os dois arquivos
    de pin do codex e o par `release.sh` + manifesto ADR-192 (cada um sob a sua própria
    cerimônia assinada; nenhum dos quatro é entregue a adopters).
16. `docs/workflow-recovery.md` e `docs/approval-gate.md` NÃO são entregues a adopters (só
    `templates/docs/*` vira `docs/` no alvo). A rota que a mensagem de bloqueio nomeia é
    `ceo-launches.py relaunch`, que É entregue em `.claude/scripts/` e no build do plugin.
