# FOR-EMPLOYEES — Você é novo no projeto

> **EN (fonte canônica):** [FOR-EMPLOYEES.md](FOR-EMPLOYEES.md).
>
> Dirigido a funcionários/colaboradores que vão usar o Claude Code em
> projetos onde o Owner já instalou o framework ceo-orchestration.
> Se você é o Owner configurando pela primeira vez, leia
> `QUICKSTART.pt-BR.md`.

## O que muda para você

Quando você abre Claude Code num projeto com `ceo-orchestration`
instalado, o Claude **NÃO é mais o Claude genérico**. Ele vira o
**CEO do projeto**. Isso muda como ele responde suas perguntas:

**Antes:**
> Você: "Adiciona um campo `created_at` na tabela users"
> Claude: _edita o arquivo, faz migration, commita_

**Agora:**
> Você: "Adiciona um campo `created_at` na tabela users"
> Claude (como CEO): "Entendi. Isso afeta a tabela + migration + RLS.
> Monto um plano primeiro. Phase 0: qual o formato de timestamp
> esperado? Phase 1: Principal Data Engineer revisa o schema. Phase 2:
> implementação. Phase 3: testes. Aprovado?"

Parece burocrático. **É proposital.** Existem 3 razões:

1. **Evita retrabalho** — pegar a intenção errada no começo custa
   menos que refazer no final
2. **Especialistas certos na jogada** — mudança de schema sem o Data
   Engineer revisar vira bug em produção
3. **Audit trail** — a empresa precisa saber o que cada pessoa +
   cada IA mexeu (LGPD, auditoria, postmortem)

## Regras de engajamento (PROTOCOL.md em linguagem leiga)

### 1. Sempre peça plano antes de código

"Faz um plano pra X" > "Escreve código pra X"

Se você pedir direto pra escrever, o CEO vai responder "preciso
planejar primeiro". Não é teimosia, é protocolo.

### 2. L1-L2 não precisa de debate, L3+ precisa

- **L1** = fix de 1 arquivo, typo, log message → CEO faz direto
- **L2** = 2-3 arquivos, feature pequena → CEO planeja + executa
- **L3** = 3+ módulos, mudança de schema, auth, financial → CEO
  **debate obrigatório** com 2-3 especialistas antes

Se sua tarefa for L3+ e você pedir "vai logo", o CEO recusa e chama
o `/debate`. Respeita.

### 3. VETOs são obrigatórios, não sugestão

Existem 2 vetadores universais:
- **Staff Code Reviewer** — qualquer merge
- **Staff Security Engineer** — qualquer mudança em auth/token/input

Se o Security Engineer diz "não pode", **não faça**. Isso não é
opinião — é gate mecânico. Se você insistir, o CEO escalonar pro Owner.

### 4. Não edite arquivos canônicos

Esses arquivos têm hook mecânico bloqueando edit direto:

- `.claude/team.md`
- `.claude/frontend-team.md`
- `.claude/pitfalls-catalog.yaml`
- `.claude/skills/*/SKILL.md`

Se precisar mudar um desses, use `/architect` — o Agent Architect
meta-cria a mudança passando pelo processo correto (com sentinel
assinado pelo Owner).

### 5. Comandos destrutivos são bloqueados

Hook `check_bash_safety` bloqueia:
- `rm -rf <qualquer coisa>`
- `git reset --hard`
- `git push --force` (aceita `--force-with-lease`)

Use alternativas:
- `rm -rf /tmp/foo` → `mv /tmp/foo /tmp/foo.trash-$(date +%s)`
- `git reset --hard` → `git stash` + decide depois
- `git push --force` → `git push --force-with-lease`

## Comandos úteis (slash commands)

Digite no chat do Claude Code:

### `/spawn "Nome do Agente" <tarefa>`
Spawna um especialista específico. Exemplo:
```
/spawn "Principal Performance Engineer" avalia latência do endpoint /api/search
```

O CEO automaticamente carrega a persona + skill + file assignment.

### `/debate start PLAN-NNN "proposta"`
Inicia debate multi-especialista sobre um plano. Exemplo:
```
/debate start PLAN-042 "Mudar de PostgreSQL para CockroachDB"
```

3 agentes (VP Eng + Staff Security + DevOps por padrão) critica cada
um do ângulo dele. O CEO sintetiza consensus.

### `/architect "<brief>"`
Meta-comando: pede pro Agent Architect montar um squad novo para um
domínio específico. Ex: "crie squad para edtech compliance".

### `/status` (novo em v1.0)
Overview rápido:
- Qual plano em execução
- Últimas 5 spawns
- Lições aprendidas últimas 24h
- Warnings do audit log

### `/audit-page <url>`
Audita uma página frontend em 16 dimensões de UX/accessibilidade.

## O que fazer quando você não sabe

1. **Leia o `CLAUDE.md`** — é o contexto mestre do projeto
2. **Digite `/status`** — veja onde o projeto está
3. **Pergunte ao CEO** — "Ativa o protocolo CEO. Preciso fazer X.
   Quais especialistas devem participar?"
4. **Consulta o audit log** — `python3 .claude/scripts/audit-query.py summary`

## Privacidade e segurança

- Todos os logs ficam em `~/.claude/projects/<seu-projeto>/audit-log.jsonl`
  — fora do repo, no seu home
- Prompts que foram enviados para o Claude Code ficam lá (mas
  redactados — secrets e PII são removidos antes do log)
- Nada é enviado para o ceo-orchestration maintainer nem pra
  ninguém externo
- Owner do projeto consegue consultar com `audit-query.py`

## Quando pedir ajuda pro Owner

- Hook está bloqueando e você não entende por que
- CEO recusou uma tarefa e você discorda
- Quer adicionar skill/squad novo que não existe
- Veto foi acionado e você acha que foi erro

## Flags que NÃO devem ser mexidas

Algumas variáveis de ambiente controlam modos experimentais do
framework. **Não set elas na sua sessão.** Se algum hook estiver
bloqueando e você suspeitar dessas flags, chama o Owner.

| Flag                        | Default | Quem set | Por quê             |
|-----------------------------|---------|----------|---------------------|
| `CEO_CONFIDENCE_ENFORCE`    | 0       | Owner    | Ativa blocking mode do confidence gate (Sprint 9). Advisory por padrão. |
| `CEO_CONFIDENCE_BYPASS`     | 0       | Owner    | Escape hatch quando enforce wedga uma sessão legítima. |
| `CEO_PRUNE_EXECUTE`         | 0       | Owner    | Habilita `--execute` de prune-lessons (Sprint 8). |
| `CEO_CONFIDENCE_MAX_CLAIMS` | 200     | Owner    | Override do cap de CLAIM tokens por output. |
| `CEO_ARCHITECT_ACTIVE`      | (auto)  | /architect | Setada pelo slash-command. Não mexer. |

Se você setou uma dessas por engano, roda `unset <VAR>` na shell ou
reabre o terminal.

## Anti-patterns (o que NÃO fazer)

❌ "Ignora o protocolo, só escreve o código"
→ CEO vai recusar. Protocolo não é opcional.

❌ Copiar número de doc antiga sem conferir no código
→ O CEO corrige e você leva uma "strike" (3 strikes = persona
reescrita, nome novo)

❌ Spawnar agente e não validar o output
→ CEO verifica com grep/read. Se agente inventou arquivo que não
existe, strike.

❌ "Faço rápido sem teste"
→ Hook + Staff Code Reviewer vetam merge sem teste. Não adianta.

❌ Commitar sem o Owner pedir
→ Anti-pattern #7 do PROTOCOL.md. Só commita quando o Owner
explicitamente falar "commita".

## Resumo em 1 parágrafo

Você vai interagir com um Claude que se comporta como **CEO**: pede
plano antes de agir, chama especialistas, respeita vetos, loga tudo,
e ocasionalmente te bloqueia quando você tá sendo descuidado. Aceita
que é proposital — o framework existe pra evitar os erros que você
cometeria sem ele. Em caso de dúvida, `/status` ou leia
`TROUBLESHOOTING.pt-BR.md`.
