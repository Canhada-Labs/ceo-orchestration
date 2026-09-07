---
id: PLAN-175
title: Skills — descoberta antes de poda: regra de poda falsificável, unknown-ratio <0,10, domain-packs opt-in, contagem derivada
status: reviewed
reviewed_at: 2026-08-11
reviewed_by: "Owner - ratificacao S302f via OWNER-RATIFY-S302.sh: ratifico os 6 planos na v2.6 (rail Codex 7 rounds, r7 APPROVE, commits ab45f56..0c90174)"
created: 2026-08-11
last_revised: 2026-09-06
owner: CEO
depends_on: [PLAN-171]
budget_tokens: 620-950k
budget_sessions: 4
budget_usd_estimate: 490-610
tier_mix_estimate: "assento Opus 5; refutadores Opus 5; docs Sonnet 5 (piso VETO nunca abaixo de Opus, ADR-052)"
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

Esta é a versão revisada pelo round 1 do debate
(`.claude/plans/PLAN-175/debate/round-1/consensus.md`, três críticos, três
`ADJUST`, nove consensos e nove achados de um crítico mantidos). A revisão
foi autorizada pelo Owner em 2026-09-06 (item 4.15 do ledger de decisões).

Duas mudanças movem a agulha em sentidos opostos, e ambas são medidas:

1. **O bloqueio por CALENDÁRIO caiu.** A versão anterior afirmava que a
   re-medição precisava de tempo de exposição e tratava isso como espera
   externa. Isso foi medido com o leitor errado (uma janela de 24 horas).
   Com o leitor certo, o denominador que o plano pedia **já existe**.
2. **A regra de poda apertou.** Aplicada como estava escrita, ela arquiva
   a skill que o `CLAUDE.md` manda invocar em toda sessão. Ver §2.

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
   default de janela dele é 30 dias, não 90. Meta: unknown-ratio para
   abaixo de 0,10 (medido hoje: 0,257).
2. **Podar o core por telemetria — regra determinística com TRÊS saídas.**
   A regra é reescrita no §2. O alvo numérico `42 → ~25` **sai da regra**:
   a regra escrita entrega 3, não 17, e os `~25` vinham do passo de
   consolidação, que agora tem critério próprio (§2.3). ARQUIVAR, nunca
   deletar.
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

## 2. A regra de poda (reescrita — o coração desta revisão)

A regra anterior tinha duas pernas e uma saída. Aplicada sobre este próprio
repositório ela **arquiva `ceo-orchestration`** — a skill que o Gate 2 do
`CLAUDE.md` manda invocar antes de qualquer trabalho, em toda sessão. A
regra nova tem três pernas e três saídas, e vem com um controle que
FALSIFICA essa autofagia.

### 2.1 As três pernas

**Perna 0 — elegibilidade (nova).** Uma skill só é CANDIDATA se todos os
canais por que ela é alcançada emitem evento observável. Hoje isso exclui
da candidatura, mecanicamente, toda skill nomeada em: `CLAUDE.md` (Gates 1
e 2), `.claude/commands/*.md`, `.claude/agents/*.md`, ou no SKILL MAP
(`.claude/team.md` mais `.claude/frontend-team.md`).

*Por que:* o canal de invocação por assento e por comando não emite nada.
O censo de 141.988 eventos da família de auditoria não tem uma única ação
cujo nome contenha `skill` correspondente a uma invocação por assento. O
leitor conta apenas eventos `agent_spawn` carregando `skill=<nome>`. Para
essa classe inteira, a perna "0 invocações" não mede ausência de uso — mede
ausência de instrumento.

**Perna 1 — guarda de denominador (nova).** Duas grandezas declaradas:
`min_observed_spawns = 100` e `min_window_coverage_days = 90`. Abaixo de
qualquer uma, a saída é RECUSA. Sem esta perna a regra fica verde com
denominador zero, que é exatamente o que o instrumento de referência faz
hoje: `ceo-boot.py` devolve `green` quando o total é zero.

**Perna 2 — telemetria.** Zero eventos `agent_spawn` carregando
`skill=<nome>` na janela declarada, lidos pelo leitor nomeado no §1.

### 2.2 As três saídas

| saída | quando | efeito |
|---|---|---|
| `MANTER` | qualquer perna de elegibilidade casa, ou há invocação na janela | nada acontece |
| `ARQUIVAR` | candidata E denominador suficiente E zero invocações | entra na lista, que ainda passa pelo processo de proposta e soak |
| `RECUSA` | denominador insuficiente | a regra não responde; nenhuma skill é arquivada |

`RECUSA` é uma saída de primeira classe, não um erro. Uma regra que não
pode ficar vermelha por amostra insuficiente não é falsificável.

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
  edição canônica** e pede assinatura do Owner. Isso não é detalhe: é o que
  faz o teto de 8 caminhos por pacote morder o P3 (116 skills), e é a razão
  de a decomposição do §5 existir.

## 4. Medição de 2026-09-06 — o que sobrevive, o que foi refutado

Todos os números abaixo foram lidos em disco nesta revisão. A janela é a
família de auditoria por projeto: **10 arquivos, 141.988 eventos, do
`2026-08-21T12:13:43Z` ao `2026-09-07T01:35:30Z` — 16,6 dias.** A família
nasceu com a onda W1 do PLAN-182 (separação por projeto), então não há
histórico anterior atribuível a este projeto.

### 4.1 O bloqueio por calendário está REFUTADO

| grandeza | medido |
|---|---|
| eventos `agent_spawn` | 109 |
| com skill nomeada | 81 |
| sem skill (`unknown`) | 28 |
| unknown-ratio | 0,257 |
| skills distintas invocadas | 11 |

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
magnitude. **Esses 2/8 são um LIMITE registrado, nunca uma melhoria:** o
`CLAUDE.md` deste projeto manda operar em português, então o caminho REAL
de uso é exatamente o ramo degradado — o único em que ligar o índice PIORA
o resultado. Ligar a sugestão por similaridade em sessão em português é
**regressão medida**, e a Fase 1 não pode ser declarada viva sobre ela.

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

Censo gerado hoje do literal "166 skills", fora de `.claude/plans/`: **10
arquivos**. Oito são documentos de produto — `CHANGELOG.md`, `CLAUDE.md`,
`README.md`, `README.pt-BR.md`, `docs/FAQ.md`, `docs/GUIA-COMPLETO.md`,
`docs/GUIA-COMPLETO.pt-BR.md` e `npm/README.md` — e dois são registros de
governança (um veredito de rail e uma proposta arquivada), históricos por
natureza. **Dos oito documentos de produto, dois estão fora da lista
vigiada:** `docs/GUIA-COMPLETO.pt-BR.md`, que é documento vivo, e
`CHANGELOG.md`, que por natureza guarda a contagem de então. O critério
novo asserta a CONTAGEM de sítios casados, não a cor do gate.

## 5. Waves

Decomposição sob o modelo de operação v2: no máximo 400 linhas alteradas ou
8 caminhos por pacote, uma rodada de mecanismo mais uma de confirmação, e
regra de parada pré-registrada por onda. Cada item declara seu `Check:`.

### W0 — a regra e a sonda viram código executável (pacote LIVRE)

Regra de parada: se o controle de não-autofagia (AC-0.2) não ficar verde em
duas rodadas, a regra muda de arquitetura em vez de ganhar mais uma
exceção.

- [ ] **AC-0.1** [P0] a regra existe como programa, com as três pernas do §2.1 e as três saídas do §2.2, e imprime seus INPUTS (janela, número de eventos, leitor usado).
  Check: `python3 .claude/plans/PLAN-175/p2/prune-rule.py --repo . --json`
- [ ] **AC-0.2** [P0] **CONTROLE DE NÃO-AUTOFAGIA.** Rodada sobre ESTE repositório, a regra devolve `MANTER` para `ceo-orchestration` e para as skills dos cinco arquétipos do piso de VETO do ADR-052 — hoje 4 skills distintas, porque dois arquétipos compartilham uma. O conjunto é derivado de `.claude/agents/`, nunca digitado, para acompanhar mudança de mapeamento. Sai diferente de zero nomeando a skill em falta.
  Check: `python3 .claude/plans/PLAN-175/p2/prune-rule.py --repo . --assert-keep-veto-floor`
- [ ] **AC-0.3** [P0] **CONTROLE POSITIVO do mecanismo.** Com a perna de elegibilidade desligada, a MESMA invocação sai diferente de zero e nomeia `ceo-orchestration` — provando que é a perna 0 que segura a skill, e não o acaso.
  Check: `python3 .claude/plans/PLAN-175/p2/prune-rule.py --repo . --assert-keep-veto-floor --disable-eligibility` sai com código diferente de 0
- [ ] **AC-0.4** [P0] a guarda de denominador devolve `RECUSA`, nunca `ARQUIVAR`, quando a telemetria está vazia — o caso medido no §4.2.
  Check: `python3 .claude/plans/PLAN-175/p2/prune-rule.py --repo . --force-empty-telemetry --json` imprime `"verdict": "RECUSA"` para toda skill
- [ ] **AC-0.5** [P0] a sonda de idioma passa a usar o modo devolvido pelo recuperador, caminho absoluto, e recusa rodar contra índice inválido; nenhum número aparece digitado na saída.
  Check: `python3 .claude/plans/PLAN-175/p1/probe-retrieval-language-gap.py --require-mode tfidf`
- [ ] **AC-0.6** o injetor de sugestão é declarado ESCOPO DESTE PLANO (onda W1), e a referência ao plano de follow-up inexistente sai do código do roteador.
  Check: `grep -rn "PLAN-097-FOLLOWUP-rag-router-wireup" .claude/hooks/ .claude/scripts/` não devolve nada

### W1 — medição publicada e decisão de idioma (pacote LIVRE)

Regra de parada: se a re-medição com N ≥ 30 não reproduzir a DIREÇÃO da
tabela do §4.4, a decisão (b) volta para o Owner com a evidência nova, e a
Fase 1 não liga.

- [ ] **AC-1.1** [P0] baseline do unknown-ratio publicado com os INPUTS: leitor, invocação completa, janela, número de spawns, data.
  Check: `python3 .claude/scripts/skill-health.py --include-rotated --since all --json`
- [ ] **AC-1.2** a condição de ativação da Fase 2 é estrita e casa com o instrumento de referência: nenhuma forma maior-ou-igual sobrevive no plano.
  Check: `grep -n "≥ 0,10\|>= 0,10\|igual ou acima de 0,10" .claude/plans/PLAN-175-skills-pruning-discovery.md | grep -v "Check:"` não devolve nada (o filtro existe porque a própria linha de verificação cita o padrão proibido), e `grep -n "ratio > 0.10" .claude/scripts/ceo-boot.py` devolve a linha do instrumento
- [ ] **AC-1.3** [P0] re-medição do gap de idioma com N ≥ 30 pares, usando a sonda corrigida da AC-0.5, com a verdade-base gerada e revisada.
  Check: `python3 .claude/plans/PLAN-175/p1/probe-retrieval-language-gap.py --pairs 30 --require-mode tfidf --json`
- [ ] **AC-1.4** [P0] a decisão (b) — indexar português, normalizar a consulta, ou declarar a limitação e manter a busca estática como caminho primário — é RATIFICADA pelo Owner antes de a Fase 1 ligar, com dono e critério de morte escritos.
  Check: `grep -n "decisao-b" .claude/plans/PLAN-175/decisions/` devolve o registro datado e assinado
- [ ] **AC-1.5** [P0] o índice ganha rota de nascimento e gatilho de reconstrução; depois de qualquer poda ele é invalidado, para a sugestão não apontar para skill arquivada.
  Check: `grep -rln "skill-index-build" .claude/hooks/ .github/workflows/ scripts/` devolve pelo menos uma rota real, não uma docstring
- [ ] **AC-1.6** [P0] o positive control da Fase 1 é escrevível: um spawn sem skill produz a sugestão no transcript, pelo injetor da AC-0.6.
  Check: `python3 -m pytest .claude/scripts/tests/ -q -k injector`
- [ ] **AC-1.7** a re-medição aos 30 dias é publicada E a decisão de Fase 2 é APLICADA pela regra do §1 (acima de 0,10 liga a Fase 2; abaixo, registra como atingido). A Fase 1 não fecha no baseline.
  Check: `python3 .claude/scripts/skill-health.py --include-rotated --since 30d --json`

### W2 — poda do core (pacote CANÔNICO, exige assinatura do Owner)

Regra de parada: nenhuma skill é movida antes de a AC-0.2 estar verde. Se a
lista derivada contiver qualquer skill do piso de VETO, a onda para.

- [ ] **AC-2.1** [P0] a lista de arquivamento é DERIVADA pela regra da W0, nunca curada à mão, e vem com os inputs impressos.
  Check: `python3 .claude/plans/PLAN-175/p2/prune-rule.py --repo . --list-archive --json`
- [ ] **AC-2.2** [P0] o destino do arquivo morto fica fora de `.claude/skills/`, ou a exclusão viaja nos DOIS derivadores no mesmo patch; controle em números: a contagem cai de 166 para 165 no patch que arquiva a primeira skill.
  Check: `bash .claude/scripts/local/verify-counts.sh`
- [ ] **AC-2.3** restauração testada: uma skill arquivada e restaurada no mesmo patch de teste, com a contagem voltando ao valor anterior.
  Check: `bash .claude/scripts/local/verify-counts.sh` depois da restauração
- [ ] **AC-2.4** a consolidação usa o critério do §2.3 e as figuras são GERADAS no patch, não digitadas.
  Check: `python3 .claude/plans/PLAN-175/p2/prune-rule.py --repo . --consolidation-census`

### W3 — domain-packs opcionais (BLOQUEADA pelo PLAN-171 W1c)

Regra de parada: sem o artefato de contrato da W1c em disco, com caminho e
data, esta onda não abre. Decomposição por domínio, um pacote por vez, para
caber no teto de 8 caminhos.

- [ ] **AC-3.1** [P0] o artefato de contrato da W1c do PLAN-171 existe em disco, com caminho e data, e é citado aqui pelo caminho.
  Check: `python3 .claude/scripts/check-staleness.py` e leitura do plano PLAN-171 com o caminho do artefato
- [ ] **AC-3.2** [P0] perna A do teste-mestre: instalação de adotante SEM pacotes funciona.
  Check: `bash scripts/tests/smoke-install.sh`
- [ ] **AC-3.3** [P0] perna B do teste-mestre, a que de fato regride: instalação com perfil `core` mais um domínio, DEPOIS da mudança — o caminho que hoje lê `.claude/skills/domains/<parte>`.
  Check: `bash scripts/tests/smoke-install.sh --profile core,<domínio>`
- [ ] **AC-3.4** um ou dois domínios de referência permanecem na árvore, e a integração contínua fica verde sem os pacotes.
  Check: `bash .claude/scripts/validate-governance.sh`

### W4 — contagem derivada nas superfícies de claim (pacote LIVRE)

Regra de parada: se o censo do literal encontrar superfície nova a cada
rodada, o problema é o censo, não a lista — trocar a arquitetura do censo.

- [ ] **AC-4.1** [P0] o censo das superfícies que carregam o literal é GERADO no patch, e inclui as que estão fora da lista de documentos vigiada (medido hoje: 10 arquivos fora de `.claude/plans/`, sendo 8 documentos de produto e 2 registros de governança; dos 8, dois não são vigiados).
  Check: `grep -rln "166 skills" --include='*.md' . | grep -v '/\.git/' | grep -v '\.claude/plans/'`
- [ ] **AC-4.2** [P0] o critério asserta a CONTAGEM de sítios CASADOS pelo verificador, não a cor do gate — uma claim reescrita que deixa de casar tem de ficar visível.
  Check: `bash .claude/scripts/local/verify-counts.sh` com a contagem de casamentos por documento comparada ao censo da AC-4.1
- [ ] **AC-4.3** as superfícies passam a dizer "N core + M frontend + pacotes opcionais", derivado, e o verificador de claims fica verde com tolerância zero.
  Check: `python3 .claude/scripts/check-claude-md-claims.py`
- [ ] **AC-4.4** leitura adicional do anexo §7: o delta de tokens do catálogo antes e depois da poda é medido e publicado junto das superfícies derivadas.
  Check: `python3 .claude/scripts/context-budget.py`

## 6. Bloqueadores e governança

- **Bloqueador único e real:** o artefato de contrato da onda W1c do
  PLAN-171 (fronteira de posse dos domain-packs). Ele prende **apenas a
  W3**. As ondas W0, W1 e W4 não dependem dele.
- **Uma só fonte de espera externa.** O frontmatter diz `external_wait:
  none` e não há segundo lugar no corpo que afirme espera. A afirmação
  anterior de espera por calendário foi refutada no §4.1.
- **Nenhum gate autoriza execução sozinho.** O rail entre modelos
  (rodadas r1 a r3 sobre a versão de S302) e o debate deste plano são
  ADVISORY. O que satisfaz a linha do runbook é o registro do debate em
  `.claude/plans/PLAN-175/debate/round-1/`; o que autoriza execução é o
  flip de status pelo Owner.
- **Custo de assinatura.** A W2 e a W3 tocam caminhos canônicos: todo
  `SKILL.md` responde canônico ao oráculo, então mover uma skill é edição
  canônica. A W2 ainda pode ter de EDITAR `verify-counts.sh`, se o destino
  do arquivo morto ficar dentro de `.claude/skills/` — e esse script é
  membro do manifesto de gates do ADR-192, que passa por cerimônia mesmo
  com o oráculo respondendo "livre". A W4 apenas RODA esse script, não o
  edita, e os documentos que ela toca são livres. Só W0, W1 e W4 são
  pacotes integralmente livres.
- **Runbook da primeira sessão:** W0 inteira. Nada de poda na sessão 1 —
  por desenho.

## 7. Anexo S305 — reframe de engenharia de contexto (advisory)

A pesquisa da S305 reposiciona este plano: a poda não é só honestidade de
catálogo — a literatura de engenharia de contexto documenta ganho de
desempenho ao reduzir a superfície de contexto carregada por sessão.
Nenhum passo muda. Leitura ADICIONAL na AC-4.4: medir o delta de tokens do
catálogo antes e depois e publicar junto das superfícies derivadas —
transforma a poda em ganho medido, não só em contagem honesta.

**Nota de escopo:** nenhum dos três críticos do round 1 examinou este
anexo. Ele permanece como estava; um round futuro que queira revisá-lo tem
de pedir foco nele.

## 8. Onde cada consenso do round 1 foi curado

| item | onde |
|---|---|
| C1 janela de 90 dias inexistente | frontmatter `external_wait: none`; §4.1; guarda `min_window_coverage_days` no §2.1 |
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
- **`budget_usd_estimate: 490-610`** = assento medido em US$ 655,23 sobre
  6 sessões numa janela de 3 dias, ou US$ 109,20 por sessão, vezes 4;
  mais 8 rodadas de refutação a US$ 0,1753 por turno de subagente, 40 a
  120 turnos por rodada. Instrumento e invocação:
  `python3 .claude/scripts/ceo-cost.py --since 3d --source transcripts --format json`.
- **`tier_mix_estimate`.** Mix medido na mesma janela: Opus 5 com 92,57%
  do gasto, Fable 5.1 com 6,97%, Sonnet 5 com 0,45%. Para este plano o mix
  planejado é assento em Opus 5, refutadores em Opus 5, documentação em
  Sonnet 5 — e nunca abaixo de Opus para o piso de VETO do ADR-052.

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
- 2026-09-06 (S348, nota do CEO ao aplicar a revisão): o campo `external_wait` ratificado na S302f («gatilho: pós-GA v1.3.0; W1c do PLAN-171 (fronteira de ownership) primeiro») foi substituído por `none` nesta revisão, com a justificativa no corpo do plano (o bloqueio por calendário está refutado: a GA v1.3.0 saiu em 2026-08-17 e o denominador de telemetria já existe). **PENDENTE de ratificação do Owner**, junto com o flip para `executing` (decisão 4.10) e a rodada 2 do debate.
- 2026-09-06 (S348, ~23:5x): **Owner ratifica o `external_wait: none`.**
  Decisão Q6 do bloco B: «Sim, ratificar junto com o flip para
  executing (Recomendado)» — registrada em
  `.claude/plans/PLAN-186/portfolio-review-S348/portfolio-review-S348.md`
  §8. O `external_wait: none` do frontmatter fica RATIFICADO. O flip
  para `status: executing` e a rodada 2 do debate seguem como já
  fixado na decisão 4.10 — não mudam nesta nota; `status:` permanece
  `reviewed`.
