# QUICKSTART — ceo-orchestration em 10 minutos

> **EN (fonte canônica):** [QUICKSTART.md](QUICKSTART.md).
>
> Guia para quem nunca usou o framework. Se você é funcionário do
> projeto, leia também `FOR-EMPLOYEES.pt-BR.md`. Se algo quebrar, veja
> `TROUBLESHOOTING.pt-BR.md`.

## O que você vai ter no final

Depois de seguir este guia, quando você abrir o Claude Code dentro do
seu repositório:

- O Claude se apresenta como **CEO** do projeto (não mais um assistente
  genérico)
- Ele **planeja** antes de agir — você sempre sabe o que ele vai fazer
- Ele **spawna especialistas** (VP de Engenharia, Staff Security, etc)
  com manuais específicos em vez de responder "do jeito dele"
- **Hooks mecânicos** impedem erros comuns (commits destrutivos,
  spawns sem skill, edits em arquivos canônicos)
- Tudo fica **auditado** num log que você pode consultar depois

## Pré-requisitos

- `git` instalado
- `python3 >= 3.9` (já vem no macOS; em Linux: `sudo apt install python3`)
- `bash` ou `zsh` (padrão em Mac/Linux)
- Claude Code CLI instalado (https://claude.com/claude-code)

## Passo 1 — Instalar o framework no seu projeto

Abra terminal na raiz do seu projeto (o que você quer que o CEO ajude
a desenvolver).

### Caminho recomendado — clonar numa tag fixa + `install.sh`

Este é o caminho canônico, igual ao `README.md` da raiz. Clonar numa
tag fixa já te dá integridade de graça — o `git` verifica a integridade
do pack ao clonar — sem precisar mexer com `shasum` na mão:

```bash
cd /tmp
git clone --branch v1.0.0 --depth 1 https://github.com/Canhada-Labs/ceo-orchestration.git
cd /caminho/do/seu/projeto
bash /tmp/ceo-orchestration/scripts/install.sh
```

### Caminho alternativo — download + SHA256 pin (dois passos)

Se você prefere não usar `npm`, **nunca** faça `curl … | bash` direto
em URL remota. O anti-pattern `curl | bash` expõe você a um MITM /
repo-tampering silencioso: você executa o que aparecer, sem
verificação de integridade. Em vez disso, baixe na tag fixa +
verifique o SHA256 publicado em release-notes:

```bash
# Defina a TAG que quer instalar (não use `main` — é alvo móvel):
TAG=v1.0.0

# 1) Baixar o instalador na tag fixa:
curl -fsSL -o /tmp/ceo-install.sh \
  "https://raw.githubusercontent.com/Canhada-Labs/ceo-orchestration/${TAG}/scripts/install.sh"

# 2) Baixar o SHA256 oficial publicado como asset da release:
curl -fsSL -o /tmp/ceo-install.sh.sha256 \
  "https://github.com/Canhada-Labs/ceo-orchestration/releases/download/${TAG}/install.sh.sha256"

# 3) Verificar integridade (sha256 do asset bate com o script baixado):
( cd /tmp && shasum -a 256 -c ceo-install.sh.sha256 ) \
  || { echo "Integrity verification FAILED — aborting"; exit 1; }

# 4) (PLAN-045 P0-15) Verificação adicional: o próprio script traz um
#     trailer `# CEO-INSTALL-SHA256:` populado no tag-cut. Execução
#     com arquivo adulterado já fail-CLOSED internamente rc=5.
bash /tmp/ceo-install.sh [--target /caminho/do/seu/projeto]
```

> **Nota sobre o SHA:** o workflow `.github/workflows/release.yml`
> publica o sha256 exato de `scripts/install.sh` como asset da release
> (`install.sh.sha256`). O comando em (2) baixa este asset
> automaticamente — não precisa copiar hex manualmente das release
> notes. Sempre use uma tag fixa; `main` é alvo móvel.

### npm install

> **Instalação via npm.** O pacote bootstrap é publicado no npm com
> SLSA 3 provenance; o caminho de clone acima também permanece suportado.

O bootstrap instala pelo npm com verificação
automática de integridade (registry npm + SLSA provenance L3):

```bash
npm install -g ceo-orchestration
cd /caminho/do/seu/projeto
ceo-orchestration
```

O pacote publicável é o nome não-escopado `ceo-orchestration` (o `bin` que ele
instala é `ceo-orchestration`). É publicado com `--provenance` (SLSA 3) e o
`npm` verifica o tarball SHA antes de extrair. Veja
`docs/install-verification.md` e `.github/workflows/npm-publish.yml`.

O script instala (sem mexer em nada fora de `.claude/`, `docs/`, e
`MEMORY.md`):

- `.claude/skills/` — biblioteca de 151 skills (manuais de especialistas)
- `.claude/hooks/` — 53 hooks Python que impedem spawns sem persona/skill
- `.claude/plans/` — onde os planos de trabalho ficam
- `.claude/team.md` + `.claude/frontend-team.md` — time (backend + frontend)
- `CLAUDE.md` — contexto mestre que o Claude Code lê em toda sessão
- `PROTOCOL.md` — regras de engajamento

## Passo 2 — Personalizar o `CLAUDE.md` do seu projeto

Abre `CLAUDE.md` na raiz. Procura e substitui:

- `{{PROJECT_NAME}}` — nome do seu projeto (ex: "your-app")
- `{{OWNER_NAME}}` — seu nome (ex: "Canhada Labs")
- `{{PROJECT_PATH}}` — caminho absoluto (ex: `/Users/you/your-app`)

Se seu projeto tem stack específico, edita a seção §CODEBASE SNAPSHOT
do `.claude/frontend-team.md` (se houver frontend).

## Passo 3 — Abrir Claude Code

```bash
cd /caminho/do/seu/projeto
claude
```

Na primeira interação, digite:

> "Ativa o protocolo CEO."

O Claude vai:
1. Ler `CLAUDE.md`, `PROTOCOL.md`, e a memória
2. Invocar a skill `ceo-orchestration`
3. Ler o roster em `.claude/team.md`
4. Responder como CEO do seu projeto

## Passo 4 — Seu primeiro pedido

Tenta algo concreto mas pequeno. Exemplo:

> "Quero adicionar um rate limit de 100 req/min no endpoint /api/users.
> Monta um plano."

O CEO vai:
1. Pedir confirmação do escopo
2. Decidir quais especialistas precisam opinar
3. Escrever um plano P0-P4 (Product lens → Planning → Implementation
   → Quality gate → Deploy)
4. **Não vai escrever código ainda** — espera você aprovar o plano

Quando aprovar:
5. Spawna o especialista certo (provavelmente Staff Backend Engineer
   com skill `public-api-design`)
6. Ele implementa
7. Code Reviewer revisa
8. Você aprova → merge

## Passo 5 — Consultar o audit log

O framework loga tudo em:
```
~/.claude/projects/<seu-projeto>/audit-log.jsonl
```

Quer ver o que aconteceu? Rode:

```bash
python3 .claude/scripts/audit-query.py summary
```

Sub-comandos úteis:

- `summary` — resumão dos últimos 100 eventos
- `by-skill` — quantas spawns por skill
- `debate` — histórico de debates
- `tokens` — quantos tokens foram gastos
- `health` — framework tá saudável? (PASS / WARN / FAIL)

## O que NÃO fazer

❌ **Não peça "escreve o código X" sem plano.** O CEO vai recusar e
pedir pra fazer o plano primeiro. Isso é proposital.

❌ **Não edite `.claude/team.md` ou `.claude/skills/core/*/SKILL.md`
sem passar pelo Architect.** Há um hook (`check_canonical_edit`) que
bloqueia edits nesses arquivos canônicos.

❌ **Não rode `rm -rf` no terminal do Claude Code.** O hook
`check_bash_safety` bloqueia comandos destrutivos.

❌ **Não copie números de docs antigas sem verificar no código.** O CEO
vai te corrigir (e é anti-pattern listado em PROTOCOL.md §Anti-patterns).

## O que fazer quando dá errado

Ver `TROUBLESHOOTING.pt-BR.md`. Top 3 comuns:

- **"Hook bloqueou meu comando"** — leia a razão no terminal, ajuste.
  Ex: `rm -rf` → use `mv` pra `/tmp/` primeiro.
- **"CEO spawnou agente e ele falhou"** — é uma das 3 causas
  (falta de skill, falta de profile, contexto incompleto). Ver
  TROUBLESHOOTING.
- **"Quero desligar tudo"** — `mv .claude .claude.disabled` e o Claude
  Code volta ao modo genérico.

## Próximos passos

- Leia `PROTOCOL.md` — é curto e explica as 3 gates
- Leia `.claude/team.md` — veja o roster de archetipos
- Leia `docs/FOR-EMPLOYEES.pt-BR.md` se você é funcionário de alguém que já
  adotou o framework

## Dúvidas frequentes

**P: Preciso pagar alguma coisa?**
R: Não. O framework é só arquivos. Você paga pelo Claude Code normal.

**P: Vai ficar mais lento?**
R: Hook latency < 40ms por invocação. Imperceptível.

**P: Posso usar com outra IA (Gemini, Cursor)?**
R: Tem um stub Gemini em `.claude/hooks/_lib/adapters/gemini.py` mas
não é parity completa. V1.0 é **Claude Code only**.

**P: Como atualizo pra uma versão nova do framework?**
R: `bash /caminho/ceo-orchestration/scripts/upgrade.sh` — respeita
customizações locais de `CLAUDE.md` e `settings.json`.
