# Condições do envelope — v1.4.0-rc.1 (pré-release; hold mecânico de 24 h antes do GA)

> Emendado depois da rodada 2 a pedido dos revisores (renumeração dos itens 15/16
> duplicados; condições 4, 5 e 7 ampliadas para o que o código faz; item 16 com as curas
> livres da rodada 2; itens 25 a 30 novos; condições 15, 18 e 21 corrigidas pelas partes 5 e 6). A versão que os revisores da rodada 2
> receberam como DATA tem sha256 `7f0dd2513413039c07a09e58697074e6305a8a0460bdd72b774a2f8f3207b12c` (pinada em
> `PROVENANCE-rc1.md` da rodada 2).

> Emendado (v6) depois da wave-rc1cure (`5518888`) e da rodada 3, parte 1: itens 1, 9,
> 17, 18, 21 e 23 marcados como CURADOS pelo pack assinado; item 8 reescrito (laundering
> pelo snapshot); itens 31 e 32 novos. A versão que os revisores da rodada 3 receberam
> (v7: item 16 reescrito para o pack 2; item 26 com `--root`; itens 33-35 novos. v8: condição 23 com mais três emissores; condição 18 diz que só o LEAF é confinado; itens 36-38. v9: condição 21 declara a janela do first-mint; condição 23 nomeia a representação; itens 39-40 DUROS (custo e credencial) e 41. v10: itens 8 (frestas b/c) e 31 marcados CURADOS em `144b0ef` (wave-rc1cure2); condição 5 remete ao 42; itens 42-43 DUROS (posse por igualdade histórica; diretório de backup não confinado) e 44 — rodada 4, parte 1. v11 (rodada 5, parte 1): 42 vale para igualdade ATUAL ou histórica e diz por que a cura literal não serve; 43 exige `.claude.bak` ausente/vazio; 45 DURO (fonte ausente ⇒ SKIPPED ⇒ rc 0) e 46 (P2). v12 (rodada 6, parte 1): 42/43/45 aceitas pelo revisor; 47 DURO declara a CLASSE das escritas fora do confinamento (instância: refresh do PLAN-SCHEMA por `cp` sobre inode hard-linked). v13 (rodada 6, parte 2): 45 cobre também o install; 47 nomeia os appends de `.gitignore` e o dispatcher e alarga os `find`; 48 DURO (re-run do install sobrescreve o dispatcher editado). v14 (rodada 6, parte 3): 16 diz o que é verdade (sweep de `.claude/` continua; dry-run 0 só com manifesto parseado); 49-50 DUROS (sweep de `.claude/`; restore-aside previsível); 51 (HMAC opcional). v15 (rodada 6, parte 4): headline e secção do CHANGELOG estreitados; claim de atribuição qualificada pela 23; contagem volátil de commits removida; 52 (piso do ceremony-lint re-pinado, residual por contagem). v16 (rodada 6, parte 5): 20 ganha o falso-AUSENTE pós-compaction (DURO); 47 ganha a entrega de hooks e `.claude/hooks` entra nos `find`; 38 ganha as descrições dos settings; 53 (ts não finito). v17 (rodada 6, parte 6): 21 ganha a posse destrutiva sobre `.salt`/`salt-minted.json` pré-existentes no diretório nativo (DURO: ausentes antes do primeiro prompt); 54 (`bytes_scanned`). v18 (rodada 7, parte 1): 55 DURO (migração ignora a cerimônia — `user` roda com `--no-settings-migrate`); 47 cobre a árvore `.claude` inteira; 4 ganha o rótulo «hook registration(s)». v19 (rodada 7, parte 2): 47 ganha o tempfile previsível do deny-baseline do install (+ condição para installs); 56 (preflight nlink sobre create-only, P2). v20 (rodada 7, parte 3 + morte da parte 4): 16 diz o que o restore faz depois da cura livre do dry-run; 26 diz que o template manual não é gate; 57 DURO (gramática do archive do restore); 58 (deriva NFKC do redator); reticências removidas do texto. v21 (rodada 8, parte 1): 59 DURO (caminho sensível rastreado aborta depois das mutações); 60 DURO (falha do escritor vira PRESERVED, rc 0 — CHANGELOG estreitado). v22 (rodada 8, parte 2): 5 corrigida (só o re-run do install re-renderiza); 14 + 61 DURO (proveniência do CODEOWNERS por sufixo, sem gramática); 62 (omissão semântica na tabela, P2). v23 (rodada 8, parte 3): 50 corrigida (o aside move vem depois da validação e do dry-run, antes da extração); 63 DURO (perfil user recebe hooks bloqueantes pelo merge aditivo — README/FAQ estreitados). v24 (rodada 8, parte 4): 58 honesta (mitigação PARCIAL; deriva na mesma linha passa); CHANGELOG estreitado em três claims (restore members fora de .claude; posse por igualdade nua; Fable só no template base). v25 (rodada 8, parte 5): 20 ganha o primeiro segundo (ABSENT desconhecido) e a leitura de `written` como atividade na janela, não autoria; 38 ganha o cabeçalho do `SessionEnd.py`; 64 DURO (colisão de posse num caminho NOVO da v1.4.0 — FALLBACK sobrescreve e o manifesto registra o hash do framework); 65 DURO (store de sessão do scratchpad segue symlink — classe da 28 no raiz de estado nativo); 66 (SPEC do scratchpad sem o store de sessão, P2); CHANGELOG: a linha do delta de memória diz atividade na janela, não autoria; UPGRADE-PROCEDURE ganha a checagem (10). v26 (rodada 8, parte 6): 67 DURO (`append_entry` lê o predecessor fora do lock — dois escritores concorrentes quebram a cadeia sem adulteração; classe pré-existente na v1.3.0; a cadeia prova integridade só por trechos de um escritor) e 68 DURO (criação da chave HMAC não exclusiva — pré-criar com um único escritor antes da primeira sessão); UPGRADE-PROCEDURE ganha a checagem (11); cabeçalho de `test_two_writer_chain.py` corrigido. v27 (rodada 9, parte 1): 14 ganha o fail-open do upgrade sobre manifesto malformado/duplicado (FALLBACK sobrescreve um hook customizado sob `refuse`; preflight DURO = parser TOTAL do manifesto, o mesmo da 61); 47 ganha o refresh do ponteiro `PROTOCOL.md` da raiz por redirect através de hard link e as duas checagens de link passam a incluir `<alvo>/PROTOCOL.md`; UPGRADE-PROCEDURE: checagem (4) com `PROTOCOL.md` e checagem (12). v28 (rodada 9, parte 2): 61 reescrita — parser TOTAL do manifesto (gramática por linha, relpath seguro, unicidade global; ensaiado com controles) no lugar do `grep` que deixava passar `lixo␠␠sufixo`, e o opt-out do CODEOWNERS dito como o código faz (vazio é re-renderizado sob `--github-owner` quando há registro; ausente é criado; sobrevive só sem a flag); 62 ganha as cópias em código do installer; cabeçalho do `delivery-routes.tsv` (livre) deixa de se anunciar única verdade e «5 por run». v29 (rodada 9, parte 3): 61 deixa de creditar ao parser do `uninstall.sh` a recusa de duplicados; 69 CURADO nesta rc (livre: uninstall recusa manifesto symlink antes do `-f` e toda ocorrência de relpath duplicado antes de backup e remoção, exit 6 — e2e U.9a/U.9b com controle pré-cura); 43 ganha o diretório de backup previsível do `doctor.sh --repair` (P2); o template `benchmarks.yml.template` (livre) diz «uma resposta bem-sucedida, até três tentativas» em vez de «uma chamada» (P2); UPGRADE-PROCEDURE (12) cobre uninstall e doctor. v30 (rodada 9, parte 4): a classe «advisory hooks only» fecha em todos os textos entregues — `npm/README.md` (linhas 98 e 136), `README.md` (tabela do plugin e válvula de escape) e `README.pt-BR.md`; 63 nomeia cada texto estreitado e o único remanescente canônico (`install.sh:11`). v31 (rodada 9, parte 5): 68 reescrita (o diretório nativo já existe e é do harness; nomes reservados da família de auditoria AUSENTES antes da primeira sessão, checagem que vê symlink pendente, chave criada com `O_EXCL|O_NOFOLLOW` — o comando da rodada 8 seguia o symlink e escreveu fora, medido); 70 DURO (assimetria de `plan_id` PreCompact/PostCompact perde a continuidade em silêncio); 71 DURO (`model` dos spawns é a tabela de política, não observação); 72 (barreira do SessionEnd usa o lock errado, P2); UPGRADE-PROCEDURE (11) reescrita. v32 (rodada 9, parte 6; 67 aceita como honesta): 68 ganha as três consequências de um objeto pré-existente em `audit-key` — 32 bytes seus adotados em silêncio; outro tamanho ⇒ todo evento com `hmac=null`; FIFO bloqueia o hook (`_check_perm_0600` não exige arquivo regular) — e a checagem (11) idem. v33 (refutadores da rodada 10, antes do candidato): 69 ganha o alias por segmento vazio (`docs//x`) que a unicidade por string não via — curado no mesmo candidato (`_rel_unsafe` recusa `//` e barra final; e2e U.9c) e declarado no `doctor.sh`; 63 nomeia `INSTALL.md` (estreitado) e afirma o único remanescente por grep, não por enumeração. v34 (arquitetura da cura, rodada 10): 69 ganha o passe de IDENTIDADE por `(st_dev, st_ino)` — a classe de alias fecha por construção (e2e U.9d, hard link, com controle contra a cura sem identidade). v35 (refutadores da rodada 10): 14 cita as linhas certas do `uninstall.sh` (25-31); o parser total testa também o ALVO do registro LINK (14, 61, guia 12); 47 e a checagem (4) em laço — ignoram caminhos que uma instalação `user` não tem e EXCLUEM os links registrados `LINK` de uma instalação `--link` (antes: insatisfazível nesse modo; `find` errava em `user`); 68 e a checagem (11) ganham `state` na lista de nomes reservados (raiz do scratchpad de sessão, seguido através de symlink — reproduzido) e 65 aponta para a mesma checagem; 38 refeito — três cláusulas curadas retiradas. v36 (caudas dos refutadores, 8 P2): 47 tira `.claude.bak/` do texto (regra mais forte na 43); 64 diz como os agentes canônicos são copiados (à parte, `cp` incondicional); 20 com os três limites da janela; 68: `.salt` truncado (não `os.replace`), temporário do marcador, rotação mensal e `memory-shared/` na lista, modo do diretório 0755→0700, e a checagem (11) avisa quando o resolvedor falha em vez de aprovar por silêncio.) Como DATA tem sha256 `dd39a1455924ecbde254e974d7bd9e9897ed10d5b603fd7ae7548ace3ea76bd4` (pinada em `PROVENANCE-rc1.md` da rodada 3).

Cada item descreve o que o código FAZ nesta rc, para que a assinatura não afirme
mais do que aconteceu. Fonte: re-pass do candidato (codex 0.147.0 pinado, modelo
gpt-5.6-sol, 6 partes) + verificação adversarial de cada achado contra o código e
os textos de desenho ratificados (registros em `PLAN-169/repass-rc1-20260908-NOGO/`).
Adopters desta rc: os repositórios do próprio maintainer, subindo da v1.3.0 em modo
cópia. «Cura antes do GA» = entra na rc.2 por cerimônia assinada, com controle positivo.

## A. Condições DURAS (o texto da release foi estreitado para dizer isto)

1. **Rota com transform sem renderer** — **CURADO em `5518888` (wave-rc1cure, assinada pelo Owner em 08/09)**: os quatro sítios da
   classe em `scripts/upgrade.sh` marcam `unrenderable-transform` como falha de
   pré-condição, persistem `upgrade_succeeded: false`, imprimem «Upgrade INCOMPLETE» e
   saem 3 (controle positivo no harness e2e). O texto anterior desta condição e a
   exceção que o CHANGELOG [1.4.0] nomeava descreviam o código PRÉ-cura e foram
   removidos (rodada 3, parte 1).
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

39. **O estado de CUSTO (cost-envelope) muda de slug sem migração — e isso decide despachos.**
    `cost_envelope.py` passa a gravar `cost-envelope-*.json` sob o slug nativo (com traço
    inicial) em vez do slug v1.3.0 sem traço; os totais diário/semanal/mensal/por plano
    voltam a ZERO no upgrade e `check_cost_envelope.py` PERMITE um despacho de swarm que o
    gasto acumulado da v1.3.0 teria bloqueado; a função também reconstrói o caminho
    `$HOME/.claude/projects/...` por conta própria, ignorando `CLAUDE_PROJECT_DIR_NATIVE`.
    Condição DURA: não habilitar `CEO_SWARM` depois do upgrade sem migrar (ou provar
    ausentes) os arquivos de custo do slug antigo; cura antes do GA: usar
    `runtime_state_dir(project)/state` e dual-read dos arquivos antigos na janela de 30
    dias, com teste de contador semeado cujo primeiro despacho pós-upgrade continua
    bloqueado (rodada 3, parte 6).
40. **O registro `credential-rotation.json` da v1.3.0 não é lido depois do upgrade.** O
    adapter vivo (`_lib/adapters/live/claude.py`) só lê o diretório novo do projeto e
    trata a ausência como «não configurado»: uma credencial já VENCIDA perde o aviso de
    rotação, o evento bloqueante e a decisão `CredentialExpired` logo após o upgrade. O
    inventário do PLAN-182 incluía este arquivo, mas a condição 27 e o procedimento de
    upgrade migram só `state/` — o registro é um irmão de topo. Condição DURA: copiar o
    registro legado para o diretório novo de cada projeto ANTES de rodar adapters vivos
    (rota em docs/UPGRADE-PROCEDURE.md); cura antes do GA: fallback nomeado ao registro
    legado quando o novo está ausente, com controle positivo de registro vencido
    (rodada 3, parte 6).
42. **Posse por igualdade HISTÓRICA sem registro anterior** (rodada 4, parte 1):
    `scripts/upgrade.sh` (`_up_tpl_generations` e os ramos de entrega de `docs/` e
    `.github/`) trata um arquivo PRÉ-EXISTENTE do adopter byte-igual a uma geração
    ANTERIOR do template — que o framework nunca entregou e que não tem digest no
    manifesto — como «pristine prior generation»: substitui-o pela geração atual e passa a
    registrá-lo como framework-owned (se igual à geração ATUAL, o ramo `IDENTICAL` ainda
    pode alterar o modo antes do registro). Os bytes substituídos são iguais ao template
    antigo, mas a POSSE muda: upgrades seguintes o reescrevem, `doctor.sh --repair` trata
    edições como drift e `uninstall` o apaga. Condição DURA: antes de rodar `upgrade.sh`,
    qualquer arquivo seu em `docs/` ou `.github/` que coincida byte a byte com um template
    de QUALQUER versão do framework — a ATUAL incluída — e que você NÃO recebeu do framework
    deve ser editado (um byte basta) ou movido; igual à geração atual, o ramo `IDENTICAL`
    normaliza o modo e registra a posse do mesmo jeito (rodada 5, parte 1) —
    `docs/UPGRADE-PROCEDURE.md` diz isto. A cura NÃO é a literal («sem digest anterior,
    igualdade = PRESERVED»): MEDIDO em 08/09 que a v1.3.0 entrega `docs/` e `.github/` ao
    disco e registra ZERO linhas deles no manifesto — a cura literal congelaria essas cinco
    entregas para todo adopter v1.3.0, exatamente o que esta release existe para passar a
    entregar. Cura = posse por EVIDÊNCIA (registro anterior OU entrega comprovada da
    v1.3.0), decisão de produto do Owner, rc.2 (pack `rc1-cure-3` em preparação).
43. **O diretório de backup do upgrade não é confinado ao alvo** (rodada 4, parte 1):
    `scripts/upgrade.sh` cria `.claude.bak/<timestamp>` com `mkdir -p` e grava ali os
    backups (SPEC, docs, CODEOWNERS...) SEM passar por `_wbm_dst_refuses`; se
    `<alvo>/.claude.bak` for um symlink (ou estiver sob um) para fora do alvo, o `mkdir -p`
    e os backups escrevem lá fora — ao contrário do que o `--help` afirma (backups
    internos ao alvo). Classe same-UID/symlink (`docs/threat-model.md`, Tier-2), mas é a
    forma fail-open que o PLAN-185 já fechou para os DESTINOS de entrega e o backup não
    herdou. «Não ser symlink» NÃO basta (rodada 5, parte 1): o timestamp tem precisão de
    segundos e o script usa `mkdir -p`, então um symlink pré-colocado em
    `.claude.bak/<timestamp>/docs` ou um leaf de backup hard-linked ainda dirige o `cp` a um
    inode externo com `.claude.bak` regular. Condição DURA: antes do upgrade,
    `<alvo>/.claude.bak` deve estar AUSENTE ou VAZIO (nenhuma entrada dentro, de nenhum
    tipo), não pode ser symlink nem estar sob um, e nenhum outro processo pode escrever
    nele durante o upgrade — `docs/UPGRADE-PROCEDURE.md` diz isto. Cura antes do GA: criar o
    diretório concreto da execução EXCLUSIVAMENTE (recusar se já existir) e validar cada
    leaf de backup com `_wbm_dst_refuses` antes da primeira mutação (symlink, ancestral
    symlink, hard link), com perna de sentinel externo intacto (pack `rc1-cure-3` se
    assinado; senão rc.2). Idem `doctor.sh --repair` (rodada 9, parte 3, P2; arquivo livre): o
    diretório de backup `.claude.bak/doctor-<timestamp UTC, segundos>` é previsível e criado
    com `mkdir -p`; o predicado de confinamento recusa symlink e hard link, mas ACEITA um leaf
    regular de link único já existente, que o `cp -p` seguinte sobrescreve — um arquivo seu
    nesse caminho exato é destruído durante o repair. A condição de `.claude.bak` AUSENTE ou
    VAZIO vale também antes de `doctor.sh --repair`. Cura antes do GA: reservar o diretório da
    execução exclusivamente (sem `-p`; sufixo único em colisão) e recusar leaf de backup
    pré-existente.
45. **Fonte AUSENTE no checkout corrente vira `SKIPPED`, não falha** (rodada 5, parte 1):
    uma rota válida cuja fonte (`templates/...`) está ausente ou não é arquivo regular no
    checkout que executa `scripts/upgrade.sh`, sem `--pin`, é contada como `SKIPPED`; a
    conservação fecha, `_UP_DELIVERY_PRECONDITION_FAILED` fica 0, o install-state grava
    `upgrade_succeeded: true`, o run imprime «Upgrade complete» e sai 0 — entrega PARCIAL
    indistinguível de sucesso pelo código de saída (a condição 34 cobre a fonte recusada
    por symlink; esta é a variante ausente/não-regular). Condição DURA: rode o upgrade a
    partir de um checkout COMPLETO do framework (clone limpo ou checkout da tag,
    `git status --porcelain` vazio, todas as fontes de `scripts/delivery-routes.tsv`
    presentes como arquivos regulares) e leia o resumo da entrega: qualquer rota `SKIPPED`
    sem `--pin` significa upgrade INCOMPLETO — repita a partir de um checkout completo.
    Cura antes do GA: permitir o skip só com `PIN_REF` definido e a fonte realmente ausente
    na versão pinada; no checkout corrente, ausência/tipo inválido chama a função comum de
    falha, persiste `false` e sai 3, com teste do estado, do banner e do código de saída.
    **`install.sh` tem o MESMO buraco** (rodada 6, parte 2): com a tabela íntegra e uma fonte
    declarada ausente ou não regular, `_wbm_source_confined` deixa o caso chegar ao `-f`, o
    instalador imprime `SKIP`, omite só aquela entrega do manifesto, grava sucesso e anuncia
    «Install complete» com rc 0. Condição DURA, também para instalações NOVAS: instale a
    partir de um checkout completo (as mesmas checagens acima) e leia o resumo — qualquer
    `SKIP` de rota significa instalação INCOMPLETA. Cura antes do GA: validar, antes da
    primeira escrita, que todas as fontes das rotas do install existem, são regulares e
    confinadas, acumulando falha não zero.
47. **CLASSE: escritas do upgrader FORA do predicado de confinamento** (rodada 6, parte 1;
    declarada como classe porque enumerar variantes uma a uma não converge — 43 e esta são
    a mesma forma). O PLAN-185 confinou os DESTINOS de entrega (`_wbm_dst_refuses` + rename
    atômico), mas `scripts/upgrade.sh` ainda escreve por OUTROS caminhos sem esse predicado
    e por `cp` direto sobre o inode existente: o refresh dos schema docs de `.claude/plans/`
    (`_refresh_schema_doc`, ~linhas 3845-3879 — o digest `8ca4f866...` é exatamente o
    `PLAN-SCHEMA.md` da v1.3.0, então todo adopter v1.3.0 copy-mode entra no ramo «pristine
    prior generation» e recebe `cp "$_rsd_src" "$_rsd_dst"`), os backups (43) e os ramos
    `REFRESHED`/`IDENTICAL` sobre destino pré-existente; os APPENDS (`>>`) em `.gitignore` e
    `.claude/.gitignore` pelos helpers de `_framework_manifest_set.sh` (chamados de
    `upgrade.sh` ~4094-4117), que só testam `-L`; e os três `cp` de `install_dispatcher`
    em `.claude/dispatcher/` (`install.sh`, fora do preflight; rodada 6, parte 2); e a
    ENTREGA DE HOOKS do `upgrade.sh` (rodada 6, parte 5): um `.claude/hooks` (diretório ou
    leaf) symlinkado para fora, ou um hook com link count > 1, faz o registro de baseline
    ser descartado como inseguro, mas a entrega seguinte usa `-d`/`-f` (que seguem) e `cp`
    simples — o hook novo de pinning e as atualizações de hooks são escritos ATRAVÉS do
    link; e o TEMPFILE do deny-baseline em `install.sh` (rodada 7, parte 2):
    `apply_deny_baseline` grava o merge em `$SETTINGS_DST.deny-baseline.$$` — irmão de
    `.claude/settings.json` com nome PREVISÍVEL (PID) que o preflight nunca examina (ele
    olha só `settings.json`); um symlink pré-plantado com esse nome faz o redirect do `jq`
    (ou do Python) escrever fora do alvo e o `mv` seguinte substitui o `settings.json` pelo
    link, com «Install complete» — a frase «neither is reachable once the shared verdict
    is consulted» no comentário dessa função é FALSA para este tempfile; e o REFRESH do
    ponteiro `PROTOCOL.md` da RAIZ (rodada 9, parte 1): o observador do ponteiro distingue
    symlink, diretório e arquivo especial (e recusa escrever através deles), mas um ponteiro
    REGULAR com link count > 1 é lido como «regular, owned» e o
    `printf '%s\n' "$_ptr_full" > "$pointer"` do ramo DELIVER/REFRESH (~linha 1919) trunca e
    reescreve o inode compartilhado — as duas checagens de link abaixo NÃO cobriam
    `<alvo>/PROTOCOL.md`, então um adopter podia seguir o preflight assinado à letra e ainda
    passar essa forma. Um destino hard-linked a um arquivo
    FORA do alvo é alterado junto (o inode é o mesmo) e um symlink (leaf ou ancestral) é
    seguido, com o upgrade reportando `REFRESHED` e saindo 0 — o próprio diff reconhece a
    forma insegura ao entregar `docs/` por rename atômico. Classe same-UID
    (`docs/threat-model.md`, Tier-2), fora do modelo de ameaça como ataque; é a forma
    fail-open que importa. Condição DURA: antes do upgrade, sob `<alvo>/.claude/plans/`,
    `<alvo>/docs/`, `<alvo>/.github/` e `<alvo>/SPEC/` (o `.claude.bak/` tem na 43 a regra MAIS
    forte — ausente ou vazio — e por isso não entra no comando; rodada 10) não pode
    haver symlink (leaf ou ancestral) nem arquivo com link count > 1 — medido com
    (rodada 7, parte 1: a lista por subárvore NÃO bastava — `backup_and_replace` e a cópia
    de agentes fazem `cp` através de `.claude/scripts`, `.claude/commands`, `.claude/skills`,
    `.claude/agents` e rosters symlinkados; a checagem cobre agora a árvore `.claude`
    INTEIRA, e o próprio `<alvo>/.claude` tem de ser um diretório real)
    (rodada 10, refutador: em laço, porque numa instalação `--ceremony user` não existem
    `SPEC/`, `docs/`, `.github/` nem `PROTOCOL.md` e um `find` com operando ausente erra e sai
    1; e EXCLUINDO os links que o próprio framework criou numa instalação `--link` — cada
    destino de `install_one` é um symlink por construção, registrado como `LINK` no
    manifesto e detectado e preservado pelo `upgrade.sh` — senão a condição era
    insatisfazível para esse modo)
    `for p in .claude docs .github SPEC .gitignore PROTOCOL.md; do [ -e "<alvo>/$p" ] || [ -L "<alvo>/$p" ] || continue; find "<alvo>/$p" -type l; done | while IFS= read -r l; do r="${l#<alvo>/}"; grep -qF "LINK  $r  " "<alvo>/.claude/.install-manifest.sha256" 2>/dev/null || printf '%s\n' "$l"; done`
    e
    `for p in .claude docs .github SPEC .gitignore PROTOCOL.md; do [ -e "<alvo>/$p" ] || [ -L "<alvo>/$p" ] || continue; find "<alvo>/$p" -type f -links +1; done`
    (`<alvo>/PROTOCOL.md` entrou na rodada 9, parte 1), ambos imprimindo NADA — um link sem
    registro `LINK` é de quem o pôs lá, não do framework —
    `docs/UPGRADE-PROCEDURE.md` diz isto; vale igualmente para `install.sh` (dispatcher,
    `.gitignore`s e o tempfile do deny-baseline: nenhum `.claude/settings.json.deny-baseline.*`
    pré-existente e nenhum outro processo criando entradas em `.claude/` enquanto o install
    roda — o `find -type l` sobre a árvore `.claude` inteira pega um link pré-plantado).
    Cura antes do GA: `mktemp` no diretório do destino registrado em `_ATOMIC_TMP_PENDING` e
    publicação por rename para o deny-baseline; `_wbm_dst_refuses`
    + recusa de `nlink > 1` antes de QUALQUER mutação em todos esses caminhos (o ponteiro
    `PROTOCOL.md` incluído), e tempfile no diretório do destino + `mv` atômico em vez de `cp`
    direto ou de redirect; controle positivo com
    `PLAN-SCHEMA.md` v1.3.0 hard-linked a um sentinel externo (bytes e modo intactos)
    (pack `rc1-cure-3`, se o Owner o assinar; senão rc.2).
48. **`install_dispatcher` copia incondicionalmente** (rodada 6, parte 2): `install.sh`
    faz `mkdir -p .claude/dispatcher` e três `cp` sem consultar proveniência — um re-run
    SOBRESCREVE arquivos do dispatcher editados pelo adopter, ao contrário do que o
    cabeçalho do script afirma («re-running won't clobber edited files»); o censo ratchet
    já classifica esses sítios como desguardados. Condição DURA: antes de re-rodar
    `install.sh`, copie para fora qualquer arquivo editado em `.claude/dispatcher/` (ele será
    substituído pelo template) — e o diretório entra nas checagens do item 47. Cura antes do
    GA: incluir os três relpaths no preflight global, `_dst_preflight` no grupo, e troca do
    `cp` incondicional por atualização baseada em proveniência; o texto do cabeçalho é
    canônico e muda na mesma cerimônia.
49. **`uninstall.sh` apaga diretórios VAZIOS seus sob `.claude/`** (rodada 6, parte 3): o
    sweep por cadeia de pais (pack 2) exclui `.claude/*` de propósito, e o sweep recursivo
    antigo `find "$TARGET/.claude" -depth -type d -empty -delete` continua — depois de um
    upgrade da v1.3.0, uma árvore vazia criada por você (ex.: `.claude/local/drafts/`),
    ausente do manifesto, é removida no uninstall, ao contrário da promessa de posse do
    cabeçalho. Nenhum ARQUIVO é removido por essa via (só diretórios vazios). Condição
    DURA: se diretórios vazios sob `.claude/` importam para você, recrie-os depois do
    uninstall. Cura antes do GA: rastrear as cadeias de pais de `.claude` como as demais
    entregas, remover o sweep recursivo e perna equivalente à U.6e numa subárvore de
    `.claude/` não relacionada.
50. **O `--restore` move o `.claude/` vivo para um caminho PREVISÍVEL sem confinamento**
    (rodada 6, parte 3): DEPOIS de conferir que o archive existe, do HMAC opcional, da
    listagem e do membro `.claude` e da fronteira do dry-run (rodada 8, parte 3 — a cura
    livre da rodada 7 moveu a validação para antes do preview), mas ANTES da extração,
    `uninstall.sh --restore` faz `mv
    .claude .claude.pre-restore-<timestamp UTC, precisão de segundos>`; um symlink
    pré-posicionado com esse nome para um diretório externo leva o SEU `.claude/` vivo
    para fora do alvo — gêmeo, do lado do restore, do defeito do backup da condição 15, e
    instância da classe 47. Condição DURA: antes de `--restore`, `<alvo>/.claude.pre-restore-*`
    deve estar AUSENTE (nenhuma entrada com esse prefixo). Cura antes do GA: criar
    exclusivamente e confinar um diretório de restore-aside e mover `.claude` para DENTRO
    dele, recusando colisão ou symlink; teste com sentinel externo.

## B. Residuais DECLARADOS por desenho ratificado (não mudam na rc.2 sem decisão do Owner)

4. **Merge de settings é aditivo por roster da cerimônia gravada** (Pacote E, ADR-197):
   uma registração de hook ou chave `.env` removida à mão pelo adopter VOLTA no
   upgrade — com log nomeado («REGISTERED: ...») e backup `settings.json.pre-h8-merge`;
   remoção deliberada exige `--no-settings-merge`. Dois textos ficam INEXATOS até a
   próxima cerimônia canônica: o `--help` («registers new lifecycle hooks», o mecanismo
   antigo) e o RESUMO FINAL do upgrade, que afirma que só hooks novos e folhas
   baseline-aware mudaram enquanto chaves `.env` ausentes também foram re-adicionadas
   (rodada 2, parte 1); e (rodada 7, parte 1, P2) o total impresso como «hook
   registration(s)» no dry-run e no run real soma também os `ADD-ENV` — com uma única
   chave `.env` ausente o script anuncia uma registração de hook que não existe.
5. **Arquivo pré-existente byte-igual à SAÍDA RENDERIZADA entra no manifesto como
   framework-owned** (`install.sh` e `upgrade.sh`, paridade entre os dois). Isso não é
   só um efeito de `uninstall`: a linha do manifesto vira PROVENIÊNCIA operacional que
   ações seguintes consomem — (a) um `CODEOWNERS` autoral igual ao render é pulado mas
   registrado, e se o adopter depois o esvaziar de propósito para desligar o roteamento
   de revisão, `_codeowners_provenance` lê a linha como prova de entrega e o RE-RUN
   SEGUINTE DE `install.sh --github-owner` o RE-RENDERIZA, religando o roteamento em
   silêncio (rodada 8, parte 2: só o installer tem essa recuperação — no `upgrade.sh` o
   hash do arquivo vazio não bate com baseline, geração atual nem histórica e ele fica
   `PRESERVED (adopter-modified)`); (b)
   `doctor.sh` passa a classificar edições posteriores como drift do adopter e pode
   fazer backup e SOBRESCREVER o arquivo sob `--repair` confirmado; (c) `uninstall`
   o apaga. O arquivo é igual ao render, não necessariamente aos bytes literais do
   template público. Cura antes do GA: exigir registro de entrega anterior, não
   igualdade nua, antes de `_append_delivered_template` (rodada 2, partes 2 e 3).
   Decisão de posse = wave com o Owner. **Rodada 4 (parte 1): o mesmo princípio vale para
   a igualdade HISTÓRICA** — ver o item 42: `_up_tpl_generations` trata um arquivo
   pré-existente byte-igual a uma geração ANTERIOR do template (nunca entregue, sem digest
   no manifesto) como «pristine prior generation», substitui-o e o registra como do
   framework.
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
8. **Tabela de rotas no CHECKOUT do framework — três frestas fail-open.** (a) Ausente ou
   corrompida: `install.sh` ainda copia `docs/` e `.github/` fixos e reporta sucesso (cura
   antes do GA). (b) Symlink no leaf: o leitor `_wbm_route_table` passou a recusar `-L`
   (**CURADO em `5518888` (wave-rc1cure, assinada pelo Owner em 08/09)**). (c) Laundering
   pelo SNAPSHOT — **CURADO em `144b0ef` (wave-rc1cure2, assinada pelo Owner em 08/09)**:
   `scripts/upgrade.sh` copiava a tabela (`[[ -f ]]` + `cp`, que seguem o link) ANTES de
   validar e o `-L` examinava o tempfile, não o leaf (rodada 3, parte 1); agora a origem é
   testada com `-L` ANTES do snapshot, o ponteiro fica na origem recusada, todo leitor
   responde zero rotas e a precondição AC-9 sai `exit 3` + `upgrade_succeeded: false`
   (perna H.15e: tabela symlinkada ⇒ rc 3, `docs/rotation-log.md` byte-idêntico). Residual
   DECLARADO da mesma classe, NÃO fechado: componentes de caminho symlinkados e o
   confinamento físico da tabela ao checkout que executa. A tabela vive no checkout que
   executa — fora do modelo de ameaça como ataque; era a forma fail-open que importava.
9. **Gramática do handle** — **CURADO em `5518888` (wave-rc1cure, assinada pelo Owner em 08/09)**: `_wbm_github_handle_ok` (produtor e
   consumidor) exige último caractere alfanumérico e recusa hífens consecutivos; o
   harness e2e discrimina `trail-`, `a-`, `a--b`.

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
    linhas 25-31): um registro seguro-na-forma é tratado como prova de posse — e, no
    installer, nem a FORMA é exigida (item 61). Escrita
    same-UID no alvo já é game-over pelo modelo de ameaça (§T-05); sidecar autenticado
    = item de v2. O cabeçalho do script deixa de anunciar um `exit 3` de HMAC que não
    existia. E no UPGRADE (rodada 9, parte 1, P1) a FORMA é exigida do jeito errado: o
    carregador do manifesto (`scripts/upgrade.sh`, ~1150-1215) DESCARTA em silêncio um
    registro cujo digest não seja exatamente 64 hex minúsculos (ou sem o separador de dois
    espaços) e INVALIDA um relpath registrado duas vezes; `_baseline_lookup` então devolve
    «sem baseline» para esse caminho, `_classify_against_baseline` responde `FALLBACK`, e o
    ramo FALLBACK (o mesmo do item 64) ignora `--on-conflict=refuse` e SOBRESCREVE um hook
    que o adopter tinha CUSTOMIZADO (backup em `.claude.bak`; a posse e o registro reescrito
    passam ao framework). É fail-OPEN sobre input de proveniência — o contrário do contrato —
    e um registro de 63 caracteres basta. (Sem manifesto NENHUM, todo arquivo existente cai
    na classificação legada `diff -q` com aviso — comportamento da v1.3.0, anunciado no
    início do upgrade como «fallback diff -q classification».) Condição DURA: antes do
    upgrade, `.claude/.install-manifest.sha256` tem de ser arquivo REGULAR (não symlink) e
    passar no parser TOTAL da condição 61 — gramática integral por linha, relpath seguro,
    unicidade global de relpath; o comando imprime NADA e termina com código 0:
    `f=.claude/.install-manifest.sha256; [ -f "$f" ] && [ ! -L "$f" ] && awk -F'  ' 'NF==0||/^#/{next} $1=="LINK"{ if (NF!=3 || $2=="" || $3=="" || $2 ~ /^\// || index($2,"..") || $2 ~ /[\t\r]/ || $3 ~ /[\t\r]/) {print "BAD line " NR; b++} else if (s[$2]++) {print "DUP " $2; b++}; next } { if (NF!=2 || length($1)!=64 || $1 !~ /^[0-9a-f]+$/ || $2=="" || $2 ~ /^\// || index($2,"..") || $2 ~ /[\t\r]/) {print "BAD line " NR; b++} else if (s[$2]++) {print "DUP " $2; b++} } END{exit (b>0)}' "$f"`
    — `docs/UPGRADE-PROCEDURE.md` diz isto (checagem 12). Cura antes do GA: registrar os
    relpaths REJEITADOS no carregador e classificá-los `CONFLICT` (preservados sob `refuse`),
    ou recusar a fase de mutação quando existir registro malformado não atribuível; controle
    positivo com digest de 63 caracteres sobre um hook customizado.
15. **O backup pré-uninstall usa caminho previsível sem criação exclusiva**
    (`.claude.backup-uninstall-<timestamp>.tar.gz` + `.hmac`): um link pré-plantado
    com esse nome faz a escrita seguir para outro inode (reproduzido: 578 bytes fora do
    alvo, same-UID). Mesma classe do ADR-196 num sítio não convertido; cura antes do
    GA: `_wbm_dst_refuses` + criação exclusiva (`PLAN-185-FOLLOWUP-uninstall-backup-confine`).
16. CURADO nesta rc (livres): a recusa/preservação do `uninstall.sh` sai 5/6 em vez de 0
    (um dry-run sobre manifesto PARSEADO sai 0; falhas de INTEGRIDADE DE ENTRADA — NUL no
    manifesto (6), tar.gz inválido ou HMAC errado no `--restore` (4) — acontecem ANTES do
    preview e são não-zero mesmo em dry-run; o `--help` diz isto desde a rodada 6 — e a
    rodada 7 (parte 3) mostrou que o `--restore` validava a listagem do archive DEPOIS do
    preview: `--dry-run --restore README.md` dizia «would EXTRACT» e saía 0; CURADO nesta rc
    (livre): a listagem e a checagem do membro `.claude` correm antes do preview, perna
    U.8a/U.8b com controle de que um backup real continua a pré-visualizar); o
    template de CI entregue verifica o SHA-256 do actionlint antes
    de extrair (o vivo já fazia; a v1.3.0 rodava `bash <(curl)` sem pin) e o gate de
    sintaxe YAML instala o parser em CI e FALHA se ele faltar, em vez de pular em verde.
    Rodada 2 (parte 3) e rodada 3 (parte 3): o parser do manifesto do `uninstall.sh`
    passou a ser TOTAL em duas etapas — a primeira (leitura EOF-safe, gramática por
    registro, controle/malformado REFUSADOS e contados, manifesto vazio REFUSADO) NÃO
    era total no Bash 3.2 (`read -r` descarta um NUL e o resto do registro ANTES do
    check de controle; diretório/FIFO caíam em `continue` sem contar; symlink pendente
    contava como ausente; symlink-leaf para arquivo externo passava `-f` e era lido
    através; o backup só levava registros com DOIS espaços enquanto a remoção aceitava
    um) — a segunda, no pack `rc1-cure-2`: NUL detectado no ARQUIVO antes do loop
    (manifesto inteiro REFUSADO, ledger mantido), tipo não-regular ou symlink =
    REFUSADO e contado (nunca lido), UMA gramática canônica de dois espaços parseada
    uma vez num ledger que alimenta backup E remoção, e — para as árvores FORA de
    `.claude/` — o sweep de diretórios vazios restrito às cadeias de pais dos arquivos
    removidos (`rmdir` de baixo para cima) em vez de `find -empty -delete`; **sob `.claude/`
    o sweep recursivo antigo CONTINUA** (item 49; rodada 6, parte 3). `--help` imprime o cabeçalho
    inteiro; `benchmarks.yml.template` reporta o status real em vez de `$?` depois de
    `!` e diz (rodada 6) que o teto de custo do runner é POR invocação de benchmark
    (US$ 1,00 estimado, `--allow-expensive` para passar) e que não há teto agregado do
    workflow; `templates/codex/pre-push-review-gate.sh` diz a verdade sobre não ser entregue
    (item 26), usa `--not --remotes` no range de branch nova e `--root` no
    `git diff-tree` (pack 2).
17. **PostCompact reinjeta campos do snapshot em `additionalContext` com sanitização só de
    não-imprimíveis** (`check_postcompact_reinject.py`): um NOME de arquivo `finish-*.sh`
    ou um valor de snapshot adulterado atravessa a fronteira da compaction como texto
    instruction-adjacent (reproduzido byte a byte). O render é pré-existente na v1.3.0; o
    fallback session-scope da v1.4.0 o torna o caminho dominante. Cura antes do GA:
    validação estrutural full-match por campo (cerimônias como contagem/ponteiro fixo)
    — CURADA no pack `rc1-cure`. Segunda rota (rodada 2, parte 5): o `plan_id` que
    `resolve_plan_id()` lê de JSON de auditoria NÃO verificado entrava no pointer
    «Active plan: ...» com checagem só de prefixo (`startswith("PLAN-")`), e a checagem
    estrita de `audit_emit.py` só sanitiza o EVENTO, depois de o valor cru já ter entrado
    no contexto — também curada no pack (`fullmatch` `PLAN-NNN`; pointer dropado e contado).
    Estado: **CURADO em `5518888` (wave-rc1cure, assinada pelo Owner em 08/09)** (gate de FORMA por campo, cerimônias como contagem, `plan_id`
    com `fullmatch` em dois consumidores, 3 testes adversariais).
18. **PreCompact segue symlink em `PLAN-NNN/LEDGER.md`** e copia até 5 headings `## `
    (≤ 160 chars) de um arquivo fora do repo para o BLOB do snapshot (nunca para o
    `additionalContext`); quem cria o symlink já lê o alvo (same-UID). **CURADO em `5518888` (wave-rc1cure, assinada pelo Owner em 08/09)**:
    `lstat` + `O_NOFOLLOW` + `fstat` (mesmo inode) no `LEDGER.md` — isto confina o LEAF,
    NÃO os ancestrais: um `PLAN-NNN/` (ou `.claude/plans/`) symlinkado para fora do repo
    ainda é atravessado pela abertura, e os headings do alvo externo entram no BLOB do
    snapshot (rodada 3, parte 5). Cura antes do GA: abrir por descritor de diretório
    (`O_DIRECTORY|O_NOFOLLOW`) ancestral a ancestral, ou `os.path.realpath` confinado à
    raiz do repo antes de abrir (superfície nova da W2 US7).
19. **Orçamento de 2,5 s do PreCompact não chega ao lock de 5 s do `state_store`** (medido
    5,14 s sob holder vivo > 2,4 s): sob contenção rara o harness mata o hook e o snapshot
    e o evento de auditoria se perdem em silêncio; a compaction nunca bloqueia. Cura curta
    na mesma cerimônia (lock_timeout com folga abaixo do timeout do harness).
20. **O delta de memória do `SessionEnd` pode dar um falso AUSENTE numa sessão LONGA que
    compactou** (rodada 6, parte 5, P1): a janela de leitura é limitada (200 registros de
    auditoria, 256 KiB ou 100 ms de relógio — o terceiro limite, apontado na rodada 10, só
    aumenta a chance do falso AUSENTE); passado isso, o `session_start` ORIGINAL sai da janela e o
    segundo `session_start` (o do restart pós-compaction) é aceito como âncora mais
    antiga — um arquivo de memória alterado ANTES da compaction e não tocado depois sai
    como `outcome="absent"` e o render diz «0 ... entries touched this session». O código
    reconhece o residual em comentário; o teste cobre dois starts só quando ambos ficam na
    janela. É um falso negativo na claim central do instrumento (a spec §8 pré-registra
    «ABSENT numa sessão que trabalhou» como o instrumento FUNCIONANDO — numa sessão longa
    compactada isso NÃO vale). Condição DURA: em sessão que compactou, leia «memory delta
    ABSENT»/«0 entries» como DESCONHECIDO, não como zero. O mesmo vale (rodada 8, parte 5,
    P1) para o PRIMEIRO SEGUNDO da sessão: o `ts` do `session_start` na cadeia tem resolução de
    segundo inteiro e a janela abre no segundo SEGUINTE (`start_ts += 1.0` em `SessionEnd.py`,
    `anchor_source=chain`) para não atribuir a esta sessão uma escrita da sessão anterior
    dentro do mesmo segundo — um arquivo de memória escrito no primeiro segundo desta sessão e
    não tocado depois sai como `absent`; o teste espera a fronteira do segundo em vez de
    exercitar a lacuna, e a linha v2.60 da SPEC escreve `st_mtime >= session_start` sem esse
    deslocamento. Condição DURA: ABSENT é DESCONHECIDO também nesse intervalo. Cura antes do
    GA: âncora com subsegundo, ou `start_unknown`/`error` quando houver atividade no segundo
    ambíguo (nunca `absent`), teste positivo em `start_ts + 0,5 s`, SPEC dizendo a janela real.
    E `written` é ATIVIDADE NA JANELA sobre o diretório de memória do projeto, que é
    COMPARTILHADO — uma sessão concorrente que escreva no mesmo diretório também produz
    `written` nesta sessão (a docstring de `_memory_delta_observed` e a SPEC já o dizem; o
    cabeçalho do módulo e o CHANGELOG diziam «DID it?»/«wrote memory» — CHANGELOG corrigido na
    rodada 8, parte 5; cabeçalho canônico, declarado na 38). Condição DURA: não leia `written`
    como prova de que ESTA sessão gravou memória. Cura antes do GA: sem prova de
    que o evento retido é o start ORIGINAL, devolver `start_unknown`; melhor, persistir uma
    âncora imutável do primeiro start (ou validar a fonte do SessionStart); teste com o
    start original evictado e o restart retido. Além disso, `SessionEnd`
    varre nomes modificados por dois scanners antes de fixar o desfecho; numa
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
    a primeira sessão de cada repositório SOZINHA depois do upgrade (mitigação válida
    para quem instala uma versão anterior). **CURADO em `5518888` (wave-rc1cure, assinada pelo Owner em 08/09)**: first-mint com
    `O_CREAT|O_EXCL|O_NOFOLLOW`, a perdedora relê o salt do vencedor (classificação
    DEPOIS do create exclusivo — a 1.ª versão da cura reintroduzia a corrida pelo
    classificador e foi pega pelo próprio teste), e o marcador `salt-minted.json` é
    escrito por tempfile `O_EXCL|O_NOFOLLOW` + `os.replace`, recusando symlink (classe
    same-UID, fora do modelo de ameaça como ataque — `docs/threat-model.md` Tier-2).
    **A cura do first-mint AINDA tem uma janela** (rodada 3, parte 6): o vencedor cria o
    `.salt` final com `O_EXCL` mas só escreve os 32 bytes depois; um perdedor que receba
    `EEXIST` nesse intervalo lê o arquivo VAZIO, classifica-o como malformado e o reabre
    com `O_TRUNC` — os dois processos ficam com salts diferentes, contra a claim «exatamente
    um processo vence» do docstring; o teste do pack pré-cria um vencedor já escrito e não
    exercita essa janela. Cura antes do GA: publicar um inode temporário COMPLETAMENTE
    escrito por operação atômica sem substituição (`link()`/`O_EXCL` no nome final), ou
    serializar leitura/criação/reparo sob lock; teste que pausa o vencedor entre a criação e
    a escrita. A mitigação operacional (primeira sessão SOZINHA) continua válida.
    **Posse destrutiva sobre arquivos PRÉ-EXISTENTES no diretório nativo do projeto**
    (rodada 6, parte 6, P1): a v1.3.0 nunca foi dona de `.salt` nem de `salt-minted.json`
    em `$HOME/.claude/projects/<slug nativo>/`; depois do upgrade, um `.salt` SEU
    pré-existente com tamanho ≠ 32 bytes é classificado como malformado e reaberto com
    `O_TRUNC` (bytes destruídos, modo alterado) e um `salt-minted.json` regular
    pré-existente é substituído sem condição — sem concorrência, symlink ou atacante.
    Condição DURA: ANTES do primeiro prompt pós-upgrade, esses dois caminhos devem estar
    AUSENTES no diretório nativo do projeto (`python3 .claude/hooks/_lib/runtime_paths.py
    --state-dir` imprime o diretório; `docs/UPGRADE-PROCEDURE.md` diz isto). Cura antes do
    GA: distinguir ausente de pré-existente/não-provado e nunca reparar in loco uma folha
    não provada (preservar + breadcrumb, ou caminho com namespace do framework e evidência
    de migração); criar o marcador sem substituição salvo se o existente for reconhecido
    como do framework.
22. **Locks em diretórios diferentes entre hooks v1.3.0 e v1.4.0** só ocorrem com
    `CEO_AUDIT_LOG_PATH` definido E as duas gerações de hooks correndo durante o upgrade;
    o efeito é appends intercalados no mesmo log = alarme de `verify_chain` (tamper-
    EVIDENTE, não silencioso). Regra: faça o upgrade sem nenhuma sessão aberta no
    repositório (docs/UPGRADE-PROCEDURE.md).
23. **O campo `project` dos eventos carrega o caminho absoluto do repositório** (o CHANGELOG
    diz, desde a rodada 6, que a atribuição correta vale para os emissores que TRANSPORTAM o
    campo e remete a esta condição para os que não o fazem) — campo-base
    contratual (`SPEC/v1/audit-log.schema.md` §501), preenchido assim por TODO emissor nas
    duas versões: não há exposição nova; a frase «slug/path never reaches the wire» no
    docstring de `audit_emit.py` e a redação DENIED do SPEC estavam erradas e foram
    corrigidas — **CURADO em `5518888` (wave-rc1cure, assinada pelo Owner em 08/09)** (texto, não comportamento). EXCEÇÃO medida (rodada 2,
    parte 5): os dois emissores da família de compaction (`check_precompact_continuity.py`,
    `check_postcompact_reinject.py`) NÃO preenchem `session_id` nem `project` —
    `emit_generic()` não os sintetiza — logo, num log de auditoria compartilhado ou com
    override, esses eventos não são atribuíveis a repositório nem a sessão. Cura antes do
    GA: passar o session id da entrada do hook e a raiz do projeto resolvida aos dois
    emissores, com testes de wire exato. Idem o único produtor de `ledger_entry_rejected`
    (`ledger_provenance.py`): não inclui `project` nem `session_id` (o wrapper usa `""`)
    — rejeições não atribuídas num log compartilhado. Idem (rodada 3, parte 4) três
    ações registradas nesta versão cujo SPEC declara `session_id` e `project` mas cujas
    implementações omitem `project` — `ceremony_lint_unlock_used` (que também omite
    `session_id`; `check-ceremony-script.py`), `ledger_checkpoint_recorded` e
    `ledger_checkpoint_skipped` (`check_ledger_checkpoint.py`). A afirmação desta condição
    vale para os emissores que TRANSPORTAM o caminho, não para todos; num
    `CEO_AUDIT_LOG_PATH` compartilhado, esses eventos não são atribuíveis. A cura «passar a
    raiz do repositório como `project`» NÃO funciona como escrita para `ledger_entry_rejected`
    (rodada 3, parte 6): o scrubber dessa ação apaga qualquer valor fora de um identificador
    de 64 caracteres sem barra — a representação precisa ser decidida (caminho absoluto como
    nos emissores-base, ou identificador opaco limitado) e alinhada em SPEC, scrubber,
    produtor e teste de wire exato ANTES da cura; até lá, as linhas ficam sem atribuição.
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
    de se auto-subtrair (`--not --remotes`, como no twin do Grok) e o `git diff-tree`
    ganhou `--root` (sem ele, arquivos canônicos introduzidos por um root commit não
    produziam paths e escapavam à revisão — rodada 3, parte 3; pack `rc1-cure-2`).
    Porte completo (roster + ciclo de vida manifesto/uninstall/backup/restore) = item
    nomeado da rc.2 (rodada 2, parte 3). **Instalado à mão, este template NÃO é um gate de
    segurança** (rodada 7, parte 3): o classificador é grosseiro (`.claude/`, `.github/`,
    `scripts/`, `SPEC/`, `PROTOCOL.md`) e responde «não canônico» para caminhos que o
    oráculo do framework classifica como canônicos — `.codex/rules/ceo.rules`,
    `.grok/config.toml`, `AGENTS.md`, `requirements.toml`,
    `templates/settings/settings.base.json` — um push que toque só esses passa sem
    revisão; a frase «over-triggers only» do cabeçalho era falsa e foi trocada (livre) por
    esta lista. Cura antes do GA: portar o oráculo fino e o fallback superset fail-closed do
    twin do Grok.
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
31. **Destinos DUPLICADOS na tabela de rotas** — **CURADO em `144b0ef` (wave-rc1cure2,
    assinada pelo Owner em 08/09)**: `_wbm_route_table_ok` recusa por NOME um destino
    declarado duas vezes, antes de qualquer leitor consumir a tabela (`upgrade.sh` ⇒ zero
    rotas, `upgrade_succeeded: false`, rc 3 — pernas H.15f e S.10e, com controle de que a
    tabela sem a duplicata continua aceita). Antes (rodada 3, parte 1): `_wbm_route_dests`
    emitia as duas linhas, a conservation law passava (rotas == linhas) e `_wbm_route_src`
    parava na primeira — a primeira rota executava DUAS vezes, a segunda era ignorada e o
    run saía 0, enquanto o parser de paridade (`_parity_classify.py`) já recusava a tabela.
32. CURADO em `5518888` sem condição própria: o `concurrency` do `validate.yml` do
    próprio framework passa a incluir o nome do evento — um push em `main` não cancela
    mais o run agendado, o único que exercita Python 3.10/3.11 (rodada 2, parte 4).
33. **O installer NÃO pré-valida «EVERY destination»** (rodada 3, parte 2): a semente
    `state/mcp_client_secrets` fica FORA do preflight de confinamento e, com
    `TARGET/state` symlinkado para um diretório externo, `mkdir -p` cria o diretório
    fora do alvo e `chmod` atua lá. Sítio já reconhecido como não curado em
    `PLAN-185/wave-s329-C-approved.md`; o CHANGELOG deixa de dizer «EVERY» e, desde a
    rodada 6, o título da secção e o headline deixam de dizer «can no longer write outside
    the target» — dizem o que é verdade: os DESTINOS de template entregues são confinados,
    e as frestas são as condições 33, 47 e 48. Cura antes
    do GA: incluir o destino no preflight e repetir a guarda no sítio.
34. **Recusa de FONTE fail-open no RESULTADO** (rodada 3, parte 2): quando um template
    de origem é um symlink externo, a contenção bloqueia a leitura, mas `install.sh`
    apenas registra `SKIP` e `upgrade.sh` conta `PRESERVED`, deixa
    `_UP_DELIVERY_PRECONDITION_FAILED=0`, imprime «Upgrade complete» e sai 0 — entrega
    incompleta por input recusado, não falha de infraestrutura. Cura antes do GA:
    acumular as recusas de fonte e marcar o run como INCOMPLETO (rc ≠ 0). A variante
    «fonte AUSENTE ou não-regular no checkout corrente ⇒ `SKIPPED` ⇒ rc 0» é o item 45
    (DURO; rodada 5, parte 1).
35. `install.sh --dry-run` promete «sempre rc 0» no `--help`, mas uma recusa de destino
    acumulada termina rc 1 (rodada 3, parte 2, P2). Documentar a exceção no help
    (canônico; próxima cerimônia).
36. `SPEC/v1/audit-log.schema.md` documenta, para `ledger_entry_rejected`, `decision=accept`
    e razões como `ok` que a implementação NUNCA produz (`audit_emit.py` reescreve toda
    decisão ≠ `reject` para `reject` e `ok` para `malformed_input`; o único produtor só
    emite rejeições): um consumidor gerado do SPEC aceita estados que não existem.
    Estreitar o SPEC ao subconjunto produzível (canônico; rodada 3, parte 4, P2).
37. `.github/workflows/ceremony-lint.yml` filtra `paths:` sem `.claude/scripts/local/historical/**`,
    que o contrato de descoberta do `check-ceremony-script.py` inclui — um PR que só toque
    um script histórico não dispara o lint fail-closed (rodada 3, parte 4, P2). Próxima
    cerimônia de workflows.
38. Docstrings PRÉ-cura que sobreviveram (rodada 3, parte 5, P2; lista REFEITA na rodada 10 —
    três cláusulas descreviam código que o pack já tinha curado): a docstring de
    `check_precompact_continuity.py` (linhas 57-63) diz que o snapshot é passado como `str` e
    redigido por `state_store.set`, quando a escrita real (~549) é campo a campo; a docstring
    de `_sanitize_memory_basename` (`SessionEnd.py` ~659-660) descreve basenames entrando em
    `systemMessage`, quando o render é counts-only (~1006, ~1070); e (rodada 8, parte 5) o
    cabeçalho de `SessionEnd.py` (item 5 da lista de responsabilidades, linhas 20-24) diz que o
    rail responde «DID it?» — se ESTA sessão gravou memória — quando a docstring de
    `_memory_delta_observed`, a SPEC v2.60 e a condição 20 dizem atividade na janela, sem
    autoria. Idem (rodada 6, parte 5) duas descrições em `.claude/settings.json` e
    `templates/settings/settings.base.json`: a do PostCompact ainda diz snapshot lido do
    scratchpad do PLANO (hoje há fallback dominante de escopo de sessão) e reinjeção só de
    PONTEIROS (hoje as restrições pinadas vêm antes). Retiradas por estarem CURADAS (rodada 10,
    verificado): «`constraint_count` ainda será allowlisted» — a docstring do PostCompact diz
    hoje o contrário — e as descrições de settings sobre `constraint_count` e sobre nomes de
    memória renderizados, que não existem (`grep` = 0 nos dois arquivos). Texto, não
    comportamento; canônicos — próxima cerimônia.
41. `audit_emit.py` diz que `constraint_count` segue disciplina estrita de inteiro e recusa
    floats, mas `int(...)` converte `1.9` em `1` e `True` em `1` — um chamador genérico
    recebe um valor lavado em vez do sentinela zero. Recusar `bool` e não-`int` antes do
    clamp (padrão `_ledger_int_field`), com controles (rodada 3, parte 6, P2).
44. Comentário e rótulo de `scripts/upgrade.sh` (~linha 2629) dizem que 20 registros
    compartilhados «do arrive» com cerimônia desconhecida, mas o código deriva `hooks: {}`
    e só aplica os valores de `env` iguais entre os perfis (o resumo do run está certo; o
    comentário e o rótulo não). Texto, não comportamento; canônico — próxima cerimônia
    (rodada 4, parte 1, P2).
46. O `--help` de `scripts/upgrade.sh` diz que `--dry-run preview` retorna 0, mas uma
    precondição de rotas (ou um transform inválido) também é avaliada no dry-run e termina
    em 3. Dizer «dry-run limpo» no código 0 e documentar o 3 para preview incompleto —
    texto, canônico, próxima cerimônia (rodada 5, parte 1, P2).
51. **O HMAC do backup pré-uninstall é OPCIONAL na prática** (rodada 6, parte 3): o sidecar
    `.hmac` só é criado quando existe uma chave local ao alvo (`.claude/.audit-key` ou
    `.claude/.install-backup-key`), e nem o install nem o upgrade em copy mode criam
    alguma delas (a chave de runtime vive no diretório por projeto do `$HOME`); um backup
    copy-mode normal sai SEM `.hmac` e o `--restore` o aceita sem `--no-hmac-verify`. O
    `--help` deixou de dizer que o backup «carrega um HMAC» (texto corrigido, livre). Cura
    antes do GA: resolver a chave de runtime real e garantir o sidecar, ou exigir bypass
    explícito para restaurar um backup não assinado (rodada 6, parte 3, P2).
52. **O piso de descoberta do `ceremony-lint` estava DEFASADO** (rodada 6, parte 4): o
    `check-ceremony-script.py` falha quando o conjunto de scripts de cerimônia RASTREADOS
    encolhe abaixo de um piso, mas o piso pinado no primeiro censo (41) ficou parado enquanto
    a descoberta chegou a 124 — apagar ou tornar invisível um script deixava 123 ≥ 41 e o
    gate saía 0 sem inspecioná-lo, embora o `ceremony-lint.yml` (canônico) o chame de
    fail-closed. Cura mínima LANDADA nesta rc (livre): o piso é re-pinado em 124 (o valor
    medido no candidato), de modo que qualquer remoção falha o gate e uma remoção
    intencional exige re-pinar conscientemente. Residual DECLARADO: um piso por CONTAGEM
    ainda aceita a substituição «tira um, põe um»; cura antes do GA: pinar o conjunto exato
    de caminhos rastreados (manifesto gerado, comparado por igualdade) com controle positivo
    de remoção de um membro conhecido.
53. `check_postcompact_reinject.py` lê o snapshot do scratchpad da sessão (gravável pelo
    agente) e um `"ts": 1e309` parseia como infinito: `int(time.time() - inf)` levanta
    `OverflowError`, que `_snapshot_age_s` não captura — o handler externo devolve `{}` e o
    bloco inteiro do PostCompact (restrições, ponteiros, evento de auditoria) é descartado.
    Cura: exigir timestamp finito e capturar `OverflowError`, degradando só o campo de idade;
    testes com `1e309`, `Infinity` e `NaN` (canônico; rodada 6, parte 5, P2).
55. **A migração de settings ignora a CERIMÔNIA e quebra o perfil `user`** (rodada 7,
    parte 1, P1): um adopter instalado com a v1.3.0 `--ceremony user` começa SEM
    `availableModels`, `fallbackModel` e `permissions` (o perfil advisory os exclui por
    desenho — `templates/settings/settings.user.json`); o merge do upgrade escolhe o
    template `user` corretamente, mas a migração baseline-aware (T5.4) que corre logo
    depois trata «ausente» como «migrar para o baseline novo» sem olhar a cerimônia e ADICIONA
    os três — inclusive `permissions.defaultMode=manual` — e o `settings.json` deixa de
    corresponder a uma instalação `user` nova. Condição DURA: adopters `user` (ou de
    cerimônia desconhecida) rodam o upgrade com `--no-settings-migrate` — o merge aditivo
    continua; só a migração de folhas é desligada — e `docs/UPGRADE-PROCEDURE.md` diz isto.
    Cura antes do GA: derivar as folhas migráveis do template da cerimônia (cerimônia
    desconhecida ⇒ só a interseção dos perfis), com teste do fluxo COMPLETO v1.3.0 `user`
    → rc.1 (os testes atuais exercitam merge e migração separadamente).
54. `ledger_provenance.py` aceita um resultado «limpo» do scanner com `bytes_scanned`
    menor do que a entrada (uma cauda hostil nunca examinada passa) e com `bytes_scanned`
    booleano (`bool` é `int`), contra o próprio contrato fail-closed «ele olhou de fato?».
    Dormente: o módulo não tem consumidor fora dos testes nesta rc. Cura: exigir `int`
    puro e `bytes_scanned == len(encoded)`, senão `scanner_unavailable` (rodada 6,
    parte 6, P2).
59. **Um caminho sensível já RASTREADO pelo git aborta o upgrade DEPOIS das mutações**
    (rodada 8, parte 1, P1): os helpers de ignore (`_apply_mcp_secrets_ignore`,
    `_apply_posture_state_ignores`, `_apply_claude_dir_gitignore`) só correm depois de
    hooks, scripts, skills, schemas e settings já terem sido reescritos; se
    `.claude/settings.local.json`, `.claude/state` ou `state/mcp_client_secrets` estiverem
    rastreados (mesmo com `git status --porcelain` vazio), o helper imprime `ERROR: ... is
    already TRACKED` e devolve 1, e o `set -e` encerra o processo ali: árvore PARCIALMENTE
    atualizada, sem entrega de `docs/`/`.github/`, sem manifesto novo, sem
    `_write_upgrade_state` e sem banner — o install-state anterior pode continuar dizendo
    sucesso. Condição DURA: antes do upgrade, `git ls-files -- .claude/settings.local.json
    .claude/state state/mcp_client_secrets` tem de imprimir NADA (se imprimir, `git rm
    --cached` desses caminhos e commit ANTES). Cura antes do GA: preflight só-leitura
    desses caminhos logo depois de resolver o alvo e antes de qualquer escrita (inclusive
    `mkdir -p "$BAK_DIR"`), com e2e v1.3.0→rc.1 que compara a árvore antes/depois da recusa.
60. **Falha do ESCRITOR ou do RENDERER depois de uma rota selecionada vira `PRESERVED`, não
    falha** (rodada 8, parte 1, P1): se `docs/` já existe sem permissão de escrita, o
    `mkdir -p` passa, o `mktemp` de `_up_tpl_write` falha e a rota é contada `PRESERVED`; o
    mesmo quando o write atômico do refresh ou o tempfile/`sed` do CODEOWNERS falha — a
    conservation law fecha, `upgrade_succeeded: true` é persistido, o banner diz «Upgrade
    complete» e o processo sai 0. O CHANGELOG dizia «a failed delivery exits 3» sem esta
    ressalva (corrigido: só as PRECONDIÇÕES de rota/fonte saem 3). Condição DURA: rode o
    upgrade com `docs/`, `.github/` e `.claude/` graváveis pelo usuário que o executa e
    com espaço em disco, e leia o resumo — uma rota `PRESERVED` que você NÃO editou é uma
    entrega que falhou. Cura antes do GA: toda falha depois de uma rota ir para
    `INSTALLED`/`REFRESHED` marca a entrega como incompleta (reason token próprio),
    `upgrade_succeeded: false`, banner `INCOMPLETE` e rc 3; controles positivos para falha
    do tempfile, do `mv` e da renderização do CODEOWNERS.
61. **`_codeowners_provenance` aceita QUALQUER linha do manifesto terminada em
    `␠␠.github/CODEOWNERS` como prova de entrega** (rodada 8, parte 2, P1; `install.sh`,
    canônico): o teste é um `grep` pelo sufixo, sem gramática de digest — `NOT-A-DIGEST
    .github/CODEOWNERS` satisfaz. Cenário: o adopter esvazia o `CODEOWNERS` de propósito
    para desligar o roteamento de revisão, existe um registro malformado com esse sufixo,
    e um re-run de `install.sh --github-owner` sobrescreve o arquivo, anuncia `RECOVERED` e
    sai 0 — contra o fail-closed sobre input de proveniência. Condição DURA (reescrita na
    rodada 9, parte 2 — a checagem por `grep` da rodada 8 deixava passar
    `<64 hex>␠␠lixo␠␠.github/CODEOWNERS`, que satisfaz também o `grep` do código e
    recuperaria um `CODEOWNERS` vazio): antes de QUALQUER re-run de `install.sh
    --github-owner` num alvo já instalado, o manifesto `.claude/.install-manifest.sha256`
    tem de ser arquivo REGULAR (não symlink) e passar no parser TOTAL — gramática integral
    por linha (registro HASH = exatamente 64 hex minúsculos, dois espaços, relpath; registro
    LINK = `LINK`, dois espaços, relpath, dois espaços, alvo), relpath seguro (relativo, sem
    `..`, sem tab ou CR) e unicidade GLOBAL de relpath — o comando imprime NADA e termina com
    código 0:
    `f=.claude/.install-manifest.sha256; [ -f "$f" ] && [ ! -L "$f" ] && awk -F'  ' 'NF==0||/^#/{next} $1=="LINK"{ if (NF!=3 || $2=="" || $3=="" || $2 ~ /^\// || index($2,"..") || $2 ~ /[\t\r]/ || $3 ~ /[\t\r]/) {print "BAD line " NR; b++} else if (s[$2]++) {print "DUP " $2; b++}; next } { if (NF!=2 || length($1)!=64 || $1 !~ /^[0-9a-f]+$/ || $2=="" || $2 ~ /^\// || index($2,"..") || $2 ~ /[\t\r]/) {print "BAD line " NR; b++} else if (s[$2]++) {print "DUP " $2; b++} } END{exit (b>0)}' "$f"`
    (gramática igual ou mais estrita que a do carregador do `upgrade.sh` — o ALVO do registro
    LINK com tab ou CR, que o carregador descarta, entrou na rodada 10; ensaiado em 09/09 com
    controles positivos — 63 hex, `lixo␠␠sufixo`, duplicado, absoluto, `..`, tab no relpath e
    no alvo, maiúsculas são todos apanhados). E o opt-out: um `CODEOWNERS` que você esvaziou de
    propósito NÃO deve ser removido — a AUSÊNCIA leva ao ramo normal, que o CRIA de novo
    (`install.sh` ~2106-2109). Com `--github-owner`, um `CODEOWNERS` VAZIO é re-renderizado
    (`RECOVERED`) sempre que o manifesto tem um registro dele — inclusive um registro LEGÍTIMO
    de uma entrega que o framework fez de verdade — e só fica intacto (com aviso) quando não
    há registro; o opt-out vazio só sobrevive com certeza a um re-run que NÃO passe
    `--github-owner` (o installer entrega então `.github/CODEOWNERS.template` e não toca no
    `CODEOWNERS`). Cura antes do GA: aplicar essa validação DENTRO de `_codeowners_provenance`
    (exatamente um registro HASH canônico para `.github/CODEOWNERS`, manifesto regular, sem
    duplicados) e distinguir «esvaziado pelo adopter» de «truncado pelo defeito» por outra
    evidência que não o tamanho. O parser do `uninstall.sh` validava a GRAMÁTICA por linha;
    a unicidade de relpath e o symlink do próprio manifesto faltavam e foram CURADOS nesta rc
    (item 69) — a rodada 8 dizia aqui que ele «já recusa» duplicados; era falso então.
63. **O perfil `user` recebe, pelo merge ADITIVO do upgrade, hooks que podem BLOQUEAR** —
    e «advisory hooks only» não é verdade (rodada 8, parte 3, P1): o merge registra
    `check_config_change.py` (default ligado), que devolve `{"decision":"block"}` numa
    edição de settings que remove uma proteção (achado `FORBIDDEN_KEYS`), e a lista
    `blocking_inclusions` de `templates/settings/settings.user.json` nomeia mais três que
    podem bloquear sob opt-in (`accel_dispatch.py`, `codex_review_user_code.py`,
    `review_loop.py`). O `--no-settings-migrate` da condição 55 NÃO evita isto (o merge
    aditivo continua). Deixaram de dizer «advisory hooks only» (arquivos livres): o `README.md`
    (a linha da cerimônia na rodada 8; a tabela do plugin e a cauda da válvula de escape na
    rodada 9, parte 4), o `docs/FAQ.md`, o `README.pt-BR.md` (as três ocorrências) e o
    `npm/README.md` — a cópia do npm mantinha as duas promessas, linhas 98 e 136, quando a
    rodada 8 estreitou só o README raiz — e `INSTALL.md` (tabela do plugin, linha 97; apanhado
    pelo refutador da rodada 10). A classe foi procurada por grep em toda a árvore entregue
    (`*.md`, `*.sh`, `*.json`, `*.template`): o ÚNICO texto que ainda diz «advisory hooks only»
    é o cabeçalho canônico de `scripts/install.sh` (linha 11) — inexato até a próxima
    cerimônia. Condição DURA: quem quer o comportamento advisory da v1.3.0
    intacto roda o upgrade também com `--no-settings-merge`; quem aceita o merge conhece as
    rotas de saída: `CEO_CONFIG_CHANGE_GUARD=0` (check_config_change), `CEO_TURBO=0` ou
    `.claude/turbo-off` (accel_dispatch), não setar `CEO_CODEX_USER_REVIEW_BLOCK=1`
    (codex_review_user_code fica detect-only) e não setar `CEO_REVIEW_LOOP=1`
    (review_loop fica desligado). Cura antes do GA: registro não bloqueante no perfil
    `user`, ou o contrato «sem GPG» substituindo «advisory» em todos os textos entregues.
64. **Colisão de posse num caminho NOVO da v1.4.0** (rodada 8, parte 5, P1): a atualização por
    arquivo do `scripts/upgrade.sh` (`_per_file_classified_update`, ~linhas 1424-1471, chamada
    por `backup_and_replace` para `.claude/hooks`, `.claude/scripts`, `.claude/commands`, os
    rosters e os domínios de skills; os cinco agentes canônicos NÃO passam por ela — rodada 10,
    refutador — `upgrade_agents_canonical_only` os copia por `cp` INCONDICIONAL, com backup em
    `.claude.bak/<ts>/agents-<nome>.bak` e preservando SÓ o override de modelo do adopter: qualquer
    outra edição sua num desses cinco arquivos é substituída a cada upgrade, classe da 48) só
    trata «arquivo novo do framework» quando o destino está
    AUSENTE. Se o adopter tem um arquivo PRÓPRIO no caminho que a v1.4.0 passa a entregar
    (instância: `.claude/hooks/check_compact_pinning.py` — o hook não existia na v1.3.0, logo o
    manifesto v1.3.0 não tem linha para ele), `_classify_against_baseline` devolve `FALLBACK`
    (sem linha de baseline), o ramo FALLBACK ignora `--on-conflict=refuse`, faz backup, SOBRESCREVE
    (o aviso só sai com `DIFF_WARN=1`, o padrão) e a reescrita final do manifesto (~5195-5198,
    `FMS_HASH_ROOT=$SOURCE_DIR`) registra o hash do FRAMEWORK: a posse do arquivo do adopter passa
    ao framework (upgrades seguintes o reescrevem; `doctor.sh --repair` trata edições como drift;
    `uninstall` o apaga). As condições 42 (`docs/`/`.github/` byte-iguais), 47 (confinamento) e 48
    (dispatcher) não cobrem esta forma. Condição DURA: antes do upgrade, nenhum arquivo SEU pode
    ocupar um caminho relativo que a v1.4.0 introduz sob `.claude/hooks/`, `.claude/scripts/`,
    `.claude/commands/`, `.claude/agents/` e `.claude/skills/` — a lista é mecânica, no checkout
    do framework: `git diff --name-status --diff-filter=A v1.3.0 v1.4.0-rc.1 -- .claude/hooks .claude/scripts .claude/commands .claude/agents .claude/skills`
    (entre eles `check_compact_pinning.py`, `check_ledger_checkpoint.py`,
    `_lib/pinned_constraints.py`, `_lib/runtime_paths.py` e `_lib/ledger_provenance.py`); mova
    ou renomeie antes — `docs/UPGRADE-PROCEDURE.md` diz isto (checagem 10). Cura antes do GA:
    «fonte nova + destino pré-existente + sem registro no manifesto» classifica como `CONFLICT`
    (preservado sob `refuse`), com controle positivo de um arquivo homônimo do adopter (rc.2).
65. **O store de SESSÃO do scratchpad segue symlinks no raiz de estado nativo** (rodada 8, parte 5,
    P1; a mesma classe da 28, noutro raiz): a v1.4.0 introduz `scratchpad-session/` sob o raiz de
    estado (`_state_root()` em `state_store.py`: `CEO_STATE_ROOT`, senão o diretório nativo do
    projeto + `/state`), escrito pelo PreCompact quando o plano não resolve
    (`check_precompact_continuity.py`, ~596-611, `open_session_scratchpad`), e nada valida o
    caminho: `state_store.py` faz `mkdir(parents=True, exist_ok=True)` e `sqlite3.connect()`
    (~225-231), que aceitam e seguem um diretório ou leaf symlinkado; o GC de sessão
    (`scratchpad_lib.py`, ~592-700) aceita um `is_dir()` verdadeiro através do link, varre o
    diretório EXTERNO com `scandir` e faz `unlink()` dos arquivos expirados cujo nome case
    `session-<uuid>.sqlite`, `-wal` ou `-shm`. Um caminho que a v1.3.0 não usava pode já ser um
    symlink ou um namespace do adopter: a primeira compaction sem plano resolvido escreve através
    dele e o GC pode apagar arquivos externos homônimos. A condição 28 cobre `<repo>/.claude/state`,
    não este raiz. Condição DURA: `<raiz de estado>/scratchpad-session` deve estar AUSENTE antes do
    primeiro prompt ou ser um diretório REAL criado pelo framework, sem arquivos estranhos com esses
    nomes; nenhum symlink (leaf ou ancestral) sob o raiz de estado — o raiz é `<nativo>/state`,
    onde `<nativo>` é o que `python3 .claude/hooks/_lib/runtime_paths.py --state-dir` imprime; a
    checagem da condição 68 apanha um `state` que seja symlink (rodada 10) e, existindo o
    diretório, `find "$d/state" -type l` tem de imprimir NADA (o mesmo `d` da 68). Cura antes do
    GA: validar o caminho completo sob o raiz resolvido, recusar leaf
    symlink ou hard-linked e fazer criação, abertura SQLite, varredura e unlink por descritores de
    diretório verificados (`O_DIRECTORY|O_NOFOLLOW`), como a 28 já pede.
67. **`append_entry` lê o predecessor e calcula o HMAC FORA do lock** (rodada 8, parte 6, P1;
    `.claude/hooks/audit_log.py` ~1258-1270 contra o `FileLock` em ~1278; a própria
    `audit_hmac.read_prev_hmac` declara «MUST be called WITH the audit-log FileLock held»): dois
    `append_entry` concorrentes no mesmo projeto — duas sessões, ou dois spawns PARALELOS da
    mesma sessão (o hook de spawn corre uma vez por chamada do Agent) — podem ler o mesmo
    `audit-log.last-hmac`; o lock só serializa os appends, e a segunda linha fica encadeada ao
    predecessor ANTIGO: `verify_chain()` acusa quebra sem que ninguém tenha adulterado nada. A
    ORDEM é a mesma da v1.3.0 (o `append_entry` da tag calcula antes do lock): classe
    PRÉ-EXISTENTE, não regressão — declarada porque a v1.4.0 move a cadeia para o diretório por
    projeto e afirma «one log, one lock». O teste concorrente
    (`tests/test_audit_log.py::test_concurrent_writes_no_interleaving`) verifica só contagem e
    JSON válido; o cabeçalho de `tests/test_two_writer_chain.py` anunciava dois testes que não
    existem (rotação; escritores concorrentes) — corrigido na rodada 8, parte 6 (arquivo livre).
    Condição DURA: a cadeia por projeto é prova de integridade SÓ para trechos escritos por UM
    escritor de cada vez; uma quebra reportada por `verify_chain()` num trecho com spawns paralelos
    ou sessões concorrentes é triada primeiro como esta corrida — o sinal é a linha reprovada
    VERIFICAR quando o `prev` usado é o HMAC da linha anterior à sua predecessora — e nunca lida
    de imediato como adulteração; quem precisa de evidência forense da cadeia nesta rc despacha
    spawns em série e não abre duas sessões no mesmo repositório. A DETECÇÃO de quebra continua
    valendo (a cadeia acusa); o que NÃO vale é a ausência de falsos positivos sob escritores
    concorrentes. Cura antes do GA (canônico, rc.2): adquirir `paths["lock"]` ANTES da rotação,
    da leitura do predecessor e do cálculo — rotação, leitura, cálculo, append e
    `write_last_hmac()` na mesma seção crítica — com teste multiprocesso de barreira antes da
    leitura exigindo cadeia íntegra pelo `verify_chain()`, não só linhas JSON distintas.
68. **A criação da chave HMAC (`get_or_create_key`) não é exclusiva** (rodada 8, parte 6, P1;
    `.claude/hooks/_lib/audit_hmac.py` ~406-429): o comentário diz «atomic»/«race-safe», mas o
    fluxo é `p.exists()` → tempfile PRÓPRIO por PID → `p.exists()` de novo → `os.replace()`; dois
    processos podem ver o segundo `exists()` falso e AMBOS publicar por `replace` — o primeiro lê
    e guarda em cache a chave A, o disco fica com a chave B: toda linha assinada com A fica
    permanentemente inverificável. A ordem é a mesma da v1.3.0 (não é regressão), mas a v1.4.0
    REABRE a primeira criação para todo adopter que atualiza: no diretório por projeto ainda não
    há `audit-key` do framework, e mais de um processo de hook pode chamar `get_or_create_key()`
    antes de a chave existir. A condição 21 declara a eleição do `.salt`, não a da chave.
    Condição DURA (reescrita na rodada 9, parte 5 — a versão da rodada 8 afirmava que o diretório
    «nasce sem `audit-key`», o que o código não garante, e o seu comando de criação seguia um
    symlink pendente: medido em 09/09, 32 bytes escritos FORA do diretório): o diretório nativo
    do projeto (`python3 .claude/hooks/_lib/runtime_paths.py --state-dir`) já EXISTE — é do
    harness, não do framework — e a v1.4.0 passa a reclamar nele a família de auditoria sem
    verificar proveniência: `audit-log.jsonl`, `audit-log.errors`, `audit-log.lock`,
    `audit-log.last-hmac`, `audit-log.chain-length`, `audit-log.rotation-manifest.json`,
    `audit-key`, `.salt`, `salt-minted.json` (mais `audit-log.jsonl.lock`, item 72, os
    temporários `*.tmp.<pid>` e `.salt-minted.json.<hex>.tmp`, os arquivos de rotação mensal
    `audit-log-<AAAA-MM>[-n].jsonl`, o subdiretório `memory-shared/` (sem consumidor vivo nesta
    rc; `mkdir` + `chmod 0700` ATRAVÉS de um symlink, medido) e — rodada 10, refutador — o
    SUBDIRETÓRIO `state`, raiz do
    scratchpad de sessão, do spool e de cinco hooks registrados, que `state_store.py` cria com
    `mkdir(parents=True)` e abre com `sqlite3.connect` ATRAVÉS de um symlink — reproduzido: um
    `state` apontando para fora recebe o SQLite do scratchpad); um `audit-log.jsonl` SEU ali é
    ANEXADO e recebe `chmod 0600`,
    `audit-log.last-hmac` e os outros sidecars seus são SUBSTITUÍDOS por `os.replace` (o `.salt`
    fora de forma é TRUNCADO no lugar, `O_TRUNC` — sobre um hard link isso destrói o inode
    partilhado; a checagem (5) do guia já o dizia; rodada 10), e um FIFO
    seu passa em `_is_safe_audit_path` (que só olha symlink e dono) e bloqueia o `open`. Para o
    `audit-key` em particular (rodada 9, parte 6): um arquivo SEU de exatamente 32 bytes nesse
    nome é ADOTADO em silêncio como a credencial do framework (`get_or_create_key` só cria
    quando o nome não existe); um arquivo de qualquer OUTRO tamanho faz `get_or_create_key`
    levantar `AuditHmacError` e TODO evento sai com `hmac=null` e
    `hmac_error=AuditHmacError` — a cadeia corre sem assinatura, sem bloquear a sessão; e um
    FIFO seu passa em `_check_perm_0600` (que testa modo e dono, nunca «arquivo regular») e
    bloqueia o hook em `read_bytes()`; e a primeira chave muda o MODO do diretório do harness
    de 0755 para 0700 (`ensure_state_dir(tighten=True)`, medido; rodada 10). Antes da
    primeira sessão depois do upgrade, TODOS esses nomes têm de estar AUSENTES do diretório —
    nem symlink, nem hard link, nem tipo não regular — e o diretório não pode ser symlink; o
    comando imprime NADA (com um `$d` vazio — resolvedor a falhar por cwd errado — ele avisa em
    vez de aprovar por silêncio; rodada 10):
    `d=$(python3 .claude/hooks/_lib/runtime_paths.py --state-dir); [ -n "$d" ] || echo "RESOLVER FAILED (run from the target root)"; [ -L "$d" ] && echo "SYMLINK DIR: $d"; for n in state memory-shared audit-log.jsonl audit-log.errors audit-log.lock audit-log.jsonl.lock audit-log.last-hmac audit-log.chain-length audit-log.rotation-manifest.json audit-key .salt salt-minted.json; do p="$d/$n"; if [ -L "$p" ] || [ -e "$p" ]; then echo "PRESENT: $p"; fi; done; for p in "$d"/audit-log-*.jsonl "$d"/audit-*.tmp.* "$d"/.salt-minted.json.*.tmp; do { [ -L "$p" ] || [ -e "$p" ]; } && echo "PRESENT: $p"; done`
    ; e a chave é criada por UM escritor, com `O_EXCL|O_NOFOLLOW` (recusa qualquer coisa já
    presente, symlink pendente incluído — ensaiado em 09/09 com HOME isolado:
    `get_or_create_key()` devolve os mesmos bytes; o controle com symlink pendente termina em
    `FileExistsError` e nada é escrito fora):
    `d=$(python3 .claude/hooks/_lib/runtime_paths.py --state-dir); python3 -c 'import os,sys; d=sys.argv[1]; os.makedirs(d, 0o700, exist_ok=True); p=os.path.join(d,"audit-key"); fd=os.open(p, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600); os.write(fd, os.urandom(32)); os.close(fd)' "$d"`
    — e não abra duas sessões nem rode a suíte de testes dos hooks no mesmo repositório enquanto
    `audit-key` não existir. `docs/UPGRADE-PROCEDURE.md` diz isto (checagem 11). Cura antes do GA
    (canônico, rc.2): recusar folhas pré-existentes sem proveniência (ou mover a família para um
    subdiretório próprio do framework) e publicar a chave por `link()` exclusivo do tempfile
    `0600` + `fsync` para o nome final (sem `replace`), perdedores relendo a vencedora; teste
    multiprocesso com barreira depois do segundo `exists()` exigindo UMA chave em disco e em cache
    e cadeia verificável.
69. **`uninstall.sh` não checava UNICIDADE de relpath nem recusava manifesto symlink — CURADO
    nesta rc** (rodada 9, parte 3, P1; arquivos livres): o parser do pack 2 validava cada linha
    isoladamente e gravava no ledger TODA ocorrência sintaticamente válida; a varredura de
    remoção processava o ledger linha a linha. Com `<sha-antigo>␠␠docs/x` seguido de
    `<sha-atual>␠␠docs/x`, a primeira linha reportava o arquivo modificado pelo adopter como
    PRESERVADO e a segunda o REMOVIA (`rm -f`, SEM `--force`); o `exit 5` chegava depois da
    remoção. E `[ ! -f "$MANIFEST" ]` seguia symlink: um manifesto symlinkado era lido através
    do link. A condição 61 dizia, até a rodada 9, que este sanitizador «já recusa» duplicados —
    era FALSO; corrigido. Cura nesta rc (livre, mesmo commit do candidato): (a) `[ -L
    "$MANIFEST" ]` ANTES do `-f` ⇒ `REFUSED` nomeado e `exit 6`, também em `--dry-run` (falha
    de integridade do input, não preview); (b) segundo passe sobre o ledger sanitizado: TODA
    ocorrência de um relpath registrado mais de uma vez é RECUSADA (contada em `Refused`,
    nunca arquivada nem removida) ANTES do backup e da varredura — o mesmo tratamento em dois
    passes do `doctor.sh`; a legenda de códigos e o sumário nomeiam a classe; e (c) — achado
    do refutador da rodada 10 sobre a própria cura — a unicidade compara STRINGS, e `_rel_unsafe`
    não recusava SEGMENTO VAZIO: `docs/x` e `docs//x` são duas linhas para UM inode, `uniq -d`
    não as pareia e a varredura preservava na primeira e removia na segunda (reproduzido);
    `_rel_unsafe` passa a recusar `//` e barra final (a cláusula que o predicado compartilhado
    `_wbm_route_relpath_ok` já tinha), recusando o alias no PRIMEIRO passe; e, porque enumerar
    grafias não converge (alias por caixa em sistema de arquivos sem distinção de maiúsculas,
    normalização Unicode do APFS, hard link entre dois caminhos registrados), (d) um passe de
    IDENTIDADE: todo relpath do ledger que exista é `lstat`-ado (leaf nunca seguido) e TODA
    grafia cujo `(st_dev, st_ino)` apareça sob mais de um nome é recusada antes do backup e da
    remoção — a classe fecha por construção, não por lista. O `doctor.sh` tem a brecha de
    string no seu `_relpath_unsafe` (aceita `//` e `./docs/x`) e nenhum passe de identidade —
    declarado, cura na rc.2. Evidência: e2e
    `scripts/tests/test-installer-write-safety-e2e.sh` U.9a (arquivo modificado sobrevive byte
    a byte a um relpath duplicado; recusa nomeada; rc 6; manifesto mantido) e U.9b (manifesto
    symlink: rc 6 antes de qualquer leitura; arquivo do framework intacto; link e manifesto
    externo intactos) e U.9c (alias `docs//x`: arquivo intacto; recusa nomeada como caminho
    inseguro; rc 6) e U.9d (hard link `docs/alias` do mesmo inode, registrado com o sha atual:
    os dois nomes sobrevivem; as duas linhas recusadas por identidade; rc 6 — portátil a
    qualquer sistema de arquivos, ao contrário de uma fixture por caixa), com controle positivo
    contra a árvore PRÉ-cura (`git archive` do candidato anterior: U.9a/U.9b vermelhas; U.9c
    vermelha contra a cura só de unicidade; U.9d vermelha contra a cura sem identidade; resto
    verde). O censo de escrita segura ganhou no
    baseline os sítios dos `mv` entre ledgers próprios (`mktemp`, nunca um caminho do alvo). O
    parser TOTAL da condição 61 continua útil ANTES de `uninstall.sh` para ver o que será
    recusado; o `doctor.sh --repair` segue coberto pela 43.
70. **Assimetria de `plan_id` entre PreCompact e PostCompact perde a continuidade em silêncio**
    (rodada 9, parte 5, P1; canônicos): `check_precompact_continuity.py` aceita qualquer PREFIXO
    `PLAN-` (`startswith`, ~310 e ~510) e, com um `plan_transition` NÃO verificado que traga
    `PLAN-123-slug`, grava o snapshot no store de PLANO com esse id e reporta `written`;
    `check_postcompact_reinject.py` exige a FORMA exata `PLAN-NNN` (`_plan_id_ok`, ~389 — a cura
    da rodada 2 endureceu só o leitor) e, ao rejeitar o id, procura o store de SESSÃO, onde nada
    foi gravado: `snapshot_found=false`, continuidade perdida sem aviso. A condição 17 cobre o
    render, não o escritor. Condição DURA: a continuidade pós-compaction só é garantida para
    planos cujo id nos eventos `plan_transition` é exatamente `PLAN-NNN`; um `snapshot_found=false`
    no PostCompact com `written` no PreCompact da mesma sessão é esta assimetria, não ausência de
    snapshot. Cura antes do GA (canônico, rc.2): validar e coagir o `plan_id` para `unknown` UMA
    vez no PreCompact, antes de `_plan_file_for`, `_write_snapshot`, do blob e do evento (id
    inválido vai ao store de sessão), com teste round-trip `PLAN-123-slug`.
71. **O campo `model` dos eventos `agent_spawn` é POLÍTICA, não observação** (rodada 9, parte 5,
    P1; canônicos): a docstring de `audit_log.py` (~876) mede que 199/199 eventos não trazem
    `tool_response.model`, então o fallback pela tabela ADR-052 (`_ADR_052_ROLE_TO_MODEL`) domina —
    um spawn `devops` corre com `claude-sonnet-4-6` pelo frontmatter de `.claude/agents/devops.md`
    mas é registrado como `claude-haiku-4-5`; um `code-reviewer` corre `claude-fable-5` pelo
    frontmatter e é registrado como `claude-opus-5`. Isso contradiz «Claude model ID used for the
    spawn» e «the audit log proves which model made the decision» (`audit_log.py` ~39-47;
    `.claude/plans/AUDIT-LOG-SCHEMA.md` §14). O teste de 14 casos verifica o frontmatter e a
    tabela separadamente, nunca a paridade. Condição DURA: leia `model` como «modelo previsto pela
    política de roteamento para o `subagent_type`», nunca como prova forense do modelo que
    executou — para atribuição real use o frontmatter do agente ou o relatório de custo do
    harness. Cura antes do GA (canônico): sem observação, ler o frontmatter autoritativo ou
    emitir `model=null` e registrar a política em campo separado; alinhar o schema; teste de
    paridade frontmatter × tabela.
72. A barreira de drenagem do `SessionEnd` (`_flush_audit_log_filelock`, ~322-338) usa
    `audit-log.jsonl.lock` enquanto os escritores usam `audit-log.lock` (`audit_emit._lock_path`
    e `audit_paths()`), e só tenta adquirir se o arquivo ERRADO existir — na prática retorna
    imediatamente; a drenagem prometida não acontece, e os emits pelo caminho assíncrono do spool
    depois dela também não a têm. Cura: usar o `_lock_path()` compartilhado e adquirir o lock
    real sempre, com teste que o mantenha ocupado (rodada 9, parte 5, P2; canônico).
57. **O `--restore` valida NOMES, não TIPOS de membro** (rodada 7, parte 3, P1): a única
    checagem estrutural é «existe um membro cujo nome começa por `.claude`»; depois o
    archive é extraído em bloco (`tar xzf ... .claude`) e os membros `.claude/*` são pulados
    na varredura de segurança. Um tar válido e não assinado com um ARQUIVO REGULAR ou um
    SYMLINK chamado `.claude` é aceito e reportado «Restore complete», substituindo o
    diretório de governança vivo pelo tipo errado ou por um link externo; membros
    symlink/hard link fora de `.claude` também são extraídos sem validação de tipo.
    Condição DURA: restaure SÓ um archive que ESTE `uninstall.sh` produziu a partir
    DESTE alvo, não modificado e com o `.hmac` verificado quando existir chave (item 51);
    nunca um archive de outra origem. Cura antes do GA: inspecionar os metadados dos
    membros antes de qualquer mutação, exigir um diretório `.claude/` real, recusar tipos
    de link fora dele e extrair num diretório de staging confinado recém-criado antes de
    trocar no lugar.
56. O preflight global de destinos do `install.sh` recusa `nlink > 1` também em destinos
    CREATE-ONLY que aquela execução só PRESERVARIA (`EXISTS → SKIP`): um `.mcp.json`
    regular hard-linked a uma configuração central dá rc 1 antes da primeira escrita,
    embora não haja escrita. Fail-closed seguro, mas bloqueia um caminho legítimo. Cura:
    preflight consciente da operação — ancestrais para todos, recusa de hard link no leaf
    só quando a execução vai escrevê-lo/substituí-lo (rodada 7, parte 2, P2).
58. **O redator de saída para o Codex aplica spans NFKC no texto original**
    (`.claude/hooks/_lib/codex_egress_redact.py` via `secret_patterns.scan_and_redact`,
    canônico; encontrado quando a rodada 7 do re-pass morreu na parte 4): o scanner
    normaliza o texto (NFKC) para casar padrões, mas os offsets encontrados são aplicados ao
    texto ORIGINAL — cada caractere que o NFKC expande («...» de um só caractere vira três;
    ligaturas, frações) desloca as redações SEGUINTES em (n-1) caracteres: a redação cai em
    cima de texto inocente e o valor casado fica parcial ou totalmente VISÍVEL (medido: o
    id de 11 dígitos de um run de CI saiu meio-redigido na rodada 6 e a redação atravessou
    uma quebra de linha na rodada 7). Mitigação nesta rc: PARCIAL (rodada 8, parte 4) — só
    o TEXTO das condições deixou de usar o caractere de reticências; o DIFF que viaja no
    mesmo payload carrega os caracteres expansíveis dos arquivos de origem (três U+2026 só
    na parte 4, além de ligaturas), e o controle de contagem de linhas do runner só pega a
    deriva que CRUZA uma quebra de linha — a deriva na mesma linha passa. Os payloads das
    rodadas 6 a 8 saíram com rótulos de redação deslocados (identificador de formato válido
    parcialmente visível; texto inocente redigido): defeito do INSTRUMENTO, presente na
    evidência arquivada, sem efeito no código entregue. Cura antes do GA: mapear os spans de volta ao texto
    original (ou redigir sobre o texto normalizado e emitir ESSE texto), com teste de
    controle positivo «segredo depois de N reticências» (rodada 7, parte 4 — falha do
    instrumento, P1 para quem envia texto com Unicode ao rail).
62. A tabela de rotas é fail-closed para zero linhas, duplicatas e linhas rejeitadas, mas
    não para OMISSÃO semântica: remover a linha de `benchmarks.yml.template` deixa cinco
    linhas válidas, `routes == rows`, o upgrade omite a entrega e sai 0. Mitigado nesta
    rc pela condição 45 (checkout completo da tag); cura: pinar por release o conjunto
    exato de destinos ou o digest esperado da tabela (rodada 8, parte 2, P2). Idem (rodada 9,
    parte 2, P2): o `install.sh` repete em código os destinos e pares fonte/destino que a
    tabela declara (`_dst_global_preflight`, `install_docs_templates` e os writers de
    `.github/`); remover ou alterar uma rota não altera essas cópias e o installer ainda
    tenta a entrega fixa (a fresta (a) da condição 8) — a paridade installer/tabela é
    VERIFICADA em CI (D3), não derivada. O cabeçalho de `scripts/delivery-routes.tsv` (arquivo
    livre) deixou de se anunciar «única verdade» para todos e de prometer «5 arquivos por
    run»: uma cerimônia `user`, uma fonte ausente ou um destino preservado entregam menos.
66. `SPEC/v1/scratchpad.schema.md` (canônico, versão 1.0.0-rc.1) continua normativo SÓ para o
    store por plano (`scratchpad/<plan_id>.sqlite`): o store de sessão
    `scratchpad-session/session-<uuid>.sqlite` — escopo, gramática do id, TTL, GC por store, lock
    permanente — não está na SPEC. Ferramenta de backup, migração ou retenção derivada do contrato
    omite o estado que hoje domina (`written_session_scope`) e um snapshot registrado pode sumir
    nessas operações. Cura: versionar a SPEC com o store de sessão (rodada 8, parte 5, P2; próxima
    cerimônia).

## D. O que este re-pass NÃO cobriu

- `.claude/scripts/**` ficou fora por orçamento e permanece coberto apenas pelas
  rodadas por wave (README-rc1.md §4).
- Limite same-UID (cadeias HMAC separadas por diretório e chave, não por privilégio);
  checksums por tarball do npm não automatizados; fence-shadow variante 5 (signatário
  == Owner) fora do modelo de ameaça — residuais herdados do trem, já no CHANGELOG.
