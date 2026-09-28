# DESIGN — wave-opus55 (PLAN-193 W3 + W4), S357, rodada 2 + integração (2026-09-23) + fix rounds r12, r13, r14 e r15 (2026-09-24)

Pacote atômico derivado por script que adota o **Claude Opus 5.5**
(`claude-opus-5-5`) como pin de sessão, membro do working set e membro do piso
de VETO, e cura a classe adaptive-only do adapter live. Base: `19771fa18257`.
Substrato das medições: Claude Code 2.1.280. Codex: as medições da S357
(22/09) rodaram no codex-cli 0.155.0; em 23/09 o Owner instalou o **0.156.1**
(`codex --version` na worktree da lane). O 0.156.1 está FORA do pin vigente
(`codex-cli-pin.txt` `<0.156.0`, manifesto 0.155.0); o pack de re-pin do W2
(commit `7dcf748e` do branch `s357/codex-pin`, conferido em 2026-09-24) pina
o binário 0.156.1 sob o range `<0.157.0` e ainda não foi assinado — ver
seção 10.

**O que mudou da rodada 1 para esta:** duas decisões do Owner de 23/09
(PLAN-193 OQ-6 e OQ-7), cada uma levantada por 2 críticos concordantes no
debate da W3 — pela regra do debate, o design TINHA de mudar:

- OQ-6 «Só no override local (Recomendado)»: `ultracode` saiu do
  `.claude/settings.json` commitado (e do comentário e do ADR); teste novo
  mantém a chave fora dos três settings commitados.
- OQ-7 «Instalação nova + opt-in (Recomendado)»: o `upgrade.sh` deixou de
  entregar `effortLevel` a quem já instalou; virou folha OPT-IN com a flag
  `--adopt-setting effortLevel` e aviso nomeado com o custo.

**O que a integração acrescentou (consenso do debate, vinculante):** a dobra
do `[1m]` também no tamper check do canal env (SI-10/FIN-2 — deixou de ser
residual, seção 3.6); a Amendment 3 declara pin ≠ fallback como modo de falha
novo com o custo por troca e, desde a r8 (seção 11.4), o limite de taxa
próprio do Opus 5.5 na API, com a contagem na quota de assinatura não
declarada (SI-4/FIN-9);
as linhas REVERT/NOTICE e o `ensure_ascii=False` na migração (seção 3.5); os
controles de teste do Critic-B (tabela PLANTADA numa cópia descartável, id
`claude-zeta-9`, fronteira de segmento, dry-run e 2.º passe pelo ramo escalar,
ida-e-volta byte a byte da forma do template, guarda sobre a forma de CADA
tag, rc incluídas); o `effortLevel` e a ausência de `ultracode` no parity
smoke; os residuais QA-UP-02/05/15 declarados por forma; a regra de parada do
rail pré-registrada e aplicada pelo SIGN (seção 9); o baseline do censo
installer-write-safety REGENERADO pelo derivador (seção 4; fix round r10);
o passo das folhas ARRAY do `upgrade.sh` lido da tabela e o inventário de
nomes de env REGISTRADO pelo derivador (fix round r11, seção 11.7).

## 1. Decisões do Owner que o pacote codifica (verbatim das opções)

| decisão | opção escolhida | onde entra |
|---|---|---|
| papel do Opus 5.5 | «Padrão + piso VETO» | ADR-149 A3.2 itens 1, 2 e 4 |
| esforço dos adopters (OQ-1, 22/09) | «xhigh» | `effortLevel: "xhigh"` no topo de `settings.base.json` e, pela derivação, de `settings.user.json` (instalação NOVA) |
| esforço de quem já instalou (OQ-7, 23/09) | «Instalação nova + opt-in (Recomendado)» | folha T5.4 `effortLevel` com `opt_in: true` + `cost_note`; flag `--adopt-setting effortLevel`; ADR A3.2 item 6 |
| ultracode (OQ-6, 23/09) | «Só no override local (Recomendado)» | nenhum settings commitado leva a chave; ADR A3.2 item 5; teste de guarda |
| esforço de quem migra o pin (OQ-8, 24/09) | «Migrar gravando 'high' (Recomendado)» | atributo `on_migrate_of` da folha `effortLevel` (`{model: {claude-opus-5: high}}`); ADR A3.2 item 6 e A3.4; `TestPinMigrationKeepsTheEffort` |
| piso do Claude Code (OQ-9, 24/09) | «Exigir CC ≥ 2.1.280 (Recomendado)» | bloco `claude-code-floor` byte a byte igual no `install.sh` e no `upgrade.sh`, flag `--allow-old-claude-code`, exit 6; `SUPPORT.md`; ADR A3.2 item 11; `TestClaudeCodeFloor` |
| forma do pacote (OQ-2) | «Exceção declarada (Recomendado)» | seção 5 |
| versão (OQ-3) | «1.4.2» | CHANGELOG/relmeta FORA deste pacote |

Consequências que NÃO são decisão nova, só aplicação: o `fallbackModel`
segue `["claude-opus-5"]`; os arquivos de agente com `veto_floor: true` seguem
em `claude-fable-5`; o working set ganha o id novo NO FIM (regra A1.1).

**Decisão da lane autora (não do Owner), declarada e PENDENTE de
ratificação do Owner:** o dogfood `.claude/settings.json` MANTÉM `effortLevel: "xhigh"`
(consenso pós-debate: o dogfood espelha o template de instalação nova).
A OQ-6 tirou o `ultracode`, mas a pergunta dela nomeava também o `xhigh` em
todo clone, worktree e night-run como parte do risco (fix round r11,
A-R2CL-02): a chave commitada traz de volta essa metade, e o sentinel pede
a ratificação na seção «Decisão pedida ao Owner ANTES do SIGN». Motivo
da manutenção: o dogfood é o formato de uma instalação mantenedor NOVA
(OQ-1), e sem a chave toda worktree
ou night-run sem o overlay local (que é untracked) cairia do `high` padrão do
Opus 5 para o `medium` padrão do Opus 5.5 (onde nenhuma outra fonte define um
nível). Reverter NÃO é uma edição só (corrigido no fix round r10, A-R1CL-03):
pede tirar as duas linhas da edição do dogfood no `edits_core.py`; fazer o
V4a do LAND comparar o `effortLevel` só nos dois templates (hoje compara nos
três contra `EXPECTED_EFFORT_LEVEL`) e o caso T16b do harness acompanhar; e
reescrever as frases que citam a chave do dogfood no item 5 do A3.2 do ADR,
no item 3 do sentinel e no `_EFFORT_COMMENT_DOGFOOD`. Nenhum teste de
unidade amarra a chave no dogfood.

## 2. Estrutura do derivador

- `apply-opus55-edits.py` — clonado em ESTRUTURA do `apply-fable51-edits.py`
  (PLAN-169, S338): âncora EXATA por edição com contagem declarada, recusa
  nomeada em 0 ou 2+, guarda de dupla aplicação no `NEW_ID`, `--root`,
  `--check-only`, `--list-paths`, re-derivação do sha do manifesto ADR-192.
- Três melhorias deliberadas sobre o molde:
  1. **plano e escrita são o MESMO cálculo**: todas as edições são simuladas
     em memória, cada âncora contada no texto PROGRESSIVAMENTE editado do seu
     path; só depois há escrita.
  2. **membros do manifesto DECLARADOS** (`EXPECTED_MANIFEST_MEMBERS`): um gate
     script a mais ou a menos tocado é recusa, nunca re-derivação silenciosa.
     Do mesmo modo (fix round r10) o baseline do ratchet installer-write-safety
     é REGENERADO pelo censo da árvore (a descoberta do próprio instrumento,
     o texto pós-edição nos `.sh` editados) e a diferença de linhas tem de ser
     a DECLARADA (`RATCHET_DELTA`).
  3. **disjunção das metades VERIFICADA (novo nesta rodada)**: um path presente
     em `edits_core.py` e em `edits_pricing.py` é DADOS INVÁLIDOS (saída 2) com
     os paths nomeados. Antes a disjunção era só contrato (e o docstring do
     `edits_core.py` afirmava uma recusa que não existia). Controle negativo:
     cópia descartável com uma metade de preço que toca `SUPPORT.md` → rc 2.
- Leitura/escrita em BYTES; `write_bytes` preserva o modo (bit x do
  `upgrade.sh`).
- Dois módulos de dados: `edits_core.py` (114 edições, 28 paths) e
  `edits_pricing.py` (60 edições, 20 paths) depois do fix round r14 (seção
  11.10). Total: 174 edições em 48 paths, mais o manifesto ADR-192, o
  baseline do ratchet e o inventário de nomes de env (os três DERIVADOS
  pelo script) = 51 paths. Sem `edits_pricing.py` o derivador aplica só o núcleo com NOTA no
  stderr; `--require-pricing` transforma a ausência em recusa — o SIGN e o
  LAND devem passar SEMPRE essa flag.
- `optimizer/model_normalize.py` fica com o builder de preço (alias
  `opus-5-5`, dobra genérica do `[1m]`, comentário corrigido e teste).

## 3. Curas de classe

### 3.1 `upgrade.sh`: ramo ESCALAR genérico com `superseded` (2.ª ocorrência)

1.ª ocorrência (A2 do ADR-149, S338): o array `availableModels` de v1.2.0/v1.3.0
seria lido como ADOPTER-CUSTOMIZED — curado com a lista `superseded` SÓ para
folhas de ARRAY. 2.ª ocorrência (esta): a folha ESCALAR `model` não tinha o
ramo, então todo adopter de v1.2.0-rc.1 até v1.4.1-rc.1 (todos enviaram
`claude-opus-5`) ficaria no pin antigo atrás de um WARNING.

Cura estrutural (não um caso especial do Opus): toda entrada de topo da
tabela T5.4 cujo `"new"` é string passa por UM ramo genérico — ausente/null →
SET; igual a `new` → no-op; igual a um `old` não-nulo ou membro de
`superseded` → MIGRATE; qualquer outro valor → PRESERVADO com aviso nomeado.
O guard C6 virou DADO (`requires_member_of: "availableModels"`); o aviso deixou
de ter `claude-opus-5` literal (derivado da tabela; nunca ecoa valor do
adopter).

### 3.2 Folha OPT-IN (OQ-7) — mecanismo genérico, primeira folha `effortLevel`

- Tabela: `effortLevel = {old: null, new: "xhigh", opt_in: true, cost_note:
  "<texto>"}`. `opt_in` é atributo GENÉRICO do ramo escalar, não código por
  chave.
- Flag: `--adopt-setting <key>` (repetível; charset `^[A-Za-z][A-Za-z0-9]*$`
  checado no bash — vazio, hífen, vírgula ou dígito inicial → `ERROR` + rc 2
  ANTES de qualquer escrita). A lista vai ao Python como argv 6.
- Ramo: veredito SET/MIGRATE numa folha `opt_in` sem a chave adotada → NÃO
  escreve e emite `WARNING: effortLevel NOT written (opt-in leaf): new installs
  ship effortLevel = xhigh; <cost_note>. To write it into this install, re-run
  with --adopt-setting effortLevel`. Valor do adopter numa folha opt-in →
  preservado COM ou SEM a flag e nomeado no stdout SEM aviso (`OK (set by
  the adopter - PRESERVED; opt-in leaf): effortLevel` — fix round r9,
  A-R1M-01: uma folha opt-in não tem baseline de que o adopter possa
  «derivar»; na r8 isso caía no WARNING de ADOPTER-CUSTOMIZED a cada
  upgrade). `--adopt-setting` para chave não-opt-in → aviso nomeado e
  ignorado.
- A tabela T5.4 é a ÚNICA rota de uma chave de topo nova até um adopter
  existente: o merge H8 só carrega `hooks` e `env` (conferido no programa jq do
  `upgrade.sh`); instalação nova recebe o template byte a byte.
- Texto do aviso sem apóstrofo (o corpo Python é string bash entre aspas
  simples; o `edits_core.py` tem `assert` para isso).

Walk e2e sobre os formatos ENVIADOS (sombra, `--settings-migrate-only`, dois
passes cada, byte-idêntico no 2.º; `laneA-core/e2e-shapes-r2.txt`), SEM e COM a
flag: v1.1.0, v1.3.0, v1.4.0, v1.4.1-rc.1 → 8 ids + pin `claude-opus-5-5`;
`effortLevel` ausente + aviso sem a flag, `xhigh` com a flag; adopter com
`model: claude-sonnet-5` e `effortLevel: high` → ambos PRESERVADOS com e sem a
flag; `availableModels` reordenado → array PRESERVADO, pin NÃO migrado,
`effortLevel` só com a flag. 12/12 idempotentes, rc 0.

### 3.3 Adapter live: default INVERTIDO (2.ª ocorrência)

`_ADAPTIVE_ONLY_MODELS` era allowlist de ids adaptive-only; `claude-opus-5` e
`claude-sonnet-5` nunca entraram, então `CEO_EFFORT_OVERRIDE` mandava o formato
legado `budget_tokens` (HTTP 400 no Opus 5.5). Cura: a lista FECHADA agora é a
dos ids pré-4.6; todo o resto é adaptive-only — um id novo nasce seguro.
Casamento: id exato ou id + segmento `-`; prefixo de provedor e tag final
`[...]` ignorados; base datada só casa com segmento de DATA; o sufixo de
versão do Vertex `@AAAAMMDD` é lido como esse segmento de data (fix round
r9, codex rail r1 P1: `claude-sonnet-4@20250514` e afins viravam adaptive).

Mesma classe, segundo efeito (fix round r9, CL-03): a normalização de um
`{type: disabled}` de quem chama era gated pelo mesmo predicado, então a
inversão passaria a DESCARTAR o `disabled` no Opus 5 e no Sonnet 5, cujo
thinking é ligado por padrão e que aceitam `disabled` (tabela da página de
troubleshooting de thinking, lida em 2026-09-23) — thinking ligado em
silêncio. Cura: `_ALWAYS_ON_THINKING_MODELS` (família Fable 5 e Opus 5.5,
os ids sempre-ligados cujo id a lane conferiu na documentação) — só neles o
`disabled` é descartado; nos demais segue como veio. Um id sempre-ligado que
a lista não conhece responde HTTP 400 (erro visível), nunca thinking ligado
em silêncio. Desde o fix round r10 (A-R1M9-07) a lista também tem
`claude-mythos-5` e `claude-mythos-preview` (a página de effort dá os ids;
o casamento por segmento cobre as versões 5.x de cada família).

### 3.5 REVERT, NOTICE e `ensure_ascii=False` (consenso do debate)

- Toda linha MIGRATE é seguida de uma linha `REVERT:`. Valor escalar
  (`model`, `permissions.defaultMode`, folha plantada): a entrada do
  `.claude/settings.local.json` que mantém o valor anterior — local vence o
  arquivo do projeto e o `upgrade.sh` nunca escreve esse arquivo (conferido:
  a única menção dele é a checagem do `.gitignore`); o valor anterior é
  sempre um literal do FRAMEWORK (old/superseded), nunca do adopter. Array
  (`availableModels`, `fallbackModel`) e registro de hook (timeout do
  pair-rail): os escopos de settings MESCLAM esses valores, então a reversão
  é o backup pré-migração (só em modo apply; o dry-run não faz backup).
- Atributo de dado `notice`: linha impressa sempre que a folha é escrita. A
  folha `model` carrega o piso Claude Code 2.1.280 do pin e a rota de volta
  para CLI antigo (QA-UP-02).
- `ensure_ascii=False` na escrita (QA-UP-11): medido — os três settings
  commitados e a base de v1.4.1-rc.1 e v1.2.0 SÃO
  `json.dumps(indent=2, ensure_ascii=False) + "\n"`; com a mudança, a forma
  do template migra de volta ao template BYTE A BYTE (teste). Um surrogate
  solitário no arquivo do adopter (o `json.load` aceita a forma escapada;
  o UTF-8 não o codifica) volta à escrita ESCAPADA das releases anteriores,
  e o arquivo ainda migra (fix round r9, A-R1M-02; na r8 a escrita falhava,
  exit 3, e a migração inteira era pulada — regressão frente à base).

### 3.6 Dobra do `[1m]` no tamper check (SI-10/FIN-2)

`_lib/effective_config._fold_one_m_tag` tira UMA tag final `[1m]` antes do
teste de pertinência ao allowlist (`ANTHROPIC_MODEL`, `ANTHROPIC_DEFAULT_*`,
`ANTHROPIC_SMALL_FAST_MODEL`). Só essa tag exata: `[2m]`, `[1M]`,
`[1m][1m]`, espaço antes da tag e `[1m]` sozinho seguem sinalizados
(fail-closed na entrada). `check-function-length` sobre `_lib`: 192 = 192.

### 3.4 `learn._tier_rank` (SI-8)

`claude-opus-5-5` estritamente ENTRE `claude-opus-5` e `claude-fable-5`
(renumerado: opus-5=5, opus-5-5=6, fable-5=7, fable-5-1=8). Teste prova
`fable-5 → opus-5-5` = demote e `opus-5 → opus-5-5` = promote.

Fix round r14 (rodada 1 do rail, P2; seção 11.10): o `cmd_owner_sign` do
`tier_policy_cli/cli.py` deixa de rotular a ação pela ordem do
`VALID_MODEL_IDS` e grava a do `learn._direction` — uma autoridade só para
a direção, a do learner; id sem rank ou o mesmo modelo nos dois lados é
recusado (exit 2) antes de assinar; o caminho de assinatura ganha testes
(`test_cli.py`, `OwnerSignDirectionTests`).

## 4. Espelhos atualizados no MESMO patch

ADR-149 (bloco do piso + working set + Amendment 3 em prosa);
`agent_frontmatter.VETO_FLOOR_ALLOWED`; `availableModels` gerado nos dois
settings; `settings.user.json` com os bytes que `gen-settings-user-template.py
--check` aceita; case-arm e mensagem do `validate-governance.sh` (+ sha no
manifesto ADR-192); `tier_policy_cli._types` e `test_types` (8);
`smoke-install-parity.sh` (lista, pin, `effortLevel` esperado, nenhum
`ultracode`); `audit_log._ADR_052_ROLE_TO_MODEL["general-purpose"]`; o baseline
installer-write-safety REGENERADO pelo próprio derivador com o censo da
árvore (fix round r10, A-R1M9-03: a versão anterior trocava UMA linha à mão
e deixava defasados os números de linha dos scripts tocados; agora só a
impressão digital da chamada da migração muda, declarada em
`RATCHET_DELTA`, e qualquer outra diferença é recusa); testes
`test_generate_available_models`, `test_adr149_validator_parity`,
`test_template_dogfood_parity` (`EXPECTED_PIN` ×2, pin ∈ piso, `effortLevel`
base == user, nenhum settings commitado com `ultracode`),
`test_upgrade_settings_migration` (`TestScalarLeafGenericBranch`,
`TestEffortLevelLeaf`, `TestScalarBranchIsGeneric`,
`TestMigrationOutputOracles`, `TestEveryShippedShapeIsKnown`),
`test_effective_config` (dobra do `[1m]`), `test_claude_adapter_thinking`
(`claude-zeta-9`, fronteira de segmento, `None`), `test_learn_mutation`,
`test_gen_settings_user_template`, `test_model_routing`. `SUPPORT.md`: linha
«Claude Code ≥ 2.1.280» para o pin, prosa do pin/fallback, instalação nova
com `xhigh` + opt-in no upgrade, prefixo do `availableModels`.

## 5. Exceção declarada à regra ≤ 8 paths (modelo de operação v2)

51 paths (fix round r14), 11 com oráculo `--is-canonical` = 1 (ADR-149,
manifesto ADR-192, adapter live, `agent_frontmatter.py`, `effective_config.py`,
`audit_log.py`, `.claude/settings.json`, `scripts/install.sh`,
`scripts/upgrade.sh`, `settings.base.json`, `settings.user.json`) e o
`validate-governance.sh` (oráculo 0, membro do manifesto ADR-192). Por que não fatiar: os espelhos são amarrados por testes
de paridade no MESMO commit; qualquer fatia intermediária deixa a árvore
vermelha, e `check-model-currency.py` exige a linha de preço no mesmo patch
do append no ADR. Registrada no PLAN-193 (OQ-2); o pacote inteiro sai de UM
derivador, reproduzível byte a byte (seção 8).

## 6. O que fica FORA do pacote e por quê

- `CHANGELOG.md` e relmeta: pertencem ao corte da 1.4.2 (relmeta-142).
- `CLAUDE.md` (39.968 de 40.000 bytes) e `.claude/team.md` (Gate-1): só em
  closeout.
- `.claude/dispatcher/routing-matrix.yaml` (alias `opus`): nota apenas.
- `_lib/model_routing._ROUTING_TABLE`, o default do revisor em
  `check_codex_stop_review.py` e o enum `hooks/_lib/tier_policy MODEL_ID`:
  decisões separadas (ADR-149 A3.5).
- Migrar qualquer agente com `veto_floor: true` para fora do `claude-fable-5`.
- O gate T3.4 do `upgrade.sh` e a linha de piso «Claude Code ≥ 2.0» do
  `SUPPORT.md`: o pacote só declara 2.1.280 como mínimo do PIN.
- `ultracode` em qualquer settings commitado (OQ-6).
- `check_agent_spawn.py` (texto da doutrina de `/effort`), a entrega do
  allowlist do ADR-149 aos adopters, um observador de troca de modelo no
  meio da sessão e o campo `model_source` no `agent_spawn`: resíduos ou
  FOLLOW-UPs declarados no ADR (A3.3/A3.4), não curados aqui — cada um é
  superfície canônica nova com risco próprio. (A dobra do `[1m]` no
  `effective_config.py` ENTROU: consenso do debate, seção 3.6.)

## 7. Debate

Na rodada 2 do core chegou inteiro só o Critic-A; a integração recebeu o
debate completo (Critic-A segurança, Critic-B QA/upgrade, Critic-C FinOps) e
as decisões do CEO depois dele. Os dois riscos com 2+ críticos (OQ-6
segurança + FinOps; OQ-7 QA + FinOps) foram levados ao Owner e o design mudou
conforme as respostas; o consenso vinculante do CEO entrou nos módulos do
derivador. O resto é decisão da lane, com motivo:

| risco | decisão |
|---|---|
| SI-1 (P0) VETO de segurança servido pelo pin no despacho mitigado | ADR A3.3 qualifica o piso por FORMA (nativo vs mitigado/Workflow); teste exige pin ∈ `VETO_FLOOR_ALLOWED` nos dois espelhos com a premissa `CLAUDE_CODE_SUBAGENT_MODEL=inherit` verificada; qual modelo serve um spawn mitigado NÃO foi medido (declarado) |
| SI-2 esforço do VETO não pinado | resíduo A3.4; medir / esforço no frontmatter = FOLLOW-UP |
| SI-3 `ultracode` commitado | **curado por remoção** (OQ-6, 2 críticos) + teste de guarda |
| SI-4 / FIN-9 pin ≠ fallback | A3.4 declara o modo de falha novo, o custo por troca (cache model-scoped: re-escrita a $6,25/MTok e leitura a $0,50/MTok do Opus 5; blocos de thinking do 5.5 perdidos) e (r8, seção 11.4) que na API o 5.5 tem limite de taxa próprio, separado do Opus 5, e a contagem na quota de assinatura do Claude Code não está declarada; cadeia ⊆ piso já testada |
| SI-5 audit log com modelo de política | linha `general-purpose` segue o pin + comentário «POLICY value, not an observation»; `model_source` = FOLLOW-UP |
| SI-6 tamper check inerte nos adopters | declarado em A3.3 |
| SI-7 afirmações falsas do ADR | A3.3 emenda A1.1 por forma (prefixo do harness vs comparação exata) |
| SI-8 rank | curado (3.4) |
| SI-9 contagem «six» | classe por forma (`veto_floor: true`); a contagem do A2.2 item 2 declarada como claim velha (medido: 5 arquivos já no `ab56e76` que a escreveu) |
| SI-10 / FIN-2 `[1m]` no canal env | **curado** (seção 3.6) + 2 testes; resíduo removido da A3.4 |
| SI-11 piso só cresce | resíduo A3.4 |
| (novo, desta lane) adopter sem opt-in cai de high para medium ao migrar o pin | declarado em A3.4; o aviso do upgrade diz o custo e a flag; a resolução registrada da OQ-7 diz o contrário — decisão pedida ao Owner no sentinel (fix round r11, A-R2CL-01) |
| QA-UP-01 re-flip de reversão deliberada | a revisão é a linha REVERT no `settings.local.json` (local vence o projeto; o upgrade nunca escreve nele), então a escolha sobrevive a upgrades futuros; proveniência no install-state = FOLLOW-UP |
| QA-UP-02 CLI < 2.1.280 | `notice` da folha `model` + linha do `SUPPORT.md`; A3.4 declara que nada sonda a versão |
| QA-UP-05 cerimônia user | declarado em A3.4 (rota `--no-settings-migrate` ⇒ pin e esforço à mão) |
| QA-UP-06/07/08/09 testes | controles congelados que falham em HEAD, tabela PLANTADA numa cópia descartável, dry-run e 2.º passe pelo ramo escalar, `claude-zeta-9` + fronteira de segmento |
| QA-UP-10 aviso verdadeiro | aviso derivado da tabela; desde a r9, «<chave> NOT migrated: <new> is not an exact entry of the adopter <array> (the harness may still admit it by prefix) - <chave> left untouched» |
| QA-UP-11 `ensure_ascii` | **curado** (seção 3.5) + oráculo byte a byte da forma do template |
| QA-UP-12 superseded das rc | `TestEveryShippedShapeIsKnown`: forma de CADA tag v1.*, rc incluídas (medido com `git show`) |
| QA-UP-13 espelhos | `EXPECTED_PIN` ×2, `effortLevel` + sem `ultracode` no parity smoke, V6 do LAND reescrito (pin de HEAD superseded, piso +1 contra HEAD, fallback igual ao HEAD) |
| QA-UP-14 colisão de prefixo | lista legada casada por fronteira de segmento; controles `claude-opus-4-10`, `claude-haiku-4-50`, `claude-30-opus` |
| QA-UP-15 downgrade | declarado em A3.4 (release anterior preserva o id e o pin; desfaz = backup ou revert do commit; a linha REVERT só sobrepõe o valor escalar pelo `settings.local.json`) |
| FIN-13 regra de parada do rail | pré-registrada e aplicada pelo SIGN (teto 3 por família; anexo só na família de materiais) — emendada pela decisão do Owner OQ-10 (teto 4; a rodada 4 é a última; anexo também na rodada 4 da família do patch; seção 11.12) |

## 8. Evidência (worktree da lane; rc)

### 8.0 Integração (rodada 2, 2026-09-23) — números superados pela seção 11.4

- Derivador (edits_core `d8da1b58…`, edits_pricing `fd4e9170…`, derivador
  `03c5ced2…`): worktree da lane com os 46 paths resetados para `19771fa1`
  (0 sujos) → `--check-only` rc 0 → aplicação rc 0 (135 edições, 46 paths)
  → 2.ª `--check-only` rc 1 (guarda de dupla aplicação) → conjunto
  modificado == `--list-paths`. `git worktree add --detach` NOVO de
  `19771fa1` (`laneA-integ/fresh-wt-r5`): `--check-only` rc 0, aplicação
  rc 0, 2.ª rc 1, **46/46 byte a byte e modo** iguais à sombra.
- Patch: `WOPUS55.patch` 2839 linhas, sha256 `457c56c3…`, 46 paths, 30 `.py`,
  3 `.sh`; o `--derive-patch` do SIGN reproduz os mesmos bytes (harness
  T22a).
- RED-first dos testes novos (HEAD + só os arquivos de teste,
  `laneA-integ/redhead-r5.*`): upgrade 8 falhas / 3 passam (as 2 guardas de
  forma enviada e o 2.º passe idempotente); o texto fora de ASCII falha pelo
  ESCAPE e a tabela plantada falha com o valor plantado intocado (`'x-a' !=
  'x-b'`) — razão certa; adapter + tamper check 3 falhas / 2 guardas.
- Testes dirigidos: 181 arquivos (todo teste que cita um módulo/arquivo
  tocado ou um id `claude-opus-5*`), sem `-n`: 4909 passed / 50 skipped / 9
  xfailed / 3 falhas — 2 do censo installer-write-safety (curadas no patch
  com a linha nova do baseline; o arquivo re-rodado: 148 passed) e 1
  AMBIENTAL (`test_real_repo_passes`: sem `PLAN-193-*.md` no worktree da
  lane). Depois da última derivação: os 6 arquivos diretamente afetados
  (migração, adapter, tamper check, paridade de template, paridade do
  ADR-149, censo) 364 passed.
- Gates: `generate-available-models.py --check` MATCH 8 ids (dogfood e base);
  `gen-settings-user-template.py --check` OK; JSON dos 3 settings OK;
  `bash -n` + `shellcheck -S warning` rc 0 nos 3 shells tocados e nos 3
  scripts da cerimônia; `shasum -a 256 -c` do manifesto OK;
  `check-model-currency.py --expected-reds` rc 0 (RED-IDS 7);
  `check-installer-write-safety.py` rc 0; `check-test-env-hygiene.py` rc 0;
  `check_contamination.py --root` rc 0; `check-function-length` sobre `_lib`
  192 = 192; `check-ceremony-script.py --json` blocking 0 (só ADVISORY
  herdados do molde).
- Medição do V-block (`laneA-integ/measure_r5.sh`, cópia descartável de
  `19771fa1` + plano + materiais commitados + patch): todo valor de
  `EXPECTED-BASELINE.txt` (V2 736 passed / 2 skipped; parity smoke rc 0 com
  `effortLevel` e sem `ultracode`; verify-counts rc 0; governança completa
  `Errors: 0`; ratchet rc 0; build-plugin rc 0).
- Harness `test-ceremony-scripts-opus55.sh` num clone descartável com
  `GNUPGHOME` descartável: **PASS=45 FAIL=0 SKIP=0**, incluindo o land
  COMPLETO (T15c: 48 paths = patch + sentinel + `.asc`) e a perna GPG real
  com chave descartável (T23). Rail e trailer SINTÉTICOS só no clone — os
  casos provam os gates, não a aprovação.

### 8.1 Rodada 2 do core (histórico; números superados pela 8.0)

- Derivação limpa: `git archive 19771fa18257` + derivador `--require-pricing`
  → 122 edições em 43 paths, **43/43 BYTE-IDÊNTICOS à sombra** (modo
  incluído); 2.ª aplicação → rc 1 (guarda de dupla aplicação); conjunto
  modificado da worktree == `--list-paths`.
- RED-first (HEAD com SÓ as edições de teste, `laneA-core/redhead-r2`):
  upgrade → **17 falhas / 7 passam** (as 7: 5 testes pré-existentes de
  `superseded` de array, o no-op de 2.º passe e «sem a flag a chave nunca
  aparece», que são guardas); adapter → 3 falhas / 3 passam (guardas da lista
  legada); paridade → `effortLevel` base==user falha, pin ∈ piso e «sem
  ultracode» passam (guardas). GREEN na sombra: 24/24, 6/6, 3/3.
- `generate-available-models.py --check` (dogfood e base) rc 0 (MATCH, 8 ids);
  `gen-settings-user-template.py --check` rc 0; JSON dos 3 settings rc 0;
  `bash -n` nos 3 shells rc 0; `shasum -c` do manifesto rc 0;
  `check-model-currency.py --expected-reds` rc 0 (RED-IDS 7).
- pytest dirigido (sem `-n`): hooks **562 passed**; scripts + tier_policy +
  otimizador + preço **752 passed / 2 skipped** (OQ-E5 resolvida; `match` em
  Python 3.9).
- `shellcheck -S warning` (o nível da CI) rc 0 no `upgrade.sh` e no
  `smoke-install-parity.sh`; mesmas classes info-level do HEAD.
- `check-test-env-hygiene.py` rc 0; `check_contamination.py --root` rc 0;
  `check-function-length.py` sem violação nova (adapters 31 = 31; tier_policy
  20 = 20).
- Oráculo `--is-canonical`: 9 paths = 1 (`laneA-core/oracle-r2.txt`).

## 9. Materiais da cerimônia (integração, rodada 2) — RE-DERIVADOS

`OWNER-OPUS55-SIGN.sh`, `OWNER-OPUS55-LAND.sh`,
`test-ceremony-scripts-opus55.sh`, `EXPECTED-BASELINE.txt` (medido de novo),
`COMMIT-MSG-OPUS55.txt`, `PROPOSED-PATCH.md`, `WOPUS55.patch` (46 paths até a
r10; 47 desde a r11) e o
sentinel `wave-opus55-approved.md` foram re-derivados para o design atual:
sem `ultracode` (V4a conta os settings com a chave; esperado 0), folha
`effortLevel` opt-in no V6d, V6 reescrito contra o HEAD (V6g: pin de HEAD
declarado e membro de `model.superseded`, fallback igual ao de HEAD, piso
+1), `test_effective_config.py` na suíte V2, lembrete final verdadeiro.

Regra de parada do rail (PRÉ-REGISTRADA, antes da rodada 1): no máximo 3
rodadas por família (`rail-round-*`, `rail-materials-round-*`); um P1 achado
só em material vira ANEXO (`Rail-Verdict: APPROVE-WITH-ANNEX`, válido SÓ na
família de materiais e só com `rail-annex.md` rastreado e não-vazio); no
máximo 2 rodadas por classe de achado (humano — o registro declara a
classe). O SIGN aplica o teto e o anexo; o LAND reaplica o teto. O harness
prova cada perna (T10d teto, T10e anexo na família errada, T10f anexo sem
arquivo, T10g controle verde) e planta SOBRE o último registro da família,
para que os casos continuem vermelhos pela razão certa depois que rodadas
reais existirem. Emenda da decisão do Owner OQ-10 (2026-09-24, verbatim
«Corrigir + rodada 4 final c/ anexo (Recomendado)»), depois de três rodadas `REJECT` com um P2
cada: UMA rodada 4, a última — teto 4, `rail-round-5.md` recusado pelo
nome, e `APPROVE-WITH-ANNEX` também na família do patch, SÓ na rodada 4 e
SÓ com `rail-round-4-annex.md` rastreado (seção 11.12).

Molde: clonado de `OWNER-S338-FABLE51-{SIGN,LAND}.sh` +
`test-ceremony-scripts-fable51.sh`; sem finalize separado (o SIGN produz e
re-confere o patch byte a byte); trailer `TO-FILL` recusado no SIGN e no
LAND; exatamente um `PLAN-193-*.md` rastreado; harness em clone descartável
com `GNUPGHOME` descartável.

## 10. Riscos abertos

- **Codex 0.156.1 instalado (23/09)**: `codex --version` na worktree diz
  `codex-cli 0.156.1`; o pin vigente é o range `<0.156.0` com manifesto
  0.155.0 ⇒ `--verify-codex-pin` falha fechado e nenhuma rodada de rail
  desta wave fecha como `verified` até um re-pin para 0.156.1 (molde
  `OWNER-PIN-SIGN.sh`, cerimônia própria) ser assinado. O SIGN desta wave
  recusa sem rail rastreado; o harness só usou rail SINTÉTICO no clone.
- Bateria completa (CI inteiro, Smoke Install ~1h50, ownership e2e, testes
  `install_*`, suíte inteira) NÃO rodada aqui por disciplina de CPU. Rodaram:
  181 arquivos de teste dirigidos, o V-block inteiro medido (inclui o parity
  smoke real, o verify-counts e a governança completa) e o land completo do
  harness (T15c).
- O `effortLevel` do dogfood (`xhigh`) muda o esforço desta própria sessão de
  trabalho do framework e de toda worktree/night-run sem overlay local;
  decisão da lane autora pendente de ratificação do Owner (seção 1); reverter toca
  a edição do dogfood, o V4a do
  LAND, o T16b do harness e as frases assinadas que citam a chave (seção 1).
- A dobra do `[1m]` entra num matcher de segurança: só a tag exata e uma
  vez; `[1M]` segue sinalizado (fail-closed — se o harness aceitar a forma
  maiúscula, é falso positivo visível, não furo).
- A linha REVERT de um escalar sugere o `settings.local.json`: a
  precedência local > projeto vem da documentação do Claude Code e das
  sondas S357 no 2.1.280; muda com o substrato.
- O casamento por prefixo vem das sondas S357 no binário 2.1.280; as frases
  sobre o `effortLevel` (valores aceitos, precedência entre arquivos,
  `modelSettings`) vêm da referência de settings do Claude Code lida em
  2026-09-23 (seção 11.4); mudam com o substrato.
- `requires_member_of` compara com igualdade EXATA, mais estrito que o harness
  (prefixo): conservador por desenho.
- O inventário de nomes de env é um dos 51 paths (desde o fix round r11):
  um land livre ou outro pacote que mude `.claude/scripts/env-inventory.json`
  antes deste faz o hunk do inventário não aplicar (G3) e o P1-b do
  SIGN recusar — a mesma colisão por path dos outros 50; e um land que
  traga um nome CLAUDE_*/ANTHROPIC_*/CEO_* novo sem registrá-lo faz o
  derivador recusar (nome fora do `ENV_INVENTORY_DELTA`). Nos dois
  casos a saída é re-derivar sobre o HEAD da hora.
- A sonda do piso do Claude Code (r13) usa job control dentro da captura
  (`disown -a`, `set -m`, `kill %1`) para parar o grupo de processos
  inteiro sem um `timeout` (o macOS não traz): provada no bash 3.2 do
  macOS e no bash 5.3 do Homebrew, com e sem pseudo-TTY e com jobs de
  fundo no pai; NÃO rodada num bash de Linux aqui (o `TestClaudeCodeFloor`
  a exercita no CI, depois do push). Um processo que o CLI tire do grupo e que
  segure a saída ainda segura a sonda (residual no ADR A3.4).
- (Curado na r15, seção 11.11.) Os testes e harnesses que executam o
  `install.sh`/`upgrade.sh` não leem mais o `claude` do host: o Eixo 4
  da camada de isolamento da suíte e o bloco `harness-claude-stub`.
  Ficam, pela forma: um teste que monta um PATH próprio decide que
  `claude` traz; sob `python -m unittest` a camada não roda; um filho
  iniciado com `env -i` perde a função exportada; um harness shell
  fora de um diretório `tests` e de `scripts/local/` não entra no censo
  do guard. Dos harnesses shell, só nove rodaram aqui com um CLI abaixo
  do piso (disciplina de CPU); o guard prova o bloco em todos.
- FOLLOW-UPs declarados e fora do pacote: proveniência das folhas escritas no
  install-state (QA-UP-01), entrega do allowlist aos adopters, observador de troca de modelo, `model_source` no `agent_spawn`,
  piso (modelo, esforço) para VETO, regra de aposentadoria do piso.

## 11. Estado para retomar (lane A core, 23/09 05:26 -03 — pausa do Owner às 06:00)

> Histórico. Os números, contagens e shas desta seção e das subseções 11.1
> a 11.6 (por exemplo `457c56c3…`, 135 ou 149 edições, 46 paths, PASS=45
> ou 54) valem para a rodada em que foram medidos; os vigentes estão na
> seção 11.7 e no `PROPOSED-PATCH.md`.

Esta passada NÃO mudou nenhuma edição, derivador, patch ou material de
cerimônia: só re-verificou o estado das 02:28 e acrescentou esta seção. Fora
este DESIGN, todo material da pasta `wave-opus55/` e o sentinel draft têm
mtime ≤ 02:28 de 23/09.

Re-verificado agora (logs em `scratchpad/laneA-core/resume-0523-*.txt`):

- Reprodução: extração NOVA de `19771fa18257` (`laneA-core/fresh-r5`,
  `laneA-core/cmp_r5.sh`) → `--check-only --require-pricing` 135 edições em
  46 paths → aplicação → **46/46 iguais byte a byte e modo** à worktree →
  nenhum path modificado fora do `--list-paths` → 2.ª passada recusada
  (guarda de dupla aplicação).
- Patch: `laneA-integ/derive-patch-r5.sh` (flags pinadas do SIGN) reproduz
  `WOPUS55.patch` byte a byte; sha256 `457c56c3…` = `Patch-sha256` do
  sentinel; 46 paths no `--numstat` (30 `.py`, 3 `.sh`); oráculo
  `--is-canonical` = 1 em 10 dos 46 (bate com o sentinel).
- Testes dirigidos na sombra, um arquivo por vez, sem `-n`: 17 arquivos,
  todos rc 0 (migração do upgrade 75 passed; adapter 48; tamper check 62;
  paridade template/dogfood 17; paridade ADR-149 14; bijeção do piso 2;
  cobertura ADR-052 7; model routing 15; model_normalize 16; doutrina A4 5;
  build-canonical-models 35; gen-settings-user 120 + 2 skip;
  generate-available-models 12; fleet presence 42; learn mutation 17;
  types 15; model currency 11).
- RED-first de novo (extração de HEAD + SÓ as edições dos 3 arquivos de
  teste, `laneA-core/redhead-r5b`): migração do upgrade rc 1 (28 falhas / 47
  passam — ramo escalar genérico, folha opt-in `effortLevel`, oráculos de
  saída, baseline 8 ids); adapter rc 1 (4 falhas — default adaptive);
  tamper check rc 1 (1 falha — `[1m]`). Os mesmos bytes de teste passam na
  sombra (linha acima).
- Gates não-pytest (`laneA-core/checks.sh`): generator `--check` MATCH 8 ids
  (dogfood e base), `gen-settings-user --check` OK, JSON dos 3 settings OK,
  `bash -n` nos 3 shells, `shasum -c` do manifesto ADR-192 OK,
  `--print-settings-baselines` rc 0, `check-model-currency.py
  --expected-reds` rc 0 (RED-IDS 7). ALL rc 0.
- Corpus gates depois do save-point (materiais já RASTREADOS na branch da
  lane): `check-ceremony-script.py --json` rc 0, 141 descobertos (3 da
  PLAN-193), `blocking_unwaived` 0 — os 3 scripts da cerimônia só com
  ADVISORY (R2a `|| true` cru, herdado do molde); `check-test-env-hygiene.py`
  rc 0.
- Main andou para `5c6ab5f6` (kit do GA 1.4.1): 9 paths mudaram desde
  `19771fa1`, **nenhum** entre os 46 do patch ⇒ o `Patch-base` segue válido
  (o SIGN exige só base ancestral + zero drift nos paths do patch).

NÃO re-rodado nesta passada (CPU; nada mudou desde a medição): o harness
`test-ceremony-scripts-opus55.sh` (último: PASS=45 FAIL=0), o V-block do
`EXPECTED-BASELINE.txt` e os 181 arquivos dirigidos da seção 8.0.

Próximos passos, na ordem (para a noite):

1. **Persistir o arquivo do plano.** `PLAN-193-release-v1-4-2-opus55-fasttrack.md`
   NÃO está no repo vivo (nem rastreado, nem untracked) nem nesta
   worktree; só existe em cópias sob o scratchpad (todas com sha256
   `b148f72db28b…`; a mais nova em
   `laneA-integ/measure-r5/.claude/plans/`). `/private/tmp` é volátil e o
   SIGN exige exatamente um `PLAN-193-*.md` rastreado. Dono: o orquestrador
   (fora da FILE ASSIGNMENT desta lane).
2. **Pin do Codex.** Instalado 0.156.1; pin vigente `<0.156.0` (manifesto
   0.155.0) e o pack de re-pin do W2 pina o binário 0.156.0 ⇒ nenhuma rodada
   de rail desta wave fecha `verified` até um re-pin assinado para o binário
   INSTALADO (cerimônia própria, molde `OWNER-PIN-SIGN.sh`).
3. **Rail.** Rodadas `rail-round-*` (sombra: codex read-only a partir da
   worktree, nunca do repo vivo) e `rail-materials-round-*` (materiais), com
   a regra de parada pré-registrada da seção 9 (≤ 3 por família; P1 só em
   material ⇒ anexo). Achado que exija mudar edição ⇒ editar
   `edits_core.py`/`edits_pricing.py`, re-derivar com `laneA-core/rederive.sh`,
   re-gerar o patch com `laneA-integ/derive-patch-r5.sh`, atualizar o
   `Patch-sha256` do sentinel e re-rodar o harness.
4. **Land livre dos materiais** (último land antes da assinatura): plano +
   `wave-opus55/` + sentinel draft; antes, `git diff --name-only 19771fa1
   HEAD` ∩ `--list-paths` tem de ser vazio (se não for: re-cortar as âncoras
   sobre o HEAD novo, trocar `Patch-base`, re-derivar tudo).
5. Owner: `OWNER-OPUS55-SIGN.sh` → `OWNER-OPUS55-LAND.sh --dry-run` →
   `OWNER-OPUS55-LAND.sh` → commit → push; bateria completa (Smoke Install
   ~1h50) no CI.

Save-point: a branch da lane `s357/wave-opus55` recebe um commit SÓ com a
pasta `.claude/plans/PLAN-193/` (materiais + sentinel draft), para que o
material-fonte sobreviva a uma limpeza do `/private/tmp`; os 46 paths
derivados ficam fora do commit (reproduzíveis byte a byte pelo derivador a
partir de `19771fa1`, provado acima). Esse commit NÃO vai ao main por
cherry-pick cego: o land dos materiais é o passo 4, sobre o HEAD da hora.

### 11.1 Passada do integrador (23/09 05:32–05:42 -03)

Nenhuma edição, derivador, patch ou sentinel mudou; só evidência nova:

- `laneA-core/cmp_r5.sh` de novo (log `laneA-integ/cmp-0535.txt`): 46/46
  byte a byte e modo; 2.ª passada recusada. As linhas `ESCAPE:` agora listam
  os 12 materiais + o sentinel — esperado, porque estão commitados na branch
  da lane e o diff é contra `19771fa1`; nenhum path derivado escapa.
- `laneA-integ/derive-patch-r5.sh` de novo: `WOPUS55.patch` byte-idêntico,
  sha256 `457c56c3…` = `Patch-sha256` do sentinel.
- Oráculo `--is-canonical` nos 46 paths: 10 canônicos (ADR-149, manifesto
  ADR-192, adapter `claude.py`, `agent_frontmatter.py`, `effective_config.py`,
  `audit_log.py`, `.claude/settings.json`, `scripts/upgrade.sh`, os 2
  templates de settings); os materiais respondem 0.
- Main segue em `5c6ab5f6`; interseção com os 46 paths = 0.
- Harness `test-ceremony-scripts-opus55.sh` re-rodado numa raiz descartável
  NOVA (`laneA-integ/harness-root-r6`, construída por
  `laneA-integ/build_harness_root_r6.sh`), GNUPGHOME descartável:
  **PASS=45 FAIL=0 SKIP=0, rc 0** (05:33:25→05:41:24; log
  `laneA-integ/logs/harness-r6.log`).
- **Arquivo do plano — DUAS versões circulam no scratchpad.** `b148f72d…` é
  a vigente (OQ-6 e OQ-7 RESOLVIDAS, regra de parada do rail pré-registrada);
  `3b3008a8…` é ANTERIOR (ainda diz «`ultracode` no settings.json do
  dogfood» — contradiz a decisão do Owner; NÃO usar). O repo vivo não tem
  nenhuma das duas, por isso o builder r5 (que copiava do vivo) não
  reconstrói mais; o r6 copia de
  `laneA-integ/PLAN-193-release-v1-4-2-opus55-fasttrack.md.persist`
  (sha256 `b148f72d…`). Persistir esse arquivo no git continua sendo o passo
  1 acima (dono: orquestrador).

### 11.2 Fix round 1 — triagem (integrador, 23/09 05:55 -03; parada do Owner às 06:00)

Sem tempo para re-derivar antes das 06:00: NADA foi alterado nos módulos
nesta passada; o tree derivado da r6 segue no worktree (não commitado,
reproduzível pelo derivador). Achados da r1, com a sonda feita agora:

| id | veredito | sonda / cura a aplicar no módulo |
|---|---|---|
| CODEX-01 (P0 no texto assinado) | REAL | `escalation_signals.py:71,123` casa por prefixo de família; ADR-149 A3.3 (`:427-429`, «every mirror — compares EXACT ids») é falso. Cura em `edits_core.py`: estreitar para gate de spawn + tamper env (após fold de 1 `[1m]`) + `--check` do gerador; nomear o detector por prefixo como ADVISORY, pela FORMA. Varrer «EXACT»/«every mirror» do A3 inteiro. |
| C1 (P1) | REAL (a confirmar em bytes) | REVERT só sai em apply para folhas-array/hooks. Opção (a): qualificar ADR A3.2 item 6 + sentinel item 4 + comentário `upgrade.sh:162`. |
| C2 (P1) | REAL | `upgrade.sh:3638` mantém ramo próprio de `permissions.defaultMode` sem `superseded`. Cura: estreitar a claim para «folhas escalares de topo» + residual declarado no A3.4. |
| A-R1-03 (P2) | REAL | `upgrade.sh:3623` «excludes». Reescrever: «does not list <pin> as an exact entry» (gerado do baseline, sem literal); ajustar o teste que monta a string. |
| C3/C4/C5 (P2) | aceitar | redação: pin «EXACT member» vs prefixo do harness; precedência projeto>usuário no `_effort_level_comment`/SUPPORT; linha do CEO em CEO-MODEL-ROUTING com o pin primeiro. |
| A-R1-04 (P2) | aceitar | docstring no adapter: aliases são resolvidos antes; + teste que fixa o comportamento de alias. |
| A-R1-01 (P1) | condição | plano `b148f72d…` não rastreado; land livre do plano é do orquestrador (fora da lane). |
| A-R1-02 / CODEX-02 | condição | codex instalado 0.156.1 ≠ pin 0.155.0; re-pin (molde PLAN-189) antes de rodada contar como verificada. |
| COV | pendente | lente de claims sobre DESIGN, resto do sentinel, COMMIT-MSG e PROPOSED-PATCH. |

**Retomar à noite, nesta ordem:** (1) aplicar as curas acima em
`edits_core.py` (e `edits_pricing.py` se tocar); (2) passo 1 da task:
checkout `19771fa1 --` dos paths derivados, derivador único, 2.ª passada
recusada, `--check-only` num worktree fresco em `laneA-integ`; (3) testes
ALVO + `generate-available-models.py --check` + `--check` do
settings.user + `test_check_model_currency.py` + `check-ceremony-script.py`;
(4) re-gerar `WOPUS55.patch`, `Patch-sha256` do sentinel, EXPECTED-BASELINE,
PROPOSED-PATCH; (5) harness em raiz descartável (`build_harness_root_r6.sh`).

### 11.3 Fix round 2 — curas aplicadas nos módulos (integrador, 23/09 06:06 -03 em diante)

Curas em `edits_core.py` (commit `b3c5b335` da branch da lane), árvore
re-derivada do zero (`laneA-integ/rederive-r5.sh`: 46 paths resetados para
`19771fa1`, 136 edições, 2.ª passada recusada rc 1, conjunto modificado ==
`--list-paths`; `--check-only` rc 0 num worktree fresco
`laneA-integ/fresh-r7`):

| achado | cura |
|---|---|
| CODEX-01 / R2-CL-01 / A-R2-CX-01 (P0) | A3.3 estreitado: EXATO só onde o framework DECIDE (gate de spawn, tamper env após a dobra do `[1m]`, `--check` do gerador); classificadores consultivos podem casar por prefixo de família — residual novo no A3.4, pela FORMA. |
| C1 / R2-CL-02 (P1) | `revert_backup()` imprime REVERT também em dry-run («an apply run backs up … copying it back undoes this»); a claim «todo MIGRATE, também em dry-run» fica verdadeira no ADR item 6, no comentário do `upgrade.sh` e no sentinel. Teste novo `test_every_dry_run_migrate_line_is_followed_by_a_revert_line`. |
| A-R2-CX-02 (P0) | semântica de merge corrigida no ADR item 6 e no comentário: `availableModels` e registros de hook fazem merge entre escopos; `fallbackModel` é substituído inteiro por escopo superior — o backup é a rota que restaura o arquivo do projeto. Comportamento inalterado. |
| C2 / R2-CL-03 (P1) | claim estreitada para folhas escalares de TOPO; residual novo no A3.4 (folha aninhada `permissions.defaultMode` sem `superseded`). |
| A-R1-03 / R2-M-02 / R2-CL-04 | aviso: «<new> is not an exact entry of the adopter availableModels (the harness may still admit it by prefix) - model left untouched»; testes montam a string da tabela; comentários do `upgrade.sh` dizem que a checagem é mais estrita que o harness. |
| C3 / R2-CL-05 | `_model_pin_comment` (dogfood e base): «MUST … EXACT member» atribuído às guardas do framework; o harness admite por prefixo. Edição NOVA na base (136.ª). |
| R2-CL-06 | `_effort_level_comment`: «max is not persisted in this key» (o «only the env … carries it» saiu — não sondado). |

Controle vermelho: os módulos da r1 (`fa2d94f`) aplicados em
`laneA-integ/fresh-r7` + o arquivo de teste NOVO ⇒ exatamente 5 falhas (as 4
do texto do aviso + a do REVERT em dry-run), 71 passam.

Diferidos (P2, decisão do integrador): C4 (precedência projeto > usuário no
comentário/SUPPORT — não sondada nesta passada; não se escreve claim sem
sonda), A-R1-04 (docstring/teste de alias no adapter). Condições fora da
lane seguem: plano `b148f72d…` não rastreado; codex 0.156.1 ≠ pin 0.155.0.

### 11.4 Integração r8 — com internet (23/09, a partir das 14:45 -03)

Fatos verificados na documentação oficial nesta passada (lidos em
2026-09-23; o substrato instalado segue Claude Code 2.1.280):

- Referência de settings do Claude Code (`settings-reference`, entradas
  `effortLevel`, `modelSettings`, `ultracode`): o `effortLevel` aceita `low`,
  `medium`, `high` ou `xhigh`; desde a 2.1.251 o `/effort` salva o nível POR
  MODELO em `modelSettings` nas settings de usuário, em vez de escrever o
  `effortLevel`; entre arquivos decide o de maior precedência que define um
  nível para aquele modelo (local > projeto > usuário), e um `effortLevel`
  de topo em settings de projeto, local ou gerenciado vale para todo modelo,
  enquanto um nas settings de USUÁRIO não vale para o Opus 5.5.
- Página de rate limits: «Claude Opus 5.5 and Claude Opus 5 each have a
  separate rate limit» — fora do limite combinado dos Opus 4.x.
- Página de preços: a tabela do Opus 5.5 segue $4 / $20, escrita de cache
  $5 (5 min) / $8 (1 h), leitura $0,20 = 0,05×, batch $2 / $10 — igual ao
  A3.1.

Curas aplicadas nos módulos (o que estava DIFERIDO por falta de sonda):

| achado | cura |
|---|---|
| C4 (P2) + decisão vinculante do CEO («project scope masks user-scope effort» no aviso) | `cost_note` da folha `effortLevel`, `_effort_level_comment` (3 settings), SUPPORT.md e ADR A3.2 item 5 dizem a precedência documentada; A3.1 ganha o fato das settings; A3.4 (instalação sem opt-in) diz que um `effortLevel` de topo nas settings de usuário não vale para o Opus 5.5 |
| frase «Claude Code 2.1.280 persists … in this key» (R2-CL-06 só tinha tirado o «only the env») | trocada por «The key takes low, medium, high or xhigh; max is not one of its values» — o `/effort` persiste em `modelSettings`, não nessa chave |
| SI-4/FIN-9 «bucket de rate-limit não declarado» | a página de rate limits DECLARA limites separados: A3.1 ganha o fato; A3.4 diz que a troca também muda de limite na API e que a contagem na quota de assinatura do Claude Code segue não declarada nem medida; sentinel e COMMIT-MSG acompanham |
| C5 (P2) | `docs/CEO-MODEL-ROUTING.md`: 1.ª linha da tabela de papéis = pin de sessão `claude-opus-5-5` (fallback `claude-opus-5`); a nota S357 qualifica o pin dos arquivos de agente (vale no despacho nativo; o mitigado herda o modelo da sessão sob `CLAUDE_CODE_SUBAGENT_MODEL=inherit`, que os três settings carregam) e cita o limite de taxa próprio |

Segue diferido: A-R1-04 (docstring de alias no adapter). Sonda: o adapter
manda o `model` VERBATIM no corpo da requisição (nenhuma resolução de alias
antes do `_resolve_effort_config`), então a frase proposta («aliases são
resolvidos antes») seria FALSA; um alias sem prefixo `claude-` não é id da
API.

Evidência r8 (logs em `scratchpad/laneA-integ/logs/*-r8*`):

- Derivação: 137 edições em 46 paths; aplicação única na worktree da lane
  (46 paths resetados para `19771fa1`), 2.ª passada recusada; worktree NOVO
  `laneA-integ/fresh-r8`: `--check-only` rc 0, aplicação rc 0, 2.ª rc 1,
  46/46 byte a byte e modo, conjunto modificado == `--list-paths`.
- Patch re-derivado com as flags pinadas do SIGN: 2927 linhas, 46 paths
  (30 `.py`, 3 `.sh`), sha256 `09b6818b…` = `Patch-sha256` do sentinel.
- RED-first (`laneA-integ/redhead-r8`): upgrade 29 falhas / 47, adapter 4 /
  44, tamper check 1 / 61.
- Testes dirigidos: 180 arquivos, 4911 passed / 51 skipped / 9 xfailed + 1
  falha AMBIENTAL (`test_real_repo_passes`, sem o arquivo do plano na lane;
  10 passed na árvore de medição). Depois das duas edições de precisão só em
  prosa (A3.1 «prices above», nota do CEO-MODEL-ROUTING com o
  `CLAUDE_CODE_SUBAGENT_MODEL=inherit`): os 23 arquivos da seleção que leem
  ADR-149, CEO-MODEL-ROUTING, SUPPORT.md, `effortLevel` ou `cost_note` de
  novo, 734 passed / 2 skipped.
- V-block (`measure_r8.sh`): mudaram só o V2 (736 → 737 passed, o teste do
  REVERT em dry-run do fix round 2) e a folha `effortLevel` da tabela T5.4
  (`cost_note` novo) — atualizados CONSCIENTEMENTE no `EXPECTED-BASELINE.txt`
  por `laneA-integ/baseline_r8.py`, que recusa se qualquer outra chave
  divergir da medição (23 chaves iguais).
- Harness: **PASS=45 FAIL=0 SKIP=0, rc 0**, incluindo o land COMPLETO (T15c: 48 paths = patch + sentinel + `.asc`) e a perna GPG real com chave descartável (T23) (15:20:03→15:28:53, log `laneA-integ/logs/harness-r8.log`).
- Gates de corpus sobre a worktree da lane: ceremony-lint `blocking` 0,
  env-hygiene rc 0, contamination rc 0, ratchet rc 0, `shellcheck -S
  warning` rc 0 nos 6 shells.

Próximos passos (fora desta lane): persistir o arquivo do plano
(`b148f72d…`); re-pin do Codex para o binário instalado; rodada de rail que
conta (`rail-round-<N>.md`, teto 3 por família; as duas rodadas informais
da seção 11.2 não deixaram registro rastreado); land livre dos materiais
sobre o HEAD da hora (conferido no fim desta passada: `main` em
`5c6ab5f6`, 9 paths mudados desde `19771fa1`, interseção com os 46 = 0);
SIGN → LAND `--dry-run` → LAND.

### 11.5 Fix round r9 — lentes de mecanismo e de claims + rail codex r1 (23/09, 16:00–17:00 -03, com internet)

Cada achado foi sondado no código ou na documentação oficial (lida em
2026-09-23: troubleshooting de thinking, sub-agents, model-config,
preços, preserved-thinking, visão geral de modelos) antes de virar cura.
Curas SÓ nos módulos do derivador e nos materiais; a árvore foi re-derivada
do zero.

| achado | veredito | cura / motivo |
|---|---|---|
| codex r1 P1 (Vertex `@AAAAMMDD`) | REAL (sondado: `claude-sonnet-4@20250514`, `claude-opus-4-1@20250805` e `claude-sonnet-4-5@20250929` voltavam adaptive) | o sufixo `@` de data vira segmento de data antes do casamento; testes legados e de controle |
| CL-03 (P1) `disabled` descartado no Opus 5/Sonnet 5 | REAL (a tabela oficial: «On» e aceita `disabled`) | `_ALWAYS_ON_THINKING_MODELS` (família Fable 5, Opus 5.5): só neles o `disabled` cai; comentário do cabeçalho pela CLASSE; ADR item 7 + residual no sentinel |
| CL-01 (P0) «toda superfície que precifica» | REAL | sentinel item 10/12, COMMIT-MSG, ADR A3.5 e PROPOSED reescritos pela FORMA (oráculo de presença; o que fica fora; grafia `[1m]` em lookup exato — sondado: 4 rollups procuram a chave exata) |
| CL-02 (P1) piso «vale no nativo» | REAL (ordem de resolução documentada: parâmetro por invocação > frontmatter > env > sessão; `inherit` = sem valor desde 2.1.196) | A3.3, nota do CEO-MODEL-ROUTING, residual do sentinel e docstring do teste de paridade reescritos |
| CL-04 (P1) OQ-6/OQ-7 só num arquivo não rastreado | CONDIÇÃO (fora da lane) + parte REAL | ADR item 5, sentinel e COMMIT-MSG marcam o `effortLevel` do dogfood como decisão da lane; persistir o plano `b148f72d…` segue com o orquestrador |
| CL-05 (P2) fallback «persiste» | REAL (troca por disponibilidade dura um turno; 429 nunca troca; o fallback de CONTEÚDO do 5.5 persiste) | A3.1 ganha os fatos; A3.3 emenda A1.1/A1.3(c); A3.4 reescrito |
| CL-06 (P2) herança de esforço «não medida» / «bloco preso ao modelo» | REAL | A3.1 cita a doc (esforço herda a sessão; o Opus 5 não lê blocos do 5.5); A3.4 reescrito |
| CL-07 (P2) comentário do `model_normalize` | REAL | «uma sessão que selecionou a variante 1M reporta…» |
| CL-08 (P2) tarifa do fast mode | REAL ($8/$40 na página de preços) | ACCELERATORS e A3.1 citam a tarifa |
| CL-09 (P2) frases do A2.1 | REAL | nova emenda por forma no A3.3 |
| CL-10 (P2) «$5/$25» no cost-of-operation | REAL | «a tarifa do modelo da sessão» |
| CL-11 (P2, cauda truncada) | REAL nas três partes sondadas | comentários citam `SessionDefaultPinTest` (o `test_session_default_pin` não existe); o do template deixa de apoiar o «MUST» em testes que não olham o valor do adopter; linha `[1m]` do SUPPORT fala do pin |
| A-R1M-01 (P2) opt-in «nunca chega ao ramo» | REAL | comentário verdadeiro + valor do adopter numa folha opt-in nomeado sem aviso (`OK (set by the adopter - PRESERVED; opt-in leaf)`) |
| A-R1M-02 (P2) `ensure_ascii=False` pula a migração | REAL (regressão frente à base) | volta à escrita escapada; teste do surrogate |
| A-R1M-03 (P2) sonda de versão do CLI | REJEITADO nesta passada | resíduo declarado (A3.4, sentinel, `notice`); endurecer é decisão do Owner |
| A-R1M-04 (P2) harness sem casos de Patch-base | REAL | T24a/T24b |
| A-R1M-05 (P2) SIGN não compara ADRs/paths | REAL | P1-d no SIGN + T25a/T25b; T7 passa a remover uma chave só do V-block |
| A-R1M-06 (P2) G0 tolera path STAGED | REAL | G0 recusa staged fora de {sentinel, `.asc`} + T26 |
| A-R1M-07 / A-R1M-08 | FORA do pacote | FOLLOW-UPs (SET dos arrays na cerimônia user; texto do `_parity_classify.py`) |
| A-R1M-09 | processo | nenhuma ação na lane |

Evidência: `PROPOSED-PATCH.md` §Evidência (144 edições; `fresh-r9` 46/46;
controle vermelho sobre a derivação r8: upgrade 3 falhas, adapter 3 falhas,
todas pela razão certa; dirigidos hooks 2480 / scripts 2246 + 1 ambiental /
demais 190; V2 742 / 2; harness PASS=50 FAIL=0 SKIP=0).

Próximos passos (fora desta lane, inalterados): persistir o arquivo do
plano; re-pin do Codex para o binário instalado; rodada de rail que conta
(`rail-round-<N>.md`; regra de parada de 3 por família — as rodadas
informais não deixaram registro rastreado); land livre dos materiais sobre
o HEAD da hora; SIGN → LAND `--dry-run` → LAND.

### 11.6 Fix round r10 — lentes de mecanismo e de claims sobre a r9 + rail codex r2/r3 (23/09, 20:50–22:15 -03, com internet)

Entrada: os achados da r1 das lentes (A-R1M9-01..08, A-R1CL-01..08; a cauda
da lista chegou TRUNCADA) e as saídas das rodadas codex r2 e r3 sobre os
bytes canônicos da r9 (`review/lanea-r2-codex-out.txt`,
`review/codex-out.txt`). Cada achado foi sondado no código ou na
documentação oficial (cópias lidas em 2026-09-23 sob `review/doc-*.md` e
`review/plat-*.md`) antes de virar cura; as curas estão SÓ nos módulos do
derivador e nos materiais, e a árvore foi re-derivada do zero.

| achado | veredito | cura |
|---|---|---|
| A-R1M9-01 (P1) / A-R1CL-05 / codex r2 #2 — «sem opt-in a sessão cai para medium» | REAL (sondado: um `effortLevel` do adopter no projeto é preservado e segue valendo; a precedência documentada lista escolha explícita, nível salvo, `effortLevel` de projeto/local/gerenciado/`--settings`, `ultracode`, esforço padrão da organização) | condicional pela FORMA no A3.4, no A3.1 (ordem de resolução), no `cost_note`, no SUPPORT.md e no sentinel |
| A-R1M9-02 (P2) / codex r2 #1 / codex r3 #1 — `requires_member_of` só lia `availableModels` | REAL | `effective_arrays[key]` para TODA folha-array, dry-run incluído; teste com folha plantada gated em `fallbackModel` |
| A-R1M9-03 (P2) — baseline do ratchet editado à mão, 251 linhas com número defasado | REAL (regeneração ≠ arquivo; mascarando os números, idênticos) | o derivador REGENERA o baseline com o censo da árvore (descoberta do próprio instrumento, texto pós-edição) e recusa diferença além do `RATCHET_DELTA`; o LAND V9e compara a regeneração byte a byte |
| A-R1M9-04 (P2) — G0 tolera material rastreado sujo | REAL | G0 recusa `git diff HEAD` não vazio sob o diretório da cerimônia e no arquivo do plano (o sentinel, fora dele, é a exceção); harness T3a/T19b/T28 (T3b prova o G2 pelo sha do sentinel) |
| A-R1M9-05 (P2) — V2 só no LAND, depois da assinatura | REAL | P1-e no SIGN: se o HEAD difere da `Patch-base` fora dos materiais desta cerimônia, roda a suite do V2 no worktree do P1-b (HEAD + derivador) e compara com `EXPECTED_UNIT_PYTEST_*` antes do pinentry; a lista vira a chave `EXPECTED_UNIT_TESTS` (um dado, dois leitores); harness T27a/T27b |
| A-R1M9-06 (P2) — batch NATIVO repassa `thinking` | REAL (sondado: `claude_batch.py` copia o dict; opt-in `CEO_NATIVE_BATCH_LIFECYCLE=1`) | RESIDUAL declarado (A3.4, sentinel); curar pediria um 47.º path canônico |
| A-R1M9-07 (P2) — Mythos fora da lista sempre-ligada | REAL (a página de thinking lista Mythos 5.1, 5 e Preview; a página de effort dá os ids) | `claude-mythos-5` e `claude-mythos-preview` em `_ALWAYS_ON_THINKING_MODELS`; comentário, ADR item 7 e sentinel pela forma; teste |
| A-R1M9-08 — incidente do revisor | FORA da lane | nada tocado em `~/.claude`; os dois diretórios residuais ficam para o Owner/orquestrador |
| A-R1CL-01 (P1) — «enforceAvailableModels ⇒ fora da lista não seleciona» | REAL (merge entre escopos não gerenciados; lista gerenciada substitui; quem restringe é o `availableModels`) | SUPPORT.md reescrito pela forma, e a linha dos Claude 4.x antigos |
| A-R1CL-02 (P2) — «enforceAvailableModels rejeita» / ressalva do managed | REAL | comentários do `upgrade.sh`: o Claude Code SUBSTITUI na partida um pin fora da lista; ressalva do dogfood = a documentada (qualquer settings gerenciado) |
| A-R1CL-03 (P2) — «reverter = uma edição» | REAL (o V4a compara os três settings) | DESIGN §1 e §10 corrigidos |
| A-R1CL-04 (P2) — comentário do `_tier_rank` | REAL (empate assina demote) | comentário exato para os dois empates e o rank acima do Fable |
| A-R1CL-06 (P2) — causa do «sem `-fast`» | REAL (o `check-model-currency.py` só lê o `cost-table.yaml`) | ACCELERATORS: escolha do pacote; a causa só para o `cost-table.yaml` |
| A-R1CL-07 (P2) — tag de decisão do Owner no dogfood | REAL | `_EFFORT_COMMENT_DOGFOOD` próprio (decisão da lane) |
| A-R1CL-08 (P2, cauda truncada) — reescrita única de arquivo migrado antes | REAL (o escritor antigo escapava; o novo não) | comentário do escritor, ADR item 6, sentinel e linha `WROTE` («JSON re-serializado») |
| codex r2 #3 — custo de cache da troca afirmado sem condição | REAL (TTL de 5 min / 1 h contado do início do último pedido) | A3.4 e sentinel: a escrita cobre a parte do contexto sem cache vivo no modelo que assume |
| codex r3 #2 (P1) — REVERT aponta um backup que pode não existir | REAL (o `cp` falho era engolido por `\|\| true`) | backup vira PRÉ-CONDIÇÃO: falhou ⇒ migração pulada com nota nomeada, arquivo intacto; teste com FALHA plantada numa cópia descartável; ADR item 6 |
| codex r3 #3 (P0 no texto assinado) — «no nativo o gate confere o arquivo» | REAL (o gatilho é o slug no texto; `subagent_type` não é lido) | A3.3 qualificado + residual novo no A3.4 e no sentinel; o gate não muda |

Evidência: `PROPOSED-PATCH.md` §Evidência (149 edições; `fresh-r10` 46/46;
controle vermelho sobre a derivação r9: upgrade 2 falhas, adapter 1, pela
razão certa; dirigidos hooks 2480 / scripts 2248 + 1 ambiental / demais
190; V2 744 / 2; harness PASS=54 FAIL=0 SKIP=0).

Rejeitado: nenhum achado. Diferido/residual: A-R1M9-06 (declarado);
A-R1M9-08 (fora da lane). A cauda truncada da lista de claims não foi lida
além do A-R1CL-08; o que dela coincidir com os achados das rodadas codex
acima foi tratado por eles.

Próximos passos (fora desta lane): persistir o arquivo do plano; re-pin do
Codex para o binário instalado; rodada de rail que conta
(`rail-round-<N>.md`; teto 3 por família, 2 por classe — a classe
«claim de esforço» já teve duas rodadas); land livre dos materiais sobre o
HEAD da hora; SIGN → LAND `--dry-run` → LAND.

### 11.7 Fix round r11 — lentes de mecanismo (R2M) e de claims (A-R2CL) sobre a r10 (23/09, a partir das 22:45 -03, com internet)

Entrada: os achados R2M-00..07 e A-R2CL-01..09 (a lista chegou TRUNCADA
no meio do A-R2CL-09; a cauda não foi lida). Cada achado foi sondado no
código ou na documentação oficial (cópias lidas em 2026-09-23 sob
`review/laneA-r2-claims/`) antes de virar cura; as curas estão SÓ nos
módulos do derivador e nos materiais, e a árvore foi re-derivada do zero.

| achado | veredito | cura |
|---|---|---|
| R2M-00 | informativo | nada |
| R2M-01 (P2) — o pacote cita `CLAUDE_CODE_EFFORT_LEVEL` e não atualiza o inventário de env | REAL (sondado: `env-inventory-check.py --check` rc 1 na r10, `new=1`; rc 0 na base). O inventário de HEAD já tinha evidências defasadas de 3 nomes, anteriores ao pacote | o derivador REGISTRA os nomes (não regenera: o `--check` compara só nomes, e uma regeneração tornaria os bytes dependentes de arquivos fora do pacote); declarado em `ENV_INVENTORY_DELTA`; recusa nomeada para nome não declarado, declarado ausente e edição direta do inventário (três controles negativos, `laneA-integ/r11/env_controls.sh`); LAND V9g (`EXPECTED_ENV_INVENTORY_RC=0`); 47.º path |
| R2M-02 (P2) — `upgrade.sh --pin <anterior>` aplica a tabela do script em execução | REAL (sondado: `_T54_BASELINES_JSON` é atribuída no topo; o `--pin` só faz `git checkout` no `SOURCE_DIR`) | residual pela forma no ADR A3.4 e no sentinel (o rollback «revert e depois `--pin`» migra de novo para a frente sem `--no-settings-migrate`); anterior ao pacote; a cura estrutural (re-exec do script pinado) é outra wave |
| R2M-03 (P2) — o teto de rodadas conta só registros rastreados | REAL (cinco rodadas codex em 23/09 — 05:53, 06:05, 15:41, 17:15, 20:47 —, todas no 0.156.1, sem registro rastreado) | sentinel e `PROPOSED-PATCH.md` declaram as rodadas, o substrato fora do pin e que o teto conta só registros rastreados |
| R2M-04 / A-R2CL-05 (P2) — o passo das folhas ARRAY percorria uma tupla literal | REAL | o passo percorre a TABELA (toda entrada de topo cujo `new` é lista; `old` opcional); teste com folha-ARRAY PLANTADA e uma escalar amarrada a ela — VERMELHO na derivação r10 (`laneA-integ/r11/red_on_r10.sh`: «MIGRATE ... plantedArray» ausente), verde na r11; a claim do ADR item 6 passou a ser verdadeira sem mudar de texto |
| R2M-05 (P2) — o G-PRE do LAND executava o derivador antes da recusa de material sujo | REAL | o `--list-paths` foi para depois da prova de materiais iguais ao HEAD assinado, no G0; harness T29 (derivador sujo com efeito colateral no import: o G0 recusa e o marcador não existe) |
| R2M-06 (P2) — `/effort off` omite o thinking e o deixa ligado onde ele é padrão | REAL (anterior ao pacote: o ramo legado também omitia) | residual pela forma no ADR A3.4 e no sentinel; cláusula no docstring do resolvedor |
| R2M-07 — incidente do revisor (diretório de estado vazio criado sob `~/.claude/projects/`) | FORA da lane | nada tocado em `~/.claude`; fica para o Owner/orquestrador |
| A-R2CL-01 (P1) — a resolução da OQ-7 diz que o upgrade não muda o esforço de quem já instalou; a migração do pin muda | REAL, e é decisão do Owner (classe «claim de esforço» no teto de 2 rodadas) | NÃO curado: o sentinel ganhou a seção «Decisões pedidas ao Owner ANTES do SIGN» com as opções (a) ratificar pela assinatura e corrigir a linha da OQ-7 no plano antes de rastreá-lo, (b) mudar a tabela e os testes antes do SIGN. O arquivo do plano está fora desta lane |
| A-R2CL-02 (P2) — `effortLevel` xhigh no dogfood traz de volta metade do risco da OQ-6 | REAL | DESIGN seção 1 reescrita (decisão da lane autora, pendente de ratificação); o sentinel pede a ratificação |
| A-R2CL-03 (P2) — texto velho no DESIGN | REAL | seção 3.3 (Mythos na lista desde a r10), seção 7 (texto do aviso da r9), seção 9 (46/47 paths), seção 11 marcada como histórico |
| A-R2CL-04 (P2) — «rejeita um pin» | REAL (página model-config: o Claude Code troca o pin na partida pelo modelo padrão, com aviso) | comentários do pin nos settings dogfood e base; docstring e mensagem do teste de pertença do `test_template_dogfood_parity.py`; varredura da forma «enforceAvailableModels ... reject» no pacote: sobra só texto-âncora (o que é substituído) |
| A-R2CL-06 (P2) — «limite inferior do que o harness admite» | REAL (lista gerenciada substitui) | ADR A3.3 qualificado |
| A-R2CL-07 (P2) — razão (ii) do A1.1 | REAL (cibersegurança vai ao Opus 4.8, `fallbackModel` é `claude-opus-5`) | ADR A3.3: a razão (ii) deixa de valer para o pin |
| A-R2CL-08 (P2) — nota de custo e `SUPPORT.md`: esforço padrão da organização sem condição; teto de esforço ausente | REAL (settings reference: `maxEffortLevel`; model-config: limites por papel) | NÃO curado (classe «claim de esforço» no teto): ANEXO no sentinel, pela forma |
| A-R2CL-09 (P2) — «a parte cobrada como Opus sai mais barata» | REAL (só ao mesmo volume de tokens) | `docs/cost-of-operation.md`: «ao mesmo volume de tokens» |

Rejeitado: nenhum. Diferido para o Owner: A-R2CL-01, A-R2CL-02 (e a linha
da OQ-7 no arquivo do plano, fora desta lane). Anexo: A-R2CL-08. Fora da
lane: R2M-07. A cauda truncada da lista não foi lida.

Evidência: `PROPOSED-PATCH.md` §Evidência (154 edições, 47 paths;
`fresh-r11` 47/47; controle vermelho sobre a derivação r10; dirigidos hooks
2512 / scripts 2271 + 1 ambiental / demais 190; V2 745 / 2; harness no
`PROPOSED-PATCH.md`).

### 11.8 Fix round r12 — decisões do Owner OQ-8/OQ-9 e as lentes da rodada 3 (24/09, com internet)

Entrada: as decisões do Owner de 2026-09-24 (OQ-8 «Migrar gravando 'high'
(Recomendado)», OQ-9 «Exigir CC ≥ 2.1.280 (Recomendado)»; registradas no
arquivo do plano que a lane leu com sha256 `6a654c62…`, fora desta lane —
não o `b148f72d` que a seção 11.1 cita) e os achados da rodada 3
(A-R3M-00..05, LA-R3CL-01..10, A-R3CX-01..02), cada um sondado no código ou
na documentação oficial (cópias de 2026-09-24 em `v142final/A/`) antes de
virar cura. As curas estão SÓ nos módulos do derivador e nos materiais; a
árvore foi re-derivada do zero.

| achado | veredito | cura |
|---|---|---|
| A-R3CX-01 (P0) — o casador de segmento põe `<id listado>-<qualquer segmento>` na classe do id listado; «todo outro id é adaptive-only» era falso para essa forma | REAL (sonda na r11: `claude-haiku-4-5-2` legado, `claude-opus-5-5-next` sempre-ligado) | CÓDIGO: uma entrada casa o id EXATO + UM segmento `-AAAAMMDD` opcional (o `@AAAAMMDD` do Vertex lido como ele) + um sufixo de versão do Bedrock opcional; a única família é `claude-3-*`; a lista sempre-ligada ganha `claude-fable-5-1` e `claude-mythos-5-1` por extenso; testes novos VERMELHOS na r11; texto do ADR A3.2 item 7, do cabeçalho do adapter e do sentinel com a regra |
| A-R3M-01 (P1) — `effortLevel: "xhigh"` num CLI antigo pode derrubar o arquivo inteiro | REAL pela forma (CHANGELOG 2.1.111/2.1.121/2.1.281); o caso exato não medido num binário | OQ-9: bloco `claude-code-floor` no `install.sh` e no `upgrade.sh` (novo path canônico), flag `--allow-old-claude-code`, exit 6; linhas do `SUPPORT.md`; ADR A3.1 (fato do CHANGELOG), A3.2 item 11, A3.4, A3.5 |
| A-R3M-02 (P2) — o derivador roda sem `-I` e um arquivo não rastreado no diretório da cerimônia sombreia a stdlib | REAL (mesmo UID) | NÃO curado nesta rodada: mexe nos três scripts da cerimônia (SIGN, LAND, harness) e no G0/P0-c; fica para a rodada dos materiais |
| A-R3M-03 (P2) — `--adopt-setting` com `--no-settings-migrate` some em silêncio | REAL | aviso nomeado logo depois da checagem do piso; teste; ADR A3.4 |
| A-R3M-04 (P2) — `tool_choice` forçado repassado no id sempre-ligado | REAL (sondado: nenhum chamador fora dos testes) | residual pela forma no ADR A3.4 e no sentinel |
| A-R3M-05 (P2) — a cauda da lista r2 truncada | processo do orquestrador | fora da lane |
| LA-R3CL-01 (P1) — listas de tags à mão | REAL | as frases do ADR, do `upgrade.sh`, dos testes e dos materiais descrevem as tags pela FORMA («toda release de v1.X-rc.1 até a última anterior a esta wave»); o teste ganhou o passeio por toda tag `v1.*` alcançável do HEAD (pulado, nomeado, sem tags) e o literal virou `SHIPPED_AT_S357`, declarado como congelado sobre as tags da S357 |
| LA-R3CL-02 (P1) — resolução da OQ-7 × a migração do pin que baixa o esforço | RESOLVIDO pela OQ-8 | `on_migrate_of` na folha `effortLevel`; ADR A3.2 item 6 e A3.4 reescritos; comentários dos três settings; `SUPPORT.md`; a pergunta ao Owner saiu do sentinel |
| LA-R3CL-03 (P2) — contabilidade da regra de parada | REAL | sentinel e `PROPOSED-PATCH.md` separam a regra pré-registrada da cláusula acrescentada na r11; seis rodadas codex citadas com as seções 11.2, 11.3, 11.5, 11.6 e 11.8; o anexo de classe saiu (as imprecisões foram curadas) |
| LA-R3CL-04 (P2) — os três `_effort_level_comment` sem a condição da organização e sem o `maxEffortLevel` | REAL | cláusulas nos comentários, na nota de custo e no `SUPPORT.md` |
| LA-R3CL-05 (P2) — `enforceAvailableModels` `true` só nas settings do framework | REAL (sondado nos templates) | `SUPPORT.md` qualificado |
| LA-R3CL-06 (P2) — o texto da exceção de cache-read perdeu o Mythos 5.1 | REAL (página de preços relida em 2026-09-24) | `provider-pricing.md`, comentários do `budget-summary.py` e do `ceo-cost-transcripts.py`, ADR A3.3 |
| LA-R3CL-07 (P2) — Mythos Preview aceita o formato estendido; Opus 5 aceita `disabled` só com esforço high ou abaixo | REAL (tabela da página de troubleshooting) | cabeçalho e comentário do adapter; ADR A3.1 |
| LA-R3CL-08 (P2) — citações por número de linha num arquivo que o pacote edita | REAL (e também o `ADR-149:95-102` do mesmo comentário) | citações por SÍMBOLO no `upgrade.sh` e no teste |
| LA-R3CL-09 (P2) — contagens, versão do re-pin e atribuição do dogfood | REAL | 164 edições / 45 paths de edição / 48; cabeçalho diz que o pack do W2 pina o 0.156.1; atribuição única: decisão da lane autora |
| LA-R3CL-10 (P2) — docstring do `[1m]` | REAL | «uma sessão que escolheu a variante 1M» |
| A-R3CX-02 (P2) — a rodada codex rodou fora do pin | REAL | registrada como evidência informal; não conta no teto |

Rejeitado: nenhum achado como falso. Não curados nesta rodada: A-R3M-02
(scripts da cerimônia) e A-R3M-05 (processo, fora da lane).

Evidência: `PROPOSED-PATCH.md` §Evidência (164 edições, 48 paths;
`fresh-r12f` 48/48; controles vermelhos sobre a derivação r11; V2 766 / 2;
testes diretos do `install.sh` 162; parity smoke rc 0; harness no
`PROPOSED-PATCH.md`).

### 11.9 Fix round r13 — a verificação vX sobre a r12 (24/09)

Entrada: o relatório da verificação (lane vX: lente Claude e codex-cli
0.155.0 via npx, read-only, sobre os bytes canônicos da r12, sha do patch
`0f6a3bcf…`): veredito NO-GO por UMA frase assinada falsa, mais três P1 do
codex e um achado menor da própria lente. Cada achado foi REPRODUZIDO
antes da cura (`scratchpad/converge/repro/`); as curas estão SÓ nos módulos
do derivador e nos materiais, e a árvore foi re-derivada do zero.

| achado | veredito | cura |
|---|---|---|
| FRASE FALSA (bloqueante; o codex a deu como P2) — ADR A3.2 item 6: «um arquivo no formato dos templates mantém byte a byte toda linha fora das folhas migradas»; o teste citado semeava do template ATUAL, que já tem `effortLevel`, e nunca passava pelo caminho que ACRESCENTA a chave | REAL (reproduzido: o template da `v1.4.1-rc.1`, pela migração do pin, muda a linha 778 `  }` para `  },`) | a frase foi estreitada à regra verdadeira: só muda, fora das folhas migradas, a linha antes de uma chave que a migração ACRESCENTA (no fim do seu objeto), que ganha a vírgula; a mesma correção no sentinel e na mensagem de commit (que repetia a frase); teste novo que lê com `git show` o template que a `v1.4.1-rc.1` enviou e exige o resultado byte a byte (pulado, nomeado, sem a tag) |
| P1 — o leitor do piso pegava o primeiro x.y.z de toda a saída de `claude --version 2>&1` | REAL (reproduzido com `claude` FALSOS: «Node v22.3.0» antes passava como 22.3.0; «dependency 1.0.0» antes recusava um CLI suportado; «2.1.280-beta.1» passava como 2.1.280) | a versão vem SÓ da primeira linha que nomeia `(Claude Code)`; uma versão com qualquer coisa depois dos três números conta como abaixo do piso (literal, qualquer que seja o número — a flag cobre um pré-lançamento que o operador aceite); uma saída sem essa linha é «version unreadable» (aviso, segue); testes com os três `claude` FALSOS, mais `2.1.281-beta.1` e uma versão sem `(Claude Code)` |
| P1 — a sonda não tinha limite de tempo e herdava o stdin | REAL (reproduzido: um `claude` que dorme segurou o upgrade pelo sono inteiro) | stdin de `/dev/null`; a sonda roda em segundo plano dentro da captura (`disown -a` isola o job, `set -m` lhe dá um grupo de processos próprio, `kill %1` para o grupo inteiro — um FILHO que segura a saída também), consultada contra `CC_FLOOR_PROBE_SECONDS=10` (+1 s de arredondamento do `SECONDS`); no limite, aviso «Claude Code version unreadable: ... did not finish within 10s and was stopped» e segue (infraestrutura, fail-open como a ausência); sem binário `timeout`. A primeira versão, com `kill "$pid"`, criava 12 linhas novas no censo installer-write-safety (`kill`/`wait` com expansão não são provados só-leitura); o `%1` não tem expansão e o `RATCHET_DELTA` ficou como estava. Testes: a sonda parada numa cópia descartável com limite de 2 s e um `claude` cujo filho dorme 60 s; a sonda sem stdin (um `claude` que responde abaixo do piso quando consegue ler uma linha) |
| P1 — o isolamento dos testes dependia do CLI do host | REAL (`_clean_env` copiava o PATH; os dois smokes herdavam o PATH; medido: o `upgrade.sh` da r12 leu o 2.1.281 do host) | `_clean_env` põe um `claude` FALSO que reporta o piso lido do `upgrade.sh` primeiro no PATH de TODO spawn do módulo (`baselines()` incluído); o `TestClaudeCodeFloor` segue passando o PATH dele; `scripts/local/smoke-install-parity.sh` e `scripts/tests/smoke-install.sh` (path novo, 49.º) fazem o mesmo antes de instalar. Controle: a árvore r12 inteira com um `claude` 2.1.200 no PATH — os dois smokes saem rc 1 (exit 6); na r13, rc 0. O `smoke-install.sh` já tinha na base um aviso do `shellcheck -S warning` (SC2010) que o V1b do LAND reprovaria agora que ele é tocado: dispensado na linha, com o motivo. Os outros testes que executam os instaladores (fora do módulo e dos smokes) seguem com o PATH do host: residual declarado (seção 10, sentinel) |
| Menor (lente) — a dica de re-execução do backup falho perdia os `--adopt-setting`; o ADR nomeava só os modos codex como saindo antes da checagem | REAL (os modos `--arming-check`/`--uninstall` com `--harness grok` também saem antes; `--help` e `--print-settings-baselines` também) | a dica mantém os `--adopt-setting` e o `--allow-old-claude-code` que o operador passou (teste com a falha plantada); o ADR A3.2 item 11 descreve pela FORMA o que sai antes da checagem (todo modo que não entrega arquivo do framework — os `--help`, o `--print-settings-baselines`, os modos de ciclo de vida do revisor `codex` ou `grok` — e toda recusa de argumento, de alvo ausente ou de pré-condição); o sentinel também |

Rejeitado: nenhum. Os P2 conhecidos da lente vA (a regra de parada no
sentinel, o item 6 do sentinel sem a regra das bases 4.0, o `exit 0` com o
backup falho e o gate do piso no `--pin` de rollback) ficam fora deste
round, que curou a lista do vX.

Evidência: `PROPOSED-PATCH.md` §Evidência (170 edições, 49 paths;
`fresh-r13d` 49/49; controles vermelhos sobre a derivação r12; V2 773 / 2;
módulo da migração 106; testes diretos do `install.sh` 162; parity smoke e
`smoke-install.sh` rc 0; harness no `PROPOSED-PATCH.md`).

### 11.10 Fix round r14 — a rodada 1 registrada do rail codex (24/09)

Entrada: `rail-round-1.md` (commit `cdb421a82a69`, mantido como registro
histórico): codex-cli 0.156.1 (payload sha256 `0196e89f…`, `gpt-6-astra`,
esforço max, `codex exec review --uncommitted` numa sombra de
`19771fa18257` com o patch `587df9f4…` aplicado sem commit) — `REJECT` com
UM achado, P2. A conferência do verificador na sombra o confirmou; aqui
ele foi medido de novo antes da cura e curado SÓ nos módulos do derivador
e nos materiais, com a árvore re-derivada do zero.

| achado | veredito | cura |
|---|---|---|
| P2 — `tier_policy_cli/cli.py` `cmd_owner_sign` decide a ação que assina por `VALID_MODEL_IDS.index(to) > .index(from)`; com o `claude-opus-5-5` acrescentado DEPOIS das duas entradas Fable, `claude-fable-5-1` → `claude-opus-5-5` sai `promote` enquanto o `learn._direction` diz `demote` (e o inverso também sai trocado) — a operação contrária registrada na cadeia assinada pelo Owner | REAL, e a CLASSE é anterior ao patch (medido com `converge/count_inverted.py`: na base, 20 dos 42 pares ordenados com o rótulo contrário ao do learner, entre eles `claude-fable-5` → `claude-opus-5` como `promote`; na r13, 24 dos 56). O `VALID_MODEL_IDS` é um allowlist na ordem do ADR, não uma ordem de tier; o `cmd_owner_sign` era o único leitor da ordem dele | cura da CLASSE (CLAUDE.md §4), não do exemplo — reposicionar o id na tupla não cura nada: o `cmd_owner_sign` grava a ação do `learn._direction` (a mesma escada do `learn._tier_rank`, uma autoridade só); um id sem rank na escada, ou o mesmo modelo nos dois lados (que antes saía `demote`), é recusado com exit 2 antes de carregar a chave HMAC e de escrever no sigchain. Testes do caminho de assinatura (`test_cli.py`, `OwnerSignDirectionTests`, com HMAC, `git` e e-mail simulados): a ação gravada == `learn._direction` nos 56 pares; os pares Fable ↔ Opus em literal, independentes da tabela do learner; as duas recusas sem sigchain escrito e sem `git`; todo id do `VALID_MODEL_IDS` com rank, sem empate (o teste de rank ≥ 0 da Amendment 2 não pegava empate). O item 8 da A3.2 do ADR passa a dizer o que o `owner-sign` assina e que ele lia a ordem da tupla; o sentinel ganha o item 14, a linha da rodada 1 na regra de parada e o residual das entradas antigas de sigchain |

Paths: `cli.py` e `test_cli.py` entram (51; ambos com oráculo
`--is-canonical` = 0 — os canônicos seguem 11); o `test_cli.py` entra na
suíte V2 (`EXPECTED_UNIT_TESTS`), que vai a 799 / 2. Controle vermelho: o
`test_cli.py` da r14 sobre a derivação r13 falha exatamente nos 4 testes
de produto novos. Nada mudou nos shells, no baseline do ratchet nem no
inventário de nomes de env.

Rejeitado: nenhum. Regra de parada: a família `rail-round` está em 1 de 3;
a próxima rodada registrada roda sobre o patch da r14. A classe «direção
assinada» é nova no rail (primeira rodada dela).

Evidência: `PROPOSED-PATCH.md` §Evidência r14 (174 edições, 51 paths;
`fresh-r14c` 51/51; controle vermelho sobre a derivação r13; V2 799 / 2;
testes diretos do `install.sh` 162; parity smoke e `smoke-install.sh` rc 0;
harness no `PROPOSED-PATCH.md`).

### 11.11 Fix round r15 — a rodada 2 registrada do rail codex (24/09)

Entrada: `rail-round-2.md` (commit `b32f2f11ea12`, mantido como registro
histórico): codex-cli 0.156.1 (payload sha256 `0196e89f…`, `gpt-6-astra`,
esforço max, `codex exec review --uncommitted` numa sombra de
`19771fa18257` com o patch `378273c9…` aplicado sem commit) — `REJECT` com
UM achado, P2. A conferência do verificador na sombra o confirmou e
declarou a classe maior que os dois exemplos; aqui ela foi medida em
EXECUÇÃO antes da cura e curada SÓ nos módulos do derivador e nos
materiais, com a árvore re-derivada do zero.

| achado | veredito | cura |
|---|---|---|
| P2 — com o `claude` 2.1.279 no PATH, `test_install_user_no_writes_outside_claude.py` e `tests/integration/test_install_smoke.py` saem 6 antes de exercitar a instalação: os harnesses herdam o PATH, ao contrário das suítes que a r13 isolou; estender o `claude` FALSO aos harnesses restantes sem enfraquecer a checagem de produção | REAL, e a CLASSE é a que a seção 10 declarava fora da wave («curar a classe inteira pede um ponto único (a camada de isolamento da suíte)»). Medida em execução (não por grep): os 41 arquivos de teste pytest que citam um instalador, com um `claude` FALSO 2.1.279 primeiro no PATH, dão 18 falhas em 12 arquivos, todas `exit 6`; entre os harnesses shell, 26 nomeiam um instalador e só os dois smokes da r13 traziam stub (sobre a r14, com um FALSO 2.1.200, `test-install-sandbox-merge.sh` sai 1 com o erro do piso) | cura da CLASSE (CLAUDE.md §4), nos dois pontos por onde passa toda execução dessas, e nunca no piso de produção: (1) o **Eixo 4** de `_lib/test_isolation.py` (canônico) — a ativação da sessão pytest põe um `claude` FALSO que responde só `--version`, com o piso do `scripts/install.sh` (127 em qualquer outra chamada), primeiro no PATH, dentro da árvore da sessão; PATH e a função `claude` exportada entram no snapshot da restauração, e uma função herdada é descartada (ela passaria por cima de todo FALSO que um teste põe no PATH); (2) o bloco **`harness-claude-stub`**, byte a byte igual, logo depois da primeira linha `set -` de cada harness shell sob um diretório `tests` ou sob `scripts/local/` que nomeia um instalador — exporta uma FUNÇÃO `claude` com a mesma resposta, que o bash roda antes de qualquer entrada do PATH (vale sob qualquer PATH dado a um filho bash que herde o ambiente, o que o stub por diretório no PATH não garantia); os dois smokes trocam o stub por diretório da r13 por ele. Guard, `TestNoHarnessReadsTheHostCli`: o `claude` da suíte é o FALSO, primeiro no PATH; um `upgrade.sh` com o ambiente da suíte lê o piso; o censo dos harnesses é re-derivado do disco (superconjunto: basta nomear um instalador) e cada um traz o bloco igual ao de referência logo depois da primeira `set -`; o bloco sombreia um `claude` 2.1.279 (o mesmo harness sem o bloco sai 6, sem escrever), vale sob outro PATH e recusa um checkout sem linha de piso única. Os dois testes da camada pytest pulam, com motivo, sob `python -m unittest` (o pytest define `PYTEST_CURRENT_TEST`, então sob pytest um Eixo 4 quebrado é VERMELHO) |

Por que dois mecanismos e não um: no pytest o stub é um arquivo no PATH
porque um teste que precisa de outro CLI põe o seu PRIMEIRO no PATH que dá
ao spawn (o `TestClaudeCodeFloor` faz isso) — uma função exportada passaria
por cima dele; nos harnesses shell, que não têm um ponto comum de
cleanup (cada um tem o seu `trap`), a função não cria arquivo nenhum e
sobrevive a um PATH trocado. Um único ponto para todos não existe: os
harnesses shell são chamados um a um pelo CI ou à mão.

Paths: `_lib/test_isolation.py` (canônico — os canônicos vão a 12) e 24
harnesses shell (livres) entram — 76; as edições dos dois smokes mudam;
`TestNoHarnessReadsTheHostCli` entra no `test_upgrade_settings_migration.py`
(V2 805 / 2); `EXPECTED_PATCH_SH_FILES` 5 → 29, `EXPECTED_PATCH_PY_FILES`
32 → 33. Nada mudou no baseline do ratchet (o censo não lê
`scripts/tests/`; o `smoke-install-parity.sh` só perde as escritas do stub
da r13, que não eram linhas do baseline) nem no inventário de nomes de env.

Rejeitado: nenhum. Regra de parada: a família `rail-round` está em 2 de 3;
a rodada 3, sobre o patch da r15, é a ÚLTIMA dentro do teto — se não for
limpa, o SIGN recusa a 4.ª e a decisão volta ao Owner. A classe «harness
herda o ambiente do host» é nova no rail (primeira rodada dela).

Evidência: `PROPOSED-PATCH.md` §Evidência r15 (204 edições, 76 paths;
`fresh-r15d` 76/76; a classe medida antes e depois com os FALSOS 2.1.279 e
2.1.200; controle vermelho sobre a derivação r14; V2 805 / 2; testes
diretos do `install.sh` 162; gates e shellcheck nos 29 shells).

### 11.12 Fix round r16 — a rodada 3 registrada do rail codex e a decisão OQ-10 (24–25/09)

Entrada: `rail-round-3.md` (commit `cd4b565f648a`, mantido como registro
histórico): codex-cli 0.156.1 (payload sha256 `0196e89f…`, `gpt-6-astra`,
esforço max, `codex exec review --uncommitted` numa sombra de
`19771fa18257` com o patch `e0f2aa33…` aplicado sem commit) — `REJECT` com
UM achado, P2. O verificador o confirmou por leitura da sombra. Com a
rodada 3 a família `rail-round` atingiu o teto de 3 (três `REJECT`, cada
um com UM P2 de classe diferente, nenhum P0/P1), e a decisão voltou ao
Owner: **OQ-10** (2026-09-24, verbatim «Corrigir + rodada 4 final c/ anexo (Recomendado)») — cura
do P2 pela classe e UMA rodada 4, a última.

| achado | veredito | cura |
|---|---|---|
| P2 — com `--adopt-setting effortLevel`, quando o parse do settings ou a escrita atômica falha, o tratamento de erro do helper imprime a re-execução sem a flag; segui-la depois de reparar uma instalação Opus 5 grava `high` em vez do `xhigh` pedido, e outra re-execução com a flag não corrige (valores presentes são preservados); reusar o comando que preserva as opções, incluindo `--allow-old-claude-code` | REAL, e a CLASSE é «dica de re-execução de uma saída de falha que perde as flags do operador». Censo na r15: das saídas da migração que deixam o arquivo sem migrar, só a do backup impossível levava as flags (montadas ali mesmo, à mão); a do helper (saída 3 ou qualquer outra não-zero) imprimia só `--settings-migrate-only`; a do `python3` ausente não dava comando nenhum | cura da CLASSE (CLAUDE.md §4) no `scripts/upgrade.sh`, pelo derivador: UMA rotina, `_t54_rerun_cmd`, monta o comando, e as TRÊS saídas imprimem o que ela monta — nenhuma monta o próprio. Ela leva cada flag do operador que decide o que a migração lê ou escreve, ou se ela roda: os `--adopt-setting` (o que ela pode escrever), o `--allow-old-claude-code` (se ela roda num Claude Code abaixo do piso), o `--pin` (o checkout da fonte cujo template ela lê) e o `--dry-run` (se ela escreve); todo valor do operador — o alvo e o ref do `--pin` — sai citado com `printf %q`, porque um caminho ou um nome de ref pode ter um metacaractere. Na saída do helper, o backup pré-migração só é nomeado quando existe (um dry-run não o escreve). Guard, `TestEveryFailureExitKeepsTheOperatorFlags`: cada saída forçada (JSON ilegível em apply e em dry-run; uma FALHA plantada numa cópia descartável do `upgrade.sh` — backup, escrita atômica, helper que quebra em apply e em dry-run, `python3` ausente), com o `settings.json` intacto e o comando impresso relido com `shlex` exatamente com as flags do operador e o mesmo alvo; o `--pin` com um ref `pin;v1` num repositório git descartável; um alvo com espaço, `$` e aspas; e nenhuma saída com o próprio comando (só a rotina tem o caminho do script e o `--settings-migrate-only`). Controle vermelho sobre a r15: 9 falhas (6 das 7 saídas, o `--pin`, o alvo citado e o estrutural) |

O `--pin` entra porque o template que a migração lê vem do checkout da
fonte que ele escolhe; uma re-execução sem ele leria o template de outro
checkout. O preço é declarado pela forma: com `--pin`, o `upgrade.sh`
recusa (exit 2, salvo `CEO_ORCH_FORCE=1`) um alvo que é repositório git
com modificação rastreada não commitada em `.claude/` — a que o próprio
upgrade escreveu, ou o JSON reparado —, com a mensagem que diz o que
fazer: recusa nomeada, nunca uma migração diferente em silêncio.
Variáveis de ambiente (`CEO_T34_NEW_EVENT_REGISTRATIONS`,
`CEO_ORCH_FORCE`) não são flags e não entram no comando.

Materiais (OQ-10, pela forma): `RAIL_MAX_ROUNDS` 3 → 4 no SIGN, no LAND
e no harness; no SIGN, um registro numerado além da rodada final
(`rail-round-5.md`) é recusado pelo NOME, qualquer que seja o veredito; na
família do patch o veredito `APPROVE-WITH-ANNEX` vale SÓ na rodada 4 e SÓ
com `rail-round-4-annex.md` rastreado e não-vazio (lido pelo nome; o glob
da família o pula); nas rodadas 1–3, só `APPROVE`; `REJECT` recusa
sempre (na rodada final, nomeando que não há outra). O LAND reaplica o
teto e a recusa pelo nome e não conta o anexo como registro. O harness
ganha um controle por regra: T10a (REJECT recusado mesmo com o anexo da
final presente), T10d (teto pela contagem, com um `rail-round-01.md`),
T10e (anexo na rodada 3 recusado), T10h (anexo da final ausente — o
`rail-annex.md` dos materiais não o substitui), T10k (anexo da final não
rastreado), T10i (controle verde: anexo na rodada 4 — o SIGN assina e o
LAND `--dry-run` passa), T10j (`rail-round-5.md` recusado pelo nome no
SIGN e no LAND) e T10l (SIGN, LAND e harness com o mesmo teto); quando a
rodada final já existe e não autoriza, o registro sintético do harness a
substitui no clone em vez de numerar uma 5.ª.

Paths: os mesmos 76 (12 canônicos); `EXPECTED_UNIT_PYTEST_PASSED` 805 →
809; o ADR-149 A3.2 item 6 passa a dizer a regra da classe (toda saída que
deixa o arquivo sem migrar, UMA rotina, as quatro flags, os valores
citados), e os 2 testes do `TestBackupIsAPrecondition` aceitam o alvo
citado. Nada mudou no baseline do ratchet (o derivador o regenerou e não
recusou) nem no inventário de nomes de env.

Rejeitado: nenhum. Regra de parada: a família `rail-round` está em 3 de
4; a rodada 4, sobre o patch da r16, é a ÚLTIMA (OQ-10). A classe desta
rodada é nova no rail (primeira rodada dela).

Evidência: `PROPOSED-PATCH.md` §Evidência r16 (207 edições, 76 paths;
`fresh-r16d` 76/76; controle vermelho sobre a derivação r15; V2 809 / 2;
testes diretos do `install.sh` 162; gates, ceremony-lint e shellcheck).
