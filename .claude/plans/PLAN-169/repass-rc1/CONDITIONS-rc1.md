# Condições do envelope — v1.4.0-rc.1 (pré-release; hold mecânico de 24 h antes do GA)

> Emendado depois da rodada 2 a pedido dos revisores (renumeração dos itens 15/16
> duplicados; condições 4, 5 e 7 ampliadas para o que o código faz; item 16 com as curas
> livres da rodada 2; itens 25 a 30 novos; condições 15, 18 e 21 corrigidas pelas partes 5 e 6). A versão que os revisores da rodada 2
> receberam como DATA tem sha256 `7f0dd2513413039c07a09e58697074e6305a8a0460bdd72b774a2f8f3207b12c` (pinada em
> `PROVENANCE-rc1.md` da rodada 2).

Cada item descreve o que o código FAZ nesta rc, para que a assinatura não afirme
mais do que aconteceu. Fonte: re-pass do candidato (codex 0.147.0 pinado, modelo
gpt-5.6-sol, 6 partes) + verificação adversarial de cada achado contra o código e
os textos de desenho ratificados (registros em `PLAN-169/repass-rc1-20260908-NOGO/`).
Adopters desta rc: os repositórios do próprio maintainer, subindo da v1.3.0 em modo
cópia. «Cura antes do GA» = entra na rc.2 por cerimônia assinada, com controle positivo.

## A. Condições DURAS (o texto da release foi estreitado para dizer isto)

1. **Rota com transform sem renderer sai 0.** `scripts/upgrade.sh` conta uma rota
   cujo transform o binário não sabe renderizar como `SKIP` nomeado e o run termina
   «Upgrade complete», rc 0 — as duas outras formas de tabela envenenada saem 3.
   Inalcançável com a tabela de seis linhas que a rc entrega; o CHANGELOG [1.4.0]
   nomeia a exceção. Cura antes do GA (~6 linhas + controle positivo).
2. **Undemote das 7 skills VETO só em install FRESCO.** Uma instalação v1.3.0 que faz
   upgrade mantém o seu `skillOverrides` (o upgrader preserva settings fora das
   migrações aditivas enumeradas). O CHANGELOG foi estreitado; a migração
   baseline-aware é cura antes do GA.
3. **`uninstall.sh` não desinstala registros `LINK` da v1.3.0.** O parser lê todo
   registro como `<sha> <relpath>`; um registro `LINK <relpath> <target>` (instalação
   `--link`) é RECUSADO com nome (falha fechada — nada é apagado fora do alvo), o
   symlink fica e o manifesto é mantido. Zero efeito em modo cópia (o caso desta rc).
   Cura antes do GA: parser com a forma `LINK` (`PLAN-169-FOLLOWUP-link-uninstall`).

27. **Os stores de estado dos planos (scratchpad SQLite de `/resume` e handoffs) mudam de
    diretório e NÃO são migrados.** Um repositório v1.3.0 com plano ATIVO abre um store
    NOVO e vazio depois do upgrade; os arquivos antigos ficam intactos em
    `$HOME/.claude/projects/ceo-orchestration/state/`. Rotas documentadas
    (docs/UPGRADE-PROCEDURE.md): `CEO_PROJECT_NAME=ceo-orchestration` até o plano fechar, ou
    copiar o diretório para o novo caminho. A migração automática (baseline-aware) é a
    condição DURA que o CHANGELOG promete e entra antes do GA (rodada 2, parte 4).
    (Numeração estável: os itens são numerados na ordem em que entraram no envelope,
    não na ordem das seções, para que as referências dos revisores continuem válidas.)

## B. Residuais DECLARADOS por desenho ratificado (não mudam na rc.2 sem decisão do Owner)

4. **Merge de settings é aditivo por roster da cerimônia gravada** (Pacote E, ADR-197):
   uma registração de hook ou chave `.env` removida à mão pelo adopter VOLTA no
   upgrade — com log nomeado («REGISTERED: …») e backup `settings.json.pre-h8-merge`;
   remoção deliberada exige `--no-settings-merge`. Dois textos ficam INEXATOS até a
   próxima cerimônia canônica: o `--help` («registers new lifecycle hooks», o mecanismo
   antigo) e o RESUMO FINAL do upgrade, que afirma que só hooks novos e folhas
   baseline-aware mudaram enquanto chaves `.env` ausentes também foram re-adicionadas
   (rodada 2, parte 1).
5. **Arquivo pré-existente byte-igual à SAÍDA RENDERIZADA entra no manifesto como
   framework-owned** (`install.sh` e `upgrade.sh`, paridade entre os dois). Isso não é
   só um efeito de `uninstall`: a linha do manifesto vira PROVENIÊNCIA operacional que
   ações seguintes consomem — (a) um `CODEOWNERS` autoral igual ao render é pulado mas
   registrado, e se o adopter depois o esvaziar de propósito para desligar o roteamento
   de revisão, `_codeowners_provenance` lê a linha como prova de entrega e o
   install/upgrade seguinte o RE-RENDERIZA, religando o roteamento em silêncio; (b)
   `doctor.sh` passa a classificar edições posteriores como drift do adopter e pode
   fazer backup e SOBRESCREVER o arquivo sob `--repair` confirmado; (c) `uninstall`
   o apaga. O arquivo é igual ao render, não necessariamente aos bytes literais do
   template público. Cura antes do GA: exigir registro de entrega anterior, não
   igualdade nua, antes de `_append_delivered_template` (rodada 2, partes 2 e 3).
   Decisão de posse = wave com o Owner.
6. **O handle do install-state (UNSIGNED, `request.github_owner`) é REPLAY do pedido
   gravado, não proveniência** (ADR-155; round-7 F4): CODEOWNERS ausente + handle
   gravado ⇒ render sem flag. Quem edita o install-state edita o CODEOWNERS
   diretamente; tensão com `docs/threat-model.md` T-008 registrada; hardening (flag
   explícita) = decisão do Owner.
7. **Registros `LINK` herdados da v1.3.0 são autorizados SÓ PELO CAMINHO** (`upgrade.sh`
   põe todo relpath `LINK` anterior em `FMS_LINK_PATHS`; `_wbm_link_allowed` confere
   apenas a pertença do relpath) e o escritor do manifesto grava o `readlink` ATUAL: um
   symlink já registrado que o adopter re-apontou tem o alvo novo lavado para a baseline
   do framework no upgrade seguinte, e um over-claim feito pela v1.3.0 sobrevive. Fora da
   coorte copy-mode desta rc, mas é o que o código faz. Cura OBRIGATÓRIA antes do GA:
   filtrar `FMS_LINK_PATHS` aos registros únicos cujo alvo gravado é igual ao `readlink`
   vivo (rodada 2, parte 2).
8. **Tabela de rotas ausente/corrompida no CHECKOUT do framework**: `install.sh` ainda
   copia `docs/` e `.github/` fixos e reporta sucesso; e `_wbm_route_table` aceita
   symlink no leaf (`-f`). A tabela vive no checkout que executa (mesma superfície do
   próprio script) — fora do modelo de ameaça como ataque; fail-closed = cura antes do GA.
9. **Gramática do handle aceita `owner-` e hífens consecutivos** (GitHub os rejeita);
   apertar no produtor e no consumidor = cura antes do GA.

## C. Hardening não bloqueante (nomeado para não se perder)

10. `--protocol-source` com caracteres fora do allowlist do consumidor é REJEITADO com
    WARNING nomeado e o ponteiro são é PRESERVADO (reproduzido: diff vazio); só um
    ponteiro também irreproduzível cai na rota D3 ratificada. Validar no produtor.
11. `chmod` falho na entrega de template é silencioso (doutrina fail-open em infra); o
    classificador de paridade acusa `MODE_DIFF` e o upgrade seguinte normaliza.
12. `CODEOWNERS` e `.template` podem coexistir através de runs (classe documentada em
    PLAN-183 §9.3; o `.template` é inerte para o GitHub).
13. O comentário de `.claude/settings.json` cita o caminho legado do audit-log
    (`projects/ceo-orchestration/`); o caminho real é o slug nativo por projeto
    (`runtime_paths.py --state-dir`). Canônico; próxima cerimônia.
14. **O manifesto de instalação não é autenticado** (`uninstall.sh` o diz nas próprias
    linhas 89-92): um registro seguro-na-forma é tratado como prova de posse. Escrita
    same-UID no alvo já é game-over pelo modelo de ameaça (§T-05); sidecar autenticado
    = item de v2. O cabeçalho do script deixa de anunciar um `exit 3` de HMAC que não
    existia.
15. **O backup pré-uninstall usa caminho previsível sem criação exclusiva**
    (`.claude.backup-uninstall-<timestamp>.tar.gz` + `.hmac`): um link pré-plantado
    com esse nome faz a escrita seguir para outro inode (reproduzido: 578 bytes fora do
    alvo, same-UID). Mesma classe do ADR-196 num sítio não convertido; cura antes do
    GA: `_wbm_dst_refuses` + criação exclusiva (`PLAN-185-FOLLOWUP-uninstall-backup-confine`).
16. CURADO nesta rc (livres): a recusa/preservação do `uninstall.sh` sai 5/6 em vez de 0
    (dry-run segue 0); o template de CI entregue verifica o SHA-256 do actionlint antes
    de extrair (o vivo já fazia; a v1.3.0 rodava `bash <(curl)` sem pin) e o gate de
    sintaxe YAML instala o parser em CI e FALHA se ele faltar, em vez de pular em verde.
    Rodada 2 (parte 3): o parser do manifesto do `uninstall.sh` é TOTAL — leitura
    EOF-safe (um registro final sem newline era descartado), gramática estrita por
    registro (`<sha256> <relpath>` ou `LINK …`), bytes de controle/registro malformado
    REFUSADOS e contados, manifesto vazio/só-comentários REFUSADO e mantido — antes,
    tudo isso zerava os contadores, apagava o ledger e saía 0 com arquivos do framework
    no lugar; `--help` imprime o cabeçalho inteiro (os códigos de saída estavam
    escondidos além da linha 30); `benchmarks.yml.template` reporta o status real em vez
    de `$?` depois de `!`; `templates/codex/pre-push-review-gate.sh` diz a verdade sobre
    não ser entregue (item 26) e usa `--not --remotes` no range de branch nova.
17. **PostCompact reinjeta campos do snapshot em `additionalContext` com sanitização só de
    não-imprimíveis** (`check_postcompact_reinject.py`): um NOME de arquivo `finish-*.sh`
    ou um valor de snapshot adulterado atravessa a fronteira da compaction como texto
    instruction-adjacent (reproduzido byte a byte). O render é pré-existente na v1.3.0; o
    fallback session-scope da v1.4.0 o torna o caminho dominante. Cura antes do GA:
    validação estrutural full-match por campo (cerimônias como contagem/ponteiro fixo)
    — CURADA no pack `rc1-cure`. Segunda rota (rodada 2, parte 5): o `plan_id` que
    `resolve_plan_id()` lê de JSON de auditoria NÃO verificado entrava no pointer
    «Active plan: …» com checagem só de prefixo (`startswith("PLAN-")`), e a checagem
    estrita de `audit_emit.py` só sanitiza o EVENTO, depois de o valor cru já ter entrado
    no contexto — também curada no pack (`fullmatch` `PLAN-NNN`; pointer dropado e contado).
18. **PreCompact segue symlink em `PLAN-NNN/LEDGER.md`** e copia até 5 headings `## `
    (≤ 160 chars) de um arquivo fora do repo para o BLOB do snapshot (nunca para o
    `additionalContext`); quem cria o symlink já lê o alvo (same-UID). Cura antes do GA:
    `lstat` + `O_NOFOLLOW` (superfície nova da W2 US7).
19. **Orçamento de 2,5 s do PreCompact não chega ao lock de 5 s do `state_store`** (medido
    5,14 s sob holder vivo > 2,4 s): sob contenção rara o harness mata o hook e o snapshot
    e o evento de auditoria se perdem em silêncio; a compaction nunca bloqueia. Cura curta
    na mesma cerimônia (lock_timeout com folga abaixo do timeout do harness).
20. `SessionEnd` varre nomes modificados por dois scanners antes de fixar o desfecho; numa
    cauda rara de 50 ms um `written` real sai como `error`/UNAVAILABLE (contrato assinado
    r6/r7/r22 — instrumento, sem impacto de segurança). O GC do scratchpad NUNCA apaga
    `.sqlite.lock` (declarado em `scratchpad_lib.py`): um inode de 0 bytes por sessão sem
    plano resolvido. A claim de crescimento limitado NÃO vale nem para bytes (rodada 2,
    parte 5): o GC pára nos primeiros 20.000 entries do diretório e aplica o cursor só
    dentro desse prefixo; quando os `.sqlite.lock` permanentes ocupam o prefixo, arquivos
    SQLite/WAL/SHM expirados além dele ficam inalcançáveis indefinidamente (starvation de
    prefixo). Cura antes do GA: paginação justa pré-cap ou sharding, para todo escopo ser
    varrido.
21. **First-mint do salt por projeto não é exclusivo** (`injection_salt.py`): duas sessões
    que enviam o PRIMEIRO prompt depois do upgrade podem cunhar salts diferentes e truncar
    o mesmo arquivo; o `prompt_sha256` das perdedoras fica irreproduzível (reproduzido:
    5/5 rodadas, 6/6 salts distintos); a cadeia HMAC segue íntegra. Pré-existente na
    v1.3.0; o upgrade reabre UM momento de mint por projeto. Mitigação operacional: abra
    a primeira sessão de cada repositório SOZINHA depois do upgrade. Cura antes do GA:
    `O_CREAT|O_EXCL|O_NOFOLLOW` e a perdedora relê; na mesma cerimônia, a escrita do
    marcador `salt-minted.json` deixa de seguir symlink (classe same-UID, fora do modelo
    de ameaça como ataque — `docs/threat-model.md` Tier-2).
22. **Locks em diretórios diferentes entre hooks v1.3.0 e v1.4.0** só ocorrem com
    `CEO_AUDIT_LOG_PATH` definido E as duas gerações de hooks correndo durante o upgrade;
    o efeito é appends intercalados no mesmo log = alarme de `verify_chain` (tamper-
    EVIDENTE, não silencioso). Regra: faça o upgrade sem nenhuma sessão aberta no
    repositório (docs/UPGRADE-PROCEDURE.md).
23. **O campo `project` dos eventos carrega o caminho absoluto do repositório** — campo-base
    contratual (`SPEC/v1/audit-log.schema.md` §501), preenchido assim por TODO emissor nas
    duas versões: não há exposição nova; a frase «slug/path never reaches the wire» no
    docstring de `audit_emit.py` e a redação DENIED do SPEC estão erradas e serão
    corrigidas no pack `rc1-cure` (texto, não comportamento). EXCEÇÃO medida (rodada 2,
    parte 5): os dois emissores da família de compaction (`check_precompact_continuity.py`,
    `check_postcompact_reinject.py`) NÃO preenchem `session_id` nem `project` —
    `emit_generic()` não os sintetiza — logo, num log de auditoria compartilhado ou com
    override, esses eventos não são atribuíveis a repositório nem a sessão. Cura antes do
    GA: passar o session id da entrada do hook e a raiz do projeto resolvida aos dois
    emissores, com testes de wire exato. Idem o único produtor de `ledger_entry_rejected`
    (`ledger_provenance.py`): não inclui `project` nem `session_id` (o wrapper usa `""`)
    — rejeições não atribuídas num log compartilhado. A afirmação desta condição vale
    para os emissores que TRANSPORTAM o caminho, não para todos (rodada 2, parte 6).
24. Follow-ups pós-GA (P2): chave de cache do `spool_writer` omite `cwd` quando qualquer
    candidato é absoluto (canto: override RELATIVO + processo longo + `chdir`); o marcador
    de rejeição de `ledger_provenance` diz «DISCARDED» num corpo que a postura advisory
    devolve (módulo sem consumidor fora de testes).

25. `_up_tmpbase` (`scripts/upgrade.sh`) detecta `TMPDIR` dentro do alvo e cai para `/tmp`,
    mas não revalida o fallback: com `TARGET=/tmp` (e `TMPDIR=/tmp`) o snapshot da tabela
    de rotas nasce DENTRO do alvo, inclusive em `--dry-run`; o trap o remove, um `SIGKILL`
    o deixa lá — contra a garantia comentada de que scratch nunca entra no target. Cura:
    validar fisicamente cada candidato de diretório temporário e recusar, nomeado, se
    nenhum ficar fora do alvo (rodada 2, parte 1).
26. **O backstop de push do Codex NÃO é entregue pelo installer**: o roster de emissão
    `--harness codex` (`scripts/_codex_harness.sh`) ships `hooks.json`, `ceo.rules` e
    `AGENTS.md`; `templates/codex/pre-push-review-gate.sh` dizia que o installer o copiava
    para `.git/hooks/pre-push` — um repositório v1.3.0 subido com `--harness codex` fica
    sem gate de push (matar ou esgotar o Stop gate permite um push canônico). O cabeçalho
    do template passa a dizer isto e como instalar à mão; o range de branch nova deixou
    de se auto-subtrair (`--not --remotes`, como no twin do Grok). Porte completo (roster
    + ciclo de vida manifesto/uninstall/backup/restore) = item nomeado da rc.2
    (rodada 2, parte 3).
28. Todo run habilitado do PostCompact limpa um marcador sob `<repo>/.claude/state` sem
    verificar se `state` é symlink (`marker.unlink()`; o escritor de pressão idem quando
    armado): um adopter com `.claude/state -> /external/state` tem o arquivo externo
    homônimo apagado. O rail de pressão de contexto (`audit_emit.py`) escreve o marker e o
    `.gc-shard-cursor` pelo mesmo ancestral e o GC pode apagar até 32 markers expirados
    no alvo externo — o `O_NOFOLLOW` protege só o arquivo final, não o ancestral, apesar
    do comentário «SYMLINK-SAFE». Condição assinada: `.claude/state` deve ser um diretório
    REAL dentro do repositório nesta rc; cura = abrir o diretório com
    `O_DIRECTORY|O_NOFOLLOW`, operar por `dir_fd` e validar identidade antes de
    `replace`/`unlink` (rodada 2, partes 5 e 6).
29. **Os overrides de diretório NÃO são atômicos por família nesta rc**: com
    `CEO_PROJECT_STATE_DIR`, `audit_hmac` mantém chave, último HMAC e contador no override
    enquanto log e spool mudam para o slug nativo — a primeira linha do log novo encadeia
    numa cabeça ausente (síncrono) ou o contador antigo excede o log novo (async), e
    `verify_chain` acusa `hmac_mismatch`/`chain_length_truncation` logo depois de um
    upgrade legítimo; com `CEO_AUDIT_LOG_PATH` o log muda mas os spools ficam no diretório
    nativo. Condição assinada: NÃO usar esses overrides através do upgrade v1.3.0→rc.1;
    cura antes do GA = uma única resolução da matriz de overrides para log, HMAC e spool,
    com migração/reset explícito dos sidecars (rodada 2, parte 6).
30. O slug nativo por projeto (`runtime_paths.py`) NÃO é único: `/srv/a-b/c` e `/srv/a/b-c`
    produzem o mesmo `-srv-a-b-c` e compartilhariam log, chave e salt. O código o admite;
    as claims gerais de isolamento por projeto não. Ressalva declarada + controle positivo
    de unicidade dos slugs dos repositórios em escopo; desambiguação = decisão própria
    (rodada 2, parte 6, P2).

## D. O que este re-pass NÃO cobriu

- `.claude/scripts/**` ficou fora por orçamento e permanece coberto apenas pelas
  rodadas por wave (README-rc1.md §4).
- Limite same-UID (cadeias HMAC separadas por diretório e chave, não por privilégio);
  checksums por tarball do npm não automatizados; fence-shadow variante 5 (signatário
  == Owner) fora do modelo de ameaça — residuais herdados do trem, já no CHANGELOG.
