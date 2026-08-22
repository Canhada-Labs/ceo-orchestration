# W1-followup — sentinel de aprovação (DRAFT: preencher Data + assinar)

> **Por que este arquivo está AQUI e não em `w1-followup-ceremony/`.**
> `check_canonical_edit.py:1004-1014` define uma união FECHADA de padrões de
> sentinel, sem catch-all: um arquivo fora deles é tratado como ÓRFÃO e NÃO
> confiável. `PLAN-182/w1-followup-ceremony/approved.md` — o caminho que o
> draft anterior propunha — **não casa nenhum**. Este caminho casa
> `PLAN-*/wave-*-approved.md`. (O precedente `S319-approved.md` também não
> casava; aquela wave landou por PACK via bash, rota em que o PreToolUse
> nunca dispara — a lição S290, "deny por FERRAMENTA é teatro: Bash escapa".)

Plans: PLAN-182
Wave: W1-followup (cura estrutural do carrier + atribuição de projeto + fecho da classe M4)
Patch: .claude/plans/PLAN-182/w1-followup-ceremony/S321-CEREMONY.patch
Patch-sha256: 31938bed1bb3eea2893260328d6fb7433ecf4387aad05467974a3d5770d60d83
Anchor-SHA: <PREENCHER-NA-ASSINATURA — `git rev-parse HEAD`>
Data: <PREENCHER-NA-ASSINATURA>

> **Sem linhas `MANIFEST-*`, deliberadamente.** O land é por PATCH, não por
> pack `tree/` — e a própria nota do draft anterior avisa que um campo
> `MANIFEST-*` vazio mata o script de land e um campo mentiroso é pior que
> ausente. O binding aqui é o `Patch-sha256`, verificável com
> `shasum -a 256 -c`.
>
> **O `Anchor-SHA` fica em branco DE PROPOSITO.** Ele foi escrito com um
> valor concreto e ficou obsoleto no commit seguinte, o que e a prova de
> que este campo nao pode ser preenchido em preparacao: preencha-o com
> `git rev-parse HEAD` no momento da assinatura. O `OWNER-S321-LAND.sh`
> aborta no G3 se ele nao casar o HEAD. Reescrever um byte deste arquivo
> depois de assinar invalida o `.asc`
> ([[feedback-clean-rail-round-is-not-the-end]]).

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs <PREENCHER-NA-ASSINATURA>
Plans: PLAN-182
Scope:
  - .claude/adr/ADR-001-runtime-state-directory.md
  - .claude/hooks/SessionEnd.py
  - .claude/hooks/_lib/cost_envelope.py
  - .claude/hooks/_lib/policy.py
  - .claude/hooks/_lib/test_isolation.py
  - .claude/hooks/_lib/testing.py
  - .claude/hooks/check_notification.py
  - .claude/hooks/check_tier_policy_misrouting_24h.py
  - .claude/scripts/lessons.py
  - conftest.py
  - tests/unit/test_runtime_state_sandbox_confinement.py
<!-- END SIGNED SCOPE -->

Authorization: Owner-signed GPG detached signature
(`wave-w1-followup-approved.md.asc`), verificada contra os DOIS rails de
signer (`.claude/sentinel-signers.txt` + o registry YAML do ADR-121). Nenhum
path acima é kernel (`check_arbitration_kernel._KERNEL_PATHS`): este sentinel
sozinho basta, sem `CEO_KERNEL_OVERRIDE`.

## O que este pacote faz (11 arquivos, 4 mudanças de comportamento)

### 1. Fecha a janela do carrier — estruturalmente, não no perímetro

`_lib/runtime_paths.runtime_state_dir()` honra `CLAUDE_PROJECT_DIR_NATIVE` na
MAIOR precedência, acima do `HOME` que a camada de isolamento redireciona.
Nenhuma das duas enumerações que deveriam cobri-lo foi atualizada quando a W1
landou, e a cura shipada em `5fe41f8` é um `pop` no import do `conftest.py`.

- `_lib/test_isolation.py` ganha `WHOLE_DIR_OVERRIDE_CARRIERS` e neutraliza o
  carrier **no import**, sem restaurar dentro do processo. Fica FORA de
  `ALL_AUDIT_CARRIERS` de propósito: pertencer a ela significaria
  snapshot+restore ao fim da sessão, que é a variante MEDIDA como reabridora
  do vazamento.
- `_lib/testing.py`: `TestEnvContext.setUp` apaga o carrier, e o validador C3
  de `subprocess_env` passa a incluí-lo nos path-carriers verificados.
- `conftest.py`: o bloco perimetral de 61 linhas é REMOVIDO no mesmo commit.
  Os fixtures `_ceo_audit_isolation_*` (gate WS-A/C/E) ficam intactos — eles
  são importados num bloco separado, verificado.

### 2. Atribuição de projeto nos emissores (a segunda metade da W2)

A W1 curou ONDE o evento é gravado; isto cura O QUE ele carrega. Medido:
15.128 dos 15.208 eventos não-atribuíveis pós-W1 vinham de `policy_evaluated`
+ `policy_denied`. **A causa não era o scrub** (`project` está em
`_FEDERATION_ENVELOPE`, logo nas allowlists) **nem o env**: era o chamador
omitindo o kwarg, com o default do emissor em `""`.

- `_lib/policy.py`: helper `_project_label()` fail-open + os dois emissores.
- `check_notification.py`: `project=` no emissor de lifecycle.

Fail-open por construção: falha de resolução devolve `""` e o evento sai como
saía antes — atribuição é observabilidade, nunca motivo para derrubar uma
decisão de policy.

### 3. Fecha a classe M4 (re-derivação local do slug)

Os 4 sites canônicos que sobraram depois dos 9 não-canônicos curados em
`9de4efc`: `SessionEnd.py`, `_lib/cost_envelope.py`,
`check_tier_policy_misrouting_24h.py` e `lessons.py` (3 ocorrências).
`lessons.py` é o caso emblemático — ele **já importava** `runtime_paths` e
mesmo assim re-derivava o slug sem o traço inicial, aterrissando as lessons do
adopter num diretório IRMÃO da raiz da família.

Com este pacote: `derive-audit-family.py --assert-no-local-slug` sai **0**, e
sob `CEO_AUDIT_FAMILY_M4_REQUIRED=1` o gate PASSA — a classe fecha por
completo. O único `rp-allow:` é o fallback de último recurso do
`cost_envelope`, marcado na própria linha e com a razão escrita.

### 4. AC-7 do PLAN-182: a decisão SPEC v1-vs-v2, registrada

`ADR-001` Amendment 2. A decisão já estava TOMADA na prática (`SPEC/v1/*.md`
editados in-place, `SPEC/` com um único `v1/`) e nunca registrada — `grep -i
SPEC` no ADR-001 devolvia 2 hits, ambos irrelevantes. A emenda registra
**por que** in-place não quebra o contrato v1 (a localização já era um
parâmetro; mudou o default, não o parâmetro) e **o que teria exigido um v2**,
para que a linha seja testável e não questão de gosto.

## O marcador de dívida: INVERTIDO, não removido

**Correção sobre o draft anterior, que estava STALE em três lugares.** O
draft mandava REMOVER
`test_debt_marker_carrier_absent_from_isolation_enumeration` e avisava que o
caso "não dispara". Ambas as coisas deixaram de valer: o commit `26a39c5`
(posterior à preparação do pack) **renomeou e reescreveu** o caso para
`test_debt_marker_isolation_layer_does_not_yet_neutralise_carrier`, que
assere COMPORTAMENTO — e portanto **fica vermelho no land**, verificado.

Este pacote o **inverte** em vez de deletá-lo:
`test_isolation_layer_neutralises_ambient_carrier`. Mesma pergunta
comportamental, resposta esperada oposta. Deletar trocaria um marcador por
nada; inverter converte o marcador no guard de regressão que a cura merece.

**Leia isto antes de interpretar um vermelho durante a verificação:** com o
pacote aplicado o arquivo dá **3 passed**. Se você aplicar só parte dele, o
guard invertido fica vermelho — e isso é o guard funcionando, não regressão.

## Provas anexadas (executadas em árvore-sombra, clone de `c66a87a`)

| prova | resultado |
|---|---|
| carrier no ambiente + cura + perímetro removido | canário **VAZIO** (dir nem existe) |
| controle negativo: cura revertida por `git stash` | canário **[audit-log.lock, state]** |
| restauração do stash | `git diff --stat` **byte-idêntico** antes/depois |
| guard invertido, cura presente | 3 passed |
| guard invertido, cura revertida | **FAILED**, com a mensagem que nomeia a regressão |
| `--assert-no-local-slug` | 16 → 7 (commit `9de4efc`) → **0** (este pacote) |
| `CEO_AUDIT_FAMILY_M4_REQUIRED=1` | **EXIT 0** — a classe fecha |
| `--assert-migrated` | EXIT 0, inalterado |

## Residual declarado (assinado com o pacote)

1. **`python -m unittest` DIRETO continua vazando** em
   `.claude/hooks/tests/test_injection_salt.py` e
   `test_audit_family_two_projects.py` (canário = 2 cada). A escrita acontece
   no `atexit`, depois do teardown, e `test_injection_salt` sequer importa
   `_lib.testing` — o hunk do `TestEnvContext` não alcança. O CI é
   pytest-only por construção, então a exposição é o runner que o próprio
   repo manda não usar. **Fechar isso é decisão à parte, não esta cerimônia**
   (replicar o `pop`-no-import de
   `tests/unit/test_credential_rotation_emit.py:76-82`).
2. **Perda cosmética aceita:** um runner que chame `pytest.main()` várias
   vezes no mesmo processo vê o carrier removido até o processo sair.
   Restaurar mais cedo é perda de CORREÇÃO (medido: reabre o vazamento).
3. **O `Scope` inclui `conftest.py` e `tests/unit/...`, que NÃO são
   canônicos.** Estão ali porque o gate `touched − scope = ∅` opera sobre os
   paths TOCADOS, não sobre os guardados; um Scope que não cobre um path
   tocado aborta o land, e isso é o comportamento correto.
4. **O gate `touched − scope = ∅` não existe automatizado.** O
   `OWNER-S319-LAND.sh:76-89` faz outra coisa (verifica que todo alvo do
   MANIFEST existe na árvore) e nunca lê o bloco `Scope`. Se este land for
   por `git apply` + commit manual, **a conferência é do operador** — os 11
   paths do patch estão listados no Scope acima, na mesma ordem de
   `git diff --cached --name-only`.

## Limite honesto (inalterado por este pacote)

Isolar a suíte não muda nada sob o mesmo UID: um processo continua lendo o
dir `0700` e a chave `0600` do outro projeto. Fronteira real exigiria UID
separado ou chave fora do alcance do processo — fora de escopo por decisão
(`CLAUDE.md` §5).
