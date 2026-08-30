# Pacote F — rail codex rodada 9 (árvore CONSISTENTE: sombra rebaseada em `40eabe8`, 2026-08-30 ~17:2x -03)

Rail-Verdict: CHANGES-REQUESTED (1 P1 refutado com fundamento — é o próprio
desenho do processo; 2 P2 REAIS, ambos curados nesta disposição com controle
vermelho→verde)

Comando: `codex exec review --uncommitted --skip-git-repo-check -c sandbox_mode="workspace-write"`,
via `rail_round.sh`. Substrato: codex-cli 0.147.0. Saída bruta:
`<scratchpad 889bc1bd>/r9.txt`. Wrapper: **TREE INTACT**.

Esta foi a primeira rodada sobre a árvore CONSISTENTE (a cura do P1 da r8):
sombra rebaseada no commit `40eabe8`, que carrega os materiais de cerimônia já
propagados (EXPECTED 29/28/29, sentinel, README-F, COMMIT-MSG, adendo da
classificação). O revisor confirmou a consistência ao não reapresentar o P1 da
r8 — e trouxe três achados novos.

## [P1] «Add signed sentinel evidence before landing» — REFUTADO: descreve o próprio fluxo

O revisor aponta que o patch toca `.claude/adr/` e `.github/workflows/`
(superfícies guardadas) «e só existe um sentinel draft com campos vazios e sem
`.asc`». Correto como DESCRIÇÃO — e é exatamente o estado intermediário que o
processo produz por desenho: o draft com `TO-FILL-AT-SIGN`/`TO-FILL-AT-FINALIZE`
é preenchido pelo `finalize-F.sh` (Scope/Patch-sha256/Patch-base) e assinado
pelo Owner no `OWNER-S331-F-SIGN.sh`; o `OWNER-S331-F-LAND.sh` verifica a
assinatura no G1/G2 e RECUSA o land sem ela. «Não pode landar até existir a
assinatura» não é um achado sobre o patch — é a especificação dos dois scripts
seguintes da cerimônia. O mesmo desenho (ADR entra `PROPOSED`; a ratificação é
o `.asc` sobre o sentinel, não o campo `Status:`) está declarado no próprio
sentinel e tem precedente em ADR-194 e ADR-196. Nenhuma ação.

## [P2-a] `_derivation.generator` validado por PRESENÇA, não por VALOR — REAL, curado

12ª aparição da família «declaração aceita e depois ignorada», agora na
superfície mais irônica: o ponteiro do artefato para o próprio mecanismo de
regeneração. `source` já era validado por valor (r3); `generator` não — um
caminho vazio ou errado sobrevivia a `--write`/`--check` para sempre.

**Cura:** constante `GEN_REL` + validação espelho da do `source`
(`spec.generator != GEN_REL ⇒ SpecError` nomeada). Controle:
`test_wrong_generator_path_is_rejected` + `test_empty_generator_is_rejected` +
o positivo `test_the_shipped_generator_path_is_the_one_accepted`.

## [P2-b] Override que virou NO-OP contra a base sobrevive com reason/evidence stale — REAL, curado

13ª aparição da mesma família, na variante por EQUIVALÊNCIA: se a base evolui
até o valor que o override declara (matcher, `statusMessage`, `_comment` de
bloco), o override deixa de mudar qualquer byte — mas continua verde, e sua
justificativa vira uma «exceção documentada» que não existe.

**Cura:** helper `_base_site(event, name)` em `validate_spec` + três guards de
VALOR (matcher do bloco; cada field de `hook`; `_comment` de bloco), todos
`SpecError` nomeando «NO-OP» e o campo. Controle vermelho→verde medido:
**5 failed / 3 passed** antes da cura (os 5 casos de rejeição não levantavam
SpecError; os 3 positivos de valor-diferente passavam) → **8 passed** depois.
O spec REAL continua válido (`--check` rc 0 — nenhum override shipado é no-op
contra a base atual, medido).

## Números após esta disposição

Arquivo nuclear **112 → 120 casos** (classe `NoOpDeclarationsAreRejected`, 8);
bateria dos 7 arquivos re-medida (ver `EXPECTED-BASELINE.txt`, bloco V2);
paridade `--check` rc 0; `py_compile` OK.

## Nota de método

A r8 provou que o rail flagra árvore inconsistente; esta rodada prova o
complemento — sobre a árvore consistente o revisor gastou o P1 no único item
que um revisor de diff não tem como ver satisfeito: a assinatura que ainda não
aconteceu. É o teto esperado de uma revisão pré-assinatura; os P2 continuam
sendo onde o rail paga.

## Disposição

Curas aplicadas na sombra; materiais re-medidos commitados; sombra rebaseada; a
rodada 10 revisa o conjunto e é a que precisa sair APPROVE.
