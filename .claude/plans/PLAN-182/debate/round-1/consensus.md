---
plan: PLAN-182
round: 1
created_at: 2026-08-20
synthesis: anonimizada (DEBATE-SCHEMA 13.2) — Critic-A/B/C
---

I have enough verified ground. Producing the synthesis.

# consensus.md — PLAN-182, debate L3 round 1

> Síntese anonimizada (DEBATE-SCHEMA §13.2). Três críticas, todas com veredito **ADJUST**. Onde as críticas divergem sobre um fato do disco, eu medi e digo quem reproduz. Medições minhas marcadas `[medido agora]` — log vivo `~/.claude/projects/ceo-orchestration/audit-log.jsonl`, **15.355 linhas**, 9.887.898 bytes.

## 1. Consensus findings

**F1 — O escopo é o DIRETÓRIO inteiro, não o audit-log. A W0-US2 fecha sobre 5 artefatos e por isso a AC-3 fecha vazia.** (A, B, C)
A inventaria `audit-key`, `.salt`, `memory-shared/`, `state/`, `fact-gate/`, `advisory-dampen/`, `tool-lifecycle/`, `cache/`, `speculative-ledger.json`, `credential-rotation.json`, sidecars e dois locks. B dá os anchors dos que faltam: `audit-log.last-hmac` (`audit_hmac.py:80`), `chain-length` (`:90`), `rotation-manifest.json` (`:103`), spool (`spool_writer.py:198`), salt (`injection_salt.py:70`), `output-scan-dedup.json` (`output_scan_dedup.py:161`) — **11 artefatos, não 5**. C mede **45 entradas** de topo e `state/` com **129.661** arquivos. Consenso: US2 tem de fechar sobre a lista completa, e o título/escopo do plano fala de "audit path" quando o objeto é runtime state.

**F2 — O `.salt` (ADR-079) é o item mais grave e o plano não o menciona uma vez.** (A, B, C — dois mecanismos distintos)
(i) *Compartilhamento*: salt único por `$HOME` ⇒ `prompt_sha256` correlaciona **entre projetos**, que é exatamente o oráculo que o ADR-079 foi escrito para fechar (A: "um segredo atravessando fronteira de projeto"; B: "a garantia do ADR-079 já é falsa", `injection_salt.py:63-70`). (ii) *Rotação silenciosa na cura*: `get_instance_salt()` (`:124-148`) **cunha e persiste na primeira chamada** quando o arquivo não existe e só devolve `b""` em falha de I/O — logo a W1, ao mudar o dir, rotaciona o salt **sem erro, sem log, sem sinal**, contra o `## No rotation` do próprio módulo (B R5, C R1). Consenso: W1 precisa de `[P0]` de carry-over **ou** emenda ao ADR-079; a W2 discute re-chavear o log e nunca cita o salt.

**F3 — §1 tem número irreprodutível e subconta a tenancy.** (A, B, C)
A: `project=="ceo-orchestration"` aparece **7 vezes** no log inteiro; os demais estão sob rótulo de caminho absoluto. B: há **quatro** valores distintos de `project`, não "um segundo projeto". C: reproduziu **1.534 exato** e `env_var_hijack_blocked` 28 / `veto_triggered` 3 / `git_hook_bypass_blocked` 1 / `output_scan_finding_suppressed` 841 — todos exatos — mas **"310" não reproduz sob nenhum predicado** (soma 302 na janela).
`[medido agora]` **5 valores distintos**: `''` 10.254 · `/Users/…/<tenant-a>` **2.136** · `/Users/…/<tenant-b>` **1.706** · `/Users/…/ceo-orchestration` **1.053** · `ceo-orchestration` **7**. São **dois** projetos estrangeiros, e este repo emite sob **dois rótulos**. O plano diz "um segundo projeto" e "310": ambos errados.

**F4 — ~2/3 a 4/5 do log não é atribuível ⇒ a opção "segregar" da W2 não é executável como escrita.** (A R1, B R3, C must-fix-7)
Todos os três medem a mesma massa: A 10.233/13.109 (78%), B 10.229 vazios + 161 ausentes, C 10.105/12.836 (~80%). Causa é código, não env faltando: `project` é parâmetro do chamador com default `""` (B: `audit_emit.py:2506` e `:2561`; C: `:2926` + ~40 assinaturas).
`[medido agora]` 10.254 vazios + **199 ausentes** = 10.453 de 15.355 (68%). Nuance nova e acionável: entre a medição de C e a minha o total cresceu **+2.519** e os não-atribuíveis só **+149** (~6%) — **a massa não-atribuível é legado quase-estático**, não taxa de produção corrente. Isso importa para a W2: o problema é uma janela histórica fechada, não um vazamento que continua no mesmo ritmo. *(Sobre a chave de junção A e C discordam — ver §6-1; medi e A vence.)*

**F5 — ADR-001 é a decisão vigente, já previu este plano, e diverge do código hoje; o plano não o cita.** (A must-fix-7, B must-fix-5, C must-fix-8)
`ADR-001-runtime-state-directory.md` é **ACCEPTED, 2026-04-11**, com a consequência literal *"the `<project-slug>` derivation is implicit … Both work; Sprint 3 may align them"* — este plano **é** esse alinhamento, adiado desde abril. A linha de Decisão define `${CLAUDE_PROJECT_DIR_NATIVE:-…}` e `[verifiquei]` **`CLAUDE_PROJECT_DIR_NATIVE` é consumido por 0 arquivos `.py`/`.sh`** — só aparece no próprio ADR (`:73`, `:79`). Consequência normativa: o literal é **defeito contra decisão ACCEPTED**, não escolha em aberto; o ADR declara blast radius L2 e os números do plano dizem L3+; e **nenhuma wave tem "emenda ao ADR-001" como entregável**, embora a doutrina do repo exija ADR antes para 3+ módulos.

**F6 — A Open Question 2 está mal-posta: já existem ≥3 esquemas de slug em produção, e o namespace escolhido não é do framework.** (A unseen-a, B nice-to-have, C R4/must-fix-3)
Path-slug (`token-estimator.py:583`, `ceo-cost.py:128`), basename-lowercase de `CLAUDE_PROJECT_DIR` (`memory_shared.py:80-87`, `persona_routing.py:187-190`), env-name (`state_store.py:125`), e `ceo-boot.py:1021-1023` que já faz `CLAUDE_PROJECT_DIR or os.getcwd()` — literalmente a regra que a W1 propõe "inventar". Além disso `~/.claude/projects/` tem **120 entradas** (A: 73 do harness / 47 do framework; B: inclui variantes de duplo traço e o slug de **outro usuário**), e o slug "óbvio" aterrissa exatamente em `~/.claude/projects/-Users-…-ceo-orchestration/`, que é **onde vive o `memory/` que o CLAUDE.md §0.3 manda carregar**. A pergunta certa não é "qual slug" — é **em que namespace o framework tem direito de escrever**, e como normaliza (traversal/colisão).

**F7 — Existe uma TERCEIRA convenção repo-local já shipada, contra a Opção A rejeitada do ADR-001.** (A unseen-b, B nice-to-have, C unseen)
`_lib/federation/handlers/audit_event_push.py:234` **escreve** em `<repo>/.claude/state/audit-log.jsonl` e `check_skill_bootstrap_post.py:129-131` **lê esse caminho como primeiro candidato**, com o literal `$HOME` só como segundo. Se ficarem, a cura entrega **três** convenções em vez de duas.

**F8 — A W1 é uma cerimônia canônica grande, e §1 contradiz §3 sobre como pagá-la.** (A R2, C R5/must-fix-5; B endossa a separação em §7)
`[verifiquei]` `check_canonical_edit.py` casa por glob `.claude/hooks/*.py` (`:30`), `_lib/*.py` (`:33`), `_lib/**/*.py` (`:35`) — **100% dos hooks e do `_lib` são canônicos** — e enumera **exatamente 5** arquivos de `.claude/scripts/` (`:131-134` + `:345`). §1 conclui "não cabem num pack"; §3 exige lote único escritores+leitores. As duas frases não podem coexistir. *(A e C medem o mesmo e concluem coisas opostas sobre a redação — §6-3.)*

**F9 — Orçamento subestimado por fator ~2.** (A unseen-f: 250-450k / 4-6 sessões; C must-fix-9: 300-500k / 4-6; B must-fix-9: não cobre 87 módulos + 45 testes + cerimônia). A e C convergem quase exatamente sem se verem. Atual: 120-260k / 2-4.

**F10 — Modos de arquivo pertencem ao inventário e são gate de migração.** (A, B R8, C nice-to-have) Dir vivo com 0644 e 0600 misturados; `verify_chain()` devolve `perm_error/key_bad_perms` com chave 0644 ⇒ copiar a chave sem `0600` transforma a migração em falha de verificação. C: `audit-log.jsonl` está **0644**, junto com 16 entradas de topo e 43.448 arquivos em `state/` — relevante porque a razão declarada do ADR-001 é vazamento de segredo.

**F11 — AC-1/AC-2 não têm instrumento executável.** (A must-fix-9, B must-fix-6) O predicado "resolve caminho de audit/state em runtime" não é executável, e grep pelo literal exige allowlist (SPEC, docs e testes legados o mantêm) ⇒ **gate verde com pergunta velha**, a classe dominante deste repo. O controle negativo tem de ser fixture de **dois** `CLAUDE_PROJECT_DIR` ⇒ dois dirs ⇒ **duas chaves HMAC distintas**; remover o resolvedor deixa vermelho.

**F12 — O lock compartilhado é artefato de primeira classe e falta no plano.** (B R7, C unseen) Mecanismos diferentes e ambos válidos: B = acoplamento de **disponibilidade** (processo travado de outro projeto estola os hooks deste); C = a serialização acidental pelo lock comum é **o que mantém a cadeia íntegra hoje**, logo migrar o lock antes/junto do log produz escrita concorrente sem exclusão mútua — **corrupção de linha, não só cadeia partida**. A ORDEM de migração do lock vira decisão normativa.

**F13 — Anchor `state_store.py:126` off-by-one** (A, B, C): o `os.environ.get("CEO_PROJECT_NAME", …)` está em `:125`; `:126` é o `return` que monta. Trivial, mas num plano cuja tese é precisão.

## 2. Single-agent insights KEPT

**K1 (A) — A superfície de INSTALAÇÃO está inteiramente fora do censo e é a causa raiz do default.**
`[verifiquei tudo]` `scripts/install.sh` e `scripts/upgrade.sh`: **0 menções** a `CEO_AUDIT_LOG_DIR`. `templates/settings/settings.base.json` não tem a chave. `templates/codex/pre-push-review-gate.sh:90` e `templates/grok/pre-push-review-gate.sh:144` hardcodam `${HOME:-/tmp}/.claude/projects/ceo-orchestration/state` — e são **git hooks instalados no repo do adopter**. `install.sh` faz EXISTS→SKIP em `settings.json` (`:1576`), logo editar template cura só instalação nova. E a cura já existe no repo: `scripts/install-accelerators.sh` injeta `CEO_AUDIT_LOG_DIR` (`:136`; cabeçalho em `:24` explica *por que* o `install.sh` não faz). Sobrevive sozinho porque é literalmente verificável e porque **inverte a ordem de causa**: o plano trata o adopter como W3-P1.

**K2 (A) — `SPEC/v1` codifica o literal como NORMATIVO, e isso é pergunta de versão.** `[verifiquei]` `SPEC/v1/audit-log.schema.md:11` = `${CEO_AUDIT_LOG_PATH:-$HOME/.claude/projects/ceo-orchestration/audit-log.jsonl}`; `SPEC/v1/state-stores.schema.md:16` = idem para `state/`. SPEC/v1 é deny-Edit por tipo e é uma das três superfícies decididas por `_ownership_verdict()`. Mudar código sem SPEC ⇒ `check-spec-drift.py` discorda; mudar SPEC ⇒ cascata de contrato **v1 vs v2**.

**K3 (A) — O CI é cego a esta classe por construção.** `[verifiquei]` `otel-smoke.yml:64` isola (`CEO_AUDIT_LOG_DIR=/tmp/ceo-otel-smoke`); `mcp-smoke.yml:320` **lê o literal**; `validate.yml` não isola nada. Um runner tem um projeto ⇒ contaminação cross-project é invisível a todo gate existente.

**K4 (A) — O restore desfaz a cura em silêncio.** `ceo-backup.sh:87,93` / `ceo-restore.sh:99,103` resolvem por `${CEO_PROJECT_NAME:-ceo-orchestration}` + literal; qualquer restore pós-W1 num shell sem env reescreve o dir antigo sem nada ficar vermelho.

**K5 (A) — Bounding rule para a matriz da US2, senão a W0 não fecha.** `env-inventory.json` registra **33 vars `CEO_*`** de audit/state/project. "5 artefatos × combinações conflitantes" sobre 33 vars é produto que ninguém fecha ⇒ definir classes de equivalência por artefato; e var nova sem atualizar `env-inventory.json` deixa a dimensão (vi) do `nightly-hygiene` vermelha.

**K6 (A) — Correção de citação: "U-1" não é dos PLAN-167/168** (`:139`); é do debate round-1 do PLAN-169 (`PLAN-169/debate/round-1/consensus.md:13`). Verificável, custo zero.

**K7 (B) — Reclassificação de propriedade de segurança: a tamper-evidence não está "degradada", está AUSENTE na fronteira.** `key_path()` (`audit_hmac.py:184-190`) devolve `<dir>/audit-key`; chave compartilhada ⇒ processo de outro projeto **recomputa a cadeia inteira** deste repo após editar/truncar e `verify_chain()` devolve `intact`. `verify_chain()` deixa de provar não-adulteração e passa a provar não-**corrupção acidental**. Consequência lógica inescapável, e contradiz a claim do `CLAUDE.md` §1. Puxa junto o must-fix-10 de B: item de honestidade no `CLAUDE.md` §5 **junto com a W1**, não depois.

**K8 (B) — Falta modelo de adversário, e ele decide a FORMA da W1.** Adopter malicioso / hook comprometido / segundo projeto do próprio operador são respostas diferentes: **chave por projeto** (isolamento por construção) vs **dir por projeto** (isolamento por convenção). Sem escrever isso, a W1 fecha a AC com a propriedade errada.

**K9 (B) — Confidencialidade, não integridade: o campo `project` é caminho absoluto em texto claro.** `[confirmei ao ler o log]` os dois tenants estrangeiros aparecem nomeados em claro. No **mesmo registro**, `repo_path_hash` é hasheado — duas políticas de redação contraditórias na mesma linha. E o §1 do plano redige o identificador na prosa sem notar que **o log não redige**.

**K10 (B) — Dedup/dampen compartilhados são oráculo de supressão cross-tenant.** `output_scan_dedup._resolve_state_dir()` (`:146-161`) e `advisory_dampen.py:166`. Os **841** `output_scan_finding_suppressed` que §1 cita como *volume de contaminação* podem ser *supressões indevidas de findings deste repo* — é eficácia de controle, não medição. Consequência operacional que a W2 tem de **prever e anunciar**: após migrar, o dedup zera e haverá rajada de advisories, que será lida como regressão.

**K11 (B) — Auditar a própria migração dentro da cadeia.** Já existe `chain_reset_marker` (`audit_emit.py:2498-2512`); a migração deve emitir marcador equivalente para a janela mista ficar declarada **dentro** da cadeia, e não só na prosa do plano.

**K12 (C) — DEFEITO VIVO, verifiquei no disco: dois leitores já resolvem para um log INEXISTENTE.**
`token-estimator.py:585` e `ceo-cost.py` usam `if scoped.exists() or scoped.parent.is_dir(): return scoped`. `[verifiquei]` `~/.claude/projects/<home-slug>/` **existe** (é o dir de transcripts do harness) e `.../audit-log.jsonl` **não existe** ⇒ o predicado é verdadeiro pelo **segundo disjunto**, os dois retornam caminho inexistente sempre que `CLAUDE_PROJECT_DIR` está setado (ou seja, em toda sessão), e o fallback legado é **inalcançável**. `scoped.parent.is_dir()` pergunta "o Claude Code já abriu este projeto?" quando a pergunta pretendida era "o log já migrou?". Duas consequências normativas: (a) a frase de §3 "os leitores seguem medindo o log contaminado" é **falsa** para esses dois; (b) a W0 deixa de ser censo e vira **triagem de uma migração já iniciada e abandonada**.

**K13 (C) — `spool_writer` quebra a cura por dentro.** `_state_dir()` = `<audit_dir>/state` incondicional, **sem override de `CEO_PROJECT_STATE_DIR`**; a chave do journal é o **PID**, namespace de baixa cardinalidade que colide entre projetos (129.661 entradas hoje). Pior: `_PROJECT_DIR_CACHE`/`_STATE_DIR_CACHE` (`:146-154`) são chaveados em `(CEO_AUDIT_LOG_DIR, HOME)` com contrato declarado "BYTE-IDENTICAL to `audit_emit._audit_dir`" (`:174-177`) — se a W1 faz o dir depender de `CLAUDE_PROJECT_DIR`/cwd, **a chave do cache não cobre o novo input** e o vazamento cross-projeto sobrevive exatamente à cura que o plano compra. Sobrevive sozinho porque é uma falha silenciosa da própria W1.

**K14 (C) — Superfície empacotada.** `dist/ceo-plugin/hooks/` (não rastreada pelo git) carrega cópia da família **não byte-idêntica** à fonte (sha diferente em `SessionStart.py` e `check_bash_safety.py`). A W3 tem de dizer se isso é família e como é regenerado.

**K15 (B, com a evidência reparada por mim) — A W0-US3 nomeia o instrumento ERRADO, e isso é a classe-assinatura do repo dentro do gate do próprio plano.**
B pediu "nomear o verificador rotation-aware" mas afirmou que `check-audit-hmac-null.py` não existe — **está errado**, ele existe (`.claude/scripts/check-audit-hmac-null.py`, 9.128 bytes, executável). O defeito real é pior: `[verifiquei o docstring]` esse script é *"a regression guard, **NOT** a full chain verification — for cryptographic chain integrity use `audit-verify-chain.py`"*, e caça a classe `hmac=null` (S234). O plano (`:111`) o manda responder "quantas cadeias distintas coexistem e o que `verify_chain()` retorna sobre a janela mista" — pergunta que ele **não pode** responder por construção. O verificador certo existe: `.claude/scripts/audit-verify-chain.py` (17.641 bytes) e **é** rotation-aware (`enforce_marker_if_manifest`, checagem de marcador na linha 1 em modo manifesto, `:288-311`). Nota de higiene: a própria memória do repo (HMAC-483) confunde os dois — a linha "use `check-audit-hmac-null.py`" para integridade de cadeia deve ser corrigida no closeout.

## 3. Single-agent insights REJECTED / DEFERRED

**X1 — REJEITADO POR MEDIÇÃO (C must-fix-7, a parte da chave de junção).** C afirma "**10.384 dos 10.391** eventos sem project compartilham `session_id` com eventos que têm project, e só **1** sessão mapeia para mais de um projeto", e usa isso para dizer que "segregar" é factível. `[medido agora]` dos **10.453** eventos sem `project` (10.254 vazios + 199 ausentes), apenas **202** têm `session_id` não-vazio, distribuídos em **6** session_ids distintos, dos quais 4 são joináveis a um rótulo; e `sessões mapeando para >1 projeto = **0**`. A chave de junção que sustenta a viabilidade **não existe**. A parte de C que sobrevive — "atribuibilidade é `[P0]` da W0, não premissa da W2" — já está em F4.

**X2 — REJEITADO POR FATO (B must-fix-1, a alegação de inexistência).** `check-audit-hmac-null.py` existe. O item vira K15 com a evidência trocada.

**X3 — REJEITADO POR FATO (B must-fix-3, "918").** O plano cita **841** (`:29`), não 918; C reproduziu 841 exato. Não atribuir ao plano número que ele não contém — num debate cujo tema é precisão numérica, isso é o mesmo defeito de assinatura.

**X4 — DEFERIDO com razão substantiva (C unseen, "Regra dos 10x": `state/` com 129.661 entradas em diretório plano).** É verdadeiro e é **escala, não isolamento** — C mesmo escreve que isolar por projeto *melhora o sintoma e não cura a chave `<PID>`*. Absorver aqui faz o plano crescer um segundo problema com gate próprio, que é como o PLAN-169 W4-C inchou até este item ter de sair dele. Registrar como dívida (`# CEO-DEBT:` + ponteiro daqui), com a exceção de que a **colisão de PID entre projetos** (K13) fica, porque essa é isolamento.

**X5 — DEFERIDO com razão substantiva (A nice-to-have, "fixar `CEO_AUDIT_LOG_DIR` em todos os jobs do `validate.yml`").** Fixar a env em CI **agora** mascara exatamente o comportamento que a W0 existe para medir: o caminho **sem env**. Vira item da W1/W3 (depois do resolvedor), nunca da W0. O irmão do item — `mcp-smoke.yml:320` e `otel-smoke.yml:64` derivarem do mesmo helper — entra já, porque é K3.

**X6 — DEFERIDO até a US5 existir (C R4, "órfãos de dados por escolha de slug").** Real, mas a lista de órfãos (`memory-shared/patterns`, `state/` do `state_store`) só é enumerável depois do inventário de diretório que ainda não foi feito. Entra na reemissão da W2, ancorado na saída da US5 — não como texto especulativo agora, que é o erro de método que o plano inteiro existe para não repetir.

## 4. Plan adjustments

| Seção-alvo | O que muda |
|---|---|
| **Frontmatter — `title` / `tags`** | "audit path isolation" → isolamento de **runtime state por projeto**; o objeto são 45 entradas de diretório (F1). Adicionar tags `salt`, `confidentiality`. |
| **Frontmatter — `budget_tokens` / `budget_sessions`** | 120-260k / 2-4 → **~300-450k / 4-6** (F9; A e C convergem independentemente). |
| **Frontmatter — `depends_on` / nova linha** | Declarar dependência de **emenda ao ADR-001** (e possivelmente ADR-079) como pré-requisito da W1 (F5, F2). |
| **§1 — evidência** | Trocar "1.534 … contra **310**" pelo histograma completo por rótulo, com comando reprodutível; corrigir "um segundo projeto" → **dois** tenants estrangeiros + este repo sob **dois** rótulos; acrescentar a massa `project=""` e a taxa corrente (~6% dos novos) (F3, F4). |
| **§1 — nota de redação** | Registrar que o log **não** redige o que a prosa redige: `project` é caminho absoluto em claro, no mesmo registro em que `repo_path_hash` é hasheado (K9). |
| **§1/§3 — contradição de cerimônia** | Escolher e escrever UMA saída: (a) lote canônico `_lib`+hooks com flag-day, ou (b) lote único com custo declarado. Corrigir "39 em `.claude/scripts/` (tier NÃO-canônico)" — não existe tier; o guard é glob + 5 arquivos enumerados (F8). |
| **§3 — tempo verbal e alcance** | "os leitores seguem medindo o log contaminado" é **falso** para `token-estimator`/`ceo-cost`, que já leem um log inexistente (K12). Reescrever como *triagem de migração parcial já em curso*. Nomear o **lock** como o mecanismo mais perigoso e sua ordem de migração (F12). |
| **§ nova (§4) — modelo de adversário + propriedade de segurança** | Escrever quem é o atacante e reclassificar: tamper-evidence é **ausente**, não degradada, na fronteira de tenancy; decide chave-por-projeto vs dir-por-projeto (K7, K8). |
| **W0-US1 — predicado** | Definir o predicado executável de `derive-audit-family.py` e a regra de allowlist; a família inclui **escritores, leitores, templates, installer, CI, SPEC e testes** (F11, K1, K2, K3). |
| **W0-US2 — matriz** | De 5 artefatos → **11+** com anchors (F1); acrescentar bounding rule por classes de equivalência sobre as 33 vars de `env-inventory.json` (K5); registrar que sob PATH-only lock e errors **não** acompanham. |
| **W0-US3 — instrumento** | Trocar `check-audit-hmac-null.py` por **`audit-verify-chain.py`** para a pergunta de cadeia, e rodar **os dois** (o delta entre eles é a resposta); anexar a saída bruta (K15, §6-2). |
| **W0-US5 (nova, `[P0]`)** | Inventário do **diretório** por artefato → dono → semântica de compartilhamento → **modo de arquivo** (F1, F10). |
| **W0-US6 (nova, `[P0]`)** | Atribuibilidade: histograma de `project`, presença de `session_id`, e **veredito explícito sobre a existência de chave de junção** — hoje medido como inexistente (F4, X1). |
| **W0-US7 (nova, `[P0]`)** | Reconciliação dos resolvedores já shipados: 4 implementações + a convenção repo-local; qual vence e o que cada uma já possui (F6, F7, K12). |
| **W0-US4** | Ampliar de "adopters instalados" para incluir `templates/`, `install.sh`, `upgrade.sh`, `settings.base.json`, `dist/ceo-plugin/hooks/` (K1, K14). |
| **W1 — `[P0]` novo** | Carry-over do `.salt` **antes** do primeiro `get_instance_salt()`, com teste que falha se o valor diferir — ou emenda ao ADR-079 declarando a rotação (F2). |
| **W1 — `[P0]` novo** | Chave de cache do `spool_writer` tem de cobrir o novo input, e `_state_dir()` precisa de override; senão o vazamento sobrevive à cura (K13). |
| **W1 — teste de paridade (AC-2)** | Fixture de **dois** `CLAUDE_PROJECT_DIR` ⇒ dois dirs ⇒ **duas chaves HMAC distintas**, com controle negativo; grep pelo literal não é oráculo (F11). |
| **W1 — item de honestidade** | Atualizar `CLAUDE.md` §5 **no mesmo lote**: enquanto a família não migrar, a claim de tamper-evidence do §1 não vale entre projetos do mesmo `$HOME` (K7). |
| **W1/W2 — modos** | Dir `0700`, key `0600`, sidecars `0600`; `verify_chain()` pós-migração como gate, com controle positivo (chave 0644 ⇒ `perm_error`) (F10). |
| **W2 — opções** | Marcar "segregar" como **indisponível para ~68-80% do log** com a medição anexa; a decisão vira "declarar a janela" vs "arquivar e recomeçar cadeia" (F4, X1). Acrescentar decisão sobre o **salt** e emitir marcador de migração na cadeia (F2, K11). |
| **W2-P1** | Reclassificar de medição para **eficácia de controle**, e prever/anunciar a rajada de advisories pós-migração (K10). |
| **W3 — novo `[P0]`** | Rota do installer: chave em `settings.base.json` + merge aditivo no `upgrade.sh` (com o backup que já existe); curar `templates/{codex,grok}/pre-push-review-gate.sh` (K1). |
| **W3 — novo `[P1]`** | `ceo-backup.sh`/`ceo-restore.sh` e `dist/ceo-plugin/hooks/` (K4, K14). |
| **AC-3** | Passa a exigir a matriz sobre a lista **fechada na US5**, não sobre os 5 artefatos de hoje. |
| **AC nova (AC-7)** | Emenda ao ADR-001 (e decisão SPEC v1 vs v2) registrada **antes** de qualquer execução da W1 (F5, K2). |
| **AC-6** | Manter como está — e acrescentar que a **reemissão da W1** passa por sua própria rodada de crítica, dado o tamanho do delta desta síntese. |
| **OQ-1** | Reescrever com "segregar" marcado indisponível (F4). |
| **OQ-2** | Reescrever: não é `CLAUDE_PROJECT_DIR` vs `git rev-parse` — é **em que namespace o framework pode escrever**, dado que `~/.claude/projects/` é do harness e já hospeda o `memory/` (F6). |
| **OQ-3** | Ampliar de `CEO_PROJECT_NAME` para os **três/quatro** esquemas de nome (F6). |
| **OQ-4 (nova)** | Semântica de "per-installation" no ADR-079: `$HOME` ou projeto? As duas leituras exigem ações **opostas** (§6-5). |
| **OQ-5 (nova)** | Ordem de execução: installer-first (A) vs por-artefato (B) vs writers-atomic + readers por candidate-list (C) — decidir **depois** da W0, não agora (§6-4). |
| **Correções pontuais** | `state_store.py:126` → `:125` (F13); "U-1" → PLAN-169 debate round-1 (K6); `install-accelerators.sh` injeta em `:136` (o `:24` é comentário de cabeçalho). |
| **Reference links** | Acrescentar ADR-001, ADR-079, `audit-verify-chain.py`, `SPEC/v1/{audit-log,state-stores}.schema.md`, `docs/ownership-decision-table.md` (histórico — a autoridade é ADR-190 + `ownership_table.tsv`). |

## 5. Round verdict

**PROCEED.**

Os três críticos convergem em ADJUST e nenhum pede redesenho: os 13 consensos são **ampliação de escopo, correção numérica e entregáveis faltantes**, todos incorporáveis ao texto atual. O que mudaria a *forma* do plano — candidate-list para leitores, fatiamento por artefato, installer-first — cai inteiramente dentro de W1-W3, que a AC-6 **já** declara esboço não-normativo a ser reemitido a partir da W0; re-criticar hoje um texto que o próprio plano manda substituir seria desperdício. A única contradição factual com consequência operacional (segregabilidade da W2) eu resolvi no disco nesta síntese, não sobra desacordo aberto entre críticos que exija árbitro. Ressalva única, já refletida em §4: como o delta é grande, a **reemissão da W1** deve passar por sua própria rodada — não esta.

## 6. Contradições entre críticos

**6-1 — A opção "segregar" da W2 é executável? (A: não · C: sim)** — **RESOLVIDO, A vence.**
A: "apenas 35 dos eventos com `project=''` carregam `session_id`; `cwd`/`repo`/`project_dir` ausentes". C: "10.384 de 10.391 compartilham `session_id` com eventos rotulados; só 1 sessão mapeia >1 projeto". `[medi]` 202 de 10.453 têm `session_id` não-vazio, em **6** session_ids distintos, e **0** sessões mapeiam para mais de um projeto. A ordem de grandeza é a de A. **Decidiria:** escrever a W2 sem a opção "segregar por `project`", e pôr a busca por discriminante alternativo como entregável explícito da W0-US6 — se a US6 achar um, a opção volta com evidência; enquanto não achar, ela não está na mesa.

**6-2 — O que `verify_chain()` diz hoje? (B: `tamper/hmac_mismatch/line=1` · C: "íntegra por acidente de lock")** — **não é contradição real: entrypoints diferentes.**
B chamou o `verify_chain()` **cru**; C argumenta pelo mecanismo (o lock comum serializa as escritas dos dois projetos). `[verifiquei]` `audit-verify-chain.py` faz checagem de **marcador na linha 1 em modo manifesto** (`enforce_marker_if_manifest`) — exatamente o que produz falso `line=1` no entrypoint cru, que é o HMAC-483 já registrado na memória do repo. **Decidiria:** a W0-US3 roda **os dois** e reporta ambos; o **delta** entre eles é o resultado, não o número de nenhum deles isolado. E corrigiria a linha da memória que manda usar o null-checker para integridade de cadeia.

**6-3 — Como descrever o tier canônico? (A: "39 em tier não-canônico está essencialmente certo" · C: "não existe tier; a frase sugere que a W1 pode landar sem sentinel")** — **medem o mesmo, concluem coisas opostas.**
`[verifiquei]` ambos estão certos sobre o fato: 5 arquivos de `.claude/scripts/` enumerados (`:131-134`, `:345`), 100% de hooks/`_lib` cobertos por glob. **Decidiria com C** na redação e **com A** na consequência: escrever "o guard casa por glob + enumeração; **a família tem ~30 arquivos canônicos e ~50 não-cerimoniais**", e manter que a razão de separar do W4-C é o **tamanho do pack**, não "escapa da cerimônia". A frase atual permite a leitura perigosa que C aponta.

**6-4 — Como fatiar a atomicidade do §3? Três propostas incompatíveis, e os três defendem o §3 no próprio §7.**
A: installer/template **primeiro** (para a hemorragia em instalações novas sem tocar canônico). B: fatiar **por artefato**, nunca por módulo. C: atomicidade só para **escritores**; leitores com *candidate-list* (padrão já em uso em `check_skill_bootstrap_post.py:128-131`), o que corta o lote canônico quase pela metade. **Decidiria:** nenhuma delas agora. Vira **OQ-5**, respondida pela tabela da W0 — escolher a ordem antes do levantamento é literalmente o erro de método (`2→4→20→≥22→63`) que originou o plano. Observação para quem responder: as três não são mutuamente exclusivas — A opera na superfície do adopter, C na de leitores, B é a regra de agrupamento; podem compor.

**6-5 — O que "per-installation" significa no ADR-079? (B: garantia já falsa · C: ambiguidade não resolvida)**
B: salt único por `$HOME` ⇒ `prompt_sha256` correlaciona entre projetos ⇒ **abrir emenda ao ADR-079**. C: se "installation" == `$HOME`, o **código está certo** e é a W1 que introduz a divergência; se == projeto, a propriedade já não vale — leituras opostas exigem ações opostas (**carry-over** vs **re-derivação**). **Decidiria:** não escolher por dedução; virar **OQ-4** decidida com o modelo de adversário (K8) — se o atacante inclui outro projeto do mesmo `$HOME`, "installation" tem de significar projeto e o salt é re-derivado com perda de correlação **declarada**; se não inclui, carry-over. E, decidido qualquer um dos dois, o ADR-079 é emendado — porque hoje ele documenta um caminho com placeholder de slug que o código não implementa.

**6-6 — Tamanho da família: três números para o mesmo conjunto.** A aceita 63 (24/39); B mede 65 literal-builders e **87** por proxy comportamental (36 hooks + 51 scripts); C aceita 63 mas rejeita a partição. **Decidiria:** nenhum número entra no plano até a W0-US1 publicar o **predicado**; até lá a frase é "hipótese, entre ~63 e ~87 conforme o predicado", que é o que a AC-1 já exige e o §1 hoje não cumpre.