# PLAN-177 W0.1 (P1-4) — reprodução do defeito e prova da cura

**v2 — pós-consenso do debate** (CF-1 shape, CF-2 chave duplicada, CF-3
assimetria, CF-4 exit codes derivados).

Clone de trabalho: `<scratchpad>/w0-p14/repo` (`git clone --local` do canônico).
O repo canônico não foi tocado.

## 1. O defeito, com os args LITERAIS do step-15

`repro.py` monta um envelope AUTO-CONSISTENTE (inputs_hash recomputado no
próprio checkout via `compute_inputs_hash` + o manifesto vivo; pins lidos de
`codex-cli-pin.txt` e `codex-cli-pin-manifest.json`) e invoca
`.github/scripts/validate-pair-rail-verdict.py` com o argv copiado de
`release.yml:726-735` (job `release-gate`).

### ANTES da cura (`git stash push` dos dois validadores)

```
$ python3 ../repro.py . NO-GO
verdict declared : ['NO-GO']
exit code        : 0
stdout           : OK: verdict v0.0.0-plan177-decision-gate valid

$ python3 ../repro.py . MAYBE
exit code        : 0
stdout           : OK: verdict v0.0.0-plan177-decision-gate valid

$ python3 ../repro.py . NO-GO GO        # chave duplicada, last-wins
verdict declared : ['NO-GO', 'GO']
exit code        : 0
stdout           : OK: verdict v0.0.0-plan177-decision-gate valid
```

### DEPOIS da cura

```
$ python3 ../repro.py . NO-GO
exit code        : 3
stderr           : INVALID: verdict decision 'NO-GO' not in {GO, GO-WITH-CONDITIONS}
                   -- a release requires an explicit authorizing decision from the
                   pair-rail. Exact match: no case folding, no substring rule
                   (NO-GO contains GO).

$ python3 ../repro.py . NO-GO GO
exit code        : 3
stderr           : INVALID: verdict decision declared more than once (x2) -- the
                   reader is last-wins, so a duplicated `verdict:` silently
                   overrides the first; exactly one is required.

$ python3 ../repro.py . GO                    -> exit 0, OK: verdict ... valid
$ python3 ../repro.py . GO-WITH-CONDITIONS    -> exit 0, OK: verdict ... valid
```

Red pelo motivo certo: o stderr nomeia a DECISÃO **e o conjunto aceito**, e cita
o valor observado entre aspas. Sempre exit **3 (INVALID)**, nunca 1 (INFRA) —
distinção load-bearing, porque INFRA é o que `CEO_PAIR_RAIL_VERDICT_OPTIONAL`
pode dispensar.

## 2. `_release_tag_guard.py` — invocação real (o rail que vale em TODO modo)

```
$ python3 repo/.claude/scripts/local/_release_tag_guard.py delta \
    --repo guardprobe --tag v1.3.0        # verdict: NO-GO
FAIL: verdict ...-v1.3.0.md: decision 'NO-GO' not in {GO, GO-WITH-CONDITIONS}
      -- a tag may only be cut on an authorizing decision.
      [...] A NO-GO over a perfect delta is still a NO-GO.
exit=13

# chave duplicada
FAIL: verdict ...-v1.3.0.md declares the decision 2 times -- this reader is
      last-wins, so a duplicated `verdict:` silently overrides the first;
      exactly one is required.
exit=13

# `verdict:` vazio -> o parser local devolve LISTA, não string (CF-1)
FAIL: verdict ...-v1.3.0.md: decision '<non-string:list>' not in
      {GO, GO-WITH-CONDITIONS} [...]
exit=13
```

`release.sh:631` chama `python3 "$TAG_GUARD" delta ... || die` — exit 13 mata a
fase de tag (AC-2: invocação real do módulo, não unit isolado).

## 3. Controle positivo da SUÍTE (o teste falha sem a cura)

Com os dois validadores stashados e os testes novos no lugar:

```
$ python3 -m pytest .claude/scripts/tests/test_release_bump_sites.py -q \
    -k "decision or authorizing or rails or infra"
38 failed, 6 passed, 52 deselected in 22.17s
```

Os **38 vermelhos** são os controles do defeito (16 do validador do CI ×
{bound, unbound} + 2 de chave duplicada + 1 de INVALID-nunca-INFRA, 16 do tag
guard × {rc, stable} + 2 de duplicata, 1 do conjunto fechado compartilhado). Os
**6 verdes** são os controles do caminho autorizante (`GO` /
`GO-WITH-CONDITIONS`) — passam antes E depois, que é o ponto deles: provam que
a cura não fechou o caminho legítimo.

## 4. Suítes com a cura

```
$ python3 -m pytest .claude/scripts/tests/test_release_bump_sites.py -x -q
96 passed in 43.30s

$ python3 -m pytest .claude/scripts/tests/test_release_bump_sites.py -q -n 4
96 passed in 13.36s          # xdist: sem vazamento de env entre workers

$ python3 -m pytest .claude/scripts/tests/test_release_workflow_asserts.py -q
67 passed in 0.42s
```

96 = 52 pré-existentes + 44 novos. 67 = 66 pré-existentes + o assert estrutural
CF-3 (`test_gate_step_invokes_the_guard_delta_mode`); o assert de exit codes
(CF-4) foi reescrito, não somado. Ambos os testes novos de
`test_release_workflow_asserts.py` **rodam** (não são skip): o `release.yml`
vivo carrega o marcador `PLAN-166 W1-B`.
