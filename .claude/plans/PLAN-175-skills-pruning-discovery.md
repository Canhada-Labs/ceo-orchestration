---
id: PLAN-175
title: Skills — descoberta antes de poda: regra de poda falsificável, unknown-ratio <0,10, domain-packs opt-in, contagem derivada
status: reviewed
reviewed_at: 2026-08-11
reviewed_by: "Owner - ratificacao S302f via OWNER-RATIFY-S302.sh: ratifico os 6 planos na v2.6 (rail Codex 7 rounds, r7 APPROVE, commits ab45f56..0c90174)"
created: 2026-08-11
last_revised: 2026-09-07
owner: CEO
depends_on: [PLAN-171]
budget_tokens: 620-950k
budget_sessions: 4
budget_usd_estimate: 500-610
tier_mix_estimate: "assento MEDIDO = Fable 5.1 (10/50 por MTok); refutadores Opus 5 (5/25); docs Sonnet 5; piso VETO nunca abaixo de Opus 5 (ADR-052). A conversão entre o assento medido e o assento planejado está declarada no §9 — sem ela a figura por sessão não é aplicável ao mix."
context_risk: medium
external_wait: none
eta_calendar: "mesmo-dia a D+1"
tags: [skills, telemetry, pruning, seed]
---

# PLAN-175 — Skills: fechar a distância entre claim e realidade

> **SEMENTE (S302, 2026-08-11), com o denominador datado.** Da auditoria
> total: a telemetria do `skill-health` sobre o histórico de então mostrou
> **157 de 164 skills com zero invocações (96%)** e **43,4% dos spawns sem
> resolver para o catálogo**. Os `164` daquela leitura são o
> `catalog_size` — a contagem de nomes DISTINTOS, que deduplica os dois
> pares de basename repetido. A contagem de ARQUIVOS é 166. As duas
> continuam certas hoje e medem coisas diferentes; ver §4.6.
> "166 skills ready-made" segue sendo a maior distância entre claim e
> realidade do repositório. Não é gargalo de velocidade — o modo por
> referência já evita o custo por sessão. É honestidade de catálogo e
> qualidade de roteamento.

## 0. O que este round mudou, e o que ele NÃO autoriza

Esta é a versão revisada pelos rounds 1 e 2 do debate
(`.claude/plans/PLAN-175/debate/round-1/consensus.md` e
`.claude/plans/PLAN-175/debate/round-2/consensus.md`; três críticos por
round, seis `ADJUST`). O round 1 foi absorvido em 2026-09-06 sob
autorização do Owner (item 4.15 do ledger de decisões); o round 2 terminou
em `ESCALATE-TO-OWNER` com oito itens bloqueantes e sete perguntas abertas,
e é o que esta revisão absorve.

Três mudanças, todas medidas:

1. **O bloqueio por CALENDÁRIO caiu.** A versão anterior afirmava que a
   re-medição precisava de tempo de exposição e tratava isso como espera
   externa. Isso foi medido com o leitor errado (uma janela de 24 horas).
   Com o leitor certo, o denominador de SPAWNS que o plano pedia **já
   existe** (medido 2026-09-07: 114 spawns).
2. **A regra de poda apertou — e apertou demais.** A perna 0 escrita no
   round 1 exclui da candidatura as 42 skills core, isto é, TODAS. O
   veredito `ARQUIVAR` ficou inalcançável por construção e a W2 abria sem
   entrada. O round 2 mediu isso; esta revisão troca a ARQUITETURA da
   perna 0 em vez de lhe dar mais uma exceção, como a regra de parada da
   própria W0 manda. Ver §2.1.
3. **A ordem das ondas inverteu.** O gate de contagem é BIDIRECIONAL:
   arquivar uma skill deixa vermelhos os documentos que publicam o número.
   A onda de contagem derivada (W4) passa a PRECEDER a onda de poda (W2).
   Ver §1 e §5.

**Sete perguntas continuam abertas e são do Owner**, não deste texto: elas
estão no §10, cada uma com as opções MEDIDAS e a consequência de cada
opção. Nenhuma foi decidida aqui.

**Este round é coerência de DESENHO, não autorização de execução.** Nem a
linha de debate do §6, nem esta revisão, nem o `status: reviewed` liberam
execução: o flip para `executing` é decisão do Owner, registrada no item
4.10 do mesmo ledger, e acontece depois desta revisão landar.

## 1. Ordem de ataque (a ordem IMPORTA)

1. **Descoberta ANTES de poda, em duas fases.** Fase 1 = sugestão
   consultiva (as três melhores skills sugeridas por similaridade de
   texto, sem bloquear nada). Fase 2 = recusar spawn que não declara skill
   NENHUMA, **ativada se a re-medição da Fase 1 deixar o unknown-ratio
   ACIMA de 0,10** — critério pela META, não por queda relativa, e a
   comparação é estrita. **Fronteira com dono único:** o instrumento de
   referência é `ceo-boot.py`, que marca vermelho em `ratio > 0.10`;
   portanto **0,10 exato NÃO ativa a Fase 2**, e este plano abandona a
   forma maior-ou-igual que carregava antes. **Leitor nomeado, invocação
   completa:**
   `python3 .claude/scripts/skill-health.py --include-rotated --since <janela> --json`.
   Sem `--include-rotated` o leitor vê só o arquivo vivo e subconta; o
   default de janela dele é 30 dias, não 90. **Nota de HEAD:** o flag é
   INERTE hoje — o mesmo run devolve `rotated_siblings_present: false`,
   porque esta família ainda não rotacionou; o flag fica porque a
   SEMÂNTICA do leitor sem ele é subcontar quando houver rotação. Meta:
   unknown-ratio para abaixo de 0,10 (**medido 2026-09-07: 0,246**, sobre
   114 invocações; a leitura do round 1, 0,257 sobre 109, é da mesma
   direção e de outro instante — as figuras deste plano são móveis por
   construção e por isso levam data).
2. **Podar o core por telemetria — regra determinística com TRÊS saídas.**
   A regra é reescrita no §2. O alvo numérico `42 → ~25` **sai da regra**:
   os `~25` vinham do passo de consolidação, que agora tem critério
   próprio (§2.3). ARQUIVAR, nunca deletar. **Quantas skills a regra
   entrega depende da arquitetura de elegibilidade que o Owner ratificar
   (OQ-1, §10): as opções medidas hoje entregam 0, 2 ou 37 candidatas.**
   Este passo não abre antes do passo 5.
3. **Mover os 116 domain skills para pacotes opcionais** instalados por
   tarball assinado (o mecanismo `squad-install` já existe); manter um ou
   dois domínios de referência na árvore. **Bloqueador nomeado:** o
   artefato de contrato da onda W1c do PLAN-171 (fronteira de posse dos
   pacotes), hoje inexistente — o PLAN-171 está `executing` e a W1c é
   contract-only e não iniciada. O que o P3 remove é a FONTE que o
   caminho de instalação por perfil lê hoje (`install.sh` resolve
   `.claude/skills/domains/<parte>` e o gerador de manifesto emite o mesmo
   caminho por parte de perfil), então o teste de regressão tem de exercer
   esse caminho, não só o caminho sem pacotes.
4. **Sweep de atualidade — EXECUTA no PLAN-172 (dono único).** Este plano
   fica com a REGRA permanente: skill core citando modelo morto ou
   codebase fantasma é defeito. Não nomear aqui o sítio do nightly: isso
   recriaria a rota dupla que o round 2 do debate anterior fechou.
5. **Despinar o "166":** contagem DERIVADA ("N core + M frontend + pacotes
   opcionais") nas superfícies de claim — remove o incentivo estrutural
   contra a poda (hoje podar exige cascata de claims mais cerimônia, então
   ninguém poda).

**A ordem de EXECUÇÃO não é a ordem desta lista.** O verificador de
contagens é BIDIRECIONAL — «a doc number that disagrees with live fails»,
`.claude/scripts/local/verify-counts.sh:25-27`, com a métrica de skills
declarada `exact (166)` em `:31`. Logo, arquivar UMA skill move o vivo para
165 e derruba, no mesmo instante, todo documento que publica o número. O
passo 5 é PRÉ-REQUISITO do passo 2, não seu sucessor. A ordem executada é:

> **W0 → W1 → W4 (contagem derivada) → W2 (poda) → W3 (domain-packs)**

com a W3 presa ao seu bloqueador nomeado (§6).

## 2. A regra de poda (reescrita — o coração desta revisão)

A regra anterior tinha duas pernas e uma saída. Aplicada sobre este próprio
repositório ela **arquiva `ceo-orchestration`** — a skill que o Gate 2 do
`CLAUDE.md` manda invocar antes de qualquer trabalho, em toda sessão. A
regra nova tem três pernas e três saídas, e vem com um controle que
FALSIFICA essa autofagia.

### 2.1 As três pernas

**Perna 0 — elegibilidade. A arquitetura do round 1 está REFUTADA por
medição, e a troca é do Owner (OQ-1).**

O round 1 escreveu a perna assim: «uma skill só é CANDIDATA se todos os
canais por que ela é alcançada emitem evento observável», excluindo toda
skill nomeada em `CLAUDE.md`, `.claude/commands/*.md`, `.claude/agents/*.md`
ou no SKILL MAP (`.claude/team.md` mais `.claude/frontend-team.md`). O
motivo continua válido: o canal de invocação por assento e por comando não
emite nada, o leitor conta apenas eventos `agent_spawn` carregando
`skill=<nome>`, e para essa classe inteira a perna "0 invocações" não mede
ausência de uso — mede ausência de instrumento.

O que a medição mostrou é que a REGRA ESCRITA não deixa sobrar ninguém.
Censo por limite de palavra do nome de cada skill core contra cada canal,
lido em 2026-09-07 na árvore do HEAD:

| canal de exclusão | quantas das 42 skills core ele nomeia |
|---|---|
| SKILL MAP (`team.md` + `frontend-team.md`) | **39** |
| `.claude/commands/*.md` | 9 |
| `.claude/agents/*.md` | 8 |
| `CLAUDE.md` | 1 |
| **união dos quatro (a perna como escrita)** | **42 — sobram 0 candidatas** |

Quem zera não é o canal de comandos: é o SKILL MAP, que por desenho nomeia
quase todo o core. Com zero candidatas, `ARQUIVAR` é inalcançável, a lista
da AC-2.1 nasce vazia e a W2 — o único pacote canônico do plano — abre sem
entrada. A regra de parada pré-registrada da W0 («se o controle não ficar
verde em duas rodadas, a regra muda de ARQUITETURA em vez de ganhar mais
uma exceção») disparou: o round 1 arquivava `ceo-orchestration`, o round 2
zera o conjunto. São as duas rodadas.

**As arquiteturas candidatas, com o conjunto MEDIDO ao lado.** Nenhuma é
escolhida aqui — a escolha é a OQ-1 do §10.

| # | o que EXCLUI da candidatura | candidatas medidas (2026-09-07) | consequência |
|---|---|---|---|
| **A** | união dos quatro canais (round 1) | **0 de 42** | REFUTADA: o experimento fica sem sujeito |
| **B** | SKILL MAP mais `.claude/agents/` mais `CLAUDE.md` — sai `.claude/commands/` | **2**: `agent-architect`, `terse-mode` | as duas candidatas são exatamente as alcançadas SÓ por comando, o canal que não emite; arquivar qualquer uma quebra um comando vivo. A W2 abre com 2 skills e cabe no teto de 8 caminhos |
| **C** | `MANTER`-override restrito: Gate 2 do `CLAUDE.md` mais o piso de VETO do ADR-052 derivado de `.claude/agents/` (medido: `ceo-orchestration`, `code-review-checklist`, `identity-and-trust-architecture`, `incident-management`, `security-and-auth`) | **37 de 42** | entrega a poda que o plano promete, mas re-abre para 37 skills a classe que a perna 0 fechou: qualquer skill alcançada só por assento ou por comando vira arquivável por ausência de INSTRUMENTO. A W2 passa a precisar de várias pernas de 8 caminhos |
| **D** | nada — o canal silencioso ganha INSTRUMENTO primeiro, e a perna 0 encolhe para os canais que ainda não emitirem | **não mensurável hoje** | fecha a causa em vez do sintoma; custo: emissão nova sob `.claude/hooks/` (o oráculo responde canônico, logo assinatura) e uma janela de observação DEPOIS de ligar — devolve espera ao plano, contra o `external_wait: none` ratificado |

Comando que reproduz a tabela na árvore do HEAD (biblioteca padrão, sem
depender de arquivo que ainda não existe):

```
python3 - <<'CENSO'
import re, pathlib
R = pathlib.Path(".")
core = sorted(p.parent.name for p in R.glob(".claude/skills/core/*/SKILL.md"))
rd = lambda ps: "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in ps if p.is_file())
ch = {"CLAUDE.md": rd([R/"CLAUDE.md"]),
      "commands":  rd(sorted(R.glob(".claude/commands/*.md"))),
      "agents":    rd(sorted(R.glob(".claude/agents/*.md"))),
      "SKILLMAP":  rd([R/".claude/team.md", R/".claude/frontend-team.md"])}
nm = lambda s, x: re.search(r"(?<![A-Za-z0-9_-])" + re.escape(s) + r"(?![A-Za-z0-9_-])", x) is not None
hit = {s: {c for c, x in ch.items() if nm(s, x)} for s in core}
veto = set()
for a in ("code-reviewer", "security-engineer", "identity-trust-architect",
          "incident-commander", "threat-detection-engineer"):
    f = R / ".claude/agents" / (a + ".md")
    if f.is_file():
        x = f.read_text(encoding="utf-8", errors="replace")
        veto |= {s for s in core if nm(s, x)}
print("core =", len(core))
for c in ch:
    print("  canal %-10s nomeia %d/%d" % (c, sum(1 for s in core if c in hit[s]), len(core)))
print("A candidatas =", len([s for s in core if not hit[s]]))
B = [s for s in core if not (hit[s] & {"SKILLMAP", "agents", "CLAUDE.md"})]
print("B candidatas =", len(B), B)
keep = veto | {s for s in core if nm(s, ch["CLAUDE.md"])}
print("C override =", sorted(keep), "-> candidatas =", len([s for s in core if s not in keep]))
CENSO
```

Saída em 2026-09-07: `core = 42`; `SKILLMAP 39/42`, `commands 9/42`,
`agents 8/42`, `CLAUDE.md 1/42`; `A = 0`; `B = 2`; `C = 37`.

**Perna 1 — guarda de denominador. O número de cobertura é do Owner
(OQ-2), porque o valor do round 1 devolve RECUSA para tudo.**

A perna existe por uma razão que sobrevive intacta: sem ela a regra fica
verde com denominador zero, que é exatamente o que o instrumento de
referência faz hoje — `ceo-boot.py:708` devolve `green` quando o total é
zero. A grandeza de SPAWNS também sobrevive: `min_observed_spawns = 100`
contra **114 spawns medidos em 2026-09-07** ⇒ satisfeita.

A grandeza de COBERTURA, não. O round 1 escreveu
`min_window_coverage_days = 90`; a família de auditoria por projeto cobre
de `2026-08-21T12:13:43Z` a `2026-09-07T03:27:15Z`, isto é **16,63 dias**
(medido; comando no §4, que resolve o diretório de estado pelo resolvedor
por projeto em vez de citar um caminho de máquina). `16,63 < 90` ⇒ pela
tabela do §2.2 a saída é
`RECUSA` **para toda skill**, e só deixaria de ser em **2026-11-19**, a
data em que a família completa 90 dias de cobertura. Isso reintroduz por
dentro o bloqueio por calendário que o §0 declara caído e colide com o
`external_wait: none` ratificado pelo Owner e com `eta_calendar:
"mesmo-dia a D+1"`.

O dano maior é sobre os CONTROLES, e é da classe canônica «o controle
reproduz a APARÊNCIA e não o MECANISMO»: com `RECUSA` dominante a AC-0.2
não pode ficar verde na propriedade que enuncia, a AC-0.3 fica verde
**pela guarda de denominador** mesmo com a proteção da perna 0 removida, e
a AC-0.4 deixa de discriminar o run com telemetria vazia do run normal. A
cura estrutural está no §5: as ACs de controle rodam com a perna 1
explicitamente NEUTRALIZADA (`--coverage-observed`), de modo que a única
variável entre a AC-0.2 e a AC-0.3 seja a perna 0, e a asserção passa a ser
sobre o MOTIVO da saída, não sobre o código de saída sozinho.

**As opções para a grandeza de cobertura, com a consequência de cada uma**
(a escolha é a OQ-2 do §10):

| # | `min_window_coverage_days` | efeito medido hoje | consequência |
|---|---|---|---|
| **i** | 90 (round 1) | RECUSA para as 42 | a W2 não abre antes de 2026-11-19; `external_wait: none` vira falso e volta a haver espera de calendário |
| **ii** | «cobertura declarada do histórico atribuível» — a família nasceu em 2026-08-21 com a W1 do PLAN-182 e não há histórico anterior atribuível a este projeto; o denominador passa a ser `min_observed_spawns` sozinho | a regra RESPONDE (114 ≥ 100) | `external_wait: none` sobrevive; o custo é que cada veredito carrega a incerteza de uma janela curta, e isso vai IMPRESSO nos inputs (AC-0.1) |
| **iii** | um número intermediário ratificado (por exemplo 14) | responde hoje (16,63 ≥ 14) | vira RECUSA se a família for rotacionada ou truncada — comportamento desejado de uma guarda, mas o número precisa de razão escrita |

**Perna 2 — telemetria.** Zero eventos `agent_spawn` carregando
`skill=<nome>` na janela declarada, lidos pelo leitor nomeado no §1.

### 2.2 As três saídas

| saída | quando | efeito |
|---|---|---|
| `MANTER` | qualquer perna de elegibilidade casa, ou há invocação na janela | nada acontece |
| `ARQUIVAR` | candidata E denominador suficiente E cadeia íntegra E zero invocações | entra na lista, que ainda passa pelo processo de proposta e soak |
| `RECUSA` | denominador insuficiente **OU cadeia de auditoria não íntegra** | a regra não responde; nenhuma skill é arquivada |

`RECUSA` é uma saída de primeira classe, não um erro. Uma regra que não
pode ficar vermelha por amostra insuficiente não é falsificável.

**Posição declarada sobre ledger não-íntegro.** O leitor que este plano
nomeia se auto-reporta hoje como não confiável:

```
python3 .claude/scripts/skill-health.py --include-rotated --since all --json
=> "chain_status": "NOT INTACT: status=tamper reason=hmac_mismatch — treat
   this report's telemetry as potentially tampered (advisory only; run
   audit-verify-chain.py for detail)"
```

Isso não é afirmação de adulteração: é o instrumento dizendo que não pode
garantir a própria evidência. Como o veredito `ARQUIVAR` desemboca em
edição canônica assinada pelo Owner, a regra **RECUSA por construção
enquanto `chain_status` não for íntegro** — a alternativa, arquivar sob
evidência declarada suspeita, inverteria a doutrina da casa. O estado da
cadeia entra nos INPUTS impressos pela regra (AC-0.1) e é medido antes de
qualquer ARQUIVAR (AC-2.0). Se o Owner preferir aceitar o risco por
escrito em vez de RECUSAR, é a OQ-3 do §10, com o efeito de cada opção
lá.

### 2.3 Consolidação (separada da regra)

Duas skills consolidam quando: (a) compartilham basename, o que quebra a
atribuição de telemetria — medidos hoje **2 pares**, ambos entre `frontend`
e `domains/fintech`, **nenhum em core**; ou (b) o Owner ratifica a
sobreposição a partir de uma lista GERADA por similaridade de corpus.
Nenhuma das figuras de consolidação é digitada: todas são geradas na
execução (§4.6 mostra por quê).

### 2.4 Destino do arquivo morto

O destino fica **fora de `.claude/skills/`**. Motivo medido: os dois
derivadores de contagem varrem recursivamente
(`verify-counts.sh` usa `find .claude/skills -name SKILL.md`;
`check-claude-md-claims.py` usa o glob `.claude/skills/**/SKILL.md`), então
uma pasta de arquivo criada sob `.claude/skills/` continua contando e o
`166` permanece `166`. Se o destino ficar dentro por outra razão, a
exclusão nos DOIS derivadores viaja no mesmo patch — e o derivador de
contagem total passaria a discordar da soma por tier, porque os matchers
por tier são de um nível só.

## 3. Guard-rails

- Poda passa pelo processo de proposta e soak existente — o gate de skills
  não é contornado, é usado a favor.
- Superfícies de contagem mudam por derivação mais `verify-counts`, nunca à
  mão (a classe de drift de contagem em documento é recidiva).
- **Amostra insuficiente é razão explícita de RECUSA**, alinhada com a
  regra seguinte.
- Telemetria continua ligada depois da poda: se o unknown-ratio não cair
  com a descoberta (passo 1), o problema é o INJETOR, não o catálogo —
  reavaliar antes do passo 2.
- **Custo de cerimônia:** o oráculo de canonicidade responde `1` para
  `.claude/skills/core/*/SKILL.md`, `.claude/skills/frontend/*/SKILL.md` e
  `.claude/skills/domains/**/SKILL.md`. Ou seja, **toda skill movida é uma
  edição canônica** e pede assinatura do Owner.
- **O teto de 8 caminhos morde TRÊS ondas, não só o P3.** Medido em
  2026-09-07: (a) o P3 move 116 skills, cada uma canônica; (b) a W4 tem de
  tocar **13 documentos** que publicam a contagem de skills — 10 vigiados
  pelo verificador e 3 que carregam o literal sem estar vigiados (censo no
  §4.7); (c) a W2, se rodar ANTES da W4, arrasta esses mesmos documentos
  para dentro do patch de arquivamento, somando dois regimes de cerimônia
  num pacote só. A decomposição do §5 existe por causa das três, e a
  inversão de ordem do §1 existe para tirar (c) do caminho.

## 4. Medição de 2026-09-06 — o que sobrevive, o que foi refutado

Todos os números abaixo foram lidos em disco. **As figuras deste plano são
MÓVEIS: a família de auditoria cresce a cada sessão, então cada número leva
a data em que foi lido e o comando que o produz.** A leitura do round 1
(2026-09-06) e a desta revisão (2026-09-07) diferem em magnitude e
concordam em direção; onde as duas aparecem, as duas estão datadas.

Janela — família de auditoria por projeto, medida em **2026-09-07**:
**10 arquivos, 144.532 eventos, de `2026-08-21T12:13:43Z` a
`2026-09-07T03:27:15Z` — 16,63 dias de cobertura.** A família nasceu com a
onda W1 do PLAN-182 (separação por projeto), então não há histórico
anterior atribuível a este projeto. Comando — ele resolve o diretório de
estado pelo resolvedor por projeto, então **roda a partir do checkout do
projeto, nunca de uma árvore de trabalho auxiliar**: uma sombra resolve
para o slug DELA e não vê arquivo nenhum da família (verificado):

```
python3 - <<'JANELA'
import os, glob, json, subprocess, datetime as dt
d = subprocess.run(["python3", ".claude/hooks/_lib/runtime_paths.py", "--state-dir"],
                   capture_output=True, text=True).stdout.strip()
files = sorted(glob.glob(os.path.join(d, "audit-log*.jsonl")))
tot = 0; first = last = None; spawns = 0
for f in files:
    with open(f, errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            tot += 1
            try:
                ev = json.loads(line)
            except Exception:
                continue
            ts = ev.get("ts") or ev.get("timestamp")
            if isinstance(ts, str) and ts[:4].isdigit():
                first = ts if first is None or ts < first else first
                last = ts if last is None or ts > last else last
            spawns += ev.get("action") == "agent_spawn"
a = dt.datetime.fromisoformat(first.replace("Z", "+00:00"))
b = dt.datetime.fromisoformat(last.replace("Z", "+00:00"))
print(len(files), "arquivos", tot, "eventos", spawns, "spawns")
print(first, "->", last, "= %.2f dias" % ((b - a).total_seconds() / 86400.0))
JANELA
```

**O estado da cadeia é um input, não um detalhe.** O mesmo leitor devolve
`chain_status: "NOT INTACT: status=tamper reason=hmac_mismatch"` — e é por
isso que o §2.2 declara a posição da regra sobre ledger não-íntegro. Nada
do que está medido abaixo deixa de ser verdade por causa disso; o que muda
é o que a regra pode DECIDIR a partir daí.

### 4.1 O bloqueio por calendário está REFUTADO

| grandeza | medido 2026-09-06 | medido 2026-09-07 |
|---|---|---|
| eventos `agent_spawn` | 109 | **114** |
| com skill nomeada | 81 | 86 |
| sem skill (`unknown`) | 28 | 28 |
| unknown-ratio | 0,257 | **0,246** |
| skills distintas invocadas | 11 | 11 |
| skills sem nenhuma invocação | — | 153 |

Leitor e invocação: `python3 .claude/scripts/skill-health.py
--include-rotated --since all --json`, chave `discovery_health`.

A versão anterior deste plano afirmava que não havia sinal a medir e que
o gate era aberto pelo calendário. Ela citava o `skill_unknown_ratio` do
`/ceo-boot`, que abre **apenas** o log vivo, sem descobrir os rotacionados,
e com janela de 24 horas. O plano pedia N ≥ 100 no passo 1 e N ≥ 30 na
re-medição do §4.3: **os dois já estão satisfeitos.** O `0,434` da semente
é da família pré-migração e está vencido.

**Consequência de sequenciamento:** o passo 1 deixa de ser bloqueado por
tempo de exposição e passa a ser bloqueado por INSTRUMENTAÇÃO, que é
trabalho que uma sessão executa. Por isso o `external_wait` do frontmatter
virou `none`, com o bloqueador real (o artefato da W1c do PLAN-171) nomeado
no §6 e preso apenas à onda W3.

### 4.2 A regra antiga arquiva este repositório

Aplicando a regra ANTIGA (duas pernas: zero invocações E ausente do SKILL
MAP) sobre este próprio repositório:

| grandeza | medido |
|---|---|
| skills core | 42 |
| core com zero invocações | 31 |
| core ausente do SKILL MAP | 3 |
| **a regra ARQUIVA** | **3: `agent-architect`, `ceo-orchestration`, `terse-mode`** |

As três são invocadas por assento ou por comando, e o canal por assento não
emite evento. `ceo-orchestration` é nomeada no Gate 2 do `CLAUDE.md`,
"invoque a skill `ceo-orchestration`", sob "antes de qualquer trabalho".

**A guarda de denominador não muda esse resultado, e é por isso que a
perna 0 é necessária.** Controle rodado numa árvore de trabalho nova, cujo
diretório de estado por projeto está vazio: **zero logs, zero eventos, zero
spawns — e a regra antiga arquiva exatamente as mesmas 3 skills.** Uma
derivação com denominador zero satisfaz trivialmente "a lista foi
DERIVADA", que era tudo o que o critério de aceite antigo exigia.

### 4.3 O piso de VETO passa raspando — e por acaso

O piso de VETO do ADR-052 são cinco arquétipos (Code Reviewer, Security
Engineer, Identity & Trust Architect, Incident Commander, Threat Detection
Engineer). Mapeados para skills pelos próprios arquivos de arquétipo em
`.claude/agents/`, eles carregam **4 skills distintas** — Threat Detection
e Security Engineer compartilham `security-and-auth`:

| skill do piso | invocações na janela | no SKILL MAP | a regra antiga arquiva? |
|---|---|---|---|
| `code-review-checklist` | 3 | sim | não |
| `security-and-auth` | 11 | sim | não |
| `identity-and-trust-architecture` | **0** | sim | não |
| `incident-management` | **0** | sim | não |

**Metade do piso de VETO tem zero invocações no histórico inteiro.** Elas
sobrevivem hoje só porque a perna do SKILL MAP as segura. Uma versão da
regra que largue essa perna — ou uma skill do piso que saia do mapa por
edição de texto — arquiva metade do piso de VETO sem que nada fique
vermelho. É por isso que o controle do §5 é AC de bloqueio, e não nota de
rodapé.

### 4.4 O índice de descoberta e o gap de idioma

**O índice não tem rota de nascimento.** O censo
`grep -rln skill-index-build` sobre `.claude/hooks/`, `.github/workflows/`
e `scripts/` devolve **1 arquivo**, e é uma docstring
(`.claude/hooks/_lib/frontmatter.py`) — nenhum hook, nenhum passo de
integração contínua, nenhuma rota de instalação. O arquivo de índice existe
hoje no diretório de estado por projeto porque foi construído à mão, uma
vez, numa máquina; ele mora fora do repositório e não é commitável, então
nasce morto em toda máquina nova e em todo adotante.

**Vivo, o recall depende do IDIOMA da consulta.** Medida anterior, N=8
pares inglês/português, alvo derivado à mão da tabela de roteamento:

| modo | recall entre os 5 primeiros (N=8) |
|---|---|
| similaridade de texto, consulta em **inglês** | 6/8 |
| busca estática (índice morto) | 4/8 |
| similaridade de texto, consulta em **português** | 2/8 |

O corpus das skills é em inglês; consultas em português colapsam num
atrator de idioma (uma skill com massa de vocabulário em português aparece
em primeiro lugar em 4 das 8 consultas). Não é efeito de tamanho de
arquivo: o ranqueador usa cosseno normalizado.

**Honestidade da amostra.** N=8, verdade-base manual, uma tentativa por
consulta. Basta para mostrar a DIREÇÃO e o atrator; não basta para fixar a
magnitude. Esses 2/8 são um LIMITE registrado, nunca uma melhoria.

**A premissa que o round 1 usou para PROIBIR a Fase 1 é falsa no HEAD, e
sai.** A versão anterior afirmava que «o `CLAUDE.md` deste projeto manda
operar em português» e convertia a tabela N=8 em «regressão medida». Censo
em 2026-09-07:

```
grep -rniE "portugu" CLAUDE.md PROTOCOL.md .claude/team.md \
     .claude/frontend-team.md .claude/skills/core/ceo-orchestration/SKILL.md
=> PROTOCOL.md:3  (ponteiro para o espelho PROTOCOL.pt-BR.md, declarando o
                   inglês como fonte de verdade)
```

Uma linha, e ela não é mandato. O `CLAUDE.md` tem **zero** ocorrências. O
que existe no repositório é: (a) o ponteiro do `PROTOCOL.md:3`; e (b) uma
família de espelhos pt-BR de documentos de produto (`README.pt-BR.md`,
`docs/GUIA-COMPLETO.pt-BR.md`, `PROTOCOL.pt-BR.md`), que faz do português
uma superfície de LEITURA de primeira classe. O idioma em que a sessão
opera vem da instrução de sessão do Owner, não de regra do repositório —
e instrução de sessão não é fato de disco que este plano possa citar.

**O que sobra depois de tirar a premissa falsa.** A tabela continua
mostrando um atrator de idioma real. O que ela NÃO mostra é a fração de
consultas efetivamente emitidas em português no caminho de produção, e
essa fração é **hoje não mensurável**: não há injetor, o recuperador é
opt-in e está desligado (§4.5), logo não existe corpus de consultas reais.
Portanto:

- «regressão medida» desce para **regressão sob a hipótese de consulta em
  português — hipótese não medida**;
- a proibição da Fase 1 perde essa base e ganha outra, explicitamente mais
  fraca e de governança: a Fase 1 não liga antes de a decisão (b) ser
  RATIFICADA (AC-1.4). Não é um número que segura a Fase 1; é uma decisão
  do Owner que ainda não foi tomada;
- a fração por idioma passa a ser mensurável só DEPOIS do injetor, e vira
  AC própria (AC-1.3b) em vez de premissa.

**E a sonda que produziu a tabela não é um controle.** Verificado no
arquivo: ela guarda o modo devolvido pelo recuperador em variáveis que
nunca usa, então não distingue o índice vivo do fallback; converte qualquer
exceção em falha silenciosa contada como erro de recall; chama o
recuperador por caminho relativo; e imprime o "4/8 medido antes" como texto
digitado, não como medida. **Corrigir a sonda é pré-requisito de qualquer
re-medição** — a classe "o instrumento exige o mesmo escrutínio adversarial
que o sujeito".

### 4.5 O consumidor que falta é o INJETOR, não o recuperador

Nenhum hook em `.claude/hooks/*.py` importa o roteador de recuperação; os
consumidores são bibliotecas e testes. O recuperador é chamado em produção
pelo script de recuperação de skills, opt-in e desligado por padrão. O que
não existe é o INJETOR: nada põe a sugestão no transcript de um spawn.
Logo o controle positivo do critério de aceite antigo ("spawn sem skill
produz sugestão no transcript") **não é escrevível hoje**.

O código do roteador delega esse wire-up a um plano de follow-up nomeado —
e **esse plano não existe** em `.claude/plans/`. A onda W0 fecha isso
declarando o injetor como escopo próprio, em vez de apontar para um
bloqueador inexistente.

### 4.6 Consolidação: três das quatro figuras não reproduzem

| figura no texto antigo | medido hoje |
|---|---|
| "lgpd ×4 → 1" | **1** skill com `lgpd` no nome em todo o catálogo. Em core há 4 skills no orbe de privacidade, e o plano nunca disse quais — a figura é subespecificada, não falsa |
| "accessibility duplicada" | **3** skills de acessibilidade: 2 em `frontend`, 1 em `domains`. **Nenhuma em core** — fora do escopo do passo que a carregava |
| "2 pares de basename duplicado" | **sobrevive**: `frontend-data-layer` e `frontend-patterns`, cada um em `frontend` e em `domains/fintech`. Também **nenhum em core** |
| "42 → ~25" | a regra escrita entrega **42 → 39** |

### 4.7 O critério de aceite antigo do passo 5 não podia ficar vermelho

`check-claude-md-claims.py` sai com código 0 HOJE, antes de qualquer
mudança: ele deriva de disco e mede DRIFT, com tolerância zero por padrão.
"gate verde depois da mudança" é satisfeito pelo estado ANTERIOR à mudança.
Pior: o casamento é por expressão regular sobre prosa, então uma claim
REESCRITA simplesmente deixa de casar e nunca mais é checada.

**Duas medições, e elas discordam — a superfície real é a UNIÃO.**

*(a) Censo pelo LITERAL.* `166 skills`, fora de `.claude/plans/`, sobre os
arquivos RASTREADOS: **10 arquivos** (`git grep -l "166 skills" -- '*.md'`).
Oito são documentos de produto — `CHANGELOG.md`, `CLAUDE.md`, `README.md`,
`README.pt-BR.md`, `docs/FAQ.md`, `docs/GUIA-COMPLETO.md`,
`docs/GUIA-COMPLETO.pt-BR.md`, `npm/README.md` — e dois são registros de
governança, históricos por natureza.

> **O censo é dependente de FERRAMENTA, e isso vai declarado.** O mesmo
> `grep -rln` sobre a árvore devolve **13** com o `grep` do sistema, porque
> inclui três espelhos GERADOS e ignorados pelo controle de versão
> (`dist/ceo-plugin/README.md` e dois sob `npm/.claude/`), confirmados com
> `git check-ignore`. O plano usa a leitura por arquivos RASTREADOS: os
> espelhos gerados são reconstruídos por `python3 scripts/build-plugin.py`
> e não são editados à mão. O `Check:` da AC-4.1 usa `git grep` exatamente
> por isso — `grep -rln` responde números diferentes em máquinas
> diferentes.

*(b) Censo pelo VIGIADO.* `bash .claude/scripts/local/verify-counts.sh
--json`, chave `rule_matches_by_doc`, prefixo `skills@`: **10 documentos**
— `CHANGELOG.md`, `INSTALL.md`, `README.md`, `README.pt-BR.md`,
`docs/ARCHITECTURE.md`, `docs/CTO-GUIDE.md`, `docs/FAQ.md`,
`docs/README.md`, `docs/WHAT-WE-ARE.md`, `npm/README.md`.

**A afirmação do round 1 sobre quem está fora da vigilância está REFUTADA.**
Ela dizia que os dois de fora eram `docs/GUIA-COMPLETO.pt-BR.md` e
`CHANGELOG.md`. Medido: `skills@CHANGELOG.md = 1` — o `CHANGELOG.md` **é**
vigiado. Os que carregam o número e **não** são vigiados para a métrica de
skills são **três**: `CLAUDE.md`, `docs/GUIA-COMPLETO.md` e
`docs/GUIA-COMPLETO.pt-BR.md`. E o censo pelo literal **subconta em cinco**:
`INSTALL.md`, `docs/ARCHITECTURE.md`, `docs/CTO-GUIDE.md`, `docs/README.md`
e `docs/WHAT-WE-ARE.md` publicam a contagem em outra forma («166-skill
inventory», célula de tabela «166») e são vigiados sem casar o literal.

**Superfície real da W4 = união de (a) e (b), menos os dois registros
históricos = 13 documentos.** É esse o número que faz a W4 estourar o teto
de 8 caminhos e exigir decomposição (§5). O critério novo asserta a
CONTAGEM de sítios casados por documento, não a cor do gate — o instrumento
para isso já existe e é exportado (`verify-counts.sh:789,795`, no `--json`
em `:1258`).

## 5. Waves

Decomposição sob o modelo de operação v2: no máximo 400 linhas alteradas ou
8 caminhos por pacote, uma rodada de mecanismo mais uma de confirmação, e
regra de parada pré-registrada por onda. Cada item declara seu `Check:`.

**Ordem executada: W0 → W1 → W4 → W2 → W3** (razão no §1).

**Regime de cerimônia por perna, com o oráculo ao lado.** Todos os
veredictos abaixo foram lidos em 2026-09-07 com
`python3 .claude/hooks/check_canonical_edit.py --is-canonical <caminho>`.
Onde o caminho ainda não existe, o veredito é do PREFIXO (o oráculo
responde por padrão de caminho, não por existência).

| perna | caminhos | oráculo | regime |
|---|---|---|---|
| W0a | `.claude/plans/PLAN-175/p2/*`, `.claude/plans/PLAN-175/p1/probe-retrieval-language-gap.py`, `.claude/plans/PLAN-175/evidence/*` | 0 | LIVRE |
| W0b | `.claude/hooks/_lib/rag_router.py` | **1** | CANÔNICO — assinatura |
| W1a | `.claude/plans/PLAN-175/evidence/*`, `.claude/plans/PLAN-175/decisions/*` | 0 | LIVRE |
| W1b | injetor sob `.claude/hooks/`, `.claude/settings.json`, rota do índice sob `.github/workflows/` | **1** | CANÔNICO — assinatura |
| W4a, W4b | os 13 documentos de produto do censo do §4.7 | 0 | LIVRE |
| W4c | `.claude/scripts/local/verify-counts.sh` | 0, **mas** é membro do manifesto de gates do ADR-192 | CERIMÔNIA |
| W2a, W2b | `SKILL.md` de origem e de destino, `.claude/adr/ADR-198-*.md` | **1** | CANÔNICO — assinatura |
| W3 | `scripts/tests/smoke-install.sh` | 0 | LIVRE |
| W3 (se tocar o installer) | `scripts/install.sh` | **1** | CANÔNICO — assinatura |

**O rótulo «pacote LIVRE» do round 1 estava errado para a W0 e a W1** — as
duas tocam caminho canônico. Por isso cada uma foi partida em perna livre
(`a`) e perna canônica (`b`), e o §6 foi corrigido no mesmo passo. **Quantas
assinaturas a primeira sessão gasta é a OQ-6 do §10**, não uma decisão deste
texto.

**Contrato de saída de `prune-rule.py`** (declarado aqui, implementado na
AC-0.1; é o que permite às ACs asserirem o MOTIVO e não só o código):

| código | significado |
|---|---|
| `0` | a asserção pedida vale |
| `2` | erro de uso — input ausente ou bandeira desconhecida |
| `3` | pelo menos uma skill protegida sairia `ARQUIVAR`; os nomes vão em `offenders` |
| `4` | `RECUSA` — a regra não pode responder (denominador ou cadeia) |

Com `--json` o programa imprime sempre `inputs`, `skills[]`, `exit_reason`
e `offenders[]`. `exit_reason` distingue `would_archive` de
`insufficient_sample` e de `chain_not_intact` — é essa distinção que
impede um controle de ficar verde pelo motivo errado.

### W0a — a regra e a sonda viram código executável (pacote LIVRE, 5 caminhos)

Cria: `.claude/plans/PLAN-175/p2/prune-rule.py`,
`.claude/plans/PLAN-175/p2/eligibility-census.py` e
`.claude/plans/PLAN-175/evidence/` — nenhum existe no HEAD (medido: a
árvore de `PLAN-175/` tem só `debate/` e `p1/`). Edita a sonda que já
existe em `p1/`.

Regra de parada: se o controle de não-autofagia (AC-0.2) não ficar verde em
duas rodadas, a regra muda de arquitetura em vez de ganhar mais uma
exceção. **Esta regra já disparou uma vez** (round 1: a regra arquivava
`ceo-orchestration`; round 2: a cura zerou as candidatas). A troca de
arquitetura está no §2.1 e a escolha é do Owner.

- [ ] **AC-0.1** [P0] a regra existe como programa, com as três pernas do §2.1 e as três saídas do §2.2, e imprime seus INPUTS: janela, número de eventos, leitor, `chain_status` da cadeia e a arquitetura de elegibilidade em vigor. Falta de qualquer um reprova.
  Check: `python3 .claude/plans/PLAN-175/p2/prune-rule.py --repo . --json | python3 -c "import json,sys;i=json.load(sys.stdin).get('inputs',{});f=sorted({'window','events','reader','chain_status','eligibility_architecture'}-set(i));print('inputs ausentes:',f);sys.exit(1 if f else 0)"`
- [ ] **AC-0.2** [P0] **CONTROLE DE NÃO-AUTOFAGIA.** Rodada sobre ESTE repositório, a regra devolve `MANTER` para `ceo-orchestration` e para as skills dos cinco arquétipos do piso de VETO do ADR-052 — hoje 4 skills distintas, porque dois arquétipos compartilham uma. O conjunto é derivado de `.claude/agents/`, nunca digitado. **A perna 1 roda NEUTRALIZADA (`--coverage-observed`)**, para que a única variável entre este AC e o próximo seja a perna 0.
  Check: `python3 .claude/plans/PLAN-175/p2/prune-rule.py --repo . --coverage-observed --assert-keep-veto-floor` sai `0`. Qualquer outro código reprova; `3` vem com o nome da skill desprotegida e `4` significa que a regra não respondeu.
- [ ] **AC-0.3** [P0] **CONTROLE POSITIVO DO MECANISMO.** A mesma invocação com a perna 0 desligada tem de reprovar **por autofagia**, não por amostra: `exit_reason == "would_archive"` e `ceo-orchestration` em `offenders`. Um vermelho por `insufficient_sample` ou `chain_not_intact` REPROVA este AC — foi exatamente assim que a guarda de 90 dias deixou o controle do round 1 verde pelo motivo errado.
  Check: `python3 .claude/plans/PLAN-175/p2/prune-rule.py --repo . --coverage-observed --assert-keep-veto-floor --disable-eligibility --json | python3 -c "import json,sys;d=json.load(sys.stdin);r=d.get('exit_reason');o=d.get('offenders',[]);print(r,o);sys.exit(0 if r=='would_archive' and 'ceo-orchestration' in o else 1)"`
- [ ] **AC-0.4** [P0] a guarda de denominador devolve `RECUSA`, nunca `ARQUIVAR`, quando a telemetria está vazia — o caso medido no §4.2 — **e DISCRIMINA do run normal**: com a perna 1 neutralizada, o run normal NÃO devolve `RECUSA` para todas. Se as duas pernas derem o mesmo conjunto de vereditos, o AC reprova.
  Check (as duas pernas têm de passar): `python3 .claude/plans/PLAN-175/p2/prune-rule.py --repo . --force-empty-telemetry --json | python3 -c "import json,sys;v={s['verdict'] for s in json.load(sys.stdin)['skills']};print(v);sys.exit(0 if v=={'RECUSA'} else 1)"` **e** `python3 .claude/plans/PLAN-175/p2/prune-rule.py --repo . --coverage-observed --json | python3 -c "import json,sys;v={s['verdict'] for s in json.load(sys.stdin)['skills']};print(v);sys.exit(0 if v!={'RECUSA'} else 1)"`
- [ ] **AC-0.5** [P0] a sonda de idioma passa a PARSEAR argv, a usar o modo devolvido pelo recuperador, a resolver o recuperador por caminho absoluto e a recusar rodar contra índice inválido; nenhum número aparece digitado na saída. **Medido no HEAD: a sonda tem zero parsing de argv** (`grep -cE 'argv|argparse|require-mode|--pairs'` devolve `0`) e sai `0` mesmo recebendo bandeira inexistente — as duas pernas abaixo estão VERMELHAS hoje.
  Check (as duas pernas): `python3 .claude/plans/PLAN-175/p1/probe-retrieval-language-gap.py --bandeira-inexistente; test $? -eq 2` **e** `python3 .claude/plans/PLAN-175/p1/probe-retrieval-language-gap.py --require-mode tfidf --json | python3 -c "import json,sys;d=json.load(sys.stdin);print(d.get('mode'),d.get('numbers_source'));sys.exit(0 if d.get('mode')=='tfidf' and d.get('numbers_source')=='measured' else 1)"`
- [ ] **AC-0.7** o censo de elegibilidade do §2.1 é GERADO, não digitado, e a tabela do plano reproduz o gerado.
  Check: `python3 .claude/plans/PLAN-175/p2/eligibility-census.py --json | python3 -c "import json,sys;d=json.load(sys.stdin);c=d['candidates_by_architecture'];print(c);sys.exit(0 if c['A']==0 and c['B']==2 and c['C']==37 else 1)"` — vermelho quando o catálogo ou os canais mudarem, que é quando a tabela do §2.1 precisa ser regerada.

### W0b — a referência morta sai do roteador (pacote CANÔNICO, 1 caminho, exige assinatura)

- [ ] **AC-0.6** [P0] o injetor de sugestão é declarado ESCOPO DESTE PLANO (onda W1b), e a referência ao plano de follow-up inexistente sai do código do roteador. O caminho é `.claude/hooks/_lib/rag_router.py`, que o oráculo responde **canônico (1)** — por isso esta perna é assinada, e não «livre» como o round 1 dizia.
  Check: `grep -rn "PLAN-097-FOLLOWUP-rag-router-wireup" .claude/hooks/ .claude/scripts/; test $? -eq 1` — hoje devolve `_lib/rag_router.py:32` com `$? -eq 0`, isto é, VERMELHO antes da onda.

### W1a — medição publicada e decisão de idioma (pacote LIVRE, 3 caminhos)

Cria `.claude/plans/PLAN-175/evidence/` e
`.claude/plans/PLAN-175/decisions/` — nenhum dos dois existe no HEAD
(medido: `grep -n "decisao-b" .claude/plans/PLAN-175/decisions/` devolve
«No such file or directory», `rc=2`).

Regra de parada: se a re-medição com N ≥ 30 não reproduzir a DIREÇÃO da
tabela do §4.4, a decisão (b) volta para o Owner com a evidência nova, e a
Fase 1 não liga.

- [ ] **AC-1.1** [P0] o baseline do unknown-ratio é PUBLICADO como arquivo GERADO, carregando os inputs: invocação literal do leitor, janela, `chain_status`, o bloco `discovery_health` e a data de geração.
  Check: `python3 -c "import json,sys;d=json.load(open('.claude/plans/PLAN-175/evidence/unknown-ratio-baseline-2026-09-07.json'));f=[k for k in ('reader_invocation','window','chain_status','discovery_health','generated_at') if k not in d];print('faltam:',f);sys.exit(1 if f else 0)"` — vermelho hoje: o arquivo não existe, e esta onda o cria.
- [ ] **AC-1.2** a condição de ativação da Fase 2 é estrita e casa com o instrumento de referência: nenhuma forma maior-ou-igual sobrevive no plano, **em nenhuma das quatro grafias** (com e sem espaço, com vírgula e com ponto decimal).
  Check: `grep -nE "(≥|>=) ?0[.,]10|igual ou acima de 0[.,]10" .claude/plans/PLAN-175-skills-pruning-discovery.md | grep -v "Check:"` não devolve nada (o filtro existe porque a própria linha de verificação cita o padrão proibido), e `grep -n "ratio > 0.10" .claude/scripts/ceo-boot.py` devolve a linha do instrumento
- [ ] **AC-1.3** [P0] re-medição do gap de idioma com N ≥ 30 pares, usando a sonda corrigida da AC-0.5, com a verdade-base gerada e revisada. A asserção é sobre a SAÍDA, não sobre bandeiras que a sonda antiga ignorava.
  Check: `python3 .claude/plans/PLAN-175/p1/probe-retrieval-language-gap.py --pairs 30 --require-mode tfidf --json | python3 -c "import json,sys;d=json.load(sys.stdin);print(d.get('pairs'),d.get('mode'));sys.exit(0 if d.get('pairs',0)>=30 and d.get('mode')=='tfidf' else 1)"`
- [ ] **AC-1.3b** a FRAÇÃO de consultas por idioma no caminho de produção é publicada, ou o plano registra por escrito que ela é não-mensurável e por quê. Hoje é não-mensurável: não há injetor e o recuperador é opt-in e desligado (§4.5), logo não existe corpus de consultas reais. Este AC só pode virar medição depois da W1b.
  Check: `python3 -c "import json,sys;d=json.load(open('.claude/plans/PLAN-175/evidence/query-language-fraction.json'));print(d.get('status'),d.get('reason'));sys.exit(0 if d.get('status') in ('measured','not-measurable') and d.get('reason') else 1)"` — vermelho hoje: o arquivo não existe.
- [ ] **AC-1.4** [P0] a decisão (b) — indexar português, normalizar a consulta, ou declarar a limitação e manter a busca estática como caminho primário — é RATIFICADA pelo Owner antes de a Fase 1 ligar. O registro fica em `.claude/plans/PLAN-175/decisions/decisao-b-idioma.md`, criado por esta onda, e carrega opção ratificada, dono, conjunto fechado de opções e critério de morte.
  Check: `grep -rn "decisao-b" .claude/plans/PLAN-175/decisions/` devolve o registro **e** `python3 -c "import sys;x=open('.claude/plans/PLAN-175/decisions/decisao-b-idioma.md').read();f=[k for k in ('opcao_ratificada:','dono:','conjunto_fechado:','criterio_de_morte:','data:') if k not in x];print('faltam:',f);sys.exit(1 if f else 0)"` — as duas pernas vermelhas hoje (`rc=2`, diretório inexistente).
- [ ] **AC-1.7** a Fase 1 **FECHA no baseline**. O `external_wait: none` foi ratificado pelo Owner em 2026-09-06, e um plano que declara ausência de espera externa não pode carregar uma espera de calendário de 30 dias no corpo. A re-medição posterior e a decisão de ligar ou não a Fase 2 saem daqui e viram follow-up nomeado (`PLAN-175-FOLLOWUP-<slug>`, PLAN-SCHEMA §1.4), criado nesta onda com o gatilho escrito.
  Check (as duas pernas): `test -f .claude/plans/PLAN-175-FOLLOWUP-fase2-remedicao.md && grep -qE "^gatilho:" .claude/plans/PLAN-175-FOLLOWUP-fase2-remedicao.md` — vermelho hoje, porque o follow-up ainda não existe **e** `grep -n "A Fase 1 não fecha no baseline" .claude/plans/PLAN-175-skills-pruning-discovery.md | grep -v "Check:"; test $? -eq 1` — a frase do round 1 que AFIRMAVA a espera saiu nesta revisão, e o `Check:` fica vermelho se ela voltar. O filtro por `Check:` existe pela mesma razão da AC-1.2: a linha de verificação cita o padrão que proíbe. A asserção é sobre a frase que AFIRMA a espera, não sobre qualquer menção a calendário — o §6 cita a espera removida por razões de registro, e citar não é afirmar.

### W1b — o injetor e a rota de nascimento do índice (pacote CANÔNICO, exige assinatura)

- [ ] **AC-1.5** [P0] o índice ganha rota de nascimento e gatilho de reconstrução; depois de qualquer poda ele é invalidado, para a sugestão não apontar para skill arquivada. **Medido no HEAD:** o único casamento de `skill-index-build` é uma docstring em `.claude/hooks/_lib/frontmatter.py` — nenhum hook, nenhum passo de integração contínua, nenhuma rota de instalação.
  Check: `test "$(grep -rln "skill-index-build" .claude/hooks/ .github/workflows/ scripts/ | grep -v "_lib/frontmatter.py" | wc -l)" -ge 1` — hoje devolve `0`, isto é, vermelho.
- [ ] **AC-1.6** [P0] o positive control da Fase 1 é escrevível: um spawn sem skill produz a sugestão no transcript, pelo injetor da AC-0.6. **O `Check:` do round 1 era um FALSO-VERDE medido:** `pytest -k injector` casa hoje dois testes alheios (`test_benchmark_judge.py::TestStructuredOutputsOptIn::test_default_path_injector_called_without_response_format` e o par `test_optin_path_threads_response_format_to_injector`), então saía `0` antes de qualquer trabalho. O `Check:` novo nomeia o arquivo de teste que esta onda cria.
  Check: `python3 -m pytest .claude/scripts/tests/test_skill_suggestion_injector.py -q` — vermelho hoje (o arquivo não existe; `pytest` sai `4`).

### W4a — contagem derivada, primeira leva (pacote LIVRE, 7 caminhos)

Regra de parada: se o censo do literal encontrar superfície nova a cada
rodada, o problema é o censo, não a lista — trocar a arquitetura do censo.

Caminhos: `README.md`, `README.pt-BR.md`, `npm/README.md`, `docs/README.md`,
`docs/FAQ.md`, `docs/ARCHITECTURE.md`, `docs/CTO-GUIDE.md`.

- [ ] **AC-4.1** [P0] o censo das superfícies é GERADO no patch e é a UNIÃO de duas medições que discordam — o literal e a lista vigiada (§4.7). O AC asserta os três números e o conjunto NOMEADO que está fora da vigilância.
  Check: `bash .claude/scripts/local/verify-counts.sh --json | python3 -c "import json,subprocess,sys;d=json.load(sys.stdin);vig={k.split('@',1)[1] for k in d['rule_matches_by_doc'] if k.startswith('skills@')};lit={p for p in subprocess.run(['git','grep','-l','166 skills','--','*.md'],capture_output=True,text=True).stdout.split() if not p.startswith('.claude/plans/')};hist={'.claude/governance/pair-rail-verdict-v1.2.0.md','.claude/proposals/SP-047-prisma-patterns-saas-platforms-move-2026-07-13.md'};prod=sorted((vig|lit)-hist);fora=sorted(lit-vig-hist);print(len(vig),len(lit),len(prod),fora);sys.exit(0 if len(prod)==13 and fora==['CLAUDE.md','docs/GUIA-COMPLETO.md','docs/GUIA-COMPLETO.pt-BR.md'] else 1)"` — verde hoje sobre `10 10 13`; fica vermelho no instante em que uma superfície entra ou sai sem o censo ser regerado.
- [ ] **AC-4.2** [P0] o critério asserta a CONTAGEM de sítios CASADOS pelo verificador, não a cor do gate — o instrumento já existe (`verify-counts.sh:789,795`, exportado no `--json` em `:1258`). Uma claim REESCRITA que deixa de casar tem de ficar visível como QUEDA de contagem.
  Check: `bash .claude/scripts/local/verify-counts.sh --json | python3 -c "import json,sys;d=json.load(sys.stdin);n=sum(v for k,v in d['rule_matches_by_doc'].items() if k.startswith('skills@'));base=json.load(open('.claude/plans/PLAN-175/evidence/rule-matches-baseline.json'))['skills_matches'];print(base,'->',n);sys.exit(0 if n>=base else 1)"` — vermelho quando um documento reescrito deixa de casar.

### W4b — contagem derivada, segunda leva (pacote LIVRE, 6 caminhos)

Caminhos: `INSTALL.md`, `docs/WHAT-WE-ARE.md`, `CHANGELOG.md`,
`docs/GUIA-COMPLETO.md`, `docs/GUIA-COMPLETO.pt-BR.md` e `CLAUDE.md`.

> **`CLAUDE.md` entra no CLOSEOUT da sessão que rodar esta onda**, nunca no
> meio dela: o §0 do próprio `CLAUDE.md` declara os arquivos do Gate 1
> cache-stable e proíbe edição no meio da sessão. `CHANGELOG.md` guarda por
> natureza a contagem de então; o tratamento dele — reescrever para a forma
> derivada ou ensinar o verificador a lê-lo como histórico — sai na W4c.

- [ ] **AC-4.3** [P0] as superfícies passam a dizer "N core + M frontend + pacotes opcionais", derivado, e nenhum documento de PRODUTO carrega mais o literal fixo.
  Check: `test "$(git grep -l "166 skills" -- '*.md' | grep -v '^\.claude/' | wc -l)" -eq 0` — hoje devolve `8`, isto é, vermelho. E `python3 .claude/scripts/check-claude-md-claims.py` continua saindo `0`.

### W4c — a lista vigiada cresce (CERIMÔNIA do ADR-192, 1 caminho)

`.claude/scripts/local/verify-counts.sh` responde `0` ao oráculo de
canonicidade, mas é membro do manifesto de gates do ADR-192
(`.claude/governance/gate-scripts-manifest.txt`, primeira linha), então
editá-lo passa por cerimônia mesmo com o oráculo «livre».

- [ ] **AC-4.5** [P0] os três documentos que publicam a contagem sem estar vigiados — `CLAUDE.md`, `docs/GUIA-COMPLETO.md`, `docs/GUIA-COMPLETO.pt-BR.md` — entram na lista vigiada, e o manifesto de gates é rebumpado no mesmo patch.
  Check: `bash .claude/scripts/local/verify-counts.sh --json | python3 -c "import json,sys;d=json.load(sys.stdin);vig={k.split('@',1)[1] for k in d['rule_matches_by_doc'] if k.startswith('skills@')};f=sorted({'CLAUDE.md','docs/GUIA-COMPLETO.md','docs/GUIA-COMPLETO.pt-BR.md'}-vig);print('ainda fora:',f);sys.exit(1 if f else 0)"` — hoje os três estão fora, isto é, vermelho.

### W2a — o primeiro arquivamento (pacote CANÔNICO, 3 caminhos, exige assinatura)

Regra de parada: nenhuma skill é movida antes de a AC-0.2 estar verde. Se a
lista derivada contiver qualquer skill do piso de VETO, a onda para. **Esta
onda não abre antes de a W4 ter landado** — o verificador é bidirecional e
o arquivamento derruba os documentos que publicam o número.

Caminhos: o `SKILL.md` de origem, o arquivo de destino fora de
`.claude/skills/`, e `.claude/adr/ADR-198-<slug>.md`.

- [ ] **AC-2.0** [P0] o estado da cadeia de auditoria é MEDIDO e registrado antes de qualquer `ARQUIVAR`, e a regra respeita a posição declarada no §2.2. Hoje o leitor devolve `NOT INTACT: status=tamper reason=hmac_mismatch`.
  Check: `python3 .claude/plans/PLAN-175/p2/prune-rule.py --repo . --list-archive --json | python3 -c "import json,sys;d=json.load(sys.stdin);cs=d['inputs']['chain_status'];intact=cs.startswith('INTACT');n=len(d.get('archive',[]));print(cs[:40],n);sys.exit(0 if intact or n==0 else 1)"` — reprova se a lista de arquivamento vier NÃO vazia com a cadeia não íntegra.
- [ ] **AC-2.1** [P0] a lista de arquivamento é DERIVADA pela regra da W0, nunca curada à mão, vem com os inputs impressos, e **não é vazia** sob a arquitetura de elegibilidade ratificada na OQ-1. Uma lista vazia satisfaz «foi derivada» e não satisfaz este AC.
  Check: `python3 .claude/plans/PLAN-175/p2/prune-rule.py --repo . --list-archive --json | python3 -c "import json,sys;d=json.load(sys.stdin);a=d.get('archive',[]);print(len(a),a);sys.exit(0 if a else 1)"`
- [ ] **AC-2.2** [P0] o destino do arquivo morto fica fora de `.claude/skills/`, ou a exclusão viaja nos DOIS derivadores no mesmo patch; e o controle é NUMÉRICO: a contagem viva cai exatamente uma unidade em relação ao valor congelado antes da onda.
  Check: `bash .claude/scripts/local/verify-counts.sh --json | python3 -c "import json,sys;d=json.load(sys.stdin);live=d['live']['skills'];base=json.load(open('.claude/plans/PLAN-175/evidence/skills-count-before-W2a.json'))['skills'];print(base,'->',live);sys.exit(0 if live==base-1 and not d['violations'] else 1)"` — reprova quando nada foi arquivado (`live == base`) e quando algum documento discorda.
- [ ] **AC-2.3** restauração testada em ÁRVORE DESCARTÁVEL: o roteiro arquiva, lê a contagem, restaura e lê de novo, e asserta as TRÊS leituras — `N`, `N-1`, `N`. É isso que o distingue da AC-2.2: um roteiro que nunca arquivou reprova na leitura do meio.
  Check: `bash .claude/plans/PLAN-175/p2/restore-roundtrip.sh --json | python3 -c "import json,sys;a,b,c=json.load(sys.stdin)['counts'];print(a,b,c);sys.exit(0 if b==a-1 and c==a else 1)"` — a asserção é FEITA FORA do roteiro, sobre as três contagens que ele imprime, porque um teste cuja aprovação depende do código que ele testa não é teste. O roteiro cria e descarta a sua própria árvore de trabalho e nunca escreve na árvore viva.
- [ ] **AC-2.5** leitura adicional do anexo §7: o delta de tokens do catálogo antes e depois da poda é medido e publicado junto das superfícies derivadas. Só é mensurável DEPOIS do primeiro arquivamento, por isso mora aqui e não na W4.
  Check: `python3 .claude/scripts/context-budget.py --json | python3 -c "import json,sys;d=json.load(sys.stdin);a=d['catalog_tokens'];b=json.load(open('.claude/plans/PLAN-175/evidence/context-budget-before-W2a.json'))['catalog_tokens'];print(b,'->',a);sys.exit(0 if a<b else 1)"` — reprova se a poda não reduziu a superfície.

### W2b — consolidação (pacote CANÔNICO, exige assinatura)

- [ ] **AC-2.4** a consolidação usa o critério do §2.3 e as figuras são GERADAS no patch, não digitadas.
  Check: `python3 .claude/plans/PLAN-175/p2/prune-rule.py --repo . --consolidation-census --json | python3 -c "import json,sys;d=json.load(sys.stdin);p=d['duplicate_basename_pairs'];print(p);sys.exit(0 if isinstance(p,list) and all('core' not in x['tiers'] for x in p) else 1)"` — reprova se algum par duplicado passar a envolver `core`, que é a condição em que o §2.3 muda de resposta.

### W3 — domain-packs opcionais (BLOQUEADA pelo PLAN-171 W1c)

Regra de parada: sem o artefato de contrato da W1c em disco, com caminho e
data, esta onda não abre. Decomposição por domínio, um pacote por vez, para
caber no teto de 8 caminhos.

- [ ] **AC-3.0** [P0] o harness de instalação aprende a receber perfil. **Medido no HEAD: ele não parseia argumento nenhum** — `scripts/tests/smoke-install.sh:17` é `TARGET="${1:-}"`, `:25` faz `mkdir -p "$TARGET"` e `:34` chama o installer com `--profile core,frontend` FIXO; não há `case`, `shift` nem `getopts` no arquivo. Passar `--profile core,<domínio>` a ele cria um diretório chamado `--profile` e instala o perfil fixo. O harness é caminho LIVRE (oráculo `0`); o installer, não (oráculo `1`). **Quem entrega esta perna — esta onda ou o PLAN-171 — é a OQ-7 do §10.**
  Check: `D=$(mktemp -d); bash scripts/tests/smoke-install.sh "$D" --profile core,fintech >/dev/null 2>&1; test -d "$D/.claude/skills/domains/fintech"; R=$?; rm -rf "$D"; exit $R` — vermelho hoje, porque o harness ignora a bandeira e instala o perfil fixo `core,frontend`. **O alvo é sempre um diretório descartável passado como primeiro posicional**: rodar o harness com a bandeira na posição do alvo faria `mkdir -p "--profile"` dentro do repositório, e um `Check:` não escreve lixo na árvore viva.
- [ ] **AC-3.1** [P0] o artefato de contrato da W1c do PLAN-171 existe em disco, com caminho e data, e é citado aqui pelo caminho. A W1c sobreviveu ao corte de 2026-09-06 que cortou W3, W4 e W5 daquele plano (`.claude/plans/PLAN-171-governance-imports-provenance.md:164`, `:186`, `:210`).
  Check: `python3 -c "import re,os,sys;x=open('.claude/plans/PLAN-171-governance-imports-provenance.md').read();m=re.search(r'W1c[^\n]*\n(?:[^\n]*\n){0,40}?([.\w/-]+\.md)',x);p=m.group(1) if m else None;print(p, bool(p) and os.path.exists(p));sys.exit(0 if p and os.path.exists(p) else 1)"` — uma perna só, que casa o caminho citado E confere que ele existe em disco. Vermelho hoje: a expressão devolve `None`, porque a W1c é contract-only e não iniciada.
- [ ] **AC-3.2** [P0] perna A do teste-mestre: instalação de adotante SEM pacotes de domínio funciona.
  Check: `bash scripts/tests/smoke-install.sh` sai `0`. Aqui o código de saída É o veredito — o harness carrega as próprias asserções e sai diferente de zero quando uma delas reprova, ao contrário das invocações que só imprimem.
- [ ] **AC-3.3** [P0] perna B do teste-mestre, a que de fato regride: instalação com perfil `core` mais um domínio, DEPOIS da mudança — o caminho que hoje lê `.claude/skills/domains/<parte>` (`scripts/install.sh:1310` e `:1319`). O AC asserta que o diretório do domínio APARECE no alvo; a perna A e a perna B deixam de ser o mesmo comando.
  Check: `D=$(mktemp -d); bash scripts/install.sh "$D" --profile core,fintech >/dev/null 2>&1; test -d "$D/.claude/skills/domains/fintech"; R=$?; rm -rf "$D"; exit $R` — reprova se o caminho por domínio deixar de entregar.
- [ ] **AC-3.4** um ou dois domínios de referência permanecem na árvore, e a integração contínua fica verde sem os pacotes.
  Check: `bash .claude/scripts/validate-governance.sh` sai `0` **e** `test "$(ls -d .claude/skills/domains/*/ | wc -l)" -ge 1`

## 6. Bloqueadores e governança

- **Bloqueador único e real:** o artefato de contrato da onda W1c do
  PLAN-171 (fronteira de posse dos domain-packs). Ele prende **apenas a
  W3**. As ondas W0, W1 e W4 não dependem dele.
- **Uma só fonte de espera externa — agora verificável.** O frontmatter diz
  `external_wait: none`, **ratificado pelo Owner em 2026-09-06** (registro
  em `.claude/plans/PLAN-186/portfolio-review-S348/portfolio-review-S348.md`
  §8). O round 2 encontrou DOIS segundos lugares que afirmavam espera e os
  dois saíram nesta revisão: a AC-1.7, que pedia re-medição «aos 30 dias»
  (agora a Fase 1 fecha no baseline e a re-medição é follow-up nomeado), e
  a guarda `min_window_coverage_days = 90` do §2.1, que devolvia RECUSA até
  2026-11-19 (agora é a OQ-2, com as três opções e o efeito de cada uma). A
  afirmação «não há segundo lugar» deixa de ser promessa e passa a ter
  verificador — a segunda perna da AC-1.7.
- **Nenhum gate autoriza execução sozinho.** O rail entre modelos
  (rodadas r1 a r3 sobre a versão de S302) e o debate deste plano são
  ADVISORY. O que satisfaz a linha do runbook é o registro do debate em
  `.claude/plans/PLAN-175/debate/round-1/`; o que autoriza execução é o
  flip de status pelo Owner.
- **Custo de assinatura — a contagem do round 1 estava errada.** O round 1
  afirmava «só W0, W1 e W4 são pacotes integralmente livres». Medido com o
  oráculo em 2026-09-07, **a W0 e a W1 tocam caminho canônico**:
  `.claude/hooks/_lib/rag_router.py` responde `1` e é o alvo da AC-0.6; o
  injetor da AC-1.6 e a rota de índice da AC-1.5 vivem sob `.claude/hooks/`
  e `.github/workflows/`, que também respondem `1`. Por isso o §5 partiu as
  duas em perna livre e perna canônica. Continua verdadeiro que a W2 e a W3
  tocam canônico (todo `SKILL.md` responde `1`; `scripts/install.sh`
  também), e que a W4 apenas RODA `verify-counts.sh` — exceto a perna W4c,
  que o EDITA e por isso passa pela cerimônia do ADR-192. **Contagem
  mínima de assinaturas do plano inteiro: W0b, W1b, W4c, W2a, W2b e, se a
  W3 tocar o installer, mais uma.**
- **Runbook da primeira sessão:** W0a inteira, que é livre. A W0b consome
  assinatura, e **se ela entra na sessão 1 é a OQ-6 do §10**. Nada de poda
  na sessão 1 — por desenho.

## 7. Anexo S305 — reframe de engenharia de contexto (advisory)

A pesquisa da S305 reposiciona este plano: a poda não é só honestidade de
catálogo — a literatura de engenharia de contexto documenta ganho de
desempenho ao reduzir a superfície de contexto carregada por sessão.
Nenhum passo muda. Leitura ADICIONAL na **AC-2.5**: medir o delta de
tokens do catálogo antes e depois e publicar junto das superfícies
derivadas — transforma a poda em ganho medido, não só em contagem honesta.
A leitura mudou de onda porque só é mensurável DEPOIS do primeiro
arquivamento, e a inversão de ordem do §1 pôs a W4 antes da W2.

**Nota de escopo:** nenhum dos três críticos do round 1 examinou este
anexo. Ele permanece como estava; um round futuro que queira revisá-lo tem
de pedir foco nele.

## 8. Onde cada consenso do round 1 foi curado

### 8.1 Round 1

| item | onde |
|---|---|
| C1 janela de 90 dias inexistente | frontmatter `external_wait: none`; §4.1. **A guarda `min_window_coverage_days = 90` NÃO cura este item — ela o reintroduz**, e o round 2 mediu isso: 16,63 dias de cobertura contra 90 exigidos devolvem RECUSA para as 42 skills. A cura real é a OQ-2 do §10 |
| C2 a regra não entrega o número, e não tem guarda | §2 inteiro; §4.2; alvo `42 → ~25` removido do título e da regra |
| C3 leitor errado, duas seções discordando | §1 passo 1 (leitor e invocação nomeados); §4.1; AC-1.1 |
| C4 o arquivo morto não sai de nenhuma contagem | §2.4; AC-2.2 |
| C5 W1c inexistente e caminho de instalação | §1 passo 3; W3 inteira; AC-3.1 a AC-3.3 |
| C6 o critério do passo 5 não pode ficar vermelho | §4.7; AC-4.1 e AC-4.2 |
| C7 decisão de idioma sem dono nem critério de morte | §4.4; AC-1.4 |
| C8 índice sem nascimento nem invalidação | §4.4; AC-1.5 |
| C9 sem decomposição em ondas | §5 inteiro; regra de parada por onda |
| K1 a regra arquiva `ceo-orchestration` | perna 0 do §2.1; §4.2; AC-0.2 e AC-0.3 |
| K2 bloqueio por calendário refutado | §0 item 1; §4.1 |
| K3 fronteira 0,10 com dois donos | §1 passo 1; AC-1.2 |
| K4 controle positivo inescrevível | §4.5; AC-0.6 e AC-1.6 |
| K5 a sonda não é um controle | §4.4 último parágrafo; AC-0.5 |
| K6 orçamento sem unidade, fonte nem spread | frontmatter; §9 |
| K7 figuras de consolidação e escopo de accessibility | §2.3; §4.6 |
| K8 denominador 164 versus 166 | bloco da semente; §4.6 |
| K9 ambiguidades de governança | §0 último parágrafo; §6 |

### 8.2 Round 2

Três críticos, três `ADJUST` (3, 5 e 5 bloqueantes), veredito de round
`ESCALATE-TO-OWNER`. Cada linha abaixo foi re-verificada em disco nesta
revisão antes de ser curada.

| item | o que a evidência mostrava | onde foi curado |
|---|---|---|
| C1 o `Check:` da AC-3.3 é inerte | `smoke-install.sh` não tem `case`, `shift` nem `getopts`; `:34` fixa `--profile core,frontend` | AC-3.0 nova (ensina o harness, caminho livre) e AC-3.3 reescrita para o installer real, assertando o diretório do domínio no alvo |
| C2 `min_window_coverage_days = 90` devolve RECUSA para tudo | cobertura medida 16,63 dias; 90 só em 2026-11-19 | §2.1 perna 1 com as três opções medidas; OQ-2; controles com a perna 1 neutralizada |
| C3 o `Check:` da AC-1.4 nunca fica verde | `decisions/` não existe (`rc=2`) e `grep -n` sem `-r` sobre diretório não casa | AC-1.4 com `grep -rn`, caminho do registro nomeado, onda que o cria e cinco campos obrigatórios |
| C4 nove `Check:` imprimem sem asserir | AC-0.1, 1.1, 1.3, 1.6, 2.1, 2.2, 2.3, 4.1, 4.4 saíam `0` sempre que a ferramenta funcionasse | todas reescritas com metade vermelha nomeada; AC-2.3 ganhou discriminante próprio |
| C5 `external_wait` ratificado no mundo, PENDENTE no texto | linha do Progress log dizia «PENDENTE» depois da ratificação | linha emendada; §6 reescrito |
| K-A a perna 0 zera as candidatas | união dos quatro canais nomeia 42 de 42 | §2.1 perna 0 trocada de ARQUITETURA, com A/B/C/D medidas; OQ-1 |
| K-B a AC-0.6 edita caminho canônico numa onda «livre» | oráculo responde `1` para `rag_router.py` | W0 partida em W0a livre e W0b canônica; §6 corrigido |
| K-C a premissa de idioma é falsa no HEAD | `grep -rniE "portugu"` devolve uma linha, `PROTOCOL.md:3`, e não é mandato | §4.4 reescrito; a proibição da Fase 1 troca de base; AC-1.3b nova |
| K-D `verify-counts` é bidirecional | `:25-27` e `:31` (`exact (166)`) | ordem invertida no §1 e no §5: W4 antes de W2 |
| K-E a cadeia é reportada NOT INTACT | `chain_status: NOT INTACT: status=tamper reason=hmac_mismatch` | §2.2 declara RECUSA por cadeia não íntegra; AC-2.0 nova; OQ-3 |
| K-F a sonda não parseia argv | `grep -cE 'argv\|argparse\|require-mode\|--pairs'` devolve `0`; a sonda sai `0` com bandeira inexistente | AC-0.5 com duas pernas, ambas vermelhas hoje |
| K-G o orçamento é refutado pelo próprio instrumento | 320–960 turnos orçados contra 50.126 medidos na janela; `assento` é Fable 5.1, não Opus 5 | §9 reescrito: regime declarado, conversão declarada, critério de morte por custo, OQ-8 |
| K-H a AC-4.2 asserta a cor do gate | `rule_matches_by_doc` existe em `:789,795` e no `--json` em `:1258` | AC-4.2 asserta a contagem de casamentos contra baseline congelado |
| K-I o teto de 8 caminhos morde a W2 | 1 `SKILL.md` + 8 documentos + o verificador | §3 corrigido; W2 partida em W2a/W2b e W4 em W4a/W4b/W4c |
| K-J a AC-1.7 é espera de 30 dias | contra `external_wait: none` ratificado | Fase 1 fecha no baseline; re-medição vira follow-up nomeado |
| F5, F9 figuras móveis sem âncora | assento andou de 655,23 para 664,00; eventos de 141.988 para 144.532 | toda figura leva data e comando; §4 abre dizendo que as figuras são móveis |
| F8 espalhamento declarado e não propagado | 51,7% sobre a média em 41 amostras, e a faixa usa o ponto | §9 diz QUAL termo carrega o espalhamento |
| R-QA9 plano L3 sem ADR nomeado | nenhum `ADR-<NNN>` novo em nenhuma onda | `ADR-198` nomeado nos caminhos da W2a |

**Achados NOVOS desta cura, que nenhum crítico do round 2 viu.** Os dois
saíram de reproduzir as evidências em vez de aceitá-las:

1. **O `Check:` da AC-1.6 era um falso-verde**, não uma invocação nua:
   `pytest .claude/scripts/tests/ -q -k injector` sai `0` HOJE porque casa
   dois testes de `test_benchmark_judge.py` sobre um «injector» de
   `response_format`, sem relação com o injetor de sugestão. O `Check:`
   novo nomeia o arquivo de teste que a W1b cria.
2. **O censo do §4.7 media a coisa errada por dois lados.** A afirmação
   «`CHANGELOG.md` está fora da lista vigiada» é falsa (`skills@CHANGELOG.md
   = 1`); os três de fora são `CLAUDE.md` e os dois `GUIA-COMPLETO`. E o
   censo pelo literal SUBCONTA em cinco documentos que publicam a contagem
   em outra forma e são vigiados. A superfície real da W4 é a UNIÃO: 13
   documentos, não 8. Além disso o censo por `grep -rln` é dependente de
   ferramenta — devolve 10 ou 13 conforme o `grep` honre ou não o controle
   de versão —, por isso o `Check:` da AC-4.1 usa `git grep`.

## 9. Como o orçamento foi derivado

Regra da casa: medida que sustenta decisão imprime seus inputs.

- **Piso por sessão.** O custo de re-pagar os gates de abertura foi medido
  em **97.292 tokens** na fronteira de uma compactação real, com controle
  independente em 97.097. **Esse piso não é constante:** a série fria tem
  espalhamento de 51,7% sobre a média em 41 amostras, então reportar só a
  média engana. Instrumento: `.claude/plans/PLAN-179/w0/gateboot_repay.py`.
- **`budget_tokens: 620-950k`** = 4 sessões × (piso ~97k + trabalho de 60k
  a 140k). O valor antigo, 150-300k em 2 a 4 sessões, dava 50-75k por
  sessão — **menos que o custo de entrar na sessão**.
  **Qual termo carrega o espalhamento:** o de PISO. A faixa publicada
  `620-950k` propaga incerteza pelo termo de TRABALHO (60k a 140k) e usa o
  piso no ponto (~97k). Propagar também o espalhamento do piso daria
  428k–1,15M. A faixa fica como está, e esta linha existe para que ninguém
  a leia como se fosse a incerteza total.
- **`budget_usd_estimate: 500-610`**, re-derivado em 2026-09-07 com
  `python3 .claude/scripts/ceo-cost.py --since 3d --source transcripts --format json`:

  | grandeza | medido 2026-09-07 |
  |---|---|
  | assento | US$ 664,00 em 1.844 turnos (US$ 0,3601/turno) |
  | subagente | US$ 8.755,02 em 50.126 turnos (US$ 0,1747/turno) |
  | total da janela | US$ 9.419,02 |

  Aritmética: 4 sessões × (US$ 664,00 ÷ 6 sessões da janela) = US$ 442,67 de
  assento; mais 8 rodadas × 40 a 120 turnos × US$ 0,1747 = US$ 55,90 a
  167,71. Soma: **US$ 498,57 a 610,38**.
- **O volume orçado é PREVISÃO DE REGIME, não extrapolação da janela — e a
  diferença vai declarada.** O mesmo instrumento, na mesma janela de 3
  dias, mede **50.126 turnos de subagente**, ou 8.354 por sessão; quatro
  sessões nesse ritmo dariam ~33.400 turnos e US$ 5.838. Os 320 a 960
  turnos orçados são **1,0% a 2,9%** disso. A razão é nomeada, não
  implícita: a janela mede o repositório INTEIRO — várias ondas de vários
  planos, incluindo noites autônomas com até 12 agentes em paralelo —,
  enquanto este plano roda sob o modelo de operação v2, com pacote de no
  máximo 8 caminhos, uma rodada de mecanismo mais uma de confirmação e teto
  absoluto de rodadas por classe. **Se o regime não valer, o orçamento não
  vale**, e é por isso que existe a linha seguinte.
- **Critério de morte por custo (pré-registrado).** Ao fim de cada sessão
  deste plano, o mesmo instrumento é rodado sobre a janela da sessão. Se o
  acumulado passar do teto do `budget_usd_estimate`, o plano PARA e volta
  ao Owner com a leitura ao lado — não continua «porque falta pouco». O
  teto exato e o critério são a OQ-8 do §10.
- **`tier_mix_estimate` — a conversão que faltava.** Mix medido em
  2026-09-07: Opus 5 com 92,44% do gasto, Fable 5.1 com 7,05%, Sonnet 5 com
  0,51%, Haiku 4.5 com 0,00%. **O papel de «assento» medido é um assento
  Fable 5.1, não Opus 5**: `by_role.assento` e `by_dimension.claude-fable-5-1`
  têm `cache_read_tokens` idêntico (994.878.343), o que identifica os dois.
  Fable 5.1 custa 10/50 por MTok e Opus 5 custa 5/25
  (`.claude/scripts/cost-table.yaml:70-73` e `:85-88`), isto é, **o assento
  medido é 2× mais caro por token que o assento que o mix planejado
  declara**. Logo os US$ 110,67 por sessão são preço de assento Fable; um
  assento Opus 5 no mesmo volume de tokens custaria cerca de metade disso,
  e a faixa publicada é conservadora nessa perna. O mix planejado continua:
  refutadores em Opus 5, documentação em Sonnet 5, nunca abaixo de Opus 5
  para o piso de VETO do ADR-052.
- **Nota de escopo.** Este orçamento é gasto de MODELO, pela convenção do
  repositório para `budget_usd_estimate`. Ele **não** inclui minutos de
  runner de integração contínua nem as rodadas de cerimônia das seis
  assinaturas contadas no §6.

## 10. Perguntas abertas — todas do Owner, nenhuma decidida aqui

O round 2 terminou em `ESCALATE-TO-OWNER`. Esta revisão curou o TEXTO de
tudo o que era coerência interna e deixou intactas as decisões que não têm
dono abaixo do Owner. Cada pergunta abaixo vem com o conjunto fechado de
opções e a consequência MEDIDA de cada uma — a escolha muda o escopo, não a
redação.

- **OQ-1 — arquitetura da perna 0 de elegibilidade.** Opções A, B, C e D da
  tabela do §2.1, com candidatas medidas 0, 2, 37 e «não mensurável hoje».
  Consequência de não escolher: `ARQUIVAR` continua inalcançável, a AC-2.1
  não pode ficar verde e a W2 não abre.
- **OQ-2 — `min_window_coverage_days`.** Opções i, ii e iii da tabela do
  §2.1, com efeito medido contra os 16,63 dias de cobertura.
  Consequência de manter 90: a W2 não abre antes de 2026-11-19 e o
  `external_wait: none` recém-ratificado passa a ser falso.
- **OQ-3 — decidir sobre ledger não íntegro.** O plano escreveu RECUSA por
  construção (§2.2). A alternativa é aceitar o risco por escrito. Hoje o
  leitor devolve `NOT INTACT: status=tamper reason=hmac_mismatch`, então a
  escolha decide se a W2 pode abrir de todo enquanto a cadeia não for
  reparada.
- **OQ-4 — decisão (b) de idioma.** Conjunto fechado (indexar português,
  normalizar a consulta, ou declarar a limitação e manter a busca estática
  como caminho primário), dono, critério de morte e o caminho do registro.
  A AC-1.4 já nomeia o caminho; falta o conteúdo. Depende da OQ-5.
- **OQ-5 — a premissa de uso em português.** Ela sai como «regressão
  medida» (§4.4) porque é falsa no HEAD. Resta escolher entre medir a
  fração real de consultas — só possível depois do injetor da W1b — ou
  manter a limitação como hipótese declarada e não medida. A escolha decide
  se a Fase 1 pode ligar antes da W1b.
- **OQ-6 — quantas assinaturas a primeira sessão gasta.** A W0b é canônica
  (`rag_router.py`, oráculo `1`) e a W1b também. Ou a sessão 1 gasta as
  duas, ou a AC-0.6 e a AC-1.5/AC-1.6 saem da sessão 1 e o runbook do §6
  encolhe para a W0a.
- **OQ-7 — quem entrega a perna de perfil do harness de instalação.** A
  AC-3.0 deste plano, ou o PLAN-171. O harness é caminho livre; o installer
  não. Consequência de não escolher: a AC-3.3 fica dependente de um
  instrumento sem dono.
- **OQ-8 — teto de gasto e critério de morte por custo.** O §9 pré-registra
  o mecanismo (medir ao fim de cada sessão e parar no teto) e deixa o
  NÚMERO em aberto, porque ele decide quando o plano para. A faixa
  re-derivada é US$ 500 a 610 sob o regime v2; o ritmo observado no
  repositório inteiro daria US$ 5.838 em quatro sessões.

## Progress log

- 2026-09-06 (S348, docs): **revisão do round 1 do debate absorvida.**
  Autorizada pelo Owner no item 4.15 do ledger de decisões da S347
  («Autorizar a revisão do plano»), com o item 4.10 fixando que o flip
  para `executing` só acontece depois desta revisão landar — por isso
  `status:` permanece `reviewed`. Os nove consensos (C1 a C9) e os nove
  achados de um crítico mantidos (K1 a K9) estão mapeados no §8. Medições
  desta revisão em §4, todas sobre a família de auditoria por projeto de
  10 arquivos e 141.988 eventos: o bloqueio por calendário está refutado
  (109 spawns, unknown-ratio 0,257), a regra antiga arquiva
  `ceo-orchestration` mesmo com denominador zero, e metade do piso de VETO
  do ADR-052 tem zero invocações no histórico inteiro.
- 2026-09-06 (S347, docs): **Decisão do Owner (item 4.15 de
  `PLAN-186/debate/owner-decisions-S347.md`, AskUserQuestion):**
  «Autorizar a revisão do plano (Recomendado)» — autoriza o pack docs com
  os 9 consensos do debate round-1. **Decisão derivada (item 4.10 do
  mesmo ledger):** o flip deste plano para `status: executing` só
  acontece DEPOIS da revisão landar — não volta a ser perguntado.
  `status:` permanece `reviewed` até lá.
- 2026-09-06 (S348, nota do CEO ao aplicar a revisão): o campo `external_wait` ratificado na S302f («gatilho: pós-GA v1.3.0; W1c do PLAN-171 (fronteira de ownership) primeiro») foi substituído por `none` nesta revisão, com a justificativa no corpo do plano (o bloqueio por calendário está refutado: a GA v1.3.0 saiu em 2026-08-17 e o denominador de telemetria já existe). **RATIFICADO pelo Owner em 2026-09-06 ~23:5x** — ver a entrada seguinte deste log, que traz a decisão e o registro. O flip para `executing` (decisão 4.10) e a rodada 2 do debate seguem separados e não são tocados por esta nota.
- 2026-09-06 (S348, ~23:5x): **Owner ratifica o `external_wait: none`.**
  Decisão Q6 do bloco B: «Sim, ratificar junto com o flip para
  executing (Recomendado)» — registrada em
  `.claude/plans/PLAN-186/portfolio-review-S348/portfolio-review-S348.md`
  §8. O `external_wait: none` do frontmatter fica RATIFICADO. O flip
  para `status: executing` e a rodada 2 do debate seguem como já
  fixado na decisão 4.10 — não mudam nesta nota; `status:` permanece
  `reviewed`.

- 2026-09-07 (S348, docs): **round 2 do debate absorvido.** Registro em
  `.claude/plans/PLAN-175/debate/round-2/consensus.md` — três críticos,
  três `ADJUST` (3, 5 e 5 bloqueantes), veredito de round
  `ESCALATE-TO-OWNER`. Os cinco consensos (C1 a C5) e os dez achados de um
  crítico mantidos (K-A a K-J) estão mapeados no §8.2, cada um com a
  evidência re-verificada em disco nesta revisão antes de ser curado. As
  três mudanças de modelo: a perna 0 de elegibilidade troca de ARQUITETURA
  porque a do round 1 zera as 42 candidatas (medido); a ordem das ondas
  inverte, com a contagem derivada (W4) precedendo a poda (W2), porque o
  verificador de contagens é bidirecional; e a W0, a W1, a W2 e a W4 ganham
  decomposição em pernas livres e canônicas, porque o rótulo «pacote LIVRE»
  do round 1 estava errado para a W0 e a W1. Duas coisas que nenhum crítico
  viu e que a re-verificação achou: o `Check:` da AC-1.6 era falso-verde
  (casava dois testes alheios) e o censo do §4.7 media 8 documentos onde a
  superfície real é 13. **Oito perguntas continuam abertas e são do Owner
  (§10); nenhuma foi decidida aqui.** `status:` permanece `reviewed`.

- **2026-09-07 (S348, Owner acordado; verbatim):** OQ-1 (arquitetura da elegibilidade, opções A/B/C/D da §2.1) — «D — não mensurável hoje» (contra a recomendação C). Consequência: sem rodada 3 e sem wave de poda até existir um instrumento que meça a elegibilidade; o plano permanece `reviewed`. A wave de instrumento é decisão seguinte do Owner.
