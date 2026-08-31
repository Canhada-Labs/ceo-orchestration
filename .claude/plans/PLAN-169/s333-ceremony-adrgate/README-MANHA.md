# Manhã de 31/08 — o que aconteceu na madrugada, e o que espera você

> Leitura de dois minutos. **Nada precisa da sua assinatura agora.**

## O que já está no `main` (três commits, todos pushados)

| commit | o quê |
|---|---|
| `48b76b1` | **Main VERDE de novo.** O `Smoke Install` do land da wave-F tinha ficado vermelho. |
| `f348ee9` | **A cadeia de ADRs vai de 11 erros para 2** — e nenhum ADR foi editado. |
| (o `303ae55` é o seu land da wave-s330-F, de ontem) |

### `48b76b1` — por que o main tinha ficado vermelho

O land da wave-F regenerou o índice de ADRs (170 → 198 linhas). Esse arquivo,
`.claude/adr/README.md`, é **semeado uma vez** pelo install e o upgrade nunca o
atualiza — de propósito: `.claude/adr` não está no conjunto que o upgrade
considera seu, e o diretório é do adopter (é onde ficam os ADRs *dele*). Como o
conteúdo do seed nunca tinha mudado desde a v1.2.0, o gate de paridade nunca
tinha visto diferença. Agora viu.

A declaração entrou no classificador (arquivo livre, sem cerimônia) com a
autoridade estrutural, ao lado das declarações irmãs de `CLAUDE.md` e
`MEMORY.md`. Verificado no e2e real: paridade `maintainer:0 user:0`, adopter
histórico `148 passed / 0 failed`, e o controle positivo continua disparando —
o gate não ficou vacuoso.

**Fica aberto para você decidir (`FU-ADR-README-SEED`):** esse seed leva o
índice dos **198 ADRs do framework** para dentro da árvore do adopter. É da
mesma família da contaminação A7. A cura é canônica (`install.sh` + um template
sem índice) e é decisão de produto.

### `f348ee9` — a cadeia de ADRs

O plano da noite dizia «dar `Status:` a nove ADRs e flipar o ADR-111 para
SUPERSEDED». **A medição refutou as duas premissas**, e ainda bem:

* os nove ADRs **têm** o campo — escrito como item de lista (`- **Status:** X`),
  forma que a âncora do leitor rejeitava. Defeito do LEITOR;
* flipar o ADR-111 **re-introduziria um bug de ledger já reparado**: o próprio
  ADR-111 (§20-31) registra que a marca SUPERSEDED anterior era falsa, o
  ADR-182 diz que a substância não é superseded, e um consumidor vivo
  (`SPEC/v1/audit-log.schema.md:329`) fala em «ADR-111 ACCEPTED gate».

Então o **objetivo** que você ratificou ficou de pé e o **mecanismo** mudou:
curar o leitor, zero ADRs editados. Onze erros viram dois.

## O que NÃO foi feito, e por quê

**O wire dos dois gates no CI não landou.** Ele viaja junto com o mecanismo que
ensina o leitor a reconhecer os dois qualificadores restantes — e esse
mecanismo levou **três rodadas de pair-rail achando furos fail-open na mesma
classe** (a isenção era mais frouxa que a semântica que declara). Ligar um gate
junto com uma isenção que o revisor ainda está furando não é enforcement.

A rota para a próxima wave está desenhada e medida em `rail-round-3.md`: trocar
a inferência por um **ledger declarado** de duas linhas, mandatory-fire, no
molde que o checker já lê para os *chain gaps*. Isso mata os quatro achados da
r3 por construção. É wave de cerimônia (dois paths canônicos: o `README.md` dos
ADRs e o `validate.yml`).

**O Bloco B (FU-7, `doctor.sh` como 3º consumidor de `_wbm_dst_refuses`) não
começou.** A recon dele está feita e verificada — fica pronta para a próxima
sessão.

## Se você quiser conferir

```
cd /Users/joaocanhada/canhada-labs/ceo-orchestration
python3 .claude/scripts/check-adr-chain.py     # 2 erros, ambos citando ADR-111
bash .claude/plans/PLAN-169/s333-ceremony-adrgate/redctl-adrgate.sh .   # controles
```

O desenho completo está em `DESIGN-ADRGATE.md`; as três rodadas do rail, com o
que cada uma achou, em `rail-round-1..3.md`.
