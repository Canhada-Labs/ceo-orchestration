# rail-sign-min — pacote cenv (PLAN-194, Lote B): o registro do rail que o molde sign-min lê

Rail-Subject: .claude/plans/PLAN-194/cenv/cenv.patch
Rail-Subject-sha256: 4a4b3e7c4f890df09d70ac02daf67b0a1b20c05081a4388e701297d103534854
Rail-Sentinel-sha256: 679a6a629e5fb8678335b72cd5f7087b5252f79af7ea6fb4f109541eb7859551
Rail-Data-sha256: 3f8a8e0161372dcf32e94ef6c2a877c47d2f12a2577106cf12e2f017064684f0
Rail-Round: única (molde sign-min) — PENDENTE
Rail-Verdict: PENDENTE

O P0 do molde (`P0:rail`) exige neste arquivo exatamente uma linha de cada um dos 3 campos sha256
acima, iguais ao sha256 do `cenv.patch`, do `cenv-approved.md` com os quatro campos por preencher e do
`sign.tsv` no `Anchor-SHA`, e uma linha `Rail-Verdict` com `APPROVE` ou `DECLARED-P2`. Com `PENDENTE`,
o SIGN recusa no P0. O veredito só muda depois da rodada única (abaixo), com as saídas verbatim das 3
lanes registradas aqui.

## Materiais desta rodada (sha256 no commit de materiais)

- `.claude/plans/PLAN-194/cenv/cenv.patch` — 4a4b3e7c4f890df09d70ac02daf67b0a1b20c05081a4388e701297d103534854
  (o mesmo patch da rodada 1 + anexo; NÃO mudou na migração)
- `.claude/plans/PLAN-194/cenv-approved.md` — 679a6a629e5fb8678335b72cd5f7087b5252f79af7ea6fb4f109541eb7859551
- `.claude/plans/PLAN-194/cenv/sign.tsv` — 3f8a8e0161372dcf32e94ef6c2a877c47d2f12a2577106cf12e2f017064684f0
- `.claude/plans/PLAN-194/cenv/sintaxe.py` — ffd2d376a108c7d8df54e066ea991323a5896ada2daca91d2071eb0496d99fb9
- `.claude/plans/PLAN-194/cenv/red-control.txt` — 432e06a404bfcc359043cd8825e884300c314fb0946d1173e15bad6636d99a44

## Checklist da rodada única (texto + dados)

1. Toda frase própria do pacote no sentinel é verdadeira no código do `Anchor-SHA` (o bloco comum é do
   molde e tem o rail do molde).
2. O controle vermelho é REPRODUZIDO sobre as pré-imagens (decisão D1): o teste novo, sozinho, contra o
   hook no blob pré-imagem `03ad92380ad8fc95878c1d36a4efb63f4b1c8a0d`, sai rc 1 com exatamente o id
   FAILED do `red-control.txt` e o `TypeError` do `action` repetido; com o patch inteiro, rc 0.
3. Nenhum gate do SIGN anterior do pacote some (tabela abaixo): o genérico está na lista fixa do molde;
   o específico é linha `hard` dos dados.
4. O `sintaxe.py` sai com rc ≠ 0 quando um dos caminhos não analisa (o molde julga só o rc na forma 3).

## Gates do SIGN anterior × molde

O SIGN anterior do pacote é `.claude/plans/PLAN-194/cenv/OWNER-CENV-SIGN.sh` (blob
`b220ac978938e3d1903d41ec323af1bb21da0c68`) do commit de materiais `83961b31` (sombra mat-cenv da S363,
nunca no `main`); a migração não o traz, nem o harness `test-ceremony-cenv.sh` e o `class-table.md`.
Linhas citadas desse arquivo:

| SIGN anterior | Molde sign-min |
|---|---|
| `ast.parse` dos 3 caminhos, `python3 -I -` (:1145-1154) | `hard` 1: `python3 .claude/plans/PLAN-194/cenv/sintaxe.py` com os 3 caminhos |
| `hard_pytest` do teste novo e do de bloqueio (:1156) | `hard` 2 (forma 4, `--tb=short`, resumo só de aprovados) |
| `hard_pytest` de `test_audit_emit.py` e `test_audit_emit_api_contract.py` (:1158) | `hard` 3 |
| `check-audit-registry-coverage.py` (:1159-1161) | `hard` 4 |
| `check-test-env-hygiene.py` (:1162-1164) | gate fixo 1 do molde |
| `validate_governance_fast.py`, rc 0 e `PASS` na última linha (:1165-1169) | `hard` 5 (rc 0; no fonte do gate, `PASS` sai só com rc 0) |
| gates de corpus env-inventory, active-hooks, contamination, build-plugin, gen-map, docs-freshness, docs-drift, verify-counts, claude-md-claims, ceremony-lint (:1170-1179) | gates fixos 2–11 do molde |
| `validate-governance` com e sem o patch (:1180) | gate fixo 13 do molde (rc 0, sem comparação com a base) |
| passada dirigida serializada, `test_cost_envelope.py` + `test_template_dogfood_parity.py` (:1184) | `hard` 6 (sem `-n`, `--strict-markers`, sem tolerância de falha pré-existente) |
| passadas paralela e serial do `pytest.ini` (:1186-1187) | suítes fixas do molde |
| controle vermelho no P0 (:948-971) | registro no sentinel (D1), reproduzido por este rail |
| — | gate fixo 12 do molde, `check-staleness.py` (novo para este pacote) |

## Histórico: rodada 1 e anexo (antes da migração)

O registro da rodada 1 foi `.claude/plans/PLAN-194/cenv/rail-record.md` (blob
`cb96a0bfb3a79a9449829958058018ae81791c51`, commit `83961b31`, sombra mat-cenv), preso ao sentinel do
SIGN anterior; ele não vem para a árvore do molde. As saídas abaixo são as dele, verbatim.

- Rodada 1: sujeito `6ccde6b0..3edf44dc` (3 commits; cherry-picks sobre `61aa7372` com patch-id igual:
  `d00a837f`, `5a1cd8ac`, `be7bec52`). Codex 0.160.0 (`exec --sandbox read-only`, gpt-6-astra,
  reasoning xhigh) em 2026-10-09; r-cenv-b em 2026-10-11 ~04:00Z; r-cenv-a ~04:03Z. GO nas três lanes;
  P0=0 P1=0 P2=0; 3 P3 distintos: 2 de texto no teste novo (curados no anexo) e 1 fora do patch
  (`_resolve_project_path`, follow-up da 1.4.4).
- Anexo `c395487e` (sobre `be7bec52`; só `.claude/hooks/tests/test_check_cost_envelope_emit.py`, +15 −6,
  comentário e docstring). Conferência: Codex 0.160.0, `--sandbox read-only`, gpt-6-astra, reasoning
  xhigh, preflight 2026-10-11T06:59:46Z; registro fora do repositório (scratchpad da sessão S363
  d876fa66, `night/rail/cenv-annex/`).

```text
=== Codex 0.160.0, rodada 1, sujeito 6ccde6b0..3edf44dc — última mensagem, verbatim ===
NENHUM ACHADO

VERDICT: GO
```

```text
# r-cenv-a (security-engineer, fable) — rail cenv r1, sujeito 6ccde6b0..3edf44dc — recebido 2026-10-11 ~04:02Z
(a) linha gravada = só a allowlist _COST_ENVELOPE_CAPPED_ALLOWLIST (audit_emit.py:1266) + envelope; project_path/user_id/command ausentes. Único caminho cru: project = CLAUDE_PROJECT_DIR, o mesmo dos outros 13 sítios dos hooks ⇒ nenhum vazamento NOVO. Resíduo descrito com verdade; nota: «ambígua» é brando — a prosa SPEC :1349-1352 CONTRADIZ a tabela :398/:1529; o item 1.4.4 deve dizer que project é envelope e a proibição mira chaves do chamador (project_path). Nenhum consumidor esperava zero eventos.
(b) chave viva idêntica antes/depois de 4 execuções; marcador 0 no log vivo e no .errors; pai vermelho em :148 pela razão certa (TypeError multiple values for 'action'); mutantes 1 e 2 vermelhos em :175/:177; HEAD emit+block+api_contract 21 passed; env-hygiene OK.
(c) censo AST 1680 .py, 1257 alvos, 7125 chamadas: HEAD 0, pai 1 (controle positivo); 15 sítios **var não-literal inspecionados à mão: nenhum colide.
(6) mensagens verdadeiras.
Achados:
- [P3] test_check_cost_envelope_emit.py:131-140 — dois dispatches precisam cair na mesma data UTC; resíduo não declarado no docstring (o de bloqueio declara). Cura: 1 frase.
- [P3, fora do patch] check_cost_envelope.py:175 _resolve_project_path() cai em os.getcwd() sem CLAUDE_PROJECT_DIR ⇒ project vira o cwd. Pré-existente; follow-up.
VERDICT: GO
```

```text
# r-cenv-b (code-reviewer, fable) — rail cenv r1, sujeito 6ccde6b0..3edf44dc — recebido 2026-10-11 ~04:00Z
ACHADOS
- [P3] .claude/hooks/tests/test_check_cost_envelope_emit.py:160-161 — comentário «``project`` is the ENVELOPE field every event carries» é impreciso: _write_event (audit_emit.py:2747) NÃO injeta project; os emissores tipados recebem project: str = "" do chamador (ex. :3009/:3028) e emit_generic só o grava se o chamador passar; há linhas com "project": "" (:2589/:2644). A asserção em si está certa (SPEC :398 lista project; valor = CLAUDE_PROJECT_DIR). Cura: só texto.
- [P3] mesmo arquivo, docstring — residual «duas chamadas a cavalo da 00:00 UTC» (test_check_cost_envelope_block.py:51-53) herdado e não declarado. Cura: uma frase. Opcional.
VERIFICADO: (1) cura = 1 linha removida; (2) pai 1 falha/8 verdes pela razão certa (TypeError multiple values for 'action'), HEAD 9/9; mutantes A e B reprovam; (3) isolamento: 0 ocorrências no log vivo/errors/fallback/state; (4) censo AST 476 arquivos, 251 chamadas: pai 1 colisão, HEAD 0; (5) nada espera zero eventos; registry-coverage OK; env-hygiene 337/337; (6) mensagens verdadeiras; (e) main 61aa7372: 0 conflitos, nenhum commit desde a base toca os arquivos.
VERDICT: GO
```

```text
=== Codex 0.160.0, conferência do anexo c395487e — última mensagem, verbatim ===
NENHUM ACHADO
VERDICT: GO
```

## Rodada única (molde sign-min) — PENDENTE

- Lanes: Codex (read-only) e 2 refutadores Claude, na mesma rodada; no máximo uma conferência de anexo.
- Ao fechar: as saídas verbatim das 3 lanes entram aqui, cada uma num bloco `text` com cabeçalho
  próprio; `Rail-Verdict: APPROVE` só com as 3 lanes GO e P0=0 P1=0 P2=0 (`DECLARED-P2` com P2
  declarados na seção abaixo). Mudar o sentinel ou os dados muda os sha256 acima e pede nova conferência.

## P2 declarados

- (nenhum)
