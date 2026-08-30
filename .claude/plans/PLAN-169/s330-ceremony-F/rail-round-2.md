# Pacote F — rail codex rodada 2 (shadow-F curada da r1, 2026-08-30 ~10:38 -03)

Rail-Verdict: CHANGES-REQUESTED (1 P1 por construção + 3 P2 reais, os três curados)

Comando: `codex exec review --uncommitted --skip-git-repo-check -c sandbox_mode="workspace-write"`,
via `rail_round.sh` (guard de integridade). Modelo `gpt-5.6-sol`, esforço xhigh.
Saída bruta: `<scratchpad efd20343>/rail/r2.txt`. Wrapper: **TREE INTACT**.

## Achados

- **[P1] «Add the required signed sentinel before landing»** — `ADR-197:7`.
  **Por construção, e não é achado.** A sombra É o estado pré-SIGN: o sentinel
  traz `TO-FILL-AT-SIGN` e o `.asc` nasce na cerimônia do Owner; o LAND recusa
  sem ele (G1/G2). Mesma disposição das rodadas 2, 3, 7 e 11 do pacote E.

- **[P2-a] Seletores que se sombreiam** — `gen-settings-user-template.py:701-704`.
  `derive_hooks` resolve um override preferindo `Evento/nome` sobre o `nome` nu.
  Um spec que declarasse **os dois** tinha a entrada nua aplicada nunca e
  recusada nunca — cada uma passava a validação por conta própria, e o defeito
  vivia só na RELAÇÃO. **REAL.**

- **[P2-b] Campos gerados perdidos com a âncora** — `:793-799`. `_derivation`
  entra depois de `_comment` e `_model_comment` antes de `model`; excluir a
  âncora levava o campo junto. **Perder `_derivation` é irrecuperável no caminho
  normal**: o artefato deixa de carregar o próprio spec e o `--check` seguinte
  sai rc 2. **REAL.**

- **[P2-c] O critério não batia com a própria lista** —
  `settings.user.json:251`. O `criterion` dizia que fica de fora todo hook que
  «bloqueia uma chamada de ferramenta sem rota advisory», e
  `check_scratchpad_access.py` está DENTRO e bloqueia um comando sem
  kill-switch. **REAL** — o veredito veio do critério ANTIGO, que a própria
  classificação substituiu.

## Curas

**P2-a** — checagem única antes do laço por chave: declarar `nome` e
`Evento/nome` juntos é recusado por nome.

**P2-b — a cura teve DUAS arquiteturas, e a primeira estava errada.** A forma
inicial REJEITAVA uma base sem a âncora e **quebrou 18 testes** cujas bases
sintéticas legitimamente não têm `_comment`. Over-correction medida. Trocada
pela outra rota que o próprio revisor ofereceu: **`generate` emite todo campo
gerado de qualquer jeito** (anexado, em ordem determinística, quando a âncora
falta), e o validador recusa apenas o que o SPEC remove — decisão de operador.
*Recusar menos, não perder nada.*

Achado colateral: **`_comment` já era protegido** por camada mais antiga (é
generator-sourced). A checagem de âncora ganha o seu lugar na OUTRA âncora,
`model`. O teste diz qual camada pega qual caso.

**P2-c — o censo mudou o desenho da cura.** Duas medições:

* **dez** dos 29 hooks retidos têm sítio de bloqueio, quase todos desde a
  v1.0.0 ⇒ o critério **nunca descreveu o perfil**; ele descreve a decisão de
  EXCLUIR entre os 26 candidatos. Lido como bicondicional é falso, e foi assim
  que o revisor o leu — com razão;
* **cinco** dos nove hooks que a wave ACRESCENTA podem bloquear, não um. Curar
  só o que o revisor nomeou teria reproduzido o defeito em escala menor.

Cura: o `criterion` declara o próprio escopo, e `blocking_inclusions` nomeia os
cinco com a rota real (`CEO_TURBO=0`; `CEO_CONFIG_CHANGE_GUARD=0`; rodar sem
`--plan`; não setar `CEO_CODEX_USER_REVIEW_BLOCK=1`; não setar
`CEO_REVIEW_LOOP=1`). O validador recusa entrada sem rota, sem evidência, morta,
duplicada ou sobre hook excluído.

**O guard que sobrevive à wave** é o de COMPLETUDE: re-deriva o conjunto do
roster ANTIGO (fixture congelada) contra as fontes dos hooks, em vez de comparar
com lista lembrada. Uma inclusão bloqueante futura fica vermelha com o nome.

## Verificação

- 14 testes novos (`SelectorsAndAnchorsAreFailClosed` 5 + `BlockingInclusionsCarryTheirRoute` 9).
- **Controle vermelho em duas pernas:** remover uma entrada de
  `blocking_inclusions` ⇒ 2 vermelhos, um nomeando `check_scratchpad_access.py`;
  remover as três validações do gerador ⇒ **9 de 14 vermelhos**, com os 5
  controles positivos passando nos dois estados.
- Suíte da cerimônia **225 → 239**; arquivo nuclear **73 → 87**.
- Paridade `--check` rc 0 antes e depois de cada cura.
- Custo revisado do template: **38.178 B (+22.360 sobre o HEAD)**, não os
  +20.061 que o writer mediu antes de `blocking_inclusions` existir. Corrigido
  no ADR, no DESIGN e no sentinel — a tabela e as conclusões juntas.

## Disposição

Sombra CURADA. A rodada 3 roda sobre ela: rodada limpa prova a SUPERFÍCIE
revisada, e a superfície mudou em três lugares.
