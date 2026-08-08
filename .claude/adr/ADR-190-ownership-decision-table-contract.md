---
adr_id: ADR-190
title: A tabela de decisão de propriedade é O contrato — dimensões, enum de 4 vereditos, INV-1..4 e a assimetria SPEC/PROTOCOL
status: ACCEPTED
proposed_at: 2026-08-07
accepted_at: 2026-08-07
proposed_by: CEO (S297 — AC-10 do PLAN-167, cumprido pelo PLAN-168 W3)
decided_by: Owner (assinatura GPG da cerimônia do PLAN-168)
risk_tier: A
debate_required: true
related_plans: [PLAN-167, PLAN-168]
related_adrs: [ADR-155, ADR-155-AMEND-1]
---

# ADR-190 — Propriedade de superfície condicional é decidida pela TABELA, executada pelos scripts

## §1 Contexto

O PLAN-167 (`7c0828a`) substituiu dezenas de `if`s espalhados por
`install.sh`/`upgrade.sh` por uma decisão única: `_ownership_verdict()` em
`scripts/_framework_manifest_set.sh`, função **pura** das dimensões
observadas, devolvendo `"<VERDICT> <HASH_SOURCE>"`. Os scripts **observam →
chamam → executam**; eles não decidem. O PLAN-168 fechou os follow-ups
(fiação de CI, INV-4, este ADR). Este registro existe para que a próxima
pessoa que "conserte uma assimetria" tenha onde ler que ela é **decidida**,
não acidental.

Autoridades, em ordem:
- **Valores:** `scripts/tests/ownership_table.tsv` — "THIS FILE IS THE TRUTH".
- **Racional e legalidade:** `docs/ownership-decision-table.md`.
- **Decisão executável:** `_ownership_verdict()` — e SÓ ela.
- **Oráculos:** `test-ownership-verdict-unit.sh` (decisão, milissegundos) e
  `test-ownership-table.sh` (observação/execução, ~25 min de installs reais);
  `test-protocol-pointer-inv4.sh` (INV-4 executável). CI: unit + controles
  por-PR em `smoke-install.yml`; e2e nightly em `ownership-nightly.yml` com
  gate de conjunto (`ownership-nightly-gate.sh` vs
  `ownership-expected-reds.txt`).

## §2 Decisão

### §2.1 As 10 dimensões

`surface · prior_record · live_type · live_content · source_has · mode ·
ceremony · operation · skip_requested · fault` — definidas, com domínios e
regras de legalidade (R-01..R-10), em `docs/ownership-decision-table.md` §2.
Uma célula é um ponto legal desse produto; a TSV enumera as classes de
equivalência (R-10).

### §2.2 O enum final tem QUATRO vereditos

`DELIVER · REFRESH · PRESERVE_OWNED · PRESERVE_UNOWNED`

- A OQ-9 (ratificada pelo Owner, 2026-08-07) colapsou `OMIT_RECORD` em
  `PRESERVE_UNOWNED`: os dois diziam "sem registro no disco" e diferiam só
  pela coluna `prior_record` — membro redundante de enum é onde dois ramos
  discordam sobre qual se aplica.
- **`ABORT_SURFACE` NÃO é veredito.** É resultado de OBSERVAÇÃO/EXECUÇÃO do
  harness (INV-3: falha de execução nunca avança o registro). A função nunca
  o devolve; um ADR que o listasse como veredito contradiria o código.

### §2.3 As quatro invariantes cross-surface (INV-1..4)

- **INV-1** — continuidade em install rerun não muda digest registrado fora
  do conjunto de continuidade.
- **INV-2** — serialização `LINK` só cobre paths que JÁ eram `LINK` antes do
  run (o symlink do adotante nunca vira registro de entrega).
- **INV-3** — falha de execução nunca avança o registro (`ABORT_SURFACE` é
  esse evento, nomeado).
- **INV-4** — install e upgrade geram conteúdo **byte-idêntico** para a mesma
  superfície. Fechada pelo PLAN-168 W2: o ponteiro `PROTOCOL.md` é gerado
  pela ÚNICA função compartilhada (`_render_protocol_pointer*` em
  `_framework_manifest_set.sh`); heredoc privado em caller é REGRESSÃO desta
  invariante. Corolário pós-INV-4: em linhas de continuidade o digest
  canônico e o prior record são os MESMOS bytes — `HASH_PRIOR_RECORD` e
  `HASH_CANONICAL_POINTER` colapsam num só claim, e o harness trata os dois
  nomes como equivalentes SÓ quando os candidatos aliasam
  (docs §2.4, "Hash-name aliasing").

### §2.4 A assimetria deliberada SPEC vs PROTOCOL

- **`SPEC/v1` editado = FORK** ⇒ a rota forçada **refresha** (é o contrato de
  compliance publicado; ADR-155-AMEND-1 §4).
- **`PROTOCOL.md` editado = CONTEÚDO do adotante** ⇒ **preserva** (prosa
  editável; sobrescrever é a perda S238 que a decisão (iii) do ADR-155
  fechou).

É a assimetria que mais convida um "conserto" futuro. Ela é **decidida**.
Quem quiser mudá-la emenda ESTE ADR e refaz o debate — não "alinha" os dois
ramos num PR.

- **`degraded` (PLAN-168 W2) não é exceção à preservação de `edited`:** é a
  constatação de que o corpo com `{{PROTOCOL_SOURCE}}` literal é lixo que o
  PRÓPRIO framework produziu (upgrade pré-fix). Reconhecimento por
  **reconstrução exata de template** (nunca substring, nunca hash estático —
  o corpo embute TARGET/PROFILE/STACK da invocação), qualquer desvio ⇒
  `edited` ⇒ preservado. Cura = `REFRESH` com backup. Doutrina r20
  (`legacy_pristine`) aplicada ao ponteiro; célula própria na TSV
  (OWN-0092..0094), R-04b.

### §2.5 Relação com o ADR-155-AMEND-1

**Emendado, não revogado.** A enumeração compartilhada (decisão (i)) e a
propriedade por registro de entrega continuam válidas; este ADR acrescenta o
contrato da DECISÃO (tabela + função + oráculos) e a INV-4 sobre o CONTEÚDO
que os dois lados produzem.

### §2.6 Células conhecidas-abertas (estado ao aceitar este ADR)

Abertas — **3**, com causa, protegidas pelo gate de conjunto (encolher =
falha; verde-total = a tabela mudou ⇒ PARAR):
- `OWN-0016` — defeito de PRODUTO (aberto).
- `OWN-0024` / `OWN-0027` — defeitos do TESTE (células de fault de execução
  que o harness ainda não instancia fielmente).

Fechada — histórico, não expectativa:
- `OWN-0074` — defeito de PRODUTO fechado pelo PLAN-168 W2: era a INV-4 se
  manifestando no digest gravado (`HASH_CANONICAL_POINTER` que não batia com
  o disco). Um ADR que a listasse como aberta nasceria stale.

## §3 Consequências

- Adicionar um ramo que decide propriedade LOCALMENTE em
  `install.sh`/`upgrade.sh`/`doctor.sh`/`uninstall.sh` reabre a classe que o
  PLAN-167 fechou — é veto de revisão, não estilo.
- Mudanças na tabela/enum/dimensões exigem: debate L3 + atualização em
  `docs/ownership-decision-table.md` + TSV + oráculos verdes + este ADR
  emendado. Os quatro andam juntos ou a mudança não anda.
- O conjunto esperado de vermelhos (`ownership-expected-reds.txt`) é parte do
  contrato: o CI compara o CONJUNTO exato (nunca `--map`, nunca rc cru) e
  qualquer status TIMEOUT/ESCAPE/AMBIG falha imediatamente.

## §4 Blast radius

`scripts/install.sh` · `scripts/upgrade.sh` · `scripts/_framework_manifest_set.sh`
· `scripts/doctor.sh` · `scripts/uninstall.sh` · os 4 oráculos/gates de teste ·
`smoke-install.yml` · `ownership-nightly.yml` · adotantes em campo (a cura do
degraded reescreve, com backup, um arquivo que upgrades antigos corromperam).
