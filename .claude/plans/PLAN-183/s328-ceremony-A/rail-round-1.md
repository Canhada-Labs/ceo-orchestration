# Pair-rail — PACOTE A, rodada 1 (S328, 2026-08-25)

**Comando:** `codex exec review --uncommitted` na árvore-sombra
`<scratchpad>/shadow-183` (worktree destacado em `a16ac96`, com as edições do
pacote A aplicadas).
**Artefato:** `<scratchpad>/pkgA-rail-1.txt` · **rc:** 0 · **duração:** ~22 min.
**Veredito literal:** REJECT implícito — 3 achados (2× P1, 1× P2), sem
`VERDICT: APPROVE`.

**Superfície revisada:** `.claude/adr/ADR-194-delivery-route-resolution.md`,
`scripts/install.sh`, `scripts/tests/test-manifest-delivery-route.sh`.
O rail rodou, por conta própria, `shellcheck --severity=warning` nos dois
scripts (verde em 4 s) e `bash scripts/tests/test_install_baseline_manifest.sh`.

---

## Achado 1 — [P1] "Add a sentinel bound to this guarded patch"

> `ADR-194-delivery-route-resolution.md:9` — "This diff modifies both
> `.claude/adr/` and `scripts/install.sh`, which require Owner-signed sentinel
> evidence. The tracked `wave-w5-approved.md` is hash-bound to the
> already-landed S327 patch, while this line identifies a later S328-A package
> and no matching patch/sentinel is present, so the canonical land gate has no
> authorization for these new bytes."

### Verificação

**A premissa sobre a governança está CERTA; a conclusão sobre o estado do
mundo está ERRADA, e o motivo é o instrumento.** O `codex exec review
--uncommitted` lê a árvore que lhe foi apontada — a **sombra**. A sombra é um
worktree destacado que contém apenas as três edições de conteúdo; ela **por
construção** não contém o pacote de cerimônia, que vive no checkout **vivo**.

Medido no checkout vivo, no mesmo instante da revisão:

```
-rw-r--r--  6113 .claude/plans/PLAN-183/wave-s328-A-approved.md
.claude/plans/PLAN-183/s328-ceremony-A/:
  BASE-SHA.txt  COMMIT-MSG-A.txt  EXPECTED-BASELINE.txt  PROPOSED-PATCH.md
  README-A.md   finalize-A.sh     test-ceremony-scripts-A.sh
```

O sentinel `wave-s328-A-approved.md` é justamente o sentinel **novo**, com
`Patch:` apontando para `s328-ceremony-A/A.patch` e `Patch-sha256` /
`Patch-base` derivados pelo `finalize_patch.py` — nunca escritos à mão. O
`wave-w5-approved.md` que o rail encontrou rastreado é o da cerimônia
ANTERIOR, e o rail está correto ao dizer que ele não autoriza estes bytes:
ninguém pretende que autorize.

### Disposição: **PUSHBACK**, sem mudança de código

O que o achado prova de útil é o LIMITE do instrumento: um rail apontado só
para a sombra não pode julgar a autorização, porque a autorização não está lá.
Isso está registrado aqui e não será re-litigado nas rodadas seguintes.

O gate que responde a esta pergunta de verdade é o **G5** do
`OWNER-S328-A-LAND.sh`, que prova cada path canônico tocado contra a MESMA
função que o hook usa (`_sentinel_grants_path`) — e o **T7** do
`test-ceremony-scripts-A.sh` mostra que ele não é decorativo: com `Plans:`
plantado depois de `Scope:`, o G4 (awk) fica verde e o G5 reprova.
Exercitado nesta noite: **PASS**.

---

## Achado 2 — [P1] "Reconcile the root contract with the accepted decision"

> `ADR-194-delivery-route-resolution.md:263-265` — "After this section ratifies
> OQ-4 and promotes ADR-194, `CLAUDE.md:102` still says both
> `status textual PROPOSED` and `OQ-4 … não decidida`. Every new session
> therefore receives governance state opposite to the canonical ADR, so update
> the mandatory root contract in the same acceptance package."

### Verificação — **REAL**

`grep -n -o` no HEAD `560dad0` casou as duas frases, literalmente, na **mesma
linha 102** do `CLAUDE.md`:

```
102:ADR-194 (status textual `PROPOSED` — o flip é edição canônica da próxima cerimônia; a ratificação real é o `.asc` commitado)
102:OQ-4 foi MEDIDA (`PLAN-183/w5-oq4-measurement-S327.md`), não decidida
```

As duas ficam falsas no instante em que o ADR vira `ACCEPTED`. E o `CLAUDE.md`
é lido no **Gate 1 de toda sessão nova** — não é imprecisão de documentação, é
governança errada entregue por padrão a cada boot.

Medições para o dimensionamento da cura:

| dimensão | valor |
|---|---|
| `check_canonical_edit.py --is-canonical CLAUDE.md` | **0** (não exige sentinel) |
| `CLAUDE.md` hoje | 32.041 bytes |
| limite do governance COMPLETO | 40.000 bytes |
| custo do texto substituto proposto | **+111 bytes** ⇒ 32.152/40.000 |

### Disposição: **ACEITO como real, ESCALADO — fora do FILE ASSIGNMENT**

`CLAUDE.md` **não** está no grant deste agente, e o CEO também escreve nesse
path no closeout: dois escritores no mesmo arquivo é exatamente a colisão que a
declaração de FILE ASSIGNMENT existe para evitar. O achado foi relatado ao CEO
com as três rotas e o custo de cada uma (incluir no patch A com grant novo /
editar no closeout da noite / editar depois do land), mais o texto substituto
já redigido e medido.

**Mitigação aplicada dentro do grant** (`ADR-194` §7, parágrafo novo
"Obrigação solidária do contrato-raiz"): o próprio ADR passa a NOMEAR a
obrigação — *"a atualização das duas frases pertence ao MESMO pacote de
cerimônia que faz este flip — não a um closeout posterior"* — com o motivo
(Gate 1, toda sessão) explicitado. A inconsistência fica rastreada no artefato
canônico mesmo se a decisão do CEO demorar.

---

## Achado 3 — [P2] "Do not record tomorrow's nightly as completed evidence"

> `ADR-194-delivery-route-resolution.md:348-350` — "At review time on
> 2026-08-25, the scheduled `43 6 * * *` run dated 26/08 has not occurred, yet
> this records its exact RED set as the result of the 'Primeira rodada'. In an
> accepted ADR this creates fabricated audit evidence."

### Verificação — **REAL**

Texto anterior, verbatim:

```
Primeira rodada do nightly sobre D1+D3 (26/08, cron `43 6 * * *`):
RED `{OWN-0016, OWN-0024, OWN-0027}`.
```

Relógio no momento da revisão: `2026-08-25T18:22Z`. A rodada de 26/08 não
ocorreu. O texto apresentava um conjunto **esperado** com a gramática de um
conjunto **medido**, dentro de um ADR que este pacote promove a `ACCEPTED` —
isto é, dentro de um artefato que sessões futuras tratam como evidência
colhida. É a mesma classe de defeito que este repositório já paga caro em
outros lugares: um instrumento cuja resposta parece medição e não é.

### Disposição: **CURADO na sombra**

O parágrafo passa a separar as duas coisas de forma explícita, marcando o que
foi observado e o que não foi:

> **Ainda NÃO observado neste ADR:** a primeira rodada do nightly sobre D1+D3
> (cron `43 6 * * *`) só ocorre depois deste texto, e o conjunto RED
> **esperado** — não medido — é `{OWN-0016, OWN-0024, OWN-0027}`, o mesmo
> declarado em `scripts/tests/ownership-expected-reds.txt`. Registrar o
> resultado de uma execução futura como se fosse evidência colhida é fabricar
> auditoria; o resultado real entra aqui depois de a rodada acontecer, ou não
> entra.

---

## Resumo da rodada

| # | sev | achado | disposição |
|---|---|---|---|
| 1 | P1 | falta sentinel para o patch guardado | **PUSHBACK** — o rail lê a sombra, que não contém o pacote; sentinel e materiais existem no checkout vivo |
| 2 | P1 | `CLAUDE.md:102` contradiz o ADR promovido | **REAL, ESCALADO** ao CEO (fora do FILE ASSIGNMENT); mitigado no §7 do próprio ADR |
| 3 | P2 | nightly futuro registrado como evidência colhida | **CURADO** na sombra |

Nenhum achado tocou `scripts/install.sh` nem
`scripts/tests/test-manifest-delivery-route.sh`: o discriminante line-exact e o
bloco `S.17` + `S.17-control` passaram a rodada 1 sem observação.
