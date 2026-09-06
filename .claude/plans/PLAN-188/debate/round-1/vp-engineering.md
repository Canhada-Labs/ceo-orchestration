---
round: 1
archetype: VP Engineering
skill: architecture-decisions
agent_persona: (nenhuma — o arquétipo não tem bloco de persona em `team.md` nem arquivo em `.claude/agents/`; perfil sintetizado da linha do SKILL MAP)
generated_at: 2026-09-06T02:10:00Z
---

## Verdict

ADJUST — 4 itens BLOQUEANTES (R-VP1..R-VP4).

## Summary (≤ 3 bullets)

- O corte «UM toolkit + manifesto por pacote» está certo: as 7 classes da tabela (`PLAN-188-shared-ceremony-toolkit.md:32-40`) são propriedades do MOLDE, não de cada wave, e o custo de assinatura é o mesmo em qualquer clone. A honestidade da medição (OQ-5 com seis limites do próprio instrumento, `:206-230`) é exemplar.
- **Onde é forte:** invariantes 1, 2, 4, 6 nomeiam o defeito e o controle; o plano recusa inventar números (OQ-4, `:202-205`); a correção ADR-031→ADR-010 está VERIFICADA em disco (`ADR-010-canonical-edit-sentinel.md:31,44,58,64` define `Scope:` + `check_canonical_edit.py`).
- **Onde é fraco:** o DESTINO escolhido (`.claude/scripts/ceremony/`) tira os scripts do único lint que hoje os cobre; um AC nasce vacuoso; uma chave do manifesto depende de um contrato (`--describe`) que não existe em nenhum derivador do repo; e a W0 promete controles vermelhos para invariantes cujo consumidor só chega na W1.

## Risks

**R-VP1 — P1 BLOQUEANTE — Migrar para `.claude/scripts/ceremony/` REMOVE os scripts do `check-ceremony-script.py`.**
O lint de cerimônia descobre candidatos por conteúdo, mas só dentro de `DISCOVERY_ROOTS = [".claude/plans", ".claude/scripts/local/historical"]` + `EXPLICIT_FILES = [".claude/scripts/local/generate-ceremony.sh"]` (`<ROOT>/.claude/scripts/check-ceremony-script.py:62-67`). Hoje TODO clone `OWNER-*-{SIGN,LAND}.sh` mora sob `.claude/plans/` e é varrido pelas regras BLOQUEANTES R1 (proveniência), R2 (`|| true` em operação irreversível), R3 (`grep|tail` em parsing de VERDICT), R4 (`git add` de diretório) e R8 (exec-bit no índice) — `:12-31`. O toolkit proposto (`:104-106`) nasce fora das três raízes: no dia do land, as 7 classes da tabela ficam fechadas e as 5 regras BLOQUEANTES do lint deixam de valer para o mesmo código. É literalmente a classe «mover artefato para outro diretório cria falso-verde», e ela morde o arquivo mais caro do repo.
*Mitigação (no MESMO patch da W0, não depois):* acrescentar `.claude/scripts/ceremony` a `DISCOVERY_ROOTS` com controle POSITIVO (um script plantado com `|| true` numa linha de `gpg` deve sair VERMELHO a partir do novo destino), e um AC que prove a cobertura pelo lint, não pela existência do diretório.

**R-VP2 — P1 BLOQUEANTE — O `Check:` do AC-3 já está verde e não pode ficar vermelho.**
AC-3 (`:172-175`) prova a migração com «`git ls-files` não lista nenhum `OWNER-*-{SIGN,LAND}.sh` para os 6 pacotes». Medido: `git ls-files | grep -icE 'w4b|w5a|w1a|w6a'` = **0**; os 48 `OWNER-*-{SIGN,LAND}.sh` rastreados são de PLAN-166..186 (`git ls-files | grep -cE 'OWNER-.*(SIGN|LAND)'` = 48) e nenhum pertence aos 6 pacotes — o próprio plano diz que eles «ficam fora do repo» (`:54-56`). O AC passa hoje, antes de qualquer linha escrita, e continua passando se a migração falhar.
*Mitigação:* o AC-3 deve provar o POSITIVO no que é rastreável: cada pacote migrado tem `ceremony.toml` rastreado, o commit assinado do pacote não invoca script próprio (derivável do `.asc` + da mensagem), e o inventário dos scripts dos 6 packs (que vivem em `<PK>`) é declarado por um manifesto sha256 rastreado, no molde da lição «staged/ gitignored ⇒ manifesto rastreado».

**R-VP3 — P1 BLOQUEANTE — `apply-<key>.py --describe` não existe em lugar nenhum, e a §Riscos contradiz a invariante 5.**
A chave `scope_generated_from = "apply-w6a.py --describe"` (`:116`) e a invariante 5 (`:130-131`) exigem que escopo do sentinel e `PROPOSED-PATCH` sejam GERADOS pelo derivador. Medido nos 9 derivadores rastreados (`for f in $(git ls-files | grep -E '/apply-[a-z0-9-]*\.py$'); do grep -c -- '--describe' $f; done`): **0 ocorrências em 9 arquivos** (`.claude/plans/PLAN-169/...`, `PLAN-179/...`, `PLAN-183/...`, `PLAN-185/...`, `PLAN-186/...`). Pior: `:148-149` promete «a migração é por manifesto, **sem re-derivar o patch**» — o que é incompatível com a invariante 5, que só funciona se o derivador de CADA pacote ganhar o subcomando. Duas seções dizem regras diferentes sobre o mesmo pacote.
*Mitigação:* especificar `--describe` como CONTRATO (saída: ops por path, determinística, byte-comparável) num item próprio da W0, com um adaptador para derivadores que não o implementam; e reescrever `:148-149` para dizer o que de fato acontece (o patch não muda; o DESCRITOR passa a existir).

**R-VP4 — P1 BLOQUEANTE — A W0 promete 9 controles vermelhos «sem consumidor», mas 4 invariantes são propriedades de scripts que só chegam na W1.**
Tabela de waves: W0 = «`ceremony.toml` schema + `lib.sh` + os 9 controles vermelhos (sem consumidor)» (`:155`); W1 = `sign.sh`/`land.sh`/`finalize.sh`/`harness.sh` (`:156`). Mas a invariante 2 compara conjuntos no `land.sh`, a 6 liga `NEW_SHA` a índice/tree/push (`:132-134`), a 7 exige o runner EXECUTADO pelo harness a partir da posição landada (`:136`) e a 8 é uma propriedade do harness (`:137`). Um controle vermelho para elas na W0 ou testa um stub (verde-vácuo) ou obriga a W0 a shipar os consumidores. E o AC-1 (`:162-167`) pede exatamente «o harness rodando a partir de um clone descartável em worktree» — ou seja, o AC-1 não é satisfazível pela W0 como descrita.
*Mitigação:* ou W0 vira «lib.sh + as 5 invariantes puras (1,3,4,5,9) com controle vermelho» e as outras 4 migram para a W1 (com AC-1 dividido em AC-1a/AC-1b), ou W0 absorve os 4 scripts — o oráculo permite: `python3 .claude/hooks/check_canonical_edit.py --is-canonical .claude/scripts/ceremony/sign.sh` imprime `0` (não-canônico), logo o pacote continua LIVRE.

**R-VP5 — P2 — O gate de toda assinatura do Owner nasce sem cadeia de autoridade própria.**
Medido: `--is-canonical` devolve `0` para `.claude/scripts/ceremony/sign.sh` e `lib.sh` — o que torna a W0 livre (bom) e, ao mesmo tempo, deixa os 5 scripts editáveis PARA SEMPRE sem sentinel, sem assinatura e sem checksum. O mecanismo que existe para isso é o ADR-192 (`.claude/governance/gate-scripts-manifest.txt`, que hoje pina `verify-counts.sh`, `validate-governance.sh`, `_release_tag_guard.py`, `release.sh`, `validate-pair-rail-verdict.py`, …). O plano não propõe entrada no manifesto em nenhuma wave.
*Mitigação:* AC novo — os 5 scripts entram no manifesto ADR-192 no mesmo patch que os cria, com o controle vermelho «mudar um byte ⇒ gate falha»; sem isso, a superfície de ataque passa de N clones revisados por rail para 1 arquivo não pinado.

**R-VP6 — P2 — O AC-4 mede uma RAZÃO com denominador livre, sobre um corpus definido por `mtime`.**
`measure-rail-classes-v2.py:32` congela `SINCE = 2026-09-04 20:00` e `:123` filtra por `os.path.getmtime(f) >= SINCE`: (a) medir «as 3 assinaturas seguintes» sobre uma árvore que ainda contenha os pacotes da S345 RE-CONTA a linha de base dentro do «depois»; (b) `mtime` não é data de criação — copiar/`checkout` a árvore muda a associação; (c) a fração `ceremony` cai se `docs` crescer, sem que um único defeito de cerimônia tenha sumido; (d) a própria OQ-5(vi) (`:219-225`) mostra que achados em `tests/` são classificados como `ceremony`, inflando exatamente a métrica do AC. E «falha = ≥ 5 %, e o plano diz o porquê» (`:180-181`) não é critério de morte: não diz o que se reverte.
*Mitigação:* AC-4 passa a exigir (i) CONTAGEM ABSOLUTA de achados de classe `ceremony` por assinatura (com a razão como contexto), (ii) `--since`/lista explícita de pacotes como parâmetro do instrumento (parâmetro que muda o veredito não tem default), (iii) critério de morte pré-registrado: se ≥ 5 % em 2 das 3 assinaturas, a W2 pára e o toolkit volta a rail antes de mais migração.

**R-VP7 — P2 — W1 e W2 estouram o modelo de operação v2 e o plano não declara o corte.**
Regra vigente: ≤ 400 linhas OU ≤ 8 paths por pacote. W2 = «migração dos 5 packs + remoção dos clones» (`:157`): 5 `ceremony.toml` + ~20 scripts removidos (4 por pacote, no molde `PLAN-169`, que tem 10 `OWNER-*` rastreados) ≈ 25 paths num único pacote canônico. W1 = 4 scripts + piloto W6a (patch + sentinel + registros) também tende a passar de 8.
*Mitigação:* a tabela de Items declara o corte: W2a/W2b/… um pacote por migração (é o formato natural — cada migração é um manifesto + uma remoção), e W1 separa «toolkit» de «piloto».

**R-VP8 — P2 — A invariante 9 (liveness) é escrita contra uma saída de codex que já não existe.**
`:139-140` exige «`VERDICT:` próprio + `tokens used` diferente de toda rodada anterior». `CLAUDE.md:108` registra, medido: «o rail codex corrente **NÃO emite** `VERDICT:` (rodada limpa = ausência do bloco `Full review comments:`)» — e a invariante 1 (`:120-122`) fala de outra gramática, `Rail-Verdict: APPROVE` no REGISTRO escrito por nós. Duas gramáticas com nomes quase iguais, uma delas ancorada num formato de CLI que já drifou (classe «substrate drift», `reference-codex-cli-substrate-drift`).
*Mitigação:* a invariante 9 é definida sobre o REGISTRO (campos obrigatórios: comando exato, header do modelo, contagem de tokens, sha do diff revisado) e o `lib.sh` valida esses campos; nunca sobre a forma da saída de um vendor.

**R-VP9 — P3 — Desvios de PLAN-SCHEMA que custam pouco e evitam ruído no gate.**
(a) `## Items` deve trazer, por unidade, «file assignment, acceptance criteria, and commit message hint» (`PLAN-SCHEMA.md:440`) — a tabela tem só Wave/Entrega/Gate, e nenhum AC está ligado a uma wave. (b) `depends_on: []` (`:7`) enquanto o piloto AC-2 é um pacote do PLAN-186, que está `status: executing` (`PLAN-186-orchestrator-operating-model.md:4`) — a W1 não pode landar antes daquele pacote existir, e o grafo do §7 do schema é o lugar de dizer isso. (c) as 5 chaves de orçamento da OQ-4 são recomendadas pelo schema (`:310-341`); ficar em aberto é legítimo, mas o Owner precisa ratificar a omissão.

**R-VP10 — P3 — O allow do guard de path absoluto é um buraco declarado.**
`:126-127` prevê «único allow por regex: o glob de self-test `claude-501/*/scratchpad`». Esse glob casa o scratchpad REAL desta máquina — um material assinado que contenha um path pessoal sob `<SP>` passaria pelo guard que existe justamente para impedi-lo.
*Mitigação:* o self-test não precisa de allow: gera o caso com um prefixo sintético (`/nonexistent/self-test/…`) e o guard fica sem exceção — «fechar canal por REMOÇÃO, não por enumeração».

## O que falta antes da W0 (OQs para o Owner ratificar)

1. **OQ-3 é PRÉ-REQUISITO da W0, não do debate genérico:** a W0 entrega «schema + `lib.sh`», e nenhum dos dois é escrevível sem decidir como o bash lê o manifesto. Recomendação: não usar TOML — usar um formato que o shell e o `python3` leem sem parser (linhas `chave<TAB>valor`, no molde de `scripts/delivery-routes.tsv`, que já tem 3 leitores), ou manter `ceremony.toml` e ler SEMPRE via `python3 -c` (stdlib ≥ 3.11 tem `tomllib`; ≥ 3.9 não — e o repo é 3.9+).
2. **OQ-5:** congelar o instrumento e comparar igual-com-igual, OU corrigir e re-medir a base. Não há terceira opção honesta; o AC-4 depende da escolha.
3. **OQ-1 (resto):** número do ADR próprio e wave da emenda ao ADR-010.
4. **OQ-2:** ordem de migração dos 5 packs — que passa a ser também a ordem de corte da W2 em subwaves (R-VP7).
5. **Novo — OQ-6:** registro do toolkit nos gates existentes (raízes do `check-ceremony-script.py`, manifesto ADR-192). Sem decisão, R-VP1 e R-VP5 permanecem.
6. **Novo — OQ-7:** contrato `--describe` (quem escreve, para quais derivadores, e o que acontece com pacotes que não o tiverem).

## Contagem

BLOQUEANTES: **4** (R-VP1, R-VP2, R-VP3, R-VP4). P2: 4. P3: 2.
