# wave-s328-B — sentinel de aprovação (DRAFT: o SIGN preenche Data / Anchor-SHA / Approved-By e assina)

> Caminho casa `PLAN-*/wave-*-approved.md` (união fechada de padrões em
> `check_canonical_edit.py`). O binding é o `Patch-sha256` (land por PATCH, sem
> `MANIFEST-*`). O bloco `Scope:` é **DERIVADO** por
> `PLAN-183/w5-ceremony/finalize_patch.py` a partir de `git apply --numstat` —
> nunca escrito à mão. O `Anchor-SHA` é preenchido pelo `OWNER-S328-B-SIGN.sh`
> com `git rev-parse HEAD` no momento da assinatura; o `OWNER-S328-B-LAND.sh`
> aborta no G1 se não casar. Reescrever um byte deste arquivo depois de assinar
> invalida o `.asc`.

Plans: PLAN-169
Wave: wave-s328-B (cura do gate hook-latency — decisão do Owner Q5 de 2026-08-25, «Emenda + gate em pacote, e 1 rerun de madrugada»: a segunda chave RELATIVA em fase 1 ADVISORY, mais as duas emendas de ADR que registram por que a primeira chave sozinha decide errado)
Patch: .claude/plans/PLAN-169/s328-ceremony-B/B.patch
Patch-sha256: e635498ac63422537574a5ce9229d36a1ef11bc7c4aaa2f157c25b048d5e0950
Patch-base: 5bbc256e23f491c1306c32c8cd31d27791ad474f
Anchor-SHA: 44610ab2173672c31d9008835ce22d61f53d7da8
Data: 2026-08-26

## O que esta wave entrega

**Três arquivos canônicos: uma emenda de ADR que decide, uma emenda de ADR que
corrige uma afirmação refutada, e três linhas funcionais de workflow.** Toda a
LÓGICA vive em `.claude/scripts/profile-opus-4-7.py` e no seu teste
`.claude/scripts/tests/test_hook_latency_relative_gate.py`, ambos NÃO-canônicos
(oráculo `--is-canonical` responde 0) e por isso entregues por commit comum,
**fora** deste pacote — o workflow apenas PASSA duas flags e imprime uma linha
a mais no step-summary. Nenhum código de decisão entra em arquivo canônico. O
gate `G-PRE` do SIGN e do LAND exige os dois em `HEAD` antes de assinar ou
aplicar: sem eles o workflow passaria flags desconhecidas e o gate sairia 2 em
todo push (achado do pair-rail, rodadas 1–5).

1. **`.claude/adr/ADR-163-hook-latency-gate-percentile-stability.md`**
   (canônico, +221 linhas) — emenda «runner-normalized second key; the spawn
   probe is blind by construction». Registra o gatilho medido (run
   `32866209415`, `a16ac96`: `check_output_secrets` p95 **361,4 / 424,8 /
   229,1 ms** contra o teto duro de 180 ms, com a sonda de contenção lendo
   **UNCONTENDED a 7,76 ms** de piso de spawn e concedendo a 3ª tentativa) e as
   três pernas que provam que o veredito foi FALSO: os mesmos bytes medem
   70–77 ms local; os mesmos bytes PASSARAM 3 h 22 min antes (`6304f66`, run
   `32845976838`), e `git diff 6304f66..a16ac96 -- .claude/hooks/` toca **zero
   arquivos**; em `56f050c` o mesmo campo foi de 209 ms para **435 ms num
   rerun do commit idêntico**. A decisão em 7 itens: o teto de 180 ms **fica
   duro** (nenhuma terceira recalibração); entra uma segunda chave RELATIVA
   `hook_p50 <= K_e × ref_p50`, **p50 dos DOIS lados**; a referência é uma 6ª
   entrada de corpus `ref_exec`, stdlib-only de 3 termos, **round-robin dentro
   do laço de cada entrada**, proibida de importar `_lib`/`.claude/hooks`;
   quatro rótulos num conjunto FECHADO; **fase 1 é o que embarca — advisory,
   exit codes byte-idênticos aos de hoje**; e o `K` **não é fixado aqui** — o
   entregável é o PROCEDIMENTO (≥10 runs verdes / ≥3 dias, `K_e = 1,25 ×
   max(R_e)` admitido só sob a cota de admissibilidade). A sonda de spawn fica,
   vestigial, rebaixada em DOUTRINA e não em código.

2. **`.claude/adr/ADR-144-subagent-model-tiering-frontmatter.md`** (canônico,
   +57 linhas) — emenda que REFUTA três asserções do §S220 (`:89`, `:90-91`,
   `:96`: «`opts.model` é silenciosamente ignorado», «tiering para subagentes
   de Workflow NÃO é alcançável hoje», «o frontmatter `model:` por agente é o
   único canal que funciona»), com a medição do probe `wf_9ddadaab-12f`
   (harness 2.1.237, n=2) registrada em `PLAN-169:704-715`: com
   `opts.model='haiku'` o modelo **SERVIDO** foi `claude-haiku-4-5-20251001`;
   o controle sem override herdou `claude-fable-5`. O escopo é declarado
   ESTREITO de propósito (substrato numa versão fixada, n=2 — nenhuma garantia
   futura), a Decisão do ADR fica intacta, e os dois herdeiros do claim
   refutado (`PLAN-178:402-403` e `.claude/workflows/eval-baseline-n20.js:3`)
   são NOMEADOS sem serem editados: se viajam neste pacote ou num seguinte é a
   **OQ-11**, decisão do Owner.

3. **`.github/workflows/validate.yml`** (canônico, +3 linhas, ZERO removidas) —
   duas flags de argv no `run_gate` (`--exec-reference` e
   `--relative-advisory`, inseridas depois de `--p99-ceiling-ms`) e uma
   `note()` no bloco `PYSUM` do `publish()`, que publica por entrada
   `phase`, `verdict_label`, `ref_p50_ms` e `R_e`. **Nada mais é tocado**:
   `run_gate` 1/2/3, `BACKOFF_S`, a `contention_probe` e o literal de
   compatibilidade `FAILED on BOTH attempts (rc1=` (2 ocorrências)
   permanecem byte a byte — é o que mantém `PLAN-161/proof-retry-matrix.sh`
   e `PLAN-159/wave2-regression-proof.sh` provados.

## O que esta wave NÃO entrega (e por quê)

- **Ela NÃO deixa o `Validate` verde por si.** Fase 1 é advisory: os exit codes
  são os de hoje, então uma execução que reprova por p95 > 180 ms continua
  reprovando. O verde vem do **rerun de madrugada** do run `32866209415` (a
  decisão Q5 do Owner) e, se o runner estiver lento de forma persistente, da
  **fase 2**, que só pode ser fixada depois de ≥10 runs publicarem `R_e`.
- **Ela NÃO fixa `K_e`.** Qualquer `K` escrito num pacote antes dessa janela é
  INVENTADO — não existe hoje, em lugar nenhum, um par `(hook, referência)`
  medido num runner de CI.
- **As seis perguntas abertas do desenho** (célula `abs_ok ∧ ¬rel_ok`; o
  backstop de 600 ms sem evidência; aceitar a janela de fase 1; o ramo de
  fallback se a admissibilidade voltar VAZIA; os dois herdeiros do ADR-144;
  e `test_hook_latency.py` não ser rede de segurança para `check_output_secrets`)
  estão registradas em **`PLAN-169` §Open questions OQ-7..OQ-12** e **NÃO são
  decididas aqui**.

## Base de CI esperada após o land

O `Validate` continua podendo reprovar pelo mesmo motivo de hoje (p95 acima de
180 ms num runner lento) — a fase 1 não muda veredito. O que MUDA é que cada
execução passa a publicar, por entrada, o rótulo e o `ref_p50`: é essa série
que alimenta a OQ-9. Todo o resto da matriz de CI fica inalterado — o pacote
não toca nenhum outro workflow, nenhum hook e nenhum gate.

## Autorização de governança

- Decisão do Owner de 2026-08-25 (S328), Q5, verbatim: «Emenda + gate em
  pacote, e 1 rerun de madrugada».
- Desenho ratificado em `.claude/plans/PLAN-169/gate-design-S328.json`
  (síntese de três críticos: `ADOPT_WITH_CHANGES` para o candidato (i),
  `REJECT` para o (ii) isolado, do qual sobrevive só o vocabulário de rótulos).
- Pair-rail: registros em
  `.claude/plans/PLAN-169/s328-ceremony-B/rail-round-*.md`.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Plans: PLAN-169
Scope:
  - .claude/adr/ADR-144-subagent-model-tiering-frontmatter.md
  - .claude/adr/ADR-163-hook-latency-gate-percentile-stability.md
  - .github/workflows/validate.yml
<!-- END SIGNED SCOPE -->

## Residual declarado

- **Um runner lento em IO é indistinguível de uma regressão em IO** por
  qualquer referência que também faça IO. Isso é ACEITO, não resolvido, e está
  escrito na própria emenda.
- **O rótulo errado do wrapper NÃO é removido pelo auto-cap — ele é
  RENOMEADO.** Os ramos de falha do `run_gate` capturam QUALQUER rc não-zero:
  uma 3ª tentativa reprovada depois de sonda UNCONTENDED sai como
  `::error::… treating as a real regression` e `exit 1`, seja o rc 124 (cap de
  420 s) ou o rc 5 (`infrastructure_contended`) que o auto-cap introduz. Achado
  do pair-rail (rodada 1, P1): a emenda AFIRMAVA que o auto-cap tornava o caso
  inalcançável, e isso estava ERRADO — está corrigido no texto que embarca.
  **Em fase 1 o caminho não existe**: `exit_class == (0 if passed else 1)` por
  construção, provado por `test_auto_cap_in_phase1_keeps_a_nonzero_exit`, que
  força `--wall-budget-seconds 0` e exige **rc 1**. Este diff canônico não cria
  nenhuma rota para o rótulo errado — mas ensinar o wrapper a distinguir rc 5
  passa a ser **pré-condição NOMEADA da fase 2**, não faxina opcional.
- **A cota de admissibilidade do `K` é ESTRITA, e o código CASA** (achado do
  pair-rail, rodada 3, P2 — curado nos dois lados). A regra relativa
  `hook_p50 <= K_e × ref_p50` aceita igualdade; se a cota também aceitasse,
  então exatamente em `K_e = cota` o controle plantado de +150 ms teria
  `hook_p50 = K_e × max(ref_p50)`, `rel_ok` VERDADEIRO, e **passaria** — o
  oposto do que admitir aquele `K` deveria garantir. Estado atual, verificado
  em disco: `profile-opus-4-7.py` rejeita `K >= admissibility_max_K` (cota
  **EXCLUSIVA**) e mantém `rel_ok` com `<=`. **A estritez vive em exatamente
  UMA das duas comparações** — torná-las ambas estritas fecharia o intervalo
  duas vezes e rejeitaria um `K` admissível. A emenda que embarca descreve essa
  regra. Uma versão anterior deste sentinel afirmava que o código «ainda não
  casava»: era verdade sobre um profiler anterior e **não é mais**.
- **A célula `abs_ok ∧ ¬rel_ok`** está implementada e testada por unidade atrás
  do parâmetro `strict_relative`, que **não tem flag de CLI** — é inalcançável
  a partir do workflow até uma decisão posterior a ligar (OQ-7).
- **Custo nomeado:** como `wave2-regression-proof.sh` roda `run_gate` sem mock,
  suas tentativas passam a amostrar também 5 × 40 pontos de referência.
