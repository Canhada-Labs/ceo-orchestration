# Pacote F — o que rodar de manhã

> Três comandos. Copie e cole cada um inteiro, na ordem. Nenhum abre editor.
> Se algum editor abrir mesmo assim: aperte `Esc`, digite `:q!` e Enter — sai
> sem salvar e nada se perde.

## 🔴 LEIA PRIMEIRO — falta UMA decisão sua

O pacote está completo e verificado, **menos um item**, e por isso o `SIGN`
ainda **recusa** assinar (ele exige `Rail-Verdict: APPROVE` no último registro
de rail — o comportamento certo).

A sétima rodada do pair-rail achou o seguinte: o hook `check_scratchpad_access.py`,
que esta wave passa a ligar para o adopter, casa por **sufixo** — qualquer
caminho que termine em `scratchpad.py`. Então um adopter que rode o **próprio**
script com esse nome e `--plan X` leva bloqueio de um guard que existe para
proteger o CLI do framework, e não tem como saber por quê. Isso bate no critério
que a própria wave declara: fica de fora todo hook que bloqueia *sem deixar uma
rota praticável*.

Duas saídas. A escolha é sua porque muda um veredito que você ratificou:

- **(a) Excluir o hook do perfil user** — uma linha no spec, roster 30 → 29.
  **É a minha recomendação:** o critério da wave decide, e o «INCLUIR» veio do
  critério ANTIGO que o próprio documento substituiu.
- **(b) Estreitar o matcher** dentro do `check_scratchpad_access.py` — mais
  correto na raiz, mas acrescenta um arquivo fora do escopo desta cerimônia, e o
  hook tem testes que assumem a folga de caminho.

O detalhe completo está em `rail-round-7.md`. Depois da sua decisão: aplico,
rodo uma rodada final de rail, e aí sim os três comandos abaixo funcionam.

---

## Antes de começar

Você vai assinar uma mudança que **altera o que um adopter recebe**: o perfil
`--ceremony user` passa de 20 para 30 registrações de hook. Isso é o ponto da
wave (a OQ-E5 que você ratificou em 27/08), não um efeito colateral. Os
detalhes, com os riscos hook a hook, estão no sentinel que você vai assinar —
seção **Residual declarado**.

O que a wave conserta, em uma frase: `templates/settings/settings.user.json`
era uma cópia manual da base cujo próprio comentário afirmava remover
"exatamente 10" hooks — eram **26**, e a proveniência citada não existe em ref
git nenhum. Agora ele é **derivado** da base por subtração declarada, e um gate
no CI compara byte a byte.

## Os três comandos

```
cd /Users/joaocanhada/canhada-labs/ceo-orchestration
bash .claude/plans/PLAN-169/OWNER-S331-F-SIGN.sh
```

O SIGN mostra o que você está assinando, preenche `Anchor-SHA` / `Data` /
`Approved-By` e pede sua senha GPG. Ele **aborta** se a árvore tiver
modificação rastreada fora do pacote — isso é proteção, não erro.

```
bash .claude/plans/PLAN-169/OWNER-S331-F-LAND.sh --dry-run
```

O dry-run roda os portões (G-PRE, G0..G5), aplica o patch, roda os gates
baratos (V1, V4, V5, V6) e **restaura a árvore**. Nada é commitado. Se ele
passar, o land real vai passar.

```
bash .claude/plans/PLAN-169/OWNER-S331-F-LAND.sh
```

O land real roda tudo (mais V2, V3 e V7), commita **sem abrir editor** e faz o
push. Ao final ele imprime o commit e os últimos runs de CI.

## Se algo abortar

Todo abort é **seguro**: a árvore é restaurada e nada foi commitado. A mensagem
diz o que fazer. Os dois abortos mais prováveis:

* **"a arvore tem modificacao rastreada fora do pacote"** — algo foi editado no
  repositório depois que o pacote foi montado. Não force: chame o Claude.
* **"o HEAD ANDOU"** — alguém commitou nesse checkout. O finalize precisa rodar
  de novo. Também não force.

## O que observar depois do push

1. O **`Validate`** ganha um step novo (`User-template derivation`). Ele deve
   passar; se reprovar, o reparo está na mensagem do próprio step.
2. O próximo `upgrade.sh` de um adopter `--ceremony user` registra **10 hooks
   novos**. Esperado.
3. O plugin passa a rodar `review_loop.py` com 15 s e `turbo_sessionstart.py`
   com 5 s (eram 60 e 10). Alinhado ao que este repositório já roda.

## Fica aberto (não é para hoje)

* **FU-F-ADRGATE** — `check-adr-chain.py` e `generate-adr-index.py` não rodam em
  CI. Achado desta wave: o índice de ADRs estava congelado em 170 com 198 no
  disco, e a cadeia sai com 11 erros pré-existentes (aos quais o ADR-197 não
  acrescenta nenhum, medido). Wave própria.
* **ADR-197 entra como `PROPOSED`.** O flip para `ACCEPTED` é cerimônia própria
  — a ratificação real é a sua assinatura sobre o sentinel.

---

## Referência — o que há no pacote

| Arquivo | O que é |
|---|---|
| `F.patch` | o patch, 20 paths, derivado da árvore-sombra |
| `wave-s330-F-approved.md` | o sentinel que você assina (o `Scope:` é derivado, não escrito à mão) |
| `EXPECTED-BASELINE.txt` | a base declarada que o V-block compara — cada valor com o comando que o mediu |
| `COMMIT-MSG-F.txt` | a mensagem de commit (o LAND usa `-F`, sem editor) |
| `DESIGN-F.md` | o desenho, os achados e os follow-ups (viaja NO patch) |
| `finalize-F.sh` | deriva o patch da sombra e o baseia no HEAD — o Claude já rodou |
| `rail-round-*.md` | os registros do pair-rail |
| `test-ceremony-scripts-F.sh` | o harness que exercita SIGN e LAND sem GPG e sem push |

`OWNER-S331-F-SIGN.sh` e `OWNER-S331-F-LAND.sh` ficam em `PLAN-169/`, um nível
acima — é onde os das cerimônias anteriores estão.
