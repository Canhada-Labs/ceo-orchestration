# Condições do envelope — v1.4.0-rc.1 (pré-release; hold mecânico de 24 h antes do GA)

> Emendado depois da rodada 2 a pedido dos revisores (renumeração dos itens 15/16
> duplicados; condições 4, 5 e 7 ampliadas para o que o código faz; item 16 com as curas
> livres da rodada 2; itens 25 a 30 novos; condições 15, 18 e 21 corrigidas pelas partes 5 e 6). A versão que os revisores da rodada 2
> receberam como DATA tem sha256 `7f0dd2513413039c07a09e58697074e6305a8a0460bdd72b774a2f8f3207b12c` (pinada em
> `PROVENANCE-rc1.md` da rodada 2).

> Emendado (v6) depois da wave-rc1cure (`5518888`) e da rodada 3, parte 1: itens 1, 9,
> 17, 18, 21 e 23 marcados como CURADOS pelo pack assinado; item 8 reescrito (laundering
> pelo snapshot); itens 31 e 32 novos. A versão que os revisores da rodada 3 receberam
> (v7: item 16 reescrito para o pack 2; item 26 com `--root`; itens 33-35 novos. v8: condição 23 com mais três emissores; condição 18 diz que só o LEAF é confinado; itens 36-38. v9: condição 21 declara a janela do first-mint; condição 23 nomeia a representação; itens 39-40 DUROS (custo e credencial) e 41. v10: itens 8 (frestas b/c) e 31 marcados CURADOS em `144b0ef` (wave-rc1cure2); condição 5 remete ao 42; itens 42-43 DUROS (posse por igualdade histórica; diretório de backup não confinado) e 44 — rodada 4, parte 1. v11 (rodada 5, parte 1): 42 vale para igualdade ATUAL ou histórica e diz por que a cura literal não serve; 43 exige `.claude.bak` ausente/vazio; 45 DURO (fonte ausente ⇒ SKIPPED ⇒ rc 0) e 46 (P2). v12 (rodada 6, parte 1): 42/43/45 aceitas pelo revisor; 47 DURO declara a CLASSE das escritas fora do confinamento (instância: refresh do PLAN-SCHEMA por `cp` sobre inode hard-linked). v13 (rodada 6, parte 2): 45 cobre também o install; 47 nomeia os appends de `.gitignore` e o dispatcher e alarga os `find`; 48 DURO (re-run do install sobrescreve o dispatcher editado). v14 (rodada 6, parte 3): 16 diz o que é verdade (sweep de `.claude/` continua; dry-run 0 só com manifesto parseado); 49-50 DUROS (sweep de `.claude/`; restore-aside previsível); 51 (HMAC opcional). v15 (rodada 6, parte 4): headline e secção do CHANGELOG estreitados; claim de atribuição qualificada pela 23; contagem volátil de commits removida; 52 (piso do ceremony-lint re-pinado, residual por contagem). v16 (rodada 6, parte 5): 20 ganha o falso-AUSENTE pós-compaction (DURO); 47 ganha a entrega de hooks e `.claude/hooks` entra nos `find`; 38 ganha as descrições dos settings; 53 (ts não finito). v17 (rodada 6, parte 6): 21 ganha a posse destrutiva sobre `.salt`/`salt-minted.json` pré-existentes no diretório nativo (DURO: ausentes antes do primeiro prompt); 54 (`bytes_scanned`).) Como DATA tem sha256 `dd39a1455924ecbde254e974d7bd9e9897ed10d5b603fd7ae7548ace3ea76bd4` (pinada em `PROVENANCE-rc1.md` da rodada 3).

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
    `$HOME/.claude/projects/…` por conta própria, ignorando `CLAUDE_PROJECT_DIR_NATIVE`.
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
    backups (SPEC, docs, CODEOWNERS…) SEM passar por `_wbm_dst_refuses`; se
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
    assinado; senão rc.2).
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
    (`_refresh_schema_doc`, ~linhas 3845-3879 — o digest `8ca4f866…` é exatamente o
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
    link. Um destino hard-linked a um arquivo
    FORA do alvo é alterado junto (o inode é o mesmo) e um symlink (leaf ou ancestral) é
    seguido, com o upgrade reportando `REFRESHED` e saindo 0 — o próprio diff reconhece a
    forma insegura ao entregar `docs/` por rename atômico. Classe same-UID
    (`docs/threat-model.md`, Tier-2), fora do modelo de ameaça como ataque; é a forma
    fail-open que importa. Condição DURA: antes do upgrade, sob `<alvo>/.claude/plans/`,
    `<alvo>/docs/`, `<alvo>/.github/`, `<alvo>/SPEC/` e `<alvo>/.claude.bak/` não pode
    haver symlink (leaf ou ancestral) nem arquivo com link count > 1 — medido com
    `find <alvo>/.claude/plans <alvo>/.claude/hooks <alvo>/docs <alvo>/.github <alvo>/SPEC
    <alvo>/.claude/dispatcher <alvo>/.gitignore <alvo>/.claude/.gitignore -type l` e o mesmo
    `find … -type f -links +1` (sobre os caminhos que existirem), ambos VAZIOS —
    `docs/UPGRADE-PROCEDURE.md` diz isto; vale igualmente para `install.sh` (dispatcher e
    `.gitignore`s). Cura antes do GA: `_wbm_dst_refuses`
    + recusa de `nlink > 1` antes de QUALQUER mutação em todos esses caminhos, e tempfile no
    diretório do destino + `mv` atômico em vez de `cp` direto; controle positivo com
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
    (rodada 6, parte 3): antes de qualquer checagem, `uninstall.sh --restore` faz `mv
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
    (um dry-run sobre manifesto PARSEADO sai 0; falhas de INTEGRIDADE DE ENTRADA — NUL no
    manifesto (6), tar.gz inválido ou HMAC errado no `--restore` (4) — acontecem ANTES do
    preview e são não-zero mesmo em dry-run; o `--help` diz isto desde a rodada 6); o
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
    «Active plan: …» com checagem só de prefixo (`startswith("PLAN-")`), e a checagem
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
    auditoria ou 256 KiB); passado isso, o `session_start` ORIGINAL sai da janela e o
    segundo `session_start` (o do restart pós-compaction) é aceito como âncora mais
    antiga — um arquivo de memória alterado ANTES da compaction e não tocado depois sai
    como `outcome="absent"` e o render diz «0 … entries touched this session». O código
    reconhece o residual em comentário; o teste cobre dois starts só quando ambos ficam na
    janela. É um falso negativo na claim central do instrumento (a spec §8 pré-registra
    «ABSENT numa sessão que trabalhou» como o instrumento FUNCIONANDO — numa sessão longa
    compactada isso NÃO vale). Condição DURA: em sessão que compactou, leia «memory delta
    ABSENT»/«0 entries» como DESCONHECIDO, não como zero. Cura antes do GA: sem prova de
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
    nomeado da rc.2 (rodada 2, parte 3).
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
38. Docstrings PRÉ-cura que sobreviveram (rodada 3, parte 5, P2): `check_precompact_continuity.py`
    diz que o snapshot é passado como `str` e redigido por `state_store.set` (hoje a
    redação é campo a campo e passa `bytes`); `check_postcompact_reinject.py` diz que
    `constraint_count` «ainda será» allowlisted (já foi); `SessionEnd.py` descreve basenames
    entrando em `systemMessage` (o render é counts-only). Idem (rodada 6, parte 5) as
    descrições em `.claude/settings.json` e `templates/settings/settings.base.json` dos
    hooks de compaction: ainda dizem armazenamento do snapshot só no plano (hoje há
    fallback dominante de escopo de sessão), reinjeção só de ponteiros (hoje as restrições
    pinadas vêm antes), `constraint_count` por allowlistar (já está) e nomes de memória
    renderizados (só contagens). Texto, não comportamento; canônicos — próxima cerimônia.
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
54. `ledger_provenance.py` aceita um resultado «limpo» do scanner com `bytes_scanned`
    menor do que a entrada (uma cauda hostil nunca examinada passa) e com `bytes_scanned`
    booleano (`bool` é `int`), contra o próprio contrato fail-closed «ele olhou de fato?».
    Dormente: o módulo não tem consumidor fora dos testes nesta rc. Cura: exigir `int`
    puro e `bytes_scanned == len(encoded)`, senão `scanner_unavailable` (rodada 6,
    parte 6, P2).

## D. O que este re-pass NÃO cobriu

- `.claude/scripts/**` ficou fora por orçamento e permanece coberto apenas pelas
  rodadas por wave (README-rc1.md §4).
- Limite same-UID (cadeias HMAC separadas por diretório e chave, não por privilégio);
  checksums por tarball do npm não automatizados; fence-shadow variante 5 (signatário
  == Owner) fora do modelo de ameaça — residuais herdados do trem, já no CHANGELOG.
