# wave-adrgate — rail codex rodada 1 (sombra base 5df5c48, 2026-08-31 S334)

Rail-Verdict: CHANGES-REQUESTED (0 P1, 1 P2 — REAL; curado ANTES da r2)

Comando: `codex exec review --uncommitted --skip-git-repo-check -c sandbox_mode="workspace-write"`,
rodado DO diretório da sombra, stdin `</dev/null`. Saída bruta:
`<scratchpad S334>/adrgate-r1.txt`. Snapshot sha256 dos 4 paths antes/depois:
TREE INTACT.

## O achado (P2, real — e é a classe FU-ADR-README-SEED chegando por outra porta)

> Keep framework-only exemptions out of the adopter seed — README.md:83
> On a fresh install, `scripts/install.sh:1654-1663` copies this README but
> no framework ADRs, while `install_scripts_selective` also ships
> `check-adr-chain.py`. These mandatory-fire entries are therefore
> immediately stale in the installed tree: running the shipped checker exits
> 1 with two "did not fire" errors, and adopters later reusing these IDs
> could instead suppress unrelated broken edges.

Verificado: verdadeiro nos dois braços. O install semeia o README (com o
ledger) E entrega o checker; o corpus do framework NÃO viaja. Sem cura, todo
adopter nasceria com `check-adr-chain.py` rc 1 — vermelho falso permanente —
e a alternativa ingênua (entrada por id nu sem N/A) abriria supressão
indevida para um ADR homônimo do adopter.

## A cura (arquitetura, não remendo — landada LIVRE no vivo nesta rodada)

Dois mecanismos ortogonais em `check-adr-chain.py`:

1. **N/A por ausência do declarante:** entrada cujo id-base do declarante
   não existe no corpus não é fired nem stale — não há bug nomeável nem
   supressão possível ali. Cura o adopter (corpus sem os ADRs do framework
   ⇒ seção inteira inerte, rc 0).
2. **Stem-pin:** as entradas do README usam o STEM COMPLETO
   (`ADR-120-pii-core-promotion`), e um token com stem só casa o arquivo
   cujo stem on-disk é IGUAL. Adopter que recrie `ADR-120-minha-coisa.md`
   com `Supersedes: ADR-111` NÃO herda a supressão — e como o id-base passa
   a existir sem firing, o mandatory-fire ACUSA a entrada (o caso
   humano-olha, exatamente como deve ser).

Testes: 49 → 52 (N/A do adopter; stem casa; stem divergente recusa E
mandatory-fire acusa). A seção do README na sombra re-derivada carrega a
gramática nova e as entradas com stem.

## Disposição do braço "keep out of the adopter seed"

A metade "não semear o README do framework no adopter" é o
`FU-ADR-README-SEED` (família A7, decisão de produto do Owner) — fica onde
está, com esta rodada citada como segunda evidência de que o seed atual é
contaminante. A cura desta wave torna o ledger INOFENSIVO no adopter
independentemente daquela decisão.
