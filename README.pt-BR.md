# ceo-orchestration

<!-- last-reviewed: 2026-06-22 v1.0.0 -->

> **English:** [`README.md`](README.md) — fonte canônica.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/Canhada-Labs/ceo-orchestration/actions/workflows/validate.yml/badge.svg)](https://github.com/Canhada-Labs/ceo-orchestration/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/Canhada-Labs/ceo-orchestration)](https://github.com/Canhada-Labs/ceo-orchestration/releases)

Uma camada de governança e auditabilidade para operar o [Claude Code](https://docs.anthropic.com/en/docs/claude-code) como um time estruturado de agentes especialistas — instalada **dentro** de um repositório existente, e não executada como um serviço.

> **Status:** framework de uso pessoal mantido — fator-ônibus 1, sem compromissos de roadmap; o repositório público é um snapshot estável, não um produto com equipe ativa. Não há comunidade pública, base de contribuidores nem adotante externo a mencionar — apenas o framework e seus testes.

A premissa é estreita e deliberada: um agente de codificação baseado em LLM é mais perigoso não quando escreve código ruim, mas quando faz uma alteração **não revisada, não registrada e irreversível** em um repositório com o qual você se importa. O `ceo-orchestration` coloca um portão e um livro-razão na frente desse momento.

---

## Nenhuma alegação de velocidade

Seis experimentos internos não encontraram **nenhum ganho geral de velocidade** desta orquestração em relação a uma sessão solo otimizada do Claude Code. O valor aqui é **governança e auditabilidade** — propriedades ortogonais à velocidade. Deixamos isso claro logo no topo, em vez de maquiá-lo. Se você procura "deixar meu agente mais rápido", esta é a ferramenta errada.

O que ele de fato oferece:

- Um portão **Planejar → Debater → Executar** para mudanças arriscadas, de modo que um agente não possa reescrever silenciosamente arquivos protegidos.
- Um **log de auditoria à prova de adulteração** (encadeado por HMAC) de cada spawn de agente, edição e cerimônia — para que você possa *detectar*, depois do fato, se o histórico registrado foi alterado.
- Um **trilho de revisão cross-model**: um segundo LLM (Codex) revisa as edições do Claude em caminhos protegidos antes que elas entrem.
- Um catálogo de **checklists de skills** prontos que um agente carrega sob demanda, em vez de improvisar.

---

## Como funciona

Quando instalado, o framework registra um conjunto de [hooks do Claude Code](https://docs.anthropic.com/en/docs/claude-code/hooks) que interceptam chamadas de ferramentas (spawn de agentes, edição de arquivos, execução de comandos de shell) e aplicam a política *antes* de a ação acontecer.

**1. O protocolo CEO.** O trabalho é enquadrado como um "CEO" delegando a agentes especialistas. Edições rotineiras seguem direto. Mudanças transversais ou arriscadas são gateadas: exigem um plano registrado e, para a classe mais arriscada, um debate estruturado de múltiplas rodadas entre personas de agentes antes da execução. O protocolo é um contrato escrito (`PROTOCOL.md`), aplicado mecanicamente por hooks, e não por convenção.

**2. Log de auditoria à prova de adulteração.** Cada evento governado acrescenta uma linha JSONL a um log de auditoria local, com cada entrada encadeada por HMAC à anterior. Uma rotina `verify_chain()` percorre o log e reporta a primeira quebra. Isso **detecta adulteração** — uma entrada removida ou editada quebra a cadeia —, mas não *prova* a ausência de adulteração, e é um controle local, não um serviço de notarização. Trate-o como um fio de armadilha de integridade, não como uma prova de tribunal.

**3. Pair-rail cross-model.** Quando um agente tenta editar um caminho canônico (protegido), um hook roteia a mudança proposta para um segundo modelo, para revisão somente leitura. Se esse revisor retornar qualquer coisa com formato de escrita, a edição é bloqueada. A ressalva honesta: o revisor padrão é outro modelo de linguagem grande, e revisores da mesma classe compartilham pontos cegos (veja *Riscos*).

**4. Checklists de skills.** O framework entrega **166 arquivos de skill** — checklists reutilizáveis e específicos de domínio (revisão de segurança, fan-out de auditoria, onboarding em uma base de código desconhecida, e assim por diante) que um agente carrega quando relevante, em vez de reinventar os passos a cada vez.

---

## O que vem na caixa

Todas as contagens abaixo são verificáveis a partir de um checkout limpo (veja *Verificando os números*).

| Componente | Contagem | Notas |
|---|---|---|
| Checklists de skills | **166** | 42 core + 8 frontend + 116 de domínio |
| Scripts de hook (em disco) | **55** | entrypoints Python em `.claude/hooks/` |
| Hooks ligados em `settings.json` | **44** | scripts distintos, 46 registros de evento |
| Módulos de biblioteca compartilhada | **68** | apenas stdlib, em `.claude/hooks/_lib/` (excluindo o `__init__.py` do pacote) |
| Slash commands | **26** | em `.claude/commands/` |
| Architecture decision records | **180** | em `.claude/adr/` |
| Testes | **~12.000 casos** | reportados por `pytest --collect-only` nas suítes de hook, script e conformidade |

A diferença entre **55 em disco** e **44 ligados** é benigna: vários módulos que não respondem a eventos são ativados via dispatch in-process (invocados por outros hooks), e não por um registro de evento direto em `settings.json`.

**Dependências de runtime: nenhuma.** Hooks e scripts são Python ≥ 3.9, **apenas biblioteca padrão** — zero pacotes de terceiros em runtime. Veja [`SBOM.md`](SBOM.md). (Desenvolvimento e CI usam ferramentas de teste de terceiros, como o pytest; o runtime instalado não usa.)

Há também um **contrato de conformidade publicado** em `SPEC/v1/` (32 arquivos — 28 `*.schema.md` mais os docs de contrato, com versão fixada), uma especificação TLA+ da máquina de estados central do circuit-breaker, um harness de conformidade e um dashboard de auditoria local somente leitura.

---

## Qual skill devo usar?

166 skills é um problema de descoberta, não uma feature. A lista curta abaixo cobre os casos do dia a dia; o resto pode esperar até algo quebrar. Slash commands são digitados no chat do Claude Code; nomes simples são checklists de skill em `.claude/skills/core/` que você (ou um agente spawnado) carrega pelo nome.

| Se você precisa de… | Use | Por quê, em uma linha |
|---|---|---|
| Um início de sessão governado | `/ceo-boot` | Roda os checks de boot da sessão e imprime um digest de estado antes de qualquer trabalho |
| Uma visão do estado do projeto num relance | `/status` | Plano, fase, vetos e atividade recente de auditoria em uma tela |
| Delegar trabalho a um agente especialista | `/spawn "<Agent>" "<task>"` | Monta o prompt de persona + skill + file-assignment que o hook de spawn exige |
| Gatear uma mudança arriscada (L3+) | `/debate start PLAN-NNN "<proposta>"` | Debate estruturado de múltiplas rodadas, registrado, antes da execução |
| Uma revisão de código estruturada | `code-review-checklist` | O checklist de revisão que um revisor spawnado carrega em vez de improvisar |
| Um scan de padrões de veto em um arquivo | `/veto-check <arquivo>` | Sinaliza padrões de code-review e segurança dignos de veto antes de um PR |
| Uma revisão de segurança e auth | `security-and-auth` | Checklist de arquitetura de segurança, autenticação/autorização e hardening |
| Se orientar em uma base de código desconhecida | `/onboard <path>` | Entry points, grafo de dependências, mapa de camadas, ordem de leitura (skill: `codebase-onboarding`) |
| Decidir o que e como testar | `testing-strategy` | Padrões de teste e doutrina de garantia de qualidade do projeto |
| Continuar um plano em um terminal novo | `/resume PLAN-NNN` | Re-deriva o estado do trabalho a partir do arquivo do plano, do log de auditoria e do scratchpad |
| Passar estado entre agentes no meio de um plano | `/memory-scratchpad` | Memória compartilhada com escopo de plano para handoff entre agentes |
| Prova de que as proteções realmente bloqueiam | `/self-test` | Teste hermético in-process das proteções centrais — sem rede, sem custo |
| Saber quanto custou um plano ou janela de tempo | `/agent-budget` | Rollup de uso de tokens e custo por plano ou janela |
| Interpretar um veredito de revisão cross-model | `cross-llm-pair-review` | Quando invocar o pair-rail e como ler os desfechos dos Casos A–F |
| Padrões de falha conhecidos antes de trabalho arriscado | `/pitfall` | Lista pitfalls do catálogo universal (mais qualquer catálogo de domínio instalado) |

Referência completa de comandos e scripts: [`docs/CHEAT-SHEET.md`](docs/CHEAT-SHEET.md). Se nada acima servir, a skill `help-me` recomenda até três skills contextuais para uma tarefa que você descreve em linguagem natural.

---

## Início rápido

> **Somente fontes oficiais.** Os únicos pontos oficiais de distribuição são o repositório GitHub [`Canhada-Labs/ceo-orchestration`](https://github.com/Canhada-Labs/ceo-orchestration) e o pacote npm [`ceo-orchestration`](https://www.npmjs.com/package/ceo-orchestration) (`npx ceo-orchestration`). Qualquer outro espelho, fork, pacote republicado, listagem em marketplace ou nome parecido é não-oficial e não-confiável. Os releases no GitHub trazem checksums SHA-256 e o pacote npm é publicado com SLSA 3 provenance — verifique antes de instalar.

**Pré-requisitos:** Python ≥ 3.9, Git e Bash. No macOS, o Bash do sistema é o 3.2; instale um moderno com `brew install bash` antes de instalar.

```bash
# 1. Clone o framework em algum lugar FORA do seu projeto
git clone https://github.com/Canhada-Labs/ceo-orchestration.git
cd ceo-orchestration

# 2. Instale-o DENTRO do seu repositório alvo
./scripts/install.sh /path/to/your-app

# 3. De dentro do seu projeto, confirme que a camada de governança está ativa
cd /path/to/your-app
bash .claude/scripts/validate-governance.sh   # imprime uma contagem de erros; 0 = saudável
```

### Escolha UM caminho de instalação

Três rotas podem colocar o framework na frente do Claude Code para um repositório alvo, e elas são **mutuamente exclusivas por repositório**. As duas rotas suportadas (script e npx) escrevem nas mesmas superfícies (`.claude/hooks/`, `.claude/skills/`, `.claude/settings.json` e o manifesto de instalação em `.claude/.install-manifest.sha256`); a rota experimental de plugin, em vez disso, empacota um bundle com seu próprio `hooks/hooks.json` sob a raiz do plugin e **não** escreve settings nem manifesto no repo alvo — então a orientação de desinstalação baseada em manifesto não se aplica a ela:

| Caminho | O que é | Status |
|---|---|---|
| `./scripts/install.sh <target>` a partir de um clone | O instalador de referência (a variante `--link` via git-submodule roda o mesmo script) | Suportado |
| `npx ceo-orchestration <target>` | Shim npm que roda o *mesmo* `install.sh` empacotado | Suportado |
| Plugin do Claude Code (`scripts/build-plugin.py`) | Empacotador experimental da superfície consultiva (`--ceremony user`) | Experimental — não é um caminho de instalação suportado |

**Não** empilhe caminhos no mesmo repositório. Misturá-los produz um modo de falha conhecido: hooks registrados duas vezes (uma em `.claude/settings.json`, outra via o registro de hooks do próprio plugin), fazendo cada ação governada pagar a cadeia de hooks em dobro; merges de settings empilhados uns sobre os outros; e um manifesto de instalação em deriva — o manifesto registra apenas o último escritor, então o `uninstall.sh` não consegue mais remover fielmente a instalação anterior e deixa órfãos para trás.

Se você misturou caminhos, recupere nesta ordem:

1. **Desinstale pelo caminho com que instalou.** Instalações via script ou npx: `scripts/uninstall.sh <target> --dry-run` primeiro, depois de verdade. O shim npm só expõe o instalador, então rode o `uninstall.sh` a partir de um clone — ele honra o mesmo manifesto que o instalador empacotado escreveu. Plugin: remova-o pelo gerenciador de plugins do Claude Code.
2. **Verifique que `.claude/` está limpo.** Sem `team.md`, `hooks/`, `skills/` ou `.install-manifest.sha256` sobrando. O desinstalador preserva deliberadamente arquivos que você modificou depois da instalação — inspecione e remova sobras manualmente.
3. **Reinstale por exatamente UM caminho.**

Veja [`INSTALL.md`](INSTALL.md) para o guia completo opção por opção.

Por padrão, o instalador copia os perfis de skill core e frontend e os hooks de governança. Selecione perfis e hooks de stack explicitamente:

```bash
./scripts/install.sh /path/to/your-app --profile core,frontend,fintech --stack node
```

Dois modos de instalação:

- `--ceremony maintainer` (padrão): governança completa, incluindo cerimônias de edição assinada em caminhos protegidos.
- `--ceremony user`: apenas hooks consultivos, sem assinatura — escreve somente sob `.claude/`. Bom para um teste de baixo atrito.

Para verificar que as proteções de segurança realmente bloqueiam o que afirmam, rode o self-test in-process (hermético, sem rede, sem custo):

```bash
# de dentro do seu projeto instalado, no Claude Code
/self-test
```

Para remover o framework de forma limpa:

```bash
/path/to/ceo-orchestration/scripts/uninstall.sh /path/to/your-app
```

---

## Verificando os números

Não acredite na tabela por fé. A partir de um checkout limpo:

```bash
find .claude/skills -name SKILL.md | wc -l        # 166 skills
ls .claude/commands/*.md | wc -l                  # 22 slash commands
ls .claude/adr | grep -c '^ADR-'                  # 180 ADRs
python3 -m pytest --collect-only -q | tail -1     # ~12.000 casos coletados
```

---

## Riscos e o que isto *não* é

A honestidade intelectual é o ponto central, então as ressalvas são de primeira classe:

- **Fator-ônibus de um.** Isto é construído e mantido por um único mantenedor. Não há um time por trás, nem SLA, nem garantia de continuidade. Avalie-o de acordo.
- **Ressalva do revisor do mesmo fornecedor.** O pair-rail cross-model reduz os pontos cegos de modelo único, mas o revisor ainda é um modelo de linguagem grande e pode compartilhar modos de falha com o modelo sob revisão. É defesa em profundidade, não um oráculo independente.
- **O Codex não vem incluído — o pair-rail fica inerte até você instalá-lo.** O trilho de revisão cross-model invoca a [CLI do Codex](https://github.com/openai/codex), que **não** é distribuída com este framework. Em uma instalação nova, sem o Codex presente, o pair-rail **falha em aberto e não contribui com nenhuma revisão** — as edições em caminhos protegidos ainda passam pela cerimônia GPG, mas nenhum segundo modelo as examina. Você só ganha o degrau cross-model depois de instalar o Codex separadamente. Veja [`docs/HONEST-LIMITATIONS.md`](docs/HONEST-LIMITATIONS.md) e o ADR-145.
- **Custo por edição.** Cada chamada de ferramenta governada roda a cadeia de hooks antes de a ação entrar, adicionando cerca de **~0,3–1,0s** de latência por edição em hardware típico. Esse é o custo do portão; se você quer zero overhead no trabalho rotineiro, a camada de governança não é de graça.
- **Um portão pode errar — há uma válvula de escape.** Os hooks falham em *aberto* diante de bugs de infraestrutura deles mesmos, mas um portão correto ainda pode emitir um DENY com o qual você discorda (um bloqueio falso em um caminho protegido). O caminho pretendido é o `/architect` (que roteia a mudança pela revisão) ou, para uma mudança estrutural do framework, um PLAN-NNN com um sentinel assinado pelo Owner. Para um override *auditado* e deliberado do gate de edição canônica, o Owner pode definir `CEO_SENTINEL_UNLOCK=<plan-id>` + `CEO_SENTINEL_UNLOCK_ACK=I-ACCEPT` para aquela ação — o próprio override é registrado. Hard-denies em caminhos de kernel exigem a cerimônia mais forte `CEO_KERNEL_OVERRIDE`. Veja [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md). Para experimentar o framework sem nenhum desse atrito, instale com `--ceremony user` (hooks consultivos, sem assinatura).
- **Detecção, não prevenção, na cadeia de auditoria.** A cadeia HMAC diz a você *que* o log registrado foi alterado; ela não pode impedir que um atacante com acesso de escrita local cause dano, e não substitui controles de acesso adequados nem backups.
- **A verificação formal tem escopo definido, não é universal.** Existe uma especificação TLA+ para a máquina de estados central, mas o model-checking **não** faz parte do gate de CI obrigatório — não interprete "tem uma especificação TLA+" como "formalmente verificado". A esmagadora maioria do comportamento é coberta por testes convencionais, não por prova mecanizada.
- **É um framework, não um produto.** Sem UI, sem runtime gerenciado, sem "sistema operacional". Ele se instala no seu repositório e sai do caminho.
- **Sem benefício de velocidade.** Reafirmado porque importa: isto não vai deixar seu agente mais rápido.

**Alternativas que vale comparar** se o seu objetivo for orquestração multiagente (em vez de governança): [AutoGen](https://github.com/microsoft/autogen), [MetaGPT](https://github.com/geekan/MetaGPT) e [LangGraph](https://github.com/langchain-ai/langgraph). Essas otimizam para colaboração entre agentes e expressividade de workflow; este projeto otimiza para *gatear e auditar* as mudanças de um único agente capaz em um repositório real.

---

## Saiba mais

**Primeira vez aqui?** Comece por estes:

- [`docs/FAQ.md`](docs/FAQ.md) — o FAQ do primeiro usuário: o que isto é (e o que não é), "um hook acabou de bloquear minha edição, e agora?", isso me deixa mais lento?, eu preciso do Codex?, o que é enviado para algum lugar?, como desinstalar.
- [`docs/QUICKSTART.md`](docs/QUICKSTART.md) — instale em um repositório e confirme que a camada de governança está ativa.
- [`docs/DAY-1-CHECKLIST.md`](docs/DAY-1-CHECKLIST.md) — uma primeira sessão guiada.

Depois, o material de referência:

- [`PROTOCOL.md`](PROTOCOL.md) — o contrato de governança (Planejar → Debater → Executar, vetos, a regra dos três strikes).
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — mapa de componentes e fluxo de dados.
- [`docs/HONEST-LIMITATIONS.md`](docs/HONEST-LIMITATIONS.md) — a versão longa da seção *Riscos*.
- [`SBOM.md`](SBOM.md) — inventário de dependências.
- [`SPEC/v1/`](SPEC/v1/) — o contrato de conformidade publicado.

---

## Licença

Veja [`LICENSE`](LICENSE).
