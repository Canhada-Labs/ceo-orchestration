> # ⛔ SUPERSEDED (S321, 2026-08-22) — NÃO ASSINE A PARTIR DESTE ARQUIVO
>
> O material canônico desta cerimônia é agora:
>
> - **sentinel:** `.claude/plans/PLAN-182/wave-w1-followup-approved.md`
>   (o caminho mudou porque `PLAN-182/w1-followup-ceremony/approved.md`
>   **não casa** nenhum padrão da união FECHADA de
>   `check_canonical_edit.py:1004-1014` — seria tratado como ÓRFÃO e
>   não-confiável)
> - **patch:** `S321-CEREMONY.patch` (11 arquivos), com `Patch-sha256`
>   amarrado no sentinel
>
> **Por que este arquivo ficou stale em menos de 24 h:** ele foi
> preparado em `8531562`, e o commit `26a39c5` — que veio DEPOIS —
> renomeou e reescreveu o marcador de dívida para asserir COMPORTAMENTO.
> Tudo o que este arquivo diz sobre "o marcador não dispara" e sobre
> removê-lo passou a ser falso: ele **fica vermelho no land** (medido), e
> o pacote novo o **inverte** em guard permanente em vez de deletá-lo.
>
> O escopo também cresceu: de 2 arquivos para 11 — o pacote absorveu a
> atribuição de projeto nos emissores (W2), o fecho da classe M4 (W3) e a
> emenda do ADR-001 que fecha o AC-7. Assinar um lote é mais barato que
> assinar quatro.
>
> Preservado como registro do que se propunha, e porque as PROVAS de
> ordenação (import → coleta → fixture → corpo) que ele documenta
> continuam válidas.

# W1-followup-approved — sentinel do follow-up da W1 (DRAFT — assinar como `approved.md`)

> **DRAFT preparado, NÃO assinado.** O `.asc` é gerado na sessão de execução:
> `gpg --armor --detach-sign --yes approved.md`. Reescrever qualquer byte deste
> arquivo depois de assinar INVALIDA a assinatura — inclusive trocar o
> `Anchor-SHA` (lição `feedback-clean-rail-round-is-not-the-end`).

Plans: PLAN-182
Wave: W1-followup (cura estrutural do carrier ADR-001 na camada de isolamento)
MANIFEST-entradas: <PREENCHER-NO-LAND>
MANIFEST-sha256: <PREENCHER-NO-LAND>
Anchor-SHA: <PREENCHER-NO-LAND>
Data: <PREENCHER-NO-LAND>

> `MANIFEST-entradas` / `MANIFEST-sha256` só têm significado se o land for por
> PACK (`w1-followup-ceremony/tree/` + `MANIFEST.sha256`), no formato que
> `OWNER-S319-LAND.sh` verifica em G0. Se o Owner aplicar os dois hunks
> diretamente (Edit sob o sentinel), remova as duas linhas ANTES de assinar — um
> campo vazio faz o script de land morrer em *"sentinel sem binding do
> manifesto"*, e um campo mentiroso é pior que ausente.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs <PREENCHER-NO-LAND>
Plans: PLAN-182
Scope:
  - .claude/hooks/_lib/test_isolation.py
  - .claude/hooks/_lib/testing.py
<!-- END SIGNED SCOPE -->

Authorization: Owner-signed GPG detached signature (`approved.md.asc`),
verificada contra os DOIS rails de signer (`.claude/sentinel-signers.txt` + o
registry YAML do ADR-121). Nenhum dos dois caminhos é kernel
(`check_arbitration_kernel._KERNEL_PATHS`): este sentinel sozinho basta, sem
`CEO_KERNEL_OVERRIDE`.

## O que este pack muda

**Move a cura do vazamento de sandbox do perímetro para a estrutura.**
`_lib/runtime_paths.runtime_state_dir()` (W1) honra `CLAUDE_PROJECT_DIR_NATIVE`
na MAIOR precedência, acima do `HOME` que a camada de isolamento redireciona.
Nenhuma das duas enumerações que deveriam cobri-lo foi atualizada quando a W1
landou; a cura shipada em `5fe41f8` é um `pop` no import do `conftest.py` raiz.

1. **`_lib/test_isolation.py`** ganha `WHOLE_DIR_OVERRIDE_CARRIERS` — a metade
   que faltava da enumeração que o próprio módulo declara viver "HERE, exactly
   once" — e neutraliza o carrier **no import**, sem restaurar dentro do
   processo. Fora de `ALL_AUDIT_CARRIERS` de propósito: pertencer a ela
   significaria "snapshot + restore ao fim da sessão", que é a variante MEDIDA
   como reabridora do vazamento.
2. **`_lib/testing.py`**: `TestEnvContext.setUp` passa a apagar o carrier (fecha
   a janela do CORPO do teste sob `python -m unittest`, onde essa classe é a
   única camada existente) e o validador C3 de `subprocess_env` passa a incluí-lo
   no conjunto de path-carriers verificados.

**REMOVER (não é canônico) é edição do MESMO commit:** o bloco import-time do
`conftest.py` raiz e o caso
`test_runtime_state_sandbox_confinement.py::test_debt_marker_carrier_absent_from_isolation_enumeration`.
Os dois primeiros casos desse arquivo — o canário e o seu controle positivo —
PERMANECEM: são o guard comportamental real.

## Decisão registrada: REMOVER, não REDIRECIONAR

Três leituras do código e duas medições:

- `AUDIT_DIR_CARRIERS` **não redireciona nada por si**: o `SET` vem de
  `audit_carrier_overrides()`, que hardcoda três chaves e não itera a tupla.
  REDIRECT exigiria editar também essa fonte única e `subprocess_env` — três
  superfícies canônicas em vez de duas.
- A regra de qual metade usar já está escrita no módulo (linhas 113-123):
  override que o `TestEnvContext` não re-aponta por teste é LIMPO, nunca fixado
  num caminho de sessão.
- Fixar o TOPO da precedência num caminho de sessão tornaria o braço DEFAULT de
  `runtime_state_dir()` inalcançável pela suíte inteira.
- A escrita que vaza é no DESLIGAMENTO do interpretador (medido: dir vazio antes
  do import, vazio depois do import, com as duas entradas depois do exit).
- A/B com controle: restaurar no teardown do fixture de sessão devolve o
  vazamento (`[audit-log.lock, state]`); não restaurar deixa o canário vazio.

Production code mantém o override integralmente — nada aqui toca
`_lib/runtime_paths.py`.

## Provas anexadas ao pack

- Árvore-sombra com controle NEGATIVO: mesmo `conftest` mínimo (SEM `pop`), mesmo
  teste `assert True` — módulo **original** ⇒ canário `[audit-log.lock, state]`;
  módulo **proposto** ⇒ canário **vazio**. Variante com `from _lib import
  audit_emit` em escopo de módulo (janela de coleta) ⇒ canário **vazio**.
- Ordenação verificada empiricamente: `conftest-import → test-module-import →
  corpo do fixture de sessão → corpo do teste` (uma cura no fixture chegaria
  dois passos tarde demais para a janela de coleta).
- Baseline pré-land no repo real: `test_live_audit_isolation.py` +
  `test_runtime_state_sandbox_confinement.py` ⇒ `EXIT=0`, 19 passed / 1 skipped;
  canário dos 4 módulos sob pytest ⇒ `EXIT=0`, 53 passed, canário vazio;
  `derive-audit-family.py --assert-migrated` ⇒ `EXIT=0`, "0 módulo(s) runtime".
- `subprocess_env(`: 24 call sites, **0** passam o carrier — o hunk do C3 é
  no-op comportamental hoje.

## Residual declarado (assinado com o pack)

1. **`python -m unittest` DIRETO continua vazando** em
   `.claude/hooks/tests/test_injection_salt.py` e
   `.claude/hooks/tests/test_audit_family_two_projects.py` (canário = 2 cada).
   Medido COM o hunk do `TestEnvContext` simulado: continua 2. A escrita é no
   `atexit`, depois de o `tearDown` já ter restaurado o carrier; e
   `test_injection_salt` sequer importa `_lib.testing`. Fechamento possível fora
   desta cerimônia (edição de arquivo de teste): replicar o `pop`-no-import de
   `tests/unit/test_credential_rotation_emit.py:76-82`. O CI é pytest-only por
   construção.
2. **O marcador de dívida NÃO dispara.** Ele assere sobre `AUDIT_DIR_CARRIERS`
   (a metade "SET"), e a cura correta não põe o nome ali — verificado:
   `NATIVE in AUDIT_DIR_CARRIERS -> False`. Ele é removido DELIBERADAMENTE, não
   porque ficou vermelho. Foi ancorado na tupla errada e teria permanecido verde
   através da cura que existia para anunciar.
3. **Perda cosmética aceita:** um runner que chama `pytest.main()` várias vezes
   no mesmo processo vê o carrier ficar removido até o processo sair. Restaurar
   mais cedo é perda de CORREÇÃO (item 4 das provas).

## Limite honesto (inalterado por este pack)

Isolar a suíte não muda nada sob o mesmo UID: um processo continua lendo o dir
`0700` e a chave `0600` do outro projeto. Fronteira real exigiria UID separado
ou chave fora do alcance do processo — fora de escopo por decisão (CLAUDE.md §5).

## Variante B — se `CLAUDE.md` §5 for corrigido no mesmo commit

§5 hoje afirma que o marcador de dívida "fica VERMELHO no dia em que a cura
estrutural landar" e que a cerimônia canônica é "o fechamento definitivo" do
resíduo `unittest`. As duas frases ficam FALSAS com este land. Se o Owner
corrigir §5 no mesmo commit, acrescente a linha ao bloco assinado **antes** de
gerar o `.asc`:

```
  - CLAUDE.md
```

e re-gere o `MANIFEST`/`Anchor-SHA`. Um Scope que não cobre um path tocado faz o
gate `touched − scope = ∅` abortar o land — que é o comportamento correto.
