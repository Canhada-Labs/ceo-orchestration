# wave-s330-F — sentinel de aprovação (DRAFT: o SIGN preenche Data / Anchor-SHA / Approved-By e assina)

> Caminho casa `PLAN-*/wave-*-approved.md` (união fechada de padrões em
> `check_canonical_edit.py`). O binding é o `Patch-sha256` (land por PATCH, sem
> `MANIFEST-*`). O bloco `Scope:` é **DERIVADO** por
> `PLAN-183/w5-ceremony/finalize_patch.py` a partir de `git apply --numstat` —
> nunca escrito à mão. O `Anchor-SHA` é preenchido pelo `OWNER-S331-F-SIGN.sh`
> com `git rev-parse HEAD` no momento da assinatura; o `OWNER-S331-F-LAND.sh`
> aborta no G1 se não casar. Reescrever um byte deste arquivo depois de assinar
> invalida o `.asc`.

Plans: PLAN-169
Wave: wave-s330-F (PLAN-169 OQ-E5 — `templates/settings/settings.user.json` deixa de ser uma cópia manual da base e passa a ser DERIVADO dela por subtração declarada, com o spec vivendo na chave `_derivation` do próprio arquivo; junto vêm a reconciliação do FU-F-ACCEL, o ADR-197, o gate de paridade no `validate.yml` e as contagens de ADR que o `verify-counts.sh` cobra)
Patch: .claude/plans/PLAN-169/s330-ceremony-F/F.patch
Patch-sha256: TO-FILL-AT-FINALIZE
Patch-base: TO-FILL-AT-FINALIZE
Anchor-SHA: TO-FILL-AT-SIGN
Data: TO-FILL-AT-SIGN

## O que esta wave entrega

**Quatro arquivos canônicos** e **dezesseis não-canônicos** que viajam no mesmo
patch. O oráculo `--is-canonical` responde `1` para
`templates/settings/settings.user.json`, `.claude/adr/ADR-197-user-profile-derivation.md`,
`.claude/adr/README.md` e `.github/workflows/validate.yml`; `0` para os
dezesseis restantes. Todos entram por esta cerimônia porque o patch é atômico —
um gerador que landasse sem o gate, ou um ADR que landasse sem as contagens que
o CI cobra, seria uma janela vermelha.

1. **`templates/settings/settings.user.json`** (canônico) — o entregável.
   Deixa de ser cópia manual e passa a ser a saída de
   `gen-settings-user-template.py` sobre `settings.base.json` mais o spec de
   subtração embutido na chave `_derivation`. O roster vai de **20 para 30
   registrações** (29 basenames).

   O que a classificação por mérito mediu (`4f4df3a`), e que motiva a wave: o
   `_comment` do arquivo afirmava remover **"exatamente 10"** hooks; eram **26**.
   Dos 10 nomeados, **só 5** sustentam o critério que o próprio comentário
   declara, e **2 não pertencem à lista por nenhuma leitura**
   (`check_scratchpad_access.py`, `check_skill_reference_read.py`). Dos 16
   restantes, **13 já faltavam na v1.0.0** — a cópia nasceu incompleta. A
   proveniência citada (`PLAN-122 WS-4`) **não existe em ref git nenhum**.
   Veredito: **17 EXCLUIR / 9 INCLUIR**, cada exclusão com classe, razão e
   evidência que RESOLVE.

2. **`.claude/scripts/gen-settings-user-template.py`** — o gerador.
   `--check` (default) / `--write` / `--json` / `--spec` para bootstrap.
   **rc 1 = drift, rc 2 = INFRA** (spec ausente ou sem a chave) — fail-loud nos
   dois, nunca um default silencioso.

3. **`scripts/build-plugin.py`** (FU-F-ACCEL, decisão do Owner de 2026-08-30:
   mesmo patch) — a tabela `ACCEL` deixa de existir. Ela era uma **terceira
   cópia** das registrações dos quatro aceleradores do PLAN-128, e divergente:
   fixava `review_loop.py` em 60 s e `turbo_sessionstart.py` em 10 s enquanto
   `settings.base.json` **e** o `.claude/settings.json` vivo deste repositório
   rodam 15 s e 5 s. Depois que o roster do template cresceu, cada um dos quatro
   passava a ser registrado **duas vezes** no `hooks.json` do plugin. A
   composição virou função pura (`compose_plugin_hooks`) e o marcador de dívida
   foi **INVERTIDO** em guard permanente.

4. **`.claude/adr/ADR-197-user-profile-derivation.md`** (canônico) + o índice
   regenerado — a decisão registrada. **ADR novo, não AMEND**, pela recomendação
   medida da §6 da classificação: um AMEND exige um ADR-pai que decida a coisa
   emendada, e **nenhum existe** (o único que menciona `--ceremony user` é o
   ADR-155-AMEND-1, e só para dizer o que o install pula).

5. **`.github/workflows/validate.yml`** (canônico, OQ-F3) — step
   `User-template derivation (PLAN-169 F — regen+diff)`, ao lado dos dois steps
   de idempotência de gerador que já existiam. Contrato: **0** in-sync / **1**
   drift / **2** input inutilizável; qualquer não-zero reprova.

6. **Os dois testes e a fixture** — **87 casos** no arquivo nuclear (61 no
   snapshot do writer; 66 com o guard invertido do FU-F-ACCEL; 73 com os guards
   da rodada 1 do pair-rail; 87 com os da rodada 2). Cada salto é cura de
   achado, nomeada em `rail-round-*.md`. Controle vermelho por fixture congelada
   (`settings.user.pre-F.json`, o template de `1c34eb5`) contra a própria
   afirmação do `_comment` antigo: 17 registrações ausentes e 2 campos
   divergentes, nomeados. E `test_install_user_skips_governance_hooks.py` passa
   a derivar a lista de hooks de governança **do spec** — antes ele carregava
   uma segunda cópia congelada da lista de 10, e por isso não podia detectar o
   erro que esta wave corrige (o bloqueador §4b do DESIGN-F).

7. **`CLAUDE.md` e 8 arquivos de documentação** — a contagem de ADRs, 197 → 198,
   em 15 sítios. Não é escolha: `verify-counts.sh` e `check-claude-md-claims.py`
   **rodam no `validate.yml`**, e um patch que adiciona um ADR sem eles nasce
   com o CI vermelho. No `CLAUDE.md` viaja **o numeral e nada mais** — a
   narrativa da §5 continua sendo trabalho de closeout.

<!-- BEGIN SIGNED SCOPE -->
Scope:
  - TO-FILL-AT-FINALIZE
<!-- END SIGNED SCOPE -->

## Residual declarado

- **A superfície de hooks do adopter `--ceremony user` MUDA.** O próximo
  `upgrade.sh` registra **10 hooks novos**. É o ponto da OQ-E5, não efeito
  colateral, mas é mudança de produto em campo. Riscos por hook na classificação
  §5; dois merecem repetição: `check_config_change.py` entra com
  `CEO_CONFIG_CHANGE_GUARD=1` **explícito** (o default vive em código, e uma
  registração é só tão advisory quanto a setting que ela lê), e
  `codex_review_user_code.py` é **DETECT-ONLY** por default — nunca roda Codex
  sem opt-in.
- **O plugin passa a rodar `review_loop.py` com 15 s e `turbo_sessionstart.py`
  com 5 s.** Alinhado à base e ao repositório vivo, mas é mudança de
  comportamento real: os valores antigos (60 e 10) não tinham fonte que os
  sustentasse.
- **+22.360 B no `settings.json` de todo adopter `--ceremony user` novo**
  (OQ-F4), quase tudo `reason`/`evidence`. Declarado, não escondido: encurtá-los
  é rota disponível; removê-los não é — são o que torna a subtração auditável.
- **`EXPECTED_TEMPLATE_REGISTRATIONS_USER=20`** em
  `s329-ceremony-E/EXPECTED-BASELINE.txt:182` fica **DEFASADO POR DECISÃO** do
  Owner (2026-08-30). É baseline histórica de cerimônia já landada, não é
  consumida por workflow nenhum, e re-rodar o `finalize-E.sh` pós-wave falha por
  desenho. Não reescrever.
- **FU-F-ADRGATE (achado desta wave, fica ABERTO).** `check-adr-chain.py` e
  `generate-adr-index.py` **não rodam em CI** — grep em `.github/workflows/` e
  em `validate-governance.sh`: zero. Consequências medidas: o índice de
  `.claude/adr/README.md` estava congelado em **170 ADRs** com **198** no disco
  (28 entraram sem regeneração), e `check-adr-chain.py` sai **rc 1 com 11 erros
  no main** (5 ADRs sem campo `Status:`, 2 `Supersedes` apontando para um ADR
  ainda `ACCEPTED`). **Medido: o ADR-197 não acrescenta nenhum erro** — a saída
  normalizada da sombra é idêntica à do main. A regeneração do índice traz
  **27 linhas que não são desta wave**; declarado aqui para que o revisor não
  procure a wave que as criou.
- **O spec é auto-descritivo, e isso é circular por desenho.** O gerador lê o
  spec do artefato que ele mesmo escreve. As duas saídas são explícitas:
  `--spec <path>` para bootstrap e rc 2 fail-loud se o arquivo sumir ou perder a
  chave. Um arquivo-irmão foi **medido e rejeitado**: `check-install-profiles.py`
  exige bijeção entre `templates/settings/*.json` e hook stacks, e o irmão a
  quebra (reproduzido com controle positivo, DESIGN-F §3.3).
- **TOCTOU entre `--check` e um editor concorrente não é tratado.** O gate é de
  CI e de pre-commit, não um lock.
- **O keyset da paridade não vigia matcher** (classificação §0), e a identidade
  de um hook nem sempre é o basename `.py` (DESIGN-F §3.1). Ambos declarados no
  ADR-197 como pontos cegos.
- **O critério do spec declara o próprio ESCOPO, e isso foi achado do rail.**
  Lido como bicondicional ele é falso: **dez** dos 29 hooks que o perfil retém
  têm sítio de bloqueio, quase todos desde a v1.0.0. Ele governa a decisão de
  EXCLUIR entre os 26 candidatos que a classificação pesou — e agora diz isso.
  Junto vem `blocking_inclusions`: os **cinco** hooks bloqueantes que ESTA wave
  acrescenta (`accel_dispatch`, `check_config_change`, `check_scratchpad_access`,
  `codex_review_user_code`, `review_loop`), cada um com a rota que o adopter
  realmente tem. O revisor achou UM; o censo mecânico que se seguiu achou os
  cinco.
- **O ADR-197 entra como `PROPOSED`.** O flip para `ACCEPTED` é cerimônia
  própria: a ratificação real é o `.asc` sobre este sentinel, não o commit que
  reescreve o campo — o mesmo que ADR-194 e ADR-196 registraram.
