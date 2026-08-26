# Pair-rail — wave-s328-B, rodada 2

Comando: `codex exec review --uncommitted` na árvore-sombra
`<scratchpad>/shadow-163` (base `a16ac96`), saída em `pkgB-rail-2.txt`.
Substrato: `codex-cli 0.147.0`. rc 0, saída não-vazia.

**Veredito da rodada:** REJECT — 1 × P1, 0 × P2.

---

## O que MUDOU em relação à rodada 1

Três dos quatro achados da rodada 1 **não voltaram**:

| rodada 1 | rodada 2 | por quê |
|---|---|---|
| **P1-2** rc 5 mislabeled no wrapper | **ausente** | curado no texto da ADR-163 (o parágrafo «Known defect» foi reescrito: o auto-cap RENOMEIA em vez de remover; fase 1 é imune por construção; distinguir rc 5 é pré-condição NOMEADA da fase 2) e o sentinel foi reconciliado no mesmo sentido |
| **P1-3** sentinel ausente para o ADR-144 | **ausente** | — |
| **P2-4** OQ-7..OQ-12 inexistentes | **ausente** | — |
| **P1-1** flags não implementadas | **repetiu** | ver abaixo |

O P1-2 era o único achado de CONTEÚDO da rodada 1 e fechou. Que os P1-3/P2-4
não tenham voltado é informativo, mas não é prova de cura: nenhum byte mudou
neles entre as rodadas, então a variação é do revisor, não da árvore. O que
vale para os dois continua sendo o registro da rodada 1.

## P1-1 (repetido) — «Implement the profiler flags before enabling them» (`validate.yml:1272-1273`)

**Claim.** `profile-opus-4-7.py:724-799` não define `--exec-reference` nem
`--relative-advisory`, e `run_hook_latency` não tem comportamento de referência;
a invocação sairia 2 no parse de argumentos em toda tentativa.

**Verificação — VERDADEIRA sobre a árvore lida, e ela NÃO pode deixar de ser
verdadeira nesta sombra.** Medido de novo no momento desta rodada:

```
HEAD vivo                              560dad0
profiler em HEAD com --exec-reference       0
teste do gate em HEAD                       0 linhas
```

A sombra está baseada em `a16ac96` e o `HEAD` vivo é `560dad0`; **nenhum dos
dois** carrega a metade não-canônica, que segue como modificação de árvore de
trabalho (`+794/−17` no profiler, mais o arquivo de teste novo) à espera do
commit comum do CEO. Enquanto isso for verdade, QUALQUER rodada de rail nesta
sombra reproduz este achado — não porque a cura falhou, mas porque o revisor
está lendo metade do trabalho.

**Isto não é a classe «achado que regenera».** O padrão que exige trocar a
arquitetura da cura é o achado que volta *depois de uma cura*, com forma nova.
Aqui não houve cura textual nenhuma a falhar: o diagnóstico é único, correto e
já tem cura MECÂNICA — que o revisor não pode ver, porque ela vive fora da
sombra, no `OWNER-S328-B-LAND.sh`.

**Cura (inalterada desde a rodada 1), no gate `G-PRE` do LAND:**

- lê o profiler de **`git show HEAD:`**, não da árvore de trabalho — hoje a
  árvore passaria e o HEAD não, então checar a árvore mediria a coisa errada;
- exige as **4 flags** declaradas em `EXPECTED_HELP_FLAGS`;
- exige `test_hook_latency_relative_gate.py` presente em HEAD;
- exige ≥ 6 referências a `OQ-7..OQ-12` em HEAD (o P2-4 da rodada 1);
- **aborta nomeando** o que falta e dizendo qual commit resolve.

**Critério de parada declarado.** A rodada final deste pacote será executada
numa sombra **rebasada no HEAD que já contiver a metade não-canônica** (passo
de refresh do `finalize-B.sh`). Ali este achado ou desaparece — e a superfície
fica provada como um todo — ou é real, e o pacote não fecha. Rodar mais rodadas
contra `a16ac96` só re-mediria a mesma ausência.

---

## Balanço

| # | severidade | veredito | ação |
|---|---|---|---|
| P1-1 | P1 | verdadeira sobre a sombra, estruturalmente inevitável nela | cura MECÂNICA já existente (G-PRE); re-rodar após o refresh da sombra |

Nenhum achado de conteúdo novo. Nenhuma edição na sombra nesta rodada.
