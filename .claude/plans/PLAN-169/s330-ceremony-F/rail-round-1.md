# Pacote F — rail codex rodada 1 (shadow-F sobre `7ffcdeb`, 2026-08-30 ~10:26 -03)

Rail-Verdict: CHANGES-REQUESTED (2 P2 reais, ambos curados nesta mesma sessão)

Comando: `codex exec review --uncommitted --skip-git-repo-check -c sandbox_mode="workspace-write"`
na `shadow-F`. Modelo `gpt-5.6-sol`, esforço xhigh. Saída bruta:
`<scratchpad efd20343>/rail/r1.txt` (14.148 linhas).

## Nota de substrato (vale para as próximas rodadas)

Duas coisas mordem quem repetir isto:

1. **`codex exec review --uncommitted` não aceita PROMPT.** A forma com
   instruções customizadas sai `error: the argument '--uncommitted' cannot be
   used with '[PROMPT]'`. A revisão é do diff, sem direcionamento.
2. **Sob `sandbox_mode="read-only"` a rodada MORRE** quando o revisor tenta
   rodar a suíte: `FileNotFoundError: No usable temporary directory found`
   (o pytest não consegue criar o tempdir de captura). A rodada 1 foi perdida
   assim antes de produzir veredito. A forma que funciona é
   `-c sandbox_mode="workspace-write"` — o que significa que **o revisor pode
   editar a árvore que revisa**. Por isso as rodadas rodam sob
   `rail_round.sh`, que hasheia cada path staged antes e depois e RECUSA
   reportar uma rodada cuja árvore mudou. Rodada 1: `TREE INTACT`.

## Achados

Nenhum defeito no que a wave ENTREGA. Os dois achados são **na própria cura**,
e da mesma classe que a wave existe para remover: *uma declaração no spec que o
gerador ignora em silêncio*.

- **[P2-1] Override de escopo de BLOCO num bloco de várias entradas** —
  `gen-settings-user-template.py:660-667`. `matcher` e o `_comment` de grupo
  pertencem ao BLOCO, e `derive_hooks` só os escreve quando o bloco se estreita
  a UMA entrada retida. A checagem de ambiguidade do validador conta
  REGISTRAÇÕES que casam o nome entre eventos — outra pergunta —, então uma
  chave legitimamente qualificada (`Evento/nome`) apontando para um bloco de
  duas entradas passava na validação e era descartada depois. **REAL.**
- **[P2-2] Exceção sem justificativa, e exceção que não muda nada** —
  `:481-490`. `annotation_overrides` aceitava entrada sem `reason` (contra o
  contrato do DESIGN-F §3) e entrada só-com-`reason`, que não altera byte
  nenhum. **REAL.**

O revisor levou os dois até o controle executável: rodou `validate_spec` com
`{'_comment': 'changed'}` e `{'reason': 'r'}` e mostrou `accepted` nos dois.

## Curas (nesta sessão)

Fail-CLOSED no validador, nas duas:

* helper `_retained_in_block(event, name)` — responde a pergunta que a
  derivação realmente faz (quantas entradas do BLOCO sobrevivem), em vez da que
  o validador fazia (quantas registrações casam o NOME);
* `matcher_overrides` e `annotation_overrides._comment` num bloco que retém ≠ 1
  entrada ⇒ **rejeitados por nome**, com a rota de reparo na mensagem;
* `annotation_overrides` exige `reason` não-vazio **e** ao menos uma mudança
  real (`_comment` ou `hook` não-vazio).

**Não é recusa cega.** Anotações de ENTRADA (`hook: {...}`) continuam aceitas,
porque a derivação as aplica sempre — e há controle positivo provando que,
quando o bloco se estreita a uma entrada, o override é aceito **e escrito de
fato** (`matcher` sai `"Edit|Write"` na saída derivada).

Depois da cura, os dois casos que o revisor mostrou como `accepted` saem
`REJECTED` com mensagem nomeada; o caso legítimo (`_comment` + `reason`) segue
aceito.

## Verificação

- Guard permanente `DeclaredOverridesAreAppliedOrRejected` — 7 testes.
- **Controle vermelho** restaurando o validador pré-cura a partir do index
  (`git show :<path>`): **4 dos 7 vermelhos** — exatamente os quatro que
  afirmam as rejeições novas. Os três controles positivos passam nos dois
  estados, que é o que torna o guard discriminante em vez de recusa geral.
- Suíte da cerimônia **218 → 225**; arquivo nuclear **66 → 73**.
- `gen --check` rc 0 antes e depois: nenhuma das curas muda o que a derivação
  PRODUZ — só o que ela ACEITA declarar.

## Disposição

Sombra CURADA. A rodada 2 roda sobre a árvore curada — rodada limpa prova a
SUPERFÍCIE revisada, não o entregável, e a superfície mudou.
