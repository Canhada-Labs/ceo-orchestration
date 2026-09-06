Rail-Verdict: APPROVE

# Rail do LAND — p171-w0-lote2 (rodada 1, árvore VIVA)

Sujeito revisado: o diff NÃO-COMMITADO da árvore viva, que é
EXATAMENTE o entregável deste land (classe S345-d). O próprio
`git status --short` que o codex rodou aparece na saída dele:

```
M  .claude/plans/PLAN-171-governance-imports-provenance.md
A  .claude/plans/PLAN-171/w0/lote-2-S347.md
M  .claude/plans/PLAN-186-orchestrator-operating-model.md
 3 files changed, 353 insertions(+), 1 deletion(-)
```

## Regra de parada PRÉ-REGISTRADA (escrita antes de ler a saída)

- P1 NOVO dentro dos paths do pack ⇒ curar no DERIVADOR + uma rodada.
- Redação / gosto / fora dos paths declarados ⇒ residual DECLARADO com
  a citação do codex e a verificação em disco.
- Rodada só com residuais ⇒ `APPROVE` com a lista abaixo.
- Nunca re-rotular um P1; nunca `APPROVE` sobre rodada incompleta.

## Lane de MECANISMO — COMPLETA

`codex exec review --uncommitted --skip-git-repo-check -c
sandbox_mode="workspace-write" -c model_reasoning_effort="max"`, da
raiz da árvore viva, pelo gate de concorrência. Saída crua fora do
repo. `rc = 0`.

Liveness: cabeçalho do CLI com `model: gpt-6-astra` (1 ocorrência); a
rodada termina com declaração PRÓPRIA de ausência de defeito acionável.
As ocorrências de «at capacity», «usage limit» e «Full review
comments:» no arquivo estão DENTRO de trechos do `CLAUDE.md` e de um
registro de rail que o codex LEU — citação, não marcador de rodada
morta (conferidas uma a uma).

A rodada não se limitou a ler: re-derivou os fatos na árvore.

- Rodou os 10 node ids da tabela do §2, extraídos do PRÓPRIO relatório
  por regex: `10 passed`.
- Apêndice C, as cinco contagens por regex: `[10, 10, 0, 0, 10]`
  (10 linhas com node id, 10 «verde», 0 vácuo, 0 sem controle, 10 com
  metade RED).
- As 10 âncoras de mutação, com `source.count(before)` e `ast.parse`
  da versão mutada: ocorrências observadas == esperadas em todas,
  inclusive `codex-filewrite` com 3.

Veredito verbatim:

> APPROVE: The documentation-only changes match the hook registrations,
> CI configuration, and census counts in the checkout. All ten
> referenced tests pass; no actionable defects were found.

Achados P1/P2 dentro dos paths do pack: **nenhum**.

## Lane de TEXTO — INCOMPLETA, sem veredito lido

Lançada em paralelo (brief no stdin, `--sandbox read-only`,
`model_reasoning_effort="max"`, escalonada > 60 s da primeira). No
momento do land o processo AINDA ESTAVA VIVO (`lsof` no próprio
arquivo de saída = 2 descritores do `node`, arquivo crescendo:
163 KB → 313 KB). Rodada incompleta **não é rodada**: nenhum veredito
foi lido dela e ela NÃO é contada. O land se apoia na lane de
mecanismo, que é a exigida pelo modelo de operação v2 e está completa.

## Residuais DECLARADOS (nenhum bloqueia o land)

1. `EVIDENCE.md` §8 e `raw/plan-edit-oracle.txt` imprimem
   `added_bytes = 959`. Verificado por mim em disco: o delta de
   CARACTERES é 959, o de BYTES é 992 (a linha anexada tem UTF-8
   acentuado) — é uma contagem de caracteres rotulada como bytes. O
   defeito é de RÓTULO e está FORA dos bytes landados (`EVIDENCE.md`
   não é commitado). A afirmação que ele sustenta reproduz:
   `pure_append = True`, `decide -> Decision(allow=True, reason=None)`
   e `decide_write -> Decision(allow=True, reason=None)`. Achado
   originalmente pelo refutador do pack.
2. Os DOIS validadores bloqueantes do trem de release
   (`.github/scripts/validate-pair-rail-verdict.py`,
   `.claude/scripts/local/_release_tag_guard.py`), que o §3 do
   `lote-1-S345.md` mandou «para o lote 2»: não são hooks
   REGISTRADOS, logo não estão em `R` e não são desta fatia. Dívida
   NOMEADA no §5 do relatório — redução de escopo tornada VISÍVEL.
3. Os 11 hooks de disco sem registração + `check_harness_config.py`
   (executado direto pela CI) + o registry do trilho Codex: mesma
   dívida, mesmo §5, derivados por `remainder.py`.
4. O censo prova que o CÓDIGO produz a saída de enforcement e que o
   TESTE a enxerga; NÃO prova que o matcher dispara em campo.
   Declarado no §3 do relatório.
5. `check_adversary`: só a rota `deny` com enforcement LIGADO foi
   medida; a rota `ask` e a advisory-off têm testes próprios,
   declarados na célula da linha 1.

## Bateria e gates deste land (todos `rc 0`)

- pytest dos 10 node ids: `10 passed`.
- `validate-governance.sh` COMPLETO: `Errors: 0`, `Warnings: 65`,
  `PASS`; `verify-counts.sh`: sem drift, `observed = 15724`;
  `check-claude-md-claims.py`; `check-staleness.py`;
  `check-test-env-hygiene.py` (337 flagged, todos allowlisted);
  `check_contamination.py`: sem contaminação fora das zonas.
- `CLAUDE.md` = 39 729 bytes (limite 40 000).
- Oráculo canônico: `0` nos três paths staged.
- O diff dos DOIS paths do pack na árvore viva é BYTE-IDÊNTICO ao
  derivado numa worktree limpa em `HEAD` (mesmo sha256).
