# W179-W24-approved — sentinel do PACOTE D, PLAN-179 W2+W4 (DRAFT — assinar como W179-W24-approved.md)

> Assinatura em um passo:
> `bash .claude/plans/PLAN-179/OWNER-W179-W24-SIGN.sh`
> (preenche Anchor/Data/Approved-By, assina INLINE e imprime o proximo comando).

Plan: PLAN-179
Wave: W2 (ledger de fronteira de trabalho) + W4 (governanca do estado duravel)
Anchor-SHA: TO-FILL-AT-SIGN
Data: TO-FILL-AT-SIGN
Approved-By: @Canhada-Labs TO-FILL-AT-SIGN

<!-- Rotulos ASCII-safe de proposito: o parser de sentinel casa o rotulo por
     PREFIXO ASCII seguido de `[^:]*:`. Prosa acentuada DEPOIS do rotulo ja
     abortou um G3 com o campo correto preenchido (licao S326). -->

## Autorizacao de governanca

- **Debate L3 cumprido:** round-1 na S312 (`PLAN-179/debate/round-1/consensus.md`,
  3x ADJUST / 0 VETO, veredito PROCEED) com as 9 emendas de consenso aplicadas
  ao plano. `status: reviewed` ratificado pelo Owner em 2026-08-18 (`a71229e`).
- **Emenda 8.2 (escopo da cerimonia):** UM sentinel cobre TODOS os paths
  tocados — nao apenas o ADR. O bloco `## Scope` abaixo e verificado
  MECANICAMENTE contra o `MANIFEST.sha256` do pack pelo gate G2b do land
  script; divergencia em qualquer direcao aborta o land.
- **Decisao do Owner de 2026-08-25 (S328, AskUserQuestion, verbatim):**
  «3 acoes — registra ledger_entry_rejected (Recomendado)». Este pacote
  executa essa decisao; a alternativa de 2 acoes fica registrada como
  descartada, nao como residual.

<!-- BEGIN SIGNED SCOPE -->

## Scope

<!-- SCOPE-BLOCK — gerado do MANIFEST.sha256 do pack; nao editar a mao.
     Regenerar com:  sed 's/^[0-9a-f]\{64\}  //' staged-w24/MANIFEST.sha256
     (aplicando o PACKMAP ao unico path mapeado). -->
```
.claude/adr/ADR-195-work-boundary-persistence.md
.claude/data/audit-registry.golden.txt
.claude/hooks/_lib/audit_emit.py
.claude/hooks/_lib/ledger_provenance.py
.claude/hooks/check_ledger_checkpoint.py
.claude/hooks/tests/test_audit_emit_api_contract.py
.claude/hooks/tests/test_audit_emit_plan163_lifecycle_actions.py
.claude/hooks/tests/test_check_ledger_checkpoint.py
.claude/hooks/tests/test_codex_egress_proof_telemetry.py
.claude/hooks/tests/test_git_bypass_guard.py
.claude/hooks/tests/test_ledger_provenance.py
.claude/hooks/tests/test_template_dogfood_parity.py
.claude/hooks/tests/test_w5_scrub_enforcement.py
.claude/settings.json
CHANGELOG.md
CLAUDE.md
INSTALL.md
README.md
README.pt-BR.md
SPEC/v1/audit-log.schema.md
docs/ARCHITECTURE.md
docs/CTO-GUIDE.md
docs/FAQ.md
docs/GUIA-COMPLETO.md
docs/README.md
npm/README.md
templates/settings/settings.base.json
```

<!-- END SIGNED SCOPE -->

## O que este pacote faz

**W2 — ledger de fronteira de trabalho.** Um hook novo
(`.claude/hooks/check_ledger_checkpoint.py`, PreToolUse/Bash, **ADVISORY por
construcao** — nao existe braco de deny no modulo) observa fronteiras de
trabalho e registra checkpoints. O gatilho deriva de **PATHS**, nunca de
`resolve_plan_id`: essa e a emenda r1-C6 do debate, e ela e verificada por um
teste de nivel **AST** que PROIBE o hook de chamar `resolve_plan_id`. Sem
isso a W2 re-herdaria exatamente a causa-raiz que o PLAN-179 existe para
curar (o censo do ADR-153: 2 eventos `plan_transition` em 12.515 linhas, os
dois de outra sessao).

**W4 — governanca do estado duravel.** `.claude/hooks/_lib/ledger_provenance.py`
traz tags de proveniencia, um write-gate **fail-CLOSED** e verificacao
pos-delecao. `ADR-195-work-boundary-persistence.md` e o registro de doutrina,
abrindo com a matriz de 3 opcoes (emenda 8.5) e com estrategia de saida
escrita (a W2 e *Embedded*).

**As 3 acoes de auditoria.** `audit_emit._KNOWN_ACTIONS` vai de **327 para
330** com `ledger_checkpoint_recorded`, `ledger_checkpoint_skipped` e
`ledger_entry_rejected`. Cada uma tem allowlist **deny-by-default** + branch
de scrub, e **nenhuma** entra em `_EMIT_GENERIC_PASSTHROUGH`. A terceira e a
que fecha o degrade: `_lib/ledger_provenance.py` procura
`emit_ledger_entry_rejected`, e sem ela `scanner_unavailable`, `oversize` e
`malformed_input` ficariam breadcrumb-only (so `reason="scanner_hit"` tinha
fallback via `emit_prompt_injection_detected`). Com a decisao do Owner, esse
residual **deixa de existir** em vez de ser declarado.

**SPEC/v1 v2.59.** Tres linhas por acao mais a entrada de historico. A versao
e v2.59 e nao v2.57: o SPEC vivo ja carrega v2.56 (este plano), v2.57
(PLAN-174/SENT-S318) e v2.58 (PLAN-182/SENT-S319). O artefato viaja no pack
com nome plano (`spec-v1-audit-log.schema.md`) porque `.claude/settings.json`
nega `Edit(SPEC/**)` e o glob casa ate uma copia dentro do pack — o deny esta
CERTO, e o destino real vive no `PACKMAP.txt`.

**Registracao nos DOIS settings.** `.claude/settings.json` **e** o espelho
`templates/settings/settings.base.json`. Foi exatamente esse o buraco que a
suite completa pegou no `staged-w01`: sem o espelho, o adopter recebe o
arquivo com o hook morto. O teste de paridade template/dogfood e quem denuncia.

**Contagens derivadas.** hooks 58 -> 59, ligados 47 -> 48, registros 49 -> 50,
`_lib` 70 -> 71, ADRs 195 -> 196, golden 331 -> 334 linhas. Os sitios de prosa
foram varridos **por numero**, nao por regra — `verify-counts.sh` vigia 11
docs e ainda assim deixa prosa cega.

## Numeracao do ADR (por que 195 e nao 194)

O ADR-194 foi tomado pelo PLAN-183 (slug `delivery-route-resolution`, landado
em `6304f66`) enquanto este pack esperava montagem. O arquivo do pack foi
renomeado para **ADR-195**, e `adr_id`, titulo e `numbering_note` acompanham;
o ponteiro de doutrina no docstring de `check_ledger_checkpoint.py` — que
apontava para o break-glass do PLAN-169 — passou a apontar para este ADR.
Zero referencias ao numero velho sobrevivem no payload. (O literal `ADR-194`
aparece uma vez em `CLAUDE.md`, na prosa que descreve o ADR do **PLAN-183** —
essa e correta e fica.)

## Prova pre-assinatura

Registrada em `.claude/plans/PLAN-179/s328-ceremony-D/`:

- `land-sim.log` — simulacao de land em clone limpo (`git clone --local`,
  pack aplicado pelo MANIFESTO honrando o PACKMAP, `PYTHONDONTWRITEBYTECODE=1`),
  com **rc AGREGADO por comando** e a suite de hooks no split exato do CI
  (`-n auto -m 'not serial'` seguido do passe `-m 'serial'`).
- `EXPECTED-BASELINE.txt` — os conjuntos DECLARADOS que o V-block do land
  compara. Nunca "contra zero": a licao 1 da S327 foi um V-block que comparava
  contra zero uma suite que e 33/1 por desenho.
- `rail-round-*.md` — rodadas do pair-rail cross-vendor sobre a arvore com o
  pack aplicado, ate `VERDICT: APPROVE` literal.
- `test-ceremony-scripts-w24.sh` — harness que exercita os proprios gates:
  planta uma divergencia e exige o vermelho NOMEADO, prova que `--dry-run`
  restaura a arvore byte a byte, e que o G2b reprova um Scope adulterado.

## Residuais DECLARADOS (o que este pacote NÃO fecha, e por quê)

Levantados pelo pair-rail cross-vendor e deliberadamente não curados aqui. Os
três primeiros são a MESMA fronteira, e quem assinar está assinando também
esta lista.

1. **O módulo de proveniência ship SEM consumidor de produção.**
   `admit_entry` tem zero call-sites fora dos testes, e o hook novo só observa
   commits via Bash. Um `Edit`/`Write` direto em `PLAN-NNN/LEDGER.md` não passa
   por proveniência, scanner nem verificação de deleção. Ligar isso cria uma
   superfície de ENFORCEMENT nova (hook em `Edit`/`Write`, decisão de postura,
   par would-block/TP-FP próprio) — é wave com debate, não linha de cerimônia.

2. **A postura padrão do write-gate devolve a entrada REJEITADA.** Sem
   `CEO_LEDGER_WRITE_GATE_ENFORCE`, um veredito `scanner_unavailable`/
   malformado/com hit ainda devolve a entrada, com `would_reject` no verdict e
   o evento emitido. É a forma measure-first que o repo já usa no
   `CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED`, está escrita no docstring da função, e
   a exposição prática hoje é zero — pelo motivo do item 1. **A wave que ligar
   o primeiro escritor tem de decidir bind-vs-measure ANTES de ligá-lo**;
   ligar o escritor mantendo o default advisory seria aí sim um fail-open.

3. **Deleção staged do ledger conta como `ledger_updated`.** Um `LEDGER.md`
   staged para deleção ainda aparece em `git diff --cached --name-only`, e
   `rel in paths` tem precedência sobre `facts["exists"]` — o commit sai com
   `would_block=0` e sem advisory, deixando a superfície de persistência ser
   removida sem ruído. As três saídas possíveis (`ledger_deleted` novo; mapear
   para `ledger_missing`; deixar cair em `ledger_absent_from_plan`) mexem num
   ENUM FECHADO que viaja no `SPEC/v1` deste próprio escopo assinado, ou nos
   números da janela. Nenhuma é escolha do agente de cerimônia; a análise
   completa está em `s328-ceremony-D/rail-round-1.md`, §P2-1.

Exposição real dos três hoje: **baixa e limitada** — o rail é ADVISORY por
construção (não existe braço de deny no módulo) e o write-gate não tem
consumidor.

## Fora deste pacote

- `check_contamination.py` (a excecao negativa para a classe `LEDGER.md`, ja
  que `.claude/plans/*` atravessa `/` no fnmatch e isenta a arvore de planos
  inteira) — o script e NAO-canonico e cabe em commit direto, fora da
  cerimonia.
- `SESSIONEND-NOTE.md` — especificacao do US8 (SessionEnd emitindo o delta
  candidato de memoria) para a cerimonia que tocar `SessionEnd.py`. Fica no
  pack como documento e **nao aterrissa**: `assemble_pack.py` exclui os
  PACK-DOCs do manifesto de proposito, senao o G5 os copiaria para a RAIZ do
  repo dentro do escopo assinado.
- O flip de `status:` do PLAN-179 — decisao do Owner, edicao canonica de
  outra janela.
