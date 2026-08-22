---
plan: PLAN-184
round: 2
rounds_synthesized: [round-1, round-2]
agents_considered: [devops, security-engineer, qa-architect]
findings_received: 29
findings_sent: 29
ingest_complete: true
decisions_revised_in_plan:
  - "§1 — a base de custo passa a citar o endpoint de billing que existe, e o número que ela publicava fica REFUTADO"
  - "§2 — a manchete de 77,7% cai; o teto real da A1 é derivado, não projetado"
  - "§3 — a gramática da entrada da denylist vira restrição [P0], não convenção"
  - "§4 — .claude/plans/** e .claude/skills/** entram como contraexemplos ao lado de docs/**"
  - "W0 — ganha o resultado que MATA o plano (pré-registro), e a unidade vira PUSH"
  - "W1 — abre com cerimônia canônica; ganha guard de fork e teste do próprio filtro"
  - "W2 — reclassificada: os timeouts medidos NÃO estouram; AC-5 vira critério ASSINADO"
  - "W3 — o instrumento de billing não atribui por workflow NEM por repositório; AC-6 reescrito"
synthesized_at: 2026-08-22
synthesized_by: CEO
verdict: ESCALATE-TO-OWNER
plan_status_after: draft (o flip é do Owner, e agora depende de UMA decisão de prioridade)
---

# PLAN-184 — síntese do debate, round 2

> **Integridade do ingest, declarada primeiro porque foi o defeito do
> round 1.** Esta síntese cobre **29 de 29 achados**, de três críticos,
> lidos ÍNTEGROS. O round 1 cobriu 16 de 23 e disse isso. A síntese
> automática deste round também recebeu payload truncado (11 de 29) e
> **recusou-se a emitir veredito**, marcando `RUN-ANOTHER-ROUND` — o
> instrumento funcionou. Esta é a síntese do CEO sobre o payload
> completo, e toda claim abaixo foi reverificada contra o disco ou
> contra a API antes de entrar aqui. Onde a crítica errou, o pushback
> está registrado com o comando que o sustenta.

## Veredito: ESCALATE-TO-OWNER

Não porque o plano esteja errado — a **doutrina** dele sobrevive inteira
à crítica, e os três críticos disseram isso independentemente. É porque
dois achados convergentes mudam a **decisão de prioridade**, e essa
decisão não é minha:

1. **A base de custo que autoriza o plano não reproduz, e a projeção é
   aritmeticamente impossível.** A §2 projeta um corte de US$ 10,67/dia
   sobre um workflow cujo gasto total medido é US$ 8,91/dia. Um corte
   não pode ser maior que a base.
2. **Existe uma alternativa com retorno da mesma ordem e risco
   estritamente menor, e ela nunca foi enumerada.** Reduzir a matriz de
   4 versões de Python para as 2 de fronteira no `push` (mantendo 4 no
   PR e no nightly) rende ~US$ 3,15/dia contra os ~US$ 4,04/dia de teto
   da A1 — sem filtro de path, sem classe nova de falso-verde, sem
   workflow novo, sem superfície derivada, sem cerimônia canônica.

Se a A0 entrar primeiro, o prêmio residual da A1 encolhe e a pergunta
"vale gastar uma cerimônia canônica num workflow novo?" muda de resposta.
**Essa é a escalação: a ordem A0-vs-A1 é do Owner.** O resto do plano
está curado no texto e fica executável em qualquer das duas ordens.

---

## Achados de consenso (2+ críticos)

### C1 [P0] — A base de custo da §1 não reproduz, e a projeção da §2 excede o gasto que ela corta
**Críticos:** `Critic-B` (F-02), `Critic-C` (QA-01, QA-02, QA-03).

`Critic-C` mediu US$ 193,38 na janela contra os US$ 314,40 do plano, e
mostrou que a projeção combinada (US$ 10,67/dia) é maior que o gasto
total medido do `validate.yml` no runner pago (US$ 8,91/dia).
`Critic-B`, por caminho independente (simulação do filtro sobre os 167
head-SHAs reais), achou 85/167 pushes puláveis, não 106, e ~48 min
pesados por run, não os 80,4 que a §2 usa como média.

**Verificação do CEO — confirma a direção, e acha algo que nenhum dos
três viu.** Rodei o endpoint de billing vivo
(`gh api /organizations/Canhada-Labs/settings/billing/usage`):

| linha (agosto) | qty | gross |
|---|---|---|
| `Actions Linux 8-core` | **9.254,909 min** | **US$ 203,61** |
| `Actions Linux` | 4.025 min | US$ 24,15 |

O plano declara **14.291 min / US$ 314,40**. O billing — que é a
autoridade — diz **9.254,9 min**. O plano superestima em ~54%.

**E o achado novo:** os minutos de 8-core são faturados sob
`repositoryName: ceo-orchestration-**private**`, não sob o repositório
público que o plano quer otimizar. Não é um detalhe de rótulo: medi o
volume dos dois repos em agosto — **privado: 73 runs; público: 400+, dos
quais 167 só de `validate.yml`**. O privado não pode gerar 9.255 min
sozinho, logo o billing está atribuindo ao repo errado o custo que o
volume diz vir do público.

**Consequência dura:** o AC-6 ("confirmar a projeção contra billing
real") é **inexequível como escrito**, porque o único instrumento que
existe não atribui por workflow *nem por repositório*.

**Pushback registrado.** `Critic-C` afirma ter "reconciliado dia a dia
contra a fatura, batendo em 20 dos 21 dias". Esse endpoint devolve **9
itens agregados por MÊS** (`date` = primeiro dia do mês) — não existe
granularidade diária nele. A ordem de grandeza do crítico está certa e é
o que importa; a alegação de reconciliação diária **não reproduz** pelo
caminho que ele cita, e fica marcada como não-verificada.

**Cura:** a §1 ganha coluna FONTE e um comando por linha (o padrão que a
§5 já pratica); os números atuais ficam **REFUTADOS**, não "não-derivados";
a W0 passa a ter de resolver a atribuição de repositório antes de
qualquer projeção. **Aterrissa em:** §1, §2, W0-US4, W0-US5, AC-6.

### C2 [P0] — A unidade é o PUSH, não o commit — e isso quebra a derivação e os controles
**Críticos:** `Critic-B` (F-02 fator 1), `Critic-C` (QA-06).

O gatilho é `push` em `main` (167/167), e `paths-ignore` avalia a UNIÃO
dos arquivos de TODOS os commits do push. A §1 inteira classifica
COMMITS, e o AC-2b especifica "um ÚNICO commit". Medido pelos dois, de
forma convergente: **20-21 dos 167 pushes carregam mais de um commit**,
um deles com 21.

**Cura:** trocar "commit" por "push" na §1 e nos ACs; **AC-2c novo** — um
único PUSH com dois commits (um só-docs, um tocando `.claude/hooks/**`)
tem de executar os 4 pesados. **Aterrissa em:** §1, W0-US1, AC-2b, AC-2c.

### C3 [P0] — O exemplar da própria denylist não é inerte
**Críticos:** `Critic-A` (SEC-P0-1, SEC-P1-5, SEC-P2-7), com o mecanismo
que `Critic-C` ratifica ao manter a prova de EXISTÊNCIA da W0-US2(b).

`.claude/plans/**` — o prefixo que o AC-2 usa como "o commit que DEVE
pular" — contém três schemas normativos (`PLAN-SCHEMA.md`,
`AUDIT-LOG-SCHEMA.md`, `DEBATE-SCHEMA.md`) cuja ENTREGA é asserida por
`tests/integration/test_install_smoke.py:66-74`, que roda no job pesado
`integration-tests`. Um commit que renomeie ou apague um deles toca só
`.claude/plans/**`, pula os pesados, e o install para de entregar o
schema ao adopter **sem nada ficar vermelho**. Mesma porta em
`.claude/adr/README.md` (:70) e `.claude/skills/core` (:66).

**Cura:** recortar a entrada em vez de descartá-la
(`.claude/plans/PLAN-*.md` + `.claude/plans/PLAN-*/**/*.md`, com os
`*SCHEMA*.md` fora); e a prova (b) da W0-US2 deixa de ser "aplicar as
três operações AO prefixo" e passa a ser "derivar os arquivos sob o
prefixo que aparecem LITERALMENTE em qualquer suíte pesada, e aplicar as
três a cada um". **Aterrissa em:** §3, §4, W0-US2, AC-4.

### C4 [P1] — Falta o backstop, e o custo de MANTER o filtro é tratado como zero
**Críticos:** `Critic-B` (F-05, F-06), com apoio de `Critic-A` (SEC-P1-3).

O plano copia o filtro do `coverage.yml` e deixa para trás o `schedule:`
que o torna sobrevivível. Sem cron, uma entrada de denylist que envelheça
(e já existem **272 arquivos `.py`** sob `.claude/plans/`) produz
silêncio permanente: nenhum run, nenhum vermelho, nenhum aviso. E nada
re-deriva a denylist com o tempo — o próprio plano exibe a prova de que
essa classe apodrece aqui (o F11, lógica de detecção de path escrita por
nós, morta na perna `pull_request`).

**Cura:** `schedule:` nightly no workflow novo + um teste em
`.claude/scripts/tests/` (que roda no job de governança, nunca filtrado)
que lê a denylist do YAML e falha se qualquer suíte pesada referenciar um
caminho coberto por ela. **Aterrissa em:** W1, §6, AC novo.

### C5 [P1] — "Verde" no runner novo não é prova, mas o critério como escrito bloqueia MELHORA
**Críticos:** `Critic-C` (QA-08) refinando o AC-5 que `Critic-B` (F-08)
mostrou estar justificado pela razão errada.

O AC-5 exige `delta de skipped = 0 E delta de passed = 0`. O delta não é
assinado: se a imagem `ubuntu-latest` tiver um binário que o larger
runner não tem, `skipped` CAI e `passed` SOBE — cobertura MELHOR
bloqueando o flip. E `Critic-B` mediu que a premissa que sustenta o AC
("`Ceo` é self-hosted, inventário de binários desconhecido") é **falsa**:
`gh api .../actions/runners` devolve `total_count: 0`, e os jobs reportam
`runner_name: ceo-1000004236` — larger runner **hospedado**.

**Cura:** assinar o critério —
`skipped(novo) <= skipped(velho) E passed(novo) >= passed(velho)` — e
manter o AC pelo motivo certo (variação de tool-cache/pip entre imagens),
não pelo falso. **Aterrissa em:** W2, AC-5.

---

## Achados de um crítico só, MANTIDOS

1. **`Critic-B`/F-01 [P0] — a cerimônia canônica nunca é mencionada.**
   Verifiquei: `check_canonical_edit.py:184-185` guarda
   `.github/workflows/*.yml`, e `:178` guarda `.claude/adr/ADR-*.md`. O
   commit de split toca no mínimo quatro paths guardados
   (`validate.yml`, o workflow novo, ADR-021, ADR-050), e
   `grep -ci "cerim\|sentinel\|canonical\|gpg"` no plano devolve **0**.
   Um plano de execução que não vê o gate que o bloqueia não é
   executável. **A W1 abre com item [P0] de cerimônia.**
2. **`Critic-A`/SEC-P0-2 [P0] — a FORMA da entrada não tem restrição.**
   `.claude/plans/**` como prefixo cru pré-aprova, para sempre, os 272
   `.py`, 102 `.sh` e 31 `.yml` que já vivem lá — incluindo
   `PLAN-179/staged-w24/` e `OWNER-W179-LAND.sh`, que são código. Cura:
   toda entrada é `<prefixo>/**/*.md`; entrada sem âncora de extensão é
   rejeitada por construção.
3. **`Critic-C`/QA-04 [P0] — a W3 não tem instrumento.** O endpoint
   clássico responde **HTTP 410**; o que funciona não tem eixo de
   workflow. Reforçado pelo meu achado de atribuição de repositório
   (C1). Cura: o número que fecha o AC-6 passa a ser **US$ por push**
   (ou por run de `validate.yml`), derivável do mesmo dado, em vez de
   US$/dia-calendário.
4. **`Critic-C`/QA-07 [P1] — a W0 não nomeia o resultado que a mata.**
   Nenhum dos cinco Checks interrompe o plano. Cura: item [P0] de
   pré-registro — "se o teto da A1 ficar abaixo de US$ N/dia, ou a
   fração só-docs abaixo de M%, a W1 não abre", com N e M escolhidos
   pelo Owner ANTES de ver o resultado.
5. **`Critic-B`/F-07 [P1] — a alternativa A0 nunca foi enumerada.**
   É metade da razão da escalação. `hook-tests-python-matrix` consome
   ~34 min wall dos ~48 min pesados por run — **75% do custo que a A1
   ataca** — e rodar só 3.9 e 3.12 no `push` rende ~US$ 3,15/dia.
6. **`Critic-A`/SEC-P1-4 [P1] — o split nasce sem guard de fork.**
   Seis workflows irmãos condicionam jobs alcançáveis por fork
   (`head.repo.full_name == github.repository`); `validate.yml` não tem
   nenhum, e o plano manda ACENDER `pull_request` pela primeira vez na
   janela medida.
7. **`Critic-A`/SEC-P1-6 [P1] — nada amarra os validadores ao job não
   filtrado.** Hoje é verdade por coincidência de layout, e a §9 já
   aponta para o A3, que desmontaria isso. Cura: manifesto rastreado +
   teste, no molde do `gate-scripts-manifest.txt` que o repo já pratica.
8. **`Critic-B`/F-04 [P1] — a previsão de estouro de timeout está
   errada.** Medido: `Formal verification` = **15 s** (teto 10 min);
   `E2E integration` = **1 m 43 s** (teto 8 min). A W2 previa que "os
   dois estouram" com o fator 2-3×. Cura: substituir 3,4/4,7 pelas
   durações medidas e rebaixar a W2 a item barato, sem wave de medição
   própria.
9. **`Critic-C`/QA-05, QA-09, QA-10, QA-12 [P1/P2]** — a hipótese de
   erro de classificação da W0-US5 é variância entre buckets, não
   redistribuição; a tabela da §1 não fecha por 27 min e não cita
   comando; o AC-3 não tem janela definida; e a lista de Open questions
   está corrompida na numeração (1,2,3,4,3b,5) com duas entradas
   concorrentes para o mesmo resíduo.

## Achados REJEITADOS, com o comando que sustenta

1. **`Critic-C`/QA-11 — "a assinatura aritmética dos 9090,909 min é uma
   tautologia".** *Parcialmente rejeitado.* A crítica está certa de que
   `200 / 0,022` devolve necessariamente `teto/preço` e não carrega
   informação. Mas ela conclui que o número "não casa com nenhuma
   quantidade medida", e casa: o billing devolve
   `quantity: 9254.90909091` para agosto — **a fração `.909` está lá**,
   e é a assinatura do corte no teto. A linha deve ser **reescrita**,
   não removida.
2. **`Critic-C`/QA-01 — "reconciliei dia a dia, batendo em 20 de 21
   dias".** *Rejeitado como método.*
   `gh api /organizations/Canhada-Labs/settings/billing/usage` devolve
   **9 itens, agregados por mês**. Não há eixo diário. A conclusão do
   crítico sobrevive por outra via (o total mensal já refuta os
   US$ 314,40); a reconciliação diária, não.

## Ajustes a aplicar no PLAN-184

Todos os itens acima já estão escritos no corpo do plano, seção por
seção — este consensus é o índice, o plano é o texto. As edições:

- §1: coluna FONTE + comando por linha; números marcados REFUTADOS; a
  atribuição de repositório do billing declarada como problema aberto.
- §2: manchete trocada; teto real da A1 derivado; ressalva de composição
  reexpressa.
- §3: gramática da entrada da denylist como restrição [P0].
- §4: `.claude/plans/**` e `.claude/skills/**` como contraexemplos.
- W0: pré-registro do resultado que mata; unidade = push; US5 com
  instrumento novo.
- W1: cerimônia canônica [P0]; guard de fork; teste do próprio filtro;
  `schedule:` de backstop.
- W2: durações medidas; AC-5 assinado; wave rebaixada.
- W3: AC-6 reescrito em US$/push.
- **A0 nova** na §6, com o número medido ao lado.
- Open questions renumeradas 1..12; OQ-3 apagada em favor da OQ-3b;
  **OQ-11 (ordem A0-vs-A1)** e **OQ-12 (atribuição de repositório no
  billing)** são as duas que o Owner precisa responder.

## Round verdict

**ESCALATE-TO-OWNER.**

- Todo P0 tem cura óbvia e as curas estão aplicadas no plano.
- O ingest chegou completo (29/29) — a condição que faltou no round 1.
- O que impede `ADJUST_PROCEED` é a decisão de prioridade: a A0 rende da
  mesma ordem que a A1 com risco estritamente menor, e a base de custo
  que justificava a urgência da A1 caiu de US$ 314,40 para US$ 203,61
  medidos — atribuídos, ainda por cima, ao repositório errado.
- **O plano fica executável.** Se o Owner decidir "A1 primeiro assim
  mesmo", nada mais precisa ser escrito: é marcar `reviewed` e abrir a
  W0.
