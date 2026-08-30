# Pacote F — rail codex rodada 6 (shadow-F curada da r5, 2026-08-30 ~15:45 -03)

Rail-Verdict: CHANGES-REQUESTED (0 P1, 3 P2 — os três reais, os três curados)

Comando: `codex exec review --uncommitted --skip-git-repo-check -c sandbox_mode="workspace-write"`,
via `rail_round.sh`. Modelo `gpt-5.6-sol`, esforço xhigh. Saída bruta:
`<scratchpad efd20343>/rail/r6.txt`. Wrapper: **TREE INTACT**.

**Primeira rodada sem P1.**

## Achados

- **[P2-a] Sobreviventes antes de recusar um blocker** —
  `gen-settings-user-template.py:857`. `blocking_inclusions` recusava a entrada
  quando QUALQUER exclusão qualificada carregava aquele basename. Se o hook é
  registrado sob dois eventos e só um é excluído, o outro **ainda alcança o
  adopter e ainda pode bloquear** — a rota tem de ser documentável. Mesma
  leitura larga demais que a rodada 4 achou no oráculo de install. **REAL.**
- **[P2-b] O plugin registra o guard sem empacotar o CLI** —
  `scripts/build-plugin.py:270-271`. O plugin passou a registrar
  `check_scratchpad_access.py` (vem do template, a única fonte desde o
  FU-F-ACCEL) mas **não empacota `.claude/scripts/scratchpad.py`**. O guard casa
  por SUFIXO `scratchpad.py`, em qualquer caminho: um adopter só-plugin rodando
  o **próprio** script com esse nome e `--plan X` pode levar bloqueio de um
  guard que protege um CLI que o plugin nunca entregou. **REAL, e de produto.**
- **[P2-c] UTF-8 inválido não respeita o contrato de exit** — `:233-237`.
  `read_text()` levanta `UnicodeDecodeError` ANTES do handler de JSON, e ele não
  é `OSError`: o CLI emitia traceback e exit genérico em vez do `RC_INFRA == 2`
  que documenta. **REAL.**

## Curas

**P2-b — entregar o CLI, não remover o hook.** `copy_guarded_clis()` copia
`scratchpad.py` para `<plugin>/scripts/`; a resolução própria dele
(`Path(__file__).parent.parent / "hooks"`) passa a apontar para o
`<plugin>/hooks` que o `copy_hooks` já popula. Se o CLI sumir da árvore, o build
**aborta** em vez de emitir um plugin incoerente. Não é lista paralela — é o
oposto: o hook e o sujeito que ele guarda deixam de ser separáveis.

**E o guard invertido pegou a própria cura — o que melhorou o guard.**
`GUARDED_CLIS` é uma tabela module-level que nomeia `check_scratchpad_access.py`,
e o `PluginHooksHaveNoParallelSource` recusava qualquer tabela assim. Mas nomear
um hook não é o defeito; **RE-REGISTRAR** um é. O guard passou a exigir as duas
coisas: nomear um hook do template **E** carregar a FORMA de uma registração
(`matcher`/`hooks`/`type`/`command`).

Verificado nos dois sentidos: passa com `GUARDED_CLIS`, e **continua vermelho
com o ACCEL replantado** (3 de 8). Um guard que não distingue empurra o próximo
autor a renomear até passar — pior que um guard estreito.

**P2-a** — pergunta por sobreviventes (`regs` menos as exclusões), não por
"algum par excluído carrega o nome".

**P2-c** — `UnicodeDecodeError` nomeado ao lado de `OSError` no `load_json`.
Um código de saída que só vale para as entradas em que alguém pensou não é
contrato.

## Verificação

- 5 testes novos: 2 para sobreviventes (parcialmente excluído ⇒ pode declarar
  rota; totalmente excluído ⇒ não pode) e `UnreadableInputIsInfrastructure` (3:
  UTF-8 inválido, JSON inválido, entrada ausente — todos rc 2).
- Controle do plugin: `build-plugin.py` roda e o `dist/ceo-plugin/scripts/`
  passa a conter `scratchpad.py`.
- Controle do rc: UTF-8 inválido saía **rc 1 com traceback**, agora sai
  **rc 2 com `INFRA:`** nomeando o arquivo.
- Bateria **261 → 266**; `gen --check`, ratchet e `check-claude-md-claims` rc 0.
- Um fragmento de mensagem da r2 precisou reconciliação («EXCLUDED» → «ALL»),
  porque a recusa ficou mais precisa: não é "está excluído", é "TODAS as
  registrações estão".

## Disposição

Sombra CURADA. Rodada 7 sobre ela.
