# wave-179close — rail codex rodada 11 (sombra pós-curas r10, S336 2026-09-01)

Rail-Verdict: CHANGES-REQUESTED (4 P2 — 2 REAIS curados, 1 hardening proporcional com fronteira declarada, 1 REFUTADO; tudo ANTES da r12)

Forma prompt-only. Saída: `<scratchpad S336>/179close-r11.txt` (14.066
linhas), exit 0. TREE-INTACT: manifest sha256 pré/pós byte-idêntico.

## Os achados (verificação + destino)

1. **[P2] Dir de memória symlinkado** — REFUTADO: o DIRETÓRIO de memória
   pode ser symlink LEGÍTIMO (dotfiles managers versionam `~/.claude` e
   symlinkam); rejeitá-lo quebraria setups reais para defender contra um
   atacante same-UID que não precisa de symlink nenhum (mesma fronteira
   das refutações r7). A garantia r10 é por ENTRADA (atribuição de mtime
   externo a um TÓPICO), não por resolução de diretório — `/tmp` e o
   próprio `$HOME` resolvem por symlink no macOS. CURA de honestidade:
   fronteira declarada em comentário no ponto exato.
2. **[P2] mtime futuro ⇒ `written` perpétuo** — VERIFICADO REAL (rollback
   de relógio, restauração de metadados, `touch -t`: o predicado só tinha
   limite inferior e um mtime futuro satisfaria `>= start` para sempre,
   sem atividade nenhuma — falso-positivo perpétuo, a pior classe). CURA:
   limite SUPERIOR capturado no início da observação (`time.time()+2.0`
   de folga de granularidade); fora da janela não conta (perder >
   inventar, doutrina r3). Controle:
   `test_future_mtime_is_outside_the_window`.
3. **[P2] `.strip()` corrompia paths exatos do `-z`** — VERIFICADO REAL:
   filename legal com espaço inicial (` .claude/plans/PLAN-042/x`) era
   colado no path canônico ⇒ pointer ERRADO (pior que ausente). CURA:
   `_git` ganha modo `raw=` (o strip de output inteiro também corromperia
   o primeiro/último path) e o índice consome VERBATIM, filtrando só
   campos vazios; sondagem empírica registrou que `-m -z --format=` emite
   NULs puros sem separadores de newline entre blocos de parent.
   Controle: `test_leading_space_path_is_not_the_plan_path`.
4. **[P2] Materialização pré-slice** — parcialmente procedente:
   `capture_output` já é limitado por timeout×throughput da fatia de
   1.0s (r10) — o resíduo é transiente e sub-segundo. HARDENING
   proporcional: `split("\0", maxsplit=cap)` limita a materialização de
   strings pequenas (o resíduo cai no slice); fronteira declarada em
   comentário. Streaming de subprocess seria desproporcional a um índice
   OPCIONAL já degradável.

## Verificação pós-cura

Bateria declarada (9 suítes) na sombra pós-cura: **327/0** (8.87s) —
`EXPECTED_UNIT_PYTEST_PASSED` 325→327 (+2 controles, nada removido).
Curas confinadas a 4 paths do EXPECTED. Refinalize + r12 na sequência.
