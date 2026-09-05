Rail-Verdict: CHANGES-REQUESTED (rodada 1 do LAND, 2 lanes codex em paralelo: MECANISMO 3 achados, TEXTO 3 achados; 3 defeitos REAIS distintos, todos CURADOS no derivador; 2 residuais DECLARADOS)

# Rail do LAND — rodada 1 — pack `p171-w0-lote1` (S345)

Rodada sobre a ÁRVORE VIVA (o diff que de fato aterrissa), não sobre a
sombra do pack. As duas lanes rodaram em paralelo pelo `codex-gate.sh`,
lançadas com mais de 60 s de intervalo, uma por chamada.

- **Lane de MECANISMO:** `codex exec review --uncommitted --skip-git-repo-check`
  (`sandbox_mode=workspace-write`, `model_reasoning_effort=max`).
  VIVA: o bloco final `Full review comments:` está presente.
- **Lane de TEXTO:** `codex exec --sandbox read-only` com brief no stdin
  (1 927 bytes). VIVA: `tokens used` presente (188.519).
- Nenhuma das duas saídas contém `usage limit`.

As duas lanes convergiram nos MESMOS dois defeitos centrais, por
caminhos diferentes. Cada achado abaixo foi verificado POR MIM no disco
antes de ser aceito; nenhum foi aceito pela leitura do texto do codex.

## Achado 1 — P1 (as DUAS lanes) — a dívida `overhead` não nomeava o arquivo que a fecha

> TEXTO: «The execution log says every one of the three debts has a closing
> file named in §2 …, but the overhead row names no file at all …
> The underlying PLAN-169 entry names `docs/TROUBLESHOOTING.md`, its PT-BR
> counterpart, and `check_anti_ceo_overhead.py`.»
>
> MECANISMO [P2]: «The overhead row … only repeats PLAN-169 closure prose and
> names no file or line, contradicting the new claim in
> `.claude/plans/PLAN-171-governance-imports-provenance.md:228-230`.»

**Verificação no disco, antes de aceitar.** A linha de `## Registro de
execução` que o derivador acrescenta ao plano afirma «uma linha por
dívida, **com o arquivo que a fecha**». Das três linhas do §2 do
relatório, duas nomeavam arquivo (`pair-rail-gate.sh:64-83`;
`inject-agent-context.sh:798-805` e `:903`) e a terceira — `overhead-ack`
— nomeava NENHUM. O achado REPRODUZ: era um fato falso num arquivo
ENTREGUE. `PLAN-169-closure-and-cross-session-evolution.md:1664` (lido
por mim) nomeia `docs/TROUBLESHOOTING.md` / `.pt-BR.md` (W2.4) e
`.claude/hooks/check_anti_ceo_overhead.py` em `e5ce982`; os dois
arquivos existem e `e5ce982` é um commit real desta árvore
(`ceremony(PLAN-169 W3): pack canonico landado …`).

**Cura (edit E1 do `cure-r1.py`, no PAYLOAD do derivador):** a linha do
§2 passa a nomear os três arquivos com a atribuição de onde eles vêm
(«nomeados pelo PRÓPRIO 169 na linha C.3, l. 1664») e declara o limite
que a lane de mecanismo apontou na segunda metade do mesmo achado — o
W0 auditou o REGISTRO e **não** re-exercitou `CEO_OVERHEAD_ACK` num
`Write`; o controle do §1 prova o BLOQUEIO, não a rota de override.

## Achado 2 — P1 (TEXTO) / P3 (MECANISMO) — a saída citada não é a que o comando produz

> TEXTO: «Running the command shown at lote-1-S345.md:263 on the staged tree
> also prints the beginning of the `PLAN-183` degraded block and a `--`
> separator between the two `PLAN-171` match groups. Lines 265-276 omit both
> without an ellipsis.»
>
> MECANISMO: «The command … matches both the PLAN-171 finding header and its
> `path:` line, so `grep -A4` necessarily includes context from the following
> PLAN-183/PLAN-172 blocks and a `--` separator … match the header
> specifically or label the displayed text as an excerpt.»

**Verificação no disco, antes de aceitar.** Rodei eu mesmo, na árvore
com a derivação aplicada: `grep -A4 -F PLAN-171` casa o cabeçalho do
achado **e** a linha `path:`; a partir do `path:` o `-A4` arrasta o
começo do bloco do PLAN-183 e o `--`. O bloco citado no Apêndice E
omitia os dois. O achado REPRODUZ.

**Cura (edits E2/E3/E4/E5):** o comando das DUAS metades passa a
ancorar no CABEÇALHO (`-F 'plan       PLAN-171'`), que não casa a linha
`path:`; a saída DEPOIS ganha o `--` que o próprio `grep` imprime entre
grupos não contíguos; e a frase explicativa deixa de dizer «o começo do
próximo bloco» e passa a descrever o discriminante medido.

**Controle de que a cura vale:** um script compara, byte a byte, o bloco
citado no arquivo entregue contra a saída REAL do comando citado, nas
duas metades. Antes da cura o bloco DEPOIS DIVERGIA; depois, os dois
comparam `QUOTED==REAL: True` (ANTES e DEPOIS). A metade ANTES foi
capturada da árvore LIMPA (que é exatamente o estado `reviewed`), não
recitada de memória.

## Residual DECLARADO 1 — «0 UNREGISTERED» (TEXTO, P1 alegado — REBAIXADO)

> «the census `0 UNREGISTERED` definition excludes two rows that have no
> settings entry.»

**Não reproduz como fato falso.** A linha de contagem define o termo NA
PRÓPRIA FRASE («no sentido de "gate que deveria estar em `settings.json`
e não está"») e ENUMERA as três exceções com o motivo de cada uma
(host `accel_dispatch`, biblioteca, script de operador); as linhas #6,
#7 e #8 da tabela dizem «**não tem registro próprio**» / «**sem registro
de hook**» em texto claro. Nada é escondido; a objeção é de REDAÇÃO
(preferir outro nome para a contagem), não de fato. A lane de MECANISMO,
que leu os mesmos arquivos, não levantou este ponto. Fica DECLARADO.

## Residual DECLARADO 2 — evidência machine-readable não rastreada (MECANISMO, P2)

> «`node-ids.txt`, `red-half.json`, and an unnamed `EVIDENCE.md` … none is
> tracked … commit the pack under a stable path or inline its
> machine-readable contents.»

**Reproduz, e está FORA dos paths declarados do pack.** O relatório já
diz, em texto, que esses arquivos «vivem no pack da sessão». Rastreá-los
significaria commitar um diretório que NENHUM pack declarou — exatamente
a bandeira vermelha que este land não pode levantar. Fica DECLARADO para
uma wave que decida a política de arquivamento de packs; não é curável
dentro dos dois paths deste pack.

## O que NÃO mudou

Nenhum path canônico foi tocado (`--is-canonical` = 0 nos dois paths,
lido do stdout, nunca do exit code). O conjunto de paths continua sendo
exatamente os dois declarados. As dez linhas do censo, os dez node ids e
as duas metades do controle positivo não foram alteradas pela cura — a
metade VERDE foi re-rodada depois dela: `10 passed`.
