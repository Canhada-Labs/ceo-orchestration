# PLAN-179 W1-b — Constraint Pinning: o conjunto fixado

> **Esta página é DOCUMENTAÇÃO DERIVADA. A fonte de verdade é o código.**
>
> ```
> .claude/hooks/_lib/pinned_constraints.py  →  PINNED_CONSTRAINTS
> ```
>
> A doc segue o código, nunca o contrário. Se esta página e a constante
> divergirem, **a página está errada** e o teste de igualdade de conjuntos
> (abaixo) falha por desenho.

---

## 1. Porque a fonte é código e não este ficheiro

Emenda **r1-C5** do debate round-1. A versão anterior de US5b guardava o
conjunto num `.md` e afirmava, na mesma página, que o conjunto **não era
derivado de disco** — uma autocontradição. A emenda resolveu-a na única
direcção que torna a afirmação verdadeira por construção:

1. **"Não derivado de disco"** — `pinned_constraints.py` não faz I/O de
   ficheiro nenhum, nem no import nem na chamada. Não existe janela em que um
   documento compactado, editado ou substituído mude o que o modelo é
   informado que as regras são. A propriedade é asseverada por um teste que
   **varre o próprio source** à procura de I/O.
2. **"Imune a Compaction-Eviction"** — a constante vive em código
   re-executado a cada invocação do hook, **fora** do transcript que o
   sumarizador reescreve. O vector adversarial nomeado em §2.2 do plano
   (conteúdo hostil já em contexto a enviesar o sumarizador para excluir
   políticas legítimas) não tem superfície para actuar sobre um literal de
   código.

Consequência operacional: **mudar o conjunto é uma edição canónica** de
`.claude/hooks/_lib/`, sujeita à cerimónia de sentinel assinado pelo Owner
(ADR-031). Essa fricção é o ponto, não um efeito colateral.

---

## 2. Critério de corte (OQ-2)

> **Só entram invariantes cuja violação seja IRREVERSÍVEL.**

Duas leituras, ambas obrigatórias:

- **Irreversível, não apenas importante.** Uma regra que pode ser desfeita no
  turno seguinte não precisa de sobreviver a uma compactação — o custo de a
  reaprender é um turno. Uma regra cuja violação produz um commit empurrado,
  uma tag publicada, um gate desarmado ou um veto atropelado não tem turno
  seguinte que a repare.
- **Pequeno por obrigação, não por gosto.** Cada entrada custa contexto em
  **todas as compactações de todas as sessões**. Um conjunto grande
  re-cria exactamente o problema de piso de contexto (`F`) que o plano existe
  para atacar (§2.1) — e que W0 mediu em **97–99k**, já o dobro do estimado.
  Um "pinning" de 30 regras seria uma segunda `CLAUDE.md` a pagar-se
  eternamente.

**Dimensão:** de **4 a 6** entradas. Hoje são **4**. O tecto de 6 é
deliberadamente baixo; chegar a ele é sinal de que o critério de corte está a
ser aplicado com folga, não de que há espaço.

**Teste de admissão de uma candidata** — as três respostas têm de ser sim:

1. A violação é irreversível sem intervenção do Owner?
2. A regra é **auto-contida** — compreensível sem ler nenhum ficheiro? (Uma
   regra que precisa de contexto é um ponteiro disfarçado, e ponteiros já
   existem: são a doutrina pointers-only do ADR-153 §Decision-2.)
3. Se esta regra for a única a sobreviver a uma compactação, o dano evitado
   justifica o custo em todas as compactações que nunca teriam violado nada?

---

## 3. O conjunto (derivado — não editar à mão)

O bloco entre os marcadores é gerado a partir de `PINNED_CONSTRAINTS` e é
**byte-exacto**. Uma entrada por linha, sem quebra de linha interna, pela
ordem da tupla.

<!-- PINNED-CONSTRAINTS-BEGIN v1 source=.claude/hooks/_lib/pinned_constraints.py symbol=PINNED_CONSTRAINTS -->
```text
PROTOCOL.md vetoes (ADR-052) are absolute. A fired veto is not a risk to accept, re-scope, or argue past — it stops the work until the Owner rules on it.
Canonical-sentinel discipline (ADR-031): no edit to a canonical governance path without a matching Owner-signed sentinel. Never disable, weaken or route around the guard to land an edit.
Never commit, push, tag or publish without explicit Owner authorization for that specific action.
Fail-CLOSED on input inside a security matcher; fail-OPEN only on infrastructure error. Never invert the two to make a gate go green.
```
<!-- PINNED-CONSTRAINTS-END -->

**Contrato de parsing** (para o teste de W1-b US5b):

- delimitadores: os dois comentários HTML acima, literais;
- corpo: o bloco ```` ```text ```` imediatamente a seguir ao marcador BEGIN;
- uma entrada por linha não-vazia, `strip()` aplicado;
- asserção: `set(entradas_do_md) == set(PINNED_CONSTRAINTS)` **e**
  `len(entradas_do_md) == constraint_count()`.

A igualdade é de **conjuntos**, mas o teste compara também o **comprimento**:
sem isso, uma entrada duplicada no `.md` passaria despercebida.

Integridade do conjunto no momento desta escrita — recomputável com
`hashlib.sha256(json.dumps(sorted(PINNED_CONSTRAINTS)).encode()).hexdigest()`:

```
7f93b0277e047183da040d5cde4077214dc3e76f4ca2c72cff24261d228bc2c5
```

Este sha256 é uma conveniência de revisão (permite ver num diff que o conjunto
mudou), **não** é o gate. O gate é a igualdade de conjuntos contra o código.

---

## 4. Porque estas quatro, e não outras

| # | Invariante | O que se perde ao violar |
|---|---|---|
| 1 | Vetos do PROTOCOL.md (ADR-052) | Um veto atropelado é trabalho executado fora de governança; a decisão do Owner que ele existia para forçar já não pode ser feita a montante. |
| 2 | Disciplina de sentinel canónico (ADR-031) | Uma edição canónica sem sentinel destrói a própria propriedade de auditabilidade que o rail entrega — e o dano não é o ficheiro, é a cadeia de prova. |
| 3 | Sem commit/push/tag/publish sem autorização | Empurrar e publicar são irreversíveis para o mundo exterior. Uma tag publicada não se retira. |
| 4 | Fail-CLOSED no input, fail-OPEN na infra | Inverter os dois para pôr um gate verde desarma silenciosamente uma defesa de segurança e deixa-a verde — a pior classe deste repo: instrumento verde com pergunta envelhecida. |

Todas as quatro passam o teste de admissão de §2. Notavelmente **fora** do
conjunto, apesar de importantes: as regras de estilo Python (reversíveis num
turno), a disciplina de nomes de plano (reversível), a doutrina de spawn
(reversível, e já coberta por um gate mecânico), e a própria doutrina
pointers-only (é uma regra sobre o hook, não sobre o modelo).

---

## 5. Fronteiras honestas

- **A mitigação é medida noutro setup.** Os números de §2.2 do plano
  (0 % → 30 %/59 %; 0 % quando a restrição sobrevive vs 38 % quando é omitida)
  vêm de arXiv 2606.22528, não deste framework. W1-b importa o **mecanismo**;
  a evidência local é o controlo adversarial de US5d.
- **US5d é uma propriedade ARQUITECTURAL, não uma afirmação sobre o modelo**
  (emenda r1-C7). O que se testa é que o payload fixado **nunca participa do
  bloco enviado ao sumarizador** — verificável no código. Que o modelo obedeça
  às regras restauradas é o que o paper mede, não o que este repo assevera.
- **O canal ainda não está provado.** Se a sonda W0-1 der negativo em
  `PostCompact`, o bloco nasce em `SessionStart(matcher=compact)` (emenda
  r1-C3), onde este repo tem precedente positivo local
  (`turbo_sessionstart.py`). O **conteúdo** desta página não muda com a
  escolha do canal; a superfície de entrega muda.
- **Decisão adiada e registada (r1-C8/8.8):** se o pinning fica ou não atrás
  do kill-switch `CEO_COMPACTION_CONTINUITY=0`. Se ficar acoplado, o desarme
  emite evento. A decisão é de W1-b e ainda não foi tomada.
- **Orçamento separado, por desenho.** O bloco fixado não conta para o tecto
  de ≤9 ponteiros do ADR-153 §Decision-2, precisamente para que o cap de
  ponteiros nunca possa despejar uma regra de governança.
