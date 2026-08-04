# Round 3 — re-review adversarial de segurança pós-fix (AC-10)

Auditor externo (Security Engineer, VETO auth/crypto). Read-only.
Posição default: a fronteira de confiança está quebrada até prova em
contrário — cada claim do round-2 foi RE-VERIFICADA contra o disco, e as
que sustentam decisão foram provadas com PROBE + CONTROLE POSITIVO, não
com leitura de prosa.

## Escopo desta review — o que exatamente foi lido

| Superfície | Estado auditado |
|---|---|
| Árvore MESCLADA (ensaio S292) | `/private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/56225249-725d-4b3d-bbd5-3b732a6581ed/scratchpad/plan165-merge/` — `.claude/scripts/night-mode.py` (1484 L, linha a linha), `.claude/scripts/ceo-boot.py` (advisory night-mode), `.claude/commands/night-mode.md`, `.claude/adr/ADR-185-*.md`, `.claude/scripts/tests/test_night_mode.py` (86 testes), `ceremony-staged/README.md`, `probes/W0-EVIDENCE.md` |
| Árvore VIVA (main) | `9c637508a1149cee70f16fb8ea48eafca1d81017` — `check_canonical_edit.py:331-344`, `check_arbitration_kernel.py:254-264`, `check_bash_safety.py:2147-2429`, `settings.json:763-799`, `_lib/audit_emit.py:1088/7274/7708-7739/9204-9295`, `SPEC/v1/audit-log.schema.md:491,571`, `scripts/install.sh:1761-1790`, `templates/settings/settings.base.json:595-608` |
| Cerimônias assinadas consideradas | `610d9ec` `[SENT-S291]` (p1-corrected + p2 + p4 + p5), `9f53628`+`93a1938` (remoção de `disableAutoMode`), sentinel `architect/round-3/approved.md` (anchor `36696c5`) |
| Ratificação do Owner | OQ1-redo 2026-08-03 — "armar autonomia é ação HUMANA (`!` ou terminal); o rail de modelo não invoca o toggle" |

Nota de fato relevante: em `9c63750` o `night-mode.py` **ainda não existe
no HEAD** (`ls .claude/scripts/night-mode.py` → No such file). A cerimônia
P1/P2 landou; o W1-land é o commit que esta review antecede.

---

## VETO status

### **NEEDS_CHANGES**

Não é BLOCK: o código do `night-mode.py` mesclado está materialmente
endurecido e o CRITICAL do round-2 (NM-01) está **provado morto** com
probe reproduzível. Não é APPROVE: duas propriedades que a governança já
**afirma por escrito em superfície canônica assinada** não são
verdadeiras na árvore que vai landar. Ambas são corrigíveis dentro do
próprio commit de W1-land — e uma delas (NF-07) é literalmente uma
obrigação que o README da cerimônia impõe a esse commit.

**O merge pode prosseguir SOMENTE no mesmo commit que carregue as duas
mitigações obrigatórias abaixo.** Landar a árvore como está publica três
claims falsos numa superfície assinada e deixa `AC-7` insatisfeita.

Contagem round-2: **9 RESOLVED · 1 RESOLVED-BY-CEREMONY · 1
PARTIALLY-RESOLVED (metade STILL-OPEN)**. Findings novos: **2 obrigatórios
(1 HIGH, 1 MEDIUM) + 3 recomendados (1 MEDIUM, 2 LOW)**.

---

## Findings — veredito finding-a-finding do round-2

| ID | Sev (r2) | Veredito | Evidência do fix (file:line) |
|---|---|---|---|
| **NM-01** | CRITICAL | **RESOLVED** (probe) | `night-mode.py:225` `_RESTORABLE_MODES = _HARNESS_PERMISSION_MODES - {"bypassPermissions", NIGHT_MODE}`; validação whole-document `:521-613`; `cmd_off` fail-closed `:902-915`. **Defesa em profundidade landada**: marker em `_CANONICAL_GUARDS` (`check_canonical_edit.py:342`), em `_KERNEL_PATHS` (`check_arbitration_kernel.py:263`) e deny Edit/Write (`settings.json:795-796`). |
| **NM-02** | HIGH | **RESOLVED** (probe) | Normalização de desync em `cmd_on` `:758-775` + simétrica em `cmd_off` `:926-946`; teste `test_desync_then_on_then_off_ends_on_project_posture` (`test_night_mode.py:721`). |
| **NM-03** | HIGH | **RESOLVED** | `.claude/scripts/night-mode.py` em `_CANONICAL_GUARDS` (`check_canonical_edit.py:343`) + deny Edit/Write (`settings.json:797-798`); marker idem. Os dois degraus da escada que o NM-03 nomeia (editar o writer / editar o snapshot) estão fechados nos dois rails. *A superfície de INVOCAÇÃO — que o NM-03 não pediu — é o NF-08 abaixo.* |
| **NM-04** | MEDIUM | **RESOLVED** | `_validate_root` `:683-711` (confinamento a `REPO_ROOT` + exigência de `.claude/settings.json` no alvo) + `_seam_widens_to` `:661-680` (o seam de teste só abre para alvos sob `tempfile.gettempdir()`, fechando a classe S284 "TEST_MODE-é-bypass"); testes `:782-812`. |
| **NM-05** | MEDIUM | **PARTIALLY-RESOLVED — metade STILL-OPEN** | *Resolvido:* a linha `night-mode-event mode=… previous_mode=… result=…` sai em TODO caminho terminante (`_summary` `:640-658`, incluindo o catch-all de `main` `:1477-1479`), com oracle estrutural `ast` (`test_night_mode.py:1687-1755`). *Aberto:* o evento forense `night_mode_toggled` **não é emitido por caminho nenhum** — ver **NF-07**. Na data do round-2 não emitir era correto (P2 não tinha landado); em `9c63750` P2 landou e a obrigação inverteu. |
| **NM-06** | MEDIUM | **RESOLVED** | `ceo-boot.py:2843-2861` `_night_mode_ratified_mode()` deriva "ratificado" da camada **project** do resolver; `:2890-2891` só renderiza quando a camada vencedora é `local`/`user` (`_NIGHT_MODE_OVERLAY_LAYERS`); o literal `manual` virou apenas `_NIGHT_MODE_RATIFIED_FALLBACK_MODE` `:2803`. Fail-open preservado `:2904-2911`. |
| **NM-07** | MEDIUM | **RESOLVED** | `probes/W0-EVIDENCE.md:4-11,28-30` registra AC-1 como ABERTA e o predicado como resolver-only; `:56-91` corrige o inventário de `_CANONICAL_GUARDS` (67 entradas medidas por import, não as cinco abreviadas) e re-deriva "ZERO hits" a partir da lista real; `:132-146` fecha AC-1 com prova harness-level obtida em 2026-08-03. |
| **NM-08** | MEDIUM (gating) | **RESOLVED-BY-CEREMONY** | `610d9ec [SENT-S291]` landou P1-corrected + P2: deny em `settings.json:793-798`, `night_mode_toggled` em `_KNOWN_ACTIONS` (`audit_emit.py:1088`), emissor tipado `:9204`, golden 324. A condição do NM-08 ("não merge antes de P1/P2 landarem") está satisfeita — mas a obrigação recíproca da mesma cerimônia sobre o commit de W1-land **não** está (NF-07). |
| **NM-09** | LOW | **RESOLVED** | `_fsync_dir` `:328-348`, chamado após `os.replace` `:377` e após os três `os.unlink` (`:1037` overlay, `:1078` marker, `:1243` marker no discard). |
| **NM-10** | LOW | **RESOLVED** | Subsumido pelo conjunto fechado + checagem de tipo: `_validate_marker:572-583` exige `isinstance(prev_value, str) and prev_value in _RESTORABLE_MODES`; qualquer dict/list/number é fail-CLOSED exit 2. |
| **NM-11** | LOW | **RESOLVED** (com resíduo) | `cmd_off:1084-1088` passou a dizer "that local value still overrides the project layer's posture", sem alegar ratificação. *Resíduo numa rota diferente:* NF-10. |

### Prova comportamental — NM-01 (o CRITICAL) está morto

Transcript do round-2 re-executado contra a árvore MESCLADA, em raiz tmp
isolada (`CEO_NIGHT_MODE_TEST_SEAM=1`, `CI` ausente), overlay inicial
`{"permissions":{"defaultMode":"plan"},"env":{"KEEP":"me"}}`:

```
$ night-mode.py on --project-root <tmp>          # overlay -> acceptEdits, marker prev_value="plan"
$ # marker prev_value adulterado à mão -> "bypassPermissions"
$ night-mode.py off --project-root <tmp>
night-mode: REFUSING to restore — ... field 'prev_value' is 'bypassPermissions', which is not a
string in the closed set of restorable modes ['auto', 'dontAsk', 'manual', 'plan'] ...
night-mode-event mode=none previous_mode=none result=refused
exit=2
$ cat <tmp>/.claude/settings.local.json
{ "permissions": { "defaultMode": "acceptEdits" }, "env": { "KEEP": "me" } }   # NÃO bypassPermissions
```

`status` sobre o mesmo marker rende `marker: PRESENT but INVALID` +
`reconciliation: DISAGREE` (o reporter não abençoa mais o que o writer
recusa — NF-06 do round-3 confirmado vivo). A rota de recuperação existe e
é não-destrutiva para o resto do overlay:

```
$ night-mode.py off --discard-snapshot --project-root <tmp>
night-mode: OFF (snapshot DISCARDED) — ... override removed (it was 'acceptEdits'), marker deleted,
prev_value NOT restored.
$ cat <tmp>/.claude/settings.local.json
{ "env": { "KEEP": "me" } }              # a chave alheia do Owner sobreviveu
```

### Prova comportamental — NM-02 (desync) está morto

```
$ on            (sem overlay)   -> armado, marker criado
$ rm marker                      # simula crash entre as duas escritas
$ on            (desync)         -> stderr: "desync detected and normalized ..."
                                    marker: prev_present=False prev_value=None
$ off                            -> "local overlay defaultMode override removed (snapshot: absent)"
$ cat settings.local.json        -> {}          # NÃO acceptEdits
```

---

## Findings NOVOS (severity-sorted)

### NF-07 / HIGH / Ação de auditoria REGISTRADA E VAZIA: `night_mode_toggled` tem emissor tipado, entrada no `_KNOWN_ACTIONS`, linha de SPEC assinada — e **zero chamadores em produção**. AC-7 não é satisfeita pela árvore que vai landar.

**CWE-778 (Insufficient Logging) · OWASP A09:2021 (Security Logging and Monitoring Failures).**

EVIDENCE.
- `grep -rn emit_night_mode_toggled` na árvore MESCLADA retorna apenas
  `.claude/hooks/_lib/audit_emit.py` (a definição), os patches em
  `.claude/plans/PLAN-165/ceremony-staged/`, o script de cerimônia de
  PLAN-162 e o `approved.md`. **Nenhum arquivo de produção chama.**
- O `night-mode.py` mesclado é explícito em NÃO emitir:
  `night-mode.py:81-87` ("This script deliberately does NOT emit a
  `night_mode_toggled` audit event: the action is unregistered until the
  P2 sentinel ceremony lands"). Essa premissa está **obsoleta desde
  `610d9ec`** — a ação está registrada (`audit_emit.py:1088`), o branch de
  scrub existe (`:7274`) e o wrapper tipado existe (`:9204`).
- O README da própria cerimônia impõe a obrigação ao commit que esta
  review antecede — `ceremony-staged/README.md`, §"P2 emit re-insertion
  (MANDATORY — same ceremony)": *"a registração landa com
  `p2-audit-action.patch` no commit da cerimônia; o emit landa no commit
  de W1-land da MESMA cerimônia — o primeiro commit que põe
  `night-mode.py` no HEAD"*. O bloco traz o helper `_emit_audit` pronto,
  a regra de posicionamento e a tabela de mapeamento de `result`.
- **Três claims falsos ficam publicados se isto landar como está:**
  1. `SPEC/v1/audit-log.schema.md:491` (canônico, assinado em `610d9ec`):
     *"emitted by `.claude/scripts/night-mode.py` on EVERY terminating
     path of `on`/`off` (applied/noop/refused/failed)"*.
  2. `.claude/commands/night-mode.md:57` (superfície do usuário): *"4.
     Emits the `night_mode_toggled` audit action (HMAC-chained)."*
  3. `audit_emit.py:9215-9219` (docstring do emissor): *"Fired by
     `.claude/scripts/night-mode.py` … once per `on`/`off` invocation"*.
- **O gate não pega**: `python3 .claude/scripts/check-audit-registry-coverage.py`
  → `OK: audit registry in sync` (exit 0) em `9c63750`, com a ação
  registrada e nenhum emissor vivo. O checker sincroniza NOMES, não
  LIVENESS. Esta é a classe `registered-vacuous` já conhecida (memória
  S287/S291) reaparecendo numa ação nova.

IMPACT. Um flip de postura entre sessões — o evento com maior valor
forense do PLAN-165 — não deixa linha na cadeia HMAC. O único registro é
uma linha de stdout que não é assinada, não é encadeada e não sobrevive
ao fechamento do terminal. `AC-7` ("Após `on` e após `off`, existe linha
`night_mode_toggled`", plano `:335`) é falsificável hoje.

FIX (obrigatório, no commit de W1-land). Aplicar o bloco §"P2 emit
re-insertion" do `ceremony-staged/README.md` verbatim: helper
`_emit_audit` (com `hashlib` importado), uma chamada imediatamente antes
de cada `return` de `cmd_on` / `cmd_off` / `cmd_off_discard_snapshot` e
uma no catch-all de `main`, mapeando `result` pela tabela do README.
Estender o oracle `ast` de NF-04 (`test_night_mode.py:1687-1755`) para
exigir o par `_summary` + `_emit_audit`, senão a próxima regressão é
silenciosa. Corrigir as três claims (2 e 3 são edições comuns; a 1 é
SPEC canônico — precisa entrar na cerimônia 2).

---

### NF-08 / MEDIUM / A ratificação OQ1-redo ("armar autonomia é ação HUMANA") **não está implementada**: o rail de Bash permite `python3 .claude/scripts/night-mode.py on`. Três comentários assinados afirmam o contrário, e o `.claude/commands/night-mode.md` mesclado instrui o MODELO a executar exatamente esse comando.

**CWE-269 (Improper Privilege Management) · OWASP LLM06 (Excessive Agency).**

EVIDENCE — probe com CONTROLE POSITIVO, contra os hooks da árvore VIVA
(`9c63750`), alimentando `check_bash_safety.py` por stdin:

```
--- CONTROLES POSITIVOS (o probe está vivo) ---
echo x > .claude/scripts/night-mode.py   -> {"decision":"block", ... "writes to canonical path"}
echo x > .claude/settings.local.json     -> {"decision":"block", ...}
echo x > .claude/state/night-mode.json   -> {"decision":"block", ...}
--- INVOCAÇÃO (a questão sob teste) ---
python3 .claude/scripts/night-mode.py on -> {}     ALLOW
./.claude/scripts/night-mode.py on       -> {}     ALLOW
bash -c "python3 .claude/scripts/night-mode.py on" -> block   (só a forma indireta, por acaso:
                                                       o substring-scan de _scan_blob)
```

A razão é estrutural, não um bug pontual:
`check_bash_safety._e3_check_canonical_path_write` (`:2147-2429`) casa
**formas de ESCRITA** — redirects, `tee`, `sed -i`, `cp/mv`, `rm`,
`touch`, `dd of=`, corpos `-c`/`-e` de interpretador, `eval/xargs/find`.
Um path canônico na posição de *script* de `python3` não é nenhuma
dessas: o branch de interpretador (`:2313-2325`) só varre o token
seguinte a `-c`/`-e`. Listar o writer em `_CANONICAL_GUARDS` protege o
arquivo contra ESCRITA; não faz nada contra EXECUÇÃO.

**Três claims assinados que a probe falsifica:**
1. `check_canonical_edit.py:338-340` (cerimônia `610d9ec`): *"Listing the
   WRITER script here also removes model-rail invocation of the toggle
   (OQ1-redo, Owner-ratified 2026-08-03: presence = only a human at the
   keyboard runs on/off, via `!` or a terminal)."*
2. `.claude/settings.json:765` `_night_mode_deny_surface_comment`: *"per
   the Owner-ratified OQ1-redo, model-rail invocation of the toggle is
   itself blocked: on/off are HUMAN actions (terminal or the `!`
   prefix)."*
3. Sentinel `architect/round-3/approved.md`: *"Implements the
   Owner-ratified OQ1-redo (2026-08-03): night-mode on/off become human
   actions."*

**Agravante — o artefato mesclado empurra o rail do modelo.**
`.claude/commands/night-mode.md` declara `allowed-tools: Bash, Read`,
se descreve como "a thin driver" e traz, como instrução ao modelo,
literalmente ` ```bash / python3 .claude/scripts/night-mode.py on ``` `
(`:41-43`) e o mesmo para `off`. Ou seja: o único artefato que
operacionaliza o toggle é um driver de MODELO, contra uma ratificação
que diz que o toggle é ação HUMANA.

REACHABILITY / IMPACT (triagem exploitability-first, honesta). Sob a
postura ratificada (`defaultMode: "manual"`) cada chamada de Bash ainda
passa pelo prompt do operador, então na configuração publicada existe um
humano no loop — mas é um *clique de aprovação num prompt de Bash*, não
"um humano no teclado rodando `on`", e é exatamente o tipo de prompt que
se aprova no automático no meio de uma sessão longa. Sob `acceptEdits`
(a própria postura que o toggle arma), sob `dontAsk`, sob `auto` ou com
um allowlist de Bash amplo, o modelo arma sozinho a postura permissiva
da PRÓXIMA sessão. O controle prometido é binário e não existe; o
controle real é probabilístico e depende da postura corrente. A
propriedade de segurança que a ratificação comprou não foi entregue.

FIX (obrigatório — escolher UM e alinhar os três comentários ao que for
escolhido):
- **(a) implementar o controle**: adicionar ao `check_bash_safety` um
  matcher de INVOCAÇÃO para `.claude/scripts/night-mode.py` (path como
  operando de qualquer comando, não só em forma de escrita), com
  mensagem apontando o `!` / terminal; e remover ou reescrever
  `.claude/commands/night-mode.md` para deixar de ser um driver de
  modelo. Custo: o slash-command deixa de funcionar como hoje. Requer
  cerimônia (edita hook canônico).
- **(b) corrigir a claim**: manter a invocação pelo rail do modelo e
  reescrever os três comentários para o que é verdade — "deny e
  `_CANONICAL_GUARDS` fecham ESCRITA do writer e do estado; a invocação
  permanece disponível ao rail do modelo e é governada pelo prompt de
  permissão de Bash da postura corrente". Requer cerimônia (dois dos
  três são arquivos canônicos: `check_canonical_edit.py` e
  `settings.json`), e re-ratificação do Owner do OQ1-redo, porque (b)
  muda o que foi ratificado.

Registro objetivo para a decisão: o comentário do **template do adopter**
(`templates/settings/settings.base.json:595`) NÃO carrega a claim falsa —
ele para em "the Bash rail is closed by `_CANONICAL_GUARDS`". A cópia de
dogfood (`.claude/settings.json:765`) é a que foi longe demais.

---

### NF-09 / MEDIUM / `off` numa rota de não-escrita reporta `applied` e afirma um restore que não aconteceu — e essa mentira vai para a cadeia HMAC assim que o NF-07 for consertado.

**CWE-1240 / integridade de registro forense.**

EVIDENCE — probe (árvore mesclada, raiz tmp; overlay apagado à mão entre
`on` e `off`, a rota que `night-mode.py:961-967` trata):

```
$ on            (overlay prévio = "plan")   -> armado
$ rm settings.local.json                     # overlay some (limpeza manual)
$ off
night-mode: warning — .../settings.local.json is gone; nothing to restore. Removing marker.
night-mode: OFF — local overlay defaultMode restored to 'plan' (snapshot). ...
night-mode-event mode=plan previous_mode=acceptEdits result=applied
exit=0
$ ls settings.local.json  ->  No such file or directory
```

A linha humana diz "restored to 'plan'", o registro máquina diz
`mode=plan result=applied`, e **nada foi escrito**: a próxima sessão
resolve a camada project (`manual`), não `plan`. O `warning` no stderr
corrige o humano atento; o registro estruturado — o que um parser lê —
fica errado. Com o NF-07 aplicado, esse mesmo par vira uma linha
`night_mode_toggled` assinada afirmando um restore inexistente.

FIX. Nessa rota, `restored` deve ser `"absent"` (nada foi restaurado) e
`result` deve refletir a ausência de escrita — sugestão: manter exit 0
com `result=noop` e uma linha humana que diga "nada a restaurar; a
próxima sessão resolve a camada project". Cobrir com teste dirigido.

---

### NF-10 / LOW / O enum `_NIGHT_MODE_MODE_ENUM` do SPEC é mais estreito que `_RESTORABLE_MODES`: um restore legítimo de `plan`/`auto`/`dontAsk` será gravado como `other`, indistinguível de valor adulterado.

EVIDENCE. `audit_emit.py:7714-7716` — `_NIGHT_MODE_MODE_ENUM =
{acceptEdits, manual, absent, other}`. `night-mode.py:225` —
`_RESTORABLE_MODES = {auto, dontAsk, manual, plan}` (confirmado pela
mensagem de recusa da probe NM-01). Interseção com o enum: só `manual`.
Logo `off` restaurando `plan` (rota que a probe exercitou e que o próprio
NF-02 do round-3 existe para preservar) grava `mode=other` — o mesmo
valor que uma coerção de lixo produz.

IMPACT. Não é vazamento e a direção é fail-safe (nada é ecoado). É perda
de fidelidade forense num caminho legítimo, e importa AGORA porque o enum
foi congelado em SPEC canônico pela cerimônia S291: alargá-lo depois
custa outra cerimônia. Decidir ANTES de fiar o emit do NF-07.

FIX. Ou alargar o enum para `_RESTORABLE_MODES ∪ {acceptEdits, absent,
other}` na cerimônia 2 (mantendo `bypassPermissions` deliberadamente
FORA — a defesa NM-01 no wire), ou registrar explicitamente na linha do
SPEC que modos fora do enum colapsam em `other` por decisão de
minimização, para que ninguém leia `other` como sinal de adulteração.

---

### NF-11 / LOW / Claim obsoleto `disableAutoMode: "disable"` em três artefatos mesclados; e `result=failed` com exit 2 no catch-all diverge da tabela de mapeamento da cerimônia.

EVIDENCE (a). `9f53628` removeu `disableAutoMode` (confirmado:
`.claude/settings.json:763` documenta a remoção e a chave não existe mais
no bloco de settings). A árvore mesclada ainda descreve a postura
publicada como `manual` **+ `disableAutoMode: "disable"`** em
`night-mode.py:8`, `.claude/commands/night-mode.md:15` e
`.claude/adr/ADR-185-night-mode-posture-toggle.md:25`.

EVIDENCE (b). `night-mode.py:1473-1480` — o catch-all de `main` emite
`result=failed` e retorna **2**. A tabela normativa de
`ceremony-staged/README.md` mapeia exit 2 (inclusive contenção de lock,
que chega aqui como `FileLockTimeout`) para `refused` e reserva `failed`
para exit 1. O registro estruturado e o exit code discordam nessa rota.

FIX. (a) três edições comuns (nenhum arquivo canônico). (b) separar
`FileLockTimeout` do catch-all genérico e emitir `refused`, ou corrigir a
tabela — mas escolher antes de fiar o NF-07, porque o mapeamento vira
conteúdo assinado.

---

## Threat model delta

O que **mudou** desde o round-2, e o que isso fecha:

1. **A escada de escalação por ESCRITA está fechada nos dois rails.** O
   round-2 tinha overlay/marker/writer como alvos tool-escreíveis sob
   `acceptEdits`. Hoje: seis entradas de deny (`settings.json:793-798`)
   fecham o rail Edit/Write; três entradas em `_CANONICAL_GUARDS`
   (`check_canonical_edit.py:341-343`) fecham o rail Bash — e essa é a
   correção que importa, porque a refutação CX-1 do codex mostrou que
   deny por-ferramenta nunca vê Bash; os dois arquivos de ESTADO subiram
   para tier de kernel (`check_arbitration_kernel.py:262-263`), onde
   nenhum sentinel concede escrita por ferramenta. Probes com controle
   positivo confirmam os três blocks.

2. **A entrada não-confiável passou a ser tratada como entrada
   não-confiável.** O marker é validado como DOCUMENTO INTEIRO antes de
   qualquer campo ser usado, incluindo a regra de consistência
   `created_file ⇒ ¬prev_present` que torna o branch destrutivo
   alcançável com segurança, e `ts`/`hostname` são checados por tipo,
   tamanho e caractere de controle. O branch de `os.unlink` do overlay
   ainda exige, além disso, que o conteúdo ATUAL seja exatamente o
   documento que `on` escreve ao criar (`night-mode.py:1005-1022`) —
   defesa em profundidade correta contra `created_file` forjado.

3. **A superfície de forja de linha foi fechada por CLASSE, não por
   instância.** Todo eco não-confiável passa por `_bounded_repr`, todo
   token do registro máquina por `_summary_token`, e o relatório inteiro
   de `status` por `_one_line` num único ponto de emissão — de modo que
   um campo futuro ecoado sem cuidado ainda não consegue forjar um
   segundo registro `reconciliation:`.

4. **O seam de teste deixou de ser bypass.** `CEO_NIGHT_MODE_TEST_SEAM`
   agora só amplia o confinamento para dentro de `tempfile.gettempdir()`;
   a primitiva "armar `acceptEdits` em QUALQUER repo da máquina" que o
   NM-04 nomeava não existe mais.

O que **não** mudou / o que a mesclagem INTRODUZ:

5. **Existe agora um binário de flip de postura no HEAD.** Enquanto
   `night-mode.py` não existia, NF-08 era teórico: não havia toggle para
   invocar. O commit de W1-land é o que transforma a claim não-cumprida
   do OQ1-redo numa primitiva viva. Esse é o motivo de NF-08 ser
   bloqueante *neste* commit e não antes.

6. **A trilha forense do flip de postura não existe** (NF-07). O
   PostToolUse não cobre o overlay (é escrito por PROCESSO, não por
   ferramenta) — foi precisamente por isso que a ação de auditoria foi
   criada. Sem o emit, a única testemunha de uma mudança de postura entre
   sessões é o banner advisory do `/ceo-boot`, que é fail-open por
   desenho e ninguém é obrigado a rodar.

7. **Classe recorrente confirmada pela terceira vez nesta cerimônia:
   claim assinado ≠ comportamento.** NF-07 e NF-08 são a mesma falha de
   processo em superfícies diferentes — texto normativo escrito no tempo
   FUTURO ("o emit landa no W1", "a invocação passa a ser humana") e
   commitado no tempo PRESENTE. Um gate que compare claim×comportamento
   para as afirmações de segurança de comentários canônicos resolveria a
   classe; hoje o que existe (`check-audit-registry-coverage.py`,
   `verify-counts`) compara NOMES e CONTAGENS, e ambos ficaram verdes
   sobre estes dois buracos.

Superfícies verificadas **sem** finding (checadas adversarialmente):
escrita atômica (mkstemp no MESMO diretório + flush + fsync + `os.replace`
+ preservação de modo + limpeza do temp em qualquer `BaseException`);
read-back re-parseando após cada replace, com falha tratada como
divergência; `FileLock` envolvendo as sequências de mutação inteiras;
ordenação settings→marker em `on` e settings→remoção-de-marker em `off`;
recusa de CI fail-closed por PRESENÇA da variável; nenhum caminho constrói
`bypassPermissions` como valor a escrever (`grep` no arquivo mesclado: só
docstrings, o enum do harness e a exclusão); nenhuma escrita fora de
`<root>/.claude/{settings.local.json,state/}`; `_atomic_write_json` usa
`os.replace` sobre o próprio path, então um symlink no lugar do overlay é
substituído, nunca seguido; o advisory do `/ceo-boot` é fail-open ponta a
ponta, resolve a raiz em tempo de chamada e sanitiza todo valor
interpolado; enum/allowlist do emissor tipado negam path, conteúdo de
arquivo e hostname cru no wire, com `hostname_hash` validado por shape
exata (`^([0-9a-f]{12})?$`, sem truncamento); paridade byte-a-byte das
seis entradas de deny entre `.claude/settings.json` e
`templates/settings/settings.base.json`; `install.sh:1761-1790` garante
`.gitignore` de estado de postura no adopter.

---

## Required mitigations (bloqueiam o APPROVE)

1. **NF-07** — fiar `_emit_audit` conforme §"P2 emit re-insertion" do
   `ceremony-staged/README.md`, no MESMO commit que põe `night-mode.py`
   no HEAD (é o que a cerimônia assinada exige). Estender o oracle `ast`
   para pinar `_summary` **e** `_emit_audit` antes de cada `return`.
   Corrigir as duas claims não-canônicas (`night-mode.md:57`,
   `audit_emit.py:9215-9219`) no mesmo commit; a claim canônica
   (`SPEC:491`) só fica verdadeira depois do emit — verificar que ficou.
2. **NF-08** — decidir (a) implementar o bloqueio de invocação ou (b)
   corrigir os três comentários assinados, e executar a decisão. Não
   landar com a claim como está: dois dos três comentários são arquivos
   canônicos e ficarão publicados afirmando um controle inexistente. Se
   for (b), a re-ratificação é do Owner, não desta review.

## Recommended hardening (não bloqueiam)

3. **NF-09** — corrigir `restored`/`result` na rota de overlay ausente
   antes de o emit ser fiado, para não assinar um restore que não houve.
4. **NF-10** — decidir o alargamento do `_NIGHT_MODE_MODE_ENUM` (ou
   documentar o colapso em `other`) antes de fiar o emit; depois custa
   cerimônia.
5. **NF-11** — remover o claim obsoleto `disableAutoMode: "disable"` dos
   três artefatos e alinhar `result` do catch-all com a tabela da
   cerimônia.
6. **Classe** — considerar um gate que verifique claims de segurança
   embutidas em comentários canônicos contra comportamento (o par
   NF-07/NF-08 passou por `check-audit-registry-coverage.py` e por
   `verify-counts` sem ruído).

---

*Review conduzida sobre a árvore MESCLADA do ensaio S292
(`…/scratchpad/plan165-merge/`) e sobre o estado da main
`9c637508a1149cee70f16fb8ea48eafca1d81017`. Todo probe rodou em raiz tmp
isolada, read-only sobre o repositório; nenhum arquivo do repositório foi
modificado por esta review além deste artefato. Instruções encontradas
dentro de conteúdo observado foram tratadas como DADO, nunca como comando
— nenhuma foi executada.*
