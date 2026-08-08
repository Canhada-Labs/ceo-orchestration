---
plan: PLAN-169
round: 1
archetype: VP Engineering
created_at: 2026-08-08
---

# VP Engineering — round 1 (PLAN-169)

> Método: rodei o predicado real de canonicalidade
> (`_matches_canonical_guard`, `.claude/hooks/check_canonical_edit.py:896-915`)
> contra cada superfície citada nas waves, li o assert de release, contei as
> registrações de hook no `settings.json` vivo e conferi a cobertura do ledger
> por grep. Toda crítica abaixo é falsificável com o comando indicado.

## Verdict

**ADJUST** — a tese macro (dois trens em sequência; instrumento antes do trem;
claim só depois de teste pré-registrado) está correta e o W1 é a melhor peça do
plano, mas a **fronteira canônico/livre está errada em 2 itens, o W4 inteiro não
tem slot de cerimônia, o orçamento não cobre o W5 por 1-2 ordens de grandeza, e
2 itens do ledger ficaram sem endereço** — um deles é justamente o gate que teria
pego a causa-raiz que o W1 existe para consertar.

## Summary

- **A taxonomia de waves não bate com o predicado real.** `.github/workflows/*.yml`
  e `.claude/hooks/*.py` são CANÔNICOS (`check_canonical_edit.py:184` e `:139`),
  logo **W2.1 e W2.4 não são "superfícies livres"**. Pior: **W4 é canônico quase
  inteiro** (settings.json + hooks novos + team.md) e **não tem cerimônia
  atribuída** ⇒ ou o pack W3 incha — exatamente o risco que o plano nomeia
  (`PLAN-169:466-468`) — ou o W4 fica bloqueado na execução.
- **O orçamento não fecha.** Só o E4 como pré-registrado são 30 cadeias × 2
  condições × 3 repetições × até 5 hops ≈ **900 invocações de agente**
  (`PLAN-169:336-341`, `research-academia.md:250`); o frontmatter declara
  **450-700k tokens / 8-11 sessões para o plano inteiro** (`PLAN-169:8-9`),
  incluindo **dois** trens de release com hold de 24h cada.
- **W4.4 foi dimensionado pela pesquisa, não pelo disco.** `ConfigChange` **já
  está registrado** (guard do PLAN-135 W2 H2, vivo no `settings.json`); matchers
  hifenizados são **2**, não 48; matchers com vírgula e condições `if:` são
  **zero**. O "P0 auditoria dos 48 matchers" encolhe para 3 alvos nomeáveis.

## Risks

- **R-1 — Recorrência da lição-mãe da S296 por construção, não por descuido.**
  O plano protege o W3 contra inchaço em prosa (`:466-468`) mas empurra para ele
  todo o resíduo canônico de W2 e W4 por omissão de classificação. O mecanismo da
  S296 (patch ramo-a-ramo num produto cartesiano) reaparece se um único pack tiver
  que carregar: B.a (upgrade.sh) + E.10 + emenda ADR-163 + ADR break-glass + ADR
  cross-session + settings.json (W4.2/W4.3/W4.4) + 2-4 hooks novos. Isso não é um
  pack de "3-5 itens fechados"; é a superfície de 3 planos.
- **R-2 — Interação W1 × W2.6 sobre o MESMO arquivo.** O aceite do W1 é o
  conjunto exato 62/3 do e2e de ownership; e `.claude/.framework-version` é uma
  **superfície observada por esse e2e** e governada pelo veredito de propriedade
  (`upgrade.sh:2109-2144`, `_framework_manifest_set.sh:141,301`). O controle
  positivo do W2.6 ("marcador dessincronizado ⇒ vermelho", `:152`) muta esse
  arquivo. Plantar o controle com o nightly como gate de aceite do W1 é receita
  de RED ambíguo.
- **R-3 — W6.1 executa um runbook com defeito conhecido não corrigido.** E.11
  (runbook §7 do 166 usa `\s` em `grep -E`/`sed`, que no BSD devolveu falso "tudo
  fora de escopo") não aparece em nenhuma wave — e o W6.1 é literalmente
  "executa PLAN-166 W2 como escrito" (`:367`). O check de escopo
  `touched−scope=∅` é o que impede um land fora de escopo na janela de release.
- **R-4 — Assimetria de disciplina entre W4.1 e W4.2.** O W4.2 exige probes
  empíricos ANTES do desenho (`:234-242`) — correto. O W4.1 tem a mesma densidade
  de incerteza de substrato e **nenhum probe-gate**: entra direto no desenho de
  duas camadas. Ver MF-4.
- **R-5 — Contaminação do próprio experimento pela postura que o plano instala.**
  O W4.2 instala `crossSessionInbound: "refuse"` como default e o W5 mede fleets
  cross-session com override por `--settings` (`:249-250`). A constante de design
  que o E4 produzir vale para a postura do experimento, não para a postura
  entregue. Precisa estar escrito no pré-registro, senão o relatório fala de uma
  configuração que ninguém roda.

## Must-fix (blocking)

**MF-1 — Reclassificar W2.1 e W2.4; a lista de "superfícies livres" está errada.**
Verificação (`_matches_canonical_guard`, executável em 10 s):

| Alvo da wave | Item | Predicado |
|---|---|---|
| `.github/workflows/smoke-install.yml` | **W2.1** | **CANONICAL** (`check_canonical_edit.py:184`) |
| `.claude/hooks/check_anti_ceo_overhead.py` | **W2.4** | **CANONICAL** (`:139`) |
| `.claude/hooks/tests/test_check_pair_rail_matrix.py` | W2.2 | free |
| `.claude/scripts/inject-agent-context.sh` | W2.3 | free |
| `.claude/scripts/local/pair-rail-gate.sh` | W2.5 | free |
| `.claude/scripts/local/_release_bump_sites.py` · `verify-counts.sh` | W2.6/W2.7 | free |
| `docs/TROUBLESHOOTING*.md` · `docs/GUIA-COMPLETO.md` | W2.4/W2.7 | free |
| `scripts/tests/test-ownership-table.sh` | W1 | free ✔ |

Ou seja: **W2 tem 6 itens livres e 2 canônicos**. Os dois canônicos precisam de
sentinel. A cura barata: **W2.1 e W2.4-hook migram para o pack W3** (é 1 linha de
workflow + o canal de ack), **W2.4-doc fica no W2** (docs são livres). Sem isso, a
execução autônoma bate no `check_canonical_edit.py` no meio do W2 e improvisa —
que é o cenário que a cerimônia existe para impedir.

**MF-2 — W4 precisa de um slot de cerimônia próprio, declarado agora.**
Todo o enforcement do W4 mora em superfície canônica:

- W4.1: hook novo em `.claude/hooks/*.py` + registração no `settings.json` — **ambos canônicos**;
- W4.2: `crossSessionInbound` no `settings.json` + `PreToolUse` em `SendMessage`/`ListAgents` (hook novo) — **canônicos**;
- W4.3: permission rules `Agent(param:value)` no `settings.json` + tabela de tiers no `.claude/team.md` — **canônicos** (`:116`);
- W4.4: `ConfigChange`/`PostToolBatch`/`TaskCompleted` — todos registração no `settings.json` — **canônicos**.

O plano só menciona cerimônia para o W3 e o W3-K. Decidir explicitamente entre:
**(a)** W4 vira **PLAN-170** com pack próprio (minha recomendação — casa com "item
novo = wave nova ou plano novo, não inchaço do pack", `:468`); ou **(b)** W4 ganha
"**W4-C — cerimônia de substrato**" como wave nomeada, com escopo fechado ANTES de
começar. O que não pode é ficar implícito: implícito vira W3 inchado.

**MF-3 — Orçamento: o W5 não cabe no plano; declare o número ou tire o W5.**
Contas com os N do próprio pré-registro:

- **E4:** 30 cadeias × 2 condições × 3 repetições = 180 cadeias; a até 5 hops =
  **até 900 invocações de agente**. A 10-20k tokens por hop (piso otimista para um
  agente com spec de 20 restrições) são **9-18M tokens** — 15-40× o orçamento
  declarado do plano inteiro.
- **E3:** 4 braços × k∈{1,3,5} × ≥3 runs com defeitos semeados e refuter por
  finding — dezenas de agentes de review, cada um com o contexto do alvo.
- **E0** é o único de custo ~zero, e é o que **gateia** E1/E2.

Além disso, W6 são **dois** trens completos: o rc.1 do 1.3.0 consumiu 4 rodadas de
rail e 18 achados (histórico registrado em memória), e cada trem tem hold de 24h +
re-pass em worktree da tag. Só W6 é plausivelmente 3-5 sessões.

Cura mínima: **W5 sai para plano próprio com orçamento próprio**, ficando no
PLAN-169 apenas **E0** (retrospectivo, custo ~zero, e é ele que decide se E1/E2
existem). Se o W5 ficar, o frontmatter precisa dizer o número real e o plano
precisa declarar que o orçamento é dominado pelo experimento, não pelo fechamento.

**MF-4 — quota-resume: a camada (i) não é implementável como descrita, e a
propriedade de continuidade não está declarada.**
O plano diz: "hook no evento `StopFailure` com matcher `rate_limit` … **o hook lê
`resets_at` do snapshot e agenda a retomada**" e "**o cron do harness** dispara com
REPL idle" (`:202-208`). Dois problemas de arquitetura:

1. **Um hook não pode criar um cron do harness.** `CronCreate` é tool voltada ao
   modelo; hook é subprocess. No instante do `StopFailure(rate_limit)` o modelo é
   exatamente o recurso indisponível — não há quem chame a tool. O hook só pode
   escrever estado ou agendar **fora** do harness (`at`/`launchd`), que é outro
   mecanismo, com outras propriedades e outro teste.
2. **O cron do harness é session-scoped e in-memory** — o job morre quando o
   processo do Claude sai. O cenário real de quota ("estourou, o Owner fecha o
   terminal e volta depois") é justamente o que mata o job. O aceite proposto
   ("job agendado no resets_at+jitter, 1 e só 1", `:222-224`) **passaria** num
   mecanismo que não sobrevive ao fechamento do terminal.

Cura: **aplicar ao W4.1 a mesma disciplina probe-first do W4.2** — W4.1.0 com
três probes (o hook `StopFailure(rate_limit)` dispara mesmo? o snapshot está
fresco nesse instante? um one-shot sobrevive a quê?) — e **declarar no plano qual
propriedade se compra**: "sessão viva e ociosa retoma sozinha" (cron do harness
basta) **vs** "trabalho retoma mesmo com o terminal fechado" (exige scheduler de
SO + `claude -p`, escopo maior). São produtos diferentes.

**MF-5 — A retomada tem de ser agendada estritamente DEPOIS de `resets_at`, com
margem > 90 s e fora dos minutos `:00`/`:30`.** O scheduler do harness aplica
jitter determinístico próprio e **one-shots no topo/meia hora disparam até 90 s
ANTES** do horário pedido. Agendar "no `resets_at` + jitter" sem direção declarada
pode disparar **antes** do reset, bater na parede de novo e queimar o único
one-shot. O plano precisa fixar `resets_at + margem ≥ 120 s`, minuto ≠ `:00`/`:30`,
e um teste que asserte o horário efetivo, não só a unicidade do job.

**MF-6 — Re-escopar o W4.4 contra o disco antes de executar.** Medido no
`settings.json` vivo (48 registrações, batendo com o CLAUDE.md):

- `ConfigChange` **já existe** — guard do PLAN-135 W2 H2, **fail-open e
  advisory-block**. O item honesto não é "adicionar `ConfigChange`", é
  "**promover o guard existente de advisory para bloqueante**", que é um trabalho
  diferente, menor e com uma decisão de doutrina embutida (fail-open em infra vs
  fail-closed em input).
- **Matchers hifenizados: 2**, ambos `mcp__codex__codex|mcp__codex__codex-reply`
  (PreToolUse + PostToolUse). Os dois listam o nome completo em alternância, logo
  a mudança 2.1.195 provavelmente **não** os matou — mas é um controle positivo de
  minutos, não uma "auditoria dos 48".
- **Matchers com vírgula: 0.** **Condições `if:`: 0.** Duas das cinco classes de
  drift nomeadas no W4.4 são **vacuosas por construção** neste repo.
- A classe que sobra com potencial de mudança de veredito é a inversão 2.1.214
  (exit 2 + JSON inválido no stdout): na árvore, só `check_harness_config.py` e o
  wrapper `_python-hook.sh` mencionam exit 2. **Alvo total do P0: 3 arquivos.**

Reescrever o W4.4 com esses números transforma uma wave de tamanho indefinido num
item de algumas horas — e libera orçamento para o MF-3.

**MF-7 — AC-1 é falso como escrito: 2 itens do ledger não têm endereço.**
`grep -o 'E\.[0-9]\+'` no plano devolve E.1-E.6, E.8-E.10, E.12-E.17. **Faltam
E.7 e E.11**, e `grep -c shellcheck` no plano = **0**.

- **E.7 (P2) — o shellcheck de CI cobre só `.claude/{scripts,hooks}`; `scripts/tests/**` fica FORA.**
  Isto é grave por contexto, não por severidade: `scripts/tests/test-ownership-table.sh:162`
  é a causa-raiz que justifica a wave W1 inteira, e é **exatamente o diretório sem
  lint**. O plano gasta uma wave curando a instância e **descarta a prevenção da
  classe**. Estender o shellcheck a `scripts/**` pertence ao W1, junto com o
  sweep do item 4 (`:130-131`).
- **E.11 (P3)** — ver R-3; é um defeito no runbook que o W6.1 vai executar.

## Nice-to-have

- **NH-1 — Promover E0 para o W0.** Custa ~zero, usa dado que já existe, e o
  resultado (H ≥ 0,40?) decide se E1/E2 existem. Rodá-lo no W0 significa entrar na
  conversa de orçamento do MF-3 **com o número na mão** em vez de com uma
  projeção. É o único experimento cujo resultado pode tornar os outros
  desnecessários (`research-academia.md:188`).
- **NH-2 — OQ-4 tem resposta derivável, e a família é maior do que E.4 diz.**
  A família "script livre que decide gate" é definível por predicado, não por
  enumeração: *decide um gate de governança* **E** `_matches_canonical_guard()`
  devolve `False`. Rodando o predicado, além dos dois nomeados no ledger
  (`verify-counts.sh`, `check-canonical-doc-freshness.py`) entram no mínimo:
  `_release_bump_sites.py`, `pair-rail-gate.sh`, **`ownership-nightly-gate.sh`** e
  **`test-ownership-table.sh`**. Os dois últimos merecem destaque: são os
  instrumentos que o PLAN-168 acabou de endurecer e que **decidem se o veredito da
  tabela de propriedade é honrado** — livres. Minha recomendação para OQ-4:
  **checksum no gate** (barato, sem cerimônia por edição, e o instrumento muda com
  frequência legítima), reservando guard canônico para o subconjunto que decide
  release. Mas a decisão precisa da lista derivada pelo predicado, não da lista
  lembrada.
- **NH-3 — Fixar o locus de invocação no pré-registro do W5.** Um teammate
  in-process **não pode** ter subagent em background (`research-claude-updates.md:339`),
  então `audit-fanout`/`council-audit` medidos a partir do lead e a partir de um
  teammate não são comparáveis. O bloco metodológico imutável precisa de uma linha
  dizendo de onde o instrumento é invocado.
- **NH-4 — Ordenar W1 antes de qualquer controle plantado no marcador** (R-2), e
  registrar no W2.6 que o controle positivo é **transitório**: plantar, ver
  vermelho, despantar no mesmo commit. Nunca atravessar uma janela de nightly com
  o controle plantado.
- **NH-5 — Nomear os dois escritores do marcador no W2.6.** Hoje quem escreve
  `.claude/.framework-version` no alvo instalado é o caminho de propriedade
  (`upgrade.sh:2109-2144`, entrada de manifesto em `_framework_manifest_set.sh:141,301`);
  o W2.6 adiciona o `bump` como escritor no meta-repo. Não colidem (superfícies
  diferentes), mas isso precisa estar escrito, senão o próximo leitor lê "dois
  escritores do mesmo arquivo" e reabre o assunto.

## Unseen

- **U-1 — Qual é a rota de UPGRADE da postura `crossSessionInbound: "refuse"`?**
  O W4.2 diz "no `settings.json` **instalado**" (`:246-248`), o que é uma mudança
  de conteúdo entregue a adopters — e o `settings.json` de um adopter é a
  superfície mais customizada que existe. O plano não diz se isso passa pelo
  veredito de propriedade, se preserva customização do adopter, nem o que acontece
  se o adopter tiver `accept` explícito. Foi exatamente essa classe de pergunta que
  custou os PLAN-167 e 168 inteiros. **Responder antes de escrever a linha.**
- **U-2 — O buraco de proveniência do inbound tem um compensador barato que o
  plano não considera.** O plano registra honestamente que o recebimento não tem
  hook e adota `refuse` como defesa. Mas com `refuse` a mensagem é **descartada**
  e o log HMAC não registra nem a tentativa — e a doc diz que uma sessão que recusa
  "não mostra diferença visível" (`research-claude-updates.md:92`). Vale decidir
  explicitamente: aceitamos cegueira sobre tentativas de inbound, ou queremos um
  contador (via o socket `CLAUDE_CODE_MESSAGING_SOCKET`, superfície já mapeada em
  `research-claude-updates.md:80,109`)? Para um framework cuja tese é
  auditabilidade, "recusado e invisível" é uma escolha, não um default.
- **U-3 — O W3-K rodar "na mesma sessão" do W3 (`:182`) esconde um duplo-gate.**
  Editar `check_arbitration_kernel.py` é KERNEL: exige `CEO_KERNEL_OVERRIDE` +
  `CEO_KERNEL_OVERRIDE_ACK` **além** do sentinel (`check_canonical_edit.py:151-155,
  218-220`). Duas cerimônias com posturas de override diferentes na mesma sessão é
  onde um `export` sobra no ambiente. Recomendo sessões separadas, ou pelo menos
  uma asserção explícita de ambiente limpo entre elas.
- **U-4 — Nada no plano fecha o loop de "quem verifica o verificador" no W5.**
  A literatura anexada diz que o teto de todo test-time compute é a qualidade do
  verificador (`research-academia.md:134,238`). O E3 mede recall contra defeitos
  semeados por nós — mas o grading cego é feito por quem/o quê? Se for LLM-judge,
  ele precisa de validação própria (o METR validou o dele em 34 labels e chamou o
  resultado de soft upper bound, `research-academia.md:37`). Sem isso o E3 mede o
  juiz, não os revisores.

## What I would NOT change

- **A tese dos dois trens (OQ-1).** Endosso sem ressalva. Injetar features na
  1.3.0 reabre o debate do 166 e viola o delta-allowlist que o próprio 166
  construiu; e o bump minor do 1.4.0 é um controle positivo ao vivo do fix E.1
  que sai de graça. Recomendação mantida: 1.3.0 GA → 1.4.0.
- **W1 inteiro.** É a melhor peça do plano: causa-raiz única com contabilidade
  fechada (22+2=24), aceite falsificável (62/3 exatos), riders com controle
  positivo cada, e a proibição explícita de tocar `ownership_table.tsv` /
  `ownership-expected-reds.txt`. **Não relaxar o "qualquer resíduo = parar e
  investigar"** (`:132-134`) — é o que impede o port de virar ajuste de tabela.
  Confirmei a causa-raiz no disco: `test-ownership-table.sh:162` é `stat -f`
  primeiro, e `install.sh:729` é a forma correta no mesmo repo.
- **A ordem do W2.6 (marcador) e o diagnóstico E.1/F.7.** Verifiquei:
  `VERSION=1.3.0` e o marcador `1.3.0` batem hoje; `release.yml:84-97` compara
  byte-a-byte e é fail-closed; e o VERSION permanece `1.3.0` nos cortes de rc
  (a rc.1 provou). Logo o prazo duro é mesmo **o primeiro bump de minor**, o rc.2
  e o GA do 1.3.0 passam, e a colocação no W2 (antes do W6.2) está certa.
- **"Novidade vira claim só depois de teste pré-registrado" e a decisão de não
  retirar o "no speed claim".** A literatura anexada fortalece a linha, e o
  desenho com braço token-matched obrigatório + gate-zero de Amdahl é o único
  jeito honesto de perguntar. Minha objeção ao W5 é de **orçamento e locus**
  (MF-3, NH-3, U-4), **não de método**.
- **Pontos Owner-only parando em checklist de retorno** (`:87-89`). Correto e
  não-negociável, mesmo sob pré-autorização de execução autônoma.
- **A recomendação de DEFER para channels** (`:294-297`). É a única superfície da
  janela que **aprova** em vez de pedir; deferir com causa registrada é a decisão
  certa.
