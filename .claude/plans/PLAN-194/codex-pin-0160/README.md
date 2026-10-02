# codex-pin-0160 — re-pin do Codex CLI 0.156.1 → 0.160.0 (PLAN-194)

Gerado por `.claude/scripts/re-pin-codex.py` em 2026-10-02 a partir do molde `.claude/plans/PLAN-193/codex-pin-0156/OWNER-PIN-SIGN.sh`
(sha256 `09ec1cf8f8efc18a9eb47a2e06298af04cfa8e501e786188356b9c8484e098df`). Não edite à mão: regenere o pack.

| valor | medido |
|---|---|
| versão | `0.160.0` (publicada em 2026-10-01) |
| range | `<0.157.0` → `<0.161.0` (inferior inalterado em `>=0.128.0`) |
| `npm_integrity` (plataforma `@openai/codex@0.160.0-darwin-arm64`) | `sha512-aefV6cqZA2REZgR//4McyXlp7zLcTti4CI2v3j9IVgNndPBv2kCeNEcz07qeelXcwOdSFPUKb6roA48vZmDgrQ==` |
| `sha256` do payload `aarch64-apple-darwin` | `112fae7a5a1223e673c8a1791d32338f37df8b527ff1159bb8adac6c4dbf1b4b` |
| `sha256` dos canônicos vivos (pin, manifesto) | `11514263cc7c219ca0d40ff8bc294f2d69cd5c837e08f80d1e10e0e73148a6f8`, `1828a56abf1acec1dadb6484aa271d263faefafe8827a75a4177f778facc933a` |
| `sha256` dos `.new` (pin, manifesto) | `cb532824ecabd8357d55799a90306dc2e326a7081a937e892df2454856264269`, `e356c3611bf9754f9e313ec644463d7bd765c9ab04ff52ea9569bb5c0b9b92dc` |
| tag que o re-pin segue | `v1.4.2` |

Arquivos: `OWNER-PIN-SIGN.sh`, `codex-cli-pin-manifest.json.new`, `codex-cli-pin.txt.new`, `pin-0160-approved.md`, `rehearse-pin-0160.sh`, `README.md`.

O `OWNER-PIN-SIGN.sh` recusa a execução real enquanto houver `TODO(owner)` no sentinel ou no
`codex-cli-pin.txt.new`. Os dois `.new` são conferidos por sha256 (`SRC_PIN_SHA256`,
`SRC_MAN_SHA256`): editar um deles à mão faz o script recusar. Para escrever a
justificativa no pin, regenere o pack (num diretório novo, ou depois de
removê-lo) com `--pin-note <arquivo>`.

O ensaio (`rehearse-pin-0160.sh`) clona o `main` e roda o script de verdade
nos controles negativos e no p2: com TODO(owner) pendente cada caso aborta no
guard TODO(owner), não no padrão que espera. Antes do ensaio: gere com
`--pin-note`, escreva as seções humanas do sentinel e commite o pack.

Texto herdado sem conferência: fora do bloco de constantes, do guard
TODO(owner) e do cabeçalho, o corpo do script é o do molde, byte a byte —
inclusive a prosa da mensagem de commit (as linhas `printf`). O gerador só
confere nela os literais de versão, hex e SRI; uma frase verdadeira apenas
para o re-pin do molde passa inalterada. Leia a mensagem de commit do script
contra ESTE re-pin antes de assinar.

O que cada passo e cada guard da cerimônia conferem, e por quê: o README do pack do molde, `.claude/plans/PLAN-193/codex-pin-0156/README.md` (o corpo do script é o do molde).
