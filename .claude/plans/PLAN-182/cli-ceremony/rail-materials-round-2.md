# Pair-rail — materiais de cerimônia (árvore viva), rodada 2 (S326, 2026-08-24 16:36–16:5xZ)

**Instrumento:** `codex exec review --uncommitted` na árvore VIVA (pedido pelo Stop-hook). Escopo:
scripts SIGN/LAND, sentinel-draft, patch finalizado, registros de rail, e o censo da W0 do PLAN-185
após a 2ª passada do agente.

**Resumo do revisor (verbatim):** *"The new security census has multiple reproducible fail-open
classifications that allow unsafe shell forms to bypass the baseline. The landing workflow can also
stage unrelated changes that it explicitly allowed outside the signed patch."*

## Materiais da cerimônia (este pacote)

| # | Sev | Achado | Verificação | Disposição |
|---|---|---|---|---|
| 1 | P1 | `OWNER-S326-LAND.sh` passo S: `git add -u` stageia toda modificação rastreada do repo, inclusive o que o G0 tolerou fora do patch. | **CONFIRMADO** — o mesmo achado da r6 do pacote (mesma leitura, revisor viu a versão anterior do LAND). | **JÁ CURADO (patch T, antes desta leitura):** staging por path explícito = `touched(patch) ∪ {sentinel, .asc}`, conjunto staged comparado ao esperado, diverge ⇒ ABORTA. Controles positivo/negativo em repo temporário. A r7 do pacote revisa a versão curada. |

Consequência de sequência: o SIGN exigia árvore inteiramente limpa; com o staging exato, um
UNTRACKED não-canônico (ex.: os arquivos da W0 do 185 ainda não commitados) nunca entra no land —
o P0 do SIGN passa a exigir "sem modificações RASTREADAS; untracked tolerado só se o oráculo disser
0; untracked canônico ⇒ aborta".

## Censo da W0 do PLAN-185 (fora do pacote — devolvido ao agente, 3ª passada)

Sete achados P1, todos fail-open no matcher: predicado negado na mesma linha (regex nunca casa);
condições compostas (`||`/`&&`) avaliadas só pela negação do teste; `|| return` creditado sem
polaridade; `rm`/`unlink` condicional creditado como guarda; `cp -P` (flag de ORIGEM) creditado como
no-follow de destino; varredura para no primeiro write alcançável; `sed -e"…"`/`--expression=`
descartados como opção genérica. **Disposição:** encaminhados ao agente `sec-185-w0` como terceira
passada obrigatória, com controle positivo NOVO por forma; o censo não entra na cerimônia.
