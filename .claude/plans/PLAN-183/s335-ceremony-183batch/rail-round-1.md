# wave-183batch — rail codex rodada 1 (sombra base 8f01202, 2026-08-31 S335)

Rail-Verdict: CHANGES-REQUESTED (1 P1 + 1 P2 — ambos verificados REAIS; curados ANTES da r2)

Comando: `codex exec review --uncommitted --skip-git-repo-check
-c sandbox_mode="workspace-write"`, do diretório da sombra, stdin
`</dev/null`. Saída bruta: `<scratchpad S335>/183batch-r1.txt` (4.029
linhas). Snapshot sha256 dos 3 paths antes/depois: TREE-INTACT.

## Os achados (e o que cada cura fez)

1. **[P1] O flip do AC-5 criava registro falso de governança** — o texto do
   AC exige «EXECUTAR o CI entregue»; o wiring registrado
   (smoke-install.yml:485 → sh:180) ATIVA e valida o template, mas nunca
   EXECUTA o workflow ativado, e W0-US3/OQ-2 seguem abertos no próprio
   plano. O runbook previa as duas saídas («satisfeito por registro?
   provável — SE sim») e a medição respondeu NÃO. CURA: flip REVERTIDO —
   viaja o REGISTRO (◐→◕) com a evidência nomeada e a razão explícita de
   o checkbox seguir aberto; finalize 4f e LAND V5/V6c-d passam a provar
   as DUAS metades (nota presente E `- [x] AC-5` == 0 — o flip é
   PROIBIDO nesta wave); baseline ganha `EXPECTED_AC5_NOTE_REFS`,
   `EXPECTED_AC5_CHECKED=0`; harness T16 planta a chave nova.
2. **[P2] `git mv` do header falha num install fresco** — o template nasce
   UNTRACKED no adopter e `git mv` recusa; o smoke mascara usando `mv`
   simples. CURA: header passa a `mv` + «commit afterwards», com a razão
   no próprio comentário. **MOLD-FINDING registrado:**
   `benchmarks.yml.template:5-7` carrega o MESMO `git mv` latente — fora
   deste patch (3 paths), cura futura nomeada no DESIGN.

## Verificação das claims

smoke-install.sh:194 usa `mv` (lido); install.sh copia sem `git add`
(comportamento conhecido do installer); W0-US3 e OQ-2 conferidos abertos
no plano (:1122-1126, :1482-1483). Pós-cura: frozen-subset **7/0** com o
header novo; flip=0 e nota=1 medidos por grep na sombra.
