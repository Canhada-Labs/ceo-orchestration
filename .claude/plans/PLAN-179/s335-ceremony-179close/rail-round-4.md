# wave-179close — rail codex rodada 4 (sombra + curas r1-r3, 2026-08-31 S335)

Rail-Verdict: CHANGES-REQUESTED (1 P1 + 1 P2 — ambos verificados REAIS; curados ANTES da r5)

Comando: idêntico às anteriores. Saída: `<scratchpad S335>/179close-r4.txt`
(12.095 linhas), TREE-INTACT.

## Os achados (e o que cada cura fez)

1. **[P1] Field-set da verificação ≠ field-set da assinatura** — o produtor
   assina EXCLUINDO `hmac` **e** `hmac_error`
   (`audit_emit._write_event`, `entry_sans`, confirmado byte a byte); o
   verificador da âncora tirava só `hmac`. Toda linha carregando
   `hmac_error` reprovaria ⇒ falso `start_unknown` sistemático. CURA: o
   verificador espelha o field-set EXATO (`pop` dos dois); o SEED dos
   testes passou a gravar `hmac_error: None` na linha E assinar excluindo
   (como a produção) — o controle agora cai sobre qualquer verificador
   que não espelhe.
2. **[P2] Fallback de id violava o contrato do delta** — sem id no
   payload, `main()` caía em `CLAUDE_SESSION_ID` (spoofable) e depois num
   timestamp fabricado; o SPEC do delta exige «threaded from the harness
   event, no silent default». CURA: `decide()` ganha
   `payload_session_id` (None = compat com chamadores legados/testes;
   "" = payload sem id ⇒ o DELTA é PULADO com breadcrumb LOUD e zero
   emit — fabricar id seria atribuição falsa); o resto do hook segue com
   o id legado. Controle novo:
   `test_no_payload_sid_skips_delta_loudly`.

## Nota de processo

A 1ª tentativa desta rodada (r3 do dia) foi MORTA externamente sem
veredito; o registro vive em rail-round-3.md. Após as curas r3, o
refactor do gate de audit-isolation (patch.dict) entrou pós-dispatch do
r4 — coberto pela r5. Suites pós-cura r4: **73 passed** nas 3 tocadas;
declarado 9-suítes = **305/0**. Harness run3 (patch pré-r4):
**22 PASS / 0 FAIL / 0 SKIP** — run4 re-carimba o patch final.
