# PLAN-169 OQ-E5 / wave-s330-F — classificação POR MÉRITO dos hooks só-na-base

**Sessão:** S330 (2026-08-27) · **HEAD analisado:** `1c34eb5` · **Escopo:** somente leitura
fora deste arquivo.

Toda linha citada foi lida neste checkout. Onde a fonte primária contradiz um
comentário do repositório, o comentário é marcado **FALSO** e a medição fica.

---

## 0. Censo — reprodução independente

Derivado por parsing do JSON (regex `_python-hook\.sh"?\s+(\S+\.py)` sobre
`hooks[*][*].hooks[*].command`), não por `grep`:

| | `settings.base.json` | `settings.user.json` |
|---|---|---|
| registros | **47** | **20** |
| distintos por basename | **46** (45 `.py` + 1 `echo` inline) | **20** |
| só-na-base (basename) | **26** | — |
| só-no-user | **0** | — |

`check_output_secrets.py` responde pelos 47 vs 46: está em `PostToolUse` **e**
`PostToolUseFailure` na base, e só em `PostToolUse` no user.

Pelo *keyset* que os oráculos usam (`evento + basename`, matcher colapsado —
`scripts/tests/test-upgrade-lifecycle-hooks-derived.sh` `_keys_raw`), o conjunto
só-na-base tem **27** chaves: as 26 acima + `PostToolUseFailure check_output_secrets.py`.

> **Ponto cego medido:** o keyset colapsa o matcher. A divergência de
> `check_anti_ceo_overhead.py` é **invisível** para *todos* os oráculos existentes
> — unit (`test_upgrade_lifecycle_hooks_derived.py`) e e2e (E.14). Nenhum
> instrumento no repositório vigia o matcher do template user hoje.

---

## 1. Tabela de classificação

Legenda de classe (EXCLUIR): `B` = bloqueia-edicao · `G` = exige-gpg-sentinel ·
`I` = exige-infra-ausente-no-user · `M` = maintainer-only-por-desenho.
Todos os paths de hook são relativos a `.claude/hooks/`.

### 1.1 — Os 26 hooks só-na-base

| # | item | evento / matcher (base) | o que faz quando DECIDE | infra de que depende | fail-open sem a infra? | switch advisory | VEREDITO | evidência |
|---|---|---|---|---|---|---|---|---|
| 1 | `accel_dispatch.py` | `PostToolUse` `Edit\|Write\|MultiEdit` to=20 | ADVISORY: funde `additionalContext` dos checks (`accel_dispatch.py:83`). Só propaga `block` se um check embutido bloquear (`:78`) — o único que pode é `verify_after_edit` **sob** `CEO_VERIFY_AFTER_EDIT_BLOCK=1` (`:132`, `:136-140`) | nenhuma (importa `verify_after_edit` sibling, copiado pelo `install.sh:1419`) | sim — «Fail-OPEN: any internal error → allow `{}`» (`:11`) | `CEO_VERIFY_AFTER_EDIT_BLOCK` (opt-in p/ bloquear), `CEO_ADEQUACY_GATE` (opt-in), `CEO_TURBO` | **INCLUIR-NO-USER** | já vai no PLUGIN advisory: `scripts/build-plugin.py:46-50` (ACCEL) sobre `settings.user.json` (`:284`) |
| 2 | `check_adversary.py` | `PreToolUse` `Bash` to=5 | **BLOQUEIA** um comando Bash que carregue credencial viva: `_evaluate` devolve `deny` (enforce) ou `ask` (advisory) em `:156-158`, e **as DUAS pernas emitem `block`** (`:254-262` e `:264-271`) | `.claude/adversary.md` (opcional; ausente ⇒ regras `.md` inertes, `:104-105`) + `_lib/secret_patterns` | infra sim (`:275-281`); **mas o caminho de segredo NÃO** — é fail-CLOSED por desenho (`:151-158`) | `CEO_ADVERSARY` gate **só as regras `.md`**. **Não existe switch para o caminho de segredo** — a mensagem `«Set CEO_ADVERSARY=0 disables enforcement»` (`:260`) é **FALSA** para ele | **EXCLUIR** · `B` | bloqueia Bash sem rota de saída; classe de FP já paga ([[feedback-cpf-checksum-collision-blocks-benign-ids]], mitigada mas não fechada por PLAN-158 W2, `:114-131`) |
| 3 | `check_arbitration_kernel.py` | `PreToolUse` `Edit\|Write\|MultiEdit\|mcp__.*` to=5 | **HARD-DENY** de edições ao kernel de arbitragem (`:309`). Explicitamente **não** destravável por sentinel (`:4-10`) | lista de kernel + `CEO_KERNEL_OVERRIDE` + `_ACK` | — | `CEO_KERNEL_OVERRIDE` / `CEO_KERNEL_OVERRIDE_ACK` (rota do Owner, não advisory) | **EXCLUIR** · `B` | ✔ um dos 10 declarados; critério **confirmado** |
| 4 | `check_bash_canonical_forensic.py` | `PostToolUse` `Bash` to=5 | Só observa: emite `canonical_edit_completed`. «Advisory PostToolUse hook (NEVER blocks)» (`:4`) | trilha de auditoria | n/a (nunca bloqueia) | nenhum | **EXCLUIR** · `M` | ✔ declarado, mas **o critério declarado é FALSO**: não bloqueia nada. A razão real está no próprio docstring (`:8-9`): é a metade E.4 de um par cuja metade E.3 (`check_canonical_edit`) o perfil user **não registra** — trilha forense de um portão que não existe |
| 5 | `check_canonical_edit.py` | `PreToolUse` `Edit\|Write\|MultiEdit\|mcp__.*` to=5 | **BLOQUEIA** (`:686`, `:3110`) toda edição a path canônico sem `approved.md` assinado pelo Owner | sentinel `.claude/plans/PLAN-*/architect/round-*/approved.md` + GPG | não (fail-CLOSED deliberado no deadline, ADR-186) | `CEO_SENTINEL_UNLOCK` + `CEO_SESSION_ANCHOR_SHA` (rota de recuperação, não advisory) | **EXCLUIR** · `G` | ✔ declarado; critério **confirmado**. É a âncora que dois oráculos exigem que continue fora (§4) |
| 6 | `check_closeout_guard.py` | `Stop` to=5 | ADVISORY, `systemMessage` só. «NEVER blocks» (`:4-5`) | git HEAD + `.claude/plans/PLAN-*/staged/**/finish-*.sh` | sim (`:4-5`) | `CEO_CLOSEOUT_GUARD=0`; default **ON** (`:118`) | **EXCLUIR** · `M` | o rito que ele lembra é o do mantenedor: «CLAUDE.md §Current Work + CHANGELOG + memory» (`:14`) e `finish-*.sh` sob `.claude/plans/PLAN-*/staged/**` (`:11`) — nada disso existe no perfil user |
| 7 | `check_codex_filewrite.py` | `PreToolUse` `mcp__codex__codex\|…-reply` to=30 | **BLOQUEIA** (`:275`, `:294`, `:356`) escrita do Codex a path da deny-list | deny-list importada de `check_canonical_edit._CANONICAL_GUARDS` (72 entradas) | **NÃO — fail-CLOSED por ADR-107** (`:24-25`) | `CEO_CODEX_FILEWRITE_DISABLE=1` (`:242`); default **ON** | **EXCLUIR** · `M` | a deny-list contém paths que num repo adopter são **do adopter**: `.github/workflows/*.yml`, `.github/CODEOWNERS`, `AGENTS.md`, `requirements.toml` (medido: `_CANONICAL_GUARDS`, 23 entradas fora de `.claude/`). Guard framework-scoped por construção ⇒ FU-F2 |
| 8 | `check_compact_pinning.py` | `SessionStart` `compact` to=5 | Só `additionalContext` (`:107`); no-op ⇒ `{}` (`:83`) | `_lib/pinned_constraints` (constante de código, zero I/O) | sim | `CEO_CONSTRAINT_PINNING=0`; default **ON** (`:87`) | **EXCLUIR** · `M` | o CONTEÚDO é governança de mantenedor: das 4 constantes, #1 = «PROTOCOL.md vetoes (ADR-052)» e #2 = «Canonical-sentinel discipline (ADR-031)» — e `--ceremony user` **não instala** `PROTOCOL.md` (`scripts/install.sh:2655`) nem o rito de sentinel |
| 9 | `check_config_change.py` | `ConfigChange` to=5 | ALLOW + audita mudança benigna; **BLOQUEIA (advisory-block)** quando entra uma `FORBIDDEN_KEYS` (`:297`) | `_lib/effective_config` (embarcado) | sim | `CEO_CONFIG_CHANGE_GUARD=0`; default **ON** (`:116`) | **INCLUIR-COM-ENV** — chave: `CEO_CONFIG_CHANGE_GUARD` | é a **única** defesa contra `disableAllHooks` no momento da edição (`effective_config.py:137-141`). Risco nomeado em §5 |
| 10 | `check_ledger_checkpoint.py` | `PreToolUse` `Bash` to=5 | ADVISORY, **sem nenhum caminho de deny** — «`ENFORCE_FLIP_IMPLEMENTED` is False and no deny path exists in this module» (`:189-192`) | escopo de plano: exige `plan_id` derivável de `plan_dir`/`plan_ac` (`:1239-1246`) | sim; sem plano ⇒ `out_of_scope_paths` + `{}` (`:1235-1237`) | `CEO_LEDGER_CHECKPOINT=0` (`:186`), master `CEO_SOTA_DISABLE` (`:188`) | **EXCLUIR** · `M` | o ledger do ADR-195/PLAN-179 W2 é o rito de estado durável **do framework**; num adopter sem `.claude/plans/PLAN-NNN/` o hook paga um cold-start de Python por chamada Bash para sair por `out_of_scope_paths` |
| 11 | `check_pair_rail.py` | `PreToolUse` `Edit\|Write\|MultiEdit` **to=210** | **BLOQUEIA** em pin-mismatch (`:1502-1511`, fail-CLOSED ADR-182); advisory quando o Codex está ausente (`CodexUnavailable` ⇒ `systemMessage`) | Codex CLI + `.claude/governance/codex-cli-pin-manifest.json` (**não instalado** em nenhuma cerimônia) | sim para Codex ausente (`:1512-1519`); **não** para pin-mismatch | `CEO_PAIR_RAIL_DISABLE=1` (`:1411`) | **EXCLUIR** · `I` | além da infra: os globs L3+ (`:157-169`) incluem **`.github/workflows/*.yml`** e `PROTOCOL.md` — um adopter editando o CI **dele** entraria num hook de 210 s |
| 12 | `check_plan_edit.py` | `PreToolUse` `Edit\|Write\|MultiEdit` to=5 | **BLOQUEIA** transições ilegais de `status:` (`:239`, `:733`) | `.claude/plans/` + gramática de lifecycle | — | nenhum | **EXCLUIR** · `B` | ✔ declarado; critério **confirmado** |
| 13 | `check_postcompact_reinject.py` | `PostCompact` to=5 | Só `additionalContext` (doutrina pointers-only, `:11`) | snapshot escrito pela metade `PreCompact` (#17) | sim | `CEO_COMPACTION_CONTINUITY=0`; default **ON** (`:494`) | **EXCLUIR** · `M` | re-emite o MESMO bloco de `check_compact_pinning` (item 8) — mesma razão. E o par depende de #17 |
| 14 | `check_protocol_semver_cascade.py` | `PreToolUse` `Edit\|Write\|MultiEdit` to=5 | **Nada bloqueia.** «advisory + **fail-OPEN ALWAYS**: it never emits `permissionDecision`, never blocks…» (`:14-15`); zero sítios de `block` | `PROTOCOL.md` + `.claude/adr/` | sim, sempre | `CEO_PROTOCOL_SYNC_CASCADE` | **EXCLUIR** · `I` | ✔ declarado, mas **critério FALSO** (não bloqueia). Razão real: `--ceremony user` **não entrega `PROTOCOL.md`** (`scripts/install.sh:2655`, guard `WS4-guard-proto`) — o sujeito do hook não existe |
| 15 | `check_scratchpad_access.py` | `PreToolUse` `Bash` to=5 | Bloqueia **só** `scratchpad.py --plan X` quando X ≠ plano da sessão (`:47-56` da `decide_command`) | `.claude/scripts/scratchpad.py` — **INSTALADO nas duas cerimônias** (`install.sh:1602` `install_scripts_selective`) | sim: sem `--plan`, sem plano resolvível, ou erro ⇒ allow (`:22-27`) | nenhum (não precisa) | **INCLUIR-NO-USER** | ✔ declarado, mas **critério FALSO nas DUAS metades**: não bloqueia edição (bloqueia uma chamada de CLI do framework) e não exige GPG/sentinel (zero `CEO_*`, zero sentinel). Guarda uma ferramenta que o perfil user recebe |
| 16 | `check_setup_verification.py` | `Setup` `init` to=15 | ADVISORY, zero sítios de block. «NEVER blocks a Setup» (`:11`) | git + a própria árvore instalada | sim (`:9-11`) | `CEO_SETUP_VERIFICATION=0`; default **ON** (`:231`) | **INCLUIR-NO-USER** | fecha a classe «hook no disco mas não registrado / exec-bit caído» (`:5-7`) — valor puro para o adopter, que é justamente quem não roda `validate-governance.sh` à mão |
| 17 | `check_precompact_continuity.py` | `PreCompact` to=5 | Escreve snapshot no scratchpad plan-scoped; não bloqueia | scratchpad + `resolve_plan_id` | sim | `CEO_COMPACTION_CONTINUITY=0`; default **ON** (`:1061`) | **EXCLUIR** · `M` | par de #13; incluir um sem o outro reproduz exatamente a assimetria que esta wave existe para curar. Além disso o rail inteiro está medido como **não-entregando** (`CLAUDE.md` §5, ADR-153 fires-proof NEGATIVO) |
| 18 | `check_skill_bootstrap_post.py` | `PostToolUse` `Edit\|Write\|MultiEdit` to=5 | Observer forense; zero sítios de block | audita o bypass `_bootstrap_bypass_allows` de `check_skill_patch_sentinel` (`:7-14`) | sim | `CEO_SKILL_BOOTSTRAP_POST` | **EXCLUIR** · `M` | ✔ declarado, **critério FALSO** (não bloqueia). Razão real: o sujeito que ele audita (#20) **não é registrado** no perfil user ⇒ o bypass não pode ocorrer |
| 19 | `check_skill_reference_read.py` | `PostToolUse` `Read` to=5 | Observer; zero sítios de block. Emite `reference_postread_observed` / `skill_reference_read_mismatch` | audit-log + evento de spawn com `claimed_sha` | sim | `CEO_SKILL_READ_V2` | **INCLUIR-NO-USER** | ✔ declarado, **critério FALSO**: não bloqueia e não exige GPG/sentinel. É a metade observadora de um par cuja metade **emissora está NO perfil user** — `check_agent_spawn.py` é registrado lá (`settings.user.json` `PreToolUse` `Agent`). Sem ele o contrato ADR-051 do adopter é inauditável |
| 20 | `check_skill_patch_sentinel.py` | `PreToolUse` `Edit\|Write\|MultiEdit` to=5 | **BLOQUEIA** escrita de `SKILL.md` (`:81`) | proposta `SP-NNN` em `.claude/proposals/` (**não instalado**) + `CEO_SKILL_PATCH_SHA` | — | `CEO_SKILL_BOOTSTRAP`/`_ACK` (bypass de bootstrap), `CEO_SOTA_DISABLE` | **EXCLUIR** · `G` | ✔ declarado; critério **confirmado** |
| 21 | `check_subagent_start.py` | `SubagentStart` to=5 | Grava sidecar de estado; zero sítios de block | dir de estado (`CEO_SUBAGENT_LIFECYCLE_STATE_DIR`, resolvido) | sim | `CEO_SUBAGENT_LIFECYCLE=0` (`:239`); default **ON** | **INCLUIR-NO-USER** | **repara uma assimetria já existente no perfil user**: `check_fluency_nudge.py` (`SubagentStop`) **está** no template user e é o CONSUMIDOR deste sidecar (`:6-11`) — hoje o user tem a metade STOP sem a metade START, e o emit `subagent_lifecycle_observed` nunca fecha |
| 22 | `check_tier_policy.py` | `PreToolUse` `Edit\|Write\|MultiEdit` to=5 | **BLOQUEIA** (`:78-81`) edição de `.claude/agents/code-reviewer.md` / `security-engineer.md` sem sentinel | sentinel `PLAN-*/architect/round-*/approved.md` com `Approved-By:` (`:64-66`, `:84-88`) | — | `CEO_KERNEL_OVERRIDE` | **EXCLUIR** · `G` | ✔ declarado; critério **confirmado** |
| 23 | `check_worktree_writer.py` | `PreToolUse` `Bash\|Edit\|Write\|MultiEdit` to=5 | **DENY fail-CLOSED** (`:665`, `:683`, `:698`, `:704`, `:709`) quando o modo parallel-writer está ativo e a escrita sai do worktree | pool de worktrees (`_worktree_pool`) | inerte: sem `CEO_PARALLEL_WRITER` é «one env lookup → allow» (`:31-33`) | `CEO_PARALLEL_WRITER` é o **opt-in**; não há kill-switch (nem precisa) | **EXCLUIR** · `M` | policia um modo de orquestração do mantenedor (ADR-049a AMEND-1). Inofensivo se incluído, mas é peso morto: nada no perfil user seta o opt-in |
| 24 | `codex_review_user_code.py` | `Stop` to=130 | Default = **DETECT-ONLY**: `systemMessage` com nudge, nunca roda Codex (`:293-303`). Bloqueia só sob `CEO_CODEX_USER_REVIEW_BLOCK=1` (`:323-324`) | Codex CLI **apenas em modo AUTO** | sim: `shutil.which("codex")` ausente ⇒ `(False, None)` = infra-skip (`:123-124`) | `CEO_CODEX_USER_REVIEW=0` (`:285`), `_AUTO` (opt-in), `_BLOCK` (opt-in) | **INCLUIR-NO-USER** | o propósito declarado é **revisar o código DO ADOPTER** (`:1-4`); e já vai no PLUGIN advisory (`build-plugin.py:53-56`) |
| 25 | `review_loop.py` | `Stop` to=15 | Bloqueia o Stop (`:282`) — mas **opt-in default-OFF**: «If `CEO_REVIEW_LOOP` != "1": return `{}`» (`:12`); cap de 3 iterações (`:43`) | git diff (read-only, `:6`) | sim | `CEO_REVIEW_LOOP` é o opt-in (`:42`) | **INCLUIR-NO-USER** | inerte por default; já vai no PLUGIN advisory (`build-plugin.py:57-58`) |
| 26 | `turbo_sessionstart.py` | `SessionStart` to=5 | Só `additionalContext` (banner); zero sítios de block | `turbo_profile` + `auto_boot` (siblings copiados) | sim, `{}` (`:12`) | `CEO_TURBO=0` **ou** `<proj>/.claude/turbo-off` (`turbo_profile.py:19-25`) | **INCLUIR-NO-USER** | já vai no PLUGIN advisory (`build-plugin.py:61-65`); é o canal `additionalContext` com evidência positiva de consumo (citado como precedente em `check_compact_pinning.py:19-21`) |

### 1.2 — As 2 divergências de matcher/registro (o `_comment` diz que não existem)

| item | base | user | veredito | evidência |
|---|---|---|---|---|
| `check_anti_ceo_overhead.py` | `PreToolUse` matcher `Agent\|Bash\|Edit\|Write\|MultiEdit\|Read\|Glob\|Grep\|WebFetch\|WebSearch\|NotebookEdit\|TodoWrite\|Task\|mcp__.*` | matcher `Read\|Edit\|Write\|MultiEdit\|Bash` | **MANTER a divergência — mas DECLARADA** (`matcher_overrides`) | hook é fail-OPEN, advisory, budget ≤20/dia. O matcher estreito é uma escolha de latência legítima para o perfil advisory (5 ferramentas × cold-start vs 14). Hoje é **drift acidental**: o `_comment` afirma paridade byte-a-byte e nenhum oráculo vigia matcher (§0) |
| `check_output_secrets.py` | 2 registros: `PostToolUse` + **`PostToolUseFailure`** | 1 registro: só `PostToolUse` | **INCLUIR o registro `PostToolUseFailure`** | é o scanner de vazamento em saída de ferramenta (ADR-057, advisory, kill-switch `CEO_OUTPUT_SCAN=0`). Uma ferramenta que **falha** é exatamente onde stack-trace vaza segredo; não há razão declarada em lugar nenhum para o perfil user cobrir só o caminho de sucesso |

### 1.3 — As 6 chaves de env

| chave | base | user | veredito | evidência / razão |
|---|---|---|---|---|
| `CEO_QUIET_MODE` | `"1"` | `"1"` | (já em ambos) | — |
| `CEO_CONFIG_PROTECTION_ADVISORY` | ausente | `"1"` | **MANTER só no user** | é o que torna `check_config_protection.py` advisory em vez de bloqueante; carga provada pelo rail round 7 P1 (`PLAN-169/s329-ceremony-E/rail-round-7.md:8`) e vigiado por `test_upgrade_lifecycle_hooks_derived.py:1053-1056` |
| `CLAUDE_CODE_SUBAGENT_MODEL` | `"inherit"` | ausente | **INCLUIR** | ADR-144 escolheu `inherit` **explicitamente sobre apagar a chave**: «chose `inherit` — it is self-documenting and corrective (re-running the installer overwrites a poisoned `haiku` back to `inherit`), whereas an absent key is silent» (`ADR-144…:110-112`). É o valor **anti-veneno**, não um pin de custo — não conflita com o `_model_comment`, que só proíbe `availableModels`/`enforceAvailableModels` |
| `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` | `"1"` | ausente | **INCLUIR** | higiene de env em subprocesso; sem conteúdo de cerimônia. Nenhum ADR encontrado — ratificação do Owner recomendada, ônus baixo |
| `BASH_MAX_TIMEOUT_MS` | `"600000"` | ausente | **INCLUIR** (com nota) | tuning do harness, mas **muda comportamento visível do adopter** (teto de 10 min nos comandos Bash *dele*). Nenhum ADR encontrado |
| `CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR` | `"1"` | ausente | **INCLUIR** | tuning do harness, sem conteúdo de cerimônia. Nenhum ADR encontrado |
| `ENABLE_TOOL_SEARCH` | `"auto"` | ausente | **INCLUIR** | tuning do harness, sem conteúdo de cerimônia. Nenhum ADR encontrado |

`env_exclude` proposto: **vazio**. Não encontrei razão provada para excluir
nenhuma das 5 — em particular `CLAUDE_CODE_SUBAGENT_MODEL`, que a leitura do
ADR-144 mostra ser o oposto de um pin restritivo.

---

## 2. Re-verificação dos 10 declarados

O `_comment` de `templates/settings/settings.user.json:2` diz que os 10 saíram por
serem «governance/sentinel/kernel hooks **that block edits or require GPG/sentinel
ceremony infra**». Medido hoje:

| hook | ainda bloqueia? | ainda exige GPG/sentinel? | critério declarado se sustenta? | veredito |
|---|---|---|---|---|
| `check_plan_edit.py` | **sim** (`:239`, `:733`) | não | **sim** (metade "bloqueia") | EXCLUIR mantido |
| `check_arbitration_kernel.py` | **sim** (`:309`) | não (kernel-override, e é anti-sentinel por desenho) | **sim** | EXCLUIR mantido |
| `check_tier_policy.py` | **sim** (`:80`) | **sim** (`:84-88`) | **sim** | EXCLUIR mantido |
| `check_canonical_edit.py` | **sim** (`:686`, `:3110`) | **sim** | **sim** | EXCLUIR mantido |
| `check_protocol_semver_cascade.py` | **NÃO** — «advisory + **fail-OPEN ALWAYS**» (`:14-15`), zero sítios | não | **NÃO** | EXCLUIR **por outra razão** (`I`): `PROTOCOL.md` não é entregue ao perfil user |
| `check_skill_patch_sentinel.py` | **sim** (`:81`) | **sim** (`.claude/proposals/` + `CEO_SKILL_PATCH_SHA`) | **sim** | EXCLUIR mantido |
| `check_scratchpad_access.py` | bloqueia, **mas não edição** — só `scratchpad.py --plan X` divergente | **não** (zero `CEO_*`, zero sentinel) | **NÃO, nas duas metades** | **SAI da lista ⇒ INCLUIR** |
| `check_skill_reference_read.py` | **NÃO** (observer, zero sítios) | não | **NÃO** | **SAI da lista ⇒ INCLUIR** |
| `check_skill_bootstrap_post.py` | **NÃO** (observer, zero sítios) | não | **NÃO** | EXCLUIR **por outra razão** (`M`): audita um bypass de um hook que o perfil user não registra |
| `check_bash_canonical_forensic.py` | **NÃO** — «NEVER blocks» (`:4`) | não | **NÃO** | EXCLUIR **por outra razão** (`M`): metade E.4 sem a metade E.3 |

**Placar:** 5 dos 10 sustentam o critério como escrito. 3 permanecem fora por
razão diferente da declarada. **2 saem da lista** (`check_scratchpad_access.py`,
`check_skill_reference_read.py`).

**Nenhum é INCLUIR-COM-ENV** — não achei entre os 10 nenhum que bloqueie e tenha
switch advisory em `.env` no molde de `check_config_protection.py`. O único
INCLUIR-COM-ENV do conjunto inteiro é `check_config_change.py` (item 9), que não
está entre os 10.

**Consequência para o texto do `_comment`:** o critério precisa ser reescrito.
Sugestão em uma linha, que cobre os 17 EXCLUIR sem ficção:

> *Fica de fora todo hook que (a) bloqueia uma chamada de ferramenta sem rota
> advisory, (b) exige infraestrutura de cerimônia que `--ceremony user` não
> instala, ou (c) observa/reforça um rito de mantenedor cuja metade enforcing o
> perfil não registra.*

---

## 3. Spec de derivação proposto (o que o gerador da wave lê)

```json
{
  "source": "settings.base.json",
  "exclude_hooks": [
    {"name": "check_canonical_edit.py",           "class": "exige-gpg-sentinel",           "reason": "bloqueia toda edicao de path canonico sem approved.md assinado pelo Owner; o perfil user nao tem rito de sentinel nem GPG", "evidence": ".claude/hooks/check_canonical_edit.py:686,3110"},
    {"name": "check_skill_patch_sentinel.py",     "class": "exige-gpg-sentinel",           "reason": "bloqueia escrita de SKILL.md sem proposta SP-NNN em .claude/proposals/ (nao instalado) + CEO_SKILL_PATCH_SHA", "evidence": ".claude/hooks/check_skill_patch_sentinel.py:81; scripts/install.sh nao instala .claude/proposals/"},
    {"name": "check_tier_policy.py",              "class": "exige-gpg-sentinel",           "reason": "bloqueia edicao dos 2 agentes com VETO sem sentinel Approved-By", "evidence": ".claude/hooks/check_tier_policy.py:80,84-88"},
    {"name": "check_arbitration_kernel.py",       "class": "bloqueia-edicao",              "reason": "HARD-DENY do kernel de arbitragem; anti-sentinel por desenho, sem rota advisory", "evidence": ".claude/hooks/check_arbitration_kernel.py:309, docstring :4-10"},
    {"name": "check_plan_edit.py",                "class": "bloqueia-edicao",              "reason": "bloqueia transicoes ilegais de status: em arquivos de plano", "evidence": ".claude/hooks/check_plan_edit.py:239,733"},
    {"name": "check_adversary.py",                "class": "bloqueia-edicao",              "reason": "bloqueia comando Bash com credencial viva mesmo com CEO_ADVERSARY unset (ask tambem emite block); nao existe switch para esse caminho", "evidence": ".claude/hooks/check_adversary.py:156-158,254-271; a mensagem :260 e falsa para o caminho de segredo"},
    {"name": "check_pair_rail.py",                "class": "exige-infra-ausente-no-user",  "reason": "exige Codex CLI + .claude/governance/codex-cli-pin-manifest.json (nao instalado); 210s; os globs L3+ incluem .github/workflows/*.yml do proprio adopter", "evidence": ".claude/hooks/check_pair_rail.py:157-169,1502-1511"},
    {"name": "check_protocol_semver_cascade.py",  "class": "exige-infra-ausente-no-user",  "reason": "vigia PROTOCOL.md, que --ceremony user nao instala; advisory fail-OPEN sempre, entao o criterio antigo (bloqueia) era falso", "evidence": ".claude/hooks/check_protocol_semver_cascade.py:14-15; scripts/install.sh:2655"},
    {"name": "check_codex_filewrite.py",          "class": "maintainer-only-por-desenho",  "reason": "deny-list compartilhada com _CANONICAL_GUARDS contem paths que num adopter sao DELE (.github/workflows/*.yml, .github/CODEOWNERS, AGENTS.md, requirements.toml); fail-CLOSED por ADR-107", "evidence": ".claude/hooks/check_canonical_edit.py:_CANONICAL_GUARDS (72 entradas, 23 fora de .claude/); check_codex_filewrite.py:24-25,275,294,356"},
    {"name": "check_worktree_writer.py",          "class": "maintainer-only-por-desenho",  "reason": "policia o modo parallel-writer (ADR-049a AMEND-1) do mantenedor; inerte sem CEO_PARALLEL_WRITER, que nada no perfil user seta", "evidence": ".claude/hooks/check_worktree_writer.py:31-33,665"},
    {"name": "check_bash_canonical_forensic.py",  "class": "maintainer-only-por-desenho",  "reason": "metade forense E.4 de um par cuja metade E.3 (check_canonical_edit) o perfil nao registra; nunca bloqueia", "evidence": ".claude/hooks/check_bash_canonical_forensic.py:4,8-9"},
    {"name": "check_skill_bootstrap_post.py",     "class": "maintainer-only-por-desenho",  "reason": "audita o bypass _bootstrap_bypass_allows de check_skill_patch_sentinel, que o perfil nao registra; sem sujeito", "evidence": ".claude/hooks/check_skill_bootstrap_post.py:7-14"},
    {"name": "check_closeout_guard.py",           "class": "maintainer-only-por-desenho",  "reason": "lembra o rito de closeout do mantenedor (CLAUDE.md, CHANGELOG, finish-*.sh em staged/)", "evidence": ".claude/hooks/check_closeout_guard.py:11,14"},
    {"name": "check_ledger_checkpoint.py",        "class": "maintainer-only-por-desenho",  "reason": "checkpoint do ledger plan-scoped (ADR-195); sem .claude/plans/PLAN-NNN/ sai sempre por out_of_scope_paths pagando um cold-start por chamada Bash", "evidence": ".claude/hooks/check_ledger_checkpoint.py:1235-1246"},
    {"name": "check_compact_pinning.py",          "class": "maintainer-only-por-desenho",  "reason": "reinjeta PINNED_CONSTRAINTS cujas entradas 1 e 2 sao PROTOCOL.md/ADR-052 e o rito de sentinel ADR-031 — nenhum dos dois existe no perfil user", "evidence": "_lib/pinned_constraints.PINNED_CONSTRAINTS[0..1]; scripts/install.sh:2655"},
    {"name": "check_postcompact_reinject.py",     "class": "maintainer-only-por-desenho",  "reason": "re-emite o mesmo bloco de check_compact_pinning; mesma razao, e depende do par PreCompact", "evidence": ".claude/hooks/check_postcompact_reinject.py:1-11"},
    {"name": "check_precompact_continuity.py",    "class": "maintainer-only-por-desenho",  "reason": "metade PreCompact do par acima; incluir uma sem a outra reproduz a assimetria que esta wave cura", "evidence": ".claude/hooks/check_precompact_continuity.py:1-12; CLAUDE.md secao 5 (ADR-153 fires-proof NEGATIVO)"}
  ],
  "env_overrides": {
    "CEO_CONFIG_PROTECTION_ADVISORY": "1",
    "CEO_CONFIG_CHANGE_GUARD": "1"
  },
  "env_exclude": [],
  "matcher_overrides": {
    "check_anti_ceo_overhead.py": {
      "PreToolUse": "Read|Edit|Write|MultiEdit|Bash",
      "reason": "escolha DELIBERADA de latencia do perfil advisory: 5 ferramentas em vez de 14 cold-starts. Hook e fail-OPEN, advisory, budget <=20/dia. Hoje esta divergencia e drift nao-declarado e nenhum oraculo a ve (o keyset colapsa matcher).",
      "evidence": "templates/settings/settings.base.json vs settings.user.json; scripts/tests/test-upgrade-lifecycle-hooks-derived.sh _keys_raw colapsa o matcher"
    }
  },
  "top_level_keep": ["_comment", "_model_comment", "_squad_allowlist_comment", "env", "hooks", "model", "squad_allowlist"]
}
```

**Notas sobre o spec:**

- `exclude_hooks` tem **17** entradas. `26 − 17 = 9` INCLUIR
  (8 diretos + `check_config_change.py` com env). Roster user resultante,
  computado sobre os artefatos: **20 → 30 registros**, **20 → 29 basenames
  distintos** (9 hooks novos + o registro `PostToolUseFailure
  check_output_secrets.py`).
- `env_overrides` inclui `CEO_CONFIG_CHANGE_GUARD: "1"` **explícito** mesmo sendo
  o default — o valor default vive em código (`check_config_change.py:116`) e a
  lição do rail round 7 é que *«uma registração é só tão advisory quanto a
  setting que ela lê»*; declarar a chave torna o perfil auto-descritivo e dá ao
  adopter um lugar onde escrever `"0"`.
- `top_level_keep` está **como o prompt pediu**, mas é preciso notar: a base tem
  14 chaves de topo que o user não tem (`permissions` — incluindo
  `defaultMode`/`deny`/`allow` —, `availableModels`, `fallbackModel`,
  `statusLine`, `plansDirectory`, `cleanupPeriodDays`, `disableSkillShellExecution`,
  `skillListingBudgetFraction`, `skillOverrides`, `attribution` + 4 comentários).
  Um gerador «por subtração» precisa de uma lista de **top-level exclude**
  explícita, senão `permissions.deny` e `availableModels` vazam para o perfil
  advisory — e `availableModels` é justamente o que o `_model_comment` proíbe
  (`settings.user.json:5`) e o que `test_template_dogfood_parity.py:398-412`
  reprova. **Recomendação: o spec ganhe `top_level_exclude` derivado, não
  `top_level_keep` literal** — um `keep` literal é a mesma classe de lista
  literal que a OQ-E5 existe para matar.

---

## 4. Mapa dos sítios que afirmam contagem/composição do template user

Efeito de referência para a coluna da direita, computado sobre os artefatos com a
mesma semântica de keyset dos oráculos: o roster user vai de **20 para 30
registros** (29 basenames) e o conjunto base-only cai de **27 para 17** chaves.

| # | sítio | valor / asserção atual | efeito da wave |
|---|---|---|---|
| 1 | `templates/settings/settings.user.json:2` (`_comment`) | «REMOVING **exactly the 10**» + «Every RETAINED entry's BEHAVIORAL fields (matcher/command/timeout) are **byte-identical**» | **as duas metades são FALSAS hoje** (2 divergências, §1.2). Precisa ser reescrito pela wave |
| 2 | `templates/settings/settings.user.json:2` | cita **`PLAN-122 WS-4`** | **o arquivo do plano NÃO existe em nenhum ref git** — `git log --all -- '.claude/plans/PLAN-122*'` = vazio; `git log --all --grep=PLAN-122` = vazio. A citação é um ponteiro morto (ver §6) |
| 3 | `.claude/scripts/tests/test_upgrade_lifecycle_hooks_derived.py:936-940` | `assertGreaterEqual(len(only), 10)` | 27 → **17**: passa (margem 7) |
| 4 | `.claude/scripts/tests/test_upgrade_lifecycle_hooks_derived.py:941-946` | `assertIn("PreToolUse check_canonical_edit.py", only)` | passa (item 5 fica EXCLUIR) |
| 5 | `.claude/scripts/tests/test_upgrade_lifecycle_hooks_derived.py:948-955` | igualdade DERIVADA (merge sob `ceremony=user` == keyset do template) | auto-ajusta |
| 6 | `.claude/scripts/tests/test_upgrade_lifecycle_hooks_derived.py:1043-1056` | `res["env"] == template["env"]` (derivado) + literal `CEO_CONFIG_PROTECTION_ADVISORY` | auto-ajusta; a chave literal permanece |
| 7 | `.claude/scripts/tests/test_upgrade_lifecycle_hooks_derived.py:1058-1062` | `key = sorted(tpl["env"])[0]` — hoje `CEO_CONFIG_PROTECTION_ADVISORY` | com as 5 chaves novas, `sorted()[0]` passa a ser **`BASH_MAX_TIMEOUT_MS`**. O teste continua válido (é derivado), mas **o alvo muda** |
| 8 | `scripts/tests/test-upgrade-lifecycle-hooks-derived.sh:749-752` (E.14a) | `BASE_ONLY_N -ge 10`; hoje **27** | → **17**: passa (margem 7) |
| 9 | `scripts/tests/test-upgrade-lifecycle-hooks-derived.sh:779` (E.14j) | `ENV_KEY` = env do user **menos** env da base; `scaffold` se vazio | hoje o conjunto é `{CEO_CONFIG_PROTECTION_ADVISORY}`; se a wave adotar as 5 da base **e** `CEO_CONFIG_CHANGE_GUARD`, sobram 2 → passa. **Se alguém "curasse" a divergência de env adotando a base inteira sem chave própria, E.14j vira `scaffold`** |
| 10 | `scripts/tests/test-upgrade-lifecycle-hooks-derived.sh:790` | `STRIP_LINE` = 1ª linha `PreToolUse *.py` do keyset user | alfabeticamente hoje `check_agent_spawn.py`; permanece (INCLUIR só acrescenta) |
| 11 | `scripts/tests/test-upgrade-lifecycle-hooks-derived.sh:249` (E.1a) | `TPL_N -ge 20` sobre a **base** | não afetado |
| 12 | `scripts/build-plugin.py:284` | lê `settings.user.json` como o «advisory set» do PLUGIN | **CONSUMIDOR NÃO NOMEADO NA OQ-E5.** Ver #13 |
| 13 | `scripts/build-plugin.py:44-66` (`ACCEL`) | acrescenta `accel_dispatch.py` (to=20), `codex_review_user_code.py` (to=130), `review_loop.py` (**to=60**), `turbo_sessionstart.py` (**to=10**) por cima do advisory set | **incluir esses 4 no template gera DUPLICATA no `hooks.json` do plugin.** Além disso os timeouts de `review_loop` (60 vs 15) e `turbo_sessionstart` (10 vs 5) **divergem** da base. A wave tem de esvaziar/reconciliar `ACCEL` no MESMO patch |
| 14 | `.claude/hooks/tests/test_template_dogfood_parity.py:103` + `:294` | `T64_TEMPLATE_REGISTRATIONS = 47` (literal, sobre a **base**) | não afetado — mas é o único oráculo de contagem literal do repo |
| 15 | `.claude/hooks/tests/test_template_dogfood_parity.py:387-416` (`TestUserTemplate`) | pin de `model`; proíbe `availableModels`/`enforceAvailableModels`; concorda com o pin da base | **não há NENHUMA asserção sobre o roster de hooks do template user** — é exatamente esse vazio que permitiu a defasagem |
| 16 | `templates/settings/settings.base.json:617` (`_posture_keys_comment`) | «this template stays at **45 registrations** until the floor probe is recorded» | **FALSO hoje: a base tem 47.** Fora do escopo da wave, mas é a mesma classe |
| 17 | `templates/settings/settings.base.json:2` (`_comment`) | «ships ALL active governance hooks the framework runs (**currently ~16+**…)» seguido de lista de 16 nomes | **defasado: 46 distintos.** Mesma classe |
| 18 | `scripts/install.sh:2145-2146` | `BASE_SRC = settings.user.json` sob `--ceremony user` | seletor; não afirma contagem |
| 19 | `scripts/upgrade.sh:2573,2607` | seleciona o template pela cerimônia (wave E, `5930974`) | seletor; não afirma contagem |
| 20 | `scripts/tests/test-install-deny-baseline.sh:22,238-244` | perna (D): «`settings.user.json` has NO permissions block» → baseline criada do zero | **quebra se o gerador copiar `permissions` da base** (ver §3, nota do `top_level_keep`) |
| 21 | `scripts/tests/smoke-install.sh:179-195` | `--ceremony user` passa `validate-governance.sh` **e** não escreve fora de `.claude/` | não afetado por registrações (os arquivos já são copiados) |
| 22 | `.claude/plans/PLAN-169/s329-ceremony-E/EXPECTED-BASELINE.txt:182` | `EXPECTED_TEMPLATE_REGISTRATIONS_USER=20` | baseline **congelada** de cerimônia já landada, lida por `finalize-E.sh:432` e `OWNER-S329-E-LAND.sh:726`. Re-rodar qualquer um deles pós-wave falha. Lição S328 aplicável: `EXPECTED_*` declarado à mão envelhece — atualizar **conscientemente com fonte**, nunca relaxar |
| 23 | `.claude/plans/PLAN-169/s329-ceremony-E/DESIGN-E.md:919,984-989` | «`settings.user.json`, **20**»; «DEFASADO em 16» | prosa de desenho da wave E |
| 24 | `.claude/plans/PLAN-169-closure-and-cross-session-evolution.md:1242,1268-1279` | «`settings.user.json` (**20**) sob `user`»; OQ-E5 «26 = 10 + 16» | plano; a wave atualiza no registro de execução |
| 25 | `CLAUDE.md:109` | «26 só-na-base = 10 excluídos de propósito + 16 que a base ganhou desde 30/07» | **a aritmética 10+16 sobrevive, mas a semântica não**: dos 10, apenas 5 sustentam o critério; 2 saem da lista. O closeout precisa reescrever |

---

## 5. Riscos por INCLUIR — o que o adopter `user` vê no próximo upgrade

Contexto que vale para todos: os **arquivos** dos 26 hooks **já estão no disco do
adopter** desde o install (`install.sh:1413-1424` `install_hooks_selective` copia
todo `.claude/hooks/*.py` e `*.sh` sem olhar a cerimônia). A wave muda
**registração**, não entrega. E desde `5930974` a semântica do
`_merge_lifecycle_hooks_into_settings` é **aditiva** — todo INCLUIR chega a todo
adopter `user` no próximo `upgrade.sh`, sem ele pedir.

| hook | o que o adopter passa a ver | switch para desligar |
|---|---|---|
| `codex_review_user_code.py` (`Stop`, to=130) | Ao fim de um turno com diff arriscado (auth/dinheiro/migração/cripto/diff grande), **uma** mensagem: «RISKY DIFF in <files> — get a cross-model review before committing: run `codex review --uncommitted`». Deduplicada por hash de diff. **Não roda Codex** e não bloqueia. Sem `codex` no PATH: silêncio | `CEO_CODEX_USER_REVIEW=0`. (Nunca ative `CEO_CODEX_USER_REVIEW_AUTO=1` no perfil user sem avisar: aí sim roda um subprocesso de até 130 s no Stop) |
| `review_loop.py` (`Stop`, to=15) | **Nada** — `CEO_REVIEW_LOOP != "1"` ⇒ `{}` já na entrada | é opt-in; ligar é a ação, não desligar |
| `turbo_sessionstart.py` (`SessionStart`) | Um banner «what's on» + banner de primeira execução no começo da sessão, via `additionalContext` | `CEO_TURBO=0` **ou** criar `<repo>/.claude/turbo-off` |
| `accel_dispatch.py` (`PostToolUse` edit, to=20) | Após um Edit/Write que quebre o arquivo (ex.: Python que não compila), um bloco «AFTER-EDIT VERIFY» no contexto. **Advisory** | `CEO_VERIFY_AFTER_EDIT_BLOCK` deve **permanecer unset** (é o que o mantém advisory); `CEO_ADEQUACY_GATE` idem |
| `check_config_change.py` (`ConfigChange`) | **Pode BLOQUEAR** o evento de mudança de settings. Duas classes de falso-positivo reais para um adopter: (a) `disableAllHooks` — o bloqueio é o ponto; (b) **`ANTHROPIC_MODEL` / `ANTHROPIC_DEFAULT_*` / `ANTHROPIC_SMALL_FAST_MODEL` fora da allowlist ADR-149** — um adopter em Bedrock/Vertex, ou usando um id de modelo próprio, é **legítimo** e leva bloqueio | `CEO_CONFIG_CHANGE_GUARD=0` (por isso o veredito é INCLUIR-**COM-ENV** e a chave entra explícita em `env_overrides`) |
| `check_setup_verification.py` (`Setup init`, to=15) | Na primeira execução pós-install, um relatório advisory de auto-verificação. Nunca bloqueia | `CEO_SETUP_VERIFICATION=0` |
| `check_subagent_start.py` (`SubagentStart`) | **Escreve estado**: um sidecar por agente no dir de estado resolvido. Nada visível; fecha o emit `subagent_lifecycle_observed` que hoje nunca fecha no perfil user | `CEO_SUBAGENT_LIFECYCLE=0` |
| `check_scratchpad_access.py` (`PreToolUse Bash`) | **Pode BLOQUEAR** exatamente um comando: `scratchpad.py --plan X` com X ≠ plano da sessão. Qualquer outro Bash é allow por caminho curto | nenhum switch (e não precisa: o escopo é uma flag de um CLI do framework). Rota do usuário: rodar sem `--plan` |
| `check_skill_reference_read.py` (`PostToolUse Read`) | Nada visível; breadcrumb no audit-log a cada Read de `SKILL.md`. **Escreve estado** em `CEO_SKILL_READ_STATE_DIR` | `CEO_SKILL_READ_V2` |
| `check_output_secrets.py` no `PostToolUseFailure` | Scanner advisory também no caminho de falha de ferramenta | `CEO_OUTPUT_SCAN=0` (mesmo switch do registro que ele já tem) |

**Risco agregado de latência:** os INCLUIR acrescentam cold-starts de Python em
`Stop` (×2), `SessionStart` (×1), `PostToolUse Edit|Write|MultiEdit` (×1),
`PostToolUse Read` (×1), `PreToolUse Bash` (×1), `SubagentStart` (×1),
`ConfigChange` (×1), `Setup init` (×1). O perfil advisory é o que mais sente
custo por turno. **Recomendação:** medir p50/p95 de `PreToolUse Bash` e
`PostToolUse Read` antes do land — são os dois eventos de maior frequência, e o
gate de hook-latency do `Validate` já é conhecido por sensibilidade a runner
(`CLAUDE.md` §5, emenda ADR-163 ainda proposta).

**Risco de plugin (o mais concreto):** `scripts/build-plugin.py` **duplica** 4
registrações se a wave landar sem tocar `ACCEL` — ver §4 #12/#13. Um
`python3 scripts/build-plugin.py` + diff do `hooks.json` gerado pertence à
bateria do land.

---

## 6. ADR — existe decisão registrada sobre a composição do perfil user?

**Não.** Medido:

- **`PLAN-122 WS-4` não existe.** `git log --all -- '.claude/plans/PLAN-122*'` →
  vazio. `git log --all --grep='PLAN-122'` → vazio. Nenhum commit em nenhum ref
  criou esse arquivo. A string `PLAN-122` aparece no repo (`SPEC/v1/audit-log.schema.md`,
  `.claude/hooks/UserPromptSubmit.py`, `.claude/scripts/optimizer/fanout.py` — o
  trabalho do *optimizer*), mas **o plano em si nunca foi commitado**. A citação
  no `_comment` do template é um ponteiro morto.
- **Nenhum ADR decide o roster.** Varredura em `.claude/adr/*.md`: o único que
  fala de `--ceremony user` é **ADR-155-AMEND-1**, e apenas para dizer o que o
  install **pula** (`:90`: «A `--ceremony user` install SKIPS `install_spec_v1`,
  …») — nada sobre hooks. ADR-181 e ADR-144 tocam só o pin de modelo / o
  `CLAUDE_CODE_SUBAGENT_MODEL`.
- **Nenhum oráculo vigia o roster.** `test_template_dogfood_parity.py`
  (`TestUserTemplate`, `:385-416`) só verifica `model`, `availableModels`,
  `enforceAvailableModels`. Os oráculos da wave E (`:913+` e E.14) verificam que
  o **upgrade reproduz o template**, não que o **template esteja certo**.

Ou seja: a composição do perfil user é hoje justificada **exclusivamente pelo
comentário do próprio arquivo que ela descreve** — um documento auto-referencial,
que aponta para um plano inexistente e cujas duas afirmações verificáveis são
falsas. É precisamente a forma «instrumento verde cuja pergunta envelheceu»
([[feedback-instrument-green-with-stale-question]]), uma camada acima: aqui não há
nem instrumento.

**Recomendação: ADR NOVO, não ADR-AMEND.** Um AMEND exige um ADR-pai que
decida a coisa emendada; não existe. O ADR novo deve fixar, no mínimo:

1. **O perfil user é DERIVADO** de `settings.base.json` por subtração declarada —
   nunca uma segunda cópia literal. (Mesma forma que a wave E aplicou ao
   `upgrade.sh` e que o PLAN-183 D3 aplicou às rotas de entrega: o metadado vira
   DADO com leitores, não literal replicado.)
2. **O critério de exclusão em 3 alíneas** (§2), substituindo o «block edits or
   require GPG/sentinel» que 5 dos 10 não satisfazem.
3. **`build-plugin.py` é o 2º leitor** do spec de derivação — `ACCEL` deixa de
   ser uma lista paralela.
4. **Um teste de paridade que faz a pergunta certa:** «o template user é
   byte-idêntico ao que o gerador produz a partir da base + spec?» — o oráculo
   que não existe hoje e sem o qual a defasagem volta.
5. Os pontos cegos declarados: matcher não vigiado pelo keyset (§0);
   `top_level_*` precisa de exclude derivado (§3).

---

## 7. Follow-ups abertos (não são da wave F; são achados dela)

- **FU-F1 — `check_adversary.py` não tem switch para o caminho de segredo.** O
  docstring (`:260`) afirma que `CEO_ADVERSARY=0` desliga o enforcement; para
  `secret_in_command` isso é **falso** (`:156-158` só escolhe entre `deny` e
  `ask`, e ambos emitem `block` em `:254-271`). Ou o texto é corrigido, ou o
  hook ganha a chave — e aí ele vira candidato a INCLUIR-COM-ENV no perfil user,
  que é onde a defesa de exfiltração mais faria falta.
- **FU-F2 — `_CANONICAL_GUARDS` não é ciente de cerimônia.** 23 das 72 entradas
  são paths que num repo adopter pertencem ao adopter (`.github/workflows/*.yml`,
  `.github/CODEOWNERS`, `AGENTS.md`, `requirements.toml`, `scripts/install.sh`…).
  É o que empurra `check_codex_filewrite` e `check_pair_rail` para fora do perfil
  user. Uma lista de guards com escopo por cerimônia devolveria os dois.
- **FU-F3 — dois comentários defasados na base** (`:2` «~16+»; `:617` «45
  registrations» vs 47 reais). Mesma classe da OQ-E5, outro arquivo.
- **FU-F4 — o piso `10` dos dois oráculos de não-vacuidade é um literal solto.**
  Com este veredito sobra folga (17 contra 10, §4 #3 e #8), mas o número `10` foi
  escrito para casar com «os 10 declarados» — uma lista que §2 mostra não
  corresponder mais ao critério. Se o piso significa «o perfil ainda difere de
  forma relevante», ele deveria ser **derivado do spec** (`len(exclude_hooks)`),
  não um literal. Um veredito mais inclusivo que o meu (p.ex. incluir também os
  4 hooks de compaction/closeout, deixando 13) continua passando e a proteção
  vira decorativa antes de ficar vermelha.
- **FU-F5 — E.14j fica a 2 chaves de virar `scaffold`** (§4 #9).

---

**STATUS: DONE_WITH_CONCERNS**
