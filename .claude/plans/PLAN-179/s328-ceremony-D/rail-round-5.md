# Pair-rail — PACOTE D, rodada 5 (rodada 3 do rail do MAIN)

**Origem:** `<scratchpad>/railmain-3.txt`, repassados pelo team-lead. Quatro
claims sobre arquivos do meu escopo. Verificados contra o código, nunca
aceitos por autoridade.

**Resultado:** 2 CURADOS com controle positivo, 2 já reportados por mim e
ainda abertos por estarem fora do meu FILE ASSIGNMENT.
Rail-Verdict: REJECT

---

## [P1] "Update the registration-count pins with the new hook" — **JÁ REPORTADO, ABERTO**

> Aplicar esta registração sobe as contagens dogfood/template de 49/46 para
> 50/47, e `test_template_dogfood_parity.py` ainda afirma 49/46. O V4 do land
> falha deterministicamente.

**Terceira confirmação independente do mesmo defeito** — eu já o tinha medido
na simulação de land (`AssertionError: 50 != 49`) e registrado na rodada 3
(§P1-1), e o rail do main agora chega nele por leitura estática.

**Disposição: inalterada.** `test_template_dogfood_parity.py` não está no meu
FILE ASSIGNMENT. Diff exato (3 sítios: `:102` 49→50, `:103` 46→47, comentário
`:101` `50 == 47 + 1 + 2`) entregue ao team-lead, e o remédio **verificado por
mim em clone: 14 passed**. Não toquei no arquivo.

## [P1] "Register the checkpoint hook during upgrades" — **JÁ REPORTADO, ABERTO**

> Para um adopter existente, atualizar só o dogfood e o template não ativa o
> hook: `scripts/upgrade.sh:_merge_lifecycle_hooks_into_settings` hard-codeia
> seis registrações e não tem entrada para `check_ledger_checkpoint.py`.

**Confirmação independente do meu próprio achado da rodada 3 (§P1-4).**
`scripts/upgrade.sh` está fora do meu grant; reportado ao team-lead com a
análise de que a cura certa é fazer a lista **derivar** do template — a mesma
forma que o PLAN-183 aplicou com `delivery-routes.tsv` — e não somar a sétima
entrada literal. Não toquei no arquivo.

---

## [P2] "Treat pathspec files as commit selectors" — **CURADO (reverti a minha própria deferral)**

> `git commit --pathspec-from-file=file` fornece os paths a serem commitados,
> mas consumi-la como opção de valor comum deixa `inv.pathspecs` vazio.
> `_committed_paths()` inspeciona então o conjunto staged INTEIRO, e um
> arquivo de plano staged mas EXCLUÍDO pelo arquivo de pathspec pode gerar um
> registro de checkpoint FALSO para um commit que não vai contê-lo.

**VERIFICADO — e este texto corrige a MINHA avaliação da rodada 3.** Lá eu
deferi o mesmo achado julgando que a cura exigiria uma classificação nova.
Estava errado, e a formulação mais precisa mostra por quê: o resultado não é
imprecisão, é um **registro FALSO** (`ledger_updated` para um commit que não
carrega o ledger). E a resposta certa **já existe no módulo** — `unparseable`
é exatamente o que ele devolve para pathspec explícito, isto é, para "o commit
seleciona paths que eu não resolvo". Aplicar a semântica existente a uma forma
que passou despercebida não é semântica nova; é a mesma.

**CURA:** `--pathspec-from-file` sai de `_COMMIT_VALUE_OPTS_LONG` e passa a
marcar `inv.pathspecs`, nas DUAS formas (`=valor` e valor separado). Daí em
diante o caminho é o já existente: `_committed_paths()` devolve `None` e o
caller reporta `unparseable`.

**CONTROLE POSITIVO (vermelho→verde):** com a forma pré-cura,
`AssertionError: 0 != 1 : []` — nenhum evento de skip, o commit classificado
pelo conjunto staged. Com a cura: **66 passed**.

Lição registrada contra mim: **deferir por "isso mexe em semântica" merece a
mesma verificação que aceitar.** Eu deferi sem checar se a semântica
necessária já estava implementada — e estava.

## [P2] "Force rejection semantics for rejected-entry events" — **CURADO**

> Como `_LEDGER_GATE_DECISIONS` inclui `accept` e o enum de reason inclui
> `ok`, um `emit_generic("ledger_entry_rejected", decision="accept",
> reason="ok", ...)` direto passa por este scrub sem alteração. Isso cria um
> evento assinado cuja ação diz que a entrada foi rejeitada enquanto os
> campos dizem que foi aceita, envenenando a série de rejeição/FPR que este
> ramo deny-by-default existe para proteger.

**VERIFICADO — verdadeiro, e é um furo de forma exata.** No disco:
`_LEDGER_GATE_DECISIONS = frozenset({"accept", "reject"})`, e o scrub coagia
**apenas** valores FORA do enum. `accept` está DENTRO — passava intacto.

O ponto que decide: **a ação já É o veredito.** `ledger_entry_rejected` só
existe para uma entrada rejeitada. Um campo `decision` que a contradiz não é
um dado alternativo, é um registro incoerente — e ele é ASSINADO na cadeia
HMAC, então a incoerência fica permanente e contamina exatamente a série que
o ramo protege.

**CURA:** para esta ação, `decision` é **forçado** a `reject` (o único
produtor legítimo, `_emit_rejection`, só chega aqui com veredito de rejeição,
então forçar é coerente com ele e fecha a porta do `emit_generic` direto); e
`reason="ok"` — que significa NÃO-rejeitada — passa a ser coagido para
`malformed_input`, junto com os valores fora do enum.

**CONTROLE POSITIVO (vermelho→verde), 2 asserções:**

```
AssertionError: 'accept' != 'reject'   <- o evento assinado saía envenenado
AssertionError: 'ok' == 'ok'           <- reason incoerente com a ação
```

Terceiro teste no par oposto: uma rejeição GENUÍNA
(`decision=reject, reason=scanner_hit, family=harness_mimicry`) atravessa
**intacta** — a cura não pode achatar o dado real.

---

## Verificação depois destas curas

| comando (clone fresco, pack aplicado) | rc |
|---|---|
| `pytest` dos 3 arquivos de teste tocados | **0** (76 passed) |
| `check-test-env-hygiene.py` | **0** |
| `check-audit-registry-coverage.py --check` | **0** |
| `validate-governance.sh` (COMPLETO) | **0** |
| `assemble_pack.py` | 25 entradas, MANIFEST confere, 0 IDENTICAL |

## Estado

Cinco rodadas somadas: **12 achados curados** (10 com controle positivo),
2 pushbacks, 3 deferidos, 1 refutado por staleness, 2 abertos fora do grant.

`Rail-Verdict` segue **REJECT** e o SIGN vai recusar assinar — correto
enquanto `CHANGELOG.md` e `test_template_dogfood_parity.py` não entrarem no
pack.
