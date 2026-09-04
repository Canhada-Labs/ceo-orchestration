# p183-ac2-evidence — rail de land, rodada 1 (S344, 2026-09-04)

Rail-Verdict: CHANGES-REQUESTED (2 P1 + 3 P2 — todos verificados REAIS; curados no derivador antes da r2)

Duas lanes codex em PARALELO sobre a ARVORE VIVA (nao sobre sombra):
`codex exec review --uncommitted` e `codex exec` com briefing das claims.

## Achados e cura

1. **[P1, lane B] O gate de whitespace ficava VERMELHO.**
   `git diff --cached --check` rc 2: os dois arquivos novos terminavam com
   linha em branco no EOF (`github-run-33896213436.md:484`,
   `smoke-install-runs.md:94`). Verificado por mim em bytes (`od -c` -> `\n\n`).
   CURA: newline final normalizado no payload e os dois digests do derivador
   re-pinados. Pos-cura `git diff --cached --check` rc 0.
   Nota: `git diff --check` NAO esta ligado como gate de CI neste repo
   (grep em `.github/workflows/` e `.claude/scripts/`: zero sitios) — o
   achado e defeito de higiene real, nao um vermelho de CI iminente.

2. **[P1, lane A] A evidencia commitada nao AMARRA o run verde aos BYTES
   do template entregue.** O objeto capturado tem nome de workflow, nomes
   de passo, status e timestamps — nao o blob, nao os corpos `run:`, nao as
   referencias de action, nao a saida do installer. NAO curavel offline (o
   repo descartavel e PRIVADO e ARQUIVADO). CURA POR ESTREITAMENTO: a secao
   «What these runs prove, and what they do not» passa a dizer explicitamente
   que offline se obtem concordancia de NOME (os onze nomes de passo BATEM o
   template em `bc52016` — verificado por mim, ver abaixo), nao amarracao
   criptografica; que o `cmp` e testemunho da sessao que capturou, nao
   evidencia re-checavel; e que o fecho do AC-2 se apoia no criterio ESCRITO
   do Owner (`PLAN-183/owner-decisions-S344.md`), nao em reproducao byte a byte.

3. **[P2, lane A] «no side files» versus um verificador que nao viaja.**
   `verify-quotes.py` vive no pack de sessao, nao no repositorio. CURA: a
   frase passa a dizer que o CHECKER nao esta no repo e que o que dispensa
   arquivos ao lado sao os DADOS (render e JSON no mesmo arquivo, conferiveis
   a olho ou por qualquer renderizador).

4. **[P2, lane A] `mv -n` sai 0 SEM mover quando o destino existe**, deixando
   o workflow INERTE em silencio — na colisao que o proprio texto antecipa.
   CURA: `benchmarks.yml.template` passa a dizer isso e manda o adopter
   conferir se o rename aconteceu, ou escolher outro nome, antes de commitar.
   O cabecalho cresce de 3-10 para 3-12 linhas e as DUAS citacoes desse
   intervalo migram na mesma derivacao (`validate.yml.template:12` -> 3-12;
   nota do plano `:5-10` -> `:5-12`). Verificado contra o disco depois de aplicar.

5. **[P2, lane B] O item da W2 dizia «a nota do AC-2 acima»** e a nota esta
   ABAIXO (item :1276, nota :1369). CURA: «abaixo».

## O que a lane B confirmou de forma independente

Os 11 nomes de passo do run batem o template em `bc52016`; os renders de JSON
reproduzem exatamente; os intervalos citados batem o disco; a varredura de dado
sensivel esta limpa. Reproduzi as tres coisas: censo por regex dos blocos de log
(13/13, igual em CONJUNTO e ORDEM nos dois runs) e comparacao nome a nome dos
onze passos contra `git show bc52016:templates/.github/workflows/validate.yml.template`.
