# W28-approved — sentinel do trem W2.8 + break-glass (DRAFT — assinar como W28-approved.md)

> Assinatura em um passo: `! bash ~/canhada-labs/OWNER-W28-SIGN.sh`
> (gera este arquivo com Anchor-SHA real, assina, dry-run, land).

Plan: PLAN-169
Wave: W2.8 (família gate-scripts, rota (b)-narrow) + W0.9 (break-glass)
Anchor-SHA: <HEAD-NO-MOMENTO-DA-ASSINATURA>
Data: <AAAA-MM-DD>

## Ratificação (decisão estruturada S312, 2026-08-18 — verbatim)

- W2.8: **"Ratificar (b)-narrow"** — fecha a classe "script livre que
  decide release sem pin"; custo do re-pin aceito (fail-loud por design).
- W0.9: **"Aceitar, renumerado"** — break-glass ADR aceito; 191→193
  (191 tomado pelo spawn-acceptance-contract-v2 do Lote B).

## Scope

```
.github/workflows/release.yml
.github/workflows/npm-publish.yml
.github/workflows/smoke-install.yml
.github/workflows/ownership-nightly.yml
RELEASE.md
CLAUDE.md
README.md
README.pt-BR.md
npm/README.md
docs/CTO-GUIDE.md
docs/FAQ.md
docs/GUIA-COMPLETO.md
.claude/adr/ADR-192-gate-scripts-checksum-manifest.md
.claude/adr/ADR-193-break-glass-repo-kill-switches.md
.claude/governance/gate-scripts-manifest.txt
```

## O que este trem muda

1. **4 workflows** ganham o step "Gate-scripts integrity (W2.8 checksum
   manifest)": `shasum -a 256 -c` do manifesto ANTES de qualquer membro
   votar na própria integridade. Manifesto ausente ou drift = fail LOUD.
2. **Manifesto** com 9 membros (verify-counts, validate-governance,
   _release_tag_guard, check-canonical-doc-freshness,
   ownership-nightly-gate, ownership-expected-reds, release.sh,
   validate-pair-rail-verdict, await_release_gate) — **REGENERADO DO
   VIVO no momento do land** (o staged é referência; nunca hash stale).
3. **ADR-192** (gate-scripts, ACCEPTED) + **ADR-193** (break-glass,
   ACCEPTED, renumerado de 191).
4. **RELEASE.md**: 31→32 steps (o novo step do release.yml).
5. **Contagem de ADRs 192→194** nas 7 superfícies derivadas (CLAUDE.md,
   READMEs, CTO-GUIDE, FAQ, GUIA) — tolerance=0 dos gates exige o bump
   no MESMO trem que adiciona os 2 ADRs.
6. Contrato novo daqui em diante: edit legítimo num membro exige re-pin
   do manifesto NO MESMO commit (rota: cerimônia canonical-edit).

## Fora deste trem

Itens já landados na W3 (`e5ce982`); staged-w3/consumed intocado;
staged-w3/pending-w28 vira histórico após este land.
