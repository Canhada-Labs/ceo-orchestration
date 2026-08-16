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
