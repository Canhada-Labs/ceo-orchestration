---
plan: PLAN-183
round: 1
created_at: 2026-08-20
synthesis: anonimizada (DEBATE-SCHEMA 13.2) — Critic-A/B/C
---

# PLAN-183 — Debate L3, round 1 — Consensus

> Sintetizado de três críticas anonimizadas (Critic-A / B / C). Toda âncora
> citada abaixo foi CONFERIDA no disco por mim nesta sessão; onde a crítica
> errou, está marcado.

---

## 1. Consensus findings

Achados levantados por 2+ críticos, agrupados por MECANISMO. Pela regra do
protocolo, cada um destes **obriga** ajuste no plano.

### C1 — A cura da W1 não alcança quem já instalou, e está na camada errada  `[A, B, C]`
Três mecanismos distintos, um mesmo desfecho: o adopter que reportou o bug
fica com o caminho absoluto **para sempre**.
- **A (R1, MF-5):** `install.sh:663-668` persiste `PH_PROTOCOL_SOURCE="$SOURCE_DIR"` (absoluto) no install-state; a precedência **#1** do upgrade relê exatamente essa chave → o próximo upgrade re-renderiza absoluto. E os dois caminhos continuam byte-idênticos *pelo mesmo gerador*, então **INV-4 passa verde** — o mesmo formato de falso-verde que o plano diagnostica em §2.
- **B (R1, MF-2):** mudar o corpo renderizado muda `_REFRESH_PROTOCOL_CANON_HASH` (`upgrade.sh:1667,1686-1690`) → o ponteiro antigo deixa de casar → `_lc="edited"` → `PRESERVE_OWNED` → `upgrade.sh:1730` imprime *"PRESERVED … pointer NOT refreshed"*.
- **C (Unseen 3):** a precedência **#2** é "um ponteiro **saudável** on-disk — *never silently rename a sound pointer*". Um ponteiro absoluto **é** saudável por essa definição.

**Conferido:** `upgrade.sh:1598-1610` traz a precedência 1/2/3 em comentário
literal, incluindo a frase acima. `install.sh:409` (`PH_PROTOCOL_SOURCE="${CEO_PROTOCOL_SOURCE:-}"`),
`:522` (`--protocol-source`), `:663-668` (fallback `$SOURCE_DIR`) — todas batem.

**Onde a cura mora** (A MF-5, corroborado por B MF-2): **dentro** de
`_render_protocol_pointer`, não no call-site. Conferido: a função já recebe
`$2=TARGET` (`_framework_manifest_set.sh:673-674`) e o ramo `"$_rpp_target"/*`
já emite relativo. Relativizando ali, install e upgrade relativizam pelo MESMO
gerador e o absoluto persistido fica inofensivo. O teste vira
`install → upgrade → assert relativo`, não `install → assert relativo`.

### C2 — A premissa de §1/AC-5 ("nunca exercitado como adopter") é FALSA  `[B, C; A em forma mais fraca]`
- **B (MF-1)** e **C (MF-3)** afirmam, e eu confirmei: `scripts/tests/smoke-install.sh` + `.github/workflows/smoke-install.yml` existem e rodam **por-PR**, com install real em scratch dir e paridade install/upgrade; `smoke-install.yml:276` tem literalmente **"Protocol pointer render control (generator parity)"**.
- **Conferência decisiva que eu rodei:** `grep -rln "validate.yml.template\|benchmarks.yml.template"` sobre `scripts/tests/`, `.github/workflows/` e `.claude/scripts/tests/` devolve **ZERO**.
- **A (U2)** chega ao mesmo lugar por outra porta: `install.sh:1108` carrega `# WS4-dispatcher-fn: E6-F5 fix — copy .claude/dispatcher/ (validate-governance.sh REQUIRES it)`, ou seja, já houve cura de gap de adopter aqui.

**Causa-raiz verdadeira, mais estreita e mais útil:** o instrumento de adopter
existe e é forte, mas (i) seu **escopo exclui `.github/`** — os dois templates
de workflow são os únicos artefatos entregues sem teste e sem referência de CI
em lugar nenhum — e (ii) ele para em *"o install escreveu os bytes certos?"* e
**nunca ativa nem executa** o CI entregue.

### C3 — `check_contamination.py` é ele próprio o vetor de contaminação  `[A, B, C — três críticos]`
Conferido linha a linha:
- `_PATTERN` (`:70-73`) = `acme\s*[Ll]edger|example[\s._\-]*owner|Example\s+Owner|[Jj]oao[\s._\-]*[Cc]anhada|Jo[aã]o` — o **nome real do mantenedor**, incluindo o token nu `Jo[aã]o`.
- O arquivo é **entregue a todo adopter** (`install_scripts_selective`, glob top-level `*.py`; só `tests/`/`legacy/` excluídos).
- `_ALLOWLIST_EXACT:100` inclui `.claude/scripts/check_contamination.py` — **o guard isenta a si mesmo**.
- `_ALLOWLIST_EXACT:97` isenta `.github/workflows/validate.yml`, mas o arquivo do adopter chama-se `validate.yml.template` — **a isenção nem viaja**.

Efeito líquido no adopter: o scanner defende a identidade **do mantenedor**,
não a do adopter. O bullet da W2 ("o `Contamination check` estava CERTO") está
correto quanto ao gatilho do A1 e **passa ao largo disto**.

### C4 — O template de CI não tem vínculo com o vivo  `[A (R2, U1), B (R2, MF-6)]`
**Conferido:** vivo `.github/workflows/validate.yml` = **71 steps / 79.993 bytes**,
`runs-on: Ceo`, `timeout-minutes: 25`, checkout SHA-pinado.
Template = **14 steps / 226 linhas**, `ubuntu-latest`, `timeout-minutes: 5`,
`actions/checkout@v4` sem pin. Nada regenera um do outro, nada diffa os dois.
Este repo grada drift em quase tudo (SPEC drift guard, Policy drift guard,
plugin manifest idempotency, install-profiles manifest gate) — o template de CI
é a **única superfície de governança sem gate de drift**. Curar 3 steps devolve
a classe na próxima edição do vivo.

### C5 — O censo do W2 é observação de campo tratada como censo, e há contradição interna VIVA  `[A (MF-1), B (MF-5)]`
- **A:** o patch r5 corrigiu a wave e deixou o cabeçalho velho. **Conferido no arquivo atual:** a tabela (`:34`) ainda diz "4 de 14 … `:70,143,154,183`" e a prosa (`:63-68`) ainda atribui a falha do `Contamination check` a "allowlist cita arquivos do framework" — enquanto a W2 (`:179-192`) diz **TRÊS** e diz que mexer na allowlist **ESCONDERIA** a contaminação. Duas afirmações opostas no mesmo documento.
- **B:** pelo menos mais quatro steps têm modo de falha condicional a adopter. **Conferido no template:** `:108-109` `python3 -c 'import yaml'` (PyYAML é terceiro — contradiz o `CLAUDE.md` §3 "stdlib-only"); `:148,158` `unittest discover`; `:176-177` actionlint baixado por `curl | bash` de `main` **sem pin** e rodando sobre `"$GITHUB_WORKSPACE/.github/workflows/"*.yml` — ou seja, gradando os workflows **do próprio adopter**; `:77` placeholder lint cujo texto de remediação manda editar `.github/workflows/validate.yml`, arquivo que o adopter **não tem**.

### C6 — A regra "VETO nunca em name-only" mora no GERADOR; a OQ-3 omite o produtor  `[A (MF-6), B (MF-7)]`
**Conferido:** `.claude/scripts/skill-budget-generator.py:352-362` demove toda
skill `tier == "domain"` abaixo de `min_dispatches`; o **único** eixo de
proteção é `if skill["tier"] != "domain": continue  # NEVER demote core/frontend`.
`grep -c "veto\|VETO\|risk_class"` no arquivo inteiro = **0**. A OQ-3 oferece
`install.sh` / hook / lint de skills e **não lista o gerador**, que é quem
escreve `overrides[key] = "name-only"`. Corolário de ambos: AC-3 ("impossível
por construção") só é satisfeita com conjunto de exclusão + asserção **nos
testes do gerador** — não corrigindo entradas no `settings.json`.

### C7 — W0-US1 deixa de ser busca aberta e vira hipótese NOMEADA, aritmeticamente testável  `[A (MF-3), C (MF-1)]`
Os dois derivam a mesma hipótese do artefato entregue, por lados opostos.
**Conferido em `templates/settings/settings.base.json`:** 46 registros de
timeout — **38 deles `"timeout": 5"`**; os únicos tetos longos são **210**
(`check_pair_rail.py`, matcher `Edit|Write|MultiEdit`) e **130**
(`codex_review_user_code.py`). `CEO_PAIR_RAIL_TIMEOUT_S` default **180**
(`check_pair_rail.py:1722`).
- **A:** logo o relatório de campo no caminho `PreToolUse:Bash` (35×, pior caso 175 s / 231 s) é **aritmeticamente impossível** como estouro de teto por-hook ⇒ o `/doctor` não está contando breach de teto por-hook. Conclusão disponível **hoje**, sem arqueologia.
- **C:** e 175 s ≈ 180 menos startup, 231 s > 210 = harness matando, em `PreToolUse:Write` 25× — **é assinatura, não fonte desconhecida**. Mais: o `_comment` do próprio template afirma *"adopters without Codex pay only the no-op"* — exatamente a afirmação que o campo contradiz, **no artefato entregue**.

### C8 — A claim secundária de §4 é falsa como escrita  `[A (MF-2), C (MF-2)]` — e contradiz o próprio §4
Plano `:127-132`: *"o audit-log NÃO registra … o único campo de duração
relevante é `policy_evaluated.duration_ms`, max 5 ms … cego às próprias paredes
falharem **por qualquer via que seja dele**"*.
**Conferido, e é falso:** `hook_duration_ms` está no schema
(`AUDIT-LOG-SCHEMA.md:73,77`), é **emitido** (`.claude/hooks/audit_log.py:559,656,1569`)
e é **consumido** (`.claude/scripts/audit-query.py:373-398`; `hook_duration_ms_p95`
em `_lib/metrics.py:87,162,201`). `_lib/audit_emit.py:1128` já carrega a forma
`check_name` + `timeout_ms`. E `canonical_edit_hook_fault` aparece **8×** em
`check_canonical_edit.py` — o que o **próprio §4** (`:105-107`) já cita, 20
linhas acima da frase "cego por qualquer via".

**Reformulação correta (A):** o gap não é cegueira, é **censura à direita** —
quando o harness mata o processo de fora, o hook nunca chega à linha de emissão,
então a amostra de `hook_duration_ms` é censurada **exatamente na cauda de
interesse**. W0-US2 deixa de ser "decidir se emite evento próprio" e passa a
**medir a TAXA DE CENSURA** (invocações esperadas × linhas emitidas) e a
**estender a forma que já existe**.

### C9 — `external_wait: "nenhum"` contradiz AC-2 [P0] (e AC-6)  `[A (R4), C (MF-9); B (U5) para AC-6]`
Frontmatter `:11` diz "não é bloqueio"; AC-2 `:214` exige "provado em PR real"
num repo que não controlamos, e a W2-P1 `:196` reforça "não localmente". Um AC
**P0 travado em SLA de terceiro é um plano que não fecha**. Mesma classe: AC-6
("achados respondidos ao adopter") é round-trip externo por definição, sem canal
nem dono nomeado.

### C10 — `depends_on: []` sub-declara o grafo; W3 colide com o PLAN-175  `[A (MF-9, R3), C (MF-8, R5)]`
**Conferido:** `PLAN-SCHEMA.md:202` — `depends_on` **MUST include parent**
quando gateia execução. A W1 declara não poder regredir 167/168 (`:170-173`) e
a W3 declara coordenação com o 175 (`:199`), com `depends_on: []` no
frontmatter. E o 175 remodela **o que** é instalado (core 42→~25, 116 domain →
packs opt-in): a regra "VETO nunca em name-only" pode nascer contra a forma
antiga, e há merge conflict garantido na seleção de skills em tempo de install.

---

## 2. Single-agent insights KEPT

| # | Achado | Crítico | Por que sobrevive sozinho |
|---|--------|---------|---------------------------|
| K1 | **O CI entregue é INERTE até o adopter renomear.** `install.sh:1516-1522` chama `install_docs_template … ".github/workflows/validate.yml.template"` — o GitHub Actions só lê `.yml`/`.yaml`. | B (U1) | **Conferido no disco.** Fato mecânico, não opinião. Consequências em três direções: baixa a severidade de A2/A3, **exige que AC-2 nomeie um passo de ativação que o plano nunca menciona**, e força a decisão "CI opt-in por rename é design ou acidente?" — mais barata que os quatro patches. |
| K2 | **O fail-soft do gerador demove TODA skill de domínio.** `skill-budget-generator.py:255-261`: log de auditoria ausente ⇒ contagens zeradas ⇒ *"every domain-tier skill will look rare"* ⇒ demoção em massa. Um adopter novo **não tem histórico por construção**. | A (U4) | **Conferido.** Consequência lógica inescapável: AC-3 **não pode** ser satisfeita corrigindo as duas entradas de hoje. E inverte a doutrina do `CLAUDE.md` §4 — aqui uma falha de infraestrutura tem consequência de **segurança** (silenciar os vetos de conta de dinheiro), não de disponibilidade. |
| K3 | **A4(ii) não é "no campo": é defeito vivo AQUI, agora.** | A (MF-7) | **Conferido:** `.claude/settings.json:872-873` tem `financial-correctness-and-math` e `financial-display` em `name-only` **neste repositório**. E são **104** entradas `name-only` tanto no `settings.base.json` quanto no vivo. §2 (`:83-86`) escreve "(no campo: …)", subdimensionando. *(Nota: o campo reportou 105 órfãs; o embarcado são 104 — a W3 deve reconciliar, não presumir.)* |
| K4 | **A1 é também divulgação de informação de host, não só portabilidade.** O ramo `*` grava o `$SOURCE_DIR` da máquina de quem instalou — tipicamente `/Users/<nome>/…` — num arquivo **versionado do repo de terceiro, possivelmente público**. | C (MF-5) | É o elo lógico que torna coerente o bullet "o `Contamination check` estava CERTO", e converte AC-1 de "é relativo" para **"nenhum caminho de home/usuário no ponteiro entregue"** — asserção falsificável em vez de descritiva. Colide com a regra "No contamination" do `CLAUDE.md` §4. |
| K5 | **`install.sh:1508` não escapa o handle.** `sed "s/{{OWNER_HANDLE}}/$GITHUB_OWNER/g"`, com `--github-owner` aceito sem validação (`:479`). | C (MF-7) | **Conferido**, e com contraste interno: o caminho do PROTOCOL_SOURCE **escapa** (`sed 's/[|&\\]/\\&/g'` dentro de `_render_protocol_pointer`) e ainda rejeita newline. Um handle com `/` ou `&` corrompe o CODEOWNERS; **CODEOWNERS malformado é ignorado SILENCIOSAMENTE pelo GitHub — o gate de revisão do adopter some sem aviso.** Uma linha de allowlist `^[A-Za-z0-9-]{1,39}$` fecha. |
| K6 | **O template não tem kill-switch; o vivo tem 16.** | B (U2) | **Conferido exatamente:** `grep -c CEO_SOTA_DISABLE` = **16** no vivo, **0** no template. É o mecanismo já estabelecido nesta casa, e é a diferença entre "o adopter desliga nosso CI num clique de repo-variable" e "o adopter edita YAML que é nosso". Também abre uma terceira opção para a OQ-1. |
| K7 | **Onde o evento de timeout morre.** `_lib/spool_writer.py` é spool durável por-PID com **drain-on-next-invoke** (conferido no docstring `:2`). Os 7 timeouts de `Stop` do relatório são justamente os que podem não ter um "próximo invoke". | C (Unseen) | Pré-condição falsificável e barata para a W0-US2: se o drain não varre spools de PIDs mortos, o instrumento perde **exatamente a cauda que existe para medir**. Casa com C8 (censura à direita). |
| K8 | **A rejeição de A6 responde a outra pergunta.** | A (MF-10) | Verificável: com `--github-owner` ausente o install escreve `.github/CODEOWNERS.template` com o token **literal** (`install.sh:1512-1514`) — em nenhum ramo sai `@Canhada-Labs`. A razão dada é verdadeira e **não alcança a observação do campo**. AC-6 promete responder o recusado "com a razão"; esta razão não fecha. |
| K9 | **Nomear os artefatos que a W1 toca e re-orçar.** `ownership_table.tsv` se declara "THIS FILE IS THE TRUTH"; o gate falha em **qualquer** diferença, inclusive encolhimento; ~25 min por rodada e2e. | B (MF-8) | Barato, verificável, e evita a armadilha conhecida deste repo: um ciclo de re-baseline de 25 min por iteração não cabe num orçamento de 30-60k que não o declara. Pareado com A (R5): o orçamento da W4 ("10-30k" para conteúdo declarado inespecificável) é decorativo. |
| K10 | `benchmarks.yml.template` ganhar cabeçalho dizendo que consome `ANTHROPIC_API_KEY` e **gasta dinheiro do adopter**. | B (nice) | Item de adopter-fitness por definição, custo de uma linha, e a W2 já vai abrir esse arquivo por causa do A3. |

---

## 3. Single-agent insights REJECTED / DEFERRED

**REJ-1 — "Trocar `CEO_ORCHESTRATION_DIR` por `CEO_PROTOCOL_SOURCE`" (B MF-4, C MF-4): REJEITADO — já está no plano.**
As linhas `155-163` do arquivo atual **já** contêm o bullet `[P0]` "Usar a
interface que JÁ EXISTE — não inventar env nova", com as âncoras corretas e a
autópsia do erro ("copiado do PLAN-001 do adopter"). Ambos os críticos citam
`:140` — linha que hoje é `"possíveis, todas aceitáveis: confirma / refuta /
fonte"`. **Fato relevante de processo:** as âncoras de corpo de B e C estão
deslocadas em ~20-38 linhas do arquivo atual, enquanto as de frontmatter batem
— indício forte de que **B e C criticaram um snapshot pré-r5**. Sobra apenas
higiene de redação (o bullet ainda *menciona* o nome morto), não mudança.

**REJ-2 — "§W2 diz 'mudar de allowlist'" (C R3): a CITAÇÃO é rejeitada, o MECANISMO é mantido.**
A W2 atual (`:184-192`) diz o **oposto** do que C cita: "Mexer na allowlist
ESCONDERIA a contaminação". Mesma causa que REJ-1. O núcleo substantivo de C
(o padrão caça a identidade errada) sobrevive **como consenso C3**, não como
item isolado.

**DEF-1 — "W0-US2 auto-inflige o timeout que mede" (C R1): DIFERIDO para restrição de desenho da W4.**
`_lib/filelock.py:120` tem `timeout: float = 2.5` — conferido — e o budget dos
hooks de parede é 5. Mas o argumento é contra **uma implementação possível**
(bracket com duas aquisições de lock), não contra a existência da US; e o
`spool_writer` existe precisamente para não pegar lock no caminho quente.
**Vira restrição escrita da W4:** *"nenhuma instrumentação de timeout pode
adicionar aquisição de lock no caminho quente"* — com controle positivo. Não
altera a W0-US2.

**DEF-2 — ADR-081 / `architecture-decisions/SKILL.md:325-326` ainda em "1-4 weeks" (A, nice-to-have): DIFERIDO ao PLAN-180.**
Razão substantiva: o PLAN-180 é o plano que **possui** a doutrina de unidade de
tempo (validador advisory + `eta_calendar`). Trazer para cá viola a disciplina
de escopo de §3, que é a única razão de este plano ter chance de pousar em 2-4
sessões.

**DEF-3 — `check-contamination.sh:18` resolve raiz por `dirname $0/../..` (C, nice-to-have): DIFERIDO, com gatilho.**
É a classe que já mordeu este repo (a lição registrada manda usar
`git rev-parse --show-toplevel`), mas é robustez interna do guard, ortogonal ao
eixo adopter. **Gatilho:** se a W2 abrir esse arquivo para tornar o `_PATTERN`
configurável (C3), corrige junto — senão fica fora.

**DEF-4 — `install.sh:1011-1015` afirma "89 unit tests" / "74 unit tests" (C, nice-to-have): DIFERIDO.**
Obsoleto contra ~770 arquivos de teste, e o adopter lê esse comentário. Mas
drift de **comentário** é classe conhecida e não-vigiada por `verify-counts` —
pertence ao instrumento de contagens, não a este plano. Fold-in oportunista se
a W2 já editar `install.sh`.

---

## 4. Plan adjustments

Índice para o CEO editar. Uma linha por ajuste.

| # | Seção-alvo | O que muda |
|---|-----------|------------|
| 1 | **§1 (parágrafo "A classe única") + AC-5** | Substituir "dogfoodado, nunca exercitado como adopter" pela versão verificável: *o instrumento de adopter existe, roda por-PR (`smoke-install.sh` + `smoke-install.yml`) e é forte — mas seu escopo exclui `.github/` (zero referências aos dois templates em qualquer teste ou workflow) e ele nunca ATIVA nem EXECUTA o CI entregue.* (C2) |
| 2 | **§2, tabela linha 34 + prosa 63-68** | Eliminar o resíduo pré-r5: some "4 de 14", some `:70` como âncora de defeito, some "allowlist cita arquivos do framework". Critério verificável: nenhuma ocorrência sobrevive no documento. (C5 / A MF-1) |
| 3 | **§2, A4(ii)** | Trocar "(no campo: …)" por "defeito vivo TAMBÉM neste repositório": `.claude/settings.json:872-873`; e registrar 104 embarcadas vs 105 reportadas, a reconciliar na W3. (K3) |
| 4 | **§4, parágrafo "Consequência secundária"** | Corrigir a claim falsa: `hook_duration_ms` existe, é emitido e é consumido; `audit_emit.py:1128` já tem `check_name`+`timeout_ms`. O gap real é **censura à direita** — harness kill nunca chega à linha de emissão. (C8) |
| 5 | **W0-US1** | De busca aberta para **hipótese nomeada a refutar**, com o teste aritmético grátis PRIMEIRO (38/46 tetos em 5 s ⇒ Bash não pode produzir 175/231 s; 210/180 é a assinatura do caminho Write). A arqueologia da fonte do `/doctor` só abre se a aritmética não explicar. (C7) |
| 6 | **W0-US2** | De "decidir se emite evento próprio" para **"medir a taxa de censura (invocações esperadas × linhas emitidas) e estender a forma existente"**; adicionar a pré-condição do spool (drain varre PID morto?). (C8 + K7) |
| 7 | **W0-US3** | Promover a `[P0]` **e** reescrever como *estender* `smoke-install.sh`/`smoke-install.yml` (o step `:276` já existe) — nunca bateria paralela. Pré-condição de land da W2. (C2 + §6.3) |
| 8 | **W1 — novo bullet `[P0]`** | Relativização decidida **dentro** de `_render_protocol_pointer` (já recebe `$2=TARGET`), não no call-site; teste = `install → upgrade → assert relativo`. (C1) |
| 9 | **W1 — novo bullet `[P0]` + AC próprio** | **Remediação retroativa:** reconhecedor de "absoluto legado" no molde de `_protocol_pointer_is_degraded` (`_framework_manifest_set.sh:736-742`), com re-render byte-a-byte e falha **para preservação**; backup em `$BAK_DIR`. AC: *"install feito com a versão anterior, ao rodar `upgrade.sh`, sai com ponteiro relativo — provado em e2e."* (C1) |
| 10 | **W1 — bullet `[P1]` de preservação** | Preservação silenciosa vira **preservação AVISADA**: WARNING quando um ponteiro preservado contém caminho absoluto. A preservação é requisito **e** modo de falha. (B MF-3) |
| 11 | **W1 — orçamento + artefatos** | Nomear quais dos cinco artefatos de ownership a wave espera tocar e orçar o ciclo de re-baseline (~25 min/iteração) em tokens+sessões. (K9) |
| 12 | **W1 — higiene** | Remover a menção residual a `CEO_ORCHESTRATION_DIR` do corpo do bullet (mantendo a autópsia, que é valiosa). (REJ-1) |
| 13 | **AC-1** | Reforçar de "é relativo" para "**nenhum caminho de home/usuário no ponteiro entregue**", asserção explícita. (K4) |
| 14 | **W2 — novo bullet `[P0]`** | **Vínculo template↔vivo**: gate de drift (steps do template ⊆ steps do vivo, com allowlist explícita de divergência) **ou** declaração escrita de "subconjunto mínimo congelado" com o teste que a executa. Sem isto a W2 é patch num arquivo sem dono. (C4) |
| 15 | **W2 — re-derivar o censo** | Step a step no template, com mecanismo nomeado por step; incluir no mínimo `:108-109` (PyYAML vs stdlib-only), `:148,158` (`unittest discover`), `:176-177` (actionlint sem pin, via `curl\|bash` de `main`, gradando os workflows do adopter), `:77` (remediação aponta arquivo inexistente), `:22-23` (timeout 5 vs 25 do vivo), `:27` (checkout sem SHA-pin). (C5) |
| 16 | **W2 — segunda metade do bullet do `Contamination check`** | Manter "ele estava CERTO" **e** acrescentar: o `_PATTERN` embarca a identidade do mantenedor, o arquivo é entregue ao adopter, e ele **se auto-isenta** (`_ALLOWLIST_EXACT:100`); a isenção de `validate.yml` nem viaja para `validate.yml.template`. Cura = padrão **configurável na instalação**, não editar lista de caminhos. (C3) |
| 17 | **W2 — kill-switch** | Template recebe `if: vars.CEO_SOTA_DISABLE != '1'` em nível de job, espelhando o vivo (16× vs 0×). (K6) |
| 18 | **W2 / OQ-1 — resposta** | Fechar: `unittest discover` **não** é preservável atrás de guarda (conftest é pytest-only ⇒ falso-vermelho). Opções honestas: remover, ou reescrever para a invocação real do CI. Somar o kill-switch de job. (§6.4) |
| 19 | **W2 — passo de ativação + AC-2** | Nomear que o install entrega `.template` (inerte) e que o CI só existe após rename; AC-2 passa a nomear o passo de ativação e a aceitar prova em repo descartável **nosso**. (K1) |
| 20 | **W2 — nice-to-have fold-in** | Cabeçalho no `benchmarks.yml.template` declarando `ANTHROPIC_API_KEY` e custo em dinheiro do adopter; alinhar checkout ao SHA-pin do vivo. (K10) |
| 21 | **W3 / OQ-3 — resposta** | Fechar a OQ: a demoção é escrita por `skill-budget-generator.py:352-362`, cujo único eixo é `tier` e que tem **zero** ocorrências de `veto/VETO/risk_class`. Invariante = conjunto de exclusão **no gerador** + asserção nos testes dele. (C6) |
| 22 | **W3 — novo bullet `[P0]`** | Corrigir a **direção do fail-soft**: log de auditoria ausente ⇒ hoje demove tudo; um adopter novo não tem histórico por construção. Falha de infra não pode ter consequência de segurança. (K2) |
| 23 | **W3 — origem do resíduo** | O mapa de overrides é **pré-cozido e embarcado** (104 entradas no `settings.base.json`, calculadas contra o inventário de 166 do framework) — as órfãs não vêm de acúmulo no adopter. "Podar depois de copiar" contradiz a doutrina 167/168 (um gerador, uma verdade): ou o template não embarca o mapa, ou o install regenera a partir do inventário instalado. (A MF-6) |
| 24 | **AC-3** | Passa a ter teste **no gerador**, não no `settings.json`. (C6 + K2) |
| 25 | **Frontmatter `external_wait` + AC-2 + AC-6** | **Decisão do CEO, nomeada no plano:** ou AC-2 aceita prova em repo descartável próprio (e `external_wait` continua "nenhum"), ou `external_wait` vira real e AC-2 cai para `[P1]`. AC-6 ganha canal + dono, ou sai das ACs e vira item de closeout. (C9) |
| 26 | **AC-6** | A razão de recusa do A6 é verdadeira mas não alcança a observação do campo — nomear o mecanismo (`install.sh:1512-1514` deixa o token literal) ou declarar "não explicado; pedimos o arquivo ao adopter". (K8) |
| 27 | **Frontmatter `depends_on` + nova seção `## Coupling`** | Declarar: W1 ↔ 167/168 (INV-4 + bateria de ownership), W3 ↔ PLAN-175 (colisão na seleção de skills em tempo de install). `PLAN-SCHEMA.md:202` exige. (C10) |
| 28 | **W4** | Manter gateada pela W0, mas: (a) orçamento deixa de ser "10-30k" fixo e ganha piso nomeado quando a W0 fechar; (b) restrição escrita — nenhuma instrumentação pode adicionar lock no caminho quente; (c) determinar serial-vs-paralelo e per-hook-vs-per-event **antes** de desenhar qualquer cura. (A R5, DEF-1, §6.5) |

**O que NÃO muda** (protegido pelos três críticos em §7, por unanimidade):
A5 declarado NÃO REPRODUZIDO com o nome do que falta; W4 gateada pela W0; a
distinção *harness kill* (fail-open) × *deadline interno do ADR-186*
(fail-closed, audita); §3 (os não-objetivos, sem re-litigar 175/182); a regra
"o teste ENTRA na bateria existente, não numa paralela"; a coluna "Verificado?"
com âncora de disco; orçamento em tokens+sessões, sem semanas.

---

## 5. Round verdict

**PROCEED**

Os 10 consensos e os 10 insights mantidos são **incorporáveis sem redesenhar o
plano**: a decomposição em waves sobrevive intacta, a fronteira de escopo de §3
sobrevive, e cada ajuste é bullet adicionado, AC re-escopada, open-question
respondida ou parágrafo corrigido. O ajuste que mais se aproxima de mudança de
forma — a reescrita da causa-raiz (§1/AC-5) — **estreita** a tese em vez de
reestruturá-la, e o efeito prático é promover a W0-US3 a `[P0]` e ancorá-la em
`smoke-install.yml:276`, que é onde o próprio plano já queria estar.

Não há decisão exclusiva do Owner: o único ponto de escolha (AC-2 × `external_wait`)
é escopo de plano, decidível pelo CEO. Não há desacordo irreconciliável entre
críticos — as três discordâncias reais estão resolvidas em §6 por leitura
determinada do disco, não por preferência.

**Ressalva de processo para o round 2, se houver:** dois dos três críticos
evidentemente leram um snapshot **pré-r5** (âncoras de corpo deslocadas ~20-38
linhas; ambos atacam `CEO_ORCHESTRATION_DIR` e o bullet da allowlist como se a
correção r5 não tivesse landado). Isso não invalida nada — **todos os
mecanismos substantivos deles foram conferidos por mim no disco e batem** — mas
um round 2 tem de receber o arquivo pós-ajuste, e a cobertura de §4/W1/W2 por
esses dois deve ser considerada parcial até lá.

---

## 6. Contradições entre críticos

**6.1 — §4: o framework é ou não é "cego às próprias paredes"?**
A e C dizem que a claim é **falsa** e trazem âncoras corretas (`hook_duration_ms`
emitido e consumido; `audit_emit.py:1128` já tem `check_name`+`timeout_ms`).
B, em §7, **endossa** a claim e diz que ela *"vale sozinha"*, pedindo para
manter a W0-US2 mesmo que o número 71 se refute.
**Conferi: A e C estão certos sobre o campo; B está certo sobre a conclusão.**
As duas metades convivem — o **título** é defensável (não existe evento quando
o harness mata o processo de fora), mas o **mecanismo** não é cegueira: é
**censura à direita** de um campo que já existe. → **Decidiria:** adotar a
reformulação de A (medir a taxa de censura, estender a forma existente) e
preservar a insistência de B de que a W0-US2 sobrevive à refutação do 71.

**6.2 — O `Contamination check` no adopter fica VERMELHO ou VERDE-VACUOSO?**
B (R3) diz vermelho — adopter brasileiro com um "João" em CHANGELOG/AUTHORS.
A (U3) e C (R3) dizem verde e inerte — o padrão não procura nada que diga
respeito ao adopter. O plano diz que **ficou vermelho no campo**.
**Não são exclusivos: é o mesmo guard com entradas diferentes.** Vermelho quando
a árvore do adopter contém os tokens — inclusive o que **nós** injetamos via A1
— e vacuamente verde quando não contém, defendendo a identidade do mantenedor
em vez da do adopter. → **Decidiria:** nomear **os dois modos** no plano; a
cura (padrão configurável na instalação + parar de embarcar a identidade do
mantenedor) fecha ambos, enquanto mexer na allowlist não fecha nenhum.

**6.3 — W0-US3: instrumento que falta, ou segundo oráculo que reabre a classe 167/168?**
A (MF-4) quer promover a `[P0]` e torná-la pré-condição de land da W2.
B (R5) alerta que um "repo descartável" cria um **segundo oráculo** ao lado de
`smoke-install.sh` + `test-ownership-table.sh`, reabrindo exatamente a classe
que dois planos fecharam.
**Não é oposição, é ordem de operações.** → **Decidiria:** promover a
CAPACIDADE a `[P0]` (A) e implementá-la como **extensão** de
`smoke-install.sh`/`smoke-install.yml` (B, C) — o step `:276` já existe. Vale
registrar que os três críticos, independentemente, protegem em §7 a regra
"entra na bateria existente"; a única violação dela no plano é a redação atual
da própria W0-US3.

**6.4 — OQ-1: os dois steps de teste saem ou ganham guarda?**
A (MF-8) demonstra que a guarda preserva um caminho **já quebrado**:
`unittest discover` é falso-vermelho porque o conftest é pytest-only, e o vivo
instala pytest+PyYAML explicitamente. B (U2) oferece um terceiro caminho: o
kill-switch de job que o vivo já usa 16×.
→ **Decidiria:** as opções vivas são **remover** ou **reescrever para a
invocação real do CI**, mais o kill-switch de job por cima. A única opção
morta é a que a OQ-1 hoje trata como default — "guarda condicional preservando
`unittest discover`".

**6.5 — Qual wave está com orçamento errado?**
A (R5) aponta a W4 ("10-30k" para conteúdo declaradamente inespecificável).
B (MF-8) aponta a W1 (30-60k sem folga para re-baseline de ownership a 25 min
por iteração). **Apontam o mesmo defeito em waves diferentes**, não se
contradizem. → **Decidiria:** re-orçar as duas; a W4 mantém "conforme W0" mas
com piso nomeado no fechamento da W0.
