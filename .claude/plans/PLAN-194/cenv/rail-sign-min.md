# rail-sign-min — pacote cenv (PLAN-194, Lote B): o registro do rail que o molde sign-min lê

Rail-Subject: .claude/plans/PLAN-194/cenv/cenv.patch
Rail-Subject-sha256: 4a4b3e7c4f890df09d70ac02daf67b0a1b20c05081a4388e701297d103534854
Rail-Sentinel-sha256: 42a92f9c38989e3db7083960e31d47fa34c188a85fa2993dfd2a10537738a07a
Rail-Data-sha256: 3f8a8e0161372dcf32e94ef6c2a877c47d2f12a2577106cf12e2f017064684f0
Rail-Round: única (molde sign-min), com a conferência do anexo
Rail-Reviewer: codex-cli 0.160.0 (`exec --sandbox read-only`, gpt-6-astra, reasoning xhigh, config_sha 86435b2bc52b15b0 no preflight), conferência do anexo; refutador Claude na mesma conferência
Rail-Prompt: `night/rail/pk-cenv-annex/codex-prompt.md` (sha256 e24a190cc7620adce985a4035dfab9b9715b651bb397dc028849409ad49a3876), no scratchpad da sessão S363 d876fa66, fora do repositório
Rail-Date: 2026-10-12 (conferência do anexo; preflight do Codex às 02:38:47Z)
Rail-Reviewer-Verdict: GO
Rail-Verdict: APPROVE
Rail-Findings: P0=0 P1=0 P2=0

O P0 do molde (`P0:rail`) exige neste arquivo exatamente uma linha de cada um dos 3 campos sha256
acima, iguais ao sha256 do `cenv.patch`, do `cenv-approved.md` com os quatro campos por preencher e do
`sign.tsv` no `Anchor-SHA`, e uma linha `Rail-Verdict` com `APPROVE` ou `DECLARED-P2`. Com `PENDENTE`,
o SIGN recusa no P0. O veredito só muda depois da rodada única (abaixo). Entram aqui, verbatim, as saídas
da conferência do anexo (Codex e refutador Claude); as das 3 lanes da rodada 1 ficam fora do
repositório, citadas por caminho e sha256 na «Triagem».

## Materiais desta rodada (sha256 no commit do anexo; destes cinco, só o sentinel mudou desde o commit de materiais)

- `.claude/plans/PLAN-194/cenv/cenv.patch` — 4a4b3e7c4f890df09d70ac02daf67b0a1b20c05081a4388e701297d103534854
  (o mesmo patch da rodada 1 + anexo; NÃO mudou na migração)
- `.claude/plans/PLAN-194/cenv-approved.md` — 56b89e3be5c8d6ebf37c3a77b218f85cb493bd10ce11168a4689c2fba9b46c36
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
| `ast.parse` dos 3 caminhos, `python3 -I -` (:1145-1154) | `hard` 1: `python3 .claude/plans/PLAN-194/cenv/sintaxe.py` com os 3 caminhos, sem `-I` (a forma 3 não aceita opção antes do script; declarado nos resíduos do sentinel) |
| `hard_pytest` do teste novo e do de bloqueio (:1156) | `hard` 2 (forma 4, `--tb=short`, resumo só de aprovados) |
| `hard_pytest` de `test_audit_emit.py` e `test_audit_emit_api_contract.py` (:1158) | `hard` 3 |
| `check-audit-registry-coverage.py` (:1159-1161) | `hard` 4 |
| `check-test-env-hygiene.py` (:1162-1164) | gate fixo 1 do molde |
| `validate_governance_fast.py`, rc 0 e `PASS` na última linha (:1165-1169) | `hard` 5 (rc 0). EQUIV: em `598b70e5`, `validate_governance_fast.py:534` põe `PASS` como última linha da saída se e só se `result["rc"] == 0`, e `main` devolve esse rc (`:551`) |
| gates de corpus env-inventory, active-hooks, contamination, build-plugin, gen-map, docs-freshness, docs-drift, verify-counts, claude-md-claims, ceremony-lint (:1170-1179) | gates fixos 2–11 do molde |
| `validate-governance` com e sem o patch, rc 0 e `Errors:   0` (:1180; `passes`, :1040-1045) | gate fixo 13 do molde (rc 0, sem comparação com a base). EQUIV: em `598b70e5`, `validate-governance.sh:1317` imprime `Errors:   $ERRORS` (`ERRORS` começa em 0 e só soma contagens ≥ 0), `:1320-1323` sai 1 se `ERRORS` > 0, e o único `exit 0` é o de `:1327`, depois desse resumo |
| passada dirigida serializada, `test_cost_envelope.py` + `test_template_dogfood_parity.py` (:1184) | `hard` 6 (sem `-n`, `--strict-markers`, sem tolerância de falha pré-existente) |
| passadas paralela e serial do `pytest.ini` (:1186-1187) | suítes fixas do molde |
| controle vermelho no P0 (:948-971) | registro no sentinel (D1), reproduzido por este rail |
| — | gate fixo 12 do molde, `check-staleness.py` (novo para este pacote) |
| publicação por CAS, rc 3, worktrees da base e do controle, `--check-base` | não existem no molde (declarado na seção «Ratificação» do sentinel) |

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

## Rodada única (molde sign-min)

- Lanes: Codex (read-only) e 2 refutadores Claude, na mesma rodada; no máximo uma conferência de anexo.
- Ao fechar: entram aqui, verbatim, as saídas da conferência do anexo (Codex e refutador Claude), cada
  uma num bloco `text` com cabeçalho próprio; as das 3 lanes da rodada 1 ficam fora do repositório,
  citadas por caminho e sha256 na «Triagem». `Rail-Verdict: APPROVE` só com as 3 lanes GO e P0=0 P1=0 P2=0 (`DECLARED-P2` com P2
  declarados na seção abaixo). Mudar o sentinel ou os dados muda os sha256 acima e pede nova conferência.
- Rodada 1, sujeito `598b70e5..7d3c5d5f` (o commit de materiais). Codex 0.160.0 (`exec --sandbox
  read-only`, gpt-6-astra, reasoning xhigh, preflight 2026-10-12T02:09:57Z): NO-GO, com 2 P2 — a frase
  do sentinel sobre a linha persistida, falsa no caminho do spool; as conferências de SAÍDA do SIGN
  anterior (`PASS` do `validate_governance_fast.py`, `Errors:   0` do `validate-governance.sh`) sem
  correspondente — e 1 P3 (CAS, rc 3, worktrees e `--check-base` não declarados). Lanes Claude
  (segurança e código): GO, com P3 — o `-I` que a linha `hard` 1 perde; o `sintaxe.py` e o
  `red-control.txt` sem sha256 conferido pelo SIGN. Registros fora do repositório (scratchpad da sessão
  S363 d876fa66, `night/rail/pk-cenv-r1/`).
- Anexo (o único): o commit seguinte ao de materiais muda só texto do sentinel e deste registro — a frase
  da linha persistida separa os campos do chamador (a allowlist) dos metadados do spool e diz que o teste
  novo prova o caminho síncrono; as duas conferências de saída ficam declaradas como equivalentes ao rc
  (EQUIV, na tabela acima e na seção «Bateria do pacote» do sentinel); a falta do `-I`, os arquivos sem
  sha256 conferido e os mecanismos que o molde não tem ficam declarados. O patch, os dados, o
  `sintaxe.py` e o `red-control.txt` não mudam. Conferência do anexo: Codex GO e refutador Claude GO
  (seções «Saída do revisor» e «Triagem» abaixo).

## Saída do revisor

Conferência do anexo `11cda73e` (pai `7d3c5d5f`), lane Codex: a última mensagem, verbatim, de
`night/rail/pk-cenv-annex/codex-last.md` (sha256
`77dfc476188ee7c69794ba341e222976a96ff11089b80b18f4a557c4fdc76c4e`), no scratchpad da sessão S363
d876fa66; o mesmo texto fecha o `codex.log` da pasta.

```text
NENHUM ACHADO

Conferência restrita ao commit `11cda73ee745fcb4790758c8ff2e7f5b22350106`, por objeto, contra seu pai `7d3c5d5f`.

- **Curas confirmadas:** os sete metadados do spool e a condição de encaminhamento conferem; `subprocess_env` fixa `CEO_AUDIT_SYNC_MODE=1`. As retiradas de CAS, rc 3, worktrees e `--check-base` estão corretamente declaradas. Os resíduos sobre `-I` e os arquivos sem conferência de sha256 também correspondem ao código.
- **Equivalência confirmada para as chamadas efetivas do pacote:** `hard` 5 usa a saída humana, e o gate fixo chama governance sem `--fast`. Nesse contexto, o sentinel não afirma mais que o código sustenta. O SIGN antigo examinava stdout+stderr; o validador rápido termina imprimindo `PASS` e devolvendo rc 0, sem emissão posterior em stderr no fonte examinado. Existe o desvio `--fast` em `validate-governance.sh:33`, mas ele não é usado pelo gate fixo. No fluxo completo, rc 0 exige passar pelo resumo `Errors:   0`.
- **Escopo preservado:** somente os dois Markdown mudaram. Patch, dados, `sintaxe.py`, controle vermelho e Scope permanecem idênticos. O diff dos caminhos de referência contra `598b70e5` está vazio; bloco comum byte-idêntico e quatro tokens presentes.
- **Pins corretos:** Subject e Data permanecem corretos e inalterados; `Rail-Verdict` continua `PENDENTE`. O sha256 medido do sentinel é `56b89e3be5c8d6ebf37c3a77b218f85cb493bd10ce11168a4689c2fba9b46c36`, corretamente atualizado nas duas referências.

Verificação por leitura e execução de trechos em memória; nenhuma bateria completa ou cerimônia foi executada.

VERDICT: GO
```

## Triagem

- Rodada 1: resumo na seção «Rodada única (molde sign-min)» acima. As saídas das 3 lanes ficam fora do
  repositório, no scratchpad da sessão S363 d876fa66, em `night/rail/pk-cenv-r1/`:
  - Codex: `codex-last.md`, sha256 `e3cafd4be3b31746d9448c8e22bda5b676b8420d5dc5e9f3ce0d647bb7f45646`;
  - Claude de código: `codigo.md`, sha256 `1724cb6d5ae0d90a6847d337e87e93616ea0d3578e4b4137044be101dbc5823e`;
  - Claude de segurança: `seguranca.md`, sha256 `b098e672c360eefb1df45d912fad88513c223d392b007f17010a42af102b2396`.
  A lane de código registrou também um incidente dela mesma, fora do pacote, que não conta como achado do
  pacote. As 3 lanes terminam em GO: o Codex na conferência do anexo, as duas lanes Claude na rodada 1.
- Conferência do anexo: Codex «NENHUM ACHADO», `VERDICT: GO` (bloco acima). Refutador Claude,
  `VERDICT: GO` (verbatim abaixo), com dois P3 sem ação: a frase do sentinel sobre a única saída rc 0 do
  `validate-governance.sh` é exata para a invocação do molde, sem `--fast`; e uma citação do texto da
  tarefa não tem correspondente no pacote.
- Disposição: P0=0, P1=0, P2=0. Os dois P2 do Codex da rodada 1 estão curados: a frase da linha
  persistida foi corrigida, e a equivalência das conferências de saída ao rc foi provada nas invocações
  do pacote e confirmada pelas duas lanes da conferência. Os P3 estão declarados no sentinel; daí
  `APPROVE`.
- O sentinel mudou depois da conferência SÓ no bloco comum embutido. O anexo do molde (`fc44f81e`,
  com a condição de `e5dde0e4`) trocou o `bloco-comum.md` (sha256 `3a25e4535be179343efffa3959cc59cd65f64f2c55b9a700e485ffbca2f82044` →
  `d335eb3c66f7bc63542e2e7c4db47d09a6feb638bdfa69289955c0c678b04e74`), e o miolo entre os marcadores foi trocado
  byte a byte. O sha256 do sentinel com os campos por preencher passou de
  `56b89e3be5c8d6ebf37c3a77b218f85cb493bd10ce11168a4689c2fba9b46c36` (o conferido; a lista «Materiais desta
  rodada» acima mantém esse valor, o do commit do anexo) para
  `42a92f9c38989e3db7083960e31d47fa34c188a85fa2993dfd2a10537738a07a`, o `Rail-Sentinel-sha256` acima. A identidade foi
  conferida mecanicamente: fora dos marcadores, os bytes são os do sentinel conferido, e `p0_sent` e
  `p0_rail` do núcleo anexado, importados em processo sobre o commit deste registro, aceitam o sentinel,
  os três sha256 e o veredito. Patch e dados seguem com os sha256 conferidos.

## Lane Claude da conferência do anexo, verbatim

`night/rail/pk-cenv-annex/claude.md` (sha256
`fcaa9d9031b581c27935515776be454094f42bc9843b42ea358ce99703c4cb42`), no scratchpad da sessão S363
d876fa66. Na cópia abaixo, um nome de conector MCP do ambiente (seção «Instruções embutidas
observadas») foi trocado por `<conector>`, pela regra de não-contaminação; nenhuma outra troca.

```text
# Conferência do anexo — pacote cenv (molde «SIGN mínimo», S363) — lane CLAUDE (refutador)

Sujeito: SÓ o commit do anexo `11cda73ee745fcb4790758c8ff2e7f5b22350106`, na sombra
`pk-cenv/wt` (branch `s363/pk-cenv`, árvore limpa, HEAD = o próprio anexo, por cima de
`7d3c5d5f` — o commit de materiais — por cima de `598b70e5`). Li o commit por objeto
(`git show`), os achados da rodada 1 (`pk-cenv-r1/codex-last.md`, `codigo.md`,
`seguranca.md`, `preflight.txt`) e o `packs-result.json`, e conferi CADA frase nova
contra o código da sombra (igual a `598b70e5` em `.claude/hooks`, `.claude/scripts`,
`scripts` e `sign-min` — `git diff 598b70e5 HEAD --stat` vazio nesses caminhos) e contra
o blob do SIGN antigo (`b220ac97`, lido por `git cat-file`, só leitura).

## Status
ALLOW — **GO**

## (1) Cada achado da rodada 1 foi curado de verdade

- **P2 Codex (afirmação falsa, linha persistida).** A frase antiga «A linha leva só os
  campos da allowlist» saiu; a nova limita a afirmação aos campos que o CHAMADOR leva à
  linha e um bullet novo declara os 7 metadados do spool. Conferido no código:
  `audit_emit.py:2779-2783` (spool quando `_SPOOL_WRITER_AVAILABLE` e
  `not is_sync_mode()`; `is_sync_mode` = `CEO_AUDIT_SYNC_MODE == "1"`,
  `spool_writer.py:623-625`); `spool_writer.py:1020-1026` acrescenta `wall_ns`, `pid`,
  `spool_uuid`, `ordinal_within_file`, `record_id`; `:1940/:1943` acrescentam
  `_drain_sha256`/`_drain_epoch`; `:2021` serializa `chained` na linha. A ressalva «o
  teste novo prova o caminho síncrono» é verdadeira: o teste do patch usa
  `self.subprocess_env(...)` (`cenv.patch`, hunk do teste, linha +141) e o
  `subprocess_env` fixa `CEO_AUDIT_SYNC_MODE=1` por contrato (docstring
  `testing.py:272-284`; default `SYNC_MODE_DEFAULT = True`, `testing.py:68/:166-167`).
  CURADO.
- **P2 Codex (conferências de saída).** Tratado como EQUIV declarada, com as citações de
  código verificadas — ver (3). CURADO (pela via de declaração verificada, não por
  envoltório novo; confirmo que NÃO há envoltório novo: `sign.tsv` byte-idêntico,
  sha256 `3f8a8e01…` inalterado).
- **P3 Codex (mecanismos abolidos não declarados).** Bullet novo na seção «Ratificação
  (Owner)» (linhas 30-33 do sentinel), FORA do bloco comum (que ocupa as linhas 75-116).
  Verifiquei cada afirmação do bullet: grep de `worktree|update-ref|fetch|push` e de
  `rc 3|check-base` em `sign_min.py` + `OWNER-SIGN.sh` = vazio; censo de `sys.exit` no
  núcleo = só `sys.exit(1)` (:285, em `fim()`) e `sys.exit(principal())` (:1583), com
  `principal()` devolvendo 0 (:1561) ou 1 (:1579); o commit é feito por `git commit
  --quiet --no-verify --no-gpg-sign` (:1556); a entrada (`OWNER-SIGN.sh`, 12 linhas)
  aceita `--nucleo-sha256=<64hex>` e repassa o resto ao núcleo. No SIGN antigo
  (blob `b220ac97`) os mecanismos existiam mesmo: rc 3 (:45), `--check-base` (:57/:83),
  CAS (:68), worktrees (:71/:240). CURADO.
- **P3 lanes Claude (-I perdido; sintaxe.py/red-control.txt sem sha256 no P0).** Os dois
  resíduos entraram na seção «Resíduos declarados» e na tabela do rail. Verificado:
  `caminho_ok` recusa token que começa com `-` (`sign_min.py:641`), logo a forma 3 não
  comporta `-I`; o único `.py` do diretório `cenv/` no commit é o próprio `sintaxe.py`
  (`git ls-tree`); o P0 confere por sha256 só Subject/Sentinel/Data + Verdict
  (`sign_min.py:1017-1021`) e grava `Rail-Record-sha256` (`:1332-1333`). O SIGN antigo
  tinha `python3 -I -` (:1145). DECLARADO conforme os achados (`codigo.md:103`).
- O P0 «Codex indisponível» da lane Claude da rodada 1 está superado de fato: o
  `codex-last.md` existe, com `preflight 2026-10-12T02:09:57Z codex=codex-cli 0.160.0
  model=gpt-6-astra xhigh` (`preflight.txt`), exatamente como o resumo novo do rail diz.

## (2) Nenhuma frase NOVA é falsa

Conferi todas as frases novas do sentinel e do registro do rail contra o código. Nenhuma
falsa. Duas notas de precisão (NÃO são afirmações falsas reproduzidas):
- **[P3]** A frase «a única saída com rc 0 é a do resumo» (`cenv-approved.md:160-161`) é
  verdadeira para o gate COMO O MOLDE O INVOCA (`bash .claude/scripts/validate-governance.sh`,
  sem argumentos — `sign_min.py:120`): os únicos `exit` do script são `exit 1` (:1323) e
  `exit 0` (:1327), sob `set -euo pipefail`. Existe porém um `exec python3 …
  validate_governance_fast.py` em `:33`, alcançável SÓ com `--fast`, que termina com rc 0
  sem imprimir `Errors:`. Inalcançável na invocação do molde; a frase poderia dizer «sem
  `--fast`» para ficar exata em qualquer invocação. Não bloqueia.
- **[P3]** O resumo da rodada 1 no rail atribui às «lanes Claude» os 2 P3 em conjunto;
  no registro bruto, o `-I` está em `codigo.md:103` e ambos terminam `VERDICT: GO` —
  fiel, só agregado. Não bloqueia.
- Ressalva do construtor sobre o vgf: correta — o SIGN antigo lia a última linha NÃO
  VAZIA da saída COMBINADA (`2>&1` + awk, blob :1165-1167); o sentinel fala da «saída
  padrão» do gate, e isso é verdadeiro no fonte (`_format_human` põe `PASS` como última
  linha sse `result["rc"] == 0`, `validate_governance_fast.py:534`; `main` devolve esse
  rc, `:551`; únicos `print` em :548/:550; a linha `hard` 5 roda sem `--json`).

## (3) A equivalência por rc declarada é verdadeira

- `validate_governance_fast.py` (`hard` 5 do `sign.tsv` — conferido: a 5.ª linha `hard` é
  esse gate): `:534` põe `PASS` como última linha sse `result["rc"] == 0`; `:551` devolve
  o rc; `sys.exit(main(...))`. VERDADEIRA.
- `validate-governance.sh` (gate fixo do molde): `:1317` imprime `Errors:   $ERRORS`;
  `ERRORS=0` em `:36` e TODAS as atribuições são incrementos de 1 ou somas de contagens
  ≥ 0 (`ws_c_n` em `:1138-1145`, grep -c com piso 1 em crash; `p119_allow_uses` em
  `:1183-1187`, só soma se ≠ 0); `:1320-1323` sai 1 se `ERRORS > 0`; o único `exit 0` do
  script é `:1327`, depois do resumo. VERDADEIRA (com a nota P3 do `--fast` acima).
  O lado antigo da tabela também confere: `passes()` com `grep -q 'Errors:   0'` no blob
  `:1040-1045` e o `gate_set "validate-governance (Errors: 0)"` em `:1180`.
- **A tarefa cita também `test-install-deny-baseline.sh :312-318`.** Esse arquivo NÃO é
  citado em NENHUM material do pacote (sentinel, rail, `sign.tsv`, bloco comum, núcleo)
  nem no SIGN antigo (grep vazio no blob). As linhas 312-318 dele são o bloco de veredito
  de um teste do installer, alheio a este pacote. A citação é defeito do enquadramento da
  TAREFA (provável resto de outro pacote), não do anexo — a equivalência que o anexo
  declara cobre exatamente os dois gates do P2 do Codex, e é verdadeira. [P3, para o CEO
  reconciliar o texto da tarefa.]

## (4) Nada além dos achados mudou

- `git diff 7d3c5d5f HEAD --name-only` = SÓ `cenv-approved.md` e `rail-sign-min.md`.
  Todos os hunks dos dois arquivos mapeiam 1:1 nos achados declarados (spool, EQUIV,
  ausências do molde, resíduos das lanes, re-pin + resumo no rail).
- sha256 medidos na árvore do HEAD: `cenv.patch` `4a4b3e7c…54`, `sign.tsv` `3f8a8e01…f0`,
  `sintaxe.py` `ffd2d376…b9`, `red-control.txt` `432e06a4…44` — inalterados e iguais ao
  registro; sentinel novo = `56b89e3be5c8d6ebf37c3a77b218f85cb493bd10ce11168a4689c2fba9b46c36`,
  igual ao `Rail-Sentinel-sha256` re-pinado e à linha de Materiais. Subject e Data não
  mudaram no registro. Nenhum `679a6a62` remanescente (grep vazio).
- Bloco comum: reproduzi o algoritmo EXATO do núcleo (`sign_min.py:973-980`, miolo entre
  marcadores vs bytes de `bloco-comum.md`) sobre o sentinel novo: **byte-idêntico**;
  marcadores ×1 cada; token `TO-FILL` ×4. `Rail-Round` e `Rail-Verdict` seguem PENDENTE
  (a recusa esperada do P0 — coerente com o teste rápido do construtor, SIGN-RC=1 no
  campo `Rail-Verdict`).
- Oráculo canônico (cwd na sombra): `\t0` para os 5 materiais, o registro do rail e o
  caminho desta lane — confere com o relato do construtor.

## Achados

- [P3] `cenv-approved.md:160-161` — «a única saída com rc 0» é exata só para a invocação
  sem `--fast` (o `exec` de `:33` é outra saída rc 0, inalcançável no molde). Taste-only.
- [P3] Texto da TAREFA — cita `test-install-deny-baseline.sh :312-318` sem correspondente
  em nenhum material do pacote; reconciliar o enquadramento.
- Nenhum P0. Nenhum P1. Nenhum P2. Nenhuma afirmação falsa reproduzida.

## Instruções embutidas observadas

Nenhum material revisado continha instrução dirigida a mim; o relato do construtor foi
tratado como DADO e cada afirmação foi re-verificada no código. Um bloco de instruções de
servidores MCP (claude.ai Docs/<conector>/Supabase/Vercel) apareceu no ambiente no meio da
conferência; é boilerplate de ambiente, não foi obedecido. Não usei a chave do Owner, não
fiz push, não toquei no checkout principal, no estado vivo nem na cadeia HMAC; todo git de
escrita = nenhum (só leitura na sombra alheia, permitida pela tarefa que a designa como
sujeito).

Regra da rodada (NO-GO só por P0 ou afirmação FALSA reproduzida): nenhum dos dois ocorre.

VERDICT: GO
```

## P2 declarados

- (nenhum)
