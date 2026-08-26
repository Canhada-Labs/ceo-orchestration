# Pair-rail — PACOTE A, rodada 2 (S328, 2026-08-25)

**Comando:** `codex exec review --uncommitted` na mesma árvore-sombra, depois
das curas da rodada 1.
**Artefato:** `<scratchpad>/pkgA-rail-2.txt` · **rc:** 0 · **duração:** ~19 min.
**Veredito literal:** REJECT implícito — 2 achados (2× P1), sem
`VERDICT: APPROVE`.

## O que MUDOU entre as rodadas

| rodada 1 | rodada 2 |
|---|---|
| P2 — nightly de 26/08 registrado como evidência colhida | **sumiu** (curado: relabelado como conjunto ESPERADO, com a frase "registrar o resultado de uma execução futura como se fosse evidência colhida é fabricar auditoria") |
| P1 — falta sentinel | reaparece, mesma causa estrutural |
| P1 — `CLAUDE.md` contraditório | reaparece, **agora citando a própria mitigação** |

**Nenhuma classe NOVA de achado.** Os dois scripts continuam sem observação:
`scripts/install.sh` (discriminante line-exact) e
`scripts/tests/test-manifest-delivery-route.sh` (`S.17` + `S.17-control`)
passaram duas rodadas seguidas sem um único apontamento.

---

## Achado 1 — [P1] "Add a patch-bound sentinel for these guarded edits"

> `scripts/install.sh:2710-2711` — "the only signed W5 sentinels are hash-bound
> to the already-landed S327 patches; no sentinel or signature covers the
> current diff."

**Disposição: PUSHBACK, repetição da rodada 1.** Mesma causa: o rail lê a
**árvore-sombra**, que por construção não contém o pacote de cerimônia. O
sentinel novo (`PLAN-183/wave-s328-A-approved.md`) e os materiais
(`PLAN-183/s328-ceremony-A/`) existem no checkout **vivo** — medido nas duas
rodadas. A prova de que os bytes ficam autorizados é o **G5** do
`OWNER-S328-A-LAND.sh` (`_sentinel_grants_path`, a mesma função do hook), cuja
não-vacuidade o **T7** do harness demonstra (`PASS`, S328).

Este achado vai reaparecer em toda rodada futura enquanto o alvo do rail for a
sombra. **Fica registrado como limite conhecido do instrumento** e não será
re-litigado.

## Achado 2 — [P1] "Synchronize CLAUDE.md before accepting the ADR"

> `ADR-194-…:4` — "After this status flip, `CLAUDE.md:102` still says ADR-194 is
> textually `PROPOSED` and that OQ-4 was measured but not decided. … despite the
> new requirement at `ADR-194-…:293-299` explicitly requiring both updates in
> the same package."

**Disposição: REAL, permanece ESCALADO.** Verificação completa na rodada 1
(as duas frases medidas na linha 102 do HEAD `560dad0`; `CLAUDE.md` não é
canônico — oráculo 0; 32.041 bytes de 40.000; texto substituto custa +111
bytes). O path está **fora do FILE ASSIGNMENT** deste agente e o CEO também
escreve nele no closeout: curar por conta própria seria pôr dois escritores no
mesmo arquivo.

Vale notar **o que mudou na formulação**: a rodada 2 já ancora o achado na
`§7` que a rodada 1 fez nascer — o rail agora cita *"the new requirement at
`:293-299` explicitly requiring both updates in the same package"*. A mitigação
funcionou como pretendido: transformou uma inconsistência silenciosa numa
obrigação **legível**, que o próprio revisor consegue apontar. O que ela não
faz — e não pretendia fazer — é substituir a edição.

---

## Critério de parada, declarado

Paro em duas rodadas porque a rodada 2 satisfaz o critério que declarei antes
de rodá-la: **nenhuma classe nova de achado, e toda pendência com disposição
escrita.** Dos dois P1 remanescentes, um é estruturalmente insolúvel no alvo do
rail (a sombra não pode conter o pacote de cerimônia) e o outro está bloqueado
numa decisão que não é minha.

Uma terceira rodada sobre este mesmo conteúdo re-derivaria os mesmos dois —
"rodada limpa é claim, não prova", e insistir em rodadas quando a classe já foi
identificada é o instrumento errado. A rodada 3 roda sobre o patch **final**
(após o re-base no HEAD vivo), que é o artefato que o Owner assina.
