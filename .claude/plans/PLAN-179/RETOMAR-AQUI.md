# RETOMAR AQUI — PLAN-179, terminal novo · 2026-08-19 08:15

## Situação em uma frase

O pack está **bom mas NÃO assinável ainda**: o pair-rail está no **round 7** e
acabou de devolver **4 achados novos (2×P1)**, sendo dois deles causados pelas
curas do round 6. **Não assine nada até o rail voltar limpo.**

## O que fazer ao abrir o próximo terminal

```
# 1. ver os achados abertos
cat .claude/plans/PLAN-179/rail-round-7/VERDICT.txt

# 2. curar os 4 (detalhe abaixo), regenerar o pack e rodar o round 8
python3 .claude/plans/PLAN-179/assemble_pack.py .claude/plans/PLAN-179/staged-w01
bash /tmp/.../scratchpad/rail_round8.sh     # copiar de rail_round7.sh trocando 7→8
```

Os scripts de rail/verificação vivem no scratchpad da sessão anterior e são
descartáveis — o essencial deles está descrito abaixo, dá para recriar em 5
linhas (clone local + aplicar o MANIFEST honrando o PACKMAP + `codex exec
review --uncommitted`, removendo `rail-round-*` do clone).

## Os 4 achados ABERTOS do round 7

1. **[P1] `--self-test` da sonda quebrado pela cura do round 6.** Agora
   `cmd_verify` exige registros de injeção nos dois canais, mas o `--self-test`
   e `.claude/scripts/tests/test_probe_postcompact_channel.py:98-104` nunca
   chamam `_record_injection`, então devolvem `EXIT_INCONCLUSIVE(4)` e falham.
   **Cura:** registrar as duas injeções antes de verificar, no self-test e nos
   testes.
2. **[P1] GC pode quebrar o locking do SQLite.** Os quatro arquivos de um store
   (`.sqlite`, `.lock`, `-wal`, `-shm`) hasheiam para **shards diferentes**,
   então podem ser removidos em varreduras distintas; e o mtime do `.lock` não
   é atualizado por aquisições, então um store ATIVO pode ter um sidecar
   removido. **Cura:** agrupar por escopo, adquirir o lock do store e decidir a
   expiração **do store como unidade** — não por arquivo.
3. **[P2] Override do sidecar: leitor ≠ escritor.** O escritor expande `~` e
   **rejeita** symlink/traversal caindo no default; meu leitor trata `~`
   literalmente e pode ler um path que o escritor recusou. **Cura:** resolver e
   validar igual ao `statusline-ceo.py:165-176`.
4. **[P2] Referências quebradas.** O script do rail apaga `rail-round-*` no
   CLONE, mas o `HANDOFF-MANHA.md:51,105,130` aponta para esses diretórios — no
   clone eles somem e as referências ficam órfãs. **Cura:** manter a exclusão
   só no clone e verificar que o repo real conserva tudo (ele conserva), ou
   parar de apagar e aceitar a contaminação com o veredito lido com atenção ao
   `workdir`.

## O que JÁ está pronto e provado (não refazer)

- **W3-K do PLAN-169: LANDADO e pushado** (`c34e8e3`), CI verde.
- Pack `staged-w01` com **34 paths**, manifesto e escopo do sentinel em dia.
- 6 rounds de rail curados: 9 → 4 → 2 → 3 → 2 → 3 achados, **todos novos a
  cada rodada** (o rail nunca repetiu um achado já curado).
- Evidência com controles positivo E negativo em `rail-round-3/`, `-4/`, `-5/`,
  `-6/` — inclusive a prova de que o código anterior **truncava um arquivo
  vítima de 44 para 3 bytes** por symlink.
- Verificação: 10 gates verdes (incl. `audit-registry`, `env-hygiene`) e suíte
  completa **7113 passed / 0 failed** na última rodada limpa.

## Ordem depois que o rail voltar limpo

1. `! bash ~/canhada-labs/BOM-DIA.sh` — detecta estado, assina (1 pinentry),
   dry-run, land, push, vigia o CI.
2. Montar `staged-w24` (W2+W4) — só depois que o w01 landar
   (`staged-w24/README-COMO-MONTAR.md` diz o que falta).
3. Flip do PLAN-179 `executing→done` — decisão do Owner.

## Aviso honesto

Sete rodadas é muito. O rail continua achando defeitos **reais e novos**, e
três deles nasceram das minhas próprias curas — o padrão é "cura introduz
defeito adjacente", não "o rail está sendo pedante". Se o round 8 trouxer mais
uma leva do mesmo tipo, a decisão certa provavelmente não é a rodada 9: é
**reduzir o escopo do pack** (landar W1/W1-b sem o guard de pressão e sem o GC,
que é de onde vieram 5 dos últimos 8 achados) e tratar o resto como wave
própria. Essa é a lição S296 registrada na memória: mudar o alvo, não insistir
na rodada.
