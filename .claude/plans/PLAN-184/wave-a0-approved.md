# wave-a0 — sentinel de aprovação (DRAFT: o Owner preenche Data/Approved-By/Anchor-SHA ao assinar)

> **Por que este arquivo está AQUI.** `check_canonical_edit.py:1004-1014`
> define uma união FECHADA de padrões de sentinel, sem catch-all: um arquivo
> fora deles é tratado como ÓRFÃO e NÃO confiável. Este caminho casa
> `PLAN-*/wave-*-approved.md`.
>
> **Um sentinel, dois planos.** O campo `Plans:` é header de continuação — o
> parser valida pelo bloco `Scope:` (paths), não pelo plano. Verificado antes
> de montar assim. É o "pacote de uma assinatura" que o Owner pediu.

Plans: PLAN-184, PLAN-174
Wave: A0 (matriz de Python no push + backstop nightly) + W2 (wire do ceremony-lint)
Patch: .claude/plans/PLAN-184/s322-ceremony/S322-CEREMONY.patch
Patch-sha256: 644d6d21870cf9db32b264a1961c73a44ce9847cabaf02b3bb190d74ac7c00f5
Anchor-SHA: ANCHOR-PLACEHOLDER
Data: DATA-PLACEHOLDER

> **O `Anchor-SHA` fica em branco DE PROPÓSITO.** Ele é o HEAD no instante da
> assinatura; preenchê-lo em preparação garante que estará obsoleto. O
> `OWNER-S322-LAND.sh` aborta no G3 se ele não casar o HEAD. Reescrever um
> byte deste arquivo depois de assinar invalida o `.asc`.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs FINGERPRINT-PLACEHOLDER
Plans: PLAN-184, PLAN-174
Scope:
  - .claude/scripts/local/install-ceremony-precommit.sh
  - .github/workflows/ceremony-lint.yml
  - .github/workflows/validate.yml
<!-- END SIGNED SCOPE -->

Authorization: Owner-signed GPG detached signature (`wave-a0-approved.md.asc`),
verificada contra o rail de signer rastreado (`.claude/sentinel-signers.txt`).
Nenhum path acima é kernel (`check_arbitration_kernel._KERNEL_PATHS`): este
sentinel sozinho basta, sem `CEO_KERNEL_OVERRIDE`.

## O que este pacote faz (3 arquivos, 2 waves independentes)

### 1. PLAN-184 A0 — matriz de Python de 4 para 2 no `push`, COM backstop

Decisão do Owner já registrada (S321): **A0 primeiro**, antes de W1/W2 do 184.

O corte: `hook-tests-python-matrix` passa a rodar só as versões de
**fronteira** (3.9 e 3.12) no gatilho `push`; no `pull_request` e no
`schedule` novo, as **quatro**. Rende ~US$3,15/dia de um teto medido de
~US$4,04/dia.

**A segunda metade é o que impede a A0 de ser uma regressão, e ela não
estava no enunciado da alternativa.** Medido antes de cortar:

| | |
|---|---|
| runs de `validate.yml` na janela, por evento | `{'push': 167}` — **100%** |
| `schedule:` no workflow | **não existia** |

Sem o cron, remover 3.10/3.11 do `push` não seria "trocar latência de
detecção por dinheiro" — seria **PERDA de cobertura**: as duas versões
deixariam de ser exercitadas em QUALQUER gatilho. Por isso o patch adiciona
`schedule: - cron: "37 7 * * *"` junto. O minuto é off-mark de propósito
(não `:00`/`:30`): a hora cheia é onde todo mundo agenda.

Validado na árvore-sombra, não no repo vivo (o hook canônico bloqueia a
edição direta, corretamente):

| verificação | resultado |
|---|---|
| `yaml.safe_load` → gatilhos | `['pull_request', 'push', 'schedule']` |
| cron parseado | `[{'cron': '37 7 * * *'}]` |
| matriz | expressão `fromJSON(github.event_name == 'push' && … \|\| …)` |
| contagem de jobs | 7 (inalterada) |
| `actionlint` | **exit 0** |

### 2. PLAN-174 W2 — o wire do ceremony-lint, que já estava pronto e travado

Os dois artefatos estavam **rastreados e prontos** em
`PLAN-174/staged-w2/` desde a S316, esperando um bloqueio que **não existe
mais**: o pin do codex foi re-pinado em `32e29b1` (0.147.0), e o próprio
PLAN-174 registra que "o texto deste plano e a memória do projeto é que não
foram atualizados, e o bloqueio sobreviveu como claim envelhecida por duas
sessões". É a terceira reincidência dessa classe.

- `.github/workflows/ceremony-lint.yml` — a perna de CI (2 jobs:
  `ceremony-lint`, `shellcheck-ceremony`). `actionlint` exit 0.
- `.claude/scripts/local/install-ceremony-precommit.sh` — a perna LOCAL,
  **advisory e opt-in por construção** (bypassável com `--no-verify`; a
  doutrina do debate r1 é explícita: *CI é O GATE*, o hook local é
  conveniência de operador e nunca conta como camada de enforcement).
  `bash -n` OK, modo `100755` carregado no patch.

**Armadilha encontrada e desarmada na promoção.** O cabeçalho do
`install-ceremony-precommit.sh.staged` declara "remover este cabeçalho de
**8 linhas** ao mover" — e o `#!/bin/bash` está na **linha 7**. Cortar 8
decapitaria o shebang. O promotor detecta o início do conteúdo por
**conteúdo** (primeira linha do shebang / do `name:`), nunca pela contagem
que o próprio cabeçalho declara: os números reais foram **6** linhas para o
installer e **36** para o `ceremony-lint.yml`.

## O que este pacote NÃO faz

- **Não flipa nenhum status de plano.** `PLAN-184` está `draft` e
  `reviewed → done` é ilegal; o flip é decisão do Owner, em commit próprio.
- **Não toca `scripts/install.sh`.** A segunda metade do A7 do PLAN-183
  (parametrizar a identidade no install-time) fica para a fila — ver §Fila.
- **Não toca `.claude/settings.json` nem `templates/settings/settings.base.json`.**
  O A4 do PLAN-183 (skills de VETO em `name-only`) fica para a fila, agora
  com um insumo que não existia: `veto_skill_map.derive_veto_skills()` devolve
  **27** skills com VETO derivadas dos organogramas, contra as 2 que o plano
  nomeava.

## Fila de cerimônia que este pacote deixa aberta (medida, não estimada)

| item | paths canônicos | por que não entrou aqui |
|---|---|---|
| PLAN-183 A4 | `.claude/settings.json`, `templates/settings/settings.base.json` | precisa da decisão de quais das 27 skills derivadas viram override |
| PLAN-183 A7 (2ª metade) | `scripts/install.sh` | parametrizar identidade no install-time; a 1ª metade landou em `4f750f0` |
| PLAN-182 decisão 3 | `.claude/hooks/_lib/runtime_paths.py` + 9 consumidores | expor `__main__`; recon mediu `BLOCKED_CANONICAL` |
| PLAN-182 rota do installer | `templates/settings/settings.base.json`, `scripts/upgrade.sh` | **decisão do Owner pendente** (§Decisão abaixo) |
| PLAN-179 W2/W4 | 9 paths (`SessionEnd.py`, `audit_emit.py`, `SPEC/v1/audit-log.schema.md`, …) | o pack ficou MONTÁVEL em `9779287`, mas montar é passo separado |
| achado novo (a1) | `scripts/upgrade.sh` | `upgrade.sh` contém "github" **zero** vezes: adotantes EXISTENTES nunca recebem `.github/` em upgrade nenhum |
| achado novo (a6) | `SPEC/v1/audit-log.schema.md` | sem uma ação `hook_invoked`, a taxa de censura é incomputável para 47 dos 49 hooks |

## Decisão do Owner ainda pendente (não decidi no seu lugar)

`PLAN-182`, item `[P0]` da rota do installer: acrescentar ou não a chave
`CLAUDE_PROJECT_DIR_NATIVE` em `settings.base.json`. Recomendação do CEO já
registrada no plano com evidência: **NÃO acrescentar** — ela viajaria
HARDCODED ao adopter e é a variável de MAIOR precedência, então pinar errado
quebraria a isolação que a W1 comprou. O veículo pronto, se a decisão for
outra, é `_T54_BASELINES_JSON` em `upgrade.sh:153-188`, nunca o merge de
hooks.

## Residual declarado

1. **O `schedule:` novo passa a gastar dinheiro todo dia.** O corte no `push`
   rende ~US$3,15/dia; o nightly de 4 versões adiciona um custo fixo que a
   §2 do PLAN-184 não orçou (ela mediu só `push`). A A0 continua
   líquida-positiva pelo teto medido, mas o número exato do nightly só sai
   depois do primeiro fire — e a W3 do plano exige 7 dias-calendário de
   billing de qualquer forma.
2. **`fromJSON` com expressão multi-linha** é válido (actionlint exit 0) mas
   é a primeira ocorrência desse padrão neste repo. Se o `schedule` disparar
   e a matriz vier vazia, o job passa VACUAMENTE — o primeiro nightly precisa
   ser inspecionado à mão para confirmar 4 entradas, não 0.
3. **A perna local do 174 é opt-in e ninguém a instala automaticamente.**
   Ela só existe depois de o operador rodar o script uma vez por clone. Isso
   é por design (CI é o gate), mas significa que landar este pacote não muda
   nada no comportamento local de quem não rodar.
