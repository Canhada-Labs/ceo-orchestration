---
plan: PLAN-182
round: 1
archetype: VP Engineering
created_at: 2026-08-20
source: workflow wf_6568bd64-6d7 (fan-out read-only; artefato gravado pelo CEO)
attribution: retorno estruturado do workflow, validado por marcadores de conteudo
---

Verification complete. Producing the critique.

---

## 1. Verdict

**ADJUST** — o método (levantamento antes de especificação) está certo e a evidência numérica principal confere no disco; mas o **modelo do problema está errado em três eixos** que mudam a forma das waves, e o W1 como escrito quebra silenciosamente um invariante do ADR-079.

## 2. Summary

O plano lê o defeito como *um literal hardcoded + N call-sites*, e propõe censo comportamental (W0) → resolvedor único (W1) → decisão sobre o log contaminado (W2) → adopters (W3). Verifiquei as âncoras: `audit_hmac.py:154-182` ✓, `audit_emit._audit_dir():2292-2299` ✓, `_log_path():2301-2305` ✓, `check_skill_bootstrap_post.py:130-131` ✓ (`Path.home()` de fato quebrado em duas linhas), a citação `## Anti-patterns` item **6** do `SKILL.md` ✓ (`SKILL.md:724,731`), o `### Registro de execução — W4 ABERTA` no PLAN-169 ✓ (`:693`), e a cura S168 no docstring ✓.

Pela minha lente, três coisas quebram o plano como está: **(a)** o escopo está desenhado em torno do artefato errado — o diretório compartilhado tem 45 entradas, não um log (inclui `audit-key`, `.salt`, `memory-shared/`, `fact-gate/`, `advisory-dampen/`, `cache/`, `tool-lifecycle/`, e um `state/` com **129.661** arquivos); **(b)** o "resolvedor único" da W1 **já existe, em quatro formas incompatíveis**, e uma delas já está resolvendo errado em produção hoje; **(c)** a W1 é obrigatoriamente uma cerimônia canônica assinada de ~30 arquivos (glob `.claude/hooks/*.py` + `_lib/**/*.py`), o que o budget de 40-80k não comporta.

## 3. Risks

1. **Rotação silenciosa do salt do ADR-079 (severidade máxima).** `injection_salt._slug_dir()` (`:61-70`) retorna o literal constante; `get_instance_salt()` (`:124-148`) **gera e persiste na primeira chamada quando o arquivo não existe**, retornando `b""` só em falha de I/O. Mecanismo: a W1 muda o diretório → `.salt` não existe lá → salt novo é cunhado **sem erro, sem log, sem sinal** → todo `prompt_sha256` histórico deixa de correlacionar. O ADR-079 proíbe isso explicitamente (`## No rotation`: "Rotating the salt would invalidate `prompt_sha256` correlations across all historical audit events — the chief use of the field"). O plano não menciona o salt nem o ADR-079.

2. **Colisão de journal de spool por PID entre projetos.** `spool_writer._state_dir()` (`:203+`) é incondicionalmente `<audit_dir>/state`, sem override de `CEO_PROJECT_STATE_DIR`. O diretório vivo tem 129.661 entradas `audit-pending.<PID>.journal[.lock]`. A chave é o **PID**, um namespace de baixa cardinalidade que **colide entre processos de projetos diferentes**. Isso não é "log compartilhado": é o buffer de escrita pré-drain compartilhado com chave colidente.

3. **Cache de slot único com chave incompleta pós-W1.** `spool_writer._PROJECT_DIR_CACHE`/`_STATE_DIR_CACHE` (`:146-154`) são chaveados em `(CEO_AUDIT_LOG_DIR, HOME)`, com contrato declarado "**BYTE-IDENTICAL to audit_emit._audit_dir**" (`:174-177`). Se a W1 faz o dir depender de `CLAUDE_PROJECT_DIR`/cwd, a chave do cache **não cobre o novo input** → um processo que muda de projeto retorna o dir cacheado do anterior. O vazamento cross-projeto sobrevive exatamente à cura que o plano compra.

4. **Órfãos de dados por escolha de slug.** Existem hoje ≥3 regras de slug divergentes: path-slug `-Users-...` (`token-estimator.py:583`, `ceo-cost.py:128`), basename-lowercase de `CLAUDE_PROJECT_DIR` (`memory_shared.py:80-87`), e nome-por-env `CEO_PROJECT_NAME` (`state_store.py:125`). Escolher uma **orfana os dados das outras duas** — `memory-shared/patterns` e o `state/` do `state_store` incluídos. A W2 só cobre "o log contaminado".

5. **Atomicidade + tier canônico ⇒ lote assinado grande.** `_CANONICAL_GUARDS` (`check_canonical_edit.py:115-200`) casa por **glob**: `.claude/hooks/*.py`, `.claude/hooks/_lib/*.py`, `.claude/hooks/_lib/**/*.py`. Todos os ~26 hooks + `_lib` da família são sentinel-gated (e `.claude/scripts/lessons.py` também, por enumeração). Somado ao §3 ("escritores e leitores no MESMO lote"), a W1 é **um pack GPG de ~30 arquivos canônicos indivisível**. É a mesma classe de risco pela qual o item saiu do W4-C, reimportada.

## 4. Must-fix

1. **Renomear o escopo e o título: é isolamento de RUNTIME STATE, não de audit path.** Inventário medido do diretório compartilhado (`~/.claude/projects/ceo-orchestration/`, 45 entradas): `audit-key`, `.salt`, `audit-log.chain-length`, `audit-log.last-hmac`, `audit-log.errors` (+7 arquivos arquivados, um de 28 MB), `advisory-dampen/`, `cache/`, `fact-gate/`, `memory-shared/`, `tool-lifecycle/`, `speculative-ledger.json`, `state/` (129.661 entradas, 2.830 não-vazias), ~19 logs rotacionados de 10 MB. Acrescentar `[P0][US5]` à W0: **inventário do DIRETÓRIO por artefato → dono → semântica de compartilhamento → modo**, não só do log.

2. **Adicionar `[P0]` à W1: carry-over explícito do `.salt` + emenda ao ADR-079.** Ou a W1 copia o salt para o dir novo antes do primeiro `get_instance_salt()`, ou o ADR-079 é emendado declarando a rotação. Verificável: teste que roda `get_instance_salt()` sob o dir novo e falha se o valor diferir do dir antigo. Sem isso a W1 quebra um invariante forense sem emitir nenhum sinal.

3. **Reescrever a O.Q. 2 e o primeiro item da W1: o resolvedor NÃO é novo.** Já existem quatro implementações shipadas: `ceo-cost.py:122-135` e `token-estimator.py:578-589` (precedência `LOG_PATH > LOG_DIR > slug > legado`, com o path-slug do ADR-001), `ceo-boot.py:1021-1023` (`CLAUDE_PROJECT_DIR or os.getcwd()` — literalmente a regra que a W1 propõe "inventar"), `memory_shared.py:80-87` (basename). A W0 tem de entregar **qual resolvedor vence e o que cada um já possui**, não "derivar um".

4. **Corrigir §1 e §3: os leitores já estão divergentes, e um já lê errado HOJE.** Medido: `~/.claude/projects/<home-slug>/` **existe** (é o dir de transcripts do Claude Code), logo em `token-estimator.py:585` o predicado `scoped.exists() or scoped.parent.is_dir()` é **verdadeiro pelo segundo disjunto**, e `scoped` (`.../audit-log.jsonl`) **não existe**. Consequência: `token-estimator` e `ceo-cost` já retornam um caminho inexistente sempre que `CLAUDE_PROJECT_DIR` está setado — leem um log vazio, silenciosamente, e o fallback legado em `:589` é **inalcançável na prática**. A frase de §3 "os leitores seguem medindo o log contaminado" é verdadeira para `ceo-boot.py:74`, `skill-health.py:200`, `audit-tokens.py:58` e **falsa** para esses dois. A W0 tem de reportar isso como defeito vivo, não como risco futuro.

5. **Corrigir "39 deles em `.claude/scripts/` (tier NÃO-canônico)".** Não existe tier: `_CANONICAL_GUARDS` é glob + enumeração por arquivo; `.claude/scripts/lessons.py`, `prune-lessons.py`, `lesson-restore.py`, `lesson_ranker.py`, `night-mode.py` **são canônicos**, e 100% dos hooks/`_lib` da família também. A justificativa correta para o plano separado não é "escapa da cerimônia" (não escapa) e sim "**adiciona ~50 arquivos não-cerimoniais a um pack de escopo fechado**". Como está, o texto sugere que a W1 pode landar sem sentinel.

6. **Publicar o comando que reproduz a evidência de §1** — a AC-1 exige isso da família; a própria §1 não cumpre. Reproduzi na janela declarada: **1.534** eventos do projeto estrangeiro ✓ exato, e `env_var_hijack_blocked` **28** ✓, `veto_triggered` **3** ✓, `git_hook_bypass_blocked` **1** ✓, `output_scan_finding_suppressed` **841** ✓ — todos exatos quando atribuídos àquele projeto. Mas **"310 do próprio ceo-orchestration" não reproduz**: com o predicado `project` não-vazio na janela `2026-08-19T21:17` → `2026-08-20T11:58Z`, este repo soma **302** (295 sob `project="<home>/ceo-orchestration"` + 7 sob `project="ceo-orchestration"`). Ou o predicado é outro, ou o número está errado; num plano cuja tese é "especifiquei além do que verifiquei", um número irreprodutível na seção de evidência é o defeito de assinatura.

7. **Acrescentar `[P0]` à W0: atribuibilidade dos eventos, que é o que decide a viabilidade da W2.** Medido: **10.105 de 12.836** eventos têm `project=""` e 161 não têm o campo — ou seja, **~80% do log não é atribuível diretamente**, porque `project` é parâmetro do chamador com default `""` (`audit_emit.py:2926` e ~40 assinaturas seguintes). A opção "segregar" da W2 é infactível ou factível conforme exista uma chave de junção; medi que existe: **10.384 dos 10.391** eventos sem project compartilham `session_id` com eventos que têm project, e só **1** sessão mapeia para mais de um projeto. Sem esse número a W2 é uma decisão sem instrumento.

8. **Emendar/citar o ADR-001.** `ADR-001-runtime-state-directory.md` é a decisão vigente e já contém a consequência exata deste plano: "*The `<project-slug>` derivation is implicit — Claude Code uses a path-based slug... The audit log uses the bare project name. Both work; Sprint 3 may align them*". Este plano **é** esse alinhamento, adiado desde abril, e não cita o ADR. Pior: a linha de DECISÃO do ADR-001 define `${CLAUDE_PROJECT_DIR_NATIVE:-$HOME/...}` e `CLAUDE_PROJECT_DIR_NATIVE` **não aparece em nenhum `.py`/`.sh` do repo** (0 arquivos) — o ADR e o código já divergem hoje. Pela doutrina da `architecture-decisions` ("irreversible + 3+ modules ⇒ ADR first"), 63+ módulos exigem ADR novo ou emenda **antes** da W1; hoje nenhuma wave tem esse entregável.

9. **Reajustar o budget.** W0 re-escopada (inventário de diretório + reconciliação de 4 resolvedores + atribuibilidade): **90-140k tokens, 1-2 sessões**. W1 como pack canônico assinado de ~30 arquivos com pair-rail: **150-300k, 2-3 sessões** — os 40-80k atuais descrevem um refactor livre, não uma cerimônia. Total realista **300-500k / 4-6 sessões**, não 120-260k / 2-4.

## 5. Nice-to-have

- Adicionar `spool_writer._project_dir_from_env()` (`:174-198`) e `_state_dir()` (`:203+`) ao bloco "o que já se sabe (verificado)" da W0-US2 e aos Reference links — o próprio docstring de `audit_hmac` diz "Precedence mirrors audit_emit **+ spool_writer**", e o plano cita só dois dos três.
- Registrar em US2 que sob **PATH-only** o *lock* e o *errors* **não** acompanham: `_lock_path()`/`_errors_path()` derivam de `_audit_dir()`, que ignora `LOG_PATH`. A frase "log e chave ficam CO-LOCADOS" é verdadeira e incompleta.
- Registrar a colisão de `state/`: `spool._state_dir()` = `<audit_dir>/state` e `state_store._state_root()` = `$HOME/.claude/projects/<CEO_PROJECT_NAME>/state` apontam para **o mesmo diretório** sob env vazia, com escapes divergentes (`CEO_AUDIT_LOG_DIR` vs `CEO_STATE_ROOT`) — setar só `CEO_AUDIT_LOG_DIR` move um e não o outro.
- Inventariar modos no W0: `audit-log.jsonl` está **0644**, junto com 16 outras entradas de topo e 43.448 arquivos em `state/`. Dado que a razão declarada do ADR-001 é vazamento de segredo, isso pertence ao inventário.
- `dist/ceo-plugin/hooks/` (não rastreado pelo git) carrega uma cópia da família **não byte-idêntica** à fonte (sha diferente em `SessionStart.py` e `check_bash_safety.py`). A W3 deveria dizer se a superfície empacotada é família e como é regenerada.

## 6. Unseen

- **O plano descreve como risco futuro (§3) um estado que já é presente.** `token-estimator`/`ceo-cost` já resolvem para um log inexistente sempre que `CLAUDE_PROJECT_DIR` está setado. A "cura pela metade" que §3 teme já foi parcialmente aplicada — por dois readers, em datas diferentes, sem plano. Isso muda a W0 de censo para **triagem de uma migração já iniciada e abandonada**.
- **`scoped.parent.is_dir()` é um predicado vacuoso.** A pergunta pretendida é "o log já migrou?"; o teste executado é "o Claude Code já abriu este projeto?" — sempre verdadeiro. É a classe *instrumento verde cuja pergunta envelheceu* já catalogada neste repo, aqui na forma de um fallback inalcançável. Vale um teste de controle negativo próprio na W1.
- **A cadeia HMAC está íntegra hoje por acidente de lock, não por design.** Ambos os projetos, sem env, resolvem `_lock_path()` para o mesmo `$HOME/.../audit-log.lock`, então as escritas intercaladas serializam e `verify_chain()` passa. Migrar o **lock** antes ou junto do **log** produz escrita concorrente sem exclusão mútua — corrupção de linhas, não só cadeia partida. §3 nomeia a quebra de cadeia; o lock é o mecanismo mais perigoso e não está nomeado.
- **A propriedade de privacidade do `.salt` é mais frágil do que o ADR sugere.** O ADR-079 fala em "per-installation" e documenta o caminho como `~/.claude/projects/<slug>/.salt` — com placeholder de slug que o código não implementa. Se "installation" == `$HOME`, o código está certo e a W1 é que introduz a divergência; se == projeto, a propriedade já não vale. **Essa ambiguidade precisa ser resolvida por escrito antes da W1**, porque as duas leituras exigem ações opostas (carry-over vs re-derivação).
- **Regra dos 10x:** `state/` com 129.661 entradas em um diretório plano é um problema de escala independente do isolamento — dez adopters no mesmo `$HOME` multiplicam isso, e a chave `<PID>` não escala nem hoje. Isolar por projeto **melhora** o sintoma e **não** cura a chave.
- **Existe uma alternativa estrutural que o plano não considera e que dissolveria §3.** O padrão *candidate-list* já está em uso no repo (`check_skill_bootstrap_post.py:128-131` tenta repo-local, depois o literal): **leitores com lista de candidatos + escritores com destino único** desacopla a migração de leitores da de escritores. A atomicidade é real para escritores+estado HMAC; para **leitores** é auto-imposta. Reconhecer isso corta o lote canônico praticamente à metade e remove a maior fonte de risco de cerimônia.

## 7. What I would NOT change

- **O sequenciamento levantamento→especificação e a §2 ("por que o grep falhou").** É a decisão certa e a evidência empírica dela (2→4→20→22→63) está honestamente registrada. Nenhuma "otimização" futura deve colapsar a W0 num censo textual.
- **A reformulação da AC-6 de condição histórica para gate de execução.** Está correta e é sutil: a redação original era insatisfazível no instante em que foi escrita. Não voltar atrás.
- **§3 e o `[P1]` "escritores e leitores no MESMO lote" — para escritores.** O mecanismo descrito (estado HMAC migra, log não → `verify_chain()` acusa quebra sem adulteração) está tecnicamente correto e verificado contra o código. Meu ajuste é restringir o escopo aos escritores, não enfraquecer a regra.
- **A AC-2 (paridade com controle negativo no mesmo commit) e a AC-4 ("não decidido" mantém o plano aberto).** São exatamente os dois gates que impedem este plano de terminar em verde vacuoso.
- **A disciplina de estimativa em tokens+sessões** (`budget_tokens`/`budget_sessions`, `external_wait: nenhum`) — já obedece ao ADR-081/PLAN-180; discordo dos valores, não da unidade.