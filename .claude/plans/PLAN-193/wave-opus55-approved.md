# wave-opus55 — sentinel de aprovação (DRAFT: o SIGN preenche Data / Anchor-SHA / Approved-By e assina)

> Caminho casa `PLAN-*/wave-*-approved.md` (união fechada de padrões em
> `check_canonical_edit.py`). O binding é o `Patch-sha256` (land por PATCH, sem
> `MANIFEST-*`). O bloco `Scope:` lista exatamente os paths que
> `git apply --numstat` lê no patch; o `OWNER-OPUS55-SIGN.sh` recusa assinar
> se os dois conjuntos diferirem (P1-c) e o `OWNER-OPUS55-LAND.sh` recusa
> landar (G4). O patch é a saída do derivador versionado
> `wave-opus55/apply-opus55-edits.py` sobre `Patch-base`: o SIGN re-deriva e
> compara byte a byte antes de assinar (P1-b) e o LAND prova
> `HEAD + derivador == árvore pós-patch` (V3). O `Anchor-SHA` é preenchido
> pelo SIGN no momento da assinatura; o LAND aborta no G1 se não casar.
> Reescrever um byte deste arquivo depois de assinar invalida o `.asc`.

Plans: PLAN-193
Wave: wave-opus55 (PLAN-193 W3 + W4 — cerimônia `adopt-opus-5.5`, ADR-149 Amendment 3. Decisões do Owner por AskUserQuestion: papel do Opus 5.5 **«Padrão + piso VETO»** (S357) — `claude-opus-5-5` entra no `AVAILABLE_MODELS_WORKING_SET` (no FIM) e no `VETO_FLOOR_ALLOWED` e vira o pin `model` de sessão; o `fallbackModel` segue `claude-opus-5`; os arquivos de agente com `veto_floor: true` seguem em `claude-fable-5`. Esforço dos adopters **«xhigh»** (OQ-1), restrito por **«Instalação nova + opt-in (Recomendado)»** (OQ-7, 2026-09-23); esforço de quem migra o pin **«Migrar gravando 'high' (Recomendado)»** (OQ-8, 2026-09-24). Piso do Claude Code **«Exigir CC ≥ 2.1.280 (Recomendado)»** (OQ-9, 2026-09-24). `ultracode` **«Só no override local (Recomendado)»** (OQ-6, 2026-09-23). Forma do pacote **«Exceção declarada»** à regra de ≤ 8 paths (OQ-2) — um pacote atômico derivado por script, porque os espelhos são amarrados por testes de paridade no MESMO commit)
Patch: .claude/plans/PLAN-193/wave-opus55/WOPUS55.patch
Patch-sha256: ed3dd91435608e54b6dd88396f4b16071bab3f81b0dff2c107df4797597cb6df
Patch-base: 19771fa182574ce3e98685708687dcbf90c3795d
Anchor-SHA: 80ca380e51b48f11afa984cf5a811b95b5359e79
Data: 2026-09-28

## O que esta wave entrega

**Doze arquivos canônicos** (oráculo `--is-canonical` = 1) e **sessenta e
quatro livres**, 76 no total, que só são verdadeiros juntos — todos DERIVADOS de um
único material versionado: `apply-opus55-edits.py` mais os dois módulos de
dados `edits_core.py` e `edits_pricing.py` (207 edições com âncora exata e
contagem declarada, contadas no texto progressivamente editado antes da
primeira escrita; os dois módulos são path-disjuntos e o derivador recusa
uma sobreposição). O baseline do ratchet installer-write-safety não é
edição: o derivador o REGENERA com o próprio censo sobre a árvore
pós-edição e recusa qualquer diferença de linhas além da declarada
(`RATCHET_DELTA`). O inventário de nomes de env também não é edição: o
derivador compara, com a varredura do próprio instrumento, os nomes da
árvore pós-edição com os do inventário de HEAD, REGISTRA os nomes que a
wave declara (`ENV_INVENTORY_DELTA`) e recusa qualquer outra diferença.

1. **`.claude/adr/ADR-149-model-id-allowlist.md`** (canônico — a FONTE): o id
   entra no FIM do working set e no bloco do piso de VETO; o
   `FALLBACK_MODEL_CHAIN` não muda; **Amendment 3** registra os fatos da
   documentação oficial, a decisão, as emendas ao texto anterior declaradas
   por forma, os residuais e o que NÃO decide.
2. **`.claude/hooks/_lib/agent_frontmatter.py`** (canônico): o
   `VETO_FLOOR_ALLOWED` ganha o id (igual, como conjunto, ao bloco do ADR —
   provado por teste). Nenhum arquivo de agente muda.
3. **Os três settings** (canônicos; `.claude/settings.json` é KERNEL): o pin
   `model` vira `claude-opus-5-5` nos três; `availableModels` regenerado do
   ADR nos dois que o carregam (`generate-available-models.py --check`:
   `MATCH (8 ids, ADR order preserved)`); `effortLevel: "xhigh"` no topo dos
   três (formato de instalação NOVA; no dogfood é decisão da lane, não opção
   do Owner); NENHUM carrega `ultracode` (teste de
   guarda); os comentários do pin e do `enforceAvailableModels` passam a
   dizer o que o harness 2.1.280 faz (casamento por PREFIXO de segmento), e
   a ressalva do `enforceAvailableModels` no dogfood passa a ser a
   documentada (com QUALQUER settings gerenciado implantado, o Claude Code lê
   a chave só da fonte gerenciada); o
   do dogfood atribui a pertença EXATA do pin ao `SessionDefaultPinTest`, e
   os dois dizem que o Claude Code troca na partida, pelo modelo padrão e
   com aviso, um pin que o `availableModels` não admite; o do template diz
   que o `upgrade.sh` é mais estrito (entrada exata); o
   comentário do `effortLevel` diz a precedência documentada (no arquivo do
   projeto a chave passa por cima do nível salvo com `/effort` nas settings
   de usuário; o `.claude/settings.local.json` passa por cima do projeto; o
   esforço padrão da organização substitui o padrão do modelo quando a
   sessão roda o modelo padrão da organização; um `maxEffortLevel` limita
   qualquer nível), o que o upgrade grava numa instalação existente (OQ-7,
   OQ-8) e, no dogfood, atribui a chave à lane, não a uma opção do Owner. O
   `settings.user.json` é o que `gen-settings-user-template.py --check`
   aceita.
4. **`scripts/upgrade.sh`** (canônico): a tabela T5.4 ganha em
   `superseded` a lista de 7 ids que toda release de v1.4.0-rc.1 até a
   última anterior a esta wave enviou, e `new` com 8; o passo das folhas
   ARRAY percorre a TABELA (toda entrada de topo cujo `new` é uma lista), sem
   código por chave, e as folhas ESCALARES de TOPO passam por UM ramo
   genérico (ausente → SET; valor enviado antes → MIGRATE; qualquer outro →
   PRESERVADO com aviso nomeado) com atributos de DADO: `requires_member_of`
   (a guarda C6, por pertença EXATA ao valor efetivo de QUALQUER folha-array
   da tabela, resolvido antes no mesmo passo, dry-run incluído — mais
   estrita que o prefixo do harness; o aviso diz isso), `opt_in` +
   `cost_note` (a folha só é escrita numa
   instalação existente com `--adopt-setting <chave>`), `on_migrate_of` (o
   valor que uma folha opt-in ausente recebe quando outra folha escalar,
   percorrida ANTES no mesmo passo, MIGRA de um valor nomeado) e `notice`
   (linha impressa quando a folha é escrita). `model` declara
   `superseded: ["claude-opus-5"]` e o `notice` do piso de CLI; `effortLevel`
   é a primeira folha opt-in e declara `high` para um `model` que migra de
   `claude-opus-5` (OQ-8: o padrão do Opus 5; o do Opus 5.5 é medium) — uma
   linha MIGRATE, a REVERT (apagar a chave) e um NOTICE que nomeia o `xhigh`
   do opt-in; um SET do pin (arquivo sem pin) não grava esforço, e a flag
   vence. Um valor presente numa folha opt-in é preservado e nomeado sem
   aviso; um `--adopt-setting` passado com `--no-settings-migrate` é
   nomeado num aviso e ignorado. Toda linha MIGRATE, também em dry-run,
   é seguida de uma linha REVERT; o backup pré-migração é PRÉ-CONDIÇÃO da
   escrita (sem ele a migração é pulada, com nota nomeada, e o arquivo fica
   como estava); toda saída da migração que deixa o arquivo sem migrar dá
   o comando que re-executa só a migração, montado por UMA rotina (item
   16);
   num arquivo no formato dos templates só mudam as linhas das folhas
   migradas e, antes de uma chave que a migração ACRESCENTA (no fim do
   seu objeto), a linha anterior, que ganha a vírgula — provado no
   template que a v1.4.1-rc.1 enviou; a escrita usa `ensure_ascii=False`, e
   volta à forma escapada quando o arquivo tem um valor que o UTF-8 não
   codifica (um surrogate solitário), para que ele ainda migre; um arquivo
   que a migração de uma release anterior escreveu (escapado) é reescrito
   uma vez na forma não-escapada.
5. **`scripts/install.sh`** e **`scripts/upgrade.sh`** (canônicos) — o piso
   do Claude Code (OQ-9): os dois leem `claude --version` antes de uma
   instalação ou upgrade escrever qualquer coisa; o que sai antes da
   checagem, pela forma, é todo modo que não entrega arquivo do framework
   (o `--help` dos dois, o `--print-settings-baselines` do `upgrade.sh`, e
   os modos de ciclo de vida do revisor no `install.sh` — `--arming-check`
   e `--uninstall`, para o harness que nomearem, `codex` ou `grok`) e toda
   recusa de argumento, de alvo ausente ou de pré-condição. Abaixo de
   2.1.280 recusam (exit 6), salvo `--allow-old-claude-code` (aviso
   nomeado); sem `claude` no PATH (CI, headless) ou com versão ilegível,
   aviso nomeado e seguem; o dry-run nomeia a recusa e segue. A sonda roda
   com stdin de `/dev/null`, em segundo plano, consultada contra um limite
   de 10 segundos; no limite ela para o grupo de processos da sonda e a
   versão fica ilegível (o aviso nomeado acima). A versão é lida SÓ da
   primeira linha da saída que nomeia `(Claude Code)` — a versão de outro
   programa impressa antes nunca é lida —, e uma versão com qualquer coisa
   depois dos três números (um pré-lançamento como `2.1.280-beta.1`)
   conta como abaixo do piso. O motivo, pela forma: os settings
   enviados carregam valores que um CLI mais antigo pode não aceitar, e um
   valor
   de settings que um CLI não aceita pode fazê-lo pular o arquivo INTEIRO,
   registros de hook incluídos (CHANGELOG do Claude Code, lido em
   2026-09-24: valores de enum legados inválidos faziam isso até a 2.1.121;
   o `xhigh` existe desde a 2.1.111). A checagem é UM bloco, byte a byte
   igual nos dois scripts; um teste mantém as cópias iguais e amarra o piso
   ao `notice` da folha `model` e à linha do `SUPPORT.md`.
6. **`.claude/hooks/_lib/adapters/live/claude.py`** (canônico): o default de
   thinking é INVERTIDO — a lista FECHADA agora é a dos ids pré-4.6; todo o
   resto é adaptive-only, então um id novo nasce seguro sob
   `CEO_EFFORT_OVERRIDE`. Uma entrada da lista casa o id EXATO, seguido
   opcionalmente de UM segmento de data (`-AAAAMMDD`, ou o `@AAAAMMDD` do
   Vertex) e de um sufixo de versão do Bedrock; um id que acrescenta outro
   segmento qualquer é OUTRO id e fica no default (a única família é a
   geração Claude 3, `claude-3-*`). Um `{type: disabled}` de quem chama só
   é descartado nos ids que o adapter lista como sempre-ligados (Fable 5 e
   5.1, Mythos 5 e 5.1, o Mythos Preview e o Opus 5.5 — os que a página de
   thinking lista como sempre ligados), pela mesma regra; nos demais segue
   como veio.
7. **`.claude/hooks/_lib/effective_config.py`** (canônico): o tamper check
   do canal env dobra UMA tag final `[1m]` antes de comparar um valor de
   modelo com o allowlist; qualquer outro sufixo segue comparado como está.
8. **`.claude/hooks/audit_log.py`** (canônico): a linha `general-purpose` do
   `_ADR_052_ROLE_TO_MODEL` segue o pin, com comentário dizendo que é valor
   de POLÍTICA, não observação.
9. **`.claude/scripts/validate-governance.sh`** (livre, MEMBRO do manifesto
   ADR-192): case-arm e mensagem do lint de `model:` ganham o id; o sha do
   membro é re-derivado em **`.claude/governance/gate-scripts-manifest.txt`**
   (canônico) no MESMO patch.
10. **Espelhos independentes** (livres): `tier_policy_cli/_types.py`,
    `tier_policy_cli/learn.py` (`_tier_rank` com o id estritamente entre Opus 5
    e Fable 5, ranks renumerados, sem empate),
    `scripts/local/smoke-install-parity.sh` (lista, pin esperado,
    `effortLevel` esperado e nenhum `ultracode` na instalação nova),
    `scripts/tests/smoke-install.sh` (o único aviso do shellcheck que ele
    já tinha na base é dispensado na linha, com o motivo, porque o LAND
    passa o shellcheck em todo `.sh` tocado) — os dois, como todo
    harness que nomeia um instalador, com o bloco do item 15 —, o
    inventário de nomes de env `.claude/scripts/env-inventory.json` (o
    derivador registra o único nome novo, a variável de esforço do Claude
    Code que a nota de custo do `effortLevel` cita; o LAND prova
    `env-inventory-check.py --check` verde) e o
    baseline do censo installer-write-safety, REGENERADO pelo derivador com o
    próprio censo (só a linha da chamada da migração muda de impressão
    digital; as do `install.sh` só mudam de número de linha; o derivador
    recusa qualquer outra diferença, e o LAND prova que o baseline é a
    regeneração, byte a byte).
11. **Custo e telemetria** (livres): o `cost-table.yaml` e toda tabela de
    rollup de custo que o `test_model_fleet_presence.py` amarra ao working
    set do ADR ganham a linha a $4/$20 (sem linha `-fast`); as duas tabelas
    de multiplicador de cache-read por modelo que esse teste mantém iguais
    ganham 0,05×; os detectores enxergam o id; `model_normalize` ganha o
    alias e a dobra genérica do `[1m]`; a faixa de reconciliação do
    `build-canonical-models.py` ganha uma linha própria do Opus 5.5 antes
    da genérica. Tabelas de preço por modelo FORA desse oráculo (snapshots
    de proveniência do Owner, fixtures de deriva, instrumentos de pesquisa
    e de torneio, o gate de custo do tier-policy) não mudam; os rollups que
    procuram o modelo pela grafia exata não precificam a grafia com a tag
    `[1m]`.
12. **Docs** (livres): `SUPPORT.md` (Claude Code ≥ 2.1.280 exigido a partir
    da v1.4.2, com a recusa, a flag e o que editar num CLI mais antigo;
    2.0 a 2.1.279 só até a v1.4.1; a prosa do allowlist diz que o
    `enforceAvailableModels` só está nas settings do próprio framework; a
    linha do `[1m]` passa a falar do pin), `docs/provider-pricing.md` (as
    exceções de cache-read da página de preços separadas das que os scripts
    carregam), `docs/cost-of-operation.md`, `docs/CEO-MODEL-ROUTING.md`
    (linha do pin de sessão na tabela de papéis), `docs/ACCELERATORS.md`
    (fast mode do Opus 5.5 a $8/$40, sem linha `-fast`).
13. **Testes** (livres): paridade e as classes novas das curas (ramo escalar
    genérico e `on_migrate_of` provados em tabela PLANTADA numa cópia
    descartável; folha opt-in; esforço gravado pela migração do pin (OQ-8);
    piso do Claude Code com um `claude` FALSO no PATH (OQ-9) — a versão
    lida só da linha `(Claude Code)`, o sufixo depois dos três números
    abaixo do piso, a sonda sem stdin e parada no limite (numa cópia
    descartável com limite de 2 s); todo teste da migração roda com um
    `claude` FALSO no piso primeiro no PATH, nunca o do host; a dica de
    re-execução de TODA saída de falha da migração mantém as flags do
    operador (item 16); REVERT/NOTICE;
    texto fora de ASCII e o surrogate solitário; ida-e-volta byte a byte da
    forma do template, e o template que a v1.4.1-rc.1 enviou pelo caminho
    que ACRESCENTA o `effortLevel` (as linhas migradas e uma vírgula);
    a forma que as tags enviaram — um literal congelado
    sobre as tags que existiam na S357 e um passeio por TODA tag `v1.*`
    alcançável do HEAD, que num checkout sem tags pula com o motivo; default
    adaptive, id listado seguido de outro segmento, grafias datada, Vertex e
    Bedrock e o `disabled` de quem chama no adapter; dobra do `[1m]` no
    tamper check; pin ∈ piso nos dois espelhos; preço da frota em toda
    tabela que o oráculo de presença amarra ao working set).
14. **`.claude/scripts/tier_policy_cli/cli.py`** (livre; a rodada 1 do
    rail, P2): o `owner-sign` grava no sigchain a ação que o
    `learn._direction` calcula, sobre a MESMA escada do
    `learn._tier_rank`. Antes ele lia a ordem do `VALID_MODEL_IDS`, um
    allowlist na ordem do ADR que não é ordem de tier (`claude-fable-5`
    é a primeira entrada): na base, 20 dos 42 pares ordenados de ids
    distintos saíam com o rótulo contrário ao do `learn._direction`
    (entre eles `claude-fable-5` → `claude-opus-5` como `promote`), e
    com o id novo seriam 24 dos 56 (`claude-fable-5-1` →
    `claude-opus-5-5` como `promote`). Um id sem rank na escada, ou o
    mesmo modelo nos dois lados (que antes saía `demote`), é recusado
    (exit 2) antes de assinar. O `tests/test_cli.py` testa o caminho
    de assinatura: a ação gravada é a do `learn._direction` nos 56
    pares, os pares Fable ↔ Opus em literal, as duas recusas sem
    sigchain escrito, e todo id do `VALID_MODEL_IDS` com rank, sem
    empate.
15. **Nenhum teste nem harness lê o `claude` do host ao rodar um
    instalador** (a rodada 2 do rail, P2). Todo teste ou harness shell
    que roda o `install.sh` ou o `upgrade.sh` herdava o PATH do host, e
    um `claude` do host abaixo do piso o fazia sair 6 antes de exercitar
    qualquer coisa (reproduzido com um `claude` FALSO 2.1.279 primeiro
    no PATH). A cura é da classe, nos dois pontos por onde passa toda
    execução dessas, sem tocar o piso de produção:
    **`.claude/hooks/_lib/test_isolation.py`** (canônico; o Eixo 4 da
    camada de isolamento da suíte pytest) põe, na ativação da sessão, um
    `claude` FALSO primeiro no PATH, dentro da árvore da sessão
    (removido com ela; o PATH volta com o snapshot da restauração): ele
    responde só `--version`, com o piso da linha única
    `CC_FLOOR_VERSION` do `scripts/install.sh`, e sai 127 em qualquer
    outra chamada; a sessão também descarta uma função `claude`
    exportada que herde. Um teste que monta um PATH próprio decide que
    `claude` ele traz. E **cada harness shell sob um diretório `tests`
    ou sob `scripts/local/` que nomeia `install.sh` ou `upgrade.sh`**
    (livres; os dois smokes do item 10 incluídos, cujo `claude` FALSO
    no PATH da r13 deu lugar a este bloco) traz o bloco
    `harness-claude-stub`, byte a byte igual, logo depois da primeira
    linha `set -` de topo: ele lê o piso do `scripts/install.sh` do
    próprio checkout e exporta uma FUNÇÃO `claude` com a mesma
    resposta; o bash roda uma função antes de qualquer entrada do PATH,
    então ela vale sob qualquer PATH que o harness dê a um filho bash
    que herde o ambiente;
    sem uma linha de piso única, o bloco recusa (exit 1). O
    `TestNoHarnessReadsTheHostCli` guarda os dois pontos: sob pytest, o
    `claude` da suíte é o FALSO, primeiro no PATH, e um `upgrade.sh` com
    o ambiente da suíte lê o piso; o conjunto de harnesses é re-derivado
    do disco e cada um traz o bloco igual ao de referência no lugar
    certo; e o bloco sombreia um `claude` 2.1.279 primeiro no PATH (o
    mesmo harness sem o bloco sai 6, sem escrever), vale sob outro PATH
    e recusa um checkout sem uma linha de piso.
16. **Toda saída de falha da migração T5.4 dá o «rode de novo» com as
    flags do operador** (a rodada 3 do rail, P2; decisão do Owner OQ-10).
    A saída de falha do helper da migração (JSON ilegível ou escrita
    atômica que falha) imprimia a re-execução SEM as flags que o
    operador passou; seguida depois de reparar o JSON, ela gravava `high`
    onde `--adopt-setting effortLevel` pedia `xhigh`, e um valor presente
    nunca é sobrescrito depois. A cura é da classe, no
    **`scripts/upgrade.sh`** (canônico): UMA rotina, `_t54_rerun_cmd`,
    monta o comando, e toda saída da migração que deixa o
    `settings.json` sem migrar imprime o que ela monta — o backup
    impossível, o `python3` ausente (que antes não dava comando nenhum)
    e a falha do helper (saída 3 ou qualquer outra saída não-zero). O
    comando leva cada flag do operador que decide o que a migração lê ou
    escreve, ou se ela roda: os `--adopt-setting`, o
    `--allow-old-claude-code`, o `--pin` e o `--dry-run`, com o alvo e o
    valor do `--pin` citados para o shell (um caminho ou um nome de ref
    pode ter um metacaractere); na saída do helper,
    o backup pré-migração só é nomeado quando existe (um dry-run não o
    escreve). O `TestEveryFailureExitKeepsTheOperatorFlags` força cada
    saída (JSON ilegível, ou uma FALHA plantada numa cópia descartável
    do `upgrade.sh`, nunca uma costura de produto), relê o comando
    impresso como o shell o leria e exige exatamente as flags do
    operador e o mesmo alvo (também um alvo com espaço, `$` e aspas, e um
    `--pin` com `;`); e confere que nenhuma saída monta o próprio comando.
    O item 6 da A3.2 do ADR-149 passa a dizer essa regra, pela forma.

## Kernel

`.claude/settings.json` ∈ `_KERNEL_PATHS`. O LAND arma
`CEO_KERNEL_OVERRIDE` ele mesmo, no menor escopo (export antes do apply,
unset após o commit, backstop no trap), com o par reason-SLUG + `I-ACCEPT`
validado VIVO contra o contrato do hook pelo harness — mecanismo idêntico ao
do land da wave-fable51 (`ab56e76`).

## Regra de parada do rail

Pré-registrada no plano em 2026-09-23, antes da 1.ª rodada (emendada
pela decisão do Owner OQ-10, abaixo): no máximo 3
rodadas; um P1 achado SÓ em material vira ANEXO (veredito
`APPROVE-WITH-ANNEX` na família de materiais, com `rail-annex.md`
rastreado); no máximo 2 rodadas por classe de achado; NO-GO só por P0 ou
condição declarada falsa. Acrescentado na r11 (não pré-registrado): o teto
é por família de registro e conta só registros `rail-round-*` /
`rail-materials-round-*` RASTREADOS; o SIGN recusa uma família além do teto
e o anexo fora da família de materiais (a OQ-10, abaixo, abre UMA exceção:
a rodada final da família do patch). Antes do primeiro registro, seis
rodadas codex rodaram sobre derivações ANTERIORES dos bytes canônicos —
cinco em 2026-09-23 (DESIGN seções 11.2, 11.3, 11.5 e 11.6) e uma lente em
2026-09-24 (seção 11.8) —, todas no Codex 0.156.1 instalado, fora do pin
vigente; os defeitos reais que acharam (P0 e P1) foram curados nos módulos
do derivador, e nenhuma deixou registro rastreado. Por estarem fora do
substrato pinado, NÃO contam no teto: a primeira rodada registrada é a 1
de 3. Uma sétima rodada, a verificação de 2026-09-24 sobre os bytes
canônicos da r12 (codex 0.155.0 via npx), deu NO-GO com três P1 e um P2,
curados na r13 (DESIGN seção 11.9); também não deixou registro
rastreado. A rodada 1 registrada (`wave-opus55/rail-round-1.md`,
codex-cli 0.156.1 sobre o patch `587df9f4…`) deu `REJECT` com um P2
— o item 14 acima —, curado na r14 nos módulos do derivador (DESIGN
seção 11.10). A rodada 2 registrada (`wave-opus55/rail-round-2.md`,
codex-cli 0.156.1 sobre o patch `378273c9…`) deu `REJECT` com um P2
— o item 15 acima —, curado na r15 nos módulos do derivador (DESIGN
seção 11.11). A rodada 3 registrada (`wave-opus55/rail-round-3.md`,
codex-cli 0.156.1 sobre o patch `e0f2aa33…`) deu `REJECT` com um P2 — o
item 16 acima —, curado na r16 nos módulos do derivador (DESIGN seção
11.12). As três rodadas deram `REJECT`, cada uma com UM P2 de classe
diferente e nenhum P0/P1; com o teto de 3 atingido, a decisão voltou ao
Owner: **OQ-10** (2026-09-24, verbatim «Corrigir + rodada 4 final c/
anexo (Recomendado)») — cura do P2 da rodada 3 pela classe e UMA rodada
4, a última. Limpa ⇒ `Rail-Verdict: APPROVE`. Só achados P2 (rotulados
P2 pelo codex e confirmados pelo verificador; um P1 do codex nunca é
re-rotulado P2) ⇒ `Rail-Verdict: APPROVE-WITH-ANNEX`, com
`wave-opus55/rail-round-4-annex.md` rastreado e não-vazio, os achados
verbatim, no HEAD que o `Anchor-SHA` assinado fixa. Qualquer P0/P1 ⇒
`REJECT`, e a decisão volta ao Owner. Não há rodada 5. O SIGN aplica a
emenda pela forma: teto de 4 registros por família; nenhum registro
numerado além da rodada 4 (um `rail-round-5.md` é recusado pelo nome);
na família do patch, o veredito de anexo só na rodada 4 e só com o
anexo dela rastreado e não-vazio; nas rodadas 1–3, só `APPROVE`
(igualdade exata); `REJECT` recusa sempre. O LAND reaplica o teto e a
recusa pelo nome, e não conta o anexo como registro.

## Decisão pedida ao Owner ANTES do SIGN (não posta nas OQs)

- **`effortLevel: "xhigh"` no dogfood commitado.** A OQ-6 tirou o
  `ultracode` do `.claude/settings.json` commitado; a pergunta dela nomeava
  também o `xhigh` em todo clone, worktree e night-run como parte do
  risco. A chave `effortLevel` commitada (formato de instalação nova;
  decisão da lane autora, não opção do Owner) traz de volta essa metade.
  Assinar este texto a ratifica; tirá-la é a reversão descrita no DESIGN
  seção 1.

## Residuais declarados (por forma; texto integral no ADR-149 A3.3/A3.4)

- O pin do arquivo de agente só vale no despacho nativo quando a chamada
  não passa `model`: um `model` por invocação passa por cima do arquivo e
  nenhum gate o observa. E o gate de spawn só confere o `model:` do arquivo
  de um papel de VETO quando o slug do papel aparece na descrição ou no
  prompt do spawn — ele não lê o `subagent_type` (anterior a esta wave,
  que não o muda). Trabalho de VETO despachado em modo mitigado ou
  por agente de Workflow, sem `model`, roda no modelo em que a sessão está
  naquele momento — o pin por padrão, ou o que um `/model`, `--model`,
  `ANTHROPIC_MODEL` ou um fallback de conteúdo que persiste na sessão
  escolheu, possivelmente fora do piso; o
  `CLAUDE_CODE_SUBAGENT_MODEL=inherit` dos settings equivale a não definir
  a variável. Qual modelo serviu um spawn mitigado NÃO foi medido.
- O esforço de subagente não é pinado: sem `effort` no arquivo de agente, o
  subagente herda o nível da sessão (documentado, não medido); um VETO
  servido por `claude-opus-5-5` roda nesse nível — o medium padrão onde
  nenhum nível está definido. FOLLOW-UP.
- Pin e fallback agora são modelos diferentes: uma troca por disponibilidade
  muda o modelo que serve no turno em que dispara (a mensagem seguinte
  volta ao pin), escreve no cache do `claude-opus-5`, ao preço de escrita
  dele, a parte do contexto que ele não tem viva (o contexto inteiro quando
  não tem nenhuma) e, ao voltar, re-escreve o que o cache do pin perdeu no
  intervalo, roda sem os blocos de thinking do Opus
  5.5 (o Opus 5 não os lê), e nenhum hook a registra; um erro de limite de
  taxa não dispara a troca; na API o Opus 5.5 tem limite de taxa próprio,
  separado do Opus 5 (página de rate limits, lida em 2026-09-23), e como a
  quota de assinatura do Claude Code conta os dois modelos não está
  declarado nem medido. Já o fallback por CONTEÚDO de um pedido que o Opus
  5.5 marca vai ao Opus 5 ou ao Opus 4.8 (membros do piso) e a sessão
  continua lá.
- O adapter só descarta o `{type: disabled}` de quem chama nos ids que
  lista como sempre-ligados; um id sempre-ligado que ele não lista (um id
  novo, ou um listado seguido de outro segmento) responde HTTP 400 a esse
  pedido (erro visível, nunca thinking ligado em silêncio). O caminho de
  batch NATIVO (opt-in, `CEO_NATIVE_BATCH_LIFECYCLE=1`) repassa o
  `thinking` de quem chama como veio; o tratamento desta wave cobre a
  chamada única e o fallback sequencial do batch, que passa por ela. Um
  `tool_choice` forçado (`any` / `tool`), HTTP 400 no `claude-opus-5-5`
  (ADR-149 A3.1), é repassado como veio pelo caminho de saída estruturada;
  nenhum chamador fora dos testes o passa hoje (conferido em 2026-09-24).
- Nos adopters o allowlist do tamper check (ADR-149) não é entregue, então a
  checagem de remap de modelo roda degradada.
- O `effortLevel: "high"` que a migração do pin grava é uma chave de
  projeto: vale para todo modelo da sessão e passa por cima do padrão do
  modelo, do esforço padrão da organização e do nível que um desenvolvedor
  salva com `/effort` nas settings de usuário (um nível pessoal vai no
  `.claude/settings.local.json`). Um `effortLevel` de topo nas settings de
  USUÁRIO, que valia para o Opus 5, não vale para o Opus 5.5; ali o `high`
  do projeto passa a decidir. A escolha explícita
  (`CLAUDE_CODE_EFFORT_LEVEL`, `--effort`, `/effort` na sessão), o
  `ultracode` e um teto `maxEffortLevel` seguem valendo por cima. Uma
  instalação sem pin no arquivo (o pin é SET, não migrado) não recebe
  `effortLevel`: onde nenhuma outra fonte define nível, roda o Opus 5.5 no
  padrão, medium.
- A checagem do piso lê o `claude` do PATH na hora da instalação ou do
  upgrade; o CLI que depois abre o projeto pode ser outro. Sem `claude` no
  PATH ela só avisa, e `--allow-old-claude-code` segue abaixo do piso:
  então o pin e o `effortLevel` enviados ficam para o operador editar
  (`SUPPORT.md`). O que um CLI abaixo de 2.1.280 faz com o pin não foi
  medido; os modos que não entregam arquivo do framework (os `--help`, o
  `--print-settings-baselines` e os modos `--arming-check` / `--uninstall`
  do revisor, `codex` ou `grok`) saem antes da checagem. A parada da
  sonda alcança só o grupo de processos dela: um processo que o CLI tire
  desse grupo e que segure a saída aberta ainda segura a sonda.
- Um teste ou harness que roda o `install.sh` ou o `upgrade.sh` não lê o
  `claude` do host (item 15), com limites pela forma: um teste que
  monta um PATH próprio, sem o da suíte, decide que `claude` ele traz;
  sob `python -m unittest` direto a camada de isolamento não roda (o CI
  é só pytest); um processo que um harness inicie com o ambiente zerado
  (`env -i`) perde a função exportada; e um harness shell fora de um
  diretório `tests` e de `scripts/local/` não entra no censo do guard.
  Os runners de CI não têm `claude`.
- Instalação de cerimônia `user` que segue a rota `--no-settings-migrate`
  ajusta pin e esforço à mão; um downgrade não desfaz o pin (desfaz: o
  backup ou o revert do commit; a linha REVERT sobrepõe o valor escalar
  pelo `settings.local.json`, sem mudar o arquivo do projeto).
- `upgrade.sh --pin <release anterior>`, rodado de um checkout mais novo do
  framework, aplica a tabela T5.4 do script EM EXECUÇÃO, não a da release
  pinada: o rollback «revert e depois `--pin`» do
  `docs/UPGRADE-PROCEDURE.md` migra de novo para a frente as settings
  revertidas, a menos que essa execução passe `--no-settings-migrate`
  (anterior a esta wave).
- Quando quem chama não passa thinking, o `/effort off`
  (`CEO_EFFORT_OVERRIDE=off`) faz o adapter omitir o parâmetro, como antes
  desta wave; num id em que o thinking é ligado por padrão, omitir deixa o
  thinking LIGADO — o `off` não o desliga ali.
- Uma entrada que um `owner-sign` anterior a esta wave gravou num
  sigchain segue com o rótulo que ele calculou pela ordem da tupla;
  esta wave não reescreve sigchain (o template enviado só traz a
  entrada `baseline` de gênese).
- O piso só cresce; nenhuma regra de aposentadoria.
- Um detector CONSULTIVO de telemetria classifica o modelo de um spawn
  de papel VETO por prefixo de família, então um id de família do piso
  que o piso não lista não gera achado ali; quem DECIDE (o gate de spawn)
  compara ids exatos.
- Uma folha escalar ANINHADA (`permissions.defaultMode`) segue com código
  próprio, sem `superseded`: o ramo genérico cobre só folhas de topo.
- O gate T3.4 do `upgrade.sh` (registros DirectoryAdded / Notification nas
  settings do adopter) segue DESLIGADO: esta wave eleva o piso, não o liga.
- O `SPEC/v1/install-cli.md` não lista `--allow-old-claude-code`,
  `--adopt-setting` nem o exit 6; a tabela de saídas dele já estava atrás
  dos scripts (para no 3, e a própria tabela de flags nomeia os exits 4 e
  5); o SPEC não muda aqui.
- A bateria de CI inteira (`Validate`, `Smoke Install`, ownership e2e) só
  roda depois do push; o LAND roda os gates de corpus e o parity smoke.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Plans: PLAN-193
Scope:
  - .claude/adr/ADR-149-model-id-allowlist.md
  - .claude/data/model-currency-expected-reds.txt
  - .claude/governance/gate-scripts-manifest.txt
  - .claude/hooks/_lib/adapters/live/claude.py
  - .claude/hooks/_lib/agent_frontmatter.py
  - .claude/hooks/_lib/effective_config.py
  - .claude/hooks/_lib/test_isolation.py
  - .claude/hooks/audit_log.py
  - .claude/hooks/tests/test_adr149_validator_parity.py
  - .claude/hooks/tests/test_claude_adapter_thinking.py
  - .claude/hooks/tests/test_effective_config.py
  - .claude/hooks/tests/test_model_routing.py
  - .claude/hooks/tests/test_template_dogfood_parity.py
  - .claude/scripts/audit-telemetry.py
  - .claude/scripts/budget-summary.py
  - .claude/scripts/build-canonical-models.py
  - .claude/scripts/ceo-cost-transcripts.py
  - .claude/scripts/ceo-cost.py
  - .claude/scripts/cost-table.yaml
  - .claude/scripts/data/installer-write-safety-baseline.txt
  - .claude/scripts/detectors/overpowered.py
  - .claude/scripts/detectors/wasteful_thinking.py
  - .claude/scripts/env-inventory.json
  - .claude/scripts/optimizer/model_normalize.py
  - .claude/scripts/optimizer/tests/test_optimizer_model_normalize.py
  - .claude/scripts/success-receipt.py
  - .claude/scripts/tests/test_a4_pricing_doctrine.py
  - .claude/scripts/tests/test_build_canonical_models.py
  - .claude/scripts/tests/test_gen_settings_user_template.py
  - .claude/scripts/tests/test_generate_available_models.py
  - .claude/scripts/tests/test_model_fleet_presence.py
  - .claude/scripts/tests/test_upgrade_settings_migration.py
  - .claude/scripts/tier_policy_cli/_types.py
  - .claude/scripts/tier_policy_cli/cli.py
  - .claude/scripts/tier_policy_cli/learn.py
  - .claude/scripts/tier_policy_cli/tests/test_cli.py
  - .claude/scripts/tier_policy_cli/tests/test_learn_mutation.py
  - .claude/scripts/tier_policy_cli/tests/test_types.py
  - .claude/scripts/validate-governance.sh
  - .claude/scripts/value-dashboard.py
  - .claude/settings.json
  - SUPPORT.md
  - docs/ACCELERATORS.md
  - docs/CEO-MODEL-ROUTING.md
  - docs/cost-of-operation.md
  - docs/provider-pricing.md
  - scripts/install.sh
  - scripts/local/smoke-install-parity.sh
  - scripts/tests/smoke-install.sh
  - scripts/tests/test-doctor-delivery-route.sh
  - scripts/tests/test-doctor.sh
  - scripts/tests/test-install-deny-baseline.sh
  - scripts/tests/test-install-harness-codex.sh
  - scripts/tests/test-install-harness-grok.sh
  - scripts/tests/test-install-sandbox-merge.sh
  - scripts/tests/test-install-upgrade-parity-e2e.sh
  - scripts/tests/test-installer-write-safety-e2e.sh
  - scripts/tests/test-manifest-delivery-route.sh
  - scripts/tests/test-night-mode-ignore-effect.sh
  - scripts/tests/test-ownership-table.sh
  - scripts/tests/test-parity-stale-planted.sh
  - scripts/tests/test-protocol-pointer-inv4.sh
  - scripts/tests/test-protocol-pointer-render.sh
  - scripts/tests/test-schema-generation-pins-unit.sh
  - scripts/tests/test-two-adopter-isolation-e2e.sh
  - scripts/tests/test-upgrade-dryrun-identity.sh
  - scripts/tests/test-upgrade-exclusions.sh
  - scripts/tests/test-upgrade-historical-adopter.sh
  - scripts/tests/test-upgrade-lifecycle-hooks-derived.sh
  - scripts/tests/test-upgrade-spec-ownership.sh
  - scripts/tests/test-w3-vcures.sh
  - scripts/tests/test_install_baseline_manifest.sh
  - scripts/tests/test_install_state_replay.sh
  - scripts/upgrade.sh
  - templates/settings/settings.base.json
  - templates/settings/settings.user.json
<!-- END SIGNED SCOPE -->
