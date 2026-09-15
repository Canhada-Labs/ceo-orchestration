# pin-0154-approved — sentinel do re-pin do codex CLI (DRAFT — assinar como pin-0154-approved.md)

Plan: PLAN-189
Wave: re-pin codex-cli 0.147.0 → 0.154.0
Anchor-SHA: <PREENCHER no SIGN com o HEAD real>
Data: 2026-09-15

## Ratificação (Owner, S352)

Pedido verbatim: «arruma o modelo do codex pro atual». Verificado nesta sessão:
o MODELO já estava atual (`gpt-6-astra`, `model_reasoning_effort = max`, herdado
do `~/.codex/config.toml`, que o runner do rail NÃO sobrescreve). O que estava
defasado era o CLI: o rail pinava 0.147.0 enquanto o binário global do Owner já
estava em 0.154.0 — SETE releases à frente. Toda rodada de rail corria sobre um
revisor mais velho do que o que o Owner usa interativamente.

## Scope

- `.claude/governance/codex-cli-pin.txt` — range `<0.148.0` → `<0.155.0`, com o
  motivo e a consequência declarados no cabeçalho.
- `.claude/governance/codex-cli-pin-manifest.json` — `package_version` 0.154.0,
  `npm_integrity` e `sha256` do payload `aarch64-apple-darwin` regenerados a
  partir do tarball real baixado do registry nesta sessão.

## Evidência dos digests (reproduzível)

    npm view @openai/codex@0.154.0 dist.integrity
      -> sha512-FV/x1OHXYv/ifjf3mXj9ThTTAWcUZN6cGIRQRhRxkKNOPuImu1WW0c8ev1vUkE9XGH90dEnYG1tBjIkxRikg0w==

    npm pack @openai/codex@0.154.0-darwin-arm64
    tar xzf openai-codex-0.154.0-darwin-arm64.tgz --include='*/bin/codex'
    shasum -a 256 package/vendor/aarch64-apple-darwin/bin/codex
      -> 4f85982624b3898c8991cb80c0981b2aa71070e3537046c9a95950318a95afcc

Binário de 212 MB; tarball de 111 MB. Nada foi instalado globalmente e nenhuma
ferramenta da máquina foi alterada.

## Protocolo (ADR-111 §pin-update-protocol)

Alargar o limite superior NÃO dispara re-run da Phase 4-bis: nenhuma medição
nova de corpus travado foi tomada. O gatilho de emenda de ADR é um desvio de
catch_rate > 5 pp no corpus travado — inexistente aqui por ausência de medição,
não por resultado.

## Consequência DECLARADA

Isto troca o INSTRUMENTO do rail. Medições feitas antes e depois deste commit
NÃO são comparáveis — a série de validade 93/93/91 da S352 foi medida sob
0.147.0. Regra da S352: ao trocar de geração, re-testar com o instrumento
intacto; aqui o instrumento muda de propósito, então a fronteira fica registrada
em vez de silenciosa.

## Residual

Só o payload `aarch64-apple-darwin` é pinado (é a plataforma do Owner). As
outras cinco plataformas do `optionalDependencies` seguem sem digest — mesma
postura da geração anterior, não regressão.
