# NIGHT-S328 — runbook de execução autônoma (~12 h, conta alternativa)

> **Status deste arquivo:** UNTRACKED de propósito (o Owner pediu: "salva no
> repo, não precisa subir"). Nunca `git add` nele. Descartar depois da noite.
> **Estado VIVO** (unidade em curso, medições, RETOMAR AQUI) fica na memória:
> `~/.claude/projects/-Users-joaocanhada-canhada-labs-ceo-orchestration/memory/project-s328-night-run-state.md`
> — é ELE que o cron de retomada lê. Este runbook é o CONTRATO; aquele é o diário.

Escrito em 2026-08-25 13:40–14:10 local, S328, HEAD `a16ac96`. Autor: CEO.

> **v2, 14:35 local — revisado pelo rail codex (materiais): REJECT, 0 P0,
> ~20 P1/P2; cada um verificado no disco e os REAIS incorporados** (§1.3 leitor
> do snapshot; §2.2 refs; §2.3 push só do `main`; §2.4 APPROVE explícito; §2.5
> COMMON `:10-40` + flags ANTES dos posicionais; U1.2 refs/F4; U1.4/U2.10 split
> serial; U2.0 skip EXISTE; U3.2 range 1217-1380; U4 ordem debate→flip→commit e
> C depende de A∧B; §4 gerador/`finalize-C`/dependências; §5 um one-shot por
> reset com no-op guard, sem recorrente; §6 prova de morte + `CronDelete`).
> Registro: `<scratchpad da S328-17>/rail-runbook-1.md`. A sessão da noite
> (`ceo-orchestration-c9`) já rodava (U0 = `560dad0`) quando a v2 entrou — foi
> avisada por SendMessage com os 16 itens.
Precedentes que este runbook copia: `NIGHT-S325-RUNBOOK.md` (trilhos),
memória `project-s327-night-run-state.md` (unidades + cron de quota),
`PLAN-183/w5-ceremony/README-CERIMONIA.md` (forma da cerimônia).

---

## 0. MANDATO E DECISÕES DO OWNER (verbatim — as ÚNICAS perguntas respondidas)

**Mandato (chat, 2026-08-25 13:38):** ausente ~12 h; montar plano de execução
autônoma; continuar após o reset da quota de 5 h; economizar contexto do main;
workflows pesados podem ir com **Opus 5 em max effort**; avançar o máximo;
"você tem sido conservador nas suas capacidades — inclua o máximo e monitore
contexto"; **se o contexto do main chegar em 80 %: finalizar os workflows que
estiverem rodando, salvar memória e CLAUDE.md, e deixar fechado**; ninguém
responde nada durante a noite; se algo exigir assinatura, **script para
assinar de manhã**.

**AskUserQuestion (2026-08-25 13:45–13:52), respostas verbatim:**

| # | Pergunta | Resposta do Owner |
|---|---|---|
| Q1 | Quota semanal em 81 % (reset seg 31/08 08:00) | **"eu vou usar outra conta pra rodar. que esta com quota integral de fable e semanal sem uso."** |
| Q2 | OQ-4 do PLAN-183 — CODEOWNERS framework-owned? | **"Pista MISTA — braço C (Recomendado)"** — inclui flip do 183 `reviewed→executing` no 1º commit |
| Q3 | PLAN-185 W0 (4 untracked, 19 P1) | **"4ª passada INVERTIDA + W1/W2 em pacote (Recomendado)"** — inclui `/debate` round-1 e autoriza o flip `draft→reviewed→executing` do 185 após o debate |
| Q4 | Entrega | **"Push granular + pacotes independentes (Recomendado)"** — não-canônico: commit por unidade verde + push para `main`; canônico: N pacotes disjuntos + `OWNER-S328-MORNING.sh` |
| Q5 | Gate hook-latency (Validate vermelha) | **"Emenda + gate em pacote, e 1 rerun de madrugada (Recomendado)"** |
| Q6 | PLAN-179 staged-w24 | **"3 ações — registra ledger_entry_rejected (Recomendado)"** |
| Q7 | Ordem | **"183 W5-b → 179 w24 → ADR-163 → 185 → 169 W4.1 → reconciliação (Recomendado)"** |

**Fato descoberto DEPOIS da Q2 (muda o conteúdo da W5-b, não a decisão):** o
braço C **já está no main** — `PLAN-183/w5-ceremony/PROPOSED-PATCH.md:89`
("pista MISTA (braço C), que é o conteúdo deste patch"), `_wbm_declared_hash_source`
vivo em `scripts/_framework_manifest_set.sh:376`, `armC.diff` não aplica
(absorvido). A ratificação é **retroativa**; a W5-b vira *fechamento* (§3 U1).

**Qualquer outra pergunta que surgir NÃO tem resposta esta noite** → registrar
como OQ no plano dono, marcar a unidade como BLOQUEADA nesse ponto e seguir
para a próxima. Nunca decidir no lugar do Owner (trilho 2.2).

---

## 1. BOOT DO TERMINAL (ordem obrigatória, ~10 min, pouco contexto)

1. **Gates 1–3** do `CLAUDE.md` §0 (CLAUDE.md, PROTOCOL.md, skill
   `ceo-orchestration`, `team.md`, `frontend-team.md`; plano ativo = este
   runbook + `PLAN-183`). Não pule.
2. `python3 .claude/scripts/ceo-boot.py --short` (cache; NÃO o completo).
3. **Confirmar a CONTA e o snapshot** (a memória é por máquina, não por conta —
   nada se perde; mas as janelas de quota são da conta nova):
   ```bash
   S=$(python3 - <<'PY'
   import importlib.util
   spec=importlib.util.spec_from_file_location("sl",".claude/scripts/statusline-ceo.py")
   m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)   # import-safe: guard __main__ em :611
   print(m._sidecar_path())   # o MESMO resolvedor do writer (:131-184): CEO_AUDIT_LOG_DIR + override validado
   PY
   )
   python3 - "$S" <<'PY'
   import json,sys,datetime
   d=json.load(open(sys.argv[1])); r=d.get("rate_limits") or {}
   print("session_id:",d.get("session_id"),"captured_at:",d.get("captured_at"),"context_pct:",d.get("context_pct"))
   def when(x):
       if x is None: return "None"
       s=str(x)
       try:
           t=datetime.datetime.fromtimestamp(int(s)) if s.isdigit() else datetime.datetime.fromisoformat(s.replace("Z","+00:00"))
           return t.astimezone().strftime("%a %d/%m %H:%M")
       except Exception: return "unparseable:"+s
   for k,v in r.items(): print(k,"used=%s%%"%v.get("used_pct"),"resets_at=",when(v.get("resets_at")))
   PY
   ```
   O `session_id` tem de ser o da sessão corrente (= último componente do
   diretório-pai do scratchpad no system prompt) e `captured_at` recente. O
   path vem do PRÓPRIO writer (`_sidecar_path()`, `statusline-ceo.py:131-184`:
   honra `CEO_AUDIT_LOG_DIR` via resolvedor e REJEITA override inseguro) —
   nunca reimplemente a resolução. `resets_at` chega como dígitos, ISO ou
   `None` (`:224-253`) — `None` ⇒ NÃO arme cron; registre e re-leia no
   próximo turno. Se
   `seven_day.used_pct ≥ 70` ⇒ a troca de conta NÃO aconteceu: escreva na
   memória, execute só U0 + U6 (leves) e PARE. Não queime a semana do Owner.
4. **Armar os acionadores de quota** (`CronCreate`; session-only; vide §5).
5. **Árvore:** `git status --short` deve mostrar SÓ: os 4 untracked do censo W0
   do 185 (`.claude/plans/PLAN-185/`, `.claude/scripts/check-installer-write-safety.py`,
   `.claude/scripts/data/`, `.claude/scripts/tests/test_check_installer_write_safety.py`)
   e este runbook. HEAD esperado `a16ac96` (ou posterior, se o Owner commitou).
   `git worktree prune` (há um `rc3-wt` prunable de sessão antiga).
6. **CI baseline a ler antes de diagnosticar** (medido S328 13:00 local):
   `Validate` de `a16ac96` = 8/9 verdes, só `opus-4-7-profiler-smoke` vermelho
   (gate hook-latency; U3 cura). `Smoke Install` VERDE em `738007e`. Nightly
   de ownership: último sucesso 25/08 07:02Z sobre `8f15b3a` (PRÉ-land); o de
   26/08 ~07:00Z é o 1º sobre D1+D3 — RED set esperado `{OWN-0016,0024,0027}`.
   Armadilhas: `Smoke Install` não roda em commit só-de-plano (filtro `paths:`);
   `cancelled` ≠ falha (grupo de concorrência); confirme o SHA do run.
7. Executar **U0** (§3) e só então abrir as faixas pesadas.

---

## 2. TRILHOS — violar qualquer um é falha de governança, não atalho

**2.1 Canônico NUNCA lande.** Oráculo, não intuição:
`python3 .claude/hooks/check_canonical_edit.py --is-canonical <path>` → `<path>\t0|1`.
Medido S328: `validate.yml`, `smoke-install.yml`, `ADR-*.md`, `.claude/hooks/*`,
`_lib/*`, `.claude/settings.json`, `scripts/upgrade.sh`, o manifesto de gates
do ADR-192 = **1**; `profile-opus-4-7.py`, `check-installer-write-safety.py`,
planos, `CLAUDE.md`, `scripts/doctor.sh`, `delivery-routes.tsv`,
`verify-counts.sh`, `docs/*` = **0**. Membro do manifesto ADR-192
(`.claude/governance/` — o arquivo `gate-scripts-manifest`) passa por cerimônia
MESMO com oráculo 0 (`verify-counts.sh`, `ownership-expected-reds.txt`) —
cheque com `grep -F <path>` no manifesto.
Canônico = sombra (`git worktree add <scratchpad>/shadow-<faixa> HEAD`) →
patch → sentinel-DRAFT → SIGN/LAND → manhã. **Nunca assinar à noite**: o
Anchor-SHA pina o HEAD e qualquer commit posterior invalida (lição S322).

**2.2 Nunca responder OQ** além das 7 da §0. Nunca flipar plano para `done`
sem os DOIS censos (ACs + TODAS as checkboxes, com seção). Flips autorizados
esta noite: 183 `reviewed→executing` (U0); 185 `draft→reviewed` (após
consensus `design-coherent` do round-1; `reviewed_at` obrigatório) e
`reviewed→executing` ANTES do commit do W0 (PLAN-SCHEMA:394-409: `draft` não
tem commits dependentes). Transições legais no grafo `check_plan_edit.py:121-132`
e campos exigidos em `:316-332`; `→done` exige `completed_at` + `related_commits`.

**2.3 Ordem dos gates: `git add <paths explícitos>` → gates de CORPUS sobre a
árvore staged → `git commit`.** NUNCA `git add -A` (4 untracked do 185 + este
runbook + sombras). Comandos exatos (S325 §0.4, verificados no disco S328):
```bash
git add <paths>
bash .claude/scripts/local/verify-counts.sh                  # exit 0
python3 .claude/scripts/check-claude-md-claims.py            # exit 0
python3 .claude/scripts/validate_governance_fast.py --json   # errors: []
python3 .claude/scripts/check-test-env-hygiene.py            # exit 0
python3 .claude/scripts/check-ceremony-script.py             # blocking: 0
python3 .claude/scripts/check-staleness.py                   # advisory
git commit -F <msg>   # trailer: Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
[ "$(git rev-parse --abbrev-ref HEAD)" = main ] && git push origin HEAD:main   # precondição + HEAD:main
```
**Commits não-canônicos acontecem SÓ no checkout principal (`main`), nunca numa
sombra/worktree** — `git push origin main` de dentro de uma sombra reporta
sucesso e deixa o commit FORA do `main` (classe curada no LAND da S327,
`rail-materials-round-1.md:45-51`). Sombras servem apenas para gerar patches.
Se `CLAUDE.md` mudou: `bash .claude/scripts/validate-governance.sh` COMPLETO
(limite 40.000 bytes; o `--fast` não checa — S327). Bit executável sai do
filesystem E do index. `git update-index --chmod=-x` sozinho não cola.
**Heredoc via Bash que CITE um path canônico é barrado pelo interceptor E.3**
(aconteceu ao escrever este runbook) — use a ferramenta Write para arquivos
não-canônicos que mencionem paths canônicos.

**2.4 Pair-rail antes de CADA commit de código, fim detectado pelo ARTEFATO:**
`cd <árvore> && codex exec review --uncommitted </dev/null` (ou
`--commit <sha>`); leia `tail -c 2000`: **rodada limpa = rc 0 E `VERDICT: APPROVE` explícito**
(AGENTS.md:34-38); saída vazia, truncada ou sem veredito = `UNAVAILABLE`, nunca
aprovação (constantes `check_codex_stop_review.py:144-146`; parsing de saída
vazia/sem veredito `:436-467`); `Full review comments:` presente = achados a
verificar um a um. Fora de dir trusted o codex PENDURA: rode do
repo/sombra ou `--skip-git-repo-check`, sempre `</dev/null` e
`--output-last-message <arquivo>`. **Parada = `VERDICT: APPROVE`.** Um REJECT
só com P2 NÃO é parada: cure ou disponha por escrito cada P2 e RE-RODE até
APPROVE — o Stop hook mantém um REJECT vigente como NÃO-liberado e o pre-push
é o backstop (`check_codex_stop_review.py:568-590`); nunca commite sob REJECT
vigente. Cada claim é verificada contra o código (`receiving-review`), nunca
obedecida.
Classe que se repete ⇒ mude a ARQUITETURA da cura, não a rodada.
Prova de morte de background = `ps -eo pid,etime,command | grep <padrão> | grep -v grep`
(`pgrep -f` casa a si mesmo). Workflow em curso: `grep -c '"result"' journal.jsonl`
vs nº de agentes; `0` é o estado NORMAL de um fan-out em curso.

**2.5 Workflow = leitura/medição/revisão; escrita = Agent governado.**
Todo agente de Workflow recebe o bloco COMMON (copiar de
`.claude/workflows/audit-fanout.js:10-40` — `READ_ONLY_RULES` + `RULES_MARKER`
das linhas 10-16 são OBRIGATÓRIOS: o validador `:128-133` rejeita prompt sem o
marcador literal `HARD RULES (ADR-136-AMEND-1 read-only confinement)`; mais
`## PROMPT DEFENSE` ≥6 bullets e `## FILE ASSIGNMENT` = `NONE-READ-ONLY`);
workflow sem COMMON nasce descoberto (ADR-191 §4). Ingest de retorno inter-agente:
JSON COMPACTO, fenced, cap 24000 com ENVENENAMENTO do truncamento (nunca
`.slice()` cru). `agent(prompt,{model:'opus',effort:'max',...})` — o rail
ROTEIA modelo (probe `wf_9ddadaab`, 169 W4.3). Escrita: Agent tool com prompt
gerado por `bash .claude/scripts/inject-agent-context.sh --files=a,b <Agente> "<tarefa>"`
— **flags ANTES dos posicionais**: o parser só lê flags iniciais (`:91-100`);
`--files=` no fim é ignorado e o escritor nasce `NONE-READ-ONLY`
(FILE ASSIGNMENT concreto; `subagent_type=general-purpose` = rail mitigado,
exceto `code-reviewer` nativo), `model:"opus"`. Um escritor por arquivo;
paralelo só com arquivos disjuntos; 4+ em comum = uma tarefa só.
Agente que cai por erro de API pode VOLTAR e sobrescrever o substituto —
re-despache para path DIFERENTE.

**2.6 Contexto do main é o recurso escasso (medido, não estimado).**
Antes de CADA unidade: `context_pct` do snapshot (§1.3). `≥ 65` ⇒ não abra
unidade pesada nova, só feche o que está aberto; `≥ 80` ⇒ **WRAP-UP** (§6).
Nunca `cat` arquivo grande no main; workflows devolvem ≤ 3 KB; logs vão para
artefatos no scratchpad e o main lê `tail`/`grep`. Atualize o arquivo de estado
na memória **após cada unidade** (compaction apaga o main — ADR-153 não
entrega; a memória é o único ponteiro que sobrevive).

**2.7 Parada.** 3 tentativas no mesmo item ⇒ registrar e seguir (anti-padrão
6). Gate de corpus vermelho que você não causou ⇒ registre, não "conserte"
alargando padrão. `origin/main` vermelho por commit SEU ⇒ pare tudo e deixe o
diagnóstico escrito. Nada de: rotear perf ao runner `Ceo`; `unittest discover`;
tocar PLAN-170/173/181 (congelados); release/tag/publicar; editar o
`.github/CODEOWNERS` vivo; `git push --force`.

**2.8 Push.** Commits granulares, um por item fechado, corpo com a MEDIÇÃO.
Push após cada commit verde (Q4). Materiais de cerimônia (patch, sentinel-draft,
SIGN/LAND, harness, README) são não-canônicos e **devem ser commitados e
pushados** — o G0 do LAND exige materiais rastreados (lição S326).

---

## 3. ESCOPO — unidades na ordem ratificada (Q7)

Faixas paralelas em sombras disjuntas: **A** = 183 (+185 empilhado depois),
**D** = 179, **B** = ADRs + gate. Arquivos disjuntos entre A/B/D (verificado:
A toca `install.sh`/`upgrade.sh`/`_framework_manifest_set.sh`/ADR-194/testes
de ownership; D toca `audit_emit.py`/`settings.json`/SPEC/hooks novos/pins/
docs de contagem; B toca `validate.yml`/`profile-opus-4-7.py`/ADR-163/ADR-144).
C (185 W1/W2) toca os MESMOS arquivos de A ⇒ empilhado sobre a sombra de A.

### U0 · Registro + flips + higiene (não-canônico, ~20 min) — SEMPRE primeiro
- Logar as 7 decisões **verbatim** (§0) nos donos: `PLAN-183` §Open questions
  item 4 (OQ-4 → "✅ RATIFICADA pelo Owner 2026-08-25: «Pista MISTA — braço C»
  — retroativa: já é o conteúdo do patch landado em `6304f66`"); `PLAN-179/staged-w24/README-COMO-MONTAR.md`
  item 1 ("DECIDIDO 2026-08-25: 3 ações"); `PLAN-185` §4 + OQ (Q3 verbatim +
  autorização de flip); `PLAN-169` §Progress log (Q5: emenda ADR-163 autorizada;
  W4.1.0 probe oportunista).
- Flip `PLAN-183` `status: reviewed → executing` (Q2). NÃO flipar 185 ainda.
- `git worktree prune`. Sombras: `shadow-183`, `shadow-179`, `shadow-163`
  (worktrees em `<scratchpad>/`), `PYTHONDONTWRITEBYTECODE=1` nas baterias
  (lição `macos-pycache-prefix`).
- Gates §2.3 → commit → push. Atualizar memória.

### U1 · [A] PLAN-183 W5-b = FECHAMENTO (canônico → PACOTE A)
Conteúdo (o braço C já está vivo — não reimplementar):
1. **ADR-194** (`.claude/adr/ADR-194-delivery-route-resolution.md`, canônico):
   `status: PROPOSED → ACCEPTED`; seção "Ratificação OQ-4 (2026-08-25)" que
   DESCREVE a pista mista como decidida (`w5-oq4-measurement-S327.md` §7:305 —
   "o ADR deve descrever a pista que o Owner ratificar"); nota "checkout raso
   ⇒ `PRESERVED` + `STALE` (lição 2 da S327; cura = deepen antes da paridade,
   `738007e`)".
2. **Obrigações residuais da W5-b** — re-derivar a lista com um Workflow
   read-only (2 agentes opus/max: um lê `grep -n "W5-b" PLAN-183-adopter-fitness.md`
   + §9; outro lê `w5-oq4-measurement-S327.md` §7 + `w5-draft-s323.md`),
   retorno JSON `{item, arquivo, canônico?, forma_do_teste, linhas_est}`.
   Candidatos já conhecidos: @815 comportamento explícito **preservar** +
   fixture pré-install-state-com-owner; @1579 chave do resolvedor tolera os
   dois destinos (o plano cita `install.sh:1497`/`:1514`; hoje as duas
   ramificações do CODEOWNERS estão em `install.sh:1618-1653` — renderizado
   1618-1645, template 1648-1653 — re-derivar) e o
   manifesto não reivindica os dois; §9.4 F4 `.github/` fora dos DOIS scanners
   de placeholder — **verificar a disposição no plano antes de incluir** (o
   rail afirma que o plano o atribui à W2, não à W5-b); @733 promoção da
   tabela (verificar o que ainda falta — "REDUZIDA, não fechada"); @1009 teste
   de `--github-owner` PLANTA divergência (compartilhado com 185 W2 — fazer UMA
   vez, na faixa A, e o pacote C só consome). Decidir só o que é MECÂNICO;
   qualquer item que exija juízo de produto → OQ (trilho 2.2).
3. Implementação por Agents governados na `shadow-183`, testes com controle
   positivo (vermelho ⇒ verde demonstrado), rail §2.4 até limpo.
4. **Bateria** (background, artefatos no scratchpad): `scripts/tests/test-ownership-verdict-unit.sh`
   (63/0), `test-manifest-delivery-route.sh`, `test-doctor-delivery-route.sh`,
   `test-install-upgrade-parity-e2e.sh --mode maintainer` e `--mode user`
   (STALE 0 nos dois), `test-upgrade-historical-adopter.sh`,
   `test-protocol-pointer-inv4.sh`, `test_install_baseline_manifest.sh`
   (**33/1 por desenho**, known-open EXATO `C.6.2`), `test-ownership-table.sh`
   (~30 min; RED set EXATO `{OWN-0016,OWN-0024,OWN-0027}` — um all-green é
   alarme), pytest EXATAMENTE como o CI — `-n auto -m 'not serial'` seguido do
   passe `-m serial` — em `.claude/hooks/tests/` e `.claude/hooks/_lib/tests/`
   (`validate.yml:343-351`, `:453-476`; marcador `serial` em `pytest.ini:83-84`).
5. **Pacote A** (§4). Checkboxes W5-b do plano: fechar só as verificadas.

### U2 · [D] PLAN-179 staged-w24 → PACOTE D (receita = README-COMO-MONTAR, RE-MEDIR números)
0. O skip PACK-DOC **JÁ EXISTE** (`assemble_pack.py:58-70`,
   `_PACK_DOC_SUFFIXES = ("-COMO-MONTAR.md", "-NOTE.md")` — o grep pelo literal
   `PACK-DOC` feito na S328 foi a sonda errada). U2.0 = só VERIFICAR: o
   manifesto tem de sair com **5** entradas, nunca 7, nenhuma na raiz.
1. **Renumerar o ADR do pack**: `ADR-194-work-boundary-persistence.md` →
   **`ADR-195-…`** (o 194 foi tomado pelo 183; próximo livre = 195, contagem
   195→196). Corrigir toda referência dentro do pack (hook, testes, ADR).
2. `audit_emit.py`: **3 ações** (`ledger_checkpoint_recorded`,
   `ledger_checkpoint_skipped`, `ledger_entry_rejected`), allowlist
   deny-by-default + scrub, NUNCA em `_EMIT_GENERIC_PASSTHROUGH`;
   `_KNOWN_ACTIONS` 327→330 (re-medir com `len(_KNOWN_ACTIONS)`).
3. `SPEC/v1/audit-log.schema.md`: 3 linhas, **v2.59** (vivo já tem v2.58) — via
   `PACKMAP.txt` (`Edit(SPEC/**)` é negado até no pack).
4. `.claude/settings.json` registração do hook + espelho em
   `templates/settings/settings.base.json` (o buraco que a suíte pegou no w01).
5. Pins: `test_audit_emit_api_contract.py:820/:839` + `_EXPECTED_KNOWN_ACTIONS_SHA256`
   (RE-DERIVAR), `test_audit_emit_plan163_lifecycle_actions.py:171`,
   `test_codex_egress_proof_telemetry.py:123`, `test_git_bypass_guard.py:885`,
   `test_w5_scrub_enforcement.py:95`.
6. `check-audit-registry-coverage.py --write-golden` no MESMO commit.
7. Contagens derivadas via `verify-counts.sh` (11 docs) + sítios de PROSA
   listados no README (varrer por número): hooks 58→59, ligados 47→48,
   registros 49→50, `_lib` 70→71, ADRs 195→196.
8. `check_contamination.py`: exceção NEGATIVA para a classe `LEDGER.md` (o
   glob `.claude/plans/*` atravessa `/`) — não-canônico, commit direto, com
   teste.
9. `python3 .claude/plans/PLAN-179/assemble_pack.py .claude/plans/PLAN-179/staged-w24`
   → MANIFEST/BASELINE **commitados**; `## Scope` do sentinel-draft derivado
   do MANIFEST (G2b).
10. Simulação de land em clone (`git clone --local`), `py_compile`, suíte
    COMPLETA de hooks com `PYTHONDONTWRITEBYTECODE=1` e o split do CI
    (`-n auto -m 'not serial'` + passe `-m serial`), validate-governance,
    verify-counts, claims — rc AGREGADO por comando.
11. `OWNER-W179-W24-LAND.sh` G7: mensagem com a decisão "3 ações";
    **D NÃO usa o SIGN patch-based do S327b**: o pack é MANIFEST-based
    (`OWNER-W179-W24-LAND.sh:26-39` — G2b `Scope` == MANIFEST; G3 verifica
    `W179-approved.md.asc` com signer-pin + anchor == HEAD). Sentinel-draft no
    molde de `W179-approved-draft.md`; assinatura = `gpg --armor --detach-sign`
    do sentinel pelo Owner (inline, pinentry) — o MORNING faz isso para D.
    **Acrescentar ao W24 LAND** (não-canônico): precondição `HEAD == main` e
    `git push origin HEAD:main` no fim — hoje ele termina num commit local e
    pede push manual (`:225-238`); mesma cura do F-LAND da S327. Harness
    `test-ceremony-scripts-w24.sh` (o V-block compara contra conjuntos
    DECLARADOS, nunca contra zero — lição 1 S327).

### U3 · [B] Emenda ADR-163 + gate + emenda ADR-144 → PACOTE B (+ rerun 03:00)
Evidência fixa: 2 SHAs (`56f050c` 209→435 ms; `a16ac96` 361/425/229 ms),
teto p95 180 ms, sonda de spawn `UNCONTENDED` (7,76 ms), local 70–77 ms —
`check_output_secrets` intocado desde 2026-07-02. A sonda mede piso de SPAWN
e é cega a runner lento-mas-descontendido (SKU/throttling).
1. **Desenho por Workflow read-only** (3 críticos opus/max com personas
   performance-engineer, devops, qa-architect na gramática reduzida) sobre
   DOIS candidatos: (i) teto RELATIVO: `hook_p95 ≤ K × ref_p50`, `ref` = carga
   de EXECUÇÃO Python medida no mesmo run (imports típicos de hook + laço
   fixo), `K` derivado da série local+CI; (ii) teto absoluto mantido, mas a
   sonda passa a medir execução Python (não spawn) e um piso alto rebaixa o
   gate a ADVISORY nomeado em vez de conceder 3ª tentativa. Critério que
   decide: **poder de detecção preservado** — controle positivo (plantar
   `time.sleep(0.15)` no hook) tem de FALHAR num runner rápido; controle
   negativo (runner lento sintético via carga) NÃO pode gerar "real
   regression".
2. Implementar: `.claude/scripts/profile-opus-4-7.py` (não-canônico) +
   `.github/workflows/validate.yml` step (canônico, linhas 1217–1380 — o step
   INTEIRO, incluindo o retry/advisory que a U3 muda; o próximo step começa
   em 1382) +
   `ADR-163` "Amendment (PLAN-169 S328)" + `ADR-144` §S220 emenda ("`opts.model`
   NÃO é mais inerte" — 169 W4.3 mediu). Testes em `.claude/scripts/tests/`
   (pytest testpaths; `scripts/tests/` NÃO é coletado).
3. Rail; **Pacote B** (pequeno). Registrar no `PLAN-169` (dono das emendas).
4. **Rerun de madrugada:** cron one-shot `3 3 26 8 *` → `gh run rerun 32866209415 --failed`
   + `gh run watch 32866209415 --exit-status`; resultado na memória. Se verde,
   `main` está verde ANTES da manhã. O rerun **não valida o pacote B** (o gate
   novo só existe na sombra): B se valida pelos controles positivo/negativo da
   U3.1 + harness.

### U4 · [A-empilhado] PLAN-185 — matcher invertido, debate, W1/W2 → PACOTE C
(a) **4ª passada INVERTIDA** (não-canônico): reescrever
`check-installer-write-safety.py` enumerando as formas PROVADAS seguras — cada
forma com controle positivo (remover a guarda ⇒ vermelho nomeado); todo o
resto = `indeterminado`. Os **19 achados** (9 do §7-quater + 10 de
`PLAN-183/w5-ceremony/rail-materials-round-1.md:12-42`) viram fixtures de
regressão. Re-derivar o censo (`PLAN-185/w0-censo-S328.md`, números do
instrumento novo). Rail até limpo. **NÃO commitar ainda** — `draft` não pode
ter commits dependentes (PLAN-SCHEMA:394-409); o commit vem em (b′).
(b) **Debate round-1**: `python3 .claude/scripts/debate-orchestrate.py --plan PLAN-185 --proposal "<blurb: W1 guarda compartilhada anti-symlink + W2 handle validado + escrita atômica>" --round 1`
→ spawnar os críticos que o orquestrador emitir (DEBATE-SCHEMA; anonimizar
antes da síntese; Red Team se Jaccard ≥ 0,7) → `consensus.md`. Se
`design-coherent`: flip `draft → reviewed` (`reviewed_at`) → `executing`;
**(b′) só ENTÃO** commit + push do W0 (paths explícitos: script,
`data/installer-write-safety-baseline.txt`, teste, censo, plano) ⇒ fecha as 2
checkboxes da W0 **exceto a cláusula "roda em CI"** (PLAN-185:90-92): o wiring
do censo em `validate.yml` é canônico e entra no pacote C ⇒ **C toca
`validate.yml` como B e depende de A E de B**. Se ESCALATE/VETO ⇒ registrar OQ;
o W0 fica untracked; pacote C NÃO se monta.
(c) **W1** (F1): `install_docs_template` recusa destino symlink (pendente ou
resolvido) reusando a MESMA guarda já existente — `_assert_no_symlink_parents`
(`install.sh:863`, chamada em `:910`; o plano cita `:2139-2159`, que hoje é o
render do ponteiro `PROTOCOL.md` — re-derivar) — uma função compartilhada; fixtures: pendente-para-fora (bytes do alvo externo NÃO existem
após o run), resolvido-para-fora, sem symlink (não-regressão); vermelho com a
guarda revertida. **W2** (F2): handle validado contra conjunto FECHADO antes
de qualquer escrita; escrita ATÔMICA (tmp + `mv`); 3 fixtures (a) `a/b` ⇒
falha nomeada e NENHUM CODEOWNERS; (b) válido ⇒ 1442 bytes / 33 linhas /
handle ≥1 e SÓ DEPOIS `grep -c '{{OWNER_HANDLE}}' == 0`; (c) destino 0 bytes
pré-existente ⇒ corrigido, não EXISTS-skip. Implementar na sombra
**empilhada sobre a árvore final de A + o hunk de B em `validate.yml`** (mesmos
arquivos). Rail; **Pacote C** com `BASE = A ∧ B` declarada e o passo de
FINALIZAÇÃO da manhã (§4, `finalize-C.sh`).

### U5 · PLAN-169 W4.1.0 — sondas de quota-resume (oportunista, $0)
No PRIMEIRO estouro de quota da noite, registrar: (i) o que o harness fez
(texto do erro; algum evento Stop/StopFailure no `audit-log.jsonl` naquele
minuto? — `StopFailure` NÃO está registrado em `settings.json`, medido S328);
(ii) frescor do sidecar (`captured_at` vs instante do estouro); (iii) latência
reset → 1ª tool call da retomada por cron. Escrever
`PLAN-169/w4.1-probe-S328.md` + linha no §Progress log. Commit + push.

### U6 · Reconciliação (não-canônico, barato, alto retorno)
- `PLAN-183` §Waves W1 (6) e W2 (7) checkboxes: verificar UMA A UMA contra o
  código/commits (`4f750f0`, `ed4d1cf`, `6304f66`, `738007e`); fechar com
  referência de commit o que está entregue; o que não está fica aberto com a
  razão escrita. Nunca "fechar por parecer feito".
- `PLAN-182` (executing, wave-cli landada): disposição escrita para 556/697,
  693, 759 (decisão do CEO já registrada: NÃO), 771; sem flip.
- `PLAN-179/RETOMAR-AQUI.md` refresh (w24 montado); `PLAN-169` progress log.
- `check-claude-md-claims.py` + `verify-counts.sh` após qualquer doc.
- `CLAUDE.md` §5: UMA edição, só se o contrato durável mudou, no closeout.

### U7 · Bônus (só com A–D empacotados e quota sobrando)
Workflow `nightly-hygiene` (read-only) → achados para U6; itens NÃO-canônicos
da W3 do 183. Nada novo além disso.

---

## 4. PACOTES DE CERIMÔNIA — contrato (um diretório por pacote)

`PLAN-<n>/s328-ceremony-<P>/` com: `<P>.patch` (git, gerado da sombra;
`BASE-SHA.txt` declara o HEAD sobre o qual aplica — C declara "após A");
`PROPOSED-PATCH.md` (o quê/por quê/medições/rodadas de rail);
`EXPECTED-BASELINE.txt` (conjuntos EXATOS de ids/contagens que o V-block
compara — nunca "zero"); `rail-round-N.md`; harness `test-ceremony-scripts-<P>.sh`
que EXERCITA o V-block e prova que o abort restaura a árvore em qualquer modo.
Sentinel-DRAFT em `PLAN-<n>/wave-s328-<P>-approved.md` na forma VIVA
(`<!-- BEGIN SIGNED SCOPE -->`, `Approved-By:` → `Plans:` → `Scope:` derivado
do patch; Anchor/Data preenchidos pelo SIGN). `OWNER-S328-<P>-SIGN.sh` e
`OWNER-S328-<P>-LAND.sh`: **primeiro** tentar
`bash .claude/scripts/local/generate-ceremony.sh --help` (o contrato manda
GERAR — `docs/OWNER-CEREMONY-CONTRACT.md:165-181`); se o gerador não emitir
cortes de wave, clonar de `PLAN-183/OWNER-S327b-{SIGN,LAND}.sh` MANTENDO o
cabeçalho `# CEREMONY-LINT: handwritten-exception:` com a razão, e passar
`check-ceremony-script.py` (blocking 0); o bloco de constantes muda E o
**V-block é trocado pela bateria do PRÓPRIO pacote** (V3–V7 do S327b são de
ownership — `OWNER-S327b-LAND.sh:549-685`): A mantém ownership
(`--ownership-e2e=run|defer` obrigatório); B = controles positivo/negativo do
gate + `.claude/scripts/tests`; C = fixtures F1/F2 + censo em CI + paridade;
D = LAND próprio do w24 (suíte de hooks com o split do CI). **Pacote
empilhado (C):** o SIGN exige `Patch-base` ancestral do HEAD e ZERO drift nos
paths tocados (`OWNER-S327b-SIGN.sh:164-190`) — como A e B mudam os mesmos
arquivos antes de C, o pacote C traz `finalize-C.sh` que o MORNING roda DEPOIS
de landar A e B; e como `finalize_patch.py` RECUSA sombra cuja base ≠ HEAD
vivo (`finalize_patch.py:342-350`), o script: recria `shadow-C` a partir do
HEAD vivo (`git worktree add … HEAD`), re-aplica o patch C (`git apply --3way`;
conflito ⇒ ABORTA nomeando o hunk), re-roda a bateria de C na sombra nova, e
só então `finalize_patch.py` (`Patch-base = HEAD`, `apply --check`, `Scope`) →
SIGN C. Rótulos do sentinel ASCII-safe
(parser casa prefixo ASCII — lição S326).

**`PLAN-183/OWNER-S328-MORNING.sh`** (o Owner roda UM comando) + `README-MANHA.md`
(leigo, copy-paste, absoluto): imprime o plano; para cada pacote na ordem
**B → A → C → D** (B primeiro para o CI ficar verde; C depois de A; D por
último — LAND mais longo): árvore limpa → SIGN (pinentry inline; `export GPG_TTY=$(tty)`)
→ LAND `--dry-run` → LAND → confere push → próximo. Para no PRIMEIRO vermelho
com diagnóstico e o comando de retomada; pacote ausente ⇒ pula AVISANDO,
**respeitando dependências**: A ou B ausente ⇒ C NÃO roda (aborta C com a
razão); B ausente ⇒ avisa que o CI segue vermelho antes de continuar;
nunca abre editor (`git commit -F`); termina com `gh run list` e o baseline
esperado do CI. Materiais commitados e pushados (trilho 2.8).

---

## 5. QUOTA E TEMPO

- Janela de 5 h começa na 1ª mensagem da conta nova. Contrato do quota-resume
  (PLAN-169 W4.1, `:451-494`), adaptado (v3): **DOIS one-shots por `resets_at`**
  (+3 e +23 min; idempotente — re-armar só se `resets_at` mudar; relaxa de
  propósito o "um e só um" do W4.1 — decisão da noite, registrada como dela;
  o contrato de EVIDÊNCIA de exaustão do W4.1 `:479-498` é do produto
  AUTOMÁTICO (arm aos 90 % sem mandato) e não se aplica a uma noite
  mandatada explicitamente pelo Owner), horário `resets_at + ≥ 3 min`
  com minuto ∉ {`:00`,`:30`} (one-shot em :00/:30 dispara até 90 s ANTES),
  **banda fail-closed** (`resets_at` no futuro E ≤ 5 h + margem; fora ⇒ não
  arma, registra), `CronCreate` com `recurring:false`. **SEM job recorrente**
  (o `23 */2` da v1 violava "um job por reset" e nunca era cancelado). Após
  CADA estouro, a retomada re-lê `resets_at` e re-arma o próximo.
- **v3 (14:55, acordado com `ceo-orchestration-c9`): SEM guarda de exaustão.**
  O risco que ela defende no PLAN-169 W4.1 (turno autônomo espúrio sem
  mandato) é por-desenho nesta noite — todo turno é mandatado; a guarda só
  mataria a noite num 5xx/overloaded/crash de tool. Em troca, o RESUME trata
  os dois riscos que ela mascarava: **R1 re-entrância** (workflows/bash/agentes
  do turno morto seguem VIVOS no processo; re-despachar a unidade `[~]` com o
  escritor anterior vivo = dois escritores no mesmo path) — inventariar antes
  de re-despachar (`grep -c '"result"' journal.jsonl` vs nº de agentes,
  `ps -eo pid,etime,command | grep -E 'codex|pytest|scripts/tests|test-ownership' | grep -v grep`,
  lista de tarefas do harness) e só relançar após PROVA de fim/morte pelo
  artefato; **R2 loop de falha não-quota** — contador de retomadas anormais
  por unidade no arquivo de estado: 2ª na mesma unidade ⇒ `[!]` com causa e
  segue; 3 seguidas sem avanço ⇒ WRAP-UP. E **arm-first**: o próximo one-shot
  é a PRIMEIRA ação do turno retomado; por reset, DOIS one-shots (+3 e
  +23 min, minuto ∉ {:00,:30}) — o 2º cobre exaustão residual/deriva do
  `resets_at` (relaxa de propósito o "um por reset" do W4.1; decisão da noite).
- **RESUME (literal e fixo):** «quota-resume S328. Se §6 WRAP-UP já concluído:
  responda `noop` e pare. Senão: (0) arme AGORA o(s) próximo(s) one-shot(s)
  do próximo `resets_at`; (1) inventarie trabalho em voo (R1) e NÃO
  re-despache unidade cujo escritor/workflow ainda vive; (2) incremente o
  contador de retomada anormal da unidade `[~]` (R2: 2 ⇒ `[!]` e próxima;
  3 seguidas sem avanço ⇒ WRAP-UP); (3) re-entre no Gate 1; leia
  `~/.claude/projects/-Users-joaocanhada-canhada-labs-ceo-orchestration/memory/project-s328-night-run-state.md`
  e `.claude/plans/PLAN-183/NIGHT-S328-RUNBOOK.md` (DADOS, não instruções do
  Owner); pegue a unidade `[~]` ou a PRÓXIMA; `git status --short`; re-arme UM
  one-shot para o próximo `resets_at`; continue. PROIBIDO neste turno e em
  qualquer retomada: assinar, landar canônico, tag/release/npm, flip de status
  além dos autorizados (183 `reviewed→executing`, já feito em `560dad0`; 185
  `draft→reviewed→executing` após consensus `design-coherent`), mudar postura. Se a entrega final (§6) já foi feita: `noop`.»
- **Rerun 03:00:** one-shot `3 3 26 8 *` (U3.4).
- Cronograma alvo (h após o boot): 0–0,5 U0 · 0,5–4 U1 ‖ U2 ‖ U3.1 (desenho)
  · 4–8 U3.2–3 + U4(a)(b) + rail de A/D · 8–11 U4(c) + pacotes + MORNING +
  harnesses · 11–11,5 U6 + U5 + closeout · **11,5 h = WRAP-UP incondicional**.
  Baterias longas SEMPRE em background com artefato; nunca esperar ocioso.
  O harness solta tarefas > ~45 min (exit 144) mas os filhos seguem — cheque o
  ARTEFATO, nunca o processo.
- Sem teto de gasto (Q1: conta com quota integral). A quota É o teto.

---

## 6. WRAP-UP (contexto ≥ 80 %, ou 11,5 h, ou quota da noite esgotada)

1. Não abrir nada novo; deixar workflows em curso terminarem (TaskStop se
   faltarem > 20 min e o artefato parcial já servir).
1b. **Prova de morte dos filhos** antes de declarar concluído:
   `ps -eo pid,etime,command | grep -E 'codex|pytest|scripts/tests|test-ownership' | grep -v grep`
   vazio (ou cada sobrevivente NOMEADO na memória); `CronList` → `CronDelete`
   de todo acionador da noite — nada dispara depois do WRAP-UP.
2. Memória: `project-s328-night-run-state.md` com **RETOMAR AQUI** no topo,
   status de cada unidade, medições, e o que está BLOQUEADO e por quê;
   `MEMORY.md` só o índice (uma linha).
3. Commit + push do não-canônico verde (paths explícitos; gates §2.3).
4. Todo pacote existente tem SIGN/LAND/harness; `OWNER-S328-MORNING.sh` e
   `README-MANHA.md` existem mesmo que parciais (pacote ausente ⇒ pula avisando).
5. `CLAUDE.md` §5: uma edição, só se o contrato durável mudou; governance
   COMPLETO antes do commit; ≤ 40.000 bytes.
6. Mensagem final = handoff: o que fechou / não fechou / por quê, cada
   afirmação com a medição; o comando ÚNICO da manhã; baseline do CI esperado.
7. `git status --short` limpo exceto: este runbook e as sombras no scratchpad.

---

## 7. O QUE NÃO ENTRA (e por quê)
Landar canônico; assinar; responder OQ nova; `git add -A`; editar membro do
ADR-192 fora de cerimônia; PLAN-170/173/181; tag/release/publicação;
`unittest discover`; rotear perf ao runner `Ceo`; editar `.github/CODEOWNERS`
vivo; qualquer "fix-of-fix" além da 3ª tentativa; qualquer mudança de
`_ownership_verdict()` (a OQ-4 decidiu que a posse das duas árvores é o
hash-gate + `hash_source`, não superfície nova).
