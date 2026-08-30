# Pacote F — rail codex rodada 10 (sombra rebaseada em `bc23796`, 2026-08-30 ~17:4x -03)

Rail-Verdict: CHANGES-REQUESTED (0 P1, 2 P2 REAIS — ambos curados nesta
disposição com controle vermelho→verde)

Comando: `codex exec review --uncommitted --skip-git-repo-check -c sandbox_mode="workspace-write"`,
via `rail_round.sh`. Substrato: codex-cli 0.147.0. Saída bruta:
`<scratchpad 889bc1bd>/r10.txt`. Wrapper: **TREE INTACT**.

Nenhum achado das rodadas anteriores reapareceu; zero P1. Os dois novos:

## [P2-a] Chave COMPUTADA some quando a base omite a gêmea passthrough — REAL, curado

14ª aparição da família, na variante de EMISSÃO: o loop de saída do
`generate()` itera as chaves DA BASE, então uma chave computada cujo par não
está na base nunca é emitida. Uma base sem `env` é forma que `validate_spec`
ACEITA (`base.get("env", {})`) — e perdê-la descarta em silêncio TODO
`env_override` declarado e validado; com o spec shipado isso entregaria
`check_config_protection.py` BLOQUEANTE em vez de advisory (a chave
`CEO_CONFIG_PROTECTION_ADVISORY` é ADICIONADA pelo spec, não herdada). Base
sem `_comment` engole o `GENERATED_COMMENT` pelo mesmo caminho. O pós-loop da
r2 já cobria as chaves de `USER_ONLY_PLACEMENT`; estas duas estavam na MESA ao
LADO (`TOP_LEVEL_COMPUTED`).

**Cura:** o pós-loop passa a varrer `TOP_LEVEL_COMPUTED` inteira — toda chave
computada ausente de `out` e não-excluída é emitida; a regra é a TABELA, não
um subconjunto escolhido à mão (`hooks` não pode faltar, coberta mesmo assim).
Controle vermelho→verde medido: **2 failed → 2 passed** (classe
`ComputedKeysSurviveABaseWithoutThem`).

## [P2-b] `CLAUDE.md` §5 carregava «20 → 30» — claim numérico de produto defasado — REAL, curado

A régua de contagens do repositório é zero-tolerance, e o patch JÁ edita o
`CLAUDE.md`. Três numerais atualizados no hunk da sombra, todos delta-zero em
bytes (o arquivo está a 56 B do teto de 40.000): «veredito 17 EXCLUIR / 9
INCLUIR» → «18 / 8», «roster `user` 20 → 30» → «20 → 29» (nos dois
parágrafos), «bateria 267/2» → «275/2». Verificado: 39.944 bytes exatos,
`check-claude-md-claims.py` rc 0. A NARRATIVA do §5 («PRONTA menos UMA
decisão») continua trabalho do closeout, como o sentinel declara — no patch
viajam numerais e nada mais.

## Números após esta disposição

Arquivo nuclear 120 → **122 casos**; bateria re-medida (EXPECTED-BASELINE
bloco V2); paridade `--check` rc 0; claims rc 0.

## Disposição

Curas aplicadas na sombra; materiais re-medidos commitados; sombra rebaseada; a
rodada 11 revisa o conjunto e é a que precisa sair APPROVE.
