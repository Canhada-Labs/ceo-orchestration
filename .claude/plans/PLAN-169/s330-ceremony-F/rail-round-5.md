# Pacote F — rail codex rodada 5 (shadow-F curada da r4, CONGELADA, 2026-08-30 ~15:20 -03)

Rail-Verdict: CHANGES-REQUESTED (1 P1 + 2 P2, os três reais, os três curados)

Comando: `codex exec review --uncommitted --skip-git-repo-check -c sandbox_mode="workspace-write"`,
via `rail_round.sh`. Modelo `gpt-5.6-sol`, esforço xhigh. Saída bruta:
`<scratchpad efd20343>/rail/r5.txt`. Wrapper: **TREE INTACT** (a lição da r4
aplicada — nenhuma edição concorrente).

## Achados

- **[P1] Verificar BYTES, não o porcelain** — `gen-settings-user-template.py:1018-1021`.
  Dois furos na cura da rodada 4: (a) um spec marcado `assume-unchanged` /
  `skip-worktree` e depois editado faz `git status --porcelain` reportar
  **limpo** — a flag de índice manda o git parar de olhar; (b) o **código de
  retorno** do `git status` era descartado, então uma invocação FALHA com stdout
  vazio lia-se como «sem alterações». Nos dois casos, bytes não-revisados
  dirigiam o `--write`. **REAL.**
- **[P2-a] Tipo do valor de anotação** — `:644-650`. Só os NOMES dos campos eram
  checados. `{"statusMessage": {"x": 1}}` validava e era emitido direto na
  entrada de hook: instalação nova e todo build de plugin receberiam
  configuração inválida com o `--check` verde. **REAL.**
- **[P2-b] Campos do bucket errado** — `:340-342`. O vocabulário compartilhado
  deixava uma exclusão DECIDIDA carregar `oq`/`note` e uma PENDENTE carregar
  `reason`/`evidence` — registros de auditoria que se contradizem, com derivação
  verde. **REAL.**

## Curas

**P1** — a pergunta passa a ser sobre os **bytes**: o working-tree é comparado
com `git show HEAD:<rel>`. Nenhuma flag de índice falsifica isso. Toda chamada
de git é checada, e falha é **recusa** (proveniência inverificável não é
proveniência).

**Controle que mostra a mentira, medido:** sob `skip-worktree` com o arquivo
editado, `git status --porcelain` sai **vazio** — e a comparação de bytes recusa
assim mesmo (`refusing --write with a MODIFIED spec`).

**P2-a** — todo valor de campo de anotação tem de ser string; `_comment`
também.

**P2-b** — `_EXCLUSION_FIELDS_DECIDED` e `_EXCLUSION_FIELDS_PENDING`,
escolhidos pelo bucket que está sendo validado. As duas formas se justificam
diferente por desenho: a decidida com `reason` + `evidence` que RESOLVE, a
pendente nomeando a questão aberta, com a razão vivendo uma vez em
`pending_note`.

## Verificação

- 3 guards novos + o teste de não-vacuidade passou a perguntar **por bucket**
  (um teste que soma os dois conjuntos não veria a troca).
- **Controle vermelho** com o gerador pré-r5: **6 vermelhos**, artefato
  byte-idêntico antes e depois.
- Dois guards da rodada 4 precisaram de **reconciliação de fragmento**, não de
  relaxamento: a mensagem passou de «unknown field(s)» para «do not belong to
  it», que é mais precisa — um campo do outro bucket não é desconhecido, é
  deslocado.
- Bateria **258 → 261**.

## Disposição

Sombra CURADA e congelada. Rodada 6 sobre ela.
