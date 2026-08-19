# Pair-rail round 3 — PLAN-179 pack · 2026-08-19

**2 achados, ambos NOVOS.** Convergência: **9 → 4 → 2**, sem repetição — o rail
parou de achar o que já foi curado e passou a achar camadas mais fundas.

## [P1] Primitivo de ESCRITA ARBITRÁRIA por symlink — introduzido por MIM

> When an agent can write the gitignored `.claude/state` directory, it can
> pre-create the predictable `.<marker>.<session>.<pid>.tmp` path as a symlink.
> This `open(..., "w")` and the following `chmod` both follow that symlink
> before `os.replace`, allowing the hook to truncate or chmod a canonical or
> external file and bypass normal write guards.

Não era teórico. **Controle negativo, contra o código pré-fix**
(`control-symlink-negative.py`): plantado um symlink em
`.claude/state/.<marker>.<pid>.tmp` apontando para um arquivo alvo, o hook
seguiu o link e **truncou a vítima de 44 para 3 bytes**, gravando `60\n` (o
valor do bucket) dentro dela.

```
PLANTED_EXACT_PATH=True
VICTIM_SIZE_BEFORE=44 AFTER=3      <-- truncada
VICTIM_INTACT=False
CONTEUDO FINAL DA VITIMA: '60\n'   <-- escrita arbitraria
```

**Cura, e por que é estrutural e não probabilística.** Três coisas juntas:
`O_EXCL` (recusa path existente), `O_NOFOLLOW` (recusa symlink mesmo se ele
aparecer entre a checagem e o open) e sufixo aleatório no nome (torna o
pre-plant inviável). O modo `0600` passa a ser dado **na criação**, o que
também fecha a janela que o `chmod` separado deixava.

**Controle positivo** (`control-symlink-positive.py`) — a versão dura: com
`os.urandom` fixado, o nome do tmp fica **previsível**, o symlink é plantado no
path EXATO que o código usará, e mesmo assim:

```
PLANTED_EXACT_PATH=True
VICTIM_SIZE_BEFORE=44 AFTER=44     <-- intacta
VICTIM_INTACT=True
SYMLINK_STILL_THERE=True           <-- a escrita RECUSOU, nao seguiu
```

Isto separa "o atacante não adivinha o nome" (fraco) de "mesmo sabendo o nome,
não funciona" (o que se quer).

## [P2] O rail pegou uma AFIRMAÇÃO FALSA que eu escrevi

> The claim that the next run resumes where iteration stopped is false because
> no cursor is retained.

No round 2 eu limitei o GC com uma janela de prefixo fixa e escrevi no
comentário que "a próxima execução continua de onde a iteração parou". **Não
continua** — nada persistia cursor algum. Um arquivo expirado atrás de um
prefixo de arquivos frescos nunca seria recuperado.

Cura nos dois GCs: a janela começa num **offset rotativo derivado do relógio**,
então execuções sucessivas cobrem fatias diferentes. E o comentário agora diz a
verdade: a cobertura é **probabilística**, não garantida — um cursor real
exigiria estado próprio que este caminho de housekeeping não justifica.

## Nota de método: o revisor leu a evidência do round 1

O clone do round 3 continha `PLAN-179/rail-round-1/VERDICT.txt`, que eu havia
commitado, e o Codex o leu durante a exploração (`--- rail verdicts ---` no
transcript). Isso quase me fez ler o veredito ERRADO: um `grep` pelo primeiro
`REJECT:` casou o texto do round 1 citando paths de `.w179-rail/repo`. O
veredito real estava no fim do transcript, citando `.w179-rail3/repo`.

Lição para a próxima rodada: **confirme o `workdir` nos paths do veredito**
antes de acreditar nele. Manter a evidência no repo continua certo (trilha
auditável), mas ela entra no contexto do próximo revisor.
