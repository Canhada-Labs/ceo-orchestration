# RETOMAR AQUI — PLAN-179 · atualizado S314, 2026-08-20 (madrugada)

## Situação em uma frase

**W0+W1+W1-b LANDADO E VERDE**: o Owner assinou (opção (a) do memo —
residual do cap de 20k declarado), a cerimônia landou em `c042f9e`, dois
fix-forwards fecharam os efeitos colaterais do corte (`6f7f20e` modes
parciais + banda ~730→~770; `45c75e3` sweep completo da família `_lib`)
e o CI de `45c75e3` terminou **5/5 success** — com o profiler curado por
RERUN (boundary-flake provado: verde no próprio sha do land, hook
`check_output_secrets` não tocado pelo pack, delta A/B local 2-4ms).

## Lições do pós-land (para o próximo corte)

- O land copia MODOS do pack: `_lib/*.py` chegou 755 e o smoke-install
  compara modo na paridade install/upgrade. Cura em dois passos porque o
  primeiro log veio truncado — varrer a FAMÍLIA inteira de uma vez.
- Os 3 test files novos do pack tiraram o "~730" da banda ±5% POR 2
  arquivos — contagem approx nos docs também é superfície de corte.
- `check_output_secrets` vive rente ao teto de 120ms p95 do profiler em
  hosted runner — INDEPENDENTE do pack (pré-land = HEAD na medição
  A/B). Se voltar a flakar, o item é recalibrar o teto ou otimizar o
  hook em wave própria, nunca reverter o land.

---

## (histórico da preparação — mantido)

O rail rodou até o **round 11**, o critério de parada publicado DISPAROU
(achado marginal de GC), **as rodadas autônomas encerraram** e o pack
`staged-w01` (39 paths) foi assinado com **UM residual declarado**
(memo em `rail-round-11/README.md`).

## O que aconteceu na S314 (rounds 8→11, todos com evidência)

Sequência completa do rail: 9 → 4 → 2 → 3 → 2 → 3 → 4 → **4 → 3 → 3 → 4**.

- **Round 8 (4 curados):** redação por CAMPO + bytes ao store — o JSON do
  snapshot não corrompe mais com `token=...` (era P1: a continuidade
  morria para exatamente os segredos que deve sobreviver); identidade do
  sidecar aceita cwd DENTRO do root; `constraint_count` reporta o
  RENDERIZADO; CLAUDE.md do pack na verdade pós-land.
- **Round 9 (3 curados):** exec bit 755 no hook novo (confirmado
  independentemente pela suíte no clone — lição "cp perde exec bit");
  `_resolve_project_root` (walk-up-first) cura a família cwd→root
  inteira; GC nunca mais unlinka lock file (inode estável).
- **Round 10 (3 curados, prescrição do rail seguida):**
  `state_store.py` ENTROU no pack com `_reopen_if_vanished()` sob TODO
  FileLock — a cura de raiz da corrida GC×conexão que os rounds 7/9/10
  circulavam; PostCompact re-arma a histerese de pressão
  (`clear_context_pressure_marker`); GC com cursor de RETOMADA
  persistido (starvation de prefixo morta).
- **Interlúdio (a suíte pegou a MINHA cura):** o `_git` do re-arme violava
  o contrato no-exec do PostCompact (tripwire de
  `test_postcompact_reinject_no_exec_payload`) — resolver do PostCompact
  virou walk-up-only, e o do PreCompact walk-up-FIRST para os dois
  concordarem. Registro honesto: o tripwire funcionou como desenhado.
- **Round 11 (2 curados, 1 skew, 1 ABERTO por decisão):** escopo do
  sentinel regenerado para 39 paths (G2b simulado OK); `(st_dev, st_ino)`
  detecta inode SUBSTITUÍDO além de ausente (cenário de dois handles,
  com teste); o "staged com subprocess" era skew clone×working-tree
  (higiene adotada: clonar só depois de commitar); **o cap de 20k
  entradas do scan fica ABERTO — ver o memo**.

## O ÚNICO aberto do pack: memo de decisão (Owner)

`rail-round-11/README.md` — em resumo: **(a) assinar com residual
declarado (recomendado)**, (b) reduzir escopo (quebra o consenso r1-C2),
(c) round 12 (contra o critério; margens decrescentes).

## Verificação (estado ao escrever)

- 39 paths, `MANIFEST.sha256` verificado; G2b (escopo==manifesto)
  simulado OK com o awk/sort exato do `OWNER-W179-LAND.sh`.
- Dirigidos: 63 (GC+state_store+compaction) + 66 (no-exec+integração no
  clone) + parity + sonda — todos verdes, exit real lido de arquivo.
- Suíte completa em clone com o pack aplicado: verde exceto 2 fails
  PRÉ-EXISTENTES fora do pack, ambos documentados: (i)
  `test_skill_patch_propose::test_diff_size_cap...` — timeout 30s
  também no HEAD vivo, CI Linux verde (classe perf local/macOS); (ii)
  `test_check_test_audit_isolation::test_gate_green_on_head` — flake
  conhecido quando OUTRA sessão escreve o audit log vivo (lição
  [[feedback-live-audit-isolation-flakes-under-concurrent-session]]).
- (A última suíte, com o inode-fix, estava rodando ao fechar — resultado
  em `~/.w179-suite8/RESULT.txt`; mudanças desde a anterior: só
  state_store inode + testes, dirigidos verdes.)

## Ordem quando o Owner decidir

1. Se (a): `! bash ~/canhada-labs/BOM-DIA.sh` — assina (1 pinentry),
   dry-run, land, push, vigia o CI. O BOM-DIA foi ENDURECIDO na S314:
   verde = TODAS as runs do sha com `conclusion=success` (`cancelled`
   não passa mais — classe do falso-verde do `c34e8e3`).
2. Montar `staged-w24` (W2+W4) — itens novos NOMEADOS para ele nesta
   sessão: state_store lock-then-open pleno (aí o GC pode coletar locks
   com segurança) e a decisão do cap de scan se o Owner escolher (b).
3. Flip do PLAN-179 `executing→done` — decisão do Owner.

## Fora do PLAN-179, também fechado na S314

- Escrituração: PLAN-169 (E.2 CLOSED via W3-K `c34e8e3`, ledger 58/3/1,
  frase falsa do PLAN-170 corrigida) e PLAN-178 (fechamento parcial:
  AC-1/2/2b/4/5 com evidência; W1.3 com destino nomeado no W4-C).
- `ceo-boot.py`: stranded-proxy casa `PLAN-NNN` em paths E subjects
  (falso-vermelho do 169 morto; live-fire feito).
- Triagem CI: `coverage.yml` e `tournament.yml` eram reds OBSOLETOS (já
  curados em `9179ef2` e `2aceb05`); o achado sistêmico é o
  `cancel-in-progress` do validate — instrumentado no BOM-DIA.
