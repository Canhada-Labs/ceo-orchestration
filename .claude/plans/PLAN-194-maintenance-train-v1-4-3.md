---
id: PLAN-194
title: Trem de manutenção pós-GA 1.4.2 até a v1.4.3
status: draft
created: 2026-09-30
owner: CEO
depends_on: [PLAN-193]
level: L3
budget_tokens: "estimado (contexto do CEO; subagentes à parte): W0 medições 150-300k (sem cota paga); W1 150-300k; W2 0,8-1,5 M com rail (debate único do plano, com a W3 e a W5c); W3 (pin automático verificado, L3) 0,8-1,5 M com debate + rail; W3b 100-200k; W4 150-300k; W5a/W5b 300-600k + cota paga da W5.0; W5c (adoção do Sonnet 5.5, L3 — decisão do Owner S359) 2-4 M com debate + rail + cota paga do re-teste na vez (precedente wave-opus55); W6 100-200k + isca paga mínima da W6.0; W7 1-2 M (kit + re-pass + cortes); W8 50-150k; livres L1-L4 300-600k"
budget_sessions: "4-8 (estimado; cada assinatura do Owner é uma parada; W2 e W7 podem precisar de sessão própria)"
context_risk: high
external_wait: "GitHub: ubuntu-latest vira Ubuntu 26.04 de 2026-10-19 a 2026-11-19 (actions/runner-images#14748). Owner: fixar a imagem do runner Ceo (OQ-2); medições pagas só na vez de cada onda (W5.0, W6.0 e o re-teste da W5c — decisão S359); rodar o script de limpeza única da W2.6 com todas as sessões do Claude fechadas (decisão S359); decidir as OQs abertas; assinar W1, W2, W3, W3b, W4, W5 (inclusive a W5c), W6, W8 e os cortes rc.1/GA; hold de 24 h entre rc e GA (ADR-103). Codex: ficar no 0.156.1 sem npm update -g até a W3 landar (decisão S359). Retenção: arquivo rotacionado mais antigo da cadeia completa 90 dias por volta de 2026-11-21. OpenAI: gpt-5/o3 aposentam em 2026-12-11."
eta_calendar: "W1 antes de 2026-10-19 (prazo externo); backup agendado e W6 antes de ~2026-11-21; W3b antes de 2026-12-11; GA v1.4.3 = max(assinaturas do Owner, hold de 24 h rc→GA) — sem data prometida"
tags: [maintenance, release, ci, ubuntu-26-04, audit-spool, codex-pin, npm, claude-code-substrate, retention]
---

> **Regra de WIP (trabalho em voo) — vale para este plano inteiro e divide as vagas com o PLAN-195
> e o PLAN-183.** No máximo **3 pacotes canônicos em voo** ao mesmo tempo; cada pacote com
> **≤ 400 linhas e ≤ 8 paths**. **Exceções — só estas três, todas geradas por ferramenta:**
> (1) **W7** (kit do corte derivado por script, como no PLAN-192/193); (2) **W5c — adoção do Sonnet
> 5.5** (decisão do Owner S359, «Adotar»: ~40 espelhos num pacote atômico derivado por script —
> precedente: OQ-2 do PLAN-193, resolvida «Exceção declarada (Recomendado)»);
> (3) o **plano B da W3** (re-pin manual: materiais gerados pelo `re-pin-codex.py`; o teto vale para o
> diff canônico). **Nunca dois pacotes tocando o mesmo arquivo** (mapa de colisões em «Approach»).
> Canônico = arquivo que só muda por cerimônia (pacote revisado + sentinel assinado por GPG do Owner).
>
> **Ordem das vagas — DECIDIDA pelo Owner (S359, 2026-09-30): «Codex automático, depois adopter
> (Recomendado)».** As 3 vagas iniciais: 1.ª **W1** deste plano (CI no Ubuntu 26.04, prazo
> 2026-10-19) → 2.ª **parte A do PLAN-195** (W1 de lá; se a ADR dela sair num pacote próprio — a
> W1-ADR —, as duas usam a MESMA vaga, uma depois da outra, a ADR antes do código) → 3.ª **W3** deste
> plano (pin automático verificado do Codex, L3). Quando a W1 landar, a vaga dela vai para a **W7a do
> PLAN-183** (conserto do A1, único P1 dos adopters); a vaga seguinte vai para a **W2** deste plano
> (estado da auditoria). A **W7b do PLAN-183** segue logo depois da W7a (OQ-21 de lá, recomendação
> aceita pelo Owner na mesma sessão). A **W5c** entra na fila depois da W2, salvo se o debate pedir
> antes (decisão do Owner, «Adotar»). O resto: **OQ-11** (inclui a parte B e a W3 do PLAN-195 em
> posição explícita). A limpeza única dos órfãos (W2.6) é operação do Owner e não ocupa vaga.
> Medições (W0, W5.0, W6.0), debates e lands livres (L1–L4) também não ocupam vaga canônica.

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
| W1 | o runner `Ceo` usa a imagem «Ubuntu Latest (24.04)», versão `latest` — se migra junto: não medido | lane `DEP-01` (`gh api orgs/Canhada-Labs/actions/hosted-runners`) |
| W1 | passos do job de governança usam o `python3` do sistema antes do `setup-python`; dois `import yaml` dependem de PyYAML do sistema | `validate.yml:61-441`, `:304-305`, `setup-python` em `:467` |
| W1 | o template do adopter roda `ubuntu-latest` com o `python3` do sistema (com fallback de pip para PyYAML) | `templates/.github/workflows/validate.yml.template:34`, `:124-126` |
| W2 | state dir com **219.527** entradas, **219.301** com 0 bytes (73.177 `audit-pending.N.journal.lock`, 73.176 `audit-pending.N.journal`, 73.153 `audit-spool.N.jsonl.lock`) | medido 2026-09-30 (`os.scandir`, só leitura) em `~/.claude/projects/<slug>/state` |
| W2 | todo processo que importa `audit_emit` registra um drain FORÇADO no `atexit`; o forçado espera até 2,5 s pelo lock canônico e lista o dir ordenado | `audit_emit.py:13344`; `spool_writer.py:66`, `:2366`, `:2436`, `:2480`, `:2573`, `:2665` |
| W2 | guards PreToolUse estouraram o timeout de 5 s sob concorrência (ação passa sem decisão) | lane `CC285-05`; `.claude/settings.json` (43 registrações com `"timeout": 5`) |
| W3 | Codex pinado 0.156.1; estável do npm 0.159.2; faixa aceita `>=0.128.0,<0.157.0` ⇒ atualizar o CLI antes de mudar o pin FECHA o rail; 18 versões estáveis em 30 dias; atestado SLSA v1 presente em 0.156.1 e 0.159.2 | `.claude/governance/codex-cli-pin.txt:147`; lanes `CX-01`, `CX-03`; memória `project-s359-urgency-triage` |
| W3b | `check-model-deprecations.py --check` sai **1** na árvore viva a partir de 2026-10-12/13 (gpt-5/o3 aposentam em 2026-12-11) | medido 2026-09-30 com `--today 2026-10-13` (rc 1) e sem `--today` (rc 0); lane `CC285-08` |
| W4 | publish com Node 20 e npm em faixa flutuante; a doc do npm exige Node ≥ 22.14 para publicação sem token | `.github/workflows/npm-publish.yml:245-250`, `:260`; lane `DEP-02` |
| W4 | tags rc **pulam** o job de publish (regra que sustenta carga, fixada por teste) | `npm-publish.yml:29-30`, `:227`; `.claude/governance/npm-trusted-publisher.txt:5-7` |
| W5 | CC 2.1.284: Ultracode não força mais xhigh; Sonnet 5.5 (`claude-sonnet-5-5`, US$ 2/10) virou o Sonnet padrão e entra pelo prefixo `claude-sonnet-5`; sessão sem `permissions.defaultMode` nasce em auto. CC 2.1.285: Bash em background morre em 30 min (máx. 2 h) | lanes `CC-01`, `CC-02`, `CC-04`, `CC285-01`, `CC285-02`, `ANT-01` |
| W6 | `cleanupPeriodDays: 90` no projeto (vence o 3650 do usuário); `audit-log-2026-08-1.jsonl` (mtime 23/08) é `*.jsonl` de topo | `.claude/settings.json:861`; `templates/settings/settings.base.json:671`; lanes `CC285-06`, `F-AUDIT-RETENTION` |

## Goal

Cortar a **v1.4.3** com o CI verde no Ubuntu 26.04, o estado da auditoria sem acúmulo por PID, o rail
do Codex com pin automático verificado (procedência conferida e hash registrado sem assinatura manual a
cada versão), o publish do npm num Node suportado e a documentação alinhada
ao Claude Code 2.1.285 — cada mudança com controle vermelho→verde registrado.

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
   mesmo pacote da W3, se couber no teto, ou landa antes dela. (No plano B da W3 vale ainda o motivo antigo: o molde do `re-pin-codex.py` só lê e
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
adotar). Esse mesmo achado é o controle vermelho da W5c. (d) Re-pin manual da 0.159.2 (a versão
anterior desta W3): descartado pelo Owner na S359 em favor do pin automático; fica como **plano B**
da W3. (e) Recusar o Sonnet 5.5 por ora (a recomendação anterior do CEO): descartada pelo Owner na
S359 («Adotar»).

**Mapa de colisões (nunca dois pacotes no mesmo arquivo).** Vale para os três planos que dividem as
vagas (este, o PLAN-195 e o PLAN-183); as ondas de outro plano são citadas pelo NOME da seção.

| arquivo | quem toca | ordem |
|---|---|---|
| `.claude/settings.json` | W6 (retenção); W5c (adoção do Sonnet 5.5: `availableModels` é gerado do ADR-149 pelo `generate-available-models.py`); **W3 do PLAN-195** (só se o Owner decidir ligar o sandbox depois da medição) | **W6 primeiro** (data de risco ~2026-11-21); depois a W5c e a W3 do PLAN-195, uma de cada vez; sandbox e retenção num pacote só apenas se as duas decisões ficarem prontas juntas antes da data (OQ-14) |
| `templates/settings/settings.base.json` | W6 (só se mudar o padrão dos adopters); W5c | W6 primeiro, W5c depois; ou um pacote só se os dois ficarem prontos juntos |
| `.claude/adr/ADR-149-model-id-allowlist.md` | W5a (texto do Ultracode, A3.1); W5c (emenda 4) | um pacote só: a correção da W5a vai dentro da emenda 4 da W5c (o Owner decidiu adotar) |
| `.claude/hooks/_lib/codex_cli_shape.py` | W3b; W3 (só se o desenho do argv fixo tocar) | sequenciais; se o debate da W3 puser este arquivo no pacote dela, a W3b (prazo duro 2026-12-11, pacote pequeno) entra no MESMO pacote, se couber no teto, ou landa antes — decisão na abertura da W3, sem mudar a ordem das vagas |
| `.claude/scripts/codex_invoke.py` | W3 (argv com modelo e esforço fixos); W3b (só se o conjunto derivado atingir o exemplo dele) | sequenciais, na mesma ordem da linha acima |
| `.claude/scripts/substrate-watch.json` | W5.1 (e a W3, se o desenho gravar o `codex_cli` ali) | UM refresh só, depois do land da W3 — ou com o 0.156.1, se o corte vier antes |
| `scripts/install.sh` e `.claude/scripts/data/installer-write-safety-baseline.txt` | W5b; W1a/W1b do PLAN-183 (re-derivação do pacote do ponteiro `PROTOCOL.md`, que toca os dois); W8 do PLAN-183 (baseline, via `upgrade.sh`) | **W5b primeiro** (pequena, 3 paths); depois a W1a/W1b do PLAN-183, re-derivadas sobre ela; por fim a W8 do PLAN-183. Toda onda que toca `scripts/**/*.sh` fora de `scripts/tests/` regenera o baseline do censo no MESMO patch (CLAUDE.md §5, PLAN-185) |
| `.github/workflows/smoke-install.yml` e `.github/workflows/ownership-nightly.yml` (os dois rodam `runs-on: ubuntu-latest`: `smoke-install.yml:196`, `ownership-nightly.yml:34`) | W1.5 (só se o censo W0.1 os marcar); W1a/W1b do PLAN-183 (estão entre os 16 paths do pacote do ponteiro) | **W1.5 primeiro** (prazo 2026-10-19); a W1 do PLAN-183 é re-derivada no HEAD depois dela |
| `.github/workflows/validate.yml` | W1 | nenhuma onda dos outros dois planos o toca hoje (conferido 2026-09-30 nas seções S359 do PLAN-183 e no PLAN-195) |
| `.claude/governance/gate-scripts-manifest.txt` (manifesto ADR-192) | W7 (só se o `release.sh`, membro do manifesto, mudar); W7b e W10 do PLAN-183 (sha do `validate-governance.sh`) | **nunca em paralelo**: a mudança do `release.sh` na W7 landa ANTES da W7b/W10 ou DEPOIS do land delas |
| `INSTALL.md` | W6 (mitigação da retenção); W8 do PLAN-183 (linha sobre o `VERSION` semeado) | **W6 primeiro** (data de risco ~2026-11-21); a W8 do PLAN-183 depois — ou a linha do `VERSION` entra no mesmo patch de documentação da W6 |
| `.claude/scripts/ceo-boot.py` | L2 (disco + deriva) | um pacote só |
| guarda de Bash (hook, testes) e docs de ameaça | W0–W2 do PLAN-195 | nenhuma onda deste plano toca esses arquivos; o `settings.json` do sandbox (W3 do PLAN-195) está na 1.ª linha; a W0 do PLAN-195 edita `docs/threat-model.md` em land livre — ver risco 9 (árvore limpa no SIGN) |
| espelhos gerados (`npm/templates/`, `npm/.claude/`, `dist/`) | W1.4 (se mexer no template do adopter); W5c; ondas que tocam hook | **não são path de pacote**: saída de build ignorada pelo git (`.gitignore:47` `npm/.claude/`, `:50` `npm/templates/`, `:198` `dist/`; `git ls-files npm/templates` = 0, medido 2026-09-30). Não entram em commit nem no Scope do sentinel; `scripts/npm-rebuild.sh` e `scripts/build-plugin.py --check` ficam como passos da bateria, sobre saídas locais |

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
| `.claude/plans/PLAN-194/codex-pin-0159-2/` (OWNER-PIN-SIGN.sh, rehearse-pin-0159-2.sh, pin-0159-2-approved.md, codex-cli-pin.txt.new, codex-cli-pin-manifest.json.new) | 0 | não | plano B da W3 (gerado; a etiqueta segue a versão do dia) |
| `.claude/plans/PLAN-193/codex-pin-0156/OWNER-PIN-SIGN.sh` | 0 | não | plano B da W3 (molde, só leitura) |
| `.claude/scripts/re-pin-codex.py` | 0 | não | plano B da W3 (só executa) |
| `.github/scripts/validate-pair-rail-verdict.py` | 0 | **sim** | W3 (não editar; lê a faixa do pin — controle W3.4 d) |
| `.github/workflows/release.yml` | 1 | — | referência (`:550-557`, `:760`) |
| `.claude/adr/ADR-182-codex-payload-pin-enforcement.md` | 1 | — | referência (emendado pela W3) |
| `.claude/scripts/codex_invoke.py` | 0 | não | W3 (argv com modelo e esforço fixos) / W3b (conferir) |
| `.claude/workflows/council-audit.js` | 1 | — | W3 (pergunta 6 do debate; se ficar fora, backlog) |
| `.claude/scripts/substrate-watch.json` | 0 | não | W5.1 |
| `.claude/hooks/_lib/codex_cli_shape.py` | 1 | — | W3b |
| `.claude/hooks/tests/test_codex_cli_shape.py` | 0 | não | W3b |
| `.claude/scripts/optimizer/codex_phase_gate.py` | 0 | não | W3b (se o conjunto derivado atingir) |
| `.claude/scripts/check-model-deprecations.py` | 0 | não | W3b (só executa) |
| `.claude/scripts/model-deprecations.json` | 0 | não | backlog (refresh do ledger) |
| `.claude/scripts/tests/test_check_model_deprecations.py` | 0 | não | W3b (regressão) |
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
| `.claude/hooks/_lib/model_routing.py` | 1 | — | backlog (Haiku 4.5) |
| `.claude/scripts/tests/test_settings_guard_loadability.py` | 0 | não | W5.1 |
| `.claude/scripts/check-substrate-watch.py` | 0 | não | W5.1 (Owner roda `--refresh`) |
| `scripts/install.sh` | 1 | — | W5b |
| `scripts/upgrade.sh` | 1 | — | W5b (só medir `:219`, `:3881-3884`) |
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
| `.claude/scripts/check-absolute-time-budget.py` (novo; nome proposto) | 0 | não | L4 (instrumento do censo) |
| `.claude/scripts/tests/test_check_absolute_time_budget.py` (novo) | 0 | não | L4 |
| `.claude/scripts/adopt-model.py` (novo) | 0 | não | L3 |
| `.claude/scripts/tests/test_adopt_model.py` (novo) | 0 | não | L3 |
| `.claude/workflows/nightly-hygiene.js` | 1 | — | referência |
| `.claude/scripts/local/release.sh` | 0 | **sim** | W7 (cerimônia se mudar) |
| `.claude/governance/gate-scripts-manifest.txt` | 1 | — | W7 (só se o `release.sh` mudar; nunca em paralelo com a W7b/W10 do PLAN-183 — mapa de colisões) |
| `.claude/plans/PLAN-193/derive-kit-142.py`, `derive-ga-kit-142.py`, `OWNER-GA-CUT.sh`, `test-ga-kit.sh`, `gen-envelope-ga.py`, `repass-ga/run-ga-repass.sh`, `LEDGER.md` | 0 | não | W7 (moldes, só leitura) |
| `.claude/plans/PLAN-194/derive-kit-143.py`, `.claude/plans/PLAN-194/derive-ga-kit-143.py`, `.claude/plans/PLAN-194/test-rc1-kit.sh` (novos) | 0 | não | W7 |
| `.claude/plans/PLAN-194/LEDGER.md` (novo) | 0 | não | todas |
| `.claude/plans/PLAN-194-maintenance-train-v1-4-3.md` (este) | 0 | não | — |
| `.claude/adr/ADR-002-hooks-package-layout.md` | 1 | — | fora (o Owner manteve o piso 3.9 na S359) |
| `CHANGELOG.md` | 0 | não | W7 |
| `CLAUDE.md` | 0 | não | fora (Gate-1; só no closeout, pelo CEO) |
| `.claude/scripts/validate-governance.sh` | 0 | **sim** | só executa |
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

- [ ] **W0.1 (para W1) — Docker `ubuntu:26.04`** (existência da tag no Docker Hub: não conferida;
  conferir antes). Rodar: (a) o `validate.yml.template` ativado por `scripts/tests/run-activated-workflow.py`
  sobre uma instalação descartável (mesmo método da medição 24.04 com 10/10 verdes, CLAUDE.md §5);
  (b) os passos do job de governança do `validate.yml` que usam o `python3` do sistema (`:61-441`),
  incluindo os `import yaml` de `:304-305`; (c) a suíte de hooks no `python3` da imagem (3.14 segundo
  a lane `DEP-01`; a matriz atual para em 3.12); (d) censo dos 21 workflows com `ubuntu-latest` e dos
  6 jobs `Ceo`: quais usam `python3`, `shellcheck` ou `jq` do sistema (a imagem 26.04 traz shellcheck
  0.11.0 e jq 1.8.1 — lane `DEP-01`). — Check: none (medição)
- [ ] **W0.2 (controle vermelho da W1)** — consultar o manifesto do `setup-python`
  (`actions/python-versions`, `versions-manifest.json`) e registrar com data: 3.9 sem build para
  26.04; 3.10+ com build. — Check: none (medição)
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
perna 3.14 verde (ou vermelha com achado nomeado no LEDGER). **Dependências:** W0.1, W0.2, OQ-2.
**Prazo:** land antes de **2026-10-19**.

### W2 — Estado da auditoria: arquivos por PID e drain forçado (L3, debate)
Check: python3 -m pytest .claude/hooks/tests/test_spool_state_gc.py .claude/hooks/tests/test_spool_drain_contended_skip.py .claude/hooks/tests/test_spool_writer_cache.py -q

**Objetivo:** a saída de um hook sem spool próprio não toma o lock canônico nem varre o diretório; os
arquivos vazios por PID deixam de se acumular; os ~219 mil órfãos atuais somem. **Por que importa:**
com o dir cheio, cada drain forçado lista e ordena ~219 mil nomes sob o lock canônico (~0,24-0,30 s
por drain, lane `H-02`); com saídas concorrentes o lock de 2,5 s estoura e guards PreToolUse passaram
do timeout de 5 s — e um guard que estoura o timeout deixa a ação passar sem decisão (lane
`CC285-05`). **Paths:** `.claude/hooks/_lib/spool_writer.py` (1); `.claude/adr/ADR-055-AMEND-4-spool-state-gc.md`
(1, novo, PROPOSED); `.claude/hooks/SessionStart.py` (1) só se o GC entrar na reconciliação de início
de sessão; `.claude/hooks/tests/test_spool_state_gc.py` (0, novo); `test_spool_drain_contended_skip.py`
(0). `audit_emit.py` (1) fica fora, salvo se o debate mostrar necessidade. **Estimativa:** 200-300
linhas, 3-5 paths (estimado). **Debate:** SIM — núcleo da cadeia de auditoria, e a cura emenda a
premissa do ADR-055-AMEND-3 de que o timeout do drain forçado é «genuinamente anômalo».

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
  não ocupa vaga): alivia o sintoma — o drain forçado deixa de listar ~219 mil nomes — até o acúmulo
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
contagem por classe no boot (lane `H-03`).

### W3 — Pin automático verificado do Codex CLI (L3, debate; decisão do Owner S359)
Check: python3 .claude/hooks/check_pair_rail.py --verify-codex-pin "$(command -v codex)"

**Decisão do Owner (S359, 2026-09-30):** «Pin automático verificado (Recomendado)». Motivo dado por
ele: não ter de mexer nisso de novo a cada versão (o Codex soltou 18 estáveis em 30 dias). Fonte:
memória `project-s359-urgency-triage` (parágrafo «Codex — decisão do Owner»). **Substitui** o re-pin
manual da 0.159.2 que a versão anterior desta onda descrevia — ele fica como **plano B** (fim da seção).

**Objetivo:** uma versão nova do Codex passa a valer para o rail sem cerimônia por versão, desde que a
procedência seja conferida automaticamente; o Owner deixa de assinar a cada atualização.
**Desenho decidido (mesma fonte):** (a) na 1.ª vez que o rail vê uma versão nova, confere sozinho a
procedência no npm (atestado SLSA v1 do CI da OpenAI — conferido presente em 0.156.1 e 0.159.2) e
registra o sha256 verificado, sem assinatura do Owner; (b) sentinela automática com corpus fixo de
defeitos avisa se o revisor piorar, **sem travar**; (c) modelo e esforço fixos no argv do rail (cura a
lane `CX-07`, antes no backlog); (d) cada veredito registra versão, modelo e esforço. **Custo
declarado na fonte:** emenda do ADR-182 + debate de segurança + 1 cerimônia. **Até landar:** ficar no
0.156.1, **sem `npm update -g`** — a faixa aceita hoje (`>=0.128.0,<0.157.0`, `codex-cli-pin.txt:147`)
recusaria a versão nova e fecharia o rail.

**Perguntas de desenho que o debate precisa fechar (não decididas aqui):**
1. Onde o sha verificado fica gravado — não pode ser o manifesto (`codex-cli-pin-manifest.json`,
   oráculo 1), que só muda por cerimônia.
2. Como conferir a assinatura do atestado num framework só-stdlib (CLAUDE.md §4) — candidato a
   medir: delegar ao `npm audit signatures` (o subcomando existe no npm desta máquina; conferido só
   por `--help` em 2026-09-30).
3. O que a faixa do `codex-cli-pin.txt` passa a dizer: o validador do veredito
   (`validate-pair-rail-verdict.py`, membro do manifesto ADR-192) lê a faixa desse arquivo
   (`--codex-cli-pin-file`, `release.yml:760`).
4. Só versões estáveis (dist-tag `latest`), nunca alpha (era a recomendação da antiga OQ-3).
5. Sem rede ou sem atestado: recusa (fail-closed na entrada, CLAUDE.md §4) e o rail segue na última
   versão verificada.
6. Rodadas manuais e o daemon: `codex_invoke.py:193`, `council-audit.js:325` e o `codex exec review`
   manual não conferem o pin (lane `CX-04`); o daemon `app-server` se atualiza sozinho fora do pin
   (lane `CX-06`) — entram no desenho ou ficam declarados.

**Paths (candidatos; o debate fecha a lista; oráculo rodado em todos):**
`.claude/adr/ADR-182-AMEND-1-codex-auto-pin-provenance.md` (1, novo, PROPOSED; nome proposto);
`.claude/hooks/check_pair_rail.py` (1); `.claude/governance/codex-cli-pin.txt` (1, só se a faixa
mudar); `.claude/hooks/tests/test_check_pair_rail_auto_pin.py` (0, novo); `.claude/scripts/codex_invoke.py`
(0; argv com modelo e esforço fixos); corpus da sentinela (path a definir no debate). **Estimativa:**
300-400 linhas por pacote, 4-8 paths (estimado); se o debate pedir mais, dividir em pacotes de ≤ 8
paths — sem exceção ao teto. **Debate:** SIM, o debate único do plano (W2, W3 e W5c — Approach,
item 4). **Cerimônia:** sim. **Vaga:** 3.ª das 3 iniciais (ordem decidida pelo Owner).

- [ ] W3.1 regra operacional até o land: Codex no 0.156.1, sem `npm update -g`; nenhuma rodada de
  rail com outro binário. — Check: python3 .claude/hooks/check_pair_rail.py --verify-codex-pin "$(command -v codex)"
- [ ] W3.2 debate único do plano (ver W2.1) e ADR-182-AMEND-1 em PROPOSED com as respostas às 6
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
- [ ] W3.6 depois do LAND: Owner atualiza o Codex para a estável do dia; na 1.ª rodada real, o
  `--verify-codex-pin` dá `verified` sem assinatura nova, e o `session_meta` mostra a versão, o
  originador `codex_exec` e 0 sessões «guardian» (lanes `CX-06`, `CX-12`). — Check: python3 .claude/hooks/check_pair_rail.py --verify-codex-pin "$(command -v codex)"

**Declarar no material assinado** (o que o desenho não cobrir): (a) o daemon `app-server` roda fora do
pin (lane `CX-06`); (b) o `~/.codex/config.toml` global muda o comportamento do rail (esforço passou de
max para xhigh em 29/09 sem re-pin — lane `CX-07`) — o argv fixo fecha isto para o rail; (c) rodadas
manuais que não conferem o pin. **Controle vermelho→verde:** W3.4. **Dependências:** debate; L1
(recomendado); 3.ª vaga inicial (decidida); árvore sem modificação rastreada no SIGN. **Prazo:** sem data
externa; não é pré-condição do corte W7 (o 0.156.1 está dentro da faixa pinada).

**Plano B — re-pin manual pelo molde (ADR-182 §5; precedentes 0155 e 0156).** Só se o debate recusar
o pin automático ou o 0.156.1 parar de funcionar antes do land. Passos: pré-condições do molde (árvore
sem modificação rastreada — o SIGN aborta, `OWNER-PIN-SIGN.sh:330` do molde, lane `CX-13`; L1
landado; este plano commitado, porque o `re-pin-codex.py` exige `--plan`; tag `v1.4.2` ancestral do
HEAD); `python3 .claude/scripts/re-pin-codex.py <versão> --plan PLAN-194 --mold
.claude/plans/PLAN-193/codex-pin-0156/OWNER-PIN-SIGN.sh --ga-tag v1.4.2 --dry-run` e depois sem
`--dry-run` (baixa ~331 MB: diretório próprio, piso de `df`, limpeza confinada); ensaio com prefixos
npm descartáveis (`$REHEARSE_CODEX_PREFIX`, `$REHEARSE_OLD_CODEX_PREFIX`); rodadas manuais
congeladas entre o `npm i -g` e o SIGN; Owner faz `npm i -g @openai/codex@<versão exata>` e o SIGN na
mesma sentada. Pacote em `.claude/plans/PLAN-194/codex-pin-<etiqueta>/` (regra do `re-pin-codex.py`:
`X.Y.Z` → `XY-Z`, ex.: `0159-2`). Controle: `--verify-codex-pin` = `mismatch` logo após o `npm i -g`
→ `verified` depois do SIGN.

### W3b — Ids OpenAI que se aposentam fora da lista de revisores
Check: python3 .claude/scripts/check-model-deprecations.py --check --today 2026-10-13

**Objetivo:** a lista `_VALID_MODELS` (`codex_cli_shape.py:97-105`) não aceita ids que aposentam.
**O conjunto sai do instrumento, não de lista à mão:** `check-model-deprecations.py` (hoje aponta
`gpt-5`/`o3` com aposentadoria 2026-12-11 — lane `CC285-08`). Medido 2026-09-30: `--check --today 2026-10-13`
sai 1; sem `--today`, 0. Nenhum workflow de CI chama o `--check` (grep em `.github/`); quem passa a
mostrar WARN é o nightly-hygiene e o pré-voo não-fatal do `upgrade.sh` no adopter
(`scripts/upgrade.sh:2867`). **Paths:** `codex_cli_shape.py` (1); `test_codex_cli_shape.py` (0);
`codex_invoke.py` e `optimizer/codex_phase_gate.py` (0) só se o conjunto derivado atingir o padrão ou
o exemplo deles; `model-currency-expected-reds.txt` (0) se o `check-model-currency.py` (autoridade A2 =
`_VALID_MODELS`) mudar o conjunto de vermelhos. **Estimativa:** 30-60 linhas, 2-5 paths. **Debate:** não.

- [ ] W3b.1 remover da lista os ids que o instrumento marca; ajustar os testes. — Check: python3 -m pytest .claude/hooks/tests/test_codex_cli_shape.py -q
- [ ] W3b.2 `check-model-currency.py` com o conjunto de vermelhos esperado atualizado conscientemente. — Check: python3 .claude/scripts/check-model-currency.py --expected-reds .claude/data/model-currency-expected-reds.txt

**Controle:** `--check --today 2026-10-13` = 1 hoje (vermelho, medido) → 0 depois (verde).
**Dependências:** nenhuma com a W3 (não espera o debate dela); se o desenho da W3 puser
`codex_cli_shape.py` ou `codex_invoke.py` no pacote, a W3b entra no mesmo pacote da W3, se couber
no teto, ou landa antes dela (mapa de colisões). **Vaga:** sem posição fixa; fura a fila pela data
(OQ-11). **Prazo:** duro em **2026-12-11**; o WARN começa em 2026-10-12.

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
contra o log do 1.4.2 com Node 20.20.2 + npm 11.20.0 (lane `DEP-02`). **Dependências:** OQ-5.
**Prazo:** land antes da rc.1 da W7, fora de janela de release.

### W5 — Substrato Claude Code 2.1.284/2.1.285
Check: python3 .claude/scripts/generate-available-models.py --check

**Objetivo:** textos e instalação coerentes com o CC 2.1.285, com números re-medidos pelo mesmo
instrumento (W5.0). O piso ≥ 2.1.280 continua correto; nenhum hook quebra no 2.1.285 (33 eventos
idênticos — lane `cc-local-impact`).

- [ ] **W5.0 — medições pagas, na vez da W5 (decisão do Owner S359: «Só quando chegar a vez
  (Recomendado)»; antiga W0.3; regras de medição da W0).** Com os MESMOS instrumentos da S357: as 8
  sondas `claude -p` + `get_settings` de Ultracode × esforço (inclusive max + ultracode, antes
  impossível); para qual id o alias `sonnet` do Agent/Workflow resolve no 2.1.285 (entra na pergunta
  (b) do debate da W5c); taxa de prompts do modo auto (controle S342; o
  runbook S341 foi medido no 2.1.259); latência de hooks numa sessão SOLO (o p50 de 1.192 ms da S359
  está contaminado pela concorrência — lane `CC285-05`). — Check: none (medição paga; resultado no LEDGER)
- [ ] **W5a — textos do Ultracode e do Bash em background (depois da W5.0).** `SUPPORT.md:107` e
  `docs/adopter-new-model-fast-access.md:154-158`, `:347-370` (livres, com data e substrato); nota de
  timeout explícito para jobs longos em background (30 min padrão, máx. 2 h). A correção do ADR-149
  A3.1 (`:381`, canônico) vai dentro da emenda 4 da W5c (o Owner decidiu adotar o Sonnet 5.5; mapa de
  colisões). — Check: python3 .claude/scripts/check-time-unit.py SUPPORT.md docs/adopter-new-model-fast-access.md
- [ ] **W5b — `defaultMode` na instalação `--ceremony user` (OQ-7).** Hoje o `install.sh` grava só a
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
  Owner). **Tamanho:** exceção (2) da regra de WIP do topo — pacote atômico derivado por script com o
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
  (mapa de colisões); SIGN/LAND. — Check: python3 .claude/scripts/check-ceremony-script.py
- [ ] **W5.1 — refresh do ledger de substrato, UMA vez, depois do land da W3 (ou com o Codex no
  0.156.1, se o corte vier antes)** (codex_cli,
  claude_code, cc_native_usage), com a réplica do loader re-derivada no MESMO patch
  (`test_settings_guard_loadability.py:138` fixa `2.1.280`; o teste de `:522` fica vermelho quando o
  ledger sobe, por desenho). O Owner roda `check-substrate-watch.py --refresh`. —
  Check: python3 -m pytest .claude/scripts/tests/test_settings_guard_loadability.py -q

**Estimativa:** W5a ~100-150 linhas, 3 paths; W5b 60-120 linhas, 2 paths; W5c (adoção) = exceção (2)
da regra de WIP do topo (~40 espelhos num pacote atômico; precedente OQ-2 do PLAN-193), 2-4 M tokens
com debate e rail + a cota paga do re-teste. **Debate:** só a W5c (no debate único do plano).
**Dependências:** W5.0 (paga, na vez da W5); W5c.1 (paga, na vez da W5c); W6 antes da W5c no
`.claude/settings.json`; W3 para a W5.1 (se landar antes do corte). **Prazo:** antes do corte W7; se
a W5c não chegar a tempo, o corte declara no material assinado que o prefixo `claude-sonnet-5` admite
o 5.5 sem a emenda.

### W6 — Retenção do log de auditoria
Check: python3 -c "import json;print(json.load(open('.claude/settings.json'))['cleanupPeriodDays'])"

**Objetivo:** nenhum arquivo da cadeia de auditoria é apagado pela varredura do Claude Code.
**Fatos:** a varredura apaga `*.jsonl` de topo mais velhos que o `cleanupPeriodDays` da sessão que
varre (CHANGELOG `[1.4.2]`, linhas 350-365); o valor do projeto é 90 (`.claude/settings.json:861`) e
vence o 3650 do usuário (lane `CC285-06`); o arquivo rotacionado mais antigo completa 90 dias por volta
de 2026-11-21; `ceo-backup.sh` inclui os arquivos rotacionados (`:204`, `:237`) e grava fora de
`~/.claude/projects/`. **Paths:** `.claude/settings.json` (1); `templates/settings/settings.base.json`
(1) só se o Owner decidir mudar o padrão dos adopters; `INSTALL.md` (0). **Estimativa:** 10-30
linhas, 1-3 paths. **Debate:** não.

- [ ] W6.0 isca da varredura de transcripts (paga mínima; na vez da W6 — mesma decisão do Owner S359,
  «Só quando chegar a vez (Recomendado)»; antiga W0.4; regras de medição da W0): diretório de projeto descartável com
  um `*.jsonl` de topo antigo; medir se o 2.1.285 apaga, por qual data (mtime?) e qual
  `cleanupPeriodDays` vale (projeto × usuário). — Check: none (medição; resultado no LEDGER)
- [ ] W6.1 Owner, fora do repositório e já: agendar `ceo-backup.sh` (crontab ou LaunchAgent) e rodar a
  primeira cópia. — Check: bash .claude/scripts/ceo-backup.sh --dry-run
- [ ] W6.2 cerimônia com o valor escolhido na OQ-8, depois da isca W6.0. — Check: python3 -c "import json;print(json.load(open('.claude/settings.json'))['cleanupPeriodDays'])"

**Controle vermelho→verde:** a isca da W6.0 apagada com o valor atual (vermelho, se o 2.1.285 ainda
varrer) → preservada com o valor novo (verde). **Colisões:** `.claude/settings.json` também é tocado
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
precisa de `codex_cli` dentro da faixa pinada — cumprido com o Codex no 0.156.1 enquanto a W3 não
landa, ou pela W3 depois dela; W1 obrigatória se o corte for depois de 2026-10-19; W2 recomendada. **Prazo:** sem data prometida (`eta_calendar`).

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
- [ ] **L2 — `/ceo-boot`: piso de disco + deriva de substrato (um pacote, mesmo arquivo).** (a) Check
  de `df` e do tamanho do `$TMPDIR` (2.ª ocorrência da classe «disco cheio»: clones de agente em 29/09,
  suítes de teste do adopter em 30/09 — cure a classe); (b) ligar `check-substrate-drift.py` offline
  (sem `--fetch`) como check (herança do PLAN-193 W5; sobrepõe o W3a do PLAN-176 — o CEO reconcilia lá).
  80-150 linhas, 2-3 paths. — Check: python3 -m pytest .claude/scripts/tests/test_ceo_boot.py .claude/scripts/tests/test_ceo_boot_enhanced.py -q
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

## Orçamento

| onda | tokens (estimado) | sessões | vaga canônica | quem espera |
|---|---|---|---|---|
| W0 | 150-300k (sem cota paga) | 1 | não | — |
| W1 | 150-300k | 1 | sim (1.ª) | assinatura; prazo 19/10 |
| W2 | 0,8-1,5 M | 1-2 | sim (a vaga seguinte à da W7a do PLAN-183 — ordem decidida) | debate único + assinatura; limpeza W2.6 rodada pelo Owner (script entregue, fora do repositório) |
| W3 | 0,8-1,5 M | 1-2 | sim (3.ª vaga inicial — ordem decidida) | debate único + assinatura; Codex parado no 0.156.1 até o land |
| W3b | 100-200k | 1 | sim | assinatura; prazo 2026-12-11 |
| W4 | 150-300k | 1 | sim | assinatura; antes da rc.1 |
| W5a/W5b | 300-600k + cota paga da W5.0 | 1 | sim (install.sh; o texto do ADR-149 vai na W5c) | W5.0 na vez da W5; decisão OQ-7 |
| W5c (adoção do Sonnet 5.5) | 2-4 M + cota paga do re-teste | 1-2 | sim (depois da W2, salvo se o debate pedir antes; exceção de tamanho declarada) | debate único + re-teste pago na vez + W6 landada (`settings.json`) + assinatura |
| W6 | 100-200k + isca paga mínima da W6.0 | 1 | sim (antes da W5c e da W3 do PLAN-195 no `settings.json`) | backup do Owner + decisão OQ-8 (+ OQ-14) |
| W7 | 1-2 M | 1-2 | sim (cortes) | hold de 24 h + assinaturas + npm |
| W8 | 50-150k | com outra | sim | OK do download |
| L1-L4 | 300-600k | espalhadas | não | — |

## Riscos

1. **Prazo de 19/10 perdido** ⇒ Validate vermelho em todo push e toda noite. Mitigação: W1 na 1.ª vaga;
   OQ-2 (fixar a imagem do runner `Ceo`) como rede sem código.
2. **O censo W0.1 acha muitos workflows quebrando** ⇒ passa de 8 paths. Mitigação: dividir por
   criticidade (gates do release primeiro); a mitigação oficial `ubuntu-24.04` é por arquivo.
3. **W2 mexe no núcleo da cadeia de auditoria** ⇒ risco de perder evento. Mitigação: debate, invariantes
   em teste de estresse, `verify_chain()`, rail, predicado conservador de GC.
4. **Pin automático aceita uma versão ruim com procedência válida** (o atestado prova a ORIGEM, não a
   QUALIDADE do revisor). Mitigação: sentinela de corpus fixo (avisa, não trava — decisão do Owner),
   versão/modelo/esforço registrados em cada veredito, debate de segurança. **Até a W3 landar:** um
   `npm update -g` fecha o rail (a faixa recusa a versão nova); mitigação: Codex no 0.156.1 (decisão
   do Owner, W3.1). No plano B volta a janela entre `npm i -g` e o SIGN: mesma sentada + rodadas
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
   explícita por arquivo no mapa de colisões, conferidas quando cada vaga abrir. Resta a W6 e a W3b
   (com data) atrás de uma fila longa: OQ-11.
9. **Árvore suja no SIGN.** O `CLAUDE.md` está a ~200 bytes do teto de 40.000 e com uma linha não
   commitada ⇒ os moldes de SIGN abortam com modificação rastreada (ex.: `OWNER-PIN-SIGN.sh:330` do
   molde do Codex, lane `CX-13`) — fora deste plano (fechamento do CEO), mas pré-condição de todo SIGN
   deste trem. Mesma classe: a W0 do PLAN-195 edita `docs/threat-model.md` em land livre, e o
   `check-threat-model-freshness.py` escreve nesse arquivo (lição S328). Mitigação: land livre de
   qualquer um dos três planos só com commit feito FORA de janela de SIGN — nenhuma edição sem commit
   quando uma assinatura estiver marcada (de preferência a W0 do PLAN-195 antes do SIGN da W1 daqui).
10. **Medições pagas gastam cota** (ordem do Owner de −1/3 de consumo). Mitigação: só o conjunto mínimo
    (W5.0, W6.0 e o re-teste da W5c), na vez de cada onda (decisão do Owner S359, «Só quando chegar a
    vez (Recomendado)»).
11. **Números envelhecem** (state dir: 218.974 entradas na triagem, lane `H-02`, e 219.527 horas
    depois, medido 2026-09-30; o Codex teve 5 minors estáveis em 12 dias, lane `CX-01`). Mitigação:
    re-medir no início de cada onda.
12. **Evidência de CI some:** runs passam a ser apagados após 90 dias a partir de 2026-10-01 (lane
    `DEP-07`). Mitigação: copiar para o LEDGER o que for evidência (ids, conclusão, datas).
13. **Instrumento vs. modo auto do CC 2.1.281+:** `rm` com alvo em variável é negado em 2 min sem
    resposta ⇒ limpeza confinada trava e o disco enche. Mitigação: `shutil.rmtree` confinado + piso de `df`.
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
- PLAN-192/193 → done; PLAN-170 → abandoned; poda do CLAUDE.md; memória defasada → **CEO, no fechamento**.
- Vazamento de pastas temporárias das suítes de teste de um adopter local → **Owner, numa sessão do adopter**
  (o lado do framework é a L2).
- Backlog sem onda (candidatos a follow-up): 190-FU audit-actions; inventário da dívida «known-open»
  com dono (lane `F-DEBT`); regex de `-FOLLOWUP-` no `check_plan_edit.py:136`; classe FN-04 além do
  ledger (lane `F13`); `codex_invoke.py`/`council-audit.js` passando pela conferência do pin (lane
  `CX-04`), salvo se o debate da W3 os incluir (pergunta 6); [fixar modelo e esforço no argv do rail
  (lane `CX-07`) saiu daqui: entrou na W3, desenho do pin automático]; refresh do `model-deprecations.json`
  (parado desde 2026-06-12, lane `ANT-05`); vigia do Haiku 4.5 (piso 2026-10-15; `model_routing.py:64-70`,
  lane `ANT-04`); pins node20 e `ubuntu-22.04` (`tier-policy.yml`, `mutation-gate.yml`,
  `benchmarks.yml.template` — lanes `DEP-04..06`); rotação do `audit-log.errors` (lane `H-03`); vazamento
  de temporários dos testes do framework (lane `H-06`); `shadow-ci.yml` que nunca rodou (lane `H-12`);
  pilha OTEL inerte (lane `CC-03`); métrica da ordem de −1/3 (custo por tarefa com cache separado).

## Open questions

As perguntas que o Owner já respondeu na S359 (2026-09-30) saíram daqui e estão RESOLVIDAS na tabela
«Decisões do Owner» do Context, com a frase exata: a antiga OQ-1 (piso do Python — «Manter 3.9
(Recomendado)»), a antiga OQ-3 (versão do Codex — perdeu o sentido com o pin automático, «Pin
automático verificado (Recomendado)»; «nunca alpha» virou a pergunta 4 do debate da W3), a antiga
OQ-4 (medições pagas — «Só quando chegar a vez (Recomendado)»), a antiga **OQ-6** (Sonnet 5.5 —
«Adotar»; a W5c virou adoção), a antiga **OQ-9** (limpeza dos ~219 mil arquivos vazios — «Script
pronto, você roda depois (Recomendado)») e a antiga **OQ-13** (3.ª vaga — «Codex automático, depois
adopter (Recomendado)»). Os números das outras ficam iguais, para não quebrar referências. Cada
pergunta que resta traz a recomendação do CEO, em linguagem simples.

- **OQ-2 — Runner «Ceo».** Fixar já a imagem dele em Ubuntu 24.04 nas configurações da organização (sem
  código)? **Recomendação: sim, antes de 19/10.** É uma rede de segurança; a W1 continua.
- **OQ-5 — Prova do publish.** A rc só consegue provar o Node e o npm, não a publicação em si (que só
  acontece no GA). Aceita a prova parcial + o playbook de rollback? **Recomendação: sim.**
- **OQ-7 — Instalação `--ceremony user`.** Gravar `defaultMode: "manual"` ou deixar herdar o modo
  auto do Claude Code? **Recomendação: gravar `manual`** (mesma postura do framework e dos 3 adopters).
- **OQ-8 — Retenção.** **Recomendação: agendar o backup já (W6.1) e, depois da isca (W6.0), subir o
  valor deste repositório para 3650**; o padrão dos adopters fica como está, com a mitigação no
  `INSTALL.md`.
- **OQ-10 — Corte dentro deste plano.** O corte da 1.4.3 (W7) fica aqui? **Recomendação: sim** (é onde
  os P2 do kit se curam).
- **OQ-11 — Ordem do que vem depois da fila já decidida.** Já decidido pelo Owner (ver «Regra de
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
  **Empate a decidir:** se a W7a landar antes de a W2 ter vaga, a vaga da W7a vai para a W2 (ordem
  literal da sua decisão) ou para a W7b («logo depois da W7a»)? **Recomendação: W2** — é a ordem
  literal; a W7b pega a vaga seguinte.
- **OQ-12 — TLC (W8) neste trem?** **Recomendação: sim se sobrar vaga;** senão, declarar no corte.
- **OQ-14 — Sandbox e retenção no mesmo pacote?** Você decidiu «Medir antes de ligar (Recomendado)»;
  fica aberto, no PLAN-195, só «ligar ou não depois da medição». Se a resposta for ligar (W3 do
  PLAN-195), essa mudança no `.claude/settings.json` pode ir no mesmo pacote da retenção (W6 daqui),
  para economizar uma assinatura? Hoje o PLAN-195 prevê cerimônia própria (W3 de lá). O mesmo arquivo
  também é tocado pela W5c (adoção do Sonnet 5.5). **Recomendação: sim, mas só se as duas decisões
  ficarem prontas juntas antes de ~2026-11-21;** a W6 vai primeiro e não espera o sandbox nem a W5c,
  porque a retenção tem data.

## Blockers

- W1: OQ-2; medição W0.1/W0.2. Prazo externo 2026-10-19.
- W2: debate único do plano; vaga seguinte à da W7a do PLAN-183 (ordem decidida); a limpeza W2.6 é
  alívio rodado pelo Owner, não bloqueia.
- W3: debate único do plano e ADR-182-AMEND-1; 3.ª vaga inicial (decidida); árvore sem modificação
  rastreada no SIGN (hoje há ` M CLAUDE.md` e edições em planos em andamento — risco 9); L1 recomendado.
- W5c: debate único do plano; re-teste pago na vez; W6 landada (`.claude/settings.json`); vaga depois
  da W2.
- W7: W4 landada.

## Next

1. W0.1 e W0.2 (medição para a W1), sem cota paga.
2. L1 (livre) — antes da W3.
3. Pacote da W1 para cerimônia.
4. Proposta do debate único W2 + W3 + W5c (não ocupa vaga); limpeza única W2.6 quando o Owner rodar o
   script entregue (fora do repositório, todas as sessões do Claude fechadas).

## How to continue

Primeira mensagem de uma sessão nova: «Ler o PLAN-194 e o `.claude/plans/PLAN-194/LEDGER.md`; conferir
`git log --oneline -5`, `gh run list --limit 5`, `npm view @openai/codex dist-tags`, `codex --version`
(deve seguir 0.156.1 até a W3 landar), `df -h /`; ver quais vagas canônicas estão em voo (PLAN-194,
PLAN-195, PLAN-183) e seguir a ordem da regra de WIP do topo. Se hoje ≥ 2026-10-19 e a W1 não landou:
parar tudo e fazer a W1.»

## Success criteria

- [ ] Validate verde em push e no nightly depois de 2026-10-19, com a perna 3.9 viva. — Check: gh run list --workflow validate.yml --limit 5 --json conclusion
- [ ] State dir sem acúmulo por PID depois de um dia de uso normal, sem `drain canonical lock timeout` sob a carga da W0.5. O teste unitário não basta: a prova é no VIVO, com as sessões do Claude paradas (evita corrida com arquivo sendo apagado) — (1) arquivos de 0 bytes nos 3 padrões no state dir INTEIRO, inclusive o subdiretório novo da W2.3, abaixo do limiar fixado no ADR-055-AMEND-4 (proposta para o debate: ≤ 1% do medido hoje); (2) 0 linhas `drain canonical lock timeout` no `audit-log.errors` com carimbo depois do LAND (o arquivo não rotaciona — lane `H-03` —, por isso a janela). **Medido 2026-09-30 (vermelho):** 219.468 arquivos de 0 bytes nos 3 padrões, de 219.839 entradas; 19.568 linhas da classe no total, 2.980 só em 2026-09-30 (UTC). Números antes/depois no LEDGER. — Check: python3 -m pytest .claude/hooks/tests/test_spool_state_gc.py -q && python3 -c "import os,re,subprocess as s;d=s.check_output(['python3','.claude/hooks/_lib/runtime_paths.py','--state-dir'],text=True).strip();p=re.compile(r'^audit-(pending\.\d+\.journal(\.lock)?|spool\.\d+\.jsonl\.lock)$');print(sum(1 for r,_,fs in os.walk(os.path.join(d,'state')) for f in fs if p.match(f) and os.path.getsize(os.path.join(r,f))==0))" && awk -v t="<ISO do LAND, ex. 2026-11-01T00:00:00Z>" '$1 >= t && /drain canonical lock timeout/' "$(python3 .claude/hooks/_lib/runtime_paths.py --state-dir)/audit-log.errors" | wc -l
- [ ] Rail com pin automático verificado: versão nova COM procedência ⇒ `verified` sem assinatura nova do Owner; SEM procedência ⇒ recusada (W3.4). — Check: python3 .claude/hooks/check_pair_rail.py --verify-codex-pin "$(command -v codex)"
- [ ] `check-model-deprecations.py --check --today 2026-10-13` = 0. — Check: python3 .claude/scripts/check-model-deprecations.py --check --today 2026-10-13
- [ ] Publish do GA 1.4.3 com Node ≥ 22.14 e npm exato. — Check: npm view ceo-orchestration version
- [ ] Textos do ADR-149/SUPPORT/doc de adopter alinhados ao CC 2.1.285, com data e substrato. — Check: python3 .claude/scripts/generate-available-models.py --check
- [ ] Sonnet 5.5 adotado pela emenda 4 do ADR-149 (W5c), com a linha de preço e o conjunto de vermelhos esperado sem achado novo, e o re-teste pago registrado no LEDGER. — Check: python3 .claude/scripts/generate-available-models.py --check && python3 .claude/scripts/check-model-currency.py --expected-reds .claude/data/model-currency-expected-reds.txt
- [ ] `cleanupPeriodDays` decidido e backup agendado antes de ~2026-11-21. — Check: bash .claude/scripts/ceo-backup.sh --dry-run
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
