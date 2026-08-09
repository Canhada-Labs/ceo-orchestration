# W3-approved — sentinel do pack canônico PLAN-169 W3 (DRAFT — assinar como W3-approved.md)

> **Como assinar (manhã, DEPOIS do GA v1.3.0):**
> 1. `cp W3-approved-draft.md W3-approved.md`
> 2. Trocar `Anchor-SHA: <HEAD-NO-MOMENTO-DA-ASSINATURA>` pelo
>    `git rev-parse HEAD` REAL (o land aborta se divergir).
> 3. `export GPG_TTY=$(tty); gpgconf --kill gpg-agent` (se pinentry chiar)
> 4. `gpg --armor --detach-sign W3-approved.md` (gera `.asc`)
> 5. `bash .claude/plans/PLAN-169/OWNER-W3-LAND.sh --dry-run` → depois sem flag.

Plan: PLAN-169
Wave: W3 (pack canônico único — cerimônia GPG comum, SEM kernel)
Anchor-SHA: <HEAD-NO-MOMENTO-DA-ASSINATURA>
Data: <AAAA-MM-DD>

## Scope

```
scripts/upgrade.sh
scripts/_framework_manifest_set.sh
scripts/tests/test-protocol-pointer-render.sh
.github/workflows/smoke-install.yml
.github/workflows/ownership-nightly.yml
.claude/hooks/check_anti_ceo_overhead.py
.claude/hooks/check_codex_stop_review.py
.claude/hooks/audit_log.py
.claude/hooks/check_agent_spawn.py
.claude/adr/ADR-163-hook-latency-gate-percentile-stability.md
.claude/adr/ADR-186-hook-deadline-policy.md
.claude/adr/ADR-191-break-glass-repo-kill-switches.md
```

## O que este pack muda (resumo por item; staged em `staged-w3/`, MANIFEST.sha256 rastreado)

1. **W3.1 (B.a)** `upgrade.sh`: allowlist POSITIVA de charset no filtro do
   `PROTOCOL_SOURCE` (valor com newline/control char rejeita ⇒ fallback D3)
   + WARNING BARULHENTO no caller quando a chave existe e foi rejeitada.
   `_framework_manifest_set.sh`: guard de newline no gerador — valor
   irrepresentável no sed ⇒ corpo DEGRADED (alvo de cura reconhecido),
   nunca render corrompido, nunca abort. Caso R9 novo no teste de render
   (9/9), validado nos DOIS sentidos contra o staged.
2. **W3.2** `smoke-install.yml`: 2º fator do controle de paridade vira
   CAUSAL (`positive control: FIRED in every mode` + nenhum veredito
   por-modo :0/:2) — fecha a exceção nomeada do AC-4 do PLAN-166 (r6-P2).
3. **W3.3** `check_anti_ceo_overhead.py`: P4 degrada para ADVISORY nos
   tools de apply (Edit/Write/MultiEdit/NotebookEdit); Bash mantém block.
   Evidência: 4 hits legítimos bloqueados (S298 ×2, S299 ×2). R-SEC6:
   cura pelo predicado, sem sentinela persistida.
4. **W2.10-deferidos (fronteira do predicado):** F4
   `check_codex_stop_review.py` default reviewer → `claude-opus-5`; F8+D1
   `audit_log.py` devops → haiku bare + docstrings de frota atualizadas;
   D2 `check_agent_spawn.py` mensagem de bloqueio passa a citar a regra
   REAL (membership em VETO_FLOOR_ALLOWED).
5. **Nightly comment** `ownership-nightly.yml`: tempo observado do run
   saudável (~41 min) no comentário; `timeout-minutes: 90` intocado.
6. **ADRs:** ADR-163 amendment (p95-on-CI substitui mediana; N-adequacy
   nos probes de teste — implementação já landou no W2.2); ADR-186 §5
   nota histórica E.17 (case-fold resolvido em `6b5dd10`); **ADR-191
   NOVO** (break-glass para kill-switches de repo — W0.9/OQ-3 aceito).

## Fora deste pack (não assinar achando que cobre)

- W1.7 shellcheck de `scripts/tests/**` em `validate.yml` = KERNEL ⇒ W4-C.
- W2.8 manifesto checksum ((b)-estreito) = aguarda SUA decisão; se
  ratificar, entra AQUI antes de assinar ou vira pack próprio.
- F1/F5/F6/F7 (decisões de tier/perfil) ⇒ W4.3; D4/D5 (team.md/SKILL.md
  Gate-2 cache-stable) ⇒ closeout de W4-C.

Assinado por: __________________ (Owner, GPG)
