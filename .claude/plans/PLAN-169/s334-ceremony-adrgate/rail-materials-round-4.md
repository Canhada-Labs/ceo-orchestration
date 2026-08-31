# wave-adrgate — rail de MATERIAIS rodada 4 (o critério da r3 DISPAROU; redesenho)

Rail-Verdict: CHANGES-REQUESTED (3 P2 — a família transacional pela 3ª vez
⇒ ARQUITETURA trocada, não um 4º boolean; verificação na r5)

Saída bruta: `<scratchpad S334>/adrgate-materials-r4.txt`. Cure-trace da
r4: 5 das 8 curas r2 **PASS** definitivo (incl. `_override_granted()`
vivo = True e `_land_rc` primeiro); as 3 restantes eram a mesma família.

## Os 3 achados

1. `STAGED_BY_LAND` herdável do ambiente + setado só DEPOIS do loop de
   add (add parcial ficava fora da cobertura).
2. O rollback do finalize destruía index pré-existente dos 4 materiais
   (reset incondicional; index-only content de terceiro perdia-se).
3. O harness não tinha cobertura executável das curas r3 — `PASS=21` era
   cego aos dois acima.

## O redesenho (o que o revisor pediu verbatim: "preserving exact
pre-state rather than adding another Boolean patch")

- **Finalize:** o backup captura o pré-estado EXATO nas DUAS dimensões —
  worktree (bytes ou ausência) E **index** (`git diff --cached --binary`
  dos 4 materiais). O rollback zera o staged deles e RE-APLICA o patch
  capturado (`git apply --cached`): index-only content de terceiros
  atravessa qualquer abort byte a byte; falha de re-apply degrada com
  AVISO apontando o patch preservado.
- **LAND:** `STAGED_BY_LAND=0` no init (nunca herdado) e `=1` ANTES do
  loop de add (add parcial já autoriza o des-stage).
- **Harness T22 (cobertura executável de verdade):** a sombra do clone
  nasce do próprio `ADRGATE.patch` commitado, a bateria curta do
  finalize passa DE VERDADE, o gerador roda, o abort cai no guard
  pré-add com um PROPOSED carregando conteúdo INDEX-ONLY plantado — e as
  asserções provam o marcador vivo no cached + worktree byte-idêntico.

Harness: `PASS=22 FAIL=0 SKIP=0`.
