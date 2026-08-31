# W2 — ensaio do AC de saída: kill-mid-unit + recuperação pelo LEDGER (S334, 2026-08-31)

**Veredito: RECUPERAÇÃO COMPLETA (rc=0), em clone descartável, sem
arqueologia de git.** O AC de saída da W2 ("matar uma sessão no meio de
uma unidade e abrir uma nova recupera o estado a partir do ledger")
está EVIDENCIADO.

## Forma do ensaio (dois PROCESSOS, morte real entre eles)

Instrumento: script efêmero de sessão (scratchpad S334), transcrito
abaixo em substância. Clone `git clone --local` do HEAD `c6fa06f` para
tmpdir descartável — nunca o repo vivo.

- **Fase A (sessão que morre):** escreve no `PLAN-179/LEDGER.md` do
  clone uma unidade em progresso `U-REHEARSAL` no contrato do
  `check_ledger_checkpoint.py` — unidade corrente, `last-commit` (SHA
  40-hex), decisão tomada, bloqueio aberto, próximo passo, e **3 ACs com
  verifier nomeado** (`verifier: `cmd` exit=N`), incluindo um verifier
  deliberadamente NEGATIVO (`exit=1` declarado, para provar que o leitor
  compara exit code em vez de aceitar sucesso). Commita a fronteira
  (`[skip-ledger]`, `--no-verify` — o ensaio testa o CONTEÚDO do ledger,
  não o hook) e o processo TERMINA. Nada do estado da fase A sobrevive
  fora do ledger.
- **Fase B (sessão nova, processo separado):** lê SÓ o `LEDGER.md`
  (nenhum `git log`/`git show`; um único `rev-parse` serve para CONFERIR
  o claim de `last-commit` do ledger, não para descobri-lo), reconstitui
  unidade/decisão/bloqueio/próximo-passo e EXECUTA cada verifier,
  comparando o exit observado com o declarado.

## Resultado (transcript da execução)

```text
[fase A] fronteira commitada no clone; sessão MORTA. head-antes-da-unidade=c6fa06f06d19
last-commit reconstituído: c6fa06f06d19 OK
campo 'decisão:': OK
campo 'bloqueio aberto:': OK
campo 'próximo passo declarado:': OK
verifier `test -f .claude/plans/PLAN-179/LEDGER.md` exit=0 (declarado 0) OK
verifier `python3 -c "import sys; sys.path.insert(0, '.claude/hooks'); import _lib.ledger_provenance"` exit=0 (declarado 0) OK
verifier `test -f .claude/plans/PLAN-179/NAO-EXISTE.md` exit=1 (declarado 1) OK
[fase B] recuperação COMPLETA (fails=0)
RC=0
```

## O que o ensaio prova — e o que não prova

- **Prova:** o CONTRATO do ledger (identificadores verbatim + verifier
  por AC) é suficiente para uma sessão nova reconstituir e VERIFICAR o
  estado de trabalho sem ler histórico de git. O verifier negativo
  batendo (`exit=1` declarado = observado) mostra que a verificação é
  comparação real, não wishful matching.
- **Não prova:** que uma sessão real ESCREVE o checkpoint na fronteira
  (isso é o observatório advisory do `check_ledger_checkpoint.py`,
  janela measure-first — enforce é cerimônia futura com tabela
  would-block/TP-FP); nem cobre US7 (PreCompact→índice do ledger), que
  segue aberto.
