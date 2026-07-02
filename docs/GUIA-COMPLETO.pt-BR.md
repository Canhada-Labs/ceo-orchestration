# Guia Completo — ceo-orchestration

> **EN (fonte canônica):** [GUIA-COMPLETO.md](GUIA-COMPLETO.md).
>
> **Leia isso primeiro.** Este documento é o ponto de entrada único.
> Ele fala com dois públicos ao mesmo tempo: quem NÃO é dev (primeiras
> duas seções) e quem É dev (resto). Cada seção marca o tempo estimado
> de leitura — pule o que não for pra você.

## Mapa deste documento

| Seção | Para quem | Tempo |
|-------|-----------|-------|
| [1. Em 2 minutos](#1-em-2-minutos-não-dev) | Não-dev, PM, founder, cliente | 2 min |
| [2. Em 10 minutos](#2-em-10-minutos-dev) | Dev que nunca viu o framework | 10 min |
| [3. O que é, o que não é](#3-o-que-é-o-que-não-é) | Todos | 5 min |
| [4. Quando usar, quando não usar](#4-quando-usar-quando-não-usar) | Dev | 3 min |
| [5. Instalar em projeto NOVO](#5-instalar-em-projeto-novo) | Dev | 10 min |
| [6. Instalar em projeto EXISTENTE](#6-instalar-em-projeto-existente) | Dev | 20 min |
| [7. Primeiros 10 minutos pós-install](#7-primeiros-10-minutos-pós-install) | Dev | 10 min |
| [8. Uso diário — o loop básico](#8-uso-diário--o-loop-básico) | Todos | 10 min |
| [9. Comandos que você vai usar](#9-comandos-que-você-vai-usar) | Todos | 5 min |
| [10. Como explicar pro time](#10-como-explicar-pro-time) | Líder técnico | 5 min |
| [11. Troubleshooting](#11-troubleshooting) | Dev | consulta |
| [12. Limitações honestas](#12-limitações-honestas) | Todos | 3 min |
| [13. Referências](#13-referências) | Dev | consulta |

---

## 1. Em 2 minutos (não-dev)

### O problema
O Claude Code (ou qualquer LLM de código) sozinho é um freelancer
genial mas generalista. Ele escreve código rápido, mas:

- Pula etapas de segurança porque "ninguém pediu"
- Inventa números e nomes de função que não existem
- Faz 80% do pedido e declara "pronto"
- Não deixa trilha pra você auditar depois

### O que o framework faz
Transforma esse freelancer em **um time estruturado**:

- Um **CEO** (o próprio Claude, em modo protocolo) recebe o pedido
- **VPs** decidem estratégia (Engenharia, Produto, Operações)
- **Especialistas** executam com checklist do domínio
- **Vetos automáticos** bloqueiam merge sem code review, sem teste, ou
  com problema de segurança
- Tudo fica num **audit log** — você entende DEPOIS por que o CEO
  tomou cada decisão

### Você, não-dev, ganha o quê?
- Entende o que vai ser feito antes de ser feito (plano em português)
- Pode perguntar "cadê o status?" e ter resposta objetiva (`/status`)
- Seu time para de entregar feature com bug de segurança óbvio
- Não precisa aprender termos técnicos — o CEO traduz o pedido

### Analogia
> É a diferença entre contratar um **freelancer** (rápido, sem
> processo) e contratar uma **agência** (gerente de conta, equipe
> especializada, revisão antes de entregar). O framework é a agência.

Pronto. Você já sabe o suficiente pra decidir se quer seu time usando
isso. Se a resposta é sim, passa pra próxima seção — ou manda um dev
ler o resto.

---

## 2. Em 10 minutos (dev)

### O que você ganha tecnicamente

1. **Skills como checklists mecânicos.** 151 skills em
   `.claude/skills/core`, `.claude/skills/frontend`, e
   `.claude/skills/domains/<dominio>`. Cada skill é um `SKILL.md` com
   regras verificáveis ("use decimal, não float", "valide CSRF",
   "exige teste de unidade para cada boundary"). Não é "use bom senso".

2. **Spawn Protocol.** Todo agent spawn carrega
   `## AGENT PROFILE` + `## SKILL CONTENT` + `## FILE ASSIGNMENT`
   antes de escrever a primeira linha. Um hook Python
   (`check_agent_spawn.py`) bloqueia spawns que não seguem o formato.
   Resultado: você não recebe mais "agent genérico com nome bonito".

3. **Hooks mecânicos em Python.** 31 hooks rodam no `PreToolUse` e
   `PostToolUse` do Claude Code, incluindo:
   - `check_agent_spawn` — persona+skill obrigatórios
   - `check_bash_safety` — bloqueia `rm -rf /`, `git push --force main`, etc
   - `check_canonical_edit` — edits em `SKILL.md` / `team.md` exigem sentinel assinado
   - `check_plan_edit` — plano não muda sem aprovação
   - `check_read_injection` — detecta prompt injection em arquivos lidos
   - `audit_log` — grava tudo em JSONL

4. **Debate protocol.** Pra task L3+ (3+ módulos, schema, auth),
   `/debate start PLAN-NNN` spawna N especialistas em paralelo
   critiquing o plano. Se 2+ apontam mesmo risco, plano É ajustado
   (não é sugestão).

5. **Audit log.** Tudo em
   `~/.claude/projects/<slug>/audit-log.jsonl`. `audit-query.py` tem
   29 subcomandos (summary, by-skill, debate, tokens, health, etc).

6. **Vetos obrigatórios.** Staff Code Reviewer veta merge sem
   `tsc/mypy/go vet` limpo. Staff Security veta mudanças de auth sem
   revisão. Domínio tem vetos próprios (fintech: Staff Quant veta uso
   de float em cálculo financeiro).

7. **SPEC v1.** Contratos schema-validados em `SPEC/v1/` (state-stores,
   adapters, normalized_envelope, judge-payload, scratchpad, session-graph,
   squad-manifest, skill-index, skill-proposals, etc). SemVer enforced.

8. **9929 testes.** `pytest .claude/hooks/tests .claude/scripts/tests`
   roda em ~30s e tem cobertura ≥86%. Você pode confiar que os hooks
   não vão te trollar.

### Como ele muda seu fluxo

Antes:
```
você escreve prompt elaborado → Claude interpreta como quer →
entrega código → você revisa → pede mudança → Claude ajusta →
você dá merge
```

Depois:
```
você escreve pedido natural → CEO vira plano P0-P4 → você aprova →
CEO spawna especialista(s) com skill/persona/files → especialista
entrega código que já passou no checklist do skill → Code Reviewer
veta ou aprova → você dá merge
```

A sensação é que ficou "mais burocrático", mas o tempo total cai
porque você para de fazer round-trip "cadê o teste?", "cadê a
validação?", "por que isso tá em float?".

### Quando o framework paga
- Task 10min+
- Cross-file ou cross-module
- Domínio sensível (auth, pagamento, saúde, financeiro)
- Projeto com múltiplos devs (a trilha de audit é inestimável)

### Quando NÃO paga
- Typo fix
- Renomear variável local
- Log message tweak
- Experiment de 5 minutos que você vai jogar fora

Pra esses, usa Claude Code direto. Overhead de spawn > benefício.

---

## 3. O que é, o que não é

### É:
- **Um framework portável.** Arquivos que você instala em `.claude/` do
  seu projeto.
- **Opinativo.** Impõe protocolo. Você pode customizar, mas não
  ignorar.
- **Stdlib-only em Python.** Zero dependências externas nos hooks.
- **Claude Code primeiro.** Adapter stub pra Gemini existe, mas
  parity real fica pra v2+.
- **Auditado.** Cada spawn, cada decision, cada veto vira evento em
  JSONL.
- **Governed por ADR.** 171 ADRs documentam toda decisão arquitetural.

### NÃO é:
- **Um produto.** Não tem UI, não tem SaaS, não tem login.
- **Uma biblioteca.** Você não faz `npm install` ou `pip install`.
  Você roda um `install.sh` que copia arquivos.
- **Um controlador remoto.** Você NÃO abre este repo e manda o Claude
  trabalhar em outro repo. Você instala o framework NO outro repo e
  abre o Claude Code lá.
- **Substituto de disciplina.** Se o código-base é caótico, framework
  amplifica o caos. Ele amplifica disciplina boa, não cria disciplina.
- **Independente de modelo.** Os "agentes" são todos o mesmo Claude.
  A diferença é perspectiva forçada + checklist carregado.

### Vocabulário essencial
| Termo | Significado |
|-------|-------------|
| **CEO** | Claude operando sob o protocolo, traduz pedido em plano |
| **Owner** | Você. Única pessoa humana no loop |
| **Skill** | Arquivo `SKILL.md` com checklist pra um domínio (ex: security-and-auth) |
| **Persona** | Um archetype em `team.md` com background + red flags + mantra |
| **Spawn** | Quando o CEO chama um sub-agent com persona + skill + file assignment |
| **Plan** | Arquivo `.claude/plans/PLAN-NNN-slug.md` que rastreia uma feature |
| **Debate** | Spawn paralelo de N agents pra critiquing um plano L3+ |
| **Veto** | Hard block. Staff specialist nega merge até issue ser resolvido |
| **ADR** | Architecture Decision Record em `.claude/adr/` |
| **Squad** | Bundle de domínio (personas + pitfalls + skills). Ex: fintech, edtech, government |
| **Hook** | Script Python que roda antes/depois de tool-call do Claude |

---

## 4. Quando usar, quando não usar

### Use quando:
- Task tem blast radius ≥3 arquivos
- Domínio é sensível (auth, pagamento, financeiro, saúde, compliance)
- Você precisa de trilha de audit pra legal/compliance/post-mortem
- Time tem 2+ devs e você quer coerência de padrão
- Você está montando produto novo e quer boas práticas desde dia 1

### Não use quando:
- É um script throwaway de 1h
- É um POC que você vai jogar fora
- Time é 1 pessoa E você nunca vai mostrar o código pra ninguém
- Você quer LLM pra rubber-duck conversa (use Claude Code direto)

### Kill-switch
Se precisar desligar tudo:
```bash
mv .claude .claude.disabled
```
Claude Code volta a operar como assistente genérico. Pra religar:
```bash
mv .claude.disabled .claude
```

---

## 5. Instalar em projeto NOVO

### Pré-requisitos
- Python 3.9+ (`python3 --version`)
- git
- bash ou zsh
- Claude Code CLI instalado

### Passo 1 — Clonar o framework
```bash
cd ~
git clone https://github.com/Canhada-Labs/ceo-orchestration.git
```

### Passo 2 — Rodar o install no seu projeto
```bash
cd /caminho/do/seu-projeto
bash ~/ceo-orchestration/scripts/install.sh
```

Isso instala o perfil `core` (42 skills universais + 8 frontend).

### Passo 3 — Adicionar perfil de domínio (se aplicável)
```bash
# Fintech (trading, cripto, pagamentos)
bash ~/ceo-orchestration/scripts/install.sh --profile core,fintech

# SaaS com LGPD pesado
bash ~/ceo-orchestration/scripts/install.sh --profile core,lgpd-heavy-saas

# Trading HFT de baixa latência
bash ~/ceo-orchestration/scripts/install.sh --profile core,fintech,trading-hft

# Edtech
bash ~/ceo-orchestration/scripts/install.sh --profile core,edtech

# Governo / setor público
bash ~/ceo-orchestration/scripts/install.sh --profile core,government

# Combinações livres
bash ~/ceo-orchestration/scripts/install.sh --profile core,fintech,lgpd-heavy-saas
```

### Passo 4 — Personalizar `CLAUDE.md`
Abre `CLAUDE.md` na raiz do projeto. Substitui placeholders:
```
{{PROJECT_NAME}}  → nome do seu projeto
{{OWNER_NAME}}    → seu nome
{{PROJECT_PATH}}  → caminho absoluto
```

### Passo 5 — Validar
```bash
# Testes do framework
python3 -m pytest .claude/hooks/tests/ .claude/scripts/tests/ -q
# Esperado: ~800+ passed, 0 failed

# Governance check
bash .claude/scripts/validate-governance.sh
# Esperado: PASS
```

### Passo 6 — Abrir Claude Code e ativar
```bash
cd /caminho/do/seu-projeto
claude
```

Na primeira mensagem:
> "Ativa o protocolo CEO."

O Claude vai ler `CLAUDE.md`, `PROTOCOL.md`, carregar a skill
`ceo-orchestration`, e responder como CEO.

### Passo 7 — Teste com um pedido pequeno
> "Quero entender o que temos no projeto. Faz um resumo."

Se ele responder descrevendo o projeto com referência a arquivos
reais, tá funcionando.

---

## 6. Instalar em projeto EXISTENTE

> **Cenário comum (ex: adopter-1).** Você já tem `.claude/` com suas
> skills custom, seus agents, seu `settings.json`. Rodar `install.sh`
> cru vai sobrescrever coisa sua. Siga este fluxo.

### Passo 1 — Backup INTEIRO
```bash
cd /caminho/do/adopter-1
cp -r .claude .claude.backup-$(date +%Y%m%d-%H%M)
cp CLAUDE.md CLAUDE.md.backup 2>/dev/null || true
cp .github/CODEOWNERS .github/CODEOWNERS.backup 2>/dev/null || true
```

### Passo 2 — Inventário do que você tem
```bash
cd /caminho/do/adopter-1

# Estrutura atual
find .claude -maxdepth 3 -type d | sort
find .claude -maxdepth 3 -name "*.md" | sort

# Skills custom? Agents custom?
ls .claude/skills/ 2>/dev/null
ls .claude/agents/ 2>/dev/null

# Settings atual
cat .claude/settings.json 2>/dev/null
```

Anote em papel:
- Skills custom que VOCÊ criou (não do framework)
- Agents/personas custom
- Permissions ou hooks customizados no `settings.json`
- Arquivo `CLAUDE.md` existente (se houver)

### Passo 3 — Instalar framework fresh em diretório separado
```bash
mkdir -p /tmp/ceo-fresh
cd /tmp/ceo-fresh
bash ~/ceo-orchestration/scripts/install.sh --profile core,fintech
# (ajusta --profile ao seu domínio)
```

Agora você tem uma instalação limpa para comparar.

### Passo 4 — Comparar fresh vs seu projeto
```bash
diff -rq /tmp/ceo-fresh/.claude /caminho/do/adopter-1/.claude
```

Saída típica vai listar 3 categorias:
1. **Só em `/tmp/ceo-fresh`** — framework files que você NÃO tem. Copia pro projeto.
2. **Só em `/caminho/do/adopter-1`** — SEUS arquivos custom. Mantém.
3. **Em ambos (differ)** — conflito. Merge manual.

### Passo 5 — Copiar o que é framework-padrão
```bash
cd /caminho/do/adopter-1

# Hooks (sempre copiar — são do framework)
cp -r /tmp/ceo-fresh/.claude/hooks .claude/

# Scripts (sempre copiar)
cp -r /tmp/ceo-fresh/.claude/scripts .claude/

# Commands (sempre copiar)
cp -r /tmp/ceo-fresh/.claude/commands .claude/

# ADR template
cp -r /tmp/ceo-fresh/.claude/adr .claude/ 2>/dev/null || cp /tmp/ceo-fresh/.claude/adr/README.md .claude/adr/

# SPEC contracts
cp -r /tmp/ceo-fresh/SPEC .

# Protocol
cp /tmp/ceo-fresh/PROTOCOL.md .
```

### Passo 6 — Merge manual do `CLAUDE.md`
Se você já tinha `CLAUDE.md`:
```bash
# Compara lado a lado
diff CLAUDE.md.backup /tmp/ceo-fresh/CLAUDE.md
```

Use o `CLAUDE.md` do framework como base (tem as 3 GATES) e transplante:
- Seção de stack-specific do seu antigo (linguagem, ferramentas)
- Contexto de domínio específico do seu projeto
- CHANGELOG histórico (se houver)

### Passo 7 — Merge manual do `settings.json`
```bash
# Veja hooks que o framework exige
cat /tmp/ceo-fresh/.claude/settings.json

# Seu settings original
cat .claude/settings.json.backup 2>/dev/null || echo "não havia"
```

Copia a seção `"hooks"` do framework pro seu `settings.json`
existente. Mantém seu `permissions` e `mcpServers`. Se houver
conflito de hooks, o framework sempre ganha (hooks do framework são
`fail-open` — não vão te atrapalhar).

### Passo 8 — Migrar SUAS skills custom pro layout do framework
Framework espera esse layout:
```
.claude/skills/
├── core/<skill>/SKILL.md            # universais
├── frontend/<skill>/SKILL.md        # universais frontend
└── domains/<seu-dominio>/           # squad do seu domínio
    ├── team-personas.md
    ├── pitfalls.yaml
    ├── task-chains.yaml
    └── skills/
        └── <skill-custom>/SKILL.md
```

Se sua skill custom estava em `.claude/skills/reconciliation-logic.md`
(achatado, sem subdir), reorganiza:

```bash
mkdir -p .claude/skills/domains/ledger/skills/reconciliation-logic
mv .claude/skills/reconciliation-logic.md \
   .claude/skills/domains/ledger/skills/reconciliation-logic/SKILL.md
```

Garante que `SKILL.md` tem frontmatter YAML obrigatório:
```yaml
---
name: Reconciliation Logic
description: Reconciliação de débito/crédito em double-entry ledger com edge cases BR (NFe, PIX delay, estorno).
trigger: Quando a task envolve reconciliação contábil ou fechamento de período.
---
```

### Passo 9 — Criar o squad do seu domínio (contrato ADR-009)
Para cada domínio custom (ex: `ledger`), os 3 arquivos são
OBRIGATÓRIOS senão o validator falha:

**`.claude/skills/domains/ledger/team-personas.md`** — personas
específicas (ex: "Staff Accounting Engineer com VETO em double-entry").

**`.claude/skills/domains/ledger/pitfalls.yaml`** — mínimo 12
pitfalls conhecidos do domínio:
```yaml
- id: ledger-001
  title: "Double-entry sem balanceamento atomico"
  severity: critical
  pattern: "INSERT INTO ledger_entries sem transação envolvendo débito E crédito"
  mitigation: "Usar tx explícita; trigger de validação no insert"
- id: ledger-002
  ...
```

**`.claude/skills/domains/ledger/task-chains.yaml`** — mínimo 2
workflows:
```yaml
- name: close-period
  steps:
    - lock-period-entries
    - reconcile-balances
    - generate-statements
    - freeze-period
- name: handle-refund
  ...
```

### Passo 10 — Atalho: `/architect` gera squad automaticamente
Se você ainda não tem os 3 arquivos, o framework pode gerar o
scaffolding pra você:

Dentro do Claude Code:
```
/architect "adopter-1: double-entry accounting with BR tax semantics, NFe integration, PIX reconciliation, LGPD-compliant audit trail"
```

Ele vai produzir os 3 arquivos + skills sugeridas. Revisa, ajusta
adicionando suas skills custom, valida.

### Passo 11 — Regenerar inventory de skills
```bash
cd /caminho/do/adopter-1
bash .claude/scripts/generate-skill-inventory.sh > /tmp/new-inv.md

# Patcha o arquivo da skill ceo-orchestration entre os marcadores:
# <!-- BEGIN AUTO-GENERATED SKILL INVENTORY -->
# ...
# <!-- END AUTO-GENERATED SKILL INVENTORY -->
```

Há um script helper pra isso:
```bash
python3 .claude/scripts/patch-skill-inventory.py /tmp/new-inv.md \
    .claude/skills/core/ceo-orchestration/SKILL.md
```

### Passo 12 — Validar o squad
```bash
python3 .claude/scripts/validate-squad-contract.py \
    --squad .claude/skills/domains/ledger/
# Esperado: exit 0
```

### Passo 13 — Testes + governance
```bash
python3 -m pytest .claude/hooks/tests/ .claude/scripts/tests/ -q
# Esperado: todos passam

bash .claude/scripts/validate-governance.sh
# Esperado: PASS
```

### Passo 14 — Atualizar `.github/CODEOWNERS`
Se você tinha CODEOWNERS, adiciona linhas do framework:
```
/.claude/skills/core/         @seu-handle
/.claude/adr/                 @seu-handle
/.claude/plans/PLAN-*.md      @seu-handle
/PROTOCOL.md                  @seu-handle
/CLAUDE.md                    @seu-handle
/SPEC/                        @seu-handle
```

### Passo 15 — Commit incremental
Não commite tudo de uma vez. Separa:
```bash
git add .claude/hooks .claude/scripts .claude/commands
git commit -m "chore(claude): install ceo-orchestration framework — infra (hooks+scripts+commands)"

git add .claude/skills/core .claude/skills/frontend SPEC/ PROTOCOL.md
git commit -m "chore(claude): install ceo-orchestration framework — skills + contracts"

git add .claude/skills/domains/ledger
git commit -m "feat(squad): migrate custom skills into ledger squad"

git add CLAUDE.md .claude/settings.json .claude/team.md
git commit -m "chore(claude): wire CLAUDE.md + team + hooks registration"
```

### Passo 16 — Teste com Claude Code
```bash
cd /caminho/do/adopter-1
claude
```
Mensagem 1:
> "Ativa o protocolo CEO."

Mensagem 2:
> "Lista as skills instaladas e descreve o squad ledger."

Se ele listar suas skills custom corretamente, migração foi bem.

### Se der errado — rollback
```bash
cd /caminho/do/adopter-1
rm -rf .claude
mv .claude.backup-YYYYMMDD-HHMM .claude
mv CLAUDE.md.backup CLAUDE.md 2>/dev/null || true
```

---

## 7. Primeiros 10 minutos pós-install

Checklist pra validar que tudo subiu:

```bash
# 1. Testes verdes (~30s)
python3 -m pytest .claude/hooks/tests/ .claude/scripts/tests/ -q

# 2. Governance PASS
bash .claude/scripts/validate-governance.sh

# 3. Inventário de skills consistente
python3 .claude/scripts/registry.py list-skills | wc -l
# Esperado: 19+ (core) ou mais dependendo do profile

# 4. CLAUDE.md personalizado (sem {{PLACEHOLDERS}})
grep -c "{{" CLAUDE.md
# Esperado: 0

# 5. Hooks registrados em settings.json
python3 -c "import json; s=json.load(open('.claude/settings.json')); print(list(s.get('hooks',{}).keys()))"
# Esperado: ['PreToolUse', 'PostToolUse'] ou similar
```

Dentro do Claude Code:
```
/status
```
Esse comando tem que responder com snapshot do projeto. Se responder,
framework tá live.

---

## 8. Uso diário — o loop básico

### Toda sessão começa igual
```
/status
```
Vê: último plano ativo, últimos spawns, warnings de CI, health do
framework.

### Pedindo algo
Você NÃO escreve prompt elaborado. Escreve em português natural:

> "Adiciona rate limit de 100req/min no /api/orders"

> "Revisa o checkout antes de eu subir pra produção"

> "Quero redesenhar a página de pricing"

O CEO:
1. Lê o pedido
2. Classifica L1/L2/L3 (quantos módulos mexidos)
3. Se L1/L2 → plano leve, spawna especialista, entrega
4. Se L3+ → propõe plano, roda debate (`/debate start`), ajusta,
   então executa
5. Retorna com output + diff pra você revisar

### Revisando output
Aprova se tá bom. Rejeita com motivo se não. O motivo vira lesson
(`/lesson-review`) — o framework aprende.

### Commit / deploy
Framework **nunca commita sem você pedir**. Quando você pedir:
```
commita isso
```
O CEO roda checklist: testes passaram? lint passou? security review?
Só depois faz `git commit`.

---

## 9. Comandos que você vai usar

### Todo dia
| Comando | O que faz |
|---------|-----------|
| `/status` | Snapshot do projeto — primeiro comando de toda sessão |
| `/spawn "Security Engineer" <task>` | Quando você sabe quem quer |
| `/veto-check <arquivo>` | Checklist formal de code review + security |
| `/pitfall <dominio>` | Antes de feature nova em domínio crítico |

### Toda semana
| Comando | O que faz |
|---------|-----------|
| `/debate start PLAN-NNN` | Pra decisões arquiteturais (schema, migração, nova integração) |
| `/audit-page <url>` | Review de front-end em 16 dimensões |
| `/lesson-review` | Olha o que o sistema aprendeu sobre seus erros/acertos |

### Ocasional
| Comando | O que faz |
|---------|-----------|
| `/agent budget PLAN-NNN` | Quanto cada plano consumiu de token/custo |
| `/architect "<novo domínio>"` | Gera squad (personas + skills + pitfalls) pra domínio novo |
| `/resume PLAN-NNN` | Retoma plano de sessão anterior |
| `/memory-scratchpad` | Memória compartilhada entre agentes no mesmo plano |
| `/skill-review` | Aprovar/rejeitar patches propostos pras skills |
| `/squad-install <tarball>` | Importar squad de terceiro (marketplace) |

### Scripts de shell
```bash
# Query do audit log
python3 .claude/scripts/audit-query.py summary
python3 .claude/scripts/audit-query.py by-skill
python3 .claude/scripts/audit-query.py health

# Dashboard local (SSE em http://localhost:7842)
python3 .claude/scripts/audit-dashboard.py

# Validar governance (roda no CI também)
bash .claude/scripts/validate-governance.sh

# Verificar staleness de docs/plans
python3 .claude/scripts/check-staleness.py
```

---

## 10. Como explicar pro time

### Elevator pitch (30s)
> "O Claude Code sozinho é um freelancer genial mas generalista. Esse
> framework transforma ele num time: um CEO que recebe o pedido, VPs
> que decidem estratégia, especialistas que executam com checklist de
> domínio, e vetos obrigatórios em segurança e code review. Tudo
> rastreável em audit log."

### Pra dev sênior
> "Mesmo Claude, mas cada spawn carrega persona + skill + file
> assignment + checklists do domínio antes de escrever a primeira
> linha. Hooks em Python bloqueiam merge sem review, edit em SKILL.md
> sem sentinel assinado, bash perigoso. Tudo em audit-log.jsonl pra
> você entender DEPOIS por que ele tomou cada decisão. Reduz
> alucinação porque força o modelo a operar dentro de um checklist
> específico em vez de improvisar."

### Pra dev júnior
> "Pensa no Claude como um time de senior engineers. Você não precisa
> saber qual deles chamar — pede em linguagem natural e o 'CEO'
> distribui. Se você pedir 'adiciona um endpoint de login', o CEO
> automaticamente chama o Security Engineer pra revisar (porque login
> é veto-protected). Você vai ver OUTPUT de especialista mesmo sem
> saber pedir pra especialista. É um jeito de aprender padrões de
> produção enquanto produz."

### Pra PM / não-dev
> "Antes: você escrevia a feature em Notion, passava pro dev, virava
> bug em produção. Agora: você escreve no chat, o CEO transforma em
> plano (com checkpoints que você aprova), especialistas implementam,
> um 'quality gate' bloqueia automaticamente se tiver problema de
> segurança ou ausência de teste. Você vê o progresso em `/status`
> sem precisar perguntar 'e aí?' toda hora."

### Regras de ouro pro time (cola no Slack)
1. Sempre começa a sessão com `/status`
2. Pede em natural, não em jargão de agente
3. Quando o hook bloqueia, LEIA a mensagem — ele sabe de algo que
   você não sabe (lição de merda já vivida por alguém)
4. Se o CEO pergunta, responde — ambiguidade vira bug
5. Não commita sem permissão explícita sua
6. Antes de feature sensível (auth/pagamento/PII), roda `/pitfall`
7. Quando rejeita output, **explica o porquê** — vira lesson

---

## 11. Troubleshooting

### "Hook bloqueou meu comando"
Leia a mensagem do hook. 95% das vezes ele tem razão. Exemplos:

- `check_bash_safety bloqueou rm -rf` → mova pra `/tmp/` em vez de
  deletar; se for legítimo, use Bash com `dangerouslyDisableSandbox: true`
  após confirmar que não vai perder dado.
- `check_agent_spawn bloqueou spawn sem SKILL CONTENT` → você (ou o
  CEO) esqueceu de montar o prompt com as 3 seções. Use
  `.claude/scripts/inject-agent-context.sh <Agent> <task>` pra gerar.
- `check_canonical_edit bloqueou edit em SKILL.md` → SKILL.md precisa
  de sentinel assinado. Caminho: abra um plano em `.claude/plans/`,
  pede pro Architect revisar, assina e aplica.

### "CEO spawnou agent e ele falhou"
3 causas comuns:
1. **Skill errada carregada** — CEO escolheu skill X quando a task
   precisava da Y. Solução: você diz explicitamente qual skill.
2. **Contexto incompleto** — agent não tinha acesso aos arquivos
   relevantes. Solução: adiciona referência explícita no pedido.
3. **Task mal especificada** — agent entregou 80% porque pedido
   tinha ambiguidade. Solução: acceptance criteria mais claro.

Em todos os casos: vira **strike** pro agent. 3 strikes = persona é
reescrita.

### "Tests do framework estão falhando"
```bash
python3 -m pytest .claude/hooks/tests/ .claude/scripts/tests/ -v
```
Se falhar:
- Python < 3.9? Framework exige 3.9+.
- `_lib` imports quebrados? Verifica se `.claude/hooks/_lib/` veio
  no install.
- Fixture faltando? Pode ser merge incompleto em projeto existente —
  refaz passo 5 do install.

### "Audit log vazio"
```bash
ls -la ~/.claude/projects/*/audit-log.jsonl
```
Se não existe, hook `audit_log.py` não está registrado. Verifica
`.claude/settings.json` seção `hooks.PostToolUse`.

### "Tô pagando muito de token"
```bash
python3 .claude/scripts/audit-query.py tokens
```
Geralmente é:
- Debate L3+ desnecessário em task pequena (ajuste blast radius)
- Agent regenerando arquivos inteiros em vez de Edit pontual
  (lesson-review pra corrigir)
- Prompts muito longos por skill inflada (revisa o SKILL.md)

### "Quero desligar"
```bash
mv .claude .claude.disabled
# Ou, pra apenas uma sessão: CEO_SOTA_DISABLE=1 claude
```

### Top docs de referência
- `docs/TROUBLESHOOTING.pt-BR.md` — troubleshooting detalhado
- `docs/FOR-EMPLOYEES.pt-BR.md` — se você é funcionário do Owner
- `docs/GLOSSARY.pt-BR.md` — vocabulário completo
- `PROTOCOL.md` — contrato de governance

---

## 12. Limitações honestas

### O que NÃO é verdade
- **"Multi-agent com expertise real"** — são todos o mesmo LLM. O
  que muda é contexto carregado e checklist enforçado. Um agent com
  skill `financial-correctness` não sabe MAIS de decimal que outro
  agent — ele só é forçado a VERIFICAR sistematicamente. Sem a skill,
  nenhum verificaria.
- **"Review independente"** — agent revisor e agent revisado
  compartilham training data. Viés idêntico. O que funciona é
  perspectiva forçada (security vs performance vs correctness)
  encontrar coisas diferentes, não "independência".
- **"Zero alucinação"** — framework reduz por forçar checklist, mas
  Claude ainda inventa nome de função às vezes. Sempre verifica
  output contra código real (grep / read / tests).

### O que SÓ funciona com disciplina humana
- Code base tem que ser razoavelmente organizado
- Você precisa revisar output, não aceitar cegamente
- `/lesson-review` semanalmente se você quer que o sistema melhore
- ADRs escritos quando decisão é L3+ (CEO lembra, mas você precisa
  aprovar)

### Quando NÃO compensa
- Projeto solo throwaway
- Protótipo de 1 semana
- Time que não quer processo (framework vai frustrar)
- Owner que não lê plano antes de aprovar (aí o framework vira
  teatro)

### Mitigações que o framework tenta
1. Skills são checklists verificáveis, não vibes
2. Output é verificado contra código (grep/read), não opinion
3. Strikes baseados em FATO, não desacordo
4. Owner é a única checagem verdadeiramente independente

---

## 13. Referências

### Docs neste repo
- `README.md` — intro bilíngue (EN + PT-BR)
- `PROTOCOL.md` — contrato de governance (leia uma vez)
- `INSTALL.md` — alternativa mais curta à seção 5 deste guia
- `docs/QUICKSTART.pt-BR.md` — 10min onboarding
- `docs/FOR-EMPLOYEES.pt-BR.md` — para funcionários de time que adotou
- `docs/GLOSSARY.pt-BR.md` — vocabulário completo
- `docs/TROUBLESHOOTING.pt-BR.md` — problemas comuns
- `docs/ROADMAP.md` — futuro do framework
- `docs/BRANCH-PROTECTION.md` — setup de GitHub branch protection
- `docs/audit-dashboard.md` — como rodar o dashboard local
- `docs/provider-pricing.md` — preços dos LLMs pra `/agent budget`

### Arquivos-chave em `.claude/`
- `.claude/team.md` — roster backend + ROUTING TABLE + SKILL MAP
- `.claude/frontend-team.md` — roster frontend
- `.claude/pitfalls-catalog.yaml` — pitfalls universais
- `.claude/task-chains.yaml` — 6 workflows universais
- `.claude/adr/` — 171 Architecture Decision Records
- `.claude/plans/` — planos ativos + arquivo
- `.claude/skills/core/` — 42 skills universais
- `.claude/skills/frontend/` — 8 skills frontend
- `.claude/skills/domains/<squad>/` — squads instalados

### Contratos em `SPEC/v1/`
- `state-stores.schema.md` — backend de estado unificado
- `adapters.schema.md` — adapters LLM (Claude, Gemini, OpenAI, local)
- `normalized_envelope.schema.md` — envelope canônico de request
- `judge-payload.schema.md` — payload do LLM-as-judge
- `scratchpad.schema.md` — memória compartilhada
- `session-graph.schema.md` — grafo derivado de sessões
- `squad-manifest.schema.md` — manifest de squad do marketplace
- `skill-index.schema.md` — índice de skills
- `skill-proposals.schema.md` — patches propostos pra skills

### GitHub
- Repo: https://github.com/Canhada-Labs/ceo-orchestration
- Issues: https://github.com/Canhada-Labs/ceo-orchestration/issues
- Releases: https://github.com/Canhada-Labs/ceo-orchestration/releases

---

## Último conselho

Este framework **amplifica disciplina, não cria disciplina**. Se seu
time já tem boas práticas (code review, ADR, trilha de audit), o
framework vira força multiplicadora. Se seu time é caótico, instalar
o framework vai ser doloroso nas primeiras 2 semanas — vale a pena
mesmo assim, porque o framework força a caminhar pra disciplina por
atrito mecânico (hooks bloqueiam, CEO recusa, Code Reviewer veta).

Quando em dúvida, leia `PROTOCOL.md` — ele é curto, é o contrato, e
resolve 80% das dúvidas de uso.

Boa sorte.
