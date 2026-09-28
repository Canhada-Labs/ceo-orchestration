# PROPOSED-PATCH — wave-opus55 (S357, cerimônia `adopt-opus-5.5`, ADR-149 Amendment 3)

Patch: `WOPUS55.patch` — a saída de `apply-opus55-edits.py --require-pricing`
(207 edições em 73 paths, dos módulos path-disjuntos `edits_core.py` — 147
edições em 53 paths — e `edits_pricing.py` — 60 em 20 —, mais o baseline do
ratchet installer-write-safety REGENERADO pelo censo, o manifesto ADR-192 com
o sha do membro re-derivado e o inventário de nomes de env com o nome novo
REGISTRADO — 76 paths) sobre `19771fa182574ce3e98685708687dcbf90c3795d`,
extraída por `git diff` com config pinada e `--full-index`. O mesmo cálculo é
o `--derive-patch` do `OWNER-OPUS55-SIGN.sh`, e o SIGN o refaz a partir do
HEAD e exige igualdade byte a byte antes de assinar (P1-b).
Patch-sha256: ed3dd91435608e54b6dd88396f4b16071bab3f81b0dff2c107df4797597cb6df

Fix round r12 (2026-09-24): aplica as decisões do Owner OQ-8 («Migrar
gravando 'high' (Recomendado)») e OQ-9 («Exigir CC ≥ 2.1.280
(Recomendado)») e cura os achados da rodada 3 das lentes (DESIGN seção
11.8).

Fix round r13 (2026-09-24): cura o que a verificação vX achou na r12 —
uma frase assinada FALSA (ADR-149 A3.2 item 6: «toda linha fora das
folhas migradas fica igual» não vale quando a migração ACRESCENTA uma
chave; a linha anterior ganha a vírgula), o leitor do piso do Claude Code
(lia o primeiro x.y.z de toda a saída; um pré-lançamento passava), a
sonda sem limite de tempo e com o stdin herdado, os testes e os smokes que
liam o `claude` do host e a dica de re-execução que perdia as flags do
operador (DESIGN seção 11.9). Os materiais das rodadas anteriores estão
SUPERADOS por este registro.

Fix round r14 (2026-09-24): cura o P2 da rodada 1 registrada do rail codex
(`rail-round-1.md`, `REJECT` sobre o patch `587df9f4…`): o `owner-sign` do
`tier_policy_cli` rotulava a ação que assina pela ORDEM do
`VALID_MODEL_IDS` (um allowlist na ordem do ADR, não uma ordem de tier) e
assinava `claude-fable-5-1` → `claude-opus-5-5` como `promote`, contra o
`demote` do `learn._direction`; a classe já existia na base
(`claude-fable-5` → `claude-opus-5` saía `promote`). A cura é da classe:
uma autoridade só (o `learn._direction`), recusa de id sem rank e do mesmo
modelo nos dois lados, e o caminho de assinatura testado — `cli.py` e
`tests/test_cli.py` entram no patch (51 paths; os canônicos seguem 11) e
o item 8 da A3.2 do ADR diz o que o `owner-sign` assina (DESIGN seção
11.10).

Fix round r15 (2026-09-24): cura o P2 da rodada 2 registrada do rail codex
(`rail-round-2.md`, `REJECT` sobre o patch `378273c9…`): com o piso do
Claude Code, todo teste ou harness shell que roda o `install.sh` ou o
`upgrade.sh` e herda o PATH do host lia o `claude` do operador; abaixo
do piso, saía 6 antes de exercitar a instalação (o codex reproduziu em
dois testes pytest fora do patch; medido aqui, em execução: 18 testes
pytest em 12 arquivos, e 24 harnesses shell sem stub). A cura é da
classe, nos dois pontos por onde passa toda execução dessas: o Eixo 4 da
camada de isolamento da suíte (`_lib/test_isolation.py`, canônico) e o
bloco `harness-claude-stub` em cada harness shell que nomeia um
instalador, os dois guardados pelo `TestNoHarnessReadsTheHostCli`; o
piso de produção não muda. 76 paths; os canônicos vão a 12 (DESIGN
seção 11.11).

Fix round r16 (2026-09-24/25): cura o P2 da rodada 3 registrada do rail
codex (`rail-round-3.md`, `REJECT` sobre o patch `e0f2aa33…`) pela classe,
conforme a decisão do Owner OQ-10 (2026-09-24, verbatim «Corrigir + rodada 4 final c/ anexo (Recomendado)»):
a saída de falha do helper da migração T5.4 (JSON ilegível, escrita
atômica que falha) imprimia a re-execução SEM as flags do operador — só a
saída do backup as levava —, e segui-la depois de reparar o JSON gravava
`high` onde `--adopt-setting effortLevel` pedia `xhigh`. UMA rotina
(`_t54_rerun_cmd`) monta o comando com os `--adopt-setting`, o
`--allow-old-claude-code`, o `--pin` e o `--dry-run` (o alvo e o valor do
`--pin` citados para o shell), e toda saída da migração que deixa o `settings.json` sem migrar o imprime:
o backup impossível, o `python3` ausente (que antes não dava comando) e a
falha do helper (saída 3 ou qualquer outra não-zero); o backup só é
nomeado quando existe. Guardado pelo
`TestEveryFailureExitKeepsTheOperatorFlags`. Os mesmos 76 paths e 12
canônicos; 207 edições (DESIGN seção 11.12). A OQ-10 também emenda a
regra de parada: UMA rodada 4, a última (seção «Regra de parada do rail»).

## Por path (76)

| path | oráculo | o que muda |
|---|---|---|
| `.claude/adr/ADR-149-model-id-allowlist.md` | CANÔNICO | id no FIM do `AVAILABLE_MODELS_WORKING_SET` e no `VETO_FLOOR_ALLOWED`; **Amendment 3** (A3.1 fatos — incl. o CHANGELOG do Claude Code sobre valores de settings que um CLI não aceita e a exceção do Mythos Preview —, A3.2 decisão em 11 itens — incl. o item 8 (a escada do `learn._tier_rank` e o `owner-sign` que assina a ação do `learn._direction`, não a ordem do `VALID_MODEL_IDS` — r14), `on_migrate_of` (OQ-8), a regra das linhas que a escrita da migração mantém (item 6: só muda, fora das folhas migradas, a linha antes de uma chave ACRESCENTADA, que ganha a vírgula — r13), a regra de casamento do adapter e o piso do Claude Code (OQ-9; item 11: a versão lida só da linha `(Claude Code)`, sufixo depois dos três números abaixo do piso, a sonda sem stdin e parada no limite de 10 s, e o que sai antes da checagem descrito pela forma, `codex` e `grok` — r13) —, A3.3 emendas por forma — incl. o limite inferior do working set só sem `availableModels` gerenciado, a razão (ii) do A1.1 que deixa de valer para o pin e o Mythos 5.1 a 0.025× na página de preços —, A3.4 residuais — incl. o `effortLevel` que a migração grava ser chave de projeto, a checagem do piso que lê o `claude` do PATH, o rollback `--pin` rodado de um checkout mais novo e o `/effort off` onde o thinking é padrão —, A3.5 não-decisões — incl. o gate T3.4 que segue desligado e o `SPEC/v1/install-cli.md` que não lista a flag nova; r16: o item 6 da A3.2 diz que TODA saída da migração que deixa o arquivo sem migrar dá o comando de re-execução montado por UMA rotina, com os `--adopt-setting`, o `--allow-old-claude-code`, o `--pin` e o `--dry-run`, e os valores do operador citados para o shell) |
| `.claude/hooks/_lib/agent_frontmatter.py` | CANÔNICO | `VETO_FLOOR_ALLOWED` += id |
| `.claude/hooks/_lib/adapters/live/claude.py` | CANÔNICO | default INVERTIDO: lista FECHADA dos ids pré-4.6 (`_LEGACY_BUDGET_FAMILIES` = a geração Claude 3; `_LEGACY_BUDGET_MODELS`; as bases 4.0 datadas, casadas SÓ com a data); uma entrada casa o id EXATO seguido opcionalmente de UM segmento `-AAAAMMDD` (o `@AAAAMMDD` do Vertex lido como ele) e de um sufixo de versão do Bedrock — qualquer outro segmento é OUTRO id (A-R3CX-01); todo id fora da lista é adaptive-only; um `{type: disabled}` de quem chama só é descartado nos ids sempre-ligados listados (`_ALWAYS_ON_THINKING_MODELS`: Fable 5 e 5.1, Mythos 5 e 5.1, Mythos Preview, Opus 5.5), pela mesma regra — nos demais segue como veio; o cabeçalho diz que o formato legado é 400 no Claude 4.7+ com a exceção do Mythos Preview e que o Opus 5 aceita `disabled` só com esforço high ou abaixo; o docstring do resolvedor de `/effort` diz que o `off` omite o thinking e que, num id em que ele é padrão, isso o deixa ligado |
| `.claude/hooks/_lib/effective_config.py` | CANÔNICO | `_fold_one_m_tag`: UMA tag final `[1m]` dobrada antes do teste de pertinência do tamper check do canal env; qualquer outro sufixo comparado como está |
| `.claude/hooks/audit_log.py` | CANÔNICO | `_ADR_052_ROLE_TO_MODEL["general-purpose"]` = id, comentário «POLICY value, not an observation» |
| `.claude/settings.json` | CANÔNICO (KERNEL) | pin → id; `availableModels` 7→8 (gerado do ADR); `effortLevel: "xhigh"` (decisão da lane autora, não opção do Owner; o sentinel pede a ratificação: o dogfood tem a forma de uma instalação NOVA de mantenedor) com comentário PRÓPRIO do dogfood (atribui a chave à lane; precedência documentada; esforço padrão da organização e `maxEffortLevel`; o que o upgrade grava — OQ-7, OQ-8; `xhigh` só desde a 2.1.111); SEM `ultracode`; comentários do pin e do `enforceAvailableModels` verdadeiros sobre o casamento por prefixo, e a ressalva do `enforceAvailableModels` é a documentada; o comentário do pin nomeia o teste que existe (`SessionDefaultPinTest`) e diz que o Claude Code troca na partida, pelo modelo padrão e com aviso, um pin que a lista não admite |
| `templates/settings/settings.base.json` | CANÔNICO | pin → id; `availableModels` 7→8; `effortLevel: "xhigh"` com comentário (instalação nova; OQ-7 e OQ-8 no upgrade; organização e `maxEffortLevel`); nota de adopter com $4/$20 e o fallback; o comentário do pin diz o que o harness admite, que um pin que a lista não admite é trocado na partida pelo modelo padrão (com aviso) e que o `upgrade.sh` é mais estrito (entrada exata) |
| `templates/settings/settings.user.json` | CANÔNICO | bytes que `gen-settings-user-template.py --check` aceita: pin → id, `effortLevel` herdado da base |
| `.claude/governance/gate-scripts-manifest.txt` | CANÔNICO | sha do membro `validate-governance.sh` re-derivado (ADR-192) |
| `scripts/install.sh` | CANÔNICO | o piso do Claude Code (OQ-9): o bloco `claude-code-floor` (byte a byte igual ao do `upgrade.sh`) lê `claude --version` antes de a instalação escrever qualquer coisa; abaixo de 2.1.280 recusa (exit 6), salvo `--allow-old-claude-code` (aviso nomeado); sem `claude` no PATH ou versão ilegível, aviso nomeado e segue; o dry-run nomeia a recusa e segue; flag documentada no `--help`; r13: a versão vem SÓ da primeira linha que nomeia `(Claude Code)` e uma versão com qualquer coisa depois dos três números conta como abaixo do piso; a sonda roda com stdin de `/dev/null`, em segundo plano (`disown -a` + `set -m`: um grupo de processos próprio, `kill %1` o para inteiro), consultada contra `CC_FLOOR_PROBE_SECONDS=10` — no limite, aviso «version unreadable» e segue, sem linha nova no censo installer-write-safety |
| `scripts/upgrade.sh` | CANÔNICO | T5.4: `availableModels.superseded` = [6 ids, 7 ids], `new` = 8; o passo das folhas ARRAY percorre a TABELA; UM ramo genérico para as folhas escalares de TOPO, com atributos de dado (`superseded`, `requires_member_of`, `opt_in` + `cost_note`, `on_migrate_of` + `on_migrate_note` — OQ-8 —, `notice`); `model` = `{old: null, superseded: ["claude-opus-5"], new: id, requires_member_of: "availableModels", notice: <piso do CLI>}`; `effortLevel` = `{old: null, new: "xhigh", opt_in: true, cost_note, on_migrate_of: {model: {claude-opus-5: high}}, on_migrate_note}` — quando o pin migra de `claude-opus-5` e o arquivo não tem `effortLevel`, grava `high` com MIGRATE, REVERT e NOTICE (um SET do pin não grava; a flag vence; valor presente nunca é sobrescrito; uma regra que nomeia folha percorrida DEPOIS é aviso nomeado); flag `--adopt-setting <chave>` (charset checado no bash, rc 2 antes de escrever; sob `--no-settings-migrate` é nomeada num aviso e ignorada); o bloco `claude-code-floor` (OQ-9) logo depois da validação do alvo, com `--allow-old-claude-code` e o exit 6 no `--help`; linha REVERT depois de TODO MIGRATE, também em dry-run; backup pré-migração como PRÉ-CONDIÇÃO da escrita (r13: a nota da falha dá o comando de re-execução com os `--adopt-setting` e o `--allow-old-claude-code` que o operador passou; r16: UMA rotina, `_t54_rerun_cmd`, monta esse comando — com o `--pin` e o `--dry-run` também, e o alvo e o valor do `--pin` citados para o shell — para TODA saída que deixa o arquivo sem migrar: backup impossível, `python3` ausente e falha do helper, cujo backup só é nomeado quando existe); o mesmo bloco `claude-code-floor` da r13 (leitor e sonda); `ensure_ascii=False` na escrita, com volta à forma escapada quando um valor não codifica em UTF-8; valor presente numa folha opt-in preservado e nomeado sem aviso (`OK (present - PRESERVED; opt-in leaf)`); comentários com as tags descritas pela forma e as citações de `effective_config.py` e do ADR-149 por SÍMBOLO, não por linha; o comentário do gate T3.4 diz que o piso subiu e o gate segue desligado |
| `.claude/hooks/_lib/test_isolation.py` | CANÔNICO (r15, path novo) | **Eixo 4** da camada de isolamento da suíte pytest: na ativação da sessão, um `claude` FALSO que responde só `--version`, com o piso da linha única `CC_FLOOR_VERSION` do `scripts/install.sh` (e 127 em qualquer outra chamada), vai primeiro no PATH, dentro da árvore da sessão (removido com ela; sem linha de piso única, nenhum stub); o PATH e a função `claude` exportada entram no snapshot da restauração, e uma função herdada é descartada (ela passaria por cima de todo `claude` FALSO que um teste põe no PATH); o docstring ganha o Eixo 4 |
| `.claude/scripts/validate-governance.sh` | livre (membro ADR-192) | case-arm, comentário e mensagem do lint de `model:` |
| `.claude/scripts/data/installer-write-safety-baseline.txt` | livre | NÃO é edição: o derivador o REGENERA com o próprio censo sobre a árvore pós-edição (os números de linha informativos dos scripts tocados acompanham — as linhas do `install.sh` só mudam de número); a única linha que muda de impressão digital é a da chamada da migração T5.4, declarada em `RATCHET_DELTA` — qualquer outra diferença é recusa |
| `.claude/scripts/env-inventory.json` | livre | NÃO é edição: o derivador compara os nomes da árvore pós-edição (varredura do próprio `env-inventory-check.py`) com os do inventário de HEAD e REGISTRA o único nome novo, `CLAUDE_CODE_EFFORT_LEVEL` (citado pela nota de custo do `effortLevel` no `upgrade.sh`), declarado em `ENV_INVENTORY_DELTA`; a constante do piso no shell (`CC_FLOOR_VERSION`) fica fora da forma de nome de env de propósito; qualquer outra diferença de nomes é recusa |
| `.claude/scripts/tier_policy_cli/_types.py` | livre | `MODEL_ID` e `VALID_MODEL_IDS` += id |
| `.claude/scripts/tier_policy_cli/learn.py` | livre | `_tier_rank`: opus-5=5, opus-5-5=6, fable-5=7, fable-5-1=8 (o comentário diz o que um empate com cada vizinho e um rank acima do Fable assinariam) |
| `.claude/scripts/tier_policy_cli/cli.py` | livre (r14, path novo) | `cmd_owner_sign`: a ação gravada no sigchain (e na mensagem do commit assinado) é o `learn._direction(from, to)`, não mais a comparação de `VALID_MODEL_IDS.index()`; id sem rank no `learn._tier_rank` ou o mesmo modelo nos dois lados → exit 2, nomeado, antes de carregar a chave HMAC e de escrever no sigchain |
| `scripts/local/smoke-install-parity.sh` | livre | `ALLOWED_MODELS`, `EXPECTED_AVAILABLE` (8), `EXPECTED_MODEL` = id, `EXPECTED_EFFORT` = `xhigh`, nenhum `ultracode` instalado; r15: o bloco `harness-claude-stub` logo depois da primeira linha `set -` de topo (o `claude` FALSO da r13, num diretório de `mktemp -d` no PATH, saiu) |
| `scripts/tests/smoke-install.sh` | livre (r13, path novo) | r15: o bloco `harness-claude-stub` logo depois da primeira linha `set -` de topo (substitui o `claude` FALSO no PATH da r13; é a cópia de REFERÊNCIA do guard); o único aviso do `shellcheck -S warning` que o arquivo já tinha na base (SC2010) é dispensado na linha, com o motivo — o LAND passa o shellcheck em todo `.sh` tocado (V1b) |
| `scripts/tests/test-doctor-delivery-route.sh` | livre (r15, path novo) | o bloco `harness-claude-stub` logo depois da primeira linha `set -` de topo |
| `scripts/tests/test-doctor.sh` | livre (r15, path novo) | o bloco `harness-claude-stub` logo depois da primeira linha `set -` de topo |
| `scripts/tests/test-install-deny-baseline.sh` | livre (r15, path novo) | o bloco `harness-claude-stub` logo depois da primeira linha `set -` de topo |
| `scripts/tests/test-install-harness-codex.sh` | livre (r15, path novo) | o bloco `harness-claude-stub` logo depois da primeira linha `set -` de topo |
| `scripts/tests/test-install-harness-grok.sh` | livre (r15, path novo) | o bloco `harness-claude-stub` logo depois da primeira linha `set -` de topo |
| `scripts/tests/test-install-sandbox-merge.sh` | livre (r15, path novo) | o bloco `harness-claude-stub` logo depois da primeira linha `set -` de topo |
| `scripts/tests/test-install-upgrade-parity-e2e.sh` | livre (r15, path novo) | o bloco `harness-claude-stub` logo depois da primeira linha `set -` de topo |
| `scripts/tests/test-installer-write-safety-e2e.sh` | livre (r15, path novo) | o bloco `harness-claude-stub` logo depois da primeira linha `set -` de topo |
| `scripts/tests/test-manifest-delivery-route.sh` | livre (r15, path novo) | o bloco `harness-claude-stub` logo depois da primeira linha `set -` de topo |
| `scripts/tests/test-night-mode-ignore-effect.sh` | livre (r15, path novo) | o bloco `harness-claude-stub` logo depois da primeira linha `set -` de topo |
| `scripts/tests/test-ownership-table.sh` | livre (r15, path novo) | o bloco `harness-claude-stub` logo depois da primeira linha `set -` de topo |
| `scripts/tests/test-parity-stale-planted.sh` | livre (r15, path novo) | o bloco `harness-claude-stub` logo depois da primeira linha `set -` de topo |
| `scripts/tests/test-protocol-pointer-inv4.sh` | livre (r15, path novo) | o bloco `harness-claude-stub` logo depois da primeira linha `set -` de topo |
| `scripts/tests/test-protocol-pointer-render.sh` | livre (r15, path novo) | o bloco `harness-claude-stub` logo depois da primeira linha `set -` de topo |
| `scripts/tests/test-schema-generation-pins-unit.sh` | livre (r15, path novo) | o bloco `harness-claude-stub` logo depois da primeira linha `set -` de topo |
| `scripts/tests/test-two-adopter-isolation-e2e.sh` | livre (r15, path novo) | o bloco `harness-claude-stub` logo depois da primeira linha `set -` de topo |
| `scripts/tests/test-upgrade-dryrun-identity.sh` | livre (r15, path novo) | o bloco `harness-claude-stub` logo depois da primeira linha `set -` de topo |
| `scripts/tests/test-upgrade-exclusions.sh` | livre (r15, path novo) | o bloco `harness-claude-stub` logo depois da primeira linha `set -` de topo |
| `scripts/tests/test-upgrade-historical-adopter.sh` | livre (r15, path novo) | o bloco `harness-claude-stub` logo depois da primeira linha `set -` de topo |
| `scripts/tests/test-upgrade-lifecycle-hooks-derived.sh` | livre (r15, path novo) | o bloco `harness-claude-stub` logo depois da primeira linha `set -` de topo |
| `scripts/tests/test-upgrade-spec-ownership.sh` | livre (r15, path novo) | o bloco `harness-claude-stub` logo depois da primeira linha `set -` de topo |
| `scripts/tests/test-w3-vcures.sh` | livre (r15, path novo) | o bloco `harness-claude-stub` logo depois da primeira linha `set -` de topo |
| `scripts/tests/test_install_baseline_manifest.sh` | livre (r15, path novo) | o bloco `harness-claude-stub` logo depois da primeira linha `set -` de topo |
| `scripts/tests/test_install_state_replay.sh` | livre (r15, path novo) | o bloco `harness-claude-stub` logo depois da primeira linha `set -` de topo |
| `.claude/scripts/cost-table.yaml` | livre | linha do id a 4.00/20.00 (sem linha `-fast`) |
| `.claude/data/model-currency-expected-reds.txt` | livre | causas citam a linha de preço por id, não por número de linha; conjunto de ids INALTERADO |
| `.claude/scripts/audit-telemetry.py` | livre | tabela de preço += id |
| `.claude/scripts/budget-summary.py` | livre | tabela de preço += id; multiplicador de cache-read 0.05 para o id; texto da exceção derivado da tabela; o comentário separa o conjunto da página de preços (Mythos 5.1 a 0.025×, fora do working set) do que o script carrega |
| `.claude/scripts/ceo-cost-transcripts.py` | livre | idem (tabela própria + multiplicador + texto derivado + a mesma separação) |
| `.claude/scripts/ceo-cost.py` | livre | tabela de preço += id |
| `.claude/scripts/success-receipt.py` | livre | tabela de preço += id |
| `.claude/scripts/value-dashboard.py` | livre | tabela de preço += id |
| `.claude/scripts/build-canonical-models.py` | livre | faixa própria `opus-5-5` na reconciliação, ANTES da genérica `opus-5+` (a genérica mediria o id a $5/$25) |
| `.claude/scripts/detectors/overpowered.py` | livre | `_LARGE_MODELS` += id |
| `.claude/scripts/detectors/wasteful_thinking.py` | livre | `_TARGET_MODELS` += id |
| `.claude/scripts/optimizer/model_normalize.py` | livre | alias `opus-5-5`; dobra genérica do sufixo `[1m]`; comentário corrigido (o `[1m]` existe na geração 5) |
| `SUPPORT.md` | livre | linha «Claude Code ≥ 2.1.280» exigida a partir da v1.4.2 (com a recusa do `install.sh`/`upgrade.sh`, a flag, o aviso sem `claude` no PATH ou com versão ilegível — r13: sem linha `(Claude Code)` com versão, ou sem resposta em 10 segundos — e o pré-lançamento contado abaixo do piso) e linha «2.0 a 2.1.279» só até a v1.4.1 (o que editar ao seguir com a flag; o CHANGELOG sobre valores que um CLI não aceita); prosa do allowlist (quem restringe é o `availableModels`; o `enforceAvailableModels: true` só está nas settings do próprio framework, os templates de adopter não o trazem), do pin/fallback e do `effortLevel` (instalação nova; `xhigh` por opt-in; `high` quando o pin migra; organização e `maxEffortLevel`); a linha dos Claude 4.x antigos culpa o `availableModels`; linhas Opus 5.5 e Opus 5; a linha do `[1m]` passa a falar do pin |
| `docs/provider-pricing.md` | livre | id nas tabelas primária, 1M e de proveniência; a exceção de cache-read separa o que a página de preços lista (Fable 5.1 e Mythos 5.1 a 0.025×, Opus 5.5 a 0.05×, relido em 2026-09-24) do que os scripts carregam |
| `docs/cost-of-operation.md` | livre | linha de preço + frase do TL;DR (números não recalculados para o pin novo; «ao mesmo volume de tokens» a parte cobrada como Opus sai mais barata); o spawn mitigado cobra a tarifa do MODELO DA SESSÃO (Opus 4.8 no cálculo; $4/$20 no pin) |
| `docs/CEO-MODEL-ROUTING.md` | livre | literal do working set + nota S357 (o pin do arquivo de agente vale no despacho nativo quando a chamada não passa `model`; o mitigado sem `model` roda no modelo em que a sessão está; limite de taxa próprio do Opus 5.5 na API) + linha do pin de sessão na tabela de papéis |
| `docs/ACCELERATORS.md` | livre | fast mode do Opus 5.5 a $8/$40 (página de preços, lida em 2026-09-23), sem linha `-fast` em nenhum rollup |
| `.claude/hooks/tests/test_claude_adapter_thinking.py` | livre | `TestAdaptiveIsTheDefault` (geração 5, ids futuros incl. `claude-zeta-9`, lista legada, fronteira de segmento, grafia Vertex `@AAAAMMDD` legada e de controle, 4.6+ nunca engolido, ids sempre-ligados, **id listado seguido de outro segmento é OUTRO id** e grafias datada/Bedrock de controle — A-R3CX-01 —, id vazio/None, override de esforço); `disabled` de quem chama mantido em Opus 5/Sonnet 5/4.8/id futuro/`claude-opus-5-5-next` e descartado em Opus 5.5/Fable 5.1 |
| `.claude/hooks/tests/test_effective_config.py` | livre | `[1m]` sobre membro não é remap; a dobra nunca lava outro valor |
| `.claude/hooks/tests/test_template_dogfood_parity.py` | livre | `EXPECTED_PIN` ×2 = id; pin ∈ `VETO_FLOOR_ALLOWED` nos dois espelhos; `effortLevel` base == user; nenhum settings commitado com `ultracode` |
| `.claude/hooks/tests/test_adr149_validator_parity.py` | livre | `ws[-2:] == [fable-5-1, opus-5-5]`; piso com o id |
| `.claude/hooks/tests/test_model_routing.py` | livre | só comentário (citava o nome removido) |
| `.claude/scripts/tests/test_upgrade_settings_migration.py` | livre | `TestScalarLeafGenericBranch`, `TestEffortLevelLeaf` (opt-in), `TestScalarBranchIsGeneric` (tabela PLANTADA numa cópia descartável do `upgrade.sh`: `requires_member_of: fallbackModel`, folha-ARRAY plantada, e `on_migrate_of` como dado — regra aplicada, regra que nomeia folha posterior é aviso, flag e valor presente vencem), `TestPinMigrationKeepsTheEffort` (OQ-8: mapeamento lido da tabela, MIGRATE+REVERT+NOTICE, idempotência, dry-run sem escrita, valor do adopter preservado, a flag vence, SET/pin custom/allowlist sem o id não gravam; `--adopt-setting` sob `--no-settings-migrate` nomeado), `TestClaudeCodeFloor` (OQ-9, com `claude` FALSO no PATH: as duas cópias do bloco iguais e o piso == `notice` == `SUPPORT.md`; abaixo recusa (exit 6) sem escrever, com 2.1.99 contra comparação de string; no piso e acima passa, com 2.1.1000; a flag segue com aviso; sem `claude` ou versão ilegível avisa e segue; dry-run nomeia a recusa sem escrever; o `install.sh` recusa com o alvo vazio; os dois `--help` documentam a flag; r13: a versão lida só da linha `(Claude Code)` — «Node v22.3.0» e «dependency 1.0.0» impressas antes —, o sufixo `-beta.1` abaixo do piso, a sonda parada no limite numa cópia descartável com 2 s e um `claude` cujo FILHO segura a saída, a sonda sem stdin, e o harness que nunca lê o CLI do host), `TestBackupIsAPrecondition` (r13: a dica de re-execução mantém `--adopt-setting` e `--allow-old-claude-code`), `TestMigrationOutputOracles` (r13: o template que a v1.4.1-rc.1 enviou, lido com `git show`, pelo caminho que ACRESCENTA o `effortLevel` — as linhas migradas e uma vírgula, byte a byte; pulado com motivo sem a tag), `TestEveryShippedShapeIsKnown` (literal congelado sobre as tags da S357 + passeio por toda tag `v1.*` alcançável do HEAD, pulado com motivo num checkout sem tags); superseded de 7 ids; citação do contrato de leitura por símbolo; r13: `_clean_env` põe um `claude` FALSO no piso (lido do `upgrade.sh`) primeiro no PATH de TODO spawn do módulo, `baselines()` incluído (r15: o docstring de `_supported_claude_dir` diz por que o módulo mantém o próprio stub — sob `python -m unittest` a camada da suíte não roda); r15: `TestNoHarnessReadsTheHostCli` (sob pytest, o `claude` da suíte é o FALSO do Eixo 4, primeiro no PATH, e um `upgrade.sh` com o ambiente da suíte lê o piso — os dois pulam com motivo sob `python -m unittest`; o censo dos harnesses, re-derivado do disco, com o bloco igual ao de referência logo depois da primeira linha `set -`; o bloco sombreia um `claude` 2.1.279 primeiro no PATH, com o controle sem o bloco saindo 6 sem escrever, vale sob outro PATH que o harness dê a um filho e recusa um checkout sem linha de piso única); r16: `TestEveryFailureExitKeepsTheOperatorFlags` (cada saída de falha da migração forçada — JSON ilegível em apply e em dry-run, ou uma falha plantada numa cópia descartável do `upgrade.sh`: backup, escrita atômica, helper que quebra, `python3` ausente — e o comando impresso relido como o shell o leria, exatamente com as flags do operador e o mesmo alvo; o `--pin` com um `;` e um alvo com espaço, `$` e aspas, citados; nenhuma saída monta o próprio comando) |
| `.claude/scripts/tests/test_generate_available_models.py` | livre | literal `WORKING_SET` + fixture |
| `.claude/scripts/tests/test_gen_settings_user_template.py` | livre | o pin do user template é comparado com a FONTE (base) |
| `.claude/scripts/tests/test_model_fleet_presence.py` | livre | `_NEW_FLEET`; working set lido do ADR em toda superfície; espelho do multiplicador de cache-read (0.05); spawn nativo `[1m]` (o docstring diz que a tag vem de uma sessão que escolheu a variante 1M) |
| `.claude/scripts/tests/test_a4_pricing_doctrine.py` | livre | taxas esperadas += id |
| `.claude/scripts/tests/test_build_canonical_models.py` | livre | faixa própria do Opus 5.5; reconciliação limpa de uma linha a $4/$20 |
| `.claude/scripts/optimizer/tests/test_optimizer_model_normalize.py` | livre | alias; dobra `[1m]`; minor 5.5 nunca dobrado em opus-5 |
| `.claude/scripts/tier_policy_cli/tests/test_types.py` | livre | `len == 8`, `assertIn` |
| `.claude/scripts/tier_policy_cli/tests/test_learn_mutation.py` | livre | opus-5 < opus-5-5 < fable-5 e as direções demote/promote |
| `.claude/scripts/tier_policy_cli/tests/test_cli.py` | livre (r14, path novo) | `OwnerSignDirectionTests` (HMAC, `git` e e-mail simulados; nada fora do diretório temporário): todo id do `VALID_MODEL_IDS` com rank, sem empate; a ação gravada == `learn._direction` nos 56 pares ordenados; os pares Fable ↔ Opus em literal (`fable-5-1` → `opus-5-5` demote e o inverso promote, `fable-5` → `opus-5-5` e `fable-5` → `opus-5` demote, `opus-5` → `opus-5-5` promote); o mesmo modelo e o id sem rank recusados (exit 2) sem sigchain escrito e sem `git` |

## O que este patch NÃO faz

- Não migra nenhum arquivo de agente (`veto_floor: true` segue em
  `claude-fable-5`) nem toca `.claude/agents/`.
- Não muda o `fallbackModel` (`["claude-opus-5"]`).
- Não escreve `xhigh` numa instalação existente sem
  `--adopt-setting effortLevel`; escreve `high` só quando o pin migra de
  `claude-opus-5` num arquivo sem `effortLevel` (OQ-8); nunca sobrescreve
  um valor presente.
- Não põe `ultracode` em nenhum settings commitado.
- Não relaxa o piso do Claude Code nem abre nele um caminho de teste:
  nenhuma variável, flag ou ramo novo no `install.sh`/`upgrade.sh` (a
  cura da rodada 2 do rail vive na camada de isolamento da suíte e nos
  harnesses).
- Não liga o gate T3.4 do `upgrade.sh` (registros DirectoryAdded /
  Notification): o piso sobe, o gate segue como está.
- Não toca o `SPEC/v1/install-cli.md`: ele não lista
  `--allow-old-claude-code`, `--adopt-setting` nem o exit 6 (a tabela de
  saídas dele já parava no 3; ADR-149 A3.5).
- Não toca `_lib/model_routing.py`, o default do revisor em
  `check_codex_stop_review.py`, o enum `MODEL_ID` do `hooks/_lib/tier_policy`,
  o texto da doutrina de `/effort` do `check_agent_spawn.py` nem o alias
  `opus` do `routing-matrix.yaml` (ADR-149 A3.5).
- Não adiciona linha a tabelas de preço por modelo fora do oráculo de
  presença (`test_model_fleet_presence.py`). Os rollups que procuram o
  modelo pela grafia exata não precificam a grafia com `[1m]`.
- Não toca `CHANGELOG.md`, `CLAUDE.md`, `.claude/team.md` (release e
  closeout).

## Regra de parada do rail

Pré-registrada no plano (2026-09-23, antes da 1.ª rodada): no máximo 3
rodadas; um P1 achado SÓ em material vira anexo; no máximo 2 rodadas por
CLASSE de achado; NO-GO só por P0 ou condição declarada falsa. Acrescentado
na r11 (não pré-registrado): o teto é por família (`rail-round-*` sobre os
bytes do patch, `rail-materials-round-*` sobre os materiais), o anexo exige
`Rail-Verdict: APPROVE-WITH-ANNEX` na família de materiais com
`rail-annex.md` rastreado e não-vazio, e o teto conta só registros
RASTREADOS. O SIGN aplica o teto e o anexo; o LAND reaplica o teto. As seis
rodadas codex anteriores ao primeiro registro — cinco em 2026-09-23 (DESIGN
seções 11.2, 11.3, 11.5 e 11.6) e a lente de 2026-09-24 (seção 11.8), todas
no Codex 0.156.1, fora do pin vigente, sem registro rastreado — rodaram
sobre derivações anteriores e não contam: a primeira rodada registrada é a
1 de 3. Uma sétima, a verificação de 2026-09-24 sobre os bytes canônicos da
r12 (codex 0.155.0 via npx), deu NO-GO com três P1 e um P2, curados na r13
(DESIGN seção 11.9); também sem registro rastreado. A rodada 1 REGISTRADA
(`rail-round-1.md`, codex-cli 0.156.1 — o binário que o pack W2 de re-pin
pina — sobre o patch `587df9f4…`) deu `REJECT` com um P2 (o `owner-sign`
que assina pela ordem da tupla), curado na r14. A rodada 2 registrada
(`rail-round-2.md`, o mesmo codex-cli 0.156.1, sobre o patch
`378273c9…`) deu `REJECT` com um P2 (os testes e harnesses que liam o
`claude` do host), curado na r15. A rodada 3 registrada
(`rail-round-3.md`, o mesmo codex-cli 0.156.1, sobre o patch
`e0f2aa33…`) deu `REJECT` com um P2 (a saída de falha do helper da
migração que perdia as flags do operador), curado na r16. Com o teto de
3 atingido, a decisão voltou ao Owner: **OQ-10** (2026-09-24, verbatim
«Corrigir + rodada 4 final c/ anexo (Recomendado)») — cura pela classe e UMA rodada 4, a
última, sobre ESTE patch: limpa ⇒ `Rail-Verdict: APPROVE`; só achados P2
(rotulados P2 pelo codex e confirmados; um P1 nunca é re-rotulado P2) ⇒
`Rail-Verdict: APPROVE-WITH-ANNEX` com `rail-round-4-annex.md` rastreado e
não-vazio, os achados verbatim; P0/P1 ⇒ `REJECT` e volta ao Owner; não há
rodada 5. O SIGN aplica: teto de 4 registros por família, nenhum
registro numerado além da rodada 4 (recusado pelo nome), anexo na
família do patch só na rodada 4 e só com o anexo dela; nas rodadas 1–3,
só `APPROVE`; `REJECT` recusa sempre. O LAND reaplica o teto e a recusa
pelo nome. O anexo de imprecisões da classe «claim de esforço» saiu do
sentinel: as duas imprecisões que ele declarava (a condição do esforço
padrão da organização e o teto `maxEffortLevel`) foram curadas nos textos
na r12.

## Evidência pré-assinatura (S357, 2026-09-24/25, base `19771fa1`; fix round r16)

Os números desta seção são os da r16 (helpers e saídas em
`scratchpad/r4/`, sufixos `r16a`–`r16d`; a derivação final é a `r16d`);
as seções da r15, da r14 e da r13, logo abaixo, seguem como histórico.

- O achado da rodada 3, conferido antes da cura: na derivação r15, das
  saídas da migração que deixam o arquivo sem migrar, só a do backup
  impossível levava as flags; a saída do helper imprimia só
  `--settings-migrate-only`, e a do `python3` ausente não dava comando.
- Derivador (`edits_core.py` 147 edições / 53 paths — as 3 novas no
  `scripts/upgrade.sh`: a rotina, a saída do `python3` ausente e a saída do
  helper; a edição da saída do backup passa a chamar a rotina —,
  `edits_pricing.py` 60 / 20 inalterado; `RATCHET_DELTA` e
  `ENV_INVENTORY_DELTA` inalterados — o derivador regenerou o baseline e
  não recusou): worktree da lane com os 76 paths resetados para o HEAD da
  lane → `--check-only` rc 0 → aplicação única rc 0 (207 edições) → 2.ª
  `--check-only` recusada (guarda de dupla aplicação); conjunto
  modificado == `--list-paths` (76). Numa extração NOVA do HEAD da lane
  (`r4/fresh-r16d`) com os módulos r16: aplicação rc 0, **76/76 byte a
  byte e modo** iguais à worktree (`r4/rederive-r16.sh`).
- Patch re-derivado com as flags pinadas do SIGN
  (`converge/derive_patch.sh`): 7434 linhas, 457.706 bytes, 76 paths (33
  `.py`, 29 `.sh`), `5129 insertions(+), 618 deletions(-)`; Scope do
  sentinel == `git apply --numstat` == `--list-paths` (inalterados).
- Controle VERMELHO da r16 (`r4/redctl-r16`: a derivação r15 inteira + SÓ
  o `test_upgrade_settings_migration.py` da r16d, log
  `r4/redctl-r16d.out`): os 4 testes novos falham, 9 falhas — 6 das 7
  saídas (JSON ilegível em apply e em dry-run, escrita atômica, helper
  que quebra em apply e em dry-run: re-execução sem as flags; `python3`
  ausente: nenhuma linha de re-execução), o teste do `--pin`, o do alvo
  citado e o teste estrutural (a rotina não existia). A saída do backup
  já passava na r15 (era a única que levava as flags), e os 2 testes do
  `TestBackupIsAPrecondition`, cuja expressão do alvo passou a aceitar o
  alvo citado com `printf %q`, passam nas duas derivações.
- Gates na worktree r16d (`r4/gates-r16d.out`):
  `generate-available-models.py --check` `MATCH (8 ids, ADR order
  preserved)`; `gen-settings-user-template.py --check` rc 0;
  `check-installer-write-safety.py` rc 0; `env-inventory-check.py
  --check` rc 0 (515 = 515); `check-model-currency.py --expected-reds`
  rc 0; `build-plugin.py --check` rc 0; `shasum -a 256 --check` do
  manifesto rc 0; `check-ceremony-script.py` 0 bloqueantes sem waiver;
  `check-test-audit-isolation.py` rc 0 (a r16c o reprovava: um `env=`
  condicional no teste novo, que o gate não resolve — todo spawn do teste
  passou a receber o `env` do `_clean_env`; o T15c do harness da r16c
  pegou pelo V9b, log `r4/harness-r16c-T15c-red.log`);
  `check-test-env-hygiene.py` rc 0;
  `bash -n` e `shellcheck -S warning` rc 0 no `upgrade.sh` e nos três
  scripts de cerimônia.
- Testes dirigidos (sem `-n`): a suíte V2 (`EXPECTED_UNIT_TESTS`)
  **809 passed / 2 skipped** (805 + os 4 do
  `TestEveryFailureExitKeepsTheOperatorFlags`); testes diretos do
  `install.sh` e do censo 162 passed.
- Rail codex: TRÊS rodadas registradas (`rail-round-1.md` a
  `rail-round-3.md`), todas `REJECT` com um P2 cada, de classes
  diferentes, curados na r14, na r15 e aqui; nenhuma rodada sobre ESTE
  patch ainda. Pela OQ-10, a rodada 4 é a última: limpa ⇒ `APPROVE`; só
  P2 ⇒ `APPROVE-WITH-ANNEX` com `rail-round-4-annex.md` rastreado; P0/P1
  ⇒ `REJECT` e volta ao Owner.
- Harness `test-ceremony-scripts-opus55.sh` numa raiz descartável
  (`r4/harness-root-r16d`: `19771fa1` + o arquivo do plano sha256
  `8e246ec6…` — a cópia do Owner com a OQ-10 — + estes materiais
  commitados, `rail-round-1.md` a `rail-round-3.md` incluídos; a raiz traz
  a tag `v1.4.1-rc.1`), com `GNUPGHOME` descartável: **PASS=63 FAIL=0
  SKIP=0, rc 0** (2026-09-25 00:21:04→00:43:02 -03, log `r4/harness-r16d.log`). A família
  `rail-round` foi lida com 3 registros, o último `REJECT`; o harness
  plantou `rail-round-4.md` com `APPROVE` SÓ no clone. Os controles da
  OQ-10: T10a (`REJECT` recusado mesmo com o anexo da rodada final
  presente), T10d (teto pela contagem), T10e (anexo na rodada 3 recusado),
  T10h (anexo da rodada final ausente), T10k (anexo não rastreado), T10i
  (controle verde: anexo na rodada 4 — o SIGN assina e o LAND `--dry-run`
  passa), T10j (`rail-round-5.md` recusado pelo nome no SIGN e no LAND) e
  T10l (o mesmo teto nos três scripts). Inclui o land COMPLETO (T15c; o
  V-block com os valores do `EXPECTED-BASELINE.txt`, V2 809 / 2) e a perna
  GPG real com chave descartável (T23). Antes da corrida,
  `validate-governance.sh` completo num clone da raiz com o patch
  aplicado: `Errors: 0` (log `r4/vg-r16d.log`). Depois dela,
  `scripts/tests/smoke-install.sh` na worktree da lane: rc 0 em 125 s
  (`r4/smoke-install-r16d.out`). Depois da corrida só mudou esta nota (os
  outros materiais são byte a byte os da raiz do harness).

## Evidência pré-assinatura (S357, 2026-09-24, base `19771fa1`; fix round r15)

Os números desta seção são os da r15 (helpers e saídas em
`scratchpad/converge/r15/` e `scratchpad/converge/`, sufixos `r15a`–`r15d`;
a derivação final é a `r15d`); as seções da r14 e da r13, logo abaixo,
seguem como histórico.

- O achado da rodada 2, medido antes da cura em EXECUÇÃO, não por grep: os
  41 arquivos de teste pytest que citam `install.sh` ou `upgrade.sh`
  (`converge/r15/py-class.txt`, sem o `test_isolation.py` e o microbench),
  rodados na worktree da derivação r14 com um `claude` FALSO 2.1.279
  primeiro no PATH (`converge/r15/run_with_fake.sh`): **18 falhas em 12
  arquivos, todas `exit 6`** (1846 passaram, 4 pulados), entre elas as
  duas que o codex citou. Harnesses shell: 26 nomeiam um instalador (o
  censo do guard); na r14 só os dois smokes traziam stub. Com um `claude`
  FALSO 2.1.200 primeiro no PATH, sobre a derivação r14,
  `test-install-sandbox-merge.sh` saiu 1 com `ERROR: Claude Code 2.1.200
  is below 2.1.280` e `test-protocol-pointer-render.sh` saiu 1 (o
  `install.sh` do caso R1 falhou); o parity smoke, que já tinha o stub da
  r13, saiu 0.
- Depois da cura, os mesmos 41 arquivos com o mesmo FALSO 2.1.279
  (derivação r15a): **1870 passed, 4 skipped, 0 falhas** (os 6 a mais são
  os testes novos); na r15d, os 12 arquivos que falhavam: 30 passed. Nove
  harnesses shell com um FALSO 2.1.200 primeiro no PATH (derivação r15a):
  `test-install-harness-codex.sh`, `test-install-sandbox-merge.sh`,
  `test-protocol-pointer-render.sh`, `test-upgrade-spec-ownership.sh`,
  `test-w3-vcures.sh`, `test-install-deny-baseline.sh`, `test-doctor.sh`,
  `smoke-install-parity.sh` e `smoke-install.sh`, todos rc 0, nenhuma
  linha `is below 2.1.280`; na r15d, de novo, os dois smokes (o
  `smoke-install.sh` em 124 s), o `test-install-sandbox-merge.sh` e o
  `test-protocol-pointer-render.sh` rc 0.
  Os outros harnesses (entre eles o e2e de ownership, ~25 min) NÃO
  rodaram aqui, por disciplina de CPU: o guard prova que trazem o bloco
  igual, e o bloco é provado em execução pelo guard.
- Derivador (`edits_core.py` 144 edições / 53 paths, `edits_pricing.py`
  60 / 20 — inalterado; `RATCHET_DELTA` e `ENV_INVENTORY_DELTA`
  inalterados: nenhum nome `CLAUDE_*`/`ANTHROPIC_*`/`CEO_*` novo, e o
  censo do ratchet não lê `scripts/tests/`): worktree da lane com os 76
  paths (e os 51 da r14) resetados para o HEAD da lane → `--check-only`
  rc 0 → aplicação única rc 0 (204 edições) → 2.ª `--check-only` recusada
  (guarda de dupla aplicação); conjunto modificado == `--list-paths` (76).
  Numa extração NOVA do HEAD da lane (`converge/fresh-r15d`) com os
  módulos r15: aplicação rc 0, **76/76 byte a byte e modo** iguais à
  worktree (`converge/rederive-r15.sh`).
- Patch re-derivado com as flags pinadas do SIGN
  (`converge/derive_patch.sh`): 7228 linhas, 446.255 bytes, 76 paths (33
  `.py`, 29 `.sh`), `4946 insertions(+), 616 deletions(-)`; Scope do
  sentinel == `git apply --numstat` == `--list-paths`; oráculo
  `--is-canonical` = 1 em 12 dos 76 (o `test_isolation.py` entra; os 24
  harnesses novos são livres); o id novo aparece 0 vezes nos 76 paths em
  HEAD. O censo do guard, rodado na worktree r15, acha exatamente os 26
  harnesses do patch.
- Controle VERMELHO da r15 (`converge/r15/redctl-r15d`: a derivação r14
  inteira + SÓ o `test_upgrade_settings_migration.py` da r15): os 6
  testes novos falham — o `claude` da suíte era o do host, um
  `upgrade.sh` com o ambiente da suíte lia a versão do host, e o bloco de
  referência não existia. Sob `python -m unittest` direto, na r15, 4
  passam e os 2 da camada pytest pulam com o motivo.
- Gates na worktree r15d: `generate-available-models.py --check` `MATCH
  (8 ids, ADR order preserved)`; `gen-settings-user-template.py --check`
  rc 0; `shasum -a 256 --check` do manifesto rc 0;
  `check-model-currency.py --expected-reds` rc 0;
  `check-installer-write-safety.py` rc 0; `env-inventory-check.py
  --check` rc 0 (515 = 515); `build-plugin.py --check` rc 0;
  `check-test-env-hygiene.py` rc 0; `check_contamination.py` rc 0;
  `check-ceremony-script.py` 0 bloqueantes sem waiver; `bash -n` e
  `shellcheck -S warning` rc 0 nos 29 shells tocados.
- Testes dirigidos (sem `-n`): a suíte V2 (`EXPECTED_UNIT_TESTS`)
  **805 passed / 2 skipped** (799 + os 6 do
  `TestNoHarnessReadsTheHostCli`); testes diretos do `install.sh` e do
  censo 162 passed.
- Rail codex: DUAS rodadas registradas (`rail-round-1.md`,
  `rail-round-2.md`), as duas `REJECT` com um P2 cada, de classes
  diferentes, curados na r14 e aqui; nenhuma rodada sobre ESTE patch
  ainda. A rodada 3 é a última dentro do teto; o SIGN recusa enquanto o
  último registro da família `rail-round` não for `Rail-Verdict: APPROVE`.
- Harness `test-ceremony-scripts-opus55.sh` numa raiz descartável
  (`converge/harness-root-r15d`: `19771fa1` + o arquivo do plano sha256
  `6a654c62…` + estes materiais commitados, `rail-round-1.md` e
  `rail-round-2.md` incluídos; a raiz traz a tag `v1.4.1-rc.1`), com
  `GNUPGHOME` descartável: **PASS=56 FAIL=0 SKIP=0, rc 0**
  (2026-09-24 07:14:13→07:34:08 -03, log `converge/r15/harness-r15d.log`).
  A família `rail-round` foi lida com 2 registros, o último `REJECT`; o
  harness plantou `rail-round-3.md` com `APPROVE` SÓ no clone (T10a
  prova o `REJECT` no fim vermelho; T10d, uma 4.ª rodada além do teto
  recusada mesmo com `APPROVE`). Inclui o land COMPLETO (T15c: 78 paths
  = patch + sentinel + `.asc`; o V-block com os valores do
  `EXPECTED-BASELINE.txt` — V1 com 29 `.sh` e 33 `.py` e o shellcheck
  neles, V2 805 / 2) e a perna GPG real com chave descartável (T23).
  Depois da corrida só mudou esta nota (os outros materiais são byte a
  byte os da raiz do harness).

## Evidência da r14 (S357, 2026-09-24, base `19771fa1`; histórico)

Os números desta seção são os da r14 (helpers e saídas em
`scratchpad/converge/`, sufixo `r14`); a seção da r13, logo abaixo, segue
como histórico dos achados que ela curou — os bytes que ela mediu só
mudaram, na r14, em `tier_policy_cli/cli.py`, `tier_policy_cli/tests/test_cli.py`
(os dois paths novos) e no item 8 da A3.2 do ADR-149 (comparação arquivo
a arquivo da derivação r13 guardada em `converge/r13-derived` com a r14:
só esses três diferem).

- O achado da rodada 1, conferido antes da cura
  (`converge/count_inverted.py`, que compara, para cada par ordenado de ids
  distintos do `VALID_MODEL_IDS`, o rótulo pela ordem da tupla com o
  `learn._direction`): na base `19771fa1`, 20 dos 42 pares com o rótulo
  contrário (entre eles `claude-fable-5` → `claude-opus-5` como
  `promote`); na derivação r13, 24 dos 56 (entre eles
  `claude-fable-5-1` → `claude-opus-5-5` como `promote` e o inverso como
  `demote`). O `cmd_owner_sign` era o único leitor da ordem da tupla como
  ordem de tier (busca por `VALID_MODEL_IDS.index` / `VALID_MODEL_IDS[`
  fora dos testes e dos planos: só `cli.py:357-360`).
- Derivador (`edits_core.py` 114 edições / 28 paths, `edits_pricing.py`
  60 / 20 — inalterado; `RATCHET_DELTA` e `ENV_INVENTORY_DELTA`
  inalterados): worktree da lane com os 51 paths (e os 49 da r13)
  resetados para o HEAD da lane → `--check-only` rc 0 → aplicação única
  rc 0 (174 edições) → 2.ª `--check-only` recusada (guarda de dupla
  aplicação); conjunto modificado == `--list-paths` (51). Numa extração
  NOVA do HEAD da lane (`converge/fresh-r14c`) com os módulos r14:
  aplicação rc 0, **51/51 byte a byte e modo** iguais à worktree
  (`converge/rederive-r14.sh`).
- Patch re-derivado com as flags pinadas do SIGN
  (`converge/derive_patch.sh`): 5768 linhas, 370.952 bytes, 51 paths (32
  `.py`, 5 `.sh`), `3794 insertions(+), 616 deletions(-)`; Scope do
  sentinel == `git apply --numstat` == `--list-paths`; oráculo
  `--is-canonical` = 1 em 11 dos 51 (`cli.py` e `test_cli.py` são
  livres); o id novo aparece 0 vezes nos 51 paths em HEAD.
- Controle VERMELHO da r14 (`converge/redctl-r14`: extração do HEAD da
  lane + os 49 arquivos da derivação r13 + SÓ o `test_cli.py` da r14):
  4 falhas, exatamente os testes novos de produto — a ação do par
  inteiro, os pares Fable ↔ Opus em literal, o mesmo modelo recusado e o
  id sem rank recusado —; 22 passam (as 21 de antes e o teste de
  paridade dos ranks, que a r13 já satisfazia).
- Gates na worktree r14: `generate-available-models.py --check` `MATCH
  (8 ids, ADR order preserved)`; `gen-settings-user-template.py --check`
  rc 0; `shasum -a 256 --check` do manifesto rc 0;
  `check-model-currency.py --expected-reds` rc 0;
  `check-installer-write-safety.py` rc 0; `env-inventory-check.py
  --check` rc 0 (515 = 515); `build-plugin.py --check` rc 0;
  `check-test-env-hygiene.py` rc 0; `check_contamination.py` rc 0;
  `bash -n` e `shellcheck -S warning` rc 0 nos 5 shells tocados.
- Testes dirigidos (sem `-n`): a suíte V2 (`EXPECTED_UNIT_TESTS`, agora
  com o `test_cli.py`) **799 passed / 2 skipped** (773 + os 26 do
  `test_cli.py`, 5 deles novos); o diretório de testes inteiro do
  `tier_policy_cli` 213 passed, e o `test_cli.py` também sob `python3 -m
  unittest` (26 OK); testes diretos do `install.sh` e do censo 162
  passed; `check-ceremony-script.py` 0 bloqueantes sem waiver; parity
  smoke rc 0 e `scripts/tests/smoke-install.sh`
  rc 0 em 125 s, os dois com um `claude` 2.1.200 primeiro no PATH do
  chamador.
- Rail codex: UMA rodada registrada, `rail-round-1.md` (2026-09-24,
  codex-cli 0.156.1, payload sha256 `0196e89f…`, `gpt-6-astra`, esforço
  max) — `REJECT`, um P2, curado aqui; nenhuma rodada sobre ESTE patch
  ainda. O SIGN recusa enquanto o último registro da família
  `rail-round` não for `Rail-Verdict: APPROVE`.
- Harness `test-ceremony-scripts-opus55.sh` numa raiz descartável
  (`converge/harness-root-r14c`: `19771fa1` + o arquivo do plano sha256
  `6a654c62…` + estes materiais commitados, `rail-round-1.md` incluído; a
  raiz traz a tag `v1.4.1-rc.1`), com `GNUPGHOME` descartável: **PASS=56
  FAIL=0 SKIP=0, rc 0** (2026-09-24 05:04:56→05:21:50 -03, log
  `converge/harness-r14c.log`). A família `rail-round` foi lida com 1
  registro, o último `REJECT`; o harness plantou `rail-round-2.md` com
  `APPROVE` SÓ no clone (T10a prova o `REJECT` no fim vermelho). Inclui o
  land COMPLETO (T15c: 53 paths = patch + sentinel + `.asc`; o V-block
  com os valores do `EXPECTED-BASELINE.txt` — V2 799 / 2) e a perna GPG
  real com chave descartável (T23). Depois da corrida só mudou prosa
  deste arquivo: esta nota e as duas acrescentadas às notas da
  comparação r13 × r14 e dos testes dirigidos acima (os outros materiais
  são byte a byte os da raiz do harness).

## Evidência da r13 (S357, 2026-09-24, base `19771fa1`; histórico)

A evidência da r12 está SUPERADA por esta (os números abaixo são os da r13;
helpers e saídas em `scratchpad/converge/`).

- Reprodução dos achados da verificação vX sobre a r12, antes de curar
  (`converge/repro/`): (1) o `templates/settings/settings.base.json` que a
  `v1.4.1-rc.1` enviou, pela migração com um `claude` FALSO no piso: além
  do pin e da cauda do `availableModels`, a linha 778 (`  }`, o fecho do
  `statusLine`, fora de qualquer folha migrada) vira `  },` porque o
  `effortLevel` é ACRESCENTADO depois dela — a frase do ADR A3.2 item 6 era
  falsa nessa forma; (2) `claude` FALSOS no dry-run: «Node v22.3.0» antes de
  «2.1.279 (Claude Code)» passava como 22.3.0, «dependency 1.0.0» antes de
  «2.1.280 (Claude Code)» era recusado como 1.0.0, e «2.1.280-beta.1»
  passava como 2.1.280; (3) um `claude` que dorme segurou o upgrade pelo
  sono inteiro (8 s de 8 s).
- Derivador (`edits_core.py` 110 edições / 26 paths, `edits_pricing.py` 60 /
  20 — inalterado; o baseline do ratchet é REGENERADO pelo censo da árvore
  contra o `RATCHET_DELTA` declarado, INALTERADO na r13: a sonda nova não
  cria linha no censo — `kill`/`wait` operam sobre o job `%1`, sem
  expansão — e a guarda `-L` do parity smoke é a forma a1 que o censo
  prova; o inventário de nomes de env tem os nomes REGISTRADOS contra o
  `ENV_INVENTORY_DELTA` declarado, inalterado): worktree da lane com os 49
  paths (e os 48 da r12) resetados para o HEAD da lane (== base nesses
  paths) → `--check-only` rc 0 → aplicação única rc 0 (170 edições) → 2.ª
  `--check-only` recusada (guarda de dupla aplicação); conjunto modificado
  == `--list-paths` (49). Numa extração NOVA do HEAD da lane (`git
  archive`, `converge/fresh-r13d`) com os módulos r13: aplicação rc 0,
  **49/49 byte a byte e modo** iguais à worktree (`converge/rederive.sh`).
- Patch re-derivado com as flags pinadas do SIGN (`converge/derive_patch.sh`,
  o mesmo `DIFF_PIN`/`DIFF_ARGS`): 5566 linhas, 49 paths (30 `.py`, 5
  `.sh`); Scope do sentinel == `git apply --numstat` == `--list-paths`;
  oráculo `--is-canonical` = 1 em 11 dos 49 (o path novo,
  `scripts/tests/smoke-install.sh`, é livre).
- Controles VERMELHOS da r13 (`converge/redctl`: extração do HEAD da lane +
  os 48 arquivos da derivação r12 + SÓ o arquivo de teste da migração da
  r13): 6 falhas, exatamente os testes novos de produto — a dica de
  re-execução com as flags, a versão lida só da linha `(Claude Code)`, o
  sufixo `-beta.1`, a linha sem `(Claude Code)` como versão ilegível, a
  sonda sem stdin e a sonda parada no limite —; 98 passam; 2 pulam, com o
  motivo (extração sem `.git`: o passeio pelas tags e o template da
  `v1.4.1-rc.1`). Isolamento, pela forma de antes: o `upgrade.sh` da r12,
  com o PATH do host, imprimiu `Claude Code:  2.1.281` (o CLI do host); o
  parity smoke e o `smoke-install.sh` da r12 (árvore r12 inteira) com um
  `claude` 2.1.200 primeiro no PATH saíram rc 1 (`ERROR: Claude Code
  2.1.200 is below 2.1.280`), e os da r13 saíram rc 0 com o mesmo PATH.
- Depois da cura, os mesmos `claude` FALSOS: «Node v22.3.0» + «2.1.279
  (Claude Code)» recusa 2.1.279; «dependency 1.0.0» + «2.1.280 (Claude
  Code)» passa (2.1.280); «2.1.280-beta.1 (Claude Code)» recusa (com o
  motivo nomeado); o `claude` que dorme 30 s é parado em ~12 s (limite de
  10 s, +1 s de arredondamento do `SECONDS`, +1 s entre o TERM e o KILL),
  com o aviso «Claude Code version unreadable», e o upgrade segue.
- A sonda (protótipos em `converge/proto/`): bash 3.2.57 (o do macOS) e
  bash 5.3.9 (Homebrew), com e sem pseudo-TTY (`script`), com e sem jobs
  de fundo no processo pai (`disown -a` isola o `%1`): versão rápida lida
  em 0 s; `exec sleep`, filho que dorme segurando a saída, `trap '' TERM`
  e o filho que sobra depois do líder sair — todos parados no limite; stdin
  com dados não chega ao `claude`. Sob bash 5.3 primeiro no PATH, os 16
  testes do piso, do backup e do template enviado passam.
- Gates na worktree r13: `generate-available-models.py --check` `MATCH (8
  ids, ADR order preserved)`; `gen-settings-user-template.py --check` rc 0;
  `shasum -a 256 --check` do manifesto rc 0; `check-model-currency.py
  --expected-reds .claude/data/model-currency-expected-reds.txt` rc 0;
  `check-installer-write-safety.py` rc 0; `env-inventory-check.py --check`
  rc 0; `build-plugin.py --check` rc 0; `check-test-env-hygiene.py` rc 0;
  `check_contamination.py` rc 0; `bash -n` e `shellcheck -S warning` rc 0
  nos 5 shells tocados (o `smoke-install.sh` com o SC2010 da base
  dispensado na linha).
- Testes dirigidos (sem `-n`): a suíte V2 (`EXPECTED_UNIT_TESTS`) 773
  passed / 2 skipped (766 → 773: os 7 testes novos da migração; o passeio
  pelas tags e o template da `v1.4.1-rc.1` RODARAM); o módulo da migração
  106 passed; testes diretos do `install.sh` e do censo
  (`test_install_sh_self_sha.py`, `test_install_sh_session_75_flags.py`,
  `test_check_installer_write_safety.py`) 162 passed; parity smoke
  (`scripts/local/smoke-install-parity.sh`) rc 0; `scripts/tests/smoke-install.sh`
  rc 0 em 123 s com um `claude` 2.1.200 primeiro no PATH do chamador (o
  FALSO do smoke vai na frente dele; a execução do CI entregue só LISTA os
  passos no macOS).
- Rail codex: nenhuma rodada rastreada. Sete rodadas INFORMAIS read-only:
  as seis anteriores (codex-cli 0.156.1, fora do pin) e a verificação de
  2026-09-24 sobre os bytes canônicos da r12 (codex-cli 0.155.0 via npx),
  NO-GO com três P1 e um P2 — curados aqui, com a frase assinada falsa
  que a lente de claims da verificação classificou como bloqueante —;
  nenhuma `rail-round-<N>.md` rastreada — o SIGN recusa sem ela, e o teto
  da regra de parada conta só registros rastreados. Um rail `verified`
  exige o re-pin (pack do W2, 0.156.1) antes da rodada que conta.
- Harness `test-ceremony-scripts-opus55.sh` numa raiz descartável
  (`converge/harness-root-r13a`: `19771fa1` + o arquivo do plano sha256
  `6a654c62…` + estes materiais commitados — a forma da árvore do Owner
  depois do land livre dos materiais; a raiz traz a tag `v1.4.1-rc.1`),
  com `GNUPGHOME` descartável: **PASS=56 FAIL=0 SKIP=0, rc 0**
  (2026-09-24 04:08:25→04:25:31 -03, log `converge/harness-r13a.log`),
  incluindo o land COMPLETO (T15c: 51 paths = patch + sentinel + `.asc`;
  o V-block com os valores do `EXPECTED-BASELINE.txt` — V1b com `bash -n`
  e `shellcheck -S warning` nos 5 `.sh`, V2 773 / 2, V7 parity smoke) e a
  perna GPG real com chave descartável (T23). Rail e trailer SINTÉTICOS só
  no clone. Depois da corrida só mudou esta prosa.
