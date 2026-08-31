# RUNBOOK S335 — executar o que o Owner ratificou no fim da S334

> **Ratificações do Owner (2026-08-31, AskUserQuestion na S334, verbatim):**
> (1) PLAN-179 = **"Fechar tudo"** — pack US7+US8 + AC(a) do W0
> supersedido pela decisão r1-C3 + válvula US2b resolvida; flip `done`
> viaja no patch. (2) Válvula US2b = **"Eta advisory + doutrina"** — o
> PreCompact ganha `eta=(T−F−S)/T` e AVISA; "negar" fica documentado como
> limite do substrato (mesma rota honesta do US9c). (3) PLAN-183 =
> **"Batch menor + começar W1"** — batch canônico completo com rail;
> W1 avança sem promessa de fechar.

## Ordem da noite (S335)

### 1. Pack `wave-179-close` (fecha o PLAN-179)

- **Molde de cerimônia: o pack ADRGATE** (`s334-ceremony-adrgate/` —
  scripts com as curas r1-r8 embutidas; clonar DELE, nunca do F).
  Hooks NÃO são `_KERNEL_PATHS` ⇒ sem `CEO_KERNEL_OVERRIDE` neste pack.
- **US8 (`SessionEnd.py`)**: a spec COMPLETA e assinada está em
  `PLAN-179/staged-w24/SESSIONEND-NOTE.md` (rail stat-only: contagem de
  arquivos de memória mudados por `st_mtime >= session_start_ts`,
  resolução do ts com terminal "não sei" explícito, campos fechados,
  kill-switch; o hook NUNCA escreve memória — torna a OMISSÃO visível).
  Implementar A PARTIR DELA, não de memória.
- **US7 (`check_precompact_continuity.py`, 1173L)**: o snapshot vira
  ÍNDICE do ledger — gatilho por PATHS do commit (emenda r1-C6: NUNCA
  `resolve_plan_id`), aponta `PLAN-NNN/LEDGER.md` + seções + last-commit
  em vez de copiar estado. No MESMO hook, a válvula ratificada:
  `eta=(T−F−S)/T` com `F+S=112638`, `T=998043` (medidos, plano
  L309-310), emitido ADVISORY.
- **Texto do plano no patch** (como o fixture viajou no adrgate):
  US7/US8 → `[x]`; AC(a) do W0 → supersedido pela r1-C3 (citar a
  ratificação de 2026-08-31); US2b → fechado por eta+doutrina; frontmatter
  `status: executing → done` + `completed_at` NO PATCH (o done só é
  verdade no land — por isso viaja nele).
- Testes: `test_check_compaction_continuity.py` (livre) + suite do
  SessionEnd conforme §test-surface da spec.

### 2. Pack `wave-183-batch` (canônicos menores; **KERNEL: toca settings.json**)

- `.claude/settings.json` — regen do skillOverrides:
  `python3 .claude/scripts/skill-budget-generator.py --jq-fragment`.
  O A4 segue VIVO em `:884-885` (`financial-correctness-and-math` e
  `financial-display` como name-only — medido na S334). settings.json ∈
  `_KERNEL_PATHS` ⇒ o LAND deste pack ARMA `CEO_KERNEL_OVERRIDE`
  (contrato vivo: reason SLUG `[A-Za-z0-9._-]{1,120}` + ACK literal
  `I-ACCEPT` — o formato W3K com espaços é RECUSADO EM SILÊNCIO).
- `templates/.github/workflows/validate.yml.template` — header "INERT AS
  SHIPPED" no padrão de `benchmarks.yml.template:3-7` (comentário puro:
  o frozen-subset test NÃO quebra — 11 steps e pins inalterados).
- **AC-5 do 183**: `smoke-install.yml:485` JÁ invoca
  `scripts/tests/smoke-install.sh` ⇒ a perna de ativação da S334 JÁ RODA
  no CI. Verificar se o Check do AC-5 fica satisfeito por REGISTRO
  (provável) — se sim, zero edição de yml e o pack encolhe.
- **W3-P1 (`settings.base.json` de-embed dos 106 overrides): AVALIAR
  ANTES de incluir** — exige coordenação com a arquitetura `_derivation`
  da wave-F (303ae55). Se a rota não for óbvia em 30 min, FICA FORA
  (follow-up), não segura o pack.

### 3. W1 do PLAN-183 (avançar; sem promessa)

Desenho (recon S334, verificado contra o plano :1148-1188): 6 itens —
(1) relativização DENTRO de `_render_protocol_pointer`
(`_framework_manifest_set.sh`); (2) reconhecedor de "absoluto legado" no
molde de `_protocol_pointer_is_degraded` (`:1439`) + re-render byte a
byte + backup, falha PARA preservação; (3) o corpo renderizado passa a
NOMEAR `--protocol-source` (hoje `:1431` só manda "editar"); (4) WARNING
quando ponteiro preservado contém caminho absoluto (ramo PRESERVE_OWNED,
`upgrade.sh:1855-1866`); (5) e2e que move source+target JUNTOS (resolve)
+ e2e que move só o target (erro nomeado); (6) **o monstro**: re-baseline
de ownership — 7 artefatos do §7 do plano, `inv4 assert_sound` editado
NA MESMA wave (senão o Check é insatisfazível), tríade live_content no
`ownership_table.tsv`, 40-70k tokens/2-4 iterações, e o
`ownership-nightly` tem de terminar com o RED id-set EXATO. Começar por
(1)-(5) em sombra; (6) por último.

## Manhã do Owner (3 cerimônias em ordem, cada uma = 4 comandos)

1. **adrgate** (pronta da S334): roteiro em `PLAN-169/OWNER-MORNING-S334.md`
   — já com `export CEO_ADRGATE_SHADOW=...` na primeira linha.
2. **wave-179-close** → PLAN-179 vira `done`.
3. **wave-183-batch** (kernel: o LAND arma o override sozinho).

## Avisos herdados

- Sombra do adrgate: worktree em
  `<scratchpad 7d42c549>/scratchpad/shadow-adrgate` (base `2858924`;
  conteúdo final). Se sumiu (reboot), contingência no OWNER-MORNING.
- O harness de cerimônia clona de HEAD: prova válida = commitar TUDO e
  rodar SEM escape (lição S334).
- Oráculo `--is-canonical` ANTES de editar QUALQUER path novo (incidente
  S334 com eval-baseline-n20.js).
