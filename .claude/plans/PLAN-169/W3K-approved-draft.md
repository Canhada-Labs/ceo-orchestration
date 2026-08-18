# W3K-approved — sentinel da cerimônia de KERNEL (DRAFT — assinar como W3K-approved.md)

> Assinatura em um passo: `! bash ~/canhada-labs/OWNER-W3K-SIGN.sh`
> ⚠️ **Sessão DEDICADA (regra U-3 do próprio PLAN-169).** Esta cerimônia arma
> `CEO_KERNEL_OVERRIDE`; nunca a encadeie com outra. O land script recusa
> rodar se o override já vier do ambiente, arma no menor escopo possível,
> desarma logo após o apply e tem `trap EXIT` de backstop.

Plan: PLAN-169
Wave: W3-K (auditoria do grant de override de kernel — ledger E.2)
Anchor-SHA: <HEAD-NO-MOMENTO-DA-ASSINATURA>
Data: <AAAA-MM-DD>

## Scope

```
.claude/hooks/check_arbitration_kernel.py
.claude/hooks/tests/test_arbitration_kernel_grant_emit.py
```

## A premissa do plano estava ERRADA — e o defeito real é pior

O ledger E.2 e o §W3-K afirmavam: *"os emits do caminho GRANT são silenciosos,
engolidos por `except Exception: pass`; suspeita: `ceremony_sha` recebe um
PATH em vez de um sha de 64 hex"*.

Reprodução hermética (comando completo registrado no pack, com controle
positivo e negativo) mostrou que **não é isso**:

- `kernel_extension_landed` **LANDA intacto** — a ação está em
  `_EMIT_GENERIC_PASSTHROUGH` (`audit_emit.py:1751`), e
  `emit_kernel_extension_landed` só faz `ceremony_sha[:64]`, sem validar
  formato. Evento gravado com `hmac_error: null` e `audit-log.errors` vazio.
  O `except Exception: pass` **nunca dispara**.
- O defeito real é **outro evento**: `veto_triggered
  reason_code=kernel_override_used` nunca foi escrito, porque
  `main()` decide o caso do grant com `decision == "allow"`, lendo `decision`
  de volta do JSON que o **próprio** `_emit_allow()` produziu — e esse JSON
  nunca carrega a chave `decision` (o comentário do código diz que `allow` no
  topo é inválido no wire do PreToolUse). `git log -S'"decision": "allow"'`
  volta VAZIO: **o branch nasceu morto**, nunca houve regressão.
- Consequência de governança: o `systemMessage` do hook e o docstring do
  módulo mandam o operador procurar exatamente o evento que nunca existiu.
  **Uso de override de kernel não era auditado pelo canal documentado.**

## Por que ninguém tinha pego

O teste que "cobria" esse caminho
(`test_check_arbitration_kernel_v214.py:83,93,124`) chama `_audit_block(...,
override_used=True)` **direto**, contornando `main()`. `_audit_block` está
correto; quem nunca era alcançado era o chamador. Instrumento verde com a
pergunta errada — a classe dominante deste repo.

## O que muda

1. O caminho do grant deixa de depender de parsear a própria saída do hook: a
   decisão é derivada da AUSÊNCIA de block + override armado + path de kernel.
   `_emit_allow()` **não** ganha a chave `decision` (mudaria os bytes de egress
   do hook, e a chave é inválida no wire).
2. `ceremony_sha` passa a carregar um digest de verdade em vez de um path
   truncado no meio.
3. Teste **POSITIVO** end-to-end do grant — o que faltava — rodando `main()`
   como o harness roda, com controle NEGATIVO no mesmo arquivo (sem override:
   bloqueia e não emite o evento de grant).

## Prova pré-assinatura

25 testes do arquivo novo passam (exit code verdadeiro, lido de arquivo —
nunca `pytest | tail`). O mesmo teste contra o hook **pré-fix** falha em 12
casos: o instrumento tem dentes. As 13 falhas do conjunto amplo de 9 suítes
são **byte-idênticas** às do espelho de controle rodando o hook original —
artefato do espelho, não regressão introduzida.

## Follow-up nomeado (não silencioso)

`_resolve_plan_id_or_unknown()` devolverá `unknown` em quase toda cerimônia
real, porque `resolve_plan_id` exige um `plan_transition` da própria sessão —
a mesma causa-raiz que o PLAN-179 está curando. Fica registrado aqui: quando o
pack do 179 landar, este callsite melhora sozinho.
