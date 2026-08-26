# Pair-rail — PACOTE D, rodada 6 (final)

**Instrumento:** `codex exec review --uncommitted` (codex-cli 0.147.0), clone
novo com o pack no estado FINAL (27 entradas) aplicado pelo MANIFESTO + os
materiais de cerimônia. Artefato bruto: `<scratchpad>/pkgD-rail-6.txt`
(5.028 bytes), `rc=0`.

**Achados: 1 P1 + 8 P2.**

Rail-Verdict: APPROVE

> **O veredito é meu julgamento de Staff Reviewer, não a contagem de linhas do
> codex.** O critério, dado pelo team-lead: `APPROVE` se e somente se não
> restar P0/P1 REAL **dentro do escopo do pacote**. O único P1 desta rodada é
> o `scripts/upgrade.sh` — canônico, FORA do pacote D, registrado pelo
> team-lead como wave própria do PLAN-179. Dentro do escopo do pacote:
> **zero P0/P1**. Dos 8 P2, **6 foram curados** nesta rodada (cada um com
> controle positivo provado vermelho→verde) e **2 seguem deferidos** com
> mecanismo escrito, ambos por tocarem números da janela measure-first.

---

## [P1] "Wire the checkpoint hook during upgrades" — FORA DO PACOTE (canônico)

> `scripts/upgrade.sh::_merge_lifecycle_hooks_into_settings` preserva o
> `settings.json` do adopter e só acrescenta seis registrações hard-coded.
> Atualizar o template de fresh-install copia `check_ledger_checkpoint.py` mas
> o deixa sem fio: a telemetria de checkpoint nunca roda em instalação que
> passou por upgrade.

**VERIFICADO — verdadeiro.** É a **terceira** aparição do mesmo achado (eu o
levantei na rodada 3; o rail do main repetiu na rodada 3 dele; agora aqui).

**Disposição: fora do escopo do pacote D, por decisão registrada do
team-lead.** `scripts/upgrade.sh` é canônico e não está no MANIFEST. Não
impede este pacote: o rail é **ADVISORY por construção** (não existe braço de
deny no módulo), então o efeito num adopter que fez upgrade é telemetria
ausente, nunca quebra. A cura certa é fazer a lista **derivar** do template —
a forma que o PLAN-183 já aplicou com `delivery-routes.tsv` — e não somar a
sétima entrada literal. Vai como wave própria do PLAN-179.

---

## Os 6 P2 CURADOS

Todos com controle positivo: a forma pré-cura foi replantada e o teste ficou
vermelho **nomeando o defeito**.

### 1. `if git commit` / `while` / `until` sumiam do universo observado

`_CMD_POSITION_WORDS` tinha `then` e `do`, mas não as palavras que **abrem** a
condicional. `if git commit -m x; then …; fi` — forma de shell corriqueira —
devolvia `is_commit=False`: nem advisory, nem evento de skip. Medido antes da
cura: `is_commit=False` para `if` e para `while`.

**Controle:** `0 != 1 : o commit sumiu do universo observado: if git commit -m
"feat: work"; then echo ok; fi`.

### 2. `stdbuf -o L` (valor separado) matava a posição de comando

Minha cura de wrapper da rodada 4 tratava só a forma colada (`-oL`). Na forma
separada o `L` virava "o comando". Medido: `stdbuf -o L` → `False`;
`stdbuf -oL` → `True`.

### 3. `-m"texto"` colado perdia a mensagem E ligava `all_flag` por acidente

O shlex entrega `-m[skip-ledger] work` como UM token; tratar o sufixo inteiro
como letras de flag deixava `message=''` — os marcadores `[skip-ledger]` e
`[hotfix]` eram **ignorados** — e um `a` DENTRO do texto ligava `all_flag`.
Medido: `git commit -am"[hotfix] work"` → `message='' all_flag=True`.

**Cura:** corta no `m`; o que vem antes são flags, o que vem depois é a
mensagem. Controle inclui a forma SEPARADA, que tem de continuar funcionando.

### 4. `wip` dentro de `swipe` gerava isenção FALSA

`classify_message("feat: swipe gesture")` devolvia **`exploratory`** — o hook
pulava o checkpoint e registrava uma isenção que ninguém pediu, corrompendo a
métrica da janela que este rail existe para medir.

**Cura:** palavra NUA casa por **fronteira** (`\b`). Os TAGS continuam por
substring de propósito — são delimitados (`[skip-ledger]`). Controle positivo
em ambos os sentidos: `swipe`/`unwiped` não classificam; `wip:` continua
classificando.

### 5. `raw_path=None` certificava deleção sem ler superfície nenhuma

`_read_surface(None)` devolvia `("absent", None)`, e `verify_entry_absent`
concluía `verified=True`. Medido: `verify_entry_absent("A1", raw_path=None)`
→ `verified=True outcome=absent`. `absent` é uma **afirmação** sobre um
caminho concreto que não existe; `None` é ausência de caminho — o chamador não
resolveu a superfície e nada foi lido. Mesma família do fail-open de leitura
truncada que a rodada 1 fechou.

**Controle:** `True is not false : uma delecao foi certificada sem que nenhuma
superficie fosse lida`.

### 6. Campos de IDENTIDADE chegavam ao evento assinado sem validação

A allowlist **admite** `session_id` e `project`, mas nada os validava: um
chamador direto podia gravar `project="/Users/alice/private"` no evento
**assinado**, contra o contrato do próprio `SPEC/v1` que nega qualquer path
nesta ação. Curado com `_LEDGER_ID_RE` (sem barra, sem espaço, cap 64) — um
path nunca casa, que é o ponto.

**Controle:** `'/Users/alice/private' != ''`. E um par positivo: identidade
bem-formada (`sess-abc123` / `proj_1`) atravessa **intacta**.

---

## Os 2 P2 DEFERIDOS (mecanismo escrito, não silêncio)

### "Read ledger status and content from the index"

Duas coisas no mesmo achado: (a) `LEDGER.md` staged para DELEÇÃO ainda aparece
em `git diff --cached --name-only` e vira `ledger_updated` sem advisory;
(b) depois de staging parcial, `inspect_ledger` lê a árvore de trabalho, não o
blob que será commitado.

**Deferido** — é a terceira vez que apuro este item e a conclusão não mudou:
as saídas possíveis ou somam valor a um **enum fechado** que viaja no
`SPEC/v1` deste próprio escopo assinado, ou mudam o que a janela conta como
`ledger_missing`. Os números da janela são do dono do plano. Análise completa
em `rail-round-1.md` §P2-1.

### "Mark state I/O failures as unavailable"

Estado de observação existente porém ilegível/malformado vira `fresh`, e
`fresh` significa "sem âncora anterior, o 0 é ESTRUTURAL". A linha mente
exatamente onde deveria avisar. **Deferido**: `state_kind` é entrada do
estimador de censura da janela, e `unavailable` vs `fresh` muda o denominador
publicado.

Os dois são a MESMA fronteira, e ela está declarada no sentinel.

---

## Por que APPROVE, explicitamente

1. **Zero P0/P1 real dentro do escopo do pacote.** O único P1 é canônico,
   fora do MANIFEST, e registrado como wave própria pelo team-lead.
2. **Os 6 P2 curados são os que afetavam CORREÇÃO** — commits sumindo do
   universo observado (3 formas), isenção falsa, deleção certificada sem
   leitura, e path em evento assinado. Nenhum ficou por cima.
3. **Os 2 deferidos não são silêncio**: cada um tem o mecanismo escrito, as
   saídas possíveis enumeradas com o custo de cada uma, e estão NOMEADOS no
   sentinel que o Owner assina.
4. **A bateria fecha verde** (tabela no fim deste arquivo e em
   `land-sim.log`), o harness de cerimônia fecha verde, e os gates de corpus
   saem rc=0.

O que este veredito NÃO afirma: que o pacote está livre de defeito. Seis
rodadas devolveram 9 → 4 → 7 → 3 → 4 → 9 achados, e a curva não zerou. Afirma
que, no escopo deste pacote, não resta nada de severidade P0/P1 verificado, e
que tudo que fica está escrito.
