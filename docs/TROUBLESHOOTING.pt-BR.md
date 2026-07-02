# TROUBLESHOOTING — Problemas comuns e soluções

> **EN (fonte canônica):** [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## "O hook bloqueou meu comando"

### Bash destrutivo bloqueado

**Mensagem:** `BLOCKED: 'rm' with -r and -f is destructive`

**Fix:** não use `rm -rf`. Opções:
```bash
# Em vez de: rm -rf foo/
mv foo/ /tmp/foo.trash-$(date +%s)

# Se precisa APAGAR mesmo:
# Roda no seu terminal (fora do Claude Code), não via CEO.
```

Lista completa de comandos bloqueados em
`.claude/hooks/check_bash_safety.py`.

### Edit em arquivo canônico bloqueado

**Mensagem:** `CANONICAL-EDIT-BLOCKED: '<path>' is a canonical
governance path`

**Fix:** use `/architect`:
```
/architect "atualiza o skill security-and-auth pra incluir X"
```

Ou, se for mudança estrutural do framework, trabalhe via PLAN-NNN
com sentinel assinado pelo Owner.

### Agent spawn bloqueado

**Mensagem:** `spawn missing ## SKILL CONTENT section`

**Causa:** você (ou o CEO) tentou invocar o Agent tool sem carregar
skill. Isso é o hook mais importante — ele impede "agente cosmético"
(só nome, sem manual).

**Fix:**
- Use `/spawn` em vez de Agent tool manual
- Ou use `bash .claude/scripts/inject-agent-context.sh "<nome>" "<task>"`

### Transição de ciclo de vida de plano bloqueada

**Mensagem:** `PLAN-LIFECYCLE: ...` (ex.: falta `reviewed_at`, falta
`completed_at`, ou um abandono sem motivo).

**Causa:** `check_plan_edit.py` impõe a máquina de estados do plano
(draft → reviewed → executing → done, mais `abandoned`). Um flip de
status que pula um timestamp obrigatório ou salta um estado é bloqueado.

**Fix:** adicione o campo exigido pela transição que você quer:
- `draft → reviewed` precisa de um stamp `reviewed_at:`
- `executing → done` precisa de um stamp `completed_at:`
- `→ abandoned` precisa de um motivo de abandono
Depois re-aplique o edit. Máquina de estados completa: `.claude/plans/PLAN-SCHEMA.md` §1.

### Padrão anti-CEO-overhead bloqueado

**Mensagem:** `GOVERNANCE: anti-CEO-overhead ...`

**Causa:** `check_anti_ceo_overhead.py` dispara quando o CEO faz por
conta própria um trabalho que deveria ser delegado (um dos predicados
P1-P5 — ex.: escrever código em massa inline em vez de spawnar um
especialista).

**Fix:** delegue via `/spawn`. Se a ação está genuinamente correta e
você aceita o overhead, defina `CEO_OVERHEAD_ACK=1` para aquela ação (o
override em si é auditado).

### Edit em caminho de kernel hard-denied

**Mensagem:** `GOVERNANCE: ... arbitration kernel ...` (hard-deny).

**Causa:** `check_arbitration_kernel.py` faz hard-deny de edits nos
caminhos do kernel de governança (os hooks, a própria lógica de
arbitragem). Essa é a guarda mais forte e não é relaxada apenas pelo
sentinel canônico.

**Fix:** mudanças de kernel passam por um PLAN-NNN com um kernel
override emitido pelo Owner: `CEO_KERNEL_OVERRIDE=<plan-id>` +
`CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT`, com escopo naquele plano. Nunca
carregue um override velho entre sessões — dê `unset` quando não for o
seu plano atual (um override esquecido silenciosamente amplia quais
edits canônicos passam).

### Acesso a scratchpad cross-plan bloqueado

**Mensagem:** `scratchpad --plan ...`

**Causa:** `check_scratchpad_access.py` bloqueia um plano de ler ou
escrever a memória de scratchpad de outro plano.

**Fix:** use o scratchpad com escopo no seu próprio plan id. Se você
precisa de um handoff, escreva no namespace de memória compartilhada via
`/memory-scratchpad` para o seu plano atual, não no caminho de outro
plano.

### Cap de custo de swarm bloqueado

**Mensagem:** `GOVERNANCE: cost_envelope_capped_at_<window>: ...`

**Causa:** `check_cost_envelope.py` bloqueia um dispatch de swarm/agente
cujo gasto estimado excederia o cap de custo por janela.

**Fix:** reduza o fan-out (menos spawns em paralelo), ou rode em lotes.
A estimativa vem de `CEO_SWARM_ESTIMATE_CENTS` /
`CEO_SWARM_ESTIMATED_SPAWN_CENTS`; se a estimativa está errada, corrija-a
antes de re-dispatchar. O cap é uma trava de orçamento, não um bug.

### Injeção em resposta de MCP bloqueada

**Mensagem:** `{"decision":"block", ...}` vindo do resultado de um MCP tool.

**Causa:** `check_mcp_response.py` (STRICT) bloqueia quando a resposta de
um MCP tool contém um padrão de prompt-injection / override de instrução.

**Fix:** isso está te protegendo — um servidor MCP externo tentou
injetar instruções. Não contorne. Inspecione o servidor MCP culpado; se
for um falso positivo em conteúdo benigno, abra uma issue com a tag
`area/hooks`.

### Sentinel de skill-patch bloqueado

**Mensagem:** `{"decision":"block", ...}` ao aplicar um skill patch.

**Causa:** `check_skill_patch_sentinel.py` bloqueia aplicar um skill
patch sem um sentinel válido assinado pelo Owner.

**Fix:** roteie mudanças de skill via `/architect` ou `/skill-review`; o
Owner assina o sentinel que autoriza a aplicação.

### Roteamento de tier-policy bloqueado

**Mensagem:** `{"decision":"block", ...}` referenciando tier policy.

**Causa:** `check_tier_policy.py` bloqueia um dispatch que viola a
política de roteamento por tier de modelo (`.claude/tier-policy.json`).

**Fix:** roteie a tarefa para o tier que a política permite para aquela
classe de tarefa. Se o próprio roteamento está errado, o fix é uma
mudança na tier-policy (canônica — via PLAN-NNN + sentinel), não um
bypass por chamada.

### Escrita de arquivo pelo Codex bloqueada

**Mensagem:** `{"decision":"block", ...}` numa escrita do Codex (pair-rail).

**Causa:** `check_codex_filewrite.py` bloqueia o pair-rail do Codex MCP
de escrever em caminhos fora do escopo permitido.

**Fix:** faça o Codex propor o diff e deixe o CEO aplicá-lo pelo caminho
normal de Edit/Write (que as guardas canônicas então avaliam). O Codex é
um revisor/propositor, não um escritor direto em caminhos protegidos.

### Confidence gate bloqueado

**Mensagem:** `decision: block` com um motivo de confiança.

**Causa:** `check_confidence_gate.py` bloqueia uma afirmação de baixa
confiança (modo block por classe do ADR-019-AMEND-1) — ex.: um agente
afirmando um fato que não consegue fundamentar.

**Fix:** fundamente a afirmação (cite o arquivo/linha) e tente de novo.
Em último caso a saída de bypass é `CEO_CONFIDENCE_BYPASS=1`, mas
prefira corrigir a afirmação a fazer bypass — uma afirmação bloqueada
costuma ser um sinal real.

### Quais hooks bloqueiam vs. apenas avisam

Nem todo hook bloqueia. Estes são **advisory-only** (emitem findings mas
nunca retornam `decision: block`), então se o trabalho parou *não* é um
destes: `check_read_injection.py`, `check_webfetch_injection.py`,
`check_output_secrets.py` / `check_output_safety.py`,
`check_pair_rail.py` (caminho de block rebaixado a advisory pelo
ADR-127), `check_skill_bootstrap_post.py`, e `audit_log.py` (observador
silencioso). O conjunto que bloqueia são os 13 hooks documentados acima
(bash-safety, canonical-edit, agent-spawn, plan-edit,
anti-ceo-overhead, arbitration-kernel, scratchpad-access,
cost-envelope, mcp-response, skill-patch-sentinel, tier-policy,
codex-filewrite, confidence-gate). Verifique o conjunto atual você mesmo
com:
```bash
grep -l '"decision": "block"' .claude/hooks/check_*.py
```

## "Não sei qual comando ou skill usar"

**Sintoma:** você tem uma tarefa mas não sabe o que invocar.

**Fix:** use a primitiva de descoberta — digite `/help me <sua situação>`
(note o espaço depois de `help`):
```
/help me I need to add a payment endpoint that takes card data
```
Ela é context-aware: dê a sua situação *atual*, não uma pergunta
genérica. Ela te roteia para a skill ou comando certo.

## "/first-run command not found"

**Sintoma:** algum doc antigo menciona um comando `/first-run` e você
recebe command-not-found.

**Causa:** não existe um comando-slash `/first-run` — não há
`.claude/commands/first-run.md`. O onboarding de primeira execução é o
script wizard, não um slash command.

**Fix:** rode o wizard direto:
```bash
python3 .claude/scripts/first-run-wizard.py run
```
Isso detecta o profile do seu repo, explica, e recomenda as principais
skills para ativar. Para descoberta contextual durante o uso normal,
use o comando `/help me <sua situação>` (ver seção acima).

## "CEO não ativou"

**Sintoma:** você digita "Ativa o protocolo CEO" e o Claude responde
como assistente genérico.

**Checklist:**
1. Você está dentro do diretório do projeto? (`pwd` deve mostrar o
   projeto, não o home)
2. Existe `CLAUDE.md` na raiz?
3. Existe `PROTOCOL.md` na raiz?
4. Existe `.claude/skills/core/ceo-orchestration/SKILL.md`?

Se algum não existe, rode o install:
```bash
bash /caminho/ceo-orchestration/scripts/install.sh
```

## "CEO spawnou agente e ele falhou"

**Sintoma:** CEO spawna "VP Engineering" e recebe output inútil ou
inventado.

**Causa 1: persona não foi carregada.** Verifique o audit log:
```bash
python3 .claude/scripts/audit-query.py search --q "VP Engineering"
```

Se o `has_profile: false` aparece, a spawn foi sem persona. CEO
precisa usar o `/spawn` corretamente.

**Causa 2: skill não existe.** Lista as skills instaladas:
```bash
python3 .claude/scripts/registry.py skills
```

Se a skill invocada não está listada, corrija o SKILL MAP em
`.claude/team.md`.

**Causa 3: agente alucinou arquivo.** Sprint 7 vai incluir confidence
gate. Por enquanto, valida você mesmo:
```bash
grep -r "<caminho que o agente citou>" .
```

Se não existe, a agent mentiu. É strike (3 strikes = persona rewrite).

## "Coverage CI falhou"

**Sintoma:** push pra main, CI de Coverage vermelho, mensagem
`FAILED under 86`.

**Fix:**
1. Rode local primeiro:
   ```bash
   python3 -m coverage run --source=.claude/hooks -m unittest discover -s .claude/hooks/tests
   python3 -m coverage run --append --source=.claude/scripts -m unittest discover -s .claude/scripts/tests
   python3 -m coverage report
   ```
2. Identifica o arquivo com gap
3. Adiciona teste pra cobrir

Ou, se foi regressão temporária (grande refactor), abra PR
relaxando threshold em `.github/workflows/coverage.yml` (Owner aprova).

## "/debate travou em 'waiting for agent N'"

**Causa:** um dos spawns paralelos falhou silenciosamente.

**Fix:**
```bash
ls -la .claude/plans/PLAN-NNN/debate/round-1/
```

Se falta um arquivo `<archetype>.md`, re-spawne aquele agente:
```
/spawn "<archetype>" "finish your round 1 critique on PLAN-NNN and write .claude/plans/PLAN-NNN/debate/round-1/<archetype-slug>.md"
```

## "Audit log cresceu muito"

**Sintoma:** `audit-log.jsonl` passou de 10 MB.

**Fix:** rotação automática já existe. Se não rotacionou:
```bash
ls -la ~/.claude/projects/<slug>/
# Procura audit-log-2026-04.jsonl, -2026-05.jsonl, etc
```

Se não há rotacionados e o arquivo tá enorme, força rotação:
```bash
mv ~/.claude/projects/<slug>/audit-log.jsonl \
   ~/.claude/projects/<slug>/audit-log-$(date +%Y-%m-manual).jsonl
```

## "Memory 'auto-carregou' errado"

**Sintoma:** CEO lembra de coisa que você não falou ou não lembra do
que falou.

**Fix:** memory fica em:
```bash
ls ~/.claude/projects/<slug>/memory/
```

Edita direto OU:
```
Esquece X.
```

CEO vai procurar a entrada na memory e remover.

## "Quero desligar tudo temporariamente"

```bash
cd /caminho/do/seu/projeto
mv .claude .claude.disabled
mv CLAUDE.md CLAUDE.md.disabled
```

Claude Code volta ao modo genérico.

Pra religar:
```bash
mv .claude.disabled .claude
mv CLAUDE.md.disabled CLAUDE.md
```

## "Como limpo audit log e lessons pra começar do zero?"

```bash
SLUG=$(pwd | sed 's|/|-|g' | sed 's|^-||')
rm -f ~/.claude/projects/$SLUG/audit-log.jsonl
rm -f ~/.claude/projects/$SLUG/audit-log.errors
rm -rf ~/.claude/projects/$SLUG/lessons/
```

Atenção: perdeu auditoria. Backup antes se for relevante.

## "CEO_HOOK_ADAPTER: o que é?"

Env-var que escolhe qual adapter de IDE usar. **V1.0 suporta só
`claude`**. Deixa vazio ou default:

```bash
# Não precisa exportar nada — o default é claude
```

Gemini stub existe mas é pra Sprint 8+. Não use em produção.

## "Testes local passam, CI falha"

**Causas comuns:**
1. **Ambiente diferente.** CI tem Python 3.11, Linux. Teste local
   provavelmente macOS + Python 3.9.
2. **Secrets faltando.** Alguns testes exigem env vars que você tem
   local mas CI não.
3. **Dependência não instalada no CI.** Veja `.github/workflows/*.yml`
   — qualquer `pip install` listado, adicione no seu ambiente.

## Pedidos comuns que o CEO recusa

- "Escreve direto sem plano" → recusa por protocolo
- "Ignora o hook X" → recusa, hooks são mecânicos
- "Merge sem code review" → Staff Code Reviewer veta
- "Commit sem eu pedir" → anti-pattern #7

Se você acha que a recusa está errada, escale pro Owner.

## Quando abrir issue no GitHub

- Hook comportamento inconsistente (block em cenário que deveria
  permitir)
- Skill com informação desatualizada
- Doc com erro

Rotular com `area/hooks`, `area/skills`, `area/docs` respectivamente.

## Último recurso: reinstalar do zero

```bash
cd /caminho/do/seu/projeto
rm -rf .claude/
rm CLAUDE.md PROTOCOL.md
bash /caminho/ceo-orchestration/scripts/install.sh
```

Perde customizações. Backup primeiro.
