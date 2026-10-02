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
budget_tokens: "estimado (contexto do CEO; subagentes à parte). Trem da 1.4.3 depois da S362 (2026-10-02), total ~5,7-11,1 M: re-pin manual do Codex 0.160.0 (RP: sonda, texto, pacote gerado, ensaio, rail) 300-600k; W2 (U2-A a U2-D + livres: verificadores do spool, estresse, W0.5, script da W2.6, AMEND-4 condensado) 1,8-3,2 M; W7a do PLAN-183 300-700k; W4 + W5.0/W5a/W5b/W5.1 + W6 800k-1,5 M + isca paga mínima da W6.0 + sondas pagas da W5.0; W5c (adoção do Sonnet 5.5) 1,5-3,0 M + re-teste pago de ~US$ 15-30; corte (derivadores do kit, metadados do release, CHANGELOG, kit, rc.1, kit do GA, GA) 900k-1,9 M; livres (cura do teste instável, textos, LEDGER) 100-200k. Já gastos, fora da conta: W0, W1, W3b, W2.0 e o debate. Fora da 1.4.3 (vão para a 1.4.4): W3 (pin automático) 1,6-2,8 M em 3 a 4 sessões, com o pacote de kernel de registro de ações; o PLAN-195; W8 50-150k; L2 restante e L3 a L5"
budget_sessions: "8-12 (estimado na S362; várias em paralelo; pelo menos 3 sessões do CEO, por dois fechamentos obrigatórios — a W2.6 e o U2-D; cada assinatura do Owner é uma parada; eram 6-11 com a W3 dentro)"
context_risk: high
external_wait: "GitHub: ubuntu-latest vira Ubuntu 26.04 de 2026-10-19 a 2026-11-19 (actions/runner-images#14748). Owner: fixar a imagem do runner Ceo em Ubuntu 24.04 nas configurações da organização (OQ-2, decidida na S361); agendar o `ceo-backup.sh` (W6.1); congelar o Claude Code durante cada onda com `DISABLE_AUTOUPDATER=1` no `env` do settings do USUÁRIO (S361, Q14); medições pagas só na vez de cada onda (W5.0, W6.0 e o re-teste da W5c — decisão S359); rodar o script de limpeza única da W2.6 com todas as sessões do Claude fechadas (decisão S359; recomendação das rodadas 1 e 2 do debate, pendente de decisão do Owner (S361): basta fechar as sessões DESTE projeto, e rodar já); **a W2.6 é RECORRENTE sob a regra de travas T1** (a cada ~2 a 4 semanas de uso intenso, quando o `/ceo-boot` acusar ≥ 100 mil travas — operação do Owner); decidir as OQs que restam (OQ-11 — o resto da ordem (a)–(f) e o empate W2 × W7b — e OQ-12) e as decisões pendentes do debate (seção «Decisões pendentes do Owner — S361 (rodada 1 do debate)», atualizada pela rodada 2); carência de 48 h, no relógio do npm, entre a publicação de uma versão do Codex e a elegibilidade dela para o pin automático (W3, depois da 1.4.3); **janela curta de manutenção em cada promoção do Codex da W3, com as rodadas de rail paradas (quiesce)**; assinar o re-pin manual do Codex (RP), W1, W2, W3b, W4, W5 (inclusive a W5c), W6, W8 e os cortes rc.1/GA; hold de 24 h entre rc e GA (ADR-103). Codex — decisão do Owner S362 (2026-10-02): re-pin MANUAL 0.156.1 → 0.160.0 como 1.ª tarefa do trem (o plano B da W3, pelo molde `.claude/plans/PLAN-193/codex-pin-0156/OWNER-PIN-SIGN.sh` com `--ga-tag v1.4.2`); o Owner instala a 0.160.0 e assina o pacote na MESMA sentada (sábado 2026-10-03); antes dela, 0.156.1; depois dela, 0.160.0; nunca npm update -g. A W3 (pin automático) fica para DEPOIS da 1.4.3: a decisão 3 não foi tomada, e o VETO de Segurança segue levantado. O kit da 1.4.3 corre só pela rota 1 do runner do re-pass; a rota 2 vira recusa nomeada. Retenção: arquivo rotacionado mais antigo da cadeia completa 90 dias por volta de 2026-11-21. OpenAI: gpt-5/o3 aposentam em 2026-12-11."
eta_calendar: "W1 antes de 2026-10-19 (prazo externo; landada em c54934d8); backup agendado e W6 antes de ~2026-11-21; W3b antes de 2026-12-11 (landada); re-pin manual do Codex: SIGN do Owner no sábado 2026-10-03; linha de corte: a derivação do kit começa no máximo em 2026-10-11; GA v1.4.3 = max(assinaturas do Owner, hold de 24 h rc→GA) — estimativa da S362, sem data prometida: 2026-10-11 no cenário otimista, 2026-10-13 a 2026-10-15 no realista"
tags: [maintenance, release, ci, ubuntu-26-04, audit-spool, codex-pin, npm, claude-code-substrate, retention]
---

> **Regra de WIP (trabalho em voo) — vale para este plano inteiro e divide as vagas com o PLAN-183
> (o PLAN-195 inteiro foi para a 1.4.4 e nada canônico dele landa antes do GA — decisão do Owner S362).**
> No máximo **4 pacotes canônicos em voo** ao mesmo tempo (eram 3; o Owner subiu para 4 na ratificação de
> 2026-10-02 — «Decisões do Owner — S362»); cada pacote com **≤ 400 linhas e ≤ 8 paths**. Um pacote está
> «em voo» da abertura da sombra canônica até o land; NÃO contam como em voo os derivadores em
> `.claude/plans/` (oráculo 0), os testes livres e a pré-revisão só com Claude. **Exceções — só estas quatro, todas geradas por ferramenta:**
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
> da W2 (contra o ADR-055-AMEND-3) e da W3 (contra o ADR-182), confirmado pela rodada 1 do debate:
> arquivo de emenda próprio nos dois (`ADR-055-AMEND-4` e `ADR-182-AMEND-1`), com rascunhos PROPOSED
> em `.claude/plans/PLAN-194/debate/round-2/` antes do pacote de ADR. **(5) Proposta do CEO (S361),
> pendente:** o pacote **1a da W3 com 9 paths no ramo (ii)** — o 9.º é o `.claude/scripts/env-inventory.json`,
> dado de inventário que a condição 13/17 do consenso r3 exige no MESMO pacote; é ratificada junto da
> decisão pendente 3 se o Owner escrever (ii). No ramo (i) o 1a tem 8 paths e a exceção não existe.
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
> **Emenda S362 (2026-10-02):** a ordem acima é histórica. As 4 vagas da 1.4.3 (decisões em «Decisões do
> Owner — S362»): vaga 1 = re-pin manual do Codex (RP) → código da W7a do PLAN-183; vaga 2 = os
> 4 pacotes da W2 em série (U2-A → U2-B → U2-C → U2-D); vaga 3 = W6.2 → W5b; vaga 4 = W4 → emenda do
> ADR-158 da W7a → W5c → metadados do release (RM). A parte A do PLAN-195, a W3 e a W7b do PLAN-183 saíram
> da 1.4.3.
>
> **Emenda da rodada 1 do debate (S361).** Dois pacotes canônicos novos entram na conta de vagas, ambos
> sob a regra de ≤ 3 em voo (≤ 4 desde a S362), ≤ 400 linhas e ≤ 8 paths. (1) A **cura da corrida do `agent_spawn`**
> (`audit_log.py` e testes; pré-condição do SIGN da W2): vaga e orçamento são decisão do Owner —
> recomendação do CEO, **pendente de decisão do Owner (S361)**: pacote próprio, o primeiro na vaga da W2
> ou na primeira vaga que abrir antes. (2) O **pacote de kernel de registro de ações** (`audit_emit.py`;
> o evento durável da aceitação do pin automático): vai em série com a W1a do PLAN-195, que pode tocar o
> mesmo arquivo (colisão do mapa), e landa ANTES da W3.6. **Rodadas 2 e 3:** a W3 passa a pacotes canônicos
> em série — **[1c]** (guarda do registro e das fontes do verificador; PRIMEIRO da fila, só se o 1b passar
> de 8 paths), **1b** (AMEND-1 + núcleo), **1a** (verificador; 9 paths no ramo (ii) com o
> inventário de ambiente — 5.ª exceção, proposta junto da decisão 3 — e 8 no (i); recontagem na abertura) e **2** (argv, chamadores livres e mensagem do Gate 4) — mais o pacote de
> kernel; a W2 fica liberada e não espera a W3.

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
| Codex: «Pin automático verificado (Recomendado)» (torna sem sentido a antiga OQ-3) | **W3 reescrita**: substitui o re-pin manual, que ficou como plano B. **S362 (2026-10-02):** o Owner ativou o plano B como 1.ª tarefa do trem — re-pin manual 0.156.1 → 0.160.0 — e a W3 foi para depois da 1.4.3 (a decisão 3 não foi tomada; o VETO de Segurança segue levantado). Em nenhum momento `npm update -g` |
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
| W3 e re-pin manual | Codex pinado 0.156.1; estável do npm: a **0.159.3** (publicada em 2026-09-30T23:02Z) era a `latest` na medição de ~20:08Z de 2026-10-01, e a **0.160.0 saiu em 2026-10-01T20:26:19Z e virou `latest`** (relido às ~21:30Z; a 0.159.2 da triagem S359 já não era a última); quem fecha o rail é o MANIFESTO por sha exato (`codex-cli-pin-manifest.json`), não a faixa `>=0.128.0,<0.157.0` do `codex-cli-pin.txt` (a faixa não fecha o rail em execução — o pré-voo, só na fase 6, apenas exige que o arquivo exista —, é gate de versão do validador do veredito de release) ⇒ atualizar o CLI antes de re-pinar FECHA o rail; **19 versões estáveis em setembro, 7 depois da 0.156.1 até a 0.159.3; a 0.160.0, de outubro, é a 8.ª** (a tag `alpha` estava em 0.161.0-alpha.13 na S361); **re-medido em 2026-10-02 ~19:43Z (S362):** `latest` = 0.160.0, nenhuma 0.160.x posterior, `alpha` = 0.162.0-alpha.7 ⇒ o re-pin manual da 1.4.3 é para a 0.160.0; atestado SLSA v1 presente em 0.156.1, 0.159.2, **0.159.3** e **0.160.0** (conferido também nos pacotes da plataforma `@openai/codex@0.159.3-darwin-arm64` e `@openai/codex@0.160.0-darwin-arm64`) | `.claude/governance/codex-cli-pin.txt:147`; `check_pair_rail.py:589-747`, `:1488-1510`; `pair-rail-gate.sh:182-220` (Gate 4, só na fase 6); `npm view @openai/codex time` e `dist` (S361); `npm view @openai/codex dist-tags` e `versions` (S362); lanes `CX-01`, `CX-03`; memória `project-s359-urgency-triage` |
| W3b | `check-model-deprecations.py --check` sai **1** na árvore viva a partir de 2026-10-12/13 (gpt-5/o3 aposentam em 2026-12-11) | medido 2026-09-30 com `--today 2026-10-13` (rc 1) e sem `--today` (rc 0); lane `CC285-08` |
| W4 | publish com Node 20 e npm em faixa flutuante; a doc do npm exige Node ≥ 22.14 para publicação sem token | `.github/workflows/npm-publish.yml:245-250`, `:260`; lane `DEP-02` |
| W4 | tags rc **pulam** o job de publish (regra que sustenta carga, fixada por teste) | `npm-publish.yml:29-30`, `:227`; `.claude/governance/npm-trusted-publisher.txt:5-7` |
| W5 | CC 2.1.284: Ultracode não força mais xhigh; Sonnet 5.5 (`claude-sonnet-5-5`, US$ 2/10) virou o Sonnet padrão e entra pelo prefixo `claude-sonnet-5`; sessão sem `permissions.defaultMode` nasce em auto. CC 2.1.285: Bash em background morre em 30 min (máx. 2 h). CC 2.1.286: o watchdog do Workflow passou de 180 s fixos com 1+5 tentativas para 600 s derivados, pausado com ferramenta em voo (medido no binário na S360; CLAUDE.md §4). **CC 2.1.287 é o instalado**: o Claude Code se auto-atualizou de 2.1.286 para 2.1.287 às 2026-10-01T18:21:01Z — as medições da S360 são do 2.1.286, e a seção nova do CHANGELOG precisa ser relida a cada versão (itens que tocam este plano na W5.0, W5.1 e W5c) | lanes `CC-01`, `CC-02`, `CC-04`, `CC285-01`, `CC285-02`, `ANT-01`; `~/.claude/.last-update-result.json`; CHANGELOG do CC 2.1.286 e 2.1.287 (lido na S361) |
| W6 | `cleanupPeriodDays: 90` no projeto (vence o 3650 do `settings.json` do usuário nas sessões deste repositório); `audit-log-2026-08-1.jsonl` (mtime 23/08) é `*.jsonl` de topo; **fato novo (S361, Q9):** a varredura usa o `cleanupPeriodDays` da sessão QUE VARRE e alcança todos os projetos — relatado pela frente de operações: 26 raízes com 90 (contagem grosseira da S361, relida pelo mesmo método: `find "$HOME" -maxdepth 4 -name Library -prune -o -type f -path '*/.claude/*' -name 'settings*.json'` ⇒ 42 arquivos de settings, 29 com 90, 12 sem a chave e só o do usuário com 3650; não é contagem de raízes de projeto) — então subir só este repositório para 3650 NÃO protege a cadeia; o backup agendado passa a ser a proteção principal | `.claude/settings.json:861`; `templates/settings/settings.base.json:671`; lanes `CC285-06`, `F-AUDIT-RETENTION`; relato da frente de operações (S360, não verificado em raiz por raiz) |

## Goal

Cortar a **v1.4.3** com o CI verde no Ubuntu 26.04, o estado da auditoria sem acúmulo por PID e sem
decisão de guard perdida, o rail do Codex re-pinado à mão na 0.160.0 (o pin automático, W3, fica para
depois da 1.4.3 — decisão do Owner S362), o publish do npm num Node suportado e a documentação alinhada
ao Claude Code 2.1.286 ou posterior (o instalado em 2026-10-02 é o 2.1.287) — cada mudança com controle
vermelho→verde registrado.

**Escopo do núcleo da 1.4.3 — decisão do Owner (S361, Q7), EMENDADA na S362 (2026-10-02).** Entram: o
**re-pin manual do Codex 0.156.1 → 0.160.0 (RP)**; **W1** (landada), **W3b** (landada), **W4**, **W6**,
**W2** (4 pacotes canônicos, U2-A a U2-D, mais os livres) e **W5a, W5b e W5.1** deste plano; a **W7a** do
PLAN-183; a **W5c**, sujeita à linha de corte; e a **rc.1 → hold de 24 h → GA** (W7). **Saem para a
1.4.4:** a W3 (pin automático: a decisão 3 não foi tomada), o PLAN-195 inteiro e a W7b do PLAN-183; ficam
também para depois do GA a W8, a L2 restante e a L3 a L5. **Versão:** com o PLAN-195 fora, nenhum pacote
do núcleo toca o `SPEC/v1` (`git diff v1.4.2..HEAD -- SPEC/` vazio, medido em 2026-10-02), então o corte é
**1.4.3**; se algum pacote passar a tocar o `SPEC/v1`, o CEO para e leva ao Owner. **Linha de corte:** o
que não estiver landado quando a derivação do kit começar (no máximo domingo 2026-10-11) sai do GA, com o
resíduo declarado. Custo declarado da W5c: 2–4 M de tokens, ~40 espelhos e o manifesto ADR-192, sem
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
   espera o debate e a decisão pendente 3. (No plano B da W3 vale ainda o motivo antigo: o molde do `re-pin-codex.py` só lê e
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
   **Debate FECHADO (S361; consensos em `.claude/plans/PLAN-194/debate/round-{1,2,3}/consensus.md`; três
   críticos — Segurança, QA e DevOps —, todos em `claude-opus-5-5`, id servido informado por cada um; crítica
   com VETO cujo modelo servido esteja fora do piso VETO não conta).** Vereditos por onda: **W5c PROCEED na
   rodada 1** (VETO de Segurança retirado, com condições); **W2 PROCEED na rodada 2** (VETO de integridade do
   log, ADR-052, retirado sob MF-R2-W2-1..4); **W3 PROCEED na rodada 3, 3 de 3 críticos** (`design-coherent`;
   nenhum P0, nenhuma afirmação FALSA no plano; consenso FINAL em `round-3/consensus.md`). **O VETO da W3 só
   se retira com a decisão pendente 3 ESCRITA pelo Owner como ramo (ii) ou ramo (i):** «confiança no
   registro» mantém o VETO e vira ESCALATE-TO-OWNER (a W3 vai ao Owner por múltipla escolha, e o PROCEED dela
   deixa de valer). As 23 condições de execução da W3 (consenso r3 §2) valem por PACOTE: condição não
   cumprida reprova o SIGN do pacote, não o debate; o rail (V2) confere, sem nova rodada. **Regra de parada,
   pré-registrada e cumprida:** ≤ 3 rodadas; NO-GO só por P0 ou afirmação FALSA no plano; nenhuma rodada do
   Codex acima de 80% do semanal (Q2). Uma onda que volta não segura as outras. **O `approved.md` terminal
   (DEBATE-SCHEMA §6) existe desde 2026-10-02** (`.claude/plans/PLAN-194/debate/round-3/approved.md`, commit
   `5c52998b`): o Owner ratificou o debate e as decisões 2, 4, 5 e 6; a decisão 1 foi superada (a cura
   landou em `65cd50d7`); a decisão 3 NÃO foi tomada, então a W3 fica ADIADA para depois da 1.4.3, com o
   VETO de Segurança levantado. O
   portão M1 do Red Team (DEBATE-SCHEMA §12.3) não se aplica à W3 (convergência na rodada N = 3 > 2); para a
   W2 (rodada 2) o CEO decide se o roda.
**Cláusula de bloqueio (decisão do Owner S361, Q3 opção 1; liberação POR ONDA):** o plano foi revisado pela
revisão no chat (PLAN-SCHEMA §4) e hoje está `executing`. **O debate único está FECHADO e as três ondas estão
LIBERADAS do portão do debate** (W5c na rodada 1, W2 na rodada 2, W3 na rodada 3); os must-fix e as
condições valem por onda e por pacote. A **W5c** segue pela fila (depois da W2; a primeira a sair se a cota
apertar). A **W2** não espera mais a cura do `agent_spawn` (W2.0, landada em `65cd50d7`) e ocupa a vaga 2
desde a S362. A **W3** está liberada do portão, mas **NENHUM pacote dela começa antes da
decisão pendente 3 ESCRITA** (é ela que retira o VETO; «confiança no registro» ⇒ ESCALATE) e das condições 1
a 5 do consenso r3 §2; na S362 o Owner a ADIOU para depois da 1.4.3 e ativou o re-pin manual. As demais ondas (W1, W3b, W4, W5a/W5b, W6, W7, W8 e os itens livres) não dependem do
debate.

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
saiu a 0.160.0): descartado pelo Owner na S359 em favor do pin automático e mantido como **plano B** da W3
(`codex-pin-<etiqueta do dia>`). **REATIVADO pelo Owner na S362 (2026-10-02)** como 1.ª tarefa do trem, para a
0.160.0, no pacote `codex-pin-0160` (fim da seção W3): a decisão 3 não foi tomada e a W3 saiu da 1.4.3. (e) Recusar o Sonnet 5.5 por ora (a recomendação anterior do CEO): descartada pelo Owner na
S359 («Adotar»).

**Mapa de colisões (nunca dois pacotes no mesmo arquivo).** Vale para os três planos que dividem as
vagas (este, o PLAN-195 e o PLAN-183); as ondas de outro plano são citadas pelo NOME da seção.

**Emenda S362 (2026-10-02) — o que vale na 1.4.3.** (1) As linhas que citam a W3, o PLAN-195 ou a W7b
do PLAN-183 ficam como registro para a 1.4.4: nenhum desses pacotes entra em voo antes do GA. (2) A
**pegada real da W5c** passa a ser a do `.claude/plans/PLAN-169/s338-ceremony-fable51/WFABLE51.patch`
(adoção do Fable 5.1, o precedente mais novo): **30 paths, medidos em 2026-10-02**, e NENHUM deles é
`scripts/install.sh`, o baseline do censo do instalador, `SUPPORT.md`, `.claude/hooks/audit_log.py`,
`.claude/hooks/_lib/test_isolation.py` ou `templates/settings/settings.user.json`. A pegada do
`WOPUS55.patch` (76 paths), usada antes, sobre-estimava as colisões. O censo da abertura da W5c confere de
novo; se ele marcar `install.sh`, a W5c re-deriva depois da W5b. (3) O texto A3.1 do ADR-149 (Ultracode)
vai DENTRO da emenda 4 da W5c; se a linha de corte tirar a W5c do GA, o A3.1 vai junto para a 1.4.4.
(4) `.claude/settings.json` é KERNEL (`check_arbitration_kernel.py:134`): a W6.2 e a W5c são pacotes de
kernel, em série (W6.2 → W5c).

| arquivo | quem toca | ordem |
|---|---|---|
| `.claude/settings.json` | W6 (retenção); W5c (adoção do Sonnet 5.5: `availableModels` é gerado do ADR-149 pelo `generate-available-models.py`); **W3 do PLAN-195** (só se o Owner decidir ligar o sandbox depois da medição); **W3, pacote 1c** (a guarda do registro em `permissions.deny`, se esse for o hospedeiro — condição 4 do consenso r3) | **W6 primeiro** (data de risco ~2026-11-21); depois a W5c, a **W3 (1c)** e a W3 do PLAN-195, uma de cada vez; sandbox, retenção e — desde a Q9 da S361 — a W5c num pacote só, apenas se ficarem prontos juntos antes da data (OQ-14, RESPONDIDA) |
| `templates/settings/settings.base.json` | W6 (só se mudar o padrão dos adopters); W5c | W6 primeiro, W5c depois; ou um pacote só se os dois ficarem prontos juntos |
| `.claude/adr/ADR-149-model-id-allowlist.md` | só a W5c (emenda 4); o texto A3.1 do Ultracode, antes atribuído à W5a, vai DENTRO dela | um pacote só, o da W5c (o Owner decidiu adotar); a W5a não toca o ADR-149; se a W5c sair pela linha de corte, o A3.1 sai junto (1.4.4) |
| `.claude/hooks/_lib/codex_cli_shape.py` | W3b; W3 (o argv com modelo e esforço fixos TOCA o arquivo — S361: hoje o padrão omite `--model` e o `_VALID_MODELS` não tem `gpt-6*`) | sequenciais, e a ordem está DECIDIDA (Q8, S361): a **W3b landa ANTES da W3**, na 3.ª vaga enquanto a W3 espera o debate; se o debate puser o arquivo no pacote da W3, a W3b entra no MESMO pacote só se couber no teto (prazo duro 2026-12-11, pacote pequeno), senão landa antes |
| `.claude/scripts/codex_invoke.py` | W3 (argv com modelo e esforço fixos); W3b (só se o conjunto derivado atingir o exemplo dele) | sequenciais, na mesma ordem da linha acima |
| `.claude/scripts/substrate-watch.json` | W5.1 (e a W3, na 1.4.4, se o desenho gravar o `codex_cli` ali) | **S362:** UM refresh só na 1.4.3, depois do LAND do re-pin manual (RP), gravando `codex_cli` 0.160.0; a W3 (1.4.4) faz o próprio refresh se mudar a versão global |
| `scripts/install.sh` e `.claude/scripts/data/installer-write-safety-baseline.txt` | W5b; W1a/W1b do PLAN-183 (re-derivação do pacote do ponteiro `PROTOCOL.md`, que toca os dois); W8 do PLAN-183 (baseline, via `upgrade.sh`). A **W5c NÃO os toca** (pegada `WFABLE51`, S362; antes se supunha que sim, pelo `WOPUS55.patch`) | **W5b primeiro e única na 1.4.3** (pequena, 3 paths); depois, na 1.4.4, a W1a/W1b do PLAN-183, re-derivadas sobre ela, e por fim a W8 do PLAN-183; se o censo da abertura da W5c marcar um dos dois, ela re-deriva depois da W5b. Toda onda que toca `scripts/**/*.sh` fora de `scripts/tests/` regenera o baseline do censo no MESMO patch (CLAUDE.md §5, PLAN-185) |
| `.github/workflows/smoke-install.yml` e `.github/workflows/ownership-nightly.yml` (os dois rodam `runs-on: ubuntu-latest`: `smoke-install.yml:196`, `ownership-nightly.yml:34`) | W1.5 (só se o censo W0.1 os marcar); W1a/W1b do PLAN-183 (estão entre os 16 paths do pacote do ponteiro) | **W1.5 primeiro** (prazo 2026-10-19); a W1 do PLAN-183 é re-derivada no HEAD depois dela |
| `.github/workflows/validate.yml` | W1 | nenhuma onda dos outros dois planos o toca hoje (conferido 2026-09-30 nas seções S359 do PLAN-183 e no PLAN-195) |
| `.claude/governance/gate-scripts-manifest.txt` (manifesto ADR-192) | W7 (só se o `release.sh`, membro do manifesto, mudar); W7b e W10 do PLAN-183 (sha do `validate-governance.sh`); **W5c** (S361: a pegada real inclui o `validate-governance.sh`); **W3, pacote 1a** (rodada 2: o verificador `.py`, o auxiliar JS e o lockfile entram no manifesto — o que o verificador grava substitui uma assinatura) | **nunca em paralelo** com a W7, a W7b, a W10 e a W5c: a mudança do `release.sh` na W7 landa ANTES da W7b/W10 ou DEPOIS do land delas; a W5c (pegada real, linha própria abaixo) e o pacote 1a da W3 seguem a mesma regra |
| `SBOM.md` | **W3, pacote 1a** (rodada 2: declara a dependência de tempo de operação — `node` + sigstore-js, versão e integridade — como ferramenta de mantenedor, fora do runtime dos hooks, e escopa o «stdlib-only» ao runtime dos hooks) | nenhuma outra onda dos três planos o cita hoje (conferido na S361: PLAN-183 e PLAN-195 não o mencionam; oráculo 0). O `CLAUDE.md` §3 («stdlib-only») só muda no fechamento, junto da poda, dentro da folga de 87 bytes (risco 9) |
| `INSTALL.md` | W6 (mitigação da retenção); W8 do PLAN-183 (linha sobre o `VERSION` semeado) | **W6 primeiro** (data de risco ~2026-11-21); a W8 do PLAN-183 depois — ou a linha do `VERSION` entra no mesmo patch de documentação da W6 |
| `.claude/scripts/ceo-boot.py` | L2 (disco + deriva + cura de classe do `scheduled_workflows_red` + cura do check de «stranded» — S361); **W2** (check advisory de observabilidade do estado da auditoria — rodada 1) | um pacote só: o da L2; se a L2 já tiver landado quando a W2 chegar, a extensão vai num land livre seguinte — nunca dois pacotes em paralelo |
| `.claude/hooks/_lib/audit_emit.py` (kernel) | **pacote de kernel de registro de ações da W3** (`_KNOWN_ACTIONS`; promove também o `pair_rail_codex_pin_mismatch`); W1a do PLAN-195 | hoje CERTA para a W3 (rodada 1): **em série**, um pacote de cada vez; o de registro de ações landa ANTES da W3.6 |
| `.claude/hooks/audit_log.py` | cura do `agent_spawn` (condição 67; LANDADA em `65cd50d7`). A W5c NÃO o toca (pegada `WFABLE51`, S362) | sem colisão aberta na 1.4.3 |
| `templates/settings/settings.user.json` | W6 (só se mudar a subtração da chave). A W5c NÃO o toca (pegada `WFABLE51`, S362) | só a W6, se precisar |
| `.claude/hooks/_lib/test_isolation.py` | nenhuma onda da 1.4.3 (a W5c NÃO o toca: pegada `WFABLE51`, S362) | — |
| `docs/CROSS-LLM-THREAT-MODEL.md` | W3, pacote 1b (o T-8, `:328`, muda no MESMO pacote que muda a âncora de confiança do hook) | nenhuma outra onda dos três planos o cita hoje (conferido na S361). O consenso da rodada 1 listou também a W0 do PLAN-195, por vizinhança com `docs/threat-model.md` — outro arquivo, que o `check-threat-model-freshness.py` escreve: vale a regra do risco 9 (árvore limpa no SIGN); re-conferir na abertura do pacote |
| `.claude/scripts/check-substrate-drift.py` | L1 (tipo do container do ledger); W3 (o detector de deriva passa a ler o registro do pin automático) | L1 primeiro; a leitura do registro entra DENTRO da L1 ou logo depois dela, antes da W3.6 |
| `.claude/hooks/_lib/filelock.py` (kernel) | só a opção T2 das travas da W2 (re-checagem de inode) | condicional: pacote de kernel PRÓPRIO, só se a W0.5 depois da cura mostrar que a listagem das travas ainda estoura o prazo do drain forçado |
| guarda de Bash (hook, testes) e docs de ameaça | W0–W2 do PLAN-195 | a **W3** deste plano só toca o `check_bash_safety.py` se a guarda do registro for hospedada nele (linha dos hospedeiros, logo abaixo; o PLAN-195 o lista com W1 e W2 — `PLAN-195-bash-guard-indirect-execution.md:263`); o `settings.json` do sandbox (W3 do PLAN-195) está na 1.ª linha; a W0 do PLAN-195 edita `docs/threat-model.md` em land livre — ver risco 9 (árvore limpa no SIGN) |
| hospedeiros da guarda do registro e das FONTES do verificador (W3, pacote 1c, ou 1b se couber; condições 4 e 6 do consenso r3) | **(a)** `permissions.deny` do `.claude/settings.json` (`:818-820`, 27 entradas; oráculo 1 — ver a linha do `settings.json`); **(b)** `.claude/hooks/check_bash_safety.py` (oráculo 1; as partes A e B do PLAN-195 o tocam); **(c)** `.claude/hooks/check_canonical_edit.py` (oráculo 1; KERNEL — `check_arbitration_kernel.py:88`; `_CANONICAL_GUARDS` em `:115`), se as fontes do verificador forem para oráculo 1 | (a) **W6 → W5c → W3 (1c)** e a W3 do PLAN-195, uma de cada vez; (b) em série com as partes A e B do PLAN-195, re-derivado sobre elas — se a guarda de Bash precisar dele, a W3.6 entra no caminho crítico do PLAN-195; PREFERÊNCIA: outro hospedeiro enquanto a parte B estiver em voo; (c) cerimônia de kernel, só se a condição 6 escolher `_CANONICAL_GUARDS` |
| espelhos gerados (`npm/templates/`, `npm/.claude/`, `dist/`) | W1.4 (se mexer no template do adopter); W5c; ondas que tocam hook | **não são path de pacote**: saída de build ignorada pelo git (`.gitignore:47` `npm/.claude/`, `:50` `npm/templates/`, `:198` `dist/`; `git ls-files npm/templates` = 0, medido 2026-09-30). Não entram em commit nem no Scope do sentinel; `scripts/npm-rebuild.sh` e `scripts/build-plugin.py --check` ficam como passos da bateria, sobre saídas locais |
| **leque de ADR** (acrescentado na S361: o achado da revisão do planejamento S360 sobre a colisão dos pacotes que criam arquivo de ADR foi confirmado e rebaixado para P2): `.claude/adr/README.md` (canônico, oráculo 1; índice regenerado por `generate-adr-index.py --write` e conferido por `--check`, `validate.yml:134-137`); os 8 documentos que citam a contagem de ADR (`README.md`, `README.pt-BR.md`, `npm/README.md`, `docs/ARCHITECTURE.md`, `docs/CTO-GUIDE.md`, `docs/FAQ.md`, `docs/GUIA-COMPLETO.md`, `docs/README.md`; `test_verify_counts.py::_EXPECTED_SITES`, `verify-counts.sh` em `validate.yml:163-166`); o preâmbulo do `CHANGELOG.md` (regra «CHANGELOG HEADER RULE» do mesmo script, `verify-counts.sh:841`, contagem exata); e o `CLAUDE.md:54` (conferido por `check-claude-md-claims.py`, `validate.yml:82-85`) | todo pacote que cria arquivo de ADR ou de emenda em arquivo próprio: a ADR-201 (parte A do PLAN-195), a W7b do PLAN-183 e — confirmado pela rodada 1 do debate — a W2 (`ADR-055-AMEND-4`) e a W3 (`ADR-182-AMEND-1`) daqui | **LAND em série**: UM pacote de ADR por vez, landado junto de um fechamento de sessão. O índice e os documentos de contagem ficam FORA da conta de ≤ 8 paths e são re-derivados no LAND (4.ª exceção da «Regra de WIP»; decisão Q5 do Owner, S361) |
| a contagem de ADR (**198** em 2026-10-01: `ls .claude/adr/ADR-*.md` contado por `wc -l`) INCLUI as **22** emendas em arquivo próprio (`ADR-*AMEND*.md`, medido na S361) | W2 e W3 (emenda em arquivo próprio nos dois, confirmado pela rodada 1; só emenda aditiva fica dentro do ADR existente — Q5) | entram no leque da linha acima; 198 → 199 não muda o tamanho do `CLAUDE.md`, mas a folga útil é de 87 bytes (máximo 39.999, porque o gate reprova a partir de 40.000 — risco 9) |
| `CHANGELOG.md` (colisão CONDICIONAL) | pacote que cria arquivo de ADR (o preâmbulo carrega a contagem) × **W7** (o `CHANGELOG.md` é path do corte) | **não podem estar em voo juntos**: o pacote de ADR landa ANTES de a W7 tocar o `CHANGELOG.md`, ou DEPOIS do corte |
| pegada real da **W5c** além dos paths candidatos (**S362: pela pegada `WFABLE51`, 30 paths medidos em 2026-10-02**; o censo da abertura da W5c fecha a lista): `.claude/settings.json` e `templates/settings/settings.base.json` (1; linhas próprias acima), `scripts/upgrade.sh` (1), `.claude/scripts/validate-governance.sh` (oráculo 0, MEMBRO do manifesto ADR-192), `.claude/governance/gate-scripts-manifest.txt` (1), o ADR-149 (1, com o A3.1 dentro), `.claude/scripts/cost-table.yaml`, `docs/provider-pricing.md` (superfície de preço citada pelo `.claude/hooks/_lib/adapters/live/_cost.py`), `scripts/local/smoke-install-parity.sh` (0) e `.claude/scripts/tier_policy_cli/` (0). NÃO entram: `scripts/install.sh`, o baseline do censo do instalador, `SUPPORT.md`, `audit_log.py`, `_lib/test_isolation.py` e `settings.user.json` (a pegada do `WOPUS55.patch`, 76 paths, usada na S361, os incluía) | W5c; o manifesto e o `upgrade.sh` também são tocados por outras ondas (linhas acima: manifesto — W7, W7b, W10; `upgrade.sh` — W5b só mede, W8 do PLAN-183 via baseline) | uma de cada vez; a W5c re-deriva sobre o HEAD do land anterior, e o manifesto segue a regra «nunca em paralelo» da linha própria |
| colisões CONDICIONAIS (S361; só valem se o outro pacote tocar o arquivo): `.claude/hooks/_lib/audit_emit.py` — a W2 NÃO o toca mais (rodada 1: sem evento por arquivo; a colisão agora é a CERTA, em linha própria acima: pacote de kernel de registro de ações da W3 × W1a do PLAN-195, que só toca o arquivo se a ADR-201 estender `_LEARNING_RAIL_ENUM`/`_LEARNING_SWITCH_ENUM`); `.github/workflows/npm-publish.yml` — W1.5 (só se o censo W0.1 o marcar) × W4; `.github/workflows/formal-verify.yml` — W1.5 (idem; está na lista `WORKFLOWS` do gate semanal, `release.yml:550`) × W8; `.claude/data/model-currency-expected-reds.txt` — W3b × W5c; `codex_cli_shape.py` — W3b × W3 (hoje CERTA, linha própria acima) | os pares citados | em cada par, um pacote por vez; o segundo re-deriva sobre o HEAD do land do primeiro. Ordem padrão: W1.5 antes de W4 e de W8 (prazo 2026-10-19); W3b antes de W5c e da W3 |

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
| `.claude/hooks/_lib/audit_emit.py` | 1 | — | pacote de kernel de registro de ações da W3 (em série com a W1a do PLAN-195); a W2 NÃO o toca (rodada 1) |
| `.claude/hooks/SessionStart.py` | 1 | — | fora da W2 (rodada 1: não há drain nem reconciliação nele; retirado dos paths) |
| `.claude/adr/ADR-055-AMEND-4-spool-state-gc.md` (novo) | 1 | — | W2 (rascunho PROPOSED em `.claude/plans/PLAN-194/debate/round-2/` primeiro; o arquivo canônico nasce no pacote de ADR — Q5) |
| `.claude/adr/ADR-055-AMEND-3-opportunistic-drain-nonblocking.md` | 1 | — | referência |
| `.claude/hooks/tests/test_spool_state_amend4.py` (novo; nome proposto na rodada 2 — substitui `test_spool_state_gc.py`, cujo nome contém o seletor `gc`) | 0 | não | W2 (oráculo rodado na S361) |
| `.claude/hooks/tests/test_spool_drain_contended_skip.py` | 0 | não | W2 |
| `.claude/hooks/tests/test_spool_writer_cache.py` | 0 | não | W2 (regressão) |
| `.claude/hooks/tests/conftest.py` | 1 | — | fora de L4 |
| `.claude/hooks/_lib/audit_hmac.py` | 1 | — | W2 (só executa `verify_chain()`) |
| `.claude/hooks/audit_log.py` | 1 | não | cura do `agent_spawn` (W2.0; LANDADA em `65cd50d7`); a W5c não o toca (pegada `WFABLE51`, S362) |
| `.claude/hooks/tests/test_two_writer_chain.py` | 0 | não | W2.0 (LANDADA em `65cd50d7`); cura de classe do teste instável `TestParallelWritersChain` (FX, land livre, nomes de classe e de método congelados) |
| `.claude/hooks/_lib/filelock.py` | 1 | não | W2, SÓ a opção T2 das travas (kernel; pacote próprio e condicional) |
| `.claude/hooks/check_plan_edit.py` | 1 | — | backlog (regex de follow-up) |
| `.claude/plans/PLAN-194/debate/round-1` (novo) | 0 | não | W2 + W3 + W5c (debate único; rodada 1 feita) |
| `.claude/plans/PLAN-194/debate/round-2` (novo) | 0 | não | W2 + W3 (rodada 2; rascunhos PROPOSED do `ADR-055-AMEND-4` e do `ADR-182-AMEND-1`) |
| `.claude/plans/PLAN-193/repass-ga/verdict-ga-3.txt` | 0 | não | L1 (evidência, só leitura) |
| `.claude/adr/ADR-182-AMEND-1-codex-auto-pin-provenance.md` (novo; nome proposto) | 1 | — | W3, pacote 1b (rascunho PROPOSED em `.claude/plans/PLAN-194/debate/round-2/`, revisado para a rodada 3; o arquivo canônico nasce no pacote de ADR — Q5) |
| `.claude/hooks/check_pair_rail.py` | 1 | — | W3, pacote 1b (cura: pin automático; o hook só faz hash e consulta local, nunca usa rede; `_emit_audit()` ligado ao `emit_generic`; sumidouro de teste só no modo de teste) |
| guarda do registro e das FONTES do verificador (hospedeiros na linha própria do mapa de colisões; oráculo rodado na abertura do 1c/1b) | a rodar | a conferir | W3, pacote 1c (PRIMEIRO da fila, se o 1b passar de 8 paths) ou 1b; condições 4 e 6 do consenso r3 (MF-R2-W3-5) |
| `.claude/scripts/codex-auto-pin-verify.py` (novo; nome proposto) | 0 | **entra no manifesto** | W3, pacote 1a (orquestrador Python do verificador, em processo próprio, fora de qualquer guard; **MEMBRO do manifesto ADR-192**, não «livre» — o oráculo 0 não basta; oráculo rodado na S361 e de novo na abertura do pacote) |
| `.claude/scripts/codex-auto-pin/verify-sigstore.js` (novo) | 0 | **entra no manifesto** | W3, pacote 1a (auxiliar `node` da assinatura; oráculo 0 medido na r3 e conferido na S361 — fonte editável pelo agente ⇒ guarda da condição 6) |
| `.claude/scripts/codex-auto-pin/package.json` (novo) | 0 | **entra no manifesto** | W3, pacote 1a, SÓ no ramo (ii) da decisão pendente 3; oráculo 0 medido na r3 e conferido na S361 |
| `.claude/scripts/codex-auto-pin/package-lock.json` (novo) | 0 | **entra no manifesto** | W3, pacote 1a, SÓ no ramo (ii) (lockfile de integridade de toda a árvore do `sigstore`); oráculo 0 medido na r3 e conferido na S361 |
| arquivo único de fixtures da camada 2 (novo; nome a fixar no 1a; sha e data de captura ao lado — condição 17) | a rodar | não | W3, pacote 1a (oráculo rodado na abertura) |
| `.claude/scripts/env-inventory.json` | 0 | não | W3, pacote 1a (a variável de modo obrigatório da camada 2 — condição 13, ajuste 17 do consenso r3; o `env-inventory-check.py` coleta TOKENS em código de framework, `:12-14`, `:107`, e acusa nome novo ou stale, `:164-169`; FORA da contagem de 8/7 do consenso: com ele o 1a tem 9 paths no ramo (ii) — exceção (5) da «Regra de WIP», proposta junto da decisão 3) |
| `.claude/hooks/check_canonical_edit.py` | 1 | — | W3, pacote 1c, SÓ se a condição 6 escolher `_CANONICAL_GUARDS` (`:115`; KERNEL — `check_arbitration_kernel.py:88`) |
| `.claude/scripts/tests/test_codex_auto_pin_verify.py` (novo; nome proposto) | 0 | não | W3, pacote 1a (matriz A/P, células de fronteira, duas camadas de teste e teste-censo) |
| `SBOM.md` | 0 | não | W3, pacote 1a (declara `node` + sigstore-js como ferramenta de mantenedor; escopa o «stdlib-only» ao runtime dos hooks) |
| `docs/CROSS-LLM-THREAT-MODEL.md` | 0 | não | W3, pacote 1b (o T-8, `:328`, muda no MESMO pacote — a âncora de confiança do hook muda) |
| `.claude/hooks/tests/test_check_pair_rail_auto_pin.py` (novo) | 0 | não | W3, pacote 1b (testes do hook: células H-xx, C-xx e R-xx do AMEND-1) |
| `.claude/governance/codex-cli-pin.txt` | 1 | — | re-pin manual 0.160.0 (RP, decisão S362): só o teto da faixa alarga, para `>=0.128.0,<0.161.0` (esperado; o `--dry-run` do gerador confere); a W3 não o toca (rodada 1: a faixa fica intocada) |
| `.claude/governance/codex-cli-pin-manifest.json` | 1 | — | re-pin manual 0.160.0 (RP): recebe o sha do payload da 0.160.0 (no pin automático da W3 não receberia — pergunta 1 do debate) |
| `.claude/governance/codex-cli-binary-sha256.txt` | 1 | — | fora do RP: o molde 0156 e o `re-pin-codex.py` não o citam (`grep`, 2026-10-02; o `PACK_FILES` do molde, `OWNER-PIN-SIGN.sh:134`, lista o sentinel, os 2 arquivos do pin, o script, o ensaio e o README) |
| `.claude/plans/PLAN-194/codex-pin-0160/` (OWNER-PIN-SIGN.sh, rehearse-pin-0160.sh, README.md, pin-0160-approved.md, codex-cli-pin.txt.new, codex-cli-pin-manifest.json.new) | 0 | não | re-pin manual 0.160.0 (RP; gerado pelo `re-pin-codex.py`, etiqueta `0160` pela `pack_tag()`; oráculo 0 medido em 2026-10-02 no script e no sentinel) |
| `.claude/plans/PLAN-193/codex-pin-0156/OWNER-PIN-SIGN.sh` | 0 | não | RP (molde, só leitura; é o molde do pack mais novo — o gerador recusa molde mais velho, `re-pin-codex.py:1952-1974`) |
| `.claude/scripts/re-pin-codex.py` | 0 | não | RP (só executa) |
| `.github/scripts/validate-pair-rail-verdict.py` | 0 | **sim** | W3 (não editar; lê a faixa do pin — controle W3.4 d; o limite do `parse_semver`, `:355-359`, é declarado no AMEND-1) |
| `.github/workflows/release.yml` | 1 | — | referência (`:550-557`, `:760`) |
| `.claude/adr/ADR-182-codex-payload-pin-enforcement.md` | 1 | — | referência (emendado pela W3) |
| `.claude/scripts/codex_invoke.py` | 0 | não | W3, pacote 2 (argv com modelo e esforço fixos, pelo núcleo de verificação) / W3b (conferir) |
| `.claude/workflows/council-audit.js` | 1 | — | FORA da W3 (rodada 1: declarado no material assinado, não convertido); backlog |
| `.claude/scripts/substrate-watch.json` | 0 | não | W5.1 |
| `.claude/hooks/_lib/codex_cli_shape.py` | 1 | — | W3b (landa ANTES da W3 — Q8, S361); W3 (argv com modelo e esforço fixos) |
| `.claude/hooks/codex_review_user_code.py` | 1 | — | FORA da W3 (rodada 1: chama `codex exec` em `:131` sem conferir o pin; hook `Stop` AUTOMÁTICO no opt-in — declarado no material assinado, com o estado do opt-in); backlog |
| `.claude/scripts/run-promotion-gate.py` | 0 | não | W3, pacote 2 (pelo núcleo de verificação; só `codex --version`, `:198`/`:212`) |
| `.claude/hooks/tests/test_codex_cli_shape.py` | 0 | não | W3b |
| `.claude/scripts/optimizer/codex_phase_gate.py` | 0 | não | W3b (se o conjunto derivado atingir) |
| `.claude/scripts/check-model-deprecations.py` | 0 | não | W3b.0 (cura da precisão do matcher — revisão Codex S359) |
| `.claude/scripts/model-deprecations.json` | 0 | não | W3b.3 (linha do `gpt-5.5`, SE a aposentadoria de 2026-10-14 se confirmar em fonte primária — land livre); W3 (o id fixado no argv do rail entra aqui — land livre ligado ao pacote 2); fora isso, backlog (refresh do ledger) |
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
| `.claude/skills/core/llm-routing-and-finops/SKILL.md` | 1 | — | W5c (alias `sonnet` mantido nos exemplos; a tabela de roteamento, `:109-123`, que cita `claude-sonnet-4-6`, é corrigida — critério pré-registrado, W5c.2 (b)) |
| `.claude/hooks/_lib/adapters/live/claude.py` | 1 | — | W5c (HTTP 400 com `thinking` desligado e `tool_choice` forçado — lane `ANT-02`) |
| `.claude/hooks/_lib/model_routing.py` | 1 | — | W5.1 (vigia do Haiku 4.5, só leitura: `:62-71` o usa em `file_read`, `line_audit` e `digest`); edição só se a aposentadoria ganhar data |
| `.claude/workflows/eval-baseline-n20.js` | 1 | — | W5.0 (sonda (d): só leitura de `:3` e `:547` — veredito W0a do PLAN-134 de que o `opts.model` do `agent()` é INERTE) |
| `.claude/scripts/tests/test_settings_guard_loadability.py` | 0 | não | W5.1 |
| `.claude/scripts/check-substrate-watch.py` | 0 | não | W5.1 (Owner roda `--refresh`) |
| `scripts/install.sh` | 1 | — | W5b |
| `scripts/upgrade.sh` | 1 | — | W5b (só medir `:219`, `:3881-3884`); W5c (pegada `WFABLE51`, mapa de colisões) |
| `scripts/tests/test-install-deny-baseline.sh` | 0 | não | W5b |
| `.claude/scripts/data/installer-write-safety-baseline.txt` | 0 | não | W5b (regenerado no mesmo patch) |
| `.claude/scripts/check-installer-write-safety.py` | 0 | não | W5b (só executa); W5c (bateria; só executa) |
| `.claude/scripts/derive-settings-baselines.py` | 0 | não | W5c (bateria: `--check` num clone com TODAS as tags GA; só executa) |
| `.claude/hooks/_lib/test_isolation.py` | 1 | não | nenhuma onda da 1.4.3 (a W5c não o toca: pegada `WFABLE51`, S362) |
| `.claude/settings.json` | 1 | — | W6 primeiro; depois W5c (`availableModels` gerado) e a W3 do PLAN-195, se o Owner ligar o sandbox (OQ-14) |
| `templates/settings/settings.base.json` | 1 | — | W6 (só se mudar o padrão dos adopters); W5c |
| `templates/settings/settings.user.json` | 1 | — | W6 (subtrai a chave; sem mudança esperada); a W5c não o toca (pegada `WFABLE51`, S362) |
| `.claude/scripts/ceo-backup.sh` | 0 | não | W6 (só executa) |
| `.claude/scripts/backup-audit.py` | 0 | não | referência |
| `.github/workflows/formal-verify.yml` | 1 | — | W8 |
| `.claude/scripts/check-substrate-drift.py` | 0 | não | L1; W3 (o detector de deriva lê o registro do pin automático — dentro da L1 ou logo depois, antes da W3.6) |
| `.claude/scripts/tests/test_check_substrate_drift.py` | 0 | não | L1 |
| `.claude/scripts/ceo-boot.py` | 0 | não | L2; W2 (check advisory de observabilidade, no pacote da L2 — mapa de colisões) |
| verificadores G6 e G7 e o script do H1 (novos; paths a fixar na abertura do pacote da W2.4-bis; só-leitura, fora de hook) | a rodar | a conferir | W2.4-bis (oráculo rodado na abertura; o encaixe no nightly pode puxar `.claude/workflows/nightly-hygiene.js`, oráculo 1) |
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
  3.14 têm. **Gravada no `PLAN-194/LEDGER.md` em 2026-10-01 (S361).** — Check: none (medição)
- [ ] **W0.5 (controle vermelho da W2; PRÉ-REGISTRADA — rodadas 1 e 2 do debate)** — em árvore
  descartável, com o pré-registro gravado no LEDGER ANTES de rodar (**gravado em 2026-10-02, S362, na
  seção «W0.5-pré-registro» do LEDGER**; a árvore sintética passa a ~233 mil entradas, o tamanho do state
  dir vivo medido pelo CEO nesse dia; margem medida ≥ 3 s ⇒ a W2 PARA e vai ao Owner). **Células:** as 8 (2^3) {saída sem
  spool próprio, com spool próprio} × {dir vazio, ~220 mil entradas} × {1 saída, ≥ 9 concorrentes} (limiar
  de 9 estimado na lane `H-02`), mais as extras: (1) «estoque só de travas (~150 mil)» — a situação
  PERMANENTE sob a regra de travas T1, que decide a T2; (2) ENTREGA DE DECISÃO de um guard que decide BLOCK,
  com ≥ 9 saídas concorrentes, o diretório cheio e um portador externo da trava canônica; (3)
  encerramento do interpretador depois do atexit (calibra `EXIT_MARGIN_S`); (4) o intervalo desde o
  INÍCIO DO WRAPPER (`_python-hook.sh`, que mantém o PID por `exec`) até a âncora do prazo; (5) o drain
  OPORTUNISTA ANTES da decisão, com a regra pré-registrada: se o tempo entre a decisão e o stdout escrito
  passar da margem, o mesmo prazo vale para o drain oportunista, no pacote da W2; (6) a vivacidade da perna
  3 sob rajada (contagem e idade dos spools órfãos com conteúdo depois da carga e depois de N emissores;
  `K_MAX` = 100); (7) **calibração com o harness REAL:** 2 chamadas `claude -p`, CC congelado, com um hook
  sintético que imprime BLOQUEIO e atrasa a saída além do timeout, contra o mesmo hook saindo rápido, com e
  sem `flush` — com stdout em pipe a decisão só sai DEPOIS do `atexit` (medido pelo sintetizador da rodada
  2 em CPython 3.9.6: 1.º byte em 1,52 s com um `atexit` de 1,5 s); sem a calibração, o controle S1 é
  declarado no material assinado como prova contra um MODELO do harness. **Métricas:** p50 e p95 da
  latência de saída, a decisão entregue ou descartada, as linhas `drain canonical lock timeout` e a taxa de
  `exit_deadline_skip`. **Estatística pré-registrada:** medir primeiro a taxa p̂ de perda de decisão no
  HEAD e escolher N com 3/N ≤ p̂/10; p95 só com N ≥ 100 (senão p90); substrato congelado e registrado em
  toda entrada (versão do CC, o `python3` que o `_python-hook.sh` usa, SO, sha do instrumento).
  **Critério de vermelho escrito antes:** ≥ 1 timeout em {~220 mil, ≥ 9}, 0 em {vazio, ≥ 9}, decisão
  perdida no braço de entrega e o H1 vermelho no HEAD (esperado F ≥ 0,9). Vermelho NÃO reproduzido ⇒ o
  LEDGER registra «controle vermelho não reproduzido» e a prova da W2 passa a ser só estrutural, declarada
  como tal. **Esperado depois da cura:** sem spool próprio, razão p95 cheio/vazio ≤ 1,2; com spool próprio e
  ~150 mil travas, decisão entregue e prazo respeitado, **sem exigir razão**. **Valores INICIAIS:** ε = 0,01
  (só com `|D|_min` ≥ 200 e o H1 medido no HEAD); `EXIT_MARGIN_S` = 1,0 s e prazo de 2,0 s — regra: margem
  ≥ p99 medido × 1,5; se não couber, encolhe o PRAZO, nunca a margem; a medição é declarada como da máquina
  do Owner, porque a CI é mais lenta; limite de 2.000 `stat` no check do `/ceo-boot`. **Gatilho numérico da
  T2, escrito ANTES de rodar:** na célula «~150 mil travas» com ≥ 9 concorrentes, `exit_deadline_skip` > 0
  ou p95 de saída acima do orçamento; ou a W2.6 precisar rodar mais de 1× por mês; ou um Linux de vida
  longa (o espaço de PIDs lá não tem teto prático). `SPOOL_LOCK_TIMEOUT` (2,5 s, `spool_writer.py:66`)
  re-medido. **Veredito gravado:** a W0.5 grava no LEDGER, no HEAD e depois da cura, uma linha
  `W0.5-veredito (HEAD)` / `W0.5-veredito (pos-cura): decisoes_descartadas=<n> N=<N>`, que o Check de
  sucesso da W2 lê («decisão perdida» sem esse veredito sai do texto). Medição fora do CI, nunca asserção
  de tempo absoluto em teste. — Check: none (medição; comandos, datas e resultados no LEDGER)
- [x] **W0.6 (para a W3; NOVA na rodada 1 do debate; sem cota paga) — FEITA em 2026-10-02 (S361);
  resultado na seção `W0.6` do LEDGER** — o verificador de assinaturas do npm num projeto-rascunho
  (`npm i --prefix <dir descartável>`, NUNCA `-g`, registro fixo, sem `.npmrc` do usuário, `npm_config_*`
  limpas). **Resultado:** o comando `npm audit signatures` NÃO serve — dá falso verde com payload
  adulterado, atestado removido, atestado de OUTRO repositório e cache quente sem rede; a biblioteca
  `sigstore` chamada COM política de identidade SERVE — verde só no íntegro, recusa toda adulteração e
  toda identidade divergente. A decisão que sobra é o EMPACOTAMENTO (decisão pendente 3), e a «confiança
  no registro» deixou de ser resíduo aceitável (virou ESCALATE). — Check: none (medição feita; resultado no LEDGER)

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
Check: python3 -m pytest .claude/hooks/tests/test_spool_state_amend4.py .claude/hooks/tests/test_spool_drain_contended_skip.py .claude/hooks/tests/test_spool_writer_cache.py -q

**Execução na 1.4.3 — decisões do Owner S362 (2026-10-02).** O teto de 400 linhas conta os testes, então a
W2 sai em **4 pacotes canônicos em série na vaga 2**, todos no `spool_writer.py`: **U2-A** = auxiliar de
saída com caminho rápido (W2.2); **U2-B** = journal vazio removido na origem (W2.3) + sinal de trava
canônica presa na saída (≤ 1 h); **U2-C** = prazo da drenagem forçada de saída com a âncora `min(import,
início do processo no kernel)` (W2.2-bis) — é a cura de SEGURANÇA; **U2-D** = o único pacote de ADR da
1.4.3 (`ADR-055-AMEND-4` ACCEPTED, com o leque de ADR e a fiação do nightly para G6 e G7). Livres em
volta: os verificadores do spool e o H1 vivo (pré-condição do LAND do U2-A e do SIGN do U2-C), o estresse
da W2.5 em três levas (a 3.ª na sombra do U2-C), a W0.5 (no HEAD e depois da cura) e o script da W2.6. A
**convivência de versões é DECLARADA** no material assinado dos U2-A a U2-C, e o LAND acontece com a sessão
aberta; a W2.6 segue exigindo as sessões DESTE projeto fechadas há ≥ 10 min e roda **depois do LAND do
U2-B**. O `ADR-055-AMEND-4` sai condensado: parte normativa com até ~250 linhas, citando o rascunho de 1.038
linhas por sha256. Se o código da W2 (U2-A a U2-C) não estiver landado quando a derivação do kit
começar, o CEO PARA e leva ao Owner, porque é a cura de segurança.

**Objetivo (rodadas 1 e 2 do debate):** sem acúmulo de journals e sem decisão perdida; travas limitadas e
limpas pela W2.6 (salvo a opção T2 das travas, abaixo). Em concreto: a saída de um hook sem spool
próprio não toma o lock canônico nem varre o diretório; o journal vazio é removido na origem; os
órfãos atuais somem (219.301 arquivos de 0 byte em 2026-09-30; 222.872 na re-medição da S361).
**Por que importa:** o risco de segurança é a DECISÃO DE GUARD PERDIDA por latência de saída; a
contagem de arquivos é higiene. Com o dir cheio, cada drain forçado lista e ordena ~219 mil nomes sob
o lock canônico (~0,24-0,30 s por drain, lane `H-02`); com saídas concorrentes o lock de 2,5 s estoura
e guards PreToolUse passaram do timeout de 5 s — e um guard que estoura o timeout deixa a ação passar
sem decisão (lane `CC285-05`). **Paths:** `.claude/hooks/_lib/spool_writer.py` (1);
`.claude/adr/ADR-055-AMEND-4-spool-state-gc.md` (1, novo, PROPOSED — rascunho em
`.claude/plans/PLAN-194/debate/round-2/ADR-055-AMEND-4-draft.md`; o arquivo canônico nasce só no pacote
de ADR, Q5; o slug fica, por anti-churn — R2-7); `.claude/hooks/tests/test_spool_state_amend4.py` (0,
novo — **o módulo NÃO se chama mais `test_spool_state_gc.py`**: o `pytest -k` casa também o NOME do
módulo, então o `-k gc` selecionaria todos os testes dele, e não só os do item; o nome novo não contém
nenhum seletor dos Checks);
`test_spool_drain_contended_skip.py` (0, o teste 4 fica intacto) e `test_spool_writer_cache.py` (0,
regressão). **Pré-condição do SIGN da W2:** a cura da corrida do `agent_spawn` (W2.0) —
`.claude/hooks/audit_log.py` (1) e `.claude/hooks/tests/test_two_writer_chain.py` (0) —, LANDADA em
pacote canônico próprio (`65cd50d7`, S361).
**Observabilidade (W2.4-bis):** `.claude/scripts/ceo-boot.py` (0), no pacote da L2, mais os verificadores
só-leitura G6 e G7, fora de hook (paths a fixar na abertura do pacote; o encaixe no nightly decide se o
`.claude/workflows/nightly-hygiene.js`, oráculo 1, entra). **Condicional (opção T2 das travas):**
`.claude/hooks/_lib/filelock.py` (1, kernel), em pacote próprio. **Fora do pacote base:** a **W2.4** (GC
dentro do hook) é CONDICIONAL e só volta como pacote próprio. **Fora da W2:** `SessionStart.py` (não há
drain nem reconciliação nele — `grep -c 'drain\|spool' .claude/hooks/SessionStart.py` = 0; a
reconciliação de início de sessão, `reconcile_journal_at_session_start`, `spool_writer.py:2467`, não tem
chamador em produção) e `audit_emit.py` (sem evento por arquivo). **Estimativa:** 1,0-1,8 M tokens com
rail (prazo na saída + provas + calibração com o harness real); 200-300 linhas e 3-5 paths estimados
antes da rodada 1 — o CEO re-estima ao abrir o pacote, com o teto de 400 linhas e ≤ 8 paths, e divide em
dois pacotes se passar. **Debate:** SIM — núcleo da cadeia de auditoria, e a cura emenda a premissa do
ADR-055-AMEND-3 de que o timeout do drain forçado é «genuinamente anômalo». `needs_debate=true` (o mesmo
que «Debate: SIM» acima).
**LIBERADA pelo PROCEED da rodada 2 do debate (S361; `design-coherent`, os três críticos) — decisão do
Owner S361, Q3, liberação por onda.** O VETO de integridade do log de auditoria (ADR-052) foi RETIRADO,
condicionado a MF-R2-W2-1..4 no texto do `ADR-055-AMEND-4` e do plano antes do pacote de ADR: (1) trava
canônica presa vira sinal em ≤ T; (2) âncora do prazo = `min(import, início do processo no kernel)`; (3)
G6 e G7 dentro da W2; (4) plano e AMEND-4 reconciliados (onde divergirem, vale o rascunho do AMEND-4).
Os must-fix de execução do consenso da rodada 2 valem como pré-requisitos; quem confere a aplicação é o
rail do pacote (V2). **Para o SIGN:** a cura do `agent_spawn` (W2.0) já landou (`65cd50d7`, a decisão
pendente 1 ficou superada) e a vaga é a 2 desde a S362; faltam os requisitos de cada pacote U2-A a U2-D. A rodada
1 tinha dado RUN-ANOTHER-ROUND: o desenho mudou de forma — a antiga W2.3 (relocação) saiu, entrou o prazo
na saída (W2.2-bis) e vale a regra de travas abaixo. MF-W2-1 a MF-W2-6 estão definidos na crítica de
segurança da rodada 1 (`.claude/plans/PLAN-194/debate/round-1/security-engineer.md`). **Emenda de ADR
(Q5, S361):** a cura contradiz uma premissa do ADR-055-AMEND-3 — mudança SEMÂNTICA ⇒ arquivo de emenda
próprio (`ADR-055-AMEND-4`), confirmado pela rodada 1 (a premissa «anômalo» muda); ele entra no leque de
ADR do mapa de colisões (LAND em série; 4.ª exceção ao teto de paths).

**Regra de travas (rodada 1; o portador do VETO prevalece no domínio dele).** Na W2, NENHUM hook faz
`unlink` de caminho `*.lock`: o `FileLock.acquire` (`.claude/hooks/_lib/filelock.py:144-149`) abre com
`O_CREAT` e faz `flock` sem comparar o inode, então apagar o caminho de uma trava quebra a exclusão
mútua (e a premissa «enquanto o PID vive, nenhum drainer toca os arquivos dele» é FALSA: a fase 1 do
drain recupera `.draining.*` «owned by a dead PID (or even a live one)», `spool_writer.py:1277-1316`).
(i) **Journals:** cura na origem — o journal vazio é removido sob a PRÓPRIA trava do journal, SÓ pela
compactação (que hoje o reescreve com 0 byte e nunca o remove, `spool_writer.py:2276-2297`; a remoção
pelo dono na saída SAIU na rodada 2: a compactação é o único produtor de journal com 0 byte, então ela
cobre todos os casos); é seguro para o ARQUIVO do journal porque o flush reabre pelo caminho, sob a mesma
trava, com `O_CREAT` (`spool_writer.py:956-962`). (ii) **Travas:** a opção **T1** é o padrão — as travas
ficam, o estoque é limpo pela W2.6 (com todas as sessões do projeto fechadas não existe adquirente
vivo), a contagem é reportada à parte (sem limiar de segurança) e fica limitada pelo espaço de PIDs. **T1
é OPERACIONAL, e a W2.6 é RECORRENTE sob ela:** o estoque de travas volta à ordem de ~150 mil em 3 a 4
semanas (~15,8 mil por dia no ritmo medido — inferência do rascunho e de um crítico, não refeita), então o
check do `/ceo-boot` conta as travas e, a partir de 100 mil, RECOMENDA rodar a W2.6 de novo
(manutenção do Owner, decisão pendente 2). A proposta de o dono apagar as próprias travas na saída NÃO
entra; só volta com quatro coisas: o censo mecânico dos 4 abridores dos caminhos de trava por PID
(`spool_writer.py:958`, `:1002`, `:1374`, `:2276`) como guarda; o sinalizador em processo do próprio
`.draining`; o controle de intercalação determinística (vermelho com remoção ingênua, verde com a cura);
e novo julgamento do portador do VETO. A opção **T2** (re-checagem de inode no `filelock.py`, kernel)
só entra como pacote de kernel PRÓPRIO e condicional, com **gatilho numérico escrito ANTES de rodar**
(W0.5): na célula «~150 mil travas» com ≥ 9 concorrentes, `exit_deadline_skip` > 0 ou p95 de saída acima
do orçamento; ou a W2.6 precisar rodar mais de 1× por mês; ou um Linux de vida longa. A opção **T3**
(relocar as travas) SAI. (T1 a T3 são as opções L1 a L3 do consenso, renomeadas aqui para não colidir
com os itens livres L1 a L5.)

**Conteúdo exigido do `ADR-055-AMEND-4` (rodadas 1 e 2; ele nasce em arquivo próprio; onde o plano e o
rascunho do AMEND-4 divergirem, VALE O RASCUNHO — MF-R2-W2-4):**

- a união de não-perda reescrita: a perna 2 vale só para quem tem spool; a perna 3 é o drain do próximo
  emissor que ganhar a trava (a varredura de órfãos roda também no drain oportunista,
  `spool_writer.py:2366-2371`); NÃO existe perna de `SessionStart`;
- o prazo da drenagem forçada de saída (W2.2-bis), com `T_min` = o MENOR timeout registrado (3 s hoje) e
  teste de deriva: estourado o prazo, o spool fica para a perna 3, e isso deixa de ser «anômalo»; **âncora
  = `min(import, início do processo no kernel)`**, com fallback e resíduo declarados (MF-R2-W2-2);
- o auxiliar de saída com `flush` de stdout e stderr ANTES da drenagem, chamado no `atexit` E no sinal;
- o **sinal de trava canônica presa em ≤ T** (≤ 1 h, pré-registrado), sem volume por saída, com controle
  positivo (MF-R2-W2-1);
- a regra de versões mistas: LAND com as sessões do projeto fechadas, declarado no material assinado, e
  adopter via `upgrade.sh` com sessão aberta declarado;
- expressões regulares ANCORADAS (`fullmatch` + `re.ASCII`; PID só de dígitos, de 1 a 10, sem zero à
  esquerda), o MESMO texto na W2.6, no check do `/ceo-boot` e no critério de sucesso; proibido reusar
  `_parse_spool_pid` para decidir remoção;
- a lista do que NUNCA se apaga: `.draining.*`, `.malformed.*`, `.quarantined.*`, `.test-origin.*`,
  `.corrupt-header.*`, `.tmp.*`, `*.compact.tmp`, spool ativo, journal com conteúdo, o journal agregado e a
  trava dele, e a família do log de auditoria;
- a recusa da execução da W2.6 por spool ativo ou `.draining.*` com PID vivo (§5.2 do rascunho);
- o caminho de reversão;
- os gatilhos de reversão, em instrumentos LIGADOS e com controle positivo de perda sintética: resíduo
  acima do limiar em 3 medições diárias EM DIAS DISTINTOS E CONSECUTIVOS DE USO (G1, com controle
  positivo também para o H1); linha de timeout depois do LAND sob a carga da W0.5 (G2, rebatizado
  «guarda de regressão»); `.draining.*` ou spool órfão com conteúdo com mais de 24 h (G3, com limiar
  operacional de 100 mil para as travas no H3); decisão perdida no controle (G4); quebra de cadeia
  atribuível à W2 depois da cura (G5); **G6** (perda REAL, só-leitura, fora de hook) e **G7** (contagem
  datada de `would-log`), ambos ATIVOS na W2;
- declarado: o gatilho `revert_trigger_truly_lost_7d` do AMEND-3 está MORTO (`truly_lost` nunca é
  incrementado — só `spool_writer.py:136`, o valor padrão, e `:2562`, a leitura), a reconciliação do
  journal não roda em produção e os journals com conteúdo (215 na releitura do redator, 2026-10-02; o
  consenso contou 214) ficam forense-only — ligar a reconciliação abriria ~76 mil journals sob o
  timeout de 5 s do `SessionStart`: fora da W2; e o resíduo da âncora, reduzido pela leitura do kernel.

- [x] W2.0 **pré-condição do SIGN da W2 — cura da corrida do `agent_spawn`** (condição 67 assinada na
  v1.4.0-rc.1; MF-W2-1). **FEITA: landada com a assinatura do Owner em `65cd50d7` (S361, 2026-10-02); a
  decisão pendente 1 ficou superada.** Os node ids do Check abaixo são os REAIS do pacote landado (relidos
  no `97a78fce` em 2026-10-02: 4 passed); os nomes propostos antes
  (`TestAgentSpawnBarrier::test_barrier_multiprocess` e `TestReadPrevHmacCensus::test_every_call_inside_filelock`)
  nunca existiram. A classe `TestParallelWritersChain` é instável quando o SO não intercala os dois
  gravadores; a cura de CLASSE é um land livre próprio (FX), com os nomes congelados. Texto original do item: `audit_log.py` lê o elo anterior e calcula o HMAC
  FORA da trava (`.claude/hooks/audit_log.py:1265-1276`; a trava, `FileLock`, só cobre o append e o
  `write_last_hmac`, `:1283`): mover chave, elo anterior e HMAC para dentro do `with FileLock(...)`,
  DEPOIS do `rotate_if_needed`. Teste de barreira multiprocesso com N escritores `agent_spawn` em
  paralelo e escritores `audit_emit` (vermelho no HEAD; verde com a cura — a docstring de
  `test_two_writer_chain.py:13-16` diz que ele «pertence à cura da rc.2», que nunca landou); censo AST:
  toda chamada a `read_prev_hmac()` fora de teste fica dentro de `with FileLock(`, com controle
  positivo («cure a classe»); a docstring do `test_two_writer_chain.py` é corrigida. A linha que
  aposenta a condição 67 vai no `CHANGELOG.md` do corte W7, NÃO no pacote da cura. Landa ANTES do SIGN da
  W2 (pacote canônico próprio, recomendado) ou dentro dela (+2 paths). Estimativa: 150-300k tokens + ~50k
  do censo AST, 0 a 1 sessão, com rail. **Rodada 2:** o Check aponta o teste de barreira e o censo AST
  por NODE ID — o `pytest test_two_writer_chain.py` inteiro é VERDE hoje (os testes existentes não cobrem
  o gravador concorrente) e não prova nada; um node id que ainda não existe faz o `pytest` sair ≠ 0, então o
  Check é vermelho antes e verde depois (nomes propostos, fixados no pacote). O LEDGER guarda a execução
  VERMELHA no HEAD ANTES do patch (comando + sha). — Check: python3 -m pytest ".claude/hooks/tests/test_two_writer_chain.py::TestPrevHmacReadCensus::test_every_chain_writer_reads_the_predecessor_under_the_lock" ".claude/hooks/tests/test_two_writer_chain.py::TestReadToAppendWindow::test_no_foreign_append_between_prev_read_and_append" ".claude/hooks/tests/test_two_writer_chain.py::TestParallelWritersChain::test_parallel_spawn_and_sync_emit_writers_keep_the_chain" ".claude/hooks/tests/test_two_writer_chain.py::TestParallelWritersChain::test_parallel_spawn_and_spool_emit_writers_keep_the_chain" -q
- [ ] W2.1 `/debate start PLAN-194` — **rodadas 1 e 2 FEITAS (S361)**, consensos em
  `.claude/plans/PLAN-194/debate/round-1/consensus.md` e `.claude/plans/PLAN-194/debate/round-2/consensus.md`
  (W2 PROCEED na rodada 2), com as propostas da W2, da W3 e da W5c no mesmo `proposal.md` (debate único —
  Approach, item 4; críticos: Segurança, QA e DevOps). Falta o CEO aplicar ao rascunho
  `.claude/plans/PLAN-194/debate/round-2/ADR-055-AMEND-4-draft.md` (PROPOSED; oráculo 0; o arquivo canônico
  nasce só no pacote de ADR — Q5) os ajustes 18 a 22 do consenso da rodada 2, SEM nova rodada: auxiliar de
  saída com `flush`, âncora `min(import, kernel)`, sinal ≤ T, `_OWN_DRAIN_PENDING` fail-safe, calibração
  com o harness real, estatística, H1 com `|D|_min` ≥ 200, G6 ativo e G7 novo, recusa da execução por
  spool ou `.draining.*` com PID vivo, R2-1..R2-7 fechados. — Check: ls .claude/plans/PLAN-194/debate/round-2/consensus.md
- [ ] W2.2 caminho rápido no **auxiliar de saída**, chamado por `_atexit_drain` (`spool_writer.py:2573`)
  E por `_signal_drain_handler`, e NUNCA por `drain_now(force=True)`: sem spool próprio e sem `.draining`
  próprio, não tomar o lock canônico — basta um `stat` do próprio spool e um sinalizador em processo
  (`_OWN_DRAIN_PENDING`), com ZERO `listdir`/`scandir`/`glob`/`iterdir`, contados por envoltório e não
  por tempo; o flush do buffer do journal continua. **O auxiliar faz `sys.stdout.flush()` e
  `sys.stderr.flush()` ANTES da drenagem** (barato; não substitui o prazo): com stdout em pipe, a decisão
  de um hook que não chama `flush` só sai DEPOIS do `atexit`. Os órfãos de outros PIDs ficam com a perna 3
  (o drain do próximo emissor que ganhar a trava). Células `fast_path`: (a) sem spool próprio e com
  envelopes de journal no buffer, o `_flush_journal_buffer` ainda roda na saída; (b) `.draining` próprio
  deixado por exceção no meio do drain: a saída AINDA força o drain (sinalizador em processo — listar o
  diretório não serve, é o que se quer evitar); (c) **o auxiliar de saída é chamado no `atexit` E no
  sinal**, e a lógica não mora no `drain_now(force=True)` (um teste falha se for movida); (d) zero
  chamadas a `os.listdir`/`os.scandir`/`glob`/`Path.iterdir`; (e) o teste 4 de
  `test_spool_drain_contended_skip.py` (`:220-231`: drain forçado com spool próprio sob trava externa ⇒
  `ok=False` + breadcrumb) fica intacto; (f) a recuperação de órfão de PID morto pelo drain OPORTUNISTA
  (`force=False`) do próximo emissor (o teste 3 atual usa `force=True`, `:213-217`). **Células do
  sinalizador (rodada 2):** o próprio `.draining` consumido por OUTRO drainer; spool próprio em quarentena
  ⇒ uma tentativa só; SIGTERM honra o caminho rápido e o prazo; e o `_OWN_DRAIN_PENDING` é FAIL-SAFE —
  liga ANTES do rename, desliga SÓ depois da remoção confirmada, com teste de exceção no meio (o censo dos
  abridores de `audit-pending.*` é guarda da W2.5). — Check: python3 -m pytest .claude/hooks/tests/test_spool_state_amend4.py -q -k fast_path
- [ ] W2.2-bis **(nova, rodada 1; MF-W2-3; reconciliada com o AMEND-4 na rodada 2)** prazo na drenagem
  forçada de saída. **`T_min`** = o MENOR `timeout` entre as registrações de hook do
  `.claude/settings.json` e dos perfis shipados em `templates/settings/` — **3 s hoje** (a registração
  PostToolUse de `check_skill_reference_read.py`; nos perfis shipados o mínimo é 5 s, conferido na S361) —,
  com um TESTE DE DERIVA que recalcula `T_min` dos arquivos e reprova se `EXIT_DEADLINE_S +
  EXIT_MARGIN_S > T_min` (uma registração nova com timeout menor deixa o teste vermelho no mesmo patch).
  Valores INICIAIS (W0.5 os re-mede): `EXIT_MARGIN_S` = 1,0 s e prazo de 2,0 s; regra: margem ≥ p99
  medido × 1,5, e se não couber encolhe o PRAZO, nunca a margem (medição da máquina do Owner; a CI é mais
  lenta). **Âncora (MF-R2-W2-2) = `min(instante do import, início do processo no kernel)`**, com o início
  do processo lido do kernel em stdlib (`ctypes`/`sysctl` no macOS, `/proc/self/stat` no Linux; o
  `_python-hook.sh:413` faz `exec`, então o PID é o mesmo e o instante de início inclui o tempo do
  wrapper); valor inválido, ausente ou no futuro ⇒ vale o do import, com o resíduo declarado (o erro só
  vai para «menos tempo»). O import do `audit_emit` é TARDIO exatamente nos guards mais críticos
  (`check_canonical_edit.py` só o importa dentro de função, `:658`, `:725`, `:1429`, `:1448`, `:1460`),
  por isso a âncora só no import não basta; o censo AST com «armar o prazo no `main`» fica como alternativa
  só se a leitura do kernel não for viável (toca hooks canônicos e pesa no teto de paths). **Controle S1:**
  um guard SINTÉTICO com import tardio depois de trabalho simulado, no molde do `check_canonical_edit.py`.
  Estourado o prazo, o spool fica para a perna 3 — e isso deixa de ser «genuinamente anômalo» (premissa do
  ADR-055-AMEND-3; é a emenda semântica do AMEND-4). É a cura da CLASSE «trabalho longo dentro de guard
  vira allow»: vale para qualquer causa de lentidão. **Sinal de trava canônica presa (MF-R2-W2-1):** o
  spool é PRÉ-cadeia, e o tempo fora da cadeia é janela de adulteração sem elo quebrado; por isso, no salto
  por prazo, UM `stat` do log canônico, e se o log não avança há mais que T (≤ 1 h, pré-registrado) sai um
  breadcrumb `STARVED` com gate e taxa limitada, no formato que `ceo-diagnose.py` e `status.py` já contam
  — breadcrumb, não evento por arquivo, e sem tocar o `audit_emit.py`. Controle positivo: um portador
  externo segura a trava por T e o sinal aparece; um vermelho prova que o G3 de 24 h sozinho não basta.
  **Controle de ENTREGA DE DECISÃO:** um guard que decide BLOCK, com várias saídas concorrentes e o
  diretório cheio, perde a decisão (vermelho, na W0.5) e passa a entregá-la (verde, depois da cura); sem a
  calibração com o harness real, S1 é declarado no material assinado como prova contra um MODELO do
  harness. Se o tempo entre a decisão e o stdout escrito passar da margem por causa do drain oportunista,
  a mesma regra de prazo vale para ele, no pacote da W2. — Check: python3 -m pytest .claude/hooks/tests/test_spool_state_amend4.py -q -k deadline
- [ ] W2.3 **(a antiga W2.3, relocação dos journals e travas por PID para um subdiretório, SAIU na
  rodada 1: criava «duas travas para o mesmo recurso» durante a convivência de versões do
  framework)** No lugar: **journal vazio removido NA ORIGEM, SÓ pela compactação, sob a PRÓPRIA trava do
  journal** (`_journal_compact_drained`, `spool_writer.py:2248-2301`): reexamina a existência do journal
  SOB a trava (hoje o `exists()` vem antes, `:2265`), lê e filtra como hoje, e com resultado VAZIO faz
  `os.unlink(journal)` sob a trava, sem escrever `.compact.tmp`; resultado não vazio segue o caminho
  atual. A remoção pelo dono na saída SAIU (redundante: a compactação é o único produtor de journal com 0
  byte; resíduo raro — `O_CREAT` seguido de falha no `write` — fica para a W2.6). Mais a regra de travas
  acima (nenhum `unlink` de `*.lock` em hook; opção T1). **Nenhum caminho de trava nem de journal muda**
  (por isso a regra de versões mistas é simples): um TESTE DOURADO dos construtores de caminho compara
  byte a byte contra o HEAD. Controle de intercalação determinística por barreira, sem `sleep` (molde de
  `test_spool_drain_contended_skip.py`): mutante 1 — remoção FORA da trava (o envelope do dono vai para um
  inode desligado) ⇒ vermelho; mutante 2 — remoção com restante não vazio (o manifesto de hash do conteúdo
  forense acusa) ⇒ vermelho; a cura ⇒ verde. — Check: python3 -m pytest .claude/hooks/tests/test_spool_state_amend4.py -q -k origin
- [ ] W2.4 **CONDICIONAL — FORA do pacote base da W2 (rodada 2).** Com a W2.3 (nenhum produtor de journal
  vazio) e a regra de travas (nenhum `unlink` de `*.lock` em hook), o pacote base NÃO leva GC no hook, e
  nenhuma varredura própria do diretório inteiro entra no hook (o custo é proporcional ao estoque, ~228
  mil nomes). O GC de journal de PID morto só volta como PACOTE PRÓPRIO, se o fluxo medido depois do LAND
  ficar acima do limiar (H1), com as condições do AMEND-4 §4.5: de carona na listagem da fase 2, DEPOIS de
  soltar a trava canônica; teto de ≤ 200 arquivos e ≤ 50 ms por execução (a confirmar na W0.5); só o padrão
  de journal, só 0 byte, PID morto; reexame sob a trava do journal; nenhum `*.lock`; a lista do que NUNCA
  se apaga; e a tabela de predicado pré-registrada, com quase-acertos tirados do censo vivo (travas de
  outros módulos, `*.compact.tmp`, journal agregado) e os journals com conteúdo como controle, com o
  porquê de cada diferença em relação ao predicado da W2.6. O Check `-k gc` SAIU (casava o nome do módulo
  e não provava a W2.4). — Check: none (condicional; sem pacote na W2 base — volta só com o fluxo medido acima do limiar)
- [ ] W2.4-bis **(nova, rodada 1; W2-7; ampliada na rodada 2)** a W2 se observa pelo RESULTADO, sem
  evento por arquivo e sem tocar o `audit_emit.py` (um evento emitido por processo sem spool recriaria os
  3 arquivos que a W2 quer deixar de criar): **(a) check advisory no `/ceo-boot`**, dentro do pacote do
  item livre L2 (mesmo arquivo, `ceo-boot.py`; mapa de colisões): a contagem POR NOME dos 3 padrões, numa
  listagem sem `stat` por entrada; os journals com 0 byte, com `stat` limitado a 2.000 (H2 ≤ 1.000 decide;
  acima, «≥ 2.000»); a idade do `.draining.*` mais velho; a contagem e a idade do spool ÓRFÃO COM CONTEÚDO
  de QUALQUER idade, como TAXA (é o resíduo visível de `exit_deadline_skip`); a contagem de travas — **a
  partir de 100 mil, RECOMENDA rodar a W2.6**; no MÁXIMO uma linha por execução, e breadcrumb com taxa
  limitada só quando um gatilho disparar, nunca de hook. **(b) G6 e G7 (MF-R2-W2-3)**, verificadores
  SÓ-LEITURA, FORA de hook, rodados no pós-LAND e no nightly: **G6** conta a perda REAL — `record_id` com
  `commit` num journal de PID morto, ausente do log canônico (e dos arquivos rotacionados) e de todo
  spool ou `.draining.*`; `record_id` em `.malformed.*`, `.quarantined.*` ou `.test-origin.*` conta como
  QUARENTENADO, não como perdido; controle positivo: cópia descartável com uma linha canônica removida ⇒
  conta 1. **G7** é a contagem datada de `would-log` (`audit_log.py:1324-1328`: num `FileLockTimeout`, a
  linha vai só para o breadcrumb `lock timeout (stale?) would-log=`), com controle positivo. **(c) G1**
  ganha controle positivo também para o H1 e cadência de 3 execuções em dias DISTINTOS e consecutivos de
  USO. **(d)** contagens da W2.6 no LEDGER e um teste que afirma contagem registrada = arquivos apagados.
  O Check ganha um seletor dos testes NOVOS (hoje ele é verde com os testes existentes de `/ceo-boot`, e
  não prova nada); nomes de seletor propostos, fixados no pacote. — Check: python3 -m pytest .claude/scripts/tests/test_ceo_boot.py .claude/scripts/tests/test_ceo_boot_enhanced.py .claude/hooks/tests/test_spool_state_amend4.py -q -k "spool_residue or loss_verifier or would_log_count"
- [ ] W2.5 invariantes provados em teste de estresse: (i) invariante por CONJUNTO — todo `record_id`
  emitido aparece exatamente UMA vez no log canônico («contagem igual» esconde perda somada a
  duplicata; `record_id` em quarentena aparece zero vezes e o arquivo está no disco); (ii)
  `verify_chain()` (`.claude/hooks/_lib/audit_hmac.py`) íntegro sobre ≥ N elos (cadeia vazia ou curta é
  verde por vácuo) — **composição da cadeia (rodada 2):** N ≥ 1.000 elos, com ≥ 100 `agent_spawn`, ≥ 100
  lotes de drain (`_drain_epoch`), ≥ 50 transições ADJACENTES entre classes de escritor e ≥ 1 rotação no
  meio; (iii) escritores mistos em paralelo: `agent_spawn` (depois da cura W2.0), `audit_emit`, drainers
  oportunistas e forçados, saídas pelo caminho rápido, saídas cortadas pelo prazo, kill -9 no meio do
  drain e reuso de PID; e a asserção de que journals COM conteúdo foram produzidos ANTES do drain; (iv)
  **mutantes plantados M-a..M-d**, cada um reprovando o teste: **M-a** — a fase 5 apaga um `.draining`
  parcialmente consumido (perda); **M-b** — a guarda `_drain_sha256` desligada na recuperação
  (duplicata); **M-c** — o estouro do prazo apaga ou renomeia o próprio spool (perda); **M-d** — a fase 2
  renomeia o spool de um PID vivo sem a trava do spool (append em voo roubado, com barreira); os
  mutantes da antiga W2.4 (GC que apaga journal com conteúdo; caminho rápido que pula quem tem spool)
  vivem nos testes `origin` e `fast_path`; (v) **guardas mecânicas:** o inode de cada `*.lock` estável do
  1.º ao último uso no estresse, e o censo dos abridores de `audit-pending.*` como teste. Afirmações
  finais: zero breadcrumb de perda (`would-log`, `spool append failed`, `journal flush failed`) e nenhum
  `.draining.*` nem spool órfão com conteúdo ao fim. — Check: python3 -m pytest .claude/hooks/tests/test_spool_state_amend4.py -q -k invariant
- [ ] W2.6 limpeza do estoque do state dir VIVO — **RECORRENTE sob a regra de travas T1** (rodada 2).
  **Decisão do Owner (S359, 2026-09-30): «Script pronto, você roda depois (Recomendado)»** (antiga OQ-9,
  resolvida). Script confinado entregue ao Owner, fora do repositório, confinado ao state dir, com
  predicado próprio (a W2.4 condicional, que adquire a trava sem bloquear dentro do hook, é outra coisa).
  **Predicado pré-registrado (AMEND-4 §5.2; uma ação por célula):** nome casando EXATAMENTE um dos 3
  padrões (as regex ancoradas do AMEND-4 §4.7, `fullmatch` + `re.ASCII`, PID só de dígitos, nunca
  `_parse_spool_pid`), arquivo comum de 0 byte, `st_nlink == 1`, PID morto, família sem conteúdo e mtime ≥
  10 min ⇒ **APAGA** (a simulação conta; só `--apply` apaga); a mesma célula com PID VIVO (inclusive PID
  reusado por processo alheio) ⇒ **MANTÉM a família inteira**, contada como «pulada: PID vivo»; qualquer
  arquivo da família com mtime < 10 min ⇒ **RECUSA a execução inteira**; **spool ativo ou `.draining.*` com
  PID vivo ⇒ RECUSA a execução inteira** (prova positiva de emissor vivo DESTE projeto, porque trava
  aberta e `flock` não mudam o mtime — acréscimo da rodada 2); journal com conteúdo ⇒ **MANTÉM a família
  inteira** (entra no manifesto de hash); symlink, hardlink, diretório ou outro tipo ⇒ **MANTÉM** + aviso;
  quase-acertos (travas de outros módulos, `statusline-snapshot.json.tmp.N`, o journal agregado e a trava
  de agregação, `*.compact.tmp`, zero à esquerda, dígitos não ASCII, `\n` final) ⇒ **MANTÉM**; state dir
  symlink, de outro dono ou com modo ≠ 0700 ⇒ **RECUSA a execução**. **Endurecimento da rodada 1
  (MF-W2-6):** resolve o state dir pelo resolvedor `_lib/runtime_paths.py`, nunca por slug derivado à
  mão (ADR-001, marcador M4), e recusa se `CEO_AUDIT_LOG_DIR` ou `CEO_AUDIT_LOG_PATH` estiverem
  definidos; abre o diretório com `O_RDONLY | O_DIRECTORY | O_NOFOLLOW`; remove RELATIVO ao descritor do
  diretório (`os.unlink(nome, dir_fd=dfd)`), sem seguir link; reexamina tipo, tamanho, contagem de links,
  `(st_dev, st_ino)` e a família imediatamente antes de cada remoção; a simulação conta POR CÉLULA;
  manifesto de hash dos journals com conteúdo antes e depois (qualquer diferença reprova); re-contagem
  pelo mesmo método do critério de sucesso. Com todas as sessões do projeto fechadas não há adquirente
  vivo, então a W2.6 PODE apagar travas. **Recorrência:** o estoque de travas volta à ordem de ~150 mil em
  semanas (inferência de um crítico, não refeita), então a W2.6 é manutenção RECORRENTE do Owner, a cada ~2
  a 4 semanas de uso intenso, quando o `/ceo-boot` acusar ≥ 100 mil travas (W2.4-bis); se precisar rodar
  mais de 1× por mês, isso é gatilho da T2 (pacote de kernel próprio). **Pré-condição — decisão 2 ACEITA
  pelo Owner (ratificação de 2026-10-02, `debate/round-3/approved.md`):** todas as sessões DESTE projeto
  fechadas (o state dir é por projeto desde a W1 do PLAN-182) há ≥ 10 min, com o predicado acima.
  **Posição — decisão do Owner S362:** a 1.ª execução roda DEPOIS do LAND do U2-B (o pacote que remove o
  journal vazio na origem, W2.3), numa sentada do Owner sem senha, com o CEO em fechamento de sessão;
  contagem antes/depois no LEDGER pelo mesmo método do critério de sucesso. Motivo: é o U2-B que impede o
  journal vazio de voltar, e as travas crescem sempre (T1); antes dele, a limpeza só alivia o sintoma até
  o acúmulo voltar (ritmo não medido; teto estimado de ~300 mil pelo espaço de PIDs do macOS, lane `H-02`;
  233.055 entradas no state dir vivo, medidas pelo CEO em 2026-10-02). Depois da W2.6, o teto de agentes
  vivos sobe de 8 para 12. As travas voltam por desenho (T1). — Check: none (operação do Owner; contagem no LEDGER)
- [ ] W2.7 rail nos bytes canônicos até rodada limpa (regra de parada pré-registrada antes da 1.ª
  rodada: ≤ 3 rodadas; NO-GO só por P0 ou afirmação falsa); SIGN/LAND. — Check: python3 .claude/scripts/check-ceremony-script.py

**Seletores dos Checks (rodadas 1 e 2).** Cada item da W2 usa um seletor `-k` DISTINTO — `fast_path`
(W2.2), `deadline` (W2.2-bis), `origin` (W2.3) e `invariant` (W2.5); o `gc` SAIU com a W2.4 condicional —,
e **cada seletor casa SÓ os testes do próprio item**: nenhum seletor é substring do nome do módulo de teste
(o `pytest -k` casa também nomes de módulo e de classe; por isso o módulo se chama
`test_spool_state_amend4.py`), e os nomes de teste carregam um só seletor. A guarda de seletor afirma as
duas coisas: o seletor que casa ZERO testes reprova (o `pytest` sai 5 quando nada é coletado, e o Check não
pode mascarar esse código) e o seletor que casa teste de OUTRO item também reprova (um Check verde por
seletor vazio ou largo demais não prova nada; o lint geral de seletores fica adiado, vale como regra de
texto aqui).

**Controle vermelho→verde (rodadas 1 e 2):** a W0.5 pré-registrada reproduz os timeouts com ~220 mil
entradas e a decisão de guard perdida (vermelho); depois da cura, o controle de ENTREGA DE DECISÃO
(W2.2-bis) fica verde. **A razão p95 cheio/vazio ≤ 1,2 vale SÓ nas células SEM spool próprio;** nas células
COM spool próprio e ~150 mil travas (o regime permanente sob T1) o esperado é decisão entregue e prazo
respeitado, SEM exigir razão (o caminho rápido sozinho não cura quem tem conteúdo). A medição é FORA do CI
(a razão medida e o controle de entrega de decisão substituem o antigo «latência igual à do dir vazio»;
nenhuma asserção de tempo absoluto em teste do CI). Sem a calibração com o harness real, o S1 é declarado no
material assinado como prova contra um MODELO do harness. Os critérios que BARRAM o SIGN são os de SEGURANÇA
(MF-W2-3 e MF-W2-5): o controle de entrega de decisão passa de vermelho a verde; o invariante por
conjunto fica verde; `verify_chain()` fica íntegro sob estresse com escritores `agent_spawn`, depois da
cura da W2.0. `truly_lost` não serve de gatilho: está morto. A contagem de arquivos é higiene: o critério
primário é o FLUXO H1 (artefatos de PID morto por PID emissor distinto na janela, lendo `pid` e `wall_ns`
do log canônico), com `|D|_min` ≥ 200 pré-registrado — abaixo dele, reprova — que não fica verde por
vácuo num dia leve nem envelhece com o estoque; o teto absoluto de 1.000 vira limite secundário de
sanidade e conta SÓ journals (as travas vão à parte, sem limiar de segurança: crescem 2 por PID novo);
denominador zero reprova (ver «Success criteria»). No vivo, a contagem é do state dir INTEIRO.
**Dependências:** W0.5 pré-registrada; debate único do plano (PROCEED da W2 dado na rodada 2); a cura do
`agent_spawn` (W2.0) landada antes do SIGN ou dentro do pacote; `ADR-055-AMEND-4` em rascunho PROPOSED;
vaga: a seguinte à que a W7a do PLAN-183 ocupar (a da W1) — ordem decidida pelo Owner, «Regra de WIP» no
topo. **Prazo:** sem data externa; recomendado antes do corte W7. **Fora (follow-up):** rotação do
`audit-log.errors` e contagem por classe no boot (lane `H-03`); ligar a reconciliação de início de
sessão (rodada 1). **Estado medido na S361 (2026-10-01, ~20:08Z):** o
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

**PROCEED na rodada 3, CONDICIONADO à decisão pendente 3 — decisão do Owner S361 (Q3); debate FECHADO.** A W3
saiu `design-coherent` com 3 de 3 críticos (consenso FINAL em `.claude/plans/PLAN-194/debate/round-3/consensus.md`;
nenhum P0, nenhuma afirmação FALSA no plano), depois do RUN-ANOTHER-ROUND das rodadas 1 e 2 (a W0.6 mudou a
arquitetura da decisão de confiança). **Está liberada do portão do debate, mas NENHUM pacote começa antes da
decisão pendente 3 ESCRITA pelo Owner como ramo (ii) ou ramo (i): é ela que retira o VETO de cadeia de
suprimento (T-8).** «Confiança no registro» mantém o VETO e vira ESCALATE-TO-OWNER (múltipla escolha); recusar
o `node` devolve o plano B (re-pin manual). **Condições:** as 23 do consenso r3 §2, aqui só pelo NÚMERO — 1 a 5
antes dos pacotes (decisão 3; decisões 4, 5 e 6 no AMEND-1 antes do 1b; plano reconciliado com o AMEND-1, que
prevalece; hospedeiro da guarda; dono para a lacuna da família do log, até o SIGN do 1b); 6 a 9 no 1c/1b (a 8 é
item livre, no `/ceo-boot`); 10 a 15 e 17 no 1a (a 13 e a 14 também nos Checks); 16, em texto; 18 a 21 no
runbook, no material de cerimônia e no 1a; 22 e 23, a sequência com o corte e a validade do Check. Condição
não cumprida reprova o SIGN do pacote correspondente, não o debate (o rail V2 confere). Base das condições:
MF-W3-1..11 (`round-1/security-engineer.md`) e MF-R2-W3-1..8 (consenso r2). `needs_debate=true` (o mesmo que
«Debate: SIM» abaixo). A 3.ª vaga inicial segue ocupada pela W3b (Q8, S361) até a decisão 3.

**Objetivo:** uma versão nova do Codex passa a valer para o rail sem cerimônia por versão, desde que a
procedência seja conferida automaticamente; o Owner deixa de assinar a cada atualização **no hook do
rail; os cortes de release seguem ancorados no manifesto assinado (pergunta 7, respondida na rodada 1)**.
**Desenho decidido (mesma fonte; (a) reescrito na rodada 1 e ajustado na rodada 2):** (a) o **verificador
roda em processo PRÓPRIO, fora de qualquer guard**, em duas fases — staging em prefixo próprio →
procedência (atestado SLSA v1 do CI da OpenAI, conferido presente em 0.156.1, 0.159.2, 0.159.3 e 0.160.0,
e **assinatura conferida pelo `sigstore.verify` COM política de identidade**, ver a pergunta 2) → sonda +
canário (W3.3) → registro do sha256 verificado → promoção ao global **a partir dos bytes VERIFICADOS**,
com a MESMA versão e o MESMO sha, sem assinatura do Owner; o **hook só faz hash e consulta local, nunca
usa rede**, e sha fora do manifesto e do registro ⇒ bloqueio, nomeando o verificador. Motivo: a verificação de procedência DENTRO do hook
PreToolUse viraria fail-OPEN por timeout (o hook tem timeout de registro de 210 s, `.claude/settings.json:285`, e a
verificação baixa ~331 MB); (b) sentinela automática com corpus fixo de defeitos que avisa se o revisor
piorar, **sem travar** — **pendente de decisão do Owner (S361; decisão pendente 4):** o corpus travado do
ADR-111 não está no repositório, e a recomendação é a W3 landar SEM sentinela, declarada; (c) modelo e
esforço fixos no argv do rail (cura a lane `CX-07`, antes no backlog) — dois eixos, conforme «Base do
argv fixo», **pendente de decisão do Owner (S361; decisão pendente 5)**; (d) cada veredito registra
versão, modelo e esforço. **Custo declarado na fonte:** emenda do ADR-182 + debate de segurança + 1
cerimônia — e, desde a rodada 1, o pacote de kernel de registro de ações e a W0.6 (feita) e, desde a rodada
2, a dependência de `node` + `sigstore` e os pacotes 1b, 1a e 2 em série. **Binário global do Codex
(decisão do Owner S362, 2026-10-02):** 0.156.1 até a sentada do re-pin manual (RP, plano B no fim desta
seção); nessa sentada o Owner instala a 0.160.0 e assina o pacote; dali até o LAND da W3 (depois da 1.4.3;
a regra termina nele e segue pelo procedimento da W3.6), 0.160.0. **Nunca `npm update -g`**: fora da sentada
do RP, o MANIFESTO por sha exato (`codex-cli-pin-manifest.json`) recusaria o binário novo e fecharia o rail: o hook
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

**Base do argv fixo — decisão de desenho da rodada 1 (C6).** O binário é automático; modelo e esforço
são DOIS eixos distintos e ficam em constante canônica, e uma cerimônia por GERAÇÃO de modelo é aceitável
e desejável. `--ignore-user-config` entra se a sonda da W3.3 confirmar a flag na versão, com uma medição
de que `memories` não carrega com ela. Cada rodada registra versão, sha do payload, modelo pedido e
modelo servido (se o `session_meta` o expuser) e esforço; o id fixado entra no
`.claude/scripts/model-deprecations.json` (oráculo 0), e id indisponível ⇒ contagem diária no boot,
nunca silêncio. **Recomendação do CEO, pendente de decisão do Owner (S361; decisão pendente 5):**
`gpt-6-astra` + `xhigh`, o par em uso de fato, condicionado ao re-teste da Q11; o id entra em
`_VALID_MODELS` no pacote 2 da W3, depois da W3b; trocar de modelo passa a ser cerimônia por GERAÇÃO.

**Perguntas de desenho — respostas da rodada 1 do debate** (consenso §6; valem como desenho de entrada da
rodada 2, não como veredito do AMEND-1; as perguntas 8 a 10 são novas):
1. **Onde o sha verificado fica gravado** — não pode ser o manifesto (`codex-cli-pin-manifest.json`,
   oráculo 1), que só muda por cerimônia. **Resposta:** num registro em diretório resolvido por
   `runtime_paths` (`.claude/hooks/_lib/runtime_paths.py`), FORA de `state/` (alcance do GC da W2) e da
   árvore git, com modos 0700/0600, só-acréscimo e a evidência completa. Leitores: SÓ o núcleo do hook
   e a CLI `--verify-codex-pin`; o passo 15 do release (o validador do veredito), o `gen-envelope-ga.py`
   e o kit NUNCA o leem. Vale só para este repositório (adopters seguem em INFRA aberto: sem
   `.claude/governance/` neles, o pin resolve como `infra`). Resíduo de mesmo UID declarado
   (CLAUDE.md §5). O registro nunca vira atalho por mtime ou tamanho que dispense o hash a cada
   invocação. **Rodada 2 (MF-R2-W3-5):** o registro é protegido contra escrita do PRÓPRIO agente — Edit,
   Write e Bash, inclusive acréscimo por redirecionamento —, com controle positivo (escrita no formato do
   agente ⇒ BLOCK). O «a conferir» do R-5 do rascunho do AMEND-1 se resolve no pacote 1b: o sandbox está
   desligado (`.claude/settings.json:8`, `"enabled": false`) e a busca rápida do sintetizador da rodada 2
   NÃO achou guarda dedicada à família do log de auditoria — resultado inconclusivo —, então, se não
   houver guarda, o pacote cria a guarda do registro e registra a lacuna da família do log como item
   próprio.
2. **Como conferir a assinatura do atestado num framework só-stdlib (CLAUDE.md §4).** **Resposta
   (rodada 2, com a W0.6, feita em 2026-10-02):** o comando `npm audit signatures` NÃO serve — dá falso
   verde com payload adulterado, atestado removido, atestado de OUTRO repositório e cache quente sem
   rede, e não aceita pacote global (`EAUDITGLOBAL`); a biblioteca `sigstore` chamada COM política SERVE
   (verde só no íntegro; recusa toda adulteração e toda identidade divergente). **V-5 = `sigstore.verify`
   COM política:** `certificateIdentityURI` exato = o SAN do `rust-release.yml` com a tag
   `rust-v<X.Y.Z>` da versão BASE (`https://github.com/openai/codex/.github/workflows/rust-release.yml@refs/tags/rust-v<X.Y.Z>`);
   `certificateIssuer` exato = `https://token.actions.githubusercontent.com`; `certificateOIDs` com os ids
   imutáveis do repositório (`965415649`) e do dono (`14957082`); sobre os bundles que o PRÓPRIO
   verificador buscou; literais em constantes canônicas com teste; NUNCA `npm audit signatures`. O
   verificador exige os DOIS bundles (lançador e plataforma): a antiga A-12 passa a ser dele (V-P3), e as
   células A-14 (identidade divergente com digests coerentes) e A-15 (assinatura inválida) viram RECUSA —
   **sai «aceita e declarada»**. **Vínculo:** o sha512 do tarball baixado é igual ao digest do `subject`
   do bundle VERIFICADO, lido dos MESMOS bytes passados ao verificador; o `dist.integrity` vira só
   cruzamento. Coerência de digests NÃO é autenticidade e não se chama «assinatura conferida»; nada de
   criptografia escrita à mão. **Dependência nomeada:** o verificador vira orquestrador Python mais um
   auxiliar `node` para a assinatura — exceção NOMEADA ao «stdlib-only», com `node` por caminho absoluto e
   versão mínima, declarada no `SBOM.md`; o vínculo atestado → tarball → payload segue na stdlib
   (`urllib` com TLS verificado, `tarfile` em fluxo, `hashlib`) e o download NUNCA roda no hook.
   **Empacotamento = decisão pendente 3**, (i) módulo interno do npm ou (ii) `sigstore` em versão exata
   com lockfile — e «confiança no registro» NÃO é mais resíduo aceitável: virou ESCALATE (a W0.6 é a
   evidência de que há mecanismo que a dispensa). A procedência vale para o artefato de PLATAFORMA
   (`@openai/codex@<v>-darwin-arm64`, 44 arquivos e ~331 MB na 0.159.3; o nome `@openai/codex-darwin-arm64`
   é um ALIAS, 404 como pacote), que é onde está o payload — o pacote `@openai/codex@<v>` é só o
   lançador (3 arquivos); os dois têm atestado SLSA v1 na 0.159.3.
3. **O que a faixa do `codex-cli-pin.txt` passa a dizer** (o validador do veredito,
   `validate-pair-rail-verdict.py`, membro do manifesto ADR-192, lê a faixa desse arquivo —
   `--codex-cli-pin-file`, `release.yml:760`). **Resposta:** a faixa fica `>=0.128.0,<0.157.0`, INTOCADA
   na W3, e os cortes seguem ancorados no manifesto; o corte declara o 0.156.1. O limite do
   `parse_semver` do validador é declarado no AMEND-1: ele casa por prefixo (`re.match`,
   `.github/scripts/validate-pair-rail-verdict.py:355-359`), então o passo 15 NÃO garante «só estável» —
   quem garante é o sha do manifesto.
4. **Só versões estáveis, nunca alpha** (era a recomendação da antiga OQ-3). **Resposta — carência de 48
   h** contada do horário de publicação NO REGISTRO (não do 1.º avistamento local), em constante
   canônica com teste. A candidata é a estável mais nova com idade ≥ 48 h, ≤ `latest`, sem `deprecated`
   e ≥ piso do manifesto — NUNCA «== `latest`» (pela cadência medida, «== `latest` + 48 h» deixaria o pin
   parado na maior parte dos dias). A `latest` fica como teto e como condição necessária («a `latest`
   atual é estável e ≥ candidata»), nunca como prova de estabilidade; `deprecated` é recusada; nunca abaixo
   do piso. **Gramática estrita (MF-W3-4):** base estável `X.Y.Z` mais o sufixo EXATO do triple da
   plataforma; qualquer outro pré-release é recusado (as dist-tags trazem alpha com sufixo de
   plataforma, como `0.159.0-alpha.12.1-darwin-arm64`). Efeito: sempre existe versão elegível e o pin
   anda uns 2 dias atrás da `latest`, sem cerimônia; a adoção roda sob demanda ou no máximo 1× por
   semana, sob o freio Q2. Medido pelo sintetizador do consenso em 2026-10-02T00:20Z: 23 estáveis desde
   2026-08-25, mediana de 22,0 h entre estáveis; `latest` = 0.160.0 (~4 h) e a 0.159.3 (~25 h) ainda NÃO
   elegíveis; a 0.159.2 (~48,3 h) elegível. A espera de 48 h é `external_wait` (relógio do npm).
5. **Sem rede ou sem atestado.** **Resposta:** TODO «binário presente, mas não verificado» — sem rede,
   sem atestado, atestado inválido, identidade divergente, carência não cumprida, sonda reprovada,
   registro ausente ou corrompido — é SECURITY, fail-CLOSED: saída 1 e bloqueio. INFRA (3) só no que já
   era INFRA no ADR-182 §2: no hook, INFRA não executa o binário e tira a revisão em silêncio
   (`check_pair_rail.py:783-786` e `:1512-1524`, «fail-OPEN advisory»). Falha de rede é falha do
   VERIFICADOR (versão não registrada), nunca INFRA do hook. O texto antigo «o rail segue na última
   versão verificada» só vale com cópia retida (a promoção em duas fases): fora dela, vira «**bloqueia
   até verificar ou reinstalar a versão verificada**».
6. **Rodadas manuais e o daemon.** **Resposta:** os chamadores LIVRES (`codex_invoke.py:193`,
   `run-promotion-gate.py`) passam pelo núcleo de verificação; os CANÔNICOS e o daemon ficam
   DECLARADOS no material assinado, com o estado do opt-in: `.claude/hooks/codex_review_user_code.py:131`
   (`codex exec --sandbox read-only`; hook `Stop` AUTOMÁTICO sob o opt-in, registrado em
   `.claude/settings.json:636-645`), `.claude/workflows/council-audit.js:325`, o `codex exec review`
   manual e o daemon `app-server` (que se atualiza sozinho fora do pin — lanes `CX-04` e `CX-06`).
   `run-promotion-gate.py` só chama `codex --version` (`:198` e `:212`).
7. **Cortes de release (acrescentada na S361).** O passo 15 do `release.yml` (`:754-763`) passa o
   manifesto assinado ao validador do veredito, que exige `codex_payload_sha256` IGUAL à entrada do
   manifesto da ÁRVORE TAGUEADA (`validate-pair-rail-verdict.py:745-763`), e o `gen-envelope-ga.py` do
   kit recusa sha ou versão diferentes do manifesto (`pinned_codex`, `PLAN-193/gen-envelope-ga.py:213-243`).
   **Resposta (a evidência no disco refutou a premissa «a W3.6 só depois da W7»):** o corte já é
   independente do Codex GLOBAL. O runner do re-pass (`PLAN-193/repass-ga/run-ga-repass.sh:242-306`) usa a
   rota 1 só se o payload global confere E a versão é a pinada; senão, a rota 2 — `npx` em cache próprio,
   que morre se a versão do npx ≠ o manifesto, verifica pelo mesmo oráculo e põe um shim no PATH (foi a
   rota do GA 1.4.1: `PLAN-192/repass-ga/PROVENANCE-ga.md:6`, «rota do codex: npx (cache proprio)»); e o
   envelope lê o Codex da PROVENANCE, nunca da máquina (`gen-envelope-ga.py:213-243`). A âncora segue
   intacta: manifesto assinado da árvore tagueada, validador e faixa sem mudança. **Rodada 2 — a rota 2
   dos runners atuais EXECUTA antes de verificar:** o `npx -y "$CODEX_PKG" --version` roda ANTES do
   oráculo `--verify-codex-pin` (o payload materializado pelo `npx` executa uma vez sem ter sido conferido
   contra o manifesto; só o cache é trocado, sem `.npmrc` vazio nem `--ignore-scripts`), e o shim faz
   `exec` do LANÇADOR, não do payload verificado (conferido no `run-ga-repass.sh`, `:266` contra
   `:282-286`, e no shim, `:302`). **Decisão:** a rota 2 é INVERTIDA no kit da 1.4.3, como pré-condição da
   W3.6 (ver a W3.6 e a W7), e a W3.6 roda LOGO DEPOIS do LAND da W3, não depois da W7. Resíduos declarados:
   o corte depende da rede e de a 0.156.1 seguir baixável no registro (R-13), e o **rollback da W3 exige
   rede** (R-16: sem rede, o rail bloqueia até haver rede — a via de instalação da versão do manifesto
   também depende de rede; o cache verificado retido das 2 últimas versões vira follow-up).
8. **A sonda vira automática?** **Resposta:** sim — automática, dentro do verificador, DEPOIS da
   procedência e ANTES do registro; bloqueante; cobre os subcomandos e as FLAGS dos chamadores e inclui o
   canário funcional (W3.3).
9. **A sentinela de qualidade** (desenho (b)). **Resposta:** o gatilho do ADR-111 §2 (governança do
   corpus travado do pair-rail) fica PRESERVADO e declarado NÃO AVALIÁVEL até existir corpus com sha e
   linha de base (m ≥ 3, variância medida com o mesmo binário): o corpus travado do ADR-111 NÃO está no
   repositório (`git ls-files | grep -c corpus/locked` = 0; `.claude/plans/PLAN-081/corpus` não existe).
   Vai ao Owner (decisão pendente 4).
10. **Modelo e esforço no argv.** **Resposta:** dois eixos; constante canônica; `--ignore-user-config`
    se a sonda confirmar; o id fixado entra no `model-deprecations.json` (ver «Base do argv fixo»;
    decisão pendente 5).

**Identidade do construtor e chave de aceitação (MF-W3-4 e MF-R2-W3-1; constantes canônicas no
verificador, com teste).** Medidos na W0.6 (0.160.0 e 0.156.1): repositório `https://github.com/openai/codex`,
workflow `.github/workflows/rust-release.yml`, ref `refs/tags/rust-v<X.Y.Z>` amarrada à versão BASE,
emissor OIDC `https://token.actions.githubusercontent.com`, `predicateType`
`https://slsa.dev/provenance/v1`, e `subject` igual ao purl do pacote de PLATAFORMA
(`pkg:npm/%40openai/codex@<X.Y.Z>-darwin-arm64`); ids IMUTÁVEIS do repositório (`965415649`) e do dono
(`14957082`) na política do `sigstore.verify`. **A âncora do vínculo é o `subject` do bundle VERIFICADO**
(`dist.integrity` só cruza). A chave de aceitação é o sha256 do payload LOCAL igual ao sha256 do ÚNICO
membro regular no caminho exato do tarball atestado, lido em fluxo: sem extrair para disco, sem symlink
nem hardlink, sem nome duplicado; o metadado local (versão do lançador) é só dica de busca. O `.npmrc` e as
variáveis `npm_config_*` podem redirecionar a raiz de confiança do npm: o verificador roda com registro
fixo, sem `.npmrc` do usuário, com essas variáveis limpas e com **caches do npm e do TUF NOVOS a cada
execução, com asserção de vazio no início** (o cache quente é célula de teste); falha de TLS é fail-CLOSED.
**Lista FECHADA de hosts:** o registro e o CDN do cache TUF (`tuf-repo-cdn.sigstore.dev`) — o rascunho do
AMEND-1 dizia «MESMO host», e a W0.6 mediu o 2.º host. **Tetos** (2× o maior medido na W0.6): packument
~33,6 MB, atestado ~30,3 KB, tarball comprimido ~268,6 MB, membro `bin/codex` ~483,1 MB, descomprimido
total ~666 MB.

**CLI e consumidores do registro (C5).** O registro é uma 2.ª fonte de verdade fora da árvore git:
`--verify-codex-pin` fica SÓ-MANIFESTO por padrão (o campo `pin_source` do JSON distingue manifesto de
registro); a aceitação pelo registro (`verified_auto`, `pin_source == "registry"`) só com a flag explícita
`--allow-auto-pin` (nome do AMEND-1 C-02). **Um literal só, o do código: `registry`** (o texto anterior
dizia `registro`; o Check afirma o literal do código). O kit com binário só auto-registrado FALHA no
pré-voo, antes de qualquer rodada paga. O contrato de cada consumidor (hook, Gate 4 do
`pair-rail-gate.sh`, `run-ga-repass.sh`, release) fica escrito no AMEND-1. **Nota de operador (rodada
2):** com o global auto-pinado (≠ manifesto), o Gate 4 da fase 6 do `pair-rail-gate.sh` FALHA por desenho
(pré-voo da trilha de release, «antes da tag»); a mensagem dele passa a nomear a rota 2 do runner, com
uma nota de operador.

**Evidência da aceitação: evento durável na cadeia HMAC (consenso §2(e); decisão pendente 6).** Cada
aceitação automática SUBSTITUI uma assinatura humana, então vira evento na cadeia como ação registrada
em `_KNOWN_ACTIONS`, com versão, triple, sha256 do payload, `integrity`, digest do atestado e
identidade. Hoje uma ação fora de `_KNOWN_ACTIONS` vira breadcrumb (`audit_emit.py:5260-5262`) e o
`pair_rail_codex_pin_mismatch` (`check_pair_rail.py:1204`) tem 0 ocorrências no `audit_emit.py`.
Veículo: UM pacote de kernel de registro de ações (`audit_emit.py`, canônico), que também promove o
`pair_rail_codex_pin_mismatch`; vai em série com a W1a do PLAN-195 e landa ANTES da W3.6. O precedente do
AMEND-3, de preferir breadcrumb para não tocar o kernel, não se aplica: ali não se substituía assinatura.
A alternativa (evidência só no registro) exige decisão ESCRITA do Owner e o resíduo no AMEND-1. **Rodada
2 — campos:** a linha do registro e o evento HMAC levam também o `signature_mode`, as versões de `node`,
npm e `sigstore`, o sha do lockfile (ou do módulo, no ramo (i)), o digest da raiz TUF e o manifesto
sha256 por membro; trocar o verificador é «instrumento mudou»; o `verifier_sha256` e o sha do lockfile
entram no conjunto permitido da revalidação do hook (H-07).

**Paths — pacotes em série (consenso r3 §2, condição 3; o AMEND-1 prevalece sobre este plano; ≤ 8 paths cada; o
oráculo `--is-canonical` roda em todos na abertura de cada pacote, inclusive no auxiliar JS).** Ordem: **[1c] →
1b → 1a → 2**, mais o de kernel; o 1b vem antes do 1a porque o verificador reaproveita funções e constantes do
núcleo (AMEND-1 §4.1). **1c** — a guarda do registro e a das FONTES do verificador (condição 6; hospedeiros na
linha própria do mapa de colisões), PRIMEIRO da fila e landada ANTES do 1.º LAND do 1a; só existe se o 1b
passar de 8 paths, senão entra no 1b. **1b** — `ADR-182-AMEND-1-codex-auto-pin-provenance.md` (1, novo; rascunho
em `.claude/plans/PLAN-194/debate/round-3/`; o arquivo canônico nasce no pacote de ADR, Q5),
`.claude/hooks/check_pair_rail.py` (1; consulta ao registro, H-07, `_emit_audit()` ligado ao `emit_generic`,
sumidouro de teste só em modo de teste), `test_check_pair_rail_auto_pin.py` (0) e `docs/CROSS-LLM-THREAT-MODEL.md`
(0; o T-8, `:328`, no MESMO pacote) — **4 paths sem a guarda**; a guarda soma os hospedeiros e o teste dela, e
se o total passar de 8 ela sai como 1c. **1a** — `.claude/scripts/codex-auto-pin-verify.py`, o auxiliar
`.claude/scripts/codex-auto-pin/verify-sigstore.js`, no ramo (ii) `package.json` + `package-lock.json` da mesma
pasta (no ramo (i), a lista canônica), `.claude/scripts/tests/test_codex_auto_pin_verify.py`, o arquivo único de
fixtures da camada 2 (nome a fixar), `SBOM.md` e `.claude/governance/gate-scripts-manifest.txt` — **8 paths no
ramo (ii), 7 no ramo (i)**, com o verificador, o auxiliar e o material do ramo DENTRO do manifesto ADR-192 (o
oráculo 0 não basta). **A contagem do consenso NÃO inclui `.claude/scripts/env-inventory.json`** (oráculo 0,
conferido), que a condição 13 (ajuste 17) pede no MESMO pacote para a variável de modo obrigatório da camada 2: com ele o 1a
tem 9 paths no ramo (ii) e 8 no (i). **Proposta do CEO (S361):** a exceção (5) da «Regra de WIP» — 9 paths
no 1a só no ramo (ii), ratificada junto da decisão 3; a alternativa de levar o `SBOM.md` ao 1b foi descartada
porque sai da letra do MF-R2-W3-7 (AMEND-1 §24). Recontagem na abertura. **2** — `codex_cli_shape.py` (1; argv fixo e id em `_VALID_MODELS`, DEPOIS da W3b —
Q8), `codex_invoke.py` (0), `run-promotion-gate.py` (0) e `.claude/scripts/local/pair-rail-gate.sh` (0; a
**mensagem do Gate 4 nomeando a rota 2** — sai do 1b). **Fora:** `codex-cli-pin.txt` (faixa intocada; só o plano
B a toca) e os chamadores canônicos `codex_review_user_code.py` e `council-audit.js` (declarados). **À parte:**
o pacote de kernel (`audit_emit.py`, 1; em série com a W1a do PLAN-195). Sentinela: sem corpus; o path só existe
se a decisão 4 for (i). **LEDGER (registrar ao abrir o 1a; a seção da W3 ainda NÃO existe):** `node` v26.3.0 da
W0.6 como linha de base da constante de versão mínima, resultados de S-13/S-14 e resultado e mecanismo da guarda
de rede do `node` (condições 10, 11 e 21). **Estimativa:** 1,6-2,8 M tokens em 3-4 sessões; kernel 100-200k + 1
cerimônia de kernel; a exceção (4) da «Regra de WIP» cobre só o índice dos ADR e os documentos de contagem, e
não os paths de código. **Debate:** SIM, o debate único (FECHADO); `needs_debate=true`. **Cerimônia:** sim.
**Vaga:** 3.ª das 3 iniciais (ordem decidida pelo Owner); ocupada pela W3b até a decisão 3 (Q8, S361).

- [ ] W3.1 regra operacional **até o LAND da W3** (ver W3.6), **reescrita pela decisão do Owner S362
  (2026-10-02)**: Codex no 0.156.1 até a sentada do re-pin manual (RP, plano B no fim desta seção); nela o
  Owner instala a 0.160.0 e assina o pacote, na MESMA sentada; daí até o LAND da W3 (depois da 1.4.3),
  0.160.0. Nunca `npm update -g`; nenhuma rodada de rail com outro binário; a série de rail do próprio RP
  roda no 0.156.1 e termina inteira antes da instalação da 0.160.0. Depois do LAND da W3, só pelo
  procedimento da W3.6 (instalar a versão ELEGÍVEL, nunca a `latest` crua). **Escopo do Check: SÓ o período
  até o LAND da W3** (só-manifesto, por isso sem flag): `verified` com o 0.156.1 antes do RP e com o 0.160.0
  depois do SIGN do RP; `mismatch` só na janela entre a instalação e o SIGN. Depois do LAND da W3 ele
  reprovaria um global auto-pinado, e o Check de sucesso e o da W3.6 usam `--allow-auto-pin`. — Check: python3 .claude/hooks/check_pair_rail.py --verify-codex-pin "$(command -v codex)"
- [ ] W3.2 debate único do plano — **FECHADO** (ver «Approach», item 4). O ADR-182-AMEND-1 REVISADO (rascunho em
  `.claude/plans/PLAN-194/debate/round-3/ADR-182-AMEND-1-draft.md`, a partir do de `round-2/`) vira o texto do
  pacote de ADR (1b) com os ajustes 18 a 32 do consenso r3 aplicados pelo CEO, sem nova rodada; as decisões do
  Owner 3 a 6 entram nele assim que saírem — **a 3 antes de qualquer pacote e as 4, 5 e 6 antes do 1b**
  (condições 1 e 2); os testes pré-registrados são SÓ os do ramo de empacotamento escolhido. — Check: ls .claude/plans/PLAN-194/debate/round-3/consensus.md
- [ ] W3.3 **sonda e canário, AUTOMÁTICOS e BLOQUEANTES**, na ordem verificar → sondar → aceitar (a sonda só
  executa binário já verificado): (i) sonda — `codex <sub> --help` no binário candidato para os subcomandos que o
  framework chama (`exec`, `review`, `app-server`; a remoção do `mcp-server` na 0.154.0 quebrou em silêncio —
  achado A7 do PLAN-183) e a UNIÃO das FLAGS dos chamadores (`exec`, `--sandbox`, `-o`, `--output-schema`,
  `--ignore-user-config` se adotado, `--model` e o ajuste de esforço) × {presente, ausente}; **o argv fixo é
  sondado TAMBÉM na 0.156.1 do manifesto**, que o corte usa; (ii) canário funcional — `exec` mínimo com o argv
  REAL sobre um diff SINTÉTICO fixo, devolvendo o JSON de veredito (política de nova tentativa pré-registrada,
  AMEND-1 A-20: o inconclusivo pode ser re-tentado, e uma nova tentativa antes de 10 min é recusada —
  condição 15). Argv obrigatório reprovado impede a aceitação e o hook bloqueia: nunca «aceita e cai em
  INFRA». Testes com `codex` stub num PATH temporário e espião de ZERO execução de payload não verificado.
  Check por **node id de CLASSE** (condição 14; AMEND-1 §19.4), nunca `-k`; nome da classe a fixar no 1a. —
  Check: python3 -m pytest .claude/scripts/tests/test_codex_auto_pin_verify.py::TestProbeAndCanary -q
- [ ] W3.4 controles vermelho→verde em árvore descartável. **Matriz** do AMEND-1 §9, com os LITERAIS do AMEND-1
  (condição 16): `verified_auto` nas células do registro, `mismatch`, saídas 0/1/3. Resumo: válido e versão nova
  ⇒ `verified_auto`/0 e registra; atestado ausente, de outro pacote, identidade ou assinatura inválida ⇒
  `mismatch`/1, SEMPRE (A-14 e A-15 são recusa); sem rede e versão nova ⇒ `mismatch`/1, nunca 3; sem rede e já
  registrada ⇒ `verified_auto`/0; payload ≠ sha registrado ⇒ `mismatch`/1; quarentena ⇒ `mismatch`; rollback
  para sha registrado ⇒ `verified_auto` depois de re-verificação SEM canário + Fase 2, que exige REDE (caches
  novos a cada execução; R-16) mas não cota (condição 18) — offline é só a conferência do HOOK (H-02, sem rede); CLI sem flag ⇒ só-manifesto; célula (d) da faixa: o validador
  do veredito segue INVALID para versão só auto-pinada (`release.yml:755-763`). **Fronteira do verificador
  (rodada 2), recusa 1, nunca INFRA:** `node` ausente; `sigstore` ausente, movido ou com versão ≠ a fixada;
  saída não-JSON; código ≠ 0; tempo excedido (o timeout do auxiliar, F-06, é constante canônica com teste);
  chamada SEM política (mutante: S-11 vira VERIFIED ⇒ vermelho); cache quente. **Células da rodada 3 (condição
  15):** B-01 linha de aceitação sem evento ⇒ ALARME; B-02 evento de quarentena sem linha ⇒ ALARME; B-03 evento
  sem linha ⇒ informativo; B-04 `--check-installed` com membro alterado ⇒ divergência relatada; A-26 duas
  execuções concorrentes do verificador ⇒ uma recusa, e a cadeia `seq`/`prev_sha256` íntegra; fronteiras com
  relógio INJETADO (47:59:59 ⇒ não candidata; 48:00:00 ⇒ candidata; 4.ª execução na semana ⇒ recusa). **Duas
  camadas** (AMEND-1 §19): camada 1 no CI (stub do subprocesso, FIAÇÃO fail-closed); camada 2 com criptografia
  REAL e offline (bundles reais da 0.156.1 e da 0.160.0, raiz TUF fixada, mutantes S-03..S-09, S-11, S-12 e
  S-13/S-14, estes MEDIDOS antes do SIGN do 1a — condição 10); fixture sintética só nas células de FORMA;
  **fixtures como instrumento:** sha e data de captura de cada bundle e da raiz TUF ao lado do arquivo, e um
  teste que acusa fixture trocada (condição 17). **MODO OBRIGATÓRIO (condição 13):** os testes `crypto_real`
  FALHAM em vez de pular com a variável de modo obrigatório ligada (nome proposto
  `CEO_CODEX_AUTO_PIN_CRYPTO_REQUIRED`, fixado no 1a; entra no `.claude/scripts/env-inventory.json` no mesmo
  pacote); a bateria do LAND, o Check de SUCESSO e o Check desta W3.4 a ligam (SKIP = falha); um CI sem `node` só
  roda sem o modo com o SKIP CONTADO e IMPRESSO, declarado; controle positivo: `node` fora do PATH com o modo
  ligado ⇒ vermelho. **Guarda de rede dos FILHOS (condição 11):** proxy morto e `NO_PROXY` vazio, com controle
  positivo VERMELHO (o fetch do filho falha) ANTES de qualquer resultado da camada 2 ou célula «sem rede»
  contar; se o proxy não prender o filho, TUF só de cache sobre a raiz fixada ou isolamento de rede, com o MESMO
  controle; resultado e mecanismo no LEDGER. **Teste-censo:** cada id da matriz liga a ≥ 1 teste por CONJUNTO
  EXATO, e a seleção do Check contém cada teste mapeado. Checks por **node id de CLASSE** (condição 14), nunca
  `-k`; nomes de classe propostos, fixados no 1a; a seleção inclui a classe da guarda do registro e das fontes
  (`test_codex_pin_registry_guard.py`, células W-01..W-09, pacote 1c/1b), para o censo não ficar vermelho com a
  implementação correta. — Check: CEO_CODEX_AUTO_PIN_CRYPTO_REQUIRED=1 python3 -m pytest .claude/scripts/tests/test_codex_auto_pin_verify.py::TestRefusalMatrix .claude/scripts/tests/test_codex_auto_pin_verify.py::TestFiacaoLayer1 .claude/scripts/tests/test_codex_auto_pin_verify.py::TestCryptoRealLayer2 .claude/scripts/tests/test_codex_auto_pin_verify.py::TestCensus .claude/hooks/tests/test_check_pair_rail_auto_pin.py::TestHookCells .claude/hooks/tests/test_codex_pin_registry_guard.py::TestRegistryAndSourceGuard -q
- [ ] W3.5 rail nas duas lanes nos bytes canônicos, em cada um dos pacotes (1c se houver, 1b, 1a e 2; o de
  kernel, à parte), na ordem 1c → 1b → 1a → 2 (regra de parada pré-registrada antes da 1.ª rodada: ≤ 3 rodadas; NO-GO só
  por P0 ou afirmação falsa);
  `check-ceremony-script.py` na bateria; materiais commitados como ÚLTIMO land antes da assinatura;
  SIGN/LAND. — Check: python3 .claude/scripts/check-ceremony-script.py
- [ ] W3.6 **logo depois do LAND da W3** (o corte já é independente do Codex global — pergunta 7; a sequência com
  a W7 está na condição 22). **Pré-condições** (consenso r3 §2, pelo número): (1) a **rota 2 INVERTIDA nos
  derivadores do kit da W7** (AMEND-1 §17) — pode landar como a PRIMEIRA peça da W7.1 —, com os controles
  K-01..K-06, o K-06 com o CONTROLE DE FALHA da condição 12 (a materialização segue ONLINE, com cache novo; o
  controle — cache esvaziado + modo offline + proxy morto EXPLÍCITO ⇒ falha — prova que o npm obedece às opções
  explícitas); o R-12 sai;
  (2) a CLI só-manifesto por padrão e o registro só com `--allow-auto-pin` DEPOIS do caminho do lançador
  (condição 9); o registro nunca é lido pelo validador, pelo `gen-envelope-ga.py` nem pelo kit; (3) a **guarda
  das fontes do verificador landada** (condição 6), além da guarda do registro; (4) **S-13/S-14 e a guarda de
  rede do `node` medidos e no LEDGER** (condições 10 e 11); (5) pré-voo do corte com a rede, os ~331 MB, o piso
  de `df` e a limpeza do `.npx-cache`, argv do runner alinhado à base da W3 e pré-voo da Q11 no re-pass da rc e
  do GA; (6) o pacote de kernel do evento (ou a decisão 6 escrita) e o detector de deriva lendo o registro (L1)
  landados; (7) o **runbook** com timeout EXPLÍCITO e rota de emergência (condições 18 e 20) e o **ensaio em
  modo só-verificação contra a 0.156.1 do manifesto**, sem gravar linha (condição 21). **Promoção** (AMEND-1
  §4.3 e §9.P): bytes VERIFICADOS, `--offline` sobre o cache do staging sob proxy morto EXPLÍCITO (condição 12),
  P-01 da árvore inteira, quiesce por `lsof`/`ps` (nunca `pgrep -f`), janela curta com as rodadas de rail
  paradas; **todo LAND do verificador, do auxiliar ou do lockfile é seguido de re-verificação da versão
  instalada** (condição 19). **Então** o Owner atualiza o Codex pela rota do verificador para a estável ELEGÍVEL
  (nunca a `latest` crua); 1.ª rodada real: `status == "verified_auto"` e `pin_source == "registry"`, evento na
  cadeia e `session_meta` com a versão, o originador `codex_exec` e 0 sessões «guardian» (lanes `CX-06`,
  `CX-12`). Resíduos: R-13 e R-16 (o rollback exige rede, não cota — condição 18). — Check: python3 .claude/hooks/check_pair_rail.py --verify-codex-pin "$(command -v codex)" --allow-auto-pin | python3 -c 'import json,sys;d=json.load(sys.stdin);sys.exit(0 if d.get("status")=="verified_auto" and d.get("pin_source")=="registry" else 1)'

**Declarar no material assinado** (o que o desenho não cobrir): (a) o daemon `app-server` roda fora do
pin (lane `CX-06`); (b) o `~/.codex/config.toml` global muda o comportamento do rail (esforço passou de
max para xhigh em 29/09 sem re-pin — lane `CX-07`; em 2026-10-01 o app regravou o arquivo com modelo
`gpt-6-astra`, esforço xhigh e `memories = true` — Q11) — o argv fixo fecha isto para o rail; (c)
rodadas manuais que não conferem o pin; (d) o pin automático NÃO muda os cortes de release: eles seguem
ancorados no manifesto assinado (pergunta 7; a faixa do `codex-cli-pin.txt` fica intocada) — e o limite
do `parse_semver` (casa por prefixo; quem garante «só estável» é o sha do manifesto); **(e)** o resíduo
de mesmo UID do registro (um processo do mesmo usuário lê o diretório 0700 e o arquivo 0600); **(f)** o
escopo: o pin protege a identidade e a integridade do REVISOR cujo veredito o framework registra, NÃO a
máquina; **(g)** a dependência de `node` + `sigstore` (versão e integridade; empacotamento (i) ou (ii),
decisão pendente 3), como exceção NOMEADA ao «stdlib-only» e ferramenta de mantenedor FORA do runtime
dos hooks — a «confiança no registro» NÃO é mais resíduo aceitável (virou ESCALATE); **(h)** a sentinela
não implementada, se a decisão pendente 4 for a opção (ii); **(i)** o hook `Stop` automático no opt-in
(`codex_review_user_code.py`, canônico) e o `council-audit.js`, fora do núcleo de verificação; **(j)**
adopters seguem em INFRA aberto (ADR-182: sem `.claude/governance/` neles, o pin resolve como `infra`);
**(k)** os executáveis irmãos do pacote de plataforma, fora do sha pinado (conferidos na promoção; a troca
deles em tempo de execução é resíduo de mesmo UID); **(l)** o rollback exige rede, não cota (R-16; condição
18); **(m)** cada promoção é uma janela curta de manutenção, com as rodadas de rail paradas (quiesce); **(n)**
o resíduo do I8: o hook confia em linhas que DECLARAM shas listados no manifesto ADR-192 e NÃO prova quais
bytes as escreveram — um teste o documenta (condição 7) e, se a guarda das fontes (condição 6) não couber, o
resíduo vai também a este material, nunca silencioso; **(o)** a proteção REDUZIDA do fallback (b) dos ids
imutáveis, SE ele for usado («repositório recriado com o mesmo nome passa» — condição 10); **(p)** toda
cerimônia ADR-192 do verificador, do auxiliar ou do lockfile é seguida de RE-VERIFICAÇÃO da versão instalada
(ou reinstalação da versão do manifesto): sem isso o H-07 tira a confiança da versão auto-pinada e o rail
bloqueia as escritas L3+ (condição 19); **(q)** o rollback para sha registrado ou para a versão do manifesto
PULA o canário (vivacidade, não segurança), a rota de EMERGÊNCIA é instalar a versão do MANIFESTO (H-01), e a
instalação crua deixa os irmãos sem conferência até a re-promoção ou o `--check-installed` (R-19; condição
18); **(r)** o modo de execução do runbook: terminal do Owner em primeiro plano, ou segundo plano com timeout
EXPLÍCITO ≥ o pior caso pré-registrado, nunca o padrão de 30 min do CC; morte no meio da Fase 2 ⇒ três
desfechos, conforme o `bin/codex` que sobrou (AMEND-1 §15): sha fora do manifesto ∪ registro ⇒ BLOCK (H-03);
sha igual ao registrado ⇒ o hook ACEITA, com os irmãos possivelmente incompletos (R-19); lançador ausente ou
`bin/codex` não resolvido/ilegível ⇒ `infra` (`check_pair_rail.py:654`, `:725`, `:731`; H-10) ⇒ o rail some com
aviso (R-8), não BLOCK — nos três, rota de emergência ou nova execução com `--promote`; a recusa do quiesce nomeia PID e caminho de cada
processo (condição 20).
**Controle vermelho→verde:** W3.4. **Dependências:** a decisão pendente 3 ESCRITA (retira o VETO; «confiança no
registro» ⇒ ESCALATE) e as condições 1 a 5 do consenso r3; o AMEND-1 final; W0.6 (feita); o pacote de kernel de
registro de ações (antes da W3.6); os pacotes [1c →] 1b → 1a → 2 em série, com a guarda das fontes landada
antes do 1.º LAND do 1a (condição 6); a rota 2 INVERTIDA no kit da W7, que pode ser a 1.ª peça da W7.1
(condição 22); L1 (recomendado — o detector de deriva lê o registro); 3.ª vaga inicial (ocupada pela W3b até a
decisão 3); a W3b landada antes; a poda do `CLAUDE.md` num fechamento antes do land da W3 (risco 9); árvore sem
modificação rastreada no SIGN. **Prazo:** sem data externa; não é pré-condição do corte W7 (o 0.156.1 está
dentro da faixa pinada, o manifesto atual é o do 0.156.1 e o corte independe do Codex global — rota 2,
invertida).

**Plano B — re-pin manual pelo molde (ADR-182 §5; precedentes 0155 e 0156) — ATIVADO para a 0.160.0
(decisão do Owner S362, 2026-10-02).** O gatilho previsto era o debate recusar o pin automático ou o 0.156.1
parar de funcionar antes do land. Na S362 o Owner ativou o plano B como 1.ª tarefa do trem (RP): a decisão 3
não foi tomada, a W3 fica para depois da 1.4.3 e o VETO de Segurança segue levantado. Pacote em
`.claude/plans/PLAN-194/codex-pin-0160/` (regra do `re-pin-codex.py`, `pack_tag()`: `0.Y.Z` → `0Y-Z`, e só
`0Y` se Z = 0). Passos:

1. Pré-condições do molde: árvore sem modificação rastreada (o SIGN aborta, `OWNER-PIN-SIGN.sh:330` do
   molde, lane `CX-13`); L1 landado; este plano commitado com o texto do re-pin, porque o `re-pin-codex.py`
   exige `--plan` e o ensaio recusa plano com linha de instalação global de outra versão
   (`rehearse-pin-0156.sh:236-249`, clonado no pacote); tag `v1.4.2` ancestral do HEAD.
2. Sonda da 0.160.0 num prefixo npm descartável, ANTES de executar qualquer binário dele: sha256 do payload
   e `--verify-codex-pin` = `mismatch`; depois `--version`, o argv do hook, o argv do CEO e o teste vivo do
   `execpolicy`. Resultado e sha256 no LEDGER antes do passo 3.
3. `python3 .claude/scripts/re-pin-codex.py 0.160.0 --plan PLAN-194 --mold
   .claude/plans/PLAN-193/codex-pin-0156/OWNER-PIN-SIGN.sh --ga-tag v1.4.2 --pin-note <arquivo> --dry-run`;
   depois o mesmo comando sem `--dry-run` (baixa ~331 MB: diretório próprio, piso de `df`, limpeza
   confinada). O `--pin-note` recebe o CAMINHO de um arquivo UTF-8 com a justificativa, sem marcador de pendência
   (o gerador recusa a nota que ainda o tenha).
4. Ensaio com prefixos npm descartáveis (`$REHEARSE_CODEX_PREFIX`, `$REHEARSE_OLD_CODEX_PREFIX`), placar
   todo verde.
5. Rail do pacote no 0.156.1 verificado, terminado inteiro antes da instalação da 0.160.0.
6. Sentada do Owner (sábado 2026-10-03), com as rodadas de rail paradas:
   `npm i -g @openai/codex@0.160.0`; `--verify-codex-pin` = `mismatch`; SIGN; push; `--verify-codex-pin` =
   `verified`. Se o SIGN abortar, reinstalar a 0.156.1 (o manifesto ainda é o dela) e conferir `verified`.

**Versão nova antes do SIGN:** se sair uma 0.160.x antes do SIGN, a ferramenta regenera o pacote em quatro
passos: (1) land de texto trocando a versão do passo 6, porque o detector do ensaio recusa outra versão neste
plano; (2) sonda nova, porque o sha do payload muda; (3) pasta nova pela `pack_tag()`; (4) comandos novos
para o Owner. Controle do RP: `--verify-codex-pin` = `mismatch` logo depois da instalação → `verified` depois
do SIGN.

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
- [x] W3b.3 **FECHADA em 2026-10-02 (S361): NÃO confirmada na fonte primária (`PLAN-194/LEDGER.md`,
  seção «W3b.3»); fecha sem a linha do `gpt-5.5`. O refresh dos ids desligados em 2026-07-23 e dos
  snapshots de 2026-12-11 entrou junto da W3b.0 (commit `a9924eb1`).** Texto original: a verificar em
  fonte primária (S361), ANTES da re-medição da W3b.0 e da W3b.1 (a linha
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
**3.ª vaga inicial**, enquanto a W3 espera o debate (PROCEED na r3) e a decisão pendente 3 (exceção à OQ-11 aprovada pelo
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
  Owner); no núcleo da 1.4.3 só «se o debate único fechar a tempo» (o da W5c já fechou: PROCEED na
  rodada 1), e é a primeira a sair se a cota apertar (Q7, S361); landa depois da W6.2, da W5a, da W5b e
  do código da W2 (U2-C), sem esperar o U2-D, re-derivada sobre o HEAD (decisão do Owner S362; antes,
  «por ÚLTIMO no núcleo»), e sai pela linha de corte se não estiver landada quando a derivação do kit
  começar. **LIBERADA pelo PROCEED da rodada 1 do debate (S361; `design-coherent`) — liberação por
  onda, decisão do Owner S361, Q3:** os must-fix MF-W5c-1 e MF-W5c-2 e os ajustes 35 a 40 do consenso
  valem como pré-requisitos de execução (o VETO de Segurança foi retirado com essas condições). **Registro no
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
  `model-currency-expected-reds.txt` e testes (0). **Censo da abertura (rodada 1; base trocada na S362):**
  contra o `WFABLE51.patch` (adoção do Fable 5.1; 30 paths, medidos em 2026-10-02 — inclui `upgrade.sh`,
  `validate-governance.sh`, o manifesto ADR-192 e `docs/provider-pricing.md`; NÃO inclui `install.sh`, o
  baseline do censo do instalador, `SUPPORT.md`, `audit_log.py`, `settings.user.json` nem
  `_lib/test_isolation.py`), e não mais contra o `WOPUS55.patch` (76 paths), com as linhas no mapa de colisões;
  `check-installer-write-safety.py` na bateria; custo do censo: +100-200k tokens. — Check: python3 .claude/scripts/generate-available-models.py --check && python3 .claude/scripts/check-model-currency.py --expected-reds .claude/data/model-currency-expected-reds.txt
- [ ] W5c.1 **re-teste pago, só na vez da W5c** («Só quando chegar a vez (Recomendado)»), com os
  MESMOS testes das adoções anteriores e o instrumento intacto (regra «modelo novo ⇒ re-testar»,
  CLAUDE.md §4); o conjunto exato de testes é fixado no LEDGER ANTES de rodar (pré-registro), junto do
  resultado da W5.0 sobre o alias `sonnet`. **Pré-registro da rodada 1:** instrumento com sha (copiar o
  da S357 para dentro da pasta do plano, ou pinar o sha); braços `claude-sonnet-5` EXATO ×
  `claude-sonnet-5-5`, mesmo esforço, `claude -p` hermético; n, métrica (defeitos achados, correção
  cega), δ de não-inferioridade e regra de custo fixados antes; **a validade vem antes das células** —
  execução com id SERVIDO ≠ pedido, ou com sha do instrumento ou versão do CC diferentes, é INVÁLIDA (não
  FAIL), refaz e não conta; efeito teto declarado (na S357 o instrumento achou 19 de 20 defeitos:
  detecta regressão, não melhora). Células (2^3, enumeradas ANTES; valores propostos, o CEO ajusta no
  LEDGER sem remover célula): defeitos {não-inferior, inferior por δ} × custo por revisão {≤ 1,2×, >
  1,2× o Sonnet 5} × os dois HTTP 400 da `ANT-02` {confirmados, não confirmados}. Ação por célula:
  não-inferior e custo ≤ 1,2× ⇒ PASS (com os 400 confirmados o adapter ganha a proteção; não confirmados,
  o adapter segue sem mudança e a `ANT-02` é registrada como refutada); não-inferior e custo > 1,2× ⇒
  PASS com o custo declarado no material assinado; inferior ⇒ FAIL — pára antes do SIGN e o Owner decide
  por múltipla escolha (o debate NÃO desfaz o «Adotar»). **Sondas do adapter (W5c-3):** duas sondas
  pagas pré-registradas, na W5.0 ou aqui — `thinking` `disabled`, e `tool_choice` forçado com `thinking`
  ligado. Regras de medição da W0. — Check: none (medição paga; resultado no LEDGER)
- [ ] W5c.2 debate L3 dentro do debate único do plano — **FEITO: rodada 1, PROCEED (`design-coherent`,
  S361)**; críticos: Segurança, QA e DevOps. Respostas (consenso §6, W5c-1 a W5c-6): (a) **formato da
  Amendment 2, só ele** — o 5.5 entra só no conjunto de trabalho, com piso VETO, fallback e pin
  inalterados e `_ROUTING_TABLE` intocado; a emenda 4 diz que `claude-sonnet-5-5` fica fora do piso VETO,
  do pin de sessão e de `.claude/agents/*.md` (A1.1 reafirmada), com controle de igualdade de bytes do
  conjunto elegível a VETO antes e depois do pacote derivado (MF-W5c-1); (b) **decidido pelo CEO, com
  critério pré-registrado:** os exemplos da skill `llm-routing-and-finops` seguem com o alias `sonnet`
  (fixar o id recria churn a cada geração); a tabela de roteamento (`SKILL.md:109-123`, que cita
  `claude-sonnet-4-6`) é corrigida no pacote — se a W5.0 medir alias → `claude-sonnet-5-5` em 3 de 3
  sondas (id servido conferido, CC congelado), a tabela cita «alias `sonnet` = `claude-sonnet-5-5` no CC
  ≥ 2.1.284, medido em <data>»; senão, cita só o alias e declara; (c) **medir primeiro** (as duas
  sondas pagas da W5c.1): o teste do adapter codifica a resposta MEDIDA, com data e substrato, e a
  proteção vale para a CLASSE `_ALWAYS_ON_THINKING_MODELS` (`.claude/hooks/_lib/adapters/live/claude.py:135-142`,
  `claude-opus-5-5` incluído), parametrizada; (d) **nenhum fato antecipa a W5c:** ela landa por ÚLTIMO
  no núcleo, re-derivada sobre o HEAD; se não estiver landada quando começar a derivação do kit da W7,
  vai para depois do GA (linha de corte). A W5c ficou FORA do escopo da rodada 2 (inalterada: PROCEED da
  rodada 1) e a rodada 3 julga só a W3. — Check: ls .claude/plans/PLAN-194/debate/round-1/consensus.md
- [ ] W5c.3 pacote derivado por script: emenda 4 do ADR-149 (**formato da Amendment 2**, texto conforme
  a W5c.2 (a): fora do piso VETO, do pin de sessão e de `.claude/agents/*.md`, com o controle de igualdade
  de bytes do conjunto elegível a VETO antes e depois; com a correção de texto do Ultracode da W5a
  dentro — mapa de colisões); linha `claude-sonnet-5-5` no `cost-table.yaml`
  com US$ 2 de entrada e US$ 10 de saída por milhão de tokens e leitura de cache a US$ 0,20 (fonte:
  CHANGELOG do Claude Code 2.1.284; conferir na página de preços no dia do pacote, como fazem os
  `source_url` das linhas vizinhas). A tabela não tem coluna de cache: o multiplicador vai nos scripts de
  custo, como na linha do Opus 5.5 (comentário em `cost-table.yaml:99`). `availableModels` regenerado
  pelo `generate-available-models.py`. **Entrega ao adopter (rodada 1, W5c-6):** as duas cláusulas da
  A2.2 (itens 5 e 6) repetidas; o array de 8 ids da 1.4.2 (o `new` atual do `upgrade.sh`, `:198`) vai
  para `superseded`, e o `new` acrescenta o 5.5 no FIM (9 ids), com casamento byte a byte; o `upgrade.sh`
  nunca alarga nem estreita em silêncio uma allowlist customizada. Quatro células: o array exato de 8
  ids ⇒ MIGRATE; o customizado ⇒ PRESERVED com WARN nomeado; o de 7 ids ⇒ MIGRATE; a 2.ª execução ⇒
  nada muda. `derive-settings-baselines.py --check` na bateria, num clone com TODAS as tags GA, e SKIP
  conta como falha (a guarda da migração do adopter PULA em clone raso —
  `test_derive_settings_baselines.py:664` e `:672`, `skipTest` — e o `validate.yml` não tem
  `fetch-depth` nem chama o `derive-settings-baselines`). **`_tier_rank`** (`tier_policy_cli/learn.py:535-563`):
  hoje `claude-sonnet-5` = 3 e `claude-opus-4-8` = 4, então `claude-sonnet-5-5` rank -1 (desconhecido) e
  não há inteiro livre entre 3 e 4 — renumerar, com as direções `sonnet-5→sonnet-5-5` = promote,
  `sonnet-5-5→opus-4-8` = promote e `sonnet-5-5→sonnet-4-6` = demote, e uma guarda de classe: todo id do
  bloco `AVAILABLE_MODELS_WORKING_SET` do ADR-149 tem posto ≥ 0. — Check: python3 .claude/scripts/generate-available-models.py --check && python3 -m pytest .claude/hooks/tests/test_adr149_validator_parity.py .claude/scripts/tests/test_check_model_currency.py -q
- [ ] W5c.4 controle vermelho→verde em árvore descartável: só a linha de preço, sem a emenda ⇒ o
  `check-model-currency.py` acusa o id sem autoridade A1 (vermelho — alternativa (c) do «Approach»); o
  braço vermelho afirma a DIFERENÇA EXATA (`+claude-sonnet-5-5` na superfície S1), não só «há achado»;
  com a emenda 4 ⇒ o conjunto de vermelhos esperado fica igual (verde). — Check: python3 .claude/scripts/check-model-currency.py --expected-reds .claude/data/model-currency-expected-reds.txt
- [ ] W5c.5 rail nas duas lanes nos bytes canônicos (regra de parada pré-registrada antes da 1.ª
  rodada: ≤ 3 rodadas; NO-GO só por P0 ou afirmação falsa); exceção de tamanho declarada no material
  assinado; `check-ceremony-script.py` na bateria; censo da abertura contra o `WOPUS55.patch` e
  `check-installer-write-safety.py` na bateria (ver o item da W5c); no `.claude/settings.json`, só depois
  do land da W6 ou no mesmo pacote dela (mapa de colisões, OQ-14); SIGN/LAND. — Check: python3 .claude/scripts/check-ceremony-script.py
- [ ] **W5.1 — refresh do ledger de substrato, UMA vez, depois do LAND do re-pin manual (RP; decisão do
  Owner S362 — antes era «depois do land da W3», que foi para a 1.4.4)**: o `codex_cli` do refresh é a
  0.160.0 pinada pelo RP; a W3 faz o próprio refresh se mudar a versão global (codex_cli,
  claude_code, cc_native_usage e, desde a S361, grok_cli — o ledger tem 0.2.93 de 2026-07-12), com a réplica do loader re-derivada no MESMO patch
  (`test_settings_guard_loadability.py:138` fixa `2.1.280`; o teste de `:522` fica vermelho quando o
  ledger sobe, por desenho). O Owner roda `check-substrate-watch.py --refresh`. **Valores a gravar no
  refresh (S361):** `claude_code` = a versão instalada na hora (2.1.287 em 2026-10-01 — as medições da
  S360 são do 2.1.286, e o ledger tem hoje 2.1.280, de 2026-09-22); `codex_cli` 0.160.0 (a versão
  pinada pelo RP; o global era o 0.156.1 em 2026-10-02); `grok_cli` 1.0.13 (instalado, `grok --version` em 2026-10-01). **Vigia do Haiku 4.5, com
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
com debate e rail + 100-200k do censo contra o precedente + a cota paga do re-teste. **Debate:** só a
W5c (no debate único do plano; rodada 1 FEITA: PROCEED).
**Dependências:** W5.0 (paga, na vez da W5); PROCEED do debate único (**dado na rodada 1** — a W5c está
LIBERADA, com os must-fix e os ajustes 35 a 40 do consenso como pré-requisitos — Q3, S361); W5c.1 (paga,
na vez da W5c); W6 antes da W5c no `.claude/settings.json`, ou no mesmo pacote pela OQ-14; o LAND do
re-pin manual (RP) para a W5.1 (S362); a W5c landa depois da W6.2, da W5a, da W5b e do código da W2
(U2-C), sem esperar o U2-D (decisão do Owner S362), e sai pela linha de corte se não estiver landada
quando a derivação do kit começar.
**Prazo:** antes do corte W7; se a W5c não chegar a tempo, o corte declara no material assinado que o
prefixo `claude-sonnet-5` admite o 5.5 sem a emenda.

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
como no PLAN-192/193 — o derivador do GA 1.4.2 tem 8.984 linhas); 1-2 M tokens (os 100-150k da rota 2
invertida saíram com a decisão S362 D-4: a rota 2 vira recusa nomeada). **Debate:** não para o
kit (molde); rail com regra de parada pré-registrada (≤ 3 rodadas; NO-GO só por P0 ou afirmação falsa).

- [ ] W7.1 curar no derivador os P2 abertos herdados do PLAN-193 (lista abaixo) e INVERTER a rota 2 do
  runner do re-pass (rodada 2; «Pré-condições do corte» — o `test-rc1-kit.sh` carrega os dois controles:
  lançador plantado nunca executa; espião de zero execução antes do oráculo). — Check: bash .claude/plans/PLAN-194/test-rc1-kit.sh
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
`gen-envelope-ga.py` do kit recusa sha ou versão diferentes) — cumprido com o manifesto atual (o do
0.156.1); a W3 NÃO muda isso (pergunta 7 da W3: o pin automático não muda os cortes). **Rodada 1 do
debate:** o **Codex global pode diferir do manifesto**, porque o runner do re-pass resolve o Codex do
MANIFESTO pela rota 2 (`npx` em cache próprio) e o envelope lê a PROVENANCE, nunca a máquina; por isso a
W3.6 roda logo depois do LAND da W3, sem esperar o corte. **Rodada 2:** a rota 2 dos runners atuais
EXECUTA antes de verificar e o shim executa o LANÇADOR, então ela é **INVERTIDA nos dois derivadores do
kit** (custo: +100 a 150k tokens). Pré-condições dessa independência: (i) os derivadores do kit
(`derive-kit-143.py` e `derive-ga-kit-143.py`) invertem a rota 2 COM controle — materializar SEM executar
(`npm install --prefix <OUT>`, `--ignore-scripts`, ambiente do npm montado do zero, registro fixo, cache
novo, versão EXATA do manifesto) → oráculo sem flag → shim com `exec` do `path` VERIFICADO → só então o
`--version`; um lançador plantado num registro redirecionado NUNCA executa, e um espião prova ZERO
execução antes do oráculo; kit com Codex global ≠ manifesto ⇒ a PROVENANCE registra a versão do manifesto
e a rota 2; o R-12 sai dos resíduos; **o K-06 repete o CONTROLE DE FALHA da
condição 12** (a mesma invocação do npm do kit, com o cache ESVAZIADO, em modo offline e com proxy morto
EXPLÍCITO, tem de FALHAR; a materialização em si segue ONLINE, com cache novo — a aquisição inicial não é
offline); (ii) o pré-voo declara a rede, os ~331 MB e o piso de `df`; (iii) o
argv do runner fica alinhado à base da W3 (ou a divergência é declarada no material assinado) e o argv
fixo é sondado também na 0.156.1 do manifesto; (iv) o pré-voo da Q11 vale no re-pass da rc e do GA; (v)
linha de corte da W5c: se ela não estiver landada quando começar a derivação do kit, vai para depois do
GA; (vi) nenhum pacote de ADR em voo durante o kit (primeiro pronto, primeiro a landar; um por
fechamento; nenhum pacote de ADR em voo entre o início da derivação do kit e a publicação do GA) — por isso o **1b (pacote
de ADR da W3) landa ANTES de começar a derivação do kit**, senão a W3.6 escorrega para depois do GA (condição
22); a inversão da rota 2 pode landar como a PRIMEIRA peça da W7.1 (derivadores com oráculo 0, K-01 e K-02),
para a W3.6 não esperar o kit inteiro. W1
obrigatória se o corte for depois de 2026-10-19; W2 recomendada. **Escopo do corte (Q7, S361):** o núcleo descrito no Goal;
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

**Emenda S362 (2026-10-02):** a W3 e o pacote de kernel dela saíram da 1.4.3 (vão para a 1.4.4, sem
custo neste trem); o re-pin manual (RP) entrou; a W2 virou 4 pacotes. Total estimado do trem até o GA:
~5,7 a 11,1 M de tokens de contexto do CEO (subagentes à parte) em ~8 a 12 sessões, várias em paralelo,
com pelo menos 3 sessões por causa de dois fechamentos obrigatórios (W2.6 e U2-D).

| onda | tokens (estimado) | sessões | vaga canônica | quem espera |
|---|---|---|---|---|
| re-pin manual do Codex 0.160.0 (RP; S362) | 300-600k (sonda, texto, pacote gerado, ensaio, rail no 0.156.1) | 1 | sim (vaga 1; exceção (3) da regra de WIP; o pin é KERNEL e o molde 0156 já lidou com isso) | assinatura do Owner (sábado 2026-10-03) |
| W0 | 150-300k (sem cota paga) | 1 | não | — |
| W1 | 150-300k | 1 | sim (1.ª) | assinatura; prazo 19/10 |
| W2 | 1,8-3,2 M (S362: U2-A a U2-D, verificadores do spool e H1, estresse, W0.5, script da W2.6 e AMEND-4 condensado; era 1,0-1,8 M) | 3-4 | sim (vaga 2, em série: U2-A → U2-B → U2-C → U2-D) | debate único (PROCEED na rodada 2; MF-R2-W2-1..4 valem) + 4 assinaturas; a W2.6 roda depois do LAND do U2-B, com as sessões deste projeto fechadas (decisão 2 aceita), e é RECORRENTE sob T1 |
| cura do `agent_spawn` (W2.0; condição 67) | FEITA (landada em `65cd50d7`) | — | — | — |
| W3 — **fora da 1.4.3 (S362; vai para a 1.4.4)** | 1,6-2,8 M, em pacotes [1c →] 1b → 1a → 2 de ≤ 8 paths em série (a W0.6 já feita, sem cota paga) + a rodada 3 do debate (150-300k, feita); as condições 1-23 cabem nesta faixa (estimativa dos críticos: 50k a 220k; a cerimônia de kernel da condição 6, se por `_CANONICAL_GUARDS`, é custo marginal sobre o 1b ou o 1c) | 3-4 (inclui o pacote de kernel) | sim (3.ª vaga inicial — ordem decidida; ocupada pela W3b até a decisão 3, Q8) | decisão pendente 3 ESCRITA (retira o VETO; «confiança no registro» ⇒ ESCALATE; debate FECHADO, PROCEED na rodada 3) + assinatura; Codex parado na versão pinada (0.160.0 depois do RP) até o LAND da W3 (depois, só pela W3.6, que roda logo depois do LAND) |
| W3: pacote de kernel de registro de ações (`audit_emit.py`) — **fora da 1.4.3 (S362)** | 100-200k + 1 cerimônia de kernel | com a W3 | sim, em série com a W1a do PLAN-195 | assinatura; landa ANTES da W3.6 |
| W3b | 100-200k | 1 | sim (3.ª vaga inicial enquanto a W3 espera — Q8, S361; landa antes da W3) | assinatura; prazo 2026-12-11 |
| W4 | 150-300k | 1 | sim | assinatura; antes da rc.1 |
| W5a/W5b | 300-600k + cota paga da W5.0 | 1 | sim (install.sh; o texto do ADR-149 vai na W5c) | W5.0 na vez da W5 (OQ-7 respondida, Q9: gravar `manual`) |
| W5c (adoção do Sonnet 5.5) | 2-4 M + 100-200k do censo contra o precedente + cota paga do re-teste | 1-2 | sim (depois da W2, salvo se o debate pedir antes; exceção de tamanho declarada) | debate único (PROCEED dado na rodada 1 — onda LIBERADA, Q3; must-fix valem) + re-teste pago na vez + W6 landada antes, ou no mesmo pacote pela OQ-14 (`settings.json`) + assinatura |
| W6 | 100-200k + isca paga mínima da W6.0 | 1 | sim (antes da W5c e da W3 do PLAN-195 no `settings.json`) | agendamento do backup pelo Owner (W6.1; a 1.ª cópia já foi feita na S361) + ensaio de restaurar e verificar (W6.3) + isca W6.0 antes da W6.2; OQ-8 e OQ-14 respondidas (Q9) — a W6 não espera o sandbox nem a W5c |
| W7 | 1-2 M (S362: a rota 2 vira recusa nomeada — os 100-150k da inversão saíram) | 1-2 | sim (cortes) | hold de 24 h + assinaturas + npm |
| W8 | 50-150k | com outra | sim | OK do download |
| L1-L4 | 300-600k | espalhadas | não | — |
| L5 (medição do ADR-191) | 50-150k (estimado; só leitura do log, mais a amostra de verdadeiros e falsos positivos) | com outra | não | — |

## Riscos

1. **Prazo de 19/10 perdido** ⇒ Validate vermelho em todo push e toda noite. Mitigação: W1 na 1.ª vaga;
   OQ-2 (fixar a imagem do runner `Ceo`; RESPONDIDA na S361 — o Owner fixa a imagem 2295, Ubuntu 24.04)
   como rede sem código.
2. **O censo W0.1 acha muitos workflows quebrando** ⇒ passa de 8 paths. Mitigação: dividir por
   criticidade (gates do release primeiro); a mitigação oficial `ubuntu-24.04` é por arquivo.
3. **W2 mexe no núcleo da cadeia de auditoria** ⇒ risco de perder evento. Mitigação: debate (rodada 2),
   invariantes em teste de estresse (por conjunto, escritores mistos, mutantes plantados),
   `verify_chain()`, rail, predicado conservador de GC, nenhum `unlink` de `*.lock` em hook, prazo na
   saída com controle de entrega de decisão e a cura do `agent_spawn` antes do SIGN.
4. **Pin automático aceita uma versão ruim com procedência válida** (o atestado prova a ORIGEM, não a
   QUALIDADE do revisor). **Mitigações reescritas na rodada 1:** o verificador roda FORA do hook (a
   verificação dentro do hook PreToolUse viraria fail-OPEN por timeout); sonda e canário funcional
   BLOQUEANTES, na ordem verificar → sondar → aceitar (cobrem a classe A7: subcomando ou flag removidos em
   silêncio); carência de 48 h contada no relógio do registro, com a estável elegível mais nova (nunca
   «== `latest`») e gramática estrita de versão; identidade do construtor fixada em constantes
   canônicas; quarentena e rollback nomeados e testados; evento durável na cadeia HMAC a cada aceitação
   (pacote de kernel de registro de ações); versão, modelo e esforço registrados em cada veredito. A
   **sentinela de corpus fixo** (avisa, não trava) está **pendente de decisão do Owner (S361; decisão
   pendente 4)**: o corpus travado do ADR-111 não está no repositório, e a recomendação é a W3 landar sem
   sentinela, declarada — o gatilho do ADR-111 §2 fica preservado e NÃO AVALIÁVEL até haver corpus com sha
   e linha de base. **Até o LAND da W3:** um `npm update -g` fecha o rail (o MANIFESTO por sha exato
   recusa o binário novo — não a faixa: o hook bloqueia as escritas L3+ e o pré-voo de fase 6 aborta; as
   rodadas manuais não conferem o pin e rodariam o binário novo sem verificação); mitigação: a regra da
   W3.1 (0.156.1 até a sentada do re-pin manual, 0.160.0 depois dela; decisão do Owner S362). **E no corte** (S361, respondido na rodada 1): o pin automático não
   muda o passo 15 do release (um veredito com o Codex novo e fora do manifesto sai INVALID), mas o corte
   é independente do Codex global — o runner do re-pass resolve o Codex do MANIFESTO pela rota 2 (`npx`
   em cache próprio) e o envelope lê a PROVENANCE —, então a W3.6 roda logo depois do LAND da W3 e o corte
   segue pela rota 2 (resíduo: depende da rede e de o 0.156.1 seguir baixável no registro). **Rodada 2:**
   **a rota 2 dos runners atuais EXECUTA antes de verificar** (o `npx ... --version` roda antes do oráculo,
   e o shim executa o lançador, não o payload verificado) **até a inversão no kit da 1.4.3** (pré-condição
   da W3.6); **os executáveis irmãos do pacote de plataforma ficam FORA do pin** (sha só do `bin/codex`:
   conferidos na promoção, e a troca em tempo de execução é resíduo de mesmo UID); a «confiança no
   registro» deixou de ser resíduo aceitável (ESCALATE); e o rollback exige rede (R-16). No re-pin manual
   (plano B, ativado na S362) volta a janela entre `npm i -g` e o SIGN: mesma sentada + rodadas manuais
   congeladas.
   **Rodada 3:** o **I8 do rascunho sobre-afirmava** — o hook confia em linhas que DECLARAM shas listados no
   manifesto ADR-192, e o escritor do registro é editável pelo agente (oráculo 0 nas fontes; nenhum hook lê o
   ADR-192 — `grep gate-scripts-manifest .claude/hooks/` não acha nada, conferido na S361), então a guarda das
   fontes (condição 6) e o texto corrigido (condição 7) fecham a via e o resíduo é nomeado; e há **dependência
   do instrumento**: o H-07 revoga a confiança a cada cerimônia do verificador, então toda cerimônia exige
   re-verificação logo depois (condição 19). A dependência de COTA no rollback está resolvida: ele pula o canário
   e tem rota de emergência (condição 18).
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
   espera o debate e a decisão pendente 3 (Q8, S361).
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
    e conferida pela recomputação contra os elos anteriores.** **Números relidos no consenso da rodada 1
    (2026-10-02T00:25Z):** `audit-log.errors` com 30.258 linhas, 30.068 delas `drain canonical lock
    timeout` (eram 25.589 às ~20:08Z, cerca de 1.100 por hora); o state dir tinha 226.831 e 226.811
    entradas às 23:55Z e às 00:00Z (contagem dos críticos); relido pelo redator às 00:39Z: 30.823 linhas,
    30.631 timeouts e ~227,9 mil entradas — o acúmulo segue. **O gatilho de reversão do ADR-055-AMEND-3
    (`revert_trigger_truly_lost_7d`) está MORTO:** `truly_lost` nunca é incrementado (só
    `spool_writer.py:136`, o valor padrão, e `:2562`, a leitura) e a reconciliação do journal
    (`spool_writer.py:2467`) não tem chamador em produção; o AMEND-4 não herda o `truly_lost` e põe os
    gatilhos em instrumentos LIGADOS, com controle positivo. **A cura da condição 67 é a W2.0,
    pré-condição do SIGN da W2** (vaga: decisão pendente 1). Mitigação: re-medir no início de cada onda.
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
17. **Trabalho longo dentro de guard vira allow por timeout** (acrescentado na rodada 1 do debate). Uma
    ação passa sem decisão quando o hook estoura o timeout; é a classe comum à W2 (a listagem de ~228 mil
    nomes sob o lock canônico na saída do hook, contra o timeout de 5 s dos guards PreToolUse) e à W3 (o
    download de ~331 MB dentro do hook do rail, contra o timeout de registro de 210 s). Mitigação: na W2,
    o prazo na drenagem forçada de saída com controle de ENTREGA DE DECISÃO (W2.2-bis) e nenhuma varredura
    própria no hook; na W3, o verificador em processo próprio, fora de qualquer guard — o hook só faz hash
    e consulta local, nunca usa rede, e sha desconhecido ⇒ bloqueio.
18. **A decisão do hook sai só depois do `atexit`** (acrescentado na rodada 2; MEDIDO). Com stdout em pipe,
    a decisão de um hook que não chama `flush` só chega ao leitor DEPOIS da drenagem de saída (medido pelo
    sintetizador da rodada 2, CPython 3.9.6 do sistema: o 1.º byte só chegou em 1,52 s com um `atexit` de
    1,5 s). Qualquer trabalho no `atexit` atrasa a decisão que o harness espera, e um hook que estoura o
    timeout é morto com a decisão descartada. Mitigação: `flush` de stdout e stderr ANTES da drenagem
    (barato; não substitui o prazo), prazo na saída com âncora `min(import, início do processo)`
    (W2.2-bis), calibração com o harness REAL na W0.5 (2 chamadas `claude -p`, CC congelado) e, sem a
    calibração, o controle S1 declarado no material assinado como prova contra um MODELO do harness.

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
  ledger (lane `F13`); `council-audit.js` e `codex_review_user_code.py` passando pela conferência do pin
  (lane `CX-04`; o `codex_invoke.py` e o `run-promotion-gate.py` entraram na W3, pacote 2 — pergunta 6,
  rodada 1); [fixar modelo e esforço no argv do rail
  (lane `CX-07`) saiu daqui: entrou na W3, desenho do pin automático]; refresh do `model-deprecations.json`
  (parado desde 2026-06-12, lane `ANT-05`; a linha do `gpt-5.5` virou a W3b.3 — S361); vigia do Haiku
  4.5 (piso 2026-10-15; `model_routing.py:64-70`, lane `ANT-04` — passou para a W5.1 na S361); pins node20 e `ubuntu-22.04` (`tier-policy.yml`, `mutation-gate.yml`,
  `benchmarks.yml.template` — lanes `DEP-04..06`); rotação do `audit-log.errors` (lane `H-03`); vazamento
  de temporários dos testes do framework (lane `H-06`); `shadow-ci.yml` que nunca rodou (lane `H-12`);
  pilha OTEL inerte (lane `CC-03`); métrica da ordem de −1/3 (custo por tarefa com cache separado —
  agora com dono: este plano, decisão Q13-h da S361, abaixo).
- **Adiados pela rodada 1 do debate (follow-ups, fora da 1.4.3):** (1) o kit re-pinar o manifesto por
  script nos cortes futuros; (2) lista de revogação assinada de versões do Codex; (3) cópia endereçada
  por conteúdo do último payload verificado (pede ADR próprio); (4) pin automático para adopters; ligar
  a reconciliação de início de sessão (`reconcile_journal_at_session_start`, hoje sem chamador em
  produção: abriria ~76 mil journals sob o timeout de 5 s do `SessionStart`); a opção T2 das travas da W2
  (re-checagem de inode no `filelock.py`, kernel), se não for escolhida; a sentinela de qualidade da W3,
  se a decisão pendente 4 for a opção (ii).

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
   arquivo (39.912 bytes, 87 de folga útil; risco 9). **Dono: o CEO**, no fechamento que antecede o land da W3. **Rodada 2:** o §3 do `CLAUDE.md` («Runtime … stdlib-only») só muda no
   fechamento, junto do `SBOM.md` da W3 (que escopa o «stdlib-only» ao runtime dos hooks e declara `node` +
   `sigstore` como ferramenta de mantenedor), DENTRO da folga de 87 bytes (risco 9) — por isso a poda vem
   antes.
4. **Cura da corrida no gravador do `agent_spawn`** (`.claude/hooks/audit_log.py`, oráculo = 1): ler o elo
   anterior e calcular o HMAC DENTRO da trava, com teste de N gravadores em paralelo e controle vermelho no
   código atual (diagnóstico no risco 11). **Dono: este plano**; pacote canônico com cerimônia, vaga e
   orçamento decididos pelo Owner. **Rodada 1 do debate:** ela é PRÉ-CONDIÇÃO do SIGN da W2 (item W2.0).
   **Recomendação do CEO, pendente de decisão do Owner (S361; decisão pendente 1):** pacote canônico
   PRÓPRIO, landado ANTES do SIGN da W2 — o primeiro pacote na vaga da W2, ou a primeira vaga que abrir
   antes (alternativa: dentro da W2, com +2 paths); 150-300k tokens + ~50k do censo AST, 0 a 1 sessão,
   com rail. A linha que aposenta a condição 67 vai no `CHANGELOG.md` do corte W7.
5. **Lacuna de guarda da família do log de auditoria** (log, chave, sal e sidecars; achado do debate, rodada 3 —
   condição 5; domínio do VETO, ADR-052). **Dono: o CEO**, com posição ANTES do SIGN do 1b: responder NO DISCO
   se existe guarda contra escrita do agente na família do log e com que controle, e registrar no LEDGER; se não
   existir, vira item ou pacote próprio no plano, com hospedeiro e posição na fila. **Resposta provisória
   (`grep`, 2026-10-02, negativa):** `check_bash_safety.py` só cita o state dir num docstring (`:1501`); o
   `check_canonical_edit.py` não tem padrão para a família; `permissions.deny` (`.claude/settings.json:820`) não
   tem entrada do log — a confirmar por escrita real na abertura do 1b. **Não bloqueia a W3; bloqueia ficar sem
   dono.**

## Decisões do Owner — S362 (2026-10-02)

Decisões do Owner no fechamento da S361 e na abertura do trem da 1.4.3, registradas em 2026-10-02. São
decisões TOMADAS: não se perguntam de novo. Siglas novas: **RP** = re-pin manual do Codex (pacote
`codex-pin-0160`); **U2-A a U2-D** = os 4 pacotes canônicos da W2 (seção W2); **FX** = cura de classe do
teste instável `TestParallelWritersChain`; **RM** = pacote de metadados do release da 1.4.3 (`release.sh` e
o manifesto ADR-192); **kit** = a derivação final dos materiais do corte.

| # | decisão |
|---|---|
| D-1 | Codex: re-pin MANUAL 0.156.1 → 0.160.0, como 1.ª tarefa do trem. A 0.160.0 é a `latest` do npm desde 2026-10-01T20:26Z; a 0.162 é só alpha; nenhuma 0.160.x saiu depois (medido em 2026-10-02). O Owner assina no sábado 2026-10-03. Molde: `.claude/plans/PLAN-193/codex-pin-0156/OWNER-PIN-SIGN.sh` com `--ga-tag v1.4.2`. |
| D-2 | A decisão 3 (empacotamento do verificador de assinatura) NÃO foi tomada. A W3 (pin automático) fica fora da 1.4.3, e o VETO de Segurança segue levantado. |
| D-3 | Se sair uma 0.160.x antes do SIGN do RP, a ferramenta regenera o pacote em 4 passos: land de texto com a versão nova neste plano (o detector do ensaio recusa outra versão); sonda nova (o sha do payload muda); pasta nova pela `pack_tag()`; comandos novos para o Owner. |
| D-4 | O kit da 1.4.3 corre só pela rota 1 do runner do re-pass; a rota 2 vira recusa nomeada (cura pela remoção; economia estimada de 100 a 150k tokens). |
| D-5 | A limpeza W2.6 roda DEPOIS do LAND do U2-B: é o U2-B que impede o journal vazio de voltar, e as travas crescem sempre (T1). |
| D-6 | O `ADR-055-AMEND-4` sai condensado: parte normativa com até ~250 linhas, citando por sha256 o rascunho de 1.038 linhas. |
| D-7 | Um pacote está «em voo» da abertura da sombra canônica até o land. Não contam: derivadores em `.claude/plans/` (oráculo 0), testes livres e pré-revisão só com Claude. |
| D-8 | A W5c landa depois da W6.2, da W5a, da W5b e do código da W2 (U2-C). Não espera o U2-D. |
| D-9 | Re-teste PAGO da W5c.1 autorizado (~US$ 15–30, estimado), com o instrumento v2 pré-registrado. |
| D-10 | O adapter da lane `ANT-02` fica fora da 1.4.3, com o resíduo declarado. |
| D-11 | W5a, W5b e W5.1 entram no núcleo. Ficam fora: a cura do log vivo criado com modo 0644 e a condição C32 do PLAN-183 (envio sem redação no modo AUTO do `codex_review_user_code`), que entra antes do SIGN da W9b de lá, na 1.4.4. |
| D-12 | npm EXATO 11.20.0 na W4 (o provado no GA 1.4.2). npm 12 só com decisão escrita. |
| D-13 | A chave HMAC (`audit-key`) e o `.salt` ganham uma cópia num cofre cifrado do Owner, nunca no destino do backup. |
| D-14 | Linha de corte: o que não estiver landado quando a derivação do kit começar (no máximo domingo 2026-10-11) sai do GA, com resíduo declarado. Candidata natural: a W5c, junto com o texto A3.1 do ADR-149. Se o código da W2 (U2-A a U2-C) estiver entre os atrasados, o CEO PARA e leva ao Owner: é a cura de segurança. |
| D-15 | Assinaturas de manhã e à noite, inclusive no fim de semana. |
| D-16 | O Owner aplica, com os comandos que o CEO entrega: `DISABLE_AUTOUPDATER=1` no settings do usuário; `memories` e `chronicle` desligados no config do Codex; o agendamento do backup; o fechamento do app Codex no re-pin. O CEO não altera configuração do Owner. |
| D-17 | O PLAN-195 inteiro vai para a 1.4.4. Pode ser construído sem pressa, fora do caminho crítico, e nada canônico dele landa antes do GA. A dúvida kernel + `SPEC/v1` da W1a de lá fica para a 1.4.4. As perguntas Q-7(a) e Q-7(b) de lá estão decididas para a 1.4.4: (a) a W1a é construída numa vaga própria durante o rail da W1-ADR; (b) a P-5 é ratificada dentro do SIGN do ADR-201, com os números no sentinel. A Q-7(c) era redundante (a P-3 já estava decidida). |
| D-18 | PLAN-183: a W7b vai para a 1.4.4; a W7a fica na 1.4.3. |
| D-19 | Lands da W2 (U2-A, U2-B e U2-C): a convivência de versões é DECLARADA no material assinado, e o land acontece com a sessão aberta. A W2.6 continua exigindo as sessões DESTE projeto fechadas há ≥ 10 min. |
| D-20 | Sonda do Codex: o Owner autorizou copiar a credencial do Codex (`auth.json`) para um `CODEX_HOME` temporário só da sonda, apagado no fim por limpeza confinada. Risco aceito: talvez precise de `codex login` depois. |
| D-21 | Ritmo: até 4 canônicos em voo; até 8 agentes vivos, com 1 vaga sempre reservada para refutador; 12 agentes só depois da W2.6. |
| D-22 | Já feito: os `approved.md` dos debates do PLAN-194 e do PLAN-183 (`5c52998b`) e o registro destas decisões na memória do CEO. |
| D-23 | Do debate: PLAN-194 — decisões 2, 4, 5 e 6 aceitas e debate ratificado (`debate/round-3/approved.md`); PLAN-183 — P4 = (i), ação auditada (W9a, 1.4.4); PLAN-195 — P-1 a P-4 do replay aceitas; a P-5 é proposta do CEO com medição (1.4.4), ratificada no SIGN do ADR-201 (D-17). |

**Onde o plano mudou:** frontmatter (`external_wait`, orçamento e `eta_calendar`); «Regra de WIP» (D-7,
D-17 e D-21); «Goal» e Q7 (D-2, D-17 e D-18); mapa de colisões (pegada da W5c e A3.1 — D-14); W2 (D-5,
D-6, D-14 e D-19); W2.0; W2.6; W3, W3.1 e plano B (D-1 a D-3); W5 e W5.1; «Orçamento»; «Decisões
pendentes»; «Blockers»; «Next»; «How to continue».

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
- **Q7 — escopo da 1.4.3.** Núcleo de ~12–13 assinaturas (W1, W4, W3b e W6; W7a do PLAN-183; W2; W5c
  depois da W2 se o debate fechar a tempo; rc.1 + GA); a escolha entre 1.4.3 e 1.5.0 sai do diff do
  `SPEC/v1`; se a cota apertar, a W5c sai primeiro. **Emendada na S362 (2026-10-02):** a parte A do
  PLAN-195 e a W3, que estavam no texto original, SAÍRAM do núcleo (o PLAN-195 inteiro e a W3 vão para a
  1.4.4); entrou o re-pin manual do Codex (RP); a versão é 1.4.3, porque nenhum pacote do núcleo toca o
  `SPEC/v1`. → «Goal», «Decisões do Owner — S362» e pré-condições da W7.
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

## Decisões pendentes do Owner — S361 (rodada 1 do debate)

**Estado em 2026-10-02 (ratificação do Owner, `.claude/plans/PLAN-194/debate/round-3/approved.md`):** a 1
ficou SUPERADA (a cura landou em `65cd50d7`); a 2, a 4, a 5 e a 6 foram ACEITAS como recomendadas; a 3 NÃO
foi tomada — o Owner escolheu o re-pin manual, a W3 fica ADIADA para depois da 1.4.3 e o VETO de Segurança
segue levantado (ver «Decisões do Owner — S362»). O texto abaixo é o das recomendações, mantido como
registro.

Saíram do consenso da rodada 1 (`round-1/consensus.md`, §8), foram atualizadas na rodada 2 e têm a **FORMA FINAL**
no consenso FINAL da rodada 3 (`.claude/plans/PLAN-194/debate/round-3/consensus.md`, §5). Cada uma traz a
RECOMENDAÇÃO do CEO, em linguagem simples, e está **pendente de decisão do Owner (S361)** — nenhuma é decisão
tomada, e o `approved.md` terminal do debate só nasce depois da ratificação delas (consenso r3 §8). **A decisão 3
é a que libera o VETO da W3: sem ela escrita, nenhum pacote da W3 começa.** O debate está FECHADO (regra de
parada em «Approach», item 4).

1. **Vaga da cura da corrida do `agent_spawn` (condição 67; risco 11, unidade 4, item W2.0).** É o único
   pré-requisito do Owner para o SIGN da W2, que saiu PROCEED na rodada 2. **Recomendação, pendente de decisão
   do Owner (S361):** pacote canônico PRÓPRIO, landado ANTES do SIGN da W2 — o 1.º pacote na vaga da W2, ou a
   primeira vaga que abrir antes. A aposentadoria da condição 67 vai no `CHANGELOG.md` do corte. Alternativa:
   dentro da W2, com +2 paths; 150 a 300k tokens + ~50k do censo AST, 0 a 1 sessão.
2. **Pré-condição e RECORRÊNCIA da W2.6.** **Recomendação, pendente de decisão do Owner (S361):** (a) trocar
   «todas as sessões do Claude fechadas» por «todas as sessões DESTE projeto fechadas»; (b) predicado do
   AMEND-4: PID vivo ⇒ pula a família; mtime < 10 min ⇒ recusa a execução; spool ativo ou `.draining.*` com
   PID vivo ⇒ recusa a execução; (c) aceitar a W2.6 como manutenção RECORRENTE, a cada ~2 a 4 semanas de uso
   intenso, quando o `/ceo-boot` acusar ≥ 100 mil travas; (d) rodar a 1.ª já. Mais de uma W2.6 por mês ⇒
   gatilho da T2 (pacote de kernel próprio).
3. **Empacotamento do verificador de assinatura da W3 — É ESTA DECISÃO QUE LIBERA O VETO DA W3.** A W0.6
   mostrou que o comando `npm audit signatures` NÃO serve e que a biblioteca `sigstore` chamada COM política de
   identidade SERVE. A escolha é o EMPACOTAMENTO: **(ii)** `sigstore` em versão exata, com lockfile de
   integridade de toda a árvore sob o manifesto ADR-192, instalado com `npm ci --ignore-scripts` em staging novo
   — código de terceiro governado pelo repositório; **(i)** o módulo interno do npm, com lista canônica de
   versões e shas e recusa fora dela — muda num upgrade do npm do Homebrew, e a falha é fail-closed (perde
   vivacidade, não segurança). Nos dois casos o verificador depende de `node` e o `SBOM.md` o declara.
   **Recomendação, pendente de decisão do Owner (S361): (ii)**, preferida pelo portador do VETO e por outro
   crítico. A retirada do VETO vale no instante em que a decisão estiver ESCRITA. «Confiança no registro» ⇒ VETO
   segue LEVANTADO ⇒ ESCALATE-TO-OWNER por múltipla escolha. Recusar o `node` ⇒ plano B (re-pin manual).
   Escrever (ii) ratifica também a exceção (5) da «Regra de WIP»: o pacote 1a com 9 paths (o 9.º é o
   inventário de ambiente, condição 13/17 do consenso r3).
4. **Sentinela de qualidade (desenho (b) da W3).** **Recomendação, pendente de decisão do Owner (S361):** opção
   (ii) — a W3 landa SEM sentinela, declarada (R-2); o gatilho do ADR-111 §2 fica preservado como NÃO AVALIÁVEL
   até haver corpus com sha e linha de base; os três críticos aceitam. Alternativa (i): construir o corpus e a
   linha de base antes da W3 (cota do Codex m × N revisões + ~100k tokens).
5. **Modelo e esforço fixos no argv do rail (W3, pergunta 10).** **Recomendação, pendente de decisão do Owner
   (S361):** `gpt-6-astra` + `xhigh`, condicionado ao re-teste da Q11; o par e as flags (`--ignore-user-config`
   incluída) precisam existir também na 0.156.1, que o corte usa; o id entra em `_VALID_MODELS` no pacote 2,
   depois da W3b; trocar de modelo é cerimônia por GERAÇÃO. **Adopters:** recomendação de opt-in, mantendo o
   padrão da conta, porque um id fixo que a conta deles não sirva rebaixa o rail a advisory.
6. **Evidência da aceitação automática.** **Recomendação, pendente de decisão do Owner (S361):** evento na
   cadeia HMAC (§12 do AMEND-1). «Só no registro» apenas por decisão ESCRITA, com o resíduo R-3.
7. **Para ciência, sem decisão:** (a) a carência é de 48 h, então o pin anda ~2 dias atrás da `latest`; (b) a
   W3 tem 1,6 a 2,8 M tokens em 3 a 4 sessões ([1c/]1b, 1a, 2 e kernel), e a W3.6 depende deles e da rota 2
   invertida, que pode ser a 1.ª peça da W7.1; (c) cada promoção é janela de manutenção; (d) o rollback exige
   rede (R-16), mas não cota (condição 18); (e) toda cerimônia do verificador exige re-verificação logo depois
   (condição 19); (f) a calibração da W2 custa 2 chamadas `claude -p` na vez da W2 (freio Q1); (g) a W2 e a W5c
   seguem pela fila.

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

- **S362 (2026-10-02):** RP — a sonda da 0.160.0, o pacote `codex-pin-0160` gerado, o ensaio verde e o rail
  no 0.156.1, antes do SIGN do Owner (sábado 2026-10-03). Nenhuma série oficial de rail canônico de outro
  pacote começa antes do LAND do RP; sombras criadas antes dele são rebaseadas antes da 1.ª rodada oficial,
  e a 1.ª rodada no 0.160.0 é re-teste do instrumento. **A W3 está ADIADA para a 1.4.4** (decisão 3 não
  tomada): as entradas da W3 abaixo valem como registro para lá.
- **Cláusula do Owner (S361, Q3): debate FECHADO; as três ondas estão liberadas do portão do debate** (W5c na
  rodada 1, W2 na rodada 2, W3 na rodada 3). Os must-fix e as condições valem por onda e por pacote. A **W3** só
  começa com a decisão pendente 3 ESCRITA (é ela que retira o VETO; «confiança no registro» ⇒ ESCALATE). As
  demais ondas não dependem do debate.
- W1: medição W0.1/W0.2 (OQ-2 respondida na S361: o Owner fixa a imagem do runner). Prazo externo
  2026-10-19.
- W2: **LIBERADA** pelo PROCEED da rodada 2 (MF-R2-W2-1..4 e os must-fix de execução como
  pré-requisitos; o CEO os aplica ao plano e ao rascunho do `ADR-055-AMEND-4` sem nova rodada); a cura do
  `agent_spawn` (W2.0) LANDOU (`65cd50d7`). O que falta, por pacote (S362): o LAND do RP antes da série
  oficial de rail; a W0.5 rodada no HEAD e o H1 vivo no LEDGER antes do SIGN do U2-A; o AMEND-4 condensado
  antes do U2-D; o U2-A a U2-C em série na vaga 2. A limpeza W2.6 roda depois do LAND do U2-B (decisão 2
  aceita; D-5).
- W3: **LIBERADA do portão do debate, CONDICIONADA à decisão pendente 3** — a decisão 3 ESCRITA (retira o VETO;
  «confiança no registro» ⇒ ESCALATE) e as condições 1 a 5 do consenso r3 (decisões 4, 5 e 6 no AMEND-1 antes do
  1b; plano reconciliado com o AMEND-1; hospedeiro da guarda; dono para a lacuna da família do log); W0.6 feita;
  guarda das fontes (condição 6) antes do 1.º LAND do 1a; S-13/S-14 e guarda de rede do `node` medidos (10 e 11)
  antes do SIGN do 1a; pacote de kernel de registro de ações landado antes da W3.6 (ou a decisão pendente 6);
  rota 2 invertida nos derivadores do kit (pré-condição da W3.6); 3.ª vaga inicial (ocupada pela W3b até a
  decisão 3 — Q8); a W3b landada antes (mesmo `codex_cli_shape.py`); árvore sem modificação rastreada no SIGN
  (na abertura da S361 a árvore estava limpa; a poda do `CLAUDE.md` num fechamento vem ANTES do land da W3 —
  risco 9); L1 recomendado.
- W5c: **LIBERADA** pela rodada 1, inalterada na rodada 2 (must-fix MF-W5c-1 e MF-W5c-2 e ajustes 35 a 40 do consenso como
  pré-requisitos); re-teste pago na vez; W6 landada antes (`.claude/settings.json`) — ou no MESMO
  pacote, se a OQ-14 se aplicar (prontos juntos antes de ~21/11); vaga 4 (S362), landando depois da
  W6.2, da W5a, da W5b e do U2-C, sem esperar o U2-D; sujeita à linha de corte de 2026-10-11.
- W7: W4 landada; pacote de ADR e W7 nunca em voo juntos (`CHANGELOG.md`); o kit corre só pela rota 1
  do runner do re-pass, e a rota 2 vira recusa nomeada, com controle (decisão S362, D-4; a inversão da
  rota 2 volta com a W3, na 1.4.4).

## Next

**Feito até 2026-10-02:** as medições W0.1, W0.2 e W0.6 (no LEDGER) e os lands abaixo, todos ancestrais
do `97a78fce` (`git merge-base --is-ancestor`): L1, L2a e L2b (`6f7069d3`,
`c4574b72`, `eb2e1e49`); W3b (`a9924eb1`, `803d7b5e`, `399efbaa`, `a0a6df06`); W1 (`c54934d8`); W2.0
(`65cd50d7`); debate único FECHADO e ratificado (`5c52998b`).

**Caminho crítico da 1.4.3 (S362):**

1. **RP:** texto do re-pin neste plano → sonda da 0.160.0 → pacote `codex-pin-0160`, ensaio e rail no
   0.156.1 → SIGN do Owner (sábado 2026-10-03) → `--verify-codex-pin` = `verified`; a 1.ª rodada no
   0.160.0 é re-teste do instrumento.
2. **W2, em série no `spool_writer.py`:** pré-registro da W0.5 no LEDGER → W0.5 no HEAD, em paralelo com os
   verificadores do spool e o H1 vivo → U2-A → U2-B → W2.6 (Owner; depois dela, 12 agentes) → U2-C (W0.5
   depois da cura e 3.ª leva do estresse na sombra) → U2-D (num fechamento de sessão).
3. **W5c, em paralelo:** pré-registro do re-teste → re-teste pago com PASS; W6.0 → W6.2; W5b; rodadas na
   sombra; rodada final sobre o patch re-derivado depois do LAND do U2-C.
4. **Fora do caminho, mas antes do kit ou da rc.1:** W4, W7a do PLAN-183, W5.1, W5a, doc da W6,
   derivadores do kit e FX.
5. **Corte:** seção `[1.4.3]` do `CHANGELOG.md` → RM → kit → rc.1 → hold de 24 h → GA. Linha de corte: o
   kit começa no máximo em 2026-10-11.

## How to continue

Primeira mensagem de uma sessão nova: «Ler o PLAN-194 e o `.claude/plans/PLAN-194/LEDGER.md` (a pasta
`PLAN-194/` e o LEDGER só existem depois do 1.º commit de trabalho); conferir
`git log --oneline -5`, `gh run list --limit 5`, `npm view @openai/codex dist-tags` (a `latest` era a 0.160.0 em 2026-10-01 às ~21:30Z e
seguia a 0.160.0 em 2026-10-02 às ~19:43Z; muda com frequência, com várias estáveis por semana — conferir; uma
0.160.x antes do SIGN do RP regenera o pacote, ver o plano B da W3), `codex --version` (0.156.1 até a sentada do
re-pin manual, RP; 0.160.0 depois dela, até o LAND da W3, que fica para depois da 1.4.3),
`claude --version` (2.1.287 em 2026-10-01; congelado durante cada onda — Q14), `df -h /System/Volumes/Data`
(o volume de dados, onde ficam o `$TMPDIR` e os clones — risco 13); ver quais vagas canônicas estão em voo
(PLAN-194, PLAN-195, PLAN-183) e seguir a ordem da regra de WIP do topo. Se hoje ≥ 2026-10-19 e a W1 não
landou: parar tudo e fazer a W1.»

**Regras de operação do trabalho longo — decisões do Owner S361 (2026-10-01).**

- **Início e cota (Q1).** Condição de início, válida só no T0 (2026-10-01, S361): statusline com
  semanal ≤ 50% e janela de 5 h ≤ 30% — cumprida, por declaração do Owner. Nas ondas seguintes não há
  limiar da Q1: valem o freio da Q2 (Codex, abaixo), o teto de agentes vivos e a leitura da cota no
  início de cada onda (medição, sem limiar decidido; se a cota apertar, a W5c sai primeiro — Q7).
  **Teto de agentes (decisão do Owner S362, D-21):** até 8 agentes vivos, com 1 vaga sempre reservada
  para refutador, até a W2.6 (que roda depois do LAND do U2-B, com as sessões DESTE projeto fechadas —
  decisão 2 aceita); depois dela, até 12. Até 4 pacotes canônicos em voo. SEM trocar de conta durante o trabalho (CLAUDE.md §4, «Quota sem
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
  `~/.claude/projects/<slug>/s360-packs/` ao fim de cada fase (cobre um reboot inesperado; na S362, a
  pasta é `s362-packs/<id>/`, com o patch e o `SHA256SUMS` de cada commit da sombra); instalação
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

**Regra da rodada 1 do debate:** todo Check deve ficar VERMELHO antes e VERDE depois, com a afirmação
dentro do código de saída — um Check verde por construção não prova nada. Os critérios da W2, da W3 e
da W5c abaixo foram reescritos na rodada 1 para cumprir a regra (e o braço vermelho da W5c.4 afirma a
DIFERENÇA EXATA, `+claude-sonnet-5-5` na superfície S1); o executor confere a mesma propriedade nos
demais ao abri-los.

- [ ] Validate verde em push e no nightly depois de 2026-10-19, com a perna 3.9 viva. — Check: gh run list --workflow validate.yml --limit 5 --json conclusion
- [ ] State dir sem acúmulo por PID e SEM decisão de guard perdida, depois de um dia de uso normal e sem `drain canonical lock timeout` sob a carga da W0.5 (rodadas 1 e 2: o critério de SEGURANÇA barra; a contagem é higiene). **Critérios que BARRAM o SIGN:** (a) o controle de entrega de decisão (W2.2-bis) passa de vermelho a verde — «decisão perdida» lê o VEREDITO gravado pela W0.5 no LEDGER (`W0.5-veredito (pos-cura): decisoes_descartadas=0`), que o Check lê; (b) o invariante por conjunto fica verde (todo `record_id` exatamente uma vez); (c) `verify_chain()` íntegro sob estresse com escritores `agent_spawn`, depois da cura da W2.0. **Higiene — a prova é no VIVO, com as sessões do projeto paradas** (evita corrida com arquivo sendo apagado; o teste unitário não basta): o critério primário é o FLUXO H1, um SCRIPT que lê `pid` e `wall_ns` do log canônico, com `|D|_min` ≥ 200 pré-registrado — abaixo dele reprova, e denominador zero reprova — e que não fica verde por vácuo num dia leve nem envelhece com o estoque (o marcador `<script do H1>` abaixo é literal: o Check sai ≠ 0 até o script existir; nome a fixar no pacote da W2.4-bis); o teto absoluto — no máximo 1.000 JOURNALS de 0 byte, no state dir INTEIRO, depois de 24 h — é limite SECUNDÁRIO de sanidade; as travas vão à parte, sem limiar de segurança; as regex são o texto do AMEND-4 §4.7 (`fullmatch` + `re.ASCII`); o carimbo do LAND sai do commit, em ISO UTC validado, e o marcador literal `<sha do commit do LAND>` faz o Check sair ≠ 0; o braço de timeouts é uma «guarda de regressão» (G2): 0 linhas `drain canonical lock timeout` com carimbo ≥ LAND (o arquivo não rotaciona — lane `H-03` —, por isso a janela). **O Check sai ≠ 0** acima do limiar, com timeout ou decisão perdida na janela, ou com denominador zero. **Medido 2026-09-30 (vermelho):** 219.468 arquivos de 0 bytes nos 3 padrões, de 219.839 entradas; 19.568 linhas da classe no total, 2.980 só em 2026-09-30 (UTC). Números antes/depois no LEDGER. — Check: python3 -m pytest .claude/hooks/tests/test_spool_state_amend4.py -q -k "fast_path or deadline or origin or invariant" && python3 -c "import os,re,subprocess as s,sys;d=s.check_output(['python3','.claude/hooks/_lib/runtime_paths.py','--state-dir'],text=True).strip();p=re.compile(r'audit-pending\.([1-9][0-9]{0,9})\.journal',re.ASCII);n=sum(1 for r,_,fs in os.walk(os.path.join(d,'state')) for f in fs if p.fullmatch(f) and os.path.getsize(os.path.join(r,f))==0);print(n);sys.exit(0 if n<=1000 else 1)" && L="$(TZ=UTC git log -1 --date=format-local:%Y-%m-%dT%H:%M:%SZ --format=%cd <sha do commit do LAND>)" && python3 -c "import re,sys;sys.exit(0 if re.fullmatch(r'20[0-9]{2}-[01][0-9]-[0-3][0-9]T[0-2][0-9]:[0-5][0-9]:[0-5][0-9]Z',sys.argv[1]) else 1)" "$L" && test "$(awk -v t="$L" '$1 >= t && /drain canonical lock timeout/' "$(python3 .claude/hooks/_lib/runtime_paths.py --state-dir)/audit-log.errors" | wc -l | tr -d ' ')" = 0 && python3 .claude/scripts/<script do H1> --d-min 200 --since "$L" && grep -q 'W0.5-veredito (pos-cura): decisoes_descartadas=0' .claude/plans/PLAN-194/LEDGER.md
- [ ] Rail com pin automático verificado (no hook do rail; os cortes de release seguem ancorados no manifesto — pergunta 7 da W3): versão nova COM procedência e FORA do manifesto ⇒ `status == "verified_auto"` **E** `pin_source == "registry"` (os literais do código; os dois juntos — condição 9), sem assinatura nova do Owner; SEM procedência, ou com identidade ou assinatura inválida, ⇒ recusada, fail-CLOSED (W3.4). O Check usa `--verify-codex-pin <caminho do lançador> --allow-auto-pin` — a flag DEPOIS do caminho, porque a CLI toma `argv[0]` como lançador (`.claude/hooks/check_pair_rail.py:2513`) —, liga o **modo obrigatório da camada 2** (SKIP = falha, condição 13) e fica vermelho enquanto o global for o 0.156.1 do manifesto. **Validade (condição 23):** o Check vale para o instante do fechamento da W3; se uma cerimônia futura puser no manifesto a mesma versão instalada, ele volta a dar `manifest`, e isso é esperado. O Check da W3.1, sem flag, cobre só o período ATÉ o LAND. — Check: CEO_CODEX_AUTO_PIN_CRYPTO_REQUIRED=1 python3 -m pytest .claude/scripts/tests/test_codex_auto_pin_verify.py::TestRefusalMatrix .claude/scripts/tests/test_codex_auto_pin_verify.py::TestFiacaoLayer1 .claude/scripts/tests/test_codex_auto_pin_verify.py::TestCryptoRealLayer2 .claude/scripts/tests/test_codex_auto_pin_verify.py::TestCensus .claude/hooks/tests/test_check_pair_rail_auto_pin.py::TestHookCells .claude/hooks/tests/test_codex_pin_registry_guard.py::TestRegistryAndSourceGuard -q && python3 .claude/hooks/check_pair_rail.py --verify-codex-pin "$(command -v codex)" --allow-auto-pin | python3 -c 'import json,sys;d=json.load(sys.stdin);sys.exit(0 if d.get("status")=="verified_auto" and d.get("pin_source")=="registry" else 1)'
- [ ] `check-model-deprecations.py --check --today 2026-10-13` = 0. — Check: python3 .claude/scripts/check-model-deprecations.py --check --today 2026-10-13
- [ ] Publish do GA 1.4.3 com Node ≥ 22.14 e npm exato. — Check: npm view ceo-orchestration version
- [ ] Textos do ADR-149/SUPPORT/doc de adopter alinhados ao CC ≥ 2.1.286 (instalado em 2026-10-01: 2.1.287), com data e substrato. — Check: python3 .claude/scripts/generate-available-models.py --check
- [ ] Sonnet 5.5 adotado pela emenda 4 do ADR-149 (W5c), com a linha de preço e o conjunto de vermelhos esperado sem achado novo, e o re-teste pago registrado no LEDGER. O Check afirma `claude-sonnet-5-5` no bloco do ADR-149, no `availableModels`, no `cost-table.yaml` e na entrada do re-teste no LEDGER (hoje nenhum dos quatro tem o id, então fica vermelho antes). — Check: python3 .claude/scripts/generate-available-models.py --check && python3 .claude/scripts/check-model-currency.py --expected-reds .claude/data/model-currency-expected-reds.txt && grep -q 'claude-sonnet-5-5' .claude/adr/ADR-149-model-id-allowlist.md && grep -q 'claude-sonnet-5-5' .claude/settings.json && grep -q 'claude-sonnet-5-5' .claude/scripts/cost-table.yaml && grep -q '^## W5c.1' .claude/plans/PLAN-194/LEDGER.md
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
  7 da W3 (o pin automático não cobre os cortes), W3b.3 (gpt-5.5 NÃO confirmado na fonte primária — LEDGER, S361; refresh dos ids de julho/dezembro feito no commit a9924eb1), W5.0/W5.1 com o CC
  2.1.286/2.1.287, W6 redesenhada (backup como proteção principal), mapa de colisões com o leque de ADR
  e a 4.ª exceção ao teto, exceção da OQ-11 para a W3b, L2 estendida, L5 nova, backlog com dono e números
  de estado. OQ-2, OQ-5, OQ-7, OQ-8, OQ-10 e OQ-14 marcadas RESPONDIDA; OQ-11 PARCIALMENTE RESPONDIDA (só a exceção da Q8; a ordem (a)–(f) e o empate seguem abertos). Nenhum marcador de
  esclarecimento vivo (PLAN-SCHEMA §14) no texto. A passagem a `executing` fica para o 1.º commit de
  trabalho.
- S361 (2026-10-01, rodada 1 do debate L3; consenso em `.claude/plans/PLAN-194/debate/round-1/consensus.md`):
  três críticos (Segurança, QA e DevOps, todos em `claude-opus-5-5`, id servido informado por cada um).
  Vereditos por onda: **W5c PROCEED** (`design-coherent`; VETO de Segurança retirado com condições),
  **W2 e W3 RUN-ANOTHER-ROUND** (VETO levantado nas duas); a rodada 2 julga só a W2 e a W3. Ajustes do
  consenso aplicados a este plano: W2 sem a relocação (a antiga W2.3 saiu), com a cura do `agent_spawn`
  como pré-condição do SIGN (W2.0), o prazo na drenagem forçada de saída (W2.2-bis), a regra de travas
  (nenhum `unlink` de `*.lock` em hook; opção T1 por padrão) e o conteúdo exigido do
  `ADR-055-AMEND-4`; W3 com o verificador FORA do hook, todo «presente, mas não verificado» fail-CLOSED,
  carência de 48 h no relógio do registro, identidade do construtor fixada, evento durável na cadeia
  HMAC (pacote de kernel de registro de ações), W0.6 e a W3.6 logo depois do LAND da W3 (o corte
  independe do Codex global — rota 2); W5c no formato da Amendment 2, com a entrega ao adopter, o
  `_tier_rank` e o pré-registro do re-teste; W0.5 pré-registrada; Success criteria reescritos; mapa de
  colisões e paths com as linhas novas; riscos 3, 4, 11 e 17; decisões pendentes do Owner registradas em
  seção própria; regra de parada do debate registrada. Status inalterado (`executing`).
- S361 (2026-10-02, rodada 2 do debate L3; consenso em `.claude/plans/PLAN-194/debate/round-2/consensus.md`,
  commit `48f03b3a`; escopo W2 e W3; os mesmos três críticos, todos em `claude-opus-5-5`, id servido
  informado por cada um; fato novo: a medição W0.6 do LEDGER). Vereditos por onda: **W2 PROCEED**
  (`design-coherent`, os três críticos; VETO de integridade do log de auditoria RETIRADO, condicionado a
  MF-R2-W2-1..4), **W3 RUN-ANOTHER-ROUND** (VETO de cadeia de suprimento LEVANTADO; a W0.6 mudou a
  arquitetura da decisão de confiança), **W5c** PROCEED (rodada 1, inalterado); a rodada 3 é a ÚLTIMA e julga
  só a W3. Ajustes do consenso aplicados a este plano (W2 e W3; os do AMEND-4 e do AMEND-1 ficam nos
  rascunhos): W2 LIBERADA, módulo de teste renomeado para `test_spool_state_amend4.py` com seletores que
  casam só os testes do item, W2.4 CONDICIONAL fora do pacote base, W2.0 por node id e censo AST, W2.2 com
  `flush` e células do sinalizador, W2.2-bis com `T_min` = menor timeout registrado, âncora `min(import,
  início do processo)` e sinal de trava presa em ≤ T, W2.4-bis com G6 e G7 e check de travas ≥ 100 mil, W2.5
  com a composição da cadeia e os mutantes M-a..M-d, W2.6 RECORRENTE sob T1 com o predicado do AMEND-4,
  W0.5 com as células, a estatística e a calibração com o harness real, Check de sucesso da W2 reescrito;
  W3 com `sigstore.verify` com política (o `npm audit signatures` NÃO serve), A-14 e A-15 como recusa (sai
  «aceita e declarada»), literais e ids imutáveis da W0.6, hosts fechados e tetos, pacotes 1b → 1a → 2 mais
  o de kernel, verificador, auxiliar `node` e lockfile DENTRO do manifesto ADR-192 (não «livre»), `SBOM.md`,
  Checks da CLI com `--allow-auto-pin` e o literal `registry`, promoção pelos bytes verificados com P-01 da
  árvore inteira e quiesce, rota 2 INVERTIDA no kit da W7, R-16 (o rollback exige rede); decisão pendente 3
  REESCRITA (empacotamento (i) ou (ii); recomendação (ii); «confiança no registro» ⇒ ESCALATE) e as
  decisões 1, 2, 4, 5, 6 e «para ciência» atualizadas. Status inalterado (`executing`).
- S361 (2026-10-02, rodada 3 do debate L3 — a ÚLTIMA; consenso FINAL em `.claude/plans/PLAN-194/debate/round-3/consensus.md`;
  escopo W3; os mesmos três críticos). **Debate FECHADO, `design-coherent` nas três ondas:** W5c PROCEED (r1), W2
  PROCEED (r2) e **W3 PROCEED (r3, 3 de 3 críticos; nenhum P0, nenhuma afirmação FALSA no plano)**, com o VETO da W3
  retirado SÓ quando a decisão pendente 3 estiver ESCRITA como ramo (ii) ou (i) («confiança no registro» ⇒
  ESCALATE) e 23 condições de execução por pacote (consenso r3 §2). O `approved.md` terminal (DEBATE-SCHEMA §6)
  AINDA NÃO EXISTE: depende da ratificação do Owner (consenso r3 §8). Ajustes 1 a 17 do consenso r3 aplicados a
  este plano: debate fechado e W3 condicionada à decisão 3 (topo, Approach, cláusula, W3); pacotes pelo AMEND-1
  (1c → 1b → 1a → 2; Gate 4 no pacote 2) e a divergência de contagem do `env-inventory.json` (9 paths no 1a
  no ramo (ii): exceção (5) proposta pelo CEO, ratificada junto da decisão 3); hospedeiros da guarda no mapa de colisões e correção da linha da guarda de Bash; oráculo
  dos paths novos; W3.3 e W3.4 por node id de CLASSE com o modo obrigatório da camada 2; `status` e `pin_source`
  no Check; novas pré-condições da W3.6; W7 (sequência e K-06); material assinado; item com dono para a lacuna de
  guarda da família do log; decisões pendentes na forma final; riscos; orçamento; LEDGER (registrar ao abrir o
  1a); inventário de ambiente. Status inalterado (`executing`).
- S362 (2026-10-02, abertura do trem da 1.4.3): **decisões do Owner D-1 a D-23** registradas em seção
  própria. Commit 1 (texto do re-pin): o plano B da W3 virou a 1.ª tarefa — re-pin manual 0.156.1 → 0.160.0
  (RP, pacote `codex-pin-0160`, molde `PLAN-193/codex-pin-0156` com `--ga-tag v1.4.2`) —, a W3 foi para a
  1.4.4 e o passo do Owner cita a versão exata (o detector do ensaio sai vazio). Commit 2: «Regra de WIP»
  com 4 canônicos e a definição de «em voo»; «Goal», Q7 e «Orçamento» sem o PLAN-195 e sem a W3; W2 em 4
  pacotes (U2-A a U2-D) com a convivência declarada; W2.0 marcada feita (`65cd50d7`) com os 4 node ids
  reais; W2.6 depois do LAND do U2-B (decisão 2 aceita); W5.1 ancorada no LAND do RP; mapa de colisões da
  W5c pela pegada `WFABLE51` (30 paths, medidos), com o A3.1 do ADR-149 dentro da W5c; «Decisões
  pendentes», «Blockers», «Next» e «How to continue» atualizados. LEDGER: entrada do RP, pré-registro da
  W0.5 e arquivamento do T0, da W0.1 e da W0.2 com âncoras estáveis. Status inalterado (`executing`).

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
- Debate único, rodada 1: `.claude/plans/PLAN-194/debate/round-1/consensus.md` (vereditos por onda,
  divergências resolvidas, ajustes e decisões pendentes); rodada 2:
  `.claude/plans/PLAN-194/debate/round-2/consensus.md` (W2 PROCEED; W3 para a rodada 3) e os rascunhos
  PROPOSED do `ADR-055-AMEND-4` e do `ADR-182-AMEND-1` na mesma pasta; rodada 3 (a ÚLTIMA; consenso FINAL):
  `.claude/plans/PLAN-194/debate/round-3/consensus.md`. Medição W0.6: seção `W0.6` de `.claude/plans/PLAN-194/LEDGER.md`. Também: ADR-055-AMEND-3 (premissa
  «anômalo» emendada pela W2); ADR-111 (corpus travado do pair-rail); `docs/CROSS-LLM-THREAT-MODEL.md`
  (T-8, atualizado pela W3).
- Externo: actions/runner-images#14748 (Ubuntu 26.04); docs.npmjs.com/trusted-publishers; changelog do
  GitHub de 2026-09-03 (várias configurações de publicador confiável).
