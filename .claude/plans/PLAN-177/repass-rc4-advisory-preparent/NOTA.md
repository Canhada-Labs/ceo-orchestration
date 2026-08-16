# Advisory rail — delta administrativo pré-t7 do envelope rc.4

## Por que este diretório existe

O re-pass t6 (GO-WITH-CONDITIONS nas 2 partes) ancorou em
`5af2cd752cdc6ba361154b2c21b0b1e425523353`. Depois do envelope
(`9109176`), sobraram na working tree materiais que a tag EXIGE
commitados (tag refusa árvore suja) mas que o delta guard PROÍBE no
delta pós-parent (allowlist aceita apenas o verdict + evidência sob
`.claude/plans/PLAN-177/` — `release.sh` é "code path" por definição
do próprio guard, e é assim por design).

## A rota (ratificada pelo P0 do round r2 abaixo)

A primeira proposta — commitar o material num commit X e mover
`parent_sha` para X preservando transcript/inputs hashes — foi
REJEITADA pelo rail (r2 P0): faria o guard tratar 5af2cd7..X como
revisado sem o re-pass de 2 partes ter olhado para ele — o bypass
exato que o invariante reviewed-parent impede.

Rota adotada: o material entra num commit administrativo X e o
**re-pass RODA DE NOVO (t7) contra X** — evidência, PROVENANCE,
MANIFEST, verdict-fields e assinatura são TODOS regenerados pelo fluxo
normal do runner, com `parent_sha = X` genuinamente revisado.

## Escopo do commit X (todo o conteúdo coberto pelos rounds abaixo)

1. `.claude/scripts/local/release.sh` — bloco PER-RELEASE
   (RELEASE_SCOPE agora nomeia PLAN-177/178 e ADRs 184→191 +
   ADR-089-AMEND-1; parágrafo rc.4 na headline). Prosa da anotação
   assinada da tag; zero lógica alterada.
2. `.claude/scripts/tests/test_release_bump_sites.py` — a regressão
   exata do RELEASE_SCOPE re-pinada na string viva (r2 P1a).
3. `CHANGELOG.md` — seção [1.3.0] agora cobre PLAN-177 (curas do
   re-pass) e TODO o PLAN-178 shipado no candidato: spawn contract v2,
   W1.2 native cost cross-check e Lote A vacuity lint (r1 P2 + r2 P1b).
4. `.claude/plans/PLAN-177/repass-rc4-20260816-t5-NOGO/` — quarentena
   da evidência do t5 NO-GO (movida pelo próprio runner fail-closed;
   mesmo padrão das quarentenas t2/t3 já na história).
5. `.claude/plans/PLAN-177/repass-rc4-20260816-t6-GWC-superseded/` —
   a evidência t6 sai de `repass-rc4/` para dar lugar à t7; o veredito
   t6 (GO-WITH-CONDITIONS) permanece válido como registro histórico,
   superado pelo t7 que cobre um superconjunto.
6. Este diretório (transcripts do rail advisory + esta nota).

O runner re-pinado (`CANDIDATE_SHA = X`) NÃO entra em X — seria
circular (X não pode conter o próprio hash). Ele entra no commit do
envelope t7, sob `repass-rc4/` (EVIDENCE_PREFIX), listado na
delta_allowlist e no MANIFEST-t7.

## Cobertura de revisão

- `codex-advisory-r1.md` — round 1 sobre o uncommitted (itens 1 e 4).
  Confirmou o conflito clean-tree × closed-delta e achou o P2 do
  CHANGELOG (item 3).
- `codex-advisory-r2.md` — round 2: P0 que definiu a rota t7 (acima),
  P1 do teste de scope (item 2), P1 da cobertura PLAN-178 no
  CHANGELOG (item 3), P2 do transcript ausente (este diretório).
- `codex-advisory-r3.md` — round 3 sobre o estado final de X: nenhum
  P0; P1a (pin do runner = X só existe pós-commit — é a sequência) e
  P1b (janela X..Y sem MANIFEST no path que o verdict VIGENTE nomeia)
  triados abaixo; P2s curados (este arquivo; contagem de features no
  CHANGELOG).

## Janela X..Y (triagem do r3-P1b — decisão registrada)

Entre o commit X e o commit Y (envelope t7), o verdict vigente nomeia
`repass-rc4/MANIFEST-rc4.sha256`, que X move para a quarentena
superseded. Consequência: `release.sh tag` na janela refusa (guard
exit 7). Isso é o comportamento DESEJADO — a tag não pode ser cortada
antes do envelope t7 — e nenhum gate de push lê o envelope
(`release.yml`, único leitor do validador, dispara apenas em push de
tag). A alternativa (deferir a quarentena para Y) inflaria a
delta_allowlist e o MANIFEST-t7 com as 12 entradas superseded,
aumentando a superfície de erro do fechamento por hash sem ganho de
segurança. Janela aceita; Y a fecha.

A revisão de PRODUTO do candidato é o re-pass t7 (2 partes) sobre X;
este rail advisory documenta apenas a composição do delta
administrativo 5af2cd7..X.

## Ciclo t7 → X2 (NO-GO nas 2 partes; curas no commit X2)

O t7 sobre X devolveu NO-GO×2 com 4 P1 + P2s. TODAS as curas estão no
commit X2 (o t8 roda sobre ele):

- P1 (parte 1): whitelist de linhas com estado de parent 3-valores nos
  DOIS readers do verdito — indentação ÓRFÃ (antes da primeira chave ou
  após escalar) e `- item` na RAIZ agora são NONCANONICAL fail-closed;
  4 shapes novos na matriz cross-reader.
- P1 (parte 2, ×3): `_refresh_schema_doc` agora (a) recusa symlink no
  LEAF (checado antes de `-e` — link quebrado não vira install-through)
  e em QUALQUER ancestral; (b) respeita `--skip` na inspeção E na
  escrita, com dry-run por-path; (c) usa `_hash_file` (fallback
  sha256sum) — sem hasher utilizável, preserva com warning. Positive
  controls: caso B2-c4 no replay (12 asserts, 64/64 PASS local).
- P2s: docstring do T-2 corrigida (counter removido não é mais
  citado); stamp same-line + Contract-row 5-cell curados no scanner
  com relapse controls; prosa do `.claude/.gitignore` gerado agora diz
  a verdade (preserva bytes; entries de postura faltantes podem ser
  ANEXADAS); `--ceremony` documentado nas 3 superfícies de usage;
  wiring CI: unit do gitignore per-PR no smoke-install.yml (sentinel
  raiz do 177) + replay suite no ownership-nightly.yml com
  timeout 90→110 (sentinel round-2 deste plano, Owner-assinado).

DEFERIDO com registro: o comentário stale em `validate.yml:~869`
("replay é local-only") é ARBITRATION-KERNEL — sem rota de sentinel por
design (exige CEO_KERNEL_OVERRIDE humano na sessão). A cura real (o
wiring) está feita; o comentário segue o próximo kernel-touch
autorizado. Nenhuma mudança executável pendente.

## Ciclo t8 → X3 (NO-GO nas 2 partes; achados NOVOS, loop convergindo)

- P1 (parte 1): `strip()` Unicode no CLASSIFICADOR de shape — valor
  U+00A0 virava parent bare e linha-NBSP virava blank; e a causa-raiz
  mais funda, o próprio `_YAML_BLOCK_RE` com `\s*` Unicode ENGOLINDO a
  linha NBSP antes do classificador. Curado nos DOIS twins (strip
  ASCII + `[ \t]*` no extrator, 1+3 sites) + 2 fixtures NBSP com
  escapes explícitos na matriz.
- P2 (parte 1): comentários/diagnósticos atualizados — root `- item`
  NÃO é permitido (só indentado sob bare key).
- P1 (parte 2 #1): schemas na enumeração baseline agora seguem o padrão
  delivery-record dos irmãos (FMS_DELIVERED_PLAN_SCHEMA /
  FMS_DELIVERED_DEBATE_SCHEMA): install seta via INSTALL_ONE_WROTE ou
  byte-compare com o source; upgrade seta pelos verdicts
  INSTALLED/REFRESHED/IDENTICAL do `_refresh_schema_doc`. Um schema
  EXISTS-skipped fica FORA do manifest ⇒ uninstall nunca o
  hash-matcheia. Positive control B2-c5 no replay (seed pré-install →
  manifest omite → uninstall preserva bytes).
- P1 (parte 2 #2): presença textual ≠ exclusão efetiva —
  `_gitignore_reassert_effective` proba `git check-ignore` por entry
  nos DOIS appliers e RE-ASSERTA a exclusão após a negação vencedora
  (last-match-wins); ainda-visível ⇒ WARNING alto. Controle S9 no unit
  (nested + root, seed `!*.json`).
- P2s: dry-run sites chamam o guard COMPARTILHADO (3 sites); testes do
  detector assertam `_has_harness_probe_fingerprint` vivo;
  `night-mode.py` nos 2 path filters do smoke-install.

## Ciclo t9 → X4 (NO-GO nas 2 partes; classes menores, ainda novas)

- P1 (parte 1 #1): extrator de bloco NÃO-ancorado — um fence de 4
  backticks com um envelope GO quoted virava o bloco autoritativo sobre
  o NO-GO real. Cura ESTRUTURAL nos 2 twins:
  `_extract_single_yaml_block` exige EXATAMENTE 1 ocorrência literal do
  opener no artefato inteiro (2+ = ambíguo = rejeitado), opener em
  line-start coluna 0, fechamento line-start. TODOS os sites (1+3)
  consomem o mesmo extrator. Teste de texto cru para os 2 rails
  (4-backtick shadow + 2 blocos + opener indentado).
- P1 (parte 1 #2): `str.splitlines()` divide em VT/FF/FS-RS/NEL/LS/PS —
  `GO<U+000B>#NO-GO` parseava como GO. O extrator agora REJEITA
  qualquer control byte exceto TAB e qualquer separador exceto LF (CR
  incluído), e todo parsing divide só em `\n`. 4 fixtures com escapes
  explícitos na matriz cross-reader.
- P2 (parte 1): sweep de prosa restrito às rows do `## Contract`
  (tabela fora da seção não é mais isenta) + positive control.
- P1 (parte 2 #1): `_apply_mcp_secrets_ignore` ganhou o MESMO probe de
  efetividade + re-asserção (o store de SEGREDOS era o único applier
  sem ele) — control S10 no unit.
- P1 (parte 2 #2): `_preview_claude_dir_gitignore` proba read-only e
  reporta "would RE-ASSERT (present but negated)" — nunca mais um
  would-PRESERVE falso; control S10 prova zero writes no preview.
- P2s: prior-bytes dos legs de schema com fallback `v1.2.0` (mesma
  geração, sha 574bd22e; nightly a fetcha) e indisponibilidade vira
  SCAFFOLD FAILURE, nunca SKIP verde; frase "CI can download it
  separately" do sidecar removida (install-npm.sh); comentário do
  ceremony reader corrigido (fail-safe user, não maintainer).

## Ciclo t10 → X5 (NO-GO nas 2 partes; TODOS os achados curados)

- P1 (parte 1): FALSE CLOSER — `^```` casava qualquer linha iniciada
  por 3 backticks, então ` ```not-a-closer ` fechava o corpo cedo e
  escondia um NO-GO posterior. Closer canônico
  `^```[ \t]*(?:\n|\Z)` nos 2 twins + fixture de texto cru + o caso
  end-to-end no CLI.
- P2s (parte 1): rejeição de CONTEÚDO assinado agora sai como exit 3
  INVALID no CLI do step-15 (era INFRA 1, amortecível pelo flag
  optional) com UnicodeDecodeError incluso; leituras de produção em
  RAW/newline="" para o CR chegar VIVO à gramática (read_text comia o
  CR que a gramática promete rejeitar) — 4 corpos on-disk
  parametrizados no CLI (two-fences, false-closer, CRLF, VT).
- P1 (parte 2 #1): re-asserção que NÃO resolve virou ERRO propagado
  (rc 1 → install/upgrade abortam sob set -e) — negação em
  `.gitignore` mais profundo não passa mais como warning+sucesso.
  Control S11.
- P1 (parte 2 #2): probes com `check-ignore --no-index` (o index não
  mente mais) + detecção de paths sensíveis JÁ TRACKED via `ls-files`
  com migração fail-closed acionável (`git rm --cached`, caminho a
  caminho). Controls: S12 (unit) + B2-c6 no replay (upgrade FALHA com
  artefato tracked; pós-migração passa; upgrade repetido idempotente,
  sem RE-ASSERT em loop).
- P2 (parte 2 #3): o emitter-drift control do night-mode efficacy
  DERIVA os paths chamando `settings_local_path()`/`marker_path()` do
  módulo real (import por spec), nunca substring — prosa histórica não
  segura mais o teste verde.
- P2 (parte 2 #4): o Contract row do SHA-256 tarball está PINADO a
  `deferred` com mutation control — flipar para `enforced` sem o
  predicado semântico (pack não-dry-run + sha256 + publicação) fica
  RED antes de enganar alguém.

## Ciclo t11 → X6

- P1 (parte 1) TRIADO COMO FALSO-POSITIVO MECÂNICO: o codex flagou o
  pin desatualizado do runner COMMITADO e o MANIFEST ausente em
  `repass-rc4/` — ambos são a mecânica documentada do ciclo (o re-pin
  é working-tree e entra no commit do envelope; a janela sem MANIFEST
  é fail-closed desejado). O prompt do runner ganhou a seção "CYCLE
  MECHANICS (do not re-flag)" para não re-litigar.
- P2 (parte 1): a suíte legada `test_validate_pair_rail_verdict.py`
  (não-CI-wired) usava fixture block-scalar `gpg_signature: |` que a
  gramática nova rejeita — fixture trocada pela forma canônica
  single-line `base64:`; 17 failed → 20 passed.
- P1 (parte 2 #1): o ramo CREATED do nested applier retornava ANTES
  dos checks — user-ceremony com overlay JÁ TRACKED instalava verde.
  Agora cria E roda efetividade+tracked (falha exigindo migração).
  Control S13.
- P1 (parte 2 #2): dry-run HONESTO sobre tracked — classifier
  read-only compartilhado (`_gitignore_tracked_sensitive`) no preview
  nested (rc 1, "would REFUSE", zero writes — S14) e nos 3 dry-run
  sites do root (install ×2 + upgrade).
- P2 (parte 2 #3): `ls-files | head -5` sob pipefail = SIGPIPE 141
  abortando o upgrade antes da mensagem de migração (a classe
  documentada do repo) — `sed -n '1,5p'`; control S15 com 6 arquivos.
- P2 (parte 2 #4): prosa do Governance no CHANGELOG desambiguada
  (range 184→191 é por NÚMERO; 192 é file-count com amendments).
