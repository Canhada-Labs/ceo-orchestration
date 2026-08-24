# NIGHT-S325 — runbook de execução autônoma (~7h)

> **Montado na S324 pelo CEO; executado pelo terminal da S325.** O Owner
> não está disponível durante a janela. Este arquivo é o CONTRATO da
> noite: se algo não está aqui, não é escopo.
>
> **Vive em `PLAN-183/` por conveniência de local, mas é CROSS-PLAN.**
> `validate_governance_fast` percorre `.claude/plans/` com `iterdir()`
> não-recursivo, então este arquivo **não** é coberto por gate nenhum — a
> disciplina aqui é de autoria, não mecânica. Não confunda "verde do
> validador" com "este runbook foi verificado".

---

## 0. TRILHOS — violar qualquer um destes é falha de governança, não atalho

### 0.1 NUNCA editar path canônico (medido pelo oráculo, não por intuição)

O oráculo é a autoridade:

```
python3 .claude/hooks/check_canonical_edit.py --is-canonical <path>
# saída: "<path>\t0|1"   — 1 = CANÔNICO = exige sentinel GPG do Owner
```

Medido na S324, para o escopo desta noite:

| path | veredito |
|---|---|
| `.claude/plans/**` | **livre** |
| `scripts/tests/**` (incl. `_parity_classify.py`, `ownership_table.tsv`) | **livre** |
| `.claude/scripts/**` (incl. `veto_skill_map.py`, `skill-budget-generator.py`, `tests/`) | **livre** |
| `scripts/doctor.sh` | **livre** |
| `docs/ownership-decision-table.md` | **livre** |
| `CLAUDE.md` | **livre** (mas ver §0.4) |
| `scripts/install.sh`, `scripts/upgrade.sh`, `scripts/_framework_manifest_set.sh` | 🔒 CANÔNICO |
| `.github/workflows/*.yml` | 🔒 CANÔNICO |
| `.claude/settings.json` | 🔒 CANÔNICO |
| `.claude/adr/*.md` | 🔒 CANÔNICO |
| `.claude/hooks/*.py`, `.claude/hooks/_lib/**` | 🔒 CANÔNICO |
| `.claude/skills/*/SKILL.md` | 🔒 CANÔNICO |

**Se um item do escopo exigir tocar um 🔒, ele PARA e vira material de
cerimônia** — nunca se contorna, nunca se "prepara staged e aplica".

### 0.2 NUNCA responder uma OQ no lugar do Owner

Três decisões estão ABERTAS e são dele. **Nenhuma linha da W5-b se
escreve antes das três**, e nenhuma delas se "assume para prosseguir":

1. **Emenda da OQ-5** — a rota (ii) não alcança adopter sem install-state
   (`upgrade.sh:798-799` resolve `CEREMONY_EFFECTIVE="user"`).
2. **A PISTA do gerador de manifesto** — condicional vs não-condicional.
   Isto **precede** a OQ-4; ratificar ~13 linhas antes disso pode ser
   trabalho morto.
3. **Re-sequenciamento do checklist da W5-b** — 5 convergências do debate.

Detalhe em `PLAN-183/debate/w5-round-1/consensus.md`.

### 0.3 NUNCA flipar plano para `done` sem os DOIS censos

Erro cometido na S324: propus fechar o PLAN-182 vendo **7/7 ACs**, e o
censo de checkboxes mostrou **dois `[P0]` abertos**. ACs não são o plano.

Antes de qualquer `→ done`:

```bash
# censo 1: ACs
python3 - <<'PY'
import re,pathlib
t=pathlib.Path("<plano>").read_text()
b=re.split(r"^##\s+",re.split(r"^##\s+Acceptance criteria",t,flags=re.M)[1],flags=re.M)[0]
print("ACs:", len(re.findall(r"^-\s*\[x\]",b,re.M)), "/", len(re.findall(r"^-\s*\[[ x]\]",b,re.M)))
PY
# censo 2: TODAS as checkboxes, com secao — e NUNCA com awk (\s nao existe em awk ERE)
grep -nE '^[[:space:]]*-[[:space:]]*\[ \]' <plano>
```

E o hook `check_plan_edit.py` exige `completed_at` **e**
`related_commits` não-vazio no frontmatter. `reviewed → done` é ILEGAL.

### 0.4 Ordem dos gates: `git add -A` → gates de corpus → `git commit`

`CLAUDE.md` §4, violado 2× na S321. Os gates de corpus perguntam sobre o
CONJUNTO de arquivos, então rodar antes da última edição é vácuo:

```bash
git add -A
bash .claude/scripts/local/verify-counts.sh                  # exit 0
python3 .claude/scripts/check-claude-md-claims.py            # exit 0
python3 .claude/scripts/validate_governance_fast.py --json   # errors: []
python3 .claude/scripts/check-test-env-hygiene.py            # exit 0
python3 .claude/scripts/check-ceremony-script.py             # blocking: 0
python3 .claude/scripts/check-staleness.py                   # advisory
git commit ...
```

E o bit executável tem de sair do **filesystem E do index** —
`git update-index --chmod=-x` sozinho não cola.

**`CLAUDE.md` é livre mas cache-stable (§0):** editar invalida o prompt
cache e re-paga ~97k medidos. Editar **uma vez**, no closeout.

### 0.5 Pair-rail antes de CADA commit, e detectar o fim pelo ARTEFATO

O stop hook exige revisão cross-model antes do commit.

```bash
codex exec review --uncommitted </dev/null    # árvore de trabalho
codex exec review --commit <sha> </dev/null   # trabalho já commitado
```

**Duas armadilhas medidas na S324, as duas me custaram uma conclusão
errada:**

- `--commit` **não emite** o marcador `^codex$` que `--uncommitted` emite.
  Não grepe por marcador assumido — leia o **fim do arquivo**
  (`tail -c 2000`) e procure `Full review comments:`. Uma rodada LIMPA não
  tem esse bloco: ela tem só o parágrafo de resumo.
- **Nunca declare um background morto por ausência de sinal.** Prova de
  morte exige `ps -eo pid,etime,command | grep <padrão> | grep -v grep`.
  `pgrep -f <padrão>` casa a **própria linha de comando do waiter** e
  mente. Para workflow: compare `grep -c '"result"' journal.jsonl` contra
  o **número de agentes**; `0 results` é o estado NORMAL de um fan-out em
  curso (os três da S324 levaram 18–21 min).

### 0.6 Workflow: agentes são READ-ONLY, e o bloco COMMON é obrigatório

`CLAUDE.md` §5: fan-out que ESCREVE fica fora do Workflow. Todo agente
recebe `## FILE ASSIGNMENT` = `NONE-READ-ONLY`, `## PROMPT DEFENSE` com
≥6 bullets e o marcador `## HARD-RULES`. Um workflow novo sem o bloco
COMMON **nasce descoberto** (ADR-191 §4). Modelo pronto: os scripts em
`…/workflows/scripts/plan183-*.js` da S324.

### 0.7 Condições de PARADA

Pare, registre e siga para o próximo item — **não insista**:

- 3 tentativas no mesmo item sem resolver ⇒ **reconsiderar arquitetura**,
  não tentar a 4ª (`PROTOCOL.md` anti-padrão 6).
- Um gate de corpus vermelho que você não causou ⇒ registre e não
  "conserte" alargando padrão.
- Qualquer coisa que exija 🔒 ou uma das 3 OQs ⇒ para o item.
- `origin/main` vermelho por causa de um commit SEU ⇒ pare tudo e deixe o
  diagnóstico escrito.

**Leia o baseline do CI antes de diagnosticar qualquer coisa (medido na
S324):**

| workflow | estado esperado | por quê |
|---|---|---|
| `Smoke Install` | **VERMELHO por desenho** | D1 não foi curado. Assinatura: `maintainer` = `STALE 3 + UNCLASSIFIED 0`; `user` = tudo zero. Última verificação real: run `32658998831` em `2578624`, que já inclui a W5-a. |
| `Validate CEO Orchestration governance` | **VERDE** | é o gate que precisa ficar verde; foi verde em `4d752e4` e `42b7812`. |

**E duas armadilhas de leitura do CI que fariam um terminal autônomo
diagnosticar errado:**

1. **`Smoke Install` NÃO roda em commit só-de-plano.** Ele tem filtros
   `paths:`, e `.claude/plans/**` / `CLAUDE.md` não casam. Ausência de run
   **não** é falha nem regressão — é o filtro funcionando. Nos commits
   `4d752e4` e `42b7812` só o `Validate` rodou, e isso está correto.
2. **`cancelled` não é falha.** Pushes em sequência cancelam o run
   anterior pelo grupo de concorrência — `7d46494`, `2ab39f6` e `d492f39`
   aparecem `cancelled` no `Validate` por isso, e o run do commit
   seguinte é o que vale. Lição já catalogada:
   `feedback-job-timeout-shows-as-cancelled-measure-suite-margin`.

⇒ Antes de tratar CI como sinal, confirme **qual sha** o run cobre e
**se o workflow foi elegível** naquele commit.

### 0.8 Commit e push

Commits **granulares**, um por item fechado, com corpo que registra a
MEDIÇÃO (não a intenção). Push após cada commit verde — não acumule. Se a
sessão morrer, o que estiver pushado é o que sobreviveu.

---

## 1. ESCOPO DA NOITE

> Ordenado por valor × independência. Cada item traz o que o FECHA, e
> nenhum depende das 3 OQs ou de path 🔒.

### Verdade desconfortável primeiro: NENHUM plano fecha nesta noite

Medido, não estimado. `PLAN-182` está 7/7 em ACs mas tem `[P0]` aberto que
é decisão do Owner. `PLAN-183` está 4/7 e as três ACs restantes são 🔒 ou
OQ-2. Os demais estão em `reviewed` sem checkbox, ou congelados.

**O que FECHA nesta noite é um DEFEITO, não um plano: o D4.** Isso é
closure real e verificável — e é a melhor coisa disponível sem o Owner.

---

### N1 · `[L]` · O resolvedor de fonte vira DADO COMPARTILHADO — e o D4 fecha

**Por que este é o item 1.** Três coisas independentes convergiram nele:
a dívida que eu mesmo nomeei na §8.5.2, o achado P2 do pair-rail
("promote the route map"), e a convergência **C3** do debate (dois
críticos). E ele **cura o D4**, que é um dos quatro defeitos do vermelho.

**Não depende de nenhuma das 3 OQs.** As OQs são sobre *registro de
ownership* e sobre a *pista do gerador*; este item responde outra
pergunta — *qual arquivo é a fonte deste destino*. São separáveis, e a
§8.5.2 já registra que são duas peças distintas.

**Paths (todos medidos LIVRES):**
- `scripts/delivery-routes.tsv` — **novo**, o dado compartilhado
- `scripts/tests/_parity_classify.py` — passa a LER o TSV (hoje tem mapa local)
- `scripts/doctor.sh` — passa a LER o TSV; **quatro** sítios, não três:
  `:401` (o `cp -p` que REPARA), `:507` (ausente), `:553` (drift) e
  `_dr_delivered` (`:625`, usado em `:633/:638/:643`) — este quarto foi
  achado pelo debate e **verificado na S324**; ele decide ENUMERAÇÃO,
  logo quem é acusado de órfão
- `.claude/scripts/tests/test_parity_source_resolution.py` — testes

**Forma do TSV, com precedente no repo.** Copie a mecânica do
`scripts/tests/ownership_table.tsv`: bloco de comentário no topo, linha de
cabeçalho, e leitura em bash por
`while IFS=$'\t' read -r dest src transform flag_dep origem nota`
(padrão literal em `test-ownership-verdict-unit.sh:61`). Em Python, split
por `\t`. **Um arquivo, dois vocabulários de leitor, zero mapas
privados.**

Conteúdo inicial = as 6 rotas medidas na S324 (5 via `install_docs_template`
+ o ramo renderizado), com `transform` ∈ {`identity`,
`substitute:{{OWNER_HANDLE}}`} e `flag_dep` marcando o ramo
`--github-owner`.

**O terceiro consumidor fica de FORA por desenho:**
`scripts/_framework_manifest_set.sh` é 🔒. Ele entra na cerimônia. Deixe o
TSV pronto para ele e **anote no runbook de saída** que ele é o único
consumidor faltante — isso encurta a cerimônia futura em vez de bloquear
esta noite.

**Fecha quando:**
1. `grep -l delivery-routes.tsv` prova que `_parity_classify.py` **e**
   `doctor.sh` leem o arquivo;
2. nenhum dos dois carrega mapa próprio (`_TEMPLATE_DELIVERED` /
   `_RENDERED_DELIVERED` saem do módulo, ou passam a ser CARREGADOS do TSV);
3. os 10 testes existentes seguem verdes **sem alterar as asserções** —
   se uma asserção precisar mudar, o refactor mudou comportamento e isso é
   sinal de PARAR e reler;
4. o censo derivado de rotas (que a S324 landou) continua vermelho ao
   remover uma entrada do TSV — **controle negativo obrigatório**, e ele
   agora prova o arquivo compartilhado, não uma constante;
5. `doctor.sh` ganha teste: fixture com `docs/BRANCH-PROTECTION.md`
   deletado ⇒ repara com os bytes de `templates/`, **não** com o
   homônimo da raiz. Sem esse teste o `:401` segue reparando errado e o
   item NÃO fechou.

**Armadilha nomeada:** o `:401` não classifica — **copia**. Um teste que
só verifique classificação deixa o reparo errado passar. O controle tem de
observar os BYTES escritos.

---

### N2 · `[M]` · Os achados do debate que não dependem das 3 OQs

Do consenso (`debate/w5-round-1/consensus.md`), estes são texto de plano
(livre) e não tocam decisão nenhuma:

- **Checks vacuosos → reescritos.** O pior, nomeado por dois críticos: a
  asserção negativa `grep {{OWNER_HANDLE}} == 0` é satisfeita
  **exatamente** pelo modo de falha perigoso. Toda asserção negativa da
  wave precisa de um par positivo que falhe quando o defeito existe.
- **Inversões de ordem.** Um item `[P1]` é pré-requisito de três `[P0]`.
  Re-ordenar **só** o que não depende das OQs; onde depender, marcar
  `⛔ gated by OQ-n` em vez de reordenar às cegas.
- **A promessa da §9.8 sem checkbox** — o controle positivo rodando
  independente do step principal. A checkbox entra; a IMPLEMENTAÇÃO é 🔒
  (`.github/workflows/smoke-install.yml`) e fica para a cerimônia. Anote
  a separação explicitamente.
- **`_dr_delivered` no censo de consumidores** — o quarto sítio, agora
  verificado.
- **`uninstall.sh` sem Check nenhum**, apesar de a wave AMPLIAR o alcance
  dele (convergência C4). Adicionar o Check; executá-lo pode exigir 🔒 —
  se exigir, a checkbox fica e a execução é da cerimônia.

**Fecha quando:** cada achado do consenso está ou (a) incorporado, ou
(b) explicitamente marcado como gated, com a OQ que o gateia nomeada.
**Nenhum achado fica sem disposição** — é a classe que o rail nomeou
("constraints in prose, not in the checklist").

---

### N3 · `[M]` · PLAN-182 — o elo de custódia e os `[P1]` abertos

**Não tente fechar o plano.** A rota do installer é `[P0]` e é decisão do
Owner (recomendação registrada: **NÃO**). O que dá:

- **O elo de custódia `new-chain ↔ archive`** (`[P0]`, L667). O Check
  aceita **duas** saídas: um evento na cadeia nova citando o caminho do
  archive e o último HMAC dele, **OU** uma linha de aceite escrita.
  ⚠️ **Prefira a linha de aceite escrita.** Emitir na cadeia HMAC VIVA é
  exatamente a superfície que a S321 mediu como perigosa (a suíte
  escrevendo 19.344 elos não-atribuíveis). Se optar pelo evento, isole e
  prove atribuição — e isso é trabalho de sessão inteira, não de item.
- **Os 4 `[P1]`:** re-avaliar `ceo-boot`/`audit-tokens`/`skill-health`
  como eficácia de controle; `ceo-backup.sh`/`ceo-restore.sh` que ainda
  defaultam para o literal; templates com dono declarado; e o e2e de dois
  adopters via `install.sh` real. **Rode o oráculo em cada path antes de
  tocar** — alguns podem ser 🔒.

**Fecha quando:** o `[P0]` do elo de custódia tem disposição escrita e
verificável, e cada `[P1]` está fechado com evidência ou marcado com o
bloqueador medido.

---

### N4 · `[S]` · Oportunista — o que o survey da S324 apontar

Um workflow de levantamento (`wf_8e901ad2-f03`, 3 lanes read-only) rodou
na S324 perguntando, por plano aberto, o que é executável sem cerimônia e
sem decisão. **Ele não havia retornado quando este runbook foi fechado.**

⇒ **Primeira ação da noite:** ler o resultado dele **antes** de começar o
N1, e só então decidir se algo do N4 sobe de prioridade.

```bash
D=~/.claude/projects/-Users-joaocanhada-canhada-labs-ceo-orchestration/*/subagents/workflows/wf_8e901ad2-f03
grep -c '"result"' $D/journal.jsonl     # compare contra 3 agentes
tail -c 3000 $D/journal.jsonl
```

Se der `0/3` e os transcripts estiverem parados há muito, ele morreu com
a sessão — **re-rodar é legítimo** (é read-only e barato):
`Workflow({scriptPath: '…/night-scope-survey-wf_8e901ad2-f03.js'})`.
E lembre da lição: **`0 results` não é prova de morte** — cheque `etime`
dos transcripts antes de concluir.

---

### Cronograma e orçamento

| janela | item | se estourar |
|---|---|---|
| 0:00–0:15 | ler o resultado do survey (N4) e re-priorizar | se ele morreu, re-rode e siga para N1 sem esperar |
| 0:15–3:30 | **N1** (route table + 2 consumidores + testes) | é o item que mais paga; se travar em 3 tentativas, PARE e escreva o diagnóstico — não tente a 4ª |
| 3:30–5:00 | **N2** (achados do debate no plano) | corte pelo fim da lista, não pela qualidade de cada item |
| 5:00–6:15 | **N3** (PLAN-182) | se o elo de custódia exigir a rota do evento, ABANDONE e escreva a linha de aceite |
| 6:15–7:00 | closeout: memória, `CLAUDE.md` (uma edição), handoff, resumo executivo | **reserve esta janela inteira** — closeout apressado é como a S324 gravou duas afirmações que caíram no mesmo dia |

**Orçamento:** ~700k–1.1M tokens. O N1 é o único item com fan-out
previsto (censo dos consumidores); N2 e N3 são trabalho direto e não
precisam de agente. **Não gaste fan-out em coisa que um `grep` resolve** —
a lição `feedback-rail-finds-the-class-census-closes-it` vale aqui.

**Regra de continuidade:** *não pare enquanto houver condição.* Se um item
fechar antes da janela, puxe o próximo. Se todos fecharem, o excedente vai
para o N4 e depois para dívida catalogada (`# CEO-DEBT:` no ledger) — mas
**nunca** para dentro de um 🔒 nem para responder uma OQ.

## 2. O que NÃO entra, e por quê

| item | bloqueador |
|---|---|
| W5-b (qualquer linha) | as 3 OQs do §0.2 |
| PLAN-183 W1 / AC-1 (ponteiro portátil) | 🔒 `install.sh` + `_framework_manifest_set.sh` |
| PLAN-183 AC-2 / AC-5 | OQ-2 em aberto (repo descartável = fixture de CI ou roteiro de release?) |
| regenerar `.claude/settings.json` (defeito A4 vivo) | 🔒 `settings.json` |
| controle positivo do e2e rodando independente (§9.8) | 🔒 `.github/workflows/smoke-install.yml` |
| rota do installer do PLAN-182 (`[P0]`) | decisão do Owner (recomendação do CEO: **NÃO**) |
| plano de segurança para F1/F2 | criar plano muda o roadmap — decisão do Owner |
| flip do PLAN-179, destino do PLAN-176 | decisões do Owner |

---

## 3. Entrega ao Owner, no fim da janela

1. **Resumo executivo** no topo do handoff: o que fechou, o que não, e
   **por que** — com a medição de cada afirmação.
2. `MEMORY.md` (cabeçalho + índice) e o arquivo-missão atualizados; toda
   afirmação obsoleta **corrigida, não acrescentada** — a S324 aprendeu
   isso: um bloco novo em cima de um bloco obsoleto faz a próxima sessão
   ler o obsoleto primeiro.
3. `CLAUDE.md` §5 editado **uma vez**, se e só se o contrato durável
   mudou.
4. **Nada pendente de assinatura** deve aparecer por surpresa: se a noite
   produzir material de cerimônia, ele vem com sentinel na forma VIVA
   (`PLAN-*/wave-*-approved.md`, `<!-- BEGIN SIGNED SCOPE -->`,
   `Approved-By:` → `Plans:` → `Scope:`), **nunca** na forma do PLAN-177,
   que é inerte (medido: `_sentinel_grants_path` = False).
