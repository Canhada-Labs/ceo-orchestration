# Pacote F — `settings.user.json` DERIVADO da base por subtração declarada

> S330 (2026-08-27). Alvo canônico: `templates/settings/settings.user.json`.
> Achado de origem: **PLAN-169 OQ-E5**, aberta no closeout do pacote E
> (`5930974`): o template `user` estava DEFASADO em 16 hooks não-deliberados.
> Classificação por mérito: `hook-classification-S330.md` (commit `4f4df3a`).
> Trabalho feito em sombra (`git clone --local` de `1c34eb5`); nada tocado no
> repo vivo. Molde: `PLAN-169/s329-ceremony-E/DESIGN-E.md` §1–§4.

## 1. O que mudou, em cinco linhas

| Dimensão | Antes (pré-S330) | Depois |
|---|---|---|
| **Fonte** | cópia MANUAL de `settings.base.json` com hooks apagados à mão, congelada em `9777a8d` (só o pin de modelo mudou depois, em `8ed9f6f`) | `templates/settings/settings.base.json` + a subtração DECLARADA na chave `_derivation` do próprio arquivo gerado |
| **Mecanismo** | nenhum — o arquivo era o artefato e a explicação era prosa no `_comment` | `.claude/scripts/gen-settings-user-template.py`, único aplicador; `--check` / `--write` / `--json` |
| **Verificação** | nenhuma. O `_comment` afirmava «removendo exatamente 10» e «entradas retidas byte-idênticas nos campos comportamentais» — **as duas afirmações eram FALSAS** e nenhum gate as lia | `--check` compara BYTE a byte; `test_gen_settings_user_template.py` fecha a integridade do spec (exclusão morta, override morto, classe fora do vocabulário, `reason`/`evidence` vazios, chave de topo não-declarada ⇒ vermelho) |
| **Critério** | prosa que **não se sustentava**: dos 10 «bloqueia ou exige GPG», só 5 sustentam (§2) | uma linha em `_derivation.criterion`, e cada exclusão com `class` de vocabulário fechado + `reason` + `evidence` linha-a-linha |
| **Roster entregue** | 20 registros | **29 registros** (28 basenames): a classificação mandou 10 por MÉRITO; o Owner reverteu 1 na r7 (§7.12); nenhum sai |

## 2. Antes/depois por registro

Base enumera **47** registros (46 `.py` em 45 basenames distintos, mais **1
comando INLINE** sem script — ver §3.1). O template `user` passa de **20** para
**29**; o conjunto só-na-base cai de 27 para **18**, e os 18 são exatamente as
`exclude_hooks` do spec. Predições da classificação (§3 «notas»): 30 registros,
29 basenames, 17 base-only — **as três bateram exatamente** na medição
PRÉ-decisão; após a reversão do Owner (§7.12) o artefato gerado mede
**29 / 28 / 18**.

### 2.1 Os 10 que a classificação mandou ENTRAR (nenhum removido; 9 entram — §7.12)

| Evento / hook | Por que entra (classificação §1.1) |
|---|---|
| `ConfigChange` / `check_config_change.py` | única defesa contra `disableAllHooks` no momento da edição; entra **com** `CEO_CONFIG_CHANGE_GUARD=1` declarado |
| `PostToolUse` / `accel_dispatch.py` | advisory, fail-OPEN; já viajava no plugin advisory |
| `PostToolUse` / `check_skill_reference_read.py` | observer; a metade EMISSORA (`check_agent_spawn.py`) já está no perfil user — sem ele o contrato ADR-051 do adopter é inauditável |
| `PostToolUseFailure` / `check_output_secrets.py` | a 2ª registração de um hook JÁ retido: uma ferramenta que **falha** é onde stack-trace vaza segredo |
| `PreToolUse` / `check_scratchpad_access.py` | guarda `scratchpad.py`, que o perfil user **recebe**; não bloqueia edição e não usa sentinel — **revertido pelo Owner na r7: EXCLUIR (§7.12)** |
| `SessionStart` / `turbo_sessionstart.py` | só `additionalContext`; já no plugin advisory |
| `Setup` / `check_setup_verification.py` | fecha «hook no disco mas não registrado»; valor puro para quem não roda `validate-governance.sh` à mão |
| `Stop` / `codex_review_user_code.py` | o propósito declarado é revisar o código DO ADOPTER |
| `Stop` / `review_loop.py` | inerte por default (`CEO_REVIEW_LOOP` é opt-in) |
| `SubagentStart` / `check_subagent_start.py` | **repara assimetria existente**: `check_fluency_nudge.py` (`SubagentStop`) já está no user e é o CONSUMIDOR deste sidecar |

### 2.2 Os 18 que FICAM DE FORA, por classe

`criterion` (uma linha, no spec): *fica de fora todo hook que (a) bloqueia uma
chamada de ferramenta sem rota advisory, (b) exige infraestrutura de cerimônia
que `--ceremony user` não instala, ou (c) observa/reforça um rito de mantenedor
cuja metade enforcing o perfil não registra.*

| `class` | N | Hooks |
|---|---|---|
| `exige-gpg-sentinel` | 3 | `check_canonical_edit`, `check_skill_patch_sentinel`, `check_tier_policy` |
| `bloqueia-edicao` | 4 | `check_arbitration_kernel`, `check_plan_edit`, `check_adversary`, `check_scratchpad_access` (§7.12) |
| `exige-infra-ausente-no-user` | 2 | `check_pair_rail`, `check_protocol_semver_cascade` |
| `maintainer-only-por-desenho` | 9 | `check_codex_filewrite`, `check_worktree_writer`, `check_bash_canonical_forensic`, `check_skill_bootstrap_post`, `check_closeout_guard`, `check_ledger_checkpoint`, `check_compact_pinning`, `check_postcompact_reinject`, `check_precompact_continuity` |

Quatro eventos somem inteiros da saída (`PreCompact`, `PostCompact`, sobra
`Setup`/`SubagentStart`/`ConfigChange`/`PostToolUseFailure` que agora EXISTEM):
o gerador REMOVE um evento esvaziado em vez de emitir array vazio, porque array
vazio afirma «este evento está ligado a nada», que não é «este evento não está
ligado».

### 2.3 Fora dos hooks

* **`env`**: `env_exclude` fica **vazio** — o perfil user ganha as 5 chaves da
  base (`CLAUDE_CODE_SUBAGENT_MODEL`, `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`,
  `BASH_MAX_TIMEOUT_MS`, `CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR`,
  `ENABLE_TOOL_SEARCH`) e mantém as suas duas
  (`CEO_CONFIG_PROTECTION_ADVISORY`, `CEO_CONFIG_CHANGE_GUARD`). A
  classificação (§1.3) mostra que `CLAUDE_CODE_SUBAGENT_MODEL: "inherit"` é o
  valor **anti-veneno** escolhido pelo ADR-144 *sobre* apagar a chave — a
  exclusão era herança do congelamento, não decisão.
* **`model`, `squad_allowlist`, `_squad_allowlist_comment`**: copiados da base
  (uma fonte, drift impossível por construção).
* **`_model_comment`**: literal do spec (prosa de POLÍTICA do perfil).
* **`_comment`**: texto fixo do gerador, sem número nenhum, apontando para o
  spec e para o `criterion`.

## 3. Achados medidos que não estavam no briefing

### 3.1 A identidade de um hook NÃO é sempre um basename `.py`

O briefing (e a minha 1ª versão do gerador) assumiram que todo registro é
identificável pelo basename `*.py` do `command`. **É falso.** A base registra
um comando INLINE em `PostToolUse`:

```
echo '{"decision":"allow","message":"POST-AGENT: Check git diff to verify file assignment compliance. ..."}'
```

A 1ª versão era fail-CLOSED nesse caso e **recusava rodar sobre o template
real**. A cura não é afrouxar: é dar ao inline uma identidade estável e
endereçável — `inline:<12 hex de sha256(command)>` — para que possa ser
excluído se alguém quiser, e para que uma exclusão dele APODREÇA RUIDOSAMENTE
(exclusão morta ⇒ vermelho) se o texto mudar. Fail-closed continua onde a
identidade é impossível: `command` ausente ou não-string.

Consequência para a contagem: 47 = 46 `.py` (45 basenames, porque
`check_output_secrets.py` aparece 2×) + 1 inline.

### 3.2 As divergências entre `user` e `base` eram TRÊS classes, não duas

O briefing nomeava duas. Medindo campo a campo os 20 registros retidos, há
**três**:

| Registro | Campo | Estado |
|---|---|---|
| `PreToolUse/check_anti_ceo_overhead.py` | `matcher` | base = 14 ferramentas + `mcp__.*`; user = 5 |
| `PreToolUse/check_anti_ceo_overhead.py` | `_comment` de bloco | user perdeu o parágrafo PLAN-125 WS-1 que explica o matcher largo |
| `PreToolUse/check_config_protection.py` | `_comment` de bloco | reescrito para a variante advisory |
| `PreToolUse/check_config_protection.py` | `statusMessage` | `"...(advisory)..."` |
| `UserPromptSubmit/UserPromptSubmit.py` | `_comment` de bloco | acrescenta a nota do recomendador PLAN-122 |

O `_comment` congelado reconhecia só a última. Isso força a forma do spec:
`matcher_overrides` sozinho **não cobre** `_comment` de bloco nem
`statusMessage`. Ficaram duas chaves, com divisão semântica limpa:

* `matcher_overrides` — o campo COMPORTAMENTAL. Forma da classificação §3:
  objeto com `matcher` + `reason` + `evidence` (um matcher estreitado sem
  justificativa registrada é exatamente como o atual apareceu).
* `annotation_overrides` — `_comment` de bloco e campos de entrada, com
  `reason` obrigatório. **`command` é PROIBIDO ali**: overridar o comando seria
  uma segunda fonte para o roster, a classe que o gerador existe para remover.

Os cinco desvios foram **PRESERVADOS verbatim** (lidos do disco, nunca
redigitados) e agora são declarados com motivo.

### 3.3 O arquivo-irmão para o spec trip(ari)a um gate — medido, com controle

O entregável 1 pedia `templates/settings/settings.user.derivation.json`, com
instrução explícita de trocar a arquitetura se algum glob o pegasse. **Pegou.**
`.claude/scripts/check-install-profiles.py` (`:240`) exige BIJEÇÃO entre as
entradas `hook_stacks` de `scripts/profiles/profiles.json` e
`templates/settings/settings*.json` no disco:

```
CONTROLE (árvore sem o arquivo)          -> rc=0  check-install-profiles: OK
POSITIVO (settings.user.derivation.json) -> rc=1  DRIFT: settings template on disk
                                                   has no hook_stacks entry
VARIANTE (user-derivation.json)          -> rc=0  (não casa o glob settings*)
```

O nome fora do glob passaria, mas não está no FILE ASSIGNMENT; a rota
sancionada pelo briefing é embutir. O spec vive na chave `_derivation` do
próprio `settings.user.json`.

**E é a arquitetura melhor, não um consolo.** A prosa que ele substitui já
viajava para os mesmos lugares (o `_comment` congelado tem 1,2 kB e é copiado
verbatim para o `.claude/settings.json` de todo adopter `--ceremony user`); a
diferença é que agora um gate a lê. Um adopter que abra seu `settings.json` vê,
no arquivo, quais hooks de governança estão ausentes e por quê.

**Prova de não-entrega / de entrega, medida em cada consumidor:**

| Consumidor | Lê o quê | O `_derivation` chega? |
|---|---|---|
| `scripts/delivery-routes.tsv` (+ `_framework_manifest_set.sh`, `doctor.sh`, `_parity_classify.py`) | 6 rotas, domínio INERTE fixo em código: `docs/<n>.md`, `.github/CODEOWNERS[.template]`, `.github/workflows/*.template` | **não** — `templates/settings/**` não é destino de rota nenhuma |
| `scripts/install.sh` (`:2144-2146`) | copia o template para `$TARGET/.claude/settings.json` | **sim** — instalação `--ceremony user` nova carrega o spec (custo em §5) |
| `scripts/upgrade.sh` (`:2603-2712`) | só `.hooks` e `.env` | **não** — adopter existente nunca recebe a chave por upgrade |
| `scripts/build-plugin.py` (`:284`) | só `.hooks` | **não** no `hooks.json`; mas ver **FU-F-ACCEL** (§5) |
| `.claude/scripts/check-install-profiles.py` | `.hooks` dos templates declarados + bijeção por nome de arquivo | **inerte** — nenhum arquivo novo, rc=0 medido |
| `.github/workflows/validate.yml` (`:254`) | `jq empty` em `templates/settings/*.json` | **inerte** — JSON válido |
| `.claude/hooks/check_canonical_edit.py` (`:308`) | glob `templates/settings/*.json` | já era canônico; editar o spec exige cerimônia GPG — **desejável** |

Custo medido: **15.818 B → 38.178 B (+22.360 B)**. (O número subiu de
+20.061 na medição do writer para +22.360 quando a rodada 2 do pair-rail
acrescentou `blocking_inclusions` ao spec — §7.7.)

### 3.4 `top_level_keep` era a mesma classe de defeito — trocado por acordo em DUAS direções

A classificação (§3, nota) rejeitou o `top_level_keep` que o briefing pediu:
uma lista literal de chaves a manter é «a mesma classe de lista literal que a
OQ-E5 existe para matar», porque a base ganhar uma chave significa o perfil
advisory silenciosamente NÃO a receber. Mas um `top_level_exclude` puro tem o
defeito oposto — a base ganha `permissions` e o perfil advisory **herda**
(quebrando `test-install-deny-baseline.sh` perna D e
`test_template_dogfood_parity.py:398-412`).

Nenhuma das duas direções fica silenciosa:

* **droppada** ⇒ `top_level_exclude` tem de NOMEAR a chave, com `reason`
  (fail-closed no validador; exclusão morta ou sem razão ⇒ vermelho);
* **herdada** ⇒ a chave nova é copiada, os bytes gerados mudam, `--check`
  fica VERMELHO e a chave aparece no diff que um humano revisa antes do
  `--write` (e o write passa pela cerimônia canônica).

São **15** chaves de topo declaradas fora, cada uma com razão: `permissions`,
`availableModels`, `fallbackModel`, `statusLine`, `plansDirectory`,
`cleanupPeriodDays`, `attribution`, `skillOverrides`,
`skillListingBudgetFraction`, `disableSkillShellExecution`,
`_model_pin_comment` e os 4 comentários que explicam os blocos removidos.
Teste `test_every_base_top_level_key_is_carried_or_named` fecha o invariante;
`test_the_enforcing_model_keys_never_reach_the_advisory_profile` é o cinto.

### 3.5 O que o entregável 5 pedia já estava certo — e isso é medido

O briefing pedia para atualizar contagens em quatro arquivos, citando
`EXPECTED_TEMPLATE_REGISTRATIONS_USER=20`. Medido:

* `git grep EXPECTED_TEMPLATE_REGISTRATIONS` **não casa nenhum teste**. O
  literal vive só em `PLAN-169/s329-ceremony-E/EXPECTED-BASELINE.txt:182`, lido
  por `finalize-E.sh:432` e `OWNER-S329-E-LAND.sh:726` — artefatos CONGELADOS
  de uma cerimônia já landada. **Não tocados**; a wave F terá o seu próprio
  baseline, e re-rodar o material da E pós-wave falharia por desenho (nota já
  registrada na classificação §4 #22).
* `test_upgrade_lifecycle_hooks_derived.py` e
  `test-upgrade-lifecycle-hooks-derived.sh` **derivam tudo** em tempo de
  execução. Os limiares são `>= 10` e o valor real cai de 27 para **17** —
  passa com margem 7. O alvo derivado `sorted(tpl["env"])[0]` muda de
  `CEO_CONFIG_PROTECTION_ADVISORY` para `BASH_MAX_TIMEOUT_MS`; o teste continua
  válido porque é derivado (previsto na classificação §4 #7).
* `test_template_dogfood_parity.py` afirma `model` e a AUSÊNCIA de
  `availableModels`/`enforceAvailableModels` — garantido por `top_level_exclude`.
* `test-install-deny-baseline.sh` perna `[D]` exige que o template **não**
  traga bloco `permissions` — garantido pelo mesmo mecanismo.

Nenhum dos quatro precisou de edição, verificado por **execução**: E unit
88/88, dogfood 14/14, e2e abaixo.

### 3.6 A mudança de roster torna uma invariante nova load-bearing — medida

Pela primeira vez o perfil advisory registra hooks que antes eram apenas
COPIADOS, nunca wired. Se algum dos 10 não chegasse ao disco do adopter, a
registração apontaria para nada. Medido: `install_hooks_selective`
(`scripts/install.sh:1413`) copia **todo** `.claude/hooks/*.py` e `*.sh` de
topo, **sem nenhum ramo por cerimônia** — o arquivo existir no repo é
exatamente a condição para chegar ao adopter. Os 10 existem (verificado um a
um). Guardado por `test_every_registered_hook_has_a_file_install_will_copy`,
que é a pergunta do ADOPTER («esta registração resolve?»), distinta da bijeção
manifesto↔disco que `check-install-profiles.py` faz.

## 4. Testes

### unit (pytest) — `.claude/scripts/tests/test_gen_settings_user_template.py`

```
python3 -m pytest .claude/scripts/tests/test_gen_settings_user_template.py -q
61 passed, 2 skipped
```

Os 2 skips são honestos e nomeados: `test_no_match_statement` (o python3 local
**É 3.9**, então `ast.Match` não existe — o piso do repo está sendo exercitado
de verdade) e `test_pending_entries_point_at_an_open_question` (o balde
`exclude_hooks_pending` está VAZIO agora que a classificação decidiu os 17; o
mecanismo permanece para a próxima não-decisão).

Sete classes:

* `ShippedTemplateMatchesItsDerivation` — paridade em BYTES (um `--check`
  estrutural ficaria verde sobre um arquivo reformatado à mão), idempotência,
  drift nomeado com o comando de remediação, `--check` como default.
* `ShippedSpecIsInternallyConsistent` — exclusões apontam para registro vivo;
  `class` no vocabulário; `reason`/`evidence` não-vazios; **`evidence` RESOLVE**
  (o 1º token tem de ser `.claude/hooks/<o próprio hook>` e existir em disco);
  sem duplicatas; `provisional` casa com o balde; toda chave de topo da base
  carregada ou nomeada; as chaves enforcing nunca vazam; `criterion` presente e
  apontado pelo `_comment`; e o invariante-mãe
  `test_the_two_buckets_cover_every_base_only_registration`.
* `FrozenCopyFailsItsOwnClaim` — o **CONTROLE VERMELHO** (abaixo).
* `DerivationMechanics` — base sintética: hook novo não-excluído ⇒ `--check`
  vermelho nomeando-o; `model` segue a base; dupla registração nas 3 direções;
  evento esvaziado some; bloco parcialmente esvaziado mantém sobreviventes;
  entradas retidas byte-idênticas salvo override declarado; `env`; identidade
  do hook inline.
* `SpecIntegrityIsFailClosed` — 20 arms de rejeição, incluindo o `top_level_keep`
  **recusado por nome** para a forma rejeitada não voltar, e a fronteira
  INFRA/DRIFT: artefato ausente é **rc 2**, nunca rc 1.
* `PluginAccelOverlapIsDeclaredDebt` — a dívida FU-F-ACCEL (§5), com anti-rot.
* `GeneratorRuntimeContract` — compila; imports só de stdlib; `from __future__`;
  sem `match`; sem `|` de união em runtime.

### CONTROLE VERMELHO — a cópia congelada contra a própria afirmação

`fixtures/settings.user.pre-F.json` é
`git show 1c34eb5:templates/settings/settings.user.json` (15.818 B, 20
registros, sem `_derivation`). O teste toma o `_comment` congelado ao pé da
letra — spec com **os 10 que ele mesmo listou**, sem overrides («byte-idênticas
nos campos comportamentais») — e mostra que isso **não reproduz** o arquivo
congelado:

```
registrações que a cópia congelada NÃO tinha: 17
   ConfigChange check_config_change.py          PreToolUse check_pair_rail.py
   PostCompact check_postcompact_reinject.py    PreToolUse check_worktree_writer.py
   PostToolUse accel_dispatch.py                SessionStart check_compact_pinning.py
   PostToolUseFailure check_output_secrets.py   SessionStart turbo_sessionstart.py
   PreCompact check_precompact_continuity.py    Setup check_setup_verification.py
   PreToolUse check_adversary.py                Stop check_closeout_guard.py
   PreToolUse check_codex_filewrite.py          Stop codex_review_user_code.py
   PreToolUse check_ledger_checkpoint.py        Stop review_loop.py
                                                SubagentStart check_subagent_start.py

campos divergentes: PreToolUse check_anti_ceo_overhead.py: matcher
                    PreToolUse check_config_protection.py: statusMessage
```

Asserções sobre a MENSAGEM, não só sobre a desigualdade: o relatório tem de
nomear `PreToolUse check_ledger_checkpoint.py`, `PostToolUseFailure
check_output_secrets.py`, o matcher e o `statusMessage`; e a contagem tem de
bater com o censo (17, declarado com fonte). A lista dos 10 é um literal
**deliberado** — é uma CITAÇÃO de um artefato histórico, não um roster que este
arquivo mantém; se o spec entregue divergir dela, é a wave funcionando.

Fecha com dois invariantes de direção:
`test_the_shipped_roster_loses_nothing_the_frozen_copy_had` (a única direção
que seria REGRESSÃO para um adopter) e
`test_what_the_shipped_roster_gained_is_exactly_what_was_ruled_in` (o veredito
de §2.1 — 9 registrações após a reversão de §7.12 — declarado com fonte).

### CONTROLE POSITIVO ao vivo, no artefato real

Plantei `CEO_QUIET_MODE: "1" -> "0"` no template do checkout e rodei a suíte:

```
PLANT  -> 5 failed, 45 passed, 1 skipped
          test_check_mode_is_green_on_the_shipped_tree
          test_default_mode_is_check
          test_generated_bytes_equal_the_shipped_bytes
          test_the_shipped_spec_does_reproduce_the_frozen_roster   (versão provisional)
          test_env_is_base_minus_exclusions_plus_overrides
RESTORE (gen --write) -> verde
```

### Suítes vizinhas (nenhuma editada)

```
.claude/scripts/tests/test_upgrade_lifecycle_hooks_derived.py   88 passed   (E unit 88 -> 88)
.claude/hooks/tests/test_template_dogfood_parity.py             14 passed
python3 .claude/scripts/check-install-profiles.py               rc=0
scripts/tests/test-upgrade-lifecycle-hooks-derived.sh           69 passed, 0 failed  (E e2e)
python3 -m pytest .claude/scripts/tests/  (varredura completa)  5748 passed, 1 FAILED, 26 skipped, 1 xfailed (17min20)
```

A única vermelha é `test_install_user_skips_governance_hooks.py` — **§4b**,
fora do FILE ASSIGNMENT. Ela só apareceu porque rodei o diretório INTEIRO;
nenhuma das suítes que o briefing e a classificação nomeiam a cobre.

**Nota sobre o e2e — por que 69 e não os 71 do briefing.** Rodado DUAS vezes:
uma no estado provisional (roster 20) e outra no estado pós-reconciliação
(roster 30; o final, pós-§7.12, é 29). **As duas
deram 69 passed / 0 failed**, o que é evidência direta de que a mudança de
roster não moveu nada no e2e. O delta contra 71 é **independente do patch**:
`E.3` e `E.9` replicam o upgrader PRÉ-CURA a partir de `git show HEAD:...` e,
com HEAD (`1c34eb5`) já além da cura do pacote E (`5930974`), os dois controles
vermelhos **expiram** e degradam para um SKIP NOMEADO (`E.3-SKIP`,
`E.9-SKIP`) em vez de emitirem os seus `ok` individuais. Nenhum dos dois lê
algo que este patch toca.

**Dois casos derivados passaram a exercitar as chaves NOVAS, sozinhos** — a
prova de que os oráculos vizinhos são derivados de verdade:

```
ok  E.14j env.CEO_CONFIG_CHANGE_GUARD=1 came back WITH the hooks
ok  E.15d the SHARED setting env.BASH_MAX_TIMEOUT_MS=600000 was restored
ok  E.15e the USER-ONLY setting env.CEO_CONFIG_CHANGE_GUARD was NOT applied
```

`E.14j`/`E.15e` derivam a chave «só-do-user» por subtração e, com
`env_exclude` vazio, ela deixou de ser `CEO_CONFIG_PROTECTION_ADVISORY` e
passou a ser `CEO_CONFIG_CHANGE_GUARD`; `E.15d` derivou uma chave COMPARTILHADA
que antes não existia. Nenhuma linha foi editada nesses arquivos.

### Gates de corpus (rodados DEPOIS da última edição, sobre o staged)

Ordem do CLAUDE.md §4: `git add` com paths EXPLÍCITOS → gates sobre a árvore
staged → (sem commit; o finalize deriva o patch).

```
python3 .claude/scripts/check-test-env-hygiene.py      rc=0   337 flagged, all allowlisted
python3 .claude/scripts/check-staleness.py             rc=0   9 findings, TODAS pré-existentes
python3 .claude/scripts/check-installer-write-safety.py rc=0  baseline intacto (nada em scripts/)
python3 .claude/scripts/check-install-profiles.py      rc=0   bijeção OK (nenhum arquivo novo em templates/settings/)
bash .claude/scripts/local/verify-counts.sh            rc=0   test_files 811 -> 812, tests 15396, sem drift
python3 -m py_compile <gerador> <teste>                rc=0
jq empty templates/settings/*.json                     rc=0   (5 templates)
```

As 9 do `check-staleness` são **pré-existentes**, provado por controle:
`git stash --include-untracked` → re-rodar → **9**; `git stash pop` → **9**.
Nenhuma cita algo que este patch toca (a entrada `PLAN-169` é
`plan_executing_stalled`, sobre o arquivo do plano, não sobre a wave).

O ratchet `installer-write-safety` **não** precisou de regeneração: o patch não
toca nenhum arquivo em `scripts/` (`git status --porcelain` = 5 paths, todos em
`.claude/` e `templates/`).

Higiene do artefato gerado: 35.879 B, termina com exatamente um `\n`, sem CR,
sem BOM, UTF-8 válido.

## 4b. BLOQUEADOR — o 26º sítio, achado por varredura, FORA do FILE ASSIGNMENT

**`.claude/scripts/tests/test_install_user_skips_governance_hooks.py` fica
VERMELHO com este patch, e eu não posso consertá-lo.**

Ele não está no mapa de 25 sítios da classificação (§4) nem no FILE ASSIGNMENT
desta wave. Foi achado rodando a suíte INTEIRA de `.claude/scripts/tests/`
(5.748 passed, 1 failed, 17 min) — não por leitura.

O que ele é: uma **segunda cópia congelada da mesma afirmação que a wave
refuta**. A tupla `_GOVERNANCE_HOOKS` (`:57-68`) é literalmente a lista de 10
do `_comment` congelado, e o teste afirma que nenhum deles é registrado sob
`--ceremony user`. A classificação S330 §2 tirou **dois** daquela lista por
mérito medido:

* `check_scratchpad_access.py` — não bloqueia edição (bloqueia só
  `scratchpad.py --plan X` divergente), zero `CEO_*`, zero sentinel, e guarda
  uma ferramenta que o perfil user **recebe**;
* `check_skill_reference_read.py` — observer, zero sítios de `block`, e a
  metade EMISSORA (`check_agent_spawn.py`) já está no perfil user.

Falha medida (para no primeiro):

```
AssertionError: 'check_scratchpad_access.py' unexpectedly found in ...
  : governance hook check_scratchpad_access should NOT be registered for user
```

**Evidência POSITIVA que vem junto:** esse teste faz um `install --ceremony
user` REAL, e o install **passou** (`returncode == 0`), produzindo um
`settings.json` com exatamente **30 registros** na medição da época
(pré-§7.12; o mesmo install hoje produz 29) — os 20 antigos mais os 10 da
§2.1, incluindo a 2ª registração de `check_output_secrets.py` e o `echo`
inline. É a prova de campo de que o template gerado instala.

**Cura (uma edição, para quem tiver o path no assignment):** trocar a lista
literal por uma derivada do próprio spec — a mesma cura que a wave aplica ao
template:

```python
import json, os
_USER_TPL = os.path.join(_REPO_ROOT, "templates", "settings", "settings.user.json")
with open(_USER_TPL, encoding="utf-8") as fh:
    _SPEC = json.load(fh)["_derivation"]
_GOVERNANCE_HOOKS = tuple(
    e["name"][:-3] for e in _SPEC["exclude_hooks"]
)          # .py stripped, because the assertions append ".py"
```

`_KEEP_HOOKS` fica como está (é uma asserção POSITIVA sobre 4 hooks que
continuam registrados, e os 4 continuam). Com isso o oráculo passa a seguir o
spec e vira vermelho quando o spec e o template divergirem — que é a pergunta
que ele deveria estar fazendo.

Enquanto isso não acontecer, **o pacote não pode landar**: a suíte fica 1
vermelha. Não reverti as duas inclusões para «ficar verde» porque isso
desfaria, em silêncio, um veredito medido que é decisão do Owner.

## 5. Questões abertas e follow-ups

> **STATUS S331 (2026-08-30).** As cinco questões abaixo foram decididas pelo
> Owner e as decisões estão EXECUTADAS neste mesmo patch — leia o §7 antes de
> agir sobre qualquer bullet desta seção. Resumo: **FU-F-ACCEL CURADO** (a
> tabela paralela não existe mais; o marcador de dívida virou guard permanente),
> **OQ-F1 congelada** por decisão, **OQ-F3 wired** no `validate.yml`, **OQ-F2 /
> OQ-F4 / OQ-F5 mantidas como estão** (as recomendações do writer foram
> ratificadas sem alteração), e a decisão de ADR saiu **novo (ADR-197), não
> AMEND**, pela recomendação medida da §6 da classificação.

* **FU-F-ACCEL (o único que a classificação marcou como «mesmo patch», e que
  este pacote NÃO pode fechar).** `scripts/build-plugin.py` monta o
  `hooks.json` do plugin a partir do `.hooks` do template user (`:284`) e
  **depois** estende com a sua própria tabela `ACCEL` (`:44-66`). Antes da wave
  F esses 4 hooks estavam fora do template, então `ACCEL` era a única fonte.
  Agora o template registra os quatro — `accel_dispatch.py`,
  `codex_review_user_code.py`, `review_loop.py`, `turbo_sessionstart.py` — e o
  build emite cada um **duas vezes**, com timeouts divergentes (`review_loop.py`
  60 vs 15 do template; `turbo_sessionstart.py` 10 vs 5).
  `scripts/build-plugin.py` está **fora do FILE ASSIGNMENT** desta wave, então
  a reconciliação é do Owner/da cerimônia. O que landa aqui é o **tripwire**:
  `PluginAccelOverlapIsDeclaredDebt` afirma que a sobreposição é EXATAMENTE
  esses 4 nomes — vermelho se alguém reconciliar o `ACCEL` (aí a lista encolhe
  para vazio e o teste passa a exigir vazio) e vermelho se alguém alargar a
  sobreposição. Verde-agora, vermelho-na-mudança, **nas duas direções**, e
  jamais um passe silencioso. Doutrina:
  [[feedback-widen-guard-then-declare-debt]] — cura bloqueada ⇒ declarar a
  dívida por path com anti-rot, nunca deixar o guard falso-verde nem landar um
  teste sabidamente vermelho.
* **OQ-F1 — `EXPECTED_TEMPLATE_REGISTRATIONS_USER=20`** em
  `s329-ceremony-E/EXPECTED-BASELINE.txt:182` fica DEFASADO (o valor real passa
  a ser 30). É baseline congelada de cerimônia já landada; re-rodar
  `finalize-E.sh` / `OWNER-S329-E-LAND.sh` pós-wave falha por desenho. Decisão:
  deixar congelado (histórico) ou atualizar conscientemente com fonte. Não
  toquei.
* **OQ-F2 — o matcher estreito de `check_anti_ceo_overhead.py`.** A
  classificação recomenda **MANTER, mas DECLARADO** (escolha de latência: 5
  ferramentas em vez de 14 cold-starts; hook fail-OPEN, budget ≤20/dia).
  Implementado como `matcher_overrides` com `reason` + `evidence`. Se o Owner
  preferir o matcher largo, apague a entrada e rode `--write`.
* **OQ-F3 — o gate no CI.** O `--check` não está wired em workflow nenhum
  (`.github/` está fora do FILE ASSIGNMENT). A cobertura existe porque
  `.claude/scripts/tests/` É coletado pelo CI; um step dedicado em
  `validate.yml`, ao lado do idempotency check do `generate-skill-inventory.sh`,
  daria mensagem melhor.
* **OQ-F4 — +22.360 B no `settings.json` de todo adopter `--ceremony user`
  novo.** Declarado, não escondido. Encurtar `reason`/`evidence` é a rota se
  for demais (removê-los, não: são o que torna a subtração auditável).
* **OQ-F5 — riscos de INCLUIR**, já enumerados na classificação §5, ficam com o
  Owner. Os dois que valem repetir: `check_config_change.py` entra com
  `CEO_CONFIG_CHANGE_GUARD=1` **explícito** (o default vive em código, e a
  lição do rail round 7 do pacote E é que «uma registração é só tão advisory
  quanto a setting que ela lê»); e `codex_review_user_code.py` é DETECT-ONLY
  por default, nunca roda Codex sem opt-in.
* **Fora de escopo, mesma classe (classificação §4 #16/#17):**
  `settings.base.json:617` afirma «45 registrations» (são 47) e o `_comment` da
  base afirma «~16+» hooks (são 46 distintos). Ponteiro morto: o `_comment` do
  user citava `PLAN-122 WS-4`, que **não existe em nenhum ref git** — removido
  pela regeneração.

## 6. Limites declarados desta wave

* Não toquei `scripts/install.sh`, `scripts/upgrade.sh`, `scripts/build-plugin.py`,
  `.claude/settings.json`, `templates/settings/settings.base.json`, `CLAUDE.md`,
  `SPEC/`, `.claude/adr/`, `PROTOCOL.md` — nada em `scripts/`, portanto o
  baseline do ratchet `installer-write-safety` não precisa ser regenerado
  (verificado por `git status` e por execução do próprio ratchet).
* `templates/settings/settings.user.derivation.json` **não foi criado** (§3.3),
  apesar de constar do FILE ASSIGNMENT: criá-lo deixa `check-install-profiles.py`
  vermelho, medido com controle positivo.
* O gerador lê o spec do artefato que ele mesmo escreve. Circular por desenho
  (auto-descritivo), com duas saídas: `--spec <path>` para bootstrap e rc 2
  fail-loud se o arquivo sumir ou perder a chave — nunca um default silencioso.
* TOCTOU entre `--check` e um editor concorrente não é tratado; o gate é de CI
  e de pre-commit, não um lock.
* A wave MUDA a superfície de hooks do adopter `--ceremony user` (20 → 30).
  Isso é o ponto da OQ-E5, não um efeito colateral — mas significa que o
  próximo `upgrade.sh` de um adopter user **registra 10 hooks novos**. Os
  riscos por hook estão na classificação §5.
---

## 7. Reconciliação S331 — o que o Owner decidiu e o que foi executado

Sessão S331 (2026-08-30), night-run autônoma. O Owner ratificou quatro decisões
antes de sair e pediu o pacote pronto para assinatura. Todas estão executadas na
sombra e verificadas; nada aqui espera uma segunda rodada de decisão.

### 7.1 As quatro decisões (verbatim das opções escolhidas)

1. **Escopo** — «Só a wave F, até a assinatura». Nenhum segundo pacote; a
   classe de defeito que isso evita é a da S328, onde o land de um pacote
   invalidou o BASELINE do outro duas vezes.
2. **FU-F-ACCEL** — «Reconciliar no MESMO patch».
3. **OQ-F1 / OQ-F3** — «Congelar F1 + incluir o step F3».
4. **ADR** — «Decida pela §6 do DESIGN-F». A §6 da *classificação*
   (`hook-classification-S330.md`, não a §6 deste arquivo) recomenda **ADR
   NOVO, não AMEND**, com o argumento de que um AMEND exige um ADR-pai que
   decida a coisa emendada e **nenhum existe** — medido: o único ADR que
   menciona `--ceremony user` é o ADR-155-AMEND-1, e apenas para dizer o que o
   install pula. Executado: **ADR-197**, com os cinco pontos que a §6 pede.

### 7.2 FU-F-ACCEL — o que mudou, e por que a divergência não era deliberada

O bullet da §5 dizia que a reconciliação era do Owner porque
`scripts/build-plugin.py` estava fora do FILE ASSIGNMENT. Ele entrou no escopo
por decisão, e a medição que a decisão destravou resolve a única ambiguidade
que restava — **qual timeout é o certo**:

| hook | ACCEL (build-plugin) | `settings.base.json` | `.claude/settings.json` **vivo** |
|---|---|---|---|
| `accel_dispatch.py` | 20 | 20 | — |
| `codex_review_user_code.py` | 130 | 130 | — |
| `review_loop.py` | **60** | **15** | **15** |
| `turbo_sessionstart.py` | **10** | **5** | **5** |

Duas fontes contra uma: os `60`/`10` do `ACCEL` eram uma **terceira cópia
defasada**, não uma escolha do plugin. `git log -L` mostra que a tabela nasceu
em `9777a8d` e nunca foi tocada desde.

O que landa:

* `ACCEL` **deixa de existir**. A composição virou função pura
  `compose_plugin_hooks(template_path)` — lê um arquivo, devolve um dict, não
  escreve nada — mais `_rewrite_hook_paths` e `dump_manifest_hooks`. Só
  `.hooks` viaja: `env` e a chave `_derivation` (~20 KB) ficam fora do plugin
  por construção, e isso é asserido.
* O marcador de dívida foi **INVERTIDO em guard permanente**, não removido:
  `PluginAccelOverlapIsDeclaredDebt` → `PluginHooksHaveNoParallelSource`, 7
  testes. O guard é deliberadamente mais largo que `ACCEL`: recusa **qualquer**
  assignment module-level cujos literais nomeiem um hook que o template já
  registra — uma tabela que volte com outro nome é o mesmo defeito.
* **Controle positivo** replantando a tabela e o extend pré-cura: **3 dos 7
  ficam vermelhos**, nomeando o ofensor
  (`{'ACCEL': ['accel_dispatch.py', 'codex_review_user_code.py',
  'review_loop.py', 'turbo_sessionstart.py']}`), a duplicata de
  `(evento, matcher, comando)`, e a contagem `2` onde deve ser `1`. Restaurado
  por backup, 7/7 verde, sem resíduo.
* Medição do entregável: o `hooks.json` composto tem **30 registrações e ZERO
  duplicatas exatas de triplo** (antes da cura os quatro apareciam 2× cada).
  As repetições de basename que sobram são registrações legítimas em eventos
  distintos (`check_output_secrets.py` em `PostToolUse` e
  `PostToolUseFailure`).
* **Consequência de produto, declarada:** o plugin passa a rodar
  `review_loop.py` com 15 s e `turbo_sessionstart.py` com 5 s. É mudança de
  comportamento real — registrada no ADR-197 §Consequences.

### 7.3 OQ-F3 — o step, e o que ele custa

`validate.yml` ganha o step `User-template derivation (PLAN-169 F — regen+diff)`,
ao lado dos dois steps de idempotência de gerador que já existiam (skill
inventory, plugin manifest) — a vizinhança que a própria OQ-F3 nomeia.
Contrato de saída: **0** in-sync / **1** drift / **2** input inutilizável, ANY
non-zero reprova. Medido nos dois sentidos: rc 0 no artefato commitado, rc 1
com diff unificado sob **um único byte** alterado (`"timeout": 15` → `16`),
restaurado em seguida. `actionlint` limpo.

`.github/workflows/validate.yml` é **canônico** (oráculo `--is-canonical` = 1),
então entra no Scope do sentinel. `scripts/build-plugin.py` **não** é canônico
nem membro do manifesto ADR-192 — entra no patch, fora do Scope.

### 7.4 O que a reconciliação encontrou de carona (declarado, não escondido)

* **FU-F-ADRGATE (novo).** `check-adr-chain.py` e `generate-adr-index.py`
  **não rodam em CI nem em `validate-governance.sh`** — grep em
  `.github/workflows/` e no script: zero. Consequências medidas: o índice de
  `.claude/adr/README.md` estava congelado em **170 ADRs** com **198** no
  disco (28 ADRs entraram sem regeneração), e `check-adr-chain.py` sai **rc 1
  com 11 erros no main** (5 ADRs sem campo `Status:`, 2 `Supersedes` apontando
  para um ADR que continua `ACCEPTED`). **Delta medido: o ADR-197 não
  acrescenta nenhum erro** — a saída normalizada da sombra é idêntica à do
  main. É a forma «instrumento verde cuja pergunta envelheceu», e a cura (wirar
  os dois no `validate.yml` e limpar os 11) é wave própria, não esta.
* **A regeneração do índice traz 27 linhas que não são desta wave.** Regenerei
  porque docs GERADOS entram na bateria de todo land, e porque deixá-lo stale
  seria escolher não corrigir um artefato que este patch torna mais stale. O
  arquivo é canônico e o Scope o cobre. Declarado aqui para que o revisor não
  procure a wave que criou os 27.
* **Contagens de ADR: 15 sítios, 9 arquivos** (`README.md`, `README.pt-BR.md`,
  `docs/{ARCHITECTURE,README,CTO-GUIDE,GUIA-COMPLETO,FAQ}.md`, `npm/README.md`,
  `CHANGELOG.md`), todos não-canônicos. A remediação foi escrita para casar só
  em linhas que mencionam ADRs e nunca dentro do identificador `ADR-197`; o
  dry-run encontrou **exatamente as 15** que o `verify-counts.sh` aponta, sem
  falso-positivo.
* **`CLAUDE.md` carrega o numeral `198`, e só isso.** `check-claude-md-claims.py`
  **roda no `validate.yml`** (linha 73), então um patch que adiciona um ADR sem
  esse byte nasce com o CI vermelho — a disciplina de cache do Gate-1 é sobre
  não reescrever prosa mid-sessão, não sobre deixar um gate reprovando. A
  narrativa da §5 do `CLAUDE.md` continua sendo trabalho de closeout.
  Verificado: `check-claude-md-claims.py` rc 0, `verify-counts.sh` rc 0,
  arquivo em 37.620 B (teto 40.000).
* **Ratchet `installer-write-safety`: rc 0 sem regeneração de baseline.** A
  regra do `CLAUDE.md` («qualquer wave que toque `scripts/` regenera o
  baseline») não dispara aqui porque o censo varre `.sh` e `build-plugin.py` é
  Python — medido, `build-plugin` tem zero entradas no baseline.

### 7.5 O que o §6 (limites) passa a dizer

O §6 afirma que a wave não toca `scripts/`, `.github/` nem `.claude/adr/`.
**Isso era verdade do snapshot do writer e deixou de ser** com as decisões do
Owner: o patch agora toca `scripts/build-plugin.py`, `.github/workflows/validate.yml`,
`.claude/adr/` (ADR-197 + índice) e os 9 arquivos de contagem. O restante do §6
continua valendo — em particular a razão medida para o spec viver na chave
`_derivation` em vez de um arquivo-irmão, e o TOCTOU não tratado.

### 7.6 Pair-rail sobre esta sombra

**Rodada 1 — 2 achados P2, ambos REAIS e ambos curados.** O revisor
(`codex exec review --uncommitted`, gpt-5.6-sol, esforço xhigh) não encontrou
defeito no que a wave entrega; encontrou defeito **na própria cura** — e da
mesma classe que a wave existe para remover: *uma declaração no spec que o
gerador ignora em silêncio*.

* **P2-1 — override de escopo de BLOCO num bloco de várias entradas.**
  `matcher` e o `_comment` de grupo são propriedades do BLOCO, e `derive_hooks`
  só os escreve quando o bloco se estreita a UMA entrada retida
  (`if len(kept_entries) == 1`). A checagem de ambiguidade do validador conta
  REGISTRAÇÕES que casam o NOME entre eventos — outra pergunta —, então uma
  chave legitimamente qualificada (`Evento/nome`) apontando para um bloco de
  duas entradas **passava na validação e era descartada depois**. O `--check`
  abençoaria uma saída cujo spec embutido afirma um override que nenhum byte
  reflete.
  **Cura:** fail-CLOSED no validador, com um helper que responde a pergunta
  certa (`_retained_in_block`: quantas entradas do bloco sobrevivem). O
  override é REJEITADO por nome, com a rota de reparo na mensagem.
  **Não é recusa cega:** anotações de ENTRADA (`hook: {...}`) continuam
  aceitas, porque a derivação as aplica sempre — e há controle positivo
  provando que, quando o bloco se estreita a uma entrada, o override é aceito
  **e escrito de fato**.

* **P2-2 — exceção sem justificativa, e exceção que não muda nada.**
  `annotation_overrides` aceitava uma entrada sem `reason` (contra o contrato
  que o §3 deste documento declara) e uma entrada só-com-`reason`, que não
  altera byte nenhum. As duas passavam por todos os gates enquanto afirmavam
  que uma exceção existe.
  **Cura:** `reason` não-vazio obrigatório, e a entrada tem de mudar alguma
  coisa (`_comment` ou `hook` não-vazio). Mesma disciplina que `exclude_hooks`
  e `matcher_overrides` já tinham.

O revisor levou os dois achados até o controle executável: rodou
`validate_spec` com `{'_comment': 'changed'}` e `{'reason': 'r'}` e mostrou
`accepted` nos dois. Depois da cura, os mesmos dois entram como `REJECTED` com
mensagem nomeada, e o caso legítimo (`_comment` + `reason`) segue aceito.

**Guard permanente:** `DeclaredOverridesAreAppliedOrRejected`, 7 testes.
**Controle vermelho** restaurando o validador pré-cura a partir do index:
**4 dos 7 ficam vermelhos** — exatamente os quatro que afirmam as rejeições
novas; os três controles positivos passam nos dois estados, que é o que torna
o guard discriminante em vez de uma recusa geral.

Suíte da cerimônia: **218 → 225** (o arquivo nuclear, 66 → 73). Paridade do
template intocada (`--check` rc 0 antes e depois), porque nenhuma das curas
muda o que a derivação PRODUZ — só o que ela ACEITA declarar.

### 7.7 Pair-rail rodada 2 — 1 P1 por construção, 3 P2 reais

Rodada sobre a árvore curada da rodada 1. O P1 (**«add the required signed
sentinel before landing»**) é **por construção**: a sombra É o estado pré-SIGN,
e o `.asc` nasce na cerimônia do Owner. Mesma disposição das rodadas 2, 3, 7 e
11 do pacote E.

Os três P2 eram reais, e os três foram curados.

**P2-a — seletores que se sombreiam.** `derive_hooks` resolve um override
preferindo `Evento/nome` sobre o `nome` nu. Um spec que declarasse **os dois**
tinha a entrada nua aplicada nunca e recusada nunca: cada uma passava a
validação por conta própria, e o defeito vivia só na RELAÇÃO entre elas. Cura:
uma checagem única antes do laço por chave — declarar ambos é recusado por nome.

**P2-b — campos gerados perdidos com a âncora.** `_derivation` entra depois de
`_comment`, `_model_comment` antes de `model`. Excluir a âncora levava o campo
gerado junto, e **perder `_derivation` é irrecuperável no caminho normal**: o
artefato deixa de carregar o próprio spec e o `--check` seguinte sai rc 2.

A primeira forma da cura REJEITAVA uma base sem a âncora — e **quebrou 18
testes** cujas bases sintéticas legitimamente não têm `_comment`. Over-correction
medida, e a arquitetura foi trocada pela outra rota que o próprio revisor
ofereceu: **`generate` passa a emitir todo campo gerado de qualquer jeito**
(anexado, em ordem determinística, quando a âncora falta) e o validador recusa
apenas o que o SPEC remove — que é decisão de operador. Recusar menos, não
perder nada.

Achado colateral da correção: **`_comment` já era protegido** por uma camada
mais antiga (é generator-sourced, e `top_level_exclude` sempre o recusou). A
checagem de âncora ganha o seu lugar na OUTRA âncora, `model`, que é chave
simples da base e nada mais protegia. O teste diz qual camada pega qual caso, em
vez de fingir que há uma só.

**P2-c — o critério não batia com a própria lista.** O `criterion` shipado dizia
que fica de fora todo hook que «bloqueia uma chamada de ferramenta sem rota
advisory»; `check_scratchpad_access.py` está DENTRO e bloqueia um comando, sem
kill-switch. O veredito veio do critério ANTIGO («bloqueia edição ou exige
GPG/sentinel»), que a própria classificação substituiu depois de medi-lo FALSO
para 5 dos 10 — o critério novo foi escrito, a lista foi mantida, e ninguém
re-derivou uma contra a outra.

O censo que se seguiu mediu duas coisas que mudam o desenho da cura:

* **dez** dos 29 hooks retidos têm sítio de bloqueio, e quase todos precedem
  esta wave (`check_bash_safety`, `check_agent_spawn`, …). Logo o critério
  **nunca descreveu o perfil** — ele descreve a decisão de EXCLUIR, aplicada aos
  26 candidatos. Lido como bicondicional é falso, e foi assim que o revisor o
  leu, com razão;
* **cinco** dos nove hooks que a wave ACRESCENTA podem bloquear, não um. Curar
  só o que o revisor nomeou teria reproduzido o defeito em escala menor.

Cura em duas partes: o `criterion` passa a declarar o próprio escopo, e
`blocking_inclusions` nomeia os cinco com a rota real do adopter
(`CEO_TURBO=0`; `CEO_CONFIG_CHANGE_GUARD=0`; rodar sem `--plan`; não setar
`CEO_CODEX_USER_REVIEW_BLOCK=1`; não setar `CEO_REVIEW_LOOP=1`). O validador
recusa entrada sem rota, sem evidência, morta, duplicada ou sobre hook excluído.

**O guard que sobrevive à wave** é o de COMPLETUDE: ele re-deriva o conjunto do
roster ANTIGO (a fixture congelada) contra as fontes dos hooks, em vez de
comparar com uma lista lembrada. Uma inclusão bloqueante futura fica vermelha
com o nome na mensagem.

**Verificação.** 14 testes novos (5 + 9). Controle vermelho em duas pernas:
remover uma entrada de `blocking_inclusions` ⇒ 2 vermelhos, um deles nomeando
`check_scratchpad_access.py`; remover as três validações do gerador ⇒ **9 de 14
vermelhos**, com os 5 controles positivos passando nos dois estados. Suíte da
cerimônia **225 → 239**; arquivo nuclear **73 → 87**. Paridade rc 0 o tempo todo.

**Custo revisado:** o template vai a **38.178 B** (+22.360 sobre o HEAD, não os
+20.061 que o writer mediu antes de `blocking_inclusions` existir).

### 7.8 Pair-rail rodada 3 — vocabulários fechados, e a rota de escrita que a wave abriu

1 P1 + 4 P2, os cinco reais. Detalhe por achado em `rail-round-3.md`; o que fica
no desenho:

**O P1 separa o que é da wave do que a precede.** `check_canonical_edit` é
registrado para `Edit|Write|MultiEdit` e **não para `Bash`**, então qualquer
gerador chamado do shell que escreva num path canônico passa fora dele —
`generate-adr-index.py --write` reescreve o canônico `.claude/adr/README.md`
assim, e `build-plugin.py --write-manifests` também. Curar um de três seria
teatro. O que ESTA wave introduziu é o `--spec <path>`: uma rota para um
documento não-revisado, fora da árvore, dirigir essa escrita. Só ela fecha
(`--write` recusa spec de fora do repositório, **rc 1** = política, nunca rc 2 =
INFRA; `--check` com spec externo segue permitido). O resto fica declarado.

**Três vocabulários passam a ser fechados** — top-level do spec (16 chaves),
campos de anotação (`statusMessage`, `_comment`) e a proibição de sobreposição
nua↔qualificada nas exclusões. Os três fechavam a mesma porta: uma declaração
aceita que a derivação depois ignora.

**O oráculo de install passou a preservar o evento.** Ele achatava toda exclusão
a um basename e afirmava ausência em TODO comando instalado; para uma exclusão
qualificada por evento — que o gerador honra mantendo a outra registração — a
afirmação é falsa. Latente hoje (0 exclusões qualificadas no spec vivo), e é
justamente por isso que foi curado agora: o ramo que nada exercita é o que
quebra no dia em que alguém o usa. O parsing virou função pura para que um spec
sintético alcance esse ramo.

**O incidente que vale mais que os cinco achados.** A primeira versão do teste
de `--write` rodava contra o repositório REAL — segura *apenas porque a cura que
ela testa estava presente*. Quando o controle vermelho removeu a cura, a escrita
passou e **reescreveu o `settings.user.json` shipado** com o spec mínimo do
teste (47 registros, `criterion` = "test fixture criterion"), e o `--check`
ficou **rc 0**, porque o arquivo batia com o spec falso que ele mesmo passou a
carregar — um verde perfeito sobre um artefato destruído.

Recuperado do `F-wip.patch`, curas de spec re-aplicadas, verificado byte a byte.
A cura é estrutural: os casos de `--write` rodam em árvore SINTÉTICA, com spec
deliberadamente fora dela, mais um controle positivo (spec dentro ⇒ escreve) e a
asserção de que o destino **não existe** após a recusa. O controle vermelho foi
refeito comparando o sha256 do template antes e depois: byte-idêntico.

> **Regra:** um teste cuja segurança depende do código que ele testa não é um
> teste. Todo caso que invoque um caminho de ESCRITA roda em árvore descartável.

Bateria **239 → 252**; arquivo nuclear **87 → 98**.

### 7.9 Pair-rail rodada 4 — proveniência, e uma over-correction minha

1 P1 + 2 P2. Registro em `rail-round-4.md`; o que fica no desenho:

**O P1 corrigiu a PERGUNTA da cura anterior.** A rodada 3 confinou o `--spec`
do `--write` ao repositório. A rodada 4 mostrou que *estar dentro do
repositório não é proveniência*: um `spec.json` **untracked** escrito em
qualquer lugar da árvore passava — e um arquivo untracked foi revisado por
ninguém. A pergunta que significa alguma coisa é se o **git VIU** o arquivo:
rastreado, e sem modificação pendente. Um spec assim passou pela mesma revisão
que qualquer outro arquivo; um untracked, ou um rastreado-mas-modificado, é
exatamente a forma de um spec que alguém acabou de escrever.

Fail-CLOSED também quando o git não responde: proveniência que não se consegue
verificar não é proveniência. É gate de POLÍTICA (rc 1), não de infraestrutura.

**O P2 mais grave é um typo.** Uma entrada de exclusão aceitava campos
desconhecidos, então `events` — erro de digitação de `event` — validava com
todos os campos obrigatórios presentes, `get("event")` devolvia `None`, e a
entrada virava exclusão **NUA**: removia TODAS as registrações de um hook de
segurança, com o artefato regenerado passando no `--check`. Um typo que ALARGA
uma subtração é a pior forma que esta família toma. Vocabulário fechado por
entrada.

**O terceiro achado é meu.** A asserção positiva que a rodada 3 acrescentou ao
oráculo de install — «uma exclusão qualificada deixa a outra registração viva» —
exigia um sobrevivente SEMPRE. Para um hook que a base registra sob aquele único
evento, a exclusão qualificada o remove por inteiro, legitimamente, e a asserção
falharia num spec válido. Agora ela pergunta à BASE antes de exigir.

**Custo de método, e ele é meu também:** editei o `DESIGN-F` na sombra enquanto
o rail rodava sobre ela. O wrapper detectou (`TREE MOVED`) e recusou reportar a
rodada como válida — que é o comportamento certo, e a razão de o guard existir.
A rodada 5 roda sobre árvore congelada.

Bateria **252 → 258**.

### 7.10 Pair-rail rodada 5 — os bytes, e o vocabulário por bucket

1 P1 + 2 P2. Os achados estreitam (de «o critério está errado» para «o tipo de
`statusMessage`»), o que é o sinal de convergência que se espera.

**P1 — o porcelain MENTE por desenho.** A cura da rodada 4 perguntava ao
`git status --porcelain` se o spec estava modificado. Um arquivo marcado
`assume-unchanged` ou `skip-worktree` reporta **limpo mesmo editado** — a flag
de índice manda o git parar de olhar. E a implementação **descartava o código de
retorno** do `git status`, então uma invocação FALHA com stdout vazio era lida
como «sem alterações»: um git quebrado virava luz verde.

Cura: comparar os **bytes** do working-tree com os do blob commitado
(`git show HEAD:<rel>`). Nenhuma flag de índice falsifica isso — ou o arquivo É
o que foi revisado, ou não é. Toda chamada de git passou a ser checada, e falha
é recusa.

Medido, e o controle mostra a mentira: sob `skip-worktree` o
`git status --porcelain` sai **vazio** com o arquivo editado, e a comparação de
bytes recusa mesmo assim.

**P2-a — o NOME permitido não diz nada sobre o VALOR.** `annotation_overrides`
checava se o campo era `statusMessage`/`_comment`, mas não o tipo. Um
`{"statusMessage": {"x": 1}}` validava e ia direto para a entrada de hook — uma
instalação nova e todo build de plugin receberiam configuração inválida com o
`--check` verde.

**P2-b — um vocabulário para dois buckets contradizia o registro de auditoria.**
Uma exclusão DECIDIDA podia carregar `oq`/`note` e uma PENDENTE `reason`/
`evidence`. As duas se justificam de formas diferentes por desenho: a decidida
com `reason` + `evidence` que resolve, a pendente nomeando a questão aberta, com
a razão vivendo uma vez em `pending_note`. Vocabulário por bucket.

Bateria **258 → 261**. Controle vermelho com o gerador pré-r5: **6 vermelhos**,
artefato byte-idêntico.

### 7.11 Pair-rail rodada 6 — ZERO P1, e um achado de produto

Três P2, nenhum P1 — a primeira rodada sem achado de severidade alta.

**O achado que vale a rodada é de PRODUTO, não do validador.** O plugin passou a
registrar `check_scratchpad_access.py` (ele vem do template, e o template é a
única fonte desde o FU-F-ACCEL) — mas o build do plugin **não empacota
`.claude/scripts/scratchpad.py`**. E o guard casa por SUFIXO `scratchpad.py`,
em qualquer caminho. Consequência em campo: um adopter que instala só o plugin e
roda o **próprio** script chamado `scratchpad.py --plan X` pode levar bloqueio
de um guard que protege um CLI que o plugin nunca entregou.

Cura: **entregar o CLI**. `copy_guarded_clis()` copia `scratchpad.py` para
`<plugin>/scripts/`, e a resolução própria dele
(`Path(__file__).parent.parent / "hooks"`) passa a apontar para o `<plugin>/hooks`
que o `copy_hooks` já popula. Não é lista paralela — é o oposto: o hook e o
sujeito que ele guarda deixam de ser separáveis. Se o CLI sumir da árvore, o
build **aborta** em vez de emitir um plugin incoerente.

**O guard invertido pegou a própria cura, e isso melhorou o guard.**
`GUARDED_CLIS` é uma tabela module-level que nomeia `check_scratchpad_access.py`
— e o `PluginHooksHaveNoParallelSource` recusava qualquer tabela assim. Mas
nomear um hook não é o defeito; **RE-REGISTRAR** um é. O guard passou a exigir as
duas coisas: nomear um hook do template E carregar a FORMA de uma registração
(`matcher`/`hooks`/`type`/`command` — as chaves de que um bloco de hook é feito).
Verificado nos dois sentidos: passa com `GUARDED_CLIS`, e **continua vermelho
com o ACCEL replantado**. Um guard que não distingue empurra o próximo autor a
renomear até passar, o que é pior que um guard estreito.

**Os outros dois:** `blocking_inclusions` recusava a entrada quando QUALQUER
exclusão qualificada carregava o basename — mas se sobra outra registração, ela
ainda alcança o adopter e ainda precisa da rota (a mesma leitura larga demais que
a rodada 4 achou no oráculo de install; agora pergunta por sobreviventes). E
UTF-8 inválido em qualquer entrada levantava `UnicodeDecodeError` **antes** do
handler de JSON — traceback e exit genérico, em vez do `RC_INFRA == 2` que o
próprio CLI documenta. Um código de saída que só vale para as entradas em que
alguém pensou não é contrato.

Bateria **261 → 266**.

### 7.12 A decisão do Owner (pós-r7), e a exclusão do scratchpad guard

A rodada 7 (registro: `rail-round-7.md`) saiu `CHANGES-REQUESTED` com dois P2:
um curado na hora (alvo malformado sob `--check --spec` escapava como traceback
ou era nomeado DRIFT — os dois casos agora saem `RC_INFRA == 2` com o arquivo
nomeado), e um que era **chamada do Owner**: `check_scratchpad_access.py` casa
por SUFIXO (`_tokens_target_scratchpad`, `check_scratchpad_access.py:96-120` —
folga deliberada para fixtures), então um adopter `--ceremony user` que rode o
PRÓPRIO script chamado `scratchpad.py` com `--plan X` levaria bloqueio de um
guard que existe para proteger o CLI do framework — sem rota praticável, contra
o critério (a) que o próprio spec declara. A cura da r6 (empacotar o CLI no
plugin) fechou «guard sem sujeito», mas não estreita o matcher.

**Decisão do Owner (2026-08-30): opção (a) — EXCLUIR o hook do perfil user**,
revertendo o INCLUIR-NO-USER da classificação §1.1 (que fora produzido pelo
critério ANTIGO, substituído pela própria wave — a mesma defasagem
lista-vs-regra da r2, um nível abaixo). Mecânica, toda por DADO no spec:

* `_derivation.exclude_hooks` ganha a entrada (classe `bloqueia-edicao`,
  reason nomeando o falso positivo e a decisão, evidence com linhas): 17 → 18.
* `_derivation.blocking_inclusions` perde a entrada: 5 → 4.
* Roster gerado: 30 → **29 registrações** (28 basenames); delta de bytes do
  template: +22.360 → **+22.001 B** (37.819 B totais).
* O plugin segue derivado do template e perde a registração E o CLI:
  `copy_guarded_clis` já era condicional («guard not registered → CLI not
  needed») — zero edição em `build-plugin.py`. O `scratchpad.py` continua
  instalado nas duas cerimônias pelo `install.sh` (classificação §5, item 15).
* `RULED_IN` do teste: 10 → 9 tuplas, no MESMO patch que o spec (o comentário
  da lista exige exatamente isso); o completeness test de
  `blocking_inclusions` re-deriva do roster novo e não precisou de edição.

Estreitar o matcher no hook (opção b) ficou registrado como defensável e
não-escolhido: tocaria arquivo fora do FILE ASSIGNMENT desta cerimônia e os
testes próprios do hook assumem a folga de caminho.

A propagação da decisão atravessou mais duas rodadas do rail. A **r8** revisou
a sombra com a cura aplicada e flagrou — corretamente — que os materiais de
cerimônia commitados na árvore ainda diziam 30/10: a cura dos materiais vivia
no working tree do checkout vivo, invisível ao clone que o revisor lê. A
resposta foi estrutural (commit dos materiais no vivo + rebase da sombra), e é
por isso que a rodada seguinte revisou uma árvore CONSISTENTE. A **r9** trouxe
os dois últimos membros da família «declaração aceita e ignorada»:
`_derivation.generator` validado só por PRESENÇA (um caminho vazio ou errado
sobrevivia ao round-trip `--write`/`--check` apontando o leitor para nada), e
o override que vira NO-OP quando a base evolui até o valor declarado — com
reason/evidence sobrevivendo como «exceção documentada» que não existe. Curas
com controle vermelho→verde medido (5 failed / 3 passed → 8 passed, classe
`NoOpDeclarationsAreRejected`; arquivo nuclear 112 → 120 casos; bateria
267 → 275). O P1 da r9 (falta de sentinel assinado) foi refutado como
descrição do próprio fluxo pré-assinatura — registros em `rail-round-8.md` e
`rail-round-9.md`.
