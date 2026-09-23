# Condições do envelope — v1.4.1 (GA: promoção da v1.4.1-rc.1 após o hold de 24 h)

Este arquivo propõe condições; não é aprovação nem assinatura. O envelope vincula o snapshot
bruto e os payloads redigidos das três partes; um `NO-GO` exige triagem e novo re-pass.
Regra do corte (a mesma da rc.1 e da v1.4.0): `NO-GO` só por condição declarada FALSA contra o
código ou por P0; um P1 não declarado vai ao veredito sob «NEW FINDINGS (annex)» como ANEXO
assinado — known-open no GA. Adopters: quem SOBE da v1.4.0 (ou da v1.3.0) por `upgrade.sh`, e
quem instala a 1.4.1 do zero — o `install.sh`, direto ou pelo `npx ceo-orchestration`, cujo
pacote este GA publica no npm (condição 3).
Texto = este cabeçalho e as condições da rc.1, com mudanças só de TEXTO: a condição 1, cuja
lista dos arquivos citados que mudam nesta faixa estava errada e deu lugar à classe deles, e
que diz o que a decisão do Owner de 2026-09-22 fez com a cura do anexo da v1.4.0; a
condição 3, reescrita para a instalação nova; as referências que, lidas sob este cabeçalho,
ficariam falsas, re-ancoradas — no re-pass e no candidato da rc.1 (`7602fbe4`) quando falam do
que já aconteceu, no escopo do re-pass do GA quando falam do escopo; a seção C, que acrescenta
ao que fica fora o envelope assinado da rc.1 e diz o que «entregue a adopters» quer dizer e o que
o pacote npm empacota; e a seção E, nova, com um achado posterior ao re-pass da rc.1, declarado
no GA (condição 23). A lista exaustiva são as âncoras de
`.claude/plans/PLAN-192/derive-ga-kit-141.py`, que deriva este arquivo do da rc.1. As demais
condições seguem verdadeiras sobre o candidato do GA, porque nenhum código mudou desde a rc.1, e
ficam como estão.
Neste texto, «rodada N» sem outra qualificação é a rodada N do re-pass da rc.1 (seção D).
O candidato da rc.1 teve `GO-WITH-CONDITIONS` nas três partes; o veredito assinado está em
`51bd2345`, o commit da tag `v1.4.1-rc.1`. Entre ele e o candidato que o re-pass do GA revisa
mudaram só o envelope assinado da rc.1 (`.claude/governance/pair-rail-verdict-v1.4.1-rc.1.md`),
`CLAUDE.md` e arquivos de planos numerados (`.claude/plans/PLAN-<N>*`) — nenhum numa pathspec
das três partes. Entre a tag da rc.1 e o candidato revisado, o `OWNER-GA-CUT.sh` recusa o corte
se mudar caminho fora de `CLAUDE.md` e dos planos numerados (no G0, contra o HEAD, antes do
passo 5; e no passo 5, contra o candidato); sobre o candidato entra só o commit do veredito do
GA, que acrescenta o próprio envelope em `.claude/governance/`, os fields assinados e a
evidência do re-pass do GA. O runner grava, por parte, se algum arquivo da pathspec mudou desde
o candidato que a rc.1 revisou.
NADA foi curado entre a rc.1 e o GA: da tag da rc.1 ao candidato revisado, main recebeu só
`CLAUDE.md` e arquivos de planos numerados, fora de toda pathspec. Segue known-open no GA tudo o que
a rc.1 declarou aberto — nas seções A a D, que seguem aqui, e, dos três vereditos da rodada 3 da
rc.1 (`.claude/plans/PLAN-192/repass-rc1/verdict-rc1-{1,2,3}.txt`, pinados pelo envelope assinado
da rc.1), os achados sob «NEW FINDINGS (annex)» e os P2 —, nenhum curado por mudança de código
ou de texto; um P2 que dependia de a tag do GA ainda não existir perde o objeto com o próprio
GA. Os P1 desse anexo NÃO estão no «Known-open» da entrada `[1.4.1]` do `CHANGELOG.md`, que é
o texto do candidato da rc.1 e segue datada de 2026-09-18.
Nenhuma versão é prometida para a cura deles, nem para a do anexo P1 da v1.4.0 (condição 1).
O envelope assinado da rc.1 prometeu que o do GA diria, item a item, o que foi curado e o que
fica known-open. Para cada item que a rc.1 declarou aberto — os das seções A a D (na D, os das
rodadas 1 e 2) e, da rodada 3, os achados do anexo e os P2 — a resposta é a mesma: nenhum foi
curado entre a rc.1 e o GA, e todos seguem known-open. Os itens estão nestas condições e nos
vereditos das três rodadas da rc.1, pinados: os das rodadas 1 e 2 na seção D, os da rodada 3
pelo envelope assinado da rc.1. Os
dois P1 que o anexo da rodada 3 acrescentou são, pela forma: uma falha ao acrescentar a linha
de vínculo (`bind`) ao índice do ledger, depois de o manifesto ter sido atualizado, deixa o
vínculo anterior como autoridade para o guard; e o `approval_gate.py` aceita ids SIMBÓLICOS de
revisão (como `HEAD`) como revisão revisada e revisão final, e a comparação passa sem
identificar o commit revisado.

## A. Condições DURAS (o texto da release foi escrito para dizer isto)

1. **O anexo P1 da v1.4.0 NÃO é curado nesta release.** As `conditions:` do envelope assinado
   `.claude/governance/pair-rail-verdict-v1.4.0.md` dizem que os anexos P1 dos vereditos da
   rc.1 e do GA ficavam «known-open no GA, cura na 1.4.1». Esta 1.4.1 é um patch FORA DE ORDEM
   que entrega o guard de Workflow aos adopters; por decisão do Owner (2026-09-18, PLAN-192
   OQ-1, «Declarar e seguir») ela NÃO cura nenhum daqueles achados. O anexo segue aberto, sem
   mudança. Os itens são as seções «NEW FINDINGS (annex)» dos vereditos em
   `.claude/plans/PLAN-169/repass-rc1/` e `.claude/plans/PLAN-169/repass-ga/`, mais as
   condições daquele envelope. Naquela decisão a cura foi re-alvejada para a 1.4.2, e é o
   que dizem a entrada `[1.4.1]` do CHANGELOG e a anotação da tag (o bloco
   `RELEASE_HEADLINE` de `.claude/scripts/local/release.sh`, que entra assinado na anotação
   da tag da rc.1 e na do GA) — texto que o GA não muda. Em 2026-09-22 o Owner decidiu que
   a 1.4.2 é uma release expressa que NÃO leva essa cura e cujo material assinado a
   re-declara aberta. Hoje nenhuma versão está prometida para ela: onde o CHANGELOG e a
   anotação da tag dizem «1.4.2», vale esta condição. Arquivos citados por
   aqueles vereditos MUDAM nesta faixa (`v1.4.0..candidato`); pela forma, são os sítios de
   versão que o bump 1.4.0 → 1.4.1 reescreveu, texto de release e de documentação, os
   templates de settings (que ganham o hook novo: a registração e a rota de desligá-lo) e o
   contrato deste repositório (`CLAUDE.md`, não entregue). Nenhuma dessas mudanças cura um
   achado: as linhas que os vereditos citam por arquivo e linha seguem no candidato com o
   mesmo texto — várias em outro número de linha, deslocadas pelo texto acrescentado antes
   delas —, fora a linha de versão dos sítios de versão, que o bump reescreveu. Essa
   linha é a que o achado P1 de identidade do SPEC cita como a identidade corrente; `SPEC/`
   não mudou nesta faixa e segue com as identidades contraditórias, agora diante da 1.4.1.
   O texto desta condição na rc.1 enumerava quatro arquivos, e a lista estava errada:
   omitia os sítios de versão citados — entre eles os que esse achado cita.
2. **O guard PODE BLOQUEAR, e o perfil `user` o mantém.** `check_workflow_launch.py` recusa uma
   retomada (`resumeFromRunId`) cujos `args` diferem do lançamento registrado, quando o vínculo
   do run é forte (por `tool_use_id` ou manual). A registração está em
   `templates/settings/settings.base.json` e em `templates/settings/settings.user.json`. Isto
   ESTENDE a condição 63 do envelope da v1.4.0: a superfície de hooks do perfil `user` não é
   advisory-only. Saídas: `CEO_WORKFLOW_RESUME_GUARD=0` (só aviso, ledger mantido),
   `CEO_WORKFLOW_LEDGER=0` (desligado), ou a declaração na própria chamada — uma `description`
   que começa por `CEO_WORKFLOW_RESUME_FORCE: <motivo>` — registrada como `mismatch_forced`.
3. **Quando o hook passa a valer num adopter.** Numa instalação NOVA — o `install.sh`, direto ou
   pelo `npx ceo-orchestration`, cujo pacote este GA publica no npm — o hook chega REGISTRADO
   quando é o próprio `install.sh` que cria o `.claude/settings.json`: os dois templates de
   settings que ele usa (`base` e `user`) o registram, e a fusão com um stack soma hooks ao
   template sem tirar nenhum. Se o `.claude/settings.json` já existe, o `install.sh` não o toca e
   o arquivo do hook chega SEM registração. O bundle do plugin (rota experimental, não
   suportada) registra o hook no próprio `hooks/hooks.json`, gerado do template `user`. Num
   adopter que SOBE de versão, o hook só passa a valer sob quatro condições juntas: um
   `upgrade.sh` para uma versão que o contenha; a cerimônia de instalação gravada no
   install-state ou passada ao upgrade; `jq` disponível; e sem `--no-settings-merge`. Faltando
   uma, o arquivo do hook chega SEM registração e nada muda. A perna do upgrade não é
   exercitada pelo smoke-install (PLAN-190 W6, pendente). A frase da entrada `[1.4.1]` do
   `CHANGELOG.md` que diz que o hook só vale num adopter depois de um `upgrade.sh` está no
   parágrafo dirigido a quem SOBE («before upgrading») e só vale para esse caso; para uma
   instalação nova a entrada não diz quando o hook passa a valer, e ela não muda no GA.
4. **O hook não emite evento de auditoria.** Os manifestos em `<state-dir>/launches/` são o
   registro; registrar a ação em `_KNOWN_ACTIONS` e no SPEC é cerimônia própria
   (`PLAN-190-FOLLOWUP-audit-actions`).
5. **As cinco CLIs de recuperação e aprovação não têm hook que as imponha.**
   `approval_gate.py`, `test_refs.py`, `mutant_sandbox.py`, `worktree_lock.py` e
   `phase_checkpoint.py` são chamadas por uma fase de workflow, por um rito de recuperação ou
   por uma pessoa. `worktree_lock.py` é um lock COOPERATIVO: um escritor que não o chama não é
   impedido. Elas landaram como scripts livres, com testes e sem rodada de pair-rail; a
   primeira revisão cruzada delas foi a rodada 1 do re-pass da rc.1, e os achados dela sobre as
   cinco seguem abertos — ver a seção D.

## B. Limites declarados do guard (residual do texto assinado da W1, `075beed9`)

6. O guard vê a chamada da tool `Workflow`, não os `agent()` internos, e não impede o harness
   de re-chavear o cache de resultados: impede o OPERADOR de retomar sobre entradas diferentes
   sem saber. Não há checkpoint dentro de um `agent()` (limite do runner).
7. O run id é extraído da resposta por forma (`wf_<hex8>`, com um sufixo opcional `-<hex>` de
   1 a 8 dígitos), nesta ordem: uma chave `runId` ou `run_id` no nível de cima da resposta — a
   primeira das duas cujo valor tiver a forma vence, e NÃO há checagem de acordo entre elas nem
   com o texto; senão o id no rótulo `Run ID:`; senão o único token com a forma no texto. Só
   quando nenhuma das duas chaves tem a forma é que a ambiguidade conta: dois ids ROTULADOS
   diferentes não vinculam nada, e, sem nenhum rotulado, dois tokens diferentes também não;
   id ausente, idem. Um token
   cuja cauda não cabe na forma (`wf_12345678-123456789`) NÃO é rejeitado: é lido pelo prefixo
   que cabe (`wf_12345678`), e esse prefixo é o que se vincula. Outra versão da CLI pode exigir
   `ceo-launches.py bind` manual. Sem vínculo forte (por `tool_use_id` ou manual) não há
   bloqueio.
8. Um resume sobre um SCRIPT diferente com os mesmos `args` é só aviso por padrão
   (`CEO_WORKFLOW_SCRIPT_GUARD=enforce` para bloquear). Para um workflow NOMEADO, `relaunch`
   reproduz o nome e os `args` sem verificar o conteúdo salvo sob aquele nome.
9. Adulteração deliberada do diretório de estado pelo mesmo usuário está fora do modelo de
   ameaça. Um MANIFESTO inconsistente (hash dos args, hash do script contra o snapshot, forma
   dos ids) é INCONCLUSIVO para o guard — nunca match, nunca bloqueio — e recusado como
   «exato» pelo `relaunch` (rc 7). O ÍNDICE `launches.jsonl` não tem verificação de integridade
   própria — as linhas são validadas só pela forma: ver a condição 10.
10. Um `scriptPath` é lido só como arquivo regular de até 8 MiB; num ponto de montagem travado
    a leitura pode segurar o hook até o timeout do harness. No wrapper, um import do
    `launch_ledger` que falha, um diretório de estado indisponível, um stdin ilegível ou uma
    exceção que escape de `decide_pre`/`decide_post` terminam em breadcrumb no stderr e `{}` (a
    chamada segue); uma falha ao GRAVAR o registro não desfaz uma decisão que o guard já tinha
    computado. Isso NÃO cobre uma leitura INCOMPLETA do índice: `iter_index` devolve as linhas
    já lidas quando um `OSError` interrompe a leitura, e pula uma linha rasgada, sem sinalizar
    nenhum dos dois casos. Se a linha de vínculo mais recente de um run se perde assim, o guard
    compara contra o vínculo anterior que sobreviveu e pode BLOQUEAR uma retomada legítima; a
    saída é a declaração `CEO_WORKFLOW_RESUME_FORCE`. Achado P1 da rodada 1, aberto.
11. O ledger guarda `args` e snapshots de script SEM poda, e `show`/`relaunch` os imprimem de
    volta: o que o operador passou em `args` fica em disco no diretório de estado do projeto.
12. Lançamento e retomada precisam do MESMO diretório de projeto. De outro worktree, ou para um
    run lançado antes de o hook existir, o guard não acha manifesto: grava `no_manifest` no
    manifesto da chamada nova e a chamada segue SEM aviso e sem bloqueio (achado P1 da rodada 1,
    aberto). O CLI sem `CLAUDE_PROJECT_DIR` sobe do diretório corrente até o projeto que contém
    `.claude/`, excluindo o `$HOME`.
13. `git status` no `cwd`, usado para registrar a revisão do código, ainda pode rodar filtros
    configurados pelo repositório; o gate de latência de hooks do CI não perfila este hook.
14. `relaunch --out` abre o destino com `O_CREAT|O_EXCL` (não abre arquivo que já existe; um
    symlink no destino é recusado, nunca seguido) e, a partir desta release, escreve em laço
    até o último byte (PLAN-190 W1.1). Isso NÃO é «o arquivo inteiro ou nenhum arquivo», e a
    limpeza NÃO é garantida como «só o arquivo desta chamada». Quatro casos, todos abertos:
    (a) uma interrupção que não é `OSError` (Ctrl-C, um sinal) no meio da escrita não é
    tratada e pode deixar um parcial no destino, sem mensagem; (b) numa falha TRATADA — erro
    de I/O, escrita sem progresso, erro no `close` — o comando devolve rc 2 e TENTA remover o
    parcial em DOIS passos, `lstat` do destino comparado ao inode que criou e depois `unlink`
    pelo nome: se o `lstat` ou o `unlink` falha, o parcial FICA e a mensagem o diz; (c) esses
    dois passos não são uma operação atômica: um escritor concorrente que substitua o destino
    entre o `lstat` e o `unlink` PERDE o arquivo dele, e a mensagem ainda diz que o parcial
    foi removido (achado da rodada 2); (d) se a segunda leitura do snapshot falha, o comando
    imprime o cabeçalho «exact recorded call», não cria arquivo nenhum e sai rc 0 (achado P2
    da rodada 2) — a cópia só existe quando a saída diz «snapshot copied to». A anotação da
    tag — o bloco `RELEASE_HEADLINE` de `.claude/scripts/local/release.sh`, canônico e
    assinado na relmeta-141 — resume a correção como «o arquivo inteiro ou nenhum arquivo»;
    ela deve ser lida com estes limites. A cura estrutural (temporário exclusivo, publicação
    por `link` sem substituição, nenhum `unlink` no destino) fica para depois desta release,
    por decisão do Owner (2026-09-18).

## C. Escopo do re-pass do GA (as três partes da rc.1)

15. Três partes, por raio de dano ao adopter, sobre o delta `v1.4.0..candidato`; o que fica de
    fora está declarado, com o motivo, em `.claude/plans/PLAN-192/repass-ga/README-ga.md` (§4, e
    §0 para o que o GA acrescenta):
    testes e fixtures; `.claude/plans/**` e `docs/research/**`; `CLAUDE.md`; os dois arquivos
    de pin do codex e o par `release.sh` + manifesto ADR-192 (cada par sob a sua própria
    cerimônia assinada). Desses quatro, os três de `.claude/governance/` não são entregues a
    adopters. O `.claude/scripts/local/release.sh` É entregue, e só pelo `upgrade.sh`: ele
    enumera `.claude/scripts/` recursivamente e o predicado `_framework_path_excluded`
    (`scripts/_framework_manifest_set.sh`) não exclui `.claude/scripts/local/`, enquanto a
    instalação fresca copia só o nível de cima de `.claude/scripts/`. Ele fica fora do
    re-pass porque a mudança dele nesta faixa é a relmeta-141 — o bloco POR-RELEASE
    (`TARGET_BASE`, título, escopo, headline) e o comentário que aponta o derivador —, assinada
    pelo Owner em cerimônia própria (`.claude/plans/PLAN-192/relmeta/`). A divergência
    instalação × upgrade sobre `.claude/scripts/local/` é achado da rodada 1, aberto. No GA fica
    fora também o envelope assinado da rc.1, `.claude/governance/pair-rail-verdict-v1.4.1-rc.1.md`:
    material de release, que o `install.sh` e o `upgrade.sh` não copiam para o alvo. Neste
    texto, «entregue a adopters» quer dizer copiado para a árvore do adopter pelo `install.sh`
    ou pelo `upgrade.sh`. O pacote npm, que o GA publica, empacota `.claude/` com as exclusões
    do passo «Stage bundle» do `npm-publish.yml`, e elas não excluem `.claude/governance/`.
16. `docs/workflow-recovery.md` e `docs/approval-gate.md` NÃO são entregues a adopters (só
    `templates/docs/*` vira `docs/` no alvo). A rota que a mensagem de bloqueio nomeia é
    `ceo-launches.py relaunch`, que É entregue em `.claude/scripts/` e no build do plugin.

## D. O que as rodadas 1 e 2 acharam, e o que mudou desde então

17. A rodada 1 rodou sobre o candidato `9e9840b2fc6c033498a0c12c65178a5254d0b04e` e está
    arquivada em `.claude/plans/PLAN-192/repass-rc1-20260918-NOGO-r1/`, com a triagem em
    `record.md`. Os três vereditos dela entram neste material assinado pelo sha256:
    `verdict-rc1-1.txt` f46ebb9e8e7d33a2e9a0295a4daccc4e2c07214cf9497b4922a4734ffae12e6a,
    `verdict-rc1-2.txt` 13716c568ddd997d2d5832d7f943b739e12dd6ab1a06b68bd6a4e8cee274b85e,
    `verdict-rc1-3.txt` a4d9c15739622c8585c56bdef53df35ea31e0c5087dd0a55b684235cac06af49.
18. O delta `9e9840b2..7602fbe4` (o candidato da rc.1) toca só `CHANGELOG.md`,
    `docs/workflow-recovery.md`,
    `docs/approval-gate.md` e arquivos sob `.claude/plans/` (o kit do re-pass, o plano e as
    rodadas 1 e 2 arquivadas): nenhum arquivo sob `.claude/hooks/`, `.claude/scripts/`, `scripts/` ou
    `templates/` mudou. As cinco condições falsas (7, 10, 12, 14, 15) foram reescritas para
    dizer o que o código faz, e as condições 5 e 9 foram ajustadas com elas. As frases que a
    rodada 1 contestou por arquivo e linha — `CHANGELOG.md:68` e `:81`,
    `docs/workflow-recovery.md:127`, `docs/approval-gate.md:31` e `:85` — foram reescritas, e
    os três arquivos ganharam a lista dos achados abertos; isto não afirma que não reste
    nenhuma outra frase imprecisa neles.
19. Todos os achados de CÓDIGO da rodada 1 seguem ABERTOS neste candidato: os P1 sob «NEW
    FINDINGS (annex)» e os P2 dos três vereditos do item 17, inclusive os que as condições 10,
    12, 14 e 15 citam; o que mudou foi o texto que os contradizia. Nenhum é P0 segundo aqueles
    vereditos. A entrada `[1.4.1]` do CHANGELOG os resume sob «Known-open (found by this
    release's cross-review)».
20. A rodada 2 rodou sobre o candidato `3ed81cf657b3d22d012b1e32269671e86f3e4030` e está
    arquivada em `.claude/plans/PLAN-192/repass-rc1-20260918-NOGO-r2/`, com a triagem em
    `record.md`. Os três vereditos dela entram neste material assinado pelo sha256:
    `verdict-rc1-1.txt` ec86430e8fa41f919a896ef2ce9d947efb382168edd826a7d0c61cdbd9e36f70,
    `verdict-rc1-2.txt` 023d8f12495eea0e4dc7811267eef23ba45ead3703d37e598697c92c6dde57af,
    `verdict-rc1-3.txt` 762f0cf19311247f537a4dde9afd0d1ff2afff25c682212ff225e670a8d7f468.
    As partes 1 e 3 deram `GO-WITH-CONDITIONS`; a parte 2 deu `NO-GO` por uma frase da
    condição 14 — «remove o parcial, só o inode que esta chamada criou» —, repetida no
    `### Fixed` do CHANGELOG: a limpeza é um `lstat` seguido de um `unlink`, não uma operação
    atômica. Conferido contra o código: o revisor tem razão.
21. Da rodada 2 ao candidato da rc.1 mudou só texto, nos mesmos arquivos do item 18: a condição 14 foi
    reescrita e a 7 ganhou uma precisão de ordem; o `### Fixed` e o «Known-open» do CHANGELOG
    e as listas de abertos dos dois docs de operador declaram a corrida da limpeza e os
    achados novos da rodada 2; `docs/approval-gate.md` deixou de chamar de «shipped default»
    uma política que é fixture de `tests/` e não é entregue a adopters.
22. Todos os achados de CÓDIGO da rodada 2 seguem ABERTOS neste candidato: os três P1 sob
    «NEW FINDINGS (annex)» da parte 3 (chave JSON duplicada em `approval_gate.py`; arquivo
    ilegível tratado como ausência em `test_refs.py`; descendentes vivos depois de um timeout
    em `mutant_sandbox.py`), o P1 da parte 2 (a corrida da condição 14) e os P2 dos três
    vereditos do item 20. Nenhum é P0 segundo aqueles vereditos.

## E. Declarado no GA (achado depois do re-pass da rc.1)

23. **O hook copia os bytes do arquivo que um `scriptPath` nomeia, antes da decisão de permissão
    do harness.** No PreToolUse da tool `Workflow`, `check_workflow_launch.py` (por
    `_lib/launch_ledger.py`) lê o arquivo regular de até 8 MiB que `tool_input.scriptPath` nomeia
    — quando a chamada não traz o texto do script em `script` —, por caminho absoluto ou relativo
    ao `cwd` da chamada, dentro ou fora do projeto, e grava uma cópia dele (`<launch_id>.script`,
    modo 0600) em `launches/`, no diretório de estado do projeto. O hook roda antes de o harness
    decidir a permissão da chamada: a cópia é gravada ainda que uma regra de negação de leitura
    cubra aquele caminho, e essa regra não cobre a cópia, que fica em outro caminho.
    `ceo-launches.py relaunch` imprime o caminho da cópia, e `relaunch --out` a copia para um
    arquivo novo. A classe, pela forma: um hook que roda antes da decisão de permissão e persiste
    os bytes de um caminho que o harness pode negar. É known-open no GA e NÃO está no
    «Known-open» da entrada `[1.4.1]` do `CHANGELOG.md`; a cura está alvejada para a 1.4.2, em
    cerimônia canônica. Saída: `CEO_WORKFLOW_LEDGER=0` desliga o hook inteiro (ledger, guard e
    cópia).
