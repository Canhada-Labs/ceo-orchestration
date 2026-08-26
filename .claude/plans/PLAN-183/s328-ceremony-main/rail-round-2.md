# Rail (codex) — main não-canônico, rodada 2

**rc:** 0 · **saída:** 3522 B · **achados:** 6 (2 P1 + 4 P2) · **veredito literal:** ausente.
**Os 4 achados da rodada 1 no meu escopo NÃO reapareceram** — as curas seguraram sob revisão nova.

---

## Achados no escopo — 2

### F8 [P2] `profile-opus-4-7.py:1409-1415` — armar a fase 2 aposentava o teto p99 duro

**Claim:** com `p99_advisory=False`, uma entrada pode atender p95 e a chave relativa e ainda estourar
o p99 duro; o rótulo fica `pass` e o ramo da fase 2 mapeia direto para exit 0.

**Verificação — REAL.** `_classify_entry` calcula `abs_ok = hook_p95 <= p95_ceiling_ms` — só p95.
`entry_passed` (`:1195-1198`) carrega `(p99_advisory or p99_within)`, então a fase 1 sai 1 via
`exit_class = 0 if passed else 1`. A fase 2 usa `_LABEL_EXIT_CLASS[aggregate]` e o rótulo `pass`
mapeia para 0. Ligar um K file retirava, calado, um teto que a fase 1 ainda cobra.

**Cura — em duas tentativas, e a primeira estava errada.** Escrevi primeiro um termo p99 CEGO
(qualquer entrada com `p99_within is False`). O teste de anistia PRÉ-EXISTENTE
(`TestSlowRunnerAmnesty::test_phase2_grants_amnesty_and_exits_0`) ficou vermelho e estava certo: como
`p99 >= p95` sempre e o teto p99 (160 ms) fica ABAIXO do p95 (180 ms), **toda** entrada que estoura
p95 estoura p99 — o termo cego tornava `advisory_slow_runner` inalcançável e cancelava a emenda
inteira. Evitei reusar `all_within_budget` justamente para não reimportar o p95 e caí no mesmo poço
por outra porta.

Cura final, escopada à célula que o rail nomeou: `hard_p99_breach` exige
`p99_within is False` **E** `verdict_label == "pass"`. Numa entrada cuja lentidão a chave relativa já
atribuiu ao runner, o estouro de p99 é o mesmo runner, não um segundo achado.

**Testes:** `TestTheHardP99CeilingSurvivesPhase2` — anti-vacuidade que prova que o fixture separa
mesmo p95 de p99 (com `_ITERATIONS=22`, p95 → `sorted[19]` e p99 → `sorted[20]`, logo são precisas
DUAS amostras altas; com uma só o p99 fica dentro, e a 1ª versão do fixture errou exatamente isso e
foi pega); a fase 2 sai 1 no estouro duro; e `--p99-advisory` continua saindo 0.

**Controle positivo:** termo `hard_p99_breach` removido do cálculo ⇒ **1 failed, 5 passed** — só o
teste de p99 cai, os de anistia seguem verdes (prova de que a cura ficou escopada). Restaurado.

### F9 [P2] `profile-opus-4-7.py:1154-1158` — timeout da referência não marcava falha

**Claim:** poucos timeouts de 10 s entre 40 amostras não movem a mediana nem os medianos de meia-
amostra, então `ref_valid` continua `true` e a fase 2 classifica contra um processo que não terminou.

**Verificação — REFUTA O COMENTÁRIO NO CÓDIGO, com números.** O comentário do escritor afirmava que
"a amostra de ~10 s envenena ref_p50/drift, que lê como infrastructure_contended downstream". Rodado
contra as próprias funções do módulo, com 3 timeouts entre as 40 amostras:

    ref_p50 = 50.0 · split-half drift = 1.000 (teto 1.5) · veredito = pass · ref_valid = True

Três processos que nunca terminaram e um atestado de saúde. A razão é estrutural: a MEDIANA é o que
torna este gate robusto a ruído de runner (ADR-163:258) — e essa mesma robustez o cega para uma
minoria de referências mortas. Estatística não responde "o processo terminou?".

**Cura — ARQUITETURAL, não pontual.** F5 (rodada 1) e F9 (rodada 2) são a MESMA classe em duas
rodadas, e a regra do repo manda trocar a arquitetura da cura. `_run_ref` passou a **inverter o
predicado**: `completed_ok = False` por padrão, e a confiança é ganha num único caminho — o processo
rodou até o fim e saiu 0. `if not completed_ok: entry_ref_failed = True`. Um ramo acrescentado depois
que esqueça de marcar falha não consegue reabrir o buraco, porque falha é o que a variável já diz.
(Esta é a mesma arquitetura que o Owner decidiu para a 4ª passada do PLAN-185: enumerar o que é
PROVADO seguro, e o resto é indeterminado.)

**Testes:** `TestAReferenceTimeoutIsAlsoAFailedMeasurement` — a REFUTAÇÃO rodada como teste (se as
checagens de forma pegassem timeouts diluídos sozinhas, a flag seria desnecessária; o teste fixa que
elas NÃO pegam) + integração com `subprocess.run` que estoura só na referência (dormir de verdade
custaria 10 s por amostra, e os hooks do corpus precisam seguir normais ou o run falha por hook e o
veredito sob teste nunca é alcançado).

**Controle positivo:** `entry_ref_failed = True` do ramo de timeout revertido para `pass` ⇒
**1 failed** (`test_a_timing_out_reference_process_reads_contended`), 1 passed. Restaurado.

---

## Estado dos testes

`test_hook_latency_relative_gate.py` — **56 passed, RC 0** (42 originais + 9 da rodada 1 + 5 da
rodada 2). `test_check_contamination_ledger_exception.py` — 17 passed, 1 skipped, RC 0.

## Fora de escopo — encaminhar

- `[P1] .claude/scripts/data/installer-write-safety-baseline.txt:40` — **repetido da rodada 1**
  (PLAN-185 W0). `scripts/upgrade.sh:3727` (`sed-interp`, fingerprint `17e1bdbce06a9384`) não está no
  baseline, então o checker sai 1 e os dois testes de baseline do rascunho estão vermelhos em
  qualquer checkout atual.
- `[P1] PLAN-179/staged-w24/.claude/hooks/tests/test_check_ledger_checkpoint.py:570` — **bloqueia a
  cerimônia W24**: o fixture cria o ledger mas stageia só `notes.md`, então o hook emite corretamente
  `ledger_missing` e a asserção de `ledger_updated` falha de forma determinística; o `LAND` do W24
  roda essa suíte no G4. Encaminhado ao dono do pacote D.
- `[P2] PLAN-179/staged-w24/.claude/hooks/check_ledger_checkpoint.py:470-472` — `env -i FOO=1 git
  commit`, `command -- git commit` e `stdbuf -oL git commit` pulam o token do wrapper mas tratam a
  OPÇÃO dele como outro comando, zerando a posição antes de chegar em `git`: `is_commit=false` e
  nenhum evento (nem gravado nem pulado).
- `[P2] PLAN-179/OWNER-W179-W24-LAND.sh:462-465` — `PYTHONDONTWRITEBYTECODE` não suprime bytecode que
  o `py_compile` produz explicitamente; o `_restore` não cobre nem preserva esses caminhos, então um
  `--dry-run` pode declarar restauração byte-a-byte depois de ter mutado o filesystem.

## Encaminhamentos para canônico

Nenhum.
