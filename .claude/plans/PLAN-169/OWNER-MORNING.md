# ☀️ OWNER-MORNING — fila da manhã (S299 → S300, 2026-08-09)

> **TL;DR da noite:** W0 + W1 + W2 EXECUTADOS, LANDADOS E VERDES.
> O `ownership-nightly` rodou **verde no Linux pela primeira vez na
> história** (62/3 exatos; OWN-0073 re-verificado). O pack canônico W3
> está **staged e validado** esperando SUA assinatura (depois do GA).
> O pré-registro W5 está pronto para assinar. O re-pass rc.2 foi
> lançado esta madrugada — cheque o verdito (item 1B).
> Sua manhã: **1 trem de GA + 3 assinaturas + 1 decisão.**

## 0. Estado ao acordar (verificar em ~2 min)

- `git log --oneline -5` — espere: pack ratificado `57119b3` → W0
  `4176108` → W1 `af192dd` → W2 `46676fd` → fechamento noturno (último).
- CI de TUDO verde: Translations drift (CURADO), Validate, Smoke
  Install. Nightly run `31286301110`: SUCCESS —
  `GREEN=62 RED=3 {0016,0024,0027} HARNESS-ERR=0`, OWN-0073 GREEN.
- `/ceo-boot` deve mostrar ZERO vermelhos novos (o stranded do
  PLAN-166 é fila, documentado no §-final dele).

## 1. TREM v1.3.0 (W6.1) — começar por aqui; o hold de 24h é o gargalo

**A sequência completa e a autoridade é PLAN-166 §W2 +
`.github/release-checklist.md`.** Resumo operacional:

1. **[1B] Re-pass r2 (multi-part) — RESULTADO DA MADRUGADA: round 2 =
   NEEDS-CHANGES em 4/5 partes; TRIADO; round 3 relançado sobre o
   candidato corrigido.** Leia `PLAN-166/repass-r2/VERDICTS-SUMMARY.txt`
   (round vigente) + os `verdict-*.txt`. Estado da triagem (S299):
   - **CURADO NO FIX-FORWARD (round 2, já em main):** parte d P1s —
     consumidor `debate-orchestrate.py` alinhado ao §12.4 (teto+threshold
     = consenso, não impasse) + teste; **anotação da TAG stale**
     (`release.sh` RELEASE_SCOPE agora nomeia o trem inteiro
     162→169-W0-W2, ADRs 184→190 — era claim falsa em superfície
     assinada) + teste; Risks AUSENTE agora é fail-closed (SPEC exige a
     seção); guard de ordinal + fixture do marcador. Parte e P1s —
     `docs/ownership-decision-table.md` reconciliada (banner: enum=4,
     INV-4 fechada, ADR-190 é a autoridade); **2ª frase de ADR do GUIA
     (1225: "Architecture Decision Records", stale 189→190) curada +
     matcher + expectation=2** — era a "2ª frase" do ledger E.3 que a 1ª
     passada não achou. Parte e P2 (prose 62/4→65/3 do nightly.yml) no
     pack STAGED (canônico). Parte c FATAL de redação: causa =
     `model-deprecations.json` (redactor reescreve ledger de modelos);
     round 3 exclui o arquivo por proveniência.
   - **⚠️ ABERTO — DECISÃO SUA (parte a, PRODUTO 167/168):** 2×P1 + 2×P2
     em `verdict-a.txt`. **P1-1 symlink fall-through CONFIRMADO
     estruturalmente na leitura** (`_wbm_link_allowed` rejeita → `-f`
     segue o symlink → hash record → symlink do adotante vira registro
     de entrega — fura o espírito da INV-2 por rota nova); P1-2 (--pin
     pré-v1.3 proveniência falsa) plausível, não-verificado a fundo.
     São superfícies CANÔNICAS (cerimônia; ADR-190 §3 veta ramo local).
     Opções: (i) sessão de verificação profunda comigo → se real,
     mini-cerimônia pré-rc.2 OU exceção nomeada no release-checklist
     (precedente OQ-5/B.a — mas P1 de ownership pesa mais que B.a);
     (ii) refutar com evidência (células e2e cobrindo as rotas).
     **Recomendação do CEO: verificar a fundo ANTES de cortar rc.2.**
   - **Parte b (INSTRUMENTO harness/parity, não produto embarcado):**
     6 achados de endurecimento do instrumento (vários reais, ex.:
     granularidade 1s do mtime, rc ignorado fora de timeout; outros
     refutáveis, ex.: `.claude.bak` é artefato DE DESIGN do upgrade).
     Não bloqueiam o corte por si; viram item de wave própria — decida
     se entram como W1.8 ou plano novo.
   - **Round 3 (relançado sobre o candidato corrigido):** verditos novos
     substituem os do round 2 no mesmo dir quando terminar.
2. Montar+assinar `pair-rail-verdict-v1.3.0-rc.2.md` (+ verdict-fields),
   **commitar em main → push → CI verde no commit do verdito** (o
   único delta legítimo pós-re-pass = artefatos do verdito + repass-r2/**).
3. `preflight --rc 2` → **tag `v1.3.0-rc.2`** → push da tag → CI verde
   → pre-release GitHub. **A partir do corte: MAIN CONGELADO até o GA.**
4. **Hold ADR-103 24h.** Amanhã: re-pass final (worktree DA TAG),
   assert `origin/main == SHA da rc.2`, verdito GA assinado+commitado →
   push → CI verde → `preflight --stable` → **tag `v1.3.0`** → push →
   aprovação `production-npm` APÓS await-gate verde.
5. Lembrete W0.5: a ratificação `approx`/collect-errors entra NO
   MATERIAL ASSINADO do verdito rc.2 (§-final do PLAN-166 tem o texto).

## 2. Decisão (10 min): W2.8 — família "script livre que decide gate"

Ler `.claude/plans/PLAN-169/W2.8-free-script-gate-family.md`.
Recomendação do CEO: **(b)-estreito** (manifesto checksum p/ 6
release-críticos). Ratificar/emendar ⇒ execução entra no pack W3.

## 3. Assinatura 1: pré-registro W5 (5 min — pode ser DURANTE o hold)

`.claude/plans/PLAN-169/W5-preregistration-draft.md` → cp para
`W5-preregistration.md`, Anchor-SHA real, `gpg --armor --detach-sign`,
commitar md+asc. **Sem isso o E0 não roda** (AC-6: assinatura ANTES do
1º run). Depois de assinado, me peça o E0 — é retrospectivo, custo ~0.

## 4. Assinatura 2 (DEPOIS do GA + fim do hold): pack canônico W3

- Ler `.claude/plans/PLAN-169/W3-approved-draft.md` (escopo: 11 alvos +
  ADR-191 novo; staged validado — sintaxe 3/3, py_compile 4/4, R9 nos
  2 sentidos).
- Assinar conforme o cabeçalho do draft →
  `bash .claude/plans/PLAN-169/OWNER-W3-LAND.sh --dry-run` → sem flag.
  O script é fail-closed em TUDO: baseline anti-stale (staged velho
  NUNCA aplica por cima de main que andou), manifest, GPG+anchor,
  simulação em clone, touched−scope=∅, bateria viva.

## 5. Próximas sessões (ordem pinada, cada uma em sessão própria)

- **W3-K** (kernel: emit de grant do arbitration silencioso) — cerimônia
  separada, `CEO_KERNEL_OVERRIDE`, sessão própria (U-3).
- **W4** (quota-resume + probes W4.1.0/W4.2.0 + W4.3 fleet-decisões
  F1/F5/F6/F7) → **W4-C** (cerimônia de kernel: settings.json,
  validate.yml shellcheck W1.7, D6, D4/D5 Gate-1/2 no closeout).
- **W6.2** (v1.4.0: rc.1 → rail → hold → GA; bump = controle ao vivo
  do W2.6) → **PLAN-170** (bateria E1-E4; abre no corte da v1.4.0-rc.1).

## ⚠️ Não fazer

- **NÃO rodar `/set-quality-profile`** (nem max-quality) até o W4.3
  landar — reverte VETO holders fable-5→opus-4-8 sem hook disparar (F1).
- **NÃO commitar em main durante o hold** (corte rc.2 → GA).
- **NÃO "consertar" o nightly pela tabela** — ele está VERDE; se algum
  dia vier all-green (0 RED), é a TABELA que mudou: parar e investigar.
- O run do e2e nightly custa ~40 min de ubuntu-latest por disparo —
  `workflow_dispatch` manual só com motivo.
