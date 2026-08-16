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
