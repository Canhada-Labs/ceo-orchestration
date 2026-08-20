# Rail round 11 — 4 achados (2×P1, 2×P2) · o critério de parada DISPAROU

Sequência: 9 → 4 → 2 → 3 → 2 → 3 → 4 → 4 → 3 → 3 → **4**.

O critério publicado no round 10 ("round 11 com achado novo em GC/pressão
⇒ parar e preparar o memo de redução") **disparou** (achado 4 é GC). Este
round encerra as rodadas autônomas: os itens mecânicos/prescritos foram
curados; a decisão de forma do pack está no memo abaixo, para o Owner.

## Disposição dos 4 achados

1. **[P1] "Staged com subprocess" — ARTEFATO DE SKEW do clone, não defeito
   do repo.** O clone do rail foi feito de HEAD ANTES do commit `a2a9a5a`
   (a cura no-exec era working-tree), e o apply copiou o staged VIVO
   (curado) por cima — codex viu destino curado × staged velho. No repo
   real: `grep -c subprocess` no staged = 0, e o tripwire
   `test_postcompact_reinject_no_exec_payload` está 16/16 verde no clone
   aplicado. **Higiene adotada:** rodada de rail só clona DEPOIS de
   commitar o staged (a causa era minha ordem commit×launch).
2. **[P1] Escopo do sentinel ≠ manifesto (39 paths) — REAL, curado.**
   `W179-approved-draft.md` ganhou os 5 paths novos (state_store, 3
   testes, COMMAND-SKILL-HOOK-MAP). Controle positivo: simulação do G2b
   do `OWNER-W179-LAND.sh` (mesmo awk/sort) = OK, 39 paths.
3. **[P2] Inode SUBSTITUÍDO não era detectado — REAL, curado.** Com dois
   handles pré-GC, o reopen do primeiro recria o path e o segundo veria
   "existe" com conexão no inode morto. `_reopen_if_vanished` agora
   compara `(st_dev, st_ino)` capturado na abertura — ausência E
   substituição reabrem. Teste: `test_second_handle_detects_inode_replacement`.
4. **[P2] Cap de 20k entradas pode starvar além do prefixo — ABERTO POR
   DECISÃO (memo abaixo).** Real no limite: >20k entradas no diretório
   (≈7k sessões mortas), o scan para no mesmo prefixo e o cursor só
   conhece o que foi escaneado.

## MEMO DE DECISÃO para o Owner (assinatura do pack)

Onze rodadas; os últimos 5 achados de GC são progressivamente mais
marginais (do "apaga sidecar de store ATIVO" no round 7 ao "starva se o
diretório passar de 20k entradas" agora). Opções na assinatura:

- **(a) Assinar como está, residual declarado** — o cap de 20k é
  ~100× além do envelope realista (GC coleta 64/run; chegar a 20k exige
  anos de GC quebrado); o residual fica nomeado aqui e no docstring.
  **Recomendação do CEO: esta.**
- **(b) Reduzir escopo** — landar sem o guard de pressão e/ou sem o GC.
  Custo: o GC é exigência do consenso r1-C2 (session-scope sem coleta =
  acumulação vetada pelo debate); remover agora é cirurgia nova em cima
  de código estabilizado — a classe S296.
- **(c) Round 12** — contra o critério publicado; o rail continua
  achando margens cada vez menores, o custo já não paga o achado.

O que já está provado a favor de (a): 63+66 testes dirigidos verdes nos
pontos exatos dos 11 rounds; suíte completa no clone com o pack aplicado
verde exceto 2 fails PRÉ-EXISTENTES e documentados fora do pack
(`skill_patch_propose` timeout local com CI Linux verde; flake conhecido
do audit-isolation quando outra sessão escreve o log vivo).
