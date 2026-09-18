# Rodada 1 do re-pass da v1.4.1-rc.1 — `NO-GO` nas três partes (2026-09-18)

> Registro de triagem. Os três vereditos deste diretório são a evidência; este arquivo diz o que
> foi conferido contra o código, o que se decidiu para a rodada 2 e por quê.

## O que rodou

- Candidato: `9e9840b2fc6c033498a0c12c65178a5254d0b04e` (o commit do bump, `release: v1.4.1`), CI verde.
- Revisor: codex 0.155.0 (binário global, payload conferido contra o manifesto ADR-182), modelo
  `gpt-6-astra`; 3 partes em paralelo; `RUNNER-OVERALL: rc=1`.
- Condições julgadas: `CONDITIONS-rc1.reviewed.md`
  (sha256 `e021623158d27549892276a2adb6e003fbd58a8c0e697dadb7c353c744ba2ebe`).
- O `MANIFEST-rc1.sha256` verifica 19/19 com o conjunto completo. No git ficam só os vereditos, a
  PROVENANCE, o MANIFEST, o candidato e as condições julgadas — a convenção dos `NO-GO` arquivados da
  v1.4.0; diffs, payloads e transcripts são reproduzíveis a partir do candidato e ficam fora do git.

| veredito | sha256 |
|---|---|
| `verdict-rc1-1.txt` | `f46ebb9e8e7d33a2e9a0295a4daccc4e2c07214cf9497b4922a4734ffae12e6a` |
| `verdict-rc1-2.txt` | `13716c568ddd997d2d5832d7f943b739e12dd6ab1a06b68bd6a4e8cee274b85e` |
| `verdict-rc1-3.txt` | `a4d9c15739622c8585c56bdef53df35ea31e0c5087dd0a55b684235cac06af49` |

## As cinco condições falsas — todas CONFIRMADAS contra o código

Nenhum P0. O `NO-GO` veio, nas três partes, pela regra do corte: condição declarada falsa.

| condição | o que ela dizia | o que o código faz (conferido) |
|---|---|---|
| 7 | id ambíguo na resposta deixa o lançamento sem vínculo | `extract_run_id` aceita a primeira de `runId`/`run_id` que tiver a forma, sem checar acordo entre as duas (sonda: duas chaves divergentes ⇒ vincula a primeira); um token com cauda longa demais é lido pelo prefixo (`wf_12345678-123456789` ⇒ `wf_12345678`), não rejeitado |
| 10 | falha de infraestrutura é fail-OPEN | `iter_index` devolve as linhas já lidas quando um `OSError` interrompe a leitura e pula linha rasgada, sem sinalizar; se o vínculo mais recente de um run se perde assim, o guard compara contra o anterior e pode BLOQUEAR uma retomada legítima |
| 12 | outro worktree ⇒ `no_manifest`, «só aviso» | `_guard` grava `no_manifest` e devolve `{}`: não há aviso nenhum |
| 14 | `relaunch --out` entrega o arquivo inteiro ou nenhum arquivo | sem `finally`: um Ctrl-C no meio da escrita pula o `close` e a limpeza; e, numa falha tratada, se o `unlink` falha o parcial fica (a própria mensagem o admite) |
| 15 | nenhum dos quatro arquivos fora do escopo é entregue a adopters | o `upgrade.sh` enumera `.claude/scripts/` recursivamente e `_framework_path_excluded` não exclui `.claude/scripts/local/`; a instalação fresca só copia o nível de cima. Medido: os três adopters do maintainer já têm `.claude/scripts/local/release.sh` |

Duas frases do `CHANGELOG` `[1.4.1]`, escritas nesta sessão, também caíram (anexo da parte 2):
«`steal` only when the holder's heartbeat is past its TTL» (o `steal` usa o limiar do CHAMADOR,
`--stale-minutes`) e «missing, ambiguous or invalid input is REJECTED … no default-green path»
(`"score": "NaN"` aprova; chave de política desconhecida some em silêncio).

## Decisão para a rodada 2 — corrigir o TEXTO, não o código

- O código da parte 1 é canônico (cerimônia GPG + Smoke Install de ~1h50 por candidato) e o mandato
  desta release é entregar o guard de `Workflow` aos adopters agora. Curar código abre superfície nova
  na última rodada que a regra de parada permite.
- A rodada 2 roda sobre um candidato em que NENHUM arquivo de código mudou: as condições 5, 7, 9, 10,
  12, 14 e 15 foram reescritas para dizer o que o código faz; o `CHANGELOG` e os dois docs de operador
  perderam as frases que o código não sustenta; os achados desta rodada entram DECLARADOS como
  abertos (seção D das condições), com o sha256 dos três vereditos acima dentro do material assinado.
- A cura de código vai para a 1.4.2 (ou para um rc.2, se o Owner preferir): lista em
  `.claude/plans/PLAN-192-release-v1-4-1.md`.
- Residual que o texto NÃO alcança: o bloco `RELEASE_HEADLINE` do `release.sh` (canônico, assinado na
  relmeta-141) resume a W1.1 como «o arquivo inteiro ou nenhum arquivo». A condição 14 declara o
  limite; mudar a frase exige nova cerimônia — decisão do Owner.
