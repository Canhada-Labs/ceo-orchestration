# pin-0155-approved — sentinel do re-pin do codex CLI 0.154.0 → 0.155.0

Plan: PLAN-189
Wave: re-pin codex-cli 0.154.0 → 0.155.0
Anchor-SHA: (preenchido pelo OWNER-PIN-SIGN.sh no momento da assinatura)
Data: 2026-09-18

## Ratificação (Owner, 2026-09-18)

Mandato verbatim, registrado no fim da S355: «o próximo terminal finaliza o que
entra na 1.4.1, assina, publica, e atualiza os repos que uso o framework pra
seguirmos trabalhando. essa é a urgência máxima agora. inclui o que dá pra fazer
rápido e bora.» O re-pin é o primeiro item do «rápido»: sem ele o pair-rail deste
repo está fail-CLOSED e o passo 15 do `release.yml` não tem como receber um
veredito produzido pelo binário que o Owner de fato usa.

Medido em 2026-09-18, neste checkout, antes do re-pin:

    python3 .claude/hooks/check_pair_rail.py --verify-codex-pin "$(which codex)"
      -> {"status": "mismatch", "detail": "payload_sha256_mismatch", ...}  rc=1
    bash .claude/scripts/local/pair-rail-gate.sh --phase 6
      -> FAIL no Gate 4b (recusa executar o payload não verificado)

`codex --version` = `codex-cli 0.155.0`; o manifesto vigente pina 0.154.0.

## Scope

- `.claude/governance/codex-cli-pin.txt` — range `<0.155.0` → `<0.156.0`
  (limite inferior INALTERADO em `>=0.128.0`), com o motivo e a consequência
  declarados no cabeçalho.
- `.claude/governance/codex-cli-pin-manifest.json` — `package_version` 0.155.0,
  `npm_integrity` e `sha256` do payload `aarch64-apple-darwin` regenerados a
  partir do tarball real baixado do registry nesta sessão.

Nada além desses dois arquivos canônicos, deste sentinel e da sua assinatura
entra no commit da cerimônia (o script confere `touched ⊆ scope`).

## Evidência dos digests (reproduzível; medida em 2026-09-18)

    npm view @openai/codex time --json | grep '"0.155.0"'
      -> "0.155.0": "2026-09-17T23:19:02.781Z"

    npm view @openai/codex@0.155.0-darwin-arm64 dist.integrity
      -> sha512-c0vbt2ZS6XiXq9gQkNictu7PH0deMyq/bw4Ia9bdihU1iJHuGuwC5vD4swU4xhLUKoTs4tMOHwYWKaofFZcVRg==

    npm pack @openai/codex@0.155.0-darwin-arm64
    openssl dgst -sha512 -binary openai-codex-0.155.0-darwin-arm64.tgz | base64
      -> c0vbt2ZS6XiXq9gQkNictu7PH0deMyq/bw4Ia9bdihU1iJHuGuwC5vD4swU4xhLUKoTs4tMOHwYWKaofFZcVRg==
         (o tarball baixado confere com o `dist.integrity` do registry)

    tar xzf openai-codex-0.155.0-darwin-arm64.tgz --include='*/bin/codex'
    shasum -a 256 package/vendor/aarch64-apple-darwin/bin/codex
      -> b0b14f9c1901c1ec44671094b2dc18b39e4bd8d36a6dc2302cc9d961a7e2a197

O binário instalado na máquina do Owner (resolvido pelo próprio verificador em
`/opt/homebrew/lib/node_modules/@openai/codex/node_modules/@openai/codex-darwin-arm64/vendor/aarch64-apple-darwin/bin/codex`)
tem o MESMO sha256 `b0b14f9c…a197` — o que está instalado é o que o registry
publica. Binário de 228.770.720 bytes; tarball de 127.426.335 bytes. O download
foi feito num diretório temporário da sessão; nada foi instalado globalmente e
nenhuma ferramenta da máquina foi alterada.

## Discrepância DECLARADA: qual `npm_integrity` se grava

O ADR-182 §5 passo 2 manda gravar o `dist.integrity` do artefato de PLATAFORMA
(`@openai/codex@<ver>-<platform>`), que é o tarball que de fato carrega o
binário pinado. O re-pin de 0.147.0 (pack SENT-S318) seguiu o ADR. O re-pin de
0.154.0 (S352, `pin-0154-approved.md`) gravou o do pacote PRINCIPAL
(`npm view @openai/codex@0.154.0 dist.integrity` → `sha512-FV/x1…`), sem
declarar o desvio.

Este re-pin VOLTA ao ADR: grava o de plataforma (`sha512-c0vbt2ZS…`), conferido
em bytes contra o tarball acima, de modo que o manifesto fica autoconsistente —
`npm_integrity` identifica o tarball e `sha256` identifica o binário dentro dele.
Para registro, o do pacote principal de 0.155.0 é
`sha512-35a85Hbwy9WXkDTJumLjTcmMgpR7BMdrTloWBVGjoA+FBCh7jb3+cYp2W+3U4klqGAjAskoIvQZv7/eedmCjHA==`.

As duas gerações anteriores, conferidas contra o registry em 2026-09-18:

    0.147.0  manifesto gravou sha512-BEUVkiOW…  = plataforma (principal é sha512-EQLEXecA…)
    0.154.0  manifesto gravou sha512-FV/x1OHX…  = principal  (plataforma é sha512-HP/vJCH/…)

Alcance do desvio, medido: `npm_integrity` e `package_version` não têm leitor
mecânico em `.claude/hooks`, `.claude/scripts` nem `.github` (busca textual em
2026-09-18, excluídos os testes) — são proveniência. O gate real é o `sha256`
por triple, e esse estava e está correto nas duas gerações.

## Protocolo (ADR-111 §pin-update-protocol; ADR-182 §5)

Alargar o limite superior NÃO dispara re-run da Phase 4-bis: nenhuma medição
nova de corpus travado foi tomada. O gatilho de emenda de ADR é um desvio de
catch_rate > 5 pp no corpus travado — inexistente aqui por ausência de medição,
não por resultado.

Forma widen-upper-only, executada FORA de janela de release aberta: o GA v1.4.0
foi cortado em 2026-09-15 e a `v1.4.1-rc.1` só é cortada DEPOIS deste commit.

O passo 4 do ADR-182 §5 (re-rodar `--verify-codex-pin` com saída 0 e
`pair-rail-gate.sh --phase 6`) é executado pelo próprio script de cerimônia,
depois de aplicar os dois arquivos e antes de commitar; qualquer um dos dois
reprovando restaura a árvore.

## Consequência DECLARADA

Isto troca o INSTRUMENTO do rail. Medições feitas antes e depois deste commit
NÃO são comparáveis. Mesma regra da S352: ao trocar de geração, re-testar com o
instrumento intacto; aqui o instrumento muda de propósito, então a fronteira
fica registrada em vez de silenciosa.

## Residual

1. Só o payload `aarch64-apple-darwin` é pinado (é a plataforma do Owner). As
   outras cinco plataformas do `optionalDependencies` seguem sem digest — mesma
   postura das gerações anteriores, não regressão.
2. As fixtures do adaptador Codex (`.claude/hooks/tests/fixtures/adapters/codex/`)
   seguem gravadas sob `codex-cli 0.139.0`, que continua DENTRO do range
   alargado; o re-record e o checklist do ADR-161 NÃO fazem parte deste pack
   (mesma postura do re-pin de 0.154.0) e ficam para a wave de substrato.
3. A cadência medida do Codex é de um minor por semana (0.154.0 em 09/09,
   0.155.0 em 17/09). Com pin de versão exata, toda atualização global do CLI
   fecha o rail até o re-pin seguinte. A cura estrutural (ferramenta que gera
   este pack a partir de um número de versão) é do toolkit do PLAN-188 e NÃO
   está neste pack.
