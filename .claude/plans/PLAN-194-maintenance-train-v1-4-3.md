---
id: PLAN-194
title: Trem de manutenção pós-GA 1.4.2 até a v1.4.3
status: executing
created: 2026-09-30
reviewed_at: 2026-10-01
executing_at: 2026-10-02
reviewed_by: "Owner — aceite em bloco das recomendações do planejamento S360 no chat da S361 (2026-10-01); Q3 opção 1: W2, W3 e W5c BLOQUEADAS até o PROCEED do debate único, com os must-fix valendo por onda"
owner: CEO
depends_on: [PLAN-193]
level: L3
budget_tokens: "estimado (contexto do CEO; subagentes à parte): W0 medições 150-300k (sem cota paga); W1 150-300k; W2 0,8-1,5 M com rail (debate único do plano, com a W3 e a W5c); W3 (pin automático verificado, L3) 0,8-1,5 M com debate + rail; W3b 100-200k; W4 150-300k; W5a/W5b 300-600k + cota paga da W5.0; W5c (adoção do Sonnet 5.5, L3 — decisão do Owner S359) 2-4 M com debate + rail + cota paga do re-teste na vez (precedente wave-opus55); W6 100-200k + isca paga mínima da W6.0; W7 1-2 M (kit + re-pass + cortes); W8 50-150k; livres L1-L4 300-600k; L5 (medição do ADR-191) 50-150k"
budget_sessions: "4-8 (estimado; cada assinatura do Owner é uma parada; W2 e W7 podem precisar de sessão própria)"
context_risk: high
external_wait: "GitHub: ubuntu-latest vira Ubuntu 26.04 de 2026-10-19 a 2026-11-19 (actions/runner-images#14748). Owner: fixar a imagem do runner Ceo em Ubuntu 24.04 nas configurações da organização (OQ-2, decidida na S361); agendar o `ceo-backup.sh` (W6.1); congelar o Claude Code durante cada onda com `DISABLE_AUTOUPDATER=1` no `env` do settings do USUÁRIO (S361, Q14); medições pagas só na vez de cada onda (W5.0, W6.0 e o re-teste da W5c — decisão S359); rodar o script de limpeza única da W2.6 com todas as sessões do Claude fechadas (decisão S359); decidir as OQs que restam (OQ-11 — o resto da ordem (a)–(f) e o empate W2 × W7b — e OQ-12); assinar W1, W2, W3, W3b, W4, W5 (inclusive a W5c), W6, W8 e os cortes rc.1/GA; hold de 24 h entre rc e GA (ADR-103). Codex: ficar no 0.156.1 sem npm update -g até a W3 landar (decisão S359) e, mesmo com a W3 landada, até o fim do corte W7 (rc.1 e GA) — salvo re-pin do manifesto dentro do kit (pergunta 7 da W3, S361). Retenção: arquivo rotacionado mais antigo da cadeia completa 90 dias por volta de 2026-11-21. OpenAI: gpt-5/o3 aposentam em 2026-12-11."
eta_calendar: "W1 antes de 2026-10-19 (prazo externo); backup agendado e W6 antes de ~2026-11-21; W3b antes de 2026-12-11; GA v1.4.3 = max(assinaturas do Owner, hold de 24 h rc→GA) — sem data prometida"
tags: [maintenance, release, ci, ubuntu-26-04, audit-spool, codex-pin, npm, claude-code-substrate, retention]
---

> **Regra de WIP (trabalho em voo) — vale para este plano inteiro e divide as vagas com o PLAN-195
> e o PLAN-183.** No máximo **3 pacotes canônicos em voo** ao mesmo tempo; cada pacote com
> **≤ 400 linhas e ≤ 8 paths**. **Exceções — só estas quatro, todas geradas por ferramenta:**
> (1) **W7** (kit do corte derivado por script, como no PLAN-192/193); (2) **W5c — adoção do Sonnet
> 5.5** (decisão do Owner S359, «Adotar»: ~40 espelhos num pacote atômico derivado por script —
> precedente: OQ-2 do PLAN-193, resolvida «Exceção declarada (Recomendado)»);
> (3) o **plano B da W3** (re-pin manual: materiais gerados pelo `re-pin-codex.py`; o teto vale para o
> diff canônico); (4) o **pacote que cria arquivo de ADR ou de emenda em arquivo próprio** (decisão
> do Owner S361, 2026-10-01, Q5 — a **4.ª exceção ao teto de 8 paths**): o índice dos ADR
> (`.claude/adr/README.md`, regenerado por `generate-adr-index.py --write`), os documentos de contagem
> (lista completa na linha «leque de ADR» do mapa de colisões) e o `CLAUDE.md:54` ficam FORA da conta de
> paths e são re-derivados no LAND; só **UM pacote de ADR em voo por vez**, landado junto de um
> fechamento de sessão. Emenda DENTRO do ADR existente só quando for aditiva (precedente: ADR-149 A3);
> mudança semântica ganha arquivo de emenda (doutrina anti-churn, README dos ADR:59-64) — o caso
> provável da W2 (contra o ADR-055-AMEND-3) e da W3 (contra o ADR-182); o debate confirma.
> **Nunca dois pacotes tocando o mesmo arquivo** (mapa de colisões em «Approach»).
> Canônico = arquivo que só muda por cerimônia (pacote revisado + sentinel assinado por GPG do Owner).
>
> **Ordem das vagas — DECIDIDA pelo Owner (S359, 2026-09-30): «Codex automático, depois adopter
> (Recomendado)».** As 3 vagas iniciais: 1.ª **W1** deste plano (CI no Ubuntu 26.04, prazo
> 2026-10-19) → 2.ª **parte A do PLAN-195** (W1 de lá; se a ADR dela sair num pacote próprio — a
> W1-ADR —, as duas usam a MESMA vaga, uma depois da outra, a ADR antes do código) → 3.ª **W3** deste
> plano (pin automático verificado do Codex, L3). **Emenda S361 (Q8, 2026-10-01):** enquanto a W3 espera
> o PROCEED do debate único, a **W3b** ocupa a 3.ª vaga e landa ANTES da W3 (as duas tocam
> `codex_cli_shape.py`), com a **W3b.0** landando antes dela como item livre; a W3 segue dona da vaga e a
> retoma quando o debate fechar (ver OQ-11). Quando a W1 landar, a vaga dela vai para a **W7a do
> PLAN-183** (conserto do A1, único P1 dos adopters); a vaga seguinte vai para a **W2** deste plano
> (estado da auditoria). A **W7b do PLAN-183** segue logo depois da W7a (OQ-21 de lá, recomendação
> aceita pelo Owner na mesma sessão). A **W5c** entra na fila depois da W2, salvo se o debate pedir
> antes (decisão do Owner, «Adotar»). O resto: **OQ-11** (inclui a parte B e a W3 do PLAN-195 em
> posição explícita). A limpeza única dos órfãos (W2.6) é operação do Owner e não ocupa vaga.
> Medições (W0, W5.0, W6.0), debates e lands livres (L1–L5 e a W3b.0) também não ocupam vaga canônica.

## Context

**Estrutura — decisão do Owner (S359, 2026-09-30), RESOLVIDA:** «ok salva memory e claude e segue
como vc sugeriu» — resposta à proposta do CEO: (1) PLAN-194 = trem de manutenção até a próxima versão
(1.4.3); (2) PLAN-195 = segurança do guarda de Bash (classe pública «GuardFall»), L3 com debate,
**fora** deste plano; (3) achados de adopter A1–A7 viram ondas novas no PLAN-183, **fora** deste
plano (com isso a OQ-19 do PLAN-183 fica resolvida: as ondas de lá deixam de ser proposta
provisória); (4) fechamento do PLAN-192/193 (→ done) e do PLAN-170 (→ abandoned) pelo CEO, **fora**
deste plano.

**Decisões do Owner (S359, 2026-09-30) que este plano aplica — RESOLVIDAS, não são perguntas
abertas.** Texto exato da opção escolhida no chat, entre aspas:

| decisão (frase exata do Owner) | efeito neste plano |
|---|---|
| piso do Python: «Manter 3.9 (Recomendado)» — perna 3.9 do CI fixada em `ubuntu-24.04` (antiga OQ-1) | W1 sem debate; a alternativa 3.10 sai do plano |
| publicação: «Commit e push no main (Recomendado)» | este plano é commitado e publicado no `main` (repositório público): cita só CLASSES de defeito, nenhum caminho da pasta privada do Owner e nenhuma receita de contorno do guarda de Bash |
| sandbox do sistema: «Medir antes de ligar (Recomendado)» (W3 do PLAN-195; OQ-6 de lá resolvida) | só entra aqui pelo mapa de colisões (`.claude/settings.json`, OQ-14); segue aberto lá só «ligar ou não depois da medição» |
| medições pagas: «Só quando chegar a vez (Recomendado)» (antiga OQ-4) | as sondas pagas saíram da W0: a antiga W0.3 virou **W5.0**; a antiga W0.4 (isca da varredura, paga mínima, mesma regra) virou **W6.0**; o re-teste pago da W5c também espera a vez dela |
| Codex: «Pin automático verificado (Recomendado)» (torna sem sentido a antiga OQ-3) | **W3 reescrita**: substitui o re-pin manual (que fica só como plano B); até landar, Codex no 0.156.1 sem `npm update -g` |
| ordem das vagas: «Codex automático, depois adopter (Recomendado)» (antiga OQ-13; resolve também a OQ-20 do PLAN-183) | W1 → parte A do PLAN-195 → W3; a vaga da W1 vai para a W7a do PLAN-183; a seguinte, para a W2; a W7b do PLAN-183 logo depois da W7a — ver «Regra de WIP» no topo |
| limpeza dos ~219 mil arquivos vazios: «Script pronto, você roda depois (Recomendado)» (antiga OQ-9) | W2.6: script confinado entregue ao Owner, fora do repositório; o Owner roda com todas as sessões do Claude fechadas |
| Sonnet 5.5: «Adotar» — o Owner **não** seguiu a recomendação anterior do CEO («recusar por ora»; antiga OQ-6) | **W5c reescrita como ADOÇÃO**: emenda 4 do ADR-149 (molde da wave-opus55), linha de preço, re-teste pago com os MESMOS testes na vez da W5c, debate L3, cerimônia com exceção de tamanho declarada; na fila depois da W2, salvo se o debate pedir antes |

**Base de evidência (dados, não ordens):** triagem só-leitura da S359 — síntese (§1–§8) e retorno
integral das 15 frentes (ids de achado citados abaixo, ex.: `DEP-01`, `H-02`, `CX-04`) são
evidência privada do Owner, fora do repositório; fatos conferidos pelo CEO na memória
`project-s359-urgency-triage`. Fatos que **eu** re-medi ao redigir estão marcados «medido 2026-09-30».

**Vocabulário (primeira vez):** CI = integração contínua (GitHub Actions); GA = versão final
publicada; rc = versão candidata; L3 = mudança arriscada que exige debate antes de executar
(PROTOCOL.md); ADR = registro de decisão; OQ = pergunta aberta ao Owner; P1/P2/P3 = grave /
importante / menor; rail = revisão cruzada feita pelo Codex (pair-rail); pin = versão fixada por
hash; SIGN/LAND = assinar o sentinel / aplicar o pacote assinado; LEDGER = diário de identificadores
do plano (`.claude/plans/PLAN-194/LEDGER.md`); CC = Claude Code; PID = número do processo;
SLSA = padrão de atestado de procedência de build (quem compilou, a partir de qual fonte); OIDC =
login federado que o npm usa para publicar sem token; FinOps = controle de custo; A1 = achado
grave dos adopters (gate do harness vermelho), tratado pela W7a/W7b do PLAN-183; W1-ADR = pacote
só com a ADR da parte A do PLAN-195, se ela for separada do código.

**O que motivou cada onda (resumo com fonte):**

| onda | fato | fonte |
|---|---|---|
| W1 | `ubuntu-latest` passa a ser Ubuntu 26.04 de 2026-10-19 a 2026-11-19; o `setup-python` não tem 3.9 para 26.04 (3.10+ tem) | actions/runner-images#14748; memória `project-s359-urgency-triage`; lane `DEP-01` |
| W1 | a matriz de testes pede 3.9 em todo push, num job `runs-on: Ceo` | `.github/workflows/validate.yml:1612`, `:1624-1627` |
| W1 | o runner `Ceo` usa a imagem «Ubuntu Latest (24.04)», versão `latest` (id 2306, relido na S361) — se migra junto: não medido; ponto superado pela Q6/OQ-2, que fixa a 2295 | lane `DEP-01` (`gh api orgs/Canhada-Labs/actions/hosted-runners`) |
| W1 | passos do job de governança usam o `python3` do sistema antes do `setup-python`; dois `import yaml` dependem de PyYAML do sistema | `validate.yml:61-441`, `:304-305`, `setup-python` em `:467` |
| W1 | o template do adopter roda `ubuntu-latest` com o `python3` do sistema (com fallback de pip para PyYAML) | `templates/.github/workflows/validate.yml.template:34`, `:124-126` |
| W2 | state dir com **219.527** entradas, **219.301** com 0 bytes (73.177 `audit-pending.N.journal.lock`, 73.176 `audit-pending.N.journal`, 73.153 `audit-spool.N.jsonl.lock`) | medido 2026-09-30 (`os.scandir`, só leitura) em `~/.claude/projects/<slug>/state`; re-medido na S361 (2026-10-01, ~20:08Z, mesmo método): **223.100** entradas, **222.872** com 0 bytes — o acúmulo segue |
| W2 | todo processo que importa `audit_emit` registra um drain FORÇADO no `atexit`; o forçado espera até 2,5 s pelo lock canônico e lista o dir ordenado | `audit_emit.py:13344`; `spool_writer.py:66`, `:2366`, `:2436`, `:2480`, `:2573`, `:2665` |
| W2 | guards PreToolUse estouraram o timeout de 5 s sob concorrência (ação passa sem decisão) | lane `CC285-05`; `.claude/settings.json` (43 registrações com `"timeout": 5`) |
| W3 | Codex pinado 0.156.1; estável do npm: a **0.159.3** (publicada em 2026-09-30T23:02Z) era a `latest` na medição de ~20:08Z de 2026-10-01, e a **0.160.0 saiu em 2026-10-01T20:26:19Z e virou `latest`** (relido às ~21:30Z; a 0.159.2 da triagem S359 já não era a última); quem fecha o rail é o MANIFESTO por sha exato (`codex-cli-pin-manifest.json`), não a faixa `>=0.128.0,<0.157.0` do `codex-cli-pin.txt` (a faixa não fecha o rail em execução — o pré-voo, só na fase 6, apenas exige que o arquivo exista —, é gate de versão do validador do veredito de release) ⇒ atualizar o CLI antes de re-pinar FECHA o rail; **19 versões estáveis em setembro, 7 depois da 0.156.1 até a 0.159.3; a 0.160.0, de outubro, é a 8.ª** (a tag `alpha` está em 0.161.0-alpha.13); atestado SLSA v1 presente em 0.156.1, 0.159.2, **0.159.3** e **0.160.0** (conferido também nos pacotes da plataforma `@openai/codex@0.159.3-darwin-arm64` e `@openai/codex@0.160.0-darwin-arm64`) | `.claude/governance/codex-cli-pin.txt:147`; `check_pair_rail.py:589-747`, `:1488-1510`; `pair-rail-gate.sh:182-220` (Gate 4, só na fase 6); `npm view @openai/codex time` e `dist` (S361); lanes `CX-01`, `CX-03`; memória `project-s359-urgency-triage` |
| W3b | `check-model-deprecations.py --check` sai **1** na árvore viva a partir de 2026-10-12/13 (gpt-5/o3 aposentam em 2026-12-11) | medido 2026-09-30 com `--today 2026-10-13` (rc 1) e sem `--today` (rc 0); lane `CC285-08` |
| W4 | publish com Node 20 e npm em faixa flutuante; a doc do npm exige Node ≥ 22.14 para publicação sem token | `.github/workflows/npm-publish.yml:245-250`, `:260`; lane `DEP-02` |
| W4 | tags rc **pulam** o job de publish (regra que sustenta carga, fixada por teste) | `npm-publish.yml:29-30`, `:227`; `.claude/governance/npm-trusted-publisher.txt:5-7` |
| W5 | CC 2.1.284: Ultracode não força mais xhigh; Sonnet 5.5 (`claude-sonnet-5-5`, US$ 2/10) virou o Sonnet padrão e entra pelo prefixo `claude-sonnet-5`; sessão sem `permissions.defaultMode` nasce em auto. CC 2.1.285: Bash em background morre em 30 min (máx. 2 h). CC 2.1.286: o watchdog do Workflow passou de 180 s fixos com 1+5 tentativas para 600 s derivados, pausado com ferramenta em voo (medido no binário na S360; CLAUDE.md §4). **CC 2.1.287 é o instalado**: o Claude Code se auto-atualizou de 2.1.286 para 2.1.287 às 2026-10-01T18:21:01Z — as medições da S360 são do 2.1.286, e a seção nova do CHANGELOG precisa ser relida a cada versão (itens que tocam este plano na W5.0, W5.1 e W5c) | lanes `CC-01`, `CC-02`, `CC-04`, `CC285-01`, `CC285-02`, `ANT-01`; `~/.claude/.last-update-result.json`; CHANGELOG do CC 2.1.286 e 2.1.287 (lido na S361) |
| W6 | `cleanupPeriodDays: 90` no projeto (vence o 3650 do `settings.json` do usuário nas sessões deste repositório); `audit-log-2026-08-1.jsonl` (mtime 23/08) é `*.jsonl` de topo; **fato novo (S361, Q9):** a varredura usa o `cleanupPeriodDays` da sessão QUE VARRE e alcança todos os projetos — relatado pela frente de operações: 26 raízes com 90 (contagem grosseira da S361, relida pelo mesmo método: `find "$HOME" -maxdepth 4 -name Library -prune -o -type f -path '*/.claude/*' -name 'settings*.json'` ⇒ 42 arquivos de settings, 29 com 90, 12 sem a chave e só o do usuário com 3650; não é contagem de raízes de projeto) — então subir só este repositório para 3650 NÃO protege a cadeia; o backup agendado passa a ser a proteção principal | `.claude/settings.json:861`; `templates/settings/settings.base.json:671`; lanes `CC285-06`, `F-AUDIT-RETENTION`; relato da frente de operações (S360, não verificado em raiz por raiz) |

## Goal

Cortar a **v1.4.3** com o CI verde no Ubuntu 26.04, o estado da auditoria sem acúmulo por PID, o rail
do Codex com pin automático verificado (procedência conferida e hash registrado sem assinatura manual a
cada versão no hook do rail; nos cortes de release, a definir — pergunta 7 da W3), o publish do npm num
Node suportado e a documentação alinhada ao Claude Code 2.1.286 ou posterior (o instalado em
2026-10-01 é o 2.1.287) — cada mudança com controle vermelho→verde registrado.

**Escopo do núcleo da 1.4.3 — decisão do Owner (S361, 2026-10-01, Q7: «Núcleo, ~12–13 assinaturas»).**
Entram: **W1, W4, W3b e W6** deste plano; a parte A do PLAN-195; a W7a do PLAN-183; a **W2**; a **W5c**
na posição da OQ-11 (depois da W2), se o debate único fechar a tempo; a **W3**, se o debate fechar, SEM
bloquear o corte; e a **rc.1 + GA** (W7). A escolha entre 1.4.3 e 1.5.0 sai do diff do `SPEC/v1` na
abertura do corte. Custo declarado da W5c: 2–4 M de tokens, ~40 espelhos e o manifesto ADR-192, sem
redução de preço. Se a cota apertar, a **W5c é a primeira a sair** (o CEO avisa antes); deixá-la fora
ADIA a adoção do Sonnet 5.5 que o Owner escolheu na S359, e não impede o uso do 5.5 (o
`claude-sonnet-5` do `availableModels` já o admite por prefixo, e o alias `sonnet` resolve para ele:
medido na S361 — a versão exata do processo em execução não foi registrada: 2.1.286 ou 2.1.287 —, um
subagente nomeado com `model: sonnet` serviu `claude-sonnet-5-5`) —
o que se perde é o re-teste.

## Approach

**Ordem e por quê.** A ordem das cerimônias segue a regra de WIP do topo (decisão do Owner). Dentro
dela, quatro reordenações que a evidência justifica:

1. **L1 (correção livre do `check-substrate-drift.py:782`) vem ANTES da W3.** Esse detector é quem
   mostra a versão nova do Codex contra o pin (PLAN-193, W5 «via expressa», item do check de deriva
   no boot), e hoje um `last_seen` que não é dicionário
   zera o relatório inteiro (P2 da parte 3 do re-pass do GA:
   `.claude/plans/PLAN-193/repass-ga/verdict-ga-3.txt:7-13`; conferido no HEAD:
   `(comp.get("last_seen") or {}).get("version")` em `.claude/scripts/check-substrate-drift.py:782`).
2. **W3b separada da W3 e sem esperar por ela.** A W3 virou L3 com debate (pin automático, decisão do
   Owner) e não tem data; a W3b tem prazo duro (2026-12-11) e não pode esperar o debate. Só ficam
   sequenciais se o desenho da W3 tocar `codex_cli_shape.py` (mapa de colisões) — aí a W3b entra no
   mesmo pacote da W3, se couber no teto, ou landa antes dela. **S361 (argv fixo do revisor + Q8):** o desenho (c) da W3
   (modelo e esforço fixos no argv) TOCA `codex_cli_shape.py` — o `_VALID_MODELS` (`:97-105`) não tem
   nenhum `gpt-6*` —, então a condição já vale: a W3b landa ANTES da W3 e ocupa a 3.ª vaga enquanto a W3
   espera o debate. (No plano B da W3 vale ainda o motivo antigo: o molde do `re-pin-codex.py` só lê e
   escreve os 2 canônicos do pin, e seu `PACK_FILES` «may list only files this tool emits».)
3. **W7 (o corte da 1.4.3) foi ACRESCENTADA.** O pedido fala em trem «até a 1.4.3», e os P2 abertos
   do kit do GA 1.4.2 só se curam no DERIVADOR do próximo kit (lane `F14`) — que só existe nesta onda.
   **W8 (TLC) foi separada dos itens livres:** o oráculo diz que `.github/workflows/formal-verify.yml`
   é **canônico** (resultado 1), então não é land livre como a triagem supunha.
4. **Um debate só para as L3 deste plano (W2, W3 e W5c).** `/debate start PLAN-194` cria uma única
   pasta de rodadas por plano (`.claude/plans/PLAN-194/debate/round-1/`, `.claude/commands/debate.md:46`);
   as L3 deste plano vão no mesmo debate, com as propostas no `proposal.md` (≤ 300 linhas,
   `.claude/plans/DEBATE-SCHEMA.md:103`). A W5c (adoção do Sonnet 5.5, decidida depois da primeira
   redação) entra nele; se as três propostas não couberem em 300 linhas, a W5c sai com crítica própria
   registrada no documento de desenho da onda, como a wave-opus55 fez (PLAN-193, W3; seção «Debate»
   do `DESIGN-OPUS55-S357.md`). Debater não ocupa vaga; a execução segue a ordem do topo.
**Cláusula de bloqueio (decisão do Owner S361, Q3 opção 1):** o plano está `reviewed` pela revisão
no chat (PLAN-SCHEMA §4), mas **W2, W3 e W5c ficam BLOQUEADAS até o PROCEED deste debate único**, e os
must-fix dele valem por onda — nenhum pacote canônico dessas três ondas começa antes. As demais ondas
(W1, W3b, W4, W5a/W5b, W6, W7, W8 e os itens livres) não dependem do debate.

**Correção de premissa (W4).** O pedido prevê «rc de controle antes do próximo GA». Uma rc **não
prova o publish**: o job de publish pula tags rc por desenho (`npm-publish.yml:29-30`, `:227`), e o
próprio registro do publicador confiável diz que a troca OIDC só é exercida «at GA, with no earlier
proof point» (`npm-trusted-publisher.txt:5-7`). A W4 faz a rc provar o **toolchain** (Node + npm
exato + empacotamento, sem publicar) e declara o resíduo: a troca OIDC em si só se prova no GA.

**Alternativas descartadas.** (a) Subir o piso do Python para 3.10 na W1: quebra adopters em 3.9 e
contradiz o contrato (CLAUDE.md §4: «Python ≥ 3.9 compatible»; a máquina do Owner roda
`/usr/bin/python3` = 3.9.6, medido 2026-09-30) — descartada pelo Owner na S359 («Manter 3.9 (Recomendado)»). (b) Trocar
`ubuntu-latest` por `ubuntu-24.04` em todos os 21 workflows de uma vez: passa de 8 paths e esconde o
26.04 para sempre; a W1 mede primeiro e muda só o que quebra. (c) Adicionar só a linha de preço do
Sonnet 5.5 no `cost-table.yaml` como land livre: cria um achado novo no `check-model-currency.py`
(superfície S1 com id que a autoridade A1 — o ADR-149 — não cobre; docstring do detector, linhas
1-40) — a linha anda DENTRO do pacote da W5c, junto com a emenda 4 do ADR-149 (o Owner decidiu
adotar). Esse mesmo achado é o controle vermelho da W5c. (d) Re-pin manual da estável do dia (a
versão anterior desta W3 citava a 0.159.2; em 2026-10-01 a estável era a 0.159.3 até as 20:26Z, quando
saiu a 0.160.0): descartado pelo Owner na S359 em favor do pin automático; fica como **plano B** da W3
(`codex-pin-<etiqueta do dia>`, ex.: `codex-pin-0159-3` para a 0.159.3; para a 0.160.0 seria `codex-pin-0160`). (e) Recusar o Sonnet 5.5 por ora (a recomendação anterior do CEO): descartada pelo Owner na
S359 («Adotar»).

**Mapa de colisões (nunca dois pacotes no mesmo arquivo).** Vale para os três planos que dividem as
vagas (este, o PLAN-195 e o PLAN-183); as ondas de outro plano são citadas pelo NOME da seção.

| arquivo | quem toca | ordem |
|---|---|---|
| `.claude/settings.json` | W6 (retenção); W5c (adoção do Sonnet 5.5: `availableModels` é gerado do ADR-149 pelo `generate-available-models.py`); **W3 do PLAN-195** (só se o Owner decidir ligar o sandbox depois da medição) | **W6 primeiro** (data de risco ~2026-11-21); depois a W5c e a W3 do PLAN-195, uma de cada vez; sandbox, retenção e — desde a Q9 da S361 — a W5c num pacote só, apenas se ficarem prontos juntos antes da data (OQ-14, RESPONDIDA) |
| `templates/settings/settings.base.json` | W6 (só se mudar o padrão dos adopters); W5c | W6 primeiro, W5c depois; ou um pacote só se os dois ficarem prontos juntos |
| `.claude/adr/ADR-149-model-id-allowlist.md` | W5a (texto do Ultracode, A3.1); W5c (emenda 4) | um pacote só: a correção da W5a vai dentro da emenda 4 da W5c (o Owner decidiu adotar) |
| `.claude/hooks/_lib/codex_cli_shape.py` | W3b; W3 (o argv com modelo e esforço fixos TOCA o arquivo — S361: hoje o padrão omite `--model` e o `_VALID_MODELS` não tem `gpt-6*`) | sequenciais, e a ordem está DECIDIDA (Q8, S361): a **W3b landa ANTES da W3**, na 3.ª vaga enquanto a W3 espera o debate; se o debate puser o arquivo no pacote da W3, a W3b entra no MESMO pacote só se couber no teto (prazo duro 2026-12-11, pacote pequeno), senão landa antes |
| `.claude/scripts/codex_invoke.py` | W3 (argv com modelo e esforço fixos); W3b (só se o conjunto derivado atingir o exemplo dele) | sequenciais, na mesma ordem da linha acima |
| `.claude/scripts/substrate-watch.json` | W5.1 (e a W3, se o desenho gravar o `codex_cli` ali) | UM refresh só, depois do land da W3 — ou com o Codex ainda no 0.156.1, se o corte W7 vier antes ou se a W3.6 só rodar depois do corte (pergunta 7 da W3) |
| `scripts/install.sh` e `.claude/scripts/data/installer-write-safety-baseline.txt` | W5b; W1a/W1b do PLAN-183 (re-derivação do pacote do ponteiro `PROTOCOL.md`, que toca os dois); W8 do PLAN-183 (baseline, via `upgrade.sh`) | **W5b primeiro** (pequena, 3 paths); depois a W1a/W1b do PLAN-183, re-derivadas sobre ela; por fim a W8 do PLAN-183. Toda onda que toca `scripts/**/*.sh` fora de `scripts/tests/` regenera o baseline do censo no MESMO patch (CLAUDE.md §5, PLAN-185) |
| `.github/workflows/smoke-install.yml` e `.github/workflows/ownership-nightly.yml` (os dois rodam `runs-on: ubuntu-latest`: `smoke-install.yml:196`, `ownership-nightly.yml:34`) | W1.5 (só se o censo W0.1 os marcar); W1a/W1b do PLAN-183 (estão entre os 16 paths do pacote do ponteiro) | **W1.5 primeiro** (prazo 2026-10-19); a W1 do PLAN-183 é re-derivada no HEAD depois dela |
| `.github/workflows/validate.yml` | W1 | nenhuma onda dos outros dois planos o toca hoje (conferido 2026-09-30 nas seções S359 do PLAN-183 e no PLAN-195) |
| `.claude/governance/gate-scripts-manifest.txt` (manifesto ADR-192) | W7 (só se o `release.sh`, membro do manifesto, mudar); W7b e W10 do PLAN-183 (sha do `validate-governance.sh`); **W5c** (S361: a pegada real inclui o `validate-governance.sh`) | **nunca em paralelo**: a mudança do `release.sh` na W7 landa ANTES da W7b/W10 ou DEPOIS do land delas; a W5c (pegada real, linha própria abaixo) segue a mesma regra |
| `INSTALL.md` | W6 (mitigação da retenção); W8 do PLAN-183 (linha sobre o `VERSION` semeado) | **W6 primeiro** (data de risco ~2026-11-21); a W8 do PLAN-183 depois — ou a linha do `VERSION` entra no mesmo patch de documentação da W6 |
| `.claude/scripts/ceo-boot.py` | L2 (disco + deriva + cura de classe do `scheduled_workflows_red` + cura do check de «stranded» — S361) | um pacote só |
| guarda de Bash (hook, testes) e docs de ameaça | W0–W2 do PLAN-195 | nenhuma onda deste plano toca esses arquivos; o `settings.json` do sandbox (W3 do PLAN-195) está na 1.ª linha; a W0 do PLAN-195 edita `docs/threat-model.md` em land livre — ver risco 9 (árvore limpa no SIGN) |
| espelhos gerados (`npm/templates/`, `npm/.claude/`, `dist/`) | W1.4 (se mexer no template do adopter); W5c; ondas que tocam hook | **não são path de pacote**: saída de build ignorada pelo git (`.gitignore:47` `npm/.claude/`, `:50` `npm/templates/`, `:198` `dist/`; `git ls-files npm/templates` = 0, medido 2026-09-30). Não entram em commit nem no Scope do sentinel; `scripts/npm-rebuild.sh` e `scripts/build-plugin.py --check` ficam como passos da bateria, sobre saídas locais |
| **leque de ADR** (acrescentado na S361: o achado da revisão do planejamento S360 sobre a colisão dos pacotes que criam arquivo de ADR foi confirmado e rebaixado para P2): `.claude/adr/README.md` (canônico, oráculo 1; índice regenerado por `generate-adr-index.py --write` e conferido por `--check`, `validate.yml:134-137`); os 8 documentos que citam a contagem de ADR (`README.md`, `README.pt-BR.md`, `npm/README.md`, `docs/ARCHITECTURE.md`, `docs/CTO-GUIDE.md`, `docs/FAQ.md`, `docs/GUIA-COMPLETO.md`, `docs/README.md`; `test_verify_counts.py::_EXPECTED_SITES`, `verify-counts.sh` em `validate.yml:163-166`); o preâmbulo do `CHANGELOG.md` (regra «CHANGELOG HEADER RULE» do mesmo script, `verify-counts.sh:841`, contagem exata); e o `CLAUDE.md:54` (conferido por `check-claude-md-claims.py`, `validate.yml:82-85`) | todo pacote que cria arquivo de ADR ou de emenda em arquivo próprio: a ADR-201 (parte A do PLAN-195), a W7b do PLAN-183 e — provavelmente — a W2 (`ADR-055-AMEND-4`) e a W3 (`ADR-182-AMEND-1`) daqui | **LAND em série**: UM pacote de ADR por vez, landado junto de um fechamento de sessão. O índice e os documentos de contagem ficam FORA da conta de ≤ 8 paths e são re-derivados no LAND (4.ª exceção da «Regra de WIP»; decisão Q5 do Owner, S361) |
| a contagem de ADR (**198** em 2026-10-01: `ls .claude/adr/ADR-*.md` contado por `wc -l`) INCLUI as **22** emendas em arquivo próprio (`ADR-*AMEND*.md`, medido na S361) | W2 e W3, se a emenda for em arquivo próprio em vez de dentro do ADR existente (só emenda aditiva fica dentro — Q5) | entram no leque da linha acima; 198 → 199 não muda o tamanho do `CLAUDE.md`, mas a folga útil é de 87 bytes (máximo 39.999, porque o gate reprova a partir de 40.000 — risco 9) |
| `CHANGELOG.md` (colisão CONDICIONAL) | pacote que cria arquivo de ADR (o preâmbulo carrega a contagem) × **W7** (o `CHANGELOG.md` é path do corte) | **não podem estar em voo juntos**: o pacote de ADR landa ANTES de a W7 tocar o `CHANGELOG.md`, ou DEPOIS do corte |
| pegada real da **W5c** além dos paths candidatos (S361, a partir do precedente da wave-opus55; o censo da abertura da W5c fecha a lista): `.claude/scripts/validate-governance.sh` (oráculo 0, MEMBRO do manifesto ADR-192), `.claude/governance/gate-scripts-manifest.txt` (1), `scripts/upgrade.sh` (1), `scripts/local/smoke-install-parity.sh` (0) e `.claude/scripts/tier_policy_cli` (0) | W5c; o manifesto e o `upgrade.sh` também são tocados por outras ondas (linhas acima: manifesto — W7, W7b, W10; `upgrade.sh` — W5b só mede, W8 do PLAN-183 via baseline) | uma de cada vez; a W5c re-deriva sobre o HEAD do land anterior, e o manifesto segue a regra «nunca em paralelo» da linha própria |
| colisões CONDICIONAIS (S361; só valem se o outro pacote tocar o arquivo): `.claude/hooks/_lib/audit_emit.py` — W2 (só se o debate exigir) × W1a do PLAN-195 (só se a ADR-201 estender `_LEARNING_RAIL_ENUM`/`_LEARNING_SWITCH_ENUM`); `.github/workflows/npm-publish.yml` — W1.5 (só se o censo W0.1 o marcar) × W4; `.github/workflows/formal-verify.yml` — W1.5 (idem; está na lista `WORKFLOWS` do gate semanal, `release.yml:550`) × W8; `.claude/data/model-currency-expected-reds.txt` — W3b × W5c; `codex_cli_shape.py` — W3b × W3 (hoje CERTA, linha própria acima) | os pares citados | em cada par, um pacote por vez; o segundo re-deriva sobre o HEAD do land do primeiro. Ordem padrão: W1.5 antes de W4 e de W8 (prazo 2026-10-19); W3b antes de W5c e da W3 |

## Paths × oráculo

Rodado em 2026-09-30 com `python3 .claude/hooks/check_canonical_edit.py --is-canonical <path>`
(saída no STDOUT: `<path>\t1` = canônico, `\t0` = livre). **Atenção:** oráculo 0 não basta — membro
do manifesto ADR-192 (`.claude/governance/gate-scripts-manifest.txt`) também exige cerimônia (lição
S326); a coluna «manifesto» foi conferida por `grep -F` no manifesto.

| path | oráculo | manifesto ADR-192 | onda |
|---|---|---|---|
| `.github/workflows/validate.yml` | 1 | — | W1 |
| `templates/.github/workflows/validate.yml.template` | 0 | não | W1 |
| `npm/templates/.github/workflows/validate.yml.template` (espelho gerado por `scripts/npm-rebuild.sh`) | 0 | não | **não é path do pacote**: saída ignorada pelo git (`.gitignore:50`); regenerada como passo da bateria da W1.4 |
| `scripts/npm-rebuild.sh` | 0 | não | W1 (só executa) |
| `scripts/tests/smoke-install.sh` | 0 | não | W0.1/W1 (só executa) |
| `scripts/tests/run-activated-workflow.py` | 0 | não | W0.1 (só executa) |
| `.github/workflows/smoke-install.yml` | 1 | — | W1.5 (só se o censo W0.1 o marcar; antes da W1 do PLAN-183 — mapa de colisões) |
| `.github/workflows/ownership-nightly.yml` | 1 | — | W1.5 (mesma regra da linha acima) |
| `.github/workflows/tier-policy.yml` | 1 | — | backlog |
| `.github/workflows/mutation-gate.yml` | 1 | — | backlog |
| `templates/.github/workflows/benchmarks.yml.template`, `npm/templates/.github/workflows/benchmarks.yml.template` | 0 | não | backlog |
| `.github/workflows/shadow-ci.yml` | 1 | — | backlog |
| `.claude/hooks/_lib/spool_writer.py` | 1 | — | W2 |
| `.claude/hooks/_lib/audit_emit.py` | 1 | — | W2 (só se o debate exigir) |
| `.claude/hooks/SessionStart.py` | 1 | — | W2 (só se o GC entrar no início de sessão) |
| `.claude/adr/ADR-055-AMEND-4-spool-state-gc.md` (novo) | 1 | — | W2 |
| `.claude/adr/ADR-055-AMEND-3-opportunistic-drain-nonblocking.md` | 1 | — | referência |
| `.claude/hooks/tests/test_spool_state_gc.py` (novo) | 0 | não | W2 |
| `.claude/hooks/tests/test_spool_drain_contended_skip.py` | 0 | não | W2 |
| `.claude/hooks/tests/test_spool_writer_cache.py` | 0 | não | W2 (regressão) |
| `.claude/hooks/tests/conftest.py` | 1 | — | fora de L4 |
| `.claude/hooks/_lib/audit_hmac.py` | 1 | — | W2 (só executa `verify_chain()`) |
| `.claude/hooks/check_plan_edit.py` | 1 | — | backlog (regex de follow-up) |
| `.claude/plans/PLAN-194/debate/round-1` (novo) | 0 | não | W2 + W3 (debate único) |
| `.claude/plans/PLAN-193/repass-ga/verdict-ga-3.txt` | 0 | não | L1 (evidência, só leitura) |
| `.claude/adr/ADR-182-AMEND-1-codex-auto-pin-provenance.md` (novo; nome proposto) | 1 | — | W3 |
| `.claude/hooks/check_pair_rail.py` | 1 | — | W3 (cura: pin automático) |
| `.claude/hooks/tests/test_check_pair_rail_auto_pin.py` (novo) | 0 | não | W3 |
| `.claude/governance/codex-cli-pin.txt` | 1 | — | W3 (só se a faixa mudar — pergunta 3 do debate); plano B |
| `.claude/governance/codex-cli-pin-manifest.json` | 1 | — | plano B da W3 (no pin automático não recebe o sha — pergunta 1 do debate) |
| `.claude/governance/codex-cli-binary-sha256.txt` | 1 | — | plano B da W3 (conferir se o molde o toca) |
| `.claude/plans/PLAN-194/codex-pin-0159-3/` (OWNER-PIN-SIGN.sh, rehearse-pin-0159-3.sh, pin-0159-3-approved.md, codex-cli-pin.txt.new, codex-cli-pin-manifest.json.new) | 0 | não | plano B da W3 (gerado; nomes de exemplo para a 0.159.3 — a etiqueta segue a versão do dia, `0160` para a 0.160.0; era `codex-pin-0159-2` na versão anterior do plano) |
| `.claude/plans/PLAN-193/codex-pin-0156/OWNER-PIN-SIGN.sh` | 0 | não | plano B da W3 (molde, só leitura) |
| `.claude/scripts/re-pin-codex.py` | 0 | não | plano B da W3 (só executa) |
| `.github/scripts/validate-pair-rail-verdict.py` | 0 | **sim** | W3 (não editar; lê a faixa do pin — controle W3.4 d) |
| `.github/workflows/release.yml` | 1 | — | referência (`:550-557`, `:760`) |
| `.claude/adr/ADR-182-codex-payload-pin-enforcement.md` | 1 | — | referência (emendado pela W3) |
| `.claude/scripts/codex_invoke.py` | 0 | não | W3 (argv com modelo e esforço fixos) / W3b (conferir) |
| `.claude/workflows/council-audit.js` | 1 | — | W3 (pergunta 6 do debate; se ficar fora, backlog) |
| `.claude/scripts/substrate-watch.json` | 0 | não | W5.1 |
| `.claude/hooks/_lib/codex_cli_shape.py` | 1 | — | W3b (landa ANTES da W3 — Q8, S361); W3 (argv com modelo e esforço fixos) |
| `.claude/hooks/codex_review_user_code.py` | 1 | — | W3 (pergunta 6 do debate: chama `codex exec` em `:131` sem conferir o pin; se ficar fora, backlog) |
| `.claude/scripts/run-promotion-gate.py` | 0 | não | W3 (pergunta 6: só `codex --version`, `:198`/`:212`; se ficar fora, backlog) |
| `.claude/hooks/tests/test_codex_cli_shape.py` | 0 | não | W3b |
| `.claude/scripts/optimizer/codex_phase_gate.py` | 0 | não | W3b (se o conjunto derivado atingir) |
| `.claude/scripts/check-model-deprecations.py` | 0 | não | W3b.0 (cura da precisão do matcher — revisão Codex S359) |
| `.claude/scripts/model-deprecations.json` | 0 | não | W3b.3 (linha do `gpt-5.5`, SE a aposentadoria de 2026-10-14 se confirmar em fonte primária — land livre); fora isso, backlog (refresh do ledger) |
| `.claude/scripts/tests/test_check_model_deprecations.py` | 0 | não | W3b.0 (controles negativos/positivos do matcher) |
| `.claude/scripts/check-model-currency.py` | 0 | não | W3b/W5c (só executa) |
| `.claude/data/model-currency-expected-reds.txt` | 0 | não | W3b/W5c |
| `.claude/scripts/tests/test_check_model_currency.py` | 0 | não | W5c |
| `.github/workflows/npm-publish.yml` | 1 | — | W4 |
| `.claude/governance/npm-trusted-publisher.txt` | 1 | — | W4 |
| `.claude/scripts/tests/test_release_workflow_asserts.py` | 0 | não | W4 |
| `.claude/plans/PLAN-158/oidc-failure-playbook.md` | 0 | não | W4 (referência; outro plano) |
| `.claude/adr/ADR-149-model-id-allowlist.md` | 1 | — | W5c (emenda 4, com a correção de texto da W5a dentro) |
| `SUPPORT.md` | 0 | não | W5a |
| `docs/adopter-new-model-fast-access.md` | 0 | não | W5a |
| `INSTALL.md` | 0 | não | W6 (doc; antes da W8 do PLAN-183 — mapa de colisões) |
| `.claude/scripts/cost-table.yaml` | 0 | não | W5c (linha `claude-sonnet-5-5`) |
| `.claude/scripts/budget-summary.py`, `.claude/scripts/ceo-cost-transcripts.py`, `.claude/scripts/success-receipt.py` | 0 | não | W5c (preço e multiplicador de cache — lista de tabelas da wave-opus55) |
| `.claude/scripts/generate-available-models.py` | 0 | não | W5c (só executa) |
| `.claude/skills/core/llm-routing-and-finops/SKILL.md` | 1 | — | W5c (alias `sonnet` × id exato — decisão do debate) |
| `.claude/hooks/_lib/adapters/live/claude.py` | 1 | — | W5c (HTTP 400 com `thinking` desligado e `tool_choice` forçado — lane `ANT-02`) |
| `.claude/hooks/_lib/model_routing.py` | 1 | — | W5.1 (vigia do Haiku 4.5, só leitura: `:62-71` o usa em `file_read`, `line_audit` e `digest`); edição só se a aposentadoria ganhar data |
| `.claude/workflows/eval-baseline-n20.js` | 1 | — | W5.0 (sonda (d): só leitura de `:3` e `:547` — veredito W0a do PLAN-134 de que o `opts.model` do `agent()` é INERTE) |
| `.claude/scripts/tests/test_settings_guard_loadability.py` | 0 | não | W5.1 |
| `.claude/scripts/check-substrate-watch.py` | 0 | não | W5.1 (Owner roda `--refresh`) |
| `scripts/install.sh` | 1 | — | W5b |
| `scripts/upgrade.sh` | 1 | — | W5b (só medir `:219`, `:3881-3884`); W5c (pegada real, mapa de colisões; precedente wave-opus55) |
| `scripts/tests/test-install-deny-baseline.sh` | 0 | não | W5b |
| `.claude/scripts/data/installer-write-safety-baseline.txt` | 0 | não | W5b (regenerado no mesmo patch) |
| `.claude/scripts/check-installer-write-safety.py` | 0 | não | W5b (só executa) |
| `.claude/settings.json` | 1 | — | W6 primeiro; depois W5c (`availableModels` gerado) e a W3 do PLAN-195, se o Owner ligar o sandbox (OQ-14) |
| `templates/settings/settings.base.json` | 1 | — | W6 (só se mudar o padrão dos adopters); W5c |
| `templates/settings/settings.user.json` | 1 | — | W6 (subtrai a chave; sem mudança esperada) |
| `.claude/scripts/ceo-backup.sh` | 0 | não | W6 (só executa) |
| `.claude/scripts/backup-audit.py` | 0 | não | referência |
| `.github/workflows/formal-verify.yml` | 1 | — | W8 |
| `.claude/scripts/check-substrate-drift.py` | 0 | não | L1 |
| `.claude/scripts/tests/test_check_substrate_drift.py` | 0 | não | L1 |
| `.claude/scripts/ceo-boot.py` | 0 | não | L2 |
| `.claude/scripts/tests/test_ceo_boot.py`, `.claude/scripts/tests/test_ceo_boot_enhanced.py` | 0 | não | L2 / L4 |
| `.claude/scripts/tests/test_ceo_boot_sched_red.py` | 0 | não | L2 (caso novo de página velha, com controle vermelho→verde) |
| `npm/.claude/scripts/ceo-boot.py` (espelho local) | 0 | não | L2: NÃO é path do pacote — saída de build ignorada pelo git (`.gitignore:47`), regenerada por `scripts/npm-rebuild.sh` como passo da bateria |
| `.claude/scripts/check-absolute-time-budget.py` (novo; nome proposto) | 0 | não | L4 (instrumento do censo) |
| `.claude/scripts/tests/test_check_absolute_time_budget.py` (novo) | 0 | não | L4 |
| `.claude/scripts/adopt-model.py` (novo) | 0 | não | L3 |
| `.claude/scripts/tests/test_adopt_model.py` (novo) | 0 | não | L3 |
| `.claude/workflows/nightly-hygiene.js` | 1 | — | referência |
| `.claude/scripts/local/release.sh` | 0 | **sim** | W7 (cerimônia se mudar) |
| `.claude/governance/gate-scripts-manifest.txt` | 1 | — | W7 (só se o `release.sh` mudar; nunca em paralelo com a W7b/W10 do PLAN-183 — mapa de colisões); W5c (sha novo do `validate-governance.sh`, se o censo da abertura o marcar — pegada real, mapa de colisões) |
| `.claude/plans/PLAN-193/derive-kit-142.py`, `derive-ga-kit-142.py`, `OWNER-GA-CUT.sh`, `test-ga-kit.sh`, `gen-envelope-ga.py`, `repass-ga/run-ga-repass.sh`, `LEDGER.md` | 0 | não | W7 (moldes, só leitura) |
| `.claude/plans/PLAN-194/derive-kit-143.py`, `.claude/plans/PLAN-194/derive-ga-kit-143.py`, `.claude/plans/PLAN-194/test-rc1-kit.sh` (novos) | 0 | não | W7 |
| `.claude/plans/PLAN-194/LEDGER.md` (novo) | 0 | não | todas |
| `.claude/plans/PLAN-194-maintenance-train-v1-4-3.md` (este) | 0 | não | — |
| `.claude/adr/ADR-002-hooks-package-layout.md` | 1 | — | fora (o Owner manteve o piso 3.9 na S359) |
| `CHANGELOG.md` | 0 | não | W7; e todo pacote que cria arquivo de ADR (o preâmbulo carrega a contagem) — colisão condicional, mapa de colisões |
| `.claude/adr/README.md` | 1 | — | todo pacote que cria arquivo de ADR ou de emenda (índice re-derivado no LAND; fora da conta de paths — 4.ª exceção da «Regra de WIP») |
| `CLAUDE.md` | 0 | não | **corrigido na S361 (antes: «fora, só no closeout»):** a linha 54 (contagem de ADR, conferida por `check-claude-md-claims.py`) VIAJA no pacote que cria arquivo de ADR; a poda por tamanho entra num fechamento ANTES do land da W3 e de qualquer acréscimo (risco 9); fora isso, só no closeout, pelo CEO (Gate-1) |
| `.claude/scripts/validate-governance.sh` | 0 | **sim** | só executa; a W5c o EDITA (pegada real, mapa de colisões — membro do manifesto ⇒ sha novo no `gate-scripts-manifest.txt` no MESMO pacote, cerimônia) |
| `scripts/local/smoke-install-parity.sh` | 0 | não | W5c (pegada real, mapa de colisões; valor do mapa, conferido por leitura da lista de guardas e do manifesto — re-rodar o oráculo na abertura da W5c) |
| `.claude/scripts/tier_policy_cli/` | 0 | não | W5c (pegada real, mapa de colisões; valor do mapa, conferido por leitura da lista de guardas e do manifesto — re-rodar o oráculo na abertura da W5c) |
| `.claude/scripts/validate_governance_fast.py`, `check-staleness.py`, `check-ceremony-script.py`, `check-time-unit.py` | 0 | não | só executam |

## Items

### W0 — Medições antes dos patches (sem código no repositório)
Check: none (medição; comandos, datas e resultados vão para `.claude/plans/PLAN-194/LEDGER.md`)

Regras de toda medição: diretório próprio no scratchpad da sessão; piso de `df` de 60 GB antes de
começar; limpeza confinada ao próprio diretório com `shutil.rmtree` em Python (no CC 2.1.281 um `rm`
com alvo em variável pede confirmação e é negado em 2 min no modo auto — lane `CC-05`); todo job em
background com timeout explícito (CC 2.1.285 mata em 30 min por padrão — lane `CC-04`); nada de
agente bloqueado mais de 180 s numa chamada (regra S358). As mesmas regras valem para as medições
que moram nas próprias ondas (W5.0, W6.0).

As antigas W0.3 e W0.4 (medições pagas) saíram daqui por decisão do Owner na S359 («Só quando chegar
a vez»): viraram **W5.0** e **W6.0**. Os números W0.3/W0.4 ficam vagos para não quebrar referências;
a W0 agora não gasta cota paga.

- [ ] **W0.1 (para W1) — Docker `ubuntu:26.04`** (a tag existe no Docker Hub: conferida em
  2026-10-01, na S361, com última atualização em 2026-09-18; **o Owner autorizou na S361, Q6, ligar o
  colima e baixar a imagem `ubuntu:26.04`** para esta medição). Rodar: (a) o `validate.yml.template` ativado por `scripts/tests/run-activated-workflow.py`
  sobre uma instalação descartável (mesmo método da medição 24.04 com 10/10 verdes, CLAUDE.md §5);
  (b) os passos do job de governança do `validate.yml` que usam o `python3` do sistema (`:61-441`),
  incluindo os `import yaml` de `:304-305`; (c) a suíte de hooks no `python3` da imagem (3.14 segundo
  a lane `DEP-01`; a matriz atual para em 3.12); (d) censo dos 21 workflows com `ubuntu-latest` e dos
  6 jobs `Ceo`: quais usam `python3`, `shellcheck` ou `jq` do sistema (a imagem 26.04 traz shellcheck
  0.11.0 e jq 1.8.1 — lane `DEP-01`). — Check: none (medição)
- [ ] **W0.2 (controle vermelho da W1)** — consultar o manifesto do `setup-python`
  (`actions/python-versions`, `versions-manifest.json`) e registrar com data: 3.9 sem build para
  26.04; 3.10+ com build. **MEDIDA em 2026-10-01 (S361)**, no `versions-manifest.json` do ramo `main` de
  `actions/python-versions`: o 3.9 NÃO tem nenhum build linux para 26.04 (só até 24.04); o 3.10 e o
  3.14 têm. Falta gravar no LEDGER, que só nasce no 1.º commit de trabalho. — Check: none (medição)
- [ ] **W0.5 (controle vermelho da W2)** — em árvore descartável: latência de saída de um hook e
  contagem de `drain canonical lock timeout` com state dir de ~220 mil entradas contra vazio, com 9 ou
  mais saídas concorrentes (limiar estimado na lane `H-02`). — Check: none (medição)

### W1 — CI pronto para Ubuntu 26.04 (PRAZO 2026-10-19)
Check: gh run list --workflow validate.yml --commit "$(git rev-parse HEAD)" --json conclusion

**Objetivo:** nenhum job do Validate fica vermelho quando `ubuntu-latest` virar 26.04, sem perder a
cobertura do piso 3.9. **Paths:** `.github/workflows/validate.yml` (1); `templates/.github/workflows/validate.yml.template`
(0) **só se** a W0.1 mostrar quebra no template (land livre separado — o espelho em `npm/templates/`
é saída de build ignorada pelo git, não path do pacote; ver mapa de colisões); outros workflows
**só** os que o censo W0.1 marcar. **Estimativa:** 40-80 linhas, 1-3 paths (estimado). **Debate:**
não — o Owner decidiu manter o piso 3.9 (S359, «Manter 3.9 (Recomendado)»); a mudança é mecânica.
**Cerimônia:** sim. **Vaga:** 1.ª das 3 iniciais (ordem decidida pelo Owner); ao landar, a vaga vai
para a W7a do PLAN-183.

- [ ] W1.1 perna 3.9 do `hook-tests-python-matrix` num rótulo fixo `ubuntu-24.04` (hoje o job inteiro
  é `runs-on: Ceo`, `:1612`); as outras pernas seguem onde estão. — Check: gh run list --workflow validate.yml --commit "$(git rev-parse HEAD)" --json conclusion
- [ ] W1.2 os `import yaml` de `:304-305` deixam de depender de PyYAML do sistema (mover para depois
  do `setup-python` de `:467` ou instalar PyYAML antes). — Check: gh run list --workflow validate.yml --commit "$(git rev-parse HEAD)" --json conclusion
- [ ] W1.3 uma perna 3.14 em `ubuntu-26.04` só no `schedule` (`validate.yml:14-15`, cron `37 7 * * *`),
  para detectar quebra do sistema novo antes dos adopters. — Check: gh run list --workflow validate.yml --event schedule --limit 1 --json conclusion
- [ ] W1.4 template do adopter: se a W0.1 (a) sair vermelha, correção livre + `scripts/npm-rebuild.sh`
  para regenerar o espelho local (saída fora do commit); se sair verde, registrar «sem mudança» no
  LEDGER. — Check: bash scripts/tests/smoke-install.sh
- [ ] W1.5 outros workflows que o censo W0.1 marcar como quebrando: mitigação `ubuntu-24.04` (a oficial
  do issue #14748), em pacotes de ≤ 8 paths, primeiro os que estão na lista `WORKFLOWS` do gate
  semanal do release (`release.yml:550`). `smoke-install.yml` e `ownership-nightly.yml` também são
  paths da W1 do PLAN-183 (pacote do ponteiro): a W1.5 vai primeiro e aquele pacote é re-derivado
  depois (mapa de colisões). — Check: gh run list --limit 30 --json workflowName,conclusion

**Controle vermelho→verde:** vermelho = W0.2 (manifesto sem 3.9 para 26.04) + W0.1 (passo que
quebra em 26.04, se houver); verde = Validate verde no push do land + primeira execução noturna da
perna 3.14 verde (ou vermelha com achado nomeado no LEDGER). **Dependências:** W0.1, W0.2; OQ-2 RESPONDIDA (2026-10-01, Q6): o Owner fixa o runner «Ceo» na imagem
2295 «Ubuntu 24.04» — hoje ele usa a 2306 «Ubuntu Latest (24.04)», versão `latest`, que pelo rótulo deve migrar junto (inferência, não medida — mesma ressalva da tabela do Context; fixar na 2295 elimina a incerteza)
(`gh api orgs/Canhada-Labs/actions/hosted-runners` e `.../hosted-runners/images/github-owned`, lidos
na S361; a lista também tem a 4951 «Ubuntu 26.04») — e a W1 segue como planejada (perna 3.9 em
`ubuntu-24.04` e canário 3.14 em 26.04), como rede para os jobs `ubuntu-latest` e para os adopters.
**Prazo:** land antes de **2026-10-19**.

### W2 — Estado da auditoria: arquivos por PID e drain forçado (L3, debate)
Check: python3 -m pytest .claude/hooks/tests/test_spool_state_gc.py .claude/hooks/tests/test_spool_drain_contended_skip.py .claude/hooks/tests/test_spool_writer_cache.py -q

**Objetivo:** a saída de um hook sem spool próprio não toma o lock canônico nem varre o diretório; os
arquivos vazios por PID deixam de se acumular; os órfãos atuais somem (219.301 arquivos de 0 byte em 2026-09-30; 222.872 na re-medição da S361). **Por que importa:**
com o dir cheio, cada drain forçado lista e ordena ~219 mil nomes sob o lock canônico (~0,24-0,30 s
por drain, lane `H-02`); com saídas concorrentes o lock de 2,5 s estoura e guards PreToolUse passaram
do timeout de 5 s — e um guard que estoura o timeout deixa a ação passar sem decisão (lane
`CC285-05`). **Paths:** `.claude/hooks/_lib/spool_writer.py` (1); `.claude/adr/ADR-055-AMEND-4-spool-state-gc.md`
(1, novo, PROPOSED); `.claude/hooks/SessionStart.py` (1) só se o GC entrar na reconciliação de início
de sessão; `.claude/hooks/tests/test_spool_state_gc.py` (0, novo); `test_spool_drain_contended_skip.py`
(0). `audit_emit.py` (1) fica fora, salvo se o debate mostrar necessidade. **Estimativa:** 200-300
linhas, 3-5 paths (estimado). **Debate:** SIM — núcleo da cadeia de auditoria, e a cura emenda a
premissa do ADR-055-AMEND-3 de que o timeout do drain forçado é «genuinamente anômalo». `needs_debate=true`
(o mesmo que «Debate: SIM» acima).
**BLOQUEADA — decisão do Owner S361 (2026-10-01, Q3):** nenhum pacote da W2 começa antes do PROCEED do
debate único (W2.1), e os must-fix dele valem para esta onda. **Emenda de ADR (Q5, S361):** a cura
contradiz uma premissa do ADR-055-AMEND-3 — mudança SEMÂNTICA ⇒ arquivo de emenda próprio
(`ADR-055-AMEND-4`), que entra no leque de ADR do mapa de colisões (LAND em série; 4.ª exceção ao teto
de paths). O debate confirma se a emenda cabe dentro do ADR existente (só se for aditiva).

- [ ] W2.1 `/debate start PLAN-194` com as propostas da W2, da W3 e da W5c no mesmo `proposal.md`
  (debate único — Approach, item 4; críticos sugeridos: Segurança, SRE, QA); ADR-055-AMEND-4 em
  PROPOSED com os invariantes abaixo. — Check: ls .claude/plans/PLAN-194/debate/round-1
- [ ] W2.2 caminho rápido no `_atexit_drain` (`spool_writer.py:2573`): sem spool próprio não vazio e
  sem `.draining`, não tomar o lock canônico. — Check: python3 -m pytest .claude/hooks/tests/test_spool_state_gc.py -q
- [ ] W2.3 journals e locks por PID fora do diretório que o drain varre (ex.: subdiretório próprio), para
  a listagem ver só spools. — Check: python3 -m pytest .claude/hooks/tests/test_spool_state_gc.py -q
- [ ] W2.4 GC de arquivos de 0 bytes de PIDs mortos, FORA do lock canônico, com predicado conservador:
  0 bytes + nome num dos 3 padrões + trava obtida sem bloquear; journal com conteúdo NUNCA é apagado;
  PID reusado não basta para apagar. — Check: python3 -m pytest .claude/hooks/tests/test_spool_state_gc.py -q
- [ ] W2.5 invariantes provados em teste de estresse: nenhum evento perdido (contagem igual antes e
  depois; `verify_chain()` íntegro, `.claude/hooks/_lib/audit_hmac.py`). — Check: python3 -m pytest .claude/hooks/tests/test_spool_state_gc.py -q -k invariant
- [ ] W2.6 limpeza única dos órfãos do state dir VIVO. **Decisão do Owner (S359, 2026-09-30):
  «Script pronto, você roda depois (Recomendado)»** (antiga OQ-9, resolvida). Script confinado
  entregue ao Owner, fora do repositório, confinado ao state dir, com predicado próprio (diferente da
  W2.4, que adquire a trava sem bloquear dentro do hook): nome casando exatamente um dos 3 padrões,
  arquivo comum de 0 byte (sem symlink nem hardlink), mtime > 10 min, PID morto, família sem conteúdo,
  re-exame antes de apagar, simulação por padrão (só apaga com `--apply`) e recusa com sessão do
  Claude viva; journal com conteúdo NUNCA; o Owner
  roda com TODAS as sessões do Claude fechadas; contagem antes/depois no LEDGER pelo mesmo método do
  critério de sucesso. **Pode rodar antes do resto da W2** (é operação do Owner fora do repositório,
  não ocupa vaga): alivia o sintoma — o drain forçado deixa de listar os ~222 mil nomes (re-medido na S361; o número cresce) — até o acúmulo
  voltar (ritmo não medido; teto estimado de ~300 mil pelo espaço de PIDs do macOS, lane `H-02`). A
  cura para os arquivos não voltarem é o resto da W2. — Check: none (operação do Owner; contagem no LEDGER)
- [ ] W2.7 rail nos bytes canônicos até rodada limpa (regra de parada pré-registrada antes da 1.ª
  rodada: ≤ 3 rodadas; NO-GO só por P0 ou afirmação falsa); SIGN/LAND. — Check: python3 .claude/scripts/check-ceremony-script.py

**Controle vermelho→verde:** W0.5 reproduz os timeouts com ~220 mil entradas (vermelho); depois da
cura, a mesma carga não gera `drain canonical lock timeout` e a latência de saída fica igual à do dir
vazio (verde). No vivo, o critério de sucesso conta os arquivos de 0 bytes no state dir INTEIRO
(inclusive o subdiretório novo da W2.3 — mudar de lugar não é curar). **Dependências:** W0.5; debate
único do plano; vaga: a seguinte à que a W7a do PLAN-183 ocupar (a da W1) — ordem decidida pelo
Owner, «Regra de WIP» no topo. **Prazo:** sem data externa;
recomendado antes do corte W7. **Fora (follow-up):** breadcrumb com taxa limitada, rotação do `audit-log.errors` e
contagem por classe no boot (lane `H-03`). **Estado medido na S361 (2026-10-01, ~20:08Z):** o
`audit-log.errors` tem 25.589 linhas (25.393 na medição anterior do mesmo dia); o log foi rotado em
2026-10-01T17:23:56Z (`audit-log.rotation-manifest.json`: arquivo anterior `audit-log-2026-10.jsonl`).

### W3 — Pin automático verificado do Codex CLI (L3, debate; decisão do Owner S359)
Check: python3 .claude/hooks/check_pair_rail.py --verify-codex-pin "$(command -v codex)"

**Decisão do Owner (S359, 2026-09-30):** «Pin automático verificado (Recomendado)». Motivo dado por
ele: não ter de mexer nisso de novo a cada versão (na triagem da S359 o Codex tinha soltado 18 estáveis
em 30 dias; medido de novo na S361: **19 estáveis em setembro, 7 depois da 0.156.1 até a 0.159.3; a 0.160.0 saiu
em 2026-10-01T20:26Z, a 8.ª**). Fonte: memória `project-s359-urgency-triage` (parágrafo «Codex —
decisão do Owner»). **Substitui** o re-pin manual (que a versão anterior desta onda descrevia para a
0.159.2; hoje seria para a 0.160.0) — ele fica como **plano B** (fim da seção).

**BLOQUEADA — decisão do Owner S361 (2026-10-01, Q3):** nenhum pacote da W3 começa antes do PROCEED do
debate único (W2.1/W3.2), e os must-fix dele valem para esta onda. `needs_debate=true` (o mesmo que
«Debate: SIM» abaixo). Enquanto isso, a 3.ª vaga inicial é ocupada pela W3b (Q8, S361).

**Objetivo:** uma versão nova do Codex passa a valer para o rail sem cerimônia por versão, desde que a
procedência seja conferida automaticamente; o Owner deixa de assinar a cada atualização **no hook do
rail; nos cortes de release, a definir (pergunta 7)**.
**Desenho decidido (mesma fonte):** (a) na 1.ª vez que o rail vê uma versão nova, confere sozinho a
procedência no npm (atestado SLSA v1 do CI da OpenAI — conferido presente em 0.156.1, 0.159.2,
0.159.3 e 0.160.0) e registra o sha256 verificado, sem assinatura do Owner; (b) sentinela automática com corpus
fixo de defeitos avisa se o revisor piorar, **sem travar**; (c) modelo e esforço fixos no argv do rail
(cura a lane `CX-07`, antes no backlog); (d) cada veredito registra versão, modelo e esforço. **Custo
declarado na fonte:** emenda do ADR-182 + debate de segurança + 1 cerimônia. **Até landar** (e, nos cortes de
release, até o fim do corte W7 — pergunta 7): ficar no 0.156.1, **sem `npm update -g`** — o MANIFESTO
por sha exato (`codex-cli-pin-manifest.json`) recusaria o binário novo e fecharia o rail: o hook
bloqueia as escritas L3+ (`check_pair_rail.py:1488-1510`, núcleo de verificação em `:589-747`); o
pré-voo `pair-rail-gate.sh` só confere o pin na fase 6 (`:182-220`) e aborta ali; as rodadas manuais
(`codex exec review`, `codex_invoke.py:193`, `council-audit.js:325`) NÃO conferem o pin e rodariam o
binário novo sem verificação (pergunta 6) — por isso a W3.1 é regra operacional. A
faixa do `codex-cli-pin.txt` (`>=0.128.0,<0.157.0`, `:147`) NÃO é quem fecha o rail: o hook do rail não
a lê e o pré-voo de fase 6 (`pair-rail-gate.sh:185`) só exige que o arquivo exista — o gate 4 compara o sha do
payload com o manifesto, não a versão com a faixa; ela é gate de VERSÃO do validador do veredito de
release (`release.yml:760`, `validate-pair-rail-verdict.py:600-618`).

**Base do argv fixo (medida na S361).** Hoje o padrão do `codex_cli_shape.py` OMITE o `--model`
(`DEFAULT_MODEL = None`, `:110`; o argumento só sai com valor explícito, `:351`), então o revisor herda
o modelo do `~/.codex/config.toml` global: na leitura da S361, `gpt-6-astra` com esforço `xhigh` nas
linhas 1-2 e `memories = true` na linha 125 (o `config.toml.bak-s344` tinha `gpt-5.6-sol`). O app
ChatGPT/Codex reescreveu esse arquivo em 2026-10-01 (Q11: às 14:07:43, segundo a decisão do Owner; o
mtime lido na S361 era 16:21:48, hora local, ou seja, o arquivo foi tocado de novo — modelo, esforço e
`memories` seguiam iguais). Fixar modelo e esforço no argv TOCA o `codex_cli_shape.py` — o `_VALID_MODELS`
(`:97-105`) não tem nenhum `gpt-6*` —, então a W3b entra junto ou landa antes (Q8: landa antes).
Avaliar também `--ignore-user-config` (existe no `codex exec` do 0.156.1: «Do not load
`$CODEX_HOME/config.toml`; auth still uses `CODEX_HOME`»), já que o config tem `memories = true`.
Pela Q11, o `gpt-6-astra` é tratado como MODELO NOVO e re-testado no 1.º pacote do trabalho longo
(regra «modelo novo ⇒ re-testar», CLAUDE.md §4), e o pré-voo de cada rodada registra o sha do config, o
modelo, o esforço e `memories` — se mudou, é «instrumento mudou» e a rodada não conta (regras de
operação em «How to continue»).

**Perguntas de desenho que o debate precisa fechar (não decididas aqui):**
1. Onde o sha verificado fica gravado — não pode ser o manifesto (`codex-cli-pin-manifest.json`,
   oráculo 1), que só muda por cerimônia.
2. Como conferir a assinatura do atestado num framework só-stdlib (CLAUDE.md §4). **O candidato da
   primeira redação não serve:** o `npm audit signatures` não aceita pacote global (`EAUDITGLOBAL`,
   medido na S361 com `npm audit signatures -g`). **Desenho sugerido para o debate (a medir):** o
   `subject.sha512` do atestado igual ao `dist.integrity` (sha512 do `npm pack`) e, daí, o sha256 do
   payload lido do tarball. A procedência vale para o artefato de PLATAFORMA
   (`@openai/codex@<v>-darwin-arm64`, 44 arquivos e ~331 MB na 0.159.3), que é onde está o payload — o
   pacote `@openai/codex@<v>` é só o lançador (3 arquivos); os dois têm atestado SLSA v1 na 0.159.3.
3. O que a faixa do `codex-cli-pin.txt` passa a dizer: o validador do veredito
   (`validate-pair-rail-verdict.py`, membro do manifesto ADR-192) lê a faixa desse arquivo
   (`--codex-cli-pin-file`, `release.yml:760`).
4. Só versões estáveis (dist-tag `latest`), nunca alpha (era a recomendação da antiga OQ-3). Desenho
   sugerido na S361: semver SEM pré-release E dist-tag `latest`, com carência de 24–48 h entre a
   publicação e a aceitação (em 2026-10-01, lido às ~21:30Z, `latest` = 0.160.0 e a tag `alpha` = 0.161.0-alpha.13; até ~20:08Z a `latest` era a 0.159.3).
5. Sem rede ou sem atestado: recusa (fail-closed na entrada, CLAUDE.md §4) e o rail segue na última
   versão verificada.
6. Rodadas manuais e o daemon: `codex_invoke.py:193`, `council-audit.js:325` e o `codex exec review`
   manual não conferem o pin (lane `CX-04`); o daemon `app-server` se atualiza sozinho fora do pin
   (lane `CX-06`) — entram no desenho ou ficam declarados. **Inventário completo (S361)** de quem chama
   o `codex` sem conferir o pin: `.claude/hooks/codex_review_user_code.py:131` (`codex exec --sandbox
   read-only`), `.claude/scripts/run-promotion-gate.py` (só `codex --version`, `:198` e `:212`),
   `.claude/scripts/codex_invoke.py:193` e `.claude/workflows/council-audit.js:325`.
7. **Cortes de release (acrescentada na S361).** O passo 15 do `release.yml` (`:754-763`) passa o
   manifesto assinado ao validador do veredito, que exige `codex_payload_sha256` IGUAL à entrada do
   manifesto da ÁRVORE TAGUEADA (`validate-pair-rail-verdict.py:745-763`), e o `gen-envelope-ga.py` do
   kit recusa sha ou versão diferentes do manifesto (`pinned_codex`, `PLAN-193/gen-envelope-ga.py:213-243`).
   Logo o pin automático NÃO cobre os cortes: um veredito de re-pass com o Codex novo sairia INVALID e o
   corte da 1.4.3 travaria. Decidir: a W3.6 (atualizar o Codex) vai para DEPOIS do corte W7, ou junto com
   um re-pin do manifesto dentro do kit.

**Paths (candidatos; o debate fecha a lista; oráculo rodado em todos):**
`.claude/adr/ADR-182-AMEND-1-codex-auto-pin-provenance.md` (1, novo, PROPOSED; nome proposto);
`.claude/hooks/check_pair_rail.py` (1); `.claude/governance/codex-cli-pin.txt` (1, só se a faixa
mudar); `.claude/hooks/tests/test_check_pair_rail_auto_pin.py` (0, novo); `.claude/scripts/codex_invoke.py`
(0; argv com modelo e esforço fixos); `.claude/hooks/_lib/codex_cli_shape.py` (1; o argv fixo — a W3b
landa antes, Q8); `.claude/hooks/codex_review_user_code.py` (1), `.claude/scripts/run-promotion-gate.py`
(0) e `.claude/workflows/council-audit.js` (1), só se a pergunta 6 os incluir; corpus da sentinela (path
a definir no debate). **Estimativa:**
300-400 linhas por pacote, 4-8 paths (estimado); se o debate pedir mais, dividir em pacotes de ≤ 8
paths — a exceção (4) da «Regra de WIP» cobre só o índice dos ADR e os documentos de contagem que o
arquivo de emenda `ADR-182-AMEND-1` arrasta (mudança semântica contra o ADR-182; o debate confirma), e
não os paths de código. **Debate:** SIM, o debate único do plano (W2, W3 e W5c — Approach,
item 4); `needs_debate=true`. **Cerimônia:** sim. **Vaga:** 3.ª das 3 iniciais (ordem decidida pelo
Owner); **ocupada pela W3b até o debate fechar** (Q8, S361).

- [ ] W3.1 regra operacional até o land e até o fim do corte W7 (pergunta 7; ver W3.6): Codex no
  0.156.1, sem `npm update -g`; nenhuma rodada de rail com outro binário. — Check: python3 .claude/hooks/check_pair_rail.py --verify-codex-pin "$(command -v codex)"
- [ ] W3.2 debate único do plano (ver W2.1) e ADR-182-AMEND-1 em PROPOSED com as respostas às 7
  perguntas acima. — Check: ls .claude/plans/PLAN-194/debate/round-1
- [ ] W3.3 antes de aceitar qualquer versão nova: ler as notas desde a 0.157.0 procurando
  subcomandos removidos que o framework chama (`exec`, `review`, `app-server`) e sondar
  `codex <sub> --help` no binário candidato (a remoção do `mcp-server` na 0.154.0 quebrou em
  silêncio — achado A7 do PLAN-183); o debate decide se essa sonda vira automática. — Check: none (leitura; resultado no LEDGER)
- [ ] W3.4 controles vermelho→verde em árvore descartável: (a) versão nova COM atestado válido ⇒
  aceita e sha registrado; (b) SEM atestado, ou com atestado de outro pacote ⇒ recusada; (c) sem
  rede ⇒ recusada, rail segue no último verificado; (d) se a faixa mudar: veredito sintético com a
  versão nova INVALID antes e válido depois no validador do veredito (flags como em
  `release.yml:755-763`). — Check: python3 -m pytest .claude/hooks/tests/test_check_pair_rail_auto_pin.py -q
- [ ] W3.5 rail nas duas lanes nos bytes canônicos (regra de parada pré-registrada antes da 1.ª
  rodada: ≤ 3 rodadas; NO-GO só por P0 ou afirmação falsa); `check-ceremony-script.py` na bateria;
  materiais commitados como ÚLTIMO land antes da assinatura; SIGN/LAND. — Check: python3 .claude/scripts/check-ceremony-script.py
- [ ] W3.6 depois do LAND **e DEPOIS do corte W7** (pergunta 7: atualizar o Codex antes do corte trava o
  veredito do re-pass; a alternativa é fazer esta etapa junto com um re-pin do manifesto dentro do kit —
  o debate decide): Owner atualiza o Codex para a estável do dia; na 1.ª rodada real, o
  `--verify-codex-pin` dá `verified` sem assinatura nova, e o `session_meta` mostra a versão, o
  originador `codex_exec` e 0 sessões «guardian» (lanes `CX-06`, `CX-12`). — Check: python3 .claude/hooks/check_pair_rail.py --verify-codex-pin "$(command -v codex)"

**Declarar no material assinado** (o que o desenho não cobrir): (a) o daemon `app-server` roda fora do
pin (lane `CX-06`); (b) o `~/.codex/config.toml` global muda o comportamento do rail (esforço passou de
max para xhigh em 29/09 sem re-pin — lane `CX-07`; em 2026-10-01 o app regravou o arquivo com modelo
`gpt-6-astra`, esforço xhigh e `memories = true` — Q11) — o argv fixo fecha isto para o rail; (c)
rodadas manuais que não conferem o pin; (d) o pin automático NÃO cobre os cortes de release
(pergunta 7). **Controle vermelho→verde:** W3.4. **Dependências:** debate (PROCEED — a onda está
BLOQUEADA até lá); L1 (recomendado); 3.ª vaga inicial (decidida; ocupada pela W3b até o debate
fechar); a W3b landada antes; árvore sem modificação rastreada no SIGN. **Prazo:** sem data externa;
não é pré-condição do corte W7 (o 0.156.1 está dentro da faixa pinada e o manifesto atual é o do
0.156.1).

**Plano B — re-pin manual pelo molde (ADR-182 §5; precedentes 0155 e 0156).** Só se o debate recusar
o pin automático ou o 0.156.1 parar de funcionar antes do land. Passos: pré-condições do molde (árvore
sem modificação rastreada — o SIGN aborta, `OWNER-PIN-SIGN.sh:330` do molde, lane `CX-13`; L1
landado; este plano commitado, porque o `re-pin-codex.py` exige `--plan`; tag `v1.4.2` ancestral do
HEAD); `python3 .claude/scripts/re-pin-codex.py <versão> --plan PLAN-194 --mold
.claude/plans/PLAN-193/codex-pin-0156/OWNER-PIN-SIGN.sh --ga-tag v1.4.2 --dry-run` e depois sem
`--dry-run` (baixa ~331 MB: diretório próprio, piso de `df`, limpeza confinada); ensaio com prefixos
npm descartáveis (`$REHEARSE_CODEX_PREFIX`, `$REHEARSE_OLD_CODEX_PREFIX`); rodadas manuais
congeladas entre o `npm i -g` e o SIGN; Owner faz `npm i -g @openai/codex@<versão exata>` e o SIGN na
mesma sentada. Pacote em `.claude/plans/PLAN-194/codex-pin-<etiqueta>/` (regra do `re-pin-codex.py`,
`pack_tag()`: `0.Y.Z` → `0Y-Z`, e só `0Y` se Z = 0 — `0159-3` para a 0.159.3, `0160` para a 0.160.0; o plano B
para a 0.159.3 se chamaria `codex-pin-0159-3`). Controle: `--verify-codex-pin` = `mismatch` logo após o `npm i -g`
→ `verified` depois do SIGN.

### W3b — Ids OpenAI que se aposentam fora da lista de revisores
Check: python3 .claude/scripts/check-model-deprecations.py --check --today 2026-10-13

**Objetivo:** a lista `_VALID_MODELS` (`codex_cli_shape.py:97-105`) não aceita ids que aposentam.
**O conjunto sai do instrumento, não de lista à mão:** `check-model-deprecations.py` (hoje aponta
`gpt-5`/`o3` com aposentadoria 2026-12-11 — lane `CC285-08`). Medido 2026-09-30: `--check --today 2026-10-13`
sai 1; sem `--today`, 0. Nenhum workflow de CI chama o `--check` (grep em `.github/`); quem passa a
mostrar WARN é o nightly-hygiene e o pré-voo não-fatal do `upgrade.sh` no adopter
(`scripts/upgrade.sh:2867`).

**O instrumento ainda não é preciso — os acertos crus NÃO são o conjunto de remoção** (revisão Codex
S359, P2; medido 2026-09-30). `build_matcher` (`check-model-deprecations.py:99-130`) só tem guarda à
DIREITA (`(?![A-Za-z0-9.])`): `gpt-5` casa dentro de `gpt-5-mini`/`gpt-5-codex` (o `-` passa) e `o3`
casa dentro de `o3-mini` e até de `lib2to3`. Os 28 WARN de `--today 2026-10-13` são 7× `gpt-5` e 2× `o3`
em `codex_cli_shape.py`, 1× `o3` em `check-model-currency.py`, 1× `o3` em `check-stdlib-only.py:63`
(`lib2to3` — fora do escopo desta onda), 1× `gpt-5` em `codex_invoke.py`, 2× em
`optimizer/codex_phase_gate.py` — e a outra metade (14) é o espelho NÃO rastreado `npm/.claude/`, que o
detector também varre. Logo: seguir os acertos crus removeria ids que o ledger não aposenta, e o
`--check` nunca chegaria a 0 dentro deste escopo. A W3b.0 cura o INSTRUMENTO antes de derivar.

**Paths:** `check-model-deprecations.py` (0) e `test_check_model_deprecations.py` (0) na W3b.0;
`codex_cli_shape.py` (1); `test_codex_cli_shape.py` (0);
`codex_invoke.py` e `optimizer/codex_phase_gate.py` (0) só se o conjunto derivado atingir o padrão ou
o exemplo deles; `model-currency-expected-reds.txt` (0) se o `check-model-currency.py` (autoridade A2 =
`_VALID_MODELS`) mudar o conjunto de vermelhos. **Estimativa:** 60-110 linhas, 4-7 paths. **Debate:** não.

- [ ] W3b.0 precisão do detector ANTES de derivar: guarda também à ESQUERDA (id não pode ser continuação
  de identificador — `lib2to3` deixa de casar `o3`) e um id aposentado não casa como PREFIXO de outro id
  (`gpt-5` ≠ `gpt-5-mini`/`gpt-5-codex`; variantes só entram se o ledger as listar como `model_id` ou
  alias); decidir e declarar o tratamento do espelho `npm/` (gitignorado, `.gitignore:47`; fora do scan
  ou classificado INERT); classificar também o acerto de `check-model-currency.py:64`, que é uma tupla
  de PREFIXOS de família (`"gpt-", "o3", "o4"`), não um id de modelo nem um dos três falsos positivos. Controles de regressão com os três falsos positivos medidos (NEGATIVOS) e com `gpt-5`/`o3`
  soltos em lista de modelos (POSITIVOS), provados vermelhos antes da cura. Critério: re-medir o
  `--check --today 2026-10-13` e registrar o conjunto restante — ele, e não a lista crua acima, é a
  entrada da W3b.1. — Check: python3 -m pytest .claude/scripts/tests/test_check_model_deprecations.py -q
- [ ] W3b.1 remover da lista os ids que o instrumento CURADO marca; ajustar os testes. — Check: python3 -m pytest .claude/hooks/tests/test_codex_cli_shape.py -q
- [ ] W3b.2 `check-model-currency.py` com o conjunto de vermelhos esperado atualizado conscientemente. — Check: python3 .claude/scripts/check-model-currency.py --expected-reds .claude/data/model-currency-expected-reds.txt
- [ ] W3b.3 **a verificar em fonte primária (S361), ANTES da re-medição da W3b.0 e da W3b.1** (a linha
  nova entra no conjunto que o detector deriva): a aposentadoria do `gpt-5.5` em 2026-10-14. NÃO
  confirmada: o cache de modelos do Codex (`~/.codex/models_cache.json`, relido em 2026-10-01T20:06Z) só
  traz «Legacy coding model», sem data; mas o `gpt-5.5` está em `_VALID_MODELS` (`codex_cli_shape.py:98`)
  e `grep -c gpt-5.5 .claude/scripts/model-deprecations.json` = 0 hoje. Se a fonte primária confirmar, a
  linha entra no `.claude/scripts/model-deprecations.json` (oráculo 0, land livre) e o conjunto derivado
  pelo detector passa a incluí-lo (entrada da W3b.1), e o prazo desse id passa a 2026-10-14, bem antes do
  2026-12-11 dos demais. Se não confirmar, a fonte consultada e o resultado vão para o LEDGER e o item
  fecha sem a linha; se confirmar, `grep -cF 'gpt-5.5' .claude/scripts/model-deprecations.json` passa de
  0 para ≥ 1. — Check: none (verificação em fonte primária; fonte e resultado no LEDGER)

**Controle:** `--check --today 2026-10-13` = 1 hoje (vermelho, medido) → 0 depois (verde).
**Dependências:** nenhuma com o debate da W3 (a W3b não espera por ele); como o desenho da W3 TOCA
`codex_cli_shape.py` (argv fixo — S361), a W3b landa ANTES da W3 (mapa de colisões; Q8) — ou entra no
mesmo pacote dela, só se couber no teto. A W3b.0 landa antes de tudo, como item livre. **Vaga:** a
**3.ª vaga inicial**, enquanto a W3 espera o PROCEED do debate único (exceção à OQ-11 aprovada pelo
Owner na S361, Q8); fora isso fura a fila pela data (OQ-11). **Prazo:** duro em **2026-12-11**; o WARN
começa em 2026-10-12.

### W4 — Publicação npm: Node suportado e npm com versão exata
Check: python3 -m pytest .claude/scripts/tests/test_release_workflow_asserts.py -q

**Objetivo:** o publish do GA roda num Node suportado pela publicação sem token (≥ 22.14) com npm em
versão exata, e a rc prova o toolchain antes do GA. **Paths:** `.github/workflows/npm-publish.yml` (1);
`.claude/governance/npm-trusted-publisher.txt` (1); `test_release_workflow_asserts.py` (0) se as
asserções precisarem acompanhar. **Estimativa:** 30-60 linhas, 2-3 paths. **Debate:** não (L2); o
controle da W4.3 é pré-condição.

- [ ] W4.1 `setup-node` em 24 (ou 22 ≥ 22.14), pinado por SHA; npm com versão EXATA em vez de
  `^11.5.1` (`:260`); comentário de `:4-5` atualizado. — Check: python3 -m pytest .claude/scripts/tests/test_release_workflow_asserts.py -q
- [ ] W4.2 registrar em `npm-trusted-publisher.txt` que a configuração no npmjs.com precisa permitir
  publicação direta, e que configuração criada ou editada depois de 2026-09-03 nasce só com «stage»
  (lane `DEP-03`). **NÃO editar a configuração do publicador confiável.** — Check: none (doc-only)
- [ ] W4.3 prova na rc: um passo/job que roda em tag rc com o MESMO Node e npm e faz tudo menos
  publicar (versões conferidas + empacotamento), mantendo a regra «rc não publica» intacta. — Check: python3 -m pytest .claude/scripts/tests/test_release_workflow_asserts.py -q

**Resíduo declarado:** a troca OIDC só é exercida no publish do GA; a rede é o playbook
`.claude/plans/PLAN-158/oidc-failure-playbook.md` (o plano B por token deixa de funcionar em jan/2027
— síntese §6). **Controle vermelho→verde:** o job da rc.1 da 1.4.3 mostra Node 24/npm exato (verde)
contra o log do 1.4.2 com Node 20.20.2 + npm 11.20.0 (lane `DEP-02`). **Dependências:** OQ-5
RESPONDIDA (2026-10-01, Q9): aceitar a prova parcial (a rc só prova Node e npm) e o playbook de rollback.
**Prazo:** land antes da rc.1 da W7, fora de janela de release.

### W5 — Substrato Claude Code 2.1.284 a 2.1.287
Check: python3 .claude/scripts/generate-available-models.py --check

**Objetivo:** textos e instalação coerentes com o CC **≥ 2.1.286** (alvo da S361; o instalado em
2026-10-01 é o 2.1.287, auto-atualizado às 18:21:01Z), com números re-medidos pelo mesmo
instrumento (W5.0). O piso ≥ 2.1.280 continua correto; nenhum hook quebra no 2.1.285 (33 eventos
idênticos — lane `cc-local-impact`) nem nos itens do CHANGELOG do 2.1.287 lidos pelo CEO na S361
(ver «Itens do CC 2.1.287» na W5.1). A versão do CC fica CONGELADA durante cada onda (Q14, S361) e só
muda entre ondas, com `claude update`, relendo a seção nova do CHANGELOG.

- [ ] **W5.0 — medições pagas, na vez da W5 (decisão do Owner S359: «Só quando chegar a vez
  (Recomendado)»; antiga W0.3; regras de medição da W0).** Com os MESMOS instrumentos da S357: as 8
  sondas `claude -p` + `get_settings` de Ultracode × esforço (inclusive max + ultracode, antes
  impossível); para qual id o alias `sonnet` do Agent/Workflow resolve no CC instalado (2.1.287; na S361
  um subagente nomeado com `model: sonnet` já serviu `claude-sonnet-5-5`; entra na pergunta
  (b) do debate da W5c); taxa de prompts do modo auto (controle S342; o
  runbook S341 foi medido no 2.1.259); latência de hooks numa sessão SOLO (o p50 de 1.192 ms da S359
  está contaminado pela concorrência — lane `CC285-05`). **Sondas baratas acrescentadas na S361**
  (alvo ≥ 2.1.286; cada uma com 1 agente ou 1 leitura): (a) o **watchdog do Workflow**, que passou de
  180 s fixos com 1+5 tentativas (até a 2.1.285) para 600 s derivados, pausado com ferramenta em voo — conferir o
  comportamento medido no binário; (b) a **espera no limite de uso** (o que o CC faz ao bater o limite
  e o efeito do `autoContinueAtUsageLimit`); (c) o hook **`PostModelSwitch` no fallback de recusa**
  (evento criado no 2.1.251, com `PreModelSwitch`; o 2.1.287 mudou as trocas automáticas de modelo
  depois de uma mensagem sinalizada para manter o nível de esforço atual); (d) NOVA: o **`opts.model`
  do `agent()` do Workflow**, que o veredito W0a do PLAN-134 deu como INERTE
  (`.claude/workflows/eval-baseline-n20.js:3` e `:547`), a RE-TESTAR no 2.1.286 ou posterior com 1
  agente, conferindo o id SERVIDO. Medido na S361: o run de planejamento, sem `model:`, saiu 100%
  `claude-opus-5-5` (`ceo-cost-transcripts.py --since-at 2026-10-01T15:00:00Z --by model`, relido na
  S361: 2.642 turnos, todos no mesmo id). **Mudança de instrumento (2.1.287):** o CHANGELOG corrige «a
  folder's CLAUDE.md being attached a second time after resuming a session or after a compaction» — as
  medições do piso re-pago (F) feitas antes da 2.1.287 são de outro instrumento e não se comparam
  sem essa nota. — Check: none (medição paga; resultado no LEDGER)
- [ ] **W5a — textos do Ultracode e do Bash em background (depois da W5.0).** `SUPPORT.md:107` e
  `docs/adopter-new-model-fast-access.md:154-158`, `:347-370` (livres, com data e substrato); nota de
  timeout explícito para jobs longos em background (30 min padrão, máx. 2 h). A correção do ADR-149
  A3.1 (`:381`, canônico) vai dentro da emenda 4 da W5c (o Owner decidiu adotar o Sonnet 5.5; mapa de
  colisões). — Check: python3 .claude/scripts/check-time-unit.py SUPPORT.md docs/adopter-new-model-fast-access.md
- [ ] **W5b — `defaultMode` na instalação `--ceremony user` (OQ-7, RESPONDIDA em 2026-10-01, Q9: gravar
  `"manual"`).** Hoje o `install.sh` grava só a
  deny-baseline (`scripts/install.sh:2448-2548`) e o template `user` exclui o bloco `permissions`
  (`templates/settings/settings.user.json:66-67`); desde o 2.1.284 sessão sem `defaultMode` nasce em
  auto. Recomendação: gravar `"manual"` junto da deny-baseline. Medir antes se o `upgrade.sh` já grava
  `defaultMode` num adopter `user` sem a chave (`scripts/upgrade.sh:219`, `:3881-3884` — não medido).
  Paths: `scripts/install.sh` (1), `scripts/tests/test-install-deny-baseline.sh` (0) e o baseline do
  censo de escrita do instalador `.claude/scripts/data/installer-write-safety-baseline.txt` (0),
  regenerado no MESMO patch (regra do ratchet do PLAN-185). **Ordem:** antes da W1a/W1b e da W8 do
  PLAN-183, que tocam o mesmo `install.sh`/baseline (mapa de colisões). Controle: instalação
  `user` descartável sem a chave (vermelho) → com `"manual"` (verde), perna (D) do teste intacta. —
  Check: bash scripts/tests/test-install-deny-baseline.sh
- [ ] **W5c — ADOÇÃO do Sonnet 5.5 (`claude-sonnet-5-5`; L3, `needs_debate=true`). Decisão do Owner
  (S359, 2026-09-30): «Adotar»** — o Owner não seguiu a recomendação anterior do CEO («recusar por
  ora»: o preço é o mesmo do Sonnet 5, US$ 2/10, `cost-table.yaml:115-119`, então a adoção não ajuda a
  meta de custo; ela vale pela coerência com o substrato — no CC 2.1.284 o 5.5 virou o Sonnet padrão e
  o prefixo `claude-sonnet-5` já o admite sem ratificação). **Molde:** wave-opus55 do PLAN-193 (W3 de
  lá; ADR-149 Amendment 3). **Vaga:** na fila depois da W2, salvo se o debate pedir antes (decisão do
  Owner); no núcleo da 1.4.3 só «se o debate único fechar a tempo», e é a primeira a sair se a cota
  apertar (Q7, S361). **BLOQUEADA — decisão do Owner S361 (2026-10-01, Q3):** nenhum pacote da W5c começa
  antes do PROCEED do debate único (W5c.2), e os must-fix dele valem para esta onda. **Registro no
  LEDGER (S361):** o CC troca de modelo em silêncio quando a API recusa um — a W5c grava o id SERVIDO de
  cada agente da onda (o `ceo-cost-transcripts.py` já mostra o servido: hoje avisa «1 modelo não
  resolvido na tabela de preços» e reporta US$ 0 para `claude-sonnet-5-5`, lido na S361; a linha de
  preço da W5c.3 fecha isso). **Tamanho:** exceção (2) da regra de WIP do topo — pacote atômico derivado por script com o
  censo de ~40 espelhos da wave-opus55, re-derivado no HEAD, de preferência gerado pelo
  `adopt-model.py` do item livre L3 (precedente: OQ-2 do PLAN-193). **Paths candidatos** (o censo
  fecha a lista; oráculo re-rodado na abertura): ADR-149 (1); `cost-table.yaml`, `budget-summary.py`,
  `ceo-cost-transcripts.py`, `success-receipt.py` (0 — as tabelas de preço da wave-opus55);
  `.claude/settings.json` e `templates/settings/settings.base.json` (1, gerados do ADR-149); skill
  `llm-routing-and-finops` (1; `SKILL.md:387-500`); adapter live `claude.py` (1);
  `model-currency-expected-reds.txt` e testes (0). — Check: python3 .claude/scripts/generate-available-models.py --check && python3 .claude/scripts/check-model-currency.py --expected-reds .claude/data/model-currency-expected-reds.txt
- [ ] W5c.1 **re-teste pago, só na vez da W5c** («Só quando chegar a vez (Recomendado)»), com os
  MESMOS testes das adoções anteriores e o instrumento intacto (regra «modelo novo ⇒ re-testar»,
  CLAUDE.md §4); o conjunto exato de testes é fixado no LEDGER ANTES de rodar (pré-registro), junto do
  resultado da W5.0 sobre o alias `sonnet`. Regras de medição da W0. — Check: none (medição paga; resultado no LEDGER)
- [ ] W5c.2 debate L3 dentro do debate único do plano (Approach, item 4; críticos da wave-opus55:
  segurança, QA/upgrade e FinOps). Perguntas: (a) o 5.5 entra só no conjunto de trabalho, com piso
  VETO, fallback e pin inalterados (formato do Amendment 2, o do Fable 5.1 — proposta do CEO), ou mais
  que isso; (b) a skill `llm-routing-and-finops` passa a citar o id exato em vez do alias `sonnet`;
  (c) a cura da classe adaptive-only (PLAN-193, W4) já cobre o 5.5 pelo ADR-149, ou o adapter live
  precisa de ajuste para os dois HTTP 400 (`thinking` desligado e `tool_choice` forçado — lane
  `ANT-02`); (d) a W5c anda antes da posição dela na fila. — Check: ls .claude/plans/PLAN-194/debate/round-1
- [ ] W5c.3 pacote derivado por script: emenda 4 do ADR-149 (com a correção de texto do Ultracode da
  W5a dentro — mapa de colisões); linha `claude-sonnet-5-5` no `cost-table.yaml` com US$ 2 de entrada
  e US$ 10 de saída por milhão de tokens e leitura de cache a US$ 0,20 (fonte: CHANGELOG do Claude
  Code 2.1.284; conferir na página de preços no dia do pacote, como fazem os `source_url` das linhas
  vizinhas). A tabela não tem coluna de cache: o multiplicador vai nos scripts de custo, como na linha
  do Opus 5.5 (comentário em `cost-table.yaml:99`). `availableModels` regenerado pelo
  `generate-available-models.py`. — Check: python3 .claude/scripts/generate-available-models.py --check && python3 -m pytest .claude/hooks/tests/test_adr149_validator_parity.py .claude/scripts/tests/test_check_model_currency.py -q
- [ ] W5c.4 controle vermelho→verde em árvore descartável: só a linha de preço, sem a emenda ⇒ o
  `check-model-currency.py` acusa o id sem autoridade A1 (vermelho — alternativa (c) do «Approach»);
  com a emenda 4 ⇒ o conjunto de vermelhos esperado fica igual (verde). — Check: python3 .claude/scripts/check-model-currency.py --expected-reds .claude/data/model-currency-expected-reds.txt
- [ ] W5c.5 rail nas duas lanes nos bytes canônicos (regra de parada pré-registrada antes da 1.ª
  rodada: ≤ 3 rodadas; NO-GO só por P0 ou afirmação falsa); exceção de tamanho declarada no material
  assinado; `check-ceremony-script.py` na bateria; no `.claude/settings.json`, só depois do land da W6
  ou no mesmo pacote dela (mapa de colisões, OQ-14); SIGN/LAND. — Check: python3 .claude/scripts/check-ceremony-script.py
- [ ] **W5.1 — refresh do ledger de substrato, UMA vez, depois do land da W3 (ou com o Codex ainda no
  0.156.1, se o corte W7 vier antes ou se a W3.6 só rodar depois do corte — pergunta 7 da W3)** (codex_cli,
  claude_code, cc_native_usage e, desde a S361, grok_cli — o ledger tem 0.2.93 de 2026-07-12), com a réplica do loader re-derivada no MESMO patch
  (`test_settings_guard_loadability.py:138` fixa `2.1.280`; o teste de `:522` fica vermelho quando o
  ledger sobe, por desenho). O Owner roda `check-substrate-watch.py --refresh`. **Valores a gravar no
  refresh (S361):** `claude_code` = a versão instalada na hora (2.1.287 em 2026-10-01 — as medições da
  S360 são do 2.1.286, e o ledger tem hoje 2.1.280, de 2026-09-22); `codex_cli` 0.156.1 (instalado e
  pinado); `grok_cli` 1.0.13 (instalado, `grok --version` em 2026-10-01). **Vigia do Haiku 4.5, com
  data:** piso de aposentadoria em 2026-10-15 («Not sooner than October 15, 2026» na página de
  deprecações da Anthropic, lida em 2026-10-01; o modelo segue «Active», sem aviso formal);
  `model_routing.py:62-71` o usa em `file_read`, `line_audit` e `digest`. A estimativa de aposentadoria
  real ≥ ~29/11 que o planejamento S360 registrou NÃO consta na fonte e não foi conferida. **Itens do
  CHANGELOG do CC 2.1.287 que tocam este plano (lidos na S361; nenhum quebra hook):** (i) trocas
  automáticas de modelo depois de uma mensagem sinalizada passam a manter o nível de esforço atual, e
  `claude -p`/SDK deixam de repetir o fallback de modelo a cada mensagem — vale para a W5c, para a
  W5.0(c) e para o runner `claude -p` do `eval-baseline-n20`; (ii) regras `Bash` de ferramenta inteira e
  hooks que permitem passam a PEDIR confirmação, em vez de rodar, para escrita de shell em arquivos que
  as ferramentas de arquivo recusam, e uma escrita de shell por symlink commitado para arquivo sensível
  ou para fora da árvore passa a nomear o destino e esperar uma pessoa — substrato novo para o PLAN-195;
  aqui só item de vigia; (iii) «Claude Mods: plugins may now modify deeper behavior» — superfície nova
  para a vigia; nenhuma habilitação de plugin nas settings DESTE repositório, mas o settings do usuário
  habilita o plugin `warp@claude-code-warp` (se ele usa a superfície de mods: não verificado). —
  Check: python3 -m pytest .claude/scripts/tests/test_settings_guard_loadability.py -q

**Estimativa:** W5a ~100-150 linhas, 3 paths; W5b 60-120 linhas, 2 paths; W5c (adoção) = exceção (2)
da regra de WIP do topo (~40 espelhos num pacote atômico; precedente OQ-2 do PLAN-193), 2-4 M tokens
com debate e rail + a cota paga do re-teste. **Debate:** só a W5c (no debate único do plano).
**Dependências:** W5.0 (paga, na vez da W5); PROCEED do debate único (a W5c está BLOQUEADA até lá — Q3,
S361); W5c.1 (paga, na vez da W5c); W6 antes da W5c no
`.claude/settings.json`, ou no mesmo pacote pela OQ-14; W3 para a W5.1 (se landar antes do corte). **Prazo:** antes do corte W7; se
a W5c não chegar a tempo, o corte declara no material assinado que o prefixo `claude-sonnet-5` admite
o 5.5 sem a emenda.

### W6 — Retenção do log de auditoria
Check: python3 -c "import json;print(json.load(open('.claude/settings.json'))['cleanupPeriodDays'])"

**Objetivo:** nenhum elo da cadeia de auditoria se PERDE: o que a varredura do Claude Code apagar
(inclusive a de sessões de outros projetos — Q9) sobrevive numa cópia agendada, restaurável e
verificável com a chave que o Owner decidir guardar (proteção principal); o 3650 deste repositório só
reduz a varredura nas sessões daqui (complemento).
**Fatos:** a varredura apaga `*.jsonl` de topo mais velhos que o `cleanupPeriodDays` da sessão que
varre (CHANGELOG `[1.4.2]`, linhas 350-365); o valor do projeto é 90 (`.claude/settings.json:861`) e
vence o 3650 do usuário (lane `CC285-06`); o arquivo rotacionado mais antigo completa 90 dias por volta
de 2026-11-21; `ceo-backup.sh` inclui os arquivos rotacionados (`:204`, `:237`) e grava fora de
`~/.claude/projects/`. **Paths:** `.claude/settings.json` (1); `templates/settings/settings.base.json`
(1) só se o Owner decidir mudar o padrão dos adopters; `INSTALL.md` (0). **Estimativa:** 10-30
linhas, 1-3 paths. **Debate:** não.

**Redesenho da W6 (decisão do Owner S361, 2026-10-01, Q9 — OQ-8 reaberta e respondida).** A varredura usa
o `cleanupPeriodDays` da sessão QUE VARRE e alcança todos os projetos (relatado pela frente de operações:
26 raízes com 90 na máquina; não verificado raiz por raiz — ver a linha W6 da tabela do Context), então
subir só este repositório para 3650 NÃO protege a cadeia. Por isso, em ordem de peso: (1) o **backup
agendado (W6.1) é a proteção principal**; (2) o aceite inclui um **ensaio de restaurar e verificar** (W6.3)
(restaurar a cópia numa árvore descartável com `ceo-restore.sh` e rodar `audit-verify-chain.py` sobre ela),
com a **decisão sobre guardar a chave HMAC ficando com o Owner**; (3) o **3650 neste repositório** (W6.2)
vira só COMPLEMENTO, depois da isca W6.0. **Limite declarado do `ceo-backup.sh`** (`:203-235`): copia
`audit-log*.jsonl`, `audit-log.errors`, `memory/` e `agent-metrics.md`, mas NÃO copia o `audit-key`, o
`.salt` nem o `audit-log.rotation-manifest.json` (nem `audit-log.last-hmac` e `audit-log.chain-length`,
conferido no 1.º backup real) — e o `audit-verify-chain.py` sai com código 2 sem a chave, então uma cópia
sem a chave guarda os bytes, mas não prova a cadeia. **No pacote do `.claude/settings.json`:**
corrigir o `_posture_comment` (`:815`): o trecho `'medium' (the default) fewer than 15` passa a `fewer
than 10` (a 2.1.271 baixou o guia de tamanho `medium` de 15 para 10 agentes; CHANGELOG do CC). **O
agendamento (crontab ou LaunchAgent) é do Owner.** Anotar também as permissões mistas na família do log
(leituras da S361, 2026-10-01: `0644` em 5 arquivos rotacionados e no `audit-log.errors`, `0600` nos
demais; o `audit-log.jsonl` vivo foi visto `0600` às ~20:10Z e `0644` às ~21:50Z, depois de uma nova
rotação — algum gravador cria o arquivo vivo sem o modo `0600`; investigar na W6 qual caminho de
criação ignora o modo do `audit_log.py`).

- [ ] W6.0 isca da varredura de transcripts (paga mínima; na vez da W6 — mesma decisão do Owner S359,
  «Só quando chegar a vez (Recomendado)»; antiga W0.4; regras de medição da W0): diretório de projeto descartável com
  um `*.jsonl` de topo antigo; medir se o CC instalado (≥ 2.1.286) apaga, por qual data (mtime?) e qual
  `cleanupPeriodDays` vale (projeto × usuário × a sessão que varre — Q9, S361). — Check: none (medição; resultado no LEDGER)
- [ ] W6.1 Owner, fora do repositório e já: agendar `ceo-backup.sh` (crontab ou LaunchAgent) e rodar a
  primeira cópia. **1.ª cópia FEITA pelo CEO em 2026-10-01T19:50:04Z (S361):**
  `ceo-backup-2026-10-01T195004Z.tar.gz`, 30.111.116 bytes, sha256 `2217cafb…3ffe78` (conferido na
  S361), em `~/.ceo-backups/<slug>/`, com 15 logs `.jsonl` (14 rotacionados + o vivo), o
  `audit-log.errors` e `memory/`; sem `audit-key`, `.salt`, `rotation-manifest`, `last-hmac` e
  `chain-length` (limite declarado acima). Falta: o AGENDAMENTO (Owner); o ensaio é a W6.3. — Check: bash .claude/scripts/ceo-backup.sh --dry-run
- [ ] W6.2 cerimônia com o valor decidido na OQ-8 (Q9: 3650 neste repositório SÓ como complemento do
  backup), depois da isca W6.0; o pacote leva também a correção do `_posture_comment`. — Check: python3 -c "import json;print(json.load(open('.claude/settings.json'))['cleanupPeriodDays'])"
- [ ] W6.3 ensaio de restaurar e verificar (Q9/OQ-8; CEO, na cópia da W6.1, sem esperar a W6.2; árvore
  descartável em diretório próprio da sessão, apagada ao terminar por limpeza confinada):
  `ceo-restore.sh <tarball do backup> --dest <dir descartável> --apply --force` e, para cada
  `audit-log*.jsonl` restaurado, `audit-verify-chain.py --log-file <cópia> --key-file <chave>`. O verde é
  PARIDADE com o original, arquivo por arquivo: mesmo código de saída e mesma 1.ª linha quebrada, inclusive
  as quebras já conhecidas (risco 11) — não se exige saída 0. Sem a chave, a cópia sai com código 2: esse é
  o vermelho. Registrar no LEDGER o resultado por arquivo, qual chave o ensaio usou e a decisão do Owner
  sobre guardar o `audit-key` e o `.salt` (fora do backup, num backup cifrado, ou não guardar). — Check:
  none (ensaio; resultado por arquivo e decisão da chave no LEDGER)

**Controle vermelho→verde:** o controle PRINCIPAL é a W6.3: a cópia restaurada, verificada sem a chave,
sai com código 2 e não prova a cadeia (vermelho) → com a chave decidida pelo Owner, o resultado é igual
ao da cadeia viva (verde). A isca da W6.0 é o controle do COMPLEMENTO (W6.2): apagada com o valor atual
(vermelho, se o 2.1.286 ou posterior ainda varrer) → preservada com o valor novo (verde). **Colisões:** `.claude/settings.json` também é tocado
pela W5c (adoção do Sonnet 5.5) e pela W3 do PLAN-195 (só se o Owner ligar o sandbox depois da
medição) — **a W6 vai primeiro** por causa da data; as outras depois, uma de cada vez (mapa de
colisões, OQ-14). `INSTALL.md` também é tocado pela W8 do PLAN-183 (linha do `VERSION`) — a W6 vai
primeiro, ou a linha entra no mesmo patch de documentação.
**Prazo:** backup antes de ~2026-11-21 (data de risco); cerimônia de preferência antes disso.
**Vaga:** sem posição fixa; fura a fila pela data (OQ-11).

### W7 — Corte da v1.4.3 (rc.1 → hold de 24 h → GA)
Check: bash .claude/scripts/local/release.sh preflight

**Objetivo:** publicar a 1.4.3 com o que landou neste trem, com o kit derivado do kit do GA 1.4.2 e os
P2 herdados curados no DERIVADOR. **Paths:** `.claude/plans/PLAN-194/derive-kit-143.py` e
`derive-ga-kit-143.py` (0, novos; moldes `PLAN-193/derive-kit-142.py` e `derive-ga-kit-142.py`) e as
saídas deles em `.claude/plans/PLAN-194/`; `CHANGELOG.md` (0); `release.sh` (manifesto ADR-192 ⇒
cerimônia, com o sha novo em `.claude/governance/gate-scripts-manifest.txt`) só se mudar — e então
nunca em paralelo com a W7b/W10 do PLAN-183, que também mexem nesse manifesto (mapa de colisões).
**Estimativa:** kit derivado por script (exceção declarada ao teto de linhas,
como no PLAN-192/193 — o derivador do GA 1.4.2 tem 8.984 linhas); 1-2 M tokens. **Debate:** não para o
kit (molde); rail com regra de parada pré-registrada (≤ 3 rodadas; NO-GO só por P0 ou afirmação falsa).

- [ ] W7.1 curar no derivador os P2 abertos herdados do PLAN-193 (lista abaixo). — Check: bash .claude/plans/PLAN-194/test-rc1-kit.sh
- [ ] W7.2 dívida «known-open» RE-DECLARADA no material assinado pela FORMA (sem enumerar sítios). — Check: none (doc-only)
- [ ] W7.3 ensaio em cadeia com a suíte COMPLETA sobre a árvore composta (regra S357). — Check: python3 -m pytest .claude/hooks/tests .claude/scripts/tests -q -x
- [ ] W7.4 rc.1 → adopters no mesmo dia → hold de 24 h (ADR-103) → GA → npm. — Check: npm view ceo-orchestration version

**P2 herdados do PLAN-193 (fonte: `PLAN-193/LEDGER.md:16-18`, `:34-35`, e o registro da rodada 3
do re-pass do GA 1.4.2 — evidência privada do Owner, fora do repositório —, que tem **11**; a memória
diz 12):**
`R3-CLAIMS-01` (passo 2 pede releitura do `npm/README.md` num bump no-op, `OWNER-GA-CUT.sh:1168-1170`);
`R3C-01` (`.gen-*.tmp` órfão sem rota de retomada); `R3S-01` (bullet do envelope, `gen-envelope-ga.py:630-631`);
`R3S-02` (comentário de histórico do runner, `run-ga-repass.sh:791-792`); `M3-01` mech-tools (forma da
mensagem de limite de conta atribuída ao 0.156.1 sem medição); `M3-01` mech-cut (janela de retomada do
G0 começa só no STEP-10); `M3-02` (banner PUBLICADO com `--from 19` sem o STEP-18); `R3H-01` (controles
por ausência de texto sem pré-condição de existência, `test-ga-kit.sh:838-840`); `R3H-02` (controles que
prometem recusa nomeada e só olham o código de saída, `:1211-1213`); `R3H-03` (recusas herdadas do G0 sem
controle de corte inteiro); `R3H-04` (índice D de `:3640-3659` não cobre B4c/B4d e R2v/R4c/R4d). Mais:
espera do registry no passo 18 (5×30 s curta para o CDN do npm); passo 5 sobrescreve `CANDIDATE.sha`
(aberto por desenho, `LEDGER.md:34-35`); o P2 da parte 3 do re-pass é a L1.

**Pré-condições do corte:** W4 landada (senão a rc não prova o toolchain); o veredito do re-pass
precisa de `codex_cli` dentro da faixa pinada E de `codex_payload_sha256` IGUAL ao do MANIFESTO assinado
da árvore tagueada (`release.yml:754-763`; `validate-pair-rail-verdict.py:745-763`; o
`gen-envelope-ga.py` do kit recusa sha ou versão diferentes) — cumprido com o Codex no 0.156.1 e o
manifesto atual; a W3 NÃO muda isso (pergunta 7 da W3: o pin automático não cobre os cortes), então o
Codex só sobe DEPOIS do corte, ou junto com um re-pin do manifesto dentro do kit; W1 obrigatória se o
corte for depois de 2026-10-19; W2 recomendada. **Escopo do corte (Q7, S361):** o núcleo descrito no Goal;
a escolha entre 1.4.3 e 1.5.0 sai do diff do `SPEC/v1` na abertura do corte. **Colisão com o leque de
ADR:** o `CHANGELOG.md` é path desta onda e carrega a contagem de ADR no preâmbulo — um pacote que cria
arquivo de ADR e a W7 não podem estar em voo juntos (mapa de colisões). **Prazo:** sem data prometida
(`eta_calendar`).

### W8 — TLC da verificação formal (canônico, sem prazo)
Check: gh run view "$(gh run list --workflow formal-verify.yml --limit 1 --json databaseId -q '.[0].databaseId')" --json jobs -q '.jobs[] | select(.name=="TLC Model Check") | .conclusion'

**Correção:** a triagem listava o TLC (verificador de modelos do TLA+) como item livre; o oráculo diz
que `.github/workflows/formal-verify.yml` é canônico (1). **Fatos:** `continue-on-error: true` em `:29`;
o hash pinado do `tla2tools` não bate desde ≥ 06/07 (lane `DEP-08`); o gate semanal do release lista
`formal-verify.yml` (`release.yml:550`) mas lê a conclusão da RUN (`:557`), que sai success.
**Paths:** `formal-verify.yml` (1). **Estimativa:** 5-20 linhas, 1 path. **Debate:** não.

**Por que o Check olha o JOB e não a RUN:** o `continue-on-error: true` está no nível do job
(`formal-verify.yml:29`), então a RUN sai `success` mesmo com o passo quebrado. Medido 2026-09-30 na
run `36719886973` (push): run `success`; job «TLC Model Check» `failure`; passo «Download + verify
tla2tools.jar» `failure`; os 3 passos TLC `skipped` — o controle vermelho já existe. Verde = job
`success`; se a decisão for remover o job, verde = `grep -c 'tlc-model-check' .github/workflows/formal-verify.yml`
igual a 0. **Resíduo a declarar:** os 3 passos TLC têm `continue-on-error: true` próprio (`:74`, `:84`,
`:94`), então job `success` prova o download e a conferência do jar, não que o modelo passou.

- [ ] W8.1 investigar o asset fora do CI (download exige OK do Owner) e decidir: re-pinar o hash com
  procedência, trocar para fonte imutável, ou remover o job e declarar. **Não** mudar o gate semanal
  para ler a conclusão do JOB antes do TLC ficar verde (bloquearia cortes). Exige `success` no job
  (ou o job removido, conferido pelo `grep` acima). — Check: gh run view "$(gh run list --workflow formal-verify.yml --limit 1 --json databaseId -q '.[0].databaseId')" --json jobs -q '.jobs[] | select(.name=="TLC Model Check") | .conclusion'

### Itens livres (oráculo 0, fora do manifesto ADR-192 — land livre com a bateria completa)
Check: python3 .claude/scripts/validate_governance_fast.py

- [ ] **L1 — `check-substrate-drift.py:782` (P2 da parte 3 do re-pass do GA; ANTES da W3).** Validar o
  tipo do container do ledger, devolver «desconhecido» por componente e preservar os achados dos outros
  componentes. Controle: ledger com `"last_seen": "2.1.280"` (string) → hoje o relatório zera
  (vermelho); depois, drift do Codex preservado (verde). ~40 linhas, 2 paths. —
  Check: python3 -m pytest .claude/scripts/tests/test_check_substrate_drift.py -q
- [ ] **L2 — `/ceo-boot`: piso de disco + deriva de substrato + cura de classe do `scheduled_workflows_red` + cura do check de «stranded» (um pacote, mesmo arquivo).** (a) Check
  de `df` e do tamanho do `$TMPDIR` (2.ª ocorrência da classe «disco cheio»: clones de agente em 29/09,
  suítes de teste do adopter em 30/09 — cure a classe); (b) ligar `check-substrate-drift.py` offline
  (sem `--fetch`) como check (herança do PLAN-193 W5; sobrepõe o W3a do PLAN-176 — o CEO reconcilia lá).
  **Acrescentado na S361 — cura de CLASSE do falso vermelho de `scheduled_workflows_red`** (2.ª
  ocorrência de duas classes; o falso vermelho foi reproduzido pelo CEO na S360 e o endpoint filtrado
  não é determinístico — medição dele, não refeita na S361): (c) UMA chamada por workflow agendado, SEM
  filtro de servidor, filtrando no cliente, com a detecção e a cura saindo da MESMA resposta, em
  paralelo; (d) UMA única constante de orçamento no lugar das três de hoje (3,5 s em
  `ceo-boot.py:2511`, 3,8 s em `:2552` e 4,0 s em `:147`); (e) guarda de frescor derivada do cron: dado
  velho vira AMARELO, nunca vermelho; (f) o resumo diz quando a cura NÃO foi verificada; (g) cura do
  falso vermelho de `check_plans_stranded_executing` (`ceo-boot.py:338-363`, chave
  `plans_stranded_executing`; recomendação `02-stranded-plans`, prioridade `high`): hoje ele dá VERMELHO a
  todo plano `executing` sem commit em 24 h, sem olhar o `external_wait` nem a folha de bloqueio
  (`## Blockers`, PLAN-SCHEMA §12); passa a consultá-los antes de dar vermelho, de modo que plano parado
  esperando algo declarado não fica vermelho. Estender o check existente, NUNCA criar um paralelo.
  Controle vermelho→verde: plano `executing` sem commit e com espera declarada sai vermelho hoje e deixa de
  sair depois. Regenerar o espelho local `npm/.claude/scripts/ceo-boot.py` (saída
  de build ignorada pelo git — não é path do pacote) e acrescentar ao `test_ceo_boot_sched_red.py` o
  caso de PÁGINA VELHA (hoje ele não tem), com controle vermelho→verde. Estimativa: 80-150 linhas antes
  da S361, 2-3 paths; com (c)-(g) o CEO re-estima ao abrir o pacote (teto de 400 linhas e ≤ 8 paths;
  divide em dois pacotes livres se passar). — Check: python3 -m pytest .claude/scripts/tests/test_ceo_boot.py .claude/scripts/tests/test_ceo_boot_enhanced.py .claude/scripts/tests/test_ceo_boot_sched_red.py .claude/scripts/tests/test_ceo_boot_task_candidate.py -q
- [ ] **L3 — `adopt-model.py` (herança do PLAN-193 W5, item «(depois)»; não existe).** Gera o conjunto
  de edições do ADR-149 para os espelhos (censo de 40 espelhos da wave-opus55). Antes da W5c (o Owner
  decidiu adotar o Sonnet 5.5): é o gerador preferido do pacote dela. 300-400 linhas, 2 paths (estimado). — Check: python3 -m pytest .claude/scripts/tests/test_adopt_model.py -q
- [ ] **L4 — classe «orçamento de tempo absoluto em teste» (herança: `PLAN-193/LEDGER.md:20`).** 3
  ocorrências (derrubou o 1.º corte da 1.4.1; reruns no gate de latência da rc da 1.4.2); ≥ 15 arquivos
  (lane `F12`, contagem por grep). **Instrumento novo** `.claude/scripts/check-absolute-time-budget.py`
  (nome proposto): censo por AST dos asserts de tempo absoluto em `.claude/hooks/tests`,
  `.claude/scripts/tests` e `.claude/scripts/swarm/tests`, com `--check` que sai 0 só com contagem 0
  fora das exceções declaradas no próprio instrumento, cada uma com motivo (`conftest.py`, canônico,
  fica fora; arquivos ainda não convertidos entram como dívida declarada numa lista que só encolhe);
  o teste do instrumento tem controle POSITIVO (módulo sintético com assert de tempo absoluto ⇒
  detectado). Troca por orçamento RELATIVO (molde da chave relativa do ADR-163), controle sob carga
  artificial (os 20 laços ocupados da S356). **Controle vermelho→verde da classe:** o censo sobre o
  HEAD de hoje ≥ 1 sem a lista de dívida (vermelho) → 0 com a lista vazia (verde). 300-400 linhas
  (estimado); ≥ 15 arquivos de teste ⇒ vários pacotes livres de ≤ 8 paths, o instrumento primeiro. —
  Check: python3 .claude/scripts/check-absolute-time-budget.py --check && python3 -m pytest .claude/scripts/tests/test_check_absolute_time_budget.py .claude/hooks/tests .claude/scripts/tests .claude/scripts/swarm/tests -q
- [ ] **L5 — medição would-block/TP-FP do ADR-191 (item livre, só leitura do log; decisão Q13(g), S361).**
  Tabela por regra (`CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED` e `CEO_SPAWN_OVERLAP_GUARD`): quantos spawns cada
  uma teria bloqueado na janela advisory (de 2026-08-13 em diante; evento
  `spawn_file_assignment_recorded`, com `path_count=0` na omissão ou no read-only) e quantos desses
  seriam verdadeiros ou falsos positivos, por amostra. É a entrada da decisão do Owner sobre a virada
  para enforce (a cerimônia segue a Q13(g): medir primeiro, decidir depois); NÃO arma nenhuma variável.
  Fora do núcleo da 1.4.3; sem vaga canônica. — Check: none (medição só de leitura; tabela no LEDGER)

## Orçamento

| onda | tokens (estimado) | sessões | vaga canônica | quem espera |
|---|---|---|---|---|
| W0 | 150-300k (sem cota paga) | 1 | não | — |
| W1 | 150-300k | 1 | sim (1.ª) | assinatura; prazo 19/10 |
| W2 | 0,8-1,5 M | 1-2 | sim (a vaga seguinte à da W7a do PLAN-183 — ordem decidida) | debate único (PROCEED — onda BLOQUEADA até lá, Q3) + assinatura; limpeza W2.6 rodada pelo Owner (script entregue, fora do repositório) |
| W3 | 0,8-1,5 M | 1-2 | sim (3.ª vaga inicial — ordem decidida; ocupada pela W3b até o debate fechar, Q8) | debate único (PROCEED — onda BLOQUEADA até lá, Q3) + assinatura; Codex parado no 0.156.1 até o land e até o fim do corte W7 (pergunta 7) |
| W3b | 100-200k | 1 | sim (3.ª vaga inicial enquanto a W3 espera — Q8, S361; landa antes da W3) | assinatura; prazo 2026-12-11 |
| W4 | 150-300k | 1 | sim | assinatura; antes da rc.1 |
| W5a/W5b | 300-600k + cota paga da W5.0 | 1 | sim (install.sh; o texto do ADR-149 vai na W5c) | W5.0 na vez da W5 (OQ-7 respondida, Q9: gravar `manual`) |
| W5c (adoção do Sonnet 5.5) | 2-4 M + cota paga do re-teste | 1-2 | sim (depois da W2, salvo se o debate pedir antes; exceção de tamanho declarada) | debate único (PROCEED — onda BLOQUEADA até lá, Q3) + re-teste pago na vez + W6 landada antes, ou no mesmo pacote pela OQ-14 (`settings.json`) + assinatura |
| W6 | 100-200k + isca paga mínima da W6.0 | 1 | sim (antes da W5c e da W3 do PLAN-195 no `settings.json`) | agendamento do backup pelo Owner (W6.1; a 1.ª cópia já foi feita na S361) + ensaio de restaurar e verificar (W6.3) + isca W6.0 antes da W6.2; OQ-8 e OQ-14 respondidas (Q9) — a W6 não espera o sandbox nem a W5c |
| W7 | 1-2 M | 1-2 | sim (cortes) | hold de 24 h + assinaturas + npm |
| W8 | 50-150k | com outra | sim | OK do download |
| L1-L4 | 300-600k | espalhadas | não | — |
| L5 (medição do ADR-191) | 50-150k (estimado; só leitura do log, mais a amostra de verdadeiros e falsos positivos) | com outra | não | — |

## Riscos

1. **Prazo de 19/10 perdido** ⇒ Validate vermelho em todo push e toda noite. Mitigação: W1 na 1.ª vaga;
   OQ-2 (fixar a imagem do runner `Ceo`; RESPONDIDA na S361 — o Owner fixa a imagem 2295, Ubuntu 24.04)
   como rede sem código.
2. **O censo W0.1 acha muitos workflows quebrando** ⇒ passa de 8 paths. Mitigação: dividir por
   criticidade (gates do release primeiro); a mitigação oficial `ubuntu-24.04` é por arquivo.
3. **W2 mexe no núcleo da cadeia de auditoria** ⇒ risco de perder evento. Mitigação: debate, invariantes
   em teste de estresse, `verify_chain()`, rail, predicado conservador de GC.
4. **Pin automático aceita uma versão ruim com procedência válida** (o atestado prova a ORIGEM, não a
   QUALIDADE do revisor). Mitigação: sentinela de corpus fixo (avisa, não trava — decisão do Owner),
   versão/modelo/esforço registrados em cada veredito, debate de segurança. **Até a W3 landar** (e, nos cortes de
   release, até o fim do corte W7 — pergunta 7): um `npm update -g` fecha o rail (o MANIFESTO por sha
   exato recusa o binário novo — não a faixa: o hook bloqueia as escritas L3+ e o pré-voo de fase 6
   aborta; as rodadas manuais não conferem o pin e rodariam o binário novo sem verificação); mitigação:
   Codex no 0.156.1
   (decisão do Owner, W3.1). **E no corte** (S361): o pin automático não cobre o passo 15 do release —
   um veredito com o Codex novo sai INVALID (pergunta 7 da W3). No plano B volta a janela entre `npm i -g` e o SIGN: mesma sentada + rodadas
   manuais congeladas.
5. **Publish do GA falha com o Node novo** (a rc não prova a troca OIDC) ⇒ rollback + re-tag.
   Mitigação: W4.3 prova o toolchain na rc; playbook do PLAN-158; W4 fora de janela de release.
6. **Edição da configuração do publicador confiável** ⇒ nasce só com «stage» e o passo 18 falha.
   Mitigação: não editar (W4.2).
7. **Varredura do CC apaga arquivos rotacionados da cadeia antes da W6.** Mitigação: backup agendado já
   (W6.1).
8. **Disputa de vagas e colisão de arquivos** com o PLAN-195 e as ondas A1–A7 do PLAN-183 (`install.sh`
   e o baseline do PLAN-185, `smoke-install.yml`/`ownership-nightly.yml`, `settings.json`, `INSTALL.md`,
   manifesto ADR-192). Mitigação: ordem das vagas decidida pelo Owner (regra de WIP do topo) e ordem
   explícita por arquivo no mapa de colisões, conferidas quando cada vaga abrir. Resta a W6
   (com data) atrás de uma fila longa: OQ-11; a W3b saiu dela — ocupa a 3.ª vaga inicial enquanto a W3
   espera o debate (Q8, S361).
9. **Árvore suja no SIGN e `CLAUDE.md` no teto.** O `CLAUDE.md` tem **39.912 bytes** depois do
   `e2e6bd1b` (S361: `wc -c`) — a 88 bytes do teto de 40.000; o gate reprova com `-ge`
   (`validate-governance.sh:632-633`: limite e teste), então a folga útil é de **87 bytes** (máximo
   39.999) — e a linha que estava não commitada já está commitada (árvore limpa na abertura da
   S361). **A poda do `CLAUDE.md` num fechamento vem ANTES do land da W3** (que torna falsa a linha do
   §4 sobre o Codex) **e de qualquer acréscimo de bytes ao arquivo.** O pacote que cria arquivo de ADR
   não é acréscimo (198 → 199 tem o mesmo tamanho; o `check-claude-md-claims.py` compara a contagem
   citada com o disco) e NÃO espera a poda — mas, com 87 bytes de folga útil, ele não acrescenta texto ao
   `CLAUDE.md` além da troca do número. Árvore suja ⇒ os moldes de SIGN abortam com
   modificação rastreada (ex.: `OWNER-PIN-SIGN.sh:330` do molde do Codex, lane `CX-13`) — árvore sem
   modificação rastreada (inclusive a poda, que é fechamento do CEO e deve estar commitada) é
   pré-condição de todo SIGN deste trem; a poda em si só é pré-condição da W3 e de acréscimos. Mesma classe: a W0 do PLAN-195 edita `docs/threat-model.md` em land livre, e o
   `check-threat-model-freshness.py` escreve nesse arquivo (lição S328). Mitigação: land livre de
   qualquer um dos três planos só com commit feito FORA de janela de SIGN — nenhuma edição sem commit
   quando uma assinatura estiver marcada (de preferência a W0 do PLAN-195 antes do SIGN da W1 daqui).
10. **Medições pagas gastam cota** (ordem do Owner de −1/3 de consumo). Mitigação: só o conjunto mínimo
    (W5.0, W6.0 e o re-teste da W5c), na vez de cada onda (decisão do Owner S359, «Só quando chegar a
    vez (Recomendado)»). **Freios do trabalho longo (S361, Q1/Q2):** a cota é COMPARTILHADA com as
    sessões paralelas do Owner em outros repositórios na mesma conta; nenhuma rodada nova do Codex acima
    de 80% do semanal; parar o Codex se o saldo de créditos cair; créditos NÃO são gastos (ver «How to
    continue»).
11. **Números envelhecem** (state dir: 218.974 entradas na triagem, lane `H-02`, e 219.527 horas
    depois, medido 2026-09-30; o Codex teve 5 minors estáveis em 12 dias, lane `CX-01`). **Re-medido na
    S361 (2026-10-01, ~20:08Z):** state dir com 223.100 entradas (222.872 com 0 bytes); `audit-log.errors`
    com 25.589 linhas; log rotado às 17:23:56Z; `audit-log-2026-10.jsonl` com a 1.ª quebra de cadeia na
    linha 7726 (a mesma da linha de base) e o `audit-log.jsonl` vivo INTACTO com 372 elos na medição do
    CEO; **relido às ~20:10Z, o vivo mostra uma 1.ª quebra na linha 441 (`agent_spawn`, 20:04:08Z, da
    sessão atual, no despacho paralelo de 4 redatores). Causa DIAGNOSTICADA pelo CEO na S361 (leitura do
    código e recomputação do HMAC de cada elo, sem escrita): é corrida no PRODUTOR, não adulteração.
    `.claude/hooks/audit_log.py:1267-1276` lê o elo anterior (`read_prev_hmac()`) e calcula o HMAC do
    `agent_spawn` FORA da trava; a trava (`FileLock`, `:1283`) só cobre o append e o `write_last_hmac`.
    Quando outro gravador anexa entre a leitura e o append (outro spawn em paralelo ou qualquer evento do
    `audit_emit`), o registro encadeia num elo velho e o `verify_chain` acusa `hmac_mismatch`. Prova: os 4
    `agent_spawn` quebrados do vivo (linhas 441, 442, 446 e 461) verificam contra um elo ANTERIOR ao
    imediato; os 3 de `audit-log-2026-10.jsonl` (a linha 7726 é um deles) e 1 de `audit-log-2026-09-7.jsonl`
    também. A quebra da linha 7726 que a S360 rotulou como «classe HMAC-483» é ESTA classe (2.ª+
    ocorrência ⇒ cura estrutural). **Não é classe nova:** é a «condição 67» assinada na v1.4.0-rc.1
    (`CHANGELOG.md:833-838`: o HMAC anterior é lido antes da trava do log, dois gravadores em paralelo
    encadeiam no mesmo predecessor e aparece uma quebra que ninguém causou); a docstring de
    `.claude/hooks/tests/test_two_writer_chain.py:13-16` diz que o teste de barreira multiprocesso
    «pertence à cura da rc.2», que nunca landou (achado do QA Architect, debate da W2, rodada 1). A
    cura aposenta a condição 67. Censo dos leitores de `read_prev_hmac()` fora de testes: o
    `audit_emit.py:2850` lê DENTRO da trava; o `check_precompact_continuity.py:432` só lê para um
    instantâneo; o `audit_log.py` é o ÚNICO gravador com a leitura fora da trava. Cura proposta: mover a
    leitura do elo e o cálculo do HMAC para dentro do `with FileLock(...)`, com teste de concorrência
    (N gravadores em paralelo ⇒ `verify_chain` íntegro) e controle vermelho no código atual. O arquivo é
    canônico (oráculo = 1) ⇒ pacote com cerimônia; o Owner decide a vaga (candidato natural: junto da W2,
    que já mexe no estado da auditoria). Até a cura, toda quebra num `agent_spawn` é presumida desta classe
    e conferida pela recomputação contra os elos anteriores.** Mitigação: re-medir no início de cada onda.
12. **Evidência de CI some:** runs passam a ser apagados após 90 dias a partir de 2026-10-01 (lane
    `DEP-07`). Mitigação: copiar para o LEDGER o que for evidência (ids, conclusão, datas).
13. **Instrumento vs. modo auto do CC 2.1.281+:** `rm` com alvo em variável é negado em 2 min sem
    resposta ⇒ limpeza confinada trava e o disco enche. Mitigação: `shutil.rmtree` confinado + piso de `df`.
    **Estado na S361 (2026-10-01):** o CEO relatou que o reboot limpou o lixo antigo do `$TMPDIR` (sobram só
    os arquivos das suítes rodando em outros repositórios); na leitura do redator, 3.428 entradas no topo
    do `$TMPDIR` e 268 GiB livres no contêiner APFS (relido no fim da S361: 256 GiB livres; o volume de dados,
    `/System/Volumes/Data`, onde ficam o `$TMPDIR` e os clones, está a ~72% de uso — os 5% que o `df -h /`
    mostra são do volume de sistema selado e não medem este risco) — quem criou as entradas não foi conferido.
14. **O debate único (W2, W3 e W5c) envelhece** até a vez da W2 e da W5c. Mitigação: re-medir no
    início de cada onda (risco 11) e reabrir só a parte afetada se os números mudarem.
15. **Referências cruzadas por número de linha envelhecem** a cada revisão (o PLAN-183 citava linhas
    deste arquivo que já mudaram). Mitigação: entre os três planos, citar pela seção («Regra de WIP»,
    «W5b», «OQ-11») e nunca pelo número de linha; o CEO atualiza as citações do PLAN-183 na mesma
    sessão desta revisão.
16. **Adoção do Sonnet 5.5 (W5c)** mexe em ~40 espelhos de uma vez e no adapter live (dois HTTP 400
    conhecidos no 5.5 — lane `ANT-02`); não reduz custo (mesmo preço do Sonnet 5). Mitigação: pacote
    derivado por script (L3 `adopt-model.py`), exceção de tamanho declarada, controle vermelho→verde
    (W5c.4), re-teste pago com os mesmos testes antes do SIGN, debate com crítico de FinOps; a W6 vai
    antes no `settings.json`.

## Fora do escopo (dono em outro lugar)

- Guarda de Bash (classe GuardFall) e seus documentos de ameaça → **PLAN-195**.
- Achados de adopter A1–A7 → **ondas novas do PLAN-183**.
- PLAN-192/193 → done; PLAN-170 → abandoned; poda do CLAUDE.md; memória defasada → **CEO, no fechamento**
  (a poda do `CLAUDE.md` é, desde a S361, PRÉ-CONDIÇÃO do land da W3 — ver «Unidades que ganharam dono»
  abaixo e o risco 9).
- Vazamento de pastas temporárias das suítes de teste de um adopter local → **Owner, numa sessão do adopter**
  (o lado do framework é a L2).
- Backlog sem onda (candidatos a follow-up): 190-FU audit-actions; inventário da dívida «known-open»
  com dono (lane `F-DEBT`); regex de `-FOLLOWUP-` no `check_plan_edit.py:136`; classe FN-04 além do
  ledger (lane `F13`); `codex_invoke.py`/`council-audit.js` passando pela conferência do pin (lane
  `CX-04`), salvo se o debate da W3 os incluir (pergunta 6); [fixar modelo e esforço no argv do rail
  (lane `CX-07`) saiu daqui: entrou na W3, desenho do pin automático]; refresh do `model-deprecations.json`
  (parado desde 2026-06-12, lane `ANT-05`; a linha do `gpt-5.5` virou a W3b.3 — S361); vigia do Haiku
  4.5 (piso 2026-10-15; `model_routing.py:64-70`, lane `ANT-04` — passou para a W5.1 na S361); pins node20 e `ubuntu-22.04` (`tier-policy.yml`, `mutation-gate.yml`,
  `benchmarks.yml.template` — lanes `DEP-04..06`); rotação do `audit-log.errors` (lane `H-03`); vazamento
  de temporários dos testes do framework (lane `H-06`); `shadow-ci.yml` que nunca rodou (lane `H-12`);
  pilha OTEL inerte (lane `CC-03`); métrica da ordem de −1/3 (custo por tarefa com cache separado —
  agora com dono: este plano, decisão Q13-h da S361, abaixo).

**Unidades que ganharam dono neste plano na S361** — sem dono elas não entravam em onda nenhuma:

1. **Virada do ADR-191 para enforce** (`CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED` e `CEO_SPAWN_OVERLAP_GUARD`).
   Nenhum dos dois está armado: o primeiro não está no ambiente desta sessão, e nenhum dos dois consta do
   `.claude/settings.json`. A janela advisory começou em 2026-08-13 (land do Lote B; o
   `PLAN-178-mast-audit-substrate-adoption.md:337` registra a janela) e o PLAN-178 está `done`
   (`completed_at: 2026-08-20`). **Dono: este plano.** Entra como item LIVRE a medição
   would-block/TP-FP (**L5**, só leitura do log); a CERIMÔNIA da virada segue a decisão Q13(g) do Owner:
   medir primeiro, decidir depois.
2. **Hook `check_writer_lock.py` do PLAN-190, W2** — não existe (`ls .claude/hooks/check_writer_lock.py`
   falha, e o `_lib/writer_lock.py` também não existe; as 3 CLIs livres da W2 landaram em `6fec455b`).
   **Dono: este plano, na fila DEPOIS do núcleo da 1.4.3**, como item `measure-first` (advisory antes de
   enforce, `CEO_WRITER_LOCK_REQUIRED=1` só depois da janela; a especificação continua em
   `PLAN-190-autonomous-execution-recoverable.md`, W2).
3. **Poda do `CLAUDE.md` num fechamento** — pré-condição do land da W3 e de qualquer acréscimo ao
   arquivo (39.912 bytes, 87 de folga útil; risco 9). **Dono: o CEO**, no fechamento que antecede o land da W3.
4. **Cura da corrida no gravador do `agent_spawn`** (`.claude/hooks/audit_log.py`, oráculo = 1): ler o elo
   anterior e calcular o HMAC DENTRO da trava, com teste de N gravadores em paralelo e controle vermelho no
   código atual (diagnóstico no risco 11). **Dono: este plano**; pacote canônico com cerimônia, vaga e
   orçamento decididos pelo Owner (candidato natural: junto da W2, que já mexe no estado da auditoria;
   estimativa a firmar na abertura, ordem de 150-300k tokens com rail).

## Decisões do Owner — S361 (2026-10-01)

O Owner aceitou em bloco, no chat da S361 (2026-10-01), as recomendações do planejamento da S360.
Abaixo, só as decisões que tocam este plano: o que ficou decidido, em linguagem simples, e a seção
onde o plano foi alterado. As respostas às perguntas abertas (OQ) estão marcadas «RESPONDIDA» (a OQ-11, «PARCIALMENTE
RESPONDIDA») no lugar delas, em «Open questions».

- **Q1 — quando e em qual conta o trabalho longo começa.** Começa já (T0 = 2026-10-01, S361), na conta
  que estiver logada, SEM trocar de conta no meio, e só se o statusline mostrar o semanal ≤ 50% e a janela
  de 5 h ≤ 30% (o Owner declarou a cota dentro do limiar na S361; a cota é compartilhada com as sessões
  paralelas dele em outros repositórios). Perfil enxuto: ≤ 8 agentes vivos, W1 primeiro. Trocar de conta
  para fugir do limite fica FORA do plano (CLAUDE.md §4, «Quota sem trocar conta»). → «How to continue»
  (regras de operação) e risco 10.
- **Q2 — créditos do Codex.** NÃO gastar créditos. Freio: nenhuma rodada nova do Codex acima de 80% do
  semanal; parar o Codex se o saldo cair; concentrar as rodadas que contam depois do reset de 07/10; o
  Owner reduz o uso do app Codex em outro repositório durante o trabalho longo. → «How to continue» e
  risco 10.
- **Q3 — o PLAN-194 passa a «revisado» agora**, pela revisão no chat (PLAN-SCHEMA §4), com uma cláusula:
  W2, W3 e W5c ficam BLOQUEADAS até o PROCEED do debate único, e os must-fix dele valem por onda. →
  cabeçalho (`status`, `reviewed_at`, `reviewed_by`), «Approach» item 4, as seções da W2, da W3 e da W5c,
  «Orçamento» e «Blockers».
- **Q5 — como o ADR cabe no teto de 8 paths.** Emenda DENTRO do ADR existente só quando for aditiva;
  mudança semântica ganha arquivo de emenda (o caso provável da W2 e da W3). Pacotes que criam arquivo
  de ADR ou de emenda ganham uma 4.ª exceção ao teto: o índice e os documentos de contagem ficam fora da
  conta e são re-derivados no LAND, com UM pacote de ADR por vez, junto de um fechamento. O
  `CLAUDE.md:54` viaja no pacote. → «Regra de WIP» (4.ª exceção), mapa de colisões (leque de ADR,
  `CHANGELOG.md`) e linha do `CLAUDE.md` em «Paths × oráculo».
- **Q6 — prazo de 19/10 (Ubuntu 26.04).** O Owner fixa a imagem do runner «Ceo» em Ubuntu 24.04; a W1
  segue como planejada; fica autorizado ligar o colima e baixar a imagem `ubuntu:26.04` para a W0.1. →
  OQ-2, W0.1 e «Dependências» da W1.
- **Q7 — escopo da 1.4.3.** Núcleo de ~12–13 assinaturas (W1, W4, W3b e W6; parte A do PLAN-195; W7a do
  PLAN-183; W2; W5c depois da W2 se o debate fechar a tempo; W3 se o debate fechar, sem bloquear o corte;
  rc.1 + GA); a escolha entre 1.4.3 e 1.5.0 sai do diff do `SPEC/v1`; se a cota apertar, a W5c sai
  primeiro. → «Goal» e pré-condições da W7.
- **Q8 — a 3.ª vaga enquanto a W3 espera o debate.** A W3b ocupa a vaga e landa ANTES da W3 (as duas
  tocam `codex_cli_shape.py`); a W3b.0 landa antes, como item livre. → «Regra de WIP», OQ-11, W3b, W3 e
  mapa de colisões.
- **Q9 — perguntas abertas que travavam o núcleo.** OQ-5: aceitar a prova parcial do publish (a rc só
  prova Node e npm) e o playbook de rollback. OQ-7: o `--ceremony user` grava `defaultMode: manual`.
  OQ-8, com TROCA: backup agendado como proteção principal, ensaio de restaurar e verificar (com a
  decisão sobre a chave HMAC) e 3650 neste repositório só como complemento. OQ-10: o corte fica neste
  plano. OQ-14: sandbox, retenção e W5c no mesmo pacote do `settings.json` só se ficarem prontos juntos
  antes de ~21/11. → «Open questions» (marcadas RESPONDIDA), W4, W5b, W6 e «Orçamento».
- **Q11 — ambiente do revisor Codex até a W3.** O Owner fecha o app ChatGPT/Codex nas janelas de rail e
  desliga `memories` no config global; o pré-voo de cada rodada registra o sha do config, o modelo, o
  esforço e `memories` — se mudou, é «instrumento mudou» e a rodada não conta; o `gpt-6-astra` é tratado
  como modelo novo e re-testado no 1.º pacote. → W3 («Base do argv fixo») e «How to continue».
- **Q12 — onde ficam as sombras dos builders.** Em `/private/tmp/claude-501/<sessão>/` (já liberado no
  modo auto), com checkpoint de cada pacote copiado para `~/.claude/projects/<slug>/s360-packs/` ao fim
  de cada fase; instalação automática do macOS desligada durante o trabalho longo; o Owner liga o auto
  no início; antes do fan-out, 1 builder de teste faz Write e `git worktree add` na sombra. O
  `/night-mode` não entra. → «How to continue» (regras de operação).
- **Q14 — versão do Claude Code durante o trabalho longo.** Congelada durante cada onda e atualizada só
  entre ondas, relendo a seção nova do CHANGELOG. Rota escolhida (lida no binário 2.1.287):
  `DISABLE_AUTOUPDATER=1` no `env` do settings do USUÁRIO, que o Owner aplica — em instalação `native`
  (a desta máquina) o `autoUpdates: false` só vale se `autoUpdatesProtectedForNative` não for `true`. →
  W5 («Objetivo»), «How to continue» e `external_wait`.
- **Q13-g — virada do ADR-191 para enforce.** Medir a tabela would-block/TP-FP como item livre e decidir
  depois. → «Fora do escopo» (unidade 1) e L5.
- **Q13-h — métrica da ordem de −1/3 de tokens.** Custo por pacote ACEITO (landado), com tokens de
  cache separados dos frescos, medido no início e no fim de cada onda; 1.º ponto: o planejamento S360,
  US$ 162,64 (medido pelo CEO; a janela fechada 15:00Z–19:00Z, relida na S361, dá US$ 166,77 — a
  janela exata do planejamento não foi reconstruída). Até a W5c, o `ceo-cost-transcripts.py` reporta
  US$ 0 para o `claude-sonnet-5-5` (modelo sem linha de preço). → «Fora do escopo» (backlog com dono) e «How to continue».

## Open questions

As perguntas que o Owner já respondeu na S359 (2026-09-30) saíram daqui e estão RESOLVIDAS na tabela
«Decisões do Owner» do Context, com a frase exata: a antiga OQ-1 (piso do Python — «Manter 3.9
(Recomendado)»), a antiga OQ-3 (versão do Codex — perdeu o sentido com o pin automático, «Pin
automático verificado (Recomendado)»; «nunca alpha» virou a pergunta 4 do debate da W3), a antiga
OQ-4 (medições pagas — «Só quando chegar a vez (Recomendado)»), a antiga **OQ-6** (Sonnet 5.5 —
«Adotar»; a W5c virou adoção), a antiga **OQ-9** (limpeza dos ~219 mil arquivos vazios — «Script
pronto, você roda depois (Recomendado)») e a antiga **OQ-13** (3.ª vaga — «Codex automático, depois
adopter (Recomendado)»). Os números das outras ficam iguais, para não quebrar referências. Cada
pergunta que resta traz a recomendação do CEO, em linguagem simples. **Na S361 (2026-10-01) o Owner
aceitou em bloco as recomendações do planejamento S360**: as perguntas que essas decisões fecham ficam no
lugar, marcadas «RESPONDIDA 2026-10-01» — a OQ-11, só «PARCIALMENTE RESPONDIDA» (a Q8 cobre apenas a
exceção da W3b) — (a lista das decisões está em «Decisões do Owner — S361»).

- **OQ-2 — Runner «Ceo». [RESPONDIDA 2026-10-01 pela Q6: sim.]** Fixar já a imagem dele em Ubuntu 24.04
  nas configurações da organização (sem código)? **Recomendação: sim, antes de 19/10.** É uma rede de
  segurança; a W1 continua. **Resposta (Owner, S361):** o Owner fixa o runner «Ceo» na imagem 2295
  «Ubuntu 24.04»; a W1 segue como planejada; fica autorizado ligar o colima e baixar a imagem
  `ubuntu:26.04` para a W0.1.
- **OQ-5 — Prova do publish. [RESPONDIDA 2026-10-01 pela Q9: sim.]** A rc só consegue provar o Node e o
  npm, não a publicação em si (que só acontece no GA). Aceita a prova parcial + o playbook de rollback?
  **Recomendação: sim.** **Resposta (Owner, S361):** aceita; a W4 destrava.
- **OQ-7 — Instalação `--ceremony user`. [RESPONDIDA 2026-10-01 pela Q9: gravar `manual`.]** Gravar
  `defaultMode: "manual"` ou deixar herdar o modo auto do Claude Code? **Recomendação: gravar `manual`**
  (mesma postura do framework e dos 3 adopters). **Resposta (Owner, S361):** gravar `manual`; a W5b
  destrava.
- **OQ-8 — Retenção. [RESPONDIDA 2026-10-01 pela Q9, COM TROCA em relação à recomendação abaixo.]**
  **Recomendação original: agendar o backup já (W6.1) e, depois da isca (W6.0), subir o valor deste
  repositório para 3650**; o padrão dos adopters fica como está, com a mitigação no `INSTALL.md`.
  **Resposta (Owner, S361), com a troca:** o fato novo é que a varredura usa o `cleanupPeriodDays` da
  sessão QUE VARRE e alcança todos os projetos (relatado: 26 raízes com 90 na máquina), então subir só
  este repositório para 3650 não protege a cadeia. Vale: (1) backup agendado (W6.1) como proteção
  PRINCIPAL; (2) ensaio de restaurar e verificar, com a decisão sobre guardar a chave HMAC ficando com o
  Owner; (3) 3650 neste repositório só como COMPLEMENTO, depois da isca W6.0. O padrão dos adopters fica
  como está, com a mitigação no `INSTALL.md`. A W6.2 destrava.
- **OQ-10 — Corte dentro deste plano. [RESPONDIDA 2026-10-01 pela Q9: sim.]** O corte da 1.4.3 (W7)
  fica aqui? **Recomendação: sim** (é onde os P2 do kit se curam). **Resposta (Owner, S361):** o corte
  fica neste plano.
- **OQ-11 — Ordem do que vem depois da fila já decidida. [PARCIALMENTE RESPONDIDA 2026-10-01 pela Q8:
  só a exceção da W3b na 3.ª vaga, abaixo; a ordem (a)–(f) e o empate seguem como RECOMENDAÇÃO do CEO,
  em aberto para o Owner.]** Já decidido pelo Owner (ver «Regra de
  WIP»): W1 → parte A do PLAN-195 → W3; depois a W7a do PLAN-183 na vaga da W1; depois a W2; a W7b do
  PLAN-183 logo depois da W7a; a W5c depois da W2 (salvo se o debate pedir antes). **Recomendação para
  o resto, nesta ordem:** (a) **parte B do PLAN-195** (W2 de lá) na primeira vaga livre depois disso —
  mesmo arquivo da parte A, então só depois do land dela; (b) **W4** antes da rc.1 da W7; (c) **W5a e
  W5b** depois da W5.0, com a W5b antes da W1a/W1b do PLAN-183 (mesmo `install.sh` — mapa de
  colisões); (d) **W3 do PLAN-195** (ligar o sandbox) só se você decidir ligar depois da medição, e
  só depois da W6 no `.claude/settings.json` (OQ-14); (e) **W8** se sobrar vaga (OQ-12); (f) W1a/W1b,
  W9, W8 e W10 do PLAN-183 pela ordem interna de lá. **Itens com data furam a fila:** a **W6**
  (retenção, ~2026-11-21) e a **W3b** (ids OpenAI, 2026-12-11) passam à frente da W7b, da W5c e de
  tudo em (a)–(f) se a fila não as alcançar a tempo — nunca à frente das 3 iniciais, da W7a nem da W2.
  **Exceção aprovada pelo Owner na S361 (Q8, 2026-10-01) — emenda a regra «nunca à frente das 3
  iniciais»:** enquanto a W3 (dona da 3.ª vaga) espera o PROCEED do debate único, a **W3b** (ids OpenAI
  que se aposentam; aviso a partir de 12/10, prazo duro 11/12) OCUPA a 3.ª vaga e landa ANTES da W3, porque
  as duas tocam `codex_cli_shape.py`; a **W3b.0** (precisão do detector, criada na S359) landa antes dela,
  como item livre. A W3 continua sendo a dona da vaga e a retoma quando o debate fechar.
  **Empate a decidir:** se a W7a landar antes de a W2 ter vaga, a vaga da W7a vai para a W2 (ordem
  literal da sua decisão) ou para a W7b («logo depois da W7a»)? **Recomendação: W2** — é a ordem
  literal; a W7b pega a vaga seguinte.
- **OQ-12 — TLC (W8) neste trem?** **Recomendação: sim se sobrar vaga;** senão, declarar no corte.
- **OQ-14 — Sandbox e retenção no mesmo pacote? [RESPONDIDA 2026-10-01 pela Q9: só se ficarem prontos
  juntos antes de ~21/11 — sandbox, retenção E, agora, a W5c; a W6 não espera.]** Você decidiu «Medir antes de ligar (Recomendado)»;
  fica aberto, no PLAN-195, só «ligar ou não depois da medição». Se a resposta for ligar (W3 do
  PLAN-195), essa mudança no `.claude/settings.json` pode ir no mesmo pacote da retenção (W6 daqui),
  para economizar uma assinatura? Hoje o PLAN-195 prevê cerimônia própria (W3 de lá). O mesmo arquivo
  também é tocado pela W5c (adoção do Sonnet 5.5). **Recomendação: sim, mas só se as duas decisões
  ficarem prontas juntas antes de ~2026-11-21;** a W6 vai primeiro e não espera o sandbox nem a W5c,
  porque a retenção tem data.

## Blockers

- **Cláusula do Owner (S361, Q3): W2, W3 e W5c estão BLOQUEADAS até o PROCEED do debate único; os
  must-fix dele valem por onda.** As demais ondas não dependem do debate.
- W1: medição W0.1/W0.2 (OQ-2 respondida na S361: o Owner fixa a imagem do runner). Prazo externo
  2026-10-19.
- W2: **BLOQUEADA** — debate único do plano (PROCEED); vaga seguinte à da W7a do PLAN-183 (ordem
  decidida); a limpeza W2.6 é alívio rodado pelo Owner, não bloqueia.
- W3: **BLOQUEADA** — debate único do plano (PROCEED) e ADR-182-AMEND-1; 3.ª vaga inicial (decidida;
  ocupada pela W3b até o debate fechar — Q8); a W3b landada antes (mesmo `codex_cli_shape.py`); árvore
  sem modificação rastreada no SIGN (na abertura da S361 a árvore estava limpa; a poda do `CLAUDE.md`
  num fechamento vem ANTES do land da W3 — risco 9); L1 recomendado.
- W5c: **BLOQUEADA** — debate único do plano (PROCEED); re-teste pago na vez; W6 landada
  antes (`.claude/settings.json`) — ou no MESMO pacote, se a OQ-14 se aplicar (prontos juntos antes de
  ~21/11); vaga depois da W2.
- W7: W4 landada; pacote de ADR e W7 nunca em voo juntos (`CHANGELOG.md`).

## Next

0. **1.º commit de trabalho:** cria a pasta `.claude/plans/PLAN-194/` e o `LEDGER.md` (os dois ainda
   não existem) e passa o plano de `reviewed` a `executing` (autoportão, PLAN-SCHEMA §4).
1. W0.1 (medição para a W1; a W0.2 já está medida e falta só gravá-la no LEDGER), sem cota paga.
2. L1 (livre) — antes da W3; **W3b.0** (livre) — antes da W3b.
3. Pacote da W1 para cerimônia (W1 primeiro — Q1).
4. **W3b** na 3.ª vaga (Q8) — pode correr em paralelo, dentro da regra de WIP, mas a W1 tem precedência.
5. Proposta do debate único W2 + W3 + W5c (não ocupa vaga; é o portão das três ondas bloqueadas — Q3);
   limpeza única W2.6 quando o Owner rodar o script entregue (fora do repositório, todas as sessões do
   Claude fechadas).

## How to continue

Primeira mensagem de uma sessão nova: «Ler o PLAN-194 e o `.claude/plans/PLAN-194/LEDGER.md` (a pasta
`PLAN-194/` e o LEDGER só existem depois do 1.º commit de trabalho); conferir
`git log --oneline -5`, `gh run list --limit 5`, `npm view @openai/codex dist-tags` (a `latest` era a 0.160.0 em 2026-10-01 às ~21:30Z; muda com
frequência, com várias estáveis por semana — conferir), `codex --version` (deve seguir 0.156.1 até o fim
do corte W7, mesmo com a W3 landada, salvo re-pin do manifesto no kit — pergunta 7 da W3),
`claude --version` (2.1.287 em 2026-10-01; congelado durante cada onda — Q14), `df -h /System/Volumes/Data`
(o volume de dados, onde ficam o `$TMPDIR` e os clones — risco 13); ver quais vagas canônicas estão em voo
(PLAN-194, PLAN-195, PLAN-183) e seguir a ordem da regra de WIP do topo. Se hoje ≥ 2026-10-19 e a W1 não
landou: parar tudo e fazer a W1.»

**Regras de operação do trabalho longo — decisões do Owner S361 (2026-10-01).**

- **Início e cota (Q1).** Condição de início, válida só no T0 (2026-10-01, S361): statusline com
  semanal ≤ 50% e janela de 5 h ≤ 30% — cumprida, por declaração do Owner. Nas ondas seguintes não há
  limiar da Q1: valem o freio da Q2 (Codex, abaixo), o teto de agentes vivos e a leitura da cota no
  início de cada onda (medição, sem limiar decidido; se a cota apertar, a W5c sai primeiro — Q7). Perfil enxuto: ≤ 8
  agentes vivos — a limpeza da W2.6 (≈ 222 mil arquivos vazios) segue PENDENTE, porque exige todas as
  sessões do Claude fechadas e o Owner tem sessões abertas em outros repositórios; até ela se provar,
  vale o teto de 8. W1 primeiro. SEM trocar de conta durante o trabalho (CLAUDE.md §4, «Quota sem
  trocar conta»).
- **Codex e créditos (Q2).** NÃO gastar créditos. Nenhuma rodada nova do Codex acima de 80% da janela
  semanal (`used_percent`); parar o Codex se o saldo de créditos cair; concentrar as rodadas que
  contam depois do reset de 07/10 (13:28Z); o Owner reduz o uso do app Codex em outro repositório
  durante o trabalho longo.
- **Ambiente do revisor Codex (Q11).** O Owner fecha o app ChatGPT/Codex nas janelas de rail e
  desliga `memories` no config global (`~/.codex/config.toml`). O pré-voo de cada rodada registra o sha
  do config, o modelo, o esforço e `memories`; se algo mudou, é «instrumento mudou» e a rodada não
  conta. O `gpt-6-astra` é MODELO NOVO e é re-testado no 1.º pacote (CLAUDE.md §4, «Modelo novo ⇒
  RE-TESTAR»).
- **Sombras dos builders (Q12).** Em `/private/tmp/claude-501/<sessão>/` (o modo auto já libera escrita
  e `git worktree add` ali), com o checkpoint de cada pacote copiado para
  `~/.claude/projects/<slug>/s360-packs/` ao fim de cada fase (cobre um reboot inesperado); instalação
  automática do macOS desligada durante o trabalho longo; o Owner liga o auto no início; antes do
  fan-out, 1 builder de teste faz Write e `git worktree add` na sombra — na S361 a sonda do CEO (1
  subagente com `model: sonnet`) escreveu na raiz de sombras e fez `git worktree add --detach` e
  `remove` sem prompt nem bloqueio. O agente NÃO alarga a própria lista de permissões; o `/night-mode`
  não entra.
- **Versão do Claude Code (Q14).** Congelada durante cada onda e atualizada só entre ondas, com
  `claude update`, relendo a seção nova do CHANGELOG. Rota: `DISABLE_AUTOUPDATER=1` no `env` do
  settings do USUÁRIO, que o Owner aplica (lido no binário 2.1.287: o atualizador desliga com
  `DISABLE_UPDATES`, com `DISABLE_AUTOUPDATER` verdadeiro ou com `autoUpdates: false`; em instalação
  `native` — a desta máquina — o `autoUpdates: false` só vale se `autoUpdatesProtectedForNative` não
  for `true`).
- **Métrica de tokens (Q13-h; ordem de −1/3).** Custo por pacote ACEITO (landado), com os tokens de
  cache separados dos frescos, medido no início e no fim de cada onda; 1.º ponto: o planejamento S360
  (US$ 162,64, medido pelo CEO). Instrumento: `ceo-cost-transcripts.py --by role,model`.

## Success criteria

- [ ] Validate verde em push e no nightly depois de 2026-10-19, com a perna 3.9 viva. — Check: gh run list --workflow validate.yml --limit 5 --json conclusion
- [ ] State dir sem acúmulo por PID depois de um dia de uso normal, sem `drain canonical lock timeout` sob a carga da W0.5. O teste unitário não basta: a prova é no VIVO, com as sessões do Claude paradas (evita corrida com arquivo sendo apagado) — (1) arquivos de 0 bytes nos 3 padrões no state dir INTEIRO, inclusive o subdiretório novo da W2.3, abaixo do limiar fixado no ADR-055-AMEND-4 (proposta para o debate: ≤ 1% do medido hoje); (2) 0 linhas `drain canonical lock timeout` no `audit-log.errors` com carimbo depois do LAND (o arquivo não rotaciona — lane `H-03` —, por isso a janela). **Medido 2026-09-30 (vermelho):** 219.468 arquivos de 0 bytes nos 3 padrões, de 219.839 entradas; 19.568 linhas da classe no total, 2.980 só em 2026-09-30 (UTC). Números antes/depois no LEDGER. — Check: python3 -m pytest .claude/hooks/tests/test_spool_state_gc.py -q && python3 -c "import os,re,subprocess as s;d=s.check_output(['python3','.claude/hooks/_lib/runtime_paths.py','--state-dir'],text=True).strip();p=re.compile(r'^audit-(pending\.\d+\.journal(\.lock)?|spool\.\d+\.jsonl\.lock)$');print(sum(1 for r,_,fs in os.walk(os.path.join(d,'state')) for f in fs if p.match(f) and os.path.getsize(os.path.join(r,f))==0))" && awk -v t="<ISO do LAND, ex. 2026-11-01T00:00:00Z>" '$1 >= t && /drain canonical lock timeout/' "$(python3 .claude/hooks/_lib/runtime_paths.py --state-dir)/audit-log.errors" | wc -l
- [ ] Rail com pin automático verificado (no hook do rail; os cortes de release são a pergunta 7 da W3): versão nova COM procedência ⇒ `verified` sem assinatura nova do Owner; SEM procedência ⇒ recusada (W3.4). — Check: python3 .claude/hooks/check_pair_rail.py --verify-codex-pin "$(command -v codex)"
- [ ] `check-model-deprecations.py --check --today 2026-10-13` = 0. — Check: python3 .claude/scripts/check-model-deprecations.py --check --today 2026-10-13
- [ ] Publish do GA 1.4.3 com Node ≥ 22.14 e npm exato. — Check: npm view ceo-orchestration version
- [ ] Textos do ADR-149/SUPPORT/doc de adopter alinhados ao CC ≥ 2.1.286 (instalado em 2026-10-01: 2.1.287), com data e substrato. — Check: python3 .claude/scripts/generate-available-models.py --check
- [ ] Sonnet 5.5 adotado pela emenda 4 do ADR-149 (W5c), com a linha de preço e o conjunto de vermelhos esperado sem achado novo, e o re-teste pago registrado no LEDGER. — Check: python3 .claude/scripts/generate-available-models.py --check && python3 .claude/scripts/check-model-currency.py --expected-reds .claude/data/model-currency-expected-reds.txt
- [ ] Backup agendado e ensaio de restaurar e verificar (W6.3) registrado no LEDGER, com paridade por arquivo e a decisão do Owner sobre a chave HMAC, antes de ~2026-11-21; `cleanupPeriodDays` decidido como complemento (o `--dry-run` abaixo não prova nem o agendamento nem o ensaio). — Check: bash .claude/scripts/ceo-backup.sh --dry-run
- [ ] GA v1.4.3 publicado (tag assinada, npm `latest=1.4.3`). — Check: npm view ceo-orchestration dist-tags

## Session history

- S359 (2026-09-30): triagem só-leitura pós-GA 1.4.2 (15 frentes); decisões do Owner (PLAN-194 =
  trem até a 1.4.3; PLAN-195 = guarda de Bash; A1–A7 no PLAN-183; fechamentos pelo CEO). Plano redigido
  em `draft`; oráculo rodado para todos os paths nomeados; state dir e `check-model-deprecations`
  re-medidos.
- S359 (2026-09-30, revisão pelos revisores): W3 reescrita como **pin automático verificado** (decisão
  do Owner que o rascunho omitia; re-pin manual vira plano B); antigas OQ-1/OQ-3/OQ-4 saíram (já
  decididas) e as sondas pagas foram para W5.0/W6.0; ordem das vagas W1 → 195-A → W3, W2 depois (OQ-13),
  com a limpeza única adiantada (OQ-9); debate único W2+W3; W5c entrou na lista de exceções do topo;
  Checks da W8, da L4 e do critério de sucesso da W2 trocados por medições que distinguem consertado
  de quebrado (run `36719886973` e state dir medidos); linha `.claude/settings.json` × PLAN-195 no
  mapa de colisões (OQ-14); oráculo rodado nos paths novos. Status inalterado (`draft`).
- S359 (2026-09-30, decisões do Owner aplicadas + checagem cruzada dos 3 planos): decisões registradas
  como RESOLVIDAS com a frase exata (estrutura, Python, publicação, sandbox, medições pagas, Codex,
  ordem das vagas, limpeza, Sonnet 5.5); antigas OQ-6, OQ-9 e OQ-13 saíram; ordem das vagas decidida
  (W1 → parte A do PLAN-195 → W3; W7a do PLAN-183 na vaga da W1; depois W2; W7b logo após a W7a);
  **W5c reescrita como ADOÇÃO** do Sonnet 5.5 (emenda 4 do ADR-149, linha de preço, re-teste pago na
  vez, debate L3 no debate único, exceção de tamanho declarada); OQ-11 com a parte B e a W3 do
  PLAN-195 em posição explícita; mapa de colisões com ordem por arquivo (`settings.json`, `install.sh`
  + baseline, `smoke-install.yml`/`ownership-nightly.yml`, manifesto ADR-192, `INSTALL.md`) e os
  espelhos gerados marcados como saída ignorada pelo git; citações de outros planos por nome de seção;
  caminhos da pasta privada do Owner retirados. Oráculo rodado nos paths novos
  (`ownership-nightly.yml`, `gate-scripts-manifest.txt` = 1; `INSTALL.md`, `budget-summary.py`,
  `ceo-cost-transcripts.py`, `success-receipt.py` = 0). Status inalterado (`draft`).
- S361 (2026-10-01): **`draft` → `reviewed`** por aceite em bloco do Owner, no chat, das recomendações
  do planejamento S360 (Q1 a Q14; as decisões que tocam este plano estão em «Decisões do Owner —
  S361»). Cláusula de bloqueio: W2, W3 e W5c BLOQUEADAS até o PROCEED do debate único, com os must-fix
  valendo por onda. Emendas de texto do planejamento aplicadas depois de conferir cada fato no disco:
  substrato do Codex (0.159.3 e, desde as 20:26Z, 0.160.0; o manifesto por sha exato, e não a faixa, fecha o rail), perguntas 2, 6 e
  7 da W3 (o pin automático não cobre os cortes), W3b.3 (gpt-5.5, a verificar), W5.0/W5.1 com o CC
  2.1.286/2.1.287, W6 redesenhada (backup como proteção principal), mapa de colisões com o leque de ADR
  e a 4.ª exceção ao teto, exceção da OQ-11 para a W3b, L2 estendida, L5 nova, backlog com dono e números
  de estado. OQ-2, OQ-5, OQ-7, OQ-8, OQ-10 e OQ-14 marcadas RESPONDIDA; OQ-11 PARCIALMENTE RESPONDIDA (só a exceção da Q8; a ordem (a)–(f) e o empate seguem abertos). Nenhum marcador de
  esclarecimento vivo (PLAN-SCHEMA §14) no texto. A passagem a `executing` fica para o 1.º commit de
  trabalho.

## Reference links

- Síntese e retorno das 15 frentes da S359: evidência privada do Owner, fora do repositório.
- Memórias: `project-s359-urgency-triage`, `project-s358-ga142-kit-build`,
  `feedback-workflow-agents-must-clean-their-clones`, `reference-cc-2-1-280-model-effort-semantics`
  (defasada no Ultracode).
- PLAN-193 (molde do re-pin, do kit e da wave-opus55); PLAN-183 (A1–A7); PLAN-195 (guarda de Bash);
  PLAN-176 (currency de modelos; reconciliar W3a com a L2).
- ADR-055 e emendas; ADR-081 (tokens como unidade de tempo); ADR-103 (hold); ADR-149 (e a emenda 4
  proposta pela W5c); ADR-163;
  ADR-182 §5 (e a emenda proposta pela W3); ADR-192.
- Layout do debate: `.claude/commands/debate.md:46`; `.claude/plans/DEBATE-SCHEMA.md`.
- Externo: actions/runner-images#14748 (Ubuntu 26.04); docs.npmjs.com/trusted-publishers; changelog do
  GitHub de 2026-09-03 (várias configurações de publicador confiável).
