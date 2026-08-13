---
id: PLAN-177
title: rc.4 — curas dos 4 P1 do re-pass GA + 2 patches de triagem S303, com controle positivo em cada gate
status: reviewed
reviewed_at: 2026-08-13
reviewed_by: "Owner — ratificação via AskUserQuestion (S304): 'Ratificar reviewed (Recomendado)' — Frontmatter vira status: reviewed com reviewed_at hoje. W0 executa em seguida (superfícies livres); o pack W1 continua exigindo assinatura GPG do Owner e a tag rc.4 continua sendo do Owner."
created: 2026-08-13
owner: CEO
depends_on: [PLAN-166]
budget_tokens: 100-180k (W0 40-70k; W1 pack+cerimônia 30-50k; W2 re-pass+corte 30-60k)
budget_sessions: 1-2
context_risk: medium
external_wait: "ADR-103: hold de 24h reinicia no corte da rc.4 ⇒ GA no dia seguinte. Cerimônia W1 exige Owner (GPG)."
tags: [release, ci, npm, governance, canonical]
---

# PLAN-177 — rc.4: fechar os 4 P1 do re-pass GA

> **v4.1 (S304).** Codex sobre a v4: 4 P1 + 1 P2, todos aplicados —
> AC-1 nomeia a chave duplicada; W2 exige OWNER-GA-CUT RETARGETADO
> para rc.4 (o script vivo pina RC_TAG/freeze-SHA/evidência da rc.3);
> AC-3 ganha o e2e do dano ORIGINAL (night-mode armado ⇒ porcelain
> limpo — byte-parity não prova eficácia); gate CF-6 ganha varredura
> NEGATIVA de vocabulário no arquivo inteiro; assert do tournament
> restrito a run-steps (o upload `uses:` não aceita working-directory).
>
> **v4 (S304, mesma sessão).** Consenso do debate round 1 aplicado
> (3× ADJUST, 0 VETO, PROCEED — `PLAN-177/debate/round-1/consensus.md`,
> 9 ajustes CF-1..CF-9): decisão malformada nunca sai por INFRA;
> chave duplicada rejeitada; assimetria load-bearing declarada;
> E_DECISION=13 + assert derivado de vars(mod); SCAN por arquivos
> explícitos; gate Where-enforced com coluna Status + contagem mínima;
> ordem do W2 corrigida (curas+bump primeiro, envelope é a última
> escrita); sweep por arquivo inteiro; entrega .gitignore completa
> (dois blocos + `.claude/.gitignore` para modo user).
>
> **v3 (S304, mesma sessão).** Recon P1-4 completo: pontos de
> inserção exatos, conjunto autoritativo do template
> (`verdict: GO | NO-GO | GO-WITH-CONDITIONS`), riders de inputs_hash
> e re-pin do W3, e o colateral da suíte morta. Ver §Riders.
>
> **v2 (S304, mesma sessão).** Recon de precisão (2 agentes Opus
> read-only) refinou as rotas: P1-1 via gerador compartilhado (INV-4),
> P1-2 sem writer novo (doutrina do módulo), P1-3 rota (ii) +
> promessas-irmãs. v1 = semente da manhã.
>
> **SEMENTE (S304, 2026-08-13).** O `OWNER-GA-CUT.sh` abortou no passo
> 1/8 em 12/08 12:35: re-pass Codex NO-GO nas duas partes, 4 achados
> P1 (evidência landada em `PLAN-166/repass-ga/`, commit `85b4b39`).
> **3 dos 4 P1 são "promessa sem gate"** — a 16ª instância da classe
> dominante do repo. Doutrina deste plano: **cada cura nasce com
> controle positivo** — um teste que prova o gate FALHANDO no cenário
> que o P1 descreve. Corolário do recon: **as correções de texto sem
> os testes novos seriam a instância 17 da mesma classe.**

## Context

Os 4 P1, todos verificados nos verdicts (`repass-ga/verdict-ga-1.txt`,
`verdict-ga-2.txt`) e nenhum refutável:

- **P1-4 (o mais grave):** `.github/scripts/validate-pair-rail-verdict.py`
  tem ZERO ocorrências de `GO`/`NO-GO` — valida pinning e TTL, nunca a
  decisão. `_release_tag_guard.py` e `release.sh tag --stable` aceitam
  verdito com decisão `NO-GO`, ausente ou desconhecida. Reproduzido com
  os args exatos do step-15 (`release.yml:726-735`): flipar para `NO-GO` retorna `OK`, exit 0,
  `release-gate` passa, e a aprovação de environment pode publicar npm
  irreversivelmente. Re-finding do P1 de `repass-r2/verdict-c.txt` cuja
  cura anterior cobriu SÓ o `OWNER-GA-CUT.sh:349-363`.
- **P1-1:** adopter v1.2.0 via `upgrade.sh` recebe `/night-mode` mas
  nunca os entries de `.gitignore` (`install_posture_state_ignores`,
  `install.sh:1830-1857`, landou PÓS-v1.2.0 — gap confirmado por
  `git show v1.2.0`). `install.sh:1860` pula o setup em
  `--ceremony user` (por design: install e upgrade concordam em user).
  O parity gate (`scripts/tests/_parity_classify.py:123-132`) nomeia o
  gap como REAL e o **allowlista** — CI incapaz de falhar no defeito.
- **P1-2:** `npm/INTEGRITY.md:4` declara "currently 1.0.1" — única
  versão hardcoded do arquivo; fora do tarball (`files`); o scanner de
  superfícies vivas tem `SCAN_ROOTS` SEM `npm/`
  (`test_release_bump_sites.py:1158`) — por isso nenhum gate viu.
  `release-checklist.md:68-71` lê como censo do repositório.
- **P1-3:** `npm/INTEGRITY.md:7-15` afirma manifesto SHA-256 por
  tarball "enforced **today**" — FALSO: `npm-publish.yml` nunca
  materializa o .tgz (`npm pack --dry-run` em :378 não escreve);
  `SHA256SUMS.txt` só tem v1.0.0 e NÃO viaja no tarball (fora do
  `files`) ⇒ a receita de consumidor (:45-48) não pode funcionar.
  **Promessas-irmãs da mesma classe (recon):** `SHA256SUMS.txt:3,13`
  (atribui geração ao workflow; o gerador real é `install-npm.sh`,
  local), `SUPPORT.md:155` (claim de verificação no `npm install -g`),
  `scripts/install-npm.sh:182-184` (comentário, CANÔNICA).
  Contra-exemplo honesto já no repo: `SECURITY.md:79-81`.

Somam-se 2 patches de triagem S303 já validados com `apply --check`:

- **T-1 (canônico):** `tournament.yml` — `working-directory:
  .claude/scripts` no step de summary (causa raiz do red de schedule já
  curada em `2aceb05`; este fecha o "Projection: N/A" silencioso).
- **T-2 (livre):** ✅ LANDADO `3842d4f` — filtro harness-probe no
  `skill_unknown_ratio` do ceo-boot (4 testes, controle negativo 5×).

## Escopo — o que NÃO entra (pré-registrado na S304)

Fora da rc.4 de propósito, cada item ampliaria a superfície do próximo
re-pass: patch de perf (toca `validate.yml` = KERNEL), node24 (toca o
caminho de publish), **rota (i) do P1-3** (implementar checksum de
tarball = sub-feature no caminho de publish, não-verificável sem cortar
tag ⇒ trem v1.4.0), rascunhos de plano, W3/W4 do PLAN-169
(mecanicamente pós-GA: o assert de delta do GA exige que entre rc.4 e
GA só existam artefatos do verdito).

## Waves

### W0 — superfícies LIVRES (L2 na superfície; o plano é L3 pelo conjunto)

1. **P1-4 — gate de decisão nos DOIS validadores.** Nenhum dos dois
   está em `_CANONICAL_GUARDS` ⇒ **sem cerimônia** (recon verificado).
   - `.github/scripts/validate-pair-rail-verdict.py`: constante
     `ACCEPTED_DECISIONS = ("GO", "GO-WITH-CONDITIONS")` junto aos
     exit codes (:83-86); bloco novo entre :230 e :231 (após o parse,
     ANTES do bind de `release_tag`): `verdict.get("verdict","")` com
     **igualdade exata** (sem normalização de caixa, sem `startswith`
     — a classe substring-vs-exact mordeu 3× na S299); fora do
     conjunto/vazio ⇒ `INVALID:` no stderr + `EXIT_VERDICT_INVALID`
     (3); docstring de exit codes atualizada.
   - `.claude/scripts/local/_release_tag_guard.py`: mesmo conjunto;
     bloco entre :295 e :296 (após bind de `release_tag`); modo
     distinto `E_DECISION = 13` (o assert de
     `test_release_workflow_asserts.py:1000-1013` exige códigos
     não-zero e distintos — código novo satisfaz e é testável como
     modo próprio); comentário-cabeçalho :52-63 atualizado.
   - `release.sh` NÃO muda: `tag()` já invoca o guard com `|| die`
     para RC e stable (:622-631) — exit≠0 do delta mata a tag.
   - **Semântica NÃO unificada com o GA-CUT:** `OWNER-GA-CUT.sh:376-391`
     checa OUTRA superfície (saída bruta do rail, `VERDICT: GO` exato,
     deliberadamente mais estrito). As duas regras coexistem.
   - **Controle positivo:** teste em
     `.claude/scripts/tests/test_release_bump_sites.py` (raiz que
     RODA em `validate.yml:424` E `release.yml:364`) — kwarg
     `verdict=` em `write_verdict`/`arm_verdict` (hoje hardcodam
     `GO`); tag_guard via helper `guard()` existente; validador do CI
     via subprocesso com os ARGS LITERAIS do step-15 — que vive em
     `release.yml:726-735` (job `release-gate`; o `npm-publish.yml`
     apenas ESPERA esse gate via `needs: await-release-gate`) — **em
     duas variantes**: parent-sha real e
     `--parent-sha ""` (o shape de `CEO_PAIR_RAIL_VERDICT_OPTIONAL=1`,
     onde o único outro bind forte está desligado). Casos: `NO-GO`,
     ausente, desconhecido (`MAYBE`) vermelhos; `GO` e
     `GO-WITH-CONDITIONS` verdes. NUNCA em `.github/scripts/tests/`
     (suíte morta — ver Riders).
2. **P1-2 — texto version-neutral + scanner (SEM writer novo).**
   - `npm/INTEGRITY.md:4`: version-neutral apontando `VERSION` como
     autoridade (NÃO adicionar como site de bump — doutrina do próprio
     `_release_bump_sites.py:82-91`: writer sem oráculo = dead rule).
   - **CF-5:** NÃO adicionar `"npm"` cru a `SCAN_ROOTS` (o bundle
     espelhado `npm/.claude/**` e o staging rsync fariam o scanner
     varrer cópias): acrescentar ARQUIVOS explícitos —
     `"npm/INTEGRITY.md"` e `"npm/README.md"` (SCAN_ROOTS já aceita
     arquivos, `RELEASE.md` é um) + teste que falha em semver nu fora
     de linha de stamp, com controle positivo plantando NO PRÓPRIO
     `npm/INTEGRITY.md` do fixture (provar a superfície, não a regra).
   - `release-checklist.md:68-71`: explicitar que a cobertura é sobre
     os sites ENUMERADOS; exaustividade sobre o repo vem do scanner.
3. **P1-3 — rota (ii): alinhar promessa ao mecanismo + gate novo.**
   - `npm/INTEGRITY.md` :7-15, :23, :30-48, :95-102: manifesto SHA-256
     sai de "enforced today" para "not yet automated (deferred)";
     corrigir a receita de consumidor. Redação-modelo:
     `SECURITY.md:79-81`.
   - `npm/SHA256SUMS.txt:3,13`: atribuição correta
     (`scripts/install-npm.sh`, local). `SUPPORT.md:155`: remover claim.
   - **CF-8: o sweep é do ARQUIVO INTEIRO**, não das faixas: +3
     promessas falsas verificadas fora delas — §GPG key aponta
     `docs/rotation-log.md` §NPM (inexistente) e `.well-known/gpg.asc`
     (inexistente); §CI verification descreve step SOURCE_DATE_EPOCH
     que `validate.yml` não tem. A receita de consumidor (:45-48) é
     REMOVIDA/substituída, não ressalvada. Varredura por VOCABULÁRIO
     de enforcement em README.md/npm/README.md/SECURITY.md/docs/ —
     couber ⇒ agora; não ⇒ item NOMEADO do trem v1.4.0.
   - **CF-6: gate anti-reincidência redesenhado:** a tabela Contract
     ganha coluna `Status` de conjunto FECHADO
     (`enforced|deferred|operator`); o teste lê SÓ linhas `enforced`,
     exige workflow em backticks que EXISTE + `step "nome"` casando
     por IGUALDADE EXATA com `- name:` do YAML; **contagem mínima ≥2**
     (sem ela o gate é vacuoso por construção); Status fora do
     conjunto ⇒ red (fail-closed em vocabulário desconhecido).
     Controles: step renomeado ⇒ red E tabela sem matches ⇒ red na
     contagem. **E (codex v4 P1-4): varredura NEGATIVA de vocabulário
     no ARQUIVO INTEIRO** — nenhuma frase de enforcement ("enforced
     today", "every tag publish records", "is verified", …) fora da
     tabela declarada/seção deferred; uma promessa nova na introdução
     tem de FALHAR, não passar em silêncio (o P1-3 original morava
     fora da tabela). Controle positivo: plantar a frase na intro ⇒
     red.
   - Rota (i) real: registrada como item do trem v1.4.0.
4. **P1-1 parte livre — CF-2 [P0], mecânica CORRIGIDA:** a tupla
   `^\.gitignore$` está em **ACCEPTED** (não KNOWN_OPEN); entry órfã
   = WARNING, NÃO mandatory-fire — o estado "cura landada + entry
   presente" é CI-VERDE E CEGO. Rota (b) do consenso: remoção atômica
   no commit do pack, justificativa = AC-3, nota explícita de que o CI
   NÃO protege o estado C (verificação humana: `git show --stat` prova
   as duas metades antes do push). **Controle positivo da superfície
   NOVA:** o plant do `--positive-control` só sabe remover linhas
   `backup_and_replace` — executar UMA VEZ, em clone scratch, o estado
   D (allowlist removida + entrega revertida) e anexar o transcript
   FATAL ao pack como evidência. O fixture v1.2.0 + controle existente
   seguem rodando por-PR e no push de main (`smoke-install.yml:65-67`).

### W1 — pack canônico único + cerimônia GPG (L3+, 1 assinatura)

Doutrina P1-1 (recon): o texto do bloco de ignore passa a viver em UM
gerador (INV-4/PLAN-168 W2 — duas cópias do mesmo texto foi a classe
que gerou o bug do pointer); saída preservada BYTE A BYTE (o header é
por-entry, dentro do loop — reimplementar "bonito" quebra parity).

Superfícies (CF-9 amplia a entrega):
- `scripts/_framework_manifest_set.sh` (~:646): +geradores — o UM
  lugar do texto — donos dos **DOIS blocos marker-guarded** do root
  `.gitignore` (mcp-secrets `install.sh:1797-1815` + posture
  `:1830-1857`; dono de um só = cerimônia sem a propriedade) E do novo
  `.claude/.gitignore`.
- `scripts/install.sh:1797-1857`: corpos inline → chamadas ao gerador,
  saída byte-idêntica; gates de cerimônia intactos (:1859-1860);
  +entrega do `.claude/.gitignore` (TODAS as cerimônias, inclusive
  `user` — escreve dentro de `.claude/`, não viola o assert
  `smoke-install.yml:220-232`).
- `scripts/upgrade.sh` (entre :3128 e :3130): entrega idempotente dos
  DOIS blocos do root (gate `[[ "$CEREMONY_EFFECTIVE" != "user" ]]`
  espelho de :3084) + `.claude/.gitignore` (todas as cerimônias) +
  `command -v` fail-loud (espelho de `install.sh:1898`) + ramo
  `--dry-run` + `_up_record_op`.
- **`.claude/.gitignore` (arquivo NOVO entregue):** conteúdo `/state/`
  + `/settings.local.json`; create-if-missing, NUNCA sobrescrever
  (adopter-owned após criação) — fecha o dano nomeado do
  `verdict-ga-1.txt:5` no modo user.
- **Idempotência por-linha do root mantida e DOCUMENTADA como
  intencional** (re-append pós-remoção deliberada é postura de
  segurança; release notes registram).
- `scripts/tests/_parity_classify.py:123-132`: REMOVER a tupla —
  mesmo commit (CF-2).
- `scripts/install-npm.sh:178-190`: o BLOCO (duas claims — comentário
  do CI + receita curl de arquivo que não viaja), não 3 linhas.
- `.github/workflows/tournament.yml`: patch T-1 + assert estrutural
  novo em `.claude/scripts/tests/` — restrito a **`run`-steps que
  consomem `projection.txt` RELATIVO** (o upload `uses:` referencia
  por path completo e nem aceita working-directory — codex v4 P2) —
  T-1 não entra sem controle.
- `.github/workflows/npm-publish.yml`: **NÃO TOCAR** (rota i excluída).
Protocolo: staged/ + manifesto sha256 RASTREADO + `shasum -c`
fail-closed + sentinel GPG inline + **escopo do sentinel ENUMERA os
arquivos livres que landam no mesmo commit** (parity_classify + testes
— senão touched−scope=∅ reprova) + `git show --stat` prova as duas
metades do CF-2 antes do push + land.
Higiene dos testes novos: tmp_path, env isolado por fixture autouse
(xdist), marker `serial` só se registrado (--strict-markers).

### W2 — rc.4 + hold + GA (espelha W2/166, doutrina intacta)

1. **CF-7 [P0] — ordem corrigida (o guard mataria a tag na ordem
   antiga):** curas + `bump --rc 4` LANDAM PRIMEIRO (push, CI verde) →
   re-pass Codex revisa ESSE SHA (snapshot limpo DETACHED; até
   APPROVE) → envelope rc.4 é a ÚLTIMA escrita antes da tag (único
   arquivo do delta parent-revisado→tag; NENHUM path do
   `pair-rail-inputs-hash-manifest.txt` tocado depois do envelope —
   senão o step-15 devolve 3 na tag) → push → **CI verde POR-JOB**
   (conclusão `success` dos jobs relevantes, nunca
   `cancelled`/`skipped` — smoke-install tem cancel-in-progress —
   pinada ao SHA; `preflight`/`tag` assertam HEAD == esse SHA) →
   `preflight --rc 4` → tag `v1.3.0-rc.4` (Owner) → push da tag →
   pre-release.
   **Pré-tag (CF-3):** assert via `gh variable list` de que
   `CEO_PAIR_RAIL_VERDICT_OPTIONAL` e `CEO_SOTA_DISABLE` estão
   ausentes/0. **Medir margem do timeout 25min do smoke-install**
   antes do corte (lição: cancelled em passo inocente).
3. Hold ADR-103 24h. Re-pass final: parent do verdito GA TEM de ser o
   commit da rc.4 (`origin/main == SHA(rc.4)`; avançou ⇒ rc.5).
4. `bump --stable` (no-op provado) → verdito GA → push → CI verde
   POR-JOB pinado ao SHA →
   `preflight --stable` → tag `v1.3.0` → aprovação `production-npm` →
   GA → **remover a limitação "OPEN P1" do CLAUDE.md §5** (a cura
   landada é a única coisa que autoriza remover a linha).
   **GA-CUT RETARGETADO (codex v4 P1-2):** o `OWNER-GA-CUT.sh` vivo
   está PINADO na rc.3 (`RC_TAG=v1.3.0-rc.3`, freeze-SHA da rc.3,
   evidência `repass-ga/` da rc.3) — corrigir só o header deixaria o
   Owner rodando um executável que aborta ou avalia evidência STALE.
   W2 gera `OWNER-GA-CUT-rc4.sh` retargetado (RC_TAG novo, freeze-SHA
   da rc.4, evidência `repass-ga-rc4/` fresca), revisado no re-pass.
   Nota B-N4 mantida: :387-389 aceita SÓ `VERDICT: GO` exato sobre a
   saída BRUTA do rail (by design); rail final devolvendo
   `GO-WITH-CONDITIONS` = triagem com o Owner, não bug; corrigir o
   header que diz o contrário.

## Riders (consequências que a cura carrega — recon P1-4)

- **R-1 inputs_hash (classe R-OPS-1/PLAN-142):**
  `validate-pair-rail-verdict.py` está no
  `pair-rail-inputs-hash-manifest.txt` — a cura MUDA o `inputs_hash`
  recomputado pelo step-15. Consequência natural: o envelope rc.4
  declara o hash novo; o da rc.3 deixa de bater (correto — a rc.3 foi
  superada). `_release_tag_guard.py` está fora do manifesto.
- **R-2 re-pin consciente do W3/169:**
  `PLAN-169/staged-w3/.claude/governance/gate-scripts-manifest.txt`
  pina o sha256 dos DOIS arquivos (batem com o disco HOJE). Pós-cura,
  o pack W3 exige re-pin CONSCIENTE — o LAND aplica com `cp` cego
  (lição S303); re-pin cego regrediria a cura. Registrar no runbook do
  W3 ANTES de assinar.
- **R-3 suíte morta (colateral, mesma classe do P1):**
  `.github/scripts/tests/` (15 testes, verdes à mão) não está em
  `pytest.ini testpaths` nem em nenhum step de CI — nunca executada.
  Wirar toca `validate.yml` (KERNEL) ⇒ FORA da rc.4; registrado como
  item do trem v1.4.0.
- **R-5 threat-model do envelope (consenso B-U2):** o que prende a
  STRING da decisão é a ASSINATURA do Owner sobre a árvore taggeada
  (`git verify-tag`, release.yml:639) — `inputs_hash` cobre os
  gate-scripts, não o verdito; `gpg_signature` é checado por presença.
  Fixture temporário auto-consistente em tmp NUNCA é bypass: nada dele
  alcança a árvore assinada.
- **R-4 verditos históricos:** censo de 11 envelopes vivos — todos
  `GO`/`GO-WITH-CONDITIONS`, campo sempre presente. O gate não quebra
  nenhum histórico; template não-preenchido é rejeitado (correto).

## Acceptance criteria

- [ ] AC-1 [P0] Regressão P1-4: validador servidor com os args exatos
      do step-15 de `release.yml:726-735` (NÃO npm-publish.yml — esse
      só espera o gate) + verdito `NO-GO`/ausente/desconhecido ⇒
      exit ≠ 0 nomeando a DECISÃO no stderr (diagnóstico específico —
      red pelo motivo certo), e `GO`/`GO-WITH-CONDITIONS` ⇒ 0. Casos
      vermelhos OBRIGATÓRIOS incluem: chave `verdict:` DUPLICADA
      (NO-GO seguido de GO — exatamente 1 chave top-level exigida) e
      formas malformadas (vazio/lista) saindo por
      VERDICT_INVALID/E_DECISION, NUNCA por INFRA. O
      fixture é um verdito temporário AUTO-CONSISTENTE: com
      `--recompute-inputs-hash` ligado e o próprio validador dentro do
      manifesto, o `inputs_hash` do fixture é RECOMPUTADO pós-cura —
      nunca reaproveitado de um envelope real (codex P2-2). Idem
      tag_guard.
- [ ] AC-2 [P0] `_release_tag_guard.py` rejeita tag com verdito não
      autorizante — provado por invocação real, não por unit isolado.
- [ ] AC-3 [P1] Parity e2e (fixture v1.2.0, por-PR e push-main) verde
      SEM a allowlist de `.gitignore`; upgrade entrega os DOIS blocos
      byte-idênticos ao install; `--ceremony user`: root .gitignore
      segue sem entrega nos DOIS caminhos, e `.claude/.gitignore` é
      entregue nos DOIS caminhos; estado D exercitado uma vez em clone
      scratch com transcript FATAL anexado (CF-2); e — codex v4 P1-3,
      o dano ORIGINAL — caso e2e que ARMA night-mode no target
      (upgrade v1.2.0 E install --ceremony user) e asserta que
      `.claude/settings.local.json` e `.claude/state/night-mode.json`
      NÃO aparecem em `git status --porcelain` (byte-parity não prova
      eficácia; ignore ineficaz idêntico nos dois caminhos passaria).
- [ ] AC-4 [P1] `npm/INTEGRITY.md` sem claim falsa (versão, gate
      inexistente, receita impossível); promessas-irmãs corrigidas
      (`SHA256SUMS.txt`, `SUPPORT.md`, `install-npm.sh`); scanner
      cobre `npm/` com controle positivo; teste "Where enforced ⇒
      step existe" verde e com controle positivo.
- [ ] AC-5 [P1] tournament.yml com working-directory (T-1).
- [ ] AC-6 [P0] Sequência W2 na ordem do CF-7 (curas+bump landados →
      re-pass do SHA → envelope como última escrita → push → CI
      por-job pinado → preflight → tag no mesmo SHA); delta
      parent-revisado→tag contém SÓ o envelope + verdict-fields;
      `gh variable list` limpo pré-tag.
- [ ] AC-7 [P0] Assimetria load-bearing declarada nos dois validadores
      (comentário) e vigiada por assert estrutural (step delta invoca
      `_release_tag_guard.py delta`); assert de E_* derivado de
      `vars(mod)` com contagem mínima.
