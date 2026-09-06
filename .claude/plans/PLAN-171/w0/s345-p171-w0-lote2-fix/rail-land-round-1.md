Rail-Verdict: APPROVE

# Rail do LAND — s344-land-combined, rodada 1 (S347, noite autônoma)

Pacote único: `p171-w0-lote2-fix` (cura pós-land do relatório do lote 2
do censo W0 do PLAN-171). UM path: `.claude/plans/PLAN-171/w0/lote-2-S347.md`
(196 inserções / 17 remoções). Oráculo `--is-canonical` = 0 (pacote LIVRE).

## Regra de parada (PRÉ-REGISTRADA, antes de ler qualquer saída)

Herdada de `STOP-RULE.md` do pacote, escrita antes da rodada 1 do build:
P1 NOVO dentro do path do pacote ⇒ cura PELO DERIVADOR + mais uma rodada
(teto 1 cura); redação, achado fora do path, ou follow-up já nomeado ⇒
residual DECLARADO com o texto do codex citado; rodada só com residuais
termina `Rail-Verdict: APPROVE`. Nunca rebaixar um P1; nunca APPROVE em
rodada incompleta. As DUAS pistas têm de estar terminadas (`lsof` sem
escritor + bloco terminal próprio) antes de qualquer leitura ou commit.

## Pistas (as duas rodaram em paralelo, escalonadas 75 s)

### Pista MECANISMO — `codex exec review --uncommitted` na árvore VIVA
- Liveness: `model: gpt-6-astra` na l. 5 do cabeçalho do próprio CLI;
  0 `Selected model is at capacity`, 0 `Review was interrupted`,
  0 `usage limit`; `lsof` sem escritor antes da leitura.
- As DUAS ocorrências de `Full review comments:` no arquivo (l. 558 e
  l. 920) são CITAÇÃO do `CLAUDE.md` §5 ecoado como contexto (a própria
  frase «rodada limpa = ausência do bloco `Full review comments:`»),
  verificadas por número de linha — não são o bloco de achados do review.
  O bloco terminal PRÓPRIO da pista é o `codex` final.
- Veredito, verbatim: «APPROVE. The revised advisory classifications and
  counts match the source. The cited opt-in controls pass, and disabling
  enforcement in memory produces the documented failure.»

### Pista TEXTO — `codex exec` com brief no stdin (16.456 bytes)
- Liveness: `model: gpt-6-astra` na l. 5; bloco `tokens used` próprio
  (130.573); 0 marcadores de morte; `lsof` sem escritor.
- O revisor re-derivou o arquivo staged INTEIRO em memória a partir do
  HEAD e dos inputs do pack (`assert reconstructed.encode() == staged`),
  conferiu que o staged é byte-idêntico à sombra revisada
  (sha256 `e804c0d1…f954ed`), re-derivou por AST os três controles
  citados do Apêndice F e leu a evidência dinâmica do JSON bruto.
- Veredito, verbatim: «APPROVE — no P1/P2 findings in the staged diff.»
  com «Appendix C reproduces 10 / 10 / 0 / 0 / 10», «Appendix F
  reproduces 0 / 0 / 1 blocking constructs», «Generated content matches
  staged bytes exactly», «No personal absolute path introduced».

## Achados

NENHUM P1 e nenhum P2 nas duas pistas. Rodada 1 LIMPA; parada pela regra
pré-registrada (≥ 1 rodada limpa, teto de 2).

## Residuais DECLARADOS (todos PRÉ-EXISTENTES e NOMEADOS no próprio relatório)

1. `PLAN-171-FOLLOWUP-lote2-generated-figures` — as figuras literais de
   §1, §4, §5 e dos Apêndices A/B/D continuam vindo do `gen-report.py` do
   pack do lote 2; só a contagem do §2 e o Apêndice C foram convertidos
   para geração por instrumento nesta cura. Fora do teto do modelo v2.
   A pista TEXTO registra o mesmo: «remaining literal figures are
   explicitly deferred».
2. `PLAN-171-FOLLOWUP-readinjection-docstring` — o docstring de
   `.claude/hooks/check_read_injection.py` (l. 44-48) ainda diz «This hook
   is advisory — it always allows», contradizendo a l. 30-33 do MESMO
   arquivo. Oráculo `--is-canonical` = 1: sai por cerimônia GPG, nunca por
   pacote livre. Fora do path deste pacote.
3. Limites do detector do Apêndice F (LOCUS / LITERALIDADE / VOCABULÁRIO /
   ENV), agora GERADOS como COMPLEMENTO dos conjuntos impressos em vez de
   enumerados à mão. Herdados pelos lotes 3-6.
4. Proveniência do Apêndice F: o texto diz `HEAD = bb68edf55413`, a árvore
   que foi MEDIDA. Verificado nesta rodada que
   `git diff --stat bb68edf HEAD -- .claude/hooks/` é VAZIO — nenhum dos
   três hooks medidos mudou entre a medição e o land; a re-medição no HEAD
   vivo devolveu `0 / 0 / 1`, idêntica.

## Rodadas anteriores (do build, sobre a SOMBRA — não substituem esta)

r1 texto REJECT (2 P1 reais, curados pelos instrumentos), r2 mecanismo
APPROVE, r3 mecanismo de CONFIRMAÇÃO APPROVE. Registros no pack.
